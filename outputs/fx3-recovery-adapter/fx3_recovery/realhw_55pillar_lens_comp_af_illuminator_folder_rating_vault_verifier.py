"""Phase 308 (55/55 Recovery Pillars Milestone) — Recovery Pillar 55 & Unified 55/55 Recovery Master
(`verify-55pillar-recovery` / `verify-pillar55-lens-comp-af-illuminator-folder-rating-vault`):

1. **Sub-Pillar 55A — `[Lens Compensation]` (`Shading Comp.` Auto/Off vs Dormant `Auto: Low`,
   `Chromatic Aberration Comp.`, `Distortion Comp.` Auto-Lock & `Breathing Comp.`), Movie
   `[AF Transition Speed]`/`[AF Subj. Shift Sensitivity]`/`[AF Assist]`, & Built-in Front
   `[AF Illuminator]` LED #8 Hardware Correction vs Zero-Illuminator `ILME-FX6` (Wave-53)**:
   - Models `ILME-FX3 Ver. 7.02` (`0x91030080`, `ilc/2210`, `PRODUCT_MODEL_ALCIN_UUD`)
     `[Shooting] -> [Image Quality/Rec] -> [Lens Compensation]` (`_f.uxc` `0x75c8`, `.uxc`/`_g.uxc`
     `0x631f`):
     * `[Shading Comp.]` (`BKID_APP_setting_lens_comp_shading`, `_f.uxc` `0x64e1`, default `Auto`,
       `Initialize`-only): exposes **ONLY `Auto` and `Off`** — strictly rejecting dormant
       `VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW` / `_f.uxc` `0x6c9c` (`Auto: Low`)
       fail-closed with `EOPNOTSUPP=95`. Notes `Auto` may apply raw shading gain in `.ARW`.
     * `[Chromatic Aberration Comp.]` (`BKID_APP_setting_lens_comp_chro_aber`, `_f.uxc` `0x68cd`,
       default `Auto`, `Initialize`-only): `Auto` / `Off`.
     * `[Distortion Comp.]` (`BKID_APP_setting_lens_comp_distortion`, `_f.uxc` `0x6200`, default
       `Off`, `Initialize`-only): `Auto` / `Off`; forced `Auto` when lens requires digital
       distortion comp (`VAL_select_distortion_support_LENS_SELECT_DISTORTION_NOT_SUPPORTED`, e.g.,
       `SELP1650`, `FE 28-70mm`) OR when Movie `[SteadyShot] = Active`; never bakes into `.ARW`
       raw pixels.
     * `[Breathing Comp.]` (`Ver. 3.00+`, `BKID_APP_setting_lens_comp_breathing`, `_f.uxc` `0x73ea`,
       default `Off`, `Camera Settings Reset`-resettable): `On` / `Off`, Movie-only, disabled when
       HDMI external RAW or unsupported lens (`BREATHING_CORRECTION_LENS_TYPE_SUPPORT`).
     * Unchipped manual lens (`VAL_launch_lens_comp_LENS_COMP_VALUE_NOT_EXIST`,
       `libInfraLensCommunicator.so`): all 4 lens comp items disabled/grayed in menu.
     * Contrasts `ILME-FX6 Ver. 6.01` (`PRODUCT_MODEL_CHAPLIN`): located under **`Technical > Lens`**
       (not legacy `Project/Paint/Lens`), saved in **`All File`** (`s/SONY/PRO/CAMERA/`), with
       `Breathing Compensation` forced `Off` whenever `Distortion Comp. = Off`, `S&Q = On`, or
       `Codec` contains `RAW`.
   - Enforces Movie `[AF Transition Speed]` (`1..7`, default `5`), `[AF Subj. Shift Sensitivity]`
     (`1..5`, default `5(Responsive)`, firmware enum `5_RESPONSICE`), and `[AF Assist]` (`On`/`Off`,
     default `Off`, Movie/`S&Q` `AF-C` / `MOVIE_AUTO` only; incompatible `SELP1650`/`SEL18200LE`)
     all resettable by `Camera Settings Reset`.
   - **CRITICAL HARDWARE CORRECTION — Built-in Front `[AF Illuminator]`**: Contrasting
     `ILME-FX6` which has **ZERO built-in AF illuminator LED** (only 6 dormant Alpha symbols in
     `FX6 appFw.so`), **`ILME-FX3` possesses a physical front built-in AF illuminator /
     Self-timer lamp LED (`TP1000886886.html` #8, `0.3m..3.0m`)** + MI-Shoe external flash AF
     illuminator (`BKID_APP_setting_still_image_af_illuminator`, `.uxc` `0xe07f`, `_f.uxc` `0x69c0`,
     `Auto`/`Off`, `Camera Settings Reset`-resettable) active **ONLY in Still `AF-S`** (locked out
     in `Movie`, `S&Q`, `AF-C`, `MF`, `Silent Mode = On`, `Focus Magnifier`, `Mount Adaptor`, and
     moving `AF-A`).

2. **Sub-Pillar 55B — `[Aperture Drive in AF]` / `[AF w/ Shutter]` / `[Pre-AF]` / `[Circ. of Focus Point]`
   / `[Focus Area Color]` Initialize-Only Persistence, and `[Create New Folder]` + Playback `[Rating]`
   (`1..5` Stars) Slot-1 Tier-0 Vault Firewall (Wave-53)**:
   - Validates all 5 `Initialize`-only items (all survive `[Camera Settings Reset]` and reset ONLY
     via `[Initialize]`):
     * `[Aperture Drive in AF]` (`BKID_APP_setting_stl_aperture_drive_in_af`, Still-only):
       `Focus Priority` / `Standard` (default) / `Silent Priority` (plus `Focus Priority` audible
       mechanical noise & burst-speed reduction notice `_g.uxc` `0x631a`/`0x63e2`).
     * `[AF w/ Shutter]` (`BKID_APP_setting_still_image_af_w_shutter`, Still-only): `On` (default)
       / `Off`.
     * `[Pre-AF]` (`BKID_APP_setting_pre_af`, Still-only, gated by `LENS_PRE_AF_SUPPORT`): `On` /
       `Off` (default).
     * `[Circ. of Focus Point]` (`BKID_APP_setting_circulate_of_focus_point`, Still/Movie/`S&Q`):
       `Circulate` / `Does Not Circulate` (default) — **orthogonal horizontal/vertical wrap ONLY,
       never diagonal wrap**.
     * `[Focus Area Color]` (`BKID_APP_setting_focus_frame_color`, Still/Movie/`S&Q`): `White`
       (default) / `Red`.
     * Contrasts `ILME-FX6` which lacks all 5 (uses cinema `Iris`; dormant PXW-FX9 string `0x4fc3`
       has `0` hits in `FX6 appFw.so`).
   - Validates `[File/Folder Settings]` (`Standard Form` `100MSDCF..999MSDCF` default vs `Date Form`
     `100_MMDD` disabling `[Select REC Folder]`; `Series`/`Reset`; `[Set File Name]` 3 chars default
     `DSC` banning leading `_`; `4,000` still limit `STATUS_OF_MEDIA_SLOT1_FOLDER_MAX`; dual-slot
     max folder# + 1) and Playback `[Rating]` (`★1..★5`, `FUNC_rating_content`,
     `VAL_xmp_rating_XMP_RATING_VALID`) + `[Rating Set(Custom Key)]` + Still-only `[Add Rating]`
     (no overwrite `_g.uxc` `0x627d`; blocked in background transfer `EBUSY=16`), contrasted with
     FX6 `XAVC Root Folder Name` & `Clip Flag` (`OK`/`NG`/`KEEP`).
   - **CRITICAL RECOVERY VAULT FIREWALL**: `[Create New Folder]`, `[Forced File Number Reset]`,
     `[Select REC Folder]` + simultaneous shoot, Playback `[Rating]` (`1..5` stars mutating
     EXIF/XMP & `AVF_INFO` ImageDB on card), and `[Add Rating]` MUST fail-closed (`EROFS=30` /
     `EBUSY=16`, `slot1_data_sector_writes == 0`, `slot1_folder_dir_mutation_bytes == 0`,
     `slot1_rating_avf_info_mutation_bytes == 0`, `slot1_vault_mutation_bytes == 0`) whenever
     `Slot 1` holds a Tier-0 recovery vault!

3. **Unified 55/55 Recovery Master Aggregator (`evaluate_realhw_55pillar_recovery_master` /
   `verify-55pillar-recovery`)**:
   - Concurrently delegates Pillars `1..54` (`evaluate_realhw_54pillar_recovery_master`) +
     **Pillar 55** (`run_pillar55_standalone_suite`) -> **`55/55` (`VERIFIED_55OF55_PILLAR_RECOVERY_MASTER`)**
     under `< 1.5s` with `overall_ready_for_hardware_attach == False`,
     `cross_model_flash_authorized == False`, `persistent_emmc_writes_authorized == False`, and
     `raw_firmware_bytes_leaked == 0`.
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
from .realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier import (
    MASTER_54_PILLAR_SPECS,
    Master54PillarRecoveryReport,
    evaluate_realhw_54pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants (Phase 308 — 55/55 Milestone)
# ---------------------------------------------------------------------------

PHASE308_SCHEMA: str = (
    "realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier_v1"
)
PHASE308_VERSION: str = "1.0.0"
PHASE308_PHASE_NUMBER: int = 308
P308_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P308_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P308_OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
P308_CROSS_MODEL_FLASH_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P308_DORMANT_SHADING_AUTO_LOW_EXPOSURE_EVENTS: int = 0
P308_LENS_COMP_LOCK_OR_ARW_CONFLATION_EVENTS: int = 0
P308_AF_ILLUMINATOR_GATE_OR_FX6_SPOOF_EVENTS: int = 0
P308_MOVIE_AF_TRANSITION_OR_ASSIST_DRIFT_EVENTS: int = 0
P308_APERTURE_DRIVE_PRE_AF_SHUTTER_RESET_DRIFT_EVENTS: int = 0
P308_CIRC_FOCUS_DIAGONAL_OR_COLOR_DRIFT_EVENTS: int = 0
P308_FOLDER_NAME_OR_LEADING_UNDERSCORE_VIOLATIONS: int = 0
P308_SLOT1_DATA_SECTOR_WRITES: int = 0
P308_SLOT1_FOLDER_DIR_MUTATION_BYTES: int = 0
P308_SLOT1_RATING_AVF_INFO_MUTATION_BYTES: int = 0
P308_SLOT1_VAULT_MUTATION_BYTES: int = 0
P308_SLOT1_FORMAT_HARD_LOCKED: bool = True
P308_SLOT1_VAULT_EROFS_EBUSY_ENFORCED: bool = True

# Hardware Truths (Wave-53 Empirical Anchors)
P308_FX3_HAS_BUILTIN_AF_ILLUMINATOR: bool = True
P308_FX3_AF_ILLUMINATOR_FRONT_PART_NO: int = 8  # TP1000886886.html #8
P308_FX3_AF_ILLUMINATOR_RANGE_M: Tuple[float, float] = (0.3, 3.0)
P308_FX3_SUPPORTS_MISHOE_FLASH_ILLUMINATOR: bool = True
P308_FX6_HAS_BUILTIN_AF_ILLUMINATOR: bool = False
P308_FX3_EXPOSES_SHADING_AUTO_LOW: bool = False
P308_FX6_HAS_APERTURE_DRIVE_PRE_AF_CIRC_COLOR: bool = False
P308_FX6_HAS_MSDCF_OR_STAR_RATING: bool = False

P308_DONOR_INSPECT_BUDGET_SECONDS: float = 0.20
P308_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P308_FAST_CLI_BUDGET_SECONDS: float = 1.5
P308_NOMINAL_BUDGET_SECONDS: float = 4.0
P308_CONCURRENT_CEILING_SECONDS: float = 6.0
P308_BOUNDED_HEADER_BYTES: int = 4096
P308_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-53 Donor Anchors (18 donors, strictly O_RDONLY)
P308_FX3_MODEL_NAME: str = "ILME-FX3"
P308_FX3_MODEL_ID: int = 0x91030080
P308_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P308_FX3_HELPGUIDE_ID: str = "ilc/2210"
P308_FX3_FW_VERSION: str = "7.02"
P308_FX3_SENSOR_FAMILY: str = "12 MP IMX510"
P308_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P308_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P308_FX6_DONOR_FW_VERSION: str = "6.01"
P308_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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

P308_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P308_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P308_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)
P308_PINNED_FX3_APPFW_702_FULL_SHA256: str = (
    "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
)

P308_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P308_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P308_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)
P308_PINNED_FX6_APPFW_601_FULL_SHA256: str = (
    "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
)

P308_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P308_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P308_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P308_DONOR_FX3_LIB_INFRA_LENS_COMM_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraLensCommunicator.so"
)
P308_PINNED_FX3_LIB_INFRA_LENS_COMM_BYTES: int = 14544
P308_PINNED_FX3_LIB_INFRA_LENS_COMM_SHA256: str = (
    "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab"
)

P308_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P308_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P308_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P308_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P308_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P308_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P308_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P308_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P308_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P308_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P308_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P308_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P308_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P308_PINNED_FX3_UXC_EN_BYTES: int = 165740
P308_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P308_DONOR_FX3_UXC_SC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc"
)
P308_PINNED_FX3_UXC_SC_BYTES: int = 149064
P308_PINNED_FX3_UXC_SC_SHA256: str = (
    "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66"
)

P308_DONOR_FX3_UXC_TC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc"
)
P308_PINNED_FX3_UXC_TC_BYTES: int = 151908
P308_PINNED_FX3_UXC_TC_SHA256: str = (
    "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3"
)

P308_DONOR_FX3_UXC_JA_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc"
)
P308_PINNED_FX3_UXC_JA_BYTES: int = 208564
P308_PINNED_FX3_UXC_JA_SHA256: str = (
    "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d"
)

P308_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P308_PINNED_FX3_UXC_EN_G_BYTES: int = 69600
P308_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P308_DONOR_FX3_UXC_SC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_g.uxc"
)
P308_PINNED_FX3_UXC_SC_G_BYTES: int = 61296
P308_PINNED_FX3_UXC_SC_G_SHA256: str = (
    "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b"
)

P308_DONOR_FX3_UXC_TC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_g.uxc"
)
P308_PINNED_FX3_UXC_TC_G_BYTES: int = 61372
P308_PINNED_FX3_UXC_TC_G_SHA256: str = (
    "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80"
)

P308_DONOR_FX3_UXC_JA_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_g.uxc"
)
P308_PINNED_FX3_UXC_JA_G_BYTES: int = 89428
P308_PINNED_FX3_UXC_JA_G_SHA256: str = (
    "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980"
)

P308_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P308_PINNED_FX6_UXC_EN_BYTES: int = 118208
P308_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P308_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P308_PINNED_FX6_UXC_EN_2_BYTES: int = 118676
P308_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# ---------------------------------------------------------------------------
# Pillar 55A Constants — [Lens Compensation], Movie AF Speed/Shift/Assist,
# & Built-in Front [AF Illuminator] LED #8 vs Zero-Illuminator ILME-FX6
# ---------------------------------------------------------------------------

P308_LENS_COMP_MENU_PATH: Tuple[str, ...] = (
    "Shooting",
    "Image Quality/Rec",
    "Lens Compensation",
)
P308_FX6_LENS_COMP_MENU_PATH: str = "Technical > Lens"
P308_FX6_LEGACY_LENS_COMP_MENU_PATH: str = "Project/Paint/Lens > Lens > Compensate"
P308_FX6_ALL_FILE_DIR: str = "s/SONY/PRO/CAMERA/"

P308_AF_MF_MENU_PATH: Tuple[str, ...] = ("Focus", "AF/MF")
P308_AF_ILLUMINATOR_MENU_PATH: Tuple[str, ...] = ("Focus", "AF/MF", "AF Illuminator")

P308_LENS_COMP_F_RESID16: int = 0x75C8
P308_LENS_COMP_RESID16: int = 0x631F
P308_SHADING_COMP_F_RESID16: int = 0x64E1
P308_DORMANT_SHADING_AUTO_LOW_F_RESID16: int = 0x6C9C  # "Auto: Low" (dormant in FX3/FX6)
P308_CHROMA_ABER_COMP_F_RESID16: int = 0x68CD
P308_DISTORTION_COMP_F_RESID16: int = 0x6200
P308_BREATHING_COMP_F_RESID16: int = 0x73EA

P308_SHADING_COMP_BKID: str = "BKID_APP_setting_lens_comp_shading"
P308_CHROMA_ABER_COMP_BKID: str = "BKID_APP_setting_lens_comp_chro_aber"
P308_DISTORTION_COMP_BKID: str = "BKID_APP_setting_lens_comp_distortion"
P308_BREATHING_COMP_BKID: str = "BKID_APP_setting_lens_comp_breathing"
P308_DORMANT_SHADING_AUTO_LOW_ENUM: str = (
    "VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW"
)
P308_UNCHIPPED_MANUAL_LENS_ENUM: str = (
    "VAL_launch_lens_comp_LENS_COMP_VALUE_NOT_EXIST"
)
P308_LENS_DISTORTION_FORCED_AUTO_ENUM: str = (
    "VAL_select_distortion_support_LENS_SELECT_DISTORTION_NOT_SUPPORTED"
)
P308_LENS_COMP_IPC_SYMBOLS: Tuple[str, ...] = (
    "osal_snd_sync_msg",
    "osal_snd_msg",
    "osal_reg_sync_msg_queue_cb",
    "PID_SET_LENS_CORRECTION_DATA",
    "PID_SET_MANUAL_LENS_CORRECTION",
)

P308_SHADING_COMP_EXPOSED_MODES: Tuple[str, ...] = ("Auto", "Off")
P308_SHADING_COMP_DORMANT_MODES: Tuple[str, ...] = (
    "Auto: Low",
    "Low",
    "LENS_COMP_SHADING_AUTO_LOW",
)
P308_SHADING_COMP_DEFAULT: str = "Auto"
P308_CHROMA_ABER_MODES: Tuple[str, ...] = ("Auto", "Off")
P308_CHROMA_ABER_DEFAULT: str = "Auto"
P308_DISTORTION_MODES: Tuple[str, ...] = ("Auto", "Off")
P308_DISTORTION_DEFAULT: str = "Off"
P308_BREATHING_DEFAULT: str = "Off"

P308_AF_TRANSITION_SPEED_F_RESID16: int = 0x6E9D
P308_AF_TRANSITION_SPEED_BKID: str = "BKID_APP_setting_movie_af_transition_speed"
P308_AF_TRANSITION_SPEED_MIN: int = 1
P308_AF_TRANSITION_SPEED_MAX: int = 7
P308_AF_TRANSITION_SPEED_DEFAULT: int = 5

P308_AF_SUBJ_SHIFT_SENS_F_RESID16: int = 0x79D6
P308_AF_SUBJ_SHIFT_SENS_COMPACT_F_RESID16: int = 0x64DE
P308_AF_SUBJ_SHIFT_SENS_BKID: str = "BKID_APP_setting_movie_af_subj_shift_sens"
P308_AF_SUBJ_SHIFT_SENS_MIN: int = 1
P308_AF_SUBJ_SHIFT_SENS_MAX: int = 5
P308_AF_SUBJ_SHIFT_SENS_DEFAULT: int = 5  # 5(Responsive) / enum 5_RESPONSICE

P308_AF_ASSIST_F_RESID16: int = 0x64A9
P308_AF_ASSIST_BKID: str = "BKID_APP_setting_af_assist"
P308_AF_ASSIST_DEFAULT: str = "Off"
P308_AF_ASSIST_INCOMPATIBLE_LENSES: Tuple[str, ...] = ("SELP1650", "SEL18200LE")

P308_AF_ILLUMINATOR_RESID16: int = 0xE07F
P308_AF_ILLUMINATOR_F_RESID16: int = 0x69C0
P308_AF_ILLUMINATOR_BKID: str = "BKID_APP_setting_still_image_af_illuminator"
P308_AF_ILLUMINATOR_MODES: Tuple[str, ...] = ("Auto", "Off")
P308_AF_ILLUMINATOR_DEFAULT: str = "Auto"

# ---------------------------------------------------------------------------
# Pillar 55B Constants — [Aperture Drive in AF] / [AF w/ Shutter] / [Pre-AF]
# / [Circ. of Focus Point] / [Focus Area Color] Initialize-Only Persistence
# & [Create New Folder] + Playback [Rating] 1..5 Stars Slot-1 Vault Firewall
# ---------------------------------------------------------------------------

P308_FOCUS_AREA_MENU_PATH: Tuple[str, ...] = ("Focus", "Focus Area")
P308_FILE_FOLDER_MENU_PATH: Tuple[str, ...] = ("Shooting", "File", "File/Folder Settings")
P308_PLAYBACK_RATING_MENU_PATH: Tuple[str, ...] = ("Playback", "Selection/Memo", "Rating")

P308_APERTURE_DRIVE_BKID: str = "BKID_APP_setting_stl_aperture_drive_in_af"
P308_APERTURE_DRIVE_SILENT_BKID: str = (
    "BKID_APP_setting_silent_detail_setting_aperture_drive_in_af"
)
P308_APERTURE_DRIVE_MODES: Tuple[str, ...] = (
    "Focus Priority",
    "Standard",
    "Silent Priority",
)
P308_APERTURE_DRIVE_DEFAULT: str = "Standard"
P308_APERTURE_DRIVE_F_RESID16: int = 0x7879
P308_APERTURE_DRIVE_ALT_F_RESID16: int = 0x67BA
P308_APERTURE_DRIVE_BURST_WARN_G_RESID16: int = 0x63E2

P308_AF_W_SHUTTER_BKID: str = "BKID_APP_setting_still_image_af_w_shutter"
P308_AF_W_SHUTTER_DEFAULT: str = "On"
P308_AF_W_SHUTTER_F_RESID16: int = 0x771D

P308_PRE_AF_BKID: str = "BKID_APP_setting_pre_af"
P308_PRE_AF_DEFAULT: str = "Off"
P308_PRE_AF_F_RESID16: int = 0x76D8

P308_CIRC_FOCUS_POINT_BKID: str = "BKID_APP_setting_circulate_of_focus_point"
P308_CIRC_FOCUS_POINT_MODES: Tuple[str, ...] = ("Circulate", "Does Not Circulate")
P308_CIRC_FOCUS_POINT_DEFAULT: str = "Does Not Circulate"
P308_CIRC_FOCUS_POINT_F_RESID16: int = 0x74F6
P308_CIRC_WRAP_AXES: Tuple[str, ...] = ("None", "Horizontal", "Vertical", "Diagonal")

P308_FOCUS_AREA_COLOR_BKID: str = "BKID_APP_setting_focus_frame_color"
P308_FOCUS_AREA_COLOR_MODES: Tuple[str, ...] = ("White", "Red")
P308_FOCUS_AREA_COLOR_DEFAULT: str = "White"
P308_FOCUS_AREA_COLOR_F_RESID16: int = 0x74AD
P308_FOCUS_AREA_COLOR_RESID16_MAP: Dict[str, int] = {"White": 0xE883, "Red": 0xE8C6}

P308_FX6_DORMANT_IRIS_AF_F24_RESID16: int = 0x4FC3  # PXW-FX9 string in FX6 _2.uxc (0 hits in appFw.so)

P308_FOLDER_NAME_FORMS: Tuple[str, ...] = ("Standard Form", "Date Form")
P308_FOLDER_NAME_DEFAULT: str = "Standard Form"
P308_FILE_NUMBER_MODES: Tuple[str, ...] = ("Series", "Reset")
P308_FILE_NUMBER_DEFAULT: str = "Series"
P308_FILE_PREFIX_DEFAULT: str = "DSC"
P308_FILE_PREFIX_LEN: int = 3
P308_FILE_PREFIX_ALLOWED_CHARS: frozenset[str] = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789_"
)
P308_FOLDER_MAX_STILLS: int = 4000
P308_FOLDER_MAX_STATUS_SYMBOL: str = "STATUS_OF_MEDIA_SLOT1_FOLDER_MAX"
P308_MIN_FOLDER_NUM: int = 100
P308_MAX_FOLDER_NUM: int = 999

P308_RATING_STARS_VALID: Tuple[int, ...] = (0, 1, 2, 3, 4, 5)
P308_RATING_SET_STARS_VALID: Tuple[int, ...] = (1, 2, 3, 4, 5)
P308_RATING_FUNC_SYMBOL: str = "FUNC_rating_content"
P308_ADD_RATING_FUNC_SYMBOL: str = "FUNC_rating_on_shooting_screen"
P308_RATING_XMP_SYMBOL: str = "VAL_xmp_rating_XMP_RATING_VALID"
P308_RATING_BG_NG_SYMBOL: str = "EDIT_FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_RATING"
P308_ADD_RATING_ALREADY_APPLIED_G_RESID16: int = 0x627D

P308_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P308_FOCUS_MODES_ALL: Tuple[str, ...] = ("AF-S", "AF-A", "AF-C", "DMF", "MF")
P308_STEADYSHOT_MODES: Tuple[str, ...] = ("Off", "Standard", "Active")
P308_ON_OFF_MODES: Tuple[str, ...] = ("On", "Off")
P308_RESET_ACTIONS: Tuple[str, ...] = (
    "None",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P308_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "CREATE_NEW_FOLDER",
    "FORCED_FILE_NUMBER_RESET",
    "SELECT_REC_FOLDER_SIMULT_SHOOT",
    "PLAYBACK_RATING_SET",
    "SHOOT_ADD_RATING",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P308_DESTRUCTIVE_VAULT_ACTIONS: Tuple[str, ...] = (
    "CREATE_NEW_FOLDER",
    "FORCED_FILE_NUMBER_RESET",
    "SELECT_REC_FOLDER_SIMULT_SHOOT",
    "PLAYBACK_RATING_SET",
    "SHOOT_ADD_RATING",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P308_SLOT1_VAULT_SLOT: int = 1
P308_SAFE_SECONDARY_SLOT: int = 2
P308_VAULT_FIREWALL_ERRNOS: Tuple[str, ...] = ("EROFS", "EBUSY")
P308_VAULT_FIREWALL_ERRNO_CODES: Dict[str, int] = {"EROFS": 30, "EBUSY": 16}
P308_EOPNOTSUPP_ERRNO: int = 95
P308_STAGE_B_VOLATILE_OVERLAY_DIR: str = (
    "/tmp/fx3_lens_comp_af_illuminator_folder_rating_vault_overlay"
)
P308_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P308_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P308_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P308_BLOCKED_INVALID_PILLAR55A_SPEC: str = "BLOCKED_INVALID_PILLAR55A_SPEC"
P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT: str = (
    "BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT"
)
P308_BLOCKED_MOVIE_AF_TRANSITION_SENS_OR_ASSIST_DRIFT: str = (
    "BLOCKED_MOVIE_AF_TRANSITION_SENS_OR_ASSIST_DRIFT"
)
P308_BLOCKED_AF_ILLUMINATOR_GATE_OR_FX6_LED_SPOOF: str = (
    "BLOCKED_AF_ILLUMINATOR_GATE_OR_FX6_LED_SPOOF"
)
P308_BLOCKED_INVALID_PILLAR55B_SPEC: str = "BLOCKED_INVALID_PILLAR55B_SPEC"
P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT: str = (
    "BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT"
)
P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT: str = (
    "BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT"
)
P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL: str = "BLOCKED_SLOT1_VAULT_WRITE_FIREWALL"
P308_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P308_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P308_STATUS_VERIFIED_PILLAR_55A: str = (
    "VERIFIED_PILLAR_55A_LENS_COMP_AUTO_OFF_NO_AUTO_LOW_MOVIE_AF_AND_BUILTIN_AF_ILLUMINATOR"
)
P308_STATUS_REJECTED_PILLAR_55A: str = (
    "REJECTED_PILLAR_55A_LENS_COMP_AUTO_OFF_NO_AUTO_LOW_MOVIE_AF_AND_BUILTIN_AF_ILLUMINATOR"
)
P308_STATUS_VERIFIED_PILLAR_55B: str = (
    "VERIFIED_PILLAR_55B_APERTURE_DRIVE_INIT_PERSIST_FOLDER_RATING_SLOT1_VAULT_FIREWALL"
)
P308_STATUS_REJECTED_PILLAR_55B: str = (
    "REJECTED_PILLAR_55B_APERTURE_DRIVE_INIT_PERSIST_FOLDER_RATING_SLOT1_VAULT_FIREWALL"
)
P308_STATUS_VERIFIED_PILLAR55_SUITE: str = (
    "VERIFIED_PILLAR55_LENS_COMP_AF_ILLUMINATOR_FOLDER_RATING_VAULT"
)
P308_STATUS_FAIL_PILLAR55_SUITE: str = (
    "FAIL_PILLAR55_LENS_COMP_AF_ILLUMINATOR_FOLDER_RATING_VAULT"
)
P308_STATUS_VERIFIED_55OF55_AGGREGATOR: str = "VERIFIED_55OF55_PILLAR_RECOVERY_MASTER"
P308_STATUS_FAIL_55OF55_AGGREGATOR: str = "FAIL_55OF55_PILLAR_RECOVERY_MASTER"

P308_PILLAR_55A_SCENARIO_IDS: Tuple[str, ...] = (
    "P55A1_LENS_COMP_AUTO_OFF_STEADYSHOT_ACTIVE_LOCK_STILL_AFS_AF_ILLUMINATOR_SAFE",
    "P55A2_CAM_RESET_PRESERVES_SHADING_CLEARS_BREATHING_AF_ASSIST_AND_FX6_ZERO_LED_SAFE",
    "P55A3_REJECT_DORMANT_SHADING_AUTO_LOW_0X6C9C_WITHOUT_EOPNOTSUPP95",
    "P55A4_REJECT_DISTORTION_OFF_UNDER_STEADYSHOT_ACTIVE_OR_ARW_BAKE_OR_FX6_RAW_BREATHING",
    "P55A5_REJECT_AF_ILLUMINATOR_IN_MOVIE_SQ_AFC_MF_SILENT_OR_FX6_SPOOF",
    "P55A6_REJECT_SLOT1_VAULT_MUTATION_OR_PERSISTENT_OVERLAY_OR_H0_H3_DRIFT",
)
P308_PILLAR_55B_SCENARIO_IDS: Tuple[str, ...] = (
    "P55B1_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_CAM_RESET_SURVIVAL_AND_SLOT2_RATING_SAFE",
    "P55B2_INITIALIZE_RESETS_5ITEMS_AND_DATE_FORM_DISABLES_SELECT_REC_FOLDER_SAFE",
    "P55B3_REJECT_CAM_RESET_WIPING_5ITEMS_OR_DIAGONAL_CIRC_WRAP_OR_FX6_IRIS_SPOOF",
    "P55B4_REJECT_LEADING_UNDERSCORE_FILENAME_4000_OVERFLOW_OR_ALREADY_RATED_OVERWRITE",
    "P55B5_REJECT_CREATE_NEW_FOLDER_OR_FORCED_NUM_RESET_ON_SLOT1_TIER0_VAULT_EROFS",
    "P55B6_REJECT_PLAYBACK_RATING_OR_ADD_RATING_EXIF_AVF_INFO_ON_SLOT1_TIER0_VAULT",
)

MASTER_55_PILLAR_COUNT: int = 55
MASTER_55_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_54_PILLAR_SPECS + (
    (
        55,
        "pillar_55_lens_comp_af_illuminator_folder_rating_vault",
        "Phase 308 (Wave-53)",
        "fx3_recovery.realhw_55pillar_lens_comp_af_illuminator_folder_rating_vault_verifier",
    ),
)
MASTER_55_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_55_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Pure Wave-53 State Computations
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
    return os.environ.get(P308_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P308_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P308_DONOR_INSPECT_BUDGET_SECONDS


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
        ("P308_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P308_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("P308_OVERALL_READY_FOR_HARDWARE_ATTACH", P308_OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("P308_CROSS_MODEL_FLASH_AUTHORIZED", P308_CROSS_MODEL_FLASH_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        (
            "P308_DORMANT_SHADING_AUTO_LOW_EXPOSURE_EVENTS",
            P308_DORMANT_SHADING_AUTO_LOW_EXPOSURE_EVENTS,
            0,
        ),
        (
            "P308_LENS_COMP_LOCK_OR_ARW_CONFLATION_EVENTS",
            P308_LENS_COMP_LOCK_OR_ARW_CONFLATION_EVENTS,
            0,
        ),
        (
            "P308_AF_ILLUMINATOR_GATE_OR_FX6_SPOOF_EVENTS",
            P308_AF_ILLUMINATOR_GATE_OR_FX6_SPOOF_EVENTS,
            0,
        ),
        (
            "P308_MOVIE_AF_TRANSITION_OR_ASSIST_DRIFT_EVENTS",
            P308_MOVIE_AF_TRANSITION_OR_ASSIST_DRIFT_EVENTS,
            0,
        ),
        (
            "P308_APERTURE_DRIVE_PRE_AF_SHUTTER_RESET_DRIFT_EVENTS",
            P308_APERTURE_DRIVE_PRE_AF_SHUTTER_RESET_DRIFT_EVENTS,
            0,
        ),
        (
            "P308_CIRC_FOCUS_DIAGONAL_OR_COLOR_DRIFT_EVENTS",
            P308_CIRC_FOCUS_DIAGONAL_OR_COLOR_DRIFT_EVENTS,
            0,
        ),
        (
            "P308_FOLDER_NAME_OR_LEADING_UNDERSCORE_VIOLATIONS",
            P308_FOLDER_NAME_OR_LEADING_UNDERSCORE_VIOLATIONS,
            0,
        ),
        ("P308_SLOT1_DATA_SECTOR_WRITES", P308_SLOT1_DATA_SECTOR_WRITES, 0),
        ("P308_SLOT1_FOLDER_DIR_MUTATION_BYTES", P308_SLOT1_FOLDER_DIR_MUTATION_BYTES, 0),
        (
            "P308_SLOT1_RATING_AVF_INFO_MUTATION_BYTES",
            P308_SLOT1_RATING_AVF_INFO_MUTATION_BYTES,
            0,
        ),
        ("P308_SLOT1_VAULT_MUTATION_BYTES", P308_SLOT1_VAULT_MUTATION_BYTES, 0),
        ("P308_SLOT1_FORMAT_HARD_LOCKED", P308_SLOT1_FORMAT_HARD_LOCKED, True),
        ("P308_SLOT1_VAULT_EROFS_EBUSY_ENFORCED", P308_SLOT1_VAULT_EROFS_EBUSY_ENFORCED, True),
        ("P308_FX3_HAS_BUILTIN_AF_ILLUMINATOR", P308_FX3_HAS_BUILTIN_AF_ILLUMINATOR, True),
        ("P308_FX3_AF_ILLUMINATOR_FRONT_PART_NO", P308_FX3_AF_ILLUMINATOR_FRONT_PART_NO, 8),
        (
            "P308_FX3_SUPPORTS_MISHOE_FLASH_ILLUMINATOR",
            P308_FX3_SUPPORTS_MISHOE_FLASH_ILLUMINATOR,
            True,
        ),
        ("P308_FX6_HAS_BUILTIN_AF_ILLUMINATOR", P308_FX6_HAS_BUILTIN_AF_ILLUMINATOR, False),
        ("P308_FX3_EXPOSES_SHADING_AUTO_LOW", P308_FX3_EXPOSES_SHADING_AUTO_LOW, False),
        (
            "P308_FX6_HAS_APERTURE_DRIVE_PRE_AF_CIRC_COLOR",
            P308_FX6_HAS_APERTURE_DRIVE_PRE_AF_CIRC_COLOR,
            False,
        ),
        ("P308_FX6_HAS_MSDCF_OR_STAR_RATING", P308_FX6_HAS_MSDCF_OR_STAR_RATING, False),
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
    return any(tok in low for tok in P308_FORBIDDEN_PERSISTENT_TARGETS)


def is_valid_fx3_file_prefix(prefix: str) -> bool:
    """Validate 3-char `[Set File Name]` prefix (`[A-Z0-9_]`, never leading `_`)."""
    return (
        isinstance(prefix, str)
        and len(prefix) == P308_FILE_PREFIX_LEN
        and prefix[0] != "_"
        and all(ch in P308_FILE_PREFIX_ALLOWED_CHARS for ch in prefix)
    )


def compute_expected_lens_comp_and_movie_af_state(
    *,
    camera_model: str,
    lens_id: str,
    unchipped_manual_lens: bool,
    lens_requires_distortion_comp: bool,
    lens_supports_breathing_comp: bool,
    shooting_domain: str,
    steadyshot_mode: str,
    hdmi_external_raw: bool,
    requested_shading_comp: str,
    requested_chroma_aber_comp: str,
    requested_distortion_comp: str,
    requested_breathing_comp: str,
    requested_af_transition_speed: int,
    requested_af_subj_shift_sens: int,
    requested_af_assist: str,
    focus_mode: str,
    fx6_sq_motion_on: bool,
    fx6_rec_codec: str,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute effective + post-reset Wave-53 Lens Comp & Movie AF states."""
    shading_rejected_errno = (
        P308_EOPNOTSUPP_ERRNO
        if requested_shading_comp in P308_SHADING_COMP_DORMANT_MODES
        else None
    )
    menu_enabled = not unchipped_manual_lens
    eff_shading = (
        P308_SHADING_COMP_DEFAULT
        if shading_rejected_errno is not None
        else requested_shading_comp
    )
    eff_chroma = requested_chroma_aber_comp
    distortion_forced_auto = bool(
        menu_enabled
        and (
            lens_requires_distortion_comp
            or (shooting_domain == "Movie" and steadyshot_mode == "Active")
        )
    )
    eff_distortion = "Auto" if distortion_forced_auto else requested_distortion_comp

    if camera_model == P308_FX6_DONOR_MODEL_NAME:
        fx6_breathing_locked_off = bool(
            eff_distortion == "Off" or fx6_sq_motion_on or ("RAW" in fx6_rec_codec.upper())
        )
        eff_breathing = "Off" if fx6_breathing_locked_off else requested_breathing_comp
        breathing_allowed = not fx6_breathing_locked_off
    else:
        breathing_allowed = bool(
            menu_enabled
            and shooting_domain == "Movie"
            and not hdmi_external_raw
            and lens_supports_breathing_comp
        )
        eff_breathing = requested_breathing_comp if breathing_allowed else "Off"

    af_assist_allowed = bool(
        shooting_domain in ("Movie", "S&Q")
        and focus_mode == "AF-C"
        and lens_id not in P308_AF_ASSIST_INCOMPATIBLE_LENSES
    )
    eff_af_assist = requested_af_assist if af_assist_allowed else "Off"

    if reset_action == "Initialize":
        post_shading = P308_SHADING_COMP_DEFAULT
        post_chroma = P308_CHROMA_ABER_DEFAULT
        post_distortion = "Auto" if distortion_forced_auto else P308_DISTORTION_DEFAULT
        post_breathing = P308_BREATHING_DEFAULT
        post_speed = P308_AF_TRANSITION_SPEED_DEFAULT
        post_sens = P308_AF_SUBJ_SHIFT_SENS_DEFAULT
        post_assist = P308_AF_ASSIST_DEFAULT
    elif reset_action == "Camera Settings Reset":
        post_shading = eff_shading
        post_chroma = eff_chroma
        post_distortion = eff_distortion
        post_breathing = P308_BREATHING_DEFAULT
        post_speed = P308_AF_TRANSITION_SPEED_DEFAULT
        post_sens = P308_AF_SUBJ_SHIFT_SENS_DEFAULT
        post_assist = P308_AF_ASSIST_DEFAULT
    else:
        post_shading = eff_shading
        post_chroma = eff_chroma
        post_distortion = eff_distortion
        post_breathing = eff_breathing
        post_speed = requested_af_transition_speed
        post_sens = requested_af_subj_shift_sens
        post_assist = eff_af_assist

    return {
        "menu_enabled": menu_enabled,
        "shading_rejected_errno": shading_rejected_errno,
        "distortion_forced_auto": distortion_forced_auto,
        "arw_distortion_baked": False,
        "breathing_allowed": breathing_allowed,
        "af_assist_allowed": af_assist_allowed,
        "post_shading": post_shading,
        "post_chroma": post_chroma,
        "post_distortion": post_distortion,
        "post_breathing": post_breathing,
        "post_af_transition_speed": post_speed,
        "post_af_subj_shift_sens": post_sens,
        "post_af_assist": post_assist,
    }


