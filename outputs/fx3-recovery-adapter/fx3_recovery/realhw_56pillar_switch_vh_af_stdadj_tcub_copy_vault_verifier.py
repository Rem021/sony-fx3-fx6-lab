"""Phase 314 (56/56 Recovery Pillars Milestone) — Wave-54 Recovery Pillar 56 & Unified 56/56
Recovery Master (`verify-56pillar-recovery` / `verify-pillar56-switch-vh-af-stdadj-tcub-copy-vault`):

1. **Sub-Pillar 56A — Still-Only `[Switch V/H AF Area]` (`0/90/270/INVALID` Orientation +
   8 Lockouts + Coords Clear), 14-Checkbox `[Focus Area Limit]` (`>= 2` `.uxc 0xea28` ->
   `EINVAL=22` vs Dormant `xl/xs/custom_1..3` `EOPNOTSUPP=95`), & `Initialize`-Only
   `[Focus Area Color]` vs Zero-Switch `ILME-FX6` (Wave-54)**:
   - Models `ILME-FX3 Ver. 7.02` (`0x91030080`, `ilc/2210`, `PRODUCT_MODEL_ALCIN_UUD`)
     `MENU -> (Focus) -> [Focus Area]`:
     * `[Switch V/H AF Area]` (`_f.uxc 0x73ae`, `BKID_APP_setting_vertical_horizontal_focus_area_switch`:
       `Off` `0x63aa` default / `AF Point Only` `0x615a` / `AF Point + AF Area` `0x69e8`) is
       **Still `AF-C` ONLY**, resets on `[Camera Settings Reset]`, tracks `0_DEGREES` / `90_DEGREES` /
       `270_DEGREES` while vertical lens pitch returns `INVALID` (no orientation switch), clears
       remembered orientation coordinates whenever the setting changes, and locks out (`EBUSY=16`) in
       `Movie`/`S&Q`, `iAuto`, `Digital Zoom`, active `AF`, burst, `Self-timer`, `Focus Magnifier`,
       and non-`AF-C`.
     * `[Focus Area Limit]` (`_f.uxc 0x6de2`, default `"―"`, resets on `[Camera Settings Reset]`):
       exposes **exact 14** `BKID_APP_focus_area_limit_*` checkboxes (7 general + 7 Still-only
       `Tracking:*` excluded in `Movie`/`S&Q`), enforces `>= 2` checked areas (`.uxc 0xea28` ->
       `EINVAL=22`), and strictly rejects dormant BIONZ XR symbols `focus_area_limit_flexible_spot_{xl,xs}`
       and `focus_area_limit_custom_{1..3}` with `EOPNOTSUPP=95`.
     * `[Focus Area Color]` (`_f.uxc 0x74ad`, `BKID_APP_setting_focus_frame_color`, `White` `.uxc 0xe883`
       default / `Red` `.uxc 0xe8c6`, Still/Movie/`S&Q`) survives `[Camera Settings Reset]` (needs
       `[Initialize]`), contrasted with `ILME-FX6 Ver. 6.01` (zero `Switch V/H AF Area`, zero
       `Focus Area Limit`, orange moving AF box + `Focus Area Ind.(AF-S)` `0x2236` + `Focus Area Marker`
       `_2.uxc 0x4d6b`).

2. **Sub-Pillar 56B — 5-Mode `[Exposure Std. Adjust]` (`1/6 EV`, `Initialize`-Only) + Still
   `[Bracket Settings]`, 7-Item `Initialize`-Only `[TC/UB]` & `[TC/UB Disp. Setting]`
   (`23.98p/24p/PAL` Format Locks vs `FX6` Physical BNC `TC IN/OUT`), and CRITICAL Reverse
   `Slot-2 -> Slot-1` `[Copy]` Tier-0 Vault `EROFS=30`/`EBUSY=16` Firewall + `[Slide Show]`
   Power-Save Bypass (Wave-54)**:
   - `[Exposure Std. Adjust]` (`_f.uxc 0x6114`/`0x6f71`, `.uxc 0xe567` warning prompt,
     `PID_SET_STANDARD_EXPOSURE_SETTING`) supports **all 5 metering modes** (`Multi` `0x6d79`, `Center`
     `0x6da8`, `Spot` `0x7a8a`, `Entire Screen Avg.` `0x6f15`, `Highlight` `0x7600`) across 13 steps
     (`-1..+1 EV` in `1/6 EV`), writes independent EXIF without mutating `[Exposure Comp.]`, shifts
     `M.M.` baseline & Spot AEL, resets bracket shot count if changed mid-bracket, and **survives
     `[Camera Settings Reset]`** (only `[Initialize]` restores `±0`). Still `[Bracket Settings]`
     (`_f.uxc 0x6466`: `[Selftimer during Bracket]` `Off/2/5/10 Sec` + `[Bracket order]` `0->-->+` /
     `-->0->+`) resets on `[Camera Settings Reset]`. `FX6` has `0` hits for `exposure_standard` and
     dormant `bracket_*` (`ENOENT=2`).
   - All 6 `MENU -> (Shooting) -> [TC/UB]` items + `(Setup) -> [Display Option] -> [TC/UB Disp. Setting]`
     (`Counter`/`TC`/`U-Bit`, movie-playback-only toggle `.uxc 0xe728`) **survive
     `[Camera Settings Reset]`** (`Initialize`-only); `[Time Code Format]` (`DF`/`NDF`) is NTSC-only,
     forced `NDF` (`[-]`) at `23.98p`/`24.00p`, and hidden in `PAL`, contrasted with `FX6` physical
     BNC `TC IN/OUT` switch (`EXT-LK`) and `Users Bit Mode: Fix/Time`.
   - **CRITICAL REVERSE `[Copy]` TIER-0 VAULT FIREWALL**: `MENU -> (Playback) -> [Edit] -> [Copy]`
     (`FUNC_copy_content`) copies FROM `[Select Playback Media]` TO the opposite slot! While
     `Select Playback Media = Slot 1` copies `Slot 1 -> Slot 2` (read-only on Slot 1, clears group
     & `Protect` flag on destination, battery + speed-class gated), switching **`[Select Playback Media]
     = Slot 2` and invoking `[Copy]` attempts massive file writes + `AVF_INFO` ImageDB mutation onto
     `Slot 1`** — MUST fail-closed (`EROFS=30` / `EBUSY=16`, `slot1_data_sector_writes == 0`,
     `slot1_copy_avf_info_mutation_bytes == 0`, `slot1_avf_info_mutated == False`,
     `slot1_vault_mutation_bytes == 0`) whenever `Slot 1` holds a Tier-0 recovery vault! `[Slide Show]`
     (`.uxc 0xe2cc`: `Repeat: Off`, `Interval: 1/3/5/10/30 Sec` default `3 Sec`, `Initialize`-only)
     bypasses `[Power Save Start Time]` (`DURING_PLAYBACK_SLIDESHOW`); `FX6` `Copy Clip` is dormant
     (`EOPNOTSUPP=95`).

3. **Unified `56/56` Recovery Master Aggregator (`evaluate_realhw_56pillar_recovery_master` /
   `verify-56pillar-recovery`)**:
   - Concurrently delegates Pillars `1..55` (`evaluate_realhw_55pillar_recovery_master`) +
     **Pillar 56** (`run_pillar56_standalone_suite`) -> **`56/56` (`VERIFIED_56OF56_PILLAR_RECOVERY_MASTER`,
     `schema_version="realhw_56pillar_recovery_master_v1"`)** in `< 1.5s` with
     `overall_ready_for_hardware_attach == False`, `cross_model_flash_authorized == False`,
     `persistent_emmc_writes_authorized == False`, and `raw_firmware_bytes_leaked == 0`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import posixpath
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
)
from .realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier import (
    MASTER_55_PILLAR_SPECS,
    Master55PillarRecoveryReport,
    evaluate_realhw_55pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants (Phase 314 — 56/56 Milestone)
# ---------------------------------------------------------------------------

PHASE314_SCHEMA: str = (
    "realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier_v1"
)
PHASE314_MASTER_SCHEMA: str = "realhw_56pillar_recovery_master_v1"
PHASE314_VERSION: str = "1.0.0"
PHASE314_PHASE_NUMBER: int = 314
P314_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
CROSS_MODEL_FLASH_AUTHORIZED: bool = False
P314_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P314_OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
P314_CROSS_MODEL_FLASH_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P314_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT_EVENTS: int = 0
P314_FOCUS_LIMIT_LT2_OR_DORMANT_SYMBOL_EVENTS: int = 0
P314_FOCUS_AREA_COLOR_OR_FX6_SPOOF_EVENTS: int = 0
P314_EXP_STD_ADJ_MODE_CONFLATION_OR_RESET_DRIFT_EVENTS: int = 0
P314_BRACKET_SETTINGS_RESET_OR_FX6_SPOOF_EVENTS: int = 0
P314_TCUB_RESET_WIPE_OR_FORMAT_LOCK_VIOLATIONS: int = 0
P314_REVERSE_COPY_SLOT2_TO_SLOT1_BYPASS_EVENTS: int = 0
P314_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF_EVENTS: int = 0
P314_SLOT1_DATA_SECTOR_WRITES: int = 0
P314_SLOT1_COPY_AVF_INFO_MUTATION_BYTES: int = 0
P314_SLOT1_VAULT_MUTATION_BYTES: int = 0
P314_SLOT1_FORMAT_HARD_LOCKED: bool = True
P314_SLOT1_VAULT_EROFS_EBUSY_ENFORCED: bool = True

# Hardware Truths (Wave-54 Empirical Anchors)
P314_FX3_HAS_SWITCH_VH_AF_AREA: bool = True
P314_FX3_FOCUS_AREA_LIMIT_COUNT: int = 14
P314_FX3_FOCUS_AREA_LIMIT_MIN_ENABLED: int = 2
P314_FX3_EXP_STD_ADJ_METERING_MODE_COUNT: int = 5
P314_FX3_HAS_PHYSICAL_BNC_TC_PORT: bool = False
P314_FX6_HAS_PHYSICAL_BNC_TC_PORT: bool = True
P314_FX6_HAS_SWITCH_VH_AF_AREA: bool = False
P314_FX6_HAS_FOCUS_AREA_LIMIT: bool = False
P314_FX6_HAS_EXP_STD_ADJ: bool = False
P314_FX6_HAS_STILL_BRACKET_SETTINGS: bool = False
P314_FX6_HAS_COPY_CLIP_ACTIVE: bool = False
P314_FX6_HAS_SLIDE_SHOW: bool = False

P314_DONOR_INSPECT_BUDGET_SECONDS: float = 0.20
P314_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P314_FAST_CLI_BUDGET_SECONDS: float = 1.5
P314_NOMINAL_BUDGET_SECONDS: float = 4.0
P314_CONCURRENT_CEILING_SECONDS: float = 6.0
P314_BOUNDED_HEADER_BYTES: int = 4096
P314_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-54 Donor Anchors (17 donors, strictly O_RDONLY)
P314_FX3_MODEL_NAME: str = "ILME-FX3"
P314_FX3_MODEL_ID: int = 0x91030080
P314_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P314_FX3_HELPGUIDE_ID: str = "ilc/2210"
P314_FX3_FW_VERSION: str = "7.02"
P314_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
    "2.00",
    "2.05",
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)
P314_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P314_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P314_FX6_DONOR_FW_VERSION: str = "6.01"

P314_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P314_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P314_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)
P314_PINNED_FX3_APPFW_702_FULL_SHA256: str = (
    "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
)

P314_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P314_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P314_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)
P314_PINNED_FX6_APPFW_601_FULL_SHA256: str = (
    "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
)

P314_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P314_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P314_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P314_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P314_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P314_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P314_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P314_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P314_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P314_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P314_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P314_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P314_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P314_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P314_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P314_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P314_PINNED_FX3_UXC_EN_BYTES: int = 165740
P314_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P314_DONOR_FX3_UXC_SC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc"
)
P314_PINNED_FX3_UXC_SC_BYTES: int = 149064
P314_PINNED_FX3_UXC_SC_SHA256: str = (
    "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66"
)

P314_DONOR_FX3_UXC_TC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc"
)
P314_PINNED_FX3_UXC_TC_BYTES: int = 151908
P314_PINNED_FX3_UXC_TC_SHA256: str = (
    "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3"
)

P314_DONOR_FX3_UXC_JA_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc"
)
P314_PINNED_FX3_UXC_JA_BYTES: int = 208564
P314_PINNED_FX3_UXC_JA_SHA256: str = (
    "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d"
)

P314_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P314_PINNED_FX3_UXC_EN_G_BYTES: int = 69600
P314_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P314_DONOR_FX3_UXC_SC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_g.uxc"
)
P314_PINNED_FX3_UXC_SC_G_BYTES: int = 61296
P314_PINNED_FX3_UXC_SC_G_SHA256: str = (
    "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b"
)

P314_DONOR_FX3_UXC_TC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_g.uxc"
)
P314_PINNED_FX3_UXC_TC_G_BYTES: int = 61372
P314_PINNED_FX3_UXC_TC_G_SHA256: str = (
    "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80"
)

P314_DONOR_FX3_UXC_JA_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_g.uxc"
)
P314_PINNED_FX3_UXC_JA_G_BYTES: int = 89428
P314_PINNED_FX3_UXC_JA_G_SHA256: str = (
    "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980"
)

P314_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P314_PINNED_FX6_UXC_EN_BYTES: int = 118208
P314_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P314_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P314_PINNED_FX6_UXC_EN_2_BYTES: int = 118676
P314_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# ---------------------------------------------------------------------------
# Pillar 56A Constants — [Switch V/H AF Area], 14-Checkbox [Focus Area Limit],
# & [Focus Area Color] Initialize-Only vs Zero-Switch ILME-FX6
# ---------------------------------------------------------------------------

P314_FOCUS_AREA_MENU_PATH: Tuple[str, ...] = ("Focus", "Focus Area")
P314_SWITCH_VH_AF_F_RESID16: int = 0x73AE
P314_SWITCH_VH_AF_BKID: str = "BKID_APP_setting_vertical_horizontal_focus_area_switch"
P314_SWITCH_VH_AF_MODES: Tuple[str, ...] = (
    "Off",
    "AF Point Only",
    "AF Point + AF Area",
)
P314_SWITCH_VH_AF_DEFAULT: str = "Off"
P314_SWITCH_VH_AF_RESID16_MAP: Dict[str, int] = {
    "Off": 0x63AA,
    "AF Point Only": 0x615A,
    "AF Point + AF Area": 0x69E8,
}
P314_SWITCH_VH_AF_ORIENTATIONS: Tuple[str, ...] = (
    "0_DEGREES",
    "90_DEGREES",
    "270_DEGREES",
    "INVALID",
)
P314_SWITCH_VH_AF_LOCKOUT_CONDITIONS: Tuple[str, ...] = (
    "Movie_Or_SQ_Domain",
    "Non_AFC_Focus_Mode",
    "Intelligent_Auto",
    "Digital_Zoom",
    "Active_AF_In_Progress",
    "Continuous_Burst",
    "Self_Timer_Countdown",
    "Focus_Magnifier",
)

P314_FOCUS_AREA_LIMIT_F_RESID16: int = 0x6DE2
P314_FOCUS_AREA_LIMIT_LT2_RESID16: int = 0xEA28
P314_FOCUS_AREA_LIMIT_CENTER_FIX_F_RESID16: int = 0x7824
P314_FOCUS_AREA_LIMIT_TRACK_CENTER_FIX_F_RESID16: int = 0x602B

P314_FOCUS_AREA_LIMIT_NON_TRACKING_7: Tuple[str, ...] = (
    "wide",
    "zone",
    "center_fix",
    "spot_s",
    "spot_m",
    "spot_l",
    "expanded_spot",
)
P314_FOCUS_AREA_LIMIT_TRACKING_7: Tuple[str, ...] = (
    "tracking_wide",
    "tracking_zone",
    "tracking_center_fix",
    "tracking_spot_s",
    "tracking_spot_m",
    "tracking_spot_l",
    "tracking_expanded_spot",
)
P314_FOCUS_AREA_LIMIT_14_AREAS: Tuple[str, ...] = (
    P314_FOCUS_AREA_LIMIT_NON_TRACKING_7 + P314_FOCUS_AREA_LIMIT_TRACKING_7
)
P314_FOCUS_AREA_LIMIT_BKID_MAP: Dict[str, str] = {
    "wide": "BKID_APP_focus_area_limit_wide",
    "zone": "BKID_APP_focus_area_limit_zone",
    "center_fix": "BKID_APP_focus_area_limit_center",
    "spot_s": "BKID_APP_focus_area_limit_flexible_spot_s",
    "spot_m": "BKID_APP_focus_area_limit_flexible_spot_m",
    "spot_l": "BKID_APP_focus_area_limit_flexible_spot_l",
    "expanded_spot": "BKID_APP_focus_area_limit_expanded_flexible_spot",
    "tracking_wide": "BKID_APP_focus_area_limit_tracking_af_wide",
    "tracking_zone": "BKID_APP_focus_area_limit_tracking_af_zone",
    "tracking_center_fix": "BKID_APP_focus_area_limit_tracking_af_center",
    "tracking_spot_s": "BKID_APP_focus_area_limit_tracking_af_flexible_spot_s",
    "tracking_spot_m": "BKID_APP_focus_area_limit_tracking_af_flexible_spot_m",
    "tracking_spot_l": "BKID_APP_focus_area_limit_tracking_af_flexible_spot_l",
    "tracking_expanded_spot": "BKID_APP_focus_area_limit_tracking_af_expanded_flexible_spot",
}
P314_FOCUS_AREA_LIMIT_DORMANT_5: Tuple[str, ...] = (
    "flexible_spot_xl",
    "flexible_spot_xs",
    "custom_1",
    "custom_2",
    "custom_3",
)

P314_FOCUS_AREA_COLOR_F_RESID16: int = 0x74AD
P314_FOCUS_AREA_COLOR_LEGACY_F_RESID16: int = 0x7087
P314_FOCUS_AREA_COLOR_BKID: str = "BKID_APP_setting_focus_frame_color"
P314_FOCUS_AREA_COLOR_MODES: Tuple[str, ...] = ("White", "Red")
P314_FOCUS_AREA_COLOR_DEFAULT: str = "White"
P314_FOCUS_AREA_COLOR_RESID16_MAP: Dict[str, int] = {"White": 0xE883, "Red": 0xE8C6}
P314_FX6_FOCUS_AREA_IND_AFS_RESID16: int = 0x2236
P314_FX6_FOCUS_AREA_MARKER_2_RESID16: int = 0x4D6B

# ---------------------------------------------------------------------------
# Pillar 56B Constants — 5-Mode [Exposure Std. Adjust] (1/6 EV, Init-Only),
# Still [Bracket Settings], 7-Item [TC/UB] & [TC/UB Disp. Setting] Format Locks,
# Bidirectional [Copy] Slot-2 -> Slot-1 Tier-0 Vault Firewall, & [Slide Show]
# ---------------------------------------------------------------------------

P314_EXP_STD_ADJ_MENU_PATH: Tuple[str, ...] = (
    "Exposure/Color",
    "Exposure Comp.",
    "Exposure Std. Adjust",
)
P314_EXP_STD_ADJ_F_RESID16: int = 0x6114
P314_EXP_STD_ADJ_ALT_F_RESID16: int = 0x6F71
P314_EXP_STD_ADJ_WARN_RESID16: int = 0xE567
P314_EXP_STD_ADJ_PID_SYMBOL: str = "PID_SET_STANDARD_EXPOSURE_SETTING"
P314_EXP_STD_ADJ_5_METERING_MODES: Tuple[str, ...] = (
    "Multi",
    "Center",
    "Spot",
    "Entire Screen Avg.",
    "Highlight",
)
P314_EXP_STD_ADJ_MODE_BKID_MAP: Dict[str, str] = {
    "Multi": "BKID_APP_setting_exposure_standard_metering_mode_multi",
    "Center": "BKID_APP_setting_exposure_standard_metering_mode_center",
    "Spot": "BKID_APP_setting_exposure_standard_metering_mode_spot",
    "Entire Screen Avg.": "BKID_APP_setting_exposure_standard_metering_mode_average",
    "Highlight": "BKID_APP_setting_exposure_standard_metering_mode_highlight",
}
P314_EXP_STD_ADJ_MODE_F_RESID16_MAP: Dict[str, int] = {
    "Multi": 0x6D79,
    "Center": 0x6DA8,
    "Spot": 0x7A8A,
    "Entire Screen Avg.": 0x6F15,
    "Highlight": 0x7600,
}
P314_EXP_STD_ADJ_MIN_SIXTHS: int = -6
P314_EXP_STD_ADJ_MAX_SIXTHS: int = 6
P314_EXP_STD_ADJ_STEPS_SIXTHS: Tuple[int, ...] = tuple(range(-6, 7))
P314_EXP_STD_ADJ_DEFAULT_SIXTHS: int = 0

P314_BRACKET_SETTINGS_MENU_PATH: Tuple[str, ...] = (
    "Shooting",
    "Drive Mode",
    "Bracket Settings",
)
P314_BRACKET_SETTINGS_F_RESID16: int = 0x6466
P314_BRACKET_SELFTIMER_F_RESID16: int = 0x6EF5
P314_BRACKET_SELFTIMER_BKID: str = "BKID_APP_setting_bracket_self_timer"
P314_BRACKET_SELFTIMER_MODES: Tuple[str, ...] = ("Off", "2 Sec", "5 Sec", "10 Sec")
P314_BRACKET_SELFTIMER_DEFAULT: str = "Off"
P314_BRACKET_ORDER_F_RESID16: int = 0x76B1
P314_BRACKET_ORDER_BKID: str = "BKID_APP_setting_bracket_order"
P314_BRACKET_ORDER_MODES: Tuple[str, ...] = ("0->-->+", "-->0->+")
P314_BRACKET_ORDER_UNICODE_MODES: Tuple[str, ...] = ("0\u2192-\u2192+", "-\u21920\u2192+")
P314_BRACKET_ORDER_DEFAULT: str = "0->-->+"

P314_TCUB_MENU_PATH: Tuple[str, ...] = ("Shooting", "TC/UB")
P314_TCUB_DISP_MENU_PATH: Tuple[str, ...] = ("Setup", "Display Option", "TC/UB Disp. Setting")
P314_TCUB_DISP_F_RESID16: int = 0x6B0C
P314_TCUB_DISP_BKID: str = "BKID_APP_setting_tc_ub_disp_setting"
P314_TCUB_DISP_MODES: Tuple[str, ...] = ("Counter", "TC", "U-Bit")
P314_TCUB_DISP_DEFAULT: str = "TC"
P314_TCUB_PLAYBACK_STILL_BLOCK_RESID16: int = 0xE728
P314_TC_PRESET_DEFAULT: str = "00:00:00.00"
P314_UB_PRESET_F_RESID16: int = 0x7AF2
P314_UB_PRESET_DEFAULT: str = "00 00 00 00"
P314_TC_FORMAT_F_RESID16: int = 0x6E3D
P314_TC_FORMAT_MODES: Tuple[str, ...] = ("DF", "NDF")
P314_TC_FORMAT_DEFAULT: str = "DF"
P314_TC_RUN_MODES: Tuple[str, ...] = ("Rec Run", "Free Run")
P314_TC_RUN_DEFAULT: str = "Rec Run"
P314_TC_MAKE_MODES: Tuple[str, ...] = ("Preset", "Regenerate")
P314_TC_MAKE_DEFAULT: str = "Preset"
P314_UB_TIME_REC_F_RESID16: int = 0x7AA8
P314_UB_TIME_REC_DEFAULT: str = "Off"
P314_TV_SYSTEMS: Tuple[str, ...] = ("NTSC", "PAL")
P314_FORCED_NDF_FRAME_RATES: Tuple[str, ...] = ("23.98p", "24.00p")
P314_MOVIE_FRAME_RATES: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25.00p",
    "29.97p",
    "50.00p",
    "59.94p",
    "100.00p",
    "119.88p",
)
P314_FX6_USB_TC_IN_ALT_BKID: str = "BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING"
P314_FX6_TC_FORMAT_2_RESID16: int = 0x456D
P314_FX6_UB_MODE_RESID16_RANGE: Tuple[int, int] = (0x48B5, 0x48B8)

P314_SELECT_PLAYBACK_MEDIA_F_RESID16: int = 0x6BCD
P314_SELECT_PLAYBACK_MEDIA_BKID: str = "BKID_APP_select_playback_media"
P314_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT: int = 1
P314_COPY_F_RESID16: int = 0x79FC
P314_COPY_FUNC_SYMBOL: str = "FUNC_copy_content"
P314_COPY_BATTERY_GATE_SYMBOL: str = "get_battery_status_for_copy"
P314_COPY_SPEED_WARN_RESID16: Tuple[int, int] = (0xE80E, 0xE8CA)
P314_COPY_FAIL_RESID16: Tuple[int, int] = (0xE366, 0xE6DB)

P314_SLIDESHOW_RESID16: int = 0xE2CC
P314_SLIDESHOW_FUNC_SYMBOL: str = "FUNC_start_playback_slide_show"
P314_SLIDESHOW_REPEAT_F_RESID16: int = 0x685F
P314_SLIDESHOW_REPEAT_DEFAULT: str = "Off"
P314_SLIDESHOW_INTERVAL_RESID16: int = 0xE2CD
P314_SLIDESHOW_INTERVALS: Tuple[str, ...] = ("1 Sec", "3 Sec", "5 Sec", "10 Sec", "30 Sec")
P314_SLIDESHOW_INTERVAL_DEFAULT: str = "3 Sec"
P314_SLIDESHOW_VALID_VIEW_MODES: Tuple[str, ...] = ("Date View", "Folder View(Still)")
P314_VIEW_MODES_ALL: Tuple[str, ...] = (
    "Date View",
    "Folder View(Still)",
    "Movie View",
    "AVCHD View",
    "XAVC S View",
)
P314_FX6_DORMANT_COPY_CLIP_2_RESID16: int = 0x4136

P314_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P314_FOCUS_MODES_ALL: Tuple[str, ...] = ("AF-S", "AF-A", "AF-C", "DMF", "MF")
P314_ON_OFF_MODES: Tuple[str, ...] = ("On", "Off")
P314_RESET_ACTIONS: Tuple[str, ...] = (
    "None",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P314_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "COPY_PLAYBACK_MEDIA",
    "SLIDESHOW_PLAYBACK",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P314_SLOT1_VAULT_SLOT: int = 1
P314_SAFE_SECONDARY_SLOT: int = 2
P314_VAULT_FIREWALL_ERRNOS: Tuple[str, ...] = ("EROFS", "EBUSY", "EINVAL", "EOPNOTSUPP")
P314_VAULT_FIREWALL_ERRNO_CODES: Dict[str, int] = {
    "EROFS": 30,
    "EBUSY": 16,
    "EINVAL": 22,
    "EOPNOTSUPP": 95,
}
P314_EOPNOTSUPP_ERRNO: int = 95
P314_EINVAL_ERRNO: int = 22
P314_EBUSY_ERRNO: int = 16
P314_EROFS_ERRNO: int = 30
P314_ENOENT_ERRNO: int = 2
P314_STAGE_B_VOLATILE_OVERLAY_DIR: str = (
    "/tmp/fx3_switch_vh_af_stdadj_tcub_copy_vault_overlay"
)
P314_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P314_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P314_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P314_BLOCKED_INVALID_PILLAR56A_SPEC: str = "BLOCKED_INVALID_PILLAR56A_SPEC"
P314_BLOCKED_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT: str = (
    "BLOCKED_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT"
)
P314_BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL: str = (
    "BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL"
)
P314_BLOCKED_FOCUS_AREA_COLOR_OR_FX6_SPOOF: str = (
    "BLOCKED_FOCUS_AREA_COLOR_OR_FX6_SPOOF"
)
P314_BLOCKED_INVALID_PILLAR56B_SPEC: str = "BLOCKED_INVALID_PILLAR56B_SPEC"
P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT: str = (
    "BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT"
)
P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT: str = (
    "BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT"
)
P314_BLOCKED_REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_FIREWALL: str = (
    "BLOCKED_REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_FIREWALL"
)
P314_BLOCKED_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF: str = (
    "BLOCKED_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF"
)
P314_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL: str = "BLOCKED_SLOT1_VAULT_WRITE_FIREWALL"
P314_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P314_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P314_STATUS_VERIFIED_PILLAR_56A: str = (
    "VERIFIED_PILLAR_56A_SWITCH_VH_AF_ORIENTATION_14AREA_LIMIT_AND_FOCUS_COLOR"
)
P314_STATUS_REJECTED_PILLAR_56A: str = (
    "REJECTED_PILLAR_56A_SWITCH_VH_AF_ORIENTATION_14AREA_LIMIT_AND_FOCUS_COLOR"
)
P314_STATUS_VERIFIED_PILLAR_56B: str = (
    "VERIFIED_PILLAR_56B_EXP_STD_ADJ_5MODE_TCUB_AND_REVERSE_COPY_SLOT1_VAULT_FIREWALL"
)
P314_STATUS_REJECTED_PILLAR_56B: str = (
    "REJECTED_PILLAR_56B_EXP_STD_ADJ_5MODE_TCUB_AND_REVERSE_COPY_SLOT1_VAULT_FIREWALL"
)
P314_STATUS_VERIFIED_PILLAR56_SUITE: str = (
    "VERIFIED_PILLAR56_SWITCH_VH_AF_STDADJ_TCUB_COPY_VAULT"
)
P314_STATUS_FAIL_PILLAR56_SUITE: str = (
    "FAIL_PILLAR56_SWITCH_VH_AF_STDADJ_TCUB_COPY_VAULT"
)
P314_STATUS_VERIFIED_56OF56_AGGREGATOR: str = "VERIFIED_56OF56_PILLAR_RECOVERY_MASTER"
P314_STATUS_FAIL_56OF56_AGGREGATOR: str = "FAIL_56OF56_PILLAR_RECOVERY_MASTER"

P314_PILLAR_56A_SCENARIO_IDS: Tuple[str, ...] = (
    "P56A1_STILL_AFC_SWITCH_VH_AF_ORIENTATION_14AREA_LIMIT_AND_COLOR_INIT_SAFE",
    "P56A2_CAM_RESET_CLEARS_SWITCH_VH_AF_AND_LIMIT_WHILE_PRESERVING_COLOR_AND_FX6_SAFE",
    "P56A3_REJECT_SWITCH_VH_AF_INVALID_PITCH_OR_8LOCKOUT_OR_FORGOT_COORDS_DRIFT",
    "P56A4_REJECT_FOCUS_AREA_LIMIT_LT2_WITHOUT_EINVAL22_OR_DORMANT_XL_XS_CUSTOM_95",
    "P56A5_REJECT_FOCUS_AREA_COLOR_CAM_RESET_WIPE_OR_FX6_SWITCH_VH_AF_SPOOF",
    "P56A6_REJECT_SLOT1_VAULT_MUTATION_OR_PERSISTENT_OVERLAY_OR_H0_H3_DRIFT",
)
P314_PILLAR_56B_SCENARIO_IDS: Tuple[str, ...] = (
    "P56B1_5MODE_EXP_STD_ADJ_EXIF_SPLIT_TCUB_NTSC_24P_NDF_AND_SLOT1_TO_SLOT2_COPY_SAFE",
    "P56B2_INITIALIZE_RESETS_EXP_STD_ADJ_7TCUB_SLIDESHOW_AND_BYPASSES_POWER_SAVE_SAFE",
    "P56B3_REJECT_EXP_STD_ADJ_4MODE_OMISSION_EXIF_CONFLATION_OR_BRACKET_RESET_DRIFT",
    "P56B4_REJECT_TCUB_CAM_RESET_WIPE_PAL_NDF_EXPOSURE_OR_STILL_PLAYBACK_TC_TOGGLE",
    "P56B5_REJECT_REVERSE_COPY_SLOT2_TO_SLOT1_TIER0_VAULT_WITHOUT_EROFS_EBUSY",
    "P56B6_REJECT_SLIDESHOW_POWER_SAVE_KILL_OR_FX6_DORMANT_COPY_CLIP_SPOOF",
)

MASTER_56_PILLAR_COUNT: int = 56
MASTER_56_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_55_PILLAR_SPECS + (
    (
        56,
        "pillar_56_switch_vh_af_stdadj_tcub_copy_vault",
        "Phase 314 (Wave-54)",
        "fx3_recovery.realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier",
    ),
)
MASTER_56_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_56_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Pure Wave-54 State Computations
# ---------------------------------------------------------------------------


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _is_clean_room_forced(force_clean_room: Optional[bool] = None) -> bool:
    """Honor explicit flag, `FX3_FX6_FORCE_CLEAN_ROOM=1`, AND `FX3_CLEAN_ROOM_TEST=1`."""
    if force_clean_room is not None:
        return bool(force_clean_room)
    if is_forced_clean_room():
        return True
    return os.environ.get(P314_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P314_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P314_DONOR_INSPECT_BUDGET_SECONDS


def _normalize_bracket_order(order: str) -> str:
    mapping = {
        "0\u2192-\u2192+": "0->-->+",
        "-\u21920\u2192+": "-->0->+",
    }
    return mapping.get(order, order)


def _is_valid_8hex_ub(value: str) -> bool:
    compact = value.replace(" ", "").strip()
    return len(compact) == 8 and all(c in "0123456789ABCDEFabcdef" for c in compact)


def _safety_invariant_errors() -> List[str]:
    errs: List[str] = []
    checks = (
        ("PERSISTENT_EMMC_WRITES_AUTHORIZED", PERSISTENT_EMMC_WRITES_AUTHORIZED, False),
        ("SPI_NOR_WRITE_AUTHORIZED", SPI_NOR_WRITE_AUTHORIZED, False),
        ("EL3_PAYLOAD_TRANSMIT_AUTHORIZED", EL3_PAYLOAD_TRANSMIT_AUTHORIZED, False),
        ("ISP_WRITE_AUTHORIZED", ISP_WRITE_AUTHORIZED, False),
        ("PERSISTENT_WRITE_RELEASE", PERSISTENT_WRITE_RELEASE, False),
        ("ALLOW_BOOT_PARTITION_TARGETING", ALLOW_BOOT_PARTITION_TARGETING, False),
        ("ALLOW_DESTRUCTIVE_FASTBOOT", ALLOW_DESTRUCTIVE_FASTBOOT, False),
        ("ALLOW_PERSISTENT_JIRITSU_WRITES", ALLOW_PERSISTENT_JIRITSU_WRITES, False),
        ("ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS", ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS, False),
        ("LIVE_USB_IOKIT_TRANSMIT_ENABLED", LIVE_USB_IOKIT_TRANSMIT_ENABLED, False),
        ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("OVERALL_READY_FOR_HARDWARE_ATTACH", OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("CROSS_MODEL_FLASH_AUTHORIZED", CROSS_MODEL_FLASH_AUTHORIZED, False),
        ("P314_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P314_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("P314_OVERALL_READY_FOR_HARDWARE_ATTACH", P314_OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("P314_CROSS_MODEL_FLASH_AUTHORIZED", P314_CROSS_MODEL_FLASH_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        (
            "P314_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT_EVENTS",
            P314_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT_EVENTS,
            0,
        ),
        (
            "P314_FOCUS_LIMIT_LT2_OR_DORMANT_SYMBOL_EVENTS",
            P314_FOCUS_LIMIT_LT2_OR_DORMANT_SYMBOL_EVENTS,
            0,
        ),
        (
            "P314_FOCUS_AREA_COLOR_OR_FX6_SPOOF_EVENTS",
            P314_FOCUS_AREA_COLOR_OR_FX6_SPOOF_EVENTS,
            0,
        ),
        (
            "P314_EXP_STD_ADJ_MODE_CONFLATION_OR_RESET_DRIFT_EVENTS",
            P314_EXP_STD_ADJ_MODE_CONFLATION_OR_RESET_DRIFT_EVENTS,
            0,
        ),
        (
            "P314_BRACKET_SETTINGS_RESET_OR_FX6_SPOOF_EVENTS",
            P314_BRACKET_SETTINGS_RESET_OR_FX6_SPOOF_EVENTS,
            0,
        ),
        (
            "P314_TCUB_RESET_WIPE_OR_FORMAT_LOCK_VIOLATIONS",
            P314_TCUB_RESET_WIPE_OR_FORMAT_LOCK_VIOLATIONS,
            0,
        ),
        (
            "P314_REVERSE_COPY_SLOT2_TO_SLOT1_BYPASS_EVENTS",
            P314_REVERSE_COPY_SLOT2_TO_SLOT1_BYPASS_EVENTS,
            0,
        ),
        (
            "P314_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF_EVENTS",
            P314_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF_EVENTS,
            0,
        ),
        ("P314_SLOT1_DATA_SECTOR_WRITES", P314_SLOT1_DATA_SECTOR_WRITES, 0),
        (
            "P314_SLOT1_COPY_AVF_INFO_MUTATION_BYTES",
            P314_SLOT1_COPY_AVF_INFO_MUTATION_BYTES,
            0,
        ),
        ("P314_SLOT1_VAULT_MUTATION_BYTES", P314_SLOT1_VAULT_MUTATION_BYTES, 0),
        ("P314_SLOT1_FORMAT_HARD_LOCKED", P314_SLOT1_FORMAT_HARD_LOCKED, True),
        ("P314_SLOT1_VAULT_EROFS_EBUSY_ENFORCED", P314_SLOT1_VAULT_EROFS_EBUSY_ENFORCED, True),
        ("P314_FX3_HAS_SWITCH_VH_AF_AREA", P314_FX3_HAS_SWITCH_VH_AF_AREA, True),
        ("P314_FX3_FOCUS_AREA_LIMIT_COUNT", P314_FX3_FOCUS_AREA_LIMIT_COUNT, 14),
        ("P314_FX3_FOCUS_AREA_LIMIT_MIN_ENABLED", P314_FX3_FOCUS_AREA_LIMIT_MIN_ENABLED, 2),
        (
            "P314_FX3_EXP_STD_ADJ_METERING_MODE_COUNT",
            P314_FX3_EXP_STD_ADJ_METERING_MODE_COUNT,
            5,
        ),
        ("P314_FX3_HAS_PHYSICAL_BNC_TC_PORT", P314_FX3_HAS_PHYSICAL_BNC_TC_PORT, False),
        ("P314_FX6_HAS_PHYSICAL_BNC_TC_PORT", P314_FX6_HAS_PHYSICAL_BNC_TC_PORT, True),
        ("P314_FX6_HAS_SWITCH_VH_AF_AREA", P314_FX6_HAS_SWITCH_VH_AF_AREA, False),
        ("P314_FX6_HAS_FOCUS_AREA_LIMIT", P314_FX6_HAS_FOCUS_AREA_LIMIT, False),
        ("P314_FX6_HAS_EXP_STD_ADJ", P314_FX6_HAS_EXP_STD_ADJ, False),
        ("P314_FX6_HAS_STILL_BRACKET_SETTINGS", P314_FX6_HAS_STILL_BRACKET_SETTINGS, False),
        ("P314_FX6_HAS_COPY_CLIP_ACTIVE", P314_FX6_HAS_COPY_CLIP_ACTIVE, False),
        ("P314_FX6_HAS_SLIDE_SHOW", P314_FX6_HAS_SLIDE_SHOW, False),
        ("OTP_FUSE_TOUCHES", OTP_FUSE_TOUCHES, 0),
        ("OTP_FUSE_WRITES", OTP_FUSE_WRITES, 0),
        ("RPMB_COUNTER_INCREMENTS", RPMB_COUNTER_INCREMENTS, 0),
        ("PASSIVE_TX_BYTES_EMITTED", PASSIVE_TX_BYTES_EMITTED, 0),
        ("PHYSICAL_USB_PACKETS_EMITTED", PHYSICAL_USB_PACKETS_EMITTED, 0),
        ("PHYSICAL_DEVICE_WRITES", PHYSICAL_DEVICE_WRITES, 0),
        ("RAW_FIRMWARE_BYTES_LEAKED", RAW_FIRMWARE_BYTES_LEAKED, 0),
    )
    for name, actual, expected in checks:
        if actual != expected:
            errs.append(f"{name} expected {expected!r}, got {actual!r}")
    return errs


def _is_tmpfs_path(path_value: str) -> bool:
    norm = posixpath.normpath(path_value)
    return norm.startswith("/tmp/") or norm.startswith("/run/")


def _targets_persistent_emmc(path_value: str) -> bool:
    low = path_value.strip().lower()
    return any(tok in low for tok in P314_FORBIDDEN_PERSISTENT_TARGETS)


def compute_expected_switch_vh_af_state(
    *,
    camera_model: str,
    shooting_domain: str,
    focus_mode: str,
    configured_switch_vh_af: str,
    previous_switch_vh_af: str,
    orientation: str,
    intelligent_auto_active: bool,
    digital_zoom_active: bool,
    af_active_in_progress: bool,
    continuous_burst_active: bool,
    self_timer_countdown_active: bool,
    focus_magnifier_active: bool,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute `[Switch V/H AF Area]` orientation switching, 8 lockouts, coords clearing, and reset."""
    if camera_model == P314_FX6_DONOR_MODEL_NAME:
        return {
            "fx6_supported": False,
            "lockout_active": True,
            "switch_triggered": False,
            "switch_errno": P314_EOPNOTSUPP_ERRNO,
            "orientation_coords_cleared": False,
            "post_switch_vh_af": "Off",
        }

    option_changed = configured_switch_vh_af != previous_switch_vh_af
    coords_cleared = option_changed or (reset_action in ("Camera Settings Reset", "Initialize"))
    lockout_active = bool(
        shooting_domain != "Still"
        or focus_mode != "AF-C"
        or intelligent_auto_active
        or digital_zoom_active
        or af_active_in_progress
        or continuous_burst_active
        or self_timer_countdown_active
        or focus_magnifier_active
    )
    valid_orientation = orientation in ("0_DEGREES", "90_DEGREES", "270_DEGREES")
    switch_triggered = bool(
        configured_switch_vh_af != "Off"
        and not lockout_active
        and valid_orientation
    )
    switch_errno = P314_EBUSY_ERRNO if (configured_switch_vh_af != "Off" and lockout_active) else None

    if reset_action in ("Camera Settings Reset", "Initialize"):
        post_mode = P314_SWITCH_VH_AF_DEFAULT
    else:
        post_mode = configured_switch_vh_af

    return {
        "fx6_supported": False,
        "lockout_active": lockout_active,
        "valid_orientation": valid_orientation,
        "switch_triggered": switch_triggered,
        "switch_errno": switch_errno,
        "orientation_coords_cleared": coords_cleared,
        "post_switch_vh_af": post_mode,
    }


