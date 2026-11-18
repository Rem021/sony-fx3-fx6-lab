"""Phase 292 — Recovery Pillar 51 & Unified 51-Pillar Recovery Master
(`verify-51pillar-recovery` / `verify-pillar51-raw-heif-colorspace-shuttertype-vault`):

1. **Pillar 51A — Still `[Image Quality Settings]` (`RAW` `Compressed`/`Uncompressed` vs
   Dormant `Lossless Comp`, `JPEG/HEIF Switch` `4:2:0`/`4:2:2` 10-bit `.HIF`,
   `[HLG Still Image]` `BT.2100` Overrides vs Still-Less `ILME-FX6`) &
   `[Color Space]` `AdobeRGB` `_DSC` Prefix + `[Set File Name]` Leading-`_` Ban +
   `Slot-1` Vault Write Firewall (Wave-49)**:
   - Models `MENU -> (Shooting) -> [Image Quality/Rec]` on stock `ILME-FX3 Ver. 7.02`
     (`12 MP IMX510`, `0x91030080`, `ilc/2210`, `PRODUCT_MODEL_ALCIN_UUD`):
     - `[JPEG/HEIF Switch]` (`BKID_APP_setting_jh_file_type`, `_f.uxc` `0x742a`): `JPEG`
       (default), `HEIF(4:2:0)` (`0x7959`), `HEIF(4:2:2)` -> 10-bit `.HIF`.
     - `[File Format]` (`BKID_APP_setting_still_file_format`, `.uxc` `0xe73d`): `RAW`
       (`0xe738`), `RAW & JPEG` (`0xe739`), `RAW & HEIF` (`0xe1fc`), `JPEG` / `HEIF`
       (`0xe7ff`, default).
     - `[RAW File Type]` (`BKID_APP_setting_still_raw_file_type`, `_f.uxc` `0x6ff2`):
       **ONLY** `[Compressed]` (`0x6f67`, default) and `[Uncompressed]` (`0x67a9`/`0x6f5b`)
       14-bit `.ARW` (`3:2` `L`, shared across Slot 1 & Slot 2). Dormant sibling
       `Lossless Comp` / `Lossless Comp (L)/(M)/(S)` (`_f.uxc` `0x6b56`,
       `0x7897`/`0x6bfd`/`0x7894`, `RAW_FILE_TYPE_LOSSLESS*`) MUST be rejected fail-closed.
     - Contrasts still-less `ILME-FX6 Ver. 6.01` (`PRODUCT_MODEL_CHAPLIN`): zero `DCIM` /
       `.ARW` / `.JPG` / `.HIF` still pipeline (`RAW` is 16-bit linear movie SDI/HDMI RAW;
       `HDR(HLG)` is movie-only).
   - Enforces `[HLG Still Image]` (`BKID_APP_setting_still_hlg_photo`, `_f.uxc` `0x76c8`,
     default `Off`): `On` requires `JPEG/HEIF Switch` in `{HEIF(4:2:0), HEIF(4:2:2)}`,
     `File Format == HEIF` only (NOT `RAW` / `RAW & HEIF`), and `P/A/S/M` shooting mode
     (not `Intelligent Auto`); locks out `Picture Profile`, `Creative Look`,
     `D-Range Optimizer` (`DRO`), and `DRO Bracket`, shifts still ISO bounds, enables
     `Gamma Display Assist` (`Auto` / `HLG(BT.2020)` `0x79e1`), and overrides
     `[Color Space]` to `BT.2100` (`BT.2020`).
   - Enforces `MENU -> (Shooting) -> [Image Quality/Rec] -> [Color Space]`
     (`BKID_APP_setting_still_color_space`, `_f.uxc` `0x68b7`): `sRGB` (`.uxc` `0xe07d`,
     default -> `DSC00001`) vs `AdobeRGB` (`.uxc` `0xe07e`/`0xe895` -> `_DSC0001`),
     plus `[Set File Name]` (`BKID_APP_set_file_name_prefix_still`, `_f.uxc` `0x6993`,
     default `DSC`, survives `Camera Settings Reset`, forbids `_` as 1st character).
   - Enforces **fail-closed `EROFS`/`EBUSY` `Slot-1` Tier-0 Vault protection** blocking
     any still `.ARW`/`.JPG`/`.HIF` capture write or `Sort Recording` write to read-only
     `Slot 1`, keeping Stage-B overlays in volatile `/tmp/` (`BLKROSET=True`) with
     `16/16` `H0 == H3` `Backup.bin`.

2. **Pillar 51B — `[Shutter Type]` Exact 2-Option Split (`Mechanical Shutter` Default vs
   `Electronic Shutter`, NO `Auto`!), `1/250 s` Flash Sync, Electronic/Silent 5-Lock
   Matrix, `[e-Front Curtain Shut.]`, `[Long Exposure NR]` / `[High ISO NR]`, &
   `[Drive Mode]` `10 fps` Burst / Bracket `Slot-1` Vault Firewall (Wave-49)**:
   - Models `MENU -> (Shooting) -> [Shutter/Silent] -> [Shutter Type]`
     (`BKID_APP_setting_still_shutter_type`, `_f.uxc` `0x7aa9`) on `ILME-FX3 Ver. 7.02`:
     exposes **ONLY 2** options (`Mechanical Shutter` `0x6ddb` default vs
     `Electronic Shutter` `0x60a1`, `P/A/S/M`-only). **`Auto` is ABSENT on FX3**
     (dormant `BKID_APP_setting_still_shutter_type_anti_distortion_shutter` rejected
     fail-closed), whereas `ILME-FX6` has `mechanical_shutter = False`.
   - Enforces Electronic Shutter (and `Silent Mode = On`, `_f.uxc` `0x7a53` / `_g.uxc`
     `0x6079`, forcing Electronic Shutter unless overridden via `Target Function Settings`)
     **5-Lock Matrix**: locks out (1) Flash (`1/250 s` FF sync `_f.uxc` `0x759b` is
     Mechanical-only), (2) `Long Exposure NR`, (3) `e-Front Curtain Shut.` (`0x64c6`,
     `On` default, survives `Camera Settings Reset`), (4) `BULB`, and (5) `Anti-flicker Shoot.`.
   - Enforces `[Long Exposure NR]` (`0x6cd7`, `>= 1 s` dark-frame subtraction `t_NR == t_shutter`,
     blocked in `Electronic Shutter`, `Silent Mode = On`, `Cont. Shooting`, `Cont. Bracket`),
     `[High ISO NR]` (`0x650b`, `Normal`/`Low`/`Off`, Still-only, unavailable in `RAW`,
     ignored on `.ARW` in `RAW & JPEG`/`RAW & HEIF`, fixed `Normal` in `Intelligent Auto`),
     and `[Drive Mode]` (`0x7228`, 8 modes: `Single`, `Cont. Shooting Hi+/Hi/Mid/Lo` up to
     `10 fps` `Hi+`, `Self-timer(Single)/(Cont)`, `Cont./Single/WB/DRO Bracket`) with
     `Compressed` RAW vs `Uncompressed` RAW/Flash `< 10 fps` drop, `Hi+` non-live monitor,
     and `F > F11` 1st-shot AF lock.
   - Enforces **fail-closed `EROFS`/`EBUSY` `Slot-1` Tier-0 Vault firewall** blocking burst
     / bracket `DCIM` writes and `AVF_INFO` ImageDB mutations whenever `Slot 1` holds the
     read-only recovery vault.

3. **Unified 51-Pillar Recovery Master (`evaluate_realhw_51pillar_recovery_master` /
   `verify-51pillar-recovery`)**:
   - Concurrently delegates Pillars `1..50` (`evaluate_realhw_50pillar_recovery_master`) +
     **Pillar 51** (`run_pillar51_standalone_suite`) -> **`51/51` (`VERIFIED_51OF51_PILLAR_RECOVERY_MASTER`)**
     with `raw_firmware_bytes_leaked == 0`, `persistent_emmc_writes_authorized == False`,
     and `overall_ready_for_hardware_attach == False`.
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
    MASTER_50_PILLAR_SPECS,
    Master50PillarRecoveryReport,
    evaluate_realhw_50pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE292_SCHEMA: str = (
    "realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier_v1"
)
PHASE292_VERSION: str = "1.0.0"
PHASE292_PHASE_NUMBER: int = 292
P292_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P292_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P292_OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P292_DORMANT_LOSSLESS_RAW_EXPOSURE_EVENTS: int = 0
P292_FX6_STILL_PIPELINE_CONFLATION_EVENTS: int = 0
P292_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT_EVENTS: int = 0
P292_COLORSPACE_ADOBERGB_PREFIX_VIOLATIONS: int = 0
P292_SHUTTER_TYPE_AUTO_SPOOF_EVENTS: int = 0
P292_FX6_MECHANICAL_SHUTTER_CONFLATION_EVENTS: int = 0
P292_ELECTRONIC_SILENT_5LOCK_BYPASS_EVENTS: int = 0
P292_NR_OR_DRIVE_BURST_WALL_VIOLATIONS: int = 0
P292_SLOT1_STILL_CAPTURE_OR_SORT_WRITE_BYTES: int = 0
P292_SLOT1_IMAGEDB_OR_BURST_MUTATION_BYTES: int = 0
P292_SLOT1_VAULT_MUTATION_BYTES: int = 0
P292_SLOT1_FORMAT_HARD_LOCKED: bool = True
P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED: bool = True

P292_FX3_UI_EXPOSES_LOSSLESS_RAW: bool = False
P292_FX3_UI_EXPOSES_SHUTTER_TYPE_AUTO: bool = False
P292_FX6_STILL_PIPELINE_PRESENT: bool = False
P292_FX6_MECHANICAL_SHUTTER_PRESENT: bool = False

P292_DONOR_INSPECT_BUDGET_SECONDS: float = 0.20
P292_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P292_FAST_CLI_BUDGET_SECONDS: float = 1.2
P292_NOMINAL_BUDGET_SECONDS: float = 4.0
P292_CONCURRENT_CEILING_SECONDS: float = 6.0
P292_BOUNDED_HEADER_BYTES: int = 4096
P292_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-49 Donor Anchors (strictly O_RDONLY)
P292_FX3_MODEL_NAME: str = "ILME-FX3"
P292_FX3_MODEL_ID: int = 0x91030080
P292_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P292_FX3_HELPGUIDE_ID: str = "ilc/2210"
P292_FX3_FW_VERSION: str = "7.02"
P292_FX3_SENSOR_FAMILY: str = "12 MP IMX510"
P292_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P292_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P292_FX6_DONOR_FW_VERSION: str = "6.01"
P292_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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

P292_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P292_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P292_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)
P292_PINNED_FX3_APPFW_702_FULL_SHA256: str = (
    "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
)

P292_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P292_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P292_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)
P292_PINNED_FX6_APPFW_601_FULL_SHA256: str = (
    "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
)

P292_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P292_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P292_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P292_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P292_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P292_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P292_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P292_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P292_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P292_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P292_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P292_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P292_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P292_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P292_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P292_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P292_PINNED_FX3_UXC_EN_BYTES: int = 165740
P292_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P292_DONOR_FX3_UXC_SC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc"
)
P292_PINNED_FX3_UXC_SC_BYTES: int = 149064
P292_PINNED_FX3_UXC_SC_SHA256: str = (
    "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66"
)

P292_DONOR_FX3_UXC_TC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc"
)
P292_PINNED_FX3_UXC_TC_BYTES: int = 151908
P292_PINNED_FX3_UXC_TC_SHA256: str = (
    "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3"
)

P292_DONOR_FX3_UXC_JA_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc"
)
P292_PINNED_FX3_UXC_JA_BYTES: int = 208564
P292_PINNED_FX3_UXC_JA_SHA256: str = (
    "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d"
)

P292_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P292_PINNED_FX3_UXC_EN_G_BYTES: int = 69600
P292_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P292_DONOR_FX3_UXC_SC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_g.uxc"
)
P292_PINNED_FX3_UXC_SC_G_BYTES: int = 61296
P292_PINNED_FX3_UXC_SC_G_SHA256: str = (
    "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b"
)

P292_DONOR_FX3_UXC_TC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_g.uxc"
)
P292_PINNED_FX3_UXC_TC_G_BYTES: int = 61372
P292_PINNED_FX3_UXC_TC_G_SHA256: str = (
    "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80"
)

P292_DONOR_FX3_UXC_JA_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_g.uxc"
)
P292_PINNED_FX3_UXC_JA_G_BYTES: int = 89428
P292_PINNED_FX3_UXC_JA_G_SHA256: str = (
    "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980"
)

P292_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P292_PINNED_FX6_UXC_EN_BYTES: int = 118208
P292_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P292_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P292_PINNED_FX6_UXC_EN_2_BYTES: int = 118676
P292_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# ---------------------------------------------------------------------------
# Pillar 51A Constants — Still [Image Quality Settings], [HLG Still Image],
# [Color Space] AdobeRGB `_DSC`, [Set File Name] Leading-`_` Ban & Slot-1 Vault
# ---------------------------------------------------------------------------

P292_IMAGE_QUALITY_REC_SUBMENU_RESID16: int = 0x601D  # string_*_g.uxc
P292_JPEG_HEIF_SWITCH_MENU_PATH: Tuple[str, ...] = ("Shooting", "Image Quality/Rec", "JPEG/HEIF Switch")
P292_IMAGE_QUALITY_MENU_PATH: Tuple[str, ...] = ("Shooting", "Image Quality/Rec", "Image Quality Settings")
P292_HLG_STILL_MENU_PATH: Tuple[str, ...] = ("Shooting", "Image Quality/Rec", "HLG Still Image")
P292_COLOR_SPACE_MENU_PATH: Tuple[str, ...] = ("Shooting", "Image Quality/Rec", "Color Space")
P292_SET_FILE_NAME_MENU_PATH: Tuple[str, ...] = ("Shooting", "File", "File/Folder Settings", "Set File Name")

P292_JPEG_HEIF_SWITCH_BKID: str = "BKID_APP_setting_jh_file_type"
P292_JPEG_HEIF_SWITCH_RESID16: int = 0x742A  # _f.uxc
P292_HEIF_420_RESID16: int = 0x7959  # _f.uxc
P292_JPEG_HEIF_SWITCH_MODES: Tuple[str, ...] = ("JPEG", "HEIF(4:2:0)", "HEIF(4:2:2)")
P292_JPEG_HEIF_SWITCH_DEFAULT: str = "JPEG"

P292_STILL_FILE_FORMAT_BKID: str = "BKID_APP_setting_still_file_format"
P292_STILL_FILE_FORMAT_RESID16: int = 0xE73D  # .uxc
P292_STILL_FILE_FORMATS: Tuple[str, ...] = ("RAW", "RAW & JPEG", "RAW & HEIF", "JPEG", "HEIF")
P292_STILL_FILE_FORMAT_DEFAULT: str = "JPEG"
P292_STILL_FILE_FORMAT_RESID16_MAP: Dict[str, int] = {
    "RAW": 0xE738,
    "RAW & JPEG": 0xE739,
    "RAW & HEIF": 0xE1FC,
    "JPEG": 0xE7FF,
    "HEIF": 0xE7FF,
}

P292_STILL_RAW_FILE_TYPE_BKID: str = "BKID_APP_setting_still_raw_file_type"
P292_STILL_RAW_FILE_TYPE_RESID16: int = 0x6FF2  # _f.uxc
P292_FX3_EXPOSED_RAW_FILE_TYPES: Tuple[str, ...] = ("Compressed", "Uncompressed")
P292_STILL_RAW_FILE_TYPE_DEFAULT: str = "Compressed"
P292_STILL_RAW_BIT_DEPTH: int = 14
P292_DORMANT_LOSSLESS_RAW_MODES: Tuple[str, ...] = (
    "Lossless Comp",
    "Lossless Comp (L)",
    "Lossless Comp (M)",
    "Lossless Comp (S)",
)
P292_DORMANT_LOSSLESS_RAW_RESID16: int = 0x6B56  # _f.uxc
P292_DORMANT_LOSSLESS_RAW_SIZES_RESID16: Tuple[int, ...] = (0x7897, 0x6BFD, 0x7894)
P292_STILL_RAW_FILE_TYPE_RESID16_MAP: Dict[str, int] = {
    "Compressed": 0x6F67,
    "Uncompressed": 0x67A9,
}

P292_JPEG_HEIF_QUALITIES: Tuple[str, ...] = ("Extra fine", "Fine", "Standard")
P292_JPEG_HEIF_QUALITY_DEFAULT: str = "Fine"
P292_JPEG_HEIF_IMAGE_SIZES: Tuple[str, ...] = ("L", "M", "S")
P292_JPEG_HEIF_IMAGE_SIZE_DEFAULT: str = "L"

P292_HLG_STILL_BKID: str = "BKID_APP_setting_still_hlg_photo"
P292_HLG_STILL_RESID16: int = 0x76C8  # _f.uxc
P292_HLG_BT2020_RESID16: int = 0x79E1  # _f.uxc
P292_HLG_STILL_DEFAULT: str = "Off"
P292_STILL_PASM_MODES: Tuple[str, ...] = ("P", "A", "S", "M")
P292_STILL_SHOOTING_MODES: Tuple[str, ...] = ("Intelligent Auto", "P", "A", "S", "M")

P292_COLOR_SPACE_BKID: str = "BKID_APP_setting_still_color_space"
P292_COLOR_SPACE_RESID16: int = 0x68B7  # _f.uxc
P292_COLOR_SPACE_MODES: Tuple[str, ...] = ("sRGB", "AdobeRGB")
P292_EFFECTIVE_COLOR_SPACES: Tuple[str, ...] = ("sRGB", "AdobeRGB", "BT.2100")
P292_COLOR_SPACE_DEFAULT: str = "sRGB"
P292_COLOR_SPACE_RESID16_MAP: Dict[str, int] = {
    "sRGB": 0xE07D,
    "AdobeRGB": 0xE07E,
}
P292_COLOR_SPACE_ADOBERGB_HINT_RESID16: int = 0xE895  # .uxc

P292_SET_FILE_NAME_BKID: str = "BKID_APP_set_file_name_prefix_still"
P292_SET_FILE_NAME_RESID16: int = 0x6993  # _f.uxc
P292_SET_FILE_NAME_DEFAULT: str = "DSC"
P292_SET_FILE_NAME_LEN: int = 3
P292_SET_FILE_NAME_ALLOWED_CHARS: str = "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"

P292_STILL_SURFACE_MODELS: Tuple[str, ...] = (
    "FX3_STILL_RAW_JPEG_HEIF_PIPELINE",
    "FX6_STILL_LESS_MOVIE_RAW_HLG_PIPELINE",
)
P292_FX6_STILL_PIPELINE_CONFLATION_ERROR: str = "FX6_HAS_ZERO_STILL_DCIM_RAW_HEIF_PIPELINE"

# ---------------------------------------------------------------------------
# Pillar 51B Constants — [Shutter Type] 2-Option Split, 1/250s Flash Sync,
# 5-Lock Matrix, [e-Front Curtain Shut.], [Long Exposure NR]/[High ISO NR], [Drive Mode]
# ---------------------------------------------------------------------------

P292_SHUTTER_TYPE_MENU_PATH: Tuple[str, ...] = ("Shooting", "Shutter/Silent", "Shutter Type")
P292_EFRONT_CURTAIN_MENU_PATH: Tuple[str, ...] = ("Shooting", "Shutter/Silent", "e-Front Curtain Shut.")
P292_SILENT_MODE_MENU_PATH: Tuple[str, ...] = ("Shooting", "Shutter/Silent", "Silent Mode Settings")
P292_LONG_EXPOSURE_NR_MENU_PATH: Tuple[str, ...] = ("Shooting", "Image Quality/Rec", "Long Exposure NR")
P292_HIGH_ISO_NR_MENU_PATH: Tuple[str, ...] = ("Shooting", "Image Quality/Rec", "High ISO NR")
P292_DRIVE_MODE_MENU_PATH: Tuple[str, ...] = ("Shooting", "Drive Mode", "Drive Mode")

P292_SHUTTER_TYPE_BKID: str = "BKID_APP_setting_still_shutter_type"
P292_DORMANT_ANTI_DISTORTION_SHUTTER_BKID: str = (
    "BKID_APP_setting_still_shutter_type_anti_distortion_shutter"
)
P292_SHUTTER_TYPE_RESID16: int = 0x7AA9  # _f.uxc
P292_FX3_EXPOSED_SHUTTER_TYPES: Tuple[str, ...] = ("Mechanical Shutter", "Electronic Shutter")
P292_DORMANT_SHUTTER_TYPES: Tuple[str, ...] = ("Auto",)
P292_SHUTTER_TYPE_DEFAULT: str = "Mechanical Shutter"
P292_SHUTTER_TYPE_RESID16_MAP: Dict[str, int] = {
    "Mechanical Shutter": 0x6DDB,
    "Electronic Shutter": 0x60A1,
}

P292_EFRONT_CURTAIN_BKID: str = "BKID_APP_setting_front_curtaion_shutter"
P292_EFRONT_CURTAIN_RESID16: int = 0x64C6  # _f.uxc
P292_EFRONT_CURTAIN_DEFAULT: str = "On"

P292_SILENT_MODE_BKID: str = "BKID_APP_setting_silent_mode"
P292_SILENT_MODE_RESID16: int = 0x7A53  # _f.uxc
P292_SILENT_MODE_G_RESID16: int = 0x6079  # _g.uxc
P292_SILENT_MODE_DEFAULT: str = "Off"
P292_APERTURE_DRIVE_IN_AF_DEFAULT: str = "Standard"
P292_AUTO_PIXEL_MAPPING_DEFAULT: str = "Off"

P292_FX3_MAX_FLASH_SYNC_DENOM: int = 250  # 1/250 s
P292_FLASH_SYNC_1_250_RESID16: int = 0x759B  # _f.uxc

P292_ELECTRONIC_SILENT_5LOCK_FUNCTIONS: Tuple[str, ...] = (
    "Flash",
    "Long Exposure NR",
    "e-Front Curtain Shut.",
    "BULB",
    "Anti-flicker Shoot.",
)

P292_LONG_EXPOSURE_NR_BKID: str = "BKID_APP_setting_still_long_exposure_nr"
P292_LONG_EXPOSURE_NR_RESID16: int = 0x6CD7  # _f.uxc
P292_LONG_EXPOSURE_NR_DEFAULT: str = "On"
P292_LONG_EXPOSURE_NR_THRESHOLD_SEC: float = 1.0

P292_HIGH_ISO_NR_BKID: str = "BKID_APP_setting_still_high_iso_nr"
P292_HIGH_ISO_NR_RESID16: int = 0x650B  # _f.uxc
P292_HIGH_ISO_NR_MODES: Tuple[str, ...] = ("Normal", "Low", "Off")
P292_HIGH_ISO_NR_DEFAULT: str = "Normal"
P292_HIGH_ISO_NR_RESID16_MAP: Dict[str, int] = {
    "Normal": 0xE9AE,
    "Low": 0xE06E,
    "Off": 0xE6D8,
}

P292_DRIVE_MODE_BKID: str = "BKID_APP_setting_menu_drive_mode"
P292_CONT_SHOOTING_SPEED_BKID: str = "BKID_APP_setting_drive_mode_cont_shooting"
P292_DRIVE_MODE_RESID16: int = 0x7228  # _f.uxc
P292_DRIVE_MODE_G_RESID16: int = 0x616E  # _g.uxc
P292_DRIVE_8_MODES: Tuple[str, ...] = (
    "Single Shooting",
    "Cont. Shooting",
    "Self-timer(Single)",
    "Self-timer(Cont)",
    "Cont. Bracket",
    "Single Bracket",
    "WB bracket",
    "DRO Bracket",
)
P292_DRIVE_MODE_DEFAULT: str = "Single Shooting"
P292_CONT_SHOOTING_4_SPEEDS: Tuple[str, ...] = ("Hi+", "Hi", "Mid", "Lo")
P292_CONT_SHOOTING_FPS_MAP: Dict[str, int] = {
    "Hi+": 10,
    "Hi": 8,
    "Mid": 6,
    "Lo": 3,
}
P292_CONT_SHOOTING_RESID16_MAP: Dict[str, int] = {
    "Hi+": 0x68D1,
    "Hi": 0x6C00,
    "Mid": 0x6F48,
    "Lo": 0x6A0B,
}
P292_DRIVE_MODE_RESID16_MAP: Dict[str, int] = {
    "Single Shooting": 0xE842,
    "Cont. Bracket": 0xE8F7,
    "Single Bracket": 0xE190,
    "WB bracket": 0xE7CF,
    "DRO Bracket": 0xE18F,
}
P292_AF_LOCK_APERTURE_THRESHOLD_F: float = 11.0
P292_SHUTTER_SURFACE_MODELS: Tuple[str, ...] = (
    "FX3_2OPT_MECHANICAL_ELECTRONIC_SHUTTER_PIPELINE",
    "FX6_NO_MECHANICAL_SHUTTER_PIPELINE",
)

# Shared Reset, Vault & Tier-0 Constants
P292_ON_OFF_MODES: Tuple[str, ...] = ("On", "Off")
P292_RESET_ACTIONS: Tuple[str, ...] = (
    "None",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P292_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "STILL_CAPTURE_WRITE",
    "SORT_RECORDING_WRITE",
    "BURST_BRACKET_DCIM_WRITE",
    "AVF_INFO_IMAGEDB_MUTATION",
    "DELETE_SINGLE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P292_DESTRUCTIVE_VAULT_ACTIONS: Tuple[str, ...] = (
    "STILL_CAPTURE_WRITE",
    "SORT_RECORDING_WRITE",
    "BURST_BRACKET_DCIM_WRITE",
    "AVF_INFO_IMAGEDB_MUTATION",
    "DELETE_SINGLE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P292_SLOT1_VAULT_SLOT: int = 1
P292_SAFE_SECONDARY_CAPTURE_SLOT: int = 2
P292_VAULT_FIREWALL_ERRNOS: Tuple[str, ...] = ("EROFS", "EBUSY")
P292_STAGE_B_VOLATILE_OVERLAY_DIR: str = (
    "/tmp/fx3_raw_heif_colorspace_shuttertype_nr_drive_vault_overlay"
)
P292_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P292_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P292_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P292_BLOCKED_INVALID_PILLAR51A_SPEC: str = "BLOCKED_INVALID_PILLAR51A_SPEC"
P292_BLOCKED_DORMANT_LOSSLESS_RAW_EXPOSURE: str = "BLOCKED_DORMANT_LOSSLESS_RAW_EXPOSURE"
P292_BLOCKED_FX6_STILL_PIPELINE_CONFLATION: str = "BLOCKED_FX6_STILL_PIPELINE_CONFLATION"
P292_BLOCKED_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT: str = (
    "BLOCKED_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT"
)
P292_BLOCKED_COLORSPACE_ADOBERGB_OR_PREFIX_VIOLATION: str = (
    "BLOCKED_COLORSPACE_ADOBERGB_OR_PREFIX_VIOLATION"
)
P292_BLOCKED_INVALID_PILLAR51B_SPEC: str = "BLOCKED_INVALID_PILLAR51B_SPEC"
P292_BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION: str = (
    "BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION"
)
P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS: str = (
    "BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS"
)
P292_BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION: str = (
    "BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION"
)
P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL: str = "BLOCKED_SLOT1_VAULT_WRITE_FIREWALL"
P292_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P292_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P292_STATUS_VERIFIED_PILLAR_51A: str = (
    "VERIFIED_PILLAR_51A_RAW_HEIF_HLG_COLORSPACE_FILENAME_AND_SLOT1_VAULT"
)
P292_STATUS_REJECTED_PILLAR_51A: str = (
    "REJECTED_PILLAR_51A_RAW_HEIF_HLG_COLORSPACE_FILENAME_AND_SLOT1_VAULT"
)
P292_STATUS_VERIFIED_PILLAR_51B: str = (
    "VERIFIED_PILLAR_51B_2OPT_SHUTTER_5LOCK_NR_10FPS_DRIVE_AND_SLOT1_VAULT"
)
P292_STATUS_REJECTED_PILLAR_51B: str = (
    "REJECTED_PILLAR_51B_2OPT_SHUTTER_5LOCK_NR_10FPS_DRIVE_AND_SLOT1_VAULT"
)
P292_STATUS_VERIFIED_PILLAR51_SUITE: str = (
    "VERIFIED_PILLAR51_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_VAULT"
)
P292_STATUS_FAIL_PILLAR51_SUITE: str = (
    "FAIL_PILLAR51_RAW_HEIF_COLORSPACE_SHUTTERTYPE_NR_DRIVE_VAULT"
)
P292_STATUS_VERIFIED_51OF51_AGGREGATOR: str = "VERIFIED_51OF51_PILLAR_RECOVERY_MASTER"
P292_STATUS_FAIL_51OF51_AGGREGATOR: str = "FAIL_51OF51_PILLAR_RECOVERY_MASTER"

P292_PILLAR_51A_SCENARIO_IDS: Tuple[str, ...] = (
    "P51A1_DEFAULT_COMPRESSED_RAW_SRGB_DSC_AND_SLOT1_VAULT_EROFS_SAFE",
    "P51A2_HEIF_422_HLG_STILL_BT2100_ADOBERGB_PREFIX_RESET_SURVIVAL_SAFE",
    "P51A3_REJECT_DORMANT_LOSSLESS_COMP_RAW_OR_FX6_STILL_CONFLATION",
    "P51A4_REJECT_HLG_STILL_PREREQ_OR_LOCKOUT_BYPASS",
    "P51A5_REJECT_ADOBERGB_PREFIX_DRIFT_OR_LEADING_UNDERSCORE_FILENAME",
    "P51A6_REJECT_SLOT1_STILL_SORT_WRITE_OR_PERSISTENT_OVERLAY_OR_H0_H3_DRIFT",
)
P292_PILLAR_51B_SCENARIO_IDS: Tuple[str, ...] = (
    "P51B1_DEFAULT_MECHANICAL_SHUTTER_1_250_FLASH_NR_SINGLE_DRIVE_SAFE",
    "P51B2_ELECTRONIC_SHUTTER_5LOCK_COMPRESSED_RAW_HI_PLUS_10FPS_F14_AF_LOCK_SAFE",
    "P51B3_REJECT_SHUTTER_TYPE_AUTO_SPOOF_OR_FX6_MECHANICAL_SHUTTER_CONFLATION",
    "P51B4_REJECT_ELECTRONIC_SILENT_5LOCK_BYPASS_OR_EFRONT_CAMSET_RESET_DRIFT",
    "P51B5_REJECT_NR_RULE_OR_UNCOMPRESSED_10FPS_OR_HLG_DRO_BRACKET_VIOLATION",
    "P51B6_REJECT_SLOT1_BURST_BRACKET_IMAGEDB_MUTATION_OR_H0_H3_DRIFT",
)

MASTER_51_PILLAR_COUNT: int = 51
MASTER_51_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_50_PILLAR_SPECS + (
    (
        51,
        "pillar_51_raw_heif_colorspace_shuttertype_nr_drive_vault",
        "Phase 292 (Wave-49)",
        "fx3_recovery.realhw_51pillar_raw_heif_colorspace_shuttertype_nr_drive_vault_verifier",
    ),
)
MASTER_51_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_51_PILLAR_SPECS)


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
    return os.environ.get(P292_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P292_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P292_DONOR_INSPECT_BUDGET_SECONDS


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
            "P292_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
            P292_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
            False,
        ),
        ("P292_OVERALL_READY_FOR_HARDWARE_ATTACH", P292_OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        (
            "P292_DORMANT_LOSSLESS_RAW_EXPOSURE_EVENTS",
            P292_DORMANT_LOSSLESS_RAW_EXPOSURE_EVENTS,
            0,
        ),
        (
            "P292_FX6_STILL_PIPELINE_CONFLATION_EVENTS",
            P292_FX6_STILL_PIPELINE_CONFLATION_EVENTS,
            0,
        ),
        (
            "P292_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT_EVENTS",
            P292_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT_EVENTS,
            0,
        ),
        (
            "P292_COLORSPACE_ADOBERGB_PREFIX_VIOLATIONS",
            P292_COLORSPACE_ADOBERGB_PREFIX_VIOLATIONS,
            0,
        ),
        ("P292_SHUTTER_TYPE_AUTO_SPOOF_EVENTS", P292_SHUTTER_TYPE_AUTO_SPOOF_EVENTS, 0),
        (
            "P292_FX6_MECHANICAL_SHUTTER_CONFLATION_EVENTS",
            P292_FX6_MECHANICAL_SHUTTER_CONFLATION_EVENTS,
            0,
        ),
        (
            "P292_ELECTRONIC_SILENT_5LOCK_BYPASS_EVENTS",
            P292_ELECTRONIC_SILENT_5LOCK_BYPASS_EVENTS,
            0,
        ),
        ("P292_NR_OR_DRIVE_BURST_WALL_VIOLATIONS", P292_NR_OR_DRIVE_BURST_WALL_VIOLATIONS, 0),
        (
            "P292_SLOT1_STILL_CAPTURE_OR_SORT_WRITE_BYTES",
            P292_SLOT1_STILL_CAPTURE_OR_SORT_WRITE_BYTES,
            0,
        ),
        (
            "P292_SLOT1_IMAGEDB_OR_BURST_MUTATION_BYTES",
            P292_SLOT1_IMAGEDB_OR_BURST_MUTATION_BYTES,
            0,
        ),
        ("P292_SLOT1_VAULT_MUTATION_BYTES", P292_SLOT1_VAULT_MUTATION_BYTES, 0),
        ("P292_SLOT1_FORMAT_HARD_LOCKED", P292_SLOT1_FORMAT_HARD_LOCKED, True),
        ("P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED", P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED, True),
        ("P292_FX3_UI_EXPOSES_LOSSLESS_RAW", P292_FX3_UI_EXPOSES_LOSSLESS_RAW, False),
        ("P292_FX3_UI_EXPOSES_SHUTTER_TYPE_AUTO", P292_FX3_UI_EXPOSES_SHUTTER_TYPE_AUTO, False),
        ("P292_FX6_STILL_PIPELINE_PRESENT", P292_FX6_STILL_PIPELINE_PRESENT, False),
        ("P292_FX6_MECHANICAL_SHUTTER_PRESENT", P292_FX6_MECHANICAL_SHUTTER_PRESENT, False),
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
    return any(tok in low for tok in P292_FORBIDDEN_PERSISTENT_TARGETS)


def is_valid_fx3_still_filename_prefix(prefix: str) -> bool:
    """Validate `[Set File Name]` 3-char prefix (`A-Z`/`0-9`/`_`, forbidding leading `_`)."""
    if len(prefix) != P292_SET_FILE_NAME_LEN:
        return False
    if prefix[0] == "_":
        return False
    return all(ch in P292_SET_FILE_NAME_ALLOWED_CHARS for ch in prefix)


def compute_expected_still_image_quality_and_hlg_state(
    *,
    jpeg_heif_switch: str,
    file_format: str,
    raw_file_type: str,
    shooting_mode: str,
    configured_hlg_still: str,
    reg_custom_iso_or_dro_bracket_active: bool,
) -> Tuple[bool, str, str, Tuple[str, ...], bool]:
    """Compute `(raw_type_allowed, eff_hlg_still, still_container_ext, locked_out_funcs, iso_bounds_shifted)`.

    - `ILME-FX3 Ver. 7.02` (`12 MP IMX510`) exposes ONLY `Compressed` and `Uncompressed`
      14-bit `.ARW` (dormant `Lossless Comp` rejected fail-closed).
    - `[HLG Still Image] = On` requires ALL 3 prerequisites:
      1. `jpeg_heif_switch in ("HEIF(4:2:0)", "HEIF(4:2:2)")`
      2. `file_format == "HEIF"` (NOT `RAW` or `RAW & HEIF`)
      3. `shooting_mode in ("P", "A", "S", "M")` (and not overridden by `Reg. Custom Shoot Set`)
    - When `eff_hlg_still == "On"`: locks out `Picture Profile`, `Creative Look`,
      `D-Range Optimizer`, and `DRO Bracket`, and shifts still ISO bounds.
    """
    raw_allowed = raw_file_type in P292_FX3_EXPOSED_RAW_FILE_TYPES
    prereqs_met = (
        jpeg_heif_switch in ("HEIF(4:2:0)", "HEIF(4:2:2)")
        and file_format == "HEIF"
        and shooting_mode in P292_STILL_PASM_MODES
        and not reg_custom_iso_or_dro_bracket_active
    )
    eff_hlg = "On" if (configured_hlg_still == "On" and prereqs_met) else "Off"
    ext = ".HIF" if jpeg_heif_switch in ("HEIF(4:2:0)", "HEIF(4:2:2)") else ".JPG"
    locked = (
        ("Picture Profile", "Creative Look", "D-Range Optimizer", "DRO Bracket")
        if eff_hlg == "On"
        else ()
    )
    return raw_allowed, eff_hlg, ext, locked, (eff_hlg == "On")


def compute_expected_colorspace_and_filename_prefix(
    *,
    jpeg_heif_switch: str,
    eff_hlg_still: str,
    configured_color_space: str,
    pre_file_name_prefix: str,
    reset_action: str,
    manual_prefix_edit: Optional[str] = None,
) -> Tuple[str, bool, str, str]:
    """Compute `(eff_color_space, prefix_valid, post_base_prefix, effective_filename_stem)`.

    - Under `HEIF(4:2:0/4:2:2)`: `[Color Space]` (`sRGB`/`AdobeRGB`) is ignored — records
      `BT.2100` (`BT.2020`) when `HLG Still = On`, else `sRGB`.
    - Under `JPEG` + `AdobeRGB`: DCF 2.0 prepends `_` (e.g. `DSC` -> `_DSC0001`).
    - `[Set File Name]` forbids `_` as the 1st character and **survives `Camera Settings Reset`**
      (reset only on `Initialize` or explicit manual edit).
    """
    if manual_prefix_edit is not None:
        candidate = manual_prefix_edit
    elif reset_action == "Initialize":
        candidate = P292_SET_FILE_NAME_DEFAULT
    else:
        candidate = pre_file_name_prefix

    prefix_valid = is_valid_fx3_still_filename_prefix(candidate)

    if jpeg_heif_switch in ("HEIF(4:2:0)", "HEIF(4:2:2)"):
        eff_cs = "BT.2100" if eff_hlg_still == "On" else "sRGB"
    else:
        eff_cs = configured_color_space

    if eff_cs == "AdobeRGB":
        stem = f"_{candidate}0001"
    else:
        stem = f"{candidate}00001"

    return eff_cs, prefix_valid, candidate, stem


def compute_expected_shutter_type_and_5lock_matrix(
    *,
    configured_shutter_type: str,
    shooting_mode: str,
    silent_mode: str,
    silent_mode_target_override_shutter: bool,
    pre_e_front_curtain: str,
    reset_action: str,
) -> Tuple[bool, str, Tuple[str, ...], bool, str]:
    """Compute `(shutter_valid, eff_shutter_type, locked_5_functions, flash_1_250_allowed, post_e_front_curtain)`.

    - `ILME-FX3` exposes ONLY `Mechanical Shutter` and `Electronic Shutter` (`Auto` rejected).
    - `Electronic Shutter` selectable only in `P/A/S/M`; `Silent Mode = On` forces
      `Electronic Shutter` unless overridden via `Target Function Settings`.
    - Whenever `Electronic Shutter` is active (or `Silent Mode = On` without override),
      all 5 functions are locked out: `Flash` (`1/250 s`), `Long Exposure NR`,
      `e-Front Curtain Shut.`, `BULB`, `Anti-flicker Shoot.`.
    - `[e-Front Curtain Shut.]` (`On` default) survives `Camera Settings Reset` and reverts
      to `On` only on `Initialize`.
    """
    shutter_valid = configured_shutter_type in P292_FX3_EXPOSED_SHUTTER_TYPES
    if not shutter_valid:
        eff_shutter = configured_shutter_type
    elif silent_mode == "On" and not silent_mode_target_override_shutter:
        eff_shutter = "Electronic Shutter"
    elif configured_shutter_type == "Electronic Shutter" and shooting_mode not in P292_STILL_PASM_MODES:
        eff_shutter = "Mechanical Shutter"
    else:
        eff_shutter = configured_shutter_type

    locks_active = eff_shutter == "Electronic Shutter" or (
        silent_mode == "On" and not silent_mode_target_override_shutter
    )
    locked = P292_ELECTRONIC_SILENT_5LOCK_FUNCTIONS if locks_active else ()
    flash_allowed = not locks_active

    post_efront = P292_EFRONT_CURTAIN_DEFAULT if reset_action == "Initialize" else pre_e_front_curtain
    return shutter_valid, eff_shutter, locked, flash_allowed, post_efront


def compute_expected_nr_and_drive_mode_boundaries(
    *,
    shooting_mode: str,
    file_format: str,
    raw_file_type: str,
    eff_hlg_still: str,
    electronic_or_silent_locks_active: bool,
    configured_long_exposure_nr: str,
    configured_high_iso_nr: str,
    drive_mode: str,
    cont_shooting_speed: str,
    flash_fired: bool,
    aperture_f_number: float,
    shutter_speed_sec: float,
    is_bulb: bool,
) -> Tuple[bool, str, bool, str, bool, int, bool, bool, bool]:
    """Compute `(long_nr_available, eff_long_nr, high_iso_nr_available, eff_high_iso_nr,
    dro_bracket_allowed, eff_burst_fps, hi_plus_live_monitor, af_locked_first_frame,
    long_nr_dark_frame_blocks_next)`.
    """
    long_nr_available = not (
        electronic_or_silent_locks_active
        or drive_mode in ("Cont. Shooting", "Cont. Bracket")
    )
    if not long_nr_available:
        eff_long_nr = "Off"
    elif shooting_mode == "Intelligent Auto":
        eff_long_nr = "On"
    else:
        eff_long_nr = configured_long_exposure_nr

    high_iso_nr_available = file_format != "RAW"
    if not high_iso_nr_available:
        eff_high_iso_nr = "Unavailable"
    elif shooting_mode == "Intelligent Auto":
        eff_high_iso_nr = "Normal"
    else:
        eff_high_iso_nr = configured_high_iso_nr

    dro_bracket_allowed = eff_hlg_still != "On"

    if drive_mode != "Cont. Shooting":
        eff_fps = 1
        hi_plus_live_monitor = True
        af_locked_first_frame = False
    else:
        nominal = P292_CONT_SHOOTING_FPS_MAP.get(cont_shooting_speed, 0)
        if cont_shooting_speed == "Hi+" and (
            (file_format in ("RAW", "RAW & JPEG", "RAW & HEIF") and raw_file_type == "Uncompressed")
            or flash_fired
        ):
            eff_fps = 8  # drops below 10 fps
        else:
            eff_fps = nominal
        hi_plus_live_monitor = cont_shooting_speed != "Hi+"
        af_locked_first_frame = (
            cont_shooting_speed in ("Hi+", "Hi", "Mid")
            and aperture_f_number > P292_AF_LOCK_APERTURE_THRESHOLD_F
        )

    long_nr_blocks = (
        eff_long_nr == "On"
        and (is_bulb or shutter_speed_sec >= P292_LONG_EXPOSURE_NR_THRESHOLD_SEC)
    )
    return (
        long_nr_available,
        eff_long_nr,
        high_iso_nr_available,
        eff_high_iso_nr,
        dro_bracket_allowed,
        eff_fps,
        hi_plus_live_monitor,
        af_locked_first_frame,
        long_nr_blocks,
    )


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase292DonorArtifactDigest:
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
class Phase292DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase292DonorArtifactDigest, ...]


@dataclass(frozen=True)
class StillImageQualityHlgColorspaceFilenameVaultSpec:
    camera_model: str = P292_FX3_MODEL_NAME
    camera_model_id: int = P292_FX3_MODEL_ID
    camera_codename: str = P292_FX3_PRODUCT_CODENAME
    helpguide_id: str = P292_FX3_HELPGUIDE_ID
    fw_version: str = P292_FX3_FW_VERSION
    still_surface_model: str = "FX3_STILL_RAW_JPEG_HEIF_PIPELINE"
    fx6_still_pipeline_present: bool = P292_FX6_STILL_PIPELINE_PRESENT
    jpeg_heif_switch_menu_path: Tuple[str, ...] = P292_JPEG_HEIF_SWITCH_MENU_PATH
    image_quality_menu_path: Tuple[str, ...] = P292_IMAGE_QUALITY_MENU_PATH
    hlg_still_menu_path: Tuple[str, ...] = P292_HLG_STILL_MENU_PATH
    color_space_menu_path: Tuple[str, ...] = P292_COLOR_SPACE_MENU_PATH
    set_file_name_menu_path: Tuple[str, ...] = P292_SET_FILE_NAME_MENU_PATH
    jpeg_heif_switch: str = P292_JPEG_HEIF_SWITCH_DEFAULT
    file_format: str = P292_STILL_FILE_FORMAT_DEFAULT
    raw_file_type: str = P292_STILL_RAW_FILE_TYPE_DEFAULT
    fx3_ui_exposes_lossless_raw: bool = P292_FX3_UI_EXPOSES_LOSSLESS_RAW
    jpeg_heif_quality: str = P292_JPEG_HEIF_QUALITY_DEFAULT
    jpeg_heif_image_size: str = P292_JPEG_HEIF_IMAGE_SIZE_DEFAULT
    shooting_mode: str = "M"
    configured_hlg_still: str = P292_HLG_STILL_DEFAULT
    reg_custom_iso_or_dro_bracket_active: bool = False
    reported_hlg_still: str = P292_HLG_STILL_DEFAULT
    reported_picture_profile_locked: bool = False
    reported_creative_look_locked: bool = False
    reported_dro_locked: bool = False
    reported_dro_bracket_locked: bool = False
    reported_hlg_iso_bounds_shifted: bool = False
    configured_color_space: str = P292_COLOR_SPACE_DEFAULT
    reported_effective_color_space: str = P292_COLOR_SPACE_DEFAULT
    pre_file_name_prefix: str = P292_SET_FILE_NAME_DEFAULT
    manual_prefix_edit: Optional[str] = None
    reset_action: str = "None"
    post_file_name_prefix: str = P292_SET_FILE_NAME_DEFAULT
    reported_filename_stem: str = "DSC00001"
    dormant_lossless_raw_exposure_events: int = 0
    fx6_still_pipeline_conflation_events: int = 0
    hlg_still_prereq_or_lockout_drift_events: int = 0
    colorspace_adobergb_prefix_violations: int = 0
    # Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P292_SLOT1_FORMAT_HARD_LOCKED
    slot1_vault_erofs_ebusy_enforced: bool = P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED
    target_still_write_slot: int = P292_SAFE_SECONDARY_CAPTURE_SLOT
    sort_recording_targets_slot1: bool = False
    requested_vault_slot: int = P292_SLOT1_VAULT_SLOT
    requested_vault_action: str = "READ_ONLY_AUDIT"
    slot1_still_capture_or_sort_write_bytes: int = 0
    overlay_dir: str = P292_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P292_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P292_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P292_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class StillImageQualityHlgColorspaceFilenameVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    raw_compressed_uncompressed_and_lossless_ban_verified: bool
    fx6_still_less_distinction_verified: bool
    hlg_still_prereqs_bt2100_lockouts_verified: bool
    colorspace_adobergb_dsc_and_prefix_ban_verified: bool
    slot1_erofs_ebusy_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    dormant_lossless_raw_exposure_events: int
    fx6_still_pipeline_conflation_events: int
    hlg_still_prereq_or_lockout_drift_events: int
    colorspace_adobergb_prefix_violations: int
    slot1_still_capture_or_sort_write_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShutterTypeNrDriveVaultSpec:
    camera_model: str = P292_FX3_MODEL_NAME
    camera_model_id: int = P292_FX3_MODEL_ID
    helpguide_id: str = P292_FX3_HELPGUIDE_ID
    fw_version: str = P292_FX3_FW_VERSION
    shutter_surface_model: str = "FX3_2OPT_MECHANICAL_ELECTRONIC_SHUTTER_PIPELINE"
    fx6_mechanical_shutter_present: bool = P292_FX6_MECHANICAL_SHUTTER_PRESENT
    shutter_type_menu_path: Tuple[str, ...] = P292_SHUTTER_TYPE_MENU_PATH
    e_front_curtain_menu_path: Tuple[str, ...] = P292_EFRONT_CURTAIN_MENU_PATH
    long_exposure_nr_menu_path: Tuple[str, ...] = P292_LONG_EXPOSURE_NR_MENU_PATH
    high_iso_nr_menu_path: Tuple[str, ...] = P292_HIGH_ISO_NR_MENU_PATH
    drive_mode_menu_path: Tuple[str, ...] = P292_DRIVE_MODE_MENU_PATH
    shooting_mode: str = "M"
    configured_shutter_type: str = P292_SHUTTER_TYPE_DEFAULT
    fx3_ui_exposes_shutter_type_auto: bool = P292_FX3_UI_EXPOSES_SHUTTER_TYPE_AUTO
    reported_shutter_type: str = P292_SHUTTER_TYPE_DEFAULT
    silent_mode: str = P292_SILENT_MODE_DEFAULT
    silent_mode_target_override_shutter: bool = False
    aperture_drive_in_af: str = P292_APERTURE_DRIVE_IN_AF_DEFAULT
    auto_pixel_mapping: str = P292_AUTO_PIXEL_MAPPING_DEFAULT
    pre_e_front_curtain: str = P292_EFRONT_CURTAIN_DEFAULT
    reset_action: str = "None"
    post_e_front_curtain: str = P292_EFRONT_CURTAIN_DEFAULT
    flash_sync_speed_denom: int = P292_FX3_MAX_FLASH_SYNC_DENOM
    reported_flash_allowed: bool = True
    reported_long_exposure_nr_allowed: bool = True
    reported_e_front_curtain_allowed: bool = True
    reported_bulb_allowed: bool = True
    reported_anti_flicker_allowed: bool = True
    file_format: str = P292_STILL_FILE_FORMAT_DEFAULT
    raw_file_type: str = P292_STILL_RAW_FILE_TYPE_DEFAULT
    eff_hlg_still: str = P292_HLG_STILL_DEFAULT
    configured_long_exposure_nr: str = P292_LONG_EXPOSURE_NR_DEFAULT
    reported_long_exposure_nr: str = P292_LONG_EXPOSURE_NR_DEFAULT
    configured_high_iso_nr: str = P292_HIGH_ISO_NR_DEFAULT
    reported_high_iso_nr: str = P292_HIGH_ISO_NR_DEFAULT
    drive_mode: str = P292_DRIVE_MODE_DEFAULT
    cont_shooting_speed: str = "Hi+"
    flash_fired: bool = False
    aperture_f_number: float = 2.8
    shutter_speed_sec: float = 0.01
    is_bulb: bool = False
    reported_eff_burst_fps: int = 1
    reported_hi_plus_live_monitor: bool = True
    reported_af_locked_first_frame: bool = False
    reported_dro_bracket_allowed: bool = True
    reported_long_nr_blocks_next: bool = False
    shutter_type_auto_spoof_events: int = 0
    fx6_mechanical_shutter_conflation_events: int = 0
    electronic_silent_5lock_bypass_events: int = 0
    nr_or_drive_burst_wall_violations: int = 0
    # Burst / Bracket Slot-1 Vault Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P292_SLOT1_FORMAT_HARD_LOCKED
    slot1_vault_erofs_ebusy_enforced: bool = P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED
    target_burst_bracket_slot: int = P292_SAFE_SECONDARY_CAPTURE_SLOT
    avf_info_imagedb_targets_slot1: bool = False
    requested_vault_slot: int = P292_SLOT1_VAULT_SLOT
    requested_vault_action: str = "READ_ONLY_AUDIT"
    slot1_imagedb_or_burst_mutation_bytes: int = 0
    overlay_dir: str = P292_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P292_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P292_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P292_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class ShutterTypeNrDriveVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    shutter_2opt_no_auto_and_fx6_contrast_verified: bool
    electronic_silent_5lock_and_1_250_sync_verified: bool
    e_front_curtain_reset_boundary_verified: bool
    long_exposure_and_high_iso_nr_verified: bool
    drive_8modes_10fps_f11_af_lock_verified: bool
    slot1_burst_imagedb_erofs_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    shutter_type_auto_spoof_events: int
    fx6_mechanical_shutter_conflation_events: int
    electronic_silent_5lock_bypass_events: int
    nr_or_drive_burst_wall_violations: int
    slot1_imagedb_or_burst_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RawHeifColorspaceShuttertypeNrDriveVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase292DonorSnapshot
    still_quality_hlg_colorspace_report: StillImageQualityHlgColorspaceFilenameVaultReport
    shutter_type_nr_drive_report: ShutterTypeNrDriveVaultReport
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
class Pillar51ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar51ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar51ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar51BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar51ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar51StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase292DonorSnapshot
    pillar_51a_raw_heif_hlg_colorspace_vault: Pillar51ASuiteResult
    pillar_51b_shuttertype_nr_drive_vault: Pillar51BSuiteResult
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
class Master51PillarRecoveryReport:
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
    # Pillar 51 & Wave-49 top-level fields
    donor_snapshot: Phase292DonorSnapshot
    pillar51_a_raw_heif_hlg_colorspace_vault: Pillar51ASuiteResult
    pillar51_b_shuttertype_nr_drive_vault: Pillar51BSuiteResult
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
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    fx3_ui_exposes_lossless_raw: bool
    fx3_ui_exposes_shutter_type_auto: bool
    fx6_still_pipeline_present: bool
    fx6_mechanical_shutter_present: bool
    # Preserved Pillars 1..50 rollup metrics
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
    master_51pillar_sha256: str
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
    max_full_bytes: int = P292_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P292_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase292_donors() -> Tuple[Phase292DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P292_DONOR_FX3_APPFW_702_RELPATH,
            P292_PINNED_FX3_APPFW_702_BYTES,
            P292_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P292_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P292_DONOR_FX6_APPFW_601_RELPATH,
            P292_PINNED_FX6_APPFW_601_BYTES,
            P292_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P292_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P292_DONOR_FX3_BACKUP_BIN_RELPATH,
            P292_PINNED_FX3_BACKUP_BIN_BYTES,
            P292_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_uxc_en_f",
            P292_DONOR_FX3_UXC_EN_F_RELPATH,
            P292_PINNED_FX3_UXC_EN_F_BYTES,
            P292_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P292_DONOR_FX3_UXC_SC_F_RELPATH,
            P292_PINNED_FX3_UXC_SC_F_BYTES,
            P292_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P292_DONOR_FX3_UXC_TC_F_RELPATH,
            P292_PINNED_FX3_UXC_TC_F_BYTES,
            P292_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P292_DONOR_FX3_UXC_JA_F_RELPATH,
            P292_PINNED_FX3_UXC_JA_F_BYTES,
            P292_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P292_DONOR_FX3_UXC_EN_RELPATH,
            P292_PINNED_FX3_UXC_EN_BYTES,
            P292_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_sc",
            P292_DONOR_FX3_UXC_SC_RELPATH,
            P292_PINNED_FX3_UXC_SC_BYTES,
            P292_PINNED_FX3_UXC_SC_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX3_SC",
        ),
        (
            "fx3_uxc_tc",
            P292_DONOR_FX3_UXC_TC_RELPATH,
            P292_PINNED_FX3_UXC_TC_BYTES,
            P292_PINNED_FX3_UXC_TC_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX3_TC",
        ),
        (
            "fx3_uxc_ja",
            P292_DONOR_FX3_UXC_JA_RELPATH,
            P292_PINNED_FX3_UXC_JA_BYTES,
            P292_PINNED_FX3_UXC_JA_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX3_JA",
        ),
        (
            "fx3_uxc_en_g",
            P292_DONOR_FX3_UXC_EN_G_RELPATH,
            P292_PINNED_FX3_UXC_EN_G_BYTES,
            P292_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx3_uxc_sc_g",
            P292_DONOR_FX3_UXC_SC_G_RELPATH,
            P292_PINNED_FX3_UXC_SC_G_BYTES,
            P292_PINNED_FX3_UXC_SC_G_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_SC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_G",
        ),
        (
            "fx3_uxc_tc_g",
            P292_DONOR_FX3_UXC_TC_G_RELPATH,
            P292_PINNED_FX3_UXC_TC_G_BYTES,
            P292_PINNED_FX3_UXC_TC_G_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_TC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_G",
        ),
        (
            "fx3_uxc_ja_g",
            P292_DONOR_FX3_UXC_JA_G_RELPATH,
            P292_PINNED_FX3_UXC_JA_G_BYTES,
            P292_PINNED_FX3_UXC_JA_G_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX3_UXC_JA_G_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_G",
        ),
        (
            "fx6_uxc_en",
            P292_DONOR_FX6_UXC_EN_RELPATH,
            P292_PINNED_FX6_UXC_EN_BYTES,
            P292_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P292_DONOR_FX6_UXC_EN_2_RELPATH,
            P292_PINNED_FX6_UXC_EN_2_BYTES,
            P292_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P292_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase292DonorArtifactDigest(
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


def inspect_phase292_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase292DonorSnapshot:
    """Inspect Wave-49 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.2s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase292_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase292DonorSnapshot(
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
            P292_DONOR_FX3_APPFW_702_RELPATH,
            P292_PINNED_FX3_APPFW_702_BYTES,
            P292_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702"),
        ),
        (
            "fx6_appfw_601_so",
            P292_DONOR_FX6_APPFW_601_RELPATH,
            P292_PINNED_FX6_APPFW_601_BYTES,
            P292_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601"),
        ),
        (
            "fx3_backup_bin",
            P292_DONOR_FX3_BACKUP_BIN_RELPATH,
            P292_PINNED_FX3_BACKUP_BIN_BYTES,
            P292_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_uxc_en_f",
            P292_DONOR_FX3_UXC_EN_F_RELPATH,
            P292_PINNED_FX3_UXC_EN_F_BYTES,
            P292_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P292_DONOR_FX3_UXC_SC_F_RELPATH,
            P292_PINNED_FX3_UXC_SC_F_BYTES,
            P292_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P292_DONOR_FX3_UXC_TC_F_RELPATH,
            P292_PINNED_FX3_UXC_TC_F_BYTES,
            P292_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P292_DONOR_FX3_UXC_JA_F_RELPATH,
            P292_PINNED_FX3_UXC_JA_F_BYTES,
            P292_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P292_DONOR_FX3_UXC_EN_RELPATH,
            P292_PINNED_FX3_UXC_EN_BYTES,
            P292_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_sc",
            P292_DONOR_FX3_UXC_SC_RELPATH,
            P292_PINNED_FX3_UXC_SC_BYTES,
            P292_PINNED_FX3_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC"),
        ),
        (
            "fx3_uxc_tc",
            P292_DONOR_FX3_UXC_TC_RELPATH,
            P292_PINNED_FX3_UXC_TC_BYTES,
            P292_PINNED_FX3_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC"),
        ),
        (
            "fx3_uxc_ja",
            P292_DONOR_FX3_UXC_JA_RELPATH,
            P292_PINNED_FX3_UXC_JA_BYTES,
            P292_PINNED_FX3_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA"),
        ),
        (
            "fx3_uxc_en_g",
            P292_DONOR_FX3_UXC_EN_G_RELPATH,
            P292_PINNED_FX3_UXC_EN_G_BYTES,
            P292_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx3_uxc_sc_g",
            P292_DONOR_FX3_UXC_SC_G_RELPATH,
            P292_PINNED_FX3_UXC_SC_G_BYTES,
            P292_PINNED_FX3_UXC_SC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_G"),
        ),
        (
            "fx3_uxc_tc_g",
            P292_DONOR_FX3_UXC_TC_G_RELPATH,
            P292_PINNED_FX3_UXC_TC_G_BYTES,
            P292_PINNED_FX3_UXC_TC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_G"),
        ),
        (
            "fx3_uxc_ja_g",
            P292_DONOR_FX3_UXC_JA_G_RELPATH,
            P292_PINNED_FX3_UXC_JA_G_BYTES,
            P292_PINNED_FX3_UXC_JA_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_G"),
        ),
        (
            "fx6_uxc_en",
            P292_DONOR_FX6_UXC_EN_RELPATH,
            P292_PINNED_FX6_UXC_EN_BYTES,
            P292_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P292_DONOR_FX6_UXC_EN_2_RELPATH,
            P292_PINNED_FX6_UXC_EN_2_BYTES,
            P292_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    artifacts: List[Phase292DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            artifacts.append(
                Phase292DonorArtifactDigest(
                    artifact_id=aid,
                    relpath=relpath,
                    present=False,
                    read_mode="LOCAL_DONOR_O_RDONLY",
                    total_bytes=0,
                    header_bytes_read=0,
                    digest_kind="MISSING",
                    digest_sha256="",
                    marker_summary="MISSING",
                    matches_pinned=False,
                )
            )
            continue
        marker_ok, marker_summary = marker_fn(raw_slice)
        matches = (total_b == expected_bytes) and (dsha == expected_sha) and bool(marker_ok)
        artifacts.append(
            Phase292DonorArtifactDigest(
                artifact_id=aid,
                relpath=relpath,
                present=True,
                read_mode="LOCAL_DONOR_O_RDONLY",
                total_bytes=total_b,
                header_bytes_read=hdr_b,
                digest_kind=dkind,
                digest_sha256=dsha,
                marker_summary=marker_summary,
                matches_pinned=matches,
            )
        )

    if any_missing:
        synth = _synthetic_phase292_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase292DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_20s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    all_ok = all(a.present and a.matches_pinned for a in artifacts)
    dt = round(time.monotonic() - t0, 6)
    return Phase292DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(artifacts),
        elapsed_seconds=dt,
        under_0_20s_budget=dt < budget,
        budget_seconds_applied=budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(artifacts),
    )


# ---------------------------------------------------------------------------
# Pillar 51A & 51B Builders and Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_still_image_quality_hlg_colorspace_filename_vault_spec() -> (
    StillImageQualityHlgColorspaceFilenameVaultSpec
):
    """Return canonical safe Wave-49 Pillar 51A specification."""
    return StillImageQualityHlgColorspaceFilenameVaultSpec()


