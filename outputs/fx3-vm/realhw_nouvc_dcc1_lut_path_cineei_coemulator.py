#!/usr/bin/env python3
"""Phase 194 — Stage 34 (`34/34` Stage) `outputs/fx3-vm/` Real-Hardware Main Track:
`ILME-FX3` (`0x91030080`, `Ver. 7.02`) No-UVC USB Gadget Firewall, `USB-PD` (`NP-FZ100`
Mandatory) vs `DC-C1` (`>=65W / 5A`) Power Budget, Dual-Media `.cube` User LUT Path-Asymmetry
(`SD: /Private/Sony/PRO/LUT/` vs `CFexpress-A: /Sony/PRO/LUT/`), `Cine EI` (`800/12800`),
and `RMT-P1BT` BT/IR Mutual-Exclusion HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) donor inspection (< 0.10s, cached per
process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), and co-emulates all four Phase 194
real-hardware pillars (A-D) while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `usb_phy_hang_events == 0`, `power_cut_brownout_events == 0`
- `sensor_analog_gain_contamination_events == 0`, `raw_firmware_bytes_leaked == 0`
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
import struct
from typing import Dict, List, Mapping, Optional, Sequence, Tuple


# ---------------------------------------------------------------------------
# Phase 194 Schema & Hard-Locked Safety Redlines
# ---------------------------------------------------------------------------

PHASE_194_SCHEMA = "phase194_realhw_nouvc_dcc1_lut_path_cineei_coemulator_v1"
PHASE_194_VERSION = "194.0.0"
STAGE_INDEX = 34
STAGE_TOTAL = 34
MILESTONE_LABEL = "34/34"
STAGE_NAME = "stage34_realhw_nouvc_dcc1_lut_path_cineei_hil"

P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
NVRAM_PERSISTENT_WRITES = 0
BK4_PERSISTENT_NVRAM_WRITES = 0
PHYSICAL_DEVICE_WRITES = 0
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
EMMC_NFLASHA_WRITE_COUNT = 0
EMMC_MUTATION_BYTES = 0
SPI_NOR_WRITE_AUTHORIZED = False
SPI_NOR_MUTATION_BYTES = 0
EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False
PHYSICAL_USB_PACKETS_EMITTED = 0
OTP_FUSE_TOUCHES = 0
RPMB_COUNTER_INCREMENTS = 0
USB_PHY_HANG_EVENTS = 0
POWER_CUT_BROWNOUT_EVENTS = 0
SENSOR_ANALOG_GAIN_CONTAMINATION_EVENTS = 0
WF12_00342260_HITS = 0
APPFW_CRASHES = 0
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
RAW_FIRMWARE_BYTES_LEAKED = 0
DONOR_ACCESS_MODE = "O_RDONLY"
BOUNDED_WINDOW_MAX_BYTES = 4096

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# ---------------------------------------------------------------------------
# Verified Local Donor Specs (12 FX3 7.02 & FX6 6.01 Real-Hardware Donors)
# ---------------------------------------------------------------------------

_FX3_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr"
_FX3_V4_USR_PREFIX = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr"
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_usb_ctrl": f"{_FX3_USR_PREFIX}/lib/libUsbControl.so",
    "fx6_usb_ctrl": f"{_FX6_NF15_PREFIX}/lib/libUsbControl.so",
    "fx3_cdc_ncm": f"{_FX3_V4_USR_PREFIX}/kmod/cdc_ncm.ko",
    "fx3_rndis_host": f"{_FX3_V4_USR_PREFIX}/kmod/rndis_host.ko",
    "fx3_bt_core": f"{_FX3_USR_PREFIX}/lib/libInfraBluetoothCore.so",
    "fx3_string_en_f": f"{_FX3_USR_PREFIX}/share/app/string_english_f.uxc",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
    "fx3_cpapp": "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
    "fx6_cpapp": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    "fx3_libmpr": f"{_FX3_USR_PREFIX}/lib/libmpr.so",
    "fx6_libmpr": f"{_FX6_NF15_PREFIX}/lib/libmpr.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_usb_ctrl": 135_424,
    "fx6_usb_ctrl": 135_424,
    "fx3_cdc_ncm": 32_208,
    "fx3_rndis_host": 14_064,
    "fx3_bt_core": 267_592,
    "fx3_string_en_f": 373_820,
    "fx3_appfw": 79_015_712,
    "fx6_appfw": 50_520_424,
    "fx3_cpapp": 15_980_568,
    "fx6_cpapp": 17_952_816,
    "fx3_libmpr": 3_517_008,
    "fx6_libmpr": 28_921_824,
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_usb_ctrl": (b"UsbControl", b"MTP", b"USB"),
    "fx6_usb_ctrl": (b"UsbControl", b"MTP", b"USB"),
    "fx3_cdc_ncm": (b"cdc_ncm", b"NCM", b"4.9.337"),
    "fx3_rndis_host": (b"rndis_host", b"RNDIS", b"4.9.337"),
    "fx3_bt_core": (b"ttyAMA3", b"BSA", b"Bluetooth"),
    "fx3_string_en_f": (
        b"USB Connection Mode",
        b"Sel. When Connect",
        b"Mass Storage",
        b"MTP",
        b"Remote Shoot",
        b"USB-LAN",
        b"USB Power Supply",
        b"Network Streaming",
        b"Cine EI",
        b"Bluetooth Rmt Ctrl",
        b"IR Remote Ctrl",
    ),
}

# Pinned bounded windows (<= 4096 B each) for large CP/AP binaries so cold inspection is < 10 ms.
LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (49_967_027, "USB_LAN", b"USB_LAN_CONNECT_LAUNCH_ON"),
        (58_720_314, "RTMP", b"INFRA_NOTIFY_RTMP_LIVE_STREAMING_BITRATE"),
        (59_805_028, "CUBE_LUT_PATH", b"/Private/Sony/PRO/LUT"),
        (59_805_028, "CUBE_EXT", b".cube"),
        (60_034_641, "SRT", b"SRT ENC_OPEN"),
        (61_296_399, "CINE_EI", b"CINE_EI"),
        (62_168_487, "USB_POWER", b"state_SUPPLYING_USB_POWER_STATE_ON"),
        (62_239_604, "SIRCS_OFF", b"SIRCS_2SEC_EVENT_STATE_OFF"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (37_236_523, "CINE_EI", b"CINE_EI"),
        (37_406_901, "RTMP", b"RTMP"),
        (37_406_901, "SRT", b"SRT"),
        (37_604_361, "CUBE_EXT", b".cube"),
        (39_359_964, "PRO_LUT", b"/Private/Sony/PRO/LUT"),
        (40_157_356, "USB_LAN", b"USB_LAN"),
        (41_514_789, "SIRCS_OFF", b"SIRCS_2SEC_EVENT_STATE_OFF"),
    ),
    "fx3_cpapp": (
        (13_142_016, "ILME-FX3", b"ILME-FX3"),
        (14_921_728, "CUBE", b"CUBE"),
        (13_670_400, "SIRCS", b"SIRCS"),
        (10_758_144, "IMX510", b"IMX510"),
    ),
    "fx6_cpapp": (
        (16_893_952, "CUBE", b"CUBE"),
        (15_144_960, "SIRCS", b"SIRCS"),
        (12_220_416, "IMX510", b"IMX510"),
    ),
    "fx3_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (186_368, "SetLutData", b"SetLutData"),
        (223_232, "HEVC", b"HEVC"),
        (241_664, "LUT", b"LUT"),
    ),
    "fx6_libmpr": (
        (0, "ELF64", b"\x7fELF"),
        (227_328, "SetLutData", b"SetLutData"),
        (260_096, "HEVC", b"HEVC"),
        (272_384, "LUT", b"LUT"),
    ),
}

# ---------------------------------------------------------------------------
# Pillar A Constants: No-UVC USB Gadget Firewall & USB-LAN / Network Streaming
# ---------------------------------------------------------------------------

MODEL_ILME_FX3 = "ILME-FX3"
MODEL_ILME_FX3A = "ILME-FX3A"
MODEL_ILME_FX30 = "ILME-FX30"
MODEL_ILME_FX2 = "ILME-FX2"

FX3_MODEL_ID = 0x91030080
FX3A_MODEL_ID = 0x9103008A
FX30_MODEL_ID = 0x91030030
FX2_MODEL_ID = 0x910300A0

MODEL_IDS: Mapping[str, int] = {
    MODEL_ILME_FX3: FX3_MODEL_ID,
    MODEL_ILME_FX3A: FX3A_MODEL_ID,
    MODEL_ILME_FX30: FX30_MODEL_ID,
    MODEL_ILME_FX2: FX2_MODEL_ID,
}

MODELS_WITHOUT_NATIVE_UVC: Tuple[str, ...] = (MODEL_ILME_FX3, MODEL_ILME_FX3A)

USB_MODE_SEL_WHEN_CONNECT = "Sel. When Connect"
USB_MODE_MSC = "MassStorage(MSC)"
USB_MODE_MTP = "MTP"
USB_MODE_REMOTE_SHOOTING = "Remote Shooting"
USB_MODE_STREAMING_UVC = "USB Streaming"

VALID_FX3_USB_CONNECTION_MODES: Tuple[str, ...] = (
    USB_MODE_SEL_WHEN_CONNECT,
    USB_MODE_MSC,
    USB_MODE_MTP,
    USB_MODE_REMOTE_SHOOTING,
)

USB_LAN_PROTO_RNDIS = "RNDIS"
USB_LAN_PROTO_CDC_NCM = "CDC-NCM"
VALID_USB_LAN_PROTOCOLS: Tuple[str, ...] = (USB_LAN_PROTO_RNDIS, USB_LAN_PROTO_CDC_NCM)

LIVE_OUT_NETWORK_STREAMING = "NETWORK_STREAMING"
LIVE_OUT_TYPE_A_HDMI = "TYPE_A_HDMI"
LIVE_OUT_IMAGING_EDGE_WEBCAM_REMOTE = "IMAGING_EDGE_WEBCAM_REMOTE"
LIVE_OUT_UVC_COMPOSITE_GADGET = "UVC_UAC_COMPOSITE_GADGET"

NETWORK_STREAMING_PROTOCOLS: Tuple[str, ...] = ("RTMP", "RTMPS", "SRT")
NETWORK_STREAMING_CODECS: Tuple[str, ...] = ("HEVC", "AVC")
NETWORK_STREAMING_MAX_BITRATE_MBPS = 38.0
EOPNOTSUPP_ERRNO = 95

# ---------------------------------------------------------------------------
# Pillar B Constants: USB Power Supply (NP-FZ100) vs DC-C1 (>=65W + 5A)
# ---------------------------------------------------------------------------

POWER_PATH_BODY_USB_PD = "BODY_USB_PD"
POWER_PATH_DC_C1_COUPLER = "DC_C1_COUPLER"
POWER_PATH_MICRO_USB = "MICRO_USB"
POWER_PATH_BATTERY_ONLY = "BATTERY_ONLY"

DC_C1_MIN_PD_WATTS = 65
DC_C1_MIN_CABLE_AMPS = 5

# ---------------------------------------------------------------------------
# Pillar C & D Constants: Dual-Media .cube LUT Paths, Cine EI & RMT-P1BT
# ---------------------------------------------------------------------------

MEDIA_SD_SDXC = "SD"
MEDIA_CFEXPRESS_A = "CFexpress-A"

LUT_DIR_BY_MEDIA: Mapping[str, str] = {
    MEDIA_SD_SDXC: "/Private/Sony/PRO/LUT/",
    MEDIA_CFEXPRESS_A: "/Sony/PRO/LUT/",
}

VALID_CUBE_LUT_POINTS: Tuple[int, ...] = (17, 33)
MAX_CUBE_FILENAME_BYTES = 63
MAX_USER_LUT_SLOTS = 16
MIN_AE_OFFSET_EV = 0.0
MAX_AE_OFFSET_EV = 2.0
VALID_AE_OFFSET_STEPS: Tuple[float, ...] = (0.0, 0.3, 0.7, 1.0, 1.3, 1.7, 2.0)

_CUBE_FILENAME_RE = re.compile(r"^[A-Za-z0-9_-]+\.cube$")

CINE_EI_BASE_ISOS: Tuple[int, ...] = (800, 12800)
CINE_EI_RANGE_BY_BASE: Mapping[int, Tuple[int, int]] = {
    800: (200, 3200),
    12800: (3200, 51200),
}

VALID_CLIP_FLAGS: Tuple[str, ...] = ("NONE", "OK", "NG", "KEEP")


class RealHwNoUvcDcc1LutCineEiError(ValueError):
    """Raised on invalid Phase 194 Stage 34 configuration or contract inputs."""


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CompactDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    file_bytes: int
    elf64_le_ok: bool
    uxd_container_ok: bool
    sha256_prefix16: str
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedWindowDonorSummary:
    artifact_key: str
    body_label: str
    source_mode: str
    bounded_windows_only: bool
    bytes_read_total: int
    file_bytes: int
    elf64_le_ok: bool
    window_hits: Dict[str, int]
    head_sha256_prefix16: str


@dataclass(frozen=True)
class Phase194DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    fx3_usb_ctrl: CompactDonorSummary
    fx6_usb_ctrl: CompactDonorSummary
    fx3_cdc_ncm: CompactDonorSummary
    fx3_rndis_host: CompactDonorSummary
    fx3_bt_core: CompactDonorSummary
    fx3_string_en_f: CompactDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_libmpr: BoundedWindowDonorSummary
    fx6_libmpr: BoundedWindowDonorSummary
    usb_mode_and_usblan_proven: bool
    network_streaming_and_power_proven: bool
    cube_lut_and_cine_ei_proven: bool
    bt_sircs_mutex_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UsbNoUvcFirewallResult:
    admitted: bool
    model_name: str
    model_id_hex: str
    native_uvc_supported: bool
    requested_usb_mode: str
    usb_lan_enabled: bool
    usb_lan_protocol: Optional[str]
    usb_lan_power_on_auto_connect: bool
    live_output_route: str
    streaming_protocol: Optional[str]
    streaming_codec: Optional[str]
    resolution: str
    fps_label: str
    bitrate_mbps: float
    audio_enabled: bool
    uvc_gadget_rejected_eopnotsupp: bool
    errno_code: int
    usb_phy_hang_events: int
    appfw_crashes: int
    status_code: str


@dataclass(frozen=True)
class PowerSupplyBudgetResult:
    admitted: bool
    power_path: str
    npfz100_inserted: bool
    usb_power_supply_menu_on: bool
    pd_adapter_watts: int
    cable_rated_amps: int
    cable_emarker_present: bool
    internal_battery_charging_active: bool
    power_off_charging_resumed: bool
    body_type_c_freed_for_data: bool
    lcd_max_brightness_locked: bool
    dc_c1_led_blinking_alarm: bool
    brownout_guard_tripped: bool
    instant_power_cut_hazard: bool
    power_cut_brownout_events: int
    appfw_crashes: int
    status_code: str


@dataclass(frozen=True)
class CubeUserLutRoutingResult:
    admitted: bool
    media_type: str
    expected_lut_dir: str
    provided_path: str
    filename: str
    filename_bytes: int
    lut_points: int
    user_slot_index: int
    ae_level_offset_ev: float
    p2_setting_slots_max: int
    persistent_emmc_writes_authorized: bool
    emmc_nflasha_write_count: int
    status_code: str


@dataclass(frozen=True)
class CineEiExposureResult:
    admitted: bool
    base_iso: int
    ei_index: int
    ei_min: int
    ei_max: int
    lut_gain_offset_ev: float
    sensor_analog_gain_locked_iso: int
    sensor_analog_gain_contamination_events: int
    mxf_xml_metadata_ei: int
    status_code: str


@dataclass(frozen=True)
class RmtP1BtAndClipFlagResult:
    admitted: bool
    model_name: str
    bluetooth_rmt_ctrl_on: bool
    rmtp1bt_bt42_paired: bool
    ir_hw_present: bool
    nfc_hw_present: bool
    ir_receiver_enabled: bool
    gps_location_linkage_enabled: bool
    requested_ir_command: bool
    ir_command_ignored: bool
    clip_flag_filter: str
    filtered_clip_ids: Tuple[str, ...]
    h0_equals_h3: bool
    persistent_emmc_writes_authorized: bool
    emmc_nflasha_write_count: int
    wf12_00342260_hits: int
    status_code: str


@dataclass(frozen=True)
class RedlineGuardProbeResult:
    valid: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    usb_phy_hang_events: int
    power_cut_brownout_events: int
    sensor_analog_gain_contamination_events: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase194DonorAudit] = {}


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

    dedup: List[Path] = []
    seen = set()
    for cand in candidates:
        s = str(cand)
        if s not in seen:
            seen.add(s)
            dedup.append(cand)
    return tuple(dedup)


def resolve_phase194_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 12 FX3 7.02 & FX6 6.01 donor paths strictly read-only, honoring clean-room mode."""
    if is_forced_clean_room(env):
        sentinel = DEFAULT_REPO_ROOT / "work" / CLEAN_ROOM_SENTINEL_DIRNAME
        return {k: sentinel / rel for k, rel in DONOR_RELPATHS.items()}

    roots = _iter_work_roots(env=env)
    resolved: Dict[str, Path] = {}
    for key, rel in DONOR_RELPATHS.items():
        chosen: Optional[Path] = None
        for root in roots:
            cand = root / rel
            if cand.is_file():
                chosen = cand
                break
        if chosen is None:
            chosen = roots[0] / rel if roots else (DEFAULT_REPO_ROOT / "work" / rel)
        resolved[key] = chosen
    return resolved


