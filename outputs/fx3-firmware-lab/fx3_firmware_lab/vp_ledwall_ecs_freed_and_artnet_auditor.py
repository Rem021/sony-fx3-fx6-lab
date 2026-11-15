"""Phase 128 — 25th Unified Firmware-Lab Auditor: Virtual Production LED-Volume
Brompton/Megapixel PWM Anti-Banding Fractional ECS Solver, Wired FreeD (D1 29-Byte)
Lens/Camera Tracking Telemetry -> Unreal LiveLink, & P12-Safe Art-Net 4 / sACN
Lighting-Cue Frame-Boundary Shutter-Sync Auditor.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`,
  `libInfraLensCommunicator.so`, `global.xdb`, `string_english.uxc`,
  `string_english_g.uxc`) and FX6 v6.01 (`appFw.so`, `libmpr.so`,
  `libNetServiceEther.so`, `global.xdb`, `string_english.uxc`,
  `string_english_2.uxc`) strictly via `os.O_RDONLY` + `mmap.ACCESS_READ` and
  ELF64 `.rodata`/`.dynstr` section-scoped scanning plus `uxa\\x07`/`.uxc`
  container parsing (< 0.35s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / `global.xdb` / `.uxc`
  fixtures carrying the exact verified contract markers and runs the identical
  four-pillar verification pipeline (< 0.02s warm, zero proprietary files
  required).

Audits Four Phase 128 Pillars:
1. Pillar A — Virtual Production LED-Volume (`Crystal LED VERONA/CAPRI`,
   `Brompton Tessera SX40 ShutterSync`, `Megapixel HELIOS Camera Mode`)
   `IMX510` Readout-Skew (`8.7ms` / `13.2ms` / `4.35ms` / `2.20ms`) & LED
   Scan-Multiplexing (`1/1..1/32`, `960..7680 Hz`) Anti-Banding Fractional
   `ECS` (`23.98..7680.0 Hz`) Harmonic Safe-Shutter Solver:
   - Maps FX6 `BKID_APP_SETTING_ECS` / `EVENT_REMOTE_SHUTTER_ECS_FREQUENCY`
     and FX3 `ANTI_FLICKER_SET_HIGH_RES_SS_ON` (`Anti-flicker Tv Scan`).
   - Solves exact fractional `ECS` frequencies aligned to sub-harmonics of the
     LED panel multiplexer cycle (`f_mux = f_pwm / scan_div`) and prevents
     sub-multiplex dark scanline banding, non-genlocked beat drift, and
     out-of-range ECS frequencies.
2. Pillar B — Wired `FreeD` (`0xD1` 29-Byte Big-Endian UDP Packet with
   Modulo-256 `0x40 - sum` Checksum) E-Mount 12-Pin Focus/Zoom/Iris -> Unreal
   Engine `LiveLinkFreeD` Bridge over Wired `CDC-NCM` (`P12` Wi-Fi-OFF):
   - Encodes and verifies bit-exact 29-byte `0xD1` frames carrying signed 24-bit
     Pan/Tilt/Roll (`deg * 32768`), signed 24-bit X/Y/Z (`mm * 64`), 24-bit
     Zoom/Focus encoder ticks, and Sony 16-bit Spare/User-Defined Iris +
     4-bit frame counter.
   - Maps E-Mount 12-pin telemetry (`libInfraLensCommunicator.so`,
     `EVENT_REMOTE_ABSOLUTE_FOCUS_POSITION`, `EVENT_REMOTE_ZOOM_POSITION_SETTING`,
     `EVENT_REMOTE_IRIS_POSITION`) and enforces `P12` Wi-Fi-OFF
     (`wf12_00342260_risk == 0`) on wired `CDC-NCM` / `RNDIS`.
3. Pillar C — `Art-Net 4` (`Art-Net\\0`, `OpDmx 0x5000`, `ArtSync 0x5200`,
   `UDP 6454`) & `sACN` (`ANSI E1.31`, `UDP 5568`, Multicast `239.255.x.y`,
   Priority `0..200`, Sync Universe) Lighting-Flash & Frame-Boundary
   Shutter-Sync Guard under Strict `P12` Wi-Fi-OFF (`wf12_00342260_risk == 0`):
   - Synthesizes and parses bit-exact `Art-Net 4 OpDmx` and `ANSI E1.31 sACN`
     packets, enforces `ArtSync` / `E1.31` Sync Universe frame latching, and
     blocks mid-readout rolling-shutter flash tearing across `IMX510` readout
     windows.
4. Pillar D — Volatile RAM Staging & Zero Persistent `eMMC` / Calibration
   Mutation Proof (`emmc_mutation_bytes == 0`, `calibration_mutation_bytes == 0`,
   `persistent_emmc_writes_authorized == False`).
"""

from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

from .emount_af_breathing_and_ibis_auditor import (
    FX3_LENS_COMM_RELPATH,
    _extract_uxc_labels,
    _parse_elf64_sections,
)
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
from .sensor_codec_compatibility_analyzer import FX3_LIBMPR_RELPATH, FX6_LIBMPR_RELPATH


PHASE_128_SCHEMA = "fx3_firmware_lab_phase128_vp_ledwall_freed_artnet_v1"
PHASE_128_VERSION = "128.0.0"

# ---------------------------------------------------------------------------
# Pillar A Constants: VP LED-Volume, IMX510 Readout & Fractional ECS Solver
# ---------------------------------------------------------------------------

ECS_FRACTIONAL_MIN_HZ = 23.98
ECS_FRACTIONAL_MAX_HZ = 7680.0
LED_PWM_MIN_HZ = 960.0
LED_PWM_MAX_HZ = 7680.0
ECS_HARMONIC_MAX_ERR_PCT = 0.50
NON_GENLOCK_MAX_BEAT_HZ = 1.25

IMX510_VP_READOUT_MS_SPECS: Dict[str, float] = {
    "4K_24P_60P_FF": 8.70,
    "4K_120P_SQ": 4.35,
    "FHD_240P_SQ": 2.20,
    "OVERSAMPLED_REF_13_2MS": 13.20,
}

VALID_LED_CONTROLLERS: Tuple[str, ...] = (
    "BROMPTON_TESSERA_SX40",
    "MEGAPIXEL_HELIOS",
    "GENERIC_NON_GENLOCK_LED",
)
VALID_LED_SCAN_DIVISORS: Tuple[int, ...] = (1, 2, 4, 8, 16, 32)
VALID_VP_CAMERA_FPS: Tuple[float, ...] = (23.976, 24.0, 25.0, 29.97, 50.0, 59.94)

# ---------------------------------------------------------------------------
# Pillar B Constants: FreeD (0xD1) 29-Byte Protocol & E-Mount FIZ Bridge
# ---------------------------------------------------------------------------

FREED_D1_PACKET_BYTES = 29
FREED_D1_MESSAGE_TYPE = 0xD1
FREED_D1_CHECKSUM_SEED = 0x40
FREED_DEFAULT_UDP_PORT = 40000
FREED_ANGLE_SCALE = 32768.0
FREED_POS_SCALE_MM = 64.0
FREED_24BIT_UMAX = 0xFFFFFF
FREED_24BIT_SMAX = 0x7FFFFF
FREED_24BIT_SMIN = -0x800000

VALID_VP_TRANSPORTS: Tuple[str, ...] = (
    "CDC_NCM_RTL8153",
    "CDC_NCM_AX88179",
    "USB_RNDIS_WIRED",
    "WIFI_WLAN0",
    "BT_PAN",
)
WIRED_VP_TRANSPORTS: Tuple[str, ...] = (
    "CDC_NCM_RTL8153",
    "CDC_NCM_AX88179",
    "USB_RNDIS_WIRED",
)
FORBIDDEN_RF_VP_TRANSPORTS: Tuple[str, ...] = ("WIFI_WLAN0", "BT_PAN")

EMOUNT_VP_LENS_PROFILES: Dict[str, Tuple[float, float, float, float, bool]] = {
    # lens_id: (focal_min_mm, focal_max_mm, f_min, f_max, is_chipped_emount)
    "SEL2470GM2": (24.0, 70.0, 2.8, 22.0, True),
    "SELP28135G": (28.0, 135.0, 4.0, 22.0, True),
    "SEL50F12GM": (50.0, 50.0, 1.2, 16.0, True),
    "MANUAL_PL_UNCHIPPED": (35.0, 35.0, 2.0, 22.0, False),
}

# ---------------------------------------------------------------------------
# Pillar C Constants: Art-Net 4 (UDP 6454) & sACN (ANSI E1.31 UDP 5568)
# ---------------------------------------------------------------------------

ARTNET_HEADER = b"Art-Net\x00"
ARTNET_UDP_PORT = 6454
ARTNET_OPCODE_OPDMX = 0x5000
ARTNET_OPCODE_ARTSYNC = 0x5200
ARTNET_PROT_VER = 14
ARTNET_MAX_UNIVERSE_CHANNELS = 512

SACN_UDP_PORT = 5568
SACN_ACN_PACKET_ID = b"ASC-E1.17\x00\x00\x00"
SACN_VECTOR_ROOT_E131_DATA = 0x00000004
SACN_VECTOR_E131_DATA_PACKET = 0x00000002
SACN_VECTOR_DMP_SET_PROPERTY = 0x02
SACN_UNIVERSE_MIN = 1
SACN_UNIVERSE_MAX = 63999
SACN_PRIORITY_DEFAULT = 100
SACN_PRIORITY_MAX = 200
LIGHTING_SYNC_MAX_JITTER_MS = 0.50

VALID_LIGHTING_PROTOCOLS: Tuple[str, ...] = ("ARTNET_4", "SACN_E131")

# ---------------------------------------------------------------------------
# Pillar D Constants: Volatile RAM Staging & Zero Persistent eMMC Guard
# ---------------------------------------------------------------------------

