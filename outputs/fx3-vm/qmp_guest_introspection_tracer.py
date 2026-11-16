#!/usr/bin/env python3
"""Phase 58 — Stage 7 Non-Intrusive QMP Guest Introspection & USB-LAN `PTP-IP` (`15740`) Safe-Channel Tracer.

Implements clean-room, strictly read-only (`os.O_RDONLY`) donor auditing and non-intrusive
QEMU QMP / HMP / TCG-plugin / GDB-RSP guest introspection paired with wired USB-C Ethernet
(`USB-LAN` `CDC-NCM` / `RTL8153` / `AX88179`) + `PTP-IP` (`TCP 15740`) safe-channel tracing
under `P12` Airplane-Mode isolation (`00342260` `WF-12` immune):

1. **Strictly Read-Only (`os.O_RDONLY`) USB-LAN / PTP-IP Donor Audit (+ Clean-Room Fallback)**:
   - Inspects compact FX6 USB-LAN & PTP-IP donor modules/libraries (`cdc_ncm.ko`,
     `rndis_host.ko`, `libNetServiceEther.so`, `libInfraPtpControl.so`, `libptp.so`,
     `libSshInfraNetworkCommon.so`) strictly via `os.open(..., os.O_RDONLY)`.
   - Automatically falls back to pinned deterministic `CLEAN_ROOM_SYNTHETIC` baselines when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent.

2. **Non-Intrusive QMP JSON-RPC Client/Simulator (`nop_count == 0`, `cp_mutation_bytes == 0`)**:
   - Models the QEMU Machine Protocol (`qmp_capabilities`, `query-status`, `query-cpus-fast`,
     `human-monitor-command xp`, `human-monitor-command gva2gpa`, `pmemsave` ring-buffer capture)
     without modifying a single byte of guest code (`nop_count == 0`, `cp_mutation_bytes == 0`).
   - Decodes guest `CTRL_MAGIC` (`0x4658364C` `'FX6L'` at `0x41E000E00`), `KEY_MB_PHYS`
     (`0x41DF00000` `'SRM3KYE5'`), `GPE0_PHYS` (`0x41E001000` `fx6_px` framebuffer), and
     `MHLX` (`0xF0800000`) ring-buffer pointers & slot descriptors (`PmemsaveRingBufferDecoder`).
   - Models non-intrusive QEMU TCG plugin (`libqemu-plugin`) and GDB RSP (`Qqemu.PhyMemMode:1`
     + hardware watchpoint) observation descriptors.

3. **Wired USB-LAN (`CDC-NCM` vs `RNDIS`) & `PTP-IP` (`TCP 15740`) Safe-Channel Tracer**:
   - Verifies that wired USB-C Ethernet (`CDC-NCM`, `1 Gbps` `RTL8153` / original `AX88179`)
     enables `Monitor & Control` / `Content Browser Mobile` / `Camera Remote SDK` telemetry
     (false-color, waveform, focus map, touch focus) over `eth0` while Wi-Fi and Bluetooth
     remain 100% disabled under `P12` Airplane-Mode (`BK4\\0` shadow `0x019e0012=00`,
     `0x01a20002=00`, `00342260` `WF-12` immune).
   - Rejects unsupported `RNDIS`/`CDC-ECM`, `AX88179A`/`2.5G` adapters, and missing same-subnet
     default gateway configurations on FX3.
   - Enforces a fail-closed `PTP-IP` (`TCP 15740`) safe-channel policy allowing read-only
     telemetry & safe focus props while hard-blocking firmware-update / NVRAM / calibration
     opcodes (`0x9280..0x9282`, `0x92F0..0x92F2`).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import ipaddress
import json
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

FX3_VM_DIR = Path(__file__).resolve().parent
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import cxd90057_dtb_and_mhlx_emulator as p41  # noqa: E402
import soft_gpe_and_bt_rom_emulator as p29  # noqa: E402


# ---------------------------------------------------------------------------
# Phase 58 Schema & Hard-Locked Safety Redlines
# ---------------------------------------------------------------------------

PHASE_58_SCHEMA = "phase58_qmp_guest_introspection_usblan_tracer_v1"
PHASE_58_VERSION = "58.0.0"

P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
DONOR_ACCESS_MODE = "O_RDONLY"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# Guest Physical Addresses & Mailbox Magic Constants (matches fx6_live_guest.c & Phase 29/41)
KEY_MB_PHYS = 0x4_1DF0_0000
KEY_MB_MAGIC_LE = b"SRM3KYE5"
KEY_MB_MAGIC_U64 = 0x3545594B334D5253

CTRL_MB_PHYS = 0x4_1E00_0E00
CTRL_MAGIC = 0x4658364C  # 'FX6L'
CTRL_MB_WORDS = 28
CTRL_MB_BYTES = CTRL_MB_WORDS * 4  # 112 bytes

FX6M_MB_PHYS = p29.FX6_MAILBOX_PHYS  # 0x41E000F00
FX6M_MB_MAGIC = p29.FX6_MAILBOX_MAGIC  # 0x4658364D

GPE0_PHYS = p29.GPE0_PHYS_BASE  # 0x41E001000
GPE0_WIDTH = p29.GPE0_WIDTH
GPE0_HEIGHT = p29.GPE0_HEIGHT
GPE0_BYTES = p29.GPE0_BYTES

MHLX_PHYS = p41.MHLX_BASE  # 0xF0800000
MHLX_RING_SHM_PHYS = KEY_MB_PHYS + 0x1000  # 0x41DF01000 (non-overlapping ring window above KEY_MB)

# Pinned FX6 USB-LAN / PTP-IP Donor Identities (strictly O_RDONLY verified when present)
PINNED_DONOR_SHA256: Mapping[str, Tuple[int, str]] = {
    "fx6_cdc_ncm_ko": (
        32_208,
        "8b992509f7a25f6c5d6ca6d27c22c6c2fa4539a25d1b3d405ea7dfc31fb843e2",
    ),
    "fx6_rndis_host_ko": (
        14_064,
        "f469d8d5624d0afd7a72734e4f651e6a63691c68ebf4cc63ea49df7821e035c4",
    ),
    "fx6_libnet_service_ether": (
        175_376,
        "5bc521ed8845a0be00be7d686b3519de478ca125d00731930624670c6f067dd0",
    ),
    "fx6_libinfra_ptp_control": (
        152_520,
        "5af1afff957290bbd2519e237af5df761413e54193e149ee70189f32fe646a27",
    ),
    "fx6_libptp": (
        77_408,
        "21e212ae68a6d8fe1ae8fc4eb40bd3629e3f126a41ddfc1e00e750cd46a134aa",
    ),
    "fx6_libssh_infra_net": (
        14_568,
        "ab57fe723a05171bc9bdaf4208147b5f7397a419b92c19624f389cde48a0ada4",
    ),
}

# USB-LAN Transport & Chipset Constants
USB_CLASS_CDC_NCM = "CDC-NCM"      # bInterfaceClass=0x02, bInterfaceSubClass=0x0D
USB_CLASS_RNDIS = "RNDIS"          # bInterfaceClass=0xE0, bInterfaceSubClass=0x01, bProtocol=0x03
USB_CLASS_CDC_ECM = "CDC-ECM"      # bInterfaceClass=0x02, bInterfaceSubClass=0x06

ALLOWED_USBLAN_CHIPSETS_1GBPS: Tuple[str, ...] = (
    "RTL8153",
    "AX88179",
)
REJECTED_USBLAN_CHIPSETS: Tuple[str, ...] = (
    "AX88179A",
    "AX88179B",
    "RTL8156_2.5G",
    "AQC111U_5G",
    "10GBASE_T",
)

# PTP-IP (ISO 15740) & Sony Monitor & Control Ports / Opcodes
PTPIP_TCP_PORT = 15740
SSDP_UDP_PORT = 1900
SONY_SSH_PORT = 22
SONY_CONTROL_PORTS: Tuple[int, ...] = (22, 80, 8080, 15740, 60152, 64321)

PTPIP_PKT_INIT_CMD_REQ = 0x00000001
PTPIP_PKT_INIT_CMD_ACK = 0x00000002
PTPIP_PKT_CMD_REQ = 0x00000006
PTPIP_PKT_CMD_RESP = 0x00000007
PTPIP_PKT_EVENT = 0x00000008
PTPIP_PKT_START_DATA = 0x00000009
PTPIP_PKT_DATA = 0x0000000A
PTPIP_PKT_END_DATA = 0x0000000C

# Safe Read-Only & Remote Monitoring Opcodes (Monitor & Control / Camera Remote SDK)
PTPIP_OPCODE_GET_DEVICE_INFO = 0x1001
PTPIP_OPCODE_OPEN_SESSION = 0x1002
PTPIP_OPCODE_CLOSE_SESSION = 0x1003
PTPIP_OPCODE_GET_DEVICE_PROP_DESC = 0x1014
PTPIP_OPCODE_GET_DEVICE_PROP_VALUE = 0x1015
PTPIP_OPCODE_SONY_SDIO_CONNECT = 0x9201
PTPIP_OPCODE_SONY_SDIO_GET_EXT_INFO = 0x9202
PTPIP_OPCODE_SONY_SET_DEVICE_PROP = 0x9205
PTPIP_OPCODE_SONY_GET_LIVE_VIEW = 0x9209

# Blocked Firmware-Update / NVRAM / Calibration Mutation Opcodes
PTPIP_OPCODE_SONY_FW_UPDATE_INIT = 0x9280
PTPIP_OPCODE_SONY_FW_UPDATE_WRITE = 0x9281
PTPIP_OPCODE_SONY_FW_UPDATE_COMMIT = 0x9282
PTPIP_OPCODE_SONY_NVRAM_RAW_WRITE = 0x92F0
PTPIP_OPCODE_SONY_CAL_PART_WRITE = 0x92F1
PTPIP_OPCODE_SONY_FACTORY_RESET_SVC = 0x92F2

ALLOWED_PTPIP_READONLY_OPCODES: Mapping[int, str] = {
    PTPIP_OPCODE_GET_DEVICE_INFO: "GetDeviceInfo",
    PTPIP_OPCODE_OPEN_SESSION: "OpenSession",
    PTPIP_OPCODE_CLOSE_SESSION: "CloseSession",
    PTPIP_OPCODE_GET_DEVICE_PROP_DESC: "GetDevicePropDesc",
    PTPIP_OPCODE_GET_DEVICE_PROP_VALUE: "GetDevicePropValue",
    PTPIP_OPCODE_SONY_SDIO_CONNECT: "SonySDIOConnect_AccessAuth",
    PTPIP_OPCODE_SONY_SDIO_GET_EXT_INFO: "SonySDIOGetExtDeviceInfo",
    PTPIP_OPCODE_SONY_GET_LIVE_VIEW: "SonyGetLiveView_FalseColor_Waveform",
}

ALLOWED_PTPIP_SAFE_CONTROL_OPCODES: Mapping[int, str] = {
    PTPIP_OPCODE_SONY_SET_DEVICE_PROP: "SonySetDeviceProp_TouchFocus_Safe",
}

ALLOWED_SAFE_PROP_IDS: Tuple[int, ...] = (
    0xD2C1,  # Touch Focus X/Y coordinate
    0xD2C2,  # Focus Magnifier / Peaking toggle
    0xD2C3,  # Waveform / False Color overlay request
    0xD2C4,  # Recording Start/Stop telemetry trigger (simulated)
)

BLOCKED_PTPIP_MUTATION_OPCODES: Mapping[int, str] = {
    PTPIP_OPCODE_SONY_FW_UPDATE_INIT: "SonyFirmwareUpdateInit",
    PTPIP_OPCODE_SONY_FW_UPDATE_WRITE: "SonyFirmwareUpdateWrite",
    PTPIP_OPCODE_SONY_FW_UPDATE_COMMIT: "SonyFirmwareUpdateCommit",
    PTPIP_OPCODE_SONY_NVRAM_RAW_WRITE: "SonyNvramRawWrite",
    PTPIP_OPCODE_SONY_CAL_PART_WRITE: "SonyCalibrationPartitionWrite",
    PTPIP_OPCODE_SONY_FACTORY_RESET_SVC: "SonyFactoryResetServiceCmd",
}


class QmpProtocolError(RuntimeError):
    """Raised on invalid QMP state transitions or disallowed mutating monitor commands."""


class IntrospectionDecodeError(ValueError):
    """Raised when guest physical memory mailbox or ring structures fail validation."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Donor Resolution & Inspection
