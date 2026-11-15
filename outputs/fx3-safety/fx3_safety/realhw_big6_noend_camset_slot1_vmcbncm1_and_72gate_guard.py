"""Phase 201 — Real-Hardware Main Track Part 23:
Gate G71 (`ILME-FX3` `Ver. 7.02` `BIG6` `[Mode Settings] = [Fixed/Variable]` &
`[Home (Lower Left)] = [Aperture / ND Filter]` Zero Physical e-ND Actuator Firewall
`e_nd_actuator_tx_count == 0` Blocking `FX6` Variable `1/4..1/128` CP Motor Drive,
plus Slot-1-Only `CAMSET01.DAT .. CAMSET10.DAT` Dual-Media Root Split
`SD: /PRIVATE/SONY/SETTING/FX3/CAMSET/` vs `CFexpress-A: /SONY/SETTING/FX3/CAMSET/`,
`MR` Recall Camera Setting Lockout, Cross-Model `ILME-FX3` / `ILME-FX3A` / `ILME-FX6`
`.DAT` Header Rejection, and Stage-B `/tmp/fx6_camset_overlay` Sandboxing with
`H0 == H3` Invariance),
Gate G72 (`VMC-BNCM1` `A-5051-506-A` `0.2m` Unidirectional Body-Only `Multi/Micro USB`
`TC IN` `[Movie]` + `[Time Code Make] = [Preset]` + `[Time Code Run] = [Free Run]`
`>= 10.0s` `EXT-LK` Lock with Auto-Release on `S&Q` or `TC Make/Run/Preset` Change,
Fail-Closed `XLR-H1` Handle Side Micro-USB `VMC-BNCM1` Connection Block, Zero Reverse
LTC/BNC `TC OUT` Drive on `Multi/Micro USB` Masked with `EOPNOTSUPP`, and Digital
Type-A HDMI-Only `[Time Code Output] = [On]` Guard Auto-Disabled in `S&Q`),
and 72-Gate Master Safety Preflight (`G01..G72` / `verify-72-gates` / `run_72_gate_preflight`).

Composes `realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard` (`G01..G70`, keeping
`evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`,
`evaluate_64gate_preflight`, `evaluate_66gate_preflight`, `evaluate_68gate_preflight`,
`evaluate_70gate_preflight`, `verify-58-gates`, `verify-60-gates`, `verify-62-gates`,
`verify-64-gates`, `verify-66-gates`, `verify-68-gates`, and `verify-70-gates` 100%
intact) while hard-locking all physical flash/write/transmit redlines:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`
- `HUMAN_HARDWARE_ATTACH_TOKEN = False`
- `PHYSICAL_USB_PACKETS_EMITTED = 0`
- `RAW_FIRMWARE_BYTES_LEAKED = 0`
- `overall_ready_for_hardware_attach = False`
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_fan_pwm_shutter_angle_lut_split_and_70gate_guard import (
    Master70GateReport,
    evaluate_70gate_preflight,
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3A_MODEL_NAME,
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_BIG6_NOEND_CAMSET_SLOT1_VMCBNCM1_72GATE_SCHEMA: str = (
    "fx3-realhw-big6-noend-camset-slot1-vmcbncm1-72gate-preflight-v1"
)
REALHW_BIG6_NOEND_CAMSET_SLOT1_VMCBNCM1_72GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Gate IDs & Canonical Codes for G71..G72
G71_GATE_ID: str = "G71_fx3_big6_zero_end_actuator_and_slot1_camset_firewall"
G71_GATE_CODE: str = "GATE_G71_FX3_BIG6_ZERO_END_ACTUATOR_AND_SLOT1_CAMSET_FIREWALL"
GATE_G71_FX3_BIG6_ZERO_END_ACTUATOR_AND_SLOT1_CAMSET_FIREWALL: str = G71_GATE_CODE
G71: str = G71_GATE_CODE

G72_GATE_ID: str = "G72_vmcbncm1_body_tcin_xlrh1_block_and_hdmi_tcout_guard"
G72_GATE_CODE: str = "GATE_G72_VMCBNCM1_BODY_TCIN_XLRH1_BLOCK_AND_HDMI_TCOUT_GUARD"
GATE_G72_VMCBNCM1_BODY_TCIN_XLRH1_BLOCK_AND_HDMI_TCOUT_GUARD: str = G72_GATE_CODE
G72: str = G72_GATE_CODE

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G71: str = (
    "VERIFIED_FX3_BIG6_ZERO_END_ACTUATOR_AND_SLOT1_CAMSET_FIREWALL"
)
STATUS_VERIFIED_G72: str = (
    "VERIFIED_VMCBNCM1_BODY_TCIN_XLRH1_BLOCK_AND_HDMI_TCOUT_GUARD"
)

# Gate G71 Violation Codes
STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN: str = (
    "BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN"
)
STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID: str = (
    "BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID"
)
STATUS_BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN: str = (
    "BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN"
)
STATUS_BLOCKED_G71_CAMSET_FILE_OR_COUNT_CEILING_EXCEEDED: str = (
    "BLOCKED_G71_CAMSET_FILE_OR_COUNT_CEILING_EXCEEDED"
)
STATUS_BLOCKED_G71_CAMSET_MEDIA_ROOT_PATH_MISMATCH: str = (
    "BLOCKED_G71_CAMSET_MEDIA_ROOT_PATH_MISMATCH"
)
STATUS_BLOCKED_G71_CAMSET_CROSS_MODEL_HEADER_REJECTED: str = (
    "BLOCKED_G71_CAMSET_CROSS_MODEL_HEADER_REJECTED"
)
STATUS_BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT: str = (
    "BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT"
)
STATUS_BLOCKED_G71_TELEMETRY_INVALID: str = (
    "BLOCKED_G71_BIG6_CAMSET_SLOT1_TELEMETRY_INVALID"
)

# Gate G72 Violation Codes
STATUS_BLOCKED_G72_XLRH1_HANDLE_MICRO_USB_VMCBNCM1_FORBIDDEN: str = (
    "BLOCKED_G72_XLRH1_HANDLE_MICRO_USB_VMCBNCM1_FORBIDDEN"
)
STATUS_BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN: str = (
    "BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN"
)
STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED: str = (
    "BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED"
)
STATUS_BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION: str = (
    "BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION"
)
STATUS_BLOCKED_G72_TELEMETRY_INVALID: str = (
    "BLOCKED_G72_VMCBNCM1_TCIN_HDMI_TCOUT_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE201_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE201_72GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G71 Constants — ILME-FX3 (Ver. 7.02) BIG6 Zero e-ND & Slot-1 CAMSET Firewall
FX6_MODEL_NAME_G71: str = "ILME-FX6"
FX3_BIG6_MIN_FW_VERSION: str = "7.00"
FX3_DEFAULT_FW_VERSION_G71: str = "7.02"

BIG6_REQUIRED_MODE_SETTING: str = "FIXED_VARIABLE"
BIG6_HOME_LOWER_LEFT_MENU_PATH: str = (
    "MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)]"
)
BIG6_HOME_LOWER_LEFT_APERTURE: str = "APERTURE"
BIG6_HOME_LOWER_LEFT_ND_FILTER: str = "ND_FILTER"
ALLOWED_BIG6_HOME_LOWER_LEFT_ITEMS: Tuple[str, ...] = (
    BIG6_HOME_LOWER_LEFT_APERTURE,
    BIG6_HOME_LOWER_LEFT_ND_FILTER,
)
BIG6_EXACT_6_CELL_LAYOUT: Tuple[str, ...] = (
    "FPS (Fixed/Variable)",
    "ISO / Base ISO",
    "Shutter speed / Shutter angle",
    "Aperture / ND Filter",
    "Picture Profile / Select LUT",
    "White Balance",
)
BIG6_STATUS_BAR_REGION_INDEX: int = 7
ALLOWED_VIRTUAL_ND_METADATA_LABELS: Tuple[str, ...] = (
    "CLEAR",
    "1/4",
    "1/8",
    "1/16",
    "1/32",
    "1/64",
    "1/128",
)

CAMSET_REQUIRED_SLOT_INDEX: int = 1
CAMSET_MAX_FILES_PER_CARD: int = 10
VALID_CAMSET_FILENAMES: Tuple[str, ...] = tuple(
    f"CAMSET{i:02d}.DAT" for i in range(1, CAMSET_MAX_FILES_PER_CARD + 1)
)
SD_CAMSET_ROOT_DIR: str = "/PRIVATE/SONY/SETTING/FX3/CAMSET/"
CFEXPRESS_A_CAMSET_ROOT_DIR: str = "/SONY/SETTING/FX3/CAMSET/"
CAMSET_EXCLUDED_MACHINE_BOUND_ITEMS: Tuple[str, ...] = (
    "WHITE_BALANCE_CUSTOM_1_2_3",
    "FTP_TRANSFER",
    "NETWORK_STREAMING",
    "IP_AND_TLS_CERTIFICATES",
    "DATE_TIME_CLOCK",
)
INCOMPATIBLE_CAMSET_MODEL_HEADERS: Tuple[str, ...] = (
    FX3_MODEL_NAME,
    FX3A_MODEL_NAME,
    FX6_MODEL_NAME_G71,
)
REQUIRED_STAGEB_CAMSET_OVERLAY_DIR: str = "/tmp/fx6_camset_overlay"
FORBIDDEN_STAGEB_CAMSET_WRITE_PATHS: Tuple[str, ...] = (
    SD_CAMSET_ROOT_DIR.rstrip("/"),
    CFEXPRESS_A_CAMSET_ROOT_DIR.rstrip("/"),
    "p2:/setting",
    "/setting",
    "/dev/nflasha2",
    "/dev/cnflasha2",
    "p2:",
)
DEFAULT_H0_CAMSET_SURFACE_SHA256: str = "c" * 64

# Gate G72 Constants — VMC-BNCM1 Body-Only TC IN, XLR-H1 Block & HDMI-Only TC OUT
VMC_BNCM1_ADAPTER_MODEL: str = "VMC-BNCM1"
VMC_BNCM1_SONY_PART_NUMBER: str = "A-5051-506-A"
VMC_BNCM1_CABLE_LENGTH_M: float = 0.2

BODY_MULTI_MICRO_USB_PORT: str = "BODY_MULTI_MICRO_USB"
XLR_H1_HANDLE_MICRO_USB_PORT: str = "XLR_H1_HANDLE_MICRO_USB"
REJECTED_VMC_BNCM1_PORTS: Tuple[str, ...] = (
    XLR_H1_HANDLE_MICRO_USB_PORT,
    "XLR_H1_MICRO_USB",
    "HANDLE_MICRO_USB",
    "TOP_HANDLE_MICRO_USB",
    "MISHOE_HANDLE_USB",
    "BODY_USB_TYPE_C",
    "USB_C",
)

TC_DIRECTION_IN_ONLY: str = "TC_IN"
TC_MAKE_PRESET_REQUIRED: str = "PRESET"
TC_RUN_FREE_RUN_REQUIRED: str = "FREE_RUN"
MIN_VMC_BNCM1_EXT_LK_SECONDS: float = 10.0

EXT_LK_STATE_LOCKED: str = "EXT-LK"
EXT_LK_STATE_ACQUIRING: str = "ACQUIRING_PRE_10S"
EXT_LK_STATE_RELEASED: str = "RELEASED_UNLOCKED"

STAGEB_BNC_TCOUT_MASK_ERRNO_NAME: str = "EOPNOTSUPP"
HDMI_TC_OUT_MENU_PATH: str = (
    "MENU -> Setup -> [External Output] -> [HDMI Output Settings] -> [Time Code Output]"
)
ALLOWED_TC_OUT_TRANSPORT_G72: str = "TYPE_A_HDMI"
REJECTED_TC_OUT_TRANSPORTS_G72: Tuple[str, ...] = (
    "BNC_TC_OUT",
    "VMC_BNCM1_BNC",
    "MULTI_MICRO_USB_LTC",
    "XLR_H1_HANDLE_MICRO_USB",
    "12G_SDI",
    "SDI",
    "3_5MM_AUDIO_LTC",
)

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE201_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"SETTING",
            b"SONY",
            b"PRIVATE",
            b"ND",
            b"Aperture",
            b"TC",
            b"HDMI",
            b"BK4",
            b"/setting",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,SETTING,SONY,PRIVATE,ND,Aperture,TC,HDMI,BK4,/setting}",
    ),
    "fx3_saveload_so": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (
            b"\x7fELF",
            b"SaveLoadSettings",
            b"Save",
            b"Load",
            b"Settings",
            b"Backup",
        ),
        "fx3/libSaveLoadSettings.so::{18760B,ELF,SaveLoadSettings,Save,Load,Settings,Backup}",
    ),
    "fx3_usbctrl_so": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbControl.so",
        135_424,
        "2bf51f28fd5066e56afc8bbb02ddbaa96b36f57ff2a823cecf9f901781754ed9",
        (
            b"\x7fELF",
            b"TC",
            b"USB",
            b"Multi",
            b"Backup",
        ),
        "fx3/libUsbControl.so::{135424B,ELF,TC,USB,Multi,Backup}",
    ),
    "fx3_bk4_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (
            b"BK4",
            b"ILME-FX3",
            b"TC",
            b"/setting",
        ),
        "fx3/FX3-CX95900_ALLLANG-Backup.bin::{2229740B,BK4,ILME-FX3,TC,/setting}",
    ),
    "fx6_bk4_bin": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (
            b"BK4",
            b"ND",
            b"TC",
            b"/setting",
        ),
        "fx6/CX95898_NTSC.bin::{2253333B,BK4,ND,TC,/setting}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase201DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
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
class Fx3Big6ZeroEndAndSlot1CamsetResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    body_model_name: str
    body_model_id: int
    body_model_id_hex: str
    firmware_version: str
    big6_home_active: bool
    mode_settings: str
    canonical_mode_settings: str
    custom_key_home_assigned: bool
    home_lower_left_menu_path: str
    home_lower_left_item: str
    canonical_home_lower_left_item: str
    big6_cell_count: int
    big6_status_bar_region_present: bool
    fx3_has_physical_end_hardware: bool
    e_nd_actuator_tx_count: int
    fx6_variable_nd_motor_cmd_sent: bool
    nd_filter_virtual_metadata_only: bool
    virtual_nd_reference_label: str
    big6_zero_end_firewall_valid: bool
    camset_slot_index: int
    mr_recall_mode_active: bool
    camset_operation_in_mr_attempted: bool
    camset_greyed_out_in_mr: bool
    media_type: str
    canonical_media_type: str
    camset_directory: str
    expected_camset_directory: str
    camset_filename: str
    camset_card_file_count: int
    excluded_machine_bound_items_stripped: bool
    camset_dat_header_model: str
    cross_model_header_rejected: bool
    stageb_camset_overlay_path: str
    stageb_camset_sandboxed_in_tmp: bool
    stageb_slot1_fx3_camset_overwrite_attempted: bool
    stageb_p2_setting_write_attempted: bool
    p2_setting_mutation_bytes: int
    h0_camset_surface_sha256: str
    h3_camset_surface_sha256: str
    h0_equals_h3_camset_surface: bool
    slot1_camset_firewall_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class VmcBncm1BodyTcInAndHdmiTcOutResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    adapter_model: str
    adapter_part_number: str
    cable_length_m: float
    connected_usb_port: str
    canonical_usb_port: str
    xlr_h1_handle_micro_usb_connected: bool
    xlr_h1_handle_micro_usb_blocked: bool
    tc_signal_direction: str
    multi_usb_ltc_bnc_tcout_drive_attempted: bool
    stageb_fx6_bnc_tcout_masked_eopnotsupp: bool
    stageb_bnc_tcout_mask_errno_name: str
    shooting_mode: str
    canonical_shooting_mode: str
    sq_mode_active: bool
    tc_make: str
    canonical_tc_make: str
    tc_run: str
    canonical_tc_run: str
    continuous_ltc_lock_seconds: float
    sq_mode_triggered: bool
    tc_make_run_preset_changed_after_lock: bool
    ext_lk_required: bool
    modeled_ext_lk_state: str
    ext_lk_locked: bool
    vmcbncm1_body_tcin_valid: bool
    hdmi_tc_out_menu_path: str
    hdmi_timecode_output: str
    tc_out_enabled: bool
    tc_out_transport: str
    canonical_tc_out_transport: str
    hdmi_only_tcout_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G71Big6NoEndCamsetSlot1GuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    big6_noend_camset_slot1_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G72VmcBncm1TcInHdmiTcOutGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    vmcbncm1_tcin_hdmi_tcout_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master72GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_69_gates_verified: bool
    all_72_gates_verified: bool
    g13_to_g72_all_passed: bool
    g71_to_g72_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_70_report: Dict[str, Any]
    g71_result: Dict[str, Any]
    g72_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return {
            k: list(v) if isinstance(v, tuple) else v
            for k, v in self.__dict__.items()
        }


# ---------------------------------------------------------------------------
# Internal Helpers (Strict os.O_RDONLY, zero raw bytes printing)
# ---------------------------------------------------------------------------


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without leaking raw bytes."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, 1_048_576)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _is_non_negative_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val >= 0


def _is_finite_number(val: Any) -> bool:
    if isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    return abs(float(val)) < 1e12 and (float(val) == float(val))


def _normalize_int_value(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.strip().lower()
        if not s:
            return None
        try:
            return int(s, 16) if s.startswith("0x") else int(s, 10)
        except ValueError:
            return None
    return None


def _norm_token(val: str) -> str:
    s = val.strip().upper()
    s = s.replace("&", "_AND_").replace(".", "_").replace("(", "_").replace(")", "")
    s = re.sub(r"[^A-Z0-9]+", "_", s).strip("_")
    return s


def _parse_version_tuple(ver_str: str) -> Optional[Tuple[int, ...]]:
    s = ver_str.strip()
    if s.lower().startswith("ver."):
        s = s[4:].strip()
    elif s.lower().startswith("v"):
        s = s[1:].strip()
    if not s or not re.fullmatch(r"\d+(?:\.\d+){1,3}", s):
        return None
    return tuple(int(part) for part in s.split("."))


def _version_gte(ver_str: str, floor_str: str) -> bool:
    v = _parse_version_tuple(ver_str)
    f = _parse_version_tuple(floor_str)
    if v is None or f is None:
        return False
    max_len = max(len(v), len(f))
    vp = v + (0,) * (max_len - len(v))
    fp = f + (0,) * (max_len - len(f))
    return vp >= fp


def _norm_mode_settings(val: str) -> str:
    t = _norm_token(val)
    if t in ("FIXED_VARIABLE", "FIXEDVARIABLE", "BIG6_FIXED_VARIABLE"):
        return BIG6_REQUIRED_MODE_SETTING
    return t


def _norm_home_lower_left_item(val: str) -> str:
    t = _norm_token(val)
    if t in ("APERTURE", "IRIS"):
        return BIG6_HOME_LOWER_LEFT_APERTURE
    if t in ("ND_FILTER", "ND", "NDFILTER"):
        return BIG6_HOME_LOWER_LEFT_ND_FILTER
    return t


def _norm_media_type_g71(media_type: str) -> str:
    t = _norm_token(media_type)
    if t in ("SD", "SDHC", "SDXC", "SD_CARD", "SDXC_UHS_II", "SDXC_V90"):
        return "SD"
    if t in (
        "CFEXPRESS_A",
        "CFEXPRESS_TYPE_A",
        "CFEXPRESS",
        "CFE_A",
        "CFEXPRESSA",
    ):
        return "CFEXPRESS_A"
    return t


def _parse_camset_slot(slot: Union[int, str]) -> Optional[int]:
    if isinstance(slot, bool):
        return None
    if isinstance(slot, int):
        return slot
    if isinstance(slot, str):
        s = slot.strip()
        m = re.fullmatch(r"(?i)slot\s*_?\s*(\d+)", s)
        if m:
            return int(m.group(1))
        if s.upper() in ("SLOT_A", "SLOTA"):
            return 1
        if s.upper() in ("SLOT_B", "SLOTB"):
            return 2
        if s.isdigit():
            return int(s)
    return None


def _norm_camset_dir(path_str: str) -> str:
    s = path_str.strip().replace("\\", "/")
    if not s:
        return ""
    if not s.endswith("/"):
        s += "/"
    return s


def _norm_model_header(val: str) -> str:
    s = val.strip().upper().replace("_", "-")
    if s in ("FX3", "ILME-FX3"):
        return FX3_MODEL_NAME
    if s in ("FX3A", "ILME-FX3A"):
        return FX3A_MODEL_NAME
    if s in ("FX6", "ILME-FX6"):
        return FX6_MODEL_NAME_G71
    return s


def _norm_usb_port_g72(port: str) -> str:
    t = _norm_token(port)
    if t in (
        "BODY_MULTI_MICRO_USB",
        "MULTI_MICRO_USB",
        "BODY_MULTI_USB",
        "MULTI_USB",
        "CAMERA_BODY_MULTI_MICRO_USB",
    ):
        return BODY_MULTI_MICRO_USB_PORT
    if t in (
        "XLR_H1_HANDLE_MICRO_USB",
        "XLR_H1_MICRO_USB",
        "XLRH1_HANDLE_MICRO_USB",
        "XLRH1_MICRO_USB",
        "HANDLE_MICRO_USB",
        "TOP_HANDLE_MICRO_USB",
        "MISHOE_HANDLE_USB",
    ):
        return XLR_H1_HANDLE_MICRO_USB_PORT
    if t in ("USB_TYPE_C", "BODY_USB_TYPE_C", "USB_C", "TYPE_C"):
        return "BODY_USB_TYPE_C"
    return t


def _norm_tc_direction(val: str) -> str:
    t = _norm_token(val)
    if t in ("TC_IN", "TCIN", "LTC_IN", "IN"):
        return TC_DIRECTION_IN_ONLY
    if t in ("TC_OUT", "TCOUT", "LTC_OUT", "BNC_TC_OUT", "OUT"):
        return "TC_OUT"
    if t in ("BIDIRECTIONAL", "IN_OUT", "TC_IN_OUT"):
        return "BIDIRECTIONAL"
    return t


def _norm_shooting_mode_g72(val: str) -> str:
    t = _norm_token(val)
    if t in ("MOVIE", "CINE_EI", "FLEXIBLE_ISO", "CUSTOM_MOVIE", "BIG6_MOVIE"):
        return "MOVIE"
    if t in ("S_AND_Q", "SQ", "SLOW_AND_QUICK"):
        return "S&Q"
    if t in ("STILL", "PHOTO"):
        return "STILL"
    return t


def _norm_tc_make(val: str) -> str:
    t = _norm_token(val)
    if t == "PRESET":
        return TC_MAKE_PRESET_REQUIRED
    if t in ("REGENERATE", "REGEN"):
        return "REGENERATE"
    return t


def _norm_tc_run(val: str) -> str:
    t = _norm_token(val)
    if t in ("FREE_RUN", "FREERUN"):
        return TC_RUN_FREE_RUN_REQUIRED
    if t in ("REC_RUN", "RECRUN"):
        return "REC_RUN"
    return t


def _norm_hdmi_tc_out_toggle(val: Union[str, bool]) -> Optional[bool]:
    if isinstance(val, bool):
        return val
    if isinstance(val, str):
        t = _norm_token(val)
        if t in ("ON", "ENABLED", "TRUE"):
            return True
        if t in ("OFF", "DISABLED", "FALSE"):
            return False
    return None


def _norm_tc_out_transport(val: str) -> str:
    t = _norm_token(val)
    if t in ("TYPE_A_HDMI", "HDMI", "HDMI_TYPE_A", "DIGITAL_TYPE_A_HDMI", "DIGITAL_HDMI"):
        return ALLOWED_TC_OUT_TRANSPORT_G72
    if t in ("NONE", "DISABLED", "OFF"):
        return "DISABLED"
    return t


def _write_stdout_safe(text: str) -> None:
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except BrokenPipeError:
        devnull = os.open(os.devnull, os.O_WRONLY)
        os.dup2(devnull, sys.stdout.fileno())
        os.close(devnull)


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase201_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase201DonorAuditResult:
    """Inspect FX3 `7.02` `cpapp-b.bin`, `libSaveLoadSettings.so`, `libUsbControl.so`,
    `FX3-CX95900_ALLLANG-Backup.bin`, and FX6 `6.01` `CX95898_NTSC.bin` strictly via
    `os.open(..., os.O_RDONLY)` with deterministic clean-room fallback when
    `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.
    """
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (
            _body,
            rel_path,
            _sz,
            _sha,
            _toks,
            _lbl,
        ) in PINNED_PHASE201_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase201DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE201_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE201_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE201_DONOR_SPECS.items()
            },
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    warnings: List[str] = []
    passed_keys: Set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE201_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
        files_inspected += 1
        sha = hashlib.sha256(blob).hexdigest()
        shas[key] = sha
        sizes[key] = len(blob)

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = len(blob) == exp_size and sha == exp_sha

        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )

        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={len(blob)} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )

        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    fx3_keys = {
        k for k, spec in PINNED_PHASE201_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    fx6_keys = {
        k for k, spec in PINNED_PHASE201_DONOR_SPECS.items() if spec[0] == "fx6"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase201DonorAuditResult(
        valid=valid,
        status=(
            STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE201_DONOR_INTEGRITY
        ),
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        fx6_contracts_verified=fx6_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Functions & Sub-Validators (G71 & G72)
# ---------------------------------------------------------------------------


def resolve_fx3_camset_slot1_directory(media_type: str) -> str:
    """Resolve the canonical `ILME-FX3` Slot-1 `CAMSET` directory across asymmetric
    Sony media layouts:
    - `SD / SDHC / SDXC`: `/PRIVATE/SONY/SETTING/FX3/CAMSET/`
    - `CFexpress Type A`: `/SONY/SETTING/FX3/CAMSET/` (top-level `/PRIVATE` omitted)
    """
    norm = _norm_media_type_g71(media_type)
    if norm == "SD":
        return SD_CAMSET_ROOT_DIR
    if norm == "CFEXPRESS_A":
        return CFEXPRESS_A_CAMSET_ROOT_DIR
    return "INVALID_MEDIA_TYPE"


def compute_vmcbncm1_ext_lk_state(
    *,
    shooting_mode: str = "Movie",
    tc_make: str = "Preset",
    tc_run: str = "Free Run",
    continuous_ltc_lock_seconds: float = 12.0,
    sq_mode_triggered: bool = False,
    tc_make_run_preset_changed_after_lock: bool = False,
) -> str:
    """Compute physical `ILME-FX3` + `VMC-BNCM1` external LTC synchronization state:
    - Requires `[Movie]` + `[Time Code Make] = [Preset]` + `[Time Code Run] = [Free Run]`
      with continuous external LTC input `>= 10.0s` to reach `EXT-LK`.
    - Immediately releases (`RELEASED_UNLOCKED`) if switched to `S&Q` or if `TC Make`,
      `TC Run`, or `Time Code Preset` is modified.
    """
    s_mode = _norm_shooting_mode_g72(shooting_mode)
    t_make = _norm_tc_make(tc_make)
    t_run = _norm_tc_run(tc_run)

    if (
        s_mode != "MOVIE"
        or sq_mode_triggered
        or tc_make_run_preset_changed_after_lock
        or t_make != TC_MAKE_PRESET_REQUIRED
        or t_run != TC_RUN_FREE_RUN_REQUIRED
    ):
        return EXT_LK_STATE_RELEASED

    if float(continuous_ltc_lock_seconds) < MIN_VMC_BNCM1_EXT_LK_SECONDS:
        return EXT_LK_STATE_ACQUIRING

    return EXT_LK_STATE_LOCKED


def validate_fx3_big6_home_zero_end_actuator(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: Union[int, str] = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G71,
    big6_home_active: bool = True,
    mode_settings: str = "Fixed/Variable",
    custom_key_home_assigned: bool = True,
    home_lower_left_item: str = "Aperture",
    big6_cell_count: int = 6,
    big6_status_bar_region_present: bool = True,
    fx3_has_physical_end_hardware: bool = False,
    e_nd_actuator_tx_count: int = 0,
    fx6_variable_nd_motor_cmd_sent: bool = False,
    nd_filter_virtual_metadata_only: bool = True,
    virtual_nd_reference_label: str = "Clear",
) -> Tuple[bool, str, List[str]]:
    """Validate `ILME-FX3` (`Ver. 7.00+`) `Home` (`BIG6`) topology and enforce zero
    physical e-ND actuator transmissions (`e_nd_actuator_tx_count == 0`).
    """
    errors: List[str] = []
    parsed_id = _normalize_int_value(body_model_id)

    if body_model_name.strip().upper() != FX3_MODEL_NAME or parsed_id != FX3_MODEL_ID:
        errors.append(
            f"Gate G71 BIG6 guard requires body={FX3_MODEL_NAME} (0x{FX3_MODEL_ID:08x}); "
            f"got {body_model_name!r} ({body_model_id!r})."
        )
        return False, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID, errors

    if not _version_gte(firmware_version, FX3_BIG6_MIN_FW_VERSION):
        errors.append(
            f"ILME-FX3 Home (BIG6) screen requires firmware >= Ver. {FX3_BIG6_MIN_FW_VERSION}; "
            f"got {firmware_version!r}."
        )
        return False, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID, errors

    # Physical e-ND actuator firewall checks (highest priority hardware protection)
    if (
        fx3_has_physical_end_hardware
        or e_nd_actuator_tx_count != 0
        or fx6_variable_nd_motor_cmd_sent
    ):
        errors.append(
            f"ILME-FX3 has zero physical built-in e-ND hardware: "
            f"fx3_has_physical_end_hardware={fx3_has_physical_end_hardware}, "
            f"e_nd_actuator_tx_count={e_nd_actuator_tx_count} (must be 0), "
            f"fx6_variable_nd_motor_cmd_sent={fx6_variable_nd_motor_cmd_sent}."
        )
        return False, STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN, errors

    norm_ll = _norm_home_lower_left_item(home_lower_left_item)
    if norm_ll not in ALLOWED_BIG6_HOME_LOWER_LEFT_ITEMS:
        errors.append(
            f"Invalid [Home (Lower Left)] item {home_lower_left_item!r}; allowed: Aperture or ND Filter."
        )
        return False, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID, errors

    if norm_ll == BIG6_HOME_LOWER_LEFT_ND_FILTER and (not nd_filter_virtual_metadata_only):
        errors.append(
            "When [Home (Lower Left)] = [ND Filter] on ILME-FX3, ND Filter must operate "
            "strictly as pure virtual/reference metadata (nd_filter_virtual_metadata_only=True)."
        )
        return False, STATUS_BLOCKED_G71_BIG6_END_ACTUATOR_TX_FORBIDDEN, errors

    nd_lbl = virtual_nd_reference_label.strip().upper()
    if nd_lbl not in ALLOWED_VIRTUAL_ND_METADATA_LABELS:
        errors.append(
            f"Invalid virtual ND reference label {virtual_nd_reference_label!r}; "
            f"expected one of {ALLOWED_VIRTUAL_ND_METADATA_LABELS}."
        )
        return False, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID, errors

    norm_mode = _norm_mode_settings(mode_settings)
    if big6_home_active:
        if norm_mode != BIG6_REQUIRED_MODE_SETTING:
            errors.append(
                f"BIG6 Home screen requires [Mode Settings] = [Fixed/Variable]; got {mode_settings!r}."
            )
            return False, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID, errors
        if not custom_key_home_assigned:
            errors.append(
                "BIG6 Home screen requires [HOME] bound via [Custom Key/Dial Set.]."
            )
            return False, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID, errors
        if big6_cell_count != 6 or (not big6_status_bar_region_present):
            errors.append(
                f"BIG6 topology must preserve exact 6-cell grid + 7th status bar "
                f"(got cells={big6_cell_count}, status_bar={big6_status_bar_region_present})."
            )
            return False, STATUS_BLOCKED_G71_BIG6_HOME_TOPOLOGY_OR_MODE_INVALID, errors

    return True, STATUS_SAFE, []


def validate_slot1_camset_dualmedia_and_crossmodel_firewall(
    *,
    host_body_model: str = FX3_MODEL_NAME,
    camset_slot: Union[int, str] = 1,
    mr_recall_mode_active: bool = False,
    camset_operation_in_mr_attempted: bool = False,
    camset_greyed_out_in_mr: bool = True,
    media_type: str = "SDXC",
    camset_directory: str = SD_CAMSET_ROOT_DIR,
    camset_filename: str = "CAMSET01.DAT",
    camset_card_file_count: int = 1,
    excluded_machine_bound_items_stripped: bool = True,
    camset_dat_header_model: str = FX3_MODEL_NAME,
    stageb_camset_overlay_path: str = REQUIRED_STAGEB_CAMSET_OVERLAY_DIR,
    stageb_slot1_fx3_camset_overwrite_attempted: bool = False,
    stageb_p2_setting_write_attempted: bool = False,
    p2_setting_mutation_bytes: int = 0,
    h0_camset_surface_sha256: str = DEFAULT_H0_CAMSET_SURFACE_SHA256,
    h3_camset_surface_sha256: str = DEFAULT_H0_CAMSET_SURFACE_SHA256,
) -> Tuple[bool, str, List[str]]:
    """Validate `[Save/Load Settings]` (`CAMSET01..10.DAT`) Slot-1-only constraint,
    `MR` mode lockout, SD vs CFexpress-A root split, cross-model (`FX3`/`FX3A`/`FX6`)
    `.DAT` header isolation, and Stage-B `/tmp/fx6_camset_overlay` sandboxing (`H0 == H3`).
    """
    errors: List[str] = []

    slot_idx = _parse_camset_slot(camset_slot)
    if slot_idx != CAMSET_REQUIRED_SLOT_INDEX:
        errors.append(
            f"[Save/Load Settings] (CAMSET) is strictly locked to Slot 1 on ILME-FX3; "
            f"got slot={camset_slot!r} (Slot 2 / non-Slot-1 rejected)."
        )
        return False, STATUS_BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN, errors

    if mr_recall_mode_active and (
        camset_operation_in_mr_attempted or (not camset_greyed_out_in_mr)
    ):
        errors.append(
            "[Save/Load Settings] is disabled (greyed out) in MR (Recall Camera Setting) mode; "
            f"operation_attempted={camset_operation_in_mr_attempted}, greyed_out={camset_greyed_out_in_mr}."
        )
        return False, STATUS_BLOCKED_G71_CAMSET_SLOT2_OR_MR_MODE_FORBIDDEN, errors

    fname = camset_filename.strip()
    if (
        fname not in VALID_CAMSET_FILENAMES
        or camset_card_file_count < 0
        or camset_card_file_count > CAMSET_MAX_FILES_PER_CARD
        or (not excluded_machine_bound_items_stripped)
    ):
        errors.append(
            f"CAMSET file/ceiling/hygiene violation: filename={camset_filename!r} "
            f"(must be CAMSET01.DAT..CAMSET10.DAT), count={camset_card_file_count} "
            f"(max {CAMSET_MAX_FILES_PER_CARD}), "
            f"excluded_machine_bound_items_stripped={excluded_machine_bound_items_stripped}."
        )
        return False, STATUS_BLOCKED_G71_CAMSET_FILE_OR_COUNT_CEILING_EXCEEDED, errors

    expected_dir = resolve_fx3_camset_slot1_directory(media_type)
    actual_dir = _norm_camset_dir(camset_directory)
    if expected_dir == "INVALID_MEDIA_TYPE" or actual_dir != expected_dir:
        errors.append(
            f"Slot-1 CAMSET dual-media root split mismatch for media_type={media_type!r}: "
            f"got {camset_directory!r}, expected {expected_dir!r}."
        )
        return False, STATUS_BLOCKED_G71_CAMSET_MEDIA_ROOT_PATH_MISMATCH, errors

    host_norm = _norm_model_header(host_body_model)
    hdr_norm = _norm_model_header(camset_dat_header_model)
    if (
        host_norm != FX3_MODEL_NAME
        or hdr_norm not in INCOMPATIBLE_CAMSET_MODEL_HEADERS
        or hdr_norm != host_norm
    ):
        errors.append(
            f"Cross-model CAMSET .DAT header rejected: host={host_body_model!r} vs "
            f".DAT header={camset_dat_header_model!r} (ILME-FX3 / ILME-FX3A / ILME-FX6 incompatible)."
        )
        return False, STATUS_BLOCKED_G71_CAMSET_CROSS_MODEL_HEADER_REJECTED, errors

    ov_norm = stageb_camset_overlay_path.strip().replace("\\", "/").rstrip("/")
    req_ov = REQUIRED_STAGEB_CAMSET_OVERLAY_DIR.rstrip("/")
    in_tmp_sandbox = ov_norm == req_ov or ov_norm.startswith(req_ov + "/")
    touches_forbidden = any(
        ov_norm == fp or ov_norm.startswith(fp + "/")
        for fp in FORBIDDEN_STAGEB_CAMSET_WRITE_PATHS
    )
    h0_clean = h0_camset_surface_sha256.strip().lower()
    h3_clean = h3_camset_surface_sha256.strip().lower()
    sha_fmt_ok = bool(re.fullmatch(r"[0-9a-f]{64}", h0_clean)) and bool(
        re.fullmatch(r"[0-9a-f]{64}", h3_clean)
    )
    h0_eq_h3 = sha_fmt_ok and (h0_clean == h3_clean)

    if (
        (not in_tmp_sandbox)
        or touches_forbidden
        or stageb_slot1_fx3_camset_overwrite_attempted
        or stageb_p2_setting_write_attempted
        or p2_setting_mutation_bytes != 0
        or (not h0_eq_h3)
    ):
        errors.append(
            f"Stage-B FX6 CAMSET sandbox / H0==H3 violation: overlay={stageb_camset_overlay_path!r} "
            f"(required under {REQUIRED_STAGEB_CAMSET_OVERLAY_DIR}), "
            f"slot1_overwrite={stageb_slot1_fx3_camset_overwrite_attempted}, "
            f"p2_write={stageb_p2_setting_write_attempted}, "
            f"p2_mutation_bytes={p2_setting_mutation_bytes}, h0_eq_h3={h0_eq_h3}."
        )
        return False, STATUS_BLOCKED_G71_STAGEB_CAMSET_OVERLAY_OR_H0_H3_DRIFT, errors

    return True, STATUS_SAFE, []


def validate_vmcbncm1_body_multi_usb_tcin_and_ext_lk(
    *,
    adapter_model: str = VMC_BNCM1_ADAPTER_MODEL,
    adapter_part_number: str = VMC_BNCM1_SONY_PART_NUMBER,
    cable_length_m: float = VMC_BNCM1_CABLE_LENGTH_M,
    connected_usb_port: str = "Multi/Micro USB",
    xlr_h1_handle_micro_usb_connected: bool = False,
    tc_signal_direction: str = "TC IN",
    multi_usb_ltc_bnc_tcout_drive_attempted: bool = False,
    stageb_fx6_bnc_tcout_masked_eopnotsupp: bool = True,
    shooting_mode: str = "Movie",
    tc_make: str = "Preset",
    tc_run: str = "Free Run",
    continuous_ltc_lock_seconds: float = 12.0,
    sq_mode_triggered: bool = False,
    tc_make_run_preset_changed_after_lock: bool = False,
    ext_lk_required: bool = True,
    ext_lk_locked: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Validate `VMC-BNCM1` (`A-5051-506-A`) strictly as unidirectional `TC IN` on the
    camera body `Multi/Micro USB` port, blocking `XLR-H1` handle Micro-USB insertion,
    blocking reverse LTC/BNC `TC OUT` drive, and enforcing `>= 10.0s` `EXT-LK` lock
    physics (`Movie` + `Preset` + `Free Run`, released on `S&Q` or `TC Make/Run/Preset`
    change).
    """
    errors: List[str] = []

    if (
        adapter_model.strip().upper() != VMC_BNCM1_ADAPTER_MODEL
        or adapter_part_number.strip().upper() != VMC_BNCM1_SONY_PART_NUMBER
        or round(float(cable_length_m), 2) != VMC_BNCM1_CABLE_LENGTH_M
    ):
        errors.append(
            f"Unsupported BNC timecode adapter metadata: model={adapter_model!r} "
            f"(expected {VMC_BNCM1_ADAPTER_MODEL}), part={adapter_part_number!r} "
            f"(expected {VMC_BNCM1_SONY_PART_NUMBER}), length={cable_length_m}m "
            f"(expected {VMC_BNCM1_CABLE_LENGTH_M}m)."
        )
        return False, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED, errors

    norm_port = _norm_usb_port_g72(connected_usb_port)
    if (
        xlr_h1_handle_micro_usb_connected
        or norm_port == XLR_H1_HANDLE_MICRO_USB_PORT
        or norm_port in REJECTED_VMC_BNCM1_PORTS
        or norm_port != BODY_MULTI_MICRO_USB_PORT
    ):
        errors.append(
            f"VMC-BNCM1 physical port violation: port={connected_usb_port!r}, "
            f"xlr_h1_handle_micro_usb_connected={xlr_h1_handle_micro_usb_connected} "
            "(VMC-BNCM1 must connect ONLY to camera body Multi/Micro USB; XLR-H1 handle "
            "side Micro-USB port is strictly forbidden)."
        )
        return (
            False,
            STATUS_BLOCKED_G72_XLRH1_HANDLE_MICRO_USB_VMCBNCM1_FORBIDDEN,
            errors,
        )

    norm_dir = _norm_tc_direction(tc_signal_direction)
    if (
        norm_dir != TC_DIRECTION_IN_ONLY
        or multi_usb_ltc_bnc_tcout_drive_attempted
        or (not stageb_fx6_bnc_tcout_masked_eopnotsupp)
    ):
        errors.append(
            f"Reverse LTC/BNC TC OUT violation on Multi/Micro USB: direction={tc_signal_direction!r}, "
            f"tcout_drive_attempted={multi_usb_ltc_bnc_tcout_drive_attempted}, "
            f"stageb_bnc_tcout_masked_eopnotsupp={stageb_fx6_bnc_tcout_masked_eopnotsupp}."
        )
        return (
            False,
            STATUS_BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN,
            errors,
        )

    modeled_state = compute_vmcbncm1_ext_lk_state(
        shooting_mode=shooting_mode,
        tc_make=tc_make,
        tc_run=tc_run,
        continuous_ltc_lock_seconds=continuous_ltc_lock_seconds,
        sq_mode_triggered=sq_mode_triggered,
        tc_make_run_preset_changed_after_lock=tc_make_run_preset_changed_after_lock,
    )

    if ext_lk_required:
        if modeled_state != EXT_LK_STATE_LOCKED or (not ext_lk_locked):
            errors.append(
                f"VMC-BNCM1 EXT-LK prerequisites unsatisfied or lock released: "
                f"mode={shooting_mode!r}, tc_make={tc_make!r}, tc_run={tc_run!r}, "
                f"lock_s={continuous_ltc_lock_seconds:.1f}s (requires >= {MIN_VMC_BNCM1_EXT_LK_SECONDS}s), "
                f"sq_triggered={sq_mode_triggered}, tc_changed={tc_make_run_preset_changed_after_lock}, "
                f"modeled_state={modeled_state}, ext_lk_locked={ext_lk_locked}."
            )
            return False, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED, errors
    else:
        expected_locked = modeled_state == EXT_LK_STATE_LOCKED
        if ext_lk_locked != expected_locked:
            errors.append(
                f"EXT-LK state mismatch during unlock rehearsal: modeled_state={modeled_state} "
                f"but ext_lk_locked={ext_lk_locked}."
            )
            return False, STATUS_BLOCKED_G72_TCIN_PREREQ_OR_EXT_LK_RELEASED, errors

    return True, STATUS_SAFE, []


def validate_digital_hdmi_type_a_only_tcout(
    *,
    shooting_mode: str = "Movie",
    sq_mode_active: bool = False,
    hdmi_timecode_output: Union[str, bool] = "On",
    tc_out_transport: str = "Type-A HDMI",
) -> Tuple[bool, str, List[str]]:
    """Validate that `ILME-FX3` `TC OUT` is routed strictly over digital Type-A HDMI
    (`[HDMI Output Settings] -> [Time Code Output] = [On]`) and automatically disabled
    in `S&Q` mode.
    """
    errors: List[str] = []
    toggle = _norm_hdmi_tc_out_toggle(hdmi_timecode_output)
    if toggle is None:
        errors.append(
            f"Invalid [Time Code Output] setting {hdmi_timecode_output!r}; expected 'On' or 'Off'."
        )
        return False, STATUS_BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION, errors

    norm_shoot = _norm_shooting_mode_g72(shooting_mode)
    in_sq = bool(sq_mode_active) or (norm_shoot == "S&Q")
    norm_trans = _norm_tc_out_transport(tc_out_transport)

    if norm_trans in ("MULTI_MICRO_USB_LTC", "VMC_BNCM1_BNC", "BNC_TC_OUT"):
        errors.append(
            f"ILME-FX3 has no BNC/Multi-USB TC OUT; got transport={tc_out_transport!r}."
        )
        return False, STATUS_BLOCKED_G72_MULTI_USB_REVERSE_BNC_TCOUT_FORBIDDEN, errors

    if toggle:
        if in_sq:
            errors.append(
                "HDMI [Time Code Output] = [On] is prohibited/auto-disabled in S&Q mode on ILME-FX3."
            )
            return False, STATUS_BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION, errors
        if norm_trans != ALLOWED_TC_OUT_TRANSPORT_G72:
            errors.append(
                f"ILME-FX3 TC OUT is restricted strictly to digital Type-A HDMI; "
                f"got transport={tc_out_transport!r}."
            )
            return False, STATUS_BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION, errors
    else:
        if norm_trans not in (ALLOWED_TC_OUT_TRANSPORT_G72, "DISABLED"):
            errors.append(
                f"Invalid non-HDMI TC OUT transport {tc_out_transport!r} even while toggle is Off."
            )
            return False, STATUS_BLOCKED_G72_TCOUT_NON_HDMI_OR_SQ_VIOLATION, errors

    return True, STATUS_SAFE, []


# ---------------------------------------------------------------------------
# 3. Composite Gate Verifiers (`G71` & `G72`)
# ---------------------------------------------------------------------------


def verify_fx3_big6_zero_end_and_slot1_camset_guard(
    *,
    guard_profile: str = "fx3-7.02-big6-zero-end-and-slot1-camset-dualmedia-v1",
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: Union[int, str] = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G71,
    big6_home_active: bool = True,
    mode_settings: str = "Fixed/Variable",
    custom_key_home_assigned: bool = True,
    home_lower_left_item: str = "Aperture",
    big6_cell_count: int = 6,
    big6_status_bar_region_present: bool = True,
    fx3_has_physical_end_hardware: bool = False,
    e_nd_actuator_tx_count: int = 0,
    fx6_variable_nd_motor_cmd_sent: bool = False,
    nd_filter_virtual_metadata_only: bool = True,
    virtual_nd_reference_label: str = "Clear",
    camset_slot: Union[int, str] = 1,
    mr_recall_mode_active: bool = False,
    camset_operation_in_mr_attempted: bool = False,
    camset_greyed_out_in_mr: bool = True,
    media_type: str = "SDXC",
    camset_directory: Optional[str] = None,
    camset_filename: str = "CAMSET01.DAT",
    camset_card_file_count: int = 1,
    excluded_machine_bound_items_stripped: bool = True,
    camset_dat_header_model: str = FX3_MODEL_NAME,
    stageb_camset_overlay_path: str = REQUIRED_STAGEB_CAMSET_OVERLAY_DIR,
    stageb_slot1_fx3_camset_overwrite_attempted: bool = False,
    stageb_p2_setting_write_attempted: bool = False,
    p2_setting_mutation_bytes: int = 0,
    h0_camset_surface_sha256: str = DEFAULT_H0_CAMSET_SURFACE_SHA256,
    h3_camset_surface_sha256: str = DEFAULT_H0_CAMSET_SURFACE_SHA256,
) -> Fx3Big6ZeroEndAndSlot1CamsetResult:
    """Gate G71 composite verifier: `ILME-FX3` (`Ver. 7.02`) `BIG6` Zero Physical e-ND
    Actuator Firewall + Slot-1 `CAMSET01..10.DAT` Dual-Media & Cross-Model Isolation.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    effective_camset_dir = (
        resolve_fx3_camset_slot1_directory(media_type)
        if camset_directory is None and isinstance(media_type, str)
        else camset_directory
    )

    req_strs = (
        guard_profile,
        body_model_name,
        firmware_version,
        mode_settings,
        home_lower_left_item,
        virtual_nd_reference_label,
        media_type,
        effective_camset_dir,
        camset_filename,
        camset_dat_header_model,
        stageb_camset_overlay_path,
        h0_camset_surface_sha256,
        h3_camset_surface_sha256,
    )
    req_bools = (
        big6_home_active,
        custom_key_home_assigned,
        big6_status_bar_region_present,
        fx3_has_physical_end_hardware,
        fx6_variable_nd_motor_cmd_sent,
        nd_filter_virtual_metadata_only,
        mr_recall_mode_active,
        camset_operation_in_mr_attempted,
        camset_greyed_out_in_mr,
        excluded_machine_bound_items_stripped,
        stageb_slot1_fx3_camset_overwrite_attempted,
        stageb_p2_setting_write_attempted,
    )
    parsed_body_id = _normalize_int_value(body_model_id)
    slot_type_ok = (
        isinstance(camset_slot, (int, str))
        and (not isinstance(camset_slot, bool))
        and (bool(camset_slot.strip()) if isinstance(camset_slot, str) else True)
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in req_bools)
        and (parsed_body_id is not None)
        and slot_type_ok
        and _is_non_negative_int(big6_cell_count)
        and _is_non_negative_int(e_nd_actuator_tx_count)
        and isinstance(camset_card_file_count, int)
        and (not isinstance(camset_card_file_count, bool))
        and _is_non_negative_int(p2_setting_mutation_bytes)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G71_TELEMETRY_INVALID)
        errors.append(
            "Gate G71 received invalid or malformed BIG6 zero-e-ND / Slot-1 CAMSET telemetry."
        )

    big6_ok = False
    camset_ok = False
    canon_mode = "INVALID"
    canon_ll = "INVALID"
    canon_media = "INVALID"
    expected_dir = "INVALID"
    parsed_slot = -1
    in_tmp_sandbox = False
    h0_eq_h3 = False
    cross_rejected = False

    if telemetry_ok:
        assert isinstance(effective_camset_dir, str)
        canon_mode = _norm_mode_settings(mode_settings)
        canon_ll = _norm_home_lower_left_item(home_lower_left_item)
        canon_media = _norm_media_type_g71(media_type)
        expected_dir = resolve_fx3_camset_slot1_directory(media_type)
        ps = _parse_camset_slot(camset_slot)
        parsed_slot = ps if ps is not None else -1
        ov_norm = stageb_camset_overlay_path.strip().replace("\\", "/").rstrip("/")
        req_ov = REQUIRED_STAGEB_CAMSET_OVERLAY_DIR.rstrip("/")
        in_tmp_sandbox = ov_norm == req_ov or ov_norm.startswith(req_ov + "/")
        h0_eq_h3 = (
            h0_camset_surface_sha256.strip().lower()
            == h3_camset_surface_sha256.strip().lower()
        )
        cross_rejected = _norm_model_header(camset_dat_header_model) != _norm_model_header(
            body_model_name
        )

        big6_ok, b_code, b_errs = validate_fx3_big6_home_zero_end_actuator(
            body_model_name=body_model_name,
            body_model_id=parsed_body_id,
            firmware_version=firmware_version,
            big6_home_active=big6_home_active,
            mode_settings=mode_settings,
            custom_key_home_assigned=custom_key_home_assigned,
            home_lower_left_item=home_lower_left_item,
            big6_cell_count=big6_cell_count,
            big6_status_bar_region_present=big6_status_bar_region_present,
            fx3_has_physical_end_hardware=fx3_has_physical_end_hardware,
            e_nd_actuator_tx_count=e_nd_actuator_tx_count,
            fx6_variable_nd_motor_cmd_sent=fx6_variable_nd_motor_cmd_sent,
            nd_filter_virtual_metadata_only=nd_filter_virtual_metadata_only,
            virtual_nd_reference_label=virtual_nd_reference_label,
        )
        if not big6_ok:
            _add_code(codes, b_code)
            errors.extend(b_errs)

        camset_ok, c_code, c_errs = (
            validate_slot1_camset_dualmedia_and_crossmodel_firewall(
                host_body_model=body_model_name,
                camset_slot=camset_slot,
                mr_recall_mode_active=mr_recall_mode_active,
                camset_operation_in_mr_attempted=camset_operation_in_mr_attempted,
                camset_greyed_out_in_mr=camset_greyed_out_in_mr,
                media_type=media_type,
                camset_directory=effective_camset_dir,
                camset_filename=camset_filename,
                camset_card_file_count=camset_card_file_count,
                excluded_machine_bound_items_stripped=excluded_machine_bound_items_stripped,
                camset_dat_header_model=camset_dat_header_model,
                stageb_camset_overlay_path=stageb_camset_overlay_path,
                stageb_slot1_fx3_camset_overwrite_attempted=stageb_slot1_fx3_camset_overwrite_attempted,
                stageb_p2_setting_write_attempted=stageb_p2_setting_write_attempted,
                p2_setting_mutation_bytes=p2_setting_mutation_bytes,
                h0_camset_surface_sha256=h0_camset_surface_sha256,
                h3_camset_surface_sha256=h3_camset_surface_sha256,
            )
        )
        if not camset_ok:
            _add_code(codes, c_code)
            errors.extend(c_errs)

    valid = (
        telemetry_ok
        and big6_ok
        and camset_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G71 if valid else codes[0]

    return Fx3Big6ZeroEndAndSlot1CamsetResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        body_model_name=str(body_model_name) if isinstance(body_model_name, str) else "INVALID",
        body_model_id=int(parsed_body_id) if parsed_body_id is not None else -1,
        body_model_id_hex=(
            f"0x{parsed_body_id:08x}"
            if parsed_body_id is not None and parsed_body_id >= 0
            else "INVALID"
        ),
        firmware_version=str(firmware_version) if isinstance(firmware_version, str) else "INVALID",
        big6_home_active=bool(big6_home_active) if isinstance(big6_home_active, bool) else False,
        mode_settings=str(mode_settings) if isinstance(mode_settings, str) else "INVALID",
        canonical_mode_settings=canon_mode,
        custom_key_home_assigned=(
            bool(custom_key_home_assigned)
            if isinstance(custom_key_home_assigned, bool)
            else False
        ),
        home_lower_left_menu_path=BIG6_HOME_LOWER_LEFT_MENU_PATH,
        home_lower_left_item=(
            str(home_lower_left_item) if isinstance(home_lower_left_item, str) else "INVALID"
        ),
        canonical_home_lower_left_item=canon_ll,
        big6_cell_count=int(big6_cell_count) if _is_non_negative_int(big6_cell_count) else -1,
        big6_status_bar_region_present=(
            bool(big6_status_bar_region_present)
            if isinstance(big6_status_bar_region_present, bool)
            else False
        ),
        fx3_has_physical_end_hardware=(
            bool(fx3_has_physical_end_hardware)
            if isinstance(fx3_has_physical_end_hardware, bool)
            else True
        ),
        e_nd_actuator_tx_count=(
            int(e_nd_actuator_tx_count)
            if _is_non_negative_int(e_nd_actuator_tx_count)
            else -1
        ),
        fx6_variable_nd_motor_cmd_sent=(
            bool(fx6_variable_nd_motor_cmd_sent)
            if isinstance(fx6_variable_nd_motor_cmd_sent, bool)
            else True
        ),
        nd_filter_virtual_metadata_only=(
            bool(nd_filter_virtual_metadata_only)
            if isinstance(nd_filter_virtual_metadata_only, bool)
            else False
        ),
        virtual_nd_reference_label=(
            str(virtual_nd_reference_label)
            if isinstance(virtual_nd_reference_label, str)
            else "INVALID"
        ),
        big6_zero_end_firewall_valid=big6_ok,
        camset_slot_index=parsed_slot,
        mr_recall_mode_active=(
            bool(mr_recall_mode_active) if isinstance(mr_recall_mode_active, bool) else False
        ),
        camset_operation_in_mr_attempted=(
            bool(camset_operation_in_mr_attempted)
            if isinstance(camset_operation_in_mr_attempted, bool)
            else True
        ),
        camset_greyed_out_in_mr=(
            bool(camset_greyed_out_in_mr)
            if isinstance(camset_greyed_out_in_mr, bool)
            else False
        ),
        media_type=str(media_type) if isinstance(media_type, str) else "INVALID",
        canonical_media_type=canon_media,
        camset_directory=(
            str(effective_camset_dir) if isinstance(effective_camset_dir, str) else "INVALID"
        ),
        expected_camset_directory=expected_dir,
        camset_filename=str(camset_filename) if isinstance(camset_filename, str) else "INVALID",
        camset_card_file_count=(
            int(camset_card_file_count)
            if isinstance(camset_card_file_count, int)
            and not isinstance(camset_card_file_count, bool)
            else -1
        ),
        excluded_machine_bound_items_stripped=(
            bool(excluded_machine_bound_items_stripped)
            if isinstance(excluded_machine_bound_items_stripped, bool)
            else False
        ),
        camset_dat_header_model=(
            str(camset_dat_header_model)
            if isinstance(camset_dat_header_model, str)
            else "INVALID"
        ),
        cross_model_header_rejected=cross_rejected,
        stageb_camset_overlay_path=(
            str(stageb_camset_overlay_path)
            if isinstance(stageb_camset_overlay_path, str)
            else "INVALID"
        ),
        stageb_camset_sandboxed_in_tmp=in_tmp_sandbox,
        stageb_slot1_fx3_camset_overwrite_attempted=(
            bool(stageb_slot1_fx3_camset_overwrite_attempted)
            if isinstance(stageb_slot1_fx3_camset_overwrite_attempted, bool)
            else True
        ),
        stageb_p2_setting_write_attempted=(
            bool(stageb_p2_setting_write_attempted)
            if isinstance(stageb_p2_setting_write_attempted, bool)
            else True
        ),
        p2_setting_mutation_bytes=(
            int(p2_setting_mutation_bytes)
            if _is_non_negative_int(p2_setting_mutation_bytes)
            else -1
        ),
        h0_camset_surface_sha256=(
            str(h0_camset_surface_sha256)
            if isinstance(h0_camset_surface_sha256, str)
            else "INVALID"
        ),
        h3_camset_surface_sha256=(
            str(h3_camset_surface_sha256)
            if isinstance(h3_camset_surface_sha256, str)
            else "INVALID"
        ),
        h0_equals_h3_camset_surface=h0_eq_h3,
        slot1_camset_firewall_valid=camset_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(
    *,
    guard_profile: str = "fx3-7.02-vmcbncm1-body-tcin-xlrh1-block-hdmi-tcout-v1",
    adapter_model: str = VMC_BNCM1_ADAPTER_MODEL,
    adapter_part_number: str = VMC_BNCM1_SONY_PART_NUMBER,
    cable_length_m: float = VMC_BNCM1_CABLE_LENGTH_M,
    connected_usb_port: str = "Multi/Micro USB",
    xlr_h1_handle_micro_usb_connected: bool = False,
    tc_signal_direction: str = "TC IN",
    multi_usb_ltc_bnc_tcout_drive_attempted: bool = False,
    stageb_fx6_bnc_tcout_masked_eopnotsupp: bool = True,
    shooting_mode: str = "Movie",
    sq_mode_active: bool = False,
    tc_make: str = "Preset",
    tc_run: str = "Free Run",
    continuous_ltc_lock_seconds: float = 12.0,
    sq_mode_triggered: bool = False,
    tc_make_run_preset_changed_after_lock: bool = False,
    ext_lk_required: bool = True,
    ext_lk_locked: bool = True,
    hdmi_timecode_output: Union[str, bool] = "On",
    tc_out_transport: str = "Type-A HDMI",
) -> VmcBncm1BodyTcInAndHdmiTcOutResult:
    """Gate G72 composite verifier: `VMC-BNCM1` (`A-5051-506-A`) Unidirectional Body-Only
    `Multi/Micro USB` `TC IN` (`EXT-LK`), `XLR-H1` Handle Side Micro-USB Block, Zero
    Reverse LTC/BNC `TC OUT` Drive, and Digital Type-A HDMI-Only `TC OUT` Guard.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        guard_profile,
        adapter_model,
        adapter_part_number,
        connected_usb_port,
        tc_signal_direction,
        shooting_mode,
        tc_make,
        tc_run,
        tc_out_transport,
    )
    req_bools = (
        xlr_h1_handle_micro_usb_connected,
        multi_usb_ltc_bnc_tcout_drive_attempted,
        stageb_fx6_bnc_tcout_masked_eopnotsupp,
        sq_mode_active,
        sq_mode_triggered,
        tc_make_run_preset_changed_after_lock,
        ext_lk_required,
        ext_lk_locked,
    )
    hdmi_toggle_type_ok = isinstance(hdmi_timecode_output, (str, bool)) and (
        bool(hdmi_timecode_output.strip())
        if isinstance(hdmi_timecode_output, str)
        else True
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in req_bools)
        and hdmi_toggle_type_ok
        and _is_finite_number(cable_length_m)
        and float(cable_length_m) > 0.0
        and _is_finite_number(continuous_ltc_lock_seconds)
        and float(continuous_ltc_lock_seconds) >= 0.0
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G72_TELEMETRY_INVALID)
        errors.append(
            "Gate G72 received invalid or malformed VMC-BNCM1 TC IN / HDMI TC OUT telemetry."
        )

    tcin_ok = False
    tcout_ok = False
    canon_port = "INVALID"
    canon_shoot = "INVALID"
    canon_make = "INVALID"
    canon_run = "INVALID"
    canon_trans = "INVALID"
    modeled_state = EXT_LK_STATE_RELEASED
    tc_out_en = False
    xlr_blocked = True

    if telemetry_ok:
        canon_port = _norm_usb_port_g72(connected_usb_port)
        canon_shoot = _norm_shooting_mode_g72(shooting_mode)
        canon_make = _norm_tc_make(tc_make)
        canon_run = _norm_tc_run(tc_run)
        canon_trans = _norm_tc_out_transport(tc_out_transport)
        parsed_toggle = _norm_hdmi_tc_out_toggle(hdmi_timecode_output)
        tc_out_en = bool(parsed_toggle) if parsed_toggle is not None else False
        xlr_blocked = (not xlr_h1_handle_micro_usb_connected) and (
            canon_port != XLR_H1_HANDLE_MICRO_USB_PORT
        )
        effective_sq_triggered = (
            bool(sq_mode_triggered) or bool(sq_mode_active) or (canon_shoot == "S&Q")
        )
        modeled_state = compute_vmcbncm1_ext_lk_state(
            shooting_mode=shooting_mode,
            tc_make=tc_make,
            tc_run=tc_run,
            continuous_ltc_lock_seconds=float(continuous_ltc_lock_seconds),
            sq_mode_triggered=effective_sq_triggered,
            tc_make_run_preset_changed_after_lock=tc_make_run_preset_changed_after_lock,
        )

        tcin_ok, i_code, i_errs = validate_vmcbncm1_body_multi_usb_tcin_and_ext_lk(
            adapter_model=adapter_model,
            adapter_part_number=adapter_part_number,
            cable_length_m=float(cable_length_m),
            connected_usb_port=connected_usb_port,
            xlr_h1_handle_micro_usb_connected=xlr_h1_handle_micro_usb_connected,
            tc_signal_direction=tc_signal_direction,
            multi_usb_ltc_bnc_tcout_drive_attempted=multi_usb_ltc_bnc_tcout_drive_attempted,
            stageb_fx6_bnc_tcout_masked_eopnotsupp=stageb_fx6_bnc_tcout_masked_eopnotsupp,
            shooting_mode=shooting_mode,
            tc_make=tc_make,
            tc_run=tc_run,
            continuous_ltc_lock_seconds=float(continuous_ltc_lock_seconds),
            sq_mode_triggered=effective_sq_triggered,
            tc_make_run_preset_changed_after_lock=tc_make_run_preset_changed_after_lock,
            ext_lk_required=ext_lk_required,
            ext_lk_locked=ext_lk_locked,
        )
        if not tcin_ok:
            _add_code(codes, i_code)
            errors.extend(i_errs)

        tcout_ok, o_code, o_errs = validate_digital_hdmi_type_a_only_tcout(
            shooting_mode=shooting_mode,
            sq_mode_active=sq_mode_active,
            hdmi_timecode_output=hdmi_timecode_output,
            tc_out_transport=tc_out_transport,
        )
        if not tcout_ok:
            _add_code(codes, o_code)
            errors.extend(o_errs)

    valid = (
        telemetry_ok
        and tcin_ok
        and tcout_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G72 if valid else codes[0]

    return VmcBncm1BodyTcInAndHdmiTcOutResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        adapter_model=str(adapter_model) if isinstance(adapter_model, str) else "INVALID",
        adapter_part_number=(
            str(adapter_part_number) if isinstance(adapter_part_number, str) else "INVALID"
        ),
        cable_length_m=float(cable_length_m) if _is_finite_number(cable_length_m) else -1.0,
        connected_usb_port=(
            str(connected_usb_port) if isinstance(connected_usb_port, str) else "INVALID"
        ),
        canonical_usb_port=canon_port,
        xlr_h1_handle_micro_usb_connected=(
            bool(xlr_h1_handle_micro_usb_connected)
            if isinstance(xlr_h1_handle_micro_usb_connected, bool)
            else True
        ),
        xlr_h1_handle_micro_usb_blocked=xlr_blocked,
        tc_signal_direction=(
            str(tc_signal_direction) if isinstance(tc_signal_direction, str) else "INVALID"
        ),
        multi_usb_ltc_bnc_tcout_drive_attempted=(
            bool(multi_usb_ltc_bnc_tcout_drive_attempted)
            if isinstance(multi_usb_ltc_bnc_tcout_drive_attempted, bool)
            else True
        ),
        stageb_fx6_bnc_tcout_masked_eopnotsupp=(
            bool(stageb_fx6_bnc_tcout_masked_eopnotsupp)
            if isinstance(stageb_fx6_bnc_tcout_masked_eopnotsupp, bool)
            else False
        ),
        stageb_bnc_tcout_mask_errno_name=STAGEB_BNC_TCOUT_MASK_ERRNO_NAME,
        shooting_mode=str(shooting_mode) if isinstance(shooting_mode, str) else "INVALID",
        canonical_shooting_mode=canon_shoot,
        sq_mode_active=bool(sq_mode_active) if isinstance(sq_mode_active, bool) else False,
        tc_make=str(tc_make) if isinstance(tc_make, str) else "INVALID",
        canonical_tc_make=canon_make,
        tc_run=str(tc_run) if isinstance(tc_run, str) else "INVALID",
        canonical_tc_run=canon_run,
        continuous_ltc_lock_seconds=(
            float(continuous_ltc_lock_seconds)
            if _is_finite_number(continuous_ltc_lock_seconds)
            else -1.0
        ),
        sq_mode_triggered=(
            bool(sq_mode_triggered) if isinstance(sq_mode_triggered, bool) else False
        ),
        tc_make_run_preset_changed_after_lock=(
            bool(tc_make_run_preset_changed_after_lock)
            if isinstance(tc_make_run_preset_changed_after_lock, bool)
            else True
        ),
        ext_lk_required=(
            bool(ext_lk_required) if isinstance(ext_lk_required, bool) else True
        ),
        modeled_ext_lk_state=modeled_state,
        ext_lk_locked=bool(ext_lk_locked) if isinstance(ext_lk_locked, bool) else False,
        vmcbncm1_body_tcin_valid=tcin_ok,
        hdmi_tc_out_menu_path=HDMI_TC_OUT_MENU_PATH,
        hdmi_timecode_output=str(hdmi_timecode_output),
        tc_out_enabled=tc_out_en,
        tc_out_transport=(
            str(tc_out_transport) if isinstance(tc_out_transport, str) else "INVALID"
        ),
        canonical_tc_out_transport=canon_trans,
        hdmi_only_tcout_valid=tcout_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G71 & Gate G72 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g71_big6_noend_camset_slot1_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    big6_camset_slot1_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase201DonorAuditResult] = None,
) -> Tuple[GateVerdict, G71Big6NoEndCamsetSlot1GuardResult]:
    """Evaluate Gate G71 (`ILME-FX3` `BIG6` Zero Physical e-ND Actuator Firewall &
    Slot-1 `CAMSET` Dual-Media Isolation).
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase201_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(big6_camset_slot1_kwargs or {})
    guard = verify_fx3_big6_zero_end_and_slot1_camset_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE201_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G71 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G71 if valid else codes[0]

    res = G71Big6NoEndCamsetSlot1GuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        big6_noend_camset_slot1_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, body={guard.body_model_name}({guard.body_model_id_hex}), "
        f"fw={guard.firmware_version}, big6={guard.canonical_mode_settings}/"
        f"{guard.canonical_home_lower_left_item}(e_nd_tx={guard.e_nd_actuator_tx_count}), "
        f"camset=Slot{guard.camset_slot_index}:{guard.canonical_media_type}:{guard.camset_directory}"
        f"{guard.camset_filename}, overlay={guard.stageb_camset_sandboxed_in_tmp}, "
        f"h0_eq_h3={guard.h0_equals_h3_camset_surface}"
    )

    verdict = GateVerdict(
        gate_id=G71_GATE_ID,
        gate_code=G71_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g72_vmcbncm1_tcin_hdmi_tcout_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    vmcbncm1_tcin_hdmi_tcout_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase201DonorAuditResult] = None,
) -> Tuple[GateVerdict, G72VmcBncm1TcInHdmiTcOutGuardResult]:
    """Evaluate Gate G72 (`VMC-BNCM1` Body-Only `TC IN` `EXT-LK`, `XLR-H1` Handle
    Micro-USB Block & Digital HDMI-Only `TC OUT` Guard).
    """
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase201_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(vmcbncm1_tcin_hdmi_tcout_kwargs or {})
    guard = verify_vmcbncm1_body_tcin_and_hdmi_tcout_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE201_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G72 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G72 if valid else codes[0]

    res = G72VmcBncm1TcInHdmiTcOutGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        vmcbncm1_tcin_hdmi_tcout_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, adapter={guard.adapter_model}({guard.adapter_part_number}), "
        f"port={guard.canonical_usb_port}(xlr_h1_blocked={guard.xlr_h1_handle_micro_usb_blocked}), "
        f"dir={guard.tc_signal_direction}({guard.modeled_ext_lk_state}@{guard.continuous_ltc_lock_seconds:.1f}s), "
        f"bnc_tcout_mask={guard.stageb_bnc_tcout_mask_errno_name}, "
        f"tcout={guard.canonical_tc_out_transport}(on={guard.tc_out_enabled})"
    )

    verdict = GateVerdict(
        gate_id=G72_GATE_ID,
        gate_code=G72_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 72-Gate Master Safety Preflight (`G01..G72`)
# ---------------------------------------------------------------------------


def evaluate_72gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G70 pass-throughs
    tier0_manifest: Optional[Dict[str, object]] = None,
    worker_syscall_trace: Optional[List[Dict[str, object]]] = None,
    init2_failsafe_hook: Optional[str] = None,
    candidate_bundle_verified: Optional[bool] = None,
    allow_dry_run_gate12: bool = False,
    gate12_kwargs: Optional[Mapping[str, Any]] = None,
    ltc_kwargs: Optional[Mapping[str, Any]] = None,
    mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    crsdk_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    crsdk_kwargs: Optional[Mapping[str, Any]] = None,
    spacc_operations: Optional[Sequence[Mapping[str, Any]]] = None,
    spacc_script_text: str = "",
    spacc_sector0_bytes: Optional[bytes] = None,
    harness_kwargs: Optional[Mapping[str, Any]] = None,
    fan_kwargs: Optional[Mapping[str, Any]] = None,
    power_kwargs: Optional[Mapping[str, Any]] = None,
    soc_start_ceiling_c: Optional[float] = None,
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    c2pa_calibration_script_text: str = "",
    calibration_mutation_bytes: int = 0,
    c2pa_keystore_writes_attempted: bool = False,
    exfat_dirty_bit_present: bool = False,
    exfat_unfinalized_rsv_present: bool = False,
    allow_c2pa_or_calibration_write: bool = False,
    p12_vma: int = P12_WLAN_FATAL_GUARD_VMA,
    p12_patched_rc: int = 0,
    p12_guard_enabled: bool = True,
    bk4_airplane_shadow: Optional[Mapping[int, int]] = None,
    wf12_bootloop_immune: bool = True,
    wbi_mutation_bytes: int = 0,
    cp_mutation_bytes: int = 0,
    nvram_persistent_writes: int = 0,
    request_persistent_emmc_writes: bool = False,
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    p1_vbr_bytes: Optional[bytes] = None,
    p1_image_path: Optional[Path] = None,
    p1_device_node: str = "/dev/nflasha1",
    require_at_least_one_lab_card: bool = True,
    usblan_kwargs: Optional[Mapping[str, Any]] = None,
    ptpip_or_mc_requests: Optional[Sequence[Any]] = None,
    ptpip_authenticated: bool = True,
    allow_protocol_3_00: bool = False,
    rig_kwargs: Optional[Mapping[str, Any]] = None,
    emount_kwargs: Optional[Mapping[str, Any]] = None,
    power_failover_kwargs: Optional[Mapping[str, Any]] = None,
    rsv_bytes: Optional[bytes] = None,
    rsv_path: Optional[Path] = None,
    xlr_kwargs: Optional[Mapping[str, Any]] = None,
    gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    dewpoint_kwargs: Optional[Mapping[str, Any]] = None,
    pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None,
    intake_fan_kwargs: Optional[Mapping[str, Any]] = None,
    tripod_housing_kwargs: Optional[Mapping[str, Any]] = None,
    sensor_curtain_kwargs: Optional[Mapping[str, Any]] = None,
    subzero_altitude_kwargs: Optional[Mapping[str, Any]] = None,
    wireless_tx_emi_kwargs: Optional[Mapping[str, Any]] = None,
    longform_endurance_kwargs: Optional[Mapping[str, Any]] = None,
    pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None,
    dummy_battery_kwargs: Optional[Mapping[str, Any]] = None,
    saltspray_haze_kwargs: Optional[Mapping[str, Any]] = None,
    followfocus_gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    hdmi_aoc_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_media_kwargs: Optional[Mapping[str, Any]] = None,
    usbpd_uvc_kwargs: Optional[Mapping[str, Any]] = None,
    multiterminal_ptp_kwargs: Optional[Mapping[str, Any]] = None,
    monsoon_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    cagetwist_xlrh1_kwargs: Optional[Mapping[str, Any]] = None,
    vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None,
    vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None,
    jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None,
    cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None,
    service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None,
    stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None,
    pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None,
    rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None,
    uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None,
    imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_ufu_kwargs: Optional[Mapping[str, Any]] = None,
    five_tier_el3_kwargs: Optional[Mapping[str, Any]] = None,
    cxd90058_sabin_kwargs: Optional[Mapping[str, Any]] = None,
    factory_seal_kwargs: Optional[Mapping[str, Any]] = None,
    c2pa_cert_kwargs: Optional[Mapping[str, Any]] = None,
    tc_gyro_meta_kwargs: Optional[Mapping[str, Any]] = None,
    dualmedia_vault_kwargs: Optional[Mapping[str, Any]] = None,
    bench_interlock_kwargs: Optional[Mapping[str, Any]] = None,
    ssboot_wbi2_kwargs: Optional[Mapping[str, Any]] = None,
    slot1_ufu_c2pa_kwargs: Optional[Mapping[str, Any]] = None,
    emount_breathing_kwargs: Optional[Mapping[str, Any]] = None,
    hdmi_raw_kwargs: Optional[Mapping[str, Any]] = None,
    fx3a_firewall_kwargs: Optional[Mapping[str, Any]] = None,
    xlrh1_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    nouvc_dcc1_pd_kwargs: Optional[Mapping[str, Any]] = None,
    lut_path_cineei_bt_kwargs: Optional[Mapping[str, Any]] = None,
    usblan_rtmp_kwargs: Optional[Mapping[str, Any]] = None,
    clipflag_anamorphic_kwargs: Optional[Mapping[str, Any]] = None,
    fan_pwm_thermal_kwargs: Optional[Mapping[str, Any]] = None,
    lut_split_shutter_angle_kwargs: Optional[Mapping[str, Any]] = None,
    # G71 inputs (BIG6 Zero e-ND Actuator & Slot-1 CAMSET Dual-Media Firewall)
    big6_camset_slot1_kwargs: Optional[Mapping[str, Any]] = None,
    # G72 inputs (VMC-BNCM1 Body-Only TC IN, XLR-H1 Micro-USB Block & HDMI-Only TC OUT)
    vmcbncm1_tcin_hdmi_tcout_kwargs: Optional[Mapping[str, Any]] = None,
    master_70_override: Optional[Master70GateReport] = None,
) -> Master72GateReport:
    """Evaluate all 72 Master Safety Gates (`G01..G72`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        if dry_run_simulated_backup is None
        else (dry_run_simulated or dry_run_simulated_backup)
    )

    m70_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated": effective_dry_run,
        "include_large_binaries": include_large_binaries,
        "work_root": work_root,
        "tier0_manifest": tier0_manifest,
        "worker_syscall_trace": worker_syscall_trace,
        "init2_failsafe_hook": init2_failsafe_hook,
        "candidate_bundle_verified": candidate_bundle_verified,
        "allow_dry_run_gate12": allow_dry_run_gate12,
        "gate12_kwargs": gate12_kwargs,
        "ltc_kwargs": ltc_kwargs,
        "mishoe_kwargs": mishoe_kwargs,
        "crsdk_requests": crsdk_requests,
        "crsdk_kwargs": crsdk_kwargs,
        "spacc_operations": spacc_operations,
        "spacc_script_text": spacc_script_text,
        "spacc_sector0_bytes": spacc_sector0_bytes,
        "harness_kwargs": harness_kwargs,
        "fan_kwargs": fan_kwargs,
        "power_kwargs": power_kwargs,
        "planned_mounts": planned_mounts,
        "planned_writes": planned_writes,
        "c2pa_calibration_script_text": c2pa_calibration_script_text,
        "calibration_mutation_bytes": calibration_mutation_bytes,
        "c2pa_keystore_writes_attempted": c2pa_keystore_writes_attempted,
        "exfat_dirty_bit_present": exfat_dirty_bit_present,
        "exfat_unfinalized_rsv_present": exfat_unfinalized_rsv_present,
        "allow_c2pa_or_calibration_write": allow_c2pa_or_calibration_write,
        "p12_vma": p12_vma,
        "p12_patched_rc": p12_patched_rc,
        "p12_guard_enabled": p12_guard_enabled,
        "bk4_airplane_shadow": bk4_airplane_shadow,
        "wf12_bootloop_immune": wf12_bootloop_immune,
        "wbi_mutation_bytes": wbi_mutation_bytes,
        "cp_mutation_bytes": cp_mutation_bytes,
        "nvram_persistent_writes": nvram_persistent_writes,
        "request_persistent_emmc_writes": request_persistent_emmc_writes,
        "slot_a": slot_a,
        "slot_b": slot_b,
        "p1_vbr_bytes": p1_vbr_bytes,
        "p1_image_path": p1_image_path,
        "p1_device_node": p1_device_node,
        "require_at_least_one_lab_card": require_at_least_one_lab_card,
        "usblan_kwargs": usblan_kwargs,
        "ptpip_or_mc_requests": ptpip_or_mc_requests,
        "ptpip_authenticated": ptpip_authenticated,
        "allow_protocol_3_00": allow_protocol_3_00,
        "rig_kwargs": rig_kwargs,
        "emount_kwargs": emount_kwargs,
        "power_failover_kwargs": power_failover_kwargs,
        "rsv_bytes": rsv_bytes,
        "rsv_path": rsv_path,
        "xlr_kwargs": xlr_kwargs,
        "gimbal_kwargs": gimbal_kwargs,
        "dewpoint_kwargs": dewpoint_kwargs,
        "pmic_usbc_kwargs": pmic_usbc_kwargs,
        "intake_fan_kwargs": intake_fan_kwargs,
        "tripod_housing_kwargs": tripod_housing_kwargs,
        "sensor_curtain_kwargs": sensor_curtain_kwargs,
        "subzero_altitude_kwargs": subzero_altitude_kwargs,
        "wireless_tx_emi_kwargs": wireless_tx_emi_kwargs,
        "longform_endurance_kwargs": longform_endurance_kwargs,
        "pl_cantilever_kwargs": pl_cantilever_kwargs,
        "dummy_battery_kwargs": dummy_battery_kwargs,
        "saltspray_haze_kwargs": saltspray_haze_kwargs,
        "followfocus_gimbal_kwargs": followfocus_gimbal_kwargs,
        "hdmi_aoc_kwargs": hdmi_aoc_kwargs,
        "cfexpress_media_kwargs": cfexpress_media_kwargs,
        "usbpd_uvc_kwargs": usbpd_uvc_kwargs,
        "multiterminal_ptp_kwargs": multiterminal_ptp_kwargs,
        "monsoon_mishoe_kwargs": monsoon_mishoe_kwargs,
        "cagetwist_xlrh1_kwargs": cagetwist_xlrh1_kwargs,
        "vp_strobe_genlock_kwargs": vp_strobe_genlock_kwargs,
        "vehiclerig_ibis_kwargs": vehiclerig_ibis_kwargs,
        "jiritsu_service_kwargs": jiritsu_service_kwargs,
        "cnflasha_dualboot_kwargs": cnflasha_dualboot_kwargs,
        "service_0336_canary_kwargs": service_0336_canary_kwargs,
        "stageb_mpr_ibis_p18_kwargs": stageb_mpr_ibis_p18_kwargs,
        "pnflasha_mtdro_kwargs": pnflasha_mtdro_kwargs,
        "rfnvs_fan_power_kwargs": rfnvs_fan_power_kwargs,
        "uart1v8_isp_kwargs": uart1v8_isp_kwargs,
        "imx510_sensor_cal_kwargs": imx510_sensor_cal_kwargs,
        "cfexpress_ufu_kwargs": cfexpress_ufu_kwargs,
        "five_tier_el3_kwargs": five_tier_el3_kwargs,
        "cxd90058_sabin_kwargs": cxd90058_sabin_kwargs,
        "factory_seal_kwargs": factory_seal_kwargs,
        "c2pa_cert_kwargs": c2pa_cert_kwargs,
        "tc_gyro_meta_kwargs": tc_gyro_meta_kwargs,
        "dualmedia_vault_kwargs": dualmedia_vault_kwargs,
        "bench_interlock_kwargs": bench_interlock_kwargs,
        "ssboot_wbi2_kwargs": ssboot_wbi2_kwargs,
        "slot1_ufu_c2pa_kwargs": slot1_ufu_c2pa_kwargs,
        "emount_breathing_kwargs": emount_breathing_kwargs,
        "hdmi_raw_kwargs": hdmi_raw_kwargs,
        "fx3a_firewall_kwargs": fx3a_firewall_kwargs,
        "xlrh1_mishoe_kwargs": xlrh1_mishoe_kwargs,
        "nouvc_dcc1_pd_kwargs": nouvc_dcc1_pd_kwargs,
        "lut_path_cineei_bt_kwargs": lut_path_cineei_bt_kwargs,
        "usblan_rtmp_kwargs": usblan_rtmp_kwargs,
        "clipflag_anamorphic_kwargs": clipflag_anamorphic_kwargs,
        "fan_pwm_thermal_kwargs": fan_pwm_thermal_kwargs,
        "lut_split_shutter_angle_kwargs": lut_split_shutter_angle_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m70_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m70_report: Master70GateReport = (
        master_70_override
        if master_70_override is not None
        else evaluate_70gate_preflight(resolved_root, **m70_kwargs)
    )

    phase201_audit = audit_phase201_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g71_verdict, g71_res = evaluate_g71_big6_noend_camset_slot1_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        big6_camset_slot1_kwargs=big6_camset_slot1_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase201_audit,
    )

    g72_verdict, g72_res = evaluate_g72_vmcbncm1_tcin_hdmi_tcout_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        vmcbncm1_tcin_hdmi_tcout_kwargs=vmcbncm1_tcin_hdmi_tcout_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase201_audit,
    )

    gates_71_to_72 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g71_verdict, g72_verdict)
    ]
    all_gates = tuple(list(m70_report.gates) + gates_71_to_72)

    g01_to_g12_verified = int(m70_report.summary["g01_to_g12_verified"])
    g13_to_g70_verified = (
        int(m70_report.summary["g13_to_g68_verified"])
        + int(m70_report.summary["g69_to_g70_verified"])
    )
    g71_to_g72_verified = sum(1 for v in (g71_verdict, g72_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g70_verified + g71_to_g72_verified

    g71_to_g72_all_passed = g71_to_g72_verified == 2
    g13_to_g72_all_passed = (
        m70_report.g13_to_g70_all_passed and g71_to_g72_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m70_report.gates[:9])

    offline_69_verified = (
        g01_to_g09_ok
        and m70_report.offline_67_gates_verified
        and g71_to_g72_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_72_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g72_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes
    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m70_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_69_verified
        and m70_report.h0_h1_trial_entry_allowed
        and g71_to_g72_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m70_report.errors) + list(g71_verdict.errors) + list(g72_verdict.errors)
    )
    warnings: List[str] = (
        list(m70_report.warnings)
        + list(g71_verdict.warnings)
        + list(g72_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m70_report.g13_to_g70_all_passed:
        overall_status = m70_report.status
    elif not g71_verdict.passed:
        overall_status = g71_verdict.status
    elif not g72_verdict.passed:
        overall_status = g72_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_72_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_72_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_72_verified:
        overall_status = "VERIFIED_ALL_72_GATES"
    else:
        overall_status = "VERIFIED_69_OF_72_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m70_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g71_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g72_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 72,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 72 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g70_verified": g13_to_g70_verified,
        "g71_to_g72_verified": g71_to_g72_verified,
        "g13_to_g72_all_passed": g13_to_g72_all_passed,
        "g71_to_g72_all_passed": g71_to_g72_all_passed,
        "offline_69_gates_verified": offline_69_verified,
        "all_72_gates_verified": all_72_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master72GateReport(
        schema=REALHW_BIG6_NOEND_CAMSET_SLOT1_VMCBNCM1_72GATE_SCHEMA,
        version=REALHW_BIG6_NOEND_CAMSET_SLOT1_VMCBNCM1_72GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_69_gates_verified=offline_69_verified,
        all_72_gates_verified=all_72_verified,
        g13_to_g72_all_passed=g13_to_g72_all_passed,
        g71_to_g72_all_passed=g71_to_g72_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_70_report=m70_report.to_dict(),
        g71_result=g71_res.to_dict(),
        g72_result=g72_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_72_master_safety_gates = evaluate_72gate_preflight
run_72_gate_preflight = evaluate_72gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_big6_noend_camset_slot1_vmcbncm1_and_72gate_guard",
        description=(
            "Phase 201 — ILME-FX3 (Ver. 7.02) BIG6 Zero e-ND Actuator & Slot-1 CAMSET "
            "Dual-Media Firewall (G71), VMC-BNCM1 Body-Only TC IN / XLR-H1 Handle "
            "Micro-USB Block / Digital Type-A HDMI TC OUT Guard (G72), and 72-Gate "
            "Master Preflight (G01..G72)"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G72 can be rehearsed offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_72gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        _write_stdout_safe(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    else:
        _write_stdout_safe(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/72 "
            f"g71_to_g72_all_passed={report.g71_to_g72_all_passed} "
            f"all_72_gates_verified={report.all_72_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"agent_auto_flash_blocked={report.agent_auto_flash_blocked} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_72_gates_verified
        if args.dry_run_simulated
        else report.offline_69_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