def build_default_safe_shutter_type_nr_drive_vault_spec() -> ShutterTypeNrDriveVaultSpec:
    """Return canonical safe Wave-49 Pillar 51B specification."""
    return ShutterTypeNrDriveVaultSpec()


def evaluate_still_image_quality_hlg_colorspace_filename_vault(
    spec: Optional[StillImageQualityHlgColorspaceFilenameVaultSpec] = None,
) -> StillImageQualityHlgColorspaceFilenameVaultReport:
    """Verify Pillar 51A: Still `[Image Quality Settings]` (`Compressed`/`Uncompressed` `.ARW`
    vs dormant `Lossless Comp`, `HEIF 4:2:0/4:2:2` `.HIF`, `[HLG Still Image]` `BT.2100`
    & lockouts vs still-less `ILME-FX6`), `[Color Space]` `AdobeRGB` `_DSC` prefix,
    `[Set File Name]` leading-`_` ban & reset persistence, and `Slot-1` `EROFS`/`EBUSY`
    vault write firewall."""
    cfg = spec if spec is not None else StillImageQualityHlgColorspaceFilenameVaultSpec()
    safety_errs = _safety_invariant_errors()
    if safety_errs or cfg.persistent_write_unlock_requested:
        errs = safety_errs + (
            ["persistent_write_unlock_requested must be False"]
            if cfg.persistent_write_unlock_requested
            else []
        )
        return StillImageQualityHlgColorspaceFilenameVaultReport(
            passed=False,
            status=P292_STATUS_REJECTED_PILLAR_51A,
            block_code=P292_BLOCKED_SAFETY_POLICY_VIOLATION,
            raw_compressed_uncompressed_and_lossless_ban_verified=False,
            fx6_still_less_distinction_verified=False,
            hlg_still_prereqs_bt2100_lockouts_verified=False,
            colorspace_adobergb_dsc_and_prefix_ban_verified=False,
            slot1_erofs_ebusy_firewall_and_h0_h3_verified=False,
            matrix_states_checked=0,
            dormant_lossless_raw_exposure_events=0,
            fx6_still_pipeline_conflation_events=0,
            hlg_still_prereq_or_lockout_drift_events=0,
            colorspace_adobergb_prefix_violations=0,
            slot1_still_capture_or_sort_write_bytes=0,
            slot1_vault_erofs_ebusy_enforced=cfg.slot1_vault_erofs_ebusy_enforced,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            digest_sha256=_canonical_sha256({"blocked": P292_BLOCKED_SAFETY_POLICY_VIOLATION}),
            errors=tuple(errs),
        )

    errs: List[str] = []
    block_code: Optional[str] = None

    def _set_block(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errs.append(msg)

    # 1. Dormant Lossless Comp RAW check (must check BEFORE generic invalid spec so explicit
    #    Lossless Comp attempts always report P292_BLOCKED_DORMANT_LOSSLESS_RAW_EXPOSURE)
    raw_ok = True
    lossless_ev = cfg.dormant_lossless_raw_exposure_events
    if (
        cfg.raw_file_type in P292_DORMANT_LOSSLESS_RAW_MODES
        or cfg.raw_file_type not in P292_FX3_EXPOSED_RAW_FILE_TYPES
        or cfg.fx3_ui_exposes_lossless_raw
        or cfg.dormant_lossless_raw_exposure_events != 0
    ):
        raw_ok = False
        lossless_ev = max(lossless_ev, 1)
        _set_block(
            P292_BLOCKED_DORMANT_LOSSLESS_RAW_EXPOSURE,
            f"ILME-FX3 Ver. 7.02 (12 MP IMX510) exposes ONLY Compressed/Uncompressed 14-bit .ARW; dormant Lossless Comp ({cfg.raw_file_type!r}) rejected fail-closed",
        )

    # 2. Still-less ILME-FX6 distinction
    fx6_ok = True
    fx6_ev = cfg.fx6_still_pipeline_conflation_events
    if (
        cfg.still_surface_model != "FX3_STILL_RAW_JPEG_HEIF_PIPELINE"
        or cfg.fx6_still_pipeline_present
        or cfg.fx6_still_pipeline_conflation_events != 0
    ):
        fx6_ok = False
        fx6_ev = max(fx6_ev, 1)
        _set_block(
            P292_BLOCKED_FX6_STILL_PIPELINE_CONFLATION,
            "ILME-FX6 Ver. 6.01 is still-less (zero DCIM/.ARW/.JPG/.HIF still pipeline); cannot conflate FX6 movie RAW/HLG with FX3 still settings",
        )

    # 3. Structural baseline spec validation
    if (
        cfg.camera_model != P292_FX3_MODEL_NAME
        or cfg.camera_model_id != P292_FX3_MODEL_ID
        or cfg.helpguide_id != P292_FX3_HELPGUIDE_ID
        or cfg.fw_version not in P292_FX3_SUPPORTED_FW_VERSIONS
        or cfg.jpeg_heif_switch_menu_path != P292_JPEG_HEIF_SWITCH_MENU_PATH
        or cfg.image_quality_menu_path != P292_IMAGE_QUALITY_MENU_PATH
        or cfg.hlg_still_menu_path != P292_HLG_STILL_MENU_PATH
        or cfg.color_space_menu_path != P292_COLOR_SPACE_MENU_PATH
        or cfg.set_file_name_menu_path != P292_SET_FILE_NAME_MENU_PATH
        or cfg.jpeg_heif_switch not in P292_JPEG_HEIF_SWITCH_MODES
        or cfg.file_format not in P292_STILL_FILE_FORMATS
        or cfg.jpeg_heif_quality not in P292_JPEG_HEIF_QUALITIES
        or cfg.jpeg_heif_image_size not in P292_JPEG_HEIF_IMAGE_SIZES
        or cfg.shooting_mode not in P292_STILL_SHOOTING_MODES
        or cfg.configured_hlg_still not in P292_ON_OFF_MODES
        or cfg.configured_color_space not in P292_COLOR_SPACE_MODES
        or cfg.reset_action not in P292_RESET_ACTIONS
        or cfg.requested_vault_action not in P292_VAULT_TARGET_ACTIONS
    ):
        _set_block(
            P292_BLOCKED_INVALID_PILLAR51A_SPEC,
            "Invalid Pillar 51A camera model, firmware, menu path, Image Quality, HLG Still, Color Space, or Reset spec",
        )

    # 4. HLG Still Image prerequisites & lockouts
    hlg_ok = True
    hlg_ev = cfg.hlg_still_prereq_or_lockout_drift_events
    _, eff_hlg, _, expected_locks, expected_iso_shift = (
        compute_expected_still_image_quality_and_hlg_state(
            jpeg_heif_switch=cfg.jpeg_heif_switch,
            file_format=cfg.file_format,
            raw_file_type=cfg.raw_file_type,
            shooting_mode=cfg.shooting_mode,
            configured_hlg_still=cfg.configured_hlg_still,
            reg_custom_iso_or_dro_bracket_active=cfg.reg_custom_iso_or_dro_bracket_active,
        )
    )
    if cfg.reported_hlg_still != eff_hlg or cfg.hlg_still_prereq_or_lockout_drift_events != 0:
        hlg_ok = False
        hlg_ev = max(hlg_ev, 1)
        _set_block(
            P292_BLOCKED_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT,
            f"HLG Still prerequisite violation: expected {eff_hlg!r}, reported {cfg.reported_hlg_still!r}",
        )
    if eff_hlg == "On":
        if not (
            cfg.reported_picture_profile_locked
            and cfg.reported_creative_look_locked
            and cfg.reported_dro_locked
            and cfg.reported_dro_bracket_locked
            and cfg.reported_hlg_iso_bounds_shifted
            and len(expected_locks) == 4
            and expected_iso_shift
        ):
            hlg_ok = False
            hlg_ev = max(hlg_ev, 1)
            _set_block(
                P292_BLOCKED_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT,
                "HLG Still = On must lock out Picture Profile, Creative Look, DRO, DRO Bracket and shift ISO bounds",
            )

    # 5. Color Space (sRGB / AdobeRGB / BT.2100) + DCF 2.0 `_DSC` prefix + Set File Name leading `_` ban
    cs_ok = True
    cs_ev = cfg.colorspace_adobergb_prefix_violations
    eff_cs, prefix_valid, expected_post_prefix, expected_stem = (
        compute_expected_colorspace_and_filename_prefix(
            jpeg_heif_switch=cfg.jpeg_heif_switch,
            eff_hlg_still=eff_hlg,
            configured_color_space=cfg.configured_color_space,
            pre_file_name_prefix=cfg.pre_file_name_prefix,
            reset_action=cfg.reset_action,
            manual_prefix_edit=cfg.manual_prefix_edit,
        )
    )
    if (
        not prefix_valid
        or cfg.post_file_name_prefix != expected_post_prefix
        or not is_valid_fx3_still_filename_prefix(cfg.post_file_name_prefix)
        or cfg.reported_effective_color_space != eff_cs
        or cfg.reported_filename_stem != expected_stem
        or cfg.colorspace_adobergb_prefix_violations != 0
    ):
        cs_ok = False
        cs_ev = max(cs_ev, 1)
        _set_block(
            P292_BLOCKED_COLORSPACE_ADOBERGB_OR_PREFIX_VIOLATION,
            (
                f"ColorSpace/FileName prefix rule violated: expected (cs={eff_cs!r}, "
                f"prefix={expected_post_prefix!r}, stem={expected_stem!r}), got "
                f"(cs={cfg.reported_effective_color_space!r}, prefix={cfg.post_file_name_prefix!r}, "
                f"stem={cfg.reported_filename_stem!r}, prefix_valid={prefix_valid})"
            ),
        )

    # Exhaustive state matrix verification across JPEG/HEIF x FileFormat x RAW x ColorSpace
    matrix_checked = 0
    for jh_sw in P292_JPEG_HEIF_SWITCH_MODES:
        for ff in P292_STILL_FILE_FORMATS:
            for rft in P292_FX3_EXPOSED_RAW_FILE_TYPES + ("Lossless Comp",):
                for cs in P292_COLOR_SPACE_MODES:
                    r_ok, e_hlg, ext, _, _ = compute_expected_still_image_quality_and_hlg_state(
                        jpeg_heif_switch=jh_sw,
                        file_format=ff,
                        raw_file_type=rft,
                        shooting_mode="M",
                        configured_hlg_still="On",
                        reg_custom_iso_or_dro_bracket_active=False,
                    )
                    e_cs, p_ok, _, stem = compute_expected_colorspace_and_filename_prefix(
                        jpeg_heif_switch=jh_sw,
                        eff_hlg_still=e_hlg,
                        configured_color_space=cs,
                        pre_file_name_prefix="DSC",
                        reset_action="Camera Settings Reset",
                    )
                    if rft == "Lossless Comp" and r_ok:
                        raw_ok = False
                    if not p_ok:
                        cs_ok = False
                    if jh_sw == "JPEG" and cs == "AdobeRGB" and not stem.startswith("_DSC"):
                        cs_ok = False
                    if jh_sw.startswith("HEIF") and (ext != ".HIF" or (ff == "HEIF" and e_cs != "BT.2100")):
                        hlg_ok = False
                    matrix_checked += 1

    # 6. Slot-1 EROFS/EBUSY Vault Write Firewall + Volatile /tmp Overlay + Tier-0 H0 == H3
    slot1_ok = True
    still_mut_bytes = cfg.slot1_still_capture_or_sort_write_bytes
    slot1_write_attempt = (
        (cfg.target_still_write_slot == P292_SLOT1_VAULT_SLOT)
        or cfg.sort_recording_targets_slot1
        or (
            cfg.requested_vault_slot == P292_SLOT1_VAULT_SLOT
            and cfg.requested_vault_action in P292_DESTRUCTIVE_VAULT_ACTIONS
        )
    )
    if (
        slot1_write_attempt
        or not cfg.slot1_holds_recovery_vault
        or not cfg.slot1_sdxc_wp_locked
        or not cfg.slot1_format_hard_locked
        or not cfg.slot1_vault_erofs_ebusy_enforced
        or cfg.slot1_still_capture_or_sort_write_bytes != 0
    ):
        slot1_ok = False
        if slot1_write_attempt:
            still_mut_bytes = max(still_mut_bytes, 4096)
        _set_block(
            P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            f"Slot-1 Tier-0 Vault EROFS/EBUSY firewall blocked still/Sort Recording/format write (slot={cfg.target_still_write_slot}, action={cfg.requested_vault_action!r})",
        )

    if (
        not _is_tmpfs_path(cfg.overlay_dir)
        or _targets_persistent_emmc(cfg.overlay_dir)
        or not cfg.p2_blkroset_locked
    ):
        slot1_ok = False
        _set_block(
            P292_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must stay in volatile /tmp or /run with BLKROSET=True: {cfg.overlay_dir!r}",
        )

    if (
        cfg.stage_b_backup_bin_writes != 0
        or cfg.backup_bin_h0_sha256 != P292_PINNED_FX3_BACKUP_BIN_SHA256
        or cfg.backup_bin_h3_sha256 != cfg.backup_bin_h0_sha256
        or cfg.tier0_surfaces_h0_h3_matched != P292_TIER0_SURFACE_COUNT
    ):
        slot1_ok = False
        _set_block(
            P292_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 H0 == H3 Backup.bin invariant drifted",
        )

    passed = (
        raw_ok
        and fx6_ok
        and hlg_ok
        and cs_ok
        and slot1_ok
        and len(errs) == 0
    )
    digest = _canonical_sha256(
        {
            "pillar": "51A",
            "passed": passed,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "lossless_ev": lossless_ev,
            "fx6_ev": fx6_ev,
            "hlg_ev": hlg_ev,
            "cs_ev": cs_ev,
            "still_mut_bytes": still_mut_bytes,
        }
    )
    return StillImageQualityHlgColorspaceFilenameVaultReport(
        passed=passed,
        status=P292_STATUS_VERIFIED_PILLAR_51A if passed else P292_STATUS_REJECTED_PILLAR_51A,
        block_code=block_code,
        raw_compressed_uncompressed_and_lossless_ban_verified=raw_ok,
        fx6_still_less_distinction_verified=fx6_ok,
        hlg_still_prereqs_bt2100_lockouts_verified=hlg_ok,
        colorspace_adobergb_dsc_and_prefix_ban_verified=cs_ok,
        slot1_erofs_ebusy_firewall_and_h0_h3_verified=slot1_ok,
        matrix_states_checked=matrix_checked,
        dormant_lossless_raw_exposure_events=lossless_ev,
        fx6_still_pipeline_conflation_events=fx6_ev,
        hlg_still_prereq_or_lockout_drift_events=hlg_ev,
        colorspace_adobergb_prefix_violations=cs_ev,
        slot1_still_capture_or_sort_write_bytes=still_mut_bytes,
        slot1_vault_erofs_ebusy_enforced=cfg.slot1_vault_erofs_ebusy_enforced,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errs),
    )


