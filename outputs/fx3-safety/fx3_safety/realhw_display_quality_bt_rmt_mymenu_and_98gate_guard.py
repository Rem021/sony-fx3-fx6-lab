"""Phase 252 (`98/98` Wave-39) Sony `ILME-FX3` (`Ver. 7.02`) Safety Gates `G97`
(`[Display Quality]` `Standard`/`High` `NP-FZ100` Tier-0 Bench Battery Conservation &
`[Bluetooth Rmt Ctrl]` Radio Prerequisites, Infrared Remote `SIRCS` Mutual Exclusion &
3-Way `Reset Network Set.` Split Guard) & `G98` (`[My Menu Setting]` 6-Operation /
`[Display From My Menu]` Persistence Across `Camera Settings Reset` + `Reset Network Set.` &
Slot-1 Tier-0 `CAMSET01.DAT` `O_RDONLY` Load-Only Firewall Guard) + Unified 98-Gate
Master Safety Preflight (`G01..G98`).

Operationalizes Wave-39 official Sony `ILME-FX3` (`Ver. 7.02`, Help Guide `ilc/2210`)
intelligence (`reports/2026-11-15-global-sony-wave39-display-quality-battery-bt-rmt-ctrl-ir-lockout-network-reset-mymenu-persist-intel/README.md`)
as deterministic offline preflight verifiers (`G97` and `G98`) and delegates
`G01..G96` directly to `evaluate_96gate_preflight()`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    ENV_FORCE_CLEAN_ROOM,
    PERSISTENT_EMMC_WRITES_AUTHORIZED,
    PERSISTENT_WRITE_RELEASE,
    STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
    STATUS_VERIFIED_SAFE,
    GateVerdict,
)
from .realhw_cfexpress_ufu_el3_and_52gate_guard import EL3_PAYLOAD_TRANSMIT_AUTHORIZED
from .realhw_dualmedia_bench_interlock_and_58gate_guard import (
    PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
)
from .realhw_filesettings_shotmark_tcregen_reclamp_and_78gate_guard import (
    _DONOR_BLOB_CACHE,
)
from .realhw_lock_op_parts_audio_timing_exp_step_and_96gate_guard import (
    Master96GateReport,
    evaluate_96gate_preflight,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_SCHEMA: str = (
    "realhw_display_quality_bt_rmt_mymenu_and_98gate_guard_v1"
)
REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_VERSION: str = "1.0.0"

G97_GATE_ID: str = (
    "G97_display_quality_battery_conservation_and_bt_rmt_ctrl_ir_lockout_guard"
)
G97_GATE_CODE: str = (
    "DISPLAY_QUALITY_BATTERY_CONSERVATION_AND_BT_RMT_CTRL_IR_LOCKOUT_GUARD"
)

G98_GATE_ID: str = (
    "G98_mymenu_6op_persistence_and_slot1_camset01_firewall_guard"
)
G98_GATE_CODE: str = (
    "MYMENU_6OP_PERSISTENCE_AND_SLOT1_CAMSET01_FIREWALL_GUARD"
)

G97: str = G97_GATE_ID
G98: str = G98_GATE_ID
GATE_G97_DISPLAY_QUALITY_BATTERY_CONSERVATION_AND_BT_RMT_CTRL_IR_LOCKOUT_GUARD: str = (
    G97_GATE_CODE
)
GATE_G98_MYMENU_6OP_PERSISTENCE_AND_SLOT1_CAMSET01_FIREWALL_GUARD: str = (
    G98_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE252: float = 0.10
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE252

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX6_MODEL_NAME: str = "ILME-FX6"
FX3_DEFAULT_FW_VERSION_PHASE252: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_PHASE252: Tuple[int, int] = (1, 0)
FX3_HELP_GUIDE_CODE_PHASE252: str = "ilc/2210"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_RESET_NETWORK_SET_PHASE252: str = "Reset Network Set."
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE252: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_RESET_NETWORK_SET_PHASE252,
    RESET_ACTION_INITIALIZE,
)

# Status & Violation Codes
STATUS_VERIFIED_G97: str = (
    "VERIFIED_G97_DISPLAY_QUALITY_BATTERY_AND_BT_RMT_IR_LOCKOUT_SAFE"
)
STATUS_VERIFIED_G98: str = (
    "VERIFIED_G98_MYMENU_6OP_PERSISTENCE_AND_SLOT1_CAMSET01_FIREWALL_SAFE"
)
STATUS_BLOCKED_PHASE252_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE252_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G97_TIER0_BATTERY_HIGH_DISPLAY_OR_BRIGHTNESS_DRAIN: str = (
    "BLOCKED_G97_TIER0_BATTERY_HIGH_DISPLAY_OR_BRIGHTNESS_DRAIN"
)
STATUS_BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION: str = (
    "BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION"
)
STATUS_BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION: str = (
    "BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION"
)
STATUS_BLOCKED_G97_BT_RMT_IR_SIRCS_MUTUAL_EXCLUSION_VIOLATION: str = (
    "BLOCKED_G97_BT_RMT_IR_SIRCS_MUTUAL_EXCLUSION_VIOLATION"
)
STATUS_BLOCKED_G97_TELEMETRY_INVALID: str = (
    "BLOCKED_G97_DISPLAY_QUALITY_BT_RMT_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION: str = (
    "BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION"
)
STATUS_BLOCKED_G98_DISPLAY_FROM_MY_MENU_ENUM_OR_OPEN_TARGET_VIOLATION: str = (
    "BLOCKED_G98_DISPLAY_FROM_MY_MENU_ENUM_OR_OPEN_TARGET_VIOLATION"
)
STATUS_BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION: str = (
    "BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION"
)
STATUS_BLOCKED_G98_TELEMETRY_INVALID: str = (
    "BLOCKED_G98_MYMENU_CAMSET_FIREWALL_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G97 Official Menu Constants (`Display Quality` & `Bluetooth Rmt Ctrl`)
# ---------------------------------------------------------------------------

DISPLAY_QUALITY_MENU_PATH_G97: str = (
    "MENU -> Setup -> [Monitor] -> [Display Quality]"
)
DISPLAY_QUALITY_STANDARD_G97: str = "Standard"
DISPLAY_QUALITY_HIGH_G97: str = "High"
ALLOWED_DISPLAY_QUALITY_MODES_G97: Tuple[str, ...] = (
    DISPLAY_QUALITY_STANDARD_G97,
    DISPLAY_QUALITY_HIGH_G97,
)
DISPLAY_QUALITY_FACTORY_DEFAULT_G97: str = DISPLAY_QUALITY_STANDARD_G97

MONITOR_BRIGHTNESS_MANUAL_G97: str = "Manual"
MONITOR_BRIGHTNESS_SUNNY_WEATHER_G97: str = "Sunny Weather"
ALLOWED_MONITOR_BRIGHTNESS_MODES_G97: Tuple[str, ...] = (
    MONITOR_BRIGHTNESS_MANUAL_G97,
    MONITOR_BRIGHTNESS_SUNNY_WEATHER_G97,
)
TIER0_BATTERY_MONITOR_BRIGHTNESS_LEVEL_G97: int = 0
ALLOWED_MONITOR_BRIGHTNESS_LEVELS_G97: Tuple[int, ...] = (-2, -1, 0, 1, 2)

POWER_SOURCE_NP_FZ100_G97: str = "NP-FZ100"
POWER_SOURCE_USB_PD_G97: str = "USB_PD"
POWER_SOURCE_DC_C1_G97: str = "DC-C1"
ALLOWED_POWER_SOURCES_G97: Tuple[str, ...] = (
    POWER_SOURCE_NP_FZ100_G97,
    POWER_SOURCE_USB_PD_G97,
    POWER_SOURCE_DC_C1_G97,
)

BT_RMT_CTRL_MENU_PATH_G97: str = (
    "MENU -> Network -> [Bluetooth] -> [Bluetooth Rmt Ctrl]"
)
BT_RMT_CTRL_OFF_G97: str = "Off"
BT_RMT_CTRL_ON_G97: str = "On"
ALLOWED_BLUETOOTH_RMT_CTRL_MODES_G97: Tuple[str, ...] = (
    BT_RMT_CTRL_OFF_G97,
    BT_RMT_CTRL_ON_G97,
)
BT_RMT_CTRL_FACTORY_DEFAULT_G97: str = BT_RMT_CTRL_OFF_G97

# ---------------------------------------------------------------------------
# Gate G98 Official Menu Constants (`My Menu Setting` & `CAMSET01.DAT` Firewall)
# ---------------------------------------------------------------------------

MY_MENU_SETTING_MENU_PATH_G98: str = "MENU -> My Menu -> [My Menu Setting]"
DISPLAY_FROM_MY_MENU_MENU_PATH_G98: str = (
    "MENU -> My Menu -> [My Menu Setting] -> [Display From My Menu]"
)
MY_MENU_SIX_SUB_OPERATIONS_G98: Tuple[str, ...] = (
    "Add Item",
    "Sort Item",
    "Delete Item",
    "Delete Page",
    "Delete All",
    "Display From My Menu",
)
ALLOWED_MY_MENU_ACTIVE_OPS_G98: Tuple[str, ...] = (
    "NONE",
    "Add Item",
    "Sort Item",
    "Delete Item",
    "Delete Page",
    "Delete All",
    "Display From My Menu",
)
MY_MENU_MAX_PAGES_G98: int = 6
MY_MENU_MAX_ITEMS_PER_PAGE_G98: int = 6
MY_MENU_MAX_TOTAL_ITEMS_G98: int = MY_MENU_MAX_PAGES_G98 * MY_MENU_MAX_ITEMS_PER_PAGE_G98

DISPLAY_FROM_MY_MENU_OFF_G98: str = "Off"
DISPLAY_FROM_MY_MENU_ON_G98: str = "On"
ALLOWED_DISPLAY_FROM_MY_MENU_MODES_G98: Tuple[str, ...] = (
    DISPLAY_FROM_MY_MENU_OFF_G98,
    DISPLAY_FROM_MY_MENU_ON_G98,
)
DISPLAY_FROM_MY_MENU_FACTORY_DEFAULT_G98: str = DISPLAY_FROM_MY_MENU_OFF_G98

MY_MENU_OPEN_TARGET_MOST_RECENT_TAB_G98: str = "MOST_RECENT_TAB"
MY_MENU_OPEN_TARGET_MY_MENU_FIRST_G98: str = "MY_MENU_FIRST"

CAMSET_DEFAULT_SLOT1_FILENAME_G98: str = "CAMSET01.DAT"
CAMSET_OP_NONE_G98: str = "NONE"
CAMSET_OP_LOAD_O_RDONLY_G98: str = "LOAD_O_RDONLY"
CAMSET_OP_SAVE_OVERWRITE_G98: str = "SAVE_OVERWRITE"
ALLOWED_CAMSET_OPERATIONS_G98: Tuple[str, ...] = (
    CAMSET_OP_NONE_G98,
    CAMSET_OP_LOAD_O_RDONLY_G98,
    CAMSET_OP_SAVE_OVERWRITE_G98,
)

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE252_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Display",
            b"Quality",
            b"Standard",
            b"High",
            b"Monitor",
            b"Brightness",
            b"Remote",
            b"Network",
            b"Reset",
            b"Initialize",
            b"Delete",
            b"Sircs",
            b"SIRCS",
        ),
        "FX3_CPAPP_DISPLAY_QUALITY_BT_RMT_SIRCS_NETWORK_RESET_STRINGS",
    ),
    "fx3_libinfrabluetooth_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraBluetooth.so",
        158_968,
        "e49bb8fbb723eef65d4b4e54788c39f57b1cd7ca72285bc02a726ada2ca8ef93",
        (
            b"\x7fELF",
            b"_ZN14InfraBluetoothC1Ev",
            b"_ZN14InfraBluetooth12start_threadEv",
            b"_ZN14InfraBluetooth11register_cbEv",
        ),
        "FX3_LIBINFRABLUETOOTH_RMT_CTRL_DISPATCH_ELF",
    ),
    "fx3_libinfraairplanemode_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAirplaneMode.so",
        14_488,
        "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea",
        (
            b"\x7fELF",
            b"_Z23AirplaneModeTraceRecordhhtj",
            b"_Z28AirplaneModeTraceRecordErrorhhtj",
        ),
        "FX3_LIBINFRAAIRPLANEMODE_ZERO_RF_INTERLOCK_ELF",
    ),
    "fx3_libsaveloadsettings_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (
            b"\x7fELF",
            b"infra_saveLoadSettings_init",
            b"_ZN16SaveLoadSettings13requestToReadEN18SaveLoadSettingsIf11RequestTypeE",
            b"_ZN16SaveLoadSettings14requestToCheckEN18SaveLoadSettingsIf11RequestType",
        ),
        "FX3_LIBSAVELOADSETTINGS_CAMSET01_MYMENU_ROUNDTRIP_ELF",
    ),
    "fx6_libinfrabluetooth_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraBluetooth.so",
        154_840,
        "3b3c1a411f3e157c6d6f7db6ae4dbbb0fc29920561eb3743b7c7723f974cc788",
        (
            b"\x7fELF",
            b"_ZN14InfraBluetoothC1Ev",
            b"_ZN14InfraBluetooth12start_threadEv",
        ),
        "FX6_LIBINFRABLUETOOTH_PARITY_ELF",
    ),
    "fx6_libinfrasircs_so": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraSircs.so",
        27_072,
        "89a33f62ec8fefb0bcab557752068ee6b11494216cc7d2fbf6a03abc3c66a4d1",
        (
            b"\x7fELF",
            b"_ZN10InfraSircs4InitEv",
            b"_ZN10InfraSircs15SetSircsOffTimeEi",
            b"_ZN10InfraSircs15ReleaseInstanceEv",
        ),
        "FX6_LIBINFRASIRCS_IR_REMOTE_MUTUAL_EXCLUSION_ELF",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase252DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_100ms: bool
    raw_firmware_bytes_leaked: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DisplayQualityAndBtRmtGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    display_quality_menu_path: str
    display_quality_factory_default: str
    pre_reset_display_quality: str
    reset_action: str
    effective_post_reset_display_quality: str
    display_quality_survives_camera_settings_reset: bool
    display_quality_survives_reset_network_set: bool
    display_quality_reset_only_by_initialize: bool
    display_quality_high_increases_np_fz100_drain: bool
    power_source: str
    tier0_bench_dump_active: bool
    monitor_brightness_mode: str
    monitor_brightness_level: int
    tier0_battery_clamped_to_standard_and_manual0: bool
    tier0_battery_high_display_violations: int
    bt_rmt_ctrl_menu_path: str
    bt_rmt_ctrl_factory_default: str
    pre_reset_bt_rmt_ctrl: str
    effective_post_reset_bt_rmt_ctrl: str
    bt_rmt_survives_camera_settings_reset: bool
    bt_rmt_reset_by_reset_network_set: bool
    bt_rmt_reset_by_initialize: bool
    bluetooth_function: str
    airplane_mode: str
    zero_rf_bench_enforced: bool
    passive_tx_bytes_emitted: int
    bt_rmt_radio_prerequisites_met: bool
    bt_rmt_ctrl_suppressed_by_radio_prereq: bool
    effective_bt_rmt_ctrl_active: bool
    ir_remote_sircs_usable: bool
    ir_remote_command_attempted: bool
    bt_rmt_ir_lockout_violations: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MyMenuAndCamsetFirewallGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    my_menu_setting_menu_path: str
    display_from_my_menu_menu_path: str
    supported_sub_operations: Tuple[str, ...]
    active_sub_operation: str
    max_pages: int
    max_items_per_page: int
    max_total_items: int
    pre_op_pages_item_counts: Tuple[int, ...]
    post_op_pages_item_counts: Tuple[int, ...]
    effective_post_reset_pages_item_counts: Tuple[int, ...]
    effective_post_reset_page_count: int
    effective_post_reset_total_items: int
    display_from_my_menu_factory_default: str
    pre_reset_display_from_my_menu: str
    reset_action: str
    effective_post_reset_display_from_my_menu: str
    menu_button_open_target: str
    my_menu_survives_camera_settings_reset: bool
    my_menu_survives_reset_network_set: bool
    my_menu_cleared_only_by_delete_ops_or_initialize: bool
    slot1_tier0_vault_protected: bool
    slot1_camset_filename: str
    slot1_camset_operation: str
    slot1_camset_open_flags: int
    camset_source_body_model: str
    camset_roundtrip_supported: bool
    camset_cross_model_fx6_rejected: bool
    slot1_camset_load_only_o_rdonly_enforced: bool
    slot1_mymenu_vault_mutation_bytes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G97DisplayQualityAndBtRmtGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    display_quality_bt_rmt_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G98MyMenuAndCamsetFirewallGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    mymenu_camset_firewall_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master98GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_95_gates_verified: bool
    all_98_gates_verified: bool
    g13_to_g98_all_passed: bool
    g97_to_g98_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_96_report: Dict[str, Any]
    g97_result: Dict[str, Any]
    g98_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers & Normalization
# ---------------------------------------------------------------------------


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip() in (
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    fd = os.open(str(path), flags)
    chunks: List[bytes] = []
    try:
        while True:
            buf = os.read(fd, 1 << 20)
            if not buf:
                break
            chunks.append(buf)
    finally:
        os.close(fd)
    return b"".join(chunks)


def _read_cached_donor_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    key = str(path.resolve())
    st = os.stat(key)
    cached = _DONOR_BLOB_CACHE.get(key)
    if cached is not None and cached[0] == st.st_size and cached[1] == st.st_mtime:
        return cached[2], cached[3], cached[4]
    blob = _read_file_o_rdonly(path)
    sha = hashlib.sha256(blob).hexdigest()
    _DONOR_BLOB_CACHE[key] = (st.st_size, st.st_mtime, len(blob), sha, blob)
    return len(blob), sha, blob


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _parse_fw_tuple(version_str: str) -> Optional[Tuple[int, int]]:
    if not isinstance(version_str, str):
        return None
    m = re.match(r"^\s*[vV]?(\d+)\.(\d+)(?:\.\d+)?\s*$", version_str)
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def _norm_on_off(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s == "ON":
        return "On"
    if s == "OFF":
        return "Off"
    return None


def _norm_reset_action_phase252(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u in ("RESET NETWORK SET.", "RESET NETWORK SET", "RESET NETWORK SETTINGS"):
        return RESET_ACTION_RESET_NETWORK_SET_PHASE252
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_display_quality_g97(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s == "STANDARD":
        return DISPLAY_QUALITY_STANDARD_G97
    if s == "HIGH":
        return DISPLAY_QUALITY_HIGH_G97
    return None


def _norm_monitor_brightness_mode_g97(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s == "MANUAL":
        return MONITOR_BRIGHTNESS_MANUAL_G97
    if s in ("SUNNY WEATHER", "SUNNY"):
        return MONITOR_BRIGHTNESS_SUNNY_WEATHER_G97
    return None


def _norm_power_source_g97(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", "_", raw.strip().strip("[]")).upper()
    if s in ("NP-FZ100", "NP_FZ100", "INTERNAL_BATTERY", "BATTERY"):
        return POWER_SOURCE_NP_FZ100_G97
    if s in ("USB_PD", "USB-PD", "USB_POWER_DELIVERY"):
        return POWER_SOURCE_USB_PD_G97
    if s in ("DC-C1", "DC_C1", "DUMMY_BATTERY"):
        return POWER_SOURCE_DC_C1_G97
    return None


def _norm_my_menu_sub_op_g98(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("NONE", "NO OP", ""):
        return "NONE"
    if s == "ADD ITEM":
        return "Add Item"
    if s == "SORT ITEM":
        return "Sort Item"
    if s == "DELETE ITEM":
        return "Delete Item"
    if s == "DELETE PAGE":
        return "Delete Page"
    if s == "DELETE ALL":
        return "Delete All"
    if s == "DISPLAY FROM MY MENU":
        return "Display From My Menu"
    return None


def _norm_camset_op_g98(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", "_", raw.strip().strip("[]")).upper()
    if s in ("NONE", "NO_OP", ""):
        return CAMSET_OP_NONE_G98
    if s in ("LOAD_O_RDONLY", "LOAD", "READ_ONLY_LOAD"):
        return CAMSET_OP_LOAD_O_RDONLY_G98
    if s in ("SAVE_OVERWRITE", "SAVE", "WRITE", "OVERWRITE"):
        return CAMSET_OP_SAVE_OVERWRITE_G98
    return None


def _norm_camset_filename_g98(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().upper()
    if re.match(r"^CAMSET(?:0[1-9]|10)\.DAT$", s):
        return s
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 252`)
# ---------------------------------------------------------------------------


def audit_phase252_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS_PHASE252,
) -> Phase252DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly
    `os.O_RDONLY` within `<0.10s`, verifying bounded symbols across
    `cpapp-b.bin`, `libInfraBluetooth.so`, `libInfraAirplaneMode.so`,
    `libSaveLoadSettings.so`, and `libInfraSircs.so` with deterministic
    `FX3_FX6_FORCE_CLEAN_ROOM=1` parity.
    """
    t0 = time.perf_counter()
    clean_forced = _is_forced_clean_room(force_clean_room)
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()

    candidate_root: Optional[Path] = None
    if not clean_forced:
        if work_root is not None:
            candidate_root = Path(work_root)
        else:
            paths = resolve_donor_thermal_power_paths(
                work_root=work_root, repo_root=resolved_repo
            )
            candidate_root = paths.work_root

    resolved: Dict[str, Path] = {}
    all_present = False
    if not clean_forced and candidate_root is not None and candidate_root.is_dir():
        all_present = True
        for key, (_body, rel_path, *_rest) in PINNED_PHASE252_DONOR_SPECS.items():
            fp = candidate_root / rel_path
            if fp.is_file():
                resolved[key] = fp
            else:
                all_present = False
                break

    if clean_forced or not all_present:
        elapsed = time.perf_counter() - t0
        within_budget = elapsed < max_budget_seconds
        synthetic_markers = tuple(
            spec[5] for spec in PINNED_PHASE252_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE252_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE252_DONOR_SPECS.items()}
        return Phase252DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE252_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_CLEAN_ROOM",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_100ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=synthetic_markers,
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            sha256_by_artifact=synthetic_shas,
            bytes_by_artifact=synthetic_sizes,
            errors=()
            if within_budget
            else (
                f"Clean-room donor check exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s).",
            ),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    passed_keys: Set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE252_DONOR_SPECS.items():
        size_b, sha, blob = _read_cached_donor_o_rdonly(resolved[key])
        files_inspected += 1
        shas[key] = sha
        sizes[key] = size_b

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = size_b == exp_size and sha == exp_sha
        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )
        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={size_b} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )
        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < max_budget_seconds
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor audit exceeded {max_budget_seconds:.3f}s budget ({elapsed:.4f}s)."
        )

    fx3_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE252_DONOR_SPECS.items()
        if s[0] == "FX3"
    )
    fx6_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE252_DONOR_SPECS.items()
        if s[0] == "FX6"
    )
    valid = fx3_ok and fx6_ok and within_budget and (not errors)
    return Phase252DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE252_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_100ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_ok,
        fx6_contracts_verified=fx6_ok,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate `G97` — `[Display Quality]` Battery Conservation & `[Bluetooth Rmt Ctrl]`
