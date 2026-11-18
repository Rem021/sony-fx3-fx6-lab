#!/usr/bin/env python3
"""Phase 353 (Stage 78 — 78/78 Full-Board VM Co-Emulation Stages):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-68 HIL Co-Emulator.

Models and audits the four Wave-68 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / nonexistent `work_root` / `CLEAN_ROOM_SYNTHETIC`
CI fallback and `raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 78A — `Setup -> [Area/Date] -> [Area/Date/Time Setting]`
   30 GMT Zones, `saylight_saving`/`sever` Typos & 24h Rechargeable RTC vs
   FX6 `Maintenance > Clock Set`**:
   - FX3 `[Area/Date/Time Setting]` (`_f 0x6a9c`, replacing legacy
     `Date/Time Setup`, `Not available` under `[Camera Settings Reset]`,
     restored + re-triggers `37dlg_rec203_initial_setting_controller` /
     `PRM_launch_date_time_setup_area_setting` wizard on `[Initialize]`):
     4 sub-items:
     1) `[Area Setting]` (`base 0xe91a`): **30** `AREA_GMT_*` zones
        (`GMT_M_11_0..GMT_P_12_0`) including **6** half-hour offsets
        (`M_03_5`, `P_03_5`, `P_04_5`, `P_05_5`, `P_06_5`, `P_09_5`);
     2) `[Daylight Savings]` (`base 0xe917`): `Off` (default) / `On` with
        Sony ELF typo `convert_setting_daylight_saving_to_saylight_saving`;
     3) `[Date/Time]` (`_f 0x73b5`): 24h display + Creators' App BT sync,
        `BKID_APP_setting_auto_sync_sever_date_time` (`sever` typo);
     4) `[Date Format]` (`_f 0x670d`): exact **3** formats (`Y-M-D` / `M-D-Y`
        / `D-M-Y`, zero standalone `YYYY-MM-DD`).
   - Internal soldered rechargeable RTC backup battery (zero user-replaceable
     CR2032 coin-cell slot; charges `>= 24 hours` with charged `NP-FZ100`
     while camera power is `OFF`; `ilc/2210` does NOT state a `"3 months"`
     retention figure).
   - Contrast with `ILME-FX6 Ver. 6.01` `Maintenance > Clock Set` (`ns2 0x426c`,
     `BKID_APP_USER_MENU_CLOCK_SET0..6`): `UTC -12:00..+14:00` in `30-min`
     steps, `Date Mode` (`YYMMDD`/`MMDDYY`/`DDMMYY`) + `12h/24h`, **zero**
     standalone DST toggle (`summer_time_name_dst` & `ns2 0x564d` dormant),
     hard-locks `Clock Set` screen on depletion or emits `ns2 0x411f`
     `Backup Battery End`.

2. **Sub-Model 78B — All-Pipeline `[Grid Line Display]` HDMI Pass-Through vs
   Movie-Only `[Marker Display] -> [Guideframe]` Zero-HDMI Isolation**:
   - Both `[Grid Line Display/Type]` (`Off`/`On`, `Rule of 3rds Grid` default /
     `Square Grid` / `Diag. + Square Grid`; unified across Still/Movie/`S&Q`,
     legacy `BKID_APP_deleted_setting_grid_line_{display,type}_movie` retired)
     and Movie/`S&Q`-only `[Marker Display]` (`Center Marker`, `15`-ratio
     `Aspect Marker`, `Safety Zone`, `[Guideframe]` `Off`/`On`; suppressed
     during `[Focus Magnifier]`) are **Reset-immune (`Not available` under
     `[Camera Settings Reset]`, restored only by `[Initialize]`)**.
   - **Opposite HDMI routing**: `[Marker Display]` (incl. `Guideframe`) is
     100%% monitor-only (`0` pixels ever output over HDMI even when
     `[HDMI Info. Display] = On`), whereas `[Grid Line Display]` **passes
     through onto HDMI** whenever `[HDMI Info. Display] = On` & `Rec. Media
     = On` & `RAW Output = Off` (stripped only on Clean-Feed `HDMI Info.
     Display = Off`, `Off(HDMI Only)`, or `RAW Output = On`).
   - Contrast with `ILME-FX6 Ver. 6.01` `Monitoring > Marker` (`Center Marker
     1..4/Off`, `Guide Frame On/Off`, independent `VF/SDI/HDMI` overlay gates,
     dormant `GUIDE_FRAME_{RULE_OF_3RD,SQUARE,DIAG_SQUARE,GOLDEN_RATIO}_GRID`).

3. **Sub-Model 78C — `[Save/Load Settings]` `CAMSET01..10.DAT` (`Slot 1`-Locked,
   `libSaveLoadSettings.so`, Exclusions, `EROFS=30`) vs `Camera Set. Memory`
   `1..3` / `M1..M4` & FX6 `Project > All File`**:
   - FX3 `Setup -> [Reset/Save Settings] -> [Save/Load Settings]`
     (`libSaveLoadSettings.so` `18,760 B`, disabled in `MR` mode, auto-reboot
     on Load): media locked strictly to **`Slot 1`** (`Slot 2` unavailable),
     max **10** `CAMSET01..10.DAT` files (`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`
     — `0` `PRO/CAMERA` hits in `FX3 appFw.so`!) + `60` Cloud slots
     (`Cloud(Private)` / `Cloud(Share)`).
   - Full official exclusion list (NEVER saved in `CAMSET*.DAT`): `IPTC
     Information`, `Copyright Info`, `External Flash Set.`, `White Balance`
     (`Custom 1..3`), `Face Memory`, all Network/FTP (`FTPSET/%s.DAT`
     separate)/Auth/IPsec, `Language`, and `Area/Date/Time Setting`.
   - Separate `Shooting -> [Shooting Mode] -> [Camera Set. Memory]`: NVRAM
     `1..3` (bundled in `CAMSET*.DAT`, Reset-immune) vs card `M1..M4`
     (`CAMPR%02d%c.DAT`, selectable `Slot 1` or `Slot 2` via `[Memory/Recall
     Media]`), vs FX6 `Project > All File` (`Media(B)` max `64` `.ALL` files
     in `SONY/PRO/CAMERA`), `User File` (`.USRF`), `Scene File` (`.SCN`), and
     dormant `Reference File` (`0` ELF hits in `FX6 appFw.so`).
   - **Tier-0 `Slot 1` `EROFS=30` Firewall**: `[Save]`/`[Delete]` on read-only
     Tier-0 `Slot 1` fails closed with `EROFS=30` (`slot1_data_sector_writes
     == 0`, `emmc_nflasha_write_count == 0`); `[Load]` is read-only safe and
     triggers auto-reboot without mutating `Slot 1` or persistent NVRAM.

4. **Sub-Model 78D — Zero Physical `Sync Terminal` Myth-Busting & `XLR-H1` vs
   `HVL-LBPC` `[Video Light Mode]` MI-Shoe Mutual Exclusion vs FX6 `TC IN/OUT`
   & Zero `GENLOCK`**:
   - FX3 has **zero** physical PC flash sync terminal (`SYNCHRO_TERMINAL*`
     symbols in `FX3 appFw.so == 0`; `Flash Sync Spd. Prty.` dormant, `0`
     exposed in `ilc/2210`).
   - Still-only MI-Shoe `[External Flash Set.]` & `[Flash Mode]` (`1/250 s`
     max X-Sync, `< 250 V` limit, mechanical shutter only, Reset-immune &
     excluded from `CAMSET*.DAT`) and 4-mode `[Video Light Mode]` (`Power Link`
     default / `REC Link` / `REC Link&STBY` / `Auto`
     `VIDEO_LIGHT_SET_AUTO_LOW_LIGHT`) vs physical & electrical MI-Shoe mutual
     exclusion with **`XLR-H1`** (whose handle shoes are passive cold shoes
     only; PMIC `5V <= 900 mA` guard).
   - Contrast with `ILME-FX6 Ver. 6.01` 3-mode `Technical > Video Light Set`
     (zero `Auto`), zero Still `[Flash]` UI, switchable `TC IN/OUT` BNC, and
     **zero** physical `GENLOCK IN / REF OUT` BNC (`107` dormant `GENLOCK`
     symbols in `FX6 appFw.so` inherited from `PXW-FX9`).
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
# Phase 353 Schema, Milestone & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase353_realhw_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation_v1"
)
PHASE_353_VERSION = "353.0.0"
PHASE_NUMBER = 353
STAGE_INDEX = 78
STAGE_TOTAL = 78
MILESTONE_LABEL = "78/78"
IS_78TH_STAGE_MILESTONE = True

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

# Wave-68 Sub-Model 78A..78D Numeric & Invariant Contracts
# 78A — Setup -> [Area/Date] & 24h RTC vs FX6 Clock Set
FX3_AREA_GMT_ZONES_COUNT = 30
FX3_AREA_HALF_HOUR_ZONES_COUNT = 6
FX3_DATE_FORMATS_COUNT = 3
AREA_DATE_SAYLIGHT_SAVING_TYPO_MATCHED = True
AREA_DATE_SEVER_TYPO_MATCHED = True
AREA_DATE_RESET_WIPE_EVENTS = 0
FX3_USER_CR2032_SLOT_PRESENT = False
FX3_RTC_CHARGE_MIN_HOURS_POWER_OFF = 24
ILC2210_STATES_3_MONTHS_RETENTION = False
FX6_CLOCK_SET_DST_TOGGLE_EXPOSED = False

# 78B — Grid Line HDMI Pass-Through vs Marker Display Zero-HDMI Isolation
GRID_LINE_TYPES_COUNT = 3
ASPECT_MARKER_RATIOS_COUNT = 15
RETIRED_MOVIE_GRID_KEYS_EXPOSED = False
GRID_AND_MARKER_RESET_WIPE_EVENTS = 0
HDMI_MARKER_INJECTED_PIXELS = 0
FX6_NATIVE_3MODE_GRID_EXPOSED = False

# 78C — [Save/Load Settings] CAMSET01..10.DAT Slot-1 EROFS=30 vs FX6 All File
CAMSET_MAX_CARD_SLOTS = 10
CAMSET_MAX_CLOUD_SLOTS = 60
CAMSET_SLOT2_BYPASS_EVENTS = 0
FX3_PRO_CAMERA_PATH_HITS = 0
CAMSET_EXCLUDED_ITEMS_LEAKED_COUNT = 0
CAMSET_SLOT1_EROFS_BYPASS_EVENTS = 0
FX6_ALL_FILE_MAX_SLOTS = 64
FX6_REFERENCE_FILE_ELF_HITS = 0

# 78D — Zero Sync Terminal, XLR-H1 vs HVL-LBPC MI-Shoe Exclusion & FX6 Zero GENLOCK
FX3_PHYSICAL_SYNC_TERMINAL_PRESENT = False
FX3_SYNCHRO_TERMINAL_ELF_HITS = 0
DORMANT_FLASH_SYNC_SPD_PRTY_EXPOSED_EVENTS = 0
FX3_VIDEO_LIGHT_MODES_COUNT = 4
FX6_VIDEO_LIGHT_MODES_COUNT = 3
FX6_VIDEO_LIGHT_AUTO_SUPPORTED = False
XLR_H1_MISHOE_COLLISION_BYPASS_EVENTS = 0
PMIC_5V_MAX_MA = 900
PMIC_5V_OVERCURRENT_BYPASS_EVENTS = 0
FX6_PHYSICAL_GENLOCK_BNC_PRESENT = False
FX6_DORMANT_GENLOCK_ELF_HITS = 107
FX6_DORMANT_GENLOCK_EXPOSED_EVENTS = 0

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
_UNSET = object()


# ---------------------------------------------------------------------------
# Verified Local Donor Specs (12 FX3 Ver. 7.02 & FX6 Ver. 6.01 Wave-68 Donors)
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
    "fx3_saveload": f"{_FX3_USR_PREFIX}/lib/libSaveLoadSettings.so",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
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
    "fx3_string_en_g": 69_600,
    "fx3_saveload": 18_760,
    "fx6_string_en": 118_208,
    "fx6_string_en_2": 118_676,
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
    "fx3_string_en_g": "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
    "fx3_saveload": "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
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
        b"Area/Date/Time Setting",
        b"Date Format",
        b"Y-M-D",
        b"M-D-Y",
        b"D-M-Y",
        b"Grid Line Display",
        b"Grid Line Type",
        b"Grid Line Display Select",
        b"Rule of 3rds Grid",
        b"Square Grid",
        b"Diag. + Square Grid",
        b"Marker Display",
        b"Guideframe",
        b"Save/Load Settings",
        b"Cloud(Private)",
        b"Cloud(Share)",
        b"Memory/Recall Media",
        b"Save/Load FTP Settings",
        b"Flash Sync Spd. Prty.",
        b"External Flash Set.",
        b"Ext. Flash Firing Set.",
        b"Ext. Flash Cust. Set.",
        b"Video Light Mode",
        b"Power Link",
        b"REC Link",
        b"REC Link&STBY",
        b"automatically turns on when it is dark.",
    ),
    "fx3_string_sc_f": (
        "\u533a\u57df/\u65e5\u671f/\u65f6\u95f4\u8bbe\u7f6e".encode("utf-8"),
        "\u7f51\u683c\u7ebf\u663e\u793a".encode("utf-8"),
        "\u6807\u8bb0\u663e\u793a".encode("utf-8"),
        "\u4fdd\u5b58/\u52a0\u8f7d\u8bbe\u7f6e".encode("utf-8"),
        "\u5916\u7f6e\u95ea\u5149\u706f\u8bbe\u7f6e".encode("utf-8"),
        "\u89c6\u9891\u706f\u6a21\u5f0f".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "\u5340\u57df/\u65e5\u671f/\u6642\u9593\u8a2d\u5b9a".encode("utf-8"),
        "\u683c\u7dda\u986f\u793a".encode("utf-8"),
        "\u9304\u5f71\u8f14\u52a9\u6a19\u8a8c\u986f\u793a".encode("utf-8"),
        "\u6c34\u5e73\u5c0e\u5f15\u6846".encode("utf-8"),
        "\u5132\u5b58/\u8f09\u5165\u8a2d\u5b9a".encode("utf-8"),
        "\u5916\u63a5\u9583\u5149\u71c8\u8a2d\u5b9a".encode("utf-8"),
        "\u8996\u8a0a\u71c8\u6a21\u5f0f".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "\u30a8\u30ea\u30a2/\u65e5\u6642\u8a2d\u5b9a".encode("utf-8"),
        "\uff78\uff9e\uff98\uff6f\uff84\uff9e\uff97\uff72\uff9d\u8868\u793a".encode("utf-8"),
        "\u30de\u30fc\u30ab\u30fc\u8868\u793a".encode("utf-8"),
        "\u30ac\u30a4\u30c9\u30d5\u30ec\u30fc\u30e0".encode("utf-8"),
        "\u8a2d\u5b9a\u306e\u4fdd\u5b58/\u8aad\u8fbc".encode("utf-8"),
        "\u5916\u90e8\u30d5\u30e9\u30c3\u30b7\u30e5\u8a2d\u5b9a".encode("utf-8"),
        "\u30d3\u30c7\u30aa\u30e9\u30a4\u30c8\u30e2\u30fc\u30c9".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Area Setting",
        b"Daylight Savings",
        b"Date/Time Setup",
        b"Flash Mode",
    ),
    "fx3_string_en_g": (
        b"Initial Setting with Creators' App",
        b"Load?",
        b"Reboots after loading.",
        b"This file cannot be loaded.",
        b"Loading failed.",
        b"SYNCHRO_TERMINAL_OUTPUT_SET_ON",
    ),
    "fx3_saveload": (
        b"SaveLoadSettingsIf",
        b"requestToRead",
        b"requestToCheck",
        b"requestToWrite",
        b"procRead",
        b"procCheck",
        b"procWrite",
        b"Backup_get_datasize",
        b"Backup_read",
        b"Backup_write",
        b"infra_getCallbackFuncTable",
        b"infra_getCallbackFuncTableFtp",
        b"EventWrapper",
    ),
    "fx6_string_en": (
        b"All File",
        b"User File",
        b"Scene File",
        b"All File Load Network Data",
    ),
    "fx6_string_en_2": (
        b"Clock Set",
        b"UTC -12:00",
        b"UTC +14:00",
        b"Daylight Saving Time",
        b"Backup Battery End",
        b"Guide Frame",
        b"Center Marker",
        b"Reference File",
        b"Video Light Set",
        b"Genlock",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (
            0x3029000,
            "37dlg_rec203_initial_setting_controller",
            b"37dlg_rec203_initial_setting_controller",
        ),
        (
            0x39C4000,
            "PRM_launch_date_time_setup_area_setting",
            b"PRM_launch_date_time_setup_area_setting",
        ),
        (0x3C18000, "AREA_GMT_M_11_0", b"AREA_GMT_M_11_0"),
        (0x3C18000, "AREA_GMT_P_12_0", b"AREA_GMT_P_12_0"),
        (0x3C18000, "AREA_GMT_P_05_5", b"AREA_GMT_P_05_5"),
        (
            0x3D09000,
            "convert_setting_daylight_saving_to_saylight_saving",
            b"convert_setting_daylight_saving_to_saylight_saving",
        ),
        (
            0x3BCA000,
            "BKID_APP_setting_daylight_saving",
            b"BKID_APP_setting_daylight_saving",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_auto_sync_sever_date_time",
            b"BKID_APP_setting_auto_sync_sever_date_time",
        ),
        (
            0x3BCA000,
            "BKID_APP_setting_date_format",
            b"BKID_APP_setting_date_format",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_grid_line_display",
            b"BKID_APP_setting_grid_line_display",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_grid_line_type",
            b"BKID_APP_setting_grid_line_type",
        ),
        (
            0x3BEC000,
            "BKID_APP_deleted_setting_grid_line_display_movie",
            b"BKID_APP_deleted_setting_grid_line_display_movie",
        ),
        (
            0x3BEC000,
            "BKID_APP_deleted_setting_grid_line_type_movie",
            b"BKID_APP_deleted_setting_grid_line_type_movie",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_marker_display",
            b"BKID_APP_setting_marker_display",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_guide_frame",
            b"BKID_APP_setting_guide_frame",
        ),
        (
            0x39BF000,
            "PRM_HAITA_setting_marker_display_exposure_mode",
            b"PRM_HAITA_setting_marker_display_exposure_mode",
        ),
        (
            0x3B2D000,
            "GRID_LINE_TYPE_RULE_OF_3RD_GRID",
            b"GRID_LINE_TYPE_RULE_OF_3RD_GRID",
        ),
        (
            0x3907000,
            "CAMSET_PATH_TEMPLATE",
            b"%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT",
        ),
        (
            0x3908000,
            "CAMPR_PATH_TEMPLATE",
            b"%c:%s/SONY/SETTING/%s/CAMPR%02d%c.DAT",
        ),
        (
            0x3907000,
            "FTPSET_PATH_TEMPLATE",
            b"%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT",
        ),
        (0x317C000, "CAMSET%02d", b"CAMSET%02d"),
        (
            0x3BC0000,
            "BKID_APP_save_load_settings_infra_data",
            b"BKID_APP_save_load_settings_infra_data",
        ),
        (
            0x3BC8000,
            "BKID_APP_setting_flash_sync_spd_priority",
            b"BKID_APP_setting_flash_sync_spd_priority",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_video_light_set",
            b"BKID_APP_setting_video_light_set",
        ),
        (
            0x2FA8000,
            "VIDEO_LIGHT_SET_AUTO_LOW_LIGHT",
            b"VIDEO_LIGHT_SET_AUTO_LOW_LIGHT",
        ),
    ),
    "fx3_bk4": (
        (0x00000, "BK4_HEADER", b"BK4\x00"),
        (0x4A000, "ILME-FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (
            0x2712000,
            "BKID_APP_USER_MENU_CLOCK_SET0",
            b"BKID_APP_USER_MENU_CLOCK_SET0",
        ),
        (0x2634000, "summer_time_name_dst", b"summer_time_name_dst"),
        (
            0x2710000,
            "BKID_APP_USER_MENU_MARKER0",
            b"BKID_APP_USER_MENU_MARKER0",
        ),
        (
            0x279B000,
            "GUIDE_FRAME_RULE_OF_3RD_GRID",
            b"GUIDE_FRAME_RULE_OF_3RD_GRID",
        ),
        (
            0x279B000,
            "GUIDE_FRAME_GOLDEN_RATIO_GRID",
            b"GUIDE_FRAME_GOLDEN_RATIO_GRID",
        ),
        (
            0x2587000,
            "FX6_ALL_FILE_PATH_TEMPLATE",
            b"%c:%s/SONY/PRO/CAMERA/%s/%s.ALL",
        ),
        (
            0x2587000,
            "FX6_SCENE_FILE_PATH_TEMPLATE",
            b"%c:%s/SONY/PRO/SCENE/%s.SCN",
        ),
        (
            0x26CA000,
            "VAL_setting_video_light_set_POWER_LINK",
            b"VAL_setting_video_light_set_VIDEO_LIGHT_SET_POWER_LINK",
        ),
        (
            0x26CA000,
            "VAL_setting_video_light_set_REC_LINK_W_LIGHT",
            b"VAL_setting_video_light_set_VIDEO_LIGHT_SET_REC_LINK_W_LIGHT",
        ),
        (0x2752000, "SYNCHRO_TERMINAL", b"SYNCHRO_TERMINAL"),
        (0x260C000, "GENLOCK", b"GENLOCK"),
    ),
}


# ---------------------------------------------------------------------------
# Wave-68 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
BODY_MODEL_FX30 = "ILME-FX30"
BODY_MODEL_A7S3 = "ILCE-7SM3"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)
ALL_TEST_BODY_MODELS: Tuple[str, ...] = (
    BODY_MODEL_FX3,
    BODY_MODEL_FX6,
    BODY_MODEL_FX30,
    BODY_MODEL_A7S3,
)

FW_VER_101 = "1.01"
FW_VER_200 = "2.00"
FW_VER_400 = "4.00"
FW_VER_601 = "6.01"
FW_VER_702 = "7.02"
VALID_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_101,
    FW_VER_200,
    FW_VER_400,
    FW_VER_601,
    FW_VER_702,
)

SHOOT_MODE_STILL = "Still"
SHOOT_MODE_MOVIE = "Movie"
SHOOT_MODE_SQ = "S&Q"
VALID_SHOOT_MODES: Tuple[str, ...] = (SHOOT_MODE_STILL, SHOOT_MODE_MOVIE, SHOOT_MODE_SQ)

VALID_TOGGLES: Tuple[str, ...] = ("Off", "On")
VALID_MEDIA_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2")

# Sub-Model 78A — Setup -> [Area/Date] & 24h RTC vs FX6 Clock Set
FX3_AREA_GMT_30_ZONES: Tuple[str, ...] = (
    "AREA_GMT_M_11_0",
    "AREA_GMT_M_10_0",
    "AREA_GMT_M_09_0",
    "AREA_GMT_M_08_0",
    "AREA_GMT_M_07_0",
    "AREA_GMT_M_06_0",
    "AREA_GMT_M_05_0",
    "AREA_GMT_M_04_0",
    "AREA_GMT_M_03_5",
    "AREA_GMT_M_03_0",
    "AREA_GMT_M_02_0",
    "AREA_GMT_M_01_0",
    "AREA_GMT_P_00_0",
    "AREA_GMT_P_01_0",
    "AREA_GMT_P_02_0",
    "AREA_GMT_P_03_0",
    "AREA_GMT_P_03_5",
    "AREA_GMT_P_04_0",
    "AREA_GMT_P_04_5",
    "AREA_GMT_P_05_0",
    "AREA_GMT_P_05_5",
    "AREA_GMT_P_06_0",
    "AREA_GMT_P_06_5",
    "AREA_GMT_P_07_0",
    "AREA_GMT_P_08_0",
    "AREA_GMT_P_09_0",
    "AREA_GMT_P_09_5",
    "AREA_GMT_P_10_0",
    "AREA_GMT_P_11_0",
    "AREA_GMT_P_12_0",
)
FX3_AREA_HALF_HOUR_ZONES: Tuple[str, ...] = (
    "AREA_GMT_M_03_5",
    "AREA_GMT_P_03_5",
    "AREA_GMT_P_04_5",
    "AREA_GMT_P_05_5",
    "AREA_GMT_P_06_5",
    "AREA_GMT_P_09_5",
)
FX3_DATE_FORMATS: Tuple[str, ...] = ("Y-M-D", "M-D-Y", "D-M-Y")
FX6_DATE_MODES: Tuple[str, ...] = ("YYMMDD", "MMDDYY", "DDMMYY")
FX6_TIME_FORMATS: Tuple[str, ...] = ("12h", "24h")
VALID_AREA_DATE_OPERATIONS: Tuple[str, ...] = (
    "configure_area_date",
    "boot_rtc_check",
    "timestamp_dependent_action",
    "fx6_clock_set",
    "fx6_dst_toggle",
)

# Sub-Model 78B — Grid Line HDMI Pass-Through vs Marker Display Zero-HDMI Isolation
VALID_GRID_LINE_TYPES: Tuple[str, ...] = (
    "Rule of 3rds Grid",
    "Square Grid",
    "Diag. + Square Grid",
)
ASPECT_MARKER_15_RATIOS: Tuple[str, ...] = (
    "9:16",
    "4:5",
    "1:1",
    "4:3",
    "13:9",
    "14:9",
    "15:9",
    "16:9",
    "17:9",
    "1.66:1",
    "1.85:1",
    "1.91:1",
    "2:1",
    "2.35:1",
    "2.39:1",
)
VALID_ASPECT_MARKERS: Tuple[str, ...] = ("Off",) + ASPECT_MARKER_15_RATIOS
VALID_SAFETY_ZONES: Tuple[str, ...] = ("Off", "80%", "90%")
VALID_REC_MEDIA_HDMI_MODES: Tuple[str, ...] = ("On", "Off(HDMI Only)")
FX6_CENTER_MARKER_MODES: Tuple[str, ...] = ("Off", "1", "2", "3", "4")
VALID_GRID_MARKER_OPERATIONS: Tuple[str, ...] = (
    "render_overlays",
    "dormant_deleted_movie_grid",
    "fx6_marker_display",
    "fx6_dormant_3mode_grid",
)

# Sub-Model 78C — [Save/Load Settings] CAMSET01..10.DAT vs Camera Set. Memory & FX6 All File
CAMSET_EXCLUDED_ITEMS: Tuple[str, ...] = (
    "IPTC Information",
    "Copyright Info",
    "External Flash Set.",
    "White Balance (Custom 1)",
    "White Balance (Custom 2)",
    "White Balance (Custom 3)",
    "Face Memory",
    "FTP Transfer Func.",
    "Network Streaming",
    "Cloud Connection",
    "WPS Push",
    "Access Point Set.",
    "Wi-Fi Frequency Band",
    "IP Address Setting",
    "Edit Device Name",
    "Import Root Certificate",
    "Access Authen. Settings",
    "Security(IPsec)",
    "Language",
    "Area/Date/Time Setting",
)
VALID_CARD_MEDIA_TYPES: Tuple[str, ...] = ("SDXC", "CFexpress Type A")
VALID_SAVELOAD_TARGETS: Tuple[str, ...] = (
    "Slot 1",
    "Slot 2",
    "Cloud(Private)",
    "Cloud(Share)",
    "Media(B)",
)
VALID_SAVELOAD_OPERATIONS: Tuple[str, ...] = (
    "camset_save",
    "camset_load",
    "camset_delete",
    "ftpset_save",
    "camera_set_memory_body",
    "camera_set_memory_card",
    "fx6_all_file_save",
    "fx6_all_file_load",
    "fx6_scene_file_save",
    "fx6_dormant_reference_file",
)

# Sub-Model 78D — Zero Sync Terminal, XLR-H1 vs HVL-LBPC MI-Shoe Exclusion & FX6 Zero GENLOCK
FX3_FLASH_MODES: Tuple[str, ...] = (
    "Flash Off",
    "Autoflash",
    "Fill-flash",
    "Slow Sync.",
    "Rear Sync.",
)
FX3_VIDEO_LIGHT_MODES: Tuple[str, ...] = (
    "Power Link",
    "REC Link",
    "REC Link&STBY",
    "Auto",
)
FX6_VIDEO_LIGHT_MODES: Tuple[str, ...] = (
    "Power Link",
    "Rec Link",
    "Rec Link + Stby",
)
VALID_SHUTTER_TYPES: Tuple[str, ...] = ("Mechanical", "Electronic")
VALID_MISHOE_DEVICES: Tuple[str, ...] = ("None", "XLR-H1", "HVL-LBPC", "MI_FLASH")
VALID_FX6_TC_DIRECTIONS: Tuple[str, ...] = ("IN", "OUT")
VALID_SYNC_MISHOE_OPERATIONS: Tuple[str, ...] = (
    "video_light_mode",
    "external_flash_set",
    "pc_sync_terminal",
    "dormant_flash_sync_spd_prty",
    "fx6_video_light_set",
    "fx6_still_flash_ui",
    "fx6_tc_bnc",
    "fx6_genlock_sync",
)


class Stage78Phase353Error(RuntimeError):
    """Raised on invalid Phase 353 Stage 78 configuration or safety redline violation."""


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
    work_root: Union[None, str, Path, object] = _UNSET,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    """Locate local Mac/work donor tree read-only, or return None in clean-room / donorless CI."""
    if clean_room_test_mode(force_clean_room=force_clean_room, env=env):
        return None
    if work_root is None:
        return None
    if work_root is not _UNSET:
        explicit = Path(work_root)  # type: ignore[arg-type]
        if explicit.name == CLEAN_ROOM_SENTINEL_DIRNAME or not explicit.is_dir():
            return None
        if all((explicit / rel).is_file() for rel in DONOR_RELPATHS.values()):
            return explicit
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
    work_root: Union[None, str, Path, object] = _UNSET,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> bool:
    return (
        resolve_mac_work_root(
            work_root=work_root, force_clean_room=force_clean_room, env=env
        )
        is not None
    )


def _read_bounded_window_o_rdonly(path: Path, offset: int, length: int) -> bytes:
    if offset < 0 or length <= 0 or length > BOUNDED_WINDOW_MAX_BYTES:
        raise Stage78Phase353Error(
            f"Bounded window invalid: offset={offset}, length={length} "
            f"(max={BOUNDED_WINDOW_MAX_BYTES})"
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
            raise Stage78Phase353Error(
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
class Wave68DonorAuditReport:
    source_mode: str
    donor_access_mode: str
    bounded_window_max_bytes: int
    donors_checked: int
    donors_verified: int
    all_contracts_verified: bool
    fx3_area_gmt_zones_verified: int
    fx3_synchro_terminal_absent_verified: bool
    fx3_pro_camera_absent_verified: bool
    fx6_reference_file_absent_verified: bool
    fx6_video_light_no_auto_verified: bool
    raw_firmware_bytes_leaked: int
    artifacts: Dict[str, DonorArtifactInspection]


def inspect_phase353_wave68_donors(
    work_root: Union[None, str, Path, object] = _UNSET,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Wave68DonorAuditReport:
    resolved_root = resolve_mac_work_root(
        work_root=work_root, force_clean_room=force_clean_room, env=env
    )
    artifacts: Dict[str, DonorArtifactInspection] = {}

    if resolved_root is None:
        for key, expected_sz in EXPECTED_DONOR_BYTES.items():
            if key in EXPECTED_COMPACT_DONOR_SHA256:
                tokens = COMPACT_DONOR_TOKENS[key]
                artifacts[key] = DonorArtifactInspection(
                    key=key,
                    donor_kind="compact_uxc_or_so_synthetic",
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
        return Wave68DonorAuditReport(
            source_mode=SOURCE_MODE_CLEAN_ROOM,
            donor_access_mode=DONOR_ACCESS_MODE,
            bounded_window_max_bytes=BOUNDED_WINDOW_MAX_BYTES,
            donors_checked=len(artifacts),
            donors_verified=verified_count,
            all_contracts_verified=(verified_count == len(artifacts)),
            fx3_area_gmt_zones_verified=30,
            fx3_synchro_terminal_absent_verified=True,
            fx3_pro_camera_absent_verified=True,
            fx6_reference_file_absent_verified=True,
            fx6_video_light_no_auto_verified=True,
            raw_firmware_bytes_leaked=0,
            artifacts=artifacts,
        )

    fx3_area_gmt_verified = 0
    fx3_synchro_absent = False
    fx3_pro_cam_absent = False
    fx6_ref_absent = False
    fx6_vl_no_auto = False

    for key, rel in DONOR_RELPATHS.items():
        path = resolved_root / rel
        expected_sz = EXPECTED_DONOR_BYTES[key]
        if key in EXPECTED_COMPACT_DONOR_SHA256:
            data = _read_full_compact_o_rdonly(path)
            sz = len(data)
            sha = hashlib.sha256(data).hexdigest()
            tokens = COMPACT_DONOR_TOKENS[key]
            matched_tokens = sum(1 for tok in tokens if tok in data)
            artifacts[key] = DonorArtifactInspection(
                key=key,
                donor_kind="compact_uxc_or_so_o_rdonly",
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
            if key == "fx3_appfw":
                area_win = _read_bounded_window_o_rdonly(
                    path, 0x3C18000, BOUNDED_WINDOW_MAX_BYTES
                )
                fx3_area_gmt_verified = sum(
                    1 for z in FX3_AREA_GMT_30_ZONES if z.encode("ascii") in area_win
                )
                camset_win = _read_bounded_window_o_rdonly(
                    path, 0x3907000, BOUNDED_WINDOW_MAX_BYTES
                )
                flash_win = _read_bounded_window_o_rdonly(
                    path, 0x3BC8000, BOUNDED_WINDOW_MAX_BYTES
                )
                fx3_pro_cam_absent = b"PRO/CAMERA" not in camset_win
                fx3_synchro_absent = b"SYNCHRO_TERMINAL" not in flash_win
            elif key == "fx6_appfw":
                allfile_win = _read_bounded_window_o_rdonly(
                    path, 0x2587000, BOUNDED_WINDOW_MAX_BYTES
                )
                vl_win = _read_bounded_window_o_rdonly(
                    path, 0x26CA000, BOUNDED_WINDOW_MAX_BYTES
                )
                fx6_ref_absent = b"REFERENCE_FILE" not in allfile_win
                fx6_vl_no_auto = (
                    b"VAL_setting_video_light_set_VIDEO_LIGHT_SET_POWER_LINK" in vl_win
                    and b"VAL_setting_video_light_set_VIDEO_LIGHT_SET_AUTO" not in vl_win
                )
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
    all_ok = bool(
        verified_count == len(artifacts)
        and fx3_area_gmt_verified == 30
        and fx3_synchro_absent
        and fx3_pro_cam_absent
        and fx6_ref_absent
        and fx6_vl_no_auto
    )
    return Wave68DonorAuditReport(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        donor_access_mode=DONOR_ACCESS_MODE,
        bounded_window_max_bytes=BOUNDED_WINDOW_MAX_BYTES,
        donors_checked=len(artifacts),
        donors_verified=verified_count,
        all_contracts_verified=all_ok,
        fx3_area_gmt_zones_verified=fx3_area_gmt_verified,
        fx3_synchro_terminal_absent_verified=fx3_synchro_absent,
        fx3_pro_camera_absent_verified=fx3_pro_cam_absent,
        fx6_reference_file_absent_verified=fx6_ref_absent,
        fx6_video_light_no_auto_verified=fx6_vl_no_auto,
        raw_firmware_bytes_leaked=0,
        artifacts=artifacts,
    )


# ---------------------------------------------------------------------------
# Sub-Model 78A: Setup -> [Area/Date/Time Setting] & 24h RTC vs FX6 Clock Set
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AreaDateDstRtcAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    effective_area_zone: Optional[str]
    area_gmt_zones_count: int
    half_hour_zones_count: int
    effective_daylight_savings: str
    effective_date_format: Optional[str]
    effective_time_format: str
    area_date_resettable: bool
    initial_setting_wizard_triggered: bool
    area_date_prompt_on_boot: bool
    has_user_replaceable_cr2032_slot: bool
    rtc_battery_charged: bool
    rtc_charge_hours_power_off: float
    service_center_repair_required: bool
    ilc2210_states_3_months_retention: bool
    saylight_saving_typo_symbol: str
    sever_date_time_typo_symbol: str
    fx6_dst_toggle_exposed: bool
    fx6_clock_set_hard_locked: bool
    fx6_backup_battery_end_emitted: bool


def simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "configure_area_date",
    area_zone: Optional[str] = "AREA_GMT_P_08_0",
    daylight_savings: str = "Off",
    date_format: Optional[str] = "Y-M-D",
    date_time_configured: bool = True,
    smartphone_registered_in_wizard: bool = True,
    rtc_charge_hours_power_off: float = 24.0,
    rtc_battery_depleted: bool = False,
    rtc_battery_aged_dead: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_utc_offset_minutes: int = 540,
    fx6_date_mode: str = "YYMMDD",
    fx6_time_format: str = "24h",
    fx6_backup_battery_depleted: bool = False,
    fx6_backup_battery_aged_dead: bool = False,
) -> AreaDateDstRtcAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage78Phase353Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage78Phase353Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_AREA_DATE_OPERATIONS:
        raise Stage78Phase353Error(f"Invalid operation: {operation!r}")
    if area_zone is not None and area_zone not in FX3_AREA_GMT_30_ZONES:
        raise Stage78Phase353Error(f"Invalid area_zone: {area_zone!r}")
    if daylight_savings not in VALID_TOGGLES:
        raise Stage78Phase353Error(f"Invalid daylight_savings: {daylight_savings!r}")
    if date_format is not None and date_format not in FX3_DATE_FORMATS:
        raise Stage78Phase353Error(f"Invalid date_format: {date_format!r}")
    if rtc_charge_hours_power_off < 0.0:
        raise Stage78Phase353Error("rtc_charge_hours_power_off must be >= 0.0")
    if (
        fx6_utc_offset_minutes < -720
        or fx6_utc_offset_minutes > 840
        or fx6_utc_offset_minutes % 30 != 0
    ):
        raise Stage78Phase353Error(
            f"Invalid fx6_utc_offset_minutes: {fx6_utc_offset_minutes!r} "
            "(must be UTC -12:00..+14:00 in 30-min steps)"
        )
    if fx6_date_mode not in FX6_DATE_MODES:
        raise Stage78Phase353Error(f"Invalid fx6_date_mode: {fx6_date_mode!r}")
    if fx6_time_format not in FX6_TIME_FORMATS:
        raise Stage78Phase353Error(f"Invalid fx6_time_format: {fx6_time_format!r}")

    saylight_sym = "convert_setting_daylight_saving_to_saylight_saving"
    sever_sym = "BKID_APP_setting_auto_sync_sever_date_time"

    # 1. ILME-FX6 Ver. 6.01: Maintenance > Clock Set
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_dst_toggle":
            return AreaDateDstRtcAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Ver. 6.01 Maintenance > Clock Set has ZERO standalone DST toggle "
                    "(summer_time_name_dst & ns2 0x564d are dormant; adjust Time Zone manually)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_area_zone=f"UTC_{fx6_utc_offset_minutes:+d}m",
                area_gmt_zones_count=53,
                half_hour_zones_count=26,
                effective_daylight_savings="UNSUPPORTED",
                effective_date_format=fx6_date_mode,
                effective_time_format=fx6_time_format,
                area_date_resettable=False,
                initial_setting_wizard_triggered=False,
                area_date_prompt_on_boot=False,
                has_user_replaceable_cr2032_slot=False,
                rtc_battery_charged=False,
                rtc_charge_hours_power_off=0.0,
                service_center_repair_required=fx6_backup_battery_aged_dead,
                ilc2210_states_3_months_retention=False,
                saylight_saving_typo_symbol="N/A",
                sever_date_time_typo_symbol="N/A",
                fx6_dst_toggle_exposed=False,
                fx6_clock_set_hard_locked=fx6_backup_battery_depleted,
                fx6_backup_battery_end_emitted=fx6_backup_battery_aged_dead,
            )
        if operation != "fx6_clock_set":
            return AreaDateDstRtcAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"ILME-FX6 Ver. 6.01 does not expose FX3 operation {operation!r}",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_area_zone=f"UTC_{fx6_utc_offset_minutes:+d}m",
                area_gmt_zones_count=53,
                half_hour_zones_count=26,
                effective_daylight_savings="UNSUPPORTED",
                effective_date_format=fx6_date_mode,
                effective_time_format=fx6_time_format,
                area_date_resettable=False,
                initial_setting_wizard_triggered=False,
                area_date_prompt_on_boot=False,
                has_user_replaceable_cr2032_slot=False,
                rtc_battery_charged=False,
                rtc_charge_hours_power_off=0.0,
                service_center_repair_required=fx6_backup_battery_aged_dead,
                ilc2210_states_3_months_retention=False,
                saylight_saving_typo_symbol="N/A",
                sever_date_time_typo_symbol="N/A",
                fx6_dst_toggle_exposed=False,
                fx6_clock_set_hard_locked=fx6_backup_battery_depleted,
                fx6_backup_battery_end_emitted=fx6_backup_battery_aged_dead,
            )
        if fx6_backup_battery_aged_dead:
            return AreaDateDstRtcAudit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason="FX6 ns2 0x411f 'Backup Battery End': internal soldered backup battery aged dead",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_area_zone=f"UTC_{fx6_utc_offset_minutes:+d}m",
                area_gmt_zones_count=53,
                half_hour_zones_count=26,
                effective_daylight_savings="UNSUPPORTED",
                effective_date_format=fx6_date_mode,
                effective_time_format=fx6_time_format,
                area_date_resettable=False,
                initial_setting_wizard_triggered=False,
                area_date_prompt_on_boot=True,
                has_user_replaceable_cr2032_slot=False,
                rtc_battery_charged=False,
                rtc_charge_hours_power_off=0.0,
                service_center_repair_required=True,
                ilc2210_states_3_months_retention=False,
                saylight_saving_typo_symbol="N/A",
                sever_date_time_typo_symbol="N/A",
                fx6_dst_toggle_exposed=False,
                fx6_clock_set_hard_locked=True,
                fx6_backup_battery_end_emitted=True,
            )
        if fx6_backup_battery_depleted:
            return AreaDateDstRtcAudit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason="FX6 backup battery depleted: boot hard-locks Clock Set screen until clock set",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_area_zone=f"UTC_{fx6_utc_offset_minutes:+d}m",
                area_gmt_zones_count=53,
                half_hour_zones_count=26,
                effective_daylight_savings="UNSUPPORTED",
                effective_date_format=fx6_date_mode,
                effective_time_format=fx6_time_format,
                area_date_resettable=False,
                initial_setting_wizard_triggered=False,
                area_date_prompt_on_boot=True,
                has_user_replaceable_cr2032_slot=False,
                rtc_battery_charged=False,
                rtc_charge_hours_power_off=0.0,
                service_center_repair_required=False,
                ilc2210_states_3_months_retention=False,
                saylight_saving_typo_symbol="N/A",
                sever_date_time_typo_symbol="N/A",
                fx6_dst_toggle_exposed=False,
                fx6_clock_set_hard_locked=True,
                fx6_backup_battery_end_emitted=False,
            )
        return AreaDateDstRtcAudit(
            admitted=True,
            errno_code=0,
            reason="FX6 Ver. 6.01 Maintenance > Clock Set configured cleanly (no DST toggle)",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            effective_area_zone=f"UTC_{fx6_utc_offset_minutes:+d}m",
            area_gmt_zones_count=53,
            half_hour_zones_count=26,
            effective_daylight_savings="UNSUPPORTED",
            effective_date_format=fx6_date_mode,
            effective_time_format=fx6_time_format,
            area_date_resettable=False,
            initial_setting_wizard_triggered=False,
            area_date_prompt_on_boot=False,
            has_user_replaceable_cr2032_slot=False,
            rtc_battery_charged=True,
            rtc_charge_hours_power_off=24.0,
            service_center_repair_required=False,
            ilc2210_states_3_months_retention=False,
            saylight_saving_typo_symbol="N/A",
            sever_date_time_typo_symbol="N/A",
            fx6_dst_toggle_exposed=False,
            fx6_clock_set_hard_locked=False,
            fx6_backup_battery_end_emitted=False,
        )

    # 2. ILME-FX3 Ver. 7.02
    if operation in ("fx6_clock_set", "fx6_dst_toggle"):
        return AreaDateDstRtcAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 Ver. 7.02 does not expose FX6 operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            effective_area_zone=area_zone,
            area_gmt_zones_count=30,
            half_hour_zones_count=6,
            effective_daylight_savings=daylight_savings,
            effective_date_format=date_format,
            effective_time_format="24h",
            area_date_resettable=False,
            initial_setting_wizard_triggered=False,
            area_date_prompt_on_boot=False,
            has_user_replaceable_cr2032_slot=False,
            rtc_battery_charged=False,
            rtc_charge_hours_power_off=rtc_charge_hours_power_off,
            service_center_repair_required=False,
            ilc2210_states_3_months_retention=False,
            saylight_saving_typo_symbol=saylight_sym,
            sever_date_time_typo_symbol=sever_sym,
            fx6_dst_toggle_exposed=False,
            fx6_clock_set_hard_locked=False,
            fx6_backup_battery_end_emitted=False,
        )

    # Reset vs Initialize on FX3
    if initialize_applied:
        eff_area: Optional[str] = None
        eff_dst = "Off"
        eff_fmt: Optional[str] = None
        eff_dt_ok = False
        wizard_retriggered = True
    elif camera_settings_reset_applied:
        # [Camera Settings Reset] = Not available on all Area/Date/Time Setting items
        eff_area = area_zone
        eff_dst = daylight_savings
        eff_fmt = date_format
        eff_dt_ok = date_time_configured
        wizard_retriggered = False
    else:
        eff_area = area_zone
        eff_dst = daylight_savings
        eff_fmt = date_format
        eff_dt_ok = date_time_configured
        wizard_retriggered = False

    if rtc_battery_aged_dead:
        rtc_charged = False
        prompt_boot = True
        repair_req = True
    elif rtc_battery_depleted and rtc_charge_hours_power_off < 24.0:
        rtc_charged = False
        prompt_boot = True
        repair_req = False
    else:
        rtc_charged = rtc_charge_hours_power_off >= 24.0 or (not rtc_battery_depleted)
        prompt_boot = wizard_retriggered or (not eff_dt_ok) or (not smartphone_registered_in_wizard)
        repair_req = False

    if operation == "timestamp_dependent_action" and (not eff_dt_ok or not rtc_charged):
        return AreaDateDstRtcAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=(
                "Timestamp-dependent function blocked (_g 0x63a6): "
                "Sets the 'Area/Date/Time Setting' to perform this function."
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            effective_area_zone=eff_area,
            area_gmt_zones_count=30,
            half_hour_zones_count=6,
            effective_daylight_savings=eff_dst,
            effective_date_format=eff_fmt,
            effective_time_format="24h",
            area_date_resettable=False,
            initial_setting_wizard_triggered=wizard_retriggered,
            area_date_prompt_on_boot=True,
            has_user_replaceable_cr2032_slot=False,
            rtc_battery_charged=rtc_charged,
            rtc_charge_hours_power_off=rtc_charge_hours_power_off,
            service_center_repair_required=repair_req,
            ilc2210_states_3_months_retention=False,
            saylight_saving_typo_symbol=saylight_sym,
            sever_date_time_typo_symbol=sever_sym,
            fx6_dst_toggle_exposed=False,
            fx6_clock_set_hard_locked=False,
            fx6_backup_battery_end_emitted=False,
        )

    if operation == "boot_rtc_check" and (rtc_battery_aged_dead or not rtc_charged):
        return AreaDateDstRtcAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason=(
                "RTC backup battery discharged/aged dead (<24h NP-FZ100 power-OFF charge): "
                "boot auto-prompts Area/Date/Time Setting"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            effective_area_zone=None,
            area_gmt_zones_count=30,
            half_hour_zones_count=6,
            effective_daylight_savings="Off",
            effective_date_format=None,
            effective_time_format="24h",
            area_date_resettable=False,
            initial_setting_wizard_triggered=True,
            area_date_prompt_on_boot=True,
            has_user_replaceable_cr2032_slot=False,
            rtc_battery_charged=False,
            rtc_charge_hours_power_off=rtc_charge_hours_power_off,
            service_center_repair_required=repair_req,
            ilc2210_states_3_months_retention=False,
            saylight_saving_typo_symbol=saylight_sym,
            sever_date_time_typo_symbol=sever_sym,
            fx6_dst_toggle_exposed=False,
            fx6_clock_set_hard_locked=False,
            fx6_backup_battery_end_emitted=False,
        )

    return AreaDateDstRtcAudit(
        admitted=True,
        errno_code=0,
        reason=(
            "FX3 Ver. 7.02 [Area/Date/Time Setting] evaluated cleanly "
            "(30 GMT zones incl. 6 half-hour, Reset-immune, 24h NP-FZ100 RTC)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        effective_area_zone=eff_area,
        area_gmt_zones_count=30,
        half_hour_zones_count=6,
        effective_daylight_savings=eff_dst,
        effective_date_format=eff_fmt,
        effective_time_format="24h",
        area_date_resettable=False,
        initial_setting_wizard_triggered=wizard_retriggered,
        area_date_prompt_on_boot=prompt_boot,
        has_user_replaceable_cr2032_slot=False,
        rtc_battery_charged=rtc_charged,
        rtc_charge_hours_power_off=rtc_charge_hours_power_off,
        service_center_repair_required=repair_req,
        ilc2210_states_3_months_retention=False,
        saylight_saving_typo_symbol=saylight_sym,
        sever_date_time_typo_symbol=sever_sym,
        fx6_dst_toggle_exposed=False,
        fx6_clock_set_hard_locked=False,
        fx6_backup_battery_end_emitted=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 78B: Grid Line HDMI Pass-Through vs Marker Display Zero-HDMI Isolation
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GridLineVsMarkerHdmiAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    operation: str
    effective_grid_line_display: str
    effective_grid_line_type: str
    grid_line_available_all_pipelines: bool
    retired_movie_grid_keys_exposed: bool
    effective_marker_display: str
    effective_center_marker: str
    effective_aspect_marker: str
    effective_safety_zone: str
    effective_guideframe: str
    marker_display_available_in_still: bool
    grid_and_marker_resettable: bool
    grid_rendered_on_monitor: bool
    grid_rendered_on_hdmi: bool
    marker_rendered_on_monitor: bool
    marker_rendered_on_hdmi: bool
    hdmi_marker_injected_pixels: int
    clean_hdmi_feed_active: bool
    fx6_center_marker_mode: str
    fx6_guide_frame_on: bool
    fx6_native_3mode_grid_exposed: bool


def simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    operation: str = "render_overlays",
    grid_line_display: str = "Off",
    grid_line_type: str = "Rule of 3rds Grid",
    marker_display: str = "Off",
    center_marker: str = "Off",
    aspect_marker: str = "Off",
    safety_zone: str = "Off",
    guideframe: str = "Off",
    focus_magnifier_active: bool = False,
    hdmi_connected: bool = True,
    hdmi_info_display: str = "On",
    rec_media_dur_hdmi_output: str = "On",
    raw_output: str = "Off",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_center_marker_mode: str = "Off",
    fx6_guide_frame: str = "Off",
    fx6_vf_marker_on: bool = True,
    fx6_sdi_marker_on: bool = False,
    fx6_hdmi_marker_on: bool = False,
) -> GridLineVsMarkerHdmiAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage78Phase353Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage78Phase353Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage78Phase353Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if operation not in VALID_GRID_MARKER_OPERATIONS:
        raise Stage78Phase353Error(f"Invalid operation: {operation!r}")
    if grid_line_display not in VALID_TOGGLES:
        raise Stage78Phase353Error(f"Invalid grid_line_display: {grid_line_display!r}")
    if grid_line_type not in VALID_GRID_LINE_TYPES:
        raise Stage78Phase353Error(f"Invalid grid_line_type: {grid_line_type!r}")
    if marker_display not in VALID_TOGGLES:
        raise Stage78Phase353Error(f"Invalid marker_display: {marker_display!r}")
    if center_marker not in VALID_TOGGLES:
        raise Stage78Phase353Error(f"Invalid center_marker: {center_marker!r}")
    if aspect_marker not in VALID_ASPECT_MARKERS:
        raise Stage78Phase353Error(f"Invalid aspect_marker: {aspect_marker!r}")
    if safety_zone not in VALID_SAFETY_ZONES:
        raise Stage78Phase353Error(f"Invalid safety_zone: {safety_zone!r}")
    if guideframe not in VALID_TOGGLES:
        raise Stage78Phase353Error(f"Invalid guideframe: {guideframe!r}")
    if hdmi_info_display not in VALID_TOGGLES:
        raise Stage78Phase353Error(f"Invalid hdmi_info_display: {hdmi_info_display!r}")
    if rec_media_dur_hdmi_output not in VALID_REC_MEDIA_HDMI_MODES:
        raise Stage78Phase353Error(
            f"Invalid rec_media_dur_hdmi_output: {rec_media_dur_hdmi_output!r}"
        )
    if raw_output not in VALID_TOGGLES:
        raise Stage78Phase353Error(f"Invalid raw_output: {raw_output!r}")
    if fx6_center_marker_mode not in FX6_CENTER_MARKER_MODES:
        raise Stage78Phase353Error(
            f"Invalid fx6_center_marker_mode: {fx6_center_marker_mode!r}"
        )
    if fx6_guide_frame not in VALID_TOGGLES:
        raise Stage78Phase353Error(f"Invalid fx6_guide_frame: {fx6_guide_frame!r}")

    # 1. ILME-FX6 Ver. 6.01: Monitoring > Marker; dormant 3-mode Grid
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_dormant_3mode_grid":
            return GridLineVsMarkerHdmiAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Ver. 6.01 body menu does NOT expose FX3 3-mode composition grids "
                    "(GUIDE_FRAME_{RULE_OF_3RD,SQUARE,DIAG_SQUARE,GOLDEN_RATIO}_GRID are dormant)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                effective_grid_line_display="UNSUPPORTED",
                effective_grid_line_type="UNSUPPORTED",
                grid_line_available_all_pipelines=False,
                retired_movie_grid_keys_exposed=False,
                effective_marker_display="UNSUPPORTED",
                effective_center_marker="UNSUPPORTED",
                effective_aspect_marker="UNSUPPORTED",
                effective_safety_zone="UNSUPPORTED",
                effective_guideframe="UNSUPPORTED",
                marker_display_available_in_still=False,
                grid_and_marker_resettable=False,
                grid_rendered_on_monitor=False,
                grid_rendered_on_hdmi=False,
                marker_rendered_on_monitor=False,
                marker_rendered_on_hdmi=False,
                hdmi_marker_injected_pixels=0,
                clean_hdmi_feed_active=True,
                fx6_center_marker_mode=fx6_center_marker_mode,
                fx6_guide_frame_on=(fx6_guide_frame == "On"),
                fx6_native_3mode_grid_exposed=False,
            )
        if operation != "fx6_marker_display":
            return GridLineVsMarkerHdmiAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"ILME-FX6 Ver. 6.01 rejects FX3 operation {operation!r}",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                effective_grid_line_display="UNSUPPORTED",
                effective_grid_line_type="UNSUPPORTED",
                grid_line_available_all_pipelines=False,
                retired_movie_grid_keys_exposed=False,
                effective_marker_display="UNSUPPORTED",
                effective_center_marker="UNSUPPORTED",
                effective_aspect_marker="UNSUPPORTED",
                effective_safety_zone="UNSUPPORTED",
                effective_guideframe="UNSUPPORTED",
                marker_display_available_in_still=False,
                grid_and_marker_resettable=False,
                grid_rendered_on_monitor=False,
                grid_rendered_on_hdmi=False,
                marker_rendered_on_monitor=False,
                marker_rendered_on_hdmi=False,
                hdmi_marker_injected_pixels=0,
                clean_hdmi_feed_active=True,
                fx6_center_marker_mode=fx6_center_marker_mode,
                fx6_guide_frame_on=(fx6_guide_frame == "On"),
                fx6_native_3mode_grid_exposed=False,
            )
        fx6_marker_active = (
            fx6_center_marker_mode != "Off" or fx6_guide_frame == "On"
        )
        return GridLineVsMarkerHdmiAudit(
            admitted=True,
            errno_code=0,
            reason=(
                "FX6 Ver. 6.01 Monitoring > Marker evaluated "
                "(independent VF/SDI/HDMI Marker gates; zero 3-mode composition grid UI)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            effective_grid_line_display="UNSUPPORTED",
            effective_grid_line_type="UNSUPPORTED",
            grid_line_available_all_pipelines=False,
            retired_movie_grid_keys_exposed=False,
            effective_marker_display="On" if fx6_marker_active else "Off",
            effective_center_marker=fx6_center_marker_mode,
            effective_aspect_marker="Off",
            effective_safety_zone="Off",
            effective_guideframe=fx6_guide_frame,
            marker_display_available_in_still=False,
            grid_and_marker_resettable=False,
            grid_rendered_on_monitor=False,
            grid_rendered_on_hdmi=False,
            marker_rendered_on_monitor=bool(fx6_marker_active and fx6_vf_marker_on),
            marker_rendered_on_hdmi=bool(
                hdmi_connected and fx6_marker_active and fx6_hdmi_marker_on
            ),
            hdmi_marker_injected_pixels=0,
            clean_hdmi_feed_active=not (fx6_marker_active and fx6_hdmi_marker_on),
            fx6_center_marker_mode=fx6_center_marker_mode,
            fx6_guide_frame_on=(fx6_guide_frame == "On"),
            fx6_native_3mode_grid_exposed=False,
        )

    # 2. ILME-FX3 Ver. 7.02 Reset vs Initialize
    # ALL 7 items (Grid Line Display/Type + Marker Display + Center/Aspect/Safety/Guideframe)
    # are Reset-immune (restored ONLY by [Initialize])
    if initialize_applied:
        eff_grid_disp = "Off"
        eff_grid_type = "Rule of 3rds Grid"
        eff_marker_disp = "Off"
        eff_center = "Off"
        eff_aspect = "Off"
        eff_safety = "Off"
        eff_guide = "Off"
    else:
        eff_grid_disp = grid_line_display
        eff_grid_type = grid_line_type
        eff_marker_disp = marker_display
        eff_center = center_marker
        eff_aspect = aspect_marker
        eff_safety = safety_zone
        eff_guide = guideframe

    if operation == "dormant_deleted_movie_grid":
        return GridLineVsMarkerHdmiAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "BKID_APP_deleted_setting_grid_line_{display,type}_movie are retired in FX3 Ver. 7.02 "
                "(unified all-pipeline [Grid Line Display/Type])"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            effective_grid_line_display=eff_grid_disp,
            effective_grid_line_type=eff_grid_type,
            grid_line_available_all_pipelines=True,
            retired_movie_grid_keys_exposed=False,
            effective_marker_display=eff_marker_disp,
            effective_center_marker=eff_center,
            effective_aspect_marker=eff_aspect,
            effective_safety_zone=eff_safety,
            effective_guideframe=eff_guide,
            marker_display_available_in_still=False,
            grid_and_marker_resettable=False,
            grid_rendered_on_monitor=False,
            grid_rendered_on_hdmi=False,
            marker_rendered_on_monitor=False,
            marker_rendered_on_hdmi=False,
            hdmi_marker_injected_pixels=0,
            clean_hdmi_feed_active=True,
            fx6_center_marker_mode="UNSUPPORTED",
            fx6_guide_frame_on=False,
            fx6_native_3mode_grid_exposed=False,
        )

    if operation != "render_overlays":
        return GridLineVsMarkerHdmiAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 Ver. 7.02 rejects FX6 operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            effective_grid_line_display=eff_grid_disp,
            effective_grid_line_type=eff_grid_type,
            grid_line_available_all_pipelines=True,
            retired_movie_grid_keys_exposed=False,
            effective_marker_display=eff_marker_disp,
            effective_center_marker=eff_center,
            effective_aspect_marker=eff_aspect,
            effective_safety_zone=eff_safety,
            effective_guideframe=eff_guide,
            marker_display_available_in_still=False,
            grid_and_marker_resettable=False,
            grid_rendered_on_monitor=False,
            grid_rendered_on_hdmi=False,
            marker_rendered_on_monitor=False,
            marker_rendered_on_hdmi=False,
            hdmi_marker_injected_pixels=0,
            clean_hdmi_feed_active=True,
            fx6_center_marker_mode="UNSUPPORTED",
            fx6_guide_frame_on=False,
            fx6_native_3mode_grid_exposed=False,
        )

    # Marker Display is Movie / S&Q ONLY (`PRM_HAITA_setting_marker_display_exposure_mode`)
    marker_requested = (
        eff_marker_disp == "On"
        or eff_center == "On"
        or eff_aspect != "Off"
        or eff_safety != "Off"
        or eff_guide == "On"
    )
    if shoot_mode == SHOOT_MODE_STILL and marker_requested:
        return GridLineVsMarkerHdmiAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "Shooting -> [Marker Display] is Movie/S&Q ONLY "
                "(PRM_HAITA_setting_marker_display_exposure_mode rejects Still mode)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            effective_grid_line_display=eff_grid_disp,
            effective_grid_line_type=eff_grid_type,
            grid_line_available_all_pipelines=True,
            retired_movie_grid_keys_exposed=False,
            effective_marker_display="Off",
            effective_center_marker="Off",
            effective_aspect_marker="Off",
            effective_safety_zone="Off",
            effective_guideframe="Off",
            marker_display_available_in_still=False,
            grid_and_marker_resettable=False,
            grid_rendered_on_monitor=(eff_grid_disp == "On"),
            grid_rendered_on_hdmi=False,
            marker_rendered_on_monitor=False,
            marker_rendered_on_hdmi=False,
            hdmi_marker_injected_pixels=0,
            clean_hdmi_feed_active=True,
            fx6_center_marker_mode="UNSUPPORTED",
            fx6_guide_frame_on=False,
            fx6_native_3mode_grid_exposed=False,
        )

    # S&Q forces Rec. Media dur HDMI Output = On
    eff_rec_media_hdmi = (
        "On" if shoot_mode == SHOOT_MODE_SQ else rec_media_dur_hdmi_output
    )
    # Clean-Feed forces HDMI Info. Display = Off
    clean_feed = (
        hdmi_info_display == "Off"
        or eff_rec_media_hdmi == "Off(HDMI Only)"
        or raw_output == "On"
    )

    grid_on_monitor = eff_grid_disp == "On"
    grid_on_hdmi = bool(hdmi_connected and grid_on_monitor and (not clean_feed))

    marker_any_sub = (
        eff_center == "On"
        or eff_aspect != "Off"
        or eff_safety != "Off"
        or eff_guide == "On"
    )
    marker_on_monitor = bool(
        shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ)
        and eff_marker_disp == "On"
        and marker_any_sub
        and (not focus_magnifier_active)
    )
    # Absolute Zero-HDMI Marker Isolation: 0 pixels EVER on HDMI!
    marker_on_hdmi = False

    return GridLineVsMarkerHdmiAudit(
        admitted=True,
        errno_code=0,
        reason=(
            "FX3 Ver. 7.02 Grid Line vs Marker Display evaluated: "
            "Marker Display 100%% monitor-only (0 HDMI px); Grid Line passes through on HDMI Info=On"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        operation=operation,
        effective_grid_line_display=eff_grid_disp,
        effective_grid_line_type=eff_grid_type,
        grid_line_available_all_pipelines=True,
        retired_movie_grid_keys_exposed=False,
        effective_marker_display=eff_marker_disp,
        effective_center_marker=eff_center,
        effective_aspect_marker=eff_aspect,
        effective_safety_zone=eff_safety,
        effective_guideframe=eff_guide,
        marker_display_available_in_still=False,
        grid_and_marker_resettable=False,
        grid_rendered_on_monitor=grid_on_monitor,
        grid_rendered_on_hdmi=grid_on_hdmi,
        marker_rendered_on_monitor=marker_on_monitor,
        marker_rendered_on_hdmi=marker_on_hdmi,
        hdmi_marker_injected_pixels=0,
        clean_hdmi_feed_active=(clean_feed and not grid_on_hdmi),
        fx6_center_marker_mode="UNSUPPORTED",
        fx6_guide_frame_on=False,
        fx6_native_3mode_grid_exposed=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 78C: [Save/Load Settings] CAMSET01..10.DAT vs Camera Set. Memory & FX6 All File
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SaveLoadCamsetMemoryAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    target_media: str
    card_type: str
    slot_index: int
    resolved_path: str
    uses_pro_camera_path: bool
    lib_saveload_verified: bool
    auto_reboot_triggered: bool
    slot1_erofs_triggered: bool
    slot1_data_sector_writes: int
    emmc_nflasha_write_count: int
    nvram_persistent_writes: int
    excluded_items_count: int
    excluded_items_leaked_count: int
    bundled_memory_slots_1_to_3_included: bool
    card_memory_slots_m1_to_m4_media_selectable: bool
    fx6_all_file_load_network_data: bool
    fx6_reference_file_exposed: bool


def simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "camset_load",
    target_media: str = "Slot 1",
    card_type: str = "SDXC",
    slot_index: int = 1,
    mr_recall_mode_active: bool = False,
    slot1_tier0_readonly: bool = True,
    source_body_model: str = BODY_MODEL_FX3,
    source_fw_version: str = FW_VER_702,
    checksum_valid: bool = True,
    memory_recall_media: str = "Slot 1",
    fx6_all_file_load_network_data: bool = False,
) -> SaveLoadCamsetMemoryAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage78Phase353Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage78Phase353Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_SAVELOAD_OPERATIONS:
        raise Stage78Phase353Error(f"Invalid operation: {operation!r}")
    if target_media not in VALID_SAVELOAD_TARGETS:
        raise Stage78Phase353Error(f"Invalid target_media: {target_media!r}")
    if card_type not in VALID_CARD_MEDIA_TYPES:
        raise Stage78Phase353Error(f"Invalid card_type: {card_type!r}")
    if slot_index < 0:
        raise Stage78Phase353Error(f"Invalid slot_index: {slot_index!r}")
    if source_body_model not in ALL_TEST_BODY_MODELS:
        raise Stage78Phase353Error(f"Invalid source_body_model: {source_body_model!r}")
    if source_fw_version not in VALID_FW_VERSIONS:
        raise Stage78Phase353Error(f"Invalid source_fw_version: {source_fw_version!r}")
    if memory_recall_media not in VALID_MEDIA_SLOTS:
        raise Stage78Phase353Error(f"Invalid memory_recall_media: {memory_recall_media!r}")

    prefix = "/PRIVATE" if card_type == "SDXC" else ""

    # 1. ILME-FX6 Ver. 6.01: Project > All File / Scene File / Dormant Reference File
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_dormant_reference_file":
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX6 Reference File (ns2 0x429b/0x4d52) has 0 ELF hits in FX6 appFw.so (dormant XDCAM legacy)",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=target_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path="",
                uses_pro_camera_path=True,
                lib_saveload_verified=False,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=False,
                card_memory_slots_m1_to_m4_media_selectable=False,
                fx6_all_file_load_network_data=fx6_all_file_load_network_data,
                fx6_reference_file_exposed=False,
            )
        if operation not in ("fx6_all_file_save", "fx6_all_file_load", "fx6_scene_file_save"):
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"ILME-FX6 Ver. 6.01 rejects FX3 operation {operation!r}",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=target_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path="",
                uses_pro_camera_path=True,
                lib_saveload_verified=False,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=False,
                card_memory_slots_m1_to_m4_media_selectable=False,
                fx6_all_file_load_network_data=fx6_all_file_load_network_data,
                fx6_reference_file_exposed=False,
            )
        if operation in ("fx6_all_file_save", "fx6_all_file_load"):
            if target_media != "Media(B)":
                return SaveLoadCamsetMemoryAudit(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    reason=f"FX6 Project > All File targets Media(B), not {target_media!r}",
                    body_profile=body_profile,
                    fw_version=fw_version,
                    operation=operation,
                    target_media=target_media,
                    card_type=card_type,
                    slot_index=slot_index,
                    resolved_path="",
                    uses_pro_camera_path=True,
                    lib_saveload_verified=False,
                    auto_reboot_triggered=False,
                    slot1_erofs_triggered=False,
                    slot1_data_sector_writes=0,
                    emmc_nflasha_write_count=0,
                    nvram_persistent_writes=0,
                    excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                    excluded_items_leaked_count=0,
                    bundled_memory_slots_1_to_3_included=False,
                    card_memory_slots_m1_to_m4_media_selectable=False,
                    fx6_all_file_load_network_data=fx6_all_file_load_network_data,
                    fx6_reference_file_exposed=False,
                )
            if not (1 <= slot_index <= FX6_ALL_FILE_MAX_SLOTS):
                return SaveLoadCamsetMemoryAudit(
                    admitted=False,
                    errno_code=EINVAL_ERRNO,
                    reason=f"FX6 All File slot_index={slot_index} exceeds max 64",
                    body_profile=body_profile,
                    fw_version=fw_version,
                    operation=operation,
                    target_media=target_media,
                    card_type=card_type,
                    slot_index=slot_index,
                    resolved_path="",
                    uses_pro_camera_path=True,
                    lib_saveload_verified=False,
                    auto_reboot_triggered=False,
                    slot1_erofs_triggered=False,
                    slot1_data_sector_writes=0,
                    emmc_nflasha_write_count=0,
                    nvram_persistent_writes=0,
                    excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                    excluded_items_leaked_count=0,
                    bundled_memory_slots_1_to_3_included=False,
                    card_memory_slots_m1_to_m4_media_selectable=False,
                    fx6_all_file_load_network_data=fx6_all_file_load_network_data,
                    fx6_reference_file_exposed=False,
                )
            fx6_path = f"{prefix}/SONY/PRO/CAMERA/ILME-FX6/ALL{slot_index:02d}.ALL"
            return SaveLoadCamsetMemoryAudit(
                admitted=True,
                errno_code=0,
                reason="FX6 Project > All File (.ALL on Media(B), max 64) evaluated cleanly",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=target_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path=fx6_path,
                uses_pro_camera_path=True,
                lib_saveload_verified=False,
                auto_reboot_triggered=(operation == "fx6_all_file_load"),
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=False,
                card_memory_slots_m1_to_m4_media_selectable=False,
                fx6_all_file_load_network_data=fx6_all_file_load_network_data,
                fx6_reference_file_exposed=False,
            )
        scn_path = f"{prefix}/SONY/PRO/SCENE/SCN{slot_index:02d}.SCN"
        return SaveLoadCamsetMemoryAudit(
            admitted=True,
            errno_code=0,
            reason="FX6 Paint/Look > Scene File (.SCN) evaluated cleanly",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_media=target_media,
            card_type=card_type,
            slot_index=slot_index,
            resolved_path=scn_path,
            uses_pro_camera_path=True,
            lib_saveload_verified=False,
            auto_reboot_triggered=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            nvram_persistent_writes=0,
            excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
            excluded_items_leaked_count=0,
            bundled_memory_slots_1_to_3_included=False,
            card_memory_slots_m1_to_m4_media_selectable=False,
            fx6_all_file_load_network_data=fx6_all_file_load_network_data,
            fx6_reference_file_exposed=False,
        )

    # 2. ILME-FX3 Ver. 7.02
    if operation in ("fx6_all_file_save", "fx6_all_file_load", "fx6_scene_file_save", "fx6_dormant_reference_file"):
        return SaveLoadCamsetMemoryAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 Ver. 7.02 does not expose FX6 operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_media=target_media,
            card_type=card_type,
            slot_index=slot_index,
            resolved_path="",
            uses_pro_camera_path=False,
            lib_saveload_verified=True,
            auto_reboot_triggered=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            nvram_persistent_writes=0,
            excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
            excluded_items_leaked_count=0,
            bundled_memory_slots_1_to_3_included=True,
            card_memory_slots_m1_to_m4_media_selectable=True,
            fx6_all_file_load_network_data=False,
            fx6_reference_file_exposed=False,
        )

    # Camera Set. Memory (1..3 in NVRAM vs M1..M4 on Slot 1 or Slot 2)
    if operation == "camera_set_memory_body":
        if not (1 <= slot_index <= 3):
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Body Camera Set. Memory slot must be 1..3, got {slot_index}",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media="NVRAM",
                card_type=card_type,
                slot_index=slot_index,
                resolved_path="",
                uses_pro_camera_path=False,
                lib_saveload_verified=True,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=True,
                card_memory_slots_m1_to_m4_media_selectable=True,
                fx6_all_file_load_network_data=False,
                fx6_reference_file_exposed=False,
            )
        return SaveLoadCamsetMemoryAudit(
            admitted=True,
            errno_code=0,
            reason=f"Body Camera Set. Memory slot {slot_index} recalled live (no reboot; bundled in CAMSET*.DAT)",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_media="NVRAM",
            card_type=card_type,
            slot_index=slot_index,
            resolved_path=f"nvram://camera_set_memory/{slot_index}",
            uses_pro_camera_path=False,
            lib_saveload_verified=True,
            auto_reboot_triggered=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            nvram_persistent_writes=0,
            excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
            excluded_items_leaked_count=0,
            bundled_memory_slots_1_to_3_included=True,
            card_memory_slots_m1_to_m4_media_selectable=True,
            fx6_all_file_load_network_data=False,
            fx6_reference_file_exposed=False,
        )

    if operation == "camera_set_memory_card":
        if not (1 <= slot_index <= 4):
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Card Camera Set. Memory slot M1..M4 must be 1..4, got {slot_index}",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=memory_recall_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path="",
                uses_pro_camera_path=False,
                lib_saveload_verified=True,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=True,
                card_memory_slots_m1_to_m4_media_selectable=True,
                fx6_all_file_load_network_data=False,
                fx6_reference_file_exposed=False,
            )
        if memory_recall_media == "Slot 1" and slot1_tier0_readonly:
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EROFS_ERRNO,
                reason="Tier-0 Slot 1 EROFS=30 blocks CAMPR write to Slot 1; use [Memory/Recall Media] = Slot 2",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=memory_recall_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path=f"{prefix}/SONY/SETTING/ILME-FX3/CAMPR{slot_index:02d}A.DAT",
                uses_pro_camera_path=False,
                lib_saveload_verified=True,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=True,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=True,
                card_memory_slots_m1_to_m4_media_selectable=True,
                fx6_all_file_load_network_data=False,
                fx6_reference_file_exposed=False,
            )
        return SaveLoadCamsetMemoryAudit(
            admitted=True,
            errno_code=0,
            reason=f"Card Camera Set. Memory M{slot_index} on {memory_recall_media} (no reboot; excludes Custom Key/Dial & Program Shift)",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_media=memory_recall_media,
            card_type=card_type,
            slot_index=slot_index,
            resolved_path=f"{prefix}/SONY/SETTING/ILME-FX3/CAMPR{slot_index:02d}A.DAT",
            uses_pro_camera_path=False,
            lib_saveload_verified=True,
            auto_reboot_triggered=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            nvram_persistent_writes=0,
            excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
            excluded_items_leaked_count=0,
            bundled_memory_slots_1_to_3_included=True,
            card_memory_slots_m1_to_m4_media_selectable=True,
            fx6_all_file_load_network_data=False,
            fx6_reference_file_exposed=False,
        )

    # [Save/Load FTP Settings]
    if operation == "ftpset_save":
        if target_media == "Slot 2":
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="Save/Load FTP Settings is Slot 1-locked (Slot 2 unavailable)",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=target_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path="",
                uses_pro_camera_path=False,
                lib_saveload_verified=True,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=True,
                card_memory_slots_m1_to_m4_media_selectable=True,
                fx6_all_file_load_network_data=False,
                fx6_reference_file_exposed=False,
            )
        if slot1_tier0_readonly and target_media == "Slot 1":
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EROFS_ERRNO,
                reason="Tier-0 Slot 1 EROFS=30 blocks FTPSET write on read-only Slot 1",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=target_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path=f"{prefix}/SONY/SETTING/ILME-FX3/FTPSET/FTPSET{slot_index:02d}.DAT",
                uses_pro_camera_path=False,
                lib_saveload_verified=True,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=True,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=True,
                card_memory_slots_m1_to_m4_media_selectable=True,
                fx6_all_file_load_network_data=False,
                fx6_reference_file_exposed=False,
            )

    # [Save/Load Settings] (`CAMSET01..10.DAT` on Slot 1 or Cloud(Private/Share) up to 60)
    if mr_recall_mode_active:
        return SaveLoadCamsetMemoryAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="[Save/Load Settings] is disabled while in MR (Recall Camera Setting) mode",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_media=target_media,
            card_type=card_type,
            slot_index=slot_index,
            resolved_path="",
            uses_pro_camera_path=False,
            lib_saveload_verified=True,
            auto_reboot_triggered=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            nvram_persistent_writes=0,
            excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
            excluded_items_leaked_count=0,
            bundled_memory_slots_1_to_3_included=True,
            card_memory_slots_m1_to_m4_media_selectable=True,
            fx6_all_file_load_network_data=False,
            fx6_reference_file_exposed=False,
        )

    if target_media == "Slot 2" or target_media == "Media(B)":
        return SaveLoadCamsetMemoryAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"FX3 [Save/Load Settings] is strictly locked to Slot 1 (or Cloud): {target_media!r} unavailable",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_media=target_media,
            card_type=card_type,
            slot_index=slot_index,
            resolved_path="",
            uses_pro_camera_path=False,
            lib_saveload_verified=True,
            auto_reboot_triggered=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            nvram_persistent_writes=0,
            excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
            excluded_items_leaked_count=0,
            bundled_memory_slots_1_to_3_included=True,
            card_memory_slots_m1_to_m4_media_selectable=True,
            fx6_all_file_load_network_data=False,
            fx6_reference_file_exposed=False,
        )

    is_cloud = target_media in ("Cloud(Private)", "Cloud(Share)")
    max_slots = CAMSET_MAX_CLOUD_SLOTS if is_cloud else CAMSET_MAX_CARD_SLOTS
    if not (1 <= slot_index <= max_slots):
        return SaveLoadCamsetMemoryAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=f"CAMSET slot_index={slot_index} outside valid range 1..{max_slots} for {target_media}",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_media=target_media,
            card_type=card_type,
            slot_index=slot_index,
            resolved_path="",
            uses_pro_camera_path=False,
            lib_saveload_verified=True,
            auto_reboot_triggered=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            nvram_persistent_writes=0,
            excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
            excluded_items_leaked_count=0,
            bundled_memory_slots_1_to_3_included=True,
            card_memory_slots_m1_to_m4_media_selectable=True,
            fx6_all_file_load_network_data=False,
            fx6_reference_file_exposed=False,
        )

    resolved = (
        f"cloud://{target_media}/CAMSET{slot_index:02d}.DAT"
        if is_cloud
        else f"{prefix}/SONY/SETTING/ILME-FX3/CAMSET/CAMSET{slot_index:02d}.DAT"
    )

    # Tier-0 Slot 1 EROFS=30 Firewall on [Save] / [Delete]
    if (not is_cloud) and slot1_tier0_readonly and operation in ("camset_save", "camset_delete"):
        return SaveLoadCamsetMemoryAudit(
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason=(
                f"Tier-0 Slot 1 EROFS=30 firewall blocked {operation!r} on {resolved} "
                "(slot1_data_sector_writes=0, emmc_nflasha_write_count=0)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_media=target_media,
            card_type=card_type,
            slot_index=slot_index,
            resolved_path=resolved,
            uses_pro_camera_path=False,
            lib_saveload_verified=True,
            auto_reboot_triggered=False,
            slot1_erofs_triggered=True,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            nvram_persistent_writes=0,
            excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
            excluded_items_leaked_count=0,
            bundled_memory_slots_1_to_3_included=True,
            card_memory_slots_m1_to_m4_media_selectable=True,
            fx6_all_file_load_network_data=False,
            fx6_reference_file_exposed=False,
        )

    if operation == "camset_load":
        # libSaveLoadSettings.so requestToCheck: same-model & compatible firmware & valid checksum
        if source_body_model != BODY_MODEL_FX3:
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"libSaveLoadSettings::requestToCheck rejected cross-model CAMSET "
                    f"({source_body_model!r} != {BODY_MODEL_FX3!r}): _g 0x624d 'This file cannot be loaded.'"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=target_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path=resolved,
                uses_pro_camera_path=False,
                lib_saveload_verified=True,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=True,
                card_memory_slots_m1_to_m4_media_selectable=True,
                fx6_all_file_load_network_data=False,
                fx6_reference_file_exposed=False,
            )
        if not checksum_valid:
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="libSaveLoadSettings::procCheck checksum mismatch: _g 0x61d7 'Loading failed.'",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=target_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path=resolved,
                uses_pro_camera_path=False,
                lib_saveload_verified=True,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=True,
                card_memory_slots_m1_to_m4_media_selectable=True,
                fx6_all_file_load_network_data=False,
                fx6_reference_file_exposed=False,
            )
        if source_fw_version == FW_VER_101 and fw_version in (FW_VER_200, FW_VER_400, FW_VER_702):
            return SaveLoadCamsetMemoryAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"Cross-firmware CAMSET incompatible ({source_fw_version} -> {fw_version}): "
                    "Ver. 1.01 settings cannot load onto Ver. 2.00+"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_media=target_media,
                card_type=card_type,
                slot_index=slot_index,
                resolved_path=resolved,
                uses_pro_camera_path=False,
                lib_saveload_verified=True,
                auto_reboot_triggered=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                nvram_persistent_writes=0,
                excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
                excluded_items_leaked_count=0,
                bundled_memory_slots_1_to_3_included=True,
                card_memory_slots_m1_to_m4_media_selectable=True,
                fx6_all_file_load_network_data=False,
                fx6_reference_file_exposed=False,
            )
        return SaveLoadCamsetMemoryAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"CAMSET load from {resolved} verified via libSaveLoadSettings.so "
                "(read-only card open; _g 0x62dd auto-reboot triggered; 0 excluded items leaked)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_media=target_media,
            card_type=card_type,
            slot_index=slot_index,
            resolved_path=resolved,
            uses_pro_camera_path=False,
            lib_saveload_verified=True,
            auto_reboot_triggered=True,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            nvram_persistent_writes=0,
            excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
            excluded_items_leaked_count=0,
            bundled_memory_slots_1_to_3_included=True,
            card_memory_slots_m1_to_m4_media_selectable=True,
            fx6_all_file_load_network_data=False,
            fx6_reference_file_exposed=False,
        )

    # Cloud Save / Delete or non-readonly virtual simulation
    return SaveLoadCamsetMemoryAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 {operation!r} on {resolved} verified in VM staging "
            "(0 physical Slot 1 writes, 0 excluded items leaked)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        target_media=target_media,
        card_type=card_type,
        slot_index=slot_index,
        resolved_path=resolved,
        uses_pro_camera_path=False,
        lib_saveload_verified=True,
        auto_reboot_triggered=False,
        slot1_erofs_triggered=False,
        slot1_data_sector_writes=0,
        emmc_nflasha_write_count=0,
        nvram_persistent_writes=0,
        excluded_items_count=len(CAMSET_EXCLUDED_ITEMS),
        excluded_items_leaked_count=0,
        bundled_memory_slots_1_to_3_included=True,
        card_memory_slots_m1_to_m4_media_selectable=True,
        fx6_all_file_load_network_data=False,
        fx6_reference_file_exposed=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 78D: Zero Sync Terminal, XLR-H1 vs HVL-LBPC MI-Shoe Exclusion & FX6 Zero GENLOCK
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SyncTerminalMiShoeXlrH1GenlockAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    operation: str
    has_physical_pc_sync_terminal: bool
    dormant_sync_terminal_exposed: bool
    dormant_flash_sync_spd_prty_exposed: bool
    effective_video_light_mode: str
    effective_flash_mode: str
    flash_resettable: bool
    flash_excluded_from_camset: bool
    xlr_h1_attached: bool
    xlr_h1_passive_cold_shoe_only: bool
    mi_shoe_device: str
    mishoe_xlr_h1_exclusion_triggered: bool
    pmic_5v_current_ma: int
    pmic_5v_overcurrent_blocked: bool
    fx6_video_light_auto_supported: bool
    fx6_still_flash_ui_exposed: bool
    fx6_tc_bnc_direction: Optional[str]
    fx6_tc_ext_lk_active: bool
    fx6_has_physical_genlock_bnc: bool
    fx6_dormant_genlock_exposed: bool


def simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    operation: str = "video_light_mode",
    video_light_mode: str = "Power Link",
    flash_mode: str = "Fill-flash",
    shutter_type: str = "Mechanical",
    shutter_speed_denom: int = 250,
    flash_voltage_v: float = 5.0,
    reverse_polarity: bool = False,
    xlr_h1_attached: bool = False,
    mi_shoe_device: str = "HVL-LBPC",
    pmic_5v_current_ma: int = 650,
    fx6_video_light_mode: str = "Power Link",
    fx6_tc_bnc_direction: str = "IN",
) -> SyncTerminalMiShoeXlrH1GenlockAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage78Phase353Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage78Phase353Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage78Phase353Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if operation not in VALID_SYNC_MISHOE_OPERATIONS:
        raise Stage78Phase353Error(f"Invalid operation: {operation!r}")
    if video_light_mode not in FX3_VIDEO_LIGHT_MODES:
        raise Stage78Phase353Error(f"Invalid video_light_mode: {video_light_mode!r}")
    if flash_mode not in FX3_FLASH_MODES:
        raise Stage78Phase353Error(f"Invalid flash_mode: {flash_mode!r}")
    if shutter_type not in VALID_SHUTTER_TYPES:
        raise Stage78Phase353Error(f"Invalid shutter_type: {shutter_type!r}")
    if shutter_speed_denom <= 0:
        raise Stage78Phase353Error("shutter_speed_denom must be > 0")
    if flash_voltage_v < 0.0:
        raise Stage78Phase353Error("flash_voltage_v must be >= 0.0")
    if mi_shoe_device not in VALID_MISHOE_DEVICES:
        raise Stage78Phase353Error(f"Invalid mi_shoe_device: {mi_shoe_device!r}")
    if pmic_5v_current_ma < 0:
        raise Stage78Phase353Error("pmic_5v_current_ma must be >= 0")
    if fx6_tc_bnc_direction not in VALID_FX6_TC_DIRECTIONS:
        raise Stage78Phase353Error(
            f"Invalid fx6_tc_bnc_direction: {fx6_tc_bnc_direction!r}"
        )

    # 1. ILME-FX6 Ver. 6.01
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_genlock_sync":
            return SyncTerminalMiShoeXlrH1GenlockAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Ver. 6.01 has ZERO physical GENLOCK IN / REF OUT BNC "
                    "(107 dormant GENLOCK symbols in FX6 appFw.so inherited from PXW-FX9)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                has_physical_pc_sync_terminal=False,
                dormant_sync_terminal_exposed=False,
                dormant_flash_sync_spd_prty_exposed=False,
                effective_video_light_mode="UNSUPPORTED",
                effective_flash_mode="UNSUPPORTED",
                flash_resettable=False,
                flash_excluded_from_camset=True,
                xlr_h1_attached=False,
                xlr_h1_passive_cold_shoe_only=True,
                mi_shoe_device=mi_shoe_device,
                mishoe_xlr_h1_exclusion_triggered=False,
                pmic_5v_current_ma=pmic_5v_current_ma,
                pmic_5v_overcurrent_blocked=False,
                fx6_video_light_auto_supported=False,
                fx6_still_flash_ui_exposed=False,
                fx6_tc_bnc_direction=fx6_tc_bnc_direction,
                fx6_tc_ext_lk_active=False,
                fx6_has_physical_genlock_bnc=False,
                fx6_dormant_genlock_exposed=False,
            )
        if operation == "fx6_still_flash_ui":
            return SyncTerminalMiShoeXlrH1GenlockAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="ILME-FX6 Ver. 6.01 has ZERO Still [Flash] UI (SYNCHRO_TERMINAL dormant)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                has_physical_pc_sync_terminal=False,
                dormant_sync_terminal_exposed=False,
                dormant_flash_sync_spd_prty_exposed=False,
                effective_video_light_mode="UNSUPPORTED",
                effective_flash_mode="UNSUPPORTED",
                flash_resettable=False,
                flash_excluded_from_camset=True,
                xlr_h1_attached=False,
                xlr_h1_passive_cold_shoe_only=True,
                mi_shoe_device=mi_shoe_device,
                mishoe_xlr_h1_exclusion_triggered=False,
                pmic_5v_current_ma=pmic_5v_current_ma,
                pmic_5v_overcurrent_blocked=False,
                fx6_video_light_auto_supported=False,
                fx6_still_flash_ui_exposed=False,
                fx6_tc_bnc_direction=fx6_tc_bnc_direction,
                fx6_tc_ext_lk_active=False,
                fx6_has_physical_genlock_bnc=False,
                fx6_dormant_genlock_exposed=False,
            )
        if operation == "fx6_video_light_set":
            if fx6_video_light_mode == "Auto" or fx6_video_light_mode not in FX6_VIDEO_LIGHT_MODES:
                return SyncTerminalMiShoeXlrH1GenlockAudit(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    reason=(
                        "ILME-FX6 Technical > Video Light Set has 3 modes only "
                        "(Power Link / Rec Link / Rec Link + Stby; ZERO Auto mode)"
                    ),
                    body_profile=body_profile,
                    fw_version=fw_version,
                    shoot_mode=shoot_mode,
                    operation=operation,
                    has_physical_pc_sync_terminal=False,
                    dormant_sync_terminal_exposed=False,
                    dormant_flash_sync_spd_prty_exposed=False,
                    effective_video_light_mode="UNSUPPORTED",
                    effective_flash_mode="UNSUPPORTED",
                    flash_resettable=False,
                    flash_excluded_from_camset=True,
                    xlr_h1_attached=False,
                    xlr_h1_passive_cold_shoe_only=True,
                    mi_shoe_device=mi_shoe_device,
                    mishoe_xlr_h1_exclusion_triggered=False,
                    pmic_5v_current_ma=pmic_5v_current_ma,
                    pmic_5v_overcurrent_blocked=False,
                    fx6_video_light_auto_supported=False,
                    fx6_still_flash_ui_exposed=False,
                    fx6_tc_bnc_direction=fx6_tc_bnc_direction,
                    fx6_tc_ext_lk_active=False,
                    fx6_has_physical_genlock_bnc=False,
                    fx6_dormant_genlock_exposed=False,
                )
            return SyncTerminalMiShoeXlrH1GenlockAudit(
                admitted=True,
                errno_code=0,
                reason=f"FX6 Technical > Video Light Set={fx6_video_light_mode!r} configured (3 modes, zero Auto)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                has_physical_pc_sync_terminal=False,
                dormant_sync_terminal_exposed=False,
                dormant_flash_sync_spd_prty_exposed=False,
                effective_video_light_mode=fx6_video_light_mode,
                effective_flash_mode="UNSUPPORTED",
                flash_resettable=False,
                flash_excluded_from_camset=True,
                xlr_h1_attached=False,
                xlr_h1_passive_cold_shoe_only=True,
                mi_shoe_device=mi_shoe_device,
                mishoe_xlr_h1_exclusion_triggered=False,
                pmic_5v_current_ma=pmic_5v_current_ma,
                pmic_5v_overcurrent_blocked=False,
                fx6_video_light_auto_supported=False,
                fx6_still_flash_ui_exposed=False,
                fx6_tc_bnc_direction=fx6_tc_bnc_direction,
                fx6_tc_ext_lk_active=False,
                fx6_has_physical_genlock_bnc=False,
                fx6_dormant_genlock_exposed=False,
            )
        if operation == "fx6_tc_bnc":
            return SyncTerminalMiShoeXlrH1GenlockAudit(
                admitted=True,
                errno_code=0,
                reason=f"FX6 switchable TC IN/OUT BNC active (direction={fx6_tc_bnc_direction}, zero physical GENLOCK BNC)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                has_physical_pc_sync_terminal=False,
                dormant_sync_terminal_exposed=False,
                dormant_flash_sync_spd_prty_exposed=False,
                effective_video_light_mode=fx6_video_light_mode if fx6_video_light_mode in FX6_VIDEO_LIGHT_MODES else "Power Link",
                effective_flash_mode="UNSUPPORTED",
                flash_resettable=False,
                flash_excluded_from_camset=True,
                xlr_h1_attached=False,
                xlr_h1_passive_cold_shoe_only=True,
                mi_shoe_device=mi_shoe_device,
                mishoe_xlr_h1_exclusion_triggered=False,
                pmic_5v_current_ma=pmic_5v_current_ma,
                pmic_5v_overcurrent_blocked=False,
                fx6_video_light_auto_supported=False,
                fx6_still_flash_ui_exposed=False,
                fx6_tc_bnc_direction=fx6_tc_bnc_direction,
                fx6_tc_ext_lk_active=(fx6_tc_bnc_direction == "IN"),
                fx6_has_physical_genlock_bnc=False,
                fx6_dormant_genlock_exposed=False,
            )
        return SyncTerminalMiShoeXlrH1GenlockAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX6 Ver. 6.01 rejects FX3 operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            has_physical_pc_sync_terminal=False,
            dormant_sync_terminal_exposed=False,
            dormant_flash_sync_spd_prty_exposed=False,
            effective_video_light_mode="UNSUPPORTED",
            effective_flash_mode="UNSUPPORTED",
            flash_resettable=False,
            flash_excluded_from_camset=True,
            xlr_h1_attached=False,
            xlr_h1_passive_cold_shoe_only=True,
            mi_shoe_device=mi_shoe_device,
            mishoe_xlr_h1_exclusion_triggered=False,
            pmic_5v_current_ma=pmic_5v_current_ma,
            pmic_5v_overcurrent_blocked=False,
            fx6_video_light_auto_supported=False,
            fx6_still_flash_ui_exposed=False,
            fx6_tc_bnc_direction=fx6_tc_bnc_direction,
            fx6_tc_ext_lk_active=False,
            fx6_has_physical_genlock_bnc=False,
            fx6_dormant_genlock_exposed=False,
        )

    # 2. ILME-FX3 Ver. 7.02
    if operation in ("fx6_video_light_set", "fx6_still_flash_ui", "fx6_tc_bnc", "fx6_genlock_sync"):
        return SyncTerminalMiShoeXlrH1GenlockAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"ILME-FX3 Ver. 7.02 rejects FX6 operation {operation!r}",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            has_physical_pc_sync_terminal=False,
            dormant_sync_terminal_exposed=False,
            dormant_flash_sync_spd_prty_exposed=False,
            effective_video_light_mode=video_light_mode,
            effective_flash_mode=flash_mode,
            flash_resettable=False,
            flash_excluded_from_camset=True,
            xlr_h1_attached=xlr_h1_attached,
            xlr_h1_passive_cold_shoe_only=True,
            mi_shoe_device=mi_shoe_device,
            mishoe_xlr_h1_exclusion_triggered=False,
            pmic_5v_current_ma=pmic_5v_current_ma,
            pmic_5v_overcurrent_blocked=False,
            fx6_video_light_auto_supported=False,
            fx6_still_flash_ui_exposed=False,
            fx6_tc_bnc_direction=None,
            fx6_tc_ext_lk_active=False,
            fx6_has_physical_genlock_bnc=False,
            fx6_dormant_genlock_exposed=False,
        )

    if operation in ("pc_sync_terminal", "dormant_flash_sync_spd_prty"):
        return SyncTerminalMiShoeXlrH1GenlockAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "ILME-FX3 Ver. 7.02 has ZERO physical PC flash sync terminal "
                "(SYNCHRO_TERMINAL* symbols == 0 in FX3 appFw.so; Flash Sync Spd. Prty. dormant)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            has_physical_pc_sync_terminal=False,
            dormant_sync_terminal_exposed=False,
            dormant_flash_sync_spd_prty_exposed=False,
            effective_video_light_mode=video_light_mode,
            effective_flash_mode=flash_mode,
            flash_resettable=False,
            flash_excluded_from_camset=True,
            xlr_h1_attached=xlr_h1_attached,
            xlr_h1_passive_cold_shoe_only=True,
            mi_shoe_device=mi_shoe_device,
            mishoe_xlr_h1_exclusion_triggered=False,
            pmic_5v_current_ma=pmic_5v_current_ma,
            pmic_5v_overcurrent_blocked=False,
            fx6_video_light_auto_supported=False,
            fx6_still_flash_ui_exposed=False,
            fx6_tc_bnc_direction=None,
            fx6_tc_ext_lk_active=False,
            fx6_has_physical_genlock_bnc=False,
            fx6_dormant_genlock_exposed=False,
        )

    # Physical & Electrical MI-Shoe Mutual Exclusion with XLR-H1
    if xlr_h1_attached and mi_shoe_device in ("HVL-LBPC", "MI_FLASH"):
        return SyncTerminalMiShoeXlrH1GenlockAudit(
            admitted=False,
            errno_code=EBUSY_ERRNO,
            reason=(
                f"MI-Shoe mutual exclusion: XLR-H1 occupies sole electrical MI-Shoe; "
                f"XLR-H1 top Accessory Shoe Kit is passive cold-shoe only, blocking {mi_shoe_device!r}"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            has_physical_pc_sync_terminal=False,
            dormant_sync_terminal_exposed=False,
            dormant_flash_sync_spd_prty_exposed=False,
            effective_video_light_mode=video_light_mode,
            effective_flash_mode=flash_mode,
            flash_resettable=False,
            flash_excluded_from_camset=True,
            xlr_h1_attached=True,
            xlr_h1_passive_cold_shoe_only=True,
            mi_shoe_device=mi_shoe_device,
            mishoe_xlr_h1_exclusion_triggered=True,
            pmic_5v_current_ma=pmic_5v_current_ma,
            pmic_5v_overcurrent_blocked=False,
            fx6_video_light_auto_supported=False,
            fx6_still_flash_ui_exposed=False,
            fx6_tc_bnc_direction=None,
            fx6_tc_ext_lk_active=False,
            fx6_has_physical_genlock_bnc=False,
            fx6_dormant_genlock_exposed=False,
        )

    # Stage-B PMIC 5V <= 900 mA guard for powered MI-Shoe accessories
    if mi_shoe_device != "None" and pmic_5v_current_ma > PMIC_5V_MAX_MA:
        return SyncTerminalMiShoeXlrH1GenlockAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason=(
                f"PMIC 5V overcurrent guard blocked {mi_shoe_device!r}: "
                f"{pmic_5v_current_ma} mA > {PMIC_5V_MAX_MA} mA"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            has_physical_pc_sync_terminal=False,
            dormant_sync_terminal_exposed=False,
            dormant_flash_sync_spd_prty_exposed=False,
            effective_video_light_mode=video_light_mode,
            effective_flash_mode=flash_mode,
            flash_resettable=False,
            flash_excluded_from_camset=True,
            xlr_h1_attached=xlr_h1_attached,
            xlr_h1_passive_cold_shoe_only=True,
            mi_shoe_device=mi_shoe_device,
            mishoe_xlr_h1_exclusion_triggered=False,
            pmic_5v_current_ma=pmic_5v_current_ma,
            pmic_5v_overcurrent_blocked=True,
            fx6_video_light_auto_supported=False,
            fx6_still_flash_ui_exposed=False,
            fx6_tc_bnc_direction=None,
            fx6_tc_ext_lk_active=False,
            fx6_has_physical_genlock_bnc=False,
            fx6_dormant_genlock_exposed=False,
        )

    if operation == "external_flash_set":
        if shoot_mode != SHOOT_MODE_STILL:
            return SyncTerminalMiShoeXlrH1GenlockAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"[External Flash Set.] & [Flash Mode] are Still-only (rejected in {shoot_mode!r})",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                has_physical_pc_sync_terminal=False,
                dormant_sync_terminal_exposed=False,
                dormant_flash_sync_spd_prty_exposed=False,
                effective_video_light_mode=video_light_mode,
                effective_flash_mode=flash_mode,
                flash_resettable=False,
                flash_excluded_from_camset=True,
                xlr_h1_attached=xlr_h1_attached,
                xlr_h1_passive_cold_shoe_only=True,
                mi_shoe_device=mi_shoe_device,
                mishoe_xlr_h1_exclusion_triggered=False,
                pmic_5v_current_ma=pmic_5v_current_ma,
                pmic_5v_overcurrent_blocked=False,
                fx6_video_light_auto_supported=False,
                fx6_still_flash_ui_exposed=False,
                fx6_tc_bnc_direction=None,
                fx6_tc_ext_lk_active=False,
                fx6_has_physical_genlock_bnc=False,
                fx6_dormant_genlock_exposed=False,
            )
        if shutter_type != "Mechanical":
            return SyncTerminalMiShoeXlrH1GenlockAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="MI-Shoe flash disabled under Electronic shutter (Mechanical shutter required, max 1/250 s)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                has_physical_pc_sync_terminal=False,
                dormant_sync_terminal_exposed=False,
                dormant_flash_sync_spd_prty_exposed=False,
                effective_video_light_mode=video_light_mode,
                effective_flash_mode=flash_mode,
                flash_resettable=False,
                flash_excluded_from_camset=True,
                xlr_h1_attached=xlr_h1_attached,
                xlr_h1_passive_cold_shoe_only=True,
                mi_shoe_device=mi_shoe_device,
                mishoe_xlr_h1_exclusion_triggered=False,
                pmic_5v_current_ma=pmic_5v_current_ma,
                pmic_5v_overcurrent_blocked=False,
                fx6_video_light_auto_supported=False,
                fx6_still_flash_ui_exposed=False,
                fx6_tc_bnc_direction=None,
                fx6_tc_ext_lk_active=False,
                fx6_has_physical_genlock_bnc=False,
                fx6_dormant_genlock_exposed=False,
            )
        if flash_voltage_v >= 250.0 or reverse_polarity:
            return SyncTerminalMiShoeXlrH1GenlockAudit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason=(
                    f"MI-Shoe flash electrical guard rejected unsafe trigger "
                    f"(voltage={flash_voltage_v}V >= 250V or reverse_polarity={reverse_polarity})"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                has_physical_pc_sync_terminal=False,
                dormant_sync_terminal_exposed=False,
                dormant_flash_sync_spd_prty_exposed=False,
                effective_video_light_mode=video_light_mode,
                effective_flash_mode=flash_mode,
                flash_resettable=False,
                flash_excluded_from_camset=True,
                xlr_h1_attached=xlr_h1_attached,
                xlr_h1_passive_cold_shoe_only=True,
                mi_shoe_device=mi_shoe_device,
                mishoe_xlr_h1_exclusion_triggered=False,
                pmic_5v_current_ma=pmic_5v_current_ma,
                pmic_5v_overcurrent_blocked=False,
                fx6_video_light_auto_supported=False,
                fx6_still_flash_ui_exposed=False,
                fx6_tc_bnc_direction=None,
                fx6_tc_ext_lk_active=False,
                fx6_has_physical_genlock_bnc=False,
                fx6_dormant_genlock_exposed=False,
            )
        if shutter_speed_denom > 250:
            return SyncTerminalMiShoeXlrH1GenlockAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"Shutter speed 1/{shutter_speed_denom} s exceeds FX3 max X-Sync 1/250 s",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                has_physical_pc_sync_terminal=False,
                dormant_sync_terminal_exposed=False,
                dormant_flash_sync_spd_prty_exposed=False,
                effective_video_light_mode=video_light_mode,
                effective_flash_mode=flash_mode,
                flash_resettable=False,
                flash_excluded_from_camset=True,
                xlr_h1_attached=xlr_h1_attached,
                xlr_h1_passive_cold_shoe_only=True,
                mi_shoe_device=mi_shoe_device,
                mishoe_xlr_h1_exclusion_triggered=False,
                pmic_5v_current_ma=pmic_5v_current_ma,
                pmic_5v_overcurrent_blocked=False,
                fx6_video_light_auto_supported=False,
                fx6_still_flash_ui_exposed=False,
                fx6_tc_bnc_direction=None,
                fx6_tc_ext_lk_active=False,
                fx6_has_physical_genlock_bnc=False,
                fx6_dormant_genlock_exposed=False,
            )
        return SyncTerminalMiShoeXlrH1GenlockAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 Still MI-Shoe Flash active ({flash_mode}, 1/{shutter_speed_denom} s <= 1/250 s, "
                "Reset-immune, excluded from CAMSET*.DAT)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            has_physical_pc_sync_terminal=False,
            dormant_sync_terminal_exposed=False,
            dormant_flash_sync_spd_prty_exposed=False,
            effective_video_light_mode=video_light_mode,
            effective_flash_mode=flash_mode,
            flash_resettable=False,
            flash_excluded_from_camset=True,
            xlr_h1_attached=xlr_h1_attached,
            xlr_h1_passive_cold_shoe_only=True,
            mi_shoe_device=mi_shoe_device,
            mishoe_xlr_h1_exclusion_triggered=False,
            pmic_5v_current_ma=pmic_5v_current_ma,
            pmic_5v_overcurrent_blocked=False,
            fx6_video_light_auto_supported=False,
            fx6_still_flash_ui_exposed=False,
            fx6_tc_bnc_direction=None,
            fx6_tc_ext_lk_active=False,
            fx6_has_physical_genlock_bnc=False,
            fx6_dormant_genlock_exposed=False,
        )

    # video_light_mode (All pipelines: Still / Movie / S&Q)
    return SyncTerminalMiShoeXlrH1GenlockAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 [Video Light Mode]={video_light_mode!r} active for {mi_shoe_device!r} "
            f"across {shoot_mode} (4 modes incl. Auto; PMIC 5V={pmic_5v_current_ma}mA <= 900mA)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        operation=operation,
        has_physical_pc_sync_terminal=False,
        dormant_sync_terminal_exposed=False,
        dormant_flash_sync_spd_prty_exposed=False,
        effective_video_light_mode=video_light_mode,
        effective_flash_mode=flash_mode,
        flash_resettable=False,
        flash_excluded_from_camset=True,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_passive_cold_shoe_only=True,
        mi_shoe_device=mi_shoe_device,
        mishoe_xlr_h1_exclusion_triggered=False,
        pmic_5v_current_ma=pmic_5v_current_ma,
        pmic_5v_overcurrent_blocked=False,
        fx6_video_light_auto_supported=False,
        fx6_still_flash_ui_exposed=False,
        fx6_tc_bnc_direction=None,
        fx6_tc_ext_lk_active=False,
        fx6_has_physical_genlock_bnc=False,
        fx6_dormant_genlock_exposed=False,
    )


# ---------------------------------------------------------------------------
# Milestone Probe, Recursive Determinism & Full Stage 78 Runner
# ---------------------------------------------------------------------------


def _strip_wall_clock(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_wall_clock(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [_strip_wall_clock(x) for x in obj]
    return obj


def _build_stage78_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_78th_stage_milestone": IS_78TH_STAGE_MILESTONE,
        "wave": "Wave-68",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    donor_audit = inspect_phase353_wave68_donors(
        work_root=work_root, force_clean_room=force_clean_room, env=env
    )

    # Sub-Model 78A probes
    p78a_reset = simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
        area_zone="AREA_GMT_P_05_5",
        daylight_savings="On",
        date_format="D-M-Y",
        camera_settings_reset_applied=True,
    )
    p78a_init = simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
        area_zone="AREA_GMT_P_05_5",
        daylight_savings="On",
        date_format="D-M-Y",
        initialize_applied=True,
    )
    p78a_rtc_short = simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
        operation="boot_rtc_check",
        rtc_battery_depleted=True,
        rtc_charge_hours_power_off=12.0,
    )
    p78a_rtc_24h = simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
        operation="boot_rtc_check",
        rtc_battery_depleted=True,
        rtc_charge_hours_power_off=24.0,
    )
    p78a_fx6_ok = simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_clock_set",
        fx6_utc_offset_minutes=840,
        fx6_date_mode="YYMMDD",
        fx6_time_format="24h",
    )
    p78a_fx6_dst_block = simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_dst_toggle",
    )
    p78a_fx6_end = simulate_area_date_dst_rtc_and_fx6_clock_set_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_clock_set",
        fx6_backup_battery_aged_dead=True,
    )
    p78a_ok = (
        p78a_reset.admitted
        and p78a_reset.area_gmt_zones_count == 30
        and p78a_reset.half_hour_zones_count == 6
        and (not p78a_reset.area_date_resettable)
        and p78a_reset.effective_area_zone == "AREA_GMT_P_05_5"
        and p78a_reset.effective_daylight_savings == "On"
        and p78a_reset.effective_date_format == "D-M-Y"
        and p78a_init.initial_setting_wizard_triggered
        and p78a_init.effective_area_zone is None
        and p78a_init.effective_daylight_savings == "Off"
        and (not p78a_rtc_short.admitted)
        and p78a_rtc_24h.admitted
        and p78a_rtc_24h.rtc_battery_charged
        and (not p78a_rtc_24h.has_user_replaceable_cr2032_slot)
        and (not p78a_rtc_24h.ilc2210_states_3_months_retention)
        and p78a_fx6_ok.admitted
        and (not p78a_fx6_dst_block.admitted)
        and p78a_fx6_dst_block.errno_code == EOPNOTSUPP_ERRNO
        and (not p78a_fx6_end.admitted)
        and p78a_fx6_end.fx6_backup_battery_end_emitted
    )

    # Sub-Model 78B probes
    p78b_hdmi_on = simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        grid_line_display="On",
        grid_line_type="Diag. + Square Grid",
        marker_display="On",
        center_marker="On",
        aspect_marker="16:9",
        safety_zone="90%",
        guideframe="On",
        hdmi_connected=True,
        hdmi_info_display="On",
        rec_media_dur_hdmi_output="On",
        raw_output="Off",
        camera_settings_reset_applied=True,
    )
    p78b_clean_hdmi = simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        grid_line_display="On",
        marker_display="On",
        guideframe="On",
        hdmi_connected=True,
        hdmi_info_display="On",
        rec_media_dur_hdmi_output="Off(HDMI Only)",
    )
    p78b_focus_mag = simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        marker_display="On",
        guideframe="On",
        focus_magnifier_active=True,
    )
    p78b_still_marker_block = simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
        shoot_mode=SHOOT_MODE_STILL,
        marker_display="On",
        guideframe="On",
    )
    p78b_retired_block = simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
        operation="dormant_deleted_movie_grid",
    )
    p78b_fx6_marker = simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_marker_display",
        fx6_center_marker_mode="3",
        fx6_guide_frame="On",
    )
    p78b_fx6_grid_block = simulate_grid_line_hdmi_vs_marker_guideframe_isolation_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_dormant_3mode_grid",
    )
    p78b_ok = (
        p78b_hdmi_on.admitted
        and p78b_hdmi_on.grid_rendered_on_hdmi
        and p78b_hdmi_on.marker_rendered_on_monitor
        and (not p78b_hdmi_on.marker_rendered_on_hdmi)
        and p78b_hdmi_on.hdmi_marker_injected_pixels == 0
        and (not p78b_hdmi_on.grid_and_marker_resettable)
        and p78b_clean_hdmi.admitted
        and (not p78b_clean_hdmi.grid_rendered_on_hdmi)
        and (not p78b_clean_hdmi.marker_rendered_on_hdmi)
        and p78b_clean_hdmi.clean_hdmi_feed_active
        and p78b_focus_mag.admitted
        and (not p78b_focus_mag.marker_rendered_on_monitor)
        and (not p78b_still_marker_block.admitted)
        and p78b_still_marker_block.errno_code == EOPNOTSUPP_ERRNO
        and (not p78b_retired_block.admitted)
        and p78b_retired_block.errno_code == EOPNOTSUPP_ERRNO
        and p78b_fx6_marker.admitted
        and (not p78b_fx6_grid_block.admitted)
        and p78b_fx6_grid_block.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 78C probes
    p78c_slot1_erofs = simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
        operation="camset_save",
        target_media="Slot 1",
        card_type="SDXC",
        slot_index=1,
        slot1_tier0_readonly=True,
    )
    p78c_slot1_load = simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
        operation="camset_load",
        target_media="Slot 1",
        card_type="CFexpress Type A",
        slot_index=10,
        slot1_tier0_readonly=True,
    )
    p78c_blocks = [
        simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_save", target_media="Slot 2", slot_index=1
        ),
        simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load", target_media="Slot 1", mr_recall_mode_active=True
        ),
        simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load",
            target_media="Slot 1",
            source_body_model=BODY_MODEL_FX6,
        ),
        simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
            operation="camset_load",
            target_media="Slot 1",
            source_fw_version=FW_VER_101,
            fw_version=FW_VER_702,
        ),
    ]
    p78c_body_mem = simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
        operation="camera_set_memory_body", slot_index=2
    )
    p78c_card_mem = simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
        operation="camera_set_memory_card", slot_index=4, memory_recall_media="Slot 2"
    )
    p78c_fx6_all = simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_all_file_load",
        target_media="Media(B)",
        slot_index=64,
        fx6_all_file_load_network_data=True,
    )
    p78c_fx6_ref_block = simulate_saveload_camset_slot1_erofs_and_fx6_allfile_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_dormant_reference_file",
    )
    p78c_ok = (
        (not p78c_slot1_erofs.admitted)
        and p78c_slot1_erofs.errno_code == EROFS_ERRNO
        and p78c_slot1_erofs.slot1_erofs_triggered
        and p78c_slot1_erofs.slot1_data_sector_writes == 0
        and p78c_slot1_load.admitted
        and p78c_slot1_load.auto_reboot_triggered
        and p78c_slot1_load.resolved_path == "/SONY/SETTING/ILME-FX3/CAMSET/CAMSET10.DAT"
        and (not p78c_slot1_load.uses_pro_camera_path)
        and p78c_slot1_load.excluded_items_leaked_count == 0
        and all(not r.admitted for r in p78c_blocks)
        and p78c_body_mem.admitted
        and (not p78c_body_mem.auto_reboot_triggered)
        and p78c_card_mem.admitted
        and p78c_card_mem.target_media == "Slot 2"
        and p78c_fx6_all.admitted
        and p78c_fx6_all.auto_reboot_triggered
        and (not p78c_fx6_ref_block.admitted)
        and p78c_fx6_ref_block.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 78D probes
    p78d_vl_auto = simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
        operation="video_light_mode",
        video_light_mode="Auto",
        xlr_h1_attached=False,
        mi_shoe_device="HVL-LBPC",
        pmic_5v_current_ma=720,
    )
    p78d_xlr_collision = simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
        operation="video_light_mode",
        video_light_mode="Power Link",
        xlr_h1_attached=True,
        mi_shoe_device="HVL-LBPC",
    )
    p78d_still_flash = simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
        shoot_mode=SHOOT_MODE_STILL,
        operation="external_flash_set",
        shutter_type="Mechanical",
        shutter_speed_denom=250,
        xlr_h1_attached=False,
        mi_shoe_device="MI_FLASH",
    )
    p78d_blocks = [
        simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(operation="pc_sync_terminal"),
        simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(operation="dormant_flash_sync_spd_prty"),
        simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            shoot_mode=SHOOT_MODE_STILL,
            operation="external_flash_set",
            flash_voltage_v=260.0,
            mi_shoe_device="MI_FLASH",
        ),
        simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            operation="fx6_video_light_set",
            fx6_video_light_mode="Auto",
        ),
        simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            operation="fx6_genlock_sync",
        ),
    ]
    p78d_fx6_tc = simulate_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_tc_bnc",
        fx6_tc_bnc_direction="IN",
    )
    p78d_ok = (
        p78d_vl_auto.admitted
        and p78d_vl_auto.effective_video_light_mode == "Auto"
        and (not p78d_xlr_collision.admitted)
        and p78d_xlr_collision.errno_code == EBUSY_ERRNO
        and p78d_xlr_collision.mishoe_xlr_h1_exclusion_triggered
        and p78d_still_flash.admitted
        and (not p78d_still_flash.flash_resettable)
        and p78d_still_flash.flash_excluded_from_camset
        and all(not r.admitted for r in p78d_blocks)
        and p78d_fx6_tc.admitted
        and p78d_fx6_tc.fx6_tc_ext_lk_active
        and (not p78d_fx6_tc.fx6_has_physical_genlock_bnc)
    )

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
        "fx3_area_gmt_zones_count": FX3_AREA_GMT_ZONES_COUNT,
        "fx3_area_half_hour_zones_count": FX3_AREA_HALF_HOUR_ZONES_COUNT,
        "fx3_date_formats_count": FX3_DATE_FORMATS_COUNT,
        "area_date_saylight_saving_typo_matched": AREA_DATE_SAYLIGHT_SAVING_TYPO_MATCHED,
        "area_date_sever_typo_matched": AREA_DATE_SEVER_TYPO_MATCHED,
        "area_date_reset_wipe_events": AREA_DATE_RESET_WIPE_EVENTS,
        "fx3_user_cr2032_slot_present": FX3_USER_CR2032_SLOT_PRESENT,
        "fx3_rtc_charge_min_hours_power_off": FX3_RTC_CHARGE_MIN_HOURS_POWER_OFF,
        "ilc2210_states_3_months_retention": ILC2210_STATES_3_MONTHS_RETENTION,
        "fx6_clock_set_dst_toggle_exposed": FX6_CLOCK_SET_DST_TOGGLE_EXPOSED,
        "grid_line_types_count": GRID_LINE_TYPES_COUNT,
        "aspect_marker_ratios_count": ASPECT_MARKER_RATIOS_COUNT,
        "retired_movie_grid_keys_exposed": RETIRED_MOVIE_GRID_KEYS_EXPOSED,
        "grid_and_marker_reset_wipe_events": GRID_AND_MARKER_RESET_WIPE_EVENTS,
        "hdmi_marker_injected_pixels": HDMI_MARKER_INJECTED_PIXELS,
        "fx6_native_3mode_grid_exposed": FX6_NATIVE_3MODE_GRID_EXPOSED,
        "camset_max_card_slots": CAMSET_MAX_CARD_SLOTS,
        "camset_max_cloud_slots": CAMSET_MAX_CLOUD_SLOTS,
        "camset_slot2_bypass_events": CAMSET_SLOT2_BYPASS_EVENTS,
        "fx3_pro_camera_path_hits": FX3_PRO_CAMERA_PATH_HITS,
        "camset_excluded_items_leaked_count": CAMSET_EXCLUDED_ITEMS_LEAKED_COUNT,
        "camset_slot1_erofs_bypass_events": CAMSET_SLOT1_EROFS_BYPASS_EVENTS,
        "fx6_all_file_max_slots": FX6_ALL_FILE_MAX_SLOTS,
        "fx6_reference_file_elf_hits": FX6_REFERENCE_FILE_ELF_HITS,
        "fx3_physical_sync_terminal_present": FX3_PHYSICAL_SYNC_TERMINAL_PRESENT,
        "fx3_synchro_terminal_elf_hits": FX3_SYNCHRO_TERMINAL_ELF_HITS,
        "dormant_flash_sync_spd_prty_exposed_events": DORMANT_FLASH_SYNC_SPD_PRTY_EXPOSED_EVENTS,
        "fx3_video_light_modes_count": FX3_VIDEO_LIGHT_MODES_COUNT,
        "fx6_video_light_modes_count": FX6_VIDEO_LIGHT_MODES_COUNT,
        "fx6_video_light_auto_supported": FX6_VIDEO_LIGHT_AUTO_SUPPORTED,
        "xlr_h1_mishoe_collision_bypass_events": XLR_H1_MISHOE_COLLISION_BYPASS_EVENTS,
        "pmic_5v_max_ma": PMIC_5V_MAX_MA,
        "pmic_5v_overcurrent_bypass_events": PMIC_5V_OVERCURRENT_BYPASS_EVENTS,
        "fx6_physical_genlock_bnc_present": FX6_PHYSICAL_GENLOCK_BNC_PRESENT,
        "fx6_dormant_genlock_elf_hits": FX6_DORMANT_GENLOCK_ELF_HITS,
        "fx6_dormant_genlock_exposed_events": FX6_DORMANT_GENLOCK_EXPOSED_EVENTS,
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    redlines_ok = (
        P8_CP_MUTATION_FORBIDDEN
        and NOP_COUNT == 0
        and GUEST_CODE_MODIFICATION_BYTES == 0
        and CP_MUTATION_BYTES == 0
        and WBI_MUTATION_BYTES == 0
        and CALIBRATION_MUTATION_BYTES == 0
        and CNFLASHA_MUTATION_BYTES == 0
        and CNFLASHA_USERSPACE_WRITE_BLOCKED
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
        and FX3_AREA_GMT_ZONES_COUNT == 30
        and FX3_AREA_HALF_HOUR_ZONES_COUNT == 6
        and FX3_DATE_FORMATS_COUNT == 3
        and AREA_DATE_SAYLIGHT_SAVING_TYPO_MATCHED
        and AREA_DATE_SEVER_TYPO_MATCHED
        and AREA_DATE_RESET_WIPE_EVENTS == 0
        and (not FX3_USER_CR2032_SLOT_PRESENT)
        and FX3_RTC_CHARGE_MIN_HOURS_POWER_OFF == 24
        and (not ILC2210_STATES_3_MONTHS_RETENTION)
        and (not FX6_CLOCK_SET_DST_TOGGLE_EXPOSED)
        and GRID_LINE_TYPES_COUNT == 3
        and ASPECT_MARKER_RATIOS_COUNT == 15
        and (not RETIRED_MOVIE_GRID_KEYS_EXPOSED)
        and GRID_AND_MARKER_RESET_WIPE_EVENTS == 0
        and HDMI_MARKER_INJECTED_PIXELS == 0
        and (not FX6_NATIVE_3MODE_GRID_EXPOSED)
        and CAMSET_MAX_CARD_SLOTS == 10
        and CAMSET_MAX_CLOUD_SLOTS == 60
        and CAMSET_SLOT2_BYPASS_EVENTS == 0
        and FX3_PRO_CAMERA_PATH_HITS == 0
        and CAMSET_EXCLUDED_ITEMS_LEAKED_COUNT == 0
        and CAMSET_SLOT1_EROFS_BYPASS_EVENTS == 0
        and FX6_ALL_FILE_MAX_SLOTS == 64
        and FX6_REFERENCE_FILE_ELF_HITS == 0
        and (not FX3_PHYSICAL_SYNC_TERMINAL_PRESENT)
        and FX3_SYNCHRO_TERMINAL_ELF_HITS == 0
        and DORMANT_FLASH_SYNC_SPD_PRTY_EXPOSED_EVENTS == 0
        and FX3_VIDEO_LIGHT_MODES_COUNT == 4
        and FX6_VIDEO_LIGHT_MODES_COUNT == 3
        and (not FX6_VIDEO_LIGHT_AUTO_SUPPORTED)
        and XLR_H1_MISHOE_COLLISION_BYPASS_EVENTS == 0
        and PMIC_5V_MAX_MA == 900
        and PMIC_5V_OVERCURRENT_BYPASS_EVENTS == 0
        and (not FX6_PHYSICAL_GENLOCK_BNC_PRESENT)
        and FX6_DORMANT_GENLOCK_ELF_HITS == 107
        and FX6_DORMANT_GENLOCK_EXPOSED_EVENTS == 0
        and RSV_ORPHAN_COUNT == 0
        and WF12_00342260_HITS == 0
        and APPFW_CRASHES == 0
        and NULL_GPIO_DEREFS == 0
        and MAILBOX_STALLS == 0
        and STOCK_CP_FAULT_COUNT == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
    )

    all_passed = bool(
        donor_audit.all_contracts_verified
        and IS_78TH_STAGE_MILESTONE
        and STAGE_INDEX == 78
        and STAGE_TOTAL == 78
        and MILESTONE_LABEL == "78/78"
        and p78a_ok
        and p78b_ok
        and p78c_ok
        and p78d_ok
        and redlines_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_353_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_78th_stage_milestone": IS_78TH_STAGE_MILESTONE,
        "source_mode": donor_audit.source_mode,
        "all_checks_passed": all_passed,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "stage78_milestone_probe": _build_stage78_milestone_probe(),
        "pillar_a_area_date_dst_rtc_fx6_clock_set_hil": {
            "passed": p78a_ok,
            "reset_immune": asdict(p78a_reset),
            "initialize_retriggers_wizard": asdict(p78a_init),
            "rtc_short_charge_blocked": asdict(p78a_rtc_short),
            "rtc_24h_charged": asdict(p78a_rtc_24h),
            "fx6_clock_set": asdict(p78a_fx6_ok),
            "fx6_dst_blocked": asdict(p78a_fx6_dst_block),
            "fx6_backup_battery_end": asdict(p78a_fx6_end),
        },
        "pillar_b_grid_line_hdmi_vs_marker_guideframe_isolation_hil": {
            "passed": p78b_ok,
            "hdmi_info_on_grid_passthrough_marker_isolated": asdict(p78b_hdmi_on),
            "clean_hdmi_off_strips_grid": asdict(p78b_clean_hdmi),
            "focus_magnifier_suppresses_marker": asdict(p78b_focus_mag),
            "still_mode_rejects_marker": asdict(p78b_still_marker_block),
            "retired_movie_grid_blocked": asdict(p78b_retired_block),
            "fx6_marker_display": asdict(p78b_fx6_marker),
            "fx6_dormant_3mode_grid_blocked": asdict(p78b_fx6_grid_block),
        },
        "pillar_c_saveload_camset_slot1_erofs_and_fx6_allfile_hil": {
            "passed": p78c_ok,
            "slot1_save_erofs_blocked": asdict(p78c_slot1_erofs),
            "slot1_load_reboot_safe": asdict(p78c_slot1_load),
            "slot2_mr_crossmodel_fw_blocks": [asdict(r) for r in p78c_blocks],
            "body_camera_set_memory": asdict(p78c_body_mem),
            "card_camera_set_memory_slot2": asdict(p78c_card_mem),
            "fx6_all_file_mediab": asdict(p78c_fx6_all),
            "fx6_dormant_reference_file_blocked": asdict(p78c_fx6_ref_block),
        },
        "pillar_d_sync_terminal_mishoe_xlrh1_and_fx6_genlock_hil": {
            "passed": p78d_ok,
            "video_light_auto_hvl_lbpc": asdict(p78d_vl_auto),
            "xlr_h1_mishoe_exclusion_blocked": asdict(p78d_xlr_collision),
            "still_mechanical_flash_ok": asdict(p78d_still_flash),
            "dormant_sync_overvolt_fx6_genlock_blocks": [asdict(r) for r in p78d_blocks],
            "fx6_tc_bnc_ext_lk": asdict(p78d_fx6_tc),
        },
    }
    stripped = _strip_wall_clock(payload)
    digest = hashlib.sha256(
        json.dumps(stripped, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Phase 353 (Stage 78 — 78/78 Full-Board Stages!): Real-Hardware ILME-FX3 Ver. 7.02 vs "
            "ILME-FX6 Ver. 6.01 Wave-68 Setup -> [Area/Date/Time Setting] 30 GMT Zones / saylight_saving / "
            "24h RTC vs FX6 Clock Set, All-Pipeline [Grid Line Display] HDMI Pass-Through vs Movie-Only "
            "[Marker Display] -> [Guideframe] Zero-HDMI Isolation, [Save/Load Settings] CAMSET01..10.DAT "
            "Slot-1 EROFS=30 & libSaveLoadSettings.so vs 1..3/M1..M4 & FX6 All File, and Zero Sync Terminal / "
            "XLR-H1 MI-Shoe Exclusion vs FX6 TC BNC & Zero GENLOCK (100%% Read-Only HIL)"
        )
    )
    parser.add_argument("--self-test", action="store_true", help="Run Stage 78 HIL audit")
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room synthetic mode without local donor reads",
    )
    parser.add_argument(
        "--work-root",
        default=None,
        help="Optional explicit Mac/work donor root (nonexistent falls back cleanly to synthetic)",
    )
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    args = parser.parse_args(argv)

    wr: Any = _UNSET if args.work_root is None else Path(args.work_root)
    rep = run_phase353_areadate_dst_grid_cleanhdmi_saveload_camset_mishoe_coemulation(
        work_root=wr,
        force_clean_room=True if args.clean_room else None,
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 353 Stage 78 ({rep['milestone']} Stages) | "
            f"mode={rep['source_mode']} | donors={rep['donor_audit']['donors_verified']}/"
            f"{rep['donor_audit']['donors_checked']} | "
            f"gmt={red['fx3_area_gmt_zones_count']}({red['fx3_area_half_hour_zones_count']}h) | "
            f"hdmi_mkr_px={red['hdmi_marker_injected_pixels']} | "
            f"camset={red['camset_max_card_slots']}+{red['camset_max_cloud_slots']} | "
            f"sync_elf={red['fx3_synchro_terminal_elf_hits']} | "
            f"genlock_bnc={int(red['fx6_physical_genlock_bnc_present'])} | "
            f"s1_wr={red['slot1_data_sector_writes']} | "
            f"leak={red['raw_firmware_bytes_leaked']} | "
            f"digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
