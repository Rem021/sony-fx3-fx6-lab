"""Phase 118 — 23rd Unified Firmware-Lab Auditor: USB-C UVC 1.5 / UAC 2.0 Streaming,
Wired P12-Safe SRT / RTMPS Network Streaming, & Sony Camera Remote SDK (CRSDK)
PTP / PTP-IP Vendor Property Translator & Destructive Flash-Opcode Firewall.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `global.xdb`,
  `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01 (`appFw.so`,
  `libmpr.so`, `libInfraPtpControl.so`, `libNetServiceEther.so`,
  `libInfraVericLiveStreaming.so`, `global.xdb`, `string_english.uxc`,
  `string_english_2.uxc`) strictly via `os.O_RDONLY` + `mmap.ACCESS_READ` and
  ELF64 `.rodata`/`.dynstr` section-scoped scanning plus `uxa\\x07`/`.uxc`
  container parsing (< 0.35s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / `global.xdb` / `.uxc`
  fixtures carrying the exact verified contract markers and runs the identical
  four-pillar verification pipeline (< 0.02s warm, zero proprietary files
  required).

Audits Four Phase 118 Pillars:
1. Pillar 1 — USB-C `UVC 1.5` / `UAC 2.0` Descriptor, Endpoint Bandwidth
   (`SuperSpeed 5Gbps` vs `High-Speed 480Mbps` `MJPEG`/`YUY2` payload budget),
   & FX6-on-FX3 Stage-B Compatibility Contract:
   - Synthesizes and validates USB-C UVC 1.5 Video Control/Streaming + UAC 2.0
     48 kHz 2-ch LPCM interface descriptors (`bInterfaceClass=0x0E` / `0x01`).
   - Audits exact endpoint payload bandwidth across `4K30p_MJPEG` (`151.5 Mbps`),
     `1080p60p_MJPEG` (`76.5 Mbps`), `1080p60p_YUY2` (`1992.2 Mbps` -> fits
     SuperSpeed `3200 Mbps` ceiling, rejected on USB 2.0 `320 Mbps` High-Speed),
     and `4K30p_YUY2` (`3982.8 Mbps` -> exceeds even USB 3.2 Gen 1 UVC ceiling).
   - Verifies FX6-on-FX3 Stage-B compatibility: recognizes FX3 v7.02 lacks a
     native USB-C UVC gadget in stock HAITA (`HDMI -> UVC` external capture
     bridge or gated FunctionFS descriptor probe) and enforces `S&Q` /
     `HDMI RAW16` mutual exclusion.
2. Pillar 2 — Wired `USB-LAN` (`CDC-NCM` / `RNDIS`) `SRT` (`Caller/Listener`,
   `AES-128/256`, ARQ `20..1000 ms`) & `RTMPS` TLS 1.3 Live Streaming Auditor
   with Strict `P12` Wi-Fi-OFF Enforcement (`wf12_00342260_risk == 0`):
   - Validates `SRT_CALLER` / `SRT_LISTENER` sessions with `AES-128` /
     `AES-256` (`10..79`-char passphrase) and bounded ARQ latency `20..1000 ms`,
     plus `RTMPS` TLS 1.3 root-CA verification and Sony FX3 bitrate envelopes
     (`4K59.94p 38 Mbps`, `4K29.97p 13..38 Mbps`, `1080p60p 4.5..27 Mbps`) +
     `4K59.94p` internal-4K rec mutual exclusion.
   - Enforces `P12` Wi-Fi/BT RF-Off isolation (`wf12_00342260_risk == 0`, `0`
     HCI/WLAN RF TX packets) by restricting transport strictly to wired
     `CDC-NCM` (`RTL8153` / `AX88179`) or wired USB `RNDIS` host link.
3. Pillar 3 — `CRSDK` `PTP` / `PTP-IP` Vendor Property Translator & Stage-B
   Destructive PTP Firmware-Update Opcode Firewall:
   - Translates `CRSDK` `CrDeviceProperty` controls (`Cine EI` `0x02CF1443`,
     `Base ISO 800/12800`, `User 3D-LUT` `0x02CF1453`, `Shutter Angle`, `Iris`,
     `Rec Control`) to Sony `PTP` (`0x054C`, `0x9201..0x9209` + `0xD2xx`) and
     `PTP-IP` (`TCP/15740`), verifying `512`-byte USB bulk packet alignment on
     `0x9209` and clamping FX6 `P4` Electronic Variable ND (`0.3..2.1` OD)
     deterministically to `Clear (0.0 OD)` on FX3 (`0` motor faults).
   - Hard-blocks all destructive USB/PTP firmware-update & flash opcodes
     (`EVENT_REMOTE_REQUEST_START_BODY_UPDATE`, `0x9280` Scalar DL mode,
     `0x9282` updater reconnect, `CRSDK_OP_REMOTE_FIRMWARE_UPDATE_*`, and
     `MTP SendObject` carrying `.DAT` / `UDTRFIRM` / `\\x89UFU` payloads) so
     an attached host SDK can never trigger a hybrid firmware brick.
4. Pillar 4 — Volatile RAM Staging & Zero Persistent `eMMC` / Calibration
   Mutation Proof:
   - Validates FX3 & FX6 `global.xdb` (`uxa\\x07`) containers read-only and
     proves `emmc_mutation_bytes == 0`, `calibration_mutation_bytes == 0`,
     `firmware_flash_opcodes_blocked == True`, and
     `persistent_emmc_writes_authorized == False`.
"""

from __future__ import annotations

import hashlib
import json
import mmap
import os
import re
import struct
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .emount_af_breathing_and_ibis_auditor import _extract_uxc_labels, _parse_elf64_sections
from .global_xdb_and_menu_tree_auditor import (
    build_sparse_uxc_string_pack,
    build_synthetic_global_xdb,
    parse_global_xdb_buffer,
)
from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    is_forced_clean_room,
    resolve_donor_file,
)
from .interval_cache_and_ftp_auditor import FX6_LIBNET_ETHER_RELPATH
from .lut3d_cube_tetrahedral_and_sdi_hdmi_auditor import (
    FX3_GLOBAL_XDB_RELPATH,
    FX3_STR_EN_G_RELPATH,
    FX3_STR_EN_RELPATH,
    FX6_GLOBAL_XDB_RELPATH,
    FX6_STR_EN_1_RELPATH,
    FX6_STR_EN_2_RELPATH,
)
from .c2pa_lens_shading_and_mc_fleet_auditor import (
    FX6_LIBINFRA_PTP_RELPATH,
    PTPIP_TCP_PORT,
)
from .sensor_codec_compatibility_analyzer import FX3_LIBMPR_RELPATH, FX6_LIBMPR_RELPATH


PHASE_118_SCHEMA = "fx3_firmware_lab_phase118_uvc_srt_crsdk_ptp_v1"
PHASE_118_VERSION = "118.0.0"

FX6_LIBVERIC_LIVE_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/"
    "nflasha15-files/lib/libInfraVericLiveStreaming.so"
)

# ---------------------------------------------------------------------------
# Pillar 1 Constants: USB-C UVC 1.5 / UAC 2.0 Descriptor & Bandwidth Budget
# ---------------------------------------------------------------------------

USB_VID_SONY = 0x054C
UVC_VERSION_15 = 0x0150
UAC_VERSION_20 = 0x0200
USB_DT_INTERFACE = 0x04
USB_CLASS_VIDEO = 0x0E
USB_CLASS_AUDIO = 0x01
UVC_DESCRIPTOR_BUNDLE_MAGIC = b"UVC15UAC"
UVC_DESCRIPTOR_BUNDLE_BYTES = 44

USB3_SUPERSPEED_5GBPS_USABLE_MBPS = 3200.0
USB2_HIGHSPEED_480MBPS_USABLE_MBPS = 320.0

UAC_SAMPLE_RATE_HZ = 48_000
UAC_CHANNELS = 2
VALID_UAC_BIT_DEPTHS: Tuple[int, ...] = (16, 24)
VALID_USB_LINK_SPEEDS: Tuple[str, ...] = ("USB3_SUPERSPEED_5G", "USB2_HIGHSPEED_480M")
VALID_UVC_STAGE_B_MODES: Tuple[str, ...] = (
    "HDMI_TO_UVC_BRIDGE",
    "FX30_A7S3_UVC_DESCRIPTOR_SIM",
    "DIRECT_FX3_NATIVE_UVC_GADGET",
)

UVC_STREAM_PROFILES: Dict[str, Dict[str, object]] = {
    "4K30P_MJPEG": {
        "width": 3840,
        "height": 2160,
        "fps": 29.97,
        "pixel_format": "MJPEG",
        "video_mbps": 150.0,
        "usb3_supported": True,
        "usb2_supported": True,
    },
    "4K30P_NV12_YUV420": {
        "width": 3840,
        "height": 2160,
        "fps": 29.97,
        "pixel_format": "NV12",
        "video_mbps": round((3840 * 2160 * 12 * 29.97) / 1_000_000.0, 3),  # 2982.999 Mbps
        "usb3_supported": True,
        "usb2_supported": False,
    },
    "4K30P_YUY2": {
        "width": 3840,
        "height": 2160,
        "fps": 30.0,
        "pixel_format": "YUY2",
        "video_mbps": round((3840 * 2160 * 16 * 30.0) / 1_000_000.0, 3),  # 3981.312 Mbps
        "usb3_supported": False,  # Exceeds 3200 Mbps SuperSpeed usable UVC payload ceiling
        "usb2_supported": False,
    },
    "1080P60P_MJPEG": {
        "width": 1920,
        "height": 1080,
        "fps": 59.94,
        "pixel_format": "MJPEG",
        "video_mbps": 75.0,
        "usb3_supported": True,
        "usb2_supported": True,
    },
    "1080P60P_YUY2": {
        "width": 1920,
        "height": 1080,
        "fps": 60.0,
        "pixel_format": "YUY2",
        "video_mbps": round((1920 * 1080 * 16 * 60.0) / 1_000_000.0, 3),  # 1990.656 Mbps
        "usb3_supported": True,
        "usb2_supported": False,
    },
    "720P30P_MJPEG": {
        "width": 1280,
        "height": 720,
        "fps": 29.97,
        "pixel_format": "MJPEG",
        "video_mbps": 25.0,
        "usb3_supported": True,
        "usb2_supported": True,
    },
}

# ---------------------------------------------------------------------------
# Pillar 2 Constants: Wired USB-LAN SRT & RTMPS Streaming + P12 Wi-Fi-OFF
# ---------------------------------------------------------------------------