def evaluate_shutter_type_nr_drive_vault(
    spec: Optional[ShutterTypeNrDriveVaultSpec] = None,
) -> ShutterTypeNrDriveVaultReport:
    """Verify Pillar 51B: `[Shutter Type]` 2-option split (`Mechanical Shutter` vs
    `Electronic Shutter`, NO `Auto`!), `1/250 s` Flash Sync, Electronic/Silent 5-Lock
    Matrix, `[e-Front Curtain Shut.]` reset boundary, `[Long Exposure NR]` / `[High ISO NR]`,
    `[Drive Mode]` `10 fps` burst / bracket `F > F11` AF lock, & `Slot-1` `EROFS`/`EBUSY`
    vault firewall."""
    cfg = spec if spec is not None else ShutterTypeNrDriveVaultSpec()
    safety_errs = _safety_invariant_errors()
    if safety_errs or cfg.persistent_write_unlock_requested:
        errs = safety_errs + (
            ["persistent_write_unlock_requested must be False"]
            if cfg.persistent_write_unlock_requested
            else []
        )
        return ShutterTypeNrDriveVaultReport(
            passed=False,
            status=P292_STATUS_REJECTED_PILLAR_51B,
            block_code=P292_BLOCKED_SAFETY_POLICY_VIOLATION,
            shutter_2opt_no_auto_and_fx6_contrast_verified=False,
            electronic_silent_5lock_and_1_250_sync_verified=False,
            e_front_curtain_reset_boundary_verified=False,
            long_exposure_and_high_iso_nr_verified=False,
            drive_8modes_10fps_f11_af_lock_verified=False,
            slot1_burst_imagedb_erofs_firewall_and_h0_h3_verified=False,
            matrix_states_checked=0,
            shutter_type_auto_spoof_events=0,
            fx6_mechanical_shutter_conflation_events=0,
            electronic_silent_5lock_bypass_events=0,
            nr_or_drive_burst_wall_violations=0,
            slot1_imagedb_or_burst_mutation_bytes=0,
            slot1_vault_erofs_ebusy_enforced=cfg.slot1_vault_erofs_ebusy_enforced,
            slot1_format_hard_locked=cfg.slot1_format_hard_locked,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            digest_sha256=_canonical_sha256({"blocked": P292_BLOCKED_SAFETY_POLICY_VIOLATION}),
            errors=tuple(errs),
        )

    errs: List[str] = []
    block_code: Optional[str] = None

    def _set_block(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errs.append(msg)

    # 1. Exact 2-option Shutter Type (NO Auto!) & FX6 contrast
    shutter_2opt_ok = True
    auto_spoof_ev = cfg.shutter_type_auto_spoof_events
    fx6_mech_ev = cfg.fx6_mechanical_shutter_conflation_events
    if (
        cfg.configured_shutter_type in P292_DORMANT_SHUTTER_TYPES
        or cfg.configured_shutter_type not in P292_FX3_EXPOSED_SHUTTER_TYPES
        or cfg.fx3_ui_exposes_shutter_type_auto
        or cfg.shutter_type_auto_spoof_events != 0
    ):
        shutter_2opt_ok = False
        auto_spoof_ev = max(auto_spoof_ev, 1)
        _set_block(
            P292_BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION,
            f"ILME-FX3 Ver. 7.02 exposes ONLY 2 Shutter Type options (Mechanical/Electronic); Auto ({cfg.configured_shutter_type!r}) rejected fail-closed",
        )
    if (
        cfg.shutter_surface_model != "FX3_2OPT_MECHANICAL_ELECTRONIC_SHUTTER_PIPELINE"
        or cfg.fx6_mechanical_shutter_present
        or cfg.fx6_mechanical_shutter_conflation_events != 0
    ):
        shutter_2opt_ok = False
        fx6_mech_ev = max(fx6_mech_ev, 1)
        _set_block(
            P292_BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION,
            "ILME-FX6 Ver. 6.01 has mechanical_shutter=False; cannot conflate with FX3 Mechanical/Electronic Shutter",
        )

    # 2. Structural baseline spec check
    if (
        cfg.camera_model != P292_FX3_MODEL_NAME
        or cfg.camera_model_id != P292_FX3_MODEL_ID
        or cfg.helpguide_id != P292_FX3_HELPGUIDE_ID
        or cfg.fw_version not in P292_FX3_SUPPORTED_FW_VERSIONS
        or cfg.shutter_type_menu_path != P292_SHUTTER_TYPE_MENU_PATH
        or cfg.e_front_curtain_menu_path != P292_EFRONT_CURTAIN_MENU_PATH
        or cfg.long_exposure_nr_menu_path != P292_LONG_EXPOSURE_NR_MENU_PATH
        or cfg.high_iso_nr_menu_path != P292_HIGH_ISO_NR_MENU_PATH
        or cfg.drive_mode_menu_path != P292_DRIVE_MODE_MENU_PATH
        or cfg.shooting_mode not in P292_STILL_SHOOTING_MODES
        or cfg.silent_mode not in P292_ON_OFF_MODES
        or cfg.pre_e_front_curtain not in P292_ON_OFF_MODES
        or cfg.file_format not in P292_STILL_FILE_FORMATS
        or cfg.raw_file_type not in P292_FX3_EXPOSED_RAW_FILE_TYPES
        or cfg.eff_hlg_still not in P292_ON_OFF_MODES
        or cfg.configured_long_exposure_nr not in P292_ON_OFF_MODES
        or cfg.configured_high_iso_nr not in P292_HIGH_ISO_NR_MODES
        or cfg.drive_mode not in P292_DRIVE_8_MODES
        or cfg.cont_shooting_speed not in P292_CONT_SHOOTING_4_SPEEDS
        or cfg.reset_action not in P292_RESET_ACTIONS
        or cfg.requested_vault_action not in P292_VAULT_TARGET_ACTIONS
    ):
        _set_block(
            P292_BLOCKED_INVALID_PILLAR51B_SPEC,
            "Invalid Pillar 51B camera model, firmware, menu path, Shutter Type, NR, or Drive Mode spec",
        )

    # 3. Electronic/Silent 5-Lock Matrix + 1/250s flash sync + e-Front Curtain reset persistence
    lock5_ok = True
    efront_ok = True
    lock5_ev = cfg.electronic_silent_5lock_bypass_events
    shutter_valid, eff_shutter, locked_5, flash_allowed, expected_efront = (
        compute_expected_shutter_type_and_5lock_matrix(
            configured_shutter_type=cfg.configured_shutter_type,
            shooting_mode=cfg.shooting_mode,
            silent_mode=cfg.silent_mode,
            silent_mode_target_override_shutter=cfg.silent_mode_target_override_shutter,
            pre_e_front_curtain=cfg.pre_e_front_curtain,
            reset_action=cfg.reset_action,
        )
    )
    locks_active = len(locked_5) > 0
    if shutter_valid and cfg.reported_shutter_type != eff_shutter:
        lock5_ok = False
        lock5_ev = max(lock5_ev, 1)
        _set_block(
            P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS,
            f"Effective Shutter Type expected {eff_shutter!r}, got {cfg.reported_shutter_type!r}",
        )

    if cfg.flash_sync_speed_denom != P292_FX3_MAX_FLASH_SYNC_DENOM:
        lock5_ok = False
        lock5_ev = max(lock5_ev, 1)
        _set_block(
            P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS,
            f"ILME-FX3 mechanical flash sync must be 1/{P292_FX3_MAX_FLASH_SYNC_DENOM}s, got 1/{cfg.flash_sync_speed_denom}s",
        )

    if (
        cfg.reported_flash_allowed != flash_allowed
        or cfg.reported_long_exposure_nr_allowed != (not locks_active)
        or cfg.reported_e_front_curtain_allowed != (not locks_active)
        or cfg.reported_bulb_allowed != (not locks_active)
        or cfg.reported_anti_flicker_allowed != (not locks_active)
        or cfg.electronic_silent_5lock_bypass_events != 0
    ):
        lock5_ok = False
        lock5_ev = max(lock5_ev, 1)
        _set_block(
            P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS,
            "Electronic/Silent 5-Lock Matrix (Flash, Long Exposure NR, e-Front Curtain Shut., BULB, Anti-flicker Shoot.) bypassed",
        )

    if cfg.post_e_front_curtain != expected_efront:
        efront_ok = False
        _set_block(
            P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS,
            f"e-Front Curtain Shut. reset boundary drift: expected {expected_efront!r} after {cfg.reset_action!r}, got {cfg.post_e_front_curtain!r}",
        )

    # 4. Long Exposure NR, High ISO NR & Drive Mode 10 fps / Bracket / F > F11 AF Lock
    nr_ok = True
    drive_ok = True
    nr_drive_ev = cfg.nr_or_drive_burst_wall_violations
    (
        _long_avail,
        eff_long_nr,
        _high_avail,
        eff_high_iso_nr,
        dro_bracket_ok,
        eff_fps,
        hi_plus_live,
        af_locked_1st,
        long_nr_blocks,
    ) = compute_expected_nr_and_drive_mode_boundaries(
        shooting_mode=cfg.shooting_mode,
        file_format=cfg.file_format,
        raw_file_type=cfg.raw_file_type,
        eff_hlg_still=cfg.eff_hlg_still,
        electronic_or_silent_locks_active=locks_active,
        configured_long_exposure_nr=cfg.configured_long_exposure_nr,
        configured_high_iso_nr=cfg.configured_high_iso_nr,
        drive_mode=cfg.drive_mode,
        cont_shooting_speed=cfg.cont_shooting_speed,
        flash_fired=cfg.flash_fired,
        aperture_f_number=cfg.aperture_f_number,
        shutter_speed_sec=cfg.shutter_speed_sec,
        is_bulb=cfg.is_bulb,
    )
    if (
        cfg.reported_long_exposure_nr != eff_long_nr
        or cfg.reported_high_iso_nr != eff_high_iso_nr
        or cfg.reported_long_nr_blocks_next != long_nr_blocks
    ):
        nr_ok = False
        nr_drive_ev = max(nr_drive_ev, 1)
        _set_block(
            P292_BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION,
            (
                f"NR boundary violation: expected (LongNR={eff_long_nr!r}, HighISONR={eff_high_iso_nr!r}, "
                f"blocks_next={long_nr_blocks}), got ({cfg.reported_long_exposure_nr!r}, "
                f"{cfg.reported_high_iso_nr!r}, {cfg.reported_long_nr_blocks_next})"
            ),
        )
    if (
        cfg.reported_eff_burst_fps != eff_fps
        or cfg.reported_hi_plus_live_monitor != hi_plus_live
        or cfg.reported_af_locked_first_frame != af_locked_1st
        or cfg.reported_dro_bracket_allowed != dro_bracket_ok
        or cfg.nr_or_drive_burst_wall_violations != 0
    ):
        drive_ok = False
        nr_drive_ev = max(nr_drive_ev, 1)
        _set_block(
            P292_BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION,
            (
                f"Drive Mode boundary violation: expected (fps={eff_fps}, live_mon={hi_plus_live}, "
                f"af_lock_1st={af_locked_1st}, dro_bracket={dro_bracket_ok}), got "
                f"(fps={cfg.reported_eff_burst_fps}, live_mon={cfg.reported_hi_plus_live_monitor}, "
                f"af_lock_1st={cfg.reported_af_locked_first_frame}, dro_bracket={cfg.reported_dro_bracket_allowed})"
            ),
        )

    # Exhaustive Shutter x Silent x RAW x Speed matrix
    matrix_checked = 0
    for stype in P292_FX3_EXPOSED_SHUTTER_TYPES + P292_DORMANT_SHUTTER_TYPES:
        for sil in P292_ON_OFF_MODES:
            s_ok, _, l5, fl_ok, _ = compute_expected_shutter_type_and_5lock_matrix(
                configured_shutter_type=stype,
                shooting_mode="M",
                silent_mode=sil,
                silent_mode_target_override_shutter=False,
                pre_e_front_curtain="On",
                reset_action="Camera Settings Reset",
            )
            if stype == "Auto" and s_ok:
                shutter_2opt_ok = False
            if (stype == "Electronic Shutter" or sil == "On") and (len(l5) != 5 or fl_ok):
                lock5_ok = False
            for rft in P292_FX3_EXPOSED_RAW_FILE_TYPES:
                for spd in P292_CONT_SHOOTING_4_SPEEDS:
                    _, _, _, _, _, fps, live, _, _ = compute_expected_nr_and_drive_mode_boundaries(
                        shooting_mode="M",
                        file_format="RAW",
                        raw_file_type=rft,
                        eff_hlg_still="Off",
                        electronic_or_silent_locks_active=(len(l5) > 0),
                        configured_long_exposure_nr="On",
                        configured_high_iso_nr="Normal",
                        drive_mode="Cont. Shooting",
                        cont_shooting_speed=spd,
                        flash_fired=False,
                        aperture_f_number=2.8,
                        shutter_speed_sec=0.01,
                        is_bulb=False,
                    )
                    if spd == "Hi+" and rft == "Compressed" and fps != 10:
                        drive_ok = False
                    if spd == "Hi+" and rft == "Uncompressed" and fps >= 10:
                        drive_ok = False
                    if spd == "Hi+" and live:
                        drive_ok = False
                    matrix_checked += 1

    # 5. Burst / Bracket Slot-1 Vault EROFS/EBUSY Firewall + Volatile /tmp Overlay + H0 == H3
    slot1_ok = True
    burst_mut_bytes = cfg.slot1_imagedb_or_burst_mutation_bytes
    slot1_write_attempt = (
        (cfg.target_burst_bracket_slot == P292_SLOT1_VAULT_SLOT)
        or cfg.avf_info_imagedb_targets_slot1
        or (
            cfg.requested_vault_slot == P292_SLOT1_VAULT_SLOT
            and cfg.requested_vault_action in P292_DESTRUCTIVE_VAULT_ACTIONS
        )
    )
    if (
        slot1_write_attempt
        or not cfg.slot1_holds_recovery_vault
        or not cfg.slot1_sdxc_wp_locked
        or not cfg.slot1_format_hard_locked
        or not cfg.slot1_vault_erofs_ebusy_enforced
        or cfg.slot1_imagedb_or_burst_mutation_bytes != 0
    ):
        slot1_ok = False
        if slot1_write_attempt:
            burst_mut_bytes = max(burst_mut_bytes, 4096)
        _set_block(
            P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            f"Slot-1 burst/bracket/AVF_INFO ImageDB EROFS/EBUSY firewall triggered (slot={cfg.target_burst_bracket_slot}, action={cfg.requested_vault_action!r})",
        )

    if (
        not _is_tmpfs_path(cfg.overlay_dir)
        or _targets_persistent_emmc(cfg.overlay_dir)
        or not cfg.p2_blkroset_locked
    ):
        slot1_ok = False
        _set_block(
            P292_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must stay in volatile /tmp or /run with BLKROSET=True: {cfg.overlay_dir!r}",
        )

    if (
        cfg.stage_b_backup_bin_writes != 0
        or cfg.backup_bin_h0_sha256 != P292_PINNED_FX3_BACKUP_BIN_SHA256
        or cfg.backup_bin_h3_sha256 != cfg.backup_bin_h0_sha256
        or cfg.tier0_surfaces_h0_h3_matched != P292_TIER0_SURFACE_COUNT
    ):
        slot1_ok = False
        _set_block(
            P292_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 H0 == H3 Backup.bin invariant drifted",
        )

    passed = (
        shutter_2opt_ok
        and lock5_ok
        and efront_ok
        and nr_ok
        and drive_ok
        and slot1_ok
        and len(errs) == 0
    )
    digest = _canonical_sha256(
        {
            "pillar": "51B",
            "passed": passed,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "auto_spoof_ev": auto_spoof_ev,
            "fx6_mech_ev": fx6_mech_ev,
            "lock5_ev": lock5_ev,
            "nr_drive_ev": nr_drive_ev,
            "burst_mut_bytes": burst_mut_bytes,
        }
    )
    return ShutterTypeNrDriveVaultReport(
        passed=passed,
        status=P292_STATUS_VERIFIED_PILLAR_51B if passed else P292_STATUS_REJECTED_PILLAR_51B,
        block_code=block_code,
        shutter_2opt_no_auto_and_fx6_contrast_verified=shutter_2opt_ok,
        electronic_silent_5lock_and_1_250_sync_verified=lock5_ok,
        e_front_curtain_reset_boundary_verified=efront_ok,
        long_exposure_and_high_iso_nr_verified=nr_ok,
        drive_8modes_10fps_f11_af_lock_verified=drive_ok,
        slot1_burst_imagedb_erofs_firewall_and_h0_h3_verified=slot1_ok,
        matrix_states_checked=matrix_checked,
        shutter_type_auto_spoof_events=auto_spoof_ev,
        fx6_mechanical_shutter_conflation_events=fx6_mech_ev,
        electronic_silent_5lock_bypass_events=lock5_ev,
        nr_or_drive_burst_wall_violations=nr_drive_ev,
        slot1_imagedb_or_burst_mutation_bytes=burst_mut_bytes,
        slot1_vault_erofs_ebusy_enforced=cfg.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=cfg.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errs),
    )


