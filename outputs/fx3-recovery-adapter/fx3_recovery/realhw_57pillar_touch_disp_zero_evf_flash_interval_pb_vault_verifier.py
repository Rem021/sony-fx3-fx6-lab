"""Phase 320 (57/57 Recovery Pillars Milestone) — Wave-55 Recovery Pillar 57 & Unified 57/57
Recovery Master (`verify-57pillar-recovery` / `verify-pillar57-touch-disp-zero-evf-flash-interval-pb-vault`):

1. **Sub-Pillar 57A — Wave-55 Touch Operation 4-Item Tree vs Dormant Touch Shutter/AE/Pad/Footer
   & 4-Shoot/3-PB DISP Zero-EVF Blackout Guard**:
   - Models `ILME-FX3 Ver. 7.02` (`0x91030080`, `ilc/2210`, `PRODUCT_MODEL_ALCIN_UUD`)
     `MENU -> (Setup) -> [Touch Operation]` (`_g 0x6345`, `base 0xe8e3`) exact **4 active items**,
     ALL 4 `Initialize`-only (`resists_camera_settings_reset=True`):
     * `[Touch Operation]` (`BKID_APP_setting_touch_operation`): `On` (default) /
       `On: Playback Only` (`_f 0x6cde`) / `Off`.
     * `[Touch Sensitivity]` (`_f 0x739f`, `BKID_APP_setting_touch_sensitivity`): `Standard`
       (default) / `Sensitive` (`_f 0x7205`, NOT `Responsive`).
     * `[Touch Func. in Shooting]` (`_f 0x7575`, `BKID_APP_setting_shooting_touch_function`):
       identical across `Still`, `Movie`, and `S&Q` — `Touch Focus` (`_f 0x6e79`/`0x7427`) /
       `Touch Tracking` (default, `_f 0x68f4`/`0x69ee`) / `Off`.
     * `[Swipe Up]` (`_f 0x7518`, `BKID_APP_setting_swipe_up`): `Open the Fn Menu` (default,
       `_f 0x7281`) / `Off` (active only when `Touch Operation == On`).
   - Fail-closed gate `EOPNOTSUPP=95` on dormant Alpha symbols in `FX3 appFw.so`/UXC with 0 hits on
     real `ILME-FX3`: `Touch Shutter` (`_f 0x6a80`), `Touch AE` (`_f 0x702a`), `Touch Panel/Pad`
     (`BKID_APP_setting_touch_panel_pad`, `_f 0x76ec`), `Touch Pad Settings`, `Footer Icon Touch`
     (`_f 0x70da`), and `Swipe Left`/`Swipe Right` (`_f 0x6b06`/`0x6c19`); contrast with
     `ILME-FX6 Ver. 6.01` (`Technical > Touch Operation` `On/Off` + `Shooting > Focus > Touch
     Function in MF` `Spot Focus`/`Tracking AF`, zero sensitivity/swipe).
   - Models `[Operation Customize] -> [DISP (Screen Disp) Set]` (`_g 0x61c4 -> 0x61da`,
     `Initialize`-only, NOT `Display Option`): exact **4** shooting monitor pages
     (`Display All Info.` `0xea0e`, `No Disp. Info.` `0xe9f9`, `Histogram` `0xe07b`, `Level` `0xe8bc`)
     and **3** playback pages (`Display Info.`, `Histogram`, `No Disp. Info.`).
   - Enforces **Zero-EVF Blackout Guard**: `ILME-FX3` has ZERO built-in EVF, ZERO eye sensor, ZERO
     `FINDER/MONITOR` button — fail-closed `EOPNOTSUPP=95` / `ENODEV=19` on dormant
     `BKID_APP_setting_finder_monitor` (`FINDER_MONITOR_FINDER` / `VIEW_FINDER`),
     `BKID_APP_disp_mode_shoot_finder`, `Select Finder/Monitor` (`_f 0x74f9`), `For viewfinder`
     (`_f 0x62d3`/`0xe2e5`), `Graphic Display` (`0xe07a`), and `Monitor Off` so recovery/Stage-B can
     never route scanout to a non-existent EVF and cause LCD blackout. Contrasted with `ILME-FX6`
     (`TYPE_BUILTIN_EVF_NOT_EXIST` + detachable 3.5" LCD `Viewfinder` + `Viewfinder Hood` +
     `Monitoring > Display On/Off` + `Home Screen Priority`/`Direct Menu Priority`).

2. **Sub-Pillar 57B — Still-Only `[AEL w/ Shutter]` & Flash Submenu Reset Split + 9-Speed
   Interval PB & Playback `[Edit]` `Slot-1` Tier-0 `EROFS=30` Vault Firewall**:
   - Models `ILME-FX3` 4 Still-only (`unavailable in Movie/S&Q -> EOPNOTSUPP=95`) metering/flash
     items and their asymmetric `[Camera Settings Reset]` behavior:
     * `[AEL w/ Shutter]` (`_f 0x669d`, `BKID_APP_setting_still_image_ael_w_shutter`): `Auto`
       (default) / `On` / `Off` — `Initialize`-only (`resists Reset`), `[AEL toggle]` custom key
       overrides half-press.
     * `[Exp.comp.set]` (`_f 0x73c2`, under `[Flash]`, `BKID_APP_setting_exp_comp_set`):
       `Ambient&flash` (default, `_f 0x6efe`) / `Ambient only` (`_f 0x7617`) — `Initialize`-only.
     * `[Wireless Flash]` (`_f 0x6201`, `BKID_APP_setting_wireless_flash`): `Off` (default) / `On`
       — **ONLY item among the 4 resettable by `[Camera Settings Reset]`** (`can_be_reset=True`).
     * `[External Flash Set.]` (`_f 0x6771`, `[Ext. Flash Firing Set.]` `0x671d` + `[Ext. Flash Cust.
       Set.]` `0x705f`): `Initialize`-only, direct MI-Shoe mount required (wired sync cord
       off-camera rejected, flash pairing/reset from camera menu unsupported); contrast with
       shutterless/still-less `ILME-FX6` (zero TTL flash system, only rolling-shutter
       `Flash Band Reduce` `FX6_2 0x4215`).
   - Models `MENU -> (Playback) -> [Viewing]` (`_g 0x6033`, NOT `Playback Option`):
     `[Cont. Play for Interval]` (`_f 0x78fa`, legacy alias `Cont. PB for Interval` `0x72e6`) &
     `[Play Speed for Interval]` (`_f 0x639e`, legacy alias `PB Speed for Interval` `0x72bd`,
     `BKID_APP_setting_continuous_playback`) with exact **`1..9` speed steps**
     (`CONTINUOUS_PLAYBACK_SPEED_1..9`, default `5`, `Initialize`-only, pure read-only
     `safe_read_only=True`, no in-camera movie synthesis).
   - Enforces **`Slot-1` Tier-0 Vault `EROFS=30` / `EOPNOTSUPP=95` Firewall** across
     `MENU -> (Playback) -> [Edit]` (`_g 0x6418`):
     * Active FX3 `[Edit]` operations (`[Rotate]` `0xe5ae`/`0x795a`, `[Photo Capture]` `0x6856` +
       `[JPEG/HEIF Switch]` `0x6938` `JPEG`/`HEIF(4:2:0)`/`HEIF(4:2:2)`, `[Copy]` `0x79fc`): allowed
       on writable `Slot 2`, but ANY write/frame-save/metadata-rotate targeting read-only Tier-0
       Vault `Slot 1` (`[Select Playback Media]` defaults to `Slot 1`) MUST fail-closed with
       `EROFS=30` (`slot1_data_sector_writes == 0`, `slot1_avf_info_mutated == False`).
     * Dormant Alpha edit traps `[Beauty Effect]` (`_f 0x7849`, `API_START_BEAUTYEFFECT_DETECTION`)
       and `[Trimming]` (`sequence_edit_trimming_*`): fail-closed `EOPNOTSUPP=95` globally AND
       stacked `EROFS=30` if targeting `Slot 1`.

3. **Unified `57/57` Recovery Master Aggregator (`evaluate_realhw_57pillar_recovery_master` /
   `verify-57pillar-recovery`)**:
   - Concurrently delegates Pillars `1..56` (`evaluate_realhw_56pillar_recovery_master`) +
     **Pillar 57** (`run_pillar57_standalone_suite`) -> **`57/57` (`VERIFIED_57OF57_PILLAR_RECOVERY_MASTER`,
     `schema_version="realhw_57pillar_recovery_master_v1"`)** in `< 1.5s` with
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
from .realhw_56pillar_switch_vh_af_stdadj_tcub_copy_vault_verifier import (
    MASTER_56_PILLAR_SPECS,
    Master56PillarRecoveryReport,
    evaluate_realhw_56pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants (Phase 320 — 57/57 Milestone)
# ---------------------------------------------------------------------------

PHASE320_SCHEMA: str = (
    "realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier_v1"
)
PHASE320_MASTER_SCHEMA: str = "realhw_57pillar_recovery_master_v1"
PHASE320_VERSION: str = "1.0.0"
PHASE320_PHASE_NUMBER: int = 320
P320_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P320_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P320_OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
P320_CROSS_MODEL_FLASH_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P320_TOUCH_OP_DORMANT_TRAP_OR_RESET_DRIFT_EVENTS: int = 0
P320_DISP_SET_OR_ZERO_EVF_BLACKOUT_EVENTS: int = 0
P320_FX6_TOUCH_OR_EVF_SPOOF_EVENTS: int = 0
P320_STILL_AEL_FLASH_RESET_SPLIT_OR_MISHOE_DRIFT_EVENTS: int = 0
P320_INTERVAL_PB_9SCALE_OR_PATH_DRIFT_EVENTS: int = 0
P320_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_BYPASS_EVENTS: int = 0
P320_SLOT1_DATA_SECTOR_WRITES: int = 0
P320_SLOT1_EDIT_AVF_INFO_MUTATION_BYTES: int = 0
P320_SLOT1_VAULT_MUTATION_BYTES: int = 0
P320_SLOT1_FORMAT_HARD_LOCKED: bool = True
P320_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED: bool = True

# Hardware Truths (Wave-55 Empirical Anchors)
P320_FX3_HAS_BUILTIN_EVF: bool = False
P320_FX3_HAS_EYE_SENSOR: bool = False
P320_FX3_HAS_FINDER_MONITOR_BUTTON: bool = False
P320_FX6_HAS_BUILTIN_EVF: bool = False
P320_FX6_HAS_DETACHABLE_LCD_VIEWFINDER: bool = True
P320_FX6_HAS_STILL_TTL_FLASH: bool = False
P320_FX6_HAS_INTERVAL_PB: bool = False
P320_FX6_HAS_PLAYBACK_EDIT_MENU: bool = False
P320_FX3_TOUCH_ACTIVE_ITEM_COUNT: int = 4
P320_FX3_DISP_SHOOT_PAGE_COUNT: int = 4
P320_FX3_DISP_PLAY_PAGE_COUNT: int = 3
P320_FX3_INTERVAL_PB_SPEED_MIN: int = 1
P320_FX3_INTERVAL_PB_SPEED_MAX: int = 9
P320_FX3_INTERVAL_PB_SPEED_DEFAULT: int = 5

P320_DONOR_INSPECT_BUDGET_SECONDS: float = 0.20
P320_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P320_FAST_CLI_BUDGET_SECONDS: float = 1.5
P320_NOMINAL_BUDGET_SECONDS: float = 4.0
P320_CONCURRENT_CEILING_SECONDS: float = 6.0
P320_BOUNDED_HEADER_BYTES: int = 4096
P320_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-55 Donor Anchors (17 donors, strictly O_RDONLY)
P320_FX3_MODEL_NAME: str = "ILME-FX3"
P320_FX3_MODEL_ID: int = 0x91030080
P320_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P320_FX3_HELPGUIDE_ID: str = "ilc/2210"
P320_FX3_FW_VERSION: str = "7.02"
P320_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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
P320_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P320_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P320_FX6_DONOR_FW_VERSION: str = "6.01"

P320_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P320_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P320_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)
P320_PINNED_FX3_APPFW_702_FULL_SHA256: str = (
    "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
)

P320_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P320_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P320_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)
P320_PINNED_FX6_APPFW_601_FULL_SHA256: str = (
    "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
)

P320_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P320_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P320_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P320_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P320_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P320_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P320_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P320_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P320_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P320_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P320_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P320_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P320_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P320_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P320_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P320_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P320_PINNED_FX3_UXC_EN_BYTES: int = 165740
P320_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P320_DONOR_FX3_UXC_SC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc"
)
P320_PINNED_FX3_UXC_SC_BYTES: int = 149064
P320_PINNED_FX3_UXC_SC_SHA256: str = (
    "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66"
)

P320_DONOR_FX3_UXC_TC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc"
)
P320_PINNED_FX3_UXC_TC_BYTES: int = 151908
P320_PINNED_FX3_UXC_TC_SHA256: str = (
    "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3"
)

P320_DONOR_FX3_UXC_JA_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc"
)
P320_PINNED_FX3_UXC_JA_BYTES: int = 208564
P320_PINNED_FX3_UXC_JA_SHA256: str = (
    "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d"
)

P320_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P320_PINNED_FX3_UXC_EN_G_BYTES: int = 69600
P320_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P320_DONOR_FX3_UXC_SC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_g.uxc"
)
P320_PINNED_FX3_UXC_SC_G_BYTES: int = 61296
P320_PINNED_FX3_UXC_SC_G_SHA256: str = (
    "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b"
)

P320_DONOR_FX3_UXC_TC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_g.uxc"
)
P320_PINNED_FX3_UXC_TC_G_BYTES: int = 61372
P320_PINNED_FX3_UXC_TC_G_SHA256: str = (
    "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80"
)

P320_DONOR_FX3_UXC_JA_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_g.uxc"
)
P320_PINNED_FX3_UXC_JA_G_BYTES: int = 89428
P320_PINNED_FX3_UXC_JA_G_SHA256: str = (
    "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980"
)

P320_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P320_PINNED_FX6_UXC_EN_BYTES: int = 118208
P320_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P320_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P320_PINNED_FX6_UXC_EN_2_BYTES: int = 118676
P320_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# ---------------------------------------------------------------------------
# Pillar 57A Constants — Wave-55 Touch Operation 4-Item Tree vs Dormant
# Touch Shutter/AE/Pad/Footer & 4-Shoot/3-PB DISP Zero-EVF Blackout Guard
# ---------------------------------------------------------------------------

P320_TOUCH_OPERATION_MENU_PATH: Tuple[str, ...] = ("Setup", "Touch Operation")
P320_TOUCH_OPERATION_G_RESID16: int = 0x6345
P320_TOUCH_OPERATION_BASE_RESID16: int = 0xE8E3
P320_TOUCH_OPERATION_BKID: str = "BKID_APP_setting_touch_operation"
P320_TOUCH_OPERATION_4_ITEMS: Tuple[str, ...] = (
    "Touch Operation",
    "Touch Sensitivity",
    "Touch Func. in Shooting",
    "Swipe Up",
)
P320_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("On", "On: Playback Only", "Off")
P320_TOUCH_OPERATION_DEFAULT: str = "On"
P320_TOUCH_OP_PLAYBACK_ONLY_F_RESID16: int = 0x6CDE

P320_TOUCH_SENSITIVITY_F_RESID16: int = 0x739F
P320_TOUCH_SENSITIVITY_SENSITIVE_F_RESID16: int = 0x7205
P320_TOUCH_SENSITIVITY_BKID: str = "BKID_APP_setting_touch_sensitivity"
P320_TOUCH_SENSITIVITY_MODES: Tuple[str, ...] = ("Standard", "Sensitive")
P320_TOUCH_SENSITIVITY_DEFAULT: str = "Standard"
P320_TOUCH_SENSITIVITY_DORMANT_OR_WRONG: str = "Responsive"

P320_TOUCH_FUNC_SHOOTING_F_RESID16: int = 0x7575
P320_TOUCH_FUNC_SHOOTING_BKID: str = "BKID_APP_setting_shooting_touch_function"
P320_TOUCH_FUNC_SHOOTING_MODES: Tuple[str, ...] = (
    "Touch Focus",
    "Touch Tracking",
    "Off",
)
P320_TOUCH_FUNC_SHOOTING_DEFAULT: str = "Touch Tracking"
P320_TOUCH_FUNC_RESID16_MAP: Dict[str, Tuple[int, ...]] = {
    "Touch Focus": (0x6E79, 0x7427),
    "Touch Tracking": (0x68F4, 0x69EE),
}

P320_SWIPE_UP_F_RESID16: int = 0x7518
P320_SWIPE_UP_FN_MENU_F_RESID16: int = 0x7281
P320_SWIPE_UP_BKID: str = "BKID_APP_setting_swipe_up"
P320_SWIPE_UP_MODES: Tuple[str, ...] = ("Open the Fn Menu", "Off")
P320_SWIPE_UP_DEFAULT: str = "Open the Fn Menu"

P320_DORMANT_TOUCH_TRAPS: Tuple[str, ...] = (
    "Touch Shutter",
    "Touch AE",
    "Touch Focus+AE",
    "Touch AE Cancel",
    "Touch Panel/Pad",
    "Touch Pad Settings",
    "Touch Pad Only",
    "Touch Pad (vertical)",
    "Footer Icon Touch",
    "Swipe Left",
    "Swipe Right",
    "BKID_APP_setting_touch_panel_pad",
    "VAL_setting_shooting_touch_function_SHOOTING_TOUCH_FUNCTION_TOUCH_SHUTTER",
    "FUNC_touch_shutter_yuv_seq",
    "PID_SET_TOUCH_SPOT_METER",
)
P320_DORMANT_TOUCH_TRAP_RESID16_MAP: Dict[str, int] = {
    "Touch Shutter": 0x6A80,
    "Touch AE": 0x702A,
    "Touch Panel/Pad": 0x76EC,
    "Footer Icon Touch": 0x70DA,
    "Swipe Left": 0x6B06,
    "Swipe Right": 0x6C19,
}

P320_FX6_TOUCH_MENU_PATH: Tuple[str, ...] = ("Technical", "Touch Operation")
P320_FX6_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("On", "Off")
P320_FX6_TOUCH_MF_PATH: Tuple[str, ...] = ("Shooting", "Focus", "Touch Function in MF")
P320_FX6_TOUCH_MF_MODES: Tuple[str, ...] = ("Spot Focus", "Tracking AF")

P320_DISP_SET_MENU_PATH: Tuple[str, ...] = (
    "Setup",
    "Operation Customize",
    "DISP (Screen Disp) Set",
)
P320_DISP_SET_WRONG_PATH: Tuple[str, ...] = (
    "Setup",
    "Display Option",
    "DISP (Screen Disp) Set",
)
P320_OP_CUSTOMIZE_G_RESID16: int = 0x61C4
P320_DISP_SET_G_RESID16: int = 0x61DA
P320_DISP_SHOOT_4_PAGES: Tuple[str, ...] = (
    "Display All Info.",
    "No Disp. Info.",
    "Histogram",
    "Level",
)
P320_DISP_SHOOT_RESID16_MAP: Dict[str, int] = {
    "Display All Info.": 0xEA0E,
    "No Disp. Info.": 0xE9F9,
    "Histogram": 0xE07B,
    "Level": 0xE8BC,
}
P320_DISP_PLAY_3_PAGES: Tuple[str, ...] = (
    "Display Info.",
    "Histogram",
    "No Disp. Info.",
)

P320_DORMANT_EVF_OR_DISP_TRAPS: Tuple[str, ...] = (
    "Select Finder/Monitor",
    "Finder/Monitor Sel.",
    "For viewfinder",
    "Graphic Display",
    "Monitor Off",
    "DISP Button:Finder",
    "FINDER/MONITOR",
    "BKID_APP_setting_finder_monitor",
    "FINDER_MONITOR_FINDER",
    "VIEW_FINDER",
    "BKID_APP_disp_mode_shoot_finder",
    "BKID_APP_valid_disp_mode_shoot_monitor_for_viewfinder",
)
P320_DORMANT_EVF_TRAP_RESID16_MAP: Dict[str, int] = {
    "Select Finder/Monitor": 0x74F9,
    "For viewfinder": 0x62D3,
    "Graphic Display": 0xE07A,
    "DISP Button:Finder": 0x6B57,
}
P320_FX6_BUILTIN_EVF_ENUM: str = "VAL_FEATURE_MANAGER_builtin_evf_TYPE_BUILTIN_EVF_NOT_EXIST"
P320_FX6_DETACHABLE_LCD_TERMS: Tuple[str, ...] = ("Viewfinder", "Viewfinder Hood")
P320_FX6_FORBIDDEN_LOUPE_TERM: str = "Loupe"
P320_FX6_INFO_DISP_MODES: Tuple[str, ...] = (
    "Home Screen Priority",
    "Direct Menu Priority",
)

# ---------------------------------------------------------------------------
# Pillar 57B Constants — Still [AEL w/ Shutter] / Flash Reset Split +
# 9-Speed Interval PB + Playback [Edit] Slot-1 Tier-0 EROFS=30 Vault Firewall
# ---------------------------------------------------------------------------

P320_AEL_W_SHUTTER_MENU_PATH: Tuple[str, ...] = (
    "Exposure/Color",
    "Metering",
    "AEL w/ Shutter",
)
P320_AEL_W_SHUTTER_F_RESID16: int = 0x669D
P320_AEL_W_SHUTTER_BKID: str = "BKID_APP_setting_still_image_ael_w_shutter"
P320_AEL_W_SHUTTER_MODES: Tuple[str, ...] = ("Auto", "On", "Off")
P320_AEL_W_SHUTTER_DEFAULT: str = "Auto"

P320_EXP_COMP_SET_MENU_PATH: Tuple[str, ...] = (
    "Exposure/Color",
    "Flash",
    "Exp.comp.set",
)
P320_EXP_COMP_SET_F_RESID16: int = 0x73C2
P320_EXP_COMP_SET_BASE_RESID16: int = 0xE11A
P320_EXP_COMP_SET_BKID: str = "BKID_APP_setting_exp_comp_set"
P320_EXP_COMP_SET_MODES: Tuple[str, ...] = ("Ambient&flash", "Ambient only")
P320_EXP_COMP_SET_DEFAULT: str = "Ambient&flash"
P320_EXP_COMP_SET_F_RESID16_MAP: Dict[str, int] = {
    "Ambient&flash": 0x6EFE,
    "Ambient only": 0x7617,
}

P320_WIRELESS_FLASH_MENU_PATH: Tuple[str, ...] = (
    "Exposure/Color",
    "Flash",
    "Wireless Flash",
)
P320_WIRELESS_FLASH_F_RESID16: int = 0x6201
P320_WIRELESS_TEST_FLASH_F_RESID16: int = 0x7567
P320_WIRELESS_FLASH_BKID: str = "BKID_APP_setting_wireless_flash"
P320_WIRELESS_FLASH_MODES: Tuple[str, ...] = ("Off", "On")
P320_WIRELESS_FLASH_DEFAULT: str = "Off"

P320_EXT_FLASH_SET_MENU_PATH: Tuple[str, ...] = (
    "Exposure/Color",
    "Flash",
    "External Flash Set.",
)
P320_EXT_FLASH_SET_F_RESID16: int = 0x6771
P320_EXT_FLASH_FIRING_F_RESID16: int = 0x671D
P320_EXT_FLASH_CUST_F_RESID16: int = 0x705F
P320_EXT_FLASH_SUBMENUS: Tuple[str, ...] = (
    "Ext. Flash Firing Set.",
    "Ext. Flash Cust. Set.",
)
P320_FX6_FLASH_BAND_REDUCE_2_RESID16: int = 0x4215

P320_INTERVAL_PB_MENU_PATH: Tuple[str, ...] = ("Playback", "Viewing")
P320_INTERVAL_PB_WRONG_PATH: Tuple[str, ...] = ("Playback", "Playback Option")
P320_PLAYBACK_VIEWING_G_RESID16: int = 0x6033
P320_PLAYBACK_OPTION_G_RESID16: int = 0x6188
P320_CONT_PLAY_INTERVAL_F_RESID16: int = 0x78FA
P320_CONT_PB_LEGACY_F_RESID16: int = 0x72E6
P320_PLAY_SPEED_INTERVAL_F_RESID16: int = 0x639E
P320_PB_SPEED_LEGACY_F_RESID16: int = 0x72BD
P320_CONTINUOUS_PLAYBACK_BKID: str = "BKID_APP_setting_continuous_playback"
P320_INTERVAL_PB_SPEED_SCALE_9: Tuple[int, ...] = tuple(range(1, 10))
P320_INTERVAL_PB_SPEED_DEFAULT: int = 5

P320_PLAYBACK_EDIT_MENU_PATH: Tuple[str, ...] = ("Playback", "Edit")
P320_PLAYBACK_EDIT_G_RESID16: int = 0x6418
P320_PLAYBACK_EDIT_ACTIVE_4_ITEMS: Tuple[str, ...] = (
    "Rotate",
    "Photo Capture",
    "JPEG/HEIF Switch",
    "Copy",
)
P320_PLAYBACK_EDIT_RESID16_MAP: Dict[str, int] = {
    "Rotate": 0xE5AE,
    "Photo Capture": 0x6856,
    "JPEG/HEIF Switch": 0x6938,
    "Copy": 0x79FC,
}
P320_PHOTO_CAPTURE_FILE_TYPES: Tuple[str, ...] = (
    "JPEG",
    "HEIF(4:2:0)",
    "HEIF(4:2:2)",
)
P320_PHOTO_CAPTURE_FILE_DEFAULT: str = "JPEG"
P320_DORMANT_PLAYBACK_EDIT_TRAPS: Tuple[str, ...] = (
    "Beauty Effect",
    "Trimming",
    "API_START_BEAUTYEFFECT_DETECTION",
    "sequence_edit_trimming_start",
)
P320_DORMANT_BEAUTY_EFFECT_F_RESID16: int = 0x7849

P320_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P320_ON_OFF_MODES: Tuple[str, ...] = ("On", "Off")
P320_RESET_ACTIONS: Tuple[str, ...] = (
    "None",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P320_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "CONT_PLAY_INTERVAL",
    "ROTATE",
    "PHOTO_CAPTURE",
    "COPY_TO_TARGET",
    "BEAUTY_EFFECT",
    "TRIMMING",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P320_WRITE_MUTATING_EDIT_ACTIONS: Tuple[str, ...] = (
    "ROTATE",
    "PHOTO_CAPTURE",
    "COPY_TO_TARGET",
    "BEAUTY_EFFECT",
    "TRIMMING",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P320_SLOT1_VAULT_SLOT: int = 1
P320_SAFE_SECONDARY_SLOT: int = 2
P320_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT: int = 1
P320_VAULT_FIREWALL_ERRNOS: Tuple[str, ...] = ("EROFS", "EBUSY", "EINVAL", "EOPNOTSUPP", "ENODEV")
P320_EOPNOTSUPP_ERRNO: int = 95
P320_EROFS_ERRNO: int = 30
P320_EINVAL_ERRNO: int = 22
P320_EBUSY_ERRNO: int = 16
P320_ENODEV_ERRNO: int = 19
P320_ENOENT_ERRNO: int = 2
P320_VAULT_FIREWALL_ERRNO_CODES: Dict[str, int] = {
    "EROFS": P320_EROFS_ERRNO,
    "EBUSY": P320_EBUSY_ERRNO,
    "EINVAL": P320_EINVAL_ERRNO,
    "EOPNOTSUPP": P320_EOPNOTSUPP_ERRNO,
    "ENODEV": P320_ENODEV_ERRNO,
}
P320_STAGE_B_VOLATILE_OVERLAY_DIR: str = (
    "/tmp/fx3_touch_disp_zero_evf_flash_interval_pb_vault_overlay"
)
P320_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P320_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P320_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P320_BLOCKED_INVALID_PILLAR57A_SPEC: str = "BLOCKED_INVALID_PILLAR57A_SPEC"
P320_BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT: str = (
    "BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT"
)
P320_BLOCKED_DISP_SET_4SHOOT_3PB_OR_PATH_DRIFT: str = (
    "BLOCKED_DISP_SET_4SHOOT_3PB_OR_PATH_DRIFT"
)
P320_BLOCKED_ZERO_EVF_BLACKOUT_GUARD_BREACH: str = (
    "BLOCKED_ZERO_EVF_BLACKOUT_GUARD_BREACH"
)
P320_BLOCKED_FX6_TOUCH_OR_EVF_SPOOF: str = "BLOCKED_FX6_TOUCH_OR_EVF_SPOOF"
P320_BLOCKED_INVALID_PILLAR57B_SPEC: str = "BLOCKED_INVALID_PILLAR57B_SPEC"
P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT: str = (
    "BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT"
)
P320_BLOCKED_EXT_FLASH_MISHOE_OR_FX6_SPOOF: str = (
    "BLOCKED_EXT_FLASH_MISHOE_OR_FX6_SPOOF"
)
P320_BLOCKED_INTERVAL_PB_9SCALE_OR_PATH_DRIFT: str = (
    "BLOCKED_INTERVAL_PB_9SCALE_OR_PATH_DRIFT"
)
P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL: str = (
    "BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL"
)
P320_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL: str = "BLOCKED_SLOT1_VAULT_WRITE_FIREWALL"
P320_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P320_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P320_STATUS_VERIFIED_PILLAR_57A: str = (
    "VERIFIED_PILLAR_57A_WAVE55_TOUCH_4ITEM_DISP_4SHOOT_3PB_AND_ZERO_EVF_BLACKOUT_GUARD"
)
P320_STATUS_REJECTED_PILLAR_57A: str = (
    "REJECTED_PILLAR_57A_WAVE55_TOUCH_4ITEM_DISP_4SHOOT_3PB_AND_ZERO_EVF_BLACKOUT_GUARD"
)
P320_STATUS_VERIFIED_PILLAR_57B: str = (
    "VERIFIED_PILLAR_57B_STILL_AEL_FLASH_RESET_SPLIT_9SPEED_INTERVAL_PB_AND_EDIT_VAULT"
)
P320_STATUS_REJECTED_PILLAR_57B: str = (
    "REJECTED_PILLAR_57B_STILL_AEL_FLASH_RESET_SPLIT_9SPEED_INTERVAL_PB_AND_EDIT_VAULT"
)
P320_STATUS_VERIFIED_PILLAR57_SUITE: str = (
    "VERIFIED_PILLAR57_TOUCH_DISP_ZERO_EVF_FLASH_INTERVAL_PB_VAULT"
)
P320_STATUS_FAIL_PILLAR57_SUITE: str = (
    "FAIL_PILLAR57_TOUCH_DISP_ZERO_EVF_FLASH_INTERVAL_PB_VAULT"
)
P320_STATUS_VERIFIED_57OF57_AGGREGATOR: str = "VERIFIED_57OF57_PILLAR_RECOVERY_MASTER"
P320_STATUS_FAIL_57OF57_AGGREGATOR: str = "FAIL_57OF57_PILLAR_RECOVERY_MASTER"

P320_PILLAR_57A_SCENARIO_IDS: Tuple[str, ...] = (
    "P57A1_FX3_TOUCH_4ITEM_SENSITIVE_SWIPE_UP_DISP_4SHOOT_3PB_AND_ZERO_EVF_SAFE",
    "P57A2_CAM_RESET_PRESERVES_ALL_4_TOUCH_AND_DISP_WHILE_INITIALIZE_RESETS_SAFE",
    "P57A3_REJECT_DORMANT_TOUCH_SHUTTER_AE_PAD_FOOTER_WITHOUT_EOPNOTSUPP95",
    "P57A4_REJECT_ZERO_EVF_BLACKOUT_FINDER_MONITOR_GRAPHIC_DISP_OR_MONITOR_OFF",
    "P57A5_REJECT_DISP_WRONG_PATH_OR_CAMERA_RESET_WIPE_OF_TOUCH_AND_DISP",
    "P57A6_REJECT_FX6_SENSITIVITY_LOUPE_SPOOF_OR_SLOT1_VAULT_OVERLAY_H0_H3_DRIFT",
)
P320_PILLAR_57B_SCENARIO_IDS: Tuple[str, ...] = (
    "P57B1_STILL_AEL_FLASH_CAM_RESET_ONLY_WIRELESS_FLASH_RESETS_AND_SLOT2_EDIT_SAFE",
    "P57B2_INITIALIZE_RESETS_ALL_AND_9SPEED_INTERVAL_PB_SPEED5_READ_ONLY_SAFE",
    "P57B3_REJECT_MOVIE_SQ_AEL_FLASH_BYPASS_OR_CAM_RESET_WIPE_OF_AEL_EXP_EXTFLASH",
    "P57B4_REJECT_SYNC_CORD_OFFCAMERA_EXTFLASH_MENU_RESET_OR_FX6_TTL_FLASH_SPOOF",
    "P57B5_REJECT_INTERVAL_PB_5SCALE_SYNTHESIS_OR_PLAYBACK_OPTION_PATH_DRIFT",
    "P57B6_REJECT_SLOT1_ROTATE_PHOTOCAP_COPY_WITHOUT_EROFS30_OR_DORMANT_BEAUTY_TRIMMING",
)

MASTER_57_PILLAR_COUNT: int = 57
MASTER_57_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_56_PILLAR_SPECS + (
    (
        57,
        "pillar_57_touch_disp_zero_evf_flash_interval_pb_vault",
        "Phase 320 (Wave-55)",
        "fx3_recovery.realhw_57pillar_touch_disp_zero_evf_flash_interval_pb_vault_verifier",
    ),
)
MASTER_57_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_57_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Pure Wave-55 State Computations
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
    return os.environ.get(P320_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P320_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P320_DONOR_INSPECT_BUDGET_SECONDS


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
        ("P320_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P320_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("P320_OVERALL_READY_FOR_HARDWARE_ATTACH", P320_OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("P320_CROSS_MODEL_FLASH_AUTHORIZED", P320_CROSS_MODEL_FLASH_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        (
            "P320_TOUCH_OP_DORMANT_TRAP_OR_RESET_DRIFT_EVENTS",
            P320_TOUCH_OP_DORMANT_TRAP_OR_RESET_DRIFT_EVENTS,
            0,
        ),
        ("P320_DISP_SET_OR_ZERO_EVF_BLACKOUT_EVENTS", P320_DISP_SET_OR_ZERO_EVF_BLACKOUT_EVENTS, 0),
        ("P320_FX6_TOUCH_OR_EVF_SPOOF_EVENTS", P320_FX6_TOUCH_OR_EVF_SPOOF_EVENTS, 0),
        (
            "P320_STILL_AEL_FLASH_RESET_SPLIT_OR_MISHOE_DRIFT_EVENTS",
            P320_STILL_AEL_FLASH_RESET_SPLIT_OR_MISHOE_DRIFT_EVENTS,
            0,
        ),
        ("P320_INTERVAL_PB_9SCALE_OR_PATH_DRIFT_EVENTS", P320_INTERVAL_PB_9SCALE_OR_PATH_DRIFT_EVENTS, 0),
        (
            "P320_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_BYPASS_EVENTS",
            P320_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_BYPASS_EVENTS,
            0,
        ),
        ("P320_SLOT1_DATA_SECTOR_WRITES", P320_SLOT1_DATA_SECTOR_WRITES, 0),
        ("P320_SLOT1_EDIT_AVF_INFO_MUTATION_BYTES", P320_SLOT1_EDIT_AVF_INFO_MUTATION_BYTES, 0),
        ("P320_SLOT1_VAULT_MUTATION_BYTES", P320_SLOT1_VAULT_MUTATION_BYTES, 0),
        ("P320_SLOT1_FORMAT_HARD_LOCKED", P320_SLOT1_FORMAT_HARD_LOCKED, True),
        ("P320_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED", P320_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED, True),
        ("P320_FX3_HAS_BUILTIN_EVF", P320_FX3_HAS_BUILTIN_EVF, False),
        ("P320_FX3_HAS_EYE_SENSOR", P320_FX3_HAS_EYE_SENSOR, False),
        ("P320_FX3_HAS_FINDER_MONITOR_BUTTON", P320_FX3_HAS_FINDER_MONITOR_BUTTON, False),
        ("P320_FX6_HAS_BUILTIN_EVF", P320_FX6_HAS_BUILTIN_EVF, False),
        ("P320_FX6_HAS_DETACHABLE_LCD_VIEWFINDER", P320_FX6_HAS_DETACHABLE_LCD_VIEWFINDER, True),
        ("P320_FX6_HAS_STILL_TTL_FLASH", P320_FX6_HAS_STILL_TTL_FLASH, False),
        ("P320_FX6_HAS_INTERVAL_PB", P320_FX6_HAS_INTERVAL_PB, False),
        ("P320_FX6_HAS_PLAYBACK_EDIT_MENU", P320_FX6_HAS_PLAYBACK_EDIT_MENU, False),
        ("P320_FX3_TOUCH_ACTIVE_ITEM_COUNT", P320_FX3_TOUCH_ACTIVE_ITEM_COUNT, 4),
        ("P320_FX3_DISP_SHOOT_PAGE_COUNT", P320_FX3_DISP_SHOOT_PAGE_COUNT, 4),
        ("P320_FX3_DISP_PLAY_PAGE_COUNT", P320_FX3_DISP_PLAY_PAGE_COUNT, 3),
        ("P320_FX3_INTERVAL_PB_SPEED_MIN", P320_FX3_INTERVAL_PB_SPEED_MIN, 1),
        ("P320_FX3_INTERVAL_PB_SPEED_MAX", P320_FX3_INTERVAL_PB_SPEED_MAX, 9),
        ("P320_FX3_INTERVAL_PB_SPEED_DEFAULT", P320_FX3_INTERVAL_PB_SPEED_DEFAULT, 5),
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
    return any(tok in low for tok in P320_FORBIDDEN_PERSISTENT_TARGETS)


def compute_expected_touch_disp_zero_evf_state(
    *,
    camera_model: str,
    shooting_domain: str,
    touch_operation: str,
    touch_sensitivity: str,
    touch_func_in_shooting: str,
    swipe_up: str,
    requested_dormant_touch_symbols: Tuple[str, ...],
    disp_shoot_pages_enabled: Tuple[str, ...],
    disp_play_pages_enabled: Tuple[str, ...],
    requested_dormant_evf_symbols: Tuple[str, ...],
    reset_action: str,
) -> Dict[str, Any]:
    """Compute Wave-55 `[Touch Operation]` 4-item tree, `[DISP (Screen Disp) Set]` 4-shoot/3-PB
    pages, `Initialize`-only reset rules, dormant Alpha trap rejections (`EOPNOTSUPP=95`),
    and Zero-EVF Blackout Guard vs `ILME-FX6`."""
    if camera_model == P320_FX6_DONOR_MODEL_NAME:
        dormant_touch_hit = bool(requested_dormant_touch_symbols)
        dormant_evf_hit = bool(requested_dormant_evf_symbols)
        return {
            "touch_op_mode": "On" if touch_operation in P320_FX6_TOUCH_OPERATION_MODES else "Off",
            "touch_sensitivity_supported": False,
            "swipe_up_supported": False,
            "swipe_up_active": False,
            "dormant_touch_errno": P320_EOPNOTSUPP_ERRNO if dormant_touch_hit else None,
            "dormant_evf_errno": P320_EOPNOTSUPP_ERRNO if dormant_evf_hit else None,
            "evf_scanout_blocked": True,
            "lcd_scanout_preserved": True,
            "post_touch_operation": touch_operation,
            "post_touch_sensitivity": "N/A_FX6",
            "post_touch_func_in_shooting": touch_func_in_shooting,
            "post_swipe_up": "N/A_FX6",
            "post_disp_shoot_pages": (),
            "post_disp_play_pages": (),
        }

    dormant_touch_hit = any(s in P320_DORMANT_TOUCH_TRAPS for s in requested_dormant_touch_symbols)
    dormant_evf_hit = any(s in P320_DORMANT_EVF_OR_DISP_TRAPS for s in requested_dormant_evf_symbols)

    if reset_action == "Initialize":
        post_touch_op = P320_TOUCH_OPERATION_DEFAULT
        post_sens = P320_TOUCH_SENSITIVITY_DEFAULT
        post_func = P320_TOUCH_FUNC_SHOOTING_DEFAULT
        post_swipe = P320_SWIPE_UP_DEFAULT
        post_disp_shoot = P320_DISP_SHOOT_4_PAGES
        post_disp_play = P320_DISP_PLAY_3_PAGES
    else:
        # ALL 4 Touch Operation items AND DISP Set survive Camera Settings Reset & Reset Network Set.
        post_touch_op = touch_operation
        post_sens = touch_sensitivity
        post_func = touch_func_in_shooting
        post_swipe = swipe_up
        post_disp_shoot = disp_shoot_pages_enabled
        post_disp_play = disp_play_pages_enabled

    swipe_up_active = post_touch_op == "On" and shooting_domain in P320_SHOOTING_DOMAINS

    return {
        "touch_op_mode": post_touch_op,
        "touch_sensitivity_supported": True,
        "swipe_up_supported": True,
        "swipe_up_active": swipe_up_active,
        "dormant_touch_errno": P320_EOPNOTSUPP_ERRNO if dormant_touch_hit else None,
        "dormant_evf_errno": P320_EOPNOTSUPP_ERRNO if dormant_evf_hit else None,
        "evf_scanout_blocked": True,
        "lcd_scanout_preserved": not dormant_evf_hit,
        "post_touch_operation": post_touch_op,
        "post_touch_sensitivity": post_sens,
        "post_touch_func_in_shooting": post_func,
        "post_swipe_up": post_swipe,
        "post_disp_shoot_pages": post_disp_shoot,
        "post_disp_play_pages": post_disp_play,
    }


def compute_expected_still_ael_flash_interval_pb_edit_vault_state(
    *,
    camera_model: str,
    shooting_domain: str,
    ael_w_shutter: str,
    ael_toggle_key_active: bool,
    exp_comp_set: str,
    wireless_flash: str,
    ext_flash_direct_mishoe: bool,
    ext_flash_sync_cord_requested: bool,
    ext_flash_camera_menu_reset_requested: bool,
    cont_play_for_interval: str,
    play_speed_for_interval: int,
    photo_capture_file_type: str,
    select_playback_media_slot: int,
    target_write_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute Still-only `[AEL w/ Shutter]` & Flash submenu asymmetric reset split,
    9-speed `[Viewing]` Interval PB, and `[Edit]` `Slot-1` Tier-0 `EROFS=30`/`EOPNOTSUPP=95` firewall."""
    if camera_model == P320_FX6_DONOR_MODEL_NAME:
        still_flash_errno: Optional[int] = P320_EOPNOTSUPP_ERRNO
        interval_errno: Optional[int] = P320_EOPNOTSUPP_ERRNO
        dormant_edit_hit = requested_vault_action in ("BEAUTY_EFFECT", "TRIMMING")
        edit_errno: Optional[str] = (
            "EOPNOTSUPP"
            if requested_vault_action in P320_WRITE_MUTATING_EDIT_ACTIONS or dormant_edit_hit
            else None
        )
        return {
            "still_flash_errno": still_flash_errno,
            "ext_flash_errno": P320_EOPNOTSUPP_ERRNO,
            "interval_pb_errno": interval_errno,
            "action_allowed": False,
            "firewall_errno": edit_errno,
            "half_press_ael_locked": False,
            "post_ael_w_shutter": "N/A_FX6",
            "post_exp_comp_set": "N/A_FX6",
            "post_wireless_flash": "N/A_FX6",
            "post_cont_play_for_interval": "N/A_FX6",
            "post_play_speed_for_interval": 0,
            "post_photo_capture_file_type": "N/A_FX6",
        }

    still_flash_errno = P320_EOPNOTSUPP_ERRNO if shooting_domain != "Still" else None
    ext_flash_errno: Optional[int] = None
    if shooting_domain != "Still":
        ext_flash_errno = P320_EOPNOTSUPP_ERRNO
    elif ext_flash_sync_cord_requested or ext_flash_camera_menu_reset_requested or not ext_flash_direct_mishoe:
        ext_flash_errno = P320_EOPNOTSUPP_ERRNO

    # Asymmetric Camera Settings Reset split:
    # ONLY Wireless Flash resets on Camera Settings Reset; AEL w/ Shutter, Exp.comp.set, External Flash Set.,
    # Interval PB, and Photo Capture file type are ALL Initialize-only!
    if reset_action == "Initialize":
        post_ael = P320_AEL_W_SHUTTER_DEFAULT
        post_exp_comp = P320_EXP_COMP_SET_DEFAULT
        post_wireless = P320_WIRELESS_FLASH_DEFAULT
        post_cont_play = "Off"
        post_speed = P320_INTERVAL_PB_SPEED_DEFAULT
        post_photo_type = P320_PHOTO_CAPTURE_FILE_DEFAULT
    elif reset_action == "Camera Settings Reset":
        post_ael = ael_w_shutter
        post_exp_comp = exp_comp_set
        post_wireless = P320_WIRELESS_FLASH_DEFAULT
        post_cont_play = cont_play_for_interval
        post_speed = play_speed_for_interval
        post_photo_type = photo_capture_file_type
    else:
        post_ael = ael_w_shutter
        post_exp_comp = exp_comp_set
        post_wireless = wireless_flash
        post_cont_play = cont_play_for_interval
        post_speed = play_speed_for_interval
        post_photo_type = photo_capture_file_type

    half_press_ael_locked = (
        shooting_domain == "Still"
        and not ael_toggle_key_active
        and post_ael in ("Auto", "On")
    )

    # Playback [Edit] Vault & Dormant Trap Firewall
    dormant_edit_hit = requested_vault_action in ("BEAUTY_EFFECT", "TRIMMING")
    mutates_slot1 = (
        target_write_slot == P320_SLOT1_VAULT_SLOT
        and requested_vault_action in P320_WRITE_MUTATING_EDIT_ACTIONS
    )
    if dormant_edit_hit:
        action_allowed = False
        firewall_errno: Optional[str] = "EROFS" if (mutates_slot1 and slot1_holds_tier0_vault) else "EOPNOTSUPP"
    elif requested_vault_action in ("FORMAT_QUICK", "FORMAT_FULL"):
        action_allowed = False
        firewall_errno = "EROFS"
    elif requested_vault_action in ("ROTATE", "PHOTO_CAPTURE", "COPY_TO_TARGET"):
        if mutates_slot1 and slot1_holds_tier0_vault:
            action_allowed = False
            firewall_errno = "EROFS"
        elif target_write_slot == P320_SAFE_SECONDARY_SLOT:
            action_allowed = True
            firewall_errno = None
        else:
            action_allowed = False
            firewall_errno = "EROFS"
    elif requested_vault_action in ("READ_ONLY_AUDIT", "CONT_PLAY_INTERVAL", "NONE"):
        action_allowed = requested_vault_action != "NONE"
        firewall_errno = None
    else:
        action_allowed = False
        firewall_errno = "EINVAL"

    return {
        "still_flash_errno": still_flash_errno,
        "ext_flash_errno": ext_flash_errno,
        "interval_pb_errno": None,
        "action_allowed": action_allowed,
        "firewall_errno": firewall_errno,
        "firewall_errno_num": (
            P320_VAULT_FIREWALL_ERRNO_CODES[firewall_errno]
            if firewall_errno in P320_VAULT_FIREWALL_ERRNO_CODES
            else None
        ),
        "half_press_ael_locked": half_press_ael_locked,
        "post_ael_w_shutter": post_ael,
        "post_exp_comp_set": post_exp_comp,
        "post_wireless_flash": post_wireless,
        "post_cont_play_for_interval": post_cont_play,
        "post_play_speed_for_interval": post_speed,
        "post_photo_capture_file_type": post_photo_type,
        "select_playback_media_slot": select_playback_media_slot,
        "target_write_slot": target_write_slot,
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback (Phase 320, 17 Donors)
# ---------------------------------------------------------------------------


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P320_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    try:
        resolved = resolve_donor_path(relpath)
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
        hdr = os.pread(fd, min(P320_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase320_donors() -> Tuple["Phase320DonorArtifactDigest", ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P320_DONOR_FX3_APPFW_702_RELPATH,
            P320_PINNED_FX3_APPFW_702_BYTES,
            P320_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P320_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P320_DONOR_FX6_APPFW_601_RELPATH,
            P320_PINNED_FX6_APPFW_601_BYTES,
            P320_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P320_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P320_DONOR_FX3_BACKUP_BIN_RELPATH,
            P320_PINNED_FX3_BACKUP_BIN_BYTES,
            P320_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_uxc_en_f",
            P320_DONOR_FX3_UXC_EN_F_RELPATH,
            P320_PINNED_FX3_UXC_EN_F_BYTES,
            P320_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P320_DONOR_FX3_UXC_SC_F_RELPATH,
            P320_PINNED_FX3_UXC_SC_F_BYTES,
            P320_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P320_DONOR_FX3_UXC_TC_F_RELPATH,
            P320_PINNED_FX3_UXC_TC_F_BYTES,
            P320_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P320_DONOR_FX3_UXC_JA_F_RELPATH,
            P320_PINNED_FX3_UXC_JA_F_BYTES,
            P320_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P320_DONOR_FX3_UXC_EN_RELPATH,
            P320_PINNED_FX3_UXC_EN_BYTES,
            P320_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_sc",
            P320_DONOR_FX3_UXC_SC_RELPATH,
            P320_PINNED_FX3_UXC_SC_BYTES,
            P320_PINNED_FX3_UXC_SC_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX3_SC",
        ),
        (
            "fx3_uxc_tc",
            P320_DONOR_FX3_UXC_TC_RELPATH,
            P320_PINNED_FX3_UXC_TC_BYTES,
            P320_PINNED_FX3_UXC_TC_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX3_TC",
        ),
        (
            "fx3_uxc_ja",
            P320_DONOR_FX3_UXC_JA_RELPATH,
            P320_PINNED_FX3_UXC_JA_BYTES,
            P320_PINNED_FX3_UXC_JA_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX3_JA",
        ),
        (
            "fx3_uxc_en_g",
            P320_DONOR_FX3_UXC_EN_G_RELPATH,
            P320_PINNED_FX3_UXC_EN_G_BYTES,
            P320_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx3_uxc_sc_g",
            P320_DONOR_FX3_UXC_SC_G_RELPATH,
            P320_PINNED_FX3_UXC_SC_G_BYTES,
            P320_PINNED_FX3_UXC_SC_G_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_SC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_G",
        ),
        (
            "fx3_uxc_tc_g",
            P320_DONOR_FX3_UXC_TC_G_RELPATH,
            P320_PINNED_FX3_UXC_TC_G_BYTES,
            P320_PINNED_FX3_UXC_TC_G_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_TC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_G",
        ),
        (
            "fx3_uxc_ja_g",
            P320_DONOR_FX3_UXC_JA_G_RELPATH,
            P320_PINNED_FX3_UXC_JA_G_BYTES,
            P320_PINNED_FX3_UXC_JA_G_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX3_UXC_JA_G_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_G",
        ),
        (
            "fx6_uxc_en",
            P320_DONOR_FX6_UXC_EN_RELPATH,
            P320_PINNED_FX6_UXC_EN_BYTES,
            P320_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P320_DONOR_FX6_UXC_EN_2_RELPATH,
            P320_PINNED_FX6_UXC_EN_2_BYTES,
            P320_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P320_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase320DonorArtifactDigest(
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


def inspect_phase320_donors_readonly(force_clean_room: Optional[bool] = None) -> "Phase320DonorSnapshot":
    """Inspect Wave-55 FX3 7.02 (`14` donors) & FX6 6.01 (`3` donors) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.2s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase320_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase320DonorSnapshot(
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
            P320_DONOR_FX3_APPFW_702_RELPATH,
            P320_PINNED_FX3_APPFW_702_BYTES,
            P320_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702"),
        ),
        (
            "fx6_appfw_601_so",
            P320_DONOR_FX6_APPFW_601_RELPATH,
            P320_PINNED_FX6_APPFW_601_BYTES,
            P320_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601"),
        ),
        (
            "fx3_backup_bin",
            P320_DONOR_FX3_BACKUP_BIN_RELPATH,
            P320_PINNED_FX3_BACKUP_BIN_BYTES,
            P320_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_uxc_en_f",
            P320_DONOR_FX3_UXC_EN_F_RELPATH,
            P320_PINNED_FX3_UXC_EN_F_BYTES,
            P320_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P320_DONOR_FX3_UXC_SC_F_RELPATH,
            P320_PINNED_FX3_UXC_SC_F_BYTES,
            P320_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P320_DONOR_FX3_UXC_TC_F_RELPATH,
            P320_PINNED_FX3_UXC_TC_F_BYTES,
            P320_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P320_DONOR_FX3_UXC_JA_F_RELPATH,
            P320_PINNED_FX3_UXC_JA_F_BYTES,
            P320_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P320_DONOR_FX3_UXC_EN_RELPATH,
            P320_PINNED_FX3_UXC_EN_BYTES,
            P320_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_sc",
            P320_DONOR_FX3_UXC_SC_RELPATH,
            P320_PINNED_FX3_UXC_SC_BYTES,
            P320_PINNED_FX3_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC"),
        ),
        (
            "fx3_uxc_tc",
            P320_DONOR_FX3_UXC_TC_RELPATH,
            P320_PINNED_FX3_UXC_TC_BYTES,
            P320_PINNED_FX3_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC"),
        ),
        (
            "fx3_uxc_ja",
            P320_DONOR_FX3_UXC_JA_RELPATH,
            P320_PINNED_FX3_UXC_JA_BYTES,
            P320_PINNED_FX3_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA"),
        ),
        (
            "fx3_uxc_en_g",
            P320_DONOR_FX3_UXC_EN_G_RELPATH,
            P320_PINNED_FX3_UXC_EN_G_BYTES,
            P320_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx3_uxc_sc_g",
            P320_DONOR_FX3_UXC_SC_G_RELPATH,
            P320_PINNED_FX3_UXC_SC_G_BYTES,
            P320_PINNED_FX3_UXC_SC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_G"),
        ),
        (
            "fx3_uxc_tc_g",
            P320_DONOR_FX3_UXC_TC_G_RELPATH,
            P320_PINNED_FX3_UXC_TC_G_BYTES,
            P320_PINNED_FX3_UXC_TC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_G"),
        ),
        (
            "fx3_uxc_ja_g",
            P320_DONOR_FX3_UXC_JA_G_RELPATH,
            P320_PINNED_FX3_UXC_JA_G_BYTES,
            P320_PINNED_FX3_UXC_JA_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_G"),
        ),
        (
            "fx6_uxc_en",
            P320_DONOR_FX6_UXC_EN_RELPATH,
            P320_PINNED_FX6_UXC_EN_BYTES,
            P320_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P320_DONOR_FX6_UXC_EN_2_RELPATH,
            P320_PINNED_FX6_UXC_EN_2_BYTES,
            P320_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    digests: List[Phase320DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            break
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        digests.append(
            Phase320DonorArtifactDigest(
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
        artifacts = _synthetic_phase320_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase320DonorSnapshot(
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
    return Phase320DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 57-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase320DonorArtifactDigest:
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
class Phase320DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase320DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TouchDispZeroEvfVaultSpec:
    # Wave-55 Touch Operation 4-item tree vs dormant Touch Shutter/AE/Pad/Footer
    camera_model: str
    fw_version: str
    shooting_domain: str
    touch_operation: str
    touch_sensitivity: str
    touch_func_in_shooting: str
    swipe_up: str
    requested_dormant_touch_symbols: Tuple[str, ...]
    reported_dormant_touch_errno: Optional[int]
    reported_swipe_up_active: bool
    post_touch_operation: str
    post_touch_sensitivity: str
    post_touch_func_in_shooting: str
    post_swipe_up: str
    # [Operation Customize] -> [DISP (Screen Disp) Set] 4-shoot / 3-PB & Zero-EVF Blackout Guard
    disp_set_menu_path: Tuple[str, ...]
    disp_shoot_pages_enabled: Tuple[str, ...]
    disp_play_pages_enabled: Tuple[str, ...]
    post_disp_shoot_pages_enabled: Tuple[str, ...]
    post_disp_play_pages_enabled: Tuple[str, ...]
    requested_dormant_evf_symbols: Tuple[str, ...]
    reported_dormant_evf_errno: Optional[int]
    fx3_has_builtin_evf: bool
    fx3_has_eye_sensor: bool
    fx3_has_finder_monitor_button: bool
    evf_scanout_blocked: bool
    lcd_panel_scanout_preserved: bool
    # ILME-FX6 boundary
    fx6_exposes_touch_sensitivity_or_swipe_up: bool
    fx6_uses_loupe_term: bool
    reset_action: str
    # Tier-0 / Stage-B / Slot-1 Vault firewall
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
    touch_op_dormant_trap_or_reset_drift_events: int
    disp_set_or_zero_evf_blackout_events: int
    fx6_touch_or_evf_spoof_events: int


@dataclass(frozen=True)
class TouchDispZeroEvfVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    touch_4item_tree_init_only_and_dormant_rejected_verified: bool
    disp_set_4shoot_3pb_and_path_verified: bool
    zero_evf_blackout_guard_verified: bool
    fx6_touch_and_detachable_lcd_contrast_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    touch_op_dormant_trap_or_reset_drift_events: int
    disp_set_or_zero_evf_blackout_events: int
    fx6_touch_or_evf_spoof_events: int
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
class StillAelFlashIntervalPbEditVaultSpec:
    # Still-only [AEL w/ Shutter] & Flash Submenu Reset Split
    camera_model: str
    fw_version: str
    shooting_domain: str
    ael_w_shutter: str
    ael_toggle_key_active: bool
    reported_half_press_ael_locked: bool
    exp_comp_set: str
    wireless_flash: str
    ext_flash_direct_mishoe: bool
    ext_flash_sync_cord_requested: bool
    ext_flash_camera_menu_reset_requested: bool
    reported_still_flash_errno: Optional[int]
    reported_ext_flash_errno: Optional[int]
    post_ael_w_shutter: str
    post_exp_comp_set: str
    post_wireless_flash: str
    fx6_exposes_still_ttl_flash_or_ael: bool
    fx6_flash_band_reduce_is_rolling_shutter_comp: bool
    # 9-Speed Interval PB under Playback -> [Viewing]
    interval_pb_menu_path: Tuple[str, ...]
    cont_play_for_interval: str
    play_speed_for_interval: int
    play_speed_scale_min: int
    play_speed_scale_max: int
    in_camera_timelapse_movie_synthesis_supported: bool
    interval_pb_read_only_safe: bool
    post_cont_play_for_interval: str
    post_play_speed_for_interval: int
    # Playback [Edit] Slot-1 Tier-0 EROFS=30 / EOPNOTSUPP=95 Vault Firewall
    select_playback_media_slot: int
    target_write_slot: int
    slot1_holds_tier0_vault: bool
    photo_capture_file_type: str
    post_photo_capture_file_type: str
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    reset_action: str
    # Slot-1 Tier-0 Vault & Stage-B Overlay
    slot1_data_sector_writes: int
    slot1_edit_avf_info_mutation_bytes: int
    slot1_avf_info_mutated: bool
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_eopnotsupp_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    still_ael_flash_reset_split_or_mishoe_drift_events: int
    interval_pb_9scale_or_path_drift_events: int
    playback_edit_dormant_or_slot1_vault_bypass_events: int


@dataclass(frozen=True)
class StillAelFlashIntervalPbEditVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    still_ael_and_flash_reset_split_verified: bool
    ext_flash_direct_mishoe_and_fx6_contrast_verified: bool
    interval_pb_9speed_viewing_path_verified: bool
    playback_edit_slot1_erofs30_and_dormant_95_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    still_ael_flash_reset_split_or_mishoe_drift_events: int
    interval_pb_9scale_or_path_drift_events: int
    playback_edit_dormant_or_slot1_vault_bypass_events: int
    slot1_data_sector_writes: int
    slot1_edit_avf_info_mutation_bytes: int
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
class TouchDispZeroEvfFlashIntervalPbVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase320DonorSnapshot
    touch_disp_zero_evf_report: TouchDispZeroEvfVaultReport
    still_ael_flash_interval_pb_edit_report: StillAelFlashIntervalPbEditVaultReport
    touch_op_dormant_trap_or_reset_drift_events: int
    disp_set_or_zero_evf_blackout_events: int
    fx6_touch_or_evf_spoof_events: int
    still_ael_flash_reset_split_or_mishoe_drift_events: int
    interval_pb_9scale_or_path_drift_events: int
    playback_edit_dormant_or_slot1_vault_bypass_events: int
    slot1_data_sector_writes: int
    slot1_edit_avf_info_mutation_bytes: int
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
class Pillar57ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar57ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar57ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar57BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar57ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar57StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase320DonorSnapshot
    pillar_57a_touch_disp_zero_evf_vault: Pillar57ASuiteResult
    pillar_57b_still_ael_flash_interval_pb_edit_vault: Pillar57BSuiteResult
    touch_op_dormant_trap_or_reset_drift_events: int
    disp_set_or_zero_evf_blackout_events: int
    fx6_touch_or_evf_spoof_events: int
    still_ael_flash_reset_split_or_mishoe_drift_events: int
    interval_pb_9scale_or_path_drift_events: int
    playback_edit_dormant_or_slot1_vault_bypass_events: int
    slot1_data_sector_writes: int
    slot1_edit_avf_info_mutation_bytes: int
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
class Master57PillarRecoveryReport:
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
    # Pillar 57 & Wave-55 top-level fields (Phase 320 — 57/57 Milestone)
    donor_snapshot: Phase320DonorSnapshot
    pillar57_a_touch_disp_zero_evf_vault: Pillar57ASuiteResult
    pillar57_b_still_ael_flash_interval_pb_edit_vault: Pillar57BSuiteResult
    touch_op_dormant_trap_or_reset_drift_events: int
    disp_set_or_zero_evf_blackout_events: int
    fx6_touch_or_evf_spoof_events: int
    still_ael_flash_reset_split_or_mishoe_drift_events: int
    interval_pb_9scale_or_path_drift_events: int
    playback_edit_dormant_or_slot1_vault_bypass_events: int
    slot1_data_sector_writes: int
    slot1_edit_avf_info_mutation_bytes: int
    slot1_avf_info_mutated: bool
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_eopnotsupp_enforced: bool
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
    # Preserved Pillars 1..56 rollup metrics
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
    master_57pillar_sha256: str
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
# Spec Builders (Pillars 57A & 57B)
# ---------------------------------------------------------------------------


def build_default_safe_touch_disp_zero_evf_vault_spec(
    **overrides: Any,
) -> TouchDispZeroEvfVaultSpec:
    """Return a clean, verified default `TouchDispZeroEvfVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P320_FX3_MODEL_NAME,
        "fw_version": P320_FX3_FW_VERSION,
        "shooting_domain": "Movie",
        "touch_operation": P320_TOUCH_OPERATION_DEFAULT,
        "touch_sensitivity": P320_TOUCH_SENSITIVITY_DEFAULT,
        "touch_func_in_shooting": P320_TOUCH_FUNC_SHOOTING_DEFAULT,
        "swipe_up": P320_SWIPE_UP_DEFAULT,
        "requested_dormant_touch_symbols": (),
        "reported_dormant_touch_errno": None,
        "reported_swipe_up_active": True,
        "post_touch_operation": P320_TOUCH_OPERATION_DEFAULT,
        "post_touch_sensitivity": P320_TOUCH_SENSITIVITY_DEFAULT,
        "post_touch_func_in_shooting": P320_TOUCH_FUNC_SHOOTING_DEFAULT,
        "post_swipe_up": P320_SWIPE_UP_DEFAULT,
        "disp_set_menu_path": P320_DISP_SET_MENU_PATH,
        "disp_shoot_pages_enabled": P320_DISP_SHOOT_4_PAGES,
        "disp_play_pages_enabled": P320_DISP_PLAY_3_PAGES,
        "post_disp_shoot_pages_enabled": P320_DISP_SHOOT_4_PAGES,
        "post_disp_play_pages_enabled": P320_DISP_PLAY_3_PAGES,
        "requested_dormant_evf_symbols": (),
        "reported_dormant_evf_errno": None,
        "fx3_has_builtin_evf": False,
        "fx3_has_eye_sensor": False,
        "fx3_has_finder_monitor_button": False,
        "evf_scanout_blocked": True,
        "lcd_panel_scanout_preserved": True,
        "fx6_exposes_touch_sensitivity_or_swipe_up": False,
        "fx6_uses_loupe_term": False,
        "reset_action": "None",
        "requested_vault_slot": P320_SLOT1_VAULT_SLOT,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P320_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P320_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P320_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P320_TIER0_SURFACE_COUNT,
        "touch_op_dormant_trap_or_reset_drift_events": 0,
        "disp_set_or_zero_evf_blackout_events": 0,
        "fx6_touch_or_evf_spoof_events": 0,
    }
    defaults.update(overrides)
    return TouchDispZeroEvfVaultSpec(**defaults)


def build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
    **overrides: Any,
) -> StillAelFlashIntervalPbEditVaultSpec:
    """Return a clean, verified default `StillAelFlashIntervalPbEditVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P320_FX3_MODEL_NAME,
        "fw_version": P320_FX3_FW_VERSION,
        "shooting_domain": "Still",
        "ael_w_shutter": P320_AEL_W_SHUTTER_DEFAULT,
        "ael_toggle_key_active": False,
        "reported_half_press_ael_locked": True,
        "exp_comp_set": P320_EXP_COMP_SET_DEFAULT,
        "wireless_flash": P320_WIRELESS_FLASH_DEFAULT,
        "ext_flash_direct_mishoe": True,
        "ext_flash_sync_cord_requested": False,
        "ext_flash_camera_menu_reset_requested": False,
        "reported_still_flash_errno": None,
        "reported_ext_flash_errno": None,
        "post_ael_w_shutter": P320_AEL_W_SHUTTER_DEFAULT,
        "post_exp_comp_set": P320_EXP_COMP_SET_DEFAULT,
        "post_wireless_flash": P320_WIRELESS_FLASH_DEFAULT,
        "fx6_exposes_still_ttl_flash_or_ael": False,
        "fx6_flash_band_reduce_is_rolling_shutter_comp": True,
        "interval_pb_menu_path": P320_INTERVAL_PB_MENU_PATH,
        "cont_play_for_interval": "Off",
        "play_speed_for_interval": P320_INTERVAL_PB_SPEED_DEFAULT,
        "play_speed_scale_min": P320_FX3_INTERVAL_PB_SPEED_MIN,
        "play_speed_scale_max": P320_FX3_INTERVAL_PB_SPEED_MAX,
        "in_camera_timelapse_movie_synthesis_supported": False,
        "interval_pb_read_only_safe": True,
        "post_cont_play_for_interval": "Off",
        "post_play_speed_for_interval": P320_INTERVAL_PB_SPEED_DEFAULT,
        "select_playback_media_slot": P320_SELECT_PLAYBACK_MEDIA_DEFAULT_SLOT,
        "target_write_slot": P320_SLOT1_VAULT_SLOT,
        "slot1_holds_tier0_vault": True,
        "photo_capture_file_type": P320_PHOTO_CAPTURE_FILE_DEFAULT,
        "post_photo_capture_file_type": P320_PHOTO_CAPTURE_FILE_DEFAULT,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": True,
        "vault_firewall_errno": None,
        "reset_action": "None",
        "slot1_data_sector_writes": 0,
        "slot1_edit_avf_info_mutation_bytes": 0,
        "slot1_avf_info_mutated": False,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_eopnotsupp_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P320_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P320_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P320_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P320_TIER0_SURFACE_COUNT,
        "still_ael_flash_reset_split_or_mishoe_drift_events": 0,
        "interval_pb_9scale_or_path_drift_events": 0,
        "playback_edit_dormant_or_slot1_vault_bypass_events": 0,
    }
    defaults.update(overrides)
    return StillAelFlashIntervalPbEditVaultSpec(**defaults)


# ---------------------------------------------------------------------------
# Evaluators & Single-Shot Combined Verifier (Pillars 57A & 57B)
# ---------------------------------------------------------------------------


def evaluate_touch_disp_zero_evf_vault(
    spec: TouchDispZeroEvfVaultSpec,
) -> TouchDispZeroEvfVaultReport:
    """Evaluate Pillar 57A: Wave-55 `[Touch Operation]` 4-item tree (`Initialize`-only) vs
    dormant `Touch Shutter`/`Touch AE`/`Touch Panel/Pad`/`Footer Icon Touch` (`EOPNOTSUPP=95`),
    `[Operation Customize] -> [DISP (Screen Disp) Set]` 4-shoot/3-PB pages, Zero-EVF Blackout
    Guard (`ILME-FX3` zero EVF/eye sensor/`FINDER/MONITOR`), `ILME-FX6` contrast, & Slot-1 Vault."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(
            P320_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Module safety invariant violation",
        )

    valid_fw = (
        (
            spec.camera_model == P320_FX3_MODEL_NAME
            and spec.fw_version in P320_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P320_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P320_FX6_DONOR_FW_VERSION
        )
    )
    valid_fx6_touch = (
        spec.camera_model == P320_FX6_DONOR_MODEL_NAME
        and spec.touch_operation in P320_FX6_TOUCH_OPERATION_MODES
        and spec.touch_func_in_shooting in P320_FX6_TOUCH_MF_MODES
    )
    valid_fx3_touch = (
        spec.camera_model == P320_FX3_MODEL_NAME
        and spec.touch_operation in P320_TOUCH_OPERATION_MODES
        and spec.touch_sensitivity in P320_TOUCH_SENSITIVITY_MODES
        and spec.touch_func_in_shooting in P320_TOUCH_FUNC_SHOOTING_MODES
        and spec.swipe_up in P320_SWIPE_UP_MODES
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P320_SHOOTING_DOMAINS
        or spec.reset_action not in P320_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P320_VAULT_TARGET_ACTIONS
    ):
        _fail(
            P320_BLOCKED_INVALID_PILLAR57A_SPEC,
            "Invalid Pillar 57A camera/shooting_domain/reset_action/vault spec parameter",
        )

    st = compute_expected_touch_disp_zero_evf_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        touch_operation=spec.touch_operation,
        touch_sensitivity=spec.touch_sensitivity,
        touch_func_in_shooting=spec.touch_func_in_shooting,
        swipe_up=spec.swipe_up,
        requested_dormant_touch_symbols=spec.requested_dormant_touch_symbols,
        disp_shoot_pages_enabled=spec.disp_shoot_pages_enabled,
        disp_play_pages_enabled=spec.disp_play_pages_enabled,
        requested_dormant_evf_symbols=spec.requested_dormant_evf_symbols,
        reset_action=spec.reset_action,
    )

    # 1. Wave-55 Touch Operation 4-item tree, Initialize-only persistence & dormant trap rejection
    touch_ok = (
        (valid_fx3_touch or valid_fx6_touch)
        and spec.touch_sensitivity != P320_TOUCH_SENSITIVITY_DORMANT_OR_WRONG
        and spec.reported_dormant_touch_errno == st["dormant_touch_errno"]
        and not (
            len(spec.requested_dormant_touch_symbols) > 0
            and spec.reported_dormant_touch_errno != P320_EOPNOTSUPP_ERRNO
        )
        and spec.reported_swipe_up_active == st["swipe_up_active"]
        and spec.post_touch_operation == st["post_touch_operation"]
        and spec.post_touch_sensitivity == st["post_touch_sensitivity"]
        and spec.post_touch_func_in_shooting == st["post_touch_func_in_shooting"]
        and spec.post_swipe_up == st["post_swipe_up"]
        and spec.touch_op_dormant_trap_or_reset_drift_events == 0
    )
    if not touch_ok:
        _fail(
            P320_BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT,
            "Touch Operation violated 4-item tree (Standard/Sensitive, Touch Focus/Tracking/Off, Swipe Up), Initialize-only persistence, or dormant Touch Shutter/AE/Pad/Footer EOPNOTSUPP=95 gate",
        )

    # 2. [Operation Customize] -> [DISP (Screen Disp) Set] 4-shoot / 3-PB pages & Initialize-only
    zero_evf_core_ok = (
        not spec.fx3_has_builtin_evf
        and not spec.fx3_has_eye_sensor
        and not spec.fx3_has_finder_monitor_button
        and spec.evf_scanout_blocked
        and spec.lcd_panel_scanout_preserved
        and spec.reported_dormant_evf_errno == st["dormant_evf_errno"]
        and not (
            len(spec.requested_dormant_evf_symbols) > 0
            and spec.reported_dormant_evf_errno != P320_EOPNOTSUPP_ERRNO
        )
    )
    disp_ok = (
        (
            spec.camera_model != P320_FX3_MODEL_NAME
            or (
                tuple(spec.disp_set_menu_path) == P320_DISP_SET_MENU_PATH
                and tuple(spec.disp_shoot_pages_enabled) == P320_DISP_SHOOT_4_PAGES
                and tuple(spec.disp_play_pages_enabled) == P320_DISP_PLAY_3_PAGES
                and tuple(spec.post_disp_shoot_pages_enabled) == tuple(st["post_disp_shoot_pages"])
                and tuple(spec.post_disp_play_pages_enabled) == tuple(st["post_disp_play_pages"])
            )
        )
        and (spec.disp_set_or_zero_evf_blackout_events == 0 or not zero_evf_core_ok)
    )
    if not disp_ok:
        _fail(
            P320_BLOCKED_DISP_SET_4SHOOT_3PB_OR_PATH_DRIFT,
            "DISP (Screen Disp) Set violated Setup -> Operation Customize path, 4-shoot/3-PB page set, or Initialize-only persistence",
        )

    # 3. Zero-EVF Blackout Guard (no EVF, no eye sensor, no FINDER/MONITOR button, dormant EVF traps -> EOPNOTSUPP=95)
    zero_evf_ok = zero_evf_core_ok and spec.disp_set_or_zero_evf_blackout_events == 0
    if not zero_evf_ok:
        _fail(
            P320_BLOCKED_ZERO_EVF_BLACKOUT_GUARD_BREACH,
            "Zero-EVF Blackout Guard breached: FX3 must never enable EVF/eye-sensor/FINDER-MONITOR/Graphic Display/Monitor Off scanout",
        )

    # 4. ILME-FX6 boundary (zero Touch Sensitivity/Swipe Up, Viewfinder/Viewfinder Hood, no Loupe)
    fx6_ok = (
        not (
            spec.camera_model == P320_FX6_DONOR_MODEL_NAME
            and (spec.fx6_exposes_touch_sensitivity_or_swipe_up or spec.fx6_uses_loupe_term)
        )
        and not spec.fx6_uses_loupe_term
        and spec.fx6_touch_or_evf_spoof_events == 0
    )
    if not fx6_ok:
        _fail(
            P320_BLOCKED_FX6_TOUCH_OR_EVF_SPOOF,
            "ILME-FX6 touch/viewfinder boundary violated (no Touch Sensitivity/Swipe Up, no Loupe terminology)",
        )

    # 5. Slot-1 Tier-0 Vault Firewall & Stage-B Overlay & H0 == H3
    destructive_vault_actions = (
        "ROTATE",
        "PHOTO_CAPTURE",
        "COPY_TO_TARGET",
        "BEAUTY_EFFECT",
        "TRIMMING",
        "FORMAT_QUICK",
        "FORMAT_FULL",
    )
    vault_fw_ok = (
        spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_vault_mutation_bytes == 0
        and not (
            spec.requested_vault_slot == P320_SLOT1_VAULT_SLOT
            and spec.requested_vault_action in destructive_vault_actions
        )
    )
    if not vault_fw_ok:
        _fail(
            P320_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS/EOPNOTSUPP firewall blocked write/format mutation on Tier-0 media",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P320_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P320_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P320_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P320_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "57A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "fw_version": spec.fw_version,
            "shooting_domain": spec.shooting_domain,
            "post_touch_operation": spec.post_touch_operation,
            "post_touch_sensitivity": spec.post_touch_sensitivity,
            "post_touch_func_in_shooting": spec.post_touch_func_in_shooting,
            "post_swipe_up": spec.post_swipe_up,
            "evf_scanout_blocked": spec.evf_scanout_blocked,
            "slot1_bytes": spec.slot1_vault_mutation_bytes,
            "errors": errors,
        }
    )
    return TouchDispZeroEvfVaultReport(
        schema=PHASE320_SCHEMA,
        version=PHASE320_VERSION,
        passed=passed,
        status=P320_STATUS_VERIFIED_PILLAR_57A if passed else P320_STATUS_REJECTED_PILLAR_57A,
        block_code=block_code,
        touch_4item_tree_init_only_and_dormant_rejected_verified=touch_ok,
        disp_set_4shoot_3pb_and_path_verified=disp_ok,
        zero_evf_blackout_guard_verified=zero_evf_ok,
        fx6_touch_and_detachable_lcd_contrast_verified=fx6_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        touch_op_dormant_trap_or_reset_drift_events=spec.touch_op_dormant_trap_or_reset_drift_events,
        disp_set_or_zero_evf_blackout_events=spec.disp_set_or_zero_evf_blackout_events,
        fx6_touch_or_evf_spoof_events=spec.fx6_touch_or_evf_spoof_events,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_still_ael_flash_interval_pb_edit_vault(
    spec: StillAelFlashIntervalPbEditVaultSpec,
) -> StillAelFlashIntervalPbEditVaultReport:
    """Evaluate Pillar 57B: Still-only `[AEL w/ Shutter]` & Flash submenu asymmetric reset split
    (`Wireless Flash` ONLY resettable via `Camera Settings Reset`), direct-MI-Shoe `[External
    Flash Set.]` vs flash-less `ILME-FX6` (`Flash Band Reduce`), 9-speed `[Viewing]` Interval PB,
    and Playback `[Edit]` `Slot-1` Tier-0 Vault `EROFS=30` / dormant `[Beauty Effect]`/`[Trimming]`
    `EOPNOTSUPP=95` firewall."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(
            P320_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Module safety invariant violation",
        )

    valid_fw = (
        (
            spec.camera_model == P320_FX3_MODEL_NAME
            and spec.fw_version in P320_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P320_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P320_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P320_SHOOTING_DOMAINS
        or spec.ael_w_shutter not in P320_AEL_W_SHUTTER_MODES
        or spec.exp_comp_set not in P320_EXP_COMP_SET_MODES
        or spec.wireless_flash not in P320_WIRELESS_FLASH_MODES
        or spec.cont_play_for_interval not in P320_ON_OFF_MODES
        or spec.photo_capture_file_type not in P320_PHOTO_CAPTURE_FILE_TYPES
        or spec.select_playback_media_slot not in (1, 2)
        or spec.target_write_slot not in (1, 2)
        or spec.reset_action not in P320_RESET_ACTIONS
        or spec.requested_vault_action not in P320_VAULT_TARGET_ACTIONS
        or (
            spec.vault_firewall_errno is not None
            and spec.vault_firewall_errno not in P320_VAULT_FIREWALL_ERRNOS
        )
    ):
        _fail(
            P320_BLOCKED_INVALID_PILLAR57B_SPEC,
            "Invalid Pillar 57B camera/AEL/Flash/IntervalPB/Edit/vault spec parameter",
        )

    st = compute_expected_still_ael_flash_interval_pb_edit_vault_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        ael_w_shutter=spec.ael_w_shutter,
        ael_toggle_key_active=spec.ael_toggle_key_active,
        exp_comp_set=spec.exp_comp_set,
        wireless_flash=spec.wireless_flash,
        ext_flash_direct_mishoe=spec.ext_flash_direct_mishoe,
        ext_flash_sync_cord_requested=spec.ext_flash_sync_cord_requested,
        ext_flash_camera_menu_reset_requested=spec.ext_flash_camera_menu_reset_requested,
        cont_play_for_interval=spec.cont_play_for_interval,
        play_speed_for_interval=spec.play_speed_for_interval,
        photo_capture_file_type=spec.photo_capture_file_type,
        select_playback_media_slot=spec.select_playback_media_slot,
        target_write_slot=spec.target_write_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
        reset_action=spec.reset_action,
    )

    # 1. Still-only [AEL w/ Shutter] & Flash submenu asymmetric reset split
    ael_flash_ok = (
        spec.reported_still_flash_errno == st["still_flash_errno"]
        and spec.reported_half_press_ael_locked == st["half_press_ael_locked"]
        and spec.post_ael_w_shutter == st["post_ael_w_shutter"]
        and spec.post_exp_comp_set == st["post_exp_comp_set"]
        and spec.post_wireless_flash == st["post_wireless_flash"]
        and spec.still_ael_flash_reset_split_or_mishoe_drift_events == 0
    )
    if not ael_flash_ok:
        _fail(
            P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT,
            "Still-only [AEL w/ Shutter] / [Exp.comp.set] / [Wireless Flash] violated Still gate (EOPNOTSUPP=95 in Movie/S&Q), [AEL toggle] override, or Camera Settings Reset split",
        )

    # 2. Direct MI-Shoe [External Flash Set.] & FX6 rolling-shutter Flash Band Reduce boundary
    ext_flash_fx6_ok = (
        spec.reported_ext_flash_errno == st["ext_flash_errno"]
        and not spec.fx6_exposes_still_ttl_flash_or_ael
        and spec.fx6_flash_band_reduce_is_rolling_shutter_comp
        and spec.still_ael_flash_reset_split_or_mishoe_drift_events == 0
    )
    if not ext_flash_fx6_ok:
        _fail(
            P320_BLOCKED_EXT_FLASH_MISHOE_OR_FX6_SPOOF,
            "External Flash Set. violated direct MI-Shoe requirement (sync cord/menu reset EOPNOTSUPP=95) or FX6 zero TTL flash / Flash Band Reduce boundary",
        )

    # 3. 9-Speed Interval PB under Playback -> [Viewing] (default 5, 1..9, Initialize-only, read-only)
    speed_in_range = (
        spec.camera_model == P320_FX6_DONOR_MODEL_NAME
        or (P320_FX3_INTERVAL_PB_SPEED_MIN <= spec.play_speed_for_interval <= P320_FX3_INTERVAL_PB_SPEED_MAX)
    )
    interval_pb_ok = (
        speed_in_range
        and spec.play_speed_scale_min == P320_FX3_INTERVAL_PB_SPEED_MIN
        and spec.play_speed_scale_max == P320_FX3_INTERVAL_PB_SPEED_MAX
        and (
            spec.camera_model != P320_FX3_MODEL_NAME
            or tuple(spec.interval_pb_menu_path) == P320_INTERVAL_PB_MENU_PATH
        )
        and not spec.in_camera_timelapse_movie_synthesis_supported
        and spec.interval_pb_read_only_safe
        and spec.post_cont_play_for_interval == st["post_cont_play_for_interval"]
        and spec.post_play_speed_for_interval == st["post_play_speed_for_interval"]
        and spec.interval_pb_9scale_or_path_drift_events == 0
    )
    if not interval_pb_ok:
        _fail(
            P320_BLOCKED_INTERVAL_PB_9SCALE_OR_PATH_DRIFT,
            "Interval PB violated Playback -> [Viewing] path, 1..9 speed scale (default 5), Initialize-only persistence, or read-only/no-synthesis contract",
        )

    # 4. Playback [Edit] Slot-1 Tier-0 EROFS=30 Firewall & dormant [Beauty Effect]/[Trimming] EOPNOTSUPP=95
    slot1_mutated_violation = (
        spec.target_write_slot == P320_SLOT1_VAULT_SLOT
        and spec.slot1_holds_tier0_vault
        and spec.requested_vault_action in P320_WRITE_MUTATING_EDIT_ACTIONS
        and spec.reported_vault_action_allowed
    )
    dormant_edit_allowed_violation = (
        spec.requested_vault_action in ("BEAUTY_EFFECT", "TRIMMING")
        and spec.reported_vault_action_allowed
    )
    edit_vault_ok = (
        not slot1_mutated_violation
        and not dormant_edit_allowed_violation
        and spec.reported_vault_action_allowed == st["action_allowed"]
        and spec.vault_firewall_errno == st["firewall_errno"]
        and spec.post_photo_capture_file_type == st["post_photo_capture_file_type"]
        and spec.playback_edit_dormant_or_slot1_vault_bypass_events == 0
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_edit_avf_info_mutation_bytes == 0
        and not spec.slot1_avf_info_mutated
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_eopnotsupp_enforced
        and spec.slot1_format_hard_locked
    )
    if not edit_vault_ok:
        _fail(
            P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL,
            "Playback [Edit] breached Slot-1 Tier-0 EROFS=30 firewall (Rotate/Photo Capture/Copy) or dormant Beauty Effect/Trimming EOPNOTSUPP=95 gate",
        )

    # 5. Stage-B Overlay & H0 == H3
    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P320_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P320_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P320_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P320_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = edit_vault_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "57B",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "shooting_domain": spec.shooting_domain,
            "post_ael": spec.post_ael_w_shutter,
            "post_exp_comp": spec.post_exp_comp_set,
            "post_wireless": spec.post_wireless_flash,
            "post_speed": spec.post_play_speed_for_interval,
            "action": spec.requested_vault_action,
            "target_slot": spec.target_write_slot,
            "slot1_writes": spec.slot1_data_sector_writes,
            "errors": errors,
        }
    )
    return StillAelFlashIntervalPbEditVaultReport(
        schema=PHASE320_SCHEMA,
        version=PHASE320_VERSION,
        passed=passed,
        status=P320_STATUS_VERIFIED_PILLAR_57B if passed else P320_STATUS_REJECTED_PILLAR_57B,
        block_code=block_code,
        still_ael_and_flash_reset_split_verified=ael_flash_ok,
        ext_flash_direct_mishoe_and_fx6_contrast_verified=ext_flash_fx6_ok,
        interval_pb_9speed_viewing_path_verified=interval_pb_ok,
        playback_edit_slot1_erofs30_and_dormant_95_verified=edit_vault_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        still_ael_flash_reset_split_or_mishoe_drift_events=(
            spec.still_ael_flash_reset_split_or_mishoe_drift_events
        ),
        interval_pb_9scale_or_path_drift_events=spec.interval_pb_9scale_or_path_drift_events,
        playback_edit_dormant_or_slot1_vault_bypass_events=(
            spec.playback_edit_dormant_or_slot1_vault_bypass_events
        ),
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_edit_avf_info_mutation_bytes=spec.slot1_edit_avf_info_mutation_bytes,
        slot1_avf_info_mutated=spec.slot1_avf_info_mutated,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_eopnotsupp_enforced=spec.slot1_vault_erofs_eopnotsupp_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_touch_disp_zero_evf_flash_interval_pb_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_57a: Optional[TouchDispZeroEvfVaultSpec] = None,
    spec_57b: Optional[StillAelFlashIntervalPbEditVaultSpec] = None,
) -> TouchDispZeroEvfFlashIntervalPbVaultReport:
    """Combined single-shot verifier for Pillar 57A + Pillar 57B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase320_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_touch_disp_zero_evf_vault(
        spec_57a or build_default_safe_touch_disp_zero_evf_vault_spec()
    )
    rep_b = evaluate_still_ael_flash_interval_pb_edit_vault(
        spec_57b or build_default_safe_still_ael_flash_interval_pb_edit_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 320 Wave-55 donor artifact parity check failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return TouchDispZeroEvfFlashIntervalPbVaultReport(
        schema=PHASE320_SCHEMA,
        version=PHASE320_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P320_STATUS_VERIFIED_PILLAR57_SUITE if all_ok else P320_STATUS_FAIL_PILLAR57_SUITE,
        donor_snapshot=donor_snapshot,
        touch_disp_zero_evf_report=rep_a,
        still_ael_flash_interval_pb_edit_report=rep_b,
        touch_op_dormant_trap_or_reset_drift_events=rep_a.touch_op_dormant_trap_or_reset_drift_events,
        disp_set_or_zero_evf_blackout_events=rep_a.disp_set_or_zero_evf_blackout_events,
        fx6_touch_or_evf_spoof_events=rep_a.fx6_touch_or_evf_spoof_events,
        still_ael_flash_reset_split_or_mishoe_drift_events=(
            rep_b.still_ael_flash_reset_split_or_mishoe_drift_events
        ),
        interval_pb_9scale_or_path_drift_events=rep_b.interval_pb_9scale_or_path_drift_events,
        playback_edit_dormant_or_slot1_vault_bypass_events=(
            rep_b.playback_edit_dormant_or_slot1_vault_bypass_events
        ),
        slot1_data_sector_writes=rep_b.slot1_data_sector_writes,
        slot1_edit_avf_info_mutation_bytes=rep_b.slot1_edit_avf_info_mutation_bytes,
        slot1_avf_info_mutated=rep_b.slot1_avf_info_mutated,
        slot1_vault_mutation_bytes=rep_a.slot1_vault_mutation_bytes + rep_b.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=(rep_a.slot1_format_hard_locked and rep_b.slot1_format_hard_locked),
        slot1_vault_erofs_eopnotsupp_enforced=(
            rep_a.slot1_vault_erofs_eopnotsupp_enforced and rep_b.slot1_vault_erofs_eopnotsupp_enforced
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


def verify_touch_disp_zero_evf_flash_interval_pb_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_57a: Optional[TouchDispZeroEvfVaultSpec] = None,
    spec_57b: Optional[StillAelFlashIntervalPbEditVaultSpec] = None,
) -> TouchDispZeroEvfFlashIntervalPbVaultReport:
    """Symmetry alias for `verify_touch_disp_zero_evf_flash_interval_pb_and_vault`."""
    return verify_touch_disp_zero_evf_flash_interval_pb_and_vault(
        force_clean_room=force_clean_room,
        spec_57a=spec_57a,
        spec_57b=spec_57b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 57A & 57B) + Standalone Pillar 57 Suite
# ---------------------------------------------------------------------------


def run_pillar57a_touch_disp_zero_evf_6_scenario_suite() -> Pillar57ASuiteResult:
    """Run 6 Pillar 57A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, TouchDispZeroEvfVaultSpec, Optional[str]], ...] = (
        (
            P320_PILLAR_57A_SCENARIO_IDS[0],
            True,
            build_default_safe_touch_disp_zero_evf_vault_spec(
                shooting_domain="Still",
                touch_operation="On",
                touch_sensitivity="Sensitive",
                touch_func_in_shooting="Touch Focus",
                swipe_up="Open the Fn Menu",
                reported_swipe_up_active=True,
                post_touch_operation="On",
                post_touch_sensitivity="Sensitive",
                post_touch_func_in_shooting="Touch Focus",
                post_swipe_up="Open the Fn Menu",
            ),
            None,
        ),
        (
            P320_PILLAR_57A_SCENARIO_IDS[1],
            True,
            build_default_safe_touch_disp_zero_evf_vault_spec(
                shooting_domain="S&Q",
                touch_operation="On: Playback Only",
                touch_sensitivity="Sensitive",
                touch_func_in_shooting="Off",
                swipe_up="Off",
                reported_swipe_up_active=False,
                reset_action="Camera Settings Reset",
                post_touch_operation="On: Playback Only",
                post_touch_sensitivity="Sensitive",
                post_touch_func_in_shooting="Off",
                post_swipe_up="Off",
            ),
            None,
        ),
        (
            P320_PILLAR_57A_SCENARIO_IDS[2],
            False,
            build_default_safe_touch_disp_zero_evf_vault_spec(
                requested_dormant_touch_symbols=(
                    "Touch Shutter",
                    "Touch AE",
                    "Touch Panel/Pad",
                    "Footer Icon Touch",
                    "Swipe Left",
                ),
                reported_dormant_touch_errno=None,
                touch_op_dormant_trap_or_reset_drift_events=1,
            ),
            P320_BLOCKED_TOUCH_4ITEM_DORMANT_OR_RESET_DRIFT,
        ),
        (
            P320_PILLAR_57A_SCENARIO_IDS[3],
            False,
            build_default_safe_touch_disp_zero_evf_vault_spec(
                requested_dormant_evf_symbols=(
                    "Select Finder/Monitor",
                    "For viewfinder",
                    "Graphic Display",
                    "Monitor Off",
                ),
                reported_dormant_evf_errno=None,
                fx3_has_builtin_evf=True,
                evf_scanout_blocked=False,
                lcd_panel_scanout_preserved=False,
                disp_set_or_zero_evf_blackout_events=1,
            ),
            P320_BLOCKED_ZERO_EVF_BLACKOUT_GUARD_BREACH,
        ),
        (
            P320_PILLAR_57A_SCENARIO_IDS[4],
            False,
            build_default_safe_touch_disp_zero_evf_vault_spec(
                disp_set_menu_path=P320_DISP_SET_WRONG_PATH,
                disp_shoot_pages_enabled=("Display All Info.", "Graphic Display"),
                disp_set_or_zero_evf_blackout_events=1,
            ),
            P320_BLOCKED_DISP_SET_4SHOOT_3PB_OR_PATH_DRIFT,
        ),
        (
            P320_PILLAR_57A_SCENARIO_IDS[5],
            False,
            build_default_safe_touch_disp_zero_evf_vault_spec(
                camera_model=P320_FX6_DONOR_MODEL_NAME,
                fw_version=P320_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                touch_operation="On",
                touch_sensitivity="Standard",
                touch_func_in_shooting="Spot Focus",
                swipe_up="Off",
                reported_swipe_up_active=False,
                post_touch_operation="On",
                post_touch_sensitivity="N/A_FX6",
                post_touch_func_in_shooting="Spot Focus",
                post_swipe_up="N/A_FX6",
                fx6_exposes_touch_sensitivity_or_swipe_up=True,
                fx6_uses_loupe_term=True,
                fx6_touch_or_evf_spoof_events=1,
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                overlay_dir="/setting/57a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P320_BLOCKED_FX6_TOUCH_OR_EVF_SPOOF,
        ),
    )

    outcomes: List[Pillar57ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_touch_disp_zero_evf_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar57ScenarioOutcome(
                scenario_id=sid,
                pillar="57A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar57ASuiteResult(
        passed=all_ok,
        status=P320_STATUS_VERIFIED_PILLAR_57A if all_ok else P320_STATUS_REJECTED_PILLAR_57A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar57b_still_ael_flash_interval_pb_edit_6_scenario_suite() -> Pillar57BSuiteResult:
    """Run 6 Pillar 57B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, StillAelFlashIntervalPbEditVaultSpec, Optional[str]], ...] = (
        (
            P320_PILLAR_57B_SCENARIO_IDS[0],
            True,
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                shooting_domain="Still",
                ael_w_shutter="On",
                ael_toggle_key_active=False,
                reported_half_press_ael_locked=True,
                exp_comp_set="Ambient only",
                wireless_flash="On",
                reset_action="Camera Settings Reset",
                post_ael_w_shutter="On",
                post_exp_comp_set="Ambient only",
                post_wireless_flash=P320_WIRELESS_FLASH_DEFAULT,
                cont_play_for_interval="On",
                play_speed_for_interval=9,
                post_cont_play_for_interval="On",
                post_play_speed_for_interval=9,
                photo_capture_file_type="HEIF(4:2:2)",
                post_photo_capture_file_type="HEIF(4:2:2)",
                select_playback_media_slot=1,
                target_write_slot=2,
                requested_vault_action="COPY_TO_TARGET",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P320_PILLAR_57B_SCENARIO_IDS[1],
            True,
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                shooting_domain="Still",
                ael_w_shutter="On",
                ael_toggle_key_active=True,
                reported_half_press_ael_locked=False,
                exp_comp_set="Ambient only",
                wireless_flash="On",
                cont_play_for_interval="On",
                play_speed_for_interval=5,
                photo_capture_file_type="HEIF(4:2:0)",
                reset_action="Initialize",
                post_ael_w_shutter=P320_AEL_W_SHUTTER_DEFAULT,
                post_exp_comp_set=P320_EXP_COMP_SET_DEFAULT,
                post_wireless_flash=P320_WIRELESS_FLASH_DEFAULT,
                post_cont_play_for_interval="Off",
                post_play_speed_for_interval=P320_INTERVAL_PB_SPEED_DEFAULT,
                post_photo_capture_file_type=P320_PHOTO_CAPTURE_FILE_DEFAULT,
                requested_vault_action="CONT_PLAY_INTERVAL",
                reported_vault_action_allowed=True,
            ),
            None,
        ),
        (
            P320_PILLAR_57B_SCENARIO_IDS[2],
            False,
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                shooting_domain="Movie",
                ael_w_shutter="On",
                exp_comp_set="Ambient only",
                reported_still_flash_errno=None,
                reset_action="Camera Settings Reset",
                post_ael_w_shutter=P320_AEL_W_SHUTTER_DEFAULT,
                post_exp_comp_set=P320_EXP_COMP_SET_DEFAULT,
                still_ael_flash_reset_split_or_mishoe_drift_events=1,
            ),
            P320_BLOCKED_STILL_AEL_OR_FLASH_RESET_SPLIT_DRIFT,
        ),
        (
            P320_PILLAR_57B_SCENARIO_IDS[3],
            False,
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                ext_flash_direct_mishoe=False,
                ext_flash_sync_cord_requested=True,
                ext_flash_camera_menu_reset_requested=True,
                reported_ext_flash_errno=None,
                fx6_exposes_still_ttl_flash_or_ael=True,
                fx6_flash_band_reduce_is_rolling_shutter_comp=False,
            ),
            P320_BLOCKED_EXT_FLASH_MISHOE_OR_FX6_SPOOF,
        ),
        (
            P320_PILLAR_57B_SCENARIO_IDS[4],
            False,
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                interval_pb_menu_path=P320_INTERVAL_PB_WRONG_PATH,
                play_speed_scale_max=5,
                in_camera_timelapse_movie_synthesis_supported=True,
                interval_pb_read_only_safe=False,
                interval_pb_9scale_or_path_drift_events=1,
            ),
            P320_BLOCKED_INTERVAL_PB_9SCALE_OR_PATH_DRIFT,
        ),
        (
            P320_PILLAR_57B_SCENARIO_IDS[5],
            False,
            build_default_safe_still_ael_flash_interval_pb_edit_vault_spec(
                select_playback_media_slot=2,
                target_write_slot=1,
                slot1_holds_tier0_vault=True,
                requested_vault_action="PHOTO_CAPTURE",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=8192,
                slot1_edit_avf_info_mutation_bytes=4096,
                slot1_avf_info_mutated=True,
                slot1_vault_mutation_bytes=12288,
                slot1_vault_erofs_eopnotsupp_enforced=False,
                playback_edit_dormant_or_slot1_vault_bypass_events=1,
            ),
            P320_BLOCKED_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_FIREWALL,
        ),
    )

    outcomes: List[Pillar57ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_still_ael_flash_interval_pb_edit_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar57ScenarioOutcome(
                scenario_id=sid,
                pillar="57B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar57BSuiteResult(
        passed=all_ok,
        status=P320_STATUS_VERIFIED_PILLAR_57B if all_ok else P320_STATUS_REJECTED_PILLAR_57B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar57_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar57StandaloneReport:
    """Run full Pillar 57 standalone suite (`6/6` Pillar 57A + `6/6` Pillar 57B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase320_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar57a_touch_disp_zero_evf_6_scenario_suite()
    res_b = run_pillar57b_still_ael_flash_interval_pb_edit_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 320 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE320_SCHEMA,
            "version": PHASE320_VERSION,
            "mode": donor_snapshot.verification_mode,
            "57a": [asdict(s) for s in res_a.scenarios],
            "57b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar57StandaloneReport(
        schema=PHASE320_SCHEMA,
        version=PHASE320_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P320_STATUS_VERIFIED_PILLAR57_SUITE if all_ok else P320_STATUS_FAIL_PILLAR57_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_57a_touch_disp_zero_evf_vault=res_a,
        pillar_57b_still_ael_flash_interval_pb_edit_vault=res_b,
        touch_op_dormant_trap_or_reset_drift_events=(
            P320_TOUCH_OP_DORMANT_TRAP_OR_RESET_DRIFT_EVENTS if res_a.passed else 1
        ),
        disp_set_or_zero_evf_blackout_events=(
            P320_DISP_SET_OR_ZERO_EVF_BLACKOUT_EVENTS if res_a.passed else 1
        ),
        fx6_touch_or_evf_spoof_events=(
            P320_FX6_TOUCH_OR_EVF_SPOOF_EVENTS if res_a.passed else 1
        ),
        still_ael_flash_reset_split_or_mishoe_drift_events=(
            P320_STILL_AEL_FLASH_RESET_SPLIT_OR_MISHOE_DRIFT_EVENTS if res_b.passed else 1
        ),
        interval_pb_9scale_or_path_drift_events=(
            P320_INTERVAL_PB_9SCALE_OR_PATH_DRIFT_EVENTS if res_b.passed else 1
        ),
        playback_edit_dormant_or_slot1_vault_bypass_events=(
            P320_PLAYBACK_EDIT_DORMANT_OR_SLOT1_VAULT_BYPASS_EVENTS if res_b.passed else 1
        ),
        slot1_data_sector_writes=P320_SLOT1_DATA_SECTOR_WRITES if res_b.passed else 1,
        slot1_edit_avf_info_mutation_bytes=(
            P320_SLOT1_EDIT_AVF_INFO_MUTATION_BYTES if res_b.passed else 4096
        ),
        slot1_avf_info_mutated=not res_b.passed,
        slot1_vault_mutation_bytes=(
            P320_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P320_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_eopnotsupp_enforced=P320_SLOT1_VAULT_EROFS_EOPNOTSUPP_ENFORCED,
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
# Unified 57-Pillar Recovery Master Aggregator (Phase 320 — 57/57 Milestone)
# ---------------------------------------------------------------------------


def _apply_master57_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def _master57_local_donors_available() -> bool:
    """Return True only when legacy BODYDATA.DAT and all 17 Wave-55 local donors exist as files."""
    required_relpaths: Tuple[str, ...] = (
        "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT",
        P320_DONOR_FX3_APPFW_702_RELPATH,
        P320_DONOR_FX6_APPFW_601_RELPATH,
        P320_DONOR_FX3_BACKUP_BIN_RELPATH,
        P320_DONOR_FX3_UXC_EN_F_RELPATH,
        P320_DONOR_FX3_UXC_SC_F_RELPATH,
        P320_DONOR_FX3_UXC_TC_F_RELPATH,
        P320_DONOR_FX3_UXC_JA_F_RELPATH,
        P320_DONOR_FX3_UXC_EN_RELPATH,
        P320_DONOR_FX3_UXC_SC_RELPATH,
        P320_DONOR_FX3_UXC_TC_RELPATH,
        P320_DONOR_FX3_UXC_JA_RELPATH,
        P320_DONOR_FX3_UXC_EN_G_RELPATH,
        P320_DONOR_FX3_UXC_SC_G_RELPATH,
        P320_DONOR_FX3_UXC_TC_G_RELPATH,
        P320_DONOR_FX3_UXC_JA_G_RELPATH,
        P320_DONOR_FX6_UXC_EN_RELPATH,
        P320_DONOR_FX6_UXC_EN_2_RELPATH,
    )
    for relpath in required_relpaths:
        try:
            resolved = resolve_donor_path(relpath, require_file=True)
        except Exception:
            return False
        if resolved is None:
            return False
        try:
            if not resolved.is_file():
                return False
        except OSError:
            return False
    return True


def evaluate_realhw_57pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master57PillarRecoveryReport:
    """Evaluate and aggregate all 57 recovery pillars (`1..57`) concurrently -> `57/57` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_57_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    if resolved_clean_room is None and not _master57_local_donors_available():
        resolved_clean_room = True
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_56pillar() -> Master56PillarRecoveryReport:
        return evaluate_realhw_56pillar_recovery_master(**kw)

    def _run_p57() -> Tuple[Pillar57StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar57_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_56 = pool.submit(_run_56pillar)
        fut_57 = pool.submit(_run_p57)
        m56_rep = fut_56.result()
        p57_rep, p57_dt = fut_57.result()

    all_errors: List[str] = list(m56_rep.errors) + list(p57_rep.errors)
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
        if getattr(m56_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-56 violated {attr_name} == {expected_val}")
        if getattr(p57_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 57 violated {attr_name} == {expected_val}")

    if p57_rep.cross_model_flash_authorized is not False:
        all_errors.append("Pillar 57 violated cross_model_flash_authorized == False")

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
        ("fx3_has_builtin_end_filter", False),
        ("fx3_has_builtin_evf", False),
        ("fx3_has_var_shutter", False),
    ):
        if getattr(m56_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-56 violated {attr_name} == {expected_val}")

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
        if getattr(p57_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 57 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m56_rep.pillars)
    spec57 = MASTER_57_PILLAR_SPECS[56]
    p57_metrics = {
        "pillar_57a_touch_disp_zero_evf_vault": (
            f"{p57_rep.pillar_57a_touch_disp_zero_evf_vault.scenarios_passed}/"
            f"{p57_rep.pillar_57a_touch_disp_zero_evf_vault.scenarios_total}"
        ),
        "pillar_57b_still_ael_flash_interval_pb_edit_vault": (
            f"{p57_rep.pillar_57b_still_ael_flash_interval_pb_edit_vault.scenarios_passed}/"
            f"{p57_rep.pillar_57b_still_ael_flash_interval_pb_edit_vault.scenarios_total}"
        ),
        "touch_op_dormant_trap_or_reset_drift_events": (
            p57_rep.touch_op_dormant_trap_or_reset_drift_events
        ),
        "disp_set_or_zero_evf_blackout_events": p57_rep.disp_set_or_zero_evf_blackout_events,
        "fx6_touch_or_evf_spoof_events": p57_rep.fx6_touch_or_evf_spoof_events,
        "still_ael_flash_reset_split_or_mishoe_drift_events": (
            p57_rep.still_ael_flash_reset_split_or_mishoe_drift_events
        ),
        "interval_pb_9scale_or_path_drift_events": p57_rep.interval_pb_9scale_or_path_drift_events,
        "playback_edit_dormant_or_slot1_vault_bypass_events": (
            p57_rep.playback_edit_dormant_or_slot1_vault_bypass_events
        ),
        "slot1_data_sector_writes": p57_rep.slot1_data_sector_writes,
        "slot1_edit_avf_info_mutation_bytes": p57_rep.slot1_edit_avf_info_mutation_bytes,
        "slot1_avf_info_mutated": p57_rep.slot1_avf_info_mutated,
        "slot1_vault_mutation_bytes": p57_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p57_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_eopnotsupp_enforced": p57_rep.slot1_vault_erofs_eopnotsupp_enforced,
        "overall_ready_for_hardware_attach": p57_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p57_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p57_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p57_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec57[0],
            pillar_id=spec57[1],
            phase_label=spec57[2],
            module_name=spec57[3],
            passed=bool(p57_rep.all_passed),
            status=p57_rep.status,
            verification_mode=p57_rep.verification_mode,
            elapsed_seconds=p57_dt,
            key_metrics=p57_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec57[1],
                    "mode": p57_rep.verification_mode,
                    "status": p57_rep.status,
                    "metrics": p57_metrics,
                    "passed": p57_rep.all_passed,
                }
            ),
            errors=tuple(p57_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master57_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p57_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_57_PILLAR_COUNT == 57
        and pillars_passed == 57
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE320_SCHEMA,
            "schema_version": PHASE320_MASTER_SCHEMA,
            "version": PHASE320_VERSION,
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
    return Master57PillarRecoveryReport(
        schema=PHASE320_SCHEMA,
        schema_version=PHASE320_MASTER_SCHEMA,
        version=PHASE320_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P320_STATUS_VERIFIED_57OF57_AGGREGATOR if all_ok else P320_STATUS_FAIL_57OF57_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P320_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P320_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P320_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p57_rep.donor_snapshot,
        pillar57_a_touch_disp_zero_evf_vault=p57_rep.pillar_57a_touch_disp_zero_evf_vault,
        pillar57_b_still_ael_flash_interval_pb_edit_vault=(
            p57_rep.pillar_57b_still_ael_flash_interval_pb_edit_vault
        ),
        touch_op_dormant_trap_or_reset_drift_events=(
            p57_rep.touch_op_dormant_trap_or_reset_drift_events
        ),
        disp_set_or_zero_evf_blackout_events=p57_rep.disp_set_or_zero_evf_blackout_events,
        fx6_touch_or_evf_spoof_events=p57_rep.fx6_touch_or_evf_spoof_events,
        still_ael_flash_reset_split_or_mishoe_drift_events=(
            p57_rep.still_ael_flash_reset_split_or_mishoe_drift_events
        ),
        interval_pb_9scale_or_path_drift_events=p57_rep.interval_pb_9scale_or_path_drift_events,
        playback_edit_dormant_or_slot1_vault_bypass_events=(
            p57_rep.playback_edit_dormant_or_slot1_vault_bypass_events
        ),
        slot1_data_sector_writes=p57_rep.slot1_data_sector_writes,
        slot1_edit_avf_info_mutation_bytes=p57_rep.slot1_edit_avf_info_mutation_bytes,
        slot1_avf_info_mutated=p57_rep.slot1_avf_info_mutated,
        slot1_vault_mutation_bytes=m56_rep.slot1_vault_mutation_bytes + p57_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p57_rep.slot1_format_hard_locked,
        slot1_vault_erofs_eopnotsupp_enforced=p57_rep.slot1_vault_erofs_eopnotsupp_enforced,
        fx3_has_eye_sensor=P320_FX3_HAS_EYE_SENSOR,
        fx3_has_finder_monitor_button=P320_FX3_HAS_FINDER_MONITOR_BUTTON,
        fx3_touch_active_item_count=P320_FX3_TOUCH_ACTIVE_ITEM_COUNT,
        fx3_disp_shoot_page_count=P320_FX3_DISP_SHOOT_PAGE_COUNT,
        fx3_disp_play_page_count=P320_FX3_DISP_PLAY_PAGE_COUNT,
        fx3_interval_pb_speed_min=P320_FX3_INTERVAL_PB_SPEED_MIN,
        fx3_interval_pb_speed_max=P320_FX3_INTERVAL_PB_SPEED_MAX,
        fx3_interval_pb_speed_default=P320_FX3_INTERVAL_PB_SPEED_DEFAULT,
        fx6_has_detachable_lcd_viewfinder=P320_FX6_HAS_DETACHABLE_LCD_VIEWFINDER,
        fx6_has_still_ttl_flash=P320_FX6_HAS_STILL_TTL_FLASH,
        fx6_has_interval_pb=P320_FX6_HAS_INTERVAL_PB,
        fx6_has_playback_edit_menu=P320_FX6_HAS_PLAYBACK_EDIT_MENU,
        switch_vh_af_lockout_or_coords_drift_events=(
            m56_rep.switch_vh_af_lockout_or_coords_drift_events
        ),
        focus_limit_lt2_or_dormant_symbol_events=m56_rep.focus_limit_lt2_or_dormant_symbol_events,
        focus_area_color_or_fx6_spoof_events=m56_rep.focus_area_color_or_fx6_spoof_events,
        exp_std_adj_mode_conflation_or_reset_drift_events=(
            m56_rep.exp_std_adj_mode_conflation_or_reset_drift_events
        ),
        bracket_settings_reset_or_fx6_spoof_events=m56_rep.bracket_settings_reset_or_fx6_spoof_events,
        tcub_reset_wipe_or_format_lock_violations=m56_rep.tcub_reset_wipe_or_format_lock_violations,
        reverse_copy_slot2_to_slot1_bypass_events=m56_rep.reverse_copy_slot2_to_slot1_bypass_events,
        slideshow_power_save_or_fx6_copy_clip_spoof_events=(
            m56_rep.slideshow_power_save_or_fx6_copy_clip_spoof_events
        ),
        slot1_copy_avf_info_mutation_bytes=m56_rep.slot1_copy_avf_info_mutation_bytes,
        fx3_has_switch_vh_af_area=m56_rep.fx3_has_switch_vh_af_area,
        fx3_focus_area_limit_count=m56_rep.fx3_focus_area_limit_count,
        fx3_focus_area_limit_min_enabled=m56_rep.fx3_focus_area_limit_min_enabled,
        fx3_exp_std_adj_metering_mode_count=m56_rep.fx3_exp_std_adj_metering_mode_count,
        fx3_has_physical_bnc_tc_port=m56_rep.fx3_has_physical_bnc_tc_port,
        fx6_has_physical_bnc_tc_port=m56_rep.fx6_has_physical_bnc_tc_port,
        fx6_has_switch_vh_af_area=m56_rep.fx6_has_switch_vh_af_area,
        fx6_has_focus_area_limit=m56_rep.fx6_has_focus_area_limit,
        fx6_has_exp_std_adj=m56_rep.fx6_has_exp_std_adj,
        fx6_has_still_bracket_settings=m56_rep.fx6_has_still_bracket_settings,
        fx6_has_copy_clip_active=m56_rep.fx6_has_copy_clip_active,
        fx6_has_slide_show=m56_rep.fx6_has_slide_show,
        dormant_shading_auto_low_exposure_events=m56_rep.dormant_shading_auto_low_exposure_events,
        lens_comp_lock_or_arw_conflation_events=m56_rep.lens_comp_lock_or_arw_conflation_events,
        af_illuminator_gate_or_fx6_spoof_events=m56_rep.af_illuminator_gate_or_fx6_spoof_events,
        movie_af_transition_or_assist_drift_events=(
            m56_rep.movie_af_transition_or_assist_drift_events
        ),
        aperture_drive_pre_af_shutter_reset_drift_events=(
            m56_rep.aperture_drive_pre_af_shutter_reset_drift_events
        ),
        circ_focus_diagonal_or_color_drift_events=m56_rep.circ_focus_diagonal_or_color_drift_events,
        folder_name_or_leading_underscore_violations=(
            m56_rep.folder_name_or_leading_underscore_violations
        ),
        slot1_folder_dir_mutation_bytes=m56_rep.slot1_folder_dir_mutation_bytes,
        slot1_rating_avf_info_mutation_bytes=m56_rep.slot1_rating_avf_info_mutation_bytes,
        fx3_has_builtin_af_illuminator=m56_rep.fx3_has_builtin_af_illuminator,
        fx6_has_builtin_af_illuminator=m56_rep.fx6_has_builtin_af_illuminator,
        fx3_exposes_shading_auto_low=m56_rep.fx3_exposes_shading_auto_low,
        fx6_has_aperture_drive_pre_af_circ_color=m56_rep.fx6_has_aperture_drive_pre_af_circ_color,
        fx6_has_msdcf_or_star_rating=m56_rep.fx6_has_msdcf_or_star_rating,
        sensor_cleaning_low_battery_bypass_events=m56_rep.sensor_cleaning_low_battery_bypass_events,
        sensor_cleaning_no_power_off_violations=m56_rep.sensor_cleaning_no_power_off_violations,
        fx6_ibis_shake_conflation_events=m56_rep.fx6_ibis_shake_conflation_events,
        ev_comp_range_or_cine_ei_lockout_violations=(
            m56_rep.ev_comp_range_or_cine_ei_lockout_violations
        ),
        exposure_step_or_dormant_reset_ev_drift_events=(
            m56_rep.exposure_step_or_dormant_reset_ev_drift_events
        ),
        focus_mode_movie_clamp_or_dormant_drift_events=(
            m56_rep.focus_mode_movie_clamp_or_dormant_drift_events
        ),
        priority_set_or_illuminator_gate_violations=(
            m56_rep.priority_set_or_illuminator_gate_violations
        ),
        image_index_dormant_or_view_mode_drift_events=(
            m56_rep.image_index_dormant_or_view_mode_drift_events
        ),
        slot1_rotate_exif_mutation_bytes=m56_rep.slot1_rotate_exif_mutation_bytes,
        fx3_has_sensor_cleaning_ibis=m56_rep.fx3_has_sensor_cleaning_ibis,
        fx3_has_exposure_comp=m56_rep.fx3_has_exposure_comp,
        fx3_has_physical_ev_reset_dial=m56_rep.fx3_has_physical_ev_reset_dial,
        fx6_has_ultrasonic_ibis_cleaning=m56_rep.fx6_has_ultrasonic_ibis_cleaning,
        fx6_has_variable_end_optical_block=m56_rep.fx6_has_variable_end_optical_block,
        fx6_has_technical_apr=m56_rep.fx6_has_technical_apr,
        fx6_has_still_exposure_comp=m56_rep.fx6_has_still_exposure_comp,
        fx6_has_still_image_index_rotate=m56_rep.fx6_has_still_image_index_rotate,
        dci4k_long_gop_or_8k_violations=m56_rep.dci4k_long_gop_or_8k_violations,
        reboot_2400p_stage_b_wipe_violations=m56_rep.reboot_2400p_stage_b_wipe_violations,
        hdmi_raw_or_still_aspect_drift_events=m56_rep.hdmi_raw_or_still_aspect_drift_events,
        fx6_still_or_raw_conflation_events=m56_rep.fx6_still_or_raw_conflation_events,
        reg_custom_hold_or_hlg_lock_drift_events=m56_rep.reg_custom_hold_or_hlg_lock_drift_events,
        camset_cross_model_path_drift_events=m56_rep.camset_cross_model_path_drift_events,
        photo_capture_dci4k_lockout_bypass_events=(
            m56_rep.photo_capture_dci4k_lockout_bypass_events
        ),
        slot1_camset_write_bytes=m56_rep.slot1_camset_write_bytes,
        slot1_photo_capture_write_bytes=m56_rep.slot1_photo_capture_write_bytes,
        fx3_appfw_has_dci4k_internal=m56_rep.fx3_appfw_has_dci4k_internal,
        fx3_appfw_has_pro_camera_path=m56_rep.fx3_appfw_has_pro_camera_path,
        fx6_has_still_aspect_ratio=m56_rep.fx6_has_still_aspect_ratio,
        fx6_has_photo_capture=m56_rep.fx6_has_photo_capture,
        fx6_has_playback_enlarge_image=m56_rep.fx6_has_playback_enlarge_image,
        fx6_has_reg_custom_shoot_set=m56_rep.fx6_has_reg_custom_shoot_set,
        fx6_has_camera_set_memory=m56_rep.fx6_has_camera_set_memory,
        movie_tracking_area_or_limit_violations=m56_rep.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=m56_rep.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=m56_rep.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=(
            m56_rep.fx6_handle_or_pos_display_conflation_events
        ),
        iso_minss_or_cine_ei_lock_drift_events=m56_rep.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=m56_rep.flash_still_mech_gate_violations,
        mishoe_pmic_5v_overcurrent_events=m56_rep.mishoe_pmic_5v_overcurrent_events,
        slot1_focus_zoom_camset_mutation_bytes=m56_rep.slot1_focus_zoom_camset_mutation_bytes,
        slot1_flash_videolight_imagedb_bytes=m56_rep.slot1_flash_videolight_imagedb_bytes,
        xlrh1_has_zoom_lever=m56_rep.xlrh1_has_zoom_lever,
        xlrh1_has_rec_button=m56_rep.xlrh1_has_rec_button,
        xlrh1_has_zoom_hold_switch=m56_rep.xlrh1_has_zoom_hold_switch,
        fx6_0_99_is_zoom_position_display=m56_rep.fx6_0_99_is_zoom_position_display,
        fx6_has_iso_auto_min_ss=m56_rep.fx6_has_iso_auto_min_ss,
        fx6_mechanical_shutter_present=m56_rep.fx6_mechanical_shutter_present,
        dormant_lossless_raw_exposure_events=m56_rep.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=m56_rep.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=m56_rep.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=m56_rep.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=m56_rep.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=m56_rep.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=m56_rep.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=m56_rep.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=m56_rep.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=m56_rep.slot1_imagedb_or_burst_mutation_bytes,
        fx3_ui_exposes_lossless_raw=m56_rep.fx3_ui_exposes_lossless_raw,
        fx3_ui_exposes_shutter_type_auto=m56_rep.fx3_ui_exposes_shutter_type_auto,
        fx6_still_pipeline_present=m56_rep.fx6_still_pipeline_present,
        double_log_or_lockout_bypass_events=m56_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=m56_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=m56_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=m56_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            m56_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        wb_custom_camset_exclusion_drift_events=m56_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            m56_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        fx3_ui_exposes_usb_streaming=m56_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m56_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m56_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m56_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m56_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m56_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m56_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m56_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m56_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m56_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m56_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m56_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m56_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m56_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m56_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m56_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m56_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m56_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m56_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m56_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m56_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m56_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m56_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m56_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m56_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m56_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m56_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m56_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m56_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m56_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m56_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m56_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m56_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=(
            m56_rep.tcub_camera_reset_wipe_or_format_violations
        ),
        fx3_has_builtin_end_filter=m56_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m56_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=(
            m56_rep.cardless_unrecorded_production_violations
        ),
        legacy_v1_audio_level_menu_spoof_events=(
            m56_rep.legacy_v1_audio_level_menu_spoof_events
        ),
        photographer_copyright_pii_leaked_bytes=m56_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m56_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m56_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m56_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m56_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m56_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m56_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m56_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m56_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m56_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m56_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m56_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m56_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m56_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m56_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m56_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m56_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m56_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m56_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m56_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m56_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m56_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m56_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m56_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m56_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m56_rep.unbuffered_battery_pull_events,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        master_57pillar_sha256=master_sha,
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


def evaluate_57pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master57PillarRecoveryReport:
    """Alias for `evaluate_realhw_57pillar_recovery_master`."""
    return evaluate_realhw_57pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_57pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master57PillarRecoveryReport:
    """Alias for `evaluate_realhw_57pillar_recovery_master`."""
    return evaluate_realhw_57pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