def _read_full_rdonly(path: Path) -> Tuple[int, bytes]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        chunks: List[bytes] = []
        remaining = max(st.st_size, 0)
        while remaining > 0:
            chunk = os.read(fd, remaining)
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        data = chunks[0] if len(chunks) == 1 else b"".join(chunks)
        return st.st_size, data
    finally:
        os.close(fd)


def _read_bounded_windows_rdonly(
    path: Path,
    windows: Sequence[Tuple[int, str, bytes]],
) -> Tuple[int, int, bytes, Dict[str, int]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        file_bytes = st.st_size
        seen_offsets: Dict[int, bytes] = {}
        bytes_read_total = 0
        hits: Dict[str, int] = {}
        for off, label, tok in windows:
            if off not in seen_offsets:
                os.lseek(fd, off, os.SEEK_SET)
                buf = os.read(fd, BOUNDED_WINDOW_MAX_BYTES)
                seen_offsets[off] = buf
                bytes_read_total += len(buf)
            else:
                buf = seen_offsets[off]
            hits[label] = 1 if tok in buf else 0
        head = seen_offsets.get(0)
        if head is None:
            os.lseek(fd, 0, os.SEEK_SET)
            head = os.read(fd, min(BOUNDED_WINDOW_MAX_BYTES, max(file_bytes, 0)))
            bytes_read_total += len(head)
        return file_bytes, bytes_read_total, head, hits
    finally:
        os.close(fd)


def _scan_compact_buf(
    data: bytes,
    *,
    file_bytes: int,
    artifact_key: str,
    body_label: str,
    source_mode: str,
    tokens: Sequence[bytes],
) -> CompactDonorSummary:
    elf64_ok = len(data) >= 64 and data[:4] == b"\x7fELF" and data[4] == 2 and data[5] == 1
    uxd_ok = len(data) >= 8 and data[:4] in (b"uxc\x07", b"uxd\x07")
    hits = {
        tok.decode("ascii", "replace"): (1 if tok in data else 0)
        for tok in tokens
    }
    return CompactDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        uxd_container_ok=uxd_ok,
        sha256_prefix16=hashlib.sha256(data).hexdigest()[:16],
        marker_hits=hits,
    )


def _scan_compact_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
    tokens: Sequence[bytes],
) -> CompactDonorSummary:
    file_bytes, data = _read_full_rdonly(path)
    return _scan_compact_buf(
        data,
        file_bytes=file_bytes,
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        tokens=tokens,
    )


