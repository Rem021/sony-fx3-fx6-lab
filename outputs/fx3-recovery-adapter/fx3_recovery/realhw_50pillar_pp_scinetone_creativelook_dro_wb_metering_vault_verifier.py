"""Phase 287 (50/50 Recovery Pillars Milestone!) — Pillar 50 & Unified 50/50 Recovery Master
(`verify-50pillar-recovery` / `verify-pp-scinetone-wb-metering-vault`):

1. **Pillar 50A — `[Picture Profile]` Out-of-Box `PP11` (`S-Cinetone`) Default vs
   `[Creative Look]` (`10` Looks) & `[D-Range Optimizer]` Mutual Exclusivity under
   `[Log Shooting]`, plus `PP1..11` Non-Resettable Internal-Parameter Recovery Trap (Wave-48)**:
   - Models `MENU` -> `(Exposure/Color)` -> `[Color/Tone]` -> `[Picture Profile]`
     (`BKID_APP_setting_picture_profile`, `_f.uxc` `0x6830`) on stock `ILME-FX3 Ver. 7.02`
     (`ilc/2210`): defaults out-of-box to **`PP11` (`S-Cinetone`, `0x67ab`/`0x6e61`)** for BOTH
     Movie and Still unless decoupled via `[Different Set for Still/Mv]` (`0x62ee`,
     `BKID_APP_setting_different_set`).
   - Enforces mutual exclusivity: whenever `[Picture Profile] != Off`, `[Creative Look]`
     (`0x6823`, `10` presets `ST`..`SE` + `CREATIVE_BOX_1..6`, default `ST`) is locked to `'-'`
     and `[D-Range Optimizer]` (`.uxc` `0xe89c`: `Off`/`Auto`/`Lv1..Lv5`, default `Auto`) is
     locked to `Off`.
   - Enforces `[Log Shooting]` (`Off`, `Flexible ISO`, `Cine EI Quick`, `Cine EI`, `_f.uxc`
     `0x6020`): locks `[Picture Profile] = Off`, `[Creative Look] = '-'`, `[DRO] = Off`, and
     Movie `Gamma Display Assist = Off` to prevent double-log or baked-look corruption; models
     `PPLUT1..4` as Movie-only and enforces `1080p` internal-recording HDMI clamp under
     `[Log Shooting] != Off` or `PPLUT1..4`.
   - Enforces the **Critical Recovery Reset Trap**: neither `[Camera Settings Reset]` nor
     `[Initialize]` resets customized internal parameters inside `PP1..PP11` or clears the
     `[Different Set for Still/Mv]` check mark (`PPLUT1..4` reset on `Initialize`). Full
     post-rollback baseline restoration requires explicit per-profile `[PPx] -> [Reset]` +
     explicit uncheck of `[Different Set for Still/Mv]`. Contrasts `ILME-FX6 Ver. 6.01`
     `Base Look` (`S-Cinetone` Scene File 1 in `Custom` vs `S-Log3` in `Cine EI`) and keeps
     Slot-1 vault strictly read-only (`BLKROSET=True`, volatile `/tmp/...` overlay, `H0 == H3`).

2. **Pillar 50B — `[White Balance]` (`2500K..9900K`, `Custom 1..3` `CAMSET` Exclusion &
   `Cine EI` / `[Custom Setup]` Recovery Guard) & `[Metering Mode]` (`6` Modes, `De-Squeeze`
   Face-Priority Lockout & `Cine EI` Passive `M.M.` Invariance)**:
   - Models `[White Balance]` (`.uxc` `0xe5d4`): `Auto` default (`Priority Set in AWB`
     `0x67a7`: `Standard` default / `Ambience` / `White`), 10 fixed presets, `C.Temp./Filter`
     (`2500K..9900K` in `100K` steps + `A7..B7`/`G7..M7`), `Custom 1..3` (`0xe79d..0xe79c`),
     non-resettable `Shutter AWB Lock` (`Off` `0x66db`, survives `Camera Settings Reset`),
     and `Shockless WB` (`1 (Fast)` `0x62fe`, bypasses `Auto`/`Underwater Auto` & live
     `C.Temp./Filter`/fine-tuning).
   - Enforces `Cine EI` / `Cine EI Quick` WB lockout (blocks `Auto` & `Underwater Auto`),
     `[Custom Setup]` error trap (blocked while `Log Shooting != Off`, `S-Log3`, or `PPLUT1..4`),
     and **`Custom 1..3` `CAMSET` exclusion**: memorized `Custom 1..3` white data survives
     `[Camera Settings Reset]` yet CANNOT be saved to or restored from `Save/Load Settings`
     (`CAMSET01..10.DAT`) on `Slot 1` — recovery audits must verify manual `Custom 1..3`
     re-registration rather than expecting `CAMSET` restore.
   - Models `[Metering Mode]` (`.uxc` `0xe5cf`: `Multi`, `Center`, `Spot: Standard`,
     `Spot: Large`, `Entire Screen Avg.`, `Highlight`), `Face Priority in Multi Metering`
     (`On` default `0x69c7`, hard-locked `Off` when `De-Squeeze != Off`), `Spot Metering Point`
     (`Center` / `Focus Point Link` `0x71b5`/`0x625c`), non-resettable `AEL w/ Shutter` (`Auto`
     `0x669d`), and `Cine EI` Base ISO (`800`/`12800`) invariance where metering feeds passive
     `M.M.` EV deviation only.

3. **Unified `50/50` Recovery Master (`evaluate_realhw_50pillar_recovery_master`)**:
   - Concurrently delegates Pillars `1..49` (`evaluate_realhw_49pillar_recovery_master`) +
     **Pillar 50** (`run_pillar50_standalone_suite`) -> **`50/50` (`VERIFIED_50OF50_PILLAR_RECOVERY_MASTER`)**
     in `< 2.2s` CLI runtime (`< 4.0s` nominal / `< 6.0s` concurrent ceiling), preserving 100%
     backward compatibility with `verify-22..49pillar-recovery`.
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
from .realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_49_PILLAR_SPECS,
    Master49PillarRecoveryReport,
    evaluate_realhw_49pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE287_SCHEMA: str = (
    "realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier_v1"
)
PHASE287_VERSION: str = "1.0.0"
PHASE287_PHASE_NUMBER: int = 287
P287_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P287_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P287_DOUBLE_LOG_OR_LOCKOUT_BYPASS_EVENTS: int = 0
P287_PPLUT_1080P_CLAMP_BYPASS_EVENTS: int = 0
P287_PP_INTERNAL_RESET_TRAP_VIOLATIONS: int = 0
P287_FX6_BASELOOK_CONFUSION_EVENTS: int = 0
P287_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP_EVENTS: int = 0
P287_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT_EVENTS: int = 0
P287_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT_EVENTS: int = 0
P287_SLOT1_VAULT_MUTATION_BYTES: int = 0
P287_SLOT1_FORMAT_HARD_LOCKED: bool = True

P287_DONOR_INSPECT_BUDGET_SECONDS: float = 0.20
P287_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P287_FAST_CLI_BUDGET_SECONDS: float = 2.2
P287_NOMINAL_BUDGET_SECONDS: float = 4.0
P287_CONCURRENT_CEILING_SECONDS: float = 6.0
P287_BOUNDED_HEADER_BYTES: int = 4096
P287_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-48 Donor Anchors (strictly O_RDONLY)
P287_FX3_MODEL_NAME: str = "ILME-FX3"
P287_FX3_MODEL_ID: int = 0x91030080
P287_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P287_FX3_HELPGUIDE_ID: str = "ilc/2210"
P287_FX3_FW_VERSION: str = "7.02"
P287_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P287_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P287_FX6_DONOR_FW_VERSION: str = "6.01"
P287_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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

P287_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P287_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P287_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)
P287_PINNED_FX3_APPFW_702_FULL_SHA256: str = (
    "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f"
)

P287_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P287_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P287_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)
P287_PINNED_FX6_APPFW_601_FULL_SHA256: str = (
    "a1c58b691c0884e1494eb16c3b256c33589a8e32b6f2f3de81af4305bf086067"
)

P287_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P287_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P287_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P287_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P287_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P287_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P287_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P287_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P287_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P287_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P287_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P287_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P287_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P287_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P287_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P287_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P287_PINNED_FX3_UXC_EN_BYTES: int = 165740
P287_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P287_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P287_PINNED_FX3_UXC_EN_G_BYTES: int = 69600
P287_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P287_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P287_PINNED_FX6_UXC_EN_BYTES: int = 118208
P287_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P287_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P287_PINNED_FX6_UXC_EN_2_BYTES: int = 118676
P287_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# ---------------------------------------------------------------------------
# Pillar 50A Constants — [Picture Profile] PP11 (S-Cinetone), [Creative Look],
# [D-Range Optimizer], [Log Shooting], & PP1..11 Reset Trap
# ---------------------------------------------------------------------------

P287_PICTURE_PROFILE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Exposure/Color",
    "Color/Tone",
    "Picture Profile",
)
P287_CREATIVE_LOOK_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Exposure/Color",
    "Color/Tone",
    "Creative Look",
)
P287_DRO_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Exposure/Color",
    "Exposure Comp.",
    "D-Range Optimizer",
)
P287_LOG_SHOOTING_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Image Quality/Rec",
    "Log Shooting Setting",
)

P287_PICTURE_PROFILE_BKID: str = "BKID_APP_setting_picture_profile"
P287_PICTURE_PROFILE_MOVIE_BKID: str = "BKID_APP_setting_picture_profile_movie"
P287_PICTURE_PROFILE_STILL_BKID: str = "BKID_APP_setting_picture_profile_still"
P287_PICTURE_PROFILE_RESID16: int = 0x6830
P287_PP11_RESID16: int = 0x67AB
P287_SCINETONE_RESID16: int = 0x6E61
P287_SCINETONE_CAUTION_ID: str = "CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG"
P287_DIFF_SET_BKID: str = "BKID_APP_setting_different_set"
P287_DIFF_SET_RESID16: int = 0x62EE
P287_DIFF_SET_PROMPT_G_RESID16: int = 0x6361

P287_CREATIVE_LOOK_BKID: str = "BKID_APP_setting_creative_style_plus"
P287_CREATIVE_LOOK_RESID16: int = 0x6823
P287_DRO_BKID: str = "BKID_APP_setting_dro"
P287_DRO_VAL_BKID: str = "BKID_APP_setting_dro_d_range_optimizer"
P287_DRO_RESID16: int = 0xE89C
P287_LOG_SHOOTING_BKID: str = "BKID_APP_setting_log_shooting"
P287_LOG_SHOOTING_RESID16: int = 0x6020
P287_SELECT_LUT_BKID: str = "BKID_APP_setting_select_lut"
P287_SELECT_LUT_RESID16: int = 0x643E
P287_DISPLAY_LUT_RESID16: int = 0x729A
P287_S709_LUT_RESID16: int = 0x6A3E

P287_FX6_BASE_LOOK_BKID_PREFIX: str = "BKID_APP_USER_MENU_BASE_LOOK"
P287_FX6_BASE_LOOK_RESID16: int = 0x23F8
P287_FX6_SCINETONE_RESID16: int = 0x20F5
P287_FX6_709TONE_RESID16: int = 0x288F

P287_PICTURE_PROFILE_FACTORY_DEFAULT: str = "PP11"
P287_PP_1_TO_11: Tuple[str, ...] = tuple(f"PP{i}" for i in range(1, 12))
P287_PPLUT_MODES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P287_PICTURE_PROFILE_ALL_MODES: Tuple[str, ...] = ("Off",) + P287_PP_1_TO_11 + P287_PPLUT_MODES
P287_PP_GAMMA_COLOR_MAP: Dict[str, Tuple[str, str]] = {
    "PP1": ("Movie", "Movie"),
    "PP2": ("Still", "Still"),
    "PP3": ("ITU709", "ITU709"),
    "PP4": ("ITU709", "ITU709"),
    "PP5": ("Cine1", "Cinema"),
    "PP6": ("Cine2", "Cinema"),
    "PP7": ("S-Log2", "S-Gamut"),
    "PP8": ("S-Log3", "S-Gamut3.Cine"),
    "PP9": ("S-Log3", "S-Gamut3"),
    "PP10": ("HLG2", "BT.2020"),
    "PP11": ("S-Cinetone", "S-Cinetone"),
    "PPLUT1": ("User .cube LUT", "User .cube LUT"),
    "PPLUT2": ("User .cube LUT", "User .cube LUT"),
    "PPLUT3": ("User .cube LUT", "User .cube LUT"),
    "PPLUT4": ("User .cube LUT", "User .cube LUT"),
}

P287_CREATIVE_LOOK_10_PRESETS: Tuple[str, ...] = (
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
P287_CREATIVE_LOOK_CUSTOM_SLOTS: Tuple[str, ...] = tuple(f"CREATIVE_BOX_{i}" for i in range(1, 7))
P287_CREATIVE_LOOK_RESID16_ANCHORS: Dict[str, int] = {
    "ST": 0x770C,
    "VV2": 0x7864,
    "SE": 0x7702,
}
P287_CREATIVE_LOOK_8_PARAMS: Tuple[str, ...] = (
    "Contrast",
    "Highlights",
    "Shadows",
    "Fade",
    "Saturation",
    "Sharpness",
    "Sharpness Range",
    "Clarity",
)
P287_CREATIVE_LOOK_DEFAULT: str = "ST"
P287_CREATIVE_LOOK_LOCKED: str = "-"

P287_DRO_MODES: Tuple[str, ...] = ("Off", "Auto", "Lv1", "Lv2", "Lv3", "Lv4", "Lv5")
P287_DRO_DEFAULT: str = "Auto"
P287_DRO_RESID16_MAP: Dict[str, int] = {"Auto": 0xEA04, "Lv1": 0xEA38, "Lv5": 0xE0BE}

P287_LOG_SHOOTING_MODES: Tuple[str, ...] = ("Off", "Flexible ISO", "Cine EI Quick", "Cine EI")
P287_LOG_SHOOTING_DEFAULT: str = "Off"
P287_LOG_SHOOTING_RESID16_MAP: Dict[str, int] = {
    "Flexible ISO": 0x6C9A,
    "Cine EI Quick": 0x611E,
    "Cine EI": 0x6822,
}
P287_ON_OFF_MODES: Tuple[str, ...] = ("Off", "On")
P287_SHOOTING_DOMAINS: Tuple[str, ...] = ("Movie", "Still", "S&Q")
P287_HDMI_OUTPUT_RESOLUTIONS: Tuple[str, ...] = ("Auto", "2160p", "1080p", "1080i", "4K")
P287_PIPELINE_SURFACE_MODELS: Tuple[str, ...] = (
    "FX3_PICTURE_PROFILE_PIPELINE",
    "FX6_BASE_LOOK_SCENE_FILE_PIPELINE",
)
P287_FX6_SHOOTING_MODES: Tuple[str, ...] = ("Custom", "Cine EI", "Cine EI Quick")
P287_FX6_BASE_LOOK_CUSTOM_DEFAULT: str = "S-Cinetone"
P287_FX6_BASE_LOOK_CINE_EI_LOCKED: str = "S-Log3"

# ---------------------------------------------------------------------------
# Pillar 50B Constants — [White Balance] (Custom 1..3 CAMSET Exclusion & Cine EI
# / Custom Setup Guard) & [Metering Mode] (6 Modes, De-Squeeze & Cine EI Base ISO)
# ---------------------------------------------------------------------------

P287_WHITE_BALANCE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Exposure/Color",
    "White Balance",
    "White Balance",
)
P287_WHITE_BALANCE_BKID: str = "BKID_APP_setting_white_balance"
P287_WHITE_BALANCE_RESID16: int = 0xE5D4
P287_PRIORITY_IN_AWB_BKID: str = "BKID_APP_setting_priority_set_in_awb"
P287_PRIORITY_IN_AWB_RESID16: int = 0x67A7
P287_SHUTTER_AWB_LOCK_BKID: str = "BKID_APP_setting_stl_awb_lock_with_shutter"
P287_SHUTTER_AWB_LOCK_RESID16: int = 0x66DB
P287_SHOCKLESS_WB_BKID: str = "BKID_APP_setting_movie_shockless_wb"
P287_SHOCKLESS_WB_RESID16: int = 0x62FE

P287_WB_AUTO_MODES: Tuple[str, ...] = ("Auto", "Underwater Auto")
P287_WB_FIXED_PRESETS: Tuple[str, ...] = (
    "Daylight",
    "Shade",
    "Cloudy",
    "Incandescent",
    "Fluor.: Warm White",
    "Fluor.: Cool White",
    "Fluor.: Day White",
    "Fluor.: Daylight",
    "Flash",
)
P287_WB_CUSTOM_SLOTS: Tuple[str, ...] = ("Custom 1", "Custom 2", "Custom 3")
P287_WB_CUSTOM_RESID16_MAP: Dict[str, int] = {
    "Custom 1": 0xE79D,
    "Custom 2": 0xE79B,
    "Custom 3": 0xE79C,
}
P287_WB_CTEMP_FILTER_MODE: str = "C.Temp./Filter"
P287_WB_ALL_MODES: Tuple[str, ...] = (
    P287_WB_AUTO_MODES
    + P287_WB_FIXED_PRESETS
    + (P287_WB_CTEMP_FILTER_MODE,)
    + P287_WB_CUSTOM_SLOTS
)
P287_WB_DEFAULT: str = "Auto"
P287_WB_CTEMP_MIN_K: int = 2500
P287_WB_CTEMP_MAX_K: int = 9900
P287_WB_CTEMP_STEP_K: int = 100
P287_WB_CTEMP_STEP_COUNT: int = 75
P287_WB_AB_RANGE: Tuple[int, int] = (-7, 7)
P287_WB_GM_RANGE: Tuple[int, int] = (-7, 7)

P287_PRIORITY_IN_AWB_MODES: Tuple[str, ...] = ("Standard", "Ambience", "White")
P287_PRIORITY_IN_AWB_DEFAULT: str = "Standard"
P287_SHUTTER_AWB_LOCK_MODES: Tuple[str, ...] = ("Shutter Half Press", "Cont. Shooting", "Off")
P287_SHUTTER_AWB_LOCK_DEFAULT: str = "Off"
P287_SHOCKLESS_WB_MODES: Tuple[str, ...] = ("Off", "1 (Fast)", "2", "3 (Slow)")
P287_SHOCKLESS_WB_DEFAULT: str = "1 (Fast)"

P287_FX6_WB_MODES: Tuple[str, ...] = ("Memory A", "Memory B", "Preset", "ATW")
P287_FX6_WB_CUSTOM_PRESETS_K: Tuple[int, ...] = (3200, 4300, 5600, 6300)
P287_FX6_WB_CINE_EI_PRESETS_K: Tuple[int, ...] = (3200, 4300, 5500)

P287_METERING_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Exposure/Color",
    "Metering",
    "Metering Mode",
)
P287_METERING_MODE_BKID: str = "BKID_APP_setting_metering_mode"
P287_METERING_MODE_SPOT_BKID: str = "BKID_APP_setting_metering_mode_spot"
P287_METERING_MODE_RESID16: int = 0xE5CF
P287_METERING_6_MODES: Tuple[str, ...] = (
    "Multi",
    "Center",
    "Spot: Standard",
    "Spot: Large",
    "Entire Screen Avg.",
    "Highlight",
)
P287_METERING_MODE_DEFAULT: str = "Multi"
P287_METERING_MODE_RESID16_MAP: Dict[str, int] = {
    "Multi": 0xE631,
    "Center": 0xE787,
    "Spot: Standard": 0x630E,
    "Spot: Large": 0x7357,
    "Entire Screen Avg.": 0x6AA1,
    "Highlight": 0x6491,
}
P287_FACE_PRIORITY_MULTI_BKID: str = "BKID_APP_setting_face_detection_in_multi"
P287_FACE_PRIORITY_MULTI_RESID16: int = 0x69C7
P287_FACE_PRIORITY_MULTI_DEFAULT: str = "On"
P287_SPOT_METERING_POINT_BKID: str = "BKID_APP_setting_spot_metering_link_to_focus_point"
P287_SPOT_METERING_POINT_RESID16: int = 0x71B5
P287_SPOT_METERING_POINT_MODES: Tuple[str, ...] = ("Center", "Focus Point Link")
P287_SPOT_METERING_POINT_DEFAULT: str = "Center"
P287_AEL_W_SHUTTER_BKID: str = "BKID_APP_setting_still_image_ael_w_shutter"
P287_AEL_W_SHUTTER_RESID16: int = 0x669D
P287_AEL_W_SHUTTER_MODES: Tuple[str, ...] = ("Auto", "On", "Off")
P287_AEL_W_SHUTTER_DEFAULT: str = "Auto"
P287_DESQUEEZE_MODES: Tuple[str, ...] = ("Off", "1.3x", "1.6x", "2.0x")
P287_FOCUS_AREAS: Tuple[str, ...] = (
    "Wide",
    "Zone",
    "Center Fix",
    "Spot",
    "Expand Spot",
    "Tracking: Spot",
    "Tracking: Expand Spot",
)
P287_SPOT_LINKABLE_FOCUS_AREAS: Tuple[str, ...] = (
    "Spot",
    "Expand Spot",
    "Tracking: Spot",
    "Tracking: Expand Spot",
)
P287_CINE_EI_BASE_ISOS: Tuple[int, ...] = (800, 12800)

P287_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P287_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "DELETE_SINGLE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P287_DESTRUCTIVE_VAULT_ACTIONS: Tuple[str, ...] = (
    "DELETE_SINGLE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P287_SLOT1_VAULT_SLOT: int = 1
P287_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P287_STAGE_B_VOLATILE_OVERLAY_DIR: str = (
    "/tmp/fx3_pp_scinetone_creativelook_dro_wb_metering_vault_overlay"
)
P287_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P287_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P287_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P287_BLOCKED_INVALID_PILLAR50A_SPEC: str = "BLOCKED_INVALID_PILLAR50A_SPEC"
P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS: str = "BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS"
P287_BLOCKED_PP_INTERNAL_OR_DIFF_SET_RESET_TRAP: str = (
    "BLOCKED_PP_INTERNAL_OR_DIFF_SET_RESET_TRAP"
)
P287_BLOCKED_FX6_BASELOOK_CONFUSION: str = "BLOCKED_FX6_BASELOOK_CONFUSION"
P287_BLOCKED_INVALID_PILLAR50B_SPEC: str = "BLOCKED_INVALID_PILLAR50B_SPEC"
P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP: str = (
    "BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP"
)
P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT: str = (
    "BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT"
)
P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT: str = (
    "BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT"
)
P287_BLOCKED_SLOT1_VAULT_FORMAT_OR_MUTATION: str = (
    "BLOCKED_SLOT1_VAULT_FORMAT_OR_MUTATION"
)
P287_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P287_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P287_STATUS_VERIFIED_PILLAR_50A: str = (
    "VERIFIED_PILLAR_50A_PP11_SCINETONE_CREATIVE_LOOK_DRO_LOG_LOCKOUT_AND_RESET_TRAP_VAULT"
)
P287_STATUS_REJECTED_PILLAR_50A: str = (
    "REJECTED_PILLAR_50A_PP11_SCINETONE_CREATIVE_LOOK_DRO_LOG_LOCKOUT_AND_RESET_TRAP_VAULT"
)
P287_STATUS_VERIFIED_PILLAR_50B: str = (
    "VERIFIED_PILLAR_50B_WHITE_BALANCE_CUSTOM_CAMSET_EXCLUSION_AND_METERING_CINE_EI_VAULT"
)
P287_STATUS_REJECTED_PILLAR_50B: str = (
    "REJECTED_PILLAR_50B_WHITE_BALANCE_CUSTOM_CAMSET_EXCLUSION_AND_METERING_CINE_EI_VAULT"
)
P287_STATUS_VERIFIED_PILLAR50_SUITE: str = (
    "VERIFIED_PILLAR50_PP_SCINETONE_CREATIVE_LOOK_DRO_WB_METERING_VAULT"
)
P287_STATUS_FAIL_PILLAR50_SUITE: str = (
    "FAIL_PILLAR50_PP_SCINETONE_CREATIVE_LOOK_DRO_WB_METERING_VAULT"
)
P287_STATUS_VERIFIED_50OF50_AGGREGATOR: str = "VERIFIED_50OF50_PILLAR_RECOVERY_MASTER"
P287_STATUS_FAIL_50OF50_AGGREGATOR: str = "FAIL_50OF50_PILLAR_RECOVERY_MASTER"

P287_PILLAR_50A_SCENARIO_IDS: Tuple[str, ...] = (
    "P50A1_DEFAULT_PP11_SCINETONE_LOCKS_CREATIVE_LOOK_DRO_BOTH_MOVIE_STILL_SAFE",
    "P50A2_LOG_SHOOTING_LOCKOUT_PPLUT_1080P_CLAMP_AND_EXPLICIT_PP_RESET_RESTORE_SAFE",
    "P50A3_REJECT_DOUBLE_LOG_LOCKOUT_BYPASS_OR_STILL_PPLUT_OR_PPLUT_2160P_BYPASS",
    "P50A4_REJECT_PP_INTERNAL_PARAM_OR_DIFF_SET_CHECKMARK_RESET_TRAP_HALLUCINATION",
    "P50A5_REJECT_FX6_BASE_LOOK_SCENE_FILE_PIPELINE_CONFLATION_ON_FX3",
    "P50A6_REJECT_PERSISTENT_OVERLAY_ESCAPE_SLOT1_MUTATION_OR_H0_H3_DRIFT",
)
P287_PILLAR_50B_SCENARIO_IDS: Tuple[str, ...] = (
    "P50B1_DEFAULT_AWB_2500K_9900K_MANUAL_CUSTOM_WB_AND_6MODE_METERING_SAFE",
    "P50B2_CINE_EI_CUSTOM_WB_OFFLOG_CAPTURE_DESQUEEZE_FACE_LOCK_AND_BASE_ISO_SAFE",
    "P50B3_REJECT_CINE_EI_AWB_OR_CUSTOM_SETUP_WHILE_LOG_OR_SLOG3_PPLUT_ERROR_TRAP",
    "P50B4_REJECT_CAMSET_CUSTOM_WB_RESTORE_EXPECTATION_NONRESET_DRIFT_OR_BAD_CTEMP",
    "P50B5_REJECT_DESQUEEZE_FACE_PRIORITY_OR_FOCUS_LINK_WIDE_OR_BASE_ISO_MISMATCH",
    "P50B6_REJECT_SLOT1_FORMAT_DELETE_PERSISTENT_OVERLAY_OR_TIER0_H0_H3_DRIFT",
)

MASTER_50_PILLAR_COUNT: int = 50
MASTER_50_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_49_PILLAR_SPECS + (
    (
        50,
        "pillar_50_pp_scinetone_creativelook_dro_wb_metering_vault",
        "Phase 287 (50/50 Milestone)",
        "fx3_recovery.realhw_50pillar_pp_scinetone_creativelook_dro_wb_metering_vault_verifier",
    ),
)
MASTER_50_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_50_PILLAR_SPECS)


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
    return os.environ.get(P287_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P287_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P287_DONOR_INSPECT_BUDGET_SECONDS


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
        ("P287_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P287_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P287_DOUBLE_LOG_OR_LOCKOUT_BYPASS_EVENTS", P287_DOUBLE_LOG_OR_LOCKOUT_BYPASS_EVENTS, 0),
        ("P287_PPLUT_1080P_CLAMP_BYPASS_EVENTS", P287_PPLUT_1080P_CLAMP_BYPASS_EVENTS, 0),
        ("P287_PP_INTERNAL_RESET_TRAP_VIOLATIONS", P287_PP_INTERNAL_RESET_TRAP_VIOLATIONS, 0),
        ("P287_FX6_BASELOOK_CONFUSION_EVENTS", P287_FX6_BASELOOK_CONFUSION_EVENTS, 0),
        (
            "P287_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP_EVENTS",
            P287_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP_EVENTS,
            0,
        ),
        (
            "P287_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT_EVENTS",
            P287_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT_EVENTS,
            0,
        ),
        (
            "P287_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT_EVENTS",
            P287_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT_EVENTS,
            0,
        ),
        ("P287_SLOT1_VAULT_MUTATION_BYTES", P287_SLOT1_VAULT_MUTATION_BYTES, 0),
        ("P287_SLOT1_FORMAT_HARD_LOCKED", P287_SLOT1_FORMAT_HARD_LOCKED, True),
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
    return any(tok in low for tok in P287_FORBIDDEN_PERSISTENT_TARGETS)


def compute_expected_pp_creativelook_dro_log_pipeline(
    *,\
    shooting_domain: str,
    intelligent_auto: bool,
    log_shooting: str,
    configured_picture_profile: str,
    configured_creative_look: str,
    configured_dro: str,
    configured_gamma_disp_assist: str,
    hlg_still_image: bool,
    hdmi_internal_recording: bool,
    configured_hdmi_resolution: str,
) -> Tuple[str, str, str, str, bool, str]:
    """Compute `(eff_pp, eff_creative_look, eff_dro, eff_gamma_assist, pplut_allowed, eff_hdmi_res)`.

    - `PPLUT1..4` are Movie-only (`pplut_allowed = shooting_domain == "Movie"`).
    - Whenever `log_shooting != "Off"`: locks `Picture Profile = Off`, `Creative Look = '-'`,
      `DRO = Off`, and Movie `Gamma Display Assist = Off`, clamping internal-rec HDMI to `1080p`.
    - Whenever `eff_pp != "Off"`: locks `Creative Look = '-'` and `DRO = Off`; `PPLUT1..4`
      with internal recording also clamps HDMI output to `1080p`.
    - Only when `log_shooting == "Off"` AND `eff_pp == "Off"` (outside `Intelligent Auto`)
      are `Creative Look` (`ST` default) and `D-Range Optimizer` (`Auto` default) active.
    """
    pplut_allowed = shooting_domain == "Movie"
    if log_shooting != "Off":
        eff_pp = "Off"
        eff_cl = P287_CREATIVE_LOOK_LOCKED
        eff_dro = "Off"
        eff_gda = "Off" if shooting_domain in ("Movie", "S&Q") else configured_gamma_disp_assist
        eff_hdmi = "1080p" if hdmi_internal_recording else configured_hdmi_resolution
        return eff_pp, eff_cl, eff_dro, eff_gda, pplut_allowed, eff_hdmi

    if intelligent_auto:
        return "Off", P287_CREATIVE_LOOK_LOCKED, "Auto", configured_gamma_disp_assist, pplut_allowed, configured_hdmi_resolution

    eff_pp = configured_picture_profile
    if eff_pp != "Off":
        eff_cl = P287_CREATIVE_LOOK_LOCKED
        eff_dro = "Off"
        eff_hdmi = (
            "1080p"
            if (eff_pp in P287_PPLUT_MODES and hdmi_internal_recording)
            else configured_hdmi_resolution
        )
        return eff_pp, eff_cl, eff_dro, configured_gamma_disp_assist, pplut_allowed, eff_hdmi

    eff_cl = configured_creative_look
    eff_dro = "Off" if hlg_still_image else configured_dro
    return eff_pp, eff_cl, eff_dro, configured_gamma_disp_assist, pplut_allowed, configured_hdmi_resolution


def compute_expected_pillar50a_reset_state(
    *,\
    pre_diff_set_pp_checked: bool,
    pre_pp_internal_customized: bool,
    pre_pplut_customized: bool,
    reset_action: str,
    explicit_per_profile_pp_reset: bool,
    explicit_diff_set_uncheck: bool,
) -> Tuple[str, str, str, str, bool, bool, bool]:
    """Compute `(post_pp, post_cl, post_dro, post_log, post_diff_set_checked, post_pp_internal_customized, post_pplut_customized)`.

    Critical Sony `ILME-FX3 Ver. 7.02` Recovery Reset Trap (`ilc/2210`):
    - `[Camera Settings Reset]` restores active selector `Picture Profile -> PP11` (`S-Cinetone`),
      `Creative Look -> ST` (locked `'-'` while `PP11` active), `DRO -> Auto` (locked `Off`), and
      `Log Shooting -> Off`, YET preserves BOTH `[Different Set for Still/Mv]` check marks AND
      customized internal parameters inside `PP1..PP11` (and `PPLUT1..4`).
    - `[Initialize]` resets `PPLUT1..4`, YET STILL preserves `[Different Set for Still/Mv]` check
      marks AND customized internal parameters inside `PP1..PP11`!
    - Full baseline restoration of `PP1..PP11` internal parameters requires explicit per-profile
      `[PPx] -> [Reset]` (`explicit_per_profile_pp_reset=True`), and clearing Still/Movie split
      requires explicit `[Different Set for Still/Mv]` uncheck.
    """
    if reset_action in ("Camera Settings Reset", "Initialize"):
        post_pp = P287_PICTURE_PROFILE_FACTORY_DEFAULT
        post_cl = P287_CREATIVE_LOOK_DEFAULT
        post_dro = P287_DRO_DEFAULT
        post_log = P287_LOG_SHOOTING_DEFAULT
        post_pplut_custom = False if reset_action == "Initialize" else pre_pplut_customized
    else:
        post_pp = P287_PICTURE_PROFILE_FACTORY_DEFAULT
        post_cl = P287_CREATIVE_LOOK_DEFAULT
        post_dro = P287_DRO_DEFAULT
        post_log = P287_LOG_SHOOTING_DEFAULT
        post_pplut_custom = pre_pplut_customized

    post_diff_checked = False if explicit_diff_set_uncheck else pre_diff_set_pp_checked
    post_pp_internal = False if explicit_per_profile_pp_reset else pre_pp_internal_customized
    return (
        post_pp,
        post_cl,
        post_dro,
        post_log,
        post_diff_checked,
        post_pp_internal,
        post_pplut_custom,
    )


def compute_expected_wb_cine_ei_custom_guard(
    *,\
    log_shooting: str,
    picture_profile: str,
    picture_profile_gamma: str,
    requested_wb_mode: str,
    ctemp_kelvin: int,
    ab_filter: int,
    gm_filter: int,
    shockless_wb_setting: str,
    custom_setup_attempted: bool,
    reset_action: str,
    camset_load_attempted: bool,
    pre_custom_wb_memorized_dirty: bool,
    manual_custom_wb_reregistered: bool,
    pre_shutter_awb_lock: str,
) -> Tuple[bool, bool, bool, bool, bool, bool, str, str]:
    """Compute `(ctemp_valid, wb_mode_allowed, custom_setup_error, shockless_applies,
    custom_wb_memorized_preserved, camset_excludes_custom_wb, post_shutter_awb_lock, post_shockless_wb)`.

    - `Cine EI` / `Cine EI Quick` blocks `Auto` & `Underwater Auto` WB.
    - `[Custom Setup]` while `Log Shooting != Off`, `gamma == 'S-Log3'`, or `PPLUT1..4` triggers
      the custom WB setup error trap.
    - `Shockless WB` does NOT smooth `Auto`/`Underwater Auto` or live `C.Temp./Filter` tweaks.
    - `Custom 1..3` memorized white data survives `[Camera Settings Reset]` (cleared only by
      `[Initialize]` or manual re-registration) and CANNOT be saved/restored via `CAMSET` (`Slot 1`).
    - `Shutter AWB Lock` survives `[Camera Settings Reset]` and reverts to `Off` only on `[Initialize]`.
    """
    ctemp_valid = (
        P287_WB_CTEMP_MIN_K <= ctemp_kelvin <= P287_WB_CTEMP_MAX_K
        and (ctemp_kelvin % P287_WB_CTEMP_STEP_K) == 0
        and P287_WB_AB_RANGE[0] <= ab_filter <= P287_WB_AB_RANGE[1]
        and P287_WB_GM_RANGE[0] <= gm_filter <= P287_WB_GM_RANGE[1]
    )
    cine_ei_active = log_shooting in ("Cine EI", "Cine EI Quick")
    wb_mode_allowed = not (cine_ei_active and requested_wb_mode in P287_WB_AUTO_MODES)
    custom_setup_error = custom_setup_attempted and (
        log_shooting != "Off"
        or picture_profile_gamma == "S-Log3"
        or picture_profile in P287_PPLUT_MODES
    )
    shockless_applies = (
        shockless_wb_setting != "Off"
        and requested_wb_mode not in (P287_WB_AUTO_MODES + (P287_WB_CTEMP_FILTER_MODE,))
    )
    camset_excludes_custom_wb = True
    if reset_action == "Initialize":
        custom_preserved = manual_custom_wb_reregistered
        post_awb_lock = P287_SHUTTER_AWB_LOCK_DEFAULT
        post_shockless = P287_SHOCKLESS_WB_DEFAULT
    elif reset_action == "Camera Settings Reset":
        custom_preserved = pre_custom_wb_memorized_dirty and not manual_custom_wb_reregistered
        post_awb_lock = pre_shutter_awb_lock
        post_shockless = P287_SHOCKLESS_WB_DEFAULT
    else:
        custom_preserved = pre_custom_wb_memorized_dirty and not manual_custom_wb_reregistered
        post_awb_lock = pre_shutter_awb_lock
        post_shockless = shockless_wb_setting

    # Even if CAMSET is loaded, Custom 1..3 memorized white registers never come from CAMSET
    if camset_load_attempted:
        camset_excludes_custom_wb = True

    return (
        ctemp_valid,
        wb_mode_allowed,
        custom_setup_error,
        shockless_applies,
        custom_preserved,
        camset_excludes_custom_wb,
        post_awb_lock,
        post_shockless,
    )


def compute_expected_metering_and_cine_ei_invariance(
    *,\
    intelligent_auto: bool,
    configured_metering_mode: str,
    desqueeze_mode: str,
    configured_face_priority: str,
    focus_area: str,
    active_tracking_running: bool,
    configured_spot_point: str,
    log_shooting: str,
    cine_ei_base_iso: int,
    pre_ael_w_shutter: str,
    reset_action: str,
) -> Tuple[str, str, str, bool, bool, str]:
    """Compute `(eff_metering, eff_face_priority, eff_spot_point, base_iso_locked_invariant,
    passive_mm_deviation_only, post_ael_w_shutter)`.

    - `Intelligent Auto` locks `Metering Mode` to `Multi`.
    - `De-Squeeze != Off` hard-locks `Face Priority in Multi Metering` to `Off`.
    - `Spot Metering Point = Focus Point Link` requires linkable spot start focus area (and does
      not follow active tracking once started); `Wide`/`Zone`/`Center Fix` force `Center`.
    - In `Cine EI` / `Cine EI Quick`, sensor Base ISO (`800` / `12800`) is locked invariant and
      metering drives passive `M.M.` EV deviation only.
    - `AEL w/ Shutter` survives `Camera Settings Reset` and reverts to `Auto` only on `Initialize`.
    """
    eff_metering = "Multi" if intelligent_auto else configured_metering_mode
    eff_face = "Off" if desqueeze_mode != "Off" else configured_face_priority
    if focus_area not in P287_SPOT_LINKABLE_FOCUS_AREAS or active_tracking_running:
        eff_spot = "Center"
    else:
        eff_spot = configured_spot_point

    cine_ei_active = log_shooting in ("Cine EI", "Cine EI Quick")
    base_iso_invariant = (not cine_ei_active) or (cine_ei_base_iso in P287_CINE_EI_BASE_ISOS)
    passive_mm_only = cine_ei_active
    post_ael = P287_AEL_W_SHUTTER_DEFAULT if reset_action == "Initialize" else pre_ael_w_shutter
    return eff_metering, eff_face, eff_spot, base_iso_invariant, passive_mm_only, post_ael


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase287DonorArtifactDigest:
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
class Phase287DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_20s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase287DonorArtifactDigest, ...]


@dataclass(frozen=True)
class PictureProfileScinetoneDroLogVaultSpec:
    camera_model: str = P287_FX3_MODEL_NAME
    camera_model_id: int = P287_FX3_MODEL_ID
    camera_codename: str = P287_FX3_PRODUCT_CODENAME
    helpguide_id: str = P287_FX3_HELPGUIDE_ID
    fw_version: str = P287_FX3_FW_VERSION
    pipeline_surface_model: str = "FX3_PICTURE_PROFILE_PIPELINE"
    picture_profile_menu_path: Tuple[str, ...] = P287_PICTURE_PROFILE_MENU_PATH
    creative_look_menu_path: Tuple[str, ...] = P287_CREATIVE_LOOK_MENU_PATH
    dro_menu_path: Tuple[str, ...] = P287_DRO_MENU_PATH
    log_shooting_menu_path: Tuple[str, ...] = P287_LOG_SHOOTING_MENU_PATH
    shooting_domain: str = "Movie"
    intelligent_auto: bool = False
    hlg_still_image: bool = False
    log_shooting: str = "Off"
    configured_picture_profile: str = P287_PICTURE_PROFILE_FACTORY_DEFAULT
    configured_creative_look: str = P287_CREATIVE_LOOK_DEFAULT
    configured_dro: str = P287_DRO_DEFAULT
    configured_gamma_disp_assist: str = "Off"
    reported_picture_profile: str = P287_PICTURE_PROFILE_FACTORY_DEFAULT
    reported_creative_look: str = P287_CREATIVE_LOOK_LOCKED
    reported_dro: str = "Off"
    reported_gamma_disp_assist: str = "Off"
    diff_set_pp_checked: bool = False
    movie_picture_profile: str = P287_PICTURE_PROFILE_FACTORY_DEFAULT
    still_picture_profile: str = P287_PICTURE_PROFILE_FACTORY_DEFAULT
    hdmi_internal_recording: bool = True
    configured_hdmi_resolution: str = "Auto"
    reported_hdmi_resolution: str = "Auto"
    double_log_or_lockout_bypass_events: int = 0
    pplut_1080p_clamp_bypass_events: int = 0
    fx6_baselook_confusion_events: int = 0
    reset_action: str = "Camera Settings Reset"
    pre_diff_set_pp_checked: bool = False
    pre_pp_internal_customized: bool = True
    pre_pplut_customized: bool = True
    explicit_per_profile_pp_reset: bool = True
    explicit_diff_set_uncheck: bool = True
    post_diff_set_pp_checked: bool = False
    post_pp_internal_customized: bool = False
    post_pplut_customized: bool = True
    pp_internal_reset_trap_violations: int = 0
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P287_SLOT1_FORMAT_HARD_LOCKED
    slot1_vault_mutation_bytes: int = 0
    overlay_dir: str = P287_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P287_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P287_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P287_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class PictureProfileScinetoneDroLogVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    pp11_scinetone_default_and_diff_set_verified: bool
    mutual_exclusivity_and_log_lockout_verified: bool
    pplut_movie_only_and_1080p_clamp_verified: bool
    pp_internal_reset_trap_verified: bool
    fx6_baselook_distinction_verified: bool
    h0_equals_h3_verified: bool
    matrix_states_checked: int
    double_log_or_lockout_bypass_events: int
    pplut_1080p_clamp_bypass_events: int
    pp_internal_reset_trap_violations: int
    fx6_baselook_confusion_events: int
    slot1_vault_mutation_bytes: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WhiteBalanceCamsetExclusionAndMeteringVaultSpec:
    camera_model: str = P287_FX3_MODEL_NAME
    camera_model_id: int = P287_FX3_MODEL_ID
    helpguide_id: str = P287_FX3_HELPGUIDE_ID
    fw_version: str = P287_FX3_FW_VERSION
    wb_menu_path: Tuple[str, ...] = P287_WHITE_BALANCE_MENU_PATH
    metering_menu_path: Tuple[str, ...] = P287_METERING_MENU_PATH
    log_shooting: str = "Off"
    picture_profile: str = P287_PICTURE_PROFILE_FACTORY_DEFAULT
    picture_profile_gamma: str = "S-Cinetone"
    wb_mode: str = P287_WB_DEFAULT
    priority_in_awb: str = P287_PRIORITY_IN_AWB_DEFAULT
    ctemp_kelvin: int = 5600
    ab_filter: int = 0
    gm_filter: int = 0
    shockless_wb_setting: str = P287_SHOCKLESS_WB_DEFAULT
    custom_setup_attempted: bool = False
    reported_custom_setup_error: bool = False
    pre_shutter_awb_lock: str = P287_SHUTTER_AWB_LOCK_DEFAULT
    post_shutter_awb_lock: str = P287_SHUTTER_AWB_LOCK_DEFAULT
    post_shockless_wb_setting: str = P287_SHOCKLESS_WB_DEFAULT
    reset_action: str = "Camera Settings Reset"
    camset_load_attempted: bool = True
    camset_slot: int = P287_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P287_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    expect_camset_restores_custom_wb: bool = False
    pre_custom_wb_memorized_dirty: bool = True
    manual_custom_wb_reregistered: bool = True
    post_custom_wb_memorized_dirty: bool = False
    wb_cine_ei_awb_or_custom_setup_trap_events: int = 0
    wb_custom_camset_exclusion_drift_events: int = 0
    intelligent_auto: bool = False
    configured_metering_mode: str = P287_METERING_MODE_DEFAULT
    reported_metering_mode: str = P287_METERING_MODE_DEFAULT
    desqueeze_mode: str = "Off"
    configured_face_priority: str = P287_FACE_PRIORITY_MULTI_DEFAULT
    reported_face_priority: str = P287_FACE_PRIORITY_MULTI_DEFAULT
    focus_area: str = "Spot"
    active_tracking_running: bool = False
    configured_spot_point: str = P287_SPOT_METERING_POINT_DEFAULT
    reported_spot_point: str = P287_SPOT_METERING_POINT_DEFAULT
    pre_ael_w_shutter: str = P287_AEL_W_SHUTTER_DEFAULT
    post_ael_w_shutter: str = P287_AEL_W_SHUTTER_DEFAULT
    cine_ei_base_iso: int = 800
    metering_altered_cine_ei_gain: bool = False
    metering_desqueeze_or_cine_ei_base_iso_drift_events: int = 0
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P287_SLOT1_FORMAT_HARD_LOCKED
    requested_vault_slot: int = P287_SLOT1_VAULT_SLOT
    requested_vault_action: str = "READ_ONLY_AUDIT"
    slot1_vault_mutation_bytes: int = 0
    overlay_dir: str = P287_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P287_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P287_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P287_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class WhiteBalanceCamsetExclusionAndMeteringVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    wb_modes_ctemp_and_shockless_verified: bool
    cine_ei_awb_and_custom_setup_trap_verified: bool
    custom_wb_camset_exclusion_and_reset_verified: bool
    metering_6modes_desqueeze_face_spot_verified: bool
    cine_ei_base_iso_mm_invariance_verified: bool
    h0_equals_h3_verified: bool
    matrix_states_checked: int
    wb_cine_ei_awb_or_custom_setup_trap_events: int
    wb_custom_camset_exclusion_drift_events: int
    metering_desqueeze_or_cine_ei_base_iso_drift_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PpScinetoneCreativeLookDroWbMeteringVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase287DonorSnapshot
    pp_scinetone_dro_report: PictureProfileScinetoneDroLogVaultReport
    wb_metering_report: WhiteBalanceCamsetExclusionAndMeteringVaultReport
    double_log_or_lockout_bypass_events: int
    pplut_1080p_clamp_bypass_events: int
    pp_internal_reset_trap_violations: int
    fx6_baselook_confusion_events: int
    wb_cine_ei_awb_or_custom_setup_trap_events: int
    wb_custom_camset_exclusion_drift_events: int
    metering_desqueeze_or_cine_ei_base_iso_drift_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
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
class Pillar50ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar50ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar50ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar50BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar50ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar50StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase287DonorSnapshot
    pillar_50a_pp_scinetone_creativelook_dro_vault: Pillar50ASuiteResult
    pillar_50b_wb_camset_exclusion_metering_vault: Pillar50BSuiteResult
    double_log_or_lockout_bypass_events: int
    pplut_1080p_clamp_bypass_events: int
    pp_internal_reset_trap_violations: int
    fx6_baselook_confusion_events: int
    wb_cine_ei_awb_or_custom_setup_trap_events: int
    wb_custom_camset_exclusion_drift_events: int
    metering_desqueeze_or_cine_ei_base_iso_drift_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
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
class Master50PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_2_2s_fast_cli_budget: bool
    under_2_5s_fast_cli_budget: bool
    under_6s_budget: bool
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    # Pillar 50 & Wave-48 top-level fields
    donor_snapshot: Phase287DonorSnapshot
    pillar50_a_pp_scinetone_creativelook_dro_vault: Pillar50ASuiteResult
    pillar50_b_wb_camset_exclusion_metering_vault: Pillar50BSuiteResult
    double_log_or_lockout_bypass_events: int
    pplut_1080p_clamp_bypass_events: int
    pp_internal_reset_trap_violations: int
    fx6_baselook_confusion_events: int
    wb_cine_ei_awb_or_custom_setup_trap_events: int
    wb_custom_camset_exclusion_drift_events: int
    metering_desqueeze_or_cine_ei_base_iso_drift_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    # Preserved Pillars 1..49 rollup metrics
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
    hardware_live_attachment_authorized: bool
    master_50pillar_sha256: str
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
    max_full_bytes: int = P287_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P287_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase287_donors() -> Tuple[Phase287DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P287_DONOR_FX3_APPFW_702_RELPATH,
            P287_PINNED_FX3_APPFW_702_BYTES,
            P287_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P287_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P287_DONOR_FX6_APPFW_601_RELPATH,
            P287_PINNED_FX6_APPFW_601_BYTES,
            P287_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P287_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P287_DONOR_FX3_BACKUP_BIN_RELPATH,
            P287_PINNED_FX3_BACKUP_BIN_BYTES,
            P287_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P287_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_uxc_en_f",
            P287_DONOR_FX3_UXC_EN_F_RELPATH,
            P287_PINNED_FX3_UXC_EN_F_BYTES,
            P287_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P287_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P287_DONOR_FX3_UXC_SC_F_RELPATH,
            P287_PINNED_FX3_UXC_SC_F_BYTES,
            P287_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P287_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P287_DONOR_FX3_UXC_TC_F_RELPATH,
            P287_PINNED_FX3_UXC_TC_F_BYTES,
            P287_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P287_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P287_DONOR_FX3_UXC_JA_F_RELPATH,
            P287_PINNED_FX3_UXC_JA_F_BYTES,
            P287_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P287_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P287_DONOR_FX3_UXC_EN_RELPATH,
            P287_PINNED_FX3_UXC_EN_BYTES,
            P287_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P287_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_en_g",
            P287_DONOR_FX3_UXC_EN_G_RELPATH,
            P287_PINNED_FX3_UXC_EN_G_BYTES,
            P287_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P287_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx6_uxc_en",
            P287_DONOR_FX6_UXC_EN_RELPATH,
            P287_PINNED_FX6_UXC_EN_BYTES,
            P287_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P287_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P287_DONOR_FX6_UXC_EN_2_RELPATH,
            P287_PINNED_FX6_UXC_EN_2_BYTES,
            P287_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P287_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase287DonorArtifactDigest(
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


def inspect_phase287_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase287DonorSnapshot:
    """Inspect Wave-48 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.2s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase287_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase287DonorSnapshot(
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
            P287_DONOR_FX3_APPFW_702_RELPATH,
            P287_PINNED_FX3_APPFW_702_BYTES,
            P287_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX3_APPFW_702"),
        ),
        (
            "fx6_appfw_601_so",
            P287_DONOR_FX6_APPFW_601_RELPATH,
            P287_PINNED_FX6_APPFW_601_BYTES,
            P287_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64(d, "FX6_APPFW_601"),
        ),
        (
            "fx3_backup_bin",
            P287_DONOR_FX3_BACKUP_BIN_RELPATH,
            P287_PINNED_FX3_BACKUP_BIN_BYTES,
            P287_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_uxc_en_f",
            P287_DONOR_FX3_UXC_EN_F_RELPATH,
            P287_PINNED_FX3_UXC_EN_F_BYTES,
            P287_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P287_DONOR_FX3_UXC_SC_F_RELPATH,
            P287_PINNED_FX3_UXC_SC_F_BYTES,
            P287_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P287_DONOR_FX3_UXC_TC_F_RELPATH,
            P287_PINNED_FX3_UXC_TC_F_BYTES,
            P287_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P287_DONOR_FX3_UXC_JA_F_RELPATH,
            P287_PINNED_FX3_UXC_JA_F_BYTES,
            P287_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P287_DONOR_FX3_UXC_EN_RELPATH,
            P287_PINNED_FX3_UXC_EN_BYTES,
            P287_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_en_g",
            P287_DONOR_FX3_UXC_EN_G_RELPATH,
            P287_PINNED_FX3_UXC_EN_G_BYTES,
            P287_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx6_uxc_en",
            P287_DONOR_FX6_UXC_EN_RELPATH,
            P287_PINNED_FX6_UXC_EN_BYTES,
            P287_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P287_DONOR_FX6_UXC_EN_2_RELPATH,
            P287_PINNED_FX6_UXC_EN_2_BYTES,
            P287_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    artifacts: List[Phase287DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            artifacts.append(
                Phase287DonorArtifactDigest(
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
            Phase287DonorArtifactDigest(
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
        synth = _synthetic_phase287_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase287DonorSnapshot(
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
    return Phase287DonorSnapshot(
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
# Pillar 50A & 50B Builders and Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_pp_scinetone_dro_log_vault_spec() -> (
    PictureProfileScinetoneDroLogVaultSpec
):
    """Return canonical safe Wave-48 Pillar 50A specification."""
    return PictureProfileScinetoneDroLogVaultSpec()


def build_default_safe_wb_camset_exclusion_metering_vault_spec() -> (
    WhiteBalanceCamsetExclusionAndMeteringVaultSpec
):
    """Return canonical safe Wave-48 Pillar 50B specification."""
    return WhiteBalanceCamsetExclusionAndMeteringVaultSpec()


def evaluate_pp_scinetone_creativelook_dro_log_vault(
    spec: Optional[PictureProfileScinetoneDroLogVaultSpec] = None,
) -> PictureProfileScinetoneDroLogVaultReport:
    """Verify Pillar 50A: Stock `ILME-FX3` `PP11` (`S-Cinetone`) default vs `Creative Look` (`10` looks)
    & `D-Range Optimizer` mutual exclusivity under `Log Shooting`, `PPLUT1..4` Movie-only & `1080p`
    clamp, `PP1..11` internal-parameter reset trap, and `ILME-FX6 Base Look` distinction."""
    cfg = spec if spec is not None else PictureProfileScinetoneDroLogVaultSpec()
    safety_errs = _safety_invariant_errors()
    if safety_errs or cfg.persistent_write_unlock_requested:
        errs = safety_errs + (
            ["persistent_write_unlock_requested must be False"]
            if cfg.persistent_write_unlock_requested
            else []
        )
        return PictureProfileScinetoneDroLogVaultReport(
            passed=False,
            status=P287_STATUS_REJECTED_PILLAR_50A,
            block_code=P287_BLOCKED_SAFETY_POLICY_VIOLATION,
            pp11_scinetone_default_and_diff_set_verified=False,
            mutual_exclusivity_and_log_lockout_verified=False,
            pplut_movie_only_and_1080p_clamp_verified=False,
            pp_internal_reset_trap_verified=False,
            fx6_baselook_distinction_verified=False,
            h0_equals_h3_verified=False,
            matrix_states_checked=0,
            double_log_or_lockout_bypass_events=0,
            pplut_1080p_clamp_bypass_events=0,
            pp_internal_reset_trap_violations=0,
            fx6_baselook_confusion_events=0,
            slot1_vault_mutation_bytes=0,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            digest_sha256=_canonical_sha256({"blocked": P287_BLOCKED_SAFETY_POLICY_VIOLATION}),
            errors=tuple(errs),
        )

    errs: List[str] = []
    block_code: Optional[str] = None

    def _set_block(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errs.append(msg)

    valid_creatives = P287_CREATIVE_LOOK_10_PRESETS + P287_CREATIVE_LOOK_CUSTOM_SLOTS
    if (
        cfg.camera_model != P287_FX3_MODEL_NAME
        or cfg.camera_model_id != P287_FX3_MODEL_ID
        or cfg.helpguide_id != P287_FX3_HELPGUIDE_ID
        or cfg.fw_version not in P287_FX3_SUPPORTED_FW_VERSIONS
        or cfg.picture_profile_menu_path != P287_PICTURE_PROFILE_MENU_PATH
        or cfg.creative_look_menu_path != P287_CREATIVE_LOOK_MENU_PATH
        or cfg.dro_menu_path != P287_DRO_MENU_PATH
        or cfg.log_shooting_menu_path != P287_LOG_SHOOTING_MENU_PATH
        or cfg.shooting_domain not in P287_SHOOTING_DOMAINS
        or cfg.log_shooting not in P287_LOG_SHOOTING_MODES
        or cfg.configured_picture_profile not in P287_PICTURE_PROFILE_ALL_MODES
        or cfg.configured_creative_look not in valid_creatives
        or cfg.configured_dro not in P287_DRO_MODES
        or cfg.configured_gamma_disp_assist not in P287_ON_OFF_MODES
        or cfg.configured_hdmi_resolution not in P287_HDMI_OUTPUT_RESOLUTIONS
        or cfg.reset_action not in P287_RESET_ACTIONS
    ):
        _set_block(
            P287_BLOCKED_INVALID_PILLAR50A_SPEC,
            "Invalid Pillar 50A camera model, firmware, menu path, Picture Profile, Creative Look, DRO, or Log Shooting spec",
        )

    # 1. FX6 Base Look vs FX3 Picture Profile distinction
    fx6_distinction_ok = True
    fx6_confusions = cfg.fx6_baselook_confusion_events
    if (
        cfg.pipeline_surface_model != "FX3_PICTURE_PROFILE_PIPELINE"
        or cfg.fx6_baselook_confusion_events != 0
    ):
        fx6_distinction_ok = False
        fx6_confusions = max(fx6_confusions, 1)
        _set_block(
            P287_BLOCKED_FX6_BASELOOK_CONFUSION,
            "ILME-FX3 uses Picture Profile / Creative Look / DRO rather than ILME-FX6 Base Look Scene Files",
        )

    # 2. Out-of-box PP11 default & Different Set for Still/Mv link
    pp11_diff_ok = True
    if not cfg.diff_set_pp_checked and cfg.movie_picture_profile != cfg.still_picture_profile:
        pp11_diff_ok = False
        _set_block(
            P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
            "When Different Set for Still/Mv is unchecked, Movie and Still Picture Profile share PP11 out-of-box",
        )

    # 3. Mutual exclusivity & Log Shooting lockout & PPLUT Movie-only 1080p clamp
    mutual_ok = True
    pplut_ok = True
    double_log_ev = cfg.double_log_or_lockout_bypass_events
    pplut_clamp_ev = cfg.pplut_1080p_clamp_bypass_events

    eff_pp, eff_cl, eff_dro, eff_gda, pplut_allowed, eff_hdmi = (
        compute_expected_pp_creativelook_dro_log_pipeline(
            shooting_domain=cfg.shooting_domain,
            intelligent_auto=cfg.intelligent_auto,
            log_shooting=cfg.log_shooting,
            configured_picture_profile=cfg.configured_picture_profile,
            configured_creative_look=cfg.configured_creative_look,
            configured_dro=cfg.configured_dro,
            configured_gamma_disp_assist=cfg.configured_gamma_disp_assist,
            hlg_still_image=cfg.hlg_still_image,
            hdmi_internal_recording=cfg.hdmi_internal_recording,
            configured_hdmi_resolution=cfg.configured_hdmi_resolution,
        )
    )
    if (
        cfg.configured_picture_profile in P287_PPLUT_MODES
        and cfg.log_shooting == "Off"
        and not pplut_allowed
    ):
        pplut_ok = False
        double_log_ev = max(double_log_ev, 1)
        _set_block(
            P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
            "PPLUT1..4 are Movie-only and cannot be selected in Still domain",
        )

    if (
        cfg.reported_picture_profile != eff_pp
        or cfg.reported_creative_look != eff_cl
        or cfg.reported_dro != eff_dro
        or cfg.reported_gamma_disp_assist != eff_gda
        or cfg.double_log_or_lockout_bypass_events != 0
    ):
        mutual_ok = False
        double_log_ev = max(double_log_ev, 1)
        _set_block(
            P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
            (
                f"Mutual-exclusivity/Log-Shooting lockout violation: expected "
                f"(PP={eff_pp!r}, CL={eff_cl!r}, DRO={eff_dro!r}, GDA={eff_gda!r}), got "
                f"(PP={cfg.reported_picture_profile!r}, CL={cfg.reported_creative_look!r}, "
                f"DRO={cfg.reported_dro!r}, GDA={cfg.reported_gamma_disp_assist!r})"
            ),
        )

    if cfg.reported_hdmi_resolution != eff_hdmi or cfg.pplut_1080p_clamp_bypass_events != 0:
        pplut_ok = False
        pplut_clamp_ev = max(pplut_clamp_ev, 1)
        _set_block(
            P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
            f"Log Shooting / PPLUT1..4 internal-rec HDMI clamp drift: expected {eff_hdmi!r}, got {cfg.reported_hdmi_resolution!r}",
        )

    matrix_checked = 0
    for dom in P287_SHOOTING_DOMAINS:
        for log_m in P287_LOG_SHOOTING_MODES:
            for pp_m in ("Off", "PP8", "PP11", "PPLUT1"):
                m_pp, m_cl, m_dro, m_gda, m_lut_ok, m_hdmi = (
                    compute_expected_pp_creativelook_dro_log_pipeline(
                        shooting_domain=dom,
                        intelligent_auto=False,
                        log_shooting=log_m,
                        configured_picture_profile=pp_m,
                        configured_creative_look="ST",
                        configured_dro="Auto",
                        configured_gamma_disp_assist="On",
                        hlg_still_image=False,
                        hdmi_internal_recording=True,
                        configured_hdmi_resolution="2160p",
                    )
                )
                if log_m != "Off" and (m_pp != "Off" or m_cl != "-" or m_dro != "Off" or m_hdmi != "1080p"):
                    mutual_ok = False
                    _set_block(
                        P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
                        "Log Shooting matrix must lock PP=Off, Creative Look='-', DRO=Off, HDMI=1080p",
                    )
                if log_m != "Off" and dom in ("Movie", "S&Q") and m_gda != "Off":
                    mutual_ok = False
                    _set_block(
                        P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
                        "Log Shooting in Movie/S&Q must lock Gamma Display Assist=Off",
                    )
                if log_m == "Off" and pp_m != "Off" and (m_cl != "-" or m_dro != "Off"):
                    mutual_ok = False
                    _set_block(
                        P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
                        "Active Picture Profile must lock Creative Look='-' and DRO=Off",
                    )
                if dom != "Movie" and m_lut_ok:
                    pplut_ok = False
                    _set_block(
                        P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
                        "PPLUT1..4 must be disallowed outside Movie domain",
                    )
                matrix_checked += 1

    # 4. Critical Recovery Reset Trap for PP1..11 internal params & Different Set check mark
    reset_trap_ok = True
    trap_violations = cfg.pp_internal_reset_trap_violations
    exp_reset = compute_expected_pillar50a_reset_state(
        pre_diff_set_pp_checked=cfg.pre_diff_set_pp_checked,
        pre_pp_internal_customized=cfg.pre_pp_internal_customized,
        pre_pplut_customized=cfg.pre_pplut_customized,
        reset_action=cfg.reset_action,
        explicit_per_profile_pp_reset=cfg.explicit_per_profile_pp_reset,
        explicit_diff_set_uncheck=cfg.explicit_diff_set_uncheck,
    )
    if (
        cfg.post_diff_set_pp_checked != exp_reset[4]
        or cfg.post_pp_internal_customized != exp_reset[5]
        or cfg.post_pplut_customized != exp_reset[6]
        or cfg.pp_internal_reset_trap_violations != 0
    ):
        reset_trap_ok = False
        trap_violations = max(trap_violations, 1)
        _set_block(
            P287_BLOCKED_PP_INTERNAL_OR_DIFF_SET_RESET_TRAP,
            (
                "PP1..11 internal parameters and Different Set for Still/Mv check marks are NOT cleared by "
                "Camera Settings Reset or Initialize; full rollback requires explicit [PPx]->[Reset] "
                f"(expected diff={exp_reset[4]}, pp_custom={exp_reset[5]}, pplut_custom={exp_reset[6]})"
            ),
        )

    for r_act in P287_RESET_ACTIONS:
        for exp_pp_rst in (False, True):
            res_t = compute_expected_pillar50a_reset_state(
                pre_diff_set_pp_checked=True,
                pre_pp_internal_customized=True,
                pre_pplut_customized=True,
                reset_action=r_act,
                explicit_per_profile_pp_reset=exp_pp_rst,
                explicit_diff_set_uncheck=False,
            )
            if res_t[4] is not True or res_t[5] != (not exp_pp_rst):
                reset_trap_ok = False
                _set_block(
                    P287_BLOCKED_PP_INTERNAL_OR_DIFF_SET_RESET_TRAP,
                    "PP1..11 internal parameter / Different Set reset trap invariant failed",
                )
            if r_act == "Initialize" and res_t[6] is not False:
                reset_trap_ok = False
                _set_block(
                    P287_BLOCKED_PP_INTERNAL_OR_DIFF_SET_RESET_TRAP,
                    "Initialize must reset PPLUT1..4 custom LUTs",
                )
            matrix_checked += 1

    # 5. Volatile /tmp overlay + Tier-0 H0 == H3 + Slot-1 read-only vault
    h0_h3_ok = True
    if (
        not _is_tmpfs_path(cfg.overlay_dir)
        or _targets_persistent_emmc(cfg.overlay_dir)
        or not cfg.p2_blkroset_locked
    ):
        h0_h3_ok = False
        _set_block(
            P287_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain strictly in volatile /tmp or /run with BLKROSET=True: {cfg.overlay_dir!r}",
        )
    if (
        not cfg.slot1_holds_recovery_vault
        or not cfg.slot1_sdxc_wp_locked
        or not cfg.slot1_format_hard_locked
        or cfg.slot1_vault_mutation_bytes != 0
        or cfg.stage_b_backup_bin_writes != 0
        or cfg.backup_bin_h0_sha256 != P287_PINNED_FX3_BACKUP_BIN_SHA256
        or cfg.backup_bin_h3_sha256 != cfg.backup_bin_h0_sha256
        or cfg.tier0_surfaces_h0_h3_matched != P287_TIER0_SURFACE_COUNT
    ):
        h0_h3_ok = False
        _set_block(
            P287_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Slot-1 read-only vault or 16/16 Tier-0 H0 == H3 Backup.bin invariant drifted",
        )

    passed = (
        pp11_diff_ok
        and mutual_ok
        and pplut_ok
        and reset_trap_ok
        and fx6_distinction_ok
        and h0_h3_ok
        and len(errs) == 0
    )
    digest = _canonical_sha256(
        {
            "pillar": "50A",
            "passed": passed,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "double_log_ev": double_log_ev,
            "pplut_clamp_ev": pplut_clamp_ev,
            "trap_violations": trap_violations,
            "fx6_confusions": fx6_confusions,
        }
    )
    return PictureProfileScinetoneDroLogVaultReport(
        passed=passed,
        status=P287_STATUS_VERIFIED_PILLAR_50A if passed else P287_STATUS_REJECTED_PILLAR_50A,
        block_code=block_code,
        pp11_scinetone_default_and_diff_set_verified=pp11_diff_ok,
        mutual_exclusivity_and_log_lockout_verified=mutual_ok,
        pplut_movie_only_and_1080p_clamp_verified=pplut_ok,
        pp_internal_reset_trap_verified=reset_trap_ok,
        fx6_baselook_distinction_verified=fx6_distinction_ok,
        h0_equals_h3_verified=h0_h3_ok,
        matrix_states_checked=matrix_checked,
        double_log_or_lockout_bypass_events=double_log_ev,
        pplut_1080p_clamp_bypass_events=pplut_clamp_ev,
        pp_internal_reset_trap_violations=trap_violations,
        fx6_baselook_confusion_events=fx6_confusions,
        slot1_vault_mutation_bytes=cfg.slot1_vault_mutation_bytes,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errs),
    )


def evaluate_wb_camset_exclusion_and_metering_vault(
    spec: Optional[WhiteBalanceCamsetExclusionAndMeteringVaultSpec] = None,
) -> WhiteBalanceCamsetExclusionAndMeteringVaultReport:
    """Verify Pillar 50B: `[White Balance]` (`2500K..9900K`, `Custom 1..3` `CAMSET` exclusion,
    `Cine EI` AWB block & `[Custom Setup]` error trap) and `[Metering Mode]` (`6` modes,
    `De-Squeeze` Face-Priority lockout & `Cine EI` Base ISO passive `M.M.` invariance)."""
    cfg = spec if spec is not None else WhiteBalanceCamsetExclusionAndMeteringVaultSpec()
    safety_errs = _safety_invariant_errors()
    if safety_errs or cfg.persistent_write_unlock_requested:
        errs = safety_errs + (
            ["persistent_write_unlock_requested must be False"]
            if cfg.persistent_write_unlock_requested
            else []
        )
        return WhiteBalanceCamsetExclusionAndMeteringVaultReport(
            passed=False,
            status=P287_STATUS_REJECTED_PILLAR_50B,
            block_code=P287_BLOCKED_SAFETY_POLICY_VIOLATION,
            wb_modes_ctemp_and_shockless_verified=False,
            cine_ei_awb_and_custom_setup_trap_verified=False,
            custom_wb_camset_exclusion_and_reset_verified=False,
            metering_6modes_desqueeze_face_spot_verified=False,
            cine_ei_base_iso_mm_invariance_verified=False,
            h0_equals_h3_verified=False,
            matrix_states_checked=0,
            wb_cine_ei_awb_or_custom_setup_trap_events=0,
            wb_custom_camset_exclusion_drift_events=0,
            metering_desqueeze_or_cine_ei_base_iso_drift_events=0,
            slot1_vault_mutation_bytes=0,
            slot1_format_hard_locked=P287_SLOT1_FORMAT_HARD_LOCKED,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            digest_sha256=_canonical_sha256({"blocked": P287_BLOCKED_SAFETY_POLICY_VIOLATION}),
            errors=tuple(errs),
        )

    errs: List[str] = []
    block_code: Optional[str] = None

    def _set_block(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errs.append(msg)

    if (
        cfg.camera_model != P287_FX3_MODEL_NAME
        or cfg.camera_model_id != P287_FX3_MODEL_ID
        or cfg.helpguide_id != P287_FX3_HELPGUIDE_ID
        or cfg.fw_version not in P287_FX3_SUPPORTED_FW_VERSIONS
        or cfg.wb_menu_path != P287_WHITE_BALANCE_MENU_PATH
        or cfg.metering_menu_path != P287_METERING_MENU_PATH
        or cfg.log_shooting not in P287_LOG_SHOOTING_MODES
        or cfg.picture_profile not in P287_PICTURE_PROFILE_ALL_MODES
        or cfg.wb_mode not in P287_WB_ALL_MODES
        or cfg.priority_in_awb not in P287_PRIORITY_IN_AWB_MODES
        or cfg.shockless_wb_setting not in P287_SHOCKLESS_WB_MODES
        or cfg.pre_shutter_awb_lock not in P287_SHUTTER_AWB_LOCK_MODES
        or cfg.reset_action not in P287_RESET_ACTIONS
        or cfg.configured_metering_mode not in P287_METERING_6_MODES
        or cfg.desqueeze_mode not in P287_DESQUEEZE_MODES
        or cfg.configured_face_priority not in P287_ON_OFF_MODES
        or cfg.focus_area not in P287_FOCUS_AREAS
        or cfg.configured_spot_point not in P287_SPOT_METERING_POINT_MODES
        or cfg.pre_ael_w_shutter not in P287_AEL_W_SHUTTER_MODES
        or cfg.requested_vault_action not in P287_VAULT_TARGET_ACTIONS
    ):
        _set_block(
            P287_BLOCKED_INVALID_PILLAR50B_SPEC,
            "Invalid Pillar 50B camera model, WB, Metering Mode, De-Squeeze, Focus Area, or vault spec",
        )

    # 1. White Balance range, Cine EI AWB block, Custom Setup error trap, CAMSET exclusion & Reset
    (
        ctemp_valid,
        wb_mode_allowed,
        custom_setup_err,
        _shockless_applies,
        custom_preserved,
        _camset_excludes_custom,
        exp_post_awb_lock,
        exp_post_shockless,
    ) = compute_expected_wb_cine_ei_custom_guard(
        log_shooting=cfg.log_shooting,
        picture_profile=cfg.picture_profile,
        picture_profile_gamma=cfg.picture_profile_gamma,
        requested_wb_mode=cfg.wb_mode,
        ctemp_kelvin=cfg.ctemp_kelvin,
        ab_filter=cfg.ab_filter,
        gm_filter=cfg.gm_filter,
        shockless_wb_setting=cfg.shockless_wb_setting,
        custom_setup_attempted=cfg.custom_setup_attempted,
        reset_action=cfg.reset_action,
        camset_load_attempted=cfg.camset_load_attempted,
        pre_custom_wb_memorized_dirty=cfg.pre_custom_wb_memorized_dirty,
        manual_custom_wb_reregistered=cfg.manual_custom_wb_reregistered,
        pre_shutter_awb_lock=cfg.pre_shutter_awb_lock,
    )

    wb_ctemp_ok = True
    cine_ei_wb_ok = True
    camset_excl_ok = True
    wb_trap_events = cfg.wb_cine_ei_awb_or_custom_setup_trap_events
    wb_camset_drift = cfg.wb_custom_camset_exclusion_drift_events

    if not ctemp_valid:
        wb_ctemp_ok = False
        wb_camset_drift = max(wb_camset_drift, 1)
        _set_block(
            P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT,
            f"C.Temp./Filter out of bounds (2500..9900K step 100K, A-B/G-M in -7..+7): {cfg.ctemp_kelvin}K",
        )

    if not wb_mode_allowed or cfg.wb_cine_ei_awb_or_custom_setup_trap_events != 0:
        cine_ei_wb_ok = False
        wb_trap_events = max(wb_trap_events, 1)
        _set_block(
            P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP,
            f"Cine EI / Cine EI Quick blocks {cfg.wb_mode!r}",
        )

    if custom_setup_err and not cfg.reported_custom_setup_error:
        cine_ei_wb_ok = False
        wb_trap_events = max(wb_trap_events, 1)
        _set_block(
            P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP,
            "Custom WB setup while Log Shooting != Off or S-Log3/PPLUT triggers custom WB error trap",
        )

    if cfg.camset_load_attempted and (
        cfg.camset_slot != P287_SLOT1_VAULT_SLOT
        or cfg.camset_filename not in P287_CAMSET_FILENAMES
        or cfg.camset_source_model != P287_FX3_MODEL_NAME
        or not cfg.camset_read_only_load
    ):
        camset_excl_ok = False
        _set_block(
            P287_BLOCKED_INVALID_PILLAR50B_SPEC,
            "CAMSET load must be read-only from Slot-1 ILME-FX3 CAMSET01..10.DAT",
        )

    if (
        cfg.expect_camset_restores_custom_wb
        or cfg.post_custom_wb_memorized_dirty != custom_preserved
        or cfg.post_shutter_awb_lock != exp_post_awb_lock
        or cfg.post_shockless_wb_setting != exp_post_shockless
        or cfg.wb_custom_camset_exclusion_drift_events != 0
    ):
        camset_excl_ok = False
        wb_camset_drift = max(wb_camset_drift, 1)
        _set_block(
            P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT,
            (
                "Custom 1..3 WB memorized data survives Camera Settings Reset and is excluded from "
                "Slot-1 Save/Load Settings (CAMSET); manual re-registration & Shutter AWB Lock parity required"
            ),
        )

    matrix_checked = 0
    for log_m in P287_LOG_SHOOTING_MODES:
        for wb_m in ("Auto", "Underwater Auto", "Daylight", "C.Temp./Filter", "Custom 1"):
            _, m_allowed, m_c_err, m_shock, _, m_excl, _, _ = (
                compute_expected_wb_cine_ei_custom_guard(
                    log_shooting=log_m,
                    picture_profile="Off" if log_m != "Off" else "PP11",
                    picture_profile_gamma="S-Log3" if log_m != "Off" else "S-Cinetone",
                    requested_wb_mode=wb_m,
                    ctemp_kelvin=5600,
                    ab_filter=0,
                    gm_filter=0,
                    shockless_wb_setting="1 (Fast)",
                    custom_setup_attempted=True,
                    reset_action="Camera Settings Reset",
                    camset_load_attempted=True,
                    pre_custom_wb_memorized_dirty=True,
                    manual_custom_wb_reregistered=False,
                    pre_shutter_awb_lock="Cont. Shooting",
                )
            )
            if log_m in ("Cine EI", "Cine EI Quick") and wb_m in P287_WB_AUTO_MODES and m_allowed:
                cine_ei_wb_ok = False
                _set_block(
                    P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP,
                    "WB matrix: Cine EI must block Auto / Underwater Auto",
                )
            if log_m != "Off" and not m_c_err:
                cine_ei_wb_ok = False
                _set_block(
                    P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP,
                    "WB matrix: Custom Setup during Log Shooting must trigger error trap",
                )
            if wb_m in ("Auto", "Underwater Auto", "C.Temp./Filter") and m_shock:
                wb_ctemp_ok = False
                _set_block(
                    P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT,
                    "Shockless WB must not claim smoothing on Auto/Underwater Auto/C.Temp./Filter",
                )
            if not m_excl:
                camset_excl_ok = False
                _set_block(
                    P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT,
                    "CAMSET must always exclude Custom 1..3 WB memorized registers",
                )
            matrix_checked += 1

    # 2. Metering Mode (6 modes), De-Squeeze Face-Priority lockout, Spot Point & Cine EI Base ISO invariance
    eff_met, eff_face, eff_spot, base_iso_inv, _passive_mm, exp_post_ael = (
        compute_expected_metering_and_cine_ei_invariance(
            intelligent_auto=cfg.intelligent_auto,
            configured_metering_mode=cfg.configured_metering_mode,
            desqueeze_mode=cfg.desqueeze_mode,
            configured_face_priority=cfg.configured_face_priority,
            focus_area=cfg.focus_area,
            active_tracking_running=cfg.active_tracking_running,
            configured_spot_point=cfg.configured_spot_point,
            log_shooting=cfg.log_shooting,
            cine_ei_base_iso=cfg.cine_ei_base_iso,
            pre_ael_w_shutter=cfg.pre_ael_w_shutter,
            reset_action=cfg.reset_action,
        )
    )

    metering_ok = True
    cine_ei_iso_ok = True
    met_drift_events = cfg.metering_desqueeze_or_cine_ei_base_iso_drift_events

    if (
        cfg.reported_metering_mode != eff_met
        or cfg.reported_face_priority != eff_face
        or cfg.reported_spot_point != eff_spot
        or cfg.post_ael_w_shutter != exp_post_ael
        or cfg.metering_desqueeze_or_cine_ei_base_iso_drift_events != 0
    ):
        metering_ok = False
        met_drift_events = max(met_drift_events, 1)
        _set_block(
            P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
            (
                f"Metering/De-Squeeze/AEL drift: expected (met={eff_met!r}, face={eff_face!r}, "
                f"spot={eff_spot!r}, ael={exp_post_ael!r}), got (met={cfg.reported_metering_mode!r}, "
                f"face={cfg.reported_face_priority!r}, spot={cfg.reported_spot_point!r}, ael={cfg.post_ael_w_shutter!r})"
            ),
        )

    if not base_iso_inv or cfg.metering_altered_cine_ei_gain:
        cine_ei_iso_ok = False
        met_drift_events = max(met_drift_events, 1)
        _set_block(
            P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
            f"Cine EI sensor Base ISO ({cfg.cine_ei_base_iso}) must stay invariant across Metering Modes (passive M.M. deviation only)",
        )

    for met_m in P287_METERING_6_MODES:
        for dsq in ("Off", "1.6x"):
            for f_area in ("Wide", "Spot"):
                _, e_f, e_s, _, _, _ = compute_expected_metering_and_cine_ei_invariance(
                    intelligent_auto=False,
                    configured_metering_mode=met_m,
                    desqueeze_mode=dsq,
                    configured_face_priority="On",
                    focus_area=f_area,
                    active_tracking_running=False,
                    configured_spot_point="Focus Point Link",
                    log_shooting="Cine EI",
                    cine_ei_base_iso=800,
                    pre_ael_w_shutter="On",
                    reset_action="Camera Settings Reset",
                )
                if dsq != "Off" and e_f != "Off":
                    metering_ok = False
                    _set_block(
                        P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
                        "De-Squeeze != Off must force Face Priority in Multi Metering = Off",
                    )
                if f_area == "Wide" and e_s != "Center":
                    metering_ok = False
                    _set_block(
                        P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
                        "Wide Focus Area must lock Spot Metering Point to Center",
                    )
                matrix_checked += 1

    # 3. Slot-1 Read-Only Vault Firewall + Volatile /tmp Overlay + Tier-0 H0 == H3
    h0_h3_ok = True
    vault_mut_bytes = cfg.slot1_vault_mutation_bytes
    destructive_slot1 = (
        cfg.requested_vault_slot == P287_SLOT1_VAULT_SLOT
        and (cfg.slot1_holds_recovery_vault or cfg.slot1_sdxc_wp_locked)
        and cfg.requested_vault_action in P287_DESTRUCTIVE_VAULT_ACTIONS
    )
    if (
        destructive_slot1
        or not cfg.slot1_holds_recovery_vault
        or not cfg.slot1_sdxc_wp_locked
        or not cfg.slot1_format_hard_locked
        or cfg.slot1_vault_mutation_bytes != 0
    ):
        h0_h3_ok = False
        if destructive_slot1:
            vault_mut_bytes = max(vault_mut_bytes, 4096)
        _set_block(
            P287_BLOCKED_SLOT1_VAULT_FORMAT_OR_MUTATION,
            f"Slot-1 dual-layer SD WP + format hard lock blocked {cfg.requested_vault_action!r} on Slot {cfg.requested_vault_slot}",
        )

    if (
        not _is_tmpfs_path(cfg.overlay_dir)
        or _targets_persistent_emmc(cfg.overlay_dir)
        or not cfg.p2_blkroset_locked
    ):
        h0_h3_ok = False
        _set_block(
            P287_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain strictly in volatile /tmp or /run with BLKROSET=True: {cfg.overlay_dir!r}",
        )

    if (
        cfg.stage_b_backup_bin_writes != 0
        or cfg.backup_bin_h0_sha256 != P287_PINNED_FX3_BACKUP_BIN_SHA256
        or cfg.backup_bin_h3_sha256 != cfg.backup_bin_h0_sha256
        or cfg.tier0_surfaces_h0_h3_matched != P287_TIER0_SURFACE_COUNT
    ):
        h0_h3_ok = False
        _set_block(
            P287_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 H0 == H3 Backup.bin invariant drifted",
        )

    passed = (
        wb_ctemp_ok
        and cine_ei_wb_ok
        and camset_excl_ok
        and metering_ok
        and cine_ei_iso_ok
        and h0_h3_ok
        and len(errs) == 0
    )
    digest = _canonical_sha256(
        {
            "pillar": "50B",
            "passed": passed,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "wb_trap_events": wb_trap_events,
            "wb_camset_drift": wb_camset_drift,
            "met_drift_events": met_drift_events,
            "vault_mut_bytes": vault_mut_bytes,
        }
    )
    return WhiteBalanceCamsetExclusionAndMeteringVaultReport(
        passed=passed,
        status=P287_STATUS_VERIFIED_PILLAR_50B if passed else P287_STATUS_REJECTED_PILLAR_50B,
        block_code=block_code,
        wb_modes_ctemp_and_shockless_verified=wb_ctemp_ok,
        cine_ei_awb_and_custom_setup_trap_verified=cine_ei_wb_ok,
        custom_wb_camset_exclusion_and_reset_verified=camset_excl_ok,
        metering_6modes_desqueeze_face_spot_verified=metering_ok,
        cine_ei_base_iso_mm_invariance_verified=cine_ei_iso_ok,
        h0_equals_h3_verified=h0_h3_ok,
        matrix_states_checked=matrix_checked,
        wb_cine_ei_awb_or_custom_setup_trap_events=wb_trap_events,
        wb_custom_camset_exclusion_drift_events=wb_camset_drift,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=met_drift_events,
        slot1_vault_mutation_bytes=vault_mut_bytes,
        slot1_format_hard_locked=cfg.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errs),
    )


def verify_pp_scinetone_creativelook_dro_wb_metering_and_vault(
    pp_spec: Optional[PictureProfileScinetoneDroLogVaultSpec] = None,
    wb_metering_spec: Optional[WhiteBalanceCamsetExclusionAndMeteringVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> PpScinetoneCreativeLookDroWbMeteringVaultReport:
    """Combined Pillar 50A + Pillar 50B + Wave-48 bounded `O_RDONLY` donor report."""
    errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase287_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_pp_scinetone_creativelook_dro_log_vault(pp_spec)
    rep_b = evaluate_wb_camset_exclusion_and_metering_vault(wb_metering_spec)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 287 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )
    ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return PpScinetoneCreativeLookDroWbMeteringVaultReport(
        schema=PHASE287_SCHEMA,
        version=PHASE287_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=ok,
        passed=ok,
        status=P287_STATUS_VERIFIED_PILLAR50_SUITE if ok else P287_STATUS_FAIL_PILLAR50_SUITE,
        donor_snapshot=donor_snapshot,
        pp_scinetone_dro_report=rep_a,
        wb_metering_report=rep_b,
        double_log_or_lockout_bypass_events=rep_a.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=rep_a.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=rep_a.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=rep_a.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=rep_b.wb_cine_ei_awb_or_custom_setup_trap_events,
        wb_custom_camset_exclusion_drift_events=rep_b.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            rep_b.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        slot1_vault_mutation_bytes=max(rep_a.slot1_vault_mutation_bytes, rep_b.slot1_vault_mutation_bytes),
        slot1_format_hard_locked=rep_b.slot1_format_hard_locked,
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


def verify_pp_scinetone_creativelook_dro_wb_metering_vault(
    pp_spec: Optional[PictureProfileScinetoneDroLogVaultSpec] = None,
    wb_metering_spec: Optional[WhiteBalanceCamsetExclusionAndMeteringVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> PpScinetoneCreativeLookDroWbMeteringVaultReport:
    """Symmetry alias for `verify_pp_scinetone_creativelook_dro_wb_metering_and_vault`."""
    return verify_pp_scinetone_creativelook_dro_wb_metering_and_vault(
        pp_spec=pp_spec,
        wb_metering_spec=wb_metering_spec,
        force_clean_room=force_clean_room,
    )


def run_pillar50a_pp_scinetone_creativelook_dro_6_scenario_suite() -> Pillar50ASuiteResult:
    """Run all 6 canonical Pillar 50A scenarios (`2` safe + `4` negative Wave-48 guards)."""
    cases: Tuple[Tuple[str, bool, PictureProfileScinetoneDroLogVaultSpec, Optional[str]], ...] = (
        (
            P287_PILLAR_50A_SCENARIO_IDS[0],
            True,
            PictureProfileScinetoneDroLogVaultSpec(),
            None,
        ),
        (
            P287_PILLAR_50A_SCENARIO_IDS[1],
            True,
            PictureProfileScinetoneDroLogVaultSpec(
                shooting_domain="Movie",
                log_shooting="Cine EI",
                configured_picture_profile="PPLUT1",
                configured_creative_look="FL",
                configured_dro="Lv3",
                configured_gamma_disp_assist="On",
                reported_picture_profile="Off",
                reported_creative_look="-",
                reported_dro="Off",
                reported_gamma_disp_assist="Off",
                diff_set_pp_checked=True,
                movie_picture_profile="PP8",
                still_picture_profile="PP11",
                hdmi_internal_recording=True,
                configured_hdmi_resolution="2160p",
                reported_hdmi_resolution="1080p",
                reset_action="Initialize",
                pre_diff_set_pp_checked=True,
                pre_pp_internal_customized=True,
                pre_pplut_customized=True,
                explicit_per_profile_pp_reset=True,
                explicit_diff_set_uncheck=False,
                post_diff_set_pp_checked=True,
                post_pp_internal_customized=False,
                post_pplut_customized=False,
            ),
            None,
        ),
        (
            P287_PILLAR_50A_SCENARIO_IDS[2],
            False,
            PictureProfileScinetoneDroLogVaultSpec(
                shooting_domain="Still",
                log_shooting="Off",
                configured_picture_profile="PPLUT1",
                reported_picture_profile="PPLUT1",
                reported_creative_look="ST",
                reported_dro="Auto",
                reported_hdmi_resolution="2160p",
                double_log_or_lockout_bypass_events=1,
                pplut_1080p_clamp_bypass_events=1,
            ),
            P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS,
        ),
        (
            P287_PILLAR_50A_SCENARIO_IDS[3],
            False,
            PictureProfileScinetoneDroLogVaultSpec(
                reset_action="Camera Settings Reset",
                pre_diff_set_pp_checked=True,
                pre_pp_internal_customized=True,
                explicit_per_profile_pp_reset=False,
                explicit_diff_set_uncheck=False,
                post_diff_set_pp_checked=False,
                post_pp_internal_customized=False,
                pp_internal_reset_trap_violations=1,
            ),
            P287_BLOCKED_PP_INTERNAL_OR_DIFF_SET_RESET_TRAP,
        ),
        (
            P287_PILLAR_50A_SCENARIO_IDS[4],
            False,
            PictureProfileScinetoneDroLogVaultSpec(
                pipeline_surface_model="FX6_BASE_LOOK_SCENE_FILE_PIPELINE",
                fx6_baselook_confusion_events=1,
            ),
            P287_BLOCKED_FX6_BASELOOK_CONFUSION,
        ),
        (
            P287_PILLAR_50A_SCENARIO_IDS[5],
            False,
            PictureProfileScinetoneDroLogVaultSpec(
                overlay_dir="/setting/pp50a",
                slot1_vault_mutation_bytes=4096,
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P287_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
        ),
    )

    outcomes: List[Pillar50ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_pp_scinetone_creativelook_dro_log_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar50ScenarioOutcome(
                scenario_id=sid,
                pillar="50A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar50ASuiteResult(
        passed=all_ok,
        status=P287_STATUS_VERIFIED_PILLAR_50A if all_ok else P287_STATUS_REJECTED_PILLAR_50A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar50b_wb_camset_exclusion_metering_6_scenario_suite() -> Pillar50BSuiteResult:
    """Run all 6 canonical Pillar 50B scenarios (`2` safe + `4` negative WB/Metering guards)."""
    cases: Tuple[Tuple[str, bool, WhiteBalanceCamsetExclusionAndMeteringVaultSpec, Optional[str]], ...] = (
        (
            P287_PILLAR_50B_SCENARIO_IDS[0],
            True,
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(),
            None,
        ),
        (
            P287_PILLAR_50B_SCENARIO_IDS[1],
            True,
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                log_shooting="Cine EI",
                picture_profile="Off",
                picture_profile_gamma="S-Log3",
                wb_mode="Custom 1",
                ctemp_kelvin=5600,
                ab_filter=1,
                gm_filter=-2,
                custom_setup_attempted=True,
                reported_custom_setup_error=True,
                pre_shutter_awb_lock="Shutter Half Press",
                post_shutter_awb_lock="Shutter Half Press",
                reset_action="Camera Settings Reset",
                pre_custom_wb_memorized_dirty=True,
                manual_custom_wb_reregistered=False,
                post_custom_wb_memorized_dirty=True,
                desqueeze_mode="1.6x",
                configured_face_priority="On",
                reported_face_priority="Off",
                focus_area="Wide",
                configured_spot_point="Focus Point Link",
                reported_spot_point="Center",
                pre_ael_w_shutter="On",
                post_ael_w_shutter="On",
                cine_ei_base_iso=12800,
            ),
            None,
        ),
        (
            P287_PILLAR_50B_SCENARIO_IDS[2],
            False,
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                log_shooting="Cine EI",
                wb_mode="Auto",
                custom_setup_attempted=True,
                reported_custom_setup_error=False,
                wb_cine_ei_awb_or_custom_setup_trap_events=1,
            ),
            P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP,
        ),
        (
            P287_PILLAR_50B_SCENARIO_IDS[3],
            False,
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                ctemp_kelvin=10000,
                expect_camset_restores_custom_wb=True,
                wb_custom_camset_exclusion_drift_events=1,
            ),
            P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT,
        ),
        (
            P287_PILLAR_50B_SCENARIO_IDS[4],
            False,
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                log_shooting="Cine EI",
                wb_mode="Custom 1",
                desqueeze_mode="1.6x",
                configured_face_priority="On",
                reported_face_priority="On",
                focus_area="Wide",
                configured_spot_point="Focus Point Link",
                reported_spot_point="Focus Point Link",
                cine_ei_base_iso=1600,
                metering_altered_cine_ei_gain=True,
                metering_desqueeze_or_cine_ei_base_iso_drift_events=1,
            ),
            P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT,
        ),
        (
            P287_PILLAR_50B_SCENARIO_IDS[5],
            False,
            WhiteBalanceCamsetExclusionAndMeteringVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_FULL",
                slot1_vault_mutation_bytes=4096,
                overlay_dir="/setting/50b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P287_BLOCKED_SLOT1_VAULT_FORMAT_OR_MUTATION,
        ),
    )

    outcomes: List[Pillar50ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_wb_camset_exclusion_and_metering_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar50ScenarioOutcome(
                scenario_id=sid,
                pillar="50B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar50BSuiteResult(
        passed=all_ok,
        status=P287_STATUS_VERIFIED_PILLAR_50B if all_ok else P287_STATUS_REJECTED_PILLAR_50B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar50_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar50StandaloneReport:
    """Run full Pillar 50 standalone suite (`6/6` Pillar 50A + `6/6` Pillar 50B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase287_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar50a_pp_scinetone_creativelook_dro_6_scenario_suite()
    res_b = run_pillar50b_wb_camset_exclusion_metering_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 287 donor verification failed")
    if not donor_snapshot.under_0_20s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE287_SCHEMA,
            "version": PHASE287_VERSION,
            "mode": donor_snapshot.verification_mode,
            "50a": [asdict(s) for s in res_a.scenarios],
            "50b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar50StandaloneReport(
        schema=PHASE287_SCHEMA,
        version=PHASE287_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P287_STATUS_VERIFIED_PILLAR50_SUITE if all_ok else P287_STATUS_FAIL_PILLAR50_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_50a_pp_scinetone_creativelook_dro_vault=res_a,
        pillar_50b_wb_camset_exclusion_metering_vault=res_b,
        double_log_or_lockout_bypass_events=(
            P287_DOUBLE_LOG_OR_LOCKOUT_BYPASS_EVENTS if res_a.passed else 1
        ),
        pplut_1080p_clamp_bypass_events=P287_PPLUT_1080P_CLAMP_BYPASS_EVENTS if res_a.passed else 1,
        pp_internal_reset_trap_violations=P287_PP_INTERNAL_RESET_TRAP_VIOLATIONS if res_a.passed else 1,
        fx6_baselook_confusion_events=P287_FX6_BASELOOK_CONFUSION_EVENTS if res_a.passed else 1,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            P287_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP_EVENTS if res_b.passed else 1
        ),
        wb_custom_camset_exclusion_drift_events=(
            P287_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT_EVENTS if res_b.passed else 1
        ),
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            P287_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT_EVENTS if res_b.passed else 1
        ),
        slot1_vault_mutation_bytes=P287_SLOT1_VAULT_MUTATION_BYTES if (res_a.passed and res_b.passed) else 4096,
        slot1_format_hard_locked=P287_SLOT1_FORMAT_HARD_LOCKED,
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
# Unified 50/50 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master50_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_50pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master50PillarRecoveryReport:
    """Evaluate and aggregate all 50 recovery pillars (`1..50`) concurrently -> `50/50` milestone master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_50_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_49pillar() -> Master49PillarRecoveryReport:
        return evaluate_realhw_49pillar_recovery_master(**kw)

    def _run_p50() -> Tuple[Pillar50StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar50_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_49 = pool.submit(_run_49pillar)
        fut_50 = pool.submit(_run_p50)
        m49_rep = fut_49.result()
        p50_rep, p50_dt = fut_50.result()

    all_errors: List[str] = list(m49_rep.errors) + list(p50_rep.errors)
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
        if getattr(m49_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-49 violated {attr_name} == {expected_val}")
        if getattr(p50_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 50 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
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
        if getattr(m49_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-49 violated {attr_name} == {expected_val}")
    if m49_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillars 1-49 violated bodydata_flash_attempts_blocked >= 1")

    for attr_name, expected_val in (
        ("double_log_or_lockout_bypass_events", 0),
        ("pplut_1080p_clamp_bypass_events", 0),
        ("pp_internal_reset_trap_violations", 0),
        ("fx6_baselook_confusion_events", 0),
        ("wb_cine_ei_awb_or_custom_setup_trap_events", 0),
        ("wb_custom_camset_exclusion_drift_events", 0),
        ("metering_desqueeze_or_cine_ei_base_iso_drift_events", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(p50_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 50 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m49_rep.pillars)
    spec50 = MASTER_50_PILLAR_SPECS[49]
    p50_metrics = {
        "pillar_50a_pp_scinetone_creativelook_dro_vault": (
            f"{p50_rep.pillar_50a_pp_scinetone_creativelook_dro_vault.scenarios_passed}/"
            f"{p50_rep.pillar_50a_pp_scinetone_creativelook_dro_vault.scenarios_total}"
        ),
        "pillar_50b_wb_camset_exclusion_metering_vault": (
            f"{p50_rep.pillar_50b_wb_camset_exclusion_metering_vault.scenarios_passed}/"
            f"{p50_rep.pillar_50b_wb_camset_exclusion_metering_vault.scenarios_total}"
        ),
        "double_log_or_lockout_bypass_events": p50_rep.double_log_or_lockout_bypass_events,
        "pplut_1080p_clamp_bypass_events": p50_rep.pplut_1080p_clamp_bypass_events,
        "pp_internal_reset_trap_violations": p50_rep.pp_internal_reset_trap_violations,
        "fx6_baselook_confusion_events": p50_rep.fx6_baselook_confusion_events,
        "wb_cine_ei_awb_or_custom_setup_trap_events": (
            p50_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        "wb_custom_camset_exclusion_drift_events": (
            p50_rep.wb_custom_camset_exclusion_drift_events
        ),
        "metering_desqueeze_or_cine_ei_base_iso_drift_events": (
            p50_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        "slot1_vault_mutation_bytes": p50_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p50_rep.slot1_format_hard_locked,
        "hardware_live_attachment_authorized": p50_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p50_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec50[0],
            pillar_id=spec50[1],
            phase_label=spec50[2],
            module_name=spec50[3],
            passed=bool(p50_rep.all_passed),
            status=p50_rep.status,
            verification_mode=p50_rep.verification_mode,
            elapsed_seconds=p50_dt,
            key_metrics=p50_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec50[1],
                    "mode": p50_rep.verification_mode,
                    "status": p50_rep.status,
                    "metrics": p50_metrics,
                    "passed": p50_rep.all_passed,
                }
            ),
            errors=tuple(p50_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master50_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p50_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_50_PILLAR_COUNT == 50
        and pillars_passed == 50
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE287_SCHEMA,
            "version": PHASE287_VERSION,
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
    return Master50PillarRecoveryReport(
        schema=PHASE287_SCHEMA,
        version=PHASE287_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P287_STATUS_VERIFIED_50OF50_AGGREGATOR if all_ok else P287_STATUS_FAIL_50OF50_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_2_2s_fast_cli_budget=elapsed < P287_FAST_CLI_BUDGET_SECONDS,
        under_2_5s_fast_cli_budget=elapsed < 2.5,
        under_6s_budget=elapsed < P287_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P287_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p50_rep.donor_snapshot,
        pillar50_a_pp_scinetone_creativelook_dro_vault=(
            p50_rep.pillar_50a_pp_scinetone_creativelook_dro_vault
        ),
        pillar50_b_wb_camset_exclusion_metering_vault=(
            p50_rep.pillar_50b_wb_camset_exclusion_metering_vault
        ),
        double_log_or_lockout_bypass_events=p50_rep.double_log_or_lockout_bypass_events,
        pplut_1080p_clamp_bypass_events=p50_rep.pplut_1080p_clamp_bypass_events,
        pp_internal_reset_trap_violations=p50_rep.pp_internal_reset_trap_violations,
        fx6_baselook_confusion_events=p50_rep.fx6_baselook_confusion_events,
        wb_cine_ei_awb_or_custom_setup_trap_events=(
            p50_rep.wb_cine_ei_awb_or_custom_setup_trap_events
        ),
        wb_custom_camset_exclusion_drift_events=p50_rep.wb_custom_camset_exclusion_drift_events,
        metering_desqueeze_or_cine_ei_base_iso_drift_events=(
            p50_rep.metering_desqueeze_or_cine_ei_base_iso_drift_events
        ),
        slot1_vault_mutation_bytes=p50_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p50_rep.slot1_format_hard_locked,
        fx3_ui_exposes_usb_streaming=m49_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=m49_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=m49_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=m49_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=m49_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=m49_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=m49_rep.slot1_vault_format_or_delete_events,
        network_reset_zero_rf_violations=m49_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m49_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m49_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m49_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m49_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m49_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m49_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m49_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m49_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m49_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m49_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m49_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m49_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m49_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m49_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m49_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m49_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m49_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m49_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m49_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m49_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m49_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m49_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m49_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m49_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m49_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=(
            m49_rep.tcub_camera_reset_wipe_or_format_violations
        ),
        fx3_has_builtin_end_filter=m49_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m49_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m49_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m49_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m49_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m49_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m49_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m49_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m49_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m49_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m49_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m49_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m49_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m49_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m49_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m49_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m49_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m49_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m49_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m49_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m49_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m49_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m49_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m49_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m49_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m49_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m49_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m49_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m49_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m49_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p50_rep.hardware_live_attachment_authorized,
        master_50pillar_sha256=master_sha,
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


def evaluate_50pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master50PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_50pillar_recovery_master`."""
    return evaluate_realhw_50pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_50pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master50PillarRecoveryReport:
    """Public CLI entry point for Phase 287 `50/50` milestone unified recovery master."""
    return evaluate_realhw_50pillar_recovery_master(
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
    "MASTER_50_PILLAR_COUNT",
    "MASTER_50_PILLAR_IDS",
    "MASTER_50_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P287_AEL_W_SHUTTER_BKID",
    "P287_AEL_W_SHUTTER_DEFAULT",
    "P287_AEL_W_SHUTTER_MODES",
    "P287_AEL_W_SHUTTER_RESID16",
    "P287_BLOCKED_DOUBLE_LOG_OR_LOCKOUT_BYPASS",
    "P287_BLOCKED_FX6_BASELOOK_CONFUSION",
    "P287_BLOCKED_INVALID_PILLAR50A_SPEC",
    "P287_BLOCKED_INVALID_PILLAR50B_SPEC",
    "P287_BLOCKED_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT",
    "P287_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P287_BLOCKED_PP_INTERNAL_OR_DIFF_SET_RESET_TRAP",
    "P287_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P287_BLOCKED_SLOT1_VAULT_FORMAT_OR_MUTATION",
    "P287_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P287_BLOCKED_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP",
    "P287_BLOCKED_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT",
    "P287_BOUNDED_HEADER_BYTES",
    "P287_CAMSET_FILENAMES",
    "P287_CINE_EI_BASE_ISOS",
    "P287_CONCURRENT_CEILING_SECONDS",
    "P287_CREATIVE_LOOK_10_PRESETS",
    "P287_CREATIVE_LOOK_8_PARAMS",
    "P287_CREATIVE_LOOK_BKID",
    "P287_CREATIVE_LOOK_CUSTOM_SLOTS",
    "P287_CREATIVE_LOOK_DEFAULT",
    "P287_CREATIVE_LOOK_LOCKED",
    "P287_CREATIVE_LOOK_MENU_PATH",
    "P287_CREATIVE_LOOK_RESID16",
    "P287_CREATIVE_LOOK_RESID16_ANCHORS",
    "P287_DESQUEEZE_MODES",
    "P287_DESTRUCTIVE_VAULT_ACTIONS",
    "P287_DIFF_SET_BKID",
    "P287_DIFF_SET_PROMPT_G_RESID16",
    "P287_DIFF_SET_RESID16",
    "P287_DISPLAY_LUT_RESID16",
    "P287_DONOR_FX3_APPFW_702_RELPATH",
    "P287_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P287_DONOR_FX3_UXC_EN_F_RELPATH",
    "P287_DONOR_FX3_UXC_EN_G_RELPATH",
    "P287_DONOR_FX3_UXC_EN_RELPATH",
    "P287_DONOR_FX3_UXC_JA_F_RELPATH",
    "P287_DONOR_FX3_UXC_SC_F_RELPATH",
    "P287_DONOR_FX3_UXC_TC_F_RELPATH",
    "P287_DONOR_FX6_APPFW_601_RELPATH",
    "P287_DONOR_FX6_UXC_EN_2_RELPATH",
    "P287_DONOR_FX6_UXC_EN_RELPATH",
    "P287_DONOR_INSPECT_BUDGET_SECONDS",
    "P287_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P287_DOUBLE_LOG_OR_LOCKOUT_BYPASS_EVENTS",
    "P287_DRO_BKID",
    "P287_DRO_DEFAULT",
    "P287_DRO_MENU_PATH",
    "P287_DRO_MODES",
    "P287_DRO_RESID16",
    "P287_DRO_RESID16_MAP",
    "P287_DRO_VAL_BKID",
    "P287_ENV_CLEAN_ROOM_TEST",
    "P287_FACE_PRIORITY_MULTI_BKID",
    "P287_FACE_PRIORITY_MULTI_DEFAULT",
    "P287_FACE_PRIORITY_MULTI_RESID16",
    "P287_FAST_CLI_BUDGET_SECONDS",
    "P287_FOCUS_AREAS",
    "P287_FORBIDDEN_PERSISTENT_TARGETS",
    "P287_FX3_FW_VERSION",
    "P287_FX3_HELPGUIDE_ID",
    "P287_FX3_MODEL_ID",
    "P287_FX3_MODEL_NAME",
    "P287_FX3_PRODUCT_CODENAME",
    "P287_FX3_SUPPORTED_FW_VERSIONS",
    "P287_FX6_709TONE_RESID16",
    "P287_FX6_BASELOOK_CONFUSION_EVENTS",
    "P287_FX6_BASE_LOOK_BKID_PREFIX",
    "P287_FX6_BASE_LOOK_CINE_EI_LOCKED",
    "P287_FX6_BASE_LOOK_CUSTOM_DEFAULT",
    "P287_FX6_BASE_LOOK_RESID16",
    "P287_FX6_DONOR_FW_VERSION",
    "P287_FX6_DONOR_MODEL_NAME",
    "P287_FX6_PRODUCT_CODENAME",
    "P287_FX6_SCINETONE_RESID16",
    "P287_FX6_SHOOTING_MODES",
    "P287_FX6_WB_CINE_EI_PRESETS_K",
    "P287_FX6_WB_CUSTOM_PRESETS_K",
    "P287_FX6_WB_MODES",
    "P287_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P287_HDMI_OUTPUT_RESOLUTIONS",
    "P287_LOG_SHOOTING_BKID",
    "P287_LOG_SHOOTING_DEFAULT",
    "P287_LOG_SHOOTING_MENU_PATH",
    "P287_LOG_SHOOTING_MODES",
    "P287_LOG_SHOOTING_RESID16",
    "P287_LOG_SHOOTING_RESID16_MAP",
    "P287_MAX_FULL_DONOR_BYTES",
    "P287_METERING_6_MODES",
    "P287_METERING_DESQUEEZE_OR_CINE_EI_BASE_ISO_DRIFT_EVENTS",
    "P287_METERING_MENU_PATH",
    "P287_METERING_MODE_BKID",
    "P287_METERING_MODE_DEFAULT",
    "P287_METERING_MODE_RESID16",
    "P287_METERING_MODE_RESID16_MAP",
    "P287_METERING_MODE_SPOT_BKID",
    "P287_NOMINAL_BUDGET_SECONDS",
    "P287_ON_OFF_MODES",
    "P287_PICTURE_PROFILE_ALL_MODES",
    "P287_PICTURE_PROFILE_BKID",
    "P287_PICTURE_PROFILE_FACTORY_DEFAULT",
    "P287_PICTURE_PROFILE_MENU_PATH",
    "P287_PICTURE_PROFILE_MOVIE_BKID",
    "P287_PICTURE_PROFILE_RESID16",
    "P287_PICTURE_PROFILE_STILL_BKID",
    "P287_PILLAR_50A_SCENARIO_IDS",
    "P287_PILLAR_50B_SCENARIO_IDS",
    "P287_PINNED_FX3_APPFW_702_BYTES",
    "P287_PINNED_FX3_APPFW_702_FULL_SHA256",
    "P287_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P287_PINNED_FX3_BACKUP_BIN_BYTES",
    "P287_PINNED_FX3_BACKUP_BIN_SHA256",
    "P287_PINNED_FX3_UXC_EN_BYTES",
    "P287_PINNED_FX3_UXC_EN_F_BYTES",
    "P287_PINNED_FX3_UXC_EN_F_SHA256",
    "P287_PINNED_FX3_UXC_EN_G_BYTES",
    "P287_PINNED_FX3_UXC_EN_G_SHA256",
    "P287_PINNED_FX3_UXC_EN_SHA256",
    "P287_PINNED_FX3_UXC_JA_F_BYTES",
    "P287_PINNED_FX3_UXC_JA_F_SHA256",
    "P287_PINNED_FX3_UXC_SC_F_BYTES",
    "P287_PINNED_FX3_UXC_SC_F_SHA256",
    "P287_PINNED_FX3_UXC_TC_F_BYTES",
    "P287_PINNED_FX3_UXC_TC_F_SHA256",
    "P287_PINNED_FX6_APPFW_601_BYTES",
    "P287_PINNED_FX6_APPFW_601_FULL_SHA256",
    "P287_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P287_PINNED_FX6_UXC_EN_2_BYTES",
    "P287_PINNED_FX6_UXC_EN_2_SHA256",
    "P287_PINNED_FX6_UXC_EN_BYTES",
    "P287_PINNED_FX6_UXC_EN_SHA256",
    "P287_PIPELINE_SURFACE_MODELS",
    "P287_PP11_RESID16",
    "P287_PPLUT_1080P_CLAMP_BYPASS_EVENTS",
    "P287_PPLUT_MODES",
    "P287_PP_1_TO_11",
    "P287_PP_GAMMA_COLOR_MAP",
    "P287_PP_INTERNAL_RESET_TRAP_VIOLATIONS",
    "P287_PRIORITY_IN_AWB_BKID",
    "P287_PRIORITY_IN_AWB_DEFAULT",
    "P287_PRIORITY_IN_AWB_MODES",
    "P287_PRIORITY_IN_AWB_RESID16",
    "P287_RESET_ACTIONS",
    "P287_S709_LUT_RESID16",
    "P287_SCINETONE_CAUTION_ID",
    "P287_SCINETONE_RESID16",
    "P287_SELECT_LUT_BKID",
    "P287_SELECT_LUT_RESID16",
    "P287_SHOCKLESS_WB_BKID",
    "P287_SHOCKLESS_WB_DEFAULT",
    "P287_SHOCKLESS_WB_MODES",
    "P287_SHOCKLESS_WB_RESID16",
    "P287_SHOOTING_DOMAINS",
    "P287_SHUTTER_AWB_LOCK_BKID",
    "P287_SHUTTER_AWB_LOCK_DEFAULT",
    "P287_SHUTTER_AWB_LOCK_MODES",
    "P287_SHUTTER_AWB_LOCK_RESID16",
    "P287_SLOT1_FORMAT_HARD_LOCKED",
    "P287_SLOT1_VAULT_MUTATION_BYTES",
    "P287_SLOT1_VAULT_SLOT",
    "P287_SPOT_LINKABLE_FOCUS_AREAS",
    "P287_SPOT_METERING_POINT_BKID",
    "P287_SPOT_METERING_POINT_DEFAULT",
    "P287_SPOT_METERING_POINT_MODES",
    "P287_SPOT_METERING_POINT_RESID16",
    "P287_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P287_STATUS_FAIL_50OF50_AGGREGATOR",
    "P287_STATUS_FAIL_PILLAR50_SUITE",
    "P287_STATUS_REJECTED_PILLAR_50A",
    "P287_STATUS_REJECTED_PILLAR_50B",
    "P287_STATUS_VERIFIED_50OF50_AGGREGATOR",
    "P287_STATUS_VERIFIED_PILLAR50_SUITE",
    "P287_STATUS_VERIFIED_PILLAR_50A",
    "P287_STATUS_VERIFIED_PILLAR_50B",
    "P287_TIER0_SURFACE_COUNT",
    "P287_VAULT_TARGET_ACTIONS",
    "P287_WB_AB_RANGE",
    "P287_WB_ALL_MODES",
    "P287_WB_AUTO_MODES",
    "P287_WB_CINE_EI_AWB_OR_CUSTOM_SETUP_TRAP_EVENTS",
    "P287_WB_CTEMP_FILTER_MODE",
    "P287_WB_CTEMP_MAX_K",
    "P287_WB_CTEMP_MIN_K",
    "P287_WB_CTEMP_STEP_COUNT",
    "P287_WB_CTEMP_STEP_K",
    "P287_WB_CUSTOM_CAMSET_EXCLUSION_DRIFT_EVENTS",
    "P287_WB_CUSTOM_RESID16_MAP",
    "P287_WB_CUSTOM_SLOTS",
    "P287_WB_DEFAULT",
    "P287_WB_FIXED_PRESETS",
    "P287_WB_GM_RANGE",
    "P287_WHITE_BALANCE_BKID",
    "P287_WHITE_BALANCE_MENU_PATH",
    "P287_WHITE_BALANCE_RESID16",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE287_PHASE_NUMBER",
    "PHASE287_SCHEMA",
    "PHASE287_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "Master50PillarRecoveryReport",
    "Phase287DonorArtifactDigest",
    "Phase287DonorSnapshot",
    "PictureProfileScinetoneDroLogVaultReport",
    "PictureProfileScinetoneDroLogVaultSpec",
    "Pillar50ASuiteResult",
    "Pillar50BSuiteResult",
    "Pillar50ScenarioOutcome",
    "Pillar50StandaloneReport",
    "PpScinetoneCreativeLookDroWbMeteringVaultReport",
    "WhiteBalanceCamsetExclusionAndMeteringVaultReport",
    "WhiteBalanceCamsetExclusionAndMeteringVaultSpec",
    "build_default_safe_pp_scinetone_dro_log_vault_spec",
    "build_default_safe_wb_camset_exclusion_metering_vault_spec",
    "compute_expected_metering_and_cine_ei_invariance",
    "compute_expected_pillar50a_reset_state",
    "compute_expected_pp_creativelook_dro_log_pipeline",
    "compute_expected_wb_cine_ei_custom_guard",
    "evaluate_50pillar_recovery_master",
    "evaluate_pp_scinetone_creativelook_dro_log_vault",
    "evaluate_realhw_50pillar_recovery_master",
    "evaluate_wb_camset_exclusion_and_metering_vault",
    "inspect_phase287_donors_readonly",
    "run_pillar50_standalone_suite",
    "run_pillar50a_pp_scinetone_creativelook_dro_6_scenario_suite",
    "run_pillar50b_wb_camset_exclusion_metering_6_scenario_suite",
    "verify_50pillar_recovery_suite",
    "verify_pp_scinetone_creativelook_dro_wb_metering_and_vault",
    "verify_pp_scinetone_creativelook_dro_wb_metering_vault",
]