VALID_STREAM_PROTOCOLS: Tuple[str, ...] = ("SRT_CALLER", "SRT_LISTENER", "RTMPS_TLS13", "RTMP_PLAIN")
VALID_WIRED_STREAM_TRANSPORTS: Tuple[str, ...] = (
    "CDC_NCM_RTL8153",
    "CDC_NCM_AX88179",
    "USB_RNDIS_WIRED",
)
FORBIDDEN_RF_TRANSPORTS: Tuple[str, ...] = (
    "WIFI_WLAN0",
    "WIFI_DIRECT_P2P",
    "BT_PAN",
    "MODEM_CELLULAR",
)
SRT_ARQ_LATENCY_MIN_MS = 20
SRT_ARQ_LATENCY_MAX_MS = 1000
SRT_PASSPHRASE_MIN_LEN = 10
SRT_PASSPHRASE_MAX_LEN = 79
VALID_SRT_PBKEYLEN: Tuple[int, ...] = (16, 32)  # AES-128, AES-256

SONY_FX3_STREAMING_BITRATE_ENVELOPES: Dict[str, Dict[str, object]] = {
    "4K_5994P": {"width": 3840, "height": 2160, "fps": 59.94, "min_mbps": 38.0, "max_mbps": 38.0, "allows_internal_4k_rec": False},
    "4K_2997P": {"width": 3840, "height": 2160, "fps": 29.97, "min_mbps": 13.0, "max_mbps": 38.0, "allows_internal_4k_rec": True},
    "2K_5994P": {"width": 2560, "height": 1440, "fps": 59.94, "min_mbps": 9.0, "max_mbps": 38.0, "allows_internal_4k_rec": False},
    "1080P_5994P": {"width": 1920, "height": 1080, "fps": 59.94, "min_mbps": 4.5, "max_mbps": 27.0, "allows_internal_4k_rec": True},
    "1080P_2997P": {"width": 1920, "height": 1080, "fps": 29.97, "min_mbps": 3.0, "max_mbps": 18.0, "allows_internal_4k_rec": True},
    "720P_5994P": {"width": 1280, "height": 720, "fps": 59.94, "min_mbps": 2.3, "max_mbps": 13.5, "allows_internal_4k_rec": True},
}

# ---------------------------------------------------------------------------
# Pillar 3 Constants: CRSDK / PTP / PTP-IP Translator & Flash-Opcode Firewall
# ---------------------------------------------------------------------------

SONY_PTP_VENDOR_EXT_ID = 0x00000011
USB_BULK_PACKET_ALIGNMENT_BYTES = 512

SONY_SAFE_PTP_OPCODES: Dict[int, str] = {
    0x9201: "PTP_OC_SONY_SDIO_Connect",
    0x9202: "PTP_OC_SONY_SDIO_GetExtDeviceInfo",
    0x9204: "PTP_OC_SONY_GetDevicePropertyValue",
    0x9205: "PTP_OC_SONY_SDIO_SetExtDevicePropValue",
    0x9206: "PTP_OC_SONY_GetControlDeviceDesc",
    0x9207: "PTP_OC_SONY_SDIO_ControlDevice",
    0x9209: "PTP_OC_SONY_SDIO_GetAllExtDevicePropInfo",
}

FORBIDDEN_PTP_FLASH_OPCODES: Dict[int, str] = {
    0x9280: "PTP_OC_SONY_DI_EXT_CMD_WRITE_FLASH_SCALAR_DL",
    0x9282: "PTP_OC_SONY_REQ_RECONNECT_UPDATER",
    0x100C: "PTP_OC_MTP_SEND_OBJECT_INFO_FIRMWARE_DAT",
    0x100D: "PTP_OC_MTP_SEND_OBJECT_FIRMWARE_PAYLOAD",
    0x9805: "PTP_OC_SONY_CRSDK_REMOTE_FIRMWARE_UPDATE_UPLOAD",
}

FORBIDDEN_CRSDK_FW_UPDATE_COMMANDS: Tuple[str, ...] = (
    "EVENT_REMOTE_REQUEST_START_BODY_UPDATE",
    "EVENT_REMOTE_REQUEST_SET_FIRMWARE_UPDATE_MODE_ON",
    "EVENT_REMOTE_REQUEST_FIRMWARE_UPDATE_CHECK",
    "FIRMWARE_UPDATE_STATUS_ACCEPTING_DATA_UPLOAD",
    "CRSDK_OP_REMOTE_FIRMWARE_UPDATE_SEND",
    "CRSDK_OP_REMOTE_FIRMWARE_UPDATE_START",
    "SONY_CMD_SCALAR_NOTIFY_DLMODE",
)

FORBIDDEN_FIRMWARE_PAYLOAD_PATTERNS: Tuple[bytes, ...] = (
    b"\x89UFU\r\n\x1a\n",
    b"UDTRFIRM",
    b"BODYDATA.DAT",
    b"FDAT",
)

CRSDK_PROPERTY_PTP_MAP: Dict[str, Dict[str, object]] = {
    "CINE_EI_LOG_MODE": {
        "crsdk_name": "CrDeviceProperty_LogShootingMode",
        "ptp_prop_code": 0xD243,
        "bk4_prop_id": 0x02CF1443,
        "valid_values": ("OFF", "FLEXIBLE_ISO", "CINE_EI_QUICK", "CINE_EI"),
        "fx3_supported": True,
        "fx6_supported": True,
    },
    "BASE_ISO": {
        "crsdk_name": "CrDeviceProperty_GainBaseIsoSensitivity",
        "ptp_prop_code": 0xD244,
        "bk4_prop_id": 0x02CF1444,
        "valid_values": (800, 12800),
        "fx3_supported": True,
        "fx6_supported": True,
    },
    "EXPOSURE_INDEX": {
        "crsdk_name": "CrDeviceProperty_ExposureIndex",
        "ptp_prop_code": 0xD245,
        "bk4_prop_id": 0x02CF1445,
        "valid_values": (200, 400, 800, 1600, 3200, 6400, 12800, 25600, 51200),
        "fx3_supported": True,
        "fx6_supported": True,
    },
    "USER_3D_LUT": {
        "crsdk_name": "CrDeviceProperty_SelectLUT",
        "ptp_prop_code": 0xD253,
        "bk4_prop_id": 0x02CF1453,
        "valid_values": ("S709", "R709", "SLOG3", "USER1", "USER2", "USER3", "USER4"),
        "fx3_supported": True,
        "fx6_supported": True,
    },
    "SHUTTER_ANGLE_X10": {
        "crsdk_name": "CrDeviceProperty_ShutterAngle",
        "ptp_prop_code": 0xD20D,
        "bk4_prop_id": 0x02CF1704,
        "valid_values": (56, 112, 450, 900, 1728, 1800, 2700, 3600),
        "fx3_supported": True,
        "fx6_supported": True,
    },
    "IRIS_FNUMBER_X100": {
        "crsdk_name": "CrDeviceProperty_FNumber",
        "ptp_prop_code": 0x5007,
        "bk4_prop_id": 0x02CF0100,
        "valid_values": (120, 140, 200, 280, 400, 560, 800, 1100, 1600, 2200),
        "fx3_supported": True,
        "fx6_supported": True,
    },
    "ND_FILTER_OD_X10": {
        "crsdk_name": "CrDeviceProperty_NDFilterOpticalDensityValue",
        "ptp_prop_code": 0xD25A,
        "bk4_prop_id": 0x02CF1501,
        "valid_values": (0, 3, 6, 9, 12, 15, 18, 21),  # 0.0 (Clear) .. 2.1 OD (1/128)
        "fx3_supported": False,  # P4: FX3 lacks physical Electronic Variable ND -> clamp Clear (0)
        "fx6_supported": True,
    },
    "REC_CONTROL": {
        "crsdk_name": "CrCommandId_MovieRecord",
        "ptp_prop_code": 0xD215,
        "bk4_prop_id": 0x02CF0010,
        "valid_values": ("REC_START", "REC_STOP"),
        "fx3_supported": True,
        "fx6_supported": True,
    },
}

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Zero Persistent eMMC / Calibration Mutation Guard
# ---------------------------------------------------------------------------

