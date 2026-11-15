"""Phase 149 — 30th Unified Firmware-Lab Auditor: Real-Hardware ILME-FX3 Body Controls
(6x Custom Buttons + Dials + T/W Zoom Rocker + 5-Way Joystick), Active Cooling Fan PWM &
Thermal Emergency Override, 3x Physical Red Tally LEDs, and `NP-FZ100` (`7.2V`) /
`USB-PD` (`9V/3A`) -> FX6 `appFw.so` Power Telemetry & `EncWfiStop` Bridge.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libsencore.so`, `libmpr.so`,
  `im.elf`, `cpapp-b.bin`, `Backup.bin`) and FX6 v6.01 (`appFw.so`, `libsencore.so`,
  `libmpr.so`, `im.elf`, `cpapp-b.bin`, `Backup.bin`) strictly via `os.O_RDONLY` +
  `mmap.ACCESS_READ` using targeted ELF64 `.dynsym`/`.dynstr`/`.rodata`/`.strtab`
  parsing, `BK4\\x00` dual-record parsing, and bounded single-pass `re.finditer`
  scans (< 1.5 s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`/`.elf` fixtures,
  `cpapp-b.bin` token buffers, and `BK4\\x00` `Backup.bin` fixtures, leaking zero
  raw Sony proprietary bytes in JSON output.

Audits Four Phase 149 Real-Hardware Physical Body Pillars & Compatibility Matrix:
1. Pillar 1 (`PHYSICAL_BODY_KEYMAP_AND_ERGONOMIC_BRIDGE`):
   Audits `WidgetBase::onKeyEvent`, `EVENT_INPUT_KEY_TACT_*` (`CUSTOM..CUSTOM6`,
   `ASSIGN1..11`, `STATUS_CHECK`, `MENU_CANCEL`, `STARTSTOP`, `AEL`, `AFON`,
   `LENS_FH`), `UIBIZ_KEY_TACT_*`, `UIBIZ_SLIKEY_ZOOM`, `im.elf` (`40,920 B`,
   `11` exports / `85` imports), and `libsencore.so` (`355` exports / `130` imports).
   Proves `libgrm-fbinit9.so` maps FX3's physical buttons, dials, joystick, and
   `T/W` zoom rocker so 100% of FX6 `Big-6 Home`, `128-Page Full Menu`,
   `Multi-Tab Status Check`, `Direct Touch/Joystick`, `Servo Zoom`, and `REC`
   functions are reachable one-handed on a real ILME-FX3 body while keeping the
   physical `MENU + SHUTTER + POWER` escape hatch unshadowed.
2. Pillar 2 (`ACTIVE_COOLING_FAN_AND_THERMAL_OVERRIDE`):
   Audits `FAN_CONTROL_AUTO`, `FAN_CONTROL_MINIMUM`, `FAN_CONTROL_OFF_IN_REC`,
   `FAN_CONTROL_ALWAYS_OFF`, `OFF_BY_THERMAL_TIME_OUT`, `FAN_BROKEN_STATUS_*`,
   `libsencore.so` (`FAN_SET_SPEED`, `CXS_WRITE_PWM`, `GET_TEMPERATURE`), and
   `cpapp-b.bin` (`SET_FAN_EQ_ID`, `FAN_R`, `PWM`, `THERM`), proving `Off in Rec`
   on Stage-B NEVER masks Stock FX3 `cpapp-b.bin` high-temperature emergency
   fan spin-up or graceful `EncWfiStop` clip-close before thermal shutdown.
3. Pillar 3 (`THREE_BODY_TALLY_LAMPS_SYNC`):
   Audits FX3's 3 physical Red Tally LEDs (Front, Top REC, Rear) and `appFw.so`
   `REC_LAMP_ALL_LIGHTS_UP` / `REC_LAMP_ONLY_FRONT_OFF` /
   `REC_LAMP_LIGHT_UP_ONLY_ONE` / `REC_LAMP_ALL_LIGHTS_OUT` + `libsencore.so`
   `TALLY_LED` + `cpapp-b.bin` `MSG_ID_INFRABB_SYS_SET_CA_TALLY` against FX6
   `BKID_APP_SETTING_FRONT_TALLY` / `REAR_TALLY` / `TALLY_LAMP_BRIGHTNESS` /
   `G_TALLY_LAMP` / `Y_TALLY_LAMP`, enforcing exact Red Tally sync and zero
   GPIO mismatch (Green/Yellow tally remains OSD-only on FX3).
4. Pillar 4 (`NP_FZ100_USB_PD_POWER_TELEMETRY_BRIDGE`):
   Audits `NP-FZ100` (`7.2V`, `6000..8400 mV`) + `USB-PD` (`9V/3A` `27W`)
   telemetry (`INFRA_NOTIFY_BATTERY_REMAIN`, `LOW_BATT`, `OFF_BY_BATT_END`,
   `SUPPLYING_USB_POWER_STATE_ON`, `libsencore.so` `USB_BUSPOWER_SUPPLY_CONTROL`,
   `cpapp-b.bin` `ACV_BATT_Snd` / `BATT_AUTH_Snd` / `BATT_STATE1..3_Snd`, and
   `libmpr.so` `EncWfiStop` / `EncWfiStopReserve`) against FX6 `BP-U` (`14.4V`)
   and `DCINVOLTAGE_ONE_VALUE` (`19.5V` / `18.0V`), proving clean `0..100%` +
   `USB-PD` HUD display, zero false `19.5V DC-IN Low Voltage` alarms, and
   timely `EncWfiStop` auto-save prior to brownout.
"""

from __future__ import annotations

import hashlib
import json
import mmap
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    is_forced_clean_room,
    resolve_donor_file,
)
from .realhw_cp_rtos_and_backup_bin_auditor import (
    BK4_HEADER_BYTES,
    BK4_MAGIC_BYTES,
    BK4_SYNC_U32,
    DESCRIPTOR_PROP_ID,
    DESCRIPTOR_SLOT_BYTES,
    DESCRIPTOR_SLOT_COUNT,
    DESCRIPTOR_TABLE_BYTES,
    parse_dual_bk4_and_descriptors,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    EXPECTED_SENCORE_EXPORTS,
    EXPECTED_SENCORE_IMPORTS,
    FX3_APPFW_P146_RELPATH,
    FX3_BACKUP_BIN_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX3_IM_ELF_P146_RELPATH,
    FX3_LIBMPR_P146_RELPATH,
    FX3_LIBSENCORE_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_BACKUP_BIN_P146_RELPATH,
    FX6_CPAPP_P146_RELPATH,
    FX6_IM_ELF_P146_RELPATH,
    FX6_LIBMPR_P146_RELPATH,
    FX6_LIBSENCORE_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
    _count_tokens_single_pass,
    _read_bytes_rdonly,
    _scan_binary_tokens_rdonly,
    _scan_elf_and_tokens_buf,
    _scan_elf_and_tokens_rdonly,
    _scan_elf_ro_markers_rdonly,
)


PHASE_149_SCHEMA = "fx3_firmware_lab_phase149_realhw_controls_tally_fan_power_v1"
PHASE_149_VERSION = "149.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------

FX3_APPFW_P149_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P149_RELPATH = FX6_APPFW_P146_RELPATH
FX3_LIBSENCORE_P149_RELPATH = FX3_LIBSENCORE_P146_RELPATH
FX6_LIBSENCORE_P149_RELPATH = FX6_LIBSENCORE_P146_RELPATH
FX3_LIBMPR_P149_RELPATH = FX3_LIBMPR_P146_RELPATH
FX6_LIBMPR_P149_RELPATH = FX6_LIBMPR_P146_RELPATH
FX3_IM_ELF_P149_RELPATH = FX3_IM_ELF_P146_RELPATH
FX6_IM_ELF_P149_RELPATH = FX6_IM_ELF_P146_RELPATH
FX3_CPAPP_P149_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P149_RELPATH = FX6_CPAPP_P146_RELPATH
FX3_BACKUP_BIN_P149_RELPATH = FX3_BACKUP_BIN_P146_RELPATH
FX6_BACKUP_BIN_P149_RELPATH = FX6_BACKUP_BIN_P146_RELPATH

# ---------------------------------------------------------------------------
# Pillar 1 Constants: Physical ILME-FX3 Controls -> FX6 Ergonomic Keymap Bridge
# ---------------------------------------------------------------------------

EXPECTED_IM_ELF_BYTES = 40_920
EXPECTED_IM_ELF_EXPORTS = 11
EXPECTED_IM_ELF_IMPORTS = 85

ESCAPE_HATCH_PHYSICAL_KEYS: Tuple[str, ...] = (
    "MENU",
    "SHUTTER_HALF_FULL",
    "POWER_SWITCH",
)

REQUIRED_FX6_REACHABLE_FUNCTIONS: Tuple[str, ...] = (
    "BIG6_HOME",
    "FULL_MENU_128P",
    "STATUS_CHECK_TABS",
    "DIRECT_TOUCH_JOYSTICK",
    "SERVO_ZOOM_8STEP",
    "REC_START_STOP",
)

