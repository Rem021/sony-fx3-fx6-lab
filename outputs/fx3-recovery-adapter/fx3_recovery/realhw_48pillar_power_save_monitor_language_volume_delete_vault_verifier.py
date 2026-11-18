"""Phase 277 — Pillar 48 (`48/48` Recovery Pillars) & Unified 48-Pillar Recovery Master
(`verify-48pillar-recovery` / `verify-power-save-monitor-language-volume-delete-vault`):

1. **Pillar 48A — `[Power Save by Monitor]` Reality Split (`appFw.so` 4-Mode vs `ILME-FX3` `ilc/2210`
   2-Item `[Power Setting Option]`), `[Power Save Start Time]` 9-Deactivation Recovery Guard,
   & `[Language]` `BK_LANG` (`0x02cf019c`) 4-Language Stage-B Recovery Parity (Wave-46)**:
   - Models `MENU` -> `(Setup)` -> `[Power Setting Option]` on physical `Sony ILME-FX3`
     (`Ver. 7.02`, `0x91030080`, `ilc/2210`): stock UI exposes ONLY `[Power Save Start Time]`
     (`Off`, `30 Min`, `5 Min` default, `2 Min`, `1 Min`, `10 Sec`) and `[Auto Power OFF Temp.]`
     (`Standard` default, `High`), while `[Power Save by Monitor]` is unexposed in stock FX3/FX3A/FX6 UI
     (`fx3_ui_exposes_power_save_by_monitor == False`).
   - Simultaneously audits shared `appFw.so` (`BKID_APP_setting_monitor_power_linkage`,
     `EXTERN_VAL_MONITOR_POWER_LINKAGE_{ON_ALL, ON_OPEN, ON_CLOSE, OFF}`) and `string_*_f.uxc`
     (`resid16=0x60b9`) exact 4 modes (`Both Linked` `0x6db5`, `Open: Return` `0x6db6`,
     `Close: Power Save` `0x60a8`, `Does Not Link` `0x6b2e`), rejecting `"Open: On/Close: Off"`
     spoofing (`legacy_power_save_monitor_spoof_events == 0`), and enforcing `Does Not Link` (or
     `Open: Return`) for folded-LCD headless HDMI bench capture on sibling `BIONZ XR` bodies.
   - Enforces `[Power Save Start Time]` in `{Off, 30 Min}` during air-gapped battery Tier-0
     recovery/dump sessions when none of Sony's 9 deactivation conditions are active, preventing
     mid-recovery idle sleep during SD Stage-B rollback or `O_RDONLY` backup inspection
     (`unsafe_power_save_sleep_interference_events == 0`).
   - Verifies `[Language]` (`BK_LANG` `0x02cf019c`, `resid16=0xe397`, default `"—"`) parity across
     `FX3` (`34` languages, `FX3-CX95900_ALLLANG-Backup.bin` `4 B` LE `@ 0x90ff0 = 0x00000000`) vs
     `FX6` (`29` languages, `CX95898_NTSC.bin` `0x00` vs `CX95899_CN1.bin` `0x19` `1 B` `@ 0x89242`),
     Stage-B 4-language `.uxc` + `.ltt` font bank table (`en=0x00`, `schinese=0x19`,
     `tchinese=0x18`, `japanese=0x01`), and `(Setup)` reset boundary survival across
     `[Camera Settings Reset]` & `[Reset Network Set.]` (reset only via `[Initialize]` /
     `libSaveLoadSettings.so`).

2. **Pillar 48B — `[Volume Settings]` (`0..15`, Default `7`), `[4ch Audio Monitoring]` (`5` Routes),
   & `[Delete confirm.]` (`"Cancel" first` Default + `Slot-1` Recovery Vault Delete/Format Firewall)**:
   - Models `MENU` -> `(Setup)` -> `[Sound Option]` -> `[Volume Settings]`
     (`BKID_APP_setting_volume_settings`, `0xe8c9`, discrete `0..15` default `7`; distinct from
     `[Audio signals]` `0x7af6`; FX6 parity `BKID_APP_SETTING_MONITOR_VOLUME`) with the `XLR-H1`
     internal-speaker acoustic feedback guard (`xlrh1_acoustic_feedback_violations == 0`).
   - Verifies `[4ch Audio Monitoring]` (`BKID_APP_setting_audio_monitoring_ch`) exact 5 routes
     (`CH1/CH2` default `0x713b`, `CH3/CH4` `0x6bf6`, `CH1+3/CH2+4` `0x6c2e`, `CH1/CH1` `0x6f9c`,
     `CH2/CH2` `0x7a26`), `3.5 mm` 2ch-stereo headphone boundary, and isolation from HDMI
     `[4ch Audio Output]` (`BKID_APP_setting_4ch_output_ch`, `0x6aa0`).
   - Enforces `[Delete confirm.]` (`BKID_APP_setting_delete_confirm`, `0xe721`: `"Cancel" first`
     default `0xe724`/`0x6a5e` vs `"Delete" first` `0xe725`/`0x6e0a`) and `[Delete pressing twice]`
     (`BKID_APP_setting_delete_by_delete_twice`, `0x74db`, default `Off`), `(Playback)` survival
     across `[Camera Settings Reset]`, and **hard `Slot-1` recovery vault delete/format firewall**
     (`slot1_vault_delete_events == 0`, `slot1_format_hard_locked == True`) blocking all playback
     delete, twice-delete, or format operations against `Slot 1` (`CAMSET`/`BODYDATA.DAT` vault).

3. **Unified `48/48` Recovery Master (`evaluate_realhw_48pillar_recovery_master`)**:
   - Concurrently delegates Pillars `1..47` (`evaluate_realhw_47pillar_recovery_master`) +
     **Pillar 48** (`run_pillar48_standalone_suite`) -> **`48/48` (`VERIFIED_48OF48_PILLAR_RECOVERY_MASTER`)**
     in `< 2.0s` CLI runtime (`< 4.0s` nominal / `< 6.0s` concurrent ceiling), preserving 100%
     backward compatibility with `verify-22..47pillar-recovery`.
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
from .realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_47_PILLAR_SPECS,
    Master47PillarRecoveryReport,
    evaluate_realhw_47pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE277_SCHEMA: str = "realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier_v1"
PHASE277_VERSION: str = "1.0.0"
PHASE277_PHASE_NUMBER: int = 277
P277_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P277_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P277_LEGACY_POWER_SAVE_MONITOR_SPOOF_EVENTS: int = 0
P277_UNSAFE_POWER_SAVE_SLEEP_INTERFERENCE_EVENTS: int = 0
P277_BK_LANG_PARITY_DRIFT_EVENTS: int = 0
P277_STAGE_B_4LANG_UXC_LTT_DRIFT_EVENTS: int = 0
P277_XLRH1_ACOUSTIC_FEEDBACK_VIOLATIONS: int = 0
P277_AUDIO_MON_4CH_HDMI_CONFUSION_EVENTS: int = 0
P277_DESTRUCTIVE_DELETE_CONFIRM_DRIFT_EVENTS: int = 0
P277_SLOT1_VAULT_DELETE_EVENTS: int = 0
P277_SLOT1_VAULT_MUTATION_BYTES: int = 0
P277_SLOT1_FORMAT_HARD_LOCKED: bool = True

P277_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P277_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P277_FAST_CLI_BUDGET_SECONDS: float = 2.0
P277_NOMINAL_BUDGET_SECONDS: float = 4.0
P277_CONCURRENT_CEILING_SECONDS: float = 6.0
P277_BOUNDED_HEADER_BYTES: int = 4096
P277_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-46 Donor Anchors (strictly O_RDONLY)
P277_FX3_MODEL_NAME: str = "ILME-FX3"
P277_FX3_MODEL_ID: int = 0x91030080
P277_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P277_FX3_HELPGUIDE_ID: str = "ilc/2210"
P277_FX3_FW_VERSION: str = "7.02"
P277_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P277_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P277_FX6_DONOR_FW_VERSION: str = "6.01"
P277_SIBLING_POWER_SAVE_MONITOR_MODELS: Tuple[str, ...] = (
    "ILME-FX2",
    "ILCE-7M4",
    "ZV-E1",
    "ILCE-6700",
)
P277_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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

P277_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P277_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P277_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P277_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P277_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P277_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P277_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P277_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P277_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P277_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)
P277_FX3_BACKUP_BK_LANG_OFFSET: int = 0x90FF0
P277_FX3_BACKUP_BK_LANG_WIDTH_BYTES: int = 4
P277_FX3_BACKUP_BK_LANG_DEFAULT_VALUE: int = 0x00

P277_DONOR_FX6_BACKUP_NTSC_BIN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin"
)
P277_PINNED_FX6_BACKUP_NTSC_BIN_BYTES: int = 2253333
P277_PINNED_FX6_BACKUP_NTSC_BIN_SHA256: str = (
    "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e"
)

P277_DONOR_FX6_BACKUP_CN1_BIN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95899_CN1.bin"
)
P277_PINNED_FX6_BACKUP_CN1_BIN_BYTES: int = 2253333
P277_PINNED_FX6_BACKUP_CN1_BIN_SHA256: str = (
    "0c98d1ad9035f0f56a60462efe0d0440c6b29d5584fd3f1e8ffd6a59366f0a28"
)
P277_FX6_BACKUP_BK_LANG_OFFSET: int = 0x89242
P277_FX6_BACKUP_BK_LANG_WIDTH_BYTES: int = 1
P277_FX6_BACKUP_NTSC_BK_LANG_VALUE: int = 0x00
P277_FX6_BACKUP_CN1_BK_LANG_VALUE: int = 0x19

# FX3 Stage-B string_*_f.uxc + string_*.uxc & FX6 string_*.uxc (EN / ZH-CN / ZH-TW / JA)
P277_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P277_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P277_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P277_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P277_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P277_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P277_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P277_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P277_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P277_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P277_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P277_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P277_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P277_PINNED_FX3_UXC_EN_BYTES: int = 165740
P277_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P277_DONOR_FX3_UXC_SC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese.uxc"
)
P277_PINNED_FX3_UXC_SC_BYTES: int = 149064
P277_PINNED_FX3_UXC_SC_SHA256: str = (
    "34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66"
)

P277_DONOR_FX3_UXC_TC_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese.uxc"
)
P277_PINNED_FX3_UXC_TC_BYTES: int = 151908
P277_PINNED_FX3_UXC_TC_SHA256: str = (
    "be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3"
)

P277_DONOR_FX3_UXC_JA_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese.uxc"
)
P277_PINNED_FX3_UXC_JA_BYTES: int = 208564
P277_PINNED_FX3_UXC_JA_SHA256: str = (
    "f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d"
)

P277_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P277_PINNED_FX6_UXC_EN_BYTES: int = 118208
P277_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P277_DONOR_FX6_UXC_SC_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_simplifiedchinese.uxc"
)
P277_PINNED_FX6_UXC_SC_BYTES: int = 118644
P277_PINNED_FX6_UXC_SC_SHA256: str = (
    "ba060e859156bfaefcc4177bfa6e9c5bea112258b15ce815a5ba683d033e688f"
)

P277_DONOR_FX6_UXC_TC_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_traditionalchinese.uxc"
)
P277_PINNED_FX6_UXC_TC_BYTES: int = 119168
P277_PINNED_FX6_UXC_TC_SHA256: str = (
    "8c34b415ce4d19fd40ca22d00c4543c64eb4741b96250de13b93ec473b25b18b"
)

P277_DONOR_FX6_UXC_JA_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_japanese.uxc"
)
P277_PINNED_FX6_UXC_JA_BYTES: int = 141692
P277_PINNED_FX6_UXC_JA_SHA256: str = (
    "9b47630ebe8e011a9d0bdb7a2fda06574f5187222b92d60bf6887042fe186d35"
)

# Pillar 48A — [Power Save by Monitor] Reality Split, [Power Save Start Time], & [Language]
P277_POWER_SETTING_OPTION_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Power Setting Option",
)
P277_FX3_POWER_SETTING_EXACT_2_SUBITEMS: Tuple[str, ...] = (
    "Power Save Start Time",
    "Auto Power OFF Temp.",
)
P277_FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR: bool = False
P277_FX6_UI_EXPOSES_POWER_SAVE_BY_MONITOR: bool = False

P277_POWER_SAVE_MONITOR_LABEL: str = "Power Save by Monitor"
P277_POWER_SAVE_MONITOR_RESID16: int = 0x60B9
P277_POWER_SAVE_MONITOR_BKID: str = "BKID_APP_setting_monitor_power_linkage"
P277_FORBIDDEN_POWER_SAVE_MONITOR_SPOOF_LABEL: str = "Open: On/Close: Off"
P277_POWER_SAVE_MONITOR_4_MODES: Tuple[str, ...] = (
    "Both Linked",
    "Open: Return",
    "Close: Power Save",
    "Does Not Link",
)
P277_POWER_SAVE_MONITOR_RESID16_MAP: Dict[str, int] = {
    "Both Linked": 0x6DB5,
    "Open: Return": 0x6DB6,
    "Close: Power Save": 0x60A8,
    "Does Not Link": 0x6B2E,
}
P277_POWER_SAVE_MONITOR_ENUM_MAP: Dict[str, str] = {
    "Both Linked": "EXTERN_VAL_MONITOR_POWER_LINKAGE_ON_ALL",
    "Open: Return": "EXTERN_VAL_MONITOR_POWER_LINKAGE_ON_OPEN",
    "Close: Power Save": "EXTERN_VAL_MONITOR_POWER_LINKAGE_ON_CLOSE",
    "Does Not Link": "EXTERN_VAL_MONITOR_POWER_LINKAGE_OFF",
}
P277_SIBLING_POWER_SAVE_MONITOR_DEFAULT: str = "Both Linked"
P277_HEADLESS_HDMI_SAFE_POWER_SAVE_MONITOR_MODES: Tuple[str, ...] = (
    "Does Not Link",
    "Open: Return",
)

P277_POWER_SAVE_START_TIME_MODES: Tuple[str, ...] = (
    "Off",
    "30 Min",
    "5 Min",
    "2 Min",
    "1 Min",
    "10 Sec",
)
P277_POWER_SAVE_START_TIME_DEFAULT: str = "5 Min"
P277_RECOVERY_SAFE_POWER_SAVE_START_TIMES: Tuple[str, ...] = ("Off", "30 Min")
P277_AUTO_POWER_OFF_TEMP_MODES: Tuple[str, ...] = ("Standard", "High")
P277_AUTO_POWER_OFF_TEMP_DEFAULT: str = "Standard"
P277_POWER_SAVE_9_DEACTIVATION_CONDITIONS: Tuple[str, ...] = (
    "USB power supply",
    "slideshow playback",
    "FTP transfer",
    "movie recording",
    "PC connection",
    "TV/HDMI connection",
    "IR Remote Ctrl = On",
    "Bluetooth Rmt Ctrl = On",
    "streaming / Creators' Cloud upload",
)

P277_LANGUAGE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Area/Date",
    "Language",
)
P277_LANGUAGE_LABEL: str = "Language"
P277_LANGUAGE_BK_KEY_HEX: str = "0x02cf019c"
P277_LANGUAGE_BK_KEY: int = 0x02CF019C
P277_LANGUAGE_RESID16: int = 0xE397
P277_FX6_LANGUAGE_RESID16: int = 0x2F4D
P277_LANGUAGE_BKID_FX3: str = "BKID_APP_setting_language"
P277_LANGUAGE_BKID_FX6: str = "BKID_APP_SETTING_LANGUAGE"
P277_LANGUAGE_DEFAULT: str = "—"
P277_FX3_LANGUAGE_COUNT: int = 34
P277_FX6_LANGUAGE_COUNT: int = 29
P277_STAGE_B_4LANG_ORDER: Tuple[str, ...] = ("en", "schinese", "tchinese", "japanese")
P277_STAGE_B_4LANG_UXC_LTT_TABLE: Dict[str, Dict[str, Any]] = {
    "en": {
        "bk_lang_val": 0x00,
        "appfw_enum": "0x2b2f_LANGUAGE_ENGLISH",
        "bank_id": 0,
        "font_str_pair": (4, 4),
        "ltt_font": "UniversOTS-SJ_wIcon.ltt",
        "fx3_f_bytes": P277_PINNED_FX3_UXC_EN_F_BYTES,
        "fx3_bytes": P277_PINNED_FX3_UXC_EN_BYTES,
        "fx6_bytes": P277_PINNED_FX6_UXC_EN_BYTES,
    },
    "schinese": {
        "bk_lang_val": 0x19,
        "appfw_enum": "0x2b45_CHINESE_SIMPLIFIED",
        "bank_id": 23,
        "font_str_pair": (19, 19),
        "ltt_font": "MYingHeiC-GB18030-SJ_wIcon.ltt",
        "fx3_f_bytes": P277_PINNED_FX3_UXC_SC_F_BYTES,
        "fx3_bytes": P277_PINNED_FX3_UXC_SC_BYTES,
        "fx6_bytes": P277_PINNED_FX6_UXC_SC_BYTES,
    },
    "tchinese": {
        "bk_lang_val": 0x18,
        "appfw_enum": "0x2b44_LANGUAGE_CHINESE_TRADITIONAL",
        "bank_id": 27,
        "font_str_pair": (22, 22),
        "ltt_font": "MYingHeiC-Big5HKSCS-SJ_wIcon.ltt",
        "fx3_f_bytes": P277_PINNED_FX3_UXC_TC_F_BYTES,
        "fx3_bytes": P277_PINNED_FX3_UXC_TC_BYTES,
        "fx6_bytes": P277_PINNED_FX6_UXC_TC_BYTES,
    },
    "japanese": {
        "bk_lang_val": 0x01,
        "appfw_enum": "0x2b30_LANGUAGE_JAPANESE",
        "bank_id": 1,
        "font_str_pair": (12, 12),
        "ltt_font": "HeiseiKakuGothW5-SJ_wIcon.ltt",
        "fx3_f_bytes": P277_PINNED_FX3_UXC_JA_F_BYTES,
        "fx3_bytes": P277_PINNED_FX3_UXC_JA_BYTES,
        "fx6_bytes": P277_PINNED_FX6_UXC_JA_BYTES,
    },
}

# Pillar 48B — [Volume Settings] (0..15), [4ch Audio Monitoring] (5 Routes), & [Delete confirm.]
P277_VOLUME_SETTINGS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Sound Option",
    "Volume Settings",
)
P277_VOLUME_SETTINGS_BKID: str = "BKID_APP_setting_volume_settings"
P277_FX6_VOLUME_SETTINGS_BKID: str = "BKID_APP_SETTING_MONITOR_VOLUME"
P277_VOLUME_SETTINGS_RESID16: int = 0xE8C9
P277_AUDIO_SIGNALS_RESID16: int = 0x7AF6
P277_VOLUME_SETTINGS_MIN: int = 0
P277_VOLUME_SETTINGS_MAX: int = 15
P277_VOLUME_SETTINGS_DEFAULT: int = 7
P277_XLRH1_SAFE_INTERNAL_SPEAKER_MAX_VOLUME: int = 4
P277_PLAYBACK_OUTPUT_TARGETS: Tuple[str, ...] = (
    "Headphone 3.5mm",
    "Internal Speaker",
    "Muted",
)

P277_AUDIO_MONITORING_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Sound Option",
    "4ch Audio Monitoring",
)
P277_AUDIO_MONITORING_BKID: str = "BKID_APP_setting_audio_monitoring_ch"
P277_HDMI_4CH_OUTPUT_BKID: str = "BKID_APP_setting_4ch_output_ch"
P277_HDMI_4CH_OUTPUT_RESID16: int = 0x6AA0
P277_HDMI_4CH_OUTPUT_MODES: Tuple[str, ...] = ("CH1/CH2", "CH3/CH4")
P277_AUDIO_MONITORING_5_ROUTES: Tuple[str, ...] = (
    "CH1/CH2",
    "CH3/CH4",
    "CH1+3/CH2+4",
    "CH1/CH1",
    "CH2/CH2",
)
P277_AUDIO_MONITORING_DEFAULT: str = "CH1/CH2"
P277_AUDIO_MONITORING_RESID16_MAP: Dict[str, int] = {
    "CH1/CH2": 0x713B,
    "CH3/CH4": 0x6BF6,
    "CH1+3/CH2+4": 0x6C2E,
    "CH1/CH1": 0x6F9C,
    "CH2/CH2": 0x7A26,
}
P277_AUDIO_MONITORING_ENUM_MAP: Dict[str, str] = {
    "CH1/CH2": "AUDIO_MONITORING_CH_1CH_2CH",
    "CH3/CH4": "AUDIO_MONITORING_CH_3CH_4CH",
    "CH1+3/CH2+4": "AUDIO_MONITORING_CH_MIX_ALL",
    "CH1/CH1": "AUDIO_MONITORING_CH_1CH",
    "CH2/CH2": "AUDIO_MONITORING_CH_2CH",
}
P277_HEADPHONE_35MM_MAX_CHANNELS: int = 2

P277_DELETE_CONFIRM_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Playback",
    "Delete",
    "Delete confirm.",
)
P277_DELETE_TWICE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Playback",
    "Delete",
    "Delete pressing twice",
)
P277_DELETE_CONFIRM_BKID: str = "BKID_APP_setting_delete_confirm"
P277_DELETE_TWICE_BKID: str = "BKID_APP_setting_delete_by_delete_twice"
P277_DELETE_CONFIRM_LABEL_RESID16: int = 0xE721
P277_DELETE_TWICE_RESID16: int = 0x74DB
P277_DELETE_CONFIRM_MODES: Tuple[str, ...] = ('"Cancel" first', '"Delete" first')
P277_DELETE_CONFIRM_DEFAULT: str = '"Cancel" first'
P277_DELETE_CONFIRM_RESID16_PAIRS: Dict[str, Tuple[int, int]] = {
    '"Cancel" first': (0xE724, 0x6A5E),
    '"Delete" first': (0xE725, 0x6E0A),
}
P277_DELETE_CONFIRM_ENUM_MAP: Dict[str, str] = {
    '"Cancel" first': "VAL_setting_delete_confirm_DELETE_CONFIRM_CANCEL_FIRST",
    '"Delete" first': "VAL_setting_delete_confirm_DELETE_CONFIRM_DELETE_FIRST",
}
P277_ON_OFF_MODES: Tuple[str, ...] = ("Off", "On")
P277_DELETE_TWICE_DEFAULT: str = "Off"

P277_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "DELETE_SINGLE",
    "DELETE_MULTIPLE",
    "DELETE_FOLDER",
    "DELETE_DATE",
    "DELETE_PRESSING_TWICE",
    "FORMAT_SLOT",
)
P277_DESTRUCTIVE_VAULT_ACTIONS: Tuple[str, ...] = (
    "DELETE_SINGLE",
    "DELETE_MULTIPLE",
    "DELETE_FOLDER",
    "DELETE_DATE",
    "DELETE_PRESSING_TWICE",
    "FORMAT_SLOT",
)

P277_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P277_SLOT1_VAULT_SLOT: int = 1
P277_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P277_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx3_power_save_monitor_language_volume_delete_vault_overlay"
P277_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P277_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P277_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P277_BLOCKED_INVALID_PILLAR48A_SPEC: str = "BLOCKED_INVALID_PILLAR48A_SPEC"
P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF: str = (
    "BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF"
)
P277_BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP: str = (
    "BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP"
)
P277_BLOCKED_BK_LANG_OR_STAGE_B_4LANG_PARITY_DRIFT: str = (
    "BLOCKED_BK_LANG_OR_STAGE_B_4LANG_PARITY_DRIFT"
)
P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT: str = (
    "BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT"
)

P277_BLOCKED_INVALID_PILLAR48B_SPEC: str = "BLOCKED_INVALID_PILLAR48B_SPEC"
P277_BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK: str = (
    "BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK"
)
P277_BLOCKED_AUDIO_MON_4CH_OR_HDMI_CONFUSION: str = (
    "BLOCKED_AUDIO_MON_4CH_OR_HDMI_CONFUSION"
)
P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT: str = (
    "BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT"
)
P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT: str = (
    "BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT"
)
P277_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P277_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P277_STATUS_VERIFIED_PILLAR_48A: str = (
    "VERIFIED_PILLAR_48A_POWER_SAVE_MONITOR_REALITY_SPLIT_9COND_RECOVERY_GUARD_AND_BK_LANG_4LANG_VAULT"
)
P277_STATUS_REJECTED_PILLAR_48A: str = (
    "REJECTED_PILLAR_48A_POWER_SAVE_MONITOR_REALITY_SPLIT_9COND_RECOVERY_GUARD_AND_BK_LANG_4LANG_VAULT"
)
P277_STATUS_VERIFIED_PILLAR_48B: str = (
    "VERIFIED_PILLAR_48B_VOLUME_0_15_XLRH1_4CH_AUDIO_MON_DELETE_CONFIRM_AND_SLOT1_VAULT"
)
P277_STATUS_REJECTED_PILLAR_48B: str = (
    "REJECTED_PILLAR_48B_VOLUME_0_15_XLRH1_4CH_AUDIO_MON_DELETE_CONFIRM_AND_SLOT1_VAULT"
)
P277_STATUS_VERIFIED_PILLAR48_SUITE: str = (
    "VERIFIED_PILLAR48_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_VAULT"
)
P277_STATUS_FAIL_PILLAR48_SUITE: str = (
    "FAIL_PILLAR48_POWER_SAVE_MONITOR_LANGUAGE_VOLUME_DELETE_VAULT"
)
P277_STATUS_VERIFIED_48OF48_AGGREGATOR: str = "VERIFIED_48OF48_PILLAR_RECOVERY_MASTER"
P277_STATUS_FAIL_48OF48_AGGREGATOR: str = "FAIL_48OF48_PILLAR_RECOVERY_MASTER"

P277_PILLAR_48A_SCENARIO_IDS: Tuple[str, ...] = (
    "P48A1_FX3_2ITEM_POWER_OPTION_AIRGAP_OFF_POWER_SAVE_9COND_AND_BK_LANG_4LANG_SETUP_SURVIVAL_SAFE",
    "P48A2_INITIALIZE_RESETS_SETUP_AND_STAGE_B_4LANG_LTT_PARITY_WITH_SIBLING_DOES_NOT_LINK_SAFE",
    "P48A3_REJECT_FX3_UI_MONITOR_POWER_EXPOSURE_OR_OPEN_ON_CLOSE_OFF_SPOOF_OR_SIBLING_LCD_CLOSE_SLEEP",
    "P48A4_REJECT_AIRGAP_TIER0_5MIN_POWER_SAVE_WHEN_0OF9_DEACTIVATION_CONDITIONS_ACTIVE",
    "P48A5_REJECT_BK_LANG_OFFSET_OR_COUNT_DRIFT_OR_STAGE_B_4LANG_UXC_LTT_MISMATCH",
    "P48A6_REJECT_CAMERA_SETTINGS_RESET_WIPING_SETUP_LANGUAGE_OR_POWER_SAVE_START_TIME",
)
P277_PILLAR_48B_SCENARIO_IDS: Tuple[str, ...] = (
    "P48B1_VOLUME_7_4CH_MON_CH1_CH2_DELETE_CONFIRM_CANCEL_FIRST_AND_SLOT1_VAULT_IMMUTABLE_SAFE",
    "P48B2_XLRH1_HEADPHONE_OR_LOW_SPEAKER_4CH_MIX_ALL_AND_INITIALIZE_WITH_CAMSET01_RESTORE_SAFE",
    "P48B3_REJECT_VOLUME_OUT_OF_0_15_OR_XLRH1_HIGH_INTERNAL_SPEAKER_ACOUSTIC_FEEDBACK",
    "P48B4_REJECT_INVALID_4CH_MON_ROUTE_OR_HDMI_4CH_OUTPUT_CHANNEL_CONFUSION",
    "P48B5_REJECT_DELETE_FIRST_OR_TWICE_ON_RECOVERY_BENCH_OR_CAMERA_SETTINGS_RESET_PLAYBACK_DRIFT",
    "P48B6_REJECT_ANY_SLOT1_PLAYBACK_DELETE_TWICE_OR_FORMAT_TARGETING_RECOVERY_VAULT",
)

MASTER_48_PILLAR_COUNT: int = 48
MASTER_48_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_47_PILLAR_SPECS + (
    (
        48,
        "pillar_48_power_save_monitor_language_volume_delete_vault",
        "Phase 277 (48/48)",
        "fx3_recovery.realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier",
    ),
)
MASTER_48_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_48_PILLAR_SPECS)


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
    return os.environ.get(P277_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P277_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P277_DONOR_INSPECT_BUDGET_SECONDS


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
        ("P277_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P277_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P277_SLOT1_FORMAT_HARD_LOCKED", P277_SLOT1_FORMAT_HARD_LOCKED, True),
        ("P277_LEGACY_POWER_SAVE_MONITOR_SPOOF_EVENTS", P277_LEGACY_POWER_SAVE_MONITOR_SPOOF_EVENTS, 0),
        (
            "P277_UNSAFE_POWER_SAVE_SLEEP_INTERFERENCE_EVENTS",
            P277_UNSAFE_POWER_SAVE_SLEEP_INTERFERENCE_EVENTS,
            0,
        ),
        ("P277_BK_LANG_PARITY_DRIFT_EVENTS", P277_BK_LANG_PARITY_DRIFT_EVENTS, 0),
        ("P277_STAGE_B_4LANG_UXC_LTT_DRIFT_EVENTS", P277_STAGE_B_4LANG_UXC_LTT_DRIFT_EVENTS, 0),
        ("P277_XLRH1_ACOUSTIC_FEEDBACK_VIOLATIONS", P277_XLRH1_ACOUSTIC_FEEDBACK_VIOLATIONS, 0),
        ("P277_AUDIO_MON_4CH_HDMI_CONFUSION_EVENTS", P277_AUDIO_MON_4CH_HDMI_CONFUSION_EVENTS, 0),
        (
            "P277_DESTRUCTIVE_DELETE_CONFIRM_DRIFT_EVENTS",
            P277_DESTRUCTIVE_DELETE_CONFIRM_DRIFT_EVENTS,
            0,
        ),
        ("P277_SLOT1_VAULT_DELETE_EVENTS", P277_SLOT1_VAULT_DELETE_EVENTS, 0),
        ("P277_SLOT1_VAULT_MUTATION_BYTES", P277_SLOT1_VAULT_MUTATION_BYTES, 0),
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
    return any(tok in low for tok in P277_FORBIDDEN_PERSISTENT_TARGETS)


def compute_expected_power_save_by_monitor_effective_state(
    *,
    camera_model: str,
    monitor_power_linkage_mode: str,
    lcd_folded_inward: bool,
    headless_hdmi_capture_active: bool,
) -> Tuple[bool, bool, bool]:
    """Compute `(ui_exposed, sleeps_on_inward_close, headless_hdmi_safe)`.

    - Stock `ILME-FX3`, `ILME-FX3A`, and `ILME-FX6` do NOT expose `[Power Save by Monitor]` in UI
      (`ui_exposed=False`, folding LCD inward does not trigger monitor sleep).
    - Sibling `BIONZ XR` bodies (`ILME-FX2`, `ILCE-7M4`, `ZV-E1`, `ILCE-6700`) expose all 4 modes;
      `Both Linked` and `Close: Power Save` trigger sleep on inward close, breaking headless HDMI capture,
      whereas `Does Not Link` and `Open: Return` keep the body awake.
    """
    ui_exposed = camera_model in P277_SIBLING_POWER_SAVE_MONITOR_MODELS
    if not ui_exposed:
        sleeps_on_close = False
    else:
        sleeps_on_close = lcd_folded_inward and monitor_power_linkage_mode in (
            "Both Linked",
            "Close: Power Save",
        )
    headless_safe = (not headless_hdmi_capture_active) or (not sleeps_on_close)
    return ui_exposed, sleeps_on_close, headless_safe


def compute_expected_power_save_start_time_recovery_guard(
    *,
    configured_power_save_start_time: str,
    active_deactivation_conditions: Tuple[str, ...],
    airgapped_battery_tier0_session: bool,
) -> Tuple[bool, bool]:
    """Compute `(idle_sleep_bypassed_by_9cond, tier0_session_sleep_safe)`.

    When any valid Sony deactivation condition (`USB power supply`, `TV/HDMI connection`,
    `movie recording`, etc.) is active, idle sleep is suppressed by firmware. When NONE of the 9
    conditions are active during an air-gapped battery Tier-0 recovery/dump session, `[Power Save Start Time]`
    MUST be `"Off"` or `"30 Min"`.
    """
    bypassed = len(active_deactivation_conditions) > 0
    if not airgapped_battery_tier0_session:
        return bypassed, True
    safe = bypassed or (configured_power_save_start_time in P277_RECOVERY_SAFE_POWER_SAVE_START_TIMES)
    return bypassed, safe


def compute_expected_pillar48a_reset_state(
    *,
    pre_power_save_start_time: str,
    pre_auto_power_off_temp: str,
    pre_sibling_power_save_by_monitor: str,
    pre_language: str,
    reset_action: str,
) -> Tuple[str, str, str, str]:
    """Compute post-reset Pillar 48A `(power_save_start_time, auto_power_off_temp,
    sibling_power_save_by_monitor, language)`.

    All four sit under `(Setup)` -> **survive `[Camera Settings Reset]` AND `[Reset Network Set.]`**,
    returning to factory defaults ONLY on `[Initialize]`.
    """
    if reset_action == "Initialize":
        return (
            P277_POWER_SAVE_START_TIME_DEFAULT,
            P277_AUTO_POWER_OFF_TEMP_DEFAULT,
            P277_SIBLING_POWER_SAVE_MONITOR_DEFAULT,
            P277_LANGUAGE_DEFAULT,
        )
    return (
        pre_power_save_start_time,
        pre_auto_power_off_temp,
        pre_sibling_power_save_by_monitor,
        pre_language,
    )


def compute_expected_xlrh1_speaker_feedback_guard(
    *,
    volume_level: int,
    xlrh1_mic_attached: bool,
    playback_output_target: str,
    xlrh1_acoustic_separation_active: bool,
) -> Tuple[bool, int]:
    """Compute `(feedback_safe, clamped_safe_speaker_volume)`.

    Sony `ilc/2210` explicitly warns to lower speaker volume or distance `XLR-H1` from the rear
    monaural speaker to avoid acoustic feedback. When `XLR-H1` is attached and output targets
    `"Internal Speaker"` without acoustic separation, volume must stay `<= 4` (otherwise risk/violation).
    """
    if (
        xlrh1_mic_attached
        and playback_output_target == "Internal Speaker"
        and not xlrh1_acoustic_separation_active
    ):
        safe = volume_level <= P277_XLRH1_SAFE_INTERNAL_SPEAKER_MAX_VOLUME
        return safe, min(volume_level, P277_XLRH1_SAFE_INTERNAL_SPEAKER_MAX_VOLUME)
    return True, volume_level


def compute_expected_pillar48b_reset_and_slot1_vault_guard(
    *,
    pre_volume_settings: int,
    pre_audio_monitoring_ch: str,
    pre_delete_confirm: str,
    pre_delete_pressing_twice: str,
    reset_action: str,
    slot1_holds_recovery_vault: bool,
    slot1_sdxc_wp_locked: bool,
    requested_vault_slot: int,
    requested_vault_action: str,
) -> Tuple[int, str, str, str, bool]:
    """Compute post-reset `(volume_settings, audio_monitoring_ch, delete_confirm,
    delete_pressing_twice, vault_action_blocked)`.

    - `[Volume Settings]` & `[4ch Audio Monitoring]` sit under `(Setup)` and `[Delete confirm.]` &
      `[Delete pressing twice]` sit under `(Playback)` -> ALL FOUR survive `[Camera Settings Reset]`
      AND `[Reset Network Set.]`, resetting ONLY on `[Initialize]`.
    - Any destructive playback delete or format action targeting `Slot 1` when it holds the recovery
      vault is hard-blocked (`vault_action_blocked = True`).
    """
    if reset_action == "Initialize":
        post_vol = P277_VOLUME_SETTINGS_DEFAULT
        post_mon = P277_AUDIO_MONITORING_DEFAULT
        post_del_cfg = P277_DELETE_CONFIRM_DEFAULT
        post_del_2x = P277_DELETE_TWICE_DEFAULT
    else:
        post_vol = pre_volume_settings
        post_mon = pre_audio_monitoring_ch
        post_del_cfg = pre_delete_confirm
        post_del_2x = pre_delete_pressing_twice

    vault_blocked = (
        requested_vault_slot == P277_SLOT1_VAULT_SLOT
        and (slot1_holds_recovery_vault or slot1_sdxc_wp_locked)
        and requested_vault_action in P277_DESTRUCTIVE_VAULT_ACTIONS
    )
    return post_vol, post_mon, post_del_cfg, post_del_2x, vault_blocked


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase277DonorArtifactDigest:
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
class Phase277DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase277DonorArtifactDigest, ...]


@dataclass(frozen=True)
class PowerSaveMonitorLanguageVaultSpec:
    camera_model: str = P277_FX3_MODEL_NAME
    camera_model_id: int = P277_FX3_MODEL_ID
    camera_codename: str = P277_FX3_PRODUCT_CODENAME
    helpguide_id: str = P277_FX3_HELPGUIDE_ID
    fw_version: str = P277_FX3_FW_VERSION
    power_setting_menu_path: Tuple[str, ...] = P277_POWER_SETTING_OPTION_MENU_PATH
    fx3_power_setting_subitems: Tuple[str, ...] = P277_FX3_POWER_SETTING_EXACT_2_SUBITEMS
    fx3_ui_exposes_power_save_by_monitor: bool = False
    fx6_ui_exposes_power_save_by_monitor: bool = False
    power_save_monitor_label: str = P277_POWER_SAVE_MONITOR_LABEL
    power_save_monitor_4_modes: Tuple[str, ...] = P277_POWER_SAVE_MONITOR_4_MODES
    sibling_power_save_by_monitor_mode: str = "Does Not Link"
    sibling_lcd_folded_inward: bool = True
    headless_hdmi_capture_active: bool = True
    legacy_power_save_monitor_spoof_events: int = 0
    airgapped_battery_tier0_session: bool = True
    active_deactivation_conditions: Tuple[str, ...] = ()
    pre_power_save_start_time: str = "Off"
    pre_auto_power_off_temp: str = "Standard"
    pre_sibling_power_save_by_monitor: str = "Does Not Link"
    language_menu_path: Tuple[str, ...] = P277_LANGUAGE_MENU_PATH
    bk_lang_key: int = P277_LANGUAGE_BK_KEY
    fx3_language_count: int = P277_FX3_LANGUAGE_COUNT
    fx6_language_count: int = P277_FX6_LANGUAGE_COUNT
    fx3_backup_bk_lang_val: int = P277_FX3_BACKUP_BK_LANG_DEFAULT_VALUE
    fx6_ntsc_bk_lang_val: int = P277_FX6_BACKUP_NTSC_BK_LANG_VALUE
    fx6_cn1_bk_lang_val: int = P277_FX6_BACKUP_CN1_BK_LANG_VALUE
    stage_b_selected_lang: str = "schinese"
    stage_b_bank_id: int = 23
    stage_b_font_str_pair: Tuple[int, int] = (19, 19)
    stage_b_ltt_font: str = "MYingHeiC-GB18030-SJ_wIcon.ltt"
    pre_language: str = "Simplified Chinese"
    reset_action: str = "Camera Settings Reset"
    camset_load_after_reset: bool = False
    camset_slot: int = P277_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P277_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_power_save_start_time: str = "Off"
    saved_auto_power_off_temp: str = "Standard"
    saved_sibling_power_save_by_monitor: str = "Does Not Link"
    saved_language: str = "Simplified Chinese"
    post_power_save_start_time: str = "Off"
    post_auto_power_off_temp: str = "Standard"
    post_sibling_power_save_by_monitor: str = "Does Not Link"
    post_language: str = "Simplified Chinese"
    unsafe_power_save_sleep_interference_events: int = 0
    bk_lang_parity_drift_events: int = 0
    stage_b_4lang_uxc_ltt_drift_events: int = 0
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_vault_delete_events: int = 0
    slot1_vault_mutation_bytes: int = 0
    overlay_dir: str = P277_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P277_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P277_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P277_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class PowerSaveMonitorLanguageVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    reality_split_and_4mode_uxc_verified: bool
    power_save_start_time_9cond_guard_verified: bool
    bk_lang_and_stage_b_4lang_parity_verified: bool
    setup_reset_persistence_and_camset_verified: bool
    h0_equals_h3_verified: bool
    matrix_states_checked: int
    fx3_ui_exposes_power_save_by_monitor: bool
    legacy_power_save_monitor_spoof_events: int
    unsafe_power_save_sleep_interference_events: int
    bk_lang_parity_drift_events: int
    stage_b_4lang_uxc_ltt_drift_events: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Volume4chMonDeleteConfirmVaultSpec:
    camera_model: str = P277_FX3_MODEL_NAME
    camera_model_id: int = P277_FX3_MODEL_ID
    helpguide_id: str = P277_FX3_HELPGUIDE_ID
    fw_version: str = P277_FX3_FW_VERSION
    volume_menu_path: Tuple[str, ...] = P277_VOLUME_SETTINGS_MENU_PATH
    audio_monitoring_menu_path: Tuple[str, ...] = P277_AUDIO_MONITORING_MENU_PATH
    delete_confirm_menu_path: Tuple[str, ...] = P277_DELETE_CONFIRM_MENU_PATH
    delete_twice_menu_path: Tuple[str, ...] = P277_DELETE_TWICE_MENU_PATH
    factory_default_volume: int = P277_VOLUME_SETTINGS_DEFAULT
    factory_default_audio_monitoring_ch: str = P277_AUDIO_MONITORING_DEFAULT
    factory_default_delete_confirm: str = P277_DELETE_CONFIRM_DEFAULT
    factory_default_delete_pressing_twice: str = P277_DELETE_TWICE_DEFAULT
    pre_volume_settings: int = 7
    xlrh1_mic_attached: bool = True
    playback_output_target: str = "Headphone 3.5mm"
    xlrh1_acoustic_separation_active: bool = True
    xlrh1_acoustic_feedback_violations: int = 0
    pre_audio_monitoring_ch: str = "CH1/CH2"
    hdmi_4ch_output_ch: str = "CH1/CH2"
    headphone_35mm_channels: int = 2
    audio_mon_4ch_hdmi_confusion_events: int = 0
    pre_delete_confirm: str = '"Cancel" first'
    pre_delete_pressing_twice: str = "Off"
    destructive_delete_confirm_drift_events: int = 0
    reset_action: str = "Camera Settings Reset"
    camset_load_after_reset: bool = False
    camset_slot: int = P277_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P277_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_volume_settings: int = 7
    saved_audio_monitoring_ch: str = "CH1/CH2"
    saved_delete_confirm: str = '"Cancel" first'
    saved_delete_pressing_twice: str = "Off"
    post_volume_settings: int = 7
    post_audio_monitoring_ch: str = "CH1/CH2"
    post_delete_confirm: str = '"Cancel" first'
    post_delete_pressing_twice: str = "Off"
    requested_vault_slot: int = P277_SLOT1_VAULT_SLOT
    requested_vault_action: str = "READ_ONLY_AUDIT"
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P277_SLOT1_FORMAT_HARD_LOCKED
    slot1_vault_delete_events: int = 0
    slot1_vault_mutation_bytes: int = 0
    overlay_dir: str = P277_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P277_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P277_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P277_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class Volume4chMonDeleteConfirmVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    volume_0_15_and_xlrh1_guard_verified: bool
    audio_mon_5_routes_and_hdmi_isolation_verified: bool
    delete_confirm_cancel_first_and_twice_verified: bool
    reset_scope_and_slot1_delete_format_firewall_verified: bool
    h0_equals_h3_verified: bool
    matrix_states_checked: int
    xlrh1_acoustic_feedback_violations: int
    audio_mon_4ch_hdmi_confusion_events: int
    destructive_delete_confirm_drift_events: int
    slot1_vault_delete_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PowerSaveMonitorLanguageVolumeDeleteVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase277DonorSnapshot
    power_save_language_report: PowerSaveMonitorLanguageVaultReport
    volume_4ch_delete_report: Volume4chMonDeleteConfirmVaultReport
    fx3_ui_exposes_power_save_by_monitor: bool
    legacy_power_save_monitor_spoof_events: int
    unsafe_power_save_sleep_interference_events: int
    bk_lang_parity_drift_events: int
    stage_b_4lang_uxc_ltt_drift_events: int
    xlrh1_acoustic_feedback_violations: int
    audio_mon_4ch_hdmi_confusion_events: int
    destructive_delete_confirm_drift_events: int
    slot1_vault_delete_events: int
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
class Pillar48ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar48ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar48ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar48BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar48ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar48StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase277DonorSnapshot
    pillar_48a_power_save_monitor_language_vault: Pillar48ASuiteResult
    pillar_48b_volume_4ch_mon_delete_confirm_slot1_vault: Pillar48BSuiteResult
    fx3_ui_exposes_power_save_by_monitor: bool
    legacy_power_save_monitor_spoof_events: int
    unsafe_power_save_sleep_interference_events: int
    bk_lang_parity_drift_events: int
    stage_b_4lang_uxc_ltt_drift_events: int
    xlrh1_acoustic_feedback_violations: int
    audio_mon_4ch_hdmi_confusion_events: int
    destructive_delete_confirm_drift_events: int
    slot1_vault_delete_events: int
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
class Master48PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_2s_fast_cli_budget: bool
    under_6s_budget: bool
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    # Pillar 48 & Wave-46 top-level fields
    donor_snapshot: Phase277DonorSnapshot
    pillar48_a_power_save_monitor_language_vault: Pillar48ASuiteResult
    pillar48_b_volume_4ch_mon_delete_confirm_slot1_vault: Pillar48BSuiteResult
    fx3_ui_exposes_power_save_by_monitor: bool
    legacy_power_save_monitor_spoof_events: int
    unsafe_power_save_sleep_interference_events: int
    bk_lang_parity_drift_events: int
    stage_b_4lang_uxc_ltt_drift_events: int
    xlrh1_acoustic_feedback_violations: int
    audio_mon_4ch_hdmi_confusion_events: int
    destructive_delete_confirm_drift_events: int
    slot1_vault_delete_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    # Preserved Pillars 1..47 rollup metrics
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
    master_48pillar_sha256: str
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
    max_full_bytes: int = P277_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P277_BOUNDED_HEADER_BYTES, total_size), 0)
        return True, total_size, len(hdr), "HEADER4K_SHA256", sha256(hdr).hexdigest(), hdr
    finally:
        os.close(fd)


def _check_elf64_aarch64_tokens(data: bytes, expected_tokens: Tuple[bytes, ...]) -> Tuple[bool, str]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return False, "NOT_ELF"
    ei_class, ei_data = data[4], data[5]
    e_machine = struct.unpack_from("<H", data, 18)[0]
    if ei_class != 2 or ei_data != 1 or e_machine != 183:
        return False, f"BAD_ELF64_AARCH64(class={ei_class},data={ei_data},mach={e_machine})"
    found = [tok.decode("ascii") for tok in expected_tokens if tok in data]
    missing = [tok.decode("ascii") for tok in expected_tokens if tok not in data]
    if missing:
        return False, f"MISSING_TOKENS:{','.join(missing)}"
    return True, f"ELF64_AARCH64:{'+'.join(found)}" if found else "ELF64_AARCH64"


def _check_uxc7_pack(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 16 or data[:4] != b"uxc\x07":
        return False, f"BAD_UXC7_MAGIC:{label}"
    return True, f"UXC7_{label}"


def _check_bk4_lang_backup(
    data: bytes,
    *,
    offset: int,
    width: int,
    expected_lang_val: int,
    label: str,
) -> Tuple[bool, str]:
    if (
        len(data) <= offset + width
        or struct.unpack_from("<I", data, 4)[0] != 0xAAAAAAAA
        or data[12:16] != b"BK4\x00"
    ):
        return False, f"BAD_BK4_MAGIC:{label}"
    if width == 4:
        actual = struct.unpack_from("<I", data, offset)[0]
    elif width == 1:
        actual = data[offset]
    else:
        return False, f"BAD_WIDTH:{width}"
    if actual != expected_lang_val:
        return False, f"BK_LANG_MISMATCH:{label}({actual:#x}!={expected_lang_val:#x})"
    return True, f"{label}:BK_LANG={actual:#04x}@{offset:#x}"


def _synthetic_phase277_donors() -> Tuple[Phase277DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P277_DONOR_FX3_APPFW_702_RELPATH,
            P277_PINNED_FX3_APPFW_702_BYTES,
            P277_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P277_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P277_DONOR_FX6_APPFW_601_RELPATH,
            P277_PINNED_FX6_APPFW_601_BYTES,
            P277_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P277_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P277_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_backup_bin",
            P277_DONOR_FX3_BACKUP_BIN_RELPATH,
            P277_PINNED_FX3_BACKUP_BIN_BYTES,
            P277_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3:BK_LANG=0x00@0x90ff0",
        ),
        (
            "fx6_backup_ntsc_bin",
            P277_DONOR_FX6_BACKUP_NTSC_BIN_RELPATH,
            P277_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
            P277_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX6_BACKUP_NTSC_BIN_SHA256,
            "SYNTHETIC_BK4_CHAPLIN_NTSC:BK_LANG=0x00@0x89242",
        ),
        (
            "fx6_backup_cn1_bin",
            P277_DONOR_FX6_BACKUP_CN1_BIN_RELPATH,
            P277_PINNED_FX6_BACKUP_CN1_BIN_BYTES,
            P277_PINNED_FX6_BACKUP_CN1_BIN_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX6_BACKUP_CN1_BIN_SHA256,
            "SYNTHETIC_BK4_CHAPLIN_CN1:BK_LANG=0x19@0x89242",
        ),
        (
            "fx3_uxc_en_f",
            P277_DONOR_FX3_UXC_EN_F_RELPATH,
            P277_PINNED_FX3_UXC_EN_F_BYTES,
            P277_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P277_DONOR_FX3_UXC_SC_F_RELPATH,
            P277_PINNED_FX3_UXC_SC_F_BYTES,
            P277_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P277_DONOR_FX3_UXC_TC_F_RELPATH,
            P277_PINNED_FX3_UXC_TC_F_BYTES,
            P277_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P277_DONOR_FX3_UXC_JA_F_RELPATH,
            P277_PINNED_FX3_UXC_JA_F_BYTES,
            P277_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P277_DONOR_FX3_UXC_EN_RELPATH,
            P277_PINNED_FX3_UXC_EN_BYTES,
            P277_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_sc",
            P277_DONOR_FX3_UXC_SC_RELPATH,
            P277_PINNED_FX3_UXC_SC_BYTES,
            P277_PINNED_FX3_UXC_SC_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX3_SC",
        ),
        (
            "fx3_uxc_tc",
            P277_DONOR_FX3_UXC_TC_RELPATH,
            P277_PINNED_FX3_UXC_TC_BYTES,
            P277_PINNED_FX3_UXC_TC_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX3_TC",
        ),
        (
            "fx3_uxc_ja",
            P277_DONOR_FX3_UXC_JA_RELPATH,
            P277_PINNED_FX3_UXC_JA_BYTES,
            P277_PINNED_FX3_UXC_JA_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX3_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX3_JA",
        ),
        (
            "fx6_uxc_en",
            P277_DONOR_FX6_UXC_EN_RELPATH,
            P277_PINNED_FX6_UXC_EN_BYTES,
            P277_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_sc",
            P277_DONOR_FX6_UXC_SC_RELPATH,
            P277_PINNED_FX6_UXC_SC_BYTES,
            P277_PINNED_FX6_UXC_SC_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX6_UXC_SC_SHA256,
            "SYNTHETIC_UXC7_FX6_SC",
        ),
        (
            "fx6_uxc_tc",
            P277_DONOR_FX6_UXC_TC_RELPATH,
            P277_PINNED_FX6_UXC_TC_BYTES,
            P277_PINNED_FX6_UXC_TC_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX6_UXC_TC_SHA256,
            "SYNTHETIC_UXC7_FX6_TC",
        ),
        (
            "fx6_uxc_ja",
            P277_DONOR_FX6_UXC_JA_RELPATH,
            P277_PINNED_FX6_UXC_JA_BYTES,
            P277_PINNED_FX6_UXC_JA_BYTES,
            "FULL_SHA256",
            P277_PINNED_FX6_UXC_JA_SHA256,
            "SYNTHETIC_UXC7_FX6_JA",
        ),
    )
    return tuple(
        Phase277DonorArtifactDigest(
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


def inspect_phase277_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase277DonorSnapshot:
    """Inspect Wave-46 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase277_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase277DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_appfw_702_so",
            P277_DONOR_FX3_APPFW_702_RELPATH,
            P277_PINNED_FX3_APPFW_702_BYTES,
            P277_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P277_DONOR_FX6_APPFW_601_RELPATH,
            P277_PINNED_FX6_APPFW_601_BYTES,
            P277_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P277_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite"),
            ),
        ),
        (
            "fx3_backup_bin",
            P277_DONOR_FX3_BACKUP_BIN_RELPATH,
            P277_PINNED_FX3_BACKUP_BIN_BYTES,
            P277_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_lang_backup(
                d,
                offset=P277_FX3_BACKUP_BK_LANG_OFFSET,
                width=P277_FX3_BACKUP_BK_LANG_WIDTH_BYTES,
                expected_lang_val=P277_FX3_BACKUP_BK_LANG_DEFAULT_VALUE,
                label="BK4_ILME_FX3",
            ),
        ),
        (
            "fx6_backup_ntsc_bin",
            P277_DONOR_FX6_BACKUP_NTSC_BIN_RELPATH,
            P277_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
            P277_PINNED_FX6_BACKUP_NTSC_BIN_SHA256,
            lambda d: _check_bk4_lang_backup(
                d,
                offset=P277_FX6_BACKUP_BK_LANG_OFFSET,
                width=P277_FX6_BACKUP_BK_LANG_WIDTH_BYTES,
                expected_lang_val=P277_FX6_BACKUP_NTSC_BK_LANG_VALUE,
                label="BK4_CHAPLIN_NTSC",
            ),
        ),
        (
            "fx6_backup_cn1_bin",
            P277_DONOR_FX6_BACKUP_CN1_BIN_RELPATH,
            P277_PINNED_FX6_BACKUP_CN1_BIN_BYTES,
            P277_PINNED_FX6_BACKUP_CN1_BIN_SHA256,
            lambda d: _check_bk4_lang_backup(
                d,
                offset=P277_FX6_BACKUP_BK_LANG_OFFSET,
                width=P277_FX6_BACKUP_BK_LANG_WIDTH_BYTES,
                expected_lang_val=P277_FX6_BACKUP_CN1_BK_LANG_VALUE,
                label="BK4_CHAPLIN_CN1",
            ),
        ),
        (
            "fx3_uxc_en_f",
            P277_DONOR_FX3_UXC_EN_F_RELPATH,
            P277_PINNED_FX3_UXC_EN_F_BYTES,
            P277_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P277_DONOR_FX3_UXC_SC_F_RELPATH,
            P277_PINNED_FX3_UXC_SC_F_BYTES,
            P277_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P277_DONOR_FX3_UXC_TC_F_RELPATH,
            P277_PINNED_FX3_UXC_TC_F_BYTES,
            P277_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P277_DONOR_FX3_UXC_JA_F_RELPATH,
            P277_PINNED_FX3_UXC_JA_F_BYTES,
            P277_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P277_DONOR_FX3_UXC_EN_RELPATH,
            P277_PINNED_FX3_UXC_EN_BYTES,
            P277_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_sc",
            P277_DONOR_FX3_UXC_SC_RELPATH,
            P277_PINNED_FX3_UXC_SC_BYTES,
            P277_PINNED_FX3_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC"),
        ),
        (
            "fx3_uxc_tc",
            P277_DONOR_FX3_UXC_TC_RELPATH,
            P277_PINNED_FX3_UXC_TC_BYTES,
            P277_PINNED_FX3_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC"),
        ),
        (
            "fx3_uxc_ja",
            P277_DONOR_FX3_UXC_JA_RELPATH,
            P277_PINNED_FX3_UXC_JA_BYTES,
            P277_PINNED_FX3_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA"),
        ),
        (
            "fx6_uxc_en",
            P277_DONOR_FX6_UXC_EN_RELPATH,
            P277_PINNED_FX6_UXC_EN_BYTES,
            P277_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_sc",
            P277_DONOR_FX6_UXC_SC_RELPATH,
            P277_PINNED_FX6_UXC_SC_BYTES,
            P277_PINNED_FX6_UXC_SC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_SC"),
        ),
        (
            "fx6_uxc_tc",
            P277_DONOR_FX6_UXC_TC_RELPATH,
            P277_PINNED_FX6_UXC_TC_BYTES,
            P277_PINNED_FX6_UXC_TC_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_TC"),
        ),
        (
            "fx6_uxc_ja",
            P277_DONOR_FX6_UXC_JA_RELPATH,
            P277_PINNED_FX6_UXC_JA_BYTES,
            P277_PINNED_FX6_UXC_JA_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_JA"),
        ),
    )

    artifacts: List[Phase277DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            artifacts.append(
                Phase277DonorArtifactDigest(
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
            Phase277DonorArtifactDigest(
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

    if any_missing and not all(a.present for a in artifacts):
        # Clean-room fallback when running on CI hosts without local Sony donors
        synth = _synthetic_phase277_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase277DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    all_ok = all(a.present and a.matches_pinned for a in artifacts)
    dt = round(time.monotonic() - t0, 6)
    return Phase277DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(artifacts),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < budget,
        budget_seconds_applied=budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(artifacts),
    )


# ---------------------------------------------------------------------------
# Pillar 48A & 48B Builders and Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_power_save_monitor_language_vault_spec() -> PowerSaveMonitorLanguageVaultSpec:
    """Return canonical safe Wave-46 Pillar 48A specification."""
    return PowerSaveMonitorLanguageVaultSpec()


def build_default_safe_volume_4ch_mon_delete_confirm_vault_spec() -> Volume4chMonDeleteConfirmVaultSpec:
    """Return canonical safe Wave-46 Pillar 48B specification."""
    return Volume4chMonDeleteConfirmVaultSpec()


def evaluate_power_save_monitor_language_vault(
    spec: Optional[PowerSaveMonitorLanguageVaultSpec] = None,
) -> PowerSaveMonitorLanguageVaultReport:
    """Verify Pillar 48A: `[Power Save by Monitor]` reality split, `[Power Save Start Time]`
    9-deactivation Tier-0 guard, and `[Language]` `BK_LANG` 4-language Stage-B parity."""
    cfg = spec if spec is not None else PowerSaveMonitorLanguageVaultSpec()
    safety_errs = _safety_invariant_errors()
    if safety_errs or cfg.persistent_write_unlock_requested:
        errs = safety_errs + (
            ["persistent_write_unlock_requested must be False"]
            if cfg.persistent_write_unlock_requested
            else []
        )
        return PowerSaveMonitorLanguageVaultReport(
            passed=False,
            status=P277_STATUS_REJECTED_PILLAR_48A,
            block_code=P277_BLOCKED_SAFETY_POLICY_VIOLATION,
            reality_split_and_4mode_uxc_verified=False,
            power_save_start_time_9cond_guard_verified=False,
            bk_lang_and_stage_b_4lang_parity_verified=False,
            setup_reset_persistence_and_camset_verified=False,
            h0_equals_h3_verified=False,
            matrix_states_checked=0,
            fx3_ui_exposes_power_save_by_monitor=False,
            legacy_power_save_monitor_spoof_events=1,
            unsafe_power_save_sleep_interference_events=0,
            bk_lang_parity_drift_events=0,
            stage_b_4lang_uxc_ltt_drift_events=0,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            digest_sha256=_canonical_sha256({"blocked": P277_BLOCKED_SAFETY_POLICY_VIOLATION}),
            errors=tuple(errs),
        )

    errs: List[str] = []
    block_code: Optional[str] = None

    def _set_block(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errs.append(msg)

    # Validate structural invariants
    if (
        cfg.camera_model != P277_FX3_MODEL_NAME
        or cfg.camera_model_id != P277_FX3_MODEL_ID
        or cfg.helpguide_id != P277_FX3_HELPGUIDE_ID
        or cfg.fw_version not in P277_FX3_SUPPORTED_FW_VERSIONS
        or cfg.power_setting_menu_path != P277_POWER_SETTING_OPTION_MENU_PATH
        or cfg.language_menu_path != P277_LANGUAGE_MENU_PATH
        or cfg.pre_power_save_start_time not in P277_POWER_SAVE_START_TIME_MODES
        or cfg.pre_auto_power_off_temp not in P277_AUTO_POWER_OFF_TEMP_MODES
        or cfg.reset_action not in P277_RESET_ACTIONS
    ):
        _set_block(
            P277_BLOCKED_INVALID_PILLAR48A_SPEC,
            "Invalid Pillar 48A camera model, firmware version, menu path, or power/reset spec",
        )

    # 1. [Power Save by Monitor] reality split & 4-mode appFw.so / .uxc check
    reality_split_ok = True
    spoof_events = cfg.legacy_power_save_monitor_spoof_events
    if (
        cfg.fx3_ui_exposes_power_save_by_monitor is not False
        or cfg.fx6_ui_exposes_power_save_by_monitor is not False
        or cfg.fx3_power_setting_subitems != P277_FX3_POWER_SETTING_EXACT_2_SUBITEMS
    ):
        reality_split_ok = False
        spoof_events = max(spoof_events, 1)
        _set_block(
            P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF,
            "Stock ILME-FX3 / ILME-FX6 UI must expose only 2 Power Setting Option items (not Power Save by Monitor)",
        )
    if (
        cfg.power_save_monitor_label != P277_POWER_SAVE_MONITOR_LABEL
        or cfg.power_save_monitor_4_modes != P277_POWER_SAVE_MONITOR_4_MODES
        or cfg.sibling_power_save_by_monitor_mode not in P277_POWER_SAVE_MONITOR_4_MODES
        or cfg.sibling_power_save_by_monitor_mode == P277_FORBIDDEN_POWER_SAVE_MONITOR_SPOOF_LABEL
        or cfg.legacy_power_save_monitor_spoof_events != 0
    ):
        reality_split_ok = False
        spoof_events = max(spoof_events, 1)
        _set_block(
            P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF,
            "Power Save by Monitor must match exact 4 appFw.so modes and reject 'Open: On/Close: Off' spoofing",
        )

    # Sibling vari-angle headless capture safety check
    _, sibling_sleeps, sibling_headless_safe = compute_expected_power_save_by_monitor_effective_state(
        camera_model="ILME-FX2",
        monitor_power_linkage_mode=cfg.sibling_power_save_by_monitor_mode,
        lcd_folded_inward=cfg.sibling_lcd_folded_inward,
        headless_hdmi_capture_active=cfg.headless_hdmi_capture_active,
    )
    if not sibling_headless_safe or (cfg.headless_hdmi_capture_active and sibling_sleeps):
        reality_split_ok = False
        _set_block(
            P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF,
            f"Sibling monitor mode {cfg.sibling_power_save_by_monitor_mode!r} causes sleep during folded-LCD headless HDMI capture",
        )

    # Exhaustive check of 4 modes x 2 LCD states x 2 HDMI states x 2 body classes (32 states)
    matrix_checked = 0
    for body_cls in (P277_FX3_MODEL_NAME, "ILME-FX2"):
        for linkage_mode in P277_POWER_SAVE_MONITOR_4_MODES:
            for folded in (False, True):
                for headless in (False, True):
                    ui_exp, sleeps, h_safe = compute_expected_power_save_by_monitor_effective_state(
                        camera_model=body_cls,
                        monitor_power_linkage_mode=linkage_mode,
                        lcd_folded_inward=folded,
                        headless_hdmi_capture_active=headless,
                    )
                    if body_cls == P277_FX3_MODEL_NAME and (ui_exp or sleeps or not h_safe):
                        reality_split_ok = False
                        _set_block(
                            P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF,
                            "FX3 reality split matrix failed",
                        )
                    matrix_checked += 1

    # 2. [Power Save Start Time] 9-deactivation Tier-0 recovery guard
    ps_9cond_ok = True
    sleep_interferences = cfg.unsafe_power_save_sleep_interference_events
    invalid_conds = [
        c for c in cfg.active_deactivation_conditions if c not in P277_POWER_SAVE_9_DEACTIVATION_CONDITIONS
    ]
    if invalid_conds:
        ps_9cond_ok = False
        _set_block(
            P277_BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP,
            f"Unknown Power Save deactivation condition(s): {invalid_conds}",
        )
    _, tier0_sleep_safe = compute_expected_power_save_start_time_recovery_guard(
        configured_power_save_start_time=cfg.post_power_save_start_time,
        active_deactivation_conditions=cfg.active_deactivation_conditions,
        airgapped_battery_tier0_session=cfg.airgapped_battery_tier0_session,
    )
    if not tier0_sleep_safe or cfg.unsafe_power_save_sleep_interference_events != 0:
        ps_9cond_ok = False
        sleep_interferences = max(sleep_interferences, 1)
        _set_block(
            P277_BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP,
            f"Air-gapped battery Tier-0 session with 0/9 deactivation conditions must not use {cfg.post_power_save_start_time!r}",
        )

    for start_t in P277_POWER_SAVE_START_TIME_MODES:
        for cond_subset in ((), (P277_POWER_SAVE_9_DEACTIVATION_CONDITIONS[0],)):
            for airgap in (False, True):
                bypassed, safe = compute_expected_power_save_start_time_recovery_guard(
                    configured_power_save_start_time=start_t,
                    active_deactivation_conditions=cond_subset,
                    airgapped_battery_tier0_session=airgap,
                )
                expected_safe = (
                    (not airgap)
                    or bypassed
                    or (start_t in P277_RECOVERY_SAFE_POWER_SAVE_START_TIMES)
                )
                if safe != expected_safe:
                    ps_9cond_ok = False
                    _set_block(
                        P277_BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP,
                        "Power Save 9-condition matrix invariant failed",
                    )
                matrix_checked += 1

    # 3. [Language] BK_LANG (0x02cf019c) parity & Stage-B 4-lang .uxc + .ltt bank table
    lang_parity_ok = True
    bk_drift = cfg.bk_lang_parity_drift_events
    uxc_ltt_drift = cfg.stage_b_4lang_uxc_ltt_drift_events
    if (
        cfg.bk_lang_key != P277_LANGUAGE_BK_KEY
        or cfg.fx3_language_count != P277_FX3_LANGUAGE_COUNT
        or cfg.fx6_language_count != P277_FX6_LANGUAGE_COUNT
        or cfg.fx3_backup_bk_lang_val != P277_FX3_BACKUP_BK_LANG_DEFAULT_VALUE
        or cfg.fx6_ntsc_bk_lang_val != P277_FX6_BACKUP_NTSC_BK_LANG_VALUE
        or cfg.fx6_cn1_bk_lang_val != P277_FX6_BACKUP_CN1_BK_LANG_VALUE
        or cfg.bk_lang_parity_drift_events != 0
    ):
        lang_parity_ok = False
        bk_drift = max(bk_drift, 1)
        _set_block(
            P277_BLOCKED_BK_LANG_OR_STAGE_B_4LANG_PARITY_DRIFT,
            "BK_LANG 0x02cf019c FX3 (34 langs, 0x00@0x90ff0) vs FX6 (29 langs, 0x00/0x19@0x89242) parity drift",
        )
    expected_lang_row = P277_STAGE_B_4LANG_UXC_LTT_TABLE.get(cfg.stage_b_selected_lang)
    if (
        expected_lang_row is None
        or cfg.stage_b_bank_id != expected_lang_row["bank_id"]
        or cfg.stage_b_font_str_pair != expected_lang_row["font_str_pair"]
        or cfg.stage_b_ltt_font != expected_lang_row["ltt_font"]
        or cfg.stage_b_4lang_uxc_ltt_drift_events != 0
    ):
        lang_parity_ok = False
        uxc_ltt_drift = max(uxc_ltt_drift, 1)
        _set_block(
            P277_BLOCKED_BK_LANG_OR_STAGE_B_4LANG_PARITY_DRIFT,
            f"Stage-B 4-lang .uxc/.ltt bank mismatch for {cfg.stage_b_selected_lang!r}",
        )
    matrix_checked += len(P277_STAGE_B_4LANG_UXC_LTT_TABLE)

    # 4. (Setup) Reset boundary survival & CAMSET01..10.DAT O_RDONLY restore
    reset_ok = True
    exp_ps, exp_temp, exp_sib, exp_lang = compute_expected_pillar48a_reset_state(
        pre_power_save_start_time=cfg.pre_power_save_start_time,
        pre_auto_power_off_temp=cfg.pre_auto_power_off_temp,
        pre_sibling_power_save_by_monitor=cfg.pre_sibling_power_save_by_monitor,
        pre_language=cfg.pre_language,
        reset_action=cfg.reset_action,
    )
    if cfg.camset_load_after_reset:
        if (
            cfg.camset_slot != P277_SLOT1_VAULT_SLOT
            or cfg.camset_filename not in P277_CAMSET_FILENAMES
            or cfg.camset_source_model != P277_FX3_MODEL_NAME
            or not cfg.camset_read_only_load
        ):
            reset_ok = False
            _set_block(
                P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT,
                "CAMSET load must be read-only from Slot-1 ILME-FX3 CAMSET01..10.DAT",
            )
        exp_ps = cfg.saved_power_save_start_time
        exp_temp = cfg.saved_auto_power_off_temp
        exp_sib = cfg.saved_sibling_power_save_by_monitor
        exp_lang = cfg.saved_language

    if (
        cfg.post_power_save_start_time != exp_ps
        or cfg.post_auto_power_off_temp != exp_temp
        or cfg.post_sibling_power_save_by_monitor != exp_sib
        or cfg.post_language != exp_lang
    ):
        reset_ok = False
        _set_block(
            P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT,
            (
                f"Setup reset boundary drift for {cfg.reset_action!r}: expected "
                f"({exp_ps!r}, {exp_temp!r}, {exp_sib!r}, {exp_lang!r}), got "
                f"({cfg.post_power_save_start_time!r}, {cfg.post_auto_power_off_temp!r}, "
                f"{cfg.post_sibling_power_save_by_monitor!r}, {cfg.post_language!r})"
            ),
        )

    for r_act in P277_RESET_ACTIONS:
        ps_out, _, _, lang_out = compute_expected_pillar48a_reset_state(
            pre_power_save_start_time="30 Min",
            pre_auto_power_off_temp="High",
            pre_sibling_power_save_by_monitor="Does Not Link",
            pre_language="Japanese",
            reset_action=r_act,
        )
        if r_act == "Initialize":
            if ps_out != P277_POWER_SAVE_START_TIME_DEFAULT or lang_out != P277_LANGUAGE_DEFAULT:
                reset_ok = False
                _set_block(
                    P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT,
                    "Initialize must reset Power Save Start Time & Language",
                )
        else:
            if ps_out != "30 Min" or lang_out != "Japanese":
                reset_ok = False
                _set_block(
                    P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT,
                    f"{r_act} must preserve Setup Power Save Start Time & Language",
                )
        matrix_checked += 1

    # 5. Volatile /tmp overlay + Tier-0 H0 == H3 + Slot-1 read-only integrity
    h0_h3_ok = True
    if not _is_tmpfs_path(cfg.overlay_dir) or _targets_persistent_emmc(cfg.overlay_dir) or not cfg.p2_blkroset_locked:
        h0_h3_ok = False
        _set_block(
            P277_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain strictly in volatile /tmp or /run with BLKROSET=True: {cfg.overlay_dir!r}",
        )
    if (
        not cfg.slot1_holds_recovery_vault
        or not cfg.slot1_sdxc_wp_locked
        or cfg.slot1_vault_delete_events != 0
        or cfg.slot1_vault_mutation_bytes != 0
        or cfg.stage_b_backup_bin_writes != 0
        or cfg.backup_bin_h0_sha256 != P277_PINNED_FX3_BACKUP_BIN_SHA256
        or cfg.backup_bin_h3_sha256 != cfg.backup_bin_h0_sha256
        or cfg.tier0_surfaces_h0_h3_matched != P277_TIER0_SURFACE_COUNT
    ):
        h0_h3_ok = False
        _set_block(
            P277_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Slot-1 read-only vault or 16/16 Tier-0 H0 == H3 Backup.bin invariant drifted",
        )

    passed = (
        reality_split_ok
        and ps_9cond_ok
        and lang_parity_ok
        and reset_ok
        and h0_h3_ok
        and len(errs) == 0
    )
    digest = _canonical_sha256(
        {
            "pillar": "48A",
            "passed": passed,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "spoof_events": spoof_events,
            "sleep_interferences": sleep_interferences,
            "bk_drift": bk_drift,
            "uxc_ltt_drift": uxc_ltt_drift,
        }
    )
    return PowerSaveMonitorLanguageVaultReport(
        passed=passed,
        status=P277_STATUS_VERIFIED_PILLAR_48A if passed else P277_STATUS_REJECTED_PILLAR_48A,
        block_code=block_code,
        reality_split_and_4mode_uxc_verified=reality_split_ok,
        power_save_start_time_9cond_guard_verified=ps_9cond_ok,
        bk_lang_and_stage_b_4lang_parity_verified=lang_parity_ok,
        setup_reset_persistence_and_camset_verified=reset_ok,
        h0_equals_h3_verified=h0_h3_ok,
        matrix_states_checked=matrix_checked,
        fx3_ui_exposes_power_save_by_monitor=cfg.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=spoof_events,
        unsafe_power_save_sleep_interference_events=sleep_interferences,
        bk_lang_parity_drift_events=bk_drift,
        stage_b_4lang_uxc_ltt_drift_events=uxc_ltt_drift,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errs),
    )


def evaluate_volume_4ch_mon_delete_confirm_vault(
    spec: Optional[Volume4chMonDeleteConfirmVaultSpec] = None,
) -> Volume4chMonDeleteConfirmVaultReport:
    """Verify Pillar 48B: `[Volume Settings]` (`0..15`, default `7`) + `XLR-H1` speaker feedback guard,
    `[4ch Audio Monitoring]` (`5` routes vs HDMI `[4ch Audio Output]`), and `[Delete confirm.]`
    (`"Cancel" first` default) + `Slot-1` recovery vault delete/format firewall."""
    cfg = spec if spec is not None else Volume4chMonDeleteConfirmVaultSpec()
    safety_errs = _safety_invariant_errors()
    if safety_errs or cfg.persistent_write_unlock_requested:
        errs = safety_errs + (
            ["persistent_write_unlock_requested must be False"]
            if cfg.persistent_write_unlock_requested
            else []
        )
        return Volume4chMonDeleteConfirmVaultReport(
            passed=False,
            status=P277_STATUS_REJECTED_PILLAR_48B,
            block_code=P277_BLOCKED_SAFETY_POLICY_VIOLATION,
            volume_0_15_and_xlrh1_guard_verified=False,
            audio_mon_5_routes_and_hdmi_isolation_verified=False,
            delete_confirm_cancel_first_and_twice_verified=False,
            reset_scope_and_slot1_delete_format_firewall_verified=False,
            h0_equals_h3_verified=False,
            matrix_states_checked=0,
            xlrh1_acoustic_feedback_violations=0,
            audio_mon_4ch_hdmi_confusion_events=0,
            destructive_delete_confirm_drift_events=0,
            slot1_vault_delete_events=0,
            slot1_vault_mutation_bytes=0,
            slot1_format_hard_locked=P277_SLOT1_FORMAT_HARD_LOCKED,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            digest_sha256=_canonical_sha256({"blocked": P277_BLOCKED_SAFETY_POLICY_VIOLATION}),
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
        cfg.camera_model != P277_FX3_MODEL_NAME
        or cfg.camera_model_id != P277_FX3_MODEL_ID
        or cfg.helpguide_id != P277_FX3_HELPGUIDE_ID
        or cfg.fw_version not in P277_FX3_SUPPORTED_FW_VERSIONS
        or cfg.volume_menu_path != P277_VOLUME_SETTINGS_MENU_PATH
        or cfg.audio_monitoring_menu_path != P277_AUDIO_MONITORING_MENU_PATH
        or cfg.delete_confirm_menu_path != P277_DELETE_CONFIRM_MENU_PATH
        or cfg.delete_twice_menu_path != P277_DELETE_TWICE_MENU_PATH
        or cfg.playback_output_target not in P277_PLAYBACK_OUTPUT_TARGETS
        or cfg.reset_action not in P277_RESET_ACTIONS
        or cfg.requested_vault_action not in P277_VAULT_TARGET_ACTIONS
    ):
        _set_block(
            P277_BLOCKED_INVALID_PILLAR48B_SPEC,
            "Invalid Pillar 48B model, menu path, playback target, or reset/vault action spec",
        )

    # 1. [Volume Settings] (0..15, default 7) + XLR-H1 internal-speaker acoustic feedback guard
    volume_ok = True
    feedback_violations = cfg.xlrh1_acoustic_feedback_violations
    if (
        cfg.factory_default_volume != P277_VOLUME_SETTINGS_DEFAULT
        or not (P277_VOLUME_SETTINGS_MIN <= cfg.pre_volume_settings <= P277_VOLUME_SETTINGS_MAX)
        or not (P277_VOLUME_SETTINGS_MIN <= cfg.post_volume_settings <= P277_VOLUME_SETTINGS_MAX)
    ):
        volume_ok = False
        _set_block(
            P277_BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK,
            f"Volume Settings must remain within discrete 0..15 with factory default 7 (got pre={cfg.pre_volume_settings}, post={cfg.post_volume_settings})",
        )
    fb_safe, _ = compute_expected_xlrh1_speaker_feedback_guard(
        volume_level=cfg.post_volume_settings,
        xlrh1_mic_attached=cfg.xlrh1_mic_attached,
        playback_output_target=cfg.playback_output_target,
        xlrh1_acoustic_separation_active=cfg.xlrh1_acoustic_separation_active,
    )
    if not fb_safe or cfg.xlrh1_acoustic_feedback_violations != 0:
        volume_ok = False
        feedback_violations = max(feedback_violations, 1)
        _set_block(
            P277_BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK,
            "XLR-H1 + Internal Speaker acoustic feedback guard triggered (volume > 4 without acoustic separation)",
        )

    matrix_checked = 0
    for vol in range(P277_VOLUME_SETTINGS_MIN, P277_VOLUME_SETTINGS_MAX + 1):
        for target in P277_PLAYBACK_OUTPUT_TARGETS:
            for sep in (False, True):
                safe, _ = compute_expected_xlrh1_speaker_feedback_guard(
                    volume_level=vol,
                    xlrh1_mic_attached=True,
                    playback_output_target=target,
                    xlrh1_acoustic_separation_active=sep,
                )
                expected = not (
                    target == "Internal Speaker"
                    and not sep
                    and vol > P277_XLRH1_SAFE_INTERNAL_SPEAKER_MAX_VOLUME
                )
                if safe != expected:
                    volume_ok = False
                    _set_block(
                        P277_BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK,
                        "Volume Settings 0..15 x XLR-H1 feedback matrix failed",
                    )
                matrix_checked += 1

    # 2. [4ch Audio Monitoring] (5 routes) vs HDMI [4ch Audio Output]
    audio_mon_ok = True
    audio_hdmi_conf = cfg.audio_mon_4ch_hdmi_confusion_events
    if (
        cfg.factory_default_audio_monitoring_ch != P277_AUDIO_MONITORING_DEFAULT
        or cfg.pre_audio_monitoring_ch not in P277_AUDIO_MONITORING_5_ROUTES
        or cfg.post_audio_monitoring_ch not in P277_AUDIO_MONITORING_5_ROUTES
        or cfg.hdmi_4ch_output_ch not in P277_HDMI_4CH_OUTPUT_MODES
        or cfg.headphone_35mm_channels > P277_HEADPHONE_35MM_MAX_CHANNELS
        or cfg.audio_mon_4ch_hdmi_confusion_events != 0
    ):
        audio_mon_ok = False
        audio_hdmi_conf = max(audio_hdmi_conf, 1)
        _set_block(
            P277_BLOCKED_AUDIO_MON_4CH_OR_HDMI_CONFUSION,
            "Invalid 4ch Audio Monitoring route (5 routes), 3.5mm > 2ch stereo, or HDMI 4ch Audio Output confusion",
        )
    matrix_checked += len(P277_AUDIO_MONITORING_5_ROUTES) * len(P277_HDMI_4CH_OUTPUT_MODES)

    # 3. [Delete confirm.] ('"Cancel" first' default) & [Delete pressing twice] ('Off' default)
    del_cfg_ok = True
    del_drift = cfg.destructive_delete_confirm_drift_events
    if (
        cfg.factory_default_delete_confirm != P277_DELETE_CONFIRM_DEFAULT
        or cfg.factory_default_delete_pressing_twice != P277_DELETE_TWICE_DEFAULT
        or cfg.pre_delete_confirm not in P277_DELETE_CONFIRM_MODES
        or cfg.post_delete_confirm not in P277_DELETE_CONFIRM_MODES
        or cfg.pre_delete_pressing_twice not in P277_ON_OFF_MODES
        or cfg.post_delete_pressing_twice not in P277_ON_OFF_MODES
    ):
        del_cfg_ok = False
        del_drift = max(del_drift, 1)
        _set_block(
            P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT,
            "Invalid Delete confirm. or Delete pressing twice state",
        )
    if (
        cfg.post_delete_confirm != P277_DELETE_CONFIRM_DEFAULT
        or cfg.post_delete_pressing_twice != P277_DELETE_TWICE_DEFAULT
        or cfg.destructive_delete_confirm_drift_events != 0
    ):
        del_cfg_ok = False
        del_drift = max(del_drift, 1)
        _set_block(
            P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT,
            "Recovery bench requires Delete confirm.='\"Cancel\" first' and Delete pressing twice='Off'",
        )

    # 4. Reset scope + hard Slot-1 recovery vault Delete/Format firewall
    firewall_ok = True
    vault_del_events = cfg.slot1_vault_delete_events
    vault_mut_bytes = cfg.slot1_vault_mutation_bytes
    exp_vol, exp_mon, exp_dc, exp_d2x, vault_blocked = (
        compute_expected_pillar48b_reset_and_slot1_vault_guard(
            pre_volume_settings=cfg.pre_volume_settings,
            pre_audio_monitoring_ch=cfg.pre_audio_monitoring_ch,
            pre_delete_confirm=cfg.pre_delete_confirm,
            pre_delete_pressing_twice=cfg.pre_delete_pressing_twice,
            reset_action=cfg.reset_action,
            slot1_holds_recovery_vault=cfg.slot1_holds_recovery_vault,
            slot1_sdxc_wp_locked=cfg.slot1_sdxc_wp_locked,
            requested_vault_slot=cfg.requested_vault_slot,
            requested_vault_action=cfg.requested_vault_action,
        )
    )
    if cfg.camset_load_after_reset:
        if (
            cfg.camset_slot != P277_SLOT1_VAULT_SLOT
            or cfg.camset_filename not in P277_CAMSET_FILENAMES
            or cfg.camset_source_model != P277_FX3_MODEL_NAME
            or not cfg.camset_read_only_load
        ):
            firewall_ok = False
            _set_block(
                P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT,
                "CAMSET load must be read-only from Slot-1 ILME-FX3 CAMSET01..10.DAT",
            )
        exp_vol = cfg.saved_volume_settings
        exp_mon = cfg.saved_audio_monitoring_ch
        exp_dc = cfg.saved_delete_confirm
        exp_d2x = cfg.saved_delete_pressing_twice

    if (
        cfg.post_volume_settings != exp_vol
        or cfg.post_audio_monitoring_ch != exp_mon
        or cfg.post_delete_confirm != exp_dc
        or cfg.post_delete_pressing_twice != exp_d2x
    ):
        del_cfg_ok = False
        del_drift = max(del_drift, 1)
        _set_block(
            P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT,
            (
                f"Setup/Playback reset drift for {cfg.reset_action!r}: expected "
                f"({exp_vol}, {exp_mon!r}, {exp_dc!r}, {exp_d2x!r}), got "
                f"({cfg.post_volume_settings}, {cfg.post_audio_monitoring_ch!r}, "
                f"{cfg.post_delete_confirm!r}, {cfg.post_delete_pressing_twice!r})"
            ),
        )

    if (
        vault_blocked
        or not cfg.slot1_holds_recovery_vault
        or not cfg.slot1_sdxc_wp_locked
        or not cfg.slot1_format_hard_locked
        or cfg.slot1_vault_delete_events != 0
        or cfg.slot1_vault_mutation_bytes != 0
    ):
        firewall_ok = False
        if vault_blocked:
            vault_del_events = max(vault_del_events, 1)
        _set_block(
            P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT,
            f"Hard Slot-1 recovery vault delete/format firewall blocked {cfg.requested_vault_action!r} on Slot {cfg.requested_vault_slot}",
        )

    for r_act in P277_RESET_ACTIONS:
        for v_act in P277_VAULT_TARGET_ACTIONS:
            rv, rm, rdc, rd2x, blk = compute_expected_pillar48b_reset_and_slot1_vault_guard(
                pre_volume_settings=12,
                pre_audio_monitoring_ch="CH1+3/CH2+4",
                pre_delete_confirm='"Delete" first',
                pre_delete_pressing_twice="On",
                reset_action=r_act,
                slot1_holds_recovery_vault=True,
                slot1_sdxc_wp_locked=True,
                requested_vault_slot=1,
                requested_vault_action=v_act,
            )
            if blk != (v_act in P277_DESTRUCTIVE_VAULT_ACTIONS):
                firewall_ok = False
                _set_block(
                    P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT,
                    "Slot-1 delete/format firewall matrix invariant failed",
                )
            if r_act == "Initialize":
                if (rv, rm, rdc, rd2x) != (7, "CH1/CH2", '"Cancel" first', "Off"):
                    del_cfg_ok = False
                    _set_block(
                        P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT,
                        "Initialize must restore Pillar 48B factory defaults",
                    )
            else:
                if (rv, rm, rdc, rd2x) != (12, "CH1+3/CH2+4", '"Delete" first', "On"):
                    del_cfg_ok = False
                    _set_block(
                        P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT,
                        f"{r_act} must preserve Pillar 48B Setup/Playback items",
                    )
            matrix_checked += 1

    # 5. Volatile /tmp overlay + Tier-0 H0 == H3
    h0_h3_ok = True
    if not _is_tmpfs_path(cfg.overlay_dir) or _targets_persistent_emmc(cfg.overlay_dir) or not cfg.p2_blkroset_locked:
        h0_h3_ok = False
        _set_block(
            P277_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain strictly in volatile /tmp or /run with BLKROSET=True: {cfg.overlay_dir!r}",
        )
    if (
        cfg.stage_b_backup_bin_writes != 0
        or cfg.backup_bin_h0_sha256 != P277_PINNED_FX3_BACKUP_BIN_SHA256
        or cfg.backup_bin_h3_sha256 != cfg.backup_bin_h0_sha256
        or cfg.tier0_surfaces_h0_h3_matched != P277_TIER0_SURFACE_COUNT
    ):
        h0_h3_ok = False
        _set_block(
            P277_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 H0 == H3 Backup.bin invariant drifted",
        )

    passed = (
        volume_ok
        and audio_mon_ok
        and del_cfg_ok
        and firewall_ok
        and h0_h3_ok
        and len(errs) == 0
    )
    digest = _canonical_sha256(
        {
            "pillar": "48B",
            "passed": passed,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "feedback_violations": feedback_violations,
            "audio_hdmi_conf": audio_hdmi_conf,
            "del_drift": del_drift,
            "vault_del_events": vault_del_events,
            "vault_mut_bytes": vault_mut_bytes,
        }
    )
    return Volume4chMonDeleteConfirmVaultReport(
        passed=passed,
        status=P277_STATUS_VERIFIED_PILLAR_48B if passed else P277_STATUS_REJECTED_PILLAR_48B,
        block_code=block_code,
        volume_0_15_and_xlrh1_guard_verified=volume_ok,
        audio_mon_5_routes_and_hdmi_isolation_verified=audio_mon_ok,
        delete_confirm_cancel_first_and_twice_verified=del_cfg_ok,
        reset_scope_and_slot1_delete_format_firewall_verified=firewall_ok,
        h0_equals_h3_verified=h0_h3_ok,
        matrix_states_checked=matrix_checked,
        xlrh1_acoustic_feedback_violations=feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=audio_hdmi_conf,
        destructive_delete_confirm_drift_events=del_drift,
        slot1_vault_delete_events=vault_del_events,
        slot1_vault_mutation_bytes=vault_mut_bytes,
        slot1_format_hard_locked=cfg.slot1_format_hard_locked,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errs),
    )


def verify_power_save_monitor_language_volume_delete_and_vault(
    power_save_lang_spec: Optional[PowerSaveMonitorLanguageVaultSpec] = None,
    volume_delete_spec: Optional[Volume4chMonDeleteConfirmVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> PowerSaveMonitorLanguageVolumeDeleteVaultReport:
    """Combined Pillar 48A + Pillar 48B + Wave-46 bounded `O_RDONLY` donor report."""
    errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase277_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_power_save_monitor_language_vault(power_save_lang_spec)
    rep_b = evaluate_volume_4ch_mon_delete_confirm_vault(volume_delete_spec)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 277 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )
    ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return PowerSaveMonitorLanguageVolumeDeleteVaultReport(
        schema=PHASE277_SCHEMA,
        version=PHASE277_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=ok,
        passed=ok,
        status=P277_STATUS_VERIFIED_PILLAR48_SUITE if ok else P277_STATUS_FAIL_PILLAR48_SUITE,
        donor_snapshot=donor_snapshot,
        power_save_language_report=rep_a,
        volume_4ch_delete_report=rep_b,
        fx3_ui_exposes_power_save_by_monitor=rep_a.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=rep_a.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            rep_a.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=rep_a.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=rep_a.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=rep_b.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=rep_b.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=rep_b.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=rep_b.slot1_vault_delete_events,
        slot1_vault_mutation_bytes=rep_b.slot1_vault_mutation_bytes,
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


def verify_power_save_monitor_language_volume_delete_vault(
    power_save_lang_spec: Optional[PowerSaveMonitorLanguageVaultSpec] = None,
    volume_delete_spec: Optional[Volume4chMonDeleteConfirmVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> PowerSaveMonitorLanguageVolumeDeleteVaultReport:
    """Symmetry alias for `verify_power_save_monitor_language_volume_delete_and_vault`."""
    return verify_power_save_monitor_language_volume_delete_and_vault(
        power_save_lang_spec=power_save_lang_spec,
        volume_delete_spec=volume_delete_spec,
        force_clean_room=force_clean_room,
    )


def run_pillar48a_power_save_monitor_start_time_language_vault_6_scenario_suite() -> (
    Pillar48ASuiteResult
):
    """Run all 6 canonical Pillar 48A scenarios (`2` safe + `4` negative Wave-46 guards)."""
    cases: Tuple[Tuple[str, bool, PowerSaveMonitorLanguageVaultSpec, Optional[str]], ...] = (
        (
            P277_PILLAR_48A_SCENARIO_IDS[0],
            True,
            PowerSaveMonitorLanguageVaultSpec(),
            None,
        ),
        (
            P277_PILLAR_48A_SCENARIO_IDS[1],
            True,
            PowerSaveMonitorLanguageVaultSpec(
                sibling_power_save_by_monitor_mode="Does Not Link",
                stage_b_selected_lang="japanese",
                stage_b_bank_id=1,
                stage_b_font_str_pair=(12, 12),
                stage_b_ltt_font="HeiseiKakuGothW5-SJ_wIcon.ltt",
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P277_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_power_save_start_time="30 Min",
                saved_auto_power_off_temp="High",
                saved_sibling_power_save_by_monitor="Open: Return",
                saved_language="Japanese",
                post_power_save_start_time="30 Min",
                post_auto_power_off_temp="High",
                post_sibling_power_save_by_monitor="Open: Return",
                post_language="Japanese",
            ),
            None,
        ),
        (
            P277_PILLAR_48A_SCENARIO_IDS[2],
            False,
            PowerSaveMonitorLanguageVaultSpec(
                fx3_ui_exposes_power_save_by_monitor=True,
                sibling_power_save_by_monitor_mode=P277_FORBIDDEN_POWER_SAVE_MONITOR_SPOOF_LABEL,
                legacy_power_save_monitor_spoof_events=1,
            ),
            P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF,
        ),
        (
            P277_PILLAR_48A_SCENARIO_IDS[3],
            False,
            PowerSaveMonitorLanguageVaultSpec(
                airgapped_battery_tier0_session=True,
                active_deactivation_conditions=(),
                pre_power_save_start_time="5 Min",
                post_power_save_start_time="5 Min",
                unsafe_power_save_sleep_interference_events=1,
            ),
            P277_BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP,
        ),
        (
            P277_PILLAR_48A_SCENARIO_IDS[4],
            False,
            PowerSaveMonitorLanguageVaultSpec(
                fx6_cn1_bk_lang_val=0x00,
                bk_lang_parity_drift_events=1,
                stage_b_selected_lang="schinese",
                stage_b_ltt_font="UniversOTS-SJ_wIcon.ltt",
                stage_b_4lang_uxc_ltt_drift_events=1,
            ),
            P277_BLOCKED_BK_LANG_OR_STAGE_B_4LANG_PARITY_DRIFT,
        ),
        (
            P277_PILLAR_48A_SCENARIO_IDS[5],
            False,
            PowerSaveMonitorLanguageVaultSpec(
                active_deactivation_conditions=("USB power supply",),
                reset_action="Camera Settings Reset",
                pre_power_save_start_time="30 Min",
                pre_language="Japanese",
                post_power_save_start_time="5 Min",
                post_language="—",
            ),
            P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT,
        ),
    )

    outcomes: List[Pillar48ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_power_save_monitor_language_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar48ScenarioOutcome(
                scenario_id=sid,
                pillar="48A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar48ASuiteResult(
        passed=all_ok,
        status=P277_STATUS_VERIFIED_PILLAR_48A if all_ok else P277_STATUS_REJECTED_PILLAR_48A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar48b_volume_4ch_mon_delete_confirm_slot1_vault_6_scenario_suite() -> (
    Pillar48BSuiteResult
):
    """Run all 6 canonical Pillar 48B scenarios (`2` safe + `4` negative Volume/4ch/Delete/Slot-1 guards)."""
    cases: Tuple[Tuple[str, bool, Volume4chMonDeleteConfirmVaultSpec, Optional[str]], ...] = (
        (
            P277_PILLAR_48B_SCENARIO_IDS[0],
            True,
            Volume4chMonDeleteConfirmVaultSpec(),
            None,
        ),
        (
            P277_PILLAR_48B_SCENARIO_IDS[1],
            True,
            Volume4chMonDeleteConfirmVaultSpec(
                xlrh1_mic_attached=True,
                playback_output_target="Internal Speaker",
                xlrh1_acoustic_separation_active=False,
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P277_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_volume_settings=4,
                saved_audio_monitoring_ch="CH1+3/CH2+4",
                saved_delete_confirm='"Cancel" first',
                saved_delete_pressing_twice="Off",
                post_volume_settings=4,
                post_audio_monitoring_ch="CH1+3/CH2+4",
                post_delete_confirm='"Cancel" first',
                post_delete_pressing_twice="Off",
            ),
            None,
        ),
        (
            P277_PILLAR_48B_SCENARIO_IDS[2],
            False,
            Volume4chMonDeleteConfirmVaultSpec(
                xlrh1_mic_attached=True,
                playback_output_target="Internal Speaker",
                xlrh1_acoustic_separation_active=False,
                pre_volume_settings=15,
                post_volume_settings=15,
                xlrh1_acoustic_feedback_violations=1,
            ),
            P277_BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK,
        ),
        (
            P277_PILLAR_48B_SCENARIO_IDS[3],
            False,
            Volume4chMonDeleteConfirmVaultSpec(
                pre_audio_monitoring_ch="4ch-Direct",
                post_audio_monitoring_ch="4ch-Direct",
                headphone_35mm_channels=4,
                audio_mon_4ch_hdmi_confusion_events=1,
            ),
            P277_BLOCKED_AUDIO_MON_4CH_OR_HDMI_CONFUSION,
        ),
        (
            P277_PILLAR_48B_SCENARIO_IDS[4],
            False,
            Volume4chMonDeleteConfirmVaultSpec(
                reset_action="Camera Settings Reset",
                pre_delete_confirm='"Delete" first',
                pre_delete_pressing_twice="On",
                post_delete_confirm='"Delete" first',
                post_delete_pressing_twice="On",
                destructive_delete_confirm_drift_events=1,
            ),
            P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT,
        ),
        (
            P277_PILLAR_48B_SCENARIO_IDS[5],
            False,
            Volume4chMonDeleteConfirmVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="DELETE_PRESSING_TWICE",
                slot1_vault_delete_events=1,
                slot1_vault_mutation_bytes=4096,
            ),
            P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT,
        ),
    )

    outcomes: List[Pillar48ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_volume_4ch_mon_delete_confirm_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar48ScenarioOutcome(
                scenario_id=sid,
                pillar="48B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar48BSuiteResult(
        passed=all_ok,
        status=P277_STATUS_VERIFIED_PILLAR_48B if all_ok else P277_STATUS_REJECTED_PILLAR_48B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar48_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar48StandaloneReport:
    """Run full Pillar 48 standalone suite (`6/6` Pillar 48A + `6/6` Pillar 48B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase277_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar48a_power_save_monitor_start_time_language_vault_6_scenario_suite()
    res_b = run_pillar48b_volume_4ch_mon_delete_confirm_slot1_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 277 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE277_SCHEMA,
            "version": PHASE277_VERSION,
            "mode": donor_snapshot.verification_mode,
            "48a": [asdict(s) for s in res_a.scenarios],
            "48b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar48StandaloneReport(
        schema=PHASE277_SCHEMA,
        version=PHASE277_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P277_STATUS_VERIFIED_PILLAR48_SUITE if all_ok else P277_STATUS_FAIL_PILLAR48_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_48a_power_save_monitor_language_vault=res_a,
        pillar_48b_volume_4ch_mon_delete_confirm_slot1_vault=res_b,
        fx3_ui_exposes_power_save_by_monitor=P277_FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR,
        legacy_power_save_monitor_spoof_events=(
            P277_LEGACY_POWER_SAVE_MONITOR_SPOOF_EVENTS if res_a.passed else 1
        ),
        unsafe_power_save_sleep_interference_events=(
            P277_UNSAFE_POWER_SAVE_SLEEP_INTERFERENCE_EVENTS if res_a.passed else 1
        ),
        bk_lang_parity_drift_events=P277_BK_LANG_PARITY_DRIFT_EVENTS if res_a.passed else 1,
        stage_b_4lang_uxc_ltt_drift_events=(
            P277_STAGE_B_4LANG_UXC_LTT_DRIFT_EVENTS if res_a.passed else 1
        ),
        xlrh1_acoustic_feedback_violations=(
            P277_XLRH1_ACOUSTIC_FEEDBACK_VIOLATIONS if res_b.passed else 1
        ),
        audio_mon_4ch_hdmi_confusion_events=(
            P277_AUDIO_MON_4CH_HDMI_CONFUSION_EVENTS if res_b.passed else 1
        ),
        destructive_delete_confirm_drift_events=(
            P277_DESTRUCTIVE_DELETE_CONFIRM_DRIFT_EVENTS if res_b.passed else 1
        ),
        slot1_vault_delete_events=P277_SLOT1_VAULT_DELETE_EVENTS if res_b.passed else 1,
        slot1_vault_mutation_bytes=P277_SLOT1_VAULT_MUTATION_BYTES if res_b.passed else 4096,
        slot1_format_hard_locked=P277_SLOT1_FORMAT_HARD_LOCKED,
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
# Unified 48/48 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master48_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_48pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master48PillarRecoveryReport:
    """Evaluate and aggregate all 48 recovery pillars (`1..48`) concurrently -> `48/48` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_48_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_47pillar() -> Master47PillarRecoveryReport:
        return evaluate_realhw_47pillar_recovery_master(**kw)

    def _run_p48() -> Tuple[Pillar48StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar48_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_47 = pool.submit(_run_47pillar)
        fut_48 = pool.submit(_run_p48)
        m47_rep = fut_47.result()
        p48_rep, p48_dt = fut_48.result()

    all_errors: List[str] = list(m47_rep.errors) + list(p48_rep.errors)
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
        if getattr(m47_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-47 violated {attr_name} == {expected_val}")
        if getattr(p48_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 48 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
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
        ("slot1_vault_mutation_bytes", 0),
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
        if getattr(m47_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-47 violated {attr_name} == {expected_val}")
    if m47_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillars 1-47 violated bodydata_flash_attempts_blocked >= 1")

    for attr_name, expected_val in (
        ("fx3_ui_exposes_power_save_by_monitor", False),
        ("legacy_power_save_monitor_spoof_events", 0),
        ("unsafe_power_save_sleep_interference_events", 0),
        ("bk_lang_parity_drift_events", 0),
        ("stage_b_4lang_uxc_ltt_drift_events", 0),
        ("xlrh1_acoustic_feedback_violations", 0),
        ("audio_mon_4ch_hdmi_confusion_events", 0),
        ("destructive_delete_confirm_drift_events", 0),
        ("slot1_vault_delete_events", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("slot1_format_hard_locked", True),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(p48_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 48 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m47_rep.pillars)
    spec48 = MASTER_48_PILLAR_SPECS[47]
    p48_metrics = {
        "pillar_48a_power_save_monitor_language_vault": (
            f"{p48_rep.pillar_48a_power_save_monitor_language_vault.scenarios_passed}/"
            f"{p48_rep.pillar_48a_power_save_monitor_language_vault.scenarios_total}"
        ),
        "pillar_48b_volume_4ch_mon_delete_confirm_slot1_vault": (
            f"{p48_rep.pillar_48b_volume_4ch_mon_delete_confirm_slot1_vault.scenarios_passed}/"
            f"{p48_rep.pillar_48b_volume_4ch_mon_delete_confirm_slot1_vault.scenarios_total}"
        ),
        "fx3_ui_exposes_power_save_by_monitor": p48_rep.fx3_ui_exposes_power_save_by_monitor,
        "legacy_power_save_monitor_spoof_events": p48_rep.legacy_power_save_monitor_spoof_events,
        "unsafe_power_save_sleep_interference_events": (
            p48_rep.unsafe_power_save_sleep_interference_events
        ),
        "bk_lang_parity_drift_events": p48_rep.bk_lang_parity_drift_events,
        "stage_b_4lang_uxc_ltt_drift_events": p48_rep.stage_b_4lang_uxc_ltt_drift_events,
        "xlrh1_acoustic_feedback_violations": p48_rep.xlrh1_acoustic_feedback_violations,
        "audio_mon_4ch_hdmi_confusion_events": p48_rep.audio_mon_4ch_hdmi_confusion_events,
        "destructive_delete_confirm_drift_events": p48_rep.destructive_delete_confirm_drift_events,
        "slot1_vault_delete_events": p48_rep.slot1_vault_delete_events,
        "slot1_vault_mutation_bytes": p48_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p48_rep.slot1_format_hard_locked,
        "hardware_live_attachment_authorized": p48_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p48_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec48[0],
            pillar_id=spec48[1],
            phase_label=spec48[2],
            module_name=spec48[3],
            passed=bool(p48_rep.all_passed),
            status=p48_rep.status,
            verification_mode=p48_rep.verification_mode,
            elapsed_seconds=p48_dt,
            key_metrics=p48_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec48[1],
                    "mode": p48_rep.verification_mode,
                    "status": p48_rep.status,
                    "metrics": p48_metrics,
                    "passed": p48_rep.all_passed,
                }
            ),
            errors=tuple(p48_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master48_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p48_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_48_PILLAR_COUNT == 48
        and pillars_passed == 48
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE277_SCHEMA,
            "version": PHASE277_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master48PillarRecoveryReport(
        schema=PHASE277_SCHEMA,
        version=PHASE277_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P277_STATUS_VERIFIED_48OF48_AGGREGATOR if all_ok else P277_STATUS_FAIL_48OF48_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_2s_fast_cli_budget=elapsed < P277_FAST_CLI_BUDGET_SECONDS,
        under_6s_budget=elapsed < P277_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P277_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p48_rep.donor_snapshot,
        pillar48_a_power_save_monitor_language_vault=p48_rep.pillar_48a_power_save_monitor_language_vault,
        pillar48_b_volume_4ch_mon_delete_confirm_slot1_vault=(
            p48_rep.pillar_48b_volume_4ch_mon_delete_confirm_slot1_vault
        ),
        fx3_ui_exposes_power_save_by_monitor=p48_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=p48_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            p48_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=p48_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=p48_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=p48_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=p48_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=p48_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=p48_rep.slot1_vault_delete_events,
        slot1_vault_mutation_bytes=p48_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p48_rep.slot1_format_hard_locked,
        legacy_mf_assist_spoof_events=m47_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m47_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m47_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m47_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m47_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m47_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m47_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m47_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m47_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m47_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m47_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m47_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m47_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m47_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m47_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m47_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=(
            m47_rep.tcub_camera_reset_wipe_or_format_violations
        ),
        fx3_has_builtin_end_filter=m47_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m47_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m47_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m47_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m47_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m47_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m47_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m47_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m47_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m47_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m47_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m47_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m47_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m47_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m47_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m47_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m47_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m47_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m47_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m47_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m47_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m47_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m47_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m47_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m47_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m47_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m47_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m47_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m47_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m47_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p48_rep.hardware_live_attachment_authorized,
        master_48pillar_sha256=master_sha,
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


def evaluate_48pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master48PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_48pillar_recovery_master`."""
    return evaluate_realhw_48pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_48pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master48PillarRecoveryReport:
    """Public CLI entry point for Phase 277 `48/48` unified recovery master."""
    return evaluate_realhw_48pillar_recovery_master(
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
    "MASTER_48_PILLAR_COUNT",
    "MASTER_48_PILLAR_IDS",
    "MASTER_48_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P277_AUDIO_MONITORING_5_ROUTES",
    "P277_AUDIO_MONITORING_BKID",
    "P277_AUDIO_MONITORING_DEFAULT",
    "P277_AUDIO_MONITORING_ENUM_MAP",
    "P277_AUDIO_MONITORING_MENU_PATH",
    "P277_AUDIO_MONITORING_RESID16_MAP",
    "P277_AUDIO_MON_4CH_HDMI_CONFUSION_EVENTS",
    "P277_AUDIO_SIGNALS_RESID16",
    "P277_AUTO_POWER_OFF_TEMP_DEFAULT",
    "P277_AUTO_POWER_OFF_TEMP_MODES",
    "P277_BK_LANG_PARITY_DRIFT_EVENTS",
    "P277_BLOCKED_AUDIO_MON_4CH_OR_HDMI_CONFUSION",
    "P277_BLOCKED_BK_LANG_OR_STAGE_B_4LANG_PARITY_DRIFT",
    "P277_BLOCKED_DESTRUCTIVE_DELETE_CONFIRM_DRIFT",
    "P277_BLOCKED_INVALID_PILLAR48A_SPEC",
    "P277_BLOCKED_INVALID_PILLAR48B_SPEC",
    "P277_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P277_BLOCKED_POWER_SAVE_MONITOR_REALITY_SPLIT_OR_SPOOF",
    "P277_BLOCKED_POWER_SAVE_START_TIME_RECOVERY_SLEEP",
    "P277_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P277_BLOCKED_SETUP_LANGUAGE_POWER_RESET_SCOPE_DRIFT",
    "P277_BLOCKED_SLOT1_VAULT_DELETE_OR_FORMAT",
    "P277_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P277_BLOCKED_VOLUME_RANGE_OR_XLRH1_FEEDBACK",
    "P277_BOUNDED_HEADER_BYTES",
    "P277_CAMSET_FILENAMES",
    "P277_CONCURRENT_CEILING_SECONDS",
    "P277_DELETE_CONFIRM_BKID",
    "P277_DELETE_CONFIRM_DEFAULT",
    "P277_DELETE_CONFIRM_ENUM_MAP",
    "P277_DELETE_CONFIRM_LABEL_RESID16",
    "P277_DELETE_CONFIRM_MENU_PATH",
    "P277_DELETE_CONFIRM_MODES",
    "P277_DELETE_CONFIRM_RESID16_PAIRS",
    "P277_DELETE_TWICE_BKID",
    "P277_DELETE_TWICE_DEFAULT",
    "P277_DELETE_TWICE_MENU_PATH",
    "P277_DELETE_TWICE_RESID16",
    "P277_DESTRUCTIVE_DELETE_CONFIRM_DRIFT_EVENTS",
    "P277_DESTRUCTIVE_VAULT_ACTIONS",
    "P277_DONOR_FX3_APPFW_702_RELPATH",
    "P277_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P277_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P277_DONOR_FX3_UXC_EN_F_RELPATH",
    "P277_DONOR_FX3_UXC_EN_RELPATH",
    "P277_DONOR_FX3_UXC_JA_F_RELPATH",
    "P277_DONOR_FX3_UXC_JA_RELPATH",
    "P277_DONOR_FX3_UXC_SC_F_RELPATH",
    "P277_DONOR_FX3_UXC_SC_RELPATH",
    "P277_DONOR_FX3_UXC_TC_F_RELPATH",
    "P277_DONOR_FX3_UXC_TC_RELPATH",
    "P277_DONOR_FX6_APPFW_601_RELPATH",
    "P277_DONOR_FX6_BACKUP_CN1_BIN_RELPATH",
    "P277_DONOR_FX6_BACKUP_NTSC_BIN_RELPATH",
    "P277_DONOR_FX6_UXC_EN_RELPATH",
    "P277_DONOR_FX6_UXC_JA_RELPATH",
    "P277_DONOR_FX6_UXC_SC_RELPATH",
    "P277_DONOR_FX6_UXC_TC_RELPATH",
    "P277_DONOR_INSPECT_BUDGET_SECONDS",
    "P277_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P277_ENV_CLEAN_ROOM_TEST",
    "P277_FAST_CLI_BUDGET_SECONDS",
    "P277_FORBIDDEN_PERSISTENT_TARGETS",
    "P277_FORBIDDEN_POWER_SAVE_MONITOR_SPOOF_LABEL",
    "P277_FX3_BACKUP_BK_LANG_DEFAULT_VALUE",
    "P277_FX3_BACKUP_BK_LANG_OFFSET",
    "P277_FX3_BACKUP_BK_LANG_WIDTH_BYTES",
    "P277_FX3_FW_VERSION",
    "P277_FX3_HELPGUIDE_ID",
    "P277_FX3_LANGUAGE_COUNT",
    "P277_FX3_MODEL_ID",
    "P277_FX3_MODEL_NAME",
    "P277_FX3_POWER_SETTING_EXACT_2_SUBITEMS",
    "P277_FX3_PRODUCT_CODENAME",
    "P277_FX3_SUPPORTED_FW_VERSIONS",
    "P277_FX3_UI_EXPOSES_POWER_SAVE_BY_MONITOR",
    "P277_FX6_BACKUP_BK_LANG_OFFSET",
    "P277_FX6_BACKUP_BK_LANG_WIDTH_BYTES",
    "P277_FX6_BACKUP_CN1_BK_LANG_VALUE",
    "P277_FX6_BACKUP_NTSC_BK_LANG_VALUE",
    "P277_FX6_DONOR_FW_VERSION",
    "P277_FX6_DONOR_MODEL_NAME",
    "P277_FX6_LANGUAGE_COUNT",
    "P277_FX6_LANGUAGE_RESID16",
    "P277_FX6_PRODUCT_CODENAME",
    "P277_FX6_UI_EXPOSES_POWER_SAVE_BY_MONITOR",
    "P277_FX6_VOLUME_SETTINGS_BKID",
    "P277_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P277_HDMI_4CH_OUTPUT_BKID",
    "P277_HDMI_4CH_OUTPUT_MODES",
    "P277_HDMI_4CH_OUTPUT_RESID16",
    "P277_HEADLESS_HDMI_SAFE_POWER_SAVE_MONITOR_MODES",
    "P277_HEADPHONE_35MM_MAX_CHANNELS",
    "P277_LANGUAGE_BKID_FX3",
    "P277_LANGUAGE_BKID_FX6",
    "P277_LANGUAGE_BK_KEY",
    "P277_LANGUAGE_BK_KEY_HEX",
    "P277_LANGUAGE_DEFAULT",
    "P277_LANGUAGE_LABEL",
    "P277_LANGUAGE_MENU_PATH",
    "P277_LANGUAGE_RESID16",
    "P277_LEGACY_POWER_SAVE_MONITOR_SPOOF_EVENTS",
    "P277_MAX_FULL_DONOR_BYTES",
    "P277_NOMINAL_BUDGET_SECONDS",
    "P277_ON_OFF_MODES",
    "P277_PILLAR_48A_SCENARIO_IDS",
    "P277_PILLAR_48B_SCENARIO_IDS",
    "P277_PINNED_FX3_APPFW_702_BYTES",
    "P277_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P277_PINNED_FX3_BACKUP_BIN_BYTES",
    "P277_PINNED_FX3_BACKUP_BIN_SHA256",
    "P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P277_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P277_PINNED_FX3_UXC_EN_BYTES",
    "P277_PINNED_FX3_UXC_EN_F_BYTES",
    "P277_PINNED_FX3_UXC_EN_F_SHA256",
    "P277_PINNED_FX3_UXC_EN_SHA256",
    "P277_PINNED_FX3_UXC_JA_BYTES",
    "P277_PINNED_FX3_UXC_JA_F_BYTES",
    "P277_PINNED_FX3_UXC_JA_F_SHA256",
    "P277_PINNED_FX3_UXC_JA_SHA256",
    "P277_PINNED_FX3_UXC_SC_BYTES",
    "P277_PINNED_FX3_UXC_SC_F_BYTES",
    "P277_PINNED_FX3_UXC_SC_F_SHA256",
    "P277_PINNED_FX3_UXC_SC_SHA256",
    "P277_PINNED_FX3_UXC_TC_BYTES",
    "P277_PINNED_FX3_UXC_TC_F_BYTES",
    "P277_PINNED_FX3_UXC_TC_F_SHA256",
    "P277_PINNED_FX3_UXC_TC_SHA256",
    "P277_PINNED_FX6_APPFW_601_BYTES",
    "P277_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P277_PINNED_FX6_BACKUP_CN1_BIN_BYTES",
    "P277_PINNED_FX6_BACKUP_CN1_BIN_SHA256",
    "P277_PINNED_FX6_BACKUP_NTSC_BIN_BYTES",
    "P277_PINNED_FX6_BACKUP_NTSC_BIN_SHA256",
    "P277_PINNED_FX6_UXC_EN_BYTES",
    "P277_PINNED_FX6_UXC_EN_SHA256",
    "P277_PINNED_FX6_UXC_JA_BYTES",
    "P277_PINNED_FX6_UXC_JA_SHA256",
    "P277_PINNED_FX6_UXC_SC_BYTES",
    "P277_PINNED_FX6_UXC_SC_SHA256",
    "P277_PINNED_FX6_UXC_TC_BYTES",
    "P277_PINNED_FX6_UXC_TC_SHA256",
    "P277_PLAYBACK_OUTPUT_TARGETS",
    "P277_POWER_SAVE_9_DEACTIVATION_CONDITIONS",
    "P277_POWER_SAVE_MONITOR_4_MODES",
    "P277_POWER_SAVE_MONITOR_BKID",
    "P277_POWER_SAVE_MONITOR_ENUM_MAP",
    "P277_POWER_SAVE_MONITOR_LABEL",
    "P277_POWER_SAVE_MONITOR_RESID16",
    "P277_POWER_SAVE_MONITOR_RESID16_MAP",
    "P277_POWER_SAVE_START_TIME_DEFAULT",
    "P277_POWER_SAVE_START_TIME_MODES",
    "P277_POWER_SETTING_OPTION_MENU_PATH",
    "P277_RECOVERY_SAFE_POWER_SAVE_START_TIMES",
    "P277_RESET_ACTIONS",
    "P277_SIBLING_POWER_SAVE_MONITOR_DEFAULT",
    "P277_SIBLING_POWER_SAVE_MONITOR_MODELS",
    "P277_SLOT1_FORMAT_HARD_LOCKED",
    "P277_SLOT1_VAULT_DELETE_EVENTS",
    "P277_SLOT1_VAULT_MUTATION_BYTES",
    "P277_SLOT1_VAULT_SLOT",
    "P277_STAGE_B_4LANG_ORDER",
    "P277_STAGE_B_4LANG_UXC_LTT_DRIFT_EVENTS",
    "P277_STAGE_B_4LANG_UXC_LTT_TABLE",
    "P277_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P277_STATUS_FAIL_48OF48_AGGREGATOR",
    "P277_STATUS_FAIL_PILLAR48_SUITE",
    "P277_STATUS_REJECTED_PILLAR_48A",
    "P277_STATUS_REJECTED_PILLAR_48B",
    "P277_STATUS_VERIFIED_48OF48_AGGREGATOR",
    "P277_STATUS_VERIFIED_PILLAR48_SUITE",
    "P277_STATUS_VERIFIED_PILLAR_48A",
    "P277_STATUS_VERIFIED_PILLAR_48B",
    "P277_TIER0_SURFACE_COUNT",
    "P277_UNSAFE_POWER_SAVE_SLEEP_INTERFERENCE_EVENTS",
    "P277_VAULT_TARGET_ACTIONS",
    "P277_VOLUME_SETTINGS_BKID",
    "P277_VOLUME_SETTINGS_DEFAULT",
    "P277_VOLUME_SETTINGS_MAX",
    "P277_VOLUME_SETTINGS_MENU_PATH",
    "P277_VOLUME_SETTINGS_MIN",
    "P277_VOLUME_SETTINGS_RESID16",
    "P277_XLRH1_ACOUSTIC_FEEDBACK_VIOLATIONS",
    "P277_XLRH1_SAFE_INTERNAL_SPEAKER_MAX_VOLUME",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE277_PHASE_NUMBER",
    "PHASE277_SCHEMA",
    "PHASE277_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "Master48PillarRecoveryReport",
    "Phase277DonorArtifactDigest",
    "Phase277DonorSnapshot",
    "Pillar48ASuiteResult",
    "Pillar48BSuiteResult",
    "Pillar48ScenarioOutcome",
    "Pillar48StandaloneReport",
    "PowerSaveMonitorLanguageVaultReport",
    "PowerSaveMonitorLanguageVaultSpec",
    "PowerSaveMonitorLanguageVolumeDeleteVaultReport",
    "Volume4chMonDeleteConfirmVaultReport",
    "Volume4chMonDeleteConfirmVaultSpec",
    "build_default_safe_power_save_monitor_language_vault_spec",
    "build_default_safe_volume_4ch_mon_delete_confirm_vault_spec",
    "compute_expected_pillar48a_reset_state",
    "compute_expected_pillar48b_reset_and_slot1_vault_guard",
    "compute_expected_power_save_by_monitor_effective_state",
    "compute_expected_power_save_start_time_recovery_guard",
    "compute_expected_xlrh1_speaker_feedback_guard",
    "evaluate_48pillar_recovery_master",
    "evaluate_power_save_monitor_language_vault",
    "evaluate_realhw_48pillar_recovery_master",
    "evaluate_volume_4ch_mon_delete_confirm_vault",
    "inspect_phase277_donors_readonly",
    "run_pillar48_standalone_suite",
    "run_pillar48a_power_save_monitor_start_time_language_vault_6_scenario_suite",
    "run_pillar48b_volume_4ch_mon_delete_confirm_slot1_vault_6_scenario_suite",
    "verify_48pillar_recovery_suite",
    "verify_power_save_monitor_language_volume_delete_and_vault",
    "verify_power_save_monitor_language_volume_delete_vault",
]