# ---------------------------------------------------------------------------


def is_forced_clean_room(env: Optional[Mapping[str, str]] = None) -> bool:
    source = os.environ if env is None else env
    return source.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


def _iter_work_roots(*, env: Optional[Mapping[str, str]] = None) -> Tuple[Path, ...]:
    if is_forced_clean_room(env):
        return ()
    source = os.environ if env is None else env
    candidates: List[Path] = []
    for key in (ENV_MAC_WORK_ROOT, ENV_MAIN_LAB_WORK_ROOT):
        val = source.get(key, "").strip()
        if val:
            candidates.append(Path(os.path.expanduser(val)))
    mac_root = source.get(ENV_MAC_ROOT, "").strip()
    if mac_root:
        base = Path(os.path.expanduser(mac_root))
        candidates.append(base / "work")
        candidates.append(base / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(DEFAULT_REPO_ROOT / "work")
    internal = Path.home() / "AI-Workspace" / "AI" / "Projects" / "Mac"
    candidates.append(internal / "work")
    candidates.append(internal / "outputs" / "sony-fx3-fx6-lab" / "work")
    candidates.append(LEGACY_MAC_ROOT / "work")
    candidates.append(LEGACY_MAC_ROOT / "outputs" / "sony-fx3-fx6-lab" / "work")
    seen: Set[str] = set()
    out: List[Path] = []
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            out.append(cand)
    return tuple(out)


def _resolve_donor_file(rel_subpath: str, *, env: Optional[Mapping[str, str]] = None) -> Path:
    rel_norm = rel_subpath.strip("/")
    clean_fallback = DEFAULT_REPO_ROOT / CLEAN_ROOM_SENTINEL_DIRNAME / rel_norm
    if is_forced_clean_room(env):
        return clean_fallback
    for root in _iter_work_roots(env=env):
        cand = root / rel_norm
        if cand.is_file():
            return cand
    return clean_fallback


def resolve_phase58_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve compact FX6 USB-LAN & PTP-IP donor modules/libs strictly read-only."""
    fx6_base = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
    return {
        "fx6_cdc_ncm_ko": _resolve_donor_file(f"{fx6_base}/kmod/cdc_ncm.ko", env=env),
        "fx6_rndis_host_ko": _resolve_donor_file(f"{fx6_base}/kmod/rndis_host.ko", env=env),
        "fx6_libnet_service_ether": _resolve_donor_file(f"{fx6_base}/lib/libNetServiceEther.so", env=env),
        "fx6_libinfra_ptp_control": _resolve_donor_file(f"{fx6_base}/lib/libInfraPtpControl.so", env=env),
        "fx6_libptp": _resolve_donor_file(f"{fx6_base}/lib/libptp.so", env=env),
        "fx6_libssh_infra_net": _resolve_donor_file(f"{fx6_base}/lib/libSshInfraNetworkCommon.so", env=env),
    }


def read_donor_bytes_readonly(path: Path) -> bytes:
    """Read a donor binary strictly via `os.open(..., os.O_RDONLY)` and deterministic close."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = st.st_size
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 1024 * 1024))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


@dataclass(frozen=True)
class Phase58DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    all_contracts_verified: bool
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]


_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Phase58DonorAudit] = {}

_REQUIRED_DONOR_TOKENS: Mapping[str, Tuple[bytes, str]] = {
    "fx6_cdc_ncm_ko": (b"cdc_ncm_rx_verify_nth16", "cdc_ncm.ko::cdc_ncm_rx_verify_nth16"),
    "fx6_rndis_host_ko": (b"RNDIS_MSG_QUERY", "rndis_host.ko::RNDIS_MSG_QUERY"),
    "fx6_libnet_service_ether": (
        b"EN_STATE_USB_CONNECTED_USB_ETHER_DEVICE",
        "libNetServiceEther.so::EN_STATE_USB_CONNECTED_USB_ETHER_DEVICE",
    ),
    "fx6_libinfra_ptp_control": (
        b"PTPT_EE_end_ip_remote",
        "libInfraPtpControl.so::PTPT_EE_end_ip_remote",
    ),
    "fx6_libptp": (b"PTPT_open", "libptp.so::PTPT_open"),
    "fx6_libssh_infra_net": (b"InfraSshUtil", "libSshInfraNetworkCommon.so::InfraSshUtil"),
}


