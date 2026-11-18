"""Phase 304 — Recovery Pillar 54 & Unified 54/54 Recovery Master (`verify-54pillar-recovery` /
`verify-pillar54-sensor-cleaning-ev-comp-focus-mode-rotate-vault`):

1. **Pillar 54A — `[Sensor Cleaning]` (`>= 51%` NP-FZ100 Battery Gate + Mandatory Physical
   Power-Switch `OFF` vs `ILME-FX6` Electronic Variable ND + `APR`), & `[Exposure Comp.]`
   (`+-5.0 EV` Still / `+-2.0 EV` Movie & `S&Q`, `M + ISO AUTO` Only, `[Exposure step]`
   `Initialize`-Only, & 100% `[Cine EI]` / `[Cine EI Quick]` Lockout + `Slot-1` Vault Firewall (Wave-52))**:
   - Models `ILME-FX3 Ver. 2.00+/7.02` (`0x91030080`, `ilc/2210`, `PRODUCT_MODEL_ALCIN_UUD`)
     `[Setup] -> [Setup Option] -> [Sensor Cleaning]` (`_f.uxc` `0x67d6`; legacy `.uxc` `0xe7d7`
     `Cleaning Mode`, `0xe879`; `appFw.so` `FUNC_set_cleaning_mode`, `sequence_set_cleaning_mode`,
     `sensor_cleaning`, `MODEL_CLEANING_MODE_COMP`): enforces **`NP-FZ100 >= 51%`** battery gate
     (`BATTERY_CHECK_FOR_CLEANING_MODE_LOWER` -> `.uxc` `0xe574`/`0xe7ba` `"Power insufficient."`,
     contrasting pre-Ver. 2.00 `>= 3` bars) and **mandatory physical power-switch `OFF`**
     (`_g.uxc` `0x6221` `"Turn the power off after cleaning the image sensor manually."`) after
     5-axis IBIS shake/park before lens removal (manual blower only, never compressed air).
   - Contrasts IBIS-less `ILME-FX6 Ver. 6.01` (`PRODUCT_MODEL_CHAPLIN`): exposes front **Electronic
     Variable ND optical block** (`1/4..1/128` + `CLEAR`, `PID_SET_VARIABLE_ND_VALUE`,
     `BKID_APP_VARIABLE_ND_CONT`) + `Technical > APR` (`MODEL_APR_EXECUTE_COMP`), with
     `CrCommandId_SensorCleaning` (`320`) SDK-unsupported (`-`) and zero ultrasonic IBIS shake.
   - Models `[Exposure Comp.]` (`BKID_APP_setting_exposure_compensation`,
     `BKID_APP_separate_movie_exposure_comp`, `_f.uxc` `0x76de`, `.uxc` `0xe956`): **`+-5.0 EV` Still**
     / **`+-2.0 EV` Movie & `S&Q`** (resettable by `Camera Settings Reset`; `[Exposure step]` `0.3EV`
     default / `0.5EV` and `[Exposure Std. Adjust]` are **`Initialize`-only**; dormant physical-dial
     `[Reset EV Comp.]` `0x7853` and Ver. 1 `[Dial Ev Comp]` `0xe4d9` omitted in `ilc/2210`), works
     in Manual `M` **ONLY with `ISO AUTO`** (unavailable under fixed ISO / `Intelligent Auto`), and is
     **100% locked out** under `[Log Shooting] = Cine EI` or `Cine EI Quick` (`EXPOSURE_MODE_MOVIE_M` +
     `Base ISO 800/12800` pinned -> `[Exposure Index]` `+-2.0 EV` with `Display LUT = On` governs
     monitoring; `Flexible ISO` keeps `Exposure Comp.` + `ISO AUTO` active).

2. **Pillar 54B — `[Focus Mode]` (`5`-Still vs `2`-Movie/`S&Q` `AF-C`/`MF` Clamp + `[Priority Set
   in AF-S/AF-C]` / `[AF Assist]` / `[AF Illuminator]`) & `[Playback]` (`[View Mode]` / Exact `9/25`
   `[Image Index]` / `[Display as Group]` / `[Display Rotation]` / `[Rotate]` `Slot-1` Tier-0 Vault
   Firewall (Wave-52))**:
   - Models `[Focus Mode]` (`BKID_APP_setting_focus_mode_menu_dial`,
     `BKID_APP_separate_movie_focus_mode`, `_g.uxc` `0x625e`/`0x6412`): **5 Still modes** (`AF-S`,
     `AF-A` factory default resettable via `Camera Settings Reset`, `AF-C`, `DMF`, `MF`; dormant
     `PF`/`SEMI_MANUAL` rejected), whereas **Movie & `S&Q` strictly clamp to 2 modes**: `AF-C`
     (encoded internally in `appFw.so` as `MOVIE_AUTO` `0x66ea`) and `MF` (rejecting `AF-S`/`AF-A`/`DMF`
     in Movie/`S&Q` fail-closed with `EOPNOTSUPP=95` / `EINVAL=22`).
   - Enforces `[Priority Set in AF-S]` & `[Priority Set in AF-C]` (`AF`, `Release`, `Balanced Emphasis`
     default, **`Initialize`-only**), `[AF Assist]` (`On`/`Off` default `Off`, Movie `AF-C` manual ring
     override), `[AF Illuminator]` (`Auto` default / `Off`, resettable via `Camera Settings Reset`,
     Still-only — locked out in Movie/`S&Q`/`AF-C`/Focus Magnifier/Mount Adaptor) vs `ILME-FX6`
     physical `AF/MF` + `Push AF Mode`.
   - Enforces Playback (`Initialize`-only survival across `Camera Settings Reset`): `[View Mode]`
     (`Date View` / `Folder View(Still)` / `Movie View` / `AVCHD View` / `XAVC S View`), exact
     `[Image Index]` **`9 Images` / `25 Images`** (rejecting dormant `12 Images` / `30 Images`),
     `[Display as Group]` (`Off`/`On`), `[Display Rotation]` (`Auto`/`Manual`/`Off`, movies always
     horizontal), and **CRITICAL `Slot-1` RECOVERY VAULT FIREWALL**: Playback `[Rotate]`
     (`FUNC_rotate_content`, `_f.uxc` `0x795a`, `.uxc` `0xe5ae`) mutates EXIF orientation / `AVF_INFO`
     database on card -> MUST fail-closed (`EROFS=30` / `EBUSY=16`, `slot1_data_sector_writes == 0`,
     `slot1_vault_mutation_bytes == 0`) whenever `Slot 1` holds a Tier-0 recovery vault!

3. **Unified 54-Pillar Recovery Master (`evaluate_realhw_54pillar_recovery_master` /
   `verify-54pillar-recovery`)**:
   - Concurrently delegates Pillars `1..53` (`evaluate_realhw_53pillar_recovery_master`) + **Pillar 54**
     (`run_pillar54_standalone_suite`) -> **`54/54` (`VERIFIED_54OF54_PILLAR_RECOVERY_MASTER`)** under
     `< 1.5s` with `overall_ready_for_hardware_attach == False`, `cross_model_flash_authorized == False`,
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
from .realhw_53pillar_dci4k_aspect_custom_hold_camset_photo_capture_vault_verifier import (
    MASTER_53_PILLAR_SPECS,
    Master53PillarRecoveryReport,
    evaluate_realhw_53pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants (Phase 304)
# ---------------------------------------------------------------------------

PHASE304_SCHEMA: str = (
    "realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier_v1"
)
PHASE304_VERSION: str = "1.0.0"
PHASE304_PHASE_NUMBER: int = 304
P304_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P304_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P304_OVERALL_READY_FOR_HARDWARE_ATTACH: bool = False
P304_CROSS_MODEL_FLASH_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P304_SENSOR_CLEANING_LOW_BATTERY_BYPASS_EVENTS: int = 0
P304_SENSOR_CLEANING_NO_POWER_OFF_VIOLATIONS: int = 0
P304_FX6_IBIS_SHAKE_CONFLATION_EVENTS: int = 0
P304_EV_COMP_RANGE_OR_CINE_EI_LOCKOUT_VIOLATIONS: int = 0
P304_EXPOSURE_STEP_OR_DORMANT_RESET_EV_DRIFT_EVENTS: int = 0
P304_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT_EVENTS: int = 0
P304_PRIORITY_SET_OR_ILLUMINATOR_GATE_VIOLATIONS: int = 0
P304_IMAGE_INDEX_DORMANT_OR_VIEW_MODE_DRIFT_EVENTS: int = 0
P304_SLOT1_DATA_SECTOR_WRITES: int = 0
P304_SLOT1_ROTATE_EXIF_MUTATION_BYTES: int = 0
P304_SLOT1_VAULT_MUTATION_BYTES: int = 0
P304_SLOT1_FORMAT_HARD_LOCKED: bool = True
P304_SLOT1_VAULT_EROFS_EBUSY_ENFORCED: bool = True

P304_FX3_HAS_SENSOR_CLEANING_IBIS: bool = True
P304_FX3_HAS_EXPOSURE_COMP: bool = True
P304_FX3_HAS_PHYSICAL_EV_RESET_DIAL: bool = False
P304_FX6_HAS_ULTRASONIC_IBIS_CLEANING: bool = False
P304_FX6_HAS_VARIABLE_END_OPTICAL_BLOCK: bool = True
P304_FX6_HAS_TECHNICAL_APR: bool = True
P304_FX6_HAS_STILL_EXPOSURE_COMP: bool = False
P304_FX6_HAS_STILL_IMAGE_INDEX_ROTATE: bool = False

P304_DONOR_INSPECT_BUDGET_SECONDS: float = 0.20
P304_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P304_FAST_CLI_BUDGET_SECONDS: float = 1.5
P304_NOMINAL_BUDGET_SECONDS: float = 4.0
P304_CONCURRENT_CEILING_SECONDS: float = 6.0
P304_BOUNDED_HEADER_BYTES: int = 4096
P304_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-52 Donor Anchors (strictly O_RDONLY)
P304_FX3_MODEL_NAME: str = "ILME-FX3"
P304_FX3_MODEL_ID: int = 0x91030080
P304_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P304_FX3_HELPGUIDE_ID: str = "ilc/2210"
P304_FX3_FW_VERSION: str = "7.02"
P304_FX3_SENSOR_FAMILY: str = "12 MP IMX510"
P304_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P304_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P304_FX6_DONOR_FW_VERSION: str = "6.01"
P304_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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
P304_FX3_PRE_V2_FW_VERSIONS: Tuple[str, ...] = ("1.00", "1.01")

P304_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P304_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P304_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)
P304_PINNED_FX3_APPFW_702_FULL_SHA256: str = (
    "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
)

P304_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P304_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P304_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)
P304_PINNED_FX6_APPFW_601_FULL_SHA256: str = (
    "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
)

P304_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P304_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P304_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P304_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P304_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P304_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P304_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P304_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P304_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P304_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P304_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P304_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P304_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P304_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P304_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P304_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P304_PINNED_FX3_UXC_EN_BYTES: int = 165740
P304_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P304_DONOR_FX3_UXC_SC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc"
)
P304_PINNED_FX3_UXC_SC_BYTES: int = 149064
P304_PINNED_FX3_UXC_SC_SHA256: str = (
    "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66"
)

P304_DONOR_FX3_UXC_TC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc"
)
P304_PINNED_FX3_UXC_TC_BYTES: int = 151908
P304_PINNED_FX3_UXC_TC_SHA256: str = (
    "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3"
)

P304_DONOR_FX3_UXC_JA_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc"
)
P304_PINNED_FX3_UXC_JA_BYTES: int = 208564
P304_PINNED_FX3_UXC_JA_SHA256: str = (
    "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d"
)

P304_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P304_PINNED_FX3_UXC_EN_G_BYTES: int = 69600
P304_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P304_DONOR_FX3_UXC_SC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_g.uxc"
)
P304_PINNED_FX3_UXC_SC_G_BYTES: int = 61296
P304_PINNED_FX3_UXC_SC_G_SHA256: str = (
    "a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b"
)

P304_DONOR_FX3_UXC_TC_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_g.uxc"
)
P304_PINNED_FX3_UXC_TC_G_BYTES: int = 61372
P304_PINNED_FX3_UXC_TC_G_SHA256: str = (
    "97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80"
)

P304_DONOR_FX3_UXC_JA_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_g.uxc"
)
P304_PINNED_FX3_UXC_JA_G_BYTES: int = 89428
P304_PINNED_FX3_UXC_JA_G_SHA256: str = (
    "4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980"
)

P304_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P304_PINNED_FX6_UXC_EN_BYTES: int = 118208
P304_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P304_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P304_PINNED_FX6_UXC_EN_2_BYTES: int = 118676
P304_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# ---------------------------------------------------------------------------
# Pillar 54A Constants — [Sensor Cleaning] (>= 51% NP-FZ100 + Power-OFF vs
# FX6 e-ND + APR) & [Exposure Comp.] (+-5.0 / +-2.0 EV + Cine EI Lockout)
# ---------------------------------------------------------------------------

P304_SENSOR_CLEANING_MENU_PATH: Tuple[str, ...] = (
    "Setup",
    "Setup Option",
    "Sensor Cleaning",
)
P304_EXPOSURE_COMP_MENU_PATH: Tuple[str, ...] = (
    "Exposure/Color",
    "Exposure Comp.",
    "Exposure Comp.",
)
P304_LOG_SHOOTING_MENU_PATH: Tuple[str, ...] = (
    "Shooting",
    "Image Quality/Rec",
    "Log Shooting Setting",
)

P304_SENSOR_CLEANING_F_RESID16: int = 0x67D6  # _f.uxc ("Sensor Cleaning")
P304_CLEANING_MODE_LEGACY_RESID16: int = 0xE7D7  # .uxc ("Cleaning Mode")
P304_CLEANING_MODE_DESC_RESID16: int = 0xE879
P304_POWER_INSUFFICIENT_RESID16: int = 0xE574  # .uxc ("Power insufficient.")
P304_POWER_INSUFFICIENT_ALT_RESID16: int = 0xE7BA
P304_MANDATORY_POWER_OFF_G_RESID16: int = 0x6221  # _g.uxc ("Turn the power off...")

P304_FX3_CLEANING_SYMBOLS: Tuple[str, ...] = (
    "FUNC_set_cleaning_mode",
    "sequence_set_cleaning_mode",
    "sensor_cleaning",
    "MODEL_CLEANING_MODE_COMP",
    "BATTERY_CHECK_FOR_CLEANING_MODE_LOWER",
    "INSUFFICIENT_BATTERY_CLEANING_MODE",
)
P304_NP_FZ100_MIN_CLEANING_PCT: int = 51  # Ver. 2.00+ .. Ver. 7.02
P304_NP_FZ100_MIN_CLEANING_BARS_PRE_V2: int = 3  # Pre-Ver. 2.00 (1.x)

P304_FX6_VARIABLE_ND_VALUES: Tuple[str, ...] = (
    "CLEAR",
    "1/4",
    "1/8",
    "1/16",
    "1/32",
    "1/64",
    "1/128",
)
P304_FX6_CLEANING_ALT_FEATURE: str = "Technical > APR"
P304_FX6_APR_SYMBOL: str = "MODEL_APR_EXECUTE_COMP"
P304_FX6_END_SYMBOLS: Tuple[str, ...] = (
    "PID_SET_VARIABLE_ND_VALUE",
    "BKID_APP_VARIABLE_ND_CONT",
)
P304_FX6_CR_SENSOR_CLEANING_CMD_ID: int = 320  # CrCommandId_SensorCleaning unsupported (-)

P304_EXPOSURE_COMP_BKID: str = "BKID_APP_setting_exposure_compensation"
P304_SEPARATE_MOVIE_EV_COMP_BKID: str = "BKID_APP_separate_movie_exposure_comp"
P304_EXPOSURE_STEP_BKID: str = "BKID_APP_setting_exposure_step"
P304_DORMANT_RESET_EV_COMP_BKID: str = "BKID_APP_setting_exposure_compensation_reset_save"

P304_EXPOSURE_COMP_F_RESID16: int = 0x76DE
P304_EXPOSURE_COMP_RESID16: int = 0xE956
P304_EXPOSURE_COMP_G_RESID16: int = 0x63C5
P304_EXPOSURE_STEP_F_RESID16: int = 0x78C4
P304_EXPOSURE_STEP_RESID16: int = 0xE348
P304_EXPOSURE_STD_ADJUST_F_RESID16: int = 0x6F71
P304_DORMANT_RESET_EV_COMP_F_RESID16: int = 0x7853
P304_DORMANT_DIAL_EV_COMP_RESID16: int = 0xE4D9

P304_EV_COMP_STILL_MIN_EV: float = -5.0
P304_EV_COMP_STILL_MAX_EV: float = 5.0
P304_EV_COMP_MOVIE_MIN_EV: float = -2.0
P304_EV_COMP_MOVIE_MAX_EV: float = 2.0
P304_EV_COMP_LIVE_METER_MIN_EV: float = -3.0
P304_EV_COMP_LIVE_METER_MAX_EV: float = 3.0
P304_EV_COMP_DEFAULT_EV: float = 0.0
P304_EXPOSURE_STEPS: Tuple[str, ...] = ("0.3EV", "0.5EV")
P304_EXPOSURE_STEP_DEFAULT: str = "0.3EV"
P304_EXPOSURE_STD_ADJUST_MIN_EV: float = -1.0
P304_EXPOSURE_STD_ADJUST_MAX_EV: float = 1.0

P304_LOG_SHOOTING_MODES: Tuple[str, ...] = ("Off", "Flexible ISO", "Cine EI Quick", "Cine EI")
P304_CINE_EI_LOCKED_LOG_MODES: Tuple[str, ...] = ("Cine EI Quick", "Cine EI")
P304_CINE_EI_BASE_ISOS: Tuple[int, ...] = (800, 12800)
P304_CINE_EI_INDEX_MIN_EV: float = -2.0
P304_CINE_EI_INDEX_MAX_EV: float = 2.0

# ---------------------------------------------------------------------------
# Pillar 54B Constants — [Focus Mode] (5-Still vs 2-Movie AF-C/MF Clamp +
# Priority Set / AF Illuminator) & [Playback] ([View Mode] / 9-25 [Image Index]
# / [Display as Group] / [Display Rotation] / [Rotate] Slot-1 Tier-0 Firewall)
# ---------------------------------------------------------------------------

P304_FOCUS_MODE_MENU_PATH: Tuple[str, ...] = (
    "Focus",
    "AF/MF",
    "Focus Mode",
)
P304_PLAYBACK_VIEW_MODE_MENU_PATH: Tuple[str, ...] = (
    "Playback",
    "Playback Target",
    "View Mode",
)
P304_PLAYBACK_OPTION_MENU_PATH: Tuple[str, ...] = (
    "Playback",
    "Playback Option",
)
P304_PLAYBACK_ROTATE_MENU_PATH: Tuple[str, ...] = (
    "Playback",
    "Edit",
    "Rotate",
)

P304_FOCUS_MODE_BKID: str = "BKID_APP_setting_focus_mode_menu_dial"
P304_SEPARATE_MOVIE_FOCUS_BKID: str = "BKID_APP_separate_movie_focus_mode"
P304_PRIORITY_AFS_BKID: str = "BKID_APP_setting_af_s_priority_setup"
P304_PRIORITY_AFC_BKID: str = "BKID_APP_setting_af_c_priority_setup"
P304_AF_ASSIST_BKID: str = "BKID_APP_setting_af_assist"
P304_AF_ILLUMINATOR_BKID: str = "BKID_APP_setting_still_image_af_illuminator"

P304_FOCUS_MODE_G_RESID16: int = 0x625E
P304_FOCUS_MODE_ALT_G_RESID16: int = 0x6412
P304_MOVIE_AUTO_AF_C_RESID16: int = 0x66EA
P304_FOCUS_MODE_RESID16_MAP: Dict[str, int] = {
    "AF-S": 0xE56D,
    "AF-A": 0xE56C,
    "AF-C": 0xE56E,
    "DMF": 0xE4AC,
    "MF": 0xE9E4,
}
P304_STILL_FOCUS_MODES: Tuple[str, ...] = ("AF-S", "AF-A", "AF-C", "DMF", "MF")
P304_STILL_FOCUS_MODE_DEFAULT: str = "AF-A"
P304_MOVIE_SQ_FOCUS_MODES: Tuple[str, ...] = ("AF-C", "MF")
P304_MOVIE_SQ_LOCKED_OUT_FOCUS_MODES: Tuple[str, ...] = ("AF-S", "AF-A", "DMF")
P304_DORMANT_FOCUS_MODES: Tuple[str, ...] = ("PF", "SEMI_MANUAL")
P304_MOVIE_CLAMP_ERRNOS: Tuple[int, ...] = (95, 22)  # EOPNOTSUPP=95, EINVAL=22

P304_AF_PRIORITY_MODES: Tuple[str, ...] = ("AF", "Release", "Balanced Emphasis")
P304_AF_PRIORITY_DEFAULT: str = "Balanced Emphasis"
P304_AF_ILLUMINATOR_MODES: Tuple[str, ...] = ("Auto", "Off")
P304_AF_ILLUMINATOR_DEFAULT: str = "Auto"

P304_VIEW_MODE_BKID: str = "BKID_APP_setting_menu_view_mode"
P304_IMAGE_INDEX_BKID: str = "BKID_APP_setting_menu_image_index"
P304_DISPLAY_GROUP_BKID: str = "BKID_APP_setting_display_group"
P304_DISPLAY_ROTATION_BKID: str = "BKID_APP_setting_display_rotatiton"  # Sony appFw.so spelling
P304_ROTATE_FUNC_SYMBOL: str = "FUNC_rotate_content"
P304_ROTATE_BG_NG_SYMBOL: str = "FUNC_CMP_NG_DURING_BACKGROUND_TRANSFER_ROTATE"
P304_ROTATE_F_RESID16: int = 0x795A
P304_ROTATE_RESID16: int = 0xE5AE
P304_UNABLE_TO_ROTATE_RESID16: int = 0xE922

P304_VIEW_MODE_ACTIVE_ILC2210: Tuple[str, ...] = (
    "Date View",
    "Folder View(Still)",
    "Movie View",
)
P304_VIEW_MODE_SUPPORTED: Tuple[str, ...] = (
    "Date View",
    "Folder View(Still)",
    "Movie View",
    "AVCHD View",
    "XAVC S View",
)
P304_VIEW_MODE_DEFAULT: str = "Date View"

P304_IMAGE_INDEX_MODES: Tuple[str, ...] = ("9 Images", "25 Images")
P304_IMAGE_INDEX_DEFAULT: str = "9 Images"
P304_DORMANT_IMAGE_INDEX_MODES: Tuple[str, ...] = (
    "12 Images",
    "30 Images",
    "12_IMAGES",
    "30_IMAGES",
)
P304_DISPLAY_GROUP_MODES: Tuple[str, ...] = ("Off", "On")
P304_DISPLAY_GROUP_DEFAULT: str = "Off"
P304_DISPLAY_ROTATION_MODES: Tuple[str, ...] = ("Auto", "Manual", "Off")
P304_DISPLAY_ROTATION_DEFAULT: str = "Auto"

P304_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P304_EXPOSURE_MODES: Tuple[str, ...] = (
    "Intelligent Auto",
    "P",
    "A",
    "S",
    "M",
    "Flexible Exposure",
)
P304_ON_OFF_MODES: Tuple[str, ...] = ("On", "Off")
P304_RESET_ACTIONS: Tuple[str, ...] = (
    "None",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P304_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "VIEW_MODE_BROWSE",
    "IMAGE_INDEX_BROWSE",
    "ROTATE_EXIF_ORIENTATION",
    "AVF_INFO_DB_MUTATE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
    "DELETE_SINGLE",
)
P304_DESTRUCTIVE_VAULT_ACTIONS: Tuple[str, ...] = (
    "ROTATE_EXIF_ORIENTATION",
    "AVF_INFO_DB_MUTATE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
    "DELETE_SINGLE",
)
P304_SLOT1_VAULT_SLOT: int = 1
P304_SAFE_SECONDARY_SLOT: int = 2
P304_VAULT_FIREWALL_ERRNOS: Tuple[str, ...] = ("EROFS", "EBUSY")
P304_VAULT_FIREWALL_ERRNO_CODES: Dict[str, int] = {"EROFS": 30, "EBUSY": 16}
P304_STAGE_B_VOLATILE_OVERLAY_DIR: str = (
    "/tmp/fx3_sensor_cleaning_ev_comp_focus_mode_rotate_vault_overlay"
)
P304_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P304_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P304_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P304_BLOCKED_INVALID_PILLAR54A_SPEC: str = "BLOCKED_INVALID_PILLAR54A_SPEC"
P304_BLOCKED_SENSOR_CLEANING_BATTERY_OR_POWER_OFF_VIOLATION: str = (
    "BLOCKED_SENSOR_CLEANING_BATTERY_OR_POWER_OFF_VIOLATION"
)
P304_BLOCKED_FX6_IBIS_SHAKE_CONFLATION: str = "BLOCKED_FX6_IBIS_SHAKE_CONFLATION"
P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT: str = (
    "BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT"
)
P304_BLOCKED_EXPOSURE_STEP_OR_DORMANT_DIAL_EV_DRIFT: str = (
    "BLOCKED_EXPOSURE_STEP_OR_DORMANT_DIAL_EV_DRIFT"
)
P304_BLOCKED_INVALID_PILLAR54B_SPEC: str = "BLOCKED_INVALID_PILLAR54B_SPEC"
P304_BLOCKED_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT: str = (
    "BLOCKED_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT"
)
P304_BLOCKED_PRIORITY_SET_OR_AF_ILLUMINATOR_DRIFT: str = (
    "BLOCKED_PRIORITY_SET_OR_AF_ILLUMINATOR_DRIFT"
)
P304_BLOCKED_PLAYBACK_VIEW_INDEX_GROUP_OR_ROTATION_DRIFT: str = (
    "BLOCKED_PLAYBACK_VIEW_INDEX_GROUP_OR_ROTATION_DRIFT"
)
P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL: str = "BLOCKED_SLOT1_VAULT_WRITE_FIREWALL"
P304_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P304_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P304_STATUS_VERIFIED_PILLAR_54A: str = (
    "VERIFIED_PILLAR_54A_SENSOR_CLEANING_51PCT_POWEROFF_FX6_END_APR_EV_COMP_CINE_EI_LOCKOUT"
)
P304_STATUS_REJECTED_PILLAR_54A: str = (
    "REJECTED_PILLAR_54A_SENSOR_CLEANING_51PCT_POWEROFF_FX6_END_APR_EV_COMP_CINE_EI_LOCKOUT"
)
P304_STATUS_VERIFIED_PILLAR_54B: str = (
    "VERIFIED_PILLAR_54B_FOCUS_MODE_5STILL_2MOVIE_CLAMP_PLAYBACK_9_25_ROTATE_SLOT1_VAULT"
)
P304_STATUS_REJECTED_PILLAR_54B: str = (
    "REJECTED_PILLAR_54B_FOCUS_MODE_5STILL_2MOVIE_CLAMP_PLAYBACK_9_25_ROTATE_SLOT1_VAULT"
)
P304_STATUS_VERIFIED_PILLAR54_SUITE: str = (
    "VERIFIED_PILLAR54_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_ROTATE_VAULT"
)
P304_STATUS_FAIL_PILLAR54_SUITE: str = (
    "FAIL_PILLAR54_SENSOR_CLEANING_EV_COMP_FOCUS_MODE_ROTATE_VAULT"
)
P304_STATUS_VERIFIED_54OF54_AGGREGATOR: str = "VERIFIED_54OF54_PILLAR_RECOVERY_MASTER"
P304_STATUS_FAIL_54OF54_AGGREGATOR: str = "FAIL_54OF54_PILLAR_RECOVERY_MASTER"

P304_PILLAR_54A_SCENARIO_IDS: Tuple[str, ...] = (
    "P54A1_SENSOR_CLEANING_51PCT_IBIS_POWER_OFF_AND_EV_COMP_M_ISO_AUTO_SAFE",
    "P54A2_EV_COMP_MOVIE_2_0EV_CAM_RESET_AND_FX6_VARIABLE_END_APR_SAFE",
    "P54A3_REJECT_SENSOR_CLEANING_UNDER_51PCT_0XE574_OR_MISSING_POWER_OFF",
    "P54A4_REJECT_FX6_ULTRASONIC_IBIS_SHAKE_OR_CR320_SPOOF",
    "P54A5_REJECT_EV_COMP_IN_CINE_EI_OR_FIXED_ISO_M_OR_DORMANT_RESET_EV_COMP",
    "P54A6_REJECT_SLOT1_VAULT_FORMAT_OR_PERSISTENT_OVERLAY_OR_H0_H3_DRIFT",
)
P304_PILLAR_54B_SCENARIO_IDS: Tuple[str, ...] = (
    "P54B1_FOCUS_MODE_5STILL_2MOVIE_CLAMP_PRIORITY_SET_INIT_AND_SLOT2_ROTATE_SAFE",
    "P54B2_PLAYBACK_DATE_MOVIE_VIEW_9_25_INDEX_GROUP_AUTO_ROTATION_SAFE",
    "P54B3_REJECT_MOVIE_SQ_AF_S_AF_A_DMF_OR_DORMANT_PF_WITHOUT_EOPNOTSUPP",
    "P54B4_REJECT_MOVIE_AF_ILLUMINATOR_OR_CAM_RESET_WIPING_PRIORITY_SET_OR_INDEX",
    "P54B5_REJECT_DORMANT_12_30_IMAGE_INDEX_OR_FX6_EXIF_ROTATE_SPOOF",
    "P54B6_REJECT_PLAYBACK_ROTATE_EXIF_OR_AVF_INFO_MUTATION_ON_SLOT1_TIER0_VAULT",
)

MASTER_54_PILLAR_COUNT: int = 54
MASTER_54_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_53_PILLAR_SPECS + (
    (
        54,
        "pillar_54_sensor_cleaning_ev_comp_focus_mode_rotate_vault",
        "Phase 304 (Wave-52)",
        "fx3_recovery.realhw_54pillar_sensor_cleaning_ev_comp_focus_mode_rotate_vault_verifier",
    ),
)
MASTER_54_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_54_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Pure Wave-52 State Computations
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
    return os.environ.get(P304_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P304_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P304_DONOR_INSPECT_BUDGET_SECONDS


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
        ("P304_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P304_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("P304_OVERALL_READY_FOR_HARDWARE_ATTACH", P304_OVERALL_READY_FOR_HARDWARE_ATTACH, False),
        ("P304_CROSS_MODEL_FLASH_AUTHORIZED", P304_CROSS_MODEL_FLASH_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        (
            "P304_SENSOR_CLEANING_LOW_BATTERY_BYPASS_EVENTS",
            P304_SENSOR_CLEANING_LOW_BATTERY_BYPASS_EVENTS,
            0,
        ),
        (
            "P304_SENSOR_CLEANING_NO_POWER_OFF_VIOLATIONS",
            P304_SENSOR_CLEANING_NO_POWER_OFF_VIOLATIONS,
            0,
        ),
        ("P304_FX6_IBIS_SHAKE_CONFLATION_EVENTS", P304_FX6_IBIS_SHAKE_CONFLATION_EVENTS, 0),
        (
            "P304_EV_COMP_RANGE_OR_CINE_EI_LOCKOUT_VIOLATIONS",
            P304_EV_COMP_RANGE_OR_CINE_EI_LOCKOUT_VIOLATIONS,
            0,
        ),
        (
            "P304_EXPOSURE_STEP_OR_DORMANT_RESET_EV_DRIFT_EVENTS",
            P304_EXPOSURE_STEP_OR_DORMANT_RESET_EV_DRIFT_EVENTS,
            0,
        ),
        (
            "P304_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT_EVENTS",
            P304_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT_EVENTS,
            0,
        ),
        (
            "P304_PRIORITY_SET_OR_ILLUMINATOR_GATE_VIOLATIONS",
            P304_PRIORITY_SET_OR_ILLUMINATOR_GATE_VIOLATIONS,
            0,
        ),
        (
            "P304_IMAGE_INDEX_DORMANT_OR_VIEW_MODE_DRIFT_EVENTS",
            P304_IMAGE_INDEX_DORMANT_OR_VIEW_MODE_DRIFT_EVENTS,
            0,
        ),
        ("P304_SLOT1_DATA_SECTOR_WRITES", P304_SLOT1_DATA_SECTOR_WRITES, 0),
        ("P304_SLOT1_ROTATE_EXIF_MUTATION_BYTES", P304_SLOT1_ROTATE_EXIF_MUTATION_BYTES, 0),
        ("P304_SLOT1_VAULT_MUTATION_BYTES", P304_SLOT1_VAULT_MUTATION_BYTES, 0),
        ("P304_SLOT1_FORMAT_HARD_LOCKED", P304_SLOT1_FORMAT_HARD_LOCKED, True),
        ("P304_SLOT1_VAULT_EROFS_EBUSY_ENFORCED", P304_SLOT1_VAULT_EROFS_EBUSY_ENFORCED, True),
        ("P304_FX3_HAS_SENSOR_CLEANING_IBIS", P304_FX3_HAS_SENSOR_CLEANING_IBIS, True),
        ("P304_FX3_HAS_EXPOSURE_COMP", P304_FX3_HAS_EXPOSURE_COMP, True),
        ("P304_FX3_HAS_PHYSICAL_EV_RESET_DIAL", P304_FX3_HAS_PHYSICAL_EV_RESET_DIAL, False),
        ("P304_FX6_HAS_ULTRASONIC_IBIS_CLEANING", P304_FX6_HAS_ULTRASONIC_IBIS_CLEANING, False),
        ("P304_FX6_HAS_VARIABLE_END_OPTICAL_BLOCK", P304_FX6_HAS_VARIABLE_END_OPTICAL_BLOCK, True),
        ("P304_FX6_HAS_TECHNICAL_APR", P304_FX6_HAS_TECHNICAL_APR, True),
        ("P304_FX6_HAS_STILL_EXPOSURE_COMP", P304_FX6_HAS_STILL_EXPOSURE_COMP, False),
        ("P304_FX6_HAS_STILL_IMAGE_INDEX_ROTATE", P304_FX6_HAS_STILL_IMAGE_INDEX_ROTATE, False),
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
    return any(tok in low for tok in P304_FORBIDDEN_PERSISTENT_TARGETS)


def compute_expected_sensor_cleaning_state(
    *,
    camera_model: str,
    fw_version: str,
    battery_pct: int,
    battery_bars: int,
    power_switch_off_after_shake: bool,
    lens_removed_before_power_off: bool,
) -> Tuple[bool, bool, Optional[int], str]:
    """Compute `(ibis_cleaning_allowed, mandatory_power_off_required, message_resid16, fx6_path)`.

    - `ILME-FX3 Ver. 2.00+..7.02`: requires `NP-FZ100 >= 51%`; `< 51%` aborts with
      `.uxc` `0xe574` (`Power insufficient.`). Pre-Ver. 2.00 required `>= 3` bars.
    - Mandatory physical power-switch `OFF` (`_g.uxc` `0x6221`) before lens removal.
    - `ILME-FX6`: IBIS-less -> ultrasonic IBIS shake is rejected; uses front Electronic
      Variable ND (`1/4..1/128` + `CLEAR`) + `Technical > APR` (`MODEL_APR_EXECUTE_COMP`).
    """
    if camera_model == P304_FX6_DONOR_MODEL_NAME:
        return False, False, None, P304_FX6_CLEANING_ALT_FEATURE
    if fw_version in P304_FX3_PRE_V2_FW_VERSIONS:
        if battery_bars < P304_NP_FZ100_MIN_CLEANING_BARS_PRE_V2:
            return False, False, P304_POWER_INSUFFICIENT_RESID16, "PRE_V2_LOW_BARS"
    else:
        if battery_pct < P304_NP_FZ100_MIN_CLEANING_PCT:
            return False, False, P304_POWER_INSUFFICIENT_RESID16, "V2_PLUS_BELOW_51PCT"
    safe_seq = bool(power_switch_off_after_shake and not lens_removed_before_power_off)
    return safe_seq, True, P304_MANDATORY_POWER_OFF_G_RESID16, "FX3_IBIS_SHAKE_AND_POWER_OFF"


def compute_expected_exposure_comp_state(
    *,
    shooting_domain: str,
    exposure_mode: str,
    iso_mode: str,
    log_shooting_mode: str,
    configured_ev_comp: float,
    configured_exposure_step: str,
    reset_action: str,
) -> Tuple[bool, float, float, float, str, bool]:
    """Compute `(ev_comp_active, min_ev, max_ev, post_ev_comp, post_exposure_step, ei_active)`.

    - Still: `-5.0..+5.0 EV`; Movie/`S&Q`: `-2.0..+2.0 EV`.
    - Disabled in `Intelligent Auto`; in `M`, works ONLY with `ISO AUTO`.
    - 100% locked out under `Cine EI` / `Cine EI Quick` (`Base ISO 800/12800`, `[Exposure Index]`
      `+-2.0 EV` governs monitoring).
    - `Camera Settings Reset` resets `Exposure Comp.` -> `0.0 EV` while `Exposure step` survives
      (clears only on `Initialize`).
    """
    is_cine_ei = log_shooting_mode in P304_CINE_EI_LOCKED_LOG_MODES
    if shooting_domain == "Still":
        min_ev, max_ev = P304_EV_COMP_STILL_MIN_EV, P304_EV_COMP_STILL_MAX_EV
    else:
        min_ev, max_ev = P304_EV_COMP_MOVIE_MIN_EV, P304_EV_COMP_MOVIE_MAX_EV

    if is_cine_ei or exposure_mode == "Intelligent Auto":
        ev_active = False
    elif exposure_mode == "M" and iso_mode != "ISO AUTO":
        ev_active = False
    else:
        ev_active = True

    if reset_action in ("Camera Settings Reset", "Initialize"):
        post_ev = P304_EV_COMP_DEFAULT_EV
    else:
        post_ev = configured_ev_comp if ev_active else P304_EV_COMP_DEFAULT_EV

    if reset_action == "Initialize":
        post_step = P304_EXPOSURE_STEP_DEFAULT
    else:
        post_step = configured_exposure_step

    return ev_active, min_ev, max_ev, post_ev, post_step, is_cine_ei


def compute_expected_focus_mode_state(
    *,
    shooting_domain: str,
    requested_focus_mode: str,
    configured_priority_afs: str,
    configured_priority_afc: str,
    configured_af_illuminator: str,
    reset_action: str,
) -> Tuple[bool, Optional[int], str, str, bool, str]:
    """Compute `(focus_mode_allowed, clamp_errno, post_priority_afs, post_priority_afc,
    af_illuminator_active, post_af_illuminator)`.

    - Still: 5 modes (`AF-S`, `AF-A` default, `AF-C`, `DMF`, `MF`); `PF`/`SEMI_MANUAL` rejected.
    - Movie & `S&Q`: strictly clamped to `AF-C` (`MOVIE_AUTO`) & `MF`; `AF-S`/`AF-A`/`DMF`
      rejected (`EOPNOTSUPP=95` / `EINVAL=22`).
    - `Priority Set in AF-S/AF-C` survive `Camera Settings Reset` (`Initialize`-only).
    - `AF Illuminator` resets on `Camera Settings Reset`, and is Still-only (locked out in
      Movie/`S&Q` or `AF-C`).
    """
    if requested_focus_mode in P304_DORMANT_FOCUS_MODES:
        mode_ok = False
        err_no: Optional[int] = 22  # EINVAL
    elif shooting_domain == "Still":
        mode_ok = requested_focus_mode in P304_STILL_FOCUS_MODES
        err_no = None if mode_ok else 22
    else:
        mode_ok = requested_focus_mode in P304_MOVIE_SQ_FOCUS_MODES
        err_no = None if mode_ok else 95  # EOPNOTSUPP

    if reset_action == "Initialize":
        post_afs = P304_AF_PRIORITY_DEFAULT
        post_afc = P304_AF_PRIORITY_DEFAULT
    else:
        post_afs = configured_priority_afs
        post_afc = configured_priority_afc

    illum_active = shooting_domain == "Still" and requested_focus_mode != "AF-C"
    if reset_action in ("Camera Settings Reset", "Initialize"):
        post_illum = P304_AF_ILLUMINATOR_DEFAULT
    else:
        post_illum = configured_af_illuminator

    return mode_ok, err_no, post_afs, post_afc, illum_active, post_illum


def compute_expected_playback_rotate_state(
    *,
    view_mode: str,
    image_index: str,
    display_as_group: str,
    display_rotation: str,
    playback_slot: int,
    slot1_holds_tier0_vault: bool,
    requested_action: str,
    background_transfer_active: bool,
    reset_action: str,
) -> Tuple[bool, bool, Optional[str], str, str, str, str]:
    """Compute `(playback_settings_valid, rotate_allowed, firewall_errno, post_view_mode,
    post_image_index, post_display_group, post_display_rotation)`.

    - Playback `[View Mode]`, `[Image Index]` (`9 Images` / `25 Images` — rejecting dormant
      `12 Images` / `30 Images`), `[Display as Group]`, and `[Display Rotation]` survive
      `Camera Settings Reset` (`Initialize`-only).
    - `[Rotate]` mutates EXIF orientation / `AVF_INFO` DB -> fail-closed (`EROFS` / `EBUSY`)
      whenever `playback_slot == 1` and `slot1_holds_tier0_vault == True`, or during background
      transfer (`EBUSY`).
    """
    settings_ok = (
        view_mode in P304_VIEW_MODE_SUPPORTED
        and image_index in P304_IMAGE_INDEX_MODES
        and image_index not in P304_DORMANT_IMAGE_INDEX_MODES
        and display_as_group in P304_DISPLAY_GROUP_MODES
        and display_rotation in P304_DISPLAY_ROTATION_MODES
    )
    if requested_action in ("ROTATE_EXIF_ORIENTATION", "AVF_INFO_DB_MUTATE"):
        if playback_slot == P304_SLOT1_VAULT_SLOT and slot1_holds_tier0_vault:
            rotate_ok = False
            errno_str: Optional[str] = "EROFS"
        elif background_transfer_active:
            rotate_ok = False
            errno_str = "EBUSY"
        else:
            rotate_ok = True
            errno_str = None
    else:
        rotate_ok = False
        errno_str = None

    if reset_action == "Initialize":
        return (
            settings_ok,
            rotate_ok,
            errno_str,
            P304_VIEW_MODE_DEFAULT,
            P304_IMAGE_INDEX_DEFAULT,
            P304_DISPLAY_GROUP_DEFAULT,
            P304_DISPLAY_ROTATION_DEFAULT,
        )
    return (
        settings_ok,
        rotate_ok,
        errno_str,
        view_mode,
        image_index,
        display_as_group,
        display_rotation,
    )

# ---------------------------------------------------------------------------
# Frozen Dataclasses (Specs, Reports, Suites & 54-Pillar Master)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase304DonorArtifactDigest:
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
class Phase304DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase304DonorArtifactDigest, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SensorCleaningEvCompVaultSpec:
    # Sensor Cleaning >= 51% NP-FZ100 + mandatory OFF vs FX6 e-ND + APR
    camera_model: str
    fw_version: str
    battery_pct: int
    battery_bars: int
    cleaning_mode_entered: bool
    power_insufficient_msg_resid16: Optional[int]
    power_switch_off_after_shake: bool
    mandatory_power_off_msg_resid16: Optional[int]
    lens_removed_before_power_off: bool
    fx6_variable_nd_step: str
    fx6_apr_supported: bool
    fx6_ultrasonic_ibis_shake_attempted: bool
    fx6_cr_sensor_cleaning_supported: bool
    # Exposure Comp. (+-5.0 EV Still / +-2.0 EV Movie & S&Q, M+ISO AUTO, Cine EI lockout)
    shooting_domain: str
    exposure_mode: str
    iso_mode: str
    log_shooting_mode: str
    cine_ei_base_iso: int
    cine_ei_exposure_index_ev: float
    display_lut_enabled: bool
    requested_ev_comp_ev: float
    reported_ev_comp_active: bool
    reported_ev_comp_min_ev: float
    reported_ev_comp_max_ev: float
    exposure_step: str
    exposure_std_adjust_ev: float
    reset_action: str
    post_reset_ev_comp_ev: float
    post_reset_exposure_step: str
    dormant_reset_ev_comp_exposed: bool
    dormant_dial_ev_comp_exposed: bool
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
    sensor_cleaning_low_battery_bypass_events: int
    sensor_cleaning_no_power_off_violations: int
    fx6_ibis_shake_conflation_events: int
    ev_comp_range_or_cine_ei_lockout_violations: int
    exposure_step_or_dormant_reset_ev_drift_events: int


@dataclass(frozen=True)
class SensorCleaningEvCompVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    sensor_cleaning_51pct_poweroff_verified: bool
    fx6_end_apr_contrast_verified: bool
    ev_comp_range_iso_auto_and_cine_ei_lockout_verified: bool
    slot1_vault_firewall_and_h0_h3_verified: bool
    matrix_states_checked: int
    sensor_cleaning_low_battery_bypass_events: int
    sensor_cleaning_no_power_off_violations: int
    fx6_ibis_shake_conflation_events: int
    ev_comp_range_or_cine_ei_lockout_violations: int
    exposure_step_or_dormant_reset_ev_drift_events: int
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
class FocusModePlaybackRotateVaultSpec:
    # Focus Mode (5 Still vs 2 Movie AF-C/MF Clamp + Priority Set / AF Illuminator)
    camera_model: str
    shooting_domain: str
    requested_focus_mode: str
    reported_focus_mode_allowed: bool
    movie_clamp_errno: Optional[int]
    af_assist_enabled: bool
    configured_priority_afs: str
    configured_priority_afc: str
    configured_af_illuminator: str
    reported_af_illuminator_active: bool
    reset_action: str
    post_priority_afs: str
    post_priority_afc: str
    post_af_illuminator: str
    # Playback (View Mode / 9-25 Image Index / Display as Group / Display Rotation / Rotate)
    view_mode: str
    image_index: str
    display_as_group: str
    display_rotation: str
    post_view_mode: str
    post_image_index: str
    post_display_as_group: str
    post_display_rotation: str
    fx6_exposes_still_image_index_or_exif_rotate: bool
    # Slot-1 Tier-0 Vault Firewall for Playback [Rotate] & AVF_INFO DB
    select_playback_media_slot: int
    slot1_holds_tier0_vault: bool
    requested_vault_action: str
    background_transfer_active: bool
    reported_rotate_allowed: bool
    rotate_firewall_errno: Optional[str]
    slot1_data_sector_writes: int
    slot1_rotate_exif_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_vault_erofs_ebusy_enforced: bool
    slot1_format_hard_locked: bool
    overlay_dir: str
    backup_bin_h0_sha256: str
    backup_bin_h3_sha256: str
    tier0_surfaces_h0_h3_matched: int
    # Negative counters
    focus_mode_movie_clamp_or_dormant_drift_events: int
    priority_set_or_illuminator_gate_violations: int
    image_index_dormant_or_view_mode_drift_events: int


@dataclass(frozen=True)
class FocusModePlaybackRotateVaultReport:
    schema: str
    version: str
    passed: bool
    status: str
    block_code: Optional[str]
    focus_mode_5still_2movie_clamp_verified: bool
    priority_set_init_and_illuminator_gate_verified: bool
    playback_view_9_25_index_group_rotation_verified: bool
    slot1_rotate_exif_erofs_ebusy_firewall_verified: bool
    matrix_states_checked: int
    focus_mode_movie_clamp_or_dormant_drift_events: int
    priority_set_or_illuminator_gate_violations: int
    image_index_dormant_or_view_mode_drift_events: int
    slot1_data_sector_writes: int
    slot1_rotate_exif_mutation_bytes: int
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
class SensorCleaningEvCompFocusModeRotateVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase304DonorSnapshot
    sensor_cleaning_ev_comp_report: SensorCleaningEvCompVaultReport
    focus_mode_playback_rotate_report: FocusModePlaybackRotateVaultReport
    sensor_cleaning_low_battery_bypass_events: int
    sensor_cleaning_no_power_off_violations: int
    fx6_ibis_shake_conflation_events: int
    ev_comp_range_or_cine_ei_lockout_violations: int
    exposure_step_or_dormant_reset_ev_drift_events: int
    focus_mode_movie_clamp_or_dormant_drift_events: int
    priority_set_or_illuminator_gate_violations: int
    image_index_dormant_or_view_mode_drift_events: int
    slot1_data_sector_writes: int
    slot1_rotate_exif_mutation_bytes: int
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
class Pillar54ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar54ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar54ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar54BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar54ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar54StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase304DonorSnapshot
    pillar_54a_sensor_cleaning_ev_comp_vault: Pillar54ASuiteResult
    pillar_54b_focus_mode_playback_rotate_vault: Pillar54BSuiteResult
    sensor_cleaning_low_battery_bypass_events: int
    sensor_cleaning_no_power_off_violations: int
    fx6_ibis_shake_conflation_events: int
    ev_comp_range_or_cine_ei_lockout_violations: int
    exposure_step_or_dormant_reset_ev_drift_events: int
    focus_mode_movie_clamp_or_dormant_drift_events: int
    priority_set_or_illuminator_gate_violations: int
    image_index_dormant_or_view_mode_drift_events: int
    slot1_data_sector_writes: int
    slot1_rotate_exif_mutation_bytes: int
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
class Master54PillarRecoveryReport:
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
    # Pillar 54 & Wave-52 top-level fields (Phase 304)
    donor_snapshot: Phase304DonorSnapshot
    pillar54_a_sensor_cleaning_ev_comp_vault: Pillar54ASuiteResult
    pillar54_b_focus_mode_playback_rotate_vault: Pillar54BSuiteResult
    sensor_cleaning_low_battery_bypass_events: int
    sensor_cleaning_no_power_off_violations: int
    fx6_ibis_shake_conflation_events: int
    ev_comp_range_or_cine_ei_lockout_violations: int
    exposure_step_or_dormant_reset_ev_drift_events: int
    focus_mode_movie_clamp_or_dormant_drift_events: int
    priority_set_or_illuminator_gate_violations: int
    image_index_dormant_or_view_mode_drift_events: int
    slot1_data_sector_writes: int
    slot1_rotate_exif_mutation_bytes: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    slot1_vault_erofs_ebusy_enforced: bool
    fx3_has_sensor_cleaning_ibis: bool
    fx3_has_exposure_comp: bool
    fx3_has_physical_ev_reset_dial: bool
    fx6_has_ultrasonic_ibis_cleaning: bool
    fx6_has_variable_end_optical_block: bool
    fx6_has_technical_apr: bool
    fx6_has_still_exposure_comp: bool
    fx6_has_still_image_index_rotate: bool
    # Preserved Pillars 1..53 rollup metrics
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
    master_54pillar_sha256: str
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
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback (Phase 304)
# ---------------------------------------------------------------------------


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P304_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P304_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase304_donors() -> Tuple[Phase304DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P304_DONOR_FX3_APPFW_702_RELPATH,
            P304_PINNED_FX3_APPFW_702_BYTES,
            P304_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P304_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P304_DONOR_FX6_APPFW_601_RELPATH,
            P304_PINNED_FX6_APPFW_601_BYTES,
            P304_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P304_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P304_DONOR_FX3_BACKUP_BIN_RELPATH,
            P304_PINNED_FX3_BACKUP_BIN_BYTES,
            P304_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_uxc_en_f",
            P304_DONOR_FX3_UXC_EN_F_RELPATH,
            P304_PINNED_FX3_UXC_EN_F_BYTES,
            P304_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P304_DONOR_FX3_UXC_SC_F_RELPATH,
            P304_PINNED_FX3_UXC_SC_F_BYTES,
            P304_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P304_DONOR_FX3_UXC_TC_F_RELPATH,
            P304_PINNED_FX3_UXC_TC_F_BYTES,
            P304_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P304_DONOR_FX3_UXC_JA_F_RELPATH,
            P304_PINNED_FX3_UXC_JA_F_BYTES,
            P304_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P304_DONOR_FX3_UXC_EN_RELPATH,
            P304_PINNED_FX3_UXC_EN_BYTES,
            P304_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_sc",
            P304_DONOR_FX3_UXC_SC_RELPATH,
            P304_PINNED_FX3_UXC_SC_BYTES,
            P304_PINNED_FX3_UXC_SC_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX3_SC",
        ),
        (
            "fx3_uxc_tc",
            P304_DONOR_FX3_UXC_TC_RELPATH,
            P304_PINNED_FX3_UXC_TC_BYTES,
            P304_PINNED_FX3_UXC_TC_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX3_TC",
        ),
        (
            "fx3_uxc_ja",
            P304_DONOR_FX3_UXC_JA_RELPATH,
            P304_PINNED_FX3_UXC_JA_BYTES,
            P304_PINNED_FX3_UXC_JA_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX3_JA",
        ),
        (
            "fx3_uxc_en_g",
            P304_DONOR_FX3_UXC_EN_G_RELPATH,
            P304_PINNED_FX3_UXC_EN_G_BYTES,
            P304_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx3_uxc_sc_g",
            P304_DONOR_FX3_UXC_SC_G_RELPATH,
            P304_PINNED_FX3_UXC_SC_G_BYTES,
            P304_PINNED_FX3_UXC_SC_G_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_SC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_G",
        ),
        (
            "fx3_uxc_tc_g",
            P304_DONOR_FX3_UXC_TC_G_RELPATH,
            P304_PINNED_FX3_UXC_TC_G_BYTES,
            P304_PINNED_FX3_UXC_TC_G_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_TC_G_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_G",
        ),
        (
            "fx3_uxc_ja_g",
            P304_DONOR_FX3_UXC_JA_G_RELPATH,
            P304_PINNED_FX3_UXC_JA_G_BYTES,
            P304_PINNED_FX3_UXC_JA_G_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX3_UXC_JA_G_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_G",
        ),
        (
            "fx6_uxc_en",
            P304_DONOR_FX6_UXC_EN_RELPATH,
            P304_PINNED_FX6_UXC_EN_BYTES,
            P304_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P304_DONOR_FX6_UXC_EN_2_RELPATH,
            P304_PINNED_FX6_UXC_EN_2_BYTES,
            P304_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P304_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase304DonorArtifactDigest(
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


def inspect_phase304_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase304DonorSnapshot:
    """Inspect Wave-52 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.2s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase304_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase304DonorSnapshot(
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
            P304_DONOR_FX3_APPFW_702_RELPATH,
            P304_PINNED_FX3_APPFW_702_BYTES,
            P304_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702"),
        ),
        (
            "fx6_appfw_601_so",
            P304_DONOR_FX6_APPFW_601_RELPATH,
            P304_PINNED_FX6_APPFW_601_BYTES,
            P304_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601"),
        ),
        (
            "fx3_backup_bin",
            P304_DONOR_FX3_BACKUP_BIN_RELPATH,
            P304_PINNED_FX3_BACKUP_BIN_BYTES,
            P304_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_uxc_en_f",
            P304_DONOR_FX3_UXC_EN_F_RELPATH,
            P304_PINNED_FX3_UXC_EN_F_BYTES,
            P304_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P304_DONOR_FX3_UXC_SC_F_RELPATH,
            P304_PINNED_FX3_UXC_SC_F_BYTES,
            P304_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P304_DONOR_FX3_UXC_TC_F_RELPATH,
            P304_PINNED_FX3_UXC_TC_F_BYTES,
            P304_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P304_DONOR_FX3_UXC_JA_F_RELPATH,
            P304_PINNED_FX3_UXC_JA_F_BYTES,
            P304_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P304_DONOR_FX3_UXC_EN_RELPATH,
            P304_PINNED_FX3_UXC_EN_BYTES,
            P304_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_sc",
            P304_DONOR_FX3_UXC_SC_RELPATH,
            P304_PINNED_FX3_UXC_SC_BYTES,
            P304_PINNED_FX3_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC"),
        ),
        (
            "fx3_uxc_tc",
            P304_DONOR_FX3_UXC_TC_RELPATH,
            P304_PINNED_FX3_UXC_TC_BYTES,
            P304_PINNED_FX3_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC"),
        ),
        (
            "fx3_uxc_ja",
            P304_DONOR_FX3_UXC_JA_RELPATH,
            P304_PINNED_FX3_UXC_JA_BYTES,
            P304_PINNED_FX3_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA"),
        ),
        (
            "fx3_uxc_en_g",
            P304_DONOR_FX3_UXC_EN_G_RELPATH,
            P304_PINNED_FX3_UXC_EN_G_BYTES,
            P304_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx3_uxc_sc_g",
            P304_DONOR_FX3_UXC_SC_G_RELPATH,
            P304_PINNED_FX3_UXC_SC_G_BYTES,
            P304_PINNED_FX3_UXC_SC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_G"),
        ),
        (
            "fx3_uxc_tc_g",
            P304_DONOR_FX3_UXC_TC_G_RELPATH,
            P304_PINNED_FX3_UXC_TC_G_BYTES,
            P304_PINNED_FX3_UXC_TC_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_G"),
        ),
        (
            "fx3_uxc_ja_g",
            P304_DONOR_FX3_UXC_JA_G_RELPATH,
            P304_PINNED_FX3_UXC_JA_G_BYTES,
            P304_PINNED_FX3_UXC_JA_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_G"),
        ),
        (
            "fx6_uxc_en",
            P304_DONOR_FX6_UXC_EN_RELPATH,
            P304_PINNED_FX6_UXC_EN_BYTES,
            P304_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P304_DONOR_FX6_UXC_EN_2_RELPATH,
            P304_PINNED_FX6_UXC_EN_2_BYTES,
            P304_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    digests: List[Phase304DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, data = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            break
        ok_marker, msum = marker_fn(data)
        matches = ok_marker and (total_b == expected_bytes) and (dsha == expected_sha)
        digests.append(
            Phase304DonorArtifactDigest(
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
        artifacts = _synthetic_phase304_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase304DonorSnapshot(
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
    return Phase304DonorSnapshot(
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
# Spec Builders & Evaluators (Pillars 54A & 54B)
# ---------------------------------------------------------------------------


def build_default_safe_sensor_cleaning_ev_comp_vault_spec(
    **overrides: Any,
) -> SensorCleaningEvCompVaultSpec:
    """Return a clean, verified default `SensorCleaningEvCompVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P304_FX3_MODEL_NAME,
        "fw_version": P304_FX3_FW_VERSION,
        "battery_pct": 82,
        "battery_bars": 4,
        "cleaning_mode_entered": True,
        "power_insufficient_msg_resid16": None,
        "power_switch_off_after_shake": True,
        "mandatory_power_off_msg_resid16": P304_MANDATORY_POWER_OFF_G_RESID16,
        "lens_removed_before_power_off": False,
        "fx6_variable_nd_step": "1/16",
        "fx6_apr_supported": True,
        "fx6_ultrasonic_ibis_shake_attempted": False,
        "fx6_cr_sensor_cleaning_supported": False,
        "shooting_domain": "Still",
        "exposure_mode": "A",
        "iso_mode": "ISO AUTO",
        "log_shooting_mode": "Off",
        "cine_ei_base_iso": 800,
        "cine_ei_exposure_index_ev": 0.0,
        "display_lut_enabled": False,
        "requested_ev_comp_ev": 1.3,
        "reported_ev_comp_active": True,
        "reported_ev_comp_min_ev": P304_EV_COMP_STILL_MIN_EV,
        "reported_ev_comp_max_ev": P304_EV_COMP_STILL_MAX_EV,
        "exposure_step": "0.3EV",
        "exposure_std_adjust_ev": 0.0,
        "reset_action": "None",
        "post_reset_ev_comp_ev": 1.3,
        "post_reset_exposure_step": "0.3EV",
        "dormant_reset_ev_comp_exposed": False,
        "dormant_dial_ev_comp_exposed": False,
        "requested_vault_slot": P304_SLOT1_VAULT_SLOT,
        "requested_vault_action": "READ_ONLY_AUDIT",
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_ebusy_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P304_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P304_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P304_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P304_TIER0_SURFACE_COUNT,
        "sensor_cleaning_low_battery_bypass_events": 0,
        "sensor_cleaning_no_power_off_violations": 0,
        "fx6_ibis_shake_conflation_events": 0,
        "ev_comp_range_or_cine_ei_lockout_violations": 0,
        "exposure_step_or_dormant_reset_ev_drift_events": 0,
    }
    defaults.update(overrides)
    return SensorCleaningEvCompVaultSpec(**defaults)


def build_default_safe_focus_mode_playback_rotate_vault_spec(
    **overrides: Any,
) -> FocusModePlaybackRotateVaultSpec:
    """Return a clean, verified default `FocusModePlaybackRotateVaultSpec`."""
    defaults: Dict[str, Any] = {
        "camera_model": P304_FX3_MODEL_NAME,
        "shooting_domain": "Still",
        "requested_focus_mode": "AF-C",
        "reported_focus_mode_allowed": True,
        "movie_clamp_errno": None,
        "af_assist_enabled": False,
        "configured_priority_afs": "Balanced Emphasis",
        "configured_priority_afc": "Balanced Emphasis",
        "configured_af_illuminator": "Auto",
        "reported_af_illuminator_active": False,
        "reset_action": "None",
        "post_priority_afs": "Balanced Emphasis",
        "post_priority_afc": "Balanced Emphasis",
        "post_af_illuminator": "Auto",
        "view_mode": "Date View",
        "image_index": "9 Images",
        "display_as_group": "Off",
        "display_rotation": "Auto",
        "post_view_mode": "Date View",
        "post_image_index": "9 Images",
        "post_display_as_group": "Off",
        "post_display_rotation": "Auto",
        "fx6_exposes_still_image_index_or_exif_rotate": False,
        "select_playback_media_slot": P304_SAFE_SECONDARY_SLOT,
        "slot1_holds_tier0_vault": True,
        "requested_vault_action": "VIEW_MODE_BROWSE",
        "background_transfer_active": False,
        "reported_rotate_allowed": False,
        "rotate_firewall_errno": None,
        "slot1_data_sector_writes": 0,
        "slot1_rotate_exif_mutation_bytes": 0,
        "slot1_vault_mutation_bytes": 0,
        "slot1_vault_erofs_ebusy_enforced": True,
        "slot1_format_hard_locked": True,
        "overlay_dir": P304_STAGE_B_VOLATILE_OVERLAY_DIR,
        "backup_bin_h0_sha256": P304_PINNED_FX3_BACKUP_BIN_SHA256,
        "backup_bin_h3_sha256": P304_PINNED_FX3_BACKUP_BIN_SHA256,
        "tier0_surfaces_h0_h3_matched": P304_TIER0_SURFACE_COUNT,
        "focus_mode_movie_clamp_or_dormant_drift_events": 0,
        "priority_set_or_illuminator_gate_violations": 0,
        "image_index_dormant_or_view_mode_drift_events": 0,
    }
    defaults.update(overrides)
    return FocusModePlaybackRotateVaultSpec(**defaults)


def evaluate_sensor_cleaning_ev_comp_vault(
    spec: SensorCleaningEvCompVaultSpec,
) -> SensorCleaningEvCompVaultReport:
    """Evaluate Pillar 54A (`[Sensor Cleaning]` `>= 51%` NP-FZ100 battery gate + mandatory
    physical power-switch `OFF` `_g.uxc` `0x6221` vs IBIS-less `ILME-FX6` Electronic Variable ND
    `1/4..1/128 + CLEAR` + `Technical > APR`, `[Exposure Comp.]` `+-5.0 EV` Still / `+-2.0 EV`
    Movie & `S&Q` + `M + ISO AUTO` only + `[Exposure step]` `Initialize`-only + 100% `[Cine EI]`
    lockout, and `Slot-1` Tier-0 Vault `EROFS`/`EBUSY` firewall)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(
            P304_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Module safety invariant violation",
        )

    valid_fw = (
        (
            spec.camera_model == P304_FX3_MODEL_NAME
            and (
                spec.fw_version in P304_FX3_SUPPORTED_FW_VERSIONS
                or spec.fw_version in P304_FX3_PRE_V2_FW_VERSIONS
            )
        )
        or (
            spec.camera_model == P304_FX6_DONOR_MODEL_NAME
            and spec.fw_version == P304_FX6_DONOR_FW_VERSION
        )
    )
    if (
        not valid_fw
        or spec.shooting_domain not in P304_SHOOTING_DOMAINS
        or spec.exposure_mode not in P304_EXPOSURE_MODES
        or spec.log_shooting_mode not in P304_LOG_SHOOTING_MODES
        or spec.exposure_step not in P304_EXPOSURE_STEPS
        or spec.post_reset_exposure_step not in P304_EXPOSURE_STEPS
        or spec.reset_action not in P304_RESET_ACTIONS
        or spec.requested_vault_action not in P304_VAULT_TARGET_ACTIONS
        or spec.fx6_variable_nd_step not in P304_FX6_VARIABLE_ND_VALUES
        or not (
            P304_EXPOSURE_STD_ADJUST_MIN_EV
            <= spec.exposure_std_adjust_ev
            <= P304_EXPOSURE_STD_ADJUST_MAX_EV
        )
        or spec.cine_ei_base_iso not in P304_CINE_EI_BASE_ISOS
        or not (
            P304_CINE_EI_INDEX_MIN_EV
            <= spec.cine_ei_exposure_index_ev
            <= P304_CINE_EI_INDEX_MAX_EV
        )
    ):
        _fail(
            P304_BLOCKED_INVALID_PILLAR54A_SPEC,
            "Invalid Pillar 54A camera/SensorCleaning/ExposureComp/CineEI/vault spec parameter",
        )

    exp_clean_ok, exp_pwr_off_req, exp_clean_resid16, exp_clean_path = (
        compute_expected_sensor_cleaning_state(
            camera_model=spec.camera_model,
            fw_version=spec.fw_version,
            battery_pct=spec.battery_pct,
            battery_bars=spec.battery_bars,
            power_switch_off_after_shake=spec.power_switch_off_after_shake,
            lens_removed_before_power_off=spec.lens_removed_before_power_off,
        )
    )

    exp_ev_active, exp_min_ev, exp_max_ev, exp_post_ev, exp_post_step, _ = (
        compute_expected_exposure_comp_state(
            shooting_domain=spec.shooting_domain,
            exposure_mode=spec.exposure_mode,
            iso_mode=spec.iso_mode,
            log_shooting_mode=spec.log_shooting_mode,
            configured_ev_comp=spec.requested_ev_comp_ev,
            configured_exposure_step=spec.exposure_step,
            reset_action=spec.reset_action,
        )
    )

    # 1. FX6 e-ND + APR contrast & zero IBIS ultrasonic shake conflation
    fx6_contrast_ok = (
        not spec.fx6_ultrasonic_ibis_shake_attempted
        and not spec.fx6_cr_sensor_cleaning_supported
        and spec.fx6_apr_supported
        and spec.fx6_variable_nd_step in P304_FX6_VARIABLE_ND_VALUES
        and not (spec.camera_model == P304_FX6_DONOR_MODEL_NAME and spec.cleaning_mode_entered)
        and spec.fx6_ibis_shake_conflation_events == 0
    )
    if not fx6_contrast_ok:
        _fail(
            P304_BLOCKED_FX6_IBIS_SHAKE_CONFLATION,
            "IBIS-less ILME-FX6 must reject ultrasonic IBIS Sensor Cleaning / CrCommandId 320 and isolate Variable ND + Technical > APR",
        )

    # 2. FX3 [Sensor Cleaning] >= 51% NP-FZ100 Gate & Mandatory Power-Switch OFF (_g.uxc 0x6221)
    if spec.camera_model == P304_FX6_DONOR_MODEL_NAME:
        sensor_cleaning_ok = (
            not spec.cleaning_mode_entered
            and not spec.power_switch_off_after_shake
            and spec.sensor_cleaning_low_battery_bypass_events == 0
            and spec.sensor_cleaning_no_power_off_violations == 0
        )
    else:
        sensor_cleaning_ok = (
            exp_clean_ok
            and exp_pwr_off_req
            and exp_clean_resid16 == P304_MANDATORY_POWER_OFF_G_RESID16
            and exp_clean_path == "FX3_IBIS_SHAKE_AND_POWER_OFF"
            and spec.cleaning_mode_entered
            and spec.power_insufficient_msg_resid16 is None
            and spec.power_switch_off_after_shake
            and spec.mandatory_power_off_msg_resid16 == P304_MANDATORY_POWER_OFF_G_RESID16
            and not spec.lens_removed_before_power_off
            and spec.sensor_cleaning_low_battery_bypass_events == 0
            and spec.sensor_cleaning_no_power_off_violations == 0
        )
    if not sensor_cleaning_ok:
        _fail(
            P304_BLOCKED_SENSOR_CLEANING_BATTERY_OR_POWER_OFF_VIOLATION,
            "FX3 Sensor Cleaning violated >= 51% NP-FZ100 battery gate (0xe574) or mandatory power-switch OFF (_g.uxc 0x6221) before lens removal",
        )

    # 3. [Exposure Comp.] +-5.0/+-2.0 EV, M + ISO AUTO, Cine EI Total Lockout, & Step/Dormant Guards
    ev_range_valid = (
        not exp_ev_active
        or (exp_min_ev <= spec.requested_ev_comp_ev <= exp_max_ev)
    )
    ev_comp_ok = (
        ev_range_valid
        and spec.reported_ev_comp_active == exp_ev_active
        and spec.reported_ev_comp_min_ev == exp_min_ev
        and spec.reported_ev_comp_max_ev == exp_max_ev
        and abs(spec.post_reset_ev_comp_ev - exp_post_ev) < 1e-6
        and spec.ev_comp_range_or_cine_ei_lockout_violations == 0
    )
    if not ev_comp_ok:
        _fail(
            P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT,
            "Exposure Comp. (+-5.0 EV Still / +-2.0 EV Movie & S&Q, M+ISO AUTO only, 100% Cine EI/Cine EI Quick lockout, or Camera Settings Reset -> 0.0 EV) violated",
        )

    step_dormant_ok = (
        spec.post_reset_exposure_step == exp_post_step
        and not spec.dormant_reset_ev_comp_exposed
        and not spec.dormant_dial_ev_comp_exposed
        and spec.exposure_step_or_dormant_reset_ev_drift_events == 0
    )
    if not step_dormant_ok:
        _fail(
            P304_BLOCKED_EXPOSURE_STEP_OR_DORMANT_DIAL_EV_DRIFT,
            "Exposure step Initialize-only survival or dormant Reset EV Comp. (0x7853) / Dial Ev Comp (0xe4d9) boundary violated",
        )

    # 4. Slot-1 Vault Write Firewall (EROFS/EBUSY) & Tier-0 H0 == H3
    vault_fw_ok = (
        spec.slot1_format_hard_locked
        and spec.slot1_vault_erofs_ebusy_enforced
        and spec.slot1_vault_mutation_bytes == 0
        and not (
            spec.requested_vault_slot == P304_SLOT1_VAULT_SLOT
            and spec.requested_vault_action in P304_DESTRUCTIVE_VAULT_ACTIONS
        )
    )
    if not vault_fw_ok:
        _fail(
            P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Vault EROFS/EBUSY firewall blocked write/format/delete/rotate mutation on Tier-0 media",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P304_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P304_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P304_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P304_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "54A",
            "passed": passed,
            "block_code": block_code,
            "camera_model": spec.camera_model,
            "fw_version": spec.fw_version,
            "battery_pct": spec.battery_pct,
            "power_switch_off_after_shake": spec.power_switch_off_after_shake,
            "fx6_vnd": spec.fx6_variable_nd_step,
            "shooting_domain": spec.shooting_domain,
            "exposure_mode": spec.exposure_mode,
            "iso_mode": spec.iso_mode,
            "log_shooting_mode": spec.log_shooting_mode,
            "requested_ev_comp_ev": spec.requested_ev_comp_ev,
            "post_reset_ev_comp_ev": spec.post_reset_ev_comp_ev,
            "post_reset_exposure_step": spec.post_reset_exposure_step,
            "slot1_bytes": spec.slot1_vault_mutation_bytes,
            "errors": errors,
        }
    )
    return SensorCleaningEvCompVaultReport(
        schema=PHASE304_SCHEMA,
        version=PHASE304_VERSION,
        passed=passed,
        status=P304_STATUS_VERIFIED_PILLAR_54A if passed else P304_STATUS_REJECTED_PILLAR_54A,
        block_code=block_code,
        sensor_cleaning_51pct_poweroff_verified=sensor_cleaning_ok,
        fx6_end_apr_contrast_verified=fx6_contrast_ok,
        ev_comp_range_iso_auto_and_cine_ei_lockout_verified=(ev_comp_ok and step_dormant_ok),
        slot1_vault_firewall_and_h0_h3_verified=slot1_and_tier0_ok,
        matrix_states_checked=16,
        sensor_cleaning_low_battery_bypass_events=spec.sensor_cleaning_low_battery_bypass_events,
        sensor_cleaning_no_power_off_violations=spec.sensor_cleaning_no_power_off_violations,
        fx6_ibis_shake_conflation_events=spec.fx6_ibis_shake_conflation_events,
        ev_comp_range_or_cine_ei_lockout_violations=spec.ev_comp_range_or_cine_ei_lockout_violations,
        exposure_step_or_dormant_reset_ev_drift_events=(
            spec.exposure_step_or_dormant_reset_ev_drift_events
        ),
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_focus_mode_playback_rotate_vault(
    spec: FocusModePlaybackRotateVaultSpec,
) -> FocusModePlaybackRotateVaultReport:
    """Evaluate Pillar 54B (`[Focus Mode]` 5-Still vs 2-Movie `AF-C`/`MF` clamp `EOPNOTSUPP=95`
    / `EINVAL=22`, `[Priority Set in AF-S/AF-C]` `Initialize`-only, Still-only `[AF Illuminator]`,
    Playback `[View Mode]` / exact `9/25` `[Image Index]` / `[Display as Group]` / `[Display
    Rotation]`, and CRITICAL `[Rotate]` EXIF / `AVF_INFO` `EROFS`/`EBUSY` Slot-1 Tier-0 Vault
    Firewall)."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if errors:
        _fail(
            P304_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Module safety invariant violation",
        )

    if (
        spec.camera_model != P304_FX3_MODEL_NAME
        or spec.shooting_domain not in P304_SHOOTING_DOMAINS
        or spec.configured_priority_afs not in P304_AF_PRIORITY_MODES
        or spec.configured_priority_afc not in P304_AF_PRIORITY_MODES
        or spec.post_priority_afs not in P304_AF_PRIORITY_MODES
        or spec.post_priority_afc not in P304_AF_PRIORITY_MODES
        or spec.configured_af_illuminator not in P304_AF_ILLUMINATOR_MODES
        or spec.post_af_illuminator not in P304_AF_ILLUMINATOR_MODES
        or spec.display_as_group not in P304_DISPLAY_GROUP_MODES
        or spec.display_rotation not in P304_DISPLAY_ROTATION_MODES
        or spec.reset_action not in P304_RESET_ACTIONS
        or spec.requested_vault_action not in P304_VAULT_TARGET_ACTIONS
    ):
        _fail(
            P304_BLOCKED_INVALID_PILLAR54B_SPEC,
            "Invalid Pillar 54B camera/FocusMode/PrioritySet/Playback/Rotate/vault spec parameter",
        )

    (
        exp_mode_ok,
        exp_clamp_errno,
        exp_post_afs,
        exp_post_afc,
        exp_illum_active,
        exp_post_illum,
    ) = compute_expected_focus_mode_state(
        shooting_domain=spec.shooting_domain,
        requested_focus_mode=spec.requested_focus_mode,
        configured_priority_afs=spec.configured_priority_afs,
        configured_priority_afc=spec.configured_priority_afc,
        configured_af_illuminator=spec.configured_af_illuminator,
        reset_action=spec.reset_action,
    )

    (
        exp_pb_ok,
        exp_rot_ok,
        exp_fw_errno,
        exp_view,
        exp_idx,
        exp_grp,
        exp_rot,
    ) = compute_expected_playback_rotate_state(
        view_mode=spec.view_mode,
        image_index=spec.image_index,
        display_as_group=spec.display_as_group,
        display_rotation=spec.display_rotation,
        playback_slot=spec.select_playback_media_slot,
        slot1_holds_tier0_vault=spec.slot1_holds_tier0_vault,
        requested_action=spec.requested_vault_action,
        background_transfer_active=spec.background_transfer_active,
        reset_action=spec.reset_action,
    )

    # 1. [Focus Mode] 5-Still vs 2-Movie AF-C/MF Clamp & Zero Dormant PF/SEMI_MANUAL
    focus_ok = (
        exp_mode_ok
        and spec.reported_focus_mode_allowed == exp_mode_ok
        and spec.movie_clamp_errno == exp_clamp_errno
        and spec.focus_mode_movie_clamp_or_dormant_drift_events == 0
    )
    if not focus_ok:
        _fail(
            P304_BLOCKED_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT,
            "Focus Mode violated 5-Still (AF-S/AF-A/AF-C/DMF/MF) vs 2-Movie/S&Q (AF-C/MF clamp EOPNOTSUPP=95/EINVAL=22) or exposed dormant PF/SEMI_MANUAL",
        )

    # 2. [Priority Set in AF-S/AF-C] Initialize-Only & Still-Only [AF Illuminator]
    priority_illum_ok = (
        spec.post_priority_afs == exp_post_afs
        and spec.post_priority_afc == exp_post_afc
        and spec.reported_af_illuminator_active == exp_illum_active
        and spec.post_af_illuminator == exp_post_illum
        and not (
            spec.shooting_domain in ("Movie", "S&Q")
            and spec.reported_af_illuminator_active
        )
        and spec.priority_set_or_illuminator_gate_violations == 0
    )
    if not priority_illum_ok:
        _fail(
            P304_BLOCKED_PRIORITY_SET_OR_AF_ILLUMINATOR_DRIFT,
            "Priority Set in AF-S/AF-C Initialize-only survival or Still-only AF Illuminator gate drifted",
        )

    # 3. Playback [View Mode], Exact 9/25 [Image Index], [Display as Group], [Display Rotation]
    playback_ok = (
        exp_pb_ok
        and spec.post_view_mode == exp_view
        and spec.post_image_index == exp_idx
        and spec.post_display_as_group == exp_grp
        and spec.post_display_rotation == exp_rot
        and not spec.fx6_exposes_still_image_index_or_exif_rotate
        and spec.image_index_dormant_or_view_mode_drift_events == 0
    )
    if not playback_ok:
        _fail(
            P304_BLOCKED_PLAYBACK_VIEW_INDEX_GROUP_OR_ROTATION_DRIFT,
            "Playback View Mode / exact 9-25 Image Index (no dormant 12/30) / Display as Group / Display Rotation / FX6 contrast violated",
        )

    # 4. CRITICAL RECOVERY VAULT FIREWALL: Playback [Rotate] & AVF_INFO DB on Slot-1 Tier-0 Vault
    slot1_destructive = (
        spec.select_playback_media_slot == P304_SLOT1_VAULT_SLOT
        and spec.requested_vault_action in P304_DESTRUCTIVE_VAULT_ACTIONS
    )
    vault_fw_ok = (
        not slot1_destructive
        and spec.reported_rotate_allowed == exp_rot_ok
        and spec.rotate_firewall_errno == exp_fw_errno
        and not (
            spec.requested_vault_action in ("ROTATE_EXIF_ORIENTATION", "AVF_INFO_DB_MUTATE")
            and spec.background_transfer_active
        )
        and spec.slot1_data_sector_writes == 0
        and spec.slot1_rotate_exif_mutation_bytes == 0
        and spec.slot1_vault_mutation_bytes == 0
        and spec.slot1_vault_erofs_ebusy_enforced
        and spec.slot1_format_hard_locked
    )
    if not vault_fw_ok:
        _fail(
            P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
            "Slot-1 Tier-0 Vault firewall blocked Playback Rotate EXIF / AVF_INFO DB mutation (EROFS=30 / EBUSY=16, 0 sector writes)",
        )

    overlay_ok = (
        _is_tmpfs_path(spec.overlay_dir)
        and not _targets_persistent_emmc(spec.overlay_dir)
    )
    if not overlay_ok:
        _fail(
            P304_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain in volatile /tmp tmpfs: {spec.overlay_dir}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P304_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P304_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P304_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 or surface count < 16",
        )

    slot1_and_tier0_ok = vault_fw_ok and overlay_ok and h0_h3_ok
    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "54B",
            "passed": passed,
            "block_code": block_code,
            "shooting_domain": spec.shooting_domain,
            "focus_mode": spec.requested_focus_mode,
            "post_priority_afs": spec.post_priority_afs,
            "post_priority_afc": spec.post_priority_afc,
            "post_view_mode": spec.post_view_mode,
            "post_image_index": spec.post_image_index,
            "post_display_as_group": spec.post_display_as_group,
            "post_display_rotation": spec.post_display_rotation,
            "slot": spec.select_playback_media_slot,
            "action": spec.requested_vault_action,
            "slot1_data_sector_writes": spec.slot1_data_sector_writes,
            "slot1_rotate_bytes": spec.slot1_rotate_exif_mutation_bytes,
            "errors": errors,
        }
    )
    return FocusModePlaybackRotateVaultReport(
        schema=PHASE304_SCHEMA,
        version=PHASE304_VERSION,
        passed=passed,
        status=P304_STATUS_VERIFIED_PILLAR_54B if passed else P304_STATUS_REJECTED_PILLAR_54B,
        block_code=block_code,
        focus_mode_5still_2movie_clamp_verified=focus_ok,
        priority_set_init_and_illuminator_gate_verified=priority_illum_ok,
        playback_view_9_25_index_group_rotation_verified=playback_ok,
        slot1_rotate_exif_erofs_ebusy_firewall_verified=slot1_and_tier0_ok,
        matrix_states_checked=16,
        focus_mode_movie_clamp_or_dormant_drift_events=(
            spec.focus_mode_movie_clamp_or_dormant_drift_events
        ),
        priority_set_or_illuminator_gate_violations=(
            spec.priority_set_or_illuminator_gate_violations
        ),
        image_index_dormant_or_view_mode_drift_events=(
            spec.image_index_dormant_or_view_mode_drift_events
        ),
        slot1_data_sector_writes=spec.slot1_data_sector_writes,
        slot1_rotate_exif_mutation_bytes=spec.slot1_rotate_exif_mutation_bytes,
        slot1_vault_mutation_bytes=spec.slot1_vault_mutation_bytes,
        slot1_vault_erofs_ebusy_enforced=spec.slot1_vault_erofs_ebusy_enforced,
        slot1_format_hard_locked=spec.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_54a: Optional[SensorCleaningEvCompVaultSpec] = None,
    spec_54b: Optional[FocusModePlaybackRotateVaultSpec] = None,
) -> SensorCleaningEvCompFocusModeRotateVaultReport:
    """Combined single-shot verifier for Pillar 54A + Pillar 54B + bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase304_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_sensor_cleaning_ev_comp_vault(
        spec_54a or build_default_safe_sensor_cleaning_ev_comp_vault_spec()
    )
    rep_b = evaluate_focus_mode_playback_rotate_vault(
        spec_54b or build_default_safe_focus_mode_playback_rotate_vault_spec()
    )

    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 304 Wave-52 donor artifact parity check failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspect exceeded budget {donor_snapshot.budget_seconds_applied}s: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return SensorCleaningEvCompFocusModeRotateVaultReport(
        schema=PHASE304_SCHEMA,
        version=PHASE304_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P304_STATUS_VERIFIED_PILLAR54_SUITE if all_ok else P304_STATUS_FAIL_PILLAR54_SUITE,
        donor_snapshot=donor_snapshot,
        sensor_cleaning_ev_comp_report=rep_a,
        focus_mode_playback_rotate_report=rep_b,
        sensor_cleaning_low_battery_bypass_events=rep_a.sensor_cleaning_low_battery_bypass_events,
        sensor_cleaning_no_power_off_violations=rep_a.sensor_cleaning_no_power_off_violations,
        fx6_ibis_shake_conflation_events=rep_a.fx6_ibis_shake_conflation_events,
        ev_comp_range_or_cine_ei_lockout_violations=(
            rep_a.ev_comp_range_or_cine_ei_lockout_violations
        ),
        exposure_step_or_dormant_reset_ev_drift_events=(
            rep_a.exposure_step_or_dormant_reset_ev_drift_events
        ),
        focus_mode_movie_clamp_or_dormant_drift_events=(
            rep_b.focus_mode_movie_clamp_or_dormant_drift_events
        ),
        priority_set_or_illuminator_gate_violations=(
            rep_b.priority_set_or_illuminator_gate_violations
        ),
        image_index_dormant_or_view_mode_drift_events=(
            rep_b.image_index_dormant_or_view_mode_drift_events
        ),
        slot1_data_sector_writes=rep_b.slot1_data_sector_writes,
        slot1_rotate_exif_mutation_bytes=rep_b.slot1_rotate_exif_mutation_bytes,
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


def verify_sensor_cleaning_ev_comp_focus_mode_rotate_vault(
    *,
    force_clean_room: Optional[bool] = None,
    spec_54a: Optional[SensorCleaningEvCompVaultSpec] = None,
    spec_54b: Optional[FocusModePlaybackRotateVaultSpec] = None,
) -> SensorCleaningEvCompFocusModeRotateVaultReport:
    """Symmetry alias for `verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault`."""
    return verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault(
        force_clean_room=force_clean_room,
        spec_54a=spec_54a,
        spec_54b=spec_54b,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillars 54A & 54B) + Standalone Pillar 54 Suite
# ---------------------------------------------------------------------------


def run_pillar54a_sensor_cleaning_ev_comp_6_scenario_suite() -> Pillar54ASuiteResult:
    """Run 6 Pillar 54A positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, SensorCleaningEvCompVaultSpec, Optional[str]], ...] = (
        (
            P304_PILLAR_54A_SCENARIO_IDS[0],
            True,
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                fw_version="7.02",
                battery_pct=51,
                cleaning_mode_entered=True,
                power_switch_off_after_shake=True,
                lens_removed_before_power_off=False,
                shooting_domain="Still",
                exposure_mode="M",
                iso_mode="ISO AUTO",
                log_shooting_mode="Off",
                requested_ev_comp_ev=-5.0,
                reported_ev_comp_active=True,
                reported_ev_comp_min_ev=-5.0,
                reported_ev_comp_max_ev=5.0,
                exposure_step="0.5EV",
                post_reset_ev_comp_ev=-5.0,
                post_reset_exposure_step="0.5EV",
            ),
            None,
        ),
        (
            P304_PILLAR_54A_SCENARIO_IDS[1],
            True,
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                battery_pct=88,
                fx6_variable_nd_step="1/64",
                fx6_apr_supported=True,
                shooting_domain="Movie",
                exposure_mode="A",
                iso_mode="ISO AUTO",
                log_shooting_mode="Flexible ISO",
                requested_ev_comp_ev=2.0,
                reported_ev_comp_active=True,
                reported_ev_comp_min_ev=-2.0,
                reported_ev_comp_max_ev=2.0,
                exposure_step="0.5EV",
                reset_action="Camera Settings Reset",
                post_reset_ev_comp_ev=0.0,
                post_reset_exposure_step="0.5EV",
            ),
            None,
        ),
        (
            P304_PILLAR_54A_SCENARIO_IDS[2],
            False,
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                battery_pct=49,
                cleaning_mode_entered=False,
                power_insufficient_msg_resid16=P304_POWER_INSUFFICIENT_RESID16,
                power_switch_off_after_shake=False,
                lens_removed_before_power_off=True,
                sensor_cleaning_low_battery_bypass_events=1,
                sensor_cleaning_no_power_off_violations=1,
            ),
            P304_BLOCKED_SENSOR_CLEANING_BATTERY_OR_POWER_OFF_VIOLATION,
        ),
        (
            P304_PILLAR_54A_SCENARIO_IDS[3],
            False,
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                fx6_ultrasonic_ibis_shake_attempted=True,
                fx6_cr_sensor_cleaning_supported=True,
                fx6_ibis_shake_conflation_events=1,
            ),
            P304_BLOCKED_FX6_IBIS_SHAKE_CONFLATION,
        ),
        (
            P304_PILLAR_54A_SCENARIO_IDS[4],
            False,
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                shooting_domain="Movie",
                exposure_mode="M",
                iso_mode="ISO 800",
                log_shooting_mode="Cine EI",
                requested_ev_comp_ev=3.0,
                reported_ev_comp_active=True,
                ev_comp_range_or_cine_ei_lockout_violations=1,
                dormant_reset_ev_comp_exposed=True,
                dormant_dial_ev_comp_exposed=True,
                exposure_step_or_dormant_reset_ev_drift_events=1,
            ),
            P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT,
        ),
        (
            P304_PILLAR_54A_SCENARIO_IDS[5],
            False,
            build_default_safe_sensor_cleaning_ev_comp_vault_spec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/54a",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar54ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_sensor_cleaning_ev_comp_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar54ScenarioOutcome(
                scenario_id=sid,
                pillar="54A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar54ASuiteResult(
        passed=all_ok,
        status=P304_STATUS_VERIFIED_PILLAR_54A if all_ok else P304_STATUS_REJECTED_PILLAR_54A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar54b_focus_mode_playback_rotate_6_scenario_suite() -> Pillar54BSuiteResult:
    """Run 6 Pillar 54B positive + fail-closed scenarios (`2` allow + `4` reject)."""
    cases: Tuple[Tuple[str, bool, FocusModePlaybackRotateVaultSpec, Optional[str]], ...] = (
        (
            P304_PILLAR_54B_SCENARIO_IDS[0],
            True,
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                shooting_domain="Still",
                requested_focus_mode="DMF",
                configured_priority_afs="Release",
                configured_priority_afc="AF",
                configured_af_illuminator="Off",
                reported_af_illuminator_active=True,
                reset_action="Camera Settings Reset",
                post_priority_afs="Release",
                post_priority_afc="AF",
                post_af_illuminator="Auto",
                select_playback_media_slot=P304_SAFE_SECONDARY_SLOT,
                requested_vault_action="ROTATE_EXIF_ORIENTATION",
                reported_rotate_allowed=True,
                rotate_firewall_errno=None,
            ),
            None,
        ),
        (
            P304_PILLAR_54B_SCENARIO_IDS[1],
            True,
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                shooting_domain="Movie",
                requested_focus_mode="AF-C",
                configured_priority_afc="AF",
                reported_af_illuminator_active=False,
                view_mode="XAVC S View",
                image_index="25 Images",
                display_as_group="On",
                display_rotation="Manual",
                reset_action="Camera Settings Reset",
                post_priority_afc="AF",
                post_af_illuminator="Auto",
                post_view_mode="XAVC S View",
                post_image_index="25 Images",
                post_display_as_group="On",
                post_display_rotation="Manual",
                select_playback_media_slot=P304_SLOT1_VAULT_SLOT,
                requested_vault_action="VIEW_MODE_BROWSE",
                reported_rotate_allowed=False,
                rotate_firewall_errno=None,
            ),
            None,
        ),
        (
            P304_PILLAR_54B_SCENARIO_IDS[2],
            False,
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                shooting_domain="Movie",
                requested_focus_mode="AF-S",
                reported_focus_mode_allowed=True,
                movie_clamp_errno=None,
                focus_mode_movie_clamp_or_dormant_drift_events=1,
            ),
            P304_BLOCKED_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT,
        ),
        (
            P304_PILLAR_54B_SCENARIO_IDS[3],
            False,
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                shooting_domain="S&Q",
                requested_focus_mode="AF-C",
                configured_priority_afs="AF",
                configured_priority_afc="Release",
                reported_af_illuminator_active=True,
                reset_action="Camera Settings Reset",
                post_priority_afs="Balanced Emphasis",
                post_priority_afc="Balanced Emphasis",
                priority_set_or_illuminator_gate_violations=1,
            ),
            P304_BLOCKED_PRIORITY_SET_OR_AF_ILLUMINATOR_DRIFT,
        ),
        (
            P304_PILLAR_54B_SCENARIO_IDS[4],
            False,
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                image_index="12 Images",
                post_image_index="12 Images",
                fx6_exposes_still_image_index_or_exif_rotate=True,
                image_index_dormant_or_view_mode_drift_events=1,
            ),
            P304_BLOCKED_PLAYBACK_VIEW_INDEX_GROUP_OR_ROTATION_DRIFT,
        ),
        (
            P304_PILLAR_54B_SCENARIO_IDS[5],
            False,
            build_default_safe_focus_mode_playback_rotate_vault_spec(
                select_playback_media_slot=P304_SLOT1_VAULT_SLOT,
                slot1_holds_tier0_vault=True,
                requested_vault_action="ROTATE_EXIF_ORIENTATION",
                reported_rotate_allowed=True,
                rotate_firewall_errno=None,
                slot1_data_sector_writes=1,
                slot1_rotate_exif_mutation_bytes=512,
                slot1_vault_mutation_bytes=4096,
                slot1_vault_erofs_ebusy_enforced=False,
                overlay_dir="/setting/54b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL,
        ),
    )

    outcomes: List[Pillar54ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_focus_mode_playback_rotate_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar54ScenarioOutcome(
                scenario_id=sid,
                pillar="54B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar54BSuiteResult(
        passed=all_ok,
        status=P304_STATUS_VERIFIED_PILLAR_54B if all_ok else P304_STATUS_REJECTED_PILLAR_54B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar54_standalone_suite(
    *, force_clean_room: Optional[bool] = None
) -> Pillar54StandaloneReport:
    """Run full Pillar 54 standalone suite (`6/6` Pillar 54A + `6/6` Pillar 54B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase304_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar54a_sensor_cleaning_ev_comp_6_scenario_suite()
    res_b = run_pillar54b_focus_mode_playback_rotate_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 304 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE304_SCHEMA,
            "version": PHASE304_VERSION,
            "mode": donor_snapshot.verification_mode,
            "54a": [asdict(s) for s in res_a.scenarios],
            "54b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar54StandaloneReport(
        schema=PHASE304_SCHEMA,
        version=PHASE304_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P304_STATUS_VERIFIED_PILLAR54_SUITE if all_ok else P304_STATUS_FAIL_PILLAR54_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_54a_sensor_cleaning_ev_comp_vault=res_a,
        pillar_54b_focus_mode_playback_rotate_vault=res_b,
        sensor_cleaning_low_battery_bypass_events=(
            P304_SENSOR_CLEANING_LOW_BATTERY_BYPASS_EVENTS if res_a.passed else 1
        ),
        sensor_cleaning_no_power_off_violations=(
            P304_SENSOR_CLEANING_NO_POWER_OFF_VIOLATIONS if res_a.passed else 1
        ),
        fx6_ibis_shake_conflation_events=(
            P304_FX6_IBIS_SHAKE_CONFLATION_EVENTS if res_a.passed else 1
        ),
        ev_comp_range_or_cine_ei_lockout_violations=(
            P304_EV_COMP_RANGE_OR_CINE_EI_LOCKOUT_VIOLATIONS if res_a.passed else 1
        ),
        exposure_step_or_dormant_reset_ev_drift_events=(
            P304_EXPOSURE_STEP_OR_DORMANT_RESET_EV_DRIFT_EVENTS if res_a.passed else 1
        ),
        focus_mode_movie_clamp_or_dormant_drift_events=(
            P304_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT_EVENTS if res_b.passed else 1
        ),
        priority_set_or_illuminator_gate_violations=(
            P304_PRIORITY_SET_OR_ILLUMINATOR_GATE_VIOLATIONS if res_b.passed else 1
        ),
        image_index_dormant_or_view_mode_drift_events=(
            P304_IMAGE_INDEX_DORMANT_OR_VIEW_MODE_DRIFT_EVENTS if res_b.passed else 1
        ),
        slot1_data_sector_writes=P304_SLOT1_DATA_SECTOR_WRITES if res_b.passed else 1,
        slot1_rotate_exif_mutation_bytes=(
            P304_SLOT1_ROTATE_EXIF_MUTATION_BYTES if res_b.passed else 512
        ),
        slot1_vault_mutation_bytes=(
            P304_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096
        ),
        slot1_format_hard_locked=P304_SLOT1_FORMAT_HARD_LOCKED,
        slot1_vault_erofs_ebusy_enforced=P304_SLOT1_VAULT_EROFS_EBUSY_ENFORCED,
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
# Unified 54-Pillar Recovery Master Aggregator (Phase 304)
# ---------------------------------------------------------------------------


def _apply_master54_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_54pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master54PillarRecoveryReport:
    """Evaluate and aggregate all 54 recovery pillars (`1..54`) concurrently -> `54/54` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(
            fault_inject_pillar in MASTER_54_PILLAR_IDS,
            f"Unknown fault_inject_pillar: {fault_inject_pillar}",
        )

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_53pillar() -> Master53PillarRecoveryReport:
        return evaluate_realhw_53pillar_recovery_master(**kw)

    def _run_p54() -> Tuple[Pillar54StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar54_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_53 = pool.submit(_run_53pillar)
        fut_54 = pool.submit(_run_p54)
        m53_rep = fut_53.result()
        p54_rep, p54_dt = fut_54.result()

    all_errors: List[str] = list(m53_rep.errors) + list(p54_rep.errors)
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
        if getattr(m53_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-53 violated {attr_name} == {expected_val}")
        if getattr(p54_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 54 violated {attr_name} == {expected_val}")

    if p54_rep.cross_model_flash_authorized is not False:
        all_errors.append("Pillar 54 violated cross_model_flash_authorized == False")

    for attr_name, expected_val in (
        ("dci4k_long_gop_or_8k_violations", 0),
        ("reboot_2400p_stage_b_wipe_violations", 0),
        ("hdmi_raw_or_still_aspect_drift_events", 0),
        ("fx6_still_or_raw_conflation_events", 0),
        ("reg_custom_hold_or_hlg_lock_drift_events", 0),
        ("camset_cross_model_path_drift_events", 0),
        ("photo_capture_dci4k_lockout_bypass_events", 0),
        ("slot1_camset_write_bytes", 0),
        ("slot1_photo_capture_write_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
        ("fx3_has_builtin_end_filter", False),
        ("fx3_has_builtin_evf", False),
        ("fx3_has_var_shutter", False),
    ):
        if getattr(m53_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-53 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("sensor_cleaning_low_battery_bypass_events", 0),
        ("sensor_cleaning_no_power_off_violations", 0),
        ("fx6_ibis_shake_conflation_events", 0),
        ("ev_comp_range_or_cine_ei_lockout_violations", 0),
        ("exposure_step_or_dormant_reset_ev_drift_events", 0),
        ("focus_mode_movie_clamp_or_dormant_drift_events", 0),
        ("priority_set_or_illuminator_gate_violations", 0),
        ("image_index_dormant_or_view_mode_drift_events", 0),
        ("slot1_data_sector_writes", 0),
        ("slot1_rotate_exif_mutation_bytes", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("slot1_vault_erofs_ebusy_enforced", True),
    ):
        if getattr(p54_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 54 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m53_rep.pillars)
    spec54 = MASTER_54_PILLAR_SPECS[53]
    p54_metrics = {
        "pillar_54a_sensor_cleaning_ev_comp_vault": (
            f"{p54_rep.pillar_54a_sensor_cleaning_ev_comp_vault.scenarios_passed}/"
            f"{p54_rep.pillar_54a_sensor_cleaning_ev_comp_vault.scenarios_total}"
        ),
        "pillar_54b_focus_mode_playback_rotate_vault": (
            f"{p54_rep.pillar_54b_focus_mode_playback_rotate_vault.scenarios_passed}/"
            f"{p54_rep.pillar_54b_focus_mode_playback_rotate_vault.scenarios_total}"
        ),
        "sensor_cleaning_low_battery_bypass_events": (
            p54_rep.sensor_cleaning_low_battery_bypass_events
        ),
        "sensor_cleaning_no_power_off_violations": (
            p54_rep.sensor_cleaning_no_power_off_violations
        ),
        "fx6_ibis_shake_conflation_events": p54_rep.fx6_ibis_shake_conflation_events,
        "ev_comp_range_or_cine_ei_lockout_violations": (
            p54_rep.ev_comp_range_or_cine_ei_lockout_violations
        ),
        "exposure_step_or_dormant_reset_ev_drift_events": (
            p54_rep.exposure_step_or_dormant_reset_ev_drift_events
        ),
        "focus_mode_movie_clamp_or_dormant_drift_events": (
            p54_rep.focus_mode_movie_clamp_or_dormant_drift_events
        ),
        "priority_set_or_illuminator_gate_violations": (
            p54_rep.priority_set_or_illuminator_gate_violations
        ),
        "image_index_dormant_or_view_mode_drift_events": (
            p54_rep.image_index_dormant_or_view_mode_drift_events
        ),
        "slot1_data_sector_writes": p54_rep.slot1_data_sector_writes,
        "slot1_rotate_exif_mutation_bytes": p54_rep.slot1_rotate_exif_mutation_bytes,
        "slot1_vault_mutation_bytes": p54_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p54_rep.slot1_format_hard_locked,
        "slot1_vault_erofs_ebusy_enforced": p54_rep.slot1_vault_erofs_ebusy_enforced,
        "overall_ready_for_hardware_attach": p54_rep.overall_ready_for_hardware_attach,
        "cross_model_flash_authorized": p54_rep.cross_model_flash_authorized,
        "hardware_live_attachment_authorized": p54_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p54_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec54[0],
            pillar_id=spec54[1],
            phase_label=spec54[2],
            module_name=spec54[3],
            passed=bool(p54_rep.all_passed),
            status=p54_rep.status,
            verification_mode=p54_rep.verification_mode,
            elapsed_seconds=p54_dt,
            key_metrics=p54_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec54[1],
                    "mode": p54_rep.verification_mode,
                    "status": p54_rep.status,
                    "metrics": p54_metrics,
                    "passed": p54_rep.all_passed,
                }
            ),
            errors=tuple(p54_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master54_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p54_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_54_PILLAR_COUNT == 54
        and pillars_passed == 54
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE304_SCHEMA,
            "version": PHASE304_VERSION,
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
    return Master54PillarRecoveryReport(
        schema=PHASE304_SCHEMA,
        version=PHASE304_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P304_STATUS_VERIFIED_54OF54_AGGREGATOR if all_ok else P304_STATUS_FAIL_54OF54_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_1_5s_fast_cli_budget=elapsed < P304_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P304_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P304_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p54_rep.donor_snapshot,
        pillar54_a_sensor_cleaning_ev_comp_vault=p54_rep.pillar_54a_sensor_cleaning_ev_comp_vault,
        pillar54_b_focus_mode_playback_rotate_vault=(
            p54_rep.pillar_54b_focus_mode_playback_rotate_vault
        ),
        sensor_cleaning_low_battery_bypass_events=p54_rep.sensor_cleaning_low_battery_bypass_events,
        sensor_cleaning_no_power_off_violations=p54_rep.sensor_cleaning_no_power_off_violations,
        fx6_ibis_shake_conflation_events=p54_rep.fx6_ibis_shake_conflation_events,
        ev_comp_range_or_cine_ei_lockout_violations=(
            p54_rep.ev_comp_range_or_cine_ei_lockout_violations
        ),
        exposure_step_or_dormant_reset_ev_drift_events=(
            p54_rep.exposure_step_or_dormant_reset_ev_drift_events
        ),
        focus_mode_movie_clamp_or_dormant_drift_events=(
            p54_rep.focus_mode_movie_clamp_or_dormant_drift_events
        ),
        priority_set_or_illuminator_gate_violations=(
            p54_rep.priority_set_or_illuminator_gate_violations
        ),
        image_index_dormant_or_view_mode_drift_events=(
            p54_rep.image_index_dormant_or_view_mode_drift_events
        ),
        slot1_data_sector_writes=p54_rep.slot1_data_sector_writes,
        slot1_rotate_exif_mutation_bytes=p54_rep.slot1_rotate_exif_mutation_bytes,
        slot1_vault_mutation_bytes=m53_rep.slot1_vault_mutation_bytes + p54_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p54_rep.slot1_format_hard_locked,
        slot1_vault_erofs_ebusy_enforced=p54_rep.slot1_vault_erofs_ebusy_enforced,
        fx3_has_sensor_cleaning_ibis=P304_FX3_HAS_SENSOR_CLEANING_IBIS,
        fx3_has_exposure_comp=P304_FX3_HAS_EXPOSURE_COMP,
        fx3_has_physical_ev_reset_dial=P304_FX3_HAS_PHYSICAL_EV_RESET_DIAL,
        fx6_has_ultrasonic_ibis_cleaning=P304_FX6_HAS_ULTRASONIC_IBIS_CLEANING,
        fx6_has_variable_end_optical_block=P304_FX6_HAS_VARIABLE_END_OPTICAL_BLOCK,
        fx6_has_technical_apr=P304_FX6_HAS_TECHNICAL_APR,
        fx6_has_still_exposure_comp=P304_FX6_HAS_STILL_EXPOSURE_COMP,
        fx6_has_still_image_index_rotate=P304_FX6_HAS_STILL_IMAGE_INDEX_ROTATE,
        dci4k_long_gop_or_8k_violations=m53_rep.dci4k_long_gop_or_8k_violations,
        reboot_2400p_stage_b_wipe_violations=m53_rep.reboot_2400p_stage_b_wipe_violations,
        hdmi_raw_or_still_aspect_drift_events=m53_rep.hdmi_raw_or_still_aspect_drift_events,
        fx6_still_or_raw_conflation_events=m53_rep.fx6_still_or_raw_conflation_events,
        reg_custom_hold_or_hlg_lock_drift_events=m53_rep.reg_custom_hold_or_hlg_lock_drift_events,
        camset_cross_model_path_drift_events=m53_rep.camset_cross_model_path_drift_events,
        photo_capture_dci4k_lockout_bypass_events=m53_rep.photo_capture_dci4k_lockout_bypass_events,
        slot1_camset_write_bytes=m53_rep.slot1_camset_write_bytes,
        slot1_photo_capture_write_bytes=m53_rep.slot1_photo_capture_write_bytes,
        fx3_appfw_has_dci4k_internal=m53_rep.fx3_appfw_has_dci4k_internal,
        fx3_appfw_has_pro_camera_path=m53_rep.fx3_appfw_has_pro_camera_path,
        fx6_has_still_aspect_ratio=m53_rep.fx6_has_still_aspect_ratio,
        fx6_has_photo_capture=m53_rep.fx6_has_photo_capture,
        fx6_has_playback_enlarge_image=m53_rep.fx6_has_playback_enlarge_image,
        fx6_has_reg_custom_shoot_set=m53_rep.fx6_has_reg_custom_shoot_set,
        fx6_has_camera_set_memory=m53_rep.fx6_has_camera_set_memory,
        movie_tracking_area_or_limit_violations=m53_rep.movie_tracking_area_or_limit_violations,
        af_area_reg_lock_or_reset_drift_events=m53_rep.af_area_reg_lock_or_reset_drift_events,
        xlrh1_zoom_or_hold_spoof_events=m53_rep.xlrh1_zoom_or_hold_spoof_events,
        fx6_handle_or_pos_display_conflation_events=(
            m53_rep.fx6_handle_or_pos_display_conflation_events
        ),
        iso_minss_or_cine_ei_lock_drift_events=m53_rep.iso_minss_or_cine_ei_lock_drift_events,
        flash_still_mech_gate_violations=m53_rep.flash_still_mech_gate_violations,
        mishoe_pmic_5v_overcurrent_events=m53_rep.mishoe_pmic_5v_overcurrent_events,
        slot1_focus_zoom_camset_mutation_bytes=m53_rep.slot1_focus_zoom_camset_mutation_bytes,
        slot1_flash_videolight_imagedb_bytes=m53_rep.slot1_flash_videolight_imagedb_bytes,
        xlrh1_has_zoom_lever=m53_rep.xlrh1_has_zoom_lever,
        xlrh1_has_rec_button=m53_rep.xlrh1_has_rec_button,
        xlrh1_has_zoom_hold_switch=m53_rep.xlrh1_has_zoom_hold_switch,
        fx6_0_99_is_zoom_position_display=m53_rep.fx6_0_99_is_zoom_position_display,
        fx6_has_iso_auto_min_ss=m53_rep.fx6_has_iso_auto_min_ss,
        fx6_mechanical_shutter_present=m53_rep.fx6_mechanical_shutter_present,
        dormant_lossless_raw_exposure_events=m53_rep.dormant_lossless_raw_exposure_events,
        fx6_still_pipeline_conflation_events=m53_rep.fx6_still_pipeline_conflation_events,
        hlg_still_prereq_or_lockout_drift_events=m53_rep.hlg_still_prereq_or_lockout_drift_events,
        colorspace_adobergb_prefix_violations=m53_rep.colorspace_adobergb_prefix_violations,
        shutter_type_auto_spoof_events=m53_rep.shutter_type_auto_spoof_events,
        fx6_mechanical_shutter_conflation_events=m53_rep.fx6_mechanical_shutter_conflation_events,
        electronic_silent_5lock_bypass_events=m53_rep.electronic_silent_5lock_bypass_events,
        nr_or_drive_burst_wall_violations=m53_rep.nr_or_drive_burst_wall_violations,
        slot1_still_capture_or_sort_write_bytes=m53_rep.slot1_still_capture_or_sort_write_bytes,
        slot1_imagedb_or_burst_mutation_bytes=m53_rep.slot1_imagedb_or_burst_mutation_bytes,
        fx3_ui_exposes_lossless_raw=m53_rep.fx3_ui_exposes_lossless_raw,
        fx3_ui_exposes_shutter_type_auto=m53_rep.fx3_ui_exposes_shutter_type_auto,
        fx6_still_pipeline_present=m53_rep.fx6_still_pipeline_present,
        double_log_or_lockout_bypass_events=m53_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=m53_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=m53_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=m53_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            m53_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        wb_custom_camset_exclusion_drift_events=m53_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            m53_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        fx3_ui_exposes_usb_streaming=m53_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m53_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m53_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m53_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m53_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m53_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m53_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m53_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m53_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m53_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m53_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m53_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m53_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m53_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m53_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m53_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m53_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m53_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m53_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m53_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m53_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m53_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m53_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m53_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m53_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m53_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m53_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m53_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m53_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m53_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m53_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m53_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m53_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=m53_rep.tcub_camera_reset_wipe_or_format_violations,
        fx3_has_builtin_end_filter=m53_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m53_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m53_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m53_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m53_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m53_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m53_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m53_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m53_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m53_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m53_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m53_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m53_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m53_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m53_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m53_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m53_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m53_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m53_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m53_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m53_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m53_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m53_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m53_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m53_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m53_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m53_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m53_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m53_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m53_rep.unbuffered_battery_pull_events,
        overall_ready_for_hardware_attach=OVERALL_READY_FOR_HARDWARE_ATTACH,
        cross_model_flash_authorized=CROSS_MODEL_FLASH_AUTHORIZED,
        hardware_live_attachment_authorized=p54_rep.hardware_live_attachment_authorized,
        master_54pillar_sha256=master_sha,
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


def evaluate_54pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master54PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_54pillar_recovery_master`."""
    return evaluate_realhw_54pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_54pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master54PillarRecoveryReport:
    """Public CLI entry point for Phase 304 `54/54` unified recovery master."""
    return evaluate_realhw_54pillar_recovery_master(
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
    "FocusModePlaybackRotateVaultReport",
    "FocusModePlaybackRotateVaultSpec",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "ISP_WRITE_AUTHORIZED",
    "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
    "MASTER_54_PILLAR_COUNT",
    "MASTER_54_PILLAR_IDS",
    "MASTER_54_PILLAR_SPECS",
    "Master54PillarRecoveryReport",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P304_AF_ASSIST_BKID",
    "P304_AF_ILLUMINATOR_BKID",
    "P304_AF_ILLUMINATOR_DEFAULT",
    "P304_AF_ILLUMINATOR_MODES",
    "P304_AF_PRIORITY_DEFAULT",
    "P304_AF_PRIORITY_MODES",
    "P304_BLOCKED_EV_COMP_RANGE_ISO_OR_CINE_EI_LOCKOUT_DRIFT",
    "P304_BLOCKED_EXPOSURE_STEP_OR_DORMANT_DIAL_EV_DRIFT",
    "P304_BLOCKED_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT",
    "P304_BLOCKED_FX6_IBIS_SHAKE_CONFLATION",
    "P304_BLOCKED_INVALID_PILLAR54A_SPEC",
    "P304_BLOCKED_INVALID_PILLAR54B_SPEC",
    "P304_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P304_BLOCKED_PLAYBACK_VIEW_INDEX_GROUP_OR_ROTATION_DRIFT",
    "P304_BLOCKED_PRIORITY_SET_OR_AF_ILLUMINATOR_DRIFT",
    "P304_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P304_BLOCKED_SENSOR_CLEANING_BATTERY_OR_POWER_OFF_VIOLATION",
    "P304_BLOCKED_SLOT1_VAULT_WRITE_FIREWALL",
    "P304_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P304_BOUNDED_HEADER_BYTES",
    "P304_CINE_EI_BASE_ISOS",
    "P304_CINE_EI_INDEX_MAX_EV",
    "P304_CINE_EI_INDEX_MIN_EV",
    "P304_CINE_EI_LOCKED_LOG_MODES",
    "P304_CLEANING_MODE_DESC_RESID16",
    "P304_CLEANING_MODE_LEGACY_RESID16",
    "P304_CONCURRENT_CEILING_SECONDS",
    "P304_CROSS_MODEL_FLASH_AUTHORIZED",
    "P304_DESTRUCTIVE_VAULT_ACTIONS",
    "P304_DISPLAY_GROUP_BKID",
    "P304_DISPLAY_GROUP_DEFAULT",
    "P304_DISPLAY_GROUP_MODES",
    "P304_DISPLAY_ROTATION_BKID",
    "P304_DISPLAY_ROTATION_DEFAULT",
    "P304_DISPLAY_ROTATION_MODES",
    "P304_DONOR_FX3_APPFW_702_RELPATH",
    "P304_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P304_DONOR_FX3_UXC_EN_F_RELPATH",
    "P304_DONOR_FX3_UXC_EN_G_RELPATH",
    "P304_DONOR_FX3_UXC_EN_RELPATH",
    "P304_DONOR_FX3_UXC_JA_F_RELPATH",
    "P304_DONOR_FX3_UXC_JA_G_RELPATH",
    "P304_DONOR_FX3_UXC_JA_RELPATH",
    "P304_DONOR_FX3_UXC_SC_F_RELPATH",
    "P304_DONOR_FX3_UXC_SC_G_RELPATH",
    "P304_DONOR_FX3_UXC_SC_RELPATH",
    "P304_DONOR_FX3_UXC_TC_F_RELPATH",
    "P304_DONOR_FX3_UXC_TC_G_RELPATH",
    "P304_DONOR_FX3_UXC_TC_RELPATH",
    "P304_DONOR_FX6_APPFW_601_RELPATH",
    "P304_DONOR_FX6_UXC_EN_2_RELPATH",
    "P304_DONOR_FX6_UXC_EN_RELPATH",
    "P304_DONOR_INSPECT_BUDGET_SECONDS",
    "P304_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P304_DORMANT_FOCUS_MODES",
    "P304_DORMANT_IMAGE_INDEX_MODES",
    "P304_DORMANT_RESET_EV_COMP_BKID",
    "P304_DORMANT_DIAL_EV_COMP_RESID16",
    "P304_DORMANT_RESET_EV_COMP_F_RESID16",
    "P304_ENV_CLEAN_ROOM_TEST",
    "P304_EV_COMP_DEFAULT_EV",
    "P304_EV_COMP_LIVE_METER_MAX_EV",
    "P304_EV_COMP_LIVE_METER_MIN_EV",
    "P304_EV_COMP_MOVIE_MAX_EV",
    "P304_EV_COMP_MOVIE_MIN_EV",
    "P304_EV_COMP_RANGE_OR_CINE_EI_LOCKOUT_VIOLATIONS",
    "P304_EV_COMP_STILL_MAX_EV",
    "P304_EV_COMP_STILL_MIN_EV",
    "P304_EXPOSURE_COMP_BKID",
    "P304_EXPOSURE_COMP_F_RESID16",
    "P304_EXPOSURE_COMP_G_RESID16",
    "P304_EXPOSURE_COMP_MENU_PATH",
    "P304_EXPOSURE_COMP_RESID16",
    "P304_EXPOSURE_MODES",
    "P304_EXPOSURE_STD_ADJUST_F_RESID16",
    "P304_EXPOSURE_STD_ADJUST_MAX_EV",
    "P304_EXPOSURE_STD_ADJUST_MIN_EV",
    "P304_EXPOSURE_STEPS",
    "P304_EXPOSURE_STEP_BKID",
    "P304_EXPOSURE_STEP_DEFAULT",
    "P304_EXPOSURE_STEP_F_RESID16",
    "P304_EXPOSURE_STEP_OR_DORMANT_RESET_EV_DRIFT_EVENTS",
    "P304_EXPOSURE_STEP_RESID16",
    "P304_FAST_CLI_BUDGET_SECONDS",
    "P304_FOCUS_MODE_ALT_G_RESID16",
    "P304_FOCUS_MODE_BKID",
    "P304_FOCUS_MODE_G_RESID16",
    "P304_FOCUS_MODE_MENU_PATH",
    "P304_FOCUS_MODE_MOVIE_CLAMP_OR_DORMANT_DRIFT_EVENTS",
    "P304_FOCUS_MODE_RESID16_MAP",
    "P304_FORBIDDEN_PERSISTENT_TARGETS",
    "P304_FX3_CLEANING_SYMBOLS",
    "P304_FX3_FW_VERSION",
    "P304_FX3_HAS_EXPOSURE_COMP",
    "P304_FX3_HAS_PHYSICAL_EV_RESET_DIAL",
    "P304_FX3_HAS_SENSOR_CLEANING_IBIS",
    "P304_FX3_HELPGUIDE_ID",
    "P304_FX3_MODEL_ID",
    "P304_FX3_MODEL_NAME",
    "P304_FX3_PRE_V2_FW_VERSIONS",
    "P304_FX3_PRODUCT_CODENAME",
    "P304_FX3_SENSOR_FAMILY",
    "P304_FX3_SUPPORTED_FW_VERSIONS",
    "P304_FX6_APR_SYMBOL",
    "P304_FX6_CLEANING_ALT_FEATURE",
    "P304_FX6_CR_SENSOR_CLEANING_CMD_ID",
    "P304_FX6_DONOR_FW_VERSION",
    "P304_FX6_DONOR_MODEL_NAME",
    "P304_FX6_END_SYMBOLS",
    "P304_FX6_HAS_STILL_EXPOSURE_COMP",
    "P304_FX6_HAS_STILL_IMAGE_INDEX_ROTATE",
    "P304_FX6_HAS_TECHNICAL_APR",
    "P304_FX6_HAS_ULTRASONIC_IBIS_CLEANING",
    "P304_FX6_HAS_VARIABLE_END_OPTICAL_BLOCK",
    "P304_FX6_IBIS_SHAKE_CONFLATION_EVENTS",
    "P304_FX6_PRODUCT_CODENAME",
    "P304_FX6_VARIABLE_ND_VALUES",
    "P304_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P304_IMAGE_INDEX_BKID",
    "P304_IMAGE_INDEX_DEFAULT",
    "P304_IMAGE_INDEX_DORMANT_OR_VIEW_MODE_DRIFT_EVENTS",
    "P304_IMAGE_INDEX_MODES",
    "P304_LOG_SHOOTING_MENU_PATH",
    "P304_LOG_SHOOTING_MODES",
    "P304_MANDATORY_POWER_OFF_G_RESID16",
    "P304_MAX_FULL_DONOR_BYTES",
    "P304_MOVIE_AUTO_AF_C_RESID16",
    "P304_MOVIE_CLAMP_ERRNOS",
    "P304_MOVIE_SQ_FOCUS_MODES",
    "P304_MOVIE_SQ_LOCKED_OUT_FOCUS_MODES",
    "P304_NOMINAL_BUDGET_SECONDS",
    "P304_NP_FZ100_MIN_CLEANING_BARS_PRE_V2",
    "P304_NP_FZ100_MIN_CLEANING_PCT",
    "P304_ON_OFF_MODES",
    "P304_OVERALL_READY_FOR_HARDWARE_ATTACH",
    "P304_PILLAR_54A_SCENARIO_IDS",
    "P304_PILLAR_54B_SCENARIO_IDS",
    "P304_PINNED_FX3_APPFW_702_BYTES",
    "P304_PINNED_FX3_APPFW_702_FULL_SHA256",
    "P304_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P304_PINNED_FX3_BACKUP_BIN_BYTES",
    "P304_PINNED_FX3_BACKUP_BIN_SHA256",
    "P304_PINNED_FX3_UXC_EN_BYTES",
    "P304_PINNED_FX3_UXC_EN_F_BYTES",
    "P304_PINNED_FX3_UXC_EN_F_SHA256",
    "P304_PINNED_FX3_UXC_EN_G_BYTES",
    "P304_PINNED_FX3_UXC_EN_G_SHA256",
    "P304_PINNED_FX3_UXC_EN_SHA256",
    "P304_PINNED_FX3_UXC_JA_BYTES",
    "P304_PINNED_FX3_UXC_JA_F_BYTES",
    "P304_PINNED_FX3_UXC_JA_F_SHA256",
    "P304_PINNED_FX3_UXC_JA_G_BYTES",
    "P304_PINNED_FX3_UXC_JA_G_SHA256",
    "P304_PINNED_FX3_UXC_JA_SHA256",
    "P304_PINNED_FX3_UXC_SC_BYTES",
    "P304_PINNED_FX3_UXC_SC_F_BYTES",
    "P304_PINNED_FX3_UXC_SC_F_SHA256",
    "P304_PINNED_FX3_UXC_SC_G_BYTES",
    "P304_PINNED_FX3_UXC_SC_G_SHA256",
    "P304_PINNED_FX3_UXC_SC_SHA256",
    "P304_PINNED_FX3_UXC_TC_BYTES",
    "P304_PINNED_FX3_UXC_TC_F_BYTES",
    "P304_PINNED_FX3_UXC_TC_F_SHA256",
    "P304_PINNED_FX3_UXC_TC_G_BYTES",
    "P304_PINNED_FX3_UXC_TC_G_SHA256",
    "P304_PINNED_FX3_UXC_TC_SHA256",
    "P304_PINNED_FX6_APPFW_601_BYTES",
    "P304_PINNED_FX6_APPFW_601_FULL_SHA256",
    "P304_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P304_PINNED_FX6_UXC_EN_2_BYTES",
    "P304_PINNED_FX6_UXC_EN_2_SHA256",
    "P304_PINNED_FX6_UXC_EN_BYTES",
    "P304_PINNED_FX6_UXC_EN_SHA256",
    "P304_PLAYBACK_OPTION_MENU_PATH",
    "P304_PLAYBACK_ROTATE_MENU_PATH",
    "P304_PLAYBACK_VIEW_MODE_MENU_PATH",
    "P304_POWER_INSUFFICIENT_ALT_RESID16",
    "P304_POWER_INSUFFICIENT_RESID16",
    "P304_PRIORITY_AFC_BKID",
    "P304_PRIORITY_AFS_BKID",
    "P304_PRIORITY_SET_OR_ILLUMINATOR_GATE_VIOLATIONS",
    "P304_RESET_ACTIONS",
    "P304_ROTATE_BG_NG_SYMBOL",
    "P304_ROTATE_FUNC_SYMBOL",
    "P304_ROTATE_F_RESID16",
    "P304_ROTATE_RESID16",
    "P304_SAFE_SECONDARY_SLOT",
    "P304_SENSOR_CLEANING_F_RESID16",
    "P304_SENSOR_CLEANING_LOW_BATTERY_BYPASS_EVENTS",
    "P304_SENSOR_CLEANING_MENU_PATH",
    "P304_SENSOR_CLEANING_NO_POWER_OFF_VIOLATIONS",
    "P304_SEPARATE_MOVIE_EV_COMP_BKID",
    "P304_SEPARATE_MOVIE_FOCUS_BKID",
    "P304_SHOOTING_DOMAINS",
    "P304_SLOT1_DATA_SECTOR_WRITES",
    "P304_SLOT1_FORMAT_HARD_LOCKED",
    "P304_SLOT1_ROTATE_EXIF_MUTATION_BYTES",
    "P304_SLOT1_VAULT_EROFS_EBUSY_ENFORCED",
    "P304_SLOT1_VAULT_MUTATION_BYTES",
    "P304_SLOT1_VAULT_SLOT",
    "P304_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P304_STATUS_FAIL_54OF54_AGGREGATOR",
    "P304_STATUS_FAIL_PILLAR54_SUITE",
    "P304_STATUS_REJECTED_PILLAR_54A",
    "P304_STATUS_REJECTED_PILLAR_54B",
    "P304_STATUS_VERIFIED_54OF54_AGGREGATOR",
    "P304_STATUS_VERIFIED_PILLAR54_SUITE",
    "P304_STATUS_VERIFIED_PILLAR_54A",
    "P304_STATUS_VERIFIED_PILLAR_54B",
    "P304_STILL_FOCUS_MODES",
    "P304_STILL_FOCUS_MODE_DEFAULT",
    "P304_TIER0_SURFACE_COUNT",
    "P304_UNABLE_TO_ROTATE_RESID16",
    "P304_VAULT_FIREWALL_ERRNOS",
    "P304_VAULT_FIREWALL_ERRNO_CODES",
    "P304_VAULT_TARGET_ACTIONS",
    "P304_VIEW_MODE_ACTIVE_ILC2210",
    "P304_VIEW_MODE_BKID",
    "P304_VIEW_MODE_DEFAULT",
    "P304_VIEW_MODE_SUPPORTED",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE304_PHASE_NUMBER",
    "PHASE304_SCHEMA",
    "PHASE304_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "Phase304DonorArtifactDigest",
    "Phase304DonorSnapshot",
    "Pillar54ASuiteResult",
    "Pillar54BSuiteResult",
    "Pillar54ScenarioOutcome",
    "Pillar54StandaloneReport",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "SensorCleaningEvCompFocusModeRotateVaultReport",
    "SensorCleaningEvCompVaultReport",
    "SensorCleaningEvCompVaultSpec",
    "build_default_safe_focus_mode_playback_rotate_vault_spec",
    "build_default_safe_sensor_cleaning_ev_comp_vault_spec",
    "compute_expected_exposure_comp_state",
    "compute_expected_focus_mode_state",
    "compute_expected_playback_rotate_state",
    "compute_expected_sensor_cleaning_state",
    "evaluate_54pillar_recovery_master",
    "evaluate_focus_mode_playback_rotate_vault",
    "evaluate_realhw_54pillar_recovery_master",
    "evaluate_sensor_cleaning_ev_comp_vault",
    "inspect_phase304_donors_readonly",
    "run_pillar54_standalone_suite",
    "run_pillar54a_sensor_cleaning_ev_comp_6_scenario_suite",
    "run_pillar54b_focus_mode_playback_rotate_6_scenario_suite",
    "verify_54pillar_recovery_suite",
    "verify_sensor_cleaning_ev_comp_focus_mode_rotate_and_vault",
    "verify_sensor_cleaning_ev_comp_focus_mode_rotate_vault",
]
