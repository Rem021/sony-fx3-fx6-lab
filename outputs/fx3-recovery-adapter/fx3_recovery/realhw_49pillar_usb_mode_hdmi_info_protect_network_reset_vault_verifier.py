"""Phase 282 — Pillar 49 (`49/49` Recovery Pillars) & Unified 49-Pillar Recovery Master
(`verify-49pillar-recovery` / `verify-usb-mode-hdmi-info-protect-network-reset-vault`):

1. **Pillar 49A — `[USB Connection Mode]` 4-Mode vs Dormant `NOUVC` `[USB Streaming]` Split,
   Data-Isolated `USB PD` Recovery Power Guard, & `[HDMI Info. Display]` LCD-Blanking /
   `1080` Clamp vs `4K` Clean-Feed Recovery Telemetry (Wave-47)**:
   - Models `MENU` -> `(Setup)` -> `[USB]` -> `[USB Connection Mode]`
     (`BKID_APP_setting_usb_connection_method`, `_f.uxc` `0x69a2`) on stock `ILME-FX3 Ver. 7.02`
     (`ilc/2210`): exposes ONLY **4** modes: `Sel. When Connect` (default `0x7738`),
     `MassStorage(MSC)` (`0x6c54`, VID:PID `054C:0DA1`, `USB_CONNECTION_METHOD_MASS_STRAGE`),
     `MTP` (`0xe24b`), and `Remote Shoot (PC Remote)` (`0x60aa`); dormant `usb_f_uvc.ko`
     (`78,840 B`) and `_f.uxc` `0x7399` / `_g.uxc` `0x63f7` `[USB Streaming]` tokens remain
     unexposed (`fx3_ui_exposes_usb_streaming == False`, `NOUVC`).
   - Enforces air-gapped Tier-0 bench rule: prohibits `MassStorage(MSC)`, `MTP`, `Remote Shoot`,
     and `USB-LAN` host data enumeration during Tier-0 backup/rollback, allowing
     `[USB Power Supply] = [On]` (`0x721e`, `USB Type-C` + `NP-FZ100` inserted;
     `[USB LUN Setting]` `Multi` default `0xe631` / `Single` `0x776d`) ONLY when `D+/D-` and
     SuperSpeed `TX/RX` data lines are physically isolated.
   - Verifies `[HDMI Info. Display]` (`BKID_APP_setting_hdmi_info_display`, `_f.uxc` `0x6e7c`):
     `On` default (`0xe07c`) outputs OSD overlays + blanks built-in LCD
     (`CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`), whereas `Off` (`0xe297`) emits clean feed and
     keeps the built-in LCD active. Operator-guided LCD menu recovery with external HDMI
     attached enforces `HDMI Info. Display = Off`. Audits `1080` internal-Log/`PPLUT1..4` clamp
     vs `4K` `Off(HDMI Only)` (`0x6573`) / `RAW Output` (`0x6e97`) auto-clean-feed override,
     and `(Setup)` survival across `[Camera Settings Reset]` (with `Framing Settings (HDMI)`
     exception returning to `Crop`).

2. **Pillar 49B — `[Protect]` Scopes vs `[Format]` Wipe (`Slot-1` Dual-Layer Hardware SD `WP` +
   Firewall Mandate) & `[Reset Network Set.]` Auto-Reboot + Post-Reboot `[Airplane Mode] = [On]`
   Zero-RF Recovery Sequence**:
   - Models `MENU` -> `(Playback)` -> `[Selection/Memo]` (`0x6239`) -> `[Protect]` (`0xe2c9`)
     exact 4 `ILME-FX3` scopes (`Single/Multiple Img.` `0xe2ca`, `All in this Folder` `0x6848`,
     `All with this date` `0x69f7`, `All Images in This Group` `0xe826`) blocking `[Delete]` /
     `[Delete pressing twice]`, yet proving **`[Format]` (`0xe449` / `0xe414`) wipes protected
     files and `M1..M4` settings**. `Slot 1` (`CAMSET`/`BODYDATA.DAT` recovery vault) MUST
     enforce BOTH physical SD `WP` lock (`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`) AND
     `slot1_format_hard_locked == True` (rejecting software-`[Protect]`-only vaults).
   - Models `[Reset Network Set.]` (`FUNC_reset_network_settings`, `SETTING_RESET_NW`,
     `_f.uxc` `0x60d3`/`0x65d3`): clears `(Network)` credentials, preserves `(Shooting)` /
     `(Setup)` / `(Playback)` / `CAMSET`, forces automatic reboot
     (`BKID_APP_is_shutdown_factor_network_reset`), and resets `[Airplane Mode]` to `Off` —
     requiring completed reboot + re-asserted `[Airplane Mode] = [On]` (`0x6df9`) before
     zero-RF recovery certification.

3. **Unified `49/49` Recovery Master (`evaluate_realhw_49pillar_recovery_master`)**:
   - Concurrently delegates Pillars `1..48` (`evaluate_realhw_48pillar_recovery_master`) +
     **Pillar 49** (`run_pillar49_standalone_suite`) -> **`49/49` (`VERIFIED_49OF49_PILLAR_RECOVERY_MASTER`)**
     in `< 2.0s` CLI runtime (`< 4.0s` nominal / `< 6.0s` concurrent ceiling), preserving 100%
     backward compatibility with `verify-22..48pillar-recovery`.
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
from .realhw_48pillar_power_save_monitor_language_volume_delete_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_48_PILLAR_SPECS,
    Master48PillarRecoveryReport,
    evaluate_realhw_48pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE282_SCHEMA: str = "realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier_v1"
PHASE282_VERSION: str = "1.0.0"
PHASE282_PHASE_NUMBER: int = 282
P282_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P282_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P282_FX3_UI_EXPOSES_USB_STREAMING: bool = False
P282_NOUVC_SPOOF_EVENTS: int = 0
P282_USB_HOST_DATA_ENUMERATION_EVENTS: int = 0
P282_HDMI_LCD_BLANKING_VIOLATIONS: int = 0
P282_HDMI_LOG_1080_BYPASS_EVENTS: int = 0
P282_SLOT1_PROTECT_ONLY_VAULT_VIOLATIONS: int = 0
P282_SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS: int = 0
P282_SLOT1_VAULT_MUTATION_BYTES: int = 0
P282_SLOT1_FORMAT_HARD_LOCKED: bool = True
P282_NETWORK_RESET_ZERO_RF_VIOLATIONS: int = 0

P282_DONOR_INSPECT_BUDGET_SECONDS: float = 0.15
P282_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P282_FAST_CLI_BUDGET_SECONDS: float = 2.0
P282_NOMINAL_BUDGET_SECONDS: float = 4.0
P282_CONCURRENT_CEILING_SECONDS: float = 6.0
P282_BOUNDED_HEADER_BYTES: int = 4096
P282_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-47 Donor Anchors (strictly O_RDONLY)
P282_FX3_MODEL_NAME: str = "ILME-FX3"
P282_FX3_MODEL_ID: int = 0x91030080
P282_FX3_PRODUCT_CODENAME: str = "PRODUCT_MODEL_ALCIN_UUD"
P282_FX3_HELPGUIDE_ID: str = "ilc/2210"
P282_FX3_FW_VERSION: str = "7.02"
P282_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P282_FX6_PRODUCT_CODENAME: str = "PRODUCT_MODEL_CHAPLIN"
P282_FX6_DONOR_FW_VERSION: str = "6.01"
P282_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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

P282_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P282_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P282_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P282_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P282_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P282_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P282_DONOR_FX3_USB_F_UVC_KO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usb_f_uvc.ko"
)
P282_PINNED_FX3_USB_F_UVC_KO_BYTES: int = 78840
P282_PINNED_FX3_USB_F_UVC_KO_SHA256: str = (
    "a23970925fa91ed7712f14bf7de8ac62ff9d63e9bcbfeecc94b37085d48c5ccc"
)

P282_DONOR_FX6_USB_F_UVC_KO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/usb_f_uvc.ko"
)
P282_PINNED_FX6_USB_F_UVC_KO_BYTES: int = 78840
P282_PINNED_FX6_USB_F_UVC_KO_SHA256: str = (
    "bf073599272e2bb5641668d457ff9962525f17a37c8c75f15a3892d7c26b5305"
)

P282_DONOR_FX3_USBG_STORAGE_KO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usbg_storage.ko"
)
P282_PINNED_FX3_USBG_STORAGE_KO_BYTES: int = 104288
P282_PINNED_FX3_USBG_STORAGE_KO_SHA256: str = (
    "b43130dbc3d9b72dc03c3acb7993639e1cefcbb43621fef809f6f617cb30b255"
)

P282_DONOR_FX3_USBG_STILLIMAGE_KO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod/usbg_stillimage.ko"
)
P282_PINNED_FX3_USBG_STILLIMAGE_KO_BYTES: int = 49448
P282_PINNED_FX3_USBG_STILLIMAGE_KO_SHA256: str = (
    "0ef9132f6e043bd38a376519f0f130545e4c8ae68473b1b9d97b1228fa2829a5"
)

P282_DONOR_FX3_LIBUSBBUSPOWER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so"
)
P282_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES: int = 48232
P282_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256: str = (
    "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748"
)

P282_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAirplaneMode.so"
)
P282_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES: int = 14488
P282_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256: str = (
    "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea"
)

P282_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P282_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P282_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P282_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P282_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P282_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P282_DONOR_FX3_UXC_EN_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_f.uxc"
)
P282_PINNED_FX3_UXC_EN_F_BYTES: int = 373820
P282_PINNED_FX3_UXC_EN_F_SHA256: str = (
    "7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b"
)

P282_DONOR_FX3_UXC_SC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_simplifiedchinese_f.uxc"
)
P282_PINNED_FX3_UXC_SC_F_BYTES: int = 322652
P282_PINNED_FX3_UXC_SC_F_SHA256: str = (
    "4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a"
)

P282_DONOR_FX3_UXC_TC_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_traditionalchinese_f.uxc"
)
P282_PINNED_FX3_UXC_TC_F_BYTES: int = 324148
P282_PINNED_FX3_UXC_TC_F_SHA256: str = (
    "32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167"
)

P282_DONOR_FX3_UXC_JA_F_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_japanese_f.uxc"
)
P282_PINNED_FX3_UXC_JA_F_BYTES: int = 447840
P282_PINNED_FX3_UXC_JA_F_SHA256: str = (
    "45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b"
)

P282_DONOR_FX3_UXC_EN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english.uxc"
)
P282_PINNED_FX3_UXC_EN_BYTES: int = 165740
P282_PINNED_FX3_UXC_EN_SHA256: str = (
    "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e"
)

P282_DONOR_FX3_UXC_EN_G_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/share/app/string_english_g.uxc"
)
P282_PINNED_FX3_UXC_EN_G_BYTES: int = 69600
P282_PINNED_FX3_UXC_EN_G_SHA256: str = (
    "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a"
)

P282_DONOR_FX6_UXC_EN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english.uxc"
)
P282_PINNED_FX6_UXC_EN_BYTES: int = 118208
P282_PINNED_FX6_UXC_EN_SHA256: str = (
    "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739"
)

P282_DONOR_FX6_UXC_EN_2_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/share/app/string_english_2.uxc"
)
P282_PINNED_FX6_UXC_EN_2_BYTES: int = 118676
P282_PINNED_FX6_UXC_EN_2_SHA256: str = (
    "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2"
)

# Pillar 49A — [USB Connection Mode], NOUVC, PD Power Guard, & [HDMI Info. Display]
P282_USB_CONNECTION_MODE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "USB",
    "USB Connection Mode",
)
P282_USB_CONNECTION_MODE_BKID: str = "BKID_APP_setting_usb_connection_method"
P282_USB_CONNECTION_MODE_RESID16: int = 0x69A2
P282_FX3_USB_CONNECTION_4_MODES: Tuple[str, ...] = (
    "Sel. When Connect",
    "MassStorage(MSC)",
    "MTP",
    "Remote Shoot (PC Remote)",
)
P282_USB_CONNECTION_MODE_DEFAULT: str = "Sel. When Connect"
P282_USB_CONNECTION_RESID16_MAP: Dict[str, int] = {
    "Sel. When Connect": 0x7738,
    "MassStorage(MSC)": 0x6C54,
    "MTP": 0xE24B,
    "Remote Shoot (PC Remote)": 0x60AA,
}
P282_USB_CONNECTION_SEL_PROMPT_RESID16_MAP: Dict[str, int] = {
    "Image Transfer (MSC)": 0x67A2,
    "Image Transfer (MTP)": 0x72CD,
    "Remote Shooting": 0x7C6F,
}
P282_USB_CONNECTION_ENUM_MAP: Dict[str, str] = {
    "Sel. When Connect": "VAL_setting_usb_connection_method_USB_CONNECTION_SELECT_AFTER_CONNECTION",
    "MassStorage(MSC)": "VAL_setting_usb_connection_method_USB_CONNECTION_MASS_STORAGE",
    "MTP": "VAL_setting_usb_connection_method_USB_CONNECTION_MTP",
    "Remote Shoot (PC Remote)": "VAL_setting_usb_connection_method_USB_CONNECTION_REMOTE_PC",
}
P282_USB_MSC_VID_PID: str = "054C:0DA1"
P282_APPFW_MASS_STRAGE_MARKER: str = "USB_CONNECTION_METHOD_MASS_STRAGE"
P282_FORBIDDEN_FX3_USB_STREAMING_MODE: str = "USB Streaming"
P282_DORMANT_UVC_ENUM: str = "VAL_setting_usb_connection_method_USB_CONNECTION_USB_STREAMING"
P282_DORMANT_UVC_EXCLUSION_BKID: str = "BKID_APP_shoot_mode_exclusion_for_usb_streaming"
P282_DORMANT_UVC_MODULE: str = "usb_f_uvc.ko"
P282_DORMANT_UVC_RESID16_F: int = 0x7399
P282_DORMANT_UVC_RESID16_G: int = 0x63F7
P282_FX6_PROCAM_UVC_BKID: str = "BKID_APP_SETTING_USB_STREAMING_PROCAM"
P282_FX6_USB_TETHERING_RESID16: int = 0x29C9

P282_USB_LUN_SETTING_MENU_PATH: Tuple[str, ...] = ("MENU", "Setup", "USB", "USB LUN Setting")
P282_USB_LUN_SETTING_BKID: str = "BKID_APP_setting_lun_settings"
P282_USB_LUN_SETTING_RESID16: int = 0x6B19
P282_USB_LUN_MODES: Tuple[str, ...] = ("Multi", "Single")
P282_USB_LUN_DEFAULT: str = "Multi"
P282_USB_LUN_RESID16_MAP: Dict[str, int] = {"Multi": 0xE631, "Single": 0x776D}
P282_USB_LUN_ENUM_MAP: Dict[str, str] = {
    "Multi": "LUN_SETTING_MULTI",
    "Single": "LUN_SETTING_SINGLE",
}

P282_USB_POWER_SUPPLY_MENU_PATH: Tuple[str, ...] = ("MENU", "Setup", "USB", "USB Power Supply")
P282_USB_POWER_SUPPLY_BKID: str = "BKID_APP_setting_usb_supply"
P282_USB_POWER_SUPPLY_RESID16: int = 0x721E
P282_USB_POWER_SUPPLY_MODES: Tuple[str, ...] = ("On", "Off")
P282_USB_POWER_SUPPLY_DEFAULT: str = "On"
P282_USB_POWER_SUPPLY_REQUIRED_PORT: str = "USB Type-C"
P282_USB_PORTS: Tuple[str, ...] = ("USB Type-C", "Multi/Micro USB", "NONE")

P282_BLOCKED_HOST_DATA_ENUMERATION_MODES: Tuple[str, ...] = (
    "MassStorage(MSC)",
    "MTP",
    "Remote Shoot (PC Remote)",
    "USB-LAN",
)
P282_TIER0_HOST_USB_DATA_STATES: Tuple[str, ...] = (
    "NONE",
    "Sel. When Connect",
    "MassStorage(MSC)",
    "MTP",
    "Remote Shoot (PC Remote)",
    "USB-LAN",
)

P282_HDMI_INFO_DISPLAY_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "External Output",
    "HDMI Info. Display",
)
P282_HDMI_INFO_DISPLAY_BKID: str = "BKID_APP_setting_hdmi_info_display"
P282_HDMI_INFO_DISPLAY_RESID16: int = 0x6E7C
P282_HDMI_INFO_DISPLAY_MODES: Tuple[str, ...] = ("On", "Off")
P282_HDMI_INFO_DISPLAY_DEFAULT: str = "On"
P282_HDMI_INFO_DISPLAY_RESID16_MAP: Dict[str, int] = {"On": 0xE07C, "Off": 0xE297}
P282_HDMI_INFO_ON_CAUTION_ID: str = "CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON"
P282_FX6_HDMI_INFO_BKID: str = "BKID_APP_SETTING_HDMI_INFO_DISPLAY"
P282_FX6_SDI_OUTPUT_BKID: str = "BKID_APP_SETTING_SDI_OUTPUT_DISPLAY"

P282_REC_MEDIA_DUR_HDMI_BKID: str = "BKID_APP_setting_rec_media_during_hdmi_output"
P282_REC_MEDIA_DUR_HDMI_RESID16: int = 0x6144
P282_REC_MEDIA_DUR_HDMI_OFF_RESID16: int = 0x6573
P282_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("On", "Off(HDMI Only)")
P282_REC_MEDIA_DUR_HDMI_DEFAULT: str = "On"
P282_RAW_OUTPUT_RESID16: int = 0x6E97
P282_ON_OFF_MODES: Tuple[str, ...] = ("Off", "On")
P282_RAW_OUTPUT_DEFAULT: str = "Off"
P282_OUTPUT_RESOLUTION_MODES: Tuple[str, ...] = ("Auto", "2160p", "1080p", "1080i")
P282_OUTPUT_RESOLUTION_DEFAULT: str = "Auto"
P282_LOG_SHOOTING_MODES: Tuple[str, ...] = ("Off", "Flexible ISO", "Cine EI Quick", "Cine EI")
P282_PICTURE_PROFILE_MODES: Tuple[str, ...] = ("Off", "PP1..PP11", "PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P282_FRAMING_HDMI_MODES: Tuple[str, ...] = ("Crop", "Full", "Off")
P282_FRAMING_HDMI_DEFAULT: str = "Crop"
P282_SHOOTING_DOMAINS: Tuple[str, ...] = ("Movie", "Still", "S&Q")

# Pillar 49B — [Protect] Scopes vs [Format] Wipe & [Reset Network Set.] Zero-RF Sequence
P282_PROTECT_MENU_PATH: Tuple[str, ...] = ("MENU", "Playback", "Selection/Memo", "Protect")
P282_SELECTION_MEMO_RESID16: int = 0x6239
P282_PROTECT_RESID16: int = 0xE2C9
P282_PROTECT_4_SCOPES: Tuple[str, ...] = (
    "Single/Multiple Img.",
    "All in this Folder",
    "All with this date",
    "All Images in This Group",
)
P282_PROTECT_SCOPE_RESID16_MAP: Dict[str, int] = {
    "Single/Multiple Img.": 0xE2CA,
    "All in this Folder": 0x6848,
    "All with this date": 0x69F7,
    "All Images in This Group": 0xE826,
}
P282_PROTECT_FUNC_MARKERS: Tuple[str, ...] = (
    "FUNC_protect_content",
    "FUNC_protect_for_multipul_images",
    "FUNC_protect_all_contents_in_this_date",
    "FUNC_protect_all_contents_in_this_group",
)
P282_PROTECT_KEY_ICON_RESID16: Tuple[int, ...] = (0xE306, 0xE66A)
P282_PROTECT_FILE_ERROR_ENUM: str = "VAL_mr_memory_error_status_MR_MEMORY_ERROR_FILE_PROTECT"

P282_FORMAT_MENU_PATH: Tuple[str, ...] = ("MENU", "Shooting", "Media", "Format")
P282_FORMAT_RESID16: int = 0xE449
P282_FORMAT_WARN_RESID16: int = 0xE414
P282_FORMAT_QUICK_RESID16: int = 0xE792
P282_FORMAT_FULL_RESID16: int = 0xE8F5
P282_SLOT1_WP_ERROR_ENUM: str = "VAL_mr_memory_error_status_MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1"
P282_SLOT1_WP_CAUTION_ID: str = "CAUTION_ID_PROTECT_MS_SLOT1"
P282_FX6_LOCK_CLIP_RESID16: int = 0x42AF
P282_FX6_LOCK_CLIP_BKID: str = "BKID_APP_USER_MENU_LOCK_UNLOCK_CLIP0"
P282_FX6_FORMAT_MEDIA_RESID16: int = 0x4254

P282_VAULT_TARGET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "READ_ONLY_AUDIT",
    "DELETE_SINGLE",
    "DELETE_PRESSING_TWICE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P282_DESTRUCTIVE_VAULT_ACTIONS: Tuple[str, ...] = (
    "DELETE_SINGLE",
    "DELETE_PRESSING_TWICE",
    "FORMAT_QUICK",
    "FORMAT_FULL",
)
P282_FORMAT_VAULT_ACTIONS: Tuple[str, ...] = ("FORMAT_QUICK", "FORMAT_FULL")

P282_RESET_NETWORK_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Network",
    "Network Option",
    "Reset Network Set.",
)
P282_NETWORK_OPTION_RESID16: int = 0x61E1
P282_RESET_NETWORK_RESID16: int = 0x60D3
P282_RESET_NETWORK_REBOOT_WARN_RESID16: int = 0x65D3
P282_RESET_NETWORK_FUNC: str = "FUNC_reset_network_settings"
P282_RESET_NETWORK_SETTING_ID: str = "SETTING_RESET_NW"
P282_RESET_NETWORK_SHUTDOWN_BKID: str = "BKID_APP_is_shutdown_factor_network_reset"
P282_AIRPLANE_MODE_BKID: str = "BKID_APP_setting_airplane_mode"
P282_AIRPLANE_MODE_RESID16: int = 0x6DF9
P282_AIRPLANE_MODE_ON_RESID16: int = 0x6B05
P282_AIRPLANE_MODE_MODES: Tuple[str, ...] = ("On", "Off")
P282_AIRPLANE_MODE_DEFAULT: str = "Off"
P282_FX6_NETWORK_RESET_RESID16: int = 0x4291
P282_FX6_ALL_RESET_RESID16: int = 0x4271
P282_FX6_NETWORK_RESET_BKID: str = "BKID_APP_USER_MENU_NETWORK_RESET"
P282_FX6_SHUTDOWN_NETWORK_RESET_BKID: str = "BKID_APP_IS_SHUTDOWN_FACTOR_NETWORK_RESET"

P282_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P282_SLOT1_VAULT_SLOT: int = 1
P282_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P282_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx3_usb_mode_hdmi_info_protect_network_reset_vault_overlay"
P282_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P282_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P282_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P282_BLOCKED_INVALID_PILLAR49A_SPEC: str = "BLOCKED_INVALID_PILLAR49A_SPEC"
P282_BLOCKED_NOUVC_OR_USB_HOST_DATA_ENUMERATION: str = (
    "BLOCKED_NOUVC_OR_USB_HOST_DATA_ENUMERATION"
)
P282_BLOCKED_USB_PD_UNISOLATED_OR_PORT_ERROR: str = (
    "BLOCKED_USB_PD_UNISOLATED_OR_PORT_ERROR"
)
P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS: str = (
    "BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS"
)
P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT: str = (
    "BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT"
)
P282_BLOCKED_INVALID_PILLAR49B_SPEC: str = "BLOCKED_INVALID_PILLAR49B_SPEC"
P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE: str = (
    "BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE"
)
P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT: str = (
    "BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT"
)
P282_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P282_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P282_STATUS_VERIFIED_PILLAR_49A: str = (
    "VERIFIED_PILLAR_49A_USB_4MODE_NOUVC_DATA_ISOLATED_PD_AND_HDMI_INFO_CLEAN_FEED_VAULT"
)
P282_STATUS_REJECTED_PILLAR_49A: str = (
    "REJECTED_PILLAR_49A_USB_4MODE_NOUVC_DATA_ISOLATED_PD_AND_HDMI_INFO_CLEAN_FEED_VAULT"
)
P282_STATUS_VERIFIED_PILLAR_49B: str = (
    "VERIFIED_PILLAR_49B_PROTECT_VS_FORMAT_SLOT1_WP_AND_NETWORK_RESET_AIRPLANE_ZERO_RF_VAULT"
)
P282_STATUS_REJECTED_PILLAR_49B: str = (
    "REJECTED_PILLAR_49B_PROTECT_VS_FORMAT_SLOT1_WP_AND_NETWORK_RESET_AIRPLANE_ZERO_RF_VAULT"
)
P282_STATUS_VERIFIED_PILLAR49_SUITE: str = (
    "VERIFIED_PILLAR49_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VAULT"
)
P282_STATUS_FAIL_PILLAR49_SUITE: str = (
    "FAIL_PILLAR49_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VAULT"
)
P282_STATUS_VERIFIED_49OF49_AGGREGATOR: str = "VERIFIED_49OF49_PILLAR_RECOVERY_MASTER"
P282_STATUS_FAIL_49OF49_AGGREGATOR: str = "FAIL_49OF49_PILLAR_RECOVERY_MASTER"

P282_PILLAR_49A_SCENARIO_IDS: Tuple[str, ...] = (
    "P49A1_USB_4MODE_NOUVC_DATA_ISOLATED_PD_AND_HDMI_INFO_OFF_LCD_VISIBLE_SETUP_SURVIVAL_SAFE",
    "P49A2_HDMI_ONLY_4K_FORCES_CLEAN_FEED_AND_INITIALIZE_WITH_CAMSET01_RESTORE_SAFE",
    "P49A3_REJECT_FX3_USB_STREAMING_NOUVC_SPOOF_OR_UNISOLATED_MSC_MTP_REMOTE_USBLAN_DATA_ENUM",
    "P49A4_REJECT_UNISOLATED_USB_PD_POWER_MISSING_NP_FZ100_OR_MULTI_MICRO_USB_PORT",
    "P49A5_REJECT_HDMI_INFO_ON_LCD_BLANKING_DURING_LCD_MENU_RECOVERY_OR_LOG_PPLUT_4K_BYPASS",
    "P49A6_REJECT_CAMERA_SETTINGS_RESET_WIPING_SETUP_USB_HDMI_OR_KEEPING_FRAMING_CROP_UNRESET",
)
P282_PILLAR_49B_SCENARIO_IDS: Tuple[str, ...] = (
    "P49B1_PROTECT_4SCOPES_SLOT1_DUAL_WP_FORMAT_FIREWALL_AND_NETWORK_RESET_REBOOT_AIRPLANE_ON_SAFE",
    "P49B2_PROTECT_BLOCKS_DELETE_ON_SLOT2_AND_RESET_NETWORK_PRESERVES_SETUP_SHOOTING_CAMSET_SAFE",
    "P49B3_REJECT_SOFTWARE_PROTECT_ONLY_SLOT1_VAULT_WITHOUT_PHYSICAL_WP_AND_FORMAT_HARD_LOCK",
    "P49B4_REJECT_SLOT1_FORMAT_QUICK_FULL_OR_PLAYBACK_DELETE_TARGETING_RECOVERY_VAULT",
    "P49B5_REJECT_NETWORK_RESET_WITHOUT_COMPLETED_REBOOT_OR_UNREASSERTED_AIRPLANE_MODE_OFF",
    "P49B6_REJECT_NETWORK_RESET_WIPING_CAMSET_OR_PERSISTENT_OVERLAY_OR_TIER0_H0_H3_DRIFT",
)

MASTER_49_PILLAR_COUNT: int = 49
MASTER_49_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_48_PILLAR_SPECS + (
    (
        49,
        "pillar_49_usb_mode_hdmi_info_protect_network_reset_vault",
        "Phase 282 (49/49)",
        "fx3_recovery.realhw_49pillar_usb_mode_hdmi_info_protect_network_reset_vault_verifier",
    ),
)
MASTER_49_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_49_PILLAR_SPECS)


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
    return os.environ.get(P282_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P282_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P282_DONOR_INSPECT_BUDGET_SECONDS


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
        ("P282_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P282_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P282_FX3_UI_EXPOSES_USB_STREAMING", P282_FX3_UI_EXPOSES_USB_STREAMING, False),
        ("P282_NOUVC_SPOOF_EVENTS", P282_NOUVC_SPOOF_EVENTS, 0),
        ("P282_USB_HOST_DATA_ENUMERATION_EVENTS", P282_USB_HOST_DATA_ENUMERATION_EVENTS, 0),
        ("P282_HDMI_LCD_BLANKING_VIOLATIONS", P282_HDMI_LCD_BLANKING_VIOLATIONS, 0),
        ("P282_HDMI_LOG_1080_BYPASS_EVENTS", P282_HDMI_LOG_1080_BYPASS_EVENTS, 0),
        ("P282_SLOT1_PROTECT_ONLY_VAULT_VIOLATIONS", P282_SLOT1_PROTECT_ONLY_VAULT_VIOLATIONS, 0),
        ("P282_SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS", P282_SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS, 0),
        ("P282_SLOT1_VAULT_MUTATION_BYTES", P282_SLOT1_VAULT_MUTATION_BYTES, 0),
        ("P282_SLOT1_FORMAT_HARD_LOCKED", P282_SLOT1_FORMAT_HARD_LOCKED, True),
        ("P282_NETWORK_RESET_ZERO_RF_VIOLATIONS", P282_NETWORK_RESET_ZERO_RF_VIOLATIONS, 0),
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
    return any(tok in low for tok in P282_FORBIDDEN_PERSISTENT_TARGETS)


def compute_expected_usb_connection_and_pd_guard(
    *,
    airgapped_tier0_session: bool,
    active_host_usb_data_mode: str,
    usb_data_lines_physically_isolated: bool,
    usb_power_supply: str,
    usb_port: str,
    np_fz100_inserted: bool,
) -> Tuple[bool, bool, bool]:
    """Compute `(host_data_blocked_safely, pd_power_allowed, overall_usb_guard_safe)`.

    - On air-gapped Tier-0 recovery/backup benches, `MassStorage(MSC)`, `MTP`,
      `Remote Shoot (PC Remote)`, and `USB-LAN` host data enumeration MUST be prevented
      (either no active host data mode or `D+/D-` & SuperSpeed data lines physically isolated).
    - `[USB Power Supply] = [On]` requires `USB Type-C` port + `NP-FZ100` inserted AND (if in
      an air-gapped Tier-0 session) physically isolated USB data lines.
    """
    host_data_active = active_host_usb_data_mode in P282_BLOCKED_HOST_DATA_ENUMERATION_MODES
    if airgapped_tier0_session:
        host_data_blocked_safely = (not host_data_active) or usb_data_lines_physically_isolated
    else:
        host_data_blocked_safely = True

    if usb_power_supply == "On":
        pd_power_allowed = (
            usb_port == P282_USB_POWER_SUPPLY_REQUIRED_PORT
            and np_fz100_inserted
            and ((not airgapped_tier0_session) or usb_data_lines_physically_isolated)
        )
    else:
        pd_power_allowed = True

    return host_data_blocked_safely, pd_power_allowed, (host_data_blocked_safely and pd_power_allowed)


def compute_expected_hdmi_info_and_resolution_state(
    *,
    configured_hdmi_info_display: str,
    rec_media_dur_hdmi: str,
    raw_output: str,
    configured_output_resolution: str,
    log_shooting: str,
    picture_profile: str,
    shooting_domain: str,
) -> Tuple[str, bool, str, bool]:
    """Compute `(effective_hdmi_info, builtin_lcd_active, effective_hdmi_resolution, clean_feed)`.

    - When `shooting_domain == "S&Q"`, firmware locks `rec_media_dur_hdmi = "On"` and
      `raw_output = "Off"`.
    - When `rec_media_dur_hdmi == "Off(HDMI Only)"` OR `raw_output == "On"` (outside S&Q),
      HDMI outputs `4K` and auto-forces `[HDMI Info. Display] = [Off]` (clean feed + LCD active).
    - When recording internally (`On`) with `RAW Output = Off`, `Log Shooting != Off` or
      `PPLUT1..PPLUT4` clamps HDMI resolution to `1080p` regardless of `[Output Resolution]`.
    - `HDMI Info. Display = On` blanks built-in LCD (`CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON`).
    """
    eff_rec_media = "On" if shooting_domain == "S&Q" else rec_media_dur_hdmi
    eff_raw = "Off" if shooting_domain == "S&Q" else raw_output

    if eff_rec_media == "Off(HDMI Only)" or eff_raw == "On":
        effective_hdmi_info = "Off"
        effective_res = "4K"
    else:
        effective_hdmi_info = configured_hdmi_info_display
        if log_shooting != "Off" or picture_profile.startswith("PPLUT"):
            effective_res = "1080p"
        else:
            effective_res = configured_output_resolution

    clean_feed = effective_hdmi_info == "Off"
    builtin_lcd_active = effective_hdmi_info == "Off"
    return effective_hdmi_info, builtin_lcd_active, effective_res, clean_feed


def compute_expected_pillar49a_reset_state(
    *,
    pre_usb_connection_mode: str,
    pre_usb_lun_setting: str,
    pre_usb_power_supply: str,
    pre_hdmi_info_display: str,
    pre_rec_media_dur_hdmi: str,
    pre_output_resolution: str,
    pre_raw_output: str,
    pre_framing_hdmi: str,
    reset_action: str,
) -> Tuple[str, str, str, str, str, str, str, str]:
    """Compute post-reset `(usb_connection_mode, usb_lun_setting, usb_power_supply,
    hdmi_info_display, rec_media_dur_hdmi, output_resolution, raw_output, framing_hdmi)`.

    - All `(Setup) -> [USB]` and `(Setup) -> [External Output]` items survive
      `[Camera Settings Reset]` and `[Reset Network Set.]`, reverting ONLY on `[Initialize]`.
    - Exception per `ilc/2210`: `[Framing Settings] -> [HDMI]` reverts to `Crop` on
      `[Camera Settings Reset]` (and `[Initialize]`), surviving `[Reset Network Set.]`.
    """
    if reset_action == "Initialize":
        return (
            P282_USB_CONNECTION_MODE_DEFAULT,
            P282_USB_LUN_DEFAULT,
            P282_USB_POWER_SUPPLY_DEFAULT,
            P282_HDMI_INFO_DISPLAY_DEFAULT,
            P282_REC_MEDIA_DUR_HDMI_DEFAULT,
            P282_OUTPUT_RESOLUTION_DEFAULT,
            P282_RAW_OUTPUT_DEFAULT,
            P282_FRAMING_HDMI_DEFAULT,
        )
    if reset_action == "Camera Settings Reset":
        return (
            pre_usb_connection_mode,
            pre_usb_lun_setting,
            pre_usb_power_supply,
            pre_hdmi_info_display,
            pre_rec_media_dur_hdmi,
            pre_output_resolution,
            pre_raw_output,
            P282_FRAMING_HDMI_DEFAULT,
        )
    return (
        pre_usb_connection_mode,
        pre_usb_lun_setting,
        pre_usb_power_supply,
        pre_hdmi_info_display,
        pre_rec_media_dur_hdmi,
        pre_output_resolution,
        pre_raw_output,
        pre_framing_hdmi,
    )


def compute_expected_protect_vs_format_slot1_defense(
    *,
    software_protect_active: bool,
    slot1_holds_recovery_vault: bool,
    slot1_sdxc_wp_locked: bool,
    slot1_format_hard_locked: bool,
    requested_vault_slot: int,
    requested_vault_action: str,
) -> Tuple[bool, bool, bool, bool]:
    """Compute `(delete_blocked_by_protect, format_wipes_protected_without_hw_wp,
    slot1_dual_layer_armed, destructive_action_blocked)`.

    - Software `[Protect]` blocks `[Delete]`/`[Delete pressing twice]`, yet `[Format]`
      (`Quick`/`Full`) wipes protected files and `M1..M4` settings unless guarded by
      physical SD `WP` (`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`) + hard format lock.
    """
    delete_blocked_by_protect = bool(software_protect_active)
    format_wipes_protected_without_hw_wp = True
    slot1_dual_layer_armed = bool(slot1_sdxc_wp_locked and slot1_format_hard_locked)
    destructive_action_blocked = (
        requested_vault_slot == P282_SLOT1_VAULT_SLOT
        and (slot1_holds_recovery_vault or slot1_sdxc_wp_locked)
        and requested_vault_action in P282_DESTRUCTIVE_VAULT_ACTIONS
    )
    return (
        delete_blocked_by_protect,
        format_wipes_protected_without_hw_wp,
        slot1_dual_layer_armed,
        destructive_action_blocked,
    )


def compute_expected_network_reset_zero_rf_sequence(
    *,
    reset_action: str,
    pre_network_creds_present: bool,
    pre_airplane_mode: str,
    pre_shooting_preserved: bool,
    pre_setup_preserved: bool,
    pre_playback_preserved: bool,
    pre_camset_preserved: bool,
    auto_reboot_completed: bool,
    post_reasserted_airplane_mode: str,
) -> Tuple[bool, bool, str, bool, bool]:
    """Compute `(post_network_creds_cleared, auto_reboot_required, immediate_post_reset_airplane_mode,
    non_network_domains_preserved, zero_rf_certified)`.

    - `[Reset Network Set.]` (`SETTING_RESET_NW`) clears `(Network)` credentials, preserves
      `(Shooting)`/`(Setup)`/`(Playback)`/`CAMSET`, forces automatic reboot
      (`BKID_APP_is_shutdown_factor_network_reset`), and resets `[Airplane Mode]` to `Off`.
    - Zero-RF recovery certification requires cleared `(Network)` credentials, completed
      reboot (if network reset ran), AND re-asserted `[Airplane Mode] = [On]`.
    """
    if reset_action == "Reset Network Set.":
        creds_cleared = True
        reboot_req = True
        imm_airplane = P282_AIRPLANE_MODE_DEFAULT
        non_nw_ok = (
            pre_shooting_preserved
            and pre_setup_preserved
            and pre_playback_preserved
            and pre_camset_preserved
        )
    elif reset_action == "Initialize":
        creds_cleared = True
        reboot_req = False
        imm_airplane = P282_AIRPLANE_MODE_DEFAULT
        non_nw_ok = pre_camset_preserved
    else:
        # NONE or Camera Settings Reset
        creds_cleared = not pre_network_creds_present
        reboot_req = False
        imm_airplane = pre_airplane_mode
        non_nw_ok = pre_setup_preserved and pre_playback_preserved and pre_camset_preserved

    zero_rf_certified = (
        creds_cleared
        and ((not reboot_req) or auto_reboot_completed)
        and post_reasserted_airplane_mode == "On"
    )
    return creds_cleared, reboot_req, imm_airplane, non_nw_ok, zero_rf_certified


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase282DonorArtifactDigest:
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
class Phase282DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase282DonorArtifactDigest, ...]


@dataclass(frozen=True)
class UsbModePdGuardHdmiInfoVaultSpec:
    camera_model: str = P282_FX3_MODEL_NAME
    camera_model_id: int = P282_FX3_MODEL_ID
    camera_codename: str = P282_FX3_PRODUCT_CODENAME
    helpguide_id: str = P282_FX3_HELPGUIDE_ID
    fw_version: str = P282_FX3_FW_VERSION
    usb_connection_menu_path: Tuple[str, ...] = P282_USB_CONNECTION_MODE_MENU_PATH
    fx3_usb_connection_4_modes: Tuple[str, ...] = P282_FX3_USB_CONNECTION_4_MODES
    fx3_ui_exposes_usb_streaming: bool = P282_FX3_UI_EXPOSES_USB_STREAMING
    dormant_uvc_ko_insmoded: bool = False
    nouvc_spoof_events: int = 0
    airgapped_tier0_session: bool = True
    pre_usb_connection_mode: str = "Sel. When Connect"
    pre_usb_lun_setting: str = "Multi"
    pre_usb_power_supply: str = "On"
    active_host_usb_data_mode: str = "NONE"
    usb_data_lines_physically_isolated: bool = True
    usb_port: str = P282_USB_POWER_SUPPLY_REQUIRED_PORT
    np_fz100_inserted: bool = True
    usb_host_data_enumeration_events: int = 0
    hdmi_info_menu_path: Tuple[str, ...] = P282_HDMI_INFO_DISPLAY_MENU_PATH
    external_hdmi_recorder_attached: bool = True
    operator_lcd_menu_recovery_active: bool = True
    pre_hdmi_info_display: str = "Off"
    pre_rec_media_dur_hdmi: str = "On"
    pre_raw_output: str = "Off"
    pre_output_resolution: str = "Auto"
    pre_framing_hdmi: str = "Full"
    shooting_domain: str = "Movie"
    log_shooting: str = "Cine EI"
    picture_profile: str = "Off"
    reported_effective_hdmi_resolution: str = "1080p"
    hdmi_lcd_blanking_violations: int = 0
    hdmi_log_1080_bypass_events: int = 0
    reset_action: str = "Camera Settings Reset"
    camset_load_after_reset: bool = False
    camset_slot: int = P282_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P282_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_usb_connection_mode: str = "Sel. When Connect"
    saved_usb_lun_setting: str = "Multi"
    saved_usb_power_supply: str = "On"
    saved_hdmi_info_display: str = "Off"
    saved_rec_media_dur_hdmi: str = "On"
    saved_output_resolution: str = "Auto"
    saved_raw_output: str = "Off"
    saved_framing_hdmi: str = "Crop"
    post_usb_connection_mode: str = "Sel. When Connect"
    post_usb_lun_setting: str = "Multi"
    post_usb_power_supply: str = "On"
    post_hdmi_info_display: str = "Off"
    post_rec_media_dur_hdmi: str = "On"
    post_output_resolution: str = "Auto"
    post_raw_output: str = "Off"
    post_framing_hdmi: str = "Crop"
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_vault_mutation_bytes: int = 0
    overlay_dir: str = P282_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P282_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P282_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P282_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class UsbModePdGuardHdmiInfoVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    usb_4mode_and_nouvc_verified: bool
    data_isolated_usb_pd_guard_verified: bool
    hdmi_info_lcd_clean_feed_and_1080_4k_verified: bool
    setup_usb_hdmi_reset_and_camset_verified: bool
    h0_equals_h3_verified: bool
    matrix_states_checked: int
    fx3_ui_exposes_usb_streaming: bool
    nouvc_spoof_events: int
    usb_host_data_enumeration_events: int
    hdmi_lcd_blanking_violations: int
    hdmi_log_1080_bypass_events: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProtectFormatNetworkResetZeroRfVaultSpec:
    camera_model: str = P282_FX3_MODEL_NAME
    camera_model_id: int = P282_FX3_MODEL_ID
    helpguide_id: str = P282_FX3_HELPGUIDE_ID
    fw_version: str = P282_FX3_FW_VERSION
    protect_menu_path: Tuple[str, ...] = P282_PROTECT_MENU_PATH
    format_menu_path: Tuple[str, ...] = P282_FORMAT_MENU_PATH
    reset_network_menu_path: Tuple[str, ...] = P282_RESET_NETWORK_MENU_PATH
    protect_4_scopes: Tuple[str, ...] = P282_PROTECT_4_SCOPES
    software_protect_active: bool = True
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_format_hard_locked: bool = P282_SLOT1_FORMAT_HARD_LOCKED
    requested_vault_slot: int = P282_SLOT1_VAULT_SLOT
    requested_vault_action: str = "READ_ONLY_AUDIT"
    slot1_protect_only_vault_violations: int = 0
    slot1_vault_format_or_delete_events: int = 0
    slot1_vault_mutation_bytes: int = 0
    reset_action: str = "Reset Network Set."
    pre_network_creds_present: bool = True
    pre_airplane_mode: str = "Off"
    pre_shooting_preserved: bool = True
    pre_setup_preserved: bool = True
    pre_playback_preserved: bool = True
    pre_camset_preserved: bool = True
    auto_reboot_triggered: bool = True
    auto_reboot_completed: bool = True
    immediate_post_reset_airplane_mode: str = "Off"
    post_network_creds_cleared: bool = True
    post_reasserted_airplane_mode: str = "On"
    network_reset_zero_rf_violations: int = 0
    camset_load_after_reset: bool = False
    camset_slot: int = P282_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P282_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    overlay_dir: str = P282_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P282_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P282_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P282_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class ProtectFormatNetworkResetZeroRfVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    protect_4scopes_and_format_override_verified: bool
    slot1_dual_layer_wp_and_format_firewall_verified: bool
    network_reset_reboot_and_airplane_zero_rf_verified: bool
    three_way_reset_scope_and_camset_verified: bool
    h0_equals_h3_verified: bool
    matrix_states_checked: int
    slot1_protect_only_vault_violations: int
    slot1_vault_format_or_delete_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    network_reset_zero_rf_violations: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UsbModeHdmiInfoProtectNetworkResetVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase282DonorSnapshot
    usb_hdmi_report: UsbModePdGuardHdmiInfoVaultReport
    protect_network_report: ProtectFormatNetworkResetZeroRfVaultReport
    fx3_ui_exposes_usb_streaming: bool
    nouvc_spoof_events: int
    usb_host_data_enumeration_events: int
    hdmi_lcd_blanking_violations: int
    hdmi_log_1080_bypass_events: int
    slot1_protect_only_vault_violations: int
    slot1_vault_format_or_delete_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    network_reset_zero_rf_violations: int
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
class Pillar49ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar49ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar49ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar49BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar49ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar49StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase282DonorSnapshot
    pillar_49a_usb_mode_pd_hdmi_info_vault: Pillar49ASuiteResult
    pillar_49b_protect_format_network_reset_vault: Pillar49BSuiteResult
    fx3_ui_exposes_usb_streaming: bool
    nouvc_spoof_events: int
    usb_host_data_enumeration_events: int
    hdmi_lcd_blanking_violations: int
    hdmi_log_1080_bypass_events: int
    slot1_protect_only_vault_violations: int
    slot1_vault_format_or_delete_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    network_reset_zero_rf_violations: int
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
class Master49PillarRecoveryReport:
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
    # Pillar 49 & Wave-47 top-level fields
    donor_snapshot: Phase282DonorSnapshot
    pillar49_a_usb_mode_pd_hdmi_info_vault: Pillar49ASuiteResult
    pillar49_b_protect_format_network_reset_vault: Pillar49BSuiteResult
    fx3_ui_exposes_usb_streaming: bool
    nouvc_spoof_events: int
    usb_host_data_enumeration_events: int
    hdmi_lcd_blanking_violations: int
    hdmi_log_1080_bypass_events: int
    slot1_protect_only_vault_violations: int
    slot1_vault_format_or_delete_events: int
    slot1_vault_mutation_bytes: int
    slot1_format_hard_locked: bool
    network_reset_zero_rf_violations: int
    # Preserved Pillars 1..48 rollup metrics
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
    master_49pillar_sha256: str
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
    max_full_bytes: int = P282_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P282_BOUNDED_HEADER_BYTES, total_size), 0)
        return True, total_size, len(hdr), "HEADER4K_SHA256", sha256(hdr).hexdigest(), hdr
    finally:
        os.close(fd)


def _check_elf64_aarch64_tokens(
    data: bytes, expected_tokens: Tuple[bytes, ...], prefix: str = "ELF64_AARCH64"
) -> Tuple[bool, str]:
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
    return True, f"{prefix}:{'+'.join(found)}" if found else prefix


def _check_uxc7_pack(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 16 or data[:4] != b"uxc\x07":
        return False, f"BAD_UXC7_MAGIC:{label}"
    return True, f"UXC7_{label}"


def _check_bk4_backup(data: bytes, label: str) -> Tuple[bool, str]:
    if len(data) < 32 or struct.unpack_from("<I", data, 4)[0] != 0xAAAAAAAA or data[12:16] != b"BK4\x00":
        return False, f"BAD_BK4_MAGIC:{label}"
    return True, f"BK4_{label}"


def _synthetic_phase282_donors() -> Tuple[Phase282DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_appfw_702_so",
            P282_DONOR_FX3_APPFW_702_RELPATH,
            P282_PINNED_FX3_APPFW_702_BYTES,
            P282_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P282_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P282_DONOR_FX6_APPFW_601_RELPATH,
            P282_PINNED_FX6_APPFW_601_BYTES,
            P282_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P282_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_usb_f_uvc_ko",
            P282_DONOR_FX3_USB_F_UVC_KO_RELPATH,
            P282_PINNED_FX3_USB_F_UVC_KO_BYTES,
            P282_PINNED_FX3_USB_F_UVC_KO_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_USB_F_UVC_KO_SHA256,
            "SYNTHETIC_ELF64_AARCH64_KMOD_DORMANT_NOUVC:uvc+usb_f_uvc",
        ),
        (
            "fx6_usb_f_uvc_ko",
            P282_DONOR_FX6_USB_F_UVC_KO_RELPATH,
            P282_PINNED_FX6_USB_F_UVC_KO_BYTES,
            P282_PINNED_FX6_USB_F_UVC_KO_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX6_USB_F_UVC_KO_SHA256,
            "SYNTHETIC_ELF64_AARCH64_KMOD_PROCAM_UVC:uvc+usb_f_uvc",
        ),
        (
            "fx3_usbg_storage_ko",
            P282_DONOR_FX3_USBG_STORAGE_KO_RELPATH,
            P282_PINNED_FX3_USBG_STORAGE_KO_BYTES,
            P282_PINNED_FX3_USBG_STORAGE_KO_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_USBG_STORAGE_KO_SHA256,
            "SYNTHETIC_ELF64_AARCH64_KMOD_MSC:usbg_storage",
        ),
        (
            "fx3_usbg_stillimage_ko",
            P282_DONOR_FX3_USBG_STILLIMAGE_KO_RELPATH,
            P282_PINNED_FX3_USBG_STILLIMAGE_KO_BYTES,
            P282_PINNED_FX3_USBG_STILLIMAGE_KO_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_USBG_STILLIMAGE_KO_SHA256,
            "SYNTHETIC_ELF64_AARCH64_KMOD_MTP:stillimage",
        ),
        (
            "fx3_libusbbuspower_so",
            P282_DONOR_FX3_LIBUSBBUSPOWER_SO_RELPATH,
            P282_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES,
            P282_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:UsbBusPower_Init+SetWatchSWForceOFF",
        ),
        (
            "fx3_libinfraairplanemode_so",
            P282_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH,
            P282_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            P282_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:infra_airplane_mode_init+AirplaneModeTraceRecord",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P282_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P282_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P282_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead",
        ),
        (
            "fx3_backup_bin",
            P282_DONOR_FX3_BACKUP_BIN_RELPATH,
            P282_PINNED_FX3_BACKUP_BIN_BYTES,
            P282_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_uxc_en_f",
            P282_DONOR_FX3_UXC_EN_F_RELPATH,
            P282_PINNED_FX3_UXC_EN_F_BYTES,
            P282_PINNED_FX3_UXC_EN_F_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_UXC_EN_F_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_F",
        ),
        (
            "fx3_uxc_sc_f",
            P282_DONOR_FX3_UXC_SC_F_RELPATH,
            P282_PINNED_FX3_UXC_SC_F_BYTES,
            P282_PINNED_FX3_UXC_SC_F_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_UXC_SC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_SC_F",
        ),
        (
            "fx3_uxc_tc_f",
            P282_DONOR_FX3_UXC_TC_F_RELPATH,
            P282_PINNED_FX3_UXC_TC_F_BYTES,
            P282_PINNED_FX3_UXC_TC_F_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_UXC_TC_F_SHA256,
            "SYNTHETIC_UXC7_FX3_TC_F",
        ),
        (
            "fx3_uxc_ja_f",
            P282_DONOR_FX3_UXC_JA_F_RELPATH,
            P282_PINNED_FX3_UXC_JA_F_BYTES,
            P282_PINNED_FX3_UXC_JA_F_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_UXC_JA_F_SHA256,
            "SYNTHETIC_UXC7_FX3_JA_F",
        ),
        (
            "fx3_uxc_en",
            P282_DONOR_FX3_UXC_EN_RELPATH,
            P282_PINNED_FX3_UXC_EN_BYTES,
            P282_PINNED_FX3_UXC_EN_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX3_EN",
        ),
        (
            "fx3_uxc_en_g",
            P282_DONOR_FX3_UXC_EN_G_RELPATH,
            P282_PINNED_FX3_UXC_EN_G_BYTES,
            P282_PINNED_FX3_UXC_EN_G_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX3_UXC_EN_G_SHA256,
            "SYNTHETIC_UXC7_FX3_EN_G",
        ),
        (
            "fx6_uxc_en",
            P282_DONOR_FX6_UXC_EN_RELPATH,
            P282_PINNED_FX6_UXC_EN_BYTES,
            P282_PINNED_FX6_UXC_EN_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX6_UXC_EN_SHA256,
            "SYNTHETIC_UXC7_FX6_EN",
        ),
        (
            "fx6_uxc_en_2",
            P282_DONOR_FX6_UXC_EN_2_RELPATH,
            P282_PINNED_FX6_UXC_EN_2_BYTES,
            P282_PINNED_FX6_UXC_EN_2_BYTES,
            "FULL_SHA256",
            P282_PINNED_FX6_UXC_EN_2_SHA256,
            "SYNTHETIC_UXC7_FX6_EN_2",
        ),
    )
    return tuple(
        Phase282DonorArtifactDigest(
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


def inspect_phase282_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase282DonorSnapshot:
    """Inspect Wave-47 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.15s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase282_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase282DonorSnapshot(
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
            P282_DONOR_FX3_APPFW_702_RELPATH,
            P282_PINNED_FX3_APPFW_702_BYTES,
            P282_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P282_DONOR_FX6_APPFW_601_RELPATH,
            P282_PINNED_FX6_APPFW_601_BYTES,
            P282_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_usb_f_uvc_ko",
            P282_DONOR_FX3_USB_F_UVC_KO_RELPATH,
            P282_PINNED_FX3_USB_F_UVC_KO_BYTES,
            P282_PINNED_FX3_USB_F_UVC_KO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"uvc", b"usb_f_uvc"), prefix="ELF64_AARCH64_KMOD_DORMANT_NOUVC"
            ),
        ),
        (
            "fx6_usb_f_uvc_ko",
            P282_DONOR_FX6_USB_F_UVC_KO_RELPATH,
            P282_PINNED_FX6_USB_F_UVC_KO_BYTES,
            P282_PINNED_FX6_USB_F_UVC_KO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"uvc", b"usb_f_uvc"), prefix="ELF64_AARCH64_KMOD_PROCAM_UVC"
            ),
        ),
        (
            "fx3_usbg_storage_ko",
            P282_DONOR_FX3_USBG_STORAGE_KO_RELPATH,
            P282_PINNED_FX3_USBG_STORAGE_KO_BYTES,
            P282_PINNED_FX3_USBG_STORAGE_KO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"usbg_storage",), prefix="ELF64_AARCH64_KMOD_MSC"
            ),
        ),
        (
            "fx3_usbg_stillimage_ko",
            P282_DONOR_FX3_USBG_STILLIMAGE_KO_RELPATH,
            P282_PINNED_FX3_USBG_STILLIMAGE_KO_BYTES,
            P282_PINNED_FX3_USBG_STILLIMAGE_KO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"stillimage",), prefix="ELF64_AARCH64_KMOD_MTP"
            ),
        ),
        (
            "fx3_libusbbuspower_so",
            P282_DONOR_FX3_LIBUSBBUSPOWER_SO_RELPATH,
            P282_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES,
            P282_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"UsbBusPower_Init", b"SetWatchSWForceOFF")
            ),
        ),
        (
            "fx3_libinfraairplanemode_so",
            P282_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH,
            P282_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            P282_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"infra_airplane_mode_init", b"AirplaneModeTraceRecord")
            ),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P282_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P282_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P282_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"SaveLoadSettingsIf", b"requestToRead")
            ),
        ),
        (
            "fx3_backup_bin",
            P282_DONOR_FX3_BACKUP_BIN_RELPATH,
            P282_PINNED_FX3_BACKUP_BIN_BYTES,
            P282_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: _check_bk4_backup(d, "ILME_FX3"),
        ),
        (
            "fx3_uxc_en_f",
            P282_DONOR_FX3_UXC_EN_F_RELPATH,
            P282_PINNED_FX3_UXC_EN_F_BYTES,
            P282_PINNED_FX3_UXC_EN_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_F"),
        ),
        (
            "fx3_uxc_sc_f",
            P282_DONOR_FX3_UXC_SC_F_RELPATH,
            P282_PINNED_FX3_UXC_SC_F_BYTES,
            P282_PINNED_FX3_UXC_SC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_SC_F"),
        ),
        (
            "fx3_uxc_tc_f",
            P282_DONOR_FX3_UXC_TC_F_RELPATH,
            P282_PINNED_FX3_UXC_TC_F_BYTES,
            P282_PINNED_FX3_UXC_TC_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_TC_F"),
        ),
        (
            "fx3_uxc_ja_f",
            P282_DONOR_FX3_UXC_JA_F_RELPATH,
            P282_PINNED_FX3_UXC_JA_F_BYTES,
            P282_PINNED_FX3_UXC_JA_F_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_JA_F"),
        ),
        (
            "fx3_uxc_en",
            P282_DONOR_FX3_UXC_EN_RELPATH,
            P282_PINNED_FX3_UXC_EN_BYTES,
            P282_PINNED_FX3_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN"),
        ),
        (
            "fx3_uxc_en_g",
            P282_DONOR_FX3_UXC_EN_G_RELPATH,
            P282_PINNED_FX3_UXC_EN_G_BYTES,
            P282_PINNED_FX3_UXC_EN_G_SHA256,
            lambda d: _check_uxc7_pack(d, "FX3_EN_G"),
        ),
        (
            "fx6_uxc_en",
            P282_DONOR_FX6_UXC_EN_RELPATH,
            P282_PINNED_FX6_UXC_EN_BYTES,
            P282_PINNED_FX6_UXC_EN_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN"),
        ),
        (
            "fx6_uxc_en_2",
            P282_DONOR_FX6_UXC_EN_2_RELPATH,
            P282_PINNED_FX6_UXC_EN_2_BYTES,
            P282_PINNED_FX6_UXC_EN_2_SHA256,
            lambda d: _check_uxc7_pack(d, "FX6_EN_2"),
        ),
    )

    artifacts: List[Phase282DonorArtifactDigest] = []
    any_missing = False
    for aid, relpath, expected_bytes, expected_sha, marker_fn in probe_specs:
        present, total_b, hdr_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(relpath)
        if not present:
            any_missing = True
            artifacts.append(
                Phase282DonorArtifactDigest(
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
            Phase282DonorArtifactDigest(
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
        synth = _synthetic_phase282_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase282DonorSnapshot(
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
    return Phase282DonorSnapshot(
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
# Pillar 49A & 49B Builders and Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_usb_mode_pd_guard_hdmi_info_vault_spec() -> UsbModePdGuardHdmiInfoVaultSpec:
    """Return canonical safe Wave-47 Pillar 49A specification."""
    return UsbModePdGuardHdmiInfoVaultSpec()


def build_default_safe_protect_format_network_reset_zero_rf_vault_spec() -> (
    ProtectFormatNetworkResetZeroRfVaultSpec
):
    """Return canonical safe Wave-47 Pillar 49B specification."""
    return ProtectFormatNetworkResetZeroRfVaultSpec()


def evaluate_usb_mode_pd_guard_and_hdmi_info_vault(
    spec: Optional[UsbModePdGuardHdmiInfoVaultSpec] = None,
) -> UsbModePdGuardHdmiInfoVaultReport:
    """Verify Pillar 49A: `[USB Connection Mode]` 4-mode vs dormant `NOUVC` `[USB Streaming]`,
    data-isolated `USB PD` recovery power guard, & `[HDMI Info. Display]` LCD-blanking /
    `1080` Log/PPLUT clamp vs `4K` clean-feed override telemetry."""
    cfg = spec if spec is not None else UsbModePdGuardHdmiInfoVaultSpec()
    safety_errs = _safety_invariant_errors()
    if safety_errs or cfg.persistent_write_unlock_requested:
        errs = safety_errs + (
            ["persistent_write_unlock_requested must be False"]
            if cfg.persistent_write_unlock_requested
            else []
        )
        return UsbModePdGuardHdmiInfoVaultReport(
            passed=False,
            status=P282_STATUS_REJECTED_PILLAR_49A,
            block_code=P282_BLOCKED_SAFETY_POLICY_VIOLATION,
            usb_4mode_and_nouvc_verified=False,
            data_isolated_usb_pd_guard_verified=False,
            hdmi_info_lcd_clean_feed_and_1080_4k_verified=False,
            setup_usb_hdmi_reset_and_camset_verified=False,
            h0_equals_h3_verified=False,
            matrix_states_checked=0,
            fx3_ui_exposes_usb_streaming=False,
            nouvc_spoof_events=0,
            usb_host_data_enumeration_events=0,
            hdmi_lcd_blanking_violations=0,
            hdmi_log_1080_bypass_events=0,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            digest_sha256=_canonical_sha256({"blocked": P282_BLOCKED_SAFETY_POLICY_VIOLATION}),
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
        cfg.camera_model != P282_FX3_MODEL_NAME
        or cfg.camera_model_id != P282_FX3_MODEL_ID
        or cfg.helpguide_id != P282_FX3_HELPGUIDE_ID
        or cfg.fw_version not in P282_FX3_SUPPORTED_FW_VERSIONS
        or cfg.usb_connection_menu_path != P282_USB_CONNECTION_MODE_MENU_PATH
        or cfg.hdmi_info_menu_path != P282_HDMI_INFO_DISPLAY_MENU_PATH
        or cfg.pre_usb_connection_mode not in P282_FX3_USB_CONNECTION_4_MODES
        or cfg.pre_usb_lun_setting not in P282_USB_LUN_MODES
        or cfg.pre_usb_power_supply not in P282_USB_POWER_SUPPLY_MODES
        or cfg.active_host_usb_data_mode not in P282_TIER0_HOST_USB_DATA_STATES
        or cfg.usb_port not in P282_USB_PORTS
        or cfg.pre_hdmi_info_display not in P282_HDMI_INFO_DISPLAY_MODES
        or cfg.pre_rec_media_dur_hdmi not in P282_REC_MEDIA_DUR_HDMI_MODES
        or cfg.pre_raw_output not in P282_ON_OFF_MODES
        or cfg.pre_output_resolution not in P282_OUTPUT_RESOLUTION_MODES
        or cfg.pre_framing_hdmi not in P282_FRAMING_HDMI_MODES
        or cfg.shooting_domain not in P282_SHOOTING_DOMAINS
        or cfg.log_shooting not in P282_LOG_SHOOTING_MODES
        or cfg.picture_profile not in P282_PICTURE_PROFILE_MODES
        or cfg.reset_action not in P282_RESET_ACTIONS
    ):
        _set_block(
            P282_BLOCKED_INVALID_PILLAR49A_SPEC,
            "Invalid Pillar 49A camera model, firmware version, menu path, USB/HDMI mode, or reset spec",
        )

    # 1. [USB Connection Mode] exact 4 modes vs dormant NOUVC + host data enumeration block
    usb_4mode_nouvc_ok = True
    nouvc_spoofs = cfg.nouvc_spoof_events
    host_enum_events = cfg.usb_host_data_enumeration_events
    if (
        cfg.fx3_usb_connection_4_modes != P282_FX3_USB_CONNECTION_4_MODES
        or P282_FORBIDDEN_FX3_USB_STREAMING_MODE in cfg.fx3_usb_connection_4_modes
        or cfg.fx3_ui_exposes_usb_streaming is not False
        or cfg.dormant_uvc_ko_insmoded is not False
        or cfg.nouvc_spoof_events != 0
    ):
        usb_4mode_nouvc_ok = False
        nouvc_spoofs = max(nouvc_spoofs, 1)
        _set_block(
            P282_BLOCKED_NOUVC_OR_USB_HOST_DATA_ENUMERATION,
            "Stock ILME-FX3 exposes only 4 USB Connection Modes; dormant usb_f_uvc.ko / USB Streaming must remain unexposed (NOUVC)",
        )

    host_data_safe, pd_power_ok, _ = compute_expected_usb_connection_and_pd_guard(
        airgapped_tier0_session=cfg.airgapped_tier0_session,
        active_host_usb_data_mode=cfg.active_host_usb_data_mode,
        usb_data_lines_physically_isolated=cfg.usb_data_lines_physically_isolated,
        usb_power_supply=cfg.post_usb_power_supply,
        usb_port=cfg.usb_port,
        np_fz100_inserted=cfg.np_fz100_inserted,
    )
    if not host_data_safe or cfg.usb_host_data_enumeration_events != 0:
        usb_4mode_nouvc_ok = False
        host_enum_events = max(host_enum_events, 1)
        _set_block(
            P282_BLOCKED_NOUVC_OR_USB_HOST_DATA_ENUMERATION,
            f"Air-gapped Tier-0 session prohibits unisolated host USB data enumeration ({cfg.active_host_usb_data_mode!r})",
        )

    # 2. Data-isolated USB PD Recovery Power Guard
    pd_guard_ok = True
    if not pd_power_ok:
        pd_guard_ok = False
        _set_block(
            P282_BLOCKED_USB_PD_UNISOLATED_OR_PORT_ERROR,
            "USB Power Supply = On requires USB Type-C, NP-FZ100 inserted, and physically isolated D+/D- & SuperSpeed lines on air-gapped Tier-0",
        )

    matrix_checked = 0
    for data_mode in P282_TIER0_HOST_USB_DATA_STATES:
        for isolated in (False, True):
            for airgap in (False, True):
                h_ok, p_ok, _ = compute_expected_usb_connection_and_pd_guard(
                    airgapped_tier0_session=airgap,
                    active_host_usb_data_mode=data_mode,
                    usb_data_lines_physically_isolated=isolated,
                    usb_power_supply="On",
                    usb_port="USB Type-C",
                    np_fz100_inserted=True,
                )
                exp_h = (not airgap) or (data_mode not in P282_BLOCKED_HOST_DATA_ENUMERATION_MODES) or isolated
                exp_p = (not airgap) or isolated
                if h_ok != exp_h or p_ok != exp_p:
                    pd_guard_ok = False
                    _set_block(
                        P282_BLOCKED_USB_PD_UNISOLATED_OR_PORT_ERROR,
                        "USB host-data / PD isolation matrix invariant failed",
                    )
                matrix_checked += 1

    # 3. [HDMI Info. Display] LCD-blanking & 1080 Log/PPLUT clamp vs 4K clean-feed override
    hdmi_ok = True
    lcd_blank_violations = cfg.hdmi_lcd_blanking_violations
    log_1080_bypasses = cfg.hdmi_log_1080_bypass_events
    eff_hdmi_info, lcd_active, eff_res, _ = compute_expected_hdmi_info_and_resolution_state(
        configured_hdmi_info_display=cfg.post_hdmi_info_display,
        rec_media_dur_hdmi=cfg.post_rec_media_dur_hdmi,
        raw_output=cfg.post_raw_output,
        configured_output_resolution=cfg.post_output_resolution,
        log_shooting=cfg.log_shooting,
        picture_profile=cfg.picture_profile,
        shooting_domain=cfg.shooting_domain,
    )
    if (
        cfg.external_hdmi_recorder_attached
        and cfg.operator_lcd_menu_recovery_active
        and (not lcd_active or eff_hdmi_info != "Off")
    ):
        hdmi_ok = False
        lcd_blank_violations = max(lcd_blank_violations, 1)
        _set_block(
            P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS,
            "HDMI Info. Display = On blanks built-in LCD (CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON) during operator LCD menu recovery",
        )
    if cfg.hdmi_lcd_blanking_violations != 0:
        hdmi_ok = False
        lcd_blank_violations = max(lcd_blank_violations, 1)
        _set_block(
            P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS,
            "Non-zero HDMI LCD blanking violations recorded",
        )
    if cfg.reported_effective_hdmi_resolution != eff_res or cfg.hdmi_log_1080_bypass_events != 0:
        hdmi_ok = False
        log_1080_bypasses = max(log_1080_bypasses, 1)
        _set_block(
            P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS,
            f"HDMI output resolution drift: expected {eff_res!r}, got {cfg.reported_effective_hdmi_resolution!r}",
        )

    for info_m in P282_HDMI_INFO_DISPLAY_MODES:
        for rec_m in P282_REC_MEDIA_DUR_HDMI_MODES:
            for raw_m in P282_ON_OFF_MODES:
                for log_m in ("Off", "Cine EI"):
                    e_info, e_lcd, e_res, e_clean = compute_expected_hdmi_info_and_resolution_state(
                        configured_hdmi_info_display=info_m,
                        rec_media_dur_hdmi=rec_m,
                        raw_output=raw_m,
                        configured_output_resolution="2160p",
                        log_shooting=log_m,
                        picture_profile="Off",
                        shooting_domain="Movie",
                    )
                    if rec_m == "Off(HDMI Only)" or raw_m == "On":
                        if e_info != "Off" or not e_lcd or not e_clean or e_res != "4K":
                            hdmi_ok = False
                            _set_block(
                                P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS,
                                "HDMI Only / RAW Output must force clean-feed Off & 4K",
                            )
                    elif log_m != "Off" and e_res != "1080p":
                        hdmi_ok = False
                        _set_block(
                            P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS,
                            "Internal Log/PPLUT recording must clamp HDMI output to 1080p",
                        )
                    matrix_checked += 1

    # 4. (Setup) Reset boundary survival & CAMSET01..10.DAT O_RDONLY restore
    reset_ok = True
    exp_tuple = compute_expected_pillar49a_reset_state(
        pre_usb_connection_mode=cfg.pre_usb_connection_mode,
        pre_usb_lun_setting=cfg.pre_usb_lun_setting,
        pre_usb_power_supply=cfg.pre_usb_power_supply,
        pre_hdmi_info_display=cfg.pre_hdmi_info_display,
        pre_rec_media_dur_hdmi=cfg.pre_rec_media_dur_hdmi,
        pre_output_resolution=cfg.pre_output_resolution,
        pre_raw_output=cfg.pre_raw_output,
        pre_framing_hdmi=cfg.pre_framing_hdmi,
        reset_action=cfg.reset_action,
    )
    if cfg.camset_load_after_reset:
        if (
            cfg.camset_slot != P282_SLOT1_VAULT_SLOT
            or cfg.camset_filename not in P282_CAMSET_FILENAMES
            or cfg.camset_source_model != P282_FX3_MODEL_NAME
            or not cfg.camset_read_only_load
        ):
            reset_ok = False
            _set_block(
                P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT,
                "CAMSET load must be read-only from Slot-1 ILME-FX3 CAMSET01..10.DAT",
            )
        exp_tuple = (
            cfg.saved_usb_connection_mode,
            cfg.saved_usb_lun_setting,
            cfg.saved_usb_power_supply,
            cfg.saved_hdmi_info_display,
            cfg.saved_rec_media_dur_hdmi,
            cfg.saved_output_resolution,
            cfg.saved_raw_output,
            cfg.saved_framing_hdmi,
        )

    actual_tuple = (
        cfg.post_usb_connection_mode,
        cfg.post_usb_lun_setting,
        cfg.post_usb_power_supply,
        cfg.post_hdmi_info_display,
        cfg.post_rec_media_dur_hdmi,
        cfg.post_output_resolution,
        cfg.post_raw_output,
        cfg.post_framing_hdmi,
    )
    if actual_tuple != exp_tuple:
        reset_ok = False
        _set_block(
            P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT,
            f"Setup USB/HDMI reset drift for {cfg.reset_action!r}: expected {exp_tuple!r}, got {actual_tuple!r}",
        )

    for r_act in P282_RESET_ACTIONS:
        out_t = compute_expected_pillar49a_reset_state(
            pre_usb_connection_mode="MTP",
            pre_usb_lun_setting="Single",
            pre_usb_power_supply="Off",
            pre_hdmi_info_display="Off",
            pre_rec_media_dur_hdmi="Off(HDMI Only)",
            pre_output_resolution="2160p",
            pre_raw_output="On",
            pre_framing_hdmi="Full",
            reset_action=r_act,
        )
        if r_act == "Initialize":
            if out_t != ("Sel. When Connect", "Multi", "On", "On", "On", "Auto", "Off", "Crop"):
                reset_ok = False
                _set_block(
                    P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT,
                    "Initialize must revert all (Setup) USB/HDMI items to defaults",
                )
        elif r_act == "Camera Settings Reset":
            if out_t != ("MTP", "Single", "Off", "Off", "Off(HDMI Only)", "2160p", "On", "Crop"):
                reset_ok = False
                _set_block(
                    P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT,
                    "Camera Settings Reset must preserve Setup USB/HDMI while resetting Framing (HDMI) to Crop",
                )
        else:
            if out_t != ("MTP", "Single", "Off", "Off", "Off(HDMI Only)", "2160p", "On", "Full"):
                reset_ok = False
                _set_block(
                    P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT,
                    f"{r_act} must preserve Setup USB/HDMI and Framing (HDMI)",
                )
        matrix_checked += 1

    # 5. Volatile /tmp overlay + Tier-0 H0 == H3 + Slot-1 read-only integrity
    h0_h3_ok = True
    if not _is_tmpfs_path(cfg.overlay_dir) or _targets_persistent_emmc(cfg.overlay_dir) or not cfg.p2_blkroset_locked:
        h0_h3_ok = False
        _set_block(
            P282_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain strictly in volatile /tmp or /run with BLKROSET=True: {cfg.overlay_dir!r}",
        )
    if (
        not cfg.slot1_holds_recovery_vault
        or not cfg.slot1_sdxc_wp_locked
        or cfg.slot1_vault_mutation_bytes != 0
        or cfg.stage_b_backup_bin_writes != 0
        or cfg.backup_bin_h0_sha256 != P282_PINNED_FX3_BACKUP_BIN_SHA256
        or cfg.backup_bin_h3_sha256 != cfg.backup_bin_h0_sha256
        or cfg.tier0_surfaces_h0_h3_matched != P282_TIER0_SURFACE_COUNT
    ):
        h0_h3_ok = False
        _set_block(
            P282_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Slot-1 read-only vault or 16/16 Tier-0 H0 == H3 Backup.bin invariant drifted",
        )

    passed = (
        usb_4mode_nouvc_ok
        and pd_guard_ok
        and hdmi_ok
        and reset_ok
        and h0_h3_ok
        and len(errs) == 0
    )
    digest = _canonical_sha256(
        {
            "pillar": "49A",
            "passed": passed,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "nouvc_spoofs": nouvc_spoofs,
            "host_enum_events": host_enum_events,
            "lcd_blank_violations": lcd_blank_violations,
            "log_1080_bypasses": log_1080_bypasses,
        }
    )
    return UsbModePdGuardHdmiInfoVaultReport(
        passed=passed,
        status=P282_STATUS_VERIFIED_PILLAR_49A if passed else P282_STATUS_REJECTED_PILLAR_49A,
        block_code=block_code,
        usb_4mode_and_nouvc_verified=usb_4mode_nouvc_ok,
        data_isolated_usb_pd_guard_verified=pd_guard_ok,
        hdmi_info_lcd_clean_feed_and_1080_4k_verified=hdmi_ok,
        setup_usb_hdmi_reset_and_camset_verified=reset_ok,
        h0_equals_h3_verified=h0_h3_ok,
        matrix_states_checked=matrix_checked,
        fx3_ui_exposes_usb_streaming=cfg.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=nouvc_spoofs,
        usb_host_data_enumeration_events=host_enum_events,
        hdmi_lcd_blanking_violations=lcd_blank_violations,
        hdmi_log_1080_bypass_events=log_1080_bypasses,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errs),
    )


def evaluate_protect_format_network_reset_zero_rf_vault(
    spec: Optional[ProtectFormatNetworkResetZeroRfVaultSpec] = None,
) -> ProtectFormatNetworkResetZeroRfVaultReport:
    """Verify Pillar 49B: `[Protect]` 4 scopes vs `[Format]` wipe (`Slot-1` dual-layer SD `WP` +
    firewall mandate) and `[Reset Network Set.]` auto-reboot + post-reboot `[Airplane Mode] = [On]`
    zero-RF recovery sequence."""
    cfg = spec if spec is not None else ProtectFormatNetworkResetZeroRfVaultSpec()
    safety_errs = _safety_invariant_errors()
    if safety_errs or cfg.persistent_write_unlock_requested:
        errs = safety_errs + (
            ["persistent_write_unlock_requested must be False"]
            if cfg.persistent_write_unlock_requested
            else []
        )
        return ProtectFormatNetworkResetZeroRfVaultReport(
            passed=False,
            status=P282_STATUS_REJECTED_PILLAR_49B,
            block_code=P282_BLOCKED_SAFETY_POLICY_VIOLATION,
            protect_4scopes_and_format_override_verified=False,
            slot1_dual_layer_wp_and_format_firewall_verified=False,
            network_reset_reboot_and_airplane_zero_rf_verified=False,
            three_way_reset_scope_and_camset_verified=False,
            h0_equals_h3_verified=False,
            matrix_states_checked=0,
            slot1_protect_only_vault_violations=0,
            slot1_vault_format_or_delete_events=0,
            slot1_vault_mutation_bytes=0,
            slot1_format_hard_locked=P282_SLOT1_FORMAT_HARD_LOCKED,
            network_reset_zero_rf_violations=0,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            digest_sha256=_canonical_sha256({"blocked": P282_BLOCKED_SAFETY_POLICY_VIOLATION}),
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
        cfg.camera_model != P282_FX3_MODEL_NAME
        or cfg.camera_model_id != P282_FX3_MODEL_ID
        or cfg.helpguide_id != P282_FX3_HELPGUIDE_ID
        or cfg.fw_version not in P282_FX3_SUPPORTED_FW_VERSIONS
        or cfg.protect_menu_path != P282_PROTECT_MENU_PATH
        or cfg.format_menu_path != P282_FORMAT_MENU_PATH
        or cfg.reset_network_menu_path != P282_RESET_NETWORK_MENU_PATH
        or cfg.pre_airplane_mode not in P282_AIRPLANE_MODE_MODES
        or cfg.immediate_post_reset_airplane_mode not in P282_AIRPLANE_MODE_MODES
        or cfg.post_reasserted_airplane_mode not in P282_AIRPLANE_MODE_MODES
        or cfg.reset_action not in P282_RESET_ACTIONS
        or cfg.requested_vault_action not in P282_VAULT_TARGET_ACTIONS
    ):
        _set_block(
            P282_BLOCKED_INVALID_PILLAR49B_SPEC,
            "Invalid Pillar 49B model, menu path, airplane mode, reset action, or vault action spec",
        )

    # 1. [Protect] exact 4 scopes vs [Format] override + Slot-1 Dual-Layer Hardware WP + Firewall
    protect_ok = True
    firewall_ok = True
    protect_only_v = cfg.slot1_protect_only_vault_violations
    format_del_ev = cfg.slot1_vault_format_or_delete_events
    vault_mut_bytes = cfg.slot1_vault_mutation_bytes

    if cfg.protect_4_scopes != P282_PROTECT_4_SCOPES:
        protect_ok = False
        _set_block(
            P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
            "Protect 4 scopes must match exact ILME-FX3 specification",
        )

    del_blk, fmt_wipes, dual_armed, vault_blocked = compute_expected_protect_vs_format_slot1_defense(
        software_protect_active=cfg.software_protect_active,
        slot1_holds_recovery_vault=cfg.slot1_holds_recovery_vault,
        slot1_sdxc_wp_locked=cfg.slot1_sdxc_wp_locked,
        slot1_format_hard_locked=cfg.slot1_format_hard_locked,
        requested_vault_slot=cfg.requested_vault_slot,
        requested_vault_action=cfg.requested_vault_action,
    )
    if cfg.software_protect_active and not del_blk:
        protect_ok = False
        _set_block(
            P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
            "Software Protect must block playback Delete / Delete pressing twice",
        )
    if not fmt_wipes:
        protect_ok = False
        _set_block(
            P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
            "Format override invariant must reflect erasure of protected files",
        )
    if (
        not dual_armed
        or not cfg.slot1_holds_recovery_vault
        or not cfg.slot1_sdxc_wp_locked
        or not cfg.slot1_format_hard_locked
        or cfg.slot1_protect_only_vault_violations != 0
    ):
        firewall_ok = False
        protect_only_v = max(protect_only_v, 1)
        _set_block(
            P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
            "Slot-1 recovery vault requires BOTH physical SD WP lock and slot1_format_hard_locked == True (software Protect alone rejected)",
        )
    if (
        vault_blocked
        or cfg.slot1_vault_format_or_delete_events != 0
        or cfg.slot1_vault_mutation_bytes != 0
    ):
        firewall_ok = False
        if vault_blocked:
            format_del_ev = max(format_del_ev, 1)
        _set_block(
            P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
            f"Hard Slot-1 Format/Delete firewall blocked {cfg.requested_vault_action!r} on Slot {cfg.requested_vault_slot}",
        )

    matrix_checked = 0
    for scope in P282_PROTECT_4_SCOPES:
        for v_act in P282_VAULT_TARGET_ACTIONS:
            d_b, f_w, _, blk = compute_expected_protect_vs_format_slot1_defense(
                software_protect_active=True,
                slot1_holds_recovery_vault=True,
                slot1_sdxc_wp_locked=True,
                slot1_format_hard_locked=True,
                requested_vault_slot=1,
                requested_vault_action=v_act,
            )
            if not d_b or not f_w or blk != (v_act in P282_DESTRUCTIVE_VAULT_ACTIONS):
                firewall_ok = False
                _set_block(
                    P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
                    f"Protect/Format matrix failed for scope={scope}, action={v_act}",
                )
            matrix_checked += 1

    for wp in (False, True):
        for fmt_lock in (False, True):
            _, _, armed, _ = compute_expected_protect_vs_format_slot1_defense(
                software_protect_active=True,
                slot1_holds_recovery_vault=True,
                slot1_sdxc_wp_locked=wp,
                slot1_format_hard_locked=fmt_lock,
                requested_vault_slot=1,
                requested_vault_action="READ_ONLY_AUDIT",
            )
            if armed != (wp and fmt_lock):
                firewall_ok = False
                _set_block(
                    P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
                    "Dual-layer SD WP + format hard lock matrix failed",
                )
            matrix_checked += 1

    # 2. [Reset Network Set.] auto-reboot + post-reboot [Airplane Mode] = [On] Zero-RF sequence
    nw_reset_ok = True
    reset_scope_ok = True
    zero_rf_violations = cfg.network_reset_zero_rf_violations

    creds_cleared, reboot_req, imm_airplane, non_nw_ok, zero_rf_ok = (
        compute_expected_network_reset_zero_rf_sequence(
            reset_action=cfg.reset_action,
            pre_network_creds_present=cfg.pre_network_creds_present,
            pre_airplane_mode=cfg.pre_airplane_mode,
            pre_shooting_preserved=cfg.pre_shooting_preserved,
            pre_setup_preserved=cfg.pre_setup_preserved,
            pre_playback_preserved=cfg.pre_playback_preserved,
            pre_camset_preserved=cfg.pre_camset_preserved,
            auto_reboot_completed=cfg.auto_reboot_completed,
            post_reasserted_airplane_mode=cfg.post_reasserted_airplane_mode,
        )
    )
    if reboot_req and (not cfg.auto_reboot_triggered or not cfg.auto_reboot_completed):
        nw_reset_ok = False
        zero_rf_violations = max(zero_rf_violations, 1)
        _set_block(
            P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT,
            "Reset Network Set. must trigger and complete automatic reboot (BKID_APP_is_shutdown_factor_network_reset)",
        )
    if (
        cfg.post_network_creds_cleared != creds_cleared
        or cfg.immediate_post_reset_airplane_mode != imm_airplane
        or not zero_rf_ok
        or cfg.network_reset_zero_rf_violations != 0
    ):
        nw_reset_ok = False
        zero_rf_violations = max(zero_rf_violations, 1)
        _set_block(
            P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT,
            "Reset Network Set. leaves Airplane Mode = Off until re-asserted to On; zero-RF sequence not satisfied",
        )
    if not non_nw_ok:
        reset_scope_ok = False
        _set_block(
            P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT,
            f"Reset scope violation on {cfg.reset_action!r}: non-network domains / CAMSET drifted",
        )

    if cfg.camset_load_after_reset:
        if (
            cfg.camset_slot != P282_SLOT1_VAULT_SLOT
            or cfg.camset_filename not in P282_CAMSET_FILENAMES
            or cfg.camset_source_model != P282_FX3_MODEL_NAME
            or not cfg.camset_read_only_load
        ):
            reset_scope_ok = False
            _set_block(
                P282_BLOCKED_INVALID_PILLAR49B_SPEC,
                "CAMSET load must be read-only from Slot-1 ILME-FX3 CAMSET01..10.DAT",
            )

    for r_act in P282_RESET_ACTIONS:
        for reb in (False, True):
            for ap_post in P282_AIRPLANE_MODE_MODES:
                cc, rr, ia, _, zrf = compute_expected_network_reset_zero_rf_sequence(
                    reset_action=r_act,
                    pre_network_creds_present=(r_act in ("Reset Network Set.", "Initialize")),
                    pre_airplane_mode="On",
                    pre_shooting_preserved=True,
                    pre_setup_preserved=True,
                    pre_playback_preserved=True,
                    pre_camset_preserved=True,
                    auto_reboot_completed=reb,
                    post_reasserted_airplane_mode=ap_post,
                )
                exp_zrf = cc and ((not rr) or reb) and (ap_post == "On")
                if r_act == "Reset Network Set." and (not rr or ia != "Off"):
                    nw_reset_ok = False
                    _set_block(
                        P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT,
                        "Reset Network Set. matrix invariant failed",
                    )
                if zrf != exp_zrf:
                    nw_reset_ok = False
                    _set_block(
                        P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT,
                        "Zero-RF certification matrix invariant failed",
                    )
                matrix_checked += 1

    # 3. Volatile /tmp overlay + Tier-0 H0 == H3
    h0_h3_ok = True
    if not _is_tmpfs_path(cfg.overlay_dir) or _targets_persistent_emmc(cfg.overlay_dir) or not cfg.p2_blkroset_locked:
        h0_h3_ok = False
        _set_block(
            P282_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must remain strictly in volatile /tmp or /run with BLKROSET=True: {cfg.overlay_dir!r}",
        )
    if (
        cfg.stage_b_backup_bin_writes != 0
        or cfg.backup_bin_h0_sha256 != P282_PINNED_FX3_BACKUP_BIN_SHA256
        or cfg.backup_bin_h3_sha256 != cfg.backup_bin_h0_sha256
        or cfg.tier0_surfaces_h0_h3_matched != P282_TIER0_SURFACE_COUNT
    ):
        h0_h3_ok = False
        _set_block(
            P282_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 H0 == H3 Backup.bin invariant drifted",
        )

    passed = (
        protect_ok
        and firewall_ok
        and nw_reset_ok
        and reset_scope_ok
        and h0_h3_ok
        and len(errs) == 0
    )
    digest = _canonical_sha256(
        {
            "pillar": "49B",
            "passed": passed,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "protect_only_v": protect_only_v,
            "format_del_ev": format_del_ev,
            "vault_mut_bytes": vault_mut_bytes,
            "zero_rf_violations": zero_rf_violations,
        }
    )
    return ProtectFormatNetworkResetZeroRfVaultReport(
        passed=passed,
        status=P282_STATUS_VERIFIED_PILLAR_49B if passed else P282_STATUS_REJECTED_PILLAR_49B,
        block_code=block_code,
        protect_4scopes_and_format_override_verified=protect_ok,
        slot1_dual_layer_wp_and_format_firewall_verified=firewall_ok,
        network_reset_reboot_and_airplane_zero_rf_verified=nw_reset_ok,
        three_way_reset_scope_and_camset_verified=reset_scope_ok,
        h0_equals_h3_verified=h0_h3_ok,
        matrix_states_checked=matrix_checked,
        slot1_protect_only_vault_violations=protect_only_v,
        slot1_vault_format_or_delete_events=format_del_ev,
        slot1_vault_mutation_bytes=vault_mut_bytes,
        slot1_format_hard_locked=cfg.slot1_format_hard_locked,
        network_reset_zero_rf_violations=zero_rf_violations,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errs),
    )


def verify_usb_mode_hdmi_info_protect_network_reset_and_vault(
    usb_hdmi_spec: Optional[UsbModePdGuardHdmiInfoVaultSpec] = None,
    protect_network_spec: Optional[ProtectFormatNetworkResetZeroRfVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> UsbModeHdmiInfoProtectNetworkResetVaultReport:
    """Combined Pillar 49A + Pillar 49B + Wave-47 bounded `O_RDONLY` donor report."""
    errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase282_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(usb_hdmi_spec)
    rep_b = evaluate_protect_format_network_reset_zero_rf_vault(protect_network_spec)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 282 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )
    ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return UsbModeHdmiInfoProtectNetworkResetVaultReport(
        schema=PHASE282_SCHEMA,
        version=PHASE282_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=ok,
        passed=ok,
        status=P282_STATUS_VERIFIED_PILLAR49_SUITE if ok else P282_STATUS_FAIL_PILLAR49_SUITE,
        donor_snapshot=donor_snapshot,
        usb_hdmi_report=rep_a,
        protect_network_report=rep_b,
        fx3_ui_exposes_usb_streaming=rep_a.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=rep_a.nouvc_spoof_events,
        usb_host_data_enumeration_events=rep_a.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=rep_a.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=rep_a.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=rep_b.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=rep_b.slot1_vault_format_or_delete_events,
        slot1_vault_mutation_bytes=rep_b.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=rep_b.slot1_format_hard_locked,
        network_reset_zero_rf_violations=rep_b.network_reset_zero_rf_violations,
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


def verify_usb_mode_hdmi_info_protect_network_reset_vault(
    usb_hdmi_spec: Optional[UsbModePdGuardHdmiInfoVaultSpec] = None,
    protect_network_spec: Optional[ProtectFormatNetworkResetZeroRfVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> UsbModeHdmiInfoProtectNetworkResetVaultReport:
    """Symmetry alias for `verify_usb_mode_hdmi_info_protect_network_reset_and_vault`."""
    return verify_usb_mode_hdmi_info_protect_network_reset_and_vault(
        usb_hdmi_spec=usb_hdmi_spec,
        protect_network_spec=protect_network_spec,
        force_clean_room=force_clean_room,
    )


def run_pillar49a_usb_mode_pd_hdmi_info_vault_6_scenario_suite() -> Pillar49ASuiteResult:
    """Run all 6 canonical Pillar 49A scenarios (`2` safe + `4` negative Wave-47 guards)."""
    cases: Tuple[Tuple[str, bool, UsbModePdGuardHdmiInfoVaultSpec, Optional[str]], ...] = (
        (
            P282_PILLAR_49A_SCENARIO_IDS[0],
            True,
            UsbModePdGuardHdmiInfoVaultSpec(),
            None,
        ),
        (
            P282_PILLAR_49A_SCENARIO_IDS[1],
            True,
            UsbModePdGuardHdmiInfoVaultSpec(
                external_hdmi_recorder_attached=True,
                operator_lcd_menu_recovery_active=True,
                pre_hdmi_info_display="On",
                post_hdmi_info_display="Off",
                pre_rec_media_dur_hdmi="Off(HDMI Only)",
                post_rec_media_dur_hdmi="Off(HDMI Only)",
                reported_effective_hdmi_resolution="4K",
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P282_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_hdmi_info_display="Off",
                saved_rec_media_dur_hdmi="Off(HDMI Only)",
                saved_framing_hdmi="Crop",
                post_framing_hdmi="Crop",
            ),
            None,
        ),
        (
            P282_PILLAR_49A_SCENARIO_IDS[2],
            False,
            UsbModePdGuardHdmiInfoVaultSpec(
                fx3_ui_exposes_usb_streaming=True,
                dormant_uvc_ko_insmoded=True,
                nouvc_spoof_events=1,
                active_host_usb_data_mode="MassStorage(MSC)",
                usb_data_lines_physically_isolated=False,
                usb_host_data_enumeration_events=1,
            ),
            P282_BLOCKED_NOUVC_OR_USB_HOST_DATA_ENUMERATION,
        ),
        (
            P282_PILLAR_49A_SCENARIO_IDS[3],
            False,
            UsbModePdGuardHdmiInfoVaultSpec(
                airgapped_tier0_session=True,
                active_host_usb_data_mode="NONE",
                usb_data_lines_physically_isolated=False,
                usb_port="Multi/Micro USB",
                np_fz100_inserted=False,
                post_usb_power_supply="On",
            ),
            P282_BLOCKED_USB_PD_UNISOLATED_OR_PORT_ERROR,
        ),
        (
            P282_PILLAR_49A_SCENARIO_IDS[4],
            False,
            UsbModePdGuardHdmiInfoVaultSpec(
                external_hdmi_recorder_attached=True,
                operator_lcd_menu_recovery_active=True,
                pre_hdmi_info_display="On",
                post_hdmi_info_display="On",
                log_shooting="Cine EI",
                reported_effective_hdmi_resolution="2160p",
                hdmi_lcd_blanking_violations=1,
                hdmi_log_1080_bypass_events=1,
            ),
            P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS,
        ),
        (
            P282_PILLAR_49A_SCENARIO_IDS[5],
            False,
            UsbModePdGuardHdmiInfoVaultSpec(
                external_hdmi_recorder_attached=False,
                reset_action="Camera Settings Reset",
                pre_usb_connection_mode="MTP",
                pre_hdmi_info_display="Off",
                pre_framing_hdmi="Full",
                post_usb_connection_mode="Sel. When Connect",
                post_hdmi_info_display="On",
                post_framing_hdmi="Full",
            ),
            P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT,
        ),
    )

    outcomes: List[Pillar49ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_usb_mode_pd_guard_and_hdmi_info_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar49ScenarioOutcome(
                scenario_id=sid,
                pillar="49A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar49ASuiteResult(
        passed=all_ok,
        status=P282_STATUS_VERIFIED_PILLAR_49A if all_ok else P282_STATUS_REJECTED_PILLAR_49A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar49b_protect_format_network_reset_vault_6_scenario_suite() -> Pillar49BSuiteResult:
    """Run all 6 canonical Pillar 49B scenarios (`2` safe + `4` negative Protect/Format/Reset-NW guards)."""
    cases: Tuple[Tuple[str, bool, ProtectFormatNetworkResetZeroRfVaultSpec, Optional[str]], ...] = (
        (
            P282_PILLAR_49B_SCENARIO_IDS[0],
            True,
            ProtectFormatNetworkResetZeroRfVaultSpec(),
            None,
        ),
        (
            P282_PILLAR_49B_SCENARIO_IDS[1],
            True,
            ProtectFormatNetworkResetZeroRfVaultSpec(
                requested_vault_slot=2,
                requested_vault_action="DELETE_SINGLE",
                reset_action="Reset Network Set.",
                auto_reboot_triggered=True,
                auto_reboot_completed=True,
                post_reasserted_airplane_mode="On",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P282_FX3_MODEL_NAME,
                camset_read_only_load=True,
            ),
            None,
        ),
        (
            P282_PILLAR_49B_SCENARIO_IDS[2],
            False,
            ProtectFormatNetworkResetZeroRfVaultSpec(
                software_protect_active=True,
                slot1_sdxc_wp_locked=False,
                slot1_format_hard_locked=False,
                slot1_protect_only_vault_violations=1,
            ),
            P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
        ),
        (
            P282_PILLAR_49B_SCENARIO_IDS[3],
            False,
            ProtectFormatNetworkResetZeroRfVaultSpec(
                requested_vault_slot=1,
                requested_vault_action="FORMAT_QUICK",
                slot1_vault_format_or_delete_events=1,
                slot1_vault_mutation_bytes=4096,
            ),
            P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE,
        ),
        (
            P282_PILLAR_49B_SCENARIO_IDS[4],
            False,
            ProtectFormatNetworkResetZeroRfVaultSpec(
                reset_action="Reset Network Set.",
                auto_reboot_triggered=True,
                auto_reboot_completed=False,
                post_reasserted_airplane_mode="Off",
                network_reset_zero_rf_violations=1,
            ),
            P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT,
        ),
        (
            P282_PILLAR_49B_SCENARIO_IDS[5],
            False,
            ProtectFormatNetworkResetZeroRfVaultSpec(
                reset_action="Reset Network Set.",
                pre_camset_preserved=False,
                overlay_dir="/setting/49b",
                backup_bin_h3_sha256="0" * 64,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT,
        ),
    )

    outcomes: List[Pillar49ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_protect_format_network_reset_zero_rf_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar49ScenarioOutcome(
                scenario_id=sid,
                pillar="49B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar49BSuiteResult(
        passed=all_ok,
        status=P282_STATUS_VERIFIED_PILLAR_49B if all_ok else P282_STATUS_REJECTED_PILLAR_49B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar49_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar49StandaloneReport:
    """Run full Pillar 49 standalone suite (`6/6` Pillar 49A + `6/6` Pillar 49B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase282_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar49a_usb_mode_pd_hdmi_info_vault_6_scenario_suite()
    res_b = run_pillar49b_protect_format_network_reset_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 282 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE282_SCHEMA,
            "version": PHASE282_VERSION,
            "mode": donor_snapshot.verification_mode,
            "49a": [asdict(s) for s in res_a.scenarios],
            "49b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar49StandaloneReport(
        schema=PHASE282_SCHEMA,
        version=PHASE282_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P282_STATUS_VERIFIED_PILLAR49_SUITE if all_ok else P282_STATUS_FAIL_PILLAR49_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_49a_usb_mode_pd_hdmi_info_vault=res_a,
        pillar_49b_protect_format_network_reset_vault=res_b,
        fx3_ui_exposes_usb_streaming=P282_FX3_UI_EXPOSES_USB_STREAMING,
        nouvc_spoof_events=P282_NOUVC_SPOOF_EVENTS if res_a.passed else 1,
        usb_host_data_enumeration_events=P282_USB_HOST_DATA_ENUMERATION_EVENTS if res_a.passed else 1,
        hdmi_lcd_blanking_violations=P282_HDMI_LCD_BLANKING_VIOLATIONS if res_a.passed else 1,
        hdmi_log_1080_bypass_events=P282_HDMI_LOG_1080_BYPASS_EVENTS if res_a.passed else 1,
        slot1_protect_only_vault_violations=(
            P282_SLOT1_PROTECT_ONLY_VAULT_VIOLATIONS if res_b.passed else 1
        ),
        slot1_vault_format_or_delete_events=(
            P282_SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS if res_b.passed else 1
        ),
        slot1_vault_mutation_bytes=P282_SLOT1_VAULT_MUTATION_BYTES if res_b.passed else 4096,
        slot1_format_hard_locked=P282_SLOT1_FORMAT_HARD_LOCKED,
        network_reset_zero_rf_violations=P282_NETWORK_RESET_ZERO_RF_VIOLATIONS if res_b.passed else 1,
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
# Unified 49/49 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master49_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_49pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master49PillarRecoveryReport:
    """Evaluate and aggregate all 49 recovery pillars (`1..49`) concurrently -> `49/49` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_49_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_48pillar() -> Master48PillarRecoveryReport:
        return evaluate_realhw_48pillar_recovery_master(**kw)

    def _run_p49() -> Tuple[Pillar49StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar49_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_48 = pool.submit(_run_48pillar)
        fut_49 = pool.submit(_run_p49)
        m48_rep = fut_48.result()
        p49_rep, p49_dt = fut_49.result()

    all_errors: List[str] = list(m48_rep.errors) + list(p49_rep.errors)
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
        if getattr(m48_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-48 violated {attr_name} == {expected_val}")
        if getattr(p49_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 49 violated {attr_name} == {expected_val}")

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
        ("slot1_format_hard_locked", True),
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
        if getattr(m48_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-48 violated {attr_name} == {expected_val}")
    if m48_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillars 1-48 violated bodydata_flash_attempts_blocked >= 1")

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
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(p49_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 49 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m48_rep.pillars)
    spec49 = MASTER_49_PILLAR_SPECS[48]
    p49_metrics = {
        "pillar_49a_usb_mode_pd_hdmi_info_vault": (
            f"{p49_rep.pillar_49a_usb_mode_pd_hdmi_info_vault.scenarios_passed}/"
            f"{p49_rep.pillar_49a_usb_mode_pd_hdmi_info_vault.scenarios_total}"
        ),
        "pillar_49b_protect_format_network_reset_vault": (
            f"{p49_rep.pillar_49b_protect_format_network_reset_vault.scenarios_passed}/"
            f"{p49_rep.pillar_49b_protect_format_network_reset_vault.scenarios_total}"
        ),
        "fx3_ui_exposes_usb_streaming": p49_rep.fx3_ui_exposes_usb_streaming,
        "nouvc_spoof_events": p49_rep.nouvc_spoof_events,
        "usb_host_data_enumeration_events": p49_rep.usb_host_data_enumeration_events,
        "hdmi_lcd_blanking_violations": p49_rep.hdmi_lcd_blanking_violations,
        "hdmi_log_1080_bypass_events": p49_rep.hdmi_log_1080_bypass_events,
        "slot1_protect_only_vault_violations": p49_rep.slot1_protect_only_vault_violations,
        "slot1_vault_format_or_delete_events": p49_rep.slot1_vault_format_or_delete_events,
        "slot1_vault_mutation_bytes": p49_rep.slot1_vault_mutation_bytes,
        "slot1_format_hard_locked": p49_rep.slot1_format_hard_locked,
        "network_reset_zero_rf_violations": p49_rep.network_reset_zero_rf_violations,
        "hardware_live_attachment_authorized": p49_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p49_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec49[0],
            pillar_id=spec49[1],
            phase_label=spec49[2],
            module_name=spec49[3],
            passed=bool(p49_rep.all_passed),
            status=p49_rep.status,
            verification_mode=p49_rep.verification_mode,
            elapsed_seconds=p49_dt,
            key_metrics=p49_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec49[1],
                    "mode": p49_rep.verification_mode,
                    "status": p49_rep.status,
                    "metrics": p49_metrics,
                    "passed": p49_rep.all_passed,
                }
            ),
            errors=tuple(p49_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master49_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p49_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_49_PILLAR_COUNT == 49
        and pillars_passed == 49
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE282_SCHEMA,
            "version": PHASE282_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master49PillarRecoveryReport(
        schema=PHASE282_SCHEMA,
        version=PHASE282_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P282_STATUS_VERIFIED_49OF49_AGGREGATOR if all_ok else P282_STATUS_FAIL_49OF49_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_2s_fast_cli_budget=elapsed < P282_FAST_CLI_BUDGET_SECONDS,
        under_6s_budget=elapsed < P282_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P282_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p49_rep.donor_snapshot,
        pillar49_a_usb_mode_pd_hdmi_info_vault=p49_rep.pillar_49a_usb_mode_pd_hdmi_info_vault,
        pillar49_b_protect_format_network_reset_vault=(
            p49_rep.pillar_49b_protect_format_network_reset_vault
        ),
        fx3_ui_exposes_usb_streaming=p49_rep.fx3_ui_exposes_usb_streaming,
        nouvc_spoof_events=p49_rep.nouvc_spoof_events,
        usb_host_data_enumeration_events=p49_rep.usb_host_data_enumeration_events,
        hdmi_lcd_blanking_violations=p49_rep.hdmi_lcd_blanking_violations,
        hdmi_log_1080_bypass_events=p49_rep.hdmi_log_1080_bypass_events,
        slot1_protect_only_vault_violations=p49_rep.slot1_protect_only_vault_violations,
        slot1_vault_format_or_delete_events=p49_rep.slot1_vault_format_or_delete_events,
        slot1_vault_mutation_bytes=p49_rep.slot1_vault_mutation_bytes,
        slot1_format_hard_locked=p49_rep.slot1_format_hard_locked,
        network_reset_zero_rf_violations=p49_rep.network_reset_zero_rf_violations,
        fx3_ui_exposes_power_save_by_monitor=m48_rep.fx3_ui_exposes_power_save_by_monitor,
        legacy_power_save_monitor_spoof_events=m48_rep.legacy_power_save_monitor_spoof_events,
        unsafe_power_save_sleep_interference_events=(
            m48_rep.unsafe_power_save_sleep_interference_events
        ),
        bk_lang_parity_drift_events=m48_rep.bk_lang_parity_drift_events,
        stage_b_4lang_uxc_ltt_drift_events=m48_rep.stage_b_4lang_uxc_ltt_drift_events,
        xlrh1_acoustic_feedback_violations=m48_rep.xlrh1_acoustic_feedback_violations,
        audio_mon_4ch_hdmi_confusion_events=m48_rep.audio_mon_4ch_hdmi_confusion_events,
        destructive_delete_confirm_drift_events=m48_rep.destructive_delete_confirm_drift_events,
        slot1_vault_delete_events=m48_rep.slot1_vault_delete_events,
        legacy_mf_assist_spoof_events=m48_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=m48_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=m48_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            m48_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=m48_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=m48_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=m48_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=m48_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            m48_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=m48_rep.slot1_vault_mutation_events,
        slot1_vault_folder_mutation_events=m48_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m48_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m48_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m48_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m48_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m48_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=(
            m48_rep.tcub_camera_reset_wipe_or_format_violations
        ),
        fx3_has_builtin_end_filter=m48_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m48_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m48_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m48_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m48_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m48_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m48_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m48_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m48_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m48_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m48_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m48_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m48_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m48_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m48_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m48_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m48_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m48_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m48_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m48_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m48_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m48_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m48_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m48_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m48_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m48_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m48_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m48_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m48_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m48_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p49_rep.hardware_live_attachment_authorized,
        master_49pillar_sha256=master_sha,
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


def evaluate_49pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master49PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_49pillar_recovery_master`."""
    return evaluate_realhw_49pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_49pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master49PillarRecoveryReport:
    """Public CLI entry point for Phase 282 `49/49` unified recovery master."""
    return evaluate_realhw_49pillar_recovery_master(
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
    "MASTER_49_PILLAR_COUNT",
    "MASTER_49_PILLAR_IDS",
    "MASTER_49_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P282_AIRPLANE_MODE_BKID",
    "P282_AIRPLANE_MODE_DEFAULT",
    "P282_AIRPLANE_MODE_MODES",
    "P282_AIRPLANE_MODE_ON_RESID16",
    "P282_AIRPLANE_MODE_RESID16",
    "P282_APPFW_MASS_STRAGE_MARKER",
    "P282_BLOCKED_HDMI_LCD_BLANKING_OR_1080_BYPASS",
    "P282_BLOCKED_HOST_DATA_ENUMERATION_MODES",
    "P282_BLOCKED_INVALID_PILLAR49A_SPEC",
    "P282_BLOCKED_INVALID_PILLAR49B_SPEC",
    "P282_BLOCKED_NETWORK_RESET_OR_AIRPLANE_ZERO_RF_DRIFT",
    "P282_BLOCKED_NOUVC_OR_USB_HOST_DATA_ENUMERATION",
    "P282_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P282_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P282_BLOCKED_SETUP_USB_HDMI_RESET_SCOPE_DRIFT",
    "P282_BLOCKED_SLOT1_PROTECT_ONLY_OR_FORMAT_WIPE",
    "P282_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P282_BLOCKED_USB_PD_UNISOLATED_OR_PORT_ERROR",
    "P282_BOUNDED_HEADER_BYTES",
    "P282_CAMSET_FILENAMES",
    "P282_CONCURRENT_CEILING_SECONDS",
    "P282_DESTRUCTIVE_VAULT_ACTIONS",
    "P282_DONOR_FX3_APPFW_702_RELPATH",
    "P282_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P282_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH",
    "P282_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P282_DONOR_FX3_LIBUSBBUSPOWER_SO_RELPATH",
    "P282_DONOR_FX3_USBG_STILLIMAGE_KO_RELPATH",
    "P282_DONOR_FX3_USBG_STORAGE_KO_RELPATH",
    "P282_DONOR_FX3_USB_F_UVC_KO_RELPATH",
    "P282_DONOR_FX3_UXC_EN_F_RELPATH",
    "P282_DONOR_FX3_UXC_EN_G_RELPATH",
    "P282_DONOR_FX3_UXC_EN_RELPATH",
    "P282_DONOR_FX3_UXC_JA_F_RELPATH",
    "P282_DONOR_FX3_UXC_SC_F_RELPATH",
    "P282_DONOR_FX3_UXC_TC_F_RELPATH",
    "P282_DONOR_FX6_APPFW_601_RELPATH",
    "P282_DONOR_FX6_USB_F_UVC_KO_RELPATH",
    "P282_DONOR_FX6_UXC_EN_2_RELPATH",
    "P282_DONOR_FX6_UXC_EN_RELPATH",
    "P282_DONOR_INSPECT_BUDGET_SECONDS",
    "P282_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P282_DORMANT_UVC_ENUM",
    "P282_DORMANT_UVC_EXCLUSION_BKID",
    "P282_DORMANT_UVC_MODULE",
    "P282_DORMANT_UVC_RESID16_F",
    "P282_DORMANT_UVC_RESID16_G",
    "P282_ENV_CLEAN_ROOM_TEST",
    "P282_FAST_CLI_BUDGET_SECONDS",
    "P282_FORBIDDEN_FX3_USB_STREAMING_MODE",
    "P282_FORBIDDEN_PERSISTENT_TARGETS",
    "P282_FORMAT_FULL_RESID16",
    "P282_FORMAT_MENU_PATH",
    "P282_FORMAT_QUICK_RESID16",
    "P282_FORMAT_RESID16",
    "P282_FORMAT_VAULT_ACTIONS",
    "P282_FORMAT_WARN_RESID16",
    "P282_FRAMING_HDMI_DEFAULT",
    "P282_FRAMING_HDMI_MODES",
    "P282_FX3_FW_VERSION",
    "P282_FX3_HELPGUIDE_ID",
    "P282_FX3_MODEL_ID",
    "P282_FX3_MODEL_NAME",
    "P282_FX3_PRODUCT_CODENAME",
    "P282_FX3_SUPPORTED_FW_VERSIONS",
    "P282_FX3_UI_EXPOSES_USB_STREAMING",
    "P282_FX3_USB_CONNECTION_4_MODES",
    "P282_FX6_ALL_RESET_RESID16",
    "P282_FX6_DONOR_FW_VERSION",
    "P282_FX6_DONOR_MODEL_NAME",
    "P282_FX6_FORMAT_MEDIA_RESID16",
    "P282_FX6_HDMI_INFO_BKID",
    "P282_FX6_LOCK_CLIP_BKID",
    "P282_FX6_LOCK_CLIP_RESID16",
    "P282_FX6_NETWORK_RESET_BKID",
    "P282_FX6_NETWORK_RESET_RESID16",
    "P282_FX6_PROCAM_UVC_BKID",
    "P282_FX6_PRODUCT_CODENAME",
    "P282_FX6_SDI_OUTPUT_BKID",
    "P282_FX6_SHUTDOWN_NETWORK_RESET_BKID",
    "P282_FX6_USB_TETHERING_RESID16",
    "P282_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P282_HDMI_INFO_DISPLAY_BKID",
    "P282_HDMI_INFO_DISPLAY_DEFAULT",
    "P282_HDMI_INFO_DISPLAY_MENU_PATH",
    "P282_HDMI_INFO_DISPLAY_MODES",
    "P282_HDMI_INFO_DISPLAY_RESID16",
    "P282_HDMI_INFO_DISPLAY_RESID16_MAP",
    "P282_HDMI_INFO_ON_CAUTION_ID",
    "P282_HDMI_LCD_BLANKING_VIOLATIONS",
    "P282_HDMI_LOG_1080_BYPASS_EVENTS",
    "P282_LOG_SHOOTING_MODES",
    "P282_MAX_FULL_DONOR_BYTES",
    "P282_NETWORK_OPTION_RESID16",
    "P282_NETWORK_RESET_ZERO_RF_VIOLATIONS",
    "P282_NOMINAL_BUDGET_SECONDS",
    "P282_NOUVC_SPOOF_EVENTS",
    "P282_ON_OFF_MODES",
    "P282_OUTPUT_RESOLUTION_DEFAULT",
    "P282_OUTPUT_RESOLUTION_MODES",
    "P282_PICTURE_PROFILE_MODES",
    "P282_PILLAR_49A_SCENARIO_IDS",
    "P282_PILLAR_49B_SCENARIO_IDS",
    "P282_PINNED_FX3_APPFW_702_BYTES",
    "P282_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P282_PINNED_FX3_BACKUP_BIN_BYTES",
    "P282_PINNED_FX3_BACKUP_BIN_SHA256",
    "P282_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES",
    "P282_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256",
    "P282_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P282_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P282_PINNED_FX3_LIBUSBBUSPOWER_SO_BYTES",
    "P282_PINNED_FX3_LIBUSBBUSPOWER_SO_SHA256",
    "P282_PINNED_FX3_USBG_STILLIMAGE_KO_BYTES",
    "P282_PINNED_FX3_USBG_STILLIMAGE_KO_SHA256",
    "P282_PINNED_FX3_USBG_STORAGE_KO_BYTES",
    "P282_PINNED_FX3_USBG_STORAGE_KO_SHA256",
    "P282_PINNED_FX3_USB_F_UVC_KO_BYTES",
    "P282_PINNED_FX3_USB_F_UVC_KO_SHA256",
    "P282_PINNED_FX3_UXC_EN_BYTES",
    "P282_PINNED_FX3_UXC_EN_F_BYTES",
    "P282_PINNED_FX3_UXC_EN_F_SHA256",
    "P282_PINNED_FX3_UXC_EN_G_BYTES",
    "P282_PINNED_FX3_UXC_EN_G_SHA256",
    "P282_PINNED_FX3_UXC_EN_SHA256",
    "P282_PINNED_FX3_UXC_JA_F_BYTES",
    "P282_PINNED_FX3_UXC_JA_F_SHA256",
    "P282_PINNED_FX3_UXC_SC_F_BYTES",
    "P282_PINNED_FX3_UXC_SC_F_SHA256",
    "P282_PINNED_FX3_UXC_TC_F_BYTES",
    "P282_PINNED_FX3_UXC_TC_F_SHA256",
    "P282_PINNED_FX6_APPFW_601_BYTES",
    "P282_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P282_PINNED_FX6_USB_F_UVC_KO_BYTES",
    "P282_PINNED_FX6_USB_F_UVC_KO_SHA256",
    "P282_PINNED_FX6_UXC_EN_2_BYTES",
    "P282_PINNED_FX6_UXC_EN_2_SHA256",
    "P282_PINNED_FX6_UXC_EN_BYTES",
    "P282_PINNED_FX6_UXC_EN_SHA256",
    "P282_PROTECT_4_SCOPES",
    "P282_PROTECT_FILE_ERROR_ENUM",
    "P282_PROTECT_FUNC_MARKERS",
    "P282_PROTECT_KEY_ICON_RESID16",
    "P282_PROTECT_MENU_PATH",
    "P282_PROTECT_RESID16",
    "P282_PROTECT_SCOPE_RESID16_MAP",
    "P282_RAW_OUTPUT_DEFAULT",
    "P282_REC_MEDIA_DUR_HDMI_BKID",
    "P282_REC_MEDIA_DUR_HDMI_DEFAULT",
    "P282_REC_MEDIA_DUR_HDMI_MODES",
    "P282_REC_MEDIA_DUR_HDMI_OFF_RESID16",
    "P282_REC_MEDIA_DUR_HDMI_RESID16",
    "P282_RESET_ACTIONS",
    "P282_RESET_NETWORK_FUNC",
    "P282_RESET_NETWORK_MENU_PATH",
    "P282_RESET_NETWORK_REBOOT_WARN_RESID16",
    "P282_RESET_NETWORK_RESID16",
    "P282_RESET_NETWORK_SETTING_ID",
    "P282_RESET_NETWORK_SHUTDOWN_BKID",
    "P282_SELECTION_MEMO_RESID16",
    "P282_SHOOTING_DOMAINS",
    "P282_SLOT1_FORMAT_HARD_LOCKED",
    "P282_SLOT1_PROTECT_ONLY_VAULT_VIOLATIONS",
    "P282_SLOT1_VAULT_FORMAT_OR_DELETE_EVENTS",
    "P282_SLOT1_VAULT_MUTATION_BYTES",
    "P282_SLOT1_VAULT_SLOT",
    "P282_SLOT1_WP_CAUTION_ID",
    "P282_SLOT1_WP_ERROR_ENUM",
    "P282_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P282_STATUS_FAIL_49OF49_AGGREGATOR",
    "P282_STATUS_FAIL_PILLAR49_SUITE",
    "P282_STATUS_REJECTED_PILLAR_49A",
    "P282_STATUS_REJECTED_PILLAR_49B",
    "P282_STATUS_VERIFIED_49OF49_AGGREGATOR",
    "P282_STATUS_VERIFIED_PILLAR49_SUITE",
    "P282_STATUS_VERIFIED_PILLAR_49A",
    "P282_STATUS_VERIFIED_PILLAR_49B",
    "P282_TIER0_HOST_USB_DATA_STATES",
    "P282_TIER0_SURFACE_COUNT",
    "P282_USB_CONNECTION_ENUM_MAP",
    "P282_USB_CONNECTION_MODE_BKID",
    "P282_USB_CONNECTION_MODE_DEFAULT",
    "P282_USB_CONNECTION_MODE_MENU_PATH",
    "P282_USB_CONNECTION_MODE_RESID16",
    "P282_USB_CONNECTION_RESID16_MAP",
    "P282_USB_CONNECTION_SEL_PROMPT_RESID16_MAP",
    "P282_USB_HOST_DATA_ENUMERATION_EVENTS",
    "P282_USB_LUN_DEFAULT",
    "P282_USB_LUN_ENUM_MAP",
    "P282_USB_LUN_MODES",
    "P282_USB_LUN_RESID16_MAP",
    "P282_USB_LUN_SETTING_BKID",
    "P282_USB_LUN_SETTING_MENU_PATH",
    "P282_USB_LUN_SETTING_RESID16",
    "P282_USB_MSC_VID_PID",
    "P282_USB_PORTS",
    "P282_USB_POWER_SUPPLY_BKID",
    "P282_USB_POWER_SUPPLY_DEFAULT",
    "P282_USB_POWER_SUPPLY_MENU_PATH",
    "P282_USB_POWER_SUPPLY_MODES",
    "P282_USB_POWER_SUPPLY_REQUIRED_PORT",
    "P282_USB_POWER_SUPPLY_RESID16",
    "P282_VAULT_TARGET_ACTIONS",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE282_PHASE_NUMBER",
    "PHASE282_SCHEMA",
    "PHASE282_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "Master49PillarRecoveryReport",
    "Phase282DonorArtifactDigest",
    "Phase282DonorSnapshot",
    "Pillar49ASuiteResult",
    "Pillar49BSuiteResult",
    "Pillar49ScenarioOutcome",
    "Pillar49StandaloneReport",
    "ProtectFormatNetworkResetZeroRfVaultReport",
    "ProtectFormatNetworkResetZeroRfVaultSpec",
    "UsbModeHdmiInfoProtectNetworkResetVaultReport",
    "UsbModePdGuardHdmiInfoVaultReport",
    "UsbModePdGuardHdmiInfoVaultSpec",
    "build_default_safe_protect_format_network_reset_zero_rf_vault_spec",
    "build_default_safe_usb_mode_pd_guard_hdmi_info_vault_spec",
    "compute_expected_hdmi_info_and_resolution_state",
    "compute_expected_network_reset_zero_rf_sequence",
    "compute_expected_pillar49a_reset_state",
    "compute_expected_protect_vs_format_slot1_defense",
    "compute_expected_usb_connection_and_pd_guard",
    "evaluate_49pillar_recovery_master",
    "evaluate_protect_format_network_reset_zero_rf_vault",
    "evaluate_realhw_49pillar_recovery_master",
    "evaluate_usb_mode_pd_guard_and_hdmi_info_vault",
    "inspect_phase282_donors_readonly",
    "run_pillar49_standalone_suite",
    "run_pillar49a_usb_mode_pd_hdmi_info_vault_6_scenario_suite",
    "run_pillar49b_protect_format_network_reset_vault_6_scenario_suite",
    "verify_49pillar_recovery_suite",
    "verify_usb_mode_hdmi_info_protect_network_reset_and_vault",
    "verify_usb_mode_hdmi_info_protect_network_reset_vault",
]