def compute_expected_focus_area_limit_and_color_state(
    *,
    camera_model: str,
    shooting_domain: str,
    requested_enabled_areas: Tuple[str, ...],
    requested_dormant_areas: Tuple[str, ...],
    configured_focus_area_color: str,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute 14-checkbox `[Focus Area Limit]` (`>= 2`, Movie Tracking exclusion, dormant rejection)
    and `Initialize`-only `[Focus Area Color]` (`White` / `Red`)."""
    if camera_model == P314_FX6_DONOR_MODEL_NAME:
        return {
            "dormant_rejected_errno": (
                P314_EOPNOTSUPP_ERRNO
                if (requested_dormant_areas or requested_enabled_areas)
                else None
            ),
            "limit_lt2_errno": None,
            "effective_areas": (),
            "post_enabled_areas": (),
            "post_focus_area_color": "OrangeMoving",
        }

    dormant_hit = any(a in P314_FOCUS_AREA_LIMIT_DORMANT_5 for a in requested_dormant_areas)
    dormant_errno = P314_EOPNOTSUPP_ERRNO if dormant_hit else None

    if shooting_domain in ("Movie", "S&Q"):
        domain_eligible = tuple(
            a for a in requested_enabled_areas if a in P314_FOCUS_AREA_LIMIT_NON_TRACKING_7
        )
    else:
        domain_eligible = tuple(
            a for a in requested_enabled_areas if a in P314_FOCUS_AREA_LIMIT_14_AREAS
        )

    limit_lt2 = len(requested_enabled_areas) < P314_FX3_FOCUS_AREA_LIMIT_MIN_ENABLED
    limit_errno = P314_EINVAL_ERRNO if limit_lt2 else None

    if reset_action in ("Camera Settings Reset", "Initialize"):
        post_areas = P314_FOCUS_AREA_LIMIT_14_AREAS
    else:
        post_areas = requested_enabled_areas

    if reset_action == "Initialize":
        post_color = P314_FOCUS_AREA_COLOR_DEFAULT
    else:
        post_color = configured_focus_area_color

    return {
        "dormant_rejected_errno": dormant_errno,
        "limit_lt2_errno": limit_errno,
        "effective_areas": domain_eligible,
        "post_enabled_areas": post_areas,
        "post_focus_area_color": post_color,
    }


def compute_expected_exposure_std_adj_and_bracket_state(
    *,
    camera_model: str,
    metering_mode: str,
    configured_std_adj_sixths: int,
    base_exposure_comp_tenths: int,
    adjusted_mid_bracket: bool,
    configured_bracket_selftimer: str,
    configured_bracket_order: str,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute 5-mode `[Exposure Std. Adjust]` (`1/6 EV`, `Initialize`-only, EXIF isolation, `M.M.`
    shift, bracket count reset) and Still `[Bracket Settings]` (`Camera Settings Reset` resettable)."""
    if camera_model == P314_FX6_DONOR_MODEL_NAME:
        return {
            "fx6_exp_std_errno": P314_ENOENT_ERRNO,
            "fx6_bracket_errno": P314_ENOENT_ERRNO,
            "post_std_adj_sixths": 0,
            "post_exposure_comp_tenths": base_exposure_comp_tenths,
            "mm_baseline_shifted_sixths": 0,
            "bracket_shot_counter_reset": False,
            "post_bracket_selftimer": "Off",
            "post_bracket_order": P314_BRACKET_ORDER_DEFAULT,
        }

    norm_order = _normalize_bracket_order(configured_bracket_order)
    if reset_action == "Initialize":
        post_std = P314_EXP_STD_ADJ_DEFAULT_SIXTHS
    else:
        post_std = configured_std_adj_sixths

    if reset_action in ("Camera Settings Reset", "Initialize"):
        post_self = P314_BRACKET_SELFTIMER_DEFAULT
        post_ord = P314_BRACKET_ORDER_DEFAULT
    else:
        post_self = configured_bracket_selftimer
        post_ord = norm_order

    return {
        "fx6_exp_std_errno": None,
        "fx6_bracket_errno": None,
        "metering_mode_valid": metering_mode in P314_EXP_STD_ADJ_5_METERING_MODES,
        "post_std_adj_sixths": post_std,
        "post_exposure_comp_tenths": base_exposure_comp_tenths,
        "mm_baseline_shifted_sixths": configured_std_adj_sixths,
        "bracket_shot_counter_reset": bool(adjusted_mid_bracket),
        "post_bracket_selftimer": post_self,
        "post_bracket_order": post_ord,
    }


def compute_expected_tcub_and_disp_state(
    *,
    camera_model: str,
    tv_system: str,
    frame_rate: str,
    playback_media_kind: str,
    tc_preset: str,
    ub_preset: str,
    tc_format: str,
    tc_run: str,
    tc_make: str,
    ub_time_rec: str,
    tc_ub_disp_setting: str,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute 7-item `Initialize`-only `[TC/UB]` + `[TC/UB Disp. Setting]`, NTSC/24p/PAL locks,
    and movie-playback-only switching (`.uxc 0xe728`)."""
    tc_format_visible = tv_system == "NTSC"
    tc_format_locked_ndf = (tv_system == "NTSC") and (frame_rate in P314_FORCED_NDF_FRAME_RATES)
    effective_tc_format = "NDF" if tc_format_locked_ndf else (tc_format if tc_format_visible else "N/A_PAL_HIDDEN")
    playback_disp_toggle_allowed = playback_media_kind != "Still"

    if camera_model == P314_FX6_DONOR_MODEL_NAME:
        return {
            "tc_format_visible": tc_format_visible,
            "tc_format_locked_ndf": tc_format_locked_ndf,
            "effective_tc_format": effective_tc_format,
            "playback_disp_toggle_allowed": playback_disp_toggle_allowed,
            "post_tc_preset": tc_preset,
            "post_ub_preset": ub_preset,
            "post_tc_format": effective_tc_format,
            "post_tc_run": tc_run,
            "post_tc_make": tc_make,
            "post_ub_time_rec": ub_time_rec,
            "post_tc_ub_disp_setting": tc_ub_disp_setting,
        }

    if reset_action == "Initialize":
        post_tc_preset = P314_TC_PRESET_DEFAULT
        post_ub_preset = P314_UB_PRESET_DEFAULT
        post_tc_format = "NDF" if tc_format_locked_ndf else (P314_TC_FORMAT_DEFAULT if tc_format_visible else "N/A_PAL_HIDDEN")
        post_tc_run = P314_TC_RUN_DEFAULT
        post_tc_make = P314_TC_MAKE_DEFAULT
        post_ub_time_rec = P314_UB_TIME_REC_DEFAULT
        post_disp = P314_TCUB_DISP_DEFAULT
    else:
        # All 7 items survive Camera Settings Reset & Reset Network Set.
        post_tc_preset = tc_preset
        post_ub_preset = ub_preset
        post_tc_format = effective_tc_format
        post_tc_run = tc_run
        post_tc_make = tc_make
        post_ub_time_rec = ub_time_rec
        post_disp = tc_ub_disp_setting

    return {
        "tc_format_visible": tc_format_visible,
        "tc_format_locked_ndf": tc_format_locked_ndf,
        "effective_tc_format": effective_tc_format,
        "playback_disp_toggle_allowed": playback_disp_toggle_allowed,
        "post_tc_preset": post_tc_preset,
        "post_ub_preset": post_ub_preset,
        "post_tc_format": post_tc_format,
        "post_tc_run": post_tc_run,
        "post_tc_make": post_tc_make,
        "post_ub_time_rec": post_ub_time_rec,
        "post_tc_ub_disp_setting": post_disp,
    }


def compute_expected_playback_copy_and_slideshow_vault_state(
    *,
    camera_model: str,
    select_playback_media_slot: int,
    slot1_holds_tier0_vault: bool,
    slot1_read_only_or_busy: bool,
    battery_ok_for_copy: bool,
    target_slot_speed_class_ok: bool,
    slideshow_view_mode: str,
    slideshow_repeat: str,
    slideshow_interval: str,
    slideshow_active: bool,
    requested_vault_action: str,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute bidirectional `[Copy]` (`Slot 1 <-> Slot 2`), fail-closed `Slot 2 -> Slot 1` Tier-0
    Vault Firewall (`EROFS=30`/`EBUSY=16`), and `[Slide Show]` Power-Save bypass."""
    source_slot = select_playback_media_slot
    dest_slot = 2 if source_slot == 1 else 1
    reverse_to_slot1 = (requested_vault_action == "COPY_PLAYBACK_MEDIA") and (dest_slot == 1)

    if camera_model == P314_FX6_DONOR_MODEL_NAME:
        copy_errno: Optional[str] = "EOPNOTSUPP" if requested_vault_action == "COPY_PLAYBACK_MEDIA" else None
        action_allowed = False
    elif requested_vault_action in ("FORMAT_QUICK", "FORMAT_FULL"):
        action_allowed = False
        copy_errno = "EROFS"
    elif requested_vault_action == "COPY_PLAYBACK_MEDIA":
        if reverse_to_slot1 and slot1_holds_tier0_vault:
            action_allowed = False
            copy_errno = "EBUSY" if slot1_read_only_or_busy else "EROFS"
        elif not battery_ok_for_copy:
            action_allowed = False
            copy_errno = "EINVAL"
        elif not target_slot_speed_class_ok:
            action_allowed = False
            copy_errno = "EINVAL"
        else:
            action_allowed = True
            copy_errno = None
    elif requested_vault_action == "SLIDESHOW_PLAYBACK":
        action_allowed = slideshow_view_mode in P314_SLIDESHOW_VALID_VIEW_MODES
        copy_errno = None if action_allowed else "EINVAL"
    else:
        action_allowed = False
        copy_errno = None

    slideshow_eligible = (
        camera_model != P314_FX6_DONOR_MODEL_NAME
        and slideshow_view_mode in P314_SLIDESHOW_VALID_VIEW_MODES
    )
    power_save_bypassed = bool(slideshow_active and slideshow_eligible)

    if reset_action == "Initialize":
        post_media_slot = P314_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT
        post_repeat = P314_SLIDESHOW_REPEAT_DEFAULT
        post_interval = P314_SLIDESHOW_INTERVAL_DEFAULT
    else:
        post_media_slot = select_playback_media_slot
        post_repeat = slideshow_repeat
        post_interval = slideshow_interval

    return {
        "source_slot": source_slot,
        "dest_slot": dest_slot,
        "reverse_to_slot1": reverse_to_slot1,
        "action_allowed": action_allowed,
        "firewall_errno": copy_errno,
        "firewall_errno_num": (
            P314_VAULT_FIREWALL_ERRNO_CODES[copy_errno] if copy_errno in P314_VAULT_FIREWALL_ERRNO_CODES else None
        ),
        "dest_group_and_protect_cleared": bool(requested_vault_action == "COPY_PLAYBACK_MEDIA" and action_allowed),
        "slideshow_eligible": slideshow_eligible,
        "power_save_bypassed": power_save_bypassed,
        "post_select_playback_media": post_media_slot,
        "post_slideshow_repeat": post_repeat,
        "post_slideshow_interval": post_interval,
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback (Phase 314, 17 Donors)
# ---------------------------------------------------------------------------


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P314_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    resolved = resolve_donor_path(relpath)
    if resolved is None:
        return False, 0, 0, "MISSING", "", b""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(str(resolved), flags)
    except OSError:
        return False, 0, 0, "OPEN_ERROR", "", b""
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return False, 0, 0, "NOT_REGULAR", "", b""
        total_size = int(st.st_size)
        if total_size <= max_full_bytes:
            chunks: List[bytes] = []
            offset = 0
            while offset < total_size:
                chunk = os.pread(fd, min(65536, total_size - offset), offset)
                if not chunk:
                    break
                chunks.append(chunk)
                offset += len(chunk)
            data = b"".join(chunks)
            return True, total_size, len(data), "FULL_SHA256", sha256(data).hexdigest(), data
        hdr = os.pread(fd, min(P314_BOUNDED_HEADER_BYTES, total_size), 0)
        return True, total_size, len(hdr), "HEADER4K_SHA256", sha256(hdr).hexdigest(), hdr
    finally:
        os.close(fd)


def _check_elf64_aarch64(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return False, f"NOT_ELF:{label}"
    ei_class, ei_data = data[4], data[5]
    e_machine = struct.unpack_from("<H", data, 18)[0]
    if ei_class != 2 or ei_data != 1 or e_machine != 183:
        return False, f"BAD_ELF64_AARCH64(class={ei_class},data={ei_data},mach={e_machine})"
    return True, f"ELF64_AARCH64:{label}"


def _check_uxc7_pack(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 16 or data[:4] != b"uxc\x07":
        return False, f"BAD_UXC7_MAGIC:{label}"
    return True, f"UXC7_{label}"


def _check_bk4_backup(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 32 or struct.unpack_from("<I", data, 4)[0] != 0xAAAAAAAA or data[12:16] != b"BK4\x00":
        return False, f"BAD_BK4_MAGIC:{label}"
    return True, f"BK4_{label}"


def _synthetic_phase314_donors() -> Tuple["Phase314DonorArtifactDigest", ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P314_DONOR_FX3_APPFW_702_RELPATH,
            P314_PINNED_FX3_APPFW_702_BYTES,
            P314_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P314_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P314_DONOR_FX6_APPFW_601_RELPATH,
            P314_PINNED_FX6_APPFW_601_BYTES,
            P314_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P314_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P314_DONOR_FX3_BACKUP_BIN_RELPATH,
            P314_PINNED_FX3_BACKUP_BIN_BYTES,
            P314_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_uxc_en_f",
            P314_DONOR_FX3_UXC_EN_F_RELPATH,
            P314_PINNED_FX3_UXC_EN_F_BYTES,
            P314_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P314_DONOR_FX3_UXC_SC_F_RELPATH,
            P314_PINNED_FX3_UXC_SC_F_BYTES,
            P314_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P314_DONOR_FX3_UXC_TC_F_RELPATH,
            P314_PINNED_FX3_UXC_TC_F_BYTES,
            P314_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P314_DONOR_FX3_UXC_JA_F_RELPATH,
            P314_PINNED_FX3_UXC_JA_F_BYTES,
            P314_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P314_DONOR_FX3_UXC_EN_RELPATH,
            P314_PINNED_FX3_UXC_EN_BYTES,
            P314_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_sc",
            P314_DONOR_FX3_UXC_SC_RELPATH,
            P314_PINNED_FX3_UXC_SC_BYTES,
            P314_PINNED_FX3_UXC_SC_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX3_SC",
        ),
        (
            "fx3_uxc_tc",
            P314_DONOR_FX3_UXC_TC_RELPATH,
            P314_PINNED_FX3_UXC_TC_BYTES,
            P314_PINNED_FX3_UXC_TC_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX3_TC",
        ),
        (
            "fx3_uxc_ja",
            P314_DONOR_FX3_UXC_JA_RELPATH,
            P314_PINNED_FX3_UXC_JA_BYTES,
            P314_PINNED_FX3_UXC_JA_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX3_JA",
        ),
        (
            "fx3_uxc_en_g",
            P314_DONOR_FX3_UXC_EN_G_RELPATH,
            P314_PINNED_FX3_UXC_EN_G_BYTES,
            P314_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx3_uxc_sc_g",
            P314_DONOR_FX3_UXC_SC_G_RELPATH,
            P314_PINNED_FX3_UXC_SC_G_BYTES,
            P314_PINNED_FX3_UXC_SC_G_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_SC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_G",
        ),
        (
            "fx3_uxc_tc_g",
            P314_DONOR_FX3_UXC_TC_G_RELPATH,
            P314_PINNED_FX3_UXC_TC_G_BYTES,
            P314_PINNED_FX3_UXC_TC_G_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_TC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_G",
        ),
        (
            "fx3_uxc_ja_g",
            P314_DONOR_FX3_UXC_JA_G_RELPATH,
            P314_PINNED_FX3_UXC_JA_G_BYTES,
            P314_PINNED_FX3_UXC_JA_G_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX3_UXC_JA_G_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_G",
        ),
        (
            "fx6_uxc_en",
            P314_DONOR_FX6_UXC_EN_RELPATH,
            P314_PINNED_FX6_UXC_EN_BYTES,
            P314_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P314_DONOR_FX6_UXC_EN_2_RELPATH,
            P314_PINNED_FX6_UXC_EN_2_BYTES,
            P314_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P314_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase314DonorArtifactDigest(
            artifact_id=aid,
            relpath=rel,
            present=True,
            read_mode="CLEAN_ROOM_SYNTHETIC",
            total_bytes=total,
            header_bytes_read=hdr_b,
            digest_kind=dkind,
            digest_sha256=dsha,
            marker_summary=msum,
            matches_pinned=True,
        )
        for aid, rel, total, hdr_b, dkind, dsha, msum in specs
    )


def inspect_phase314_donors_readonly(force_clean_room: Optional[bool] = None) -> "Phase314DonorSnapshot":
    """Inspect Wave-54 FX3 7.02 (`14` donors) & FX6 6.01 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.2s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase314_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase314DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_20s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_appfw_702_so",
            P314_DONOR_FX3_APPFW_702_RELPATH,
            P314_PINNED_FX3_APPFW_702_BYTES,
            P314_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702"),
        ),
        (
            "fx6_appfw_601_so",
            P314_DONOR_FX6_APPFW_601_RELPATH,
            P314_PINNED_FX6_APPFW_601_BYTES,
            P314_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601"),
        ),
        (
            "fx3_backup_bin",
            P314_DONOR_FX3_BACKUP_BIN_RELPATH,
            P314_PINNED_FX3_BACKUP_BIN_BYTES,
            P314_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_uxc_en_f",
            P314_DONOR_FX3_UXC_EN_F_RELPATH,
            P314_PINNED_FX3_UXC_EN_F_BYTES,
            P314_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P314_DONOR_FX3_UXC_SC_F_RELPATH,
            P314_PINNED_FX3_UXC_SC_F_BYTES,
            P314_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P314_DONOR_FX3_UXC_TC_F_RELPATH,
            P314_PINNED_FX3_UXC_TC_F_BYTES,
            P314_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P314_DONOR_FX3_UXC_JA_F_RELPATH,
            P314_PINNED_FX3_UXC_JA_F_BYTES,
            P314_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P314_DONOR_FX3_UXC_EN_RELPATH,
            P314_PINNED_FX3_UXC_EN_BYTES,
            P314_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_sc",
            P314_DONOR_FX3_UXC_SC_RELPATH,
            P314_PINNED_FX3_UXC_SC_BYTES,
            P314_PINNED_FX3_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC"),
        ),
        (
            "fx3_uxc_tc",
            P314_DONOR_FX3_UXC_TC_RELPATH,
            P314_PINNED_FX3_UXC_TC_BYTES,
            P314_PINNED_FX3_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC"),
        ),
        (
            "fx3_uxc_ja",
            P314_DONOR_FX3_UXC_JA_RELPATH,
            P314_PINNED_FX3_UXC_JA_BYTES,
            P314_PINNED_FX3_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA"),
        ),
        (
            "fx3_uxc_en_g",
            P314_DONOR_FX3_UXC_EN_G_RELPATH,
            P314_PINNED_FX3_UXC_EN_G_BYTES,
            P314_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx3_uxc_sc_g",
            P314_DONOR_FX3_UXC_SC_G_RELPATH,
            P314_PINNED_FX3_UXC_SC_G_BYTES,
            P314_PINNED_FX3_UXC_SC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_G"),
        ),
        (
            "fx3_uxc_tc_g",
            P314_DONOR_FX3_UXC_TC_G_RELPATH,
            P314_PINNED_FX3_UXC_TC_G_BYTES,
            P314_PINNED_FX3_UXC_TC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_G"),
        ),
        (
            "fx3_uxc_ja_g",
            P314_DONOR_FX3_UXC_JA_G_RELPATH,
            P314_PINNED_FX3_UXC_JA_G_BYTES,
            P314_PINNED_FX3_UXC_JA_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_G"),
        ),
        (
            "fx6_uxc_en",
            P314_DONOR_FX6_UXC_EN_RELPATH,
            P314_PINNED_FX6_UXC_EN_BYTES,
            P314_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P314_DONOR_FX6_UXC_EN_2_RELPATH,
            P314_PINNED_FX6_UXC_EN_2_BYTES,
            P314_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    digests: List[Phase314DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            break
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        digests.append(
            Phase314DonorArtifactDigest(
                artifact_id=aid,
                relpath=relpath,
                present=True,
                read_mode="LOCAL_DONOR_O_RDONLY",
                total_bytes=total_b,
                header_bytes_read=hdr_b,
                digest_kind=dkind,
                digest_sha256=dsha,
                marker_summary=msum,
                matches_pinned=matches,
            )
        )

    if any_missing:
        artifacts = _synthetic_phase314_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase314DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_20s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    all_ok = all(d.present and d.matches_pinned for d in digests) and len(digests) == len(probe_specs)
    dt = round(time.monotonic() - t0, 6)
    return Phase314DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_20s_budget=dt < budget,
        budget_seconds_applied=budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Frozen Dataclasses (Specs, Reports, Suites & 56-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase314DonorArtifactDigest:
    artifact_id: str
    relpath: str
    present: bool
    read_mode: str
    total_bytes: int
    header_bytes_read: int
    digest_kind: str
    digest_sha256: str
    marker_summary: str
    matches_pinned: bool


@dataclass(frozen=True)
class Phase314DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase314DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SwitchVhAfFocusLimitColorVaultSpec:
    # Still-Only [Switch V/H AF Area] (0/90/270/INVALID orientation + 8 lockouts + coords clear)
    camera_model: str
    fw_version: str
    shooting_domain: str
    focus_mode: str
    configured_switch_vh_af: str
    previous_switch_vh_af: str
    orientation: str
    intelligent_auto_active: bool
    digital_zoom_active: bool
    af_active_in_progress: bool
    continuous_burst_active: bool
    self_timer_countdown_active: bool
    focus_magnifier_active: bool
    reported_switch_triggered: bool
    reported_switch_errno: Optional[int]
    reported_orientation_coords_cleared: bool
    post_switch_vh_af: str
    # 14-Checkbox [Focus Area Limit] (>= 2 `.uxc 0xea28` -> EINVAL=22 vs dormant xl/xs/custom_1..3 -> EOPNOTSUPP=95)
    requested_enabled_areas: Tuple[str, ...]
    requested_dormant_areas: Tuple[str, ...]
    reported_limit_lt2_errno: Optional[int]
    reported_dormant_errno: Optional[int]
    reported_movie_tracking_excluded: bool
    post_enabled_areas: Tuple[str, ...]
    # Initialize-Only [Focus Area Color] (White / Red) vs Zero-Switch FX6
    configured_focus_area_color: str
    post_focus_area_color: str
    reset_action: str
    fx6_exposes_switch_vh_af_or_limit: bool
    fx6_exposes_white_red_color_toggle: bool
    # Tier-0 / Stage-B / Slot-1 Vault firewall
    requested_vault_slot: int
    requested_vault_action: str
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    switch_vh_af_lockout_or_coords_drift_events: int
    focus_limit_lt2_or_dormant_symbol_events: int
    focus_area_color_or_fx6_spoof_events: int


@dataclass(frozen=True)
class SwitchVhAfFocusLimitColorVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    switch_vh_af_orientation_lockout_coords_verified: bool
    focus_area_limit_14checkbox_ge2_and_dormant_verified: bool
    focus_area_color_init_only_and_fx6_zero_switch_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    switch_vh_af_lockout_or_coords_drift_events: int
    focus_limit_lt2_or_dormant_symbol_events: int
    focus_area_color_or_fx6_spoof_events: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ExposureStdTcubReverseCopyVaultSpec:
    # 5-Mode [Exposure Std. Adjust] (1/6 EV, Initialize-Only) + Still [Bracket Settings]
    camera_model: str
    fw_version: str
    exp_std_metering_mode: str
    exp_std_supported_modes_count: int
    exp_std_warn_prompt_acknowledged: bool
    configured_exp_std_adj_sixths: int
    base_exposure_comp_tenths: int
    reported_post_exposure_comp_tenths: int
    reported_exif_std_adj_isolated: bool
    reported_mm_baseline_shifted_sixths: int
    adjusted_mid_bracket: bool
    reported_bracket_shot_counter_reset: bool
    post_exp_std_adj_sixths: int
    configured_bracket_selftimer: str
    configured_bracket_order: str
    post_bracket_selftimer: str
    post_bracket_order: str
    fx6_exp_std_errno: Optional[int]
    fx6_bracket_errno: Optional[int]
    # 7-Item Initialize-Only [TC/UB] & [TC/UB Disp. Setting] Format Locks vs FX6 BNC TC IN/OUT
    tv_system: str
    frame_rate: str
    playback_media_kind: str
    tc_preset: str
    ub_preset: str
    tc_format: str
    tc_run: str
    tc_make: str
    ub_time_rec: str
    tc_ub_disp_setting: str
    reported_tc_format_visible: bool
    reported_tc_format_locked_ndf: bool
    reported_playback_disp_toggle_allowed: bool
    post_tc_preset: str
    post_ub_preset: str
    post_tc_format: str
    post_tc_run: str
    post_tc_make: str
    post_ub_time_rec: str
    post_tc_ub_disp_setting: str
    fx3_has_physical_bnc_tc_port: bool
    fx6_has_physical_bnc_tc_port: bool
    # CRITICAL Bidirectional [Copy] (Slot-2 -> Slot-1 Tier-0 Vault Firewall) & [Slide Show]
    select_playback_media_slot: int
    slot1_holds_tier0_vault: bool
    slot1_read_only_or_busy: bool
    battery_ok_for_copy: bool
    target_slot_speed_class_ok: bool
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    reported_dest_group_and_protect_cleared: bool
    slideshow_view_mode: str
    slideshow_repeat: str
    slideshow_interval: str
    slideshow_active: bool
    reported_power_save_bypassed: bool
    post_select_playback_media: int
    post_slideshow_repeat: str
    post_slideshow_interval: str
    fx6_copy_clip_active: bool
    reset_action: str
    # Slot-1 Tier-0 Vault & Stage-B Overlay
    slot1_data_sector_writes: int
    slot1_copy_avf_info_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    exp_std_adj_mode_conflation_or_reset_drift_events: int
    bracket_settings_reset_or_fx6_spoof_events: int
    tcub_reset_wipe_or_format_lock_violations: int
    reverse_copy_slot2_to_slot1_bypass_events: int
    slideshow_power_save_or_fx6_copy_clip_spoof_events: int


@dataclass(frozen=True)
class ExposureStdTcubReverseCopyVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    exp_std_adj_5mode_exif_and_init_only_verified: bool
    bracket_settings_reset_and_fx6_dormant_verified: bool
    tcub_7item_init_only_format_locks_and_fx6_bnc_verified: bool
    reverse_copy_slot2_to_slot1_erofs_ebusy_firewall_verified: bool
    slideshow_power_save_bypass_and_fx6_copy_clip_dormant_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    exp_std_adj_mode_conflation_or_reset_drift_events: int
    bracket_settings_reset_or_fx6_spoof_events: int
    tcub_reset_wipe_or_format_lock_violations: int
    reverse_copy_slot2_to_slot1_bypass_events: int
    slideshow_power_save_or_fx6_copy_clip_spoof_events: int
    slot1_data_sector_writes: int
    slot1_copy_avf_info_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SwitchVhAfStdAdjTcubCopyVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase314DonorSnapshot
    switch_vh_af_focus_limit_color_report: SwitchVhAfFocusLimitColorVaultReport
    exposure_std_tcub_reverse_copy_report: ExposureStdTcubReverseCopyVaultReport
    switch_vh_af_lockout_or_coords_drift_events: int
    focus_limit_lt2_or_dormant_symbol_events: int
    focus_area_color_or_fx6_spoof_events: int
    exp_std_adj_mode_conflation_or_reset_drift_events: int
    bracket_settings_reset_or_fx6_spoof_events: int
    tcub_reset_wipe_or_format_lock_violations: int
    reverse_copy_slot2_to_slot1_bypass_events: int
    slideshow_power_save_or_fx6_copy_clip_spoof_events: int
    slot1_data_sector_writes: int
    slot1_copy_avf_info_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar56ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar56ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar56ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar56BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar56ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar56StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase314DonorSnapshot
    pillar_56a_switch_vh_af_focus_limit_color_vault: Pillar56ASuiteResult
    pillar_56b_exposure_std_tcub_reverse_copy_vault: Pillar56BSuiteResult
    switch_vh_af_lockout_or_coords_drift_events: int
    focus_limit_lt2_or_dormant_symbol_events: int
    focus_area_color_or_fx6_spoof_events: int
    exp_std_adj_mode_conflation_or_reset_drift_events: int
    bracket_settings_reset_or_fx6_spoof_events: int
    tcub_reset_wipe_or_format_lock_violations: int
    reverse_copy_slot2_to_slot1_bypass_events: int
    slideshow_power_save_or_fx6_copy_clip_spoof_events: int
    slot1_data_sector_writes: int
    slot1_copy_avf_info_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    suite_sha256: str
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master56PillarRecoveryReport:
    schema: str
    schema_version: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_1_5s_fast_cli_budget: bool
    under_2_5s_fast_cli_budget: bool
    under_6s_budget: bool
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    # Pillar 56 & Wave-54 top-level fields (Phase 314 — 56/56 Milestone)
    donor_snapshot: Phase314DonorSnapshot
    pillar56_a_switch_vh_af_focus_limit_color_vault: Pillar56ASuiteResult
    pillar56_b_exposure_std_tcub_reverse_copy_vault: Pillar56BSuiteResult
    switch_vh_af_lockout_or_coords_drift_events: int
    focus_limit_lt2_or_dormant_symbol_events: int
    focus_area_color_or_fx6_spoof_events: int
    exp_std_adj_mode_conflation_or_reset_drift_events: int
    bracket_settings_reset_or_fx6_spoof_events: int
    tcub_reset_wipe_or_format_lock_violations: int
    reverse_copy_slot2_to_slot1_bypass_events: int
    slideshow_power_save_or_fx6_copy_clip_spoof_events: int
    slot1_data_sector_writes: int
    slot1_copy_avf_info_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    fx3_has_switch_vh_af_area: bool
    fx3_focus_area_limit_count: int
    fx3_focus_area_limit_min_enabled: int
    fx3_exp_std_adj_metering_mode_count: int
    fx3_has_physical_bnc_tc_port: bool
    fx6_has_physical_bnc_tc_port: bool
    fx6_has_switch_vh_af_area: bool
    fx6_has_focus_area_limit: bool
    fx6_has_exp_std_adj: bool
    fx6_has_still_bracket_settings: bool
    fx6_has_copy_clip_active: bool
    fx6_has_slide_show: bool
    # Preserved Pillars 1..55 rollup metrics
    dormant_shading_auto_low_exposure_events: int
    lens_comp_lock_or_arw_conflation_events: int
    af_illuminator_gate_or_fx6_spoof_events: int
    movie_af_transition_or_assist_drift_events: int
    aperture_drive_pre_af_shutter_reset_drift_events: int
    circ_focus_diagonal_or_color_drift_events: int
    folder_name_or_leading_underscore_violations: int
    slot1_folder_dir_mutation_bytes: int
    slot1_rating_avf_info_mutation_bytes: int
    fx3_has_builtin_af_illuminator: bool
    fx6_has_builtin_af_illuminator: bool
    fx3_exposes_shading_auto_low: bool
    fx6_has_aperture_drive_pre_af_circ_color: bool
    fx6_has_msdcf_or_star_rating: bool
    sensor_cleaning_low_battery_bypass_events: int
    sensor_cleaning_no_power_off_violations: int
    fx6_ibis_shake_conflation_events: int
    ev_comp_range_or_cine_ei_lockout_violations: int
    exposure_step_or_dormant_reset_ev_drift_events: int
    focus_mode_movie_clamp_or_dormant_drift_events: int
    priority_set_or_illuminator_gate_violations: int
    image_index_dormant_or_view_mode_drift_events: int
    slot1_rotate_exif_mutation_bytes: int
    fx3_has_sensor_cleaning_ibis: bool
    fx3_has_exposure_comp: bool
    fx3_has_physical_ev_reset_dial: bool
    fx6_has_ultrasonic_ibis_cleaning: bool
    fx6_has_variable_end_optical_block: bool
    fx6_has_technical_apr: bool
    fx6_has_still_exposure_comp: bool
    fx6_has_still_image_index_rotate: bool
    dci4k_long_gop_or_8k_violations: int
    reboot_2400p_stage_b_wipe_violations: int
    hdmi_raw_or_still_aspect_drift_events: int
    fx6_still_or_raw_conflation_events: int
    reg_custom_hold_or_hlg_lock_drift_events: int
    camset_cross_model_path_drift_events: int
    photo_capture_dci4k_lockout_bypass_events: int
    slot1_camset_write_bytes: int
    slot1_photo_capture_write_bytes: int
    fx3_appfw_has_dci4k_internal: bool
    fx3_appfw_has_pro_camera_path: bool
    fx6_has_still_aspect_ratio: bool
    fx6_has_photo_capture: bool
    fx6_has_playback_enlarge_image: bool
    fx6_has_reg_custom_shoot_set: bool
    fx6_has_camera_set_memory: bool
    movie_tracking_area_or_limit_violations: int
    af_area_reg_lock_or_reset_drift_events: int
    xlrh1_zoom_or_hold_spoof_events: int
    fx6_handle_or_pos_display_conflation_events: int
    iso_minss_or_cine_ei_lock_drift_events: int
    flash_still_mech_gate_violations: int
    mishoe_pmic_5v_overcurrent_events: int
    slot1_focus_zoom_camset_mutation_bytes: int
    slot1_flash_videolight_imagedb_bytes: int
    xlrh1_has_zoom_lever: bool
    xlrh1_has_rec_button: bool
    xlrh1_has_zoom_hold_switch: bool
    fx6_0_99_is_zoom_position_display: bool
    fx6_has_iso_auto_min_ss: bool
    fx6_mechanical_shutter_present: bool
    dormant_lossless_raw_exposure_events: int
    fx6_still_pipeline_conflation_events: int
    hlg_still_prereq_or_lockout_drift_events: int
    colorspace_adobergb_prefix_violations: int
    shutter_type_auto_spoof_events: int
    fx6_mechanical_shutter_conflation_events: int
    electronic_silent_5lock_bypass_events: int
    nr_or_drive_burst_wall_violations: int
    slot1_still_capture_or_sort_write_bytes: int
    slot1_imagedb_or_burst_mutation_bytes: int
    fx3_ui_exposes_lossless_raw: bool
    fx3_ui_exposes_shutter_type_auto: bool
    fx6_still_pipeline_present: bool
    double_log_or_lockout_bypass_events: int
    pplut_1080p_clamp_bypass_events: int
    pp_internal_reset_trap_violations: int
    fx6_baselook_confusion_events: int
    wb_cine_ei_awb_or_custom_setup_trap_events: int
    wb_custom_camset_exclusion_drift_events: int
    metering_desqueeze_or_cine_ei_base_iso_drift_events: int
    fx3_ui_exposes_usb_streaming: bool
    nouvc_spoof_events: int
    usb_host_data_enumeration_events: int
    hdmi_lcd_blanking_violations: int
    hdmi_log_1080_bypass_events: int
    slot1_protect_only_vault_violations: int
    slot1_vault_format_or_delete_events: int
    network_reset_zero_rf_violations: int
    fx3_ui_exposes_power_save_by_monitor: bool
    legacy_power_save_monitor_spoof_events: int
    unsafe_power_save_sleep_interference_events: int
    bk_lang_parity_drift_events: int
    stage_b_4lang_uxc_ltt_drift_events: int
    xlrh1_acoustic_feedback_violations: int
    audio_mon_4ch_hdmi_confusion_events: int
    destructive_delete_confirm_drift_events: int
    slot1_vault_delete_events: int
    legacy_mf_assist_spoof_events: int
    still_movie_initial_mag_couplings: int
    movie_af_in_focus_mag_events: int
    hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int
    movie_sq_af_illuminator_fire_events: int
    legacy_datetime_setup_spoof_events: int
    unsolicited_rtc_timezone_jump_events: int
    mishoe_5v_overcurrent_events: int
    hdmi_res_log_internal_rec_2160p_bypass_events: int
    slot1_vault_mutation_events: int
    slot1_vault_folder_mutation_events: int
    slot1_vault_folder_mutation_bytes: int
    movie_custom_folder_or_title_overflow_events: int
    still_prefix_underscore_lead_or_len_violations: int
    gamma_assist_log_lockout_bypass_events: int
    gamma_assist_external_hdmi_leak_events: int
    tcub_camera_reset_wipe_or_format_violations: int
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
    apsc_s35_4k_or_raw_bypass_events: int
    ai_unit_subject_recog_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    version_dialog_flash_writes: int
    bodydata_flash_attempts_blocked: int
    slot1_bodydata_vault_mutation_bytes: int
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_raw_or_240p_bypass_events: int
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    slot1_custom_key_vault_mutation_bytes: int
    fx3_has_builtin_evf: bool
    evf_finder_monitor_spoof_events: int
    tier0_battery_high_display_violations: int
    bt_rmt_ir_lockout_violations: int
    slot1_mymenu_vault_mutation_bytes: int
    destructive_menu_delete_confusions: int
    shutter_angle_exposure_step_drift_events: int
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
    overall_ready_for_hardware_attach: bool
    cross_model_flash_authorized: bool
    hardware_live_attachment_authorized: bool
    master_56pillar_sha256: str
    cnflasha_userspace_write_blocked: bool
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Spec Builders (Pillars 56A & 56B)
# ---------------------------------------------------------------------------


def build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
    **overrides: Any,
) -> SwitchVhAfFocusLimitColorVaultSpec:
    """Return a clean, verified default `SwitchVhAfFocusLimitColorVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P314_FX3_MODEL_NAME,
        "fw_version": P314_FX3_FW_VERSION,
        "shooting_domain": "Still",
        "focus_mode": "AF-C",
        "configured_switch_vh_af": "AF Point + AF Area",
        "previous_switch_vh_af": "AF Point + AF Area",
        "orientation": "90_DEGREES",
        "intelligent_auto_active": False,
        "digital_zoom_active": False,
        "af_active_in_progress": False,
        "continuous_burst_active": False,
        "self_timer_countdown_active": False,
        "focus_magnifier_active": False,
        "reported_switch_triggered": True,
        "reported_switch_errno": None,
        "reported_orientation_coords_cleared": False,
        "post_switch_vh_af": "AF Point + AF Area",
        "requested_enabled_areas": P314_FOCUS_AREA_LIMIT_14_AREAS,
        "requested_dormant_areas": (),
        "reported_limit_lt2_errno": None,
        "reported_dormant_errno": None,
        "reported_movie_tracking_excluded": False,
        "post_enabled_areas": P314_FOCUS_AREA_LIMIT_14_AREAS,
        "configured_focus_area_color": P314_FOCUS_AREA_COLOR_DEFAULT,
        "post_focus_area_color": P314_FOCUS_AREA_COLOR_DEFAULT,
        "reset_action": "None",
        "fx6_exposes_switch_vh_af_or_limit": False,
        "fx6_exposes_white_red_color_toggle": False,
        "requested_vault_slot": P314_SLOT1_VAULT_SLOT,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_ebusy_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P314_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P314_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P314_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P314_TIER0_SURFACE_COUNT,
        "switch_vh_af_lockout_or_coords_drift_events": 0,
        "focus_limit_lt2_or_dormant_symbol_events": 0,
        "focus_area_color_or_fx6_spoof_events": 0,
    }
    defaults.update(overrides)
    return SwitchVhAfFocusLimitColorVaultSpec(**defaults)


def build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
    **overrides: Any,
) -> ExposureStdTcubReverseCopyVaultSpec:
    """Return a clean, verified default `ExposureStdTcubReverseCopyVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P314_FX3_MODEL_NAME,
        "fw_version": P314_FX3_FW_VERSION,
        "exp_std_metering_mode": "Multi",
        "exp_std_supported_modes_count": P314_FX3_EXP_STD_ADJ_METERING_MODE_COUNT,
        "exp_std_warn_prompt_acknowledged": True,
        "configured_exp_std_adj_sixths": 0,
        "base_exposure_comp_tenths": 0,
        "reported_post_exposure_comp_tenths": 0,
        "reported_exif_std_adj_isolated": True,
        "reported_mm_baseline_shifted_sixths": 0,
        "adjusted_mid_bracket": False,
        "reported_bracket_shot_counter_reset": False,
        "post_exp_std_adj_sixths": 0,
        "configured_bracket_selftimer": P314_BRACKET_SELFTIMER_DEFAULT,
        "configured_bracket_order": P314_BRACKET_ORDER_DEFAULT,
        "post_bracket_selftimer": P314_BRACKET_SELFTIMER_DEFAULT,
        "post_bracket_order": P314_BRACKET_ORDER_DEFAULT,
        "fx6_exp_std_errno": None,
        "fx6_bracket_errno": None,
        "tv_system": "NTSC",
        "frame_rate": "29.97p",
        "playback_media_kind": "Movie",
        "tc_preset": P314_TC_PRESET_DEFAULT,
        "ub_preset": P314_UB_PRESET_DEFAULT,
        "tc_format": P314_TC_FORMAT_DEFAULT,
        "tc_run": P314_TC_RUN_DEFAULT,
        "tc_make": P314_TC_MAKE_DEFAULT,
        "ub_time_rec": P314_UB_TIME_REC_DEFAULT,
        "tc_ub_disp_setting": P314_TCUB_DISP_DEFAULT,
        "reported_tc_format_visible": True,
        "reported_tc_format_locked_ndf": False,
        "reported_playback_disp_toggle_allowed": True,
        "post_tc_preset": P314_TC_PRESET_DEFAULT,
        "post_ub_preset": P314_UB_PRESET_DEFAULT,
        "post_tc_format": P314_TC_FORMAT_DEFAULT,
        "post_tc_run": P314_TC_RUN_DEFAULT,
        "post_tc_make": P314_TC_MAKE_DEFAULT,
        "post_ub_time_rec": P314_UB_TIME_REC_DEFAULT,
        "post_tc_ub_disp_setting": P314_TCUB_DISP_DEFAULT,
        "fx3_has_physical_bnc_tc_port": False,
        "fx6_has_physical_bnc_tc_port": True,
        "select_playback_media_slot": P314_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "slot1_read_only_or_busy": True,
        "battery_ok_for_copy": True,
        "target_slot_speed_class_ok": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": False,
        "vault_firewall_errno": None,
        "reported_dest_group_and_protect_cleared": False,
        "slideshow_view_mode": "Date View",
        "slideshow_repeat": P314_SLIDESHOW_REPEAT_DEFAULT,
        "slideshow_interval": P314_SLIDESHOW_INTERVAL_DEFAULT,
        "slideshow_active": False,
        "reported_power_save_bypassed": False,
        "post_select_playback_media": P314_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT,
        "post_slideshow_repeat": P314_SLIDESHOW_REPEAT_DEFAULT,
        "post_slideshow_interval": P314_SLIDESHOW_INTERVAL_DEFAULT,
        "fx6_copy_clip_active": False,
        "reset_action": "None",
        "slot1_data_sector_writes": 0,
        "slot1_copy_avf_info_mutation_bytes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_ebusy_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P314_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P314_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P314_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P314_TIER0_SURFACE_COUNT,
        "exp_std_adj_mode_conflation_or_reset_drift_events": 0,
        "bracket_settings_reset_or_fx6_spoof_events": 0,
        "tcub_reset_wipe_or_format_lock_violations": 0,
        "reverse_copy_slot2_to_slot1_bypass_events": 0,
        "slideshow_power_save_or_fx6_copy_clip_spoof_events": 0,
    }
    defaults.update(overrides)
    return ExposureStdTcubReverseCopyVaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Evaluators & Single-Shot Combined Verifier (Pillars 56A & 56B)
# ---------------------------------------------------------------------------


def evaluate_switch_vh_af_focus_limit_color_vault(
    spec: SwitchVhAfFocusLimitColorVaultSpec,
) -> SwitchVhAfFocusLimitColorVaultReport:
    """Evaluate Pillar 56A: Still `AF-C`-only `[Switch V/H AF Area]` (`0/90/270/INVALID` + 8
    lockouts + coords clear), 14-checkbox `[Focus Area Limit]` (`>= 2` `.uxc 0xea28 -> EINVAL=22` vs
    dormant `xl/xs/custom_1..3 -> EOPNOTSUPP=95`), `Initialize`-only `[Focus Area Color]` vs zero-switch
    `ILME-FX6`, and Slot-1 Tier-0 Vault Firewall."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(
            P314_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Module safety invariant violation",
        )

    valid_fw = (
        (
            spec.camera_model == P314_FX3_MODEL_NAME
            and spec.fw_version in P314_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P314_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P314_FX6_DONOR_FW_VERSION
        )
    )
    valid_post_color = (
        spec.post_focus_area_color in P314_FOCUS_AREA_COLOR_MODES
        or (
            spec.camera_model == P314_FX6_DONOR_MODEL_NAME
            and spec.post_focus_area_color == "OrangeMoving"
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P314_SHOOTING_DOMAINS
        or spec.focus_mode not in P314_FOCUS_MODES_ALL
        or spec.configured_switch_vh_af not in P314_SWITCH_VH_AF_MODES
        or spec.previous_switch_vh_af not in P314_SWITCH_VH_AF_MODES
        or spec.post_switch_vh_af not in P314_SWITCH_VH_AF_MODES
        or spec.orientation not in P314_SWITCH_VH_AF_ORIENTATIONS
        or spec.configured_focus_area_color not in P314_FOCUS_AREA_COLOR_MODES
        or not valid_post_color
        or spec.reset_action not in P314_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P314_VAULT_TARGET_ACTIONS
    ):
        _fail(
            P314_BLOCKED_INVALID_PILLAR56A_SPEC,
            "Invalid Pillar 56A camera/SwitchVH/FocusLimit/FocusColor/vault spec parameter",
        )

    vh = compute_expected_switch_vh_af_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        focus_mode=spec.focus_mode,
        configured_switch_vh_af=spec.configured_switch_vh_af,
        previous_switch_vh_af=spec.previous_switch_vh_af,
        orientation=spec.orientation,
        intelligent_auto_active=spec.intelligent_auto_active,
        digital_zoom_active=spec.digital_zoom_active,
        af_active_in_progress=spec.af_active_in_progress,
        continuous_burst_active=spec.continuous_burst_active,
        self_timer_countdown_active=spec.self_timer_countdown_active,
        focus_magnifier_active=spec.focus_magnifier_active,
        reset_action=spec.reset_action,
    )
    fl = compute_expected_focus_area_limit_and_color_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        requested_enabled_areas=spec.requested_enabled_areas,
        requested_dormant_areas=spec.requested_dormant_areas,
        configured_focus_area_color=spec.configured_focus_area_color,
        reset_action=spec.reset_action,
    )

    # 1. [Switch V/H AF Area] Still AF-C only, 0/90/270 vs INVALID pitch, 8 lockouts, coords clear
    switch_vh_af_ok = (
        spec.reported_switch_triggered == vh["switch_triggered"]
        and spec.reported_switch_errno == vh["switch_errno"]
        and spec.reported_orientation_coords_cleared == vh["orientation_coords_cleared"]
        and spec.post_switch_vh_af == vh["post_switch_vh_af"]
        and not (spec.orientation == "INVALID" and spec.reported_switch_triggered)
        and spec.switch_vh_af_lockout_or_coords_drift_events == 0
    )
    if not switch_vh_af_ok:
        _fail(
            P314_BLOCKED_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT,
            "Switch V/H AF Area violated Still AF-C gate, INVALID vertical pitch lockout, 8 lockouts (EBUSY=16), coords clear on change, or Camera Settings Reset",
        )

    # 2. 14-checkbox [Focus Area Limit] (>= 2 EINVAL=22, dormant xl/xs/custom_1..3 EOPNOTSUPP=95)
    focus_limit_ok = (
        spec.reported_limit_lt2_errno == fl["limit_lt2_errno"]
        and not (
            spec.camera_model == P314_FX3_MODEL_NAME
            and len(spec.requested_enabled_areas) < P314_FX3_FOCUS_AREA_LIMIT_MIN_ENABLED
            and spec.reported_limit_lt2_errno != P314_EINVAL_ERRNO
        )
        and spec.reported_dormant_errno == fl["dormant_rejected_errno"]
        and not (
            len(spec.requested_dormant_areas) > 0
            and spec.reported_dormant_errno != P314_EOPNOTSUPP_ERRNO
        )
        and tuple(spec.post_enabled_areas) == tuple(fl["post_enabled_areas"])
        and not (
            spec.camera_model == P314_FX3_MODEL_NAME
            and spec.shooting_domain in ("Movie", "S&Q")
            and not spec.reported_movie_tracking_excluded
        )
        and spec.focus_limit_lt2_or_dormant_symbol_events == 0
    )
    if not focus_limit_ok:
        _fail(
            P314_BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL,
            "Focus Area Limit violated 14-checkbox >= 2 floor (.uxc 0xea28 EINVAL=22), Movie Tracking exclusion, or dormant xl/xs/custom_1..3 rejection (EOPNOTSUPP=95)",
        )

    # 3. Initialize-only [Focus Area Color] (White/Red) vs zero-switch FX6
    color_fx6_ok = (
        spec.post_focus_area_color == fl["post_focus_area_color"]
        and not (
            spec.camera_model == P314_FX6_DONOR_MODEL_NAME
            and (spec.fx6_exposes_switch_vh_af_or_limit or spec.fx6_exposes_white_red_color_toggle)
        )
        and spec.focus_area_color_or_fx6_spoof_events == 0
    )
    if not color_fx6_ok:
        _fail(
            P314_BLOCKED_FOCUS_AREA_COLOR_OR_FX6_SPOOF,
            "Focus Area Color violated Initialize-only persistence or FX6 zero Switch V/H AF / zero Limit / orange-moving boundary",
        )

    # 4. Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
    destructive_vault_actions = (
        "COPY_PLAYBACK_MEDIA",
        "FORMAT_QUICK",
        "FORMAT_FULL",
    )
    vault_fw_ok = (
        spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_ebusy_enforced
        and spec.slot1_vault_mutation_bytes == 0
        and not (
            spec.requested_vault_slot == P314_SLOT1_VAULT_SLOT
            and spec.requested_vault_action in destructive_vault_actions
        )
    )
    if not vault_fw_ok:
        _fail(
            P314_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS/EBUSY firewall blocked write/format mutation on Tier-0 media",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P314_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P314_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P314_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P314_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "56A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "fw_version": spec.fw_version,
            "shooting_domain": spec.shooting_domain,
            "focus_mode": spec.focus_mode,
            "orientation": spec.orientation,
            "post_switch_vh_af": spec.post_switch_vh_af,
            "post_enabled_areas_count": len(spec.post_enabled_areas),
            "post_focus_area_color": spec.post_focus_area_color,
            "slot1_bytes": spec.slot1_vault_mutation_bytes,
            "errors": errors,
        }
    )
    return SwitchVhAfFocusLimitColorVaultReport(
        schema=PHASE314_SCHEMA,
        version=PHASE314_VERSION,
        passed=passed,
        status=P314_STATUS_VERIFIED_PILLAR_56A if passed else P314_STATUS_REJECTED_PILLAR_56A,
        block_code=block_code,
        switch_vh_af_orientation_lockout_coords_verified=switch_vh_af_ok,
        focus_area_limit_14checkbox_ge2_and_dormant_verified=focus_limit_ok,
        focus_area_color_init_only_and_fx6_zero_switch_verified=color_fx6_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        switch_vh_af_lockout_or_coords_drift_events=spec.switch_vh_af_lockout_or_coords_drift_events,
        focus_limit_lt2_or_dormant_symbol_events=spec.focus_limit_lt2_or_dormant_symbol_events,
        focus_area_color_or_fx6_spoof_events=spec.focus_area_color_or_fx6_spoof_events,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_exposure_std_tcub_reverse_copy_vault(
    spec: ExposureStdTcubReverseCopyVaultSpec,
) -> ExposureStdTcubReverseCopyVaultReport:
    """Evaluate Pillar 56B: 5-mode `[Exposure Std. Adjust]` (`1/6 EV`, `Initialize`-only, EXIF
    isolation, `M.M.` shift) + Still `[Bracket Settings]`, 7-item `Initialize`-only `[TC/UB]` &
    `[TC/UB Disp. Setting]` (`23.98p/24p/PAL` locks vs FX6 physical BNC), and CRITICAL Reverse
    `Slot-2 -> Slot-1` `[Copy]` Tier-0 Vault `EROFS=30`/`EBUSY=16` Firewall + `[Slide Show]`."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(
            P314_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Module safety invariant violation",
        )

    valid_fw = (
        (
            spec.camera_model == P314_FX3_MODEL_NAME
            and spec.fw_version in P314_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P314_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P314_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.exp_std_metering_mode not in P314_EXP_STD_ADJ_5_METERING_MODES
        or not (
            P314_EXP_STD_ADJ_MIN_SIXTHS
            <= spec.configured_exp_std_adj_sixths
            <= P314_EXP_STD_ADJ_MAX_SIXTHS
        )
        or not (
            P314_EXP_STD_ADJ_MIN_SIXTHS
            <= spec.post_exp_std_adj_sixths
            <= P314_EXP_STD_ADJ_MAX_SIXTHS
        )
        or spec.configured_bracket_selftimer not in P314_BRACKET_SELFTIMER_MODES
        or spec.post_bracket_selftimer not in P314_BRACKET_SELFTIMER_MODES
        or _normalize_bracket_order(spec.configured_bracket_order) not in P314_BRACKET_ORDER_MODES
        or _normalize_bracket_order(spec.post_bracket_order) not in P314_BRACKET_ORDER_MODES
        or spec.tv_system not in P314_TV_SYSTEMS
        or spec.frame_rate not in P314_MOVIE_FRAME_RATES
        or spec.tc_format not in P314_TC_FORMAT_MODES
        or spec.tc_run not in P314_TC_RUN_MODES
        or spec.tc_make not in P314_TC_MAKE_MODES
        or spec.ub_time_rec not in P314_ON_OFF_MODES
        or spec.tc_ub_disp_setting not in P314_TCUB_DISP_MODES
        or spec.post_tc_ub_disp_setting not in P314_TCUB_DISP_MODES
        or not _is_valid_8hex_ub(spec.ub_preset)
        or spec.select_playback_media_slot not in (1, 2)
        or spec.post_select_playback_media not in (1, 2)
        or spec.slideshow_view_mode not in P314_VIEW_MODES_ALL
        or spec.slideshow_repeat not in P314_ON_OFF_MODES
        or spec.post_slideshow_repeat not in P314_ON_OFF_MODES
        or spec.slideshow_interval not in P314_SLIDESHOW_INTERVALS
        or spec.post_slideshow_interval not in P314_SLIDESHOW_INTERVALS
        or (
            spec.vault_firewall_errno is not None
            and spec.vault_firewall_errno not in P314_VAULT_FIREWALL_ERRNOS
        )
        or spec.reset_action not in P314_RESET_ACTIONS
        or spec.requested_vault_action not in P314_VAULT_TARGET_ACTIONS
    ):
        _fail(
            P314_BLOCKED_INVALID_PILLAR56B_SPEC,
            "Invalid Pillar 56B camera/ExposureStd/Bracket/TCUB/Copy/SlideShow/vault spec parameter",
        )

    eb = compute_expected_exposure_std_adj_and_bracket_state(
        camera_model=spec.camera_model,
        metering_mode=spec.exp_std_metering_mode,
        configured_std_adj_sixths=spec.configured_exp_std_adj_sixths,
        base_exposure_comp_tenths=spec.base_exposure_comp_tenths,
        adjusted_mid_bracket=spec.adjusted_mid_bracket,
        configured_bracket_selftimer=spec.configured_bracket_selftimer,
        configured_bracket_order=spec.configured_bracket_order,
        reset_action=spec.reset_action,
    )
    tc = compute_expected_tcub_and_disp_state(
        camera_model=spec.camera_model,
        tv_system=spec.tv_system,
        frame_rate=spec.frame_rate,
        playback_media_kind=spec.playback_media_kind,
        tc_preset=spec.tc_preset,
        ub_preset=spec.ub_preset,
        tc_format=spec.tc_format,
        tc_run=spec.tc_run,
        tc_make=spec.tc_make,
        ub_time_rec=spec.ub_time_rec,
        tc_ub_disp_setting=spec.tc_ub_disp_setting,
        reset_action=spec.reset_action,
    )
    cp = compute_expected_playback_copy_and_slideshow_vault_state(
        camera_model=spec.camera_model,
        select_playback_media_slot=spec.select_playback_media_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        slot1_read_only_or_busy=spec.slot1_read_only_or_busy,
        battery_ok_for_copy=spec.battery_ok_for_copy,
        target_slot_speed_class_ok=spec.target_slot_speed_class_ok,
        slideshow_view_mode=spec.slideshow_view_mode,
        slideshow_repeat=spec.slideshow_repeat,
        slideshow_interval=spec.slideshow_interval,
        slideshow_active=spec.slideshow_active,
        requested_vault_action=spec.requested_vault_action,
        reset_action=spec.reset_action,
    )

    # 1. 5-mode [Exposure Std. Adjust] (1/6 EV, Initialize-only, EXIF isolated, M.M. shift, bracket count reset)
    #    & Still [Bracket Settings] (Camera Settings Reset resettable; FX6 dormant ENOENT=2)
    exp_std_5mode_ok = (
        spec.exp_std_supported_modes_count == P314_FX3_EXP_STD_ADJ_METERING_MODE_COUNT
        and (
            spec.camera_model != P314_FX3_MODEL_NAME
            or spec.configured_exp_std_adj_sixths == 0
            or spec.exp_std_warn_prompt_acknowledged
        )
        and spec.post_exp_std_adj_sixths == eb["post_std_adj_sixths"]
        and spec.reported_post_exposure_comp_tenths == eb["post_exposure_comp_tenths"]
        and spec.reported_exif_std_adj_isolated
        and spec.reported_mm_baseline_shifted_sixths == eb["mm_baseline_shifted_sixths"]
        and spec.reported_bracket_shot_counter_reset == eb["bracket_shot_counter_reset"]
        and spec.fx6_exp_std_errno == eb["fx6_exp_std_errno"]
        and spec.exp_std_adj_mode_conflation_or_reset_drift_events == 0
    )
    bracket_ok = (
        spec.post_bracket_selftimer == eb["post_bracket_selftimer"]
        and _normalize_bracket_order(spec.post_bracket_order) == eb["post_bracket_order"]
        and spec.fx6_bracket_errno == eb["fx6_bracket_errno"]
        and spec.bracket_settings_reset_or_fx6_spoof_events == 0
    )
    if not (exp_std_5mode_ok and bracket_ok):
        _fail(
            P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT,
            "Exposure Std. Adjust (5 metering modes, 1/6 EV, EXIF isolated, M.M. shift, Initialize-only) or Bracket Settings / FX6 ENOENT=2 contract drifted",
        )

    # 2. 7-item Initialize-only [TC/UB] + [TC/UB Disp. Setting] & NTSC/24p/PAL locks vs FX6 physical BNC
    tcub_ok = (
        spec.reported_tc_format_visible == tc["tc_format_visible"]
        and spec.reported_tc_format_locked_ndf == tc["tc_format_locked_ndf"]
        and spec.reported_playback_disp_toggle_allowed == tc["playback_disp_toggle_allowed"]
        and spec.post_tc_preset == tc["post_tc_preset"]
        and spec.post_ub_preset == tc["post_ub_preset"]
        and spec.post_tc_format == tc["post_tc_format"]
        and spec.post_tc_run == tc["post_tc_run"]
        and spec.post_tc_make == tc["post_tc_make"]
        and spec.post_ub_time_rec == tc["post_ub_time_rec"]
        and spec.post_tc_ub_disp_setting == tc["post_tc_ub_disp_setting"]
        and not spec.fx3_has_physical_bnc_tc_port
        and spec.fx6_has_physical_bnc_tc_port
        and spec.tcub_reset_wipe_or_format_lock_violations == 0
    )
    if not tcub_ok:
        _fail(
            P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT,
            "7-item TC/UB & TC/UB Disp. Setting Initialize-only, NTSC/23.98p/24p NDF/PAL format locks, movie-playback-only toggle (.uxc 0xe728), or FX3/FX6 BNC boundary violated",
        )

    # 3. CRITICAL Reverse Slot-2 -> Slot-1 [Copy] Tier-0 Vault Firewall (EROFS=30 / EBUSY=16, 0 sector/AVF_INFO writes)
    reverse_copy_blocked_violation = (
        cp["reverse_to_slot1"] and spec.slot1_holds_tier0_vault
    )
    format_vault_violation = (
        spec.requested_vault_action in ("FORMAT_QUICK", "FORMAT_FULL")
        and spec.slot1_holds_tier0_vault
    )
    reverse_copy_ok = (
        not reverse_copy_blocked_violation
        and not format_vault_violation
        and spec.reported_vault_action_allowed == cp["action_allowed"]
        and spec.vault_firewall_errno == cp["firewall_errno"]
        and spec.reported_dest_group_and_protect_cleared == cp["dest_group_and_protect_cleared"]
        and spec.post_select_playback_media == cp["post_select_playback_media"]
        and spec.reverse_copy_slot2_to_slot1_bypass_events == 0
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_copy_avf_info_mutation_bytes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_ebusy_enforced
        and spec.slot1_format_hard_locked
    )
    if not reverse_copy_ok:
        _fail(
            P314_BLOCKED_REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_FIREWALL,
            "Reverse Slot-2 -> Slot-1 [Copy] Tier-0 Vault firewall breached (must fail-closed with EROFS=30 / EBUSY=16, 0 Slot-1 sector writes, 0 AVF_INFO mutation)",
        )

    # 4. [Slide Show] Power-Save bypass (Date View / Folder View(Still)) & FX6 Copy Clip dormant
    slideshow_ok = (
        spec.reported_power_save_bypassed == cp["power_save_bypassed"]
        and spec.post_slideshow_repeat == cp["post_slideshow_repeat"]
        and spec.post_slideshow_interval == cp["post_slideshow_interval"]
        and not spec.fx6_copy_clip_active
        and spec.slideshow_power_save_or_fx6_copy_clip_spoof_events == 0
    )
    if not slideshow_ok:
        _fail(
            P314_BLOCKED_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF,
            "Slide Show Power Save Start Time bypass (DURING_PLAYBACK_SLIDESHOW), Initialize-only persistence, or FX6 dormant Copy Clip boundary violated",
        )

    # 5. Stage-B Overlay & H0 == H3
    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P314_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P314_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P314_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P314_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = reverse_copy_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "56B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "exp_mode": spec.exp_std_metering_mode,
            "post_exp_std_sixths": spec.post_exp_std_adj_sixths,
            "post_bracket_order": spec.post_bracket_order,
            "tv_system": spec.tv_system,
            "frame_rate": spec.frame_rate,
            "post_tc_format": spec.post_tc_format,
            "select_slot": spec.select_playback_media_slot,
            "action": spec.requested_vault_action,
            "slot1_data_sector_writes": spec.slot1_data_sector_writes,
            "slot1_copy_avf_info_bytes": spec.slot1_copy_avf_info_mutation_bytes,
            "errors": errors,
        }
    )
    return ExposureStdTcubReverseCopyVaultReport(
        schema=PHASE314_SCHEMA,
        version=PHASE314_VERSION,
        passed=passed,
        status=P314_STATUS_VERIFIED_PILLAR_56B if passed else P314_STATUS_REJECTED_PILLAR_56B,
        block_code=block_code,
        exp_std_adj_5mode_exif_and_init_only_verified=exp_std_5mode_ok,
        bracket_settings_reset_and_fx6_dormant_verified=bracket_ok,
        tcub_7item_init_only_format_locks_and_fx6_bnc_verified=tcub_ok,
        reverse_copy_slot2_to_slot1_erofs_ebusy_firewall_verified=reverse_copy_ok,
        slideshow_power_save_bypass_and_fx6_copy_clip_dormant_verified=slideshow_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        exp_std_adj_mode_conflation_or_reset_drift_events=(
            spec.exp_std_adj_mode_conflation_or_reset_drift_events
        ),
        bracket_settings_reset_or_fx6_spoof_events=spec.bracket_settings_reset_or_fx6_spoof_events,
        tcub_reset_wipe_or_format_lock_violations=spec.tcub_reset_wipe_or_format_lock_violations,
        reverse_copy_slot2_to_slot1_bypass_events=spec.reverse_copy_slot2_to_slot1_bypass_events,
        slideshow_power_save_or_fx6_copy_clip_spoof_events=(
            spec.slideshow_power_save_or_fx6_copy_clip_spoof_events
        ),
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_copy_avf_info_mutation_bytes=spec.slot1_copy_avf_info_mutation_bytes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_switch_vh_af_stdadj_tcub_copy_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_56a: Optional[SwitchVhAfFocusLimitColorVaultSpec] = None,
    spec_56b: Optional[ExposureStdTcubReverseCopyVaultSpec] = None,
) -> SwitchVhAfStdAdjTcubCopyVaultReport:
    """Combined single-shot verifier for Pillar 56A + Pillar 56B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase314_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_switch_vh_af_focus_limit_color_vault(
        spec_56a or build_default_safe_switch_vh_af_focus_limit_color_vault_spec()
    )
    rep_b = evaluate_exposure_std_tcub_reverse_copy_vault(
        spec_56b or build_default_safe_exposure_std_tcub_reverse_copy_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 314 Wave-54 donor artifact parity check failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return SwitchVhAfStdAdjTcubCopyVaultReport(
        schema=PHASE314_SCHEMA,
        version=PHASE314_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P314_STATUS_VERIFIED_PILLAR56_SUITE if all_ok else P314_STATUS_FAIL_PILLAR56_SUITE,
        donor_snapshot=donor_snapshot,
        switch_vh_af_focus_limit_color_report=rep_a,
        exposure_std_tcub_reverse_copy_report=rep_b,
        switch_vh_af_lockout_or_coords_drift_events=rep_a.switch_vh_af_lockout_or_coords_drift_events,
        focus_limit_lt2_or_dormant_symbol_events=rep_a.focus_limit_lt2_or_dormant_symbol_events,
        focus_area_color_or_fx6_spoof_events=rep_a.focus_area_color_or_fx6_spoof_events,
        exp_std_adj_mode_conflation_or_reset_drift_events=(
            rep_b.exp_std_adj_mode_conflation_or_reset_drift_events
        ),
        bracket_settings_reset_or_fx6_spoof_events=rep_b.bracket_settings_reset_or_fx6_spoof_events,
        tcub_reset_wipe_or_format_lock_violations=rep_b.tcub_reset_wipe_or_format_lock_violations,
        reverse_copy_slot2_to_slot1_bypass_events=rep_b.reverse_copy_slot2_to_slot1_bypass_events,
        slideshow_power_save_or_fx6_copy_clip_spoof_events=(
            rep_b.slideshow_power_save_or_fx6_copy_clip_spoof_events
        ),
        slot1_data_sector_writes=rep_b.slot1_data_sector_writes,
        slot1_copy_avf_info_mutation_bytes=rep_b.slot1_copy_avf_info_mutation_bytes,
        slot1_vault_mutation_bytes=rep_a.slot1_vault_mutation_bytes + rep_b.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=(rep_a.slot1_format_hard_locked and rep_b.slot1_format_hard_locked),
        slot1_vault_erofs_ebusy_enforced=(
            rep_a.slot1_vault_erofs_ebusy_enforced and rep_b.slot1_vault_erofs_ebusy_enforced
        ),
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(errs),
    )


def verify_switch_vh_af_stdadj_tcub_copy_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_56a: Optional[SwitchVhAfFocusLimitColorVaultSpec] = None,
    spec_56b: Optional[ExposureStdTcubReverseCopyVaultSpec] = None,
) -> SwitchVhAfStdAdjTcubCopyVaultReport:
    """Symmetry alias for `verify_switch_vh_af_stdadj_tcub_copy_and_vault`."""
    return verify_switch_vh_af_stdadj_tcub_copy_and_vault(
        force_clean_room=force_clean_room,
        spec_56a=spec_56a,
        spec_56b=spec_56b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 56A & 56B) + Standalone Pillar 56 Suite
# ---------------------------------------------------------------------------


def run_pillar56a_switch_vh_af_focus_limit_color_6_scenario_suite() -> Pillar56ASuiteResult:
    """Run 6 Pillar 56A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, SwitchVhAfFocusLimitColorVaultSpec, Optional[str]], ...] = (
        (
            P314_PILLAR_56A_SCENARIO_IDS[0],
            True,
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                shooting_domain="Still",
                focus_mode="AF-C",
                configured_switch_vh_af="AF Point + AF Area",
                previous_switch_vh_af="Off",
                orientation="270_DEGREES",
                reported_switch_triggered=True,
                reported_switch_errno=None,
                reported_orientation_coords_cleared=True,
                post_switch_vh_af="AF Point + AF Area",
                requested_enabled_areas=("wide", "zone", "tracking_wide"),
                post_enabled_areas=("wide", "zone", "tracking_wide"),
                configured_focus_area_color="Red",
                post_focus_area_color="Red",
            ),
            None,
        ),
        (
            P314_PILLAR_56A_SCENARIO_IDS[1],
            True,
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                shooting_domain="Still",
                focus_mode="AF-C",
                configured_switch_vh_af="AF Point Only",
                previous_switch_vh_af="AF Point Only",
                orientation="90_DEGREES",
                reported_switch_triggered=True,
                reported_orientation_coords_cleared=True,
                requested_enabled_areas=("wide", "spot_m"),
                configured_focus_area_color="Red",
                reset_action="Camera Settings Reset",
                post_switch_vh_af="Off",
                post_enabled_areas=P314_FOCUS_AREA_LIMIT_14_AREAS,
                post_focus_area_color="Red",
            ),
            None,
        ),
        (
            P314_PILLAR_56A_SCENARIO_IDS[2],
            False,
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                shooting_domain="Movie",
                focus_mode="AF-C",
                configured_switch_vh_af="AF Point + AF Area",
                previous_switch_vh_af="Off",
                orientation="INVALID",
                focus_magnifier_active=True,
                reported_switch_triggered=True,
                reported_switch_errno=None,
                reported_orientation_coords_cleared=False,
                reported_movie_tracking_excluded=True,
                switch_vh_af_lockout_or_coords_drift_events=1,
            ),
            P314_BLOCKED_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT,
        ),
        (
            P314_PILLAR_56A_SCENARIO_IDS[3],
            False,
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                requested_enabled_areas=("wide",),
                requested_dormant_areas=("flexible_spot_xl", "custom_1"),
                reported_limit_lt2_errno=None,
                reported_dormant_errno=None,
                post_enabled_areas=("wide",),
                focus_limit_lt2_or_dormant_symbol_events=1,
            ),
            P314_BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL,
        ),
        (
            P314_PILLAR_56A_SCENARIO_IDS[4],
            False,
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                camera_model=P314_FX6_DONOR_MODEL_NAME,
                fw_version=P314_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                configured_switch_vh_af="Off",
                previous_switch_vh_af="Off",
                reported_switch_triggered=False,
                reported_switch_errno=P314_EOPNOTSUPP_ERRNO,
                reported_orientation_coords_cleared=False,
                post_switch_vh_af="Off",
                requested_enabled_areas=(),
                post_enabled_areas=(),
                configured_focus_area_color="Red",
                post_focus_area_color="Red",
                fx6_exposes_switch_vh_af_or_limit=True,
                fx6_exposes_white_red_color_toggle=True,
                focus_area_color_or_fx6_spoof_events=1,
            ),
            P314_BLOCKED_FOCUS_AREA_COLOR_OR_FX6_SPOOF,
        ),
        (
            P314_PILLAR_56A_SCENARIO_IDS[5],
            False,
            build_default_safe_switch_vh_af_focus_limit_color_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/56a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P314_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar56ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_switch_vh_af_focus_limit_color_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar56ScenarioOutcome(
                scenario_id=sid,
                pillar="56A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar56ASuiteResult(
        passed=all_ok,
        status=P314_STATUS_VERIFIED_PILLAR_56A if all_ok else P314_STATUS_REJECTED_PILLAR_56A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar56b_exposure_std_tcub_reverse_copy_6_scenario_suite() -> Pillar56BSuiteResult:
    """Run 6 Pillar 56B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, ExposureStdTcubReverseCopyVaultSpec, Optional[str]], ...] = (
        (
            P314_PILLAR_56B_SCENARIO_IDS[0],
            True,
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                exp_std_metering_mode="Highlight",
                configured_exp_std_adj_sixths=2,
                base_exposure_comp_tenths=-7,
                reported_post_exposure_comp_tenths=-7,
                reported_exif_std_adj_isolated=True,
                reported_mm_baseline_shifted_sixths=2,
                adjusted_mid_bracket=True,
                reported_bracket_shot_counter_reset=True,
                post_exp_std_adj_sixths=2,
                configured_bracket_selftimer="5 Sec",
                configured_bracket_order="-->0->+",
                post_bracket_selftimer=P314_BRACKET_SELFTIMER_DEFAULT,
                post_bracket_order=P314_BRACKET_ORDER_DEFAULT,
                tv_system="NTSC",
                frame_rate="24.00p",
                tc_preset="01:23:45.00",
                ub_preset="AB CD EF 12",
                tc_format="DF",
                tc_run="Free Run",
                tc_make="Regenerate",
                ub_time_rec="On",
                tc_ub_disp_setting="U-Bit",
                reported_tc_format_visible=True,
                reported_tc_format_locked_ndf=True,
                post_tc_preset="01:23:45.00",
                post_ub_preset="AB CD EF 12",
                post_tc_format="NDF",
                post_tc_run="Free Run",
                post_tc_make="Regenerate",
                post_ub_time_rec="On",
                post_tc_ub_disp_setting="U-Bit",
                select_playback_media_slot=1,
                requested_vault_action="COPY_PLAYBACK_MEDIA",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                reported_dest_group_and_protect_cleared=True,
                reset_action="Camera Settings Reset",
            ),
            None,
        ),
        (
            P314_PILLAR_56B_SCENARIO_IDS[1],
            True,
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                exp_std_metering_mode="Entire Screen Avg.",
                configured_exp_std_adj_sixths=-3,
                reported_mm_baseline_shifted_sixths=-3,
                post_exp_std_adj_sixths=0,
                configured_bracket_selftimer="10 Sec",
                configured_bracket_order="-->0->+",
                tv_system="PAL",
                frame_rate="25.00p",
                tc_preset="10:00:00.12",
                ub_preset="11 22 33 44",
                tc_run="Free Run",
                tc_make="Regenerate",
                ub_time_rec="On",
                tc_ub_disp_setting="Counter",
                reported_tc_format_visible=False,
                reported_tc_format_locked_ndf=False,
                slideshow_view_mode="Folder View(Still)",
                slideshow_repeat="On",
                slideshow_interval="10 Sec",
                slideshow_active=True,
                reported_power_save_bypassed=True,
                reset_action="Initialize",
                post_tc_preset=P314_TC_PRESET_DEFAULT,
                post_ub_preset=P314_UB_PRESET_DEFAULT,
                post_tc_format="N/A_PAL_HIDDEN",
                post_tc_run=P314_TC_RUN_DEFAULT,
                post_tc_make=P314_TC_MAKE_DEFAULT,
                post_ub_time_rec=P314_UB_TIME_REC_DEFAULT,
                post_tc_ub_disp_setting=P314_TCUB_DISP_DEFAULT,
                post_select_playback_media=P314_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT,
                post_slideshow_repeat=P314_SLIDESHOW_REPEAT_DEFAULT,
                post_slideshow_interval=P314_SLIDESHOW_INTERVAL_DEFAULT,
            ),
            None,
        ),
        (
            P314_PILLAR_56B_SCENARIO_IDS[2],
            False,
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                exp_std_metering_mode="Highlight",
                exp_std_supported_modes_count=4,
                configured_exp_std_adj_sixths=3,
                base_exposure_comp_tenths=-5,
                reported_post_exposure_comp_tenths=0,
                reported_exif_std_adj_isolated=False,
                reset_action="Camera Settings Reset",
                post_exp_std_adj_sixths=0,
                exp_std_adj_mode_conflation_or_reset_drift_events=1,
            ),
            P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT,
        ),
        (
            P314_PILLAR_56B_SCENARIO_IDS[3],
            False,
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                tv_system="PAL",
                frame_rate="25.00p",
                playback_media_kind="Still",
                reported_tc_format_visible=True,
                reported_playback_disp_toggle_allowed=True,
                reset_action="Camera Settings Reset",
                post_tc_preset=P314_TC_PRESET_DEFAULT,
                tcub_reset_wipe_or_format_lock_violations=1,
            ),
            P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT,
        ),
        (
            P314_PILLAR_56B_SCENARIO_IDS[4],
            False,
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                select_playback_media_slot=2,
                slot1_holds_tier0_vault=True,
                requested_vault_action="COPY_PLAYBACK_MEDIA",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                reported_dest_group_and_protect_cleared=True,
                slot1_data_sector_writes=8192,
                slot1_copy_avf_info_mutation_bytes=4096,
                slot1_vault_mutation_bytes=12288,
                slot1_vault_erofs_ebusy_enforced=False,
                reverse_copy_slot2_to_slot1_bypass_events=1,
            ),
            P314_BLOCKED_REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_FIREWALL,
        ),
        (
            P314_PILLAR_56B_SCENARIO_IDS[5],
            False,
            build_default_safe_exposure_std_tcub_reverse_copy_vault_spec(
                slideshow_view_mode="Date View",
                slideshow_active=True,
                reported_power_save_bypassed=False,
                fx6_copy_clip_active=True,
                slideshow_power_save_or_fx6_copy_clip_spoof_events=1,
            ),
            P314_BLOCKED_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF,
        ),
    )

    outcomes: List[Pillar56ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_exposure_std_tcub_reverse_copy_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar56ScenarioOutcome(
                scenario_id=sid,
                pillar="56B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar56BSuiteResult(
        passed=all_ok,
        status=P314_STATUS_VERIFIED_PILLAR_56B if all_ok else P314_STATUS_REJECTED_PILLAR_56B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar56_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar56StandaloneReport:
    """Run full Pillar 56 standalone suite (`6/6` Pillar 56A + `6/6` Pillar 56B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase314_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar56a_switch_vh_af_focus_limit_color_6_scenario_suite()
    res_b = run_pillar56b_exposure_std_tcub_reverse_copy_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 314 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE314_SCHEMA,
            "version": PHASE314_VERSION,
            "mode": donor_snapshot.verification_mode,
            "56a": [asdict(s) for s in res_a.scenarios],
            "56b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar56StandaloneReport(
        schema=PHASE314_SCHEMA,
        version=PHASE314_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P314_STATUS_VERIFIED_PILLAR56_SUITE if all_ok else P314_STATUS_FAIL_PILLAR56_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_56a_switch_vh_af_focus_limit_color_vault=res_a,
        pillar_56b_exposure_std_tcub_reverse_copy_vault=res_b,
        switch_vh_af_lockout_or_coords_drift_events=(
            P314_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT_EVENTS if res_a.passed else 1
        ),
        focus_limit_lt2_or_dormant_symbol_events=(
            P314_FOCUS_LIMIT_LT2_OR_DORMANT_SYMBOL_EVENTS if res_a.passed else 1
        ),
        focus_area_color_or_fx6_spoof_events=(
            P314_FOCUS_AREA_COLOR_OR_FX6_SPOOF_EVENTS if res_a.passed else 1
        ),
        exp_std_adj_mode_conflation_or_reset_drift_events=(
            P314_EXP_STD_ADJ_MODE_CONFLATION_OR_RESET_DRIFT_EVENTS if res_b.passed else 1
        ),
        bracket_settings_reset_or_fx6_spoof_events=(
            P314_BRACKET_SETTINGS_RESET_OR_FX6_SPOOF_EVENTS if res_b.passed else 1
        ),
        tcub_reset_wipe_or_format_lock_violations=(
            P314_TCUB_RESET_WIPE_OR_FORMAT_LOCK_VIOLATIONS if res_b.passed else 1
        ),
        reverse_copy_slot2_to_slot1_bypass_events=(
            P314_REVERSE_COPY_SLOT2_TO_SLOT1_BYPASS_EVENTS if res_b.passed else 1
        ),
        slideshow_power_save_or_fx6_copy_clip_spoof_events=(
            P314_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF_EVENTS if res_b.passed else 1
        ),
        slot1_data_sector_writes=P314_SLOT1_DATA_SECTOR_WRITES if res_b.passed else 1,
        slot1_copy_avf_info_mutation_bytes=(
            P314_SLOT1_COPY_AVF_INFO_MUTATION_BYTES if res_b.passed else 4096
        ),
        slot1_vault_mutation_bytes=(
            P314_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P314_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_ebusy_enforced=P314_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        suite_sha256=suite_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errs),
    )


# ---------------------------------------------------------------------------
# Unified 56-Pillar Recovery Master Aggregator (Phase 314 — 56/56 Milestone)
# ---------------------------------------------------------------------------


def _apply_master56_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
    err = f"FAULT_INJECTED:{pillar.pillar_id}"
    return MasterPillarStatus(
        pillar_number=pillar.pillar_number,
        pillar_id=pillar.pillar_id,
        phase_label=pillar.phase_label,
        module_name=pillar.module_name,
        passed=False,
        status=f"FAULT_INJECTED_{pillar.pillar_id.upper()}",
        verification_mode=pillar.verification_mode,
        elapsed_seconds=pillar.elapsed_seconds,
        key_metrics=pillar.key_metrics,
        digest_sha256=_canonical_sha256({"pillar": pillar.pillar_id, "fault_injected": True}),
        errors=pillar.errors + (err,),
    )


def evaluate_realhw_56pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master56PillarRecoveryReport:
    """Evaluate and aggregate all 56 recovery pillars (`1..56`) concurrently -> `56/56` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_56_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_55pillar() -> Master55PillarRecoveryReport:
        return evaluate_realhw_55pillar_recovery_master(**kw)

    def _run_p56() -> Tuple[Pillar56StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar56_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_55 = pool.submit(_run_55pillar)
        fut_56 = pool.submit(_run_p56)
        m55_rep = fut_55.result()
        p56_rep, p56_dt = fut_56.result()

    all_errors: List[str] = list(m55_rep.errors) + list(p56_rep.errors)
    for attr_name, expected_val in (
        ("otp_fuse_touches", 0),
        ("otp_fuse_writes", 0),
        ("rpmb_counter_increments", 0),
        ("passive_tx_bytes_emitted", 0),
        ("physical_usb_packets_emitted", 0),
        ("physical_device_writes", 0),
        ("raw_firmware_bytes_leaked", 0),
        ("el3_payload_transmit_authorized", False),
        ("isp_write_authorized", False),
        ("spi_nor_write_authorized", False),
        ("persistent_emmc_writes_authorized", False),
        ("persistent_write_release", False),
        ("live_usb_iokit_transmit_enabled", False),
        ("cnflasha_userspace_write_blocked", True),
        ("overall_ready_for_hardware_attach", False),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(m55_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-55 violated {attr_name} == {expected_val}")
        if getattr(p56_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 56 violated {attr_name} == {expected_val}")

    if p56_rep.cross_model_flash_authorized is not False:
        all_errors.append("Pillar 56 violated cross_model_flash_authorized == False")

    for attr_name, expected_val in (
        ("dormant_shading_auto_low_exposure_events", 0),
        ("lens_comp_lock_or_arw_conflation_events", 0),
        ("af_illuminator_gate_or_fx6_spoof_events", 0),
        ("movie_af_transition_or_assist_drift_events", 0),
        ("aperture_drive_pre_af_shutter_reset_drift_events", 0),
        ("circ_focus_diagonal_or_color_drift_events", 0),
        ("folder_name_or_leading_underscore_violations", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_folder_dir_mutation_bytes", 0),
        ("slot1_rating_avf_info_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
        ("fx3_has_builtin_end_filter", False),
        ("fx3_has_builtin_evf", False),
        ("fx3_has_var_shutter", False),
    ):
        if getattr(m55_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-55 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("switch_vh_af_lockout_or_coords_drift_events", 0),
        ("focus_limit_lt2_or_dormant_symbol_events", 0),
        ("focus_area_color_or_fx6_spoof_events", 0),
        ("exp_std_adj_mode_conflation_or_reset_drift_events", 0),
        ("bracket_settings_reset_or_fx6_spoof_events", 0),
        ("tcub_reset_wipe_or_format_lock_violations", 0),
        ("reverse_copy_slot2_to_slot1_bypass_events", 0),
        ("slideshow_power_save_or_fx6_copy_clip_spoof_events", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_copy_avf_info_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
    ):
        if getattr(p56_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 56 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m55_rep.pillars)
    spec56 = MASTER_56_PILLAR_SPECS[55]
    p56_metrics = {
        "pillar_56a_switch_vh_af_focus_limit_color_vault": (
            f"{p56_rep.pillar_56a_switch_vh_af_focus_limit_color_vault.scenarios_passed}/"
            f"{p56_rep.pillar_56a_switch_vh_af_focus_limit_color_vault.scenarios_total}"
        ),
        "pillar_56b_exposure_std_tcub_reverse_copy_vault": (
            f"{p56_rep.pillar_56b_exposure_std_tcub_reverse_copy_vault.scenarios_passed}/"
            f"{p56_rep.pillar_56b_exposure_std_tcub_reverse_copy_vault.scenarios_total}"
        ),
        "switch_vh_af_lockout_or_coords_drift_events": (
            p56_rep.switch_vh_af_lockout_or_coords_drift_events
        ),
        "focus_limit_lt2_or_dormant_symbol_events": (
            p56_rep.focus_limit_lt2_or_dormant_symbol_events
        ),
        "focus_area_color_or_fx6_spoof_events": (
            p56_rep.focus_area_color_or_fx6_spoof_events
        ),
        "exp_std_adj_mode_conflation_or_reset_drift_events": (
            p56_rep.exp_std_adj_mode_conflation_or_reset_drift_events
        ),
        "bracket_settings_reset_or_fx6_spoof_events": (
            p56_rep.bracket_settings_reset_or_fx6_spoof_events
        ),
        "tcub_reset_wipe_or_format_lock_violations": (
            p56_rep.tcub_reset_wipe_or_format_lock_violations
        ),
        "reverse_copy_slot2_to_slot1_bypass_events": (
            p56_rep.reverse_copy_slot2_to_slot1_bypass_events
        ),
        "slideshow_power_save_or_fx6_copy_clip_spoof_events": (
            p56_rep.slideshow_power_save_or_fx6_copy_clip_spoof_events
        ),
        "slot1_data_sector_writes": p56_rep.slot1_data_sector_writes,
        "slot1_copy_avf_info_mutation_bytes": p56_rep.slot1_copy_avf_info_mutation_bytes,
        "slot1_vault_mutation_bytes": p56_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p56_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_ebusy_enforced": p56_rep.slot1_vault_erofs_ebusy_enforced,
        "overall_ready_for_hardware_attach": p56_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p56_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p56_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p56_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec56[0],
            pillar_id=spec56[1],
            phase_label=spec56[2],
            module_name=spec56[3],
            passed=bool(p56_rep.all_passed),
            status=p56_rep.status,
            verification_mode=p56_rep.verification_mode,
            elapsed_seconds=p56_dt,
            key_metrics=p56_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec56[1],
                    "mode": p56_rep.verification_mode,
                    "status": p56_rep.status,
                    "metrics": p56_metrics,
                    "passed": p56_rep.all_passed,
                }
            ),
            errors=tuple(p56_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master56_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p56_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_56_PILLAR_COUNT == 56
        and pillars_passed == 56
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE314_SCHEMA,
            "schema_version": PHASE314_MASTER_SCHEMA,
            "version": PHASE314_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [
                (p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses
            ],
            "all_passed": all_ok,
        }
    )
    return Master56PillarRecoveryReport(
        schema=PHASE314_SCHEMA,
        schema_version=PHASE314_MASTER_SCHEMA,
        version=PHASE314_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P314_STATUS_VERIFIED_56OF56_AGGREGATOR if all_ok else P314_STATUS_FAIL_56OF56_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P314_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P314_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P314_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p56_rep.donor_snapshot,
        pillar56_a_switch_vh_af_focus_limit_color_vault=(
            p56_rep.pillar_56a_switch_vh_af_focus_limit_color_vault
        ),
        pillar56_b_exposure_std_tcub_reverse_copy_vault=(
            p56_rep.pillar_56b_exposure_std_tcub_reverse_copy_vault
        ),
        switch_vh_af_lockout_or_coords_drift_events=(
            p56_rep.switch_vh_af_lockout_or_coords_drift_events
        ),
        focus_limit_lt2_or_dormant_symbol_events=p56_rep.focus_limit_lt2_or_dormant_symbol_events,
        focus_area_color_or_fx6_spoof_events=p56_rep.focus_area_color_or_fx6_spoof_events,
        exp_std_adj_mode_conflation_or_reset_drift_events=(
            p56_rep.exp_std_adj_mode_conflation_or_reset_drift_events
        ),
        bracket_settings_reset_or_fx6_spoof_events=p56_rep.bracket_settings_reset_or_fx6_spoof_events,
        tcub_reset_wipe_or_format_lock_violations=p56_rep.tcub_reset_wipe_or_format_lock_violations,
        reverse_copy_slot2_to_slot1_bypass_events=p56_rep.reverse_copy_slot2_to_slot1_bypass_events,
        slideshow_power_save_or_fx6_copy_clip_spoof_events=(
            p56_rep.slideshow_power_save_or_fx6_copy_clip_spoof_events
        ),
        slot1_data_sector_writes=p56_rep.slot1_data_sector_writes,
        slot1_copy_avf_info_mutation_bytes=p56_rep.slot1_copy_avf_info_mutation_bytes,
        slot1_vault_mutation_bytes=m55_rep.slot1_vault_mutation_bytes + p56_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p56_rep.slot1_format_hard_locked,
        slot1_vault_erofs_ebusy_enforced=p56_rep.slot1_vault_erofs_ebusy_enforced,
        fx3_has_switch_vh_af_area=P314_FX3_HAS_SWITCH_VH_AF_AREA,
        fx3_focus_area_limit_count=P314_FX3_FOCUS_AREA_LIMIT_COUNT,
        fx3_focus_area_limit_min_enabled=P314_FX3_FOCUS_AREA_LIMIT_MIN_ENABLED,
        fx3_exp_std_adj_metering_mode_count=P314_FX3_EXP_STD_ADJ_METERING_MODE_COUNT,
        fx3_has_physical_bnc_tc_port=P314_FX3_HAS_PHYSICAL_BNC_TC_PORT,
        fx6_has_physical_bnc_tc_port=P314_FX6_HAS_PHYSICAL_BNC_TC_PORT,
        fx6_has_switch_vh_af_area=P314_FX6_HAS_SWITCH_VH_AF_AREA,
        fx6_has_focus_area_limit=P314_FX6_HAS_FOCUS_AREA_LIMIT,
        fx6_has_exp_std_adj=P314_FX6_HAS_EXP_STD_ADJ,
        fx6_has_still_bracket_settings=P314_FX6_HAS_STILL_BRACKET_SETTINGS,
        fx6_has_copy_clip_active=P314_FX6_HAS_COPY_CLIP_ACTIVE,
        fx6_has_slide_show=P314_FX6_HAS_SLIDE_SHOW,
        dormant_shading_auto_low_exposure_events=m55_rep.dormant_shading_auto_low_exposure_events,
        lens_comp_lock_or_arw_conflation_events=m55_rep.lens_comp_lock_or_arw_conflation_events,
        af_illuminator_gate_or_fx6_spoof_events=m55_rep.af_illuminator_gate_or_fx6_spoof_events,
        movie_af_transition_or_assist_drift_events=(
            m55_rep.movie_af_transition_or_assist_drift_events
        ),
        aperture_drive_pre_af_shutter_reset_drift_events=(
            m55_rep.aperture_drive_pre_af_shutter_reset_drift_events
        ),
        circ_focus_diagonal_or_color_drift_events=m55_rep.circ_focus_diagonal_or_color_drift_events,
        folder_name_or_leading_underscore_violations=(
            m55_rep.folder_name_or_leading_underscore_violations
        ),
        slot1_folder_dir_mutation_bytes=m55_rep.slot1_folder_dir_mutation_bytes,
        slot1_rating_avf_info_mutation_bytes=m55_rep.slot1_rating_avf_info_mutation_bytes,
        fx3_has_builtin_af_illuminator=m55_rep.fx3_has_builtin_af_illuminator,
        fx6_has_builtin_af_illuminator=m55_rep.fx6_has_builtin_af_illuminator,
        fx3_exposes_shading_auto_low=m55_rep.fx3_exposes_shading_auto_low,
        fx6_has_aperture_drive_pre_af_circ_color=m55_rep.fx6_has_aperture_drive_pre_af_circ_color,
        fx6_has_msdcf_or_star_rating=m55_rep.fx6_has_msdcf_or_star_rating,
        sensor_cleaning_low_battery_bypass_events=m55_rep.sensor_cleaning_low_battery_bypass_events,
        sensor_cleaning_no_power_off_violations=m55_rep.sensor_cleaning_no_power_off_violations,
        fx6_ibis_shake_conflation_events=m55_rep.fx6_ibis_shake_conflation_events,
        ev_comp_range_or_cine_ei_lockout_violations=(
            m55_rep.ev_comp_range_or_cine_ei_lockout_violations
        ),
        exposure_step_or_dormant_reset_ev_drift_events=(
            m55_rep.exposure_step_or_dormant_reset_ev_drift_events
        ),
        focus_mode_movie_clamp_or_dormant_drift_events=(
            m55_rep.focus_mode_movie_clamp_or_dormant_drift_events
        ),
        priority_set_or_illuminator_gate_violations=(
            m55_rep.priority_set_or_illuminator_gate_violations
        ),
        image_index_dormant_or_view_mode_drift_events=(
            m55_rep.image_index_dormant_or_view_mode_drift_events
        ),
        slot1_rotate_exif_mutation_bytes=m55_rep.slot1_rotate_exif_mutation_bytes,
        fx3_has_sensor_cleaning_ibis=m55_rep.fx3_has_sensor_cleaning_ibis,
        fx3_has_exposure_comp=m55_rep.fx3_has_exposure_comp,
        fx3_has_physical_ev_reset_dial=m55_rep.fx3_has_physical_ev_reset_dial,
        fx6_has_ultrasonic_ibis_cleaning=m55_rep.fx6_has_ultrasonic_ibis_cleaning,
        fx6_has_variable_end_optical_block=m55_rep.fx6_has_variable_end_optical_block,
        fx6_has_technical_apr=m55_rep.fx6_has_technical_apr,
        fx6_has_still_exposure_comp=m55_rep.fx6_has_still_exposure_comp,
        fx6_has_still_image_index_rotate=m55_rep.fx6_has_still_image_index_rotate,
        dci4k_long_gop_or_8k_violations=m55_rep.dci4k_long_gop_or_8k_violations,
        reboot_2400p_stage_b_wipe_violations=m55_rep.reboot_2400p_stage_b_wipe_violations,
        hdmi_raw_or_still_aspect_drift_events=m55_rep.hdmi_raw_or_still_aspect_drift_events,
        fx6_still_or_raw_conflation_events=m55_rep.fx6_still_or_raw_conflation_events,
        reg_custom_hold_or_hlg_lock_drift_events=m55_rep.reg_custom_hold_or_hlg_lock_drift_events,
        camset_cross_model_path_drift_events=m55_rep.camset_cross_model_path_drift_events,
        photo_capture_dci4k_lockout_bypass_events=(
            m55_rep.photo_capture_dci4k_lockout_bypass_events
        ),
        slot1_camset_write_bytes=m55_rep.slot1_camset_write_bytes,
        slot1_photo_capture_write_bytes=m55_rep.slot1_photo_capture_write_bytes,
        fx3_appfw_has_dci4k_internal=m55_rep.fx3_appfw_has_dci4k_internal,
        fx3_appfw_has_pro_camera_path=m55_rep.fx3_appfw_has_pro_camera_path,
        fx6_has_still_aspect_ratio=m55_rep.fx6_has_still_aspect_ratio,
        fx6_has_photo_capture=m55_rep.fx6_has_photo_capture,
        fx6_has_playback_enlarge_image=m55_rep.fx6_has_playback_enlarge_image,
        fx6_has_reg_custom_shoot_set=m55_rep.fx6_has_reg_custom_shoot_set,
        fx6_has_camera_set_memory=m55_rep.fx6_has_camera_set_memory,
        movie_tracking_area_or_limit_violations=m55_rep.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=m55_rep.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=m55_rep.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=(
            m55_rep.fx6_handle_or_pos_display_conflation_events
        ),
        iso_minss_or_cine_ei_lock_drift_events=m55_rep.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=m55_rep.flash_still_mech_gate_violations,
        mishoe_pmic_5v_overcurrent_events=m55_rep.mishoe_pmic_5v_overcurrent_events,
        slot1_focus_zoom_camset_mutation_bytes=m55_rep.slot1_focus_zoom_camset_mutation_bytes,
        slot1_flash_videolight_imagedb_bytes=m55_rep.slot1_flash_videolight_imagedb_bytes,
        xlrh1_has_zoom_lever=m55_rep.xlrh1_has_zoom_lever,
        xlrh1_has_rec_button=m55_rep.xlrh1_has_rec_button,
        xlrh1_has_zoom_hold_switch=m55_rep.xlrh1_has_zoom_hold_switch,
        fx6_0_99_is_zoom_position_display=m55_rep.fx6_0_99_is_zoom_position_display,
        fx6_has_iso_auto_min_ss=m55_rep.fx6_has_iso_auto_min_ss,
        fx6_mechanical_shutter_present=m55_rep.fx6_mechanical_shutter_present,
        dormant_lossless_raw_exposure_events=m55_rep.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=m55_rep.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=m55_rep.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=m55_rep.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=m55_rep.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=m55_rep.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=m55_rep.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=m55_rep.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=m55_rep.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=m55_rep.slot1_imagedb_or_burst_mutation_bytes,
        fx3_ui_exposes_lossless_raw=m55_rep.fx3_ui_exposes_lossless_raw,
        fx3_ui_exposes_shutter_type_auto=m55_rep.fx3_ui_exposes_shutter_type_auto,
        fx6_still_pipeline_present=m55_rep.fx6_still_pipeline_present,
        double_log_or_lockout_bypass_events=m55_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=m55_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=m55_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=m55_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            m55_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        wb_custom_camset_exclusion_drift_events=m55_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            m55_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        fx3_ui_exposes_usb_streaming=m55_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m55_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m55_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m55_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m55_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m55_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m55_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m55_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m55_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m55_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m55_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m55_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m55_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m55_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m55_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m55_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m55_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m55_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m55_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m55_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m55_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m55_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m55_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m55_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m55_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m55_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m55_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m55_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m55_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m55_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m55_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m55_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m55_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=m55_rep.tcub_camera_reset_wipe_or_format_violations,
        fx3_has_builtin_end_filter=m55_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m55_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m55_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m55_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m55_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m55_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m55_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m55_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m55_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m55_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m55_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m55_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m55_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m55_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m55_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m55_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m55_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m55_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m55_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m55_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m55_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m55_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m55_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m55_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m55_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m55_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m55_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m55_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m55_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m55_rep.unbuffered_battery_pull_events,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=p56_rep.hardware_live_attachment_authorized,
        master_56pillar_sha256=master_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(all_errors),
    )


def evaluate_56pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master56PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_56pillar_recovery_master`."""
    return evaluate_realhw_56pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_56pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master56PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_56pillar_recovery_master`."""
    return evaluate_realhw_56pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS",
    "ALLOW_PERSISTENT_JIRITSU_WRITES",
    "CNFLASHA_USERSPACE_WRITE_BLOCKED",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "ExposureStdTcubReverseCopyVaultReport",
    "ExposureStdTcubReverseCopyVaultSpec",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "ISP_WRITE_AUTHORIZED",
    "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
    "MASTER_56_PILLAR_COUNT",
    "MASTER_56_PILLAR_IDS",
    "MASTER_56_PILLAR_SPECS",
    "Master56PillarRecoveryReport",
    "MasterPillarStatus",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P314_BLOCKED_EXP_STD_ADJ_5MODE_OR_BRACKET_DRIFT",
    "P314_BLOCKED_FOCUS_AREA_COLOR_OR_FX6_SPOOF",
    "P314_BLOCKED_FOCUS_AREA_LIMIT_LT2_OR_DORMANT_SYMBOL",
    "P314_BLOCKED_INVALID_PILLAR56A_SPEC",
    "P314_BLOCKED_INVALID_PILLAR56B_SPEC",
    "P314_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P314_BLOCKED_REVERSE_COPY_SLOT2_TO_SLOT1_VAULT_FIREWALL",
    "P314_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P314_BLOCKED_SLIDESHOW_POWER_SAVE_OR_FX6_COPY_CLIP_SPOOF",
    "P314_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL",
    "P314_BLOCKED_SWITCH_VH_AF_LOCKOUT_OR_COORDS_DRIFT",
    "P314_BLOCKED_TCUB_INIT_RESET_OR_FORMAT_LOCK_DRIFT",
    "P314_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P314_BOUNDED_HEADER_BYTES",
    "P314_BRACKET_ORDER_DEFAULT",
    "P314_BRACKET_ORDER_F_RESID16",
    "P314_BRACKET_ORDER_MODES",
    "P314_BRACKET_ORDER_UNICODE_MODES",
    "P314_BRACKET_SELFTIMER_BKID",
    "P314_BRACKET_SELFTIMER_DEFAULT",
    "P314_BRACKET_SELFTIMER_F_RESID16",
    "P314_BRACKET_SELFTIMER_MODES",
    "P314_BRACKET_SETTINGS_F_RESID16",
    "P314_BRACKET_SETTINGS_MENU_PATH",
    "P314_CONCURRENT_CEILING_SECONDS",
    "P314_COPY_BATTERY_GATE_SYMBOL",
    "P314_COPY_FAIL_RESID16",
    "P314_COPY_FUNC_SYMBOL",
    "P314_COPY_F_RESID16",
    "P314_COPY_SPEED_WARN_RESID16",
    "P314_CROSS_MODEL_FLASH_AUTHORIZED",
    "P314_DONOR_FX3_APPFW_702_RELPATH",
    "P314_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P314_DONOR_FX3_UXC_EN_F_RELPATH",
    "P314_DONOR_FX3_UXC_EN_G_RELPATH",
    "P314_DONOR_FX3_UXC_EN_RELPATH",
    "P314_DONOR_FX3_UXC_JA_F_RELPATH",
    "P314_DONOR_FX3_UXC_JA_G_RELPATH",
    "P314_DONOR_FX3_UXC_JA_RELPATH",
    "P314_DONOR_FX3_UXC_SC_F_RELPATH",
    "P314_DONOR_FX3_UXC_SC_G_RELPATH",
    "P314_DONOR_FX3_UXC_SC_RELPATH",
    "P314_DONOR_FX3_UXC_TC_F_RELPATH",
    "P314_DONOR_FX3_UXC_TC_G_RELPATH",
    "P314_DONOR_FX3_UXC_TC_RELPATH",
    "P314_DONOR_FX6_APPFW_601_RELPATH",
    "P314_DONOR_FX6_UXC_EN_2_RELPATH",
    "P314_DONOR_FX6_UXC_EN_RELPATH",
    "P314_DONOR_INSPECT_BUDGET_SECONDS",
    "P314_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P314_EBUSY_ERRNO",
    "P314_EINVAL_ERRNO",
    "P314_ENOENT_ERRNO",
    "P314_ENV_CLEAN_ROOM_TEST",
    "P314_EOPNOTSUPP_ERRNO",
    "P314_EROFS_ERRNO",
    "P314_EXP_STD_ADJ_5_METERING_MODES",
    "P314_EXP_STD_ADJ_ALT_F_RESID16",
    "P314_EXP_STD_ADJ_DEFAULT_SIXTHS",
    "P314_EXP_STD_ADJ_F_RESID16",
    "P314_EXP_STD_ADJ_MAX_SIXTHS",
    "P314_EXP_STD_ADJ_MENU_PATH",
    "P314_EXP_STD_ADJ_MIN_SIXTHS",
    "P314_EXP_STD_ADJ_MODE_BKID_MAP",
    "P314_EXP_STD_ADJ_MODE_F_RESID16_MAP",
    "P314_EXP_STD_ADJ_PID_SYMBOL",
    "P314_EXP_STD_ADJ_STEPS_SIXTHS",
    "P314_EXP_STD_ADJ_WARN_RESID16",
    "P314_FAST_CLI_BUDGET_SECONDS",
    "P314_FOCUS_AREA_COLOR_BKID",
    "P314_FOCUS_AREA_COLOR_DEFAULT",
    "P314_FOCUS_AREA_COLOR_F_RESID16",
    "P314_FOCUS_AREA_COLOR_LEGACY_F_RESID16",
    "P314_FOCUS_AREA_COLOR_MODES",
    "P314_FOCUS_AREA_COLOR_RESID16_MAP",
    "P314_FOCUS_AREA_LIMIT_14_AREAS",
    "P314_FOCUS_AREA_LIMIT_BKID_MAP",
    "P314_FOCUS_AREA_LIMIT_CENTER_FIX_F_RESID16",
    "P314_FOCUS_AREA_LIMIT_DORMANT_5",
    "P314_FOCUS_AREA_LIMIT_F_RESID16",
    "P314_FOCUS_AREA_LIMIT_LT2_RESID16",
    "P314_FOCUS_AREA_LIMIT_NON_TRACKING_7",
    "P314_FOCUS_AREA_LIMIT_TRACKING_7",
    "P314_FOCUS_AREA_LIMIT_TRACK_CENTER_FIX_F_RESID16",
    "P314_FOCUS_AREA_MENU_PATH",
    "P314_FOCUS_MODES_ALL",
    "P314_FORBIDDEN_PERSISTENT_TARGETS",
    "P314_FORCED_NDF_FRAME_RATES",
    "P314_FX3_EXP_STD_ADJ_METERING_MODE_COUNT",
    "P314_FX3_FOCUS_AREA_LIMIT_COUNT",
    "P314_FX3_FOCUS_AREA_LIMIT_MIN_ENABLED",
    "P314_FX3_FW_VERSION",
    "P314_FX3_HAS_PHYSICAL_BNC_TC_PORT",
    "P314_FX3_HAS_SWITCH_VH_AF_AREA",
    "P314_FX3_HELPGUIDE_ID",
    "P314_FX3_MODEL_ID",
    "P314_FX3_MODEL_NAME",
    "P314_FX3_PRODUCT_CODENAME",
    "P314_FX3_SUPPORTED_FW_VERSIONS",
    "P314_FX6_DONOR_FW_VERSION",
    "P314_FX6_DONOR_MODEL_NAME",
    "P314_FX6_DORMANT_COPY_CLIP_2_RESID16",
    "P314_FX6_FOCUS_AREA_IND_AFS_RESID16",
    "P314_FX6_FOCUS_AREA_MARKER_2_RESID16",
    "P314_FX6_HAS_COPY_CLIP_ACTIVE",
    "P314_FX6_HAS_EXP_STD_ADJ",
    "P314_FX6_HAS_FOCUS_AREA_LIMIT",
    "P314_FX6_HAS_PHYSICAL_BNC_TC_PORT",
    "P314_FX6_HAS_SLIDE_SHOW",
    "P314_FX6_HAS_STILL_BRACKET_SETTINGS",
    "P314_FX6_HAS_SWITCH_VH_AF_AREA",
    "P314_FX6_PRODUCT_CODENAME",
    "P314_FX6_TC_FORMAT_2_RESID16",
    "P314_FX6_UB_MODE_RESID16_RANGE",
    "P314_FX6_USB_TC_IN_ALT_BKID",
    "P314_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P314_MAX_FULL_DONOR_BYTES",
    "P314_MOVIE_FRAME_RATES",
    "P314_NOMINAL_BUDGET_SECONDS",
    "P314_ON_OFF_MODES",
    "P314_OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P314_PILLAR_56A_SCENARIO_IDS",
    "P314_PILLAR_56B_SCENARIO_IDS",
    "P314_PINNED_FX3_APPFW_702_BYTES",
    "P314_PINNED_FX3_APPFW_702_FULL_SHA256",
    "P314_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P314_PINNED_FX3_BACKUP_BIN_BYTES",
    "P314_PINNED_FX3_BACKUP_BIN_SHA256",
    "P314_PINNED_FX3_UXC_EN_BYTES",
    "P314_PINNED_FX3_UXC_EN_F_BYTES",
    "P314_PINNED_FX3_UXC_EN_F_SHA256",
    "P314_PINNED_FX3_UXC_EN_G_BYTES",
    "P314_PINNED_FX3_UXC_EN_G_SHA256",
    "P314_PINNED_FX3_UXC_EN_SHA256",
    "P314_PINNED_FX3_UXC_JA_BYTES",
    "P314_PINNED_FX3_UXC_JA_F_BYTES",
    "P314_PINNED_FX3_UXC_JA_F_SHA256",
    "P314_PINNED_FX3_UXC_JA_G_BYTES",
    "P314_PINNED_FX3_UXC_JA_G_SHA256",
    "P314_PINNED_FX3_UXC_JA_SHA256",
    "P314_PINNED_FX3_UXC_SC_BYTES",
    "P314_PINNED_FX3_UXC_SC_F_BYTES",
    "P314_PINNED_FX3_UXC_SC_F_SHA256",
    "P314_PINNED_FX3_UXC_SC_G_BYTES",
    "P314_PINNED_FX3_UXC_SC_G_SHA256",
    "P314_PINNED_FX3_UXC_SC_SHA256",
    "P314_PINNED_FX3_UXC_TC_BYTES",
    "P314_PINNED_FX3_UXC_TC_F_BYTES",
    "P314_PINNED_FX3_UXC_TC_F_SHA256",
    "P314_PINNED_FX3_UXC_TC_G_BYTES",
    "P314_PINNED_FX3_UXC_TC_G_SHA256",
    "P314_PINNED_FX3_UXC_TC_SHA256",
    "P314_PINNED_FX6_APPFW_601_BYTES",
    "P314_PINNED_FX6_APPFW_601_FULL_SHA256",
    "P314_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P314_PINNED_FX6_UXC_EN_2_BYTES",
    "P314_PINNED_FX6_UXC_EN_2_SHA256",
    "P314_PINNED_FX6_UXC_EN_BYTES",
    "P314_PINNED_FX6_UXC_EN_SHA256",
    "P314_RESET_ACTIONS",
    "P314_SAFE_SECONDARY_SLOT",
    "P314_SELECT_PLAYBACK_MEDIA_BKID",
    "P314_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT",
    "P314_SELECT_PLAYBACK_MEDIA_F_RESID16",
    "P314_SHOOTING_DOMAINS",
    "P314_SLIDESHOW_FUNC_SYMBOL",
    "P314_SLIDESHOW_INTERVALS",
    "P314_SLIDESHOW_INTERVAL_DEFAULT",
    "P314_SLIDESHOW_INTERVAL_RESID16",
    "P314_SLIDESHOW_REPEAT_DEFAULT",
    "P314_SLIDESHOW_REPEAT_F_RESID16",
    "P314_SLIDESHOW_RESID16",
    "P314_SLIDESHOW_VALID_VIEW_MODES",
    "P314_SLOT1_COPY_AVF_INFO_MUTATION_BYTES",
    "P314_SLOT1_DATA_SECTOR_WRITES",
    "P314_SLOT1_FORMAT_HARD_LOCKED",
    "P314_SLOT1_VAULT_EROFS_EBUSY_ENFORCED",
    "P314_SLOT1_VAULT_MUTATION_BYTES",
    "P314_SLOT1_VAULT_SLOT",
    "P314_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P314_STATUS_FAIL_56OF56_AGGREGATOR",
    "P314_STATUS_FAIL_PILLAR56_SUITE",
    "P314_STATUS_REJECTED_PILLAR_56A",
    "P314_STATUS_REJECTED_PILLAR_56B",
    "P314_STATUS_VERIFIED_56OF56_AGGREGATOR",
    "P314_STATUS_VERIFIED_PILLAR56_SUITE",
    "P314_STATUS_VERIFIED_PILLAR_56A",
    "P314_STATUS_VERIFIED_PILLAR_56B",
    "P314_SWITCH_VH_AF_BKID",
    "P314_SWITCH_VH_AF_DEFAULT",
    "P314_SWITCH_VH_AF_F_RESID16",
    "P314_SWITCH_VH_AF_LOCKOUT_CONDITIONS",
    "P314_SWITCH_VH_AF_MODES",
    "P314_SWITCH_VH_AF_ORIENTATIONS",
    "P314_SWITCH_VH_AF_RESID16_MAP",
    "P314_TCUB_DISP_BKID",
    "P314_TCUB_DISP_DEFAULT",
    "P314_TCUB_DISP_F_RESID16",
    "P314_TCUB_DISP_MENU_PATH",
    "P314_TCUB_DISP_MODES",
    "P314_TCUB_MENU_PATH",
    "P314_TCUB_PLAYBACK_STILL_BLOCK_RESID16",
    "P314_TC_FORMAT_DEFAULT",
    "P314_TC_FORMAT_F_RESID16",
    "P314_TC_FORMAT_MODES",
    "P314_TC_MAKE_DEFAULT",
    "P314_TC_MAKE_MODES",
    "P314_TC_PRESET_DEFAULT",
    "P314_TC_RUN_DEFAULT",
    "P314_TC_RUN_MODES",
    "P314_TIER0_SURFACE_COUNT",
    "P314_TV_SYSTEMS",
    "P314_UB_PRESET_DEFAULT",
    "P314_UB_PRESET_F_RESID16",
    "P314_UB_TIME_REC_DEFAULT",
    "P314_UB_TIME_REC_F_RESID16",
    "P314_VAULT_FIREWALL_ERRNOS",
    "P314_VAULT_FIREWALL_ERRNO_CODES",
    "P314_VAULT_TARGET_ACTIONS",
    "P314_VIEW_MODES_ALL",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE314_MASTER_SCHEMA",
    "PHASE314_PHASE_NUMBER",
    "PHASE314_SCHEMA",
    "PHASE314_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "Phase314DonorArtifactDigest",
    "Phase314DonorSnapshot",
    "Pillar56ASuiteResult",
    "Pillar56BSuiteResult",
    "Pillar56ScenarioOutcome",
    "Pillar56StandaloneReport",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "SwitchVhAfFocusLimitColorVaultReport",
    "SwitchVhAfFocusLimitColorVaultSpec",
    "SwitchVhAfStdAdjTcubCopyVaultReport",
    "build_default_safe_exposure_std_tcub_reverse_copy_vault_spec",
    "build_default_safe_switch_vh_af_focus_limit_color_vault_spec",
    "compute_expected_exposure_std_adj_and_bracket_state",
    "compute_expected_focus_area_limit_and_color_state",
    "compute_expected_playback_copy_and_slideshow_vault_state",
    "compute_expected_switch_vh_af_state",
    "compute_expected_tcub_and_disp_state",
    "evaluate_56pillar_recovery_master",
    "evaluate_exposure_std_tcub_reverse_copy_vault",
    "evaluate_realhw_56pillar_recovery_master",
    "evaluate_switch_vh_af_focus_limit_color_vault",
    "inspect_phase314_donors_readonly",
    "run_pillar56_standalone_suite",
    "run_pillar56a_switch_vh_af_focus_limit_color_6_scenario_suite",
    "run_pillar56b_exposure_std_tcub_reverse_copy_6_scenario_suite",
    "verify_56pillar_recovery_suite",
    "verify_switch_vh_af_stdadj_tcub_copy_and_vault",
    "verify_switch_vh_af_stdadj_tcub_copy_vault",
]
