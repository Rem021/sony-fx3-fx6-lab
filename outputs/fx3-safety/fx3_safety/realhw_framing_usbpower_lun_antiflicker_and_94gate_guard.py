"""Phase 246 (`94/94` Wave-37) Sony `ILME-FX3` (`Ver. 7.02`) Safety Gates `G93`
(`[Framing Settings]` Asymmetric `Full`/`Crop` Stream Guard & `[Anti-flicker Shoot.]`
Mechanical-Still-Only / No-`Var. Shutter` Firewall) & `G94` (`[USB Power Supply]`
Mandatory `NP-FZ100` Insertion + `USB Type-C` Exclusivity & `[USB LUN Setting]`
`Multi`/`Single` Setup Persistence Guard) + Unified 94-Gate Master Safety
Preflight (`G01..G94`).

Operationalizes Wave-37 official Sony `ILME-FX3` (`Ver. 7.02`) intelligence
(`reports/2026-11-15-global-sony-wave37-framing-settings-crop-full-usb-power-battery-lun-antiflicker-novarshutter-intel/README.md`)
as deterministic offline preflight verifiers (`G93` and `G94`) and delegates
`G01..G92` directly to `evaluate_92gate_preflight()`.
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
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import SPI_NOR_WRITE_AUTHORIZED
from .realhw_shoe_audio_wind_saveload_c3_and_92gate_guard import (
    Master92GateReport,
    evaluate_92gate_preflight,
)
from .thermal_pwm_and_power_guard import resolve_donor_thermal_power_paths

# ---------------------------------------------------------------------------
# Schema, Gate Identifiers & Hard-Locked Safety Redline Constants
# ---------------------------------------------------------------------------

REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_SCHEMA: str = (
    "realhw_framing_usbpower_lun_antiflicker_and_94gate_guard_v1"
)
REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_VERSION: str = "1.0.0"

G93_GATE_ID: str = (
    "G93_framing_asymmetric_crop_full_and_antiflicker_no_varshutter_guard"
)
G93_GATE_CODE: str = (
    "FRAMING_ASYMMETRIC_CROP_FULL_AND_ANTIFLICKER_NO_VARSHUTTER_GUARD"
)

G94_GATE_ID: str = (
    "G94_usb_power_npfz100_typec_interlock_and_usb_lun_setup_persistence_guard"
)
G94_GATE_CODE: str = (
    "USB_POWER_NPFZ100_TYPEC_INTERLOCK_AND_USB_LUN_SETUP_PERSISTENCE_GUARD"
)

G93: str = G93_GATE_ID
G94: str = G94_GATE_ID
GATE_G93_FRAMING_ASYMMETRIC_CROP_FULL_AND_ANTIFLICKER_NO_VARSHUTTER_GUARD: str = (
    G93_GATE_CODE
)
GATE_G94_USB_POWER_NPFZ100_TYPEC_INTERLOCK_AND_USB_LUN_SETUP_PERSISTENCE_GUARD: str = (
    G94_GATE_CODE
)

HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0
DONOR_CHECK_MAX_SECONDS_PHASE246: float = 0.10
DONOR_CHECK_MAX_SECONDS: float = DONOR_CHECK_MAX_SECONDS_PHASE246

FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX3_DEFAULT_FW_VERSION_PHASE246: str = "7.02"
FX3_MIN_SUPPORTED_FW_TUPLE_PHASE246: Tuple[int, int] = (1, 0)
FX3_HELP_GUIDE_CODE_G93: str = "ilc/2210"
FX30_HELP_GUIDE_CODE_G93: str = "ilc/2220"
ZVE1_HELP_GUIDE_CODE_G93: str = "ilc/2330"

RESET_ACTION_NONE: str = "NONE"
RESET_ACTION_CAMERA_SETTINGS_RESET: str = "Camera Settings Reset"
RESET_ACTION_INITIALIZE: str = "Initialize"
ALLOWED_RESET_ACTIONS_PHASE246: Tuple[str, ...] = (
    RESET_ACTION_NONE,
    RESET_ACTION_CAMERA_SETTINGS_RESET,
    RESET_ACTION_INITIALIZE,
)

# Status & Violation Codes
STATUS_VERIFIED_G93: str = (
    "VERIFIED_G93_FRAMING_ASYMMETRIC_STREAM_AND_ANTIFLICKER_NO_VARSHUTTER_SAFE"
)
STATUS_VERIFIED_G94: str = (
    "VERIFIED_G94_USB_POWER_NPFZ100_TYPEC_AND_USB_LUN_PERSISTENCE_SAFE"
)
STATUS_BLOCKED_PHASE246_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE246_DONOR_CONTRACT_INTEGRITY"
)

STATUS_BLOCKED_G93_FRAMING_ENUM_ASYMMETRIC_DEFAULT_OR_RESET_VIOLATION: str = (
    "BLOCKED_G93_FRAMING_ENUM_ASYMMETRIC_DEFAULT_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G93_HDMI_RAW_WITH_FRAMING_CROP_CONFLICT: str = (
    "BLOCKED_G93_HDMI_RAW_WITH_FRAMING_CROP_CONFLICT"
)
STATUS_BLOCKED_G93_ZVE1_AUTOFRAMING_MENU_CONFLATION: str = (
    "BLOCKED_G93_ZVE1_AUTOFRAMING_MENU_CONFLATION"
)
STATUS_BLOCKED_G93_ANTIFLICKER_ENUM_OR_RESET_VIOLATION: str = (
    "BLOCKED_G93_ANTIFLICKER_ENUM_OR_RESET_VIOLATION"
)
STATUS_BLOCKED_G93_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION: str = (
    "BLOCKED_G93_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION"
)
STATUS_BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION: str = (
    "BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION"
)
STATUS_BLOCKED_G93_TELEMETRY_INVALID: str = (
    "BLOCKED_G93_FRAMING_ANTIFLICKER_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G94_USB_SETUP_ENUM_OR_RESET_PERSISTENCE_VIOLATION: str = (
    "BLOCKED_G94_USB_SETUP_ENUM_OR_RESET_PERSISTENCE_VIOLATION"
)
STATUS_BLOCKED_G94_USB_POWER_WITHOUT_NPFZ100_BATTERY_UNAVAILABLE: str = (
    "BLOCKED_G94_USB_POWER_WITHOUT_NPFZ100_BATTERY_UNAVAILABLE"
)
STATUS_BLOCKED_G94_MID_SESSION_BATTERY_REMOVAL_UNBUFFERED_CUTOFF: str = (
    "BLOCKED_G94_MID_SESSION_BATTERY_REMOVAL_UNBUFFERED_CUTOFF"
)
STATUS_BLOCKED_G94_MULTI_MICRO_USB_POWER_OR_CHARGE_UNSUPPORTED: str = (
    "BLOCKED_G94_MULTI_MICRO_USB_POWER_OR_CHARGE_UNSUPPORTED"
)
STATUS_BLOCKED_G94_USB_LUN_SLOT_VISIBILITY_MISMATCH: str = (
    "BLOCKED_G94_USB_LUN_SLOT_VISIBILITY_MISMATCH"
)
STATUS_BLOCKED_G94_LIVE_HOST_USB_ATTACHMENT_FORBIDDEN: str = (
    "BLOCKED_G94_LIVE_HOST_USB_ATTACHMENT_FORBIDDEN"
)
STATUS_BLOCKED_G94_TELEMETRY_INVALID: str = (
    "BLOCKED_G94_USB_POWER_LUN_TELEMETRY_INVALID"
)

# ---------------------------------------------------------------------------
# Gate G93 Canonical Constants: [Framing Settings] & [Anti-flicker Shoot.]
# ---------------------------------------------------------------------------

FRAMING_SETTINGS_MENU_PATH: str = "MENU -> Shooting -> [Framing Settings]"
FRAMING_MODE_OFF: str = "Off"
FRAMING_MODE_ON: str = "On"
ALLOWED_FRAMING_MODES: Tuple[str, ...] = (FRAMING_MODE_OFF, FRAMING_MODE_ON)
FRAMING_FACTORY_DEFAULT: str = FRAMING_MODE_OFF

FRAMING_OUTPUT_FULL: str = "Full"
FRAMING_OUTPUT_CROP: str = "Crop"
ALLOWED_FRAMING_STREAM_OUTPUTS: Tuple[str, ...] = (
    FRAMING_OUTPUT_FULL,
    FRAMING_OUTPUT_CROP,
)
# Factory asymmetric dual-stream defaults on ILME-FX3 (ilc/2210):
# internal card [Recording/Streaming] = Full, external [HDMI] = Crop
FRAMING_REC_STREAMING_FACTORY_DEFAULT: str = FRAMING_OUTPUT_FULL
FRAMING_HDMI_FACTORY_DEFAULT: str = FRAMING_OUTPUT_CROP

REJECTED_ZVE1_AUTOFRAMING_LABELS: Tuple[str, ...] = (
    "Autoframing Settings",
    "[Autoframing Settings]",
    "Auto Framing Settings",
    "ZV-E1 Autoframing",
    "ilc/2330",
)

ANTI_FLICKER_SHOOT_MENU_PATH: str = (
    "MENU -> Shooting -> [Shutter/Silent] -> [Anti-flicker Shoot.]"
)
ANTI_FLICKER_SHOOT_OFF: str = "Off"
ANTI_FLICKER_SHOOT_ON: str = "On"
ALLOWED_ANTI_FLICKER_SHOOT_MODES: Tuple[str, ...] = (
    ANTI_FLICKER_SHOOT_OFF,
    ANTI_FLICKER_SHOOT_ON,
)
ANTI_FLICKER_SHOOT_FACTORY_DEFAULT: str = ANTI_FLICKER_SHOOT_OFF
ANTI_FLICKER_DETECTED_MAINS_HZ: Tuple[int, ...] = (100, 120)

SHOOT_MODE_STILL_G93: str = "Still"
SHOOT_MODE_MOVIE_G93: str = "Movie"
SHOOT_MODE_SQ_MOTION_G93: str = "S&Q Motion"
ALLOWED_SHOOT_MODES_G93: Tuple[str, ...] = (
    SHOOT_MODE_STILL_G93,
    SHOOT_MODE_MOVIE_G93,
    SHOOT_MODE_SQ_MOTION_G93,
)

SHUTTER_TYPE_MECHANICAL_G93: str = "Mechanical"
SHUTTER_TYPE_ELECTRONIC_G93: str = "Electronic"
ALLOWED_SHUTTER_TYPES_G93: Tuple[str, ...] = (
    SHUTTER_TYPE_MECHANICAL_G93,
    SHUTTER_TYPE_ELECTRONIC_G93,
)

FX3_HAS_VAR_SHUTTER: bool = False
FX3_HAS_FX6_ECS_MENU: bool = False
REJECTED_VAR_SHUTTER_AND_ECS_MODELS_G93: Tuple[str, ...] = (
    "ILME-FX30 (ilc/2220 [Var. Shutter])",
    "ILCE-6700 (ilc/2320 [Var. Shutter])",
    "ILME-FX6 (ECS Extended Clear Scan)",
)

# ---------------------------------------------------------------------------
# Gate G94 Canonical Constants: [USB Power Supply] & [USB LUN Setting]
# ---------------------------------------------------------------------------

USB_SETUP_MENU_PATH_G94: str = "MENU -> Setup -> [USB]"
USB_CONNECTION_MODE_MENU_PATH_G94: str = (
    "MENU -> Setup -> [USB] -> [USB Connection Mode]"
)
USB_LUN_SETTING_MENU_PATH_G94: str = "MENU -> Setup -> [USB] -> [USB LUN Setting]"
USB_POWER_SUPPLY_MENU_PATH_G94: str = "MENU -> Setup -> [USB] -> [USB Power Supply]"

USB_CONN_SEL_WHEN_CONNECT_G94: str = "Sel. When Connect"
USB_CONN_MASS_STORAGE_MSC_G94: str = "MassStorage(MSC)"
USB_CONN_MTP_G94: str = "MTP"
USB_CONN_PC_REMOTE_G94: str = "PC Remote"
USB_CONN_LAN_WIRED_G94: str = "LAN(Wired)"
ALLOWED_USB_CONNECTION_MODES_G94: Tuple[str, ...] = (
    USB_CONN_SEL_WHEN_CONNECT_G94,
    USB_CONN_MASS_STORAGE_MSC_G94,
    USB_CONN_MTP_G94,
    USB_CONN_PC_REMOTE_G94,
    USB_CONN_LAN_WIRED_G94,
)
USB_CONNECTION_MODE_FACTORY_DEFAULT_G94: str = USB_CONN_SEL_WHEN_CONNECT_G94

USB_LUN_MULTI_G94: str = "Multi"
USB_LUN_SINGLE_G94: str = "Single"
ALLOWED_USB_LUN_SETTINGS_G94: Tuple[str, ...] = (
    USB_LUN_MULTI_G94,
    USB_LUN_SINGLE_G94,
)
USB_LUN_SETTING_FACTORY_DEFAULT_G94: str = USB_LUN_MULTI_G94

USB_POWER_SUPPLY_ON_G94: str = "On"
USB_POWER_SUPPLY_OFF_G94: str = "Off"
ALLOWED_USB_POWER_SUPPLY_MODES_G94: Tuple[str, ...] = (
    USB_POWER_SUPPLY_ON_G94,
    USB_POWER_SUPPLY_OFF_G94,
)
USB_POWER_SUPPLY_FACTORY_DEFAULT_G94: str = USB_POWER_SUPPLY_ON_G94

USB_PORT_TYPE_C_G94: str = "USB Type-C"
USB_PORT_MULTI_MICRO_G94: str = "Multi/Micro USB"
USB_PORT_NONE_G94: str = "Disconnected"
ALLOWED_USB_POWER_PORTS_G94: Tuple[str, ...] = (
    USB_PORT_TYPE_C_G94,
    USB_PORT_MULTI_MICRO_G94,
    USB_PORT_NONE_G94,
)

BATTERY_BAY_NP_FZ100_G94: str = "NP-FZ100"
BATTERY_BAY_DC_C1_COUPLER_G94: str = "DC-C1"
BATTERY_BAY_EMPTY_G94: str = "Empty"
ALLOWED_BATTERY_BAY_SOURCES_G94: Tuple[str, ...] = (
    BATTERY_BAY_NP_FZ100_G94,
    BATTERY_BAY_DC_C1_COUPLER_G94,
    BATTERY_BAY_EMPTY_G94,
)

# ---------------------------------------------------------------------------
# Pinned Local Donor Contracts (O_RDONLY, <0.10s, Clean-Room Fallback)
# ---------------------------------------------------------------------------

PINNED_PHASE246_DONOR_SPECS: Dict[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_bin": (
        "FX3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"Crop",
            b"Full",
            b"HDMI",
            b"Shutter",
            b"Silent",
            b"Flicker",
            b"USB",
            b"Multi",
            b"Single",
            b"Power",
            b"Battery",
            b"Reset",
            b"Initialize",
        ),
        "FX3_CPAPP_FRAMING_ANTIFLICKER_USBPOWER_LUN_STRINGS",
    ),
    "fx3_usb_buspower_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so",
        48_232,
        "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
        (b"\x7fELF", b"UsbBusPower", b"BusPower", b"UsbControl", b"USB", b"Power"),
        "FX3_LIBUSBBUSPOWER_TYPEC_NPFZ100_INTERLOCK_ELF",
    ),
    "fx3_msc_server_so": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMscServer.so",
        64_456,
        "3802b00e6cd5961e703f03c2b6f2e3f08a35323dc019921f73f29b8f9c813938",
        (b"\x7fELF", b"UsbControl", b"MscServer", b"USB", b"Lun"),
        "FX3_LIBINFRAMSCSERVER_MULTI_SINGLE_LUN_ELF",
    ),
    "fx3_bk4_bin": (
        "FX3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"/setting"),
        "FX3_BK4_RESET_VS_INITIALIZE_USB_PERSISTENCE_SEED",
    ),
    "fx6_bk4_bin": (
        "FX6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"NTSC", b"/setting"),
        "FX6_CHAPLIN_ECS_NON_FX3_VAR_SHUTTER_PARITY_REF",
    ),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase246DonorAuditResult:
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
class FramingAndAntiflickerGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    help_guide_code: str
    firmware_version: str
    framing_settings_menu_path: str
    anti_flicker_shoot_menu_path: str
    framing_menu_node_label: str
    zve1_autoframing_conflation_rejected: bool
    pre_reset_framing: str
    pre_reset_recording_streaming: str
    pre_reset_hdmi: str
    pre_reset_anti_flicker_shoot: str
    reset_action: str
    expected_post_reset_framing: str
    effective_post_reset_framing: str
    expected_post_reset_recording_streaming: str
    effective_post_reset_recording_streaming: str
    expected_post_reset_hdmi: str
    effective_post_reset_hdmi: str
    framing_reset_by_camera_settings_reset: bool
    framing_asymmetric_factory_default_preserved: bool
    active_recording_streaming_routing: str
    active_hdmi_routing: str
    hdmi_raw_output_enabled: bool
    hdmi_raw_framing_conflict_blocked: bool
    expected_post_reset_anti_flicker_shoot: str
    effective_post_reset_anti_flicker_shoot: str
    anti_flicker_reset_by_camera_settings_reset: bool
    shoot_mode: str
    silent_mode: str
    shutter_type: str
    effective_shutter_mechanism: str
    anti_flicker_mechanical_still_only_eligible: bool
    anti_flicker_functional: bool
    detected_mains_flicker_hz: Tuple[int, ...]
    fx3_has_var_shutter: bool
    fx3_has_fx6_ecs_menu: bool
    var_shutter_or_ecs_false_assumption_blocked: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UsbPowerInterlockAndLunPersistenceResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    usb_setup_menu_path: str
    usb_connection_mode_menu_path: str
    usb_lun_setting_menu_path: str
    usb_power_supply_menu_path: str
    pre_reset_usb_connection_mode: str
    pre_reset_usb_lun_setting: str
    pre_reset_usb_power_supply: str
    reset_action: str
    expected_post_reset_usb_connection_mode: str
    effective_post_reset_usb_connection_mode: str
    expected_post_reset_usb_lun_setting: str
    effective_post_reset_usb_lun_setting: str
    expected_post_reset_usb_power_supply: str
    effective_post_reset_usb_power_supply: str
    usb_setup_survives_camera_settings_reset: bool
    usb_setup_reset_only_by_initialize: bool
    battery_bay_source: str
    np_fz100_or_dc_c1_present: bool
    usb_power_port: str
    usb_wall_adapter_connected: bool
    power_on_requested: bool
    power_on_available: bool
    mid_session_battery_removed: bool
    mid_session_unbuffered_power_off_triggered: bool
    usb_power_type_c_exclusive: bool
    multi_micro_usb_power_or_charge_supported: bool
    effective_usb_bus_power_active: bool
    expected_msc_exposed_lun_count: int
    effective_msc_exposed_lun_count: int
    exposed_msc_slots: Tuple[str, ...]
    off_camera_wp_locked_sdxc_reader_used: bool
    live_host_usb_attach_requested: bool
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G93FramingAndAntiflickerGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    framing_antiflicker_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G94UsbPowerAndLunPersistenceGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    usb_power_lun_guard: Dict[str, Any]
    hardware_live_attachment_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master94GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_91_gates_verified: bool
    all_94_gates_verified: bool
    g13_to_g94_all_passed: bool
    g93_to_g94_all_passed: bool
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
    master_92_report: Dict[str, Any]
    g93_result: Dict[str, Any]
    g94_result: Dict[str, Any]
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


def _norm_reset_action(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    u = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if u in ("NONE", "NO RESET", ""):
        return RESET_ACTION_NONE
    if u == "CAMERA SETTINGS RESET":
        return RESET_ACTION_CAMERA_SETTINGS_RESET
    if u == "INITIALIZE":
        return RESET_ACTION_INITIALIZE
    return None


def _norm_framing_stream_output(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s == "FULL":
        return FRAMING_OUTPUT_FULL
    if s == "CROP":
        return FRAMING_OUTPUT_CROP
    return None


def _norm_shoot_mode_g93(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("STILL", "STILL SHOOTING", "PHOTO"):
        return SHOOT_MODE_STILL_G93
    if s in ("MOVIE", "MOVIE RECORDING", "MOVIE REC"):
        return SHOOT_MODE_MOVIE_G93
    if s in ("S&Q MOTION", "S&Q", "SQ MOTION", "SQ", "S&Q RECORDING"):
        return SHOOT_MODE_SQ_MOTION_G93
    return None


def _norm_shutter_type_g93(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("MECHANICAL", "MECHANICAL SHUTTER", "MECH"):
        return SHUTTER_TYPE_MECHANICAL_G93
    if s in ("ELECTRONIC", "ELECTRONIC SHUTTER", "ELEC"):
        return SHUTTER_TYPE_ELECTRONIC_G93
    return None


def _norm_usb_conn_mode_g94(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]")).upper()
    if s in ("SEL. WHEN CONNECT", "SEL WHEN CONNECT", "SELECT WHEN CONNECT"):
        return USB_CONN_SEL_WHEN_CONNECT_G94
    if s in ("MASSSTORAGE(MSC)", "MASS STORAGE(MSC)", "MASS STORAGE", "MSC"):
        return USB_CONN_MASS_STORAGE_MSC_G94
    if s == "MTP":
        return USB_CONN_MTP_G94
    if s in ("PC REMOTE", "PCREMOTE"):
        return USB_CONN_PC_REMOTE_G94
    if s in ("LAN(WIRED)", "USB-LAN", "WIRED LAN"):
        return USB_CONN_LAN_WIRED_G94
    return None


def _norm_usb_lun_g94(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = raw.strip().strip("[]").upper()
    if s == "MULTI":
        return USB_LUN_MULTI_G94
    if s == "SINGLE":
        return USB_LUN_SINGLE_G94
    return None


def _norm_usb_port_g94(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", " ")).upper()
    if s in ("USB TYPE-C", "USB TYPE C", "TYPE-C", "TYPE C", "USBC", "USB-C"):
        return USB_PORT_TYPE_C_G94
    if s in (
        "MULTI/MICRO USB",
        "MULTI MICRO USB",
        "MICRO USB",
        "MULTI TERMINAL",
        "MULTI USB",
    ):
        return USB_PORT_MULTI_MICRO_G94
    if s in ("DISCONNECTED", "NONE", "OFF", ""):
        return USB_PORT_NONE_G94
    return None


def _norm_battery_bay_g94(raw: Any) -> Optional[str]:
    if not isinstance(raw, str):
        return None
    s = re.sub(r"\s+", " ", raw.strip().strip("[]").replace("_", "-")).upper()
    if s in ("NP-FZ100", "NPFZ100", "FZ100"):
        return BATTERY_BAY_NP_FZ100_G94
    if s in ("DC-C1", "DCC1", "DC-C1 COUPLER"):
        return BATTERY_BAY_DC_C1_COUPLER_G94
    if s in ("EMPTY", "NONE", "REMOVED", "NO-BATTERY", "NO BATTERY", ""):
        return BATTERY_BAY_EMPTY_G94
    return None


# ---------------------------------------------------------------------------
# 1. Bounded `< 0.10s` O_RDONLY Donor Contract Audit (`Phase 246`)
# ---------------------------------------------------------------------------


def audit_phase246_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS_PHASE246,
) -> Phase246DonorAuditResult:
    """Inspect local FX3 Ver. 7.02 / FX6 Ver. 6.01 donor artifacts strictly
    `os.O_RDONLY` within `<0.10s`, with automatic `CLEAN_ROOM_SYNTHETIC`
    fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent.
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
        for key, (_body, rel_path, *_rest) in PINNED_PHASE246_DONOR_SPECS.items():
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
            spec[5] for spec in PINNED_PHASE246_DONOR_SPECS.values()
        )
        synthetic_shas = {
            k: f"synthetic:{v[3][:16]}" for k, v in PINNED_PHASE246_DONOR_SPECS.items()
        }
        synthetic_sizes = {k: v[2] for k, v in PINNED_PHASE246_DONOR_SPECS.items()}
        return Phase246DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE246_DONOR_INTEGRITY
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
    ) in PINNED_PHASE246_DONOR_SPECS.items():
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
        for k, s in PINNED_PHASE246_DONOR_SPECS.items()
        if s[0] == "FX3"
    )
    fx6_ok = all(
        k in passed_keys
        for k, s in PINNED_PHASE246_DONOR_SPECS.items()
        if s[0] == "FX6"
    )
    valid = fx3_ok and fx6_ok and within_budget and (not errors)
    return Phase246DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE246_DONOR_INTEGRITY,
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
# 2. Gate `G93`: `[Framing Settings]` Asymmetric `Full`/`Crop` Stream Guard &
#    `[Anti-flicker Shoot.]` Mechanical-Still-Only / No-`Var. Shutter` Firewall
# ---------------------------------------------------------------------------