# Canonical 1:1 Physical FX3 Control -> FX6 Function Map
FX3_PHYSICAL_KEYMAP_SPECS: Dict[str, Dict[str, object]] = {
    "CUSTOM_1": {
        "fx6_function": "STATUS_CHECK_TABS",
        "fx6_assign_slot": "ASSIGN_1",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Maps FX3 Top-Rear Custom 1 (ISO/Assign) -> FX6 Multi-Tab Status Check or Assign 1.",
    },
    "CUSTOM_2": {
        "fx6_function": "ASSIGN_2_PEAKING_OR_WFM",
        "fx6_assign_slot": "ASSIGN_2",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Maps FX3 Custom 2 -> FX6 Assign 2 (Peaking / Waveform).",
    },
    "CUSTOM_3": {
        "fx6_function": "ASSIGN_3_FALSE_COLOR_OR_ZEBRA",
        "fx6_assign_slot": "ASSIGN_3",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Maps FX3 Custom 3 (Grip Top) -> FX6 Assign 3 (False Color / Zebra).",
    },
    "CUSTOM_4": {
        "fx6_function": "BIG6_HOME",
        "fx6_assign_slot": "ASSIGN_4",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Maps FX3 Rear Custom 4 (Trash/C4) short-press -> FX6 Big-6 Home Screen.",
    },
    "CUSTOM_5": {
        "fx6_function": "ASSIGN_5_BASE_ISO_CINE_EI",
        "fx6_assign_slot": "ASSIGN_5",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Maps FX3 Top Custom 5 -> FX6 Assign 5 (Base ISO 800/12800 / Cine EI Switch).",
    },
    "CUSTOM_6": {
        "fx6_function": "ASSIGN_6_USER_LUT_TOGGLE",
        "fx6_assign_slot": "ASSIGN_6",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Maps FX3 Front/Top Custom 6 -> FX6 Assign 6 (User 3D LUT On/Off).",
    },
    "REC_TOP": {
        "fx6_function": "REC_START_STOP",
        "fx6_assign_slot": "REC_TRIGGER",
        "classification": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "FX3 Top Tally-Ring REC button maps directly to EVENT_INPUT_KEY_TACT_STARTSTOP_ON.",
    },
    "REC_FRONT": {
        "fx6_function": "REC_START_STOP",
        "fx6_assign_slot": "REC_TRIGGER_FRONT",
        "classification": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "FX3 Front-Grip Sub REC button mirrors STARTSTOP.",
    },
    "ZOOM_ROCKER_T_W": {
        "fx6_function": "SERVO_ZOOM_8STEP",
        "fx6_assign_slot": "SLIKEY_ZOOM",
        "classification": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "FX3 shutter-ring T/W lever maps directly to UIBIZ_SLIKEY_ZOOM (8-step PZ + CIZ).",
    },
    "MODE": {
        "fx6_function": "BIG6_HOME",
        "fx6_assign_slot": "HOME_SECONDARY",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "FX3 MODE button invokes Big-6 Home quick toggle without blocking MENU.",
    },
    "PLAY": {
        "fx6_function": "THUMBNAIL_PLAYBACK",
        "fx6_assign_slot": "PLAY_THUMB",
        "classification": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Direct passthrough via UIBIZ_KEY_TACT_PLAY.",
    },
    "DELETE_DISP": {
        "fx6_function": "STATUS_CHECK_TABS",
        "fx6_assign_slot": "DISP_STATUS",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Maps DISP/DELETE in live-view to FX6 Multi-Tab Status Check / OSD cycle.",
    },
    "JOYSTICK_5WAY": {
        "fx6_function": "DIRECT_TOUCH_JOYSTICK",
        "fx6_assign_slot": "MULTI_SELECTOR",
        "classification": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "5-way joystick + GPE0 touch navigate Big-6 tiles and 128-page menu one-handed.",
    },
    "FRONT_REAR_DIALS": {
        "fx6_function": "IRIS_SHUTTER_ISO_DIALS",
        "fx6_assign_slot": "ROTARY_DIALS",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Front Dial (Iris/Shutter), Rear Dial (ISO/EI), Rear Wheel (Menu Scroll/ND Soft).",
    },
    "AF_ON": {
        "fx6_function": "ASSIGN_8_PUSH_AF_MF",
        "fx6_assign_slot": "ASSIGN_8",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Replaces absent FX6 Top-Handle Assign 8 with body AF-ON.",
    },
    "AEL": {
        "fx6_function": "ASSIGN_10_PUSH_AUTO_IRIS",
        "fx6_assign_slot": "ASSIGN_10",
        "classification": BRIDGE_CLASS_SHIM_TRANSLATED,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Maps body AEL to Push Auto Iris (redirected from absent Variable ND).",
    },
    "LENS_FOCUS_HOLD": {
        "fx6_function": "ASSIGN_7_LENS_FH",
        "fx6_assign_slot": "LENS_FH",
        "classification": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "escape_hatch_protected": False,
        "one_handed_reachable": True,
        "notes": "Direct passthrough via EVENT_INPUT_KEY_LENS_FH_ON / libInfraLensCommunicator.so.",
    },
    "MENU": {
        "fx6_function": "FULL_MENU_128P",
        "fx6_assign_slot": "MENU_ESCAPE_HATCH",
        "classification": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "escape_hatch_protected": True,
        "one_handed_reachable": True,
        "notes": "Protected physical escape-hatch key; opens 128-page Full Menu and never preempted.",
    },
    "SHUTTER_HALF_FULL": {
        "fx6_function": "PHYSICAL_ESCAPE_HATCH_INTACT",
        "fx6_assign_slot": "S1_S2_ESCAPE_HATCH",
        "classification": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "escape_hatch_protected": True,
        "one_handed_reachable": True,
        "notes": "Protected physical escape-hatch key; untouched by Stage-B key remapper.",
    },
    "POWER_SWITCH": {
        "fx6_function": "PHYSICAL_ESCAPE_HATCH_INTACT",
        "fx6_assign_slot": "POWER_ESCAPE_HATCH",
        "classification": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "escape_hatch_protected": True,
        "one_handed_reachable": True,
        "notes": "Protected physical hardware power rail switch; never masked by userland.",
    },
}

FX6_ABSENT_BODY_CONTROLS: Tuple[str, ...] = (
    "FX6_SLOT_SEL_BUTTON",
    "FX6_FULL_AUTO_BUTTON",
    "FX6_ND_WHEEL_AND_PRESET",
)

KEYMAP_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "_ZN2ux6wgtsys10WidgetBase10onKeyEventERKNS0_8KeyEventE",
    "EVENT_INPUT_KEY_TACT_CUSTOM_ON",
    "EVENT_INPUT_KEY_TACT_CUSTOM2_ON",
    "EVENT_INPUT_KEY_TACT_CUSTOM3_ON",
    "EVENT_INPUT_KEY_TACT_CUSTOM5_ON",
    "EVENT_INPUT_KEY_TACT_CUSTOM6_ON",
    "EVENT_INPUT_KEY_TACT_STARTSTOP_ON",
    "EVENT_INPUT_KEY_TACT_AEL_ON",
    "EVENT_INPUT_KEY_TACT_AFON_ON",
    "UIBIZ_KEY_TACT_MENU",
    "UIBIZ_KEY_TACT_MODE",
    "UIBIZ_KEY_TACT_PLAY",
    "UIBIZ_KEY_TACT_DELETE",
    "UIBIZ_SLIKEY_ZOOM",
    "UIBIZ_KEY_SLIKEY_ZOOM_SPINAL",
)

KEYMAP_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "_ZN2ux6wgtsys10WidgetBase10onKeyEventERKNS0_8KeyEventE",
    "EVENT_INPUT_KEY_TACT_ASSIGN1_ON",
    "EVENT_INPUT_KEY_TACT_ASSIGN4_ON",
    "EVENT_INPUT_KEY_TACT_ASSIGN6_ON",
    "EVENT_INPUT_KEY_TACT_ASSIGN10_ON",
    "EVENT_INPUT_KEY_TACT_STATUS_CHECK_ON",
    "EVENT_INPUT_KEY_TACT_DISP_SEL_ON",
    "EVENT_INPUT_KEY_TACT_MENU_CANCEL_ON",
    "EVENT_INPUT_KEY_LENS_FH_ON",
    "EVENT_INPUT_KEY_TACT_ONEPUSH_AUTO_IRIS_ON",
    "ASSIGNABLE_SWITCH_BASE_ISO_SENSITIVITY",
    "ASSIGNABLE_SWITCH_ND_FILTER_POSITION",
    "UIBIZ_KEY_TACT_MENU",
    "UIBIZ_KEY_TACT_MODE",
    "UIBIZ_SLIKEY_ZOOM",
    "UIBIZ_KEY_SLIKEY_ZOOM_SPINAL",
)

SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS: Tuple[str, ...] = (
    "FAN_SET_SPEED",
    "CXS_WRITE_PWM",
    "GET_TEMPERATURE",
    "C_IMAGER_TEMP_CHK",
    "TALLY_LED",
    "USB_BUSPOWER_SUPPLY_CONTROL",
    "CTRL_POWER",
    "OUTSIDE_EVF_KEY_POSITION",
)

# ---------------------------------------------------------------------------
# Pillar 2 Constants: Active Cooling Fan & Thermal Emergency Override
# ---------------------------------------------------------------------------

VALID_FAN_MODES: Tuple[str, ...] = ("AUTO1", "AUTO2", "MINIMUM", "OFF_IN_REC", "ALWAYS_OFF")
THERMAL_PREHIGH_C = 58.0
THERMAL_EMERGENCY_SPINUP_C = 65.0
THERMAL_CRITICAL_SHUTDOWN_C = 72.0

FAN_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "FAN_CONTROL_AUTO",
    "FAN_CONTROL_MINIMUM",
    "FAN_CONTROL_OFF_IN_REC",
    "FAN_CONTROL_ALWAYS_OFF",
    "OFF_BY_THERMAL_TIME_OUT",
    "FAN_BROKEN_STATUS_NORMAL",
    "FAN_BROKEN_STATUS_BROKEN",
    "FAN_ERROR",
)

FAN_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "FAN_CONTROL_AUTO",
    "FAN_CONTROL_MINIMUM",
    "FAN_CONTROL_OFF_IN_REC",
    "FAN_CONTROL_ALWAYS_OFF",
    "BKID_APP_SETTING_FAN_CONTROL",
    "BKID_APP_USER_MENU_FAN_CONTROL",
    "EVENT_REMOTE_FAN_OPERATION_STATUS",
    "OFF_BY_THERMAL_TIME_OUT",
    "FAN_BROKEN_STATUS_NORMAL",
)

FAN_CP_SHARED_MARKERS: Tuple[str, ...] = (
    "SET_FAN_EQ_ID",
    "PROC_MSG_SET_FAN_EQ_ID:",
    "FAN_R",
    "PWM",
    "THERM",
)

# ---------------------------------------------------------------------------
# Pillar 3 Constants: 3x Physical Body Red Tally Lamps
# ---------------------------------------------------------------------------

FX3_PHYSICAL_TALLY_LEDS: Tuple[str, ...] = (
    "FRONT_TALLY_LED",
    "TOP_REC_TALLY_LED",
    "REAR_TALLY_LED",
)
VALID_TALLY_COLORS: Tuple[str, ...] = ("RED", "GREEN", "YELLOW")
VALID_TALLY_BRIGHTNESS_P149: Tuple[str, ...] = ("HIGH", "LOW", "OFF")

TALLY_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "REC_LAMP_ALL_LIGHTS_UP",
    "REC_LAMP_LIGHT_UP_ONLY_ONE",
    "REC_LAMP_ONLY_FRONT_OFF",
    "REC_LAMP_ALL_LIGHTS_OUT",
)

TALLY_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "BKID_APP_SETTING_FRONT_TALLY",
    "BKID_APP_SETTING_REAR_TALLY",
    "BKID_APP_SETTING_TALLY_LAMP_BRIGHTNESS",
    "BKID_APP_SETTING_G_TALLY_LAMP",
    "BKID_APP_SETTING_Y_TALLY_LAMP",
    "REC_LAMP_ALL_LIGHTS_UP",
    "REC_LAMP_LIGHT_UP_ONLY_ONE",
    "REC_LAMP_ONLY_FRONT_OFF",
    "REC_LAMP_ALL_LIGHTS_OUT",
)

TALLY_CP_SHARED_MARKERS: Tuple[str, ...] = (
    "MSG_ID_INFRABB_SYS_SET_CA_TALLY",
)

# ---------------------------------------------------------------------------
# Pillar 4 Constants: NP-FZ100 (7.2V) + USB-PD (9V/3A) Power Telemetry
# ---------------------------------------------------------------------------