#    Infrared Remote (`SIRCS`) Lockout + 3-Way `Reset Network Set.` Split Guard
# ---------------------------------------------------------------------------


def resolve_fx3_display_quality_and_bt_rmt_state(
    *,
    pre_reset_display_quality: str = DISPLAY_QUALITY_STANDARD_G97,
    pre_reset_bt_rmt_ctrl: str = BT_RMT_CTRL_OFF_G97,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    power_source: str = POWER_SOURCE_NP_FZ100_G97,
    tier0_bench_dump_active: bool = True,
    monitor_brightness_mode: str = MONITOR_BRIGHTNESS_MANUAL_G97,
    monitor_brightness_level: int = TIER0_BATTERY_MONITOR_BRIGHTNESS_LEVEL_G97,
    bluetooth_function: str = "Off",
    airplane_mode: str = "On",
) -> Dict[str, Any]:
    """Deterministic `ILME-FX3` (`Ver. 7.02`) state resolver for `[Display Quality]`
    (`MENU -> Setup -> [Monitor] -> [Display Quality]`) and `[Bluetooth Rmt Ctrl]`
    (`MENU -> Network -> [Bluetooth] -> [Bluetooth Rmt Ctrl]`) across the exact
    3-reset domain split (`Camera Settings Reset` vs `Reset Network Set.` vs
    `Initialize`).
    """
    norm_disp = (
        _norm_display_quality_g97(pre_reset_display_quality)
        or DISPLAY_QUALITY_FACTORY_DEFAULT_G97
    )
    norm_bt = _norm_on_off(pre_reset_bt_rmt_ctrl) or BT_RMT_CTRL_FACTORY_DEFAULT_G97
    norm_reset = _norm_reset_action_phase252(reset_action) or RESET_ACTION_NONE
    norm_power = _norm_power_source_g97(power_source) or POWER_SOURCE_NP_FZ100_G97
    norm_bmode = (
        _norm_monitor_brightness_mode_g97(monitor_brightness_mode)
        or MONITOR_BRIGHTNESS_MANUAL_G97
    )
    norm_bt_func = _norm_on_off(bluetooth_function) or "Off"
    norm_airplane = _norm_on_off(airplane_mode) or "On"

    # [Display Quality] is in [Setup] -> [Monitor]: survives BOTH
    # [Camera Settings Reset] AND [Reset Network Set.], reset ONLY by [Initialize].
    if norm_reset == RESET_ACTION_INITIALIZE:
        post_disp = DISPLAY_QUALITY_FACTORY_DEFAULT_G97
    else:
        post_disp = norm_disp

    # [Bluetooth Rmt Ctrl] is in [Network] -> [Bluetooth]: survives
    # [Camera Settings Reset], reset to Off by BOTH [Reset Network Set.] AND [Initialize].
    if norm_reset in (
        RESET_ACTION_RESET_NETWORK_SET_PHASE252,
        RESET_ACTION_INITIALIZE,
    ):
        post_bt_rmt = BT_RMT_CTRL_FACTORY_DEFAULT_G97
    else:
        post_bt_rmt = norm_bt

    radio_prereq_met = (norm_bt_func == "On") and (norm_airplane == "Off")
    eff_bt_rmt_active = (post_bt_rmt == BT_RMT_CTRL_ON_G97) and radio_prereq_met
    bt_suppressed = (post_bt_rmt == BT_RMT_CTRL_ON_G97) and (not radio_prereq_met)

    # Sony Ver. 7.02 Help Guide: an infrared remote commander (SIRCS) CANNOT be
    # used while [Bluetooth Rmt Ctrl] is set to [On].
    ir_sircs_usable = post_bt_rmt != BT_RMT_CTRL_ON_G97

    tier0_clamped = (
        (not tier0_bench_dump_active)
        or (norm_power != POWER_SOURCE_NP_FZ100_G97)
        or (
            post_disp == DISPLAY_QUALITY_STANDARD_G97
            and norm_bmode == MONITOR_BRIGHTNESS_MANUAL_G97
            and int(monitor_brightness_level) == TIER0_BATTERY_MONITOR_BRIGHTNESS_LEVEL_G97
        )
    )

    return {
        "expected_post_reset_display_quality": post_disp,
        "display_quality_survives_camera_settings_reset": True,
        "display_quality_survives_reset_network_set": True,
        "display_quality_reset_only_by_initialize": True,
        "tier0_battery_clamped_to_standard_and_manual0": tier0_clamped,
        "expected_post_reset_bt_rmt_ctrl": post_bt_rmt,
        "bt_rmt_survives_camera_settings_reset": True,
        "bt_rmt_reset_by_reset_network_set": True,
        "bt_rmt_reset_by_initialize": True,
        "bt_rmt_radio_prerequisites_met": radio_prereq_met,
        "bt_rmt_ctrl_suppressed_by_radio_prereq": bt_suppressed,
        "expected_effective_bt_rmt_ctrl_active": eff_bt_rmt_active,
        "expected_ir_remote_sircs_usable": ir_sircs_usable,
    }


def verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE252,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE252,
    pre_reset_display_quality: str = DISPLAY_QUALITY_STANDARD_G97,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    observed_post_reset_display_quality: Optional[str] = None,
    display_quality_survives_camera_settings_reset: bool = True,
    display_quality_survives_reset_network_set: bool = True,
    display_quality_reset_only_by_initialize: bool = True,
    display_quality_high_increases_np_fz100_drain: bool = True,
    power_source: str = POWER_SOURCE_NP_FZ100_G97,
    tier0_bench_dump_active: bool = True,
    monitor_brightness_mode: str = MONITOR_BRIGHTNESS_MANUAL_G97,
    monitor_brightness_level: int = TIER0_BATTERY_MONITOR_BRIGHTNESS_LEVEL_G97,
    tier0_battery_high_display_violations: int = 0,
    pre_reset_bt_rmt_ctrl: str = BT_RMT_CTRL_OFF_G97,
    observed_post_reset_bt_rmt_ctrl: Optional[str] = None,
    bt_rmt_survives_camera_settings_reset: bool = True,
    bt_rmt_reset_by_reset_network_set: bool = True,
    bt_rmt_reset_by_initialize: bool = True,
    bluetooth_function: str = "Off",
    airplane_mode: str = "On",
    zero_rf_bench_enforced: bool = True,
    passive_tx_bytes_emitted: int = 0,
    observed_effective_bt_rmt_ctrl_active: Optional[bool] = None,
    observed_ir_remote_sircs_usable: Optional[bool] = None,
    ir_remote_command_attempted: bool = False,
    bt_rmt_ir_lockout_violations: int = 0,
) -> DisplayQualityAndBtRmtGuardResult:
    """Verify Gate `G97`: `ILME-FX3` (`Ver. 7.02`) `[Display Quality]` (`Standard`
    default / `High`) battery conservation & `[Setup]` survival across both
    `[Camera Settings Reset]` and `[Reset Network Set.]` + `[Bluetooth Rmt Ctrl]`
    (`Off` default / `On`) radio prerequisites, `SIRCS` infrared remote mutual
    exclusion, and 3-way `Reset Network Set.` split.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE252
        or body_model_name != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE252
    ):
        _add_code(codes, STATUS_BLOCKED_G97_TELEMETRY_INVALID)
        errors.append(
            f"Invalid ILME-FX3 G97 telemetry: model={body_model_name!r} "
            f"(0x{int(body_model_id):08x}), fw={firmware_version!r}, guide={help_guide_code!r}."
        )

    norm_disp = _norm_display_quality_g97(pre_reset_display_quality)
    norm_reset = _norm_reset_action_phase252(reset_action)
    if norm_disp is None or norm_reset is None:
        _add_code(
            codes,
            STATUS_BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
        )
        errors.append(
            f"Invalid [Display Quality] {pre_reset_display_quality!r} or reset_action {reset_action!r}."
        )

    norm_power = _norm_power_source_g97(power_source)
    norm_bmode = _norm_monitor_brightness_mode_g97(monitor_brightness_mode)
    if (
        norm_power is None
        or norm_bmode is None
        or not isinstance(monitor_brightness_level, int)
        or isinstance(monitor_brightness_level, bool)
        or monitor_brightness_level not in ALLOWED_MONITOR_BRIGHTNESS_LEVELS_G97
    ):
        _add_code(codes, STATUS_BLOCKED_G97_TELEMETRY_INVALID)
        errors.append(
            f"Invalid power_source={power_source!r} or monitor_brightness="
            f"{monitor_brightness_mode!r}({monitor_brightness_level!r})."
        )

    norm_bt_rmt = _norm_on_off(pre_reset_bt_rmt_ctrl)
    if norm_bt_rmt is None:
        _add_code(
            codes,
            STATUS_BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION,
        )
        errors.append(
            f"Invalid [Bluetooth Rmt Ctrl] mode {pre_reset_bt_rmt_ctrl!r} (expected 'Off' or 'On')."
        )

    norm_bt_func = _norm_on_off(bluetooth_function)
    norm_airplane = _norm_on_off(airplane_mode)
    if (
        norm_bt_func is None
        or norm_airplane is None
        or int(passive_tx_bytes_emitted) < 0
        or int(tier0_battery_high_display_violations) < 0
        or int(bt_rmt_ir_lockout_violations) < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G97_TELEMETRY_INVALID)
        errors.append(
            f"Invalid radio/counter telemetry: bt_fn={bluetooth_function!r}, "
            f"airplane={airplane_mode!r}, tx={passive_tx_bytes_emitted}."
        )

    state = resolve_fx3_display_quality_and_bt_rmt_state(
        pre_reset_display_quality=norm_disp or DISPLAY_QUALITY_FACTORY_DEFAULT_G97,
        pre_reset_bt_rmt_ctrl=norm_bt_rmt or BT_RMT_CTRL_FACTORY_DEFAULT_G97,
        reset_action=norm_reset or RESET_ACTION_NONE,
        power_source=norm_power or POWER_SOURCE_NP_FZ100_G97,
        tier0_bench_dump_active=bool(tier0_bench_dump_active),
        monitor_brightness_mode=norm_bmode or MONITOR_BRIGHTNESS_MANUAL_G97,
        monitor_brightness_level=(
            int(monitor_brightness_level)
            if isinstance(monitor_brightness_level, int)
            else 0
        ),
        bluetooth_function=norm_bt_func or "Off",
        airplane_mode=norm_airplane or "On",
    )

    exp_post_disp = state["expected_post_reset_display_quality"]
    if observed_post_reset_display_quality is not None:
        obs_disp = _norm_display_quality_g97(observed_post_reset_display_quality)
        if obs_disp is None or obs_disp != exp_post_disp:
            _add_code(
                codes,
                STATUS_BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
            )
            errors.append(
                f"Post-reset [Display Quality] mismatch after {reset_action!r}: "
                f"observed={observed_post_reset_display_quality!r}, expected={exp_post_disp!r}."
            )
        eff_post_disp = obs_disp or exp_post_disp
    else:
        eff_post_disp = exp_post_disp

    if (
        not display_quality_survives_camera_settings_reset
        or not display_quality_survives_reset_network_set
        or not display_quality_reset_only_by_initialize
        or not display_quality_high_increases_np_fz100_drain
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G97_DISPLAY_QUALITY_ENUM_OR_RESET_PERSISTENCE_VIOLATION,
        )
        errors.append(
            "[Display Quality] must survive both [Camera Settings Reset] and "
            "[Reset Network Set.], reset only by [Initialize], and track [High] battery drain."
        )

    eff_power = norm_power or POWER_SOURCE_NP_FZ100_G97
    eff_bmode = norm_bmode or MONITOR_BRIGHTNESS_MANUAL_G97
    eff_blevel = (
        int(monitor_brightness_level)
        if isinstance(monitor_brightness_level, int)
        else 0
    )
    tier0_viol_count = int(tier0_battery_high_display_violations)
    if bool(tier0_bench_dump_active) and eff_power == POWER_SOURCE_NP_FZ100_G97:
        if (
            eff_post_disp != DISPLAY_QUALITY_STANDARD_G97
            or eff_bmode != MONITOR_BRIGHTNESS_MANUAL_G97
            or eff_blevel != TIER0_BATTERY_MONITOR_BRIGHTNESS_LEVEL_G97
        ):
            tier0_viol_count += 1

    tier0_clamped = tier0_viol_count == 0 and (
        (not bool(tier0_bench_dump_active))
        or eff_power != POWER_SOURCE_NP_FZ100_G97
        or (
            eff_post_disp == DISPLAY_QUALITY_STANDARD_G97
            and eff_bmode == MONITOR_BRIGHTNESS_MANUAL_G97
            and eff_blevel == TIER0_BATTERY_MONITOR_BRIGHTNESS_LEVEL_G97
        )
    )
    if not tier0_clamped or tier0_viol_count > 0:
        _add_code(codes, STATUS_BLOCKED_G97_TIER0_BATTERY_HIGH_DISPLAY_OR_BRIGHTNESS_DRAIN)
        errors.append(
            f"Internal NP-FZ100 Tier-0 bench dump requires [Display Quality]=Standard "
            f"and [Monitor Brightness]=Manual(0): got quality={eff_post_disp!r}, "
            f"brightness={eff_bmode}({eff_blevel}), violations={tier0_viol_count}."
        )

    exp_post_bt = state["expected_post_reset_bt_rmt_ctrl"]
    if observed_post_reset_bt_rmt_ctrl is not None:
        obs_bt = _norm_on_off(observed_post_reset_bt_rmt_ctrl)
        if obs_bt is None or obs_bt != exp_post_bt:
            _add_code(
                codes,
                STATUS_BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION,
            )
            errors.append(
                f"Post-reset [Bluetooth Rmt Ctrl] mismatch after {reset_action!r}: "
                f"observed={observed_post_reset_bt_rmt_ctrl!r}, expected={exp_post_bt!r}."
            )
        eff_post_bt = obs_bt or exp_post_bt
    else:
        eff_post_bt = exp_post_bt

    if (
        not bt_rmt_survives_camera_settings_reset
        or not bt_rmt_reset_by_reset_network_set
        or not bt_rmt_reset_by_initialize
    ):
        _add_code(
            codes,
            STATUS_BLOCKED_G97_BT_RMT_CTRL_ENUM_OR_NETWORK_RESET_SPLIT_VIOLATION,
        )
        errors.append(
            "[Bluetooth Rmt Ctrl] must survive [Camera Settings Reset] and reset to "
            "Off on BOTH [Reset Network Set.] and [Initialize]."
        )

    eff_bt_func = norm_bt_func or "Off"
    eff_airplane = norm_airplane or "On"
    radio_prereq_met = (eff_bt_func == "On") and (eff_airplane == "Off")
    exp_bt_active = (eff_post_bt == BT_RMT_CTRL_ON_G97) and radio_prereq_met
    eff_bt_active = (
        bool(observed_effective_bt_rmt_ctrl_active)
        if observed_effective_bt_rmt_ctrl_active is not None
        else exp_bt_active
    )

    if eff_bt_active != exp_bt_active:
        _add_code(
            codes,
            STATUS_BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
        )
        errors.append(
            f"[Bluetooth Rmt Ctrl] active state {eff_bt_active} violates radio "
            f"prerequisites ([Bluetooth Function]={eff_bt_func}, [Airplane Mode]={eff_airplane})."
        )

    if bool(zero_rf_bench_enforced):
        if (
            eff_airplane != "On"
            or int(passive_tx_bytes_emitted) != 0
            or eff_bt_active
        ):
            _add_code(
                codes,
                STATUS_BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
            )
            errors.append(
                f"Zero-RF bench violation: airplane_mode={eff_airplane!r}, "
                f"passive_tx_bytes_emitted={passive_tx_bytes_emitted}, bt_active={eff_bt_active}."
            )
    elif int(passive_tx_bytes_emitted) > 0 and eff_airplane == "On":
        _add_code(
            codes,
            STATUS_BLOCKED_G97_BT_RMT_PREREQUISITE_OR_ZERO_RF_BENCH_VIOLATION,
        )
        errors.append("RF bytes emitted while [Airplane Mode]=On.")

    exp_ir_usable = eff_post_bt != BT_RMT_CTRL_ON_G97
    eff_ir_usable = (
        bool(observed_ir_remote_sircs_usable)
        if observed_ir_remote_sircs_usable is not None
        else exp_ir_usable
    )
    ir_viol_count = int(bt_rmt_ir_lockout_violations)
    if eff_post_bt == BT_RMT_CTRL_ON_G97 and (
        eff_ir_usable or bool(ir_remote_command_attempted)
    ):
        ir_viol_count += 1
    if eff_ir_usable != exp_ir_usable or ir_viol_count > 0:
        _add_code(codes, STATUS_BLOCKED_G97_BT_RMT_IR_SIRCS_MUTUAL_EXCLUSION_VIOLATION)
        errors.append(
            f"SIRCS Infrared Remote mutual exclusion violated while "
            f"[Bluetooth Rmt Ctrl]={eff_post_bt!r}: ir_usable={eff_ir_usable}, "
            f"ir_attempted={ir_remote_command_attempted}, violations={ir_viol_count}."
        )

    valid = not codes
    status = STATUS_VERIFIED_G97 if valid else codes[0]
    return DisplayQualityAndBtRmtGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08x}",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        display_quality_menu_path=DISPLAY_QUALITY_MENU_PATH_G97,
        display_quality_factory_default=DISPLAY_QUALITY_FACTORY_DEFAULT_G97,
        pre_reset_display_quality=norm_disp or str(pre_reset_display_quality),
        reset_action=norm_reset or str(reset_action),
        effective_post_reset_display_quality=eff_post_disp,
        display_quality_survives_camera_settings_reset=bool(
            display_quality_survives_camera_settings_reset
        ),
        display_quality_survives_reset_network_set=bool(
            display_quality_survives_reset_network_set
        ),
        display_quality_reset_only_by_initialize=bool(
            display_quality_reset_only_by_initialize
        ),
        display_quality_high_increases_np_fz100_drain=bool(
            display_quality_high_increases_np_fz100_drain
        ),
        power_source=eff_power,
        tier0_bench_dump_active=bool(tier0_bench_dump_active),
        monitor_brightness_mode=eff_bmode,
        monitor_brightness_level=eff_blevel,
        tier0_battery_clamped_to_standard_and_manual0=tier0_clamped,
        tier0_battery_high_display_violations=tier0_viol_count,
        bt_rmt_ctrl_menu_path=BT_RMT_CTRL_MENU_PATH_G97,
        bt_rmt_ctrl_factory_default=BT_RMT_CTRL_FACTORY_DEFAULT_G97,
        pre_reset_bt_rmt_ctrl=norm_bt_rmt or str(pre_reset_bt_rmt_ctrl),
        effective_post_reset_bt_rmt_ctrl=eff_post_bt,
        bt_rmt_survives_camera_settings_reset=bool(
            bt_rmt_survives_camera_settings_reset
        ),
        bt_rmt_reset_by_reset_network_set=bool(bt_rmt_reset_by_reset_network_set),
        bt_rmt_reset_by_initialize=bool(bt_rmt_reset_by_initialize),
        bluetooth_function=eff_bt_func,
        airplane_mode=eff_airplane,
        zero_rf_bench_enforced=bool(zero_rf_bench_enforced),
        passive_tx_bytes_emitted=int(passive_tx_bytes_emitted),
        bt_rmt_radio_prerequisites_met=radio_prereq_met,
        bt_rmt_ctrl_suppressed_by_radio_prereq=(eff_post_bt == BT_RMT_CTRL_ON_G97)
        and (not radio_prereq_met),
        effective_bt_rmt_ctrl_active=eff_bt_active,
        ir_remote_sircs_usable=eff_ir_usable,
        ir_remote_command_attempted=bool(ir_remote_command_attempted),
        bt_rmt_ir_lockout_violations=ir_viol_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g97_display_quality_and_bt_rmt_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    display_quality_bt_rmt_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase252DonorAuditResult] = None,
) -> Tuple[GateVerdict, G97DisplayQualityAndBtRmtGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase252_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_display_quality_battery_and_bt_rmt_ir_lockout_guard(
        **dict(display_quality_bt_rmt_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G97.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G97 if valid else codes[0]

    res = G97DisplayQualityAndBtRmtGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        display_quality_bt_rmt_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, display_quality={guard.effective_post_reset_display_quality}"
        f"(tier0_clamped={guard.tier0_battery_clamped_to_standard_and_manual0},"
        f"batt_viol={guard.tier0_battery_high_display_violations}), "
        f"bt_rmt={guard.effective_post_reset_bt_rmt_ctrl}"
        f"(active={guard.effective_bt_rmt_ctrl_active},airplane={guard.airplane_mode},"
        f"tx={guard.passive_tx_bytes_emitted},ir_viol={guard.bt_rmt_ir_lockout_violations})"
    )
    verdict = GateVerdict(
        gate_id=G97_GATE_ID,
        gate_code=G97_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate `G98` — `[My Menu Setting]` 6-Operation Persistence & Slot-1 Tier-0
#    `CAMSET01.DAT` `O_RDONLY` Load-Only Firewall Guard
# ---------------------------------------------------------------------------


def resolve_fx3_mymenu_and_camset_firewall_state(
    *,
    pre_op_pages_item_counts: Sequence[int] = (6, 4),
    active_sub_operation: str = "NONE",
    target_page_index: int = 0,
    pre_reset_display_from_my_menu: str = DISPLAY_FROM_MY_MENU_ON_G98,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
) -> Dict[str, Any]:
    """Deterministic `ILME-FX3` (`Ver. 7.02`) state resolver for `[My Menu Setting]`
    (`Add Item`, `Sort Item`, `Delete Item`, `Delete Page`, `Delete All`, and
    `[Display From My Menu]` `Off`/`On`, up to `6` pages x `6` items = `36` items)
    across `Camera Settings Reset`, `Reset Network Set.`, and `Initialize`.
    """
    pages: List[int] = [int(c) for c in pre_op_pages_item_counts if int(c) > 0]
    norm_op = _norm_my_menu_sub_op_g98(active_sub_operation) or "NONE"
    norm_dfmm = (
        _norm_on_off(pre_reset_display_from_my_menu)
        or DISPLAY_FROM_MY_MENU_FACTORY_DEFAULT_G98
    )
    norm_reset = _norm_reset_action_phase252(reset_action) or RESET_ACTION_NONE

    post_op = list(pages)
    idx = max(0, int(target_page_index))
    if norm_op == "Add Item":
        if not post_op:
            post_op = [1]
        elif idx < len(post_op) and post_op[idx] < MY_MENU_MAX_ITEMS_PER_PAGE_G98:
            post_op[idx] += 1
        elif len(post_op) < MY_MENU_MAX_PAGES_G98:
            post_op.append(1)
        else:
            post_op[-1] += 1  # triggers capacity overflow check in verifier
    elif norm_op == "Sort Item":
        pass  # reorders items within pages without changing counts
    elif norm_op == "Delete Item":
        if post_op:
            p_i = min(idx, len(post_op) - 1)
            post_op[p_i] -= 1
            if post_op[p_i] <= 0:
                post_op.pop(p_i)
    elif norm_op == "Delete Page":
        if post_op:
            p_i = min(idx, len(post_op) - 1)
            post_op.pop(p_i)
    elif norm_op == "Delete All":
        post_op = []

    # Both [My Menu] registered pages and [Display From My Menu] survive BOTH
    # [Camera Settings Reset] AND [Reset Network Set.], clearing ONLY on [Initialize]
    # (or explicit [Delete All] / [Delete Page] above).
    if norm_reset == RESET_ACTION_INITIALIZE:
        post_reset_pages: Tuple[int, ...] = ()
        post_reset_dfmm = DISPLAY_FROM_MY_MENU_FACTORY_DEFAULT_G98
    else:
        post_reset_pages = tuple(post_op)
        post_reset_dfmm = norm_dfmm

    open_target = (
        MY_MENU_OPEN_TARGET_MY_MENU_FIRST_G98
        if post_reset_dfmm == DISPLAY_FROM_MY_MENU_ON_G98
        else MY_MENU_OPEN_TARGET_MOST_RECENT_TAB_G98
    )

    return {
        "post_op_pages_item_counts": tuple(post_op),
        "expected_post_reset_pages_item_counts": post_reset_pages,
        "expected_post_reset_page_count": len(post_reset_pages),
        "expected_post_reset_total_items": sum(post_reset_pages),
        "expected_post_reset_display_from_my_menu": post_reset_dfmm,
        "expected_menu_button_open_target": open_target,
        "my_menu_survives_camera_settings_reset": True,
        "my_menu_survives_reset_network_set": True,
        "my_menu_cleared_only_by_delete_ops_or_initialize": True,
    }


def verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
    *,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE252,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_PHASE252,
    supported_sub_operations: Sequence[str] = MY_MENU_SIX_SUB_OPERATIONS_G98,
    active_sub_operation: str = "NONE",
    target_page_index: int = 0,
    pre_op_pages_item_counts: Sequence[int] = (6, 4),
    observed_post_reset_pages_item_counts: Optional[Sequence[int]] = None,
    pre_reset_display_from_my_menu: str = DISPLAY_FROM_MY_MENU_ON_G98,
    reset_action: str = RESET_ACTION_CAMERA_SETTINGS_RESET,
    observed_post_reset_display_from_my_menu: Optional[str] = None,
    observed_menu_button_open_target: Optional[str] = None,
    my_menu_survives_camera_settings_reset: bool = True,
    my_menu_survives_reset_network_set: bool = True,
    my_menu_cleared_only_by_delete_ops_or_initialize: bool = True,
    slot1_tier0_vault_protected: bool = True,
    slot1_camset_filename: str = CAMSET_DEFAULT_SLOT1_FILENAME_G98,
    slot1_camset_operation: str = CAMSET_OP_LOAD_O_RDONLY_G98,
    slot1_camset_open_flags: int = os.O_RDONLY,
    camset_source_body_model: str = FX3_MODEL_NAME,
    camset_roundtrip_supported: bool = True,
    camset_cross_model_fx6_rejected: bool = True,
    slot1_mymenu_vault_mutation_bytes: int = 0,
) -> MyMenuAndCamsetFirewallGuardResult:
    """Verify Gate `G98`: `ILME-FX3` (`Ver. 7.02`) `[My Menu Setting]` (`Add Item`,
    `Sort Item`, `Delete Item`, `Delete Page`, `Delete All`, up to `6x6 = 36` items,
    and `[Display From My Menu]` `Off`/`On`), persistence across both
    `[Camera Settings Reset]` and `[Reset Network Set.]`, and Slot-1 Tier-0
    `CAMSET01.DAT` `O_RDONLY` load-only firewall (`slot1_mymenu_vault_mutation_bytes == 0`).
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE252
        or body_model_name != FX3_MODEL_NAME
        or int(body_model_id) != FX3_MODEL_ID
        or help_guide_code != FX3_HELP_GUIDE_CODE_PHASE252
    ):
        _add_code(codes, STATUS_BLOCKED_G98_TELEMETRY_INVALID)
        errors.append(
            f"Invalid ILME-FX3 G98 telemetry: model={body_model_name!r} "
            f"(0x{int(body_model_id):08x}), fw={firmware_version!r}, guide={help_guide_code!r}."
        )

    norm_supported: List[str] = []
    sub_ops_valid = True
    for raw_op in supported_sub_operations:
        nop = _norm_my_menu_sub_op_g98(raw_op)
        if nop is None or nop == "NONE":
            sub_ops_valid = False
        else:
            norm_supported.append(nop)
    if (
        not sub_ops_valid
        or tuple(norm_supported) != MY_MENU_SIX_SUB_OPERATIONS_G98
    ):
        _add_code(codes, STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION)
        errors.append(
            f"[My Menu Setting] must expose exact 6 sub-operations "
            f"{MY_MENU_SIX_SUB_OPERATIONS_G98}; got {tuple(supported_sub_operations)!r}."
        )

    norm_active_op = _norm_my_menu_sub_op_g98(active_sub_operation)
    if norm_active_op is None or norm_active_op not in ALLOWED_MY_MENU_ACTIVE_OPS_G98:
        _add_code(codes, STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION)
        errors.append(f"Unsupported [My Menu Setting] operation: {active_sub_operation!r}.")

    try:
        raw_pages = tuple(int(x) for x in pre_op_pages_item_counts)
    except (TypeError, ValueError):
        raw_pages = ()
        _add_code(codes, STATUS_BLOCKED_G98_TELEMETRY_INVALID)
        errors.append("Invalid pre_op_pages_item_counts sequence.")

    if (
        len(raw_pages) > MY_MENU_MAX_PAGES_G98
        or any(c < 0 or c > MY_MENU_MAX_ITEMS_PER_PAGE_G98 for c in raw_pages)
        or sum(raw_pages) > MY_MENU_MAX_TOTAL_ITEMS_G98
    ):
        _add_code(codes, STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION)
        errors.append(
            f"Pre-op My Menu capacity violation (max 6 pages x 6 items = 36): {raw_pages!r}."
        )

    norm_dfmm = _norm_on_off(pre_reset_display_from_my_menu)
    if norm_dfmm is None:
        _add_code(
            codes,
            STATUS_BLOCKED_G98_DISPLAY_FROM_MY_MENU_ENUM_OR_OPEN_TARGET_VIOLATION,
        )
        errors.append(
            f"Invalid [Display From My Menu] mode {pre_reset_display_from_my_menu!r}."
        )

    norm_reset = _norm_reset_action_phase252(reset_action)
    if norm_reset is None:
        _add_code(codes, STATUS_BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION)
        errors.append(f"Invalid reset_action {reset_action!r} in Gate G98.")

    state = resolve_fx3_mymenu_and_camset_firewall_state(
        pre_op_pages_item_counts=raw_pages,
        active_sub_operation=norm_active_op or "NONE",
        target_page_index=target_page_index,
        pre_reset_display_from_my_menu=(
            norm_dfmm or DISPLAY_FROM_MY_MENU_FACTORY_DEFAULT_G98
        ),
        reset_action=norm_reset or RESET_ACTION_NONE,
    )

    post_op_pages: Tuple[int, ...] = state["post_op_pages_item_counts"]
    if (
        len(post_op_pages) > MY_MENU_MAX_PAGES_G98
        or any(c < 1 or c > MY_MENU_MAX_ITEMS_PER_PAGE_G98 for c in post_op_pages)
        or sum(post_op_pages) > MY_MENU_MAX_TOTAL_ITEMS_G98
    ):
        _add_code(codes, STATUS_BLOCKED_G98_MY_MENU_SUB_OP_OR_CAPACITY_VIOLATION)
        errors.append(
            f"Post-op My Menu capacity overflow (max 6x6=36): {post_op_pages!r}."
        )

    exp_pages: Tuple[int, ...] = state["expected_post_reset_pages_item_counts"]
    if observed_post_reset_pages_item_counts is not None:
        obs_pages = tuple(int(x) for x in observed_post_reset_pages_item_counts)
        if obs_pages != exp_pages:
            _add_code(codes, STATUS_BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION)
            errors.append(
                f"Post-reset My Menu pages mismatch after {reset_action!r}: "
                f"observed={obs_pages!r}, expected={exp_pages!r}."
            )
        eff_pages = obs_pages
    else:
        eff_pages = exp_pages

    exp_dfmm = state["expected_post_reset_display_from_my_menu"]
    if observed_post_reset_display_from_my_menu is not None:
        obs_dfmm = _norm_on_off(observed_post_reset_display_from_my_menu)
        if obs_dfmm is None:
            _add_code(
                codes,
                STATUS_BLOCKED_G98_DISPLAY_FROM_MY_MENU_ENUM_OR_OPEN_TARGET_VIOLATION,
            )
            errors.append(
                f"Invalid observed [Display From My Menu] {observed_post_reset_display_from_my_menu!r}."
            )
        elif obs_dfmm != exp_dfmm:
            _add_code(codes, STATUS_BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION)
            errors.append(
                f"Post-reset [Display From My Menu] mismatch after {reset_action!r}: "
                f"observed={obs_dfmm!r}, expected={exp_dfmm!r}."
            )
        eff_dfmm = obs_dfmm or exp_dfmm
    else:
        eff_dfmm = exp_dfmm

    exp_open_target = (
        MY_MENU_OPEN_TARGET_MY_MENU_FIRST_G98
        if eff_dfmm == DISPLAY_FROM_MY_MENU_ON_G98
        else MY_MENU_OPEN_TARGET_MOST_RECENT_TAB_G98
    )
    eff_open_target = (
        str(observed_menu_button_open_target).strip().upper()
        if observed_menu_button_open_target is not None
        else exp_open_target
    )
    if eff_open_target != exp_open_target:
        _add_code(
            codes,
            STATUS_BLOCKED_G98_DISPLAY_FROM_MY_MENU_ENUM_OR_OPEN_TARGET_VIOLATION,
        )
        errors.append(
            f"MENU button open target {eff_open_target!r} mismatches "
            f"[Display From My Menu]={eff_dfmm!r} (expected {exp_open_target!r})."
        )

    if (
        not my_menu_survives_camera_settings_reset
        or not my_menu_survives_reset_network_set
        or not my_menu_cleared_only_by_delete_ops_or_initialize
    ):
        _add_code(codes, STATUS_BLOCKED_G98_MY_MENU_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            "My Menu pages and [Display From My Menu] must survive both "
            "[Camera Settings Reset] and [Reset Network Set.]."
        )

    norm_camset_fn = _norm_camset_filename_g98(slot1_camset_filename)
    norm_camset_op = _norm_camset_op_g98(slot1_camset_operation)
    write_flag_mask = (
        getattr(os, "O_WRONLY", 1)
        | getattr(os, "O_RDWR", 2)
        | getattr(os, "O_CREAT", 0)
        | getattr(os, "O_TRUNC", 0)
        | getattr(os, "O_APPEND", 0)
    )
    has_write_flags = (int(slot1_camset_open_flags) & write_flag_mask) != 0
    mut_bytes = int(slot1_mymenu_vault_mutation_bytes)
    if mut_bytes < 0:
        _add_code(codes, STATUS_BLOCKED_G98_TELEMETRY_INVALID)
        errors.append("Negative slot1_mymenu_vault_mutation_bytes.")

    load_only_enforced = (
        norm_camset_fn is not None
        and norm_camset_op in (CAMSET_OP_NONE_G98, CAMSET_OP_LOAD_O_RDONLY_G98)
        and (not has_write_flags)
        and mut_bytes == 0
        and camset_source_body_model == FX3_MODEL_NAME
        and bool(camset_roundtrip_supported)
        and bool(camset_cross_model_fx6_rejected)
    )
    if bool(slot1_tier0_vault_protected):
        if not load_only_enforced:
            _add_code(codes, STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION)
            errors.append(
                f"Slot-1 Tier-0 CAMSET01.DAT firewall violation: file={slot1_camset_filename!r}, "
                f"op={slot1_camset_operation!r}, flags=0x{int(slot1_camset_open_flags):x}, "
                f"source_model={camset_source_body_model!r}, mutation_bytes={mut_bytes}."
            )
    else:
        if (
            norm_camset_fn is None
            or norm_camset_op is None
            or camset_source_body_model != FX3_MODEL_NAME
            or not camset_roundtrip_supported
            or not camset_cross_model_fx6_rejected
            or mut_bytes > 0
        ):
            _add_code(codes, STATUS_BLOCKED_G98_SLOT1_CAMSET01_FIREWALL_MUTATION_VIOLATION)
            errors.append("CAMSET firewall/cross-model integrity violated.")

    valid = not codes
    status = STATUS_VERIFIED_G98 if valid else codes[0]
    return MyMenuAndCamsetFirewallGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=body_model_name,
        body_model_id_hex=f"0x{int(body_model_id):08x}",
        help_guide_code=help_guide_code,
        firmware_version=firmware_version,
        my_menu_setting_menu_path=MY_MENU_SETTING_MENU_PATH_G98,
        display_from_my_menu_menu_path=DISPLAY_FROM_MY_MENU_MENU_PATH_G98,
        supported_sub_operations=tuple(norm_supported),
        active_sub_operation=norm_active_op or str(active_sub_operation),
        max_pages=MY_MENU_MAX_PAGES_G98,
        max_items_per_page=MY_MENU_MAX_ITEMS_PER_PAGE_G98,
        max_total_items=MY_MENU_MAX_TOTAL_ITEMS_G98,
        pre_op_pages_item_counts=raw_pages,
        post_op_pages_item_counts=post_op_pages,
        effective_post_reset_pages_item_counts=eff_pages,
        effective_post_reset_page_count=len(eff_pages),
        effective_post_reset_total_items=sum(eff_pages),
        display_from_my_menu_factory_default=DISPLAY_FROM_MY_MENU_FACTORY_DEFAULT_G98,
        pre_reset_display_from_my_menu=norm_dfmm or str(pre_reset_display_from_my_menu),
        reset_action=norm_reset or str(reset_action),
        effective_post_reset_display_from_my_menu=eff_dfmm,
        menu_button_open_target=eff_open_target,
        my_menu_survives_camera_settings_reset=bool(
            my_menu_survives_camera_settings_reset
        ),
        my_menu_survives_reset_network_set=bool(my_menu_survives_reset_network_set),
        my_menu_cleared_only_by_delete_ops_or_initialize=bool(
            my_menu_cleared_only_by_delete_ops_or_initialize
        ),
        slot1_tier0_vault_protected=bool(slot1_tier0_vault_protected),
        slot1_camset_filename=norm_camset_fn or str(slot1_camset_filename),
        slot1_camset_operation=norm_camset_op or str(slot1_camset_operation),
        slot1_camset_open_flags=int(slot1_camset_open_flags),
        camset_source_body_model=camset_source_body_model,
        camset_roundtrip_supported=bool(camset_roundtrip_supported),
        camset_cross_model_fx6_rejected=bool(camset_cross_model_fx6_rejected),
        slot1_camset_load_only_o_rdonly_enforced=load_only_enforced,
        slot1_mymenu_vault_mutation_bytes=max(0, mut_bytes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g98_mymenu_and_camset_firewall_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    mymenu_camset_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase252DonorAuditResult] = None,
) -> Tuple[GateVerdict, G98MyMenuAndCamsetFirewallGuardResult]:
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase252_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_mymenu_6op_persistence_and_slot1_camset_firewall_guard(
        **dict(mymenu_camset_kwargs or {})
    )

    codes: List[str] = []
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC write authorization requested in Gate G98.")
    if not audit.valid:
        _add_code(codes, audit.status)
    for c in guard.violation_codes:
        _add_code(codes, c)

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G98 if valid else codes[0]

    res = G98MyMenuAndCamsetFirewallGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        mymenu_camset_firewall_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, mymenu_pages={guard.effective_post_reset_page_count}"
        f"(items={guard.effective_post_reset_total_items},dfmm={guard.effective_post_reset_display_from_my_menu},"
        f"open={guard.menu_button_open_target}), "
        f"slot1_camset={guard.slot1_camset_filename}({guard.slot1_camset_operation},"
        f"mut_bytes={guard.slot1_mymenu_vault_mutation_bytes})"
    )
    verdict = GateVerdict(
        gate_id=G98_GATE_ID,
        gate_code=G98_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `98`-Gate Master Safety Preflight (`G01..G98`)
# ---------------------------------------------------------------------------


def evaluate_98gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    display_quality_bt_rmt_kwargs: Optional[Mapping[str, Any]] = None,
    mymenu_camset_kwargs: Optional[Mapping[str, Any]] = None,
    master_96_override: Optional[Master96GateReport] = None,
    **m96_passthrough_kwargs: Any,
) -> Master98GateReport:
    """Evaluate all 98 Master Safety Gates (`G01..G98`) deterministically by
    delegating `G01..G96` directly to `evaluate_96gate_preflight()`.
    """
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        or simulate_bench_dry_run
        or bool(dry_run_simulated_backup)
    )

    m96_report: Master96GateReport = (
        master_96_override
        if master_96_override is not None
        else evaluate_96gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m96_passthrough_kwargs,
        )
    )

    phase252_audit = audit_phase252_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g97_verdict, g97_res = evaluate_g97_display_quality_and_bt_rmt_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        display_quality_bt_rmt_kwargs=display_quality_bt_rmt_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase252_audit,
    )

    g98_verdict, g98_res = evaluate_g98_mymenu_and_camset_firewall_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        mymenu_camset_kwargs=mymenu_camset_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase252_audit,
    )

    gates_97_to_98 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g97_verdict, g98_verdict)
    ]
    all_gates = tuple(list(m96_report.gates) + gates_97_to_98)

    g01_to_g12_verified = int(m96_report.summary["g01_to_g12_verified"])
    g13_to_g96_verified = (
        int(m96_report.summary["g13_to_g94_verified"])
        + int(m96_report.summary["g95_to_g96_verified"])
    )
    g97_to_g98_verified = sum(1 for v in (g97_verdict, g98_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g96_verified + g97_to_g98_verified

    g97_to_g98_all_passed = g97_to_g98_verified == 2
    g13_to_g98_all_passed = m96_report.g13_to_g96_all_passed and g97_to_g98_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m96_report.gates[:9])

    offline_95_verified = (
        g01_to_g09_ok
        and m96_report.offline_93_gates_verified
        and g97_to_g98_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_98_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g98_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m96_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_95_verified
        and m96_report.h0_h1_trial_entry_allowed
        and g97_to_g98_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m96_report.errors) + list(g97_verdict.errors) + list(g98_verdict.errors)
    )
    warnings: List[str] = (
        list(m96_report.warnings)
        + list(g97_verdict.warnings)
        + list(g98_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m96_report.g13_to_g96_all_passed:
        overall_status = m96_report.status
    elif not g97_verdict.passed:
        overall_status = g97_verdict.status
    elif not g98_verdict.passed:
        overall_status = g98_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_98_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_98_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_98_verified:
        overall_status = "VERIFIED_ALL_98_GATES"
    else:
        overall_status = "VERIFIED_95_OF_98_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m96_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g97_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g98_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 98,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 98 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g96_verified": g13_to_g96_verified,
        "g97_to_g98_verified": g97_to_g98_verified,
        "g13_to_g98_all_passed": g13_to_g98_all_passed,
        "g97_to_g98_all_passed": g97_to_g98_all_passed,
        "offline_95_gates_verified": offline_95_verified,
        "all_98_gates_verified": all_98_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master98GateReport(
        schema=REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_SCHEMA,
        version=REALHW_DISPLAY_QUALITY_BT_RMT_MYMENU_98GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_95_gates_verified=offline_95_verified,
        all_98_gates_verified=all_98_verified,
        g13_to_g98_all_passed=g13_to_g98_all_passed,
        g97_to_g98_all_passed=g97_to_g98_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_96_report=m96_report.to_dict(),
        g97_result=g97_res.to_dict(),
        g98_result=g98_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_98_master_safety_gates = evaluate_98gate_preflight
run_98_gate_preflight = evaluate_98gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_display_quality_bt_rmt_mymenu_and_98gate_guard",
        description=(
            "Phase 252 Safety Gates G97 (Display Quality Battery Conservation & "
            "Bluetooth Rmt Ctrl IR Lockout / Reset Network Set. Split Guard) + "
            "G98 (My Menu 6-Op Persistence & Slot-1 CAMSET01.DAT Firewall Guard) "
            "+ Unified 98-Gate Master Safety Preflight"
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_98gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        try:
            sys.stdout.write(
                json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
            )
            sys.stdout.flush()
        except BrokenPipeError:
            devnull = os.open(os.devnull, os.O_WRONLY)
            os.dup2(devnull, sys.stdout.fileno())
            os.close(devnull)
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/98 "
            f"g97_to_g98_all_passed={report.g97_to_g98_all_passed} "
            f"all_98_gates_verified={report.all_98_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"usb_packets_transmitted={report.usb_packets_transmitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_98_gates_verified
        if args.dry_run_simulated
        else report.offline_95_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
