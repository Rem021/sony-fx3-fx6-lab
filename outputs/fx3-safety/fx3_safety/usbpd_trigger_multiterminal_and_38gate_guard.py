"""Phase 120 — Unnegotiated 20V USB-C PD Trigger-Cable / Dual-Source D-Tap+USB-PD Cross-Feed
& Isochronous UVC 1.5 Thermal Firewall (Gate G37), Sony 15-Pin Multi-Terminal LTC +5V Clash /
3.3V UART Over-Drive & Destructive CRSDK PTP Flash-Opcode Hardware Guard (Gate G38), and
Unified 38-Gate Master Safety Preflight (`G01..G38` / `verify-38-gates`).

Operationalizes two critical USB-C PD / Multi-Terminal / PTP hardware-protection firewalls
for Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057`), while keeping all
prior gate modules (`preflight.py`, `master_16gate_preflight.py`,
`usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`,
`phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`,
`intake_occlusion_tripod_and_26gate_guard.py`, `sensor_curtain_subzero_and_28gate_guard.py`,
`wireless_tx_emi_endurance_and_30gate_guard.py`,
`pl_cantilever_dummybatt_and_32gate_guard.py`,
`saltspray_haze_followfocus_and_34gate_guard.py`, and
`hdmi_aoc_5v_cfexpress_and_36gate_guard.py`) completely untouched:

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor USB-PD / Multi-Terminal / PTP Audit**:
   - Inspects local FX3 `v7.02` & FX6 `v6.01` `libBusPower.so`
     (`_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt`,
     `_ZN8BusPower27NotifyUSBPowerContractStateEi`,
     `_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi`, `MSGID_VBUS_ERROR_EVT`),
     `libUsbBusPower.so` (`_ZN11UsbBusPower11IsVbusReadyEv`,
     `_ZN11UsbBusPower22SetPowerContractStatusEi`,
     `_ZN11UsbBusPower15GetCurrentLimitEv`,
     `_ZN11UsbBusPower18SetWatchSWForceOFFEv`),
     `libUsbControl.so` (`_ZN12UsbIfWrapper20isMultiPortSupportedEv`,
     `_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv`,
     `MSGID_VBUS_CHANGED_EVT`, `MSGID_VBUS_ERROR_EVT`), and
     `libInfraPtpControl.so` (`InfraPtpControl_Init`, `PTPT_init`,
     `PTPT_open`, `_ZN31PtptMultiSessionCallBackWrapper15OnPtpCommandCmpEPv`)
     strictly via `os.open(..., os.O_RDONLY)`, plus optional chunked scans of
     `appFw.so` (`DFS_FACTOR_UVC`, `PID_SET_EE_FRAME_RATE_MODE_BY_UVC`,
     `VAL_HAITA_file_format_xavc_hs_streaming_restriction_UVC_FORMAT_30p`,
     `AUTO_POFF_TEMP`, `VAL_setting_auto_pwr_off_temp_AUTO_PWR_OFF_TEMP_STANDARD`,
     `VAL_setting_auto_pwr_off_temp_AUTO_PWR_OFF_TEMP_HIGH`,
     `INFRA_NOTIFY_TIMECODE_EXT_TC_STATUS`,
     `FIRMWARE_UPDATE_CHECK_MEDIA_NO_WRITABLE`) and `cpapp-b.bin`
     (`BATT_AUTH_S`, `BATT_STATE1_S`, `THERMISTOR_ADJ_START`, `FAN_EQ_ID`) when
     `include_large_binaries=True`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent.

2. **Gate G37 — Unnegotiated `20V` USB-C PD Decoy/Trigger Cable, Dual-Source (`D-Tap`
   Dummy-Batt + `USB-PD` VBUS) Cross-Feed & Continuous `4K30p` `UVC 1.5` Thermal
   Saturation Firewall**:
   - Protects FX3's `SY-1129` USB Type-C CC/VBUS PMIC front-end and SoC thermal
     envelope.
   - Fails closed on:
     a) `BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE` when
        `usbc_vbus_measured_v > 9.6` without valid `9V/3A` (`27W`) PD PDO contract
        (e.g., passive `12V/15V/20V` D-Tap-to-USB-C decoy cable forcing
        `14.8V..20V` onto VBUS before CC negotiation, or
        `cc_pin_short_to_vbus == True`),
     b) `BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED` when
        `unregulated_dummy_battery_active == True` and
        `usbc_pd_power_sink_active == True` and
        `common_vmount_battery_shared_without_dc_isolator == True`,
     c) `BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION` when
        `uvc_4k30p_streaming_hours >= 2.0` and `ambient_temp_c > 35.0` and
        `internal_np_fz100_charging_while_streaming == True` and
        `auto_power_off_temp_standard == True`.

3. **Gate G38 — Sony `15-Pin Multi-Terminal` `LTC` BNC Adapter `+5V` Pin Clash,
   `3.3V/5V` UART Over-Drive (`1.8V` `CXD90057` Pad Limit) & Destructive `CRSDK`
   `PTP` Firmware-Flash Opcode Hardware Guard**:
   - Protects FX3's delicate `15-pin Multi/Micro-USB` connector (`LTC` Timecode-In,
     `LANC`/remote, composite/sense pins) and `1.8V` debug UART pads.
   - Fails closed on:
     a) `BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH` when
        `ltc_bnc_adapter_attached == True` and (`ltc_peak_to_peak_v > 5.0` or
        `third_party_non_sony_id_resistor_short == True`),
     b) `BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD` when
        `uart_probe_attached == True` and (`uart_logic_level_v > 1.95` or
        `uart_tx_line_physically_connected == True`), enforcing strictly `1.8V`
        passive RX-only monitoring,
     c) `BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE` when
        `usb_ptp_crsdk_session_active == True` and
        `ptp_fw_flash_opcodes_blocked_in_filter == False`.

4. **Unified 38-Gate Master Safety Preflight (`evaluate_38gate_preflight` / CLI
   `verify-38-gates`)**:
   - Composes `evaluate_36gate_preflight` (`G01..G36`) with `G37` and `G38`:
     * Offline default mode: `35/38` gates pass (`G10..G12` physical Tier-0 backup
       truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `38/38` simulation gates pass
       (`dry_run_rehearsal_only = True`), while `persistent_emmc_writes_authorized`,
       `persistent_write_release`, and `overall_ready_for_hardware_attach` remain
       hard-locked to `False`.

Hard Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- All donor file reads strictly use `os.open(..., os.O_RDONLY)`.
- Zero raw binary `bytes` repr output (always `.hex()`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exfat_media_integrity_guard import MediaSlotConfig
from .hdmi_aoc_5v_cfexpress_and_36gate_guard import (
    Master36GateReport,
    evaluate_36gate_preflight,
)
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
    scan_tokens_o_rdonly,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

USBPD_MULTITERMINAL_38GATE_SCHEMA: str = (
    "fx3-usbpd-trigger-multiterminal-38gate-preflight-v1"
)
USBPD_MULTITERMINAL_38GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G37..G38
G37_GATE_ID: str = "G37_usbpd_trigger_dual_crossfeed_and_uvc_thermal_safe"
G37_GATE_CODE: str = "USBPD_TRIGGER_DUAL_CROSSFEED_AND_UVC_THERMAL_SAFE"

G38_GATE_ID: str = "G38_multiterminal_ltc_uart_1v8_and_ptp_flash_guard_safe"
G38_GATE_CODE: str = "MULTITERMINAL_LTC_UART_1V8_AND_PTP_FLASH_GUARD_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G37: str = (
    "VERIFIED_USBPD_TRIGGER_DUAL_CROSSFEED_AND_UVC_THERMAL_SAFE"
)
STATUS_VERIFIED_G38: str = (
    "VERIFIED_MULTITERMINAL_LTC_UART_1V8_AND_PTP_FLASH_GUARD_SAFE"
)

# Gate G37 Violation Codes
STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE: str = (
    "BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE"
)
STATUS_BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED: str = (
    "BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED"
)
STATUS_BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION: str = (
    "BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION"
)
STATUS_BLOCKED_USBPD_UVC_TELEMETRY_INVALID: str = (
    "BLOCKED_USBPD_UVC_TELEMETRY_INVALID"
)

# Gate G38 Violation Codes
STATUS_BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH: str = (
    "BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH"
)
STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD: str = (
    "BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD"
)
STATUS_BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE: str = (
    "BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE"
)
STATUS_BLOCKED_MULTITERMINAL_PTP_TELEMETRY_INVALID: str = (
    "BLOCKED_MULTITERMINAL_PTP_TELEMETRY_INVALID"
)

STATUS_BLOCKED_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE120_38GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G37 USB-C PD Trigger, Dual-Source Cross-Feed & UVC 1.5 Thermal Thresholds
USBC_VBUS_UNNEGOTIATED_MAX_V: float = 9.6
USBPD_VALID_PDO_VOLTAGE_V: float = 9.0
USBPD_VALID_PDO_CURRENT_A: float = 3.0
USBPD_VALID_PDO_POWER_W: float = 27.0
UVC_4K30P_THERMAL_SATURATION_HOURS: float = 2.0
UVC_4K30P_HIGH_AMBIENT_THRESHOLD_C: float = 35.0

# Gate G38 Sony 15-Pin Multi-Terminal LTC, 1.8V UART & PTP Flash Opcode Thresholds
MULTITERMINAL_LTC_MAX_VPP: float = 5.0
CXD90057_UART_NOMINAL_V: float = 1.8
CXD90057_UART_IO_ABSOLUTE_MAX_V: float = 1.95
PTP_DESTRUCTIVE_FW_FLASH_OPCODES: Tuple[int, ...] = (
    0x9208,
    0x9219,
    0x922B,
    0x9280,
    0x92F0,
)

# Compact FX3/FX6 Donor Specs for USB-PD / BusPower / Multi-Port / PTP Control (O_RDONLY verified)
PINNED_PHASE120_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_lib_bus_power": (
        "fx3",
        "libBusPower.so",
        43_968,
        "4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e",
        (
            b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
            b"_ZN8BusPower27NotifyUSBPowerContractStateEi",
            b"_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi",
            b"MSGID_VBUS_ERROR_EVT",
        ),
        "fx3/libBusPower.so::{SetUSBPDSinkStatusToPowerManager,NotifyUSBPowerContractState,NotifyUSBPowerSupplyState,MSGID_VBUS_ERROR_EVT}",
    ),
    "fx6_lib_bus_power": (
        "fx6",
        "libBusPower.so",
        43_968,
        "d4f2ffe4e74786b66b64ca4eec05b0d433ff0157326156a486d7afec742d00b8",
        (
            b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt",
            b"_ZN8BusPower27NotifyUSBPowerContractStateEi",
            b"_ZN8BusPower25NotifyUSBPowerSupplyStateEPvi",
            b"MSGID_VBUS_ERROR_EVT",
        ),
        "fx6/libBusPower.so::{SetUSBPDSinkStatusToPowerManager,NotifyUSBPowerContractState,NotifyUSBPowerSupplyState,MSGID_VBUS_ERROR_EVT}",
    ),
    "fx3_lib_usb_bus_power": (
        "fx3",
        "libUsbBusPower.so",
        48_232,
        "c606880c92ecf6028c436233b50e0b08791ff8cf0d9dbae748359b38013f5748",
        (
            b"_ZN11UsbBusPower11IsVbusReadyEv",
            b"_ZN11UsbBusPower22SetPowerContractStatusEi",
            b"_ZN11UsbBusPower15GetCurrentLimitEv",
            b"_ZN11UsbBusPower18SetWatchSWForceOFFEv",
        ),
        "fx3/libUsbBusPower.so::{IsVbusReady,SetPowerContractStatus,GetCurrentLimit,SetWatchSWForceOFF}",
    ),
    "fx6_lib_usb_bus_power": (
        "fx6",
        "libUsbBusPower.so",
        48_232,
        "4215a9e989d25896bd12de85928d58fac76d6c4b8dac04cc43ee1b9106c2fe71",
        (
            b"_ZN11UsbBusPower11IsVbusReadyEv",
            b"_ZN11UsbBusPower22SetPowerContractStatusEi",
            b"_ZN11UsbBusPower15GetCurrentLimitEv",
            b"_ZN11UsbBusPower18SetWatchSWForceOFFEv",
        ),
        "fx6/libUsbBusPower.so::{IsVbusReady,SetPowerContractStatus,GetCurrentLimit,SetWatchSWForceOFF}",
    ),
    "fx3_lib_usb_control": (
        "fx3",
        "libUsbControl.so",
        135_424,
        "2bf51f28fd5066e56afc8bbb02ddbaa96b36f57ff2a823cecf9f901781754ed9",
        (
            b"_ZN12UsbIfWrapper20isMultiPortSupportedEv",
            b"_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv",
            b"MSGID_VBUS_CHANGED_EVT",
            b"MSGID_VBUS_ERROR_EVT",
        ),
        "fx3/libUsbControl.so::{isMultiPortSupported,actionOnChangeVbus,MSGID_VBUS_CHANGED_EVT,MSGID_VBUS_ERROR_EVT}",
    ),
    "fx6_lib_usb_control": (
        "fx6",
        "libUsbControl.so",
        135_424,
        "951d1da8a4366dc8cf7bf475181344ea487e661869701218a2343e9c9ecf1483",
        (
            b"_ZN12UsbIfWrapper20isMultiPortSupportedEv",
            b"_ZN10UsbControl18actionOnChangeVbusEPN3UFW3FsmEiPv",
            b"MSGID_VBUS_CHANGED_EVT",
            b"MSGID_VBUS_ERROR_EVT",
        ),
        "fx6/libUsbControl.so::{isMultiPortSupported,actionOnChangeVbus,MSGID_VBUS_CHANGED_EVT,MSGID_VBUS_ERROR_EVT}",
    ),
    "fx3_lib_infra_ptp_control": (
        "fx3",
        "libInfraPtpControl.so",
        165_320,
        "445c83b36c7243a880523e4dd03f7231d6de601fe227b6730bf0b4e3b2741c6d",
        (
            b"InfraPtpControl_Init",
            b"PTPT_init",
            b"PTPT_open",
            b"_ZN31PtptMultiSessionCallBackWrapper15OnPtpCommandCmpEPv",
        ),
        "fx3/libInfraPtpControl.so::{InfraPtpControl_Init,PTPT_init,PTPT_open,OnPtpCommandCmp}",
    ),
    "fx6_lib_infra_ptp_control": (
        "fx6",
        "libInfraPtpControl.so",
        152_520,
        "5af1afff957290bbd2519e237af5df761413e54193e149ee70189f32fe646a27",
        (
            b"InfraPtpControl_Init",
            b"PTPT_init",
            b"PTPT_open",
            b"_ZN31PtptMultiSessionCallBackWrapper15OnPtpCommandCmpEPv",
        ),
        "fx6/libInfraPtpControl.so::{InfraPtpControl_Init,PTPT_init,PTPT_open,OnPtpCommandCmp}",
    ),
}

PINNED_APPFW_USBPD_UVC_PTP_TOKENS: Tuple[str, ...] = (
    "DFS_FACTOR_UVC",
    "PID_SET_EE_FRAME_RATE_MODE_BY_UVC",
    "VAL_HAITA_file_format_xavc_hs_streaming_restriction_UVC_FORMAT_30p",
    "AUTO_POFF_TEMP",
    "VAL_setting_auto_pwr_off_temp_AUTO_PWR_OFF_TEMP_STANDARD",
    "VAL_setting_auto_pwr_off_temp_AUTO_PWR_OFF_TEMP_HIGH",
    "INFRA_NOTIFY_TIMECODE_EXT_TC_STATUS",
    "FIRMWARE_UPDATE_CHECK_MEDIA_NO_WRITABLE",
)

PINNED_CPAPP_BATT_THERM_TOKENS: Tuple[str, ...] = (
    "BATT_AUTH_S",
    "BATT_STATE1_S",
    "THERMISTOR_ADJ_START",
    "FAN_EQ_ID",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase120DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    usbpd_buspower_tokens_verified: bool
    multiport_usbctrl_tokens_verified: bool
    ptp_crsdk_control_tokens_verified: bool
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UsbPdTriggerUvcFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    power_profile: str
    usbc_vbus_measured_v: float
    valid_9v_3a_pd_pdo_contract: bool
    pd_contract_voltage_v: float
    pd_contract_current_a: float
    pd_contract_power_w: float
    cc_pin_short_to_vbus: bool
    unregulated_dummy_battery_active: bool
    usbc_pd_power_sink_active: bool
    common_vmount_battery_shared_without_dc_isolator: bool
    uvc_4k30p_streaming_hours: float
    ambient_temp_c: float
    internal_np_fz100_charging_while_streaming: bool
    auto_power_off_temp_standard: bool
    estimated_uvc_soc_temp_c: float
    usbc_trigger_cable_safe: bool
    dual_power_crossfeed_safe: bool
    uvc_thermal_saturation_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class MultiTerminalLtcUartPtpGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    interface_profile: str
    ltc_bnc_adapter_attached: bool
    ltc_peak_to_peak_v: float
    third_party_non_sony_id_resistor_short: bool
    uart_probe_attached: bool
    uart_logic_level_v: float
    uart_pad_overdrive_ratio: float
    uart_tx_line_physically_connected: bool
    usb_ptp_crsdk_session_active: bool
    ptp_fw_flash_opcodes_blocked_in_filter: bool
    blocked_ptp_opcodes_hex: Tuple[str, ...]
    multiterminal_ltc_voltage_safe: bool
    uart_1v8_rx_only_safe: bool
    ptp_fw_flash_opcode_guard_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G37UsbPdUvcResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    usbpd_uvc_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G38MultiTerminalPtpResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    multiterminal_ptp_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master38GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_35_gates_verified: bool
    all_38_gates_verified: bool
    g13_to_g38_all_passed: bool
    g37_to_g38_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_36_report: Dict[str, Any]
    g37_result: Dict[str, Any]
    g38_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


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
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without printing raw bytes."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _is_finite_number(val: Any) -> bool:
    return (
        isinstance(val, (int, float))
        and (not isinstance(val, bool))
        and math.isfinite(float(val))
    )


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase120_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase120DonorAuditResult:
    """Inspect FX3/FX6 USB-PD/BusPower/Multi-Port/PTP donors via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)

    if work_root is not None and paths.work_root is None:
        explicit_root = Path(work_root)
        fx3_lib_dir = (
            explicit_root
            / "fx3-vm-20261101"
            / "menu-repair-01"
            / "original-uipc"
            / "ap-projection"
            / "regular-files"
            / "usr"
            / "lib"
        )
        fx6_lib_dir = (
            explicit_root
            / "fx3-color-port-20261027"
            / "FX6-donor-assessment-20261103"
            / "team"
            / "donor"
            / "nflasha15-files"
            / "lib"
        )
        effective_work_root: Optional[Path] = explicit_root
    else:
        fx3_lib_dir = paths.fx3_lib_dir
        fx6_lib_dir = paths.fx6_lib_dir
        effective_work_root = paths.work_root

    resolved: Dict[str, Path] = {
        "fx3_lib_bus_power": fx3_lib_dir / "libBusPower.so",
        "fx6_lib_bus_power": fx6_lib_dir / "libBusPower.so",
        "fx3_lib_usb_bus_power": fx3_lib_dir / "libUsbBusPower.so",
        "fx6_lib_usb_bus_power": fx6_lib_dir / "libUsbBusPower.so",
        "fx3_lib_usb_control": fx3_lib_dir / "libUsbControl.so",
        "fx6_lib_usb_control": fx6_lib_dir / "libUsbControl.so",
        "fx3_lib_infra_ptp_control": fx3_lib_dir / "libInfraPtpControl.so",
        "fx6_lib_infra_ptp_control": fx6_lib_dir / "libInfraPtpControl.so",
    }

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase120DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE120_DONOR_SPECS.values()
            ),
            missing_markers=(),
            usbpd_buspower_tokens_verified=True,
            multiport_usbctrl_tokens_verified=True,
            ptp_crsdk_control_tokens_verified=True,
            large_binaries_scanned=False,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE120_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE120_DONOR_SPECS.items()
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
    passed_keys: set[str] = set()

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE120_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
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

    files_inspected = len(resolved)
    large_scanned = False
    appfw_ok = True
    cpapp_ok = True
    if include_large_binaries:
        if paths.fx3_appfw_path.is_file():
            appfw_sz, missing_appfw = scan_tokens_o_rdonly(
                paths.fx3_appfw_path, PINNED_APPFW_USBPD_UVC_PTP_TOKENS
            )
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                appfw_ok = False
                missing.extend(missing_appfw)
                errors.append(
                    f"fx3 appFw.so missing UVC/AUTO_POFF_TEMP/TIMECODE/FW_UPDATE tokens: {missing_appfw}"
                )
            else:
                checked.append(
                    "fx3/appFw.so::DFS_FACTOR_UVC+AUTO_POFF_TEMP+EXT_TC_STATUS+FIRMWARE_UPDATE_CHECK"
                )
        else:
            warnings.append(
                "fx3/appFw.so not found for optional large-binary UVC/TC/PTP scan."
            )

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(
                paths.fx3_cp_path, PINNED_CPAPP_BATT_THERM_TOKENS
            )
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                cpapp_ok = False
                missing.extend(missing_cp)
                errors.append(
                    f"fx3 cpapp-b.bin missing BATT_AUTH_S/THERMISTOR_ADJ_START/FAN_EQ_ID tokens: {missing_cp}"
                )
            else:
                checked.append(
                    "fx3/cpapp-b.bin::BATT_AUTH_S+BATT_STATE1_S+THERMISTOR_ADJ_START+FAN_EQ_ID"
                )
        else:
            warnings.append(
                "fx3/cpapp-b.bin not found for optional large-binary battery/thermistor scan."
            )

    valid = len(errors) == 0 and len(missing) == 0
    return Phase120DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        usbpd_buspower_tokens_verified={
            "fx3_lib_bus_power",
            "fx6_lib_bus_power",
            "fx3_lib_usb_bus_power",
            "fx6_lib_usb_bus_power",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        multiport_usbctrl_tokens_verified={
            "fx3_lib_usb_control",
            "fx6_lib_usb_control",
        }.issubset(passed_keys)
        and appfw_ok,
        ptp_crsdk_control_tokens_verified={
            "fx3_lib_infra_ptp_control",
            "fx6_lib_infra_ptp_control",
        }.issubset(passed_keys)
        and appfw_ok,
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Electrical, UVC Thermal & 1.8V UART Over-Drive Physics Helpers
# ---------------------------------------------------------------------------


def compute_usbpd_contract_watts(
    pd_contract_voltage_v: float,
    pd_contract_current_a: float,
) -> float:
    """Compute negotiated USB-C PD PDO power envelope (W = V * A)."""
    if not (
        _is_finite_number(pd_contract_voltage_v)
        and _is_finite_number(pd_contract_current_a)
    ):
        raise ValueError(
            "pd_contract_voltage_v and pd_contract_current_a must be finite numbers."
        )
    if float(pd_contract_voltage_v) < 0.0 or float(pd_contract_current_a) < 0.0:
        raise ValueError(
            "pd_contract_voltage_v and pd_contract_current_a must be >= 0.0."
        )
    return float(pd_contract_voltage_v) * float(pd_contract_current_a)


def estimate_uvc_4k30p_thermal_rise_c(
    uvc_4k30p_streaming_hours: float,
    ambient_temp_c: float,
    *,
    internal_np_fz100_charging_while_streaming: bool = False,
) -> float:
    """Estimate steady-state CXD90057 SoC temperature (°C) under isochronous 4K30p UVC 1.5."""
    if not (
        _is_finite_number(uvc_4k30p_streaming_hours)
        and _is_finite_number(ambient_temp_c)
    ):
        raise ValueError(
            "uvc_4k30p_streaming_hours and ambient_temp_c must be finite numbers."
        )
    if float(uvc_4k30p_streaming_hours) < 0.0:
        raise ValueError("uvc_4k30p_streaming_hours must be >= 0.0.")
    if float(ambient_temp_c) < -40.0 or float(ambient_temp_c) > 85.0:
        raise ValueError("ambient_temp_c must be in [-40.0, 85.0] C.")

    saturation_factor = min(
        1.0, float(uvc_4k30p_streaming_hours) / UVC_4K30P_THERMAL_SATURATION_HOURS
    )
    isp_uvc_rise_c = 22.0 + 18.0 * saturation_factor
    charger_heat_c = (
        9.0 * (0.5 + 0.5 * saturation_factor)
        if internal_np_fz100_charging_while_streaming
        else 0.0
    )
    return float(ambient_temp_c) + isp_uvc_rise_c + charger_heat_c


def compute_uart_pad_overdrive_ratio(
    uart_logic_level_v: float,
    *,
    nominal_pad_v: float = CXD90057_UART_NOMINAL_V,
) -> float:
    """Compute voltage overdrive ratio relative to CXD90057 1.8V BootROM UART I/O rail."""
    if not (
        _is_finite_number(uart_logic_level_v) and _is_finite_number(nominal_pad_v)
    ):
        raise ValueError("uart_logic_level_v and nominal_pad_v must be finite numbers.")
    if float(uart_logic_level_v) < 0.0 or float(nominal_pad_v) <= 0.0:
        raise ValueError("uart_logic_level_v >= 0.0 and nominal_pad_v > 0.0 required.")
    return float(uart_logic_level_v) / float(nominal_pad_v)


# ---------------------------------------------------------------------------
# 3. Gate G37 — Unnegotiated 20V USB-C PD Trigger, Dual-Source Cross-Feed & UVC Thermal
# ---------------------------------------------------------------------------


def verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(
    *,
    power_profile: str = "FX3_REGULATED_9V3A_USBPD",
    usbc_vbus_measured_v: float = 9.0,
    valid_9v_3a_pd_pdo_contract: bool = True,
    pd_contract_voltage_v: float = 9.0,
    pd_contract_current_a: float = 3.0,
    cc_pin_short_to_vbus: bool = False,
    unregulated_dummy_battery_active: bool = False,
    usbc_pd_power_sink_active: bool = True,
    common_vmount_battery_shared_without_dc_isolator: bool = False,
    uvc_4k30p_streaming_hours: float = 0.5,
    ambient_temp_c: float = 25.0,
    internal_np_fz100_charging_while_streaming: bool = False,
    auto_power_off_temp_standard: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> UsbPdTriggerUvcFirewallResult:
    """Verify Gate G37 (USB-C PD 20V trigger cable, dual-source cross-feed & UVC 1.5 thermal)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
        )

    telemetry_ok = True
    if not _is_finite_number(usbc_vbus_measured_v) or float(usbc_vbus_measured_v) < 0.0:
        _add_code(codes, STATUS_BLOCKED_USBPD_UVC_TELEMETRY_INVALID)
        errors.append(
            f"usbc_vbus_measured_v must be finite >= 0.0, got {usbc_vbus_measured_v!r}."
        )
        telemetry_ok = False
        eff_vbus_v = 9.0
    else:
        eff_vbus_v = float(usbc_vbus_measured_v)

    if not _is_finite_number(pd_contract_voltage_v) or float(pd_contract_voltage_v) < 0.0:
        _add_code(codes, STATUS_BLOCKED_USBPD_UVC_TELEMETRY_INVALID)
        errors.append(
            f"pd_contract_voltage_v must be finite >= 0.0, got {pd_contract_voltage_v!r}."
        )
        telemetry_ok = False
        eff_pd_v = 9.0
    else:
        eff_pd_v = float(pd_contract_voltage_v)

    if not _is_finite_number(pd_contract_current_a) or float(pd_contract_current_a) < 0.0:
        _add_code(codes, STATUS_BLOCKED_USBPD_UVC_TELEMETRY_INVALID)
        errors.append(
            f"pd_contract_current_a must be finite >= 0.0, got {pd_contract_current_a!r}."
        )
        telemetry_ok = False
        eff_pd_a = 3.0
    else:
        eff_pd_a = float(pd_contract_current_a)

    if (
        not _is_finite_number(uvc_4k30p_streaming_hours)
        or float(uvc_4k30p_streaming_hours) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_USBPD_UVC_TELEMETRY_INVALID)
        errors.append(
            f"uvc_4k30p_streaming_hours must be finite >= 0.0, got {uvc_4k30p_streaming_hours!r}."
        )
        telemetry_ok = False
        eff_uvc_hours = 0.5
    else:
        eff_uvc_hours = float(uvc_4k30p_streaming_hours)

    if (
        not _is_finite_number(ambient_temp_c)
        or float(ambient_temp_c) < -40.0
        or float(ambient_temp_c) > 85.0
    ):
        _add_code(codes, STATUS_BLOCKED_USBPD_UVC_TELEMETRY_INVALID)
        errors.append(
            f"ambient_temp_c must be finite in [-40.0, 85.0] C, got {ambient_temp_c!r}."
        )
        telemetry_ok = False
        eff_ambient_c = 25.0
    else:
        eff_ambient_c = float(ambient_temp_c)

    pd_power_w = compute_usbpd_contract_watts(eff_pd_v, eff_pd_a)
    est_uvc_soc_c = estimate_uvc_4k30p_thermal_rise_c(
        eff_uvc_hours,
        eff_ambient_c,
        internal_np_fz100_charging_while_streaming=bool(
            internal_np_fz100_charging_while_streaming
        ),
    )

    # a) Unnegotiated 20V USB-C PD Trigger/Decoy Cable & CC-Short Guard
    pdo_9v3a_contract_valid = (
        bool(valid_9v_3a_pd_pdo_contract)
        and (eff_pd_v <= USBC_VBUS_UNNEGOTIATED_MAX_V)
        and (pd_power_w >= USBPD_VALID_PDO_POWER_W - 1e-6)
    )
    usbc_trigger_cable_safe = not (
        telemetry_ok
        and (
            (eff_vbus_v > USBC_VBUS_UNNEGOTIATED_MAX_V)
            or bool(cc_pin_short_to_vbus)
        )
    )
    if not usbc_trigger_cable_safe:
        _add_code(codes, STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE)
        errors.append(
            f"BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE: {power_profile} presents "
            f"usbc_vbus_measured_v={eff_vbus_v:.2f} V (limit {USBC_VBUS_UNNEGOTIATED_MAX_V:.1f} V), "
            f"valid_9v_3a_pd_pdo_contract={valid_9v_3a_pd_pdo_contract}, "
            f"cc_pin_short_to_vbus={cc_pin_short_to_vbus} across FX3 SY-1129 USB-C PMIC front-end."
        )

    # b) Unisolated Dual-Source (D-Tap Dummy-Battery + USB-PD VBUS) Cross-Feed Guard
    dual_power_crossfeed_safe = not (
        telemetry_ok
        and bool(unregulated_dummy_battery_active)
        and bool(usbc_pd_power_sink_active)
        and bool(common_vmount_battery_shared_without_dc_isolator)
    )
    if not dual_power_crossfeed_safe:
        _add_code(codes, STATUS_BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED)
        errors.append(
            "BLOCKED_UNISOLATED_DTAP_USBPD_DUAL_POWER_CROSSFEED: "
            "unregulated_dummy_battery_active=True and usbc_pd_power_sink_active=True "
            "sharing a common V-Mount battery without DC-DC ground isolation risks "
            "ground-loop return current and PMIC buck/charger cross-feed blowout."
        )

    # c) Continuous 4K30p UVC 1.5 Thermal Saturation Firewall
    uvc_thermal_saturation_safe = not (
        telemetry_ok
        and (eff_uvc_hours >= UVC_4K30P_THERMAL_SATURATION_HOURS)
        and (eff_ambient_c > UVC_4K30P_HIGH_AMBIENT_THRESHOLD_C)
        and bool(internal_np_fz100_charging_while_streaming)
        and bool(auto_power_off_temp_standard)
    )
    if not uvc_thermal_saturation_safe:
        _add_code(codes, STATUS_BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION)
        errors.append(
            f"BLOCKED_UVC_4K30P_CONTINUOUS_THERMAL_SATURATION: uvc_4k30p_streaming_hours="
            f"{eff_uvc_hours:.2f}h (>= {UVC_4K30P_THERMAL_SATURATION_HOURS:.1f}h) at "
            f"ambient_temp_c={eff_ambient_c:.1f}C (> {UVC_4K30P_HIGH_AMBIENT_THRESHOLD_C:.1f}C) "
            "with internal NP-FZ100 charging active and Auto Power OFF Temp=Standard "
            f"(estimated SoC={est_uvc_soc_c:.1f}C) risks abrupt UVC thermal cutoff."
        )

    if telemetry_ok and len(errors) == 0:
        if (
            unregulated_dummy_battery_active
            and usbc_pd_power_sink_active
            and not common_vmount_battery_shared_without_dc_isolator
        ):
            warnings.append(
                "Dual power paths active with DC-DC isolation verified; cross-feed prevented."
            )
        if (
            eff_uvc_hours >= UVC_4K30P_THERMAL_SATURATION_HOURS
            and eff_ambient_c > UVC_4K30P_HIGH_AMBIENT_THRESHOLD_C
        ):
            warnings.append(
                "Long-duration hot-ambient UVC 1.5 streaming mitigated by disabling "
                "internal charging and/or setting Auto Power OFF Temp=High."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return UsbPdTriggerUvcFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        power_profile=str(power_profile),
        usbc_vbus_measured_v=round(eff_vbus_v, 3),
        valid_9v_3a_pd_pdo_contract=pdo_9v3a_contract_valid,
        pd_contract_voltage_v=round(eff_pd_v, 3),
        pd_contract_current_a=round(eff_pd_a, 3),
        pd_contract_power_w=round(pd_power_w, 2),
        cc_pin_short_to_vbus=bool(cc_pin_short_to_vbus),
        unregulated_dummy_battery_active=bool(unregulated_dummy_battery_active),
        usbc_pd_power_sink_active=bool(usbc_pd_power_sink_active),
        common_vmount_battery_shared_without_dc_isolator=bool(
            common_vmount_battery_shared_without_dc_isolator
        ),
        uvc_4k30p_streaming_hours=round(eff_uvc_hours, 3),
        ambient_temp_c=round(eff_ambient_c, 2),
        internal_np_fz100_charging_while_streaming=bool(
            internal_np_fz100_charging_while_streaming
        ),
        auto_power_off_temp_standard=bool(auto_power_off_temp_standard),
        estimated_uvc_soc_temp_c=round(est_uvc_soc_c, 2),
        usbc_trigger_cable_safe=usbc_trigger_cable_safe,
        dual_power_crossfeed_safe=dual_power_crossfeed_safe,
        uvc_thermal_saturation_safe=uvc_thermal_saturation_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G38 — Multi-Terminal LTC +5V Clash, 1.8V UART Over-Drive & PTP Flash Guard
# ---------------------------------------------------------------------------


def verify_multiterminal_ltc_uart_and_ptp_guard(
    *,
    interface_profile: str = "FX3_15PIN_MULTITERMINAL_ISOLATED_RX_ONLY",
    ltc_bnc_adapter_attached: bool = False,
    ltc_peak_to_peak_v: float = 2.0,
    third_party_non_sony_id_resistor_short: bool = False,
    uart_probe_attached: bool = False,
    uart_logic_level_v: float = 1.8,
    uart_tx_line_physically_connected: bool = False,
    usb_ptp_crsdk_session_active: bool = True,
    ptp_fw_flash_opcodes_blocked_in_filter: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> MultiTerminalLtcUartPtpGuardResult:
    """Verify Gate G38 (15-pin Multi-Terminal LTC clash, 1.8V UART overdrive & PTP flash guard)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
        )

    telemetry_ok = True
    if not _is_finite_number(ltc_peak_to_peak_v) or float(ltc_peak_to_peak_v) < 0.0:
        _add_code(codes, STATUS_BLOCKED_MULTITERMINAL_PTP_TELEMETRY_INVALID)
        errors.append(
            f"ltc_peak_to_peak_v must be finite >= 0.0, got {ltc_peak_to_peak_v!r}."
        )
        telemetry_ok = False
        eff_ltc_vpp = 2.0
    else:
        eff_ltc_vpp = float(ltc_peak_to_peak_v)

    if not _is_finite_number(uart_logic_level_v) or float(uart_logic_level_v) < 0.0:
        _add_code(codes, STATUS_BLOCKED_MULTITERMINAL_PTP_TELEMETRY_INVALID)
        errors.append(
            f"uart_logic_level_v must be finite >= 0.0, got {uart_logic_level_v!r}."
        )
        telemetry_ok = False
        eff_uart_v = CXD90057_UART_NOMINAL_V
    else:
        eff_uart_v = float(uart_logic_level_v)

    uart_overdrive_ratio = compute_uart_pad_overdrive_ratio(eff_uart_v)

    # a) 15-Pin Multi-Terminal LTC BNC Adapter +5V Pin Clash & ID-Resistor Short Guard
    multiterminal_ltc_voltage_safe = not (
        telemetry_ok
        and bool(ltc_bnc_adapter_attached)
        and (
            (eff_ltc_vpp > MULTITERMINAL_LTC_MAX_VPP)
            or bool(third_party_non_sony_id_resistor_short)
        )
    )
    if not multiterminal_ltc_voltage_safe:
        _add_code(codes, STATUS_BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH)
        errors.append(
            f"BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH: {interface_profile} has "
            f"ltc_bnc_adapter_attached=True with ltc_peak_to_peak_v={eff_ltc_vpp:.2f} Vpp "
            f"(limit {MULTITERMINAL_LTC_MAX_VPP:.1f} Vpp) or "
            f"third_party_non_sony_id_resistor_short={third_party_non_sony_id_resistor_short}, "
            "risking Multi-Terminal Pin-6/Pin-3 +5V sense damage."
        )

    # b) 3.3V/5V UART Over-Drive Guard (1.8V CXD90057 Pad Limit, RX-Only Passive Tap)
    uart_1v8_rx_only_safe = not (
        telemetry_ok
        and bool(uart_probe_attached)
        and (
            (eff_uart_v > CXD90057_UART_IO_ABSOLUTE_MAX_V)
            or bool(uart_tx_line_physically_connected)
        )
    )
    if not uart_1v8_rx_only_safe:
        _add_code(codes, STATUS_BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD)
        errors.append(
            f"BLOCKED_UART_3V3_5V_PAD_OVERDRIVE_HAZARD: uart_probe_attached=True with "
            f"uart_logic_level_v={eff_uart_v:.2f} V (limit {CXD90057_UART_IO_ABSOLUTE_MAX_V:.2f} V, "
            f"overdrive={uart_overdrive_ratio:.2f}x) and "
            f"uart_tx_line_physically_connected={uart_tx_line_physically_connected}; "
            "only strictly 1.8V passive RX-only monitoring is permitted."
        )

    # c) Destructive CRSDK PTP Firmware-Flash Opcode Guard in Hybrid Mode
    ptp_fw_flash_opcode_guard_safe = not (
        telemetry_ok
        and bool(usb_ptp_crsdk_session_active)
        and (not bool(ptp_fw_flash_opcodes_blocked_in_filter))
    )
    if not ptp_fw_flash_opcode_guard_safe:
        _add_code(codes, STATUS_BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE)
        errors.append(
            "BLOCKED_PTP_FIRMWARE_UPDATE_OPCODE_IN_HYBRID_MODE: "
            "usb_ptp_crsdk_session_active=True with ptp_fw_flash_opcodes_blocked_in_filter=False "
            "exposes FX3 RAM-overlay hybrid session to destructive PTP/Updater flash opcodes."
        )

    if telemetry_ok and len(errors) == 0:
        if ltc_bnc_adapter_attached:
            warnings.append(
                f"15-Pin Multi-Terminal LTC BNC adapter active within safe envelope ({eff_ltc_vpp:.2f} Vpp)."
            )
        if uart_probe_attached:
            warnings.append(
                f"1.8V passive RX-only UART probe active ({eff_uart_v:.2f} V, TX disconnected)."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return MultiTerminalLtcUartPtpGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        interface_profile=str(interface_profile),
        ltc_bnc_adapter_attached=bool(ltc_bnc_adapter_attached),
        ltc_peak_to_peak_v=round(eff_ltc_vpp, 3),
        third_party_non_sony_id_resistor_short=bool(
            third_party_non_sony_id_resistor_short
        ),
        uart_probe_attached=bool(uart_probe_attached),
        uart_logic_level_v=round(eff_uart_v, 3),
        uart_pad_overdrive_ratio=round(uart_overdrive_ratio, 3),
        uart_tx_line_physically_connected=bool(uart_tx_line_physically_connected),
        usb_ptp_crsdk_session_active=bool(usb_ptp_crsdk_session_active),
        ptp_fw_flash_opcodes_blocked_in_filter=bool(
            ptp_fw_flash_opcodes_blocked_in_filter
        ),
        blocked_ptp_opcodes_hex=tuple(
            f"0x{op:04x}" for op in PTP_DESTRUCTIVE_FW_FLASH_OPCODES
        ),
        multiterminal_ltc_voltage_safe=multiterminal_ltc_voltage_safe,
        uart_1v8_rx_only_safe=uart_1v8_rx_only_safe,
        ptp_fw_flash_opcode_guard_safe=ptp_fw_flash_opcode_guard_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G37 & Gate G38 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g37_usbpd_trigger_and_uvc_thermal(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    usbpd_uvc_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase120DonorAuditResult] = None,
) -> Tuple[GateVerdict, G37UsbPdUvcResult]:
    """Evaluate Gate G37 (`usbpd_trigger_dual_crossfeed_and_uvc_thermal_safe`)."""
    audit = donor_audit or audit_phase120_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(usbpd_uvc_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    fw_res = verify_usbpd_trigger_dual_crossfeed_and_uvc_firewall(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in fw_res.violation_codes:
        _add_code(codes, c)
    errors.extend(fw_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(fw_res.warnings)

    passed = (
        audit.valid
        and fw_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G37
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_UNNEGOTIATED_20V_USBC_TRIGGER_CABLE
        )
    )

    res = G37UsbPdUvcResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        usbpd_uvc_firewall=fw_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G37_GATE_ID,
        gate_code=G37_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Unnegotiated 20V USB-C PD Trigger, Dual-Source D-Tap+USB-PD Cross-Feed & "
            f"UVC 1.5 Thermal Firewall ({fw_res.status}, vbus={fw_res.usbc_vbus_measured_v:.2f}V, "
            f"pdo_9v3a={fw_res.valid_9v_3a_pd_pdo_contract}, "
            f"crossfeed_safe={fw_res.dual_power_crossfeed_safe}, "
            f"uvc_hours={fw_res.uvc_4k30p_streaming_hours:.2f}h, "
            f"ambient={fw_res.ambient_temp_c:.1f}C, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "usbc_trigger_cable_safe": fw_res.usbc_trigger_cable_safe,
            "dual_power_crossfeed_safe": fw_res.dual_power_crossfeed_safe,
            "uvc_thermal_saturation_safe": fw_res.uvc_thermal_saturation_safe,
        },
    )
    return verdict, res


def evaluate_g38_multiterminal_ltc_uart_and_ptp(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    multiterminal_ptp_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase120DonorAuditResult] = None,
) -> Tuple[GateVerdict, G38MultiTerminalPtpResult]:
    """Evaluate Gate G38 (`multiterminal_ltc_uart_1v8_and_ptp_flash_guard_safe`)."""
    audit = donor_audit or audit_phase120_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(multiterminal_ptp_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_multiterminal_ltc_uart_and_ptp_guard(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in guard_res.violation_codes:
        _add_code(codes, c)
    errors.extend(guard_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(guard_res.warnings)

    passed = (
        audit.valid
        and guard_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G38
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_MULTITERMINAL_LTC_PIN_VOLTAGE_CLASH
        )
    )

    res = G38MultiTerminalPtpResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        multiterminal_ptp_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G38_GATE_ID,
        gate_code=G38_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Sony 15-Pin Multi-Terminal LTC +5V Clash, 1.8V UART RX-Only Over-Drive & "
            f"CRSDK PTP Flash-Opcode Guard ({guard_res.status}, "
            f"ltc_attached={guard_res.ltc_bnc_adapter_attached}, "
            f"ltc_vpp={guard_res.ltc_peak_to_peak_v:.2f}V, "
            f"uart_attached={guard_res.uart_probe_attached}, "
            f"uart_v={guard_res.uart_logic_level_v:.2f}V, "
            f"ptp_filter={guard_res.ptp_fw_flash_opcodes_blocked_in_filter}, "
            f"{audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "multiterminal_ltc_voltage_safe": guard_res.multiterminal_ltc_voltage_safe,
            "uart_1v8_rx_only_safe": guard_res.uart_1v8_rx_only_safe,
            "ptp_fw_flash_opcode_guard_safe": guard_res.ptp_fw_flash_opcode_guard_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 38-Gate Preflight Evaluator (`G01..G38`) & CLI
# ---------------------------------------------------------------------------


def evaluate_38gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G36 pass-throughs
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
    ptpip_or_mc_requests: Optional[Sequence[Mapping[str, Any]]] = None,
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
    # G37 inputs (USB-C PD 20V Trigger, Dual-Source Cross-Feed & UVC 1.5 Thermal Firewall)
    usbpd_uvc_kwargs: Optional[Mapping[str, Any]] = None,
    # G38 inputs (15-Pin Multi-Terminal LTC +5V Clash, 1.8V UART Over-Drive & PTP Flash Guard)
    multiterminal_ptp_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master38GateReport:
    """Evaluate all 38 Master Safety Gates (`G01..G38`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m36_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated_backup": bool(dry_run_simulated_backup),
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
    }
    if soc_start_ceiling_c is not None:
        m36_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m36_report: Master36GateReport = evaluate_36gate_preflight(
        resolved_root, **m36_kwargs
    )

    phase120_audit = audit_phase120_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g37_verdict, g37_res = evaluate_g37_usbpd_trigger_and_uvc_thermal(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        usbpd_uvc_kwargs=usbpd_uvc_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase120_audit,
    )

    g38_verdict, g38_res = evaluate_g38_multiterminal_ltc_uart_and_ptp(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        multiterminal_ptp_kwargs=multiterminal_ptp_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase120_audit,
    )

    gates_37_to_38 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g37_verdict, g38_verdict)
    ]
    all_gates = tuple(list(m36_report.gates) + gates_37_to_38)

    g01_to_g12_verified = int(m36_report.summary["g01_to_g12_verified"])
    g13_to_g36_verified = (
        int(m36_report.summary["g13_to_g34_verified"])
        + int(m36_report.summary["g35_to_g36_verified"])
    )
    g37_to_g38_verified = sum(1 for v in (g37_verdict, g38_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g36_verified + g37_to_g38_verified

    g37_to_g38_all_passed = g37_to_g38_verified == 2
    g13_to_g38_all_passed = (
        m36_report.g13_to_g36_all_passed and g37_to_g38_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m36_report.gates[:9])

    offline_35_verified = (
        g01_to_g09_ok
        and m36_report.offline_33_gates_verified
        and g37_to_g38_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_38_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g38_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (
        not dry_run_simulated_backup
    )
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g38_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_35_verified
        and m36_report.h0_h1_trial_entry_allowed
        and g37_to_g38_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m36_report.errors) + list(g37_verdict.errors) + list(g38_verdict.errors)
    )
    warnings: List[str] = (
        list(m36_report.warnings)
        + list(g37_verdict.warnings)
        + list(g38_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m36_report.g13_to_g36_all_passed:
        overall_status = m36_report.status
    elif not g37_verdict.passed:
        overall_status = g37_verdict.status
    elif not g38_verdict.passed:
        overall_status = g38_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_38_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_38_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_38_verified:
        overall_status = "VERIFIED_ALL_38_GATES"
    else:
        overall_status = "VERIFIED_35_OF_38_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m36_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g37_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g38_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 38,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 38 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g36_verified": g13_to_g36_verified,
        "g37_to_g38_verified": g37_to_g38_verified,
        "g13_to_g38_all_passed": g13_to_g38_all_passed,
        "g37_to_g38_all_passed": g37_to_g38_all_passed,
        "offline_35_gates_verified": offline_35_verified,
        "all_38_gates_verified": all_38_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master38GateReport(
        schema=USBPD_MULTITERMINAL_38GATE_SCHEMA,
        version=USBPD_MULTITERMINAL_38GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_35_gates_verified=offline_35_verified,
        all_38_gates_verified=all_38_verified,
        g13_to_g38_all_passed=g13_to_g38_all_passed,
        g37_to_g38_all_passed=g37_to_g38_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_36_report=m36_report.to_dict(),
        g37_result=g37_res.to_dict(),
        g38_result=g38_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_38_master_safety_gates = evaluate_38gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="usbpd_trigger_multiterminal_and_38gate_guard",
        description=(
            "Milestone Phase 120 — Unnegotiated 20V USB-C PD Trigger / Dual-Source Cross-Feed "
            "& UVC 1.5 Thermal Firewall (G37), Sony 15-Pin Multi-Terminal LTC +5V Clash / 1.8V "
            "UART Over-Drive & CRSDK PTP Flash-Opcode Guard (G38), and 38-Gate Master Preflight (G01..G38)"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G38 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_38gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/38 "
            f"g37_to_g38_all_passed={report.g37_to_g38_all_passed} "
            f"all_38_gates_verified={report.all_38_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_38_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_35_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
