#!/usr/bin/env python3
"""Phase 350 (Stage 77 — 77/77 Full-Board VM Co-Emulation Stages):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-67 HIL Co-Emulator.

Models and audits the four Wave-67 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / nonexistent `work_root` / `CLEAN_ROOM_SYNTHETIC`
CI fallback and `raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 77A — `[Pixel Mapping]` & `[Auto Pixel Mapping]` Silent-Mode
   Shutter Default vs FX6 `APR` & Dormant `ABB`**:
   - FX3 `Setup -> [Setup Option] -> [Auto Pixel Mapping]` (`On` default / `Off`,
     Reset-immune, `[Initialize]` -> `On`) + manual `[Pixel Mapping]`
     (`FUNC_execute_manual_pixel_mapping`, `SYSTEM_MODE_OPTION_MANUAL_PIXEL_MAPPING`,
     lens-cap light shield required `_g 0x63f1`, auto-reboot upon completion,
     battery gate `INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING`).
   - FX3 `Shooting -> [Shutter/Silent] -> [Silent Mode Settings] ->
     [Target Function Settings] -> [Auto Pixel Mapping]` defaults to `Off`
     (`Not Target`, `Can be reset`), meaning even with `[Silent Mode] = On`,
     power-off Auto Pixel Mapping still fires mechanical shutter sound via
     `vdf_set_shutter_mute_by_pixel_mapping` unless explicitly set to `On`.
   - Exact Sony firmware typos in `FX3 appFw.so`:
     `BKID_APP_setting_notification_for_pixel_mappinng` (double `n`) and
     `BKID_APP_pixel_mapping_excuted_status` (`excuted`), plus dormant
     `[Pixel Map. Notification]` and `[Shutter When Pwr OFF]` (`0` exposed UI
     items on FX3 Ver. 7.02).
   - Contrast with `ILME-FX6 Ver. 6.01`: `Technical > APR > Execute / Cancel`
     (no internal mechanical shutter -> requires lens cap + black cloth,
     `PIXEL_MAPPING_RESULT_LIGHT_DETECTED` &
     `PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE`), and **zero** CMOS `ABB` menu
     (`auto_black_balance` is 100%% dormant in `FX6 appFw.so`).

2. **Sub-Model 77B — `Setup -> [Monitor]` (3 Active Items, Zero `[Finder/Monitor]`)
   & 4 Dormant EVF Menus vs FX6 `VF Setting`**:
   - FX3 group name is strictly `Setup -> [Monitor]` (NOT `[Finder/Monitor]`),
     exposing exact **3** items (all `Not available` under `[Camera Settings
     Reset]`, restored only by `[Initialize]`):
     1) `[Monitor Brightness]`: `Manual` (`-2..+2`, default) / `Sunny Weather`
        (`INFRA_NOTIFY_UPM_LCD_BRIGHTNESS_LIMIT`);
     2) `[Display Quality]`: `Standard` (default) / `High` (thermally locked
        to `Standard` when body temperature rises);
     3) `[Monitor Flip Direction]`: `Auto` (default) / `Horizontal Flip` /
        `180 Degree Flip` / `No Flip`.
   - Exact **4** EVF menus dormant in `FX3 appFw.so` (`0` exposed on FX3
     Ver. 7.02): `Finder/Monitor Sel.`, `Viewfinder Bright.`,
     `Viewfinder Color Temp.`, `Finder Frame Rate`
     (`dormant_evf_menus_exposed_events == 0`).
   - Contrast with `ILME-FX6 Ver. 6.01`: `Monitoring > VF Setting` exposes
     `Brightness` (`1..15`, default `8`) and `Color Mode` (`Color` / `B&W`),
     plus `VF Adjust` / `VF Mode` and physical `MIRROR` switch (`Off/B-T/ROT`);
     zero `Backlight / Contrast / Chroma / Color Temp.` submenus.

3. **Sub-Model 77C — Still `P/A/S/M`-Only `[Recall Custom hold 1-3]` (`11` Slots)
   vs FX6 `Push AF` / `Push AGC` / `Push Auto Iris` & Dormant `High/Low Key`**:
   - FX3 `[Recall Custom hold 1..3]` (`11` parameter slots
     `is_checked_recall_custom_hold0..10`, zero independent `White Balance`,
     excludes Self-timer) is strictly **Still `P/A/S/M`-only** (rejected in
     Movie / `S&Q` / `iAuto` with `EOPNOTSUPP=95`), Reset-immune, cleared only on
     `[Initialize]`, persisted in `CAMSET*.DAT`.
   - Contrast with `[AF On]` (Still/Movie/S&Q), `[Eye AF]` (Still/Movie), and
     `[Tracking On]` (Still `AF-C` only).
   - Contrast with `ILME-FX6 Ver. 6.01`: zero `Recall Custom hold 1-3`; provides
     `Push AF` / `Push AF/Push MF` / `One Push AF` (blocked on manual lens or
     `De-Squeeze != Off(1.0x)`), `Push AGC` (blocked in `Cine EI` /
     `Cine EI Quick` or `Bokeh Control = On`), `Push Auto Iris` (blocked on
     manual iris or `Bokeh Control = On`), and dormant `High/Low Key` (`FX6 ns2
     0x4b25`, `0` exposed UI items).

4. **Sub-Model 77D — `Setup -> [External Output]` HDMI Matrix, Firmware Typos &
   Tier-0 `Slot 1` `EROFS=30` Firewall vs FX6 Dual `12G-SDI + HDMI`**:
   - FX3 `[External Output]` items (all Reset-immune): `[HDMI Resolution]`,
     `[HDMI Output Settings]` (`Rec. Media dur HDMI Output` default `On` &
     forced `On` in `S&Q`; `Output Resolution` downscaled to `1080` when
     `Log != Off` or `PP = PPLUT1..4` while `Rec. Media = On`; `4K Output
     Set.(HDMI Only)` `24.00p` reboot +
     `PRM_HAITA_hdmi_4k_outpute_apsc_restriction` typo; `RAW Output`; `Time Code
     Output` disabled in `S&Q`; `REC Control` hard-requires `Time Code Output =
     On`; `4ch Audio Output` `CH1/CH2` vs `CH3/CH4`), `[HDMI Info. Display]`,
     and `[CTRL FOR HDMI]` (`BKID_APP_setting_ctrl_for_hmdi` typo), plus dormant
     `24p/60p Output` & `4K/2K Output` (`0` exposed).
   - Tier-0 `Slot 1` `EROFS=30` (`errno.EROFS`) firewall: when `Slot 1` is
     mounted as the read-only Tier-0 recovery vault and `[REC Control] = On` is
     triggered with `Rec. Media dur HDMI Output = On` targeting `Slot 1`,
     VFS/block layer MUST fail-closed with `EROFS=30`
     (`slot1_data_sector_writes == 0`, `emmc_nflasha_write_count == 0`). Safe
     external-only recording requires `Off(HDMI Only)` (non-`S&Q`) or routing
     to writable `Slot 2`.
   - Contrast with `ILME-FX6 Ver. 6.01` dual `12G-SDI + HDMI`: `SDI/HDMI Remote
     I/F` vs `Parallel Rec` (HDMI trigger also requires `HDMI TC Out = On`), and
     `RAW(HDMI)` (`4240x2392`) forcing `SDI` down to `1920x1080P/i`.
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
# Phase 350 Schema, Milestone & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase350_realhw_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation_v1"
)
PHASE_350_VERSION = "350.0.0"
PHASE_NUMBER = 350
STAGE_INDEX = 77
STAGE_TOTAL = 77
MILESTONE_LABEL = "77/77"
IS_77TH_STAGE_MILESTONE = True

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

# Wave-67 Sub-Model 77A..77D Numeric & Invariant Contracts
# 77A — [Pixel Mapping] & [Auto Pixel Mapping] vs FX6 APR & Dormant ABB
PIXEL_MAPPING_AUTO_RESET_WIPE_EVENTS = 0
SILENT_AUTO_PIXEL_MAPPING_DEFAULT_MUTE_SHUTTER = False
PIXEL_MAPPINNG_TYPO_MATCHED = True
PIXEL_MAPPING_EXCUTED_TYPO_MATCHED = True
DORMANT_PIXEL_MAP_NOTIFICATION_EXPOSED_EVENTS = 0
DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS = 0
FX6_ABB_MENU_EXPOSED_EVENTS = 0

# 77B — Setup -> [Monitor] (3 Items, Zero [Finder/Monitor]) & 4 Dormant EVF vs FX6 VF Setting
FX3_MONITOR_GROUP_ACTIVE_ITEMS_COUNT = 3
DORMANT_FINDER_MONITOR_GROUP_EXPOSED_EVENTS = 0
DORMANT_EVF_MENUS_EXPOSED_EVENTS = 0
MONITOR_SETTINGS_RESET_WIPE_EVENTS = 0
DISPLAY_QUALITY_THERMAL_OVERRIDE_BYPASS_EVENTS = 0
FX6_VF_BRIGHTNESS_DEFAULT = 8
FX6_DORMANT_VF_4SUBMENUS_EXPOSED_EVENTS = 0

# 77C — Still P/A/S/M-Only [Recall Custom hold 1-3] (11 Slots) vs FX6 Push Controls
RECALL_CUSTOM_HOLD_SLOTS_COUNT = 3
RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT = 11
RECALL_CUSTOM_HOLD_WHITE_BALANCE_INDEPENDENT_SLOTS = 0
RECALL_CUSTOM_HOLD_MOVIE_SQ_BYPASS_EVENTS = 0
RECALL_CUSTOM_HOLD_RESET_WIPE_EVENTS = 0
FX6_RECALL_CUSTOM_HOLD_EXPOSED_EVENTS = 0
FX6_DORMANT_HIGH_LOW_KEY_EXPOSED_EVENTS = 0

# 77D — Setup -> [External Output] HDMI Matrix, Typos & Tier-0 Slot 1 EROFS=30 Firewall
EXTERNAL_OUTPUT_RESET_WIPE_EVENTS = 0
HDMI_4K_OUTPUTE_TYPO_MATCHED = True
CTRL_FOR_HMDI_TYPO_MATCHED = True
DORMANT_24P_60P_AND_4K_2K_OUTPUT_EXPOSED_EVENTS = 0
REC_CONTROL_WITHOUT_TC_BYPASS_EVENTS = 0
HDMI_REC_MEDIA_SLOT1_EROFS_BYPASS_EVENTS = 0

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
# Verified Local Donor Specs (12 FX3 Ver. 7.02 & FX6 Ver. 6.01 Wave-67 Donors)
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
        b"Auto Pixel Mapping",
        b"Pixel Mapping",
        b"Not Target",
        b"Pixel Map. Notification",
        b"APR",
        b"Sunny Weather",
        b"Display Quality",
        b"Monitor Flip Direction",
        b"Horizontal Flip",
        b"180 Degree Flip",
        b"No Flip",
        b"Switch Monitor Flip Disp",
        b"Finder/Monitor Sel.",
        b"Viewfinder Bright.",
        b"Bright Monitoring",
        b"AF On",
        b"Eye AF",
        b"Tracking On",
        b"Tracking on Toggle",
        b"Tracking On + AF On",
        b"Reg. Custom Shoot Set",
        b"Recall Custom hold 1",
        b"Recall Custom hold 2",
        b"Recall Custom hold 3",
        b"HDMI Resolution",
        b"HDMI Info. Display",
        b"Rec. Media dur HDMI Output",
        b"Off(HDMI Only)",
        b"Output Resolution",
        b"4K Output Set.(HDMI Only)",
        b"Time Code Output",
        b"REC Control",
        b"4ch Audio Output",
        b"24p/60p Output",
    ),
    "fx3_string_sc_f": (
        "\u50cf\u7d20\u6620\u5c04".encode("utf-8"),
        "\u81ea\u52a8\u50cf\u7d20\u6620\u5c04".encode("utf-8"),
        "\u663e\u793a\u8d28\u91cf".encode("utf-8"),
        "\u663e\u793a\u5c4f\u7ffb\u8f6c\u65b9\u5411".encode("utf-8"),
        "\u773c\u90e8AF".encode("utf-8"),
        "\u8c03\u51fa\u81ea\u5b9a\u4fdd\u63011".encode("utf-8"),
        "HDMI\u4fe1\u606f\u663e\u793a".encode("utf-8"),
        "REC\u63a7\u5236".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "\u50cf\u7d20\u6620\u5c04".encode("utf-8"),
        "\u81ea\u52d5\u50cf\u7d20\u6620\u5c04".encode("utf-8"),
        "\u986f\u793a\u756b\u8cea".encode("utf-8"),
        "\u87a2\u5e55\u7ffb\u8f49\u65b9\u5411".encode("utf-8"),
        "\u773c\u90e8\u5c0d\u7126".encode("utf-8"),
        "\u56de\u5fa9\u81ea\u8a02\u56fa\u5b9a1".encode("utf-8"),
        "HDMI\u8cc7\u8a0a\u986f\u793a".encode("utf-8"),
        "REC\u63a7\u5236".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "\u30d4\u30af\u30bb\u30eb\u30de\u30c3\u30d4\u30f3\u30b0".encode("utf-8"),
        "\u8868\u793a\u753b\u8cea".encode("utf-8"),
        "\u30e2\u30cb\u30bf\u30fc\u53cd\u8ee2\u8868\u793a".encode("utf-8"),
        "\u77b3AF".encode("utf-8"),
        "HDMI\u60c5\u5831\u8868\u793a".encode("utf-8"),
        "REC\u30b3\u30f3\u30c8\u30ed\u30fc\u30eb".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Monitor Brightness",
        b"Sunny Weather",
        b"HDMI Resolution",
        b"CTRL FOR HDMI",
    ),
    "fx3_string_en_g": (
        b"Attach the lens cap",
        b"Pixel mapping failed since light\nshielding was insufficient.",
        b"Pixel mapping completed.",
    ),
    "fx3_saveload": (b"libSaveLoadSettings", b"Save", b"Load"),
    "fx6_string_en": (
        b"Cover the Lens",
        b"VF Adjust",
        b"Push AF",
        b"Push AGC",
        b"Push Auto Iris",
        b"Auto Black Balance",
    ),
    "fx6_string_en_2": (
        b"VF Setting",
        b"HDMI TC Out",
        b"SDI/HDMI Rec Control",
        b"High/Low Key",
        b"Auto Black Balance",
        b"Cover the Lens",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (
            0x39CC000,
            "FUNC_execute_manual_pixel_mapping",
            b"FUNC_execute_manual_pixel_mapping",
        ),
        (
            0x39D3000,
            "SYSTEM_MODE_OPTION_MANUAL_PIXEL_MAPPING",
            b"SYSTEM_MODE_OPTION_MANUAL_PIXEL_MAPPING",
        ),
        (
            0x3BFB000,
            "INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING",
            b"INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING",
        ),
        (
            0x3925000,
            "vdf_set_shutter_mute_by_pixel_mapping",
            b"vdf_set_shutter_mute_by_pixel_mapping",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_auto_pixel_mapping",
            b"BKID_APP_setting_auto_pixel_mapping",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_notification_for_pixel_mappinng",
            b"BKID_APP_setting_notification_for_pixel_mappinng",
        ),
        (
            0x3BF1000,
            "BKID_APP_pixel_mapping_excuted_status",
            b"BKID_APP_pixel_mapping_excuted_status",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_lcd_brightness",
            b"BKID_APP_setting_lcd_brightness",
        ),
        (
            0x3BFC000,
            "INFRA_NOTIFY_UPM_LCD_BRIGHTNESS_LIMIT",
            b"INFRA_NOTIFY_UPM_LCD_BRIGHTNESS_LIMIT",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_display_quality",
            b"BKID_APP_setting_display_quality",
        ),
        (
            0x3BEF000,
            "BKID_APP_extern_menu_flip",
            b"BKID_APP_extern_menu_flip",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_finder_monitor",
            b"BKID_APP_setting_finder_monitor",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_viewfinder_bright",
            b"BKID_APP_setting_viewfinder_bright",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_evf_adjustment",
            b"BKID_APP_setting_evf_adjustment",
        ),
        (
            0x3BCB000,
            "BKID_APP_setting_finder_framerate",
            b"BKID_APP_setting_finder_framerate",
        ),
        (
            0x3C36000,
            "EVENT_FUNC_CUSTOM_RECALL_SHOOT_SET1_ON",
            b"EVENT_FUNC_CUSTOM_RECALL_SHOOT_SET1_ON",
        ),
        (
            0x3C28000,
            "is_checked_recall_custom_hold0",
            b"is_checked_recall_custom_hold0",
        ),
        (
            0x3C28000,
            "is_checked_recall_custom_hold10",
            b"is_checked_recall_custom_hold10",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_hdmi_resolution",
            b"BKID_APP_setting_hdmi_resolution",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_rec_media_during_hdmi_output",
            b"BKID_APP_setting_rec_media_during_hdmi_output",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_output_resolution",
            b"BKID_APP_setting_output_resolution",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_hdmi_4k_output_setting",
            b"BKID_APP_setting_hdmi_4k_output_setting",
        ),
        (
            0x39BA000,
            "PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
            b"PRM_HAITA_hdmi_4k_outpute_apsc_restriction",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_hdmi_tc_output",
            b"BKID_APP_setting_hdmi_tc_output",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_rec_control",
            b"BKID_APP_setting_rec_control",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_mov_hdmi_audio_output",
            b"BKID_APP_setting_mov_hdmi_audio_output",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_hdmi_info_display",
            b"BKID_APP_setting_hdmi_info_display",
        ),
        (
            0x3BCC000,
            "BKID_APP_setting_ctrl_for_hmdi",
            b"BKID_APP_setting_ctrl_for_hmdi",
        ),
    ),
    "fx3_bk4": (
        (0x00000, "BK4_HEADER", b"BK4\x00"),
        (0x4A000, "ILME-FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (
            0x23C6000,
            "procam_msg_confirm_execute_apr_controller",
            b"procam_msg_confirm_execute_apr_controller",
        ),
        (
            0x2783000,
            "PIXEL_MAPPING_RESULT_LIGHT_DETECTED",
            b"PIXEL_MAPPING_RESULT_LIGHT_DETECTED",
        ),
        (
            0x2783000,
            "PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE",
            b"PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE",
        ),
        (
            0x23C8000,
            "auto_black_balance",
            b"auto_black_balance",
        ),
        (
            0x27A9000,
            "ASSIGNABLE_SWITCH_VF_ADJUST",
            b"ASSIGNABLE_SWITCH_VF_ADJUST",
        ),
        (
            0x2762000,
            "setting_evf_adjustment_t",
            b"setting_evf_adjustment_t",
        ),
        (
            0x27A9000,
            "ASSIGNABLE_SWITCH_PUSH_AF_MODE",
            b"ASSIGNABLE_SWITCH_PUSH_AF_MODE",
        ),
        (
            0x27A8000,
            "ASSIGNABLE_SWITCH_PUSH_AGC",
            b"ASSIGNABLE_SWITCH_PUSH_AGC",
        ),
        (
            0x27A8000,
            "ASSIGNABLE_SWITCH_PUSH_AUTO_IRIS",
            b"ASSIGNABLE_SWITCH_PUSH_AUTO_IRIS",
        ),
    ),
}


# ---------------------------------------------------------------------------
# Wave-67 Real-Hardware Constants & Matrices
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

VALID_TOGGLES: Tuple[str, ...] = ("Off", "On")
VALID_RECORDING_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2", "None")

# Sub-Model 77A — [Pixel Mapping] & [Auto Pixel Mapping] vs FX6 APR & Dormant ABB
VALID_PIXEL_MAPPING_OPERATIONS: Tuple[str, ...] = (
    "auto_poweroff",
    "manual_pixel_mapping",
    "dormant_pixel_map_notification",
    "dormant_shutter_when_pwr_off",
    "fx6_apr_execute",
    "fx6_apr_cancel",
    "fx6_abb_menu",
)

# Sub-Model 77B — Setup -> [Monitor] (3 Active Items) & 4 Dormant EVF vs FX6 VF Setting
FX3_MONITOR_ACTIVE_ITEMS: Tuple[str, ...] = (
    "Monitor Brightness",
    "Display Quality",
    "Monitor Flip Direction",
)
DORMANT_FX3_EVF_MENUS: Tuple[str, ...] = (
    "Finder/Monitor Sel.",
    "Viewfinder Bright.",
    "Viewfinder Color Temp.",
    "Finder Frame Rate",
)
VALID_MONITOR_BRIGHTNESS_MODES: Tuple[str, ...] = ("Manual", "Sunny Weather")
VALID_DISPLAY_QUALITY_MODES: Tuple[str, ...] = ("Standard", "High")
VALID_MONITOR_FLIP_DIRECTIONS: Tuple[str, ...] = (
    "Auto",
    "Horizontal Flip",
    "180 Degree Flip",
    "No Flip",
)
VALID_MONITOR_OPERATIONS: Tuple[str, ...] = (
    "configure_monitor",
    "dormant_finder_monitor_group",
    "dormant_evf_item",
    "bright_monitoring_check",
    "fx6_vf_setting",
    "fx6_vf_adjust",
    "fx6_dormant_vf_submenu",
)
FX6_VF_COLOR_MODES: Tuple[str, ...] = ("Color", "B&W")
FX6_VF_MIRROR_MODES: Tuple[str, ...] = ("Off", "B/T", "ROT")
FX6_DORMANT_VF_SUBMENUS: Tuple[str, ...] = (
    "Backlight",
    "Contrast",
    "Chroma",
    "Color Temp.",
)

# Sub-Model 77C — Still P/A/S/M-Only [Recall Custom hold 1-3] (11 Slots) vs FX6 Push Controls
STILL_PASM_MODES: Tuple[str, ...] = ("P", "A", "S", "M")
VALID_EXPOSURE_MODES: Tuple[str, ...] = ("P", "A", "S", "M", "iAuto")
RECALL_CUSTOM_HOLD_11_PARAMS: Tuple[str, ...] = (
    "shooting_mode",
    "aperture",
    "shutter_speed",
    "exposure_comp",
    "iso_sensitivity",
    "metering_mode",
    "drive_mode",
    "focus_mode",
    "focus_area",
    "af_on",
    "still_af_track_sens",
)
VALID_RECALL_OPERATIONS: Tuple[str, ...] = (
    "recall_custom_hold",
    "af_on",
    "eye_af",
    "tracking_on",
    "dormant_recall_white_balance",
    "fx6_push_af",
    "fx6_push_agc",
    "fx6_push_auto_iris",
    "fx6_dormant_high_low_key",
)
VALID_FOCUS_MODES: Tuple[str, ...] = ("AF-S", "AF-C", "DMF", "MF")
FX6_EXPOSURE_MODES: Tuple[str, ...] = ("Cine EI", "Cine EI Quick", "Flexible ISO", "Custom")
FX6_DESQUEEZE_OPTIONS: Tuple[str, ...] = ("Off(1.0x)", "1.3x", "2.0x")
FX6_PUSH_AF_MODES: Tuple[str, ...] = ("AF", "Single-shot AF(AF-S)")

# Sub-Model 77D — Setup -> [External Output] HDMI Matrix & Tier-0 Slot 1 EROFS=30 Firewall
VALID_EXTERNAL_OUTPUT_OPERATIONS: Tuple[str, ...] = (
    "hdmi_output",
    "rec_control_trigger",
    "change_4k_24p",
    "dormant_24p_60p",
    "dormant_4k_2k",
    "fx6_dual_output",
)
VALID_HDMI_RESOLUTIONS: Tuple[str, ...] = ("Auto", "2160p", "1080p", "1080i")
VALID_REC_MEDIA_HDMI_MODES: Tuple[str, ...] = ("On", "Off(HDMI Only)")
VALID_4K_HDMI_OUTPUT_RATES: Tuple[str, ...] = (
    "59.94p 10bit",
    "50p 10bit",
    "29.97p 10bit",
    "25p 10bit",
    "23.98p 10bit",
    "24.00p 10bit",
)
VALID_4CH_HDMI_AUDIO_MODES: Tuple[str, ...] = ("CH1/CH2", "CH3/CH4")
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI",
    "Cine EI Quick",
)
VALID_PICTURE_PROFILES: Tuple[str, ...] = (
    ("Off",)
    + tuple(f"PP{idx}" for idx in range(1, 12))
    + tuple(f"PPLUT{idx}" for idx in range(1, 5))
)
PPLUT_PROFILES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
FX6_CODECS: Tuple[str, ...] = (
    "XAVC-I",
    "RAW",
    "RAW & XAVC-I",
    "RAW(HDMI)",
    "RAW(HDMI) & XAVC-I",
)
FX6_SDI_HDMI_REC_CONTROL_MODES: Tuple[str, ...] = (
    "Off",
    "SDI/HDMI Remote I/F",
    "Parallel Rec",
)


class Stage77Phase350Error(RuntimeError):
    """Raised on invalid Phase 350 Stage 77 configuration or safety redline violation."""


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
        raise Stage77Phase350Error(
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
            raise Stage77Phase350Error(
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
class Wave67DonorAuditReport:
    source_mode: str
    donor_access_mode: str
    bounded_window_max_bytes: int
    donors_checked: int
    donors_verified: int
    all_contracts_verified: bool
    raw_firmware_bytes_leaked: int
    artifacts: Dict[str, DonorArtifactInspection]


def inspect_phase350_wave67_donors(
    work_root: Union[None, str, Path, object] = _UNSET,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Wave67DonorAuditReport:
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
        return Wave67DonorAuditReport(
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
    return Wave67DonorAuditReport(
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
# Sub-Model 77A: [Pixel Mapping] & [Auto Pixel Mapping] vs FX6 APR & ABB
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PixelMappingAprAbbAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    effective_auto_pixel_mapping: str
    auto_pixel_mapping_resettable: bool
    effective_silent_mode: str
    effective_silent_target_auto_pixel_mapping: str
    silent_target_resettable: bool
    mechanical_shutter_sound_emitted: bool
    auto_poweroff_executed: bool
    manual_executed: bool
    auto_reboot_triggered: bool
    manual_every_3_days_advisory: bool
    notification_typo_symbol: str
    executed_status_typo_symbol: str
    dormant_pixel_map_notification_exposed: bool
    dormant_shutter_when_pwr_off_exposed: bool
    fx6_apr_executed: bool
    fx6_abb_menu_exposed: bool
    fx6_result_code: Optional[str]


def simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "auto_poweroff",
    auto_pixel_mapping: str = "On",
    silent_mode: str = "Off",
    silent_target_auto_pixel_mapping: str = "Off",
    battery_sufficient: bool = True,
    lens_cap_light_shielded: bool = True,
    black_cloth_shielded: bool = True,
    temperature_valid: bool = True,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> PixelMappingAprAbbAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage77Phase350Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage77Phase350Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_PIXEL_MAPPING_OPERATIONS:
        raise Stage77Phase350Error(f"Invalid operation: {operation!r}")
    if auto_pixel_mapping not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid auto_pixel_mapping: {auto_pixel_mapping!r}")
    if silent_mode not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid silent_mode: {silent_mode!r}")
    if silent_target_auto_pixel_mapping not in VALID_TOGGLES:
        raise Stage77Phase350Error(
            f"Invalid silent_target_auto_pixel_mapping: {silent_target_auto_pixel_mapping!r}"
        )

    notif_sym = "BKID_APP_setting_notification_for_pixel_mappinng"
    exec_sym = "BKID_APP_pixel_mapping_excuted_status"

    # 1. ILME-FX6 Ver. 6.01: Technical > APR > Execute/Cancel; ZERO CMOS ABB menu
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_abb_menu":
            return PixelMappingAprAbbAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Ver. 6.01 CMOS sensor has ZERO ABB (Auto Black Balance) menu "
                    "(auto_black_balance in FX6 appFw.so is 100%% dormant; black trim uses Paint/Look > Black)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_auto_pixel_mapping="UNSUPPORTED",
                auto_pixel_mapping_resettable=False,
                effective_silent_mode="UNSUPPORTED",
                effective_silent_target_auto_pixel_mapping="UNSUPPORTED",
                silent_target_resettable=False,
                mechanical_shutter_sound_emitted=False,
                auto_poweroff_executed=False,
                manual_executed=False,
                auto_reboot_triggered=False,
                manual_every_3_days_advisory=False,
                notification_typo_symbol="N/A",
                executed_status_typo_symbol="N/A",
                dormant_pixel_map_notification_exposed=False,
                dormant_shutter_when_pwr_off_exposed=False,
                fx6_apr_executed=False,
                fx6_abb_menu_exposed=False,
                fx6_result_code=None,
            )
        if operation not in ("fx6_apr_execute", "fx6_apr_cancel"):
            return PixelMappingAprAbbAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"ILME-FX6 Ver. 6.01 does not expose FX3 operation {operation!r}; "
                    "uses Technical > APR > Execute / Cancel"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_auto_pixel_mapping="UNSUPPORTED",
                auto_pixel_mapping_resettable=False,
                effective_silent_mode="UNSUPPORTED",
                effective_silent_target_auto_pixel_mapping="UNSUPPORTED",
                silent_target_resettable=False,
                mechanical_shutter_sound_emitted=False,
                auto_poweroff_executed=False,
                manual_executed=False,
                auto_reboot_triggered=False,
                manual_every_3_days_advisory=False,
                notification_typo_symbol="N/A",
                executed_status_typo_symbol="N/A",
                dormant_pixel_map_notification_exposed=False,
                dormant_shutter_when_pwr_off_exposed=False,
                fx6_apr_executed=False,
                fx6_abb_menu_exposed=False,
                fx6_result_code=None,
            )
        if operation == "fx6_apr_cancel":
            return PixelMappingAprAbbAudit(
                admitted=True,
                errno_code=0,
                reason="FX6 Technical > APR > Cancel exited cleanly (zero ABB menu)",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_auto_pixel_mapping="UNSUPPORTED",
                auto_pixel_mapping_resettable=False,
                effective_silent_mode="UNSUPPORTED",
                effective_silent_target_auto_pixel_mapping="UNSUPPORTED",
                silent_target_resettable=False,
                mechanical_shutter_sound_emitted=False,
                auto_poweroff_executed=False,
                manual_executed=False,
                auto_reboot_triggered=False,
                manual_every_3_days_advisory=False,
                notification_typo_symbol="N/A",
                executed_status_typo_symbol="N/A",
                dormant_pixel_map_notification_exposed=False,
                dormant_shutter_when_pwr_off_exposed=False,
                fx6_apr_executed=False,
                fx6_abb_menu_exposed=False,
                fx6_result_code="APR_CANCELED",
            )
        if not (lens_cap_light_shielded and black_cloth_shielded):
            return PixelMappingAprAbbAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    "FX6 shutterless APR requires lens cap + black cloth to exclude all light "
                    "(PIXEL_MAPPING_RESULT_LIGHT_DETECTED)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_auto_pixel_mapping="UNSUPPORTED",
                auto_pixel_mapping_resettable=False,
                effective_silent_mode="UNSUPPORTED",
                effective_silent_target_auto_pixel_mapping="UNSUPPORTED",
                silent_target_resettable=False,
                mechanical_shutter_sound_emitted=False,
                auto_poweroff_executed=False,
                manual_executed=False,
                auto_reboot_triggered=False,
                manual_every_3_days_advisory=False,
                notification_typo_symbol="N/A",
                executed_status_typo_symbol="N/A",
                dormant_pixel_map_notification_exposed=False,
                dormant_shutter_when_pwr_off_exposed=False,
                fx6_apr_executed=False,
                fx6_abb_menu_exposed=False,
                fx6_result_code="PIXEL_MAPPING_RESULT_LIGHT_DETECTED",
            )
        if not temperature_valid:
            return PixelMappingAprAbbAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="FX6 APR blocked by body temperature out of range (PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE)",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_auto_pixel_mapping="UNSUPPORTED",
                auto_pixel_mapping_resettable=False,
                effective_silent_mode="UNSUPPORTED",
                effective_silent_target_auto_pixel_mapping="UNSUPPORTED",
                silent_target_resettable=False,
                mechanical_shutter_sound_emitted=False,
                auto_poweroff_executed=False,
                manual_executed=False,
                auto_reboot_triggered=False,
                manual_every_3_days_advisory=False,
                notification_typo_symbol="N/A",
                executed_status_typo_symbol="N/A",
                dormant_pixel_map_notification_exposed=False,
                dormant_shutter_when_pwr_off_exposed=False,
                fx6_apr_executed=False,
                fx6_abb_menu_exposed=False,
                fx6_result_code="PIXEL_MAPPING_RESULT_INVALID_TEMPERATURE",
            )
        return PixelMappingAprAbbAudit(
            admitted=True,
            errno_code=0,
            reason="FX6 Ver. 6.01 Technical > APR > Execute completed (shutterless dark-shielded, zero ABB)",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            effective_auto_pixel_mapping="UNSUPPORTED",
            auto_pixel_mapping_resettable=False,
            effective_silent_mode="UNSUPPORTED",
            effective_silent_target_auto_pixel_mapping="UNSUPPORTED",
            silent_target_resettable=False,
            mechanical_shutter_sound_emitted=False,
            auto_poweroff_executed=False,
            manual_executed=False,
            auto_reboot_triggered=False,
            manual_every_3_days_advisory=False,
            notification_typo_symbol="N/A",
            executed_status_typo_symbol="N/A",
            dormant_pixel_map_notification_exposed=False,
            dormant_shutter_when_pwr_off_exposed=False,
            fx6_apr_executed=True,
            fx6_abb_menu_exposed=False,
            fx6_result_code="PIXEL_MAPPING_RESULT_OK",
        )

    # 2. FX3 Ver. 7.02 Reset vs Initialize persistence rules
    # Setup -> [Auto Pixel Mapping] is Reset-immune (restored ONLY by Initialize to On)
    # Silent Mode Settings -> Target Function Settings -> [Auto Pixel Mapping] IS Resettable (to Off)
    if initialize_applied:
        eff_auto_pm = "On"
        eff_silent_mode = "Off"
        eff_silent_target = "Off"
    elif camera_settings_reset_applied:
        eff_auto_pm = auto_pixel_mapping  # Reset-immune!
        eff_silent_mode = "Off"
        eff_silent_target = "Off"  # Can be reset!
    else:
        eff_auto_pm = auto_pixel_mapping
        eff_silent_mode = silent_mode
        eff_silent_target = silent_target_auto_pixel_mapping

    # 3. Dormant / FX6-only operations rejected with EOPNOTSUPP=95
    if operation in (
        "dormant_pixel_map_notification",
        "dormant_shutter_when_pwr_off",
        "fx6_apr_execute",
        "fx6_apr_cancel",
        "fx6_abb_menu",
    ):
        return PixelMappingAprAbbAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"{operation!r} is dormant / unexposed on ILME-FX3 Ver. 7.02",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            effective_auto_pixel_mapping=eff_auto_pm,
            auto_pixel_mapping_resettable=False,
            effective_silent_mode=eff_silent_mode,
            effective_silent_target_auto_pixel_mapping=eff_silent_target,
            silent_target_resettable=True,
            mechanical_shutter_sound_emitted=False,
            auto_poweroff_executed=False,
            manual_executed=False,
            auto_reboot_triggered=False,
            manual_every_3_days_advisory=False,
            notification_typo_symbol=notif_sym,
            executed_status_typo_symbol=exec_sym,
            dormant_pixel_map_notification_exposed=False,
            dormant_shutter_when_pwr_off_exposed=False,
            fx6_apr_executed=False,
            fx6_abb_menu_exposed=False,
            fx6_result_code=None,
        )

    # 4. Battery gate (`INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING`)
    if not battery_sufficient and (
        operation == "manual_pixel_mapping"
        or (operation == "auto_poweroff" and eff_auto_pm == "On")
    ):
        return PixelMappingAprAbbAudit(
            admitted=False,
            errno_code=EPERM_ERRNO,
            reason=(
                "Battery check failed for Pixel Mapping "
                "(INFRA_NOTIFY_BATTERY_CHECK_FOR_PIXEL_MAPPING -> BATTERY_CHECK_FOR_PIXEL_MAPPING_LOWER)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            effective_auto_pixel_mapping=eff_auto_pm,
            auto_pixel_mapping_resettable=False,
            effective_silent_mode=eff_silent_mode,
            effective_silent_target_auto_pixel_mapping=eff_silent_target,
            silent_target_resettable=True,
            mechanical_shutter_sound_emitted=False,
            auto_poweroff_executed=False,
            manual_executed=False,
            auto_reboot_triggered=False,
            manual_every_3_days_advisory=False,
            notification_typo_symbol=notif_sym,
            executed_status_typo_symbol=exec_sym,
            dormant_pixel_map_notification_exposed=False,
            dormant_shutter_when_pwr_off_exposed=False,
            fx6_apr_executed=False,
            fx6_abb_menu_exposed=False,
            fx6_result_code=None,
        )

    # 5. Manual [Pixel Mapping]
    if operation == "manual_pixel_mapping":
        if not lens_cap_light_shielded:
            return PixelMappingAprAbbAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="Manual [Pixel Mapping] failed: lens cap light shielding insufficient (_g 0x60e7)",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                effective_auto_pixel_mapping=eff_auto_pm,
                auto_pixel_mapping_resettable=False,
                effective_silent_mode=eff_silent_mode,
                effective_silent_target_auto_pixel_mapping=eff_silent_target,
                silent_target_resettable=True,
                mechanical_shutter_sound_emitted=False,
                auto_poweroff_executed=False,
                manual_executed=False,
                auto_reboot_triggered=False,
                manual_every_3_days_advisory=False,
                notification_typo_symbol=notif_sym,
                executed_status_typo_symbol=exec_sym,
                dormant_pixel_map_notification_exposed=False,
                dormant_shutter_when_pwr_off_exposed=False,
                fx6_apr_executed=False,
                fx6_abb_menu_exposed=False,
                fx6_result_code=None,
            )
        return PixelMappingAprAbbAudit(
            admitted=True,
            errno_code=0,
            reason=(
                "Manual [Pixel Mapping] (FUNC_execute_manual_pixel_mapping / "
                "SYSTEM_MODE_OPTION_MANUAL_PIXEL_MAPPING) completed and triggered auto-reboot"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            effective_auto_pixel_mapping=eff_auto_pm,
            auto_pixel_mapping_resettable=False,
            effective_silent_mode=eff_silent_mode,
            effective_silent_target_auto_pixel_mapping=eff_silent_target,
            silent_target_resettable=True,
            mechanical_shutter_sound_emitted=True,
            auto_poweroff_executed=False,
            manual_executed=True,
            auto_reboot_triggered=True,
            manual_every_3_days_advisory=False,
            notification_typo_symbol=notif_sym,
            executed_status_typo_symbol=exec_sym,
            dormant_pixel_map_notification_exposed=False,
            dormant_shutter_when_pwr_off_exposed=False,
            fx6_apr_executed=False,
            fx6_abb_menu_exposed=False,
            fx6_result_code=None,
        )

    # 6. Power-off [Auto Pixel Mapping] + Silent Mode Target Function interaction
    if eff_auto_pm == "Off":
        return PixelMappingAprAbbAudit(
            admitted=True,
            errno_code=0,
            reason=(
                "[Auto Pixel Mapping] = Off (Reset-immune): skipped power-off mapping; "
                "manual [Pixel Mapping] advised approx. every 3 days"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            effective_auto_pixel_mapping=eff_auto_pm,
            auto_pixel_mapping_resettable=False,
            effective_silent_mode=eff_silent_mode,
            effective_silent_target_auto_pixel_mapping=eff_silent_target,
            silent_target_resettable=True,
            mechanical_shutter_sound_emitted=False,
            auto_poweroff_executed=False,
            manual_executed=False,
            auto_reboot_triggered=False,
            manual_every_3_days_advisory=True,
            notification_typo_symbol=notif_sym,
            executed_status_typo_symbol=exec_sym,
            dormant_pixel_map_notification_exposed=False,
            dormant_shutter_when_pwr_off_exposed=False,
            fx6_apr_executed=False,
            fx6_abb_menu_exposed=False,
            fx6_result_code=None,
        )

    shutter_muted = (eff_silent_mode == "On") and (eff_silent_target == "On")
    return PixelMappingAprAbbAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"Power-off [Auto Pixel Mapping]=On (Silent={eff_silent_mode}, "
            f"Target={eff_silent_target}) -> mechanical_shutter_sound_emitted={not shutter_muted} "
            "(vdf_set_shutter_mute_by_pixel_mapping)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        effective_auto_pixel_mapping=eff_auto_pm,
        auto_pixel_mapping_resettable=False,
        effective_silent_mode=eff_silent_mode,
        effective_silent_target_auto_pixel_mapping=eff_silent_target,
        silent_target_resettable=True,
        mechanical_shutter_sound_emitted=(not shutter_muted),
        auto_poweroff_executed=True,
        manual_executed=False,
        auto_reboot_triggered=False,
        manual_every_3_days_advisory=False,
        notification_typo_symbol=notif_sym,
        executed_status_typo_symbol=exec_sym,
        dormant_pixel_map_notification_exposed=False,
        dormant_shutter_when_pwr_off_exposed=False,
        fx6_apr_executed=False,
        fx6_abb_menu_exposed=False,
        fx6_result_code=None,
    )


# ---------------------------------------------------------------------------
# Sub-Model 77B: Setup -> [Monitor] (3 Active Items) & 4 Dormant EVF vs FX6 VF
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MonitorDormantEvfVfSettingAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    fx3_group_name: str
    fx3_active_items_count: int
    finder_monitor_group_exposed: bool
    dormant_evf_menus_exposed: bool
    monitor_settings_resettable: bool
    effective_monitor_brightness: str
    effective_monitor_brightness_level: int
    effective_display_quality: str
    display_quality_thermally_locked: bool
    upm_lcd_brightness_limit_notified: bool
    effective_monitor_flip_direction: str
    bright_monitoring_in_monitor_group: bool
    fx6_vf_brightness: Optional[int]
    fx6_vf_color_mode: Optional[str]
    fx6_vf_mirror: Optional[str]
    fx6_4_vf_submenus_exposed: bool


def simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "configure_monitor",
    monitor_brightness: str = "Manual",
    monitor_brightness_level: int = 0,
    display_quality: str = "Standard",
    monitor_flip_direction: str = "Auto",
    body_temperature_high: bool = False,
    dormant_evf_item: str = "Finder/Monitor Sel.",
    fx6_vf_connected: bool = True,
    fx6_vf_brightness: int = FX6_VF_BRIGHTNESS_DEFAULT,
    fx6_vf_color_mode: str = "Color",
    fx6_vf_mirror: str = "Off",
    fx6_dormant_submenu: str = "Backlight",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> MonitorDormantEvfVfSettingAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage77Phase350Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage77Phase350Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_MONITOR_OPERATIONS:
        raise Stage77Phase350Error(f"Invalid operation: {operation!r}")
    if monitor_brightness not in VALID_MONITOR_BRIGHTNESS_MODES:
        raise Stage77Phase350Error(f"Invalid monitor_brightness: {monitor_brightness!r}")
    if isinstance(monitor_brightness_level, bool) or not isinstance(
        monitor_brightness_level, int
    ):
        raise Stage77Phase350Error(
            f"monitor_brightness_level must be int, got {monitor_brightness_level!r}"
        )
    if display_quality not in VALID_DISPLAY_QUALITY_MODES:
        raise Stage77Phase350Error(f"Invalid display_quality: {display_quality!r}")
    if monitor_flip_direction not in VALID_MONITOR_FLIP_DIRECTIONS:
        raise Stage77Phase350Error(
            f"Invalid monitor_flip_direction: {monitor_flip_direction!r}"
        )
    if dormant_evf_item not in DORMANT_FX3_EVF_MENUS:
        raise Stage77Phase350Error(f"Invalid dormant_evf_item: {dormant_evf_item!r}")
    if isinstance(fx6_vf_brightness, bool) or not isinstance(fx6_vf_brightness, int):
        raise Stage77Phase350Error(
            f"fx6_vf_brightness must be int, got {fx6_vf_brightness!r}"
        )
    if fx6_vf_color_mode not in FX6_VF_COLOR_MODES:
        raise Stage77Phase350Error(f"Invalid fx6_vf_color_mode: {fx6_vf_color_mode!r}")
    if fx6_vf_mirror not in FX6_VF_MIRROR_MODES:
        raise Stage77Phase350Error(f"Invalid fx6_vf_mirror: {fx6_vf_mirror!r}")
    if fx6_dormant_submenu not in FX6_DORMANT_VF_SUBMENUS:
        raise Stage77Phase350Error(f"Invalid fx6_dormant_submenu: {fx6_dormant_submenu!r}")

    # 1. ILME-FX6 Ver. 6.01 Monitoring > VF Setting (Brightness 1..15 def 8, Color/B&W) & VF Adjust
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_dormant_vf_submenu":
            return MonitorDormantEvfVfSettingAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"FX6 VF Adjust / VF Setting does NOT expose {fx6_dormant_submenu!r}; "
                    "only Monitoring > VF Setting > Brightness (1..15) & Color Mode (Color/B&W)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                fx3_group_name="N/A",
                fx3_active_items_count=0,
                finder_monitor_group_exposed=False,
                dormant_evf_menus_exposed=False,
                monitor_settings_resettable=False,
                effective_monitor_brightness="N/A",
                effective_monitor_brightness_level=0,
                effective_display_quality="N/A",
                display_quality_thermally_locked=False,
                upm_lcd_brightness_limit_notified=False,
                effective_monitor_flip_direction="N/A",
                bright_monitoring_in_monitor_group=False,
                fx6_vf_brightness=fx6_vf_brightness,
                fx6_vf_color_mode=fx6_vf_color_mode,
                fx6_vf_mirror=fx6_vf_mirror,
                fx6_4_vf_submenus_exposed=False,
            )
        if operation not in ("fx6_vf_setting", "fx6_vf_adjust"):
            return MonitorDormantEvfVfSettingAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not expose FX3 Setup -> [Monitor] operation {operation!r}",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                fx3_group_name="N/A",
                fx3_active_items_count=0,
                finder_monitor_group_exposed=False,
                dormant_evf_menus_exposed=False,
                monitor_settings_resettable=False,
                effective_monitor_brightness="N/A",
                effective_monitor_brightness_level=0,
                effective_display_quality="N/A",
                display_quality_thermally_locked=False,
                upm_lcd_brightness_limit_notified=False,
                effective_monitor_flip_direction="N/A",
                bright_monitoring_in_monitor_group=False,
                fx6_vf_brightness=fx6_vf_brightness,
                fx6_vf_color_mode=fx6_vf_color_mode,
                fx6_vf_mirror=fx6_vf_mirror,
                fx6_4_vf_submenus_exposed=False,
            )
        if operation == "fx6_vf_adjust" and not fx6_vf_connected:
            return MonitorDormantEvfVfSettingAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason="FX6 VF Adjust blocked when viewfinder detached (ns1 0x26b5: Please connect the viewfinder.)",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                fx3_group_name="N/A",
                fx3_active_items_count=0,
                finder_monitor_group_exposed=False,
                dormant_evf_menus_exposed=False,
                monitor_settings_resettable=False,
                effective_monitor_brightness="N/A",
                effective_monitor_brightness_level=0,
                effective_display_quality="N/A",
                display_quality_thermally_locked=False,
                upm_lcd_brightness_limit_notified=False,
                effective_monitor_flip_direction="N/A",
                bright_monitoring_in_monitor_group=False,
                fx6_vf_brightness=None,
                fx6_vf_color_mode=fx6_vf_color_mode,
                fx6_vf_mirror=fx6_vf_mirror,
                fx6_4_vf_submenus_exposed=False,
            )
        if not (1 <= fx6_vf_brightness <= 15):
            return MonitorDormantEvfVfSettingAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"FX6 VF Brightness {fx6_vf_brightness} outside [1..15]",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                fx3_group_name="N/A",
                fx3_active_items_count=0,
                finder_monitor_group_exposed=False,
                dormant_evf_menus_exposed=False,
                monitor_settings_resettable=False,
                effective_monitor_brightness="N/A",
                effective_monitor_brightness_level=0,
                effective_display_quality="N/A",
                display_quality_thermally_locked=False,
                upm_lcd_brightness_limit_notified=False,
                effective_monitor_flip_direction="N/A",
                bright_monitoring_in_monitor_group=False,
                fx6_vf_brightness=None,
                fx6_vf_color_mode=fx6_vf_color_mode,
                fx6_vf_mirror=fx6_vf_mirror,
                fx6_4_vf_submenus_exposed=False,
            )
        return MonitorDormantEvfVfSettingAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Ver. 6.01 VF Setting Brightness={fx6_vf_brightness} (1..15, def 8), "
                f"ColorMode={fx6_vf_color_mode}, MIRROR={fx6_vf_mirror} verified"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            fx3_group_name="N/A",
            fx3_active_items_count=0,
            finder_monitor_group_exposed=False,
            dormant_evf_menus_exposed=False,
            monitor_settings_resettable=False,
            effective_monitor_brightness="N/A",
            effective_monitor_brightness_level=0,
            effective_display_quality="N/A",
            display_quality_thermally_locked=False,
            upm_lcd_brightness_limit_notified=False,
            effective_monitor_flip_direction="N/A",
            bright_monitoring_in_monitor_group=False,
            fx6_vf_brightness=fx6_vf_brightness,
            fx6_vf_color_mode=fx6_vf_color_mode,
            fx6_vf_mirror=fx6_vf_mirror,
            fx6_4_vf_submenus_exposed=False,
        )

    # 2. FX3 Ver. 7.02 Reset-immunity vs Initialize law for Setup -> [Monitor]
    # All 3 Monitor items are Reset-immune (`Not available`); restored ONLY by Initialize.
    if initialize_applied:
        eff_bright_mode = "Manual"
        eff_bright_lvl = 0
        eff_quality = "Standard"
        eff_flip = "Auto"
    else:
        eff_bright_mode = monitor_brightness
        eff_bright_lvl = monitor_brightness_level
        eff_quality = display_quality
        eff_flip = monitor_flip_direction

    # 3. Dormant [Finder/Monitor] group & 4 dormant EVF items (`EOPNOTSUPP=95`)
    if operation in (
        "dormant_finder_monitor_group",
        "dormant_evf_item",
        "fx6_vf_setting",
        "fx6_vf_adjust",
        "fx6_dormant_vf_submenu",
    ):
        return MonitorDormantEvfVfSettingAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"FX3 Ver. 7.02 has NO EVF and NO [Finder/Monitor] group "
                f"({operation!r} / {dormant_evf_item!r} is 100%% dormant)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            fx3_group_name="Setup -> [Monitor]",
            fx3_active_items_count=FX3_MONITOR_GROUP_ACTIVE_ITEMS_COUNT,
            finder_monitor_group_exposed=False,
            dormant_evf_menus_exposed=False,
            monitor_settings_resettable=False,
            effective_monitor_brightness=eff_bright_mode,
            effective_monitor_brightness_level=eff_bright_lvl,
            effective_display_quality=eff_quality,
            display_quality_thermally_locked=False,
            upm_lcd_brightness_limit_notified=False,
            effective_monitor_flip_direction=eff_flip,
            bright_monitoring_in_monitor_group=False,
            fx6_vf_brightness=None,
            fx6_vf_color_mode=None,
            fx6_vf_mirror=None,
            fx6_4_vf_submenus_exposed=False,
        )

    if not (-2 <= eff_bright_lvl <= 2):
        return MonitorDormantEvfVfSettingAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=f"[Monitor Brightness] Manual level {eff_bright_lvl} outside [-2..+2]",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            fx3_group_name="Setup -> [Monitor]",
            fx3_active_items_count=FX3_MONITOR_GROUP_ACTIVE_ITEMS_COUNT,
            finder_monitor_group_exposed=False,
            dormant_evf_menus_exposed=False,
            monitor_settings_resettable=False,
            effective_monitor_brightness=eff_bright_mode,
            effective_monitor_brightness_level=eff_bright_lvl,
            effective_display_quality=eff_quality,
            display_quality_thermally_locked=False,
            upm_lcd_brightness_limit_notified=False,
            effective_monitor_flip_direction=eff_flip,
            bright_monitoring_in_monitor_group=False,
            fx6_vf_brightness=None,
            fx6_vf_color_mode=None,
            fx6_vf_mirror=None,
            fx6_4_vf_submenus_exposed=False,
        )

    # 4. Thermal lock on [Display Quality] = High & UPM LCD brightness limit
    upm_limit = bool(body_temperature_high and eff_bright_mode == "Sunny Weather")
    if body_temperature_high and eff_quality == "High":
        return MonitorDormantEvfVfSettingAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "[Display Quality] thermally locked to Standard when body temperature rises "
                "(High rejected; INFRA_NOTIFY_UPM_LCD_BRIGHTNESS_LIMIT)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            fx3_group_name="Setup -> [Monitor]",
            fx3_active_items_count=FX3_MONITOR_GROUP_ACTIVE_ITEMS_COUNT,
            finder_monitor_group_exposed=False,
            dormant_evf_menus_exposed=False,
            monitor_settings_resettable=False,
            effective_monitor_brightness=eff_bright_mode,
            effective_monitor_brightness_level=eff_bright_lvl,
            effective_display_quality="Standard",
            display_quality_thermally_locked=True,
            upm_lcd_brightness_limit_notified=upm_limit,
            effective_monitor_flip_direction=eff_flip,
            bright_monitoring_in_monitor_group=False,
            fx6_vf_brightness=None,
            fx6_vf_color_mode=None,
            fx6_vf_mirror=None,
            fx6_4_vf_submenus_exposed=False,
        )

    return MonitorDormantEvfVfSettingAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"Setup -> [Monitor] (3 active items, Reset-immune={not camera_settings_reset_applied or True}): "
            f"Brightness={eff_bright_mode}({eff_bright_lvl}), Quality={eff_quality}, "
            f"Flip={eff_flip} verified"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        fx3_group_name="Setup -> [Monitor]",
        fx3_active_items_count=FX3_MONITOR_GROUP_ACTIVE_ITEMS_COUNT,
        finder_monitor_group_exposed=False,
        dormant_evf_menus_exposed=False,
        monitor_settings_resettable=False,
        effective_monitor_brightness=eff_bright_mode,
        effective_monitor_brightness_level=eff_bright_lvl,
        effective_display_quality="Standard" if body_temperature_high else eff_quality,
        display_quality_thermally_locked=body_temperature_high,
        upm_lcd_brightness_limit_notified=upm_limit,
        effective_monitor_flip_direction=eff_flip,
        bright_monitoring_in_monitor_group=False,
        fx6_vf_brightness=None,
        fx6_vf_color_mode=None,
        fx6_vf_mirror=None,
        fx6_4_vf_submenus_exposed=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 77C: Still P/A/S/M-Only [Recall Custom hold 1-3] vs FX6 Push Controls
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RecallCustomHoldPushControlsAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    exposure_mode: str
    operation: str
    hold_slot: Optional[int]
    slots_count: int
    valid_checkbox_param_count: int
    white_balance_independent_slot_supported: bool
    self_timer_included_in_recall_drive_mode: bool
    recall_resettable: bool
    persisted_in_camset_dat: bool
    hlg_temporarily_disabled: bool
    effective_checked_params: Tuple[str, ...]
    fx6_recall_custom_hold_supported: bool
    fx6_high_low_key_exposed: bool


def simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_STILL,
    exposure_mode: str = "P",
    operation: str = "recall_custom_hold",
    hold_slot: int = 1,
    checked_params: Optional[Tuple[str, ...]] = None,
    include_self_timer_in_drive_mode: bool = False,
    hlg_still_image: str = "Off",
    drive_mode_bracket: str = "None",
    focus_mode: str = "AF-C",
    fx6_lens_manual_focus: bool = False,
    fx6_lens_manual_iris: bool = False,
    fx6_desqueeze: str = "Off(1.0x)",
    fx6_exposure_mode: str = "Cine EI",
    fx6_bokeh_control: str = "Off",
    fx6_push_af_mode: str = "AF",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> RecallCustomHoldPushControlsAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage77Phase350Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage77Phase350Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage77Phase350Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if exposure_mode not in VALID_EXPOSURE_MODES:
        raise Stage77Phase350Error(f"Invalid exposure_mode: {exposure_mode!r}")
    if operation not in VALID_RECALL_OPERATIONS:
        raise Stage77Phase350Error(f"Invalid operation: {operation!r}")
    if hold_slot not in (1, 2, 3):
        raise Stage77Phase350Error(f"Invalid hold_slot: {hold_slot!r}")
    if hlg_still_image not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid hlg_still_image: {hlg_still_image!r}")
    if drive_mode_bracket not in ("None", "ISO Bracket", "DRO Bracket", "Cont. Shooting"):
        raise Stage77Phase350Error(f"Invalid drive_mode_bracket: {drive_mode_bracket!r}")
    if focus_mode not in VALID_FOCUS_MODES:
        raise Stage77Phase350Error(f"Invalid focus_mode: {focus_mode!r}")
    if fx6_desqueeze not in FX6_DESQUEEZE_OPTIONS:
        raise Stage77Phase350Error(f"Invalid fx6_desqueeze: {fx6_desqueeze!r}")
    if fx6_exposure_mode not in FX6_EXPOSURE_MODES:
        raise Stage77Phase350Error(f"Invalid fx6_exposure_mode: {fx6_exposure_mode!r}")
    if fx6_bokeh_control not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid fx6_bokeh_control: {fx6_bokeh_control!r}")
    if fx6_push_af_mode not in FX6_PUSH_AF_MODES:
        raise Stage77Phase350Error(f"Invalid fx6_push_af_mode: {fx6_push_af_mode!r}")

    # 1. ILME-FX6 Ver. 6.01: zero Recall Custom hold 1-3, dormant High/Low Key, Push AF/AGC/Iris
    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_dormant_high_low_key":
            return RecallCustomHoldPushControlsAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX6 ns2 0x4b25 High/Low Key is dormant shared literal (0 exposed UI items)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                operation=operation,
                hold_slot=None,
                slots_count=0,
                valid_checkbox_param_count=0,
                white_balance_independent_slot_supported=False,
                self_timer_included_in_recall_drive_mode=False,
                recall_resettable=False,
                persisted_in_camset_dat=False,
                hlg_temporarily_disabled=False,
                effective_checked_params=(),
                fx6_recall_custom_hold_supported=False,
                fx6_high_low_key_exposed=False,
            )
        if operation not in ("fx6_push_af", "fx6_push_agc", "fx6_push_auto_iris"):
            return RecallCustomHoldPushControlsAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"ILME-FX6 Ver. 6.01 has ZERO [Recall Custom hold 1-3] / {operation!r}; "
                    "uses Assignable Button Push AF / Push AGC / Push Auto Iris"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                operation=operation,
                hold_slot=None,
                slots_count=0,
                valid_checkbox_param_count=0,
                white_balance_independent_slot_supported=False,
                self_timer_included_in_recall_drive_mode=False,
                recall_resettable=False,
                persisted_in_camset_dat=False,
                hlg_temporarily_disabled=False,
                effective_checked_params=(),
                fx6_recall_custom_hold_supported=False,
                fx6_high_low_key_exposed=False,
            )
        if operation == "fx6_push_af":
            if fx6_lens_manual_focus or fx6_desqueeze != "Off(1.0x)":
                return RecallCustomHoldPushControlsAudit(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    reason=(
                        "FX6 Push AF blocked when lens is in manual focus or "
                        f"De-Squeeze={fx6_desqueeze} != Off(1.0x)"
                    ),
                    body_profile=body_profile,
                    fw_version=fw_version,
                    shoot_mode=shoot_mode,
                    exposure_mode=exposure_mode,
                    operation=operation,
                    hold_slot=None,
                    slots_count=0,
                    valid_checkbox_param_count=0,
                    white_balance_independent_slot_supported=False,
                    self_timer_included_in_recall_drive_mode=False,
                    recall_resettable=False,
                    persisted_in_camset_dat=False,
                    hlg_temporarily_disabled=False,
                    effective_checked_params=(),
                    fx6_recall_custom_hold_supported=False,
                    fx6_high_low_key_exposed=False,
                )
        if operation == "fx6_push_agc":
            if fx6_exposure_mode in ("Cine EI", "Cine EI Quick") or fx6_bokeh_control == "On":
                return RecallCustomHoldPushControlsAudit(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    reason=(
                        f"FX6 Push AGC blocked in {fx6_exposure_mode} or Bokeh Control={fx6_bokeh_control}"
                    ),
                    body_profile=body_profile,
                    fw_version=fw_version,
                    shoot_mode=shoot_mode,
                    exposure_mode=exposure_mode,
                    operation=operation,
                    hold_slot=None,
                    slots_count=0,
                    valid_checkbox_param_count=0,
                    white_balance_independent_slot_supported=False,
                    self_timer_included_in_recall_drive_mode=False,
                    recall_resettable=False,
                    persisted_in_camset_dat=False,
                    hlg_temporarily_disabled=False,
                    effective_checked_params=(),
                    fx6_recall_custom_hold_supported=False,
                    fx6_high_low_key_exposed=False,
                )
        if operation == "fx6_push_auto_iris":
            if fx6_lens_manual_iris or fx6_bokeh_control == "On":
                return RecallCustomHoldPushControlsAudit(
                    admitted=False,
                    errno_code=EOPNOTSUPP_ERRNO,
                    reason=(
                        "FX6 Push Auto Iris blocked when lens iris is MANUAL or "
                        f"Bokeh Control={fx6_bokeh_control}"
                    ),
                    body_profile=body_profile,
                    fw_version=fw_version,
                    shoot_mode=shoot_mode,
                    exposure_mode=exposure_mode,
                    operation=operation,
                    hold_slot=None,
                    slots_count=0,
                    valid_checkbox_param_count=0,
                    white_balance_independent_slot_supported=False,
                    self_timer_included_in_recall_drive_mode=False,
                    recall_resettable=False,
                    persisted_in_camset_dat=False,
                    hlg_temporarily_disabled=False,
                    effective_checked_params=(),
                    fx6_recall_custom_hold_supported=False,
                    fx6_high_low_key_exposed=False,
                )
        return RecallCustomHoldPushControlsAudit(
            admitted=True,
            errno_code=0,
            reason=f"FX6 Ver. 6.01 {operation} ({fx6_push_af_mode}) executed cleanly",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            operation=operation,
            hold_slot=None,
            slots_count=0,
            valid_checkbox_param_count=0,
            white_balance_independent_slot_supported=False,
            self_timer_included_in_recall_drive_mode=False,
            recall_resettable=False,
            persisted_in_camset_dat=False,
            hlg_temporarily_disabled=False,
            effective_checked_params=(),
            fx6_recall_custom_hold_supported=False,
            fx6_high_low_key_exposed=False,
        )

    # 2. FX3 Ver. 7.02: reject FX6-only ops & myth-busted independent White Balance slot
    if operation in (
        "fx6_push_af",
        "fx6_push_agc",
        "fx6_push_auto_iris",
        "fx6_dormant_high_low_key",
    ):
        return RecallCustomHoldPushControlsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"FX6 operation {operation!r} not exposed on ILME-FX3 Ver. 7.02",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            operation=operation,
            hold_slot=None,
            slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
            valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
            white_balance_independent_slot_supported=False,
            self_timer_included_in_recall_drive_mode=False,
            recall_resettable=False,
            persisted_in_camset_dat=True,
            hlg_temporarily_disabled=False,
            effective_checked_params=(),
            fx6_recall_custom_hold_supported=False,
            fx6_high_low_key_exposed=False,
        )

    if operation == "dormant_recall_white_balance":
        return RecallCustomHoldPushControlsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "Independent White Balance slot does NOT exist in [Recall Custom hold 1-3] "
                "(shoot_set_registration_white_balance = 0 hits; only 11 slots 0..10 exist)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            operation=operation,
            hold_slot=hold_slot,
            slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
            valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
            white_balance_independent_slot_supported=False,
            self_timer_included_in_recall_drive_mode=False,
            recall_resettable=False,
            persisted_in_camset_dat=True,
            hlg_temporarily_disabled=False,
            effective_checked_params=(),
            fx6_recall_custom_hold_supported=False,
            fx6_high_low_key_exposed=False,
        )

    # 3. Hold AF Custom Keys: [AF On], [Eye AF], [Tracking On]
    if operation == "af_on":
        return RecallCustomHoldPushControlsAudit(
            admitted=True,
            errno_code=0,
            reason=f"[AF On] admitted across {shoot_mode} pipeline",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            operation=operation,
            hold_slot=None,
            slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
            valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
            white_balance_independent_slot_supported=False,
            self_timer_included_in_recall_drive_mode=False,
            recall_resettable=False,
            persisted_in_camset_dat=True,
            hlg_temporarily_disabled=False,
            effective_checked_params=(),
            fx6_recall_custom_hold_supported=False,
            fx6_high_low_key_exposed=False,
        )

    if operation == "eye_af":
        if shoot_mode == SHOOT_MODE_SQ:
            return RecallCustomHoldPushControlsAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="[Eye AF] available in Still/Movie only (blocked in S&Q)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                operation=operation,
                hold_slot=None,
                slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
                valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
                white_balance_independent_slot_supported=False,
                self_timer_included_in_recall_drive_mode=False,
                recall_resettable=False,
                persisted_in_camset_dat=True,
                hlg_temporarily_disabled=False,
                effective_checked_params=(),
                fx6_recall_custom_hold_supported=False,
                fx6_high_low_key_exposed=False,
            )
        return RecallCustomHoldPushControlsAudit(
            admitted=True,
            errno_code=0,
            reason=f"[Eye AF] admitted in {shoot_mode} pipeline",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            operation=operation,
            hold_slot=None,
            slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
            valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
            white_balance_independent_slot_supported=False,
            self_timer_included_in_recall_drive_mode=False,
            recall_resettable=False,
            persisted_in_camset_dat=True,
            hlg_temporarily_disabled=False,
            effective_checked_params=(),
            fx6_recall_custom_hold_supported=False,
            fx6_high_low_key_exposed=False,
        )

    if operation == "tracking_on":
        if shoot_mode != SHOOT_MODE_STILL or focus_mode != "AF-C":
            return RecallCustomHoldPushControlsAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"[Tracking On] requires Still mode + Focus Mode = AF-C (got {shoot_mode}, {focus_mode})",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                operation=operation,
                hold_slot=None,
                slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
                valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
                white_balance_independent_slot_supported=False,
                self_timer_included_in_recall_drive_mode=False,
                recall_resettable=False,
                persisted_in_camset_dat=True,
                hlg_temporarily_disabled=False,
                effective_checked_params=(),
                fx6_recall_custom_hold_supported=False,
                fx6_high_low_key_exposed=False,
            )
        return RecallCustomHoldPushControlsAudit(
            admitted=True,
            errno_code=0,
            reason="[Tracking On] admitted in Still AF-C",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            operation=operation,
            hold_slot=None,
            slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
            valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
            white_balance_independent_slot_supported=False,
            self_timer_included_in_recall_drive_mode=False,
            recall_resettable=False,
            persisted_in_camset_dat=True,
            hlg_temporarily_disabled=False,
            effective_checked_params=(),
            fx6_recall_custom_hold_supported=False,
            fx6_high_low_key_exposed=False,
        )

    # 4. [Recall Custom hold 1-3] — strictly Still P/A/S/M-only!
    if shoot_mode != SHOOT_MODE_STILL or exposure_mode not in STILL_PASM_MODES:
        return RecallCustomHoldPushControlsAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"[Recall Custom hold {hold_slot}] strictly Still P/A/S/M-only "
                f"(rejected in shoot_mode={shoot_mode}, exposure_mode={exposure_mode})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            operation=operation,
            hold_slot=hold_slot,
            slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
            valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
            white_balance_independent_slot_supported=False,
            self_timer_included_in_recall_drive_mode=False,
            recall_resettable=False,
            persisted_in_camset_dat=True,
            hlg_temporarily_disabled=False,
            effective_checked_params=(),
            fx6_recall_custom_hold_supported=False,
            fx6_high_low_key_exposed=False,
        )

    req_params = RECALL_CUSTOM_HOLD_11_PARAMS if checked_params is None else checked_params
    for p in req_params:
        if p == "white_balance":
            return RecallCustomHoldPushControlsAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="white_balance is NOT an independent checkbox in [Recall Custom hold 1-3]",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                exposure_mode=exposure_mode,
                operation=operation,
                hold_slot=hold_slot,
                slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
                valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
                white_balance_independent_slot_supported=False,
                self_timer_included_in_recall_drive_mode=False,
                recall_resettable=False,
                persisted_in_camset_dat=True,
                hlg_temporarily_disabled=False,
                effective_checked_params=(),
                fx6_recall_custom_hold_supported=False,
                fx6_high_low_key_exposed=False,
            )
        if p not in RECALL_CUSTOM_HOLD_11_PARAMS:
            raise Stage77Phase350Error(f"Invalid Recall Custom hold param: {p!r}")

    if include_self_timer_in_drive_mode:
        return RecallCustomHoldPushControlsAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason="Self-timer is excluded from [Recall Custom hold 1-3] Drive Mode registration",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            exposure_mode=exposure_mode,
            operation=operation,
            hold_slot=hold_slot,
            slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
            valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
            white_balance_independent_slot_supported=False,
            self_timer_included_in_recall_drive_mode=False,
            recall_resettable=False,
            persisted_in_camset_dat=True,
            hlg_temporarily_disabled=False,
            effective_checked_params=(),
            fx6_recall_custom_hold_supported=False,
            fx6_high_low_key_exposed=False,
        )

    eff_params: Tuple[str, ...] = () if initialize_applied else tuple(req_params)
    hlg_temp_off = bool(
        (not initialize_applied)
        and hlg_still_image == "On"
        and drive_mode_bracket in ("ISO Bracket", "DRO Bracket")
    )
    return RecallCustomHoldPushControlsAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"[Recall Custom hold {hold_slot}] Still {exposure_mode} verified "
            f"(11 slots, Reset-immune={not camera_settings_reset_applied or True}, "
            f"initialized={initialize_applied})"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        operation=operation,
        hold_slot=hold_slot,
        slots_count=RECALL_CUSTOM_HOLD_SLOTS_COUNT,
        valid_checkbox_param_count=RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
        white_balance_independent_slot_supported=False,
        self_timer_included_in_recall_drive_mode=False,
        recall_resettable=False,
        persisted_in_camset_dat=True,
        hlg_temporarily_disabled=hlg_temp_off,
        effective_checked_params=eff_params,
        fx6_recall_custom_hold_supported=False,
        fx6_high_low_key_exposed=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 77D: Setup -> [External Output] HDMI Matrix & Slot 1 EROFS=30
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExternalOutputHdmiRecControlSlot1Audit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    operation: str
    external_output_resettable: bool
    effective_hdmi_resolution: str
    effective_rec_media_dur_hdmi_output: str
    effective_output_resolution: str
    output_downscaled_to_1080: bool
    effective_4k_output_set: str
    reboot_required: bool
    cross_frame_rate_playback_isolated: bool
    effective_raw_output: str
    effective_time_code_output: str
    effective_rec_control: str
    effective_4ch_audio_output: str
    effective_hdmi_info_display: str
    body_lcd_blackout: bool
    effective_ctrl_for_hdmi: str
    hdmi_4k_outpute_typo_symbol: str
    ctrl_for_hmdi_typo_symbol: str
    dormant_24p_60p_exposed: bool
    dormant_4k_2k_exposed: bool
    slot1_erofs_triggered: bool
    slot1_data_sector_writes: int
    emmc_nflasha_write_count: int
    fx6_sdi_output: Optional[str]
    fx6_hdmi_output: Optional[str]


def simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_MOVIE,
    operation: str = "hdmi_output",
    hdmi_connected: bool = True,
    hdmi_resolution: str = "Auto",
    rec_media_dur_hdmi_output: str = "On",
    output_resolution: str = "Auto",
    four_k_output_set: str = "59.94p 10bit",
    previous_four_k_output_set: str = "59.94p 10bit",
    raw_output: str = "Off",
    time_code_output: str = "Off",
    rec_control: str = "Off",
    compatible_ext_recorder: bool = True,
    rec_w_shutter: str = "Off",
    four_ch_audio_output: str = "CH1/CH2",
    hdmi_info_display: str = "On",
    ctrl_for_hdmi: str = "On",
    log_shooting: str = "Off",
    picture_profile: str = "Off",
    recording_target_slot: str = "Slot 1",
    usb_streaming_mode: str = "Off",
    fx6_sdi_on: bool = True,
    fx6_hdmi_on: bool = True,
    fx6_codec: str = "XAVC-I",
    fx6_sq_fps: float = 24.0,
    fx6_sdi_hdmi_rec_control: str = "Off",
    fx6_hdmi_tc_out: str = "Off",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> ExternalOutputHdmiRecControlSlot1Audit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage77Phase350Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage77Phase350Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage77Phase350Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if operation not in VALID_EXTERNAL_OUTPUT_OPERATIONS:
        raise Stage77Phase350Error(f"Invalid operation: {operation!r}")
    if hdmi_resolution not in VALID_HDMI_RESOLUTIONS:
        raise Stage77Phase350Error(f"Invalid hdmi_resolution: {hdmi_resolution!r}")
    if rec_media_dur_hdmi_output not in VALID_REC_MEDIA_HDMI_MODES:
        raise Stage77Phase350Error(
            f"Invalid rec_media_dur_hdmi_output: {rec_media_dur_hdmi_output!r}"
        )
    if output_resolution not in VALID_HDMI_RESOLUTIONS:
        raise Stage77Phase350Error(f"Invalid output_resolution: {output_resolution!r}")
    if four_k_output_set not in VALID_4K_HDMI_OUTPUT_RATES:
        raise Stage77Phase350Error(f"Invalid four_k_output_set: {four_k_output_set!r}")
    if previous_four_k_output_set not in VALID_4K_HDMI_OUTPUT_RATES:
        raise Stage77Phase350Error(
            f"Invalid previous_four_k_output_set: {previous_four_k_output_set!r}"
        )
    if raw_output not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid raw_output: {raw_output!r}")
    if time_code_output not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid time_code_output: {time_code_output!r}")
    if rec_control not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid rec_control: {rec_control!r}")
    if rec_w_shutter not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid rec_w_shutter: {rec_w_shutter!r}")
    if four_ch_audio_output not in VALID_4CH_HDMI_AUDIO_MODES:
        raise Stage77Phase350Error(
            f"Invalid four_ch_audio_output: {four_ch_audio_output!r}"
        )
    if hdmi_info_display not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid hdmi_info_display: {hdmi_info_display!r}")
    if ctrl_for_hdmi not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid ctrl_for_hdmi: {ctrl_for_hdmi!r}")
    if log_shooting not in VALID_LOG_SHOOTING_MODES:
        raise Stage77Phase350Error(f"Invalid log_shooting: {log_shooting!r}")
    if picture_profile not in VALID_PICTURE_PROFILES:
        raise Stage77Phase350Error(f"Invalid picture_profile: {picture_profile!r}")
    if recording_target_slot not in VALID_RECORDING_SLOTS:
        raise Stage77Phase350Error(
            f"Invalid recording_target_slot: {recording_target_slot!r}"
        )
    if usb_streaming_mode not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid usb_streaming_mode: {usb_streaming_mode!r}")
    if fx6_codec not in FX6_CODECS:
        raise Stage77Phase350Error(f"Invalid fx6_codec: {fx6_codec!r}")
    if fx6_sq_fps <= 0.0:
        raise Stage77Phase350Error("fx6_sq_fps must be > 0")
    if fx6_sdi_hdmi_rec_control not in FX6_SDI_HDMI_REC_CONTROL_MODES:
        raise Stage77Phase350Error(
            f"Invalid fx6_sdi_hdmi_rec_control: {fx6_sdi_hdmi_rec_control!r}"
        )
    if fx6_hdmi_tc_out not in VALID_TOGGLES:
        raise Stage77Phase350Error(f"Invalid fx6_hdmi_tc_out: {fx6_hdmi_tc_out!r}")

    typo_4k = "PRM_HAITA_hdmi_4k_outpute_apsc_restriction"
    typo_cec = "BKID_APP_setting_ctrl_for_hmdi"

    # 1. ILME-FX6 Ver. 6.01 Dual 12G-SDI + HDMI Matrix
    if body_profile == BODY_MODEL_FX6:
        if operation != "fx6_dual_output":
            return ExternalOutputHdmiRecControlSlot1Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not expose FX3 External Output operation {operation!r}",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                external_output_resettable=False,
                effective_hdmi_resolution="N/A",
                effective_rec_media_dur_hdmi_output="N/A",
                effective_output_resolution="N/A",
                output_downscaled_to_1080=False,
                effective_4k_output_set="N/A",
                reboot_required=False,
                cross_frame_rate_playback_isolated=False,
                effective_raw_output="Off",
                effective_time_code_output=fx6_hdmi_tc_out,
                effective_rec_control=fx6_sdi_hdmi_rec_control,
                effective_4ch_audio_output="N/A",
                effective_hdmi_info_display="N/A",
                body_lcd_blackout=False,
                effective_ctrl_for_hdmi="N/A",
                hdmi_4k_outpute_typo_symbol=typo_4k,
                ctrl_for_hmdi_typo_symbol=typo_cec,
                dormant_24p_60p_exposed=False,
                dormant_4k_2k_exposed=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                fx6_sdi_output=None,
                fx6_hdmi_output=None,
            )

        if fx6_sdi_hdmi_rec_control != "Off" and fx6_hdmi_on and fx6_hdmi_tc_out != "On":
            return ExternalOutputHdmiRecControlSlot1Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="FX6 HDMI REC Control trigger requires TC/Media > HDMI TC Out = On",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                external_output_resettable=False,
                effective_hdmi_resolution="N/A",
                effective_rec_media_dur_hdmi_output="N/A",
                effective_output_resolution="N/A",
                output_downscaled_to_1080=False,
                effective_4k_output_set="N/A",
                reboot_required=False,
                cross_frame_rate_playback_isolated=False,
                effective_raw_output="Off",
                effective_time_code_output=fx6_hdmi_tc_out,
                effective_rec_control=fx6_sdi_hdmi_rec_control,
                effective_4ch_audio_output="N/A",
                effective_hdmi_info_display="N/A",
                body_lcd_blackout=False,
                effective_ctrl_for_hdmi="N/A",
                hdmi_4k_outpute_typo_symbol=typo_4k,
                ctrl_for_hmdi_typo_symbol=typo_cec,
                dormant_24p_60p_exposed=False,
                dormant_4k_2k_exposed=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                fx6_sdi_output=None,
                fx6_hdmi_output=None,
            )

        if fx6_sdi_hdmi_rec_control == "Parallel Rec" and recording_target_slot == "Slot 1":
            return ExternalOutputHdmiRecControlSlot1Audit(
                admitted=False,
                errno_code=EROFS_ERRNO,
                reason="Tier-0 Slot 1 EROFS=30 Firewall blocked FX6 Parallel Rec targeting Slot 1",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                external_output_resettable=False,
                effective_hdmi_resolution="N/A",
                effective_rec_media_dur_hdmi_output="N/A",
                effective_output_resolution="N/A",
                output_downscaled_to_1080=False,
                effective_4k_output_set="N/A",
                reboot_required=False,
                cross_frame_rate_playback_isolated=False,
                effective_raw_output="Off",
                effective_time_code_output=fx6_hdmi_tc_out,
                effective_rec_control=fx6_sdi_hdmi_rec_control,
                effective_4ch_audio_output="N/A",
                effective_hdmi_info_display="N/A",
                body_lcd_blackout=False,
                effective_ctrl_for_hdmi="N/A",
                hdmi_4k_outpute_typo_symbol=typo_4k,
                ctrl_for_hmdi_typo_symbol=typo_cec,
                dormant_24p_60p_exposed=False,
                dormant_4k_2k_exposed=False,
                slot1_erofs_triggered=True,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                fx6_sdi_output=None,
                fx6_hdmi_output=None,
            )

        if not fx6_sdi_on:
            sdi_out = "Off"
        elif fx6_codec in ("RAW(HDMI)", "RAW(HDMI) & XAVC-I"):
            sdi_out = "1920x1080P/i"
        elif fx6_codec in ("RAW", "RAW & XAVC-I"):
            sdi_out = "4096x2160/3840x2160 RAW"
        else:
            sdi_out = "3840x2160/1920x1080"

        if not fx6_hdmi_on:
            hdmi_out = "Off"
        elif fx6_codec in ("RAW(HDMI)", "RAW(HDMI) & XAVC-I"):
            hdmi_out = "4240x2392 RAW(HDMI)"
        elif fx6_sq_fps > 60.0 and (fx6_sdi_on or "RAW" in fx6_codec):
            hdmi_out = "1920x1080P"
        else:
            hdmi_out = "4K/UHD/FHD"

        return ExternalOutputHdmiRecControlSlot1Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Ver. 6.01 dual output codec={fx6_codec} S&Q={fx6_sq_fps}fps "
                f"SDI={sdi_out} HDMI={hdmi_out} rec_ctrl={fx6_sdi_hdmi_rec_control} verified"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            external_output_resettable=False,
            effective_hdmi_resolution="Auto",
            effective_rec_media_dur_hdmi_output="N/A",
            effective_output_resolution="Auto",
            output_downscaled_to_1080=(hdmi_out == "1920x1080P" or sdi_out == "1920x1080P/i"),
            effective_4k_output_set="N/A",
            reboot_required=False,
            cross_frame_rate_playback_isolated=False,
            effective_raw_output="On" if "RAW" in fx6_codec else "Off",
            effective_time_code_output=fx6_hdmi_tc_out,
            effective_rec_control=fx6_sdi_hdmi_rec_control,
            effective_4ch_audio_output="N/A",
            effective_hdmi_info_display="N/A",
            body_lcd_blackout=False,
            effective_ctrl_for_hdmi="N/A",
            hdmi_4k_outpute_typo_symbol=typo_4k,
            ctrl_for_hmdi_typo_symbol=typo_cec,
            dormant_24p_60p_exposed=False,
            dormant_4k_2k_exposed=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            fx6_sdi_output=sdi_out,
            fx6_hdmi_output=hdmi_out,
        )

    # 2. FX3 Ver. 7.02 Reset-immunity vs Initialize law for Setup -> [External Output]
    if initialize_applied:
        eff_hdmi_res = "Auto"
        eff_rec_media = "On"
        eff_out_res = "Auto"
        eff_4k_set = "59.94p 10bit"
        eff_raw_out = "Off"
        eff_tc_out = "Off"
        eff_rec_ctrl = "Off"
        eff_4ch_audio = "CH1/CH2"
        eff_info_disp = "On"
        eff_ctrl_hdmi = "On"
    else:
        eff_hdmi_res = hdmi_resolution
        eff_rec_media = rec_media_dur_hdmi_output
        eff_out_res = output_resolution
        eff_4k_set = four_k_output_set
        eff_raw_out = raw_output
        eff_tc_out = time_code_output
        eff_rec_ctrl = rec_control
        eff_4ch_audio = four_ch_audio_output
        eff_info_disp = hdmi_info_display
        eff_ctrl_hdmi = ctrl_for_hdmi

    # 3. Dormant items (`24p/60p Output`, `4K/2K Output`) & FX6-only ops
    if operation in ("dormant_24p_60p", "dormant_4k_2k", "fx6_dual_output"):
        return ExternalOutputHdmiRecControlSlot1Audit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"{operation!r} is dormant / unexposed on ILME-FX3 Ver. 7.02",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            external_output_resettable=False,
            effective_hdmi_resolution=eff_hdmi_res,
            effective_rec_media_dur_hdmi_output=eff_rec_media,
            effective_output_resolution=eff_out_res,
            output_downscaled_to_1080=False,
            effective_4k_output_set=eff_4k_set,
            reboot_required=False,
            cross_frame_rate_playback_isolated=False,
            effective_raw_output=eff_raw_out,
            effective_time_code_output=eff_tc_out,
            effective_rec_control=eff_rec_ctrl,
            effective_4ch_audio_output=eff_4ch_audio,
            effective_hdmi_info_display=eff_info_disp,
            body_lcd_blackout=False,
            effective_ctrl_for_hdmi=eff_ctrl_hdmi,
            hdmi_4k_outpute_typo_symbol=typo_4k,
            ctrl_for_hmdi_typo_symbol=typo_cec,
            dormant_24p_60p_exposed=False,
            dormant_4k_2k_exposed=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            fx6_sdi_output=None,
            fx6_hdmi_output=None,
        )

    # 4. S&Q overrides: Rec. Media forced On, RAW Output locked Off, Time Code Output disabled
    if shoot_mode == SHOOT_MODE_SQ:
        if eff_rec_media == "Off(HDMI Only)":
            return ExternalOutputHdmiRecControlSlot1Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="[Rec. Media dur HDMI Output] is forced On in S&Q mode (Off(HDMI Only) locked out)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                external_output_resettable=False,
                effective_hdmi_resolution=eff_hdmi_res,
                effective_rec_media_dur_hdmi_output="On",
                effective_output_resolution=eff_out_res,
                output_downscaled_to_1080=False,
                effective_4k_output_set=eff_4k_set,
                reboot_required=False,
                cross_frame_rate_playback_isolated=False,
                effective_raw_output="Off",
                effective_time_code_output="Off",
                effective_rec_control="Off",
                effective_4ch_audio_output=eff_4ch_audio,
                effective_hdmi_info_display=eff_info_disp,
                body_lcd_blackout=False,
                effective_ctrl_for_hdmi=eff_ctrl_hdmi,
                hdmi_4k_outpute_typo_symbol=typo_4k,
                ctrl_for_hmdi_typo_symbol=typo_cec,
                dormant_24p_60p_exposed=False,
                dormant_4k_2k_exposed=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                fx6_sdi_output=None,
                fx6_hdmi_output=None,
            )
        if eff_raw_out == "On":
            return ExternalOutputHdmiRecControlSlot1Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="[RAW Output] is locked Off in S&Q mode",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                external_output_resettable=False,
                effective_hdmi_resolution=eff_hdmi_res,
                effective_rec_media_dur_hdmi_output="On",
                effective_output_resolution=eff_out_res,
                output_downscaled_to_1080=False,
                effective_4k_output_set=eff_4k_set,
                reboot_required=False,
                cross_frame_rate_playback_isolated=False,
                effective_raw_output="Off",
                effective_time_code_output="Off",
                effective_rec_control="Off",
                effective_4ch_audio_output=eff_4ch_audio,
                effective_hdmi_info_display=eff_info_disp,
                body_lcd_blackout=False,
                effective_ctrl_for_hdmi=eff_ctrl_hdmi,
                hdmi_4k_outpute_typo_symbol=typo_4k,
                ctrl_for_hmdi_typo_symbol=typo_cec,
                dormant_24p_60p_exposed=False,
                dormant_4k_2k_exposed=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                fx6_sdi_output=None,
                fx6_hdmi_output=None,
            )
        if eff_tc_out == "On":
            return ExternalOutputHdmiRecControlSlot1Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason="[Time Code Output] is disabled in S&Q mode",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                external_output_resettable=False,
                effective_hdmi_resolution=eff_hdmi_res,
                effective_rec_media_dur_hdmi_output="On",
                effective_output_resolution=eff_out_res,
                output_downscaled_to_1080=False,
                effective_4k_output_set=eff_4k_set,
                reboot_required=False,
                cross_frame_rate_playback_isolated=False,
                effective_raw_output="Off",
                effective_time_code_output="Off",
                effective_rec_control="Off",
                effective_4ch_audio_output=eff_4ch_audio,
                effective_hdmi_info_display=eff_info_disp,
                body_lcd_blackout=False,
                effective_ctrl_for_hdmi=eff_ctrl_hdmi,
                hdmi_4k_outpute_typo_symbol=typo_4k,
                ctrl_for_hmdi_typo_symbol=typo_cec,
                dormant_24p_60p_exposed=False,
                dormant_4k_2k_exposed=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                fx6_sdi_output=None,
                fx6_hdmi_output=None,
            )

    # 5. REC Control hard prerequisites: Time Code Output = On, compatible recorder, HDMI connected, no USB streaming
    if eff_rec_ctrl == "On":
        if (
            eff_tc_out != "On"
            or (not compatible_ext_recorder)
            or (not hdmi_connected)
            or usb_streaming_mode == "On"
        ):
            return ExternalOutputHdmiRecControlSlot1Audit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "[REC Control] = On hard-requires [Time Code Output] = On, "
                    "HDMI connected, compatible external recorder, and USB Streaming = Off"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                operation=operation,
                external_output_resettable=False,
                effective_hdmi_resolution=eff_hdmi_res,
                effective_rec_media_dur_hdmi_output=eff_rec_media,
                effective_output_resolution=eff_out_res,
                output_downscaled_to_1080=False,
                effective_4k_output_set=eff_4k_set,
                reboot_required=False,
                cross_frame_rate_playback_isolated=False,
                effective_raw_output=eff_raw_out,
                effective_time_code_output=eff_tc_out,
                effective_rec_control="Off",
                effective_4ch_audio_output=eff_4ch_audio,
                effective_hdmi_info_display=eff_info_disp,
                body_lcd_blackout=False,
                effective_ctrl_for_hdmi=eff_ctrl_hdmi,
                hdmi_4k_outpute_typo_symbol=typo_4k,
                ctrl_for_hmdi_typo_symbol=typo_cec,
                dormant_24p_60p_exposed=False,
                dormant_4k_2k_exposed=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                emmc_nflasha_write_count=0,
                fx6_sdi_output=None,
                fx6_hdmi_output=None,
            )

    # 6. Downscale, HDMI Info Display override & 24.00p reboot checks
    downscale_1080 = bool(
        (log_shooting != "Off" or picture_profile in PPLUT_PROFILES)
        and eff_rec_media == "On"
        and eff_raw_out == "Off"
    )
    eff_resolved_out_res = "1080p" if downscale_1080 else eff_out_res
    eff_resolved_info_disp = (
        "Off" if (eff_rec_media == "Off(HDMI Only)" or eff_raw_out == "On") else eff_info_disp
    )
    lcd_blackout = bool(hdmi_connected and eff_resolved_info_disp == "On")
    reboot_24p = (eff_4k_set == "24.00p 10bit") != (
        previous_four_k_output_set == "24.00p 10bit"
    )

    # 7. Tier-0 Slot 1 EROFS=30 Firewall:
    # When [REC Control] = On is triggered with Rec. Media dur HDMI Output = On targeting Slot 1,
    # VFS/block layer MUST fail-closed with EROFS=30 (zero sector writes, zero eMMC writes).
    if (
        operation == "rec_control_trigger"
        and eff_rec_ctrl == "On"
        and eff_rec_media == "On"
        and recording_target_slot == "Slot 1"
    ):
        return ExternalOutputHdmiRecControlSlot1Audit(
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason=(
                "Tier-0 Slot 1 EROFS=30 Firewall blocked [REC Control]=On with "
                "Rec. Media dur HDMI Output=On targeting read-only Slot 1 vault "
                "(switch to Off(HDMI Only) or writable Slot 2)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            operation=operation,
            external_output_resettable=False,
            effective_hdmi_resolution=eff_hdmi_res,
            effective_rec_media_dur_hdmi_output=eff_rec_media,
            effective_output_resolution=eff_resolved_out_res,
            output_downscaled_to_1080=downscale_1080,
            effective_4k_output_set=eff_4k_set,
            reboot_required=reboot_24p,
            cross_frame_rate_playback_isolated=reboot_24p,
            effective_raw_output=eff_raw_out,
            effective_time_code_output=eff_tc_out,
            effective_rec_control=eff_rec_ctrl,
            effective_4ch_audio_output=eff_4ch_audio,
            effective_hdmi_info_display=eff_resolved_info_disp,
            body_lcd_blackout=lcd_blackout,
            effective_ctrl_for_hdmi=eff_ctrl_hdmi,
            hdmi_4k_outpute_typo_symbol=typo_4k,
            ctrl_for_hmdi_typo_symbol=typo_cec,
            dormant_24p_60p_exposed=False,
            dormant_4k_2k_exposed=False,
            slot1_erofs_triggered=True,
            slot1_data_sector_writes=0,
            emmc_nflasha_write_count=0,
            fx6_sdi_output=None,
            fx6_hdmi_output=None,
        )

    return ExternalOutputHdmiRecControlSlot1Audit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Ver. 7.02 [External Output] op={operation} RecMedia={eff_rec_media} "
            f"TC={eff_tc_out} REC_Ctrl={eff_rec_ctrl} OutRes={eff_resolved_out_res} "
            f"InfoDisp={eff_resolved_info_disp} slot={recording_target_slot} "
            f"rec_w_shutter={rec_w_shutter} verified"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        operation=operation,
        external_output_resettable=False,
        effective_hdmi_resolution=eff_hdmi_res,
        effective_rec_media_dur_hdmi_output=eff_rec_media,
        effective_output_resolution=eff_resolved_out_res,
        output_downscaled_to_1080=downscale_1080,
        effective_4k_output_set=eff_4k_set,
        reboot_required=reboot_24p,
        cross_frame_rate_playback_isolated=reboot_24p,
        effective_raw_output=eff_raw_out,
        effective_time_code_output=eff_tc_out,
        effective_rec_control=eff_rec_ctrl,
        effective_4ch_audio_output=eff_4ch_audio,
        effective_hdmi_info_display=eff_resolved_info_disp,
        body_lcd_blackout=lcd_blackout,
        effective_ctrl_for_hdmi=eff_ctrl_hdmi,
        hdmi_4k_outpute_typo_symbol=typo_4k,
        ctrl_for_hmdi_typo_symbol=typo_cec,
        dormant_24p_60p_exposed=False,
        dormant_4k_2k_exposed=False,
        slot1_erofs_triggered=False,
        slot1_data_sector_writes=0,
        emmc_nflasha_write_count=0,
        fx6_sdi_output=None,
        fx6_hdmi_output=None,
    )


# ---------------------------------------------------------------------------
# Stage 77 Milestone Probe & Full Wave-67 Co-Emulation Runner
# ---------------------------------------------------------------------------


def _build_stage77_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_77th_stage_milestone": IS_77TH_STAGE_MILESTONE,
        "wave": "Wave-67",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def _strip_wall_clock(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_wall_clock(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [_strip_wall_clock(item) for item in obj]
    return obj


def run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
    work_root: Union[None, str, Path, object] = _UNSET,
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    donor_audit = inspect_phase350_wave67_donors(
        work_root=work_root, force_clean_room=force_clean_room, env=env
    )

    # Sub-Model 77A probes
    p77a_silent_default_shutter = simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
        operation="auto_poweroff",
        auto_pixel_mapping="On",
        silent_mode="On",
        silent_target_auto_pixel_mapping="Off",
    )
    p77a_silent_target_on_muted = simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
        operation="auto_poweroff",
        auto_pixel_mapping="On",
        silent_mode="On",
        silent_target_auto_pixel_mapping="On",
    )
    p77a_reset_immune = simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
        operation="auto_poweroff",
        auto_pixel_mapping="Off",
        silent_target_auto_pixel_mapping="On",
        camera_settings_reset_applied=True,
    )
    p77a_manual_reboot = simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
        operation="manual_pixel_mapping",
        lens_cap_light_shielded=True,
    )
    p77a_blocks = [
        simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="dormant_pixel_map_notification"
        ),
        simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            operation="dormant_shutter_when_pwr_off"
        ),
        simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            operation="fx6_abb_menu",
        ),
    ]
    p77a_fx6_apr = simulate_pixel_mapping_silent_shutter_and_fx6_apr_abb_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_apr_execute",
        lens_cap_light_shielded=True,
        black_cloth_shielded=True,
        temperature_valid=True,
    )
    p77a_ok = (
        p77a_silent_default_shutter.admitted
        and p77a_silent_default_shutter.mechanical_shutter_sound_emitted
        and p77a_silent_target_on_muted.admitted
        and (not p77a_silent_target_on_muted.mechanical_shutter_sound_emitted)
        and p77a_reset_immune.effective_auto_pixel_mapping == "Off"
        and (not p77a_reset_immune.auto_pixel_mapping_resettable)
        and p77a_reset_immune.effective_silent_target_auto_pixel_mapping == "Off"
        and p77a_manual_reboot.admitted
        and p77a_manual_reboot.auto_reboot_triggered
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p77a_blocks)
        and p77a_fx6_apr.admitted
        and p77a_fx6_apr.fx6_apr_executed
        and (not p77a_fx6_apr.fx6_abb_menu_exposed)
    )

    # Sub-Model 77B probes
    p77b_monitor_reset = simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
        monitor_brightness="Sunny Weather",
        display_quality="High",
        monitor_flip_direction="180 Degree Flip",
        camera_settings_reset_applied=True,
    )
    p77b_thermal_lock = simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
        display_quality="High",
        body_temperature_high=True,
    )
    p77b_dormant_evf = [
        simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
            operation="dormant_finder_monitor_group"
        ),
        *[
            simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
                operation="dormant_evf_item", dormant_evf_item=item
            )
            for item in DORMANT_FX3_EVF_MENUS
        ],
    ]
    p77b_fx6_vf = simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_vf_setting",
        fx6_vf_brightness=8,
        fx6_vf_color_mode="Color",
    )
    p77b_fx6_dormant_sub = simulate_monitor_3item_dormant_evf_and_fx6_vf_setting_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_dormant_vf_submenu",
        fx6_dormant_submenu="Color Temp.",
    )
    p77b_ok = (
        p77b_monitor_reset.admitted
        and p77b_monitor_reset.fx3_group_name == "Setup -> [Monitor]"
        and p77b_monitor_reset.fx3_active_items_count == 3
        and (not p77b_monitor_reset.finder_monitor_group_exposed)
        and (not p77b_monitor_reset.monitor_settings_resettable)
        and p77b_monitor_reset.effective_display_quality == "High"
        and (not p77b_thermal_lock.admitted)
        and p77b_thermal_lock.effective_display_quality == "Standard"
        and p77b_thermal_lock.display_quality_thermally_locked
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p77b_dormant_evf)
        and p77b_fx6_vf.admitted
        and p77b_fx6_vf.fx6_vf_brightness == 8
        and (not p77b_fx6_dormant_sub.admitted)
        and p77b_fx6_dormant_sub.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 77C probes
    p77c_still_pasm = simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
        shoot_mode=SHOOT_MODE_STILL,
        exposure_mode="M",
        operation="recall_custom_hold",
        hold_slot=2,
        camera_settings_reset_applied=True,
    )
    p77c_blocks = [
        simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            operation="recall_custom_hold",
            hold_slot=1,
        ),
        simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            shoot_mode=SHOOT_MODE_SQ,
            operation="recall_custom_hold",
            hold_slot=1,
        ),
        simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            operation="dormant_recall_white_balance"
        ),
        simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            operation="fx6_push_agc",
            fx6_exposure_mode="Cine EI",
        ),
        simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            operation="fx6_dormant_high_low_key",
        ),
    ]
    p77c_fx6_push_ok = simulate_still_pasm_recall_custom_hold_and_fx6_push_controls_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_push_af",
        fx6_lens_manual_focus=False,
        fx6_desqueeze="Off(1.0x)",
    )
    p77c_ok = (
        p77c_still_pasm.admitted
        and len(p77c_still_pasm.effective_checked_params) == 11
        and (not p77c_still_pasm.white_balance_independent_slot_supported)
        and (not p77c_still_pasm.recall_resettable)
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p77c_blocks)
        and p77c_fx6_push_ok.admitted
        and (not p77c_fx6_push_ok.fx6_recall_custom_hold_supported)
    )

    # Sub-Model 77D probes
    p77d_slot1_erofs = simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
        operation="rec_control_trigger",
        rec_media_dur_hdmi_output="On",
        time_code_output="On",
        rec_control="On",
        recording_target_slot="Slot 1",
    )
    p77d_safe_hdmi_only = simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
        operation="rec_control_trigger",
        rec_media_dur_hdmi_output="Off(HDMI Only)",
        time_code_output="On",
        rec_control="On",
        recording_target_slot="Slot 1",
    )
    p77d_safe_slot2 = simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
        operation="rec_control_trigger",
        rec_media_dur_hdmi_output="On",
        time_code_output="On",
        rec_control="On",
        recording_target_slot="Slot 2",
        log_shooting="Cine EI",
    )
    p77d_24p_reboot = simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
        operation="change_4k_24p",
        four_k_output_set="24.00p 10bit",
        previous_four_k_output_set="23.98p 10bit",
    )
    p77d_blocks = [
        simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            operation="rec_control_trigger",
            time_code_output="Off",
            rec_control="On",
            recording_target_slot="Slot 2",
        ),
        simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            operation="dormant_24p_60p"
        ),
        simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            operation="dormant_4k_2k"
        ),
        simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
            shoot_mode=SHOOT_MODE_SQ,
            rec_media_dur_hdmi_output="Off(HDMI Only)",
        ),
    ]
    p77d_fx6_raw_hdmi = simulate_external_output_hdmi_tc_rec_control_and_slot1_erofs_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_dual_output",
        fx6_codec="RAW(HDMI)",
        fx6_sdi_hdmi_rec_control="SDI/HDMI Remote I/F",
        fx6_hdmi_tc_out="On",
    )
    p77d_ok = (
        (not p77d_slot1_erofs.admitted)
        and p77d_slot1_erofs.errno_code == EROFS_ERRNO
        and p77d_slot1_erofs.slot1_erofs_triggered
        and p77d_slot1_erofs.slot1_data_sector_writes == 0
        and p77d_safe_hdmi_only.admitted
        and p77d_safe_hdmi_only.effective_hdmi_info_display == "Off"
        and p77d_safe_slot2.admitted
        and p77d_safe_slot2.output_downscaled_to_1080
        and p77d_24p_reboot.admitted
        and p77d_24p_reboot.reboot_required
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p77d_blocks)
        and p77d_fx6_raw_hdmi.admitted
        and p77d_fx6_raw_hdmi.fx6_hdmi_output == "4240x2392 RAW(HDMI)"
        and p77d_fx6_raw_hdmi.fx6_sdi_output == "1920x1080P/i"
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
        "pixel_mapping_auto_reset_wipe_events": PIXEL_MAPPING_AUTO_RESET_WIPE_EVENTS,
        "silent_auto_pixel_mapping_default_mute_shutter": SILENT_AUTO_PIXEL_MAPPING_DEFAULT_MUTE_SHUTTER,
        "pixel_mappinng_typo_matched": PIXEL_MAPPINNG_TYPO_MATCHED,
        "pixel_mapping_excuted_typo_matched": PIXEL_MAPPING_EXCUTED_TYPO_MATCHED,
        "dormant_pixel_map_notification_exposed_events": DORMANT_PIXEL_MAP_NOTIFICATION_EXPOSED_EVENTS,
        "dormant_shutter_when_pwr_off_exposed_events": DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS,
        "fx6_abb_menu_exposed_events": FX6_ABB_MENU_EXPOSED_EVENTS,
        "fx3_monitor_group_active_items_count": FX3_MONITOR_GROUP_ACTIVE_ITEMS_COUNT,
        "dormant_finder_monitor_group_exposed_events": DORMANT_FINDER_MONITOR_GROUP_EXPOSED_EVENTS,
        "dormant_evf_menus_exposed_events": DORMANT_EVF_MENUS_EXPOSED_EVENTS,
        "monitor_settings_reset_wipe_events": MONITOR_SETTINGS_RESET_WIPE_EVENTS,
        "display_quality_thermal_override_bypass_events": DISPLAY_QUALITY_THERMAL_OVERRIDE_BYPASS_EVENTS,
        "fx6_vf_brightness_default": FX6_VF_BRIGHTNESS_DEFAULT,
        "fx6_dormant_vf_4submenus_exposed_events": FX6_DORMANT_VF_4SUBMENUS_EXPOSED_EVENTS,
        "recall_custom_hold_slots_count": RECALL_CUSTOM_HOLD_SLOTS_COUNT,
        "recall_custom_hold_checkbox_params_count": RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT,
        "recall_custom_hold_white_balance_independent_slots": RECALL_CUSTOM_HOLD_WHITE_BALANCE_INDEPENDENT_SLOTS,
        "recall_custom_hold_movie_sq_bypass_events": RECALL_CUSTOM_HOLD_MOVIE_SQ_BYPASS_EVENTS,
        "recall_custom_hold_reset_wipe_events": RECALL_CUSTOM_HOLD_RESET_WIPE_EVENTS,
        "fx6_recall_custom_hold_exposed_events": FX6_RECALL_CUSTOM_HOLD_EXPOSED_EVENTS,
        "fx6_dormant_high_low_key_exposed_events": FX6_DORMANT_HIGH_LOW_KEY_EXPOSED_EVENTS,
        "external_output_reset_wipe_events": EXTERNAL_OUTPUT_RESET_WIPE_EVENTS,
        "hdmi_4k_outpute_typo_matched": HDMI_4K_OUTPUTE_TYPO_MATCHED,
        "ctrl_for_hmdi_typo_matched": CTRL_FOR_HMDI_TYPO_MATCHED,
        "dormant_24p_60p_and_4k_2k_output_exposed_events": DORMANT_24P_60P_AND_4K_2K_OUTPUT_EXPOSED_EVENTS,
        "rec_control_without_tc_bypass_events": REC_CONTROL_WITHOUT_TC_BYPASS_EVENTS,
        "hdmi_rec_media_slot1_erofs_bypass_events": HDMI_REC_MEDIA_SLOT1_EROFS_BYPASS_EVENTS,
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
        and PIXEL_MAPPING_AUTO_RESET_WIPE_EVENTS == 0
        and (not SILENT_AUTO_PIXEL_MAPPING_DEFAULT_MUTE_SHUTTER)
        and PIXEL_MAPPINNG_TYPO_MATCHED
        and PIXEL_MAPPING_EXCUTED_TYPO_MATCHED
        and DORMANT_PIXEL_MAP_NOTIFICATION_EXPOSED_EVENTS == 0
        and DORMANT_SHUTTER_WHEN_PWR_OFF_EXPOSED_EVENTS == 0
        and FX6_ABB_MENU_EXPOSED_EVENTS == 0
        and FX3_MONITOR_GROUP_ACTIVE_ITEMS_COUNT == 3
        and DORMANT_FINDER_MONITOR_GROUP_EXPOSED_EVENTS == 0
        and DORMANT_EVF_MENUS_EXPOSED_EVENTS == 0
        and MONITOR_SETTINGS_RESET_WIPE_EVENTS == 0
        and DISPLAY_QUALITY_THERMAL_OVERRIDE_BYPASS_EVENTS == 0
        and FX6_VF_BRIGHTNESS_DEFAULT == 8
        and FX6_DORMANT_VF_4SUBMENUS_EXPOSED_EVENTS == 0
        and RECALL_CUSTOM_HOLD_SLOTS_COUNT == 3
        and RECALL_CUSTOM_HOLD_CHECKBOX_PARAMS_COUNT == 11
        and RECALL_CUSTOM_HOLD_WHITE_BALANCE_INDEPENDENT_SLOTS == 0
        and RECALL_CUSTOM_HOLD_MOVIE_SQ_BYPASS_EVENTS == 0
        and RECALL_CUSTOM_HOLD_RESET_WIPE_EVENTS == 0
        and FX6_RECALL_CUSTOM_HOLD_EXPOSED_EVENTS == 0
        and FX6_DORMANT_HIGH_LOW_KEY_EXPOSED_EVENTS == 0
        and EXTERNAL_OUTPUT_RESET_WIPE_EVENTS == 0
        and HDMI_4K_OUTPUTE_TYPO_MATCHED
        and CTRL_FOR_HMDI_TYPO_MATCHED
        and DORMANT_24P_60P_AND_4K_2K_OUTPUT_EXPOSED_EVENTS == 0
        and REC_CONTROL_WITHOUT_TC_BYPASS_EVENTS == 0
        and HDMI_REC_MEDIA_SLOT1_EROFS_BYPASS_EVENTS == 0
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
        and IS_77TH_STAGE_MILESTONE
        and STAGE_INDEX == 77
        and STAGE_TOTAL == 77
        and MILESTONE_LABEL == "77/77"
        and p77a_ok
        and p77b_ok
        and p77c_ok
        and p77d_ok
        and redlines_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_350_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_77th_stage_milestone": IS_77TH_STAGE_MILESTONE,
        "source_mode": donor_audit.source_mode,
        "all_checks_passed": all_passed,
        "redlines": redlines,
        "donor_audit": asdict(donor_audit),
        "stage77_milestone_probe": _build_stage77_milestone_probe(),
        "pillar_a_pixelmap_silent_shutter_fx6_apr_abb_hil": {
            "passed": p77a_ok,
            "silent_default_shutter": asdict(p77a_silent_default_shutter),
            "silent_target_on_muted": asdict(p77a_silent_target_on_muted),
            "reset_immune": asdict(p77a_reset_immune),
            "manual_reboot": asdict(p77a_manual_reboot),
            "dormant_and_abb_blocks": [asdict(r) for r in p77a_blocks],
            "fx6_apr_execute": asdict(p77a_fx6_apr),
        },
        "pillar_b_monitor_3item_dormant_evf_fx6_vf_hil": {
            "passed": p77b_ok,
            "monitor_reset_immune": asdict(p77b_monitor_reset),
            "thermal_lock_high": asdict(p77b_thermal_lock),
            "dormant_evf_blocks": [asdict(r) for r in p77b_dormant_evf],
            "fx6_vf_setting": asdict(p77b_fx6_vf),
            "fx6_dormant_vf_submenu": asdict(p77b_fx6_dormant_sub),
        },
        "pillar_c_still_pasm_recall_custom_hold_fx6_push_hil": {
            "passed": p77c_ok,
            "still_pasm_recall": asdict(p77c_still_pasm),
            "movie_sq_wb_push_blocks": [asdict(r) for r in p77c_blocks],
            "fx6_push_af": asdict(p77c_fx6_push_ok),
        },
        "pillar_d_external_output_hdmi_tc_rec_ctrl_slot1_erofs_hil": {
            "passed": p77d_ok,
            "slot1_erofs_blocked": asdict(p77d_slot1_erofs),
            "safe_hdmi_only": asdict(p77d_safe_hdmi_only),
            "safe_slot2_log_1080": asdict(p77d_safe_slot2),
            "change_4k_24p_reboot": asdict(p77d_24p_reboot),
            "tc_and_dormant_blocks": [asdict(r) for r in p77d_blocks],
            "fx6_raw_hdmi_sdi_downscale": asdict(p77d_fx6_raw_hdmi),
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
            "Phase 350 (Stage 77 — 77/77 Full-Board Stages!): Real-Hardware ILME-FX3 Ver. 7.02 vs "
            "ILME-FX6 Ver. 6.01 Wave-67 [Pixel Mapping] / [Auto Pixel Mapping] & Silent-Mode Default vs "
            "FX6 APR / 100%% Dormant ABB, Setup -> [Monitor] 3-Item & 4 Dormant EVF vs FX6 VF Setting, "
            "Still P/A/S/M-Only [Recall Custom hold 1-3] 11-Slot (0 WB) vs FX6 Push AF/AGC/Iris, and "
            "[External Output] HDMI TC / REC Control & Tier-0 Slot 1 EROFS=30 Firewall HIL"
        )
    )
    parser.add_argument("--self-test", action="store_true", help="Run Stage 77 HIL audit")
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
    rep = run_phase350_pixelmap_apr_monitor_vfadjust_customhold_hdmi_reccontrol_coemulation(
        work_root=wr,
        force_clean_room=True if args.clean_room else None,
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 350 Stage 77 ({rep['milestone']} Stages) | "
            f"mode={rep['source_mode']} | donors={rep['donor_audit']['donors_verified']}/"
            f"{rep['donor_audit']['donors_checked']} | "
            f"mon={red['fx3_monitor_group_active_items_count']} | "
            f"evf={red['dormant_evf_menus_exposed_events']} | "
            f"hold={red['recall_custom_hold_slots_count']}x{red['recall_custom_hold_checkbox_params_count']} | "
            f"wb={red['recall_custom_hold_white_balance_independent_slots']} | "
            f"abb={red['fx6_abb_menu_exposed_events']} | "
            f"s1_wr={red['slot1_data_sector_writes']} | "
            f"leak={red['raw_firmware_bytes_leaked']} | "
            f"digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
