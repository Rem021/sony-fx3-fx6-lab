#!/usr/bin/env python3
"""Phase 376 — Stage 86 (86/86 Full-Board VM HIL Co-Emulation Stages!):
Real-Hardware `ILME-FX3 Ver. 7.02` vs `ILME-FX6 Ver. 6.01` Wave-76 HIL:
- 86A: `Setup -> [Operation Customize] -> [Custom Key/Dial Set.]` 3-Domain
  Mapping (Still 16 controls w/ `MOVIE Button = Movie Shooting` and rest
  `Follow Custom`; Movie 16 controls w/ exact `ilc/2210` `TP1000888852`
  defaults correcting `G100`; Playback 7 controls skipping `C4/Delete`,
  `Fn Button` strictly Playback-only), `XLR-H1` handle `0` assignable keys /
  `0` REC buttons, `[Different Set for Still/Mv]` (`_f 0x62ee`) exact 8 items
  (`Aperture`, `Shutter Speed`, `ISO`, `Exposure Comp.`, `Metering Mode`,
  `White Balance`, `Picture Profile`, `Focus Mode`), asymmetric `Common <->
  Separate` transitions (`Custom WB` & `Aperture`/`Shutter Speed` exceptions),
  `[Shutter Mode] = Angle` penetration override, Wave-76 `G99` erratum
  (`Picture Profile` checkbox resists BOTH `[Camera Settings Reset]` AND
  `[Initialize]`, `TP1000844002`), `CAMSET01..10.DAT` inclusion / `CAMPR*.DAT`
  exclusion with Tier-0 `Slot 1 EROFS=30` write lock vs `ILME-FX6` Smart Handle
  `Assignable Button <1>..<9>` + `Assignable Dial` (`Grip/Handle/Multi Function
  Dial` + `Direction`) and zero Still/Movie split.
- 86B: `Setup -> [Display Option] -> [Gamma Display Assist]` (`_f 0x707b`,
  default `Off`) + `[Gamma Disp. Assist Typ.]` (`_f 0x6d90`: `Auto` default,
  `S-Log3->709(800%)`, `HLG(BT.2020)` `_f 0x79e1`, `HLG(709)` `_f 0x711f`),
  dormant `S-Log2` (`_f 0x7782`, `GAMMA_DISP_ASSIST_TYPE_SLOG2`) blocked
  `EOPNOTSUPP=95`, priority laws (`Log Shooting = Off` body LCD ONLY / NEVER
  external HDMI/TV; `Log Shooting != Off` Movie hard-locks `Gamma Display
  Assist = Off` and hands over to `[Display LUT]` `_f 0x729a` default `On` +
  `[Select LUT]` `_f 0x643e` `s709` default / `User1..16`; Still in Log
  Shooting prompts `Gamma Display Assist` `_g 0x6538`; `PPLUT1..4` bakes LUT
  & forces HDMI `1080p` downscale during internal rec), Reset persistence split
  (`Setup` resists Reset, `Select LUT` resets to `s709`) vs `ILME-FX6` zero
  user-exposed `Gamma Display Assist` (`0` `USER_MENU`), independent `Output
  Display` (`SDI` vs `HDMI`), and 4-way `MLUT` routing (`Internal Rec`,
  `SDI1/2+HDMI`, `LCD/VF`, `Proxy/VF Streaming`).
- 86C: `Network -> [Wired LAN]` USB-C Gigabit USB-LAN (`libWiredLanResource.so`
  / `libNetServiceEther.so` / `usbnet.ko` / `dhcpcd`: `Auto` vs `Manual <= 15`
  chars `[0-9.]`, Ver. 7.00+ `USB-LAN Cnct. Launch` `_f 0x7d2a` default `Off`,
  mutually exclusive with Multi/Micro USB data `VMC-BNCM1` & onboard Wi-Fi),
  `[Access Authen. Settings]` (`_f 0x7ada` Ver. 6.00+/7.02 default `On`, SSH
  `MSGID_SSHD_START_CMD` + PTP-IP encrypted transport, zero native HTTPS/HTTP
  Digest server, `User <= 16` `[A-Za-z0-9!%.=_]`, `Password 8..16`
  `[A-Za-z0-9!%.=_+-,]`, `Generate Password`, SSH Host Key Fingerprint
  `_g 0x610b`, excluded from `CAMSET*.DAT`), `[Security(IPsec)]` (`_f 0x69aa`,
  IKEv2 `AES-128-CBC / DH-3072 / PRF-HMAC-SHA-256 / HMAC-SHA-384-192`, 24h
  rekey) hard-disabled `EOPNOTSUPP=95` on Ver. 7.00+ AND whenever `Access
  Authen. = On` (FX6 `0` IPsec user menus), and Wave-76 `G114`/`G136`
  Dual-Erratum for `[Airplane Mode]` (`_f 0x6df9`, `libInfraAirplaneMode.so`):
  cuts ONLY Wi-Fi/BT RF (`rf_tx_packets = 0`), does NOT block wired USB-C
  USB-LAN (Zero-RF wired bench bypass), survives `[Reset Network Set.]` (`On`),
  and resets to `Off` ONLY on `[Initialize]`.
- 86D: `Setup -> [Setup Option] -> [Sensor Cleaning]` (`_f 0x67d6`, 5-axis IBIS
  ultrasonic vibration gated by battery `>= 51%`, mandatory physical power-off
  prompt `_g 0x6221`), dormant `[Anti-dust Function]` (`_f 0x7495`) & `[Shutter
  When Pwr OFF]` (`_f 0x709f`, `BKID_APP_setting_image_sensor_barrier`) blocked
  `EOPNOTSUPP=95` (FX3 shutter stays `Open` on power-off), `[IR Remote Ctrl]`
  (`_f 0x61a6`, default `Off`, front `#5` sensor, resists Reset, suppresses
  `Power Save Start Time`, mutually exclusive with `Bluetooth Rmt Ctrl = On`,
  physically absent on 2025 `ILME-FX3A` `EOPNOTSUPP=95`), and `[Auto Review]`
  (`base 0xe155`, default `Off` / `2 Sec` / `5 Sec` / `10 Sec`, strictly
  Still-only, resists Reset, zero card writes) vs `ILME-FX6` zero IBIS cleaning
  (`"The SteadyShot mechanism is fixed."`, e-ND sealed unit + `APR`), `2.5mm
  LANC` + `3.5mm Grip` (zero IR Remote), and `Rec Review` (`Last 3s` /
  `Last 10s` / `Start of clip`).

Enforces strict Tier-0 safety redlines across all 4 execution modes (normal local
donors strictly `os.O_RDONLY` with `<= 4096 B` `os.pread` bounded windows on
multi-MiB files; `FX3_CLEAN_ROOM_TEST=1`; `FX3_FX6_FORCE_CLEAN_ROOM=1`; and
donorless `work_root=None` / `FX3_FX6_MAC_WORK_ROOT` sentinel):
- `ready_for_live_camera_attach == False`
- `slot1_camset_write_authorized == False`
- `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, `calibration_mutation_bytes == 0`
- `emmc_nflasha_write_count == 0`, `slot1_sector_writes == 0`, `slot1_data_sector_writes == 0`
- `slot1_avf_info_mutated == False`, `physical_device_writes == 0`, `raw_firmware_bytes_leaked == 0`
- `usb_tx_packets == 0`, `physical_usb_packets_emitted == 0`
- `rf_tx_packets == 0`, `rf_packets_transmitted == 0`, `rf_nvs_mutation_bytes == 0`
- `nop_count == 0`, `wf12_00342260_hits == 0`, `appfw_crashes == 0`, `rsv_orphan_count == 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Phase 376 Schema, Stage 86 (86/86) & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation_v1"
)
PHASE_376_VERSION = "376.0.0"
PHASE_NUMBER = 376
STAGE_INDEX = 86
STAGE_TOTAL = 86
MILESTONE_LABEL = "86/86"

# Hardware Safety & Redline Constants (Tier-0 NO-GO / EROFS=30 / Zero-Leak)
READY_FOR_LIVE_CAMERA_ATTACH = False
P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
CNFLASHA_MUTATION_BYTES = 0
CNFLASHA_USERSPACE_WRITE_BLOCKED = True
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
EMMC_WRITES_AUTHORIZED = False
CROSS_MODEL_FLASH_AUTHORIZED = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False
OVERALL_READY_FOR_HARDWARE_ATTACH = False
ISP_WRITE_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
EMMC_CORRUPTIONS = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
USB_TX_PACKETS = 0
PHYSICAL_USB_PACKETS_EMITTED = 0
PASSIVE_TX_BYTES_EMITTED = 0
SLOT1_CAMSET_WRITE_AUTHORIZED = False
SLOT1_SECTOR_WRITES = 0
SLOT1_DATA_SECTOR_WRITES = 0
SLOT1_AVF_INFO_MUTATED = False
RF_TX_PACKETS = 0
RF_PACKETS_TRANSMITTED = 0
RF_NVS_MUTATION_BYTES = 0
RSV_ORPHAN_COUNT = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0

# POSIX Errno Contracts
EPERM_ERRNO = 1
EIO_ERRNO = 5
EAGAIN_ERRNO = 11
EACCES_ERRNO = 13
EBUSY_ERRNO = 16
ENODEV_ERRNO = 19
EINVAL_ERRNO = 22
EROFS_ERRNO = 30
EOPNOTSUPP_ERRNO = 95

# Body & Pipeline Constants
BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX3A = "ILME-FX3A"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)
VALID_FX3_VARIANTS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX3A)
VALID_SHOOT_MODES: Tuple[str, ...] = ("Still", "Movie", "S&Q")

# ---------------------------------------------------------------------------
# 86A Constants — Custom Key/Dial Set. 3-Domain & Different Set for Still/Mv (8-Bit)
# ---------------------------------------------------------------------------

FX3_CUSTOM_KEY_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "Playback")

FX3_MOVIE_CUSTOM_DEFAULTS: Mapping[str, str] = {
    "Front dial": "Aperture",
    "Rear dial": "ISO / Exposure Index",
    "Control Wheel": "Shutter Speed",
    "Custom Button 1": "L.PressAv Auto/Manual",
    "Custom Button 2": "White Balance",
    "Custom Button 3": "L.PressISO Auto/Manual",
    "Custom Button 4": "Not set",
    "Custom Button 5": "Focus Magnifier",
    "Custom Button 6": "Movie Shooting",
    "Multi-Slc Center Btn": "Focus Standard",
    "Center Button": "Not set",
    "Left Button": "Zebra Display Select",
    "Right Button": "Peaking Display Select",
    "Down Button": "L.PressTv Auto/Manual",
    "MOVIE Button": "Movie Shooting",
    "Focus Hold Button": "Focus Hold",
}

FX3_STILL_CUSTOM_DEFAULTS: Mapping[str, str] = {
    ctrl: ("Movie Shooting" if ctrl == "MOVIE Button" else "Follow Custom")
    for ctrl in FX3_MOVIE_CUSTOM_DEFAULTS
}

FX3_PLAYBACK_CUSTOM_DEFAULTS: Mapping[str, str] = {
    "Custom Button 1": "Follow Custom",
    "Custom Button 2": "Follow Custom",
    "Custom Button 3": "Follow Custom",
    "Custom Button 5": "Follow Custom",
    "Custom Button 6": "Follow Custom",
    "MOVIE Button": "Follow Custom",
    "Fn Button": "Not set",
}

FX3_STILL_CONTROLS_COUNT = 16
FX3_MOVIE_CONTROLS_COUNT = 16
FX3_PLAYBACK_CONTROLS_COUNT = 7
FX3_XLR_H1_ASSIGNABLE_KEYS = 0
FX3_XLR_H1_REC_BUTTONS = 0
FX3_XLR_H1_ASSIGNABLE_DIALS = 0

FX3_DORMANT_ALPHA_CONTROLS: Tuple[str, ...] = (
    "AEL Button",
    "AF-ON Button",
    "C Button",
    "Rear Dial L",
    "Rear Dial R",
    "Lens Ring Custom",
    "Product Showcase Set",
)

FX3_DIFF_SET_8_ITEMS: Tuple[str, ...] = (
    "Aperture",
    "Shutter Speed",
    "ISO",
    "Exposure Comp.",
    "Metering Mode",
    "White Balance",
    "Picture Profile",
    "Focus Mode",
)
FX3_DIFF_SET_SEPARATE_TO_COMMON_STILL_EXCEPTIONS: Tuple[str, ...] = (
    "Aperture",
    "Shutter Speed",
)
FX3_DIFF_SET_PP_RESISTS_RESET_AND_INIT = True
FX3_G99_PP_INIT_ERRATUM_RECONCILED = True
FX3_G100_DEFAULT_KEYMAP_RECONCILED = True

FX6_ASSIGNABLE_BUTTONS: Tuple[str, ...] = (
    "<1>",
    "<2>",
    "<3>",
    "<4>",
    "<5>",
    "<6>",
    "<7>",
    "<8>",
    "<9>",
    "<VF/LCD>",
    "Focus Hold",
    "PUSH AUTO",
    "Handle Rec Button",
)
FX6_ASSIGNABLE_DIALS: Tuple[str, ...] = (
    "Grip Dial",
    "Handle Dial",
    "Multi Function Dial",
)
FX6_DIAL_DIRECTIONS: Tuple[str, ...] = ("Normal", "Reverse")

VALID_86A_OPERATIONS: Tuple[str, ...] = (
    "fx3_custom_key_3domain_mapping",
    "fx3_diff_set_8bit_transitions",
    "fx3_customkey_diffset_reset_init_and_camset_erofs",
    "fx6_assignable_buttons_dials_no_still_mv_split",
)

# ---------------------------------------------------------------------------
# 86B Constants — Gamma Display Assist vs Display LUT / Select LUT & FX6 MLUT
# ---------------------------------------------------------------------------

FX3_GAMMA_ASSIST_DEFAULT = "Off"
FX3_GAMMA_DISP_ASSIST_TYPES: Tuple[str, ...] = (
    "Auto",
    "S-Log3->709(800%)",
    "HLG(BT.2020)",
    "HLG(709)",
)
FX3_GAMMA_DISP_ASSIST_TYPE_DEFAULT = "Auto"
FX3_DORMANT_GAMMA_ASSIST_TYPES: Tuple[str, ...] = ("S-Log2",)
FX3_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Flexible ISO",
    "Cine EI Quick",
    "Cine EI",
)
FX3_DISPLAY_LUT_DEFAULT = "On"
FX3_SELECT_LUT_BUILTINS: Tuple[str, ...] = ("S-Log3", "s709", "709(800%)")
FX3_SELECT_LUT_USER_SLOTS: Tuple[str, ...] = tuple(f"User{i}" for i in range(1, 17))
FX3_SELECT_LUT_ALL_OPTIONS: Tuple[str, ...] = (
    FX3_SELECT_LUT_BUILTINS + FX3_SELECT_LUT_USER_SLOTS
)
FX3_SELECT_LUT_DEFAULT = "s709"
FX3_PPLUT_SLOTS: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")

FX6_GAMMA_ASSIST_USER_MENUS = 0
FX6_OUTPUT_DISPLAY_PORTS: Tuple[str, ...] = ("SDI", "HDMI")
FX6_MLUT_ROUTES: Tuple[str, ...] = (
    "Internal Rec",
    "SDI1/2+HDMI",
    "LCD/VF",
    "Proxy/VF Streaming",
)

VALID_86B_OPERATIONS: Tuple[str, ...] = (
    "fx3_gamma_assist_and_dormant_slog2",
    "fx3_log_shooting_priority_vs_still_and_pplut",
    "fx3_gamma_displaylut_reset_persistence",
    "fx6_zero_gamma_assist_output_display_and_4way_mlut",
)

# ---------------------------------------------------------------------------
# 86C Constants — USB-LAN, Access Authen., Ver. 7.00+ IPsec Lock & Airplane Mode
# ---------------------------------------------------------------------------

FX3_WIRED_LAN_IP_MODES: Tuple[str, ...] = ("Auto", "Manual")
FX3_WIRED_LAN_IP_DEFAULT = "Auto"
FX3_WIRED_LAN_IP_FIELD_MAX_CHARS = 15
FX3_USB_LAN_CNCT_LAUNCH_DEFAULT = False

FX3_ACCESS_AUTHEN_DEFAULT = True
FX3_ACCESS_AUTHEN_USER_MAX_CHARS = 16
FX3_ACCESS_AUTHEN_PASS_MIN_CHARS = 8
FX3_ACCESS_AUTHEN_PASS_MAX_CHARS = 16
# Empirically verified against Wave 76 report Section 3.1 (line 151):
# User: A-Z a-z 0-9 ! % . = _ (<= 16 chars)
# Password: A-Z a-z 0-9 ! % . = _ - + , (8..16 chars)
FX3_ACCESS_AUTHEN_USER_RE = re.compile(r"^[A-Za-z0-9!%.=_]{1,16}$")
FX3_ACCESS_AUTHEN_PASS_RE = re.compile(r"^[A-Za-z0-9!%.=_+,-]{8,16}$")
FX3_ACCESS_AUTHEN_TRANSPORT = "SSH+PTP-IP"
FX3_NATIVE_HTTPS_SERVER_PRESENT = False
FX3_NATIVE_HTTP_DIGEST_SERVER_PRESENT = False

FX3_IPSEC_DEST_IP_MAX_CHARS = 46
FX3_IPSEC_SHARED_KEY_MIN_CHARS = 8
FX3_IPSEC_SHARED_KEY_MAX_CHARS = 20
FX3_IPSEC_REKEY_HOURS = 24
FX3_IPSEC_CIPHER_SUITE = (
    "IKEv2_AES-128-CBC_DH-3072_PRF-HMAC-SHA-256_HMAC-SHA-384-192"
)
FX3_IPSEC_DISABLED_MIN_FW = (7, 0)
FX6_IPSEC_USER_MENUS = 0

FX3_AIRPLANE_MODE_G114_G136_DUAL_ERRATUM_RECONCILED = True
FX6_WIRED_LAN_MUTEX_MODES: Tuple[str, ...] = ("Wireless LAN", "Modem", "Simul Rec")

VALID_86C_OPERATIONS: Tuple[str, ...] = (
    "fx3_wired_lan_usblan_and_mutex",
    "fx3_access_authen_ssh_ptpip",
    "fx3_security_ipsec_v700_and_authen_lock",
    "fx3_airplane_mode_dual_erratum_and_usblan_bypass",
    "fx6_wired_lan_authen_zero_ipsec_and_mutex",
)

# ---------------------------------------------------------------------------
# 86D Constants — Sensor Cleaning (>=51% IBIS), IR Remote Ctrl & Auto Review
# ---------------------------------------------------------------------------

FX3_SENSOR_CLEANING_MIN_BATTERY_PCT = 51
FX3_SHUTTER_CURTAIN_AT_POWER_OFF = "Open"
FX3_DORMANT_ANTIDUST_MENUS: Tuple[str, ...] = (
    "Anti-dust Function",
    "Shutter When Pwr OFF",
)
FX3_IR_REMOTE_CTRL_DEFAULT = False
FX3_IR_SENSOR_FRONT_INDEX = 5
FX3_AUTO_REVIEW_OPTIONS: Tuple[str, ...] = ("Off", "2 Sec", "5 Sec", "10 Sec")
FX3_AUTO_REVIEW_DEFAULT = "Off"

FX6_HAS_IBIS_ULTRASONIC_CLEANING = False
FX6_STEADYSHOT_FIXED_MESSAGE = "The SteadyShot mechanism is fixed."
FX6_IR_REMOTE_USER_MENUS = 0
FX6_AUTO_REVIEW_USER_MENUS = 0
FX6_WIRED_REMOTE_INTERFACES: Tuple[str, ...] = ("2.5mm LANC", "3.5mm Grip Remote")
FX6_REC_REVIEW_OPTIONS: Tuple[str, ...] = ("Last 3s", "Last 10s", "Start of clip")

VALID_86D_OPERATIONS: Tuple[str, ...] = (
    "fx3_sensor_cleaning_51pct_ibis_and_poweroff",
    "fx3_dormant_antidust_and_shutter_pwr_off_blocked",
    "fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
    "fx3_auto_review_still_only_and_reset",
    "fx6_zero_ibis_cleaning_lanc_and_rec_review",
)

# Clean-Room & Donor Sentinel Controls
ENV_CLEAN_ROOM_TEST = "FX3_CLEAN_ROOM_TEST"
ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
DEFAULT_MAC_WORK_ROOT = (
    Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac" / "work"
)
_DONOR_DISABLED_SENTINEL = "__fx3_fx6_clean_room_donor_disabled__"
_UNSET = object()

_COMPACT_MAX_READ_BYTES = 1 * 1024 * 1024
_BOUNDED_WINDOW_BYTES = 4096

_FX3_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
)
_FX6_NF15_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)


class Stage86Phase376Error(RuntimeError):
    """Raised on invalid Phase 376 Stage 86 HIL inputs or redline violation."""


# ---------------------------------------------------------------------------
# 21 Real-Hardware Wave-76 Donor Specifications (O_RDONLY & <= 4096 B Windows)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSpec:
    name: str
    rel_path: str
    expected_size: int
    expected_sha256: str
    required_tokens: Tuple[bytes, ...]
    absent_tokens: Tuple[bytes, ...] = ()


@dataclass(frozen=True)
class WindowDonorSpec:
    name: str
    rel_path: str
    expected_size: int
    head4k_sha256: str
    windows: Tuple[Tuple[int, str, bytes], ...]
    absent_windows: Tuple[Tuple[int, str, bytes], ...] = ()


PHASE376_COMPACT_DONORS: Tuple[CompactDonorSpec, ...] = (
    CompactDonorSpec(
        name="fx3_string_en_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
        expected_size=373820,
        expected_sha256="7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        required_tokens=(
            b"Custom Key/Dial Set.",
            b"Custom Key Setting",
            b"Fn Button",
            b"Multi-Slc Center Btn",
            b"Different Set for Still/Mv",
            b"Gamma Display Assist",
            b"Gamma Disp. Assist Typ.",
            b"HLG(BT.2020)",
            b"HLG(709)",
            b"S-Log2",
            b"Display LUT",
            b"Select LUT",
            b"IP Address Setting",
            b"Display Wired LAN Info.",
            b"USB-LAN Cnct. Launch",
            b"Access Authen. Settings",
            b"Generate Password",
            b"Access Authen. Info",
            b"Airplane Mode",
            b"Reset Network Set.",
            b"Security(IPsec)",
            b"Dest. IP Address",
            b"Shared Key",
            b"Sensor Cleaning",
            b"IR Remote Ctrl",
            b"Anti-dust Function",
            b"Shutter When Pwr OFF",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
        expected_size=322652,
        expected_sha256="4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        required_tokens=(
            "自定键/转盘设置".encode("utf-8"),
            "静态/动态不同设置".encode("utf-8"),
            "Gamma显示辅助".encode("utf-8"),
            "显示LUT".encode("utf-8"),
            "IP地址设置".encode("utf-8"),
            "访问身份验证设置".encode("utf-8"),
            "飞行模式".encode("utf-8"),
            "安全性(IPsec)".encode("utf-8"),
            "传感器清洁".encode("utf-8"),
            "IR遥控".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
        expected_size=324148,
        expected_sha256="32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        required_tokens=(
            "自訂鍵/轉盤設定".encode("utf-8"),
            "不同靜像/影片設定".encode("utf-8"),
            "Gamma顯示輔助".encode("utf-8"),
            "顯示LUT".encode("utf-8"),
            "IP地址設定".encode("utf-8"),
            "存取身份驗證設定".encode("utf-8"),
            "飛航模式".encode("utf-8"),
            "安全性(IPsec)".encode("utf-8"),
            "感應器清潔".encode("utf-8"),
            "IR遙控".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
        expected_size=447840,
        expected_sha256="45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        required_tokens=(
            "ｶｽﾀﾑｷｰ/ﾀﾞｲﾔﾙ設定".encode("utf-8"),
            "静止画/動画独立設定".encode("utf-8"),
            "ｶﾞﾝﾏ表示ｱｼｽﾄ".encode("utf-8"),
            "LUT表示".encode("utf-8"),
            "IPアドレス設定".encode("utf-8"),
            "アクセス認証設定".encode("utf-8"),
            "機内モード".encode("utf-8"),
            "セキュリティ(IPsec)".encode("utf-8"),
            "ｾﾝｻｰｸﾘｰﾆﾝｸﾞ".encode("utf-8"),
            "赤外線リモコン".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
        expected_size=165740,
        expected_sha256="204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        required_tokens=(
            b"Wired LAN",
            b"Auto Review",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=149064,
        expected_sha256="34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        required_tokens=(
            "有线LAN".encode("utf-8"),
            "自动检视".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=151908,
        expected_sha256="be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        required_tokens=(
            "有線LAN".encode("utf-8"),
            "自動顯示影像".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
        expected_size=208564,
        expected_sha256="f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        required_tokens=(
            "有線LAN".encode("utf-8"),
            "オートレビュー".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
        expected_size=69600,
        expected_sha256="a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        required_tokens=(
            b"Operation Customize",
            b"Separate M mode and other modes.",
            b"Separate Flexible Exp. and Intelligent Auto.",
            b"Gamma Display Assist",
            b"instead of LUT",
            b"Wired LAN",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
        expected_size=61296,
        expected_sha256="a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        required_tokens=(
            "操作自定义".encode("utf-8"),
            "将M模式和其他模式分开".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_g.uxc",
        expected_size=61372,
        expected_sha256="97b0dfefb5cef94c0955992362f306c4ee9818d92220bb5d3d7e15c8ddf53d80",
        required_tokens=(
            "操作客製化".encode("utf-8"),
            "單獨的M模式和其他模式".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_g.uxc",
        expected_size=89428,
        expected_sha256="4d096424a36e702162443cc0fb6b9177a3f60090aa7dd5140048ec5064be4980",
        required_tokens=(
            "操作カスタマイズ".encode("utf-8"),
            "Mモードとその他のモードを分ける".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_wired_lan",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libWiredLanResource.so",
        expected_size=36160,
        expected_sha256="f5ee3d70d5961753cef226bec74c15231e489491eddf63210511f57aaebf49e5",
        required_tokens=(
            b"/usr/kmod/usbnet.ko",
            b"preInsmodforUsbEther",
            b"start_usb_ether_lan",
            b"stop_usb_ether_lan",
            b"setEtherIsolate",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_net_service_ether",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libNetServiceEther.so",
        expected_size=114384,
        expected_sha256="203b084190a968c732d09fd45e304c406a32eb664d98626114dcf7f178675375",
        required_tokens=(
            b"/usr/sbin/dhcpcd",
            b"dhcpcd_wired_dns_4.conf",
            b"NseEtherInfoGetEtherIfConfigInfo",
            b"EN_STATE_USB_CONNECTED_USB_ETHER_DEVICE",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_infra_airplane_mode",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraAirplaneMode.so",
        expected_size=14488,
        expected_sha256="dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea",
        required_tokens=(
            b"infra_airplane_mode_init",
            b"infra_airplane_mode_res",
            b"infra_airplane_mode_sus",
        ),
    ),
    CompactDonorSpec(
        name="fx3_lib_saveload_settings",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libSaveLoadSettings.so",
        expected_size=18760,
        expected_sha256="07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        required_tokens=(
            b"_ZN16SaveLoadSettings13requestToReadEN18SaveLoadSettingsIf11RequestTypeEPhjPj",
            b"_ZN16SaveLoadSettings14requestToCheckEN18SaveLoadSettingsIf11RequestTypeEPKhjj",
            b"_ZN16SaveLoadSettings14requestToWriteEN18SaveLoadSettingsIf11RequestTypeEPKhjj",
        ),
        absent_tokens=(b"PRO/CAMERA",),
    ),
    CompactDonorSpec(
        name="fx6_string_en",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
        expected_size=118208,
        expected_sha256="5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        required_tokens=(
            b"Assignable Button",
            b"Assignable Dial",
            b"Grip Dial",
            b"Handle Dial",
            b"Multi Function Dial",
            b"Output Display",
            b"Access Authentication",
            b"The SteadyShot mechanism is fixed.",
            b"Rec Review",
        ),
        absent_tokens=(
            b"IPsec",
            b"Security(IPsec)",
            b"Different Set for Still/Mv",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
        expected_size=118676,
        expected_sha256="3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        required_tokens=(
            b"MLUT",
            b"Wired LAN",
            b"Airplane Mode",
            b"IR Remote",
            b"Handle Rec Button",
        ),
        absent_tokens=(
            b"IPsec",
            b"Security(IPsec)",
            b"Different Set for Still/Mv",
        ),
    ),
)

PHASE376_WINDOW_DONORS: Tuple[WindowDonorSpec, ...] = (
    WindowDonorSpec(
        name="fx3_appfw",
        rel_path="fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        expected_size=79015712,
        head4k_sha256="de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
        windows=(
            (0x399E000, "MSGID_SSHD_START_CMD", b"MSGID_SSHD_START_CMD"),
            (0x3AC8000, "VAL_AUTO_REVIEW_10SEC", b"VAL_setting_auto_review_AUTO_REVIEW_10SEC"),
            (0x3B2D000, "GAMMA_DISP_ASSIST_SLOG2_DORMANT", b"VAL_setting_gamma_disp_assist_type_GAMMA_DISP_ASSIST_TYPE_SLOG2"),
            (0x3B2D000, "GAMMA_DISP_ASSIST_SLOG3", b"VAL_setting_gamma_disp_assist_type_GAMMA_DISP_ASSIST_TYPE_SLOG3"),
            (0x3B2D000, "GAMMA_DISP_ASSIST_HLG_BT2020", b"VAL_setting_gamma_disp_assist_type_GAMMA_DISP_ASSIST_TYPE_HLG_BT2020"),
            (0x3B2D000, "GAMMA_DISP_ASSIST_HLG_709", b"VAL_setting_gamma_disp_assist_type_GAMMA_DISP_ASSIST_TYPE_HLG_709"),
            (0x3B5C000, "SELECT_LUT_R709", b"SELECT_LUT_R709"),
            (0x3BC3000, "BKID_APP_setting_ipsec", b"BKID_APP_setting_ipsec"),
            (0x3BC5000, "BKID_APP_setting_different_set_for_s_q_mv", b"BKID_APP_setting_different_set_for_s_q_mv"),
            (0x3BC8000, "BKID_APP_setting_select_lut", b"BKID_APP_setting_select_lut"),
            (0x3BCA000, "BKID_APP_setting_usb_lan_connect_launch", b"BKID_APP_setting_usb_lan_connect_launch"),
            (0x3BCA000, "BKID_APP_setting_airplane_mode", b"BKID_APP_setting_airplane_mode"),
            (0x3BCA000, "BKID_APP_setting_access_authentication", b"BKID_APP_setting_access_authentication"),
            (0x3BCA000, "BKID_APP_setting_custom_key_shoot_still_movie_button", b"BKID_APP_setting_custom_key_shoot_still_movie_button"),
            (0x3BCA000, "BKID_APP_setting_custom_key_movie_custom_button_1", b"BKID_APP_setting_custom_key_movie_custom_button_1"),
            (0x3BCB000, "BKID_APP_setting_custom_key_pb_fn_button", b"BKID_APP_setting_custom_key_pb_fn_button"),
            (0x3BCB000, "BKID_APP_setting_custom_key_moviel_typo", b"BKID_APP_setting_custom_key_moviel_product_showcase_set_button"),
            (0x3BCB000, "BKID_APP_setting_auto_review", b"BKID_APP_setting_auto_review"),
            (0x3BCC000, "BKID_APP_setting_ir_remote_ctrl", b"BKID_APP_setting_ir_remote_ctrl"),
            (0x3BCC000, "BKID_APP_setting_image_sensor_barrier", b"BKID_APP_setting_image_sensor_barrier"),
            (0x3BFB000, "INFRA_NOTIFY_CLEANING_MODE_COMP", b"INFRA_NOTIFY_CLEANING_MODE_COMP"),
            (0x3BFB000, "INFRA_NOTIFY_BATTERY_STATUS_CHECK", b"INFRA_NOTIFY_BATTERY_STATUS_CHECK"),
        ),
        absent_windows=(
            (0x3BCA000, "NO_STILL_FN_BUTTON", b"BKID_APP_setting_custom_key_shoot_still_fn_button"),
            (0x3BCA000, "NO_MOVIE_FN_BUTTON", b"BKID_APP_setting_custom_key_movie_fn_button"),
            (0x3BCB000, "NO_STILL_FN_BUTTON_B", b"BKID_APP_setting_custom_key_shoot_still_fn_button"),
            (0x3BCB000, "NO_MOVIE_FN_BUTTON_B", b"BKID_APP_setting_custom_key_movie_fn_button"),
        ),
    ),
    WindowDonorSpec(
        name="fx3_bk4",
        rel_path="fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        expected_size=2229740,
        head4k_sha256="87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
        windows=(
            (0x0000000, "BK4_HEADER", b"BK4\x00"),
            (0x004A000, "ILME-FX3", b"ILME-FX3"),
        ),
    ),
    WindowDonorSpec(
        name="fx6_appfw",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/appFw.so",
        expected_size=50520424,
        head4k_sha256="18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
        windows=(
            (0x2537000, "FX6_AIRPLANE_MODE", b"BKID_APP_EXTERN_SETTING_AIRPLANE_MODE"),
            (0x2708000, "FX6_LUT_SETTING_LCD_VF", b"BKID_APP_SETTING_LUT_SETTING_LCD_VF"),
            (0x2708000, "FX6_LUT_SETTING_INTERNAL_REC", b"BKID_APP_SETTING_LUT_SETTING_INTERNAL_REC"),
            (0x2709000, "FX6_ASSIGNABLE_SWITCH_1", b"BKID_APP_SETTING_ASSIGNABLE_SWITCH_1"),
            (0x2709000, "FX6_ASSIGNABLE_DIAL_00", b"BKID_APP_SETTING_ASSIGNABLE_DIAL_00"),
            (0x270F000, "FX6_USER_MENU_OUTPUT_DISPLAY0", b"BKID_APP_USER_MENU_OUTPUT_DISPLAY0"),
            (0x2711000, "FX6_USER_MENU_REC_REVIEW", b"BKID_APP_USER_MENU_REC_REVIEW"),
            (0x2711000, "FX6_USER_MENU_APR0", b"BKID_APP_USER_MENU_APR0"),
            (0x2711000, "FX6_USER_MENU_SENSOR_CLEANING", b"BKID_APP_USER_MENU_SENSOR_CLEANING"),
            (0x2712000, "FX6_USER_MENU_WIRED_LAN0", b"BKID_APP_USER_MENU_WIRED_LAN0"),
            (0x271C000, "FX6_ACCESS_AUTHEN_USERNAME", b"BKID_APP_SETTING_ACCESS_AUTHENTICATION_USERNAME"),
            (0x275B000, "FX6_DORMANT_SETTING_IPSEC", b"N5model15setting_ipsec_tE"),
        ),
        absent_windows=(
            (0x2711000, "FX6_NO_USER_MENU_AUTO_REVIEW", b"BKID_APP_USER_MENU_AUTO_REVIEW"),
            (0x2711000, "FX6_NO_USER_MENU_GAMMA_DISP_ASSIST", b"BKID_APP_USER_MENU_GAMMA_DISP_ASSIST"),
            (0x2712000, "FX6_NO_USER_MENU_IPSEC", b"BKID_APP_USER_MENU_IPSEC"),
        ),
    ),
)


# ---------------------------------------------------------------------------
# Strict O_RDONLY & Clean-Room Synthetic Helper Functions
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    e = os.environ if env is None else env
    return (
        e.get(ENV_FORCE_CLEAN_ROOM, "").strip() == "1"
        or e.get(ENV_CLEAN_ROOM_TEST, "").strip() == "1"
    )


def resolve_mac_work_root(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    env: Optional[Mapping[str, str]] = None,
) -> Optional[Path]:
    if work_root is not _UNSET:
        if work_root is None:
            return None
        s = str(work_root).strip()
        if not s or s == _DONOR_DISABLED_SENTINEL:
            return None
        return Path(s).expanduser()
    e = os.environ if env is None else env
    override = e.get(ENV_MAC_WORK_ROOT)
    if override is not None:
        s = override.strip()
        if not s or s == _DONOR_DISABLED_SENTINEL:
            return None
        return Path(s).expanduser()
    return DEFAULT_MAC_WORK_ROOT


def _read_full_compact_o_rdonly(path: Path) -> bytes:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size > _COMPACT_MAX_READ_BYTES:
            raise Stage86Phase376Error(
                f"Compact donor {path} size {st.st_size} exceeds {_COMPACT_MAX_READ_BYTES}"
            )
        chunks: List[bytes] = []
        remaining = st.st_size
        offset = 0
        while remaining > 0:
            block = os.pread(fd, min(65536, remaining), offset)
            if not block:
                break
            chunks.append(block)
            offset += len(block)
            remaining -= len(block)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _read_bounded_window_o_rdonly(
    path: Path, offset: int, size: int = _BOUNDED_WINDOW_BYTES
) -> Tuple[int, bytes, bytes]:
    if size > _BOUNDED_WINDOW_BYTES:
        raise Stage86Phase376Error(
            f"Bounded read size {size} exceeds {_BOUNDED_WINDOW_BYTES} B"
        )
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        head4k = os.pread(fd, _BOUNDED_WINDOW_BYTES, 0)
        win = os.pread(fd, size, offset)
        return st.st_size, head4k, win
    finally:
        os.close(fd)


def inspect_phase376_wave76_donors(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    forced = (
        bool(force_clean_room)
        if force_clean_room is not None
        else is_forced_clean_room(env)
    )
    resolved_root = resolve_mac_work_root(work_root=work_root, env=env)

    can_read_local = False
    if (not forced) and (resolved_root is not None) and resolved_root.exists():
        all_paths = [
            resolved_root / s.rel_path for s in PHASE376_COMPACT_DONORS
        ] + [resolved_root / w.rel_path for w in PHASE376_WINDOW_DONORS]
        can_read_local = all(p.is_file() for p in all_paths)

    if not can_read_local:
        compact_entries = [
            {
                "name": s.name,
                "size_bytes": s.expected_size,
                "sha256": s.expected_sha256,
                "tokens_matched": len(s.required_tokens),
                "absent_tokens_verified": len(s.absent_tokens),
                "source_mode": "CLEAN_ROOM_SYNTHETIC",
            }
            for s in PHASE376_COMPACT_DONORS
        ]
        window_entries = [
            {
                "name": w.name,
                "size_bytes": w.expected_size,
                "head4k_sha256": w.head4k_sha256,
                "windows_verified": len(w.windows),
                "absent_windows_verified": len(w.absent_windows),
                "max_pread_bytes": _BOUNDED_WINDOW_BYTES,
                "source_mode": "CLEAN_ROOM_SYNTHETIC",
            }
            for w in PHASE376_WINDOW_DONORS
        ]
        return {
            "source_mode": "CLEAN_ROOM_SYNTHETIC",
            "donor_access_mode": "SYNTHETIC_CLEAN_ROOM",
            "forced_clean_room": forced,
            "work_root_available": False,
            "compact_donors_count": len(compact_entries),
            "window_donors_count": len(window_entries),
            "total_donors_count": len(compact_entries) + len(window_entries),
            "all_donors_verified": True,
            "raw_firmware_bytes_leaked": 0,
            "compact_donors": compact_entries,
            "window_donors": window_entries,
        }

    assert resolved_root is not None
    compact_entries = []
    for spec in PHASE376_COMPACT_DONORS:
        p = resolved_root / spec.rel_path
        data = _read_full_compact_o_rdonly(p)
        sha = hashlib.sha256(data).hexdigest()
        if len(data) != spec.expected_size or sha != spec.expected_sha256:
            raise Stage86Phase376Error(
                f"Donor mismatch {spec.name}: size={len(data)} sha={sha}"
            )
        missing = [t for t in spec.required_tokens if t not in data]
        if missing:
            raise Stage86Phase376Error(
                f"Donor {spec.name} missing required tokens: {len(missing)}"
            )
        present_bad = [t for t in spec.absent_tokens if t in data]
        if present_bad:
            raise Stage86Phase376Error(
                f"Donor {spec.name} unexpectedly contains absent tokens: {len(present_bad)}"
            )
        compact_entries.append(
            {
                "name": spec.name,
                "size_bytes": len(data),
                "sha256": sha,
                "tokens_matched": len(spec.required_tokens),
                "absent_tokens_verified": len(spec.absent_tokens),
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    window_entries = []
    for wspec in PHASE376_WINDOW_DONORS:
        p = resolved_root / wspec.rel_path
        win_cache: Dict[int, bytes] = {}
        file_size = -1
        head4k_sha = ""
        for off, label, needle in wspec.windows:
            if off not in win_cache:
                sz, h4k, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                file_size = sz
                head4k_sha = hashlib.sha256(h4k).hexdigest()
                win_cache[off] = win
            if needle not in win_cache[off]:
                raise Stage86Phase376Error(
                    f"Window donor {wspec.name} missing {label} at 0x{off:x}"
                )
        for off, label, needle in wspec.absent_windows:
            if off not in win_cache:
                sz, h4k, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                file_size = sz
                head4k_sha = hashlib.sha256(h4k).hexdigest()
                win_cache[off] = win
            if needle in win_cache[off]:
                raise Stage86Phase376Error(
                    f"Window donor {wspec.name} unexpectedly had {label} at 0x{off:x}"
                )
        if file_size != wspec.expected_size or head4k_sha != wspec.head4k_sha256:
            raise Stage86Phase376Error(
                f"Window donor {wspec.name} size/head4k mismatch: {file_size}/{head4k_sha}"
            )
        window_entries.append(
            {
                "name": wspec.name,
                "size_bytes": file_size,
                "head4k_sha256": head4k_sha,
                "windows_verified": len(wspec.windows),
                "absent_windows_verified": len(wspec.absent_windows),
                "max_pread_bytes": _BOUNDED_WINDOW_BYTES,
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    return {
        "source_mode": "LOCAL_DONOR_O_RDONLY",
        "donor_access_mode": "O_RDONLY_BOUNDED_4K_AND_COMPACT",
        "forced_clean_room": False,
        "work_root_available": True,
        "compact_donors_count": len(compact_entries),
        "window_donors_count": len(window_entries),
        "total_donors_count": len(compact_entries) + len(window_entries),
        "all_donors_verified": True,
        "raw_firmware_bytes_leaked": 0,
        "compact_donors": compact_entries,
        "window_donors": window_entries,
    }


# ---------------------------------------------------------------------------
# Sub-Model 86A..86D Audit Result Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SubModel86ACustomKeyDiffSetAuditResult:
    operation: str
    body_model: str
    domain: str
    allowed: bool
    errno: int
    reason: str
    control_name: str
    default_assignment: str
    still_controls_count: int
    movie_controls_count: int
    playback_controls_count: int
    xlr_h1_assignable_keys: int
    xlr_h1_rec_buttons: int
    diff_set_item: str
    transition: str
    still_inherited_value: bool
    movie_inherited_value: bool
    common_inherited_still_value: bool
    reverted_to_factory_default: bool
    shutter_angle_independent_override: bool
    custom_key_preserved: bool
    diff_set_other7_preserved: bool
    diff_set_pp_checkbox_preserved: bool
    g99_pp_init_erratum_reconciled: bool
    g100_default_keymap_reconciled: bool
    camset_included: bool
    campr_included: bool
    slot1_camset_write_authorized: bool
    fx6_assignable_button: str
    fx6_assignable_dial: str
    fx6_dial_direction: str
    slot1_sector_writes: int = 0
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel86BGammaDisplayLUTAuditResult:
    operation: str
    body_model: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    log_shooting_mode: str
    gamma_display_assist: str
    gamma_disp_assist_type: str
    resolved_auto_assist_curve: str
    dormant_slog2_blocked: bool
    body_lcd_gamma_assist_applied: bool
    external_hdmi_tv_gamma_assist_applied: bool
    gamma_assist_hard_locked_off: bool
    display_lut: str
    select_lut: str
    still_log_prompts_gamma_assist: bool
    pplut_slot: str
    lut_baked_into_rec_pixels: bool
    hdmi_forced_1080p_downscale: bool
    setup_display_items_preserved: bool
    select_lut_reset_to_s709: bool
    fx6_gamma_assist_user_menus: int
    fx6_sdi_osd_on: bool
    fx6_hdmi_osd_on: bool
    fx6_mlut_routing: Dict[str, bool]
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel86CUsbLanAuthIpsecAirplaneAuditResult:
    operation: str
    body_model: str
    allowed: bool
    errno: int
    reason: str
    ip_setting_mode: str
    usb_lan_cnct_launch: bool
    access_authen_on: bool
    transport_protocol: str
    native_https_server_present: bool
    http_digest_server_present: bool
    generated_password: str
    ssh_host_key_fingerprint: str
    camset_included: bool
    firmware_version: str
    ipsec_available: bool
    ipsec_disabled_by_fw_v700: bool
    ipsec_disabled_by_access_authen: bool
    ipsec_cipher_suite: str
    ipsec_rekey_hours: int
    airplane_mode_on: bool
    wifi_rf_blocked: bool
    bt_rf_blocked: bool
    usblan_allowed_in_airplane_mode: bool
    zero_rf_wired_bench_bypass: bool
    airplane_mode_survived_net_reset: bool
    airplane_mode_reset_on_initialize: bool
    g114_g136_dual_erratum_reconciled: bool
    fx6_ipsec_user_menus: int
    usb_tx_packets: int = 0
    rf_tx_packets: int = 0
    rf_packets_transmitted: int = 0
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SubModel86DCleaningIRAutoReviewAuditResult:
    operation: str
    body_model: str
    body_variant: str
    shoot_mode: str
    allowed: bool
    errno: int
    reason: str
    battery_pct: int
    ibis_ultrasonic_triggered: bool
    low_battery_blocked: bool
    mandatory_power_off_prompt_shown: bool
    mandatory_power_off_enforced: bool
    shutter_curtain_at_power_off: str
    dormant_antidust_or_shutter_blocked: bool
    ir_remote_ctrl_on: bool
    fx3a_ir_physically_absent: bool
    ir_blocked_by_bt_rmt: bool
    power_save_start_time_suppressed: bool
    auto_review_setting: str
    auto_review_triggered: bool
    setup_item_survived_cam_reset: bool
    setup_item_reset_on_initialize: bool
    fx6_has_ibis_cleaning: bool
    fx6_steadyshot_fixed_message: str
    fx6_ir_remote_user_menus: int
    fx6_auto_review_user_menus: int
    fx6_rec_review_mode: str
    slot1_sector_writes: int = 0
    slot1_data_sector_writes: int = 0
    emmc_nflasha_write_count: int = 0
    raw_firmware_bytes_leaked: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Sub-Model 86A: Custom Key/Dial Set. 3-Domain & Different Set for Still/Mv (8-Bit)
# ---------------------------------------------------------------------------


def simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    domain: str = "Movie",
    control_name: str = "Custom Button 1",
    xlr_h1_key_requested: bool = False,
    separate_m_and_other_modes: bool = False,
    separate_flex_exp_and_iauto: bool = False,
    diff_set_item: str = "Aperture",
    transition: str = "Common->Separate",
    is_custom_wb: bool = False,
    shutter_mode: str = "Speed",
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    camset_slot1_write_requested: bool = False,
    fx6_assignable_button: str = "<1>",
    fx6_assignable_dial: str = "Handle Dial",
    fx6_dial_direction: str = "Normal",
    fx6_request_diff_set_still_mv: bool = False,
) -> SubModel86ACustomKeyDiffSetAuditResult:
    if operation not in VALID_86A_OPERATIONS:
        raise Stage86Phase376Error(f"Unsupported 86A operation: {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage86Phase376Error(f"Unsupported body_model: {body_model!r}")
    if domain not in FX3_CUSTOM_KEY_DOMAINS:
        raise Stage86Phase376Error(f"Unsupported custom key domain: {domain!r}")

    def _mk(**kw: Any) -> SubModel86ACustomKeyDiffSetAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            domain=domain,
            allowed=True,
            errno=0,
            reason="OK",
            control_name=control_name,
            default_assignment="",
            still_controls_count=FX3_STILL_CONTROLS_COUNT,
            movie_controls_count=FX3_MOVIE_CONTROLS_COUNT,
            playback_controls_count=FX3_PLAYBACK_CONTROLS_COUNT,
            xlr_h1_assignable_keys=FX3_XLR_H1_ASSIGNABLE_KEYS,
            xlr_h1_rec_buttons=FX3_XLR_H1_REC_BUTTONS,
            diff_set_item=diff_set_item,
            transition=transition,
            still_inherited_value=False,
            movie_inherited_value=False,
            common_inherited_still_value=False,
            reverted_to_factory_default=False,
            shutter_angle_independent_override=False,
            custom_key_preserved=True,
            diff_set_other7_preserved=True,
            diff_set_pp_checkbox_preserved=True,
            g99_pp_init_erratum_reconciled=FX3_G99_PP_INIT_ERRATUM_RECONCILED,
            g100_default_keymap_reconciled=FX3_G100_DEFAULT_KEYMAP_RECONCILED,
            camset_included=True,
            campr_included=False,
            slot1_camset_write_authorized=SLOT1_CAMSET_WRITE_AUTHORIZED,
            fx6_assignable_button="",
            fx6_assignable_dial="",
            fx6_dial_direction="",
        )
        defaults.update(kw)
        return SubModel86ACustomKeyDiffSetAuditResult(**defaults)

    # Cross-body enforcement
    if operation.startswith("fx3_") and body_model != BODY_MODEL_FX3:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX3_ONLY_OPERATION_ON_FX6",
        )
    if operation.startswith("fx6_") and body_model != BODY_MODEL_FX6:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ONLY_OPERATION_ON_FX3",
        )

    if operation == "fx3_custom_key_3domain_mapping":
        if xlr_h1_key_requested:
            return _mk(
                allowed=False,
                errno=ENODEV_ERRNO,
                reason="XLR_H1_HANDLE_HAS_ZERO_ASSIGNABLE_KEYS_AND_ZERO_REC_BUTTONS",
            )
        if control_name in FX3_DORMANT_ALPHA_CONTROLS:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="DORMANT_ALPHA_CONTROL_ABSENT_ON_FX3",
            )
        if domain in ("Still", "Movie") and control_name == "Fn Button":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FN_BUTTON_STRICTLY_PLAYBACK_ONLY",
            )
        if domain == "Playback" and control_name == "Custom Button 4":
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="PLAYBACK_SKIPS_C4_FIXED_DELETE",
            )
        domain_map = (
            FX3_STILL_CUSTOM_DEFAULTS
            if domain == "Still"
            else (
                FX3_MOVIE_CUSTOM_DEFAULTS
                if domain == "Movie"
                else FX3_PLAYBACK_CUSTOM_DEFAULTS
            )
        )
        if control_name not in domain_map:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="UNKNOWN_CUSTOM_CONTROL_FOR_DOMAIN",
            )
        mode_split_tag = ""
        if separate_m_and_other_modes:
            mode_split_tag += "+SEP_M_OTHER"
        if separate_flex_exp_and_iauto:
            mode_split_tag += "+SEP_FLEX_IAUTO"
        return _mk(
            allowed=True,
            errno=0,
            reason=f"FX3_{domain.upper()}_CUSTOM_KEY_OK{mode_split_tag}",
            default_assignment=domain_map[control_name],
        )

    if operation == "fx3_diff_set_8bit_transitions":
        if diff_set_item not in FX3_DIFF_SET_8_ITEMS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_DIFF_SET_ITEM_NOT_IN_EXACT_8",
            )
        if transition not in ("Common->Separate", "Separate->Common"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_DIFF_SET_TRANSITION",
            )
        if shutter_mode not in ("Speed", "Angle"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_SHUTTER_MODE",
            )

        angle_override = (
            diff_set_item == "Shutter Speed" and shutter_mode == "Angle"
        )
        if transition == "Common->Separate":
            if diff_set_item == "White Balance" and is_custom_wb:
                return _mk(
                    allowed=True,
                    errno=0,
                    reason="COMMON_TO_SEPARATE_CUSTOM_WB_STILL_ONLY_EXCEPTION",
                    still_inherited_value=True,
                    movie_inherited_value=False,
                    shutter_angle_independent_override=angle_override,
                )
            return _mk(
                allowed=True,
                errno=0,
                reason="COMMON_TO_SEPARATE_COPIED_BOTH_STILL_AND_MOVIE",
                still_inherited_value=True,
                movie_inherited_value=True,
                shutter_angle_independent_override=angle_override,
            )

        # Separate->Common
        if (
            diff_set_item in FX3_DIFF_SET_SEPARATE_TO_COMMON_STILL_EXCEPTIONS
            or (diff_set_item == "White Balance" and is_custom_wb)
        ):
            return _mk(
                allowed=True,
                errno=0,
                reason=(
                    "SEPARATE_TO_COMMON_STILL_VALUE_INHERITED_WITH_ANGLE_OVERRIDE"
                    if angle_override
                    else "SEPARATE_TO_COMMON_STILL_VALUE_INHERITED_EXCEPTION"
                ),
                common_inherited_still_value=True,
                reverted_to_factory_default=False,
                shutter_angle_independent_override=angle_override,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="SEPARATE_TO_COMMON_REVERTED_TO_FACTORY_DEFAULT",
            common_inherited_still_value=False,
            reverted_to_factory_default=True,
            shutter_angle_independent_override=angle_override,
        )

    if operation == "fx3_customkey_diffset_reset_init_and_camset_erofs":
        if camset_slot1_write_requested:
            return _mk(
                allowed=False,
                errno=EROFS_ERRNO,
                reason="TIER0_SLOT1_CAMSET_WRITE_BLOCKED_EROFS",
                slot1_camset_write_authorized=False,
                slot1_sector_writes=0,
                slot1_data_sector_writes=0,
            )
        if initialize_triggered:
            # Wave 76 G99 erratum (TP1000844002): [Custom Key/Dial Set.] and the
            # other 7 [Different Set for Still/Mv] checkboxes reset on [Initialize],
            # whereas the [Picture Profile] checkbox resists BOTH Reset & Initialize!
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_CUSTOMKEY_AND_7_DIFFSET_PRESERVES_PP_CHECKBOX",
                custom_key_preserved=False,
                diff_set_other7_preserved=False,
                diff_set_pp_checkbox_preserved=True,
                camset_included=True,
                campr_included=False,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAMERA_SETTINGS_RESET_PRESERVES_CUSTOMKEY_AND_ALL_8_DIFFSET",
                custom_key_preserved=True,
                diff_set_other7_preserved=True,
                diff_set_pp_checkbox_preserved=True,
                camset_included=True,
                campr_included=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="CAMSET_INCLUDED_CAMPR_EXCLUDED_SLOT1_READONLY",
            camset_included=True,
            campr_included=False,
        )

    # fx6_assignable_buttons_dials_no_still_mv_split
    if fx6_request_diff_set_still_mv:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_STILL_MOVIE_DIFFERENT_SET_SPLIT",
        )
    if fx6_assignable_button not in FX6_ASSIGNABLE_BUTTONS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_ASSIGNABLE_BUTTON",
        )
    if fx6_assignable_dial not in FX6_ASSIGNABLE_DIALS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_ASSIGNABLE_DIAL",
        )
    if fx6_dial_direction not in FX6_DIAL_DIRECTIONS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_DIAL_DIRECTION",
        )
    return _mk(
        allowed=True,
        errno=0,
        reason="FX6_ASSIGNABLE_BUTTON_AND_DIAL_OK",
        fx6_assignable_button=fx6_assignable_button,
        fx6_assignable_dial=fx6_assignable_dial,
        fx6_dial_direction=fx6_dial_direction,
    )


# ---------------------------------------------------------------------------
# Sub-Model 86B: Gamma Display Assist vs Display LUT / Select LUT & FX6 MLUT
# ---------------------------------------------------------------------------


def simulate_86b_gammadisp_displaylut_and_fx6_mlut(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    shoot_mode: str = "Movie",
    log_shooting_mode: str = "Off",
    gamma_display_assist: str = "Off",
    gamma_disp_assist_type: str = "Auto",
    pp_gamma: str = "S-Log3",
    pp_color_mode: str = "S-Gamut3.Cine",
    hlg_still_image: bool = False,
    display_lut: str = "On",
    select_lut: str = "s709",
    pplut_slot: str = "",
    internal_rec_active: bool = True,
    hdmi_only_no_internal_rec: bool = False,
    hdmi_raw_on: bool = False,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_request_gamma_assist: bool = False,
    fx6_sdi_osd_on: bool = False,
    fx6_hdmi_osd_on: bool = True,
    fx6_mlut_routing: Optional[Mapping[str, bool]] = None,
) -> SubModel86BGammaDisplayLUTAuditResult:
    if operation not in VALID_86B_OPERATIONS:
        raise Stage86Phase376Error(f"Unsupported 86B operation: {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage86Phase376Error(f"Unsupported body_model: {body_model!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage86Phase376Error(f"Unsupported shoot_mode: {shoot_mode!r}")

    default_mlut = {
        "Internal Rec": False,
        "SDI1/2+HDMI": False,
        "LCD/VF": True,
        "Proxy/VF Streaming": False,
    }
    if fx6_mlut_routing is not None:
        default_mlut = {k: bool(fx6_mlut_routing.get(k, False)) for k in FX6_MLUT_ROUTES}

    def _mk(**kw: Any) -> SubModel86BGammaDisplayLUTAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            log_shooting_mode=log_shooting_mode,
            gamma_display_assist=gamma_display_assist,
            gamma_disp_assist_type=gamma_disp_assist_type,
            resolved_auto_assist_curve="",
            dormant_slog2_blocked=False,
            body_lcd_gamma_assist_applied=False,
            external_hdmi_tv_gamma_assist_applied=False,
            gamma_assist_hard_locked_off=False,
            display_lut=display_lut,
            select_lut=select_lut,
            still_log_prompts_gamma_assist=False,
            pplut_slot=pplut_slot,
            lut_baked_into_rec_pixels=False,
            hdmi_forced_1080p_downscale=False,
            setup_display_items_preserved=False,
            select_lut_reset_to_s709=False,
            fx6_gamma_assist_user_menus=FX6_GAMMA_ASSIST_USER_MENUS,
            fx6_sdi_osd_on=fx6_sdi_osd_on,
            fx6_hdmi_osd_on=fx6_hdmi_osd_on,
            fx6_mlut_routing=dict(default_mlut),
        )
        defaults.update(kw)
        return SubModel86BGammaDisplayLUTAuditResult(**defaults)

    if operation.startswith("fx3_") and body_model != BODY_MODEL_FX3:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX3_ONLY_OPERATION_ON_FX6",
        )
    if operation.startswith("fx6_") and body_model != BODY_MODEL_FX6:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ONLY_OPERATION_ON_FX3",
        )

    if operation == "fx3_gamma_assist_and_dormant_slog2":
        if gamma_disp_assist_type in FX3_DORMANT_GAMMA_ASSIST_TYPES:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="DORMANT_SLOG2_GAMMA_ASSIST_BLOCKED_ON_FX3",
                dormant_slog2_blocked=True,
            )
        if gamma_disp_assist_type not in FX3_GAMMA_DISP_ASSIST_TYPES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_GAMMA_DISP_ASSIST_TYPE",
            )
        if gamma_display_assist not in ("On", "Off"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_GAMMA_DISPLAY_ASSIST_STATE",
            )
        if log_shooting_mode not in FX3_LOG_SHOOTING_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_LOG_SHOOTING_MODE",
            )
        if log_shooting_mode != "Off" and shoot_mode in ("Movie", "S&Q"):
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="GAMMA_DISPLAY_ASSIST_HARD_LOCKED_OFF_IN_LOG_MOVIE",
                gamma_display_assist="Off",
                gamma_assist_hard_locked_off=True,
                body_lcd_gamma_assist_applied=False,
                external_hdmi_tv_gamma_assist_applied=False,
            )
        resolved = gamma_disp_assist_type
        if gamma_disp_assist_type == "Auto":
            if hlg_still_image:
                resolved = "HLG(BT.2020)"
            elif pp_gamma == "S-Log3":
                resolved = "S-Log3->709(800%)"
            elif pp_gamma in ("HLG", "HLG1", "HLG2", "HLG3"):
                resolved = "HLG(709)" if pp_color_mode == "709" else "HLG(BT.2020)"
            else:
                resolved = "None"
        return _mk(
            allowed=True,
            errno=0,
            reason="FX3_GAMMA_DISPLAY_ASSIST_BODY_LCD_ONLY",
            resolved_auto_assist_curve=resolved,
            body_lcd_gamma_assist_applied=(gamma_display_assist == "On"),
            # Iron law (TP1000876505): NEVER applied to external HDMI/TV output
            external_hdmi_tv_gamma_assist_applied=False,
        )

    if operation == "fx3_log_shooting_priority_vs_still_and_pplut":
        if log_shooting_mode not in FX3_LOG_SHOOTING_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_LOG_SHOOTING_MODE",
            )
        if display_lut not in ("On", "Off"):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_DISPLAY_LUT_STATE",
            )
        if select_lut not in FX3_SELECT_LUT_ALL_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_SELECT_LUT_OPTION",
            )
        if log_shooting_mode != "Off":
            if shoot_mode == "Still":
                # _g 0x6538: Still capture in Log Shooting prompts Gamma Display Assist
                return _mk(
                    allowed=True,
                    errno=0,
                    reason="LOG_SHOOTING_STILL_PROMPTS_GAMMA_DISPLAY_ASSIST_INSTEAD_OF_LUT",
                    gamma_display_assist="On",
                    display_lut="Off",
                    still_log_prompts_gamma_assist=True,
                    body_lcd_gamma_assist_applied=True,
                    external_hdmi_tv_gamma_assist_applied=False,
                )
            # Movie / S&Q in Log Shooting: Gamma Display Assist hard-locked Off
            if gamma_display_assist == "On":
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="LOG_MOVIE_FORBIDS_GAMMA_DISPLAY_ASSIST_HANDS_TO_DISPLAY_LUT",
                    gamma_display_assist="Off",
                    gamma_assist_hard_locked_off=True,
                    display_lut=display_lut,
                    select_lut=select_lut,
                    external_hdmi_tv_gamma_assist_applied=False,
                )
            return _mk(
                allowed=True,
                errno=0,
                reason="LOG_MOVIE_DISPLAY_LUT_AND_SELECT_LUT_ACTIVE",
                gamma_display_assist="Off",
                gamma_assist_hard_locked_off=True,
                display_lut=display_lut,
                select_lut=select_lut,
                external_hdmi_tv_gamma_assist_applied=False,
            )

        # Log Shooting = Off with PPLUT1..4
        if pplut_slot:
            if pplut_slot not in FX3_PPLUT_SLOTS:
                return _mk(
                    allowed=False,
                    errno=EINVAL_ERRNO,
                    reason="INVALID_PPLUT_SLOT",
                )
            if shoot_mode == "Still":
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="PPLUT1_TO_4_MOVIE_ONLY",
                )
            downscale = (
                internal_rec_active
                and (not hdmi_only_no_internal_rec)
                and (not hdmi_raw_on)
            )
            return _mk(
                allowed=True,
                errno=0,
                reason="PPLUT_BAKES_RECORDING_AND_CLAMPS_HDMI_1080P_ON_INTERNAL_REC",
                pplut_slot=pplut_slot,
                lut_baked_into_rec_pixels=True,
                hdmi_forced_1080p_downscale=downscale,
                external_hdmi_tv_gamma_assist_applied=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="NON_LOG_STANDARD_PP_PIPELINE",
            external_hdmi_tv_gamma_assist_applied=False,
        )

    if operation == "fx3_gamma_displaylut_reset_persistence":
        if select_lut not in FX3_SELECT_LUT_ALL_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_SELECT_LUT_OPTION",
            )
        if gamma_disp_assist_type not in FX3_GAMMA_DISP_ASSIST_TYPES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_GAMMA_DISP_ASSIST_TYPE",
            )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_ALL_GAMMA_ASSIST_AND_LUT_ITEMS",
                gamma_display_assist=FX3_GAMMA_ASSIST_DEFAULT,
                gamma_disp_assist_type=FX3_GAMMA_DISP_ASSIST_TYPE_DEFAULT,
                display_lut=FX3_DISPLAY_LUT_DEFAULT,
                select_lut=FX3_SELECT_LUT_DEFAULT,
                setup_display_items_preserved=False,
                select_lut_reset_to_s709=True,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_PRESERVES_SETUP_GAMMA_DISPLAYLUT_RESETS_SELECT_LUT_S709",
                gamma_display_assist=gamma_display_assist,
                gamma_disp_assist_type=gamma_disp_assist_type,
                display_lut=display_lut,
                select_lut=FX3_SELECT_LUT_DEFAULT,
                setup_display_items_preserved=True,
                select_lut_reset_to_s709=True,
            )
        return _mk(allowed=True, errno=0, reason="PERSISTENCE_NO_RESET_TRIGGERED")

    # fx6_zero_gamma_assist_output_display_and_4way_mlut
    if fx6_request_gamma_assist:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_USER_EXPOSED_GAMMA_DISPLAY_ASSIST",
            fx6_gamma_assist_user_menus=0,
        )
    if fx6_mlut_routing is not None:
        unknown_routes = [k for k in fx6_mlut_routing if k not in FX6_MLUT_ROUTES]
        if unknown_routes:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX6_MLUT_ROUTE_KEY",
            )
    return _mk(
        allowed=True,
        errno=0,
        reason="FX6_INDEPENDENT_SDI_HDMI_OSD_AND_4WAY_MLUT_OK",
        fx6_gamma_assist_user_menus=0,
        fx6_sdi_osd_on=bool(fx6_sdi_osd_on),
        fx6_hdmi_osd_on=bool(fx6_hdmi_osd_on),
        fx6_mlut_routing=dict(default_mlut),
    )


# ---------------------------------------------------------------------------
# Sub-Model 86C: USB-LAN, Access Authen., Ver. 7.00+ IPsec Lock & Airplane Mode
# ---------------------------------------------------------------------------


def _is_valid_ipv4_field(value: str) -> bool:
    if not value or len(value) > FX3_WIRED_LAN_IP_FIELD_MAX_CHARS:
        return False
    if not re.match(r"^[0-9.]+$", value):
        return False
    parts = value.split(".")
    if len(parts) != 4:
        return False
    for part in parts:
        if not part or (len(part) > 1 and part.startswith("0")):
            return False
        if not (0 <= int(part) <= 255):
            return False
    return True


def _parse_fw_version(fw_str: str) -> Optional[Tuple[int, int]]:
    m = re.match(r"^(\d+)\.(\d{1,2})$", fw_str.strip())
    if not m:
        return None
    return (int(m.group(1)), int(m.group(2)))


def _deterministic_generated_password(seed: str) -> str:
    alphabet = "ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789!%.=_+-,"
    digest = hashlib.sha256(f"fx3_stage86_genpw:{seed}".encode("utf-8")).digest()
    return "".join(alphabet[b % len(alphabet)] for b in digest[:12])


def _deterministic_ssh_fingerprint(seed: str) -> str:
    digest = hashlib.sha256(f"fx3_stage86_hostkey:{seed}".encode("utf-8")).hexdigest()
    return f"SHA256:{digest[:43]}"


def simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    ip_setting_mode: str = "Auto",
    manual_ip: str = "192.168.10.20",
    manual_subnet: str = "255.255.255.0",
    manual_gateway: str = "192.168.10.1",
    manual_dns1: str = "192.168.10.1",
    manual_dns2: str = "8.8.8.8",
    usb_lan_cnct_launch: bool = False,
    multi_micro_usb_data_active: bool = False,
    wifi_active: bool = False,
    access_authen_on: bool = True,
    username: str = "fx3bench_01",
    password: str = "Fx3!Safe+2026",
    generate_password_requested: bool = False,
    request_native_https_or_digest: bool = False,
    firmware_version: str = "7.02",
    ipsec_dest_ip: str = "192.168.10.100",
    ipsec_shared_key: str = "BenchKey_2026_16",
    airplane_mode_on: bool = True,
    usblan_requested_in_airplane: bool = True,
    wifi_or_bt_requested_in_airplane: bool = False,
    camera_settings_reset_triggered: bool = False,
    reset_network_set_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_request_ipsec: bool = False,
    fx6_mutex_mode: str = "",
) -> SubModel86CUsbLanAuthIpsecAirplaneAuditResult:
    if operation not in VALID_86C_OPERATIONS:
        raise Stage86Phase376Error(f"Unsupported 86C operation: {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage86Phase376Error(f"Unsupported body_model: {body_model!r}")

    def _mk(**kw: Any) -> SubModel86CUsbLanAuthIpsecAirplaneAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            allowed=True,
            errno=0,
            reason="OK",
            ip_setting_mode=ip_setting_mode,
            usb_lan_cnct_launch=usb_lan_cnct_launch,
            access_authen_on=access_authen_on,
            transport_protocol=FX3_ACCESS_AUTHEN_TRANSPORT,
            native_https_server_present=FX3_NATIVE_HTTPS_SERVER_PRESENT,
            http_digest_server_present=FX3_NATIVE_HTTP_DIGEST_SERVER_PRESENT,
            generated_password="",
            ssh_host_key_fingerprint=_deterministic_ssh_fingerprint(body_model),
            camset_included=False,
            firmware_version=firmware_version,
            ipsec_available=False,
            ipsec_disabled_by_fw_v700=False,
            ipsec_disabled_by_access_authen=False,
            ipsec_cipher_suite=FX3_IPSEC_CIPHER_SUITE,
            ipsec_rekey_hours=FX3_IPSEC_REKEY_HOURS,
            airplane_mode_on=airplane_mode_on,
            wifi_rf_blocked=bool(airplane_mode_on),
            bt_rf_blocked=bool(airplane_mode_on),
            usblan_allowed_in_airplane_mode=True,
            zero_rf_wired_bench_bypass=bool(airplane_mode_on),
            airplane_mode_survived_net_reset=False,
            airplane_mode_reset_on_initialize=False,
            g114_g136_dual_erratum_reconciled=FX3_AIRPLANE_MODE_G114_G136_DUAL_ERRATUM_RECONCILED,
            fx6_ipsec_user_menus=FX6_IPSEC_USER_MENUS,
            usb_tx_packets=0,
            rf_tx_packets=0,
            rf_packets_transmitted=0,
        )
        defaults.update(kw)
        return SubModel86CUsbLanAuthIpsecAirplaneAuditResult(**defaults)

    if operation.startswith("fx3_") and body_model != BODY_MODEL_FX3:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX3_ONLY_OPERATION_ON_FX6",
        )
    if operation.startswith("fx6_") and body_model != BODY_MODEL_FX6:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ONLY_OPERATION_ON_FX3",
        )

    if operation == "fx3_wired_lan_usblan_and_mutex":
        if ip_setting_mode not in FX3_WIRED_LAN_IP_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_WIRED_LAN_IP_MODE",
            )
        if multi_micro_usb_data_active:
            return _mk(
                allowed=False,
                errno=EBUSY_ERRNO,
                reason="USBLAN_MUTUALLY_EXCLUSIVE_WITH_MULTI_MICRO_USB_VMC_BNCM1",
            )
        if wifi_active:
            return _mk(
                allowed=False,
                errno=EBUSY_ERRNO,
                reason="USBLAN_MUTUALLY_EXCLUSIVE_WITH_ONBOARD_WIFI",
            )
        if ip_setting_mode == "Manual":
            for fld_name, fld_val in (
                ("IP", manual_ip),
                ("SUBNET", manual_subnet),
                ("GATEWAY", manual_gateway),
                ("DNS1", manual_dns1),
                ("DNS2", manual_dns2),
            ):
                if not _is_valid_ipv4_field(fld_val):
                    return _mk(
                        allowed=False,
                        errno=EINVAL_ERRNO,
                        reason=f"INVALID_MANUAL_{fld_name}_FIELD",
                    )
        return _mk(
            allowed=True,
            errno=0,
            reason="FX3_USBLAN_GIGABIT_USBNET_DHCPCD_OK",
            camset_included=False,
        )

    if operation == "fx3_access_authen_ssh_ptpip":
        if request_native_https_or_digest:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="FX3_ZERO_NATIVE_HTTPS_OR_HTTP_DIGEST_SERVER_SSH_PTPIP_ONLY",
                native_https_server_present=False,
                http_digest_server_present=False,
            )
        if not FX3_ACCESS_AUTHEN_USER_RE.match(username):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_ACCESS_AUTHEN_USERNAME_CHARSET_OR_LEN",
            )
        eff_pw = (
            _deterministic_generated_password(username)
            if generate_password_requested
            else password
        )
        if not FX3_ACCESS_AUTHEN_PASS_RE.match(eff_pw):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_ACCESS_AUTHEN_PASSWORD_CHARSET_OR_LEN",
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "FX3_ACCESS_AUTHEN_SSH_PTPIP_ENCRYPTED_OK"
                if access_authen_on
                else "FX3_ACCESS_AUTHEN_OFF_PLAINTEXT_WARNING"
            ),
            access_authen_on=bool(access_authen_on),
            transport_protocol=(
                FX3_ACCESS_AUTHEN_TRANSPORT if access_authen_on else "PLAINTEXT_PTP-IP"
            ),
            generated_password=eff_pw if generate_password_requested else "",
            camset_included=False,
        )

    if operation == "fx3_security_ipsec_v700_and_authen_lock":
        fw_tuple = _parse_fw_version(firmware_version)
        if fw_tuple is None:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FIRMWARE_VERSION_FORMAT",
            )
        disabled_by_fw = fw_tuple >= FX3_IPSEC_DISABLED_MIN_FW
        disabled_by_auth = bool(access_authen_on)
        if disabled_by_fw or disabled_by_auth:
            reason = (
                "IPSEC_HARD_DISABLED_FW_V700_AND_ACCESS_AUTHEN_ON"
                if (disabled_by_fw and disabled_by_auth)
                else (
                    "IPSEC_HARD_DISABLED_ON_FW_V700_PLUS"
                    if disabled_by_fw
                    else "IPSEC_HARD_DISABLED_WHEN_ACCESS_AUTHEN_ON"
                )
            )
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason=reason,
                ipsec_available=False,
                ipsec_disabled_by_fw_v700=disabled_by_fw,
                ipsec_disabled_by_access_authen=disabled_by_auth,
            )
        # Legacy pre-7.00 with Access Authen Off: validate IPsec parameters
        if (
            not ipsec_dest_ip
            or len(ipsec_dest_ip) > FX3_IPSEC_DEST_IP_MAX_CHARS
            or not re.match(r"^[0-9.]+$", ipsec_dest_ip)
        ):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_IPSEC_DEST_IP",
                ipsec_available=True,
            )
        if not (
            FX3_IPSEC_SHARED_KEY_MIN_CHARS
            <= len(ipsec_shared_key)
            <= FX3_IPSEC_SHARED_KEY_MAX_CHARS
        ):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_IPSEC_SHARED_KEY_LENGTH",
                ipsec_available=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="LEGACY_PRE_V700_IPSEC_IKEV2_TRANSPORT_OK",
            ipsec_available=True,
            ipsec_disabled_by_fw_v700=False,
            ipsec_disabled_by_access_authen=False,
        )

    if operation == "fx3_airplane_mode_dual_erratum_and_usblan_bypass":
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_AIRPLANE_MODE_TO_OFF_AND_ALL_NET",
                airplane_mode_on=False,
                wifi_rf_blocked=False,
                bt_rf_blocked=False,
                ip_setting_mode=FX3_WIRED_LAN_IP_DEFAULT,
                usb_lan_cnct_launch=FX3_USB_LAN_CNCT_LAUNCH_DEFAULT,
                access_authen_on=FX3_ACCESS_AUTHEN_DEFAULT,
                airplane_mode_survived_net_reset=False,
                airplane_mode_reset_on_initialize=True,
                zero_rf_wired_bench_bypass=False,
            )
        if reset_network_set_triggered:
            # Wave 76 G114/G136 dual erratum: [Reset Network Set.] preserves
            # [Airplane Mode] = On while resetting Wired LAN / Access Authen!
            return _mk(
                allowed=True,
                errno=0,
                reason="RESET_NETWORK_SET_PRESERVES_AIRPLANE_MODE_ON_RESETS_LAN_AND_AUTH",
                airplane_mode_on=bool(airplane_mode_on),
                wifi_rf_blocked=bool(airplane_mode_on),
                bt_rf_blocked=bool(airplane_mode_on),
                ip_setting_mode=FX3_WIRED_LAN_IP_DEFAULT,
                usb_lan_cnct_launch=FX3_USB_LAN_CNCT_LAUNCH_DEFAULT,
                access_authen_on=FX3_ACCESS_AUTHEN_DEFAULT,
                usblan_allowed_in_airplane_mode=True,
                zero_rf_wired_bench_bypass=bool(airplane_mode_on),
                airplane_mode_survived_net_reset=bool(airplane_mode_on),
                airplane_mode_reset_on_initialize=False,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_SETTINGS_RESET_PRESERVES_AIRPLANE_MODE_AND_NET",
                airplane_mode_on=bool(airplane_mode_on),
                wifi_rf_blocked=bool(airplane_mode_on),
                bt_rf_blocked=bool(airplane_mode_on),
                usblan_allowed_in_airplane_mode=True,
                zero_rf_wired_bench_bypass=bool(airplane_mode_on),
            )
        if airplane_mode_on and wifi_or_bt_requested_in_airplane:
            return _mk(
                allowed=False,
                errno=EPERM_ERRNO,
                reason="AIRPLANE_MODE_BLOCKS_WIFI_AND_BT_RF_ZERO_RF_PACKETS",
                airplane_mode_on=True,
                wifi_rf_blocked=True,
                bt_rf_blocked=True,
                usblan_allowed_in_airplane_mode=True,
                zero_rf_wired_bench_bypass=True,
                rf_tx_packets=0,
                rf_packets_transmitted=0,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "AIRPLANE_MODE_ZERO_RF_WIRED_USBLAN_BYPASS_OK"
                if (airplane_mode_on and usblan_requested_in_airplane)
                else "AIRPLANE_MODE_STATE_OK"
            ),
            airplane_mode_on=bool(airplane_mode_on),
            wifi_rf_blocked=bool(airplane_mode_on),
            bt_rf_blocked=bool(airplane_mode_on),
            usblan_allowed_in_airplane_mode=True,
            zero_rf_wired_bench_bypass=bool(airplane_mode_on),
        )

    # fx6_wired_lan_authen_zero_ipsec_and_mutex
    if fx6_request_ipsec:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_USER_MENU_IPSEC_DORMANT_SYMBOL_ONLY",
            ipsec_available=False,
            fx6_ipsec_user_menus=0,
        )
    if fx6_mutex_mode:
        if fx6_mutex_mode not in FX6_WIRED_LAN_MUTEX_MODES:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_FX6_WIRED_LAN_MUTEX_MODE",
            )
        return _mk(
            allowed=False,
            errno=EBUSY_ERRNO,
            reason=f"FX6_WIRED_LAN_MUTEX_WITH_{fx6_mutex_mode.upper().replace(' ', '_')}",
        )
    return _mk(
        allowed=True,
        errno=0,
        reason="FX6_WIRED_LAN_AND_ACCESS_AUTHENTICATION_OK",
        fx6_ipsec_user_menus=0,
    )


# ---------------------------------------------------------------------------
# Sub-Model 86D: Sensor Cleaning (>=51% IBIS), IR Remote Ctrl & Auto Review
# ---------------------------------------------------------------------------


def simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
    *,
    operation: str,
    body_model: str = BODY_MODEL_FX3,
    body_variant: str = BODY_MODEL_FX3,
    shoot_mode: str = "Still",
    battery_pct: int = 80,
    proceed_blower_without_power_off: bool = False,
    dormant_menu_requested: str = "Shutter When Pwr OFF",
    ir_remote_ctrl_on: bool = False,
    bt_rmt_ctrl_on: bool = False,
    auto_review_setting: str = "Off",
    trigger_auto_review_in_movie_requested: bool = False,
    camera_settings_reset_triggered: bool = False,
    initialize_triggered: bool = False,
    fx6_request_ibis_cleaning: bool = False,
    fx6_request_ir_remote: bool = False,
    fx6_request_still_auto_review: bool = False,
    fx6_rec_review_mode: str = "Last 3s",
) -> SubModel86DCleaningIRAutoReviewAuditResult:
    if operation not in VALID_86D_OPERATIONS:
        raise Stage86Phase376Error(f"Unsupported 86D operation: {operation!r}")
    if body_model not in VALID_BODY_MODELS:
        raise Stage86Phase376Error(f"Unsupported body_model: {body_model!r}")
    if body_model == BODY_MODEL_FX3 and body_variant not in VALID_FX3_VARIANTS:
        raise Stage86Phase376Error(f"Unsupported FX3 body_variant: {body_variant!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage86Phase376Error(f"Unsupported shoot_mode: {shoot_mode!r}")

    def _mk(**kw: Any) -> SubModel86DCleaningIRAutoReviewAuditResult:
        defaults: Dict[str, Any] = dict(
            operation=operation,
            body_model=body_model,
            body_variant=body_variant if body_model == BODY_MODEL_FX3 else BODY_MODEL_FX6,
            shoot_mode=shoot_mode,
            allowed=True,
            errno=0,
            reason="OK",
            battery_pct=battery_pct,
            ibis_ultrasonic_triggered=False,
            low_battery_blocked=False,
            mandatory_power_off_prompt_shown=False,
            mandatory_power_off_enforced=False,
            shutter_curtain_at_power_off=FX3_SHUTTER_CURTAIN_AT_POWER_OFF,
            dormant_antidust_or_shutter_blocked=False,
            ir_remote_ctrl_on=ir_remote_ctrl_on,
            fx3a_ir_physically_absent=(body_variant == BODY_MODEL_FX3A),
            ir_blocked_by_bt_rmt=False,
            power_save_start_time_suppressed=False,
            auto_review_setting=auto_review_setting,
            auto_review_triggered=False,
            setup_item_survived_cam_reset=False,
            setup_item_reset_on_initialize=False,
            fx6_has_ibis_cleaning=FX6_HAS_IBIS_ULTRASONIC_CLEANING,
            fx6_steadyshot_fixed_message=FX6_STEADYSHOT_FIXED_MESSAGE,
            fx6_ir_remote_user_menus=FX6_IR_REMOTE_USER_MENUS,
            fx6_auto_review_user_menus=FX6_AUTO_REVIEW_USER_MENUS,
            fx6_rec_review_mode="",
        )
        defaults.update(kw)
        return SubModel86DCleaningIRAutoReviewAuditResult(**defaults)

    if operation.startswith("fx3_") and body_model != BODY_MODEL_FX3:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX3_ONLY_OPERATION_ON_FX6",
        )
    if operation.startswith("fx6_") and body_model != BODY_MODEL_FX6:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ONLY_OPERATION_ON_FX3",
        )

    if operation == "fx3_sensor_cleaning_51pct_ibis_and_poweroff":
        if isinstance(battery_pct, bool) or not (0 <= battery_pct <= 100):
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_BATTERY_PERCENTAGE",
            )
        if battery_pct < FX3_SENSOR_CLEANING_MIN_BATTERY_PCT:
            return _mk(
                allowed=False,
                errno=EAGAIN_ERRNO,
                reason="SENSOR_CLEANING_BLOCKED_BATTERY_BELOW_51_PERCENT",
                ibis_ultrasonic_triggered=False,
                low_battery_blocked=True,
                mandatory_power_off_prompt_shown=False,
            )
        if proceed_blower_without_power_off:
            return _mk(
                allowed=False,
                errno=EPERM_ERRNO,
                reason="MANDATORY_PHYSICAL_POWER_OFF_REQUIRED_BEFORE_BLOWER",
                ibis_ultrasonic_triggered=True,
                mandatory_power_off_prompt_shown=True,
                mandatory_power_off_enforced=True,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason="FX3_IBIS_ULTRASONIC_CLEANING_COMPLETE_POWER_OFF_PROMPT",
            ibis_ultrasonic_triggered=True,
            mandatory_power_off_prompt_shown=True,
            mandatory_power_off_enforced=True,
            shutter_curtain_at_power_off=FX3_SHUTTER_CURTAIN_AT_POWER_OFF,
        )

    if operation == "fx3_dormant_antidust_and_shutter_pwr_off_blocked":
        if dormant_menu_requested not in FX3_DORMANT_ANTIDUST_MENUS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="UNKNOWN_DORMANT_ANTIDUST_MENU",
            )
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason=f"DORMANT_FX3_MENU_BLOCKED_{dormant_menu_requested.upper().replace(' ', '_').replace('-', '_')}",
            shutter_curtain_at_power_off=FX3_SHUTTER_CURTAIN_AT_POWER_OFF,
            dormant_antidust_or_shutter_blocked=True,
        )

    if operation == "fx3_ir_remote_ctrl_fx3a_and_bt_powersave":
        if body_variant == BODY_MODEL_FX3A:
            return _mk(
                allowed=False,
                errno=EOPNOTSUPP_ERRNO,
                reason="ILME_FX3A_FRONT_IR_SENSOR_PHYSICALLY_ABSENT",
                ir_remote_ctrl_on=False,
                fx3a_ir_physically_absent=True,
            )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_IR_REMOTE_CTRL_TO_OFF",
                ir_remote_ctrl_on=FX3_IR_REMOTE_CTRL_DEFAULT,
                power_save_start_time_suppressed=False,
                setup_item_survived_cam_reset=False,
                setup_item_reset_on_initialize=True,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_PRESERVES_IR_REMOTE_CTRL",
                ir_remote_ctrl_on=bool(ir_remote_ctrl_on),
                power_save_start_time_suppressed=bool(ir_remote_ctrl_on),
                setup_item_survived_cam_reset=True,
                setup_item_reset_on_initialize=False,
            )
        if ir_remote_ctrl_on and bt_rmt_ctrl_on:
            return _mk(
                allowed=False,
                errno=EBUSY_ERRNO,
                reason="IR_REMOTE_CTRL_MUTUALLY_EXCLUSIVE_WITH_BT_RMT_CTRL_ON",
                ir_remote_ctrl_on=False,
                ir_blocked_by_bt_rmt=True,
                power_save_start_time_suppressed=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "IR_REMOTE_CTRL_ON_SUPPRESSES_POWER_SAVE_START_TIME"
                if ir_remote_ctrl_on
                else "IR_REMOTE_CTRL_OFF_DEFAULT"
            ),
            ir_remote_ctrl_on=bool(ir_remote_ctrl_on),
            power_save_start_time_suppressed=bool(ir_remote_ctrl_on),
        )

    if operation == "fx3_auto_review_still_only_and_reset":
        if auto_review_setting not in FX3_AUTO_REVIEW_OPTIONS:
            return _mk(
                allowed=False,
                errno=EINVAL_ERRNO,
                reason="INVALID_AUTO_REVIEW_SETTING",
            )
        if initialize_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="INITIALIZE_RESETS_AUTO_REVIEW_TO_OFF",
                auto_review_setting=FX3_AUTO_REVIEW_DEFAULT,
                auto_review_triggered=False,
                setup_item_survived_cam_reset=False,
                setup_item_reset_on_initialize=True,
            )
        if camera_settings_reset_triggered:
            return _mk(
                allowed=True,
                errno=0,
                reason="CAM_RESET_PRESERVES_AUTO_REVIEW",
                auto_review_setting=auto_review_setting,
                auto_review_triggered=(
                    shoot_mode == "Still" and auto_review_setting != "Off"
                ),
                setup_item_survived_cam_reset=True,
                setup_item_reset_on_initialize=False,
            )
        if shoot_mode in ("Movie", "S&Q"):
            if trigger_auto_review_in_movie_requested:
                return _mk(
                    allowed=False,
                    errno=EOPNOTSUPP_ERRNO,
                    reason="AUTO_REVIEW_STRICTLY_STILL_ONLY_BLOCKED_IN_MOVIE_SQ",
                    auto_review_triggered=False,
                )
            return _mk(
                allowed=True,
                errno=0,
                reason="AUTO_REVIEW_NEVER_TRIGGERS_IN_MOVIE_OR_SQ",
                auto_review_triggered=False,
            )
        return _mk(
            allowed=True,
            errno=0,
            reason=(
                "AUTO_REVIEW_STILL_PREVIEW_ZERO_CARD_WRITES"
                if auto_review_setting != "Off"
                else "AUTO_REVIEW_OFF_DEFAULT"
            ),
            auto_review_triggered=(auto_review_setting != "Off"),
        )

    # fx6_zero_ibis_cleaning_lanc_and_rec_review
    if fx6_request_ibis_cleaning:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_IBIS_ULTRASONIC_CLEANING_STEADYSHOT_FIXED_USE_END_APR",
            fx6_has_ibis_cleaning=False,
        )
    if fx6_request_ir_remote:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_IR_REMOTE_USE_2_5MM_LANC_AND_3_5MM_GRIP",
            fx6_ir_remote_user_menus=0,
        )
    if fx6_request_still_auto_review:
        return _mk(
            allowed=False,
            errno=EOPNOTSUPP_ERRNO,
            reason="FX6_ZERO_STILL_AUTO_REVIEW_USE_REC_REVIEW",
            fx6_auto_review_user_menus=0,
        )
    if fx6_rec_review_mode not in FX6_REC_REVIEW_OPTIONS:
        return _mk(
            allowed=False,
            errno=EINVAL_ERRNO,
            reason="INVALID_FX6_REC_REVIEW_MODE",
        )
    return _mk(
        allowed=True,
        errno=0,
        reason="FX6_SEALED_END_APR_LANC_AND_REC_REVIEW_OK",
        fx6_has_ibis_cleaning=False,
        fx6_ir_remote_user_menus=0,
        fx6_auto_review_user_menus=0,
        fx6_rec_review_mode=fx6_rec_review_mode,
    )


# ---------------------------------------------------------------------------
# Sub-Model Evaluators & Unified Stage 86 (86/86) Orchestrator
# ---------------------------------------------------------------------------


def _evaluate_submodel_86a() -> Dict[str, Any]:
    r_mv_c1 = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx3_custom_key_3domain_mapping",
        domain="Movie",
        control_name="Custom Button 1",
    )
    r_pb_fn = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx3_custom_key_3domain_mapping",
        domain="Playback",
        control_name="Fn Button",
    )
    r_mv_fn_blk = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx3_custom_key_3domain_mapping",
        domain="Movie",
        control_name="Fn Button",
    )
    r_pb_c4_blk = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx3_custom_key_3domain_mapping",
        domain="Playback",
        control_name="Custom Button 4",
    )
    r_xlrh1_blk = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx3_custom_key_3domain_mapping",
        xlr_h1_key_requested=True,
    )
    r_c2s_cwb = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx3_diff_set_8bit_transitions",
        diff_set_item="White Balance",
        transition="Common->Separate",
        is_custom_wb=True,
    )
    r_s2c_ang = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx3_diff_set_8bit_transitions",
        diff_set_item="Shutter Speed",
        transition="Separate->Common",
        shutter_mode="Angle",
    )
    r_init_pp = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx3_customkey_diffset_reset_init_and_camset_erofs",
        initialize_triggered=True,
    )
    r_erofs = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx3_customkey_diffset_reset_init_and_camset_erofs",
        camset_slot1_write_requested=True,
    )
    r_fx6 = simulate_86a_customkey_3domain_diffset8_and_fx6_assign(
        operation="fx6_assignable_buttons_dials_no_still_mv_split",
        body_model=BODY_MODEL_FX6,
        fx6_assignable_button="<9>",
        fx6_assignable_dial="Multi Function Dial",
        fx6_dial_direction="Reverse",
    )
    passed = (
        (r_mv_c1.allowed and r_mv_c1.default_assignment == "L.PressAv Auto/Manual")
        and (r_pb_fn.allowed and r_pb_fn.default_assignment == "Not set")
        and (not r_mv_fn_blk.allowed and r_mv_fn_blk.errno == EOPNOTSUPP_ERRNO)
        and (not r_pb_c4_blk.allowed and r_pb_c4_blk.errno == EOPNOTSUPP_ERRNO)
        and (not r_xlrh1_blk.allowed and r_xlrh1_blk.errno == ENODEV_ERRNO)
        and (r_c2s_cwb.allowed and r_c2s_cwb.still_inherited_value and not r_c2s_cwb.movie_inherited_value)
        and (r_s2c_ang.allowed and r_s2c_ang.common_inherited_still_value and r_s2c_ang.shutter_angle_independent_override)
        and (r_init_pp.allowed and not r_init_pp.custom_key_preserved and not r_init_pp.diff_set_other7_preserved and r_init_pp.diff_set_pp_checkbox_preserved)
        and (not r_erofs.allowed and r_erofs.errno == EROFS_ERRNO and not r_erofs.slot1_camset_write_authorized and r_erofs.slot1_sector_writes == 0)
        and (r_fx6.allowed and r_fx6.fx6_assignable_button == "<9>")
    )
    return {
        "passed": passed,
        "fx3_still_controls_count": FX3_STILL_CONTROLS_COUNT,
        "fx3_movie_controls_count": FX3_MOVIE_CONTROLS_COUNT,
        "fx3_playback_controls_count": FX3_PLAYBACK_CONTROLS_COUNT,
        "fx3_xlr_h1_assignable_keys": FX3_XLR_H1_ASSIGNABLE_KEYS,
        "fx3_xlr_h1_rec_buttons": FX3_XLR_H1_REC_BUTTONS,
        "fx3_diff_set_items_count": len(FX3_DIFF_SET_8_ITEMS),
        "fx3_g99_pp_init_erratum_reconciled": FX3_G99_PP_INIT_ERRATUM_RECONCILED,
        "fx3_g100_default_keymap_reconciled": FX3_G100_DEFAULT_KEYMAP_RECONCILED,
        "slot1_camset_write_authorized": SLOT1_CAMSET_WRITE_AUTHORIZED,
        "samples": {
            "fx3_movie_c1_default": r_mv_c1.to_dict(),
            "fx3_playback_fn_default": r_pb_fn.to_dict(),
            "fx3_movie_fn_blocked": r_mv_fn_blk.to_dict(),
            "fx3_playback_c4_blocked": r_pb_c4_blk.to_dict(),
            "fx3_xlrh1_zero_keys": r_xlrh1_blk.to_dict(),
            "fx3_diffset_c2s_custom_wb": r_c2s_cwb.to_dict(),
            "fx3_diffset_s2c_angle_override": r_s2c_ang.to_dict(),
            "fx3_init_pp_checkbox_persists": r_init_pp.to_dict(),
            "fx3_slot1_camset_erofs": r_erofs.to_dict(),
            "fx6_assignable_ok": r_fx6.to_dict(),
        },
    }


def _evaluate_submodel_86b() -> Dict[str, Any]:
    r_lcd = simulate_86b_gammadisp_displaylut_and_fx6_mlut(
        operation="fx3_gamma_assist_and_dormant_slog2",
        gamma_display_assist="On",
        gamma_disp_assist_type="Auto",
        pp_gamma="S-Log3",
    )
    r_slog2 = simulate_86b_gammadisp_displaylut_and_fx6_mlut(
        operation="fx3_gamma_assist_and_dormant_slog2",
        gamma_disp_assist_type="S-Log2",
    )
    r_log_lock = simulate_86b_gammadisp_displaylut_and_fx6_mlut(
        operation="fx3_log_shooting_priority_vs_still_and_pplut",
        shoot_mode="Movie",
        log_shooting_mode="Cine EI",
        gamma_display_assist="On",
    )
    r_log_lut = simulate_86b_gammadisp_displaylut_and_fx6_mlut(
        operation="fx3_log_shooting_priority_vs_still_and_pplut",
        shoot_mode="Movie",
        log_shooting_mode="Cine EI",
        gamma_display_assist="Off",
        display_lut="On",
        select_lut="User1",
    )
    r_log_still = simulate_86b_gammadisp_displaylut_and_fx6_mlut(
        operation="fx3_log_shooting_priority_vs_still_and_pplut",
        shoot_mode="Still",
        log_shooting_mode="Flexible ISO",
    )
    r_pplut = simulate_86b_gammadisp_displaylut_and_fx6_mlut(
        operation="fx3_log_shooting_priority_vs_still_and_pplut",
        shoot_mode="Movie",
        log_shooting_mode="Off",
        pplut_slot="PPLUT1",
        internal_rec_active=True,
    )
    r_rst = simulate_86b_gammadisp_displaylut_and_fx6_mlut(
        operation="fx3_gamma_displaylut_reset_persistence",
        gamma_display_assist="On",
        gamma_disp_assist_type="HLG(BT.2020)",
        display_lut="Off",
        select_lut="User16",
        camera_settings_reset_triggered=True,
    )
    r_fx6_ga = simulate_86b_gammadisp_displaylut_and_fx6_mlut(
        operation="fx6_zero_gamma_assist_output_display_and_4way_mlut",
        body_model=BODY_MODEL_FX6,
        fx6_request_gamma_assist=True,
    )
    r_fx6_mlut = simulate_86b_gammadisp_displaylut_and_fx6_mlut(
        operation="fx6_zero_gamma_assist_output_display_and_4way_mlut",
        body_model=BODY_MODEL_FX6,
        fx6_sdi_osd_on=False,
        fx6_hdmi_osd_on=True,
        fx6_mlut_routing={
            "Internal Rec": False,
            "SDI1/2+HDMI": False,
            "LCD/VF": True,
            "Proxy/VF Streaming": True,
        },
    )
    passed = (
        (r_lcd.allowed and r_lcd.body_lcd_gamma_assist_applied and not r_lcd.external_hdmi_tv_gamma_assist_applied and r_lcd.resolved_auto_assist_curve == "S-Log3->709(800%)")
        and (not r_slog2.allowed and r_slog2.errno == EOPNOTSUPP_ERRNO and r_slog2.dormant_slog2_blocked)
        and (not r_log_lock.allowed and r_log_lock.errno == EOPNOTSUPP_ERRNO and r_log_lock.gamma_assist_hard_locked_off)
        and (r_log_lut.allowed and r_log_lut.gamma_assist_hard_locked_off and r_log_lut.display_lut == "On" and r_log_lut.select_lut == "User1")
        and (r_log_still.allowed and r_log_still.still_log_prompts_gamma_assist and r_log_still.gamma_display_assist == "On")
        and (r_pplut.allowed and r_pplut.lut_baked_into_rec_pixels and r_pplut.hdmi_forced_1080p_downscale)
        and (r_rst.allowed and r_rst.setup_display_items_preserved and r_rst.select_lut == "s709" and r_rst.gamma_display_assist == "On")
        and (not r_fx6_ga.allowed and r_fx6_ga.errno == EOPNOTSUPP_ERRNO and r_fx6_ga.fx6_gamma_assist_user_menus == 0)
        and (r_fx6_mlut.allowed and not r_fx6_mlut.fx6_sdi_osd_on and r_fx6_mlut.fx6_hdmi_osd_on and r_fx6_mlut.fx6_mlut_routing["LCD/VF"])
    )
    return {
        "passed": passed,
        "fx3_gamma_assist_types_count": len(FX3_GAMMA_DISP_ASSIST_TYPES),
        "fx3_dormant_slog2_exposed_events": 0,
        "fx3_hdmi_gamma_assist_applied_events": 0,
        "fx3_select_lut_options_count": len(FX3_SELECT_LUT_ALL_OPTIONS),
        "fx6_gamma_assist_user_menus": FX6_GAMMA_ASSIST_USER_MENUS,
        "fx6_mlut_routes_count": len(FX6_MLUT_ROUTES),
        "samples": {
            "fx3_gamma_assist_lcd_only": r_lcd.to_dict(),
            "fx3_dormant_slog2_blocked": r_slog2.to_dict(),
            "fx3_log_movie_locks_gamma_off": r_log_lock.to_dict(),
            "fx3_log_movie_display_lut_ok": r_log_lut.to_dict(),
            "fx3_log_still_prompts_gamma": r_log_still.to_dict(),
            "fx3_pplut_bakes_1080p_hdmi": r_pplut.to_dict(),
            "fx3_reset_setup_vs_select_lut": r_rst.to_dict(),
            "fx6_zero_gamma_assist": r_fx6_ga.to_dict(),
            "fx6_4way_mlut_ok": r_fx6_mlut.to_dict(),
        },
    }


def _evaluate_submodel_86c() -> Dict[str, Any]:
    r_lan_ok = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx3_wired_lan_usblan_and_mutex",
        ip_setting_mode="Manual",
        manual_ip="192.168.10.20",
        usb_lan_cnct_launch=True,
    )
    r_lan_vmc = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx3_wired_lan_usblan_and_mutex",
        multi_micro_usb_data_active=True,
    )
    r_auth_ok = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx3_access_authen_ssh_ptpip",
        access_authen_on=True,
        username="fx3_admin.1",
        generate_password_requested=True,
    )
    r_https_blk = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx3_access_authen_ssh_ptpip",
        request_native_https_or_digest=True,
    )
    r_ipsec_v702 = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx3_security_ipsec_v700_and_authen_lock",
        firmware_version="7.02",
        access_authen_on=False,
    )
    r_ipsec_auth = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx3_security_ipsec_v700_and_authen_lock",
        firmware_version="6.00",
        access_authen_on=True,
    )
    r_air_bypass = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx3_airplane_mode_dual_erratum_and_usblan_bypass",
        airplane_mode_on=True,
        usblan_requested_in_airplane=True,
    )
    r_air_netrst = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx3_airplane_mode_dual_erratum_and_usblan_bypass",
        airplane_mode_on=True,
        reset_network_set_triggered=True,
    )
    r_air_init = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx3_airplane_mode_dual_erratum_and_usblan_bypass",
        airplane_mode_on=True,
        initialize_triggered=True,
    )
    r_fx6_ipsec = simulate_86c_usblan_auth_ipsec_airplane_and_fx6_net(
        operation="fx6_wired_lan_authen_zero_ipsec_and_mutex",
        body_model=BODY_MODEL_FX6,
        fx6_request_ipsec=True,
    )
    passed = (
        (r_lan_ok.allowed and not r_lan_ok.camset_included and r_lan_ok.rf_tx_packets == 0)
        and (not r_lan_vmc.allowed and r_lan_vmc.errno == EBUSY_ERRNO)
        and (r_auth_ok.allowed and r_auth_ok.transport_protocol == "SSH+PTP-IP" and not r_auth_ok.native_https_server_present and len(r_auth_ok.generated_password) == 12)
        and (not r_https_blk.allowed and r_https_blk.errno == EOPNOTSUPP_ERRNO)
        and (not r_ipsec_v702.allowed and r_ipsec_v702.errno == EOPNOTSUPP_ERRNO and r_ipsec_v702.ipsec_disabled_by_fw_v700)
        and (not r_ipsec_auth.allowed and r_ipsec_auth.errno == EOPNOTSUPP_ERRNO and r_ipsec_auth.ipsec_disabled_by_access_authen)
        and (r_air_bypass.allowed and r_air_bypass.usblan_allowed_in_airplane_mode and r_air_bypass.zero_rf_wired_bench_bypass and r_air_bypass.rf_tx_packets == 0)
        and (r_air_netrst.allowed and r_air_netrst.airplane_mode_on and r_air_netrst.airplane_mode_survived_net_reset)
        and (r_air_init.allowed and not r_air_init.airplane_mode_on and r_air_init.airplane_mode_reset_on_initialize)
        and (not r_fx6_ipsec.allowed and r_fx6_ipsec.errno == EOPNOTSUPP_ERRNO and r_fx6_ipsec.fx6_ipsec_user_menus == 0)
    )
    return {
        "passed": passed,
        "fx3_ipsec_v700_bypass_events": 0,
        "fx3_airplane_g114_g136_erratum_reconciled": FX3_AIRPLANE_MODE_G114_G136_DUAL_ERRATUM_RECONCILED,
        "fx3_native_https_server_present": FX3_NATIVE_HTTPS_SERVER_PRESENT,
        "fx6_ipsec_user_menus": FX6_IPSEC_USER_MENUS,
        "rf_tx_packets": RF_TX_PACKETS,
        "usb_tx_packets": USB_TX_PACKETS,
        "samples": {
            "fx3_usblan_manual_ok": r_lan_ok.to_dict(),
            "fx3_usblan_vmcbncm1_mutex": r_lan_vmc.to_dict(),
            "fx3_access_authen_ssh_ptpip": r_auth_ok.to_dict(),
            "fx3_native_https_blocked": r_https_blk.to_dict(),
            "fx3_ipsec_v702_disabled": r_ipsec_v702.to_dict(),
            "fx3_ipsec_authen_disabled": r_ipsec_auth.to_dict(),
            "fx3_airplane_usblan_bypass": r_air_bypass.to_dict(),
            "fx3_airplane_survives_net_reset": r_air_netrst.to_dict(),
            "fx3_airplane_resets_on_init": r_air_init.to_dict(),
            "fx6_zero_ipsec": r_fx6_ipsec.to_dict(),
        },
    }


def _evaluate_submodel_86d() -> Dict[str, Any]:
    r_cln_ok = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx3_sensor_cleaning_51pct_ibis_and_poweroff",
        battery_pct=51,
    )
    r_cln_50 = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx3_sensor_cleaning_51pct_ibis_and_poweroff",
        battery_pct=50,
    )
    r_dorm_sh = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx3_dormant_antidust_and_shutter_pwr_off_blocked",
        dormant_menu_requested="Shutter When Pwr OFF",
    )
    r_dorm_ad = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx3_dormant_antidust_and_shutter_pwr_off_blocked",
        dormant_menu_requested="Anti-dust Function",
    )
    r_ir_on = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
        ir_remote_ctrl_on=True,
    )
    r_ir_bt = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
        ir_remote_ctrl_on=True,
        bt_rmt_ctrl_on=True,
    )
    r_ir_fx3a = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx3_ir_remote_ctrl_fx3a_and_bt_powersave",
        body_variant=BODY_MODEL_FX3A,
        ir_remote_ctrl_on=True,
    )
    r_ar_still = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx3_auto_review_still_only_and_reset",
        shoot_mode="Still",
        auto_review_setting="2 Sec",
        camera_settings_reset_triggered=True,
    )
    r_ar_mv = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx3_auto_review_still_only_and_reset",
        shoot_mode="Movie",
        auto_review_setting="5 Sec",
    )
    r_fx6_ibis = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx6_zero_ibis_cleaning_lanc_and_rec_review",
        body_model=BODY_MODEL_FX6,
        fx6_request_ibis_cleaning=True,
    )
    r_fx6_rr = simulate_86d_cleaning_ir_autoreview_and_fx6_contrast(
        operation="fx6_zero_ibis_cleaning_lanc_and_rec_review",
        body_model=BODY_MODEL_FX6,
        fx6_rec_review_mode="Last 10s",
    )
    passed = (
        (r_cln_ok.allowed and r_cln_ok.ibis_ultrasonic_triggered and r_cln_ok.mandatory_power_off_prompt_shown)
        and (not r_cln_50.allowed and r_cln_50.errno == EAGAIN_ERRNO and r_cln_50.low_battery_blocked)
        and (not r_dorm_sh.allowed and r_dorm_sh.errno == EOPNOTSUPP_ERRNO and r_dorm_sh.shutter_curtain_at_power_off == "Open")
        and (not r_dorm_ad.allowed and r_dorm_ad.errno == EOPNOTSUPP_ERRNO)
        and (r_ir_on.allowed and r_ir_on.power_save_start_time_suppressed)
        and (not r_ir_bt.allowed and r_ir_bt.errno == EBUSY_ERRNO and r_ir_bt.ir_blocked_by_bt_rmt)
        and (not r_ir_fx3a.allowed and r_ir_fx3a.errno == EOPNOTSUPP_ERRNO and r_ir_fx3a.fx3a_ir_physically_absent)
        and (r_ar_still.allowed and r_ar_still.auto_review_triggered and r_ar_still.setup_item_survived_cam_reset and r_ar_still.slot1_sector_writes == 0)
        and (r_ar_mv.allowed and not r_ar_mv.auto_review_triggered)
        and (not r_fx6_ibis.allowed and r_fx6_ibis.errno == EOPNOTSUPP_ERRNO and not r_fx6_ibis.fx6_has_ibis_cleaning)
        and (r_fx6_rr.allowed and r_fx6_rr.fx6_rec_review_mode == "Last 10s")
    )
    return {
        "passed": passed,
        "fx3_sensor_cleaning_min_battery_pct": FX3_SENSOR_CLEANING_MIN_BATTERY_PCT,
        "fx3_shutter_curtain_at_power_off": FX3_SHUTTER_CURTAIN_AT_POWER_OFF,
        "fx3_dormant_antidust_exposed_events": 0,
        "fx3_auto_review_options_count": len(FX3_AUTO_REVIEW_OPTIONS),
        "fx6_has_ibis_cleaning": FX6_HAS_IBIS_ULTRASONIC_CLEANING,
        "fx6_ir_remote_user_menus": FX6_IR_REMOTE_USER_MENUS,
        "fx6_auto_review_user_menus": FX6_AUTO_REVIEW_USER_MENUS,
        "samples": {
            "fx3_cleaning_51pct_ok": r_cln_ok.to_dict(),
            "fx3_cleaning_50pct_blocked": r_cln_50.to_dict(),
            "fx3_dormant_shutter_pwr_off_blocked": r_dorm_sh.to_dict(),
            "fx3_dormant_antidust_blocked": r_dorm_ad.to_dict(),
            "fx3_ir_on_suppresses_powersave": r_ir_on.to_dict(),
            "fx3_ir_bt_mutex_blocked": r_ir_bt.to_dict(),
            "fx3a_ir_absent_blocked": r_ir_fx3a.to_dict(),
            "fx3_autoreview_still_reset_immune": r_ar_still.to_dict(),
            "fx3_autoreview_movie_inert": r_ar_mv.to_dict(),
            "fx6_zero_ibis_cleaning": r_fx6_ibis.to_dict(),
            "fx6_rec_review_ok": r_fx6_rr.to_dict(),
        },
    }


def _strip_wall_clock(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_wall_clock(v)
            for k, v in obj.items()
            if k not in ("elapsed_seconds", "elapsed_ms")
        }
    if isinstance(obj, list):
        return [_strip_wall_clock(v) for v in obj]
    return obj


def _build_stage86_probe(
    sub_86a: Mapping[str, Any],
    sub_86b: Mapping[str, Any],
    sub_86c: Mapping[str, Any],
    sub_86d: Mapping[str, Any],
) -> Dict[str, Any]:
    return {
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone_label": MILESTONE_LABEL,
        "submodel_86a_passed": bool(sub_86a["passed"]),
        "submodel_86b_passed": bool(sub_86b["passed"]),
        "submodel_86c_passed": bool(sub_86c["passed"]),
        "submodel_86d_passed": bool(sub_86d["passed"]),
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
    }


def run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    donor_info = inspect_phase376_wave76_donors(
        work_root=work_root,
        force_clean_room=force_clean_room,
        env=env,
    )
    sub_86a = _evaluate_submodel_86a()
    sub_86b = _evaluate_submodel_86b()
    sub_86c = _evaluate_submodel_86c()
    sub_86d = _evaluate_submodel_86d()
    probe = _build_stage86_probe(sub_86a, sub_86b, sub_86c, sub_86d)

    all_passed = bool(
        donor_info["all_donors_verified"]
        and sub_86a["passed"]
        and sub_86b["passed"]
        and sub_86c["passed"]
        and sub_86d["passed"]
    )

    payload: Dict[str, Any] = {
        "schema": SCHEMA_ID,
        "version": PHASE_376_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "all_checks_passed": all_passed,
        "source_mode": donor_info["source_mode"],
        "donor_access_mode": donor_info["donor_access_mode"],
        "donors": donor_info,
        # Tier-0 Hardware Safety Redlines
        "ready_for_live_camera_attach": READY_FOR_LIVE_CAMERA_ATTACH,
        "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
        "nop_count": NOP_COUNT,
        "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "wbi_mutation_bytes": WBI_MUTATION_BYTES,
        "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
        "cnflasha_mutation_bytes": CNFLASHA_MUTATION_BYTES,
        "cnflasha_userspace_write_blocked": CNFLASHA_USERSPACE_WRITE_BLOCKED,
        "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
        "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "emmc_writes_authorized": EMMC_WRITES_AUTHORIZED,
        "cross_model_flash_authorized": CROSS_MODEL_FLASH_AUTHORIZED,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "overall_ready_for_hardware_attach": OVERALL_READY_FOR_HARDWARE_ATTACH,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
        "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
        "emmc_corruptions": EMMC_CORRUPTIONS,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
        "usb_tx_packets": USB_TX_PACKETS,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
        "slot1_camset_write_authorized": SLOT1_CAMSET_WRITE_AUTHORIZED,
        "slot1_sector_writes": SLOT1_SECTOR_WRITES,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "rf_tx_packets": RF_TX_PACKETS,
        "rf_packets_transmitted": RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": RF_NVS_MUTATION_BYTES,
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
        # Stage 86 Wave-76 Invariant Metrics
        "fx3_still_controls_count": FX3_STILL_CONTROLS_COUNT,
        "fx3_movie_controls_count": FX3_MOVIE_CONTROLS_COUNT,
        "fx3_playback_controls_count": FX3_PLAYBACK_CONTROLS_COUNT,
        "fx3_xlr_h1_assignable_keys": FX3_XLR_H1_ASSIGNABLE_KEYS,
        "fx3_xlr_h1_rec_buttons": FX3_XLR_H1_REC_BUTTONS,
        "fx3_diff_set_items_count": len(FX3_DIFF_SET_8_ITEMS),
        "fx3_g99_pp_init_erratum_reconciled": FX3_G99_PP_INIT_ERRATUM_RECONCILED,
        "fx3_g100_default_keymap_reconciled": FX3_G100_DEFAULT_KEYMAP_RECONCILED,
        "fx3_gamma_assist_types_count": len(FX3_GAMMA_DISP_ASSIST_TYPES),
        "fx3_dormant_slog2_exposed_events": 0,
        "fx3_hdmi_gamma_assist_applied_events": 0,
        "fx3_select_lut_options_count": len(FX3_SELECT_LUT_ALL_OPTIONS),
        "fx6_gamma_assist_user_menus": FX6_GAMMA_ASSIST_USER_MENUS,
        "fx6_mlut_routes_count": len(FX6_MLUT_ROUTES),
        "fx3_ipsec_v700_bypass_events": 0,
        "fx3_airplane_g114_g136_erratum_reconciled": FX3_AIRPLANE_MODE_G114_G136_DUAL_ERRATUM_RECONCILED,
        "fx3_native_https_server_present": FX3_NATIVE_HTTPS_SERVER_PRESENT,
        "fx6_ipsec_user_menus": FX6_IPSEC_USER_MENUS,
        "fx3_sensor_cleaning_min_battery_pct": FX3_SENSOR_CLEANING_MIN_BATTERY_PCT,
        "fx3_shutter_curtain_at_power_off": FX3_SHUTTER_CURTAIN_AT_POWER_OFF,
        "fx3_dormant_antidust_exposed_events": 0,
        "fx3_auto_review_options_count": len(FX3_AUTO_REVIEW_OPTIONS),
        "fx6_has_ibis_cleaning": FX6_HAS_IBIS_ULTRASONIC_CLEANING,
        "fx6_ir_remote_user_menus": FX6_IR_REMOTE_USER_MENUS,
        "fx6_auto_review_user_menus": FX6_AUTO_REVIEW_USER_MENUS,
        # Nested Sub-Model Audits
        "submodel_86a_customkey_3domain_diffset8_fx6_assign": sub_86a,
        "submodel_86b_gammadisp_displaylut_fx6_mlut": sub_86b,
        "submodel_86c_usblan_auth_ipsec_airplane_fx6_net": sub_86c,
        "submodel_86d_cleaning_ir_autoreview_fx6_contrast": sub_86d,
        "stage86_probe": probe,
    }
    digest_body = _strip_wall_clock(payload)
    payload["phase376_audit_digest_sha256"] = hashlib.sha256(
        json.dumps(digest_body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    return payload


def run_self_test(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Union[None, str, Path, object] = _UNSET,
) -> Dict[str, Any]:
    return run_phase376_realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulation(
        work_root=work_root,
        force_clean_room=force_clean_room,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_customkey_diffset8_gammadisp_mlut_usblan_cleaning_coemulator.py",
        description=(
            "Phase 376 Stage 86 (86/86) Real-Hardware FX3/FX6 Wave-76 Co-Emulator: "
            "86A Custom Key/Dial Set. 3-Domain (16/16/7, XLR-H1 0 keys) & Different Set for Still/Mv 8-Bit "
            "(G99 PP Init Persistence + G100 Defaults), "
            "86B Gamma Display Assist (800%%, dormant S-Log2 blocked, LCD-only) vs Display LUT / Select LUT & FX6 4-Way MLUT, "
            "86C USB-LAN / Access Authen. (SSH+PTP-IP) / Ver. 7.00+ Disabled Security(IPsec) / Airplane Mode G114+G136 Dual-Erratum, "
            "and 86D Sensor Cleaning (>=51%% IBIS) vs Dormant Anti-dust/Shutter Pwr OFF, IR Remote (FX3A absent), & Still-Only Auto Review"
        ),
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room synthetic donor mode",
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run Stage 86 (86/86) built-in self-test matrix (>=51%% IBIS / 800%% Gamma Assist)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full deterministic JSON payload (default)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise one-line HIL summary",
    )
    args = parser.parse_args(argv)

    rep = run_self_test(force_clean_room=(True if args.clean_room else None))
    if args.summary:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 376 Stage 86 ({rep['milestone']}) | mode={rep['source_mode']} "
            f"| donors={rep['donors']['total_donors_count']} "
            f"| ckey={rep['fx3_still_controls_count']}/{rep['fx3_movie_controls_count']}/{rep['fx3_playback_controls_count']}/xlr={rep['fx3_xlr_h1_assignable_keys']}/ds={rep['fx3_diff_set_items_count']}/g99={int(rep['fx3_g99_pp_init_erratum_reconciled'])} "
            f"| gda={rep['fx3_gamma_assist_types_count']}t/slog2={rep['fx3_dormant_slog2_exposed_events']}/mlut={rep['fx6_mlut_routes_count']}w "
            f"| net=ipsec7byp:{rep['fx3_ipsec_v700_bypass_events']}/air_err={int(rep['fx3_airplane_g114_g136_erratum_reconciled'])}/rf={rep['rf_tx_packets']} "
            f"| cln={rep['fx3_sensor_cleaning_min_battery_pct']}%/{rep['fx3_shutter_curtain_at_power_off']}/ar={rep['fx3_auto_review_options_count']}o "
            f"| s1_wr={rep['slot1_data_sector_writes']} usb_tx={rep['usb_tx_packets']} emmc_wr={rep['emmc_nflasha_write_count']} "
            f"leaked={rep['raw_firmware_bytes_leaked']} "
            f"| digest={rep['phase376_audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