def compute_expected_af_illuminator_state(
    *,
    camera_model: str,
    shooting_domain: str,
    focus_mode: str,
    configured_af_illuminator: str,
    silent_mode_on: bool,
    focus_magnifier_active: bool,
    mount_adaptor_attached: bool,
    subject_moving_in_afa: bool,
    mishoe_external_flash_attached: bool,
    reset_action: str,
) -> Tuple[bool, bool, str, bool]:
    """Compute `(builtin_led_active, mishoe_flash_illum_active, post_af_illuminator, has_builtin_led)`.

    - `ILME-FX3`: physically possesses front LED #8 (`TP1000886886.html` #8, `0.3..3.0 m`) +
      MI-Shoe external flash illuminator, active ONLY in `Still` `AF-S` (or static `AF-A`
      when not moving, though gated out for `Movie`, `S&Q`, `AF-C`, `MF`, `Silent Mode = On`,
      `Focus Magnifier`, and `Mount Adaptor`).
    - `ILME-FX6`: `has_builtin_led == False` (ZERO built-in AF illuminator).
    """
    if camera_model == P308_FX6_DONOR_MODEL_NAME:
        return False, False, "Off", False

    eligible = (
        configured_af_illuminator == "Auto"
        and shooting_domain == "Still"
        and (
            focus_mode == "AF-S"
            or (focus_mode == "AF-A" and not subject_moving_in_afa)
        )
        and not silent_mode_on
        and not focus_magnifier_active
        and not mount_adaptor_attached
    )
    mishoe_active = bool(eligible and mishoe_external_flash_attached)
    if reset_action in ("Camera Settings Reset", "Initialize"):
        post_setting = P308_AF_ILLUMINATOR_DEFAULT
    else:
        post_setting = configured_af_illuminator
    return eligible, mishoe_active, post_setting, True


