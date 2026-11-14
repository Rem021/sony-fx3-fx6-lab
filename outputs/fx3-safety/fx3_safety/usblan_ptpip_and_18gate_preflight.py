"""Phase 61 — Wired `USB-LAN` (`CDC-NCM`/`RTL8153` + `PTP-IP 15740` / `Monitor & Control`) Security Firewall & 18-Gate Master Safety Preflight (`G01..G18`).

Operationalizes Phase 57 (`exfat_media_integrity_guard`) and Phase 58
(`Wave-5 USB-LAN / PTP-IP`) findings into `outputs/fx3-safety/`, composing
`master_16gate_preflight.evaluate_16_master_safety_gates` (`G01..G16` untouched)
with two new deterministic gates (`G17` and `G18`):

- `G17` (`EXFAT_BOOTCHECKSUM_AND_CLIENT_MEDIA_ISOLATION`):
  Integrates Phase 57 `exfat_media_integrity_guard` to verify 12-sector
  Microsoft/SDA `exFAT` `BootChecksum`, reject `VolumeDirty` (`0x0002`) /
  `MediaFailure` (`0x0004`), isolate Sony `XDROOT`/`M4ROOT`/`.RSV` client
  production footage on `Slot A`/`Slot B`, and enforce `p1` `FAT12`/`FAT16`
  separation from external `exFAT` media before `H0`/`H1` trial entry.

- `G18` (`USBLAN_PTPIP_FIREWALL_AND_AIRPLANE_COEXISTENCE`):
  Enforces wired-only `USB-LAN` (`CDC-NCM` + `1 Gbps` `RTL8153` / original
  `AX88179` on `eth0`/`usblan0` with FX3 same-subnet Manual gateway checks)
  coexisting with `P12` (`libWlanResource.so @ 0x70d4 -> rc=0`) + `BK4\\0`
  Airplane-Mode wireless silence (`wifi_radio_enabled == False`,
  `/dev/ttyAMA3` Bluetooth UART disabled, `bt_hci_tx_packets == 0`, Sony Notice
  `00342260` `WF-12` bootloop immunity), while fail-closed firewalling `PTP-IP`
  (`TCP 15740`) and `Monitor & Control` (`UDP 1900`, `HTTP/HTTPS`
  `80/443/8080/60152/64321`) to safe shooting/monitoring operations and blocking
  firmware updates (`0x9280..0x92FF`, `SendObjectInfo` `.dat`/`.ufu`, HTTP
  `/fwupdate`), service-mode unlocks, NVRAM `BK4` writes, raw partition
  transfers, and telnet/rsh shells.

Hard Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- All donor file reads strictly use `os.open(..., os.O_RDONLY)`.
- Zero raw binary `bytes` repr output (always `.hex()`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import struct
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .exfat_media_integrity_guard import (
    ExfatMediaIntegrityReport,
    MediaSlotConfig,
    evaluate_exfat_media_integrity_guard,
)
from .master_16gate_preflight import (
    BK4_AIRPLANE_SHADOW_REQUIRED,
    DEFAULT_REPO_ROOT,
    FX6_WLAN_RSRC_DONOR_SHA256,
    FX6_WLAN_RSRC_DONOR_SIZE,
    FX6_WLAN_RSRC_P12_ORIG_HEX,
    FX6_WLAN_RSRC_P12_PATCHED_HEX,
    GateVerdict,
    Master16GateReport,
    P12_WLAN_FATAL_GUARD_VMA,
    evaluate_16_master_safety_gates,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

USBLAN_PTPIP_18GATE_SCHEMA: str = "fx3-usblan-ptpip-18gate-preflight-v1"
USBLAN_PTPIP_18GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G17..G18
G17_GATE_ID: str = "G17_exfat_bootchecksum_and_client_media_isolation"
G17_GATE_CODE: str = "EXFAT_BOOTCHECKSUM_AND_CLIENT_MEDIA_ISOLATION"

G18_GATE_ID: str = "G18_usblan_ptpip_firewall_and_airplane_coexistence"
G18_GATE_CODE: str = "USBLAN_PTPIP_FIREWALL_AND_AIRPLANE_COEXISTENCE"

# Status Codes
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G17: str = "VERIFIED_EXFAT_BOOTCHECKSUM_AND_CLIENT_MEDIA_ISOLATED"
STATUS_VERIFIED_G18: str = "VERIFIED_USBLAN_PTPIP_AND_AIRPLANE_COEXISTENCE"

STATUS_BLOCKED_G17_EXFAT_INTEGRITY: str = "BLOCKED_BY_G17_EXFAT_BOOTCHECKSUM_OR_CLIENT_MEDIA"
STATUS_BLOCKED_G18_USBLAN_AIRPLANE: str = "BLOCKED_BY_G18_USBLAN_OR_AIRPLANE_COEXISTENCE"
STATUS_BLOCKED_G18_PTPIP_FIREWALL: str = "BLOCKED_BY_G18_PTPIP_OR_MC_FIREWALL"

STATUS_BLOCKED_USBLAN_UNSUPPORTED_CLASS: str = "BLOCKED_USBLAN_UNSUPPORTED_USB_CLASS"
STATUS_BLOCKED_USBLAN_INCOMPATIBLE_CHIPSET: str = "BLOCKED_USBLAN_INCOMPATIBLE_CHIPSET_OR_SPEED"
STATUS_BLOCKED_USBLAN_GATEWAY_MISCONFIGURED: str = "BLOCKED_USBLAN_MISSING_SAME_SUBNET_GATEWAY"
STATUS_BLOCKED_USBLAN_WIRELESS_INTERFACE: str = "BLOCKED_USBLAN_WIRELESS_INTERFACE_FORBIDDEN"
STATUS_BLOCKED_WIFI_RADIO_ENABLED: str = "BLOCKED_WIFI_RADIO_ENABLED_WF12_HAZARD"
STATUS_BLOCKED_BT_RADIO_ENABLED: str = "BLOCKED_BLUETOOTH_UART_ENABLED"

STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE: str = "BLOCKED_PTPIP_FIRMWARE_UPDATE_PAYLOAD"
STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK: str = "BLOCKED_PTPIP_SERVICE_MODE_UNLOCK"
STATUS_BLOCKED_PTPIP_NVRAM_WRITE: str = "BLOCKED_PTPIP_NVRAM_BK4_PERSISTENT_WRITE"
STATUS_BLOCKED_PTPIP_RAW_PARTITION: str = "BLOCKED_PTPIP_RAW_PARTITION_TRANSFER"
STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS: str = "BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS_ENDPOINT"
STATUS_BLOCKED_PTPIP_UNKNOWN_OP: str = "BLOCKED_PTPIP_UNKNOWN_OPERATION_FAIL_CLOSED"

STATUS_BLOCKED_DONOR_INTEGRITY: str = "BLOCKED_USBLAN_PTPIP_DONOR_INTEGRITY_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"

# USB-LAN Transport, Chipset & Radio Constants
USB_CLASS_CDC_NCM: str = "CDC-NCM"
USB_CLASS_RNDIS: str = "RNDIS"
USB_CLASS_CDC_ECM: str = "CDC-ECM"

ALLOWED_USBLAN_CHIPSETS_1GBPS: Tuple[str, ...] = ("RTL8153", "AX88179")
REJECTED_USBLAN_CHIPSETS: Tuple[str, ...] = (
    "AX88179A",
    "AX88179B",
    "RTL8156_2.5G",
    "AQC111U_5G",
    "10GBASE_T",
)

BT_UART_TTY_DEVICE: str = "/dev/ttyAMA3"

# PTP-IP (ISO 15740) & Monitor & Control Ports
PTPIP_TCP_PORT: int = 15740
SSDP_UDP_PORT: int = 1900
SONY_SSH_PORT: int = 22
SONY_CONTROL_PORTS: Tuple[int, ...] = (22, 80, 443, 8080, 15740, 60152, 64321)
MC_HTTP_ALLOWED_PORTS: Tuple[int, ...] = (80, 443, 8080, 60152, 64321)
MC_UDP_ALLOWED_PORTS: Tuple[int, ...] = (1900, 8080, 60152, 64321)
DANGEROUS_SHELL_PORTS: Tuple[int, ...] = (23, 512, 513, 514, 2323)
DANGEROUS_SHELL_PROTOCOLS: Tuple[str, ...] = ("telnet", "rsh", "rlogin", "rexec", "nc", "netcat", "raw_shell")

# PTP-IP Framing & Opcodes
PTPIP_PKT_INIT_CMD_REQ: int = 0x00000001
PTPIP_PKT_INIT_CMD_ACK: int = 0x00000002
PTPIP_PKT_CMD_REQ: int = 0x00000006
PTPIP_PKT_CMD_RESP: int = 0x00000007
PTPIP_PKT_EVENT: int = 0x00000008

PTP_OC_GET_DEVICE_INFO: int = 0x1001
PTP_OC_OPEN_SESSION: int = 0x1002
PTP_OC_CLOSE_SESSION: int = 0x1003
PTP_OC_SEND_OBJECT_INFO: int = 0x100C
PTP_OC_SEND_OBJECT: int = 0x100D
PTP_OC_GET_DEVICE_PROP_DESC: int = 0x1014
PTP_OC_GET_DEVICE_PROP_VALUE: int = 0x1015
PTP_OC_GET_EVENT: int = 0x101A

PTP_OC_SONY_SDIO_CONNECT: int = 0x9201
PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO: int = 0x9202
PTP_OC_SONY_GET_DEVICE_PROP_DESC: int = 0x9203
PTP_OC_SONY_GET_DEVICE_PROPERTY_VALUE: int = 0x9204
PTP_OC_SONY_SET_DEVICE_PROP: int = 0x9205
PTP_OC_SONY_GET_CONTROL_DEVICE_DESC: int = 0x9206
PTP_OC_SONY_CONTROL_DEVICE: int = 0x9207
PTP_OC_SONY_GET_LIVE_VIEW: int = 0x9209

SONY_PROTOCOL_2_00: int = 0xC8
SONY_PROTOCOL_3_00: int = 0x12C

PTPIP_RESTRICTED_OPCODE_RANGE: Tuple[int, int] = (0x9280, 0x92FF)

ALLOWED_PTPIP_READONLY_OPCODES: Mapping[int, str] = {
    PTP_OC_GET_DEVICE_INFO: "GetDeviceInfo",
    PTP_OC_OPEN_SESSION: "OpenSession",
    PTP_OC_CLOSE_SESSION: "CloseSession",
    PTP_OC_GET_DEVICE_PROP_DESC: "GetDevicePropDesc",
    PTP_OC_GET_DEVICE_PROP_VALUE: "GetDevicePropValue",
    PTP_OC_GET_EVENT: "GetEvent",
    PTP_OC_SONY_SDIO_CONNECT: "SonySDIOConnect_AccessAuth",
    PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO: "SonySDIOGetExtDeviceInfo",
    PTP_OC_SONY_GET_DEVICE_PROP_DESC: "SonyGetDevicePropDesc",
    PTP_OC_SONY_GET_DEVICE_PROPERTY_VALUE: "SonyGetDevicePropValue",
    PTP_OC_SONY_GET_CONTROL_DEVICE_DESC: "SonyGetControlDeviceDesc",
    PTP_OC_SONY_GET_LIVE_VIEW: "SonyGetLiveView_Waveform_FalseColor",
}

ALLOWED_PTPIP_SAFE_CONTROL_OPCODES: Mapping[int, str] = {
    PTP_OC_SONY_SET_DEVICE_PROP: "SonySetDeviceProp_SafeShooting",
    PTP_OC_SONY_CONTROL_DEVICE: "SonyControlDevice_SafeShooting",
}

ALLOWED_SAFE_PROP_IDS: Tuple[int, ...] = (
    0x5005,  # WhiteBalance
    0xD20D,  # ShutterSpeed / ShutterAngle
    0xD210,  # ISO / ExposureIndex
    0xD21C,  # ColorTemp
    0xD2C1,  # AF Touch Focus X/Y coordinate
    0xD2C2,  # Focus Magnifier / Peaking / Focus Map toggle
    0xD2C3,  # Waveform / False Color overlay request
    0xD2C4,  # Recording Start/Stop telemetry trigger
)

BLOCKED_PTPIP_MUTATION_OPCODES: Mapping[int, str] = {
    0x9280: "SonyFirmwareUpdateInit",
    0x9281: "SonyFirmwareUpdateWrite",
    0x9282: "SonyFirmwareUpdateCommit",
    0x9283: "SonyFirmwarePackageTransfer",
    0x9290: "SonyServiceModeUnlock",
    0x92A0: "SonyAdjustControlServiceExec",
    0x92C0: "SonyRawPartitionTransferInit",
    0x92C1: "SonyRawPartitionBlockWrite",
    0x92F0: "SonyNvramBk4RawWrite",
    0x92F1: "SonyCalibrationPartitionWrite",
    0x92F2: "SonyFactoryResetServiceCmd",
}

SAFE_MC_SHOOTING_PROPS_AND_ACTIONS: Tuple[str, ...] = (
    "GETDEVICEINFO",
    "GETEVENT",
    "OPENSESSION",
    "CLOSESESSION",
    "LIVEVIEW",
    "STARTLIVEVIEW",
    "STOPLIVEVIEW",
    "GETLIVEVIEWFRAME",
    "WAVEFORM",
    "GETWAVEFORMTELEMETRY",
    "FALSECOLOR",
    "FOCUSMAP",
    "ISO",
    "ISOSENSITIVITY",
    "SETISOSPEEDRATE",
    "EI",
    "EXPOSUREINDEX",
    "SETEXPOSUREINDEX",
    "GAINBASEISO",
    "SHUTTER",
    "SHUTTERSPEED",
    "SETSHUTTERSPEED",
    "SHUTTERANGLE",
    "WB",
    "WHITEBALANCE",
    "SETWHITEBALANCE",
    "COLORTEMP",
    "SETCOLORTEMPERATURE",
    "AF_TOUCHFOCUS",
    "TOUCHFOCUS",
    "SETTOUCHAFPOSITION",
    "ACTHALFPRESSSHUTTER",
    "MOVIEREC",
    "STARTMOVIEREC",
    "STOPMOVIEREC",
    "RECSTART",
    "RECSTOP",
    "GETAPPLICATIONINFO",
    "GETVERSIONS",
)

SAFE_MC_HTTP_PATHS: Tuple[str, ...] = (
    "/sony/camera",
    "/liveview",
    "/liveview/stream",
    "/dd.xml",
    "/scalarapi/camera",
)

SAFE_MC_UDP_ACTIONS: Tuple[str, ...] = (
    "M_SEARCH",
    "MSEARCH",
    "NOTIFY",
    "SSDP_DISCOVER",
    "LIVEVIEW_STREAM",
    "WAVEFORM_STREAM",
)

# Fail-closed dangerous token tables (checked BEFORE any allowlist)
DANGEROUS_RAW_PARTITION_TOKENS: Tuple[str, ...] = (
    "/DEV/NFLASHA",
    "/DEV/CNFLASHA",
    "/DEV/PNFLASHA",
    "/DEV/MMCBLK0",
    "/DEV/MTD",
    "/DEV/BOOT0",
    "/DEV/BOOT1",
    "SECTOR0",
    "SPI_NOR",
    "WBI2",
    "CPAPP",
    "P1:/",
    "P2:/",
    "P5:/",
    "P8:/",
    "RAW_PARTITION",
    "EMMC_WRITE",
)

DANGEROUS_NVRAM_BK4_TOKENS: Tuple[str, ...] = (
    "BK4",
    "BACKUP.BIN",
    "BACKUP_BIN",
    "NVRAM",
    "CAMSET",
    "PRODUCT_MODEL",
    "ALCIN_UUD",
    "LENSFILE",
    "PSD.BIN",
    "PSD_BIN",
    "DEFDET",
    "DDRTRAINING",
    "0X019E0012",
    "0X00010000",
    "0X02CF0001",
    "/SETTING/",
)

DANGEROUS_SERVICE_UNLOCK_TOKENS: Tuple[str, ...] = (
    "SERVICE_MODE",
    "SERVICE-MODE",
    "SERVICE_UNLOCK",
    "054C:0336",
    "ADJUSTCONTROL",
    "ADJUST_CONTROL",
    "SENSER",
    "SET_FILE_PATH",
    "0X400F",
    "0X0040",
    "PMCA",
    "UART_BOOT",
    "FASTBOOT",
    "CETUS_",
)

DANGEROUS_FWUPDATE_TOKENS: Tuple[str, ...] = (
    "/FWUPDATE",
    "FWUPDATE",
    "/UPDATER",
    "STARTFIRMWAREUPDATE",
    "UPLOADFIRMWARE",
    "UPDATEFILETRANSFER",
    "FIRMWARE",
    "BODYDATA.DAT",
    "BODYDATA",
    ".UFU",
    ".DAT",
    "FLASH_WRITE",
    "FLASHCP",
)

DANGEROUS_HTTP_OR_SHELL_PATH_TOKENS: Tuple[str, ...] = (
    "/SHELL",
    "/EXEC",
    "/CGI-BIN",
    "/FACTORY",
    "/NVRAM",
    "/SERVICE",
    "DD IF=",
    "RM -RF",
)
_DANGEROUS_SHELL_WORD_RE = re.compile(r"\b(TELNET|RSH|RLOGIN|REXEC|NETCAT|RAW_SHELL)\b")

# Pinned FX6 USB-LAN / PTP-IP / P12 Donor Receipts (strictly O_RDONLY verified)
PINNED_USBLAN_DONOR_SPECS: Mapping[str, Tuple[str, int, str, bytes, str]] = {
    "fx6_cdc_ncm_ko": (
        "kmod/cdc_ncm.ko",
        32_208,
        "8b992509f7a25f6c5d6ca6d27c22c6c2fa4539a25d1b3d405ea7dfc31fb843e2",
        b"cdc_ncm_rx_verify_nth16",
        "cdc_ncm.ko::cdc_ncm_rx_verify_nth16",
    ),
    "fx6_rndis_host_ko": (
        "kmod/rndis_host.ko",
        14_064,
        "f469d8d5624d0afd7a72734e4f651e6a63691c68ebf4cc63ea49df7821e035c4",
        b"RNDIS_MSG_QUERY",
        "rndis_host.ko::RNDIS_MSG_QUERY",
    ),
    "fx6_libnet_service_ether": (
        "lib/libNetServiceEther.so",
        175_376,
        "5bc521ed8845a0be00be7d686b3519de478ca125d00731930624670c6f067dd0",
        b"EN_STATE_USB_CONNECTED_USB_ETHER_DEVICE",
        "libNetServiceEther.so::EN_STATE_USB_CONNECTED_USB_ETHER_DEVICE",
    ),
    "fx6_libinfra_ptp_control": (
        "lib/libInfraPtpControl.so",
        152_520,
        "5af1afff957290bbd2519e237af5df761413e54193e149ee70189f32fe646a27",
        b"PTPT_EE_end_ip_remote",
        "libInfraPtpControl.so::PTPT_EE_end_ip_remote",
    ),
    "fx6_libptp": (
        "lib/libptp.so",
        77_408,
        "21e212ae68a6d8fe1ae8fc4eb40bd3629e3f126a41ddfc1e00e750cd46a134aa",
        b"PTPT_open",
        "libptp.so::PTPT_open",
    ),
    "fx6_libssh_infra_net": (
        "lib/libSshInfraNetworkCommon.so",
        14_568,
        "ab57fe723a05171bc9bdaf4208147b5f7397a419b92c19624f389cde48a0ada4",
        b"InfraSshUtil",
        "libSshInfraNetworkCommon.so::InfraSshUtil",
    ),
    "fx6_libwlan_resource": (
        "lib/libWlanResource.so",
        FX6_WLAN_RSRC_DONOR_SIZE,
        FX6_WLAN_RSRC_DONOR_SHA256,
        b"_Z16handleFatalErrorv",
        "libWlanResource.so::_Z16handleFatalErrorv",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Raw binary bytes never stored or printed; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsbLanDonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    p12_vma_hex: str
    p12_orig_hex: str
    p12_patched_hex: str
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UsbLanAirplaneCoexistenceResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    camera_body: str
    interface_name: str
    usb_class: str
    chipset: str
    link_speed_mbps: int
    ip_mode: str
    camera_ip: str
    subnet_mask: str
    default_gateway: str
    gateway_same_subnet: bool
    wifi_radio_enabled: bool
    wlan_driver_loaded: bool
    bluetooth_uart_enabled: bool
    bt_tty_device: str
    bt_hci_tx_packets: int
    p12_airplane_mode: bool
    p12_guard_verified: bool
    bk4_airplane_shadow_verified: bool
    wf12_00342260_immune: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    monitoring_features: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PtpIpMcOperationDecision:
    protocol: str
    port: int
    interface_name: str
    opcode_hex: str
    operation_name: str
    prop_id_hex: str
    target_detail: str
    classification: str
    allowed: bool
    status: str
    reason: str
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PtpIpMcFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    total_operations: int
    allowed_count: int
    blocked_count: int
    allowed_operations: Tuple[str, ...]
    blocked_operations: Tuple[str, ...]
    decisions: Tuple[PtpIpMcOperationDecision, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G18UsbLanPtpIpResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    usblan_coexistence: Dict[str, Any]
    ptpip_mc_firewall: Dict[str, Any]
    wifi_radio_enabled: bool
    bluetooth_uart_enabled: bool
    wf12_00342260_immune: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master18GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    all_18_gates_verified: bool
    offline_15_gates_verified: bool
    g13_to_g18_all_passed: bool
    g17_to_g18_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_16_report: Dict[str, Any]
    g17_result: Dict[str, Any]
    g18_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers (Strict O_RDONLY, zero raw bytes printing)
# ---------------------------------------------------------------------------


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


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


def _norm_upper(value: str) -> str:
    return re.sub(r"[\s\-]+", "_", value.strip().upper())


def _is_wireless_interface(iface: str) -> bool:
    low = iface.strip().lower()
    return low.startswith(("wlan", "wl", "p2p", "ath", "ra0", "uap"))


def _is_wired_usblan_interface(iface: str) -> bool:
    low = iface.strip().lower()
    return bool(low) and (not _is_wireless_interface(low)) and low.startswith(("eth", "usblan", "en", "usb"))


def _parse_int_opt(val: Any) -> Optional[int]:
    if val is None:
        return None
    if isinstance(val, bool):
        return int(val)
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.strip()
        if not s:
            return None
        return int(s, 0)
    raise ValueError(f"Unsupported integer type: {type(val).__name__}")


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) FX6 USB-LAN / PTP-IP / P12 Donor Audit
# ---------------------------------------------------------------------------


def audit_usblan_ptpip_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> UsbLanDonorAuditResult:
    """Inspect FX6 USB-LAN, PTP-IP & libWlanResource.so donors strictly via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    nflasha15_root = paths.fx6_lib_dir.parent

    resolved: Dict[str, Path] = {
        key: nflasha15_root / spec[0]
        for key, spec in PINNED_USBLAN_DONOR_SPECS.items()
    }
    donor_available = (not clean_forced) and (paths.work_root is not None) and all(p.is_file() for p in resolved.values())

    if not donor_available:
        return UsbLanDonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(spec[4] for spec in PINNED_USBLAN_DONOR_SPECS.values()),
            missing_markers=(),
            sha256_by_artifact={k: spec[2] for k, spec in PINNED_USBLAN_DONOR_SPECS.items()},
            bytes_by_artifact={k: spec[1] for k, spec in PINNED_USBLAN_DONOR_SPECS.items()},
            p12_vma_hex=hex(P12_WLAN_FATAL_GUARD_VMA),
            p12_orig_hex=FX6_WLAN_RSRC_P12_ORIG_HEX,
            p12_patched_hex=FX6_WLAN_RSRC_P12_PATCHED_HEX,
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    p12_orig_hex = ""

    for key, spec in PINNED_USBLAN_DONOR_SPECS.items():
        _rel, exp_size, exp_sha, marker_bytes, marker_label = spec
        blob = _read_file_o_rdonly(resolved[key])
        sha = hashlib.sha256(blob).hexdigest()
        shas[key] = sha
        sizes[key] = len(blob)

        if marker_bytes in blob:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(f"Donor {key} missing required symbol marker {marker_label}.")

        if len(blob) != exp_size or sha != exp_sha:
            errors.append(
                f"Donor {key} integrity mismatch: size={len(blob)} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )

        if key == "fx6_libwlan_resource":
            p12_orig_hex = blob[P12_WLAN_FATAL_GUARD_VMA : P12_WLAN_FATAL_GUARD_VMA + 8].hex()
            if p12_orig_hex != FX6_WLAN_RSRC_P12_ORIG_HEX:
                errors.append(
                    f"libWlanResource.so @ {hex(P12_WLAN_FATAL_GUARD_VMA)} hex={p12_orig_hex} "
                    f"!= expected {FX6_WLAN_RSRC_P12_ORIG_HEX}."
                )

    valid = len(errors) == 0 and len(missing) == 0
    return UsbLanDonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=len(resolved),
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        p12_vma_hex=hex(P12_WLAN_FATAL_GUARD_VMA),
        p12_orig_hex=p12_orig_hex or FX6_WLAN_RSRC_P12_ORIG_HEX,
        p12_patched_hex=FX6_WLAN_RSRC_P12_PATCHED_HEX,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Wired USB-LAN & P12 Airplane-Mode Coexistence Verifier
# ---------------------------------------------------------------------------


def verify_usblan_wired_control_and_airplane_coexistence(
    *,
    camera_body: str = "ILME-FX3",
    interface_name: str = "eth0",
    usb_class: str = USB_CLASS_CDC_NCM,
    chipset: str = "RTL8153",
    link_speed_mbps: int = 1000,
    ip_mode: str = "Manual",
    camera_ip: str = "192.168.0.10",
    subnet_mask: str = "255.255.255.0",
    default_gateway: str = "192.168.0.1",
    wifi_radio_enabled: bool = False,
    wlan_driver_loaded: bool = False,
    bluetooth_uart_enabled: bool = False,
    bt_tty_device: str = BT_UART_TTY_DEVICE,
    bt_hci_tx_packets: int = 0,
    p12_airplane_mode: bool = True,
    p12_guard_enabled: bool = True,
    p12_vma: int = P12_WLAN_FATAL_GUARD_VMA,
    p12_patched_rc: int = 0,
    bk4_airplane_shadow: Optional[Mapping[int, int]] = None,
    wf12_bootloop_immune: bool = True,
    request_persistent_emmc_writes: bool = False,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
) -> UsbLanAirplaneCoexistenceResult:
    """Enforce wired-only USB-LAN (`CDC-NCM` / `RTL8153` / `AX88179`) + `P12` Airplane-Mode radio silence."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC write authorization request blocked: "
            "PERSISTENT_EMMC_WRITES_AUTHORIZED=False, PERSISTENT_WRITE_RELEASE=False."
        )

    # 1. Wired interface check (never wlan0 / p2p0)
    if not _is_wired_usblan_interface(interface_name):
        _add_code(codes, STATUS_BLOCKED_USBLAN_WIRELESS_INTERFACE)
        errors.append(
            f"USB-LAN interface {interface_name!r} is not a wired eth/usblan interface; "
            "wireless interfaces (wlan*/p2p*) are strictly forbidden."
        )

    # 2. USB gadget class check (CDC-NCM only; reject RNDIS / CDC-ECM)
    norm_usb_class = usb_class.strip().upper()
    if norm_usb_class != USB_CLASS_CDC_NCM:
        _add_code(codes, STATUS_BLOCKED_USBLAN_UNSUPPORTED_CLASS)
        errors.append(
            f"Unsupported USB-LAN class {usb_class!r}; FX3/FX6 requires wired CDC-NCM (0x02/0x0D), "
            "rejecting RNDIS / CDC-ECM."
        )

    # 3. Adapter chipset & 1 Gbps speed check
    norm_chipset = chipset.strip().upper()
    if norm_chipset not in ALLOWED_USBLAN_CHIPSETS_1GBPS or int(link_speed_mbps) != 1000:
        _add_code(codes, STATUS_BLOCKED_USBLAN_INCOMPATIBLE_CHIPSET)
        errors.append(
            f"Incompatible USB-LAN adapter chipset={chipset!r} / speed={link_speed_mbps} Mbps; "
            "requires 1000 Mbps RTL8153 or original AX88179 (rejecting AX88179A/B and 2.5G/5G/10G)."
        )

    # 4. IPv4 subnet & FX3 Manual same-subnet Default Gateway rule
    gw_ok = False
    try:
        cam_addr = ipaddress.IPv4Address(camera_ip.strip())
        net = ipaddress.IPv4Network(f"{camera_ip.strip()}/{subnet_mask.strip()}", strict=False)
        if ip_mode.strip().lower() == "manual":
            if not default_gateway.strip():
                gw_ok = False
            else:
                gw_addr = ipaddress.IPv4Address(default_gateway.strip())
                gw_ok = (gw_addr in net) and (gw_addr != cam_addr)
            if not gw_ok:
                _add_code(codes, STATUS_BLOCKED_USBLAN_GATEWAY_MISCONFIGURED)
                errors.append(
                    f"FX3 Manual USB-LAN IP {camera_ip}/{subnet_mask} requires a valid Default Gateway "
                    f"in the same subnet (got {default_gateway!r})."
                )
        else:
            gw_ok = True
            if default_gateway.strip():
                gw_addr = ipaddress.IPv4Address(default_gateway.strip())
                gw_ok = (gw_addr in net) and (gw_addr != cam_addr)
                if not gw_ok:
                    _add_code(codes, STATUS_BLOCKED_USBLAN_GATEWAY_MISCONFIGURED)
                    errors.append(
                        f"Default Gateway {default_gateway!r} is outside subnet {net}."
                    )
    except (ipaddress.AddressValueError, ipaddress.NetmaskValueError, ValueError) as exc:
        gw_ok = False
        _add_code(codes, STATUS_BLOCKED_USBLAN_GATEWAY_MISCONFIGURED)
        errors.append(f"Invalid USB-LAN IPv4 configuration: {exc}")

    # 5. P12 Airplane-Mode & Wireless Radio Silence (Wi-Fi + Bluetooth /dev/ttyAMA3)
    if wifi_radio_enabled or wlan_driver_loaded:
        _add_code(codes, STATUS_BLOCKED_WIFI_RADIO_ENABLED)
        errors.append(
            f"Wi-Fi radio/driver must be 100% disabled under P12 Airplane-Mode "
            f"(wifi_radio_enabled={wifi_radio_enabled}, wlan_driver_loaded={wlan_driver_loaded})."
        )

    if bluetooth_uart_enabled or int(bt_hci_tx_packets) != 0:
        _add_code(codes, STATUS_BLOCKED_BT_RADIO_ENABLED)
        errors.append(
            f"Bluetooth UART ({bt_tty_device}) must remain 100% disabled with 0 HCI TX packets "
            f"(bluetooth_uart_enabled={bluetooth_uart_enabled}, bt_hci_tx_packets={bt_hci_tx_packets})."
        )

    p12_ok = (
        bool(p12_airplane_mode)
        and bool(p12_guard_enabled)
        and (p12_vma == P12_WLAN_FATAL_GUARD_VMA)
        and (int(p12_patched_rc) == 0)
        and bool(wf12_bootloop_immune)
    )
    if not p12_ok:
        _add_code(codes, STATUS_BLOCKED_G18_USBLAN_AIRPLANE)
        errors.append(
            f"P12 WF-12 Airplane-Mode guard mismatch: p12_airplane_mode={p12_airplane_mode}, "
            f"p12_guard_enabled={p12_guard_enabled}, p12_vma={hex(p12_vma)}, "
            f"p12_patched_rc={p12_patched_rc}, wf12_bootloop_immune={wf12_bootloop_immune}."
        )

    shadow = dict(BK4_AIRPLANE_SHADOW_REQUIRED if bk4_airplane_shadow is None else bk4_airplane_shadow)
    bk4_ok = all(shadow.get(k) == expected for k, expected in BK4_AIRPLANE_SHADOW_REQUIRED.items())
    if not bk4_ok:
        _add_code(codes, STATUS_BLOCKED_G18_USBLAN_AIRPLANE)
        errors.append(
            "BK4 Airplane-Mode shadow mismatch: expected {0x019e0012: 0, 0x0051000f: 0, 0x01a20002: 0}, "
            "got " + str({hex(k): v for k, v in shadow.items()})
        )

    wf12_immune = (
        p12_ok
        and bk4_ok
        and (not wifi_radio_enabled)
        and (not wlan_driver_loaded)
        and (not bluetooth_uart_enabled)
        and (int(bt_hci_tx_packets) == 0)
    )

    valid = len(errors) == 0 and wf12_immune
    status = STATUS_VERIFIED_SAFE if valid else (codes[0] if codes else STATUS_BLOCKED_G18_USBLAN_AIRPLANE)
    features: Tuple[str, ...] = (
        (
            "Monitor & Control Live View (eth0)",
            "False Color & Waveform Telemetry",
            "Focus Map & AF Touch-Focus Control",
            "PTP-IP Safe Shooting Control (TCP 15740)",
            "P12 Airplane-Mode Wi-Fi/BT Disabled (00342260 WF-12 Immune)",
        )
        if valid
        else ()
    )

    return UsbLanAirplaneCoexistenceResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=verification_mode,
        camera_body=camera_body,
        interface_name=interface_name,
        usb_class=norm_usb_class,
        chipset=norm_chipset,
        link_speed_mbps=int(link_speed_mbps),
        ip_mode=ip_mode,
        camera_ip=camera_ip,
        subnet_mask=subnet_mask,
        default_gateway=default_gateway,
        gateway_same_subnet=gw_ok,
        wifi_radio_enabled=bool(wifi_radio_enabled),
        wlan_driver_loaded=bool(wlan_driver_loaded),
        bluetooth_uart_enabled=bool(bluetooth_uart_enabled),
        bt_tty_device=bt_tty_device,
        bt_hci_tx_packets=int(bt_hci_tx_packets),
        p12_airplane_mode=bool(p12_airplane_mode),
        p12_guard_verified=p12_ok,
        bk4_airplane_shadow_verified=bk4_ok,
        wf12_00342260_immune=wf12_immune,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        monitoring_features=features,
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "sony_notice_id": "00342260",
            "p12_vma_hex": hex(p12_vma),
            "bk4_airplane_shadow": {hex(k): v for k, v in shadow.items()},
            "control_ports": list(SONY_CONTROL_PORTS),
            "ssdp_udp_port": SSDP_UDP_PORT,
        },
    )


# ---------------------------------------------------------------------------
# 3. Wired PTP-IP (TCP 15740) & Monitor & Control Security Firewall
# ---------------------------------------------------------------------------


def build_ptpip_cmd_request_frame(
    *,
    opcode: int,
    tx_id: int,
    param1: int = 0,
    param2: int = 0,
    data_phase: int = 1,
) -> bytes:
    """Build an ISO 15740 PTP-IP `CmdRequest` packet (`len, type=6, data_phase, opcode, tx_id, p1, p2`)."""
    return struct.pack(
        "<IIIIIII",
        28,
        PTPIP_PKT_CMD_REQ,
        data_phase,
        opcode & 0xFFFF,
        tx_id,
        param1,
        param2,
    )


def _scan_dangerous_payload_tokens(text_upper: str) -> Optional[Tuple[str, str]]:
    for tok in DANGEROUS_RAW_PARTITION_TOKENS:
        if tok in text_upper:
            return STATUS_BLOCKED_PTPIP_RAW_PARTITION, f"raw partition transfer token {tok!r}"
    for tok in DANGEROUS_NVRAM_BK4_TOKENS:
        if tok in text_upper:
            return STATUS_BLOCKED_PTPIP_NVRAM_WRITE, f"NVRAM/BK4 persistent write token {tok!r}"
    for tok in DANGEROUS_SERVICE_UNLOCK_TOKENS:
        if tok in text_upper:
            return STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK, f"service-mode unlock token {tok!r}"
    for tok in DANGEROUS_FWUPDATE_TOKENS:
        if tok in text_upper:
            return STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE, f"network firmware update token {tok!r}"
    for tok in DANGEROUS_HTTP_OR_SHELL_PATH_TOKENS:
        if tok in text_upper:
            return STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS, f"dangerous HTTP/shell token {tok!r}"
    m_shell = _DANGEROUS_SHELL_WORD_RE.search(text_upper)
    if m_shell is not None:
        return STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS, f"dangerous remote shell token {m_shell.group(1)!r}"
    return None


def classify_usblan_ptpip_or_mc_operation(
    operation: Mapping[str, Any],
    *,
    authenticated: bool = True,
    allow_protocol_3_00: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> PtpIpMcOperationDecision:
    """Classify a single PTP-IP (`TCP 15740`) or `Monitor & Control` (`UDP`/`HTTP`) operation fail-closed."""
    protocol = str(operation.get("protocol", "ptpip")).strip().lower() or "ptpip"
    iface = str(operation.get("interface", operation.get("iface", "eth0"))).strip() or "eth0"
    default_port = (
        PTPIP_TCP_PORT
        if protocol == "ptpip"
        else (SSDP_UDP_PORT if protocol in ("udp", "ssdp") else 80)
    )
    try:
        port = _parse_int_opt(operation.get("port"))
        if port is None:
            port = default_port
    except ValueError:
        return PtpIpMcOperationDecision(
            protocol=protocol,
            port=-1,
            interface_name=iface,
            opcode_hex="N/A",
            operation_name="InvalidPort",
            prop_id_hex="0x0000",
            target_detail=str(operation.get("port", "")),
            classification="INVALID_PORT",
            allowed=False,
            status=STATUS_BLOCKED_PTPIP_UNKNOWN_OP,
            reason=f"Invalid port {operation.get('port')!r} rejected fail-closed.",
        )

    try:
        opcode = _parse_int_opt(operation.get("opcode"))
    except ValueError:
        return PtpIpMcOperationDecision(
            protocol=protocol,
            port=port,
            interface_name=iface,
            opcode_hex=str(operation.get("opcode", "")),
            operation_name="InvalidOpcode",
            prop_id_hex="0x0000",
            target_detail="",
            classification="INVALID_OPCODE",
            allowed=False,
            status=STATUS_BLOCKED_PTPIP_UNKNOWN_OP,
            reason=f"Malformed PTP-IP opcode {operation.get('opcode')!r} rejected fail-closed.",
        )

    try:
        prop_id = _parse_int_opt(operation.get("prop_id", operation.get("param1"))) or 0
    except ValueError:
        prop_id = -1

    op_hex = f"0x{opcode:04x}" if opcode is not None else "N/A"
    prop_hex = f"0x{prop_id:04x}" if prop_id >= 0 else "INVALID"

    action_raw = str(
        operation.get("action")
        or operation.get("rpc_method")
        or operation.get("property")
        or operation.get("operation")
        or operation.get("command")
        or ""
    ).strip()
    path_raw = str(operation.get("path", operation.get("uri", operation.get("endpoint", "")))).strip()
    filename_raw = str(operation.get("filename", operation.get("payload", operation.get("target", "")))).strip()
    method_raw = str(operation.get("method", "")).strip().upper()
    combined_detail = " | ".join(part for part in (action_raw, path_raw, filename_raw, method_raw) if part)
    combined_upper = combined_detail.upper()

    # 0. Redline: never authorize persistent eMMC writes
    if (
        request_persistent_emmc_writes
        or bool(operation.get("request_persistent_emmc_writes", False))
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        return PtpIpMcOperationDecision(
            protocol=protocol,
            port=port,
            interface_name=iface,
            opcode_hex=op_hex,
            operation_name=action_raw or "PersistentWriteAttempt",
            prop_id_hex=prop_hex,
            target_detail=combined_detail,
            classification="PERSISTENT_EMMC_WRITE_REDLINE",
            allowed=False,
            status=STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
            reason="Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).",
        )

    # 1. Must arrive over wired USB-LAN interface (never wlan* / p2p*)
    if not _is_wired_usblan_interface(iface):
        return PtpIpMcOperationDecision(
            protocol=protocol,
            port=port,
            interface_name=iface,
            opcode_hex=op_hex,
            operation_name=action_raw or protocol,
            prop_id_hex=prop_hex,
            target_detail=combined_detail,
            classification="WIRELESS_INTERFACE_FORBIDDEN",
            allowed=False,
            status=STATUS_BLOCKED_USBLAN_WIRELESS_INTERFACE,
            reason=f"Traffic on non-wired interface {iface!r} is forbidden; wired USB-LAN eth0/usblan0 only.",
        )

    # 2. Block raw telnet / rsh / rlogin / netcat shells immediately
    if protocol in DANGEROUS_SHELL_PROTOCOLS or port in DANGEROUS_SHELL_PORTS:
        return PtpIpMcOperationDecision(
            protocol=protocol,
            port=port,
            interface_name=iface,
            opcode_hex=op_hex,
            operation_name=action_raw or f"{protocol}:{port}",
            prop_id_hex=prop_hex,
            target_detail=combined_detail,
            classification="DANGEROUS_REMOTE_SHELL",
            allowed=False,
            status=STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS,
            reason=f"Raw shell protocol/port ({protocol}/{port}) is strictly blocked on USB-LAN.",
        )

    # 3. Scan combined path / filename / action / payload for dangerous tokens BEFORE allowlists
    token_hit = _scan_dangerous_payload_tokens(combined_upper)
    if token_hit is not None:
        hit_status, hit_desc = token_hit
        return PtpIpMcOperationDecision(
            protocol=protocol,
            port=port,
            interface_name=iface,
            opcode_hex=op_hex,
            operation_name=action_raw or path_raw or filename_raw or "BlockedOperation",
            prop_id_hex=prop_hex,
            target_detail=combined_detail,
            classification="BLOCKED_DANGEROUS_TOKEN",
            allowed=False,
            status=hit_status,
            reason=f"Blocked fail-closed due to {hit_desc} with PERSISTENT_EMMC_WRITES_AUTHORIZED=False.",
        )

    # 4. Protocol-specific fail-closed enforcement
    if protocol == "ptpip":
        if port != PTPIP_TCP_PORT:
            return PtpIpMcOperationDecision(
                protocol=protocol,
                port=port,
                interface_name=iface,
                opcode_hex=op_hex,
                operation_name=action_raw or "UnexpectedPtpIpPort",
                prop_id_hex=prop_hex,
                target_detail=combined_detail,
                classification="UNEXPECTED_PTPIP_PORT",
                allowed=False,
                status=STATUS_BLOCKED_PTPIP_UNKNOWN_OP,
                reason=f"PTP-IP traffic must use TCP {PTPIP_TCP_PORT}, got {port}.",
            )
        if opcode is None:
            return PtpIpMcOperationDecision(
                protocol=protocol,
                port=port,
                interface_name=iface,
                opcode_hex=op_hex,
                operation_name=action_raw or "MissingOpcode",
                prop_id_hex=prop_hex,
                target_detail=combined_detail,
                classification="MISSING_OPCODE",
                allowed=False,
                status=STATUS_BLOCKED_PTPIP_UNKNOWN_OP,
                reason="Missing PTP-IP opcode rejected fail-closed.",
            )

        # Restricted 0x9280..0x92FF vendor mutation range
        if PTPIP_RESTRICTED_OPCODE_RANGE[0] <= opcode <= PTPIP_RESTRICTED_OPCODE_RANGE[1]:
            op_name = BLOCKED_PTPIP_MUTATION_OPCODES.get(opcode, f"RestrictedSonyVendorOpcode_{op_hex}")
            if opcode <= 0x928F:
                blk_status = STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE
                blk_cls = "BLOCKED_FW_UPDATE_OPCODE"
            elif opcode <= 0x92BF:
                blk_status = STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK
                blk_cls = "BLOCKED_SERVICE_UNLOCK_OPCODE"
            elif opcode <= 0x92DF:
                blk_status = STATUS_BLOCKED_PTPIP_RAW_PARTITION
                blk_cls = "BLOCKED_RAW_PARTITION_OPCODE"
            else:
                blk_status = (
                    STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK
                    if opcode == 0x92F2
                    else STATUS_BLOCKED_PTPIP_NVRAM_WRITE
                )
                blk_cls = "BLOCKED_NVRAM_BK4_OR_FACTORY_OPCODE"
            return PtpIpMcOperationDecision(
                protocol=protocol,
                port=port,
                interface_name=iface,
                opcode_hex=op_hex,
                operation_name=op_name,
                prop_id_hex=prop_hex,
                target_detail=combined_detail,
                classification=blk_cls,
                allowed=False,
                status=blk_status,
                reason=(
                    f"PTP-IP opcode {op_hex} ({op_name}) in restricted 0x9280..0x92FF range "
                    "blocked fail-closed (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
                ),
            )

        # Block SendObjectInfo / SendObject (0x100C / 0x100D) fail-closed
        if opcode in (PTP_OC_SEND_OBJECT_INFO, PTP_OC_SEND_OBJECT):
            return PtpIpMcOperationDecision(
                protocol=protocol,
                port=port,
                interface_name=iface,
                opcode_hex=op_hex,
                operation_name="SendObjectInfo" if opcode == PTP_OC_SEND_OBJECT_INFO else "SendObject",
                prop_id_hex=prop_hex,
                target_detail=combined_detail,
                classification="BLOCKED_OBJECT_TRANSFER",
                allowed=False,
                status=STATUS_BLOCKED_PTPIP_FIRMWARE_UPDATE,
                reason=f"PTP-IP object transfer {op_hex} ({filename_raw or 'payload'}) blocked fail-closed.",
            )

        # Authentication check (allow initial Connect/GetDeviceInfo pre-auth)
        if not authenticated and opcode not in (PTP_OC_SONY_SDIO_CONNECT, PTP_OC_GET_DEVICE_INFO):
            return PtpIpMcOperationDecision(
                protocol=protocol,
                port=port,
                interface_name=iface,
                opcode_hex=op_hex,
                operation_name=ALLOWED_PTPIP_READONLY_OPCODES.get(opcode, "UnauthenticatedOp"),
                prop_id_hex=prop_hex,
                target_detail=combined_detail,
                classification="UNAUTHENTICATED_SESSION",
                allowed=False,
                status=STATUS_BLOCKED_PTPIP_SERVICE_UNLOCK,
                reason=f"Unauthenticated PTP-IP opcode {op_hex} blocked prior to Access Authentication.",
            )

        # Sony 0x9202 protocol 3.00 regression check
        if opcode == PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO:
            proto_ver = _parse_int_opt(operation.get("protocol_version"))
            if proto_ver == SONY_PROTOCOL_3_00 and not allow_protocol_3_00:
                return PtpIpMcOperationDecision(
                    protocol=protocol,
                    port=port,
                    interface_name=iface,
                    opcode_hex=op_hex,
                    operation_name=ALLOWED_PTPIP_READONLY_OPCODES[opcode],
                    prop_id_hex=prop_hex,
                    target_detail=combined_detail,
                    classification="PROTOCOL_3_00_REGRESSION",
                    allowed=False,
                    status=STATUS_BLOCKED_PTPIP_UNKNOWN_OP,
                    reason="SONY_PROTOCOL_3_00 (0x12c) rejected; enforce 0xc8 fallback.",
                )

        # Whitelisted read-only / live-view / event opcodes
        if opcode in ALLOWED_PTPIP_READONLY_OPCODES:
            return PtpIpMcOperationDecision(
                protocol=protocol,
                port=port,
                interface_name=iface,
                opcode_hex=op_hex,
                operation_name=ALLOWED_PTPIP_READONLY_OPCODES[opcode],
                prop_id_hex=prop_hex,
                target_detail=combined_detail,
                classification="ALLOWED_READONLY_TELEMETRY",
                allowed=True,
                status=STATUS_VERIFIED_SAFE,
                reason=f"Whitelisted PTP-IP read-only/monitoring opcode {op_hex}.",
            )

        # Whitelisted safe shooting property / control opcodes (0x9205 / 0x9207)
        if opcode in ALLOWED_PTPIP_SAFE_CONTROL_OPCODES:
            norm_act = _norm_upper(action_raw)
            prop_ok = (prop_id in ALLOWED_SAFE_PROP_IDS) or (norm_act in SAFE_MC_SHOOTING_PROPS_AND_ACTIONS)
            if prop_ok:
                # Extra ShutterAngle millidegrees guard
                if norm_act == "SHUTTERANGLE" and "unit" in operation:
                    unit = str(operation.get("unit", "")).strip().lower()
                    if unit != "millidegrees":
                        return PtpIpMcOperationDecision(
                            protocol=protocol,
                            port=port,
                            interface_name=iface,
                            opcode_hex=op_hex,
                            operation_name=ALLOWED_PTPIP_SAFE_CONTROL_OPCODES[opcode],
                            prop_id_hex=prop_hex,
                            target_detail=combined_detail,
                            classification="SHUTTER_ANGLE_UNIT_MISMATCH",
                            allowed=False,
                            status=STATUS_BLOCKED_PTPIP_UNKNOWN_OP,
                            reason=f"ShutterAngle requires millidegrees, got {unit!r}.",
                        )
                return PtpIpMcOperationDecision(
                    protocol=protocol,
                    port=port,
                    interface_name=iface,
                    opcode_hex=op_hex,
                    operation_name=ALLOWED_PTPIP_SAFE_CONTROL_OPCODES[opcode],
                    prop_id_hex=prop_hex,
                    target_detail=combined_detail,
                    classification="ALLOWED_SAFE_SHOOTING_CONTROL",
                    allowed=True,
                    status=STATUS_VERIFIED_SAFE,
                    reason=f"Whitelisted safe shooting/monitoring control ({action_raw or prop_hex}).",
                )
            return PtpIpMcOperationDecision(
                protocol=protocol,
                port=port,
                interface_name=iface,
                opcode_hex=op_hex,
                operation_name=ALLOWED_PTPIP_SAFE_CONTROL_OPCODES[opcode],
                prop_id_hex=prop_hex,
                target_detail=combined_detail,
                classification="UNWHITELISTED_PROPERTY_FAIL_CLOSED",
                allowed=False,
                status=STATUS_BLOCKED_PTPIP_UNKNOWN_OP,
                reason=f"Unwhitelisted property/control {action_raw or prop_hex!r} blocked fail-closed.",
            )

        return PtpIpMcOperationDecision(
            protocol=protocol,
            port=port,
            interface_name=iface,
            opcode_hex=op_hex,
            operation_name=action_raw or f"UnknownPtpIpOpcode_{op_hex}",
            prop_id_hex=prop_hex,
            target_detail=combined_detail,
            classification="UNKNOWN_PTPIP_OPCODE",
            allowed=False,
            status=STATUS_BLOCKED_PTPIP_UNKNOWN_OP,
            reason=f"Unknown PTP-IP opcode {op_hex} blocked fail-closed.",
        )

    if protocol in ("udp", "ssdp"):
        norm_act = _norm_upper(action_raw or method_raw)
        if port in MC_UDP_ALLOWED_PORTS and norm_act in SAFE_MC_UDP_ACTIONS:
            return PtpIpMcOperationDecision(
                protocol=protocol,
                port=port,
                interface_name=iface,
                opcode_hex=op_hex,
                operation_name=action_raw or method_raw or "SSDP",
                prop_id_hex=prop_hex,
                target_detail=combined_detail,
                classification="ALLOWED_MC_UDP_DISCOVERY_OR_STREAM",
                allowed=True,
                status=STATUS_VERIFIED_SAFE,
                reason=f"Whitelisted Monitor & Control UDP/{port} operation ({action_raw or method_raw}).",
            )
        return PtpIpMcOperationDecision(
            protocol=protocol,
            port=port,
            interface_name=iface,
            opcode_hex=op_hex,
            operation_name=action_raw or f"UDP_{port}",
            prop_id_hex=prop_hex,
            target_detail=combined_detail,
            classification="BLOCKED_UDP_OPERATION",
            allowed=False,
            status=STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS,
            reason=f"Unwhitelisted UDP/{port} operation ({action_raw or method_raw!r}) blocked fail-closed.",
        )

    if protocol in ("http", "https"):
        if port not in MC_HTTP_ALLOWED_PORTS:
            return PtpIpMcOperationDecision(
                protocol=protocol,
                port=port,
                interface_name=iface,
                opcode_hex=op_hex,
                operation_name=f"{method_raw or 'HTTP'} {path_raw}",
                prop_id_hex=prop_hex,
                target_detail=combined_detail,
                classification="BLOCKED_HTTP_PORT",
                allowed=False,
                status=STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS,
                reason=f"HTTP/HTTPS port {port} not in Monitor & Control whitelist {MC_HTTP_ALLOWED_PORTS}.",
            )
        norm_path = path_raw.split("?", 1)[0].rstrip("/").lower() or "/"
        norm_act = _norm_upper(action_raw)
        http_method = method_raw or "GET"
        path_allowed = any(norm_path == p or norm_path.startswith(p + "/") for p in SAFE_MC_HTTP_PATHS)
        if path_allowed and http_method in ("GET", "POST"):
            if http_method == "GET" and (not norm_act or norm_act in SAFE_MC_SHOOTING_PROPS_AND_ACTIONS):
                return PtpIpMcOperationDecision(
                    protocol=protocol,
                    port=port,
                    interface_name=iface,
                    opcode_hex=op_hex,
                    operation_name=f"GET {norm_path}",
                    prop_id_hex=prop_hex,
                    target_detail=combined_detail,
                    classification="ALLOWED_MC_HTTP_READONLY",
                    allowed=True,
                    status=STATUS_VERIFIED_SAFE,
                    reason=f"Whitelisted Monitor & Control HTTP GET {norm_path}.",
                )
            if http_method == "POST" and norm_act in SAFE_MC_SHOOTING_PROPS_AND_ACTIONS:
                return PtpIpMcOperationDecision(
                    protocol=protocol,
                    port=port,
                    interface_name=iface,
                    opcode_hex=op_hex,
                    operation_name=f"POST {norm_path}:{action_raw}",
                    prop_id_hex=prop_hex,
                    target_detail=combined_detail,
                    classification="ALLOWED_MC_HTTP_SHOOTING_RPC",
                    allowed=True,
                    status=STATUS_VERIFIED_SAFE,
                    reason=f"Whitelisted Monitor & Control JSON-RPC {action_raw} on {norm_path}.",
                )
        return PtpIpMcOperationDecision(
            protocol=protocol,
            port=port,
            interface_name=iface,
            opcode_hex=op_hex,
            operation_name=f"{http_method} {path_raw}",
            prop_id_hex=prop_hex,
            target_detail=combined_detail,
            classification="BLOCKED_HTTP_ENDPOINT",
            allowed=False,
            status=STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS,
            reason=f"HTTP endpoint {http_method} {path_raw!r} (action={action_raw!r}) blocked fail-closed.",
        )

    return PtpIpMcOperationDecision(
        protocol=protocol,
        port=port,
        interface_name=iface,
        opcode_hex=op_hex,
        operation_name=action_raw or protocol,
        prop_id_hex=prop_hex,
        target_detail=combined_detail,
        classification="UNSUPPORTED_PROTOCOL_FAIL_CLOSED",
        allowed=False,
        status=STATUS_BLOCKED_MC_HTTP_OR_SHELL_DANGEROUS,
        reason=f"Unsupported USB-LAN protocol {protocol!r} blocked fail-closed.",
    )


def evaluate_ptpip_15740_packet(
    frame: bytes,
    *,
    tcp_port: int = PTPIP_TCP_PORT,
    interface_name: str = "eth0",
    authenticated: bool = True,
    filename_hint: str = "",
) -> PtpIpMcOperationDecision:
    """Decode a binary ISO 15740 PTP-IP `CmdRequest` frame and enforce fail-closed policy."""
    if len(frame) < 20:
        raise ValueError(f"PTP-IP frame too short: {len(frame)} < 20")
    pkt_len, _pkt_type, _data_phase, opcode_raw, _tx_id = struct.unpack_from("<IIIII", frame, 0)
    if pkt_len != len(frame):
        raise ValueError(f"PTP-IP length mismatch: header={pkt_len}, actual={len(frame)}")
    opcode = opcode_raw & 0xFFFF
    prop_id = struct.unpack_from("<I", frame, 20)[0] if len(frame) >= 24 else 0
    return classify_usblan_ptpip_or_mc_operation(
        {
            "protocol": "ptpip",
            "port": tcp_port,
            "interface": interface_name,
            "opcode": opcode,
            "prop_id": prop_id,
            "filename": filename_hint,
        },
        authenticated=authenticated,
    )


def default_safe_usblan_ptpip_session() -> Tuple[Dict[str, Any], ...]:
    """Deterministic safe shooting & monitoring USB-LAN / PTP-IP / M&C session trace."""
    return (
        {"protocol": "udp", "port": SSDP_UDP_PORT, "interface": "eth0", "action": "M-SEARCH"},
        {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "interface": "eth0", "opcode": PTP_OC_SONY_SDIO_CONNECT},
        {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "interface": "eth0", "opcode": PTP_OC_GET_DEVICE_INFO},
        {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "interface": "eth0", "opcode": PTP_OC_OPEN_SESSION},
        {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "interface": "eth0", "opcode": PTP_OC_GET_EVENT},
        {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "interface": "eth0", "opcode": PTP_OC_SONY_GET_LIVE_VIEW},
        {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "interface": "eth0", "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "prop_id": 0xD210, "property": "ExposureIndex"},
        {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "interface": "eth0", "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "prop_id": 0xD20D, "property": "ShutterAngle", "unit": "millidegrees"},
        {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "interface": "eth0", "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "prop_id": 0x5005, "property": "WhiteBalance"},
        {"protocol": "ptpip", "port": PTPIP_TCP_PORT, "interface": "eth0", "opcode": PTP_OC_SONY_SET_DEVICE_PROP, "prop_id": 0xD2C1, "property": "AF_TouchFocus"},
        {"protocol": "http", "port": 8080, "interface": "eth0", "method": "POST", "path": "/sony/camera", "action": "getWaveformTelemetry"},
        {"protocol": "http", "port": 8080, "interface": "eth0", "method": "GET", "path": "/liveview/stream"},
    )


def audit_usblan_ptpip_and_mc_firewall(
    operations: Optional[Sequence[Mapping[str, Any]]] = None,
    *,
    authenticated: bool = True,
    allow_protocol_3_00: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> PtpIpMcFirewallResult:
    """Audit a sequence of USB-LAN PTP-IP & Monitor & Control operations fail-closed."""
    ops = tuple(default_safe_usblan_ptpip_session() if operations is None else operations)
    decisions: List[PtpIpMcOperationDecision] = []
    allowed_ops: List[str] = []
    blocked_ops: List[str] = []
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes cannot be authorized via USB-LAN PTP-IP / M&C.")

    for op in ops:
        dec = classify_usblan_ptpip_or_mc_operation(
            op,
            authenticated=authenticated,
            allow_protocol_3_00=allow_protocol_3_00,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
        )
        decisions.append(dec)
        label = f"{dec.protocol}:{dec.port}/{dec.opcode_hex}:{dec.operation_name}"
        if dec.allowed:
            allowed_ops.append(label)
        else:
            blocked_ops.append(label)
            _add_code(codes, dec.status)
            errors.append(dec.reason)

    valid = (len(blocked_ops) == 0) and (len(errors) == 0) and (len(decisions) > 0)
    if len(decisions) == 0:
        _add_code(codes, STATUS_BLOCKED_G18_PTPIP_FIREWALL)
        errors.append("Empty USB-LAN PTP-IP operation sequence rejected fail-closed.")
    status = STATUS_VERIFIED_SAFE if valid else (codes[0] if codes else STATUS_BLOCKED_G18_PTPIP_FIREWALL)

    return PtpIpMcFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        total_operations=len(decisions),
        allowed_count=len(allowed_ops),
        blocked_count=len(blocked_ops),
        allowed_operations=tuple(allowed_ops),
        blocked_operations=tuple(blocked_ops),
        decisions=tuple(decisions),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate 17 & Gate 18 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g17_exfat_and_client_media_isolation(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    p1_vbr_bytes: Optional[bytes] = None,
    p1_image_path: Optional[Path] = None,
    p1_device_node: str = "/dev/nflasha1",
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    require_at_least_one_lab_card: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> Tuple[GateVerdict, ExfatMediaIntegrityReport]:
    """Evaluate Gate G17 (`EXFAT_BOOTCHECKSUM_AND_CLIENT_MEDIA_ISOLATION`)."""
    rep = evaluate_exfat_media_integrity_guard(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        slot_a=slot_a,
        slot_b=slot_b,
        p1_vbr_bytes=p1_vbr_bytes,
        p1_image_path=p1_image_path,
        p1_device_node=p1_device_node,
        planned_mounts=planned_mounts,
        planned_writes=planned_writes,
        require_at_least_one_lab_card=require_at_least_one_lab_card,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    codes = list(rep.violation_codes)
    errors = list(rep.errors)
    if rep.persistent_emmc_writes_authorized or rep.persistent_write_release:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("G17 redline violation: persistent_emmc_writes_authorized must be False.")

    passed = rep.all_passed and rep.h0_h1_trial_entry_allowed and (not errors)
    status = STATUS_VERIFIED_G17 if passed else (codes[0] if codes else STATUS_BLOCKED_G17_EXFAT_INTEGRITY)
    p1_fs = rep.filesystem_separation.get("p1_filesystem", "UNKNOWN")
    slots = rep.dual_slot_firewall.get("inserted_lab_slots", ())

    verdict = GateVerdict(
        gate_id=G17_GATE_ID,
        gate_code=G17_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Phase 57 exFAT BootChecksum & Sony media isolation ({rep.verification_mode}): "
            f"p1_fs={p1_fs}, lab_slots={list(slots)}, "
            f"h0_h1_trial_entry_allowed={rep.h0_h1_trial_entry_allowed}, "
            f"persistent_emmc_writes_authorized={rep.persistent_emmc_writes_authorized}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=rep.warnings,
        details={
            "verification_mode": rep.verification_mode,
            "h0_h1_trial_entry_allowed": rep.h0_h1_trial_entry_allowed,
            "p1_filesystem": p1_fs,
            "inserted_lab_slots": list(slots),
            "phase57_status": rep.status,
        },
    )
    return verdict, rep


def evaluate_g18_usblan_ptpip_and_airplane_coexistence(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    usblan_kwargs: Optional[Mapping[str, Any]] = None,
    ptpip_or_mc_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    authenticated: bool = True,
    allow_protocol_3_00: bool = False,
    p12_vma: int = P12_WLAN_FATAL_GUARD_VMA,
    p12_patched_rc: int = 0,
    p12_guard_enabled: bool = True,
    bk4_airplane_shadow: Optional[Mapping[int, int]] = None,
    wf12_bootloop_immune: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> Tuple[GateVerdict, G18UsbLanPtpIpResult]:
    """Evaluate Gate G18 (`USBLAN_PTPIP_FIREWALL_AND_AIRPLANE_COEXISTENCE`)."""
    donor_audit = audit_usblan_ptpip_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_usblan = dict(usblan_kwargs or {})
    eff_usblan.setdefault("p12_vma", p12_vma)
    eff_usblan.setdefault("p12_patched_rc", p12_patched_rc)
    eff_usblan.setdefault("p12_guard_enabled", p12_guard_enabled)
    eff_usblan.setdefault("bk4_airplane_shadow", bk4_airplane_shadow)
    eff_usblan.setdefault("wf12_bootloop_immune", wf12_bootloop_immune)
    eff_usblan["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_usblan.get("request_persistent_emmc_writes", False)
    )
    eff_usblan["verification_mode"] = donor_audit.verification_mode

    coexistence = verify_usblan_wired_control_and_airplane_coexistence(**eff_usblan)
    firewall = audit_usblan_ptpip_and_mc_firewall(
        ptpip_or_mc_requests,
        authenticated=authenticated,
        allow_protocol_3_00=allow_protocol_3_00,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not donor_audit.valid:
        _add_code(codes, donor_audit.status)
        errors.extend(donor_audit.errors)
    for c in coexistence.violation_codes + firewall.violation_codes:
        _add_code(codes, c)
    errors.extend(coexistence.errors)
    errors.extend(firewall.errors)
    warnings.extend(donor_audit.warnings)
    warnings.extend(coexistence.warnings)
    warnings.extend(firewall.warnings)

    passed = (
        donor_audit.valid
        and coexistence.valid
        and firewall.valid
        and (not coexistence.wifi_radio_enabled)
        and (not coexistence.bluetooth_uart_enabled)
        and coexistence.wf12_00342260_immune
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = STATUS_VERIFIED_G18 if passed else (codes[0] if codes else STATUS_BLOCKED_G18_USBLAN_AIRPLANE)

    res = G18UsbLanPtpIpResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=donor_audit.verification_mode,
        donor_audit=donor_audit.to_dict(),
        usblan_coexistence=coexistence.to_dict(),
        ptpip_mc_firewall=firewall.to_dict(),
        wifi_radio_enabled=coexistence.wifi_radio_enabled,
        bluetooth_uart_enabled=coexistence.bluetooth_uart_enabled,
        wf12_00342260_immune=coexistence.wf12_00342260_immune,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G18_GATE_ID,
        gate_code=G18_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Wired USB-LAN ({coexistence.usb_class}/{coexistence.chipset} {coexistence.link_speed_mbps}Mbps "
            f"on {coexistence.interface_name}, {donor_audit.verification_mode}): "
            f"wifi_radio_enabled={coexistence.wifi_radio_enabled}, "
            f"bt_uart_enabled={coexistence.bluetooth_uart_enabled}, "
            f"wf12_00342260_immune={coexistence.wf12_00342260_immune}, "
            f"ptpip_mc_allowed={firewall.allowed_count}/{firewall.total_operations}, "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": donor_audit.verification_mode,
            "wifi_radio_enabled": coexistence.wifi_radio_enabled,
            "bluetooth_uart_enabled": coexistence.bluetooth_uart_enabled,
            "wf12_00342260_immune": coexistence.wf12_00342260_immune,
            "usb_class": coexistence.usb_class,
            "chipset": coexistence.chipset,
            "ptpip_allowed_count": firewall.allowed_count,
            "ptpip_blocked_count": firewall.blocked_count,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Master 18-Gate Evaluator (`G01..G18`) & CLI
# ---------------------------------------------------------------------------


def evaluate_18_master_safety_gates(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G12 pass-throughs
    tier0_manifest: Optional[Dict[str, object]] = None,
    worker_syscall_trace: Optional[List[Dict[str, object]]] = None,
    init2_failsafe_hook: Optional[str] = None,
    candidate_bundle_verified: Optional[bool] = None,
    allow_dry_run_gate12: bool = False,
    use_synthetic_dry_run_tier0: bool = False,
    gate12_kwargs: Optional[Mapping[str, Any]] = None,
    # G13..G16 pass-throughs
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
    # G17 inputs (Phase 57 exFAT & client media isolation)
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    p1_vbr_bytes: Optional[bytes] = None,
    p1_image_path: Optional[Path] = None,
    p1_device_node: str = "/dev/nflasha1",
    require_at_least_one_lab_card: bool = True,
    # G18 inputs (Phase 58/61 USB-LAN PTP-IP firewall & Airplane-Mode)
    usblan_kwargs: Optional[Mapping[str, Any]] = None,
    ptpip_or_mc_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    ptpip_authenticated: bool = True,
    allow_protocol_3_00: bool = False,
) -> Master18GateReport:
    """Evaluate all 18 Master Safety Gates (`G01..G18`) deterministically."""
    resolved_root = (DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m16_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "include_large_binaries": include_large_binaries,
        "work_root": work_root,
        "tier0_manifest": tier0_manifest,
        "worker_syscall_trace": worker_syscall_trace,
        "init2_failsafe_hook": init2_failsafe_hook,
        "candidate_bundle_verified": candidate_bundle_verified,
        "allow_dry_run_gate12": allow_dry_run_gate12,
        "use_synthetic_dry_run_tier0": use_synthetic_dry_run_tier0,
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
    }
    if soc_start_ceiling_c is not None:
        m16_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m16_report: Master16GateReport = evaluate_16_master_safety_gates(resolved_root, **m16_kwargs)

    g17_verdict, g17_res = evaluate_g17_exfat_and_client_media_isolation(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        slot_a=slot_a,
        slot_b=slot_b,
        p1_vbr_bytes=p1_vbr_bytes,
        p1_image_path=p1_image_path,
        p1_device_node=p1_device_node,
        planned_mounts=planned_mounts,
        planned_writes=planned_writes,
        require_at_least_one_lab_card=require_at_least_one_lab_card,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    g18_verdict, g18_res = evaluate_g18_usblan_ptpip_and_airplane_coexistence(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        usblan_kwargs=usblan_kwargs,
        ptpip_or_mc_requests=ptpip_or_mc_requests,
        authenticated=ptpip_authenticated,
        allow_protocol_3_00=allow_protocol_3_00,
        p12_vma=p12_vma,
        p12_patched_rc=p12_patched_rc,
        p12_guard_enabled=p12_guard_enabled,
        bk4_airplane_shadow=bk4_airplane_shadow,
        wf12_bootloop_immune=wf12_bootloop_immune,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    gates_17_to_18 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g17_verdict, g18_verdict)
    ]
    all_gates = tuple(list(m16_report.gates) + gates_17_to_18)

    g01_to_g12_verified = int(m16_report.summary["g01_to_g12_verified"])
    g13_to_g16_verified = int(m16_report.summary["g13_to_g16_verified"])
    g17_to_g18_verified = sum(1 for v in (g17_verdict, g18_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g16_verified + g17_to_g18_verified

    g17_to_g18_all_passed = g17_to_g18_verified == 2
    g13_to_g18_all_passed = m16_report.g13_to_g16_all_passed and g17_to_g18_all_passed
    g01_to_g09_ok = all(str(g["status"]).startswith("VERIFIED") for g in m16_report.gates[:9])

    offline_15_verified = g01_to_g09_ok and g13_to_g18_all_passed
    all_18_verified = (g01_to_g12_verified == 12) and g13_to_g18_all_passed
    h0_h1_allowed = (
        offline_15_verified
        and g17_res.h0_h1_trial_entry_allowed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = list(m16_report.errors) + list(g17_verdict.errors) + list(g18_verdict.errors)
    warnings: List[str] = list(m16_report.warnings) + list(g17_verdict.warnings) + list(g18_verdict.warnings)

    if not m16_report.g13_to_g16_all_passed:
        overall_status = m16_report.status
    elif not g17_verdict.passed:
        overall_status = g17_verdict.status
    elif not g18_verdict.passed:
        overall_status = g18_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_18_verified:
        overall_status = "VERIFIED_ALL_18_GATES_OFFLINE_DRY_RUN"
    else:
        overall_status = "VERIFIED_G01_G09_AND_G13_G18_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m16_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g17_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g18_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 18,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 18 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g16_verified": g13_to_g16_verified,
        "g17_to_g18_verified": g17_to_g18_verified,
        "g13_to_g18_all_passed": g13_to_g18_all_passed,
        "g17_to_g18_all_passed": g17_to_g18_all_passed,
        "offline_15_gates_verified": offline_15_verified,
        "all_18_gates_verified": all_18_verified,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master18GateReport(
        schema=USBLAN_PTPIP_18GATE_SCHEMA,
        version=USBLAN_PTPIP_18GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        all_18_gates_verified=all_18_verified,
        offline_15_gates_verified=offline_15_verified,
        g13_to_g18_all_passed=g13_to_g18_all_passed,
        g17_to_g18_all_passed=g17_to_g18_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_16_report=m16_report.to_dict(),
        g17_result=g17_res.to_dict(),
        g18_result=g18_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="usblan_ptpip_and_18gate_preflight",
        description="Phase 61 — Wired USB-LAN / PTP-IP Firewall & 18-Gate Master Safety Preflight (G01..G18)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    parser.add_argument(
        "--dry-run-tier0",
        action="store_true",
        help="Supply synthetic dry-run Tier-0 inputs so G01..G18 can be exercised offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_18_master_safety_gates(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        use_synthetic_dry_run_tier0=bool(args.dry_run_tier0),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/18 "
            f"g17_to_g18_all_passed={report.g17_to_g18_all_passed} "
            f"all_18_gates_verified={report.all_18_gates_verified} "
            f"h0_h1_trial_entry_allowed={report.h0_h1_trial_entry_allowed} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = report.all_18_gates_verified if args.dry_run_tier0 else report.offline_15_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