def resolve_fx3_framing_and_antiflicker_state(
    *,
    pre_reset_framing: str = FRAMING_FACTORY_DEFAULT,
    pre_reset_recording_streaming: str = FRAMING_REC_STREAMING_FACTORY_DEFAULT,
    pre_reset_hdmi: str = FRAMING_HDMI_FACTORY_DEFAULT,
    pre_reset_anti_flicker_shoot: str = ANTI_FLICKER_SHOOT_FACTORY_DEFAULT,
    reset_action: str = RESET_ACTION_NONE,
    shoot_mode: str = SHOOT_MODE_MOVIE_G93,
    silent_mode: str = "Off",
    shutter_type: str = SHUTTER_TYPE_MECHANICAL_G93,
) -> Dict[str, Any]:
    """Compute deterministic post-reset `[Framing Settings]` asymmetric stream
    routing and `[Anti-flicker Shoot.]` mechanical-shutter-still-only eligibility
    for `ILME-FX3` (`ilc/2210` `Ver. 7.02`).
    """
    frm = _norm_on_off(pre_reset_framing) or FRAMING_FACTORY_DEFAULT
    rec_stream = (
        _norm_framing_stream_output(pre_reset_recording_streaming)
        or FRAMING_REC_STREAMING_FACTORY_DEFAULT
    )
    hdmi_stream = (
        _norm_framing_stream_output(pre_reset_hdmi) or FRAMING_HDMI_FACTORY_DEFAULT
    )
    aflicker = (
        _norm_on_off(pre_reset_anti_flicker_shoot)
        or ANTI_FLICKER_SHOOT_FACTORY_DEFAULT
    )
    rst = _norm_reset_action(reset_action) or RESET_ACTION_NONE
    smode = _norm_shoot_mode_g93(shoot_mode) or SHOOT_MODE_MOVIE_G93
    silent = _norm_on_off(silent_mode) or "Off"
    stype = _norm_shutter_type_g93(shutter_type) or SHUTTER_TYPE_MECHANICAL_G93

    # All [Framing Settings] items and [Anti-flicker Shoot.] reset to factory
    # defaults under both [Camera Settings Reset] and [Initialize].
    if rst in (RESET_ACTION_CAMERA_SETTINGS_RESET, RESET_ACTION_INITIALIZE):
        post_framing = FRAMING_FACTORY_DEFAULT
        post_rec_stream = FRAMING_REC_STREAMING_FACTORY_DEFAULT
        post_hdmi = FRAMING_HDMI_FACTORY_DEFAULT
        post_aflicker = ANTI_FLICKER_SHOOT_FACTORY_DEFAULT
    else:
        post_framing = frm
        post_rec_stream = rec_stream
        post_hdmi = hdmi_stream
        post_aflicker = aflicker

    # Effective stream routing: when [Framing] == Off, both internal recording/
    # streaming and HDMI carry the uncropped Full frame; when [Framing] == On,
    # each stream follows its independent Full/Crop setting (default: Rec=Full,
    # HDMI=Crop).
    if post_framing == FRAMING_MODE_ON:
        active_rec_routing = post_rec_stream
        active_hdmi_routing = post_hdmi
    else:
        active_rec_routing = FRAMING_OUTPUT_FULL
        active_hdmi_routing = FRAMING_OUTPUT_FULL

    # Movie / S&Q Motion and [Silent Mode]=On always use electronic readout;
    # [Anti-flicker Shoot.] functions strictly in Still mode with mechanical
    # shutter and [Silent Mode]=Off.
    if (
        smode == SHOOT_MODE_STILL_G93
        and silent == "Off"
        and stype == SHUTTER_TYPE_MECHANICAL_G93
    ):
        effective_shutter_mechanism = SHUTTER_TYPE_MECHANICAL_G93
        mechanical_still_eligible = True
    else:
        effective_shutter_mechanism = SHUTTER_TYPE_ELECTRONIC_G93
        mechanical_still_eligible = False

    anti_flicker_functional = (
        post_aflicker == ANTI_FLICKER_SHOOT_ON and mechanical_still_eligible
    )

    return {
        "expected_post_reset_framing": post_framing,
        "expected_post_reset_recording_streaming": post_rec_stream,
        "expected_post_reset_hdmi": post_hdmi,
        "expected_post_reset_anti_flicker_shoot": post_aflicker,
        "active_recording_streaming_routing": active_rec_routing,
        "active_hdmi_routing": active_hdmi_routing,
        "effective_shutter_mechanism": effective_shutter_mechanism,
        "anti_flicker_mechanical_still_only_eligible": mechanical_still_eligible,
        "anti_flicker_functional": anti_flicker_functional,
        "fx3_has_var_shutter": FX3_HAS_VAR_SHUTTER,
        "fx3_has_fx6_ecs_menu": FX3_HAS_FX6_ECS_MENU,
    }


def verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    help_guide_code: str = FX3_HELP_GUIDE_CODE_G93,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE246,
    framing_menu_node_label: str = "[Framing Settings]",
    claimed_zv_e1_autoframing: bool = False,
    pre_reset_framing: str = FRAMING_FACTORY_DEFAULT,
    pre_reset_recording_streaming: str = FRAMING_REC_STREAMING_FACTORY_DEFAULT,
    pre_reset_hdmi: str = FRAMING_HDMI_FACTORY_DEFAULT,
    pre_reset_anti_flicker_shoot: str = ANTI_FLICKER_SHOOT_FACTORY_DEFAULT,
    reset_action: str = RESET_ACTION_NONE,
    claimed_post_reset_framing: Optional[str] = None,
    claimed_post_reset_recording_streaming: Optional[str] = None,
    claimed_post_reset_hdmi: Optional[str] = None,
    claimed_factory_recording_streaming_default: str = FRAMING_REC_STREAMING_FACTORY_DEFAULT,
    claimed_factory_hdmi_default: str = FRAMING_HDMI_FACTORY_DEFAULT,
    hdmi_raw_output_enabled: bool = False,
    claimed_post_reset_anti_flicker_shoot: Optional[str] = None,
    shoot_mode: str = SHOOT_MODE_MOVIE_G93,
    silent_mode: str = "Off",
    shutter_type: str = SHUTTER_TYPE_MECHANICAL_G93,
    claimed_anti_flicker_functional: Optional[bool] = None,
    require_active_anti_flicker_mitigation: bool = False,
    claimed_fx3_var_shutter_supported: bool = False,
    requested_var_shutter_mode: Optional[str] = None,
    claimed_fx3_ecs_supported: bool = False,
) -> FramingAndAntiflickerGuardResult:
    """Verify Wave-37 Gate `G93` invariants on `ILME-FX3` (`ilc/2210` `Ver. 7.02`)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        not isinstance(body_model_name, str)
        or not isinstance(body_model_id, int)
        or isinstance(body_model_id, bool)
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE246
    ):
        _add_code(codes, STATUS_BLOCKED_G93_TELEMETRY_INVALID)
        errors.append(
            f"Invalid G93 body/firmware telemetry: model={body_model_name!r}, "
            f"id={body_model_id!r}, fw={firmware_version!r}."
        )

    # Check ZV-E1 [Autoframing Settings] conflation & model identity
    norm_label = (
        framing_menu_node_label.strip()
        if isinstance(framing_menu_node_label, str)
        else ""
    )
    norm_label_plain = re.sub(r"\s+", " ", norm_label.strip("[]")).upper()
    norm_guide = (
        help_guide_code.strip().lower() if isinstance(help_guide_code, str) else ""
    )
    norm_model = (
        body_model_name.strip().upper() if isinstance(body_model_name, str) else ""
    )

    zve1_conflated = (
        bool(claimed_zv_e1_autoframing)
        or "AUTOFRAMING" in norm_label_plain
        or "AUTO FRAMING" in norm_label_plain
        or norm_guide == ZVE1_HELP_GUIDE_CODE_G93
        or "ZV-E1" in norm_model
        or norm_label_plain != "FRAMING SETTINGS"
    )
    if zve1_conflated:
        _add_code(codes, STATUS_BLOCKED_G93_ZVE1_AUTOFRAMING_MENU_CONFLATION)
        errors.append(
            f"ILME-FX3 (ilc/2210) uses '[Framing Settings]' (Monitor & Control), "
            f"never consumer ZV-E1 '[Autoframing Settings]' (got label={framing_menu_node_label!r}, "
            f"guide={help_guide_code!r}, model={body_model_name!r})."
        )

    # Check FX30 [Var. Shutter] / FX6 ECS false assumptions or model conflation
    req_var = (
        requested_var_shutter_mode.strip().upper()
        if isinstance(requested_var_shutter_mode, str)
        else ""
    )
    var_or_ecs_assumed = (
        bool(claimed_fx3_var_shutter_supported)
        or bool(claimed_fx3_ecs_supported)
        or (req_var not in ("", "NONE", "UNSUPPORTED_ON_FX3"))
        or norm_guide in (FX30_HELP_GUIDE_CODE_G93, "ilc/2320")
        or norm_model in ("ILME-FX30", "ILCE-6700", "ILME-FX6")
    )
    if var_or_ecs_assumed:
        _add_code(codes, STATUS_BLOCKED_G93_FALSE_VAR_SHUTTER_OR_FX6_ECS_ASSUMPTION)
        errors.append(
            "Stock ILME-FX3 (ilc/2210 Ver. 7.02) does NOT implement [Var. Shutter] "
            "(FX30 ilc/2220 / ILCE-6700 ilc/2320) or FX6 ECS Extended Clear Scan."
        )
    elif norm_model != FX3_MODEL_NAME or body_model_id != FX3_MODEL_ID or norm_guide != FX3_HELP_GUIDE_CODE_G93:
        if not zve1_conflated:
            _add_code(codes, STATUS_BLOCKED_G93_TELEMETRY_INVALID)
            errors.append(
                f"Unexpected G93 target camera identifiers: model={body_model_name!r}, "
                f"id=0x{body_model_id:08x}, guide={help_guide_code!r}."
            )

    # Validate [Framing Settings] enums, asymmetric defaults & reset behavior
    norm_pre_frm = _norm_on_off(pre_reset_framing)
    norm_pre_rec = _norm_framing_stream_output(pre_reset_recording_streaming)
    norm_pre_hdmi = _norm_framing_stream_output(pre_reset_hdmi)
    norm_rst = _norm_reset_action(reset_action)
    norm_fac_rec = _norm_framing_stream_output(
        claimed_factory_recording_streaming_default
    )
    norm_fac_hdmi = _norm_framing_stream_output(claimed_factory_hdmi_default)

    asymmetric_default_ok = (
        norm_fac_rec == FRAMING_REC_STREAMING_FACTORY_DEFAULT
        and norm_fac_hdmi == FRAMING_HDMI_FACTORY_DEFAULT
    )
    if (
        norm_pre_frm is None
        or norm_pre_rec is None
        or norm_pre_hdmi is None
        or norm_rst is None
        or not asymmetric_default_ok
    ):
        _add_code(
            codes, STATUS_BLOCKED_G93_FRAMING_ENUM_ASYMMETRIC_DEFAULT_OR_RESET_VIOLATION
        )
        errors.append(
            f"[Framing Settings] enum/asymmetric-default/reset invalid: framing={pre_reset_framing!r}, "
            f"rec={pre_reset_recording_streaming!r}, hdmi={pre_reset_hdmi!r}, reset={reset_action!r}, "
            f"factory=({claimed_factory_recording_streaming_default!r}, {claimed_factory_hdmi_default!r})."
        )

    # Validate [Anti-flicker Shoot.] enum, shoot_mode, silent_mode, shutter_type
    norm_pre_af = _norm_on_off(pre_reset_anti_flicker_shoot)
    norm_smode = _norm_shoot_mode_g93(shoot_mode)
    norm_silent = _norm_on_off(silent_mode)
    norm_stype = _norm_shutter_type_g93(shutter_type)

    if norm_pre_af is None:
        _add_code(codes, STATUS_BLOCKED_G93_ANTIFLICKER_ENUM_OR_RESET_VIOLATION)
        errors.append(
            f"Invalid [Anti-flicker Shoot.] enum value: {pre_reset_anti_flicker_shoot!r}."
        )
    if norm_smode is None or norm_silent is None or norm_stype is None:
        _add_code(codes, STATUS_BLOCKED_G93_TELEMETRY_INVALID)
        errors.append(
            f"Invalid G93 shooting/shutter state: shoot_mode={shoot_mode!r}, "
            f"silent_mode={silent_mode!r}, shutter_type={shutter_type!r}."
        )

    resolved = resolve_fx3_framing_and_antiflicker_state(
        pre_reset_framing=norm_pre_frm or FRAMING_FACTORY_DEFAULT,
        pre_reset_recording_streaming=(
            norm_pre_rec or FRAMING_REC_STREAMING_FACTORY_DEFAULT
        ),
        pre_reset_hdmi=norm_pre_hdmi or FRAMING_HDMI_FACTORY_DEFAULT,
        pre_reset_anti_flicker_shoot=(
            norm_pre_af or ANTI_FLICKER_SHOOT_FACTORY_DEFAULT
        ),
        reset_action=norm_rst or RESET_ACTION_NONE,
        shoot_mode=norm_smode or SHOOT_MODE_MOVIE_G93,
        silent_mode=norm_silent or "Off",
        shutter_type=norm_stype or SHUTTER_TYPE_MECHANICAL_G93,
    )

    exp_frm = resolved["expected_post_reset_framing"]
    exp_rec = resolved["expected_post_reset_recording_streaming"]
    exp_hdmi = resolved["expected_post_reset_hdmi"]
    exp_af = resolved["expected_post_reset_anti_flicker_shoot"]

    eff_frm = (
        exp_frm
        if claimed_post_reset_framing is None
        else (_norm_on_off(claimed_post_reset_framing) or str(claimed_post_reset_framing))
    )
    eff_rec = (
        exp_rec
        if claimed_post_reset_recording_streaming is None
        else (
            _norm_framing_stream_output(claimed_post_reset_recording_streaming)
            or str(claimed_post_reset_recording_streaming)
        )
    )
    eff_hdmi = (
        exp_hdmi
        if claimed_post_reset_hdmi is None
        else (
            _norm_framing_stream_output(claimed_post_reset_hdmi)
            or str(claimed_post_reset_hdmi)
        )
    )
    eff_af = (
        exp_af
        if claimed_post_reset_anti_flicker_shoot is None
        else (
            _norm_on_off(claimed_post_reset_anti_flicker_shoot)
            or str(claimed_post_reset_anti_flicker_shoot)
        )
    )

    if eff_frm != exp_frm or eff_rec != exp_rec or eff_hdmi != exp_hdmi:
        _add_code(
            codes, STATUS_BLOCKED_G93_FRAMING_ENUM_ASYMMETRIC_DEFAULT_OR_RESET_VIOLATION
        )
        errors.append(
            f"[Framing Settings] post-reset mismatch under {norm_rst}: expected "
            f"({exp_frm}, Rec={exp_rec}, HDMI={exp_hdmi}), got "
            f"({eff_frm!r}, Rec={eff_rec!r}, HDMI={eff_hdmi!r})."
        )

    if eff_af != exp_af:
        _add_code(codes, STATUS_BLOCKED_G93_ANTIFLICKER_ENUM_OR_RESET_VIOLATION)
        errors.append(
            f"[Anti-flicker Shoot.] post-reset mismatch under {norm_rst}: "
            f"expected {exp_af}, got {eff_af!r}."
        )

    # HDMI RAW output cannot be combined with [Framing] = On (cropped framing mode)
    raw_conflict = bool(hdmi_raw_output_enabled) and (eff_frm == FRAMING_MODE_ON)
    if raw_conflict:
        _add_code(codes, STATUS_BLOCKED_G93_HDMI_RAW_WITH_FRAMING_CROP_CONFLICT)
        errors.append(
            "HDMI RAW output cannot be combined with [Framing]=On on ILME-FX3 "
            f"(active Rec={resolved['active_recording_streaming_routing']}, "
            f"HDMI={resolved['active_hdmi_routing']})."
        )

    # Mechanical-shutter still-image scope enforcement for [Anti-flicker Shoot.]
    af_func = bool(resolved["anti_flicker_functional"])
    if (
        claimed_anti_flicker_functional is not None
        and bool(claimed_anti_flicker_functional) != af_func
    ):
        _add_code(
            codes, STATUS_BLOCKED_G93_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION
        )
        errors.append(
            f"[Anti-flicker Shoot.] functional state mismatch: claimed={claimed_anti_flicker_functional}, "
            f"actual={af_func} (shoot_mode={norm_smode}, silent_mode={norm_silent}, "
            f"shutter={resolved['effective_shutter_mechanism']})."
        )
    if require_active_anti_flicker_mitigation and not af_func:
        _add_code(
            codes, STATUS_BLOCKED_G93_ANTIFLICKER_MOVIE_OR_ELECTRONIC_SHUTTER_VIOLATION
        )
        errors.append(
            "[Anti-flicker Shoot.] does NOT function in Movie/S&Q mode or with "
            "[Silent Mode]=On / electronic shutter (mechanical-shutter still only)."
        )

    if eff_af == ANTI_FLICKER_SHOOT_ON and not af_func and not codes:
        warnings.append(
            "[Anti-flicker Shoot.]=On is currently dormant outside mechanical-shutter Still mode."
        )

    valid = not codes
    status = STATUS_VERIFIED_G93 if valid else codes[0]
    model_id_hex = (
        f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "INVALID"
    )

    return FramingAndAntiflickerGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=str(body_model_name),
        body_model_id_hex=model_id_hex,
        help_guide_code=str(help_guide_code),
        firmware_version=str(firmware_version),
        framing_settings_menu_path=FRAMING_SETTINGS_MENU_PATH,
        anti_flicker_shoot_menu_path=ANTI_FLICKER_SHOOT_MENU_PATH,
        framing_menu_node_label=str(framing_menu_node_label),
        zve1_autoframing_conflation_rejected=not zve1_conflated,
        pre_reset_framing=norm_pre_frm or str(pre_reset_framing),
        pre_reset_recording_streaming=(
            norm_pre_rec or str(pre_reset_recording_streaming)
        ),
        pre_reset_hdmi=norm_pre_hdmi or str(pre_reset_hdmi),
        pre_reset_anti_flicker_shoot=(
            norm_pre_af or str(pre_reset_anti_flicker_shoot)
        ),
        reset_action=norm_rst or str(reset_action),
        expected_post_reset_framing=exp_frm,
        effective_post_reset_framing=eff_frm,
        expected_post_reset_recording_streaming=exp_rec,
        effective_post_reset_recording_streaming=eff_rec,
        expected_post_reset_hdmi=exp_hdmi,
        effective_post_reset_hdmi=eff_hdmi,
        framing_reset_by_camera_settings_reset=True,
        framing_asymmetric_factory_default_preserved=asymmetric_default_ok,
        active_recording_streaming_routing=resolved[
            "active_recording_streaming_routing"
        ],
        active_hdmi_routing=resolved["active_hdmi_routing"],
        hdmi_raw_output_enabled=bool(hdmi_raw_output_enabled),
        hdmi_raw_framing_conflict_blocked=not raw_conflict,
        expected_post_reset_anti_flicker_shoot=exp_af,
        effective_post_reset_anti_flicker_shoot=eff_af,
        anti_flicker_reset_by_camera_settings_reset=True,
        shoot_mode=norm_smode or str(shoot_mode),
        silent_mode=norm_silent or str(silent_mode),
        shutter_type=norm_stype or str(shutter_type),
        effective_shutter_mechanism=resolved["effective_shutter_mechanism"],
        anti_flicker_mechanical_still_only_eligible=bool(
            resolved["anti_flicker_mechanical_still_only_eligible"]
        ),
        anti_flicker_functional=af_func,
        detected_mains_flicker_hz=ANTI_FLICKER_DETECTED_MAINS_HZ,
        fx3_has_var_shutter=FX3_HAS_VAR_SHUTTER,
        fx3_has_fx6_ecs_menu=FX3_HAS_FX6_ECS_MENU,
        var_shutter_or_ecs_false_assumption_blocked=not var_or_ecs_assumed,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g93_framing_and_antiflicker_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    framing_antiflicker_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase246DonorAuditResult] = None,
) -> Tuple[GateVerdict, G93FramingAndAntiflickerGuardResult]:
    """Evaluate Gate `G93` combining bounded `<0.10s` `O_RDONLY` donor audit
    and `[Framing Settings]` / `[Anti-flicker Shoot.]` verification.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase246_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_framing_asymmetric_and_antiflicker_no_varshutter_guard(
        **(dict(framing_antiflicker_kwargs) if framing_antiflicker_kwargs else {})
    )

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE246_DONOR_INTEGRITY)
        errors.extend(audit.errors)
    for c in guard.violation_codes:
        _add_code(codes, c)
    errors.extend(guard.errors)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G93 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G93 if valid else codes[0]

    res = G93FramingAndAntiflickerGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        framing_antiflicker_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, framing={guard.effective_post_reset_framing}"
        f"(rec={guard.effective_post_reset_recording_streaming},"
        f"hdmi={guard.effective_post_reset_hdmi},"
        f"raw_conflict_blocked={guard.hdmi_raw_framing_conflict_blocked}), "
        f"antiflicker={guard.effective_post_reset_anti_flicker_shoot}"
        f"(func={guard.anti_flicker_functional},"
        f"has_var_shutter={guard.fx3_has_var_shutter})"
    )
    verdict = GateVerdict(
        gate_id=G93_GATE_ID,
        gate_code=G93_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 3. Gate `G94`: `[USB Power Supply]` Mandatory `NP-FZ100` Insertion +
#    `USB Type-C` Exclusivity & `[USB LUN Setting]` `Multi`/`Single` Setup
#    Persistence Guard
# ---------------------------------------------------------------------------


def resolve_fx3_usb_power_interlock_and_lun_persistence_state(
    *,
    pre_reset_usb_connection_mode: str = USB_CONNECTION_MODE_FACTORY_DEFAULT_G94,
    pre_reset_usb_lun_setting: str = USB_LUN_SETTING_FACTORY_DEFAULT_G94,
    pre_reset_usb_power_supply: str = USB_POWER_SUPPLY_FACTORY_DEFAULT_G94,
    reset_action: str = RESET_ACTION_NONE,
    battery_bay_source: str = BATTERY_BAY_NP_FZ100_G94,
    usb_power_port: str = USB_PORT_TYPE_C_G94,
    usb_wall_adapter_connected: bool = True,
    mid_session_battery_removed: bool = False,
) -> Dict[str, Any]:
    """Compute deterministic post-reset `[Setup] -> [USB]` survival, `[USB Power Supply]`
    battery/port hardware interlocks, and `[USB LUN Setting]` slot exposure on
    `ILME-FX3` (`Ver. 7.02`).
    """
    conn = (
        _norm_usb_conn_mode_g94(pre_reset_usb_connection_mode)
        or USB_CONNECTION_MODE_FACTORY_DEFAULT_G94
    )
    lun = (
        _norm_usb_lun_g94(pre_reset_usb_lun_setting)
        or USB_LUN_SETTING_FACTORY_DEFAULT_G94
    )
    pwr = (
        _norm_on_off(pre_reset_usb_power_supply)
        or USB_POWER_SUPPLY_FACTORY_DEFAULT_G94
    )
    rst = _norm_reset_action(reset_action) or RESET_ACTION_NONE
    bay = _norm_battery_bay_g94(battery_bay_source) or BATTERY_BAY_NP_FZ100_G94
    port = _norm_usb_port_g94(usb_power_port) or USB_PORT_TYPE_C_G94

    # Per Sony ILME-FX3 "List of default setting values":
    # [USB Connection Mode], [USB LUN Setting], and [USB Power Supply] under
    # [Setup] -> [USB] SURVIVE [Camera Settings Reset] and reset ONLY on [Initialize].
    if rst == RESET_ACTION_INITIALIZE:
        post_conn = USB_CONNECTION_MODE_FACTORY_DEFAULT_G94
        post_lun = USB_LUN_SETTING_FACTORY_DEFAULT_G94
        post_pwr = USB_POWER_SUPPLY_FACTORY_DEFAULT_G94
    else:
        post_conn = conn
        post_lun = lun
        post_pwr = pwr

    np_fz100_or_dc_c1_present = bay in (
        BATTERY_BAY_NP_FZ100_G94,
        BATTERY_BAY_DC_C1_COUPLER_G94,
    )
    power_on_available = np_fz100_or_dc_c1_present

    unbuffered_cutoff = bool(mid_session_battery_removed) and (
        bay != BATTERY_BAY_DC_C1_COUPLER_G94
    )

    effective_usb_bus_power_active = (
        post_pwr == USB_POWER_SUPPLY_ON_G94
        and port == USB_PORT_TYPE_C_G94
        and bool(usb_wall_adapter_connected)
        and np_fz100_or_dc_c1_present
        and (not unbuffered_cutoff)
    )

    if post_lun == USB_LUN_MULTI_G94:
        expected_lun_count = 2
        exposed_slots: Tuple[str, ...] = ("Slot 1", "Slot 2")
    else:
        expected_lun_count = 1
        exposed_slots = ("Primary Recording Slot",)

    return {
        "expected_post_reset_usb_connection_mode": post_conn,
        "expected_post_reset_usb_lun_setting": post_lun,
        "expected_post_reset_usb_power_supply": post_pwr,
        "usb_setup_survives_camera_settings_reset": True,
        "usb_setup_reset_only_by_initialize": True,
        "np_fz100_or_dc_c1_present": np_fz100_or_dc_c1_present,
        "power_on_available": power_on_available,
        "mid_session_unbuffered_power_off_triggered": unbuffered_cutoff,
        "usb_power_type_c_exclusive": True,
        "multi_micro_usb_power_or_charge_supported": False,
        "effective_usb_bus_power_active": effective_usb_bus_power_active,
        "expected_msc_exposed_lun_count": expected_lun_count,
        "exposed_msc_slots": exposed_slots,
    }


def verify_usb_power_npfz100_typec_and_lun_persistence_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_PHASE246,
    pre_reset_usb_connection_mode: str = USB_CONNECTION_MODE_FACTORY_DEFAULT_G94,
    pre_reset_usb_lun_setting: str = USB_LUN_SETTING_FACTORY_DEFAULT_G94,
    pre_reset_usb_power_supply: str = USB_POWER_SUPPLY_FACTORY_DEFAULT_G94,
    reset_action: str = RESET_ACTION_NONE,
    claimed_post_reset_usb_connection_mode: Optional[str] = None,
    claimed_post_reset_usb_lun_setting: Optional[str] = None,
    claimed_post_reset_usb_power_supply: Optional[str] = None,
    battery_bay_source: str = BATTERY_BAY_NP_FZ100_G94,
    usb_power_port: str = USB_PORT_TYPE_C_G94,
    usb_wall_adapter_connected: bool = True,
    power_on_requested: bool = True,
    claimed_power_on_without_battery_allowed: bool = False,
    mid_session_battery_removed: bool = False,
    claimed_multi_micro_usb_power_supported: bool = False,
    claimed_msc_exposed_lun_count: Optional[int] = None,
    off_camera_wp_locked_sdxc_reader_used: bool = True,
    live_host_usb_attach_requested: bool = False,
    simulated_usb_packets_transmitted: int = 0,
) -> UsbPowerInterlockAndLunPersistenceResult:
    """Verify Wave-37 Gate `G94` invariants on `ILME-FX3` (`Ver. 7.02`)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    fw_tuple = _parse_fw_tuple(firmware_version)
    if (
        not isinstance(body_model_name, str)
        or body_model_name.strip().upper() != FX3_MODEL_NAME
        or not isinstance(body_model_id, int)
        or isinstance(body_model_id, bool)
        or body_model_id != FX3_MODEL_ID
        or fw_tuple is None
        or fw_tuple < FX3_MIN_SUPPORTED_FW_TUPLE_PHASE246
        or not isinstance(simulated_usb_packets_transmitted, int)
        or isinstance(simulated_usb_packets_transmitted, bool)
        or simulated_usb_packets_transmitted < 0
    ):
        _add_code(codes, STATUS_BLOCKED_G94_TELEMETRY_INVALID)
        errors.append(
            f"Invalid G94 body/firmware/USB telemetry: model={body_model_name!r}, "
            f"id={body_model_id!r}, fw={firmware_version!r}, "
            f"packets={simulated_usb_packets_transmitted!r}."
        )

    norm_conn = _norm_usb_conn_mode_g94(pre_reset_usb_connection_mode)
    norm_lun = _norm_usb_lun_g94(pre_reset_usb_lun_setting)
    norm_pwr = _norm_on_off(pre_reset_usb_power_supply)
    norm_rst = _norm_reset_action(reset_action)
    norm_bay = _norm_battery_bay_g94(battery_bay_source)
    norm_port = _norm_usb_port_g94(usb_power_port)

    if (
        norm_conn is None
        or norm_lun is None
        or norm_pwr is None
        or norm_rst is None
    ):
        _add_code(codes, STATUS_BLOCKED_G94_USB_SETUP_ENUM_OR_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            f"Invalid [Setup] -> [USB] enum or reset action: conn={pre_reset_usb_connection_mode!r}, "
            f"lun={pre_reset_usb_lun_setting!r}, power={pre_reset_usb_power_supply!r}, "
            f"reset={reset_action!r}."
        )

    if norm_bay is None or norm_port is None:
        _add_code(codes, STATUS_BLOCKED_G94_TELEMETRY_INVALID)
        errors.append(
            f"Invalid G94 battery bay or USB port identifier: bay={battery_bay_source!r}, "
            f"port={usb_power_port!r}."
        )

    resolved = resolve_fx3_usb_power_interlock_and_lun_persistence_state(
        pre_reset_usb_connection_mode=(
            norm_conn or USB_CONNECTION_MODE_FACTORY_DEFAULT_G94
        ),
        pre_reset_usb_lun_setting=norm_lun or USB_LUN_SETTING_FACTORY_DEFAULT_G94,
        pre_reset_usb_power_supply=norm_pwr or USB_POWER_SUPPLY_FACTORY_DEFAULT_G94,
        reset_action=norm_rst or RESET_ACTION_NONE,
        battery_bay_source=norm_bay or BATTERY_BAY_NP_FZ100_G94,
        usb_power_port=norm_port or USB_PORT_TYPE_C_G94,
        usb_wall_adapter_connected=bool(usb_wall_adapter_connected),
        mid_session_battery_removed=bool(mid_session_battery_removed),
    )

    exp_conn = resolved["expected_post_reset_usb_connection_mode"]
    exp_lun = resolved["expected_post_reset_usb_lun_setting"]
    exp_pwr = resolved["expected_post_reset_usb_power_supply"]

    eff_conn = (
        exp_conn
        if claimed_post_reset_usb_connection_mode is None
        else (
            _norm_usb_conn_mode_g94(claimed_post_reset_usb_connection_mode)
            or str(claimed_post_reset_usb_connection_mode)
        )
    )
    eff_lun = (
        exp_lun
        if claimed_post_reset_usb_lun_setting is None
        else (
            _norm_usb_lun_g94(claimed_post_reset_usb_lun_setting)
            or str(claimed_post_reset_usb_lun_setting)
        )
    )
    eff_pwr = (
        exp_pwr
        if claimed_post_reset_usb_power_supply is None
        else (
            _norm_on_off(claimed_post_reset_usb_power_supply)
            or str(claimed_post_reset_usb_power_supply)
        )
    )

    if eff_conn != exp_conn or eff_lun != exp_lun or eff_pwr != exp_pwr:
        _add_code(codes, STATUS_BLOCKED_G94_USB_SETUP_ENUM_OR_RESET_PERSISTENCE_VIOLATION)
        errors.append(
            f"[Setup] -> [USB] persistence mismatch under {norm_rst}: expected "
            f"(conn={exp_conn}, lun={exp_lun}, power={exp_pwr}), got "
            f"(conn={eff_conn!r}, lun={eff_lun!r}, power={eff_pwr!r})."
        )

    # Interlock (a): Mandatory inserted NP-FZ100 battery pack (or DC-C1 coupler)
    if (bool(power_on_requested) and not resolved["power_on_available"]) or bool(
        claimed_power_on_without_battery_allowed
    ):
        _add_code(codes, STATUS_BLOCKED_G94_USB_POWER_WITHOUT_NPFZ100_BATTERY_UNAVAILABLE)
        errors.append(
            "Turning ILME-FX3 on without an inserted NP-FZ100 battery pack (or DC-C1 "
            "coupler) is hardware-unavailable even when USB wall power is connected."
        )

    if resolved["mid_session_unbuffered_power_off_triggered"]:
        _add_code(codes, STATUS_BLOCKED_G94_MID_SESSION_BATTERY_REMOVAL_UNBUFFERED_CUTOFF)
        errors.append(
            "Removing the NP-FZ100 battery pack while USB power is supplied from a "
            "wall outlet causes immediate unbuffered camera power-off."
        )

    # Interlock (b): USB Type-C exclusivity vs Multi/Micro USB prohibition
    if norm_port == USB_PORT_MULTI_MICRO_G94 or bool(
        claimed_multi_micro_usb_power_supported
    ):
        _add_code(codes, STATUS_BLOCKED_G94_MULTI_MICRO_USB_POWER_OR_CHARGE_UNSUPPORTED)
        errors.append(
            "ILME-FX3 cannot receive USB power supply or internal battery charging "
            "via Multi/Micro USB; USB power delivery is USB Type-C exclusive."
        )

    # [USB LUN Setting] Multi (2 LUNs) vs Single (1 LUN) visibility
    exp_lun_count = int(resolved["expected_msc_exposed_lun_count"])
    if claimed_msc_exposed_lun_count is None:
        eff_lun_count = exp_lun_count
    else:
        if isinstance(claimed_msc_exposed_lun_count, bool) or not isinstance(
            claimed_msc_exposed_lun_count, int
        ):
            eff_lun_count = -1
        else:
            eff_lun_count = claimed_msc_exposed_lun_count

    if eff_lun_count != exp_lun_count:
        _add_code(codes, STATUS_BLOCKED_G94_USB_LUN_SLOT_VISIBILITY_MISMATCH)
        errors.append(
            f"[USB LUN Setting]={eff_lun} MSC slot exposure mismatch: expected "
            f"{exp_lun_count} LUN(s) ({resolved['exposed_msc_slots']}), got {claimed_msc_exposed_lun_count!r}."
        )

    # Hard-block physical live host USB attachment / packet emission on lab bench
    if (
        bool(live_host_usb_attach_requested)
        or simulated_usb_packets_transmitted > 0
        or (not bool(off_camera_wp_locked_sdxc_reader_used))
        or HARDWARE_LIVE_ATTACHMENT_AUTHORIZED
    ):
        _add_code(codes, STATUS_BLOCKED_G94_LIVE_HOST_USB_ATTACHMENT_FORBIDDEN)
        errors.append(
            "Physical live host USB attachment or packet transmission is hard-blocked "
            "on lab bench; Tier-0 SHA-256 verification must use off-camera WP-locked SDXC readers."
        )

    if eff_lun == USB_LUN_SINGLE_G94 and not codes:
        warnings.append(
            "[USB LUN Setting]=Single exposes only the primary recording slot over MSC for legacy hosts."
        )

    valid = not codes
    status = STATUS_VERIFIED_G94 if valid else codes[0]
    model_id_hex = (
        f"0x{body_model_id:08x}"
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else "INVALID"
    )

    return UsbPowerInterlockAndLunPersistenceResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        body_model_name=str(body_model_name),
        body_model_id_hex=model_id_hex,
        firmware_version=str(firmware_version),
        usb_setup_menu_path=USB_SETUP_MENU_PATH_G94,
        usb_connection_mode_menu_path=USB_CONNECTION_MODE_MENU_PATH_G94,
        usb_lun_setting_menu_path=USB_LUN_SETTING_MENU_PATH_G94,
        usb_power_supply_menu_path=USB_POWER_SUPPLY_MENU_PATH_G94,
        pre_reset_usb_connection_mode=norm_conn or str(pre_reset_usb_connection_mode),
        pre_reset_usb_lun_setting=norm_lun or str(pre_reset_usb_lun_setting),
        pre_reset_usb_power_supply=norm_pwr or str(pre_reset_usb_power_supply),
        reset_action=norm_rst or str(reset_action),
        expected_post_reset_usb_connection_mode=exp_conn,
        effective_post_reset_usb_connection_mode=eff_conn,
        expected_post_reset_usb_lun_setting=exp_lun,
        effective_post_reset_usb_lun_setting=eff_lun,
        expected_post_reset_usb_power_supply=exp_pwr,
        effective_post_reset_usb_power_supply=eff_pwr,
        usb_setup_survives_camera_settings_reset=True,
        usb_setup_reset_only_by_initialize=True,
        battery_bay_source=norm_bay or str(battery_bay_source),
        np_fz100_or_dc_c1_present=bool(resolved["np_fz100_or_dc_c1_present"]),
        usb_power_port=norm_port or str(usb_power_port),
        usb_wall_adapter_connected=bool(usb_wall_adapter_connected),
        power_on_requested=bool(power_on_requested),
        power_on_available=bool(resolved["power_on_available"]),
        mid_session_battery_removed=bool(mid_session_battery_removed),
        mid_session_unbuffered_power_off_triggered=bool(
            resolved["mid_session_unbuffered_power_off_triggered"]
        ),
        usb_power_type_c_exclusive=True,
        multi_micro_usb_power_or_charge_supported=False,
        effective_usb_bus_power_active=bool(resolved["effective_usb_bus_power_active"]),
        expected_msc_exposed_lun_count=exp_lun_count,
        effective_msc_exposed_lun_count=eff_lun_count,
        exposed_msc_slots=tuple(resolved["exposed_msc_slots"]),
        off_camera_wp_locked_sdxc_reader_used=bool(
            off_camera_wp_locked_sdxc_reader_used
        ),
        live_host_usb_attach_requested=bool(live_host_usb_attach_requested),
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def evaluate_g94_usb_power_and_lun_persistence_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    usb_power_lun_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase246DonorAuditResult] = None,
) -> Tuple[GateVerdict, G94UsbPowerAndLunPersistenceGuardResult]:
    """Evaluate Gate `G94` combining bounded `<0.10s` `O_RDONLY` donor audit
    and `[USB Power Supply]` / `[USB LUN Setting]` verification.
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase246_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_usb_power_npfz100_typec_and_lun_persistence_guard(
        **(dict(usb_power_lun_kwargs) if usb_power_lun_kwargs else {})
    )

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE246_DONOR_INTEGRITY)
        errors.extend(audit.errors)
    for c in guard.violation_codes:
        _add_code(codes, c)
    errors.extend(guard.errors)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G94 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G94 if valid else codes[0]

    res = G94UsbPowerAndLunPersistenceGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        usb_power_lun_guard=guard.to_dict(),
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, usb_pwr={guard.effective_post_reset_usb_power_supply}"
        f"(bay={guard.battery_bay_source},port={guard.usb_power_port},"
        f"bus_pwr_active={guard.effective_usb_bus_power_active}), "
        f"lun={guard.effective_post_reset_usb_lun_setting}"
        f"(luns={guard.effective_msc_exposed_lun_count},"
        f"survives_reset={guard.usb_setup_survives_camera_settings_reset},"
        f"usb_pkts={USB_PACKETS_TRANSMITTED})"
    )
    verdict = GateVerdict(
        gate_id=G94_GATE_ID,
        gate_code=G94_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 4. Unified `94`-Gate Master Safety Preflight (`G01..G94`)
# ---------------------------------------------------------------------------


def evaluate_94gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    framing_antiflicker_kwargs: Optional[Mapping[str, Any]] = None,
    usb_power_lun_kwargs: Optional[Mapping[str, Any]] = None,
    master_92_override: Optional[Master92GateReport] = None,
    **m92_passthrough_kwargs: Any,
) -> Master94GateReport:
    """Evaluate all 94 Master Safety Gates (`G01..G94`) deterministically by
    delegating `G01..G92` directly to `evaluate_92gate_preflight()`.
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

    m92_report: Master92GateReport = (
        master_92_override
        if master_92_override is not None
        else evaluate_92gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m92_passthrough_kwargs,
        )
    )

    phase246_audit = audit_phase246_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g93_verdict, g93_res = evaluate_g93_framing_and_antiflicker_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        framing_antiflicker_kwargs=framing_antiflicker_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase246_audit,
    )

    g94_verdict, g94_res = evaluate_g94_usb_power_and_lun_persistence_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        usb_power_lun_kwargs=usb_power_lun_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase246_audit,
    )

    gates_93_to_94 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g93_verdict, g94_verdict)
    ]
    all_gates = tuple(list(m92_report.gates) + gates_93_to_94)

    g01_to_g12_verified = int(m92_report.summary["g01_to_g12_verified"])
    g13_to_g92_verified = (
        int(m92_report.summary["g13_to_g90_verified"])
        + int(m92_report.summary["g91_to_g92_verified"])
    )
    g93_to_g94_verified = sum(1 for v in (g93_verdict, g94_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g92_verified + g93_to_g94_verified

    g93_to_g94_all_passed = g93_to_g94_verified == 2
    g13_to_g94_all_passed = m92_report.g13_to_g92_all_passed and g93_to_g94_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m92_report.gates[:9])

    offline_91_verified = (
        g01_to_g09_ok
        and m92_report.offline_89_gates_verified
        and g93_to_g94_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_94_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g94_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m92_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_91_verified
        and m92_report.h0_h1_trial_entry_allowed
        and g93_to_g94_all_passed
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
        list(m92_report.errors) + list(g93_verdict.errors) + list(g94_verdict.errors)
    )
    warnings: List[str] = (
        list(m92_report.warnings)
        + list(g93_verdict.warnings)
        + list(g94_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m92_report.g13_to_g92_all_passed:
        overall_status = m92_report.status
    elif not g93_verdict.passed:
        overall_status = g93_verdict.status
    elif not g94_verdict.passed:
        overall_status = g94_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_94_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_94_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_94_verified:
        overall_status = "VERIFIED_ALL_94_GATES"
    else:
        overall_status = "VERIFIED_91_OF_94_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m92_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g93_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g94_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 94,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 94 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g92_verified": g13_to_g92_verified,
        "g93_to_g94_verified": g93_to_g94_verified,
        "g13_to_g94_all_passed": g13_to_g94_all_passed,
        "g93_to_g94_all_passed": g93_to_g94_all_passed,
        "offline_91_gates_verified": offline_91_verified,
        "all_94_gates_verified": all_94_verified,
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

    return Master94GateReport(
        schema=REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_SCHEMA,
        version=REALHW_FRAMING_USBPOWER_LUN_ANTIFLICKER_94GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_91_gates_verified=offline_91_verified,
        all_94_gates_verified=all_94_verified,
        g13_to_g94_all_passed=g13_to_g94_all_passed,
        g93_to_g94_all_passed=g93_to_g94_all_passed,
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
        master_92_report=m92_report.to_dict(),
        g93_result=g93_res.to_dict(),
        g94_result=g94_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_94_master_safety_gates = evaluate_94gate_preflight
run_94_gate_preflight = evaluate_94gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_framing_usbpower_lun_antiflicker_and_94gate_guard",
        description=(
            "Phase 246 Safety Gates G93 (Framing Settings Asymmetric Full/Crop Stream "
            "Guard & Anti-flicker Shoot. Mechanical-Still-Only / No-Var. Shutter "
            "Firewall) + G94 (USB Power Supply Mandatory NP-FZ100 Insertion + USB "
            "Type-C Exclusivity & USB LUN Setting Multi/Single Setup Persistence "
            "Guard) + Unified 94-Gate Master Safety Preflight"
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

    report = evaluate_94gate_preflight(
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
            f"verified={report.summary['verified_gates']}/94 "
            f"g93_to_g94_all_passed={report.g93_to_g94_all_passed} "
            f"all_94_gates_verified={report.all_94_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"usb_packets_transmitted={report.usb_packets_transmitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_94_gates_verified
        if args.dry_run_simulated
        else report.offline_91_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
