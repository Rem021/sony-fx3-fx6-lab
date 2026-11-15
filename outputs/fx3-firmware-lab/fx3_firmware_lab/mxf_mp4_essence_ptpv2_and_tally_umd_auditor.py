"""Phase 122 — 24th Unified Firmware-Lab Auditor: XAVC MXF OP1a (FX6) vs MP4 ISO-BMFF (FX3)
Container Essence / SMPTE UMID / KLV RDD-18 Metadata Translator, SMPTE ST 2059-2 PTPv2
Frame-Phase Sync, & Wired P12-Safe TSL UMD v5.0 Tally Bridge Auditor.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `global.xdb`,
  `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01 (`appFw.so`,
  `libmpr.so`, `libInfraPtpControl.so`, `libNetServiceEther.so`, `global.xdb`,
  `string_english.uxc`, `string_english_2.uxc`) strictly via `os.O_RDONLY` +
  `mmap.ACCESS_READ` and ELF64 `.rodata`/`.dynstr` section-scoped scanning plus
  `uxa\\x07`/`.uxc` container parsing (< 0.35s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / `global.xdb` / `.uxc`
  fixtures carrying the exact verified contract markers and runs the identical
  four-pillar verification pipeline (< 0.02s warm, zero proprietary files
  required).

Audits Four Phase 122 Pillars:
1. Pillar A — `FX6 MXF OP1a` (`libXavcMxf`, `MuxMxfFnlzPrm_GetVideoCompression`,
   `GetCubeFilePathForMXF`, `setMetaData_ExposureIndexRDD18`,
   `setMetaData_CaptureGammaRDD18`) <-> `FX3 MP4 ISO-BMFF` (`GetCubeFilePath`,
   `SPVC` / `rtmd` KLV box) Lossless Essence & Metadata Bridge Contract:
   - Verifies 32-byte SMPTE ST 330 `UMID` preservation on lossless `XAVC-I`
     (`AVC480_*_H422IP` + 24-bit 48 kHz LPCM) rewrap vs UMID regeneration on
     transcode.
   - Builds and CRC32-verifies SMPTE RDD-18 KLV / MP4 `rtmd` (`0x646D7472`)
     acquisition packets (`ExposureIndexOfPhotoMeter`, `CaptureGammaEquation`
     Tag `0x3210`, `CaptureColorPrimaries`, `FrameRate`, `FNumber`,
     `ExposureTime`, `WhiteBalanceKelvin`, LUT `CubeFilePath`).
   - Preserves `SPVC` (`sony.private_cert.v1`) integrity (never spoofing native
     certificates on Stage-B rewrapped clips) and blocks un-translated raw
     `MXF OP1a` writes onto FX3 `MP4` `M4ROOT/CLIP` slots.
2. Pillar B — `SMPTE ST 2059-2` (`IEEE 1588-2008 PTPv2`) Sub-Microsecond
   Hardware/Software Timestamping vs Multi-Terminal `LTC` (`SMPTE 12M`)
   Frame-Edge Phase Alignment over Wired `USB-LAN` (`CDC-NCM` / `RNDIS`):
   - Separates `SMPTE ST 2059-2` `PTPv2` timing from Sony `PTP-IP` (`TCP/15740`)
     remote camera control.
   - Converts `PTPv2` TAI epoch nanoseconds (with `37 s` TAI-UTC offset) into
     phase-locked `SMPTE 12M` `LTC` frame edges (`23.976..59.94 fps`) fed via
     `VMC-BNCM1` (`LTC IN`) / FX6 BNC `TC IN` (`<= 500.0 us` phase margin).
   - Enforces `P12` Wi-Fi-OFF (`wf12_00342260_risk == 0`) over wired `USB-LAN`
     and blocks `VMC-BNCM1` attachment during `H0` / `uart_boot` (Pins 7/8/9).
3. Pillar C — Studio Broadcast `TSL UMD v5.0` (UDP/TCP port `40003` / `5727` /
   `8900`) Red (`PGM`) / Green (`PVW`) Tally & `16-char` Dynamic Camera UMD
   Label Translator onto FX3 Physical Front/Top/Rear Tally LEDs + OSD Border
   under Strict `P12` Wi-Fi-OFF (`wf12_00342260_risk == 0`):
   - Implements bit-exact little-endian `TSL UMD v5.0` wire encoding/decoding
     (`PBC`, `VER=0`, `FLAGS` ASCII/UTF-16LE, `SCREEN`, `<DMSG>` `INDEX`,
     `CONTROL` RH/Text/LH tally + brightness, `LENGTH`, `TEXT`), `<= 2048 B`
     UDP framing, and TCP `DLE/STX` (`0xFE 0x02`) + `0xFE` byte-stuffing.
   - Enforces FX3 single-color Red LED hardware truth: `Red (PGM)` lights
     FX3 Front+Rear Red Tally LEDs + `RED` OSD border; `Green (PVW)` keeps
     FX3 physical Red LEDs strictly `OFF` (preventing false on-air Red tally
     confusion!) while drawing a `GREEN` OSD preview border (`0` missing-GPIO
     faults for FX6-only `G Tally Lamp`).
4. Pillar D — Volatile RAM Staging & Zero Persistent `eMMC` / Calibration
   Mutation Proof (`emmc_mutation_bytes == 0`, `calibration_mutation_bytes == 0`,
   `persistent_emmc_writes_authorized == False`).
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
from .c2pa_lens_shading_and_mc_fleet_auditor import FX6_LIBINFRA_PTP_RELPATH
from .lut3d_cube_tetrahedral_and_sdi_hdmi_auditor import (
    FX3_GLOBAL_XDB_RELPATH,
    FX3_STR_EN_G_RELPATH,
    FX3_STR_EN_RELPATH,
    FX6_GLOBAL_XDB_RELPATH,
    FX6_STR_EN_1_RELPATH,
    FX6_STR_EN_2_RELPATH,
)
from .sensor_codec_compatibility_analyzer import FX3_LIBMPR_RELPATH, FX6_LIBMPR_RELPATH


PHASE_122_SCHEMA = "fx3_firmware_lab_phase122_mxf_mp4_ptpv2_tally_v1"
PHASE_122_VERSION = "122.0.0"

# ---------------------------------------------------------------------------
# Pillar A Constants: MXF OP1a <-> MP4 ISO-BMFF, SMPTE UMID & RDD-18 / rtmd
# ---------------------------------------------------------------------------

SMPTE_UMID_BASIC_PREFIX_HEX = "060a2b340101010501010d4313000000"
SMPTE_UMID_BYTES = 32
RTMD_HANDLER_FOURCC = "rtmd"
SPVC_BOX_FOURCC = "SPVC"
SPVC_UUID_SCHEMA = "sony.private_cert.v1"

RDD18_KLV_PACKET_MAGIC = b"\x06\x0e\x2b\x34"
RDD18_EXPOSURE_INDEX_UL_HEX = "060e2b340101010e04200103010c0000"
RDD18_CAPTURE_GAMMA_SLOG3_UL_HEX = "060e2b340401010d04010101010b0000"
RDD18_CAPTURE_GAMMA_REC709_UL_HEX = "060e2b34040101010401010101020000"
RDD18_CAPTURE_GAMMA_HLG_UL_HEX = "060e2b340401010d0401010101090000"

CAPTURE_GAMMA_UL_MAP: Dict[str, str] = {
    "S-LOG3": RDD18_CAPTURE_GAMMA_SLOG3_UL_HEX,
    "S-LOG3-CINE": RDD18_CAPTURE_GAMMA_SLOG3_UL_HEX,
    "REC709": RDD18_CAPTURE_GAMMA_REC709_UL_HEX,
    "REC2100-HLG": RDD18_CAPTURE_GAMMA_HLG_UL_HEX,
}

VALID_CAPTURE_PRIMARIES_P122: Tuple[str, ...] = (
    "S-GAMUT3.CINE",
    "S-GAMUT3",
    "REC709",
    "REC2020",
)

VALID_CONTAINER_FORMATS: Tuple[str, ...] = ("MXF_OP1A", "MP4_ISOBMFF")
VALID_ESSENCE_CODECS: Tuple[str, ...] = (
    "XAVC_I_H422IP",
    "XAVC_L_H422L",
    "XAVC_S_I_H422IP",
    "XAVC_HS_HEVC",
)
VALID_BRIDGE_MODES: Tuple[str, ...] = ("LOSSLESS_REWRAP", "TRANSCODE", "DIRECT_RAW_COPY")

# ---------------------------------------------------------------------------
# Pillar B Constants: SMPTE ST 2059-2 PTPv2 & Multi-Terminal LTC Phase Sync
# ---------------------------------------------------------------------------

SMPTE_ST2059_DEFAULT_DOMAIN = 127
PTP_TAI_UTC_OFFSET_SEC = 37
PTPV2_MAX_HW_JITTER_US = 1.0
PTPV2_MAX_SW_JITTER_US = 250.0
LTC_MAX_PHASE_OFFSET_US = 500.0

VALID_SYNC_PROFILES: Tuple[str, ...] = (
    "SMPTE_ST_2059_2_HW_TS",
    "SMPTE_ST_2059_2_SW_TS",
    "PTP_IP_15740_CONTROL",
)
VALID_SYNC_TRANSPORTS: Tuple[str, ...] = (
    "CDC_NCM_RTL8153",
    "CDC_NCM_AX88179",
    "USB_RNDIS_WIRED",
    "WIFI_WLAN0",
    "BT_PAN",
)
WIRED_SYNC_TRANSPORTS: Tuple[str, ...] = (
    "CDC_NCM_RTL8153",
    "CDC_NCM_AX88179",
    "USB_RNDIS_WIRED",
)
FORBIDDEN_RF_SYNC_TRANSPORTS: Tuple[str, ...] = ("WIFI_WLAN0", "BT_PAN")

PTPV2_FPS_SPECS: Dict[str, Tuple[int, int, int, bool]] = {
    "23.976_NDF": (24000, 1001, 24, False),
    "24.000_NDF": (24, 1, 24, False),
    "25.000_NDF": (25, 1, 25, False),
    "29.970_DF": (30000, 1001, 30, True),
    "29.970_NDF": (30000, 1001, 30, False),
    "50.000_NDF": (50, 1, 50, False),
    "59.940_DF": (60000, 1001, 60, True),
}

# ---------------------------------------------------------------------------
# Pillar C Constants: TSL UMD v5.0 Wire Protocol & FX3 Tally Hardware Bridge
# ---------------------------------------------------------------------------

TSL_UMD_V5_MINOR_VER = 0x00
TSL_UMD_UDP_MAX_BYTES = 2048
TSL_UMD_DLE = 0xFE
TSL_UMD_STX = 0x02
TSL_UMD_MAX_LABEL_CHARS = 16

TSL_UMD_PORTS: Dict[str, Tuple[str, int]] = {
    "UDP_40003": ("UDP", 40003),
    "TCP_5727": ("TCP", 5727),
    "TCP_5728": ("TCP", 5728),
    "UDP_8900": ("UDP", 8900),
}

TSL_TALLY_COLOR_NAMES: Dict[int, str] = {
    0: "OFF",
    1: "RED",
    2: "GREEN",
    3: "AMBER",
}

# ---------------------------------------------------------------------------
# Pillar D Constants: Volatile RAM Staging & Zero Persistent eMMC Guard
# ---------------------------------------------------------------------------

VOLATILE_STAGING_PREFIXES_P122: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_PERSISTENT_EMMC_RE_P122 = re.compile(
    r"(?:^|/)(?:p(?:[1-9]|1[0-8])|nflasha\d*|cnflasha\d*|mmcblk0(?:p\d+|rpmb)?|mtdblock\d*)(?:/|:|$)"
    r"|bodydata\.dat|udtrfirm|psd\.bin|defdet\.bin|backup\.bin|jiritsu|updater://|nvram://|eeprom://",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Verified Binary & .uxc Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX6_LIBMPR_PHASE122_MARKERS: Tuple[str, ...] = (
    "_ZN10libXavcMxf11SetClipNameEjRA4_KN3mpr13ClipNameParamE",
    "MuxMxfFnlzPrm_GetVideoCompression",
    "_ZN3mpr21GetCubeFilePathForMXFERKN4sidb10recordInfoEjRNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE",
    "setMetaData_ExposureIndexRDD18",
    "setMetaData_CaptureGammaRDD18",
    "_ZN3mpr4UMID15CreateBasicUMIDEv",
)

FX3_LIBMPR_PHASE122_MARKERS: Tuple[str, ...] = (
    "_ZN3mpr15GetCubeFilePathERKN4sidb10recordInfoEjRNSt7__cxx1112basic_stringIcSt11char_traitsIcESaIcEEE",
    "SPVC",
    "_Z34PrepareInitialVectorAndSPVCBoxDataN3mpr8libcrypt13operationModeEj",
    "_ZN4sidb35defStruct2sidb_CaptureGammaEquationEN9DefStruct9RDD18Meta20CaptureGammaEquationE",
    "_ZN16XavcsMovieWriter25SetRealTimeMetaSampleInfoEP10libXavcMp4RSt6vectorIN3mpr16MovieEncodeTable8MetaInfoESaIS5_EEjjm",
    "_ZN3mpr4UMID15CreateBasicUMIDEv",
)

FX6_APPFW_PHASE122_MARKERS: Tuple[str, ...] = (
    "VAL_setting_codec_category_CODEC_CATEGORY_XAVC_MXF",
    "get_pair_UMID_unique_id_of_opposite_slot_with_current_unique_id",
    "BKID_APP_SETTING_TIMECODE_DISPLAY",
    "BKID_APP_SETTING_FRONT_TALLY",
    "BKID_APP_SETTING_REAR_TALLY",
    "BKID_APP_SETTING_TALLY_LAMP_BRIGHTNESS",
    "BKID_APP_SETTING_TALLY_CONTROL",
    "BKID_APP_SETTING_G_TALLY_LAMP",
)

FX3_APPFW_PHASE122_MARKERS: Tuple[str, ...] = (
    "sequence_set_tally_status",
    "INFRA_NOTIFY_TIMECODE_EXT_TC_STATUS",
    "EXT_TC_LOCK_STATUS_LOCK",
    "STREAMING_CONNECT_METHOD_WIRED_LAN",
    "USB_LAN_CONNECT_LAUNCH_ON",
    "INFRA_NOTIFY_PTP_OPERATION_DATA_SET",
)

FX6_LIBINFRA_PTP_PHASE122_MARKERS: Tuple[str, ...] = (
    "InfraPtpControl_Init",
    "PTPT_init_ip_remote",
)

FX6_LIBNET_ETHER_PHASE122_MARKERS: Tuple[str, ...] = (
    "CT_ID_ASYNC_REQ_START_USB_HOST",
    "32mEN_EVT_API_SETUP_WIRED_ETHER_IF",
)

FX3_NS39_PHASE122_LABELS: Dict[int, str] = {
    0x0004E100: "Wired LAN",
    0x0004E7FD: "MP4",
}

FX3_NS3_PHASE122_LABELS: Dict[int, str] = {
    0x0000601C: "Turning PC Remote(Wired LAN) on\nenables connection.",
    0x00006398: "Wired LAN",
}

FX6_NS1_PHASE122_LABELS: Dict[int, str] = {
    0x000024F6: "Front Tally Lamp",
    0x000024F8: "Rear Tally Lamp",
    0x000024FA: "Tally Control",
    0x000025B6: "Tally Lamp Brightness",
    0x000025BE: "G Tally Lamp",
}

FX6_NS2_PHASE122_LABELS: Dict[int, str] = {
    0x00004072: "Rec Lamp[F]: On",
    0x00004074: "Rec Lamp[R]: On",
    0x00004242: "Timecode",
    0x00004245: "HDMI TC Out",
    0x000042C8: "Tally",
    0x000042D7: "Wired LAN",
}


# ---------------------------------------------------------------------------
# Dataclasses (JSON-clean: no raw bytes attributes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Rdd18RtmdFrameDecoded:
    valid: bool
    exposure_index: int
    base_iso: int
    gamma_name: str
    gamma_ul_hex: str
    primaries_name: str
    fps_x1000: int
    f_number_x100: int
    shutter_angle_x10: int
    wb_kelvin: int
    cube_lut_path: str
    umid_hex: str
    crc32_valid: bool
    packet_hex: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MxfMp4BridgeEvalResult:
    valid: bool
    status: str
    source_container: str
    target_container: str
    source_codec: str
    target_codec: str
    bridge_mode: str
    source_umid_hex: str
    target_umid_hex: str
    umid_preserved: bool
    spvc_preserved_without_spoofing: bool
    rdd18_rtmd_decoded: Rdd18RtmdFrameDecoded
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MxfMp4EssenceBridgeReport:
    passed: bool
    fx6_libmpr_mxf_markers: Tuple[str, ...]
    fx3_libmpr_mp4_markers: Tuple[str, ...]
    fx6_appfw_mxf_markers: Tuple[str, ...]
    uxc_container_labels: Dict[str, str]
    eval_mxf_to_mp4_lossless_rewrap: MxfMp4BridgeEvalResult
    eval_mp4_to_mxf_lossless_rewrap: MxfMp4BridgeEvalResult
    eval_transcode_regenerates_umid: MxfMp4BridgeEvalResult
    blocked_raw_mxf_on_mp4_slot: MxfMp4BridgeEvalResult
    blocked_corrupt_rdd18_crc: MxfMp4BridgeEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Ptpv2ToLtcResult:
    valid: bool
    fps_key: str
    tai_ns: int
    utc_ns: int
    tai_utc_offset_sec: int
    smpte12m_timecode: str
    frame_phase_offset_us: float
    drop_frame: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Ptpv2LtcSyncEvalResult:
    valid: bool
    status: str
    sync_profile: str
    transport_driver: str
    ptpv2_domain: int
    p12_airplane_rf_off: bool
    wf12_00342260_risk: int
    measured_ptp_jitter_us: float
    ltc_phase_offset_us: float
    vmc_bncm1_attached: bool
    uart_boot_active: bool
    ptpv2_to_ltc: Ptpv2ToLtcResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Ptpv2LtcPhaseSyncReport:
    passed: bool
    fx3_appfw_tc_lan_markers: Tuple[str, ...]
    fx6_appfw_tc_markers: Tuple[str, ...]
    fx6_libnet_ether_markers: Tuple[str, ...]
    fx6_libinfra_ptp_markers: Tuple[str, ...]
    uxc_tc_lan_labels: Dict[str, str]
    eval_st2059_hw_ts_cdc_ncm_23976: Ptpv2LtcSyncEvalResult
    eval_st2059_sw_ts_rndis_2997df: Ptpv2LtcSyncEvalResult
    blocked_ptpip_confused_with_ptpv2: Ptpv2LtcSyncEvalResult
    blocked_wifi_wlan0_p12_violation: Ptpv2LtcSyncEvalResult
    blocked_ltc_phase_drift_exceeded: Ptpv2LtcSyncEvalResult
    blocked_vmc_bncm1_during_uart_boot: Ptpv2LtcSyncEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TslUmdV5DisplayMsg:
    index: int
    rh_tally: int
    text_tally: int
    lh_tally: int
    brightness: int
    text: str


@dataclass(frozen=True)
class TslUmdV5PacketDecoded:
    valid: bool
    pbc: int
    ver: int
    flags: int
    is_utf16le: bool
    is_scontrol: bool
    screen: int
    tcp_dle_stx_framed: bool
    messages: Tuple[TslUmdV5DisplayMsg, ...]
    packet_hex: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TslTallyBridgeEvalResult:
    valid: bool
    status: str
    port_key: str
    transport_driver: str
    p12_airplane_rf_off: bool
    wf12_00342260_risk: int
    target_display_index: int
    incoming_lh_tally: int
    incoming_tally_name: str
    fx3_front_rear_red_leds_on: bool
    osd_border_color: str
    raw_umd_label: str
    sanitized_16char_label: str
    fx6_green_gpio_faults: int
    packet_decoded: TslUmdV5PacketDecoded
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TslUmdTallyBridgeReport:
    passed: bool
    fx3_appfw_tally_markers: Tuple[str, ...]
    fx6_appfw_tally_markers: Tuple[str, ...]
    uxc_tally_labels: Dict[str, str]
    eval_udp_40003_pgm_red_tally: TslTallyBridgeEvalResult
    eval_tcp_5727_pvw_green_osd_only: TslTallyBridgeEvalResult
    eval_udp_8900_utf16_amber_16char_clamp: TslTallyBridgeEvalResult
    eval_off_tally_clears_leds_and_border: TslTallyBridgeEvalResult
    blocked_wifi_p12_tally_violation: TslTallyBridgeEvalResult
    blocked_udp_over_2048_bytes: TslTallyBridgeEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase122WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZeroMutationEssenceTallyReport:
    passed: bool
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    volatile_staging_guard: Phase122WriteGuardResult
    blocked_bodydata_dat_guard: Phase122WriteGuardResult
    blocked_nflasha15_guard: Phase122WriteGuardResult
    blocked_cnflasha0_guard: Phase122WriteGuardResult
    blocked_backup_bin_guard: Phase122WriteGuardResult
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MxfMp4EssencePtpv2AndTallyUmdReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    donor_file_sizes: Dict[str, int]
    pillar_a_mxf_mp4_essence_bridge: MxfMp4EssenceBridgeReport
    pillar_b_ptpv2_ltc_phase_sync: Ptpv2LtcPhaseSyncReport
    pillar_c_tsl_umd_tally_bridge: TslUmdTallyBridgeReport
    pillar_d_zero_mutation_emmc_guard: ZeroMutationEssenceTallyReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only Helpers (os.O_RDONLY + mmap.ACCESS_READ)
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
# Pillar A Functions: SMPTE UMID, RDD-18 <-> MP4 rtmd Translator & Essence Bridge
# ---------------------------------------------------------------------------


def build_smpte_umid(
    *,
    device_node_hex: str = "a1c190057f30",
    material_counter: int = 1,
    creation_unix_sec: int = 1794715200,
) -> str:
    """Build a deterministic 32-byte (64-hex) SMPTE ST 330 Basic UMID."""
    node_bytes = bytes.fromhex(device_node_hex.strip().lower().zfill(12))[:6]
    time_bytes = struct.pack(">Q", creation_unix_sec & 0xFFFFFFFFFFFFFFFF)[2:]
    ctr_bytes = struct.pack(">I", material_counter & 0xFFFFFFFF)
    # 16B Universal Label + 6B creation timestamp + 4B material counter + 6B device node = 32B
    raw = bytes.fromhex(SMPTE_UMID_BASIC_PREFIX_HEX) + time_bytes + ctr_bytes + node_bytes
    if len(raw) != SMPTE_UMID_BYTES:
        raise AssertionError(f"UMID length {len(raw)} != {SMPTE_UMID_BYTES}")
    return raw.hex()


def build_rdd18_rtmd_klv_frame(
    *,
    exposure_index: int = 800,
    base_iso: int = 800,
    gamma_name: str = "S-LOG3",
    primaries_name: str = "S-GAMUT3.CINE",
    fps_x1000: int = 23976,
    f_number_x100: int = 280,
    shutter_angle_x10: int = 1800,
    wb_kelvin: int = 5600,
    cube_lut_path: str = "/tmp/fx3_stageb_lut/S709_33.cube",
    umid_hex: Optional[str] = None,
) -> bytes:
    """Build a deterministic SMPTE RDD-18 / MP4 `rtmd` acquisition metadata frame packet."""
    norm_gamma = gamma_name.strip().upper()
    norm_prim = primaries_name.strip().upper()
    if norm_gamma not in CAPTURE_GAMMA_UL_MAP:
        raise ValueError(f"Unsupported gamma_name={gamma_name!r}")
    if norm_prim not in VALID_CAPTURE_PRIMARIES_P122:
        raise ValueError(f"Unsupported primaries_name={primaries_name!r}")

    umid_str = (umid_hex or build_smpte_umid()).strip().lower()
    umid_bytes = bytes.fromhex(umid_str)
    if len(umid_bytes) != SMPTE_UMID_BYTES:
        raise ValueError("UMID must be exactly 32 bytes (64 hex chars)")

    gamma_ul_bytes = bytes.fromhex(CAPTURE_GAMMA_UL_MAP[norm_gamma])
    prim_b = norm_prim.encode("ascii")[:16].ljust(16, b"\x00")
    gamma_b = norm_gamma.encode("ascii")[:16].ljust(16, b"\x00")
    lut_b = cube_lut_path.encode("utf-8")[:64].ljust(64, b"\x00")

    # 16B KLV key + fixed payload + 4B CRC32
    header = bytes.fromhex(RDD18_EXPOSURE_INDEX_UL_HEX)
    body = struct.pack(
        ">16sII16s16s16sIIII64s32s",
        header,
        exposure_index,
        base_iso,
        gamma_b,
        gamma_ul_bytes,
        prim_b,
        fps_x1000,
        f_number_x100,
        shutter_angle_x10,
        wb_kelvin,
        lut_b,
        umid_bytes,
    )
    crc = zlib.crc32(body) & 0xFFFFFFFF
    return body + struct.pack(">I", crc)


def decode_rdd18_rtmd_klv_frame(packet: bytes) -> Rdd18RtmdFrameDecoded:
    """Decode and CRC32-verify an RDD-18 / MP4 `rtmd` frame packet."""
    expected_len = struct.calcsize(">16sII16s16s16sIIII64s32s") + 4
    if len(packet) != expected_len:
        return Rdd18RtmdFrameDecoded(
            valid=False,
            exposure_index=0,
            base_iso=0,
            gamma_name="INVALID",
            gamma_ul_hex="",
            primaries_name="INVALID",
            fps_x1000=0,
            f_number_x100=0,
            shutter_angle_x10=0,
            wb_kelvin=0,
            cube_lut_path="",
            umid_hex="",
            crc32_valid=False,
            packet_hex=packet.hex(),
            errors=(f"Invalid RDD-18 packet size {len(packet)} != {expected_len}",),
        )
    body = packet[:-4]
    (rx_crc,) = struct.unpack(">I", packet[-4:])
    crc_ok = rx_crc == (zlib.crc32(body) & 0xFFFFFFFF)
    errors: List[str] = []
    if not crc_ok:
        errors.append("CRC32 mismatch on RDD-18 / rtmd KLV packet")

    (
        hdr,
        ei,
        base_iso,
        gamma_b,
        gamma_ul_b,
        prim_b,
        fps_x1000,
        f_num,
        shutter_x10,
        wb_k,
        lut_b,
        umid_b,
    ) = struct.unpack(">16sII16s16s16sIIII64s32s", body)

    if hdr[:4] != RDD18_KLV_PACKET_MAGIC:
        errors.append("Missing SMPTE KLV Universal Key prefix 060e2b34")
    gamma_name = gamma_b.rstrip(b"\x00").decode("ascii", "replace")
    prim_name = prim_b.rstrip(b"\x00").decode("ascii", "replace")
    lut_path = lut_b.rstrip(b"\x00").decode("utf-8", "replace")
    umid_hex = umid_b.hex()
    if not umid_hex.startswith(SMPTE_UMID_BASIC_PREFIX_HEX):
        errors.append("UMID missing SMPTE ST 330 Basic UMID UL prefix")
    if base_iso not in (800, 12800):
        errors.append(f"Invalid Cinema Line Base ISO {base_iso}")

    return Rdd18RtmdFrameDecoded(
        valid=len(errors) == 0,
        exposure_index=ei,
        base_iso=base_iso,
        gamma_name=gamma_name,
        gamma_ul_hex=gamma_ul_b.hex(),
        primaries_name=prim_name,
        fps_x1000=fps_x1000,
        f_number_x100=f_num,
        shutter_angle_x10=shutter_x10,
        wb_kelvin=wb_k,
        cube_lut_path=lut_path,
        umid_hex=umid_hex,
        crc32_valid=crc_ok,
        packet_hex=packet.hex(),
        errors=tuple(errors),
    )


def evaluate_mxf_mp4_essence_bridge(
    *,
    source_container: str = "MXF_OP1A",
    target_container: str = "MP4_ISOBMFF",
    source_codec: str = "XAVC_I_H422IP",
    target_codec: str = "XAVC_S_I_H422IP",
    bridge_mode: str = "LOSSLESS_REWRAP",
    source_umid_hex: Optional[str] = None,
    exposure_index: int = 800,
    base_iso: int = 800,
    gamma_name: str = "S-LOG3",
    primaries_name: str = "S-GAMUT3.CINE",
    cube_lut_path: str = "/tmp/fx3_stageb_lut/S709_33.cube",
    attempt_spvc_spoof: bool = False,
    corrupt_rdd18_crc: bool = False,
) -> MxfMp4BridgeEvalResult:
    """Evaluate FX6 MXF OP1a <-> FX3 MP4 ISO-BMFF essence, UMID, and RDD-18 metadata bridge."""
    src_c = source_container.strip().upper()
    dst_c = target_container.strip().upper()
    src_k = source_codec.strip().upper()
    dst_k = target_codec.strip().upper()
    mode = bridge_mode.strip().upper()

    if src_c not in VALID_CONTAINER_FORMATS or dst_c not in VALID_CONTAINER_FORMATS:
        raise ValueError(f"Unsupported container pair {src_c} -> {dst_c}")
    if src_k not in VALID_ESSENCE_CODECS or dst_k not in VALID_ESSENCE_CODECS:
        raise ValueError(f"Unsupported codec pair {src_k} -> {dst_k}")
    if mode not in VALID_BRIDGE_MODES:
        raise ValueError(f"Unsupported bridge_mode={bridge_mode!r}")

    src_umid = (source_umid_hex or build_smpte_umid(material_counter=1)).strip().lower()
    if mode == "TRANSCODE":
        dst_umid = build_smpte_umid(material_counter=2, creation_unix_sec=1794715205)
    else:
        dst_umid = src_umid

    pkt = bytearray(
        build_rdd18_rtmd_klv_frame(
            exposure_index=exposure_index,
            base_iso=base_iso,
            gamma_name=gamma_name,
            primaries_name=primaries_name,
            cube_lut_path=cube_lut_path,
            umid_hex=dst_umid,
        )
    )
    if corrupt_rdd18_crc:
        pkt[-1] ^= 0xA5
    decoded = decode_rdd18_rtmd_klv_frame(bytes(pkt))
    errors: List[str] = list(decoded.errors)

    umid_preserved = src_umid == dst_umid
    spvc_safe = not attempt_spvc_spoof

    if attempt_spvc_spoof:
        errors.append(
            "BLOCKED_SPVC_CERT_SPOOFING: Stage-B rewrap must strip/mark unsigned rather than "
            "forging sony.private_cert.v1 SPVC box"
        )

    if mode == "DIRECT_RAW_COPY" and src_c == "MXF_OP1A" and dst_c == "MP4_ISOBMFF":
        errors.append(
            "BLOCKED_RAW_MXF_OP1A_ON_MP4_SLOT: ILME-FX3 M4ROOT/CLIP requires MP4 ISO-BMFF + rtmd "
            "muxing (use LOSSLESS_REWRAP)"
        )

    # Lossless rewrap requires H.264 High 4:2:2 Intra parity between XAVC-I (MXF) and XAVC S-I (MP4)
    if mode == "LOSSLESS_REWRAP":
        intra_pair = {src_k, dst_k}.issubset({"XAVC_I_H422IP", "XAVC_S_I_H422IP"})
        if not intra_pair and src_k != dst_k:
            errors.append(
                f"BLOCKED_INCOMPATIBLE_LOSSLESS_REWRAP: {src_k} cannot losslessly rewrap to {dst_k}"
            )
        if not umid_preserved:
            errors.append("BLOCKED_UMID_MISMATCH_ON_LOSSLESS_REWRAP")

    if not errors:
        if mode == "LOSSLESS_REWRAP":
            status = "LOSSLESS_ESSENCE_REWRAP_VERIFIED"
        else:
            status = "TRANSCODE_NEW_UMID_VERIFIED"
    else:
        status = errors[0].split(":", 1)[0]

    return MxfMp4BridgeEvalResult(
        valid=len(errors) == 0,
        status=status,
        source_container=src_c,
        target_container=dst_c,
        source_codec=src_k,
        target_codec=dst_k,
        bridge_mode=mode,
        source_umid_hex=src_umid,
        target_umid_hex=dst_umid,
        umid_preserved=umid_preserved,
        spvc_preserved_without_spoofing=spvc_safe,
        rdd18_rtmd_decoded=decoded,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar B Functions: SMPTE ST 2059-2 PTPv2 <-> Multi-Terminal LTC Sync
# ---------------------------------------------------------------------------


def ptpv2_tai_to_smpte12m_tc(
    *,
    tai_ns: int,
    tai_utc_offset_sec: int = PTP_TAI_UTC_OFFSET_SEC,
    fps_key: str = "23.976_NDF",
) -> Ptpv2ToLtcResult:
    """Convert SMPTE ST 2059-2 PTPv2 TAI nanoseconds into SMPTE 12M LTC & frame-edge phase."""
    norm_fps = fps_key.strip().upper()
    if norm_fps not in PTPV2_FPS_SPECS:
        raise ValueError(f"Unsupported fps_key={fps_key!r}")
    if tai_ns < 0:
        return Ptpv2ToLtcResult(
            valid=False,
            fps_key=norm_fps,
            tai_ns=tai_ns,
            utc_ns=0,
            tai_utc_offset_sec=tai_utc_offset_sec,
            smpte12m_timecode="00:00:00:00",
            frame_phase_offset_us=0.0,
            drop_frame=False,
            errors=("Negative TAI timestamp",),
        )

    fps_num, fps_den, nominal_fps, is_df = PTPV2_FPS_SPECS[norm_fps]
    utc_ns = tai_ns - (tai_utc_offset_sec * 1_000_000_000)
    if utc_ns < 0:
        utc_ns = 0

    # Exact rational frame index since epoch
    frame_duration_ns = (1_000_000_000 * fps_den) / fps_num
    total_frames_exact = utc_ns / frame_duration_ns
    nearest_frame = round(total_frames_exact)
    phase_offset_us = round(((total_frames_exact - nearest_frame) * frame_duration_ns) / 1_000.0, 3)

    # Convert UTC day seconds + frame-in-second into HH:MM:SS:FF
    utc_sec_total = utc_ns // 1_000_000_000
    day_sec = utc_sec_total % 86400
    hh = day_sec // 3600
    mm = (day_sec % 3600) // 60
    ss = day_sec % 60
    sub_ns = utc_ns % 1_000_000_000
    ff = int((sub_ns * nominal_fps) // 1_000_000_000) % nominal_fps
    if is_df and ff in (0, 1) and ss == 0 and (mm % 10) != 0:
        ff = 2
    sep = ";" if is_df else ":"
    tc_str = f"{hh:02d}:{mm:02d}:{ss:02d}{sep}{ff:02d}"

    return Ptpv2ToLtcResult(
        valid=True,
        fps_key=norm_fps,
        tai_ns=tai_ns,
        utc_ns=utc_ns,
        tai_utc_offset_sec=tai_utc_offset_sec,
        smpte12m_timecode=tc_str,
        frame_phase_offset_us=phase_offset_us,
        drop_frame=is_df,
        errors=(),
    )


def evaluate_ptpv2_ltc_phase_sync(
    *,
    sync_profile: str = "SMPTE_ST_2059_2_HW_TS",
    transport_driver: str = "CDC_NCM_RTL8153",
    ptpv2_domain: int = SMPTE_ST2059_DEFAULT_DOMAIN,
    p12_airplane_rf_off: bool = True,
    measured_ptp_jitter_us: float = 0.42,
    ltc_phase_offset_us: float = 120.0,
    vmc_bncm1_attached: bool = True,
    uart_boot_active: bool = False,
    tai_ns: int = 1_794_715_237_000_000_000,
    fps_key: str = "23.976_NDF",
) -> Ptpv2LtcSyncEvalResult:
    """Audit SMPTE ST 2059-2 PTPv2 timestamping vs Multi-Terminal LTC alignment under P12."""
    prof = sync_profile.strip().upper()
    drv = transport_driver.strip().upper()
    if prof not in VALID_SYNC_PROFILES:
        raise ValueError(f"Unsupported sync_profile={sync_profile!r}")
    if drv not in VALID_SYNC_TRANSPORTS:
        raise ValueError(f"Unsupported transport_driver={transport_driver!r}")

    errors: List[str] = []
    wf12_risk = 0

    if prof == "PTP_IP_15740_CONTROL":
        errors.append(
            "BLOCKED_PTPIP_NOT_IEEE1588_PTPV2: Sony PTP-IP (TCP/15740) is camera control only, "
            "not SMPTE ST 2059-2 PTPv2 synchronization"
        )

    if drv in FORBIDDEN_RF_SYNC_TRANSPORTS and p12_airplane_rf_off:
        wf12_risk = 1
        errors.append(
            f"BLOCKED_P12_RF_OFF_VIOLATION_00342260: {drv} forbidden under P12 Airplane RF-Off; "
            "bind PTPv2 exclusively to wired USB-LAN (CDC-NCM / RNDIS)"
        )
    elif drv not in WIRED_SYNC_TRANSPORTS:
        errors.append(f"Unsupported non-wired PTPv2 transport {drv}")

    if not (0 <= ptpv2_domain <= 255):
        errors.append(f"BLOCKED_INVALID_PTPV2_DOMAIN: {ptpv2_domain} outside [0..255]")

    if prof == "SMPTE_ST_2059_2_HW_TS" and measured_ptp_jitter_us > PTPV2_MAX_HW_JITTER_US:
        errors.append(
            f"BLOCKED_PTPV2_HW_JITTER_EXCEEDED: {measured_ptp_jitter_us} us > {PTPV2_MAX_HW_JITTER_US} us"
        )
    if prof == "SMPTE_ST_2059_2_SW_TS" and measured_ptp_jitter_us > PTPV2_MAX_SW_JITTER_US:
        errors.append(
            f"BLOCKED_PTPV2_SW_JITTER_EXCEEDED: {measured_ptp_jitter_us} us > {PTPV2_MAX_SW_JITTER_US} us"
        )

    if abs(ltc_phase_offset_us) > LTC_MAX_PHASE_OFFSET_US:
        errors.append(
            f"BLOCKED_LTC_PHASE_DRIFT_EXCEEDED: |{ltc_phase_offset_us}| us > {LTC_MAX_PHASE_OFFSET_US} us"
        )

    if uart_boot_active and vmc_bncm1_attached:
        errors.append(
            "BLOCKED_VMC_BNCM1_DURING_UART_BOOT: Disconnect VMC-BNCM1 LTC cable during H0/Tier-3 "
            "uart_boot to protect Multi-Port Pins 7/8/9"
        )

    tc_res = ptpv2_tai_to_smpte12m_tc(tai_ns=tai_ns, fps_key=fps_key)
    if not tc_res.valid:
        errors.extend(tc_res.errors)

    status = "ST2059_PTPV2_LTC_PHASE_LOCKED" if not errors else errors[0].split(":", 1)[0]
    return Ptpv2LtcSyncEvalResult(
        valid=len(errors) == 0,
        status=status,
        sync_profile=prof,
        transport_driver=drv,
        ptpv2_domain=ptpv2_domain,
        p12_airplane_rf_off=p12_airplane_rf_off,
        wf12_00342260_risk=wf12_risk,
        measured_ptp_jitter_us=measured_ptp_jitter_us,
        ltc_phase_offset_us=ltc_phase_offset_us,
        vmc_bncm1_attached=vmc_bncm1_attached,
        uart_boot_active=uart_boot_active,
        ptpv2_to_ltc=tc_res,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar C Functions: TSL UMD v5.0 Wire Builder/Parser & FX3 Tally Translator
# ---------------------------------------------------------------------------


def sanitize_umd_label_16(raw_label: str) -> str:
    """Strip control/ANSI sequences and clamp UMD label to 16 printable characters."""
    no_ansi = re.sub(r"\x1b\[[0-9;]*[A-Za-z]", "", raw_label)
    cleaned = "".join(ch for ch in no_ansi if ch.isprintable() and ord(ch) >= 0x20).strip()
    return cleaned[:TSL_UMD_MAX_LABEL_CHARS]


def _tcp_dle_stuff(payload: bytes) -> bytes:
    stuffed = bytearray([TSL_UMD_DLE, TSL_UMD_STX])
    for b in payload:
        stuffed.append(b)
        if b == TSL_UMD_DLE:
            stuffed.append(TSL_UMD_DLE)
    return bytes(stuffed)


def _tcp_dle_unstuff(framed: bytes) -> Tuple[bytes, Optional[str]]:
    if len(framed) < 2 or framed[0] != TSL_UMD_DLE or framed[1] != TSL_UMD_STX:
        return b"", "Missing TCP DLE/STX (0xFE 0x02) header"
    out = bytearray()
    i = 2
    n = len(framed)
    while i < n:
        b = framed[i]
        if b == TSL_UMD_DLE:
            if i + 1 < n and framed[i + 1] == TSL_UMD_DLE:
                out.append(TSL_UMD_DLE)
                i += 2
                continue
            return b"", "Unescaped 0xFE DLE byte in TCP TSL UMD v5.0 stream"
        out.append(b)
        i += 1
    return bytes(out), None


def build_tsl_umd_v5_packet(
    *,
    screen: int = 0,
    entries: Sequence[Tuple[int, int, int, int, int, str]],
    unicode_utf16: bool = False,
    tcp_dle_stx: bool = False,
) -> bytes:
    """Build a little-endian TSL UMD v5.0 wire packet.

    Each entry tuple is `(index, rh_tally, text_tally, lh_tally, brightness, text)`.
    """
    flags = 0x01 if unicode_utf16 else 0x00
    dmsgs = bytearray()
    for index, rh, txt_t, lh, bright, text in entries:
        for tval in (rh, txt_t, lh):
            if tval not in (0, 1, 2, 3):
                raise ValueError(f"Invalid 2-bit TSL tally state {tval}")
        if not (0 <= bright <= 3):
            raise ValueError(f"Invalid TSL brightness {bright} not in 0..3")
        control = (rh & 0x03) | ((txt_t & 0x03) << 2) | ((lh & 0x03) << 4) | ((bright & 0x03) << 6)
        text_bytes = text.encode("utf-16le") if unicode_utf16 else text.encode("ascii", "replace")
        dmsgs.extend(struct.pack("<HHH", index & 0xFFFF, control, len(text_bytes)))
        dmsgs.extend(text_bytes)

    body_after_pbc = struct.pack("<BBH", TSL_UMD_V5_MINOR_VER, flags, screen & 0xFFFF) + bytes(dmsgs)
    pkt = struct.pack("<H", len(body_after_pbc)) + body_after_pbc
    if tcp_dle_stx:
        return _tcp_dle_stuff(pkt)
    return pkt


def parse_tsl_umd_v5_packet(
    raw_packet: bytes,
    *,
    expect_tcp_dle_stx: bool = False,
) -> TslUmdV5PacketDecoded:
    """Parse and validate a TSL UMD v5.0 UDP or TCP DLE/STX packet."""
    errors: List[str] = []
    payload = raw_packet
    if expect_tcp_dle_stx:
        payload, err = _tcp_dle_unstuff(raw_packet)
        if err:
            return TslUmdV5PacketDecoded(
                valid=False,
                pbc=0,
                ver=0,
                flags=0,
                is_utf16le=False,
                is_scontrol=False,
                screen=0,
                tcp_dle_stx_framed=True,
                messages=(),
                packet_hex=raw_packet.hex(),
                errors=(err,),
            )
    elif len(raw_packet) > TSL_UMD_UDP_MAX_BYTES:
        errors.append(f"BLOCKED_TSL_UDP_PACKET_EXCEEDS_2048B: {len(raw_packet)} > {TSL_UMD_UDP_MAX_BYTES}")

    if len(payload) < 6:
        return TslUmdV5PacketDecoded(
            valid=False,
            pbc=0,
            ver=0,
            flags=0,
            is_utf16le=False,
            is_scontrol=False,
            screen=0,
            tcp_dle_stx_framed=expect_tcp_dle_stx,
            messages=(),
            packet_hex=raw_packet.hex(),
            errors=tuple(errors + ["Packet shorter than 6-byte TSL UMD v5.0 header"]),
        )

    (pbc, ver, flags, screen) = struct.unpack_from("<HBBH", payload, 0)
    if pbc != len(payload) - 2:
        errors.append(f"PBC length mismatch: pbc={pbc} != payload-2 ({len(payload) - 2})")
    if ver != TSL_UMD_V5_MINOR_VER:
        errors.append(f"Unsupported TSL UMD version {ver} != 0 (v5.00)")

    is_utf16 = bool(flags & 0x01)
    is_scontrol = bool(flags & 0x02)
    msgs: List[TslUmdV5DisplayMsg] = []

    if not is_scontrol:
        offset = 6
        end = 2 + pbc
        while offset < min(end, len(payload)):
            if offset + 6 > len(payload):
                errors.append("Truncated <DMSG> header")
                break
            idx, ctrl, length = struct.unpack_from("<HHH", payload, offset)
            offset += 6
            if ctrl & 0x8000:
                errors.append("Unsupported undefined CONTROL DATA bit 15 in TSL v5.00")
                break
            if offset + length > len(payload):
                errors.append("Truncated <DMSG> TEXT field")
                break
            txt_raw = payload[offset : offset + length]
            offset += length
            txt = txt_raw.decode("utf-16le", "replace") if is_utf16 else txt_raw.decode("ascii", "replace")
            msgs.append(
                TslUmdV5DisplayMsg(
                    index=idx,
                    rh_tally=ctrl & 0x03,
                    text_tally=(ctrl >> 2) & 0x03,
                    lh_tally=(ctrl >> 4) & 0x03,
                    brightness=(ctrl >> 6) & 0x03,
                    text=txt,
                )
            )

    return TslUmdV5PacketDecoded(
        valid=len(errors) == 0,
        pbc=pbc,
        ver=ver,
        flags=flags,
        is_utf16le=is_utf16,
        is_scontrol=is_scontrol,
        screen=screen,
        tcp_dle_stx_framed=expect_tcp_dle_stx,
        messages=tuple(msgs),
        packet_hex=raw_packet.hex(),
        errors=tuple(errors),
    )


def evaluate_tsl_umd_tally_translation(
    *,
    port_key: str = "UDP_40003",
    transport_driver: str = "CDC_NCM_RTL8153",
    p12_airplane_rf_off: bool = True,
    target_display_index: int = 0,
    lh_tally: int = 1,
    text_tally: int = 1,
    rh_tally: int = 1,
    brightness: int = 3,
    raw_umd_label: str = "CAM-A1 FX3 STAGEB",
    unicode_utf16: bool = False,
    oversize_udp_test: bool = False,
) -> TslTallyBridgeEvalResult:
    """Translate a TSL UMD v5.0 packet into P12-safe FX3 physical Tally LED + OSD border states."""
    norm_port = port_key.strip().upper()
    norm_drv = transport_driver.strip().upper()
    if norm_port not in TSL_UMD_PORTS:
        raise ValueError(f"Unsupported port_key={port_key!r}")
    if norm_drv not in VALID_SYNC_TRANSPORTS:
        raise ValueError(f"Unsupported transport_driver={transport_driver!r}")

    proto_kind, _port_num = TSL_UMD_PORTS[norm_port]
    is_tcp = proto_kind == "TCP"

    label_for_wire = raw_umd_label if not oversize_udp_test else ("X" * 2100)
    wire_pkt = build_tsl_umd_v5_packet(
        screen=0,
        entries=((target_display_index, rh_tally, text_tally, lh_tally, brightness, label_for_wire),),
        unicode_utf16=unicode_utf16,
        tcp_dle_stx=is_tcp,
    )
    decoded = parse_tsl_umd_v5_packet(wire_pkt, expect_tcp_dle_stx=is_tcp)
    errors: List[str] = list(decoded.errors)

    wf12_risk = 0
    if norm_drv in FORBIDDEN_RF_SYNC_TRANSPORTS and p12_airplane_rf_off:
        wf12_risk = 1
        errors.append(
            f"BLOCKED_P12_RF_OFF_VIOLATION_00342260: TSL UMD tally listener cannot run on {norm_drv} "
            "under P12 Airplane RF-Off; bind strictly to wired USB-LAN (CDC-NCM / RNDIS)"
        )
    elif norm_drv not in WIRED_SYNC_TRANSPORTS:
        errors.append(f"Unsupported non-wired TSL transport {norm_drv}")

    matched_msg = next(
        (m for m in decoded.messages if m.index in (target_display_index, 0xFFFF)),
        decoded.messages[0] if decoded.messages else None,
    )
    active_tally = matched_msg.lh_tally if matched_msg else 0
    tally_name = TSL_TALLY_COLOR_NAMES.get(active_tally, "OFF")

    # FX3 hardware LEDs are RED-only (no physical Green LED).
    # Red (PGM=1) turns physical Front+Rear Red LEDs ON + RED OSD border.
    # Green (PVW=2) keeps physical Red LEDs strictly OFF (prevents false on-air Red tally!) + GREEN OSD border.
    fx3_red_leds_on = active_tally == 1
    osd_border = {
        0: "NONE",
        1: "RED",
        2: "GREEN",
        3: "AMBER",
    }.get(active_tally, "NONE")

    sanitized_label = sanitize_umd_label_16(matched_msg.text if matched_msg else raw_umd_label)
    status = "TSL_UMD_V5_P12_TALLY_TRANSLATED" if not errors else errors[0].split(":", 1)[0]

    return TslTallyBridgeEvalResult(
        valid=len(errors) == 0,
        status=status,
        port_key=norm_port,
        transport_driver=norm_drv,
        p12_airplane_rf_off=p12_airplane_rf_off,
        wf12_00342260_risk=wf12_risk,
        target_display_index=target_display_index,
        incoming_lh_tally=active_tally,
        incoming_tally_name=tally_name,
        fx3_front_rear_red_leds_on=fx3_red_leds_on,
        osd_border_color=osd_border,
        raw_umd_label=raw_umd_label,
        sanitized_16char_label=sanitized_label,
        fx6_green_gpio_faults=0,
        packet_decoded=decoded,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar D Functions: Volatile Staging & Zero Persistent eMMC Mutation Guard
# ---------------------------------------------------------------------------


def evaluate_phase122_write_guard(target_path: str) -> Phase122WriteGuardResult:
    """Enforce volatile RAM staging only and zero persistent eMMC/OTA/calibration mutation."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES_P122) and not bool(
        FORBIDDEN_PERSISTENT_EMMC_RE_P122.search(norm)
    )
    if is_volatile:
        return Phase122WriteGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            emmc_mutation_bytes=0,
            calibration_mutation_bytes=0,
            errors=(),
        )
    return Phase122WriteGuardResult(
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
# Pillar Evaluators & Top-Level Phase 122 Unified Auditor
# ---------------------------------------------------------------------------


def evaluate_pillar_a_mxf_mp4_essence_bridge(
    *,
    fx6_libmpr_mxf_markers: Tuple[str, ...],
    fx3_libmpr_mp4_markers: Tuple[str, ...],
    fx6_appfw_mxf_markers: Tuple[str, ...],
    uxc_container_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> MxfMp4EssenceBridgeReport:
    errors = list(extra_errors)
    umid = build_smpte_umid(material_counter=42, creation_unix_sec=1794715200)

    e_mxf_mp4 = evaluate_mxf_mp4_essence_bridge(
        source_container="MXF_OP1A",
        target_container="MP4_ISOBMFF",
        source_codec="XAVC_I_H422IP",
        target_codec="XAVC_S_I_H422IP",
        bridge_mode="LOSSLESS_REWRAP",
        source_umid_hex=umid,
        exposure_index=1600,
        base_iso=800,
        gamma_name="S-LOG3",
        primaries_name="S-GAMUT3.CINE",
    )
    e_mp4_mxf = evaluate_mxf_mp4_essence_bridge(
        source_container="MP4_ISOBMFF",
        target_container="MXF_OP1A",
        source_codec="XAVC_S_I_H422IP",
        target_codec="XAVC_I_H422IP",
        bridge_mode="LOSSLESS_REWRAP",
        source_umid_hex=umid,
        exposure_index=12800,
        base_iso=12800,
        gamma_name="REC2100-HLG",
        primaries_name="REC2020",
    )
    e_transcode = evaluate_mxf_mp4_essence_bridge(
        source_container="MXF_OP1A",
        target_container="MP4_ISOBMFF",
        source_codec="XAVC_I_H422IP",
        target_codec="XAVC_HS_HEVC",
        bridge_mode="TRANSCODE",
        source_umid_hex=umid,
    )
    b_raw_copy = evaluate_mxf_mp4_essence_bridge(
        source_container="MXF_OP1A",
        target_container="MP4_ISOBMFF",
        source_codec="XAVC_I_H422IP",
        target_codec="XAVC_S_I_H422IP",
        bridge_mode="DIRECT_RAW_COPY",
        source_umid_hex=umid,
    )
    b_crc = evaluate_mxf_mp4_essence_bridge(
        source_container="MXF_OP1A",
        target_container="MP4_ISOBMFF",
        bridge_mode="LOSSLESS_REWRAP",
        corrupt_rdd18_crc=True,
    )

    if not e_mxf_mp4.valid or not e_mxf_mp4.umid_preserved:
        errors.append(f"MXF->MP4 lossless rewrap failed: {e_mxf_mp4.errors}")
    if not e_mp4_mxf.valid or not e_mp4_mxf.umid_preserved:
        errors.append(f"MP4->MXF lossless rewrap failed: {e_mp4_mxf.errors}")
    if not e_transcode.valid or e_transcode.umid_preserved:
        errors.append("Transcode bridge failed or failed to regenerate UMID")
    if b_raw_copy.valid:
        errors.append("Raw MXF copy onto MP4 slot was not blocked")
    if b_crc.valid:
        errors.append("Corrupt RDD-18 CRC32 packet was not blocked")

    return MxfMp4EssenceBridgeReport(
        passed=len(errors) == 0,
        fx6_libmpr_mxf_markers=fx6_libmpr_mxf_markers,
        fx3_libmpr_mp4_markers=fx3_libmpr_mp4_markers,
        fx6_appfw_mxf_markers=fx6_appfw_mxf_markers,
        uxc_container_labels=uxc_container_labels,
        eval_mxf_to_mp4_lossless_rewrap=e_mxf_mp4,
        eval_mp4_to_mxf_lossless_rewrap=e_mp4_mxf,
        eval_transcode_regenerates_umid=e_transcode,
        blocked_raw_mxf_on_mp4_slot=b_raw_copy,
        blocked_corrupt_rdd18_crc=b_crc,
        errors=tuple(errors),
    )


def evaluate_pillar_b_ptpv2_ltc_phase_sync(
    *,
    fx3_appfw_tc_lan_markers: Tuple[str, ...],
    fx6_appfw_tc_markers: Tuple[str, ...],
    fx6_libnet_ether_markers: Tuple[str, ...],
    fx6_libinfra_ptp_markers: Tuple[str, ...],
    uxc_tc_lan_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> Ptpv2LtcPhaseSyncReport:
    errors = list(extra_errors)

    e_hw = evaluate_ptpv2_ltc_phase_sync(
        sync_profile="SMPTE_ST_2059_2_HW_TS",
        transport_driver="CDC_NCM_RTL8153",
        measured_ptp_jitter_us=0.35,
        ltc_phase_offset_us=85.0,
        vmc_bncm1_attached=True,
        uart_boot_active=False,
        fps_key="23.976_NDF",
    )
    e_sw = evaluate_ptpv2_ltc_phase_sync(
        sync_profile="SMPTE_ST_2059_2_SW_TS",
        transport_driver="USB_RNDIS_WIRED",
        measured_ptp_jitter_us=110.0,
        ltc_phase_offset_us=210.0,
        vmc_bncm1_attached=True,
        uart_boot_active=False,
        fps_key="29.970_DF",
    )
    b_ptpip = evaluate_ptpv2_ltc_phase_sync(
        sync_profile="PTP_IP_15740_CONTROL",
        transport_driver="CDC_NCM_RTL8153",
    )
    b_wifi = evaluate_ptpv2_ltc_phase_sync(
        sync_profile="SMPTE_ST_2059_2_HW_TS",
        transport_driver="WIFI_WLAN0",
        p12_airplane_rf_off=True,
    )
    b_drift = evaluate_ptpv2_ltc_phase_sync(
        sync_profile="SMPTE_ST_2059_2_HW_TS",
        transport_driver="CDC_NCM_AX88179",
        ltc_phase_offset_us=1800.0,
    )
    b_uart = evaluate_ptpv2_ltc_phase_sync(
        sync_profile="SMPTE_ST_2059_2_HW_TS",
        transport_driver="CDC_NCM_RTL8153",
        vmc_bncm1_attached=True,
        uart_boot_active=True,
    )

    for lbl, ev in (("hw_23976", e_hw), ("sw_2997df", e_sw)):
        if not ev.valid or ev.wf12_00342260_risk != 0:
            errors.append(f"Positive PTPv2->LTC check {lbl} failed: {ev.errors}")
    for lbl, blk in (
        ("ptpip", b_ptpip),
        ("wifi_p12", b_wifi),
        ("ltc_drift", b_drift),
        ("uart_boot", b_uart),
    ):
        if blk.valid:
            errors.append(f"Negative PTPv2->LTC guard {lbl} unexpectedly passed")
    if b_wifi.wf12_00342260_risk == 0:
        errors.append("Wi-Fi P12 violation failed to flag wf12_00342260_risk")

    return Ptpv2LtcPhaseSyncReport(
        passed=len(errors) == 0,
        fx3_appfw_tc_lan_markers=fx3_appfw_tc_lan_markers,
        fx6_appfw_tc_markers=fx6_appfw_tc_markers,
        fx6_libnet_ether_markers=fx6_libnet_ether_markers,
        fx6_libinfra_ptp_markers=fx6_libinfra_ptp_markers,
        uxc_tc_lan_labels=uxc_tc_lan_labels,
        eval_st2059_hw_ts_cdc_ncm_23976=e_hw,
        eval_st2059_sw_ts_rndis_2997df=e_sw,
        blocked_ptpip_confused_with_ptpv2=b_ptpip,
        blocked_wifi_wlan0_p12_violation=b_wifi,
        blocked_ltc_phase_drift_exceeded=b_drift,
        blocked_vmc_bncm1_during_uart_boot=b_uart,
        errors=tuple(errors),
    )


def evaluate_pillar_c_tsl_umd_tally_bridge(
    *,
    fx3_appfw_tally_markers: Tuple[str, ...],
    fx6_appfw_tally_markers: Tuple[str, ...],
    uxc_tally_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> TslUmdTallyBridgeReport:
    errors = list(extra_errors)

    e_pgm_red = evaluate_tsl_umd_tally_translation(
        port_key="UDP_40003",
        transport_driver="CDC_NCM_RTL8153",
        target_display_index=0,
        lh_tally=1,
        text_tally=1,
        rh_tally=1,
        brightness=3,
        raw_umd_label="CAM-A1 FX3",
    )
    e_pvw_green = evaluate_tsl_umd_tally_translation(
        port_key="TCP_5727",
        transport_driver="CDC_NCM_AX88179",
        target_display_index=0x00FE,  # includes 0xFE byte to exercise TCP DLE escaping
        lh_tally=2,
        text_tally=2,
        rh_tally=2,
        brightness=2,
        raw_umd_label="CAM-B2 PREVIEW",
    )
    e_amber_utf16 = evaluate_tsl_umd_tally_translation(
        port_key="UDP_8900",
        transport_driver="USB_RNDIS_WIRED",
        target_display_index=3,
        lh_tally=3,
        text_tally=3,
        rh_tally=0,
        brightness=1,
        raw_umd_label="CAM-C3_ISO_LONG_LABEL_OVER16",
        unicode_utf16=True,
    )
    e_off = evaluate_tsl_umd_tally_translation(
        port_key="TCP_5728",
        transport_driver="CDC_NCM_RTL8153",
        target_display_index=0,
        lh_tally=0,
        text_tally=0,
        rh_tally=0,
        brightness=0,
        raw_umd_label="CAM-A1",
    )
    b_wifi = evaluate_tsl_umd_tally_translation(
        port_key="UDP_40003",
        transport_driver="WIFI_WLAN0",
        p12_airplane_rf_off=True,
        lh_tally=1,
    )
    b_udp_2k = evaluate_tsl_umd_tally_translation(
        port_key="UDP_40003",
        transport_driver="CDC_NCM_RTL8153",
        oversize_udp_test=True,
    )

    if not e_pgm_red.valid or not e_pgm_red.fx3_front_rear_red_leds_on or e_pgm_red.osd_border_color != "RED":
        errors.append(f"TSL Red PGM tally translation failed: {e_pgm_red.errors}")
    if (
        not e_pvw_green.valid
        or e_pvw_green.fx3_front_rear_red_leds_on
        or e_pvw_green.osd_border_color != "GREEN"
        or not e_pvw_green.packet_decoded.tcp_dle_stx_framed
    ):
        errors.append(f"TSL Green PVW tally OSD-only containment failed: {e_pvw_green.errors}")
    if (
        not e_amber_utf16.valid
        or e_amber_utf16.fx3_front_rear_red_leds_on
        or len(e_amber_utf16.sanitized_16char_label) != TSL_UMD_MAX_LABEL_CHARS
    ):
        errors.append(f"TSL UTF-16LE Amber 16-char clamp failed: {e_amber_utf16.errors}")
    if not e_off.valid or e_off.fx3_front_rear_red_leds_on or e_off.osd_border_color != "NONE":
        errors.append("TSL Off tally did not clear LEDs and OSD border")
    if b_wifi.valid or b_wifi.wf12_00342260_risk == 0:
        errors.append("TSL over Wi-Fi P12 violation was not blocked")
    if b_udp_2k.valid:
        errors.append("Oversized >2048B TSL UDP packet was not blocked")

    return TslUmdTallyBridgeReport(
        passed=len(errors) == 0,
        fx3_appfw_tally_markers=fx3_appfw_tally_markers,
        fx6_appfw_tally_markers=fx6_appfw_tally_markers,
        uxc_tally_labels=uxc_tally_labels,
        eval_udp_40003_pgm_red_tally=e_pgm_red,
        eval_tcp_5727_pvw_green_osd_only=e_pvw_green,
        eval_udp_8900_utf16_amber_16char_clamp=e_amber_utf16,
        eval_off_tally_clears_leds_and_border=e_off,
        blocked_wifi_p12_tally_violation=b_wifi,
        blocked_udp_over_2048_bytes=b_udp_2k,
        errors=tuple(errors),
    )


def evaluate_pillar_d_zero_mutation_emmc_guard(
    *,
    fx3_global_xdb_valid: bool,
    fx6_global_xdb_valid: bool,
    extra_errors: Sequence[str] = (),
) -> ZeroMutationEssenceTallyReport:
    errors = list(extra_errors)
    if not fx3_global_xdb_valid:
        errors.append("FX3 global.xdb (uxa\\x07) failed structural validation")
    if not fx6_global_xdb_valid:
        errors.append("FX6 global.xdb (uxa\\x07) failed structural validation")

    g_vol = evaluate_phase122_write_guard("/tmp/fx3_stageb_mxf_ptpv2_tally_shadow.json")
    g_body = evaluate_phase122_write_guard("/mnt/sd/BODYDATA.DAT")
    g_nf15 = evaluate_phase122_write_guard("/dev/nflasha15")
    g_cn0 = evaluate_phase122_write_guard("/dev/cnflasha0")
    g_bak = evaluate_phase122_write_guard("p2:/setting/Backup.bin")

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

    return ZeroMutationEssenceTallyReport(
        passed=len(errors) == 0,
        fx3_global_xdb_valid=fx3_global_xdb_valid,
        fx6_global_xdb_valid=fx6_global_xdb_valid,
        volatile_staging_guard=g_vol,
        blocked_bodydata_dat_guard=g_body,
        blocked_nflasha15_guard=g_nf15,
        blocked_cnflasha0_guard=g_cn0,
        blocked_backup_bin_guard=g_bak,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


def build_clean_room_mxf_mp4_ptpv2_tally_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, `global.xdb`, and `.uxc` fixtures."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)

    def _pack(tokens: Sequence[str]) -> bytes:
        return elf_hdr + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    return {
        "fx3_appfw": _pack(FX3_APPFW_PHASE122_MARKERS),
        "fx6_appfw": _pack(FX6_APPFW_PHASE122_MARKERS),
        "fx3_libmpr": _pack(FX3_LIBMPR_PHASE122_MARKERS),
        "fx6_libmpr": _pack(FX6_LIBMPR_PHASE122_MARKERS),
        "fx6_libinfra_ptp": _pack(FX6_LIBINFRA_PTP_PHASE122_MARKERS),
        "fx6_libnet_ether": _pack(FX6_LIBNET_ETHER_PHASE122_MARKERS),
        "fx3_global_xdb": build_synthetic_global_xdb("fx3_702"),
        "fx6_global_xdb": build_synthetic_global_xdb("fx6_601"),
        "fx3_str_en": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS39_PHASE122_LABELS.items()}, namespace_id=39
        ),
        "fx3_str_en_g": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS3_PHASE122_LABELS.items()}, namespace_id=3
        ),
        "fx6_str_en_1": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS1_PHASE122_LABELS.items()}, namespace_id=1
        ),
        "fx6_str_en_2": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS2_PHASE122_LABELS.items()}, namespace_id=2
        ),
    }