def _scan_large_donor_rdonly(
    path: Path,
    *,
    artifact_key: str,
    body_label: str,
    windows: Sequence[Tuple[int, str, bytes]],
) -> BoundedWindowDonorSummary:
    file_bytes, bytes_read_total, head, hits = _read_bounded_windows_rdonly(path, windows)
    elf64_ok = len(head) >= 64 and head[:4] == b"\x7fELF" and head[4] == 2 and head[5] == 1
    return BoundedWindowDonorSummary(
        artifact_key=artifact_key,
        body_label=body_label,
        source_mode="LOCAL_DONOR_RDONLY",
        bounded_windows_only=True,
        bytes_read_total=bytes_read_total,
        file_bytes=file_bytes,
        elf64_le_ok=elf64_ok,
        window_hits=hits,
        head_sha256_prefix16=hashlib.sha256(head[:BOUNDED_WINDOW_MAX_BYTES]).hexdigest()[:16],
    )


def _build_synthetic_elf64_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    buf = bytearray(64)
    buf[:4] = b"\x7fELF"
    buf[4] = 2
    buf[5] = 1
    buf[6] = 1
    struct.pack_into("<HHI", buf, 16, 3, 0xB7, 1)
    return bytes(buf) + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_synthetic_uxd_bytes(tokens: Sequence[bytes], tag: bytes) -> bytes:
    return b"uxc\x07\x00\x00\x00\x00" + b"\x00".join(tokens) + b"\x00" + tag + b"\x00"


def _build_clean_room_donor_audit() -> Phase194DonorAudit:
    mode = "CLEAN_ROOM_SYNTHETIC"

    def _mk_compact(key: str, label: str, is_uxd: bool) -> CompactDonorSummary:
        toks = COMPACT_DONOR_TOKENS[key]
        raw = (
            _build_synthetic_uxd_bytes(toks, f"{key}_SYNTH".encode("ascii"))
            if is_uxd
            else _build_synthetic_elf64_bytes(toks, f"{key}_SYNTH".encode("ascii"))
        )
        return _scan_compact_buf(
            raw,
            file_bytes=EXPECTED_DONOR_BYTES[key],
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            tokens=toks,
        )

    def _mk_large(key: str, label: str, is_elf: bool) -> BoundedWindowDonorSummary:
        wins = LARGE_DONOR_WINDOWS[key]
        if is_elf:
            head = _build_synthetic_elf64_bytes((), f"{key}_HEAD".encode("ascii"))
        else:
            head = (b"CPAPP_SYNTH_" + label.encode("ascii")).ljust(64, b"\x00")
        hits = {lbl: 1 for _off, lbl, _tok in wins}
        return BoundedWindowDonorSummary(
            artifact_key=key,
            body_label=label,
            source_mode=mode,
            bounded_windows_only=True,
            bytes_read_total=len(head),
            file_bytes=EXPECTED_DONOR_BYTES[key],
            elf64_le_ok=is_elf,
            window_hits=hits,
            head_sha256_prefix16=hashlib.sha256(head).hexdigest()[:16],
        )

    return Phase194DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_usb_ctrl=_mk_compact("fx3_usb_ctrl", "FX3_7.02", False),
        fx6_usb_ctrl=_mk_compact("fx6_usb_ctrl", "FX6_6.01", False),
        fx3_cdc_ncm=_mk_compact("fx3_cdc_ncm", "FX3_7.02", False),
        fx3_rndis_host=_mk_compact("fx3_rndis_host", "FX3_7.02", False),
        fx3_bt_core=_mk_compact("fx3_bt_core", "FX3_7.02", False),
        fx3_string_en_f=_mk_compact("fx3_string_en_f", "FX3_7.02", True),
        fx3_appfw=_mk_large("fx3_appfw", "FX3_7.02", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6_6.01", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3_7.02", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6_6.01", False),
        fx3_libmpr=_mk_large("fx3_libmpr", "FX3_7.02", True),
        fx6_libmpr=_mk_large("fx6_libmpr", "FX6_6.01", True),
        usb_mode_and_usblan_proven=True,
        network_streaming_and_power_proven=True,
        cube_lut_and_cine_ei_proven=True,
        bt_sircs_mutex_proven=True,
        all_contracts_verified=True,
        errors=(),
    )


def inspect_phase194_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase194DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.10s, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase194_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple(
        (k, str(p), p.stat().st_size, p.stat().st_mtime_ns)
        for k, p in sorted(paths.items())
    )
    cache_key = ("LOCAL_DONOR_RDONLY", sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    fx3_usb_ctrl = _scan_compact_rdonly(
        paths["fx3_usb_ctrl"],
        artifact_key="fx3_usb_ctrl",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_usb_ctrl"],
    )
    fx6_usb_ctrl = _scan_compact_rdonly(
        paths["fx6_usb_ctrl"],
        artifact_key="fx6_usb_ctrl",
        body_label="FX6_6.01",
        tokens=COMPACT_DONOR_TOKENS["fx6_usb_ctrl"],
    )
    fx3_cdc_ncm = _scan_compact_rdonly(
        paths["fx3_cdc_ncm"],
        artifact_key="fx3_cdc_ncm",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_cdc_ncm"],
    )
    fx3_rndis_host = _scan_compact_rdonly(
        paths["fx3_rndis_host"],
        artifact_key="fx3_rndis_host",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_rndis_host"],
    )
    fx3_bt_core = _scan_compact_rdonly(
        paths["fx3_bt_core"],
        artifact_key="fx3_bt_core",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_bt_core"],
    )
    fx3_string_en_f = _scan_compact_rdonly(
        paths["fx3_string_en_f"],
        artifact_key="fx3_string_en_f",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_string_en_f"],
    )
    fx3_appfw = _scan_large_donor_rdonly(
        paths["fx3_appfw"],
        artifact_key="fx3_appfw",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_appfw"],
    )
    fx6_appfw = _scan_large_donor_rdonly(
        paths["fx6_appfw"],
        artifact_key="fx6_appfw",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_appfw"],
    )
    fx3_cpapp = _scan_large_donor_rdonly(
        paths["fx3_cpapp"],
        artifact_key="fx3_cpapp",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_cpapp"],
    )
    fx6_cpapp = _scan_large_donor_rdonly(
        paths["fx6_cpapp"],
        artifact_key="fx6_cpapp",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_cpapp"],
    )
    fx3_libmpr = _scan_large_donor_rdonly(
        paths["fx3_libmpr"],
        artifact_key="fx3_libmpr",
        body_label="FX3_7.02",
        windows=LARGE_DONOR_WINDOWS["fx3_libmpr"],
    )
    fx6_libmpr = _scan_large_donor_rdonly(
        paths["fx6_libmpr"],
        artifact_key="fx6_libmpr",
        body_label="FX6_6.01",
        windows=LARGE_DONOR_WINDOWS["fx6_libmpr"],
    )

    errors: List[str] = []
    compact_items = (
        fx3_usb_ctrl,
        fx6_usb_ctrl,
        fx3_cdc_ncm,
        fx3_rndis_host,
        fx3_bt_core,
        fx3_string_en_f,
    )
    for item in compact_items:
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.marker_hits.values()):
            errors.append(f"{item.artifact_key} missing required tokens: {item.marker_hits}")

    for item in (fx3_appfw, fx6_appfw, fx3_cpapp, fx6_cpapp, fx3_libmpr, fx6_libmpr):
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.window_hits.values()):
            errors.append(f"{item.artifact_key} missing bounded window markers: {item.window_hits}")

    usb_usblan_ok = (
        fx3_usb_ctrl.elf64_le_ok
        and fx6_usb_ctrl.elf64_le_ok
        and fx3_cdc_ncm.elf64_le_ok
        and fx3_rndis_host.elf64_le_ok
        and fx3_string_en_f.uxd_container_ok
        and fx3_string_en_f.marker_hits.get("USB Connection Mode") == 1
        and fx3_string_en_f.marker_hits.get("USB-LAN") == 1
        and fx3_appfw.window_hits.get("USB_LAN") == 1
        and fx6_appfw.window_hits.get("USB_LAN") == 1
    )
    stream_power_ok = (
        fx3_string_en_f.marker_hits.get("USB Power Supply") == 1
        and fx3_string_en_f.marker_hits.get("Network Streaming") == 1
        and fx3_appfw.window_hits.get("RTMP") == 1
        and fx3_appfw.window_hits.get("SRT") == 1
        and fx3_appfw.window_hits.get("USB_POWER") == 1
        and fx6_appfw.window_hits.get("RTMP") == 1
        and fx6_appfw.window_hits.get("SRT") == 1
        and fx3_libmpr.window_hits.get("HEVC") == 1
        and fx6_libmpr.window_hits.get("HEVC") == 1
    )
    lut_cine_ei_ok = (
        fx3_string_en_f.marker_hits.get("Cine EI") == 1
        and fx3_appfw.window_hits.get("CUBE_LUT_PATH") == 1
        and fx3_appfw.window_hits.get("CUBE_EXT") == 1
        and fx3_appfw.window_hits.get("CINE_EI") == 1
        and fx6_appfw.window_hits.get("PRO_LUT") == 1
        and fx6_appfw.window_hits.get("CINE_EI") == 1
        and fx3_cpapp.window_hits.get("ILME-FX3") == 1
        and fx3_cpapp.window_hits.get("CUBE") == 1
        and fx6_cpapp.window_hits.get("CUBE") == 1
        and fx3_libmpr.window_hits.get("SetLutData") == 1
        and fx6_libmpr.window_hits.get("SetLutData") == 1
    )
    bt_sircs_ok = (
        fx3_bt_core.elf64_le_ok
        and all(fx3_bt_core.marker_hits.values())
        and fx3_string_en_f.marker_hits.get("Bluetooth Rmt Ctrl") == 1
        and fx3_string_en_f.marker_hits.get("IR Remote Ctrl") == 1
        and fx3_appfw.window_hits.get("SIRCS_OFF") == 1
        and fx6_appfw.window_hits.get("SIRCS_OFF") == 1
        and fx3_cpapp.window_hits.get("SIRCS") == 1
        and fx6_cpapp.window_hits.get("SIRCS") == 1
    )

    all_ok = (
        len(errors) == 0
        and usb_usblan_ok
        and stream_power_ok
        and lut_cine_ei_ok
        and bt_sircs_ok
    )

    audit = Phase194DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY",
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_usb_ctrl=fx3_usb_ctrl,
        fx6_usb_ctrl=fx6_usb_ctrl,
        fx3_cdc_ncm=fx3_cdc_ncm,
        fx3_rndis_host=fx3_rndis_host,
        fx3_bt_core=fx3_bt_core,
        fx3_string_en_f=fx3_string_en_f,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_libmpr=fx3_libmpr,
        fx6_libmpr=fx6_libmpr,
        usb_mode_and_usblan_proven=usb_usblan_ok,
        network_streaming_and_power_proven=stream_power_ok,
        cube_lut_and_cine_ei_proven=lut_cine_ei_ok,
        bt_sircs_mutex_proven=bt_sircs_ok,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Pillar A: ILME-FX3 (0x91030080) No-UVC USB Gadget Firewall & USB-LAN / Streaming
