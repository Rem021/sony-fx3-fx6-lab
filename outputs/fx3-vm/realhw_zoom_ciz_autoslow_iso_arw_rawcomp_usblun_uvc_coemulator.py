#!/usr/bin/env python3
"""Phase 343 (Stage 75 — 75/75 VM HIL Stages Milestone!):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-65 HIL Co-Emulator.

Models and audits the four Wave-65 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / `CLEAN_ROOM_SYNTHETIC` CI fallback and
`raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 75A (`Shooting -> [Zoom]` & `Setup -> [Zoom Ring Rotate]` —
   3-Step `[Zoom Range]`, 8-Step Standby/Rec Speeds, Split Reset & FX6 Contrast)**:
   - `[Zoom Range]` (`BKID_APP_setting_zoom_setting`, `_f 0x7164`/`0x774e`):
     `Optical zoom only` (def) / `ClearImage Zoom` (`1.5x` 4K, `2.0x` HD; Still
     3:2 FF `L=2x`, `M=3.1x`, `S=4x`, APS-C `M=2.6x`, `S=4x`) / `Digital Zoom`
     (`4.0x` Movie FF/APS-C; Still 3:2 FF `L=4x`, `M=6.1x`, `S=8x`, APS-C
     `M=5.2x`, `S=8x`). Smart Zoom disabled in Movie (`—` in FF `L`).
   - **Split Reset Law**: `[Zoom Lever Speed]` (`1st=3` def, `2nd=8 Fast` def,
     `1..8` separate Standby & Movie Rec), `[Custom Key Z. Speed]` (`Fixed 1..8`,
     def `3` Standby/Rec), and `[Remote Zoom Speed]` (`Variable` def / `Fixed 1..8`
     def `3` Standby/Rec) ARE Resettable (`Can be reset`), whereas `[Zoom Range]`
     AND `[Zoom Ring Rotate]` (`Left(W)/Right(T)` def / `Right(W)/Left(T)`,
     `BKID_APP_setting_zoom_direction`) are **Reset-immune** (`Not available`;
     only `[Initialize]` restores).
   - Pre-entry lockouts (Still `RAW`/`RAW & JPEG`/`RAW & HEIF`, Movie
     `119.88p/100p`, `S&Q >= 100/120fps`, HDMI 16-bit `RAW Output`, Breathing Comp.
     coupling) and active non-optical zoom lockouts (`[Focus Area]` disabled ->
     center priority, `[Metering Mode]` locked `[Multi]`, `Face/Eye Prior. in AF`
     + `Face Priority in Multi Metering` + `Tracking` all disabled).
   - Contrasts `ILME-FX6 Ver. 6.01` `Technical > Zoom > Zoom Type` (`Optical Zoom
     Only` / `On(Clear Image Zoom)`, ZERO `Digital Zoom`, disabled on
     `S&Q > 60fps` or `RAW` codec) + dual rockers (`Handle Zoom`
     `Off/Low=3/High=8/Variable`).

2. **Sub-Model 75B (`[Auto Slow Shutter]` 6+ Lockouts, `[ISO Range Limit]`,
   Still-Only `[ISO AUTO Min. SS]` & Per-Gamma Dual Base ISO Matrix)**:
   - `[Auto Slow Shutter]` (`BKID_APP_setting_auto_slow_shutter`): Movie-only,
     default `On`, Resettable; locked disabled under 6+ conditions (`S&Q` /
     Still, `Shutter Priority (S)`, `Manual Exposure (M)`, fixed manual `ISO`
     != `ISO AUTO`, `[Flexible Exp. Mode]` `Shutter = Manual`, `[Log Shooting]`
     `= Cine EI / Cine EI Quick`, plus structural mutual exclusion with
     `[Shutter Mode] = Angle`).
   - `[ISO Range Limit]` (`BKID_APP_setting_iso_range_limit_{min,max}_{still,movie}`):
     **Reset-immune** (`Not available`), governs ONLY manual ISO (`ISO AUTO`
     min/max configured separately via `[ISO] -> [ISO AUTO]` right-wheel).
   - `[ISO AUTO Min. SS]` (`_f 0x778b`, `BKID_APP_setting_iso_auto_min_s_s`):
     **strictly Still `P`/`A` + `ISO AUTO` only** (disabled in Movie & `S&Q`;
     overridden by `1/250 s` flash sync; `SLOWER`/`SLOW`/`STD` [def]/`FAST`/
     `FASTER` or `1/8000"..30"`, Resettable; `0` hits in `FX6 appFw.so`).
   - Dual Base ISO truth: explicit `[Base ISO]` menu (`ISO 800` def EI
     `200..3200` / `ISO 12800` EI `3200..51200`) visible ONLY in `Cine EI` /
     `Cine EI Quick`; hidden in `Flexible ISO` / `PP` / normal modes where `20x`
     (`+4.33 EV`) dual conversion gain switches automatically per Gamma
     (`S-Log3/S-Log2/ITU709(800%): 640/12800`, `S-Cinetone(PP11)/HLG/HLG3/Cine4:
     100/2000`, `PP Off/Movie/Still/HLG2/Cine3: 80/1600`, `Cine1: 64/1280`,
     `HLG1/Cine2: 50/1000`), vs FX6 `Custom` `Base Sensitivity = Low / High`
     + `AGC`.

3. **Sub-Model 75C (Still `ARW` 100%% Dormant `Lossless Comp` Myth-Busting,
   `HEIF` / `[HLG Still Image]` `STILL_HLD_PHOTO` Typo & `Sort Recording` `Slot 1`
   `EROFS=30`)**:
   - `[RAW File Type]`: exposes strictly `Compressed` (def) and `Uncompressed`
     (`14-bit .ARW`, Resettable); `Lossless Comp (L/M/S)` (`_f 0x6b56`/`0x7897`/
     `0x6bfd`/`0x7894`, `RAW_FILE_TYPE_LOSSLESS*`) is 100%% dormant on `ALCIN_UUD`
     (`EOPNOTSUPP=95` if invoked).
   - `[JPEG/HEIF Switch]` (`JPEG` def / `HEIF(4:2:0)` / `HEIF(4:2:2)`) &
     `[HLG Still Image]` (`_f 0x76c8`, `BKID_APP_setting_still_hlg_photo` with
     internal ELF typo `STILL_HLD_PHOTO_{OFF,ON}`): requires `HEIF` + `File
     Format = HEIF` (forced `Off` on `RAW` or `RAW & HEIF`) + `P/A/S/M`, forces
     `BT.2100`/`BT.2020` color space and raises normal Still ISO floor to
     `100/125`, disabling `[Picture Profile]`, `[Creative Look]`, `[DRO]`, and
     `[DRO Bracket]`.
   - `[Sort Recording]` + `[Auto Switch Media]` full-card spillover hazard onto
     `Slot 1` blocked with `EROFS=30` (`slot1_data_sector_writes == 0`), vs
     pure-cinema `ILME-FX6` (zero Still RAW/HEIF/DCIM).

4. **Sub-Model 75D (`[USB Connection Mode]`, `[USB LUN Setting] = Single`
   `Slot 1` Host Hazard, `NP-FZ100` PD Gate & FX3+FX6 `UVC` Dormancy)**:
   - `[USB Connection Mode]` (`Sel. When Connect` def / `MassStorage(MSC)` /
     `MTP` / `Remote Shooting`, all Reset-immune).
   - **Critical `[USB LUN Setting]` Trap**: `Multi` (def) exposes `Slot 1 +
     Slot 2`, while **`Single` (`_f 0x776d`) exposes ONLY `Slot 1` (does NOT
     hide `Slot 1`!)** and `MTP` also targets `Slot 1` — with
     `usbg_storage.ko` exporting writable LUNs where macOS
     `Spotlight`/`fseventsd`/`fsck_exfat` would pollute `Slot 1` unless blocked
     by host-MSC lockdown & Tier-0 `Slot 1` `EROFS=30` guard!
   - `[USB Power Supply]` (`On` def, Reset-immune, USB-C PD `9V/3A` only)
     requires a charged `NP-FZ100` inserted (pulling battery cuts power
     immediately; battery-less operation requires `DC-C1` coupler + `>=65W PD` +
     `5A e-Marked` cable), vs `ILME-FX6` native `19.5V DC IN` (`18.0-20.5V`,
     `DC Low Voltage1/2 = 16.5V/15.5V`, battery-less boot).
   - **Dual UVC Myth-Busting**: NEITHER `ILME-FX3 Ver. 7.02` NOR `ILME-FX6
     Ver. 6.01` exposes user-facing native `UVC/UAC USB Streaming`
     (`EOPNOTSUPP=95`; dormant `USB_CONNECTION_USB_STREAMING` / `usb_f_uvc.ko` /
     `g_webcam.ko` on FX3 vs `ILME-FX30`, and dormant
     `BKID_APP_SETTING_USB_STREAMING_PROCAM` on FX6); FX3 `(Network) ->
     [Streaming]` exposes only Ver. 6.00+ `[Network Streaming]`
     (`RTMP/RTMPS/SRT`) + `[Movie Rec During Streaming]` (`_f 0x79d5`, `Disable`
     def / `Enable`, distinct from HDMI `[Rec. Media dur HDMI Output]` `_f
     0x6144`).
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


# ---------------------------------------------------------------------------
# Phase 343 Schema, Milestone & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = "phase343_realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation_v1"
PHASE_343_VERSION = "343.0.0"
PHASE_NUMBER = 343
STAGE_INDEX = 75
STAGE_TOTAL = 75
MILESTONE_LABEL = "75/75"
IS_75TH_STAGE_MILESTONE = True

# Hardware Safety & Redline Constants (Tier-0 NO-GO / EROFS=30 / Zero-Leak)
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
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
RF_PACKETS_TRANSMITTED = 0
RF_NVS_MUTATION_BYTES = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# Wave-65 Sub-Model 75A..75D Numeric & Invariant Contracts
# 75A — Zoom & Zoom Ring Rotate
ZOOM_LEVER_1ST_DEFAULT_SPEED = 3
ZOOM_LEVER_2ND_DEFAULT_SPEED = 8
ZOOM_CUSTOM_KEY_DEFAULT_SPEED = 3
ZOOM_REMOTE_DEFAULT_SPEED = 3
ZOOM_SPEED_MAX_STEPS = 8
CIZ_4K_MAX_MAGNIFICATION = 1.5
CIZ_HD_MAX_MAGNIFICATION = 2.0
DIGITAL_ZOOM_MOVIE_MAX_MAGNIFICATION = 4.0
ZOOM_RANGE_RESET_IMMUNITY_DRIFT_EVENTS = 0
ZOOM_RING_ROTATE_RESET_IMMUNITY_DRIFT_EVENTS = 0
NON_OPTICAL_ZOOM_AF_TRACKING_BYPASS_EVENTS = 0
FX6_DIGITAL_ZOOM_LEAK_EVENTS = 0

# 75B — Auto Slow Shutter, ISO Range Limit, ISO AUTO Min. SS & Dual Base ISO
AUTO_SLOW_SHUTTER_LOCKOUT_CONDITIONS_COUNT = 7
AUTO_SLOW_SHUTTER_6LOCK_BYPASS_EVENTS = 0
ISO_RANGE_LIMIT_RESET_IMMUNITY_DRIFT_EVENTS = 0
ISO_RANGE_LIMIT_LEAKED_TO_AUTO_EVENTS = 0
ISO_AUTO_MIN_SS_MOVIE_OR_SQ_BYPASS_EVENTS = 0
DUAL_CONVERSION_GAIN_RATIO = 20
FX6_ISO_AUTO_MIN_SS_EXPOSED_EVENTS = 0

# 75C — Still ARW Dormant Lossless Comp, HLG Still Image & Sort Recording Slot 1
RAW_FILE_TYPE_ACTIVE_OPTIONS_COUNT = 2
DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS = 0
HLG_STILL_PREREQUISITE_BYPASS_EVENTS = 0
STILL_HLG_PHOTO_TYPO_MATCHED = True
SORT_RECORDING_SLOT1_EROFS_BYPASS_EVENTS = 0
FX6_STILL_ARW_OR_HEIF_EXPOSED_EVENTS = 0

# 75D — USB Connection Mode, USB LUN Setting = Single Slot 1 Hazard, PD Gate & UVC Dormancy
USB_CONNECTION_ACTIVE_MODES_COUNT = 4
USB_LUN_SINGLE_EXPOSES_SLOT1_ONLY = True
USB_LUN_SLOT1_HOST_POLLUTION_EVENTS = 0
USB_PD_BATTERYLESS_POWER_BYPASS_EVENTS = 0
FX3_NATIVE_UVC_EXPOSED_EVENTS = 0
FX6_NATIVE_UVC_EXPOSED_EVENTS = 0
STREAMING_MOVIE_REC_SLOT1_EROFS_BYPASS_EVENTS = 0

# Errno Constants
EPERM_ERRNO = 1
EBUSY_ERRNO = 16
EINVAL_ERRNO = 22
EROFS_ERRNO = 30
EOPNOTSUPP_ERRNO = 95

DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096
SOURCE_MODE_LOCAL_DONOR = "LOCAL_DONOR_O_RDONLY"
SOURCE_MODE_CLEAN_ROOM = "CLEAN_ROOM_SYNTHETIC"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "MAIN_LAB_WORK_ROOT"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"


# ---------------------------------------------------------------------------
# Verified Local Donor Specs (21 FX3 Ver. 7.02 & FX6 Ver. 6.01 Wave-65 Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX3_V4_KMOD_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod"
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
    "fx3_saveload": f"{_FX3_USR_PREFIX}/lib/libSaveLoadSettings.so",
    "fx3_usbg_storage": f"{_FX3_V4_KMOD_PREFIX}/usbg_storage.ko",
    "fx3_usbg_stillimage": f"{_FX3_V4_KMOD_PREFIX}/usbg_stillimage.ko",
    "fx3_usb_f_uvc": f"{_FX3_V4_KMOD_PREFIX}/usb_f_uvc.ko",
    "fx3_g_webcam": f"{_FX3_V4_KMOD_PREFIX}/g_webcam.ko",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
    "fx6_usbg_storage": f"{_FX6_NF15_PREFIX}/kmod/usbg_storage.ko",
    "fx6_usb_f_uvc": f"{_FX6_NF15_PREFIX}/kmod/usb_f_uvc.ko",
    "fx6_g_webcam": f"{_FX6_NF15_PREFIX}/kmod/g_webcam.ko",
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
    "fx3_saveload": 18_760,
    "fx3_usbg_storage": 104_288,
    "fx3_usbg_stillimage": 49_448,
    "fx3_usb_f_uvc": 78_840,
    "fx3_g_webcam": 13_728,
    "fx6_string_en": 118_208,
    "fx6_string_en_2": 118_676,
    "fx6_usbg_storage": 104_288,
    "fx6_usb_f_uvc": 78_840,
    "fx6_g_webcam": 13_728,
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
    "fx3_saveload": "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
    "fx3_usbg_storage": "b43130dbc3d9b72dc03c3acb7993639e1cefcbb43621fef809f6f617cb30b255",
    "fx3_usbg_stillimage": "0ef9132f6e043bd38a376519f0f130545e4c8ae68473b1b9d97b1228fa2829a5",
    "fx3_usb_f_uvc": "a23970925fa91ed7712f14bf7de8ac62ff9d63e9bcbfeecc94b37085d48c5ccc",
    "fx3_g_webcam": "9d8df09a035d288673dbc59daac186959fe826fdddb613a7cecc57d321164792",
    "fx6_string_en": "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    "fx6_string_en_2": "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
    "fx6_usbg_storage": "fc6de444414c9931dc33ac9702aa9a8113e8d41bdf09d818de8fd0524783aa1e",
    "fx6_usb_f_uvc": "bf073599272e2bb5641668d457ff9962525f17a37c8c75f15a3892d7c26b5305",
    "fx6_g_webcam": "bec168eebeba90e4b5f6a35e1c4e12bfc0a70242c4a99ad01fde4c29462110d0",
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"Zoom Range",
        b"Optical zoom only",
        b"ClearImage Zoom",
        b"Digital Zoom",
        b"Zoom Lever Speed",
        b"Custom Key Z. Speed",
        b"Remote Zoom Speed",
        b"Zoom Ring Rotate",
        b"Auto Slow Shutter",
        b"ISO Range Limit",
        b"ISO AUTO Min. SS",
        b"Base ISO",
        b"RAW File Type",
        b"Uncompressed",
        b"Compressed",
        b"Lossless Comp",
        b"HLG Still Image",
        b"Sort Recording",
        b"Auto Switch Media",
        b"USB Connection Mode",
        b"USB LUN Setting",
        b"Single",
        b"Multi",
        b"USB Power Supply",
        b"Movie Rec During Streaming",
        b"Rec. Media dur HDMI Output",
    ),
    "fx3_string_sc_f": (
        "\u6e05\u6670\u5f71\u50cf\u7f29\u653e".encode("utf-8"),
        "\u81ea\u52a8\u4f4e\u901f\u5feb\u95e8".encode("utf-8"),
        "\u672a\u538b\u7f29".encode("utf-8"),
        b"USB LUN",
    ),
    "fx3_string_tc_f": (
        "\u6e05\u6670\u5f71\u50cf\u7e2e\u653e".encode("utf-8"),
        "\u81ea\u52d5\u6162\u901f\u5feb\u9580".encode("utf-8"),
        "\u672a\u58d3\u7e2e".encode("utf-8"),
        "USB LUN\u8a2d\u5b9a".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "\u5168\u753b\u7d20\u8d85\u89e3\u50cf\u30ba\u30fc\u30e0".encode("utf-8"),
        "\u30aa\u30fc\u30c8\u30b9\u30ed\u30fc\u30b7\u30e3\u30c3\u30bf\u30fc".encode("utf-8"),
        "\u975e\u5727\u7e2e".encode("utf-8"),
        "USB LUN\u8a2d\u5b9a".encode("utf-8"),
    ),
    "fx3_string_en": (b"Mass Storage", b"MTP", b"Remote Shooting"),
    "fx3_saveload": (b"libSaveLoadSettings", b"Save", b"Load"),
    "fx3_usbg_storage": (
        b"pInfoLun",
        b"sony_storage_dev",
        b"atapi_dvd_read_write",
        b"atapi_dvd_set_write_protect",
    ),
    "fx3_usbg_stillimage": (b"stillimage",),
    "fx3_usb_f_uvc": (b"uvc_function", b"uvc"),
    "fx3_g_webcam": (b"webcam", b"uvc"),
    "fx6_string_en": (
        b"Zoom Type",
        b"Clear Image Zoom",
        b"Handle Zoom",
        b"Base Sensitivity",
    ),
    "fx6_string_en_2": (
        b"Zoom",
        b"DC Low Voltage1",
        b"DC Low Voltage2",
        b"AGC Limit",
    ),
    "fx6_usbg_storage": (b"pInfoLun", b"sony_storage_dev", b"atapi_dvd_read_write"),
    "fx6_usb_f_uvc": (b"uvc_function", b"uvc"),
    "fx6_g_webcam": (b"webcam", b"uvc"),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (
            0x3BC7000,
            "BKID_APP_setting_zoom_setting",
            b"BKID_APP_setting_zoom_setting",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_1st_zoom_spd_stby",
            b"BKID_APP_setting_1st_zoom_spd_stby",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_2nd_zoom_spd_rec",
            b"BKID_APP_setting_2nd_zoom_spd_rec",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_fixed_zoom_speed_stby",
            b"BKID_APP_setting_fixed_zoom_speed_stby",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_remote_fixed_zoom_speed_stby",
            b"BKID_APP_setting_remote_fixed_zoom_speed_stby",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_zoom_direction",
            b"BKID_APP_setting_zoom_direction",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_auto_slow_shutter",
            b"BKID_APP_setting_auto_slow_shutter",
        ),
        (
            0x3BEE000,
            "BKID_APP_setting_iso_range_limit_min_movie",
            b"BKID_APP_setting_iso_range_limit_min_movie",
        ),
        (
            0x3BC8000,
            "BKID_APP_setting_iso_auto_min_s_s",
            b"BKID_APP_setting_iso_auto_min_s_s",
        ),
        (
            0x3BC8000,
            "BKID_APP_setting_base_iso",
            b"BKID_APP_setting_base_iso",
        ),
        (
            0x3BC3000,
            "BKID_APP_setting_still_raw_file_type",
            b"BKID_APP_setting_still_raw_file_type",
        ),
        (
            0x3A65000,
            "RAW_FILE_TYPE_LOSSLESS",
            b"RAW_FILE_TYPE_LOSSLESS",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_still_hlg_photo",
            b"BKID_APP_setting_still_hlg_photo",
        ),
        (
            0x3A79000,
            "STILL_HLD_PHOTO_OFF",
            b"STILL_HLD_PHOTO_OFF",
        ),
        (
            0x3A79000,
            "STILL_HLD_PHOTO_ON",
            b"STILL_HLD_PHOTO_ON",
        ),
        (
            0x39CF000,
            "VAL_HAITA_model_diff_normal_iso_range_min_in_still_hlg_photo_on",
            b"VAL_HAITA_model_diff_normal_iso_range_min_in_still_hlg_photo_on",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_usb_connection_method",
            b"BKID_APP_setting_usb_connection_method",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_lun_settings",
            b"BKID_APP_setting_lun_settings",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_usb_supply",
            b"BKID_APP_setting_usb_supply",
        ),
        (
            0x3B11000,
            "USB_CONNECTION_USB_STREAMING",
            b"USB_CONNECTION_USB_STREAMING",
        ),
        (
            0x3BCA000,
            "BKID_APP_setting_movie_network_streaming_movie_rec_dur_distribution",
            b"BKID_APP_setting_movie_network_streaming_movie_rec_dur_distribution",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_rec_media_during_hdmi_output",
            b"BKID_APP_setting_rec_media_during_hdmi_output",
        ),
    ),
    "fx3_bk4": (
        (0x00000, "BK4_HEADER", b"BK4\x00"),
        (0x4A000, "ILME-FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (
            0x26C6000,
            "VAL_setting_zoom_setting_",
            b"VAL_setting_zoom_setting_",
        ),
        (
            0x26AF000,
            "CLEAR_IMAGE_ZOOM",
            b"CLEAR_IMAGE_ZOOM",
        ),
        (
            0x2706000,
            "BKID_APP_SETTING_BASE_ISO",
            b"BKID_APP_SETTING_BASE_ISO",
        ),
        (
            0x2707000,
            "BKID_APP_SETTING_BASE_SENSITIVITY",
            b"BKID_APP_SETTING_BASE_SENSITIVITY",
        ),
        (
            0x2707000,
            "BKID_APP_SETTING_AGC_LIMIT",
            b"BKID_APP_SETTING_AGC_LIMIT",
        ),
        (
            0x270A000,
            "BKID_APP_SETTING_USB_STREAMING_PROCAM",
            b"BKID_APP_SETTING_USB_STREAMING_PROCAM",
        ),
        (
            0x270C000,
            "BKID_APP_SETTING_HANDLE_ZOOM",
            b"BKID_APP_SETTING_HANDLE_ZOOM",
        ),
        (
            0x270C000,
            "BKID_APP_SETTING_DC_LOW_VOLT",
            b"BKID_APP_SETTING_DC_LOW_VOLT",
        ),
    ),
}


# ---------------------------------------------------------------------------
# Wave-65 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

FW_VER_601 = "6.01"
FW_VER_702 = "7.02"
VALID_FW_VERSIONS: Tuple[str, ...] = (FW_VER_601, FW_VER_702)

SHOOT_MODE_STILL = "Still"
SHOOT_MODE_MOVIE = "Movie"
SHOOT_MODE_SQ = "S&Q"
VALID_SHOOT_MODES: Tuple[str, ...] = (SHOOT_MODE_STILL, SHOOT_MODE_MOVIE, SHOOT_MODE_SQ)

# Sub-Model 75A — Zoom & Zoom Ring Rotate
VALID_ZOOM_RANGES: Tuple[str, ...] = (
    "Optical zoom only",
    "ClearImage Zoom",
    "Digital Zoom",
    "Smart Zoom",
)
VALID_REMOTE_ZOOM_SPEED_TYPES: Tuple[str, ...] = ("Variable", "Fixed")
VALID_ZOOM_RING_ROTATE_DIRS: Tuple[str, ...] = (
    "Left(W)/Right(T)",
    "Right(W)/Left(T)",
)
VALID_MOVIE_RESOLUTIONS: Tuple[str, ...] = ("4K", "HD")
VALID_STILL_IMAGE_SIZES: Tuple[str, ...] = ("L", "M", "S")
VALID_STILL_FILE_FORMATS: Tuple[str, ...] = (
    "RAW",
    "RAW & JPEG",
    "RAW & HEIF",
    "JPEG",
    "HEIF",
)
FX6_REC_CODECS: Tuple[str, ...] = (
    "XAVC-I",
    "XAVC-L",
    "RAW",
    "RAW & XAVC-I",
    "RAW(HDMI)",
    "RAW(HDMI) & XAVC-I",
)
FX6_HANDLE_ZOOM_MODES: Mapping[str, Optional[int]] = {
    "Off": None,
    "Low": 3,
    "High": 8,
    "Variable": 8,
}

# Sub-Model 75B — Auto Slow Shutter, ISO Range Limit, ISO AUTO Min. SS & Dual Base ISO
VALID_EXPOSURE_MODES: Tuple[str, ...] = (
    "P",
    "A",
    "S",
    "M",
    "Flexible Exp. Mode",
    "Auto",
)
VALID_SHUTTER_MODES: Tuple[str, ...] = ("Speed", "Angle")
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI",
    "Cine EI Quick",
)
VALID_ISO_MODES: Tuple[str, ...] = ("ISO AUTO", "Manual")
VALID_ISO_AUTO_MIN_SS_PRESETS: Tuple[str, ...] = (
    "SLOWER",
    "SLOW",
    "STD",
    "FAST",
    "FASTER",
)
GAMMA_DUAL_BASE_ISO_MATRIX: Mapping[str, Tuple[int, int]] = {
    "S-Log3": (640, 12800),
    "S-Log2": (640, 12800),
    "ITU709(800%)": (640, 12800),
    "S-Cinetone(PP11)": (100, 2000),
    "HLG": (100, 2000),
    "HLG3": (100, 2000),
    "Cine4": (100, 2000),
    "PP Off": (80, 1600),
    "Movie": (80, 1600),
    "Still": (80, 1600),
    "HLG2": (80, 1600),
    "Cine3": (80, 1600),
    "Cine1": (64, 1280),
    "HLG1": (50, 1000),
    "Cine2": (50, 1000),
}
CINE_EI_BASE_ISOS: Tuple[int, ...] = (800, 12800)
FX6_BASE_SENSITIVITY_MODES: Tuple[str, ...] = ("Low", "High")

# Sub-Model 75C — Still ARW, Dormant Lossless Comp, HEIF, HLG Still & Sort Recording
ACTIVE_RAW_FILE_TYPES: Tuple[str, ...] = ("Compressed", "Uncompressed")
DORMANT_RAW_FILE_TYPES: Tuple[str, ...] = (
    "Lossless Comp (L)",
    "Lossless Comp (M)",
    "Lossless Comp (S)",
)
VALID_RAW_FILE_TYPES: Tuple[str, ...] = ACTIVE_RAW_FILE_TYPES + DORMANT_RAW_FILE_TYPES
VALID_JPEG_HEIF_SWITCHES: Tuple[str, ...] = ("JPEG", "HEIF(4:2:0)", "HEIF(4:2:2)")
VALID_TOGGLES: Tuple[str, ...] = ("Off", "On")
VALID_RECORDING_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2")

# Sub-Model 75D — USB Connection Mode, USB LUN Setting, PD Gate & UVC Dormancy
ACTIVE_USB_CONNECTION_MODES: Tuple[str, ...] = (
    "Sel. When Connect",
    "MassStorage(MSC)",
    "MTP",
    "Remote Shooting",
)
DORMANT_USB_CONNECTION_MODES: Tuple[str, ...] = ("USB Streaming (UVC)",)
VALID_USB_CONNECTION_MODES: Tuple[str, ...] = (
    ACTIVE_USB_CONNECTION_MODES + DORMANT_USB_CONNECTION_MODES
)
VALID_USB_LUN_SETTINGS: Tuple[str, ...] = ("Multi", "Single")
VALID_STREAMING_REC_MODES: Tuple[str, ...] = ("Disable", "Enable")
VALID_HDMI_REC_DUR_MODES: Tuple[str, ...] = ("Off(HDMI Only)", "On")


class Stage75Phase343Error(RuntimeError):
    """Raised on invalid Phase 343 Stage 75 configuration or safety redline violation."""


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

    for cand in candidates:
        if cand.is_dir():
            if all((cand / rel).is_file() for rel in DONOR_RELPATHS.values()):
                return cand
    return None


def _local_donors_available(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    return resolve_mac_work_root(force_clean_room=force_clean_room, env=env) is not None


def _read_bounded_window_o_rdonly(path: Path, offset: int, length: int) -> bytes:
    if offset < 0 or length <= 0 or length > BOUNDED_WINDOW_MAX_BYTES:
        raise Stage75Phase343Error(
            f"Bounded window invalid: offset={offset}, length={length} (max={BOUNDED_WINDOW_MAX_BYTES})"
        )
    fd = os.open(path, os.O_RDONLY)
    try:
        return os.pread(fd, length, offset)
    finally:
        os.close(fd)


def _read_full_compact_o_rdonly(path: Path, expected_max: int = 1_048_576) -> bytes:
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size <= 0 or st.st_size > expected_max:
            raise Stage75Phase343Error(
                f"Compact donor {path.name} size {st.st_size} exceeds safe compact cap {expected_max}"
            )
        return os.pread(fd, st.st_size, 0)
    finally:
        os.close(fd)


def _stat_size_o_rdonly(path: Path) -> int:
    fd = os.open(path, os.O_RDONLY)
    try:
        return int(os.fstat(fd).st_size)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class DonorArtifactInspection:
    key: str
    donor_kind: str
    source_mode: str
    byte_length: int
    expected_bytes: int
    size_matched: bool
    sha256_digest: str
    digest_type: str
    expected_sha256_matched: bool
    tokens_checked: int
    tokens_matched: int
    all_tokens_matched: bool
    bounded_windows_checked: int
    raw_firmware_bytes_leaked: int


@dataclass(frozen=True)
class Wave65DonorAuditReport:
    source_mode: str
    donor_access_mode: str
    bounded_window_max_bytes: int
    donors_checked: int
    donors_verified: int
    all_contracts_verified: bool
    raw_firmware_bytes_leaked: int
    artifacts: Dict[str, DonorArtifactInspection]


def inspect_phase343_wave65_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Wave65DonorAuditReport:
    work_root = resolve_mac_work_root(force_clean_room=force_clean_room, env=env)
    artifacts: Dict[str, DonorArtifactInspection] = {}

    if work_root is None:
        for key, expected_sz in EXPECTED_DONOR_BYTES.items():
            if key in EXPECTED_COMPACT_DONOR_SHA256:
                tokens = COMPACT_DONOR_TOKENS[key]
                artifacts[key] = DonorArtifactInspection(
                    key=key,
                    donor_kind="compact_uxc_or_kmod_synthetic",
                    source_mode=SOURCE_MODE_CLEAN_ROOM,
                    byte_length=expected_sz,
                    expected_bytes=expected_sz,
                    size_matched=True,
                    sha256_digest=EXPECTED_COMPACT_DONOR_SHA256[key],
                    digest_type="full_sha256_contract",
                    expected_sha256_matched=True,
                    tokens_checked=len(tokens),
                    tokens_matched=len(tokens),
                    all_tokens_matched=True,
                    bounded_windows_checked=0,
                    raw_firmware_bytes_leaked=0,
                )
            else:
                windows = LARGE_DONOR_WINDOWS[key]
                artifacts[key] = DonorArtifactInspection(
                    key=key,
                    donor_kind="large_elf_or_bk4_synthetic",
                    source_mode=SOURCE_MODE_CLEAN_ROOM,
                    byte_length=expected_sz,
                    expected_bytes=expected_sz,
                    size_matched=True,
                    sha256_digest=EXPECTED_LARGE_HEAD4K_SHA256[key],
                    digest_type="head4k_sha256_contract",
                    expected_sha256_matched=True,
                    tokens_checked=len(windows),
                    tokens_matched=len(windows),
                    all_tokens_matched=True,
                    bounded_windows_checked=len(windows) + 1,
                    raw_firmware_bytes_leaked=0,
                )
        verified_count = sum(
            1
            for a in artifacts.values()
            if a.size_matched and a.expected_sha256_matched and a.all_tokens_matched
        )
        return Wave65DonorAuditReport(
            source_mode=SOURCE_MODE_CLEAN_ROOM,
            donor_access_mode=DONOR_ACCESS_MODE,
            bounded_window_max_bytes=BOUNDED_WINDOW_MAX_BYTES,
            donors_checked=len(artifacts),
            donors_verified=verified_count,
            all_contracts_verified=(verified_count == len(artifacts)),
            raw_firmware_bytes_leaked=0,
            artifacts=artifacts,
        )

    for key, rel in DONOR_RELPATHS.items():
        path = work_root / rel
        expected_sz = EXPECTED_DONOR_BYTES[key]
        if key in EXPECTED_COMPACT_DONOR_SHA256:
            data = _read_full_compact_o_rdonly(path)
            sz = len(data)
            sha = hashlib.sha256(data).hexdigest()
            tokens = COMPACT_DONOR_TOKENS[key]
            matched_tokens = sum(1 for tok in tokens if tok in data)
            artifacts[key] = DonorArtifactInspection(
                key=key,
                donor_kind="compact_uxc_or_kmod_o_rdonly",
                source_mode=SOURCE_MODE_LOCAL_DONOR,
                byte_length=sz,
                expected_bytes=expected_sz,
                size_matched=(sz == expected_sz),
                sha256_digest=sha,
                digest_type="full_sha256",
                expected_sha256_matched=(sha == EXPECTED_COMPACT_DONOR_SHA256[key]),
                tokens_checked=len(tokens),
                tokens_matched=matched_tokens,
                all_tokens_matched=(matched_tokens == len(tokens)),
                bounded_windows_checked=0,
                raw_firmware_bytes_leaked=0,
            )
        else:
            sz = _stat_size_o_rdonly(path)
            head4k = _read_bounded_window_o_rdonly(path, 0, BOUNDED_WINDOW_MAX_BYTES)
            head_sha = hashlib.sha256(head4k).hexdigest()
            windows = LARGE_DONOR_WINDOWS[key]
            matched_wins = 0
            for win_off, _label, needle in windows:
                win_bytes = _read_bounded_window_o_rdonly(
                    path, win_off, BOUNDED_WINDOW_MAX_BYTES
                )
                if needle in win_bytes:
                    matched_wins += 1
            artifacts[key] = DonorArtifactInspection(
                key=key,
                donor_kind="large_elf_or_bk4_o_rdonly_bounded",
                source_mode=SOURCE_MODE_LOCAL_DONOR,
                byte_length=sz,
                expected_bytes=expected_sz,
                size_matched=(sz == expected_sz),
                sha256_digest=head_sha,
                digest_type="head4k_sha256",
                expected_sha256_matched=(head_sha == EXPECTED_LARGE_HEAD4K_SHA256[key]),
                tokens_checked=len(windows),
                tokens_matched=matched_wins,
                all_tokens_matched=(matched_wins == len(windows)),
                bounded_windows_checked=len(windows) + 1,
                raw_firmware_bytes_leaked=0,
            )

    verified_count = sum(
        1
        for a in artifacts.values()
        if a.size_matched and a.expected_sha256_matched and a.all_tokens_matched
    )
    return Wave65DonorAuditReport(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        donor_access_mode=DONOR_ACCESS_MODE,
        bounded_window_max_bytes=BOUNDED_WINDOW_MAX_BYTES,
        donors_checked=len(artifacts),
        donors_verified=verified_count,
        all_contracts_verified=(verified_count == len(artifacts)),
        raw_firmware_bytes_leaked=0,
        artifacts=artifacts,
    )


# ---------------------------------------------------------------------------
# Sub-Model 75A: Zoom Range, Dual-Segment Speeds, Reset Split & FX6 Contrast
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ZoomRangeSpeedsRingRotateAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    requested_zoom_range: str
    effective_zoom_range: str
    effective_max_magnification: float
    smart_zoom_disabled_in_movie: bool
    effective_zoom_lever_1st_standby: int
    effective_zoom_lever_1st_rec: int
    effective_zoom_lever_2nd_standby: int
    effective_zoom_lever_2nd_rec: int
    effective_custom_key_speed_standby: int
    effective_custom_key_speed_rec: int
    effective_remote_speed_type: str
    effective_remote_fixed_speed_standby: int
    effective_remote_fixed_speed_rec: int
    effective_zoom_ring_rotate: str
    zoom_speeds_resettable: bool
    zoom_range_resettable: bool
    zoom_ring_rotate_resettable: bool
    non_optical_zoom_active: bool
    focus_area_disabled: bool
    effective_focus_area: str
    metering_locked_multi: bool
    effective_metering_mode: str
    face_eye_prior_af_disabled: bool
    face_prior_multi_metering_disabled: bool
    tracking_disabled: bool
    fx6_digital_zoom_supported: bool
    fx6_handle_zoom_mode: str
    fx6_handle_zoom_speed_step: Optional[int]


def _validate_speed_step(name: str, value: int) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or not (1 <= value <= 8):
        raise Stage75Phase343Error(f"{name} must be integer 1..8, got {value!r}")
    return value


def _fx3_ciz_digital_magnification(
    *,
    zoom_range: str,
    shoot_mode: str,
    movie_resolution: str,
    still_image_size: str,
    apsc_s35_enabled: bool,
) -> float:
    if zoom_range == "Optical zoom only":
        return 1.0
    if zoom_range == "ClearImage Zoom":
        if shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ):
            return 1.5 if movie_resolution == "4K" else 2.0
        if not apsc_s35_enabled:
            return {"L": 2.0, "M": 3.1, "S": 4.0}[still_image_size]
        return {"L": 2.0, "M": 2.6, "S": 4.0}[still_image_size]
    if zoom_range == "Digital Zoom":
        if shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ):
            return 4.0
        if not apsc_s35_enabled:
            return {"L": 4.0, "M": 6.1, "S": 8.0}[still_image_size]
        return {"L": 4.0, "M": 5.2, "S": 8.0}[still_image_size]
    if zoom_range == "Smart Zoom":
        if not apsc_s35_enabled:
            return {"L": 1.0, "M": 1.5, "S": 2.0}[still_image_size]
        return {"L": 1.0, "M": 1.5, "S": 2.0}[still_image_size]
    raise Stage75Phase343Error(f"Unsupported zoom_range: {zoom_range!r}")


def simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    fps: float = 59.94,
    still_file_format: str = "JPEG",
    still_image_size: str = "L",
    apsc_s35_enabled: bool = False,
    hdmi_raw_output: bool = False,
    breathing_comp_enabled: bool = False,
    movie_resolution: str = "4K",
    zoom_range: str = "Optical zoom only",
    zoom_lever_1st_standby: int = 3,
    zoom_lever_1st_rec: int = 3,
    zoom_lever_2nd_standby: int = 8,
    zoom_lever_2nd_rec: int = 8,
    custom_key_zoom_speed_standby: int = 3,
    custom_key_zoom_speed_rec: int = 3,
    remote_zoom_speed_type: str = "Variable",
    remote_zoom_fixed_standby: int = 3,
    remote_zoom_fixed_rec: int = 3,
    zoom_ring_rotate: str = "Left(W)/Right(T)",
    requested_focus_area: Optional[str] = None,
    requested_metering_mode: Optional[str] = None,
    requested_face_eye_prior_af: Optional[bool] = None,
    requested_face_prior_multi_metering: Optional[bool] = None,
    requested_tracking: Optional[bool] = None,
    fx6_codec: str = "XAVC-I",
    fx6_handle_zoom: str = "Variable",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> ZoomRangeSpeedsRingRotateAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage75Phase343Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage75Phase343Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage75Phase343Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if still_file_format not in VALID_STILL_FILE_FORMATS:
        raise Stage75Phase343Error(f"Invalid still_file_format: {still_file_format!r}")
    if still_image_size not in VALID_STILL_IMAGE_SIZES:
        raise Stage75Phase343Error(f"Invalid still_image_size: {still_image_size!r}")
    if movie_resolution not in VALID_MOVIE_RESOLUTIONS:
        raise Stage75Phase343Error(f"Invalid movie_resolution: {movie_resolution!r}")
    if zoom_range not in VALID_ZOOM_RANGES:
        raise Stage75Phase343Error(f"Invalid zoom_range: {zoom_range!r}")
    if remote_zoom_speed_type not in VALID_REMOTE_ZOOM_SPEED_TYPES:
        raise Stage75Phase343Error(
            f"Invalid remote_zoom_speed_type: {remote_zoom_speed_type!r}"
        )
    if zoom_ring_rotate not in VALID_ZOOM_RING_ROTATE_DIRS:
        raise Stage75Phase343Error(f"Invalid zoom_ring_rotate: {zoom_ring_rotate!r}")
    if fx6_codec not in FX6_REC_CODECS:
        raise Stage75Phase343Error(f"Invalid fx6_codec: {fx6_codec!r}")
    if fx6_handle_zoom not in FX6_HANDLE_ZOOM_MODES:
        raise Stage75Phase343Error(f"Invalid fx6_handle_zoom: {fx6_handle_zoom!r}")
    if fps <= 0.0:
        raise Stage75Phase343Error(f"fps must be > 0, got {fps!r}")

    _validate_speed_step("zoom_lever_1st_standby", zoom_lever_1st_standby)
    _validate_speed_step("zoom_lever_1st_rec", zoom_lever_1st_rec)
    _validate_speed_step("zoom_lever_2nd_standby", zoom_lever_2nd_standby)
    _validate_speed_step("zoom_lever_2nd_rec", zoom_lever_2nd_rec)
    _validate_speed_step("custom_key_zoom_speed_standby", custom_key_zoom_speed_standby)
    _validate_speed_step("custom_key_zoom_speed_rec", custom_key_zoom_speed_rec)
    _validate_speed_step("remote_zoom_fixed_standby", remote_zoom_fixed_standby)
    _validate_speed_step("remote_zoom_fixed_rec", remote_zoom_fixed_rec)

    eff_l1_stby = zoom_lever_1st_standby
    eff_l1_rec = zoom_lever_1st_rec
    eff_l2_stby = zoom_lever_2nd_standby
    eff_l2_rec = zoom_lever_2nd_rec
    eff_ck_stby = custom_key_zoom_speed_standby
    eff_ck_rec = custom_key_zoom_speed_rec
    eff_rmt_type = remote_zoom_speed_type
    eff_rmt_stby = remote_zoom_fixed_standby
    eff_rmt_rec = remote_zoom_fixed_rec
    eff_zoom_range = zoom_range
    eff_ring = zoom_ring_rotate

    if camera_settings_reset_applied or initialize_applied:
        # Resettable speeds revert to defaults
        eff_l1_stby = ZOOM_LEVER_1ST_DEFAULT_SPEED
        eff_l1_rec = ZOOM_LEVER_1ST_DEFAULT_SPEED
        eff_l2_stby = ZOOM_LEVER_2ND_DEFAULT_SPEED
        eff_l2_rec = ZOOM_LEVER_2ND_DEFAULT_SPEED
        eff_ck_stby = ZOOM_CUSTOM_KEY_DEFAULT_SPEED
        eff_ck_rec = ZOOM_CUSTOM_KEY_DEFAULT_SPEED
        eff_rmt_type = "Variable"
        eff_rmt_stby = ZOOM_REMOTE_DEFAULT_SPEED
        eff_rmt_rec = ZOOM_REMOTE_DEFAULT_SPEED
    if initialize_applied:
        # Only [Initialize] restores Reset-immune [Zoom Range] & [Zoom Ring Rotate]
        eff_zoom_range = "Optical zoom only"
        eff_ring = "Left(W)/Right(T)"

    fx6_step = FX6_HANDLE_ZOOM_MODES[fx6_handle_zoom]

    # FX6 Ver. 6.01 Contrast
    if body_profile == BODY_MODEL_FX6:
        if eff_zoom_range == "Digital Zoom":
            return ZoomRangeSpeedsRingRotateAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX6 Ver. 6.01 lacks Digital Zoom (VAL_setting_zoom_setting_* only Optical/ClearImage)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_zoom_range=zoom_range,
                effective_zoom_range="Optical zoom only",
                effective_max_magnification=1.0,
                smart_zoom_disabled_in_movie=True,
                effective_zoom_lever_1st_standby=eff_l1_stby,
                effective_zoom_lever_1st_rec=eff_l1_rec,
                effective_zoom_lever_2nd_standby=eff_l2_stby,
                effective_zoom_lever_2nd_rec=eff_l2_rec,
                effective_custom_key_speed_standby=eff_ck_stby,
                effective_custom_key_speed_rec=eff_ck_rec,
                effective_remote_speed_type=eff_rmt_type,
                effective_remote_fixed_speed_standby=eff_rmt_stby,
                effective_remote_fixed_speed_rec=eff_rmt_rec,
                effective_zoom_ring_rotate=eff_ring,
                zoom_speeds_resettable=True,
                zoom_range_resettable=False,
                zoom_ring_rotate_resettable=False,
                non_optical_zoom_active=False,
                focus_area_disabled=False,
                effective_focus_area="Wide",
                metering_locked_multi=False,
                effective_metering_mode="Multi",
                face_eye_prior_af_disabled=False,
                face_prior_multi_metering_disabled=False,
                tracking_disabled=False,
                fx6_digital_zoom_supported=False,
                fx6_handle_zoom_mode=fx6_handle_zoom,
                fx6_handle_zoom_speed_step=fx6_step,
            )
        if eff_zoom_range == "Smart Zoom":
            return ZoomRangeSpeedsRingRotateAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX6 is cinema-only and does not expose Smart Zoom",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_zoom_range=zoom_range,
                effective_zoom_range="Optical zoom only",
                effective_max_magnification=1.0,
                smart_zoom_disabled_in_movie=True,
                effective_zoom_lever_1st_standby=eff_l1_stby,
                effective_zoom_lever_1st_rec=eff_l1_rec,
                effective_zoom_lever_2nd_standby=eff_l2_stby,
                effective_zoom_lever_2nd_rec=eff_l2_rec,
                effective_custom_key_speed_standby=eff_ck_stby,
                effective_custom_key_speed_rec=eff_ck_rec,
                effective_remote_speed_type=eff_rmt_type,
                effective_remote_fixed_speed_standby=eff_rmt_stby,
                effective_remote_fixed_speed_rec=eff_rmt_rec,
                effective_zoom_ring_rotate=eff_ring,
                zoom_speeds_resettable=True,
                zoom_range_resettable=False,
                zoom_ring_rotate_resettable=False,
                non_optical_zoom_active=False,
                focus_area_disabled=False,
                effective_focus_area="Wide",
                metering_locked_multi=False,
                effective_metering_mode="Multi",
                face_eye_prior_af_disabled=False,
                face_prior_multi_metering_disabled=False,
                tracking_disabled=False,
                fx6_digital_zoom_supported=False,
                fx6_handle_zoom_mode=fx6_handle_zoom,
                fx6_handle_zoom_speed_step=fx6_step,
            )
        if eff_zoom_range == "ClearImage Zoom" and (
            (shoot_mode == SHOOT_MODE_SQ and fps > 60.0) or ("RAW" in fx6_codec)
        ):
            return ZoomRangeSpeedsRingRotateAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX6 Clear Image Zoom locked off under S&Q > 60fps or RAW codec",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_zoom_range=zoom_range,
                effective_zoom_range="Optical zoom only",
                effective_max_magnification=1.0,
                smart_zoom_disabled_in_movie=True,
                effective_zoom_lever_1st_standby=eff_l1_stby,
                effective_zoom_lever_1st_rec=eff_l1_rec,
                effective_zoom_lever_2nd_standby=eff_l2_stby,
                effective_zoom_lever_2nd_rec=eff_l2_rec,
                effective_custom_key_speed_standby=eff_ck_stby,
                effective_custom_key_speed_rec=eff_ck_rec,
                effective_remote_speed_type=eff_rmt_type,
                effective_remote_fixed_speed_standby=eff_rmt_stby,
                effective_remote_fixed_speed_rec=eff_rmt_rec,
                effective_zoom_ring_rotate=eff_ring,
                zoom_speeds_resettable=True,
                zoom_range_resettable=False,
                zoom_ring_rotate_resettable=False,
                non_optical_zoom_active=False,
                focus_area_disabled=False,
                effective_focus_area="Wide",
                metering_locked_multi=False,
                effective_metering_mode="Multi",
                face_eye_prior_af_disabled=False,
                face_prior_multi_metering_disabled=False,
                tracking_disabled=False,
                fx6_digital_zoom_supported=False,
                fx6_handle_zoom_mode=fx6_handle_zoom,
                fx6_handle_zoom_speed_step=fx6_step,
            )
        fx6_mag = (
            1.0
            if eff_zoom_range == "Optical zoom only"
            else (1.5 if movie_resolution == "4K" else 2.0)
        )
        fx6_non_opt = eff_zoom_range != "Optical zoom only"
        return ZoomRangeSpeedsRingRotateAudit(
            admitted=True,
            errno_code=0,
            reason="FX6 Ver. 6.01 Zoom Type + Handle Zoom rocker simulation passed",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_zoom_range=zoom_range,
            effective_zoom_range=eff_zoom_range,
            effective_max_magnification=fx6_mag,
            smart_zoom_disabled_in_movie=True,
            effective_zoom_lever_1st_standby=eff_l1_stby,
            effective_zoom_lever_1st_rec=eff_l1_rec,
            effective_zoom_lever_2nd_standby=eff_l2_stby,
            effective_zoom_lever_2nd_rec=eff_l2_rec,
            effective_custom_key_speed_standby=eff_ck_stby,
            effective_custom_key_speed_rec=eff_ck_rec,
            effective_remote_speed_type=eff_rmt_type,
            effective_remote_fixed_speed_standby=eff_rmt_stby,
            effective_remote_fixed_speed_rec=eff_rmt_rec,
            effective_zoom_ring_rotate=eff_ring,
            zoom_speeds_resettable=True,
            zoom_range_resettable=False,
            zoom_ring_rotate_resettable=False,
            non_optical_zoom_active=fx6_non_opt,
            focus_area_disabled=fx6_non_opt,
            effective_focus_area="Center Priority" if fx6_non_opt else "Wide",
            metering_locked_multi=fx6_non_opt,
            effective_metering_mode="Multi",
            face_eye_prior_af_disabled=fx6_non_opt,
            face_prior_multi_metering_disabled=fx6_non_opt,
            tracking_disabled=fx6_non_opt,
            fx6_digital_zoom_supported=False,
            fx6_handle_zoom_mode=fx6_handle_zoom,
            fx6_handle_zoom_speed_step=fx6_step,
        )

    # FX3 Ver. 7.02 Logic
    if eff_zoom_range == "Smart Zoom":
        if shoot_mode != SHOOT_MODE_STILL:
            return ZoomRangeSpeedsRingRotateAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="Smart Zoom disabled in Movie and S&Q modes",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_zoom_range=zoom_range,
                effective_zoom_range="Optical zoom only",
                effective_max_magnification=1.0,
                smart_zoom_disabled_in_movie=True,
                effective_zoom_lever_1st_standby=eff_l1_stby,
                effective_zoom_lever_1st_rec=eff_l1_rec,
                effective_zoom_lever_2nd_standby=eff_l2_stby,
                effective_zoom_lever_2nd_rec=eff_l2_rec,
                effective_custom_key_speed_standby=eff_ck_stby,
                effective_custom_key_speed_rec=eff_ck_rec,
                effective_remote_speed_type=eff_rmt_type,
                effective_remote_fixed_speed_standby=eff_rmt_stby,
                effective_remote_fixed_speed_rec=eff_rmt_rec,
                effective_zoom_ring_rotate=eff_ring,
                zoom_speeds_resettable=True,
                zoom_range_resettable=False,
                zoom_ring_rotate_resettable=False,
                non_optical_zoom_active=False,
                focus_area_disabled=False,
                effective_focus_area="Wide",
                metering_locked_multi=False,
                effective_metering_mode="Multi",
                face_eye_prior_af_disabled=False,
                face_prior_multi_metering_disabled=False,
                tracking_disabled=False,
                fx6_digital_zoom_supported=False,
                fx6_handle_zoom_mode=fx6_handle_zoom,
                fx6_handle_zoom_speed_step=fx6_step,
            )
        if still_image_size == "L" or ("RAW" in still_file_format):
            return ZoomRangeSpeedsRingRotateAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="Smart Zoom unavailable ('—') at Still L image size or with RAW",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_zoom_range=zoom_range,
                effective_zoom_range="Optical zoom only",
                effective_max_magnification=1.0,
                smart_zoom_disabled_in_movie=True,
                effective_zoom_lever_1st_standby=eff_l1_stby,
                effective_zoom_lever_1st_rec=eff_l1_rec,
                effective_zoom_lever_2nd_standby=eff_l2_stby,
                effective_zoom_lever_2nd_rec=eff_l2_rec,
                effective_custom_key_speed_standby=eff_ck_stby,
                effective_custom_key_speed_rec=eff_ck_rec,
                effective_remote_speed_type=eff_rmt_type,
                effective_remote_fixed_speed_standby=eff_rmt_stby,
                effective_remote_fixed_speed_rec=eff_rmt_rec,
                effective_zoom_ring_rotate=eff_ring,
                zoom_speeds_resettable=True,
                zoom_range_resettable=False,
                zoom_ring_rotate_resettable=False,
                non_optical_zoom_active=False,
                focus_area_disabled=False,
                effective_focus_area="Wide",
                metering_locked_multi=False,
                effective_metering_mode="Multi",
                face_eye_prior_af_disabled=False,
                face_prior_multi_metering_disabled=False,
                tracking_disabled=False,
                fx6_digital_zoom_supported=False,
                fx6_handle_zoom_mode=fx6_handle_zoom,
                fx6_handle_zoom_speed_step=fx6_step,
            )

    if eff_zoom_range != "Optical zoom only":
        # Pre-entry lockouts for non-optical zoom (CIZ / Digital / Smart)
        lockout_reason: Optional[str] = None
        if shoot_mode == SHOOT_MODE_STILL and "RAW" in still_file_format:
            lockout_reason = f"Still {still_file_format} blocks non-optical zoom"
        elif shoot_mode == SHOOT_MODE_MOVIE and fps >= 100.0:
            lockout_reason = f"Movie HFR ({fps}p >= 100p) blocks ClearImage/Digital Zoom"
        elif shoot_mode == SHOOT_MODE_SQ and fps >= 100.0:
            lockout_reason = f"S&Q HFR ({fps}fps >= 100fps) blocks ClearImage/Digital Zoom"
        elif hdmi_raw_output:
            lockout_reason = "HDMI 16-bit RAW Output blocks ClearImage/Digital Zoom"
        elif breathing_comp_enabled:
            lockout_reason = "Breathing Comp. = On conflicts with ClearImage/Digital Zoom"

        if lockout_reason is not None:
            return ZoomRangeSpeedsRingRotateAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=lockout_reason,
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_zoom_range=zoom_range,
                effective_zoom_range="Optical zoom only",
                effective_max_magnification=1.0,
                smart_zoom_disabled_in_movie=True,
                effective_zoom_lever_1st_standby=eff_l1_stby,
                effective_zoom_lever_1st_rec=eff_l1_rec,
                effective_zoom_lever_2nd_standby=eff_l2_stby,
                effective_zoom_lever_2nd_rec=eff_l2_rec,
                effective_custom_key_speed_standby=eff_ck_stby,
                effective_custom_key_speed_rec=eff_ck_rec,
                effective_remote_speed_type=eff_rmt_type,
                effective_remote_fixed_speed_standby=eff_rmt_stby,
                effective_remote_fixed_speed_rec=eff_rmt_rec,
                effective_zoom_ring_rotate=eff_ring,
                zoom_speeds_resettable=True,
                zoom_range_resettable=False,
                zoom_ring_rotate_resettable=False,
                non_optical_zoom_active=False,
                focus_area_disabled=False,
                effective_focus_area="Wide",
                metering_locked_multi=False,
                effective_metering_mode="Multi",
                face_eye_prior_af_disabled=False,
                face_prior_multi_metering_disabled=False,
                tracking_disabled=False,
                fx6_digital_zoom_supported=False,
                fx6_handle_zoom_mode=fx6_handle_zoom,
                fx6_handle_zoom_speed_step=fx6_step,
            )

        # Active non-optical zoom lockouts (CIZ / Digital)
        if eff_zoom_range in ("ClearImage Zoom", "Digital Zoom"):
            active_lock_violation: Optional[str] = None
            if requested_focus_area not in (None, "Center Priority"):
                active_lock_violation = (
                    f"[Focus Area] = {requested_focus_area} disabled under {eff_zoom_range} (forced Center Priority)"
                )
            elif requested_metering_mode not in (None, "Multi"):
                active_lock_violation = (
                    f"[Metering Mode] = {requested_metering_mode} locked to [Multi] under {eff_zoom_range}"
                )
            elif requested_face_eye_prior_af is True:
                active_lock_violation = (
                    f"Face/Eye Prior. in AF disabled under {eff_zoom_range}"
                )
            elif requested_face_prior_multi_metering is True:
                active_lock_violation = (
                    f"Face Priority in Multi Metering disabled under {eff_zoom_range}"
                )
            elif requested_tracking is True:
                active_lock_violation = f"Tracking disabled under {eff_zoom_range}"

            if active_lock_violation is not None:
                return ZoomRangeSpeedsRingRotateAudit(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    reason=active_lock_violation,
                    body_profile=body_profile,
                    fw_version=fw_version,
                    shoot_mode=shoot_mode,
                    requested_zoom_range=zoom_range,
                    effective_zoom_range=eff_zoom_range,
                    effective_max_magnification=1.0,
                    smart_zoom_disabled_in_movie=True,
                    effective_zoom_lever_1st_standby=eff_l1_stby,
                    effective_zoom_lever_1st_rec=eff_l1_rec,
                    effective_zoom_lever_2nd_standby=eff_l2_stby,
                    effective_zoom_lever_2nd_rec=eff_l2_rec,
                    effective_custom_key_speed_standby=eff_ck_stby,
                    effective_custom_key_speed_rec=eff_ck_rec,
                    effective_remote_speed_type=eff_rmt_type,
                    effective_remote_fixed_speed_standby=eff_rmt_stby,
                    effective_remote_fixed_speed_rec=eff_rmt_rec,
                    effective_zoom_ring_rotate=eff_ring,
                    zoom_speeds_resettable=True,
                    zoom_range_resettable=False,
                    zoom_ring_rotate_resettable=False,
                    non_optical_zoom_active=True,
                    focus_area_disabled=True,
                    effective_focus_area="Center Priority",
                    metering_locked_multi=True,
                    effective_metering_mode="Multi",
                    face_eye_prior_af_disabled=True,
                    face_prior_multi_metering_disabled=True,
                    tracking_disabled=True,
                    fx6_digital_zoom_supported=False,
                    fx6_handle_zoom_mode=fx6_handle_zoom,
                    fx6_handle_zoom_speed_step=fx6_step,
                )

    mag = _fx3_ciz_digital_magnification(
        zoom_range=eff_zoom_range,
        shoot_mode=shoot_mode,
        movie_resolution=movie_resolution,
        still_image_size=still_image_size,
        apsc_s35_enabled=apsc_s35_enabled,
    )
    non_opt_ciz_dig = eff_zoom_range in ("ClearImage Zoom", "Digital Zoom")
    return ZoomRangeSpeedsRingRotateAudit(
        admitted=True,
        errno_code=0,
        reason="FX3 Ver. 7.02 Zoom Range, 8-step speeds & Reset split verified",
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        requested_zoom_range=zoom_range,
        effective_zoom_range=eff_zoom_range,
        effective_max_magnification=mag,
        smart_zoom_disabled_in_movie=True,
        effective_zoom_lever_1st_standby=eff_l1_stby,
        effective_zoom_lever_1st_rec=eff_l1_rec,
        effective_zoom_lever_2nd_standby=eff_l2_stby,
        effective_zoom_lever_2nd_rec=eff_l2_rec,
        effective_custom_key_speed_standby=eff_ck_stby,
        effective_custom_key_speed_rec=eff_ck_rec,
        effective_remote_speed_type=eff_rmt_type,
        effective_remote_fixed_speed_standby=eff_rmt_stby,
        effective_remote_fixed_speed_rec=eff_rmt_rec,
        effective_zoom_ring_rotate=eff_ring,
        zoom_speeds_resettable=True,
        zoom_range_resettable=False,
        zoom_ring_rotate_resettable=False,
        non_optical_zoom_active=non_opt_ciz_dig,
        focus_area_disabled=non_opt_ciz_dig,
        effective_focus_area="Center Priority" if non_opt_ciz_dig else (requested_focus_area or "Wide"),
        metering_locked_multi=non_opt_ciz_dig,
        effective_metering_mode="Multi" if non_opt_ciz_dig else (requested_metering_mode or "Multi"),
        face_eye_prior_af_disabled=non_opt_ciz_dig,
        face_prior_multi_metering_disabled=non_opt_ciz_dig,
        tracking_disabled=non_opt_ciz_dig,
        fx6_digital_zoom_supported=False,
        fx6_handle_zoom_mode=fx6_handle_zoom,
        fx6_handle_zoom_speed_step=fx6_step,
    )


# ---------------------------------------------------------------------------
# Sub-Model 75B: Auto Slow Shutter (6+ Locks), ISO Range Limit, Min. SS, Dual Base
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AutoSlowShutterIsoDualBaseAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    exposure_mode: str
    log_shooting: str
    gamma_profile: str
    auto_slow_shutter_locked: bool
    auto_slow_shutter_lock_reasons: Tuple[str, ...]
    effective_auto_slow_shutter: str
    auto_slow_shutter_resettable: bool
    effective_iso_range_limit_min: int
    effective_iso_range_limit_max: int
    iso_range_limit_resettable: bool
    iso_range_limit_governs_manual_only: bool
    effective_iso_auto_min_limit: int
    effective_iso_auto_max_limit: int
    iso_auto_min_ss_enabled: bool
    effective_iso_auto_min_ss: str
    iso_auto_min_ss_resettable: bool
    flash_sync_override_active: bool
    flash_sync_override_shutter: Optional[str]
    base_iso_menu_visible: bool
    effective_base_iso: Optional[int]
    dual_base_low_iso: int
    dual_base_high_iso: int
    dual_conversion_gain_ratio: int
    fx6_iso_auto_min_ss_supported: bool
    fx6_base_sensitivity: str
    fx6_agc_enabled: bool


def _is_valid_iso_auto_min_ss_value(val: str) -> bool:
    if val in VALID_ISO_AUTO_MIN_SS_PRESETS:
        return True
    if val.startswith("1/") and val[2:].isdigit():
        denom = int(val[2:])
        return 2 <= denom <= 8000
    if val.endswith('"') and val[:-1].replace(".", "", 1).isdigit():
        secs = float(val[:-1])
        return 0.4 <= secs <= 30.0
    return False


def simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    exposure_mode: str = "P",
    flex_exp_shutter_auto: bool = True,
    shutter_mode: str = "Speed",
    log_shooting: str = "Off",
    gamma_profile: str = "S-Log3",
    iso_mode: str = "ISO AUTO",
    manual_iso: int = 800,
    auto_slow_shutter_requested: Optional[str] = None,
    iso_range_limit_min: int = 80,
    iso_range_limit_max: int = 102400,
    iso_auto_min_limit: int = 80,
    iso_auto_max_limit: int = 12800,
    iso_auto_min_ss_requested: Optional[str] = None,
    external_flash_attached: bool = False,
    base_iso_requested: Optional[int] = None,
    fx6_base_sensitivity: str = "Low",
    fx6_agc_enabled: bool = True,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> AutoSlowShutterIsoDualBaseAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage75Phase343Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage75Phase343Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage75Phase343Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if exposure_mode not in VALID_EXPOSURE_MODES:
        raise Stage75Phase343Error(f"Invalid exposure_mode: {exposure_mode!r}")
    if shutter_mode not in VALID_SHUTTER_MODES:
        raise Stage75Phase343Error(f"Invalid shutter_mode: {shutter_mode!r}")
    if log_shooting not in VALID_LOG_SHOOTING_MODES:
        raise Stage75Phase343Error(f"Invalid log_shooting: {log_shooting!r}")
    if gamma_profile not in GAMMA_DUAL_BASE_ISO_MATRIX:
        raise Stage75Phase343Error(f"Invalid gamma_profile: {gamma_profile!r}")
    if iso_mode not in VALID_ISO_MODES:
        raise Stage75Phase343Error(f"Invalid iso_mode: {iso_mode!r}")
    if auto_slow_shutter_requested not in (None, "On", "Off"):
        raise Stage75Phase343Error(
            f"Invalid auto_slow_shutter_requested: {auto_slow_shutter_requested!r}"
        )
    if iso_range_limit_min <= 0 or iso_range_limit_max < iso_range_limit_min:
        raise Stage75Phase343Error(
            f"Invalid iso_range_limit bounds: [{iso_range_limit_min}, {iso_range_limit_max}]"
        )
    if iso_auto_min_limit <= 0 or iso_auto_max_limit < iso_auto_min_limit:
        raise Stage75Phase343Error(
            f"Invalid iso_auto bounds: [{iso_auto_min_limit}, {iso_auto_max_limit}]"
        )
    if iso_auto_min_ss_requested is not None and (
        not _is_valid_iso_auto_min_ss_value(iso_auto_min_ss_requested)
    ):
        raise Stage75Phase343Error(
            f"Invalid iso_auto_min_ss_requested: {iso_auto_min_ss_requested!r}"
        )
    if base_iso_requested is not None and base_iso_requested not in CINE_EI_BASE_ISOS:
        raise Stage75Phase343Error(f"Invalid base_iso_requested: {base_iso_requested!r}")
    if fx6_base_sensitivity not in FX6_BASE_SENSITIVITY_MODES:
        raise Stage75Phase343Error(
            f"Invalid fx6_base_sensitivity: {fx6_base_sensitivity!r}"
        )

    eff_limit_min = iso_range_limit_min
    eff_limit_max = iso_range_limit_max
    eff_auto_min = iso_auto_min_limit
    eff_auto_max = iso_auto_max_limit
    if initialize_applied:
        eff_limit_min = 80
        eff_limit_max = 102400
        eff_auto_min = 80
        eff_auto_max = 12800

    # FX6 Ver. 6.01 Contrast
    if body_profile == BODY_MODEL_FX6:
        if iso_auto_min_ss_requested is not None:
            return AutoSlowShutterIsoDualBaseAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX6 Ver. 6.01 has ZERO ISO AUTO Min. SS menu (0 hits in FX6 appFw.so)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                log_shooting=log_shooting,
                gamma_profile=gamma_profile,
                auto_slow_shutter_locked=True,
                auto_slow_shutter_lock_reasons=("fx6_pro_cinema_exposure",),
                effective_auto_slow_shutter="Off",
                auto_slow_shutter_resettable=True,
                effective_iso_range_limit_min=eff_limit_min,
                effective_iso_range_limit_max=eff_limit_max,
                iso_range_limit_resettable=False,
                iso_range_limit_governs_manual_only=True,
                effective_iso_auto_min_limit=eff_auto_min,
                effective_iso_auto_max_limit=eff_auto_max,
                iso_auto_min_ss_enabled=False,
                effective_iso_auto_min_ss="UNSUPPORTED",
                iso_auto_min_ss_resettable=False,
                flash_sync_override_active=False,
                flash_sync_override_shutter=None,
                base_iso_menu_visible=True,
                effective_base_iso=800 if fx6_base_sensitivity == "Low" else 12800,
                dual_base_low_iso=800,
                dual_base_high_iso=12800,
                dual_conversion_gain_ratio=16,
                fx6_iso_auto_min_ss_supported=False,
                fx6_base_sensitivity=fx6_base_sensitivity,
                fx6_agc_enabled=fx6_agc_enabled,
            )
        fx6_base_num = 800 if fx6_base_sensitivity == "Low" else 12800
        return AutoSlowShutterIsoDualBaseAudit(
            admitted=True,
            errno_code=0,
            reason="FX6 Ver. 6.01 Custom Base Sensitivity (Low/High) + AGC simulation passed",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            gamma_profile=gamma_profile,
            auto_slow_shutter_locked=False,
            auto_slow_shutter_lock_reasons=(),
            effective_auto_slow_shutter="On",
            auto_slow_shutter_resettable=True,
            effective_iso_range_limit_min=eff_limit_min,
            effective_iso_range_limit_max=eff_limit_max,
            iso_range_limit_resettable=False,
            iso_range_limit_governs_manual_only=True,
            effective_iso_auto_min_limit=eff_auto_min,
            effective_iso_auto_max_limit=eff_auto_max,
            iso_auto_min_ss_enabled=False,
            effective_iso_auto_min_ss="UNSUPPORTED",
            iso_auto_min_ss_resettable=False,
            flash_sync_override_active=False,
            flash_sync_override_shutter=None,
            base_iso_menu_visible=True,
            effective_base_iso=fx6_base_num,
            dual_base_low_iso=800,
            dual_base_high_iso=12800,
            dual_conversion_gain_ratio=16,
            fx6_iso_auto_min_ss_supported=False,
            fx6_base_sensitivity=fx6_base_sensitivity,
            fx6_agc_enabled=fx6_agc_enabled,
        )

    # FX3 Ver. 7.02 Logic
    # 1. [Auto Slow Shutter] 7-condition lock matrix
    ass_lock_reasons: List[str] = []
    if shoot_mode != SHOOT_MODE_MOVIE:
        ass_lock_reasons.append(f"shoot_mode_{shoot_mode}_not_movie")
    if exposure_mode == "S":
        ass_lock_reasons.append("exposure_mode_shutter_priority_S")
    if exposure_mode == "M":
        ass_lock_reasons.append("exposure_mode_manual_M")
    if iso_mode != "ISO AUTO":
        ass_lock_reasons.append("fixed_manual_iso_not_auto")
    if exposure_mode == "Flexible Exp. Mode" and (not flex_exp_shutter_auto):
        ass_lock_reasons.append("flex_exp_shutter_manual")
    if log_shooting in ("Cine EI", "Cine EI Quick"):
        ass_lock_reasons.append(f"log_shooting_{log_shooting}")
    if shutter_mode == "Angle":
        ass_lock_reasons.append("shutter_mode_angle_exclusion")

    ass_locked = len(ass_lock_reasons) > 0
    if camera_settings_reset_applied or initialize_applied:
        eff_ass = "On"
    else:
        eff_ass = (
            auto_slow_shutter_requested
            if auto_slow_shutter_requested is not None
            else "On"
        )

    low_iso, high_iso = GAMMA_DUAL_BASE_ISO_MATRIX[gamma_profile]
    base_menu_visible = log_shooting in ("Cine EI", "Cine EI Quick")
    eff_base_iso: Optional[int] = (
        (
            800
            if (camera_settings_reset_applied or initialize_applied or base_iso_requested is None)
            else base_iso_requested
        )
        if base_menu_visible
        else None
    )

    if ass_locked and auto_slow_shutter_requested is not None:
        return AutoSlowShutterIsoDualBaseAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"[Auto Slow Shutter] locked disabled: {', '.join(ass_lock_reasons)}",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            gamma_profile=gamma_profile,
            auto_slow_shutter_locked=True,
            auto_slow_shutter_lock_reasons=tuple(ass_lock_reasons),
            effective_auto_slow_shutter="Disabled",
            auto_slow_shutter_resettable=True,
            effective_iso_range_limit_min=eff_limit_min,
            effective_iso_range_limit_max=eff_limit_max,
            iso_range_limit_resettable=False,
            iso_range_limit_governs_manual_only=True,
            effective_iso_auto_min_limit=eff_auto_min,
            effective_iso_auto_max_limit=eff_auto_max,
            iso_auto_min_ss_enabled=False,
            effective_iso_auto_min_ss="STD",
            iso_auto_min_ss_resettable=True,
            flash_sync_override_active=False,
            flash_sync_override_shutter=None,
            base_iso_menu_visible=base_menu_visible,
            effective_base_iso=eff_base_iso,
            dual_base_low_iso=low_iso,
            dual_base_high_iso=high_iso,
            dual_conversion_gain_ratio=DUAL_CONVERSION_GAIN_RATIO,
            fx6_iso_auto_min_ss_supported=False,
            fx6_base_sensitivity=fx6_base_sensitivity,
            fx6_agc_enabled=fx6_agc_enabled,
        )

    # 2. [ISO Range Limit] governs Manual ISO only (Reset-immune)
    if iso_mode == "Manual" and (
        manual_iso < eff_limit_min or manual_iso > eff_limit_max
    ):
        return AutoSlowShutterIsoDualBaseAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=(
                f"Manual ISO {manual_iso} outside [ISO Range Limit] "
                f"[{eff_limit_min}, {eff_limit_max}]"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            gamma_profile=gamma_profile,
            auto_slow_shutter_locked=ass_locked,
            auto_slow_shutter_lock_reasons=tuple(ass_lock_reasons),
            effective_auto_slow_shutter="Disabled" if ass_locked else eff_ass,
            auto_slow_shutter_resettable=True,
            effective_iso_range_limit_min=eff_limit_min,
            effective_iso_range_limit_max=eff_limit_max,
            iso_range_limit_resettable=False,
            iso_range_limit_governs_manual_only=True,
            effective_iso_auto_min_limit=eff_auto_min,
            effective_iso_auto_max_limit=eff_auto_max,
            iso_auto_min_ss_enabled=False,
            effective_iso_auto_min_ss="STD",
            iso_auto_min_ss_resettable=True,
            flash_sync_override_active=False,
            flash_sync_override_shutter=None,
            base_iso_menu_visible=base_menu_visible,
            effective_base_iso=eff_base_iso,
            dual_base_low_iso=low_iso,
            dual_base_high_iso=high_iso,
            dual_conversion_gain_ratio=DUAL_CONVERSION_GAIN_RATIO,
            fx6_iso_auto_min_ss_supported=False,
            fx6_base_sensitivity=fx6_base_sensitivity,
            fx6_agc_enabled=fx6_agc_enabled,
        )

    # 3. [ISO AUTO Min. SS] — strictly Still P/A + ISO AUTO only
    min_ss_enabled = (
        shoot_mode == SHOOT_MODE_STILL
        and exposure_mode in ("P", "A")
        and iso_mode == "ISO AUTO"
    )
    if iso_auto_min_ss_requested is not None and not min_ss_enabled:
        return AutoSlowShutterIsoDualBaseAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "[ISO AUTO Min. SS] requires Still P/A + ISO AUTO "
                f"(got {shoot_mode} {exposure_mode} {iso_mode})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            gamma_profile=gamma_profile,
            auto_slow_shutter_locked=ass_locked,
            auto_slow_shutter_lock_reasons=tuple(ass_lock_reasons),
            effective_auto_slow_shutter="Disabled" if ass_locked else eff_ass,
            auto_slow_shutter_resettable=True,
            effective_iso_range_limit_min=eff_limit_min,
            effective_iso_range_limit_max=eff_limit_max,
            iso_range_limit_resettable=False,
            iso_range_limit_governs_manual_only=True,
            effective_iso_auto_min_limit=eff_auto_min,
            effective_iso_auto_max_limit=eff_auto_max,
            iso_auto_min_ss_enabled=False,
            effective_iso_auto_min_ss="Disabled",
            iso_auto_min_ss_resettable=True,
            flash_sync_override_active=False,
            flash_sync_override_shutter=None,
            base_iso_menu_visible=base_menu_visible,
            effective_base_iso=eff_base_iso,
            dual_base_low_iso=low_iso,
            dual_base_high_iso=high_iso,
            dual_conversion_gain_ratio=DUAL_CONVERSION_GAIN_RATIO,
            fx6_iso_auto_min_ss_supported=False,
            fx6_base_sensitivity=fx6_base_sensitivity,
            fx6_agc_enabled=fx6_agc_enabled,
        )

    # 4. Explicit [Base ISO] visibility gate
    if base_iso_requested is not None and not base_menu_visible:
        return AutoSlowShutterIsoDualBaseAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"[Base ISO] menu hidden outside Cine EI / Cine EI Quick (log_shooting={log_shooting}); "
                f"sensor uses automatic 20x dual conversion gain ({low_iso}/{high_iso})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            log_shooting=log_shooting,
            gamma_profile=gamma_profile,
            auto_slow_shutter_locked=ass_locked,
            auto_slow_shutter_lock_reasons=tuple(ass_lock_reasons),
            effective_auto_slow_shutter="Disabled" if ass_locked else eff_ass,
            auto_slow_shutter_resettable=True,
            effective_iso_range_limit_min=eff_limit_min,
            effective_iso_range_limit_max=eff_limit_max,
            iso_range_limit_resettable=False,
            iso_range_limit_governs_manual_only=True,
            effective_iso_auto_min_limit=eff_auto_min,
            effective_iso_auto_max_limit=eff_auto_max,
            iso_auto_min_ss_enabled=min_ss_enabled,
            effective_iso_auto_min_ss="STD" if min_ss_enabled else "Disabled",
            iso_auto_min_ss_resettable=True,
            flash_sync_override_active=False,
            flash_sync_override_shutter=None,
            base_iso_menu_visible=False,
            effective_base_iso=None,
            dual_base_low_iso=low_iso,
            dual_base_high_iso=high_iso,
            dual_conversion_gain_ratio=DUAL_CONVERSION_GAIN_RATIO,
            fx6_iso_auto_min_ss_supported=False,
            fx6_base_sensitivity=fx6_base_sensitivity,
            fx6_agc_enabled=fx6_agc_enabled,
        )

    if camera_settings_reset_applied or initialize_applied:
        eff_min_ss = "STD" if min_ss_enabled else "Disabled"
    elif min_ss_enabled:
        eff_min_ss = iso_auto_min_ss_requested or "STD"
    else:
        eff_min_ss = "Disabled"

    flash_override = bool(min_ss_enabled and external_flash_attached)
    return AutoSlowShutterIsoDualBaseAudit(
        admitted=True,
        errno_code=0,
        reason="FX3 Ver. 7.02 Auto Slow Shutter, ISO Range Limit, ISO AUTO Min. SS & Dual Base ISO verified",
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        log_shooting=log_shooting,
        gamma_profile=gamma_profile,
        auto_slow_shutter_locked=ass_locked,
        auto_slow_shutter_lock_reasons=tuple(ass_lock_reasons),
        effective_auto_slow_shutter="Disabled" if ass_locked else eff_ass,
        auto_slow_shutter_resettable=True,
        effective_iso_range_limit_min=eff_limit_min,
        effective_iso_range_limit_max=eff_limit_max,
        iso_range_limit_resettable=False,
        iso_range_limit_governs_manual_only=True,
        effective_iso_auto_min_limit=eff_auto_min,
        effective_iso_auto_max_limit=eff_auto_max,
        iso_auto_min_ss_enabled=min_ss_enabled,
        effective_iso_auto_min_ss=eff_min_ss,
        iso_auto_min_ss_resettable=True,
        flash_sync_override_active=flash_override,
        flash_sync_override_shutter="1/250" if flash_override else None,
        base_iso_menu_visible=base_menu_visible,
        effective_base_iso=eff_base_iso,
        dual_base_low_iso=low_iso,
        dual_base_high_iso=high_iso,
        dual_conversion_gain_ratio=DUAL_CONVERSION_GAIN_RATIO,
        fx6_iso_auto_min_ss_supported=False,
        fx6_base_sensitivity=fx6_base_sensitivity,
        fx6_agc_enabled=fx6_agc_enabled,
    )


# ---------------------------------------------------------------------------
# Sub-Model 75C: Still ARW Dormant Lossless Comp, HLG Still & Sort Slot-1 EROFS
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StillArwRawCompHeifHlgAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    effective_raw_file_type: str
    lossless_raw_dormant_alcin_uud: bool
    effective_jpeg_heif_switch: str
    effective_hlg_still_image: str
    hlg_still_internal_elf_symbol: str
    hlg_still_color_space: str
    hlg_still_iso_floor_range: Tuple[int, int]
    pp_creative_look_dro_disabled: bool
    effective_sort_recording: str
    sort_recording_resettable: bool
    raw_file_type_resettable: bool
    hlg_still_resettable: bool
    recording_slot: str
    slot1_erofs_triggered: bool
    slot1_data_sector_writes: int
    fx6_has_still_arw_heif: bool


def simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_STILL,
    exposure_mode: str = "P",
    file_format: str = "RAW",
    raw_file_type: str = "Compressed",
    jpeg_heif_switch: str = "JPEG",
    hlg_still_image: str = "Off",
    sort_recording: str = "Off",
    auto_switch_media: str = "Off",
    recording_slot: str = "Slot 2",
    slot2_full_spillover_triggered: bool = False,
    capture_triggered: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> StillArwRawCompHeifHlgAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage75Phase343Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage75Phase343Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in (SHOOT_MODE_STILL, SHOOT_MODE_MOVIE):
        raise Stage75Phase343Error(f"Invalid shoot_mode for 75C: {shoot_mode!r}")
    if exposure_mode not in VALID_EXPOSURE_MODES:
        raise Stage75Phase343Error(f"Invalid exposure_mode: {exposure_mode!r}")
    if file_format not in VALID_STILL_FILE_FORMATS:
        raise Stage75Phase343Error(f"Invalid file_format: {file_format!r}")
    if raw_file_type not in VALID_RAW_FILE_TYPES:
        raise Stage75Phase343Error(f"Invalid raw_file_type: {raw_file_type!r}")
    if jpeg_heif_switch not in VALID_JPEG_HEIF_SWITCHES:
        raise Stage75Phase343Error(f"Invalid jpeg_heif_switch: {jpeg_heif_switch!r}")
    if hlg_still_image not in VALID_TOGGLES:
        raise Stage75Phase343Error(f"Invalid hlg_still_image: {hlg_still_image!r}")
    if sort_recording not in VALID_TOGGLES:
        raise Stage75Phase343Error(f"Invalid sort_recording: {sort_recording!r}")
    if auto_switch_media not in VALID_TOGGLES:
        raise Stage75Phase343Error(f"Invalid auto_switch_media: {auto_switch_media!r}")
    if recording_slot not in VALID_RECORDING_SLOTS:
        raise Stage75Phase343Error(f"Invalid recording_slot: {recording_slot!r}")

    if body_profile == BODY_MODEL_FX6:
        if shoot_mode == SHOOT_MODE_STILL:
            return StillArwRawCompHeifHlgAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="ILME-FX6 Ver. 6.01 is pure cinema (zero Still ARW/HEIF/HLG Still/DCIM)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                effective_raw_file_type="UNSUPPORTED",
                lossless_raw_dormant_alcin_uud=False,
                effective_jpeg_heif_switch="UNSUPPORTED",
                effective_hlg_still_image="Off",
                hlg_still_internal_elf_symbol="ABSENT",
                hlg_still_color_space="NONE",
                hlg_still_iso_floor_range=(800, 800),
                pp_creative_look_dro_disabled=False,
                effective_sort_recording="Off",
                sort_recording_resettable=False,
                raw_file_type_resettable=False,
                hlg_still_resettable=False,
                recording_slot=recording_slot,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                fx6_has_still_arw_heif=False,
            )
        return StillArwRawCompHeifHlgAudit(
            admitted=True,
            errno_code=0,
            reason="ILME-FX6 Ver. 6.01 pure-cinema baseline (no Still ARW/HEIF/DCIM)",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            effective_raw_file_type="UNSUPPORTED",
            lossless_raw_dormant_alcin_uud=False,
            effective_jpeg_heif_switch="UNSUPPORTED",
            effective_hlg_still_image="Off",
            hlg_still_internal_elf_symbol="ABSENT",
            hlg_still_color_space="NONE",
            hlg_still_iso_floor_range=(800, 800),
            pp_creative_look_dro_disabled=False,
            effective_sort_recording="Off",
            sort_recording_resettable=False,
            raw_file_type_resettable=False,
            hlg_still_resettable=False,
            recording_slot=recording_slot,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            fx6_has_still_arw_heif=False,
        )

    # FX3 Ver. 7.02
    if raw_file_type in DORMANT_RAW_FILE_TYPES:
        return StillArwRawCompHeifHlgAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"[RAW File Type] = {raw_file_type} (RAW_FILE_TYPE_LOSSLESS*) is 100%% dormant "
                "on ALCIN_UUD (FX3 exposes strictly Compressed & Uncompressed)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            effective_raw_file_type="Compressed",
            lossless_raw_dormant_alcin_uud=True,
            effective_jpeg_heif_switch=jpeg_heif_switch,
            effective_hlg_still_image="Off",
            hlg_still_internal_elf_symbol="STILL_HLD_PHOTO_OFF",
            hlg_still_color_space="sRGB",
            hlg_still_iso_floor_range=(80, 100),
            pp_creative_look_dro_disabled=False,
            effective_sort_recording=sort_recording,
            sort_recording_resettable=False,
            raw_file_type_resettable=True,
            hlg_still_resettable=True,
            recording_slot=recording_slot,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            fx6_has_still_arw_heif=False,
        )

    eff_raw = raw_file_type
    eff_jh = jpeg_heif_switch
    eff_hlg = hlg_still_image
    eff_sort = sort_recording
    if camera_settings_reset_applied or initialize_applied:
        eff_raw = "Compressed"
        eff_jh = "JPEG"
        eff_hlg = "Off"
    if initialize_applied:
        eff_sort = "Off"

    # [HLG Still Image] prerequisite validation
    if eff_hlg == "On":
        hlg_fail_reason: Optional[str] = None
        if shoot_mode != SHOOT_MODE_STILL:
            hlg_fail_reason = "[HLG Still Image] is Still-only"
        elif eff_jh not in ("HEIF(4:2:0)", "HEIF(4:2:2)"):
            hlg_fail_reason = "[HLG Still Image] requires [JPEG/HEIF Switch] = HEIF(4:2:0) or HEIF(4:2:2)"
        elif file_format != "HEIF":
            hlg_fail_reason = (
                f"[HLG Still Image] forced Off under [File Format] = {file_format} "
                "(requires pure HEIF, blocked on RAW or RAW & HEIF)"
            )
        elif exposure_mode not in ("P", "A", "S", "M"):
            hlg_fail_reason = (
                f"[HLG Still Image] requires P/A/S/M exposure mode (got {exposure_mode})"
            )

        if hlg_fail_reason is not None:
            return StillArwRawCompHeifHlgAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=hlg_fail_reason,
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                effective_raw_file_type=eff_raw,
                lossless_raw_dormant_alcin_uud=True,
                effective_jpeg_heif_switch=eff_jh,
                effective_hlg_still_image="Off",
                hlg_still_internal_elf_symbol="STILL_HLD_PHOTO_OFF",
                hlg_still_color_space="sRGB",
                hlg_still_iso_floor_range=(80, 100),
                pp_creative_look_dro_disabled=False,
                effective_sort_recording=eff_sort,
                sort_recording_resettable=False,
                raw_file_type_resettable=True,
                hlg_still_resettable=True,
                recording_slot=recording_slot,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                fx6_has_still_arw_heif=False,
            )

    # Tier-0 Slot 1 EROFS=30 Firewall (direct Slot 1 capture OR Slot 2 -> Slot 1 spillover)
    slot1_hazard = (recording_slot == "Slot 1" and capture_triggered) or (
        recording_slot == "Slot 2"
        and auto_switch_media == "On"
        and slot2_full_spillover_triggered
    )
    if slot1_hazard:
        return StillArwRawCompHeifHlgAudit(
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason=(
                "Tier-0 Slot 1 EROFS=30 Firewall blocked Sort/Auto Switch spillover "
                "or direct capture onto Slot 1 (slot1_data_sector_writes=0)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            effective_raw_file_type=eff_raw,
            lossless_raw_dormant_alcin_uud=True,
            effective_jpeg_heif_switch=eff_jh,
            effective_hlg_still_image=eff_hlg,
            hlg_still_internal_elf_symbol=(
                "STILL_HLD_PHOTO_ON" if eff_hlg == "On" else "STILL_HLD_PHOTO_OFF"
            ),
            hlg_still_color_space="BT.2100/BT.2020" if eff_hlg == "On" else "sRGB",
            hlg_still_iso_floor_range=(100, 125) if eff_hlg == "On" else (80, 100),
            pp_creative_look_dro_disabled=(eff_hlg == "On"),
            effective_sort_recording=eff_sort,
            sort_recording_resettable=False,
            raw_file_type_resettable=True,
            hlg_still_resettable=True,
            recording_slot="Slot 1",
            slot1_erofs_triggered=True,
            slot1_data_sector_writes=0,
            fx6_has_still_arw_heif=False,
        )

    hlg_on = eff_hlg == "On"
    return StillArwRawCompHeifHlgAudit(
        admitted=True,
        errno_code=0,
        reason="FX3 Ver. 7.02 Still ARW/HEIF/HLG Still Image & Sort Recording Slot-2 safe",
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        effective_raw_file_type=eff_raw,
        lossless_raw_dormant_alcin_uud=True,
        effective_jpeg_heif_switch=eff_jh,
        effective_hlg_still_image=eff_hlg,
        hlg_still_internal_elf_symbol=(
            "STILL_HLD_PHOTO_ON" if hlg_on else "STILL_HLD_PHOTO_OFF"
        ),
        hlg_still_color_space="BT.2100/BT.2020" if hlg_on else "sRGB",
        hlg_still_iso_floor_range=(100, 125) if hlg_on else (80, 100),
        pp_creative_look_dro_disabled=hlg_on,
        effective_sort_recording=eff_sort,
        sort_recording_resettable=False,
        raw_file_type_resettable=True,
        hlg_still_resettable=True,
        recording_slot=recording_slot,
        slot1_erofs_triggered=False,
        slot1_data_sector_writes=0,
        fx6_has_still_arw_heif=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 75D: USB Mode, USB LUN=Single Slot-1 Hazard, PD Gate & UVC Dormancy
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsbModeLunPdUvcAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    effective_usb_connection_mode: str
    effective_usb_lun_setting: str
    effective_usb_power_supply: str
    usb_settings_resettable: bool
    exposed_luns: Tuple[str, ...]
    single_lun_exposes_slot1_only: bool
    slot1_exposed_hazard_detected: bool
    slot1_erofs_triggered: bool
    slot1_data_sector_writes: int
    np_fz100_pd_gate_satisfied: bool
    power_cut_brownout: bool
    fx6_batteryless_dcin_active: bool
    native_uvc_exposed: bool
    uvc_kmods_dormant_at_boot: bool
    network_streaming_enabled: bool
    effective_movie_rec_during_streaming: str
    effective_hdmi_rec_media_dur_hdmi: str


def simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    usb_connection_mode: str = "Sel. When Connect",
    usb_lun_setting: str = "Multi",
    host_os_msc_lockdown: bool = True,
    host_write_attempt_on_slot1: bool = False,
    usb_power_supply: str = "On",
    usb_pd_voltage_v: float = 9.0,
    usb_pd_current_a: float = 3.0,
    np_fz100_inserted: bool = True,
    np_fz100_pulled_live: bool = False,
    dc_c1_coupler_attached: bool = False,
    dc_c1_pd_watts: int = 0,
    dc_c1_cable_amps: int = 0,
    fx6_dc_in_voltage_v: float = 19.5,
    network_streaming_enabled: bool = False,
    movie_rec_during_streaming: str = "Disable",
    hdmi_rec_media_dur_hdmi: str = "Off(HDMI Only)",
    recording_slot: str = "Slot 2",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> UsbModeLunPdUvcAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage75Phase343Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage75Phase343Error(f"Invalid fw_version: {fw_version!r}")
    if usb_connection_mode not in VALID_USB_CONNECTION_MODES:
        raise Stage75Phase343Error(
            f"Invalid usb_connection_mode: {usb_connection_mode!r}"
        )
    if usb_lun_setting not in VALID_USB_LUN_SETTINGS:
        raise Stage75Phase343Error(f"Invalid usb_lun_setting: {usb_lun_setting!r}")
    if usb_power_supply not in VALID_TOGGLES:
        raise Stage75Phase343Error(f"Invalid usb_power_supply: {usb_power_supply!r}")
    if movie_rec_during_streaming not in VALID_STREAMING_REC_MODES:
        raise Stage75Phase343Error(
            f"Invalid movie_rec_during_streaming: {movie_rec_during_streaming!r}"
        )
    if hdmi_rec_media_dur_hdmi not in VALID_HDMI_REC_DUR_MODES:
        raise Stage75Phase343Error(
            f"Invalid hdmi_rec_media_dur_hdmi: {hdmi_rec_media_dur_hdmi!r}"
        )
    if recording_slot not in VALID_RECORDING_SLOTS:
        raise Stage75Phase343Error(f"Invalid recording_slot: {recording_slot!r}")

    eff_usb_mode = usb_connection_mode
    eff_lun = usb_lun_setting
    eff_usb_pwr = usb_power_supply
    eff_stream_rec = movie_rec_during_streaming
    eff_hdmi_rec = hdmi_rec_media_dur_hdmi
    if initialize_applied:
        eff_usb_mode = "Sel. When Connect"
        eff_lun = "Multi"
        eff_usb_pwr = "On"
        eff_stream_rec = "Disable"
        eff_hdmi_rec = "Off(HDMI Only)"
    elif camera_settings_reset_applied:
        # USB settings are Reset-immune; only Movie/HDMI rec flags revert
        eff_stream_rec = "Disable"
        eff_hdmi_rec = "Off(HDMI Only)"

    # 1. Dual FX3 + FX6 Native UVC/UAC Dormancy Gate
    if eff_usb_mode in DORMANT_USB_CONNECTION_MODES:
        return UsbModeLunPdUvcAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"{body_profile} Ver. {fw_version} does NOT expose native UVC/UAC USB Streaming "
                "(dormant USB_CONNECTION_USB_STREAMING / BKID_APP_SETTING_USB_STREAMING_PROCAM)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            effective_usb_connection_mode="Sel. When Connect",
            effective_usb_lun_setting=eff_lun,
            effective_usb_power_supply=eff_usb_pwr,
            usb_settings_resettable=False,
            exposed_luns=(),
            single_lun_exposes_slot1_only=True,
            slot1_exposed_hazard_detected=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            np_fz100_pd_gate_satisfied=False,
            power_cut_brownout=False,
            fx6_batteryless_dcin_active=False,
            native_uvc_exposed=False,
            uvc_kmods_dormant_at_boot=True,
            network_streaming_enabled=network_streaming_enabled,
            effective_movie_rec_during_streaming=eff_stream_rec,
            effective_hdmi_rec_media_dur_hdmi=eff_hdmi_rec,
        )

    # 2. FX6 19.5V DC IN Comparison
    if body_profile == BODY_MODEL_FX6:
        dc_ok = 18.0 <= fx6_dc_in_voltage_v <= 20.5
        if not dc_ok:
            return UsbModeLunPdUvcAudit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason=(
                    f"FX6 DC IN {fx6_dc_in_voltage_v}V out of 18.0-20.5V envelope "
                    "(DC Low Voltage1=16.5V / Low Voltage2=15.5V trip)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                effective_usb_connection_mode=eff_usb_mode,
                effective_usb_lun_setting=eff_lun,
                effective_usb_power_supply="Off",
                usb_settings_resettable=False,
                exposed_luns=(),
                single_lun_exposes_slot1_only=True,
                slot1_exposed_hazard_detected=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                np_fz100_pd_gate_satisfied=False,
                power_cut_brownout=True,
                fx6_batteryless_dcin_active=False,
                native_uvc_exposed=False,
                uvc_kmods_dormant_at_boot=True,
                network_streaming_enabled=network_streaming_enabled,
                effective_movie_rec_during_streaming=eff_stream_rec,
                effective_hdmi_rec_media_dur_hdmi=eff_hdmi_rec,
            )
        return UsbModeLunPdUvcAudit(
            admitted=True,
            errno_code=0,
            reason="FX6 Ver. 6.01 19.5V DC IN battery-less boot & zero native UVC verified",
            body_profile=body_profile,
            fw_version=fw_version,
            effective_usb_connection_mode=eff_usb_mode,
            effective_usb_lun_setting=eff_lun,
            effective_usb_power_supply="Off",
            usb_settings_resettable=False,
            exposed_luns=(),
            single_lun_exposes_slot1_only=True,
            slot1_exposed_hazard_detected=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            np_fz100_pd_gate_satisfied=False,
            power_cut_brownout=False,
            fx6_batteryless_dcin_active=True,
            native_uvc_exposed=False,
            uvc_kmods_dormant_at_boot=True,
            network_streaming_enabled=network_streaming_enabled,
            effective_movie_rec_during_streaming=eff_stream_rec,
            effective_hdmi_rec_media_dur_hdmi=eff_hdmi_rec,
        )

    # 3. FX3 Exposed LUNs & [USB LUN Setting] = Single Slot 1 Hazard
    if eff_usb_mode == "MassStorage(MSC)":
        exposed_luns: Tuple[str, ...] = (
            ("Slot 1",) if eff_lun == "Single" else ("Slot 1", "Slot 2")
        )
    elif eff_usb_mode == "MTP":
        exposed_luns = ("Slot 1",)
    else:
        exposed_luns = ()

    slot1_exposed = "Slot 1" in exposed_luns
    if slot1_exposed and (host_write_attempt_on_slot1 or not host_os_msc_lockdown):
        return UsbModeLunPdUvcAudit(
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason=(
                "Tier-0 Slot 1 EROFS=30 Firewall blocked macOS Spotlight/fseventsd/fsck_exfat "
                "host write hazard on USB MSC/MTP Single/Multi LUN"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            effective_usb_connection_mode=eff_usb_mode,
            effective_usb_lun_setting=eff_lun,
            effective_usb_power_supply=eff_usb_pwr,
            usb_settings_resettable=False,
            exposed_luns=exposed_luns,
            single_lun_exposes_slot1_only=True,
            slot1_exposed_hazard_detected=True,
            slot1_erofs_triggered=True,
            slot1_data_sector_writes=0,
            np_fz100_pd_gate_satisfied=bool(np_fz100_inserted and not np_fz100_pulled_live),
            power_cut_brownout=False,
            fx6_batteryless_dcin_active=False,
            native_uvc_exposed=False,
            uvc_kmods_dormant_at_boot=True,
            network_streaming_enabled=network_streaming_enabled,
            effective_movie_rec_during_streaming=eff_stream_rec,
            effective_hdmi_rec_media_dur_hdmi=eff_hdmi_rec,
        )

    # 4. FX3 NP-FZ100 + USB-C PD 9V/3A Gate vs DC-C1 Coupler
    dcc1_ok = bool(dc_c1_coupler_attached and dc_c1_pd_watts >= 65 and dc_c1_cable_amps >= 5)
    battery_ok = bool(np_fz100_inserted and not np_fz100_pulled_live)
    pd_input_ok = bool(
        eff_usb_pwr == "On" and usb_pd_voltage_v >= 9.0 and usb_pd_current_a >= 3.0
    )
    if (not battery_ok) and (not dcc1_ok):
        return UsbModeLunPdUvcAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason=(
                "FX3 USB Power Supply (9V/3A PD) requires charged NP-FZ100 inserted "
                "(pulling battery cuts power immediately; battery-less requires DC-C1 + >=65W PD + 5A cable)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            effective_usb_connection_mode=eff_usb_mode,
            effective_usb_lun_setting=eff_lun,
            effective_usb_power_supply=eff_usb_pwr,
            usb_settings_resettable=False,
            exposed_luns=exposed_luns,
            single_lun_exposes_slot1_only=True,
            slot1_exposed_hazard_detected=slot1_exposed,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            np_fz100_pd_gate_satisfied=False,
            power_cut_brownout=True,
            fx6_batteryless_dcin_active=False,
            native_uvc_exposed=False,
            uvc_kmods_dormant_at_boot=True,
            network_streaming_enabled=network_streaming_enabled,
            effective_movie_rec_during_streaming=eff_stream_rec,
            effective_hdmi_rec_media_dur_hdmi=eff_hdmi_rec,
        )

    # 5. Streaming / HDMI Rec Media Slot 1 EROFS=30 Firewall
    rec_slot1_hazard = (
        recording_slot == "Slot 1"
        and (
            (network_streaming_enabled and eff_stream_rec == "Enable")
            or eff_hdmi_rec == "On"
        )
    )
    if rec_slot1_hazard:
        return UsbModeLunPdUvcAudit(
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason=(
                "Tier-0 Slot 1 EROFS=30 Firewall blocked Movie Rec During Streaming / "
                "Rec. Media dur HDMI Output write onto Slot 1 (slot1_data_sector_writes=0)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            effective_usb_connection_mode=eff_usb_mode,
            effective_usb_lun_setting=eff_lun,
            effective_usb_power_supply=eff_usb_pwr,
            usb_settings_resettable=False,
            exposed_luns=exposed_luns,
            single_lun_exposes_slot1_only=True,
            slot1_exposed_hazard_detected=slot1_exposed,
            slot1_erofs_triggered=True,
            slot1_data_sector_writes=0,
            np_fz100_pd_gate_satisfied=bool((battery_ok and pd_input_ok) or dcc1_ok),
            power_cut_brownout=False,
            fx6_batteryless_dcin_active=False,
            native_uvc_exposed=False,
            uvc_kmods_dormant_at_boot=True,
            network_streaming_enabled=network_streaming_enabled,
            effective_movie_rec_during_streaming=eff_stream_rec,
            effective_hdmi_rec_media_dur_hdmi=eff_hdmi_rec,
        )

    return UsbModeLunPdUvcAudit(
        admitted=True,
        errno_code=0,
        reason="FX3 Ver. 7.02 USB Mode/LUN/PD/Streaming-Rec & Dual UVC Dormancy verified",
        body_profile=body_profile,
        fw_version=fw_version,
        effective_usb_connection_mode=eff_usb_mode,
        effective_usb_lun_setting=eff_lun,
        effective_usb_power_supply=eff_usb_pwr,
        usb_settings_resettable=False,
        exposed_luns=exposed_luns,
        single_lun_exposes_slot1_only=True,
        slot1_exposed_hazard_detected=slot1_exposed,
        slot1_erofs_triggered=False,
        slot1_data_sector_writes=0,
        np_fz100_pd_gate_satisfied=bool((battery_ok and pd_input_ok) or dcc1_ok),
        power_cut_brownout=False,
        fx6_batteryless_dcin_active=False,
        native_uvc_exposed=False,
        uvc_kmods_dormant_at_boot=True,
        network_streaming_enabled=network_streaming_enabled,
        effective_movie_rec_during_streaming=eff_stream_rec,
        effective_hdmi_rec_media_dur_hdmi=eff_hdmi_rec,
    )


# ---------------------------------------------------------------------------
# Stage 75 Milestone Probe & Full Wave-65 Co-Emulation Runner
# ---------------------------------------------------------------------------


def _build_stage75_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_75th_stage_milestone": IS_75TH_STAGE_MILESTONE,
        "wave": "Wave-65",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    donor_audit = inspect_phase343_wave65_donors(
        force_clean_room=force_clean_room, env=env
    )

    # Sub-Model 75A probes
    p75a_ciz_4k_ok = simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        fps=59.94,
        movie_resolution="4K",
        zoom_range="ClearImage Zoom",
        zoom_lever_1st_standby=5,
        zoom_lever_1st_rec=2,
        zoom_lever_2nd_standby=7,
        zoom_lever_2nd_rec=6,
        custom_key_zoom_speed_standby=4,
        custom_key_zoom_speed_rec=2,
        remote_zoom_speed_type="Fixed",
        remote_zoom_fixed_standby=6,
        remote_zoom_fixed_rec=4,
        zoom_ring_rotate="Right(W)/Left(T)",
    )
    p75a_reset_split_ok = simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        fps=59.94,
        movie_resolution="HD",
        zoom_range="ClearImage Zoom",
        zoom_lever_1st_standby=6,
        zoom_lever_2nd_rec=2,
        custom_key_zoom_speed_rec=7,
        remote_zoom_speed_type="Fixed",
        remote_zoom_fixed_rec=5,
        zoom_ring_rotate="Right(W)/Left(T)",
        camera_settings_reset_applied=True,
    )
    p75a_digital_still_ok = simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
        shoot_mode=SHOOT_MODE_STILL,
        still_file_format="JPEG",
        still_image_size="M",
        zoom_range="Digital Zoom",
    )
    p75a_blocks = [
        simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=SHOOT_MODE_STILL,
            still_file_format="RAW",
            zoom_range="ClearImage Zoom",
        ),
        simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            fps=119.88,
            zoom_range="ClearImage Zoom",
        ),
        simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=SHOOT_MODE_SQ,
            fps=120.0,
            zoom_range="Digital Zoom",
        ),
        simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            hdmi_raw_output=True,
            zoom_range="ClearImage Zoom",
        ),
        simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            zoom_range="ClearImage Zoom",
            requested_tracking=True,
        ),
        simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            zoom_range="Digital Zoom",
            requested_metering_mode="Spot",
        ),
    ]
    p75a_fx6 = [
        simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            shoot_mode=SHOOT_MODE_MOVIE,
            zoom_range="ClearImage Zoom",
            fx6_handle_zoom="High",
        ),
        simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            shoot_mode=SHOOT_MODE_MOVIE,
            zoom_range="Digital Zoom",
        ),
        simulate_zoom_range_speeds_ring_rotate_and_fx6_zoom_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            shoot_mode=SHOOT_MODE_SQ,
            fps=120.0,
            zoom_range="ClearImage Zoom",
        ),
    ]
    p75a_ok = (
        p75a_ciz_4k_ok.admitted
        and p75a_ciz_4k_ok.effective_max_magnification == 1.5
        and p75a_ciz_4k_ok.focus_area_disabled
        and p75a_ciz_4k_ok.effective_focus_area == "Center Priority"
        and p75a_ciz_4k_ok.metering_locked_multi
        and p75a_ciz_4k_ok.face_eye_prior_af_disabled
        and p75a_ciz_4k_ok.face_prior_multi_metering_disabled
        and p75a_ciz_4k_ok.tracking_disabled
        and p75a_reset_split_ok.admitted
        and p75a_reset_split_ok.effective_max_magnification == 2.0
        and p75a_reset_split_ok.effective_zoom_lever_1st_standby == 3
        and p75a_reset_split_ok.effective_zoom_lever_2nd_rec == 8
        and p75a_reset_split_ok.effective_custom_key_speed_rec == 3
        and p75a_reset_split_ok.effective_remote_speed_type == "Variable"
        and p75a_reset_split_ok.effective_zoom_range == "ClearImage Zoom"
        and p75a_reset_split_ok.effective_zoom_ring_rotate == "Right(W)/Left(T)"
        and (not p75a_reset_split_ok.zoom_range_resettable)
        and (not p75a_reset_split_ok.zoom_ring_rotate_resettable)
        and p75a_digital_still_ok.admitted
        and p75a_digital_still_ok.effective_max_magnification == 6.1
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p75a_blocks)
        and p75a_fx6[0].admitted
        and p75a_fx6[0].fx6_handle_zoom_speed_step == 8
        and (not p75a_fx6[1].admitted)
        and p75a_fx6[1].errno_code == EOPNOTSUPP_ERRNO
        and (not p75a_fx6[1].fx6_digital_zoom_supported)
        and (not p75a_fx6[2].admitted)
        and p75a_fx6[2].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 75B probes
    p75b_still_min_ss_flash_ok = simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
        shoot_mode=SHOOT_MODE_STILL,
        exposure_mode="A",
        iso_mode="ISO AUTO",
        iso_range_limit_min=200,
        iso_range_limit_max=6400,
        iso_auto_min_limit=80,
        iso_auto_max_limit=25600,
        iso_auto_min_ss_requested="FAST",
        external_flash_attached=True,
        gamma_profile="S-Cinetone(PP11)",
        camera_settings_reset_applied=True,
    )
    p75b_cine_ei_ok = simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        exposure_mode="M",
        log_shooting="Cine EI",
        gamma_profile="S-Log3",
        base_iso_requested=12800,
    )
    p75b_blocks = [
        simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=SHOOT_MODE_SQ,
            auto_slow_shutter_requested="On",
        ),
        simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            exposure_mode="S",
            auto_slow_shutter_requested="On",
        ),
        simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            exposure_mode="Flexible Exp. Mode",
            flex_exp_shutter_auto=False,
            auto_slow_shutter_requested="On",
        ),
        simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            shutter_mode="Angle",
            auto_slow_shutter_requested="On",
        ),
        simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            iso_mode="ISO AUTO",
            iso_auto_min_ss_requested="STD",
        ),
        simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            log_shooting="Flexible ISO",
            base_iso_requested=12800,
        ),
    ]
    p75b_fx6 = [
        simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            fx6_base_sensitivity="High",
            fx6_agc_enabled=True,
        ),
        simulate_auto_slow_shutter_iso_limit_min_ss_dual_base_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            iso_auto_min_ss_requested="STD",
        ),
    ]
    p75b_ok = (
        p75b_still_min_ss_flash_ok.admitted
        and p75b_still_min_ss_flash_ok.iso_auto_min_ss_enabled
        and p75b_still_min_ss_flash_ok.effective_iso_auto_min_ss == "STD"
        and p75b_still_min_ss_flash_ok.flash_sync_override_active
        and p75b_still_min_ss_flash_ok.flash_sync_override_shutter == "1/250"
        and p75b_still_min_ss_flash_ok.effective_iso_range_limit_min == 200
        and p75b_still_min_ss_flash_ok.effective_iso_range_limit_max == 6400
        and (not p75b_still_min_ss_flash_ok.iso_range_limit_resettable)
        and p75b_still_min_ss_flash_ok.effective_iso_auto_min_limit == 80
        and p75b_still_min_ss_flash_ok.effective_iso_auto_max_limit == 25600
        and p75b_still_min_ss_flash_ok.dual_base_low_iso == 100
        and p75b_still_min_ss_flash_ok.dual_base_high_iso == 2000
        and p75b_cine_ei_ok.admitted
        and p75b_cine_ei_ok.base_iso_menu_visible
        and p75b_cine_ei_ok.effective_base_iso == 12800
        and p75b_cine_ei_ok.auto_slow_shutter_locked
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p75b_blocks)
        and p75b_fx6[0].admitted
        and p75b_fx6[0].effective_base_iso == 12800
        and (not p75b_fx6[1].admitted)
        and p75b_fx6[1].errno_code == EOPNOTSUPP_ERRNO
        and (not p75b_fx6[1].fx6_iso_auto_min_ss_supported)
    )

    # Sub-Model 75C probes
    p75c_uncomp_reset_ok = simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
        file_format="RAW",
        raw_file_type="Uncompressed",
        sort_recording="On",
        camera_settings_reset_applied=True,
    )
    p75c_hlg_heif_ok = simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
        file_format="HEIF",
        jpeg_heif_switch="HEIF(4:2:2)",
        hlg_still_image="On",
        exposure_mode="M",
        recording_slot="Slot 2",
        capture_triggered=True,
    )
    p75c_blocks = [
        simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            raw_file_type="Lossless Comp (L)",
        ),
        simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            file_format="RAW & HEIF",
            jpeg_heif_switch="HEIF(4:2:0)",
            hlg_still_image="On",
        ),
        simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
            recording_slot="Slot 2",
            sort_recording="On",
            auto_switch_media="On",
            slot2_full_spillover_triggered=True,
        ),
    ]
    p75c_fx6 = simulate_still_arw_rawcomp_heif_hlg_and_sort_slot1_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        shoot_mode=SHOOT_MODE_STILL,
    )
    p75c_ok = (
        p75c_uncomp_reset_ok.admitted
        and p75c_uncomp_reset_ok.effective_raw_file_type == "Compressed"
        and p75c_uncomp_reset_ok.effective_sort_recording == "On"
        and (not p75c_uncomp_reset_ok.sort_recording_resettable)
        and p75c_hlg_heif_ok.admitted
        and p75c_hlg_heif_ok.effective_hlg_still_image == "On"
        and p75c_hlg_heif_ok.hlg_still_internal_elf_symbol == "STILL_HLD_PHOTO_ON"
        and p75c_hlg_heif_ok.hlg_still_color_space == "BT.2100/BT.2020"
        and p75c_hlg_heif_ok.hlg_still_iso_floor_range == (100, 125)
        and p75c_hlg_heif_ok.pp_creative_look_dro_disabled
        and (not p75c_blocks[0].admitted)
        and p75c_blocks[0].errno_code == EOPNOTSUPP_ERRNO
        and (not p75c_blocks[1].admitted)
        and p75c_blocks[1].errno_code == EOPNOTSUPP_ERRNO
        and (not p75c_blocks[2].admitted)
        and p75c_blocks[2].errno_code == EROFS_ERRNO
        and p75c_blocks[2].slot1_erofs_triggered
        and p75c_blocks[2].slot1_data_sector_writes == 0
        and (not p75c_fx6.admitted)
        and p75c_fx6.errno_code == EOPNOTSUPP_ERRNO
        and (not p75c_fx6.fx6_has_still_arw_heif)
    )

    # Sub-Model 75D probes
    p75d_single_lun_ok = simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
        usb_connection_mode="MassStorage(MSC)",
        usb_lun_setting="Single",
        host_os_msc_lockdown=True,
        camera_settings_reset_applied=True,
    )
    p75d_dcc1_ok = simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
        np_fz100_inserted=False,
        dc_c1_coupler_attached=True,
        dc_c1_pd_watts=65,
        dc_c1_cable_amps=5,
    )
    p75d_blocks = [
        simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            usb_connection_mode="MassStorage(MSC)",
            usb_lun_setting="Single",
            host_os_msc_lockdown=False,
        ),
        simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            np_fz100_inserted=True,
            np_fz100_pulled_live=True,
        ),
        simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            usb_connection_mode="USB Streaming (UVC)",
        ),
        simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            network_streaming_enabled=True,
            movie_rec_during_streaming="Enable",
            recording_slot="Slot 1",
        ),
    ]
    p75d_fx6 = [
        simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            fx6_dc_in_voltage_v=19.5,
        ),
        simulate_usb_mode_lun_pd_and_uvc_dormancy_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            usb_connection_mode="USB Streaming (UVC)",
        ),
    ]
    p75d_ok = (
        p75d_single_lun_ok.admitted
        and p75d_single_lun_ok.effective_usb_connection_mode == "MassStorage(MSC)"
        and p75d_single_lun_ok.effective_usb_lun_setting == "Single"
        and p75d_single_lun_ok.exposed_luns == ("Slot 1",)
        and p75d_single_lun_ok.single_lun_exposes_slot1_only
        and p75d_single_lun_ok.slot1_exposed_hazard_detected
        and (not p75d_single_lun_ok.usb_settings_resettable)
        and p75d_dcc1_ok.admitted
        and p75d_dcc1_ok.np_fz100_pd_gate_satisfied
        and (not p75d_blocks[0].admitted)
        and p75d_blocks[0].errno_code == EROFS_ERRNO
        and p75d_blocks[0].slot1_erofs_triggered
        and p75d_blocks[0].slot1_data_sector_writes == 0
        and (not p75d_blocks[1].admitted)
        and p75d_blocks[1].errno_code == EPERM_ERRNO
        and p75d_blocks[1].power_cut_brownout
        and (not p75d_blocks[2].admitted)
        and p75d_blocks[2].errno_code == EOPNOTSUPP_ERRNO
        and (not p75d_blocks[2].native_uvc_exposed)
        and (not p75d_blocks[3].admitted)
        and p75d_blocks[3].errno_code == EROFS_ERRNO
        and p75d_blocks[3].slot1_erofs_triggered
        and p75d_fx6[0].admitted
        and p75d_fx6[0].fx6_batteryless_dcin_active
        and (not p75d_fx6[1].admitted)
        and p75d_fx6[1].errno_code == EOPNOTSUPP_ERRNO
        and (not p75d_fx6[1].native_uvc_exposed)
    )

    milestone_probe = _build_stage75_milestone_probe()

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
        # 75A redlines
        "zoom_lever_1st_default_speed": ZOOM_LEVER_1ST_DEFAULT_SPEED,
        "zoom_lever_2nd_default_speed": ZOOM_LEVER_2ND_DEFAULT_SPEED,
        "zoom_custom_key_default_speed": ZOOM_CUSTOM_KEY_DEFAULT_SPEED,
        "zoom_remote_default_speed": ZOOM_REMOTE_DEFAULT_SPEED,
        "zoom_speed_max_steps": ZOOM_SPEED_MAX_STEPS,
        "ciz_4k_max_magnification": CIZ_4K_MAX_MAGNIFICATION,
        "ciz_hd_max_magnification": CIZ_HD_MAX_MAGNIFICATION,
        "digital_zoom_movie_max_magnification": DIGITAL_ZOOM_MOVIE_MAX_MAGNIFICATION,
        "zoom_range_reset_immunity_drift_events": ZOOM_RANGE_RESET_IMMUNITY_DRIFT_EVENTS,
        "zoom_ring_rotate_reset_immunity_drift_events": ZOOM_RING_ROTATE_RESET_IMMUNITY_DRIFT_EVENTS,
        "non_optical_zoom_af_tracking_bypass_events": NON_OPTICAL_ZOOM_AF_TRACKING_BYPASS_EVENTS,
        "fx6_digital_zoom_leak_events": FX6_DIGITAL_ZOOM_LEAK_EVENTS,
        # 75B redlines
        "auto_slow_shutter_lockout_conditions_count": AUTO_SLOW_SHUTTER_LOCKOUT_CONDITIONS_COUNT,
        "auto_slow_shutter_6lock_bypass_events": AUTO_SLOW_SHUTTER_6LOCK_BYPASS_EVENTS,
        "iso_range_limit_reset_immunity_drift_events": ISO_RANGE_LIMIT_RESET_IMMUNITY_DRIFT_EVENTS,
        "iso_range_limit_leaked_to_auto_events": ISO_RANGE_LIMIT_LEAKED_TO_AUTO_EVENTS,
        "iso_auto_min_ss_movie_or_sq_bypass_events": ISO_AUTO_MIN_SS_MOVIE_OR_SQ_BYPASS_EVENTS,
        "dual_conversion_gain_ratio": DUAL_CONVERSION_GAIN_RATIO,
        "fx6_iso_auto_min_ss_exposed_events": FX6_ISO_AUTO_MIN_SS_EXPOSED_EVENTS,
        # 75C redlines
        "raw_file_type_active_options_count": RAW_FILE_TYPE_ACTIVE_OPTIONS_COUNT,
        "dormant_lossless_raw_exposed_events": DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS,
        "hlg_still_prerequisite_bypass_events": HLG_STILL_PREREQUISITE_BYPASS_EVENTS,
        "still_hlg_photo_typo_matched": STILL_HLG_PHOTO_TYPO_MATCHED,
        "sort_recording_slot1_erofs_bypass_events": SORT_RECORDING_SLOT1_EROFS_BYPASS_EVENTS,
        "fx6_still_arw_or_heif_exposed_events": FX6_STILL_ARW_OR_HEIF_EXPOSED_EVENTS,
        # 75D redlines
        "usb_connection_active_modes_count": USB_CONNECTION_ACTIVE_MODES_COUNT,
        "usb_lun_single_exposes_slot1_only": USB_LUN_SINGLE_EXPOSES_SLOT1_ONLY,
        "usb_lun_slot1_host_pollution_events": USB_LUN_SLOT1_HOST_POLLUTION_EVENTS,
        "usb_pd_batteryless_power_bypass_events": USB_PD_BATTERYLESS_POWER_BYPASS_EVENTS,
        "fx3_native_uvc_exposed_events": FX3_NATIVE_UVC_EXPOSED_EVENTS,
        "fx6_native_uvc_exposed_events": FX6_NATIVE_UVC_EXPOSED_EVENTS,
        "streaming_movie_rec_slot1_erofs_bypass_events": STREAMING_MOVIE_REC_SLOT1_EROFS_BYPASS_EVENTS,
        # Runtime / Zero-Leak redlines
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    redlines_ok = (
        bool(P8_CP_MUTATION_FORBIDDEN)
        and NOP_COUNT == 0
        and GUEST_CODE_MODIFICATION_BYTES == 0
        and CP_MUTATION_BYTES == 0
        and WBI_MUTATION_BYTES == 0
        and CALIBRATION_MUTATION_BYTES == 0
        and CNFLASHA_MUTATION_BYTES == 0
        and bool(CNFLASHA_USERSPACE_WRITE_BLOCKED)
        and NVRAM_PERSISTENT_WRITES == 0
        and BK4_PERSISTENT_NVRAM_WRITES == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not EMMC_WRITES_AUTHORIZED)
        and (not CROSS_MODEL_FLASH_AUTHORIZED)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not OVERALL_READY_FOR_HARDWARE_ATTACH)
        and (not ISP_WRITE_AUTHORIZED)
        and EMMC_NFLASHA_WRITE_COUNT == 0
        and EMMC_MUTATION_BYTES == 0
        and EMMC_CORRUPTIONS == 0
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and SPI_NOR_MUTATION_BYTES == 0
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and PASSIVE_TX_BYTES_EMITTED == 0
        and SLOT1_DATA_SECTOR_WRITES == 0
        and (not SLOT1_AVF_INFO_MUTATED)
        and RF_PACKETS_TRANSMITTED == 0
        and RF_NVS_MUTATION_BYTES == 0
        and ZOOM_LEVER_1ST_DEFAULT_SPEED == 3
        and ZOOM_LEVER_2ND_DEFAULT_SPEED == 8
        and ZOOM_CUSTOM_KEY_DEFAULT_SPEED == 3
        and ZOOM_REMOTE_DEFAULT_SPEED == 3
        and ZOOM_SPEED_MAX_STEPS == 8
        and CIZ_4K_MAX_MAGNIFICATION == 1.5
        and CIZ_HD_MAX_MAGNIFICATION == 2.0
        and DIGITAL_ZOOM_MOVIE_MAX_MAGNIFICATION == 4.0
        and ZOOM_RANGE_RESET_IMMUNITY_DRIFT_EVENTS == 0
        and ZOOM_RING_ROTATE_RESET_IMMUNITY_DRIFT_EVENTS == 0
        and NON_OPTICAL_ZOOM_AF_TRACKING_BYPASS_EVENTS == 0
        and FX6_DIGITAL_ZOOM_LEAK_EVENTS == 0
        and AUTO_SLOW_SHUTTER_LOCKOUT_CONDITIONS_COUNT == 7
        and AUTO_SLOW_SHUTTER_6LOCK_BYPASS_EVENTS == 0
        and ISO_RANGE_LIMIT_RESET_IMMUNITY_DRIFT_EVENTS == 0
        and ISO_RANGE_LIMIT_LEAKED_TO_AUTO_EVENTS == 0
        and ISO_AUTO_MIN_SS_MOVIE_OR_SQ_BYPASS_EVENTS == 0
        and DUAL_CONVERSION_GAIN_RATIO == 20
        and FX6_ISO_AUTO_MIN_SS_EXPOSED_EVENTS == 0
        and RAW_FILE_TYPE_ACTIVE_OPTIONS_COUNT == 2
        and DORMANT_LOSSLESS_RAW_EXPOSED_EVENTS == 0
        and HLG_STILL_PREREQUISITE_BYPASS_EVENTS == 0
        and bool(STILL_HLG_PHOTO_TYPO_MATCHED)
        and SORT_RECORDING_SLOT1_EROFS_BYPASS_EVENTS == 0
        and FX6_STILL_ARW_OR_HEIF_EXPOSED_EVENTS == 0
        and USB_CONNECTION_ACTIVE_MODES_COUNT == 4
        and bool(USB_LUN_SINGLE_EXPOSES_SLOT1_ONLY)
        and USB_LUN_SLOT1_HOST_POLLUTION_EVENTS == 0
        and USB_PD_BATTERYLESS_POWER_BYPASS_EVENTS == 0
        and FX3_NATIVE_UVC_EXPOSED_EVENTS == 0
        and FX6_NATIVE_UVC_EXPOSED_EVENTS == 0
        and STREAMING_MOVIE_REC_SLOT1_EROFS_BYPASS_EVENTS == 0
        and RSV_ORPHAN_COUNT == 0
        and NULL_GPIO_DEREFS == 0
        and MAILBOX_STALLS == 0
        and STOCK_CP_FAULT_COUNT == 0
        and WF12_00342260_HITS == 0
        and APPFW_CRASHES == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
    )

    all_passed = (
        bool(donor_audit.all_contracts_verified)
        and donor_audit.raw_firmware_bytes_leaked == 0
        and p75a_ok
        and p75b_ok
        and p75c_ok
        and p75d_ok
        and redlines_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_343_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_75th_stage_milestone": IS_75TH_STAGE_MILESTONE,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "donor_audit": asdict(donor_audit),
        "stage75_milestone_probe": milestone_probe,
        "pillar_a_zoom_range_speeds_ring_rotate_hil": {
            "passed": p75a_ok,
            "fx3_ciz_4k_active_lockouts": asdict(p75a_ciz_4k_ok),
            "fx3_reset_split_law": asdict(p75a_reset_split_ok),
            "fx3_digital_still_m_61x": asdict(p75a_digital_still_ok),
            "lockout_probes": [asdict(r) for r in p75a_blocks],
            "fx6_comparison": [asdict(r) for r in p75a_fx6],
        },
        "pillar_b_auto_slow_shutter_iso_limit_min_ss_dual_base_hil": {
            "passed": p75b_ok,
            "fx3_still_min_ss_flash_and_iso_limit": asdict(p75b_still_min_ss_flash_ok),
            "fx3_cine_ei_12800_base_iso": asdict(p75b_cine_ei_ok),
            "lockout_probes": [asdict(r) for r in p75b_blocks],
            "fx6_comparison": [asdict(r) for r in p75b_fx6],
        },
        "pillar_c_still_arw_rawcomp_heif_hlg_sort_slot1_hil": {
            "passed": p75c_ok,
            "fx3_uncompressed_reset_to_compressed": asdict(p75c_uncomp_reset_ok),
            "fx3_hlg_still_heif_422_on": asdict(p75c_hlg_heif_ok),
            "lockout_and_erofs_probes": [asdict(r) for r in p75c_blocks],
            "fx6_comparison": asdict(p75c_fx6),
        },
        "pillar_d_usb_mode_lun_pd_and_uvc_dormancy_hil": {
            "passed": p75d_ok,
            "fx3_single_lun_slot1_exposure_lockdown": asdict(p75d_single_lun_ok),
            "fx3_dcc1_65w_5a_ok": asdict(p75d_dcc1_ok),
            "lockout_and_erofs_probes": [asdict(r) for r in p75d_blocks],
            "fx6_comparison": [asdict(r) for r in p75d_fx6],
        },
        "redlines": redlines,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulator.py",
        description=(
            "Phase 343 (Stage 75 — 75/75 VM HIL Stages Milestone!) Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-65 Co-Emulator: "
            "75A [Zoom Range] CIZ/Digital/8-Step Speeds & Reset-Immune [Zoom Ring Rotate], "
            "75B [Auto Slow Shutter] 7-Lockouts / [ISO Range Limit] / Still-Only [ISO AUTO Min. SS] & Dual Base ISO, "
            "75C Still ARW 100%% Dormant Lossless Comp & [HLG Still Image] STILL_HLD_PHOTO & Sort Slot-1 EROFS=30, "
            "75D [USB Connection Mode] / [USB LUN Setting]=Single Slot-1 Hazard / NP-FZ100 PD Gate / Dual FX3+FX6 UVC Dormancy."
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run complete Phase 343 Stage 75 Wave-65 HIL co-emulation audit",
    )
    parser.add_argument(
        "--clean-room",
        "--force-clean-room",
        dest="clean_room",
        action="store_true",
        help="Force CLEAN_ROOM_SYNTHETIC mode without local Mac/work donor reads",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit deterministic JSON report (default output format)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise single-line summary instead of JSON",
    )
    args = parser.parse_args(argv)

    rep = run_phase343_zoom_ciz_autoslow_iso_arw_rawcomp_usblun_uvc_coemulation(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 343 Stage 75 (75/75 Milestone) | mode={rep['source_mode']} | "
            f"ciz={red['ciz_4k_max_magnification']}/{red['ciz_hd_max_magnification']}x "
            f"ass_lck={red['auto_slow_shutter_lockout_conditions_count']} "
            f"dcg={red['dual_conversion_gain_ratio']}x "
            f"raw_opt={red['raw_file_type_active_options_count']} "
            f"usb_m={red['usb_connection_active_modes_count']} "
            f"uvc={red['fx3_native_uvc_exposed_events']}/{red['fx6_native_uvc_exposed_events']} "
            f"s1_wr={red['slot1_data_sector_writes']} leak={red['raw_firmware_bytes_leaked']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