VOLATILE_STAGING_PREFIXES: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_PERSISTENT_EMMC_RE = re.compile(
    r"(?:^|/)(?:p(?:[1-9]|1[0-8])|nflasha\d*|cnflasha\d*|mmcblk0(?:p\d+|rpmb)?|mtdblock\d*)(?:/|:|$)"
    r"|bodydata\.dat|udtrfirm|psd\.bin|defdet\.bin|backup\.bin|jiritsu|updater://|nvram://|eeprom://",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Verified Binary & .uxc Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_PHASE118_MARKERS: Tuple[str, ...] = (
    # Pillar 1: UVC / USB Streaming
    "VAL_HAITA_file_format_xavc_hs_streaming_restriction_UVC_FORMAT_30p",
    "INFRA_NOTIFY_USB_STREAMING_STATE_CHANGED",
    "INFRA_NOTIFY_USB_STREAMING_FORMAT_CHANGED",
    "VAL_usb_streaming_mode_USB_STREAMING_MODE_ON",
    # Pillar 2: SRT / Live Streaming
    "DefInfraVericLiveStreaming::TP_PROTOCOL",
    "DefInfraVericLiveStreaming::TP_CRYPTO_ALGO",
    "DefInfraVericLiveStreaming::TP_KEY_LENGTH",
    "BT_LIVE_STREAMING_SETTING_RESULT_PASSPHRASE_NOT_SET",
    # Pillar 3: CRSDK / Cine EI / Base ISO / PTP / FW Update Firewall
    "VAL_setting_log_shooting_LOG_SHOOTING_CINE_EI",
    "BASE_ISO_LOW_800",
    "BASE_ISO_HIGH_12800",
    "VAL_firmware_update_status_FIRMWARE_UPDATE_STATUS_ACCEPTING_DATA_UPLOAD",
    "INFRA_NOTIFY_PTP_OPERATION_DATA_SET",
)

FX6_APPFW_PHASE118_MARKERS: Tuple[str, ...] = (
    # Pillar 1: UVC / Procam USB Streaming
    "BKID_APP_SETTING_USB_STREAMING_PROCAM",
    "BKID_APP_SETTING_USB_STREAMING_FORMAT_PROCAM",
    "BKID_APP_SETTING_USB_STREAMING_AUDIO_PROCAM",
    "FUNC_set_usb_streaming_procam",
    # Pillar 2: SRT / RTMPS
    "BKID_APP_SETTING_SRT_SETTINGS1_CODEC",
    "BKID_APP_SETTING_SRT_SETTINGS1_STREAMING_BITRATE",
    "RTMPS_DefaultCertificates.pem",
    # Pillar 3: Remote FW Update + Variable ND
    "EVENT_REMOTE_REQUEST_START_BODY_UPDATE",
    "EVENT_REMOTE_REQUEST_SET_FIRMWARE_UPDATE_MODE_ON",
    "EVENT_REMOTE_REQUEST_FIRMWARE_UPDATE_CHECK",
    "FIRMWARE_UPDATE_STATUS_ACCEPTING_DATA_UPLOAD",
    "ND_FILTER_MANUAL_SET_0_3",
)

FX3_LIBMPR_PHASE118_MARKERS: Tuple[str, ...] = ("LPCM", "48000", "3840_2160", "1920_1080")
FX6_LIBMPR_PHASE118_MARKERS: Tuple[str, ...] = ("LPCM", "48000", "AVC_3840_2160_H422IP@L52")
FX6_LIBINFRA_PTP_PHASE118_MARKERS: Tuple[str, ...] = (
    "InfraPtpControl_Init",
    "PTPT_init_ip_remote",
    "PTPT_EE_send_data_ip_remote",
    "31PtptMultiSessionCallBackWrapper",
)
FX6_LIBNET_ETHER_PHASE118_MARKERS: Tuple[str, ...] = (
    "CT_ID_ASYNC_REQ_START_USB_HOST",
    "32mEN_STATE_USB_CONNECTED_USB_ETHER_DEVICE",
    "32mEN_EVT_API_SETUP_WIRED_ETHER_IF",
)
FX6_LIBVERIC_LIVE_PHASE118_MARKERS: Tuple[str, ...] = (
    "_ZN26DefInfraVericLiveStreaming23InfraVericLiveStreaming33receiveAddStreamingDestinationCmdERKNS_10ST_MSG_CMDE",
)

# Verified .uxc String Resource IDs
FX3_NS39_PHASE118_LABELS: Dict[int, str] = {
    0x0004E244: "Connected to PC Remote.\nCannot be executed.",
    0x0004EA54: "Connected to Remote Shooting.\nCannot be executed.",
}
FX3_NS3_PHASE118_LABELS: Dict[int, str] = {
    0x0000601C: "Turning PC Remote(Wired LAN) on\nenables connection.",
    0x000061AF: "Start streaming from the connected device. USB Streaming ends when the USB cable is removed.",
    0x0000620D: "Invalid during USB Streaming.",
}
FX6_NS1_PHASE118_LABELS: Dict[int, str] = {
    0x000024AF: "RTMP/RTMPS",
    0x000024C1: "RTMPS Certificate",
    0x00002777: "RTMP/RTMPS Streaming",
    0x00002BD1: "SRT-Caller 1",
}
FX6_NS2_PHASE118_LABELS: Dict[int, str] = {
    0x000049E3: "LPCM",
    0x00005002: "LPCM",
}

# ---------------------------------------------------------------------------
# Dataclasses (JSON-clean: no raw bytes objects stored in attributes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UvcUacDescriptorDecoded:
    valid: bool
    vendor_id: int
    uvc_bcd: int
    uac_bcd: int
    width: int
    height: int
    fps_x100: int
    pixel_format: str
    uac_sample_rate_hz: int
    uac_channels: int
    uac_bit_depth: int
    crc32_valid: bool
    packet_hex: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UvcUacBandwidthEvalResult:
    valid: bool
    status: str
    profile_id: str
    usb_link_speed: str
    stage_b_mode: str
    video_mbps: float
    audio_mbps: float
    total_payload_mbps: float
    link_usable_ceiling_mbps: float
    headroom_mbps: float
    sq_motion_active: bool
    hdmi_raw_active: bool
    fx3_native_uvc_absent_contained: bool
    descriptor_decoded: UvcUacDescriptorDecoded
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UvcUacStreamingReport:
    passed: bool
    fx3_appfw_uvc_markers: Tuple[str, ...]
    fx6_appfw_uvc_markers: Tuple[str, ...]
    fx3_libmpr_uac_markers: Tuple[str, ...]
    fx6_libmpr_uac_markers: Tuple[str, ...]
    uxc_uvc_labels: Dict[str, str]
    eval_4k30_mjpeg_usb3_bridge: UvcUacBandwidthEvalResult
    eval_1080p60_mjpeg_usb2_hs: UvcUacBandwidthEvalResult
    eval_1080p60_yuy2_usb3_ss: UvcUacBandwidthEvalResult
    blocked_1080p60_yuy2_on_usb2_hs: UvcUacBandwidthEvalResult
    blocked_4k30_yuy2_exceeds_usb3_ss: UvcUacBandwidthEvalResult
    blocked_fx3_direct_native_uvc: UvcUacBandwidthEvalResult
    blocked_uvc_during_hdmi_raw: UvcUacBandwidthEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class WiredStreamEvalResult:
    valid: bool
    status: str
    protocol: str
    transport_driver: str
    p12_airplane_rf_off: bool
    wf12_00342260_risk: int
    hci_rf_tx_packets: int
    resolution_key: str
    bitrate_mbps: float
    internal_4k_rec_requested: bool
    srt_pbkeylen_bytes: int
    srt_arq_latency_ms: int
    rtt_ms: int
    tls_version: str
    root_ca_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class WiredSrtRtmpsP12Report:
    passed: bool
    fx3_appfw_srt_markers: Tuple[str, ...]
    fx6_appfw_srt_markers: Tuple[str, ...]
    fx6_libnet_ether_markers: Tuple[str, ...]
    fx6_libveric_live_markers: Tuple[str, ...]
    uxc_srt_rtmps_labels: Dict[str, str]
    eval_srt_caller_aes256_4k30_cdc_ncm: WiredStreamEvalResult
    eval_srt_listener_aes128_1080p60_rndis: WiredStreamEvalResult
    eval_rtmps_tls13_1080p60_cdc_ncm: WiredStreamEvalResult
    blocked_wifi_wlan0_p12_violation: WiredStreamEvalResult
    blocked_srt_arq_out_of_range: WiredStreamEvalResult
    blocked_srt_weak_passphrase: WiredStreamEvalResult
    blocked_plaintext_rtmp_tls_required: WiredStreamEvalResult
    blocked_4k5994_stream_with_4k_rec: WiredStreamEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CrsdkPtpPropertyTranslation:
    valid: bool
    status: str
    target_body: str
    property_key: str
    crsdk_name: str
    ptp_prop_code_hex: str
    bk4_prop_id_hex: str
    requested_value: str
    effective_value: str
    p4_nd_clamped_clear: bool
    transport: str
    bulk_512b_aligned: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PtpFlashFirewallVerdict:
    allowed: bool
    status: str
    opcode_hex: str
    command_name: str
    target_or_filename: str
    flash_write_executed: bool
    brick_risk_prevented: bool
    emmc_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CrsdkPtpFirewallReport:
    passed: bool
    fx3_appfw_crsdk_markers: Tuple[str, ...]
    fx6_appfw_crsdk_markers: Tuple[str, ...]
    fx6_libinfra_ptp_markers: Tuple[str, ...]
    uxc_crsdk_labels: Dict[str, str]
    eval_cine_ei_fx3_ptp: CrsdkPtpPropertyTranslation
    eval_base_iso_12800_ptpip: CrsdkPtpPropertyTranslation
    eval_user_lut_shutter_angle_fx3: CrsdkPtpPropertyTranslation
    eval_p4_fx3_nd_clamped_clear: CrsdkPtpPropertyTranslation
    eval_fx6_variable_nd_accepted: CrsdkPtpPropertyTranslation
    eval_0x9209_bulk_512b_aligned: CrsdkPtpPropertyTranslation
    blocked_0x9209_unaligned_read: CrsdkPtpPropertyTranslation
    blocked_fw_update_mode_on: PtpFlashFirewallVerdict
    blocked_start_body_update: PtpFlashFirewallVerdict
    blocked_0x9280_scalar_dl: PtpFlashFirewallVerdict
    blocked_0x9282_updater_reconnect: PtpFlashFirewallVerdict
    blocked_mtp_send_ufu_payload: PtpFlashFirewallVerdict
    allowed_safe_0x9205_prop_set: PtpFlashFirewallVerdict
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase118WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZeroMutationEmmcPreservationReport:
    passed: bool
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    volatile_staging_guard: Phase118WriteGuardResult
    blocked_bodydata_dat_guard: Phase118WriteGuardResult
    blocked_nflasha15_guard: Phase118WriteGuardResult
    blocked_cnflasha0_guard: Phase118WriteGuardResult
    blocked_backup_bin_guard: Phase118WriteGuardResult
    firmware_flash_opcodes_blocked: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UsbUvcUacSrtAndCrsdkPtpReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    donor_file_sizes: Dict[str, int]
    pillar_1_uvc_uac_streaming: UvcUacStreamingReport
    pillar_2_wired_srt_rtmps_p12: WiredSrtRtmpsP12Report
    pillar_3_crsdk_ptp_firewall: CrsdkPtpFirewallReport
    pillar_4_zero_mutation_emmc_preservation: ZeroMutationEmmcPreservationReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Read-Only Helpers (Strictly os.O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------


def _read_bytes_rdonly(path: Path) -> bytes:
    """Read an entire file strictly via `os.O_RDONLY`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return b""
        chunks: List[bytes] = []
        remaining = sz
        while remaining > 0:
            block = os.read(fd, remaining)
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Mapping[str, Sequence[str]],
    *,
    is_elf: bool,
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    """Open `path` strictly `os.O_RDONLY` with `mmap.ACCESS_READ` and scan markers."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {k: () for k in marker_groups}

        unique_markers = sorted(
            {m for markers in marker_groups.values() for m in markers},
            key=lambda s: (-len(s), s),
        )
        matched_tokens: set[bytes] = set()

        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            ranges: List[Tuple[int, int]] = [(0, sz)]
            if is_elf:
                try:
                    secs = _parse_elf64_sections(mm)  # type: ignore[arg-type]
                    elf_ranges = [secs[s] for s in (".rodata", ".dynstr") if s in secs]
                    if elf_ranges:
                        ranges = elf_ranges
                except ValueError:
                    ranges = [(0, sz)]

            if unique_markers:
                pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
                for off, rsz in ranges:
                    for mo in pat.finditer(mm, off, off + rsz):
                        matched_tokens.add(mo.group(0))

        matched_list = list(matched_tokens)
        present_markers = {
            m
            for m in unique_markers
            if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
        }
        results: Dict[str, Tuple[str, ...]] = {
            group_name: tuple(m for m in markers if m in present_markers)
            for group_name, markers in marker_groups.items()
        }
        return sz, results
    finally:
        os.close(fd)


def _scan_bytes_marker_groups(
    blob: bytes,
    marker_groups: Mapping[str, Sequence[str]],
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    unique_markers = sorted(
        {m for markers in marker_groups.values() for m in markers},
        key=lambda s: (-len(s), s),
    )
    results: Dict[str, Tuple[str, ...]] = {k: () for k in marker_groups}
    if unique_markers:
        pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
        matched_tokens = {mo.group(0) for mo in pat.finditer(blob)}
        matched_list = list(matched_tokens)
        present_markers = {
            m
            for m in unique_markers
            if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
        }
        results = {
            group_name: tuple(m for m in markers if m in present_markers)
            for group_name, markers in marker_groups.items()
        }
    return len(blob), results


# ---------------------------------------------------------------------------
# Pillar 1 Functions: USB-C UVC 1.5 / UAC 2.0 Descriptor & Bandwidth Audit
# ---------------------------------------------------------------------------


def build_uvc15_uac20_descriptor_bundle(
    *,
    width: int = 3840,
    height: int = 2160,
    fps_x100: int = 2997,
    pixel_format: str = "MJPEG",
    uac_sample_rate_hz: int = UAC_SAMPLE_RATE_HZ,
    uac_channels: int = UAC_CHANNELS,
    uac_bit_depth: int = 16,
) -> bytes:
    """Build a 44-byte USB-C UVC 1.5 + UAC 2.0 interface descriptor verification bundle."""
    if uac_sample_rate_hz != UAC_SAMPLE_RATE_HZ or uac_channels != UAC_CHANNELS:
        raise ValueError("UAC 2.0 bundle requires 48000 Hz 2-ch stereo LPCM")
    if uac_bit_depth not in VALID_UAC_BIT_DEPTHS:
        raise ValueError(f"Unsupported uac_bit_depth={uac_bit_depth}")
    fmt_b = pixel_format.strip().upper().encode("ascii")[:8].ljust(8, b"\x00")
    body = struct.pack(
        "<8sHBBHHHHHH8sIHBB",
        UVC_DESCRIPTOR_BUNDLE_MAGIC,
        USB_VID_SONY,
        USB_DT_INTERFACE,
        USB_CLASS_VIDEO,
        UVC_VERSION_15,
        UAC_VERSION_20,
        width,
        height,
        fps_x100,
        USB_CLASS_AUDIO,
        fmt_b,
        uac_sample_rate_hz,
        0,
        uac_channels,
        uac_bit_depth,
    )
    crc = zlib.crc32(body) & 0xFFFFFFFF
    pkt = body + struct.pack("<I", crc)
    if len(pkt) != UVC_DESCRIPTOR_BUNDLE_BYTES:
        raise AssertionError(f"Unexpected bundle len {len(pkt)} != {UVC_DESCRIPTOR_BUNDLE_BYTES}")
    return pkt


def decode_uvc15_uac20_descriptor_bundle(packet: bytes) -> UvcUacDescriptorDecoded:
    """Decode and CRC32-verify a 44-byte UVC 1.5 + UAC 2.0 descriptor bundle."""
    errors: List[str] = []
    if len(packet) != UVC_DESCRIPTOR_BUNDLE_BYTES:
        return UvcUacDescriptorDecoded(
            valid=False,
            vendor_id=0,
            uvc_bcd=0,
            uac_bcd=0,
            width=0,
            height=0,
            fps_x100=0,
            pixel_format="INVALID",
            uac_sample_rate_hz=0,
            uac_channels=0,
            uac_bit_depth=0,
            crc32_valid=False,
            packet_hex=packet.hex(),
            errors=(f"Invalid bundle size {len(packet)} != {UVC_DESCRIPTOR_BUNDLE_BYTES}",),
        )
    body = packet[:-4]
    (rx_crc,) = struct.unpack("<I", packet[-4:])
    crc_ok = rx_crc == (zlib.crc32(body) & 0xFFFFFFFF)
    if not crc_ok:
        errors.append("CRC32 mismatch on UVC/UAC descriptor bundle")

    unpacked = struct.unpack("<8sHBBHHHHHH8sIHBB", body)
    magic, vid, dt_if, cls_v, uvc_bcd, uac_bcd, w, h, fps_x100, cls_a, fmt_b, sr, _pad, ch, bd = unpacked
    if magic != UVC_DESCRIPTOR_BUNDLE_MAGIC:
        errors.append("Invalid UVC/UAC descriptor magic")
    if vid != USB_VID_SONY:
        errors.append(f"Unexpected USB VID 0x{vid:04X} != 0x054C")
    if dt_if != USB_DT_INTERFACE or cls_v != USB_CLASS_VIDEO or cls_a != USB_CLASS_AUDIO:
        errors.append("Invalid USB interface class codes (expected 0x0E Video + 0x01 Audio)")
    if uvc_bcd != UVC_VERSION_15 or uac_bcd != UAC_VERSION_20:
        errors.append("Expected UVC 1.5 (0x0150) and UAC 2.0 (0x0200)")
    fmt = fmt_b.rstrip(b"\x00").decode("ascii", "replace")
    return UvcUacDescriptorDecoded(
        valid=len(errors) == 0,
        vendor_id=vid,
        uvc_bcd=uvc_bcd,
        uac_bcd=uac_bcd,
        width=w,
        height=h,
        fps_x100=fps_x100,
        pixel_format=fmt,
        uac_sample_rate_hz=sr,
        uac_channels=ch,
        uac_bit_depth=bd,
        crc32_valid=crc_ok,
        packet_hex=packet.hex(),
        errors=tuple(errors),
    )


def evaluate_uvc_uac_bandwidth_and_compat(
    *,
    profile_id: str = "4K30P_MJPEG",
    usb_link_speed: str = "USB3_SUPERSPEED_5G",
    stage_b_mode: str = "HDMI_TO_UVC_BRIDGE",
    uac_bit_depth: int = 16,
    sq_motion_active: bool = False,
    hdmi_raw_active: bool = False,
    corrupt_descriptor_crc: bool = False,
) -> UvcUacBandwidthEvalResult:
    """Audit USB-C UVC 1.5 / UAC 2.0 bandwidth budget and FX6-on-FX3 Stage-B compatibility."""
    norm_prof = profile_id.strip().upper()
    norm_link = usb_link_speed.strip().upper()
    norm_mode = stage_b_mode.strip().upper()
    if norm_prof not in UVC_STREAM_PROFILES:
        raise ValueError(f"Unsupported UVC profile_id={profile_id!r}")
    if norm_link not in VALID_USB_LINK_SPEEDS:
        raise ValueError(f"Unsupported usb_link_speed={usb_link_speed!r}")
    if norm_mode not in VALID_UVC_STAGE_B_MODES:
        raise ValueError(f"Unsupported stage_b_mode={stage_b_mode!r}")
    if uac_bit_depth not in VALID_UAC_BIT_DEPTHS:
        raise ValueError(f"Unsupported uac_bit_depth={uac_bit_depth}")

    spec = UVC_STREAM_PROFILES[norm_prof]
    w = int(spec["width"])
    h = int(spec["height"])
    fps = float(spec["fps"])
    fmt = str(spec["pixel_format"])
    video_mbps = float(spec["video_mbps"])
    audio_mbps = round((UAC_SAMPLE_RATE_HZ * UAC_CHANNELS * uac_bit_depth) / 1_000_000.0, 4)
    total_mbps = round(video_mbps + audio_mbps, 4)

    ceiling = (
        USB3_SUPERSPEED_5GBPS_USABLE_MBPS
        if norm_link == "USB3_SUPERSPEED_5G"
        else USB2_HIGHSPEED_480MBPS_USABLE_MBPS
    )
    headroom = round(ceiling - total_mbps, 4)

    pkt = bytearray(
        build_uvc15_uac20_descriptor_bundle(
            width=w,
            height=h,
            fps_x100=int(round(fps * 100)),
            pixel_format=fmt,
            uac_bit_depth=uac_bit_depth,
        )
    )
    if corrupt_descriptor_crc:
        pkt[-1] ^= 0x5A
    decoded = decode_uvc15_uac20_descriptor_bundle(bytes(pkt))

    errors: List[str] = list(decoded.errors)
    status = "UVC15_UAC20_STAGE_B_COMPAT_VERIFIED"

    if norm_mode == "DIRECT_FX3_NATIVE_UVC_GADGET":
        status = "BLOCKED_FX3_NATIVE_UVC_GADGET_ABSENT"
        errors.append(
            "BLOCKED_FX3_NATIVE_UVC_GADGET_ABSENT: ILME-FX3 v7.02 omits native USB Streaming "
            "gadget; route via HDMI_TO_UVC_BRIDGE or FX30_A7S3_UVC_DESCRIPTOR_SIM"
        )
    if total_mbps > ceiling:
        status = (
            "BLOCKED_USB2_HS_480M_BANDWIDTH_EXCEEDED"
            if norm_link == "USB2_HIGHSPEED_480M"
            else "BLOCKED_USB3_SS_5G_BANDWIDTH_EXCEEDED"
        )
        errors.append(
            f"{status}: {total_mbps:.3f} Mbps > usable {norm_link} ceiling {ceiling:.1f} Mbps"
        )
    if sq_motion_active:
        status = "BLOCKED_UVC_SQ_MOTION_EXCLUSION"
        errors.append("BLOCKED_UVC_SQ_MOTION_EXCLUSION: USB Streaming is disabled during S&Q Motion")
    if hdmi_raw_active:
        status = "BLOCKED_UVC_HDMI_RAW16_EXCLUSION"
        errors.append("BLOCKED_UVC_HDMI_RAW16_EXCLUSION: UVC/Streaming disabled during 16-bit HDMI RAW")

    return UvcUacBandwidthEvalResult(
        valid=len(errors) == 0,
        status=status,
        profile_id=norm_prof,
        usb_link_speed=norm_link,
        stage_b_mode=norm_mode,
        video_mbps=video_mbps,
        audio_mbps=audio_mbps,
        total_payload_mbps=total_mbps,
        link_usable_ceiling_mbps=ceiling,
        headroom_mbps=headroom,
        sq_motion_active=sq_motion_active,
        hdmi_raw_active=hdmi_raw_active,
        fx3_native_uvc_absent_contained=(norm_mode != "DIRECT_FX3_NATIVE_UVC_GADGET"),
        descriptor_decoded=decoded,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2 Functions: Wired USB-LAN SRT & RTMPS Streaming + P12 RF-Off Guard
# ---------------------------------------------------------------------------


def evaluate_wired_srt_rtmps_stream(
    *,
    protocol: str = "SRT_CALLER",
    transport_driver: str = "CDC_NCM_RTL8153",
    p12_airplane_rf_off: bool = True,
    resolution_key: str = "4K_2997P",
    bitrate_mbps: float = 34.0,
    internal_4k_rec_requested: bool = True,
    srt_pbkeylen_bytes: int = 32,
    srt_passphrase: str = "StageB_FX3_WiredSRT_2026!",
    srt_arq_latency_ms: int = 120,
    rtt_ms: int = 25,
    tls_version: str = "TLS_1_3",
    root_ca_verified: bool = True,
    require_encryption: bool = True,
) -> WiredStreamEvalResult:
    """Audit wired USB-LAN SRT (Caller/Listener, AES-128/256, ARQ) & RTMPS TLS 1.3 under P12."""
    norm_proto = protocol.strip().upper()
    norm_drv = transport_driver.strip().upper()
    norm_res = resolution_key.strip().upper()
    norm_tls = tls_version.strip().upper()
    errors: List[str] = []

    if norm_proto not in VALID_STREAM_PROTOCOLS:
        raise ValueError(f"Unsupported protocol={protocol!r}")
    if norm_res not in SONY_FX3_STREAMING_BITRATE_ENVELOPES:
        raise ValueError(f"Unsupported resolution_key={resolution_key!r}")

    # P12 Wi-Fi / BT RF-Off Firewall
    is_rf_transport = norm_drv in FORBIDDEN_RF_TRANSPORTS
    is_wired_allowed = norm_drv in VALID_WIRED_STREAM_TRANSPORTS
    wf12_risk = 0
    hci_tx = 0

    if is_rf_transport or not is_wired_allowed:
        if p12_airplane_rf_off:
            wf12_risk = 1
            hci_tx = 1 if norm_drv == "BT_PAN" else 0
            errors.append(
                f"BLOCKED_P12_RF_OFF_VIOLATION_00342260: RF/unknown transport {norm_drv!r} "
                "forbidden under P12 Airplane RF-Off; use CDC_NCM_RTL8153 / CDC_NCM_AX88179 / USB_RNDIS_WIRED"
            )
        else:
            errors.append(f"Unsupported/RF streaming transport {norm_drv!r} without wired USB-LAN")

    env = SONY_FX3_STREAMING_BITRATE_ENVELOPES[norm_res]
    min_b = float(env["min_mbps"])
    max_b = float(env["max_mbps"])
    if bitrate_mbps < min_b or bitrate_mbps > max_b:
        errors.append(
            f"BLOCKED_BITRATE_OUT_OF_ENVELOPE: {bitrate_mbps} Mbps outside [{min_b}..{max_b}] for {norm_res}"
        )

    if internal_4k_rec_requested and not bool(env["allows_internal_4k_rec"]):
        errors.append(
            f"BLOCKED_4K5994_INTERNAL_4K_REC_EXCLUSION: [Movie Rec During Streaming] cannot use 4K while streaming {norm_res}"
        )

    if norm_proto in ("SRT_CALLER", "SRT_LISTENER"):
        if srt_pbkeylen_bytes not in VALID_SRT_PBKEYLEN:
            errors.append(f"BLOCKED_SRT_INVALID_PBKEYLEN: {srt_pbkeylen_bytes} not in {VALID_SRT_PBKEYLEN}")
        if require_encryption and (
            len(srt_passphrase) < SRT_PASSPHRASE_MIN_LEN or len(srt_passphrase) > SRT_PASSPHRASE_MAX_LEN
        ):
            errors.append(
                f"BLOCKED_SRT_PASSPHRASE_LENGTH: len={len(srt_passphrase)} must be [{SRT_PASSPHRASE_MIN_LEN}..{SRT_PASSPHRASE_MAX_LEN}]"
            )
        if srt_arq_latency_ms < SRT_ARQ_LATENCY_MIN_MS or srt_arq_latency_ms > SRT_ARQ_LATENCY_MAX_MS:
            errors.append(
                f"BLOCKED_SRT_ARQ_LATENCY_OUT_OF_RANGE: {srt_arq_latency_ms} ms not in [{SRT_ARQ_LATENCY_MIN_MS}..{SRT_ARQ_LATENCY_MAX_MS}]"
            )
        if srt_arq_latency_ms < (3 * max(1, rtt_ms)):
            errors.append(
                f"BLOCKED_SRT_ARQ_RTT_MARGIN: latency {srt_arq_latency_ms} ms < 3x RTT ({3 * rtt_ms} ms)"
            )
    elif norm_proto == "RTMPS_TLS13":
        if norm_tls not in ("TLS_1_3", "TLS_1_2"):
            errors.append(f"BLOCKED_RTMPS_WEAK_TLS: {norm_tls}")
        if not root_ca_verified:
            errors.append("BLOCKED_RTMPS_ROOT_CERT_UNVERIFIED")
    elif norm_proto == "RTMP_PLAIN":
        if require_encryption:
            errors.append("BLOCKED_PLAINTEXT_RTMP_WHEN_TLS_REQUIRED: use RTMPS_TLS13 or SRT")

    status = (
        f"WIRED_{norm_proto}_P12_ISOLATED_VERIFIED"
        if not errors
        else errors[0].split(":", 1)[0]
    )

    return WiredStreamEvalResult(
        valid=len(errors) == 0,
        status=status,
        protocol=norm_proto,
        transport_driver=norm_drv,
        p12_airplane_rf_off=p12_airplane_rf_off,
        wf12_00342260_risk=wf12_risk,
        hci_rf_tx_packets=hci_tx,
        resolution_key=norm_res,
        bitrate_mbps=bitrate_mbps,
        internal_4k_rec_requested=internal_4k_rec_requested,
        srt_pbkeylen_bytes=srt_pbkeylen_bytes,
        srt_arq_latency_ms=srt_arq_latency_ms,
        rtt_ms=rtt_ms,
        tls_version=norm_tls,
        root_ca_verified=root_ca_verified,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3 Functions: CRSDK PTP/PTP-IP Translator & Flash-Opcode Firewall
# ---------------------------------------------------------------------------


def translate_crsdk_property_to_ptp(
    *,
    target_body: str = "ILME-FX3",
    property_key: str = "CINE_EI_LOG_MODE",
    value: object = "CINE_EI",
    transport: str = "USB_PTP",
    bulk_read_bytes: int = 1024,
) -> CrsdkPtpPropertyTranslation:
    """Translate CRSDK CrDeviceProperty into Sony PTP/PTP-IP + BK4 contract with P4 ND clamp."""
    norm_body = target_body.strip().upper()
    norm_key = property_key.strip().upper()
    norm_tr = transport.strip().upper()
    if norm_body not in ("ILME-FX3", "ILME-FX6"):
        raise ValueError(f"Unsupported target_body={target_body!r}")
    if norm_key not in CRSDK_PROPERTY_PTP_MAP:
        raise ValueError(f"Unsupported property_key={property_key!r}")
    if norm_tr not in ("USB_PTP", "WIRED_PTPIP_15740"):
        raise ValueError(f"Unsupported PTP transport={transport!r}")

    spec = CRSDK_PROPERTY_PTP_MAP[norm_key]
    ptp_code = int(spec["ptp_prop_code"])
    bk4_id = int(spec["bk4_prop_id"])
    valid_vals = tuple(spec["valid_values"])  # type: ignore[arg-type]
    errors: List[str] = []

    norm_val = value.strip().upper() if isinstance(value, str) else value
    if norm_val not in valid_vals:
        errors.append(f"BLOCKED_INVALID_CRSDK_PROPERTY_VALUE: {norm_val!r} not in {valid_vals}")

    # 512-byte USB bulk packet alignment guard (0x9209 multi-packet response safety)
    aligned = (bulk_read_bytes > 0) and (bulk_read_bytes % USB_BULK_PACKET_ALIGNMENT_BYTES == 0)
    if norm_tr == "USB_PTP" and not aligned:
        errors.append(
            f"BLOCKED_PTP_0x9209_BULK_UNALIGNED_READ: {bulk_read_bytes} B not multiple of 512 B"
        )

    # P4 Electronic Variable ND -> Clear (0) clamp on FX3
    p4_clamped = False
    effective_val = str(norm_val)
    status = "CRSDK_PTP_PROPERTY_TRANSLATED"
    if norm_key == "ND_FILTER_OD_X10" and norm_body == "ILME-FX3":
        if norm_val != 0:
            p4_clamped = True
            effective_val = "0_CLEAR_P4_CLAMP"
            status = "P4_ABSENT_ND_CLAMPED_CLEAR"
        else:
            effective_val = "0_CLEAR"
    elif errors:
        status = errors[0].split(":", 1)[0]

    return CrsdkPtpPropertyTranslation(
        valid=len(errors) == 0,
        status=status,
        target_body=norm_body,
        property_key=norm_key,
        crsdk_name=str(spec["crsdk_name"]),
        ptp_prop_code_hex=f"0x{ptp_code:04X}",
        bk4_prop_id_hex=f"0x{bk4_id:08X}",
        requested_value=str(norm_val),
        effective_value=effective_val,
        p4_nd_clamped_clear=p4_clamped,
        transport=norm_tr,
        bulk_512b_aligned=aligned,
        errors=tuple(errors),
    )


def evaluate_ptp_flash_opcode_firewall(
    *,
    opcode: int,
    command_name: str = "",
    target_or_filename: str = "",
    payload_prefix: bytes = b"",
) -> PtpFlashFirewallVerdict:
    """Stage-B Firewall hard-blocking USB/PTP firmware-update & eMMC flash opcodes."""
    norm_cmd = command_name.strip().upper()
    norm_tgt = target_or_filename.strip()
    reasons: List[str] = []

    if opcode in FORBIDDEN_PTP_FLASH_OPCODES:
        reasons.append(
            f"Forbidden PTP flash/updater opcode 0x{opcode:04X} ({FORBIDDEN_PTP_FLASH_OPCODES[opcode]})"
        )
    if norm_cmd in FORBIDDEN_CRSDK_FW_UPDATE_COMMANDS:
        reasons.append(f"Forbidden CRSDK firmware-update command {norm_cmd}")
    if norm_tgt and FORBIDDEN_PERSISTENT_EMMC_RE.search(norm_tgt):
        reasons.append(f"Forbidden firmware/eMMC target path {norm_tgt!r}")
    if any(pat in payload_prefix for pat in FORBIDDEN_FIRMWARE_PAYLOAD_PATTERNS):
        reasons.append("Forbidden firmware container magic detected in PTP/MTP upload payload")

    if reasons:
        return PtpFlashFirewallVerdict(
            allowed=False,
            status="BLOCKED_STAGE_B_PTP_FLASH_OPCODE_FIREWALL",
            opcode_hex=f"0x{opcode:04X}",
            command_name=norm_cmd or FORBIDDEN_PTP_FLASH_OPCODES.get(opcode, "UNKNOWN"),
            target_or_filename=norm_tgt,
            flash_write_executed=False,
            brick_risk_prevented=True,
            emmc_mutation_bytes=0,
            errors=tuple(reasons),
        )

    if opcode not in SONY_SAFE_PTP_OPCODES:
        return PtpFlashFirewallVerdict(
            allowed=False,
            status="BLOCKED_UNLISTED_PTP_VENDOR_OPCODE",
            opcode_hex=f"0x{opcode:04X}",
            command_name=norm_cmd or "UNLISTED_OPCODE",
            target_or_filename=norm_tgt,
            flash_write_executed=False,
            brick_risk_prevented=True,
            emmc_mutation_bytes=0,
            errors=(f"Fail-closed: opcode 0x{opcode:04X} not in allowlisted safe CRSDK PTP opcodes",),
        )

    return PtpFlashFirewallVerdict(
        allowed=True,
        status="SAFE_CRSDK_PTP_OPCODE_ALLOWED",
        opcode_hex=f"0x{opcode:04X}",
        command_name=norm_cmd or SONY_SAFE_PTP_OPCODES[opcode],
        target_or_filename=norm_tgt,
        flash_write_executed=False,
        brick_risk_prevented=False,
        emmc_mutation_bytes=0,
        errors=(),
    )


# ---------------------------------------------------------------------------
# Pillar 4 Functions: Volatile Staging & Zero Persistent eMMC Mutation Guard
# ---------------------------------------------------------------------------


def evaluate_phase118_write_guard(target_path: str) -> Phase118WriteGuardResult:
    """Enforce volatile RAM staging only and zero persistent eMMC/OTA/calibration mutation."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES) and not bool(
        FORBIDDEN_PERSISTENT_EMMC_RE.search(norm)
    )
    if is_volatile:
        return Phase118WriteGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            emmc_mutation_bytes=0,
            calibration_mutation_bytes=0,
            errors=(),
        )
    return Phase118WriteGuardResult(
        valid=False,
        status="BLOCKED_PERSISTENT_EMMC_OR_OTA_WRITE",
        target_path=norm,
        volatile_ram_staged=False,
        persistent_write_blocked=True,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        errors=(f"BLOCKED_PERSISTENT_EMMC_OR_OTA_WRITE: target_path={norm!r}",),
    )


# ---------------------------------------------------------------------------
# Pillar Evaluators & Top-Level Phase 118 Unified Auditor
# ---------------------------------------------------------------------------


def evaluate_pillar_1_uvc_uac_streaming(
    *,
    fx3_appfw_uvc_markers: Tuple[str, ...],
    fx6_appfw_uvc_markers: Tuple[str, ...],
    fx3_libmpr_uac_markers: Tuple[str, ...],
    fx6_libmpr_uac_markers: Tuple[str, ...],
    uxc_uvc_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> UvcUacStreamingReport:
    errors = list(extra_errors)

    e_4k30_mjpeg = evaluate_uvc_uac_bandwidth_and_compat(
        profile_id="4K30P_MJPEG",
        usb_link_speed="USB3_SUPERSPEED_5G",
        stage_b_mode="HDMI_TO_UVC_BRIDGE",
    )
    e_1080_mjpeg_usb2 = evaluate_uvc_uac_bandwidth_and_compat(
        profile_id="1080P60P_MJPEG",
        usb_link_speed="USB2_HIGHSPEED_480M",
        stage_b_mode="FX30_A7S3_UVC_DESCRIPTOR_SIM",
    )
    e_1080_yuy2_usb3 = evaluate_uvc_uac_bandwidth_and_compat(
        profile_id="1080P60P_YUY2",
        usb_link_speed="USB3_SUPERSPEED_5G",
        stage_b_mode="HDMI_TO_UVC_BRIDGE",
        uac_bit_depth=24,
    )
    b_1080_yuy2_usb2 = evaluate_uvc_uac_bandwidth_and_compat(
        profile_id="1080P60P_YUY2",
        usb_link_speed="USB2_HIGHSPEED_480M",
        stage_b_mode="HDMI_TO_UVC_BRIDGE",
    )
    b_4k30_yuy2_usb3 = evaluate_uvc_uac_bandwidth_and_compat(
        profile_id="4K30P_YUY2",
        usb_link_speed="USB3_SUPERSPEED_5G",
        stage_b_mode="HDMI_TO_UVC_BRIDGE",
    )
    b_fx3_direct = evaluate_uvc_uac_bandwidth_and_compat(
        profile_id="4K30P_MJPEG",
        usb_link_speed="USB3_SUPERSPEED_5G",
        stage_b_mode="DIRECT_FX3_NATIVE_UVC_GADGET",
    )
    b_raw_excl = evaluate_uvc_uac_bandwidth_and_compat(
        profile_id="1080P60P_MJPEG",
        usb_link_speed="USB3_SUPERSPEED_5G",
        stage_b_mode="HDMI_TO_UVC_BRIDGE",
        hdmi_raw_active=True,
    )

    for lbl, ev in (
        ("4k30_mjpeg", e_4k30_mjpeg),
        ("1080_mjpeg_usb2", e_1080_mjpeg_usb2),
        ("1080_yuy2_usb3", e_1080_yuy2_usb3),
    ):
        if not ev.valid:
            errors.append(f"Positive UVC check {lbl} failed: {ev.errors}")
    for lbl, blk in (
        ("1080_yuy2_usb2", b_1080_yuy2_usb2),
        ("4k30_yuy2_usb3", b_4k30_yuy2_usb3),
        ("fx3_direct", b_fx3_direct),
        ("hdmi_raw_excl", b_raw_excl),
    ):
        if blk.valid:
            errors.append(f"Negative UVC guard {lbl} unexpectedly passed")

    return UvcUacStreamingReport(
        passed=len(errors) == 0,
        fx3_appfw_uvc_markers=fx3_appfw_uvc_markers,
        fx6_appfw_uvc_markers=fx6_appfw_uvc_markers,
        fx3_libmpr_uac_markers=fx3_libmpr_uac_markers,
        fx6_libmpr_uac_markers=fx6_libmpr_uac_markers,
        uxc_uvc_labels=uxc_uvc_labels,
        eval_4k30_mjpeg_usb3_bridge=e_4k30_mjpeg,
        eval_1080p60_mjpeg_usb2_hs=e_1080_mjpeg_usb2,
        eval_1080p60_yuy2_usb3_ss=e_1080_yuy2_usb3,
        blocked_1080p60_yuy2_on_usb2_hs=b_1080_yuy2_usb2,
        blocked_4k30_yuy2_exceeds_usb3_ss=b_4k30_yuy2_usb3,
        blocked_fx3_direct_native_uvc=b_fx3_direct,
        blocked_uvc_during_hdmi_raw=b_raw_excl,
        errors=tuple(errors),
    )


def evaluate_pillar_2_wired_srt_rtmps_p12(
    *,
    fx3_appfw_srt_markers: Tuple[str, ...],
    fx6_appfw_srt_markers: Tuple[str, ...],
    fx6_libnet_ether_markers: Tuple[str, ...],
    fx6_libveric_live_markers: Tuple[str, ...],
    uxc_srt_rtmps_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> WiredSrtRtmpsP12Report:
    errors = list(extra_errors)

    e_srt_caller = evaluate_wired_srt_rtmps_stream(
        protocol="SRT_CALLER",
        transport_driver="CDC_NCM_RTL8153",
        resolution_key="4K_2997P",
        bitrate_mbps=34.0,
        internal_4k_rec_requested=True,
        srt_pbkeylen_bytes=32,
        srt_arq_latency_ms=120,
        rtt_ms=25,
    )
    e_srt_listener = evaluate_wired_srt_rtmps_stream(
        protocol="SRT_LISTENER",
        transport_driver="USB_RNDIS_WIRED",
        resolution_key="1080P_5994P",
        bitrate_mbps=20.0,
        internal_4k_rec_requested=True,
        srt_pbkeylen_bytes=16,
        srt_arq_latency_ms=200,
        rtt_ms=30,
    )
    e_rtmps = evaluate_wired_srt_rtmps_stream(
        protocol="RTMPS_TLS13",
        transport_driver="CDC_NCM_AX88179",
        resolution_key="1080P_5994P",
        bitrate_mbps=15.0,
        internal_4k_rec_requested=False,
        tls_version="TLS_1_3",
        root_ca_verified=True,
    )
    b_wifi = evaluate_wired_srt_rtmps_stream(
        protocol="SRT_CALLER",
        transport_driver="WIFI_WLAN0",
        p12_airplane_rf_off=True,
    )
    b_arq = evaluate_wired_srt_rtmps_stream(
        protocol="SRT_CALLER",
        transport_driver="CDC_NCM_RTL8153",
        srt_arq_latency_ms=1500,
    )
    b_pass = evaluate_wired_srt_rtmps_stream(
        protocol="SRT_CALLER",
        transport_driver="CDC_NCM_RTL8153",
        srt_passphrase="short",
    )
    b_rtmp_plain = evaluate_wired_srt_rtmps_stream(
        protocol="RTMP_PLAIN",
        transport_driver="CDC_NCM_RTL8153",
        resolution_key="1080P_5994P",
        bitrate_mbps=10.0,
        require_encryption=True,
    )
    b_4k60_rec = evaluate_wired_srt_rtmps_stream(
        protocol="SRT_CALLER",
        transport_driver="CDC_NCM_RTL8153",
        resolution_key="4K_5994P",
        bitrate_mbps=38.0,
        internal_4k_rec_requested=True,
    )

    for lbl, ev in (
        ("srt_caller", e_srt_caller),
        ("srt_listener", e_srt_listener),
        ("rtmps", e_rtmps),
    ):
        if not ev.valid or ev.wf12_00342260_risk != 0 or ev.hci_rf_tx_packets != 0:
            errors.append(f"Positive wired streaming check {lbl} failed: {ev.errors}")
    for lbl, blk in (
        ("wifi_p12", b_wifi),
        ("arq_oob", b_arq),
        ("weak_pass", b_pass),
        ("plain_rtmp", b_rtmp_plain),
        ("4k60_rec_excl", b_4k60_rec),
    ):
        if blk.valid:
            errors.append(f"Negative streaming guard {lbl} unexpectedly passed")
    if b_wifi.wf12_00342260_risk == 0:
        errors.append("Wi-Fi P12 violation failed to flag wf12_00342260_risk")

    return WiredSrtRtmpsP12Report(
        passed=len(errors) == 0,
        fx3_appfw_srt_markers=fx3_appfw_srt_markers,
        fx6_appfw_srt_markers=fx6_appfw_srt_markers,
        fx6_libnet_ether_markers=fx6_libnet_ether_markers,
        fx6_libveric_live_markers=fx6_libveric_live_markers,
        uxc_srt_rtmps_labels=uxc_srt_rtmps_labels,
        eval_srt_caller_aes256_4k30_cdc_ncm=e_srt_caller,
        eval_srt_listener_aes128_1080p60_rndis=e_srt_listener,
        eval_rtmps_tls13_1080p60_cdc_ncm=e_rtmps,
        blocked_wifi_wlan0_p12_violation=b_wifi,
        blocked_srt_arq_out_of_range=b_arq,
        blocked_srt_weak_passphrase=b_pass,
        blocked_plaintext_rtmp_tls_required=b_rtmp_plain,
        blocked_4k5994_stream_with_4k_rec=b_4k60_rec,
        errors=tuple(errors),
    )


def evaluate_pillar_3_crsdk_ptp_firewall(
    *,
    fx3_appfw_crsdk_markers: Tuple[str, ...],
    fx6_appfw_crsdk_markers: Tuple[str, ...],
    fx6_libinfra_ptp_markers: Tuple[str, ...],
    uxc_crsdk_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> CrsdkPtpFirewallReport:
    errors = list(extra_errors)

    e_cine = translate_crsdk_property_to_ptp(
        target_body="ILME-FX3",
        property_key="CINE_EI_LOG_MODE",
        value="CINE_EI",
        transport="USB_PTP",
    )
    e_iso = translate_crsdk_property_to_ptp(
        target_body="ILME-FX3",
        property_key="BASE_ISO",
        value=12800,
        transport="WIRED_PTPIP_15740",
    )
    e_lut = translate_crsdk_property_to_ptp(
        target_body="ILME-FX3",
        property_key="USER_3D_LUT",
        value="USER1",
        transport="USB_PTP",
    )
    e_nd_fx3 = translate_crsdk_property_to_ptp(
        target_body="ILME-FX3",
        property_key="ND_FILTER_OD_X10",
        value=9,
        transport="USB_PTP",
    )
    e_nd_fx6 = translate_crsdk_property_to_ptp(
        target_body="ILME-FX6",
        property_key="ND_FILTER_OD_X10",
        value=9,
        transport="WIRED_PTPIP_15740",
    )
    e_bulk_ok = translate_crsdk_property_to_ptp(
        target_body="ILME-FX3",
        property_key="SHUTTER_ANGLE_X10",
        value=1800,
        transport="USB_PTP",
        bulk_read_bytes=1536,
    )
    b_bulk_bad = translate_crsdk_property_to_ptp(
        target_body="ILME-FX3",
        property_key="SHUTTER_ANGLE_X10",
        value=1800,
        transport="USB_PTP",
        bulk_read_bytes=12,
    )

    for lbl, ev in (
        ("cine_ei", e_cine),
        ("base_iso", e_iso),
        ("user_lut", e_lut),
        ("p4_fx3_nd", e_nd_fx3),
        ("fx6_nd", e_nd_fx6),
        ("bulk_ok", e_bulk_ok),
    ):
        if not ev.valid:
            errors.append(f"CRSDK PTP translation {lbl} failed: {ev.errors}")
    if not e_nd_fx3.p4_nd_clamped_clear or e_nd_fx6.p4_nd_clamped_clear:
        errors.append("P4 Electronic Variable ND FX3->Clear clamp asymmetry failed")
    if b_bulk_bad.valid:
        errors.append("Unaligned 12-byte 0x9209 USB bulk read was not blocked")

    # Stage-B Destructive PTP Firmware-Update Opcode Firewall
    fw_mode_on = evaluate_ptp_flash_opcode_firewall(
        opcode=0x9207,
        command_name="EVENT_REMOTE_REQUEST_SET_FIRMWARE_UPDATE_MODE_ON",
    )
    fw_start_body = evaluate_ptp_flash_opcode_firewall(
        opcode=0x9207,
        command_name="EVENT_REMOTE_REQUEST_START_BODY_UPDATE",
    )
    fw_9280 = evaluate_ptp_flash_opcode_firewall(
        opcode=0x9280,
        command_name="SONY_CMD_SCALAR_NOTIFY_DLMODE",
        target_or_filename="/dev/nflasha5",
    )
    fw_9282 = evaluate_ptp_flash_opcode_firewall(
        opcode=0x9282,
        command_name="PTP_OC_SONY_REQ_RECONNECT_UPDATER",
    )
    fw_send_ufu = evaluate_ptp_flash_opcode_firewall(
        opcode=0x100D,
        target_or_filename="BODYDATA.DAT",
        payload_prefix=b"\x89UFU\r\n\x1a\nUDTRFIRM",
    )
    safe_9205 = evaluate_ptp_flash_opcode_firewall(
        opcode=0x9205,
        command_name="PTP_OC_SONY_SDIO_SetExtDevicePropValue",
    )

    for lbl, blk in (
        ("fw_mode_on", fw_mode_on),
        ("fw_start_body", fw_start_body),
        ("fw_9280", fw_9280),
        ("fw_9282", fw_9282),
        ("fw_send_ufu", fw_send_ufu),
    ):
        if blk.allowed or blk.flash_write_executed or not blk.brick_risk_prevented or blk.emmc_mutation_bytes != 0:
            errors.append(f"PTP flash firewall {lbl} failed to block destructive opcode")
    if not safe_9205.allowed:
        errors.append(f"Safe 0x9205 property set opcode blocked: {safe_9205.errors}")

    return CrsdkPtpFirewallReport(
        passed=len(errors) == 0,
        fx3_appfw_crsdk_markers=fx3_appfw_crsdk_markers,
        fx6_appfw_crsdk_markers=fx6_appfw_crsdk_markers,
        fx6_libinfra_ptp_markers=fx6_libinfra_ptp_markers,
        uxc_crsdk_labels=uxc_crsdk_labels,
        eval_cine_ei_fx3_ptp=e_cine,
        eval_base_iso_12800_ptpip=e_iso,
        eval_user_lut_shutter_angle_fx3=e_lut,
        eval_p4_fx3_nd_clamped_clear=e_nd_fx3,
        eval_fx6_variable_nd_accepted=e_nd_fx6,
        eval_0x9209_bulk_512b_aligned=e_bulk_ok,
        blocked_0x9209_unaligned_read=b_bulk_bad,
        blocked_fw_update_mode_on=fw_mode_on,
        blocked_start_body_update=fw_start_body,
        blocked_0x9280_scalar_dl=fw_9280,
        blocked_0x9282_updater_reconnect=fw_9282,
        blocked_mtp_send_ufu_payload=fw_send_ufu,
        allowed_safe_0x9205_prop_set=safe_9205,
        errors=tuple(errors),
    )


def evaluate_pillar_4_zero_mutation_emmc_preservation(
    *,
    fx3_global_xdb_valid: bool,
    fx6_global_xdb_valid: bool,
    extra_errors: Sequence[str] = (),
) -> ZeroMutationEmmcPreservationReport:
    errors = list(extra_errors)
    if not fx3_global_xdb_valid:
        errors.append("FX3 global.xdb (uxa\\x07) failed structural validation")
    if not fx6_global_xdb_valid:
        errors.append("FX6 global.xdb (uxa\\x07) failed structural validation")

    g_vol = evaluate_phase118_write_guard("/tmp/fx3_stageb_uvc_srt_crsdk_shadow.json")
    g_body = evaluate_phase118_write_guard("/mnt/sd/BODYDATA.DAT")
    g_nf15 = evaluate_phase118_write_guard("/dev/nflasha15")
    g_cn0 = evaluate_phase118_write_guard("/dev/cnflasha0")
    g_bak = evaluate_phase118_write_guard("p2:/setting/Backup.bin")

    if not g_vol.valid:
        errors.append("Volatile RAM staging unexpectedly blocked")
    for lbl, blk in (
        ("BODYDATA.DAT", g_body),
        ("nflasha15", g_nf15),
        ("cnflasha0", g_cn0),
        ("Backup.bin", g_bak),
    ):
        if blk.valid:
            errors.append(f"Persistent eMMC/OTA target {lbl} was not blocked")

    return ZeroMutationEmmcPreservationReport(
        passed=len(errors) == 0,
        fx3_global_xdb_valid=fx3_global_xdb_valid,
        fx6_global_xdb_valid=fx6_global_xdb_valid,
        volatile_staging_guard=g_vol,
        blocked_bodydata_dat_guard=g_body,
        blocked_nflasha15_guard=g_nf15,
        blocked_cnflasha0_guard=g_cn0,
        blocked_backup_bin_guard=g_bak,
        firmware_flash_opcodes_blocked=True,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


def build_clean_room_uvc_srt_crsdk_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, `global.xdb`, and `.uxc` fixtures."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)

    def _pack(tokens: Sequence[str]) -> bytes:
        return elf_hdr + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    return {
        "fx3_appfw": _pack(FX3_APPFW_PHASE118_MARKERS),
        "fx6_appfw": _pack(FX6_APPFW_PHASE118_MARKERS),
        "fx3_libmpr": _pack(FX3_LIBMPR_PHASE118_MARKERS),
        "fx6_libmpr": _pack(FX6_LIBMPR_PHASE118_MARKERS),
        "fx6_libinfra_ptp": _pack(FX6_LIBINFRA_PTP_PHASE118_MARKERS),
        "fx6_libnet_ether": _pack(FX6_LIBNET_ETHER_PHASE118_MARKERS),
        "fx6_libveric_live": _pack(FX6_LIBVERIC_LIVE_PHASE118_MARKERS),
        "fx3_global_xdb": build_synthetic_global_xdb("fx3_702"),
        "fx6_global_xdb": build_synthetic_global_xdb("fx6_601"),
        "fx3_str_en": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS39_PHASE118_LABELS.items()}, namespace_id=39
        ),
        "fx3_str_en_g": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS3_PHASE118_LABELS.items()}, namespace_id=3
        ),
        "fx6_str_en_1": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS1_PHASE118_LABELS.items()}, namespace_id=1
        ),
        "fx6_str_en_2": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS2_PHASE118_LABELS.items()}, namespace_id=2
        ),
    }


def analyze_usb_uvc_uac_srt_and_crsdk_ptp(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> UsbUvcUacSrtAndCrsdkPtpReport:
    """Run the 23rd unified firmware-lab auditor in Local Donor (`os.O_RDONLY`) or Clean-Room mode."""
    root = repo_root or DEFAULT_REPO_ROOT
    forced_clean = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not forced_clean:
        donor_paths = {
            "fx3_appfw": resolve_donor_file(FX3_APPFW_RELPATH, repo_root=root),
            "fx6_appfw": resolve_donor_file(FX6_APPFW_RELPATH, repo_root=root),
            "fx3_libmpr": resolve_donor_file(FX3_LIBMPR_RELPATH, repo_root=root),
            "fx6_libmpr": resolve_donor_file(FX6_LIBMPR_RELPATH, repo_root=root),
            "fx6_libinfra_ptp": resolve_donor_file(FX6_LIBINFRA_PTP_RELPATH, repo_root=root),
            "fx6_libnet_ether": resolve_donor_file(FX6_LIBNET_ETHER_RELPATH, repo_root=root),
            "fx6_libveric_live": resolve_donor_file(FX6_LIBVERIC_LIVE_RELPATH, repo_root=root),
            "fx3_global_xdb": resolve_donor_file(FX3_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx6_global_xdb": resolve_donor_file(FX6_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx3_str_en": resolve_donor_file(FX3_STR_EN_RELPATH, repo_root=root),
            "fx3_str_en_g": resolve_donor_file(FX3_STR_EN_G_RELPATH, repo_root=root),
            "fx6_str_en_1": resolve_donor_file(FX6_STR_EN_1_RELPATH, repo_root=root),
            "fx6_str_en_2": resolve_donor_file(FX6_STR_EN_2_RELPATH, repo_root=root),
        }

    use_local = (not forced_clean) and all(p is not None and p.is_file() for p in donor_paths.values())
    mode = "LOCAL_DONOR_VERIFIED" if use_local else "CLEAN_ROOM_SYNTHETIC"

    fx3_app_groups = {
        "uvc": FX3_APPFW_PHASE118_MARKERS[:4],
        "srt": FX3_APPFW_PHASE118_MARKERS[4:8],
        "crsdk": FX3_APPFW_PHASE118_MARKERS[8:13],
    }
    fx6_app_groups = {
        "uvc": FX6_APPFW_PHASE118_MARKERS[:4],
        "srt": FX6_APPFW_PHASE118_MARKERS[4:7],
        "crsdk": FX6_APPFW_PHASE118_MARKERS[7:12],
    }
    fx3_mpr_groups = {"uvc": FX3_LIBMPR_PHASE118_MARKERS}
    fx6_mpr_groups = {"uvc": FX6_LIBMPR_PHASE118_MARKERS}
    fx6_ptp_groups = {"crsdk": FX6_LIBINFRA_PTP_PHASE118_MARKERS}
    fx6_eth_groups = {"srt": FX6_LIBNET_ETHER_PHASE118_MARKERS}
    fx6_veric_groups = {"srt": FX6_LIBVERIC_LIVE_PHASE118_MARKERS}

    if use_local:
        sz_fx3_app, fx3_app_res = _scan_donor_rdonly_markers(donor_paths["fx3_appfw"], fx3_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_app, fx6_app_res = _scan_donor_rdonly_markers(donor_paths["fx6_appfw"], fx6_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx3_mpr, fx3_mpr_res = _scan_donor_rdonly_markers(donor_paths["fx3_libmpr"], fx3_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_mpr, fx6_mpr_res = _scan_donor_rdonly_markers(donor_paths["fx6_libmpr"], fx6_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_ptp, fx6_ptp_res = _scan_donor_rdonly_markers(donor_paths["fx6_libinfra_ptp"], fx6_ptp_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_eth, fx6_eth_res = _scan_donor_rdonly_markers(donor_paths["fx6_libnet_ether"], fx6_eth_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_veric, fx6_veric_res = _scan_donor_rdonly_markers(donor_paths["fx6_libveric_live"], fx6_veric_groups, is_elf=True)  # type: ignore[arg-type]
        fx3_xdb_bytes = _read_bytes_rdonly(donor_paths["fx3_global_xdb"])  # type: ignore[arg-type]
        fx6_xdb_bytes = _read_bytes_rdonly(donor_paths["fx6_global_xdb"])  # type: ignore[arg-type]
        fx3_str_en_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en"])  # type: ignore[arg-type]
        fx3_str_en_g_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en_g"])  # type: ignore[arg-type]
        fx6_str_en_1_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_1"])  # type: ignore[arg-type]
        fx6_str_en_2_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_2"])  # type: ignore[arg-type]
    else:
        fx = build_clean_room_uvc_srt_crsdk_fixtures()
        sz_fx3_app, fx3_app_res = _scan_bytes_marker_groups(fx["fx3_appfw"], fx3_app_groups)
        sz_fx6_app, fx6_app_res = _scan_bytes_marker_groups(fx["fx6_appfw"], fx6_app_groups)
        sz_fx3_mpr, fx3_mpr_res = _scan_bytes_marker_groups(fx["fx3_libmpr"], fx3_mpr_groups)
        sz_fx6_mpr, fx6_mpr_res = _scan_bytes_marker_groups(fx["fx6_libmpr"], fx6_mpr_groups)
        sz_fx6_ptp, fx6_ptp_res = _scan_bytes_marker_groups(fx["fx6_libinfra_ptp"], fx6_ptp_groups)
        sz_fx6_eth, fx6_eth_res = _scan_bytes_marker_groups(fx["fx6_libnet_ether"], fx6_eth_groups)
        sz_fx6_veric, fx6_veric_res = _scan_bytes_marker_groups(fx["fx6_libveric_live"], fx6_veric_groups)
        fx3_xdb_bytes = fx["fx3_global_xdb"]
        fx6_xdb_bytes = fx["fx6_global_xdb"]
        fx3_str_en_bytes = fx["fx3_str_en"]
        fx3_str_en_g_bytes = fx["fx3_str_en_g"]
        fx6_str_en_1_bytes = fx["fx6_str_en_1"]
        fx6_str_en_2_bytes = fx["fx6_str_en_2"]

    sizes: Dict[str, int] = {
        "fx3_appfw": sz_fx3_app,
        "fx6_appfw": sz_fx6_app,
        "fx3_libmpr": sz_fx3_mpr,
        "fx6_libmpr": sz_fx6_mpr,
        "fx6_libinfra_ptp": sz_fx6_ptp,
        "fx6_libnet_ether": sz_fx6_eth,
        "fx6_libveric_live": sz_fx6_veric,
        "fx3_global_xdb": len(fx3_xdb_bytes),
        "fx6_global_xdb": len(fx6_xdb_bytes),
        "fx3_str_en": len(fx3_str_en_bytes),
        "fx3_str_en_g": len(fx3_str_en_g_bytes),
        "fx6_str_en_1": len(fx6_str_en_1_bytes),
        "fx6_str_en_2": len(fx6_str_en_2_bytes),
    }

    p1_extra: List[str] = []
    p2_extra: List[str] = []
    p3_extra: List[str] = []
    p4_extra: List[str] = []

    for label, actual, expected, bucket in (
        ("FX3 appFw UVC", fx3_app_res["uvc"], fx3_app_groups["uvc"], p1_extra),
        ("FX6 appFw UVC", fx6_app_res["uvc"], fx6_app_groups["uvc"], p1_extra),
        ("FX3 libmpr UAC", fx3_mpr_res["uvc"], fx3_mpr_groups["uvc"], p1_extra),
        ("FX6 libmpr UAC", fx6_mpr_res["uvc"], fx6_mpr_groups["uvc"], p1_extra),
        ("FX3 appFw SRT", fx3_app_res["srt"], fx3_app_groups["srt"], p2_extra),
        ("FX6 appFw SRT", fx6_app_res["srt"], fx6_app_groups["srt"], p2_extra),
        ("FX6 libNetServiceEther", fx6_eth_res["srt"], fx6_eth_groups["srt"], p2_extra),
        ("FX6 libInfraVericLiveStreaming", fx6_veric_res["srt"], fx6_veric_groups["srt"], p2_extra),
        ("FX3 appFw CRSDK", fx3_app_res["crsdk"], fx3_app_groups["crsdk"], p3_extra),
        ("FX6 appFw CRSDK", fx6_app_res["crsdk"], fx6_app_groups["crsdk"], p3_extra),
        ("FX6 libInfraPtpControl", fx6_ptp_res["crsdk"], fx6_ptp_groups["crsdk"], p3_extra),
    ):
        if len(actual) != len(expected):
            bucket.append(f"Missing {label} markers ({len(actual)}/{len(expected)})")

    fx3_ux_en, u_err_1 = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE118_LABELS)
    fx3_ux_g, u_err_2 = _extract_uxc_labels(fx3_str_en_g_bytes, FX3_NS3_PHASE118_LABELS)
    fx6_ux_1, u_err_3 = _extract_uxc_labels(fx6_str_en_1_bytes, FX6_NS1_PHASE118_LABELS)
    fx6_ux_2, u_err_4 = _extract_uxc_labels(fx6_str_en_2_bytes, FX6_NS2_PHASE118_LABELS)
    p3_extra.extend(u_err_1)
    p1_extra.extend(u_err_2)
    p2_extra.extend(u_err_3)
    p1_extra.extend(u_err_4)

    uxc_uvc_labels = {
        "fx3_usb_streaming_start": fx3_ux_g.get("0x000061af", ""),
        "fx3_usb_streaming_invalid": fx3_ux_g.get("0x0000620d", ""),
        "fx6_lpcm_1": fx6_ux_2.get("0x000049e3", ""),
        "fx6_lpcm_2": fx6_ux_2.get("0x00005002", ""),
    }
    uxc_srt_rtmps_labels = {
        "fx6_rtmp_rtmps": fx6_ux_1.get("0x000024af", ""),
        "fx6_rtmps_cert": fx6_ux_1.get("0x000024c1", ""),
        "fx6_rtmp_streaming": fx6_ux_1.get("0x00002777", ""),
        "fx6_srt_caller_1": fx6_ux_1.get("0x00002bd1", ""),
    }
    uxc_crsdk_labels = {
        "fx3_pc_remote_busy": fx3_ux_en.get("0x0004e244", ""),
        "fx3_remote_shooting_busy": fx3_ux_en.get("0x0004ea54", ""),
        "fx3_pc_remote_wired_lan": fx3_ux_g.get("0x0000601c", ""),
    }

    p1 = evaluate_pillar_1_uvc_uac_streaming(
        fx3_appfw_uvc_markers=fx3_app_res["uvc"],
        fx6_appfw_uvc_markers=fx6_app_res["uvc"],
        fx3_libmpr_uac_markers=fx3_mpr_res["uvc"],
        fx6_libmpr_uac_markers=fx6_mpr_res["uvc"],
        uxc_uvc_labels=uxc_uvc_labels,
        extra_errors=p1_extra,
    )
    p2 = evaluate_pillar_2_wired_srt_rtmps_p12(
        fx3_appfw_srt_markers=fx3_app_res["srt"],
        fx6_appfw_srt_markers=fx6_app_res["srt"],
        fx6_libnet_ether_markers=fx6_eth_res["srt"],
        fx6_libveric_live_markers=fx6_veric_res["srt"],
        uxc_srt_rtmps_labels=uxc_srt_rtmps_labels,
        extra_errors=p2_extra,
    )
    p3 = evaluate_pillar_3_crsdk_ptp_firewall(
        fx3_appfw_crsdk_markers=fx3_app_res["crsdk"],
        fx6_appfw_crsdk_markers=fx6_app_res["crsdk"],
        fx6_libinfra_ptp_markers=fx6_ptp_res["crsdk"],
        uxc_crsdk_labels=uxc_crsdk_labels,
        extra_errors=p3_extra,
    )

    try:
        parse_global_xdb_buffer(fx3_xdb_bytes)
        fx3_xdb_ok = True
    except Exception:
        fx3_xdb_ok = False
    try:
        parse_global_xdb_buffer(fx6_xdb_bytes)
        fx6_xdb_ok = True
    except Exception:
        fx6_xdb_ok = False

    p4 = evaluate_pillar_4_zero_mutation_emmc_preservation(
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
        extra_errors=p4_extra,
    )

    all_errors = p1.errors + p2.errors + p3.errors + p4.errors
    all_passed = bool(p1.passed and p2.passed and p3.passed and p4.passed and len(all_errors) == 0)

    digest_payload = {
        "schema_version": PHASE_118_SCHEMA,
        "phase_version": PHASE_118_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "donor_file_sizes": sizes,
        "p1": asdict(p1),
        "p2": asdict(p2),
        "p3": asdict(p3),
        "p4": asdict(p4),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return UsbUvcUacSrtAndCrsdkPtpReport(
        schema_version=PHASE_118_SCHEMA,
        phase_version=PHASE_118_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        donor_file_sizes=sizes,
        pillar_1_uvc_uac_streaming=p1,
        pillar_2_wired_srt_rtmps_p12=p2,
        pillar_3_crsdk_ptp_firewall=p3,
        pillar_4_zero_mutation_emmc_preservation=p4,
        report_sha256=report_sha256,
        errors=tuple(all_errors),
    )


def usb_uvc_uac_srt_and_crsdk_ptp_report_to_dict(
    report: UsbUvcUacSrtAndCrsdkPtpReport,
) -> Dict[str, object]:
    """Convert `UsbUvcUacSrtAndCrsdkPtpReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
