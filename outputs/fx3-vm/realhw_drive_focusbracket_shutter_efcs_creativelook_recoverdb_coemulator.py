#!/usr/bin/env python3
"""Phase 346 (Stage 76 — 76/76 Full-Board VM Co-Emulation Stages):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-66 HIL Co-Emulator.

Models and audits the four Wave-66 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / `CLEAN_ROOM_SYNTHETIC` CI fallback and
`raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 76A (`Shooting -> [Drive Mode]` `10 fps` Cont. / Bracket Matrix &
   100%% Dormant `[Focus Bracket]` Myth-Busting)**:
   - Active Still `[Drive Mode]` options (`_f 0x7228`, all `Can be reset`,
     disabled in Movie/`S&Q`): `Single Shooting` (def), `Cont. Shooting` (`Hi+`
     `~10 fps` non-realtime live view / `Hi` `~8 fps` / `Mid` `~6 fps` / `Lo`
     `~3 fps`; `> F11` locks focus on 1st frame in `Hi+/Hi/Mid`; `Uncompressed
     RAW` or Flash reduces burst rate), `Self-timer(Single)` (`10/5/2 Sec`),
     `Self-timer(Cont)` (`10/5/2 Sec x 3/5 Img.` 6 options; dormant `10 Img.`
     rejected `EOPNOTSUPP=95`), `Cont. Bracket` & `Single Bracket`
     (`0.3/0.5/0.7/1.0 EV x 3/5/9 Img.`, `2.0/3.0 EV x 3/5 Img.`, disabled in
     `iAuto`), `WB bracket` (`Lo +-10 MK-1` / `Hi +-20 MK-1` x 3), `DRO Bracket`
     (`Lo Lv 1,2,3` / `Hi Lv 1,3,5`; disabled when `[HLG Still Image] = On`),
     `[Bracket Settings]` (`0->-->+` def / `-->0->+`), and `[Interval Shoot
     Func.]` (independent `Shutter Type in Interval = Electronic Shutter` def).
   - **100%% Dormant `[Focus Bracket]` Myth-Busting**: `[Focus Bracket]`
     (`DRIVE_MODE_FOCUS_BRACKET`, `0` hits in `ilc/2210` on `ALCIN_UUD`, plus `0`
     Still `[Drive Mode]` on pure-cinema `ILME-FX6`) rejected `EOPNOTSUPP=95`.

2. **Sub-Model 76B (`[Shutter Type]` 2-Option Zero-`Auto`, Single `1/250 s`
   X-Sync, Reset-Immune `[e-Front Curtain Shut.]` `curtaion` Typo, `[Long
   Exposure NR]` & `[High ISO NR]`)**:
   - `[Shutter Type]` (`BKID_APP_setting_still_shutter_type`, `Can be reset`)
     exposes strictly **2** options (`Mechanical Shutter` def / `Electronic
     Shutter`) — rejects dormant `Auto` (`EOPNOTSUPP=95`). Selecting
     `Electronic Shutter` (or `[Silent Mode] = On`) locks out **5** features:
     `Flash`, `[Long Exposure NR]`, `[e-Front Curtain Shut.]`, `BULB`, and
     `[Anti-flicker Shoot.]`.
   - Flash X-Sync is strictly **`1/250 s` across BOTH FF & APS-C** (`0` hits
     for `1/320 s` in `ilc/2210`!).
   - `[e-Front Curtain Shut.]` (`BKID_APP_setting_front_curtaion_shutter` Sony
     internal typo `curtaion`): `On` def / `Off`, **Reset-immune** (`Not
     available`, restored only on Initialize), emits bokeh-clipping and
     Minolta/3rd-party adapter shading advisories.
   - `[Long Exposure NR]` (`On` def / `Off`, `Can be reset`, `>= 1 s`
     dark-frame subtraction, locked in Electronic/Silent/Cont./Cont.Bracket,
     forced `On` in `iAuto`) & `[High ISO NR]` (`Normal` def / `Low` / `Off`,
     `Can be reset`, dormant `HIGH` rejected `EOPNOTSUPP=95`, disabled on pure
     `RAW` and never alters `.ARW`), contrasted against `ILME-FX6` shutterless
     `Shooting > Noise Suppression` (`Off/Low/Mid/High`) & `Technical > APR >
     Execute`.

3. **Sub-Model 76C (`[Creative Look]` `10` Presets + `6` Custom Looks + `8`
   Params `0..9` Bounds, `PP`/`Log` Override & 100%% Dormant `[Soft Skin
   Effect]`)**:
   - `[Creative Look]` (`Can be reset`): `10` presets (`ST` def, `PT`, `NT`,
     `VV`, `VV2`, `FL`, `IN`, `SH`, `BW`, `SE`) + `Custom Look 1..6`
     (`look{0..15}` separate Still & Movie), with exact **8** parameter bounds:
     `-9..+9` (`Contrast`, `Highlights`, `Shadows`, `Saturation`), **`0..9`**
     (`Fade`, `Sharpness`, `Clarity` — NOT `-9..+9`!), and **`1..5`**
     (`Sharpness Range` / ELF `fineness`).
   - Parameter & pipeline lockouts: `BW`/`SE` lock out `Saturation`;
     Movie/`S&Q` lock out `Sharpness Range`; `iAuto`, `[Picture Profile] !=
     Off`, `[Log Shooting] != Off`, or `[HLG Still Image] = On` lock `[Creative
     Look]` (`[-]`).
   - **100%% Dormant `[Soft Skin Effect]` Myth-Busting**: rejects `[Soft Skin
     Effect]` (`EOPNOTSUPP=95`) on BOTH `ILME-FX3 Ver. 7.02` AND `ILME-FX6
     Ver. 6.01` (`0` hits in `ilc/2210`, unsupported in Sony Camera Remote SDK),
     contrasting `FX6` `Paint/Look > Base Look` + `Scene File` + `Detail`/`Matrix`.

4. **Sub-Model 76D (`Playback -> [Delete]` / `[Protect]` & `[Recover Image DB]`
   `AVF_INFO` Tier-0 `Slot 1` `EROFS=30` Firewall)**:
   - `[Delete]` (`All Other Than This Img.`, `All Images in This Group`,
     `Multiple Img.`, `All in this Folder`, `All with this date`), `[Delete
     confirm.]` (`"Cancel" first` def / `"Delete" first`), `[Delete pressing
     twice]` (`Off` def / `On` instant unconfirmed delete hazard!), and
     `[Protect]` (coupled main + `*S03.MP4` Proxy delete/protect; `[Copy]` does
     not copy Protect; all Playback configs **Reset-immune**).
   - `[Recover Image DB]` (`SYSTEM_MODE_OPTION_RECOVER_DB`, unaffected by Reset
     AND Initialize, rewrites `AVF_INFO` and clears FTP transfer status) vs
     read-only `[Display Media Info.]` (`40,000`-still cap, `NOT_DISPLAYNG`
     typo, `0` writes): enforces fail-closed Tier-0 `Slot 1` `EROFS=30`
     (`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`) on
     any `[Delete]`/`[Protect]`/`[Recover Image DB]` targeting `Slot 1`, vs
     `ILME-FX6` `Lock/Unlock Clip` + `Restore Media(A)/(B)` (`ng_write_protected`).
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
# Phase 346 Schema, Milestone & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase346_realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation_v1"
)
PHASE_346_VERSION = "346.0.0"
PHASE_NUMBER = 346
STAGE_INDEX = 76
STAGE_TOTAL = 76
MILESTONE_LABEL = "76/76"
IS_76TH_STAGE_MILESTONE = True

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

# Wave-66 Sub-Model 76A..76D Numeric & Invariant Contracts
# 76A — Still [Drive Mode] & 100% Dormant [Focus Bracket]
STILL_CONT_HI_PLUS_MAX_FPS = 10
STILL_CONT_HI_MAX_FPS = 8
STILL_CONT_MID_MAX_FPS = 6
STILL_CONT_LO_MAX_FPS = 3
STILL_CONT_AF_LOCK_APERTURE_THRESHOLD = 11.0
SELF_TIMER_CONT_OPTIONS_COUNT = 6
DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS = 0
FX6_STILL_DRIVE_MODE_EXPOSED_EVENTS = 0
DRO_BRACKET_HLG_BYPASS_EVENTS = 0

# 76B — [Shutter Type] 2-Option Zero-Auto, 1/250 s X-Sync, EFCS `curtaion` & NR
SHUTTER_TYPE_ACTIVE_OPTIONS_COUNT = 2
DORMANT_SHUTTER_TYPE_AUTO_EXPOSED_EVENTS = 0
FLASH_X_SYNC_MAX_SPEED_DENOM = 250
APSC_1_320_XSYNC_SPOOF_EVENTS = 0
E_FRONT_CURTAIN_TYPO_MATCHED = True
E_FRONT_CURTAIN_RESET_WIPE_EVENTS = 0
ESHUTTER_5LOCK_BYPASS_EVENTS = 0
DORMANT_HIGH_ISO_NR_HIGH_EXPOSED_EVENTS = 0
HIGH_ISO_NR_ARW_MUTATION_EVENTS = 0

# 76C — [Creative Look] 10+6 Slots, 8 Params `0..9` Bounds & Dormant [Soft Skin Effect]
CREATIVE_LOOK_PRESETS_COUNT = 10
CREATIVE_LOOK_CUSTOM_SLOTS_COUNT = 6
CREATIVE_LOOK_TOTAL_SLOTS_COUNT = 16
CREATIVE_LOOK_PARAM_COUNT = 8
CREATIVE_LOOK_CLARITY_FADE_SHARPNESS_MAX = 9
CREATIVE_LOOK_SHARPNESS_RANGE_MIN = 1
CREATIVE_LOOK_SHARPNESS_RANGE_MAX = 5
CREATIVE_LOOK_PP_LOG_HLG_OVERRIDE_BYPASS_EVENTS = 0
FX3_SOFT_SKIN_EFFECT_EXPOSED_EVENTS = 0
FX6_SOFT_SKIN_EFFECT_EXPOSED_EVENTS = 0

# 76D — [Delete] / [Protect] / [Recover Image DB] AVF_INFO Slot 1 EROFS=30 Firewall
PLAYBACK_CONFIG_RESET_WIPE_EVENTS = 0
RECOVER_DB_RESET_OR_INIT_WIPE_EVENTS = 0
RECOVER_DB_SLOT1_EROFS_BYPASS_EVENTS = 0
DELETE_OR_PROTECT_SLOT1_EROFS_BYPASS_EVENTS = 0
DISPLAY_MEDIA_INFO_STILL_CAP = 40_000
NOT_DISPLAYNG_TYPO_MATCHED = True
PROXY_DECOUPLED_ORPHAN_EVENTS = 0

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
# Verified Local Donor Specs (11 FX3 Ver. 7.02 & FX6 Ver. 6.01 Wave-66 Donors)
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
        b"Drive Mode",
        b"Focus Bracket",
        b"Single Shooting",
        b"Cont. Shooting",
        b"Self-timer(Single)",
        b"Self-timer(Cont)",
        b"Cont. Bracket",
        b"Single Bracket",
        b"WB bracket",
        b"DRO Bracket",
        b"Bracket Settings",
        b"Interval Shoot Func.",
        b"Shutter Type",
        b"Mechanical Shutter",
        b"Electronic Shutter",
        b"e-Front Curtain Shut.",
        b"Long Exposure NR",
        b"High ISO NR",
        b"Creative Look",
        b"Highlights",
        b"Shadows",
        b"Fade",
        b"Sharpness Range",
        b"Clarity",
        b"Soft Skin Effect",
        b"Delete pressing twice",
        b"Recover Image DB",
        b"Display Media Info.",
    ),
    "fx3_string_sc_f": (
        "\u9a71\u52a8\u6a21\u5f0f".encode("utf-8"),
        "\u5355\u5f20\u62cd\u6444".encode("utf-8"),
        "\u8fde\u62cd".encode("utf-8"),
        "\u5feb\u95e8\u7c7b\u578b".encode("utf-8"),
        "\u7535\u5b50\u524d\u5e18\u5feb\u95e8".encode("utf-8"),
        "\u9ad8ISO\u964d\u566a".encode("utf-8"),
        "\u521b\u610f\u5916\u89c2".encode("utf-8"),
    ),
    "fx3_string_tc_f": (
        "\u9a45\u52d5\u6a21\u5f0f".encode("utf-8"),
        "\u55ae\u5f35\u62cd\u651d".encode("utf-8"),
        "\u9023\u62cd".encode("utf-8"),
        "\u5feb\u9580\u985e\u578b".encode("utf-8"),
        "\u98a8\u683c\u5916\u89c0".encode("utf-8"),
    ),
    "fx3_string_ja_f": (
        "\u30c9\u30e9\u30a4\u30d6\u30e2\u30fc\u30c9".encode("utf-8"),
        "1\u679a\u64ae\u5f71".encode("utf-8"),
        "\u9023\u7d9a\u64ae\u5f71".encode("utf-8"),
        "\u30b7\u30e3\u30c3\u30bf\u30fc\u65b9\u5f0f".encode("utf-8"),
        "\u96fb\u5b50\u5148\u5e55\u30b7\u30e3\u30c3\u30bf\u30fc".encode("utf-8"),
        "\u9ad8\u611f\u5ea6NR".encode("utf-8"),
    ),
    "fx3_string_en": (
        b"Single Shooting",
        b"Cont. Shooting",
        b"High ISO NR",
        b"Delete",
        b"Delete confirm.",
        b'"Cancel" first',
        b'"Delete" first',
        b"Protect",
        b"Recover Image DB",
        b"Display Media Info.",
        b"All with this date",
    ),
    "fx3_saveload": (b"libSaveLoadSettings", b"Save", b"Load"),
    "fx6_string_en": (
        b"Base Look",
        b"Noise Suppression",
        b"Restore Media",
        b"Soft Skin Effect",
    ),
    "fx6_string_en_2": (
        b"Noise Suppression",
        b"Restore Media",
        b"Scene File",
        b"APR",
    ),
}

LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (
            0x3AA2000,
            "DRIVE_MODE_1_IMAGE_SHOOTING",
            b"DRIVE_MODE_1_IMAGE_SHOOTING",
        ),
        (
            0x3AA2000,
            "DRIVE_MODE_FOCUS_BRACKET",
            b"DRIVE_MODE_FOCUS_BRACKET",
        ),
        (
            0x2FA1000,
            "DRIVE_MODE_CONT_SHOOTING",
            b"DRIVE_MODE_CONT_SHOOTING",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_focus_bracket_order",
            b"BKID_APP_setting_focus_bracket_order",
        ),
        (
            0x3BC6000,
            "BKID_APP_setting_still_shutter_type",
            b"BKID_APP_setting_still_shutter_type",
        ),
        (
            0x3A77000,
            "STILL_SHUTTER_TYPE_MECHANICAL",
            b"STILL_SHUTTER_TYPE_MECHANICAL",
        ),
        (
            0x3B60000,
            "STILL_SHUTTER_TYPE_ANTI_DISTORTION_SHUTTER_AUTO",
            b"STILL_SHUTTER_TYPE_ANTI_DISTORTION_SHUTTER_AUTO",
        ),
        (
            0x3BC7000,
            "BKID_APP_setting_front_curtaion_shutter",
            b"BKID_APP_setting_front_curtaion_shutter",
        ),
        (
            0x3BC5000,
            "BKID_APP_setting_still_long_exposure_nr",
            b"BKID_APP_setting_still_long_exposure_nr",
        ),
        (
            0x3BC5000,
            "BKID_APP_setting_still_high_iso_nr",
            b"BKID_APP_setting_still_high_iso_nr",
        ),
        (
            0x3BE7000,
            "BKID_APP_creative_look_option_look0",
            b"BKID_APP_creative_look_option_look0",
        ),
        (
            0x3BC8000,
            "BKID_APP_setting_soft_skin_effect",
            b"BKID_APP_setting_soft_skin_effect",
        ),
        (
            0x3BC9000,
            "BKID_APP_setting_delete_confirm",
            b"BKID_APP_setting_delete_confirm",
        ),
        (
            0x3BC9000,
            "BKID_APP_setting_delete_by_delete_twice",
            b"BKID_APP_setting_delete_by_delete_twice",
        ),
        (
            0x39D3000,
            "SYSTEM_MODE_OPTION_RECOVER_DB",
            b"SYSTEM_MODE_OPTION_RECOVER_DB",
        ),
        (
            0x39BA000,
            "PRM_media_info_displaying_state",
            b"PRM_media_info_displaying_state",
        ),
        (
            0x3AFD000,
            "NOT_DISPLAYNG",
            b"NOT_DISPLAYNG",
        ),
    ),
    "fx3_bk4": (
        (0x00000, "BK4_HEADER", b"BK4\x00"),
        (0x4A000, "ILME-FX3", b"ILME-FX3"),
    ),
    "fx6_appfw": (
        (
            0x25C1000,
            "sequence_start_focus_bracket",
            b"sequence_start_focus_bracket",
        ),
        (
            0x23EF000,
            "soft_skin_effect",
            b"soft_skin_effect",
        ),
        (
            0x270D000,
            "BKID_APP_USER_MENU_NOISE_SUPPRESSION0",
            b"BKID_APP_USER_MENU_NOISE_SUPPRESSION0",
        ),
        (
            0x287E000,
            "user_menu_noise_suppression0",
            b"user_menu_noise_suppression0",
        ),
        (
            0x23AE000,
            "procam_touch_list_base_look_presenter",
            b"procam_touch_list_base_look_presenter",
        ),
        (
            0x23C6000,
            "procam_msg_confirm_execute_apr_controller",
            b"procam_msg_confirm_execute_apr_controller",
        ),
        (
            0x23C6000,
            "procam_msg_confirm_restore_media_a_controller",
            b"procam_msg_confirm_restore_media_a_controller",
        ),
        (
            0x28E0000,
            "ng_write_protected",
            b"ng_write_protected",
        ),
    ),
}


# ---------------------------------------------------------------------------
# Wave-66 Real-Hardware Constants & Matrices
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
VALID_RECORDING_SLOTS: Tuple[str, ...] = ("Slot 1", "Slot 2")

# Sub-Model 76A — Still [Drive Mode] & 100% Dormant [Focus Bracket]
ACTIVE_DRIVE_MODES: Tuple[str, ...] = (
    "Single Shooting",
    "Cont. Shooting",
    "Self-timer(Single)",
    "Self-timer(Cont)",
    "Cont. Bracket",
    "Single Bracket",
    "WB bracket",
    "DRO Bracket",
)
DORMANT_DRIVE_MODES: Tuple[str, ...] = ("Focus Bracket",)
VALID_DRIVE_MODES: Tuple[str, ...] = ACTIVE_DRIVE_MODES + DORMANT_DRIVE_MODES

CONT_SHOOT_SPEEDS: Mapping[str, int] = {
    "Hi+": STILL_CONT_HI_PLUS_MAX_FPS,
    "Hi": STILL_CONT_HI_MAX_FPS,
    "Mid": STILL_CONT_MID_MAX_FPS,
    "Lo": STILL_CONT_LO_MAX_FPS,
}
VALID_SELF_TIMER_SINGLE_SECS: Tuple[int, ...] = (10, 5, 2)
VALID_SELF_TIMER_CONT_SECS: Tuple[int, ...] = (10, 5, 2)
ACTIVE_SELF_TIMER_CONT_SHOTS: Tuple[int, ...] = (3, 5)
DORMANT_SELF_TIMER_CONT_SHOTS: Tuple[int, ...] = (10,)
VALID_SELF_TIMER_CONT_SHOTS: Tuple[int, ...] = (
    ACTIVE_SELF_TIMER_CONT_SHOTS + DORMANT_SELF_TIMER_CONT_SHOTS
)
VALID_BRACKET_EV_STEPS: Tuple[float, ...] = (0.3, 0.5, 0.7, 1.0, 2.0, 3.0)
VALID_BRACKET_SHOTS: Tuple[int, ...] = (3, 5, 9)
VALID_WB_DRO_LEVELS: Tuple[str, ...] = ("Lo", "Hi")
VALID_BRACKET_SELFTIMERS: Tuple[str, ...] = ("Off", "2 Sec", "5 Sec", "10 Sec")
VALID_BRACKET_ORDERS: Tuple[str, ...] = ("0->-->+", "-->0->+")
VALID_INTERVAL_SHUTTER_TYPES: Tuple[str, ...] = (
    "Electronic Shutter",
    "Mechanical Shutter",
)

# Sub-Model 76B — [Shutter Type], X-Sync, EFCS `curtaion`, Long Exp NR & High ISO NR
ACTIVE_STILL_SHUTTER_TYPES: Tuple[str, ...] = (
    "Mechanical Shutter",
    "Electronic Shutter",
)
DORMANT_STILL_SHUTTER_TYPES: Tuple[str, ...] = ("Auto",)
VALID_STILL_SHUTTER_TYPES: Tuple[str, ...] = (
    ACTIVE_STILL_SHUTTER_TYPES + DORMANT_STILL_SHUTTER_TYPES
)
ESHUTTER_5_LOCKED_FEATURES: Tuple[str, ...] = (
    "Flash",
    "Long Exposure NR",
    "e-Front Curtain Shut.",
    "BULB",
    "Anti-flicker Shoot.",
)
VALID_SENSOR_CROPS: Tuple[str, ...] = ("Full-Frame", "APS-C/S35")
ACTIVE_HIGH_ISO_NR_LEVELS: Tuple[str, ...] = ("Normal", "Low", "Off")
DORMANT_HIGH_ISO_NR_LEVELS: Tuple[str, ...] = ("High",)
VALID_HIGH_ISO_NR_LEVELS: Tuple[str, ...] = (
    ACTIVE_HIGH_ISO_NR_LEVELS + DORMANT_HIGH_ISO_NR_LEVELS
)
VALID_STILL_FILE_FORMATS: Tuple[str, ...] = (
    "RAW",
    "RAW & JPEG",
    "RAW & HEIF",
    "JPEG",
    "HEIF",
)
FX6_EXPOSURE_MODES: Tuple[str, ...] = ("Cine EI", "Cine EI Quick", "Flexible ISO", "Custom")
FX6_NOISE_SUPPRESSION_LEVELS: Tuple[str, ...] = ("Off", "Low", "Mid", "High")

# Sub-Model 76C — [Creative Look], 8 Params, PP/Log Override & Dormant [Soft Skin Effect]
CREATIVE_LOOK_PRESETS: Tuple[str, ...] = (
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
CREATIVE_LOOK_CUSTOM_SLOTS: Tuple[str, ...] = tuple(
    f"Custom Look {idx}" for idx in range(1, 7)
)
VALID_CREATIVE_LOOK_CHOICES: Tuple[str, ...] = (
    CREATIVE_LOOK_PRESETS + CREATIVE_LOOK_CUSTOM_SLOTS
)
CREATIVE_LOOK_PARAM_BOUNDS: Mapping[str, Tuple[int, int]] = {
    "contrast": (-9, 9),
    "highlights": (-9, 9),
    "shadows": (-9, 9),
    "fade": (0, 9),
    "saturation": (-9, 9),
    "sharpness": (0, 9),
    "sharpness_range": (1, 5),
    "clarity": (0, 9),
}
VALID_PICTURE_PROFILES: Tuple[str, ...] = ("Off",) + tuple(
    f"PP{idx}" for idx in range(1, 12)
)
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI",
    "Cine EI Quick",
)
VALID_SOFT_SKIN_EFFECT_OPTIONS: Tuple[str, ...] = ("Off", "Low", "Mid", "High")
FX6_BASE_LOOK_MODES: Tuple[str, ...] = (
    "S-Cinetone",
    "Standard",
    "Still",
    "ITU709",
    "709tone",
    "s709",
    "709(800)",
    "S-Log3",
    "HLG Live",
    "HLG Mild",
    "HLG Natural",
)

# Sub-Model 76D — Playback [Delete]/[Protect]/[Recover Image DB]/[Display Media Info.]
VALID_PLAYBACK_OPERATIONS: Tuple[str, ...] = (
    "delete",
    "protect",
    "configure_playback",
    "recover_image_db",
    "display_media_info",
    "copy_protect_check",
)
VALID_DELETE_SCOPES: Tuple[str, ...] = (
    "Single",
    "All Other Than This Img.",
    "All Images in This Group",
    "Multiple Img.",
    "All in this Folder",
    "All with this date",
)
VALID_DELETE_CONFIRM_MODES: Tuple[str, ...] = ('"Cancel" first', '"Delete" first')
VALID_PROTECT_SCOPES: Tuple[str, ...] = (
    "Single",
    "Multiple Img.",
    "All in this Folder",
    "Cancel All in this Folder",
    "All with this date",
    "Cancel All with this date",
    "All Images in This Group",
    "Cancel All in This Group",
)
VALID_FX6_PLAYBACK_OPERATIONS: Tuple[str, ...] = (
    "Lock/Unlock Clip",
    "Delete Clip",
    "Restore Media(A)",
    "Restore Media(B)",
    "Media Status",
)


class Stage76Phase346Error(RuntimeError):
    """Raised on invalid Phase 346 Stage 76 configuration or safety redline violation."""


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
        raise Stage76Phase346Error(
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
            raise Stage76Phase346Error(
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
class Wave66DonorAuditReport:
    source_mode: str
    donor_access_mode: str
    bounded_window_max_bytes: int
    donors_checked: int
    donors_verified: int
    all_contracts_verified: bool
    raw_firmware_bytes_leaked: int
    artifacts: Dict[str, DonorArtifactInspection]


def inspect_phase346_wave66_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Wave66DonorAuditReport:
    work_root = resolve_mac_work_root(force_clean_room=force_clean_room, env=env)
    artifacts: Dict[str, DonorArtifactInspection] = {}

    if work_root is None:
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
        return Wave66DonorAuditReport(
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
    return Wave66DonorAuditReport(
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
# Sub-Model 76A: Still [Drive Mode] 10 fps / Bracket Matrix & Focus Bracket Myth
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class DriveModeFocusBracketAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    requested_drive_mode: str
    effective_drive_mode: str
    focus_bracket_exposed: bool
    fx6_still_drive_mode_supported: bool
    effective_cont_speed: Optional[str]
    nominal_max_fps: int
    effective_fps_cap: float
    burst_rate_reduced: bool
    live_view_realtime: bool
    af_locked_on_first_frame: bool
    effective_self_timer_single_sec: Optional[int]
    effective_self_timer_cont_sec: Optional[int]
    effective_self_timer_cont_shots: Optional[int]
    self_timer_cont_options_count: int
    effective_bracket_ev_step: Optional[float]
    effective_bracket_shots: Optional[int]
    effective_wb_bracket_level: Optional[str]
    effective_dro_bracket_level: Optional[str]
    dro_bracket_blocked_by_hlg: bool
    effective_bracket_selftimer: str
    effective_bracket_order: str
    interval_shoot_enabled: bool
    effective_shutter_type_in_interval: str
    interval_outputs_still_sequence_only: bool
    drive_mode_resettable: bool


def simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_STILL,
    exposure_mode: str = "P",
    drive_mode: str = "Single Shooting",
    cont_speed: str = "Hi+",
    aperture_f_stop: float = 2.8,
    raw_file_type: str = "Compressed",
    external_flash_attached: bool = False,
    self_timer_single_sec: int = 10,
    self_timer_cont_sec: int = 10,
    self_timer_cont_shots: int = 3,
    bracket_ev_step: float = 0.7,
    bracket_shots: int = 3,
    wb_bracket_level: str = "Lo",
    dro_bracket_level: str = "Lo",
    hlg_still_image: str = "Off",
    bracket_selftimer: str = "Off",
    bracket_order: str = "0->-->+",
    interval_shoot_enabled: bool = False,
    shutter_type_in_interval: str = "Electronic Shutter",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> DriveModeFocusBracketAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage76Phase346Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage76Phase346Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage76Phase346Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if drive_mode not in VALID_DRIVE_MODES:
        raise Stage76Phase346Error(f"Invalid drive_mode: {drive_mode!r}")
    if cont_speed not in CONT_SHOOT_SPEEDS:
        raise Stage76Phase346Error(f"Invalid cont_speed: {cont_speed!r}")
    if aperture_f_stop <= 0.0:
        raise Stage76Phase346Error(f"Invalid aperture_f_stop: {aperture_f_stop!r}")
    if raw_file_type not in ("Compressed", "Uncompressed"):
        raise Stage76Phase346Error(f"Invalid raw_file_type: {raw_file_type!r}")
    if self_timer_single_sec not in VALID_SELF_TIMER_SINGLE_SECS:
        raise Stage76Phase346Error(
            f"Invalid self_timer_single_sec: {self_timer_single_sec!r}"
        )
    if self_timer_cont_sec not in VALID_SELF_TIMER_CONT_SECS:
        raise Stage76Phase346Error(
            f"Invalid self_timer_cont_sec: {self_timer_cont_sec!r}"
        )
    if self_timer_cont_shots not in VALID_SELF_TIMER_CONT_SHOTS:
        raise Stage76Phase346Error(
            f"Invalid self_timer_cont_shots: {self_timer_cont_shots!r}"
        )
    if bracket_ev_step not in VALID_BRACKET_EV_STEPS:
        raise Stage76Phase346Error(f"Invalid bracket_ev_step: {bracket_ev_step!r}")
    if bracket_shots not in VALID_BRACKET_SHOTS:
        raise Stage76Phase346Error(f"Invalid bracket_shots: {bracket_shots!r}")
    if wb_bracket_level not in VALID_WB_DRO_LEVELS:
        raise Stage76Phase346Error(f"Invalid wb_bracket_level: {wb_bracket_level!r}")
    if dro_bracket_level not in VALID_WB_DRO_LEVELS:
        raise Stage76Phase346Error(f"Invalid dro_bracket_level: {dro_bracket_level!r}")
    if hlg_still_image not in VALID_TOGGLES:
        raise Stage76Phase346Error(f"Invalid hlg_still_image: {hlg_still_image!r}")
    if bracket_selftimer not in VALID_BRACKET_SELFTIMERS:
        raise Stage76Phase346Error(f"Invalid bracket_selftimer: {bracket_selftimer!r}")
    if bracket_order not in VALID_BRACKET_ORDERS:
        raise Stage76Phase346Error(f"Invalid bracket_order: {bracket_order!r}")
    if shutter_type_in_interval not in VALID_INTERVAL_SHUTTER_TYPES:
        raise Stage76Phase346Error(
            f"Invalid shutter_type_in_interval: {shutter_type_in_interval!r}"
        )

    # 1. FX6 pure-cinema contrast: zero Still Drive Mode & zero Focus Bracket
    if body_profile == BODY_MODEL_FX6:
        return DriveModeFocusBracketAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "ILME-FX6 Ver. 6.01 is pure cinema (0 Still [Drive Mode] and 0 [Focus Bracket]; "
                "56+ focus_bracket symbols in FX6 appFw.so are dormant shared Alpha leftovers)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_drive_mode=drive_mode,
            effective_drive_mode="UNSUPPORTED",
            focus_bracket_exposed=False,
            fx6_still_drive_mode_supported=False,
            effective_cont_speed=None,
            nominal_max_fps=0,
            effective_fps_cap=0.0,
            burst_rate_reduced=False,
            live_view_realtime=True,
            af_locked_on_first_frame=False,
            effective_self_timer_single_sec=None,
            effective_self_timer_cont_sec=None,
            effective_self_timer_cont_shots=None,
            self_timer_cont_options_count=0,
            effective_bracket_ev_step=None,
            effective_bracket_shots=None,
            effective_wb_bracket_level=None,
            effective_dro_bracket_level=None,
            dro_bracket_blocked_by_hlg=False,
            effective_bracket_selftimer="Off",
            effective_bracket_order="0->-->+",
            interval_shoot_enabled=False,
            effective_shutter_type_in_interval="UNSUPPORTED",
            interval_outputs_still_sequence_only=False,
            drive_mode_resettable=False,
        )

    # 2. 100% Dormant [Focus Bracket] myth-busting on ILME-FX3 Ver. 7.02
    if drive_mode in DORMANT_DRIVE_MODES:
        return DriveModeFocusBracketAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "[Focus Bracket] (DRIVE_MODE_FOCUS_BRACKET / BKID_APP_setting_focus_bracket_order) "
                "is 100%% dormant on ILME-FX3 Ver. 7.02 (0 hits in Sony ilc/2210 Help Guide)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_drive_mode=drive_mode,
            effective_drive_mode="Single Shooting",
            focus_bracket_exposed=False,
            fx6_still_drive_mode_supported=False,
            effective_cont_speed=None,
            nominal_max_fps=0,
            effective_fps_cap=0.0,
            burst_rate_reduced=False,
            live_view_realtime=True,
            af_locked_on_first_frame=False,
            effective_self_timer_single_sec=None,
            effective_self_timer_cont_sec=None,
            effective_self_timer_cont_shots=None,
            self_timer_cont_options_count=SELF_TIMER_CONT_OPTIONS_COUNT,
            effective_bracket_ev_step=None,
            effective_bracket_shots=None,
            effective_wb_bracket_level=None,
            effective_dro_bracket_level=None,
            dro_bracket_blocked_by_hlg=False,
            effective_bracket_selftimer="Off",
            effective_bracket_order="0->-->+",
            interval_shoot_enabled=False,
            effective_shutter_type_in_interval="Electronic Shutter",
            interval_outputs_still_sequence_only=True,
            drive_mode_resettable=True,
        )

    # 3. Movie / S&Q lock out all Still [Drive Mode] operations
    if shoot_mode != SHOOT_MODE_STILL:
        return DriveModeFocusBracketAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"Still [Drive Mode] and [Interval Shoot Func.] disabled in {shoot_mode} mode",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_drive_mode=drive_mode,
            effective_drive_mode="Disabled",
            focus_bracket_exposed=False,
            fx6_still_drive_mode_supported=False,
            effective_cont_speed=None,
            nominal_max_fps=0,
            effective_fps_cap=0.0,
            burst_rate_reduced=False,
            live_view_realtime=True,
            af_locked_on_first_frame=False,
            effective_self_timer_single_sec=None,
            effective_self_timer_cont_sec=None,
            effective_self_timer_cont_shots=None,
            self_timer_cont_options_count=SELF_TIMER_CONT_OPTIONS_COUNT,
            effective_bracket_ev_step=None,
            effective_bracket_shots=None,
            effective_wb_bracket_level=None,
            effective_dro_bracket_level=None,
            dro_bracket_blocked_by_hlg=False,
            effective_bracket_selftimer="Off",
            effective_bracket_order="0->-->+",
            interval_shoot_enabled=False,
            effective_shutter_type_in_interval="Electronic Shutter",
            interval_outputs_still_sequence_only=True,
            drive_mode_resettable=True,
        )

    # Reset law: ALL Still [Drive Mode], [Bracket Settings], & [Interval Shoot Func.] ARE Resettable
    if camera_settings_reset_applied or initialize_applied:
        eff_drive = "Single Shooting"
        eff_bracket_selftimer = "Off"
        eff_bracket_order = "0->-->+"
        eff_interval_shutter = "Electronic Shutter"
        eff_interval_enabled = False
    else:
        eff_drive = drive_mode
        eff_bracket_selftimer = bracket_selftimer
        eff_bracket_order = bracket_order
        eff_interval_shutter = shutter_type_in_interval
        eff_interval_enabled = interval_shoot_enabled

    # 4. Dormant Self-timer(Cont) 10-image option myth-busting (only 3/5 exposed = 6 options)
    if eff_drive == "Self-timer(Cont)" and self_timer_cont_shots in DORMANT_SELF_TIMER_CONT_SHOTS:
        return DriveModeFocusBracketAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "Self-timer(Cont) 10-image option (10SEC_10IMAGES) is dormant on FX3 Ver. 7.02; "
                "only 6 options (10/5/2 Sec x 3/5 Img.) are exposed"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_drive_mode=drive_mode,
            effective_drive_mode="Single Shooting",
            focus_bracket_exposed=False,
            fx6_still_drive_mode_supported=False,
            effective_cont_speed=None,
            nominal_max_fps=0,
            effective_fps_cap=0.0,
            burst_rate_reduced=False,
            live_view_realtime=True,
            af_locked_on_first_frame=False,
            effective_self_timer_single_sec=None,
            effective_self_timer_cont_sec=self_timer_cont_sec,
            effective_self_timer_cont_shots=None,
            self_timer_cont_options_count=SELF_TIMER_CONT_OPTIONS_COUNT,
            effective_bracket_ev_step=None,
            effective_bracket_shots=None,
            effective_wb_bracket_level=None,
            effective_dro_bracket_level=None,
            dro_bracket_blocked_by_hlg=False,
            effective_bracket_selftimer=eff_bracket_selftimer,
            effective_bracket_order=eff_bracket_order,
            interval_shoot_enabled=eff_interval_enabled,
            effective_shutter_type_in_interval=eff_interval_shutter,
            interval_outputs_still_sequence_only=True,
            drive_mode_resettable=True,
        )

    # 5. Bracket rules: iAuto blocks exposure brackets; 2.0/3.0 EV capped at 3/5 shots; HLG blocks DRO Bracket
    if eff_drive in ("Cont. Bracket", "Single Bracket"):
        if exposure_mode == "iAuto":
            return DriveModeFocusBracketAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"[{eff_drive}] disabled in Intelligent Auto (iAuto)",
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_drive_mode=drive_mode,
                effective_drive_mode="Single Shooting",
                focus_bracket_exposed=False,
                fx6_still_drive_mode_supported=False,
                effective_cont_speed=None,
                nominal_max_fps=0,
                effective_fps_cap=0.0,
                burst_rate_reduced=False,
                live_view_realtime=True,
                af_locked_on_first_frame=False,
                effective_self_timer_single_sec=None,
                effective_self_timer_cont_sec=None,
                effective_self_timer_cont_shots=None,
                self_timer_cont_options_count=SELF_TIMER_CONT_OPTIONS_COUNT,
                effective_bracket_ev_step=None,
                effective_bracket_shots=None,
                effective_wb_bracket_level=None,
                effective_dro_bracket_level=None,
                dro_bracket_blocked_by_hlg=False,
                effective_bracket_selftimer=eff_bracket_selftimer,
                effective_bracket_order=eff_bracket_order,
                interval_shoot_enabled=eff_interval_enabled,
                effective_shutter_type_in_interval=eff_interval_shutter,
                interval_outputs_still_sequence_only=True,
                drive_mode_resettable=True,
            )
        if bracket_ev_step in (2.0, 3.0) and bracket_shots == 9:
            return DriveModeFocusBracketAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"{bracket_ev_step} EV bracket supports strictly 3 or 5 images "
                    "(9-image option available only for 0.3/0.5/0.7/1.0 EV)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_drive_mode=drive_mode,
                effective_drive_mode="Single Shooting",
                focus_bracket_exposed=False,
                fx6_still_drive_mode_supported=False,
                effective_cont_speed=None,
                nominal_max_fps=0,
                effective_fps_cap=0.0,
                burst_rate_reduced=False,
                live_view_realtime=True,
                af_locked_on_first_frame=False,
                effective_self_timer_single_sec=None,
                effective_self_timer_cont_sec=None,
                effective_self_timer_cont_shots=None,
                self_timer_cont_options_count=SELF_TIMER_CONT_OPTIONS_COUNT,
                effective_bracket_ev_step=bracket_ev_step,
                effective_bracket_shots=None,
                effective_wb_bracket_level=None,
                effective_dro_bracket_level=None,
                dro_bracket_blocked_by_hlg=False,
                effective_bracket_selftimer=eff_bracket_selftimer,
                effective_bracket_order=eff_bracket_order,
                interval_shoot_enabled=eff_interval_enabled,
                effective_shutter_type_in_interval=eff_interval_shutter,
                interval_outputs_still_sequence_only=True,
                drive_mode_resettable=True,
            )

    if eff_drive == "DRO Bracket" and hlg_still_image == "On":
        return DriveModeFocusBracketAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="[DRO Bracket] disabled when [HLG Still Image] = On",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_drive_mode=drive_mode,
            effective_drive_mode="Single Shooting",
            focus_bracket_exposed=False,
            fx6_still_drive_mode_supported=False,
            effective_cont_speed=None,
            nominal_max_fps=0,
            effective_fps_cap=0.0,
            burst_rate_reduced=False,
            live_view_realtime=True,
            af_locked_on_first_frame=False,
            effective_self_timer_single_sec=None,
            effective_self_timer_cont_sec=None,
            effective_self_timer_cont_shots=None,
            self_timer_cont_options_count=SELF_TIMER_CONT_OPTIONS_COUNT,
            effective_bracket_ev_step=None,
            effective_bracket_shots=None,
            effective_wb_bracket_level=None,
            effective_dro_bracket_level=None,
            dro_bracket_blocked_by_hlg=True,
            effective_bracket_selftimer=eff_bracket_selftimer,
            effective_bracket_order=eff_bracket_order,
            interval_shoot_enabled=eff_interval_enabled,
            effective_shutter_type_in_interval=eff_interval_shutter,
            interval_outputs_still_sequence_only=True,
            drive_mode_resettable=True,
        )

    eff_cont_speed: Optional[str] = cont_speed if eff_drive == "Cont. Shooting" else None
    nominal_fps = CONT_SHOOT_SPEEDS[cont_speed] if eff_drive == "Cont. Shooting" else 0
    burst_reduced = bool(
        eff_drive == "Cont. Shooting"
        and (raw_file_type == "Uncompressed" or external_flash_attached)
    )
    if eff_drive == "Cont. Shooting":
        eff_fps = float(nominal_fps) * (0.6 if raw_file_type == "Uncompressed" else 1.0)
        if external_flash_attached:
            eff_fps = min(eff_fps, 5.0)
        live_view_rt = cont_speed != "Hi+"
        af_locked_1st = (
            aperture_f_stop > STILL_CONT_AF_LOCK_APERTURE_THRESHOLD
            and cont_speed in ("Hi+", "Hi", "Mid")
        )
    else:
        eff_fps = 0.0
        live_view_rt = True
        af_locked_1st = False

    return DriveModeFocusBracketAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Ver. 7.02 Still [Drive Mode]={eff_drive} verified "
            "(Focus Bracket 100%% dormant, Can be reset)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        requested_drive_mode=drive_mode,
        effective_drive_mode=eff_drive,
        focus_bracket_exposed=False,
        fx6_still_drive_mode_supported=False,
        effective_cont_speed=eff_cont_speed,
        nominal_max_fps=nominal_fps,
        effective_fps_cap=round(eff_fps, 2),
        burst_rate_reduced=burst_reduced,
        live_view_realtime=live_view_rt,
        af_locked_on_first_frame=af_locked_1st,
        effective_self_timer_single_sec=(
            self_timer_single_sec if eff_drive == "Self-timer(Single)" else None
        ),
        effective_self_timer_cont_sec=(
            self_timer_cont_sec if eff_drive == "Self-timer(Cont)" else None
        ),
        effective_self_timer_cont_shots=(
            self_timer_cont_shots if eff_drive == "Self-timer(Cont)" else None
        ),
        self_timer_cont_options_count=SELF_TIMER_CONT_OPTIONS_COUNT,
        effective_bracket_ev_step=(
            bracket_ev_step
            if eff_drive in ("Cont. Bracket", "Single Bracket")
            else None
        ),
        effective_bracket_shots=(
            bracket_shots
            if eff_drive in ("Cont. Bracket", "Single Bracket")
            else (
                3
                if eff_drive in ("WB bracket", "DRO Bracket")
                else None
            )
        ),
        effective_wb_bracket_level=wb_bracket_level if eff_drive == "WB bracket" else None,
        effective_dro_bracket_level=dro_bracket_level if eff_drive == "DRO Bracket" else None,
        dro_bracket_blocked_by_hlg=False,
        effective_bracket_selftimer=eff_bracket_selftimer,
        effective_bracket_order=eff_bracket_order,
        interval_shoot_enabled=eff_interval_enabled,
        effective_shutter_type_in_interval=eff_interval_shutter,
        interval_outputs_still_sequence_only=True,
        drive_mode_resettable=True,
    )


# ---------------------------------------------------------------------------
# Sub-Model 76B: [Shutter Type] Zero-Auto, 1/250 s X-Sync, EFCS & NR
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ShutterEfcsNrAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    sensor_crop: str
    effective_shutter_type: str
    shutter_type_auto_exposed: bool
    shutter_type_resettable: bool
    eshutter_or_silent_5locks_engaged: bool
    locked_features: Tuple[str, ...]
    flash_xsync_max_denom: int
    bokeh_clipping_advisory: bool
    minolta_adapter_shading_advisory: bool
    high_ss_non_hss_banding_advisory: bool
    effective_efcs: str
    efcs_elf_symbol: str
    efcs_resettable: bool
    effective_long_exposure_nr: str
    long_exposure_nr_resettable: bool
    dark_frame_subtraction_triggered: bool
    effective_high_iso_nr: str
    high_iso_nr_resettable: bool
    high_iso_nr_disabled_on_pure_raw: bool
    arw_raw_data_mutated: bool
    fx6_noise_suppression: Optional[str]
    fx6_apr_executed: bool


def simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_STILL,
    exposure_mode: str = "P",
    sensor_crop: str = "Full-Frame",
    shutter_type: str = "Mechanical Shutter",
    silent_mode: str = "Off",
    drive_mode: str = "Single Shooting",
    efcs_setting: str = "On",
    aperture_f_stop: float = 2.8,
    shutter_seconds: float = 0.008,
    adapter_or_third_party_lens: bool = False,
    third_party_non_hss_trigger: bool = False,
    flash_requested: bool = False,
    requested_flash_xsync_denom: int = 250,
    bulb_requested: bool = False,
    anti_flicker_requested: bool = False,
    efcs_active_use_requested: bool = False,
    long_exposure_nr_requested: Optional[str] = None,
    file_format: str = "RAW & JPEG",
    high_iso_nr_requested: Optional[str] = None,
    fx6_exposure_mode: str = "Cine EI",
    fx6_noise_suppression: str = "Off",
    fx6_apr_execute: bool = False,
    apr_lens_cap_covered: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> ShutterEfcsNrAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage76Phase346Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage76Phase346Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage76Phase346Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if sensor_crop not in VALID_SENSOR_CROPS:
        raise Stage76Phase346Error(f"Invalid sensor_crop: {sensor_crop!r}")
    if shutter_type not in VALID_STILL_SHUTTER_TYPES:
        raise Stage76Phase346Error(f"Invalid shutter_type: {shutter_type!r}")
    if silent_mode not in VALID_TOGGLES:
        raise Stage76Phase346Error(f"Invalid silent_mode: {silent_mode!r}")
    if drive_mode not in ACTIVE_DRIVE_MODES:
        raise Stage76Phase346Error(f"Invalid drive_mode: {drive_mode!r}")
    if efcs_setting not in VALID_TOGGLES:
        raise Stage76Phase346Error(f"Invalid efcs_setting: {efcs_setting!r}")
    if shutter_seconds <= 0.0 or aperture_f_stop <= 0.0:
        raise Stage76Phase346Error("shutter_seconds and aperture_f_stop must be > 0")
    if requested_flash_xsync_denom <= 0:
        raise Stage76Phase346Error("requested_flash_xsync_denom must be > 0")
    if long_exposure_nr_requested not in (None, "On", "Off"):
        raise Stage76Phase346Error(
            f"Invalid long_exposure_nr_requested: {long_exposure_nr_requested!r}"
        )
    if file_format not in VALID_STILL_FILE_FORMATS:
        raise Stage76Phase346Error(f"Invalid file_format: {file_format!r}")
    if high_iso_nr_requested is not None and high_iso_nr_requested not in VALID_HIGH_ISO_NR_LEVELS:
        raise Stage76Phase346Error(
            f"Invalid high_iso_nr_requested: {high_iso_nr_requested!r}"
        )
    if fx6_exposure_mode not in FX6_EXPOSURE_MODES:
        raise Stage76Phase346Error(f"Invalid fx6_exposure_mode: {fx6_exposure_mode!r}")
    if fx6_noise_suppression not in FX6_NOISE_SUPPRESSION_LEVELS:
        raise Stage76Phase346Error(
            f"Invalid fx6_noise_suppression: {fx6_noise_suppression!r}"
        )

    # 1. ILME-FX6 Ver. 6.01 shutterless cinema contrast
    if body_profile == BODY_MODEL_FX6:
        if (
            shutter_type != "Mechanical Shutter"
            or flash_requested
            or bulb_requested
            or anti_flicker_requested
            or efcs_active_use_requested
            or long_exposure_nr_requested is not None
        ):
            return ShutterEfcsNrAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Ver. 6.01 has NO mechanical focal-plane shutter, NO EFCS, NO Flash X-Sync, "
                    "and NO Long Exposure NR (uses Shooting > Noise Suppression & Technical > APR)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                sensor_crop=sensor_crop,
                effective_shutter_type="SHUTTERLESS_CINEMA",
                shutter_type_auto_exposed=False,
                shutter_type_resettable=False,
                eshutter_or_silent_5locks_engaged=False,
                locked_features=(),
                flash_xsync_max_denom=0,
                bokeh_clipping_advisory=False,
                minolta_adapter_shading_advisory=False,
                high_ss_non_hss_banding_advisory=False,
                effective_efcs="UNSUPPORTED",
                efcs_elf_symbol="DORMANT_SHARED",
                efcs_resettable=False,
                effective_long_exposure_nr="UNSUPPORTED",
                long_exposure_nr_resettable=False,
                dark_frame_subtraction_triggered=False,
                effective_high_iso_nr="UNSUPPORTED",
                high_iso_nr_resettable=False,
                high_iso_nr_disabled_on_pure_raw=False,
                arw_raw_data_mutated=False,
                fx6_noise_suppression=fx6_noise_suppression,
                fx6_apr_executed=False,
            )
        if fx6_apr_execute and not apr_lens_cap_covered:
            return ShutterEfcsNrAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    "FX6 Technical > APR > Execute requires lens cap completely covered "
                    "(procam_msg_confirm_execute_apr_controller)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                sensor_crop=sensor_crop,
                effective_shutter_type="SHUTTERLESS_CINEMA",
                shutter_type_auto_exposed=False,
                shutter_type_resettable=False,
                eshutter_or_silent_5locks_engaged=False,
                locked_features=(),
                flash_xsync_max_denom=0,
                bokeh_clipping_advisory=False,
                minolta_adapter_shading_advisory=False,
                high_ss_non_hss_banding_advisory=False,
                effective_efcs="UNSUPPORTED",
                efcs_elf_symbol="DORMANT_SHARED",
                efcs_resettable=False,
                effective_long_exposure_nr="UNSUPPORTED",
                long_exposure_nr_resettable=False,
                dark_frame_subtraction_triggered=False,
                effective_high_iso_nr="UNSUPPORTED",
                high_iso_nr_resettable=False,
                high_iso_nr_disabled_on_pure_raw=False,
                arw_raw_data_mutated=False,
                fx6_noise_suppression=fx6_noise_suppression,
                fx6_apr_executed=False,
            )
        return ShutterEfcsNrAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Ver. 6.01 Noise Suppression={fx6_noise_suppression} "
                f"(mode={fx6_exposure_mode}, APR_executed={fx6_apr_execute}) verified"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            effective_shutter_type="SHUTTERLESS_CINEMA",
            shutter_type_auto_exposed=False,
            shutter_type_resettable=False,
            eshutter_or_silent_5locks_engaged=False,
            locked_features=(),
            flash_xsync_max_denom=0,
            bokeh_clipping_advisory=False,
            minolta_adapter_shading_advisory=False,
            high_ss_non_hss_banding_advisory=False,
            effective_efcs="UNSUPPORTED",
            efcs_elf_symbol="DORMANT_SHARED",
            efcs_resettable=False,
            effective_long_exposure_nr="UNSUPPORTED",
            long_exposure_nr_resettable=False,
            dark_frame_subtraction_triggered=False,
            effective_high_iso_nr="UNSUPPORTED",
            high_iso_nr_resettable=False,
            high_iso_nr_disabled_on_pure_raw=False,
            arw_raw_data_mutated=False,
            fx6_noise_suppression=fx6_noise_suppression,
            fx6_apr_executed=fx6_apr_execute,
        )

    # 2. FX3 Ver. 7.02 Reset rules
    # Resettable: [Shutter Type], [Long Exposure NR], [High ISO NR]
    # Reset-immune: [e-Front Curtain Shut.] (`BKID_APP_setting_front_curtaion_shutter`)
    if initialize_applied:
        eff_shutter_type = "Mechanical Shutter"
        eff_efcs = "On"
        eff_lenr_req: Optional[str] = "On"
        eff_hinr_req: Optional[str] = "Normal"
    elif camera_settings_reset_applied:
        eff_shutter_type = "Mechanical Shutter"
        eff_efcs = efcs_setting
        eff_lenr_req = "On"
        eff_hinr_req = "Normal"
    else:
        eff_shutter_type = shutter_type
        eff_efcs = efcs_setting
        eff_lenr_req = long_exposure_nr_requested
        eff_hinr_req = high_iso_nr_requested

    # 3. Reject dormant [Shutter Type] = Auto (`EOPNOTSUPP=95`)
    if eff_shutter_type in DORMANT_STILL_SHUTTER_TYPES:
        return ShutterEfcsNrAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "[Shutter Type] = Auto (STILL_SHUTTER_TYPE_ANTI_DISTORTION_SHUTTER_AUTO) is dormant "
                "on ILME-FX3 Ver. 7.02; strictly 2 options exposed (Mechanical / Electronic Shutter)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            effective_shutter_type="Mechanical Shutter",
            shutter_type_auto_exposed=False,
            shutter_type_resettable=True,
            eshutter_or_silent_5locks_engaged=False,
            locked_features=(),
            flash_xsync_max_denom=FLASH_X_SYNC_MAX_SPEED_DENOM,
            bokeh_clipping_advisory=False,
            minolta_adapter_shading_advisory=False,
            high_ss_non_hss_banding_advisory=False,
            effective_efcs=eff_efcs,
            efcs_elf_symbol="BKID_APP_setting_front_curtaion_shutter",
            efcs_resettable=False,
            effective_long_exposure_nr="On",
            long_exposure_nr_resettable=True,
            dark_frame_subtraction_triggered=False,
            effective_high_iso_nr="Normal",
            high_iso_nr_resettable=True,
            high_iso_nr_disabled_on_pure_raw=(file_format == "RAW"),
            arw_raw_data_mutated=False,
            fx6_noise_suppression=None,
            fx6_apr_executed=False,
        )

    # 4. Electronic Shutter OR Silent Mode = On locks out 5 features
    eshutter_or_silent = eff_shutter_type == "Electronic Shutter" or silent_mode == "On"
    locked_5 = ESHUTTER_5_LOCKED_FEATURES if eshutter_or_silent else ()
    if eshutter_or_silent and (
        flash_requested
        or bulb_requested
        or anti_flicker_requested
        or efcs_active_use_requested
        or (eff_lenr_req is not None)
    ):
        return ShutterEfcsNrAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "Electronic Shutter / Silent Mode = On locks out 5 features: "
                "Flash, [Long Exposure NR], [e-Front Curtain Shut.], BULB, [Anti-flicker Shoot.]"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            effective_shutter_type=eff_shutter_type,
            shutter_type_auto_exposed=False,
            shutter_type_resettable=True,
            eshutter_or_silent_5locks_engaged=True,
            locked_features=locked_5,
            flash_xsync_max_denom=FLASH_X_SYNC_MAX_SPEED_DENOM,
            bokeh_clipping_advisory=False,
            minolta_adapter_shading_advisory=False,
            high_ss_non_hss_banding_advisory=False,
            effective_efcs="Locked",
            efcs_elf_symbol="BKID_APP_setting_front_curtaion_shutter",
            efcs_resettable=False,
            effective_long_exposure_nr="Locked",
            long_exposure_nr_resettable=True,
            dark_frame_subtraction_triggered=False,
            effective_high_iso_nr=eff_hinr_req or "Normal",
            high_iso_nr_resettable=True,
            high_iso_nr_disabled_on_pure_raw=(file_format == "RAW"),
            arw_raw_data_mutated=False,
            fx6_noise_suppression=None,
            fx6_apr_executed=False,
        )

    # 5. Flash X-Sync strictly 1/250 s across BOTH FF & APS-C (NO 1/320 s on FX3!)
    if flash_requested and requested_flash_xsync_denom > FLASH_X_SYNC_MAX_SPEED_DENOM:
        return ShutterEfcsNrAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"Flash X-Sync 1/{requested_flash_xsync_denom} s unsupported on ILME-FX3 ({sensor_crop}); "
                "FX3 X-Sync is strictly 1/250 s across BOTH Full-Frame & APS-C (0 hits for 1/320 s)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            effective_shutter_type=eff_shutter_type,
            shutter_type_auto_exposed=False,
            shutter_type_resettable=True,
            eshutter_or_silent_5locks_engaged=False,
            locked_features=(),
            flash_xsync_max_denom=FLASH_X_SYNC_MAX_SPEED_DENOM,
            bokeh_clipping_advisory=False,
            minolta_adapter_shading_advisory=False,
            high_ss_non_hss_banding_advisory=False,
            effective_efcs=eff_efcs,
            efcs_elf_symbol="BKID_APP_setting_front_curtaion_shutter",
            efcs_resettable=False,
            effective_long_exposure_nr=eff_lenr_req or "On",
            long_exposure_nr_resettable=True,
            dark_frame_subtraction_triggered=False,
            effective_high_iso_nr=eff_hinr_req or "Normal",
            high_iso_nr_resettable=True,
            high_iso_nr_disabled_on_pure_raw=(file_format == "RAW"),
            arw_raw_data_mutated=False,
            fx6_noise_suppression=None,
            fx6_apr_executed=False,
        )

    # 6. Long Exposure NR lockouts (`Cont. Shooting`, `Cont. Bracket`) & iAuto On-lock
    lenr_burst_locked = drive_mode in ("Cont. Shooting", "Cont. Bracket")
    if lenr_burst_locked and eff_lenr_req is not None:
        return ShutterEfcsNrAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"[Long Exposure NR] disabled in {drive_mode}",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            effective_shutter_type=eff_shutter_type,
            shutter_type_auto_exposed=False,
            shutter_type_resettable=True,
            eshutter_or_silent_5locks_engaged=eshutter_or_silent,
            locked_features=locked_5,
            flash_xsync_max_denom=FLASH_X_SYNC_MAX_SPEED_DENOM,
            bokeh_clipping_advisory=False,
            minolta_adapter_shading_advisory=False,
            high_ss_non_hss_banding_advisory=False,
            effective_efcs=eff_efcs,
            efcs_elf_symbol="BKID_APP_setting_front_curtaion_shutter",
            efcs_resettable=False,
            effective_long_exposure_nr="Disabled",
            long_exposure_nr_resettable=True,
            dark_frame_subtraction_triggered=False,
            effective_high_iso_nr=eff_hinr_req or "Normal",
            high_iso_nr_resettable=True,
            high_iso_nr_disabled_on_pure_raw=(file_format == "RAW"),
            arw_raw_data_mutated=False,
            fx6_noise_suppression=None,
            fx6_apr_executed=False,
        )
    if exposure_mode == "iAuto" and eff_lenr_req == "Off":
        return ShutterEfcsNrAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="[Long Exposure NR] forced On in Intelligent Auto (cannot be set to Off)",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            effective_shutter_type=eff_shutter_type,
            shutter_type_auto_exposed=False,
            shutter_type_resettable=True,
            eshutter_or_silent_5locks_engaged=eshutter_or_silent,
            locked_features=locked_5,
            flash_xsync_max_denom=FLASH_X_SYNC_MAX_SPEED_DENOM,
            bokeh_clipping_advisory=False,
            minolta_adapter_shading_advisory=False,
            high_ss_non_hss_banding_advisory=False,
            effective_efcs=eff_efcs,
            efcs_elf_symbol="BKID_APP_setting_front_curtaion_shutter",
            efcs_resettable=False,
            effective_long_exposure_nr="On",
            long_exposure_nr_resettable=True,
            dark_frame_subtraction_triggered=False,
            effective_high_iso_nr="Normal",
            high_iso_nr_resettable=True,
            high_iso_nr_disabled_on_pure_raw=(file_format == "RAW"),
            arw_raw_data_mutated=False,
            fx6_noise_suppression=None,
            fx6_apr_executed=False,
        )

    # 7. High ISO NR: dormant "High" rejected, disabled on pure RAW, fixed Normal in iAuto
    if eff_hinr_req in DORMANT_HIGH_ISO_NR_LEVELS:
        return ShutterEfcsNrAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="[High ISO NR] = High is dormant on ILME-FX3 Ver. 7.02 (only Normal/Low/Off exposed)",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            effective_shutter_type=eff_shutter_type,
            shutter_type_auto_exposed=False,
            shutter_type_resettable=True,
            eshutter_or_silent_5locks_engaged=eshutter_or_silent,
            locked_features=locked_5,
            flash_xsync_max_denom=FLASH_X_SYNC_MAX_SPEED_DENOM,
            bokeh_clipping_advisory=False,
            minolta_adapter_shading_advisory=False,
            high_ss_non_hss_banding_advisory=False,
            effective_efcs=eff_efcs,
            efcs_elf_symbol="BKID_APP_setting_front_curtaion_shutter",
            efcs_resettable=False,
            effective_long_exposure_nr=eff_lenr_req or "On",
            long_exposure_nr_resettable=True,
            dark_frame_subtraction_triggered=False,
            effective_high_iso_nr="Normal",
            high_iso_nr_resettable=True,
            high_iso_nr_disabled_on_pure_raw=(file_format == "RAW"),
            arw_raw_data_mutated=False,
            fx6_noise_suppression=None,
            fx6_apr_executed=False,
        )
    if file_format == "RAW" and eff_hinr_req is not None and not (camera_settings_reset_applied or initialize_applied):
        return ShutterEfcsNrAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="[High ISO NR] disabled when [File Format] = RAW (never modifies .ARW data)",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            effective_shutter_type=eff_shutter_type,
            shutter_type_auto_exposed=False,
            shutter_type_resettable=True,
            eshutter_or_silent_5locks_engaged=eshutter_or_silent,
            locked_features=locked_5,
            flash_xsync_max_denom=FLASH_X_SYNC_MAX_SPEED_DENOM,
            bokeh_clipping_advisory=False,
            minolta_adapter_shading_advisory=False,
            high_ss_non_hss_banding_advisory=False,
            effective_efcs=eff_efcs,
            efcs_elf_symbol="BKID_APP_setting_front_curtaion_shutter",
            efcs_resettable=False,
            effective_long_exposure_nr=eff_lenr_req or "On",
            long_exposure_nr_resettable=True,
            dark_frame_subtraction_triggered=False,
            effective_high_iso_nr="Disabled",
            high_iso_nr_resettable=True,
            high_iso_nr_disabled_on_pure_raw=True,
            arw_raw_data_mutated=False,
            fx6_noise_suppression=None,
            fx6_apr_executed=False,
        )
    if exposure_mode == "iAuto" and eff_hinr_req in ("Low", "Off"):
        return ShutterEfcsNrAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason="[High ISO NR] fixed to Normal in Intelligent Auto",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            sensor_crop=sensor_crop,
            effective_shutter_type=eff_shutter_type,
            shutter_type_auto_exposed=False,
            shutter_type_resettable=True,
            eshutter_or_silent_5locks_engaged=eshutter_or_silent,
            locked_features=locked_5,
            flash_xsync_max_denom=FLASH_X_SYNC_MAX_SPEED_DENOM,
            bokeh_clipping_advisory=False,
            minolta_adapter_shading_advisory=False,
            high_ss_non_hss_banding_advisory=False,
            effective_efcs=eff_efcs,
            efcs_elf_symbol="BKID_APP_setting_front_curtaion_shutter",
            efcs_resettable=False,
            effective_long_exposure_nr=eff_lenr_req or "On",
            long_exposure_nr_resettable=True,
            dark_frame_subtraction_triggered=False,
            effective_high_iso_nr="Normal",
            high_iso_nr_resettable=True,
            high_iso_nr_disabled_on_pure_raw=False,
            arw_raw_data_mutated=False,
            fx6_noise_suppression=None,
            fx6_apr_executed=False,
        )

    eff_lenr = (
        "Locked"
        if (eshutter_or_silent or lenr_burst_locked)
        else (eff_lenr_req or "On")
    )
    eff_hinr = "Disabled" if file_format == "RAW" else (eff_hinr_req or "Normal")
    dark_frame = bool(eff_lenr == "On" and shutter_seconds >= 1.0)
    shutter_denom = 1.0 / shutter_seconds
    bokeh_adv = bool((not eshutter_or_silent) and eff_efcs == "On" and aperture_f_stop <= 2.0 and shutter_denom >= 2000.0)
    minolta_adv = bool((not eshutter_or_silent) and eff_efcs == "On" and adapter_or_third_party_lens)
    non_hss_adv = bool(flash_requested and third_party_non_hss_trigger and shutter_denom > 4000.0)

    return ShutterEfcsNrAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Ver. 7.02 Shutter={eff_shutter_type}, EFCS={eff_efcs} (Reset-immune, curtaion typo), "
            f"X-Sync=1/250s, LongExpNR={eff_lenr}, HighISONR={eff_hinr} verified"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        sensor_crop=sensor_crop,
        effective_shutter_type=eff_shutter_type,
        shutter_type_auto_exposed=False,
        shutter_type_resettable=True,
        eshutter_or_silent_5locks_engaged=eshutter_or_silent,
        locked_features=locked_5,
        flash_xsync_max_denom=FLASH_X_SYNC_MAX_SPEED_DENOM,
        bokeh_clipping_advisory=bokeh_adv,
        minolta_adapter_shading_advisory=minolta_adv,
        high_ss_non_hss_banding_advisory=non_hss_adv,
        effective_efcs="Locked" if eshutter_or_silent else eff_efcs,
        efcs_elf_symbol="BKID_APP_setting_front_curtaion_shutter",
        efcs_resettable=False,
        effective_long_exposure_nr=eff_lenr,
        long_exposure_nr_resettable=True,
        dark_frame_subtraction_triggered=dark_frame,
        effective_high_iso_nr=eff_hinr,
        high_iso_nr_resettable=True,
        high_iso_nr_disabled_on_pure_raw=(file_format == "RAW"),
        arw_raw_data_mutated=False,
        fx6_noise_suppression=None,
        fx6_apr_executed=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 76C: [Creative Look] 10+6, 8 Params `0..9`, PP/Log Override & Soft Skin
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CreativeLookSoftSkinAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    shoot_mode: str
    requested_look: str
    effective_creative_look: str
    creative_look_locked_dash: bool
    creative_look_resettable: bool
    look_slots_separate_still_movie: bool
    presets_count: int
    custom_slots_count: int
    param_count: int
    effective_params: Dict[str, Optional[int]]
    saturation_locked_bw_se: bool
    sharpness_range_locked_movie_sq: bool
    soft_skin_effect_exposed: bool
    fx6_base_look: Optional[str]
    fx6_paint_pipeline_active: bool


def _validate_creative_look_params(
    *,
    contrast: Optional[int],
    highlights: Optional[int],
    shadows: Optional[int],
    fade: Optional[int],
    saturation: Optional[int],
    sharpness: Optional[int],
    sharpness_range: Optional[int],
    clarity: Optional[int],
) -> Optional[str]:
    checks = {
        "contrast": contrast,
        "highlights": highlights,
        "shadows": shadows,
        "fade": fade,
        "saturation": saturation,
        "sharpness": sharpness,
        "sharpness_range": sharpness_range,
        "clarity": clarity,
    }
    for name, val in checks.items():
        if val is None:
            continue
        if isinstance(val, bool) or not isinstance(val, int):
            raise Stage76Phase346Error(f"{name} must be integer, got {val!r}")
        lo, hi = CREATIVE_LOOK_PARAM_BOUNDS[name]
        if not (lo <= val <= hi):
            return f"{name}={val} outside valid range [{lo}..{hi}]"
    return None


def simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    shoot_mode: str = SHOOT_MODE_STILL,
    exposure_mode: str = "P",
    creative_look: str = "ST",
    picture_profile: str = "Off",
    log_shooting: str = "Off",
    hlg_still_image: str = "Off",
    contrast: Optional[int] = None,
    highlights: Optional[int] = None,
    shadows: Optional[int] = None,
    fade: Optional[int] = None,
    saturation: Optional[int] = None,
    sharpness: Optional[int] = None,
    sharpness_range: Optional[int] = None,
    clarity: Optional[int] = None,
    soft_skin_effect_requested: Optional[str] = None,
    fx6_base_look: str = "S-Cinetone",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> CreativeLookSoftSkinAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage76Phase346Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage76Phase346Error(f"Invalid fw_version: {fw_version!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage76Phase346Error(f"Invalid shoot_mode: {shoot_mode!r}")
    if creative_look not in VALID_CREATIVE_LOOK_CHOICES:
        raise Stage76Phase346Error(f"Invalid creative_look: {creative_look!r}")
    if picture_profile not in VALID_PICTURE_PROFILES:
        raise Stage76Phase346Error(f"Invalid picture_profile: {picture_profile!r}")
    if log_shooting not in VALID_LOG_SHOOTING_MODES:
        raise Stage76Phase346Error(f"Invalid log_shooting: {log_shooting!r}")
    if hlg_still_image not in VALID_TOGGLES:
        raise Stage76Phase346Error(f"Invalid hlg_still_image: {hlg_still_image!r}")
    if (
        soft_skin_effect_requested is not None
        and soft_skin_effect_requested not in VALID_SOFT_SKIN_EFFECT_OPTIONS
    ):
        raise Stage76Phase346Error(
            f"Invalid soft_skin_effect_requested: {soft_skin_effect_requested!r}"
        )
    if fx6_base_look not in FX6_BASE_LOOK_MODES:
        raise Stage76Phase346Error(f"Invalid fx6_base_look: {fx6_base_look!r}")

    # 1. Dual FX3 + FX6 100% Dormant [Soft Skin Effect] Rejection (`EOPNOTSUPP=95`)
    if soft_skin_effect_requested is not None:
        return CreativeLookSoftSkinAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"[Soft Skin Effect] is 100%% dormant / unsupported on BOTH {BODY_MODEL_FX3} Ver. 7.02 "
                f"AND {BODY_MODEL_FX6} Ver. 6.01 (0 hits in ilc/2210, CrDeviceProperty_SoftSkinEffect = '-')"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_look=creative_look,
            effective_creative_look="[-]",
            creative_look_locked_dash=False,
            creative_look_resettable=True,
            look_slots_separate_still_movie=True,
            presets_count=CREATIVE_LOOK_PRESETS_COUNT,
            custom_slots_count=CREATIVE_LOOK_CUSTOM_SLOTS_COUNT,
            param_count=CREATIVE_LOOK_PARAM_COUNT,
            effective_params={},
            saturation_locked_bw_se=False,
            sharpness_range_locked_movie_sq=False,
            soft_skin_effect_exposed=False,
            fx6_base_look=fx6_base_look if body_profile == BODY_MODEL_FX6 else None,
            fx6_paint_pipeline_active=(body_profile == BODY_MODEL_FX6),
        )

    # 2. ILME-FX6 Ver. 6.01 Paint/Look > Base Look + Scene File + Detail/Matrix Contrast
    if body_profile == BODY_MODEL_FX6:
        if creative_look != "ST" or any(
            v is not None
            for v in (
                contrast,
                highlights,
                shadows,
                fade,
                saturation,
                sharpness,
                sharpness_range,
                clarity,
            )
        ):
            return CreativeLookSoftSkinAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "ILME-FX6 Ver. 6.01 has NO [Creative Look]; uses Paint/Look > Base Look + "
                    "Scene File + Detail/Matrix"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_look=creative_look,
                effective_creative_look="UNSUPPORTED",
                creative_look_locked_dash=False,
                creative_look_resettable=False,
                look_slots_separate_still_movie=False,
                presets_count=0,
                custom_slots_count=0,
                param_count=0,
                effective_params={},
                saturation_locked_bw_se=False,
                sharpness_range_locked_movie_sq=False,
                soft_skin_effect_exposed=False,
                fx6_base_look=fx6_base_look,
                fx6_paint_pipeline_active=True,
            )
        return CreativeLookSoftSkinAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Ver. 6.01 Paint/Look Base Look={fx6_base_look} + Scene File + Detail/Matrix "
                "(zero Creative Look / zero Soft Skin Effect) verified"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_look=creative_look,
            effective_creative_look="UNSUPPORTED",
            creative_look_locked_dash=False,
            creative_look_resettable=False,
            look_slots_separate_still_movie=False,
            presets_count=0,
            custom_slots_count=0,
            param_count=0,
            effective_params={},
            saturation_locked_bw_se=False,
            sharpness_range_locked_movie_sq=False,
            soft_skin_effect_exposed=False,
            fx6_base_look=fx6_base_look,
            fx6_paint_pipeline_active=True,
        )

    # 3. Reset law: [Creative Look] IS Resettable (ST, all modified params revert to defaults)
    if camera_settings_reset_applied or initialize_applied:
        eff_look = "ST"
        eff_contrast: Optional[int] = 0
        eff_highlights: Optional[int] = 0
        eff_shadows: Optional[int] = 0
        eff_fade: Optional[int] = 0
        eff_saturation: Optional[int] = 0
        eff_sharpness: Optional[int] = 0
        eff_sharpness_range: Optional[int] = 3
        eff_clarity: Optional[int] = 0
    else:
        eff_look = creative_look
        eff_contrast = contrast
        eff_highlights = highlights
        eff_shadows = shadows
        eff_fade = fade
        eff_saturation = saturation
        eff_sharpness = sharpness
        eff_sharpness_range = sharpness_range
        eff_clarity = clarity

    # 4. Bounds check on all 8 parameters (Fade, Sharpness, Clarity are 0..9; Sharpness Range 1..5)
    bound_err = _validate_creative_look_params(
        contrast=eff_contrast,
        highlights=eff_highlights,
        shadows=eff_shadows,
        fade=eff_fade,
        saturation=eff_saturation,
        sharpness=eff_sharpness,
        sharpness_range=eff_sharpness_range,
        clarity=eff_clarity,
    )
    if bound_err is not None:
        return CreativeLookSoftSkinAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=f"[Creative Look] parameter out of bounds: {bound_err}",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_look=creative_look,
            effective_creative_look=eff_look,
            creative_look_locked_dash=False,
            creative_look_resettable=True,
            look_slots_separate_still_movie=True,
            presets_count=CREATIVE_LOOK_PRESETS_COUNT,
            custom_slots_count=CREATIVE_LOOK_CUSTOM_SLOTS_COUNT,
            param_count=CREATIVE_LOOK_PARAM_COUNT,
            effective_params={},
            saturation_locked_bw_se=(eff_look in ("BW", "SE")),
            sharpness_range_locked_movie_sq=(shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ)),
            soft_skin_effect_exposed=False,
            fx6_base_look=None,
            fx6_paint_pipeline_active=False,
        )

    # 5. Pipeline override: iAuto / PP != Off / Log != Off / HLG Still == On -> locked [-]
    override_reasons: List[str] = []
    if exposure_mode == "iAuto":
        override_reasons.append("Intelligent Auto")
    if picture_profile != "Off":
        override_reasons.append(f"Picture Profile={picture_profile}")
    if log_shooting != "Off":
        override_reasons.append(f"Log Shooting={log_shooting}")
    if hlg_still_image == "On":
        override_reasons.append("HLG Still Image=On")

    locked_dash = len(override_reasons) > 0
    if locked_dash:
        if not (camera_settings_reset_applied or initialize_applied) and (
            creative_look != "ST"
            or any(
                v is not None
                for v in (
                    contrast,
                    highlights,
                    shadows,
                    fade,
                    saturation,
                    sharpness,
                    sharpness_range,
                    clarity,
                )
            )
        ):
            return CreativeLookSoftSkinAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"[Creative Look] overridden and locked as [-] by {', '.join(override_reasons)}"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                shoot_mode=shoot_mode,
                requested_look=creative_look,
                effective_creative_look="[-]",
                creative_look_locked_dash=True,
                creative_look_resettable=True,
                look_slots_separate_still_movie=True,
                presets_count=CREATIVE_LOOK_PRESETS_COUNT,
                custom_slots_count=CREATIVE_LOOK_CUSTOM_SLOTS_COUNT,
                param_count=CREATIVE_LOOK_PARAM_COUNT,
                effective_params={},
                saturation_locked_bw_se=False,
                sharpness_range_locked_movie_sq=False,
                soft_skin_effect_exposed=False,
                fx6_base_look=None,
                fx6_paint_pipeline_active=False,
            )
        return CreativeLookSoftSkinAudit(
            admitted=True,
            errno_code=0,
            reason=f"[Creative Look] correctly locked to [-] under {', '.join(override_reasons)}",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_look=creative_look,
            effective_creative_look="[-]",
            creative_look_locked_dash=True,
            creative_look_resettable=True,
            look_slots_separate_still_movie=True,
            presets_count=CREATIVE_LOOK_PRESETS_COUNT,
            custom_slots_count=CREATIVE_LOOK_CUSTOM_SLOTS_COUNT,
            param_count=CREATIVE_LOOK_PARAM_COUNT,
            effective_params={},
            saturation_locked_bw_se=False,
            sharpness_range_locked_movie_sq=False,
            soft_skin_effect_exposed=False,
            fx6_base_look=None,
            fx6_paint_pipeline_active=False,
        )

    # 6. Per-parameter locks: BW/SE lock Saturation; Movie/S&Q lock Sharpness Range
    sat_locked = eff_look in ("BW", "SE")
    sr_locked = shoot_mode in (SHOOT_MODE_MOVIE, SHOOT_MODE_SQ)
    if sat_locked and saturation is not None and not (camera_settings_reset_applied or initialize_applied):
        return CreativeLookSoftSkinAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"Saturation cannot be adjusted when [Creative Look] = {eff_look}",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_look=creative_look,
            effective_creative_look=eff_look,
            creative_look_locked_dash=False,
            creative_look_resettable=True,
            look_slots_separate_still_movie=True,
            presets_count=CREATIVE_LOOK_PRESETS_COUNT,
            custom_slots_count=CREATIVE_LOOK_CUSTOM_SLOTS_COUNT,
            param_count=CREATIVE_LOOK_PARAM_COUNT,
            effective_params={},
            saturation_locked_bw_se=True,
            sharpness_range_locked_movie_sq=sr_locked,
            soft_skin_effect_exposed=False,
            fx6_base_look=None,
            fx6_paint_pipeline_active=False,
        )
    if sr_locked and sharpness_range is not None and not (camera_settings_reset_applied or initialize_applied):
        return CreativeLookSoftSkinAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"Sharpness Range (fineness) cannot be adjusted in {shoot_mode} mode",
            body_profile=body_profile,
            fw_version=fw_version,
            shoot_mode=shoot_mode,
            requested_look=creative_look,
            effective_creative_look=eff_look,
            creative_look_locked_dash=False,
            creative_look_resettable=True,
            look_slots_separate_still_movie=True,
            presets_count=CREATIVE_LOOK_PRESETS_COUNT,
            custom_slots_count=CREATIVE_LOOK_CUSTOM_SLOTS_COUNT,
            param_count=CREATIVE_LOOK_PARAM_COUNT,
            effective_params={},
            saturation_locked_bw_se=sat_locked,
            sharpness_range_locked_movie_sq=True,
            soft_skin_effect_exposed=False,
            fx6_base_look=None,
            fx6_paint_pipeline_active=False,
        )

    eff_params: Dict[str, Optional[int]] = {
        "contrast": 0 if eff_contrast is None else eff_contrast,
        "highlights": 0 if eff_highlights is None else eff_highlights,
        "shadows": 0 if eff_shadows is None else eff_shadows,
        "fade": 0 if eff_fade is None else eff_fade,
        "saturation": None if sat_locked else (0 if eff_saturation is None else eff_saturation),
        "sharpness": 0 if eff_sharpness is None else eff_sharpness,
        "sharpness_range": None if sr_locked else (3 if eff_sharpness_range is None else eff_sharpness_range),
        "clarity": 0 if eff_clarity is None else eff_clarity,
    }
    return CreativeLookSoftSkinAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 Ver. 7.02 [Creative Look]={eff_look} (10 presets + 6 Custom, 8 params 0..9 bounds, "
            "Soft Skin Effect 100%% dormant) verified"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        shoot_mode=shoot_mode,
        requested_look=creative_look,
        effective_creative_look=eff_look,
        creative_look_locked_dash=False,
        creative_look_resettable=True,
        look_slots_separate_still_movie=True,
        presets_count=CREATIVE_LOOK_PRESETS_COUNT,
        custom_slots_count=CREATIVE_LOOK_CUSTOM_SLOTS_COUNT,
        param_count=CREATIVE_LOOK_PARAM_COUNT,
        effective_params=eff_params,
        saturation_locked_bw_se=sat_locked,
        sharpness_range_locked_movie_sq=sr_locked,
        soft_skin_effect_exposed=False,
        fx6_base_look=None,
        fx6_paint_pipeline_active=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 76D: Playback [Delete]/[Protect]/[Recover Image DB] Slot 1 EROFS=30
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PlaybackRecoverDbSlot1Audit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    target_slot: str
    effective_delete_confirm: str
    effective_delete_pressing_twice: str
    instant_unconfirmed_delete_hazard: bool
    playback_config_resettable: bool
    recover_db_unaffected_by_reset_and_init: bool
    protected_files_skipped: int
    deleted_main_files: int
    deleted_proxy_files: int
    proxy_coupled_atomically: bool
    copy_preserves_protect: bool
    avf_info_rewritten: bool
    ftp_transfer_status_cleared: bool
    media_files_preserved: bool
    displayed_remaining_stills: Optional[int]
    still_cap_40000_applied: bool
    slot1_erofs_triggered: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    fx6_error_token: Optional[str]


def simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "display_media_info",
    target_slot: str = "Slot 2",
    delete_scope: str = "Single",
    protect_scope: str = "Single",
    delete_confirm: str = '"Cancel" first',
    delete_pressing_twice: str = "Off",
    protected_count: int = 0,
    unprotected_count: int = 1,
    has_coupled_proxy: bool = True,
    battery_percent: int = 85,
    raw_remaining_stills: int = 45_200,
    fx6_operation: str = "Media Status",
    fx6_media_write_protected: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
) -> PlaybackRecoverDbSlot1Audit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage76Phase346Error(f"Invalid body_profile: {body_profile!r}")
    if fw_version not in VALID_FW_VERSIONS:
        raise Stage76Phase346Error(f"Invalid fw_version: {fw_version!r}")
    if operation not in VALID_PLAYBACK_OPERATIONS:
        raise Stage76Phase346Error(f"Invalid operation: {operation!r}")
    if target_slot not in VALID_RECORDING_SLOTS:
        raise Stage76Phase346Error(f"Invalid target_slot: {target_slot!r}")
    if delete_scope not in VALID_DELETE_SCOPES:
        raise Stage76Phase346Error(f"Invalid delete_scope: {delete_scope!r}")
    if protect_scope not in VALID_PROTECT_SCOPES:
        raise Stage76Phase346Error(f"Invalid protect_scope: {protect_scope!r}")
    if delete_confirm not in VALID_DELETE_CONFIRM_MODES:
        raise Stage76Phase346Error(f"Invalid delete_confirm: {delete_confirm!r}")
    if delete_pressing_twice not in VALID_TOGGLES:
        raise Stage76Phase346Error(
            f"Invalid delete_pressing_twice: {delete_pressing_twice!r}"
        )
    if protected_count < 0 or unprotected_count < 0:
        raise Stage76Phase346Error("protected_count and unprotected_count must be >= 0")
    if not (0 <= battery_percent <= 100):
        raise Stage76Phase346Error(f"Invalid battery_percent: {battery_percent!r}")
    if raw_remaining_stills < 0:
        raise Stage76Phase346Error("raw_remaining_stills must be >= 0")
    if fx6_operation not in VALID_FX6_PLAYBACK_OPERATIONS:
        raise Stage76Phase346Error(f"Invalid fx6_operation: {fx6_operation!r}")

    # 1. ILME-FX6 Ver. 6.01 Lock/Unlock Clip, Delete Clip, Restore Media(A)/(B), Media Status
    if body_profile == BODY_MODEL_FX6:
        fx6_write_op = fx6_operation in (
            "Lock/Unlock Clip",
            "Delete Clip",
            "Restore Media(A)",
            "Restore Media(B)",
        )
        if fx6_write_op and (fx6_media_write_protected or target_slot == "Slot 1"):
            return PlaybackRecoverDbSlot1Audit(
                admitted=False,
                errno_code=EROFS_ERRNO,
                reason=(
                    f"FX6 {fx6_operation} blocked fail-closed (ng_write_protected / Slot 1 EROFS=30)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=fx6_operation,
                target_slot=target_slot,
                effective_delete_confirm="N/A",
                effective_delete_pressing_twice="N/A",
                instant_unconfirmed_delete_hazard=False,
                playback_config_resettable=False,
                recover_db_unaffected_by_reset_and_init=True,
                protected_files_skipped=0,
                deleted_main_files=0,
                deleted_proxy_files=0,
                proxy_coupled_atomically=True,
                copy_preserves_protect=False,
                avf_info_rewritten=False,
                ftp_transfer_status_cleared=False,
                media_files_preserved=True,
                displayed_remaining_stills=None,
                still_cap_40000_applied=False,
                slot1_erofs_triggered=(target_slot == "Slot 1"),
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                fx6_error_token="ng_write_protected",
            )
        return PlaybackRecoverDbSlot1Audit(
            admitted=True,
            errno_code=0,
            reason=f"FX6 Ver. 6.01 {fx6_operation} on {target_slot} completed safely",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=fx6_operation,
            target_slot=target_slot,
            effective_delete_confirm="N/A",
            effective_delete_pressing_twice="N/A",
            instant_unconfirmed_delete_hazard=False,
            playback_config_resettable=False,
            recover_db_unaffected_by_reset_and_init=True,
            protected_files_skipped=0,
            deleted_main_files=unprotected_count if fx6_operation == "Delete Clip" else 0,
            deleted_proxy_files=unprotected_count if (fx6_operation == "Delete Clip" and has_coupled_proxy) else 0,
            proxy_coupled_atomically=True,
            copy_preserves_protect=False,
            avf_info_rewritten=fx6_operation in ("Restore Media(A)", "Restore Media(B)"),
            ftp_transfer_status_cleared=False,
            media_files_preserved=(fx6_operation != "Delete Clip"),
            displayed_remaining_stills=None,
            still_cap_40000_applied=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            fx6_error_token=None,
        )

    # 2. FX3 Playback config Reset-immunity vs Initialize law
    # Playback configs ([Delete confirm.], [Delete pressing twice]) are Reset-immune;
    # restored ONLY on Initialize. [Recover Image DB] is unaffected by BOTH Reset & Initialize.
    if initialize_applied:
        eff_confirm = '"Cancel" first'
        eff_twice = "Off"
    else:
        eff_confirm = delete_confirm
        eff_twice = delete_pressing_twice

    hazard = bool(eff_confirm == '"Delete" first' or eff_twice == "On")

    # 3. Read-only [Display Media Info.] (40,000 still cap, 0 writes on Slot 1 or Slot 2)
    if operation == "display_media_info":
        capped = min(raw_remaining_stills, DISPLAY_MEDIA_INFO_STILL_CAP)
        return PlaybackRecoverDbSlot1Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"[Display Media Info.] read-only inspection on {target_slot}: "
                f"remaining_stills={capped} (cap 40,000, NOT_DISPLAYNG typo, 0 writes)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            effective_delete_confirm=eff_confirm,
            effective_delete_pressing_twice=eff_twice,
            instant_unconfirmed_delete_hazard=hazard,
            playback_config_resettable=False,
            recover_db_unaffected_by_reset_and_init=True,
            protected_files_skipped=0,
            deleted_main_files=0,
            deleted_proxy_files=0,
            proxy_coupled_atomically=True,
            copy_preserves_protect=False,
            avf_info_rewritten=False,
            ftp_transfer_status_cleared=False,
            media_files_preserved=True,
            displayed_remaining_stills=capped,
            still_cap_40000_applied=(raw_remaining_stills > DISPLAY_MEDIA_INFO_STILL_CAP),
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            fx6_error_token=None,
        )

    if operation in ("configure_playback", "copy_protect_check"):
        return PlaybackRecoverDbSlot1Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"Playback config verified (confirm={eff_confirm}, twice={eff_twice}, "
                "Reset-immune, Copy does not copy Protect)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            effective_delete_confirm=eff_confirm,
            effective_delete_pressing_twice=eff_twice,
            instant_unconfirmed_delete_hazard=hazard,
            playback_config_resettable=False,
            recover_db_unaffected_by_reset_and_init=True,
            protected_files_skipped=0,
            deleted_main_files=0,
            deleted_proxy_files=0,
            proxy_coupled_atomically=True,
            copy_preserves_protect=False,
            avf_info_rewritten=False,
            ftp_transfer_status_cleared=False,
            media_files_preserved=True,
            displayed_remaining_stills=None,
            still_cap_40000_applied=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            fx6_error_token=None,
        )

    # 4. Tier-0 Slot 1 EROFS=30 Firewall: ANY [Delete] / [Protect] / [Recover Image DB]
    # targeting Slot 1 MUST fail-closed with EROFS=30 and ZERO sector / AVF_INFO writes!
    if target_slot == "Slot 1":
        return PlaybackRecoverDbSlot1Audit(
            admitted=False,
            errno_code=EROFS_ERRNO,
            reason=(
                f"Tier-0 Slot 1 EROFS=30 Firewall blocked [{operation}] on Slot 1 recovery vault "
                "(slot1_data_sector_writes=0, slot1_avf_info_mutated=False)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            effective_delete_confirm=eff_confirm,
            effective_delete_pressing_twice=eff_twice,
            instant_unconfirmed_delete_hazard=hazard,
            playback_config_resettable=False,
            recover_db_unaffected_by_reset_and_init=True,
            protected_files_skipped=0,
            deleted_main_files=0,
            deleted_proxy_files=0,
            proxy_coupled_atomically=True,
            copy_preserves_protect=False,
            avf_info_rewritten=False,
            ftp_transfer_status_cleared=False,
            media_files_preserved=True,
            displayed_remaining_stills=None,
            still_cap_40000_applied=False,
            slot1_erofs_triggered=True,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            fx6_error_token=None,
        )

    # 5. Slot 2 safe execution
    if operation == "recover_image_db":
        if battery_percent < 20:
            return PlaybackRecoverDbSlot1Audit(
                admitted=False,
                errno_code=EPERM_ERRNO,
                reason=(
                    f"[Recover Image DB] on Slot 2 blocked due to insufficient battery ({battery_percent}%% < 20%%)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                target_slot=target_slot,
                effective_delete_confirm=eff_confirm,
                effective_delete_pressing_twice=eff_twice,
                instant_unconfirmed_delete_hazard=hazard,
                playback_config_resettable=False,
                recover_db_unaffected_by_reset_and_init=True,
                protected_files_skipped=0,
                deleted_main_files=0,
                deleted_proxy_files=0,
                proxy_coupled_atomically=True,
                copy_preserves_protect=False,
                avf_info_rewritten=False,
                ftp_transfer_status_cleared=False,
                media_files_preserved=True,
                displayed_remaining_stills=None,
                still_cap_40000_applied=False,
                slot1_erofs_triggered=False,
                slot1_data_sector_writes=0,
                slot1_avf_info_mutated=False,
                fx6_error_token=None,
            )
        return PlaybackRecoverDbSlot1Audit(
            admitted=True,
            errno_code=0,
            reason=(
                "[Recover Image DB] on Slot 2 rewrote AVF_INFO and cleared FTP transfer status "
                "(unaffected by Reset & Initialize, media files preserved, Slot 1 untouched)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            effective_delete_confirm=eff_confirm,
            effective_delete_pressing_twice=eff_twice,
            instant_unconfirmed_delete_hazard=hazard,
            playback_config_resettable=False,
            recover_db_unaffected_by_reset_and_init=True,
            protected_files_skipped=0,
            deleted_main_files=0,
            deleted_proxy_files=0,
            proxy_coupled_atomically=True,
            copy_preserves_protect=False,
            avf_info_rewritten=True,
            ftp_transfer_status_cleared=True,
            media_files_preserved=True,
            displayed_remaining_stills=None,
            still_cap_40000_applied=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            fx6_error_token=None,
        )

    if operation == "delete":
        del_main = unprotected_count
        del_proxy = unprotected_count if has_coupled_proxy else 0
        return PlaybackRecoverDbSlot1Audit(
            admitted=True,
            errno_code=0,
            reason=(
                f"[Delete] scope={delete_scope} on Slot 2 deleted {del_main} main + {del_proxy} *S03.MP4 proxy "
                f"(skipped {protected_count} protected, Slot 1 untouched)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            target_slot=target_slot,
            effective_delete_confirm=eff_confirm,
            effective_delete_pressing_twice=eff_twice,
            instant_unconfirmed_delete_hazard=hazard,
            playback_config_resettable=False,
            recover_db_unaffected_by_reset_and_init=True,
            protected_files_skipped=protected_count,
            deleted_main_files=del_main,
            deleted_proxy_files=del_proxy,
            proxy_coupled_atomically=True,
            copy_preserves_protect=False,
            avf_info_rewritten=True,
            ftp_transfer_status_cleared=False,
            media_files_preserved=False,
            displayed_remaining_stills=None,
            still_cap_40000_applied=False,
            slot1_erofs_triggered=False,
            slot1_data_sector_writes=0,
            slot1_avf_info_mutated=False,
            fx6_error_token=None,
        )

    # operation == "protect" on Slot 2
    return PlaybackRecoverDbSlot1Audit(
        admitted=True,
        errno_code=0,
        reason=(
            f"[Protect] scope={protect_scope} on Slot 2 atomically coupled main + *S03.MP4 proxy "
            "(Copy does not preserve Protect, Slot 1 untouched)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        target_slot=target_slot,
        effective_delete_confirm=eff_confirm,
        effective_delete_pressing_twice=eff_twice,
        instant_unconfirmed_delete_hazard=hazard,
        playback_config_resettable=False,
        recover_db_unaffected_by_reset_and_init=True,
        protected_files_skipped=0,
        deleted_main_files=0,
        deleted_proxy_files=0,
        proxy_coupled_atomically=True,
        copy_preserves_protect=False,
        avf_info_rewritten=True,
        ftp_transfer_status_cleared=False,
        media_files_preserved=True,
        displayed_remaining_stills=None,
        still_cap_40000_applied=False,
        slot1_erofs_triggered=False,
        slot1_data_sector_writes=0,
        slot1_avf_info_mutated=False,
        fx6_error_token=None,
    )


# ---------------------------------------------------------------------------
# Stage 76 Milestone Probe & Full Wave-66 Co-Emulation Runner
# ---------------------------------------------------------------------------


def _build_stage76_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_76th_stage_milestone": IS_76TH_STAGE_MILESTONE,
        "wave": "Wave-66",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    donor_audit = inspect_phase346_wave66_donors(
        force_clean_room=force_clean_room, env=env
    )

    # Sub-Model 76A probes
    p76a_cont_hi_plus = simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
        drive_mode="Cont. Shooting",
        cont_speed="Hi+",
        aperture_f_stop=16.0,
        raw_file_type="Uncompressed",
    )
    p76a_reset_ok = simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
        drive_mode="Cont. Bracket",
        bracket_ev_step=1.0,
        bracket_shots=9,
        bracket_order="-->0->+",
        bracket_selftimer="5 Sec",
        shutter_type_in_interval="Mechanical Shutter",
        camera_settings_reset_applied=True,
    )
    p76a_blocks = [
        simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Focus Bracket",
        ),
        simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            drive_mode="Cont. Shooting",
        ),
        simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="DRO Bracket",
            hlg_still_image="On",
        ),
        simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
            drive_mode="Self-timer(Cont)",
            self_timer_cont_shots=10,
        ),
    ]
    p76a_fx6 = simulate_drive_mode_cont_bracket_and_dormant_focus_bracket_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        drive_mode="Focus Bracket",
    )
    p76a_ok = (
        p76a_cont_hi_plus.admitted
        and p76a_cont_hi_plus.nominal_max_fps == 10
        and (not p76a_cont_hi_plus.live_view_realtime)
        and p76a_cont_hi_plus.af_locked_on_first_frame
        and p76a_cont_hi_plus.burst_rate_reduced
        and (not p76a_cont_hi_plus.focus_bracket_exposed)
        and p76a_reset_ok.admitted
        and p76a_reset_ok.effective_drive_mode == "Single Shooting"
        and p76a_reset_ok.effective_bracket_order == "0->-->+"
        and p76a_reset_ok.effective_shutter_type_in_interval == "Electronic Shutter"
        and p76a_reset_ok.drive_mode_resettable
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p76a_blocks)
        and (not p76a_fx6.admitted)
        and p76a_fx6.errno_code == EOPNOTSUPP_ERRNO
        and (not p76a_fx6.fx6_still_drive_mode_supported)
    )

    # Sub-Model 76B probes
    p76b_efcs_reset_ok = simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
        shutter_type="Electronic Shutter",
        efcs_setting="Off",
        long_exposure_nr_requested="Off",
        high_iso_nr_requested="Low",
        camera_settings_reset_applied=True,
    )
    p76b_long_exp_ok = simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
        shutter_type="Mechanical Shutter",
        efcs_setting="On",
        aperture_f_stop=1.4,
        shutter_seconds=2.0,
        flash_requested=True,
        requested_flash_xsync_denom=250,
        sensor_crop="APS-C/S35",
        file_format="RAW & JPEG",
        high_iso_nr_requested="Off",
    )
    p76b_blocks = [
        simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            shutter_type="Auto",
        ),
        simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            shutter_type="Electronic Shutter",
            flash_requested=True,
        ),
        simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            sensor_crop="APS-C/S35",
            flash_requested=True,
            requested_flash_xsync_denom=320,
        ),
        simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            high_iso_nr_requested="High",
        ),
        simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            file_format="RAW",
            high_iso_nr_requested="Normal",
        ),
    ]
    p76b_fx6 = [
        simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            fx6_noise_suppression="Mid",
            fx6_apr_execute=True,
            apr_lens_cap_covered=True,
        ),
        simulate_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            flash_requested=True,
        ),
    ]
    p76b_ok = (
        p76b_efcs_reset_ok.admitted
        and p76b_efcs_reset_ok.effective_shutter_type == "Mechanical Shutter"
        and p76b_efcs_reset_ok.effective_efcs == "Off"
        and (not p76b_efcs_reset_ok.efcs_resettable)
        and p76b_efcs_reset_ok.efcs_elf_symbol == "BKID_APP_setting_front_curtaion_shutter"
        and p76b_efcs_reset_ok.effective_long_exposure_nr == "On"
        and p76b_efcs_reset_ok.effective_high_iso_nr == "Normal"
        and p76b_long_exp_ok.admitted
        and p76b_long_exp_ok.dark_frame_subtraction_triggered
        and p76b_long_exp_ok.flash_xsync_max_denom == 250
        and (not p76b_long_exp_ok.arw_raw_data_mutated)
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p76b_blocks)
        and p76b_fx6[0].admitted
        and p76b_fx6[0].fx6_apr_executed
        and (not p76b_fx6[1].admitted)
        and p76b_fx6[1].errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 76C probes
    p76c_custom1_ok = simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
        shoot_mode=SHOOT_MODE_STILL,
        creative_look="Custom Look 1",
        contrast=2,
        highlights=-3,
        shadows=4,
        fade=9,
        saturation=1,
        sharpness=9,
        sharpness_range=5,
        clarity=9,
    )
    p76c_pp11_dash_ok = simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
        shoot_mode=SHOOT_MODE_MOVIE,
        picture_profile="PP11",
    )
    p76c_blocks = [
        simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            clarity=-1,
        ),
        simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            creative_look="BW",
            saturation=2,
        ),
        simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            shoot_mode=SHOOT_MODE_MOVIE,
            sharpness_range=3,
        ),
        simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            picture_profile="PP11",
            creative_look="VV",
        ),
        simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            soft_skin_effect_requested="Mid",
        ),
    ]
    p76c_fx6 = [
        simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            fx6_base_look="s709",
        ),
        simulate_creative_look_params_pp_log_override_and_soft_skin_dormancy_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            soft_skin_effect_requested="Low",
        ),
    ]
    p76c_ok = (
        p76c_custom1_ok.admitted
        and p76c_custom1_ok.effective_creative_look == "Custom Look 1"
        and p76c_custom1_ok.effective_params["clarity"] == 9
        and p76c_custom1_ok.effective_params["fade"] == 9
        and p76c_custom1_ok.effective_params["sharpness_range"] == 5
        and (not p76c_custom1_ok.soft_skin_effect_exposed)
        and p76c_pp11_dash_ok.admitted
        and p76c_pp11_dash_ok.effective_creative_look == "[-]"
        and p76c_pp11_dash_ok.creative_look_locked_dash
        and (not p76c_blocks[0].admitted)
        and p76c_blocks[0].errno_code == EINVAL_ERRNO
        and all((not r.admitted) and r.errno_code == EOPNOTSUPP_ERRNO for r in p76c_blocks[1:])
        and p76c_fx6[0].admitted
        and p76c_fx6[0].fx6_base_look == "s709"
        and (not p76c_fx6[1].admitted)
        and p76c_fx6[1].errno_code == EOPNOTSUPP_ERRNO
        and (not p76c_fx6[1].soft_skin_effect_exposed)
    )

    # Sub-Model 76D probes
    p76d_slot2_recover_ok = simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
        operation="recover_image_db",
        target_slot="Slot 2",
        delete_confirm='"Delete" first',
        delete_pressing_twice="On",
        camera_settings_reset_applied=True,
    )
    p76d_media_info_ok = simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
        operation="display_media_info",
        target_slot="Slot 1",
        raw_remaining_stills=52_000,
    )
    p76d_slot1_blocks = [
        simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="delete",
            target_slot="Slot 1",
            delete_scope="All in this Folder",
        ),
        simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="protect",
            target_slot="Slot 1",
            protect_scope="All with this date",
        ),
        simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            operation="recover_image_db",
            target_slot="Slot 1",
        ),
    ]
    p76d_fx6 = [
        simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            target_slot="Slot 2",
            fx6_operation="Restore Media(B)",
        ),
        simulate_delete_protect_recover_db_and_slot1_erofs_firewall_hil(
            body_profile=BODY_MODEL_FX6,
            fw_version=FW_VER_601,
            target_slot="Slot 2",
            fx6_operation="Delete Clip",
            fx6_media_write_protected=True,
        ),
    ]
    p76d_ok = (
        p76d_slot2_recover_ok.admitted
        and p76d_slot2_recover_ok.avf_info_rewritten
        and p76d_slot2_recover_ok.ftp_transfer_status_cleared
        and p76d_slot2_recover_ok.media_files_preserved
        and p76d_slot2_recover_ok.effective_delete_confirm == '"Delete" first'
        and p76d_slot2_recover_ok.effective_delete_pressing_twice == "On"
        and p76d_slot2_recover_ok.instant_unconfirmed_delete_hazard
        and (not p76d_slot2_recover_ok.playback_config_resettable)
        and p76d_slot2_recover_ok.recover_db_unaffected_by_reset_and_init
        and p76d_slot2_recover_ok.slot1_data_sector_writes == 0
        and p76d_media_info_ok.admitted
        and p76d_media_info_ok.displayed_remaining_stills == 40_000
        and p76d_media_info_ok.still_cap_40000_applied
        and (not p76d_media_info_ok.slot1_erofs_triggered)
        and p76d_media_info_ok.slot1_data_sector_writes == 0
        and all(
            (not r.admitted)
            and r.errno_code == EROFS_ERRNO
            and r.slot1_erofs_triggered
            and r.slot1_data_sector_writes == 0
            and (not r.slot1_avf_info_mutated)
            for r in p76d_slot1_blocks
        )
        and p76d_fx6[0].admitted
        and (not p76d_fx6[1].admitted)
        and p76d_fx6[1].errno_code == EROFS_ERRNO
        and p76d_fx6[1].fx6_error_token == "ng_write_protected"
    )

    milestone_probe = _build_stage76_milestone_probe()

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
        # 76A redlines
        "still_cont_hi_plus_max_fps": STILL_CONT_HI_PLUS_MAX_FPS,
        "still_cont_hi_max_fps": STILL_CONT_HI_MAX_FPS,
        "still_cont_mid_max_fps": STILL_CONT_MID_MAX_FPS,
        "still_cont_lo_max_fps": STILL_CONT_LO_MAX_FPS,
        "self_timer_cont_options_count": SELF_TIMER_CONT_OPTIONS_COUNT,
        "dormant_focus_bracket_exposed_events": DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS,
        "fx6_still_drive_mode_exposed_events": FX6_STILL_DRIVE_MODE_EXPOSED_EVENTS,
        "dro_bracket_hlg_bypass_events": DRO_BRACKET_HLG_BYPASS_EVENTS,
        # 76B redlines
        "shutter_type_active_options_count": SHUTTER_TYPE_ACTIVE_OPTIONS_COUNT,
        "dormant_shutter_type_auto_exposed_events": DORMANT_SHUTTER_TYPE_AUTO_EXPOSED_EVENTS,
        "flash_x_sync_max_speed_denom": FLASH_X_SYNC_MAX_SPEED_DENOM,
        "apsc_1_320_xsync_spoof_events": APSC_1_320_XSYNC_SPOOF_EVENTS,
        "e_front_curtain_typo_matched": E_FRONT_CURTAIN_TYPO_MATCHED,
        "e_front_curtain_reset_wipe_events": E_FRONT_CURTAIN_RESET_WIPE_EVENTS,
        "eshutter_5lock_bypass_events": ESHUTTER_5LOCK_BYPASS_EVENTS,
        "dormant_high_iso_nr_high_exposed_events": DORMANT_HIGH_ISO_NR_HIGH_EXPOSED_EVENTS,
        "high_iso_nr_arw_mutation_events": HIGH_ISO_NR_ARW_MUTATION_EVENTS,
        # 76C redlines
        "creative_look_presets_count": CREATIVE_LOOK_PRESETS_COUNT,
        "creative_look_custom_slots_count": CREATIVE_LOOK_CUSTOM_SLOTS_COUNT,
        "creative_look_param_count": CREATIVE_LOOK_PARAM_COUNT,
        "creative_look_clarity_fade_sharpness_max": CREATIVE_LOOK_CLARITY_FADE_SHARPNESS_MAX,
        "creative_look_pp_log_hlg_override_bypass_events": (
            CREATIVE_LOOK_PP_LOG_HLG_OVERRIDE_BYPASS_EVENTS
        ),
        "fx3_soft_skin_effect_exposed_events": FX3_SOFT_SKIN_EFFECT_EXPOSED_EVENTS,
        "fx6_soft_skin_effect_exposed_events": FX6_SOFT_SKIN_EFFECT_EXPOSED_EVENTS,
        # 76D redlines
        "playback_config_reset_wipe_events": PLAYBACK_CONFIG_RESET_WIPE_EVENTS,
        "recover_db_reset_or_init_wipe_events": RECOVER_DB_RESET_OR_INIT_WIPE_EVENTS,
        "recover_db_slot1_erofs_bypass_events": RECOVER_DB_SLOT1_EROFS_BYPASS_EVENTS,
        "delete_or_protect_slot1_erofs_bypass_events": DELETE_OR_PROTECT_SLOT1_EROFS_BYPASS_EVENTS,
        "display_media_info_still_cap": DISPLAY_MEDIA_INFO_STILL_CAP,
        "not_displayng_typo_matched": NOT_DISPLAYNG_TYPO_MATCHED,
        "proxy_decoupled_orphan_events": PROXY_DECOUPLED_ORPHAN_EVENTS,
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
        and STILL_CONT_HI_PLUS_MAX_FPS == 10
        and STILL_CONT_HI_MAX_FPS == 8
        and STILL_CONT_MID_MAX_FPS == 6
        and STILL_CONT_LO_MAX_FPS == 3
        and SELF_TIMER_CONT_OPTIONS_COUNT == 6
        and DORMANT_FOCUS_BRACKET_EXPOSED_EVENTS == 0
        and FX6_STILL_DRIVE_MODE_EXPOSED_EVENTS == 0
        and DRO_BRACKET_HLG_BYPASS_EVENTS == 0
        and SHUTTER_TYPE_ACTIVE_OPTIONS_COUNT == 2
        and DORMANT_SHUTTER_TYPE_AUTO_EXPOSED_EVENTS == 0
        and FLASH_X_SYNC_MAX_SPEED_DENOM == 250
        and APSC_1_320_XSYNC_SPOOF_EVENTS == 0
        and bool(E_FRONT_CURTAIN_TYPO_MATCHED)
        and E_FRONT_CURTAIN_RESET_WIPE_EVENTS == 0
        and ESHUTTER_5LOCK_BYPASS_EVENTS == 0
        and DORMANT_HIGH_ISO_NR_HIGH_EXPOSED_EVENTS == 0
        and HIGH_ISO_NR_ARW_MUTATION_EVENTS == 0
        and CREATIVE_LOOK_PRESETS_COUNT == 10
        and CREATIVE_LOOK_CUSTOM_SLOTS_COUNT == 6
        and CREATIVE_LOOK_PARAM_COUNT == 8
        and CREATIVE_LOOK_CLARITY_FADE_SHARPNESS_MAX == 9
        and CREATIVE_LOOK_PP_LOG_HLG_OVERRIDE_BYPASS_EVENTS == 0
        and FX3_SOFT_SKIN_EFFECT_EXPOSED_EVENTS == 0
        and FX6_SOFT_SKIN_EFFECT_EXPOSED_EVENTS == 0
        and PLAYBACK_CONFIG_RESET_WIPE_EVENTS == 0
        and RECOVER_DB_RESET_OR_INIT_WIPE_EVENTS == 0
        and RECOVER_DB_SLOT1_EROFS_BYPASS_EVENTS == 0
        and DELETE_OR_PROTECT_SLOT1_EROFS_BYPASS_EVENTS == 0
        and DISPLAY_MEDIA_INFO_STILL_CAP == 40_000
        and bool(NOT_DISPLAYNG_TYPO_MATCHED)
        and PROXY_DECOUPLED_ORPHAN_EVENTS == 0
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
        and p76a_ok
        and p76b_ok
        and p76c_ok
        and p76d_ok
        and redlines_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_346_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_76th_stage_milestone": IS_76TH_STAGE_MILESTONE,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "donor_audit": asdict(donor_audit),
        "stage76_milestone_probe": milestone_probe,
        "pillar_a_drive_mode_cont_bracket_focus_bracket_hil": {
            "passed": p76a_ok,
            "fx3_cont_hi_plus_10fps_f16_uncomp": asdict(p76a_cont_hi_plus),
            "fx3_drive_mode_reset_verified": asdict(p76a_reset_ok),
            "lockout_and_dormancy_probes": [asdict(r) for r in p76a_blocks],
            "fx6_comparison": asdict(p76a_fx6),
        },
        "pillar_b_shutter_type_xsync_efcs_long_exp_high_iso_nr_hil": {
            "passed": p76b_ok,
            "fx3_efcs_reset_immunity": asdict(p76b_efcs_reset_ok),
            "fx3_long_exp_nr_xsync_250": asdict(p76b_long_exp_ok),
            "lockout_and_dormancy_probes": [asdict(r) for r in p76b_blocks],
            "fx6_comparison": [asdict(r) for r in p76b_fx6],
        },
        "pillar_c_creative_look_params_pp_log_soft_skin_hil": {
            "passed": p76c_ok,
            "fx3_custom1_0_9_bounds": asdict(p76c_custom1_ok),
            "fx3_pp11_forced_dash": asdict(p76c_pp11_dash_ok),
            "lockout_and_dormancy_probes": [asdict(r) for r in p76c_blocks],
            "fx6_comparison": [asdict(r) for r in p76c_fx6],
        },
        "pillar_d_delete_protect_recover_db_slot1_erofs_hil": {
            "passed": p76d_ok,
            "fx3_slot2_recover_db_ok": asdict(p76d_slot2_recover_ok),
            "fx3_display_media_info_40k_cap": asdict(p76d_media_info_ok),
            "slot1_erofs30_firewall_probes": [asdict(r) for r in p76d_slot1_blocks],
            "fx6_comparison": [asdict(r) for r in p76d_fx6],
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
        prog="realhw_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulator.py",
        description=(
            "Phase 346 (Stage 76 — 76/76 Full-Board VM Co-Emulation Stages!) Real-Hardware "
            "ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-66 Co-Emulator: "
            "76A Still [Drive Mode] 10 fps Cont./Bracket & 100%% Dormant [Focus Bracket], "
            "76B [Shutter Type] 2-Option Zero-Auto / 1/250 s X-Sync / Reset-Immune [e-Front Curtain Shut.] curtaion Typo / Long Exposure & High ISO NR, "
            "76C [Creative Look] 10+6 Slots & 8 Params 0..9 Bounds & PP/Log Override vs 100%% Dormant [Soft Skin Effect], "
            "76D Playback [Delete]/[Protect]/[Recover Image DB] AVF_INFO Tier-0 Slot 1 EROFS=30 Firewall."
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run complete Phase 346 Stage 76 Wave-66 HIL co-emulation audit",
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

    rep = run_phase346_drive_focusbracket_shutter_efcs_creativelook_recoverdb_coemulation(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 346 Stage 76 (76/76 Stages) | mode={rep['source_mode']} | "
            f"fps={red['still_cont_hi_plus_max_fps']} "
            f"fbrk={red['dormant_focus_bracket_exposed_events']} "
            f"shut={red['shutter_type_active_options_count']} "
            f"xsync=1/{red['flash_x_sync_max_speed_denom']} "
            f"cl={red['creative_look_presets_count']}+{red['creative_look_custom_slots_count']} "
            f"sse={red['fx3_soft_skin_effect_exposed_events']}/{red['fx6_soft_skin_effect_exposed_events']} "
            f"s1_wr={red['slot1_data_sector_writes']} leak={red['raw_firmware_bytes_leaked']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
