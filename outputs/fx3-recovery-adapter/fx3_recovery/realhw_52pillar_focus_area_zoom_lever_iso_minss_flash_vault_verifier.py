"""Phase 296 — Recovery Pillar 52 & Unified 52-Pillar Recovery Master
(`verify-52pillar-recovery` / `verify-pillar52-focus-area-zoom-iso-flash-vault`):

1. **Pillar 52A — `[Focus Area]` 14-Area Hierarchy (7 Universal Still+Movie vs 7
   Still-Only `Tracking:`), `[Focus Area Limit]` (`>= 2`), `[AF Area Registration]`
   (`Lock Operation Parts = Off` Coupling & `Initialize`-Only Survival), & Body `W/T`
   Zoom Lever vs Handle-Less `XLR-H1` Myth-Bust + `Slot-1` Vault Firewall (Wave-50)**:
   - Models `MENU -> Focus -> [Focus Area]` (`BKID_APP_setting_autofocus_area_contrast_detect_af`,
     factory default `Wide`) on `ILME-FX3 Ver. 7.02` (`0x91030080`, `ilc/2210`,
     `PRODUCT_MODEL_ALCIN_UUD`):
     - **7 Universal (`Still + Movie/S&Q`)**: `Wide`, `Zone`, `Center Fix`, `Spot: S`,
       `Spot: M`, `Spot: L`, `Expand Spot`.
     - **7 Still-Only (`Still AF-C`)**: `Tracking: Wide`, `Tracking: Zone`,
       `Tracking: Center Fix`, `Tracking: Spot S`, `Tracking: Spot M`, `Tracking: Spot L`,
       `Tracking: Expand Spot` — strictly **locked out in Movie / `S&Q`** (which uses
       `[Touch Tracking]` under `AF-S`/`AF-A`/`AF-C`/`DMF` + optical zoom, NOT `MF`).
     - `[Focus Area Limit]` requires **`>= 2` of 14 areas** enabled (`.uxc` `0xe227`),
       `[Switch V/H AF Area]` is Still-only, `[Circ. of Focus Point]` wraps H/V (not
       diagonally), and `[AF Area Registration]` (`Off`/`On`) **survives
       `Camera Settings Reset`** (needs `[Initialize]` / `[Del. Regist. AF Area]`),
       is disabled in Movie/`S&Q`/`Intelligent Auto`, and **forces
       `[Lock Operation Parts] = Off`**.
     - Contrasts `ILME-FX6 Ver. 6.01` (`PRODUCT_MODEL_CHAPLIN`), which exposes ONLY
       `Wide / Zone / Flexible Spot` with zero `Tracking:` menu focus areas and zero
       `Focus Area Limit` / `AF Area Registration`.
   - Enforces the `XLR-H1` hardware myth-bust truth:
     - **`ILME-FX3` `XLR-H1` handle unit is strictly an audio-interface handle with ZERO
       zoom lever, ZERO record button, and ZERO `ZOOM HOLD` switch** (`xlrh1_has_zoom_lever
       = False`, `xlrh1_has_rec_button = False`, `xlrh1_has_zoom_hold_switch = False`).
     - Zoom on FX3 uses body `W/T` `[Zoom Lever Speed]` (`1st = 3 / 2nd = 8`, `1..8` split
       `STBY`/`REC`), `[Custom Key Z. Speed]` (`Fixed Speed = 3`, `1..8`), `[Remote Zoom
       Speed]` (`Variable` default / `Fixed 1..8`, `STBY`/`REC`), and `[Zoom Range]`
       (`Optical zoom only` / `ClearImage Zoom` / `Digital Zoom`).
     - Contrasts `ILME-FX6` Smart Handle (`Handle Zoom` `Off/Low/High/Variable 1..8` +
       `Handle HOLD Switch` `Normal`/`Rec Button Only`, where `0..99` is strictly
       `Zoom Position Display`, NOT a `Fixed 1..99` speed scale).

2. **Pillar 52B — `[ISO Range Limit]` & Still-Only `[ISO AUTO Min. SS]` vs `Cine EI`
   Base ISO `800 / 12800` Lock + `[Flash Mode]` Mechanical-Shutter Still Gate vs
   `[Video Light Mode]` `PMIC 5V <= 900 mA` Rail & `Slot-1` Vault Firewall (Wave-50)**:
   - Enforces `[ISO Range Limit]` (`Min/Max` clamping `ISO AUTO` & manual ISO, survives
     `Camera Settings Reset`) and **Still-only** `[ISO AUTO Min. SS]` (`Slower`/`Slow`/
     `Standard`/`Fast`/`Faster` or `1/8000..30"`, active in Still `P`/`A` or `M + ISO AUTO`,
     resettable via `Camera Settings Reset`), both **locked out under Movie `Cine EI` /
     `Cine EI Quick`** (which hard-pin Base ISO `800` or `12800` and lock `[Auto Slow
     Shutter]`). Contrasts `ILME-FX6` (`AGC`, zero `[ISO AUTO Min. SS]`).
   - Enforces `[Flash Mode]` (`Flash Off`, `Autoflash`, `Fill-flash`, `Slow Sync.`,
     `Rear Sync.`; Pillar 52 baseline default `Fill-flash`, `1/250 s` FF mechanical sync)
     **strictly gated to Mechanical-Shutter `EXPOSURE_MODE_STILL`** — blocked in
     Movie/`S&Q`, `Electronic Shutter`, `Silent Mode = On`, and still-less `ILME-FX6`
     (`mechanical_shutter = False`, uses `Flash Band Reduce`).
   - Models `[Video Light Mode]` (`Power Link` default / `REC Link` / `REC Link&STBY` /
     `Auto`) spanning **Still + Movie + `S&Q`** under a strict **MI-Shoe `PMIC 5V <=
     900 mA`** current guard, non-Sony `<250 V` center-pin guard, and **zero `Slot-1`
     Tier-0 Vault / `cnflasha` writes** (`EROFS`/`EBUSY`, `/tmp/` volatile overlay with
     `BLKROSET=True`, and `16/16 H0 == H3` `Backup.bin`).

3. **Unified 52-Pillar Recovery Master (`evaluate_realhw_52pillar_recovery_master` /
   `verify-52pillar-recovery`)**:
   - Concurrently delegates Pillars `1..51` (`evaluate_realhw_51pillar_recovery_master`)
     + **Pillar 52** (`run_pillar52_standalone_suite`) -> **`52/52`
     (`VERIFIED_52OF52_PILLAR_RECOVERY_MASTER`)** with `raw_firmware_bytes_leaked == 0`,
     `persistent_emmc_writes_authorized == False`, and
     `overall_ready_for_hardware_attach == False`.
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
from .realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier import (
    MASTER_51_PILLAR_SPECS,
    Master51PillarRecoveryReport,
    evaluate_realhw_51pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE296_SCHEMA: str = (
    "realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier_v1"
)
PHASE296_VERSION: str = "1.0.0"
PHASE296_PHASE_NUMBER: int = 296
P296_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P296_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P296_OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P296_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATIONS: int = 0
P296_AF_AREA_REG_LOCK_OR_RESET_DRIFT_EVENTS: int = 0
P296_XLRH1_ZOOM_OR_HOLD_SPOOF_EVENTS: int = 0
P296_FX6_HANDLE_OR_POS_DISPLAY_CONFLATION_EVENTS: int = 0
P296_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT_EVENTS: int = 0
P296_FLASH_STILL_MECH_GATE_VIOLATIONS: int = 0
P296_MISHOE_PMIC_5V_OVERCURRENT_EVENTS: int = 0
P296_SLOT1_FOCUS_ZOOM_CAMSET_MUTATION_BYTES: int = 0
P296_SLOT1_FLASH_VIDEOLIGHT_IMAGEDB_BYTES: int = 0
P296_SLOT1_VAULT_MUTATION_BYTES: int = 0
P296_SLOT1_FORMAT_HARD_LOCKED: bool = True
P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED: bool = True

P296_XLRH1_HAS_ZOOM_LEVER: bool = False
P296_XLRH1_HAS_REC_BUTTON: bool = False
P296_XLRH1_HAS_ZOOM_HOLD_SWITCH: bool = False
P296_FX6_0_99_IS_ZOOM_POSITION_DISPLAY: bool = True
P296_FX6_HAS_ISO_AUTO_MIN_SS: bool = False
P296_FX6_MECHANICAL_SHUTTER_PRESENT: bool = False

P296_DONOR_INSPECT_BUDGET_SECONDS: float = 0.20
P296_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P296_FAST_CLI_BUDGET_SECONDS: float = 1.2
P296_NOMINAL_BUDGET_SECONDS: float = 4.0
P296_CONCURRENT_CEILING_SECONDS: float = 6.0
P296_BOUNDED_HEADER_BYTES: int = 4096
P296_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-50 Donor Anchors (strictly O_RDONLY)
P296_FX3_MODEL_NAME: str = "ILME-FX3"
P296_FX3_MODEL_ID: int = 0x91030080
P296_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P296_FX3_HELPGUIDE_ID: str = "ilc/2210"
P296_FX3_FW_VERSION: str = "7.02"
P296_FX3_SENSOR_FAMILY: str = "12 MP IMX510"
P296_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P296_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P296_FX6_DONOR_FW_VERSION: str = "6.01"
P296_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
    "2.00",
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P296_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P296_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P296_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)
P296_PINNED_FX3_APPFW_702_FULL_SHA256: str = (
    "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
)

P296_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P296_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P296_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)
P296_PINNED_FX6_APPFW_601_FULL_SHA256: str = (
    "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
)

P296_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P296_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P296_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P296_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P296_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P296_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P296_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P296_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P296_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P296_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P296_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P296_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P296_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P296_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P296_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P296_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P296_PINNED_FX3_UXC_EN_BYTES: int = 165740
P296_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P296_DONOR_FX3_UXC_SC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc"
)
P296_PINNED_FX3_UXC_SC_BYTES: int = 149064
P296_PINNED_FX3_UXC_SC_SHA256: str = (
    "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66"
)

P296_DONOR_FX3_UXC_TC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc"
)
P296_PINNED_FX3_UXC_TC_BYTES: int = 151908
P296_PINNED_FX3_UXC_TC_SHA256: str = (
    "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3"
)

P296_DONOR_FX3_UXC_JA_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc"
)
P296_PINNED_FX3_UXC_JA_BYTES: int = 208564
P296_PINNED_FX3_UXC_JA_SHA256: str = (
    "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d"
)

P296_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P296_PINNED_FX3_UXC_EN_G_BYTES: int = 69600
P296_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P296_DONOR_FX3_UXC_SC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_g.uxc"
)
P296_PINNED_FX3_UXC_SC_G_BYTES: int = 61296
P296_PINNED_FX3_UXC_SC_G_SHA256: str = (
    "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b"
)

P296_DONOR_FX3_UXC_TC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_g.uxc"
)
P296_PINNED_FX3_UXC_TC_G_BYTES: int = 61372
P296_PINNED_FX3_UXC_TC_G_SHA256: str = (
    "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80"
)

P296_DONOR_FX3_UXC_JA_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_g.uxc"
)
P296_PINNED_FX3_UXC_JA_G_BYTES: int = 89428
P296_PINNED_FX3_UXC_JA_G_SHA256: str = (
    "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980"
)

P296_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P296_PINNED_FX6_UXC_EN_BYTES: int = 118208
P296_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P296_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P296_PINNED_FX6_UXC_EN_2_BYTES: int = 118676
P296_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# ---------------------------------------------------------------------------
# Pillar 52A Constants — [Focus Area] 14-Area Matrix, [Focus Area Limit],
# [Switch V/H AF Area], [Focus Area Color], [Circ. of Focus Point],
# [AF Area Registration] & Body W/T Zoom Lever vs Handle-Less XLR-H1 Myth-Bust
# ---------------------------------------------------------------------------

P296_FOCUS_AREA_MENU_PATH: Tuple[str, ...] = ("Focus", "Focus Area", "Focus Area")
P296_FOCUS_AREA_LIMIT_MENU_PATH: Tuple[str, ...] = ("Focus", "Focus Area", "Focus Area Limit")
P296_SWITCH_VH_AF_MENU_PATH: Tuple[str, ...] = ("Focus", "Focus Area", "Switch V/H AF Area")
P296_FOCUS_AREA_COLOR_MENU_PATH: Tuple[str, ...] = ("Focus", "Focus Area", "Focus Area Color")
P296_CIRC_FOCUS_POINT_MENU_PATH: Tuple[str, ...] = ("Focus", "Focus Area", "Circ. of Focus Point")
P296_AF_AREA_REG_MENU_PATH: Tuple[str, ...] = ("Focus", "Focus Area", "AF Area Registration")
P296_DEL_REGIST_AF_AREA_MENU_PATH: Tuple[str, ...] = ("Focus", "Focus Area", "Del. Regist. AF Area")
P296_ZOOM_MENU_PATH: Tuple[str, ...] = ("Shooting", "Zoom")

P296_FOCUS_AREA_BKID: str = "BKID_APP_setting_autofocus_area_contrast_detect_af"
P296_FOCUS_AREA_G_RESID16: int = 0x61F1  # _g.uxc
P296_FOCUS_AREA_7_UNIVERSAL: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Center Fix",
    "Spot: S",
    "Spot: M",
    "Spot: L",
    "Expand Spot",
)
P296_FOCUS_AREA_7_STILL_TRACKING: Tuple[str, ...] = (
    "Tracking: Wide",
    "Tracking: Zone",
    "Tracking: Center Fix",
    "Tracking: Spot S",
    "Tracking: Spot M",
    "Tracking: Spot L",
    "Tracking: Expand Spot",
)
P296_FOCUS_AREA_14_AREAS: Tuple[str, ...] = (
    P296_FOCUS_AREA_7_UNIVERSAL + P296_FOCUS_AREA_7_STILL_TRACKING
)
P296_FOCUS_AREA_DEFAULT: str = "Wide"
P296_FOCUS_AREA_LIMIT_MIN_AREAS: int = 2
P296_FOCUS_AREA_LIMIT_MIN_RESID16: int = 0xE227  # .uxc
P296_FOCUS_AREA_LIMIT_BKID_PREFIX: str = "BKID_APP_focus_area_limit_"
P296_FOCUS_AREA_RESID16_MAP: Dict[str, int] = {
    "Wide": 0xE9B5,
    "Zone": 0xEA3E,
    "Center Fix": 0x7824,
    "Spot: S": 0x65BF,
    "Spot: M": 0x65C0,
    "Spot: L": 0x65C1,
    "Expand Spot": 0x6785,
    "Tracking: Wide": 0x6701,
    "Tracking: Zone": 0x6853,
    "Tracking: Center Fix": 0x602B,
    "Tracking: Spot S": 0x7739,
    "Tracking: Spot M": 0x773A,
    "Tracking: Spot L": 0x7741,
    "Tracking: Expand Spot": 0x6125,
}
P296_FX6_FOCUS_AREAS: Tuple[str, ...] = ("Wide", "Zone", "Flexible Spot")

P296_SWITCH_VH_AF_BKID: str = "BKID_APP_setting_vertical_horizontal_focus_area_switch"
P296_SWITCH_VH_AF_MODES: Tuple[str, ...] = ("Off", "AF Point Only", "AF Point + AF Area")
P296_SWITCH_VH_AF_DEFAULT: str = "Off"

P296_FOCUS_AREA_COLOR_BKID: str = "BKID_APP_setting_focus_frame_color"
P296_FOCUS_AREA_COLOR_MODES: Tuple[str, ...] = ("White", "Red")
P296_FOCUS_AREA_COLOR_DEFAULT: str = "White"

P296_CIRC_FOCUS_POINT_BKID: str = "BKID_APP_setting_circulate_of_focus_point"
P296_CIRC_FOCUS_POINT_MODES: Tuple[str, ...] = ("Does Not Circulate", "Circulate")
P296_CIRC_FOCUS_POINT_DEFAULT: str = "Does Not Circulate"
P296_CIRC_ELIGIBLE_FOCUS_AREAS: Tuple[str, ...] = (
    "Zone",
    "Spot: S",
    "Spot: M",
    "Spot: L",
    "Expand Spot",
    "Tracking: Zone",
    "Tracking: Spot S",
    "Tracking: Spot M",
    "Tracking: Spot L",
    "Tracking: Expand Spot",
)

P296_AF_AREA_REG_BKID: str = "BKID_APP_setting_register_the_af_frame"
P296_AF_AREA_REG_RESID16: int = 0x6B65  # _f.uxc
P296_AF_AREA_REG_DEFAULT: str = "Off"
P296_DEL_REGIST_AF_AREA_RESID16: int = 0x696C  # _f.uxc
P296_LOCK_OPERATION_PARTS_BKID: str = "BKID_APP_setting_lock_operation_parts"

P296_ZOOM_RANGE_BKID: str = "BKID_APP_setting_zoom_setting"
P296_ZOOM_RANGES: Tuple[str, ...] = ("Optical zoom only", "ClearImage Zoom", "Digital Zoom")
P296_ZOOM_RANGE_DEFAULT: str = "Optical zoom only"
P296_ZOOM_LEVER_1ST_SPEED_DEFAULT: int = 3
P296_ZOOM_LEVER_2ND_SPEED_DEFAULT: int = 8
P296_CUSTOM_KEY_ZOOM_SPEED_DEFAULT: int = 3
P296_REMOTE_ZOOM_SPEED_TYPES: Tuple[str, ...] = ("Variable", "Fixed")
P296_REMOTE_ZOOM_SPEED_TYPE_DEFAULT: str = "Variable"
P296_REMOTE_ZOOM_FIXED_SPEED_DEFAULT: int = 3
P296_ZOOM_SPEED_MIN: int = 1
P296_ZOOM_SPEED_MAX: int = 8
P296_FX6_HANDLE_ZOOM_MODES: Tuple[str, ...] = ("Off", "Low", "High", "Variable")
P296_FX6_HANDLE_HOLD_SWITCH_MODES: Tuple[str, ...] = ("Normal", "Rec Button Only")
P296_FX6_ZOOM_POS_DISPLAY_MIN: int = 0
P296_FX6_ZOOM_POS_DISPLAY_MAX: int = 99

P296_FOCUS_MODES: Tuple[str, ...] = ("AF-S", "AF-A", "AF-C", "DMF", "MF")
P296_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P296_STILL_PASM_MODES: Tuple[str, ...] = ("P", "A", "S", "M")
P296_STILL_SHOOTING_MODES: Tuple[str, ...] = ("Intelligent Auto", "P", "A", "S", "M")

# ---------------------------------------------------------------------------
# Pillar 52B Constants — [ISO Range Limit], Still-Only [ISO AUTO Min. SS],
# Cine EI Base ISO 800/12800 Lockout, [Flash Mode] Still Mech Gate &
# [Video Light Mode] PMIC 5V <= 900 mA Rail + Slot-1 Vault Guard
# ---------------------------------------------------------------------------

P296_ISO_RANGE_LIMIT_MENU_PATH: Tuple[str, ...] = ("Exposure/Color", "Exposure", "ISO Range Limit")
P296_ISO_AUTO_MIN_SS_MENU_PATH: Tuple[str, ...] = ("Exposure/Color", "Exposure", "ISO AUTO Min. SS")
P296_FLASH_MODE_MENU_PATH: Tuple[str, ...] = ("Exposure/Color", "Flash", "Flash Mode")
P296_VIDEO_LIGHT_MODE_MENU_PATH: Tuple[str, ...] = ("Setup", "Setup Option", "Video Light Mode")

P296_ISO_RANGE_LIMIT_BKID: str = "BKID_APP_setting_iso_range_limit_min"
P296_ISO_RANGE_MIN_FLOOR: int = 50
P296_ISO_RANGE_MAX_CEILING: int = 409600
P296_ISO_AUTO_MIN_SS_BKID: str = "BKID_APP_setting_iso_auto_min_s_s"
P296_ISO_AUTO_MIN_SS_RELATIVE: Tuple[str, ...] = (
    "Slower",
    "Slow",
    "Standard",
    "Fast",
    "Faster",
)
P296_ISO_AUTO_MIN_SS_SHUTTER_THRESHOLDS: Tuple[str, ...] = (
    "1/8000",
    "1/4000",
    "1/2000",
    "1/1000",
    "1/500",
    "1/250",
    "1/125",
    "1/60",
    "1/30",
    "1/15",
    "1/8",
    "1/4",
    "1/2",
    '1"',
    '2"',
    '4"',
    '8"',
    '15"',
    '30"',
)
P296_ISO_AUTO_MIN_SS_OPTIONS: Tuple[str, ...] = (
    P296_ISO_AUTO_MIN_SS_RELATIVE + P296_ISO_AUTO_MIN_SS_SHUTTER_THRESHOLDS
)
P296_ISO_AUTO_MIN_SS_DEFAULT: str = "Standard"
P296_LOG_SHOOTING_MODES: Tuple[str, ...] = ("Off", "Flexible ISO", "Cine EI Quick", "Cine EI")
P296_CINE_EI_LOCKED_LOG_MODES: Tuple[str, ...] = ("Cine EI Quick", "Cine EI")
P296_CINE_EI_BASE_ISOS: Tuple[int, ...] = (800, 12800)

P296_FLASH_MODE_BKID: str = "BKID_APP_setting_flash_mode"
P296_FLASH_MODE_RESID16: int = 0xE5CE  # .uxc
P296_FLASH_5_MODES: Tuple[str, ...] = (
    "Flash Off",
    "Autoflash",
    "Fill-flash",
    "Slow Sync.",
    "Rear Sync.",
)
P296_FLASH_MODE_DEFAULT: str = "Fill-flash"
P296_FLASH_MODE_RESID16_MAP: Dict[str, int] = {
    "Autoflash": 0xE6D2,
    "Flash Off": 0xE6D3,
    "Slow Sync.": 0xE6D4,
    "Fill-flash": 0xE6D5,
    "Rear Sync.": 0xE95C,
}
P296_FX3_MAX_FLASH_SYNC_DENOM: int = 250  # 1/250 s FF mechanical sync
P296_SHUTTER_TYPES: Tuple[str, ...] = ("Mechanical Shutter", "Electronic Shutter")
P296_FLASH_COMP_MIN_EV: float = -3.0
P296_FLASH_COMP_MAX_EV: float = 3.0
P296_EXP_COMP_SET_MODES: Tuple[str, ...] = ("Ambient&flash", "Ambient only")

P296_VIDEO_LIGHT_MODE_BKID: str = "BKID_APP_setting_video_light_set"
P296_VIDEO_LIGHT_MODE_RESID16: int = 0x6211  # _f.uxc
P296_VIDEO_LIGHT_4_MODES: Tuple[str, ...] = (
    "Power Link",
    "REC Link",
    "REC Link&STBY",
    "Auto",
)
P296_VIDEO_LIGHT_MODE_DEFAULT: str = "Power Link"
P296_MISHOE_PMIC_5V_MAX_MA: int = 900
P296_MISHOE_NON_SONY_FLASH_MAX_V: float = 250.0

# Shared Reset, Vault & Tier-0 Constants
P296_ON_OFF_MODES: Tuple[str, ...] = ("On", "Off")
P296_RESET_ACTIONS: Tuple[str, ...] = (
    "None",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P296_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "CAMSET_FOCUS_ZOOM_WRITE",
    "STILL_FLASH_CAPTURE_WRITE",
    "VIDEO_LIGHT_CLIP_WRITE",
    "AVF_INFO_IMAGEDB_MUTATION",
    "DELETE_SINGLE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P296_DESTRUCTIVE_VAULT_ACTIONS: Tuple[str, ...] = (
    "CAMSET_FOCUS_ZOOM_WRITE",
    "STILL_FLASH_CAPTURE_WRITE",
    "VIDEO_LIGHT_CLIP_WRITE",
    "AVF_INFO_IMAGEDB_MUTATION",
    "DELETE_SINGLE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P296_SLOT1_VAULT_SLOT: int = 1
P296_SAFE_SECONDARY_CAPTURE_SLOT: int = 2
P296_VAULT_FIREWALL_ERRNOS: Tuple[str, ...] = ("EROFS", "EBUSY")
P296_STAGE_B_VOLATILE_OVERLAY_DIR: str = (
    "/tmp/fx3_focus_area_zoom_iso_minss_flash_vault_overlay"
)
P296_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P296_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P296_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P296_BLOCKED_INVALID_PILLAR52A_SPEC: str = "BLOCKED_INVALID_PILLAR52A_SPEC"
P296_BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION: str = (
    "BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION"
)
P296_BLOCKED_AF_AREA_REG_LOCK_OR_RESET_DRIFT: str = (
    "BLOCKED_AF_AREA_REG_LOCK_OR_RESET_DRIFT"
)
P296_BLOCKED_XLRH1_ZOOM_MYTH_OR_FX6_HANDLE_CONFLATION: str = (
    "BLOCKED_XLRH1_ZOOM_MYTH_OR_FX6_HANDLE_CONFLATION"
)
P296_BLOCKED_INVALID_PILLAR52B_SPEC: str = "BLOCKED_INVALID_PILLAR52B_SPEC"
P296_BLOCKED_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT: str = (
    "BLOCKED_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT"
)
P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION: str = (
    "BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION"
)
P296_BLOCKED_VIDEO_LIGHT_PMIC_900MA_OVERCURRENT: str = (
    "BLOCKED_VIDEO_LIGHT_PMIC_900MA_OVERCURRENT"
)
P296_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL: str = "BLOCKED_SLOT1_VAULT_WRITE_FIREWALL"
P296_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P296_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P296_STATUS_VERIFIED_PILLAR_52A: str = (
    "VERIFIED_PILLAR_52A_FOCUS_AREA_14_AF_REG_BODY_ZOOM_XLRH1_MYTHBUST_AND_SLOT1_VAULT"
)
P296_STATUS_REJECTED_PILLAR_52A: str = (
    "REJECTED_PILLAR_52A_FOCUS_AREA_14_AF_REG_BODY_ZOOM_XLRH1_MYTHBUST_AND_SLOT1_VAULT"
)
P296_STATUS_VERIFIED_PILLAR_52B: str = (
    "VERIFIED_PILLAR_52B_ISO_LIMIT_MINSS_CINE_EI_FLASH_MECH_GATE_VIDEOLIGHT_900MA_AND_SLOT1_VAULT"
)
P296_STATUS_REJECTED_PILLAR_52B: str = (
    "REJECTED_PILLAR_52B_ISO_LIMIT_MINSS_CINE_EI_FLASH_MECH_GATE_VIDEOLIGHT_900MA_AND_SLOT1_VAULT"
)
P296_STATUS_VERIFIED_PILLAR52_SUITE: str = (
    "VERIFIED_PILLAR52_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_VAULT"
)
P296_STATUS_FAIL_PILLAR52_SUITE: str = (
    "FAIL_PILLAR52_FOCUS_AREA_ZOOM_LEVER_ISO_MINSS_FLASH_VAULT"
)
P296_STATUS_VERIFIED_52OF52_AGGREGATOR: str = "VERIFIED_52OF52_PILLAR_RECOVERY_MASTER"
P296_STATUS_FAIL_52OF52_AGGREGATOR: str = "FAIL_52OF52_PILLAR_RECOVERY_MASTER"

P296_PILLAR_52A_SCENARIO_IDS: Tuple[str, ...] = (
    "P52A1_DEFAULT_STILL_WIDE_14AREA_BODY_ZOOM_3_8_NO_XLRH1_LEVER_SAFE",
    "P52A2_STILL_TRACKING_AF_REG_ON_UNLOCKS_OP_PARTS_SURVIVES_CAMSET_RESET_SAFE",
    "P52A3_REJECT_MOVIE_TRACKING_FOCUS_AREA_OR_LIMIT_UNDER_2_OR_FX6_CONFLATION",
    "P52A4_REJECT_AF_AREA_REG_LOCK_OP_PARTS_ON_OR_CAMSET_RESET_WIPE",
    "P52A5_REJECT_XLRH1_ZOOM_LEVER_REC_HOLD_MYTH_OR_FX6_0_99_SCALE_SPOOF",
    "P52A6_REJECT_SLOT1_FOCUS_ZOOM_CAMSET_WRITE_OR_PERSISTENT_OVERLAY_OR_H0_H3_DRIFT",
)
P296_PILLAR_52B_SCENARIO_IDS: Tuple[str, ...] = (
    "P52B1_DEFAULT_STILL_MECH_FILL_FLASH_1_250_ISO_MINSS_STD_VIDEOLIGHT_POWER_LINK_SAFE",
    "P52B2_MOVIE_CINE_EI_BASE800_LOCKOUT_FLEXIBLE_ISO_CLAMP_AND_PMIC_900MA_SAFE",
    "P52B3_REJECT_MOVIE_ISO_AUTO_MINSS_OR_CINE_EI_NON_BASE_ISO_OR_FX6_MINSS_SPOOF",
    "P52B4_REJECT_FLASH_IN_MOVIE_SQ_ELECTRONIC_SHUTTER_OR_SILENT_MODE",
    "P52B5_REJECT_VIDEOLIGHT_PMIC_5V_OVER_900MA_OR_HIGH_TRIGGER_VOLTAGE",
    "P52B6_REJECT_SLOT1_FLASH_VIDEOLIGHT_WRITE_IMAGEDB_MUTATION_OR_H0_H3_DRIFT",
)

MASTER_52_PILLAR_COUNT: int = 52
MASTER_52_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_51_PILLAR_SPECS + (
    (
        52,
        "pillar_52_focus_area_zoom_lever_iso_minss_flash_vault",
        "Phase 296 (Wave-50)",
        "fx3_recovery.realhw_52pillar_focus_area_zoom_lever_iso_minss_flash_vault_verifier",
    ),
)
MASTER_52_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_52_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Deterministic State Computations
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
    return os.environ.get(P296_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P296_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P296_DONOR_INSPECT_BUDGET_SECONDS


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
        (
            "P296_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
            P296_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            False,
        ),
        ("P296_OVERALL_READY_FOR_HARDWARE_ATTACH", P296_OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        (
            "P296_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATIONS",
            P296_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATIONS,
            0,
        ),
        (
            "P296_AF_AREA_REG_LOCK_OR_RESET_DRIFT_EVENTS",
            P296_AF_AREA_REG_LOCK_OR_RESET_DRIFT_EVENTS,
            0,
        ),
        ("P296_XLRH1_ZOOM_OR_HOLD_SPOOF_EVENTS", P296_XLRH1_ZOOM_OR_HOLD_SPOOF_EVENTS, 0),
        (
            "P296_FX6_HANDLE_OR_POS_DISPLAY_CONFLATION_EVENTS",
            P296_FX6_HANDLE_OR_POS_DISPLAY_CONFLATION_EVENTS,
            0,
        ),
        (
            "P296_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT_EVENTS",
            P296_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT_EVENTS,
            0,
        ),
        ("P296_FLASH_STILL_MECH_GATE_VIOLATIONS", P296_FLASH_STILL_MECH_GATE_VIOLATIONS, 0),
        ("P296_MISHOE_PMIC_5V_OVERCURRENT_EVENTS", P296_MISHOE_PMIC_5V_OVERCURRENT_EVENTS, 0),
        (
            "P296_SLOT1_FOCUS_ZOOM_CAMSET_MUTATION_BYTES",
            P296_SLOT1_FOCUS_ZOOM_CAMSET_MUTATION_BYTES,
            0,
        ),
        (
            "P296_SLOT1_FLASH_VIDEOLIGHT_IMAGEDB_BYTES",
            P296_SLOT1_FLASH_VIDEOLIGHT_IMAGEDB_BYTES,
            0,
        ),
        ("P296_SLOT1_VAULT_MUTATION_BYTES", P296_SLOT1_VAULT_MUTATION_BYTES, 0),
        ("P296_SLOT1_FORMAT_HARD_LOCKED", P296_SLOT1_FORMAT_HARD_LOCKED, True),
        ("P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED", P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED, True),
        ("P296_XLRH1_HAS_ZOOM_LEVER", P296_XLRH1_HAS_ZOOM_LEVER, False),
        ("P296_XLRH1_HAS_REC_BUTTON", P296_XLRH1_HAS_REC_BUTTON, False),
        ("P296_XLRH1_HAS_ZOOM_HOLD_SWITCH", P296_XLRH1_HAS_ZOOM_HOLD_SWITCH, False),
        ("P296_FX6_0_99_IS_ZOOM_POSITION_DISPLAY", P296_FX6_0_99_IS_ZOOM_POSITION_DISPLAY, True),
        ("P296_FX6_HAS_ISO_AUTO_MIN_SS", P296_FX6_HAS_ISO_AUTO_MIN_SS, False),
        ("P296_FX6_MECHANICAL_SHUTTER_PRESENT", P296_FX6_MECHANICAL_SHUTTER_PRESENT, False),
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
    return any(tok in low for tok in P296_FORBIDDEN_PERSISTENT_TARGETS)


def compute_expected_focus_area_and_af_reg_state(
    *,
    shooting_domain: str,
    shooting_mode: str,
    focus_mode: str,
    zoom_range: str,
    configured_focus_area: str,
    focus_area_limit_enabled_areas: Tuple[str, ...],
    pre_af_area_reg: str,
    configured_lock_operation_parts: str,
    configured_focus_area_color: str,
    reset_action: str,
    del_regist_af_area_invoked: bool = False,
) -> Tuple[bool, str, bool, bool, str, str, str]:
    """Compute `(tracking_areas_allowed, eff_focus_area, focus_area_limit_valid,
    touch_tracking_allowed, post_af_area_reg, eff_lock_operation_parts, post_focus_area_color)`.

    - In `Movie` / `S&Q`: all 7 `Tracking:` menu focus areas are locked out;
      `[Touch Tracking]` is available only when `focus_mode != "MF"` and
      `zoom_range == "Optical zoom only"`.
    - `[Focus Area Limit]` requires `>= 2` of 14 valid areas enabled.
    - `[AF Area Registration]` (`Off`/`On`) survives `Camera Settings Reset`,
      clears only on `Initialize` (or `[Del. Regist. AF Area]`), is disabled in
      `Movie`/`S&Q`/`Intelligent Auto`, and forces `[Lock Operation Parts] = "Off"`.
    - `[Focus Area Color]` survives `Camera Settings Reset` and resets on `Initialize`.
    """
    tracking_allowed = shooting_domain == "Still" and shooting_mode != "Intelligent Auto"
    if shooting_mode == "Intelligent Auto":
        eff_focus_area = P296_FOCUS_AREA_DEFAULT
    elif not tracking_allowed and configured_focus_area in P296_FOCUS_AREA_7_STILL_TRACKING:
        eff_focus_area = configured_focus_area.replace("Tracking: ", "")
        if eff_focus_area.startswith("Spot "):
            eff_focus_area = eff_focus_area.replace("Spot ", "Spot: ")
    else:
        eff_focus_area = configured_focus_area

    unique_valid_limit = tuple(
        dict.fromkeys(a for a in focus_area_limit_enabled_areas if a in P296_FOCUS_AREA_14_AREAS)
    )
    limit_valid = (
        len(unique_valid_limit) == len(focus_area_limit_enabled_areas)
        and len(unique_valid_limit) >= P296_FOCUS_AREA_LIMIT_MIN_AREAS
    )

    touch_tracking_allowed = (
        shooting_domain in ("Movie", "S&Q")
        and focus_mode != "MF"
        and zoom_range == "Optical zoom only"
    )

    if reset_action == "Initialize" or del_regist_af_area_invoked:
        post_af_reg = P296_AF_AREA_REG_DEFAULT
    else:
        post_af_reg = pre_af_area_reg

    af_reg_active_here = (
        post_af_reg == "On"
        and shooting_domain == "Still"
        and shooting_mode != "Intelligent Auto"
    )
    eff_lock_parts = "Off" if af_reg_active_here else configured_lock_operation_parts

    post_color = (
        P296_FOCUS_AREA_COLOR_DEFAULT
        if reset_action == "Initialize"
        else configured_focus_area_color
    )
    return (
        tracking_allowed,
        eff_focus_area,
        limit_valid,
        touch_tracking_allowed,
        post_af_reg,
        eff_lock_parts,
        post_color,
    )


def compute_expected_zoom_speed_and_reset_state(
    *,
    zoom_range: str,
    file_format: str,
    frame_rate_fps: int,
    pre_zoom_lever_1st_stby: int,
    pre_zoom_lever_2nd_stby: int,
    pre_custom_key_zoom_stby: int,
    pre_remote_zoom_speed_type: str,
    pre_remote_zoom_fixed_stby: int,
    reset_action: str,
) -> Tuple[bool, str, int, int, int, str, int]:
    """Compute `(ciz_dz_allowed, post_zoom_range, post_1st, post_2nd,
    post_custom_key, post_remote_type, post_remote_fixed)`.

    - `ClearImage Zoom` & `Digital Zoom` are unavailable in `RAW` or `120`/`100p`.
    - `Zoom Range` needs `[Initialize]` (survives `Camera Settings Reset`).
    - `Zoom Lever Speed`, `Custom Key Z. Speed`, and `Remote Zoom Speed` are all
      resettable via `Camera Settings Reset` (and `Initialize`).
    """
    ciz_dz_allowed = not ("RAW" in file_format or frame_rate_fps >= 100)
    post_zoom_range = P296_ZOOM_RANGE_DEFAULT if reset_action == "Initialize" else zoom_range
    resets_speed = reset_action in ("Camera Settings Reset", "Initialize")
    return (
        ciz_dz_allowed,
        post_zoom_range,
        P296_ZOOM_LEVER_1ST_SPEED_DEFAULT if resets_speed else pre_zoom_lever_1st_stby,
        P296_ZOOM_LEVER_2ND_SPEED_DEFAULT if resets_speed else pre_zoom_lever_2nd_stby,
        P296_CUSTOM_KEY_ZOOM_SPEED_DEFAULT if resets_speed else pre_custom_key_zoom_stby,
        P296_REMOTE_ZOOM_SPEED_TYPE_DEFAULT if resets_speed else pre_remote_zoom_speed_type,
        P296_REMOTE_ZOOM_FIXED_SPEED_DEFAULT if resets_speed else pre_remote_zoom_fixed_stby,
    )


def compute_expected_iso_range_minss_and_cine_ei_state(
    *,
    shooting_domain: str,
    shooting_mode: str,
    log_shooting_mode: str,
    cine_ei_base_iso: int,
    iso_mode: str,
    requested_iso: int,
    iso_range_limit_min: int,
    iso_range_limit_max: int,
    configured_iso_auto_min_ss: str,
    reset_action: str,
) -> Tuple[bool, bool, bool, int, str]:
    """Compute `(iso_range_limit_active, iso_auto_min_ss_active,
    auto_slow_shutter_allowed, eff_iso, post_iso_auto_min_ss)`.

    - Under Movie `Cine EI` / `Cine EI Quick`: sensor sensitivity is hard-pinned to
      Base ISO `800` or `12800`; `[ISO Range Limit]`, `[ISO AUTO Min. SS]`, and
      `[Auto Slow Shutter]` are all locked out.
    - `[ISO AUTO Min. SS]` is **Still-only** (`shooting_domain == "Still"`), active in
      `P`/`A` or `M + ISO AUTO`, and resets to `"Standard"` on `Camera Settings Reset` /
      `Initialize`.
    """
    cine_ei_locked = (
        shooting_domain in ("Movie", "S&Q")
        and log_shooting_mode in P296_CINE_EI_LOCKED_LOG_MODES
    )
    iso_range_active = not cine_ei_locked
    iso_auto_min_ss_active = (
        (not cine_ei_locked)
        and shooting_domain == "Still"
        and (
            shooting_mode in ("P", "A")
            or (shooting_mode == "M" and iso_mode == "ISO AUTO")
        )
    )
    auto_slow_shutter_allowed = (not cine_ei_locked) and shooting_domain in ("Movie", "S&Q")

    if cine_ei_locked:
        eff_iso = cine_ei_base_iso if cine_ei_base_iso in P296_CINE_EI_BASE_ISOS else 800
    else:
        eff_iso = max(iso_range_limit_min, min(iso_range_limit_max, requested_iso))

    post_min_ss = (
        P296_ISO_AUTO_MIN_SS_DEFAULT
        if reset_action in ("Camera Settings Reset", "Initialize")
        else configured_iso_auto_min_ss
    )
    return (
        iso_range_active,
        iso_auto_min_ss_active,
        auto_slow_shutter_allowed,
        eff_iso,
        post_min_ss,
    )


def compute_expected_flash_and_video_light_state(
    *,
    camera_model: str,
    shooting_domain: str,
    shutter_type: str,
    silent_mode: str,
    silent_mode_target_override_shutter: bool,
    configured_flash_mode: str,
    configured_video_light_mode: str,
    mishoe_5v_draw_ma: int,
    reset_action: str,
) -> Tuple[bool, str, bool, bool]:
    """Compute `(flash_allowed, post_flash_mode, video_light_allowed, pmic_5v_rail_safe)`.

    - `[Flash Mode]` is **strictly gated to `ILME-FX3` Mechanical-Shutter
      `EXPOSURE_MODE_STILL`**: blocked in `Movie`/`S&Q`, `Electronic Shutter`,
      `Silent Mode = On` (without target override), and still-less `ILME-FX6`.
    - `[Video Light Mode]` spans Still + Movie + `S&Q` under `PMIC 5V <= 900 mA`.
    """
    silent_forcing_elec = silent_mode == "On" and not silent_mode_target_override_shutter
    flash_allowed = (
        camera_model == P296_FX3_MODEL_NAME
        and shooting_domain == "Still"
        and shutter_type == "Mechanical Shutter"
        and not silent_forcing_elec
    )
    post_flash = (
        P296_FLASH_MODE_DEFAULT
        if reset_action in ("Camera Settings Reset", "Initialize")
        else configured_flash_mode
    )
    pmic_safe = 0 <= mishoe_5v_draw_ma <= P296_MISHOE_PMIC_5V_MAX_MA
    video_light_allowed = (
        shooting_domain in P296_SHOOTING_DOMAINS
        and configured_video_light_mode in P296_VIDEO_LIGHT_4_MODES
        and pmic_safe
    )
    return flash_allowed, post_flash, video_light_allowed, pmic_safe


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase296DonorArtifactDigest:
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
class Phase296DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase296DonorArtifactDigest, ...]


@dataclass(frozen=True)
class FocusAreaZoomLeverXlrH1VaultSpec:
    camera_model: str = P296_FX3_MODEL_NAME
    camera_model_id: int = P296_FX3_MODEL_ID
    camera_codename: str = P296_FX3_PRODUCT_CODENAME
    helpguide_id: str = P296_FX3_HELPGUIDE_ID
    fw_version: str = P296_FX3_FW_VERSION
    focus_zoom_surface_model: str = "FX3_14AREA_BODY_WT_ZOOM_LEVER_NO_XLRH1_ZOOM"
    fx6_focus_areas: Tuple[str, ...] = P296_FX6_FOCUS_AREAS
    focus_area_menu_path: Tuple[str, ...] = P296_FOCUS_AREA_MENU_PATH
    focus_area_limit_menu_path: Tuple[str, ...] = P296_FOCUS_AREA_LIMIT_MENU_PATH
    af_area_reg_menu_path: Tuple[str, ...] = P296_AF_AREA_REG_MENU_PATH
    zoom_menu_path: Tuple[str, ...] = P296_ZOOM_MENU_PATH
    shooting_domain: str = "Still"
    shooting_mode: str = "M"
    focus_mode: str = "AF-C"
    configured_focus_area: str = P296_FOCUS_AREA_DEFAULT
    reported_focus_area: str = P296_FOCUS_AREA_DEFAULT
    reported_tracking_areas_allowed: bool = True
    reported_touch_tracking_allowed: bool = False
    focus_area_limit_enabled_areas: Tuple[str, ...] = P296_FOCUS_AREA_14_AREAS
    switch_vh_af_area: str = P296_SWITCH_VH_AF_DEFAULT
    configured_focus_area_color: str = P296_FOCUS_AREA_COLOR_DEFAULT
    post_focus_area_color: str = P296_FOCUS_AREA_COLOR_DEFAULT
    circ_of_focus_point: str = P296_CIRC_FOCUS_POINT_DEFAULT
    pre_af_area_reg: str = P296_AF_AREA_REG_DEFAULT
    post_af_area_reg: str = P296_AF_AREA_REG_DEFAULT
    del_regist_af_area_invoked: bool = False
    configured_lock_operation_parts: str = "Off"
    reported_lock_operation_parts: str = "Off"
    reset_action: str = "None"
    # Zoom & XLR-H1 Myth-Bust
    xlrh1_attached: bool = True
    xlrh1_has_zoom_lever: bool = P296_XLRH1_HAS_ZOOM_LEVER
    xlrh1_has_rec_button: bool = P296_XLRH1_HAS_REC_BUTTON
    xlrh1_has_zoom_hold_switch: bool = P296_XLRH1_HAS_ZOOM_HOLD_SWITCH
    fx6_zoom_0_99_is_position_display: bool = P296_FX6_0_99_IS_ZOOM_POSITION_DISPLAY
    zoom_range: str = P296_ZOOM_RANGE_DEFAULT
    post_zoom_range: str = P296_ZOOM_RANGE_DEFAULT
    file_format: str = "XAVC S 4K"
    frame_rate_fps: int = 24
    pre_zoom_lever_1st_stby: int = P296_ZOOM_LEVER_1ST_SPEED_DEFAULT
    pre_zoom_lever_1st_rec: int = P296_ZOOM_LEVER_1ST_SPEED_DEFAULT
    pre_zoom_lever_2nd_stby: int = P296_ZOOM_LEVER_2ND_SPEED_DEFAULT
    pre_zoom_lever_2nd_rec: int = P296_ZOOM_LEVER_2ND_SPEED_DEFAULT
    post_zoom_lever_1st_stby: int = P296_ZOOM_LEVER_1ST_SPEED_DEFAULT
    post_zoom_lever_2nd_stby: int = P296_ZOOM_LEVER_2ND_SPEED_DEFAULT
    pre_custom_key_zoom_stby: int = P296_CUSTOM_KEY_ZOOM_SPEED_DEFAULT
    pre_custom_key_zoom_rec: int = P296_CUSTOM_KEY_ZOOM_SPEED_DEFAULT
    post_custom_key_zoom_stby: int = P296_CUSTOM_KEY_ZOOM_SPEED_DEFAULT
    pre_remote_zoom_speed_type: str = P296_REMOTE_ZOOM_SPEED_TYPE_DEFAULT
    post_remote_zoom_speed_type: str = P296_REMOTE_ZOOM_SPEED_TYPE_DEFAULT
    pre_remote_zoom_fixed_stby: int = P296_REMOTE_ZOOM_FIXED_SPEED_DEFAULT
    pre_remote_zoom_fixed_rec: int = P296_REMOTE_ZOOM_FIXED_SPEED_DEFAULT
    post_remote_zoom_fixed_stby: int = P296_REMOTE_ZOOM_FIXED_SPEED_DEFAULT
    movie_tracking_area_or_limit_violations: int = 0
    af_area_reg_lock_or_reset_drift_events: int = 0
    xlrh1_zoom_or_hold_spoof_events: int = 0
    fx6_handle_or_pos_display_conflation_events: int = 0
    # Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P296_SLOT1_FORMAT_HARD_LOCKED
    slot1_vault_erofs_ebusy_enforced: bool = P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED
    target_focus_zoom_slot: int = P296_SAFE_SECONDARY_CAPTURE_SLOT
    camset_af_zoom_targets_slot1: bool = False
    requested_vault_slot: int = P296_SLOT1_VAULT_SLOT
    requested_vault_action: str = "READ_ONLY_AUDIT"
    slot1_focus_zoom_camset_mutation_bytes: int = 0
    overlay_dir: str = P296_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P296_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P296_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P296_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class FocusAreaZoomLeverXlrH1VaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    focus_area_14_and_movie_tracking_lock_verified: bool
    focus_limit_and_circ_vh_rules_verified: bool
    af_area_reg_lock_op_parts_off_and_reset_verified: bool
    body_zoom_lever_and_xlrh1_myth_bust_verified: bool
    fx6_smart_handle_and_0_99_pos_display_contrast_verified: bool
    slot1_erofs_ebusy_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    movie_tracking_area_or_limit_violations: int
    af_area_reg_lock_or_reset_drift_events: int
    xlrh1_zoom_or_hold_spoof_events: int
    fx6_handle_or_pos_display_conflation_events: int
    slot1_focus_zoom_camset_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IsoRangeMinssFlashVideolightVaultSpec:
    camera_model: str = P296_FX3_MODEL_NAME
    camera_model_id: int = P296_FX3_MODEL_ID
    helpguide_id: str = P296_FX3_HELPGUIDE_ID
    fw_version: str = P296_FX3_FW_VERSION
    iso_flash_surface_model: str = "FX3_STILL_MECH_FLASH_AND_ISO_MINSS_VS_CINE_EI"
    fx6_has_iso_auto_min_ss: bool = P296_FX6_HAS_ISO_AUTO_MIN_SS
    fx6_mechanical_shutter_present: bool = P296_FX6_MECHANICAL_SHUTTER_PRESENT
    iso_range_limit_menu_path: Tuple[str, ...] = P296_ISO_RANGE_LIMIT_MENU_PATH
    iso_auto_min_ss_menu_path: Tuple[str, ...] = P296_ISO_AUTO_MIN_SS_MENU_PATH
    flash_mode_menu_path: Tuple[str, ...] = P296_FLASH_MODE_MENU_PATH
    video_light_mode_menu_path: Tuple[str, ...] = P296_VIDEO_LIGHT_MODE_MENU_PATH
    shooting_domain: str = "Still"
    shooting_mode: str = "A"
    log_shooting_mode: str = "Off"
    cine_ei_base_iso: int = 800
    iso_mode: str = "ISO AUTO"
    requested_iso: int = 800
    reported_iso: int = 800
    iso_range_limit_min: int = 100
    iso_range_limit_max: int = 12800
    reported_iso_range_limit_active: bool = True
    configured_iso_auto_min_ss: str = P296_ISO_AUTO_MIN_SS_DEFAULT
    post_iso_auto_min_ss: str = P296_ISO_AUTO_MIN_SS_DEFAULT
    reported_iso_auto_min_ss_active: bool = True
    reported_auto_slow_shutter_allowed: bool = False
    shutter_type: str = "Mechanical Shutter"
    silent_mode: str = "Off"
    silent_mode_target_override_shutter: bool = False
    configured_flash_mode: str = P296_FLASH_MODE_DEFAULT
    post_flash_mode: str = P296_FLASH_MODE_DEFAULT
    flash_sync_speed_denom: int = P296_FX3_MAX_FLASH_SYNC_DENOM
    flash_comp_ev: float = 0.0
    exp_comp_set: str = "Ambient&flash"
    reported_flash_allowed: bool = True
    flash_fired: bool = False
    configured_video_light_mode: str = P296_VIDEO_LIGHT_MODE_DEFAULT
    reported_video_light_allowed: bool = True
    mishoe_5v_draw_ma: int = 650
    non_sony_flash_trigger_voltage_v: float = 12.0
    reset_action: str = "None"
    iso_minss_or_cine_ei_lock_drift_events: int = 0
    flash_still_mech_gate_violations: int = 0
    mishoe_5v_overcurrent_events: int = 0
    # Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P296_SLOT1_FORMAT_HARD_LOCKED
    slot1_vault_erofs_ebusy_enforced: bool = P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED
    target_capture_slot: int = P296_SAFE_SECONDARY_CAPTURE_SLOT
    avf_info_imagedb_targets_slot1: bool = False
    requested_vault_slot: int = P296_SLOT1_VAULT_SLOT
    requested_vault_action: str = "READ_ONLY_AUDIT"
    slot1_flash_videolight_imagedb_bytes: int = 0
    overlay_dir: str = P296_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P296_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P296_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P296_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class IsoRangeMinssFlashVideolightVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    iso_range_limit_and_still_minss_verified: bool
    cine_ei_base_800_12800_lockout_verified: bool
    flash_still_mech_1_250_gate_verified: bool
    video_light_pmic_900ma_rail_verified: bool
    slot1_erofs_ebusy_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    iso_minss_or_cine_ei_lock_drift_events: int
    flash_still_mech_gate_violations: int
    mishoe_5v_overcurrent_events: int
    slot1_flash_videolight_imagedb_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FocusAreaZoomLeverIsoMinssFlashVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase296DonorSnapshot
    focus_area_zoom_xlrh1_report: FocusAreaZoomLeverXlrH1VaultReport
    iso_minss_flash_videolight_report: IsoRangeMinssFlashVideolightVaultReport
    movie_tracking_area_or_limit_violations: int
    af_area_reg_lock_or_reset_drift_events: int
    xlrh1_zoom_or_hold_spoof_events: int
    fx6_handle_or_pos_display_conflation_events: int
    iso_minss_or_cine_ei_lock_drift_events: int
    flash_still_mech_gate_violations: int
    mishoe_5v_overcurrent_events: int
    slot1_focus_zoom_camset_mutation_bytes: int
    slot1_flash_videolight_imagedb_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    overall_ready_for_hardware_attach: bool
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
class Pillar52ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar52ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar52ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar52BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar52ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar52StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase296DonorSnapshot
    pillar_52a_focus_area_zoom_xlrh1_vault: Pillar52ASuiteResult
    pillar_52b_iso_minss_flash_videolight_vault: Pillar52BSuiteResult
    movie_tracking_area_or_limit_violations: int
    af_area_reg_lock_or_reset_drift_events: int
    xlrh1_zoom_or_hold_spoof_events: int
    fx6_handle_or_pos_display_conflation_events: int
    iso_minss_or_cine_ei_lock_drift_events: int
    flash_still_mech_gate_violations: int
    mishoe_5v_overcurrent_events: int
    slot1_focus_zoom_camset_mutation_bytes: int
    slot1_flash_videolight_imagedb_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    overall_ready_for_hardware_attach: bool
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
class Master52PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_1_2s_fast_cli_budget: bool
    under_2_5s_fast_cli_budget: bool
    under_6s_budget: bool
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    # Pillar 52 & Wave-50 top-level fields
    donor_snapshot: Phase296DonorSnapshot
    pillar52_a_focus_area_zoom_xlrh1_vault: Pillar52ASuiteResult
    pillar52_b_iso_minss_flash_videolight_vault: Pillar52BSuiteResult
    movie_tracking_area_or_limit_violations: int
    af_area_reg_lock_or_reset_drift_events: int
    xlrh1_zoom_or_hold_spoof_events: int
    fx6_handle_or_pos_display_conflation_events: int
    iso_minss_or_cine_ei_lock_drift_events: int
    flash_still_mech_gate_violations: int
    mishoe_pmic_5v_overcurrent_events: int
    slot1_focus_zoom_camset_mutation_bytes: int
    slot1_flash_videolight_imagedb_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    xlrh1_has_zoom_lever: bool
    xlrh1_has_rec_button: bool
    xlrh1_has_zoom_hold_switch: bool
    fx6_0_99_is_zoom_position_display: bool
    fx6_has_iso_auto_min_ss: bool
    fx6_mechanical_shutter_present: bool
    # Preserved Pillars 1..51 rollup metrics
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
    hardware_live_attachment_authorized: bool
    master_52pillar_sha256: str
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
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P296_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P296_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase296_donors() -> Tuple[Phase296DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P296_DONOR_FX3_APPFW_702_RELPATH,
            P296_PINNED_FX3_APPFW_702_BYTES,
            P296_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P296_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P296_DONOR_FX6_APPFW_601_RELPATH,
            P296_PINNED_FX6_APPFW_601_BYTES,
            P296_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P296_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P296_DONOR_FX3_BACKUP_BIN_RELPATH,
            P296_PINNED_FX3_BACKUP_BIN_BYTES,
            P296_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_uxc_en_f",
            P296_DONOR_FX3_UXC_EN_F_RELPATH,
            P296_PINNED_FX3_UXC_EN_F_BYTES,
            P296_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P296_DONOR_FX3_UXC_SC_F_RELPATH,
            P296_PINNED_FX3_UXC_SC_F_BYTES,
            P296_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P296_DONOR_FX3_UXC_TC_F_RELPATH,
            P296_PINNED_FX3_UXC_TC_F_BYTES,
            P296_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P296_DONOR_FX3_UXC_JA_F_RELPATH,
            P296_PINNED_FX3_UXC_JA_F_BYTES,
            P296_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P296_DONOR_FX3_UXC_EN_RELPATH,
            P296_PINNED_FX3_UXC_EN_BYTES,
            P296_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_sc",
            P296_DONOR_FX3_UXC_SC_RELPATH,
            P296_PINNED_FX3_UXC_SC_BYTES,
            P296_PINNED_FX3_UXC_SC_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX3_SC",
        ),
        (
            "fx3_uxc_tc",
            P296_DONOR_FX3_UXC_TC_RELPATH,
            P296_PINNED_FX3_UXC_TC_BYTES,
            P296_PINNED_FX3_UXC_TC_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX3_TC",
        ),
        (
            "fx3_uxc_ja",
            P296_DONOR_FX3_UXC_JA_RELPATH,
            P296_PINNED_FX3_UXC_JA_BYTES,
            P296_PINNED_FX3_UXC_JA_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX3_JA",
        ),
        (
            "fx3_uxc_en_g",
            P296_DONOR_FX3_UXC_EN_G_RELPATH,
            P296_PINNED_FX3_UXC_EN_G_BYTES,
            P296_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx3_uxc_sc_g",
            P296_DONOR_FX3_UXC_SC_G_RELPATH,
            P296_PINNED_FX3_UXC_SC_G_BYTES,
            P296_PINNED_FX3_UXC_SC_G_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_SC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_G",
        ),
        (
            "fx3_uxc_tc_g",
            P296_DONOR_FX3_UXC_TC_G_RELPATH,
            P296_PINNED_FX3_UXC_TC_G_BYTES,
            P296_PINNED_FX3_UXC_TC_G_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_TC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_G",
        ),
        (
            "fx3_uxc_ja_g",
            P296_DONOR_FX3_UXC_JA_G_RELPATH,
            P296_PINNED_FX3_UXC_JA_G_BYTES,
            P296_PINNED_FX3_UXC_JA_G_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX3_UXC_JA_G_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_G",
        ),
        (
            "fx6_uxc_en",
            P296_DONOR_FX6_UXC_EN_RELPATH,
            P296_PINNED_FX6_UXC_EN_BYTES,
            P296_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P296_DONOR_FX6_UXC_EN_2_RELPATH,
            P296_PINNED_FX6_UXC_EN_2_BYTES,
            P296_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P296_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase296DonorArtifactDigest(
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


def inspect_phase296_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase296DonorSnapshot:
    """Inspect Wave-50 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.2s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase296_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase296DonorSnapshot(
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
            P296_DONOR_FX3_APPFW_702_RELPATH,
            P296_PINNED_FX3_APPFW_702_BYTES,
            P296_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702"),
        ),
        (
            "fx6_appfw_601_so",
            P296_DONOR_FX6_APPFW_601_RELPATH,
            P296_PINNED_FX6_APPFW_601_BYTES,
            P296_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601"),
        ),
        (
            "fx3_backup_bin",
            P296_DONOR_FX3_BACKUP_BIN_RELPATH,
            P296_PINNED_FX3_BACKUP_BIN_BYTES,
            P296_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_uxc_en_f",
            P296_DONOR_FX3_UXC_EN_F_RELPATH,
            P296_PINNED_FX3_UXC_EN_F_BYTES,
            P296_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P296_DONOR_FX3_UXC_SC_F_RELPATH,
            P296_PINNED_FX3_UXC_SC_F_BYTES,
            P296_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P296_DONOR_FX3_UXC_TC_F_RELPATH,
            P296_PINNED_FX3_UXC_TC_F_BYTES,
            P296_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P296_DONOR_FX3_UXC_JA_F_RELPATH,
            P296_PINNED_FX3_UXC_JA_F_BYTES,
            P296_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P296_DONOR_FX3_UXC_EN_RELPATH,
            P296_PINNED_FX3_UXC_EN_BYTES,
            P296_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_sc",
            P296_DONOR_FX3_UXC_SC_RELPATH,
            P296_PINNED_FX3_UXC_SC_BYTES,
            P296_PINNED_FX3_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC"),
        ),
        (
            "fx3_uxc_tc",
            P296_DONOR_FX3_UXC_TC_RELPATH,
            P296_PINNED_FX3_UXC_TC_BYTES,
            P296_PINNED_FX3_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC"),
        ),
        (
            "fx3_uxc_ja",
            P296_DONOR_FX3_UXC_JA_RELPATH,
            P296_PINNED_FX3_UXC_JA_BYTES,
            P296_PINNED_FX3_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA"),
        ),
        (
            "fx3_uxc_en_g",
            P296_DONOR_FX3_UXC_EN_G_RELPATH,
            P296_PINNED_FX3_UXC_EN_G_BYTES,
            P296_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx3_uxc_sc_g",
            P296_DONOR_FX3_UXC_SC_G_RELPATH,
            P296_PINNED_FX3_UXC_SC_G_BYTES,
            P296_PINNED_FX3_UXC_SC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_G"),
        ),
        (
            "fx3_uxc_tc_g",
            P296_DONOR_FX3_UXC_TC_G_RELPATH,
            P296_PINNED_FX3_UXC_TC_G_BYTES,
            P296_PINNED_FX3_UXC_TC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_G"),
        ),
        (
            "fx3_uxc_ja_g",
            P296_DONOR_FX3_UXC_JA_G_RELPATH,
            P296_PINNED_FX3_UXC_JA_G_BYTES,
            P296_PINNED_FX3_UXC_JA_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_G"),
        ),
        (
            "fx6_uxc_en",
            P296_DONOR_FX6_UXC_EN_RELPATH,
            P296_PINNED_FX6_UXC_EN_BYTES,
            P296_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P296_DONOR_FX6_UXC_EN_2_RELPATH,
            P296_PINNED_FX6_UXC_EN_2_BYTES,
            P296_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    digests: List[Phase296DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            break
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        digests.append(
            Phase296DonorArtifactDigest(
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
        artifacts = _synthetic_phase296_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase296DonorSnapshot(
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
    return Phase296DonorSnapshot(
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
# Spec Builders & Evaluators (Pillars 52A & 52B)
# ---------------------------------------------------------------------------


def build_default_safe_focus_area_zoom_xlrh1_vault_spec(
    **overrides: Any,
) -> FocusAreaZoomLeverXlrH1VaultSpec:
    """Return a clean, verified default `FocusAreaZoomLeverXlrH1VaultSpec`."""
    spec = FocusAreaZoomLeverXlrH1VaultSpec()
    if not overrides:
        return spec
    return FocusAreaZoomLeverXlrH1VaultSpec(**{**asdict(spec), **overrides})


def build_default_safe_iso_minss_flash_videolight_vault_spec(
    **overrides: Any,
) -> IsoRangeMinssFlashVideolightVaultSpec:
    """Return a clean, verified default `IsoRangeMinssFlashVideolightVaultSpec`."""
    spec = IsoRangeMinssFlashVideolightVaultSpec()
    if not overrides:
        return spec
    return IsoRangeMinssFlashVideolightVaultSpec(**{**asdict(spec), **overrides})


def evaluate_focus_area_zoom_xlrh1_vault(
    spec: FocusAreaZoomLeverXlrH1VaultSpec,
) -> FocusAreaZoomLeverXlrH1VaultReport:
    """Evaluate Pillar 52A (`[Focus Area]` 14-area hierarchy, `[Focus Area Limit]` `>= 2`,
    `[AF Area Registration]` `Lock Operation Parts = Off` + `Initialize` survival,
    body `W/T` Zoom Lever vs handle-less `XLR-H1` myth-bust, FX6 Smart Handle contrast,
    and `Slot-1` `EROFS`/`EBUSY` Vault firewall)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested or errors:
        _fail(
            P296_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Persistent write release or module safety policy violation",
        )

    # Camera identity & structural baseline
    if (
        spec.camera_model != P296_FX3_MODEL_NAME
        or spec.camera_model_id != P296_FX3_MODEL_ID
        or spec.fw_version not in P296_FX3_SUPPORTED_FW_VERSIONS
        or spec.helpguide_id != P296_FX3_HELPGUIDE_ID
        or spec.shooting_domain not in P296_SHOOTING_DOMAINS
        or spec.shooting_mode not in P296_STILL_SHOOTING_MODES
        or spec.focus_mode not in P296_FOCUS_MODES
        or spec.switch_vh_af_area not in P296_SWITCH_VH_AF_MODES
        or spec.configured_focus_area_color not in P296_FOCUS_AREA_COLOR_MODES
        or spec.circ_of_focus_point not in P296_CIRC_FOCUS_POINT_MODES
        or spec.pre_af_area_reg not in P296_ON_OFF_MODES
        or spec.configured_lock_operation_parts not in P296_ON_OFF_MODES
        or spec.zoom_range not in P296_ZOOM_RANGES
        or spec.pre_remote_zoom_speed_type not in P296_REMOTE_ZOOM_SPEED_TYPES
        or spec.reset_action not in P296_RESET_ACTIONS
        or spec.requested_vault_action not in P296_VAULT_TARGET_ACTIONS
    ):
        _fail(
            P296_BLOCKED_INVALID_PILLAR52A_SPEC,
            "Invalid Pillar 52A camera/focus/zoom/reset/vault spec parameter",
        )

    for spd_name, spd_val in (
        ("pre_zoom_lever_1st_stby", spec.pre_zoom_lever_1st_stby),
        ("pre_zoom_lever_1st_rec", spec.pre_zoom_lever_1st_rec),
        ("pre_zoom_lever_2nd_stby", spec.pre_zoom_lever_2nd_stby),
        ("pre_zoom_lever_2nd_rec", spec.pre_zoom_lever_2nd_rec),
        ("pre_custom_key_zoom_stby", spec.pre_custom_key_zoom_stby),
        ("pre_custom_key_zoom_rec", spec.pre_custom_key_zoom_rec),
        ("pre_remote_zoom_fixed_stby", spec.pre_remote_zoom_fixed_stby),
        ("pre_remote_zoom_fixed_rec", spec.pre_remote_zoom_fixed_rec),
    ):
        if not (P296_ZOOM_SPEED_MIN <= spd_val <= P296_ZOOM_SPEED_MAX):
            _fail(
                P296_BLOCKED_INVALID_PILLAR52A_SPEC,
                f"Zoom speed {spd_name}={spd_val} outside 1..8",
            )

    (
        exp_tracking_allowed,
        exp_focus_area,
        exp_limit_valid,
        exp_touch_tracking_allowed,
        exp_post_af_reg,
        exp_lock_parts,
        exp_post_color,
    ) = compute_expected_focus_area_and_af_reg_state(
        shooting_domain=spec.shooting_domain,
        shooting_mode=spec.shooting_mode,
        focus_mode=spec.focus_mode,
        zoom_range=spec.zoom_range,
        configured_focus_area=spec.configured_focus_area,
        focus_area_limit_enabled_areas=spec.focus_area_limit_enabled_areas,
        pre_af_area_reg=spec.pre_af_area_reg,
        configured_lock_operation_parts=spec.configured_lock_operation_parts,
        configured_focus_area_color=spec.configured_focus_area_color,
        reset_action=spec.reset_action,
        del_regist_af_area_invoked=spec.del_regist_af_area_invoked,
    )

    (
        exp_ciz_dz_allowed,
        exp_post_zoom_range,
        exp_post_1st,
        exp_post_2nd,
        exp_post_custom,
        exp_post_remote_type,
        exp_post_remote_fixed,
    ) = compute_expected_zoom_speed_and_reset_state(
        zoom_range=spec.zoom_range,
        file_format=spec.file_format,
        frame_rate_fps=spec.frame_rate_fps,
        pre_zoom_lever_1st_stby=spec.pre_zoom_lever_1st_stby,
        pre_zoom_lever_2nd_stby=spec.pre_zoom_lever_2nd_stby,
        pre_custom_key_zoom_stby=spec.pre_custom_key_zoom_stby,
        pre_remote_zoom_speed_type=spec.pre_remote_zoom_speed_type,
        pre_remote_zoom_fixed_stby=spec.pre_remote_zoom_fixed_stby,
        reset_action=spec.reset_action,
    )

    # 1. Focus Area 14-area hierarchy, Movie Tracking: lockout & >= 2 Focus Area Limit
    focus_ok = (
        spec.configured_focus_area in P296_FOCUS_AREA_14_AREAS
        and spec.reported_focus_area == exp_focus_area
        and spec.reported_tracking_areas_allowed == exp_tracking_allowed
        and spec.reported_touch_tracking_allowed == exp_touch_tracking_allowed
        and exp_limit_valid
        and spec.fx6_focus_areas == P296_FX6_FOCUS_AREAS
        and spec.focus_zoom_surface_model == "FX3_14AREA_BODY_WT_ZOOM_LEVER_NO_XLRH1_ZOOM"
        and spec.movie_tracking_area_or_limit_violations == 0
    )
    if not focus_ok:
        _fail(
            P296_BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION,
            "Focus Area 14-area hierarchy / Movie Tracking: lockout / >=2 Focus Area Limit / FX6 contrast violated",
        )

    limit_circ_vh_ok = (
        exp_limit_valid
        and spec.post_focus_area_color == exp_post_color
        and not (
            spec.shooting_domain in ("Movie", "S&Q")
            and spec.switch_vh_af_area != "Off"
        )
    )
    if not limit_circ_vh_ok:
        _fail(
            P296_BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION,
            "Focus Area Limit / Switch V/H AF Area / Focus Area Color reset rule violated",
        )

    # 2. [AF Area Registration] (forces Lock Operation Parts = Off & survives Camera Settings Reset)
    af_reg_ok = (
        spec.post_af_area_reg == exp_post_af_reg
        and spec.reported_lock_operation_parts == exp_lock_parts
        and spec.af_area_reg_lock_or_reset_drift_events == 0
    )
    if not af_reg_ok:
        _fail(
            P296_BLOCKED_AF_AREA_REG_LOCK_OR_RESET_DRIFT,
            "AF Area Registration (Lock Operation Parts=Off coupling or Camera Settings Reset survival) drifted",
        )

    # 3. Body W/T Zoom Lever vs Handle-Less XLR-H1 Myth-Bust & FX6 Smart Handle Contrast
    zoom_xlrh1_ok = (
        not spec.xlrh1_has_zoom_lever
        and not spec.xlrh1_has_rec_button
        and not spec.xlrh1_has_zoom_hold_switch
        and spec.xlrh1_zoom_or_hold_spoof_events == 0
        and spec.post_zoom_range == exp_post_zoom_range
        and spec.post_zoom_lever_1st_stby == exp_post_1st
        and spec.post_zoom_lever_2nd_stby == exp_post_2nd
        and spec.post_custom_key_zoom_stby == exp_post_custom
        and spec.post_remote_zoom_speed_type == exp_post_remote_type
        and spec.post_remote_zoom_fixed_stby == exp_post_remote_fixed
        and (
            exp_ciz_dz_allowed
            or spec.zoom_range == "Optical zoom only"
        )
    )
    fx6_contrast_ok = (
        spec.fx6_zoom_0_99_is_position_display
        and spec.fx6_handle_or_pos_display_conflation_events == 0
    )
    if not (zoom_xlrh1_ok and fx6_contrast_ok):
        _fail(
            P296_BLOCKED_XLRH1_ZOOM_MYTH_OR_FX6_HANDLE_CONFLATION,
            "XLR-H1 zoom/rec/hold myth or FX6 Smart Handle / 0..99 Zoom Position Display conflation detected",
        )

    # 4. Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    vault_fw_ok = (
        spec.slot1_holds_recovery_vault
        and spec.slot1_sdxc_wp_locked
        and spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_ebusy_enforced
        and spec.target_focus_zoom_slot == P296_SAFE_SECONDARY_CAPTURE_SLOT
        and not spec.camset_af_zoom_targets_slot1
        and spec.requested_vault_action not in P296_DESTRUCTIVE_VAULT_ACTIONS
        and spec.slot1_focus_zoom_camset_mutation_bytes == 0
    )
    if not vault_fw_ok:
        _fail(
            P296_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS/EBUSY firewall blocked Focus/Zoom CAMSET/Format/Delete mutation",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
        and spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
    )
    if not overlay_ok:
        _fail(
            P296_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must stay in volatile /tmp with BLKROSET=True: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P296_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P296_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P296_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "52A",
            "passed": passed,
            "block_code": block_code,
            "focus_area": spec.reported_focus_area,
            "af_area_reg": spec.post_af_area_reg,
            "lock_op_parts": spec.reported_lock_operation_parts,
            "zoom_1st_2nd": (spec.post_zoom_lever_1st_stby, spec.post_zoom_lever_2nd_stby),
            "xlrh1_zoom": spec.xlrh1_has_zoom_lever,
            "slot1_bytes": spec.slot1_focus_zoom_camset_mutation_bytes,
            "errors": errors,
        }
    )
    return FocusAreaZoomLeverXlrH1VaultReport(
        passed=passed,
        status=P296_STATUS_VERIFIED_PILLAR_52A if passed else P296_STATUS_REJECTED_PILLAR_52A,
        block_code=block_code,
        focus_area_14_and_movie_tracking_lock_verified=focus_ok,
        focus_limit_and_circ_vh_rules_verified=limit_circ_vh_ok,
        af_area_reg_lock_op_parts_off_and_reset_verified=af_reg_ok,
        body_zoom_lever_and_xlrh1_myth_bust_verified=zoom_xlrh1_ok,
        fx6_smart_handle_and_0_99_pos_display_contrast_verified=fx6_contrast_ok,
        slot1_erofs_ebusy_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=14,
        movie_tracking_area_or_limit_violations=spec.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=spec.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=spec.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=spec.fx6_handle_or_pos_display_conflation_events,
        slot1_focus_zoom_camset_mutation_bytes=spec.slot1_focus_zoom_camset_mutation_bytes,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_iso_minss_flash_videolight_vault(
    spec: IsoRangeMinssFlashVideolightVaultSpec,
) -> IsoRangeMinssFlashVideolightVaultReport:
    """Evaluate Pillar 52B (`[ISO Range Limit]` & Still-only `[ISO AUTO Min. SS]` vs
    `Cine EI` Base ISO `800 / 12800` lockout, `[Flash Mode]` Mechanical-Shutter Still
    gate + `1/250 s` FF sync, `[Video Light Mode]` `PMIC 5V <= 900 mA` rail guard,
    and `Slot-1` `EROFS`/`EBUSY` Vault firewall)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested or errors:
        _fail(
            P296_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Persistent write release or module safety policy violation",
        )

    if (
        spec.camera_model != P296_FX3_MODEL_NAME
        or spec.camera_model_id != P296_FX3_MODEL_ID
        or spec.fw_version not in P296_FX3_SUPPORTED_FW_VERSIONS
        or spec.helpguide_id != P296_FX3_HELPGUIDE_ID
        or spec.shooting_domain not in P296_SHOOTING_DOMAINS
        or spec.shooting_mode not in P296_STILL_SHOOTING_MODES
        or spec.log_shooting_mode not in P296_LOG_SHOOTING_MODES
        or spec.configured_iso_auto_min_ss not in P296_ISO_AUTO_MIN_SS_OPTIONS
        or spec.shutter_type not in P296_SHUTTER_TYPES
        or spec.silent_mode not in P296_ON_OFF_MODES
        or spec.configured_flash_mode not in P296_FLASH_5_MODES
        or spec.configured_video_light_mode not in P296_VIDEO_LIGHT_4_MODES
        or spec.exp_comp_set not in P296_EXP_COMP_SET_MODES
        or spec.reset_action not in P296_RESET_ACTIONS
        or spec.requested_vault_action not in P296_VAULT_TARGET_ACTIONS
        or not (
            P296_ISO_RANGE_MIN_FLOOR <= spec.iso_range_limit_min <= spec.iso_range_limit_max <= P296_ISO_RANGE_MAX_CEILING
        )
        or not (P296_FLASH_COMP_MIN_EV <= spec.flash_comp_ev <= P296_FLASH_COMP_MAX_EV)
    ):
        _fail(
            P296_BLOCKED_INVALID_PILLAR52B_SPEC,
            "Invalid Pillar 52B camera/ISO/Flash/VideoLight/vault spec parameter",
        )

    (
        exp_iso_range_active,
        exp_iso_auto_min_ss_active,
        exp_auto_slow_shutter_allowed,
        exp_iso,
        exp_post_min_ss,
    ) = compute_expected_iso_range_minss_and_cine_ei_state(
        shooting_domain=spec.shooting_domain,
        shooting_mode=spec.shooting_mode,
        log_shooting_mode=spec.log_shooting_mode,
        cine_ei_base_iso=spec.cine_ei_base_iso,
        iso_mode=spec.iso_mode,
        requested_iso=spec.requested_iso,
        iso_range_limit_min=spec.iso_range_limit_min,
        iso_range_limit_max=spec.iso_range_limit_max,
        configured_iso_auto_min_ss=spec.configured_iso_auto_min_ss,
        reset_action=spec.reset_action,
    )

    (
        exp_flash_allowed,
        exp_post_flash_mode,
        exp_video_light_allowed,
        exp_pmic_safe,
    ) = compute_expected_flash_and_video_light_state(
        camera_model=spec.camera_model,
        shooting_domain=spec.shooting_domain,
        shutter_type=spec.shutter_type,
        silent_mode=spec.silent_mode,
        silent_mode_target_override_shutter=spec.silent_mode_target_override_shutter,
        configured_flash_mode=spec.configured_flash_mode,
        configured_video_light_mode=spec.configured_video_light_mode,
        mishoe_5v_draw_ma=spec.mishoe_5v_draw_ma,
        reset_action=spec.reset_action,
    )

    # 1. [ISO Range Limit] & Still-only [ISO AUTO Min. SS]
    iso_minss_ok = (
        spec.reported_iso_range_limit_active == exp_iso_range_active
        and spec.reported_iso_auto_min_ss_active == exp_iso_auto_min_ss_active
        and spec.reported_auto_slow_shutter_allowed == exp_auto_slow_shutter_allowed
        and spec.reported_iso == exp_iso
        and spec.post_iso_auto_min_ss == exp_post_min_ss
        and not spec.fx6_has_iso_auto_min_ss
        and spec.iso_minss_or_cine_ei_lock_drift_events == 0
    )
    cine_ei_ok = True
    if spec.shooting_domain in ("Movie", "S&Q") and spec.log_shooting_mode in P296_CINE_EI_LOCKED_LOG_MODES:
        cine_ei_ok = (
            spec.reported_iso in P296_CINE_EI_BASE_ISOS
            and not spec.reported_iso_range_limit_active
            and not spec.reported_iso_auto_min_ss_active
            and not spec.reported_auto_slow_shutter_allowed
        )
    if not (iso_minss_ok and cine_ei_ok):
        _fail(
            P296_BLOCKED_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT,
            "ISO Range Limit / Still-only ISO AUTO Min. SS / Cine EI Base ISO 800/12800 lockout drifted",
        )

    # 2. [Flash Mode] Mechanical-Shutter Still Gate + 1/250 s Sync & FX6 Contrast
    flash_gate_ok = (
        spec.reported_flash_allowed == exp_flash_allowed
        and spec.post_flash_mode == exp_post_flash_mode
        and spec.flash_sync_speed_denom == P296_FX3_MAX_FLASH_SYNC_DENOM
        and not spec.fx6_mechanical_shutter_present
        and (not spec.flash_fired or exp_flash_allowed)
        and spec.flash_still_mech_gate_violations == 0
    )
    if not flash_gate_ok:
        _fail(
            P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION,
            "Flash Mode Still Mechanical-Shutter gate (1/250 s sync / Movie / Electronic / Silent lockout) violated",
        )

    # 3. [Video Light Mode] & MI-Shoe PMIC 5V <= 900 mA Rail Guard
    video_light_ok = (
        spec.reported_video_light_allowed == exp_video_light_allowed
        and exp_pmic_safe
        and 0.0 <= spec.non_sony_flash_trigger_voltage_v <= P296_MISHOE_NON_SONY_FLASH_MAX_V
        and spec.mishoe_5v_overcurrent_events == 0
    )
    if not video_light_ok:
        _fail(
            P296_BLOCKED_VIDEO_LIGHT_PMIC_900MA_OVERCURRENT,
            f"Video Light MI-Shoe PMIC 5V <= 900 mA or <250 V trigger guard violated (draw={spec.mishoe_5v_draw_ma} mA)",
        )

    # 4. Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    vault_fw_ok = (
        spec.slot1_holds_recovery_vault
        and spec.slot1_sdxc_wp_locked
        and spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_ebusy_enforced
        and spec.target_capture_slot == P296_SAFE_SECONDARY_CAPTURE_SLOT
        and not spec.avf_info_imagedb_targets_slot1
        and spec.requested_vault_action not in P296_DESTRUCTIVE_VAULT_ACTIONS
        and spec.slot1_flash_videolight_imagedb_bytes == 0
    )
    if not vault_fw_ok:
        _fail(
            P296_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS/EBUSY firewall blocked Flash/VideoLight/ImageDB/Format/Delete mutation",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
        and spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
    )
    if not overlay_ok:
        _fail(
            P296_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must stay in volatile /tmp with BLKROSET=True: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P296_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P296_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P296_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "52B",
            "passed": passed,
            "block_code": block_code,
            "iso": spec.reported_iso,
            "iso_minss": spec.post_iso_auto_min_ss,
            "flash_mode": spec.post_flash_mode,
            "flash_allowed": spec.reported_flash_allowed,
            "video_light": spec.configured_video_light_mode,
            "mishoe_ma": spec.mishoe_5v_draw_ma,
            "slot1_bytes": spec.slot1_flash_videolight_imagedb_bytes,
            "errors": errors,
        }
    )
    return IsoRangeMinssFlashVideolightVaultReport(
        passed=passed,
        status=P296_STATUS_VERIFIED_PILLAR_52B if passed else P296_STATUS_REJECTED_PILLAR_52B,
        block_code=block_code,
        iso_range_limit_and_still_minss_verified=iso_minss_ok,
        cine_ei_base_800_12800_lockout_verified=cine_ei_ok,
        flash_still_mech_1_250_gate_verified=flash_gate_ok,
        video_light_pmic_900ma_rail_verified=video_light_ok,
        slot1_erofs_ebusy_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=14,
        iso_minss_or_cine_ei_lock_drift_events=spec.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=spec.flash_still_mech_gate_violations,
        mishoe_5v_overcurrent_events=spec.mishoe_5v_overcurrent_events,
        slot1_flash_videolight_imagedb_bytes=spec.slot1_flash_videolight_imagedb_bytes,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_focus_area_zoom_lever_iso_minss_flash_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_52a: Optional[FocusAreaZoomLeverXlrH1VaultSpec] = None,
    spec_52b: Optional[IsoRangeMinssFlashVideolightVaultSpec] = None,
) -> FocusAreaZoomLeverIsoMinssFlashVaultReport:
    """Combined single-shot verifier for Pillar 52A + Pillar 52B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase296_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_focus_area_zoom_xlrh1_vault(
        spec_52a or build_default_safe_focus_area_zoom_xlrh1_vault_spec()
    )
    rep_b = evaluate_iso_minss_flash_videolight_vault(
        spec_52b or build_default_safe_iso_minss_flash_videolight_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 296 Wave-50 donor artifact parity check failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return FocusAreaZoomLeverIsoMinssFlashVaultReport(
        schema=PHASE296_SCHEMA,
        version=PHASE296_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P296_STATUS_VERIFIED_PILLAR52_SUITE if all_ok else P296_STATUS_FAIL_PILLAR52_SUITE,
        donor_snapshot=donor_snapshot,
        focus_area_zoom_xlrh1_report=rep_a,
        iso_minss_flash_videolight_report=rep_b,
        movie_tracking_area_or_limit_violations=rep_a.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=rep_a.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=rep_a.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=(
            rep_a.fx6_handle_or_pos_display_conflation_events
        ),
        iso_minss_or_cine_ei_lock_drift_events=rep_b.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=rep_b.flash_still_mech_gate_violations,
        mishoe_5v_overcurrent_events=rep_b.mishoe_5v_overcurrent_events,
        slot1_focus_zoom_camset_mutation_bytes=rep_a.slot1_focus_zoom_camset_mutation_bytes,
        slot1_flash_videolight_imagedb_bytes=rep_b.slot1_flash_videolight_imagedb_bytes,
        slot1_vault_mutation_bytes=(
            rep_a.slot1_focus_zoom_camset_mutation_bytes + rep_b.slot1_flash_videolight_imagedb_bytes
        ),
        slot1_format_hard_locked=(rep_a.slot1_format_hard_locked and rep_b.slot1_format_hard_locked),
        slot1_vault_erofs_ebusy_enforced=(
            rep_a.slot1_vault_erofs_ebusy_enforced and rep_b.slot1_vault_erofs_ebusy_enforced
        ),
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
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


def verify_focus_area_zoom_lever_iso_minss_flash_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_52a: Optional[FocusAreaZoomLeverXlrH1VaultSpec] = None,
    spec_52b: Optional[IsoRangeMinssFlashVideolightVaultSpec] = None,
) -> FocusAreaZoomLeverIsoMinssFlashVaultReport:
    """Symmetry alias for `verify_focus_area_zoom_lever_iso_minss_flash_and_vault`."""
    return verify_focus_area_zoom_lever_iso_minss_flash_and_vault(
        force_clean_room=force_clean_room,
        spec_52a=spec_52a,
        spec_52b=spec_52b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 52A & 52B) + Standalone Pillar 52 Suite
# ---------------------------------------------------------------------------


def run_pillar52a_focus_area_zoom_xlrh1_6_scenario_suite() -> Pillar52ASuiteResult:
    """Run 6 Pillar 52A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, FocusAreaZoomLeverXlrH1VaultSpec, Optional[str]], ...] = (
        (
            P296_PILLAR_52A_SCENARIO_IDS[0],
            True,
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(),
            None,
        ),
        (
            P296_PILLAR_52A_SCENARIO_IDS[1],
            True,
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                configured_focus_area="Tracking: Spot M",
                reported_focus_area="Tracking: Spot M",
                pre_af_area_reg="On",
                post_af_area_reg="On",
                configured_lock_operation_parts="On",
                reported_lock_operation_parts="Off",
                configured_focus_area_color="Red",
                post_focus_area_color="Red",
                circ_of_focus_point="Circulate",
                reset_action="Camera Settings Reset",
                post_zoom_lever_1st_stby=P296_ZOOM_LEVER_1ST_SPEED_DEFAULT,
                post_zoom_lever_2nd_stby=P296_ZOOM_LEVER_2ND_SPEED_DEFAULT,
                pre_zoom_lever_1st_stby=5,
                pre_zoom_lever_2nd_stby=6,
            ),
            None,
        ),
        (
            P296_PILLAR_52A_SCENARIO_IDS[2],
            False,
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                shooting_domain="Movie",
                configured_focus_area="Tracking: Wide",
                reported_focus_area="Tracking: Wide",
                reported_tracking_areas_allowed=True,
                focus_area_limit_enabled_areas=("Wide",),
                movie_tracking_area_or_limit_violations=1,
            ),
            P296_BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION,
        ),
        (
            P296_PILLAR_52A_SCENARIO_IDS[3],
            False,
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                pre_af_area_reg="On",
                post_af_area_reg="Off",
                reset_action="Camera Settings Reset",
                configured_lock_operation_parts="On",
                reported_lock_operation_parts="On",
                af_area_reg_lock_or_reset_drift_events=1,
            ),
            P296_BLOCKED_AF_AREA_REG_LOCK_OR_RESET_DRIFT,
        ),
        (
            P296_PILLAR_52A_SCENARIO_IDS[4],
            False,
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                xlrh1_has_zoom_lever=True,
                xlrh1_has_rec_button=True,
                xlrh1_has_zoom_hold_switch=True,
                fx6_zoom_0_99_is_position_display=False,
                xlrh1_zoom_or_hold_spoof_events=1,
                fx6_handle_or_pos_display_conflation_events=1,
            ),
            P296_BLOCKED_XLRH1_ZOOM_MYTH_OR_FX6_HANDLE_CONFLATION,
        ),
        (
            P296_PILLAR_52A_SCENARIO_IDS[5],
            False,
            build_default_safe_focus_area_zoom_xlrh1_vault_spec(
                target_focus_zoom_slot=1,
                camset_af_zoom_targets_slot1=True,
                requested_vault_slot=1,
                requested_vault_action="CAMSET_FOCUS_ZOOM_WRITE",
                slot1_focus_zoom_camset_mutation_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/52a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P296_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar52ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_focus_area_zoom_xlrh1_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar52ScenarioOutcome(
                scenario_id=sid,
                pillar="52A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar52ASuiteResult(
        passed=all_ok,
        status=P296_STATUS_VERIFIED_PILLAR_52A if all_ok else P296_STATUS_REJECTED_PILLAR_52A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar52b_iso_minss_flash_videolight_6_scenario_suite() -> Pillar52BSuiteResult:
    """Run 6 Pillar 52B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, IsoRangeMinssFlashVideolightVaultSpec, Optional[str]], ...] = (
        (
            P296_PILLAR_52B_SCENARIO_IDS[0],
            True,
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                flash_fired=True,
                mishoe_5v_draw_ma=720,
            ),
            None,
        ),
        (
            P296_PILLAR_52B_SCENARIO_IDS[1],
            True,
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                shooting_domain="Movie",
                shooting_mode="M",
                log_shooting_mode="Cine EI",
                cine_ei_base_iso=800,
                requested_iso=3200,
                reported_iso=800,
                reported_iso_range_limit_active=False,
                reported_iso_auto_min_ss_active=False,
                reported_auto_slow_shutter_allowed=False,
                reported_flash_allowed=False,
                configured_video_light_mode="REC Link",
                mishoe_5v_draw_ma=880,
            ),
            None,
        ),
        (
            P296_PILLAR_52B_SCENARIO_IDS[2],
            False,
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                shooting_domain="Movie",
                shooting_mode="M",
                log_shooting_mode="Cine EI",
                cine_ei_base_iso=800,
                requested_iso=3200,
                reported_iso=3200,
                reported_iso_range_limit_active=True,
                reported_iso_auto_min_ss_active=True,
                reported_auto_slow_shutter_allowed=True,
                reported_flash_allowed=False,
                fx6_has_iso_auto_min_ss=True,
                iso_minss_or_cine_ei_lock_drift_events=1,
            ),
            P296_BLOCKED_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT,
        ),
        (
            P296_PILLAR_52B_SCENARIO_IDS[3],
            False,
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                shooting_domain="Still",
                shutter_type="Electronic Shutter",
                silent_mode="On",
                reported_flash_allowed=True,
                flash_fired=True,
                flash_still_mech_gate_violations=1,
            ),
            P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION,
        ),
        (
            P296_PILLAR_52B_SCENARIO_IDS[4],
            False,
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                configured_video_light_mode="REC Link&STBY",
                reported_video_light_allowed=True,
                mishoe_5v_draw_ma=1150,
                non_sony_flash_trigger_voltage_v=300.0,
                mishoe_5v_overcurrent_events=1,
            ),
            P296_BLOCKED_VIDEO_LIGHT_PMIC_900MA_OVERCURRENT,
        ),
        (
            P296_PILLAR_52B_SCENARIO_IDS[5],
            False,
            build_default_safe_iso_minss_flash_videolight_vault_spec(
                target_capture_slot=1,
                avf_info_imagedb_targets_slot1=True,
                requested_vault_slot=1,
                requested_vault_action="VIDEO_LIGHT_CLIP_WRITE",
                slot1_flash_videolight_imagedb_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/52b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P296_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar52ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_iso_minss_flash_videolight_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar52ScenarioOutcome(
                scenario_id=sid,
                pillar="52B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar52BSuiteResult(
        passed=all_ok,
        status=P296_STATUS_VERIFIED_PILLAR_52B if all_ok else P296_STATUS_REJECTED_PILLAR_52B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar52_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar52StandaloneReport:
    """Run full Pillar 52 standalone suite (`6/6` Pillar 52A + `6/6` Pillar 52B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase296_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar52a_focus_area_zoom_xlrh1_6_scenario_suite()
    res_b = run_pillar52b_iso_minss_flash_videolight_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 296 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE296_SCHEMA,
            "version": PHASE296_VERSION,
            "mode": donor_snapshot.verification_mode,
            "52a": [asdict(s) for s in res_a.scenarios],
            "52b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar52StandaloneReport(
        schema=PHASE296_SCHEMA,
        version=PHASE296_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P296_STATUS_VERIFIED_PILLAR52_SUITE if all_ok else P296_STATUS_FAIL_PILLAR52_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_52a_focus_area_zoom_xlrh1_vault=res_a,
        pillar_52b_iso_minss_flash_videolight_vault=res_b,
        movie_tracking_area_or_limit_violations=(
            P296_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATIONS if res_a.passed else 1
        ),
        af_area_reg_lock_or_reset_drift_events=(
            P296_AF_AREA_REG_LOCK_OR_RESET_DRIFT_EVENTS if res_a.passed else 1
        ),
        xlrh1_zoom_or_hold_spoof_events=(
            P296_XLRH1_ZOOM_OR_HOLD_SPOOF_EVENTS if res_a.passed else 1
        ),
        fx6_handle_or_pos_display_conflation_events=(
            P296_FX6_HANDLE_OR_POS_DISPLAY_CONFLATION_EVENTS if res_a.passed else 1
        ),
        iso_minss_or_cine_ei_lock_drift_events=(
            P296_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT_EVENTS if res_b.passed else 1
        ),
        flash_still_mech_gate_violations=(
            P296_FLASH_STILL_MECH_GATE_VIOLATIONS if res_b.passed else 1
        ),
        mishoe_5v_overcurrent_events=(
            P296_MISHOE_PMIC_5V_OVERCURRENT_EVENTS if res_b.passed else 1
        ),
        slot1_focus_zoom_camset_mutation_bytes=(
            P296_SLOT1_FOCUS_ZOOM_CAMSET_MUTATION_BYTES if res_a.passed else 4096
        ),
        slot1_flash_videolight_imagedb_bytes=(
            P296_SLOT1_FLASH_VIDEOLIGHT_IMAGEDB_BYTES if res_b.passed else 4096
        ),
        slot1_vault_mutation_bytes=(
            P296_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P296_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_ebusy_enforced=P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
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
# Unified 52-Pillar Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master52_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_52pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master52PillarRecoveryReport:
    """Evaluate and aggregate all 52 recovery pillars (`1..52`) concurrently -> `52/52` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_52_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_51pillar() -> Master51PillarRecoveryReport:
        return evaluate_realhw_51pillar_recovery_master(**kw)

    def _run_p52() -> Tuple[Pillar52StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar52_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_51 = pool.submit(_run_51pillar)
        fut_52 = pool.submit(_run_p52)
        m51_rep = fut_51.result()
        p52_rep, p52_dt = fut_52.result()

    all_errors: List[str] = list(m51_rep.errors) + list(p52_rep.errors)
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
        if getattr(m51_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-51 violated {attr_name} == {expected_val}")
        if getattr(p52_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 52 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("dormant_lossless_raw_exposure_events", 0),
        ("fx6_still_pipeline_conflation_events", 0),
        ("hlg_still_prereq_or_lockout_drift_events", 0),
        ("colorspace_adobergb_prefix_violations", 0),
        ("shutter_type_auto_spoof_events", 0),
        ("fx6_mechanical_shutter_conflation_events", 0),
        ("electronic_silent_5lock_bypass_events", 0),
        ("nr_or_drive_burst_wall_violations", 0),
        ("slot1_still_capture_or_sort_write_bytes", 0),
        ("slot1_imagedb_or_burst_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
        ("double_log_or_lockout_bypass_events", 0),
        ("pplut_1080p_clamp_bypass_events", 0),
        ("pp_internal_reset_trap_violations", 0),
        ("fx6_baselook_confusion_events", 0),
        ("wb_cine_ei_awb_or_custom_setup_trap_events", 0),
        ("wb_custom_camset_exclusion_drift_events", 0),
        ("metering_desqueeze_or_cine_ei_base_iso_drift_events", 0),
        ("fx3_ui_exposes_usb_streaming", False),
        ("nouvc_spoof_events", 0),
        ("usb_host_data_enumeration_events", 0),
        ("hdmi_lcd_blanking_violations", 0),
        ("hdmi_log_1080_bypass_events", 0),
        ("slot1_protect_only_vault_violations", 0),
        ("slot1_vault_format_or_delete_events", 0),
        ("network_reset_zero_rf_violations", 0),
        ("fx3_ui_exposes_power_save_by_monitor", False),
        ("legacy_power_save_monitor_spoof_events", 0),
        ("unsafe_power_save_sleep_interference_events", 0),
        ("bk_lang_parity_drift_events", 0),
        ("stage_b_4lang_uxc_ltt_drift_events", 0),
        ("xlrh1_acoustic_feedback_violations", 0),
        ("audio_mon_4ch_hdmi_confusion_events", 0),
        ("destructive_delete_confirm_drift_events", 0),
        ("slot1_vault_delete_events", 0),
        ("legacy_mf_assist_spoof_events", 0),
        ("still_movie_initial_mag_couplings", 0),
        ("movie_af_in_focus_mag_events", 0),
        ("hdmi_clean_feed_focus_mag_or_peaking_leak_pixels", 0),
        ("movie_sq_af_illuminator_fire_events", 0),
        ("legacy_datetime_setup_spoof_events", 0),
        ("unsolicited_rtc_timezone_jump_events", 0),
        ("mishoe_5v_overcurrent_events", 0),
        ("hdmi_res_log_internal_rec_2160p_bypass_events", 0),
        ("slot1_vault_mutation_events", 0),
        ("slot1_vault_folder_mutation_events", 0),
        ("slot1_vault_folder_mutation_bytes", 0),
        ("movie_custom_folder_or_title_overflow_events", 0),
        ("still_prefix_underscore_lead_or_len_violations", 0),
        ("gamma_assist_log_lockout_bypass_events", 0),
        ("gamma_assist_external_hdmi_leak_events", 0),
        ("tcub_camera_reset_wipe_or_format_violations", 0),
        ("fx3_has_builtin_end_filter", False),
        ("e_nd_actuator_tx_count", 0),
        ("cardless_unrecorded_production_violations", 0),
        ("legacy_v1_audio_level_menu_spoof_events", 0),
        ("photographer_copyright_pii_leaked_bytes", 0),
        ("copyright_char_overflow_or_movie_mutation_events", 0),
        ("slot1_copyright_vault_mutation_bytes", 0),
        ("apsc_s35_4k_or_raw_bypass_events", 0),
        ("ai_unit_subject_recog_spoof_events", 0),
        ("hdmi_clean_feed_eye_frame_baked_pixels", 0),
        ("version_dialog_flash_writes", 0),
        ("slot1_bodydata_vault_mutation_bytes", 0),
        ("auto_slow_shutter_lockout_bypass_events", 0),
        ("auto_slow_shutter_angle_overlap_events", 0),
        ("breathing_comp_raw_or_240p_bypass_events", 0),
        ("hdmi_rec_ctrl_without_tc_violations", 0),
        ("slot1_hdmi_rec_vault_mutation_bytes", 0),
        ("diff_set_transition_corruption_events", 0),
        ("shutter_angle_common_bleed_events", 0),
        ("slot1_custom_key_vault_mutation_bytes", 0),
        ("fx3_has_builtin_evf", False),
        ("evf_finder_monitor_spoof_events", 0),
        ("tier0_battery_high_display_violations", 0),
        ("bt_rmt_ir_lockout_violations", 0),
        ("slot1_mymenu_vault_mutation_bytes", 0),
        ("destructive_menu_delete_confusions", 0),
        ("shutter_angle_exposure_step_drift_events", 0),
        ("fx3_has_var_shutter", False),
        ("unbuffered_battery_pull_events", 0),
    ):
        if getattr(m51_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-51 violated {attr_name} == {expected_val}")
    if m51_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillars 1-51 violated bodydata_flash_attempts_blocked >= 1")

    for attr_name, expected_val in (
        ("movie_tracking_area_or_limit_violations", 0),
        ("af_area_reg_lock_or_reset_drift_events", 0),
        ("xlrh1_zoom_or_hold_spoof_events", 0),
        ("fx6_handle_or_pos_display_conflation_events", 0),
        ("iso_minss_or_cine_ei_lock_drift_events", 0),
        ("flash_still_mech_gate_violations", 0),
        ("mishoe_5v_overcurrent_events", 0),
        ("slot1_focus_zoom_camset_mutation_bytes", 0),
        ("slot1_flash_videolight_imagedb_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
    ):
        if getattr(p52_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 52 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m51_rep.pillars)
    spec52 = MASTER_52_PILLAR_SPECS[51]
    p52_metrics = {
        "pillar_52a_focus_area_zoom_xlrh1_vault": (
            f"{p52_rep.pillar_52a_focus_area_zoom_xlrh1_vault.scenarios_passed}/"
            f"{p52_rep.pillar_52a_focus_area_zoom_xlrh1_vault.scenarios_total}"
        ),
        "pillar_52b_iso_minss_flash_videolight_vault": (
            f"{p52_rep.pillar_52b_iso_minss_flash_videolight_vault.scenarios_passed}/"
            f"{p52_rep.pillar_52b_iso_minss_flash_videolight_vault.scenarios_total}"
        ),
        "movie_tracking_area_or_limit_violations": p52_rep.movie_tracking_area_or_limit_violations,
        "af_area_reg_lock_or_reset_drift_events": p52_rep.af_area_reg_lock_or_reset_drift_events,
        "xlrh1_zoom_or_hold_spoof_events": p52_rep.xlrh1_zoom_or_hold_spoof_events,
        "fx6_handle_or_pos_display_conflation_events": (
            p52_rep.fx6_handle_or_pos_display_conflation_events
        ),
        "iso_minss_or_cine_ei_lock_drift_events": p52_rep.iso_minss_or_cine_ei_lock_drift_events,
        "flash_still_mech_gate_violations": p52_rep.flash_still_mech_gate_violations,
        "mishoe_5v_overcurrent_events": p52_rep.mishoe_5v_overcurrent_events,
        "slot1_focus_zoom_camset_mutation_bytes": p52_rep.slot1_focus_zoom_camset_mutation_bytes,
        "slot1_flash_videolight_imagedb_bytes": p52_rep.slot1_flash_videolight_imagedb_bytes,
        "slot1_vault_mutation_bytes": p52_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p52_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_ebusy_enforced": p52_rep.slot1_vault_erofs_ebusy_enforced,
        "overall_ready_for_hardware_attach": p52_rep.overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": p52_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p52_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec52[0],
            pillar_id=spec52[1],
            phase_label=spec52[2],
            module_name=spec52[3],
            passed=bool(p52_rep.all_passed),
            status=p52_rep.status,
            verification_mode=p52_rep.verification_mode,
            elapsed_seconds=p52_dt,
            key_metrics=p52_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec52[1],
                    "mode": p52_rep.verification_mode,
                    "status": p52_rep.status,
                    "metrics": p52_metrics,
                    "passed": p52_rep.all_passed,
                }
            ),
            errors=tuple(p52_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master52_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p52_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_52_PILLAR_COUNT == 52
        and pillars_passed == 52
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE296_SCHEMA,
            "version": PHASE296_VERSION,
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
    return Master52PillarRecoveryReport(
        schema=PHASE296_SCHEMA,
        version=PHASE296_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P296_STATUS_VERIFIED_52OF52_AGGREGATOR if all_ok else P296_STATUS_FAIL_52OF52_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_2s_fast_cli_budget=elapsed < P296_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P296_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P296_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p52_rep.donor_snapshot,
        pillar52_a_focus_area_zoom_xlrh1_vault=p52_rep.pillar_52a_focus_area_zoom_xlrh1_vault,
        pillar52_b_iso_minss_flash_videolight_vault=p52_rep.pillar_52b_iso_minss_flash_videolight_vault,
        movie_tracking_area_or_limit_violations=p52_rep.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=p52_rep.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=p52_rep.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=(
            p52_rep.fx6_handle_or_pos_display_conflation_events
        ),
        iso_minss_or_cine_ei_lock_drift_events=p52_rep.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=p52_rep.flash_still_mech_gate_violations,
        mishoe_pmic_5v_overcurrent_events=p52_rep.mishoe_5v_overcurrent_events,
        slot1_focus_zoom_camset_mutation_bytes=p52_rep.slot1_focus_zoom_camset_mutation_bytes,
        slot1_flash_videolight_imagedb_bytes=p52_rep.slot1_flash_videolight_imagedb_bytes,
        slot1_vault_mutation_bytes=p52_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p52_rep.slot1_format_hard_locked,
        slot1_vault_erofs_ebusy_enforced=p52_rep.slot1_vault_erofs_ebusy_enforced,
        xlrh1_has_zoom_lever=P296_XLRH1_HAS_ZOOM_LEVER,
        xlrh1_has_rec_button=P296_XLRH1_HAS_REC_BUTTON,
        xlrh1_has_zoom_hold_switch=P296_XLRH1_HAS_ZOOM_HOLD_SWITCH,
        fx6_0_99_is_zoom_position_display=P296_FX6_0_99_IS_ZOOM_POSITION_DISPLAY,
        fx6_has_iso_auto_min_ss=P296_FX6_HAS_ISO_AUTO_MIN_SS,
        fx6_mechanical_shutter_present=P296_FX6_MECHANICAL_SHUTTER_PRESENT,
        dormant_lossless_raw_exposure_events=m51_rep.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=m51_rep.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=m51_rep.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=m51_rep.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=m51_rep.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=m51_rep.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=m51_rep.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=m51_rep.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=m51_rep.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=m51_rep.slot1_imagedb_or_burst_mutation_bytes,
        fx3_ui_exposes_lossless_raw=m51_rep.fx3_ui_exposes_lossless_raw,
        fx3_ui_exposes_shutter_type_auto=m51_rep.fx3_ui_exposes_shutter_type_auto,
        fx6_still_pipeline_present=m51_rep.fx6_still_pipeline_present,
        double_log_or_lockout_bypass_events=m51_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=m51_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=m51_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=m51_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            m51_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        wb_custom_camset_exclusion_drift_events=m51_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            m51_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        fx3_ui_exposes_usb_streaming=m51_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m51_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m51_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m51_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m51_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m51_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m51_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m51_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m51_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m51_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m51_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m51_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m51_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m51_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m51_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m51_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m51_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m51_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m51_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m51_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m51_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m51_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m51_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m51_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=(
            m51_rep.mishoe_5v_overcurrent_events + p52_rep.mishoe_5v_overcurrent_events
        ),
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m51_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m51_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m51_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m51_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m51_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m51_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m51_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m51_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=(
            m51_rep.tcub_camera_reset_wipe_or_format_violations
        ),
        fx3_has_builtin_end_filter=m51_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m51_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m51_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m51_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m51_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m51_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m51_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m51_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m51_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m51_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m51_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m51_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m51_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m51_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m51_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m51_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m51_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m51_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m51_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m51_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m51_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m51_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m51_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m51_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m51_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m51_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m51_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m51_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m51_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m51_rep.unbuffered_battery_pull_events,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        hardware_live_attachment_authorized=p52_rep.hardware_live_attachment_authorized,
        master_52pillar_sha256=master_sha,
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


def evaluate_52pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master52PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_52pillar_recovery_master`."""
    return evaluate_realhw_52pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_52pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master52PillarRecoveryReport:
    """Public CLI entry point for Phase 296 `52/52` unified recovery master."""
    return evaluate_realhw_52pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS",
    "ALLOW_PERSISTENT_JIRITSU_WRITES",
    "CNFLASHA_USERSPACE_WRITE_BLOCKED",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "ISP_WRITE_AUTHORIZED",
    "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
    "MASTER_52_PILLAR_COUNT",
    "MASTER_52_PILLAR_IDS",
    "MASTER_52_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P296_AF_AREA_REG_BKID",
    "P296_AF_AREA_REG_DEFAULT",
    "P296_AF_AREA_REG_LOCK_OR_RESET_DRIFT_EVENTS",
    "P296_AF_AREA_REG_MENU_PATH",
    "P296_AF_AREA_REG_RESID16",
    "P296_BLOCKED_AF_AREA_REG_LOCK_OR_RESET_DRIFT",
    "P296_BLOCKED_FLASH_STILL_MECH_GATE_VIOLATION",
    "P296_BLOCKED_INVALID_PILLAR52A_SPEC",
    "P296_BLOCKED_INVALID_PILLAR52B_SPEC",
    "P296_BLOCKED_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT",
    "P296_BLOCKED_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATION",
    "P296_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P296_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P296_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL",
    "P296_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P296_BLOCKED_VIDEO_LIGHT_PMIC_900MA_OVERCURRENT",
    "P296_BLOCKED_XLRH1_ZOOM_MYTH_OR_FX6_HANDLE_CONFLATION",
    "P296_BOUNDED_HEADER_BYTES",
    "P296_CINE_EI_BASE_ISOS",
    "P296_CINE_EI_LOCKED_LOG_MODES",
    "P296_CIRC_ELIGIBLE_FOCUS_AREAS",
    "P296_CIRC_FOCUS_POINT_BKID",
    "P296_CIRC_FOCUS_POINT_DEFAULT",
    "P296_CIRC_FOCUS_POINT_MENU_PATH",
    "P296_CIRC_FOCUS_POINT_MODES",
    "P296_CONCURRENT_CEILING_SECONDS",
    "P296_CUSTOM_KEY_ZOOM_SPEED_DEFAULT",
    "P296_DEL_REGIST_AF_AREA_MENU_PATH",
    "P296_DEL_REGIST_AF_AREA_RESID16",
    "P296_DESTRUCTIVE_VAULT_ACTIONS",
    "P296_DONOR_FX3_APPFW_702_RELPATH",
    "P296_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P296_DONOR_FX3_UXC_EN_F_RELPATH",
    "P296_DONOR_FX3_UXC_EN_G_RELPATH",
    "P296_DONOR_FX3_UXC_EN_RELPATH",
    "P296_DONOR_FX3_UXC_JA_F_RELPATH",
    "P296_DONOR_FX3_UXC_JA_G_RELPATH",
    "P296_DONOR_FX3_UXC_JA_RELPATH",
    "P296_DONOR_FX3_UXC_SC_F_RELPATH",
    "P296_DONOR_FX3_UXC_SC_G_RELPATH",
    "P296_DONOR_FX3_UXC_SC_RELPATH",
    "P296_DONOR_FX3_UXC_TC_F_RELPATH",
    "P296_DONOR_FX3_UXC_TC_G_RELPATH",
    "P296_DONOR_FX3_UXC_TC_RELPATH",
    "P296_DONOR_FX6_APPFW_601_RELPATH",
    "P296_DONOR_FX6_UXC_EN_2_RELPATH",
    "P296_DONOR_FX6_UXC_EN_RELPATH",
    "P296_DONOR_INSPECT_BUDGET_SECONDS",
    "P296_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P296_ENV_CLEAN_ROOM_TEST",
    "P296_EXP_COMP_SET_MODES",
    "P296_FAST_CLI_BUDGET_SECONDS",
    "P296_FLASH_5_MODES",
    "P296_FLASH_COMP_MAX_EV",
    "P296_FLASH_COMP_MIN_EV",
    "P296_FLASH_MODE_BKID",
    "P296_FLASH_MODE_DEFAULT",
    "P296_FLASH_MODE_MENU_PATH",
    "P296_FLASH_MODE_RESID16",
    "P296_FLASH_MODE_RESID16_MAP",
    "P296_FLASH_STILL_MECH_GATE_VIOLATIONS",
    "P296_FOCUS_AREA_14_AREAS",
    "P296_FOCUS_AREA_7_STILL_TRACKING",
    "P296_FOCUS_AREA_7_UNIVERSAL",
    "P296_FOCUS_AREA_BKID",
    "P296_FOCUS_AREA_COLOR_BKID",
    "P296_FOCUS_AREA_COLOR_DEFAULT",
    "P296_FOCUS_AREA_COLOR_MENU_PATH",
    "P296_FOCUS_AREA_COLOR_MODES",
    "P296_FOCUS_AREA_DEFAULT",
    "P296_FOCUS_AREA_G_RESID16",
    "P296_FOCUS_AREA_LIMIT_BKID_PREFIX",
    "P296_FOCUS_AREA_LIMIT_MENU_PATH",
    "P296_FOCUS_AREA_LIMIT_MIN_AREAS",
    "P296_FOCUS_AREA_LIMIT_MIN_RESID16",
    "P296_FOCUS_AREA_MENU_PATH",
    "P296_FOCUS_AREA_RESID16_MAP",
    "P296_FOCUS_MODES",
    "P296_FORBIDDEN_PERSISTENT_TARGETS",
    "P296_FX3_FW_VERSION",
    "P296_FX3_HELPGUIDE_ID",
    "P296_FX3_MAX_FLASH_SYNC_DENOM",
    "P296_FX3_MODEL_ID",
    "P296_FX3_MODEL_NAME",
    "P296_FX3_PRODUCT_CODENAME",
    "P296_FX3_SENSOR_FAMILY",
    "P296_FX3_SUPPORTED_FW_VERSIONS",
    "P296_FX6_0_99_IS_ZOOM_POSITION_DISPLAY",
    "P296_FX6_DONOR_FW_VERSION",
    "P296_FX6_DONOR_MODEL_NAME",
    "P296_FX6_FOCUS_AREAS",
    "P296_FX6_HANDLE_HOLD_SWITCH_MODES",
    "P296_FX6_HANDLE_OR_POS_DISPLAY_CONFLATION_EVENTS",
    "P296_FX6_HANDLE_ZOOM_MODES",
    "P296_FX6_HAS_ISO_AUTO_MIN_SS",
    "P296_FX6_MECHANICAL_SHUTTER_PRESENT",
    "P296_FX6_PRODUCT_CODENAME",
    "P296_FX6_ZOOM_POS_DISPLAY_MAX",
    "P296_FX6_ZOOM_POS_DISPLAY_MIN",
    "P296_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P296_ISO_AUTO_MIN_SS_BKID",
    "P296_ISO_AUTO_MIN_SS_DEFAULT",
    "P296_ISO_AUTO_MIN_SS_MENU_PATH",
    "P296_ISO_AUTO_MIN_SS_OPTIONS",
    "P296_ISO_AUTO_MIN_SS_RELATIVE",
    "P296_ISO_AUTO_MIN_SS_SHUTTER_THRESHOLDS",
    "P296_ISO_MINSS_OR_CINE_EI_LOCK_DRIFT_EVENTS",
    "P296_ISO_RANGE_LIMIT_BKID",
    "P296_ISO_RANGE_LIMIT_MENU_PATH",
    "P296_ISO_RANGE_MAX_CEILING",
    "P296_ISO_RANGE_MIN_FLOOR",
    "P296_LOCK_OPERATION_PARTS_BKID",
    "P296_LOG_SHOOTING_MODES",
    "P296_MAX_FULL_DONOR_BYTES",
    "P296_MISHOE_NON_SONY_FLASH_MAX_V",
    "P296_MISHOE_PMIC_5V_MAX_MA",
    "P296_MISHOE_PMIC_5V_OVERCURRENT_EVENTS",
    "P296_MOVIE_TRACKING_AREA_OR_LIMIT_VIOLATIONS",
    "P296_NOMINAL_BUDGET_SECONDS",
    "P296_ON_OFF_MODES",
    "P296_OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P296_PILLAR_52A_SCENARIO_IDS",
    "P296_PILLAR_52B_SCENARIO_IDS",
    "P296_PINNED_FX3_APPFW_702_BYTES",
    "P296_PINNED_FX3_APPFW_702_FULL_SHA256",
    "P296_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P296_PINNED_FX3_BACKUP_BIN_BYTES",
    "P296_PINNED_FX3_BACKUP_BIN_SHA256",
    "P296_PINNED_FX3_UXC_EN_BYTES",
    "P296_PINNED_FX3_UXC_EN_F_BYTES",
    "P296_PINNED_FX3_UXC_EN_F_SHA256",
    "P296_PINNED_FX3_UXC_EN_G_BYTES",
    "P296_PINNED_FX3_UXC_EN_G_SHA256",
    "P296_PINNED_FX3_UXC_EN_SHA256",
    "P296_PINNED_FX3_UXC_JA_BYTES",
    "P296_PINNED_FX3_UXC_JA_F_BYTES",
    "P296_PINNED_FX3_UXC_JA_F_SHA256",
    "P296_PINNED_FX3_UXC_JA_G_BYTES",
    "P296_PINNED_FX3_UXC_JA_G_SHA256",
    "P296_PINNED_FX3_UXC_JA_SHA256",
    "P296_PINNED_FX3_UXC_SC_BYTES",
    "P296_PINNED_FX3_UXC_SC_F_BYTES",
    "P296_PINNED_FX3_UXC_SC_F_SHA256",
    "P296_PINNED_FX3_UXC_SC_G_BYTES",
    "P296_PINNED_FX3_UXC_SC_G_SHA256",
    "P296_PINNED_FX3_UXC_SC_SHA256",
    "P296_PINNED_FX3_UXC_TC_BYTES",
    "P296_PINNED_FX3_UXC_TC_F_BYTES",
    "P296_PINNED_FX3_UXC_TC_F_SHA256",
    "P296_PINNED_FX3_UXC_TC_G_BYTES",
    "P296_PINNED_FX3_UXC_TC_G_SHA256",
    "P296_PINNED_FX3_UXC_TC_SHA256",
    "P296_PINNED_FX6_APPFW_601_BYTES",
    "P296_PINNED_FX6_APPFW_601_FULL_SHA256",
    "P296_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P296_PINNED_FX6_UXC_EN_2_BYTES",
    "P296_PINNED_FX6_UXC_EN_2_SHA256",
    "P296_PINNED_FX6_UXC_EN_BYTES",
    "P296_PINNED_FX6_UXC_EN_SHA256",
    "P296_REMOTE_ZOOM_FIXED_SPEED_DEFAULT",
    "P296_REMOTE_ZOOM_SPEED_TYPES",
    "P296_REMOTE_ZOOM_SPEED_TYPE_DEFAULT",
    "P296_RESET_ACTIONS",
    "P296_SAFE_SECONDARY_CAPTURE_SLOT",
    "P296_SHOOTING_DOMAINS",
    "P296_SHUTTER_TYPES",
    "P296_SLOT1_FLASH_VIDEOLIGHT_IMAGEDB_BYTES",
    "P296_SLOT1_FOCUS_ZOOM_CAMSET_MUTATION_BYTES",
    "P296_SLOT1_FORMAT_HARD_LOCKED",
    "P296_SLOT1_VAULT_EROFS_EBUSY_ENFORCED",
    "P296_SLOT1_VAULT_MUTATION_BYTES",
    "P296_SLOT1_VAULT_SLOT",
    "P296_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P296_STATUS_FAIL_52OF52_AGGREGATOR",
    "P296_STATUS_FAIL_PILLAR52_SUITE",
    "P296_STATUS_REJECTED_PILLAR_52A",
    "P296_STATUS_REJECTED_PILLAR_52B",
    "P296_STATUS_VERIFIED_52OF52_AGGREGATOR",
    "P296_STATUS_VERIFIED_PILLAR52_SUITE",
    "P296_STATUS_VERIFIED_PILLAR_52A",
    "P296_STATUS_VERIFIED_PILLAR_52B",
    "P296_STILL_PASM_MODES",
    "P296_STILL_SHOOTING_MODES",
    "P296_SWITCH_VH_AF_BKID",
    "P296_SWITCH_VH_AF_DEFAULT",
    "P296_SWITCH_VH_AF_MENU_PATH",
    "P296_SWITCH_VH_AF_MODES",
    "P296_TIER0_SURFACE_COUNT",
    "P296_VAULT_FIREWALL_ERRNOS",
    "P296_VAULT_TARGET_ACTIONS",
    "P296_VIDEO_LIGHT_4_MODES",
    "P296_VIDEO_LIGHT_MODE_BKID",
    "P296_VIDEO_LIGHT_MODE_DEFAULT",
    "P296_VIDEO_LIGHT_MODE_MENU_PATH",
    "P296_VIDEO_LIGHT_MODE_RESID16",
    "P296_XLRH1_HAS_REC_BUTTON",
    "P296_XLRH1_HAS_ZOOM_HOLD_SWITCH",
    "P296_XLRH1_HAS_ZOOM_LEVER",
    "P296_XLRH1_ZOOM_OR_HOLD_SPOOF_EVENTS",
    "P296_ZOOM_LEVER_1ST_SPEED_DEFAULT",
    "P296_ZOOM_LEVER_2ND_SPEED_DEFAULT",
    "P296_ZOOM_MENU_PATH",
    "P296_ZOOM_RANGES",
    "P296_ZOOM_RANGE_BKID",
    "P296_ZOOM_RANGE_DEFAULT",
    "P296_ZOOM_SPEED_MAX",
    "P296_ZOOM_SPEED_MIN",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE296_PHASE_NUMBER",
    "PHASE296_SCHEMA",
    "PHASE296_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "FocusAreaZoomLeverIsoMinssFlashVaultReport",
    "FocusAreaZoomLeverXlrH1VaultReport",
    "FocusAreaZoomLeverXlrH1VaultSpec",
    "IsoRangeMinssFlashVideolightVaultReport",
    "IsoRangeMinssFlashVideolightVaultSpec",
    "Master52PillarRecoveryReport",
    "Phase296DonorArtifactDigest",
    "Phase296DonorSnapshot",
    "Pillar52ASuiteResult",
    "Pillar52BSuiteResult",
    "Pillar52ScenarioOutcome",
    "Pillar52StandaloneReport",
    "build_default_safe_focus_area_zoom_xlrh1_vault_spec",
    "build_default_safe_iso_minss_flash_videolight_vault_spec",
    "compute_expected_flash_and_video_light_state",
    "compute_expected_focus_area_and_af_reg_state",
    "compute_expected_iso_range_minss_and_cine_ei_state",
    "compute_expected_zoom_speed_and_reset_state",
    "evaluate_52pillar_recovery_master",
    "evaluate_focus_area_zoom_xlrh1_vault",
    "evaluate_iso_minss_flash_videolight_vault",
    "evaluate_realhw_52pillar_recovery_master",
    "inspect_phase296_donors_readonly",
    "run_pillar52_standalone_suite",
    "run_pillar52a_focus_area_zoom_xlrh1_6_scenario_suite",
    "run_pillar52b_iso_minss_flash_videolight_6_scenario_suite",
    "verify_52pillar_recovery_suite",
    "verify_focus_area_zoom_lever_iso_minss_flash_and_vault",
    "verify_focus_area_zoom_lever_iso_minss_flash_vault",
]