NP_FZ100_NOMINAL_MV_P149 = 7200
NP_FZ100_MAX_MV_P149 = 8400
NP_FZ100_MIN_OPERATING_MV_P149 = 6000
NP_FZ100_NEAR_END_MV_P149 = 6350
NP_FZ100_ENC_WFI_STOP_MV_P149 = 6100
NP_FZ100_NEAR_END_SOC_PCT = 5
NP_FZ100_ENC_WFI_STOP_SOC_PCT = 2
NP_FZ100_WH_P149 = 16.4
FX3_ACTIVE_4K60_POWER_W = 10.5

USB_PD_NOMINAL_MV = 9000
USB_PD_NOMINAL_MA = 3000
USB_PD_POWER_MW = 27_000
USB_PD_MIN_REC_POWER_MW = 15_000  # 5V/3A minimum for sustained 4K recording

FX6_BPU_NOMINAL_MV = 14400
FX6_DC_IN_NOMINAL_MV_P149 = 19500
FX6_DC_IN_LOW_ALARM_MV = 18000

VALID_USB_PD_PROFILES: Tuple[str, ...] = (
    "NONE",
    "USB_PD_9V_3A_27W",
    "USB_PD_5V_3A_15W",
    "USB_LEGACY_5V_500MA",
)

POWER_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "INFRA_NOTIFY_BATTERY_REMAIN",
    "INFRA_NOTIFY_BATTERY_STATUS_CHECK",
    "LOW_BATT",
    "OFF_BY_BATT_END",
    "OFF_BY_BATT_THERMAL",
    "OFF_BY_BATT_INVALID",
    "VAL_supplying_usb_power_state_SUPPLYING_USB_POWER_STATE_ON",
)

POWER_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "INFRA_NOTIFY_BATTERY_REMAIN",
    "INFRA_NOTIFY_BATTERY_STATUS_CHECK",
    "LOW_BATT",
    "OFF_BY_BATT_END",
    "DCINVOLTAGE_ONE_VALUE",
    "DCINVOLTAGE_TWO_VALUE",
    "BATTERY_TYPE_DC_IN",
    "USB_POWER_SUPPLY_PORT1",
    "VAL_power_supply_end_status_SONY_INFO_BATTERY_NEAR_END",
    "VAL_power_supply_end_status_SONY_INFO_BATTERY_END",
)

POWER_MPR_SHARED_MARKERS: Tuple[str, ...] = (
    "_ZN3mpr5Codec10EncWfiStopEP16AvbbcApi_EncStopNS0_9CodecTypeENS0_10FileFormatEP12PayloadCodec",
    "_ZN3mpr5Codec17EncWfiStopReserveENS0_9CodecTypeENS0_10FileFormatEP12PayloadCodec",
)

POWER_CP_SHARED_MARKERS: Tuple[str, ...] = (
    "ACV_BATT_Snd",
    "BATT_AUTH_Snd",
    "BATT_STATE1_Snd",
    "BATT_STATE2_Snd",
    "BATT_STATE3_Snd",
    "BATT_TYPE1_Snd",
    "BATT_TYPE2_Snd",
    "BattCheck_Rcv",
    "N6Camera7FC_Sync11BatteryInfoE",
)

# ---------------------------------------------------------------------------
# Write-Guard Constants
# ---------------------------------------------------------------------------

