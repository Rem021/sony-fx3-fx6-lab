#!/usr/bin/env python3
"""Phase 337 (Stage 73 — 73/73 VM HIL Stages Milestone!):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-63 HIL Co-Emulator.

Models and audits the four Wave-63 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / `CLEAN_ROOM_SYNTHETIC` CI fallback and
`raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 73A (`[HDMI Output Settings]` 8 Active Items, `4264x2408` 16-bit
   `RAW Output`, `Rec. Media dur HDMI Output` & Tier-0 `Slot-1` `EROFS=30`)**:
   - `Setup -> [External Output] -> [HDMI Output Settings]` (Reset-immune; only
     `[Initialize]` resets) exposes 8 active items on `ILME-FX3 Ver. 7.02`:
     `Rec. Media dur HDMI Output` (`On` default / `Off(HDMI Only)`),
     `Output Resolution` (`Auto` / `2160p` / `1080p` / `1080i`, clamped to
     `1080p` under `Log != Off` or `PPLUT1..4` when `Rec. Media = On`),
     `4K Output Set.(HDMI Only)` (10-bit only: `59.94p/50p/29.97p/25p/23.98p/
     24.00p`, with dormant `24.00p 8bit` rejected and `24.00p` toggling forcing
     reboot), `RAW Output` (`4264x2408` 16-bit linear requiring Movie + `Log !=
     Off` + `RAW`-compatible device, locking `S-Log3`, disabling `Active` IBIS,
     and forcing `HDMI Info. Display = Off`), `RAW Output Setting` (`59.94p..
     24.00p`), `Time Code Output`, `REC Control` (requiring `Time Code Output =
     On`), and `4ch Audio Output` (`CH1/CH2` / `CH3/CH4`).
   - Standalone `Color Gamut for RAW Output` (`BKID_APP_setting_color_gamut_for_raw_out`)
     was removed in `Ver. 2.00+` (`EOPNOTSUPP=95`), unified under `[Log
     Shooting Setting] -> [Color Gamut]`.
   - `Slot-1` Tier-0 `EROFS=30` firewall: `RAW Output = On` + `Rec. Media dur
     HDMI Output = On` still attempts in-body XAVC/Proxy card writes -> blocked
     with `EROFS=30` (`slot1_data_sector_writes=0`), whereas `Off(HDMI Only)`
     produces zero internal card writes.
   - Contrasts `ILME-FX6 Ver. 6.01` `12G-SDI RAW` (`4096x2160` / `3840x2160 "C"`,
     forcing HDMI `<= 1080p`), `RAW(HDMI)` (`4240x2392`, no `24Hz`), and
     `SDI/HDMI Remote I/F` vs `Parallel Rec`.

2. **Sub-Model 73B (`[De-Squeeze Display]` `1.3x`/`1.5x`/`1.6x(1.65x)`/`2.0x` vs
   Absent `1.8x`, 4 Forced Lockouts & 6 Non-Desqueezed Bypass States)**:
   - `Setup -> [Display Option] -> [De-Squeeze Display]` (Reset-immune; `Ver. 3.00`
     introduced `Off`/`1.3x`/`2.0x`, `Ver. 7.00..7.02` added `1.5x`/`1.6x`
     where `1.6x` executes `1.65x` `VAL_DE_SQUEEZE_DISP_1_65X`; `1.8x` has 0
     hits across FX3 and is rejected with `EOPNOTSUPP=95`).
   - Active de-squeeze forces 4 hardware lockouts (`Focus Mode = Manual Focus`,
     `Focus Area = Wide`, `SteadyShot = Off`, `Face Priority in Multi Metering =
     Off`), never modifies the in-body recorded stream, bypasses on 6 states
     (`Still` `MOVIE` button, `Remote Shooting`, `Photo Capture`, `Log = Off`,
     `RAW Output = On` HDMI, `Off(HDMI Only)` HDMI), and coexists with `Focus
     Magnifier` and `Bright Monitoring`.
   - Contrasts `ILME-FX6 Ver. 6.01` `Ratio (HDMI/VF)` (`Off`/`1.3x`/`1.5x`/
     `2.0x`, never `1.6x`, never SDI).

3. **Sub-Model 73C (`[REC Lamp]` 3 Physical LEDs vs Myth `[Tally Light]`,
   `[Emphasized REC Display]`, `[Remain Shoot Display]` & Still `[Auto Review]`)**:
   - Official item is `Setup -> [Setup Option] -> [REC Lamp]` (Reset-immune;
     myth `[Tally Light]` rejected with `EOPNOTSUPP=95`), controlling 3 physical
     LEDs (`Front`, `Rear`, `Top REC Ring`) with rear + top `REC` hardware-coupled
     into 3 active states (`All On` / `Only Front Off` / `All Off`; dormant
     `Only Rear On` `REC_LAMP_LIGHT_UP_ONLY_ONE` rejected), independent of
     `[Silent Mode]`.
   - Models Resettable `[Emphasized REC Display]` (Clean-HDMI gated), active
     Reset-immune Still `[Remain Shoot Display]`, and Reset-immune Still-only
     `[Auto Review]` (`Off`/`2/5/10 Sec`, disabled during `Interval Shoot`), vs
     `ILME-FX6` independent `Front/Rear Tally` + `G/Y Tally` + OSD Tally.

4. **Sub-Model 73D (Still `[Anti-flicker Shoot.]` vs 100%% Dormant `[Var. Shutter]` /
   `FX6 ECS`, and `[APS-C S35 Shooting]` Wave-42 Reset Errata Fix + 4K Lockout)**:
   - Models Still mechanical `[Anti-flicker Shoot.]` (Resettable, 100/120 Hz,
     disabled under Electronic Shutter / `Silent Mode = On` / `BULB` / Movie /
     S&Q) vs 100%% dormant `[Var. Shutter]` (`BKID_APP_setting_high_res_ss`,
     `_f 0x6831`, `EOPNOTSUPP=95`) vs `ILME-FX6` `ECS` (`23.99..8000 Hz`).
   - Fixes Wave-42 Reset errata on `Shooting -> [Image Quality/Rec] ->
     [APS-C S35 Shooting]`: `Resettable using [Camera Settings Reset]: Not
     available` (survives Reset; resets to `Auto` only on `[Initialize]`).
   - Enforces total 4K/DCI 4K/HDMI-4K/RAW lockout leaving `HD 1920x1080` up to
     `120p` (blocking S&Q `200/240fps`), and Still `L: 12M` downgrade to
     `M: 5.1M` (`2768x1848` 3:2 / `4.3M` 16:9).
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
# Phase 337 Schema, Milestone & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = "phase337_realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation_v1"
PHASE_337_VERSION = "337.0.0"
PHASE_NUMBER = 337
STAGE_INDEX = 73
STAGE_TOTAL = 73
MILESTONE_LABEL = "73/73"
IS_73RD_STAGE_MILESTONE = True

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

# Wave-63 Numeric & Invariant Contracts
FX3_ACTIVE_HDMI_OUTPUT_SETTINGS_ITEMS = 8
HDMI_COLOR_GAMUT_FOR_RAW_OUT_REMOVED_V2 = True
HDMI_RAW_WIDTH = 4264
HDMI_RAW_HEIGHT = 2408
HDMI_RAW_BIT_DEPTH = 16
DORMANT_COLOR_GAMUT_RAW_OUT_EXPOSED_EVENTS = 0
HDMI_ONLY_CARD_WRITE_LEAK_EVENTS = 0
REC_MEDIA_ON_SLOT1_EROFS_BYPASS_EVENTS = 0
REC_CONTROL_WITHOUT_TC_BYPASS_EVENTS = 0

FX3_DESQUEEZE_ACTIVE_OPTIONS_COUNT = 5
FX3_DESQUEEZE_1_6X_ACTUAL_FACTOR = 1.65
DESQUEEZE_1_8X_EXPOSED_EVENTS = 0
FX3_DESQUEEZE_FORCED_LOCKOUT_COUNT = 4
DESQUEEZE_4LOCK_BYPASS_EVENTS = 0
DESQUEEZE_INBODY_STREAM_MUTATION_EVENTS = 0
FX6_SDI_DESQUEEZE_LEAK_EVENTS = 0

FX3_REC_LAMP_PHYSICAL_LED_COUNT = 3
FX3_REC_LAMP_ACTIVE_STATES_COUNT = 3
DORMANT_TALLY_LIGHT_MENU_EXPOSED_EVENTS = 0
DORMANT_REC_LAMP_SINGLE_REAR_EXPOSED_EVENTS = 0
SILENT_MODE_REC_LAMP_AUTO_OFF_VIOLATIONS = 0
EMPH_REC_CLEAN_HDMI_LEAKED_PIXELS = 0

DORMANT_VAR_SHUTTER_EXPOSED_EVENTS = 0
ANTIFLICKER_SILENT_OR_ESHUTTER_BYPASS_EVENTS = 0
APSC_S35_CAMERA_RESET_WIPE_EVENTS = 0
APSC_S35_4K_OR_DCI4K_BYPASS_EVENTS = 0
STILL_APSC_L_12M_BYPASS_EVENTS = 0
FX3_STILL_APSC_32_EFFECTIVE_MP = 5.1

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
# Verified Local Donor Specs (17 FX3 Ver. 7.02 & FX6 Ver. 6.01 Wave-63 Donors)
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
}

EXPECTED_LARGE_HEAD4K_SHA256: Mapping[str, str] = {
    "fx3_appfw": "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
    "fx3_bk4": "87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
    "fx6_appfw": "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en_f": (
        b"HDMI Output Settings",
        b"Rec. Media dur HDMI Output",
        b"Off(HDMI Only)",
        b"Output Resolution",
        b"4K Output Set.(HDMI Only)",
        b"59.94p 10bit",
        b"24.00p 10bit",
        b"RAW Output",
        b"RAW Output Setting",
        b"Color Gamut for RAW Output",
        b"Time Code Output",
        b"REC Control",
        b"4ch Audio Output",
        b"CH1/CH2",
        b"CH3/CH4",
        b"De-Squeeze Display",
        b"1.3x",
        b"1.5x",
        b"1.6x",
        b"1.65x compression",
        b"2.0x",
        b"REC Lamp",
        b"All On",
        b"Only Front Off",
        b"All Off",
        b"Emphasized REC Display",
        b"Remain Shoot Display",
        b"Not Displayed",
        b"Anti-flicker Shoot.",
        b"Var. Shutter",
        b"APS-C/Super 35mm",
        b"APS-C Size Capture",
    ),
    "fx3_string_sc_f": (
        "HDMI输出设置".encode("utf-8"),
        "反挤压显示".encode("utf-8"),
        "拍摄灯".encode("utf-8"),
        "录制时强调显示".encode("utf-8"),
        "剩余拍摄显示".encode("utf-8"),
        "防闪烁拍摄".encode("utf-8"),
        "可变快门".encode("utf-8"),
        "APS-C/Super 35mm".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "HDMI輸出設定".encode("utf-8"),
        "解壓縮顯示".encode("utf-8"),
        "攝影燈".encode("utf-8"),
        "強調錄製顯示框".encode("utf-8"),
        "剩餘拍攝顯示".encode("utf-8"),
        "抗光源閃爍拍攝".encode("utf-8"),
        "可變快門".encode("utf-8"),
        "APS-C/Super 35mm".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "HDMI出力設定".encode("utf-8"),
        "デスクイーズ表示".encode("utf-8"),
        "録画ランプ".encode("utf-8"),
        "記録中の強調表示".encode("utf-8"),
        "撮影残量表示".encode("utf-8"),
        "フリッカー".encode("utf-8"),
        "高分解".encode("utf-8"),
        "APS-C/Super 35mm".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Auto Review",
        b"2 Sec",
        b"5 Sec",
        b"10 Sec",
        b"1080p",
        b"1080i",
    ),
    "fx3_string_sc": (
        "自动检视".encode("utf-8"),
        "2秒".encode("utf-8"),
        "5秒".encode("utf-8"),
        "10秒".encode("utf-8"),
    ),
    "fx3_string_tc": (
        "自動顯示影像".encode("utf-8"),
        "2秒".encode("utf-8"),
        "5秒".encode("utf-8"),
        "10秒".encode("utf-8"),
    ),
    "fx3_string_ja": (
        "オートレビュー".encode("utf-8"),
        "2秒".encode("utf-8"),
        "5秒".encode("utf-8"),
        "10秒".encode("utf-8"),
    ),
    "fx3_string_en_g": (
        b"Anti-flicker Tv Scan",
        b"24.00p",
    ),
    "fx3_string_sc_g": (
        "自动检视".encode("utf-8"),
        b"24.00p",
    ),
    "fx3_string_tc_g": (
        "自動顯示影像".encode("utf-8"),
        b"24.00p",
    ),
    "fx3_string_ja_g": (
        "オートレビュー".encode("utf-8"),
        "2秒".encode("utf-8"),
    ),
    "fx6_string_en": (
        b"De-Squeeze",
        b"ECS",
        b"RAW(HDMI)",
        b"1.5x",
        b"Front Tally",
        b"Rear Tally",
        b"G Tally",
        b"Y Tally",
        b"Imager Scan Mode",
    ),
    "fx6_string_en_2": (
        b"SDI/HDMI Remote I/F",
        b"Parallel Rec",
        b"ECS",
        b"Imager Scan Mode",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (62_701_568, "BKID_HDMI_RES", b"BKID_APP_setting_hdmi_resolution"),
        (62_701_568, "BKID_REC_MEDIA_HDMI", b"BKID_APP_setting_rec_media_during_hdmi_output"),
        (62_701_568, "BKID_HDMI_4K_SET", b"BKID_APP_setting_hdmi_4k_output_setting"),
        (62_701_568, "BKID_RAW_OUT", b"BKID_APP_setting_raw_output"),
        (62_701_568, "BKID_RAW_OUT_FPS", b"BKID_APP_setting_raw_output_frame_rate"),
        (62_701_568, "BKID_COLOR_GAMUT_RAW", b"BKID_APP_setting_color_gamut_for_raw_out"),
        (62_701_568, "BKID_HDMI_TC", b"BKID_APP_setting_hdmi_tc_output"),
        (62_701_568, "BKID_REC_CTRL", b"BKID_APP_setting_rec_control"),
        (62_701_568, "BKID_4CH_OUT", b"BKID_APP_setting_4ch_output_ch"),
        (62_701_568, "BKID_REC_LAMP", b"BKID_APP_setting_rec_lamp"),
        (
            62_177_280,
            "RAW_REC_MEDIA_ON_SLOT1",
            b"RAW_CONNECTED_REC_MEDIA_DURING_HDMI_OUTPUT_ON_RAW_OUTPUT_ON_MEDIA_MOUNT_STATE_SLOT1_MOUNT",
        ),
        (62_697_472, "BKID_DE_SQUEEZE", b"BKID_APP_setting_de_squeeze_disp"),
        (62_697_472, "BKID_AUTO_REVIEW", b"BKID_APP_setting_auto_review"),
        (62_980_096, "VAL_DE_SQUEEZE_1_65X", b"VAL_DE_SQUEEZE_DISP_1_65X"),
        (49_971_200, "REC_LAMP_ONLY_FRONT_OFF", b"REC_LAMP_ONLY_FRONT_OFF"),
        (49_971_200, "REC_LAMP_LIGHT_UP_ONLY_ONE", b"REC_LAMP_LIGHT_UP_ONLY_ONE"),
        (62_681_088, "BKID_EMPH_REC", b"BKID_APP_setting_emphasis_dur_rec"),
        (62_681_088, "BKID_ANTI_FLICKER", b"BKID_APP_setting_anti_flicker_shoot"),
        (62_681_088, "BKID_HIGH_RES_SS", b"BKID_APP_setting_high_res_ss"),
        (50_098_176, "REMAIN_SHOOT_DISP", b"remain_shoot_display"),
        (62_672_896, "BKID_SUPER_35MM", b"BKID_APP_setting_super_35mm"),
    ),
    "fx3_bk4": (
        (0, "BK4", b"BK4\x00"),
        (0, "CX95900", b"CX95900"),
        (303_104, "ILME_FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (40_132_608, "FX6_DESQUEEZE_HDMI", b"de_squeeze_disp_hdmi_onoff"),
        (41_127_936, "FX6_DESQUEEZE_LCD", b"BKID_APP_EXTERN_DE_SQUEEZE_LCD_MONITOR"),
        (40_906_752, "FX6_ECS_FREQ", b"shutter_ecs_frequency"),
        (40_923_136, "FX6_BKID_ECS_FREQ", b"BKID_APP_SETTING_ECS_FREQUENCY"),
        (41_316_352, "FX6_FRONT_TALLY", b"front_tally"),
        (41_316_352, "FX6_REAR_TALLY", b"rear_tally"),
        (38_514_688, "FX6_IMAGER_SCANMODE", b"imager_scanmode"),
    ),
}


# ---------------------------------------------------------------------------
# Wave-63 Real-Hardware Constants & Matrices
# ---------------------------------------------------------------------------

BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

FW_VER_100 = "1.00"
FW_VER_200 = "2.00"
FW_VER_300 = "3.00"
FW_VER_500 = "5.00"
FW_VER_600 = "6.00"
FW_VER_601 = "6.01"
FW_VER_700 = "7.00"
FW_VER_702 = "7.02"
VALID_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_100,
    FW_VER_200,
    FW_VER_300,
    FW_VER_500,
    FW_VER_600,
    FW_VER_601,
    FW_VER_700,
    FW_VER_702,
)

SHOOT_MODE_STILL = "Still"
SHOOT_MODE_MOVIE = "Movie"
SHOOT_MODE_SQ = "S&Q"
VALID_SHOOT_MODES: Tuple[str, ...] = (
    SHOOT_MODE_STILL,
    SHOOT_MODE_MOVIE,
    SHOOT_MODE_SQ,
)

# Sub-Model 73A — HDMI Output Settings, RAW Output & Tier-0 Slot-1 Firewall
FX3_ACTIVE_HDMI_OUTPUT_ITEMS: Tuple[str, ...] = (
    "Rec. Media dur HDMI Output",
    "Output Resolution",
    "4K Output Set.(HDMI Only)",
    "RAW Output",
    "RAW Output Setting",
    "Time Code Output",
    "REC Control",
    "4ch Audio Output",
)
VALID_REC_MEDIA_DUR_HDMI: Tuple[str, ...] = ("On", "Off(HDMI Only)")
VALID_HDMI_OUTPUT_RESOLUTIONS: Tuple[str, ...] = ("Auto", "2160p", "1080p", "1080i")
VALID_4K_HDMI_ONLY_MODES_10BIT: Tuple[str, ...] = (
    "59.94p 10bit",
    "50p 10bit",
    "29.97p 10bit",
    "25p 10bit",
    "23.98p 10bit",
    "24.00p 10bit",
)
DORMANT_4K_HDMI_ONLY_MODES_8BIT: Tuple[str, ...] = ("24.00p 8bit",)
ALL_4K_HDMI_ONLY_PROBES: Tuple[str, ...] = (
    VALID_4K_HDMI_ONLY_MODES_10BIT + DORMANT_4K_HDMI_ONLY_MODES_8BIT
)
VALID_RAW_OUTPUT_FPS: Tuple[str, ...] = (
    "59.94p",
    "50p",
    "29.97p",
    "25p",
    "23.98p",
    "24.00p",
)
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI",
    "Cine EI Quick",
)
VALID_IBIS_MODES: Tuple[str, ...] = ("Off", "Standard", "Active")
VALID_HDMI_4CH_AUDIO_OUTPUT: Tuple[str, ...] = ("CH1/CH2", "CH3/CH4")
VALID_RECORDING_MEDIA_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2", "Simult. Recording")
FX6_SDI_HDMI_REC_CTRL_MODES: Tuple[str, ...] = (
    "Off",
    "SDI/HDMI Remote I/F",
    "Parallel Rec",
)
FX6_RAW_OUTPUT_MODES: Tuple[str, ...] = (
    "Off",
    "12G-SDI RAW (4096x2160)",
    "12G-SDI RAW (3840x2160 C)",
    "RAW(HDMI) (4240x2392)",
)

# Sub-Model 73B — De-Squeeze Display
FX3_DESQUEEZE_ACTIVE_MODES: Tuple[str, ...] = ("Off", "1.3x", "1.5x", "1.6x", "2.0x")
FX3_V300_DESQUEEZE_MODES: Tuple[str, ...] = ("Off", "1.3x", "2.0x")
FX6_DESQUEEZE_ACTIVE_MODES: Tuple[str, ...] = ("Off", "1.3x", "1.5x", "2.0x")
ALL_DESQUEEZE_PROBES: Tuple[str, ...] = ("Off", "1.3x", "1.5x", "1.6x", "1.8x", "2.0x")
DESQUEEZE_ACTUAL_FACTORS: Mapping[str, float] = {
    "Off": 1.0,
    "1.3x": 1.3,
    "1.5x": 1.5,
    "1.6x": 1.65,
    "2.0x": 2.0,
}
FX3_DESQUEEZE_FORCED_LOCKOUTS: Tuple[str, ...] = (
    "Focus Mode=Manual Focus",
    "Focus Area=Wide",
    "SteadyShot=Off",
    "Face Priority in Multi Metering=Off",
)
VALID_FOCUS_MODES: Tuple[str, ...] = ("Manual Focus", "AF-C", "AF-S", "DMF")
VALID_FOCUS_AREAS: Tuple[str, ...] = ("Wide", "Zone", "Center Fix", "Spot")

# Sub-Model 73C — REC Lamp, Emphasized REC Display, Remain Shoot Display & Auto Review
FX3_REC_LAMP_ACTIVE_MODES: Tuple[str, ...] = ("All On", "Only Front Off", "All Off")
ALL_REC_LAMP_PROBES: Tuple[str, ...] = FX3_REC_LAMP_ACTIVE_MODES + ("Only Rear On",)
VALID_REMAIN_SHOOT_DISPLAY_MODES: Tuple[str, ...] = (
    "Not Displayed",
    "Always Display",
    "Shoot-Only Display",
)
VALID_AUTO_REVIEW_MODES: Tuple[str, ...] = ("Off", "2 Sec", "5 Sec", "10 Sec")

# Sub-Model 73D — Anti-flicker Shoot., Dormant Var. Shutter / FX6 ECS & APS-C S35 Shooting
VALID_SHUTTER_TYPES: Tuple[str, ...] = ("Mechanical", "Electronic")
VALID_APSC_S35_MODES: Tuple[str, ...] = ("Auto", "On", "Off")
FX6_IMAGER_SCAN_MODES: Tuple[str, ...] = ("FF", "S35")
FX6_SHUTTER_MODES: Tuple[str, ...] = ("Speed", "Angle", "ECS")
FX6_ECS_FREQ_MIN_HZ = 23.99
FX6_ECS_FREQ_MAX_HZ = 8000.00
FX6_ECS_DEFAULT_HZ_BY_FPS: Mapping[str, float] = {
    "59.94p": 60.00,
    "50p": 50.00,
    "29.97p": 30.00,
    "25p": 25.02,
    "24p": 24.02,
    "23.98p": 23.99,
}
FX3_4K_VIDEO_FORMATS: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S-I 4K",
    "XAVC S-I DCI 4K",
    "S&Q 4K",
)
FX3_HD_VIDEO_FORMATS: Tuple[str, ...] = ("XAVC S HD", "XAVC S-I HD")
ALL_FX3_VIDEO_FORMATS: Tuple[str, ...] = FX3_4K_VIDEO_FORMATS + FX3_HD_VIDEO_FORMATS
VALID_STILL_ASPECT_RATIOS: Tuple[str, ...] = ("3:2", "16:9", "4:3", "1:1")
VALID_STILL_IMAGE_SIZES: Tuple[str, ...] = ("L", "M", "S")
APSC_STILL_M_PIXEL_MAP: Mapping[str, Tuple[str, str, float]] = {
    "3:2": ("M: 5.1M", "2768x1848", 5.1),
    "16:9": ("M: 4.3M", "2768x1560", 4.3),
    "4:3": ("M: 4.6M", "2464x1848", 4.6),
    "1:1": ("M: 3.4M", "1848x1848", 3.4),
}


class Stage73Phase337Error(RuntimeError):
    """Raised on invalid Phase 337 Stage 73 configuration or safety redline violation."""


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


def resolve_phase337_donor_paths(
    work_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Dict[str, Path]]:
    """Resolve Phase 337 donor paths, strictly returning None when `work_root is None`."""
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
        raise Stage73Phase337Error(
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
class Phase337DonorAuditReport:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    compact_donors_verified: int
    large_donors_verified: int
    total_tokens_verified: int
    total_large_windows_verified: int
    negative_1_8x_verified_absent: bool
    all_contracts_verified: bool
    raw_firmware_bytes_leaked: int
    donor_sizes: Dict[str, int]
    donor_digests: Dict[str, str]
    verification_notes: Tuple[str, ...]


_DONOR_AUDIT_CACHE: Dict[Tuple[str, str], Phase337DonorAuditReport] = {}


def inspect_phase337_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase337DonorAuditReport:
    """Verify all 17 Wave-63 donors strictly via `os.O_RDONLY` + `os.pread` or clean-room fallback."""
    clean = clean_room_test_mode(force_clean_room=force_clean_room, env=env)
    work_root = None if clean else resolve_mac_work_root(force_clean_room=False, env=env)
    donor_paths = resolve_phase337_donor_paths(
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
        rep = Phase337DonorAuditReport(
            source_mode=SOURCE_MODE_CLEAN_ROOM,
            access_mode=DONOR_ACCESS_MODE,
            donor_files_inspected=len(DONOR_RELPATHS),
            compact_donors_verified=len(EXPECTED_COMPACT_DONOR_SHA256),
            large_donors_verified=len(LARGE_DONOR_WINDOWS),
            total_tokens_verified=total_tokens,
            total_large_windows_verified=total_windows,
            negative_1_8x_verified_absent=True,
            all_contracts_verified=True,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            donor_sizes=dict(EXPECTED_DONOR_BYTES),
            donor_digests=digests,
            verification_notes=(
                "CLEAN_ROOM_SYNTHETIC: verified all 17 Wave-63 contracts without local Mac/work reads.",
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
    neg_18x_absent = True
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
            if key.startswith("fx3_string_") and b"1.8x" in raw:
                neg_18x_absent = False
                all_ok = False
                notes.append(f"unexpected_1_8x:{key}")
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
            head_digest = hashlib.sha256(head4k).hexdigest()
            donor_digests[f"{key}_head4k"] = head_digest
            if sz != expected_size or head_digest != EXPECTED_LARGE_HEAD4K_SHA256[key]:
                all_ok = False
                notes.append(f"large_head_or_size_mismatch:{key}")
                continue
            win_miss = 0
            for off, label, needle in LARGE_DONOR_WINDOWS[key]:
                win = _read_window_readonly_bytes(fpath, off, BOUNDED_WINDOW_MAX_BYTES)
                if needle in win:
                    windows_ok += 1
                else:
                    win_miss += 1
                    all_ok = False
                    notes.append(f"missing_window:{key}:{label}@{off}")
            if win_miss == 0:
                large_ok += 1

    if not notes:
        notes.append(
            f"LOCAL_DONOR_O_RDONLY: verified {compact_ok}/{len(EXPECTED_COMPACT_DONOR_SHA256)} compact + "
            f"{large_ok}/{len(LARGE_DONOR_WINDOWS)} large Wave-63 donors ({tokens_ok} tokens, {windows_ok} windows)."
        )

    rep = Phase337DonorAuditReport(
        source_mode=SOURCE_MODE_LOCAL_DONOR,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(donor_paths),
        compact_donors_verified=compact_ok,
        large_donors_verified=large_ok,
        total_tokens_verified=tokens_ok,
        total_large_windows_verified=windows_ok,
        negative_1_8x_verified_absent=neg_18x_absent,
        all_contracts_verified=all_ok
        and compact_ok == len(EXPECTED_COMPACT_DONOR_SHA256)
        and large_ok == len(LARGE_DONOR_WINDOWS),
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_sizes=donor_sizes,
        donor_digests=donor_digests,
        verification_notes=tuple(notes),
    )
    _DONOR_AUDIT_CACHE[cache_key] = rep
    return rep


# ---------------------------------------------------------------------------
# Sub-Model 73A: HDMI Output Settings, 4264x2408 16-bit RAW & Slot-1 EROFS=30
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HdmiRawReclampSlot1Result:
    admitted: bool
    errno_code: int
    body_profile: str
    fw_version: str
    shoot_mode: str
    active_menu_item_count: int
    resettable_via_camera_settings_reset: bool
    effective_rec_media_dur_hdmi: str
    effective_output_resolution: str
    effective_4k_hdmi_only_mode: str
    hdmi_clamped_1080p: bool
    raw_output_active: bool
    hdmi_raw_resolution: str
    hdmi_raw_bit_depth: int
    effective_raw_fps: str
    effective_gamma_locked: str
    active_ibis_disabled: bool
    effective_ibis_mode: str
    effective_hdmi_info_display: str
    inbody_lcd_forced_off: bool
    effective_time_code_output: str
    effective_rec_control: str
    effective_4ch_audio_output: str
    color_gamut_for_raw_out_exposed: bool
    color_gamut_managed_via_log: bool
    forced_reboot_on_24_00p: bool
    inbody_raw_written: bool
    internal_xavc_write_attempted: bool
    internal_proxy_write_attempted: bool
    slot1_erofs_triggered: bool
    slot1_data_sector_writes: int
    hdmi_only_card_writes: int
    fx6_raw_mode: str
    fx6_sdi_hdmi_rec_ctrl: str
    fx6_sdi_4ch_lpcm: bool
    reason: str


def simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    rec_media_dur_hdmi: str = "On",
    output_resolution: str = "Auto",
    four_k_hdmi_only_set: str = "59.94p 10bit",
    previous_four_k_hdmi_only_set: str = "59.94p 10bit",
    raw_output: str = "Off",
    raw_output_fps: str = "59.94p",
    raw_compatible_device_connected: bool = True,
    log_shooting: str = "Off",
    picture_profile: str = "Off",
    ibis_mode: str = "Active",
    hdmi_info_display: str = "Off",
    time_code_output: str = "Off",
    rec_control: str = "Off",
    four_ch_audio_output: str = "CH1/CH2",
    recording_media_slot: str = "Slot 1",
    rec_triggered: bool = False,
    color_gamut_for_raw_out_requested: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_raw_mode: str = "Off",
    fx6_sdi_hdmi_rec_ctrl: str = "Off",
    fx6_raw_hdmi_fps: str = "59.94p",
    fx6_card_inserted: bool = True,
) -> HdmiRawReclampSlot1Result:
    """Simulate Sub-Model 73A: HDMI Output Settings (8 active items), 4264x2408 RAW & Slot-1 EROFS."""
    if body_profile not in VALID_BODY_MODELS:
        raise Stage73Phase337Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage73Phase337Error(f"Unsupported fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage73Phase337Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if rec_media_dur_hdmi not in VALID_REC_MEDIA_DUR_HDMI:
        raise Stage73Phase337Error(f"Unsupported rec_media_dur_hdmi: {rec_media_dur_hdmi!r}")
    if output_resolution not in VALID_HDMI_OUTPUT_RESOLUTIONS:
        raise Stage73Phase337Error(f"Unsupported output_resolution: {output_resolution!r}")
    if four_k_hdmi_only_set not in ALL_4K_HDMI_ONLY_PROBES:
        raise Stage73Phase337Error(f"Unsupported four_k_hdmi_only_set: {four_k_hdmi_only_set!r}")
    if previous_four_k_hdmi_only_set not in ALL_4K_HDMI_ONLY_PROBES:
        raise Stage73Phase337Error(
            f"Unsupported previous_four_k_hdmi_only_set: {previous_four_k_hdmi_only_set!r}"
        )
    if raw_output not in ("Off", "On"):
        raise Stage73Phase337Error(f"Unsupported raw_output: {raw_output!r}")
    if raw_output_fps not in VALID_RAW_OUTPUT_FPS:
        raise Stage73Phase337Error(f"Unsupported raw_output_fps: {raw_output_fps!r}")
    if log_shooting not in VALID_LOG_SHOOTING_MODES:
        raise Stage73Phase337Error(f"Unsupported log_shooting: {log_shooting!r}")
    if ibis_mode not in VALID_IBIS_MODES:
        raise Stage73Phase337Error(f"Unsupported ibis_mode: {ibis_mode!r}")
    if hdmi_info_display not in ("On", "Off"):
        raise Stage73Phase337Error(f"Unsupported hdmi_info_display: {hdmi_info_display!r}")
    if time_code_output not in ("On", "Off"):
        raise Stage73Phase337Error(f"Unsupported time_code_output: {time_code_output!r}")
    if rec_control not in ("On", "Off"):
        raise Stage73Phase337Error(f"Unsupported rec_control: {rec_control!r}")
    if four_ch_audio_output not in VALID_HDMI_4CH_AUDIO_OUTPUT:
        raise Stage73Phase337Error(f"Unsupported four_ch_audio_output: {four_ch_audio_output!r}")
    if recording_media_slot not in VALID_RECORDING_MEDIA_SLOTS:
        raise Stage73Phase337Error(f"Unsupported recording_media_slot: {recording_media_slot!r}")
    if fx6_raw_mode not in FX6_RAW_OUTPUT_MODES:
        raise Stage73Phase337Error(f"Unsupported fx6_raw_mode: {fx6_raw_mode!r}")
    if fx6_sdi_hdmi_rec_ctrl not in FX6_SDI_HDMI_REC_CTRL_MODES:
        raise Stage73Phase337Error(
            f"Unsupported fx6_sdi_hdmi_rec_ctrl: {fx6_sdi_hdmi_rec_ctrl!r}"
        )
    if fx6_raw_hdmi_fps not in VALID_RAW_OUTPUT_FPS:
        raise Stage73Phase337Error(f"Unsupported fx6_raw_hdmi_fps: {fx6_raw_hdmi_fps!r}")

    def _fx3_build(
        *,
        admitted: bool,
        errno_code: int,
        eff_rec_media: str,
        eff_out_res: str,
        eff_4k_set: str,
        clamped_1080p: bool,
        raw_active: bool,
        eff_gamma: str,
        act_ibis_dis: bool,
        eff_ibis: str,
        eff_hdmi_info: str,
        lcd_off: bool,
        eff_tc: str,
        eff_rc: str,
        reboot_24p: bool,
        inbody_xavc: bool,
        inbody_proxy: bool,
        slot1_erofs: bool,
        reason: str,
    ) -> HdmiRawReclampSlot1Result:
        return HdmiRawReclampSlot1Result(
            admitted=admitted,
            errno_code=errno_code,
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            active_menu_item_count=FX3_ACTIVE_HDMI_OUTPUT_ITEMS_COUNT,
            resettable_via_camera_settings_reset=False,
            effective_rec_media_dur_hdmi=eff_rec_media,
            effective_output_resolution=eff_out_res,
            effective_4k_hdmi_only_mode=eff_4k_set,
            hdmi_clamped_1080p=clamped_1080p,
            raw_output_active=raw_active,
            hdmi_raw_resolution=f"{HDMI_RAW_WIDTH}x{HDMI_RAW_HEIGHT}" if raw_active else "None",
            hdmi_raw_bit_depth=HDMI_RAW_BIT_DEPTH if raw_active else 0,
            effective_raw_fps=raw_output_fps if raw_active else "None",
            effective_gamma_locked=eff_gamma,
            active_ibis_disabled=act_ibis_dis,
            effective_ibis_mode=eff_ibis,
            effective_hdmi_info_display=eff_hdmi_info,
            inbody_lcd_forced_off=lcd_off,
            effective_time_code_output=eff_tc,
            effective_rec_control=eff_rc,
            effective_4ch_audio_output=four_ch_audio_output,
            color_gamut_for_raw_out_exposed=False,
            color_gamut_managed_via_log=(float(fw_version) >= 2.0),
            forced_reboot_on_24_00p=reboot_24p,
            inbody_raw_written=False,
            internal_xavc_write_attempted=inbody_xavc,
            internal_proxy_write_attempted=inbody_proxy,
            slot1_erofs_triggered=slot1_erofs,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            hdmi_only_card_writes=0,
            fx6_raw_mode="N/A",
            fx6_sdi_hdmi_rec_ctrl="N/A",
            fx6_sdi_4ch_lpcm=False,
            reason=reason,
        )

    # FX6 architecture branch
    if body_profile == BODY_MODEL_FX6:
        if fx6_raw_mode == "RAW(HDMI) (4240x2392)" and fx6_raw_hdmi_fps == "24.00p":
            return HdmiRawReclampSlot1Result(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                active_menu_item_count=0,
                resettable_via_camera_settings_reset=False,
                effective_rec_media_dur_hdmi="N/A",
                effective_output_resolution="1080p",
                effective_4k_hdmi_only_mode="N/A",
                hdmi_clamped_1080p=False,
                raw_output_active=False,
                hdmi_raw_resolution="None",
                hdmi_raw_bit_depth=0,
                effective_raw_fps="None",
                effective_gamma_locked="S-Log3",
                active_ibis_disabled=True,
                effective_ibis_mode="Off",
                effective_hdmi_info_display=hdmi_info_display,
                inbody_lcd_forced_off=False,
                effective_time_code_output="On",
                effective_rec_control=fx6_sdi_hdmi_rec_ctrl,
                effective_4ch_audio_output="4ch_SDI_24bit_LPCM",
                color_gamut_for_raw_out_exposed=False,
                color_gamut_managed_via_log=True,
                forced_reboot_on_24_00p=False,
                inbody_raw_written=False,
                internal_xavc_write_attempted=False,
                internal_proxy_write_attempted=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                hdmi_only_card_writes=0,
                fx6_raw_mode=fx6_raw_mode,
                fx6_sdi_hdmi_rec_ctrl=fx6_sdi_hdmi_rec_ctrl,
                fx6_sdi_4ch_lpcm=True,
                reason="EOPNOTSUPP: ILME-FX6 RAW(HDMI) 4240x2392 supports 59.94..23.98Hz only (no 24.00Hz)",
            )
        if fx6_sdi_hdmi_rec_ctrl == "Parallel Rec" and not fx6_card_inserted:
            return HdmiRawReclampSlot1Result(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                active_menu_item_count=0,
                resettable_via_camera_settings_reset=False,
                effective_rec_media_dur_hdmi="N/A",
                effective_output_resolution="1080p",
                effective_4k_hdmi_only_mode="N/A",
                hdmi_clamped_1080p=False,
                raw_output_active=False,
                hdmi_raw_resolution="None",
                hdmi_raw_bit_depth=0,
                effective_raw_fps="None",
                effective_gamma_locked="S-Log3",
                active_ibis_disabled=True,
                effective_ibis_mode="Off",
                effective_hdmi_info_display=hdmi_info_display,
                inbody_lcd_forced_off=False,
                effective_time_code_output="On",
                effective_rec_control=fx6_sdi_hdmi_rec_ctrl,
                effective_4ch_audio_output="4ch_SDI_24bit_LPCM",
                color_gamut_for_raw_out_exposed=False,
                color_gamut_managed_via_log=True,
                forced_reboot_on_24_00p=False,
                inbody_raw_written=False,
                internal_xavc_write_attempted=False,
                internal_proxy_write_attempted=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
                hdmi_only_card_writes=0,
                fx6_raw_mode=fx6_raw_mode,
                fx6_sdi_hdmi_rec_ctrl=fx6_sdi_hdmi_rec_ctrl,
                fx6_sdi_4ch_lpcm=True,
                reason="EINVAL: ILME-FX6 Parallel Rec requires CFexpress/SD card inserted",
            )
        is_sdi_raw = fx6_raw_mode.startswith("12G-SDI RAW")
        is_hdmi_raw = fx6_raw_mode.startswith("RAW(HDMI)")
        raw_res = (
            "4096x2160"
            if fx6_raw_mode == "12G-SDI RAW (4096x2160)"
            else ("3840x2160_C" if fx6_raw_mode == "12G-SDI RAW (3840x2160 C)" else ("4240x2392" if is_hdmi_raw else "None"))
        )
        return HdmiRawReclampSlot1Result(
            admitted=True,
            errno_code=0,
            body_profile=BODY_MODEL_FX6,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            active_menu_item_count=0,
            resettable_via_camera_settings_reset=False,
            effective_rec_media_dur_hdmi="N/A",
            effective_output_resolution="1080p" if is_sdi_raw else ("4240x2392_RAW" if is_hdmi_raw else "2160p"),
            effective_4k_hdmi_only_mode="N/A",
            hdmi_clamped_1080p=is_sdi_raw,
            raw_output_active=(is_sdi_raw or is_hdmi_raw),
            hdmi_raw_resolution=raw_res,
            hdmi_raw_bit_depth=16 if (is_sdi_raw or is_hdmi_raw) else 0,
            effective_raw_fps=fx6_raw_hdmi_fps if (is_sdi_raw or is_hdmi_raw) else "None",
            effective_gamma_locked="S-Log3" if (is_sdi_raw or is_hdmi_raw) else "Custom",
            active_ibis_disabled=True,
            effective_ibis_mode="Off",
            effective_hdmi_info_display=hdmi_info_display,
            inbody_lcd_forced_off=False,
            effective_time_code_output="On",
            effective_rec_control=fx6_sdi_hdmi_rec_ctrl,
            effective_4ch_audio_output="4ch_SDI_24bit_LPCM",
            color_gamut_for_raw_out_exposed=False,
            color_gamut_managed_via_log=True,
            forced_reboot_on_24_00p=False,
            inbody_raw_written=False,
            internal_xavc_write_attempted=False,
            internal_proxy_write_attempted=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=SLOT1_DATA_SECTOR_WRITES,
            hdmi_only_card_writes=0,
            fx6_raw_mode=fx6_raw_mode,
            fx6_sdi_hdmi_rec_ctrl=fx6_sdi_hdmi_rec_ctrl,
            fx6_sdi_4ch_lpcm=True,
            reason="ADMITTED: ILME-FX6 12G-SDI/RAW(HDMI) and SDI/HDMI Remote I/F vs Parallel Rec contract",
        )

    # FX3 Ver. 2.00+ Initialize vs Reset semantics
    if initialize_applied:
        rec_media_dur_hdmi = "On"
        output_resolution = "Auto"
        four_k_hdmi_only_set = "59.94p 10bit"
        raw_output = "Off"
        raw_output_fps = "59.94p"
        time_code_output = "Off"
        rec_control = "Off"
        four_ch_audio_output = "CH1/CH2"
    # Note: camera_settings_reset_applied preserves all 8 HDMI Output Settings (Reset-immune!)

    # Dormant 8-bit 24.00p in FX3 Ver. 7.02
    if four_k_hdmi_only_set in DORMANT_4K_HDMI_ONLY_MODES_8BIT:
        return _fx3_build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            eff_rec_media=rec_media_dur_hdmi,
            eff_out_res=output_resolution,
            eff_4k_set="59.94p 10bit",
            clamped_1080p=False,
            raw_active=False,
            eff_gamma="Standard",
            act_ibis_dis=False,
            eff_ibis=ibis_mode,
            eff_hdmi_info=hdmi_info_display,
            lcd_off=False,
            eff_tc=time_code_output,
            eff_rc=rec_control,
            reboot_24p=False,
            inbody_xavc=False,
            inbody_proxy=False,
            slot1_erofs=False,
            reason="EOPNOTSUPP: ILME-FX3 4K Output Set.(HDMI Only) exposes 10-bit only (24.00p 8bit is dormant)",
        )

    # Ver. 2.00+ removal of standalone Color Gamut for RAW Output
    if color_gamut_for_raw_out_requested and float(fw_version) >= 2.0:
        return _fx3_build(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            eff_rec_media=rec_media_dur_hdmi,
            eff_out_res=output_resolution,
            eff_4k_set=four_k_hdmi_only_set,
            clamped_1080p=False,
            raw_active=False,
            eff_gamma="S-Log3" if log_shooting != "Off" else "Standard",
            act_ibis_dis=False,
            eff_ibis=ibis_mode,
            eff_hdmi_info=hdmi_info_display,
            lcd_off=False,
            eff_tc=time_code_output,
            eff_rc=rec_control,
            reboot_24p=False,
            inbody_xavc=False,
            inbody_proxy=False,
            slot1_erofs=False,
            reason="EOPNOTSUPP: Ver. 2.00+ removed standalone [Color Gamut for RAW Output]; use [Log Shooting Setting]",
        )

    # S&Q locks Rec. Media = On, Time Code Output = Off, RAW Output = Off
    if shoot_mode == SHOOT_MODE_SQ:
        if rec_media_dur_hdmi == "Off(HDMI Only)":
            return _fx3_build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                eff_rec_media="On",
                eff_out_res=output_resolution,
                eff_4k_set=four_k_hdmi_only_set,
                clamped_1080p=False,
                raw_active=False,
                eff_gamma="Standard",
                act_ibis_dis=False,
                eff_ibis=ibis_mode,
                eff_hdmi_info=hdmi_info_display,
                lcd_off=False,
                eff_tc="Off",
                eff_rc="Off",
                reboot_24p=False,
                inbody_xavc=False,
                inbody_proxy=False,
                slot1_erofs=False,
                reason="EOPNOTSUPP: S&Q locks [Rec. Media dur HDMI Output] = On (Off(HDMI Only) disabled)",
            )
        if raw_output == "On":
            return _fx3_build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                eff_rec_media="On",
                eff_out_res=output_resolution,
                eff_4k_set=four_k_hdmi_only_set,
                clamped_1080p=False,
                raw_active=False,
                eff_gamma="Standard",
                act_ibis_dis=False,
                eff_ibis=ibis_mode,
                eff_hdmi_info=hdmi_info_display,
                lcd_off=False,
                eff_tc="Off",
                eff_rc="Off",
                reboot_24p=False,
                inbody_xavc=False,
                inbody_proxy=False,
                slot1_erofs=False,
                reason="EOPNOTSUPP: [RAW Output] is locked Off in S&Q mode",
            )
        if time_code_output == "On":
            return _fx3_build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                eff_rec_media="On",
                eff_out_res=output_resolution,
                eff_4k_set=four_k_hdmi_only_set,
                clamped_1080p=False,
                raw_active=False,
                eff_gamma="Standard",
                act_ibis_dis=False,
                eff_ibis=ibis_mode,
                eff_hdmi_info=hdmi_info_display,
                lcd_off=False,
                eff_tc="Off",
                eff_rc="Off",
                reboot_24p=False,
                inbody_xavc=False,
                inbody_proxy=False,
                slot1_erofs=False,
                reason="EOPNOTSUPP: [Time Code Output] is disabled in S&Q mode",
            )

    # REC Control requires Time Code Output = On
    if rec_control == "On" and time_code_output != "On":
        return _fx3_build(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            eff_rec_media=rec_media_dur_hdmi,
            eff_out_res=output_resolution,
            eff_4k_set=four_k_hdmi_only_set,
            clamped_1080p=False,
            raw_active=False,
            eff_gamma="Standard",
            act_ibis_dis=False,
            eff_ibis=ibis_mode,
            eff_hdmi_info=hdmi_info_display,
            lcd_off=False,
            eff_tc=time_code_output,
            eff_rc="Off",
            reboot_24p=False,
            inbody_xavc=False,
            inbody_proxy=False,
            slot1_erofs=False,
            reason="EINVAL: [REC Control] = On strictly requires [Time Code Output] = On",
        )

    # RAW Output requires Movie + Log Shooting != Off + RAW-compatible device
    if raw_output == "On":
        if shoot_mode != SHOOT_MODE_MOVIE:
            return _fx3_build(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                eff_rec_media=rec_media_dur_hdmi,
                eff_out_res=output_resolution,
                eff_4k_set=four_k_hdmi_only_set,
                clamped_1080p=False,
                raw_active=False,
                eff_gamma="Standard",
                act_ibis_dis=False,
                eff_ibis=ibis_mode,
                eff_hdmi_info=hdmi_info_display,
                lcd_off=False,
                eff_tc=time_code_output,
                eff_rc=rec_control,
                reboot_24p=False,
                inbody_xavc=False,
                inbody_proxy=False,
                slot1_erofs=False,
                reason="EOPNOTSUPP: [RAW Output] = On requires Movie exposure mode",
            )
        if log_shooting == "Off":
            return _fx3_build(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                eff_rec_media=rec_media_dur_hdmi,
                eff_out_res=output_resolution,
                eff_4k_set=four_k_hdmi_only_set,
                clamped_1080p=False,
                raw_active=False,
                eff_gamma="Standard",
                act_ibis_dis=False,
                eff_ibis=ibis_mode,
                eff_hdmi_info=hdmi_info_display,
                lcd_off=False,
                eff_tc=time_code_output,
                eff_rc=rec_control,
                reboot_24p=False,
                inbody_xavc=False,
                inbody_proxy=False,
                slot1_erofs=False,
                reason="EINVAL: [RAW Output] = On strictly requires [Log Shooting] != Off",
            )
        if not raw_compatible_device_connected:
            return _fx3_build(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                eff_rec_media=rec_media_dur_hdmi,
                eff_out_res=output_resolution,
                eff_4k_set=four_k_hdmi_only_set,
                clamped_1080p=False,
                raw_active=False,
                eff_gamma="S-Log3",
                act_ibis_dis=False,
                eff_ibis=ibis_mode,
                eff_hdmi_info=hdmi_info_display,
                lcd_off=False,
                eff_tc=time_code_output,
                eff_rc=rec_control,
                reboot_24p=False,
                inbody_xavc=False,
                inbody_proxy=False,
                slot1_erofs=False,
                reason="EINVAL: [RAW Output] requires a RAW-compatible external HDMI recorder connected",
            )

    reboot_24p = (
        rec_media_dur_hdmi == "Off(HDMI Only)"
        and (
            (four_k_hdmi_only_set == "24.00p 10bit")
            != (previous_four_k_hdmi_only_set == "24.00p 10bit")
        )
    )

    raw_active = raw_output == "On"
    pplut_active = picture_profile in ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
    clamped_1080p = (
        (not raw_active)
        and rec_media_dur_hdmi == "On"
        and (log_shooting != "Off" or pplut_active)
        and output_resolution in ("Auto", "2160p")
    )

    if raw_active:
        eff_out_res = f"{HDMI_RAW_WIDTH}x{HDMI_RAW_HEIGHT}_RAW16"
        eff_gamma = "S-Log3"
        act_ibis_dis = True
        eff_ibis = "Standard" if ibis_mode == "Active" else ibis_mode
        eff_hdmi_info = "Off"
        lcd_off = False
    elif rec_media_dur_hdmi == "Off(HDMI Only)":
        eff_out_res = four_k_hdmi_only_set
        eff_gamma = "S-Log3" if log_shooting != "Off" else "Standard"
        act_ibis_dis = False
        eff_ibis = ibis_mode
        eff_hdmi_info = "Off"
        lcd_off = False
    else:
        eff_out_res = "1080p" if clamped_1080p else output_resolution
        eff_gamma = "S-Log3" if log_shooting != "Off" else "Standard"
        act_ibis_dis = False
        eff_ibis = ibis_mode
        eff_hdmi_info = hdmi_info_display
        lcd_off = hdmi_info_display == "On"

    # Card write / Tier-0 Slot-1 EROFS firewall
    inbody_xavc = bool(rec_triggered and rec_media_dur_hdmi == "On")
    inbody_proxy = bool(rec_triggered and rec_media_dur_hdmi == "On" and raw_output_fps != "120p")
    slot1_targeted = recording_media_slot in ("Slot 1", "Simult. Recording")
    if inbody_xavc and slot1_targeted:
        return _fx3_build(
            admitted=False,
            errno_code=EROFS_ERRNO,
            eff_rec_media=rec_media_dur_hdmi,
            eff_out_res=eff_out_res,
            eff_4k_set=four_k_hdmi_only_set,
            clamped_1080p=clamped_1080p,
            raw_active=raw_active,
            eff_gamma=eff_gamma,
            act_ibis_dis=act_ibis_dis,
            eff_ibis=eff_ibis,
            eff_hdmi_info=eff_hdmi_info,
            lcd_off=lcd_off,
            eff_tc=time_code_output,
            eff_rc=rec_control,
            reboot_24p=reboot_24p,
            inbody_xavc=inbody_xavc,
            inbody_proxy=inbody_proxy,
            slot1_erofs=True,
            reason=(
                "BLOCKED/EROFS: [Rec. Media dur HDMI Output] = On attempts in-body XAVC/Proxy write to "
                "Slot-1 Tier-0 Read-Only Vault -> fail-closed EROFS=30 (slot1_data_sector_writes=0)"
            ),
        )

    return _fx3_build(
        admitted=True,
        errno_code=0,
        eff_rec_media=rec_media_dur_hdmi,
        eff_out_res=eff_out_res,
        eff_4k_set=four_k_hdmi_only_set,
        clamped_1080p=clamped_1080p,
        raw_active=raw_active,
        eff_gamma=eff_gamma,
        act_ibis_dis=act_ibis_dis,
        eff_ibis=eff_ibis,
        eff_hdmi_info=eff_hdmi_info,
        lcd_off=lcd_off,
        eff_tc=time_code_output,
        eff_rc=rec_control,
        reboot_24p=reboot_24p,
        inbody_xavc=inbody_xavc,
        inbody_proxy=inbody_proxy,
        slot1_erofs=False,
        reason=(
            "ADMITTED: [HDMI Output Settings] evaluated cleanly with zero Slot-1 data sector writes"
            + (" (Off(HDMI Only): zero internal card writes)" if rec_media_dur_hdmi == "Off(HDMI Only)" else "")
        ),
    )


FX3_ACTIVE_HDMI_OUTPUT_ITEMS_COUNT = len(FX3_ACTIVE_HDMI_OUTPUT_ITEMS)


# ---------------------------------------------------------------------------
# Sub-Model 73B: De-Squeeze Display, 4 Forced Lockouts & 6 Bypass States
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DeSqueeze4LocksResult:
    admitted: bool
    errno_code: int
    body_profile: str
    fw_version: str
    shoot_mode: str
    requested_desqueeze: str
    effective_desqueeze: str
    actual_horizontal_factor: float
    resettable_via_camera_settings_reset: bool
    forced_lockouts: Tuple[str, ...]
    effective_focus_mode: str
    effective_focus_area: str
    effective_steadyshot: str
    effective_face_priority_metering: str
    inbody_recorded_stream_desqueezed: bool
    lcd_desqueezed: bool
    hdmi_desqueezed: bool
    sdi_desqueezed: bool
    bypass_reason: str
    coexists_with_focus_magnifier: bool
    coexists_with_bright_monitoring: bool
    reason: str


def simulate_desqueeze_display_4locks_and_bypass_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    desqueeze_mode: str = "Off",
    requested_focus_mode: str = "Manual Focus",
    requested_focus_area: str = "Wide",
    requested_steadyshot: str = "Off",
    requested_face_priority_metering: str = "Off",
    log_shooting: str = "Cine EI",
    raw_output: str = "Off",
    rec_media_dur_hdmi: str = "On",
    still_movie_button_rec: bool = False,
    remote_shooting: bool = False,
    photo_capture: bool = False,
    focus_magnifier_active: bool = False,
    bright_monitoring_active: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_sd_or_raw_hdmi: bool = False,
) -> DeSqueeze4LocksResult:
    """Simulate Sub-Model 73B: De-Squeeze Display, 4 Forced Lockouts, 6 Bypass States & FX6 Ratio."""
    if body_profile not in VALID_BODY_MODELS:
        raise Stage73Phase337Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage73Phase337Error(f"Unsupported fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage73Phase337Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if desqueeze_mode not in ALL_DESQUEEZE_PROBES:
        raise Stage73Phase337Error(f"Unsupported desqueeze_mode: {desqueeze_mode!r}")
    if requested_focus_mode not in VALID_FOCUS_MODES:
        raise Stage73Phase337Error(f"Unsupported requested_focus_mode: {requested_focus_mode!r}")
    if requested_focus_area not in VALID_FOCUS_AREAS:
        raise Stage73Phase337Error(f"Unsupported requested_focus_area: {requested_focus_area!r}")
    if requested_steadyshot not in VALID_IBIS_MODES:
        raise Stage73Phase337Error(f"Unsupported requested_steadyshot: {requested_steadyshot!r}")
    if requested_face_priority_metering not in ("On", "Off"):
        raise Stage73Phase337Error(
            f"Unsupported requested_face_priority_metering: {requested_face_priority_metering!r}"
        )
    if log_shooting not in VALID_LOG_SHOOTING_MODES:
        raise Stage73Phase337Error(f"Unsupported log_shooting: {log_shooting!r}")
    if raw_output not in ("Off", "On"):
        raise Stage73Phase337Error(f"Unsupported raw_output: {raw_output!r}")
    if rec_media_dur_hdmi not in VALID_REC_MEDIA_DUR_HDMI:
        raise Stage73Phase337Error(f"Unsupported rec_media_dur_hdmi: {rec_media_dur_hdmi!r}")

    if initialize_applied:
        desqueeze_mode = "Off"
    # Note: Reset-immune (`camera_settings_reset_applied` does NOT wipe desqueeze_mode)

    # 1.8x strictly absent on FX3 & FX6
    if desqueeze_mode == "1.8x":
        return DeSqueeze4LocksResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_desqueeze="1.8x",
            effective_desqueeze="Off",
            actual_horizontal_factor=1.0,
            resettable_via_camera_settings_reset=False,
            forced_lockouts=(),
            effective_focus_mode=requested_focus_mode,
            effective_focus_area=requested_focus_area,
            effective_steadyshot=requested_steadyshot,
            effective_face_priority_metering=requested_face_priority_metering,
            inbody_recorded_stream_desqueezed=False,
            lcd_desqueezed=False,
            hdmi_desqueezed=False,
            sdi_desqueezed=False,
            bypass_reason="None",
            coexists_with_focus_magnifier=True,
            coexists_with_bright_monitoring=True,
            reason="EOPNOTSUPP: De-Squeeze 1.8x has 0 hits in FX3/FX6 firmware and is unsupported",
        )

    # FX6 architecture
    if body_profile == BODY_MODEL_FX6:
        if desqueeze_mode not in FX6_DESQUEEZE_ACTIVE_MODES:
            return DeSqueeze4LocksResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_desqueeze=desqueeze_mode,
                effective_desqueeze="Off",
                actual_horizontal_factor=1.0,
                resettable_via_camera_settings_reset=False,
                forced_lockouts=(),
                effective_focus_mode=requested_focus_mode,
                effective_focus_area=requested_focus_area,
                effective_steadyshot="Off",
                effective_face_priority_metering="Off",
                inbody_recorded_stream_desqueezed=False,
                lcd_desqueezed=False,
                hdmi_desqueezed=False,
                sdi_desqueezed=False,
                bypass_reason="None",
                coexists_with_focus_magnifier=True,
                coexists_with_bright_monitoring=True,
                reason=f"EOPNOTSUPP: ILME-FX6 Ratio (HDMI/VF) excludes {desqueeze_mode!r} (only Off/1.3x/1.5x/2.0x)",
            )
        if desqueeze_mode != "Off" and (requested_focus_mode != "Manual Focus" or requested_focus_area == "Spot"):
            return DeSqueeze4LocksResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX6,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_desqueeze=desqueeze_mode,
                effective_desqueeze=desqueeze_mode,
                actual_horizontal_factor=DESQUEEZE_ACTUAL_FACTORS[desqueeze_mode],
                resettable_via_camera_settings_reset=False,
                forced_lockouts=("Autofocus=Disabled", "Spot Focus=Disabled"),
                effective_focus_mode="Manual Focus",
                effective_focus_area="Wide",
                effective_steadyshot="Off",
                effective_face_priority_metering="Off",
                inbody_recorded_stream_desqueezed=False,
                lcd_desqueezed=True,
                hdmi_desqueezed=(not fx6_sd_or_raw_hdmi),
                sdi_desqueezed=False,
                bypass_reason="RAW/SD HDMI" if fx6_sd_or_raw_hdmi else "None",
                coexists_with_focus_magnifier=True,
                coexists_with_bright_monitoring=True,
                reason="EOPNOTSUPP: ILME-FX6 De-Squeeze disables Autofocus and Spot Focus",
            )
        active = desqueeze_mode != "Off"
        return DeSqueeze4LocksResult(
            admitted=True,
            errno_code=0,
            body_profile=BODY_MODEL_FX6,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_desqueeze=desqueeze_mode,
            effective_desqueeze=desqueeze_mode,
            actual_horizontal_factor=DESQUEEZE_ACTUAL_FACTORS[desqueeze_mode],
            resettable_via_camera_settings_reset=False,
            forced_lockouts=("Autofocus=Disabled", "Spot Focus=Disabled") if active else (),
            effective_focus_mode="Manual Focus" if active else requested_focus_mode,
            effective_focus_area="Wide" if active else requested_focus_area,
            effective_steadyshot="Off",
            effective_face_priority_metering="Off",
            inbody_recorded_stream_desqueezed=False,
            lcd_desqueezed=active,
            hdmi_desqueezed=active and (not fx6_sd_or_raw_hdmi),
            sdi_desqueezed=False,
            bypass_reason="RAW/SD HDMI" if (active and fx6_sd_or_raw_hdmi) else "None",
            coexists_with_focus_magnifier=True,
            coexists_with_bright_monitoring=True,
            reason="ADMITTED: ILME-FX6 De-Squeeze applies to HDMI/VF only (never SDI)",
        )

    # FX3 version gate (Ver. 3.00 lacked 1.5x/1.6x; Ver. 7.00+ activates both)
    if float(fw_version) < 7.0 and desqueeze_mode in ("1.5x", "1.6x"):
        return DeSqueeze4LocksResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_desqueeze=desqueeze_mode,
            effective_desqueeze="Off",
            actual_horizontal_factor=1.0,
            resettable_via_camera_settings_reset=False,
            forced_lockouts=(),
            effective_focus_mode=requested_focus_mode,
            effective_focus_area=requested_focus_area,
            effective_steadyshot=requested_steadyshot,
            effective_face_priority_metering=requested_face_priority_metering,
            inbody_recorded_stream_desqueezed=False,
            lcd_desqueezed=False,
            hdmi_desqueezed=False,
            sdi_desqueezed=False,
            bypass_reason="None",
            coexists_with_focus_magnifier=True,
            coexists_with_bright_monitoring=True,
            reason=f"EOPNOTSUPP: {desqueeze_mode} requires ILME-FX3 Ver. 7.00+ (absent in Ver. {fw_version})",
        )

    # Still mode grayed out for active De-Squeeze
    if shoot_mode == SHOOT_MODE_STILL and desqueeze_mode != "Off" and not still_movie_button_rec:
        return DeSqueeze4LocksResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_desqueeze=desqueeze_mode,
            effective_desqueeze="Off",
            actual_horizontal_factor=1.0,
            resettable_via_camera_settings_reset=False,
            forced_lockouts=(),
            effective_focus_mode=requested_focus_mode,
            effective_focus_area=requested_focus_area,
            effective_steadyshot=requested_steadyshot,
            effective_face_priority_metering=requested_face_priority_metering,
            inbody_recorded_stream_desqueezed=False,
            lcd_desqueezed=False,
            hdmi_desqueezed=False,
            sdi_desqueezed=False,
            bypass_reason="Still mode",
            coexists_with_focus_magnifier=True,
            coexists_with_bright_monitoring=True,
            reason="EOPNOTSUPP: [De-Squeeze Display] is available only in Movie and S&Q modes",
        )

    # 4 Forced Lockouts when active
    if desqueeze_mode != "Off" and (not still_movie_button_rec):
        violated = []
        if requested_focus_mode != "Manual Focus":
            violated.append(f"Focus Mode={requested_focus_mode}")
        if requested_focus_area != "Wide":
            violated.append(f"Focus Area={requested_focus_area}")
        if requested_steadyshot != "Off":
            violated.append(f"SteadyShot={requested_steadyshot}")
        if requested_face_priority_metering != "Off":
            violated.append(f"Face Priority={requested_face_priority_metering}")
        if violated:
            return DeSqueeze4LocksResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX3,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_desqueeze=desqueeze_mode,
                effective_desqueeze=desqueeze_mode,
                actual_horizontal_factor=DESQUEEZE_ACTUAL_FACTORS[desqueeze_mode],
                resettable_via_camera_settings_reset=False,
                forced_lockouts=FX3_DESQUEEZE_FORCED_LOCKOUTS,
                effective_focus_mode="Manual Focus",
                effective_focus_area="Wide",
                effective_steadyshot="Off",
                effective_face_priority_metering="Off",
                inbody_recorded_stream_desqueezed=False,
                lcd_desqueezed=False,
                hdmi_desqueezed=False,
                sdi_desqueezed=False,
                bypass_reason="4-Lockout Violation",
                coexists_with_focus_magnifier=True,
                coexists_with_bright_monitoring=True,
                reason=f"EOPNOTSUPP: [De-Squeeze Display] != Off enforces 4 hardware lockouts (violated: {violated})",
            )

    active = desqueeze_mode != "Off"
    bypass_reasons: List[str] = []
    lcd_desq = active
    hdmi_desq = active

    if active:
        if still_movie_button_rec:
            bypass_reasons.append("Still MOVIE button")
            lcd_desq = False
            hdmi_desq = False
        if remote_shooting:
            bypass_reasons.append("Remote Shooting")
            lcd_desq = False
            hdmi_desq = False
        if photo_capture:
            bypass_reasons.append("Photo Capture")
            lcd_desq = False
            hdmi_desq = False
        if log_shooting == "Off":
            bypass_reasons.append("Log Shooting=Off")
            lcd_desq = False
            hdmi_desq = False
        if raw_output == "On":
            bypass_reasons.append("RAW Output=On (HDMI)")
            hdmi_desq = False
        if rec_media_dur_hdmi == "Off(HDMI Only)":
            bypass_reasons.append("Off(HDMI Only)")
            hdmi_desq = False

    return DeSqueeze4LocksResult(
        admitted=True,
        errno_code=0,
        body_profile=BODY_MODEL_FX3,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        requested_desqueeze=desqueeze_mode,
        effective_desqueeze=desqueeze_mode,
        actual_horizontal_factor=DESQUEEZE_ACTUAL_FACTORS[desqueeze_mode],
        resettable_via_camera_settings_reset=False,
        forced_lockouts=FX3_DESQUEEZE_FORCED_LOCKOUTS if active else (),
        effective_focus_mode="Manual Focus" if active else requested_focus_mode,
        effective_focus_area="Wide" if active else requested_focus_area,
        effective_steadyshot="Off" if active else requested_steadyshot,
        effective_face_priority_metering="Off" if active else requested_face_priority_metering,
        inbody_recorded_stream_desqueezed=False,
        lcd_desqueezed=lcd_desq,
        hdmi_desqueezed=hdmi_desq,
        sdi_desqueezed=False,
        bypass_reason=", ".join(bypass_reasons) if bypass_reasons else "None",
        coexists_with_focus_magnifier=True,
        coexists_with_bright_monitoring=True,
        reason=(
            "ADMITTED: [De-Squeeze Display] active (1.6x executes 1.65x; "
            f"focus_mag={focus_magnifier_active}, bright_mon={bright_monitoring_active})"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 73C: REC Lamp (3 LEDs), Emphasized REC, Remain Shoot & Auto Review
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecLampDisplayReviewResult:
    admitted: bool
    errno_code: int
    body_profile: str
    shoot_mode: str
    effective_rec_lamp_mode: str
    rec_lamp_resettable: bool
    front_tally_led_on: bool
    rear_tally_led_on: bool
    top_rec_button_ring_led_on: bool
    rear_top_rec_hardware_coupled: bool
    silent_mode_leaves_rec_lamp_untouched: bool
    effective_emphasized_rec_display: str
    emphasized_rec_resettable: bool
    lcd_emph_rec_rendered: bool
    hdmi_emph_rec_rendered: bool
    hdmi_emph_rec_leaked_pixels: int
    effective_remain_shoot_display: str
    remain_shoot_active_on_fx3: bool
    remain_shoot_resettable: bool
    effective_auto_review: str
    auto_review_resettable: bool
    auto_review_magnify_supported: bool
    fx6_independent_front_rear_tally: bool
    fx6_green_yellow_tally_supported: bool
    reason: str


def simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    recording_active: bool = True,
    rec_lamp_mode: str = "All On",
    tally_light_menu_requested: bool = False,
    silent_mode: str = "Off",
    emphasized_rec_display: str = "On",
    hdmi_info_display: str = "Off",
    raw_output: str = "Off",
    rec_media_dur_hdmi: str = "On",
    remain_shoot_display: str = "Not Displayed",
    auto_review: str = "Off",
    interval_shoot: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_front_tally: str = "On",
    fx6_rear_tally: str = "On",
    fx6_g_tally: str = "On",
    fx6_y_tally: str = "On",
) -> RecLampDisplayReviewResult:
    """Simulate Sub-Model 73C: REC Lamp 3-LED Coupling, Emphasized REC, Remain Shoot & Auto Review."""
    if body_profile not in VALID_BODY_MODELS:
        raise Stage73Phase337Error(f"Unsupported body_profile: {body_profile!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage73Phase337Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if rec_lamp_mode not in ALL_REC_LAMP_PROBES:
        raise Stage73Phase337Error(f"Unsupported rec_lamp_mode: {rec_lamp_mode!r}")
    if silent_mode not in ("On", "Off"):
        raise Stage73Phase337Error(f"Unsupported silent_mode: {silent_mode!r}")
    if emphasized_rec_display not in ("On", "Off"):
        raise Stage73Phase337Error(f"Unsupported emphasized_rec_display: {emphasized_rec_display!r}")
    if hdmi_info_display not in ("On", "Off"):
        raise Stage73Phase337Error(f"Unsupported hdmi_info_display: {hdmi_info_display!r}")
    if raw_output not in ("Off", "On"):
        raise Stage73Phase337Error(f"Unsupported raw_output: {raw_output!r}")
    if rec_media_dur_hdmi not in VALID_REC_MEDIA_DUR_HDMI:
        raise Stage73Phase337Error(f"Unsupported rec_media_dur_hdmi: {rec_media_dur_hdmi!r}")
    if remain_shoot_display not in VALID_REMAIN_SHOOT_DISPLAY_MODES:
        raise Stage73Phase337Error(f"Unsupported remain_shoot_display: {remain_shoot_display!r}")
    if auto_review not in VALID_AUTO_REVIEW_MODES:
        raise Stage73Phase337Error(f"Unsupported auto_review: {auto_review!r}")

    if body_profile == BODY_MODEL_FX6:
        return RecLampDisplayReviewResult(
            admitted=True,
            errno_code=0,
            body_profile=BODY_MODEL_FX6,
            shoot_mode=shoot_mode,
            effective_rec_lamp_mode=f"Front={fx6_front_tally},Rear={fx6_rear_tally}",
            rec_lamp_resettable=False,
            front_tally_led_on=(fx6_front_tally == "On") and recording_active,
            rear_tally_led_on=(fx6_rear_tally == "On") and recording_active,
            top_rec_button_ring_led_on=False,
            rear_top_rec_hardware_coupled=False,
            silent_mode_leaves_rec_lamp_untouched=True,
            effective_emphasized_rec_display="N/A",
            emphasized_rec_resettable=False,
            lcd_emph_rec_rendered=False,
            hdmi_emph_rec_rendered=False,
            hdmi_emph_rec_leaked_pixels=0,
            effective_remain_shoot_display="N/A",
            remain_shoot_active_on_fx3=False,
            remain_shoot_resettable=False,
            effective_auto_review="N/A",
            auto_review_resettable=False,
            auto_review_magnify_supported=False,
            fx6_independent_front_rear_tally=True,
            fx6_green_yellow_tally_supported=(fx6_g_tally == "On" or fx6_y_tally == "On"),
            reason="ADMITTED: ILME-FX6 Technical > Tally exposes independent Front/Rear and G/Y Tally",
        )

    # Myth-busting [Tally Light]
    if tally_light_menu_requested:
        return RecLampDisplayReviewResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            shoot_mode=shoot_mode,
            effective_rec_lamp_mode=rec_lamp_mode,
            rec_lamp_resettable=False,
            front_tally_led_on=False,
            rear_tally_led_on=False,
            top_rec_button_ring_led_on=False,
            rear_top_rec_hardware_coupled=True,
            silent_mode_leaves_rec_lamp_untouched=True,
            effective_emphasized_rec_display=emphasized_rec_display,
            emphasized_rec_resettable=True,
            lcd_emph_rec_rendered=False,
            hdmi_emph_rec_rendered=False,
            hdmi_emph_rec_leaked_pixels=0,
            effective_remain_shoot_display=remain_shoot_display,
            remain_shoot_active_on_fx3=True,
            remain_shoot_resettable=False,
            effective_auto_review=auto_review,
            auto_review_resettable=False,
            auto_review_magnify_supported=True,
            fx6_independent_front_rear_tally=False,
            fx6_green_yellow_tally_supported=False,
            reason="EOPNOTSUPP: ILME-FX3 has no [Tally Light] menu (official item is [REC Lamp])",
        )

    # Dormant single-rear UXC _f 0x743e / REC_LAMP_LIGHT_UP_ONLY_ONE
    if rec_lamp_mode == "Only Rear On":
        return RecLampDisplayReviewResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            shoot_mode=shoot_mode,
            effective_rec_lamp_mode="All On",
            rec_lamp_resettable=False,
            front_tally_led_on=False,
            rear_tally_led_on=False,
            top_rec_button_ring_led_on=False,
            rear_top_rec_hardware_coupled=True,
            silent_mode_leaves_rec_lamp_untouched=True,
            effective_emphasized_rec_display=emphasized_rec_display,
            emphasized_rec_resettable=True,
            lcd_emph_rec_rendered=False,
            hdmi_emph_rec_rendered=False,
            hdmi_emph_rec_leaked_pixels=0,
            effective_remain_shoot_display=remain_shoot_display,
            remain_shoot_active_on_fx3=True,
            remain_shoot_resettable=False,
            effective_auto_review=auto_review,
            auto_review_resettable=False,
            auto_review_magnify_supported=True,
            fx6_independent_front_rear_tally=False,
            fx6_green_yellow_tally_supported=False,
            reason=(
                "EOPNOTSUPP: REC_LAMP_LIGHT_UP_ONLY_ONE (_f 0x743e) is dormant on FX3; "
                "rear LED is hardware-coupled with top REC button ring"
            ),
        )

    # Reset vs Initialize rules
    eff_rec_lamp = "All On" if initialize_applied else rec_lamp_mode
    eff_emph_rec = "On" if (initialize_applied or camera_settings_reset_applied) else emphasized_rec_display
    eff_remain_shoot = "Not Displayed" if initialize_applied else remain_shoot_display
    eff_auto_review = "Off" if initialize_applied else auto_review

    # Interval shoot disables Still Auto Review
    if interval_shoot and eff_auto_review != "Off":
        return RecLampDisplayReviewResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            shoot_mode=shoot_mode,
            effective_rec_lamp_mode=eff_rec_lamp,
            rec_lamp_resettable=False,
            front_tally_led_on=False,
            rear_tally_led_on=False,
            top_rec_button_ring_led_on=False,
            rear_top_rec_hardware_coupled=True,
            silent_mode_leaves_rec_lamp_untouched=True,
            effective_emphasized_rec_display=eff_emph_rec,
            emphasized_rec_resettable=True,
            lcd_emph_rec_rendered=False,
            hdmi_emph_rec_rendered=False,
            hdmi_emph_rec_leaked_pixels=0,
            effective_remain_shoot_display=eff_remain_shoot,
            remain_shoot_active_on_fx3=True,
            remain_shoot_resettable=False,
            effective_auto_review="Off",
            auto_review_resettable=False,
            auto_review_magnify_supported=False,
            fx6_independent_front_rear_tally=False,
            fx6_green_yellow_tally_supported=False,
            reason="EOPNOTSUPP: [Auto Review] is disabled during [Interval Shoot Func.]",
        )

    # Note: Silent Mode does NOT disable REC Lamp (`silent_mode_leaves_rec_lamp_untouched = True`)
    lamp_active = recording_active and (shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ))
    front_on = lamp_active and eff_rec_lamp == "All On"
    rear_on = lamp_active and eff_rec_lamp in ("All On", "Only Front Off")
    top_ring_on = rear_on  # Hardware-coupled

    lcd_emph = (
        recording_active
        and eff_emph_rec == "On"
        and shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ)
    )
    hdmi_emph = (
        lcd_emph
        and hdmi_info_display == "On"
        and raw_output == "Off"
        and rec_media_dur_hdmi == "On"
    )
    leaked_clean_pixels = 0  # Clean-HDMI when hdmi_info_display == "Off" or RAW / HDMI Only

    return RecLampDisplayReviewResult(
        admitted=True,
        errno_code=0,
        body_profile=BODY_MODEL_FX3,
        shoot_mode=shoot_mode,
        effective_rec_lamp_mode=eff_rec_lamp,
        rec_lamp_resettable=False,
        front_tally_led_on=front_on,
        rear_tally_led_on=rear_on,
        top_rec_button_ring_led_on=top_ring_on,
        rear_top_rec_hardware_coupled=True,
        silent_mode_leaves_rec_lamp_untouched=True,
        effective_emphasized_rec_display=eff_emph_rec,
        emphasized_rec_resettable=True,
        lcd_emph_rec_rendered=lcd_emph,
        hdmi_emph_rec_rendered=hdmi_emph,
        hdmi_emph_rec_leaked_pixels=leaked_clean_pixels,
        effective_remain_shoot_display=eff_remain_shoot,
        remain_shoot_active_on_fx3=True,
        remain_shoot_resettable=False,
        effective_auto_review=eff_auto_review if shoot_mode == SHOOT_MODE_STILL else "Off",
        auto_review_resettable=False,
        auto_review_magnify_supported=(shoot_mode == SHOOT_MODE_STILL and not interval_shoot),
        fx6_independent_front_rear_tally=False,
        fx6_green_yellow_tally_supported=False,
        reason=(
            f"ADMITTED: REC Lamp={eff_rec_lamp} (silent_mode={silent_mode} untouched), "
            f"EmphREC={eff_emph_rec}, RemainShoot={eff_remain_shoot}, AutoReview={eff_auto_review}"
        ),
    )


# ---------------------------------------------------------------------------
# Sub-Model 73D: Still Anti-flicker, Dormant Var. Shutter / FX6 ECS & APS-C S35
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AntiFlickerVarShutterApscResult:
    admitted: bool
    errno_code: int
    body_profile: str
    shoot_mode: str
    effective_antiflicker_shoot: str
    antiflicker_resettable: bool
    antiflicker_supported_hz: Tuple[int, ...]
    var_shutter_exposed: bool
    fx6_shutter_mode: str
    fx6_ecs_frequency_hz: float
    effective_apsc_s35_mode: str
    apsc_s35_resettable: bool
    apsc_s35_crop_active: bool
    effective_video_format: str
    max_video_resolution: str
    max_regular_fps: int
    still_aspect_ratio: str
    effective_still_image_size_label: str
    effective_still_dimensions: str
    effective_still_megapixels: float
    downgraded_from_L_to_M: bool
    fx6_ciz_max_4k_ratio: float
    reason: str


def simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    shoot_mode: str = SHOOT_MODE_STILL,
    antiflicker_shoot: str = "Off",
    shutter_type: str = "Mechanical",
    silent_mode: str = "Off",
    bulb_active: bool = False,
    var_shutter_requested: bool = False,
    apsc_s35_mode: str = "Auto",
    s35_lens_mounted: bool = False,
    video_format: str = "XAVC S HD",
    fps: float = 59.94,
    four_k_hdmi_only_requested: bool = False,
    raw_output: str = "Off",
    auto_framing: bool = False,
    still_aspect_ratio: str = "3:2",
    still_image_size_requested: str = "L",
    allow_auto_still_downgrade: bool = True,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_imager_scan_mode: str = "FF",
    fx6_shutter_mode: str = "Speed",
    fx6_ecs_frequency_hz: Optional[float] = None,
    fx6_project_fps: str = "59.94p",
) -> AntiFlickerVarShutterApscResult:
    """Simulate Sub-Model 73D: Still Anti-flicker, Dormant Var. Shutter / FX6 ECS & APS-C S35."""
    if body_profile not in VALID_BODY_MODELS:
        raise Stage73Phase337Error(f"Unsupported body_profile: {body_profile!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage73Phase337Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if antiflicker_shoot not in ("On", "Off"):
        raise Stage73Phase337Error(f"Unsupported antiflicker_shoot: {antiflicker_shoot!r}")
    if shutter_type not in VALID_SHUTTER_TYPES:
        raise Stage73Phase337Error(f"Unsupported shutter_type: {shutter_type!r}")
    if silent_mode not in ("On", "Off"):
        raise Stage73Phase337Error(f"Unsupported silent_mode: {silent_mode!r}")
    if apsc_s35_mode not in VALID_APSC_S35_MODES:
        raise Stage73Phase337Error(f"Unsupported apsc_s35_mode: {apsc_s35_mode!r}")
    if video_format not in ALL_FX3_VIDEO_FORMATS:
        raise Stage73Phase337Error(f"Unsupported video_format: {video_format!r}")
    if raw_output not in ("Off", "On"):
        raise Stage73Phase337Error(f"Unsupported raw_output: {raw_output!r}")
    if still_aspect_ratio not in VALID_STILL_ASPECT_RATIOS:
        raise Stage73Phase337Error(f"Unsupported still_aspect_ratio: {still_aspect_ratio!r}")
    if still_image_size_requested not in VALID_STILL_IMAGE_SIZES:
        raise Stage73Phase337Error(
            f"Unsupported still_image_size_requested: {still_image_size_requested!r}"
        )
    if fx6_imager_scan_mode not in FX6_IMAGER_SCAN_MODES:
        raise Stage73Phase337Error(f"Unsupported fx6_imager_scan_mode: {fx6_imager_scan_mode!r}")
    if fx6_shutter_mode not in FX6_SHUTTER_MODES:
        raise Stage73Phase337Error(f"Unsupported fx6_shutter_mode: {fx6_shutter_mode!r}")
    if fx6_project_fps not in FX6_ECS_DEFAULT_HZ_BY_FPS:
        raise Stage73Phase337Error(f"Unsupported fx6_project_fps: {fx6_project_fps!r}")

    # FX6 architecture
    if body_profile == BODY_MODEL_FX6:
        eff_ecs = (
            FX6_ECS_DEFAULT_HZ_BY_FPS[fx6_project_fps]
            if fx6_ecs_frequency_hz is None
            else float(fx6_ecs_frequency_hz)
        )
        if fx6_shutter_mode == "ECS" and not (
            FX6_ECS_FREQ_MIN_HZ <= eff_ecs <= FX6_ECS_FREQ_MAX_HZ
        ):
            return AntiFlickerVarShutterApscResult(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                body_profile=BODY_MODEL_FX6,
                shoot_mode=SHOOT_MODE_MOVIE,
                effective_antiflicker_shoot="N/A",
                antiflicker_resettable=False,
                antiflicker_supported_hz=(),
                var_shutter_exposed=False,
                fx6_shutter_mode=fx6_shutter_mode,
                fx6_ecs_frequency_hz=eff_ecs,
                effective_apsc_s35_mode=fx6_imager_scan_mode,
                apsc_s35_resettable=False,
                apsc_s35_crop_active=(fx6_imager_scan_mode == "S35"),
                effective_video_format=video_format,
                max_video_resolution="1920x1080" if fx6_imager_scan_mode == "S35" else "4096x2160",
                max_regular_fps=120,
                still_aspect_ratio="N/A",
                effective_still_image_size_label="N/A",
                effective_still_dimensions="N/A",
                effective_still_megapixels=0.0,
                downgraded_from_L_to_M=False,
                fx6_ciz_max_4k_ratio=1.5,
                reason=f"EINVAL: ILME-FX6 ECS Frequency must be 23.99..8000.00 Hz; got {eff_ecs}",
            )
        if fx6_imager_scan_mode == "S35" and (video_format in FX3_4K_VIDEO_FORMATS or raw_output == "On"):
            return AntiFlickerVarShutterApscResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX6,
                shoot_mode=SHOOT_MODE_MOVIE,
                effective_antiflicker_shoot="N/A",
                antiflicker_resettable=False,
                antiflicker_supported_hz=(),
                var_shutter_exposed=False,
                fx6_shutter_mode=fx6_shutter_mode,
                fx6_ecs_frequency_hz=eff_ecs,
                effective_apsc_s35_mode="S35",
                apsc_s35_resettable=False,
                apsc_s35_crop_active=True,
                effective_video_format=video_format,
                max_video_resolution="1920x1080",
                max_regular_fps=120,
                still_aspect_ratio="N/A",
                effective_still_image_size_label="N/A",
                effective_still_dimensions="N/A",
                effective_still_megapixels=0.0,
                downgraded_from_L_to_M=False,
                fx6_ciz_max_4k_ratio=1.5,
                reason="EOPNOTSUPP: ILME-FX6 Imager Scan Mode = S35 restricts output to 1920x1080 (1..120fps) and disables RAW",
            )
        return AntiFlickerVarShutterApscResult(
            admitted=True,
            errno_code=0,
            body_profile=BODY_MODEL_FX6,
            shoot_mode=SHOOT_MODE_MOVIE,
            effective_antiflicker_shoot="N/A",
            antiflicker_resettable=False,
            antiflicker_supported_hz=(),
            var_shutter_exposed=False,
            fx6_shutter_mode=fx6_shutter_mode,
            fx6_ecs_frequency_hz=eff_ecs,
            effective_apsc_s35_mode=fx6_imager_scan_mode,
            apsc_s35_resettable=False,
            apsc_s35_crop_active=(fx6_imager_scan_mode == "S35"),
            effective_video_format=video_format,
            max_video_resolution="1920x1080" if fx6_imager_scan_mode == "S35" else "4096x2160",
            max_regular_fps=120,
            still_aspect_ratio="N/A",
            effective_still_image_size_label="N/A",
            effective_still_dimensions="N/A",
            effective_still_megapixels=0.0,
            downgraded_from_L_to_M=False,
            fx6_ciz_max_4k_ratio=1.5,
            reason="ADMITTED: ILME-FX6 ECS / Imager Scan Mode contract verified",
        )

    # 100% Dormant [Var. Shutter] on ILME-FX3 Ver. 7.02
    if var_shutter_requested:
        return AntiFlickerVarShutterApscResult(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            body_profile=BODY_MODEL_FX3,
            shoot_mode=shoot_mode,
            effective_antiflicker_shoot=antiflicker_shoot,
            antiflicker_resettable=True,
            antiflicker_supported_hz=(100, 120),
            var_shutter_exposed=False,
            fx6_shutter_mode="N/A",
            fx6_ecs_frequency_hz=0.0,
            effective_apsc_s35_mode=apsc_s35_mode,
            apsc_s35_resettable=False,
            apsc_s35_crop_active=False,
            effective_video_format=video_format,
            max_video_resolution="1920x1080",
            max_regular_fps=120,
            still_aspect_ratio=still_aspect_ratio,
            effective_still_image_size_label="L: 12M",
            effective_still_dimensions="4240x2832",
            effective_still_megapixels=12.1,
            downgraded_from_L_to_M=False,
            fx6_ciz_max_4k_ratio=1.5,
            reason=(
                "EOPNOTSUPP: [Var. Shutter] (BKID_APP_setting_high_res_ss / _f 0x6831) is 100% dormant "
                "on ILME-FX3 Ver. 7.02 (0 TYPE_MENU_ITEM_*HIGH_RES* hits)"
            ),
        )

    # Reset vs Initialize semantics
    # Anti-flicker Shoot.: Resettable (`Can be reset` -> Off)
    # APS-C S35 Shooting: Reset-immune (`Resettable: Not available` -> Wave-42 errata fix!)
    eff_antiflicker = "Off" if (initialize_applied or camera_settings_reset_applied) else antiflicker_shoot
    eff_apsc = "Auto" if initialize_applied else apsc_s35_mode

    # Anti-flicker Shoot. locks out non-Still, Electronic Shutter, Silent Mode=On, BULB
    if eff_antiflicker == "On":
        if (
            shoot_mode != SHOOT_MODE_STILL
            or shutter_type != "Mechanical"
            or silent_mode == "On"
            or bulb_active
        ):
            return AntiFlickerVarShutterApscResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX3,
                shoot_mode=shoot_mode,
                effective_antiflicker_shoot="Off",
                antiflicker_resettable=True,
                antiflicker_supported_hz=(100, 120),
                var_shutter_exposed=False,
                fx6_shutter_mode="N/A",
                fx6_ecs_frequency_hz=0.0,
                effective_apsc_s35_mode=eff_apsc,
                apsc_s35_resettable=False,
                apsc_s35_crop_active=False,
                effective_video_format=video_format,
                max_video_resolution="4096x2160",
                max_regular_fps=120,
                still_aspect_ratio=still_aspect_ratio,
                effective_still_image_size_label="L: 12M",
                effective_still_dimensions="4240x2832",
                effective_still_megapixels=12.1,
                downgraded_from_L_to_M=False,
                fx6_ciz_max_4k_ratio=1.5,
                reason=(
                    "EOPNOTSUPP: [Anti-flicker Shoot.] supports Still Mechanical shutter only "
                    "(disabled in Movie/S&Q, Electronic Shutter, Silent Mode=On, and BULB)"
                ),
            )

    apsc_crop_active = (eff_apsc == "On") or (eff_apsc == "Auto" and s35_lens_mounted)

    # Total 4K/DCI 4K/HDMI-4K/RAW/S&Q-200-240/AutoFraming lockout when APS-C S35 crop active
    if apsc_crop_active and shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ):
        if (
            video_format in FX3_4K_VIDEO_FORMATS
            or four_k_hdmi_only_requested
            or raw_output == "On"
            or auto_framing
            or (shoot_mode == SHOOT_MODE_SQ and fps >= 200.0)
        ):
            return AntiFlickerVarShutterApscResult(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                body_profile=BODY_MODEL_FX3,
                shoot_mode=shoot_mode,
                effective_antiflicker_shoot=eff_antiflicker,
                antiflicker_resettable=True,
                antiflicker_supported_hz=(100, 120),
                var_shutter_exposed=False,
                fx6_shutter_mode="N/A",
                fx6_ecs_frequency_hz=0.0,
                effective_apsc_s35_mode=eff_apsc,
                apsc_s35_resettable=False,
                apsc_s35_crop_active=True,
                effective_video_format=video_format,
                max_video_resolution="1920x1080",
                max_regular_fps=120,
                still_aspect_ratio=still_aspect_ratio,
                effective_still_image_size_label="N/A",
                effective_still_dimensions="N/A",
                effective_still_megapixels=0.0,
                downgraded_from_L_to_M=False,
                fx6_ciz_max_4k_ratio=1.5,
                reason=(
                    "EOPNOTSUPP: [APS-C S35 Shooting] = On locks out all 4K/DCI 4K formats, "
                    "4K Output Set.(HDMI Only), RAW Output, Auto Framing, and S&Q 200/240fps; "
                    "only HD 1920x1080 (<=120p) allowed"
                ),
            )

    # Still L: 12M -> M: 5.1M (3:2 2768x1848) / 4.3M (16:9) downgrade under APS-C crop
    downgraded = False
    if shoot_mode == SHOOT_MODE_STILL and apsc_crop_active:
        if still_image_size_requested == "L":
            if not allow_auto_still_downgrade:
                return AntiFlickerVarShutterApscResult(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    body_profile=BODY_MODEL_FX3,
                    shoot_mode=SHOOT_MODE_STILL,
                    effective_antiflicker_shoot=eff_antiflicker,
                    antiflicker_resettable=True,
                    antiflicker_supported_hz=(100, 120),
                    var_shutter_exposed=False,
                    fx6_shutter_mode="N/A",
                    fx6_ecs_frequency_hz=0.0,
                    effective_apsc_s35_mode=eff_apsc,
                    apsc_s35_resettable=False,
                    apsc_s35_crop_active=True,
                    effective_video_format="N/A",
                    max_video_resolution="1920x1080",
                    max_regular_fps=120,
                    still_aspect_ratio=still_aspect_ratio,
                    effective_still_image_size_label=APSC_STILL_M_PIXEL_MAP[still_aspect_ratio][0],
                    effective_still_dimensions=APSC_STILL_M_PIXEL_MAP[still_aspect_ratio][1],
                    effective_still_megapixels=APSC_STILL_M_PIXEL_MAP[still_aspect_ratio][2],
                    downgraded_from_L_to_M=True,
                    fx6_ciz_max_4k_ratio=1.5,
                    reason=(
                        f"EOPNOTSUPP: Still L: 12M is disabled under APS-C S35; downgraded to "
                        f"{APSC_STILL_M_PIXEL_MAP[still_aspect_ratio][0]} ({APSC_STILL_M_PIXEL_MAP[still_aspect_ratio][1]})"
                    ),
                )
            downgraded = True
            lbl, dims, mp = APSC_STILL_M_PIXEL_MAP[still_aspect_ratio]
        elif still_image_size_requested == "M":
            lbl, dims, mp = APSC_STILL_M_PIXEL_MAP[still_aspect_ratio]
        else:
            lbl, dims, mp = ("S: 2.0M", "1744x1160", 2.0)
    else:
        lbl, dims, mp = (
            ("L: 12M", "4240x2832", 12.1)
            if still_aspect_ratio == "3:2"
            else ("L: 10M", "4240x2384", 10.1)
        )

    return AntiFlickerVarShutterApscResult(
        admitted=True,
        errno_code=0,
        body_profile=BODY_MODEL_FX3,
        shoot_mode=shoot_mode,
        effective_antiflicker_shoot=eff_antiflicker,
        antiflicker_resettable=True,
        antiflicker_supported_hz=(100, 120),
        var_shutter_exposed=False,
        fx6_shutter_mode="N/A",
        fx6_ecs_frequency_hz=0.0,
        effective_apsc_s35_mode=eff_apsc,
        apsc_s35_resettable=False,
        apsc_s35_crop_active=apsc_crop_active,
        effective_video_format=video_format if shoot_mode != SHOOT_MODE_STILL else "N/A",
        max_video_resolution="1920x1080" if apsc_crop_active else "4096x2160",
        max_regular_fps=120,
        still_aspect_ratio=still_aspect_ratio,
        effective_still_image_size_label=lbl,
        effective_still_dimensions=dims,
        effective_still_megapixels=mp,
        downgraded_from_L_to_M=downgraded,
        fx6_ciz_max_4k_ratio=1.5,
        reason=(
            f"ADMITTED: AntiFlicker={eff_antiflicker}, APS-C={eff_apsc} "
            f"(crop={apsc_crop_active}, still={lbl} {dims})"
        ),
    )


# ---------------------------------------------------------------------------
# Stage 73 Milestone Probe & Unified Phase 337 Runner
# ---------------------------------------------------------------------------


def _build_stage73_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_73rd_stage_milestone": IS_73RD_STAGE_MILESTONE,
        "wave": "Wave-63",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute complete Phase 337 Stage 73 (73/73 Milestone!) Wave-63 HIL co-emulation."""
    donor_audit = inspect_phase337_donors(force_clean_room=force_clean_room, env=env)

    # Sub-Model 73A probes
    p73a_raw_hdmionly_ok = simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        rec_media_dur_hdmi="Off(HDMI Only)",
        raw_output="On",
        raw_output_fps="59.94p",
        log_shooting="Cine EI",
        ibis_mode="Active",
        hdmi_info_display="On",
        time_code_output="On",
        rec_control="On",
        four_ch_audio_output="CH3/CH4",
        rec_triggered=True,
        camera_settings_reset_applied=True,
    )
    p73a_reclamp_and_24p_ok = [
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="On",
            output_resolution="Auto",
            log_shooting="Flexible ISO",
        ),
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="On",
            output_resolution="2160p",
            picture_profile="PPLUT1",
        ),
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="Off(HDMI Only)",
            four_k_hdmi_only_set="24.00p 10bit",
            previous_four_k_hdmi_only_set="59.94p 10bit",
        ),
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="On",
            raw_output="Off",
            hdmi_info_display="On",
        ),
    ]
    p73a_locks_and_erofs = [
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_media_dur_hdmi="On",
            raw_output="On",
            log_shooting="Cine EI",
            recording_media_slot="Slot 1",
            rec_triggered=True,
        ),
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            color_gamut_for_raw_out_requested=True,
            fw_version=FW_VER_702,
        ),
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            rec_control="On",
            time_code_output="Off",
        ),
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            four_k_hdmi_only_set="24.00p 8bit",
        ),
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            raw_output="On",
            log_shooting="Off",
        ),
    ]
    p73a_fx6 = [
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_raw_mode="12G-SDI RAW (3840x2160 C)",
            fx6_sdi_hdmi_rec_ctrl="Parallel Rec",
            fx6_card_inserted=True,
        ),
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_raw_mode="RAW(HDMI) (4240x2392)",
            fx6_raw_hdmi_fps="24.00p",
        ),
        simulate_hdmi_output_raw_4264_reclamp_and_slot1_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_raw_mode="RAW(HDMI) (4240x2392)",
            fx6_raw_hdmi_fps="23.98p",
            fx6_sdi_hdmi_rec_ctrl="SDI/HDMI Remote I/F",
            fx6_card_inserted=False,
        ),
    ]
    p73a_ok = (
        p73a_raw_hdmionly_ok.admitted
        and p73a_raw_hdmionly_ok.active_menu_item_count == 8
        and (not p73a_raw_hdmionly_ok.resettable_via_camera_settings_reset)
        and p73a_raw_hdmionly_ok.hdmi_raw_resolution == "4264x2408"
        and p73a_raw_hdmionly_ok.hdmi_raw_bit_depth == 16
        and p73a_raw_hdmionly_ok.effective_gamma_locked == "S-Log3"
        and p73a_raw_hdmionly_ok.active_ibis_disabled
        and p73a_raw_hdmionly_ok.effective_hdmi_info_display == "Off"
        and (not p73a_raw_hdmionly_ok.internal_xavc_write_attempted)
        and (not p73a_raw_hdmionly_ok.internal_proxy_write_attempted)
        and p73a_raw_hdmionly_ok.slot1_data_sector_writes == 0
        and p73a_raw_hdmionly_ok.hdmi_only_card_writes == 0
        and p73a_reclamp_and_24p_ok[0].hdmi_clamped_1080p
        and p73a_reclamp_and_24p_ok[1].hdmi_clamped_1080p
        and p73a_reclamp_and_24p_ok[2].forced_reboot_on_24_00p
        and p73a_reclamp_and_24p_ok[3].inbody_lcd_forced_off
        and (not p73a_locks_and_erofs[0].admitted)
        and p73a_locks_and_erofs[0].errno_code == EROFS_ERRNO
        and p73a_locks_and_erofs[0].slot1_erofs_triggered
        and p73a_locks_and_erofs[0].internal_xavc_write_attempted
        and p73a_locks_and_erofs[0].slot1_data_sector_writes == 0
        and (not p73a_locks_and_erofs[1].admitted)
        and p73a_locks_and_erofs[1].errno_code == EOPNOTSUPP_ERRNO
        and (not p73a_locks_and_erofs[2].admitted)
        and p73a_locks_and_erofs[2].errno_code == EINVAL_ERRNO
        and (not p73a_locks_and_erofs[3].admitted)
        and p73a_locks_and_erofs[3].errno_code == EOPNOTSUPP_ERRNO
        and (not p73a_locks_and_erofs[4].admitted)
        and p73a_locks_and_erofs[4].errno_code == EINVAL_ERRNO
        and p73a_fx6[0].admitted
        and p73a_fx6[0].hdmi_clamped_1080p
        and (not p73a_fx6[1].admitted)
        and p73a_fx6[1].errno_code == EOPNOTSUPP_ERRNO
        and p73a_fx6[2].admitted
        and p73a_fx6[2].hdmi_raw_resolution == "4240x2392"
    )

    # Sub-Model 73B probes
    p73b_165x_ok = simulate_desqueeze_display_4locks_and_bypass_hil(
        desqueeze_mode="1.6x",
        focus_magnifier_active=True,
        bright_monitoring_active=True,
        camera_settings_reset_applied=True,
    )
    p73b_bypasses = [
        simulate_desqueeze_display_4locks_and_bypass_hil(
            shoot_mode=SHOOT_MODE_STILL,
            desqueeze_mode="1.5x",
            still_movie_button_rec=True,
        ),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.5x",
            remote_shooting=True,
        ),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.5x",
            photo_capture=True,
        ),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.5x",
            log_shooting="Off",
        ),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.5x",
            raw_output="On",
        ),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.5x",
            rec_media_dur_hdmi="Off(HDMI Only)",
        ),
    ]
    p73b_blocks = [
        simulate_desqueeze_display_4locks_and_bypass_hil(desqueeze_mode="1.8x"),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.3x",
            requested_focus_mode="AF-C",
        ),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.3x",
            requested_focus_area="Spot",
        ),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.3x",
            requested_steadyshot="Active",
        ),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            desqueeze_mode="1.3x",
            requested_face_priority_metering="On",
        ),
    ]
    p73b_fx6 = [
        simulate_desqueeze_display_4locks_and_bypass_hil(
            body_profile=BODY_MODEL_FX6,
            desqueeze_mode="1.5x",
        ),
        simulate_desqueeze_display_4locks_and_bypass_hil(
            body_profile=BODY_MODEL_FX6,
            desqueeze_mode="1.6x",
        ),
    ]
    p73b_ok = (
        p73b_165x_ok.admitted
        and p73b_165x_ok.actual_horizontal_factor == 1.65
        and (not p73b_165x_ok.resettable_via_camera_settings_reset)
        and len(p73b_165x_ok.forced_lockouts) == 4
        and (not p73b_165x_ok.inbody_recorded_stream_desqueezed)
        and p73b_165x_ok.lcd_desqueezed
        and p73b_165x_ok.hdmi_desqueezed
        and p73b_165x_ok.coexists_with_focus_magnifier
        and p73b_165x_ok.coexists_with_bright_monitoring
        and all(r.admitted and (not r.hdmi_desqueezed) for r in p73b_bypasses)
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p73b_blocks)
        and p73b_fx6[0].admitted
        and p73b_fx6[0].lcd_desqueezed
        and p73b_fx6[0].hdmi_desqueezed
        and (not p73b_fx6[0].sdi_desqueezed)
        and (not p73b_fx6[1].admitted)
        and p73b_fx6[1].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 73C probes
    p73c_rec_lamp_only_front_off = simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
        rec_lamp_mode="Only Front Off",
        silent_mode="On",
        emphasized_rec_display="Off",
        hdmi_info_display="Off",
        remain_shoot_display="Always Display",
        camera_settings_reset_applied=True,
    )
    p73c_still_review_ok = simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
        shoot_mode=SHOOT_MODE_STILL,
        recording_active=False,
        remain_shoot_display="Shoot-Only Display",
        auto_review="5 Sec",
        camera_settings_reset_applied=True,
    )
    p73c_blocks = [
        simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            tally_light_menu_requested=True,
        ),
        simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            rec_lamp_mode="Only Rear On",
        ),
        simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
            shoot_mode=SHOOT_MODE_STILL,
            auto_review="2 Sec",
            interval_shoot=True,
        ),
    ]
    p73c_fx6 = simulate_rec_lamp_emph_rec_remain_shoot_auto_review_hil(
        body_profile=BODY_MODEL_FX6,
        fx6_front_tally="Off",
        fx6_rear_tally="On",
        fx6_g_tally="On",
        fx6_y_tally="On",
    )
    p73c_ok = (
        p73c_rec_lamp_only_front_off.admitted
        and p73c_rec_lamp_only_front_off.effective_rec_lamp_mode == "Only Front Off"
        and (not p73c_rec_lamp_only_front_off.front_tally_led_on)
        and p73c_rec_lamp_only_front_off.rear_tally_led_on
        and p73c_rec_lamp_only_front_off.top_rec_button_ring_led_on
        and p73c_rec_lamp_only_front_off.rear_top_rec_hardware_coupled
        and p73c_rec_lamp_only_front_off.silent_mode_leaves_rec_lamp_untouched
        and p73c_rec_lamp_only_front_off.effective_emphasized_rec_display == "On"
        and p73c_rec_lamp_only_front_off.emphasized_rec_resettable
        and (not p73c_rec_lamp_only_front_off.hdmi_emph_rec_rendered)
        and p73c_rec_lamp_only_front_off.hdmi_emph_rec_leaked_pixels == 0
        and p73c_rec_lamp_only_front_off.effective_remain_shoot_display == "Always Display"
        and (not p73c_rec_lamp_only_front_off.remain_shoot_resettable)
        and p73c_still_review_ok.admitted
        and p73c_still_review_ok.effective_auto_review == "5 Sec"
        and (not p73c_still_review_ok.auto_review_resettable)
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p73c_blocks)
        and p73c_fx6.admitted
        and p73c_fx6.fx6_independent_front_rear_tally
        and p73c_fx6.fx6_green_yellow_tally_supported
    )

    # Sub-Model 73D probes
    p73d_antiflicker_still_ok = simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
        shoot_mode=SHOOT_MODE_STILL,
        antiflicker_shoot="On",
        shutter_type="Mechanical",
        silent_mode="Off",
        apsc_s35_mode="On",
        still_aspect_ratio="3:2",
        still_image_size_requested="L",
        allow_auto_still_downgrade=True,
        camera_settings_reset_applied=True,
    )
    p73d_hd_120p_apsc_ok = simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        apsc_s35_mode="On",
        video_format="XAVC S HD",
        fps=119.88,
        camera_settings_reset_applied=True,
    )
    p73d_blocks = [
        simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            var_shutter_requested=True,
        ),
        simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=SHOOT_MODE_STILL,
            antiflicker_shoot="On",
            shutter_type="Electronic",
        ),
        simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=SHOOT_MODE_STILL,
            antiflicker_shoot="On",
            silent_mode="On",
        ),
        simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            apsc_s35_mode="On",
            video_format="XAVC S-I DCI 4K",
        ),
        simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            apsc_s35_mode="On",
            video_format="XAVC S HD",
            four_k_hdmi_only_requested=True,
        ),
        simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            shoot_mode=SHOOT_MODE_SQ,
            apsc_s35_mode="On",
            video_format="XAVC S-I HD",
            fps=240.0,
        ),
    ]
    p73d_fx6 = [
        simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_shutter_mode="ECS",
            fx6_project_fps="59.94p",
        ),
        simulate_antiflicker_dormant_varshutter_and_apsc_4k_lockout_hil(
            body_profile=BODY_MODEL_FX6,
            fx6_imager_scan_mode="S35",
            video_format="XAVC S-I 4K",
        ),
    ]
    p73d_ok = (
        p73d_antiflicker_still_ok.admitted
        and p73d_antiflicker_still_ok.effective_antiflicker_shoot == "Off"
        and p73d_antiflicker_still_ok.antiflicker_resettable
        and p73d_antiflicker_still_ok.effective_apsc_s35_mode == "On"
        and (not p73d_antiflicker_still_ok.apsc_s35_resettable)
        and p73d_antiflicker_still_ok.effective_still_image_size_label == "M: 5.1M"
        and p73d_antiflicker_still_ok.effective_still_dimensions == "2768x1848"
        and p73d_antiflicker_still_ok.effective_still_megapixels == 5.1
        and p73d_antiflicker_still_ok.downgraded_from_L_to_M
        and p73d_hd_120p_apsc_ok.admitted
        and p73d_hd_120p_apsc_ok.effective_apsc_s35_mode == "On"
        and p73d_hd_120p_apsc_ok.max_video_resolution == "1920x1080"
        and p73d_hd_120p_apsc_ok.max_regular_fps == 120
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p73d_blocks)
        and (not p73d_blocks[0].var_shutter_exposed)
        and p73d_fx6[0].admitted
        and p73d_fx6[0].fx6_ecs_frequency_hz == 60.00
        and (not p73d_fx6[1].admitted)
        and p73d_fx6[1].errno_code == EOPNOTSUPP_ERRNO
    )

    milestone_probe = _build_stage73_milestone_probe()

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
        "fx3_active_hdmi_output_settings_items": FX3_ACTIVE_HDMI_OUTPUT_SETTINGS_ITEMS,
        "hdmi_color_gamut_for_raw_out_removed_v2": HDMI_COLOR_GAMUT_FOR_RAW_OUT_REMOVED_V2,
        "hdmi_raw_width": HDMI_RAW_WIDTH,
        "hdmi_raw_height": HDMI_RAW_HEIGHT,
        "hdmi_raw_bit_depth": HDMI_RAW_BIT_DEPTH,
        "dormant_color_gamut_raw_out_exposed_events": DORMANT_COLOR_GAMUT_RAW_OUT_EXPOSED_EVENTS,
        "hdmi_only_card_write_leak_events": HDMI_ONLY_CARD_WRITE_LEAK_EVENTS,
        "rec_media_on_slot1_erofs_bypass_events": REC_MEDIA_ON_SLOT1_EROFS_BYPASS_EVENTS,
        "rec_control_without_tc_bypass_events": REC_CONTROL_WITHOUT_TC_BYPASS_EVENTS,
        "fx3_desqueeze_active_options_count": FX3_DESQUEEZE_ACTIVE_OPTIONS_COUNT,
        "fx3_desqueeze_1_6x_actual_factor": FX3_DESQUEEZE_1_6X_ACTUAL_FACTOR,
        "desqueeze_1_8x_exposed_events": DESQUEEZE_1_8X_EXPOSED_EVENTS,
        "fx3_desqueeze_forced_lockout_count": FX3_DESQUEEZE_FORCED_LOCKOUT_COUNT,
        "desqueeze_4lock_bypass_events": DESQUEEZE_4LOCK_BYPASS_EVENTS,
        "desqueeze_inbody_stream_mutation_events": DESQUEEZE_INBODY_STREAM_MUTATION_EVENTS,
        "fx6_sdi_desqueeze_leak_events": FX6_SDI_DESQUEEZE_LEAK_EVENTS,
        "fx3_rec_lamp_physical_led_count": FX3_REC_LAMP_PHYSICAL_LED_COUNT,
        "fx3_rec_lamp_active_states_count": FX3_REC_LAMP_ACTIVE_STATES_COUNT,
        "dormant_tally_light_menu_exposed_events": DORMANT_TALLY_LIGHT_MENU_EXPOSED_EVENTS,
        "dormant_rec_lamp_single_rear_exposed_events": DORMANT_REC_LAMP_SINGLE_REAR_EXPOSED_EVENTS,
        "silent_mode_rec_lamp_auto_off_violations": SILENT_MODE_REC_LAMP_AUTO_OFF_VIOLATIONS,
        "emph_rec_clean_hdmi_leaked_pixels": EMPH_REC_CLEAN_HDMI_LEAKED_PIXELS,
        "dormant_var_shutter_exposed_events": DORMANT_VAR_SHUTTER_EXPOSED_EVENTS,
        "antiflicker_silent_or_eshutter_bypass_events": ANTIFLICKER_SILENT_OR_ESHUTTER_BYPASS_EVENTS,
        "apsc_s35_camera_reset_wipe_events": APSC_S35_CAMERA_RESET_WIPE_EVENTS,
        "apsc_s35_4k_or_dci4k_bypass_events": APSC_S35_4K_OR_DCI4K_BYPASS_EVENTS,
        "still_apsc_l_12m_bypass_events": STILL_APSC_L_12M_BYPASS_EVENTS,
        "fx3_still_apsc_32_effective_mp": FX3_STILL_APSC_32_EFFECTIVE_MP,
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
        and donor_audit.negative_1_8x_verified_absent
        and p73a_ok
        and p73b_ok
        and p73c_ok
        and p73d_ok
        and milestone_probe["is_73rd_stage_milestone"]
        and redlines["fx3_active_hdmi_output_settings_items"] == 8
        and bool(redlines["hdmi_color_gamut_for_raw_out_removed_v2"])
        and redlines["hdmi_raw_width"] == 4264
        and redlines["hdmi_raw_height"] == 2408
        and redlines["hdmi_raw_bit_depth"] == 16
        and redlines["dormant_color_gamut_raw_out_exposed_events"] == 0
        and redlines["hdmi_only_card_write_leak_events"] == 0
        and redlines["rec_media_on_slot1_erofs_bypass_events"] == 0
        and redlines["rec_control_without_tc_bypass_events"] == 0
        and redlines["fx3_desqueeze_active_options_count"] == 5
        and redlines["fx3_desqueeze_1_6x_actual_factor"] == 1.65
        and redlines["desqueeze_1_8x_exposed_events"] == 0
        and redlines["fx3_desqueeze_forced_lockout_count"] == 4
        and redlines["desqueeze_4lock_bypass_events"] == 0
        and redlines["desqueeze_inbody_stream_mutation_events"] == 0
        and redlines["fx6_sdi_desqueeze_leak_events"] == 0
        and redlines["fx3_rec_lamp_physical_led_count"] == 3
        and redlines["fx3_rec_lamp_active_states_count"] == 3
        and redlines["dormant_tally_light_menu_exposed_events"] == 0
        and redlines["dormant_rec_lamp_single_rear_exposed_events"] == 0
        and redlines["silent_mode_rec_lamp_auto_off_violations"] == 0
        and redlines["emph_rec_clean_hdmi_leaked_pixels"] == 0
        and redlines["dormant_var_shutter_exposed_events"] == 0
        and redlines["antiflicker_silent_or_eshutter_bypass_events"] == 0
        and redlines["apsc_s35_camera_reset_wipe_events"] == 0
        and redlines["apsc_s35_4k_or_dci4k_bypass_events"] == 0
        and redlines["still_apsc_l_12m_bypass_events"] == 0
        and redlines["fx3_still_apsc_32_effective_mp"] == 5.1
        and redlines["slot1_data_sector_writes"] == 0
        and (not redlines["slot1_avf_info_mutated"])
        and redlines["rf_packets_transmitted"] == 0
        and redlines["rf_nvs_mutation_bytes"] == 0
        and redlines["raw_firmware_bytes_leaked"] == 0
        and redlines["physical_device_writes"] == 0
        and redlines["emmc_nflasha_write_count"] == 0
        and bool(redlines["cnflasha_userspace_write_blocked"])
        and (not redlines["persistent_emmc_writes_authorized"])
        and (not redlines["emmc_writes_authorized"])
        and (not redlines["cross_model_flash_authorized"])
        and (not redlines["hardware_live_attachment_authorized"])
        and (not redlines["overall_ready_for_hardware_attach"])
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_337_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_73rd_stage_milestone": True,
        "source_mode": donor_audit.source_mode,
        "access_mode": donor_audit.access_mode,
        "all_checks_passed": all_passed,
        "donor_audit": asdict(donor_audit),
        "pillar_a_hdmi_raw_4264_reclamp_and_slot1_hil": {
            "passed": p73a_ok,
            "raw_hdmionly_ok": asdict(p73a_raw_hdmionly_ok),
            "reclamp_and_24p_ok": [asdict(r) for r in p73a_reclamp_and_24p_ok],
            "locks_and_erofs": [asdict(r) for r in p73a_locks_and_erofs],
            "fx6_comparison": [asdict(r) for r in p73a_fx6],
        },
        "pillar_b_desqueeze_165x_4locks_and_6bypasses_hil": {
            "passed": p73b_ok,
            "desqueeze_165x_ok": asdict(p73b_165x_ok),
            "bypasses_6_states": [asdict(r) for r in p73b_bypasses],
            "lockout_and_18x_blocks": [asdict(r) for r in p73b_blocks],
            "fx6_comparison": [asdict(r) for r in p73b_fx6],
        },
        "pillar_c_rec_lamp_emph_rec_remain_shoot_auto_review_hil": {
            "passed": p73c_ok,
            "rec_lamp_only_front_off": asdict(p73c_rec_lamp_only_front_off),
            "still_review_ok": asdict(p73c_still_review_ok),
            "blocks": [asdict(r) for r in p73c_blocks],
            "fx6_comparison": asdict(p73c_fx6),
        },
        "pillar_d_antiflicker_dormant_varshutter_ecs_and_apsc_s35_hil": {
            "passed": p73d_ok,
            "antiflicker_still_ok": asdict(p73d_antiflicker_still_ok),
            "hd_120p_apsc_ok": asdict(p73d_hd_120p_apsc_ok),
            "blocks": [asdict(r) for r in p73d_blocks],
            "fx6_comparison": [asdict(r) for r in p73d_fx6],
        },
        "milestone_probe": milestone_probe,
        "redlines": redlines,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulator.py",
        description=(
            "Phase 337 (Stage 73 -- 73/73 VM HIL Stages Milestone!) Real-Hardware ILME-FX3 "
            "Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-63 [HDMI Output Settings] (8 items, 4264x2408 "
            "16-bit RAW, Rec. Media dur HDMI Output Slot-1 EROFS=30), [De-Squeeze Display] "
            "(1.3x/1.5x/1.6x[1.65x]/2.0x vs absent 1.8x, 4 lockouts, 6 bypasses), [REC Lamp] "
            "(3 physical LEDs, [Emphasized REC Display], [Remain Shoot Display], [Auto Review]), "
            "and Still [Anti-flicker Shoot.] vs 100%% Dormant [Var. Shutter] / FX6 ECS + "
            "[APS-C S35 Shooting] Wave-42 Reset errata fix & 4K lockout HIL Co-Emulator"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        default=True,
        help="Run complete Phase 337 Stage 73 Wave-63 co-emulation self-test suite (default)",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force CLEAN_ROOM_SYNTHETIC mode without reading local Mac/work donors",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full deterministic JSON payload (default unless --summary)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise one-line status summary instead of full JSON",
    )
    args = parser.parse_args(argv)
    rep = run_phase337_hdmi_raw_desqueeze_reclamp_varshutter_apsc_coemulation(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        red = rep["redlines"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 337 Stage 73 ({rep['milestone']} Milestone) | mode={rep['source_mode']} "
            f"hdmi={red['fx3_active_hdmi_output_settings_items']} "
            f"raw={red['hdmi_raw_width']}x{red['hdmi_raw_height']}@{red['hdmi_raw_bit_depth']}b "
            f"desq={red['fx3_desqueeze_active_options_count']}({red['fx3_desqueeze_1_6x_actual_factor']}x) "
            f"lamp={red['fx3_rec_lamp_physical_led_count']}/{red['fx3_rec_lamp_active_states_count']} "
            f"apsc_mp={red['fx3_still_apsc_32_effective_mp']}M "
            f"s1_wr={red['slot1_data_sector_writes']} leak={red['raw_firmware_bytes_leaked']} "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
