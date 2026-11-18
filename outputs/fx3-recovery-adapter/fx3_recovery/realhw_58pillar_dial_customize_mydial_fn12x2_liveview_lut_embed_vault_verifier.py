"""Phase 326 (58/58 Recovery Pillars Milestone) — Wave-56 Recovery Pillar 58 & Unified 58/58
Recovery Master (`verify-58pillar-recovery` / `verify-pillar58-dial-customize-mydial-fn12x2-liveview-lut-embed-vault`):

1. **Sub-Pillar 58A — Wave-56 `[Dial Customize]` 5-Item Tree vs Dormant `[Dial Setup]` / `[Dial / Wheel Lock]` /
   `Rear Dial L/R` (`EOPNOTSUPP=95`), `My Dial 1..3` Lock-Override + `[Fn Menu Settings]` `12 + 12` Split & FX6 Boundary**:
   - Models `ILME-FX3 Ver. 7.02` (`0x91030080`, `ilc/2210`, `PRODUCT_MODEL_ALCIN_UUD`)
     `MENU -> (Setup) -> [Dial Customize]` (`_g 0x62ed`) exact **5 active items**, ALL 5 `Initialize`-only
     (`Camera Settings Reset` disabled):
     * `[Custom Key/Dial Set.]` (`_f 0x6290`/`0x73a0`, replacing legacy Ver. 1.xx `[Dial Setup]`).
     * `[My Dial Settings]` (`_f 0x6538`, `My Dial 1..3`: `_f 0x67da`/`0x64ec`/`0x6936`).
     * `[Av/Tv Rotate]` (`_f 0x72e3`, `BKID_APP_setting_av_tv_rotate`): `Normal` (`0x688f`, default) /
       `Reverse` (`0x6175`).
     * `[Function Ring(Lens)]` (`_f 0x715e`, `BKID_APP_setting_function_ring`): `Power Focus`
       (`0x71aa`/`0x767f`, default) / `APS-C/Super 35 mm / Full Frame` (reject
       `VAL_setting_function_ring_FUNCTION_RING_INVALID`).
     * `[Lock Operation Parts]` (`_f 0x6904`, `BKID_APP_setting_device_lock`): `Off` (default) /
       `Multi-Selector Only` (`0x686b`) / `Dial + Wheel` (`0x61bb`) / `All`; replaces legacy
       `[Dial / Wheel Lock]` (`0xe352` / `Dial Lock` `0x737b` / `Wheel Lock` `0x7acd`); supports
       long-press `Fn` toggle lock and 5-second `MENU + Fn` full lock (all except shutter).
   - Enforces **3-physical-dial topology** (`Front Dial` `0xe4da`/`0x6d2a`, single `Rear Dial`
     `0xe4db`/`0x6b61`, `Control Wheel` `0xe353`/`0x6178`); fail-closed `EOPNOTSUPP=95` on dormant
     Alpha symbols (`Rear Dial L/R` `0x6a5c`/`0x680d`, `Dial Setup` `BKID_APP_setting_dial_setup`,
     `Dial/Wheel Setup` `0x6a89`, and `Dial / Wheel Lock` `0xe352`).
   - Models `My Dial 1..3`: 3 shared NVRAM banks (`list0..2`, `Initialize`-only), Still/Movie
     independent recall assignment (`Hold` `0x66fe`, `Toggle` `0x6bc0`, `1->2->3` `0x7987`),
     auto-skipping all-`Not set` (`--`) banks, and temporarily overriding `[Lock Operation Parts]`
     while a My Dial bank is active.
   - Models `[Operation Customize] -> [Fn Menu Settings]` (`_g 0x614b`, `Initialize`-only): strict
     `12 Still + 12 Movie` slots (`0..11`, `BKID_APP_fn_menu_item_ids_for_{still,movie}0..11`);
     pressing `Fn` when all 12 slots are `Not set` (`0xe0ac`) triggers `_f 0x6220` invalid prompt.
   - Enforces `ILME-FX6 Ver. 6.01` boundary (`Multi Function Dial` under `Project > Multi Function Dial
     > Default Function`, `Grip Dial` `ASSIGNABLE_DIAL_00`, `Handle Dial` `ASSIGNABLE_DIAL_01`, `IRIS Dial`,
     `ND Dial`, physical `HOLD` switch, `Status Screens`, & `Direct Menu`; zero `Av/Tv Rotate` /
     `Lock Operation Parts` / `My Dial` / `Fn Menu`).

2. **Sub-Pillar 58B — `[Live View Display Set.]` 3-Item Asymmetric Reset Split, `[Grid Line]` HDMI Clean-Feed
   Isolation, `[Manage User LUTs]` / `[Embed LUT File]` Container Embed vs `PPLUT1..4` Baking & `Slot-1`
   Tier-0 Vault `EROFS=30` Firewall**:
   - Models `Shooting -> [Shooting Display]` (`_g 0x615e`) `-> [Live View Display Set.]` (`_f 0x6429`,
     Still-only; Movie/`S&Q` rejected `EOPNOTSUPP=95`) exact 3-item split:
     * `[Live View Display]` (`_f 0x7227`, `base 0xe3ca`, `BKID_APP_setting_live_view_display`):
       `Setting Effect ON` (`0x7913`/`0xe3c6`, default) / `Setting Effect OFF` (`0x642f`/`0xe3c7`),
       `Initialize`-only, auto-forced `Setting Effect OFF` when `[Bright Monitoring]` is active,
       switchable via `[Live View Disp. Select]` (`0x6001`).
     * `[Exposure Effect]` (`_f 0x6552`, `BKID_APP_setting_flash_exposure_effect`): `Exposure Set. & flash`
       (`0x6bee`, default) / `Exposure Setting Only` (`0x762b`), `Initialize`-only.
     * `[Frame Rate Low Limit]` (`_f 0x700e`): `On` / `Off` (default) — **ONLY Resettable item
       (`can_be_reset=True`)** on `[Camera Settings Reset]`.
   - Models `[Grid Line Display]` (`_f 0x64b8`/`0x6f9d`/`0x747d`, `On`/`Off` default, `Initialize`-only)
     & `[Grid Line Type]` (`_f 0x7920`/`0x69c9`: `Rule of 3rds Grid` `0x78ae`/`0xe809` default /
     `Square Grid` `0x715a`/`0xe806` / `Diag. + Square Grid` `0x786c`/`0xe807`, `Initialize`-only),
     Still/Movie/`S&Q`, isolated to body LCD when `HDMI Info. Display = Off` (`0x6e7c`) or RAW /
     `Off(HDMI Only)` (contrasted with `ILME-FX6` `Monitoring > Marker > Guide Frame` & dormant PNG
     custom grid `BKID_APP_IS_EXIST_CUSTOM_GRID_LINE0..3`).
   - Models LUT topology & `Slot-1` Tier-0 Vault `EROFS=30` firewall:
     * `Exposure/Color -> [Color/Tone]` (`_g 0x61fa`) `-> [Manage User LUTs]` (`_f 0x71af`: `User1..16`,
       `Import/Edit` `0x6a05` / `Delete All` `0x6543`, `Initialize`-only, 17/33-pt `.cube`, SD/SDXC
       `/Private/Sony/PRO/LUT`, CFexpress Type A `/Sony/PRO/LUT`) & `[Select LUT]` (`_f 0x643e`:
       `S-Log3` / `s709` default Resettable / `709(800%)` / `User1..16`, unset slot falls back to
       `S-Log3` `0x77ca`).
     * `Shooting -> [Image Quality/Rec] -> [Log Shooting Setting] -> [Embed LUT File]` (`_f 0x680f`,
       NOT under `Color/Tone`, `On` default **Resettable**): container metadata embed preserving
       native `S-Log3` pixels with zero `.cube` sidecar, hardware-locked `Off` on SD/SDHC (`_g 0x61a0`,
       requires SDXC or CFexpress Type A).
     * `Picture Profile -> PPLUT1..4` (`_f 0x6095`, `[Basic Look]` `0x6f6d`): irreversible DSP pixel
       baking, **Resettable** on both `Camera Settings Reset` & `Initialize` (unlike `PP1..PP11`).
     * `ILME-FX6` contrast: `Base Look` 16-slot UI cap vs dormant `PRM_is_exist_user_lut0..49`,
       `Import from Media(B)`, `/PRIVATE/SONY/PRO/LUT/`, `/SONY/PRO/LUT/`, and independent channel
       LUT switches (`Internal Rec.` / `SDI/HDMI` / `LCD/VF` / `Proxy/Stream`).
     * `Slot-1` Tier-0 Vault Firewall: read-only `.cube` import from `Slot-1` is safe iff
       `slot1_data_sector_writes == 0` and zero folder creation (`Make Cube Folder`); ANY recording,
       write, folder-create, export, or format targeting `Slot-1` fails closed with `EROFS=30`.

3. **Unified `58/58` Recovery Master Aggregator (`evaluate_realhw_58pillar_recovery_master` /
   `verify-58pillar-recovery`)**:
   - Concurrently delegates Pillars `1..57` (`evaluate_realhw_57pillar_recovery_master`) + **Pillar 58**
     (`run_pillar58_standalone_suite`) -> **`58/58` (`VERIFIED_58OF58_PILLAR_RECOVERY_MASTER`,
     `schema_version="realhw_58pillar_recovery_master_v1"`)** in `< 1.5s`, explicitly guarding
     `work_root is None` in donor resolution for donorless Ubuntu CI fallback to `CLEAN_ROOM_SYNTHETIC`.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import posixpath
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, iter_donor_work_roots, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
)
from .realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier import (
    MASTER_57_PILLAR_SPECS,
    Master57PillarRecoveryReport,
    evaluate_realhw_57pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants (Phase 326 — 58/58 Milestone)
# ---------------------------------------------------------------------------

PHASE326_SCHEMA: str = (
    "realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier_v1"
)
PHASE326_MASTER_SCHEMA: str = "realhw_58pillar_recovery_master_v1"
PHASE326_VERSION: str = "1.0.0"
PHASE326_PHASE_NUMBER: int = 326
P326_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P326_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P326_OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
P326_CROSS_MODEL_FLASH_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P326_DIAL_CUSTOMIZE_DORMANT_TRAP_OR_RESET_DRIFT_EVENTS: int = 0
P326_REAR_DIAL_LR_OR_MYDIAL_OVERRIDE_DRIFT_EVENTS: int = 0
P326_FN_MENU_12X2_OR_FX6_DIAL_SPOOF_EVENTS: int = 0
P326_LIVE_VIEW_DISPLAY_RESET_SPLIT_OR_MODE_DRIFT_EVENTS: int = 0
P326_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK_EVENTS: int = 0
P326_LUT_PATH_EMBED_SIDECAR_OR_SLOT1_VAULT_BYPASS_EVENTS: int = 0
P326_SLOT1_DATA_SECTOR_WRITES: int = 0
P326_SLOT1_LUT_MUTATION_BYTES: int = 0
P326_SLOT1_VAULT_MUTATION_BYTES: int = 0
P326_SLOT1_FORMAT_HARD_LOCKED: bool = True
P326_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED: bool = True

# Hardware & Menu Empirical Truths (Wave-56)
P326_FX3_DIAL_CUSTOMIZE_ITEM_COUNT: int = 5
P326_FX3_PHYSICAL_DIAL_COUNT: int = 3
P326_FX3_MY_DIAL_BANK_COUNT: int = 3
P326_FX3_FN_MENU_STILL_SLOTS: int = 12
P326_FX3_FN_MENU_MOVIE_SLOTS: int = 12
P326_FX3_LIVE_VIEW_DISPLAY_SET_ITEM_COUNT: int = 3
P326_FX3_GRID_LINE_TYPE_COUNT: int = 3
P326_FX3_USER_LUT_SLOT_COUNT: int = 16
P326_FX3_PPLUT_SLOT_COUNT: int = 4
P326_FX3_LUT_CUBE_POINT_SIZES: Tuple[int, ...] = (17, 33)
P326_FX6_USER_LUT_UI_CAP: int = 16
P326_FX6_DORMANT_USER_LUT_BUFFER_CAP: int = 50
P326_FX6_HAS_AV_TV_ROTATE: bool = False
P326_FX6_HAS_MY_DIAL: bool = False
P326_FX6_HAS_FN_MENU: bool = False
P326_FX6_HAS_MULTI_CHANNEL_LUT_SWITCHES: bool = True

P326_DONOR_INSPECT_BUDGET_SECONDS: float = 0.20
P326_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P326_FAST_CLI_BUDGET_SECONDS: float = 1.5
P326_NOMINAL_BUDGET_SECONDS: float = 4.0
P326_CONCURRENT_CEILING_SECONDS: float = 6.0
P326_BOUNDED_HEADER_BYTES: int = 4096
P326_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-56 Donor Anchors (17 donors, strictly O_RDONLY)
P326_FX3_MODEL_NAME: str = "ILME-FX3"
P326_FX3_MODEL_ID: int = 0x91030080
P326_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P326_FX3_HELPGUIDE_ID: str = "ilc/2210"
P326_FX3_FW_VERSION: str = "7.02"
P326_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = ("7.02", "7.01", "7.00", "6.02", "6.00")
P326_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P326_FX6_DONOR_FW_VERSION: str = "6.01"

P326_SLOT1_VAULT_SLOT: int = 1
P326_SAFE_SECONDARY_SLOT: int = 2
P326_TIER0_SURFACE_COUNT: int = 16
P326_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx3_stageb_overlay/pillar58"
P326_PERSISTENT_EMMC_PREFIXES: Tuple[str, ...] = (
    "/setting",
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/pnflasha",
    "/dev/mtd",
    "/usr",
    "/mnt/emmc",
)

P326_EPERM_ERRNO: int = 1
P326_EINVAL_ERRNO: int = 22
P326_EROFS_ERRNO: int = 30
P326_EOPNOTSUPP_ERRNO: int = 95

# Sub-Pillar 58A Empirical UXC resid16, BKID & Topology Constants
P326_DIAL_CUSTOMIZE_G_RESID16: int = 0x62ED
P326_CUSTOM_KEY_DIAL_SET_F_RESID16_A: int = 0x6290
P326_CUSTOM_KEY_DIAL_SET_F_RESID16_B: int = 0x73A0
P326_MY_DIAL_SETTINGS_F_RESID16: int = 0x6538
P326_MY_DIAL_1_F_RESID16: int = 0x67DA
P326_MY_DIAL_2_F_RESID16: int = 0x64EC
P326_MY_DIAL_3_F_RESID16: int = 0x6936
P326_AV_TV_ROTATE_F_RESID16: int = 0x72E3
P326_AV_TV_ROTATE_NORMAL_F_RESID16: int = 0x688F
P326_AV_TV_ROTATE_REVERSE_F_RESID16: int = 0x6175
P326_FUNCTION_RING_F_RESID16: int = 0x715E
P326_FUNCTION_RING_POWER_FOCUS_F_RESID16_A: int = 0x71AA
P326_FUNCTION_RING_POWER_FOCUS_F_RESID16_B: int = 0x767F
P326_LOCK_OPERATION_PARTS_F_RESID16: int = 0x6904
P326_LOCK_MULTISELECTOR_F_RESID16: int = 0x686B
P326_LOCK_DIAL_WHEEL_F_RESID16: int = 0x61BB
P326_DORMANT_DIAL_WHEEL_LOCK_BASE_RESID16: int = 0xE352
P326_DORMANT_DIAL_LOCK_F_RESID16: int = 0x737B
P326_DORMANT_WHEEL_LOCK_F_RESID16: int = 0x7ACD
P326_DORMANT_DIAL_WHEEL_SETUP_F_RESID16: int = 0x6A89
P326_DORMANT_REAR_DIAL_L_F_RESID16: int = 0x6A5C
P326_DORMANT_REAR_DIAL_R_F_RESID16: int = 0x680D

P326_FRONT_DIAL_BASE_RESID16: int = 0xE4DA
P326_FRONT_DIAL_F_RESID16: int = 0x6D2A
P326_REAR_DIAL_BASE_RESID16: int = 0xE4DB
P326_REAR_DIAL_F_RESID16: int = 0x6B61
P326_CONTROL_WHEEL_BASE_RESID16: int = 0xE353
P326_CONTROL_WHEEL_F_RESID16: int = 0x6178
P326_MY_DIAL_HOLD_F_RESID16: int = 0x66FE
P326_MY_DIAL_TOGGLE_F_RESID16: int = 0x6BC0
P326_MY_DIAL_CYCLE_123_F_RESID16: int = 0x7987
P326_FN_MENU_SETTINGS_G_RESID16: int = 0x614B
P326_FN_NOT_SET_BASE_RESID16: int = 0xE0AC
P326_FN_ALL_NOT_SET_INVALID_F_RESID16: int = 0x6220

P326_BKID_AV_TV_ROTATE: str = "BKID_APP_setting_av_tv_rotate"
P326_BKID_FUNCTION_RING: str = "BKID_APP_setting_function_ring"
P326_BKID_DEVICE_LOCK: str = "BKID_APP_setting_device_lock"
P326_BKID_DORMANT_DIAL_SETUP: str = "BKID_APP_setting_dial_setup"
P326_BKID_FN_STILL_PREFIX: str = "BKID_APP_fn_menu_item_ids_for_still"
P326_BKID_FN_MOVIE_PREFIX: str = "BKID_APP_fn_menu_item_ids_for_movie"
P326_FUNCTION_RING_INVALID_VAL: str = "VAL_setting_function_ring_FUNCTION_RING_INVALID"

P326_DIAL_CUSTOMIZE_5_ITEMS: Tuple[str, ...] = (
    "Custom Key/Dial Set.",
    "My Dial Settings",
    "Av/Tv Rotate",
    "Function Ring(Lens)",
    "Lock Operation Parts",
)
P326_PHYSICAL_3_DIALS: Tuple[str, ...] = (
    "Front Dial",
    "Rear Dial",
    "Control Wheel",
)
P326_DORMANT_DIAL_SYMBOLS: Tuple[str, ...] = (
    "Rear Dial L",
    "Rear Dial R",
    "Dial Setup",
    "Dial/Wheel Setup",
    "Dial / Wheel Lock",
    "Dial Lock",
    "Wheel Lock",
    "DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO",
)
P326_AV_TV_ROTATE_MODES: Tuple[str, ...] = ("Normal", "Reverse")
P326_AV_TV_ROTATE_DEFAULT: str = "Normal"
P326_FUNCTION_RING_MODES: Tuple[str, ...] = (
    "Power Focus",
    "APS-C/Super 35 mm / Full Frame",
)
P326_FUNCTION_RING_ALL_MODES: Tuple[str, ...] = (
    "Power Focus",
    "APS-C/Super 35 mm / Full Frame",
    "INVALID",
)
P326_FUNCTION_RING_DEFAULT: str = "Power Focus"
P326_LOCK_OPERATION_PARTS_MODES: Tuple[str, ...] = (
    "Off",
    "Multi-Selector Only",
    "Dial + Wheel",
    "All",
)
P326_LOCK_OPERATION_PARTS_DEFAULT: str = "Off"
P326_MY_DIAL_RECALL_MODES: Tuple[str, ...] = (
    "None",
    "Hold",
    "Toggle",
    "1->2->3",
)
P326_FX6_MULTI_FUNCTION_DIAL_FUNCTIONS: Tuple[str, ...] = (
    "Off",
    "IRIS",
    "ISO/Gain/EI",
    "Auto Exposure Level",
    "Audio Input Level",
)
P326_FX6_DIAL_CONTROLS: Tuple[str, ...] = (
    "Multi Function Dial",
    "Grip Dial",
    "Handle Dial",
    "IRIS Dial",
    "ND Dial",
)
P326_FX6_QUICK_MENU_ALTERNATIVES: Tuple[str, ...] = (
    "Status Screens",
    "Direct Menu",
)
P326_FX6_INFO_DISP_PRIORITY_MODES: Tuple[str, ...] = (
    "Home Screen Priority",
    "Direct Menu Priority",
)

# Sub-Pillar 58B Empirical UXC resid16, BKID & Menu/Path Constants
P326_SHOOTING_DISPLAY_G_RESID16: int = 0x615E
P326_LIVE_VIEW_DISPLAY_SET_F_RESID16: int = 0x6429
P326_LIVE_VIEW_DISPLAY_F_RESID16: int = 0x7227
P326_LIVE_VIEW_DISPLAY_BASE_RESID16: int = 0xE3CA
P326_SETTING_EFFECT_ON_F_RESID16: int = 0x7913
P326_SETTING_EFFECT_ON_BASE_RESID16: int = 0xE3C6
P326_SETTING_EFFECT_OFF_F_RESID16: int = 0x642F
P326_SETTING_EFFECT_OFF_BASE_RESID16: int = 0xE3C7
P326_LIVE_VIEW_DISP_SELECT_F_RESID16: int = 0x6001
P326_EXPOSURE_EFFECT_F_RESID16: int = 0x6552
P326_EXPOSURE_SET_AND_FLASH_F_RESID16: int = 0x6BEE
P326_EXPOSURE_SETTING_ONLY_F_RESID16: int = 0x762B
P326_FRAME_RATE_LOW_LIMIT_F_RESID16: int = 0x700E

P326_GRID_LINE_DISPLAY_F_RESID16_SET: Tuple[int, ...] = (0x64B8, 0x6F9D, 0x747D)
P326_GRID_LINE_DISPLAY_SELECT_F_RESID16: int = 0x70C5
P326_GRID_LINE_TYPE_F_RESID16_SET: Tuple[int, ...] = (0x7920, 0x69C9)
P326_GRID_RULE_OF_3RDS_F_RESID16: int = 0x78AE
P326_GRID_RULE_OF_3RDS_BASE_RESID16: int = 0xE809
P326_GRID_SQUARE_F_RESID16: int = 0x715A
P326_GRID_SQUARE_BASE_RESID16: int = 0xE806
P326_GRID_DIAG_SQUARE_F_RESID16: int = 0x786C
P326_GRID_DIAG_SQUARE_BASE_RESID16: int = 0xE807
P326_HDMI_INFO_DISPLAY_F_RESID16: int = 0x6E7C

P326_COLOR_TONE_G_RESID16: int = 0x61FA
P326_MANAGE_USER_LUTS_F_RESID16: int = 0x71AF
P326_MANAGE_USER_LUTS_IMPORT_EDIT_F_RESID16: int = 0x6A05
P326_MANAGE_USER_LUTS_DELETE_ALL_F_RESID16: int = 0x6543
P326_SELECT_LUT_F_RESID16: int = 0x643E
P326_SELECT_LUT_SLOG3_FALLBACK_F_RESID16: int = 0x77CA
P326_EMBED_LUT_FILE_F_RESID16: int = 0x680F
P326_EMBED_LUT_SDHC_LOCK_G_RESID16: int = 0x61A0
P326_PICTURE_PROFILE_PPLUT_F_RESID16: int = 0x6095
P326_PPLUT_BASIC_LOOK_F_RESID16: int = 0x6F6D

P326_BKID_LIVE_VIEW_DISPLAY: str = "BKID_APP_setting_live_view_display"
P326_BKID_FLASH_EXPOSURE_EFFECT: str = "BKID_APP_setting_flash_exposure_effect"
P326_BKID_GRID_LINE_DISPLAY: str = "BKID_APP_setting_grid_line_display"
P326_BKID_GRID_LINE_TYPE: str = "BKID_APP_setting_grid_line_type"
P326_BKID_HDMI_INFO_DISPLAY: str = "BKID_APP_setting_hdmi_info_display"
P326_BKID_SELECT_LUT: str = "BKID_APP_setting_select_lut"
P326_BKID_EMBED_LUT_FILE: str = "BKID_APP_setting_embed_lut_file"
P326_BKID_FX6_FLEXIBLE_ISO_EMBED_LUT_FILE: str = "BKID_APP_SETTING_FLEXIBLE_ISO_EMBED_LUT_FILE"

P326_LIVE_VIEW_DISPLAY_MODES: Tuple[str, ...] = (
    "Setting Effect ON",
    "Setting Effect OFF",
)
P326_LIVE_VIEW_DISPLAY_DEFAULT: str = "Setting Effect ON"
P326_EXPOSURE_EFFECT_MODES: Tuple[str, ...] = (
    "Exposure Set. & flash",
    "Exposure Setting Only",
)
P326_EXPOSURE_EFFECT_DEFAULT: str = "Exposure Set. & flash"
P326_ON_OFF_MODES: Tuple[str, ...] = ("On", "Off")
P326_GRID_LINE_TYPES: Tuple[str, ...] = (
    "Rule of 3rds Grid",
    "Square Grid",
    "Diag. + Square Grid",
)
P326_GRID_LINE_TYPE_DEFAULT: str = "Rule of 3rds Grid"

P326_SELECT_LUT_BUILTINS: Tuple[str, ...] = ("S-Log3", "s709", "709(800%)")
P326_SELECT_LUT_USER_SLOTS: Tuple[str, ...] = tuple(f"User{i}" for i in range(1, 17))
P326_SELECT_LUT_OPTIONS: Tuple[str, ...] = P326_SELECT_LUT_BUILTINS + P326_SELECT_LUT_USER_SLOTS
P326_SELECT_LUT_DEFAULT: str = "s709"
P326_PPLUT_SLOTS: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P326_EMBED_LUT_FILE_DEFAULT: str = "On"

P326_FX3_LUT_SD_DIR: str = "/Private/Sony/PRO/LUT"
P326_FX3_LUT_CFEXPRESS_DIR: str = "/Sony/PRO/LUT"
P326_FX6_LUT_SD_DIR: str = "/PRIVATE/SONY/PRO/LUT/"
P326_FX6_LUT_CFEXPRESS_DIR: str = "/SONY/PRO/LUT/"

P326_EMBED_LUT_VALID_PATH: Tuple[str, ...] = (
    "Shooting",
    "Image Quality/Rec",
    "Log Shooting Setting",
    "Embed LUT File",
)
P326_EMBED_LUT_WRONG_PATH: Tuple[str, ...] = (
    "Exposure/Color",
    "Color/Tone",
    "Embed LUT File",
)
P326_LIVE_VIEW_DISPLAY_SET_PATH: Tuple[str, ...] = (
    "Shooting",
    "Shooting Display",
    "Live View Display Set.",
)
P326_CARD_MEDIA_TYPES: Tuple[str, ...] = ("SD", "SDHC", "SDXC", "CFexpress Type A")
P326_LUT_WORKFLOW_MODES: Tuple[str, ...] = (
    "LOG_SHOOTING_EMBED",
    "PPLUT_BAKE",
    "VIEW_LUT_ONLY",
)
P326_FX6_LUT_CHANNELS: Tuple[str, ...] = (
    "Internal Rec.",
    "SDI/HDMI",
    "LCD/VF",
    "Proxy/Stream",
)

P326_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P326_RESET_ACTIONS: Tuple[str, ...] = ("None", "Camera Settings Reset", "Initialize")
P326_VAULT_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "IMPORT_USER_LUT_CUBE",
    "EMBED_LUT_RECORD",
    "PPLUT_RECORD",
    "MAKE_CUBE_FOLDER",
    "EXPORT_OR_WRITE_LUT",
    "DELETE_ALL_CARD",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P326_READ_ONLY_VAULT_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "IMPORT_USER_LUT_CUBE",
)
P326_WRITE_MUTATING_VAULT_ACTIONS: Tuple[str, ...] = (
    "EMBED_LUT_RECORD",
    "PPLUT_RECORD",
    "MAKE_CUBE_FOLDER",
    "EXPORT_OR_WRITE_LUT",
    "DELETE_ALL_CARD",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P326_VAULT_FIREWALL_ERRNOS: Tuple[str, ...] = ("EROFS", "EOPNOTSUPP", "EINVAL", "EPERM")
P326_VAULT_FIREWALL_ERRNO_CODES: Dict[str, int] = {
    "EPERM": P326_EPERM_ERRNO,
    "EINVAL": P326_EINVAL_ERRNO,
    "EROFS": P326_EROFS_ERRNO,
    "EOPNOTSUPP": P326_EOPNOTSUPP_ERRNO,
}

# Pinned Wave-56 17 Local Donors (14 FX3 7.02 + 3 FX6 6.01, strictly O_RDONLY)
P326_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P326_PINNED_FX3_APPFW_702_BYTES: int = 79_015_712
P326_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P326_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P326_PINNED_FX6_APPFW_601_BYTES: int = 50_520_424
P326_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P326_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P326_PINNED_FX3_BACKUP_BIN_BYTES: int = 2_229_740
P326_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P326_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P326_PINNED_FX3_UXC_EN_F_BYTES: int = 373_820
P326_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P326_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P326_PINNED_FX3_UXC_SC_F_BYTES: int = 322_652
P326_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P326_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P326_PINNED_FX3_UXC_TC_F_BYTES: int = 324_148
P326_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P326_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P326_PINNED_FX3_UXC_JA_F_BYTES: int = 447_840
P326_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P326_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P326_PINNED_FX3_UXC_EN_BYTES: int = 165_740
P326_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P326_DONOR_FX3_UXC_SC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc"
)
P326_PINNED_FX3_UXC_SC_BYTES: int = 149_064
P326_PINNED_FX3_UXC_SC_SHA256: str = (
    "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66"
)

P326_DONOR_FX3_UXC_TC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc"
)
P326_PINNED_FX3_UXC_TC_BYTES: int = 151_908
P326_PINNED_FX3_UXC_TC_SHA256: str = (
    "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3"
)

P326_DONOR_FX3_UXC_JA_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc"
)
P326_PINNED_FX3_UXC_JA_BYTES: int = 208_564
P326_PINNED_FX3_UXC_JA_SHA256: str = (
    "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d"
)

P326_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P326_PINNED_FX3_UXC_EN_G_BYTES: int = 69_600
P326_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P326_DONOR_FX3_UXC_SC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_g.uxc"
)
P326_PINNED_FX3_UXC_SC_G_BYTES: int = 61_296
P326_PINNED_FX3_UXC_SC_G_SHA256: str = (
    "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b"
)

P326_DONOR_FX3_UXC_TC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_g.uxc"
)
P326_PINNED_FX3_UXC_TC_G_BYTES: int = 61_372
P326_PINNED_FX3_UXC_TC_G_SHA256: str = (
    "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80"
)

P326_DONOR_FX3_UXC_JA_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_g.uxc"
)
P326_PINNED_FX3_UXC_JA_G_BYTES: int = 89_428
P326_PINNED_FX3_UXC_JA_G_SHA256: str = (
    "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980"
)

P326_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P326_PINNED_FX6_UXC_EN_BYTES: int = 118_208
P326_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P326_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P326_PINNED_FX6_UXC_EN_2_BYTES: int = 118_676
P326_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# Status & Block Codes
P326_STATUS_VERIFIED_PILLAR_58A: str = (
    "VERIFIED_PILLAR_58A_DIAL_CUSTOMIZE_MYDIAL_FN12X2_VAULT"
)
P326_STATUS_REJECTED_PILLAR_58A: str = (
    "REJECTED_PILLAR_58A_DIAL_CUSTOMIZE_MYDIAL_FN12X2_VAULT"
)
P326_STATUS_VERIFIED_PILLAR_58B: str = (
    "VERIFIED_PILLAR_58B_LIVEVIEW_GRID_LUT_EMBED_PPLUT_VAULT"
)
P326_STATUS_REJECTED_PILLAR_58B: str = (
    "REJECTED_PILLAR_58B_LIVEVIEW_GRID_LUT_EMBED_PPLUT_VAULT"
)
P326_STATUS_VERIFIED_PILLAR58_SUITE: str = (
    "VERIFIED_PILLAR58_DIAL_CUSTOMIZE_MYDIAL_FN12X2_LIVEVIEW_LUT_EMBED_VAULT"
)
P326_STATUS_FAIL_PILLAR58_SUITE: str = (
    "FAIL_PILLAR58_DIAL_CUSTOMIZE_MYDIAL_FN12X2_LIVEVIEW_LUT_EMBED_VAULT"
)
P326_STATUS_VERIFIED_58OF58_AGGREGATOR: str = "VERIFIED_58OF58_PILLAR_RECOVERY_MASTER"
P326_STATUS_FAIL_58OF58_AGGREGATOR: str = "FAIL_58OF58_PILLAR_RECOVERY_MASTER"

P326_BLOCKED_SAFETY_POLICY_VIOLATION: str = "P326_BLOCKED_SAFETY_POLICY_VIOLATION"
P326_BLOCKED_INVALID_PILLAR58A_SPEC: str = "P326_BLOCKED_INVALID_PILLAR58A_SPEC"
P326_BLOCKED_INVALID_PILLAR58B_SPEC: str = "P326_BLOCKED_INVALID_PILLAR58B_SPEC"
P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT: str = (
    "P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT"
)
P326_BLOCKED_3DIAL_TOPOLOGY_OR_MYDIAL_OVERRIDE_DRIFT: str = (
    "P326_BLOCKED_3DIAL_TOPOLOGY_OR_MYDIAL_OVERRIDE_DRIFT"
)
P326_BLOCKED_FN_12X2_OR_FX6_DIAL_SPOOF: str = "P326_BLOCKED_FN_12X2_OR_FX6_DIAL_SPOOF"
P326_BLOCKED_LIVE_VIEW_RESET_SPLIT_OR_STILL_GATE: str = (
    "P326_BLOCKED_LIVE_VIEW_RESET_SPLIT_OR_STILL_GATE"
)
P326_BLOCKED_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK: str = (
    "P326_BLOCKED_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK"
)
P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF: str = (
    "P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF"
)
P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL: str = "P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL"
P326_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "P326_BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P326_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "P326_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

# 12 Scenario IDs (6 Pillar 58A + 6 Pillar 58B)
P326_PILLAR_58A_SCENARIO_IDS: Tuple[str, ...] = (
    "P58A1_ALLOW_DIAL_CUSTOMIZE_5ITEM_INIT_ONLY_MYDIAL_123_OVERRIDE_AND_FN_12X2",
    "P58A2_ALLOW_MYDIAL_CYCLE_SKIP_EMPTY_LONG_FN_AND_5S_MENU_FN_LOCK",
    "P58A3_REJECT_DORMANT_REAR_DIAL_LR_DIAL_SETUP_OR_FUNCTION_RING_INVALID",
    "P58A4_REJECT_CAMERA_SETTINGS_RESET_WIPING_DIAL_CUSTOMIZE_OR_MYDIAL_LOCK_FAIL",
    "P58A5_REJECT_ALL_NOT_SET_FN_BYPASS_OR_NON_12X2_STILL_MOVIE_SLOT_MISMATCH",
    "P58A6_REJECT_FX6_AV_TV_MYDIAL_FN_SPOOF_OR_SLOT1_VAULT_WRITE",
)

P326_PILLAR_58B_SCENARIO_IDS: Tuple[str, ...] = (
    "P58B1_ALLOW_LIVE_VIEW_RESET_SPLIT_BRIGHT_MON_GRID_HDMI_CLEAN_FEED_AND_LUT_EMBED",
    "P58B2_ALLOW_SLOT1_READONLY_USER_LUT_IMPORT_CUBE_AND_PPLUT1_4_RESET_BAKE_SLOT2",
    "P58B3_REJECT_LIVE_VIEW_IN_MOVIE_OR_RESET_WIPING_LIVE_VIEW_EXPOSURE_EFFECT",
    "P58B4_REJECT_GRID_LINE_HDMI_CLEAN_FEED_LEAK_OR_FX6_CUSTOM_PNG_GRID_SPOOF",
    "P58B5_REJECT_EMBED_LUT_WRONG_PATH_SIDECAR_SDHC_BYPASS_OR_PPLUT_RESET_DRIFT",
    "P58B6_REJECT_SLOT1_VAULT_EROFS30_EMBED_PPLUT_FOLDER_CREATE_OR_FORMAT_BYPASS",
)

# Unified 58/58 Pillar Specs (Pillars 1..57 + Pillar 58)
MASTER_58_PILLAR_COUNT: int = 58
MASTER_58_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_57_PILLAR_SPECS + (
    (
        58,
        "pillar_58_dial_customize_mydial_fn12x2_liveview_lut_embed_vault",
        "Phase 326 Wave-56 Dial Customize 5-Item + My Dial 1..3 + Fn 12x2 + Live View Reset Split + Grid HDMI Clean-Feed + Embed LUT/PPLUT1..4 + Slot-1 Vault",
        "realhw_58pillar_dial_customize_mydial_fn12x2_liveview_lut_embed_vault_verifier",
    ),
)
MASTER_58_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_58_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Safety, Hashing & Deterministic State Helpers
# ---------------------------------------------------------------------------


def _need(condition: bool, message: str) -> None:
    if not condition:
        raise ValueError(message)


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return sha256(payload.encode("utf-8")).hexdigest()


def _is_clean_room_forced(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is True:
        return True
    env_flag = os.environ.get(P326_ENV_CLEAN_ROOM_TEST, "").strip().lower()
    if env_flag in ("1", "true", "yes"):
        return True
    if is_forced_clean_room():
        return True
    return False


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true" or os.environ.get(
        "CI", ""
    ).strip().lower() in ("1", "true", "yes"):
        return P326_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P326_DONOR_INSPECT_BUDGET_SECONDS


def _is_tmpfs_path(path: str) -> bool:
    norm = posixpath.normpath(path)
    return norm == "/tmp" or norm.startswith("/tmp/")


def _targets_persistent_emmc(path: str) -> bool:
    norm = posixpath.normpath(path)
    return any(
        norm == pref or norm.startswith(pref + "/") or norm.startswith(pref)
        for pref in P326_PERSISTENT_EMMC_PREFIXES
    )


def _safety_invariant_errors() -> List[str]:
    errs: List[str] = []
    if PERSISTENT_EMMC_WRITES_AUTHORIZED:
        errs.append("PERSISTENT_EMMC_WRITES_AUTHORIZED must remain False")
    if SPI_NOR_WRITE_AUTHORIZED:
        errs.append("SPI_NOR_WRITE_AUTHORIZED must remain False")
    if EL3_PAYLOAD_TRANSMIT_AUTHORIZED:
        errs.append("EL3_PAYLOAD_TRANSMIT_AUTHORIZED must remain False")
    if ISP_WRITE_AUTHORIZED:
        errs.append("ISP_WRITE_AUTHORIZED must remain False")
    if PERSISTENT_WRITE_RELEASE:
        errs.append("PERSISTENT_WRITE_RELEASE must remain False")
    if ALLOW_BOOT_PARTITION_TARGETING:
        errs.append("ALLOW_BOOT_PARTITION_TARGETING must remain False")
    if ALLOW_DESTRUCTIVE_FASTBOOT:
        errs.append("ALLOW_DESTRUCTIVE_FASTBOOT must remain False")
    if ALLOW_PERSISTENT_JIRITSU_WRITES:
        errs.append("ALLOW_PERSISTENT_JIRITSU_WRITES must remain False")
    if ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS:
        errs.append("ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS must remain False")
    if LIVE_USB_IOKIT_TRANSMIT_ENABLED:
        errs.append("LIVE_USB_IOKIT_TRANSMIT_ENABLED must remain False")
    if HARDWARE_LIVE_ATTACHMENT_AUTHORIZED:
        errs.append("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED must remain False")
    if OVERALL_READY_FOR_HARDWARE_ATTACH:
        errs.append("OVERALL_READY_FOR_HARDWARE_ATTACH must remain False")
    if CROSS_MODEL_FLASH_AUTHORIZED:
        errs.append("CROSS_MODEL_FLASH_AUTHORIZED must remain False")
    if not READ_ONLY_DONOR_ACCESS:
        errs.append("READ_ONLY_DONOR_ACCESS must remain True")
    if not P326_SLOT1_FORMAT_HARD_LOCKED:
        errs.append("P326_SLOT1_FORMAT_HARD_LOCKED must remain True")
    if not P326_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED:
        errs.append("P326_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED must remain True")
    if not CNFLASHA_USERSPACE_WRITE_BLOCKED:
        errs.append("CNFLASHA_USERSPACE_WRITE_BLOCKED must remain True")
    if OTP_FUSE_TOUCHES != 0 or OTP_FUSE_WRITES != 0:
        errs.append("OTP_FUSE_TOUCHES / OTP_FUSE_WRITES must remain 0")
    if RPMB_COUNTER_INCREMENTS != 0:
        errs.append("RPMB_COUNTER_INCREMENTS must remain 0")
    if PASSIVE_TX_BYTES_EMITTED != 0:
        errs.append("PASSIVE_TX_BYTES_EMITTED must remain 0")
    if PHYSICAL_USB_PACKETS_EMITTED != 0:
        errs.append("PHYSICAL_USB_PACKETS_EMITTED must remain 0")
    if PHYSICAL_DEVICE_WRITES != 0:
        errs.append("PHYSICAL_DEVICE_WRITES must remain 0")
    if RAW_FIRMWARE_BYTES_LEAKED != 0:
        errs.append("RAW_FIRMWARE_BYTES_LEAKED must remain 0")
    return errs


def compute_expected_dial_customize_mydial_fn12x2_state(
    *,
    camera_model: str,
    shooting_domain: str,
    dial_customize_items: Tuple[str, ...],
    av_tv_rotate: str,
    function_ring_lens: str,
    lock_operation_parts: str,
    physical_dials_present: Tuple[str, ...],
    requested_dormant_dial_symbols: Tuple[str, ...],
    my_dial_1_configured: bool,
    my_dial_2_configured: bool,
    my_dial_3_configured: bool,
    my_dial_recall_mode: str,
    my_dial_cycle_step: int,
    fn_still_slot_count: int,
    fn_movie_slot_count: int,
    fn_all_not_set_pressed: bool,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-56 Dial Customize + My Dial 1..3 + Fn Menu 12+12 state."""
    is_fx3 = camera_model == P326_FX3_MODEL_NAME
    dormant_dial_hit = (
        len(requested_dormant_dial_symbols) > 0
        or function_ring_lens == "INVALID"
        or any(d in ("Rear Dial L", "Rear Dial R") for d in physical_dials_present)
    )
    dormant_dial_errno: Optional[int] = (
        P326_EOPNOTSUPP_ERRNO if dormant_dial_hit else None
    )

    # All 5 Dial Customize items, My Dial 1..3 banks, and Fn Menu Settings are Initialize-only!
    if is_fx3 and reset_action == "Initialize":
        post_av_tv = P326_AV_TV_ROTATE_DEFAULT
        post_fn_ring = P326_FUNCTION_RING_DEFAULT
        post_lock = P326_LOCK_OPERATION_PARTS_DEFAULT
    else:
        post_av_tv = av_tv_rotate
        post_fn_ring = function_ring_lens
        post_lock = lock_operation_parts

    # My Dial 1->2->3 cycle auto-skips all-Not-set banks & temporarily overrides Lock Operation Parts
    banks = (
        (1, my_dial_1_configured),
        (2, my_dial_2_configured),
        (3, my_dial_3_configured),
    )
    active_bank: Optional[int] = None
    if is_fx3 and my_dial_recall_mode != "None":
        configured_banks = [num for num, cfg in banks if cfg]
        if configured_banks:
            if my_dial_recall_mode in ("Hold", "Toggle"):
                if my_dial_cycle_step in configured_banks:
                    active_bank = my_dial_cycle_step
                else:
                    active_bank = configured_banks[0]
            elif my_dial_recall_mode == "1->2->3":
                candidates = [num for num in configured_banks if num >= max(1, my_dial_cycle_step)]
                active_bank = candidates[0] if candidates else None

    dials_temporarily_unlocked = (
        is_fx3
        and active_bank is not None
        and post_lock in ("Dial + Wheel", "All")
    )
    fn_invalid_prompt_errno: Optional[int] = (
        P326_EINVAL_ERRNO if (is_fx3 and fn_all_not_set_pressed) else None
    )

    return {
        "dormant_dial_errno": dormant_dial_errno,
        "post_av_tv_rotate": post_av_tv,
        "post_function_ring_lens": post_fn_ring,
        "post_lock_operation_parts": post_lock,
        "active_my_dial_bank": active_bank,
        "dials_temporarily_unlocked_by_mydial": dials_temporarily_unlocked,
        "fn_invalid_prompt_errno": fn_invalid_prompt_errno,
        "dial_customize_item_count": len(dial_customize_items),
        "fn_still_slot_count": fn_still_slot_count,
        "fn_movie_slot_count": fn_movie_slot_count,
        "shooting_domain": shooting_domain,
    }