VOLATILE_STAGING_PREFIXES_P128: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_PERSISTENT_EMMC_RE_P128 = re.compile(
    r"(?:^|/)(?:p(?:[1-9]|1[0-8])|nflasha\d*|cnflasha\d*|mmcblk0(?:p\d+|rpmb)?|mtdblock\d*)(?:/|:|$)"
    r"|bodydata\.dat|udtrfirm|psd\.bin|defdet\.bin|backup\.bin|jiritsu|updater://|nvram://|eeprom://",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Verified Binary & .uxc Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_PHASE128_MARKERS: Tuple[str, ...] = (
    "ANTI_FLICKER_SET_HIGH_RES_SS_ON",
    "EVENT_FUNC_ANTI_FLICKER_SET_HIGH_RES_SS_SET_ON",
    "EVENT_REMOTE_SHUTTER_ANGLE",
    "EVENT_REMOTE_ABSOLUTE_FOCUS_POSITION",
    "EVENT_REMOTE_IRIS_POSITION",
    "EVENT_REMOTE_ZOOM_POSITION_SETTING",
    "EXTERN_SETTING_AIRPLANE_MODE_ON",
)

FX6_APPFW_PHASE128_MARKERS: Tuple[str, ...] = (
    "BKID_APP_SETTING_ECS",
    "BKID_APP_SETTING_ECS_FREQUENCY",
    "EVENT_REMOTE_SHUTTER_ECS_FREQUENCY",
    "BKID_APP_SETTING_SHUTTER_ANGLE",
    "BKID_APP_SETTING_FOCUS_POSITION_DISPLAY",
    "BKID_APP_SETTING_LENS_ZOOM_POSITION_DISPLAY",
)

FX3_LIBMPR_PHASE128_MARKERS: Tuple[str, ...] = (
    "FocalLength",
    "HighResolutionShutterSpeedMode",
    "ul_FocalLengthIn35mmFilm",
)

FX6_LIBMPR_PHASE128_MARKERS: Tuple[str, ...] = (
    "ConvertReadoutDuration",
    "NormalImageControl_EffectivePixelReadoutTime",
    "NormalImageControl_FocalLength",
    "NormalImageControl_FocusDistance",
    "PhaseDifferenceImageControl_IrisControlValue",
    "HighResolutionShutterSpeedMode",
)

FX3_LENS_COMM_PHASE128_MARKERS: Tuple[str, ...] = (
    "_ZN16LensCommunicator18GetMountedLensInfoEPv",
    "_ZN16LensCommunicator10SndSyncMsgEPvj",
)

FX6_LIBNET_ETHER_PHASE128_MARKERS: Tuple[str, ...] = (
    "32mCT_ID_ASYNC_REQ_SETUP_WIRED_ETHER_IF",
    "32mEN_EVT_WER_START_WIRED_LAN_COMP",
)

FX3_NS39_PHASE128_LABELS: Dict[int, str] = {
    0x0004E116: "Using the lens focal length",
    0x0004E39A: "WireLAN(USB-LAN)",
}

FX3_NS3_PHASE128_LABELS: Dict[int, str] = {
    0x000060A8: "\ue801Anti-flicker Tv Scan",
    0x0000645F: "USB-LAN/Tethering",
}

FX6_NS1_PHASE128_LABELS: Dict[int, str] = {
    0x00002077: "ECS",
    0x000022DB: "ECS On/Off",
    0x0000224E: "Focal Length",
    0x000020D1: "IRIS",
}

FX6_NS2_PHASE128_LABELS: Dict[int, str] = {
    0x00004D96: "Shutter Angle",
    0x00004D98: "ECS Frequency",
    0x00004538: "Focus Position",
    0x0000453C: "Iris Position",
    0x000042D3: "Airplane Mode",
}

# ---------------------------------------------------------------------------
# Dataclasses (JSON-clean: no raw bytes attributes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class VpLedwallEcsEvalResult:
    valid: bool
    status: str
    led_controller: str
    readout_mode: str
    imx510_readout_ms: float
    camera_fps: float
    target_shutter_angle_deg: float
    led_pwm_refresh_hz: float
    scan_multiplex_ratio: int
    effective_mux_cycle_hz: float
    genlock_spg_locked: bool
    solved_ecs_hz: float
    effective_exposure_ms: float
    harmonic_k_cycles: int
    harmonic_error_pct: float
    beat_drift_hz: float
    fx3_var_shutter_equivalent_hz: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class VpLedwallEcsSolverReport:
    passed: bool
    fx3_appfw_ecs_markers: Tuple[str, ...]
    fx6_appfw_ecs_markers: Tuple[str, ...]
    fx3_libmpr_ecs_markers: Tuple[str, ...]
    fx6_libmpr_ecs_markers: Tuple[str, ...]
    uxc_ecs_labels: Dict[str, str]
    eval_brompton_verona_7680hz_8_7ms: VpLedwallEcsEvalResult
    eval_helios_subframe_3840hz_13_2ms: VpLedwallEcsEvalResult
    eval_non_genlock_fractional_ecs: VpLedwallEcsEvalResult
    blocked_sub_mux_scanline_banding: VpLedwallEcsEvalResult
    blocked_harmonic_beat_banding: VpLedwallEcsEvalResult
    blocked_ecs_out_of_range: VpLedwallEcsEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FreedD1PacketDecoded:
    valid: bool
    message_type: int
    camera_id: int
    pan_deg: float
    tilt_deg: float
    roll_deg: float
    pos_x_mm: float
    pos_y_mm: float
    pos_z_mm: float
    zoom_ticks_24bit: int
    focus_ticks_24bit: int
    spare_u16: int
    iris_12bit: int
    frame_counter_4bit: int
    checksum_byte: int
    expected_checksum_byte: int
    packet_bytes_len: int
    packet_hex: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FreedLiveLinkEvalResult:
    valid: bool
    status: str
    lens_id: str
    focal_length_mm: float
    focus_distance_m: float
    f_stop: float
    external_fiz_encoder: bool
    transport_driver: str
    p12_airplane_rf_off: bool
    wf12_00342260_risk: int
    udp_port: int
    decoded_packet: FreedD1PacketDecoded
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FreedLiveLinkBridgeReport:
    passed: bool
    fx3_appfw_lens_markers: Tuple[str, ...]
    fx6_appfw_lens_markers: Tuple[str, ...]
    fx3_lens_comm_markers: Tuple[str, ...]
    fx6_libnet_ether_markers: Tuple[str, ...]
    uxc_lens_lan_labels: Dict[str, str]
    eval_sel2470gm2_cdc_ncm_livelink: FreedLiveLinkEvalResult
    eval_selp28135g_rndis_livelink: FreedLiveLinkEvalResult
    eval_manual_pl_with_external_fiz: FreedLiveLinkEvalResult
    blocked_wifi_wlan0_p12_violation: FreedLiveLinkEvalResult
    blocked_unchipped_lens_no_encoder: FreedLiveLinkEvalResult
    blocked_corrupt_freed_d1_checksum: FreedLiveLinkEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ArtnetOpDmxDecoded:
    valid: bool
    opcode: int
    protocol_version: int
    sequence: int
    physical: int
    net: int
    sub_uni: int
    port_address_15bit: int
    dmx_length: int
    dmx_first_4_channels: Tuple[int, ...]
    packet_hex: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SacnE131Decoded:
    valid: bool
    universe: int
    priority: int
    sequence: int
    sync_universe: int
    multicast_ip: str
    source_name: str
    dmx_length: int
    dmx_first_4_channels: Tuple[int, ...]
    packet_hex: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ArtnetSacnSyncEvalResult:
    valid: bool
    status: str
    protocol: str
    transport_driver: str
    p12_airplane_rf_off: bool
    wf12_00342260_risk: int
    readout_mode: str
    imx510_readout_ms: float
    camera_fps: float
    frame_period_ms: float
    cue_phase_offset_ms: float
    cue_hold_duration_ms: float
    frame_sync_latched: bool
    sync_jitter_ms: float
    rolling_shutter_tear_risk: bool
    artnet_decoded: Optional[ArtnetOpDmxDecoded]
    sacn_decoded: Optional[SacnE131Decoded]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ArtnetSacnShutterSyncReport:
    passed: bool
    fx3_appfw_sync_markers: Tuple[str, ...]
    fx6_libnet_ether_markers: Tuple[str, ...]
    uxc_airplane_lan_labels: Dict[str, str]
    eval_artnet4_opdmx_artsync_cdc_ncm: ArtnetSacnSyncEvalResult
    eval_sacn_e131_sync_univ_cdc_ncm: ArtnetSacnSyncEvalResult
    blocked_rolling_shutter_flash_tear: ArtnetSacnSyncEvalResult
    blocked_unsynced_multi_universe_dmx: ArtnetSacnSyncEvalResult
    blocked_wifi_wlan0_p12_lighting: ArtnetSacnSyncEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase128WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZeroMutationVpGuardReport:
    passed: bool
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    volatile_staging_guard: Phase128WriteGuardResult
    blocked_bodydata_dat_guard: Phase128WriteGuardResult
    blocked_nflasha15_guard: Phase128WriteGuardResult
    blocked_cnflasha0_guard: Phase128WriteGuardResult
    blocked_backup_bin_guard: Phase128WriteGuardResult
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class VpLedwallEcsFreedAndArtnetReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    donor_file_sizes: Dict[str, int]
    pillar_a_vp_ledwall_ecs_solver: VpLedwallEcsSolverReport
    pillar_b_freed_livelink_bridge: FreedLiveLinkBridgeReport
    pillar_c_artnet_sacn_shutter_sync: ArtnetSacnShutterSyncReport
    pillar_d_zero_mutation_vp_guard: ZeroMutationVpGuardReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only ELF64 / Donor Scanner Helpers (`os.O_RDONLY` + `mmap`)
# ---------------------------------------------------------------------------


def _read_bytes_rdonly(path: Path) -> bytes:
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size == 0:
            return b""
        mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        try:
            return bytes(mm)
        finally:
            mm.close()
    finally:
        os.close(fd)


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Dict[str, Tuple[str, ...]],
    *,
    is_elf: bool = True,
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    """Scan ELF64 `.rodata`/`.dynstr` (or raw buffer) strictly `os.O_RDONLY` + `mmap.ACCESS_READ`."""
    fd = os.open(path, os.O_RDONLY)
    try:
        st = os.fstat(fd)
        size = int(st.st_size)
        if size == 0:
            return 0, {k: () for k in marker_groups}
        mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        try:
            windows: List[Tuple[int, int]] = []
            if is_elf:
                try:
                    sections = _parse_elf64_sections(mm)
                except ValueError:
                    sections = {}
                for sec_name in (".rodata", ".dynstr", ".data.rel.ro", ".strtab"):
                    if sec_name in sections:
                        off, sec_sz = sections[sec_name]
                        if sec_sz > 0 and off + sec_sz <= size:
                            windows.append((off, off + sec_sz))
            if not windows:
                windows = [(0, size)]

            found: Dict[str, Tuple[str, ...]] = {}
            for group_name, tokens in marker_groups.items():
                matched: List[str] = []
                for tok in tokens:
                    needle = tok.encode("latin1")
                    if any(mm.find(needle, start, end) != -1 for start, end in windows):
                        matched.append(tok)
                found[group_name] = tuple(matched)
            return size, found
        finally:
            mm.close()
    finally:
        os.close(fd)


def _scan_bytes_marker_groups(
    data: bytes,
    marker_groups: Dict[str, Tuple[str, ...]],
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    found: Dict[str, Tuple[str, ...]] = {}
    for group_name, tokens in marker_groups.items():
        found[group_name] = tuple(tok for tok in tokens if tok.encode("latin1") in data)
    return len(data), found


# ---------------------------------------------------------------------------
# Pillar A Functions: VP LED-Volume IMX510 & Fractional ECS Safe-Shutter Solver
# ---------------------------------------------------------------------------


def solve_vp_ledwall_ecs_shutter(
    *,
    led_controller: str = "BROMPTON_TESSERA_SX40",
    readout_mode: str = "4K_24P_60P_FF",
    camera_fps: float = 23.976,
    target_shutter_angle_deg: float = 180.0,
    led_pwm_refresh_hz: float = 7680.0,
    scan_multiplex_ratio: int = 16,
    genlock_spg_locked: bool = True,
    candidate_ecs_hz: Optional[float] = None,
) -> VpLedwallEcsEvalResult:
    """Solve or validate a fractional Extended Clear Scan (ECS) shutter frequency
    that avoids rolling-shutter scanline banding on Brompton/Megapixel LED volumes.
    """
    ctrl = led_controller.strip().upper()
    rmode = readout_mode.strip().upper()
    if ctrl not in VALID_LED_CONTROLLERS:
        raise ValueError(f"Unsupported led_controller={led_controller!r}")
    if rmode not in IMX510_VP_READOUT_MS_SPECS:
        raise ValueError(f"Unsupported readout_mode={readout_mode!r}")
    if scan_multiplex_ratio not in VALID_LED_SCAN_DIVISORS:
        raise ValueError(f"Unsupported scan_multiplex_ratio={scan_multiplex_ratio!r}")
    if camera_fps <= 0.0:
        raise ValueError("camera_fps must be positive")
    if not (5.6 <= target_shutter_angle_deg <= 360.0):
        raise ValueError("target_shutter_angle_deg must be in [5.6, 360.0]")

    readout_ms = IMX510_VP_READOUT_MS_SPECS[rmode]
    effective_mux_hz = led_pwm_refresh_hz / float(scan_multiplex_ratio)
    nominal_ecs_hz = camera_fps * (360.0 / target_shutter_angle_deg)

    errors: List[str] = []
    if not (LED_PWM_MIN_HZ <= led_pwm_refresh_hz <= LED_PWM_MAX_HZ):
        errors.append(
            f"BLOCKED_LED_PWM_OUT_OF_RANGE: led_pwm_refresh_hz={led_pwm_refresh_hz:.2f} "
            f"outside [{LED_PWM_MIN_HZ:.1f}, {LED_PWM_MAX_HZ:.1f}] Hz"
        )

    if candidate_ecs_hz is None:
        # Snap nominal exposure duration to nearest integer k >= 1 of LED mux scan cycles
        ideal_k = max(1, round(effective_mux_hz / nominal_ecs_hz))
        solved_ecs = round(effective_mux_hz / float(ideal_k), 2)
        if not (ECS_FRACTIONAL_MIN_HZ <= solved_ecs <= ECS_FRACTIONAL_MAX_HZ):
            solved_ecs = min(ECS_FRACTIONAL_MAX_HZ, max(ECS_FRACTIONAL_MIN_HZ, round(nominal_ecs_hz, 2)))
    else:
        solved_ecs = round(float(candidate_ecs_hz), 4)

    if not (ECS_FRACTIONAL_MIN_HZ <= solved_ecs <= ECS_FRACTIONAL_MAX_HZ):
        errors.append(
            f"BLOCKED_ECS_OUT_OF_RANGE: solved_ecs_hz={solved_ecs:.2f} outside "
            f"[{ECS_FRACTIONAL_MIN_HZ:.2f}, {ECS_FRACTIONAL_MAX_HZ:.1f}] Hz"
        )

    effective_exposure_ms = 1000.0 / solved_ecs if solved_ecs > 0.0 else 0.0
    k_float = effective_mux_hz / solved_ecs if solved_ecs > 0.0 else 0.0
    harmonic_k = max(1, round(k_float))
    nearest_harmonic_hz = effective_mux_hz / float(harmonic_k)
    harmonic_error_pct = (
        abs(solved_ecs - nearest_harmonic_hz) / nearest_harmonic_hz * 100.0
        if nearest_harmonic_hz > 0.0
        else 100.0
    )
    beat_drift_hz = abs(solved_ecs - nearest_harmonic_hz)

    # Check sub-multiplexer exposure (shorter than 1 full scan cycle -> dark scanline bar)
    # Note: Brompton ShutterSync / Megapixel HELIOS Camera Mode with genlock can sync
    # sub-frame slices when PWM >= 3840 Hz, whereas un-synced or sub-mux exposure bands.
    if solved_ecs > effective_mux_hz * 1.005 and not (
        genlock_spg_locked and ctrl in ("BROMPTON_TESSERA_SX40", "MEGAPIXEL_HELIOS") and led_pwm_refresh_hz >= 3840.0
    ):
        errors.append(
            f"BLOCKED_SUB_MUX_SCANLINE_BANDING: exposure {effective_exposure_ms:.3f}ms "
            f"({solved_ecs:.2f}Hz) is shorter than LED mux period {1000.0 / effective_mux_hz:.3f}ms "
            f"({effective_mux_hz:.2f}Hz)"
        )
    elif harmonic_error_pct > ECS_HARMONIC_MAX_ERR_PCT:
        errors.append(
            f"BLOCKED_HARMONIC_BEAT_BANDING: solved_ecs_hz={solved_ecs:.2f}Hz deviates "
            f"{harmonic_error_pct:.2f}% (beat {beat_drift_hz:.2f}Hz) from nearest mux sub-harmonic "
            f"{nearest_harmonic_hz:.2f}Hz (k={harmonic_k})"
        )

    if (not genlock_spg_locked) and beat_drift_hz > NON_GENLOCK_MAX_BEAT_HZ:
        errors.append(
            f"BLOCKED_NON_GENLOCK_PHASE_DRIFT: free-running beat_drift_hz={beat_drift_hz:.2f} > "
            f"{NON_GENLOCK_MAX_BEAT_HZ:.2f} Hz"
        )

    status = "VP_LEDWALL_ECS_HARMONIC_SAFE" if not errors else errors[0].split(":", 1)[0]
    return VpLedwallEcsEvalResult(
        valid=len(errors) == 0,
        status=status,
        led_controller=ctrl,
        readout_mode=rmode,
        imx510_readout_ms=readout_ms,
        camera_fps=camera_fps,
        target_shutter_angle_deg=target_shutter_angle_deg,
        led_pwm_refresh_hz=led_pwm_refresh_hz,
        scan_multiplex_ratio=scan_multiplex_ratio,
        effective_mux_cycle_hz=round(effective_mux_hz, 4),
        genlock_spg_locked=genlock_spg_locked,
        solved_ecs_hz=round(solved_ecs, 2),
        effective_exposure_ms=round(effective_exposure_ms, 4),
        harmonic_k_cycles=harmonic_k,
        harmonic_error_pct=round(harmonic_error_pct, 4),
        beat_drift_hz=round(beat_drift_hz, 4),
        fx3_var_shutter_equivalent_hz=round(solved_ecs, 2),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar B Functions: FreeD (0xD1 29-Byte) & Wired E-Mount LiveLink Bridge
# ---------------------------------------------------------------------------


def _pack_signed_24be(value: int) -> bytes:
    clamped = max(FREED_24BIT_SMIN, min(FREED_24BIT_SMAX, int(value)))
    if clamped < 0:
        clamped += 1 << 24
    return bytes(((clamped >> 16) & 0xFF, (clamped >> 8) & 0xFF, clamped & 0xFF))


def _unpack_signed_24be(raw3: bytes) -> int:
    val = (raw3[0] << 16) | (raw3[1] << 8) | raw3[2]
    if val & 0x800000:
        val -= 1 << 24
    return val


def _pack_unsigned_24be(value: int) -> bytes:
    clamped = max(0, min(FREED_24BIT_UMAX, int(value)))
    return bytes(((clamped >> 16) & 0xFF, (clamped >> 8) & 0xFF, clamped & 0xFF))


def _unpack_unsigned_24be(raw3: bytes) -> int:
    return (raw3[0] << 16) | (raw3[1] << 8) | raw3[2]


def compute_freed_d1_checksum(packet_prefix_28: bytes) -> int:
    """Compute official FreeD D1 8-bit modulo-256 checksum: `(0x40 - sum(bytes[0..27])) & 0xFF`."""
    if len(packet_prefix_28) != 28:
        raise ValueError(f"Expected 28 prefix bytes, got {len(packet_prefix_28)}")
    return (FREED_D1_CHECKSUM_SEED - sum(packet_prefix_28)) & 0xFF


def build_freed_d1_packet(
    *,
    camera_id: int = 1,
    pan_deg: float = 0.0,
    tilt_deg: float = 0.0,
    roll_deg: float = 0.0,
    pos_x_mm: float = 0.0,
    pos_y_mm: float = 0.0,
    pos_z_mm: float = 1500.0,
    zoom_ticks_24bit: int = 0x400000,
    focus_ticks_24bit: int = 0x200000,
    iris_12bit: int = 0x400,
    frame_counter_4bit: int = 0,
    corrupt_checksum: bool = False,
) -> bytes:
    """Build a 29-byte FreeD D1 big-endian UDP telemetry packet."""
    if not (0 <= camera_id <= 0xFF):
        raise ValueError("camera_id must be 0..255")
    if not (0 <= iris_12bit <= 0xFFF):
        raise ValueError("iris_12bit must be 0..4095")
    if not (0 <= frame_counter_4bit <= 0x0F):
        raise ValueError("frame_counter_4bit must be 0..15")

    spare_u16 = ((frame_counter_4bit & 0x0F) << 12) | (iris_12bit & 0x0FFF)
    prefix = bytearray()
    prefix.append(FREED_D1_MESSAGE_TYPE)
    prefix.append(camera_id & 0xFF)
    prefix.extend(_pack_signed_24be(round(pan_deg * FREED_ANGLE_SCALE)))
    prefix.extend(_pack_signed_24be(round(tilt_deg * FREED_ANGLE_SCALE)))
    prefix.extend(_pack_signed_24be(round(roll_deg * FREED_ANGLE_SCALE)))
    prefix.extend(_pack_signed_24be(round(pos_x_mm * FREED_POS_SCALE_MM)))
    prefix.extend(_pack_signed_24be(round(pos_y_mm * FREED_POS_SCALE_MM)))
    prefix.extend(_pack_signed_24be(round(pos_z_mm * FREED_POS_SCALE_MM)))
    prefix.extend(_pack_unsigned_24be(zoom_ticks_24bit))
    prefix.extend(_pack_unsigned_24be(focus_ticks_24bit))
    prefix.extend(struct.pack(">H", spare_u16))

    csum = compute_freed_d1_checksum(bytes(prefix))
    if corrupt_checksum:
        csum = (csum ^ 0x5A) & 0xFF
    return bytes(prefix) + bytes((csum,))


def parse_and_verify_freed_d1_packet(raw_packet: bytes) -> FreedD1PacketDecoded:
    """Decode and strictly verify a 29-byte FreeD D1 packet."""
    errors: List[str] = []
    if len(raw_packet) != FREED_D1_PACKET_BYTES:
        errors.append(
            f"BLOCKED_FREED_D1_LENGTH_MISMATCH: expected {FREED_D1_PACKET_BYTES}B, got {len(raw_packet)}B"
        )
        return FreedD1PacketDecoded(
            valid=False,
            message_type=raw_packet[0] if raw_packet else 0,
            camera_id=raw_packet[1] if len(raw_packet) > 1 else 0,
            pan_deg=0.0,
            tilt_deg=0.0,
            roll_deg=0.0,
            pos_x_mm=0.0,
            pos_y_mm=0.0,
            pos_z_mm=0.0,
            zoom_ticks_24bit=0,
            focus_ticks_24bit=0,
            spare_u16=0,
            iris_12bit=0,
            frame_counter_4bit=0,
            checksum_byte=raw_packet[-1] if raw_packet else 0,
            expected_checksum_byte=0,
            packet_bytes_len=len(raw_packet),
            packet_hex=raw_packet.hex(),
            errors=tuple(errors),
        )

    msg_type = raw_packet[0]
    cam_id = raw_packet[1]
    if msg_type != FREED_D1_MESSAGE_TYPE:
        errors.append(f"BLOCKED_FREED_D1_MESSAGE_TYPE: expected 0xD1, got 0x{msg_type:02X}")

    expected_csum = compute_freed_d1_checksum(raw_packet[:28])
    actual_csum = raw_packet[28]
    if actual_csum != expected_csum:
        errors.append(
            f"BLOCKED_FREED_D1_CHECKSUM_MISMATCH: expected 0x{expected_csum:02X}, got 0x{actual_csum:02X}"
        )

    pan_deg = _unpack_signed_24be(raw_packet[2:5]) / FREED_ANGLE_SCALE
    tilt_deg = _unpack_signed_24be(raw_packet[5:8]) / FREED_ANGLE_SCALE
    roll_deg = _unpack_signed_24be(raw_packet[8:11]) / FREED_ANGLE_SCALE
    pos_x_mm = _unpack_signed_24be(raw_packet[11:14]) / FREED_POS_SCALE_MM
    pos_y_mm = _unpack_signed_24be(raw_packet[14:17]) / FREED_POS_SCALE_MM
    pos_z_mm = _unpack_signed_24be(raw_packet[17:20]) / FREED_POS_SCALE_MM
    zoom_ticks = _unpack_unsigned_24be(raw_packet[20:23])
    focus_ticks = _unpack_unsigned_24be(raw_packet[23:26])
    (spare_u16,) = struct.unpack_from(">H", raw_packet, 26)
    frame_counter = (spare_u16 >> 12) & 0x0F
    iris_12bit = spare_u16 & 0x0FFF

    return FreedD1PacketDecoded(
        valid=len(errors) == 0,
        message_type=msg_type,
        camera_id=cam_id,
        pan_deg=round(pan_deg, 5),
        tilt_deg=round(tilt_deg, 5),
        roll_deg=round(roll_deg, 5),
        pos_x_mm=round(pos_x_mm, 4),
        pos_y_mm=round(pos_y_mm, 4),
        pos_z_mm=round(pos_z_mm, 4),
        zoom_ticks_24bit=zoom_ticks,
        focus_ticks_24bit=focus_ticks,
        spare_u16=spare_u16,
        iris_12bit=iris_12bit,
        frame_counter_4bit=frame_counter,
        checksum_byte=actual_csum,
        expected_checksum_byte=expected_csum,
        packet_bytes_len=len(raw_packet),
        packet_hex=raw_packet.hex(),
        errors=tuple(errors),
    )


def map_emount_fiz_to_freed_ticks(
    *,
    lens_id: str,
    focal_length_mm: float,
    focus_distance_m: float,
    f_stop: float,
) -> Tuple[int, int, int]:
    """Map physical E-Mount focal length, focus distance, and T/F-stop to FreeD 24-bit ticks + 12-bit Iris."""
    if lens_id not in EMOUNT_VP_LENS_PROFILES:
        raise ValueError(f"Unsupported lens_id={lens_id!r}")
    fmin, fmax, ap_min, ap_max, _chipped = EMOUNT_VP_LENS_PROFILES[lens_id]

    if fmax > fmin:
        z_norm = max(0.0, min(1.0, (focal_length_mm - fmin) / (fmax - fmin)))
    else:
        z_norm = 0.5
    zoom_ticks = round(z_norm * FREED_24BIT_UMAX)

    # Inverse-distance focus encoder curve (0.25m near -> 100m+ infinity)
    clamped_dist = max(0.25, min(1000.0, focus_distance_m))
    f_norm = max(0.0, min(1.0, (1.0 / clamped_dist) / (1.0 / 0.25)))
    focus_ticks = round((1.0 - f_norm) * FREED_24BIT_UMAX)

    if ap_max > ap_min:
        i_norm = max(0.0, min(1.0, math.log2(max(ap_min, min(ap_max, f_stop)) / ap_min) / math.log2(ap_max / ap_min)))
    else:
        i_norm = 0.0
    iris_12bit = round(i_norm * 0xFFF)
    return zoom_ticks, focus_ticks, iris_12bit


def evaluate_freed_livelink_bridge(
    *,
    lens_id: str = "SEL2470GM2",
    focal_length_mm: float = 35.0,
    focus_distance_m: float = 2.5,
    f_stop: float = 2.8,
    external_fiz_encoder: bool = False,
    transport_driver: str = "CDC_NCM_RTL8153",
    p12_airplane_rf_off: bool = True,
    camera_id: int = 1,
    pan_deg: float = 12.5,
    tilt_deg: float = -3.25,
    roll_deg: float = 0.0,
    pos_x_mm: float = 120.0,
    pos_y_mm: float = -450.0,
    pos_z_mm: float = 1650.0,
    frame_counter_4bit: int = 5,
    udp_port: int = FREED_DEFAULT_UDP_PORT,
    corrupt_checksum: bool = False,
) -> FreedLiveLinkEvalResult:
    """Evaluate E-Mount 12-Pin / External FIZ -> FreeD D1 -> Unreal LiveLink over Wired P12 LAN."""
    if lens_id not in EMOUNT_VP_LENS_PROFILES:
        raise ValueError(f"Unsupported lens_id={lens_id!r}")
    norm_drv = transport_driver.strip().upper()
    if norm_drv not in VALID_VP_TRANSPORTS:
        raise ValueError(f"Unsupported transport_driver={transport_driver!r}")

    _fmin, _fmax, _apmin, _apmax, is_chipped = EMOUNT_VP_LENS_PROFILES[lens_id]
    zoom_t, focus_t, iris_12 = map_emount_fiz_to_freed_ticks(
        lens_id=lens_id,
        focal_length_mm=focal_length_mm,
        focus_distance_m=focus_distance_m,
        f_stop=f_stop,
    )
    pkt = build_freed_d1_packet(
        camera_id=camera_id,
        pan_deg=pan_deg,
        tilt_deg=tilt_deg,
        roll_deg=roll_deg,
        pos_x_mm=pos_x_mm,
        pos_y_mm=pos_y_mm,
        pos_z_mm=pos_z_mm,
        zoom_ticks_24bit=zoom_t,
        focus_ticks_24bit=focus_t,
        iris_12bit=iris_12,
        frame_counter_4bit=frame_counter_4bit,
        corrupt_checksum=corrupt_checksum,
    )
    decoded = parse_and_verify_freed_d1_packet(pkt)
    errors: List[str] = list(decoded.errors)

    if not is_chipped and not external_fiz_encoder:
        errors.append(
            f"BLOCKED_UNCHIPPED_LENS_NO_FIZ_ENCODER: {lens_id} lacks E-Mount 12-pin telemetry "
            "and requires an external hardware FIZ encoder"
        )

    wf12_risk = 0
    if norm_drv in FORBIDDEN_RF_VP_TRANSPORTS and p12_airplane_rf_off:
        wf12_risk = 1
        errors.append(
            f"BLOCKED_P12_RF_OFF_VIOLATION_00342260: FreeD LiveLink stream cannot bind to {norm_drv} "
            "under P12 Airplane RF-Off; bind strictly to wired USB-LAN (CDC-NCM / RNDIS)"
        )
    elif norm_drv not in WIRED_VP_TRANSPORTS:
        errors.append(f"Unsupported non-wired FreeD transport {norm_drv}")

    status = "FREED_D1_LIVELINK_WIRED_READY" if not errors else errors[0].split(":", 1)[0]
    return FreedLiveLinkEvalResult(
        valid=len(errors) == 0,
        status=status,
        lens_id=lens_id,
        focal_length_mm=focal_length_mm,
        focus_distance_m=focus_distance_m,
        f_stop=f_stop,
        external_fiz_encoder=external_fiz_encoder,
        transport_driver=norm_drv,
        p12_airplane_rf_off=p12_airplane_rf_off,
        wf12_00342260_risk=wf12_risk,
        udp_port=udp_port,
        decoded_packet=decoded,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar C Functions: Art-Net 4 (OpDmx) & sACN (E1.31) Shutter-Sync Guard
# ---------------------------------------------------------------------------


def build_artnet_opdmx_packet(
    *,
    net: int = 0,
    sub_uni: int = 0,
    sequence: int = 1,
    physical: int = 0,
    dmx_channels: Sequence[int] = (255, 200, 128, 64),
) -> bytes:
    """Build an Art-Net 4 OpDmx (`0x5000`, UDP `6454`) packet."""
    if not (0 <= net <= 127):
        raise ValueError("Art-Net Net must be 0..127")
    if not (0 <= sub_uni <= 255):
        raise ValueError("Art-Net SubUni must be 0..255")
    if not (0 <= sequence <= 255):
        raise ValueError("Art-Net Sequence must be 0..255")

    slots = list(dmx_channels)
    if len(slots) < 2:
        slots.extend([0] * (2 - len(slots)))
    if len(slots) % 2 == 1:
        slots.append(0)
    if len(slots) > ARTNET_MAX_UNIVERSE_CHANNELS:
        raise ValueError(f"DMX universe max {ARTNET_MAX_UNIVERSE_CHANNELS} channels")

    payload = bytes(max(0, min(255, int(v))) for v in slots)
    hdr = struct.pack(
        "<8sH",
        ARTNET_HEADER,
        ARTNET_OPCODE_OPDMX,
    ) + struct.pack(
        ">HBBBBH",
        ARTNET_PROT_VER,
        sequence,
        physical & 0xFF,
        sub_uni & 0xFF,
        net & 0x7F,
        len(payload),
    )
    return hdr + payload


def parse_artnet_opdmx_packet(raw_packet: bytes) -> ArtnetOpDmxDecoded:
    """Parse and validate an Art-Net 4 OpDmx (`0x5000`) packet."""
    errors: List[str] = []
    if len(raw_packet) < 20:
        return ArtnetOpDmxDecoded(
            valid=False,
            opcode=0,
            protocol_version=0,
            sequence=0,
            physical=0,
            net=0,
            sub_uni=0,
            port_address_15bit=0,
            dmx_length=0,
            dmx_first_4_channels=(),
            packet_hex=raw_packet.hex(),
            errors=("Art-Net OpDmx packet shorter than 20 bytes",),
        )

    magic, opcode = struct.unpack_from("<8sH", raw_packet, 0)
    prot_ver, seq, phys, sub_uni, net, dmx_len = struct.unpack_from(">HBBBBH", raw_packet, 10)
    if magic != ARTNET_HEADER:
        errors.append("Invalid Art-Net header magic")
    if opcode != ARTNET_OPCODE_OPDMX:
        errors.append(f"Unexpected Art-Net OpCode 0x{opcode:04X} != 0x5000")
    if prot_ver < ARTNET_PROT_VER:
        errors.append(f"Art-Net ProtVer {prot_ver} < 14")
    if not (2 <= dmx_len <= ARTNET_MAX_UNIVERSE_CHANNELS):
        errors.append(f"Invalid Art-Net DMX length {dmx_len}")
    if 18 + dmx_len > len(raw_packet):
        errors.append("Truncated Art-Net DMX payload")

    dmx_slice = raw_packet[18 : 18 + min(dmx_len, len(raw_packet) - 18)]
    first4 = tuple(dmx_slice[:4])
    port_addr = ((net & 0x7F) << 8) | (sub_uni & 0xFF)
    return ArtnetOpDmxDecoded(
        valid=len(errors) == 0,
        opcode=opcode,
        protocol_version=prot_ver,
        sequence=seq,
        physical=phys,
        net=net,
        sub_uni=sub_uni,
        port_address_15bit=port_addr,
        dmx_length=dmx_len,
        dmx_first_4_channels=first4,
        packet_hex=raw_packet.hex(),
        errors=tuple(errors),
    )


def sacn_universe_multicast_ip(universe: int) -> str:
    if not (SACN_UNIVERSE_MIN <= universe <= SACN_UNIVERSE_MAX):
        raise ValueError(f"sACN universe must be {SACN_UNIVERSE_MIN}..{SACN_UNIVERSE_MAX}")
    return f"239.255.{(universe >> 8) & 0xFF}.{universe & 0xFF}"


def build_sacn_e131_packet(
    *,
    universe: int = 1,
    priority: int = SACN_PRIORITY_DEFAULT,
    sequence: int = 1,
    sync_universe: int = 100,
    source_name: str = "FX3-VP-BRIDGE",
    dmx_channels: Sequence[int] = (255, 192, 64, 0),
) -> bytes:
    """Build a compact ANSI E1.31 sACN Data packet (Root + Framing + DMP layers)."""
    if not (SACN_UNIVERSE_MIN <= universe <= SACN_UNIVERSE_MAX):
        raise ValueError(f"sACN universe must be {SACN_UNIVERSE_MIN}..{SACN_UNIVERSE_MAX}")
    if not (0 <= priority <= SACN_PRIORITY_MAX):
        raise ValueError(f"sACN priority must be 0..{SACN_PRIORITY_MAX}")
    if not (1 <= len(dmx_channels) <= ARTNET_MAX_UNIVERSE_CHANNELS):
        raise ValueError("DMX channel count must be 1..512")

    slots = bytes([0]) + bytes(max(0, min(255, int(v))) for v in dmx_channels)  # Start code 0x00 + DMX
    # DMP layer
    dmp_len = 10 + len(slots)
    dmp = struct.pack(
        ">HBBHH",
        0x7000 | dmp_len,
        SACN_VECTOR_DMP_SET_PROPERTY,
        0xA1,
        0x0000,
        0x0001,
    ) + struct.pack(">H", len(slots)) + slots

    # Framing layer (77 bytes header + DMP)
    src_bytes = source_name.encode("utf-8", "replace")[:64].ljust(64, b"\x00")
    framing_len = 77 + len(dmp)
    framing = (
        struct.pack(">HI", 0x7000 | framing_len, SACN_VECTOR_E131_DATA_PACKET)
        + src_bytes
        + struct.pack(">BHBBH", priority, sync_universe, sequence & 0xFF, 0x00, universe)
    )

    # Root layer (38 bytes header + Framing)
    cid = hashlib.sha256(b"fx3-vp-sacn-cid").digest()[:16]
    root_len = 22 + len(framing)
    root = (
        struct.pack(">HH12sHI", 0x0010, 0x0000, SACN_ACN_PACKET_ID, 0x7000 | root_len, SACN_VECTOR_ROOT_E131_DATA)
        + cid
    )
    return root + framing + dmp


def parse_sacn_e131_packet(raw_packet: bytes) -> SacnE131Decoded:
    """Parse and validate an ANSI E1.31 sACN Data packet."""
    errors: List[str] = []
    if len(raw_packet) < 126:
        return SacnE131Decoded(
            valid=False,
            universe=0,
            priority=0,
            sequence=0,
            sync_universe=0,
            multicast_ip="",
            source_name="",
            dmx_length=0,
            dmx_first_4_channels=(),
            packet_hex=raw_packet.hex(),
            errors=("sACN packet shorter than minimum 126 bytes",),
        )

    preamble, postamble, acn_id, _root_fl, root_vec = struct.unpack_from(">HH12sHI", raw_packet, 0)
    if preamble != 0x0010 or postamble != 0x0000:
        errors.append("Invalid sACN Root ACN preamble")
    if acn_id != SACN_ACN_PACKET_ID:
        errors.append("Invalid sACN ACN Packet Identifier")
    if root_vec != SACN_VECTOR_ROOT_E131_DATA:
        errors.append(f"Invalid sACN Root Vector 0x{root_vec:08X}")

    _fr_fl, fr_vec = struct.unpack_from(">HI", raw_packet, 38)
    if fr_vec != SACN_VECTOR_E131_DATA_PACKET:
        errors.append(f"Invalid sACN Framing Vector 0x{fr_vec:08X}")
    src_name = raw_packet[44:108].split(b"\x00", 1)[0].decode("utf-8", "replace")
    priority, sync_univ, seq, _opts, universe = struct.unpack_from(">BHBBH", raw_packet, 108)
    if not (SACN_UNIVERSE_MIN <= universe <= SACN_UNIVERSE_MAX):
        errors.append(f"Invalid sACN universe {universe}")
    if priority > SACN_PRIORITY_MAX:
        errors.append(f"Invalid sACN priority {priority} > 200")

    _dmp_fl, dmp_vec, _addr_type, _first_addr, _addr_inc, prop_cnt = struct.unpack_from(">HBBHHH", raw_packet, 115)
    if dmp_vec != SACN_VECTOR_DMP_SET_PROPERTY:
        errors.append(f"Invalid sACN DMP Vector 0x{dmp_vec:02X}")

    dmx_slots = raw_packet[126 : 125 + prop_cnt]  # skip start code byte at 125
    dmx_len = max(0, prop_cnt - 1)
    mcast_ip = sacn_universe_multicast_ip(universe) if (SACN_UNIVERSE_MIN <= universe <= SACN_UNIVERSE_MAX) else ""
    return SacnE131Decoded(
        valid=len(errors) == 0,
        universe=universe,
        priority=priority,
        sequence=seq,
        sync_universe=sync_univ,
        multicast_ip=mcast_ip,
        source_name=src_name,
        dmx_length=dmx_len,
        dmx_first_4_channels=tuple(dmx_slots[:4]),
        packet_hex=raw_packet.hex(),
        errors=tuple(errors),
    )


def evaluate_artnet_sacn_shutter_sync(
    *,
    protocol: str = "ARTNET_4",
    transport_driver: str = "CDC_NCM_RTL8153",
    p12_airplane_rf_off: bool = True,
    readout_mode: str = "4K_24P_60P_FF",
    camera_fps: float = 23.976,
    cue_phase_offset_ms: float = 35.0,
    cue_hold_duration_ms: float = 55.0,
    frame_sync_latched: bool = True,
    sync_jitter_ms: float = 0.18,
    multi_universe_count: int = 4,
    universe: int = 1,
    dmx_channels: Sequence[int] = (255, 220, 128, 0),
) -> ArtnetSacnSyncEvalResult:
    """Evaluate Art-Net 4 / sACN DMX lighting cue synchronization vs IMX510 rolling-shutter window."""
    proto = protocol.strip().upper()
    norm_drv = transport_driver.strip().upper()
    rmode = readout_mode.strip().upper()
    if proto not in VALID_LIGHTING_PROTOCOLS:
        raise ValueError(f"Unsupported lighting protocol={protocol!r}")
    if norm_drv not in VALID_VP_TRANSPORTS:
        raise ValueError(f"Unsupported transport_driver={transport_driver!r}")
    if rmode not in IMX510_VP_READOUT_MS_SPECS:
        raise ValueError(f"Unsupported readout_mode={readout_mode!r}")

    readout_ms = IMX510_VP_READOUT_MS_SPECS[rmode]
    frame_period_ms = 1000.0 / camera_fps
    errors: List[str] = []

    artnet_dec: Optional[ArtnetOpDmxDecoded] = None
    sacn_dec: Optional[SacnE131Decoded] = None
    if proto == "ARTNET_4":
        pkt = build_artnet_opdmx_packet(
            net=(universe >> 8) & 0x7F,
            sub_uni=universe & 0xFF,
            sequence=12,
            dmx_channels=dmx_channels,
        )
        artnet_dec = parse_artnet_opdmx_packet(pkt)
        errors.extend(artnet_dec.errors)
    else:
        pkt = build_sacn_e131_packet(
            universe=max(1, universe),
            priority=120,
            sequence=12,
            sync_universe=100 if frame_sync_latched else 0,
            dmx_channels=dmx_channels,
        )
        sacn_dec = parse_sacn_e131_packet(pkt)
        errors.extend(sacn_dec.errors)

    wf12_risk = 0
    if norm_drv in FORBIDDEN_RF_VP_TRANSPORTS and p12_airplane_rf_off:
        wf12_risk = 1
        errors.append(
            f"BLOCKED_P12_RF_OFF_VIOLATION_00342260: {proto} DMX listener cannot run on {norm_drv} "
            "under P12 Airplane RF-Off; bind strictly to wired USB-LAN (CDC-NCM / RNDIS)"
        )
    elif norm_drv not in WIRED_VP_TRANSPORTS:
        errors.append(f"Unsupported non-wired DMX transport {norm_drv}")

    if multi_universe_count > 1 and not frame_sync_latched:
        errors.append(
            f"BLOCKED_UNSYNCED_MULTI_UNIVERSE_DMX: {multi_universe_count} universes require "
            "ArtSync (0x5200) or sACN E1.31 Synchronization Universe latching"
        )

    if sync_jitter_ms > LIGHTING_SYNC_MAX_JITTER_MS:
        errors.append(
            f"BLOCKED_LIGHTING_SYNC_JITTER_EXCEEDED: sync_jitter_ms={sync_jitter_ms:.3f} > "
            f"{LIGHTING_SYNC_MAX_JITTER_MS:.2f} ms"
        )

    # Rolling-shutter partial-frame flash tear check:
    # A cue edge landing inside active sensor readout [0.0, readout_ms) OR a short flash
    # shorter than frame_period_ms + readout_ms tears across IMX510 scanlines.
    phase_mod = cue_phase_offset_ms % frame_period_ms
    edge_inside_readout = 0.0 < phase_mod < readout_ms
    too_short_for_global_capture = cue_hold_duration_ms < (frame_period_ms + readout_ms)
    tear_risk = bool(edge_inside_readout or too_short_for_global_capture)
    if tear_risk:
        errors.append(
            f"BLOCKED_ROLLING_SHUTTER_FLASH_TEAR: phase={phase_mod:.2f}ms inside readout "
            f"[0,{readout_ms:.2f})ms or hold={cue_hold_duration_ms:.2f}ms < "
            f"{frame_period_ms + readout_ms:.2f}ms"
        )

    status = "ARTNET_SACN_P12_FRAME_BOUNDARY_SYNCED" if not errors else errors[0].split(":", 1)[0]
    return ArtnetSacnSyncEvalResult(
        valid=len(errors) == 0,
        status=status,
        protocol=proto,
        transport_driver=norm_drv,
        p12_airplane_rf_off=p12_airplane_rf_off,
        wf12_00342260_risk=wf12_risk,
        readout_mode=rmode,
        imx510_readout_ms=readout_ms,
        camera_fps=camera_fps,
        frame_period_ms=round(frame_period_ms, 4),
        cue_phase_offset_ms=cue_phase_offset_ms,
        cue_hold_duration_ms=cue_hold_duration_ms,
        frame_sync_latched=frame_sync_latched,
        sync_jitter_ms=sync_jitter_ms,
        rolling_shutter_tear_risk=tear_risk,
        artnet_decoded=artnet_dec,
        sacn_decoded=sacn_dec,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar D Functions: Volatile RAM Staging & Zero Persistent eMMC Mutation Guard
# ---------------------------------------------------------------------------


def evaluate_phase128_write_guard(target_path: str) -> Phase128WriteGuardResult:
    """Enforce volatile RAM staging only and zero persistent eMMC/OTA/calibration mutation."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES_P128) and not bool(
        FORBIDDEN_PERSISTENT_EMMC_RE_P128.search(norm)
    )
    if is_volatile:
        return Phase128WriteGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            emmc_mutation_bytes=0,
            calibration_mutation_bytes=0,
            errors=(),
        )
    return Phase128WriteGuardResult(
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
# Pillar Evaluators & Top-Level Phase 128 Unified Auditor
# ---------------------------------------------------------------------------


def evaluate_pillar_a_vp_ledwall_ecs_solver(
    *,
    fx3_appfw_ecs_markers: Tuple[str, ...],
    fx6_appfw_ecs_markers: Tuple[str, ...],
    fx3_libmpr_ecs_markers: Tuple[str, ...],
    fx6_libmpr_ecs_markers: Tuple[str, ...],
    uxc_ecs_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> VpLedwallEcsSolverReport:
    errors = list(extra_errors)

    e_brompton = solve_vp_ledwall_ecs_shutter(
        led_controller="BROMPTON_TESSERA_SX40",
        readout_mode="4K_24P_60P_FF",
        camera_fps=23.976,
        target_shutter_angle_deg=180.0,
        led_pwm_refresh_hz=7680.0,
        scan_multiplex_ratio=16,
        genlock_spg_locked=True,
    )
    e_helios = solve_vp_ledwall_ecs_shutter(
        led_controller="MEGAPIXEL_HELIOS",
        readout_mode="OVERSAMPLED_REF_13_2MS",
        camera_fps=24.0,
        target_shutter_angle_deg=180.0,
        led_pwm_refresh_hz=3840.0,
        scan_multiplex_ratio=8,
        genlock_spg_locked=True,
    )
    e_non_genlock = solve_vp_ledwall_ecs_shutter(
        led_controller="GENERIC_NON_GENLOCK_LED",
        readout_mode="4K_24P_60P_FF",
        camera_fps=29.97,
        target_shutter_angle_deg=180.0,
        led_pwm_refresh_hz=1920.0,
        scan_multiplex_ratio=8,
        genlock_spg_locked=False,
        candidate_ecs_hz=60.0,  # exact k=4 sub-harmonic of 240Hz mux (0.00Hz beat)
    )
    b_sub_mux = solve_vp_ledwall_ecs_shutter(
        led_controller="GENERIC_NON_GENLOCK_LED",
        readout_mode="4K_120P_SQ",
        camera_fps=59.94,
        target_shutter_angle_deg=45.0,
        led_pwm_refresh_hz=1920.0,
        scan_multiplex_ratio=16,  # effective mux = 120Hz; 480Hz exposure is < 1 mux cycle
        genlock_spg_locked=False,
        candidate_ecs_hz=480.0,
    )
    b_beat = solve_vp_ledwall_ecs_shutter(
        led_controller="BROMPTON_TESSERA_SX40",
        readout_mode="4K_24P_60P_FF",
        camera_fps=23.976,
        target_shutter_angle_deg=180.0,
        led_pwm_refresh_hz=3840.0,
        scan_multiplex_ratio=16,  # effective mux = 240Hz -> nearest sub-harmonic to 50Hz is 48Hz (k=5)
        genlock_spg_locked=True,
        candidate_ecs_hz=53.5,
    )
    b_range = solve_vp_ledwall_ecs_shutter(
        led_controller="BROMPTON_TESSERA_SX40",
        readout_mode="4K_24P_60P_FF",
        camera_fps=24.0,
        target_shutter_angle_deg=180.0,
        led_pwm_refresh_hz=7680.0,
        scan_multiplex_ratio=1,
        genlock_spg_locked=True,
        candidate_ecs_hz=9000.0,
    )

    for lbl, ev in (("brompton", e_brompton), ("helios", e_helios), ("non_genlock", e_non_genlock)):
        if not ev.valid:
            errors.append(f"Positive VP ECS solver {lbl} failed: {ev.errors}")
    for lbl, blk in (("sub_mux", b_sub_mux), ("beat", b_beat), ("range", b_range)):
        if blk.valid:
            errors.append(f"Negative VP ECS guard {lbl} unexpectedly passed")

    return VpLedwallEcsSolverReport(
        passed=len(errors) == 0,
        fx3_appfw_ecs_markers=fx3_appfw_ecs_markers,
        fx6_appfw_ecs_markers=fx6_appfw_ecs_markers,
        fx3_libmpr_ecs_markers=fx3_libmpr_ecs_markers,
        fx6_libmpr_ecs_markers=fx6_libmpr_ecs_markers,
        uxc_ecs_labels=uxc_ecs_labels,
        eval_brompton_verona_7680hz_8_7ms=e_brompton,
        eval_helios_subframe_3840hz_13_2ms=e_helios,
        eval_non_genlock_fractional_ecs=e_non_genlock,
        blocked_sub_mux_scanline_banding=b_sub_mux,
        blocked_harmonic_beat_banding=b_beat,
        blocked_ecs_out_of_range=b_range,
        errors=tuple(errors),
    )


def evaluate_pillar_b_freed_livelink_bridge(
    *,
    fx3_appfw_lens_markers: Tuple[str, ...],
    fx6_appfw_lens_markers: Tuple[str, ...],
    fx3_lens_comm_markers: Tuple[str, ...],
    fx6_libnet_ether_markers: Tuple[str, ...],
    uxc_lens_lan_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> FreedLiveLinkBridgeReport:
    errors = list(extra_errors)

    e_gm2 = evaluate_freed_livelink_bridge(
        lens_id="SEL2470GM2",
        focal_length_mm=35.0,
        focus_distance_m=2.5,
        f_stop=2.8,
        transport_driver="CDC_NCM_RTL8153",
    )
    e_pz = evaluate_freed_livelink_bridge(
        lens_id="SELP28135G",
        focal_length_mm=85.0,
        focus_distance_m=5.0,
        f_stop=4.0,
        transport_driver="USB_RNDIS_WIRED",
    )
    e_pl_ext = evaluate_freed_livelink_bridge(
        lens_id="MANUAL_PL_UNCHIPPED",
        focal_length_mm=35.0,
        focus_distance_m=3.0,
        f_stop=2.8,
        external_fiz_encoder=True,
        transport_driver="CDC_NCM_AX88179",
    )
    b_wifi = evaluate_freed_livelink_bridge(
        lens_id="SEL2470GM2",
        transport_driver="WIFI_WLAN0",
        p12_airplane_rf_off=True,
    )
    b_unchipped = evaluate_freed_livelink_bridge(
        lens_id="MANUAL_PL_UNCHIPPED",
        external_fiz_encoder=False,
        transport_driver="CDC_NCM_RTL8153",
    )
    b_csum = evaluate_freed_livelink_bridge(
        lens_id="SEL2470GM2",
        transport_driver="CDC_NCM_RTL8153",
        corrupt_checksum=True,
    )

    for lbl, ev in (("gm2", e_gm2), ("pz", e_pz), ("pl_ext", e_pl_ext)):
        if not ev.valid or ev.wf12_00342260_risk != 0 or ev.decoded_packet.packet_bytes_len != 29:
            errors.append(f"Positive FreeD LiveLink check {lbl} failed: {ev.errors}")
    for lbl, blk in (("wifi_p12", b_wifi), ("unchipped", b_unchipped), ("checksum", b_csum)):
        if blk.valid:
            errors.append(f"Negative FreeD LiveLink guard {lbl} unexpectedly passed")
    if b_wifi.wf12_00342260_risk == 0:
        errors.append("FreeD over Wi-Fi P12 violation failed to flag wf12_00342260_risk")

    return FreedLiveLinkBridgeReport(
        passed=len(errors) == 0,
        fx3_appfw_lens_markers=fx3_appfw_lens_markers,
        fx6_appfw_lens_markers=fx6_appfw_lens_markers,
        fx3_lens_comm_markers=fx3_lens_comm_markers,
        fx6_libnet_ether_markers=fx6_libnet_ether_markers,
        uxc_lens_lan_labels=uxc_lens_lan_labels,
        eval_sel2470gm2_cdc_ncm_livelink=e_gm2,
        eval_selp28135g_rndis_livelink=e_pz,
        eval_manual_pl_with_external_fiz=e_pl_ext,
        blocked_wifi_wlan0_p12_violation=b_wifi,
        blocked_unchipped_lens_no_encoder=b_unchipped,
        blocked_corrupt_freed_d1_checksum=b_csum,
        errors=tuple(errors),
    )


def evaluate_pillar_c_artnet_sacn_shutter_sync(
    *,
    fx3_appfw_sync_markers: Tuple[str, ...],
    fx6_libnet_ether_markers: Tuple[str, ...],
    uxc_airplane_lan_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> ArtnetSacnShutterSyncReport:
    errors = list(extra_errors)

    e_artnet = evaluate_artnet_sacn_shutter_sync(
        protocol="ARTNET_4",
        transport_driver="CDC_NCM_RTL8153",
        readout_mode="4K_24P_60P_FF",
        camera_fps=23.976,
        cue_phase_offset_ms=20.0,
        cue_hold_duration_ms=55.0,
        frame_sync_latched=True,
        sync_jitter_ms=0.15,
    )
    e_sacn = evaluate_artnet_sacn_shutter_sync(
        protocol="SACN_E131",
        transport_driver="CDC_NCM_AX88179",
        readout_mode="OVERSAMPLED_REF_13_2MS",
        camera_fps=24.0,
        cue_phase_offset_ms=22.0,
        cue_hold_duration_ms=60.0,
        frame_sync_latched=True,
        sync_jitter_ms=0.20,
        universe=12,
    )
    b_tear = evaluate_artnet_sacn_shutter_sync(
        protocol="ARTNET_4",
        transport_driver="CDC_NCM_RTL8153",
        readout_mode="4K_24P_60P_FF",
        camera_fps=23.976,
        cue_phase_offset_ms=4.2,  # lands right inside 8.7ms IMX510 readout!
        cue_hold_duration_ms=12.0,
        frame_sync_latched=True,
    )
    b_unsynced = evaluate_artnet_sacn_shutter_sync(
        protocol="SACN_E131",
        transport_driver="CDC_NCM_RTL8153",
        cue_phase_offset_ms=20.0,
        cue_hold_duration_ms=55.0,
        frame_sync_latched=False,
        multi_universe_count=8,
    )
    b_wifi = evaluate_artnet_sacn_shutter_sync(
        protocol="ARTNET_4",
        transport_driver="WIFI_WLAN0",
        p12_airplane_rf_off=True,
        cue_phase_offset_ms=20.0,
        cue_hold_duration_ms=55.0,
        frame_sync_latched=True,
    )

    for lbl, ev in (("artnet4", e_artnet), ("sacn_e131", e_sacn)):
        if not ev.valid or ev.wf12_00342260_risk != 0 or ev.rolling_shutter_tear_risk:
            errors.append(f"Positive Art-Net/sACN check {lbl} failed: {ev.errors}")
    for lbl, blk in (("flash_tear", b_tear), ("unsynced_dmx", b_unsynced), ("wifi_p12", b_wifi)):
        if blk.valid:
            errors.append(f"Negative Art-Net/sACN guard {lbl} unexpectedly passed")
    if b_wifi.wf12_00342260_risk == 0:
        errors.append("Art-Net over Wi-Fi P12 violation failed to flag wf12_00342260_risk")

    return ArtnetSacnShutterSyncReport(
        passed=len(errors) == 0,
        fx3_appfw_sync_markers=fx3_appfw_sync_markers,
        fx6_libnet_ether_markers=fx6_libnet_ether_markers,
        uxc_airplane_lan_labels=uxc_airplane_lan_labels,
        eval_artnet4_opdmx_artsync_cdc_ncm=e_artnet,
        eval_sacn_e131_sync_univ_cdc_ncm=e_sacn,
        blocked_rolling_shutter_flash_tear=b_tear,
        blocked_unsynced_multi_universe_dmx=b_unsynced,
        blocked_wifi_wlan0_p12_lighting=b_wifi,
        errors=tuple(errors),
    )


def evaluate_pillar_d_zero_mutation_vp_guard(
    *,
    fx3_global_xdb_valid: bool,
    fx6_global_xdb_valid: bool,
    extra_errors: Sequence[str] = (),
) -> ZeroMutationVpGuardReport:
    errors = list(extra_errors)
    if not fx3_global_xdb_valid:
        errors.append("FX3 global.xdb (uxa\\x07) failed structural validation")
    if not fx6_global_xdb_valid:
        errors.append("FX6 global.xdb (uxa\\x07) failed structural validation")

    g_vol = evaluate_phase128_write_guard("/tmp/fx3_stageb_vp_ledwall_freed_artnet.json")
    g_body = evaluate_phase128_write_guard("/mnt/sd/BODYDATA.DAT")
    g_nf15 = evaluate_phase128_write_guard("/dev/nflasha15")
    g_cn0 = evaluate_phase128_write_guard("/dev/cnflasha0")
    g_bak = evaluate_phase128_write_guard("p2:/setting/Backup.bin")

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

    return ZeroMutationVpGuardReport(
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


def build_clean_room_vp_ledwall_freed_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, `global.xdb`, and `.uxc` fixtures."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)

    def _pack(tokens: Sequence[str]) -> bytes:
        return elf_hdr + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    return {
        "fx3_appfw": _pack(FX3_APPFW_PHASE128_MARKERS),
        "fx6_appfw": _pack(FX6_APPFW_PHASE128_MARKERS),
        "fx3_libmpr": _pack(FX3_LIBMPR_PHASE128_MARKERS),
        "fx6_libmpr": _pack(FX6_LIBMPR_PHASE128_MARKERS),
        "fx3_lens_comm": _pack(FX3_LENS_COMM_PHASE128_MARKERS),
        "fx6_libnet_ether": _pack(FX6_LIBNET_ETHER_PHASE128_MARKERS),
        "fx3_global_xdb": build_synthetic_global_xdb("fx3_702"),
        "fx6_global_xdb": build_synthetic_global_xdb("fx6_601"),
        "fx3_str_en": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS39_PHASE128_LABELS.items()}, namespace_id=39
        ),
        "fx3_str_en_g": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS3_PHASE128_LABELS.items()}, namespace_id=3
        ),
        "fx6_str_en_1": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS1_PHASE128_LABELS.items()}, namespace_id=1
        ),
        "fx6_str_en_2": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS2_PHASE128_LABELS.items()}, namespace_id=2
        ),
    }


def analyze_vp_ledwall_ecs_freed_and_artnet(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> VpLedwallEcsFreedAndArtnetReport:
    """Run the 25th unified firmware-lab auditor in Local Donor (`os.O_RDONLY`) or Clean-Room mode."""
    root = repo_root or DEFAULT_REPO_ROOT
    forced_clean = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not forced_clean:
        donor_paths = {
            "fx3_appfw": resolve_donor_file(FX3_APPFW_RELPATH, repo_root=root),
            "fx6_appfw": resolve_donor_file(FX6_APPFW_RELPATH, repo_root=root),
            "fx3_libmpr": resolve_donor_file(FX3_LIBMPR_RELPATH, repo_root=root),
            "fx6_libmpr": resolve_donor_file(FX6_LIBMPR_RELPATH, repo_root=root),
            "fx3_lens_comm": resolve_donor_file(FX3_LENS_COMM_RELPATH, repo_root=root),
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
        "ecs": FX3_APPFW_PHASE128_MARKERS[:3],
        "lens": FX3_APPFW_PHASE128_MARKERS[3:6],
        "sync": FX3_APPFW_PHASE128_MARKERS[6:],
    }
    fx6_app_groups = {
        "ecs": FX6_APPFW_PHASE128_MARKERS[:4],
        "lens": FX6_APPFW_PHASE128_MARKERS[4:],
    }
    fx3_mpr_groups = {"ecs": FX3_LIBMPR_PHASE128_MARKERS}
    fx6_mpr_groups = {"ecs": FX6_LIBMPR_PHASE128_MARKERS}
    fx3_lc_groups = {"lens": FX3_LENS_COMM_PHASE128_MARKERS}
    fx6_eth_groups = {"eth": FX6_LIBNET_ETHER_PHASE128_MARKERS}

    if use_local:
        sz_fx3_app, fx3_app_res = _scan_donor_rdonly_markers(donor_paths["fx3_appfw"], fx3_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_app, fx6_app_res = _scan_donor_rdonly_markers(donor_paths["fx6_appfw"], fx6_app_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx3_mpr, fx3_mpr_res = _scan_donor_rdonly_markers(donor_paths["fx3_libmpr"], fx3_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_mpr, fx6_mpr_res = _scan_donor_rdonly_markers(donor_paths["fx6_libmpr"], fx6_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx3_lc, fx3_lc_res = _scan_donor_rdonly_markers(donor_paths["fx3_lens_comm"], fx3_lc_groups, is_elf=True)  # type: ignore[arg-type]
        sz_fx6_eth, fx6_eth_res = _scan_donor_rdonly_markers(donor_paths["fx6_libnet_ether"], fx6_eth_groups, is_elf=True)  # type: ignore[arg-type]
        fx3_xdb_bytes = _read_bytes_rdonly(donor_paths["fx3_global_xdb"])  # type: ignore[arg-type]
        fx6_xdb_bytes = _read_bytes_rdonly(donor_paths["fx6_global_xdb"])  # type: ignore[arg-type]
        fx3_str_en_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en"])  # type: ignore[arg-type]
        fx3_str_en_g_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en_g"])  # type: ignore[arg-type]
        fx6_str_en_1_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_1"])  # type: ignore[arg-type]
        fx6_str_en_2_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_2"])  # type: ignore[arg-type]
    else:
        fx = build_clean_room_vp_ledwall_freed_fixtures()
        sz_fx3_app, fx3_app_res = _scan_bytes_marker_groups(fx["fx3_appfw"], fx3_app_groups)
        sz_fx6_app, fx6_app_res = _scan_bytes_marker_groups(fx["fx6_appfw"], fx6_app_groups)
        sz_fx3_mpr, fx3_mpr_res = _scan_bytes_marker_groups(fx["fx3_libmpr"], fx3_mpr_groups)
        sz_fx6_mpr, fx6_mpr_res = _scan_bytes_marker_groups(fx["fx6_libmpr"], fx6_mpr_groups)
        sz_fx3_lc, fx3_lc_res = _scan_bytes_marker_groups(fx["fx3_lens_comm"], fx3_lc_groups)
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
        "fx3_lens_comm": sz_fx3_lc,
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
        ("FX3 appFw ECS", fx3_app_res["ecs"], fx3_app_groups["ecs"], pa_extra),
        ("FX6 appFw ECS", fx6_app_res["ecs"], fx6_app_groups["ecs"], pa_extra),
        ("FX3 libmpr ECS", fx3_mpr_res["ecs"], fx3_mpr_groups["ecs"], pa_extra),
        ("FX6 libmpr ECS", fx6_mpr_res["ecs"], fx6_mpr_groups["ecs"], pa_extra),
        ("FX3 appFw Lens", fx3_app_res["lens"], fx3_app_groups["lens"], pb_extra),
        ("FX6 appFw Lens", fx6_app_res["lens"], fx6_app_groups["lens"], pb_extra),
        ("FX3 LensCommunicator", fx3_lc_res["lens"], fx3_lc_groups["lens"], pb_extra),
        ("FX6 libNetServiceEther", fx6_eth_res["eth"], fx6_eth_groups["eth"], pb_extra),
        ("FX3 appFw Sync", fx3_app_res["sync"], fx3_app_groups["sync"], pc_extra),
    ):
        if len(actual) != len(expected):
            bucket.append(f"Missing {label} markers ({len(actual)}/{len(expected)})")

    fx3_ux_en, u_err_1 = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE128_LABELS)
    fx3_ux_g, u_err_2 = _extract_uxc_labels(fx3_str_en_g_bytes, FX3_NS3_PHASE128_LABELS)
    fx6_ux_1, u_err_3 = _extract_uxc_labels(fx6_str_en_1_bytes, FX6_NS1_PHASE128_LABELS)
    fx6_ux_2, u_err_4 = _extract_uxc_labels(fx6_str_en_2_bytes, FX6_NS2_PHASE128_LABELS)
    pa_extra.extend(u_err_2)
    pa_extra.extend(u_err_3)
    pb_extra.extend(u_err_1)
    pc_extra.extend(u_err_4)

    uxc_ecs_labels = {
        "fx3_anti_flicker_tv_scan": fx3_ux_g.get("0x000060a8", ""),
        "fx6_ecs": fx6_ux_1.get("0x00002077", ""),
        "fx6_ecs_on_off": fx6_ux_1.get("0x000022db", ""),
        "fx6_shutter_angle": fx6_ux_2.get("0x00004d96", ""),
        "fx6_ecs_frequency": fx6_ux_2.get("0x00004d98", ""),
    }
    uxc_lens_lan_labels = {
        "fx3_lens_focal_length": fx3_ux_en.get("0x0004e116", ""),
        "fx3_wire_lan": fx3_ux_en.get("0x0004e39a", ""),
        "fx3_usb_lan_tethering": fx3_ux_g.get("0x0000645f", ""),
        "fx6_focal_length": fx6_ux_1.get("0x0000224e", ""),
        "fx6_iris": fx6_ux_1.get("0x000020d1", ""),
        "fx6_focus_position": fx6_ux_2.get("0x00004538", ""),
        "fx6_iris_position": fx6_ux_2.get("0x0000453c", ""),
    }
    uxc_airplane_lan_labels = {
        "fx3_wire_lan": fx3_ux_en.get("0x0004e39a", ""),
        "fx6_airplane_mode": fx6_ux_2.get("0x000042d3", ""),
    }

    pa = evaluate_pillar_a_vp_ledwall_ecs_solver(
        fx3_appfw_ecs_markers=fx3_app_res["ecs"],
        fx6_appfw_ecs_markers=fx6_app_res["ecs"],
        fx3_libmpr_ecs_markers=fx3_mpr_res["ecs"],
        fx6_libmpr_ecs_markers=fx6_mpr_res["ecs"],
        uxc_ecs_labels=uxc_ecs_labels,
        extra_errors=pa_extra,
    )
    pb = evaluate_pillar_b_freed_livelink_bridge(
        fx3_appfw_lens_markers=fx3_app_res["lens"],
        fx6_appfw_lens_markers=fx6_app_res["lens"],
        fx3_lens_comm_markers=fx3_lc_res["lens"],
        fx6_libnet_ether_markers=fx6_eth_res["eth"],
        uxc_lens_lan_labels=uxc_lens_lan_labels,
        extra_errors=pb_extra,
    )
    pc = evaluate_pillar_c_artnet_sacn_shutter_sync(
        fx3_appfw_sync_markers=fx3_app_res["sync"],
        fx6_libnet_ether_markers=fx6_eth_res["eth"],
        uxc_airplane_lan_labels=uxc_airplane_lan_labels,
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

    pd = evaluate_pillar_d_zero_mutation_vp_guard(
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
        extra_errors=pd_extra,
    )

    all_errors = pa.errors + pb.errors + pc.errors + pd.errors
    all_passed = bool(pa.passed and pb.passed and pc.passed and pd.passed and len(all_errors) == 0)

    digest_payload = {
        "schema_version": PHASE_128_SCHEMA,
        "phase_version": PHASE_128_VERSION,
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

    return VpLedwallEcsFreedAndArtnetReport(
        schema_version=PHASE_128_SCHEMA,
        phase_version=PHASE_128_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        donor_file_sizes=sizes,
        pillar_a_vp_ledwall_ecs_solver=pa,
        pillar_b_freed_livelink_bridge=pb,
        pillar_c_artnet_sacn_shutter_sync=pc,
        pillar_d_zero_mutation_vp_guard=pd,
        report_sha256=report_sha256,
        errors=tuple(all_errors),
    )


def vp_ledwall_ecs_freed_and_artnet_report_to_dict(
    report: VpLedwallEcsFreedAndArtnetReport,
) -> Dict[str, object]:
    """Convert `VpLedwallEcsFreedAndArtnetReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