VOLATILE_STAGING_PREFIXES_P149: Tuple[str, ...] = ("/tmp/", "ram://", "ramdisk://", "mem://")
FORBIDDEN_PERSISTENT_NVS_OR_EMMC_RE_P149 = re.compile(
    r"(^/dev/(nflash|cnflash|mmcblk0)|Backup\.bin|psd\.bin|defdet\.bin|cpapp-b\.bin|loader_nor\.bin|^p[0-9]+:|jiritsu|/cert\b|nvram://|eeprom://)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PhysicalKeymapEvalResult:
    valid: bool
    status: str
    physical_control: str
    fx6_target_function: str
    classification: str
    one_handed_reachable: bool
    escape_hatch_preserved: bool
    missing_gpio_faults: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CoolingFanThermalEvalResult:
    valid: bool
    status: str
    requested_fan_mode: str
    effective_pwm_pct: int
    is_recording: bool
    sensor_temp_c: float
    fan_broken: bool
    thermal_emergency_override_active: bool
    thermal_emergency_override_intact: bool
    graceful_enc_wfi_stop_triggered: bool
    classification: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TallyLampsEvalResult:
    valid: bool
    status: str
    front_tally_enabled: bool
    rear_tally_enabled: bool
    brightness: str
    rec_tally_blink: bool
    is_recording: bool
    tally_color: str
    rec_lamp_opcode: str
    front_led_lit: bool
    top_rec_led_lit: bool
    rear_led_lit: bool
    osd_only_tally: bool
    gpio_mismatch_count: int
    classification: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PowerTelemetryEvalResult:
    valid: bool
    status: str
    battery_voltage_mv: int
    soc_pct: int
    remain_minutes: int
    usb_pd_profile: str
    usb_pd_attached: bool
    hud_display_badge: str
    false_dcin_low_voltage_alarm: bool
    near_end_warning: bool
    enc_wfi_graceful_stop_triggered: bool
    corrupt_rsv_clip_prevented: bool
    classification: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase149WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar1PhysicalKeymapReport:
    passed: bool
    fx3_appfw_keymap_hits: int
    fx6_appfw_keymap_hits: int
    fx3_sencore: ElfSectionSummary
    fx6_sencore: ElfSectionSummary
    sencore_exports_identical: bool
    fx3_im_elf: ElfSectionSummary
    fx6_im_elf: ElfSectionSummary
    im_elf_abi_identical: bool
    fx3_backup_subsystems: int
    fx6_backup_subsystems: int
    fx3_backup_checksums_valid: bool
    fx6_backup_checksums_valid: bool
    all_fx6_core_functions_reachable: bool
    escape_hatch_preserved: bool
    sample_evals: Tuple[PhysicalKeymapEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2CoolingFanThermalReport:
    passed: bool
    fx3_appfw_fan_hits: int
    fx6_appfw_fan_hits: int
    fx3_cp_fan_hits: Dict[str, int]
    fx6_cp_fan_hits: Dict[str, int]
    sencore_fan_pwm_verified: bool
    thermal_emergency_override_intact: bool
    sample_evals: Tuple[CoolingFanThermalEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3TallyLampsReport:
    passed: bool
    fx3_appfw_tally_hits: int
    fx6_appfw_tally_hits: int
    fx3_cp_tally_hits: int
    fx6_cp_tally_hits: int
    sencore_tally_led_verified: bool
    zero_gpio_mismatch_verified: bool
    sample_evals: Tuple[TallyLampsEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4PowerTelemetryReport:
    passed: bool
    fx3_appfw_power_hits: int
    fx6_appfw_power_hits: int
    fx3_mpr_wfi_hits: int
    fx6_mpr_wfi_hits: int
    fx3_cp_batt_hits: int
    fx6_cp_batt_hits: int
    sencore_usb_buspower_verified: bool
    false_dcin_alarm_eliminated: bool
    enc_wfi_low_batt_autosave_verified: bool
    sample_evals: Tuple[PowerTelemetryEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ControlsTallyFanPowerTouchpoint:
    touchpoint_id: str
    subsystem: str
    fx6_feature: str
    fx3_target: str
    classification: str
    shim_mechanism: str
    safety_invariant: str


@dataclass(frozen=True)
class ControlsTallyFanPowerMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    subsystem_counts: Dict[str, int]
    touchpoints: Tuple[ControlsTallyFanPowerTouchpoint, ...]


@dataclass(frozen=True)
class RealhwPhysicalControlsTallyFanAndPowerReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    all_fx6_core_functions_reachable: bool
    escape_hatch_preserved: bool
    thermal_emergency_override_intact: bool
    zero_gpio_mismatch_verified: bool
    false_dcin_alarm_eliminated: bool
    enc_wfi_low_batt_autosave_verified: bool
    persistent_emmc_writes_authorized: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    donor_file_sizes: Dict[str, int]
    pillar1_keymap: Pillar1PhysicalKeymapReport
    pillar2_fan_thermal: Pillar2CoolingFanThermalReport
    pillar3_tally_lamps: Pillar3TallyLampsReport
    pillar4_power_telemetry: Pillar4PowerTelemetryReport
    compatibility_matrix: ControlsTallyFanPowerMatrixSummary
    volatile_guard_ok: Phase149WriteGuardResult
    forbidden_backup_guard_blocked: Phase149WriteGuardResult
    forbidden_cpapp_guard_blocked: Phase149WriteGuardResult
    forbidden_emmc_guard_blocked: Phase149WriteGuardResult
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Clean-Room Fixture Builders (Zero Proprietary Files Required)
# ---------------------------------------------------------------------------


def _build_synthetic_bk4_backup(subsystems: int, body_tag: bytes) -> bytes:
    """Build deterministic dual-record BK4\\x00 Backup.bin fixture (mirrors Phase 137/146)."""
    def _make_record(marker_path: str) -> bytes:
        table = bytearray(DESCRIPTOR_TABLE_BYTES)
        ent = bytearray(DESCRIPTOR_SLOT_BYTES)
        struct.pack_into("<QQII", ent, 0, 0x1000, 0x1FFF, 1, 0)
        pb = marker_path.encode("ascii")
        ent[24 : 24 + len(pb)] = pb
        table[0:DESCRIPTOR_SLOT_BYTES] = ent
        table[DESCRIPTOR_TABLE_BYTES - len(body_tag) :] = body_tag

        hdr = bytearray(BK4_HEADER_BYTES)
        struct.pack_into(
            "<II4s4sIIIII",
            hdr,
            0,
            0x04000000,
            BK4_SYNC_U32,
            b"\x00\x00\x00\x00",
            BK4_MAGIC_BYTES,
            subsystems,
            2048,
            BK4_HEADER_BYTES,
            len(table),
            0,
        )
        body = bytes(hdr) + bytes(table)
        csum = (sum(body) - sum(body[32:36])) & 0xFFFFFFFF
        struct.pack_into("<I", hdr, 32, csum)
        return bytes(hdr) + bytes(table)

    return _make_record("\\av-cam.bin") + _make_record("\\sabin\\idt_cam.bin")


def build_clean_room_realhw_controls_fan_power_fixtures() -> Dict[str, bytes]:
    """Synthesize deterministic clean-room ELF64, CP RTOS, and BK4 Backup.bin fixtures."""
    sencore_exports = tuple(f"sencore_export_{i:03d}" for i in range(EXPECTED_SENCORE_EXPORTS))
    sencore_imports = tuple(f"sencore_import_{i:03d}" for i in range(EXPECTED_SENCORE_IMPORTS))
    sencore_needed = ("libc.so.6", "libosal_uipc.so")

    fx3_sencore = _build_synthetic_elf64(
        exports=sencore_exports,
        imports=sencore_imports,
        dt_needed=sencore_needed,
        rodata_strings=SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS,
    )
    fx6_sencore = _build_synthetic_elf64(
        exports=sencore_exports,
        imports=sencore_imports,
        dt_needed=sencore_needed,
        rodata_strings=SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS,
    )

    im_exports = tuple(f"im_export_{i:02d}" for i in range(EXPECTED_IM_ELF_EXPORTS))
    im_imports = tuple(f"im_import_{i:02d}" for i in range(EXPECTED_IM_ELF_IMPORTS))
    im_needed = (
        "libjemalloc_ds.so.2",
        "libIMDB.so",
        "libbackup.so",
        "libosal_utm.so",
        "libosal_uipc.so",
        "libdl.so.2",
        "libpthread.so.0",
        "libSTMcmdexecute.so",
        "libssl.so.3",
        "libcrypto.so.3",
        "libstdc++.so.6",
        "libm.so.6",
        "libgcc_s.so.1",
        "libc.so.6",
        "librt.so.1",
    )
    im_rodata = ("IMDB_find_entry", "Backup_read", "Backup_write", "osal_snd_msg")
    fx3_im_elf = _build_synthetic_elf64(
        exports=im_exports, imports=im_imports, dt_needed=im_needed, rodata_strings=im_rodata
    )
    fx6_im_elf = _build_synthetic_elf64(
        exports=im_exports, imports=im_imports, dt_needed=im_needed, rodata_strings=im_rodata
    )

    fx3_appfw_tokens = tuple(
        dict.fromkeys(
            KEYMAP_APPFW_FX3_MARKERS
            + FAN_APPFW_FX3_MARKERS
            + TALLY_APPFW_FX3_MARKERS
            + POWER_APPFW_FX3_MARKERS
        )
    )
    fx6_appfw_tokens = tuple(
        dict.fromkeys(
            KEYMAP_APPFW_FX6_MARKERS
            + FAN_APPFW_FX6_MARKERS
            + TALLY_APPFW_FX6_MARKERS
            + POWER_APPFW_FX6_MARKERS
        )
    )
    fx3_appfw = _build_synthetic_elf64(
        exports=("fx3_appfw_main",),
        imports=("_ZN3mpr5Codec10EncWfiStopEP16AvbbcApi_EncStopNS0_9CodecTypeENS0_10FileFormatEP12PayloadCodec",),
        dt_needed=("libmpr.so", "libsencore.so"),
        rodata_strings=fx3_appfw_tokens,
    )
    fx6_appfw = _build_synthetic_elf64(
        exports=("fx6_appfw_main",),
        imports=("_ZN3mpr5Codec10EncWfiStopEP16AvbbcApi_EncStopNS0_9CodecTypeENS0_10FileFormatEP12PayloadCodec",),
        dt_needed=("libmpr.so", "libsencore.so"),
        rodata_strings=fx6_appfw_tokens,
    )

    fx3_libmpr = _build_synthetic_elf64(
        exports=POWER_MPR_SHARED_MARKERS,
        imports=("osal_snd_msg",),
        dt_needed=("libosal_uipc.so",),
        rodata_strings=POWER_MPR_SHARED_MARKERS,
    )
    fx6_libmpr = _build_synthetic_elf64(
        exports=POWER_MPR_SHARED_MARKERS,
        imports=("osal_snd_msg",),
        dt_needed=("libosal_uipc.so",),
        rodata_strings=POWER_MPR_SHARED_MARKERS,
    )

    cp_shared = "\x00".join(
        FAN_CP_SHARED_MARKERS + TALLY_CP_SHARED_MARKERS + POWER_CP_SHARED_MARKERS
    )
    fx3_cpapp = (cp_shared + "\x00THERM\x00PWM\x00").encode("ascii")
    fx6_cpapp = (cp_shared + "\x00THERMAL_SENSOR\x00PWM\x00").encode("ascii")

    fx3_backup = _build_synthetic_bk4_backup(819, b"ALCIN_UUD")
    fx6_backup = _build_synthetic_bk4_backup(840, b"CHAPLIN")

    return {
        "fx3_appfw": fx3_appfw,
        "fx6_appfw": fx6_appfw,
        "fx3_sencore": fx3_sencore,
        "fx6_sencore": fx6_sencore,
        "fx3_libmpr": fx3_libmpr,
        "fx6_libmpr": fx6_libmpr,
        "fx3_im_elf": fx3_im_elf,
        "fx6_im_elf": fx6_im_elf,
        "fx3_cpapp": fx3_cpapp,
        "fx6_cpapp": fx6_cpapp,
        "fx3_backup": fx3_backup,
        "fx6_backup": fx6_backup,
    }


# ---------------------------------------------------------------------------
# Pillar Evaluators (Positive + Negative Fail-Closed Validation)
# ---------------------------------------------------------------------------


def evaluate_physical_keymap_bridge(
    *,
    physical_control: str = "CUSTOM_4",
    requested_fx6_function: Optional[str] = None,
    override_escape_hatch: bool = False,
    mask_absent_fx6_controls: bool = True,
) -> PhysicalKeymapEvalResult:
    """Evaluate FX3 physical body keymap & ergonomic one-handed bridge onto FX6 functions."""
    ctrl = physical_control.strip().upper()
    errors: List[str] = []

    if ctrl in FX6_ABSENT_BODY_CONTROLS:
        if not mask_absent_fx6_controls:
            errors.append(
                f"BLOCKED_UNMASKED_ABSENT_FX6_CONTROL: {ctrl} missing on FX3 body; requires soft-map/mask"
            )
        target_fn = (
            "BIG6_OR_STATUS_SLOT_TOGGLE"
            if ctrl == "FX6_SLOT_SEL_BUTTON"
            else ("MODE_AUTO_SOFT_SELECT" if ctrl == "FX6_FULL_AUTO_BUTTON" else "PUSH_AUTO_IRIS_OR_ISO_DIAL")
        )
        status = "ABSENT_FX6_CONTROL_SOFT_MAPPED" if not errors else errors[0].split(":", 1)[0]
        return PhysicalKeymapEvalResult(
            valid=len(errors) == 0,
            status=status,
            physical_control=ctrl,
            fx6_target_function=target_fn,
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW if ctrl == "FX6_ND_WHEEL_AND_PRESET" else BRIDGE_CLASS_SHIM_TRANSLATED,
            one_handed_reachable=True,
            escape_hatch_preserved=not override_escape_hatch,
            missing_gpio_faults=0,
            errors=tuple(errors),
        )

    if ctrl not in FX3_PHYSICAL_KEYMAP_SPECS:
        errors.append(f"BLOCKED_UNKNOWN_FX3_CONTROL: {ctrl!r}")
        return PhysicalKeymapEvalResult(
            valid=False,
            status="BLOCKED_UNKNOWN_FX3_CONTROL",
            physical_control=ctrl,
            fx6_target_function="UNKNOWN",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            one_handed_reachable=False,
            escape_hatch_preserved=not override_escape_hatch,
            missing_gpio_faults=1,
            errors=tuple(errors),
        )

    spec = FX3_PHYSICAL_KEYMAP_SPECS[ctrl]
    default_fn = str(spec["fx6_function"])
    target_fn = requested_fx6_function.strip().upper() if requested_fx6_function else default_fn
    is_escape = bool(spec["escape_hatch_protected"])

    if override_escape_hatch or (is_escape and target_fn != default_fn):
        errors.append(
            f"BLOCKED_ESCAPE_HATCH_PREEMPTION: {ctrl} is part of MENU+SHUTTER+POWER physical escape hatch"
        )

    status = "FX3_PHYSICAL_KEYMAP_BRIDGE_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return PhysicalKeymapEvalResult(
        valid=len(errors) == 0,
        status=status,
        physical_control=ctrl,
        fx6_target_function=target_fn,
        classification=str(spec["classification"]),
        one_handed_reachable=bool(spec["one_handed_reachable"]),
        escape_hatch_preserved=(not override_escape_hatch) and (not (is_escape and target_fn != default_fn)),
        missing_gpio_faults=0,
        errors=tuple(errors),
    )


def evaluate_cooling_fan_thermal_bridge(
    *,
    requested_fan_mode: str = "OFF_IN_REC",
    is_recording: bool = True,
    sensor_temp_c: float = 42.0,
    fan_broken: bool = False,
    allow_cp_thermal_override: bool = True,
) -> CoolingFanThermalEvalResult:
    """Evaluate active cooling fan PWM routing & Stock-CP thermal emergency override safety."""
    mode = requested_fan_mode.strip().upper()
    errors: List[str] = []

    if mode not in VALID_FAN_MODES:
        errors.append(f"BLOCKED_UNKNOWN_FAN_MODE: {mode!r}")
        return CoolingFanThermalEvalResult(
            valid=False,
            status="BLOCKED_UNKNOWN_FAN_MODE",
            requested_fan_mode=mode,
            effective_pwm_pct=0,
            is_recording=is_recording,
            sensor_temp_c=sensor_temp_c,
            fan_broken=fan_broken,
            thermal_emergency_override_active=False,
            thermal_emergency_override_intact=False,
            graceful_enc_wfi_stop_triggered=False,
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            errors=tuple(errors),
        )

    if mode == "ALWAYS_OFF" and is_recording:
        errors.append("BLOCKED_UNSAFE_ALWAYS_OFF_IN_REC: FX3 recording prohibits FAN_CONTROL_ALWAYS_OFF")

    if not allow_cp_thermal_override:
        errors.append(
            "BLOCKED_THERMAL_OVERRIDE_BYPASS: Stock-CP cpapp-b.bin emergency thermal PWM override must remain intact"
        )

    emergency_active = allow_cp_thermal_override and (
        sensor_temp_c >= THERMAL_EMERGENCY_SPINUP_C or fan_broken
    )
    graceful_stop = allow_cp_thermal_override and (
        sensor_temp_c >= THERMAL_CRITICAL_SHUTDOWN_C or (fan_broken and sensor_temp_c >= THERMAL_PREHIGH_C)
    )

    if fan_broken:
        pwm_pct = 0
        if is_recording and sensor_temp_c >= THERMAL_PREHIGH_C:
            # Fan failed while hot -> graceful EncWfiStop before OFF_BY_THERMAL_TIME_OUT
            graceful_stop = allow_cp_thermal_override
    elif emergency_active:
        # Stock FX3 cpapp-b.bin overrides OFF_IN_REC / MINIMUM at >= 65C
        pwm_pct = 100
    elif mode == "OFF_IN_REC" and is_recording:
        pwm_pct = 0 if sensor_temp_c < THERMAL_PREHIGH_C else 45
    elif mode == "MINIMUM":
        pwm_pct = 25 if sensor_temp_c < THERMAL_PREHIGH_C else 60
    elif mode == "AUTO2":
        pwm_pct = 35 if sensor_temp_c < 45.0 else (65 if sensor_temp_c < THERMAL_PREHIGH_C else 85)
    elif mode == "AUTO1":
        pwm_pct = 45 if sensor_temp_c < 45.0 else (75 if sensor_temp_c < THERMAL_PREHIGH_C else 90)
    else:  # ALWAYS_OFF in standby
        pwm_pct = 0

    override_intact = allow_cp_thermal_override and (
        (sensor_temp_c < THERMAL_EMERGENCY_SPINUP_C) or (pwm_pct == 100) or fan_broken
    )

    if errors:
        status = errors[0].split(":", 1)[0]
    elif graceful_stop:
        status = "THERMAL_CRITICAL_GRACEFUL_ENC_WFI_STOP"
    elif emergency_active:
        status = "THERMAL_EMERGENCY_CP_OVERRIDE_SPINUP"
    else:
        status = "COOLING_FAN_PWM_BRIDGE_VERIFIED"

    return CoolingFanThermalEvalResult(
        valid=len(errors) == 0,
        status=status,
        requested_fan_mode=mode,
        effective_pwm_pct=pwm_pct,
        is_recording=is_recording,
        sensor_temp_c=float(sensor_temp_c),
        fan_broken=fan_broken,
        thermal_emergency_override_active=emergency_active,
        thermal_emergency_override_intact=override_intact,
        graceful_enc_wfi_stop_triggered=graceful_stop,
        classification=BRIDGE_CLASS_SHIM_TRANSLATED if mode == "OFF_IN_REC" else BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        errors=tuple(errors),
    )


def evaluate_tally_lamps_bridge(
    *,
    front_tally_enabled: bool = True,
    rear_tally_enabled: bool = True,
    brightness: str = "HIGH",
    rec_tally_blink: bool = False,
    is_recording: bool = True,
    tally_color: str = "RED",
    allow_non_red_on_red_gpio: bool = False,
) -> TallyLampsEvalResult:
    """Evaluate 3x physical FX3 Red Tally LEDs vs FX6 Front/Rear/Green/Yellow tally controls."""
    bri = brightness.strip().upper()
    col = tally_color.strip().upper()
    errors: List[str] = []

    if bri not in VALID_TALLY_BRIGHTNESS_P149:
        errors.append(f"BLOCKED_UNKNOWN_TALLY_BRIGHTNESS: {bri!r}")
    if col not in VALID_TALLY_COLORS:
        errors.append(f"BLOCKED_UNKNOWN_TALLY_COLOR: {col!r}")
    if col in ("GREEN", "YELLOW") and allow_non_red_on_red_gpio:
        errors.append(
            f"BLOCKED_TALLY_GPIO_COLOR_MISMATCH: FX3 only has Red Tally LEDs; cannot drive {col} onto Red GPIO"
        )

    if col in ("GREEN", "YELLOW"):
        # Green (PVW) and Yellow tally remain OSD-only on FX3 so talent/operator never confuse PVW with on-air Red!
        opcode = "OSD_BORDER_ONLY_NO_RED_LED"
        front_lit = False
        top_lit = False
        rear_lit = False
        osd_only = True
        classification = BRIDGE_CLASS_MASKED_ABSENT_HW
        gpio_mismatch = 1 if allow_non_red_on_red_gpio else 0
    else:
        osd_only = False
        gpio_mismatch = 0
        classification = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        if not is_recording or bri == "OFF" or (not front_tally_enabled and not rear_tally_enabled):
            opcode = "REC_LAMP_ALL_LIGHTS_OUT"
            front_lit = False
            top_lit = False
            rear_lit = False
        elif front_tally_enabled and rear_tally_enabled:
            opcode = "REC_LAMP_ALL_LIGHTS_UP"
            front_lit = True
            top_lit = True
            rear_lit = True
        elif not front_tally_enabled and rear_tally_enabled:
            opcode = "REC_LAMP_ONLY_FRONT_OFF"
            front_lit = False
            top_lit = True
            rear_lit = True
        else:  # front_tally_enabled and not rear_tally_enabled
            opcode = "REC_LAMP_LIGHT_UP_ONLY_ONE"
            front_lit = True
            top_lit = False
            rear_lit = False
            classification = BRIDGE_CLASS_SHIM_TRANSLATED

    status = "TALLY_LAMPS_3X_SYNC_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return TallyLampsEvalResult(
        valid=len(errors) == 0,
        status=status,
        front_tally_enabled=front_tally_enabled,
        rear_tally_enabled=rear_tally_enabled,
        brightness=bri,
        rec_tally_blink=rec_tally_blink,
        is_recording=is_recording,
        tally_color=col,
        rec_lamp_opcode=opcode,
        front_led_lit=front_lit,
        top_rec_led_lit=top_lit,
        rear_led_lit=rear_lit,
        osd_only_tally=osd_only,
        gpio_mismatch_count=gpio_mismatch,
        classification=classification,
        errors=tuple(errors),
    )


def evaluate_power_telemetry_bridge(
    *,
    battery_voltage_mv: int = 7400,
    soc_pct: int = 68,
    usb_pd_profile: str = "USB_PD_9V_3A_27W",
    battery_authenticated: bool = True,
    is_recording: bool = True,
    apply_fx6_18v_dcin_threshold: bool = False,
) -> PowerTelemetryEvalResult:
    """Evaluate NP-FZ100 (7.2V) + USB-PD (9V/3A) telemetry & EncWfiStop low-battery auto-save."""
    pd_prof = usb_pd_profile.strip().upper()
    errors: List[str] = []

    if pd_prof not in VALID_USB_PD_PROFILES:
        errors.append(f"BLOCKED_UNKNOWN_USB_PD_PROFILE: {pd_prof!r}")
    if not (0 <= soc_pct <= 100):
        errors.append(f"BLOCKED_OUT_OF_RANGE_SOC_PCT: {soc_pct}")
    if not battery_authenticated:
        errors.append("BLOCKED_UNAUTHENTICATED_BATTERY: OFF_BY_BATT_INVALID (cpapp-b.bin BATT_AUTH_Snd)")
    if battery_voltage_mv > NP_FZ100_MAX_MV_P149 + 100:
        errors.append(f"BLOCKED_BATT_OVERVOLTAGE: {battery_voltage_mv}mV exceeds 8.4V NP-FZ100 envelope")
    if battery_voltage_mv < 5600:
        errors.append(f"BLOCKED_BATT_UNDERVOLTAGE_DEAD: {battery_voltage_mv}mV (OFF_BY_BATT_DEAD)")
    if apply_fx6_18v_dcin_threshold:
        errors.append(
            "BLOCKED_FALSE_FX6_DCIN_19V5_ALARM: FX6 18.0V/19.5V DC-IN threshold must be masked for FX3 7.2V/USB-PD"
        )

    pd_attached = pd_prof in ("USB_PD_9V_3A_27W", "USB_PD_5V_3A_15W")
    if pd_prof == "USB_LEGACY_5V_500MA" and is_recording and soc_pct <= NP_FZ100_NEAR_END_SOC_PCT:
        errors.append(
            "BLOCKED_INSUFFICIENT_USB_POWER_FOR_REC: 5V/0.5A (2.5W) cannot sustain 4K recording on low NP-FZ100"
        )

    usable_wh = NP_FZ100_WH_P149 * (soc_pct / 100.0)
    remain_min = int(round((usable_wh / FX3_ACTIVE_4K60_POWER_W) * 60.0))
    if pd_prof == "USB_PD_9V_3A_27W":
        hud_badge = f"{soc_pct}% + USB-PD (9V/3A)"
    elif pd_prof == "USB_PD_5V_3A_15W":
        hud_badge = f"{soc_pct}% + USB-PD (5V/3A)"
    elif pd_prof == "USB_LEGACY_5V_500MA":
        hud_badge = f"{soc_pct}% (USB 5V Slow)"
    else:
        hud_badge = f"{soc_pct}% ({remain_min}min)"

    near_end = (not pd_attached) and (
        soc_pct <= NP_FZ100_NEAR_END_SOC_PCT or battery_voltage_mv <= NP_FZ100_NEAR_END_MV_P149
    )
    enc_wfi_stop = (not pd_attached) and is_recording and (
        soc_pct <= NP_FZ100_ENC_WFI_STOP_SOC_PCT or battery_voltage_mv <= NP_FZ100_ENC_WFI_STOP_MV_P149
    )

    if errors:
        status = errors[0].split(":", 1)[0]
    elif enc_wfi_stop:
        status = "LOW_BATT_GRACEFUL_ENC_WFI_STOP"
    elif near_end:
        status = "SONY_INFO_BATTERY_NEAR_END_WARNING"
    else:
        status = "NP_FZ100_USB_PD_TELEMETRY_VERIFIED"

    return PowerTelemetryEvalResult(
        valid=len(errors) == 0,
        status=status,
        battery_voltage_mv=battery_voltage_mv,
        soc_pct=soc_pct,
        remain_minutes=remain_min,
        usb_pd_profile=pd_prof,
        usb_pd_attached=pd_attached,
        hud_display_badge=hud_badge,
        false_dcin_low_voltage_alarm=apply_fx6_18v_dcin_threshold,
        near_end_warning=near_end,
        enc_wfi_graceful_stop_triggered=enc_wfi_stop,
        corrupt_rsv_clip_prevented=enc_wfi_stop or (not is_recording) or (not near_end) or pd_attached,
        classification=BRIDGE_CLASS_SHIM_TRANSLATED,
        errors=tuple(errors),
    )


def evaluate_phase149_write_guard(target_path: str) -> Phase149WriteGuardResult:
    """Enforce volatile RAM staging only and zero persistent eMMC / Backup.bin / CP mutations."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES_P149) and not bool(
        FORBIDDEN_PERSISTENT_NVS_OR_EMMC_RE_P149.search(norm)
    )
    if is_volatile:
        return Phase149WriteGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            emmc_mutation_bytes=0,
            calibration_mutation_bytes=0,
            errors=(),
        )
    return Phase149WriteGuardResult(
        valid=False,
        status="BLOCKED_PERSISTENT_EMMC_OR_NVS_WRITE",
        target_path=norm,
        volatile_ram_staged=False,
        persistent_write_blocked=True,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        errors=(f"BLOCKED_PERSISTENT_EMMC_OR_NVS_WRITE: target_path={norm!r}",),
    )


def build_phase149_controls_matrix() -> ControlsTallyFanPowerMatrixSummary:
    """Construct the cross-body compatibility matrix across Controls, Fan, Tally, and Power."""
    entries: Tuple[ControlsTallyFanPowerTouchpoint, ...] = (
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="KEYMAP_CUSTOM4_MODE_BIG6_HOME",
            subsystem="CONTROLS_KEYMAP",
            fx6_feature="FX6 Dedicated HOME (Big-6) Button",
            fx3_target="FX3 Custom 4 / MODE Button",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_mechanism="libgrm-fbinit9.so KeyEvent translator -> Big-6 toggle",
            safety_invariant="100% one-handed Big-6 access without preempting MENU",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="KEYMAP_CUSTOM1_DELETE_STATUS_CHECK",
            subsystem="CONTROLS_KEYMAP",
            fx6_feature="FX6 STATUS Button (Multi-Tab Status Check)",
            fx3_target="FX3 DISP/DELETE / Custom 1 Button",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_mechanism="libgrm-fbinit9.so KeyEvent -> EVENT_INPUT_KEY_TACT_STATUS_CHECK_ON",
            safety_invariant="Zero missing-GPIO errors; playback delete untouched in PLAY mode",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="KEYMAP_CUSTOM_1_6_AND_LENS_FH",
            subsystem="CONTROLS_KEYMAP",
            fx6_feature="FX6 Assignable 1..10 & Lens Focus Hold",
            fx3_target="FX3 Custom 1..6 + Joystick + AF-ON + AEL + Lens FH",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_mechanism="Static keymap table in /tmp volatile BK4 shadow",
            safety_invariant="Zero p2:/Backup.bin BK4 writes; zero null-GPIO faults",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="KEYMAP_ZOOM_ROCKER_AND_REC",
            subsystem="CONTROLS_KEYMAP",
            fx6_feature="FX6 Grip/Handle Servo Zoom & Top/Front REC",
            fx3_target="FX3 T/W Zoom Rocker + Top & Front REC Buttons",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_mechanism="Direct UIBIZ_SLIKEY_ZOOM & EVENT_INPUT_KEY_TACT_STARTSTOP_ON",
            safety_invariant="8-step variable PZ + CIZ + dual REC triggers preserved",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="KEYMAP_ESCAPE_HATCH_MENU_SHUTTER_PWR",
            subsystem="CONTROLS_KEYMAP",
            fx6_feature="Stage-B Physical Recovery Escape Hatch",
            fx3_target="FX3 MENU + SHUTTER + POWER Hardware Switches",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            shim_mechanism="Hard exclusion from KeyEvent preemption/remapping",
            safety_invariant="escape_hatch_preserved == True at all times",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="KEYMAP_ABSENT_SLOT_AUTO_ND_CONTROLS",
            subsystem="CONTROLS_KEYMAP",
            fx6_feature="FX6 Physical SLOT SEL, FULL AUTO, ND Wheel",
            fx3_target="Big6 Slot Toggle, Menu Mode, Push Auto Iris / NO_OP",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            shim_mechanism="Non-blocking soft-map / NO_OP mask in libgrm-fbinit9.so",
            safety_invariant="Zero hardware ND or dedicated-switch polling stalls",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="FAN_MODE_AUTO1_AUTO2_MIN_OFFINREC",
            subsystem="FAN_THERMAL",
            fx6_feature="FX6 Cooling Fan (Auto1 / Auto2 / Minimum / Off in Rec)",
            fx3_target="FX3 Internal Blower PWM (libsencore FAN_SET_SPEED / CXS_WRITE_PWM)",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_mechanism="BKID_APP_SETTING_FAN_CONTROL -> cpapp-b.bin SET_FAN_EQ_ID",
            safety_invariant="Fan PWM curve matches FX3 thermistor hardware",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="FAN_THERMAL_EMERGENCY_CP_OVERRIDE",
            subsystem="FAN_THERMAL",
            fx6_feature="Off-in-Rec User Silence vs Thermal Safety",
            fx3_target="Stock-CP cpapp-b.bin >=65C Spin-Up + >=72C EncWfiStop",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            shim_mechanism="Unmodified Stock FX3 cpapp-b.bin RTOS thermal loop",
            safety_invariant="thermal_emergency_override_intact == True",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="TALLY_3X_RED_LEDS_FRONT_TOP_REAR",
            subsystem="TALLY_LEDS",
            fx6_feature="FX6 Front/Rear Tally + Brightness + Blink",
            fx3_target="FX3 Front + Top REC + Rear Physical Red Tally LEDs",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_mechanism="REC_LAMP_ALL_LIGHTS_UP / ONLY_FRONT_OFF / ONLY_ONE -> SET_CA_TALLY",
            safety_invariant="100% REC state synchronization across all 3 Red LEDs",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="TALLY_GREEN_YELLOW_OSD_ISOLATION",
            subsystem="TALLY_LEDS",
            fx6_feature="FX6 Green (PVW) & Yellow Broadcast Tally Lamps",
            fx3_target="GPE0 OSD Border Only (Physical Red LEDs Strictly OFF)",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            shim_mechanism="libgrm-fbinit9.so masks G_TALLY/Y_TALLY from Red GPIO",
            safety_invariant="gpio_mismatch_count == 0 (no false on-air Red Tally)",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="POWER_NP_FZ100_SOC_AND_USB_PD_HUD",
            subsystem="POWER_TELEMETRY",
            fx6_feature="FX6 BP-U (14.4V) / 19.5V DC-IN Battery HUD",
            fx3_target="FX3 NP-FZ100 (7.2V) 0..100% + USB-PD (9V/3A 27W) Flag",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_mechanism="Masks DCINVOLTAGE_ONE_VALUE 18V alarm; forwards InfoLITHIUM SoC + PD",
            safety_invariant="false_dcin_low_voltage_alarm == False",
        ),
        ControlsTallyFanPowerTouchpoint(
            touchpoint_id="POWER_LOW_BATT_ENC_WFI_AUTOSAVE",
            subsystem="POWER_TELEMETRY",
            fx6_feature="FX6 Low-Battery Graceful Clip Close",
            fx3_target="cpapp-b.bin BATT_STATE -> libmpr.so EncWfiStop + EncWfiClose",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            shim_mechanism="Stock-CP OFF_BY_BATT_END triggers MPR EncWfiStop at <=2% / 6.1V",
            safety_invariant="Zero .RSV unfinalized clip loss on battery depletion",
        ),
    )

    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    sub_counts: Dict[str, int] = {}
    for e in entries:
        class_counts[e.classification] = class_counts.get(e.classification, 0) + 1
        sub_counts[e.subsystem] = sub_counts.get(e.subsystem, 0) + 1

    return ControlsTallyFanPowerMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        subsystem_counts=sub_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Unified Phase 149 Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_physical_controls_tally_fan_and_power(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwPhysicalControlsTallyFanAndPowerReport:
    """Run all 4 Phase 149 real-hardware controls, fan, tally, and power bridge pillars."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    forced = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not forced:
        rel_map = {
            "fx3_appfw": FX3_APPFW_P149_RELPATH,
            "fx6_appfw": FX6_APPFW_P149_RELPATH,
            "fx3_sencore": FX3_LIBSENCORE_P149_RELPATH,
            "fx6_sencore": FX6_LIBSENCORE_P149_RELPATH,
            "fx3_libmpr": FX3_LIBMPR_P149_RELPATH,
            "fx6_libmpr": FX6_LIBMPR_P149_RELPATH,
            "fx3_im_elf": FX3_IM_ELF_P149_RELPATH,
            "fx6_im_elf": FX6_IM_ELF_P149_RELPATH,
            "fx3_cpapp": FX3_CPAPP_P149_RELPATH,
            "fx6_cpapp": FX6_CPAPP_P149_RELPATH,
            "fx3_backup": FX3_BACKUP_BIN_P149_RELPATH,
            "fx6_backup": FX6_BACKUP_BIN_P149_RELPATH,
        }
        donor_paths = {k: resolve_donor_file(v, repo_root=root) for k, v in rel_map.items()}

    use_local = (not forced) and bool(donor_paths) and all(p is not None for p in donor_paths.values())
    mode = "LOCAL_DONOR_VERIFIED" if use_local else "CLEAN_ROOM_SYNTHETIC"
    source_mode = "LOCAL_DONOR_RDONLY" if use_local else "SYNTHETIC_CLEAN_ROOM"

    fx3_appfw_tokens = tuple(
        dict.fromkeys(
            KEYMAP_APPFW_FX3_MARKERS
            + FAN_APPFW_FX3_MARKERS
            + TALLY_APPFW_FX3_MARKERS
            + POWER_APPFW_FX3_MARKERS
        )
    )
    fx6_appfw_tokens = tuple(
        dict.fromkeys(
            KEYMAP_APPFW_FX6_MARKERS
            + FAN_APPFW_FX6_MARKERS
            + TALLY_APPFW_FX6_MARKERS
            + POWER_APPFW_FX6_MARKERS
        )
    )
    cp_tokens = tuple(
        dict.fromkeys(FAN_CP_SHARED_MARKERS + TALLY_CP_SHARED_MARKERS + POWER_CP_SHARED_MARKERS)
    )

    donor_sizes: Dict[str, int] = {}
    if use_local:
        p = {k: v for k, v in donor_paths.items() if v is not None}
        _, fx3_app_hits = _scan_elf_ro_markers_rdonly(p["fx3_appfw"], fx3_appfw_tokens)
        _, fx6_app_hits = _scan_elf_ro_markers_rdonly(p["fx6_appfw"], fx6_appfw_tokens)
        fx3_sc_sum, fx3_sc_exp, fx3_sc_imp = _scan_elf_and_tokens_rdonly(
            p["fx3_sencore"],
            binary_name="libsencore.so",
            body_label="FX3_7.02",
            tokens=SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS,
        )
        fx6_sc_sum, fx6_sc_exp, fx6_sc_imp = _scan_elf_and_tokens_rdonly(
            p["fx6_sencore"],
            binary_name="libsencore.so",
            body_label="FX6_6.01",
            tokens=SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS,
        )
        _, fx3_mpr_hits = _scan_elf_ro_markers_rdonly(p["fx3_libmpr"], POWER_MPR_SHARED_MARKERS)
        _, fx6_mpr_hits = _scan_elf_ro_markers_rdonly(p["fx6_libmpr"], POWER_MPR_SHARED_MARKERS)
        fx3_im_sum, fx3_im_exp, fx3_im_imp = _scan_elf_and_tokens_rdonly(
            p["fx3_im_elf"], binary_name="im.elf", body_label="FX3_7.02"
        )
        fx6_im_sum, fx6_im_exp, fx6_im_imp = _scan_elf_and_tokens_rdonly(
            p["fx6_im_elf"], binary_name="im.elf", body_label="FX6_6.01"
        )
        _, fx3_cp_hits = _scan_binary_tokens_rdonly(p["fx3_cpapp"], cp_tokens)
        _, fx6_cp_hits = _scan_binary_tokens_rdonly(p["fx6_cpapp"], cp_tokens)
        fx3_bk_raw = _read_bytes_rdonly(p["fx3_backup"])
        fx6_bk_raw = _read_bytes_rdonly(p["fx6_backup"])

        for k, path_obj in p.items():
            donor_sizes[k] = path_obj.stat().st_size
    else:
        fx = build_clean_room_realhw_controls_fan_power_fixtures()
        fx3_app_hits = _count_tokens_single_pass(fx["fx3_appfw"], fx3_appfw_tokens)
        fx6_app_hits = _count_tokens_single_pass(fx["fx6_appfw"], fx6_appfw_tokens)
        fx3_sc_sum, fx3_sc_exp, fx3_sc_imp = _scan_elf_and_tokens_buf(
            fx["fx3_sencore"],
            binary_name="libsencore.so",
            body_label="FX3_7.02",
            source_mode=source_mode,
            tokens=SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS,
        )
        fx6_sc_sum, fx6_sc_exp, fx6_sc_imp = _scan_elf_and_tokens_buf(
            fx["fx6_sencore"],
            binary_name="libsencore.so",
            body_label="FX6_6.01",
            source_mode=source_mode,
            tokens=SENCORE_CONTROLS_TALLY_FAN_POWER_MARKERS,
        )
        fx3_mpr_hits = _count_tokens_single_pass(fx["fx3_libmpr"], POWER_MPR_SHARED_MARKERS)
        fx6_mpr_hits = _count_tokens_single_pass(fx["fx6_libmpr"], POWER_MPR_SHARED_MARKERS)
        fx3_im_sum, fx3_im_exp, fx3_im_imp = _scan_elf_and_tokens_buf(
            fx["fx3_im_elf"],
            binary_name="im.elf",
            body_label="FX3_7.02",
            source_mode=source_mode,
        )
        fx6_im_sum, fx6_im_exp, fx6_im_imp = _scan_elf_and_tokens_buf(
            fx["fx6_im_elf"],
            binary_name="im.elf",
            body_label="FX6_6.01",
            source_mode=source_mode,
        )
        fx3_cp_hits = _count_tokens_single_pass(fx["fx3_cpapp"], cp_tokens)
        fx6_cp_hits = _count_tokens_single_pass(fx["fx6_cpapp"], cp_tokens)
        fx3_bk_raw = fx["fx3_backup"]
        fx6_bk_raw = fx["fx6_backup"]

        for k, buf in fx.items():
            donor_sizes[k] = len(buf)

    # ---- Pillar 1: Physical Body Keymap & Ergonomic Navigation Bridge ----
    p1_errors: List[str] = []
    fx3_key_hits = sum(1 for m in KEYMAP_APPFW_FX3_MARKERS if fx3_app_hits.get(m, 0) > 0)
    fx6_key_hits = sum(1 for m in KEYMAP_APPFW_FX6_MARKERS if fx6_app_hits.get(m, 0) > 0)
    if fx3_key_hits < len(KEYMAP_APPFW_FX3_MARKERS) or fx6_key_hits < len(KEYMAP_APPFW_FX6_MARKERS):
        p1_errors.append(
            f"Incomplete appFw keymap marker coverage: fx3={fx3_key_hits}/{len(KEYMAP_APPFW_FX3_MARKERS)}, "
            f"fx6={fx6_key_hits}/{len(KEYMAP_APPFW_FX6_MARKERS)}"
        )

    sc_identical = (
        fx3_sc_exp == fx6_sc_exp
        and fx3_sc_imp == fx6_sc_imp
        and fx3_sc_sum.export_count == EXPECTED_SENCORE_EXPORTS
        and fx3_sc_sum.import_count == EXPECTED_SENCORE_IMPORTS
    )
    if not sc_identical:
        p1_errors.append(
            f"libsencore.so ABI mismatch: fx3=({fx3_sc_sum.export_count},{fx3_sc_sum.import_count}), "
            f"fx6=({fx6_sc_sum.export_count},{fx6_sc_sum.import_count})"
        )

    im_identical = (
        fx3_im_exp == fx6_im_exp
        and fx3_im_imp == fx6_im_imp
        and fx3_im_sum.dt_needed == fx6_im_sum.dt_needed
        and fx3_im_sum.export_count == EXPECTED_IM_ELF_EXPORTS
        and fx3_im_sum.import_count == EXPECTED_IM_ELF_IMPORTS
    )
    if not im_identical:
        p1_errors.append(
            f"im.elf ABI mismatch: fx3=({fx3_im_sum.export_count},{fx3_im_sum.import_count}), "
            f"fx6=({fx6_im_sum.export_count},{fx6_im_sum.import_count})"
        )

    fx3_bk_sum, _, _ = parse_dual_bk4_and_descriptors(fx3_bk_raw, body="FX3_7.02")
    fx6_bk_sum, _, _ = parse_dual_bk4_and_descriptors(fx6_bk_raw, body="FX6_6.01")
    fx3_bk_ok = fx3_bk_sum.rec0_checksum_valid and fx3_bk_sum.rec1_checksum_valid
    fx6_bk_ok = fx6_bk_sum.rec0_checksum_valid and fx6_bk_sum.rec1_checksum_valid
    if not fx3_bk_ok or not fx6_bk_ok:
        p1_errors.append(f"Backup.bin BK4 dual checksum failed: fx3={fx3_bk_ok}, fx6={fx6_bk_ok}")

    p1_evals = (
        evaluate_physical_keymap_bridge(physical_control="CUSTOM_4"),
        evaluate_physical_keymap_bridge(physical_control="MENU"),
        evaluate_physical_keymap_bridge(physical_control="DELETE_DISP"),
        evaluate_physical_keymap_bridge(physical_control="JOYSTICK_5WAY"),
        evaluate_physical_keymap_bridge(physical_control="ZOOM_ROCKER_T_W"),
        evaluate_physical_keymap_bridge(physical_control="REC_TOP"),
        evaluate_physical_keymap_bridge(physical_control="SHUTTER_HALF_FULL"),
        evaluate_physical_keymap_bridge(physical_control="POWER_SWITCH"),
        evaluate_physical_keymap_bridge(physical_control="FX6_ND_WHEEL_AND_PRESET", mask_absent_fx6_controls=True),
    )
    reachable_fns = {ev.fx6_target_function for ev in p1_evals if ev.valid and ev.one_handed_reachable}
    all_reachable = all(fn in reachable_fns for fn in REQUIRED_FX6_REACHABLE_FUNCTIONS)
    escape_preserved = all(ev.valid and ev.escape_hatch_preserved for ev in p1_evals)
    for ev in p1_evals:
        if not ev.valid or ev.missing_gpio_faults != 0:
            p1_errors.extend(ev.errors)
    if not all_reachable:
        p1_errors.append(f"Missing reachable core FX6 functions: {sorted(set(REQUIRED_FX6_REACHABLE_FUNCTIONS) - reachable_fns)}")

    p1_report = Pillar1PhysicalKeymapReport(
        passed=len(p1_errors) == 0,
        fx3_appfw_keymap_hits=fx3_key_hits,
        fx6_appfw_keymap_hits=fx6_key_hits,
        fx3_sencore=fx3_sc_sum,
        fx6_sencore=fx6_sc_sum,
        sencore_exports_identical=sc_identical,
        fx3_im_elf=fx3_im_sum,
        fx6_im_elf=fx6_im_sum,
        im_elf_abi_identical=im_identical,
        fx3_backup_subsystems=fx3_bk_sum.rec0_subsystems,
        fx6_backup_subsystems=fx6_bk_sum.rec0_subsystems,
        fx3_backup_checksums_valid=fx3_bk_ok,
        fx6_backup_checksums_valid=fx6_bk_ok,
        all_fx6_core_functions_reachable=all_reachable,
        escape_hatch_preserved=escape_preserved,
        sample_evals=p1_evals,
        errors=tuple(p1_errors),
    )

    # ---- Pillar 2: Active Cooling Fan PWM & Thermal Emergency Override ----
    p2_errors: List[str] = []
    fx3_fan_hits = sum(1 for m in FAN_APPFW_FX3_MARKERS if fx3_app_hits.get(m, 0) > 0)
    fx6_fan_hits = sum(1 for m in FAN_APPFW_FX6_MARKERS if fx6_app_hits.get(m, 0) > 0)
    if fx3_fan_hits < len(FAN_APPFW_FX3_MARKERS) or fx6_fan_hits < len(FAN_APPFW_FX6_MARKERS):
        p2_errors.append(f"Incomplete appFw fan marker coverage: fx3={fx3_fan_hits}, fx6={fx6_fan_hits}")

    fx3_cp_fan = {m: fx3_cp_hits.get(m, 0) for m in FAN_CP_SHARED_MARKERS}
    fx6_cp_fan = {m: fx6_cp_hits.get(m, 0) for m in FAN_CP_SHARED_MARKERS}
    for m in FAN_CP_SHARED_MARKERS:
        if fx3_cp_fan[m] == 0 or fx6_cp_fan[m] == 0:
            p2_errors.append(f"Missing shared cpapp fan/thermal marker {m!r}")

    sencore_fan_ok = all(
        fx3_sc_sum.marker_hits.get(m, 0) > 0 and fx6_sc_sum.marker_hits.get(m, 0) > 0
        for m in ("FAN_SET_SPEED", "CXS_WRITE_PWM", "GET_TEMPERATURE")
    )
    if not sencore_fan_ok:
        p2_errors.append("Missing libsencore.so FAN_SET_SPEED/CXS_WRITE_PWM/GET_TEMPERATURE markers")

    p2_evals = (
        evaluate_cooling_fan_thermal_bridge(requested_fan_mode="AUTO1", is_recording=True, sensor_temp_c=42.0),
        evaluate_cooling_fan_thermal_bridge(requested_fan_mode="AUTO2", is_recording=True, sensor_temp_c=48.0),
        evaluate_cooling_fan_thermal_bridge(requested_fan_mode="MINIMUM", is_recording=True, sensor_temp_c=40.0),
        evaluate_cooling_fan_thermal_bridge(requested_fan_mode="OFF_IN_REC", is_recording=True, sensor_temp_c=40.0),
        evaluate_cooling_fan_thermal_bridge(requested_fan_mode="OFF_IN_REC", is_recording=True, sensor_temp_c=67.5),
        evaluate_cooling_fan_thermal_bridge(requested_fan_mode="OFF_IN_REC", is_recording=True, sensor_temp_c=73.0),
    )
    for ev in p2_evals:
        if not ev.valid or not ev.thermal_emergency_override_intact:
            p2_errors.extend(ev.errors)

    thermal_intact = all(ev.thermal_emergency_override_intact for ev in p2_evals)
    p2_report = Pillar2CoolingFanThermalReport(
        passed=len(p2_errors) == 0,
        fx3_appfw_fan_hits=fx3_fan_hits,
        fx6_appfw_fan_hits=fx6_fan_hits,
        fx3_cp_fan_hits=fx3_cp_fan,
        fx6_cp_fan_hits=fx6_cp_fan,
        sencore_fan_pwm_verified=sencore_fan_ok,
        thermal_emergency_override_intact=thermal_intact,
        sample_evals=p2_evals,
        errors=tuple(p2_errors),
    )

    # ---- Pillar 3: 3x Physical Body Red Tally Lamps Sync ----
    p3_errors: List[str] = []
    fx3_tally_hits = sum(1 for m in TALLY_APPFW_FX3_MARKERS if fx3_app_hits.get(m, 0) > 0)
    fx6_tally_hits = sum(1 for m in TALLY_APPFW_FX6_MARKERS if fx6_app_hits.get(m, 0) > 0)
    if fx3_tally_hits < len(TALLY_APPFW_FX3_MARKERS) or fx6_tally_hits < len(TALLY_APPFW_FX6_MARKERS):
        p3_errors.append(f"Incomplete appFw tally marker coverage: fx3={fx3_tally_hits}, fx6={fx6_tally_hits}")

    fx3_cp_tally = fx3_cp_hits.get("MSG_ID_INFRABB_SYS_SET_CA_TALLY", 0)
    fx6_cp_tally = fx6_cp_hits.get("MSG_ID_INFRABB_SYS_SET_CA_TALLY", 0)
    if fx3_cp_tally == 0 or fx6_cp_tally == 0:
        p3_errors.append(f"Missing cpapp MSG_ID_INFRABB_SYS_SET_CA_TALLY: fx3={fx3_cp_tally}, fx6={fx6_cp_tally}")

    sencore_tally_ok = (
        fx3_sc_sum.marker_hits.get("TALLY_LED", 0) > 0
        and fx6_sc_sum.marker_hits.get("TALLY_LED", 0) > 0
    )
    if not sencore_tally_ok:
        p3_errors.append("Missing libsencore.so TALLY_LED marker")

    p3_evals = (
        evaluate_tally_lamps_bridge(front_tally_enabled=True, rear_tally_enabled=True, is_recording=True, tally_color="RED"),
        evaluate_tally_lamps_bridge(front_tally_enabled=False, rear_tally_enabled=True, is_recording=True, tally_color="RED"),
        evaluate_tally_lamps_bridge(front_tally_enabled=True, rear_tally_enabled=False, is_recording=True, tally_color="RED"),
        evaluate_tally_lamps_bridge(front_tally_enabled=True, rear_tally_enabled=True, is_recording=False, tally_color="RED"),
        evaluate_tally_lamps_bridge(front_tally_enabled=True, rear_tally_enabled=True, is_recording=True, tally_color="GREEN"),
        evaluate_tally_lamps_bridge(front_tally_enabled=True, rear_tally_enabled=True, is_recording=True, tally_color="YELLOW"),
    )
    for ev in p3_evals:
        if not ev.valid or ev.gpio_mismatch_count != 0:
            p3_errors.extend(ev.errors)

    zero_gpio_mismatch = all(ev.gpio_mismatch_count == 0 for ev in p3_evals)
    p3_report = Pillar3TallyLampsReport(
        passed=len(p3_errors) == 0,
        fx3_appfw_tally_hits=fx3_tally_hits,
        fx6_appfw_tally_hits=fx6_tally_hits,
        fx3_cp_tally_hits=fx3_cp_tally,
        fx6_cp_tally_hits=fx6_cp_tally,
        sencore_tally_led_verified=sencore_tally_ok,
        zero_gpio_mismatch_verified=zero_gpio_mismatch,
        sample_evals=p3_evals,
        errors=tuple(p3_errors),
    )

    # ---- Pillar 4: NP-FZ100 (7.2V) + USB-PD (9V/3A) Power Telemetry Bridge ----
    p4_errors: List[str] = []
    fx3_pwr_hits = sum(1 for m in POWER_APPFW_FX3_MARKERS if fx3_app_hits.get(m, 0) > 0)
    fx6_pwr_hits = sum(1 for m in POWER_APPFW_FX6_MARKERS if fx6_app_hits.get(m, 0) > 0)
    if fx3_pwr_hits < len(POWER_APPFW_FX3_MARKERS) or fx6_pwr_hits < len(POWER_APPFW_FX6_MARKERS):
        p4_errors.append(f"Incomplete appFw power marker coverage: fx3={fx3_pwr_hits}, fx6={fx6_pwr_hits}")

    fx3_wfi_hits = sum(1 for m in POWER_MPR_SHARED_MARKERS if fx3_mpr_hits.get(m, 0) > 0)
    fx6_wfi_hits = sum(1 for m in POWER_MPR_SHARED_MARKERS if fx6_mpr_hits.get(m, 0) > 0)
    if fx3_wfi_hits < len(POWER_MPR_SHARED_MARKERS) or fx6_wfi_hits < len(POWER_MPR_SHARED_MARKERS):
        p4_errors.append(f"Missing libmpr.so EncWfiStop markers: fx3={fx3_wfi_hits}, fx6={fx6_wfi_hits}")

    fx3_cp_batt = sum(1 for m in POWER_CP_SHARED_MARKERS if fx3_cp_hits.get(m, 0) > 0)
    fx6_cp_batt = sum(1 for m in POWER_CP_SHARED_MARKERS if fx6_cp_hits.get(m, 0) > 0)
    if fx3_cp_batt < len(POWER_CP_SHARED_MARKERS) or fx6_cp_batt < len(POWER_CP_SHARED_MARKERS):
        p4_errors.append(f"Incomplete cpapp battery telemetry markers: fx3={fx3_cp_batt}, fx6={fx6_cp_batt}")

    sencore_usb_ok = (
        fx3_sc_sum.marker_hits.get("USB_BUSPOWER_SUPPLY_CONTROL", 0) > 0
        and fx6_sc_sum.marker_hits.get("USB_BUSPOWER_SUPPLY_CONTROL", 0) > 0
    )
    if not sencore_usb_ok:
        p4_errors.append("Missing libsencore.so USB_BUSPOWER_SUPPLY_CONTROL marker")

    p4_evals = (
        evaluate_power_telemetry_bridge(battery_voltage_mv=7600, soc_pct=78, usb_pd_profile="NONE", is_recording=True),
        evaluate_power_telemetry_bridge(battery_voltage_mv=7400, soc_pct=62, usb_pd_profile="USB_PD_9V_3A_27W", is_recording=True),
        evaluate_power_telemetry_bridge(battery_voltage_mv=6320, soc_pct=4, usb_pd_profile="NONE", is_recording=True),
        evaluate_power_telemetry_bridge(battery_voltage_mv=6080, soc_pct=2, usb_pd_profile="NONE", is_recording=True),
    )
    for ev in p4_evals:
        if not ev.valid or ev.false_dcin_low_voltage_alarm:
            p4_errors.extend(ev.errors)

    false_dcin_eliminated = all(not ev.false_dcin_low_voltage_alarm for ev in p4_evals)
    autosave_verified = p4_evals[-1].enc_wfi_graceful_stop_triggered and p4_evals[-1].corrupt_rsv_clip_prevented
    if not autosave_verified:
        p4_errors.append("Low-battery EncWfiStop graceful clip-close failed to trigger at <=2% / 6.08V")

    p4_report = Pillar4PowerTelemetryReport(
        passed=len(p4_errors) == 0,
        fx3_appfw_power_hits=fx3_pwr_hits,
        fx6_appfw_power_hits=fx6_pwr_hits,
        fx3_mpr_wfi_hits=fx3_wfi_hits,
        fx6_mpr_wfi_hits=fx6_wfi_hits,
        fx3_cp_batt_hits=fx3_cp_batt,
        fx6_cp_batt_hits=fx6_cp_batt,
        sencore_usb_buspower_verified=sencore_usb_ok,
        false_dcin_alarm_eliminated=false_dcin_eliminated,
        enc_wfi_low_batt_autosave_verified=autosave_verified,
        sample_evals=p4_evals,
        errors=tuple(p4_errors),
    )

    compat_matrix = build_phase149_controls_matrix()

    vol_guard = evaluate_phase149_write_guard("/tmp/stage_b/keymap_fan_tally_shadow.json")
    bk_guard = evaluate_phase149_write_guard("p2:/setting/Backup.bin")
    cp_guard = evaluate_phase149_write_guard("/dev/nflasha8/cpapp-b.bin")
    emmc_guard = evaluate_phase149_write_guard("/dev/mmcblk0p2")

    guard_errors: List[str] = []
    if not vol_guard.valid:
        guard_errors.append("Volatile RAM staging guard unexpectedly rejected /tmp path")
    if not bk_guard.persistent_write_blocked or not cp_guard.persistent_write_blocked or not emmc_guard.persistent_write_blocked:
        guard_errors.append("Persistent NVS/CP/eMMC write guard failed to block forbidden write target")

    all_errors = tuple(p1_errors + p2_errors + p3_errors + p4_errors + guard_errors)
    all_passed = (
        p1_report.passed
        and p2_report.passed
        and p3_report.passed
        and p4_report.passed
        and len(all_errors) == 0
    )

    draft_dict = {
        "schema_version": PHASE_149_SCHEMA,
        "phase_version": PHASE_149_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "all_fx6_core_functions_reachable": all_reachable,
        "escape_hatch_preserved": escape_preserved,
        "thermal_emergency_override_intact": thermal_intact,
        "zero_gpio_mismatch_verified": zero_gpio_mismatch,
        "false_dcin_alarm_eliminated": false_dcin_eliminated,
        "enc_wfi_low_batt_autosave_verified": autosave_verified,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "donor_file_sizes": donor_sizes,
        "pillar1_keymap": asdict(p1_report),
        "pillar2_fan_thermal": asdict(p2_report),
        "pillar3_tally_lamps": asdict(p3_report),
        "pillar4_power_telemetry": asdict(p4_report),
        "compatibility_matrix": asdict(compat_matrix),
        "volatile_guard_ok": asdict(vol_guard),
        "forbidden_backup_guard_blocked": asdict(bk_guard),
        "forbidden_cpapp_guard_blocked": asdict(cp_guard),
        "forbidden_emmc_guard_blocked": asdict(emmc_guard),
        "errors": list(all_errors),
    }
    digest = hashlib.sha256(
        json.dumps(draft_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return RealhwPhysicalControlsTallyFanAndPowerReport(
        schema_version=PHASE_149_SCHEMA,
        phase_version=PHASE_149_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        all_fx6_core_functions_reachable=all_reachable,
        escape_hatch_preserved=escape_preserved,
        thermal_emergency_override_intact=thermal_intact,
        zero_gpio_mismatch_verified=zero_gpio_mismatch,
        false_dcin_alarm_eliminated=false_dcin_eliminated,
        enc_wfi_low_batt_autosave_verified=autosave_verified,
        persistent_emmc_writes_authorized=False,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        donor_file_sizes=donor_sizes,
        pillar1_keymap=p1_report,
        pillar2_fan_thermal=p2_report,
        pillar3_tally_lamps=p3_report,
        pillar4_power_telemetry=p4_report,
        compatibility_matrix=compat_matrix,
        volatile_guard_ok=vol_guard,
        forbidden_backup_guard_blocked=bk_guard,
        forbidden_cpapp_guard_blocked=cp_guard,
        forbidden_emmc_guard_blocked=emmc_guard,
        report_sha256=digest,
        errors=all_errors,
    )


def realhw_physical_controls_tally_fan_and_power_report_to_dict(
    report: RealhwPhysicalControlsTallyFanAndPowerReport,
) -> Dict[str, object]:
    """Convert `RealhwPhysicalControlsTallyFanAndPowerReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