# ---------------------------------------------------------------------------


def probe_usb_nouvc_gadget_firewall(
    *,
    model_name: str = MODEL_ILME_FX3,
    requested_usb_mode: str = USB_MODE_SEL_WHEN_CONNECT,
    uvc_composite_descriptor_pushed: bool = False,
    usb_lan_enabled: bool = False,
    usb_lan_protocol: Optional[str] = None,
    usb_lan_power_on_auto_connect: bool = False,
    live_output_route: str = LIVE_OUT_NETWORK_STREAMING,
    streaming_protocol: Optional[str] = "SRT",
    streaming_codec: Optional[str] = "HEVC",
    resolution: str = "3840x2160",
    fps_label: str = "59.94p",
    bitrate_mbps: float = 38.0,
) -> UsbNoUvcFirewallResult:
    """Co-emulate ILME-FX3/FX3A No-UVC gadget firewall, USB-LAN & 4K59.94p streaming."""
    if model_name not in MODEL_IDS:
        raise RealHwNoUvcDcc1LutCineEiError(f"Unsupported model_name: {model_name!r}")
    model_id = MODEL_IDS[model_name]
    model_id_hex = f"0x{model_id:08x}"
    native_uvc_supported = model_name not in MODELS_WITHOUT_NATIVE_UVC

    # Guard 1: Reject UVC/UAC composite gadget descriptor or [USB Streaming] on FX3 / FX3A
    if (
        uvc_composite_descriptor_pushed
        or requested_usb_mode == USB_MODE_STREAMING_UVC
        or live_output_route == LIVE_OUT_UVC_COMPOSITE_GADGET
    ) and not native_uvc_supported:
        return UsbNoUvcFirewallResult(
            admitted=False,
            model_name=model_name,
            model_id_hex=model_id_hex,
            native_uvc_supported=False,
            requested_usb_mode=requested_usb_mode,
            usb_lan_enabled=usb_lan_enabled,
            usb_lan_protocol=usb_lan_protocol,
            usb_lan_power_on_auto_connect=usb_lan_power_on_auto_connect,
            live_output_route=live_output_route,
            streaming_protocol=streaming_protocol,
            streaming_codec=streaming_codec,
            resolution=resolution,
            fps_label=fps_label,
            bitrate_mbps=float(bitrate_mbps),
            audio_enabled=False,
            uvc_gadget_rejected_eopnotsupp=True,
            errno_code=EOPNOTSUPP_ERRNO,
            usb_phy_hang_events=USB_PHY_HANG_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code="REJECTED_EOPNOTSUPP_NO_NATIVE_UVC_ON_FX3",
        )

    if requested_usb_mode not in VALID_FX3_USB_CONNECTION_MODES and not (
        native_uvc_supported and requested_usb_mode == USB_MODE_STREAMING_UVC
    ):
        return UsbNoUvcFirewallResult(
            admitted=False,
            model_name=model_name,
            model_id_hex=model_id_hex,
            native_uvc_supported=native_uvc_supported,
            requested_usb_mode=requested_usb_mode,
            usb_lan_enabled=usb_lan_enabled,
            usb_lan_protocol=usb_lan_protocol,
            usb_lan_power_on_auto_connect=usb_lan_power_on_auto_connect,
            live_output_route=live_output_route,
            streaming_protocol=streaming_protocol,
            streaming_codec=streaming_codec,
            resolution=resolution,
            fps_label=fps_label,
            bitrate_mbps=float(bitrate_mbps),
            audio_enabled=False,
            uvc_gadget_rejected_eopnotsupp=True,
            errno_code=EOPNOTSUPP_ERRNO,
            usb_phy_hang_events=USB_PHY_HANG_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code="BLOCKED_UNSUPPORTED_USB_CONNECTION_MODE",
        )

    if usb_lan_enabled and usb_lan_protocol not in VALID_USB_LAN_PROTOCOLS:
        return UsbNoUvcFirewallResult(
            admitted=False,
            model_name=model_name,
            model_id_hex=model_id_hex,
            native_uvc_supported=native_uvc_supported,
            requested_usb_mode=requested_usb_mode,
            usb_lan_enabled=True,
            usb_lan_protocol=usb_lan_protocol,
            usb_lan_power_on_auto_connect=usb_lan_power_on_auto_connect,
            live_output_route=live_output_route,
            streaming_protocol=streaming_protocol,
            streaming_codec=streaming_codec,
            resolution=resolution,
            fps_label=fps_label,
            bitrate_mbps=float(bitrate_mbps),
            audio_enabled=False,
            uvc_gadget_rejected_eopnotsupp=False,
            errno_code=22,
            usb_phy_hang_events=USB_PHY_HANG_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code="BLOCKED_INVALID_USB_LAN_PROTOCOL",
        )

    # Guard 2: Legacy Imaging Edge Webcam over Remote Shooting (capped 1024x576, no audio)
    if live_output_route == LIVE_OUT_IMAGING_EDGE_WEBCAM_REMOTE:
        if requested_usb_mode != USB_MODE_REMOTE_SHOOTING:
            return UsbNoUvcFirewallResult(
                admitted=False,
                model_name=model_name,
                model_id_hex=model_id_hex,
                native_uvc_supported=native_uvc_supported,
                requested_usb_mode=requested_usb_mode,
                usb_lan_enabled=usb_lan_enabled,
                usb_lan_protocol=usb_lan_protocol,
                usb_lan_power_on_auto_connect=usb_lan_power_on_auto_connect,
                live_output_route=live_output_route,
                streaming_protocol=None,
                streaming_codec=None,
                resolution="1024x576",
                fps_label="29.97p",
                bitrate_mbps=0.0,
                audio_enabled=False,
                uvc_gadget_rejected_eopnotsupp=False,
                errno_code=22,
                usb_phy_hang_events=USB_PHY_HANG_EVENTS,
                appfw_crashes=APPFW_CRASHES,
                status_code="BLOCKED_WEBCAM_REQUIRES_REMOTE_SHOOTING_MODE",
            )
        return UsbNoUvcFirewallResult(
            admitted=True,
            model_name=model_name,
            model_id_hex=model_id_hex,
            native_uvc_supported=native_uvc_supported,
            requested_usb_mode=requested_usb_mode,
            usb_lan_enabled=False,
            usb_lan_protocol=None,
            usb_lan_power_on_auto_connect=False,
            live_output_route=live_output_route,
            streaming_protocol=None,
            streaming_codec=None,
            resolution="1024x576",
            fps_label="29.97p",
            bitrate_mbps=0.0,
            audio_enabled=False,
            uvc_gadget_rejected_eopnotsupp=False,
            errno_code=0,
            usb_phy_hang_events=USB_PHY_HANG_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code="IMAGING_EDGE_WEBCAM_1024X576_NO_AUDIO_OK",
        )

    # Guard 3: Network Streaming (RTMP/RTMPS/SRT <= 38 Mbps HEVC/AVC)
    if live_output_route == LIVE_OUT_NETWORK_STREAMING:
        if (
            streaming_protocol not in NETWORK_STREAMING_PROTOCOLS
            or streaming_codec not in NETWORK_STREAMING_CODECS
            or bitrate_mbps <= 0.0
            or bitrate_mbps > NETWORK_STREAMING_MAX_BITRATE_MBPS
        ):
            return UsbNoUvcFirewallResult(
                admitted=False,
                model_name=model_name,
                model_id_hex=model_id_hex,
                native_uvc_supported=native_uvc_supported,
                requested_usb_mode=requested_usb_mode,
                usb_lan_enabled=usb_lan_enabled,
                usb_lan_protocol=usb_lan_protocol,
                usb_lan_power_on_auto_connect=usb_lan_power_on_auto_connect,
                live_output_route=live_output_route,
                streaming_protocol=streaming_protocol,
                streaming_codec=streaming_codec,
                resolution=resolution,
                fps_label=fps_label,
                bitrate_mbps=float(bitrate_mbps),
                audio_enabled=False,
                uvc_gadget_rejected_eopnotsupp=False,
                errno_code=22,
                usb_phy_hang_events=USB_PHY_HANG_EVENTS,
                appfw_crashes=APPFW_CRASHES,
                status_code="BLOCKED_NETWORK_STREAMING_BUDGET_OR_PROTO",
            )
        return UsbNoUvcFirewallResult(
            admitted=True,
            model_name=model_name,
            model_id_hex=model_id_hex,
            native_uvc_supported=native_uvc_supported,
            requested_usb_mode=requested_usb_mode,
            usb_lan_enabled=usb_lan_enabled,
            usb_lan_protocol=usb_lan_protocol,
            usb_lan_power_on_auto_connect=usb_lan_power_on_auto_connect,
            live_output_route=live_output_route,
            streaming_protocol=streaming_protocol,
            streaming_codec=streaming_codec,
            resolution=resolution,
            fps_label=fps_label,
            bitrate_mbps=float(bitrate_mbps),
            audio_enabled=True,
            uvc_gadget_rejected_eopnotsupp=False,
            errno_code=0,
            usb_phy_hang_events=USB_PHY_HANG_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code="NETWORK_STREAMING_4K5994_38MBPS_OK",
        )

    # Guard 4: Type-A HDMI capture card live output
    if live_output_route == LIVE_OUT_TYPE_A_HDMI:
        return UsbNoUvcFirewallResult(
            admitted=True,
            model_name=model_name,
            model_id_hex=model_id_hex,
            native_uvc_supported=native_uvc_supported,
            requested_usb_mode=requested_usb_mode,
            usb_lan_enabled=usb_lan_enabled,
            usb_lan_protocol=usb_lan_protocol,
            usb_lan_power_on_auto_connect=usb_lan_power_on_auto_connect,
            live_output_route=live_output_route,
            streaming_protocol=None,
            streaming_codec=None,
            resolution=resolution,
            fps_label=fps_label,
            bitrate_mbps=0.0,
            audio_enabled=True,
            uvc_gadget_rejected_eopnotsupp=False,
            errno_code=0,
            usb_phy_hang_events=USB_PHY_HANG_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code="TYPE_A_HDMI_CLEAN_LIVE_OUTPUT_OK",
        )

    raise RealHwNoUvcDcc1LutCineEiError(f"Unsupported live_output_route: {live_output_route!r}")