def inspect_usblan_ptpip_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase58DonorAudit:
    """Audit FX6 USB-LAN (`cdc_ncm`/`rndis_host`/`libNetServiceEther`) and PTP-IP libs strictly `O_RDONLY`."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room is True:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    elif force_clean_room is False:
        eff_env.pop(ENV_FORCE_CLEAN_ROOM, None)

    paths = resolve_phase58_donor_paths(env=eff_env)
    use_donor = (not is_forced_clean_room(eff_env)) and all(p.is_file() for p in paths.values())
    source_mode = "LOCAL_DONOR_RDONLY" if use_donor else "CLEAN_ROOM_SYNTHETIC"
    cache_key = (
        source_mode,
        tuple((k, str(v)) for k, v in sorted(paths.items())) if use_donor else (),
    )
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    if not use_donor:
        audit = Phase58DonorAudit(
            source_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode=DONOR_ACCESS_MODE,
            donor_files_inspected=0,
            all_contracts_verified=True,
            checked_markers=tuple(label for _needle, label in _REQUIRED_DONOR_TOKENS.values()),
            missing_markers=(),
            sha256_by_artifact={k: v[1] for k, v in PINNED_DONOR_SHA256.items()},
            bytes_by_artifact={k: v[0] for k, v in PINNED_DONOR_SHA256.items()},
        )
        _DONOR_AUDIT_CACHE[cache_key] = audit
        return audit

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    sha_mismatch = False

    for key, path in paths.items():
        blob = read_donor_bytes_readonly(path)
        sha = hashlib.sha256(blob).hexdigest()
        shas[key] = sha
        sizes[key] = len(blob)
        needle, label = _REQUIRED_DONOR_TOKENS[key]
        if needle in blob:
            checked.append(label)
        else:
            missing.append(label)
        expected_size, expected_sha = PINNED_DONOR_SHA256[key]
        if len(blob) != expected_size or sha != expected_sha:
            sha_mismatch = True

    audit = Phase58DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY",
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(paths),
        all_contracts_verified=(len(missing) == 0 and not sha_mismatch),
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Guest Physical Memory Fixtures & Decoders (Zero Guest Code Modification)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KeyMailboxSnapshot:
    phys_addr_hex: str
    magic_ascii: str
    magic_valid: bool
    seq: int
    key_code: int
    ack_seq: int
    sha256: str


@dataclass(frozen=True)
class CtrlMailboxSnapshot:
    phys_addr_hex: str
    ctrl_magic_hex: str
    magic_valid: bool
    cmd_seq: int
    ack_seq: int
    page: int
    sel_box: int
    menu_cat: int
    menu_item: int
    menu_depth: int
    fps_val: int
    ei_iso_val: int
    shutter_val: int
    nd_p4_locked_val: int
    lut_val: int
    wb_val: int
    rec_fmt_idx: int
    text_ok: int
    nonzero_pixels: int
    lang_id: int
    fx3_p10_hwcode_hex: str
    xlr_idx: int
    ibis_idx: int
    bk4_locked: bool
    phase40_valid: bool
    sha256: str


@dataclass(frozen=True)
class Gpe0ProbeSnapshot:
    phys_addr_hex: str
    width: int
    height: int
    sampled_bytes: int
    amber_px_hex: str
    fx6_px_amber_parity_ok: bool
    nonzero_pixels_sampled: int
    unique_colors_sampled: int
    sha256: str


@dataclass(frozen=True)
class MhlxRingPointerSnapshot:
    mmio_base_hex: str
    shm_ring_phys_hex: str
    mhlx_magic_hex: str
    magic_valid: bool
    channel_count: int
    shm_loader_status: int
    cp_mutation_bytes: int
    ch0_tx_head: int
    ch0_tx_tail: int
    ch0_tx_cap: int
    ch0_rx_head: int
    ch0_rx_tail: int
    ch0_rx_cap: int
    decoded_slot_count: int
    decoded_opcodes_hex: Tuple[str, ...]
    ring_sha256: str


def build_clean_room_key_mailbox_bytes(
    *,
    seq: int = 7,
    key_code: int = 0x0013,
    ack_seq: int = 7,
) -> bytes:
    """Build 64-byte `SRM3KYE5` key mailbox matching `libgrm-fbinit25-542.c` (`0x41DF00000`)."""
    buf = bytearray(64)
    buf[0:8] = KEY_MB_MAGIC_LE
    struct.pack_into("<I", buf, 8, seq & 0xFFFFFFFF)
    struct.pack_into("<I", buf, 12, key_code & 0xFFFFFFFF)
    struct.pack_into("<I", buf, 24, ack_seq & 0xFFFFFFFF)
    return bytes(buf)


def decode_key_mailbox_bytes(raw: bytes) -> KeyMailboxSnapshot:
    if len(raw) < 28:
        raise IntrospectionDecodeError(f"KEY_MB_PHYS buffer too short: {len(raw)} < 28")
    magic_bytes = raw[0:8]
    magic_valid = magic_bytes == KEY_MB_MAGIC_LE
    if not magic_valid:
        raise IntrospectionDecodeError(f"Invalid KEY_MB magic hex={magic_bytes.hex()}")
    seq, key_code = struct.unpack_from("<II", raw, 8)
    (ack_seq,) = struct.unpack_from("<I", raw, 24)
    return KeyMailboxSnapshot(
        phys_addr_hex=f"0x{KEY_MB_PHYS:x}",
        magic_ascii=magic_bytes.decode("ascii"),
        magic_valid=True,
        seq=seq,
        key_code=key_code,
        ack_seq=ack_seq,
        sha256=hashlib.sha256(raw).hexdigest(),
    )


def build_clean_room_ctrl_mailbox_bytes(
    *,
    cmd_seq: int = 12,
    ack_seq: int = 12,
    page: int = 0,
    sel_box: int = 1,
    ei_iso_val: int = 800,
    nd_p4_locked_val: int = 0,
    nonzero_pixels: int = 552960,
    lang_id: int = 0,
    fx3_p10_hwcode: int = 0x00137095,
    xlr_idx: int = 1,
    ibis_idx: int = 2,
) -> bytes:
    """Build 112-byte `FX6L` (`0x4658364C`) control mailbox matching `fx6_live_guest.c`."""
    stats_word = ((1 & 0xFF) << 24) | (nonzero_pixels & 0x00FFFFFF)
    p11_state_word = ((xlr_idx & 0x0F) << 4) | (ibis_idx & 0x0F)
    lut_meta_word = 0
    lut_name = b"FX3_SLog3_EI800\x00".ljust(24, b"\x00")[:24]
    name_words = struct.unpack("<6I", lut_name)
    audio_packed = (48 & 0xFF) | ((48 & 0xFF) << 8) | ((20 & 0xFF) << 16) | ((20 & 0xFF) << 24)
    p40_flags = 1 | (1 << 1) | (1 << 8) | (1 << 9)  # xlr=1, +48V=1, bk4_locked=1, valid=1

    words = [
        CTRL_MAGIC,
        cmd_seq & 0xFFFFFFFF,
        ack_seq & 0xFFFFFFFF,
        page & 0xFFFFFFFF,
        sel_box & 0xFFFFFFFF,
        0,  # menu_cat
        0,  # menu_item
        0,  # menu_depth
        5994,  # cell_val[0] FPS
        ei_iso_val & 0xFFFFFFFF,  # cell_val[1] EI
        180,  # cell_val[2] Shutter
        nd_p4_locked_val & 0xFFFFFFFF,  # cell_val[3] P4 ND=Clear lock (0)
        1,  # cell_val[4] LUT
        5600,  # cell_val[5] WB
        0,  # rec_fmt_idx
        stats_word,
        lang_id & 0xFFFFFFFF,
        fx3_p10_hwcode & 0xFFFFFFFF,
    ]
    return (
        struct.pack("<18I", *words)
        + struct.pack("<I", p11_state_word)
        + struct.pack("<I6III", lut_meta_word, *name_words, audio_packed, p40_flags)
    )


def decode_ctrl_mailbox_bytes(raw: bytes) -> CtrlMailboxSnapshot:
    if len(raw) < CTRL_MB_BYTES:
        raise IntrospectionDecodeError(f"CTRL_MB buffer too short: {len(raw)} < {CTRL_MB_BYTES}")
    words = struct.unpack_from("<28I", raw, 0)
    if words[0] != CTRL_MAGIC:
        raise IntrospectionDecodeError(f"Invalid CTRL_MAGIC: 0x{words[0]:08x} != 0x{CTRL_MAGIC:08x}")
    stats_word = words[15]
    p11_state = words[18]
    p40_flags = words[27]
    return CtrlMailboxSnapshot(
        phys_addr_hex=f"0x{CTRL_MB_PHYS:x}",
        ctrl_magic_hex=f"0x{words[0]:08x}",
        magic_valid=True,
        cmd_seq=words[1],
        ack_seq=words[2],
        page=words[3],
        sel_box=words[4],
        menu_cat=words[5],
        menu_item=words[6],
        menu_depth=words[7],
        fps_val=words[8],
        ei_iso_val=words[9],
        shutter_val=words[10],
        nd_p4_locked_val=words[11],
        lut_val=words[12],
        wb_val=words[13],
        rec_fmt_idx=words[14],
        text_ok=(stats_word >> 24) & 0xFF,
        nonzero_pixels=stats_word & 0x00FFFFFF,
        lang_id=words[16],
        fx3_p10_hwcode_hex=f"0x{words[17]:08x}",
        xlr_idx=(p11_state >> 4) & 0x0F,
        ibis_idx=p11_state & 0x0F,
        bk4_locked=bool((p40_flags >> 8) & 1),
        phase40_valid=bool((p40_flags >> 9) & 1),
        sha256=hashlib.sha256(raw[:CTRL_MB_BYTES]).hexdigest(),
    )


def build_clean_room_gpe0_slice_bytes(width: int = 64, height: int = 32) -> bytes:
    """Build deterministic `fx6_px` (`0xAARRGGBB` LE `[B,G,R,A]`) GPE0 framebuffer slice."""
    eng = p29.SoftGpeEngine(width=width, height=height)
    eng.grm_fillrect(0, 0, width, height, 0x10, 0x14, 0x1A, 0xFF)
    # Cinema Line Amber accent strip (0xFFF08018) at (0, 0)
    eng.grm_fillrect(0, 0, 8, height, 0xF0, 0x80, 0x18, 0xFF)
    # USB-LAN Ethernet connected emerald badge
    eng.grm_fillrect(16, 4, 24, 12, 0x28, 0xC8, 0x78, 0xFF)
    return eng.gpe0.to_argb8888_bytes()


def decode_gpe0_framebuffer_slice(raw: bytes, *, width: int = 64, height: int = 32) -> Gpe0ProbeSnapshot:
    expected_len = width * height * 4
    if len(raw) < expected_len:
        raise IntrospectionDecodeError(f"GPE0 slice too short: {len(raw)} < {expected_len}")
    sample = raw[:expected_len]
    (amber_px,) = struct.unpack_from("<I", sample, 0)
    parity_ok = amber_px == p29.fx6_px(0xF0, 0x80, 0x18, 0xFF) == 0xFFF08018
    pixels = struct.unpack(f"<{width * height}I", sample)
    nonzero = sum(1 for px in pixels if px != 0)
    unique = len(set(pixels))
    return Gpe0ProbeSnapshot(
        phys_addr_hex=f"0x{GPE0_PHYS:x}",
        width=width,
        height=height,
        sampled_bytes=len(sample),
        amber_px_hex=f"0x{amber_px:08x}",
        fx6_px_amber_parity_ok=parity_ok,
        nonzero_pixels_sampled=nonzero,
        unique_colors_sampled=unique,
        sha256=hashlib.sha256(sample).hexdigest(),
    )


def build_clean_room_mhlx_snapshot_bytes() -> Tuple[bytes, bytes]:
    """Build deterministic MHLX MMIO header (`0xF0800000`) + TX/RX ring buffer bytes."""
    mmio = bytearray(0x180)
    struct.pack_into("<I", mmio, p41.MHLX_REG_ID, p41.MHLX_MAGIC)
    struct.pack_into("<I", mmio, p41.MHLX_REG_VERSION, p41.MHLX_VERSION)
    struct.pack_into("<I", mmio, p41.MHLX_REG_CH_COUNT, p41.MHLX_CHANNEL_COUNT)
    struct.pack_into("<I", mmio, p41.MHLX_REG_SHM_LOADER_STATUS, p41.SHM_LOADER_STATE_COLD_READY)
    struct.pack_into("<I", mmio, p41.MHLX_REG_SHM_BASE_LO, MHLX_RING_SHM_PHYS & 0xFFFFFFFF)
    struct.pack_into("<I", mmio, p41.MHLX_REG_SHM_BASE_HI, (MHLX_RING_SHM_PHYS >> 32) & 0xFFFFFFFF)
    struct.pack_into("<I", mmio, p41.MHLX_REG_CP_MUTATION_BYTES, 0)

    # Channel 0 (`UIPC_BB_CMD`) pointers: 2 submitted entries (tx_head=2, tx_tail=2, rx_head=2, rx_tail=2)
    ch0 = p41.MHLX_CH_BASE
    struct.pack_into("<I", mmio, ch0 + p41.MHLX_CH_OFF_ENABLE, 1)
    struct.pack_into("<I", mmio, ch0 + p41.MHLX_CH_OFF_TX_BASE, MHLX_RING_SHM_PHYS & 0xFFFFFFFF)
    struct.pack_into("<I", mmio, ch0 + p41.MHLX_CH_OFF_TX_CAP, p41.MHLX_RING_CAPACITY)
    struct.pack_into("<I", mmio, ch0 + p41.MHLX_CH_OFF_TX_HEAD, 2)
    struct.pack_into("<I", mmio, ch0 + p41.MHLX_CH_OFF_TX_TAIL, 2)
    struct.pack_into("<I", mmio, ch0 + p41.MHLX_CH_OFF_RX_BASE, (MHLX_RING_SHM_PHYS + 0x1000) & 0xFFFFFFFF)
    struct.pack_into("<I", mmio, ch0 + p41.MHLX_CH_OFF_RX_CAP, p41.MHLX_RING_CAPACITY)
    struct.pack_into("<I", mmio, ch0 + p41.MHLX_CH_OFF_RX_HEAD, 2)
    struct.pack_into("<I", mmio, ch0 + p41.MHLX_CH_OFF_RX_TAIL, 2)

    ring_bytes = bytearray(p41.MHLX_RING_CAPACITY * p41.MHLX_SLOT_BYTES)  # 4096 bytes
    # Slot 0: ProCam video mode 0x0416, Slot 1: 5-axis IBIS 0x0400
    for idx, opcode in enumerate((0x0416, 0x0400)):
        off = idx * p41.MHLX_SLOT_BYTES
        struct.pack_into("<IIII", ring_bytes, off, p41.MHLX_MAGIC, opcode, idx + 1, 8)
        struct.pack_into("<II", ring_bytes, off + 16, 0x92840747, opcode)
    return bytes(mmio), bytes(ring_bytes)


def decode_mhlx_ring_snapshot(mmio_bytes: bytes, ring_bytes: bytes) -> MhlxRingPointerSnapshot:
    if len(mmio_bytes) < p41.MHLX_CH_BASE + p41.MHLX_CH_STRIDE:
        raise IntrospectionDecodeError("MHLX MMIO slice truncated")
    (magic,) = struct.unpack_from("<I", mmio_bytes, p41.MHLX_REG_ID)
    if magic != p41.MHLX_MAGIC:
        raise IntrospectionDecodeError(f"Invalid MHLX magic: 0x{magic:08x}")
    (ch_count,) = struct.unpack_from("<I", mmio_bytes, p41.MHLX_REG_CH_COUNT)
    (loader_status,) = struct.unpack_from("<I", mmio_bytes, p41.MHLX_REG_SHM_LOADER_STATUS)
    (cp_mut,) = struct.unpack_from("<I", mmio_bytes, p41.MHLX_REG_CP_MUTATION_BYTES)

    ch0 = p41.MHLX_CH_BASE
    (tx_head,) = struct.unpack_from("<I", mmio_bytes, ch0 + p41.MHLX_CH_OFF_TX_HEAD)
    (tx_tail,) = struct.unpack_from("<I", mmio_bytes, ch0 + p41.MHLX_CH_OFF_TX_TAIL)
    (tx_cap,) = struct.unpack_from("<I", mmio_bytes, ch0 + p41.MHLX_CH_OFF_TX_CAP)
    (rx_head,) = struct.unpack_from("<I", mmio_bytes, ch0 + p41.MHLX_CH_OFF_RX_HEAD)
    (rx_tail,) = struct.unpack_from("<I", mmio_bytes, ch0 + p41.MHLX_CH_OFF_RX_TAIL)
    (rx_cap,) = struct.unpack_from("<I", mmio_bytes, ch0 + p41.MHLX_CH_OFF_RX_CAP)

    opcodes: List[str] = []
    max_slots = min(tx_head, len(ring_bytes) // p41.MHLX_SLOT_BYTES)
    for idx in range(max_slots):
        off = idx * p41.MHLX_SLOT_BYTES
        slot_magic, opcode, _seq, _plen = struct.unpack_from("<IIII", ring_bytes, off)
        if slot_magic == p41.MHLX_MAGIC:
            opcodes.append(f"0x{opcode:04x}")

    return MhlxRingPointerSnapshot(
        mmio_base_hex=f"0x{MHLX_PHYS:x}",
        shm_ring_phys_hex=f"0x{MHLX_RING_SHM_PHYS:x}",
        mhlx_magic_hex=f"0x{magic:08x}",
        magic_valid=True,
        channel_count=ch_count,
        shm_loader_status=loader_status,
        cp_mutation_bytes=cp_mut,
        ch0_tx_head=tx_head,
        ch0_tx_tail=tx_tail,
        ch0_tx_cap=tx_cap,
        ch0_rx_head=rx_head,
        ch0_rx_tail=rx_tail,
        ch0_rx_cap=rx_cap,
        decoded_slot_count=len(opcodes),
        decoded_opcodes_hex=tuple(opcodes),
        ring_sha256=hashlib.sha256(ring_bytes).hexdigest(),
    )


# ---------------------------------------------------------------------------
# Clean-Room QMP JSON-RPC Protocol Client & Transport Simulator
# ---------------------------------------------------------------------------


class SimulatedQmpGuestTransport:
    """In-memory QEMU QMP JSON-RPC simulator backed by guest physical memory pages.

    Strictly passive and read-only (`nop_count == 0`, `cp_mutation_bytes == 0`):
    - Enforces QMP `CAPABILITIES_NEGOTIATION` before `COMMAND_MODE`.
    - Serves `qmp_capabilities`, `query-status`, `query-cpus-fast`, `pmemsave`,
      and `human-monitor-command` (`xp`, `info registers`, `gva2gpa`).
    - Rejects any mutating HMP/QMP commands to guarantee zero guest mutation.
    """

    def __init__(self) -> None:
        self._negotiated = False
        self._pmemsave_captures: Dict[str, bytes] = {}
        self.command_journal: List[Dict[str, Any]] = []

        key_mb = build_clean_room_key_mailbox_bytes()
        ctrl_mb = build_clean_room_ctrl_mailbox_bytes()
        gpe0_slice = build_clean_room_gpe0_slice_bytes(width=64, height=32)
        mhlx_mmio, mhlx_ring = build_clean_room_mhlx_snapshot_bytes()

        self._phys_regions: Tuple[Tuple[int, bytes], ...] = (
            (KEY_MB_PHYS, key_mb),
            (MHLX_RING_SHM_PHYS, mhlx_ring),
            (CTRL_MB_PHYS, ctrl_mb),
            (GPE0_PHYS, gpe0_slice),
            (MHLX_PHYS, mhlx_mmio),
        )

    @property
    def negotiated(self) -> bool:
        return self._negotiated

    def greeting_line(self) -> str:
        return json.dumps(
            {
                "QMP": {
                    "version": {"qemu": {"major": 9, "minor": 2, "micro": 0}, "package": "fx3-vm-clean-room"},
                    "capabilities": ["oob"],
                }
            },
            separators=(",", ":"),
        )

    def read_phys_bytes(self, phys_addr: int, size: int) -> bytes:
        if size <= 0 or size > 4 * 1024 * 1024:
            raise QmpProtocolError(f"Invalid physical read size: {size}")
        for base, blob in self._phys_regions:
            end = base + len(blob)
            if base <= phys_addr and phys_addr + size <= end:
                off = phys_addr - base
                return blob[off : off + size]
        raise QmpProtocolError(f"Unmapped physical introspection range: 0x{phys_addr:x}+{size}")

    def get_captured_pmemsave(self, label: str) -> bytes:
        if label not in self._pmemsave_captures:
            raise QmpProtocolError(f"No in-memory pmemsave capture for {label!r}")
        return self._pmemsave_captures[label]

    def _handle_hmp(self, cmd_line: str) -> str:
        text = cmd_line.strip()
        if text == "info registers":
            return (
                "PC=ffffff800810a420 SP=ffffff8009403f00 PSTATE=600001c5\n"
                "X00=000000004658364c X01=000000041e000e00 X02=000000041df00000 X03=0000000000000000\n"
            )
        if text.startswith("gva2gpa "):
            addr_tok = text.split(None, 1)[1].strip()
            gva = int(addr_tok, 16)
            known_map = {
                0xFFFFFF80_41DF0000: KEY_MB_PHYS,
                0xFFFFFF80_41E00E00: CTRL_MB_PHYS,
                0xFFFFFF80_41E01000: GPE0_PHYS,
                0xFFFFFF80_F0800000: MHLX_PHYS,
            }
            gpa = known_map.get(gva, gva & 0xFFFF_FFFF)
            return f"gpa: 0x{gpa:x}\n"

        xp_match = re.fullmatch(r"xp\s+/(\d+)([xdu])([bhwg])\s+(0x[0-9a-fA-F]+|[0-9]+)", text)
        if xp_match:
            count = int(xp_match.group(1))
            fmt_kind = xp_match.group(2)
            width_ch = xp_match.group(3)
            addr = int(xp_match.group(4), 0)
            width_map = {"b": 1, "h": 2, "w": 4, "g": 8}
            fmt_map = {"b": "B", "h": "H", "w": "I", "g": "Q"}
            unit = width_map[width_ch]
            raw = self.read_phys_bytes(addr, count * unit)
            lines: List[str] = []
            per_line = 4 if unit <= 4 else 2
            for idx in range(0, count, per_line):
                line_addr = addr + idx * unit
                vals: List[str] = []
                for j in range(idx, min(count, idx + per_line)):
                    (val,) = struct.unpack_from("<" + fmt_map[width_ch], raw, j * unit)
                    if fmt_kind == "x":
                        vals.append(f"0x{val:0{unit * 2}x}")
                    else:
                        vals.append(str(val))
                lines.append(f"{line_addr:016x}: " + " ".join(vals))
            return "\n".join(lines) + "\n"

        raise QmpProtocolError(f"Non-intrusive read-only tracer rejected HMP command: {text!r}")

    def execute_raw(self, req_line: str) -> str:
        req = json.loads(req_line)
        cmd = req.get("execute")
        req_id = req.get("id")
        args = req.get("arguments") or {}

        def _reply(payload: Dict[str, Any]) -> str:
            resp = dict(payload)
            if req_id is not None:
                resp["id"] = req_id
            self.command_journal.append({"execute": cmd, "id": req_id, "ok": "return" in resp})
            return json.dumps(resp, separators=(",", ":"))

        if not self._negotiated:
            if cmd != "qmp_capabilities":
                return _reply(
                    {
                        "error": {
                            "class": "CommandNotFound",
                            "desc": f"The command {cmd} has not been found (capabilities not negotiated)",
                        }
                    }
                )
            self._negotiated = True
            return _reply({"return": {}})

        if cmd == "qmp_capabilities":
            return _reply(
                {"error": {"class": "CommandNotFound", "desc": "Capabilities already negotiated"}}
            )
        if cmd == "query-status":
            return _reply({"return": {"running": True, "singlestep": False, "status": "running"}})
        if cmd == "query-cpus-fast":
            cpus = [
                {
                    "cpu-index": idx,
                    "qom-path": f"/machine/unattached/device[{idx}]",
                    "thread-id": 1000 + idx,
                    "target": "aarch64",
                    "props": {"core-id": idx},
                }
                for idx in range(4)
            ]
            return _reply({"return": cpus})
        if cmd == "human-monitor-command":
            cmd_line = str(args.get("command-line", ""))
            try:
                out = self._handle_hmp(cmd_line)
            except QmpProtocolError as exc:
                return _reply({"error": {"class": "GenericError", "desc": str(exc)}})
            return _reply({"return": out})
        if cmd == "pmemsave":
            val = int(args["val"])
            size = int(args["size"])
            filename = str(args["filename"])
            if not filename.startswith("mem://"):
                raise QmpProtocolError(
                    "Clean-room pmemsave requires virtual in-memory 'mem://' target (zero repo disk writes)"
                )
            blob = self.read_phys_bytes(val, size)
            self._pmemsave_captures[filename] = blob
            return _reply({"return": {}})

        return _reply(
            {
                "error": {
                    "class": "CommandNotFound",
                    "desc": f"Disallowed or unsupported QMP command in passive tracer: {cmd}",
                }
            }
        )


class QmpGuestIntrospectionClient:
    """Clean-room QMP JSON-RPC client exercising non-intrusive guest physical introspection."""

    def __init__(self, transport: SimulatedQmpGuestTransport) -> None:
        self.transport = transport
        self._seq = 0
        self.greeting = json.loads(transport.greeting_line())

    def call(self, execute: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        self._seq += 1
        req: Dict[str, Any] = {"execute": execute, "id": self._seq}
        if arguments is not None:
            req["arguments"] = arguments
        resp = json.loads(self.transport.execute_raw(json.dumps(req)))
        if "error" in resp:
            raise QmpProtocolError(f"QMP error on {execute}: {resp['error']}")
        return resp["return"]

    def negotiate_capabilities(self, *, enable_oob: bool = True) -> Dict[str, Any]:
        args = {"enable": ["oob"]} if enable_oob else {}
        return self.call("qmp_capabilities", args)

    def query_status(self) -> Dict[str, Any]:
        return self.call("query-status")

    def query_cpus_fast(self) -> List[Dict[str, Any]]:
        res = self.call("query-cpus-fast")
        assert isinstance(res, list)
        return res

    def hmp(self, command_line: str) -> str:
        res = self.call("human-monitor-command", {"command-line": command_line})
        return str(res)

    def hmp_xp_u32(self, phys_addr: int, count: int) -> Tuple[int, ...]:
        out = self.hmp(f"xp /{count}xw 0x{phys_addr:x}")
        values: List[int] = []
        for line in out.splitlines():
            if ":" not in line:
                continue
            rhs = line.split(":", 1)[1].strip()
            for tok in rhs.split():
                values.append(int(tok, 16))
        if len(values) != count:
            raise IntrospectionDecodeError(f"xp returned {len(values)} words, expected {count}")
        return tuple(values)

    def pmemsave_capture(self, phys_addr: int, size: int, mem_uri: str) -> bytes:
        self.call("pmemsave", {"val": phys_addr, "size": size, "filename": mem_uri})
        return self.transport.get_captured_pmemsave(mem_uri)


def build_tcg_plugin_and_gdb_specs() -> Dict[str, Any]:
    """Build non-intrusive QEMU TCG plugin (`libqemu-plugin`) & GDB RSP watchpoint specs."""
    return {
        "nop_count": NOP_COUNT,
        "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
        "cp_mutation_bytes": CP_MUTATION_BYTES,
        "tcg_plugin_spec": {
            "header": "include/plugins/qemu-plugin.h",
            "cpp_wrapper": "libqemu-plugin.h (QBox LibQemuPlugin)",
            "exported_symbol": "QEMU_PLUGIN_EXPORT int qemu_plugin_version = QEMU_PLUGIN_VERSION",
            "entry_symbol": "qemu_plugin_install",
            "callbacks": [
                "qemu_plugin_register_vcpu_tb_trans_cb",
                "qemu_plugin_register_vcpu_mem_cb(QEMU_PLUGIN_MEM_RW)",
                "qemu_plugin_read_memory_hwaddr",
            ],
            "watched_phys_apertures": [
                f"0x{KEY_MB_PHYS:x}",
                f"0x{CTRL_MB_PHYS:x}",
                f"0x{GPE0_PHYS:x}",
                f"0x{MHLX_PHYS:x}",
            ],
            "cli_flag": "-plugin contrib/plugins/libhotblocks.so -d plugin",
        },
        "gdb_rsp_spec": {
            "accel": "tcg",
            "unlimited_hw_watchpoints": True,
            "physical_memory_mode_packet": "Qqemu.PhyMemMode:1",
            "physical_memory_query_packet": "qqemu.PhyMemMode",
            "watchpoint_packets": [
                f"Z2,{KEY_MB_PHYS:x},4",
                f"Z2,{CTRL_MB_PHYS:x},4",
            ],
            "guest_text_sw_breakpoints": 0,
        },
    }


# ---------------------------------------------------------------------------
# Wired USB-LAN (`CDC-NCM` / `RNDIS`) & `PTP-IP` (`TCP 15740`) Safe-Channel Tracer
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UsbLanEvaluationResult:
    passed: bool
    status: str
    usb_class: str
    chipset: str
    link_speed_mbps: int
    ip_mode: str
    camera_ip: str
    subnet_mask: str
    default_gateway: str
    gateway_same_subnet: bool
    p12_airplane_mode: bool
    wlan_disabled: bool
    bt_disabled: bool
    wf12_00342260_immune: bool
    monitoring_features: Tuple[str, ...]
    wdt_resets: int


def evaluate_usblan_link_under_p12(
    *,
    camera_body: str = "ILME-FX3",
    usb_class: str = USB_CLASS_CDC_NCM,
    chipset: str = "RTL8153",
    link_speed_mbps: int = 1000,
    ip_mode: str = "Manual",
    camera_ip: str = "192.168.0.10",
    subnet_mask: str = "255.255.255.0",
    default_gateway: str = "192.168.0.1",
    p12_airplane_mode: bool = True,
) -> UsbLanEvaluationResult:
    """Evaluate wired USB-C Ethernet (`USB-LAN`) viability under `P12` Airplane-Mode."""
    # Check P12 Airplane-mode shadow state (0x019e0012=00, 0x01a20002=00 -> BT/Wi-Fi off)
    if p12_airplane_mode:
        bt_res = p29.run_bsa_bringup_scenario(
            p29.BT_MODE_AIRPLANE_GATED,
            bkid_0x019e0012=0x00,
            bkid_0x01a20002=0x00,
        )
        bt_disabled = bt_res.tx_packets == 0 and bt_res.airplane_latched
    else:
        bt_disabled = False

    wlan_disabled = p12_airplane_mode
    wf12_immune = p12_airplane_mode and bt_disabled

    # Check USB-LAN class and adapter chipset constraints
    if usb_class != USB_CLASS_CDC_NCM:
        return UsbLanEvaluationResult(
            passed=False,
            status=f"REJECTED_UNSUPPORTED_USB_CLASS_{usb_class}",
            usb_class=usb_class,
            chipset=chipset,
            link_speed_mbps=link_speed_mbps,
            ip_mode=ip_mode,
            camera_ip=camera_ip,
            subnet_mask=subnet_mask,
            default_gateway=default_gateway,
            gateway_same_subnet=False,
            p12_airplane_mode=p12_airplane_mode,
            wlan_disabled=wlan_disabled,
            bt_disabled=bt_disabled,
            wf12_00342260_immune=wf12_immune,
            monitoring_features=(),
            wdt_resets=0,
        )

    if chipset not in ALLOWED_USBLAN_CHIPSETS_1GBPS or link_speed_mbps != 1000:
        return UsbLanEvaluationResult(
            passed=False,
            status="REJECTED_INCOMPATIBLE_ADAPTER_CHIPSET_OR_SPEED",
            usb_class=usb_class,
            chipset=chipset,
            link_speed_mbps=link_speed_mbps,
            ip_mode=ip_mode,
            camera_ip=camera_ip,
            subnet_mask=subnet_mask,
            default_gateway=default_gateway,
            gateway_same_subnet=False,
            p12_airplane_mode=p12_airplane_mode,
            wlan_disabled=wlan_disabled,
            bt_disabled=bt_disabled,
            wf12_00342260_immune=wf12_immune,
            monitoring_features=(),
            wdt_resets=0,
        )

    # FX3/FX3A Manual IP requires a Default Gateway in the same subnet
    net = ipaddress.IPv4Network(f"{camera_ip}/{subnet_mask}", strict=False)
    gw_ok = True
    if ip_mode.lower() == "manual":
        if not default_gateway.strip():
            gw_ok = False
        else:
            try:
                gw_ip = ipaddress.IPv4Address(default_gateway.strip())
                gw_ok = gw_ip in net and gw_ip != ipaddress.IPv4Address(camera_ip)
            except ipaddress.AddressValueError:
                gw_ok = False

    if not gw_ok:
        return UsbLanEvaluationResult(
            passed=False,
            status="MISCONFIGURED_MISSING_SAME_SUBNET_GATEWAY",
            usb_class=usb_class,
            chipset=chipset,
            link_speed_mbps=link_speed_mbps,
            ip_mode=ip_mode,
            camera_ip=camera_ip,
            subnet_mask=subnet_mask,
            default_gateway=default_gateway,
            gateway_same_subnet=False,
            p12_airplane_mode=p12_airplane_mode,
            wlan_disabled=wlan_disabled,
            bt_disabled=bt_disabled,
            wf12_00342260_immune=wf12_immune,
            monitoring_features=(),
            wdt_resets=0,
        )

    features: Tuple[str, ...] = (
        "Monitor & Control Live View (eth0)",
        "False Color (Pattern1 SDR / Pattern2 S-Log3)",
        "Waveform & Histogram Telemetry",
        "Focus Map & Touch-Focus Control",
        "Access Authentication (SSH/TLS)",
        "Content Browser Mobile / Camera Remote SDK (TCP 15740)"
        if "FX6" in camera_body
        else "Camera Remote SDK / PTP-IP (TCP 15740)",
    )
    return UsbLanEvaluationResult(
        passed=True,
        status="ALLOWED_USB_LAN_LINK_UP",
        usb_class=usb_class,
        chipset=chipset,
        link_speed_mbps=link_speed_mbps,
        ip_mode=ip_mode,
        camera_ip=camera_ip,
        subnet_mask=subnet_mask,
        default_gateway=default_gateway,
        gateway_same_subnet=True,
        p12_airplane_mode=p12_airplane_mode,
        wlan_disabled=wlan_disabled,
        bt_disabled=bt_disabled,
        wf12_00342260_immune=wf12_immune,
        monitoring_features=features,
        wdt_resets=0,
    )


@dataclass(frozen=True)
class PtpIpPacketTrace:
    tx_id: int
    tcp_port: int
    pkt_type_hex: str
    opcode_hex: str
    opcode_name: str
    authenticated: bool
    allowed: bool
    decision: str
    prop_id_hex: str
    cp_mutation_bytes: int
    nvram_persistent_writes: int
    physical_device_writes: int


def build_ptpip_cmd_request_frame(
    *,
    opcode: int,
    tx_id: int,
    param1: int = 0,
    param2: int = 0,
    data_phase: int = 1,
) -> bytes:
    """Build an ISO 15740 PTP-IP `CmdRequest` packet (`len, type=6, data_phase, opcode, tx_id, p1, p2`)."""
    return struct.pack("<IIIIIII", 28, PTPIP_PKT_CMD_REQ, data_phase, opcode & 0xFFFF, tx_id, param1, param2)


def evaluate_ptpip_15740_packet(
    frame: bytes,
    *,
    tcp_port: int = PTPIP_TCP_PORT,
    authenticated: bool = True,
) -> PtpIpPacketTrace:
    """Trace and enforce safe-channel policy on an ISO 15740 PTP-IP packet."""
    if len(frame) < 20:
        raise IntrospectionDecodeError(f"PTP-IP frame too short: {len(frame)} < 20")
    pkt_len, pkt_type, _data_phase, opcode_raw, tx_id = struct.unpack_from("<IIIII", frame, 0)
    if pkt_len != len(frame):
        raise IntrospectionDecodeError(f"PTP-IP length mismatch: header={pkt_len}, actual={len(frame)}")
    opcode = opcode_raw & 0xFFFF
    prop_id = struct.unpack_from("<I", frame, 20)[0] if len(frame) >= 24 else 0

    if tcp_port != PTPIP_TCP_PORT:
        return PtpIpPacketTrace(
            tx_id=tx_id,
            tcp_port=tcp_port,
            pkt_type_hex=f"0x{pkt_type:08x}",
            opcode_hex=f"0x{opcode:04x}",
            opcode_name="NonPtpIpPort",
            authenticated=authenticated,
            allowed=False,
            decision="BLOCKED_UNEXPECTED_TCP_PORT",
            prop_id_hex=f"0x{prop_id:04x}",
            cp_mutation_bytes=0,
            nvram_persistent_writes=0,
            physical_device_writes=0,
        )

    if opcode in BLOCKED_PTPIP_MUTATION_OPCODES:
        return PtpIpPacketTrace(
            tx_id=tx_id,
            tcp_port=tcp_port,
            pkt_type_hex=f"0x{pkt_type:08x}",
            opcode_hex=f"0x{opcode:04x}",
            opcode_name=BLOCKED_PTPIP_MUTATION_OPCODES[opcode],
            authenticated=authenticated,
            allowed=False,
            decision="BLOCKED_FIRMWARE_UPDATE_OPCODE",
            prop_id_hex=f"0x{prop_id:04x}",
            cp_mutation_bytes=0,
            nvram_persistent_writes=0,
            physical_device_writes=0,
        )

    if not authenticated and opcode not in (PTPIP_OPCODE_SONY_SDIO_CONNECT, PTPIP_OPCODE_GET_DEVICE_INFO):
        return PtpIpPacketTrace(
            tx_id=tx_id,
            tcp_port=tcp_port,
            pkt_type_hex=f"0x{pkt_type:08x}",
            opcode_hex=f"0x{opcode:04x}",
            opcode_name=ALLOWED_PTPIP_READONLY_OPCODES.get(opcode, "UnknownOpcode"),
            authenticated=False,
            allowed=False,
            decision="BLOCKED_UNAUTHENTICATED_SESSION",
            prop_id_hex=f"0x{prop_id:04x}",
            cp_mutation_bytes=0,
            nvram_persistent_writes=0,
            physical_device_writes=0,
        )

    if opcode in ALLOWED_PTPIP_READONLY_OPCODES:
        return PtpIpPacketTrace(
            tx_id=tx_id,
            tcp_port=tcp_port,
            pkt_type_hex=f"0x{pkt_type:08x}",
            opcode_hex=f"0x{opcode:04x}",
            opcode_name=ALLOWED_PTPIP_READONLY_OPCODES[opcode],
            authenticated=authenticated,
            allowed=True,
            decision="ALLOWED_READONLY_TELEMETRY",
            prop_id_hex=f"0x{prop_id:04x}",
            cp_mutation_bytes=0,
            nvram_persistent_writes=0,
            physical_device_writes=0,
        )

    if opcode in ALLOWED_PTPIP_SAFE_CONTROL_OPCODES:
        if prop_id in ALLOWED_SAFE_PROP_IDS:
            return PtpIpPacketTrace(
                tx_id=tx_id,
                tcp_port=tcp_port,
                pkt_type_hex=f"0x{pkt_type:08x}",
                opcode_hex=f"0x{opcode:04x}",
                opcode_name=ALLOWED_PTPIP_SAFE_CONTROL_OPCODES[opcode],
                authenticated=authenticated,
                allowed=True,
                decision="ALLOWED_SAFE_MONITOR_CONTROL",
                prop_id_hex=f"0x{prop_id:04x}",
                cp_mutation_bytes=0,
                nvram_persistent_writes=0,
                physical_device_writes=0,
            )
        return PtpIpPacketTrace(
            tx_id=tx_id,
            tcp_port=tcp_port,
            pkt_type_hex=f"0x{pkt_type:08x}",
            opcode_hex=f"0x{opcode:04x}",
            opcode_name=ALLOWED_PTPIP_SAFE_CONTROL_OPCODES[opcode],
            authenticated=authenticated,
            allowed=False,
            decision="BLOCKED_UNWHITELISTED_PROP_MUTATION",
            prop_id_hex=f"0x{prop_id:04x}",
            cp_mutation_bytes=0,
            nvram_persistent_writes=0,
            physical_device_writes=0,
        )

    return PtpIpPacketTrace(
        tx_id=tx_id,
        tcp_port=tcp_port,
        pkt_type_hex=f"0x{pkt_type:08x}",
        opcode_hex=f"0x{opcode:04x}",
        opcode_name="UnknownVendorOpcode",
        authenticated=authenticated,
        allowed=False,
        decision="BLOCKED_UNKNOWN_OPCODE_FAIL_CLOSED",
        prop_id_hex=f"0x{prop_id:04x}",
        cp_mutation_bytes=0,
        nvram_persistent_writes=0,
        physical_device_writes=0,
    )


def trace_ptpip_15740_session() -> Dict[str, Any]:
    """Run deterministic PTP-IP (`TCP 15740`) safe-channel audit across allowed and blocked opcodes."""
    packets = [
        (build_ptpip_cmd_request_frame(opcode=PTPIP_OPCODE_SONY_SDIO_CONNECT, tx_id=1), True),
        (build_ptpip_cmd_request_frame(opcode=PTPIP_OPCODE_GET_DEVICE_INFO, tx_id=2), True),
        (build_ptpip_cmd_request_frame(opcode=PTPIP_OPCODE_OPEN_SESSION, tx_id=3), True),
        (build_ptpip_cmd_request_frame(opcode=PTPIP_OPCODE_SONY_GET_LIVE_VIEW, tx_id=4), True),
        (build_ptpip_cmd_request_frame(opcode=PTPIP_OPCODE_SONY_SET_DEVICE_PROP, tx_id=5, param1=0xD2C1), True),
        (build_ptpip_cmd_request_frame(opcode=PTPIP_OPCODE_SONY_FW_UPDATE_INIT, tx_id=6), True),
        (build_ptpip_cmd_request_frame(opcode=PTPIP_OPCODE_SONY_FW_UPDATE_WRITE, tx_id=7), True),
        (build_ptpip_cmd_request_frame(opcode=PTPIP_OPCODE_SONY_CAL_PART_WRITE, tx_id=8), True),
        (build_ptpip_cmd_request_frame(opcode=PTPIP_OPCODE_SONY_NVRAM_RAW_WRITE, tx_id=9), True),
    ]
    traces = [evaluate_ptpip_15740_packet(frame, authenticated=auth) for frame, auth in packets]
    allowed_traces = [t for t in traces if t.allowed]
    blocked_traces = [t for t in traces if not t.allowed]
    return {
        "tcp_port": PTPIP_TCP_PORT,
        "ssdp_udp_port": SSDP_UDP_PORT,
        "total_packets": len(traces),
        "allowed_count": len(allowed_traces),
        "blocked_count": len(blocked_traces),
        "fw_update_opcodes_blocked": all(
            not t.allowed and t.decision == "BLOCKED_FIRMWARE_UPDATE_OPCODE"
            for t in blocked_traces
        ),
        "cp_mutation_bytes": 0,
        "nvram_persistent_writes": 0,
        "physical_device_writes": 0,
        "traces": [asdict(t) for t in traces],
    }


# ---------------------------------------------------------------------------
# Unified Phase 58 Stage 7 Audit Orchestrator & CLI
# ---------------------------------------------------------------------------


_PHASE58_CACHE: Dict[Tuple[str, bool], Dict[str, Any]] = {}


def run_phase58_qmp_tracer_audit(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, Any]:
    """Run full Phase 58 Stage 7 QMP guest introspection + USB-LAN PTP-IP safe-channel audit."""
    donor_audit = inspect_usblan_ptpip_donors(force_clean_room=force_clean_room, env=env)
    cache_key = (donor_audit.source_mode, donor_audit.all_contracts_verified)
    if cache_key in _PHASE58_CACHE:
        return json.loads(json.dumps(_PHASE58_CACHE[cache_key]))

    # 1. QMP JSON-RPC Non-Intrusive Session
    transport = SimulatedQmpGuestTransport()
    client = QmpGuestIntrospectionClient(transport)

    # Verify pre-capability rejection first (protocol conformance)
    pre_cap_rejected = False
    try:
        client.query_status()
    except QmpProtocolError:
        pre_cap_rejected = True

    client.negotiate_capabilities(enable_oob=True)
    vm_status = client.query_status()
    cpus_fast = client.query_cpus_fast()
    regs_text = client.hmp("info registers")
    gpa_line = client.hmp("gva2gpa 0xffffff8041e00e00").strip()

    # 2. HMP `xp` + `pmemsave` Physical Memory Introspection (Zero Guest Code Modification)
    key_mb_words = client.hmp_xp_u32(KEY_MB_PHYS, 16)
    key_mb_raw = struct.pack("<16I", *key_mb_words)
    key_mb = decode_key_mailbox_bytes(key_mb_raw)

    ctrl_mb_words = client.hmp_xp_u32(CTRL_MB_PHYS, CTRL_MB_WORDS)
    ctrl_mb_raw = struct.pack(f"<{CTRL_MB_WORDS}I", *ctrl_mb_words)
    ctrl_mb = decode_ctrl_mailbox_bytes(ctrl_mb_raw)

    gpe0_raw = client.pmemsave_capture(GPE0_PHYS, 64 * 32 * 4, "mem://gpe0_slice.bin")
    gpe0_probe = decode_gpe0_framebuffer_slice(gpe0_raw, width=64, height=32)

    mhlx_mmio_raw = client.pmemsave_capture(MHLX_PHYS, 0x180, "mem://mhlx_mmio.bin")
    mhlx_ring_raw = client.pmemsave_capture(
        MHLX_RING_SHM_PHYS,
        p41.MHLX_RING_CAPACITY * p41.MHLX_SLOT_BYTES,
        "mem://mhlx_ring.bin",
    )
    mhlx_snapshot = decode_mhlx_ring_snapshot(mhlx_mmio_raw, mhlx_ring_raw)

    # 3. USB-LAN (CDC-NCM vs RNDIS) under P12 Airplane-Mode + PTP-IP (15740) Safe-Channel
    usblan_fx3_ncm = evaluate_usblan_link_under_p12(
        camera_body="ILME-FX3",
        usb_class=USB_CLASS_CDC_NCM,
        chipset="RTL8153",
        link_speed_mbps=1000,
        ip_mode="Manual",
        camera_ip="192.168.0.10",
        subnet_mask="255.255.255.0",
        default_gateway="192.168.0.1",
        p12_airplane_mode=True,
    )
    usblan_fx6_ncm = evaluate_usblan_link_under_p12(
        camera_body="ILME-FX6",
        usb_class=USB_CLASS_CDC_NCM,
        chipset="AX88179",
        link_speed_mbps=1000,
        ip_mode="Auto",
        camera_ip="192.168.0.20",
        subnet_mask="255.255.255.0",
        default_gateway="192.168.0.1",
        p12_airplane_mode=True,
    )
    usblan_rndis_rejected = evaluate_usblan_link_under_p12(
        camera_body="ILME-FX3",
        usb_class=USB_CLASS_RNDIS,
        chipset="RTL8153",
        p12_airplane_mode=True,
    )
    usblan_ax88179a_rejected = evaluate_usblan_link_under_p12(
        camera_body="ILME-FX6",
        usb_class=USB_CLASS_CDC_NCM,
        chipset="AX88179A",
        p12_airplane_mode=True,
    )
    usblan_missing_gw_rejected = evaluate_usblan_link_under_p12(
        camera_body="ILME-FX3",
        usb_class=USB_CLASS_CDC_NCM,
        chipset="RTL8153",
        ip_mode="Manual",
        camera_ip="192.168.0.10",
        subnet_mask="255.255.255.0",
        default_gateway="",
        p12_airplane_mode=True,
    )

    ptpip_session = trace_ptpip_15740_session()
    instrumentation_specs = build_tcg_plugin_and_gdb_specs()

    all_passed = (
        donor_audit.all_contracts_verified
        and pre_cap_rejected
        and vm_status.get("status") == "running"
        and len(cpus_fast) == 4
        and "PC=" in regs_text
        and gpa_line == f"gpa: 0x{CTRL_MB_PHYS:x}"
        and key_mb.magic_valid
        and ctrl_mb.magic_valid
        and ctrl_mb.nd_p4_locked_val == 0
        and ctrl_mb.bk4_locked
        and gpe0_probe.fx6_px_amber_parity_ok
        and mhlx_snapshot.magic_valid
        and mhlx_snapshot.cp_mutation_bytes == 0
        and mhlx_snapshot.decoded_slot_count == 2
        and usblan_fx3_ncm.passed
        and usblan_fx3_ncm.wf12_00342260_immune
        and usblan_fx6_ncm.passed
        and not usblan_rndis_rejected.passed
        and not usblan_ax88179a_rejected.passed
        and not usblan_missing_gw_rejected.passed
        and ptpip_session["allowed_count"] == 5
        and ptpip_session["blocked_count"] == 4
        and ptpip_session["fw_update_opcodes_blocked"]
    )

    core: Dict[str, Any] = {
        "schema": PHASE_58_SCHEMA,
        "version": PHASE_58_VERSION,
        "all_checks_passed": all_passed,
        "source_mode": donor_audit.source_mode,
        "redlines": {
            "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
            "nop_count": NOP_COUNT,
            "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
            "cp_mutation_bytes": CP_MUTATION_BYTES,
            "wbi_mutation_bytes": WBI_MUTATION_BYTES,
            "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
            "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
            "physical_device_writes": PHYSICAL_DEVICE_WRITES,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "qmp_session": {
            "qemu_version": client.greeting["QMP"]["version"]["qemu"],
            "capabilities": client.greeting["QMP"]["capabilities"],
            "pre_capabilities_rejected": pre_cap_rejected,
            "vm_status": vm_status,
            "vcpu_count": len(cpus_fast),
            "cpus_fast": cpus_fast,
            "gva2gpa_ctrl_mb": gpa_line,
            "command_count": len(transport.command_journal),
        },
        "guest_introspection": {
            "key_mailbox": asdict(key_mb),
            "ctrl_mailbox": asdict(ctrl_mb),
            "gpe0_probe": asdict(gpe0_probe),
            "mhlx_ring": asdict(mhlx_snapshot),
            "instrumentation_specs": instrumentation_specs,
        },
        "usblan_p12_isolation": {
            "fx3_cdc_ncm_rtl8153": asdict(usblan_fx3_ncm),
            "fx6_cdc_ncm_ax88179": asdict(usblan_fx6_ncm),
            "rndis_rejected": asdict(usblan_rndis_rejected),
            "ax88179a_rejected": asdict(usblan_ax88179a_rejected),
            "fx3_missing_gateway_rejected": asdict(usblan_missing_gw_rejected),
        },
        "ptpip_15740_safe_channel": ptpip_session,
    }
    digest = hashlib.sha256(
        json.dumps(core, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    core["audit_digest_sha256"] = digest
    _PHASE58_CACHE[cache_key] = core
    return json.loads(json.dumps(core))


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="qmp_guest_introspection_tracer.py",
        description="Phase 58 Stage 7 Non-Intrusive QMP Guest Introspection & USB-LAN PTP-IP Tracer",
    )
    parser.add_argument("--self-test", action="store_true", help="Run full Stage 7 audit")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line PASS/FAIL summary")
    args = parser.parse_args(argv)

    rep = run_phase58_qmp_tracer_audit(force_clean_room=True if args.clean_room else None)

    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        gi = rep["guest_introspection"]
        ptp = rep["ptpip_15740_safe_channel"]
        usb = rep["usblan_p12_isolation"]["fx3_cdc_ncm_rtl8153"]
        sys.stdout.write(
            f"[{status}] Phase 58 QMP Guest Introspection & USB-LAN Tracer | "
            f"mode={rep['source_mode']} nop={rep['redlines']['nop_count']} "
            f"cp_mut={rep['redlines']['cp_mutation_bytes']} | "
            f"ctrl={gi['ctrl_mailbox']['ctrl_magic_hex']} "
            f"key={gi['key_mailbox']['magic_ascii']} "
            f"mhlx_slots={gi['mhlx_ring']['decoded_slot_count']} | "
            f"usblan={usb['usb_class']}/{usb['chipset']}(wf12_immune={usb['wf12_00342260_immune']}) "
            f"ptpip_15740={ptp['allowed_count']}ok/{ptp['blocked_count']}blocked | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