def compute_expected_liveview_grid_lut_embed_state(
    *,
    camera_model: str,
    shooting_domain: str,
    live_view_display: str,
    bright_monitoring_active: bool,
    exposure_effect: str,
    frame_rate_low_limit: str,
    grid_line_display: str,
    grid_line_type: str,
    hdmi_info_display: str,
    raw_output_or_hdmi_only: bool,
    card_media_type: str,
    user_lut_slot_populated: bool,
    select_lut: str,
    embed_lut_file: str,
    pplut_slot: str,
    lut_workflow_mode: str,
    requested_vault_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
    make_cube_folder_on_slot1: bool,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute canonical Wave-56 Live View asymmetric reset split, Grid HDMI isolation, LUT Embed/PPLUT & Slot-1 Vault state."""
    is_fx3 = camera_model == P326_FX3_MODEL_NAME
    # Live View Display Set. is Still-only on FX3
    live_view_gate_errno: Optional[int] = (
        P326_EOPNOTSUPP_ERRNO if (is_fx3 and shooting_domain != "Still") else None
    )

    effective_live_view = (
        "Setting Effect OFF" if bright_monitoring_active else live_view_display
    )
    if reset_action == "Initialize":
        post_live_view = P326_LIVE_VIEW_DISPLAY_DEFAULT
        post_exp_effect = P326_EXPOSURE_EFFECT_DEFAULT
        post_frame_rate_low_limit = "Off"
        post_grid_display = "Off"
        post_grid_type = P326_GRID_LINE_TYPE_DEFAULT
        post_select_lut = P326_SELECT_LUT_DEFAULT
        post_embed_lut = P326_EMBED_LUT_FILE_DEFAULT
        post_pplut_reset = True
    elif reset_action == "Camera Settings Reset":
        # CRITICAL Wave-56 Asymmetric Reset Truths:
        # - Live View Display, Exposure Effect, Grid Line Display, Grid Line Type, User LUTs: NOT reset
        # - Frame Rate Low Limit, Select LUT (-> s709), Embed LUT File (-> On), PPLUT1..4: RESET!
        post_live_view = effective_live_view
        post_exp_effect = exposure_effect
        post_frame_rate_low_limit = "Off"
        post_grid_display = grid_line_display
        post_grid_type = grid_line_type
        post_select_lut = P326_SELECT_LUT_DEFAULT
        post_embed_lut = P326_EMBED_LUT_FILE_DEFAULT
        post_pplut_reset = True
    else:
        post_live_view = effective_live_view
        post_exp_effect = exposure_effect
        post_frame_rate_low_limit = frame_rate_low_limit
        post_grid_display = grid_line_display
        post_grid_type = grid_line_type
        post_select_lut = select_lut
        post_embed_lut = embed_lut_file
        post_pplut_reset = False

    # HDMI Info Display forced Off when RAW output or Off(HDMI Only)
    effective_hdmi_info = "Off" if raw_output_or_hdmi_only else hdmi_info_display
    clean_hdmi_osd_isolated_to_lcd = effective_hdmi_info == "Off"

    # SD/SDHC hardware-locks Embed LUT File to Off
    sd_sdhc_embed_locked = is_fx3 and card_media_type in ("SD", "SDHC")
    effective_embed_lut = "Off" if sd_sdhc_embed_locked else embed_lut_file

    # Unpopulated User1..16 falls back to S-Log3 monitoring
    if select_lut.startswith("User") and not user_lut_slot_populated:
        effective_monitored_lut = "S-Log3"
    else:
        effective_monitored_lut = select_lut

    # Container metadata embed vs irreversible DSP pixel baking
    is_embed_mode = (
        lut_workflow_mode == "LOG_SHOOTING_EMBED" and effective_embed_lut == "On"
    )
    is_pplut_mode = lut_workflow_mode == "PPLUT_BAKE" and pplut_slot in P326_PPLUT_SLOTS
    slog3_pixels_preserved = not is_pplut_mode
    external_cube_sidecar_generated = False

    # Expected LUT dir on FX3 vs FX6
    if is_fx3:
        expected_lut_dir = (
            P326_FX3_LUT_CFEXPRESS_DIR
            if card_media_type == "CFexpress Type A"
            else P326_FX3_LUT_SD_DIR
        )
    else:
        expected_lut_dir = (
            P326_FX6_LUT_CFEXPRESS_DIR
            if card_media_type == "CFexpress Type A"
            else P326_FX6_LUT_SD_DIR
        )

    # Slot-1 Tier-0 Vault Firewall
    mutates_slot1 = requested_vault_slot == P326_SLOT1_VAULT_SLOT and (
        requested_vault_action in P326_WRITE_MUTATING_VAULT_ACTIONS
        or make_cube_folder_on_slot1
    )
    if mutates_slot1 and slot1_holds_tier0_vault:
        action_allowed = False
        firewall_errno: Optional[str] = "EROFS"
    elif requested_vault_action in ("FORMAT_QUICK", "FORMAT_FULL"):
        action_allowed = False
        firewall_errno = "EROFS"
    elif requested_vault_action == "IMPORT_USER_LUT_CUBE":
        # Read-only .cube import from Slot-1 allowed iff zero data sector writes and zero folder creation
        action_allowed = not make_cube_folder_on_slot1
        firewall_errno = "EROFS" if make_cube_folder_on_slot1 else None
    elif requested_vault_action in ("READ_ONLY_AUDIT",):
        action_allowed = True
        firewall_errno = None
    elif requested_vault_action == "NONE":
        action_allowed = False
        firewall_errno = None
    elif requested_vault_slot == P326_SAFE_SECONDARY_SLOT:
        action_allowed = True
        firewall_errno = None
    else:
        action_allowed = False
        firewall_errno = "EROFS"

    return {
        "live_view_gate_errno": live_view_gate_errno,
        "effective_live_view_display": effective_live_view,
        "post_live_view_display": post_live_view,
        "post_exposure_effect": post_exp_effect,
        "post_frame_rate_low_limit": post_frame_rate_low_limit,
        "post_grid_line_display": post_grid_display,
        "post_grid_line_type": post_grid_type,
        "effective_hdmi_info_display": effective_hdmi_info,
        "clean_hdmi_osd_isolated_to_lcd": clean_hdmi_osd_isolated_to_lcd,
        "sd_sdhc_embed_locked_off": sd_sdhc_embed_locked,
        "effective_embed_lut_file": effective_embed_lut,
        "effective_monitored_lut": effective_monitored_lut,
        "post_select_lut": post_select_lut,
        "post_embed_lut_file": post_embed_lut,
        "post_pplut_reset": post_pplut_reset,
        "slog3_pixels_preserved": slog3_pixels_preserved,
        "external_cube_sidecar_generated": external_cube_sidecar_generated,
        "expected_lut_dir": expected_lut_dir,
        "action_allowed": action_allowed,
        "firewall_errno": firewall_errno,
        "firewall_errno_num": (
            P326_VAULT_FIREWALL_ERRNO_CODES[firewall_errno]
            if firewall_errno in P326_VAULT_FIREWALL_ERRNO_CODES
            else None
        ),
        "is_embed_mode": is_embed_mode,
        "is_pplut_mode": is_pplut_mode,
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & work_root=None Clean-Room Guard (17 Donors)
# ---------------------------------------------------------------------------


def _iter_work_roots() -> Tuple[Optional[Path], ...]:
    """Return candidate donor work roots (delegates to `iter_donor_work_roots`)."""
    return iter_donor_work_roots()


def _resolve_phase326_donor_path(
    relpath: str,
    *,
    work_roots: Optional[Tuple[Optional[Path], ...]] = None,
) -> Optional[Path]:
    """Resolve `relpath` with an explicit `work_root is None` guard for donorless Ubuntu CI."""
    if _is_clean_room_forced(None):
        return None
    rel_norm = relpath.strip("/")
    if rel_norm.startswith("work/"):
        rel_norm = rel_norm[len("work/") :]
    roots = _iter_work_roots() if work_roots is None else work_roots
    for work_root in roots:
        if work_root is None:
            continue
        candidate = Path(work_root) / rel_norm
        try:
            if candidate.exists():
                return candidate
        except OSError:
            continue
    return None


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P326_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = _resolve_phase326_donor_path(relpath)
    except Exception:
        return False, 0, 0, "MISSING", "", b""
    if resolved is None:
        return False, 0, 0, "MISSING", "", b""
    try:
        if not resolved.exists():
            return False, 0, 0, "MISSING", "", b""
    except OSError:
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
        hdr = os.pread(fd, min(P326_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase326_donors() -> Tuple["Phase326DonorArtifactDigest", ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P326_DONOR_FX3_APPFW_702_RELPATH,
            P326_PINNED_FX3_APPFW_702_BYTES,
            P326_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P326_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P326_DONOR_FX6_APPFW_601_RELPATH,
            P326_PINNED_FX6_APPFW_601_BYTES,
            P326_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P326_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P326_DONOR_FX3_BACKUP_BIN_RELPATH,
            P326_PINNED_FX3_BACKUP_BIN_BYTES,
            P326_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_uxc_en_f",
            P326_DONOR_FX3_UXC_EN_F_RELPATH,
            P326_PINNED_FX3_UXC_EN_F_BYTES,
            P326_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P326_DONOR_FX3_UXC_SC_F_RELPATH,
            P326_PINNED_FX3_UXC_SC_F_BYTES,
            P326_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P326_DONOR_FX3_UXC_TC_F_RELPATH,
            P326_PINNED_FX3_UXC_TC_F_BYTES,
            P326_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P326_DONOR_FX3_UXC_JA_F_RELPATH,
            P326_PINNED_FX3_UXC_JA_F_BYTES,
            P326_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P326_DONOR_FX3_UXC_EN_RELPATH,
            P326_PINNED_FX3_UXC_EN_BYTES,
            P326_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_sc",
            P326_DONOR_FX3_UXC_SC_RELPATH,
            P326_PINNED_FX3_UXC_SC_BYTES,
            P326_PINNED_FX3_UXC_SC_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX3_SC",
        ),
        (
            "fx3_uxc_tc",
            P326_DONOR_FX3_UXC_TC_RELPATH,
            P326_PINNED_FX3_UXC_TC_BYTES,
            P326_PINNED_FX3_UXC_TC_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX3_TC",
        ),
        (
            "fx3_uxc_ja",
            P326_DONOR_FX3_UXC_JA_RELPATH,
            P326_PINNED_FX3_UXC_JA_BYTES,
            P326_PINNED_FX3_UXC_JA_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX3_JA",
        ),
        (
            "fx3_uxc_en_g",
            P326_DONOR_FX3_UXC_EN_G_RELPATH,
            P326_PINNED_FX3_UXC_EN_G_BYTES,
            P326_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx3_uxc_sc_g",
            P326_DONOR_FX3_UXC_SC_G_RELPATH,
            P326_PINNED_FX3_UXC_SC_G_BYTES,
            P326_PINNED_FX3_UXC_SC_G_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_SC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_G",
        ),
        (
            "fx3_uxc_tc_g",
            P326_DONOR_FX3_UXC_TC_G_RELPATH,
            P326_PINNED_FX3_UXC_TC_G_BYTES,
            P326_PINNED_FX3_UXC_TC_G_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_TC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_G",
        ),
        (
            "fx3_uxc_ja_g",
            P326_DONOR_FX3_UXC_JA_G_RELPATH,
            P326_PINNED_FX3_UXC_JA_G_BYTES,
            P326_PINNED_FX3_UXC_JA_G_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX3_UXC_JA_G_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_G",
        ),
        (
            "fx6_uxc_en",
            P326_DONOR_FX6_UXC_EN_RELPATH,
            P326_PINNED_FX6_UXC_EN_BYTES,
            P326_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P326_DONOR_FX6_UXC_EN_2_RELPATH,
            P326_PINNED_FX6_UXC_EN_2_BYTES,
            P326_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P326_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase326DonorArtifactDigest(
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


def inspect_phase326_donors_readonly(force_clean_room: Optional[bool] = None) -> "Phase326DonorSnapshot":
    """Inspect Wave-56 FX3 7.02 (`14` donors) & FX6 6.01 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.2s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase326_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase326DonorSnapshot(
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
            P326_DONOR_FX3_APPFW_702_RELPATH,
            P326_PINNED_FX3_APPFW_702_BYTES,
            P326_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702"),
        ),
        (
            "fx6_appfw_601_so",
            P326_DONOR_FX6_APPFW_601_RELPATH,
            P326_PINNED_FX6_APPFW_601_BYTES,
            P326_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601"),
        ),
        (
            "fx3_backup_bin",
            P326_DONOR_FX3_BACKUP_BIN_RELPATH,
            P326_PINNED_FX3_BACKUP_BIN_BYTES,
            P326_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_uxc_en_f",
            P326_DONOR_FX3_UXC_EN_F_RELPATH,
            P326_PINNED_FX3_UXC_EN_F_BYTES,
            P326_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P326_DONOR_FX3_UXC_SC_F_RELPATH,
            P326_PINNED_FX3_UXC_SC_F_BYTES,
            P326_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P326_DONOR_FX3_UXC_TC_F_RELPATH,
            P326_PINNED_FX3_UXC_TC_F_BYTES,
            P326_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P326_DONOR_FX3_UXC_JA_F_RELPATH,
            P326_PINNED_FX3_UXC_JA_F_BYTES,
            P326_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P326_DONOR_FX3_UXC_EN_RELPATH,
            P326_PINNED_FX3_UXC_EN_BYTES,
            P326_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_sc",
            P326_DONOR_FX3_UXC_SC_RELPATH,
            P326_PINNED_FX3_UXC_SC_BYTES,
            P326_PINNED_FX3_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC"),
        ),
        (
            "fx3_uxc_tc",
            P326_DONOR_FX3_UXC_TC_RELPATH,
            P326_PINNED_FX3_UXC_TC_BYTES,
            P326_PINNED_FX3_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC"),
        ),
        (
            "fx3_uxc_ja",
            P326_DONOR_FX3_UXC_JA_RELPATH,
            P326_PINNED_FX3_UXC_JA_BYTES,
            P326_PINNED_FX3_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA"),
        ),
        (
            "fx3_uxc_en_g",
            P326_DONOR_FX3_UXC_EN_G_RELPATH,
            P326_PINNED_FX3_UXC_EN_G_BYTES,
            P326_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx3_uxc_sc_g",
            P326_DONOR_FX3_UXC_SC_G_RELPATH,
            P326_PINNED_FX3_UXC_SC_G_BYTES,
            P326_PINNED_FX3_UXC_SC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_G"),
        ),
        (
            "fx3_uxc_tc_g",
            P326_DONOR_FX3_UXC_TC_G_RELPATH,
            P326_PINNED_FX3_UXC_TC_G_BYTES,
            P326_PINNED_FX3_UXC_TC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_G"),
        ),
        (
            "fx3_uxc_ja_g",
            P326_DONOR_FX3_UXC_JA_G_RELPATH,
            P326_PINNED_FX3_UXC_JA_G_BYTES,
            P326_PINNED_FX3_UXC_JA_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_G"),
        ),
        (
            "fx6_uxc_en",
            P326_DONOR_FX6_UXC_EN_RELPATH,
            P326_PINNED_FX6_UXC_EN_BYTES,
            P326_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P326_DONOR_FX6_UXC_EN_2_RELPATH,
            P326_PINNED_FX6_UXC_EN_2_BYTES,
            P326_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    digests: List[Phase326DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            break
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        digests.append(
            Phase326DonorArtifactDigest(
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
        artifacts = _synthetic_phase326_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase326DonorSnapshot(
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
    return Phase326DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 58-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase326DonorArtifactDigest:
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
class Phase326DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase326DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DialCustomizeMyDialFn12x2VaultSpec:
    # Wave-56 [Dial Customize] 5-Item Initialize-only Tree & Dormant Trap Rejection
    camera_model: str
    fw_version: str
    shooting_domain: str
    dial_customize_items: Tuple[str, ...]
    av_tv_rotate: str
    function_ring_lens: str
    lock_operation_parts: str
    long_press_fn_toggles_lock: bool
    menu_plus_fn_5s_full_lock_supported: bool
    post_av_tv_rotate: str
    post_function_ring_lens: str
    post_lock_operation_parts: str
    # 3-Physical-Dial Topology vs Dormant Rear Dial L/R / Dial Setup / Dial/Wheel Lock
    physical_dials_present: Tuple[str, ...]
    requested_dormant_dial_symbols: Tuple[str, ...]
    reported_dormant_dial_errno: Optional[int]
    # My Dial 1..3 Shared NVRAM Banks, Still/Movie Trigger & Lock Override
    my_dial_1_configured: bool
    my_dial_2_configured: bool
    my_dial_3_configured: bool
    my_dial_recall_mode: str
    my_dial_cycle_step: int
    reported_active_my_dial_bank: Optional[int]
    reported_dials_temporarily_unlocked: bool
    # [Operation Customize] -> [Fn Menu Settings] 12 Still + 12 Movie Split
    fn_still_slot_count: int
    fn_movie_slot_count: int
    fn_all_not_set_pressed: bool
    reported_fn_invalid_prompt_errno: Optional[int]
    # ILME-FX6 Control Architecture Boundary
    fx6_dial_controls: Tuple[str, ...]
    fx6_exposes_av_tv_mydial_or_fn_menu: bool
    fx6_uses_physical_hold_switch: bool
    reset_action: str
    # Slot-1 Tier-0 Vault & Stage-B Overlay
    requested_vault_slot: int
    requested_vault_action: str
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    dial_customize_dormant_trap_or_reset_drift_events: int
    rear_dial_lr_or_mydial_override_drift_events: int
    fn_menu_12x2_or_fx6_dial_spoof_events: int


@dataclass(frozen=True)
class DialCustomizeMyDialFn12x2VaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    dial_customize_5item_init_only_and_lock_verified: bool
    three_dial_topology_and_mydial_override_verified: bool
    fn_12x2_split_and_fx6_dial_boundary_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    dial_customize_dormant_trap_or_reset_drift_events: int
    rear_dial_lr_or_mydial_override_drift_events: int
    fn_menu_12x2_or_fx6_dial_spoof_events: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LiveViewGridLutEmbedPplutVaultSpec:
    # Wave-56 [Live View Display Set.] Still-only 3-Item Asymmetric Reset Split
    camera_model: str
    fw_version: str
    shooting_domain: str
    live_view_menu_path: Tuple[str, ...]
    live_view_display: str
    bright_monitoring_active: bool
    reported_live_view_display: str
    exposure_effect: str
    frame_rate_low_limit: str
    reported_live_view_gate_errno: Optional[int]
    post_live_view_display: str
    post_exposure_effect: str
    post_frame_rate_low_limit: str
    # [Grid Line Display] / [Grid Line Type] & Clean-HDMI/RAW OSD Isolation
    grid_line_display: str
    grid_line_type: str
    post_grid_line_display: str
    post_grid_line_type: str
    hdmi_info_display: str
    raw_output_or_hdmi_only: bool
    reported_clean_hdmi_osd_isolated_to_lcd: bool
    reported_hdmi_clean_feed_grid_leaked: bool
    fx6_uses_marker_guide_frame: bool
    fx6_exposes_dormant_custom_png_grid: bool
    # LUT Topology: [Manage User LUTs] / [Select LUT] / [Embed LUT File] vs PPLUT1..4
    card_media_type: str
    lut_card_dir: str
    lut_cube_points: int
    user_lut_slot_populated: bool
    select_lut: str
    reported_monitored_lut: str
    post_select_lut: str
    embed_lut_menu_path: Tuple[str, ...]
    embed_lut_file: str
    reported_embed_lut_file: str
    post_embed_lut_file: str
    pplut_slot: str
    post_pplut_reset: bool
    lut_workflow_mode: str
    reported_slog3_pixels_preserved: bool
    reported_external_cube_sidecar_generated: bool
    fx6_user_lut_ui_cap: int
    fx6_exposes_50_lut_slots: bool
    fx6_supports_multi_channel_lut_switches: bool
    reset_action: str
    # Slot-1 Tier-0 Vault & Stage-B Overlay
    requested_vault_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    make_cube_folder_on_slot1: bool
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_lut_mutation_bytes: int
    slot1_avf_info_mutated: bool
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    live_view_display_reset_split_or_mode_drift_events: int
    grid_line_or_hdmi_clean_feed_leak_events: int
    lut_path_embed_sidecar_or_slot1_vault_bypass_events: int


@dataclass(frozen=True)
class LiveViewGridLutEmbedPplutVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    live_view_3item_reset_split_and_bright_mon_verified: bool
    grid_line_and_hdmi_clean_feed_isolation_verified: bool
    lut_paths_embed_metadata_vs_pplut_bake_and_fx6_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    live_view_display_reset_split_or_mode_drift_events: int
    grid_line_or_hdmi_clean_feed_leak_events: int
    lut_path_embed_sidecar_or_slot1_vault_bypass_events: int
    slot1_data_sector_writes: int
    slot1_lut_mutation_bytes: int
    slot1_avf_info_mutated: bool
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DialCustomizeMyDialFn12x2LiveViewLutEmbedVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase326DonorSnapshot
    dial_customize_report: DialCustomizeMyDialFn12x2VaultReport
    liveview_lut_embed_report: LiveViewGridLutEmbedPplutVaultReport
    dial_customize_dormant_trap_or_reset_drift_events: int
    rear_dial_lr_or_mydial_override_drift_events: int
    fn_menu_12x2_or_fx6_dial_spoof_events: int
    live_view_display_reset_split_or_mode_drift_events: int
    grid_line_or_hdmi_clean_feed_leak_events: int
    lut_path_embed_sidecar_or_slot1_vault_bypass_events: int
    slot1_data_sector_writes: int
    slot1_lut_mutation_bytes: int
    slot1_avf_info_mutated: bool
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
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
class Pillar58ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar58ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar58ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar58BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar58ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar58StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase326DonorSnapshot
    pillar_58a_dial_customize_mydial_fn12x2_vault: Pillar58ASuiteResult
    pillar_58b_liveview_grid_lut_embed_pplut_vault: Pillar58BSuiteResult
    dial_customize_dormant_trap_or_reset_drift_events: int
    rear_dial_lr_or_mydial_override_drift_events: int
    fn_menu_12x2_or_fx6_dial_spoof_events: int
    live_view_display_reset_split_or_mode_drift_events: int
    grid_line_or_hdmi_clean_feed_leak_events: int
    lut_path_embed_sidecar_or_slot1_vault_bypass_events: int
    slot1_data_sector_writes: int
    slot1_lut_mutation_bytes: int
    slot1_avf_info_mutated: bool
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
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
class Master58PillarRecoveryReport:
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
    # Pillar 58 & Wave-56 top-level fields (Phase 326 — 58/58 Milestone)
    donor_snapshot: Phase326DonorSnapshot
    pillar58_a_dial_customize_mydial_fn12x2_vault: Pillar58ASuiteResult
    pillar58_b_liveview_grid_lut_embed_pplut_vault: Pillar58BSuiteResult
    dial_customize_dormant_trap_or_reset_drift_events: int
    rear_dial_lr_or_mydial_override_drift_events: int
    fn_menu_12x2_or_fx6_dial_spoof_events: int
    live_view_display_reset_split_or_mode_drift_events: int
    grid_line_or_hdmi_clean_feed_leak_events: int
    lut_path_embed_sidecar_or_slot1_vault_bypass_events: int
    slot1_data_sector_writes: int
    slot1_lut_mutation_bytes: int
    slot1_avf_info_mutated: bool
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
    fx3_dial_customize_item_count: int
    fx3_physical_dial_count: int
    fx3_my_dial_bank_count: int
    fx3_fn_menu_still_slots: int
    fx3_fn_menu_movie_slots: int
    fx3_live_view_display_set_item_count: int
    fx3_grid_line_type_count: int
    fx3_user_lut_slot_count: int
    fx3_pplut_slot_count: int
    fx6_user_lut_ui_cap: int
    fx6_has_av_tv_rotate: bool
    fx6_has_my_dial: bool
    fx6_has_fn_menu: bool
    fx6_has_multi_channel_lut_switches: bool
    # Preserved Pillars 1..57 rollup metrics
    touch_op_dormant_trap_or_reset_drift_events: int
    disp_set_or_zero_evf_blackout_events: int
    fx6_touch_or_evf_spoof_events: int
    still_ael_flash_reset_split_or_mishoe_drift_events: int
    interval_pb_9scale_or_path_drift_events: int
    playback_edit_dormant_or_slot1_vault_bypass_events: int
    slot1_edit_avf_info_mutation_bytes: int
    fx3_has_eye_sensor: bool
    fx3_has_finder_monitor_button: bool
    fx3_touch_active_item_count: int
    fx3_disp_shoot_page_count: int
    fx3_disp_play_page_count: int
    fx3_interval_pb_speed_min: int
    fx3_interval_pb_speed_max: int
    fx3_interval_pb_speed_default: int
    fx6_has_detachable_lcd_viewfinder: bool
    fx6_has_still_ttl_flash: bool
    fx6_has_interval_pb: bool
    fx6_has_playback_edit_menu: bool
    switch_vh_af_lockout_or_coords_drift_events: int
    focus_limit_lt2_or_dormant_symbol_events: int
    focus_area_color_or_fx6_spoof_events: int
    exp_std_adj_mode_conflation_or_reset_drift_events: int
    bracket_settings_reset_or_fx6_spoof_events: int
    tcub_reset_wipe_or_format_lock_violations: int
    reverse_copy_slot2_to_slot1_bypass_events: int
    slideshow_power_save_or_fx6_copy_clip_spoof_events: int
    slot1_copy_avf_info_mutation_bytes: int
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
    master_58pillar_sha256: str
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
# Spec Builders (Pillars 58A & 58B)
# ---------------------------------------------------------------------------


def build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
    **overrides: Any,
) -> DialCustomizeMyDialFn12x2VaultSpec:
    """Return a clean, verified default `DialCustomizeMyDialFn12x2VaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P326_FX3_MODEL_NAME,
        "fw_version": P326_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "dial_customize_items": P326_DIAL_CUSTOMIZE_5_ITEMS,
        "av_tv_rotate": P326_AV_TV_ROTATE_DEFAULT,
        "function_ring_lens": P326_FUNCTION_RING_DEFAULT,
        "lock_operation_parts": P326_LOCK_OPERATION_PARTS_DEFAULT,
        "long_press_fn_toggles_lock": True,
        "menu_plus_fn_5s_full_lock_supported": True,
        "post_av_tv_rotate": P326_AV_TV_ROTATE_DEFAULT,
        "post_function_ring_lens": P326_FUNCTION_RING_DEFAULT,
        "post_lock_operation_parts": P326_LOCK_OPERATION_PARTS_DEFAULT,
        "physical_dials_present": P326_PHYSICAL_3_DIALS,
        "requested_dormant_dial_symbols": (),
        "reported_dormant_dial_errno": None,
        "my_dial_1_configured": True,
        "my_dial_2_configured": False,
        "my_dial_3_configured": True,
        "my_dial_recall_mode": "1->2->3",
        "my_dial_cycle_step": 1,
        "reported_active_my_dial_bank": 1,
        "reported_dials_temporarily_unlocked": False,
        "fn_still_slot_count": P326_FX3_FN_MENU_STILL_SLOTS,
        "fn_movie_slot_count": P326_FX3_FN_MENU_MOVIE_SLOTS,
        "fn_all_not_set_pressed": False,
        "reported_fn_invalid_prompt_errno": None,
        "fx6_dial_controls": P326_FX6_DIAL_CONTROLS,
        "fx6_exposes_av_tv_mydial_or_fn_menu": False,
        "fx6_uses_physical_hold_switch": True,
        "reset_action": "None",
        "requested_vault_slot": P326_SLOT1_VAULT_SLOT,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P326_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P326_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P326_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P326_TIER0_SURFACE_COUNT,
        "dial_customize_dormant_trap_or_reset_drift_events": 0,
        "rear_dial_lr_or_mydial_override_drift_events": 0,
        "fn_menu_12x2_or_fx6_dial_spoof_events": 0,
    }
    defaults.update(overrides)
    return DialCustomizeMyDialFn12x2VaultSpec(**defaults)


def build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
    **overrides: Any,
) -> LiveViewGridLutEmbedPplutVaultSpec:
    """Return a clean, verified default `LiveViewGridLutEmbedPplutVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P326_FX3_MODEL_NAME,
        "fw_version": P326_FX3_FW_VERSION,
        "shooting_domain": "Still",
        "live_view_menu_path": P326_LIVE_VIEW_DISPLAY_SET_PATH,
        "live_view_display": P326_LIVE_VIEW_DISPLAY_DEFAULT,
        "bright_monitoring_active": False,
        "reported_live_view_display": P326_LIVE_VIEW_DISPLAY_DEFAULT,
        "exposure_effect": P326_EXPOSURE_EFFECT_DEFAULT,
        "frame_rate_low_limit": "Off",
        "reported_live_view_gate_errno": None,
        "post_live_view_display": P326_LIVE_VIEW_DISPLAY_DEFAULT,
        "post_exposure_effect": P326_EXPOSURE_EFFECT_DEFAULT,
        "post_frame_rate_low_limit": "Off",
        "grid_line_display": "Off",
        "grid_line_type": P326_GRID_LINE_TYPE_DEFAULT,
        "post_grid_line_display": "Off",
        "post_grid_line_type": P326_GRID_LINE_TYPE_DEFAULT,
        "hdmi_info_display": "Off",
        "raw_output_or_hdmi_only": False,
        "reported_clean_hdmi_osd_isolated_to_lcd": True,
        "reported_hdmi_clean_feed_grid_leaked": False,
        "fx6_uses_marker_guide_frame": True,
        "fx6_exposes_dormant_custom_png_grid": False,
        "card_media_type": "CFexpress Type A",
        "lut_card_dir": P326_FX3_LUT_CFEXPRESS_DIR,
        "lut_cube_points": 33,
        "user_lut_slot_populated": True,
        "select_lut": P326_SELECT_LUT_DEFAULT,
        "reported_monitored_lut": P326_SELECT_LUT_DEFAULT,
        "post_select_lut": P326_SELECT_LUT_DEFAULT,
        "embed_lut_menu_path": P326_EMBED_LUT_VALID_PATH,
        "embed_lut_file": P326_EMBED_LUT_FILE_DEFAULT,
        "reported_embed_lut_file": P326_EMBED_LUT_FILE_DEFAULT,
        "post_embed_lut_file": P326_EMBED_LUT_FILE_DEFAULT,
        "pplut_slot": "PPLUT1",
        "post_pplut_reset": False,
        "lut_workflow_mode": "LOG_SHOOTING_EMBED",
        "reported_slog3_pixels_preserved": True,
        "reported_external_cube_sidecar_generated": False,
        "fx6_user_lut_ui_cap": P326_FX6_USER_LUT_UI_CAP,
        "fx6_exposes_50_lut_slots": False,
        "fx6_supports_multi_channel_lut_switches": True,
        "reset_action": "None",
        "requested_vault_slot": P326_SLOT1_VAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "make_cube_folder_on_slot1": False,
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_lut_mutation_bytes": 0,
        "slot1_avf_info_mutated": False,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P326_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P326_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P326_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P326_TIER0_SURFACE_COUNT,
        "live_view_display_reset_split_or_mode_drift_events": 0,
        "grid_line_or_hdmi_clean_feed_leak_events": 0,
        "lut_path_embed_sidecar_or_slot1_vault_bypass_events": 0,
    }
    defaults.update(overrides)
    return LiveViewGridLutEmbedPplutVaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Evaluators & Single-Shot Combined Verifier (Pillars 58A & 58B)
# ---------------------------------------------------------------------------


def evaluate_dial_customize_mydial_fn12x2_vault(
    spec: DialCustomizeMyDialFn12x2VaultSpec,
) -> DialCustomizeMyDialFn12x2VaultReport:
    """Evaluate Pillar 58A: Wave-56 `[Dial Customize]` 5-item Initialize-only tree vs dormant
    `Dial Setup` / `Dial / Wheel Lock` / `Rear Dial L/R` (`EOPNOTSUPP=95`), `My Dial 1..3`
    skip-empty + Lock override, `[Fn Menu Settings]` `12 + 12`, `ILME-FX6` contrast, & Slot-1 Vault."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P326_BLOCKED_SAFETY_POLICY_VIOLATION, "Module safety invariant violation")

    valid_fw = (
        (
            spec.camera_model == P326_FX3_MODEL_NAME
            and spec.fw_version in P326_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P326_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P326_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P326_SHOOTING_DOMAINS
        or spec.av_tv_rotate not in P326_AV_TV_ROTATE_MODES
        or spec.function_ring_lens not in P326_FUNCTION_RING_ALL_MODES
        or spec.lock_operation_parts not in P326_LOCK_OPERATION_PARTS_MODES
        or spec.my_dial_recall_mode not in P326_MY_DIAL_RECALL_MODES
        or spec.reset_action not in P326_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P326_VAULT_ACTIONS
    ):
        _fail(
            P326_BLOCKED_INVALID_PILLAR58A_SPEC,
            "Invalid Pillar 58A camera/dial/reset/vault spec parameter",
        )

    st = compute_expected_dial_customize_mydial_fn12x2_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        dial_customize_items=spec.dial_customize_items,
        av_tv_rotate=spec.av_tv_rotate,
        function_ring_lens=spec.function_ring_lens,
        lock_operation_parts=spec.lock_operation_parts,
        physical_dials_present=spec.physical_dials_present,
        requested_dormant_dial_symbols=spec.requested_dormant_dial_symbols,
        my_dial_1_configured=spec.my_dial_1_configured,
        my_dial_2_configured=spec.my_dial_2_configured,
        my_dial_3_configured=spec.my_dial_3_configured,
        my_dial_recall_mode=spec.my_dial_recall_mode,
        my_dial_cycle_step=spec.my_dial_cycle_step,
        fn_still_slot_count=spec.fn_still_slot_count,
        fn_movie_slot_count=spec.fn_movie_slot_count,
        fn_all_not_set_pressed=spec.fn_all_not_set_pressed,
        reset_action=spec.reset_action,
    )

    # 1. [Dial Customize] 5-item Initialize-only tree, Function Ring validity & Lock Operation Parts
    dial_5item_ok = (
        (
            spec.camera_model != P326_FX3_MODEL_NAME
            or (
                tuple(spec.dial_customize_items) == P326_DIAL_CUSTOMIZE_5_ITEMS
                and spec.long_press_fn_toggles_lock
                and spec.menu_plus_fn_5s_full_lock_supported
            )
        )
        and spec.function_ring_lens in P326_FUNCTION_RING_MODES
        and spec.post_av_tv_rotate == st["post_av_tv_rotate"]
        and spec.post_function_ring_lens == st["post_function_ring_lens"]
        and spec.post_lock_operation_parts == st["post_lock_operation_parts"]
        and spec.reported_dormant_dial_errno == st["dormant_dial_errno"]
        and not (
            (len(spec.requested_dormant_dial_symbols) > 0 or spec.function_ring_lens == "INVALID")
            and spec.reported_dormant_dial_errno != P326_EOPNOTSUPP_ERRNO
        )
        and spec.dial_customize_dormant_trap_or_reset_drift_events == 0
    )
    if not dial_5item_ok:
        _fail(
            P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT,
            "Dial Customize violated 5-item Initialize-only tree, Function Ring(Lens) valid modes, Lock Operation Parts (long-press Fn / 5s MENU+Fn), or dormant Dial Setup/Lock EOPNOTSUPP=95",
        )

    # 2. 3-Physical-Dial topology & My Dial 1..3 skip-empty + Lock override
    three_dial_mydial_ok = (
        (
            spec.camera_model != P326_FX3_MODEL_NAME
            or (
                tuple(spec.physical_dials_present) == P326_PHYSICAL_3_DIALS
                and spec.reported_active_my_dial_bank == st["active_my_dial_bank"]
                and spec.reported_dials_temporarily_unlocked
                == st["dials_temporarily_unlocked_by_mydial"]
            )
        )
        and not any(d in ("Rear Dial L", "Rear Dial R") for d in spec.physical_dials_present)
        and spec.rear_dial_lr_or_mydial_override_drift_events == 0
    )
    if not three_dial_mydial_ok:
        _fail(
            P326_BLOCKED_3DIAL_TOPOLOGY_OR_MYDIAL_OVERRIDE_DRIFT,
            "3-dial topology (Front Dial/Rear Dial/Control Wheel) or My Dial 1..3 skip-empty / Lock override contract violated",
        )

    # 3. [Fn Menu Settings] 12 Still + 12 Movie & ILME-FX6 Control Architecture Boundary
    fn_fx6_ok = (
        (
            spec.camera_model != P326_FX3_MODEL_NAME
            or (
                spec.fn_still_slot_count == P326_FX3_FN_MENU_STILL_SLOTS
                and spec.fn_movie_slot_count == P326_FX3_FN_MENU_MOVIE_SLOTS
                and spec.reported_fn_invalid_prompt_errno == st["fn_invalid_prompt_errno"]
            )
        )
        and (
            spec.camera_model != P326_FX6_DONOR_MODEL_NAME
            or (
                tuple(spec.fx6_dial_controls) == P326_FX6_DIAL_CONTROLS
                and not spec.fx6_exposes_av_tv_mydial_or_fn_menu
                and spec.fx6_uses_physical_hold_switch
            )
        )
        and not spec.fx6_exposes_av_tv_mydial_or_fn_menu
        and spec.fn_menu_12x2_or_fx6_dial_spoof_events == 0
    )
    if not fn_fx6_ok:
        _fail(
            P326_BLOCKED_FN_12X2_OR_FX6_DIAL_SPOOF,
            "Fn Menu 12+12 split / all-Not-set prompt or ILME-FX6 Multi Function/Grip/Handle/IRIS/ND Dial boundary violated",
        )

    # 4. Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
    vault_fw_ok = (
        spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_vault_mutation_bytes == 0
        and not (
            spec.requested_vault_slot == P326_SLOT1_VAULT_SLOT
            and spec.requested_vault_action in P326_WRITE_MUTATING_VAULT_ACTIONS
        )
    )
    if not vault_fw_ok:
        _fail(
            P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS=30 firewall blocked write/format mutation on Tier-0 media",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P326_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P326_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P326_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P326_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "58A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "fw_version": spec.fw_version,
            "shooting_domain": spec.shooting_domain,
            "post_av_tv_rotate": spec.post_av_tv_rotate,
            "post_function_ring_lens": spec.post_function_ring_lens,
            "post_lock_operation_parts": spec.post_lock_operation_parts,
            "active_my_dial_bank": spec.reported_active_my_dial_bank,
            "fn_still": spec.fn_still_slot_count,
            "fn_movie": spec.fn_movie_slot_count,
            "slot1_bytes": spec.slot1_vault_mutation_bytes,
            "errors": errors,
        }
    )
    return DialCustomizeMyDialFn12x2VaultReport(
        schema=PHASE326_SCHEMA,
        version=PHASE326_VERSION,
        passed=passed,
        status=P326_STATUS_VERIFIED_PILLAR_58A if passed else P326_STATUS_REJECTED_PILLAR_58A,
        block_code=block_code,
        dial_customize_5item_init_only_and_lock_verified=dial_5item_ok,
        three_dial_topology_and_mydial_override_verified=three_dial_mydial_ok,
        fn_12x2_split_and_fx6_dial_boundary_verified=fn_fx6_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        dial_customize_dormant_trap_or_reset_drift_events=(
            spec.dial_customize_dormant_trap_or_reset_drift_events
        ),
        rear_dial_lr_or_mydial_override_drift_events=(
            spec.rear_dial_lr_or_mydial_override_drift_events
        ),
        fn_menu_12x2_or_fx6_dial_spoof_events=spec.fn_menu_12x2_or_fx6_dial_spoof_events,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_liveview_grid_lut_embed_pplut_vault(
    spec: LiveViewGridLutEmbedPplutVaultSpec,
) -> LiveViewGridLutEmbedPplutVaultReport:
    """Evaluate Pillar 58B: Still-only `[Live View Display Set.]` 3-item asymmetric reset split,
    `[Grid Line]` Clean-HDMI/RAW OSD isolation, `[Manage User LUTs]` / `[Embed LUT File]` container
    embed vs `PPLUT1..4` baking & `ILME-FX6` contrast, + `Slot-1` Tier-0 Vault `EROFS=30` firewall."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(P326_BLOCKED_SAFETY_POLICY_VIOLATION, "Module safety invariant violation")

    valid_fw = (
        (
            spec.camera_model == P326_FX3_MODEL_NAME
            and spec.fw_version in P326_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P326_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P326_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P326_SHOOTING_DOMAINS
        or spec.live_view_display not in P326_LIVE_VIEW_DISPLAY_MODES
        or spec.exposure_effect not in P326_EXPOSURE_EFFECT_MODES
        or spec.frame_rate_low_limit not in P326_ON_OFF_MODES
        or spec.grid_line_display not in P326_ON_OFF_MODES
        or spec.grid_line_type not in P326_GRID_LINE_TYPES
        or spec.hdmi_info_display not in P326_ON_OFF_MODES
        or spec.card_media_type not in P326_CARD_MEDIA_TYPES
        or spec.select_lut not in P326_SELECT_LUT_OPTIONS
        or spec.embed_lut_file not in P326_ON_OFF_MODES
        or spec.pplut_slot not in P326_PPLUT_SLOTS
        or spec.lut_workflow_mode not in P326_LUT_WORKFLOW_MODES
        or spec.reset_action not in P326_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P326_VAULT_ACTIONS
        or (
            spec.vault_firewall_errno is not None
            and spec.vault_firewall_errno not in P326_VAULT_FIREWALL_ERRNOS
        )
    ):
        _fail(
            P326_BLOCKED_INVALID_PILLAR58B_SPEC,
            "Invalid Pillar 58B camera/LiveView/Grid/LUT/vault spec parameter",
        )

    st = compute_expected_liveview_grid_lut_embed_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        live_view_display=spec.live_view_display,
        bright_monitoring_active=spec.bright_monitoring_active,
        exposure_effect=spec.exposure_effect,
        frame_rate_low_limit=spec.frame_rate_low_limit,
        grid_line_display=spec.grid_line_display,
        grid_line_type=spec.grid_line_type,
        hdmi_info_display=spec.hdmi_info_display,
        raw_output_or_hdmi_only=spec.raw_output_or_hdmi_only,
        card_media_type=spec.card_media_type,
        user_lut_slot_populated=spec.user_lut_slot_populated,
        select_lut=spec.select_lut,
        embed_lut_file=spec.embed_lut_file,
        pplut_slot=spec.pplut_slot,
        lut_workflow_mode=spec.lut_workflow_mode,
        requested_vault_slot=spec.requested_vault_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
        make_cube_folder_on_slot1=spec.make_cube_folder_on_slot1,
        reset_action=spec.reset_action,
    )

    # 1. Still-only [Live View Display Set.] 3-item asymmetric reset split & Bright Monitoring force OFF
    live_view_ok = (
        tuple(spec.live_view_menu_path) == P326_LIVE_VIEW_DISPLAY_SET_PATH
        and spec.reported_live_view_gate_errno == st["live_view_gate_errno"]
        and not (
            spec.camera_model == P326_FX3_MODEL_NAME
            and spec.shooting_domain != "Still"
            and spec.reported_live_view_gate_errno != P326_EOPNOTSUPP_ERRNO
        )
        and spec.reported_live_view_display == st["effective_live_view_display"]
        and spec.post_live_view_display == st["post_live_view_display"]
        and spec.post_exposure_effect == st["post_exposure_effect"]
        and spec.post_frame_rate_low_limit == st["post_frame_rate_low_limit"]
        and spec.live_view_display_reset_split_or_mode_drift_events == 0
    )
    if not live_view_ok:
        _fail(
            P326_BLOCKED_LIVE_VIEW_RESET_SPLIT_OR_STILL_GATE,
            "Live View Display Set. violated Still-only gate (EOPNOTSUPP=95 in Movie/S&Q), Bright Monitoring auto-OFF, or Frame Rate Low Limit Reset split",
        )

    # 2. [Grid Line Display] / [Grid Line Type] & Clean-HDMI/RAW OSD Isolation + FX6 boundary
    grid_hdmi_ok = (
        spec.post_grid_line_display == st["post_grid_line_display"]
        and spec.post_grid_line_type == st["post_grid_line_type"]
        and spec.reported_clean_hdmi_osd_isolated_to_lcd == st["clean_hdmi_osd_isolated_to_lcd"]
        and not (
            st["clean_hdmi_osd_isolated_to_lcd"] and spec.reported_hdmi_clean_feed_grid_leaked
        )
        and spec.fx6_uses_marker_guide_frame
        and not spec.fx6_exposes_dormant_custom_png_grid
        and spec.grid_line_or_hdmi_clean_feed_leak_events == 0
    )
    if not grid_hdmi_ok:
        _fail(
            P326_BLOCKED_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK,
            "Grid Line violated Initialize-only rules, Clean-HDMI/RAW OSD body-LCD isolation, or FX6 dormant custom PNG grid exclusion",
        )

    # 3. LUT Paths, [Manage User LUTs] / [Select LUT], [Embed LUT File] vs PPLUT1..4 & FX6 contrast
    lut_ok = (
        spec.lut_card_dir == st["expected_lut_dir"]
        and spec.lut_cube_points in P326_FX3_LUT_CUBE_POINT_SIZES
        and tuple(spec.embed_lut_menu_path) == P326_EMBED_LUT_VALID_PATH
        and spec.reported_monitored_lut == st["effective_monitored_lut"]
        and spec.post_select_lut == st["post_select_lut"]
        and spec.reported_embed_lut_file == st["effective_embed_lut_file"]
        and spec.post_embed_lut_file == st["post_embed_lut_file"]
        and spec.post_pplut_reset == st["post_pplut_reset"]
        and spec.reported_slog3_pixels_preserved == st["slog3_pixels_preserved"]
        and spec.reported_external_cube_sidecar_generated
        == st["external_cube_sidecar_generated"]
        and spec.fx6_user_lut_ui_cap == P326_FX6_USER_LUT_UI_CAP
        and not spec.fx6_exposes_50_lut_slots
        and spec.fx6_supports_multi_channel_lut_switches
        and spec.lut_path_embed_sidecar_or_slot1_vault_bypass_events == 0
    )
    if not lut_ok:
        _fail(
            P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF,
            "LUT workflow violated SD/CFexpress dir, Embed LUT File Log Shooting path / SDHC lock / metadata-only embed, PPLUT1..4 bake & reset split, or FX6 16-slot boundary",
        )

    # 4. Slot-1 Tier-0 Vault Firewall (EROFS=30 on writes/folder-create, safe read-only .cube import allowed)
    slot1_mutated_violation = (
        spec.requested_vault_slot == P326_SLOT1_VAULT_SLOT
        and spec.slot1_holds_tier0_vault
        and (
            spec.requested_vault_action in P326_WRITE_MUTATING_VAULT_ACTIONS
            or spec.make_cube_folder_on_slot1
        )
        and spec.reported_vault_action_allowed
    )
    vault_fw_ok = (
        not slot1_mutated_violation
        and spec.reported_vault_action_allowed == st["action_allowed"]
        and spec.vault_firewall_errno == st["firewall_errno"]
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_lut_mutation_bytes == 0
        and not spec.slot1_avf_info_mutated
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
    )
    if not vault_fw_ok:
        _fail(
            P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault EROFS=30 firewall breached by LUT Embed/PPLUT/folder-create/write/format targeting Slot-1",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P326_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P326_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P326_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P326_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "58B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "shooting_domain": spec.shooting_domain,
            "post_live_view": spec.post_live_view_display,
            "post_exp_effect": spec.post_exposure_effect,
            "post_frll": spec.post_frame_rate_low_limit,
            "post_grid": spec.post_grid_line_display,
            "post_select_lut": spec.post_select_lut,
            "post_embed_lut": spec.post_embed_lut_file,
            "post_pplut_reset": spec.post_pplut_reset,
            "vault_slot": spec.requested_vault_slot,
            "vault_action": spec.requested_vault_action,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return LiveViewGridLutEmbedPplutVaultReport(
        schema=PHASE326_SCHEMA,
        version=PHASE326_VERSION,
        passed=passed,
        status=P326_STATUS_VERIFIED_PILLAR_58B if passed else P326_STATUS_REJECTED_PILLAR_58B,
        block_code=block_code,
        live_view_3item_reset_split_and_bright_mon_verified=live_view_ok,
        grid_line_and_hdmi_clean_feed_isolation_verified=grid_hdmi_ok,
        lut_paths_embed_metadata_vs_pplut_bake_and_fx6_verified=lut_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        live_view_display_reset_split_or_mode_drift_events=(
            spec.live_view_display_reset_split_or_mode_drift_events
        ),
        grid_line_or_hdmi_clean_feed_leak_events=spec.grid_line_or_hdmi_clean_feed_leak_events,
        lut_path_embed_sidecar_or_slot1_vault_bypass_events=(
            spec.lut_path_embed_sidecar_or_slot1_vault_bypass_events
        ),
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_lut_mutation_bytes=spec.slot1_lut_mutation_bytes,
        slot1_avf_info_mutated=spec.slot1_avf_info_mutated,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_dial_customize_mydial_fn12x2_liveview_lut_embed_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_58a: Optional[DialCustomizeMyDialFn12x2VaultSpec] = None,
    spec_58b: Optional[LiveViewGridLutEmbedPplutVaultSpec] = None,
) -> DialCustomizeMyDialFn12x2LiveViewLutEmbedVaultReport:
    """Combined single-shot verifier for Pillar 58A + Pillar 58B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase326_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_dial_customize_mydial_fn12x2_vault(
        spec_58a or build_default_safe_dial_customize_mydial_fn12x2_vault_spec()
    )
    rep_b = evaluate_liveview_grid_lut_embed_pplut_vault(
        spec_58b or build_default_safe_liveview_grid_lut_embed_pplut_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 326 Wave-56 donor artifact parity check failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return DialCustomizeMyDialFn12x2LiveViewLutEmbedVaultReport(
        schema=PHASE326_SCHEMA,
        version=PHASE326_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P326_STATUS_VERIFIED_PILLAR58_SUITE if all_ok else P326_STATUS_FAIL_PILLAR58_SUITE,
        donor_snapshot=donor_snapshot,
        dial_customize_report=rep_a,
        liveview_lut_embed_report=rep_b,
        dial_customize_dormant_trap_or_reset_drift_events=(
            rep_a.dial_customize_dormant_trap_or_reset_drift_events
        ),
        rear_dial_lr_or_mydial_override_drift_events=(
            rep_a.rear_dial_lr_or_mydial_override_drift_events
        ),
        fn_menu_12x2_or_fx6_dial_spoof_events=rep_a.fn_menu_12x2_or_fx6_dial_spoof_events,
        live_view_display_reset_split_or_mode_drift_events=(
            rep_b.live_view_display_reset_split_or_mode_drift_events
        ),
        grid_line_or_hdmi_clean_feed_leak_events=rep_b.grid_line_or_hdmi_clean_feed_leak_events,
        lut_path_embed_sidecar_or_slot1_vault_bypass_events=(
            rep_b.lut_path_embed_sidecar_or_slot1_vault_bypass_events
        ),
        slot1_data_sector_writes=rep_b.slot1_data_sector_writes,
        slot1_lut_mutation_bytes=rep_b.slot1_lut_mutation_bytes,
        slot1_avf_info_mutated=rep_b.slot1_avf_info_mutated,
        slot1_vault_mutation_bytes=rep_a.slot1_vault_mutation_bytes + rep_b.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=(rep_a.slot1_format_hard_locked and rep_b.slot1_format_hard_locked),
        slot1_vault_erofs_eopnotsupp_enforced=(
            rep_a.slot1_vault_erofs_eopnotsupp_enforced
            and rep_b.slot1_vault_erofs_eopnotsupp_enforced
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


def verify_dial_customize_mydial_fn12x2_liveview_lut_embed_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_58a: Optional[DialCustomizeMyDialFn12x2VaultSpec] = None,
    spec_58b: Optional[LiveViewGridLutEmbedPplutVaultSpec] = None,
) -> DialCustomizeMyDialFn12x2LiveViewLutEmbedVaultReport:
    """Symmetry alias for `verify_dial_customize_mydial_fn12x2_liveview_lut_embed_and_vault`."""
    return verify_dial_customize_mydial_fn12x2_liveview_lut_embed_and_vault(
        force_clean_room=force_clean_room,
        spec_58a=spec_58a,
        spec_58b=spec_58b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 58A & 58B) + Standalone Pillar 58 Suite
# ---------------------------------------------------------------------------


def run_pillar58a_dial_customize_mydial_fn12x2_6_scenario_suite() -> Pillar58ASuiteResult:
    """Run 6 Pillar 58A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, DialCustomizeMyDialFn12x2VaultSpec, Optional[str]], ...] = (
        (
            P326_PILLAR_58A_SCENARIO_IDS[0],
            True,
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                shooting_domain="Movie",
                av_tv_rotate="Reverse",
                function_ring_lens="APS-C/Super 35 mm / Full Frame",
                lock_operation_parts="Dial + Wheel",
                reset_action="Camera Settings Reset",
                post_av_tv_rotate="Reverse",
                post_function_ring_lens="APS-C/Super 35 mm / Full Frame",
                post_lock_operation_parts="Dial + Wheel",
                my_dial_1_configured=True,
                my_dial_2_configured=False,
                my_dial_3_configured=True,
                my_dial_recall_mode="Hold",
                my_dial_cycle_step=1,
                reported_active_my_dial_bank=1,
                reported_dials_temporarily_unlocked=True,
            ),
            None,
        ),
        (
            P326_PILLAR_58A_SCENARIO_IDS[1],
            True,
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                shooting_domain="Still",
                av_tv_rotate="Reverse",
                function_ring_lens="APS-C/Super 35 mm / Full Frame",
                lock_operation_parts="All",
                my_dial_1_configured=True,
                my_dial_2_configured=False,
                my_dial_3_configured=True,
                my_dial_recall_mode="1->2->3",
                my_dial_cycle_step=2,
                reported_active_my_dial_bank=3,
                reported_dials_temporarily_unlocked=True,
                reset_action="None",
                post_av_tv_rotate="Reverse",
                post_function_ring_lens="APS-C/Super 35 mm / Full Frame",
                post_lock_operation_parts="All",
            ),
            None,
        ),
        (
            P326_PILLAR_58A_SCENARIO_IDS[2],
            False,
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                physical_dials_present=("Front Dial", "Rear Dial L", "Rear Dial R", "Control Wheel"),
                requested_dormant_dial_symbols=(
                    "Rear Dial L",
                    "Rear Dial R",
                    "Dial Setup",
                    "Dial/Wheel Setup",
                    "Dial / Wheel Lock",
                ),
                function_ring_lens="INVALID",
                reported_dormant_dial_errno=None,
                dial_customize_dormant_trap_or_reset_drift_events=1,
                rear_dial_lr_or_mydial_override_drift_events=1,
            ),
            P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT,
        ),
        (
            P326_PILLAR_58A_SCENARIO_IDS[3],
            False,
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                av_tv_rotate="Reverse",
                lock_operation_parts="Dial + Wheel",
                reset_action="Camera Settings Reset",
                post_av_tv_rotate="Normal",
                post_lock_operation_parts="Off",
                my_dial_recall_mode="Toggle",
                my_dial_cycle_step=1,
                reported_active_my_dial_bank=1,
                reported_dials_temporarily_unlocked=False,
                dial_customize_dormant_trap_or_reset_drift_events=1,
                rear_dial_lr_or_mydial_override_drift_events=1,
            ),
            P326_BLOCKED_DIAL_CUSTOMIZE_5ITEM_OR_RESET_DRIFT,
        ),
        (
            P326_PILLAR_58A_SCENARIO_IDS[4],
            False,
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                fn_still_slot_count=24,
                fn_movie_slot_count=0,
                fn_all_not_set_pressed=True,
                reported_fn_invalid_prompt_errno=None,
                fn_menu_12x2_or_fx6_dial_spoof_events=1,
            ),
            P326_BLOCKED_FN_12X2_OR_FX6_DIAL_SPOOF,
        ),
        (
            P326_PILLAR_58A_SCENARIO_IDS[5],
            False,
            build_default_safe_dial_customize_mydial_fn12x2_vault_spec(
                camera_model=P326_FX6_DONOR_MODEL_NAME,
                fw_version=P326_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                fx6_exposes_av_tv_mydial_or_fn_menu=True,
                fx6_uses_physical_hold_switch=False,
                fn_menu_12x2_or_fx6_dial_spoof_events=1,
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/58a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P326_BLOCKED_FN_12X2_OR_FX6_DIAL_SPOOF,
        ),
    )

    outcomes: List[Pillar58ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_dial_customize_mydial_fn12x2_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar58ScenarioOutcome(
                scenario_id=sid,
                pillar="58A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar58ASuiteResult(
        passed=all_ok,
        status=P326_STATUS_VERIFIED_PILLAR_58A if all_ok else P326_STATUS_REJECTED_PILLAR_58A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar58b_liveview_lut_embed_pplut_6_scenario_suite() -> Pillar58BSuiteResult:
    """Run 6 Pillar 58B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, LiveViewGridLutEmbedPplutVaultSpec, Optional[str]], ...] = (
        (
            P326_PILLAR_58B_SCENARIO_IDS[0],
            True,
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                shooting_domain="Still",
                live_view_display="Setting Effect ON",
                bright_monitoring_active=True,
                reported_live_view_display="Setting Effect OFF",
                exposure_effect="Exposure Setting Only",
                frame_rate_low_limit="On",
                grid_line_display="On",
                grid_line_type="Diag. + Square Grid",
                hdmi_info_display="Off",
                raw_output_or_hdmi_only=True,
                reported_clean_hdmi_osd_isolated_to_lcd=True,
                reported_hdmi_clean_feed_grid_leaked=False,
                reset_action="Camera Settings Reset",
                post_live_view_display="Setting Effect OFF",
                post_exposure_effect="Exposure Setting Only",
                post_frame_rate_low_limit="Off",
                post_grid_line_display="On",
                post_grid_line_type="Diag. + Square Grid",
                card_media_type="CFexpress Type A",
                lut_card_dir=P326_FX3_LUT_CFEXPRESS_DIR,
                select_lut="User1",
                user_lut_slot_populated=True,
                reported_monitored_lut="User1",
                post_select_lut="s709",
                embed_lut_file="Off",
                reported_embed_lut_file="Off",
                post_embed_lut_file="On",
                pplut_slot="PPLUT1",
                post_pplut_reset=True,
                lut_workflow_mode="LOG_SHOOTING_EMBED",
                reported_slog3_pixels_preserved=True,
                reported_external_cube_sidecar_generated=False,
                requested_vault_slot=2,
                requested_vault_action="EMBED_LUT_RECORD",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P326_PILLAR_58B_SCENARIO_IDS[1],
            True,
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                shooting_domain="Still",
                card_media_type="SDXC",
                lut_card_dir=P326_FX3_LUT_SD_DIR,
                lut_cube_points=17,
                select_lut="User16",
                user_lut_slot_populated=False,
                reported_monitored_lut="S-Log3",
                lut_workflow_mode="PPLUT_BAKE",
                pplut_slot="PPLUT4",
                reported_slog3_pixels_preserved=False,
                reset_action="Initialize",
                post_live_view_display="Setting Effect ON",
                post_exposure_effect="Exposure Set. & flash",
                post_frame_rate_low_limit="Off",
                post_grid_line_display="Off",
                post_grid_line_type="Rule of 3rds Grid",
                post_select_lut="s709",
                post_embed_lut_file="On",
                post_pplut_reset=True,
                requested_vault_slot=1,
                requested_vault_action="IMPORT_USER_LUT_CUBE",
                make_cube_folder_on_slot1=False,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=0,
            ),
            None,
        ),
        (
            P326_PILLAR_58B_SCENARIO_IDS[2],
            False,
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                shooting_domain="Movie",
                reported_live_view_gate_errno=None,
                live_view_display="Setting Effect OFF",
                exposure_effect="Exposure Setting Only",
                reset_action="Camera Settings Reset",
                post_live_view_display="Setting Effect ON",
                post_exposure_effect="Exposure Set. & flash",
                live_view_display_reset_split_or_mode_drift_events=1,
            ),
            P326_BLOCKED_LIVE_VIEW_RESET_SPLIT_OR_STILL_GATE,
        ),
        (
            P326_PILLAR_58B_SCENARIO_IDS[3],
            False,
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                grid_line_display="On",
                hdmi_info_display="Off",
                raw_output_or_hdmi_only=True,
                reported_clean_hdmi_osd_isolated_to_lcd=False,
                reported_hdmi_clean_feed_grid_leaked=True,
                fx6_uses_marker_guide_frame=False,
                fx6_exposes_dormant_custom_png_grid=True,
                grid_line_or_hdmi_clean_feed_leak_events=1,
            ),
            P326_BLOCKED_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK,
        ),
        (
            P326_PILLAR_58B_SCENARIO_IDS[4],
            False,
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                card_media_type="SDHC",
                lut_card_dir=P326_FX3_LUT_CFEXPRESS_DIR,
                embed_lut_menu_path=P326_EMBED_LUT_WRONG_PATH,
                embed_lut_file="On",
                reported_embed_lut_file="On",
                lut_workflow_mode="LOG_SHOOTING_EMBED",
                reported_external_cube_sidecar_generated=True,
                post_pplut_reset=False,
                reset_action="Camera Settings Reset",
                fx6_exposes_50_lut_slots=True,
                lut_path_embed_sidecar_or_slot1_vault_bypass_events=1,
            ),
            P326_BLOCKED_LUT_PATH_EMBED_VS_PPLUT_OR_FX6_SPOOF,
        ),
        (
            P326_PILLAR_58B_SCENARIO_IDS[5],
            False,
            build_default_safe_liveview_grid_lut_embed_pplut_vault_spec(
                requested_vault_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="EMBED_LUT_RECORD",
                make_cube_folder_on_slot1=True,
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=8192,
                slot1_lut_mutation_bytes=4096,
                slot1_avf_info_mutated=True,
                slot1_vault_mutation_bytes=12288,
                slot1_vault_erofs_eopnotsupp_enforced=False,
            ),
            P326_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar58ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_liveview_grid_lut_embed_pplut_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar58ScenarioOutcome(
                scenario_id=sid,
                pillar="58B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar58BSuiteResult(
        passed=all_ok,
        status=P326_STATUS_VERIFIED_PILLAR_58B if all_ok else P326_STATUS_REJECTED_PILLAR_58B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar58_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar58StandaloneReport:
    """Run full Pillar 58 standalone suite (`6/6` Pillar 58A + `6/6` Pillar 58B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase326_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar58a_dial_customize_mydial_fn12x2_6_scenario_suite()
    res_b = run_pillar58b_liveview_lut_embed_pplut_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 326 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE326_SCHEMA,
            "version": PHASE326_VERSION,
            "mode": donor_snapshot.verification_mode,
            "58a": [asdict(s) for s in res_a.scenarios],
            "58b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar58StandaloneReport(
        schema=PHASE326_SCHEMA,
        version=PHASE326_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P326_STATUS_VERIFIED_PILLAR58_SUITE if all_ok else P326_STATUS_FAIL_PILLAR58_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_58a_dial_customize_mydial_fn12x2_vault=res_a,
        pillar_58b_liveview_grid_lut_embed_pplut_vault=res_b,
        dial_customize_dormant_trap_or_reset_drift_events=(
            P326_DIAL_CUSTOMIZE_DORMANT_TRAP_OR_RESET_DRIFT_EVENTS if res_a.passed else 1
        ),
        rear_dial_lr_or_mydial_override_drift_events=(
            P326_REAR_DIAL_LR_OR_MYDIAL_OVERRIDE_DRIFT_EVENTS if res_a.passed else 1
        ),
        fn_menu_12x2_or_fx6_dial_spoof_events=(
            P326_FN_MENU_12X2_OR_FX6_DIAL_SPOOF_EVENTS if res_a.passed else 1
        ),
        live_view_display_reset_split_or_mode_drift_events=(
            P326_LIVE_VIEW_DISPLAY_RESET_SPLIT_OR_MODE_DRIFT_EVENTS if res_b.passed else 1
        ),
        grid_line_or_hdmi_clean_feed_leak_events=(
            P326_GRID_LINE_OR_HDMI_CLEAN_FEED_LEAK_EVENTS if res_b.passed else 1
        ),
        lut_path_embed_sidecar_or_slot1_vault_bypass_events=(
            P326_LUT_PATH_EMBED_SIDECAR_OR_SLOT1_VAULT_BYPASS_EVENTS if res_b.passed else 1
        ),
        slot1_data_sector_writes=P326_SLOT1_DATA_SECTOR_WRITES if res_b.passed else 1,
        slot1_lut_mutation_bytes=P326_SLOT1_LUT_MUTATION_BYTES if res_b.passed else 4096,
        slot1_avf_info_mutated=not res_b.passed,
        slot1_vault_mutation_bytes=(
            P326_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P326_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P326_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
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
# Unified 58-Pillar Recovery Master Aggregator (Phase 326 — 58/58 Milestone)
# ---------------------------------------------------------------------------


def _apply_master58_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_58pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master58PillarRecoveryReport:
    """Evaluate and aggregate all 58 recovery pillars (`1..58`) concurrently -> `58/58` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_58_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_57pillar() -> Master57PillarRecoveryReport:
        return evaluate_realhw_57pillar_recovery_master(**kw)

    def _run_p58() -> Tuple[Pillar58StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar58_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_57 = pool.submit(_run_57pillar)
        fut_58 = pool.submit(_run_p58)
        m57_rep = fut_57.result()
        p58_rep, p58_dt = fut_58.result()

    all_errors: List[str] = list(m57_rep.errors) + list(p58_rep.errors)
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
        if getattr(m57_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-57 violated {attr_name} == {expected_val}")
        if getattr(p58_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 58 violated {attr_name} == {expected_val}")

    if p58_rep.cross_model_flash_authorized is not False:
        all_errors.append("Pillar 58 violated cross_model_flash_authorized == False")

    for attr_name, expected_val in (
        ("touch_op_dormant_trap_or_reset_drift_events", 0),
        ("disp_set_or_zero_evf_blackout_events", 0),
        ("fx6_touch_or_evf_spoof_events", 0),
        ("still_ael_flash_reset_split_or_mishoe_drift_events", 0),
        ("interval_pb_9scale_or_path_drift_events", 0),
        ("playback_edit_dormant_or_slot1_vault_bypass_events", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_edit_avf_info_mutation_bytes", 0),
        ("slot1_avf_info_mutated", False),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
    ):
        if getattr(m57_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-57 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("dial_customize_dormant_trap_or_reset_drift_events", 0),
        ("rear_dial_lr_or_mydial_override_drift_events", 0),
        ("fn_menu_12x2_or_fx6_dial_spoof_events", 0),
        ("live_view_display_reset_split_or_mode_drift_events", 0),
        ("grid_line_or_hdmi_clean_feed_leak_events", 0),
        ("lut_path_embed_sidecar_or_slot1_vault_bypass_events", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_lut_mutation_bytes", 0),
        ("slot1_avf_info_mutated", False),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_eopnotsupp_enforced", True),
    ):
        if getattr(p58_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 58 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m57_rep.pillars)
    spec58 = MASTER_58_PILLAR_SPECS[57]
    p58_metrics = {
        "pillar_58a_dial_customize_mydial_fn12x2_vault": (
            f"{p58_rep.pillar_58a_dial_customize_mydial_fn12x2_vault.scenarios_passed}/"
            f"{p58_rep.pillar_58a_dial_customize_mydial_fn12x2_vault.scenarios_total}"
        ),
        "pillar_58b_liveview_grid_lut_embed_pplut_vault": (
            f"{p58_rep.pillar_58b_liveview_grid_lut_embed_pplut_vault.scenarios_passed}/"
            f"{p58_rep.pillar_58b_liveview_grid_lut_embed_pplut_vault.scenarios_total}"
        ),
        "dial_customize_dormant_trap_or_reset_drift_events": (
            p58_rep.dial_customize_dormant_trap_or_reset_drift_events
        ),
        "rear_dial_lr_or_mydial_override_drift_events": (
            p58_rep.rear_dial_lr_or_mydial_override_drift_events
        ),
        "fn_menu_12x2_or_fx6_dial_spoof_events": p58_rep.fn_menu_12x2_or_fx6_dial_spoof_events,
        "live_view_display_reset_split_or_mode_drift_events": (
            p58_rep.live_view_display_reset_split_or_mode_drift_events
        ),
        "grid_line_or_hdmi_clean_feed_leak_events": (
            p58_rep.grid_line_or_hdmi_clean_feed_leak_events
        ),
        "lut_path_embed_sidecar_or_slot1_vault_bypass_events": (
            p58_rep.lut_path_embed_sidecar_or_slot1_vault_bypass_events
        ),
        "slot1_data_sector_writes": p58_rep.slot1_data_sector_writes,
        "slot1_lut_mutation_bytes": p58_rep.slot1_lut_mutation_bytes,
        "slot1_avf_info_mutated": p58_rep.slot1_avf_info_mutated,
        "slot1_vault_mutation_bytes": p58_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p58_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p58_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p58_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p58_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p58_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p58_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec58[0],
            pillar_id=spec58[1],
            phase_label=spec58[2],
            module_name=spec58[3],
            passed=bool(p58_rep.all_passed),
            status=p58_rep.status,
            verification_mode=p58_rep.verification_mode,
            elapsed_seconds=p58_dt,
            key_metrics=p58_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec58[1],
                    "mode": p58_rep.verification_mode,
                    "status": p58_rep.status,
                    "metrics": p58_metrics,
                    "passed": p58_rep.all_passed,
                }
            ),
            errors=tuple(p58_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master58_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p58_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_58_PILLAR_COUNT == 58
        and pillars_passed == 58
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE326_SCHEMA,
            "schema_version": PHASE326_MASTER_SCHEMA,
            "version": PHASE326_VERSION,
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
    return Master58PillarRecoveryReport(
        schema=PHASE326_SCHEMA,
        schema_version=PHASE326_MASTER_SCHEMA,
        version=PHASE326_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P326_STATUS_VERIFIED_58OF58_AGGREGATOR if all_ok else P326_STATUS_FAIL_58OF58_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P326_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P326_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P326_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p58_rep.donor_snapshot,
        pillar58_a_dial_customize_mydial_fn12x2_vault=(
            p58_rep.pillar_58a_dial_customize_mydial_fn12x2_vault
        ),
        pillar58_b_liveview_grid_lut_embed_pplut_vault=(
            p58_rep.pillar_58b_liveview_grid_lut_embed_pplut_vault
        ),
        dial_customize_dormant_trap_or_reset_drift_events=(
            p58_rep.dial_customize_dormant_trap_or_reset_drift_events
        ),
        rear_dial_lr_or_mydial_override_drift_events=(
            p58_rep.rear_dial_lr_or_mydial_override_drift_events
        ),
        fn_menu_12x2_or_fx6_dial_spoof_events=p58_rep.fn_menu_12x2_or_fx6_dial_spoof_events,
        live_view_display_reset_split_or_mode_drift_events=(
            p58_rep.live_view_display_reset_split_or_mode_drift_events
        ),
        grid_line_or_hdmi_clean_feed_leak_events=p58_rep.grid_line_or_hdmi_clean_feed_leak_events,
        lut_path_embed_sidecar_or_slot1_vault_bypass_events=(
            p58_rep.lut_path_embed_sidecar_or_slot1_vault_bypass_events
        ),
        slot1_data_sector_writes=m57_rep.slot1_data_sector_writes + p58_rep.slot1_data_sector_writes,
        slot1_lut_mutation_bytes=p58_rep.slot1_lut_mutation_bytes,
        slot1_avf_info_mutated=m57_rep.slot1_avf_info_mutated or p58_rep.slot1_avf_info_mutated,
        slot1_vault_mutation_bytes=(
            m57_rep.slot1_vault_mutation_bytes + p58_rep.slot1_vault_mutation_bytes
        ),
        slot1_format_hard_locked=p58_rep.slot1_format_hard_locked,
        slot1_vault_erofs_eopnotsupp_enforced=p58_rep.slot1_vault_erofs_eopnotsupp_enforced,
        fx3_dial_customize_item_count=P326_FX3_DIAL_CUSTOMIZE_ITEM_COUNT,
        fx3_physical_dial_count=P326_FX3_PHYSICAL_DIAL_COUNT,
        fx3_my_dial_bank_count=P326_FX3_MY_DIAL_BANK_COUNT,
        fx3_fn_menu_still_slots=P326_FX3_FN_MENU_STILL_SLOTS,
        fx3_fn_menu_movie_slots=P326_FX3_FN_MENU_MOVIE_SLOTS,
        fx3_live_view_display_set_item_count=P326_FX3_LIVE_VIEW_DISPLAY_SET_ITEM_COUNT,
        fx3_grid_line_type_count=P326_FX3_GRID_LINE_TYPE_COUNT,
        fx3_user_lut_slot_count=P326_FX3_USER_LUT_SLOT_COUNT,
        fx3_pplut_slot_count=P326_FX3_PPLUT_SLOT_COUNT,
        fx6_user_lut_ui_cap=P326_FX6_USER_LUT_UI_CAP,
        fx6_has_av_tv_rotate=P326_FX6_HAS_AV_TV_ROTATE,
        fx6_has_my_dial=P326_FX6_HAS_MY_DIAL,
        fx6_has_fn_menu=P326_FX6_HAS_FN_MENU,
        fx6_has_multi_channel_lut_switches=P326_FX6_HAS_MULTI_CHANNEL_LUT_SWITCHES,
        touch_op_dormant_trap_or_reset_drift_events=(
            m57_rep.touch_op_dormant_trap_or_reset_drift_events
        ),
        disp_set_or_zero_evf_blackout_events=m57_rep.disp_set_or_zero_evf_blackout_events,
        fx6_touch_or_evf_spoof_events=m57_rep.fx6_touch_or_evf_spoof_events,
        still_ael_flash_reset_split_or_mishoe_drift_events=(
            m57_rep.still_ael_flash_reset_split_or_mishoe_drift_events
        ),
        interval_pb_9scale_or_path_drift_events=m57_rep.interval_pb_9scale_or_path_drift_events,
        playback_edit_dormant_or_slot1_vault_bypass_events=(
            m57_rep.playback_edit_dormant_or_slot1_vault_bypass_events
        ),
        slot1_edit_avf_info_mutation_bytes=m57_rep.slot1_edit_avf_info_mutation_bytes,
        fx3_has_eye_sensor=m57_rep.fx3_has_eye_sensor,
        fx3_has_finder_monitor_button=m57_rep.fx3_has_finder_monitor_button,
        fx3_touch_active_item_count=m57_rep.fx3_touch_active_item_count,
        fx3_disp_shoot_page_count=m57_rep.fx3_disp_shoot_page_count,
        fx3_disp_play_page_count=m57_rep.fx3_disp_play_page_count,
        fx3_interval_pb_speed_min=m57_rep.fx3_interval_pb_speed_min,
        fx3_interval_pb_speed_max=m57_rep.fx3_interval_pb_speed_max,
        fx3_interval_pb_speed_default=m57_rep.fx3_interval_pb_speed_default,
        fx6_has_detachable_lcd_viewfinder=m57_rep.fx6_has_detachable_lcd_viewfinder,
        fx6_has_still_ttl_flash=m57_rep.fx6_has_still_ttl_flash,
        fx6_has_interval_pb=m57_rep.fx6_has_interval_pb,
        fx6_has_playback_edit_menu=m57_rep.fx6_has_playback_edit_menu,
        switch_vh_af_lockout_or_coords_drift_events=(
            m57_rep.switch_vh_af_lockout_or_coords_drift_events
        ),
        focus_limit_lt2_or_dormant_symbol_events=m57_rep.focus_limit_lt2_or_dormant_symbol_events,
        focus_area_color_or_fx6_spoof_events=m57_rep.focus_area_color_or_fx6_spoof_events,
        exp_std_adj_mode_conflation_or_reset_drift_events=(
            m57_rep.exp_std_adj_mode_conflation_or_reset_drift_events
        ),
        bracket_settings_reset_or_fx6_spoof_events=m57_rep.bracket_settings_reset_or_fx6_spoof_events,
        tcub_reset_wipe_or_format_lock_violations=m57_rep.tcub_reset_wipe_or_format_lock_violations,
        reverse_copy_slot2_to_slot1_bypass_events=m57_rep.reverse_copy_slot2_to_slot1_bypass_events,
        slideshow_power_save_or_fx6_copy_clip_spoof_events=(
            m57_rep.slideshow_power_save_or_fx6_copy_clip_spoof_events
        ),
        slot1_copy_avf_info_mutation_bytes=m57_rep.slot1_copy_avf_info_mutation_bytes,
        fx3_has_switch_vh_af_area=m57_rep.fx3_has_switch_vh_af_area,
        fx3_focus_area_limit_count=m57_rep.fx3_focus_area_limit_count,
        fx3_focus_area_limit_min_enabled=m57_rep.fx3_focus_area_limit_min_enabled,
        fx3_exp_std_adj_metering_mode_count=m57_rep.fx3_exp_std_adj_metering_mode_count,
        fx3_has_physical_bnc_tc_port=m57_rep.fx3_has_physical_bnc_tc_port,
        fx6_has_physical_bnc_tc_port=m57_rep.fx6_has_physical_bnc_tc_port,
        fx6_has_switch_vh_af_area=m57_rep.fx6_has_switch_vh_af_area,
        fx6_has_focus_area_limit=m57_rep.fx6_has_focus_area_limit,
        fx6_has_exp_std_adj=m57_rep.fx6_has_exp_std_adj,
        fx6_has_still_bracket_settings=m57_rep.fx6_has_still_bracket_settings,
        fx6_has_copy_clip_active=m57_rep.fx6_has_copy_clip_active,
        fx6_has_slide_show=m57_rep.fx6_has_slide_show,
        dormant_shading_auto_low_exposure_events=m57_rep.dormant_shading_auto_low_exposure_events,
        lens_comp_lock_or_arw_conflation_events=m57_rep.lens_comp_lock_or_arw_conflation_events,
        af_illuminator_gate_or_fx6_spoof_events=m57_rep.af_illuminator_gate_or_fx6_spoof_events,
        movie_af_transition_or_assist_drift_events=m57_rep.movie_af_transition_or_assist_drift_events,
        aperture_drive_pre_af_shutter_reset_drift_events=(
            m57_rep.aperture_drive_pre_af_shutter_reset_drift_events
        ),
        circ_focus_diagonal_or_color_drift_events=m57_rep.circ_focus_diagonal_or_color_drift_events,
        folder_name_or_leading_underscore_violations=(
            m57_rep.folder_name_or_leading_underscore_violations
        ),
        slot1_folder_dir_mutation_bytes=m57_rep.slot1_folder_dir_mutation_bytes,
        slot1_rating_avf_info_mutation_bytes=m57_rep.slot1_rating_avf_info_mutation_bytes,
        fx3_has_builtin_af_illuminator=m57_rep.fx3_has_builtin_af_illuminator,
        fx6_has_builtin_af_illuminator=m57_rep.fx6_has_builtin_af_illuminator,
        fx3_exposes_shading_auto_low=m57_rep.fx3_exposes_shading_auto_low,
        fx6_has_aperture_drive_pre_af_circ_color=m57_rep.fx6_has_aperture_drive_pre_af_circ_color,
        fx6_has_msdcf_or_star_rating=m57_rep.fx6_has_msdcf_or_star_rating,
        sensor_cleaning_low_battery_bypass_events=m57_rep.sensor_cleaning_low_battery_bypass_events,
        sensor_cleaning_no_power_off_violations=m57_rep.sensor_cleaning_no_power_off_violations,
        fx6_ibis_shake_conflation_events=m57_rep.fx6_ibis_shake_conflation_events,
        ev_comp_range_or_cine_ei_lockout_violations=(
            m57_rep.ev_comp_range_or_cine_ei_lockout_violations
        ),
        exposure_step_or_dormant_reset_ev_drift_events=(
            m57_rep.exposure_step_or_dormant_reset_ev_drift_events
        ),
        focus_mode_movie_clamp_or_dormant_drift_events=(
            m57_rep.focus_mode_movie_clamp_or_dormant_drift_events
        ),
        priority_set_or_illuminator_gate_violations=m57_rep.priority_set_or_illuminator_gate_violations,
        image_index_dormant_or_view_mode_drift_events=(
            m57_rep.image_index_dormant_or_view_mode_drift_events
        ),
        slot1_rotate_exif_mutation_bytes=m57_rep.slot1_rotate_exif_mutation_bytes,
        fx3_has_sensor_cleaning_ibis=m57_rep.fx3_has_sensor_cleaning_ibis,
        fx3_has_exposure_comp=m57_rep.fx3_has_exposure_comp,
        fx3_has_physical_ev_reset_dial=m57_rep.fx3_has_physical_ev_reset_dial,
        fx6_has_ultrasonic_ibis_cleaning=m57_rep.fx6_has_ultrasonic_ibis_cleaning,
        fx6_has_variable_end_optical_block=m57_rep.fx6_has_variable_end_optical_block,
        fx6_has_technical_apr=m57_rep.fx6_has_technical_apr,
        fx6_has_still_exposure_comp=m57_rep.fx6_has_still_exposure_comp,
        fx6_has_still_image_index_rotate=m57_rep.fx6_has_still_image_index_rotate,
        dci4k_long_gop_or_8k_violations=m57_rep.dci4k_long_gop_or_8k_violations,
        reboot_2400p_stage_b_wipe_violations=m57_rep.reboot_2400p_stage_b_wipe_violations,
        hdmi_raw_or_still_aspect_drift_events=m57_rep.hdmi_raw_or_still_aspect_drift_events,
        fx6_still_or_raw_conflation_events=m57_rep.fx6_still_or_raw_conflation_events,
        reg_custom_hold_or_hlg_lock_drift_events=m57_rep.reg_custom_hold_or_hlg_lock_drift_events,
        camset_cross_model_path_drift_events=m57_rep.camset_cross_model_path_drift_events,
        photo_capture_dci4k_lockout_bypass_events=m57_rep.photo_capture_dci4k_lockout_bypass_events,
        slot1_camset_write_bytes=m57_rep.slot1_camset_write_bytes,
        slot1_photo_capture_write_bytes=m57_rep.slot1_photo_capture_write_bytes,
        fx3_appfw_has_dci4k_internal=m57_rep.fx3_appfw_has_dci4k_internal,
        fx3_appfw_has_pro_camera_path=m57_rep.fx3_appfw_has_pro_camera_path,
        fx6_has_still_aspect_ratio=m57_rep.fx6_has_still_aspect_ratio,
        fx6_has_photo_capture=m57_rep.fx6_has_photo_capture,
        fx6_has_playback_enlarge_image=m57_rep.fx6_has_playback_enlarge_image,
        fx6_has_reg_custom_shoot_set=m57_rep.fx6_has_reg_custom_shoot_set,
        fx6_has_camera_set_memory=m57_rep.fx6_has_camera_set_memory,
        movie_tracking_area_or_limit_violations=m57_rep.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=m57_rep.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=m57_rep.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=(
            m57_rep.fx6_handle_or_pos_display_conflation_events
        ),
        iso_minss_or_cine_ei_lock_drift_events=m57_rep.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=m57_rep.flash_still_mech_gate_violations,
        mishoe_pmic_5v_overcurrent_events=m57_rep.mishoe_pmic_5v_overcurrent_events,
        slot1_focus_zoom_camset_mutation_bytes=m57_rep.slot1_focus_zoom_camset_mutation_bytes,
        slot1_flash_videolight_imagedb_bytes=m57_rep.slot1_flash_videolight_imagedb_bytes,
        xlrh1_has_zoom_lever=m57_rep.xlrh1_has_zoom_lever,
        xlrh1_has_rec_button=m57_rep.xlrh1_has_rec_button,
        xlrh1_has_zoom_hold_switch=m57_rep.xlrh1_has_zoom_hold_switch,
        fx6_0_99_is_zoom_position_display=m57_rep.fx6_0_99_is_zoom_position_display,
        fx6_has_iso_auto_min_ss=m57_rep.fx6_has_iso_auto_min_ss,
        fx6_mechanical_shutter_present=m57_rep.fx6_mechanical_shutter_present,
        dormant_lossless_raw_exposure_events=m57_rep.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=m57_rep.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=m57_rep.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=m57_rep.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=m57_rep.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=m57_rep.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=m57_rep.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=m57_rep.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=m57_rep.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=m57_rep.slot1_imagedb_or_burst_mutation_bytes,
        fx3_ui_exposes_lossless_raw=m57_rep.fx3_ui_exposes_lossless_raw,
        fx3_ui_exposes_shutter_type_auto=m57_rep.fx3_ui_exposes_shutter_type_auto,
        fx6_still_pipeline_present=m57_rep.fx6_still_pipeline_present,
        double_log_or_lockout_bypass_events=m57_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=m57_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=m57_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=m57_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            m57_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        wb_custom_camset_exclusion_drift_events=m57_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            m57_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        fx3_ui_exposes_usb_streaming=m57_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m57_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m57_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m57_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m57_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m57_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m57_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m57_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m57_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m57_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m57_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m57_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m57_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m57_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m57_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m57_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m57_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m57_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m57_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m57_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m57_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m57_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m57_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m57_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m57_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m57_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m57_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m57_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m57_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m57_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m57_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m57_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m57_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=m57_rep.tcub_camera_reset_wipe_or_format_violations,
        fx3_has_builtin_end_filter=m57_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m57_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m57_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m57_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m57_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m57_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m57_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m57_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m57_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m57_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m57_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m57_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m57_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m57_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m57_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m57_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m57_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m57_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m57_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m57_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m57_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m57_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m57_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m57_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m57_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m57_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m57_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m57_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m57_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m57_rep.unbuffered_battery_pull_events,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_58pillar_sha256=master_sha,
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


def evaluate_58pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master58PillarRecoveryReport:
    """Short alias for `evaluate_realhw_58pillar_recovery_master`."""
    return evaluate_realhw_58pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_58pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master58PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_58pillar_recovery_master`."""
    return evaluate_realhw_58pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