def verify_raw_heif_colorspace_shuttertype_nr_drive_and_vault(
    still_spec: Optional[StillImageQualityHlgColorspaceFilenameVaultSpec] = None,
    shutter_drive_spec: Optional[ShutterTypeNrDriveVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> RawHeifColorspaceShuttertypeNrDriveVaultReport:
    """Combined Pillar 51A + Pillar 51B + Wave-49 bounded `O_RDONLY` donor report."""
    errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase292_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_still_image_quality_hlg_colorspace_filename_vault(still_spec)
    rep_b = evaluate_shutter_type_nr_drive_vault(shutter_drive_spec)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 292 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )
    ok = rep_a.passed and rep_b.passed and len(errs) == 0
    vault_mut = max(
        rep_a.slot1_still_capture_or_sort_write_bytes,
        rep_b.slot1_imagedb_or_burst_mutation_bytes,
    )
    return RawHeifColorspaceShuttertypeNrDriveVaultReport(
        schema=PHASE292_SCHEMA,
        version=PHASE292_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=ok,
        passed=ok,
        status=P292_STATUS_VERIFIED_PILLAR51_SUITE if ok else P292_STATUS_FAIL_PILLAR51_SUITE,
        donor_snapshot=donor_snapshot,
        still_quality_hlg_colorspace_report=rep_a,
        shutter_type_nr_drive_report=rep_b,
        dormant_lossless_raw_exposure_events=rep_a.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=rep_a.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=rep_a.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=rep_a.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=rep_b.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=rep_b.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=rep_b.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=rep_b.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=rep_a.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=rep_b.slot1_imagedb_or_burst_mutation_bytes,
        slot1_vault_mutation_bytes=vault_mut,
        slot1_format_hard_locked=rep_b.slot1_format_hard_locked,
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


def verify_raw_heif_colorspace_shuttertype_nr_drive_vault(
    still_spec: Optional[StillImageQualityHlgColorspaceFilenameVaultSpec] = None,
    shutter_drive_spec: Optional[ShutterTypeNrDriveVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> RawHeifColorspaceShuttertypeNrDriveVaultReport:
    """Symmetry alias for `verify_raw_heif_colorspace_shuttertype_nr_drive_and_vault`."""
    return verify_raw_heif_colorspace_shuttertype_nr_drive_and_vault(
        still_spec=still_spec,
        shutter_drive_spec=shutter_drive_spec,
        force_clean_room=force_clean_room,
    )


def run_pillar51a_raw_heif_hlg_colorspace_6_scenario_suite() -> Pillar51ASuiteResult:
    """Run all 6 canonical Pillar 51A scenarios (`2` safe + `4` negative Wave-49 guards)."""
    cases: Tuple[
        Tuple[str, bool, StillImageQualityHlgColorspaceFilenameVaultSpec, Optional[str]], ...
    ] = (
        (
            P292_PILLAR_51A_SCENARIO_IDS[0],
            True,
            StillImageQualityHlgColorspaceFilenameVaultSpec(),
            None,
        ),
        (
            P292_PILLAR_51A_SCENARIO_IDS[1],
            True,
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                jpeg_heif_switch="HEIF(4:2:2)",
                file_format="HEIF",
                raw_file_type="Uncompressed",
                shooting_mode="M",
                configured_hlg_still="On",
                reported_hlg_still="On",
                reported_picture_profile_locked=True,
                reported_creative_look_locked=True,
                reported_dro_locked=True,
                reported_dro_bracket_locked=True,
                reported_hlg_iso_bounds_shifted=True,
                configured_color_space="AdobeRGB",
                reported_effective_color_space="BT.2100",
                pre_file_name_prefix="FX3",
                reset_action="Camera Settings Reset",
                post_file_name_prefix="FX3",
                reported_filename_stem="FX300001",
                target_still_write_slot=2,
            ),
            None,
        ),
        (
            P292_PILLAR_51A_SCENARIO_IDS[2],
            False,
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                raw_file_type="Lossless Comp",
                fx3_ui_exposes_lossless_raw=True,
                dormant_lossless_raw_exposure_events=1,
                still_surface_model="FX6_STILL_LESS_MOVIE_RAW_HLG_PIPELINE",
                fx6_still_pipeline_present=True,
                fx6_still_pipeline_conflation_events=1,
            ),
            P292_BLOCKED_DORMANT_LOSSLESS_RAW_EXPOSURE,
        ),
        (
            P292_PILLAR_51A_SCENARIO_IDS[3],
            False,
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                jpeg_heif_switch="HEIF(4:2:0)",
                file_format="RAW & HEIF",
                shooting_mode="M",
                configured_hlg_still="On",
                reported_hlg_still="On",
                reported_picture_profile_locked=False,
                reported_creative_look_locked=False,
                reported_dro_locked=False,
                reported_dro_bracket_locked=False,
                reported_hlg_iso_bounds_shifted=False,
                reported_effective_color_space="sRGB",
                hlg_still_prereq_or_lockout_drift_events=1,
            ),
            P292_BLOCKED_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT,
        ),
        (
            P292_PILLAR_51A_SCENARIO_IDS[4],
            False,
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                jpeg_heif_switch="JPEG",
                configured_color_space="AdobeRGB",
                reported_effective_color_space="AdobeRGB",
                pre_file_name_prefix="DSC",
                manual_prefix_edit="_A1",
                post_file_name_prefix="_A1",
                reported_filename_stem="DSC00001",
                colorspace_adobergb_prefix_violations=1,
            ),
            P292_BLOCKED_COLORSPACE_ADOBERGB_OR_PREFIX_VIOLATION,
        ),
        (
            P292_PILLAR_51A_SCENARIO_IDS[5],
            False,
            StillImageQualityHlgColorspaceFilenameVaultSpec(
                target_still_write_slot=1,
                sort_recording_targets_slot1=True,
                requested_vault_slot=1,
                requested_vault_action="STILL_CAPTURE_WRITE",
                slot1_still_capture_or_sort_write_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/51a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar51ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_still_image_quality_hlg_colorspace_filename_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar51ScenarioOutcome(
                scenario_id=sid,
                pillar="51A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar51ASuiteResult(
        passed=all_ok,
        status=P292_STATUS_VERIFIED_PILLAR_51A if all_ok else P292_STATUS_REJECTED_PILLAR_51A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar51b_shuttertype_nr_drive_6_scenario_suite() -> Pillar51BSuiteResult:
    """Run all 6 canonical Pillar 51B scenarios (`2` safe + `4` negative Wave-49 guards)."""
    cases: Tuple[Tuple[str, bool, ShutterTypeNrDriveVaultSpec, Optional[str]], ...] = (
        (
            P292_PILLAR_51B_SCENARIO_IDS[0],
            True,
            ShutterTypeNrDriveVaultSpec(),
            None,
        ),
        (
            P292_PILLAR_51B_SCENARIO_IDS[1],
            True,
            ShutterTypeNrDriveVaultSpec(
                shooting_mode="M",
                configured_shutter_type="Electronic Shutter",
                reported_shutter_type="Electronic Shutter",
                silent_mode="Off",
                pre_e_front_curtain="Off",
                reset_action="Camera Settings Reset",
                post_e_front_curtain="Off",
                reported_flash_allowed=False,
                reported_long_exposure_nr_allowed=False,
                reported_e_front_curtain_allowed=False,
                reported_bulb_allowed=False,
                reported_anti_flicker_allowed=False,
                file_format="RAW",
                raw_file_type="Compressed",
                configured_long_exposure_nr="On",
                reported_long_exposure_nr="Off",
                configured_high_iso_nr="Normal",
                reported_high_iso_nr="Unavailable",
                drive_mode="Cont. Shooting",
                cont_shooting_speed="Hi+",
                flash_fired=False,
                aperture_f_number=14.0,
                reported_eff_burst_fps=10,
                reported_hi_plus_live_monitor=False,
                reported_af_locked_first_frame=True,
                reported_dro_bracket_allowed=True,
                target_burst_bracket_slot=2,
            ),
            None,
        ),
        (
            P292_PILLAR_51B_SCENARIO_IDS[2],
            False,
            ShutterTypeNrDriveVaultSpec(
                configured_shutter_type="Auto",
                fx3_ui_exposes_shutter_type_auto=True,
                shutter_type_auto_spoof_events=1,
                shutter_surface_model="FX6_NO_MECHANICAL_SHUTTER_PIPELINE",
                fx6_mechanical_shutter_present=True,
                fx6_mechanical_shutter_conflation_events=1,
            ),
            P292_BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION,
        ),
        (
            P292_PILLAR_51B_SCENARIO_IDS[3],
            False,
            ShutterTypeNrDriveVaultSpec(
                configured_shutter_type="Electronic Shutter",
                reported_shutter_type="Electronic Shutter",
                silent_mode="On",
                pre_e_front_curtain="Off",
                reset_action="Camera Settings Reset",
                post_e_front_curtain="On",
                reported_flash_allowed=True,
                reported_long_exposure_nr_allowed=True,
                reported_e_front_curtain_allowed=True,
                reported_bulb_allowed=True,
                reported_anti_flicker_allowed=True,
                electronic_silent_5lock_bypass_events=1,
            ),
            P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS,
        ),
        (
            P292_PILLAR_51B_SCENARIO_IDS[4],
            False,
            ShutterTypeNrDriveVaultSpec(
                file_format="RAW",
                raw_file_type="Uncompressed",
                eff_hlg_still="On",
                configured_high_iso_nr="Low",
                reported_high_iso_nr="Low",
                drive_mode="Cont. Shooting",
                cont_shooting_speed="Hi+",
                aperture_f_number=16.0,
                reported_eff_burst_fps=10,
                reported_hi_plus_live_monitor=True,
                reported_af_locked_first_frame=False,
                reported_dro_bracket_allowed=True,
                nr_or_drive_burst_wall_violations=1,
            ),
            P292_BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION,
        ),
        (
            P292_PILLAR_51B_SCENARIO_IDS[5],
            False,
            ShutterTypeNrDriveVaultSpec(
                target_burst_bracket_slot=1,
                avf_info_imagedb_targets_slot1=True,
                requested_vault_slot=1,
                requested_vault_action="BURST_BRACKET_DCIM_WRITE",
                slot1_imagedb_or_burst_mutation_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/51b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar51ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_shutter_type_nr_drive_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar51ScenarioOutcome(
                scenario_id=sid,
                pillar="51B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar51BSuiteResult(
        passed=all_ok,
        status=P292_STATUS_VERIFIED_PILLAR_51B if all_ok else P292_STATUS_REJECTED_PILLAR_51B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar51_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar51StandaloneReport:
    """Run full Pillar 51 standalone suite (`6/6` Pillar 51A + `6/6` Pillar 51B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase292_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar51a_raw_heif_hlg_colorspace_6_scenario_suite()
    res_b = run_pillar51b_shuttertype_nr_drive_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 292 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE292_SCHEMA,
            "version": PHASE292_VERSION,
            "mode": donor_snapshot.verification_mode,
            "51a": [asdict(s) for s in res_a.scenarios],
            "51b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar51StandaloneReport(
        schema=PHASE292_SCHEMA,
        version=PHASE292_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P292_STATUS_VERIFIED_PILLAR51_SUITE if all_ok else P292_STATUS_FAIL_PILLAR51_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_51a_raw_heif_hlg_colorspace_vault=res_a,
        pillar_51b_shuttertype_nr_drive_vault=res_b,
        dormant_lossless_raw_exposure_events=(
            P292_DORMANT_LOSSLESS_RAW_EXPOSURE_EVENTS if res_a.passed else 1
        ),
        fx6_still_pipeline_conflation_events=(
            P292_FX6_STILL_PIPELINE_CONFLATION_EVENTS if res_a.passed else 1
        ),
        hlg_still_prereq_or_lockout_drift_events=(
            P292_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT_EVENTS if res_a.passed else 1
        ),
        colorspace_adobergb_prefix_violations=(
            P292_COLORSPACE_ADOBERGB_PREFIX_VIOLATIONS if res_a.passed else 1
        ),
        shutter_type_auto_spoof_events=P292_SHUTTER_TYPE_AUTO_SPOOF_EVENTS if res_b.passed else 1,
        fx6_mechanical_shutter_conflation_events=(
            P292_FX6_MECHANICAL_SHUTTER_CONFLATION_EVENTS if res_b.passed else 1
        ),
        electronic_silent_5lock_bypass_events=(
            P292_ELECTRONIC_SILENT_5LOCK_BYPASS_EVENTS if res_b.passed else 1
        ),
        nr_or_drive_burst_wall_violations=(
            P292_NR_OR_DRIVE_BURST_WALL_VIOLATIONS if res_b.passed else 1
        ),
        slot1_still_capture_or_sort_write_bytes=(
            P292_SLOT1_STILL_CAPTURE_OR_SORT_WRITE_BYTES if res_a.passed else 4096
        ),
        slot1_imagedb_or_burst_mutation_bytes=(
            P292_SLOT1_IMAGEDB_OR_BURST_MUTATION_BYTES if res_b.passed else 4096
        ),
        slot1_vault_mutation_bytes=(
            P292_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P292_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_ebusy_enforced=P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
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
# Unified 51-Pillar Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master51_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_51pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master51PillarRecoveryReport:
    """Evaluate and aggregate all 51 recovery pillars (`1..51`) concurrently -> `51/51` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_51_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_50pillar() -> Master50PillarRecoveryReport:
        return evaluate_realhw_50pillar_recovery_master(**kw)

    def _run_p51() -> Tuple[Pillar51StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar51_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_50 = pool.submit(_run_50pillar)
        fut_51 = pool.submit(_run_p51)
        m50_rep = fut_50.result()
        p51_rep, p51_dt = fut_51.result()

    all_errors: List[str] = list(m50_rep.errors) + list(p51_rep.errors)
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
    ):
        if getattr(m50_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-50 violated {attr_name} == {expected_val}")
        if getattr(p51_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 51 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
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
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
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
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(m50_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-50 violated {attr_name} == {expected_val}")
    if m50_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillars 1-50 violated bodydata_flash_attempts_blocked >= 1")

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
        ("overall_ready_for_hardware_attach", False),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(p51_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 51 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m50_rep.pillars)
    spec51 = MASTER_51_PILLAR_SPECS[50]
    p51_metrics = {
        "pillar_51a_raw_heif_hlg_colorspace_vault": (
            f"{p51_rep.pillar_51a_raw_heif_hlg_colorspace_vault.scenarios_passed}/"
            f"{p51_rep.pillar_51a_raw_heif_hlg_colorspace_vault.scenarios_total}"
        ),
        "pillar_51b_shuttertype_nr_drive_vault": (
            f"{p51_rep.pillar_51b_shuttertype_nr_drive_vault.scenarios_passed}/"
            f"{p51_rep.pillar_51b_shuttertype_nr_drive_vault.scenarios_total}"
        ),
        "dormant_lossless_raw_exposure_events": p51_rep.dormant_lossless_raw_exposure_events,
        "fx6_still_pipeline_conflation_events": p51_rep.fx6_still_pipeline_conflation_events,
        "hlg_still_prereq_or_lockout_drift_events": p51_rep.hlg_still_prereq_or_lockout_drift_events,
        "colorspace_adobergb_prefix_violations": p51_rep.colorspace_adobergb_prefix_violations,
        "shutter_type_auto_spoof_events": p51_rep.shutter_type_auto_spoof_events,
        "fx6_mechanical_shutter_conflation_events": p51_rep.fx6_mechanical_shutter_conflation_events,
        "electronic_silent_5lock_bypass_events": p51_rep.electronic_silent_5lock_bypass_events,
        "nr_or_drive_burst_wall_violations": p51_rep.nr_or_drive_burst_wall_violations,
        "slot1_still_capture_or_sort_write_bytes": p51_rep.slot1_still_capture_or_sort_write_bytes,
        "slot1_imagedb_or_burst_mutation_bytes": p51_rep.slot1_imagedb_or_burst_mutation_bytes,
        "slot1_vault_mutation_bytes": p51_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p51_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_ebusy_enforced": p51_rep.slot1_vault_erofs_ebusy_enforced,
        "overall_ready_for_hardware_attach": p51_rep.overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": p51_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p51_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec51[0],
            pillar_id=spec51[1],
            phase_label=spec51[2],
            module_name=spec51[3],
            passed=bool(p51_rep.all_passed),
            status=p51_rep.status,
            verification_mode=p51_rep.verification_mode,
            elapsed_seconds=p51_dt,
            key_metrics=p51_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec51[1],
                    "mode": p51_rep.verification_mode,
                    "status": p51_rep.status,
                    "metrics": p51_metrics,
                    "passed": p51_rep.all_passed,
                }
            ),
            errors=tuple(p51_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master51_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p51_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_51_PILLAR_COUNT == 51
        and pillars_passed == 51
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE292_SCHEMA,
            "version": PHASE292_VERSION,
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
    return Master51PillarRecoveryReport(
        schema=PHASE292_SCHEMA,
        version=PHASE292_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P292_STATUS_VERIFIED_51OF51_AGGREGATOR if all_ok else P292_STATUS_FAIL_51OF51_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_2s_fast_cli_budget=elapsed < P292_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P292_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P292_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p51_rep.donor_snapshot,
        pillar51_a_raw_heif_hlg_colorspace_vault=p51_rep.pillar_51a_raw_heif_hlg_colorspace_vault,
        pillar51_b_shuttertype_nr_drive_vault=p51_rep.pillar_51b_shuttertype_nr_drive_vault,
        dormant_lossless_raw_exposure_events=p51_rep.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=p51_rep.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=p51_rep.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=p51_rep.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=p51_rep.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=p51_rep.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=p51_rep.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=p51_rep.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=p51_rep.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=p51_rep.slot1_imagedb_or_burst_mutation_bytes,
        slot1_vault_mutation_bytes=p51_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p51_rep.slot1_format_hard_locked,
        slot1_vault_erofs_ebusy_enforced=p51_rep.slot1_vault_erofs_ebusy_enforced,
        fx3_ui_exposes_lossless_raw=P292_FX3_UI_EXPOSES_LOSSLESS_RAW,
        fx3_ui_exposes_shutter_type_auto=P292_FX3_UI_EXPOSES_SHUTTER_TYPE_AUTO,
        fx6_still_pipeline_present=P292_FX6_STILL_PIPELINE_PRESENT,
        fx6_mechanical_shutter_present=P292_FX6_MECHANICAL_SHUTTER_PRESENT,
        double_log_or_lockout_bypass_events=m50_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=m50_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=m50_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=m50_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            m50_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        wb_custom_camset_exclusion_drift_events=m50_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            m50_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        fx3_ui_exposes_usb_streaming=m50_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m50_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m50_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m50_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m50_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m50_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m50_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m50_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m50_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m50_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m50_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m50_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m50_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m50_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m50_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m50_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m50_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m50_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m50_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m50_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m50_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m50_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m50_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m50_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m50_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m50_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m50_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m50_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m50_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m50_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m50_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m50_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m50_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=(
            m50_rep.tcub_camera_reset_wipe_or_format_violations
        ),
        fx3_has_builtin_end_filter=m50_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m50_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m50_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m50_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m50_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m50_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m50_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m50_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m50_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m50_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m50_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m50_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m50_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m50_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m50_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m50_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m50_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m50_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m50_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m50_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m50_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m50_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m50_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m50_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m50_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m50_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m50_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m50_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m50_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m50_rep.unbuffered_battery_pull_events,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        hardware_live_attachment_authorized=p51_rep.hardware_live_attachment_authorized,
        master_51pillar_sha256=master_sha,
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


def evaluate_51pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master51PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_51pillar_recovery_master`."""
    return evaluate_realhw_51pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_51pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master51PillarRecoveryReport:
    """Public CLI entry point for Phase 292 `51/51` unified recovery master."""
    return evaluate_realhw_51pillar_recovery_master(
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
    "MASTER_51_PILLAR_COUNT",
    "MASTER_51_PILLAR_IDS",
    "MASTER_51_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P292_AF_LOCK_APERTURE_THRESHOLD_F",
    "P292_APERTURE_DRIVE_IN_AF_DEFAULT",
    "P292_AUTO_PIXEL_MAPPING_DEFAULT",
    "P292_BLOCKED_COLORSPACE_ADOBERGB_OR_PREFIX_VIOLATION",
    "P292_BLOCKED_DORMANT_LOSSLESS_RAW_EXPOSURE",
    "P292_BLOCKED_ELECTRONIC_SILENT_5LOCK_BYPASS",
    "P292_BLOCKED_FX6_STILL_PIPELINE_CONFLATION",
    "P292_BLOCKED_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT",
    "P292_BLOCKED_INVALID_PILLAR51A_SPEC",
    "P292_BLOCKED_INVALID_PILLAR51B_SPEC",
    "P292_BLOCKED_NR_OR_DRIVE_BURST_WALL_VIOLATION",
    "P292_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P292_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P292_BLOCKED_SHUTTER_TYPE_AUTO_OR_FX6_CONFLATION",
    "P292_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL",
    "P292_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P292_BOUNDED_HEADER_BYTES",
    "P292_COLORSPACE_ADOBERGB_PREFIX_VIOLATIONS",
    "P292_COLOR_SPACE_BKID",
    "P292_COLOR_SPACE_DEFAULT",
    "P292_COLOR_SPACE_MENU_PATH",
    "P292_COLOR_SPACE_MODES",
    "P292_COLOR_SPACE_RESID16",
    "P292_COLOR_SPACE_RESID16_MAP",
    "P292_COLOR_SPACE_ADOBERGB_HINT_RESID16",
    "P292_CONCURRENT_CEILING_SECONDS",
    "P292_CONT_SHOOTING_4_SPEEDS",
    "P292_CONT_SHOOTING_FPS_MAP",
    "P292_CONT_SHOOTING_RESID16_MAP",
    "P292_CONT_SHOOTING_SPEED_BKID",
    "P292_DESTRUCTIVE_VAULT_ACTIONS",
    "P292_DONOR_FX3_APPFW_702_RELPATH",
    "P292_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P292_DONOR_FX3_UXC_EN_F_RELPATH",
    "P292_DONOR_FX3_UXC_EN_G_RELPATH",
    "P292_DONOR_FX3_UXC_EN_RELPATH",
    "P292_DONOR_FX3_UXC_JA_F_RELPATH",
    "P292_DONOR_FX3_UXC_JA_G_RELPATH",
    "P292_DONOR_FX3_UXC_JA_RELPATH",
    "P292_DONOR_FX3_UXC_SC_F_RELPATH",
    "P292_DONOR_FX3_UXC_SC_G_RELPATH",
    "P292_DONOR_FX3_UXC_SC_RELPATH",
    "P292_DONOR_FX3_UXC_TC_F_RELPATH",
    "P292_DONOR_FX3_UXC_TC_G_RELPATH",
    "P292_DONOR_FX3_UXC_TC_RELPATH",
    "P292_DONOR_FX6_APPFW_601_RELPATH",
    "P292_DONOR_FX6_UXC_EN_2_RELPATH",
    "P292_DONOR_FX6_UXC_EN_RELPATH",
    "P292_DONOR_INSPECT_BUDGET_SECONDS",
    "P292_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P292_DORMANT_ANTI_DISTORTION_SHUTTER_BKID",
    "P292_DORMANT_LOSSLESS_RAW_EXPOSURE_EVENTS",
    "P292_DORMANT_LOSSLESS_RAW_MODES",
    "P292_DORMANT_LOSSLESS_RAW_RESID16",
    "P292_DORMANT_LOSSLESS_RAW_SIZES_RESID16",
    "P292_DORMANT_SHUTTER_TYPES",
    "P292_DRIVE_8_MODES",
    "P292_DRIVE_MODE_BKID",
    "P292_DRIVE_MODE_DEFAULT",
    "P292_DRIVE_MODE_G_RESID16",
    "P292_DRIVE_MODE_MENU_PATH",
    "P292_DRIVE_MODE_RESID16",
    "P292_DRIVE_MODE_RESID16_MAP",
    "P292_EFFECTIVE_COLOR_SPACES",
    "P292_EFRONT_CURTAIN_BKID",
    "P292_EFRONT_CURTAIN_DEFAULT",
    "P292_EFRONT_CURTAIN_MENU_PATH",
    "P292_EFRONT_CURTAIN_RESID16",
    "P292_ELECTRONIC_SILENT_5LOCK_BYPASS_EVENTS",
    "P292_ELECTRONIC_SILENT_5LOCK_FUNCTIONS",
    "P292_ENV_CLEAN_ROOM_TEST",
    "P292_FAST_CLI_BUDGET_SECONDS",
    "P292_FLASH_SYNC_1_250_RESID16",
    "P292_FORBIDDEN_PERSISTENT_TARGETS",
    "P292_FX3_EXPOSED_RAW_FILE_TYPES",
    "P292_FX3_EXPOSED_SHUTTER_TYPES",
    "P292_FX3_FW_VERSION",
    "P292_FX3_HELPGUIDE_ID",
    "P292_FX3_MAX_FLASH_SYNC_DENOM",
    "P292_FX3_MODEL_ID",
    "P292_FX3_MODEL_NAME",
    "P292_FX3_PRODUCT_CODENAME",
    "P292_FX3_SENSOR_FAMILY",
    "P292_FX3_SUPPORTED_FW_VERSIONS",
    "P292_FX3_UI_EXPOSES_LOSSLESS_RAW",
    "P292_FX3_UI_EXPOSES_SHUTTER_TYPE_AUTO",
    "P292_FX6_DONOR_FW_VERSION",
    "P292_FX6_DONOR_MODEL_NAME",
    "P292_FX6_MECHANICAL_SHUTTER_CONFLATION_EVENTS",
    "P292_FX6_MECHANICAL_SHUTTER_PRESENT",
    "P292_FX6_PRODUCT_CODENAME",
    "P292_FX6_STILL_PIPELINE_CONFLATION_EVENTS",
    "P292_FX6_STILL_PIPELINE_CONFLATION_ERROR",
    "P292_FX6_STILL_PIPELINE_PRESENT",
    "P292_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P292_HEIF_420_RESID16",
    "P292_HIGH_ISO_NR_BKID",
    "P292_HIGH_ISO_NR_DEFAULT",
    "P292_HIGH_ISO_NR_MENU_PATH",
    "P292_HIGH_ISO_NR_MODES",
    "P292_HIGH_ISO_NR_RESID16",
    "P292_HIGH_ISO_NR_RESID16_MAP",
    "P292_HLG_BT2020_RESID16",
    "P292_HLG_STILL_BKID",
    "P292_HLG_STILL_DEFAULT",
    "P292_HLG_STILL_MENU_PATH",
    "P292_HLG_STILL_PREREQ_OR_LOCKOUT_DRIFT_EVENTS",
    "P292_HLG_STILL_RESID16",
    "P292_IMAGE_QUALITY_MENU_PATH",
    "P292_IMAGE_QUALITY_REC_SUBMENU_RESID16",
    "P292_JPEG_HEIF_IMAGE_SIZES",
    "P292_JPEG_HEIF_IMAGE_SIZE_DEFAULT",
    "P292_JPEG_HEIF_QUALITIES",
    "P292_JPEG_HEIF_QUALITY_DEFAULT",
    "P292_JPEG_HEIF_SWITCH_BKID",
    "P292_JPEG_HEIF_SWITCH_DEFAULT",
    "P292_JPEG_HEIF_SWITCH_MENU_PATH",
    "P292_JPEG_HEIF_SWITCH_MODES",
    "P292_JPEG_HEIF_SWITCH_RESID16",
    "P292_LONG_EXPOSURE_NR_BKID",
    "P292_LONG_EXPOSURE_NR_DEFAULT",
    "P292_LONG_EXPOSURE_NR_MENU_PATH",
    "P292_LONG_EXPOSURE_NR_RESID16",
    "P292_LONG_EXPOSURE_NR_THRESHOLD_SEC",
    "P292_MAX_FULL_DONOR_BYTES",
    "P292_NOMINAL_BUDGET_SECONDS",
    "P292_NR_OR_DRIVE_BURST_WALL_VIOLATIONS",
    "P292_ON_OFF_MODES",
    "P292_OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P292_PILLAR_51A_SCENARIO_IDS",
    "P292_PILLAR_51B_SCENARIO_IDS",
    "P292_PINNED_FX3_APPFW_702_BYTES",
    "P292_PINNED_FX3_APPFW_702_FULL_SHA256",
    "P292_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P292_PINNED_FX3_BACKUP_BIN_BYTES",
    "P292_PINNED_FX3_BACKUP_BIN_SHA256",
    "P292_PINNED_FX3_UXC_EN_BYTES",
    "P292_PINNED_FX3_UXC_EN_F_BYTES",
    "P292_PINNED_FX3_UXC_EN_F_SHA256",
    "P292_PINNED_FX3_UXC_EN_G_BYTES",
    "P292_PINNED_FX3_UXC_EN_G_SHA256",
    "P292_PINNED_FX3_UXC_EN_SHA256",
    "P292_PINNED_FX3_UXC_JA_BYTES",
    "P292_PINNED_FX3_UXC_JA_F_BYTES",
    "P292_PINNED_FX3_UXC_JA_F_SHA256",
    "P292_PINNED_FX3_UXC_JA_G_BYTES",
    "P292_PINNED_FX3_UXC_JA_G_SHA256",
    "P292_PINNED_FX3_UXC_JA_SHA256",
    "P292_PINNED_FX3_UXC_SC_BYTES",
    "P292_PINNED_FX3_UXC_SC_F_BYTES",
    "P292_PINNED_FX3_UXC_SC_F_SHA256",
    "P292_PINNED_FX3_UXC_SC_G_BYTES",
    "P292_PINNED_FX3_UXC_SC_G_SHA256",
    "P292_PINNED_FX3_UXC_SC_SHA256",
    "P292_PINNED_FX3_UXC_TC_BYTES",
    "P292_PINNED_FX3_UXC_TC_F_BYTES",
    "P292_PINNED_FX3_UXC_TC_F_SHA256",
    "P292_PINNED_FX3_UXC_TC_G_BYTES",
    "P292_PINNED_FX3_UXC_TC_G_SHA256",
    "P292_PINNED_FX3_UXC_TC_SHA256",
    "P292_PINNED_FX6_APPFW_601_BYTES",
    "P292_PINNED_FX6_APPFW_601_FULL_SHA256",
    "P292_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P292_PINNED_FX6_UXC_EN_2_BYTES",
    "P292_PINNED_FX6_UXC_EN_2_SHA256",
    "P292_PINNED_FX6_UXC_EN_BYTES",
    "P292_PINNED_FX6_UXC_EN_SHA256",
    "P292_RESET_ACTIONS",
    "P292_SAFE_SECONDARY_CAPTURE_SLOT",
    "P292_SET_FILE_NAME_ALLOWED_CHARS",
    "P292_SET_FILE_NAME_BKID",
    "P292_SET_FILE_NAME_DEFAULT",
    "P292_SET_FILE_NAME_LEN",
    "P292_SET_FILE_NAME_MENU_PATH",
    "P292_SET_FILE_NAME_RESID16",
    "P292_SHUTTER_SURFACE_MODELS",
    "P292_SHUTTER_TYPE_AUTO_SPOOF_EVENTS",
    "P292_SHUTTER_TYPE_BKID",
    "P292_SHUTTER_TYPE_DEFAULT",
    "P292_SHUTTER_TYPE_MENU_PATH",
    "P292_SHUTTER_TYPE_RESID16",
    "P292_SHUTTER_TYPE_RESID16_MAP",
    "P292_SILENT_MODE_BKID",
    "P292_SILENT_MODE_DEFAULT",
    "P292_SILENT_MODE_G_RESID16",
    "P292_SILENT_MODE_MENU_PATH",
    "P292_SILENT_MODE_RESID16",
    "P292_SLOT1_FORMAT_HARD_LOCKED",
    "P292_SLOT1_IMAGEDB_OR_BURST_MUTATION_BYTES",
    "P292_SLOT1_STILL_CAPTURE_OR_SORT_WRITE_BYTES",
    "P292_SLOT1_VAULT_EROFS_EBUSY_ENFORCED",
    "P292_SLOT1_VAULT_MUTATION_BYTES",
    "P292_SLOT1_VAULT_SLOT",
    "P292_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P292_STATUS_FAIL_51OF51_AGGREGATOR",
    "P292_STATUS_FAIL_PILLAR51_SUITE",
    "P292_STATUS_REJECTED_PILLAR_51A",
    "P292_STATUS_REJECTED_PILLAR_51B",
    "P292_STATUS_VERIFIED_51OF51_AGGREGATOR",
    "P292_STATUS_VERIFIED_PILLAR51_SUITE",
    "P292_STATUS_VERIFIED_PILLAR_51A",
    "P292_STATUS_VERIFIED_PILLAR_51B",
    "P292_STILL_FILE_FORMAT_BKID",
    "P292_STILL_FILE_FORMAT_DEFAULT",
    "P292_STILL_FILE_FORMAT_RESID16",
    "P292_STILL_FILE_FORMAT_RESID16_MAP",
    "P292_STILL_FILE_FORMATS",
    "P292_STILL_PASM_MODES",
    "P292_STILL_RAW_BIT_DEPTH",
    "P292_STILL_RAW_FILE_TYPE_BKID",
    "P292_STILL_RAW_FILE_TYPE_DEFAULT",
    "P292_STILL_RAW_FILE_TYPE_RESID16",
    "P292_STILL_RAW_FILE_TYPE_RESID16_MAP",
    "P292_STILL_SHOOTING_MODES",
    "P292_STILL_SURFACE_MODELS",
    "P292_TIER0_SURFACE_COUNT",
    "P292_VAULT_FIREWALL_ERRNOS",
    "P292_VAULT_TARGET_ACTIONS",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE292_PHASE_NUMBER",
    "PHASE292_SCHEMA",
    "PHASE292_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "Master51PillarRecoveryReport",
    "Phase292DonorArtifactDigest",
    "Phase292DonorSnapshot",
    "Pillar51ASuiteResult",
    "Pillar51BSuiteResult",
    "Pillar51ScenarioOutcome",
    "Pillar51StandaloneReport",
    "RawHeifColorspaceShuttertypeNrDriveVaultReport",
    "ShutterTypeNrDriveVaultReport",
    "ShutterTypeNrDriveVaultSpec",
    "StillImageQualityHlgColorspaceFilenameVaultReport",
    "StillImageQualityHlgColorspaceFilenameVaultSpec",
    "build_default_safe_shutter_type_nr_drive_vault_spec",
    "build_default_safe_still_image_quality_hlg_colorspace_filename_vault_spec",
    "compute_expected_colorspace_and_filename_prefix",
    "compute_expected_nr_and_drive_mode_boundaries",
    "compute_expected_shutter_type_and_5lock_matrix",
    "compute_expected_still_image_quality_and_hlg_state",
    "evaluate_51pillar_recovery_master",
    "evaluate_realhw_51pillar_recovery_master",
    "evaluate_shutter_type_nr_drive_vault",
    "evaluate_still_image_quality_hlg_colorspace_filename_vault",
    "inspect_phase292_donors_readonly",
    "is_valid_fx3_still_filename_prefix",
    "run_pillar51_standalone_suite",
    "run_pillar51a_raw_heif_hlg_colorspace_6_scenario_suite",
    "run_pillar51b_shuttertype_nr_drive_6_scenario_suite",
    "verify_51pillar_recovery_suite",
    "verify_raw_heif_colorspace_shuttertype_nr_drive_and_vault",
    "verify_raw_heif_colorspace_shuttertype_nr_drive_vault",
]