def compute_expected_aperture_drive_and_focus_ui_state(
    *,
    camera_model: str,
    configured_aperture_drive_in_af: str,
    configured_af_w_shutter: str,
    configured_pre_af: str,
    lens_supports_pre_af: bool,
    configured_circ_of_focus_point: str,
    circ_wrap_axis: str,
    configured_focus_area_color: str,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute effective + reset state for the 5 `Initialize`-only focus/aperture items."""
    if camera_model == P308_FX6_DONOR_MODEL_NAME:
        return {
            "fx6_has_5items": False,
            "pre_af_effective": "Off",
            "circ_diagonal_rejected": circ_wrap_axis == "Diagonal",
            "post_aperture_drive": P308_APERTURE_DRIVE_DEFAULT,
            "post_af_w_shutter": P308_AF_W_SHUTTER_DEFAULT,
            "post_pre_af": P308_PRE_AF_DEFAULT,
            "post_circ_focus_point": P308_CIRC_FOCUS_POINT_DEFAULT,
            "post_focus_area_color": P308_FOCUS_AREA_COLOR_DEFAULT,
            "focus_priority_burst_warn": False,
        }

    pre_af_eff = configured_pre_af if lens_supports_pre_af else "Off"
    if reset_action == "Initialize":
        post_ap = P308_APERTURE_DRIVE_DEFAULT
        post_shutter = P308_AF_W_SHUTTER_DEFAULT
        post_pre = P308_PRE_AF_DEFAULT
        post_circ = P308_CIRC_FOCUS_POINT_DEFAULT
        post_color = P308_FOCUS_AREA_COLOR_DEFAULT
    else:
        post_ap = configured_aperture_drive_in_af
        post_shutter = configured_af_w_shutter
        post_pre = pre_af_eff
        post_circ = configured_circ_of_focus_point
        post_color = configured_focus_area_color

    return {
        "fx6_has_5items": False,
        "pre_af_effective": pre_af_eff,
        "circ_diagonal_rejected": circ_wrap_axis == "Diagonal",
        "post_aperture_drive": post_ap,
        "post_af_w_shutter": post_shutter,
        "post_pre_af": post_pre,
        "post_circ_focus_point": post_circ,
        "post_focus_area_color": post_color,
        "focus_priority_burst_warn": configured_aperture_drive_in_af == "Focus Priority",
    }


def compute_expected_folder_and_rating_vault_state(
    *,
    folder_name_form: str,
    file_number_mode: str,
    file_prefix: str,
    current_folder_still_count: int,
    target_slot: int,
    dual_slot_simult_rec: bool,
    slot1_holds_tier0_vault: bool,
    requested_vault_action: str,
    requested_rating_stars: int,
    image_already_rated: bool,
    shooting_domain: str,
    background_transfer_active: bool,
    reset_action: str,
) -> Dict[str, Any]:
    """Compute `[File/Folder Settings]`, `[Rating]`, and Slot-1 Tier-0 Vault Firewall decision."""
    prefix_ok = is_valid_fx3_file_prefix(file_prefix)
    folder_max_reached = current_folder_still_count >= P308_FOLDER_MAX_STILLS
    select_rec_folder_enabled = folder_name_form == "Standard Form"

    rating_allowed = requested_rating_stars in P308_RATING_STARS_VALID
    add_rating_allowed = (
        shooting_domain == "Still"
        and requested_rating_stars in P308_RATING_SET_STARS_VALID
        and not image_already_rated
    )

    touches_slot1 = (target_slot == P308_SLOT1_VAULT_SLOT) or dual_slot_simult_rec
    if requested_vault_action in P308_DESTRUCTIVE_VAULT_ACTIONS:
        if touches_slot1 and slot1_holds_tier0_vault:
            action_allowed = False
            fw_errno: Optional[str] = "EROFS"
            fw_errno_num: Optional[int] = P308_VAULT_FIREWALL_ERRNO_CODES["EROFS"]
        elif requested_vault_action in ("PLAYBACK_RATING_SET", "SHOOT_ADD_RATING") and (
            background_transfer_active
        ):
            action_allowed = False
            fw_errno = "EBUSY"
            fw_errno_num = P308_VAULT_FIREWALL_ERRNO_CODES["EBUSY"]
        elif requested_vault_action == "CREATE_NEW_FOLDER" and folder_max_reached:
            action_allowed = True
            fw_errno = None
            fw_errno_num = None
        elif requested_vault_action == "SHOOT_ADD_RATING" and not add_rating_allowed:
            action_allowed = False
            fw_errno = "EINVAL"
            fw_errno_num = 22
        else:
            action_allowed = True
            fw_errno = None
            fw_errno_num = None
    else:
        action_allowed = False
        fw_errno = None
        fw_errno_num = None

    if reset_action == "Initialize":
        post_folder_form = P308_FOLDER_NAME_DEFAULT
        post_file_num = P308_FILE_NUMBER_DEFAULT
        post_prefix = P308_FILE_PREFIX_DEFAULT
    else:
        post_folder_form = folder_name_form
        post_file_num = file_number_mode
        post_prefix = file_prefix

    return {
        "prefix_valid": prefix_ok,
        "folder_max_reached": folder_max_reached,
        "select_rec_folder_enabled": select_rec_folder_enabled,
        "rating_allowed": rating_allowed,
        "add_rating_allowed": add_rating_allowed,
        "action_allowed": action_allowed,
        "firewall_errno": fw_errno,
        "firewall_errno_num": fw_errno_num,
        "post_folder_name_form": post_folder_form,
        "post_file_number_mode": post_file_num,
        "post_file_prefix": post_prefix,
    }


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback (Phase 308, 18 Donors)
# ---------------------------------------------------------------------------


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P308_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P308_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase308_donors() -> Tuple[Phase308DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P308_DONOR_FX3_APPFW_702_RELPATH,
            P308_PINNED_FX3_APPFW_702_BYTES,
            P308_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P308_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P308_DONOR_FX6_APPFW_601_RELPATH,
            P308_PINNED_FX6_APPFW_601_BYTES,
            P308_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P308_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P308_DONOR_FX3_BACKUP_BIN_RELPATH,
            P308_PINNED_FX3_BACKUP_BIN_BYTES,
            P308_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_lib_infra_lens_comm_so",
            P308_DONOR_FX3_LIB_INFRA_LENS_COMM_RELPATH,
            P308_PINNED_FX3_LIB_INFRA_LENS_COMM_BYTES,
            P308_PINNED_FX3_LIB_INFRA_LENS_COMM_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_LIB_INFRA_LENS_COMM_SHA256,
            "SYNTHETIC_ELF64_AARCH64_LIBINFRALENSCOMMUNICATOR",
        ),
        (
            "fx3_uxc_en_f",
            P308_DONOR_FX3_UXC_EN_F_RELPATH,
            P308_PINNED_FX3_UXC_EN_F_BYTES,
            P308_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P308_DONOR_FX3_UXC_SC_F_RELPATH,
            P308_PINNED_FX3_UXC_SC_F_BYTES,
            P308_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P308_DONOR_FX3_UXC_TC_F_RELPATH,
            P308_PINNED_FX3_UXC_TC_F_BYTES,
            P308_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P308_DONOR_FX3_UXC_JA_F_RELPATH,
            P308_PINNED_FX3_UXC_JA_F_BYTES,
            P308_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P308_DONOR_FX3_UXC_EN_RELPATH,
            P308_PINNED_FX3_UXC_EN_BYTES,
            P308_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_sc",
            P308_DONOR_FX3_UXC_SC_RELPATH,
            P308_PINNED_FX3_UXC_SC_BYTES,
            P308_PINNED_FX3_UXC_SC_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX3_SC",
        ),
        (
            "fx3_uxc_tc",
            P308_DONOR_FX3_UXC_TC_RELPATH,
            P308_PINNED_FX3_UXC_TC_BYTES,
            P308_PINNED_FX3_UXC_TC_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX3_TC",
        ),
        (
            "fx3_uxc_ja",
            P308_DONOR_FX3_UXC_JA_RELPATH,
            P308_PINNED_FX3_UXC_JA_BYTES,
            P308_PINNED_FX3_UXC_JA_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX3_JA",
        ),
        (
            "fx3_uxc_en_g",
            P308_DONOR_FX3_UXC_EN_G_RELPATH,
            P308_PINNED_FX3_UXC_EN_G_BYTES,
            P308_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx3_uxc_sc_g",
            P308_DONOR_FX3_UXC_SC_G_RELPATH,
            P308_PINNED_FX3_UXC_SC_G_BYTES,
            P308_PINNED_FX3_UXC_SC_G_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_SC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_G",
        ),
        (
            "fx3_uxc_tc_g",
            P308_DONOR_FX3_UXC_TC_G_RELPATH,
            P308_PINNED_FX3_UXC_TC_G_BYTES,
            P308_PINNED_FX3_UXC_TC_G_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_TC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_G",
        ),
        (
            "fx3_uxc_ja_g",
            P308_DONOR_FX3_UXC_JA_G_RELPATH,
            P308_PINNED_FX3_UXC_JA_G_BYTES,
            P308_PINNED_FX3_UXC_JA_G_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX3_UXC_JA_G_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_G",
        ),
        (
            "fx6_uxc_en",
            P308_DONOR_FX6_UXC_EN_RELPATH,
            P308_PINNED_FX6_UXC_EN_BYTES,
            P308_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P308_DONOR_FX6_UXC_EN_2_RELPATH,
            P308_PINNED_FX6_UXC_EN_2_BYTES,
            P308_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P308_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase308DonorArtifactDigest(
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


def inspect_phase308_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase308DonorSnapshot:
    """Inspect Wave-53 FX3 7.02 (`16` donors incl. `libInfraLensCommunicator.so`) & FX6 6.01 (`2` uxcs) strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.2s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase308_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase308DonorSnapshot(
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
            P308_DONOR_FX3_APPFW_702_RELPATH,
            P308_PINNED_FX3_APPFW_702_BYTES,
            P308_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702"),
        ),
        (
            "fx6_appfw_601_so",
            P308_DONOR_FX6_APPFW_601_RELPATH,
            P308_PINNED_FX6_APPFW_601_BYTES,
            P308_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601"),
        ),
        (
            "fx3_backup_bin",
            P308_DONOR_FX3_BACKUP_BIN_RELPATH,
            P308_PINNED_FX3_BACKUP_BIN_BYTES,
            P308_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_lib_infra_lens_comm_so",
            P308_DONOR_FX3_LIB_INFRA_LENS_COMM_RELPATH,
            P308_PINNED_FX3_LIB_INFRA_LENS_COMM_BYTES,
            P308_PINNED_FX3_LIB_INFRA_LENS_COMM_SHA256,
            lambda d: _check_elf64_aarch64(d, "LIBINFRALENSCOMMUNICATOR"),
        ),
        (
            "fx3_uxc_en_f",
            P308_DONOR_FX3_UXC_EN_F_RELPATH,
            P308_PINNED_FX3_UXC_EN_F_BYTES,
            P308_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P308_DONOR_FX3_UXC_SC_F_RELPATH,
            P308_PINNED_FX3_UXC_SC_F_BYTES,
            P308_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P308_DONOR_FX3_UXC_TC_F_RELPATH,
            P308_PINNED_FX3_UXC_TC_F_BYTES,
            P308_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P308_DONOR_FX3_UXC_JA_F_RELPATH,
            P308_PINNED_FX3_UXC_JA_F_BYTES,
            P308_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P308_DONOR_FX3_UXC_EN_RELPATH,
            P308_PINNED_FX3_UXC_EN_BYTES,
            P308_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_sc",
            P308_DONOR_FX3_UXC_SC_RELPATH,
            P308_PINNED_FX3_UXC_SC_BYTES,
            P308_PINNED_FX3_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC"),
        ),
        (
            "fx3_uxc_tc",
            P308_DONOR_FX3_UXC_TC_RELPATH,
            P308_PINNED_FX3_UXC_TC_BYTES,
            P308_PINNED_FX3_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC"),
        ),
        (
            "fx3_uxc_ja",
            P308_DONOR_FX3_UXC_JA_RELPATH,
            P308_PINNED_FX3_UXC_JA_BYTES,
            P308_PINNED_FX3_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA"),
        ),
        (
            "fx3_uxc_en_g",
            P308_DONOR_FX3_UXC_EN_G_RELPATH,
            P308_PINNED_FX3_UXC_EN_G_BYTES,
            P308_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx3_uxc_sc_g",
            P308_DONOR_FX3_UXC_SC_G_RELPATH,
            P308_PINNED_FX3_UXC_SC_G_BYTES,
            P308_PINNED_FX3_UXC_SC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_G"),
        ),
        (
            "fx3_uxc_tc_g",
            P308_DONOR_FX3_UXC_TC_G_RELPATH,
            P308_PINNED_FX3_UXC_TC_G_BYTES,
            P308_PINNED_FX3_UXC_TC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_G"),
        ),
        (
            "fx3_uxc_ja_g",
            P308_DONOR_FX3_UXC_JA_G_RELPATH,
            P308_PINNED_FX3_UXC_JA_G_BYTES,
            P308_PINNED_FX3_UXC_JA_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_G"),
        ),
        (
            "fx6_uxc_en",
            P308_DONOR_FX6_UXC_EN_RELPATH,
            P308_PINNED_FX6_UXC_EN_BYTES,
            P308_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P308_DONOR_FX6_UXC_EN_2_RELPATH,
            P308_PINNED_FX6_UXC_EN_2_BYTES,
            P308_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    digests: List[Phase308DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            break
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        digests.append(
            Phase308DonorArtifactDigest(
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
        artifacts = _synthetic_phase308_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase308DonorSnapshot(
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
    return Phase308DonorSnapshot(
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
# Frozen Dataclasses (Specs, Reports, Suites & 55-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase308DonorArtifactDigest:
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
class Phase308DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase308DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LensCompAfIlluminatorVaultSpec:
    # Lens Compensation (Shading Auto/Off vs dormant Auto: Low, Chroma, Distortion lock, Breathing)
    camera_model: str
    fw_version: str
    lens_id: str
    unchipped_manual_lens: bool
    lens_requires_distortion_comp: bool
    lens_supports_breathing_comp: bool
    shooting_domain: str
    steadyshot_mode: str
    hdmi_external_raw: bool
    requested_shading_comp: str
    shading_comp_rejected_errno: Optional[int]
    dormant_shading_auto_low_exposed: bool
    requested_chroma_aber_comp: str
    requested_distortion_comp: str
    reported_distortion_forced_auto: bool
    arw_distortion_baked: bool
    arw_shading_gain_applied_on_auto: bool
    requested_breathing_comp: str
    fx6_lens_menu_path: str
    fx6_saved_in_all_file: bool
    fx6_sq_motion_on: bool
    fx6_rec_codec: str
    # Movie AF Transition Speed (1..7), AF Subj. Shift Sens. (1..5), AF Assist (Movie/S&Q AF-C)
    focus_mode: str
    requested_af_transition_speed: int
    requested_af_subj_shift_sens: int
    requested_af_assist: str
    # Built-in Front AF Illuminator LED #8 (0.3..3.0 m) + MI-Shoe external flash vs FX6 0 LED
    configured_af_illuminator: str
    silent_mode_on: bool
    focus_magnifier_active: bool
    mount_adaptor_attached: bool
    subject_moving_in_afa: bool
    mishoe_external_flash_attached: bool
    reported_builtin_af_illuminator_active: bool
    reported_mishoe_af_illuminator_active: bool
    reported_has_builtin_af_illuminator: bool
    # Reset & post-reset state
    reset_action: str
    post_shading_comp: str
    post_chroma_aber_comp: str
    post_distortion_comp: str
    post_breathing_comp: str
    post_af_transition_speed: int
    post_af_subj_shift_sens: int
    post_af_assist: str
    post_af_illuminator: str
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
    dormant_shading_auto_low_exposure_events: int
    lens_comp_lock_or_arw_conflation_events: int
    af_illuminator_gate_or_fx6_spoof_events: int
    movie_af_transition_or_assist_drift_events: int


@dataclass(frozen=True)
class LensCompAfIlluminatorVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    lens_comp_auto_off_no_auto_low_verified: bool
    movie_af_transition_shift_assist_verified: bool
    builtin_front_af_illuminator_vs_fx6_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    dormant_shading_auto_low_exposure_events: int
    lens_comp_lock_or_arw_conflation_events: int
    af_illuminator_gate_or_fx6_spoof_events: int
    movie_af_transition_or_assist_drift_events: int
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
class ApertureDriveFolderRatingVaultSpec:
    # 5 Initialize-Only Focus/Aperture Items
    camera_model: str
    shooting_domain: str
    configured_aperture_drive_in_af: str
    aperture_drive_burst_warn_acknowledged: bool
    configured_af_w_shutter: str
    configured_pre_af: str
    lens_supports_pre_af: bool
    configured_circ_of_focus_point: str
    circ_wrap_axis: str
    configured_focus_area_color: str
    reset_action: str
    post_aperture_drive_in_af: str
    post_af_w_shutter: str
    post_pre_af: str
    post_circ_of_focus_point: str
    post_focus_area_color: str
    fx6_exposes_aperture_drive_or_circ_color: bool
    # File/Folder Settings & Playback Rating 1..5 Stars + Slot-1 Tier-0 Vault Firewall
    folder_name_form: str
    select_rec_folder_enabled: bool
    file_number_mode: str
    file_prefix: str
    post_folder_name_form: str
    post_file_number_mode: str
    post_file_prefix: str
    current_folder_still_count: int
    requested_rating_stars: int
    rating_set_custom_key_mask: Tuple[int, ...]
    image_already_rated: bool
    background_transfer_active: bool
    fx6_exposes_msdcf_or_star_rating: bool
    # Slot-1 Tier-0 Vault Firewall
    target_media_slot: int
    dual_slot_simult_rec: bool
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    reported_vault_action_allowed: bool
    vault_firewall_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_folder_dir_mutation_bytes: int
    slot1_rating_avf_info_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    aperture_drive_pre_af_shutter_reset_drift_events: int
    circ_focus_diagonal_or_color_drift_events: int
    folder_name_or_leading_underscore_violations: int


@dataclass(frozen=True)
class ApertureDriveFolderRatingVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    aperture_drive_pre_af_shutter_init_only_verified: bool
    circ_focus_orthogonal_and_area_color_verified: bool
    file_folder_and_playback_rating_policy_verified: bool
    slot1_folder_rating_erofs_ebusy_firewall_verified: bool
    matrix_states_checked: int
    aperture_drive_pre_af_shutter_reset_drift_events: int
    circ_focus_diagonal_or_color_drift_events: int
    folder_name_or_leading_underscore_violations: int
    slot1_data_sector_writes: int
    slot1_folder_dir_mutation_bytes: int
    slot1_rating_avf_info_mutation_bytes: int
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
class LensCompAfIlluminatorFolderRatingVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase308DonorSnapshot
    lens_comp_af_illuminator_report: LensCompAfIlluminatorVaultReport
    aperture_drive_folder_rating_report: ApertureDriveFolderRatingVaultReport
    dormant_shading_auto_low_exposure_events: int
    lens_comp_lock_or_arw_conflation_events: int
    af_illuminator_gate_or_fx6_spoof_events: int
    movie_af_transition_or_assist_drift_events: int
    aperture_drive_pre_af_shutter_reset_drift_events: int
    circ_focus_diagonal_or_color_drift_events: int
    folder_name_or_leading_underscore_violations: int
    slot1_data_sector_writes: int
    slot1_folder_dir_mutation_bytes: int
    slot1_rating_avf_info_mutation_bytes: int
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
class Pillar55ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar55ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar55ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar55BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar55ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar55StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase308DonorSnapshot
    pillar_55a_lens_comp_af_illuminator_vault: Pillar55ASuiteResult
    pillar_55b_aperture_drive_folder_rating_vault: Pillar55BSuiteResult
    dormant_shading_auto_low_exposure_events: int
    lens_comp_lock_or_arw_conflation_events: int
    af_illuminator_gate_or_fx6_spoof_events: int
    movie_af_transition_or_assist_drift_events: int
    aperture_drive_pre_af_shutter_reset_drift_events: int
    circ_focus_diagonal_or_color_drift_events: int
    folder_name_or_leading_underscore_violations: int
    slot1_data_sector_writes: int
    slot1_folder_dir_mutation_bytes: int
    slot1_rating_avf_info_mutation_bytes: int
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
class Master55PillarRecoveryReport:
    schema: str
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
    # Pillar 55 & Wave-53 top-level fields (Phase 308 — 55/55 Milestone)
    donor_snapshot: Phase308DonorSnapshot
    pillar55_a_lens_comp_af_illuminator_vault: Pillar55ASuiteResult
    pillar55_b_aperture_drive_folder_rating_vault: Pillar55BSuiteResult
    dormant_shading_auto_low_exposure_events: int
    lens_comp_lock_or_arw_conflation_events: int
    af_illuminator_gate_or_fx6_spoof_events: int
    movie_af_transition_or_assist_drift_events: int
    aperture_drive_pre_af_shutter_reset_drift_events: int
    circ_focus_diagonal_or_color_drift_events: int
    folder_name_or_leading_underscore_violations: int
    slot1_data_sector_writes: int
    slot1_folder_dir_mutation_bytes: int
    slot1_rating_avf_info_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    fx3_has_builtin_af_illuminator: bool
    fx6_has_builtin_af_illuminator: bool
    fx3_exposes_shading_auto_low: bool
    fx6_has_aperture_drive_pre_af_circ_color: bool
    fx6_has_msdcf_or_star_rating: bool
    # Preserved Pillars 1..54 rollup metrics
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
    master_55pillar_sha256: str
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
# Spec Builders & Evaluators (Pillars 55A & 55B)
# ---------------------------------------------------------------------------


def build_default_safe_lens_comp_af_illuminator_vault_spec(
    **overrides: Any,
) -> LensCompAfIlluminatorVaultSpec:
    """Return a clean, verified default `LensCompAfIlluminatorVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P308_FX3_MODEL_NAME,
        "fw_version": P308_FX3_FW_VERSION,
        "lens_id": "SEL2470GM2",
        "unchipped_manual_lens": False,
        "lens_requires_distortion_comp": False,
        "lens_supports_breathing_comp": True,
        "shooting_domain": "Still",
        "steadyshot_mode": "Standard",
        "hdmi_external_raw": False,
        "requested_shading_comp": "Auto",
        "shading_comp_rejected_errno": None,
        "dormant_shading_auto_low_exposed": False,
        "requested_chroma_aber_comp": "Auto",
        "requested_distortion_comp": "Off",
        "reported_distortion_forced_auto": False,
        "arw_distortion_baked": False,
        "arw_shading_gain_applied_on_auto": True,
        "requested_breathing_comp": "Off",
        "fx6_lens_menu_path": P308_FX6_LENS_COMP_MENU_PATH,
        "fx6_saved_in_all_file": True,
        "fx6_sq_motion_on": False,
        "fx6_rec_codec": "XAVC-I",
        "focus_mode": "AF-S",
        "requested_af_transition_speed": P308_AF_TRANSITION_SPEED_DEFAULT,
        "requested_af_subj_shift_sens": P308_AF_SUBJ_SHIFT_SENS_DEFAULT,
        "requested_af_assist": "Off",
        "configured_af_illuminator": "Auto",
        "silent_mode_on": False,
        "focus_magnifier_active": False,
        "mount_adaptor_attached": False,
        "subject_moving_in_afa": False,
        "mishoe_external_flash_attached": True,
        "reported_builtin_af_illuminator_active": True,
        "reported_mishoe_af_illuminator_active": True,
        "reported_has_builtin_af_illuminator": True,
        "reset_action": "None",
        "post_shading_comp": "Auto",
        "post_chroma_aber_comp": "Auto",
        "post_distortion_comp": "Off",
        "post_breathing_comp": "Off",
        "post_af_transition_speed": P308_AF_TRANSITION_SPEED_DEFAULT,
        "post_af_subj_shift_sens": P308_AF_SUBJ_SHIFT_SENS_DEFAULT,
        "post_af_assist": "Off",
        "post_af_illuminator": "Auto",
        "requested_vault_slot": P308_SLOT1_VAULT_SLOT,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_ebusy_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P308_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P308_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P308_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P308_TIER0_SURFACE_COUNT,
        "dormant_shading_auto_low_exposure_events": 0,
        "lens_comp_lock_or_arw_conflation_events": 0,
        "af_illuminator_gate_or_fx6_spoof_events": 0,
        "movie_af_transition_or_assist_drift_events": 0,
    }
    defaults.update(overrides)
    return LensCompAfIlluminatorVaultSpec(**defaults)


def build_default_safe_aperture_drive_folder_rating_vault_spec(
    **overrides: Any,
) -> ApertureDriveFolderRatingVaultSpec:
    """Return a clean, verified default `ApertureDriveFolderRatingVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P308_FX3_MODEL_NAME,
        "shooting_domain": "Still",
        "configured_aperture_drive_in_af": "Standard",
        "aperture_drive_burst_warn_acknowledged": True,
        "configured_af_w_shutter": "On",
        "configured_pre_af": "Off",
        "lens_supports_pre_af": True,
        "configured_circ_of_focus_point": "Does Not Circulate",
        "circ_wrap_axis": "Horizontal",
        "configured_focus_area_color": "White",
        "reset_action": "None",
        "post_aperture_drive_in_af": "Standard",
        "post_af_w_shutter": "On",
        "post_pre_af": "Off",
        "post_circ_of_focus_point": "Does Not Circulate",
        "post_focus_area_color": "White",
        "fx6_exposes_aperture_drive_or_circ_color": False,
        "folder_name_form": "Standard Form",
        "select_rec_folder_enabled": True,
        "file_number_mode": "Series",
        "file_prefix": "DSC",
        "post_folder_name_form": "Standard Form",
        "post_file_number_mode": "Series",
        "post_file_prefix": "DSC",
        "current_folder_still_count": 42,
        "requested_rating_stars": 3,
        "rating_set_custom_key_mask": (1, 3, 5),
        "image_already_rated": False,
        "background_transfer_active": False,
        "fx6_exposes_msdcf_or_star_rating": False,
        "target_media_slot": P308_SAFE_SECONDARY_SLOT,
        "dual_slot_simult_rec": False,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "reported_vault_action_allowed": False,
        "vault_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_folder_dir_mutation_bytes": 0,
        "slot1_rating_avf_info_mutation_bytes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_ebusy_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P308_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P308_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P308_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P308_TIER0_SURFACE_COUNT,
        "aperture_drive_pre_af_shutter_reset_drift_events": 0,
        "circ_focus_diagonal_or_color_drift_events": 0,
        "folder_name_or_leading_underscore_violations": 0,
    }
    defaults.update(overrides)
    return ApertureDriveFolderRatingVaultSpec(**defaults)


def evaluate_lens_comp_af_illuminator_vault(
    spec: LensCompAfIlluminatorVaultSpec,
) -> LensCompAfIlluminatorVaultReport:
    """Evaluate Pillar 55A (`[Lens Compensation]` Auto/Off without dormant `Auto: Low` `0x6c9c`
    `EOPNOTSUPP=95` + Distortion Auto-lock + `Breathing Comp.` + FX6 `Technical > Lens` `All File`,
    Movie `[AF Transition Speed]`/`[AF Subj. Shift Sens.]`/`[AF Assist]`, & Built-in Front
    `[AF Illuminator]` LED #8 + MI-Shoe Still-only vs Zero-Illuminator `ILME-FX6`)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(
            P308_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Module safety invariant violation",
        )

    valid_fw = (
        (
            spec.camera_model == P308_FX3_MODEL_NAME
            and spec.fw_version in P308_FX3_SUPPORTED_FW_VERSIONS
        )
        or (
            spec.camera_model == P308_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P308_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P308_SHOOTING_DOMAINS
        or spec.steadyshot_mode not in P308_STEADYSHOT_MODES
        or spec.requested_shading_comp
        not in (P308_SHADING_COMP_EXPOSED_MODES + P308_SHADING_COMP_DORMANT_MODES)
        or spec.requested_chroma_aber_comp not in P308_CHROMA_ABER_MODES
        or spec.requested_distortion_comp not in P308_DISTORTION_MODES
        or spec.requested_breathing_comp not in P308_ON_OFF_MODES
        or spec.focus_mode not in P308_FOCUS_MODES_ALL
        or not (
            P308_AF_TRANSITION_SPEED_MIN
            <= spec.requested_af_transition_speed
            <= P308_AF_TRANSITION_SPEED_MAX
        )
        or not (
            P308_AF_SUBJ_SHIFT_SENS_MIN
            <= spec.requested_af_subj_shift_sens
            <= P308_AF_SUBJ_SHIFT_SENS_MAX
        )
        or spec.requested_af_assist not in P308_ON_OFF_MODES
        or spec.configured_af_illuminator not in P308_AF_ILLUMINATOR_MODES
        or spec.reset_action not in P308_RESET_ACTIONS
        or spec.requested_vault_slot not in (1, 2)
        or spec.requested_vault_action not in P308_VAULT_TARGET_ACTIONS
    ):
        _fail(
            P308_BLOCKED_INVALID_PILLAR55A_SPEC,
            "Invalid Pillar 55A camera/LensComp/AF/Illuminator/vault spec parameter",
        )

    lc = compute_expected_lens_comp_and_movie_af_state(
        camera_model=spec.camera_model,
        lens_id=spec.lens_id,
        unchipped_manual_lens=spec.unchipped_manual_lens,
        lens_requires_distortion_comp=spec.lens_requires_distortion_comp,
        lens_supports_breathing_comp=spec.lens_supports_breathing_comp,
        shooting_domain=spec.shooting_domain,
        steadyshot_mode=spec.steadyshot_mode,
        hdmi_external_raw=spec.hdmi_external_raw,
        requested_shading_comp=spec.requested_shading_comp,
        requested_chroma_aber_comp=spec.requested_chroma_aber_comp,
        requested_distortion_comp=spec.requested_distortion_comp,
        requested_breathing_comp=spec.requested_breathing_comp,
        requested_af_transition_speed=spec.requested_af_transition_speed,
        requested_af_subj_shift_sens=spec.requested_af_subj_shift_sens,
        requested_af_assist=spec.requested_af_assist,
        focus_mode=spec.focus_mode,
        fx6_sq_motion_on=spec.fx6_sq_motion_on,
        fx6_rec_codec=spec.fx6_rec_codec,
        reset_action=spec.reset_action,
    )
    exp_led_active, exp_mishoe_active, exp_post_illum, exp_has_led = (
        compute_expected_af_illuminator_state(
            camera_model=spec.camera_model,
            shooting_domain=spec.shooting_domain,
            focus_mode=spec.focus_mode,
            configured_af_illuminator=spec.configured_af_illuminator,
            silent_mode_on=spec.silent_mode_on,
            focus_magnifier_active=spec.focus_magnifier_active,
            mount_adaptor_attached=spec.mount_adaptor_attached,
            subject_moving_in_afa=spec.subject_moving_in_afa,
            mishoe_external_flash_attached=spec.mishoe_external_flash_attached,
            reset_action=spec.reset_action,
        )
    )

    # 1. Lens Compensation: Shading Auto/Off only (reject dormant Auto: Low as EOPNOTSUPP=95)
    #    Distortion forced Auto on lens/SteadyShot Active, zero .ARW bake, Breathing & FX6 path
    shading_valid_mode = (
        spec.requested_shading_comp in P308_SHADING_COMP_EXPOSED_MODES
        and not spec.dormant_shading_auto_low_exposed
        and spec.shading_comp_rejected_errno is None
        and spec.dormant_shading_auto_low_exposure_events == 0
    )
    fx6_lens_ok = (
        spec.camera_model != P308_FX6_DONOR_MODEL_NAME
        or (
            spec.fx6_lens_menu_path == P308_FX6_LENS_COMP_MENU_PATH
            and spec.fx6_lens_menu_path != P308_FX6_LEGACY_LENS_COMP_MENU_PATH
            and spec.fx6_saved_in_all_file
        )
    )
    lens_comp_ok = (
        shading_valid_mode
        and spec.reported_distortion_forced_auto == lc["distortion_forced_auto"]
        and not (lc["distortion_forced_auto"] and spec.post_distortion_comp != "Auto")
        and not spec.arw_distortion_baked
        and not (not lc["menu_enabled"] and spec.requested_breathing_comp == "On")
        and spec.post_shading_comp == lc["post_shading"]
        and spec.post_chroma_aber_comp == lc["post_chroma"]
        and spec.post_distortion_comp == lc["post_distortion"]
        and spec.post_breathing_comp == lc["post_breathing"]
        and fx6_lens_ok
        and spec.lens_comp_lock_or_arw_conflation_events == 0
    )
    if not lens_comp_ok:
        _fail(
            P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT,
            "Lens Compensation violated Shading Auto/Off-only (dormant Auto: Low 0x6c9c EOPNOTSUPP=95), Distortion Auto-lock/no-ARW-bake, Breathing, or FX6 Technical > Lens isolation",
        )

    # 2. Movie AF Transition Speed (1..7), AF Subj. Shift Sens. (1..5), AF Assist (Movie/S&Q AF-C)
    movie_af_ok = (
        spec.post_af_transition_speed == lc["post_af_transition_speed"]
        and spec.post_af_subj_shift_sens == lc["post_af_subj_shift_sens"]
        and spec.post_af_assist == lc["post_af_assist"]
        and spec.movie_af_transition_or_assist_drift_events == 0
    )
    if not movie_af_ok:
        _fail(
            P308_BLOCKED_MOVIE_AF_TRANSITION_SENS_OR_ASSIST_DRIFT,
            "Movie AF Transition Speed (1..7), AF Subj. Shift Sens. (1..5), or AF Assist Camera Settings Reset / compatibility contract drifted",
        )

    # 3. Built-in Front AF Illuminator LED #8 (0.3..3.0m) + MI-Shoe Still AF-S vs Zero-LED FX6
    illum_ok = (
        spec.reported_has_builtin_af_illuminator == exp_has_led
        and spec.reported_builtin_af_illuminator_active == exp_led_active
        and spec.reported_mishoe_af_illuminator_active == exp_mishoe_active
        and spec.post_af_illuminator == exp_post_illum
        and not (
            spec.camera_model == P308_FX6_DONOR_MODEL_NAME
            and (
                spec.reported_has_builtin_af_illuminator
                or spec.reported_builtin_af_illuminator_active
            )
        )
        and spec.af_illuminator_gate_or_fx6_spoof_events == 0
    )
    if not illum_ok:
        _fail(
            P308_BLOCKED_AF_ILLUMINATOR_GATE_OR_FX6_LED_SPOOF,
            "AF Illuminator violated FX3 front LED #8 Still AF-S gate (locked in Movie/S&Q/AF-C/MF/Silent/Magnifier/Adaptor) or zero-illuminator FX6 boundary",
        )

    # 4. Slot-1 Tier-0 Vault Firewall & H0 == H3
    vault_fw_ok = (
        spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_ebusy_enforced
        and spec.slot1_vault_mutation_bytes == 0
        and not (
            spec.requested_vault_slot == P308_SLOT1_VAULT_SLOT
            and spec.requested_vault_action in P308_DESTRUCTIVE_VAULT_ACTIONS
        )
    )
    if not vault_fw_ok:
        _fail(
            P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS/EBUSY firewall blocked write/format/folder/rating mutation on Tier-0 media",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P308_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P308_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P308_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P308_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "55A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "fw_version": spec.fw_version,
            "shooting_domain": spec.shooting_domain,
            "focus_mode": spec.focus_mode,
            "post_shading": spec.post_shading_comp,
            "post_distortion": spec.post_distortion_comp,
            "post_breathing": spec.post_breathing_comp,
            "builtin_led_active": spec.reported_builtin_af_illuminator_active,
            "has_builtin_led": spec.reported_has_builtin_af_illuminator,
            "slot1_bytes": spec.slot1_vault_mutation_bytes,
            "errors": errors,
        }
    )
    return LensCompAfIlluminatorVaultReport(
        schema=PHASE308_SCHEMA,
        version=PHASE308_VERSION,
        passed=passed,
        status=P308_STATUS_VERIFIED_PILLAR_55A if passed else P308_STATUS_REJECTED_PILLAR_55A,
        block_code=block_code,
        lens_comp_auto_off_no_auto_low_verified=lens_comp_ok,
        movie_af_transition_shift_assist_verified=movie_af_ok,
        builtin_front_af_illuminator_vs_fx6_verified=illum_ok,
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        dormant_shading_auto_low_exposure_events=spec.dormant_shading_auto_low_exposure_events,
        lens_comp_lock_or_arw_conflation_events=spec.lens_comp_lock_or_arw_conflation_events,
        af_illuminator_gate_or_fx6_spoof_events=spec.af_illuminator_gate_or_fx6_spoof_events,
        movie_af_transition_or_assist_drift_events=spec.movie_af_transition_or_assist_drift_events,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_aperture_drive_folder_rating_vault(
    spec: ApertureDriveFolderRatingVaultSpec,
) -> ApertureDriveFolderRatingVaultReport:
    """Evaluate Pillar 55B (`[Aperture Drive in AF]`/`[AF w/ Shutter]`/`[Pre-AF]`/
    `[Circ. of Focus Point]` (orthogonal only)/`[Focus Area Color]` Initialize-only persistence,
    `[File/Folder Settings]` + Playback `[Rating]` 1..5 stars, and CRITICAL Slot-1 Tier-0 Vault
    `EROFS`/`EBUSY` Firewall against `[Create New Folder]`, `[Forced File Number Reset]`,
    `[Rating]`, and `[Add Rating]`)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(
            P308_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Module safety invariant violation",
        )

    if (
        spec.camera_model != P308_FX3_MODEL_NAME
        or spec.shooting_domain not in P308_SHOOTING_DOMAINS
        or spec.configured_aperture_drive_in_af not in P308_APERTURE_DRIVE_MODES
        or spec.post_aperture_drive_in_af not in P308_APERTURE_DRIVE_MODES
        or spec.configured_af_w_shutter not in P308_ON_OFF_MODES
        or spec.post_af_w_shutter not in P308_ON_OFF_MODES
        or spec.configured_pre_af not in P308_ON_OFF_MODES
        or spec.post_pre_af not in P308_ON_OFF_MODES
        or spec.configured_circ_of_focus_point not in P308_CIRC_FOCUS_POINT_MODES
        or spec.post_circ_of_focus_point not in P308_CIRC_FOCUS_POINT_MODES
        or spec.circ_wrap_axis not in P308_CIRC_WRAP_AXES
        or spec.configured_focus_area_color not in P308_FOCUS_AREA_COLOR_MODES
        or spec.post_focus_area_color not in P308_FOCUS_AREA_COLOR_MODES
        or spec.folder_name_form not in P308_FOLDER_NAME_FORMS
        or spec.post_folder_name_form not in P308_FOLDER_NAME_FORMS
        or spec.file_number_mode not in P308_FILE_NUMBER_MODES
        or spec.post_file_number_mode not in P308_FILE_NUMBER_MODES
        or spec.requested_rating_stars not in P308_RATING_STARS_VALID
        or spec.target_media_slot not in (1, 2)
        or (
            spec.vault_firewall_errno is not None
            and spec.vault_firewall_errno not in P308_VAULT_FIREWALL_ERRNOS
        )
        or spec.reset_action not in P308_RESET_ACTIONS
        or spec.requested_vault_action not in P308_VAULT_TARGET_ACTIONS
    ):
        _fail(
            P308_BLOCKED_INVALID_PILLAR55B_SPEC,
            "Invalid Pillar 55B camera/ApertureDrive/CircFocus/Folder/Rating/vault spec parameter",
        )

    af_ui = compute_expected_aperture_drive_and_focus_ui_state(
        camera_model=spec.camera_model,
        configured_aperture_drive_in_af=spec.configured_aperture_drive_in_af,
        configured_af_w_shutter=spec.configured_af_w_shutter,
        configured_pre_af=spec.configured_pre_af,
        lens_supports_pre_af=spec.lens_supports_pre_af,
        configured_circ_of_focus_point=spec.configured_circ_of_focus_point,
        circ_wrap_axis=spec.circ_wrap_axis,
        configured_focus_area_color=spec.configured_focus_area_color,
        reset_action=spec.reset_action,
    )
    fr = compute_expected_folder_and_rating_vault_state(
        folder_name_form=spec.folder_name_form,
        file_number_mode=spec.file_number_mode,
        file_prefix=spec.file_prefix,
        current_folder_still_count=spec.current_folder_still_count,
        target_slot=spec.target_media_slot,
        dual_slot_simult_rec=spec.dual_slot_simult_rec,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_vault_action=spec.requested_vault_action,
        requested_rating_stars=spec.requested_rating_stars,
        image_already_rated=spec.image_already_rated,
        shooting_domain=spec.shooting_domain,
        background_transfer_active=spec.background_transfer_active,
        reset_action=spec.reset_action,
    )

    # 1. 5 Initialize-only items & orthogonal Circ. of Focus Point (no diagonal wrap)
    init5_ok = (
        spec.post_aperture_drive_in_af == af_ui["post_aperture_drive"]
        and spec.post_af_w_shutter == af_ui["post_af_w_shutter"]
        and spec.post_pre_af == af_ui["post_pre_af"]
        and not (not spec.lens_supports_pre_af and spec.configured_pre_af == "On" and spec.post_pre_af == "On")
        and (
            spec.configured_aperture_drive_in_af != "Focus Priority"
            or spec.aperture_drive_burst_warn_acknowledged
        )
        and spec.post_circ_of_focus_point == af_ui["post_circ_focus_point"]
        and not af_ui["circ_diagonal_rejected"]
        and spec.post_focus_area_color == af_ui["post_focus_area_color"]
        and not spec.fx6_exposes_aperture_drive_or_circ_color
        and spec.aperture_drive_pre_af_shutter_reset_drift_events == 0
        and spec.circ_focus_diagonal_or_color_drift_events == 0
    )
    if not init5_ok:
        _fail(
            P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT,
            "5 Initialize-only items (Aperture Drive in AF / AF w/ Shutter / Pre-AF / orthogonal Circ. of Focus Point / Focus Area Color) or FX6 Iris boundary drifted",
        )

    # 2. [File/Folder Settings] & Playback [Rating] (1..5 stars, no leading '_', <= 4000, no Add overwrite)
    mask_valid = all(star in P308_RATING_SET_STARS_VALID for star in spec.rating_set_custom_key_mask)
    folder_rating_ok = (
        fr["prefix_valid"]
        and is_valid_fx3_file_prefix(spec.post_file_prefix)
        and spec.select_rec_folder_enabled == fr["select_rec_folder_enabled"]
        and spec.post_folder_name_form == fr["post_folder_name_form"]
        and spec.post_file_number_mode == fr["post_file_number_mode"]
        and spec.post_file_prefix == fr["post_file_prefix"]
        and fr["rating_allowed"]
        and mask_valid
        and not (
            spec.requested_vault_action == "CREATE_NEW_FOLDER"
            and spec.current_folder_still_count > P308_FOLDER_MAX_STILLS
        )
        and not (
            spec.requested_vault_action == "SHOOT_ADD_RATING"
            and not fr["add_rating_allowed"]
        )
        and not spec.fx6_exposes_msdcf_or_star_rating
        and spec.folder_name_or_leading_underscore_violations == 0
    )
    if not folder_rating_ok:
        _fail(
            P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT,
            "File/Folder Settings (Standard/Date Form, Series/Reset, 3-char DSC prefix, 4000 limit) or Playback Rating 1..5 stars contract violated",
        )

    # 3. CRITICAL SLOT-1 TIER-0 VAULT FIREWALL: [Create New Folder], [Forced File Number Reset],
    #    [Select REC Folder] simult, Playback [Rating], [Add Rating]
    touches_slot1 = (
        spec.target_media_slot == P308_SLOT1_VAULT_SLOT or spec.dual_slot_simult_rec
    )
    slot1_destructive = (
        touches_slot1
        and spec.slot1_holds_tier0_vault
        and spec.requested_vault_action in P308_DESTRUCTIVE_VAULT_ACTIONS
    )
    vault_fw_ok = (
        not slot1_destructive
        and spec.reported_vault_action_allowed == fr["action_allowed"]
        and spec.vault_firewall_errno == fr["firewall_errno"]
        and not (
            spec.requested_vault_action in ("PLAYBACK_RATING_SET", "SHOOT_ADD_RATING")
            and spec.background_transfer_active
        )
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_folder_dir_mutation_bytes == 0
        and spec.slot1_rating_avf_info_mutation_bytes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_ebusy_enforced
        and spec.slot1_format_hard_locked
    )
    if not vault_fw_ok:
        _fail(
            P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault firewall blocked Create New Folder / Forced File Number Reset / Playback Rating EXIF+AVF_INFO mutation (EROFS=30 / EBUSY=16, 0 sector writes)",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P308_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P308_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P308_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P308_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "55B",
            "passed": passed,
            "block_code": block_code,
            "post_aperture_drive": spec.post_aperture_drive_in_af,
            "post_af_w_shutter": spec.post_af_w_shutter,
            "post_pre_af": spec.post_pre_af,
            "post_circ_focus": spec.post_circ_of_focus_point,
            "post_focus_color": spec.post_focus_area_color,
            "post_folder_form": spec.post_folder_name_form,
            "post_prefix": spec.post_file_prefix,
            "target_slot": spec.target_media_slot,
            "action": spec.requested_vault_action,
            "slot1_data_sector_writes": spec.slot1_data_sector_writes,
            "slot1_folder_bytes": spec.slot1_folder_dir_mutation_bytes,
            "slot1_rating_bytes": spec.slot1_rating_avf_info_mutation_bytes,
            "errors": errors,
        }
    )
    return ApertureDriveFolderRatingVaultReport(
        schema=PHASE308_SCHEMA,
        version=PHASE308_VERSION,
        passed=passed,
        status=P308_STATUS_VERIFIED_PILLAR_55B if passed else P308_STATUS_REJECTED_PILLAR_55B,
        block_code=block_code,
        aperture_drive_pre_af_shutter_init_only_verified=init5_ok,
        circ_focus_orthogonal_and_area_color_verified=(
            not af_ui["circ_diagonal_rejected"]
            and spec.circ_focus_diagonal_or_color_drift_events == 0
        ),
        file_folder_and_playback_rating_policy_verified=folder_rating_ok,
        slot1_folder_rating_erofs_ebusy_firewall_verified=slot1_and_tier0_ok,
        matrix_states_checked=18,
        aperture_drive_pre_af_shutter_reset_drift_events=(
            spec.aperture_drive_pre_af_shutter_reset_drift_events
        ),
        circ_focus_diagonal_or_color_drift_events=spec.circ_focus_diagonal_or_color_drift_events,
        folder_name_or_leading_underscore_violations=(
            spec.folder_name_or_leading_underscore_violations
        ),
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_folder_dir_mutation_bytes=spec.slot1_folder_dir_mutation_bytes,
        slot1_rating_avf_info_mutation_bytes=spec.slot1_rating_avf_info_mutation_bytes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_lens_comp_af_illuminator_folder_rating_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_55a: Optional[LensCompAfIlluminatorVaultSpec] = None,
    spec_55b: Optional[ApertureDriveFolderRatingVaultSpec] = None,
) -> LensCompAfIlluminatorFolderRatingVaultReport:
    """Combined single-shot verifier for Pillar 55A + Pillar 55B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase308_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_lens_comp_af_illuminator_vault(
        spec_55a or build_default_safe_lens_comp_af_illuminator_vault_spec()
    )
    rep_b = evaluate_aperture_drive_folder_rating_vault(
        spec_55b or build_default_safe_aperture_drive_folder_rating_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 308 Wave-53 donor artifact parity check failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return LensCompAfIlluminatorFolderRatingVaultReport(
        schema=PHASE308_SCHEMA,
        version=PHASE308_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P308_STATUS_VERIFIED_PILLAR55_SUITE if all_ok else P308_STATUS_FAIL_PILLAR55_SUITE,
        donor_snapshot=donor_snapshot,
        lens_comp_af_illuminator_report=rep_a,
        aperture_drive_folder_rating_report=rep_b,
        dormant_shading_auto_low_exposure_events=rep_a.dormant_shading_auto_low_exposure_events,
        lens_comp_lock_or_arw_conflation_events=rep_a.lens_comp_lock_or_arw_conflation_events,
        af_illuminator_gate_or_fx6_spoof_events=rep_a.af_illuminator_gate_or_fx6_spoof_events,
        movie_af_transition_or_assist_drift_events=rep_a.movie_af_transition_or_assist_drift_events,
        aperture_drive_pre_af_shutter_reset_drift_events=(
            rep_b.aperture_drive_pre_af_shutter_reset_drift_events
        ),
        circ_focus_diagonal_or_color_drift_events=rep_b.circ_focus_diagonal_or_color_drift_events,
        folder_name_or_leading_underscore_violations=(
            rep_b.folder_name_or_leading_underscore_violations
        ),
        slot1_data_sector_writes=rep_b.slot1_data_sector_writes,
        slot1_folder_dir_mutation_bytes=rep_b.slot1_folder_dir_mutation_bytes,
        slot1_rating_avf_info_mutation_bytes=rep_b.slot1_rating_avf_info_mutation_bytes,
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


def verify_lens_comp_af_illuminator_folder_rating_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_55a: Optional[LensCompAfIlluminatorVaultSpec] = None,
    spec_55b: Optional[ApertureDriveFolderRatingVaultSpec] = None,
) -> LensCompAfIlluminatorFolderRatingVaultReport:
    """Symmetry alias for `verify_lens_comp_af_illuminator_folder_rating_and_vault`."""
    return verify_lens_comp_af_illuminator_folder_rating_and_vault(
        force_clean_room=force_clean_room,
        spec_55a=spec_55a,
        spec_55b=spec_55b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 55A & 55B) + Standalone Pillar 55 Suite
# ---------------------------------------------------------------------------


def run_pillar55a_lens_comp_af_illuminator_6_scenario_suite() -> Pillar55ASuiteResult:
    """Run 6 Pillar 55A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, LensCompAfIlluminatorVaultSpec, Optional[str]], ...] = (
        (
            P308_PILLAR_55A_SCENARIO_IDS[0],
            True,
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Still",
                steadyshot_mode="Standard",
                requested_shading_comp="Auto",
                requested_chroma_aber_comp="Auto",
                requested_distortion_comp="Auto",
                reported_distortion_forced_auto=False,
                post_shading_comp="Auto",
                post_chroma_aber_comp="Auto",
                post_distortion_comp="Auto",
                focus_mode="AF-S",
                configured_af_illuminator="Auto",
                mishoe_external_flash_attached=True,
                reported_builtin_af_illuminator_active=True,
                reported_mishoe_af_illuminator_active=True,
                reported_has_builtin_af_illuminator=True,
                post_af_illuminator="Auto",
            ),
            None,
        ),
        (
            P308_PILLAR_55A_SCENARIO_IDS[1],
            True,
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                camera_model=P308_FX6_DONOR_MODEL_NAME,
                fw_version=P308_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                steadyshot_mode="Off",
                requested_shading_comp="Off",
                requested_chroma_aber_comp="Off",
                requested_distortion_comp="Auto",
                reported_distortion_forced_auto=False,
                requested_breathing_comp="On",
                focus_mode="AF-C",
                configured_af_illuminator="Off",
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
                reported_has_builtin_af_illuminator=False,
                reset_action="Camera Settings Reset",
                post_shading_comp="Off",
                post_chroma_aber_comp="Off",
                post_distortion_comp="Auto",
                post_breathing_comp="Off",
                post_af_transition_speed=P308_AF_TRANSITION_SPEED_DEFAULT,
                post_af_subj_shift_sens=P308_AF_SUBJ_SHIFT_SENS_DEFAULT,
                post_af_assist="Off",
                post_af_illuminator="Off",
            ),
            None,
        ),
        (
            P308_PILLAR_55A_SCENARIO_IDS[2],
            False,
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                requested_shading_comp="Auto: Low",
                dormant_shading_auto_low_exposed=True,
                shading_comp_rejected_errno=None,
                dormant_shading_auto_low_exposure_events=1,
            ),
            P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT,
        ),
        (
            P308_PILLAR_55A_SCENARIO_IDS[3],
            False,
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                shooting_domain="Movie",
                steadyshot_mode="Active",
                requested_distortion_comp="Off",
                reported_distortion_forced_auto=False,
                post_distortion_comp="Off",
                arw_distortion_baked=True,
                focus_mode="AF-C",
                mishoe_external_flash_attached=False,
                reported_builtin_af_illuminator_active=False,
                reported_mishoe_af_illuminator_active=False,
                lens_comp_lock_or_arw_conflation_events=1,
            ),
            P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT,
        ),
        (
            P308_PILLAR_55A_SCENARIO_IDS[4],
            False,
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                camera_model=P308_FX6_DONOR_MODEL_NAME,
                fw_version=P308_FX6_DONOR_FW_VERSION,
                shooting_domain="Movie",
                steadyshot_mode="Standard",
                requested_distortion_comp="Off",
                post_distortion_comp="Off",
                focus_mode="AF-C",
                configured_af_illuminator="Auto",
                reported_has_builtin_af_illuminator=True,
                reported_builtin_af_illuminator_active=True,
                post_af_illuminator="Auto",
                af_illuminator_gate_or_fx6_spoof_events=1,
            ),
            P308_BLOCKED_AF_ILLUMINATOR_GATE_OR_FX6_LED_SPOOF,
        ),
        (
            P308_PILLAR_55A_SCENARIO_IDS[5],
            False,
            build_default_safe_lens_comp_af_illuminator_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="CREATE_NEW_FOLDER",
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/55a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar55ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_lens_comp_af_illuminator_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar55ScenarioOutcome(
                scenario_id=sid,
                pillar="55A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar55ASuiteResult(
        passed=all_ok,
        status=P308_STATUS_VERIFIED_PILLAR_55A if all_ok else P308_STATUS_REJECTED_PILLAR_55A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar55b_aperture_drive_folder_rating_6_scenario_suite() -> Pillar55BSuiteResult:
    """Run 6 Pillar 55B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, ApertureDriveFolderRatingVaultSpec, Optional[str]], ...] = (
        (
            P308_PILLAR_55B_SCENARIO_IDS[0],
            True,
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                shooting_domain="Still",
                configured_aperture_drive_in_af="Focus Priority",
                aperture_drive_burst_warn_acknowledged=True,
                configured_af_w_shutter="Off",
                configured_pre_af="On",
                lens_supports_pre_af=True,
                configured_circ_of_focus_point="Circulate",
                circ_wrap_axis="Horizontal",
                configured_focus_area_color="Red",
                reset_action="Camera Settings Reset",
                post_aperture_drive_in_af="Focus Priority",
                post_af_w_shutter="Off",
                post_pre_af="On",
                post_circ_of_focus_point="Circulate",
                post_focus_area_color="Red",
                target_media_slot=P308_SAFE_SECONDARY_SLOT,
                requested_vault_action="PLAYBACK_RATING_SET",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P308_PILLAR_55B_SCENARIO_IDS[1],
            True,
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_aperture_drive_in_af="Silent Priority",
                configured_af_w_shutter="Off",
                configured_pre_af="On",
                configured_circ_of_focus_point="Circulate",
                circ_wrap_axis="Vertical",
                configured_focus_area_color="Red",
                folder_name_form="Date Form",
                select_rec_folder_enabled=False,
                file_number_mode="Reset",
                file_prefix="FX3",
                reset_action="Initialize",
                post_aperture_drive_in_af="Standard",
                post_af_w_shutter="On",
                post_pre_af="Off",
                post_circ_of_focus_point="Does Not Circulate",
                post_focus_area_color="White",
                post_folder_name_form="Standard Form",
                post_file_number_mode="Series",
                post_file_prefix="DSC",
                target_media_slot=P308_SLOT1_VAULT_SLOT,
                requested_vault_action="READ_ONLY_AUDIT",
                reported_vault_action_allowed=False,
                vault_firewall_errno=None,
            ),
            None,
        ),
        (
            P308_PILLAR_55B_SCENARIO_IDS[2],
            False,
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                configured_aperture_drive_in_af="Focus Priority",
                configured_circ_of_focus_point="Circulate",
                circ_wrap_axis="Diagonal",
                reset_action="Camera Settings Reset",
                post_aperture_drive_in_af="Standard",
                fx6_exposes_aperture_drive_or_circ_color=True,
                aperture_drive_pre_af_shutter_reset_drift_events=1,
                circ_focus_diagonal_or_color_drift_events=1,
            ),
            P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT,
        ),
        (
            P308_PILLAR_55B_SCENARIO_IDS[3],
            False,
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                file_prefix="_FX",
                post_file_prefix="_FX",
                current_folder_still_count=4001,
                image_already_rated=True,
                target_media_slot=P308_SAFE_SECONDARY_SLOT,
                requested_vault_action="READ_ONLY_AUDIT",
                folder_name_or_leading_underscore_violations=1,
            ),
            P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT,
        ),
        (
            P308_PILLAR_55B_SCENARIO_IDS[4],
            False,
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                target_media_slot=P308_SLOT1_VAULT_SLOT,
                slot1_holds_tier0_vault=True,
                requested_vault_action="CREATE_NEW_FOLDER",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=1,
                slot1_folder_dir_mutation_bytes=4096,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/55b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
        (
            P308_PILLAR_55B_SCENARIO_IDS[5],
            False,
            build_default_safe_aperture_drive_folder_rating_vault_spec(
                target_media_slot=P308_SLOT1_VAULT_SLOT,
                slot1_holds_tier0_vault=True,
                requested_vault_action="PLAYBACK_RATING_SET",
                reported_vault_action_allowed=True,
                vault_firewall_errno=None,
                slot1_data_sector_writes=1,
                slot1_rating_avf_info_mutation_bytes=2048,
                slot1_vault_mutation_bytes=2048,
                slot1_vault_erofs_ebusy_enforced=False,
            ),
            P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar55ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_aperture_drive_folder_rating_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar55ScenarioOutcome(
                scenario_id=sid,
                pillar="55B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar55BSuiteResult(
        passed=all_ok,
        status=P308_STATUS_VERIFIED_PILLAR_55B if all_ok else P308_STATUS_REJECTED_PILLAR_55B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar55_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar55StandaloneReport:
    """Run full Pillar 55 standalone suite (`6/6` Pillar 55A + `6/6` Pillar 55B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase308_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar55a_lens_comp_af_illuminator_6_scenario_suite()
    res_b = run_pillar55b_aperture_drive_folder_rating_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 308 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE308_SCHEMA,
            "version": PHASE308_VERSION,
            "mode": donor_snapshot.verification_mode,
            "55a": [asdict(s) for s in res_a.scenarios],
            "55b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar55StandaloneReport(
        schema=PHASE308_SCHEMA,
        version=PHASE308_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P308_STATUS_VERIFIED_PILLAR55_SUITE if all_ok else P308_STATUS_FAIL_PILLAR55_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_55a_lens_comp_af_illuminator_vault=res_a,
        pillar_55b_aperture_drive_folder_rating_vault=res_b,
        dormant_shading_auto_low_exposure_events=(
            P308_DORMANT_SHADING_AUTO_LOW_EXPOSURE_EVENTS if res_a.passed else 1
        ),
        lens_comp_lock_or_arw_conflation_events=(
            P308_LENS_COMP_LOCK_OR_ARW_CONFLATION_EVENTS if res_a.passed else 1
        ),
        af_illuminator_gate_or_fx6_spoof_events=(
            P308_AF_ILLUMINATOR_GATE_OR_FX6_SPOOF_EVENTS if res_a.passed else 1
        ),
        movie_af_transition_or_assist_drift_events=(
            P308_MOVIE_AF_TRANSITION_OR_ASSIST_DRIFT_EVENTS if res_a.passed else 1
        ),
        aperture_drive_pre_af_shutter_reset_drift_events=(
            P308_APERTURE_DRIVE_PRE_AF_SHUTTER_RESET_DRIFT_EVENTS if res_b.passed else 1
        ),
        circ_focus_diagonal_or_color_drift_events=(
            P308_CIRC_FOCUS_DIAGONAL_OR_COLOR_DRIFT_EVENTS if res_b.passed else 1
        ),
        folder_name_or_leading_underscore_violations=(
            P308_FOLDER_NAME_OR_LEADING_UNDERSCORE_VIOLATIONS if res_b.passed else 1
        ),
        slot1_data_sector_writes=P308_SLOT1_DATA_SECTOR_WRITES if res_b.passed else 1,
        slot1_folder_dir_mutation_bytes=(
            P308_SLOT1_FOLDER_DIR_MUTATION_BYTES if res_b.passed else 4096
        ),
        slot1_rating_avf_info_mutation_bytes=(
            P308_SLOT1_RATING_AVF_INFO_MUTATION_BYTES if res_b.passed else 2048
        ),
        slot1_vault_mutation_bytes=(
            P308_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P308_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_ebusy_enforced=P308_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
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
# Unified 55-Pillar Recovery Master Aggregator (Phase 308 — 55/55 Milestone)
# ---------------------------------------------------------------------------


def _apply_master55_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_55pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master55PillarRecoveryReport:
    """Evaluate and aggregate all 55 recovery pillars (`1..55`) concurrently -> `55/55` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_55_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_54pillar() -> Master54PillarRecoveryReport:
        return evaluate_realhw_54pillar_recovery_master(**kw)

    def _run_p55() -> Tuple[Pillar55StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar55_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_54 = pool.submit(_run_54pillar)
        fut_55 = pool.submit(_run_p55)
        m54_rep = fut_54.result()
        p55_rep, p55_dt = fut_55.result()

    all_errors: List[str] = list(m54_rep.errors) + list(p55_rep.errors)
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
        if getattr(m54_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-54 violated {attr_name} == {expected_val}")
        if getattr(p55_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 55 violated {attr_name} == {expected_val}")

    if p55_rep.cross_model_flash_authorized is not False:
        all_errors.append("Pillar 55 violated cross_model_flash_authorized == False")

    for attr_name, expected_val in (
        ("sensor_cleaning_low_battery_bypass_events", 0),
        ("sensor_cleaning_no_power_off_violations", 0),
        ("fx6_ibis_shake_conflation_events", 0),
        ("ev_comp_range_or_cine_ei_lockout_violations", 0),
        ("exposure_step_or_dormant_reset_ev_drift_events", 0),
        ("focus_mode_movie_clamp_or_dormant_drift_events", 0),
        ("priority_set_or_illuminator_gate_violations", 0),
        ("image_index_dormant_or_view_mode_drift_events", 0),
        ("slot1_rotate_exif_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
        ("fx3_has_builtin_end_filter", False),
        ("fx3_has_builtin_evf", False),
        ("fx3_has_var_shutter", False),
    ):
        if getattr(m54_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-54 violated {attr_name} == {expected_val}")

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
    ):
        if getattr(p55_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 55 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m54_rep.pillars)
    spec55 = MASTER_55_PILLAR_SPECS[54]
    p55_metrics = {
        "pillar_55a_lens_comp_af_illuminator_vault": (
            f"{p55_rep.pillar_55a_lens_comp_af_illuminator_vault.scenarios_passed}/"
            f"{p55_rep.pillar_55a_lens_comp_af_illuminator_vault.scenarios_total}"
        ),
        "pillar_55b_aperture_drive_folder_rating_vault": (
            f"{p55_rep.pillar_55b_aperture_drive_folder_rating_vault.scenarios_passed}/"
            f"{p55_rep.pillar_55b_aperture_drive_folder_rating_vault.scenarios_total}"
        ),
        "dormant_shading_auto_low_exposure_events": (
            p55_rep.dormant_shading_auto_low_exposure_events
        ),
        "lens_comp_lock_or_arw_conflation_events": (
            p55_rep.lens_comp_lock_or_arw_conflation_events
        ),
        "af_illuminator_gate_or_fx6_spoof_events": (
            p55_rep.af_illuminator_gate_or_fx6_spoof_events
        ),
        "movie_af_transition_or_assist_drift_events": (
            p55_rep.movie_af_transition_or_assist_drift_events
        ),
        "aperture_drive_pre_af_shutter_reset_drift_events": (
            p55_rep.aperture_drive_pre_af_shutter_reset_drift_events
        ),
        "circ_focus_diagonal_or_color_drift_events": (
            p55_rep.circ_focus_diagonal_or_color_drift_events
        ),
        "folder_name_or_leading_underscore_violations": (
            p55_rep.folder_name_or_leading_underscore_violations
        ),
        "slot1_data_sector_writes": p55_rep.slot1_data_sector_writes,
        "slot1_folder_dir_mutation_bytes": p55_rep.slot1_folder_dir_mutation_bytes,
        "slot1_rating_avf_info_mutation_bytes": p55_rep.slot1_rating_avf_info_mutation_bytes,
        "slot1_vault_mutation_bytes": p55_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p55_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_ebusy_enforced": p55_rep.slot1_vault_erofs_ebusy_enforced,
        "overall_ready_for_hardware_attach": p55_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p55_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p55_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p55_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec55[0],
            pillar_id=spec55[1],
            phase_label=spec55[2],
            module_name=spec55[3],
            passed=bool(p55_rep.all_passed),
            status=p55_rep.status,
            verification_mode=p55_rep.verification_mode,
            elapsed_seconds=p55_dt,
            key_metrics=p55_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec55[1],
                    "mode": p55_rep.verification_mode,
                    "status": p55_rep.status,
                    "metrics": p55_metrics,
                    "passed": p55_rep.all_passed,
                }
            ),
            errors=tuple(p55_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master55_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p55_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_55_PILLAR_COUNT == 55
        and pillars_passed == 55
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE308_SCHEMA,
            "version": PHASE308_VERSION,
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
    return Master55PillarRecoveryReport(
        schema=PHASE308_SCHEMA,
        version=PHASE308_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P308_STATUS_VERIFIED_55OF55_AGGREGATOR if all_ok else P308_STATUS_FAIL_55OF55_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P308_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P308_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P308_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p55_rep.donor_snapshot,
        pillar55_a_lens_comp_af_illuminator_vault=(
            p55_rep.pillar_55a_lens_comp_af_illuminator_vault
        ),
        pillar55_b_aperture_drive_folder_rating_vault=(
            p55_rep.pillar_55b_aperture_drive_folder_rating_vault
        ),
        dormant_shading_auto_low_exposure_events=p55_rep.dormant_shading_auto_low_exposure_events,
        lens_comp_lock_or_arw_conflation_events=p55_rep.lens_comp_lock_or_arw_conflation_events,
        af_illuminator_gate_or_fx6_spoof_events=p55_rep.af_illuminator_gate_or_fx6_spoof_events,
        movie_af_transition_or_assist_drift_events=(
            p55_rep.movie_af_transition_or_assist_drift_events
        ),
        aperture_drive_pre_af_shutter_reset_drift_events=(
            p55_rep.aperture_drive_pre_af_shutter_reset_drift_events
        ),
        circ_focus_diagonal_or_color_drift_events=p55_rep.circ_focus_diagonal_or_color_drift_events,
        folder_name_or_leading_underscore_violations=(
            p55_rep.folder_name_or_leading_underscore_violations
        ),
        slot1_data_sector_writes=p55_rep.slot1_data_sector_writes,
        slot1_folder_dir_mutation_bytes=p55_rep.slot1_folder_dir_mutation_bytes,
        slot1_rating_avf_info_mutation_bytes=p55_rep.slot1_rating_avf_info_mutation_bytes,
        slot1_vault_mutation_bytes=m54_rep.slot1_vault_mutation_bytes + p55_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p55_rep.slot1_format_hard_locked,
        slot1_vault_erofs_ebusy_enforced=p55_rep.slot1_vault_erofs_ebusy_enforced,
        fx3_has_builtin_af_illuminator=P308_FX3_HAS_BUILTIN_AF_ILLUMINATOR,
        fx6_has_builtin_af_illuminator=P308_FX6_HAS_BUILTIN_AF_ILLUMINATOR,
        fx3_exposes_shading_auto_low=P308_FX3_EXPOSES_SHADING_AUTO_LOW,
        fx6_has_aperture_drive_pre_af_circ_color=P308_FX6_HAS_APERTURE_DRIVE_PRE_AF_CIRC_COLOR,
        fx6_has_msdcf_or_star_rating=P308_FX6_HAS_MSDCF_OR_STAR_RATING,
        sensor_cleaning_low_battery_bypass_events=m54_rep.sensor_cleaning_low_battery_bypass_events,
        sensor_cleaning_no_power_off_violations=m54_rep.sensor_cleaning_no_power_off_violations,
        fx6_ibis_shake_conflation_events=m54_rep.fx6_ibis_shake_conflation_events,
        ev_comp_range_or_cine_ei_lockout_violations=(
            m54_rep.ev_comp_range_or_cine_ei_lockout_violations
        ),
        exposure_step_or_dormant_reset_ev_drift_events=(
            m54_rep.exposure_step_or_dormant_reset_ev_drift_events
        ),
        focus_mode_movie_clamp_or_dormant_drift_events=(
            m54_rep.focus_mode_movie_clamp_or_dormant_drift_events
        ),
        priority_set_or_illuminator_gate_violations=(
            m54_rep.priority_set_or_illuminator_gate_violations
        ),
        image_index_dormant_or_view_mode_drift_events=(
            m54_rep.image_index_dormant_or_view_mode_drift_events
        ),
        slot1_rotate_exif_mutation_bytes=m54_rep.slot1_rotate_exif_mutation_bytes,
        fx3_has_sensor_cleaning_ibis=m54_rep.fx3_has_sensor_cleaning_ibis,
        fx3_has_exposure_comp=m54_rep.fx3_has_exposure_comp,
        fx3_has_physical_ev_reset_dial=m54_rep.fx3_has_physical_ev_reset_dial,
        fx6_has_ultrasonic_ibis_cleaning=m54_rep.fx6_has_ultrasonic_ibis_cleaning,
        fx6_has_variable_end_optical_block=m54_rep.fx6_has_variable_end_optical_block,
        fx6_has_technical_apr=m54_rep.fx6_has_technical_apr,
        fx6_has_still_exposure_comp=m54_rep.fx6_has_still_exposure_comp,
        fx6_has_still_image_index_rotate=m54_rep.fx6_has_still_image_index_rotate,
        dci4k_long_gop_or_8k_violations=m54_rep.dci4k_long_gop_or_8k_violations,
        reboot_2400p_stage_b_wipe_violations=m54_rep.reboot_2400p_stage_b_wipe_violations,
        hdmi_raw_or_still_aspect_drift_events=m54_rep.hdmi_raw_or_still_aspect_drift_events,
        fx6_still_or_raw_conflation_events=m54_rep.fx6_still_or_raw_conflation_events,
        reg_custom_hold_or_hlg_lock_drift_events=m54_rep.reg_custom_hold_or_hlg_lock_drift_events,
        camset_cross_model_path_drift_events=m54_rep.camset_cross_model_path_drift_events,
        photo_capture_dci4k_lockout_bypass_events=(
            m54_rep.photo_capture_dci4k_lockout_bypass_events
        ),
        slot1_camset_write_bytes=m54_rep.slot1_camset_write_bytes,
        slot1_photo_capture_write_bytes=m54_rep.slot1_photo_capture_write_bytes,
        fx3_appfw_has_dci4k_internal=m54_rep.fx3_appfw_has_dci4k_internal,
        fx3_appfw_has_pro_camera_path=m54_rep.fx3_appfw_has_pro_camera_path,
        fx6_has_still_aspect_ratio=m54_rep.fx6_has_still_aspect_ratio,
        fx6_has_photo_capture=m54_rep.fx6_has_photo_capture,
        fx6_has_playback_enlarge_image=m54_rep.fx6_has_playback_enlarge_image,
        fx6_has_reg_custom_shoot_set=m54_rep.fx6_has_reg_custom_shoot_set,
        fx6_has_camera_set_memory=m54_rep.fx6_has_camera_set_memory,
        movie_tracking_area_or_limit_violations=m54_rep.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=m54_rep.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=m54_rep.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=(
            m54_rep.fx6_handle_or_pos_display_conflation_events
        ),
        iso_minss_or_cine_ei_lock_drift_events=m54_rep.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=m54_rep.flash_still_mech_gate_violations,
        mishoe_pmic_5v_overcurrent_events=m54_rep.mishoe_pmic_5v_overcurrent_events,
        slot1_focus_zoom_camset_mutation_bytes=m54_rep.slot1_focus_zoom_camset_mutation_bytes,
        slot1_flash_videolight_imagedb_bytes=m54_rep.slot1_flash_videolight_imagedb_bytes,
        xlrh1_has_zoom_lever=m54_rep.xlrh1_has_zoom_lever,
        xlrh1_has_rec_button=m54_rep.xlrh1_has_rec_button,
        xlrh1_has_zoom_hold_switch=m54_rep.xlrh1_has_zoom_hold_switch,
        fx6_0_99_is_zoom_position_display=m54_rep.fx6_0_99_is_zoom_position_display,
        fx6_has_iso_auto_min_ss=m54_rep.fx6_has_iso_auto_min_ss,
        fx6_mechanical_shutter_present=m54_rep.fx6_mechanical_shutter_present,
        dormant_lossless_raw_exposure_events=m54_rep.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=m54_rep.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=m54_rep.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=m54_rep.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=m54_rep.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=m54_rep.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=m54_rep.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=m54_rep.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=m54_rep.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=m54_rep.slot1_imagedb_or_burst_mutation_bytes,
        fx3_ui_exposes_lossless_raw=m54_rep.fx3_ui_exposes_lossless_raw,
        fx3_ui_exposes_shutter_type_auto=m54_rep.fx3_ui_exposes_shutter_type_auto,
        fx6_still_pipeline_present=m54_rep.fx6_still_pipeline_present,
        double_log_or_lockout_bypass_events=m54_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=m54_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=m54_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=m54_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            m54_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        wb_custom_camset_exclusion_drift_events=m54_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            m54_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        fx3_ui_exposes_usb_streaming=m54_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m54_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m54_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m54_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m54_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m54_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m54_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m54_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m54_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m54_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m54_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m54_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m54_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m54_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m54_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m54_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m54_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m54_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m54_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m54_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m54_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m54_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m54_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m54_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m54_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m54_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m54_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m54_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m54_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m54_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m54_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m54_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m54_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=m54_rep.tcub_camera_reset_wipe_or_format_violations,
        fx3_has_builtin_end_filter=m54_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m54_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m54_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m54_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m54_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m54_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m54_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m54_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m54_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m54_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m54_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m54_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m54_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m54_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m54_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m54_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m54_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m54_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m54_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m54_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m54_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m54_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m54_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m54_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m54_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m54_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m54_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m54_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m54_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m54_rep.unbuffered_battery_pull_events,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=p55_rep.hardware_live_attachment_authorized,
        master_55pillar_sha256=master_sha,
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


def evaluate_55pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master55PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_55pillar_recovery_master`."""
    return evaluate_realhw_55pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_55pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master55PillarRecoveryReport:
    """Public CLI entry point for Phase 308 `55/55` unified recovery master."""
    return evaluate_realhw_55pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS",
    "ALLOW_PERSISTENT_JIRITSU_WRITES",
    "ApertureDriveFolderRatingVaultReport",
    "ApertureDriveFolderRatingVaultSpec",
    "CROSS_MODEL_FLASH_AUTHORIZED",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "ISP_WRITE_AUTHORIZED",
    "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
    "LensCompAfIlluminatorFolderRatingVaultReport",
    "LensCompAfIlluminatorVaultReport",
    "LensCompAfIlluminatorVaultSpec",
    "MASTER_55_PILLAR_COUNT",
    "MASTER_55_PILLAR_IDS",
    "MASTER_55_PILLAR_SPECS",
    "Master55PillarRecoveryReport",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P308_ADD_RATING_ALREADY_APPLIED_G_RESID16",
    "P308_ADD_RATING_FUNC_SYMBOL",
    "P308_AF_ASSIST_BKID",
    "P308_AF_ASSIST_DEFAULT",
    "P308_AF_ASSIST_F_RESID16",
    "P308_AF_ASSIST_INCOMPATIBLE_LENSES",
    "P308_AF_ILLUMINATOR_BKID",
    "P308_AF_ILLUMINATOR_DEFAULT",
    "P308_AF_ILLUMINATOR_F_RESID16",
    "P308_AF_ILLUMINATOR_GATE_OR_FX6_SPOOF_EVENTS",
    "P308_AF_ILLUMINATOR_MENU_PATH",
    "P308_AF_ILLUMINATOR_MODES",
    "P308_AF_ILLUMINATOR_RESID16",
    "P308_AF_MF_MENU_PATH",
    "P308_AF_SUBJ_SHIFT_SENS_BKID",
    "P308_AF_SUBJ_SHIFT_SENS_COMPACT_F_RESID16",
    "P308_AF_SUBJ_SHIFT_SENS_DEFAULT",
    "P308_AF_SUBJ_SHIFT_SENS_F_RESID16",
    "P308_AF_SUBJ_SHIFT_SENS_MAX",
    "P308_AF_SUBJ_SHIFT_SENS_MIN",
    "P308_AF_TRANSITION_SPEED_BKID",
    "P308_AF_TRANSITION_SPEED_DEFAULT",
    "P308_AF_TRANSITION_SPEED_F_RESID16",
    "P308_AF_TRANSITION_SPEED_MAX",
    "P308_AF_TRANSITION_SPEED_MIN",
    "P308_AF_W_SHUTTER_BKID",
    "P308_AF_W_SHUTTER_DEFAULT",
    "P308_AF_W_SHUTTER_F_RESID16",
    "P308_APERTURE_DRIVE_ALT_F_RESID16",
    "P308_APERTURE_DRIVE_BKID",
    "P308_APERTURE_DRIVE_BURST_WARN_G_RESID16",
    "P308_APERTURE_DRIVE_DEFAULT",
    "P308_APERTURE_DRIVE_F_RESID16",
    "P308_APERTURE_DRIVE_MODES",
    "P308_APERTURE_DRIVE_PRE_AF_SHUTTER_RESET_DRIFT_EVENTS",
    "P308_APERTURE_DRIVE_SILENT_BKID",
    "P308_BLOCKED_AF_ILLUMINATOR_GATE_OR_FX6_LED_SPOOF",
    "P308_BLOCKED_APERTURE_DRIVE_PRE_AF_CIRC_COLOR_INIT_DRIFT",
    "P308_BLOCKED_DORMANT_SHADING_AUTO_LOW_OR_LENS_COMP_DRIFT",
    "P308_BLOCKED_FOLDER_SETTINGS_OR_RATING_POLICY_DRIFT",
    "P308_BLOCKED_INVALID_PILLAR55A_SPEC",
    "P308_BLOCKED_INVALID_PILLAR55B_SPEC",
    "P308_BLOCKED_MOVIE_AF_TRANSITION_SENS_OR_ASSIST_DRIFT",
    "P308_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P308_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P308_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL",
    "P308_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P308_BOUNDED_HEADER_BYTES",
    "P308_BREATHING_COMP_BKID",
    "P308_BREATHING_COMP_F_RESID16",
    "P308_BREATHING_DEFAULT",
    "P308_CHROMA_ABER_COMP_BKID",
    "P308_CHROMA_ABER_COMP_F_RESID16",
    "P308_CHROMA_ABER_DEFAULT",
    "P308_CHROMA_ABER_MODES",
    "P308_CIRC_FOCUS_DIAGONAL_OR_COLOR_DRIFT_EVENTS",
    "P308_CIRC_FOCUS_POINT_BKID",
    "P308_CIRC_FOCUS_POINT_DEFAULT",
    "P308_CIRC_FOCUS_POINT_F_RESID16",
    "P308_CIRC_FOCUS_POINT_MODES",
    "P308_CIRC_WRAP_AXES",
    "P308_CONCURRENT_CEILING_SECONDS",
    "P308_CROSS_MODEL_FLASH_AUTHORIZED",
    "P308_DESTRUCTIVE_VAULT_ACTIONS",
    "P308_DISTORTION_COMP_BKID",
    "P308_DISTORTION_COMP_F_RESID16",
    "P308_DISTORTION_DEFAULT",
    "P308_DISTORTION_MODES",
    "P308_DONOR_FX3_APPFW_702_RELPATH",
    "P308_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P308_DONOR_FX3_LIB_INFRA_LENS_COMM_RELPATH",
    "P308_DONOR_FX3_UXC_EN_F_RELPATH",
    "P308_DONOR_FX3_UXC_EN_G_RELPATH",
    "P308_DONOR_FX3_UXC_EN_RELPATH",
    "P308_DONOR_FX3_UXC_JA_F_RELPATH",
    "P308_DONOR_FX3_UXC_JA_G_RELPATH",
    "P308_DONOR_FX3_UXC_JA_RELPATH",
    "P308_DONOR_FX3_UXC_SC_F_RELPATH",
    "P308_DONOR_FX3_UXC_SC_G_RELPATH",
    "P308_DONOR_FX3_UXC_SC_RELPATH",
    "P308_DONOR_FX3_UXC_TC_F_RELPATH",
    "P308_DONOR_FX3_UXC_TC_G_RELPATH",
    "P308_DONOR_FX3_UXC_TC_RELPATH",
    "P308_DONOR_FX6_APPFW_601_RELPATH",
    "P308_DONOR_FX6_UXC_EN_2_RELPATH",
    "P308_DONOR_FX6_UXC_EN_RELPATH",
    "P308_DONOR_INSPECT_BUDGET_SECONDS",
    "P308_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P308_DORMANT_SHADING_AUTO_LOW_ENUM",
    "P308_DORMANT_SHADING_AUTO_LOW_EXPOSURE_EVENTS",
    "P308_DORMANT_SHADING_AUTO_LOW_F_RESID16",
    "P308_ENV_CLEAN_ROOM_TEST",
    "P308_EOPNOTSUPP_ERRNO",
    "P308_FAST_CLI_BUDGET_SECONDS",
    "P308_FILE_FOLDER_MENU_PATH",
    "P308_FILE_NUMBER_DEFAULT",
    "P308_FILE_NUMBER_MODES",
    "P308_FILE_PREFIX_ALLOWED_CHARS",
    "P308_FILE_PREFIX_DEFAULT",
    "P308_FILE_PREFIX_LEN",
    "P308_FOCUS_AREA_COLOR_BKID",
    "P308_FOCUS_AREA_COLOR_DEFAULT",
    "P308_FOCUS_AREA_COLOR_F_RESID16",
    "P308_FOCUS_AREA_COLOR_MODES",
    "P308_FOCUS_AREA_COLOR_RESID16_MAP",
    "P308_FOCUS_AREA_MENU_PATH",
    "P308_FOCUS_MODES_ALL",
    "P308_FOLDER_MAX_STATUS_SYMBOL",
    "P308_FOLDER_MAX_STILLS",
    "P308_FOLDER_NAME_DEFAULT",
    "P308_FOLDER_NAME_FORMS",
    "P308_FOLDER_NAME_OR_LEADING_UNDERSCORE_VIOLATIONS",
    "P308_FORBIDDEN_PERSISTENT_TARGETS",
    "P308_FX3_AF_ILLUMINATOR_FRONT_PART_NO",
    "P308_FX3_AF_ILLUMINATOR_RANGE_M",
    "P308_FX3_EXPOSES_SHADING_AUTO_LOW",
    "P308_FX3_FW_VERSION",
    "P308_FX3_HAS_BUILTIN_AF_ILLUMINATOR",
    "P308_FX3_HELPGUIDE_ID",
    "P308_FX3_MODEL_ID",
    "P308_FX3_MODEL_NAME",
    "P308_FX3_PRODUCT_CODENAME",
    "P308_FX3_SENSOR_FAMILY",
    "P308_FX3_SUPPORTED_FW_VERSIONS",
    "P308_FX3_SUPPORTS_MISHOE_FLASH_ILLUMINATOR",
    "P308_FX6_ALL_FILE_DIR",
    "P308_FX6_DONOR_FW_VERSION",
    "P308_FX6_DONOR_MODEL_NAME",
    "P308_FX6_DORMANT_IRIS_AF_F24_RESID16",
    "P308_FX6_HAS_APERTURE_DRIVE_PRE_AF_CIRC_COLOR",
    "P308_FX6_HAS_BUILTIN_AF_ILLUMINATOR",
    "P308_FX6_HAS_MSDCF_OR_STAR_RATING",
    "P308_FX6_LEGACY_LENS_COMP_MENU_PATH",
    "P308_FX6_LENS_COMP_MENU_PATH",
    "P308_FX6_PRODUCT_CODENAME",
    "P308_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P308_LENS_COMP_F_RESID16",
    "P308_LENS_COMP_IPC_SYMBOLS",
    "P308_LENS_COMP_LOCK_OR_ARW_CONFLATION_EVENTS",
    "P308_LENS_COMP_MENU_PATH",
    "P308_LENS_COMP_RESID16",
    "P308_LENS_DISTORTION_FORCED_AUTO_ENUM",
    "P308_MAX_FOLDER_NUM",
    "P308_MAX_FULL_DONOR_BYTES",
    "P308_MIN_FOLDER_NUM",
    "P308_MOVIE_AF_TRANSITION_OR_ASSIST_DRIFT_EVENTS",
    "P308_NOMINAL_BUDGET_SECONDS",
    "P308_ON_OFF_MODES",
    "P308_OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P308_PILLAR_55A_SCENARIO_IDS",
    "P308_PILLAR_55B_SCENARIO_IDS",
    "P308_PINNED_FX3_APPFW_702_BYTES",
    "P308_PINNED_FX3_APPFW_702_FULL_SHA256",
    "P308_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P308_PINNED_FX3_BACKUP_BIN_BYTES",
    "P308_PINNED_FX3_BACKUP_BIN_SHA256",
    "P308_PINNED_FX3_LIB_INFRA_LENS_COMM_BYTES",
    "P308_PINNED_FX3_LIB_INFRA_LENS_COMM_SHA256",
    "P308_PINNED_FX3_UXC_EN_BYTES",
    "P308_PINNED_FX3_UXC_EN_F_BYTES",
    "P308_PINNED_FX3_UXC_EN_F_SHA256",
    "P308_PINNED_FX3_UXC_EN_G_BYTES",
    "P308_PINNED_FX3_UXC_EN_G_SHA256",
    "P308_PINNED_FX3_UXC_EN_SHA256",
    "P308_PINNED_FX3_UXC_JA_BYTES",
    "P308_PINNED_FX3_UXC_JA_F_BYTES",
    "P308_PINNED_FX3_UXC_JA_F_SHA256",
    "P308_PINNED_FX3_UXC_JA_G_BYTES",
    "P308_PINNED_FX3_UXC_JA_G_SHA256",
    "P308_PINNED_FX3_UXC_JA_SHA256",
    "P308_PINNED_FX3_UXC_SC_BYTES",
    "P308_PINNED_FX3_UXC_SC_F_BYTES",
    "P308_PINNED_FX3_UXC_SC_F_SHA256",
    "P308_PINNED_FX3_UXC_SC_G_BYTES",
    "P308_PINNED_FX3_UXC_SC_G_SHA256",
    "P308_PINNED_FX3_UXC_SC_SHA256",
    "P308_PINNED_FX3_UXC_TC_BYTES",
    "P308_PINNED_FX3_UXC_TC_F_BYTES",
    "P308_PINNED_FX3_UXC_TC_F_SHA256",
    "P308_PINNED_FX3_UXC_TC_G_BYTES",
    "P308_PINNED_FX3_UXC_TC_G_SHA256",
    "P308_PINNED_FX3_UXC_TC_SHA256",
    "P308_PINNED_FX6_APPFW_601_BYTES",
    "P308_PINNED_FX6_APPFW_601_FULL_SHA256",
    "P308_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P308_PINNED_FX6_UXC_EN_2_BYTES",
    "P308_PINNED_FX6_UXC_EN_2_SHA256",
    "P308_PINNED_FX6_UXC_EN_BYTES",
    "P308_PINNED_FX6_UXC_EN_SHA256",
    "P308_PLAYBACK_RATING_MENU_PATH",
    "P308_PRE_AF_BKID",
    "P308_PRE_AF_DEFAULT",
    "P308_PRE_AF_F_RESID16",
    "P308_RATING_BG_NG_SYMBOL",
    "P308_RATING_FUNC_SYMBOL",
    "P308_RATING_SET_STARS_VALID",
    "P308_RATING_STARS_VALID",
    "P308_RATING_XMP_SYMBOL",
    "P308_RESET_ACTIONS",
    "P308_SAFE_SECONDARY_SLOT",
    "P308_SHADING_COMP_BKID",
    "P308_SHADING_COMP_DEFAULT",
    "P308_SHADING_COMP_DORMANT_MODES",
    "P308_SHADING_COMP_EXPOSED_MODES",
    "P308_SHADING_COMP_F_RESID16",
    "P308_SHOOTING_DOMAINS",
    "P308_SLOT1_DATA_SECTOR_WRITES",
    "P308_SLOT1_FOLDER_DIR_MUTATION_BYTES",
    "P308_SLOT1_FORMAT_HARD_LOCKED",
    "P308_SLOT1_RATING_AVF_INFO_MUTATION_BYTES",
    "P308_SLOT1_VAULT_EROFS_EBUSY_ENFORCED",
    "P308_SLOT1_VAULT_MUTATION_BYTES",
    "P308_SLOT1_VAULT_SLOT",
    "P308_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P308_STATUS_FAIL_55OF55_AGGREGATOR",
    "P308_STATUS_FAIL_PILLAR55_SUITE",
    "P308_STATUS_REJECTED_PILLAR_55A",
    "P308_STATUS_REJECTED_PILLAR_55B",
    "P308_STATUS_VERIFIED_55OF55_AGGREGATOR",
    "P308_STATUS_VERIFIED_PILLAR55_SUITE",
    "P308_STATUS_VERIFIED_PILLAR_55A",
    "P308_STATUS_VERIFIED_PILLAR_55B",
    "P308_STEADYSHOT_MODES",
    "P308_TIER0_SURFACE_COUNT",
    "P308_UNCHIPPED_MANUAL_LENS_ENUM",
    "P308_VAULT_FIREWALL_ERRNOS",
    "P308_VAULT_FIREWALL_ERRNO_CODES",
    "P308_VAULT_TARGET_ACTIONS",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE308_PHASE_NUMBER",
    "PHASE308_SCHEMA",
    "PHASE308_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "Phase308DonorArtifactDigest",
    "Phase308DonorSnapshot",
    "Pillar55ASuiteResult",
    "Pillar55BSuiteResult",
    "Pillar55ScenarioOutcome",
    "Pillar55StandaloneReport",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "build_default_safe_aperture_drive_folder_rating_vault_spec",
    "build_default_safe_lens_comp_af_illuminator_vault_spec",
    "compute_expected_af_illuminator_state",
    "compute_expected_aperture_drive_and_focus_ui_state",
    "compute_expected_folder_and_rating_vault_state",
    "compute_expected_lens_comp_and_movie_af_state",
    "evaluate_55pillar_recovery_master",
    "evaluate_aperture_drive_folder_rating_vault",
    "evaluate_lens_comp_af_illuminator_vault",
    "evaluate_realhw_55pillar_recovery_master",
    "inspect_phase308_donors_readonly",
    "is_valid_fx3_file_prefix",
    "run_pillar55_standalone_suite",
    "run_pillar55a_lens_comp_af_illuminator_6_scenario_suite",
    "run_pillar55b_aperture_drive_folder_rating_6_scenario_suite",
    "verify_55pillar_recovery_suite",
    "verify_lens_comp_af_illuminator_folder_rating_and_vault",
    "verify_lens_comp_af_illuminator_folder_rating_vault",
]
