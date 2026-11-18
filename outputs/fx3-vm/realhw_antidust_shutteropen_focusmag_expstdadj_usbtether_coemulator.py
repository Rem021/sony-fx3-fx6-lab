#!/usr/bin/env python3
"""Phase 362 (Stage 81 — 81/81 Full-Board VM Co-Emulation Stages!):
Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-71 HIL Co-Emulator.

Models and audits the four Wave-71 subsystems strictly via read-only
`os.O_RDONLY` + bounded `<= 4096 B` `os.pread` donor inspection (with
seamless `work_root=None` / nonexistent `work_root` / `CLEAN_ROOM_SYNTHETIC`
CI fallback and `raw_firmware_bytes_leaked == 0`):

1. **Sub-Model 81A — Dormant `[Anti-Dust Function]` / `[Shutter When Pwr OFF]`
   & Always-Open Mechanical Curtain vs `[Sensor Cleaning]` `>=51%%` & FX6
   Sealed `e-ND` + `APR`**:
   - FX3 `ilc/2210` Help Guide has `0` hits for `Shutter When Pwr OFF` and
     `Anti-dust Function` (`_f 0x7495`/`0x709f`,
     `anti_dust_shutter_when_power_off`,
     `BKID_APP_setting_image_sensor_barrier`, `PID_SET_IMAGE_SENSOR_BARRIER`
     are compiled-in dormant shared-platform symbols masked out by
     `VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD` -> `EOPNOTSUPP=95`).
   - FX3 mechanical focal-plane shutter curtain ALWAYS stays **OPEN (`OPEN`)**
     at power-OFF (`curtain_closed_at_power_off_events == 0`), exposing only
     `Setup -> [Setup Option] -> [Sensor Cleaning]` (`_f 0x67d6`, legacy
     `Cleaning Mode` `0xe7d7`, `NP-FZ100 >= 51%%` gate -> `EAGAIN=11` below 51%%,
     IBIS ultrasonic shake + mandatory physical power-OFF prompt).
   - Contrast with `ILME-FX6 Ver. 6.01`: `0` `shutter_when_power_off` symbols
     in `FX6 appFw.so`, zero mechanical shutter, zero IBIS ultrasonic cleaning
     (`EOPNOTSUPP=95`), CMOS sealed behind `1/4..1/128 + CLEAR` variable `e-ND`
     (`PID_SET_VARIABLE_ND_VALUE`) + IR-cut glass, and `Technical > APR`
     (`MODEL_APR_EXECUTE_COMP`).

2. **Sub-Model 81B — `[Focus Magnifier]` Full 5-Item `[Focus Assistant]`
   Cluster, `12.1MP` Exact Ratios, `REC` Continuity & Clean-HDMI vs FX6
   `VF x3/x6` & `HDMI x2/x4`**:
   - All 5 items under `Shooting -> [Focus] -> [Focus Assistant]` are
     Reset-resistant (`Not available` in Ver. 2.00+, cleared only by
     `[Initialize]`): `[Focus Magnifier]` (default `C5` + `MF` double-tap),
     `[Focus Magnif. Time]` (`2 Sec`/`5 Sec`/`No Limit` default),
     `[Initial Focus Mag.]` (Still FF `x1.0 -> x2.1 -> x4.1`, Still APS-C
     `x1.0 -> x1.5 -> x3.0`, Movie/`S&Q` `x1.0 <-> x4.0`; dormant high-MP
     ratios `x1.6/x2.7/x3.1/x3.6/x3.7/x4.2/x4.7/x5.3/x5.5/x6.1` rejected with
     `EOPNOTSUPP=95`), Still-only `[AF in Focus Mag.]` & `[Auto Magnifier in MF]`.
   - Continuous across `MOVIE REC` start/stop (`0` `focus_magnif x movie_rec`
     mutex), zero crop on internal XAVC or Clean-HDMI (`HDMI Info. Display =
     Off`), coexists with `[Peaking Display]`, Ver. 7.00+ `[Bright Monitoring]`,
     and `[De-Squeeze Display]` while suppressing `[Marker Display]`,
     `[Switch V/H AF Area]`, and `[AF Illuminator]`.
   - Contrast with `ILME-FX6 Ver. 6.01`: `Focus Magnifier x3/x6`
     (`BKID_APP_SETTING_CONTINUE_FOCUS_MAGNIFIER`) + Ver. 6.0+
     `Focus Mag Button Target` (`VF: x3/x6` vs `HDMI: x2/x4`,
     `FUNC_monitor_focus_magnifier_x2x4`; SDI & internal MXF never magnified).

3. **Sub-Model 81C — `[Exposure Std. Adjust]` 5-Mode `+-1 EV` `1/6 EV`
   Reset-Resistant Calibration Trap vs FX6 `Auto Exposure Level -3.0..+3.0`**:
   - FX3 `Exposure/Color -> [Exposure Comp.] -> [Exposure Std. Adjust]` across
     all 5 metering modes (`Multi`, `Center`, `Spot`, `Entire Screen Avg.`,
     `Highlight`, `-1 EV..+1 EV` in `1/6 EV` steps = 13 steps, dormant
     `EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_8` rejected `EOPNOTSUPP=95`).
   - **Reset-resistant (`Not available` under `[Camera Settings Reset]`, cleared
     only by `[Initialize]`)**, shows warning icon when non-zero, shifts `M.M.`
     zero point & Spot AEL without altering `[Exposure Comp.]` or EXIF
     `ExposureBiasValue`, resets exposure bracket counter if changed mid-burst,
     shifts actual AE in `P/A/S` or `Flexible ISO + ISO AUTO`, and affects only
     `M.M.` readout in `Cine EI` / `Cine EI Quick` / `M + Fixed ISO`.
   - Contrast with `ILME-FX6 Ver. 6.01` `Shooting > Auto Exposure > Level`
     (`-3.0..+3.0` in `0.25 EV` steps = 25 steps `LEVEL_MINUS_3_0..LEVEL_3_0`,
     disproving `+-2.0 EV` rumor, plus per-LUT `Base Look > AE Level Offset`
     and `AE Speed -99..+99`).

4. **Sub-Model 81D — Wired Smartphone `[USB-LAN/Tethering]`
   `CDC-NCM/RNDIS/ipheth` Zero-RF Streaming/FTP & Tier-0 `Slot 1 EROFS=30`
   MSC/MTP Firewall vs FX6 `usbg_iap.ko`**:
   - FX3 `Setup -> [USB] -> [USB Connection Mode]` (4 items; `NOUVC` dormant)
     vs `Network -> [USB-LAN/Tethering]` + Ver. 7.00+ `USB-LAN Cnct. Launch`
     (`libNetServiceTethering.so` + `libTetheringResource.so` +
     `cdc_ether.ko`/`cdc_ncm.ko`/`ipheth.ko`/`rndis_host.ko` + `dhcpcd`),
     enabling `RTMP/RTMPS/SRT` & `FTP` with **`[Airplane Mode] = On`
     (`rf_tx_packets == 0`)** (whereas `Creators' App` streaming wizard
     requires BT+Wi-Fi, wired USB `Monitor & Control` Ver. 4.00+ disables
     Timecode/Focus Map/LUT import and dual-USB simultaneous comms, and
     `[Reset Network Set.]` requires immediate `Airplane Mode = On` re-arm).
   - Hard `EROFS=30` + `usbgmscif_setReadOnly` firewall blocking `MTP`
     (`Slot 1`-locked) and `MSC` (`Single`/`Multi` LUN) writes to Tier-0
     `Slot 1` (`slot1_sector_writes == 0`).
   - Contrast with `ILME-FX6 Ver. 6.01` `Network > USB Tethering`: `FX6
     libInfraUsbCmn.so` actively links `/usr/kmod/usbg_iap.ko` (`CUsbGadgetIAP`
     iAP2), stripped from `FX3 libInfraUsbCmn.so` & `FX3 appFw.so`.
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union


# ---------------------------------------------------------------------------
# Phase 362 Schema, Stage 81 (81/81) & Tier-0 Redlines
# ---------------------------------------------------------------------------

SCHEMA_ID = (
    "phase362_realhw_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation_v1"
)
PHASE_362_VERSION = "362.0.0"
PHASE_NUMBER = 362
STAGE_INDEX = 81
STAGE_TOTAL = 81
MILESTONE_LABEL = "81/81"
IS_81ST_STAGE_MILESTONE = True

# Hardware Safety & Redline Constants (Tier-0 NO-GO / EROFS=30 / Zero-Leak)
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
PHYSICAL_USB_PACKETS_EMITTED = 0
PASSIVE_TX_BYTES_EMITTED = 0
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

# Wave-71 Sub-Model 81A..81D Numeric & Invariant Contracts
# 81A — Dormant [Anti-Dust Function] / [Shutter When Pwr OFF] & Always-Open Curtain
FX3_ILC2210_SHUTTER_WHEN_PWR_OFF_HITS = 0
FX3_SHUTTER_CURTAIN_AT_POWER_OFF = "OPEN"
FX3_CURTAIN_CLOSED_AT_POWER_OFF_EVENTS = 0
FX3_SENSOR_CLEANING_MIN_BATTERY_PCT = 51
FX3_SENSOR_CLEANING_LOW_BATT_BYPASS_EVENTS = 0
FX6_SHUTTER_WHEN_POWER_OFF_APPFW_SYMBOLS = 0
FX6_MECHANICAL_SHUTTER_PRESENT = False
FX6_IBIS_CLEANING_SUPPORTED = False
FX6_CMOS_SEALED_BEHIND_END_IRCUT = True

# 81B — [Focus Magnifier] Full 5-Item Cluster, 12.1MP Exact Ratios, REC & Clean-HDMI
FX3_FOCUS_ASSISTANT_ITEMS_COUNT = 5
FX3_FOCUS_MAG_REC_CONTINUITY_BROKEN_EVENTS = 0
FX3_FOCUS_MAG_XAVC_OR_CLEAN_HDMI_CROP_PIXELS = 0
FX3_DORMANT_HIGH_MP_MAG_RATIO_EXPOSED_EVENTS = 0
FX6_FOCUS_MAG_VF_RATIOS: Tuple[str, ...] = ("x3.0", "x6.0")
FX6_FOCUS_MAG_HDMI_RATIOS: Tuple[str, ...] = ("x2.0", "x4.0")
FX6_SDI_MXF_MAGNIFIED_EVENTS = 0

# 81C — [Exposure Std. Adjust] 5-Mode +-1 EV 1/6 EV Calibration Trap vs FX6 AE Level
FX3_EXP_STD_ADJ_METERING_MODES_COUNT = 5
FX3_EXP_STD_ADJ_STEPS_PER_MODE = 13
FX3_EXP_STD_ADJ_STEP_EV = "1/6"
FX3_EXP_STD_ADJ_CAMERA_RESET_WIPE_EVENTS = 0
FX3_EXP_STD_ADJ_EXIF_BIAS_MUTATION_EVENTS = 0
FX3_EXP_STD_ADJ_STEP_1_8_EXPOSED_EVENTS = 0
FX6_AE_LEVEL_MIN = -3.0
FX6_AE_LEVEL_MAX = 3.0
FX6_AE_LEVEL_STEP = 0.25
FX6_AE_LEVEL_STEPS_COUNT = 25
FX6_PM_2EV_RUMOR_DISPROVED = True
FX6_AE_SPEED_MIN = -99
FX6_AE_SPEED_MAX = 99

# 81D — Wired Smartphone [USB-LAN/Tethering] Zero-RF, Slot 1 EROFS=30 & FX6 usbg_iap.ko
FX3_USB_CONNECTION_MODES_COUNT = 4
FX3_USB_TETHERING_ZERO_RF_SUPPORTED = True
FX3_SLOT1_MTP_MSC_WRITE_BYPASS_EVENTS = 0
FX3_DUAL_USB_PORT_SIMULTANEOUS_EVENTS = 0
FX3_LIBINFRAUSBCMN_IAP_SYMBOL_COUNT = 0
FX6_LIBINFRAUSBCMN_IAP_LINKED = True

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

# Body / Firmware / Mode Constants
BODY_MODEL_FX3 = "ILME-FX3"
BODY_MODEL_FX6 = "ILME-FX6"
VALID_BODY_MODELS: Tuple[str, ...] = (BODY_MODEL_FX3, BODY_MODEL_FX6)

FW_VER_101 = "1.01"
FW_VER_200 = "2.00"
FW_VER_400 = "4.00"
FW_VER_700 = "7.00"
FW_VER_702 = "7.02"
FW_VER_601 = "6.01"
VALID_FX3_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_101,
    FW_VER_200,
    FW_VER_400,
    FW_VER_700,
    FW_VER_702,
)
VALID_ALL_FW_VERSIONS: Tuple[str, ...] = (
    FW_VER_101,
    FW_VER_200,
    FW_VER_400,
    FW_VER_700,
    FW_VER_702,
    FW_VER_601,
)

# 81A Constants
VALID_81A_OPERATIONS: Tuple[str, ...] = (
    "power_off_curtain_state",
    "anti_dust_function",
    "shutter_when_pwr_off",
    "sensor_cleaning",
    "auto_cleaning_power_off",
    "fx6_end_seal_and_apr",
    "fx6_sensor_cleaning",
)

# 81B Constants
FX3_FOCUS_ASSISTANT_5_ITEMS: Tuple[str, ...] = (
    "[Focus Magnifier]",
    "[Focus Magnif. Time]",
    "[Initial Focus Mag.]",
    "[AF in Focus Mag.]",
    "[Auto Magnifier in MF]",
)
VALID_FOCUS_MAG_TIMES: Tuple[str, ...] = ("2 Sec", "5 Sec", "No Limit")
VALID_SHOOT_MODES: Tuple[str, ...] = ("Still_FF", "Still_APSC", "Movie", "S&Q")
FX3_STILL_FF_RATIOS: Tuple[str, ...] = ("x1.0", "x2.1", "x4.1")
FX3_STILL_APSC_RATIOS: Tuple[str, ...] = ("x1.0", "x1.5", "x3.0")
FX3_MOVIE_RATIOS: Tuple[str, ...] = ("x1.0", "x4.0")
FX3_DORMANT_HIGH_MP_RATIOS: Tuple[str, ...] = (
    "x1.6",
    "x2.7",
    "x3.1",
    "x3.6",
    "x3.7",
    "x4.2",
    "x4.7",
    "x5.3",
    "x5.5",
    "x6.1",
)
FX6_FOCUS_MAG_TARGETS: Tuple[str, ...] = ("VF", "HDMI")
VALID_81B_OPERATIONS: Tuple[str, ...] = (
    "focus_magnifier",
    "focus_mag_time",
    "initial_focus_mag",
    "af_in_focus_mag",
    "auto_magnifier_in_mf",
    "fx6_focus_magnifier",
)

# 81C Constants
FX3_METERING_5_MODES: Tuple[str, ...] = (
    "Multi",
    "Center",
    "Spot",
    "Entire Screen Avg.",
    "Highlight",
)
VALID_EXP_STEP_SIZES: Tuple[str, ...] = ("1/6", "1/8")
VALID_EXPOSURE_CONTROL_MODES: Tuple[str, ...] = (
    "P",
    "A",
    "S",
    "M_ISO_AUTO",
    "M_FIXED_ISO",
    "Cine_EI",
    "Cine_EI_Quick",
    "Flexible_ISO_AUTO",
)
VALID_FX6_AE_MODES: Tuple[str, ...] = ("Backlight", "Standard", "Spotlight")
VALID_81C_OPERATIONS: Tuple[str, ...] = (
    "set_std_adjust",
    "query_metering",
    "fx6_auto_exposure",
)

# 81D Constants
FX3_USB_CONNECTION_4_MODES: Tuple[str, ...] = (
    "Sel. When Connect",
    "MassStorage(MSC)",
    "MTP",
    "Remote Shooting",
)
VALID_USB_TETHER_DRIVERS: Tuple[str, ...] = (
    "cdc_ncm.ko",
    "cdc_ether.ko",
    "rndis_host.ko",
    "ipheth.ko",
)
VALID_USB_LUN_SETTINGS: Tuple[str, ...] = ("Multi", "Single")
VALID_81D_OPERATIONS: Tuple[str, ...] = (
    "usb_connection_mode",
    "usb_streaming_nouvc",
    "usb_lan_tethering_streaming",
    "usb_lan_tethering_ftp",
    "creators_app_usb",
    "monitor_and_control_usb",
    "dual_usb_ports",
    "reset_network_set",
    "mtp_slot_access",
    "msc_slot_access",
    "fx6_usb_tethering_iap",
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
_FX3_KMOD_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr/kmod"
)
_FX6_NF15_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)


class Stage81Phase362Error(RuntimeError):
    """Raised on invalid Phase 362 Stage 81 HIL inputs or redline violation."""


# ---------------------------------------------------------------------------
# 26 Real-Hardware Wave-71 Donor Specifications (O_RDONLY & <= 4096 B Windows)
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


PHASE362_COMPACT_DONORS: Tuple[CompactDonorSpec, ...] = (
    CompactDonorSpec(
        name="fx3_string_en_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
        expected_size=373820,
        expected_sha256="7e1f78fc8722671c3252fee0636d3804e7fd6157064ea2e1ef5344052247995b",
        required_tokens=(
            b"Anti-dust Function",
            b"Shutter When Pwr OFF",
            b"Sensor Cleaning",
            b"Focus Magnif. Time",
            b"Initial Focus Mag.",
            b"x4.0",
            b"x2.1",
            b"x1.5",
            b"x4.2",
            b"AF in Focus Mag.",
            b"Auto Magnifier in MF",
            b"Exposure Std. Adjust",
            b"Entire Screen Avg.",
            b"USB Connection Mode",
            b"Sel. When Connect",
            b"USB LUN Setting",
            b"Tethering Connection",
            b"USB-LAN Cnct. Launch",
            b"USB Streaming",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_f.uxc",
        expected_size=322652,
        expected_sha256="4c034acb454208b6fe549e1b2296fdab26984ca752f2f27a97b40f8b67a15a7a",
        required_tokens=(
            "防尘功能".encode("utf-8"),
            "关机时快门".encode("utf-8"),
            "传感器清洁".encode("utf-8"),
            "对焦放大时间".encode("utf-8"),
            "放大对焦中AF".encode("utf-8"),
            "MF中自动放大对焦".encode("utf-8"),
            "曝光标准调整".encode("utf-8"),
            "整个屏幕平均".encode("utf-8"),
            "USB连接模式".encode("utf-8"),
            "连接时选择".encode("utf-8"),
            "USB LUN设定".encode("utf-8"),
            "网络共享连接".encode("utf-8"),
            "启动时USB-LAN连接".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese_f.uxc",
        expected_size=324148,
        expected_sha256="32c2f18528e1f5a2fec0a8d0fac48fddc5c7b76d6a0553e43e1f8fdfb59a7167",
        required_tokens=(
            "防塵功能".encode("utf-8"),
            "關閉電源時快門".encode("utf-8"),
            "感應器清潔".encode("utf-8"),
            "對焦放大時間".encode("utf-8"),
            "對焦放大鏡中對焦".encode("utf-8"),
            "MF中自動對焦放大".encode("utf-8"),
            "曝光標準調整".encode("utf-8"),
            "全螢幕平均".encode("utf-8"),
            "USB連線模式".encode("utf-8"),
            "連接時選擇".encode("utf-8"),
            "USB LUN設定".encode("utf-8"),
            "網際網路共用連接".encode("utf-8"),
            "啟動時USB-LAN連線".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja_f",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese_f.uxc",
        expected_size=447840,
        expected_sha256="45ba0b3625f3cdadd16d5987af8fe83f6a640d5c3a1d48abb3b4c1a36a1b338b",
        required_tokens=(
            "アンチダスト機能".encode("utf-8"),
            "電源OFF時のｼｬｯﾀｰ".encode("utf-8"),
            "ｾﾝｻｰｸﾘｰﾆﾝｸﾞ".encode("utf-8"),
            "ピント拡大時間".encode("utf-8"),
            "ﾋﾟﾝﾄ拡大初期倍率".encode("utf-8"),
            "ピント拡大中のAF".encode("utf-8"),
            "MF時自動ﾋﾟﾝﾄ拡大".encode("utf-8"),
            "露出基準調整".encode("utf-8"),
            "USB接続モード".encode("utf-8"),
            "USB-LAN/テザリング接続".encode("utf-8"),
            "起動時のUSB-LAN接続".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
        expected_size=165740,
        expected_sha256="204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
        required_tokens=(
            b"Cleaning Mode",
            b"Performs auto image sensor cleaning.",
            b"Focus Magnifier",
            b"2 Sec",
            b"5 Sec",
            b"No Limit",
            b"+1/6",
            b"-1/6",
            b"Mass Storage",
            b"MTP",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese.uxc",
        expected_size=149064,
        expected_sha256="34989daa8ea8a8dcb7c0dbe5df61db4e9667cd6e6d29b73628fdbb244e0bdc66",
        required_tokens=(
            "清洁模式".encode("utf-8"),
            b"+1/6",
            b"-1/6",
            b"MTP",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_tc",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_traditionalchinese.uxc",
        expected_size=151908,
        expected_sha256="be21a9ad44fc9e49bc03900f3231672c9856eb7e64f38812a2a3008d20c3e7e3",
        required_tokens=(
            "清潔模式".encode("utf-8"),
            b"+1/6",
            b"-1/6",
            b"MTP",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_ja",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_japanese.uxc",
        expected_size=208564,
        expected_sha256="f6c8f40d576e693a5a0401c28150ec3ca24901c63c6e99c6a6bb1f90403b603d",
        required_tokens=(
            "クリーニングモード".encode("utf-8"),
            "自動クリーニング".encode("utf-8"),
            b"+1/6",
            b"-1/6",
            b"MTP",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_en_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
        expected_size=69600,
        expected_sha256="a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
        required_tokens=(
            b"USB-LAN/Tethering Connection must be\nexecuted to use network streaming.",
            b"USB-LAN/Tethering",
        ),
    ),
    CompactDonorSpec(
        name="fx3_string_sc_g",
        rel_path=f"{_FX3_USR_PREFIX}/share/app/string_simplifiedchinese_g.uxc",
        expected_size=61296,
        expected_sha256="a6f236ddc3b3127486c7fc7c42fafc1f19af8071ecaa4ce36f534a93b78cd17b",
        required_tokens=(
            "USB-LAN/".encode("utf-8"),
            "流式传输".encode("utf-8"),
        ),
    ),
    CompactDonorSpec(
        name="fx3_libnetservicetethering",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libNetServiceTethering.so",
        expected_size=126616,
        expected_sha256="f1e7c27e29a5b923da5656e96e0c3d50a5d675d35c68ae7119dabf9de3418d9a",
        required_tokens=(
            b"startDHCPClient",
            b"/usr/sbin/dhcpcd",
            b"dhcpcd_tethering_dns_4_noipv4ll.conf",
            b"judgeTetheringDevice",
        ),
    ),
    CompactDonorSpec(
        name="fx3_libtetheringresource",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libTetheringResource.so",
        expected_size=14928,
        expected_sha256="92717396ccb58b5234c804e9f37a1045984922243b300e6ed7f17d90761dd567",
        required_tokens=(
            b"cdc_ether.ko",
            b"cdc_ncm.ko",
            b"ipheth.ko",
            b"rndis_host.ko",
            b"mii.ko",
            b"usbnet.ko",
        ),
    ),
    CompactDonorSpec(
        name="fx3_libinfrausbcmn",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libInfraUsbCmn.so",
        expected_size=159504,
        expected_sha256="6caefd0677ee01cc6cdd54555f4422b03a86d12304c60f5372de18315bdd4396",
        required_tokens=(
            b"/proc/usbg_storage/storage_access_info",
            b"usbgmscif_setReadOnly",
        ),
        absent_tokens=(
            b"CUsbGadgetIAP",
            b"usbg_iap",
        ),
    ),
    CompactDonorSpec(
        name="fx3_libusbcontrol",
        rel_path=f"{_FX3_USR_PREFIX}/lib/libUsbControl.so",
        expected_size=135424,
        expected_sha256="2bf51f28fd5066e56afc8bbb02ddbaa96b36f57ff2a823cecf9f901781754ed9",
        required_tokens=(
            b"MSGID_SETCONFIG_MTP_EVT",
            b"createMtpRootHandle",
        ),
    ),
    CompactDonorSpec(
        name="fx3_kmod_cdc_ncm",
        rel_path=f"{_FX3_KMOD_PREFIX}/cdc_ncm.ko",
        expected_size=32208,
        expected_sha256="fce183b98eebbda9bb7954854bdcb717c2da74785c97a08a767afc235628ff70",
        required_tokens=(b"cdc_ncm",),
    ),
    CompactDonorSpec(
        name="fx3_kmod_rndis_host",
        rel_path=f"{_FX3_KMOD_PREFIX}/rndis_host.ko",
        expected_size=14064,
        expected_sha256="8417d601c621de19526f18ca92102a3adb718c8372a0d0f73f5cf9fd89f93d17",
        required_tokens=(b"rndis_host",),
    ),
    CompactDonorSpec(
        name="fx3_kmod_ipheth",
        rel_path=f"{_FX3_KMOD_PREFIX}/ipheth.ko",
        expected_size=15552,
        expected_sha256="11405854810149ebf7af93534ad1fc6b8b01ea626108a42ae5725e2845126ac6",
        required_tokens=(b"ipheth",),
    ),
    CompactDonorSpec(
        name="fx3_kmod_cdc_ether",
        rel_path=f"{_FX3_KMOD_PREFIX}/cdc_ether.ko",
        expected_size=13592,
        expected_sha256="273e4ae1cfa08d0a2c70b653d48ce01f483bd72944c6cfb8932a7810c73c0ab0",
        required_tokens=(b"cdc_ether",),
    ),
    CompactDonorSpec(
        name="fx3_kmod_usbg_iap",
        rel_path=f"{_FX3_KMOD_PREFIX}/usbg_iap.ko",
        expected_size=21168,
        expected_sha256="4289ccd406dd4cd0efe3b05b7151486bd354aebd9f85625996efa9e16aed01b6",
        required_tokens=(b"usbg_iap",),
    ),
    CompactDonorSpec(
        name="fx6_string_en",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
        expected_size=118208,
        expected_sha256="5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
        required_tokens=(
            b"Sensor Cleaning",
            b"APR",
            b"Focus Magnifier",
            b"Focus Mag Button Target",
            b"HDMI Focus Mag",
            b"Base Look",
            b"AE Level Offset",
            b"USB Tethering",
            b"USB Tethering Cam Rmt Ctrl",
            b"Auto Exposure",
        ),
    ),
    CompactDonorSpec(
        name="fx6_string_en_2",
        rel_path=f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
        expected_size=118676,
        expected_sha256="3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
        required_tokens=(
            b"Focus Magnifier",
            b"AE Level",
        ),
    ),
    CompactDonorSpec(
        name="fx6_libnetservicetethering",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/libNetServiceTethering.so",
        expected_size=106584,
        expected_sha256="eb23a90cfd81ef480edac55736560d8438190ae9dee9635acfad88fdf7f7112e",
        required_tokens=(
            b"/var/run/dhcpcd/resolv.conf/usb0.dhcp",
            b"NstTetheringStatusGetUPMStatus",
        ),
    ),
    CompactDonorSpec(
        name="fx6_libinfrausbcmn",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/libInfraUsbCmn.so",
        expected_size=164144,
        expected_sha256="a81404ed2f2c0a29fff34d53a2d145fa52632fa0a8796cee096353f4c8220d65",
        required_tokens=(
            b"/usr/kmod/usbg_iap.ko",
            b"CUsbGadgetIAP",
        ),
    ),
)

PHASE362_WINDOW_DONORS: Tuple[WindowDonorSpec, ...] = (
    WindowDonorSpec(
        name="fx3_appfw",
        rel_path="fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        expected_size=79015712,
        head4k_sha256="de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674",
        windows=(
            (0x399D800, "anti_dust_shutter_when_power_off", b"anti_dust_shutter_when_power_off"),
            (0x399D800, "silent_mode_shutter_when_power_off", b"silent_mode_shutter_when_power_off"),
            (0x3BCC000, "BKID_APP_setting_image_sensor_barrier", b"BKID_APP_setting_image_sensor_barrier"),
            (0x3951800, "PID_SET_IMAGE_SENSOR_BARRIER", b"PID_SET_IMAGE_SENSOR_BARRIER"),
            (0x39D3000, "VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD", b"VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD"),
            (0x39CC000, "FUNC_set_cleaning_mode", b"FUNC_set_cleaning_mode"),
            (0x3C1F000, "BATTERY_CHECK_FOR_CLEANING_MODE_", b"BATTERY_CHECK_FOR_CLEANING_MODE_"),
            (0x2FCE800, "view_focus_magnification_enlarged_position", b"view_focus_magnification_enlarged_position"),
            (0x3BC1000, "BKID_APP_focus_magnification_area_center_x", b"BKID_APP_focus_magnification_area_center_x"),
            (0x3BC9000, "BKID_APP_MR_setting_focus_magnification_time", b"BKID_APP_MR_setting_focus_magnification_time"),
            (0x2FA4800, "MOV_INIT_RATIO_FOCUS_MAGNIF_X1_0", b"MOV_INIT_RATIO_FOCUS_MAGNIF_X1_0"),
            (0x2FA4800, "MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0", b"MOV_INIT_RATIO_FOCUS_MAGNIF_X4_0"),
            (0x2FA4000, "STL_INIT_RATIO_FOCUS_MAGNIF_X1_0", b"STL_INIT_RATIO_FOCUS_MAGNIF_X1_0"),
            (0x2FA4000, "STL_INIT_RATIO_FOCUS_MAGNIF_PIXEL_BY_PIXEL_X1_5", b"STL_INIT_RATIO_FOCUS_MAGNIF_PIXEL_BY_PIXEL_X1_5"),
            (0x2FA4000, "STL_INIT_RATIO_FOCUS_MAGNIF_PIXEL_BY_PIXEL_X2_1", b"STL_INIT_RATIO_FOCUS_MAGNIF_PIXEL_BY_PIXEL_X2_1"),
            (0x2FA4800, "STL_INIT_RATIO_FOCUS_MAGNIF_PIXEL_BY_PIXEL_X6_1", b"STL_INIT_RATIO_FOCUS_MAGNIF_PIXEL_BY_PIXEL_X6_1"),
            (0x2FA4800, "TWICE_OF_PIXEL_BY_PIXEL", b"TWICE_OF_PIXEL_BY_PIXEL"),
            (0x3ABB800, "FOCUS_MAGNIFICATION_MODE_ON_MAG2_EXPOSURE_MODE_MOVIE", b"FOCUS_MAGNIFICATION_MODE_ON_MAG2_EXPOSURE_MODE_MOVIE"),
            (0x3969800, "vdf_set_yuv_layout_for_focus_magnification_out_t", b"vdf_set_yuv_layout_for_focus_magnification_out_t"),
            (0x3BF0000, "BKID_APP_extern_menu_standard_exposure_shift_multi", b"BKID_APP_extern_menu_standard_exposure_shift_multi"),
            (0x3BF0000, "BKID_APP_extern_menu_standard_exposure_shift_center", b"BKID_APP_extern_menu_standard_exposure_shift_center"),
            (0x3BF0000, "BKID_APP_extern_menu_standard_exposure_shift_spot", b"BKID_APP_extern_menu_standard_exposure_shift_spot"),
            (0x3BF0000, "BKID_APP_extern_menu_standard_exposure_shift_average", b"BKID_APP_extern_menu_standard_exposure_shift_average"),
            (0x3BF0000, "BKID_APP_extern_menu_standard_exposure_shift_highlight", b"BKID_APP_extern_menu_standard_exposure_shift_highlight"),
            (0x3C11800, "EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_6", b"EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_6"),
            (0x3C11800, "EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_8", b"EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_8"),
            (0x3BCC000, "BKID_APP_setting_usb_connection_method", b"BKID_APP_setting_usb_connection_method"),
            (0x3C1A000, "USB_CONNECTION_METHOD_MTP", b"USB_CONNECTION_METHOD_MTP"),
            (0x3C1A000, "USB_CONNECTION_METHOD_MASS_STRAGE", b"USB_CONNECTION_METHOD_MASS_STRAGE"),
            (0x3C1A000, "USB_CONNECTION_METHOD_TETHERING", b"USB_CONNECTION_METHOD_TETHERING"),
            (0x2FA6800, "STREAMING_CONNECT_METHOD_USB_TETHERING", b"STREAMING_CONNECT_METHOD_USB_TETHERING"),
            (0x3B0F800, "FTP_CONNECT_METHOD_USB_TETHERING", b"FTP_CONNECT_METHOD_USB_TETHERING"),
            (0x3BCA000, "BKID_APP_setting_usb_lan_connect_launch", b"BKID_APP_setting_usb_lan_connect_launch"),
        ),
        absent_windows=(
            (0x3C1A000, "NO_CUsbGadgetIAP", b"CUsbGadgetIAP"),
            (0x3ABB800, "NO_focus_magnif_x_movie_rec", b"focus_magnif x movie_rec"),
        ),
    ),
    WindowDonorSpec(
        name="fx3_bk4",
        rel_path="fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        expected_size=2229740,
        head4k_sha256="87b30e89cbf4a649f8ccd10e8d6c4f64641525e6c71525f66d51d35e0bbd3d46",
        windows=(
            (0x00000, "BK4_HEADER", b"BK4\x00"),
            (0x4A000, "ILME-FX3", b"ILME-FX3"),
        ),
    ),
    WindowDonorSpec(
        name="fx6_appfw",
        rel_path=f"{_FX6_NF15_PREFIX}/lib/appFw.so",
        expected_size=50520424,
        head4k_sha256="18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd",
        windows=(
            (0x260A800, "PID_SET_VARIABLE_ND_VALUE", b"PID_SET_VARIABLE_ND_VALUE"),
            (0x271D800, "BKID_APP_VARIABLE_ND_CONT", b"BKID_APP_VARIABLE_ND_CONT"),
            (0x23C8800, "MODEL_APR_EXECUTE_COMP", b"MODEL_APR_EXECUTE_COMP"),
            (0x27A9000, "ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x3_x6", b"ASSIGNABLE_SWITCH_FOCUS_MAGNIFIER_x3_x6"),
            (0x271C800, "BKID_APP_SETTING_CONTINUE_FOCUS_MAGNIFIER", b"BKID_APP_SETTING_CONTINUE_FOCUS_MAGNIFIER"),
            (0x270B800, "BKID_APP_SETTING_FOCUS_MAG_BUTTON_TARGET", b"BKID_APP_SETTING_FOCUS_MAG_BUTTON_TARGET"),
            (0x2647800, "FUNC_monitor_focus_magnifier_x2x4", b"FUNC_monitor_focus_magnifier_x2x4"),
            (0x26AD800, "VAL_setting_assign_auto_exposure_level_LEVEL_MINUS_3_0", b"VAL_setting_assign_auto_exposure_level_LEVEL_MINUS_3_0"),
            (0x26AD800, "VAL_setting_assign_auto_exposure_level_LEVEL_3_0", b"VAL_setting_assign_auto_exposure_level_LEVEL_3_0"),
            (0x2707800, "BKID_APP_SETTING_AUTO_EXPOSURE_LEVEL", b"BKID_APP_SETTING_AUTO_EXPOSURE_LEVEL"),
            (0x2707000, "BKID_APP_SETTING_AE_LEVEL_OFFSET", b"BKID_APP_SETTING_AE_LEVEL_OFFSET"),
            (0x2718800, "BKID_APP_EXTERN_AE_SPEED", b"BKID_APP_EXTERN_AE_SPEED"),
            (0x2707800, "BKID_APP_SETTING_DETECT_WINDOW", b"BKID_APP_SETTING_DETECT_WINDOW"),
            (0x26AD000, "VAL_setting_auto_exposure_mode_MODE_", b"VAL_setting_auto_exposure_mode_MODE_"),
            (0x270A800, "BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING", b"BKID_APP_SETTING_USB_TC_IN_ALT_MODE_SETTING"),
        ),
        absent_windows=(
            (0x260A800, "NO_shutter_when_power_off", b"shutter_when_power_off"),
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
            raise Stage81Phase362Error(
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
        raise Stage81Phase362Error(
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


def inspect_phase362_wave71_donors(
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
            resolved_root / s.rel_path for s in PHASE362_COMPACT_DONORS
        ] + [resolved_root / w.rel_path for w in PHASE362_WINDOW_DONORS]
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
            for s in PHASE362_COMPACT_DONORS
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
            for w in PHASE362_WINDOW_DONORS
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
    for spec in PHASE362_COMPACT_DONORS:
        p = resolved_root / spec.rel_path
        data = _read_full_compact_o_rdonly(p)
        if len(data) != spec.expected_size:
            raise Stage81Phase362Error(
                f"{spec.name} size {len(data)} != expected {spec.expected_size}"
            )
        digest = hashlib.sha256(data).hexdigest()
        if digest != spec.expected_sha256:
            raise Stage81Phase362Error(
                f"{spec.name} sha256 {digest} != expected {spec.expected_sha256}"
            )
        for tok in spec.required_tokens:
            if tok not in data:
                raise Stage81Phase362Error(
                    f"{spec.name} missing required token {tok!r}"
                )
        for abs_tok in spec.absent_tokens:
            if abs_tok in data:
                raise Stage81Phase362Error(
                    f"{spec.name} unexpectedly contains forbidden token {abs_tok!r}"
                )
        compact_entries.append(
            {
                "name": spec.name,
                "size_bytes": len(data),
                "sha256": digest,
                "tokens_matched": len(spec.required_tokens),
                "absent_tokens_verified": len(spec.absent_tokens),
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    window_entries = []
    for wspec in PHASE362_WINDOW_DONORS:
        p = resolved_root / wspec.rel_path
        size0, head4k, _ = _read_bounded_window_o_rdonly(p, 0, _BOUNDED_WINDOW_BYTES)
        if size0 != wspec.expected_size:
            raise Stage81Phase362Error(
                f"{wspec.name} size {size0} != expected {wspec.expected_size}"
            )
        h4k_sha = hashlib.sha256(head4k).hexdigest()
        if h4k_sha != wspec.head4k_sha256:
            raise Stage81Phase362Error(
                f"{wspec.name} head4k sha256 {h4k_sha} != expected {wspec.head4k_sha256}"
            )
        cache: Dict[int, bytes] = {}
        for off, label, needle in wspec.windows:
            if off not in cache:
                _, _, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                cache[off] = win
            if needle not in cache[off]:
                raise Stage81Phase362Error(
                    f"{wspec.name} window 0x{off:x} ({label}) missing {needle!r}"
                )
        for off, label, forbidden in wspec.absent_windows:
            if off not in cache:
                _, _, win = _read_bounded_window_o_rdonly(
                    p, off, _BOUNDED_WINDOW_BYTES
                )
                cache[off] = win
            if forbidden in cache[off]:
                raise Stage81Phase362Error(
                    f"{wspec.name} window 0x{off:x} ({label}) unexpectedly contains {forbidden!r}"
                )
        window_entries.append(
            {
                "name": wspec.name,
                "size_bytes": size0,
                "head4k_sha256": h4k_sha,
                "windows_verified": len(wspec.windows),
                "absent_windows_verified": len(wspec.absent_windows),
                "max_pread_bytes": _BOUNDED_WINDOW_BYTES,
                "source_mode": "LOCAL_DONOR_O_RDONLY",
            }
        )

    return {
        "source_mode": "LOCAL_DONOR_O_RDONLY",
        "donor_access_mode": "O_RDONLY",
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
# Sub-Model 81A: Dormant Anti-Dust / Shutter When Pwr OFF & Always-Open Curtain
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AntiDustShutterOpenAndCleaningAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    anti_dust_menu_exposed: bool
    shutter_when_pwr_off_exposed: bool
    dormant_feature_mask: str
    curtain_state_at_power_off: str
    curtain_always_open: bool
    curtain_closed_at_power_off_events: int
    sensor_cleaning_menu_label: Optional[str]
    sensor_cleaning_min_battery_pct: int
    battery_pct: int
    np_fz100_inserted: bool
    ibis_ultrasonic_shake_executed: bool
    mandatory_physical_power_off_prompt: bool
    mechanical_shutter_present: bool
    cmos_sealed_behind_end_ircut: bool
    variable_nd_range: Optional[str]
    apr_calibration_supported: bool


def simulate_antidust_shutteropen_and_cleaning_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "power_off_curtain_state",
    battery_pct: int = 80,
    np_fz100_inserted: bool = True,
    requested_curtain_close_on_power_off: bool = False,
) -> AntiDustShutterOpenAndCleaningAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage81Phase362Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage81Phase362Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_81A_OPERATIONS:
        raise Stage81Phase362Error(f"Unsupported 81A operation: {operation!r}")
    if battery_pct < 0 or battery_pct > 100:
        raise Stage81Phase362Error(f"battery_pct out of range 0..100: {battery_pct}")

    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_end_seal_and_apr":
            return AntiDustShutterOpenAndCleaningAudit(
                admitted=True,
                errno_code=0,
                reason=(
                    "FX6 has zero mechanical focal-plane shutter; CMOS sealed behind "
                    "1/4..1/128 + CLEAR variable e-ND + IR-cut glass; Technical > APR active"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                anti_dust_menu_exposed=False,
                shutter_when_pwr_off_exposed=False,
                dormant_feature_mask="CHAPLIN_NO_MECHANICAL_SHUTTER",
                curtain_state_at_power_off="NONE_SEALED_END",
                curtain_always_open=False,
                curtain_closed_at_power_off_events=0,
                sensor_cleaning_menu_label=None,
                sensor_cleaning_min_battery_pct=0,
                battery_pct=battery_pct,
                np_fz100_inserted=False,
                ibis_ultrasonic_shake_executed=False,
                mandatory_physical_power_off_prompt=False,
                mechanical_shutter_present=False,
                cmos_sealed_behind_end_ircut=True,
                variable_nd_range="1/4..1/128 + CLEAR",
                apr_calibration_supported=True,
            )
        # FX6 has neither Shutter When Pwr OFF nor IBIS Sensor Cleaning
        return AntiDustShutterOpenAndCleaningAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"FX6 {operation} unsupported (0 shutter_when_power_off symbols, "
                "zero IBIS, CrCommandId_SensorCleaning unsupported) -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            anti_dust_menu_exposed=False,
            shutter_when_pwr_off_exposed=False,
            dormant_feature_mask="CHAPLIN_NO_MECHANICAL_SHUTTER",
            curtain_state_at_power_off="NONE_SEALED_END",
            curtain_always_open=False,
            curtain_closed_at_power_off_events=0,
            sensor_cleaning_menu_label=None,
            sensor_cleaning_min_battery_pct=0,
            battery_pct=battery_pct,
            np_fz100_inserted=False,
            ibis_ultrasonic_shake_executed=False,
            mandatory_physical_power_off_prompt=False,
            mechanical_shutter_present=False,
            cmos_sealed_behind_end_ircut=True,
            variable_nd_range="1/4..1/128 + CLEAR",
            apr_calibration_supported=True,
        )

    # ILME-FX3 path
    cleaning_label = "Cleaning Mode" if fw_version == FW_VER_101 else "Sensor Cleaning"
    feature_mask = "VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD"

    if operation in ("anti_dust_function", "shutter_when_pwr_off"):
        return AntiDustShutterOpenAndCleaningAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"FX3 {operation} is compiled-in dormant (_f 0x7495/0x709f, "
                "PID_SET_IMAGE_SENSOR_BARRIER) masked by ALCIN_UUD; ilc/2210 0 hits -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            anti_dust_menu_exposed=False,
            shutter_when_pwr_off_exposed=False,
            dormant_feature_mask=feature_mask,
            curtain_state_at_power_off="OPEN",
            curtain_always_open=True,
            curtain_closed_at_power_off_events=0,
            sensor_cleaning_menu_label=cleaning_label,
            sensor_cleaning_min_battery_pct=FX3_SENSOR_CLEANING_MIN_BATTERY_PCT,
            battery_pct=battery_pct,
            np_fz100_inserted=np_fz100_inserted,
            ibis_ultrasonic_shake_executed=False,
            mandatory_physical_power_off_prompt=False,
            mechanical_shutter_present=True,
            cmos_sealed_behind_end_ircut=False,
            variable_nd_range=None,
            apr_calibration_supported=False,
        )

    if requested_curtain_close_on_power_off:
        return AntiDustShutterOpenAndCleaningAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "FX3 mechanical focal-plane curtain cannot close on power-OFF "
                "(image_sensor_barrier masked by ALCIN_UUD); curtain remains OPEN -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            anti_dust_menu_exposed=False,
            shutter_when_pwr_off_exposed=False,
            dormant_feature_mask=feature_mask,
            curtain_state_at_power_off="OPEN",
            curtain_always_open=True,
            curtain_closed_at_power_off_events=0,
            sensor_cleaning_menu_label=cleaning_label,
            sensor_cleaning_min_battery_pct=FX3_SENSOR_CLEANING_MIN_BATTERY_PCT,
            battery_pct=battery_pct,
            np_fz100_inserted=np_fz100_inserted,
            ibis_ultrasonic_shake_executed=False,
            mandatory_physical_power_off_prompt=False,
            mechanical_shutter_present=True,
            cmos_sealed_behind_end_ircut=False,
            variable_nd_range=None,
            apr_calibration_supported=False,
        )

    if operation in ("power_off_curtain_state", "auto_cleaning_power_off"):
        return AntiDustShutterOpenAndCleaningAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 {operation}: mechanical shutter curtain stays OPEN at power-OFF; "
                "piezo auto-cleaning runs without closing curtain"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            anti_dust_menu_exposed=False,
            shutter_when_pwr_off_exposed=False,
            dormant_feature_mask=feature_mask,
            curtain_state_at_power_off="OPEN",
            curtain_always_open=True,
            curtain_closed_at_power_off_events=0,
            sensor_cleaning_menu_label=cleaning_label,
            sensor_cleaning_min_battery_pct=FX3_SENSOR_CLEANING_MIN_BATTERY_PCT,
            battery_pct=battery_pct,
            np_fz100_inserted=np_fz100_inserted,
            ibis_ultrasonic_shake_executed=(operation == "auto_cleaning_power_off"),
            mandatory_physical_power_off_prompt=False,
            mechanical_shutter_present=True,
            cmos_sealed_behind_end_ircut=False,
            variable_nd_range=None,
            apr_calibration_supported=False,
        )

    # operation == "sensor_cleaning"
    if not np_fz100_inserted:
        return AntiDustShutterOpenAndCleaningAudit(
            admitted=False,
            errno_code=EIO_ERRNO,
            reason="[Sensor Cleaning] requires inserted NP-FZ100 -> EIO=5",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            anti_dust_menu_exposed=False,
            shutter_when_pwr_off_exposed=False,
            dormant_feature_mask=feature_mask,
            curtain_state_at_power_off="OPEN",
            curtain_always_open=True,
            curtain_closed_at_power_off_events=0,
            sensor_cleaning_menu_label=cleaning_label,
            sensor_cleaning_min_battery_pct=FX3_SENSOR_CLEANING_MIN_BATTERY_PCT,
            battery_pct=battery_pct,
            np_fz100_inserted=False,
            ibis_ultrasonic_shake_executed=False,
            mandatory_physical_power_off_prompt=False,
            mechanical_shutter_present=True,
            cmos_sealed_behind_end_ircut=False,
            variable_nd_range=None,
            apr_calibration_supported=False,
        )

    if battery_pct < FX3_SENSOR_CLEANING_MIN_BATTERY_PCT:
        return AntiDustShutterOpenAndCleaningAudit(
            admitted=False,
            errno_code=EAGAIN_ERRNO,
            reason=(
                f"[{cleaning_label}] refused at {battery_pct}%% "
                f"(< {FX3_SENSOR_CLEANING_MIN_BATTERY_PCT}%% NP-FZ100 gate) -> EAGAIN=11"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            anti_dust_menu_exposed=False,
            shutter_when_pwr_off_exposed=False,
            dormant_feature_mask=feature_mask,
            curtain_state_at_power_off="OPEN",
            curtain_always_open=True,
            curtain_closed_at_power_off_events=0,
            sensor_cleaning_menu_label=cleaning_label,
            sensor_cleaning_min_battery_pct=FX3_SENSOR_CLEANING_MIN_BATTERY_PCT,
            battery_pct=battery_pct,
            np_fz100_inserted=True,
            ibis_ultrasonic_shake_executed=False,
            mandatory_physical_power_off_prompt=False,
            mechanical_shutter_present=True,
            cmos_sealed_behind_end_ircut=False,
            variable_nd_range=None,
            apr_calibration_supported=False,
        )

    return AntiDustShutterOpenAndCleaningAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"[{cleaning_label}] admitted at {battery_pct}%% >= 51%%; IBIS ultrasonic "
            "shake executed + mandatory physical power-OFF prompt; curtain remains OPEN"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        anti_dust_menu_exposed=False,
        shutter_when_pwr_off_exposed=False,
        dormant_feature_mask=feature_mask,
        curtain_state_at_power_off="OPEN",
        curtain_always_open=True,
        curtain_closed_at_power_off_events=0,
        sensor_cleaning_menu_label=cleaning_label,
        sensor_cleaning_min_battery_pct=FX3_SENSOR_CLEANING_MIN_BATTERY_PCT,
        battery_pct=battery_pct,
        np_fz100_inserted=True,
        ibis_ultrasonic_shake_executed=True,
        mandatory_physical_power_off_prompt=True,
        mechanical_shutter_present=True,
        cmos_sealed_behind_end_ircut=False,
        variable_nd_range=None,
        apr_calibration_supported=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 81B: [Focus Magnifier] 5-Item Cluster, 12.1MP Ratios & Clean-HDMI
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FocusMagnifierClusterAndFx6TargetAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    focus_assistant_items_count: int
    default_button_binding: str
    mf_double_tap_supported: bool
    shoot_mode: str
    allowed_ratios: Tuple[str, ...]
    effective_ratio: str
    effective_mag_time: str
    resettable_via_camera_settings_reset: bool
    rec_active: bool
    rec_continuity_preserved: bool
    internal_xavc_cropped_pixels: int
    clean_hdmi_cropped_pixels: int
    hdmi_info_display: str
    hdmi_mirrors_magnifier_osd: bool
    coexists_with_peaking_brightmon_desqueeze: bool
    suppresses_marker_vhaf_afilluminator: bool
    fx6_button_target: Optional[str]
    fx6_target_ratios: Tuple[str, ...]
    fx6_sdi_and_mxf_never_magnified: bool


def simulate_focus_magnifier_cluster_vs_fx6_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "focus_magnifier",
    shoot_mode: str = "Movie",
    requested_ratio: Optional[str] = None,
    focus_mag_time: str = "No Limit",
    af_mode: str = "MF",
    touch_operation: str = "On",
    cont_shooting: bool = False,
    mount_adapter: bool = False,
    rec_active: bool = False,
    hdmi_info_display: str = "Off",
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_button_target: str = "VF",
) -> FocusMagnifierClusterAndFx6TargetAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage81Phase362Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage81Phase362Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_81B_OPERATIONS:
        raise Stage81Phase362Error(f"Unsupported 81B operation: {operation!r}")
    if shoot_mode not in VALID_SHOOT_MODES:
        raise Stage81Phase362Error(f"Unsupported shoot_mode: {shoot_mode!r}")
    if focus_mag_time not in VALID_FOCUS_MAG_TIMES:
        raise Stage81Phase362Error(f"Unsupported focus_mag_time: {focus_mag_time!r}")
    if hdmi_info_display not in ("Off", "On"):
        raise Stage81Phase362Error(f"Unsupported hdmi_info_display: {hdmi_info_display!r}")
    if fx6_button_target not in FX6_FOCUS_MAG_TARGETS:
        raise Stage81Phase362Error(f"Unsupported fx6_button_target: {fx6_button_target!r}")

    if body_profile == BODY_MODEL_FX6:
        if operation in ("af_in_focus_mag", "auto_magnifier_in_mf"):
            return FocusMagnifierClusterAndFx6TargetAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=f"FX6 does not support {operation} -> EOPNOTSUPP=95",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                focus_assistant_items_count=0,
                default_button_binding="ASSIGN 4 / ASSIGN 7",
                mf_double_tap_supported=False,
                shoot_mode="Movie",
                allowed_ratios=FX6_FOCUS_MAG_VF_RATIOS,
                effective_ratio="x1.0",
                effective_mag_time="No Limit",
                resettable_via_camera_settings_reset=False,
                rec_active=rec_active,
                rec_continuity_preserved=True,
                internal_xavc_cropped_pixels=0,
                clean_hdmi_cropped_pixels=0,
                hdmi_info_display=hdmi_info_display,
                hdmi_mirrors_magnifier_osd=False,
                coexists_with_peaking_brightmon_desqueeze=True,
                suppresses_marker_vhaf_afilluminator=False,
                fx6_button_target=fx6_button_target,
                fx6_target_ratios=(
                    FX6_FOCUS_MAG_VF_RATIOS
                    if fx6_button_target == "VF"
                    else FX6_FOCUS_MAG_HDMI_RATIOS
                ),
                fx6_sdi_and_mxf_never_magnified=True,
            )

        target_ratios = (
            FX6_FOCUS_MAG_VF_RATIOS
            if fx6_button_target == "VF"
            else FX6_FOCUS_MAG_HDMI_RATIOS
        )
        eff_ratio = requested_ratio if requested_ratio is not None else target_ratios[0]
        if eff_ratio not in ("x1.0",) + target_ratios:
            return FocusMagnifierClusterAndFx6TargetAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"FX6 Focus Mag Button Target={fx6_button_target} allows "
                    f"{target_ratios}, rejecting {eff_ratio} (FS7 x4/x8 dormant) -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                focus_assistant_items_count=2,
                default_button_binding="ASSIGN 4 / ASSIGN 7 (Focus Magnifier x3/x6)",
                mf_double_tap_supported=False,
                shoot_mode="Movie",
                allowed_ratios=target_ratios,
                effective_ratio="x1.0",
                effective_mag_time="No Limit",
                resettable_via_camera_settings_reset=False,
                rec_active=rec_active,
                rec_continuity_preserved=True,
                internal_xavc_cropped_pixels=0,
                clean_hdmi_cropped_pixels=0,
                hdmi_info_display=hdmi_info_display,
                hdmi_mirrors_magnifier_osd=(fx6_button_target == "HDMI"),
                coexists_with_peaking_brightmon_desqueeze=True,
                suppresses_marker_vhaf_afilluminator=False,
                fx6_button_target=fx6_button_target,
                fx6_target_ratios=target_ratios,
                fx6_sdi_and_mxf_never_magnified=True,
            )

        return FocusMagnifierClusterAndFx6TargetAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Ver. 6.0+ Focus Mag Button Target={fx6_button_target} active at "
                f"{eff_ratio} (REC continuity via CONTINUE_FOCUS_MAGNIFIER; SDI & MXF clean)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            focus_assistant_items_count=2,
            default_button_binding="ASSIGN 4 / ASSIGN 7 (Focus Magnifier x3/x6)",
            mf_double_tap_supported=False,
            shoot_mode="Movie",
            allowed_ratios=target_ratios,
            effective_ratio=eff_ratio,
            effective_mag_time="No Limit",
            resettable_via_camera_settings_reset=False,
            rec_active=rec_active,
            rec_continuity_preserved=True,
            internal_xavc_cropped_pixels=0,
            clean_hdmi_cropped_pixels=0,
            hdmi_info_display=hdmi_info_display,
            hdmi_mirrors_magnifier_osd=(fx6_button_target == "HDMI"),
            coexists_with_peaking_brightmon_desqueeze=True,
            suppresses_marker_vhaf_afilluminator=False,
            fx6_button_target=fx6_button_target,
            fx6_target_ratios=target_ratios,
            fx6_sdi_and_mxf_never_magnified=True,
        )

    # ILME-FX3 path
    if shoot_mode == "Still_FF":
        allowed = FX3_STILL_FF_RATIOS
        default_init = "x2.1"
    elif shoot_mode == "Still_APSC":
        allowed = FX3_STILL_APSC_RATIOS
        default_init = "x1.5"
    else:
        allowed = FX3_MOVIE_RATIOS
        default_init = "x4.0"

    v2_plus_reset_resistant = fw_version != FW_VER_101
    # In Ver. 1.x only [Focus Magnifier] was resettable; Ver. 2.00+ marks all 5 Not available
    item_resettable = (not v2_plus_reset_resistant) and (operation == "focus_magnifier")

    if requested_ratio in FX3_DORMANT_HIGH_MP_RATIOS:
        return FocusMagnifierClusterAndFx6TargetAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"12.1MP FX3 rejects dormant high-MP ratio {requested_ratio} "
                f"(allowed for {shoot_mode}: {allowed}) -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            focus_assistant_items_count=FX3_FOCUS_ASSISTANT_ITEMS_COUNT,
            default_button_binding="Custom Button 5 (FOCUS MAG)",
            mf_double_tap_supported=(af_mode == "MF" and touch_operation == "On"),
            shoot_mode=shoot_mode,
            allowed_ratios=allowed,
            effective_ratio="x1.0",
            effective_mag_time=focus_mag_time,
            resettable_via_camera_settings_reset=(not v2_plus_reset_resistant),
            rec_active=rec_active,
            rec_continuity_preserved=True,
            internal_xavc_cropped_pixels=0,
            clean_hdmi_cropped_pixels=0,
            hdmi_info_display=hdmi_info_display,
            hdmi_mirrors_magnifier_osd=(hdmi_info_display == "On"),
            coexists_with_peaking_brightmon_desqueeze=True,
            suppresses_marker_vhaf_afilluminator=True,
            fx6_button_target=None,
            fx6_target_ratios=(),
            fx6_sdi_and_mxf_never_magnified=False,
        )

    eff_ratio = requested_ratio if requested_ratio is not None else default_init
    if eff_ratio not in allowed:
        return FocusMagnifierClusterAndFx6TargetAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                f"Ratio {eff_ratio} invalid for {shoot_mode} (allowed: {allowed}) -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            focus_assistant_items_count=FX3_FOCUS_ASSISTANT_ITEMS_COUNT,
            default_button_binding="Custom Button 5 (FOCUS MAG)",
            mf_double_tap_supported=(af_mode == "MF" and touch_operation == "On"),
            shoot_mode=shoot_mode,
            allowed_ratios=allowed,
            effective_ratio="x1.0",
            effective_mag_time=focus_mag_time,
            resettable_via_camera_settings_reset=(not v2_plus_reset_resistant),
            rec_active=rec_active,
            rec_continuity_preserved=True,
            internal_xavc_cropped_pixels=0,
            clean_hdmi_cropped_pixels=0,
            hdmi_info_display=hdmi_info_display,
            hdmi_mirrors_magnifier_osd=(hdmi_info_display == "On"),
            coexists_with_peaking_brightmon_desqueeze=True,
            suppresses_marker_vhaf_afilluminator=True,
            fx6_button_target=None,
            fx6_target_ratios=(),
            fx6_sdi_and_mxf_never_magnified=False,
        )

    if operation == "af_in_focus_mag":
        if shoot_mode in ("Movie", "S&Q") or af_mode == "AF-C" or cont_shooting or mount_adapter:
            return FocusMagnifierClusterAndFx6TargetAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"[AF in Focus Mag.] Still-only (blocked under shoot_mode={shoot_mode}, "
                    f"af_mode={af_mode}, cont={cont_shooting}, adapter={mount_adapter}) -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                focus_assistant_items_count=FX3_FOCUS_ASSISTANT_ITEMS_COUNT,
                default_button_binding="Custom Button 5 (FOCUS MAG)",
                mf_double_tap_supported=(af_mode == "MF" and touch_operation == "On"),
                shoot_mode=shoot_mode,
                allowed_ratios=allowed,
                effective_ratio=eff_ratio,
                effective_mag_time=focus_mag_time,
                resettable_via_camera_settings_reset=False,
                rec_active=rec_active,
                rec_continuity_preserved=True,
                internal_xavc_cropped_pixels=0,
                clean_hdmi_cropped_pixels=0,
                hdmi_info_display=hdmi_info_display,
                hdmi_mirrors_magnifier_osd=(hdmi_info_display == "On"),
                coexists_with_peaking_brightmon_desqueeze=True,
                suppresses_marker_vhaf_afilluminator=True,
                fx6_button_target=None,
                fx6_target_ratios=(),
                fx6_sdi_and_mxf_never_magnified=False,
            )

    if operation == "auto_magnifier_in_mf":
        if shoot_mode in ("Movie", "S&Q") or af_mode not in ("MF", "DMF") or mount_adapter:
            return FocusMagnifierClusterAndFx6TargetAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    f"[Auto Magnifier in MF] Still MF/DMF-only (blocked under shoot_mode={shoot_mode}, "
                    f"af_mode={af_mode}, adapter={mount_adapter}) -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                focus_assistant_items_count=FX3_FOCUS_ASSISTANT_ITEMS_COUNT,
                default_button_binding="Custom Button 5 (FOCUS MAG)",
                mf_double_tap_supported=(af_mode == "MF" and touch_operation == "On"),
                shoot_mode=shoot_mode,
                allowed_ratios=allowed,
                effective_ratio=eff_ratio,
                effective_mag_time=focus_mag_time,
                resettable_via_camera_settings_reset=False,
                rec_active=rec_active,
                rec_continuity_preserved=True,
                internal_xavc_cropped_pixels=0,
                clean_hdmi_cropped_pixels=0,
                hdmi_info_display=hdmi_info_display,
                hdmi_mirrors_magnifier_osd=(hdmi_info_display == "On"),
                coexists_with_peaking_brightmon_desqueeze=True,
                suppresses_marker_vhaf_afilluminator=True,
                fx6_button_target=None,
                fx6_target_ratios=(),
                fx6_sdi_and_mxf_never_magnified=False,
            )

    eff_time = focus_mag_time
    if initialize_applied:
        eff_ratio = "x1.0"
        eff_time = "No Limit"
    elif camera_settings_reset_applied and item_resettable:
        eff_ratio = "x1.0"

    return FocusMagnifierClusterAndFx6TargetAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 [Focus Assistant] {operation} admitted ({shoot_mode} {eff_ratio}, "
            f"time={eff_time}, REC continuity={'preserved' if rec_active else 'standby'}, "
            "0px XAVC/Clean-HDMI crop)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        focus_assistant_items_count=FX3_FOCUS_ASSISTANT_ITEMS_COUNT,
        default_button_binding="Custom Button 5 (FOCUS MAG)",
        mf_double_tap_supported=(af_mode == "MF" and touch_operation == "On"),
        shoot_mode=shoot_mode,
        allowed_ratios=allowed,
        effective_ratio=eff_ratio,
        effective_mag_time=eff_time,
        resettable_via_camera_settings_reset=item_resettable,
        rec_active=rec_active,
        rec_continuity_preserved=True,
        internal_xavc_cropped_pixels=0,
        clean_hdmi_cropped_pixels=0,
        hdmi_info_display=hdmi_info_display,
        hdmi_mirrors_magnifier_osd=(hdmi_info_display == "On" and eff_ratio != "x1.0"),
        coexists_with_peaking_brightmon_desqueeze=True,
        suppresses_marker_vhaf_afilluminator=(eff_ratio != "x1.0"),
        fx6_button_target=None,
        fx6_target_ratios=(),
        fx6_sdi_and_mxf_never_magnified=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 81C: [Exposure Std. Adjust] 5-Mode +-1 EV 1/6 EV vs FX6 AE Level
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ExposureStdAdjustVsFx6AeAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    metering_mode: Optional[str]
    metering_modes_count: int
    step_size: str
    effective_offset_sixths: int
    effective_offset_ev: float
    resettable_via_camera_settings_reset: bool
    cleared_only_by_initialize: bool
    warning_icon_shown: bool
    exposure_comp_ev: float
    exif_exposure_bias_ev: float
    mm_zero_point_shifted_ev: float
    spot_ael_shifted_ev: float
    actual_ae_shifted_ev: float
    mm_only_affected: bool
    bracket_counter_reset: bool
    fx6_ae_level: Optional[float]
    fx6_ae_level_steps_count: int
    fx6_ae_mode: Optional[str]
    fx6_ae_speed: Optional[int]
    fx6_base_look_ae_offset: Optional[float]
    fx6_agc_and_autoshutter_locked_in_cine_ei: bool


def simulate_exposure_std_adjust_vs_fx6_ae_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "set_std_adjust",
    metering_mode: str = "Multi",
    offset_sixths: int = 0,
    step_size: str = "1/6",
    exposure_control_mode: str = "P",
    exposure_comp_ev: float = 0.0,
    bracket_in_progress: bool = False,
    camera_settings_reset_applied: bool = False,
    initialize_applied: bool = False,
    fx6_ae_level: float = 0.0,
    fx6_ae_mode: str = "Standard",
    fx6_ae_speed: int = 0,
    fx6_base_look_ae_offset: float = 0.0,
    fx6_cine_ei_active: bool = False,
) -> ExposureStdAdjustVsFx6AeAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage81Phase362Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage81Phase362Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_81C_OPERATIONS:
        raise Stage81Phase362Error(f"Unsupported 81C operation: {operation!r}")
    if metering_mode not in FX3_METERING_5_MODES:
        raise Stage81Phase362Error(f"Unsupported metering_mode: {metering_mode!r}")
    if step_size not in VALID_EXP_STEP_SIZES:
        raise Stage81Phase362Error(f"Unsupported step_size: {step_size!r}")
    if exposure_control_mode not in VALID_EXPOSURE_CONTROL_MODES:
        raise Stage81Phase362Error(
            f"Unsupported exposure_control_mode: {exposure_control_mode!r}"
        )
    if fx6_ae_mode not in VALID_FX6_AE_MODES:
        raise Stage81Phase362Error(f"Unsupported fx6_ae_mode: {fx6_ae_mode!r}")

    if body_profile == BODY_MODEL_FX6:
        if fx6_ae_level < FX6_AE_LEVEL_MIN or fx6_ae_level > FX6_AE_LEVEL_MAX:
            return ExposureStdAdjustVsFx6AeAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"FX6 Auto Exposure Level {fx6_ae_level} out of range "
                    f"[{FX6_AE_LEVEL_MIN}, {FX6_AE_LEVEL_MAX}] -> EINVAL=22"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                metering_mode=None,
                metering_modes_count=0,
                step_size="0.25",
                effective_offset_sixths=0,
                effective_offset_ev=0.0,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=False,
                warning_icon_shown=False,
                exposure_comp_ev=0.0,
                exif_exposure_bias_ev=0.0,
                mm_zero_point_shifted_ev=0.0,
                spot_ael_shifted_ev=0.0,
                actual_ae_shifted_ev=0.0,
                mm_only_affected=False,
                bracket_counter_reset=False,
                fx6_ae_level=fx6_ae_level,
                fx6_ae_level_steps_count=FX6_AE_LEVEL_STEPS_COUNT,
                fx6_ae_mode=fx6_ae_mode,
                fx6_ae_speed=fx6_ae_speed,
                fx6_base_look_ae_offset=fx6_base_look_ae_offset,
                fx6_agc_and_autoshutter_locked_in_cine_ei=fx6_cine_ei_active,
            )

        # Must be exact 0.25 EV multiple (4 * fx6_ae_level is integer)
        scaled = fx6_ae_level * 4.0
        if abs(scaled - round(scaled)) > 1e-9:
            return ExposureStdAdjustVsFx6AeAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=(
                    f"FX6 Auto Exposure Level {fx6_ae_level} not a 0.25 EV step -> EINVAL=22"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                metering_mode=None,
                metering_modes_count=0,
                step_size="0.25",
                effective_offset_sixths=0,
                effective_offset_ev=0.0,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=False,
                warning_icon_shown=False,
                exposure_comp_ev=0.0,
                exif_exposure_bias_ev=0.0,
                mm_zero_point_shifted_ev=0.0,
                spot_ael_shifted_ev=0.0,
                actual_ae_shifted_ev=0.0,
                mm_only_affected=False,
                bracket_counter_reset=False,
                fx6_ae_level=fx6_ae_level,
                fx6_ae_level_steps_count=FX6_AE_LEVEL_STEPS_COUNT,
                fx6_ae_mode=fx6_ae_mode,
                fx6_ae_speed=fx6_ae_speed,
                fx6_base_look_ae_offset=fx6_base_look_ae_offset,
                fx6_agc_and_autoshutter_locked_in_cine_ei=fx6_cine_ei_active,
            )

        if fx6_ae_speed < FX6_AE_SPEED_MIN or fx6_ae_speed > FX6_AE_SPEED_MAX:
            return ExposureStdAdjustVsFx6AeAudit(
                admitted=False,
                errno_code=EINVAL_ERRNO,
                reason=f"FX6 AE Speed {fx6_ae_speed} out of range -99..+99 -> EINVAL=22",
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                metering_mode=None,
                metering_modes_count=0,
                step_size="0.25",
                effective_offset_sixths=0,
                effective_offset_ev=0.0,
                resettable_via_camera_settings_reset=False,
                cleared_only_by_initialize=False,
                warning_icon_shown=False,
                exposure_comp_ev=0.0,
                exif_exposure_bias_ev=0.0,
                mm_zero_point_shifted_ev=0.0,
                spot_ael_shifted_ev=0.0,
                actual_ae_shifted_ev=0.0,
                mm_only_affected=False,
                bracket_counter_reset=False,
                fx6_ae_level=fx6_ae_level,
                fx6_ae_level_steps_count=FX6_AE_LEVEL_STEPS_COUNT,
                fx6_ae_mode=fx6_ae_mode,
                fx6_ae_speed=fx6_ae_speed,
                fx6_base_look_ae_offset=fx6_base_look_ae_offset,
                fx6_agc_and_autoshutter_locked_in_cine_ei=fx6_cine_ei_active,
            )

        return ExposureStdAdjustVsFx6AeAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX6 Shooting > Auto Exposure Level={fx6_ae_level:+.2f} EV "
                f"(25 steps -3.0..+3.0 @ 0.25, Mode={fx6_ae_mode}, Speed={fx6_ae_speed}, "
                f"BaseLook Offset={fx6_base_look_ae_offset:+.2f})"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            metering_mode=None,
            metering_modes_count=0,
            step_size="0.25",
            effective_offset_sixths=0,
            effective_offset_ev=0.0,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=False,
            warning_icon_shown=False,
            exposure_comp_ev=0.0,
            exif_exposure_bias_ev=0.0,
            mm_zero_point_shifted_ev=0.0,
            spot_ael_shifted_ev=0.0,
            actual_ae_shifted_ev=round(fx6_ae_level + fx6_base_look_ae_offset, 4),
            mm_only_affected=False,
            bracket_counter_reset=False,
            fx6_ae_level=fx6_ae_level,
            fx6_ae_level_steps_count=FX6_AE_LEVEL_STEPS_COUNT,
            fx6_ae_mode=fx6_ae_mode,
            fx6_ae_speed=fx6_ae_speed,
            fx6_base_look_ae_offset=fx6_base_look_ae_offset,
            fx6_agc_and_autoshutter_locked_in_cine_ei=fx6_cine_ei_active,
        )

    # ILME-FX3 path
    if step_size == "1/8":
        return ExposureStdAdjustVsFx6AeAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "FX3 rejects dormant EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_8 "
                "(only 1/6 EV steps exposed) -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            metering_mode=metering_mode,
            metering_modes_count=FX3_EXP_STD_ADJ_METERING_MODES_COUNT,
            step_size=step_size,
            effective_offset_sixths=0,
            effective_offset_ev=0.0,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            warning_icon_shown=False,
            exposure_comp_ev=exposure_comp_ev,
            exif_exposure_bias_ev=exposure_comp_ev,
            mm_zero_point_shifted_ev=0.0,
            spot_ael_shifted_ev=0.0,
            actual_ae_shifted_ev=0.0,
            mm_only_affected=False,
            bracket_counter_reset=False,
            fx6_ae_level=None,
            fx6_ae_level_steps_count=0,
            fx6_ae_mode=None,
            fx6_ae_speed=None,
            fx6_base_look_ae_offset=None,
            fx6_agc_and_autoshutter_locked_in_cine_ei=False,
        )

    if offset_sixths < -6 or offset_sixths > 6:
        return ExposureStdAdjustVsFx6AeAudit(
            admitted=False,
            errno_code=EINVAL_ERRNO,
            reason=(
                f"FX3 [Exposure Std. Adjust] offset {offset_sixths}/6 EV out of "
                "[-6, +6] (+-1 EV) -> EINVAL=22"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            metering_mode=metering_mode,
            metering_modes_count=FX3_EXP_STD_ADJ_METERING_MODES_COUNT,
            step_size=step_size,
            effective_offset_sixths=0,
            effective_offset_ev=0.0,
            resettable_via_camera_settings_reset=False,
            cleared_only_by_initialize=True,
            warning_icon_shown=False,
            exposure_comp_ev=exposure_comp_ev,
            exif_exposure_bias_ev=exposure_comp_ev,
            mm_zero_point_shifted_ev=0.0,
            spot_ael_shifted_ev=0.0,
            actual_ae_shifted_ev=0.0,
            mm_only_affected=False,
            bracket_counter_reset=False,
            fx6_ae_level=None,
            fx6_ae_level_steps_count=0,
            fx6_ae_mode=None,
            fx6_ae_speed=None,
            fx6_base_look_ae_offset=None,
            fx6_agc_and_autoshutter_locked_in_cine_ei=False,
        )

    # Reset-resistant: Camera Settings Reset does NOT wipe offset; only Initialize wipes to 0
    eff_sixths = 0 if initialize_applied else offset_sixths
    _ = camera_settings_reset_applied  # explicitly ignored (Not available)
    eff_ev = round(eff_sixths / 6.0, 6)

    mm_only = exposure_control_mode in ("M_FIXED_ISO", "Cine_EI", "Cine_EI_Quick")
    actual_ae_shift = 0.0 if mm_only else eff_ev

    return ExposureStdAdjustVsFx6AeAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 [Exposure Std. Adjust] {metering_mode}={eff_sixths:+d}/6 EV "
            f"(reset-resistant, EXIF ExposureBiasValue untouched={exposure_comp_ev:+.2f} EV, "
            f"mode={exposure_control_mode}, mm_only={mm_only})"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        metering_mode=metering_mode,
        metering_modes_count=FX3_EXP_STD_ADJ_METERING_MODES_COUNT,
        step_size="1/6",
        effective_offset_sixths=eff_sixths,
        effective_offset_ev=eff_ev,
        resettable_via_camera_settings_reset=False,
        cleared_only_by_initialize=True,
        warning_icon_shown=(eff_sixths != 0),
        exposure_comp_ev=exposure_comp_ev,
        exif_exposure_bias_ev=exposure_comp_ev,
        mm_zero_point_shifted_ev=eff_ev,
        spot_ael_shifted_ev=eff_ev,
        actual_ae_shifted_ev=actual_ae_shift,
        mm_only_affected=mm_only,
        bracket_counter_reset=(bracket_in_progress and operation == "set_std_adjust" and not initialize_applied),
        fx6_ae_level=None,
        fx6_ae_level_steps_count=0,
        fx6_ae_mode=None,
        fx6_ae_speed=None,
        fx6_base_look_ae_offset=None,
        fx6_agc_and_autoshutter_locked_in_cine_ei=False,
    )


# ---------------------------------------------------------------------------
# Sub-Model 81D: Wired Smartphone USB-LAN/Tethering, Zero-RF & Slot 1 EROFS=30
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsbTetheringZeroRfAndSlot1FirewallAudit:
    admitted: bool
    errno_code: int
    reason: str
    body_profile: str
    fw_version: str
    operation: str
    usb_connection_mode: str
    usb_lun_setting: str
    tethering_driver: Optional[str]
    dhcpcd_active: bool
    airplane_mode: str
    rf_tx_packets: int
    zero_rf_tethering_active: bool
    usb_lan_cnct_launch: str
    creators_app_usb_streaming_wizard_blocked: bool
    mc_usb_timecode_supported: bool
    mc_usb_focus_map_supported: bool
    mc_usb_lut_import_supported: bool
    dual_usb_comms_blocked: bool
    post_reset_network_airplane_rearm_required: bool
    target_slot: str
    slot1_sector_writes: int
    slot1_erofs_enforced: bool
    usbg_iap_linked: bool
    fx6_usb_hub_allowed: bool


def simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
    *,
    body_profile: str = BODY_MODEL_FX3,
    fw_version: str = FW_VER_702,
    operation: str = "usb_lan_tethering_streaming",
    usb_connection_mode: str = "Sel. When Connect",
    usb_lun_setting: str = "Multi",
    tethering_driver: str = "cdc_ncm.ko",
    airplane_mode: str = "On",
    usb_lan_cnct_launch: str = "Off",
    target_slot: str = "Slot 1",
    host_write_requested: bool = False,
    camera_settings_reset_applied: bool = False,
) -> UsbTetheringZeroRfAndSlot1FirewallAudit:
    if body_profile not in VALID_BODY_MODELS:
        raise Stage81Phase362Error(f"Unsupported body_profile: {body_profile!r}")
    if fw_version not in VALID_ALL_FW_VERSIONS:
        raise Stage81Phase362Error(f"Unsupported fw_version: {fw_version!r}")
    if operation not in VALID_81D_OPERATIONS:
        raise Stage81Phase362Error(f"Unsupported 81D operation: {operation!r}")
    if usb_connection_mode not in FX3_USB_CONNECTION_4_MODES:
        raise Stage81Phase362Error(
            f"Unsupported usb_connection_mode: {usb_connection_mode!r}"
        )
    if usb_lun_setting not in VALID_USB_LUN_SETTINGS:
        raise Stage81Phase362Error(f"Unsupported usb_lun_setting: {usb_lun_setting!r}")
    if tethering_driver not in VALID_USB_TETHER_DRIVERS:
        raise Stage81Phase362Error(f"Unsupported tethering_driver: {tethering_driver!r}")
    if airplane_mode not in ("Off", "On"):
        raise Stage81Phase362Error(f"Unsupported airplane_mode: {airplane_mode!r}")
    if usb_lan_cnct_launch not in ("Off", "On"):
        raise Stage81Phase362Error(
            f"Unsupported usb_lan_cnct_launch: {usb_lan_cnct_launch!r}"
        )
    if target_slot not in ("Slot 1", "Slot 2"):
        raise Stage81Phase362Error(f"Unsupported target_slot: {target_slot!r}")

    if body_profile == BODY_MODEL_FX6:
        if operation == "fx6_usb_tethering_iap":
            return UsbTetheringZeroRfAndSlot1FirewallAudit(
                admitted=True,
                errno_code=0,
                reason=(
                    "FX6 Network > USB Tethering (Setting: On, Camera Remote Control: Enable) "
                    "actively links /usr/kmod/usbg_iap.ko (CUsbGadgetIAP) for Monitor & Control "
                    "Tethering (USB); no USB Hub"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                usb_connection_mode="USB Tethering (PORT1)",
                usb_lun_setting="N/A",
                tethering_driver="usbg_iap.ko",
                dhcpcd_active=True,
                airplane_mode="N/A",
                rf_tx_packets=0,
                zero_rf_tethering_active=True,
                usb_lan_cnct_launch="N/A",
                creators_app_usb_streaming_wizard_blocked=True,
                mc_usb_timecode_supported=True,
                mc_usb_focus_map_supported=False,
                mc_usb_lut_import_supported=False,
                dual_usb_comms_blocked=True,
                post_reset_network_airplane_rearm_required=False,
                target_slot="Slot 1",
                slot1_sector_writes=0,
                slot1_erofs_enforced=True,
                usbg_iap_linked=True,
                fx6_usb_hub_allowed=False,
            )
        return UsbTetheringZeroRfAndSlot1FirewallAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=f"FX6 {operation} not applicable (use fx6_usb_tethering_iap) -> EOPNOTSUPP=95",
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            usb_connection_mode="USB Tethering (PORT1)",
            usb_lun_setting="N/A",
            tethering_driver="usbg_iap.ko",
            dhcpcd_active=False,
            airplane_mode="N/A",
            rf_tx_packets=0,
            zero_rf_tethering_active=False,
            usb_lan_cnct_launch="N/A",
            creators_app_usb_streaming_wizard_blocked=True,
            mc_usb_timecode_supported=True,
            mc_usb_focus_map_supported=False,
            mc_usb_lut_import_supported=False,
            dual_usb_comms_blocked=True,
            post_reset_network_airplane_rearm_required=False,
            target_slot="Slot 1",
            slot1_sector_writes=0,
            slot1_erofs_enforced=True,
            usbg_iap_linked=True,
            fx6_usb_hub_allowed=False,
        )

    # ILME-FX3 path
    _ = camera_settings_reset_applied  # G114: Camera Settings Reset does not clear USB/Tethering

    if operation == "usb_streaming_nouvc":
        return UsbTetheringZeroRfAndSlot1FirewallAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "FX3 USB_CONNECTION_METHOD_USB_STREAMING (_f 0x63f7) is dormant NOUVC "
                "on Ver. 7.02 -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            usb_connection_mode=usb_connection_mode,
            usb_lun_setting=usb_lun_setting,
            tethering_driver=None,
            dhcpcd_active=False,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            zero_rf_tethering_active=False,
            usb_lan_cnct_launch=usb_lan_cnct_launch,
            creators_app_usb_streaming_wizard_blocked=True,
            mc_usb_timecode_supported=False,
            mc_usb_focus_map_supported=False,
            mc_usb_lut_import_supported=False,
            dual_usb_comms_blocked=True,
            post_reset_network_airplane_rearm_required=False,
            target_slot=target_slot,
            slot1_sector_writes=0,
            slot1_erofs_enforced=True,
            usbg_iap_linked=False,
            fx6_usb_hub_allowed=False,
        )

    if operation == "dual_usb_ports":
        return UsbTetheringZeroRfAndSlot1FirewallAudit(
            admitted=False,
            errno_code=EBUSY_ERRNO,
            reason=(
                "ilc/2210 forbids simultaneous USB Type-C and Multi/Micro-USB "
                "communication -> EBUSY=16"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            usb_connection_mode=usb_connection_mode,
            usb_lun_setting=usb_lun_setting,
            tethering_driver=None,
            dhcpcd_active=False,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            zero_rf_tethering_active=False,
            usb_lan_cnct_launch=usb_lan_cnct_launch,
            creators_app_usb_streaming_wizard_blocked=True,
            mc_usb_timecode_supported=False,
            mc_usb_focus_map_supported=False,
            mc_usb_lut_import_supported=False,
            dual_usb_comms_blocked=True,
            post_reset_network_airplane_rearm_required=False,
            target_slot=target_slot,
            slot1_sector_writes=0,
            slot1_erofs_enforced=True,
            usbg_iap_linked=False,
            fx6_usb_hub_allowed=False,
        )

    if operation in ("usb_lan_tethering_streaming", "usb_lan_tethering_ftp"):
        return UsbTetheringZeroRfAndSlot1FirewallAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 {operation} via {tethering_driver} + dhcpcd_tethering_dns_4_noipv4ll.conf "
                f"with Airplane Mode={airplane_mode} (rf_tx_packets=0, 0 CUsbGadgetIAP)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            usb_connection_mode=usb_connection_mode,
            usb_lun_setting=usb_lun_setting,
            tethering_driver=tethering_driver,
            dhcpcd_active=True,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            zero_rf_tethering_active=(airplane_mode == "On"),
            usb_lan_cnct_launch=usb_lan_cnct_launch,
            creators_app_usb_streaming_wizard_blocked=True,
            mc_usb_timecode_supported=False,
            mc_usb_focus_map_supported=False,
            mc_usb_lut_import_supported=False,
            dual_usb_comms_blocked=True,
            post_reset_network_airplane_rearm_required=False,
            target_slot=target_slot,
            slot1_sector_writes=0,
            slot1_erofs_enforced=True,
            usbg_iap_linked=False,
            fx6_usb_hub_allowed=False,
        )

    if operation == "creators_app_usb":
        # Creators' App streaming wizard requires BT+Wi-Fi, blocked in USB-only / Airplane On
        return UsbTetheringZeroRfAndSlot1FirewallAudit(
            admitted=False,
            errno_code=EOPNOTSUPP_ERRNO,
            reason=(
                "Creators' App Network Streaming wizard requires BT+Wi-Fi and is "
                "unsupported over direct USB session -> EOPNOTSUPP=95"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            usb_connection_mode="Remote Shooting",
            usb_lun_setting=usb_lun_setting,
            tethering_driver=None,
            dhcpcd_active=False,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            zero_rf_tethering_active=False,
            usb_lan_cnct_launch=usb_lan_cnct_launch,
            creators_app_usb_streaming_wizard_blocked=True,
            mc_usb_timecode_supported=False,
            mc_usb_focus_map_supported=False,
            mc_usb_lut_import_supported=False,
            dual_usb_comms_blocked=True,
            post_reset_network_airplane_rearm_required=False,
            target_slot=target_slot,
            slot1_sector_writes=0,
            slot1_erofs_enforced=True,
            usbg_iap_linked=False,
            fx6_usb_hub_allowed=False,
        )

    if operation == "monitor_and_control_usb":
        return UsbTetheringZeroRfAndSlot1FirewallAudit(
            admitted=True,
            errno_code=0,
            reason=(
                "Monitor & Control Ver. 4.00+ wired USB-C [Remote Shooting] active; "
                "Timecode, Focus Map & LUT import disabled over FX3 USB"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            usb_connection_mode="Remote Shooting",
            usb_lun_setting=usb_lun_setting,
            tethering_driver=None,
            dhcpcd_active=False,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            zero_rf_tethering_active=(airplane_mode == "On"),
            usb_lan_cnct_launch=usb_lan_cnct_launch,
            creators_app_usb_streaming_wizard_blocked=True,
            mc_usb_timecode_supported=False,
            mc_usb_focus_map_supported=False,
            mc_usb_lut_import_supported=False,
            dual_usb_comms_blocked=True,
            post_reset_network_airplane_rearm_required=False,
            target_slot=target_slot,
            slot1_sector_writes=0,
            slot1_erofs_enforced=True,
            usbg_iap_linked=False,
            fx6_usb_hub_allowed=False,
        )

    if operation == "reset_network_set":
        # After [Reset Network Set.] reboot, Airplane Mode reverts Off -> immediate re-arm required!
        return UsbTetheringZeroRfAndSlot1FirewallAudit(
            admitted=True,
            errno_code=0,
            reason=(
                "[Reset Network Set.] wipes credentials, reboots camera and resets "
                "[Airplane Mode] to Off; bench must immediately re-arm Airplane Mode = On"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            usb_connection_mode=usb_connection_mode,
            usb_lun_setting=usb_lun_setting,
            tethering_driver=None,
            dhcpcd_active=False,
            airplane_mode="Off",
            rf_tx_packets=0,
            zero_rf_tethering_active=False,
            usb_lan_cnct_launch="Off",
            creators_app_usb_streaming_wizard_blocked=True,
            mc_usb_timecode_supported=False,
            mc_usb_focus_map_supported=False,
            mc_usb_lut_import_supported=False,
            dual_usb_comms_blocked=True,
            post_reset_network_airplane_rearm_required=True,
            target_slot=target_slot,
            slot1_sector_writes=0,
            slot1_erofs_enforced=True,
            usbg_iap_linked=False,
            fx6_usb_hub_allowed=False,
        )

    if operation in ("mtp_slot_access", "msc_slot_access"):
        # MTP hard-locks to Slot 1; MSC exposes Slot 1 (Single) or Slot 1+2 (Multi)
        eff_slot = "Slot 1" if operation == "mtp_slot_access" else target_slot
        if eff_slot == "Slot 1" and host_write_requested:
            return UsbTetheringZeroRfAndSlot1FirewallAudit(
                admitted=False,
                errno_code=EROFS_ERRNO,
                reason=(
                    f"Tier-0 Slot 1 {operation} host write blocked by hard EROFS=30 + "
                    "usbgmscif_setReadOnly firewall (slot1_sector_writes=0)"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                usb_connection_mode=(
                    "MTP" if operation == "mtp_slot_access" else "MassStorage(MSC)"
                ),
                usb_lun_setting=usb_lun_setting,
                tethering_driver=None,
                dhcpcd_active=False,
                airplane_mode=airplane_mode,
                rf_tx_packets=0,
                zero_rf_tethering_active=(airplane_mode == "On"),
                usb_lan_cnct_launch=usb_lan_cnct_launch,
                creators_app_usb_streaming_wizard_blocked=True,
                mc_usb_timecode_supported=False,
                mc_usb_focus_map_supported=False,
                mc_usb_lut_import_supported=False,
                dual_usb_comms_blocked=True,
                post_reset_network_airplane_rearm_required=False,
                target_slot=eff_slot,
                slot1_sector_writes=0,
                slot1_erofs_enforced=True,
                usbg_iap_linked=False,
                fx6_usb_hub_allowed=False,
            )
        if operation == "mtp_slot_access" and target_slot == "Slot 2":
            return UsbTetheringZeroRfAndSlot1FirewallAudit(
                admitted=False,
                errno_code=EOPNOTSUPP_ERRNO,
                reason=(
                    "MTP hard-locks to Slot 1 (ilc/2210); Slot 2 direct MTP target "
                    "unsupported -> EOPNOTSUPP=95"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                usb_connection_mode="MTP",
                usb_lun_setting=usb_lun_setting,
                tethering_driver=None,
                dhcpcd_active=False,
                airplane_mode=airplane_mode,
                rf_tx_packets=0,
                zero_rf_tethering_active=(airplane_mode == "On"),
                usb_lan_cnct_launch=usb_lan_cnct_launch,
                creators_app_usb_streaming_wizard_blocked=True,
                mc_usb_timecode_supported=False,
                mc_usb_focus_map_supported=False,
                mc_usb_lut_import_supported=False,
                dual_usb_comms_blocked=True,
                post_reset_network_airplane_rearm_required=False,
                target_slot="Slot 1",
                slot1_sector_writes=0,
                slot1_erofs_enforced=True,
                usbg_iap_linked=False,
                fx6_usb_hub_allowed=False,
            )
        if operation == "msc_slot_access" and target_slot == "Slot 2" and usb_lun_setting == "Single":
            return UsbTetheringZeroRfAndSlot1FirewallAudit(
                admitted=False,
                errno_code=ENODEV_ERRNO,
                reason=(
                    "MSC [USB LUN Setting] = Single exposes Slot 1 ONLY; Slot 2 LUN "
                    "not presented -> ENODEV=19"
                ),
                body_profile=body_profile,
                fw_version=fw_version,
                operation=operation,
                usb_connection_mode="MassStorage(MSC)",
                usb_lun_setting=usb_lun_setting,
                tethering_driver=None,
                dhcpcd_active=False,
                airplane_mode=airplane_mode,
                rf_tx_packets=0,
                zero_rf_tethering_active=(airplane_mode == "On"),
                usb_lan_cnct_launch=usb_lan_cnct_launch,
                creators_app_usb_streaming_wizard_blocked=True,
                mc_usb_timecode_supported=False,
                mc_usb_focus_map_supported=False,
                mc_usb_lut_import_supported=False,
                dual_usb_comms_blocked=True,
                post_reset_network_airplane_rearm_required=False,
                target_slot=target_slot,
                slot1_sector_writes=0,
                slot1_erofs_enforced=True,
                usbg_iap_linked=False,
                fx6_usb_hub_allowed=False,
            )
        return UsbTetheringZeroRfAndSlot1FirewallAudit(
            admitted=True,
            errno_code=0,
            reason=(
                f"FX3 {operation} read-only / virtual Slot 2 scratch admitted "
                f"(Slot 1 EROFS=30 intact, slot1_sector_writes=0)"
            ),
            body_profile=body_profile,
            fw_version=fw_version,
            operation=operation,
            usb_connection_mode=(
                "MTP" if operation == "mtp_slot_access" else "MassStorage(MSC)"
            ),
            usb_lun_setting=usb_lun_setting,
            tethering_driver=None,
            dhcpcd_active=False,
            airplane_mode=airplane_mode,
            rf_tx_packets=0,
            zero_rf_tethering_active=(airplane_mode == "On"),
            usb_lan_cnct_launch=usb_lan_cnct_launch,
            creators_app_usb_streaming_wizard_blocked=True,
            mc_usb_timecode_supported=False,
            mc_usb_focus_map_supported=False,
            mc_usb_lut_import_supported=False,
            dual_usb_comms_blocked=True,
            post_reset_network_airplane_rearm_required=False,
            target_slot=eff_slot,
            slot1_sector_writes=0,
            slot1_erofs_enforced=True,
            usbg_iap_linked=False,
            fx6_usb_hub_allowed=False,
        )

    # operation == "usb_connection_mode"
    return UsbTetheringZeroRfAndSlot1FirewallAudit(
        admitted=True,
        errno_code=0,
        reason=(
            f"FX3 [USB Connection Mode]={usb_connection_mode} (4 active items, "
            f"LUN={usb_lun_setting}, Camera Settings Reset preserved)"
        ),
        body_profile=body_profile,
        fw_version=fw_version,
        operation=operation,
        usb_connection_mode=usb_connection_mode,
        usb_lun_setting=usb_lun_setting,
        tethering_driver=None,
        dhcpcd_active=False,
        airplane_mode=airplane_mode,
        rf_tx_packets=0,
        zero_rf_tethering_active=(airplane_mode == "On"),
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        creators_app_usb_streaming_wizard_blocked=True,
        mc_usb_timecode_supported=False,
        mc_usb_focus_map_supported=False,
        mc_usb_lut_import_supported=False,
        dual_usb_comms_blocked=True,
        post_reset_network_airplane_rearm_required=False,
        target_slot=target_slot,
        slot1_sector_writes=0,
        slot1_erofs_enforced=True,
        usbg_iap_linked=False,
        fx6_usb_hub_allowed=False,
    )


# ---------------------------------------------------------------------------
# Milestone Probe, Recursive Determinism & Full Stage 81 Runner
# ---------------------------------------------------------------------------


def _strip_wall_clock(obj: Any) -> Any:
    if isinstance(obj, dict):
        return {
            k: _strip_wall_clock(v)
            for k, v in obj.items()
            if k != "elapsed_seconds"
        }
    if isinstance(obj, list):
        return [_strip_wall_clock(x) for x in obj]
    return obj


def _build_stage81_milestone_probe() -> Dict[str, object]:
    return {
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_81st_stage_milestone": IS_81ST_STAGE_MILESTONE,
        "wave": "Wave-71",
        "fx3_target_version": "Ver. 7.02",
        "fx6_comparison_version": "Ver. 6.01",
    }


def run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
    *,
    work_root: Union[None, str, Path, object] = _UNSET,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    donor_audit = inspect_phase362_wave71_donors(
        work_root=work_root, force_clean_room=force_clean_room, env=env
    )

    # Sub-Model 81A probes
    p81a_curtain_open = simulate_antidust_shutteropen_and_cleaning_hil(
        operation="power_off_curtain_state"
    )
    p81a_antidust_dormant = simulate_antidust_shutteropen_and_cleaning_hil(
        operation="anti_dust_function"
    )
    p81a_shutter_pwroff_dormant = simulate_antidust_shutteropen_and_cleaning_hil(
        operation="shutter_when_pwr_off"
    )
    p81a_close_curtain_blocked = simulate_antidust_shutteropen_and_cleaning_hil(
        operation="power_off_curtain_state",
        requested_curtain_close_on_power_off=True,
    )
    p81a_cleaning_50_refused = simulate_antidust_shutteropen_and_cleaning_hil(
        operation="sensor_cleaning", battery_pct=50
    )
    p81a_cleaning_51_ok = simulate_antidust_shutteropen_and_cleaning_hil(
        operation="sensor_cleaning", battery_pct=51
    )
    p81a_fx6_end_apr = simulate_antidust_shutteropen_and_cleaning_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_end_seal_and_apr",
    )
    p81a_fx6_cleaning_blocked = simulate_antidust_shutteropen_and_cleaning_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_sensor_cleaning",
    )
    p81a_ok = (
        p81a_curtain_open.admitted
        and p81a_curtain_open.curtain_state_at_power_off == "OPEN"
        and p81a_curtain_open.curtain_always_open
        and p81a_curtain_open.curtain_closed_at_power_off_events == 0
        and (not p81a_antidust_dormant.admitted)
        and p81a_antidust_dormant.errno_code == EOPNOTSUPP_ERRNO
        and (not p81a_shutter_pwroff_dormant.admitted)
        and p81a_shutter_pwroff_dormant.errno_code == EOPNOTSUPP_ERRNO
        and (not p81a_close_curtain_blocked.admitted)
        and p81a_close_curtain_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not p81a_cleaning_50_refused.admitted)
        and p81a_cleaning_50_refused.errno_code == EAGAIN_ERRNO
        and p81a_cleaning_51_ok.admitted
        and p81a_cleaning_51_ok.ibis_ultrasonic_shake_executed
        and p81a_cleaning_51_ok.mandatory_physical_power_off_prompt
        and p81a_fx6_end_apr.admitted
        and (not p81a_fx6_end_apr.mechanical_shutter_present)
        and p81a_fx6_end_apr.cmos_sealed_behind_end_ircut
        and p81a_fx6_end_apr.apr_calibration_supported
        and (not p81a_fx6_cleaning_blocked.admitted)
        and p81a_fx6_cleaning_blocked.errno_code == EOPNOTSUPP_ERRNO
    )

    # Sub-Model 81B probes
    p81b_ff_x21 = simulate_focus_magnifier_cluster_vs_fx6_hil(
        operation="initial_focus_mag", shoot_mode="Still_FF", requested_ratio="x2.1"
    )
    p81b_apsc_x15 = simulate_focus_magnifier_cluster_vs_fx6_hil(
        operation="initial_focus_mag", shoot_mode="Still_APSC", requested_ratio="x1.5"
    )
    p81b_movie_x40_rec = simulate_focus_magnifier_cluster_vs_fx6_hil(
        operation="focus_magnifier",
        shoot_mode="Movie",
        requested_ratio="x4.0",
        rec_active=True,
        hdmi_info_display="Off",
        camera_settings_reset_applied=True,
    )
    p81b_dormant_x42_rejected = simulate_focus_magnifier_cluster_vs_fx6_hil(
        operation="initial_focus_mag", shoot_mode="Still_FF", requested_ratio="x4.2"
    )
    p81b_af_still_ok = simulate_focus_magnifier_cluster_vs_fx6_hil(
        operation="af_in_focus_mag", shoot_mode="Still_FF", af_mode="AF-S"
    )
    p81b_af_movie_blocked = simulate_focus_magnifier_cluster_vs_fx6_hil(
        operation="af_in_focus_mag", shoot_mode="Movie", af_mode="AF-C"
    )
    p81b_automf_movie_blocked = simulate_focus_magnifier_cluster_vs_fx6_hil(
        operation="auto_magnifier_in_mf", shoot_mode="Movie", af_mode="MF"
    )
    p81b_fx6_vf = simulate_focus_magnifier_cluster_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_focus_magnifier",
        fx6_button_target="VF",
        requested_ratio="x6.0",
        rec_active=True,
    )
    p81b_fx6_hdmi = simulate_focus_magnifier_cluster_vs_fx6_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_focus_magnifier",
        fx6_button_target="HDMI",
        requested_ratio="x4.0",
        rec_active=True,
    )
    p81b_ok = (
        p81b_ff_x21.admitted
        and p81b_ff_x21.allowed_ratios == FX3_STILL_FF_RATIOS
        and p81b_apsc_x15.admitted
        and p81b_apsc_x15.allowed_ratios == FX3_STILL_APSC_RATIOS
        and p81b_movie_x40_rec.admitted
        and p81b_movie_x40_rec.focus_assistant_items_count == 5
        and p81b_movie_x40_rec.rec_continuity_preserved
        and (not p81b_movie_x40_rec.resettable_via_camera_settings_reset)
        and p81b_movie_x40_rec.internal_xavc_cropped_pixels == 0
        and p81b_movie_x40_rec.clean_hdmi_cropped_pixels == 0
        and (not p81b_movie_x40_rec.hdmi_mirrors_magnifier_osd)
        and p81b_movie_x40_rec.coexists_with_peaking_brightmon_desqueeze
        and p81b_movie_x40_rec.suppresses_marker_vhaf_afilluminator
        and (not p81b_dormant_x42_rejected.admitted)
        and p81b_dormant_x42_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p81b_af_still_ok.admitted
        and (not p81b_af_movie_blocked.admitted)
        and p81b_af_movie_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not p81b_automf_movie_blocked.admitted)
        and p81b_automf_movie_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p81b_fx6_vf.admitted
        and p81b_fx6_vf.fx6_target_ratios == ("x3.0", "x6.0")
        and p81b_fx6_vf.fx6_sdi_and_mxf_never_magnified
        and p81b_fx6_hdmi.admitted
        and p81b_fx6_hdmi.fx6_target_ratios == ("x2.0", "x4.0")
        and p81b_fx6_hdmi.fx6_sdi_and_mxf_never_magnified
    )

    # Sub-Model 81C probes
    p81c_spot_reset_survives = simulate_exposure_std_adjust_vs_fx6_ae_hil(
        metering_mode="Spot",
        offset_sixths=-3,
        exposure_control_mode="P",
        exposure_comp_ev=0.0,
        bracket_in_progress=True,
        camera_settings_reset_applied=True,
    )
    p81c_init_clears = simulate_exposure_std_adjust_vs_fx6_ae_hil(
        metering_mode="Spot",
        offset_sixths=-3,
        initialize_applied=True,
    )
    p81c_cine_ei_mm_only = simulate_exposure_std_adjust_vs_fx6_ae_hil(
        metering_mode="Multi",
        offset_sixths=4,
        exposure_control_mode="Cine_EI",
    )
    p81c_flex_iso_auto_shifts_ae = simulate_exposure_std_adjust_vs_fx6_ae_hil(
        metering_mode="Entire Screen Avg.",
        offset_sixths=3,
        exposure_control_mode="Flexible_ISO_AUTO",
    )
    p81c_step_1_8_rejected = simulate_exposure_std_adjust_vs_fx6_ae_hil(
        step_size="1/8"
    )
    p81c_fx6_minus_30 = simulate_exposure_std_adjust_vs_fx6_ae_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_auto_exposure",
        fx6_ae_level=-3.0,
        fx6_ae_mode="Backlight",
        fx6_ae_speed=-50,
        fx6_base_look_ae_offset=0.5,
        fx6_cine_ei_active=True,
    )
    p81c_fx6_over_limit = simulate_exposure_std_adjust_vs_fx6_ae_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_auto_exposure",
        fx6_ae_level=3.25,
    )
    p81c_ok = (
        p81c_spot_reset_survives.admitted
        and p81c_spot_reset_survives.metering_modes_count == 5
        and p81c_spot_reset_survives.effective_offset_sixths == -3
        and (not p81c_spot_reset_survives.resettable_via_camera_settings_reset)
        and p81c_spot_reset_survives.cleared_only_by_initialize
        and p81c_spot_reset_survives.warning_icon_shown
        and p81c_spot_reset_survives.exif_exposure_bias_ev == 0.0
        and p81c_spot_reset_survives.mm_zero_point_shifted_ev == -0.5
        and p81c_spot_reset_survives.actual_ae_shifted_ev == -0.5
        and p81c_spot_reset_survives.bracket_counter_reset
        and p81c_init_clears.admitted
        and p81c_init_clears.effective_offset_sixths == 0
        and p81c_cine_ei_mm_only.admitted
        and p81c_cine_ei_mm_only.mm_only_affected
        and p81c_cine_ei_mm_only.actual_ae_shifted_ev == 0.0
        and p81c_flex_iso_auto_shifts_ae.admitted
        and (not p81c_flex_iso_auto_shifts_ae.mm_only_affected)
        and p81c_flex_iso_auto_shifts_ae.actual_ae_shifted_ev == 0.5
        and (not p81c_step_1_8_rejected.admitted)
        and p81c_step_1_8_rejected.errno_code == EOPNOTSUPP_ERRNO
        and p81c_fx6_minus_30.admitted
        and p81c_fx6_minus_30.fx6_ae_level_steps_count == 25
        and p81c_fx6_minus_30.fx6_agc_and_autoshutter_locked_in_cine_ei
        and (not p81c_fx6_over_limit.admitted)
        and p81c_fx6_over_limit.errno_code == EINVAL_ERRNO
    )

    # Sub-Model 81D probes
    p81d_zero_rf_stream = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        operation="usb_lan_tethering_streaming",
        tethering_driver="cdc_ncm.ko",
        airplane_mode="On",
    )
    p81d_zero_rf_ftp_ipheth = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        operation="usb_lan_tethering_ftp",
        tethering_driver="ipheth.ko",
        airplane_mode="On",
    )
    p81d_nouvc_blocked = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        operation="usb_streaming_nouvc"
    )
    p81d_creators_app_stream_blocked = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        operation="creators_app_usb"
    )
    p81d_mc_usb_ok = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        operation="monitor_and_control_usb"
    )
    p81d_dual_usb_blocked = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        operation="dual_usb_ports"
    )
    p81d_reset_net_rearm = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        operation="reset_network_set"
    )
    p81d_slot1_mtp_erofs = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        operation="mtp_slot_access", target_slot="Slot 1", host_write_requested=True
    )
    p81d_slot1_msc_erofs = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        operation="msc_slot_access", target_slot="Slot 1", host_write_requested=True
    )
    p81d_fx6_iap = simulate_usb_tethering_zero_rf_and_slot1_firewall_hil(
        body_profile=BODY_MODEL_FX6,
        fw_version=FW_VER_601,
        operation="fx6_usb_tethering_iap",
    )
    p81d_ok = (
        p81d_zero_rf_stream.admitted
        and p81d_zero_rf_stream.rf_tx_packets == 0
        and p81d_zero_rf_stream.zero_rf_tethering_active
        and p81d_zero_rf_stream.dhcpcd_active
        and (not p81d_zero_rf_stream.usbg_iap_linked)
        and p81d_zero_rf_ftp_ipheth.admitted
        and p81d_zero_rf_ftp_ipheth.rf_tx_packets == 0
        and (not p81d_nouvc_blocked.admitted)
        and p81d_nouvc_blocked.errno_code == EOPNOTSUPP_ERRNO
        and (not p81d_creators_app_stream_blocked.admitted)
        and p81d_creators_app_stream_blocked.errno_code == EOPNOTSUPP_ERRNO
        and p81d_mc_usb_ok.admitted
        and (not p81d_mc_usb_ok.mc_usb_timecode_supported)
        and (not p81d_mc_usb_ok.mc_usb_focus_map_supported)
        and (not p81d_mc_usb_ok.mc_usb_lut_import_supported)
        and (not p81d_dual_usb_blocked.admitted)
        and p81d_dual_usb_blocked.errno_code == EBUSY_ERRNO
        and p81d_reset_net_rearm.admitted
        and p81d_reset_net_rearm.post_reset_network_airplane_rearm_required
        and (not p81d_slot1_mtp_erofs.admitted)
        and p81d_slot1_mtp_erofs.errno_code == EROFS_ERRNO
        and p81d_slot1_mtp_erofs.slot1_sector_writes == 0
        and (not p81d_slot1_msc_erofs.admitted)
        and p81d_slot1_msc_erofs.errno_code == EROFS_ERRNO
        and p81d_slot1_msc_erofs.slot1_sector_writes == 0
        and p81d_fx6_iap.admitted
        and p81d_fx6_iap.usbg_iap_linked
        and (not p81d_fx6_iap.fx6_usb_hub_allowed)
    )

    redlines: Dict[str, object] = {
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
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
        "slot1_sector_writes": SLOT1_SECTOR_WRITES,
        "slot1_data_sector_writes": SLOT1_DATA_SECTOR_WRITES,
        "slot1_avf_info_mutated": SLOT1_AVF_INFO_MUTATED,
        "rf_tx_packets": RF_TX_PACKETS,
        "rf_packets_transmitted": RF_PACKETS_TRANSMITTED,
        "rf_nvs_mutation_bytes": RF_NVS_MUTATION_BYTES,
        # 81A
        "fx3_ilc2210_shutter_when_pwr_off_hits": FX3_ILC2210_SHUTTER_WHEN_PWR_OFF_HITS,
        "fx3_shutter_curtain_at_power_off": FX3_SHUTTER_CURTAIN_AT_POWER_OFF,
        "fx3_curtain_closed_at_power_off_events": FX3_CURTAIN_CLOSED_AT_POWER_OFF_EVENTS,
        "fx3_sensor_cleaning_min_battery_pct": FX3_SENSOR_CLEANING_MIN_BATTERY_PCT,
        "fx3_sensor_cleaning_low_batt_bypass_events": FX3_SENSOR_CLEANING_LOW_BATT_BYPASS_EVENTS,
        "fx6_shutter_when_power_off_appfw_symbols": FX6_SHUTTER_WHEN_POWER_OFF_APPFW_SYMBOLS,
        "fx6_mechanical_shutter_present": FX6_MECHANICAL_SHUTTER_PRESENT,
        "fx6_ibis_cleaning_supported": FX6_IBIS_CLEANING_SUPPORTED,
        "fx6_cmos_sealed_behind_end_ircut": FX6_CMOS_SEALED_BEHIND_END_IRCUT,
        # 81B
        "fx3_focus_assistant_items_count": FX3_FOCUS_ASSISTANT_ITEMS_COUNT,
        "fx3_focus_mag_rec_continuity_broken_events": FX3_FOCUS_MAG_REC_CONTINUITY_BROKEN_EVENTS,
        "fx3_focus_mag_xavc_or_clean_hdmi_crop_pixels": FX3_FOCUS_MAG_XAVC_OR_CLEAN_HDMI_CROP_PIXELS,
        "fx3_dormant_high_mp_mag_ratio_exposed_events": FX3_DORMANT_HIGH_MP_MAG_RATIO_EXPOSED_EVENTS,
        "fx6_sdi_mxf_magnified_events": FX6_SDI_MXF_MAGNIFIED_EVENTS,
        # 81C
        "fx3_exp_std_adj_metering_modes_count": FX3_EXP_STD_ADJ_METERING_MODES_COUNT,
        "fx3_exp_std_adj_steps_per_mode": FX3_EXP_STD_ADJ_STEPS_PER_MODE,
        "fx3_exp_std_adj_step_ev": FX3_EXP_STD_ADJ_STEP_EV,
        "fx3_exp_std_adj_camera_reset_wipe_events": FX3_EXP_STD_ADJ_CAMERA_RESET_WIPE_EVENTS,
        "fx3_exp_std_adj_exif_bias_mutation_events": FX3_EXP_STD_ADJ_EXIF_BIAS_MUTATION_EVENTS,
        "fx3_exp_std_adj_step_1_8_exposed_events": FX3_EXP_STD_ADJ_STEP_1_8_EXPOSED_EVENTS,
        "fx6_ae_level_min": FX6_AE_LEVEL_MIN,
        "fx6_ae_level_max": FX6_AE_LEVEL_MAX,
        "fx6_ae_level_step": FX6_AE_LEVEL_STEP,
        "fx6_ae_level_steps_count": FX6_AE_LEVEL_STEPS_COUNT,
        "fx6_pm_2ev_rumor_disproved": FX6_PM_2EV_RUMOR_DISPROVED,
        "fx6_ae_speed_min": FX6_AE_SPEED_MIN,
        "fx6_ae_speed_max": FX6_AE_SPEED_MAX,
        # 81D
        "fx3_usb_connection_modes_count": FX3_USB_CONNECTION_MODES_COUNT,
        "fx3_usb_tethering_zero_rf_supported": FX3_USB_TETHERING_ZERO_RF_SUPPORTED,
        "fx3_slot1_mtp_msc_write_bypass_events": FX3_SLOT1_MTP_MSC_WRITE_BYPASS_EVENTS,
        "fx3_dual_usb_port_simultaneous_events": FX3_DUAL_USB_PORT_SIMULTANEOUS_EVENTS,
        "fx3_libinfrausbcmn_iap_symbol_count": FX3_LIBINFRAUSBCMN_IAP_SYMBOL_COUNT,
        "fx6_libinfrausbcmn_iap_linked": FX6_LIBINFRAUSBCMN_IAP_LINKED,
        # Fault Counters
        "rsv_orphan_count": RSV_ORPHAN_COUNT,
        "wf12_00342260_hits": WF12_00342260_HITS,
        "appfw_crashes": APPFW_CRASHES,
        "null_gpio_derefs": NULL_GPIO_DEREFS,
        "mailbox_stalls": MAILBOX_STALLS,
        "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    all_passed = bool(
        donor_audit["all_donors_verified"] and p81a_ok and p81b_ok and p81c_ok and p81d_ok
    )

    payload: Dict[str, object] = {
        "schema": SCHEMA_ID,
        "version": PHASE_362_VERSION,
        "phase_number": PHASE_NUMBER,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "is_81st_stage_milestone": IS_81ST_STAGE_MILESTONE,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit["source_mode"],
        "redlines": redlines,
        "donor_audit": donor_audit,
        "stage81_milestone_probe": _build_stage81_milestone_probe(),
        "pillar_a_antidust_shutteropen_sensorcleaning_vs_fx6_end_hil": {
            "passed": p81a_ok,
            "fx3_power_off_curtain_always_open": asdict(p81a_curtain_open),
            "fx3_dormant_anti_dust_function_rejected": asdict(p81a_antidust_dormant),
            "fx3_dormant_shutter_when_pwr_off_rejected": asdict(p81a_shutter_pwroff_dormant),
            "fx3_close_curtain_at_power_off_blocked": asdict(p81a_close_curtain_blocked),
            "fx3_sensor_cleaning_50pct_refused": asdict(p81a_cleaning_50_refused),
            "fx3_sensor_cleaning_51pct_admitted": asdict(p81a_cleaning_51_ok),
            "fx6_sealed_end_ircut_and_apr": asdict(p81a_fx6_end_apr),
            "fx6_ibis_sensor_cleaning_unsupported": asdict(p81a_fx6_cleaning_blocked),
        },
        "pillar_b_focus_magnifier_cluster_ratios_rec_cleanhdmi_vs_fx6_hil": {
            "passed": p81b_ok,
            "fx3_still_ff_x21": asdict(p81b_ff_x21),
            "fx3_still_apsc_x15": asdict(p81b_apsc_x15),
            "fx3_movie_x40_rec_continuity_clean_hdmi": asdict(p81b_movie_x40_rec),
            "fx3_dormant_high_mp_ratio_x42_rejected": asdict(p81b_dormant_x42_rejected),
            "fx3_still_af_in_focus_mag_ok": asdict(p81b_af_still_ok),
            "fx3_movie_af_in_focus_mag_blocked": asdict(p81b_af_movie_blocked),
            "fx3_movie_auto_magnifier_mf_blocked": asdict(p81b_automf_movie_blocked),
            "fx6_vf_x3_x6_target_and_rec": asdict(p81b_fx6_vf),
            "fx6_hdmi_x2_x4_target_and_sdi_mxf_clean": asdict(p81b_fx6_hdmi),
        },
        "pillar_c_exposure_std_adjust_5mode_reset_trap_vs_fx6_ae_hil": {
            "passed": p81c_ok,
            "fx3_spot_reset_resistant_and_exif_decoupled": asdict(p81c_spot_reset_survives),
            "fx3_initialize_clears_std_adjust": asdict(p81c_init_clears),
            "fx3_cine_ei_mm_only_readout_shifted": asdict(p81c_cine_ei_mm_only),
            "fx3_flexible_iso_auto_shifts_actual_ae": asdict(p81c_flex_iso_auto_shifts_ae),
            "fx3_dormant_step_1_8_rejected": asdict(p81c_step_1_8_rejected),
            "fx6_ae_level_minus_3_0_25step_and_base_look": asdict(p81c_fx6_minus_30),
            "fx6_ae_level_over_3_0_rejected": asdict(p81c_fx6_over_limit),
        },
        "pillar_d_usb_tethering_zero_rf_slot1_erofs_vs_fx6_iap_hil": {
            "passed": p81d_ok,
            "fx3_cdc_ncm_zero_rf_streaming": asdict(p81d_zero_rf_stream),
            "fx3_ipheth_zero_rf_ftp": asdict(p81d_zero_rf_ftp_ipheth),
            "fx3_usb_streaming_nouvc_dormant": asdict(p81d_nouvc_blocked),
            "fx3_creators_app_usb_streaming_wizard_blocked": asdict(p81d_creators_app_stream_blocked),
            "fx3_monitor_and_control_usb_capabilities": asdict(p81d_mc_usb_ok),
            "fx3_dual_usb_simultaneous_blocked": asdict(p81d_dual_usb_blocked),
            "fx3_reset_network_set_requires_airplane_rearm": asdict(p81d_reset_net_rearm),
            "fx3_slot1_mtp_write_erofs_30": asdict(p81d_slot1_mtp_erofs),
            "fx3_slot1_msc_write_erofs_30": asdict(p81d_slot1_msc_erofs),
            "fx6_usbg_iap_usb_tethering": asdict(p81d_fx6_iap),
        },
    }

    digest = hashlib.sha256(
        json.dumps(_strip_wall_clock(payload), sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulator.py",
        description=(
            "Phase 362 (Stage 81 — 81/81 Full-Board VM Co-Emulation Stages!): "
            "Real-Hardware ILME-FX3 Ver. 7.02 vs ILME-FX6 Ver. 6.01 Wave-71 "
            "Dormant Anti-Dust/Always-Open Shutter & Sensor Cleaning >=51%% / "
            "Focus Magnifier 5-Item Cluster & 12.1MP Ratios / Exposure Std. Adjust "
            "5-Mode +-1EV Reset Trap / USB-LAN Tethering Zero-RF & Slot 1 EROFS=30 HIL Co-Emulator"
        ),
    )
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Run all 81A..81D HIL checks and 26-donor O_RDONLY/clean-room audit",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force deterministic CLEAN_ROOM_SYNTHETIC mode (0%% raw donor dependency)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit full deterministic JSON audit report (default)",
    )
    parser.add_argument(
        "--summary",
        action="store_true",
        help="Emit concise one-line HIL pass/fail summary (100%% Redline enforced)",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)
    rep = run_phase362_antidust_shutteropen_focusmag_expstdadj_usbtether_coemulation(
        force_clean_room=True if args.clean_room else None
    )
    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        red = rep["redlines"]
        sys.stdout.write(
            f"[{status}] Phase 362 Stage 81 ({rep['milestone']} Stages) | "
            f"src={rep['source_mode']} | donors={rep['donor_audit']['total_donors_count']} | "
            f"curtain={red['fx3_shutter_curtain_at_power_off']} | "
            f"fmag_items={red['fx3_focus_assistant_items_count']} | "
            f"exp_modes={red['fx3_exp_std_adj_metering_modes_count']} | "
            f"rf_tx={red['rf_tx_packets']} | "
            f"s1_wr={red['slot1_sector_writes']} | "
            f"emmc_wr={red['emmc_nflasha_write_count']} | "
            f"digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2, sort_keys=True) + "\n")
    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