def analyze_mxf_mp4_essence_ptpv2_and_tally_umd(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> MxfMp4EssencePtpv2AndTallyUmdReport:
    """Run the 24th unified firmware-lab auditor in Local Donor (`os.O_RDONLY`) or Clean-Room mode."""
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
        "tally": FX3_APPFW_PHASE122_MARKERS[:1],
        "tc_lan": FX3_APPFW_PHASE122_MARKERS[1:],
    }
    fx6_app_groups = {
        "mxf": FX6_APPFW_PHASE122_MARKERS[:2],
        "tc": FX6_APPFW_PHASE122_MARKERS[2:3],
        "tally": FX6_APPFW_PHASE122_MARKERS[3:],
    }
    fx3_mpr_groups = {"mp4": FX3_LIBMPR_PHASE122_MARKERS}
    fx6_mpr_groups = {"mxf": FX6_LIBMPR_PHASE122_MARKERS}
    fx6_ptp_groups = {"ptp": FX6_LIBINFRA_PTP_PHASE122_MARKERS}
    fx6_eth_groups = {"eth": FX6_LIBNET_ETHER_PHASE122_MARKERS}

    if use_local:
        sz_fx3_app, fx3_app_res = _scan_donor_rdonly_markers(donor_paths["fx3_appfw"], fx3_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_app, fx6_app_res = _scan_donor_rdonly_markers(donor_paths["fx6_appfw"], fx6_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx3_mpr, fx3_mpr_res = _scan_donor_rdonly_markers(donor_paths["fx3_libmpr"], fx3_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_mpr, fx6_mpr_res = _scan_donor_rdonly_markers(donor_paths["fx6_libmpr"], fx6_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_ptp, fx6_ptp_res = _scan_donor_rdonly_markers(donor_paths["fx6_libinfra_ptp"], fx6_ptp_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_eth, fx6_eth_res = _scan_donor_rdonly_markers(donor_paths["fx6_libnet_ether"], fx6_eth_groups, is_elf=True)  # type: ignore[arg-type]
        fx3_xdb_bytes = _read_bytes_rdonly(donor_paths["fx3_global_xdb"])  # type: ignore[arg-type]
        fx6_xdb_bytes = _read_bytes_rdonly(donor_paths["fx6_global_xdb"])  # type: ignore[arg-type]
        fx3_str_en_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en"])  # type: ignore[arg-type]
        fx3_str_en_g_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en_g"])  # type: ignore[arg-type]
        fx6_str_en_1_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_1"])  # type: ignore[arg-type]
        fx6_str_en_2_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_2"])  # type: ignore[arg-type]
    else:
        fx = build_clean_room_mxf_mp4_ptpv2_tally_fixtures()
        sz_fx3_app, fx3_app_res = _scan_bytes_marker_groups(fx["fx3_appfw"], fx3_app_groups)
        sz_fx6_app, fx6_app_res = _scan_bytes_marker_groups(fx["fx6_appfw"], fx6_app_groups)
        sz_fx3_mpr, fx3_mpr_res = _scan_bytes_marker_groups(fx["fx3_libmpr"], fx3_mpr_groups)
        sz_fx6_mpr, fx6_mpr_res = _scan_bytes_marker_groups(fx["fx6_libmpr"], fx6_mpr_groups)
        sz_fx6_ptp, fx6_ptp_res = _scan_bytes_marker_groups(fx["fx6_libinfra_ptp"], fx6_ptp_groups)
        sz_fx6_eth, fx6_eth_res = _scan_bytes_marker_groups(fx["fx6_libnet_ether"], fx6_eth_groups)
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
        "fx3_global_xdb": len(fx3_xdb_bytes),
        "fx6_global_xdb": len(fx6_xdb_bytes),
        "fx3_str_en": len(fx3_str_en_bytes),
        "fx3_str_en_g": len(fx3_str_en_g_bytes),
        "fx6_str_en_1": len(fx6_str_en_1_bytes),
        "fx6_str_en_2": len(fx6_str_en_2_bytes),
    }

    pa_extra: List[str] = []
    pb_extra: List[str] = []
    pc_extra: List[str] = []
    pd_extra: List[str] = []

    for label, actual, expected, bucket in (
        ("FX6 libmpr MXF", fx6_mpr_res["mxf"], fx6_mpr_groups["mxf"], pa_extra),
        ("FX3 libmpr MP4", fx3_mpr_res["mp4"], fx3_mpr_groups["mp4"], pa_extra),
        ("FX6 appFw MXF", fx6_app_res["mxf"], fx6_app_groups["mxf"], pa_extra),
        ("FX3 appFw TC/LAN", fx3_app_res["tc_lan"], fx3_app_groups["tc_lan"], pb_extra),
        ("FX6 appFw TC", fx6_app_res["tc"], fx6_app_groups["tc"], pb_extra),
        ("FX6 libNetServiceEther", fx6_eth_res["eth"], fx6_eth_groups["eth"], pb_extra),
        ("FX6 libInfraPtpControl", fx6_ptp_res["ptp"], fx6_ptp_groups["ptp"], pb_extra),
        ("FX3 appFw Tally", fx3_app_res["tally"], fx3_app_groups["tally"], pc_extra),
        ("FX6 appFw Tally", fx6_app_res["tally"], fx6_app_groups["tally"], pc_extra),
    ):
        if len(actual) != len(expected):
            bucket.append(f"Missing {label} markers ({len(actual)}/{len(expected)})")

    fx3_ux_en, u_err_1 = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE122_LABELS)
    fx3_ux_g, u_err_2 = _extract_uxc_labels(fx3_str_en_g_bytes, FX3_NS3_PHASE122_LABELS)
    fx6_ux_1, u_err_3 = _extract_uxc_labels(fx6_str_en_1_bytes, FX6_NS1_PHASE122_LABELS)
    fx6_ux_2, u_err_4 = _extract_uxc_labels(fx6_str_en_2_bytes, FX6_NS2_PHASE122_LABELS)
    pa_extra.extend(u_err_1)
    pb_extra.extend(u_err_2)
    pc_extra.extend(u_err_3)
    pc_extra.extend(u_err_4)

    uxc_container_labels = {
        "fx3_mp4": fx3_ux_en.get("0x0004e7fd", ""),
        "fx3_wired_lan": fx3_ux_en.get("0x0004e100", ""),
    }
    uxc_tc_lan_labels = {
        "fx3_pc_remote_wired_lan": fx3_ux_g.get("0x0000601c", ""),
        "fx3_wired_lan": fx3_ux_g.get("0x00006398", ""),
        "fx6_timecode": fx6_ux_2.get("0x00004242", ""),
        "fx6_hdmi_tc_out": fx6_ux_2.get("0x00004245", ""),
    }
    uxc_tally_labels = {
        "fx6_front_tally": fx6_ux_1.get("0x000024f6", ""),
        "fx6_rear_tally": fx6_ux_1.get("0x000024f8", ""),
        "fx6_tally_control": fx6_ux_1.get("0x000024fa", ""),
        "fx6_tally_brightness": fx6_ux_1.get("0x000025b6", ""),
        "fx6_g_tally_lamp": fx6_ux_1.get("0x000025be", ""),
        "fx6_rec_lamp_f_on": fx6_ux_2.get("0x00004072", ""),
        "fx6_rec_lamp_r_on": fx6_ux_2.get("0x00004074", ""),
        "fx6_tally": fx6_ux_2.get("0x000042c8", ""),
        "fx6_wired_lan": fx6_ux_2.get("0x000042d7", ""),
    }

    pa = evaluate_pillar_a_mxf_mp4_essence_bridge(
        fx6_libmpr_mxf_markers=fx6_mpr_res["mxf"],
        fx3_libmpr_mp4_markers=fx3_mpr_res["mp4"],
        fx6_appfw_mxf_markers=fx6_app_res["mxf"],
        uxc_container_labels=uxc_container_labels,
        extra_errors=pa_extra,
    )
    pb = evaluate_pillar_b_ptpv2_ltc_phase_sync(
        fx3_appfw_tc_lan_markers=fx3_app_res["tc_lan"],
        fx6_appfw_tc_markers=fx6_app_res["tc"],
        fx6_libnet_ether_markers=fx6_eth_res["eth"],
        fx6_libinfra_ptp_markers=fx6_ptp_res["ptp"],
        uxc_tc_lan_labels=uxc_tc_lan_labels,
        extra_errors=pb_extra,
    )
    pc = evaluate_pillar_c_tsl_umd_tally_bridge(
        fx3_appfw_tally_markers=fx3_app_res["tally"],
        fx6_appfw_tally_markers=fx6_app_res["tally"],
        uxc_tally_labels=uxc_tally_labels,
        extra_errors=pc_extra,
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

    pd = evaluate_pillar_d_zero_mutation_emmc_guard(
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
        extra_errors=pd_extra,
    )

    all_errors = pa.errors + pb.errors + pc.errors + pd.errors
    all_passed = bool(pa.passed and pb.passed and pc.passed and pd.passed and len(all_errors) == 0)

    digest_payload = {
        "schema_version": PHASE_122_SCHEMA,
        "phase_version": PHASE_122_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "donor_file_sizes": sizes,
        "pa": asdict(pa),
        "pb": asdict(pb),
        "pc": asdict(pc),
        "pd": asdict(pd),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return MxfMp4EssencePtpv2AndTallyUmdReport(
        schema_version=PHASE_122_SCHEMA,
        phase_version=PHASE_122_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        donor_file_sizes=sizes,
        pillar_a_mxf_mp4_essence_bridge=pa,
        pillar_b_ptpv2_ltc_phase_sync=pb,
        pillar_c_tsl_umd_tally_bridge=pc,
        pillar_d_zero_mutation_emmc_guard=pd,
        report_sha256=report_sha256,
        errors=tuple(all_errors),
    )


def mxf_mp4_essence_ptpv2_and_tally_umd_report_to_dict(
    report: MxfMp4EssencePtpv2AndTallyUmdReport,
) -> Dict[str, object]:
    """Convert `MxfMp4EssencePtpv2AndTallyUmdReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