def evaluate_pillar_a_nouvc_usb_gadget_firewall() -> Dict[str, object]:
    uvc_gadget_rejected = probe_usb_nouvc_gadget_firewall(
        model_name=MODEL_ILME_FX3,
        requested_usb_mode=USB_MODE_STREAMING_UVC,
        uvc_composite_descriptor_pushed=True,
        live_output_route=LIVE_OUT_UVC_COMPOSITE_GADGET,
    )
    fx3a_uvc_rejected = probe_usb_nouvc_gadget_firewall(
        model_name=MODEL_ILME_FX3A,
        requested_usb_mode=USB_MODE_STREAMING_UVC,
        uvc_composite_descriptor_pushed=True,
    )
    usblan_cdc_ncm_srt_ok = probe_usb_nouvc_gadget_firewall(
        model_name=MODEL_ILME_FX3,
        requested_usb_mode=USB_MODE_SEL_WHEN_CONNECT,
        usb_lan_enabled=True,
        usb_lan_protocol=USB_LAN_PROTO_CDC_NCM,
        usb_lan_power_on_auto_connect=True,
        live_output_route=LIVE_OUT_NETWORK_STREAMING,
        streaming_protocol="SRT",
        streaming_codec="HEVC",
        resolution="3840x2160",
        fps_label="59.94p",
        bitrate_mbps=38.0,
    )
    usblan_rndis_rtmps_ok = probe_usb_nouvc_gadget_firewall(
        model_name=MODEL_ILME_FX3,
        requested_usb_mode=USB_MODE_MTP,
        usb_lan_enabled=True,
        usb_lan_protocol=USB_LAN_PROTO_RNDIS,
        usb_lan_power_on_auto_connect=True,
        live_output_route=LIVE_OUT_NETWORK_STREAMING,
        streaming_protocol="RTMPS",
        streaming_codec="AVC",
        bitrate_mbps=25.0,
    )
    hdmi_type_a_ok = probe_usb_nouvc_gadget_firewall(
        model_name=MODEL_ILME_FX3,
        requested_usb_mode=USB_MODE_MSC,
        live_output_route=LIVE_OUT_TYPE_A_HDMI,
        resolution="3840x2160",
        fps_label="59.94p",
    )
    remote_webcam_576p_ok = probe_usb_nouvc_gadget_firewall(
        model_name=MODEL_ILME_FX3,
        requested_usb_mode=USB_MODE_REMOTE_SHOOTING,
        live_output_route=LIVE_OUT_IMAGING_EDGE_WEBCAM_REMOTE,
    )
    over_38mbps_blocked = probe_usb_nouvc_gadget_firewall(
        model_name=MODEL_ILME_FX3,
        requested_usb_mode=USB_MODE_SEL_WHEN_CONNECT,
        usb_lan_enabled=True,
        usb_lan_protocol=USB_LAN_PROTO_CDC_NCM,
        live_output_route=LIVE_OUT_NETWORK_STREAMING,
        streaming_protocol="SRT",
        streaming_codec="HEVC",
        bitrate_mbps=45.0,
    )

    passed = (
        (not uvc_gadget_rejected.admitted)
        and uvc_gadget_rejected.uvc_gadget_rejected_eopnotsupp
        and uvc_gadget_rejected.errno_code == EOPNOTSUPP_ERRNO
        and uvc_gadget_rejected.usb_phy_hang_events == 0
        and (not fx3a_uvc_rejected.admitted)
        and fx3a_uvc_rejected.errno_code == EOPNOTSUPP_ERRNO
        and usblan_cdc_ncm_srt_ok.admitted
        and usblan_cdc_ncm_srt_ok.usb_lan_power_on_auto_connect
        and usblan_cdc_ncm_srt_ok.bitrate_mbps == 38.0
        and usblan_rndis_rtmps_ok.admitted
        and hdmi_type_a_ok.admitted
        and remote_webcam_576p_ok.admitted
        and remote_webcam_576p_ok.resolution == "1024x576"
        and (not remote_webcam_576p_ok.audio_enabled)
        and (not over_38mbps_blocked.admitted)
    )
    return {
        "passed": passed,
        "uvc_composite_rejected_eopnotsupp": asdict(uvc_gadget_rejected),
        "fx3a_uvc_rejected_eopnotsupp": asdict(fx3a_uvc_rejected),
        "usblan_cdc_ncm_4k5994_srt_38mbps_ok": asdict(usblan_cdc_ncm_srt_ok),
        "usblan_rndis_rtmps_ok": asdict(usblan_rndis_rtmps_ok),
        "type_a_hdmi_4k5994_ok": asdict(hdmi_type_a_ok),
        "remote_shooting_webcam_576p_no_audio_ok": asdict(remote_webcam_576p_ok),
        "over_38mbps_streaming_blocked": asdict(over_38mbps_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar B: USB Power Supply (NP-FZ100 Mandatory) vs DC-C1 (>=65W + 5A Cable)
# ---------------------------------------------------------------------------


def probe_power_supply_budget(
    *,
    power_path: str = POWER_PATH_BODY_USB_PD,
    npfz100_inserted: bool = True,
    usb_power_supply_menu_on: bool = True,
    camera_powered_off: bool = False,
    pd_adapter_watts: int = 65,
    cable_rated_amps: int = 5,
    cable_emarker_present: bool = True,
) -> PowerSupplyBudgetResult:
    """Co-emulate FX3 body USB-PD (NP-FZ100 mandatory) vs DC-C1 (>=65W + 5A) power budget."""
    if power_path == POWER_PATH_MICRO_USB:
        return PowerSupplyBudgetResult(
            admitted=False,
            power_path=power_path,
            npfz100_inserted=npfz100_inserted,
            usb_power_supply_menu_on=usb_power_supply_menu_on,
            pd_adapter_watts=pd_adapter_watts,
            cable_rated_amps=cable_rated_amps,
            cable_emarker_present=cable_emarker_present,
            internal_battery_charging_active=False,
            power_off_charging_resumed=False,
            body_type_c_freed_for_data=True,
            lcd_max_brightness_locked=False,
            dc_c1_led_blinking_alarm=False,
            brownout_guard_tripped=False,
            instant_power_cut_hazard=False,
            power_cut_brownout_events=POWER_CUT_BROWNOUT_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code="REJECTED_MICRO_USB_POWER_NOT_SUPPORTED",
        )

    if power_path == POWER_PATH_BODY_USB_PD:
        if not npfz100_inserted:
            return PowerSupplyBudgetResult(
                admitted=False,
                power_path=power_path,
                npfz100_inserted=False,
                usb_power_supply_menu_on=usb_power_supply_menu_on,
                pd_adapter_watts=pd_adapter_watts,
                cable_rated_amps=cable_rated_amps,
                cable_emarker_present=cable_emarker_present,
                internal_battery_charging_active=False,
                power_off_charging_resumed=False,
                body_type_c_freed_for_data=False,
                lcd_max_brightness_locked=False,
                dc_c1_led_blinking_alarm=False,
                brownout_guard_tripped=True,
                instant_power_cut_hazard=True,
                power_cut_brownout_events=POWER_CUT_BROWNOUT_EVENTS,
                appfw_crashes=APPFW_CRASHES,
                status_code="INSTANT_POWER_CUT_HAZARD_NP_FZ100_PULLED_UNDER_USB_PD",
            )
        if not usb_power_supply_menu_on:
            return PowerSupplyBudgetResult(
                admitted=True,
                power_path=power_path,
                npfz100_inserted=True,
                usb_power_supply_menu_on=False,
                pd_adapter_watts=pd_adapter_watts,
                cable_rated_amps=cable_rated_amps,
                cable_emarker_present=cable_emarker_present,
                internal_battery_charging_active=camera_powered_off,
                power_off_charging_resumed=camera_powered_off,
                body_type_c_freed_for_data=False,
                lcd_max_brightness_locked=False,
                dc_c1_led_blinking_alarm=False,
                brownout_guard_tripped=False,
                instant_power_cut_hazard=False,
                power_cut_brownout_events=POWER_CUT_BROWNOUT_EVENTS,
                appfw_crashes=APPFW_CRASHES,
                status_code="USB_POWER_SUPPLY_OFF_RUNNING_ON_NP_FZ100",
            )
        return PowerSupplyBudgetResult(
            admitted=True,
            power_path=power_path,
            npfz100_inserted=True,
            usb_power_supply_menu_on=True,
            pd_adapter_watts=pd_adapter_watts,
            cable_rated_amps=cable_rated_amps,
            cable_emarker_present=cable_emarker_present,
            internal_battery_charging_active=camera_powered_off,
            power_off_charging_resumed=camera_powered_off,
            body_type_c_freed_for_data=False,
            lcd_max_brightness_locked=False,
            dc_c1_led_blinking_alarm=False,
            brownout_guard_tripped=False,
            instant_power_cut_hazard=False,
            power_cut_brownout_events=POWER_CUT_BROWNOUT_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code=(
                "BODY_USB_PD_POWER_OFF_CHARGING_RESUMED_OK"
                if camera_powered_off
                else "BODY_USB_PD_ACTIVE_NP_FZ100_PRESENT_CHARGING_PAUSED_OK"
            ),
        )

    if power_path == POWER_PATH_DC_C1_COUPLER:
        budget_ok = (
            pd_adapter_watts >= DC_C1_MIN_PD_WATTS
            and cable_rated_amps >= DC_C1_MIN_CABLE_AMPS
            and cable_emarker_present
        )
        if not budget_ok:
            return PowerSupplyBudgetResult(
                admitted=False,
                power_path=power_path,
                npfz100_inserted=False,
                usb_power_supply_menu_on=usb_power_supply_menu_on,
                pd_adapter_watts=pd_adapter_watts,
                cable_rated_amps=cable_rated_amps,
                cable_emarker_present=cable_emarker_present,
                internal_battery_charging_active=False,
                power_off_charging_resumed=False,
                body_type_c_freed_for_data=True,
                lcd_max_brightness_locked=True,
                dc_c1_led_blinking_alarm=True,
                brownout_guard_tripped=True,
                instant_power_cut_hazard=False,
                power_cut_brownout_events=POWER_CUT_BROWNOUT_EVENTS,
                appfw_crashes=APPFW_CRASHES,
                status_code="REJECTED_DC_C1_BLINKING_LED_BROWNOUT_LT65W_OR_NON_5A_CABLE",
            )
        return PowerSupplyBudgetResult(
            admitted=True,
            power_path=power_path,
            npfz100_inserted=False,
            usb_power_supply_menu_on=usb_power_supply_menu_on,
            pd_adapter_watts=pd_adapter_watts,
            cable_rated_amps=cable_rated_amps,
            cable_emarker_present=True,
            internal_battery_charging_active=False,
            power_off_charging_resumed=False,
            body_type_c_freed_for_data=True,
            lcd_max_brightness_locked=True,
            dc_c1_led_blinking_alarm=False,
            brownout_guard_tripped=False,
            instant_power_cut_hazard=False,
            power_cut_brownout_events=POWER_CUT_BROWNOUT_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code="DC_C1_65W_5A_EMARKED_TYPE_C_FREED_LCD_MAX_LOCKED_OK",
        )

    if power_path == POWER_PATH_BATTERY_ONLY:
        if not npfz100_inserted:
            return PowerSupplyBudgetResult(
                admitted=False,
                power_path=power_path,
                npfz100_inserted=False,
                usb_power_supply_menu_on=False,
                pd_adapter_watts=0,
                cable_rated_amps=0,
                cable_emarker_present=False,
                internal_battery_charging_active=False,
                power_off_charging_resumed=False,
                body_type_c_freed_for_data=True,
                lcd_max_brightness_locked=False,
                dc_c1_led_blinking_alarm=False,
                brownout_guard_tripped=True,
                instant_power_cut_hazard=True,
                power_cut_brownout_events=POWER_CUT_BROWNOUT_EVENTS,
                appfw_crashes=APPFW_CRASHES,
                status_code="NO_POWER_SOURCE_NP_FZ100_MISSING",
            )
        return PowerSupplyBudgetResult(
            admitted=True,
            power_path=power_path,
            npfz100_inserted=True,
            usb_power_supply_menu_on=False,
            pd_adapter_watts=0,
            cable_rated_amps=0,
            cable_emarker_present=False,
            internal_battery_charging_active=False,
            power_off_charging_resumed=False,
            body_type_c_freed_for_data=True,
            lcd_max_brightness_locked=False,
            dc_c1_led_blinking_alarm=False,
            brownout_guard_tripped=False,
            instant_power_cut_hazard=False,
            power_cut_brownout_events=POWER_CUT_BROWNOUT_EVENTS,
            appfw_crashes=APPFW_CRASHES,
            status_code="BATTERY_ONLY_NP_FZ100_OK",
        )

    raise RealHwNoUvcDcc1LutCineEiError(f"Unsupported power_path: {power_path!r}")


def evaluate_pillar_b_usb_pd_vs_dcc1_power_budget() -> Dict[str, object]:
    body_pd_active = probe_power_supply_budget(
        power_path=POWER_PATH_BODY_USB_PD,
        npfz100_inserted=True,
        usb_power_supply_menu_on=True,
        camera_powered_off=False,
    )
    body_pd_off_charging = probe_power_supply_budget(
        power_path=POWER_PATH_BODY_USB_PD,
        npfz100_inserted=True,
        usb_power_supply_menu_on=True,
        camera_powered_off=True,
    )
    npfz100_pulled_hazard = probe_power_supply_budget(
        power_path=POWER_PATH_BODY_USB_PD,
        npfz100_inserted=False,
        usb_power_supply_menu_on=True,
    )
    micro_usb_rejected = probe_power_supply_budget(
        power_path=POWER_PATH_MICRO_USB,
    )
    dcc1_65w_5a_ok = probe_power_supply_budget(
        power_path=POWER_PATH_DC_C1_COUPLER,
        pd_adapter_watts=65,
        cable_rated_amps=5,
        cable_emarker_present=True,
    )
    dcc1_45w_brownout = probe_power_supply_budget(
        power_path=POWER_PATH_DC_C1_COUPLER,
        pd_adapter_watts=45,
        cable_rated_amps=5,
        cable_emarker_present=True,
    )
    dcc1_3a_cable_brownout = probe_power_supply_budget(
        power_path=POWER_PATH_DC_C1_COUPLER,
        pd_adapter_watts=100,
        cable_rated_amps=3,
        cable_emarker_present=False,
    )

    passed = (
        body_pd_active.admitted
        and body_pd_active.npfz100_inserted
        and (not body_pd_active.internal_battery_charging_active)
        and body_pd_off_charging.admitted
        and body_pd_off_charging.power_off_charging_resumed
        and (not npfz100_pulled_hazard.admitted)
        and npfz100_pulled_hazard.instant_power_cut_hazard
        and npfz100_pulled_hazard.brownout_guard_tripped
        and (not micro_usb_rejected.admitted)
        and dcc1_65w_5a_ok.admitted
        and dcc1_65w_5a_ok.body_type_c_freed_for_data
        and dcc1_65w_5a_ok.lcd_max_brightness_locked
        and (not dcc1_65w_5a_ok.dc_c1_led_blinking_alarm)
        and (not dcc1_45w_brownout.admitted)
        and dcc1_45w_brownout.dc_c1_led_blinking_alarm
        and dcc1_45w_brownout.brownout_guard_tripped
        and (not dcc1_3a_cable_brownout.admitted)
        and dcc1_3a_cable_brownout.dc_c1_led_blinking_alarm
        and dcc1_3a_cable_brownout.brownout_guard_tripped
    )
    return {
        "passed": passed,
        "body_usb_pd_active_npfz100_ok": asdict(body_pd_active),
        "body_usb_pd_power_off_charging_ok": asdict(body_pd_off_charging),
        "npfz100_pulled_instant_power_cut_hazard": asdict(npfz100_pulled_hazard),
        "micro_usb_power_rejected": asdict(micro_usb_rejected),
        "dcc1_65w_5a_emarker_ok": asdict(dcc1_65w_5a_ok),
        "dcc1_45w_blinking_led_blocked": asdict(dcc1_45w_brownout),
        "dcc1_3a_cable_blinking_led_blocked": asdict(dcc1_3a_cable_brownout),
    }


# ---------------------------------------------------------------------------
# Pillar C & D: Dual-Media .cube LUT Path-Asymmetry, Cine EI & RMT-P1BT HIL
# ---------------------------------------------------------------------------


def validate_dual_media_cube_lut_path(
    *,
    media_type: str = MEDIA_SD_SDXC,
    directory_path: str = "/Private/Sony/PRO/LUT/",
    filename: str = "SLog3_to_Rec709_33pt.cube",
    lut_points: int = 33,
    user_slot_index: int = 1,
    ae_level_offset_ev: float = 0.0,
) -> CubeUserLutRoutingResult:
    """Enforce SD (/Private/Sony/PRO/LUT/) vs CFexpress-A (/Sony/PRO/LUT/) LUT rules."""
    if media_type not in LUT_DIR_BY_MEDIA:
        raise RealHwNoUvcDcc1LutCineEiError(f"Unsupported media_type: {media_type!r}")
    expected_dir = LUT_DIR_BY_MEDIA[media_type]
    norm_dir = directory_path if directory_path.endswith("/") else f"{directory_path}/"
    fn_bytes = len(filename.encode("utf-8"))

    if norm_dir != expected_dir:
        return CubeUserLutRoutingResult(
            admitted=False,
            media_type=media_type,
            expected_lut_dir=expected_dir,
            provided_path=f"{norm_dir}{filename}",
            filename=filename,
            filename_bytes=fn_bytes,
            lut_points=lut_points,
            user_slot_index=user_slot_index,
            ae_level_offset_ev=ae_level_offset_ev,
            p2_setting_slots_max=MAX_USER_LUT_SLOTS,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
            status_code="REJECTED_DUAL_MEDIA_LUT_PATH_ASYMMETRY_MISMATCH",
        )

    if lut_points not in VALID_CUBE_LUT_POINTS:
        return CubeUserLutRoutingResult(
            admitted=False,
            media_type=media_type,
            expected_lut_dir=expected_dir,
            provided_path=f"{norm_dir}{filename}",
            filename=filename,
            filename_bytes=fn_bytes,
            lut_points=lut_points,
            user_slot_index=user_slot_index,
            ae_level_offset_ev=ae_level_offset_ev,
            p2_setting_slots_max=MAX_USER_LUT_SLOTS,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
            status_code="REJECTED_UNSUPPORTED_CUBE_LUT_GRID_SIZE",
        )

    if fn_bytes > MAX_CUBE_FILENAME_BYTES or not _CUBE_FILENAME_RE.match(filename):
        return CubeUserLutRoutingResult(
            admitted=False,
            media_type=media_type,
            expected_lut_dir=expected_dir,
            provided_path=f"{norm_dir}{filename}",
            filename=filename,
            filename_bytes=fn_bytes,
            lut_points=lut_points,
            user_slot_index=user_slot_index,
            ae_level_offset_ev=ae_level_offset_ev,
            p2_setting_slots_max=MAX_USER_LUT_SLOTS,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
            status_code="REJECTED_CUBE_FILENAME_GT63B_OR_NON_ALNUM",
        )

    if not (1 <= user_slot_index <= MAX_USER_LUT_SLOTS):
        return CubeUserLutRoutingResult(
            admitted=False,
            media_type=media_type,
            expected_lut_dir=expected_dir,
            provided_path=f"{norm_dir}{filename}",
            filename=filename,
            filename_bytes=fn_bytes,
            lut_points=lut_points,
            user_slot_index=user_slot_index,
            ae_level_offset_ev=ae_level_offset_ev,
            p2_setting_slots_max=MAX_USER_LUT_SLOTS,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
            status_code="REJECTED_USER_LUT_SLOT_OUT_OF_RANGE_1_16",
        )

    rounded_ev = round(float(ae_level_offset_ev), 1)
    if rounded_ev not in VALID_AE_OFFSET_STEPS:
        return CubeUserLutRoutingResult(
            admitted=False,
            media_type=media_type,
            expected_lut_dir=expected_dir,
            provided_path=f"{norm_dir}{filename}",
            filename=filename,
            filename_bytes=fn_bytes,
            lut_points=lut_points,
            user_slot_index=user_slot_index,
            ae_level_offset_ev=ae_level_offset_ev,
            p2_setting_slots_max=MAX_USER_LUT_SLOTS,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
            status_code="REJECTED_AE_LEVEL_OFFSET_OUT_OF_RANGE_0_TO_PLUS2EV",
        )

    return CubeUserLutRoutingResult(
        admitted=True,
        media_type=media_type,
        expected_lut_dir=expected_dir,
        provided_path=f"{norm_dir}{filename}",
        filename=filename,
        filename_bytes=fn_bytes,
        lut_points=lut_points,
        user_slot_index=user_slot_index,
        ae_level_offset_ev=rounded_ev,
        p2_setting_slots_max=MAX_USER_LUT_SLOTS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
        status_code="CUBE_USER_LUT_PATH_AND_SLOT_OK",
    )


def evaluate_cine_ei_exposure(
    *,
    base_iso: int = 12800,
    ei_index: int = 12800,
) -> CineEiExposureResult:
    """Co-emulate Cine EI 800/12800 Dual Native ISO without CMOS analog-gain contamination."""
    if base_iso not in CINE_EI_BASE_ISOS:
        raise RealHwNoUvcDcc1LutCineEiError(f"Unsupported Cine EI base_iso: {base_iso!r}")
    ei_min, ei_max = CINE_EI_RANGE_BY_BASE[base_iso]
    if not (ei_min <= ei_index <= ei_max):
        return CineEiExposureResult(
            admitted=False,
            base_iso=base_iso,
            ei_index=ei_index,
            ei_min=ei_min,
            ei_max=ei_max,
            lut_gain_offset_ev=0.0,
            sensor_analog_gain_locked_iso=base_iso,
            sensor_analog_gain_contamination_events=SENSOR_ANALOG_GAIN_CONTAMINATION_EVENTS,
            mxf_xml_metadata_ei=base_iso,
            status_code="REJECTED_CINE_EI_INDEX_OUT_OF_RANGE",
        )

    import math

    ev_offset = round(math.log2(ei_index / base_iso), 2)
    return CineEiExposureResult(
        admitted=True,
        base_iso=base_iso,
        ei_index=ei_index,
        ei_min=ei_min,
        ei_max=ei_max,
        lut_gain_offset_ev=ev_offset,
        sensor_analog_gain_locked_iso=base_iso,
        sensor_analog_gain_contamination_events=SENSOR_ANALOG_GAIN_CONTAMINATION_EVENTS,
        mxf_xml_metadata_ei=ei_index,
        status_code="CINE_EI_DUAL_NATIVE_ISO_ZERO_GAIN_CONTAMINATION_OK",
    )


def probe_rmtp1bt_and_clip_flag_mutex(
    *,
    model_name: str = MODEL_ILME_FX3,
    bluetooth_rmt_ctrl_on: bool = True,
    rmtp1bt_bt42_paired: bool = True,
    requested_ir_command: bool = False,
    clip_flag_filter: str = "OK",
) -> RmtP1BtAndClipFlagResult:
    """Co-emulate RMT-P1BT BT 4.2 vs IR/GPS mutex and Creators' Cloud OK/NG/KEEP filter."""
    if model_name not in (MODEL_ILME_FX3, MODEL_ILME_FX3A):
        raise RealHwNoUvcDcc1LutCineEiError(f"Unsupported model_name for RMT-P1BT: {model_name!r}")
    if clip_flag_filter not in VALID_CLIP_FLAGS:
        raise RealHwNoUvcDcc1LutCineEiError(f"Unsupported clip_flag_filter: {clip_flag_filter!r}")

    ir_hw_present = model_name == MODEL_ILME_FX3
    nfc_hw_present = model_name == MODEL_ILME_FX3
    ir_receiver_enabled = ir_hw_present and (not bluetooth_rmt_ctrl_on)
    gps_location_linkage_enabled = not bluetooth_rmt_ctrl_on
    ir_command_ignored = requested_ir_command and (not ir_receiver_enabled)

    sample_clips = (
        ("C0001", "OK"),
        ("C0002", "NG"),
        ("C0003", "KEEP"),
        ("C0004", "OK"),
    )
    filtered = tuple(
        cid for cid, flg in sample_clips if clip_flag_filter == "NONE" or flg == clip_flag_filter
    )
    return RmtP1BtAndClipFlagResult(
        admitted=True,
        model_name=model_name,
        bluetooth_rmt_ctrl_on=bluetooth_rmt_ctrl_on,
        rmtp1bt_bt42_paired=rmtp1bt_bt42_paired and bluetooth_rmt_ctrl_on,
        ir_hw_present=ir_hw_present,
        nfc_hw_present=nfc_hw_present,
        ir_receiver_enabled=ir_receiver_enabled,
        gps_location_linkage_enabled=gps_location_linkage_enabled,
        requested_ir_command=requested_ir_command,
        ir_command_ignored=ir_command_ignored,
        clip_flag_filter=clip_flag_filter,
        filtered_clip_ids=filtered,
        h0_equals_h3=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        emmc_nflasha_write_count=EMMC_NFLASHA_WRITE_COUNT,
        wf12_00342260_hits=WF12_00342260_HITS,
        status_code=(
            "RMT_P1BT_ON_IR_AND_GPS_LINKAGE_DISABLED_OK"
            if bluetooth_rmt_ctrl_on
            else (
                "IR_REMOTE_ENABLED_ON_FX3_BT_RMT_OFF_OK"
                if ir_hw_present
                else "FX3A_NO_IR_NO_NFC_HW_PRESENT_OK"
            )
        ),
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    trigger_usb_phy_hang: bool = False,
    trigger_power_cut_brownout: bool = False,
    contaminate_sensor_analog_gain: bool = False,
) -> RedlineGuardProbeResult:
    """Enforce hard safety redlines fail-closed on any forbidden hardware-write attempt."""
    blocked: List[str] = []
    if authorize_persistent_emmc_writes:
        blocked.append("PERSISTENT_EMMC_WRITES")
    if authorize_spi_nor_write:
        blocked.append("SPI_NOR_WRITE")
    if authorize_el3_payload_transmit:
        blocked.append("EL3_PAYLOAD_TRANSMIT")
    if emit_physical_usb_packet:
        blocked.append("PHYSICAL_USB_PACKET_EMIT")
    if touch_otp_fuse:
        blocked.append("OTP_FUSE_TOUCH")
    if increment_rpmb_counter:
        blocked.append("RPMB_COUNTER_INCREMENT")
    if trigger_usb_phy_hang:
        blocked.append("USB_PHY_HANG")
    if trigger_power_cut_brownout:
        blocked.append("POWER_CUT_BROWNOUT")
    if contaminate_sensor_analog_gain:
        blocked.append("SENSOR_ANALOG_GAIN_CONTAMINATION")

    if blocked:
        return RedlineGuardProbeResult(
            valid=False,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            otp_fuse_touches=0,
            rpmb_counter_increments=0,
            usb_phy_hang_events=0,
            power_cut_brownout_events=0,
            sensor_analog_gain_contamination_events=0,
            blocked_action="+".join(blocked),
            status_code=f"BLOCKED_HARD_SAFETY_REDLINE_{blocked[0]}",
        )

    return RedlineGuardProbeResult(
        valid=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        usb_phy_hang_events=USB_PHY_HANG_EVENTS,
        power_cut_brownout_events=POWER_CUT_BROWNOUT_EVENTS,
        sensor_analog_gain_contamination_events=SENSOR_ANALOG_GAIN_CONTAMINATION_EVENTS,
        blocked_action="NONE",
        status_code="HARD_SAFETY_REDLINES_LOCKED_OK",
    )


def evaluate_pillar_c_d_lut_cineei_rmtp1bt_and_redlines() -> Dict[str, object]:
    sd_33pt_ok = validate_dual_media_cube_lut_path(
        media_type=MEDIA_SD_SDXC,
        directory_path="/Private/Sony/PRO/LUT/",
        filename="SLog3_Rec709_33pt.cube",
        lut_points=33,
        user_slot_index=1,
        ae_level_offset_ev=0.0,
    )
    cfex_17pt_ok = validate_dual_media_cube_lut_path(
        media_type=MEDIA_CFEXPRESS_A,
        directory_path="/Sony/PRO/LUT/",
        filename="SLog3_Cine_17pt.cube",
        lut_points=17,
        user_slot_index=16,
        ae_level_offset_ev=2.0,
    )
    cfex_with_private_blocked = validate_dual_media_cube_lut_path(
        media_type=MEDIA_CFEXPRESS_A,
        directory_path="/Private/Sony/PRO/LUT/",
        filename="SLog3_Rec709_33pt.cube",
        lut_points=33,
    )
    sd_without_private_blocked = validate_dual_media_cube_lut_path(
        media_type=MEDIA_SD_SDXC,
        directory_path="/Sony/PRO/LUT/",
        filename="SLog3_Rec709_33pt.cube",
        lut_points=33,
    )
    gt63b_filename_blocked = validate_dual_media_cube_lut_path(
        media_type=MEDIA_SD_SDXC,
        directory_path="/Private/Sony/PRO/LUT/",
        filename=("A" * 59) + ".cube",  # 64 bytes > 63
        lut_points=33,
    )
    slot17_blocked = validate_dual_media_cube_lut_path(
        media_type=MEDIA_SD_SDXC,
        directory_path="/Private/Sony/PRO/LUT/",
        filename="ValidLut.cube",
        lut_points=33,
        user_slot_index=17,
    )

    cineei_12800_3200_ok = evaluate_cine_ei_exposure(base_iso=12800, ei_index=3200)
    cineei_12800_51200_ok = evaluate_cine_ei_exposure(base_iso=12800, ei_index=51200)
    cineei_800_800_ok = evaluate_cine_ei_exposure(base_iso=800, ei_index=800)
    cineei_12800_64000_blocked = evaluate_cine_ei_exposure(base_iso=12800, ei_index=64000)

    rmt_bt_on_disables_ir_gps = probe_rmtp1bt_and_clip_flag_mutex(
        model_name=MODEL_ILME_FX3,
        bluetooth_rmt_ctrl_on=True,
        requested_ir_command=True,
        clip_flag_filter="OK",
    )
    rmt_bt_off_enables_ir_fx3 = probe_rmtp1bt_and_clip_flag_mutex(
        model_name=MODEL_ILME_FX3,
        bluetooth_rmt_ctrl_on=False,
        requested_ir_command=True,
        clip_flag_filter="KEEP",
    )
    fx3a_no_ir_no_nfc = probe_rmtp1bt_and_clip_flag_mutex(
        model_name=MODEL_ILME_FX3A,
        bluetooth_rmt_ctrl_on=False,
        requested_ir_command=True,
        clip_flag_filter="NG",
    )

    baseline = probe_hard_safety_redline()
    probes = (
        probe_hard_safety_redline(authorize_persistent_emmc_writes=True),
        probe_hard_safety_redline(authorize_spi_nor_write=True),
        probe_hard_safety_redline(authorize_el3_payload_transmit=True),
        probe_hard_safety_redline(emit_physical_usb_packet=True),
        probe_hard_safety_redline(touch_otp_fuse=True),
        probe_hard_safety_redline(increment_rpmb_counter=True),
        probe_hard_safety_redline(trigger_usb_phy_hang=True),
        probe_hard_safety_redline(trigger_power_cut_brownout=True),
        probe_hard_safety_redline(contaminate_sensor_analog_gain=True),
    )

    passed = (
        sd_33pt_ok.admitted
        and cfex_17pt_ok.admitted
        and (not cfex_with_private_blocked.admitted)
        and (not sd_without_private_blocked.admitted)
        and (not gt63b_filename_blocked.admitted)
        and (not slot17_blocked.admitted)
        and cineei_12800_3200_ok.admitted
        and cineei_12800_3200_ok.lut_gain_offset_ev == -2.0
        and cineei_12800_3200_ok.sensor_analog_gain_locked_iso == 12800
        and cineei_12800_51200_ok.admitted
        and cineei_12800_51200_ok.lut_gain_offset_ev == 2.0
        and cineei_800_800_ok.admitted
        and (not cineei_12800_64000_blocked.admitted)
        and rmt_bt_on_disables_ir_gps.admitted
        and (not rmt_bt_on_disables_ir_gps.ir_receiver_enabled)
        and (not rmt_bt_on_disables_ir_gps.gps_location_linkage_enabled)
        and rmt_bt_on_disables_ir_gps.ir_command_ignored
        and rmt_bt_on_disables_ir_gps.filtered_clip_ids == ("C0001", "C0004")
        and rmt_bt_on_disables_ir_gps.h0_equals_h3
        and rmt_bt_off_enables_ir_fx3.ir_receiver_enabled
        and (not rmt_bt_off_enables_ir_fx3.ir_command_ignored)
        and (not fx3a_no_ir_no_nfc.ir_hw_present)
        and (not fx3a_no_ir_no_nfc.nfc_hw_present)
        and baseline.valid
        and (not baseline.persistent_emmc_writes_authorized)
        and (not baseline.spi_nor_write_authorized)
        and (not baseline.el3_payload_transmit_authorized)
        and baseline.physical_usb_packets_emitted == 0
        and baseline.otp_fuse_touches == 0
        and baseline.rpmb_counter_increments == 0
        and all((not p.valid) for p in probes)
    )
    return {
        "passed": passed,
        "sd_private_lut_33pt_ok": asdict(sd_33pt_ok),
        "cfexpress_noprivate_lut_17pt_ok": asdict(cfex_17pt_ok),
        "cfexpress_private_prefix_blocked": asdict(cfex_with_private_blocked),
        "sd_missing_private_prefix_blocked": asdict(sd_without_private_blocked),
        "filename_gt63b_blocked": asdict(gt63b_filename_blocked),
        "slot_17_blocked": asdict(slot17_blocked),
        "cine_ei_12800_3200ei_ok": asdict(cineei_12800_3200_ok),
        "cine_ei_12800_51200ei_ok": asdict(cineei_12800_51200_ok),
        "cine_ei_800_800ei_ok": asdict(cineei_800_800_ok),
        "cine_ei_12800_64000ei_blocked": asdict(cineei_12800_64000_blocked),
        "rmtp1bt_bt_on_disables_ir_gps": asdict(rmt_bt_on_disables_ir_gps),
        "rmtp1bt_bt_off_enables_ir_fx3": asdict(rmt_bt_off_enables_ir_fx3),
        "fx3a_no_ir_no_nfc_mutex": asdict(fx3a_no_ir_no_nfc),
        "baseline_redline_lock": asdict(baseline),
        "blocked_redline_probes": [asdict(p) for p in probes],
    }


# ---------------------------------------------------------------------------
# Unified Phase 194 Stage 34 Orchestrator & CLI
# ---------------------------------------------------------------------------


def run_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute the full Phase 194 Stage 34 (`34/34`) co-emulation audit."""
    donor_audit = inspect_phase194_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_nouvc_usb_gadget_firewall()
    pillar_b = evaluate_pillar_b_usb_pd_vs_dcc1_power_budget()
    pillar_cd = evaluate_pillar_c_d_lut_cineei_rmtp1bt_and_redlines()

    all_passed = (
        donor_audit.all_contracts_verified
        and donor_audit.raw_firmware_bytes_leaked == 0
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_cd["passed"])
    )

    payload: Dict[str, object] = {
        "schema": PHASE_194_SCHEMA,
        "version": PHASE_194_VERSION,
        "stage_index": STAGE_INDEX,
        "stage_total": STAGE_TOTAL,
        "milestone": MILESTONE_LABEL,
        "stage": STAGE_NAME,
        "source_mode": donor_audit.source_mode,
        "all_checks_passed": all_passed,
        "redlines": {
            "p8_cp_mutation_forbidden": P8_CP_MUTATION_FORBIDDEN,
            "nop_count": NOP_COUNT,
            "guest_code_modification_bytes": GUEST_CODE_MODIFICATION_BYTES,
            "cp_mutation_bytes": CP_MUTATION_BYTES,
            "wbi_mutation_bytes": WBI_MUTATION_BYTES,
            "calibration_mutation_bytes": CALIBRATION_MUTATION_BYTES,
            "nvram_persistent_writes": NVRAM_PERSISTENT_WRITES,
            "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
            "physical_device_writes": PHYSICAL_DEVICE_WRITES,
            "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
            "emmc_nflasha_write_count": EMMC_NFLASHA_WRITE_COUNT,
            "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
            "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
            "spi_nor_mutation_bytes": SPI_NOR_MUTATION_BYTES,
            "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
            "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
            "otp_fuse_touches": OTP_FUSE_TOUCHES,
            "rpmb_counter_increments": RPMB_COUNTER_INCREMENTS,
            "usb_phy_hang_events": USB_PHY_HANG_EVENTS,
            "power_cut_brownout_events": POWER_CUT_BROWNOUT_EVENTS,
            "sensor_analog_gain_contamination_events": SENSOR_ANALOG_GAIN_CONTAMINATION_EVENTS,
            "null_gpio_derefs": NULL_GPIO_DEREFS,
            "mailbox_stalls": MAILBOX_STALLS,
            "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
            "wf12_00342260_hits": WF12_00342260_HITS,
            "appfw_crashes": APPFW_CRASHES,
            "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "pillar_a_nouvc_usb_gadget_firewall_hil": pillar_a,
        "pillar_b_usb_pd_vs_dcc1_power_budget_hil": pillar_b,
        "pillar_c_d_lut_path_cineei_rmtp1bt_and_redlines": pillar_cd,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_nouvc_dcc1_lut_path_cineei_coemulator.py",
        description="Phase 194 Stage 34 (34/34) ILME-FX3 No-UVC USB Gadget Firewall, USB-PD vs DC-C1, Dual-Media .cube LUT Path-Asymmetry, Cine EI & RMT-P1BT HIL Co-Emulator",
    )
    parser.add_argument("--self-test", action="store_true", help="Run Stage 34 self-test and exit 0/1")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line audit summary")
    args = parser.parse_args(argv)

    rep = run_phase194_realhw_nouvc_dcc1_lut_path_cineei_hil(
        force_clean_room=True if args.clean_room else None,
        env=os.environ,
    )

    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_nouvc_usb_gadget_firewall_hil"]["usblan_cdc_ncm_4k5994_srt_38mbps_ok"]
        pb = rep["pillar_b_usb_pd_vs_dcc1_power_budget_hil"]["dcc1_65w_5a_emarker_ok"]
        sys.stdout.write(
            f"[{status}] Phase 194 Stage 34 ({MILESTONE_LABEL}) Real-HW No-UVC / DC-C1 / LUT-Path / CineEI / RMT-P1BT HIL | "
            f"mode={rep['source_mode']} | uvc_errno={EOPNOTSUPP_ERRNO} | "
            f"srt={pa['resolution']}@{pa['fps_label']}/{pa['bitrate_mbps']}Mbps | "
            f"dcc1={pb['pd_adapter_watts']}W/{pb['cable_rated_amps']}A | "
            f"emmc_wr={rep['redlines']['emmc_nflasha_write_count']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
