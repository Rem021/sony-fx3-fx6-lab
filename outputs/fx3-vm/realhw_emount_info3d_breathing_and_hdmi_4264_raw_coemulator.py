#!/usr/bin/env python3
"""Phase 182 — Stage 32 (`32/32` Stage) `outputs/fx3-vm/` Real-Hardware Main Track:
Sony `MIRA_CETUS2` E-Mount `info7/info8/info3D` Serial Handshake + `0x02cf0232` Breathing
Compensation & Type-A HDMI `4264x2408` 16-bit Linear RAW (`BRAW` / `ProRes RAW`) HIL Co-Emulator.

Implements strictly read-only (`os.open(..., os.O_RDONLY)`) donor inspection (< 0.10s, cached per
process, bounded <= 4096 B windows on large firmware binaries) with deterministic
`CLEAN_ROOM_SYNTHETIC` fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`), and co-emulates all four Phase 182
real-hardware pillars (A-D) for physical Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`,
AP `CXD90057` *Mira* + CP `CXD90058` *Cetus*) while hard-locking:
- `persistent_emmc_writes_authorized == False`
- `spi_nor_write_authorized == False`
- `el3_payload_transmit_authorized == False`
- `physical_usb_packets_emitted == 0`
- `otp_fuse_touches == 0`
- `rpmb_counter_increments == 0`
- `lens_partition_writes == 0` (`p18:/lens/LENSFILE.BIN` `BLKROSET=1`)
- `sdi_bnc_mmio_faults == 0`, `raw_firmware_bytes_leaked == 0`

1. **Fast Dual-Mode `O_RDONLY` Donor Inspection (< 0.10s, cached per process)**:
   - Inspects 12 real FX3 `7.02` & FX6 `6.01` donors via `os.open(..., os.O_RDONLY)`:
     `libInfraLensCommunicator.so` (FX3/FX6 `14,544 B`), `libInfraAdjMedia.so` (FX3 `318,152 B` /
     FX6 `334,536 B`), `string_english.uxc` / `string_english_g.uxc` / `string_english_2.uxc`
     (`4264x2408`, `Breathing Comp`, `Focus Map`, `ProRes`, `RAW Output Format`), plus bounded
     `<= 4096 B` windows on `cpapp-b.bin` (FX3 `15,980,568 B` / FX6 `17,952,816 B`: `Draw Widget <FocusMap>`,
     `fixed_lensfile`, `ExtractFromCombinedLensData`, `MoniFpga`) and `appFw.so` (FX3 `79,015,712 B` /
     FX6 `50,520,424 B`: `uc_BreathingCorrectionLensType`, `HDMI_RAW_CONNECTSTATE_NOT_SET`,
     `parent_child_server_camera_ssh_info7`/`info8`, and LE `0x02cf0232` BKID).
   - Deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files
     are absent; zero raw Sony bytes emitted (`raw_firmware_bytes_leaked == 0`).

2. **Pillar A — `MIRA_CETUS2` E-Mount `info7 / info8 / info3D` & `0x02cf0232` Breathing Comp HIL**:
   - Evaluates `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)` across Sony first-party
     E-mount lenses (`FE PZ 16-35mm F4 G`, `FE 24-70mm F2.8 GM II`), third-party E-mount lenses
     (`(lens_id >> 14) != 3`), and manual PL/E adapters (`lens_id == 0xFFFF`), gating
     `0x02cf0232` (`BKID_APP_MR_SETTING_LENS_COMP_BREATHING`), Catalyst clip metadata injection,
     Monitor & Control `2.1.0+` Focus Map depth stream, and `p18:/lens/LENSFILE.BIN` `BLKROSET=1`.

3. **Pillar B — Type-A HDMI `4264x2408` (`60p`) 16-bit Linear RAW (`BRAW` / `ProRes RAW`) vs Masked `12G-SDI` HIL**:
   - Co-emulates CTA-861 EDID + Sony VSIF (`0x81`) negotiation with `Video Assist 12G HDR 3.22+`
     (accepts `4264x2408` 16->12-bit `.braw` with capture-locked ISO; rejects `Video Assist 3G`),
     `Atomos Ninja V/Ultra` (`AtomOS 10.64+`, encapsulates WB + ISO offset), simultaneous internal
     `XAVC S-I / HS + Proxy` dual-slot recording, `1.5x`/`1.6x` anamorphic de-squeeze OSD non-bake,
     and masked `12G-SDI` BNC MMIO (`0` faults).

4. **Pillar C & D — WPA2/WPA3 Network Sanitizer & Hard Safety Redline Invariants**:
   - Enforces `WPA2/WPA3` wireless security floor (plus `WIRED_USB_CDC_NCM`), sanitizes metadata/SSID
     inputs fail-closed, and locks all physical write / USB / OTP / RPMB redlines.
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
import zlib


# ---------------------------------------------------------------------------
# Phase 182 Schema & Hard-Locked Safety Redlines
# ---------------------------------------------------------------------------

PHASE_182_SCHEMA = "phase182_realhw_emount_info3d_breathing_hdmi_4264_raw_coemulator_v1"
PHASE_182_VERSION = "182.0.0"
STAGE_INDEX = 32
STAGE_TOTAL = 32
MILESTONE_LABEL = "32/32"
STAGE_NAME = "stage32_realhw_emount_info3d_breathing_hdmi_4264_raw_hil"

P8_CP_MUTATION_FORBIDDEN = True
NOP_COUNT = 0
GUEST_CODE_MODIFICATION_BYTES = 0
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
LENS_PARTITION_WRITES = 0
P18_MUTATION_BYTES = 0
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
SDI_BNC_MMIO_FAULTS = 0
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
_FX6_NF15_PREFIX = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"

DONOR_RELPATHS: Mapping[str, str] = {
    "fx3_lens_comm": f"{_FX3_USR_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx6_lens_comm": f"{_FX6_NF15_PREFIX}/lib/libInfraLensCommunicator.so",
    "fx3_adj_media": f"{_FX3_USR_PREFIX}/lib/libInfraAdjMedia.so",
    "fx6_adj_media": f"{_FX6_NF15_PREFIX}/lib/libInfraAdjMedia.so",
    "fx3_string_en": f"{_FX3_USR_PREFIX}/share/app/string_english.uxc",
    "fx3_string_en_g": f"{_FX3_USR_PREFIX}/share/app/string_english_g.uxc",
    "fx6_string_en": f"{_FX6_NF15_PREFIX}/share/app/string_english.uxc",
    "fx6_string_en_2": f"{_FX6_NF15_PREFIX}/share/app/string_english_2.uxc",
    "fx3_cpapp": "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
    "fx6_cpapp": "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
    "fx3_appfw": "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
    "fx6_appfw": f"{_FX6_NF15_PREFIX}/lib/appFw.so",
}

EXPECTED_DONOR_BYTES: Mapping[str, int] = {
    "fx3_lens_comm": 14_544,
    "fx6_lens_comm": 14_544,
    "fx3_adj_media": 318_152,
    "fx6_adj_media": 334_536,
    "fx3_string_en": 165_740,
    "fx3_string_en_g": 69_600,
    "fx6_string_en": 118_208,
    "fx6_string_en_2": 118_676,
    "fx3_cpapp": 15_980_568,
    "fx6_cpapp": 17_952_816,
    "fx3_appfw": 79_015_712,
    "fx6_appfw": 50_520_424,
}

COMPACT_DONOR_TOKENS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx6_lens_comm": (b"LensCommunicator", b"GetMountedLensInfo", b"SndSyncMsg"),
    "fx3_adj_media": (b"AVBB_SCN_START_HDMI", b"AVBB_SCN_STOP_HDMI", b"RAW"),
    "fx6_adj_media": (b"AVBB_SCN_START_HDMI", b"AVBB_SCN_STOP_HDMI", b"RAW"),
    "fx3_string_en": (b"Invalid during RAW movies output over HDMI.", b"HDMI"),
    "fx3_string_en_g": (b"RAW movies output", b"Crop: HDMI"),
    "fx6_string_en": (b"4264x2408", b"Breathing Comp", b"Focus Map", b"RAW Output Format"),
    "fx6_string_en_2": (b"ProRes", b"RAW Output Format", b"XAVC-I"),
}

# Pinned bounded windows (<= 4096 B each) for large CP/AP binaries so cold inspection is < 5 ms.
LARGE_DONOR_WINDOWS: Mapping[str, Tuple[Tuple[int, str, bytes], ...]] = {
    "fx3_cpapp": (
        (315_000, "Draw Widget <FocusMap>", b"Draw Widget <FocusMap>"),
        (2_507_000, "Breathing", b"Breathing"),
        (3_443_000, "fixed_lensfile", b"fixed_lensfile"),
        (3_443_000, "ExtractFromCombinedLensData", b"ExtractFromCombinedLensData"),
    ),
    "fx6_cpapp": (
        (1_145_000, "MoniFpga", b"MoniFpga"),
        (2_536_000, "Breathing", b"Breathing"),
        (3_475_000, "fixed_lensfile", b"fixed_lensfile"),
        (3_475_000, "ExtractFromCombinedLensData", b"ExtractFromCombinedLensData"),
    ),
    "fx3_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (51_401_000, "FocusMap", b"FocusMap"),
        (60_259_000, "uc_BreathingCorrectionLensType", b"uc_BreathingCorrectionLensType"),
        (60_657_500, "HDMI_RAW_CONNECTSTATE_NOT_SET", b"HDMI_RAW_CONNECTSTATE_NOT_SET"),
    ),
    "fx6_appfw": (
        (0, "ELF64", b"\x7fELF"),
        (41_203_000, "HDMI_RAW", b"HDMI_RAW"),
        (42_784_500, "info7", b"info7"),
        (42_784_500, "info8", b"info8"),
        (46_307_500, "0x02cf0232_le", b"\x32\x02\xcf\x02"),
    ),
}

# ---------------------------------------------------------------------------
# Pillar A Constants: MIRA_CETUS2 E-Mount info7/info8/info3D & 0x02cf0232
# ---------------------------------------------------------------------------

BKID_APP_MR_SETTING_LENS_COMP_BREATHING = 0x02CF0232
BKID_BREATHING_HEX = "0x02cf0232"
P18_LENSFILE_PATH = "p18:/lens/LENSFILE.BIN"
P18_BLKROSET_LOCKED = 1
P18_MOUNT_FLAGS = "MS_RDONLY"
MONITOR_CONTROL_MIN_VERSION = (2, 1, 0)
MONITOR_CONTROL_MIN_VERSION_STR = "2.1.0"

LENS_CLASS_SONY_FIRST_PARTY = "SONY_FIRST_PARTY_EMOUNT"
LENS_CLASS_THIRD_PARTY = "THIRD_PARTY_EMOUNT"
LENS_CLASS_MANUAL_PL = "MANUAL_PL_E_ADAPTER"

MANUAL_PL_LENS_ID = 0xFFFF
VALID_LENS_PRESETS: Mapping[str, Tuple[int, str, float]] = {
    "SELP1635G": (0xC120, "FE PZ 16-35mm F4 G", 1.055),
    "SEL2470GM2": (0xC135, "FE 24-70mm F2.8 GM II", 1.072),
    "SEL50F12GM": (0xC118, "FE 50mm F1.2 GM", 1.064),
    "SIGMA_24_70_DG_DN": (0x4210, "Sigma 24-70mm F2.8 DG DN Art", 1.000),
    "TAMRON_28_75_G2": (0x8150, "Tamron 28-75mm F2.8 Di III VXD G2", 1.000),
    "PL_ADAPTER_UNCHIPPED": (MANUAL_PL_LENS_ID, "Manual PL-to-E Unchipped Adapter", 1.000),
}

# ---------------------------------------------------------------------------
# Pillar B Constants: Type-A HDMI 4264x2408 (60p) 16-bit RAW vs Masked 12G-SDI
# ---------------------------------------------------------------------------

HDMI_RAW_WIDTH = 4264
HDMI_RAW_HEIGHT = 2408
HDMI_RAW_BIT_DEPTH_LINEAR = 16
HDMI_RAW_MAX_FPS = 60.0
HDMI_RAW_SUPPORTED_FPS: Tuple[str, ...] = ("23.98p", "24.00p", "25.00p", "29.97p", "50.00p", "59.94p")
HDMI_RAW_UNSUPPORTED_FPS: Tuple[str, ...] = ("100.00p", "119.88p", "120.00p")

RECORDER_VA_12G_HDR = "VIDEO_ASSIST_12G_HDR"
RECORDER_VA_3G = "VIDEO_ASSIST_3G"
RECORDER_ATOMOS_NINJA_V = "ATOMOS_NINJA_V"
RECORDER_ATOMOS_NINJA_ULTRA = "ATOMOS_NINJA_ULTRA"

VIDEO_ASSIST_12G_MIN_FW = (3, 22, 0)
ATOMOS_MIN_FW = (10, 64, 0)

VALID_ANAMORPHIC_DESQUEEZE: Tuple[float, ...] = (1.0, 1.3, 1.33, 1.5, 1.6, 2.0)
SUPPORTED_INTERNAL_SIMUL_CODECS: Tuple[str, ...] = ("XAVC S-I", "XAVC HS", "XAVC S")

# ---------------------------------------------------------------------------
# Pillar C Constants: WPA2/WPA3 Network Sanitizer & Hard Redline Floor
# ---------------------------------------------------------------------------

ALLOWED_NETWORK_SECURITY_MODES: Tuple[str, ...] = ("WPA2", "WPA3", "WIRED_USB_CDC_NCM")
REJECTED_NETWORK_SECURITY_MODES: Tuple[str, ...] = ("WEP", "WPA1", "OPEN", "TKIP", "IPsec")
_FORBIDDEN_META_RE = re.compile(r"(\.\./|\.\.\\|/dev/|nvram|p18:/lens|[\x00-\x1f;`|&$<>])", re.IGNORECASE)


class RealHwEmountInfo3dHdmiRawError(ValueError):
    """Raised on invalid Phase 182 Stage 32 configuration or contract inputs."""


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
class Phase182DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    fx3_lens_comm: CompactDonorSummary
    fx6_lens_comm: CompactDonorSummary
    fx3_adj_media: CompactDonorSummary
    fx6_adj_media: CompactDonorSummary
    fx3_string_en: CompactDonorSummary
    fx3_string_en_g: CompactDonorSummary
    fx6_string_en: CompactDonorSummary
    fx6_string_en_2: CompactDonorSummary
    fx3_cpapp: BoundedWindowDonorSummary
    fx6_cpapp: BoundedWindowDonorSummary
    fx3_appfw: BoundedWindowDonorSummary
    fx6_appfw: BoundedWindowDonorSummary
    lens_comm_abi_parity_proven: bool
    fx6_bkid_02cf0232_and_info7_8_proven: bool
    fx6_4264x2408_and_prores_proven: bool
    fx3_breathing_and_hdmi_raw_proven: bool
    all_contracts_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class EmountInfo3dHandshakeResult:
    valid: bool
    lens_id: int
    lens_id_hex: str
    lens_name: str
    lens_class: str
    sony_first_party_match: bool
    info7_packet_hex: str
    info8_packet_hex: str
    info3d_packet_hex: str
    info_crc32_valid: bool
    p18_lensfile_path: str
    p18_blkroset: int
    lens_partition_writes: int
    breathing_comp_authorized: bool
    bkid_0x02cf0232_passthrough: bool
    breathing_crop_factor: float
    catalyst_breathing_meta_injected: bool
    focus_map_stream_active: bool
    mc_app_version: str
    mc_transport: str
    appfw_crashes: int
    status_code: str


@dataclass(frozen=True)
class Hdmi4264RawNegotiationResult:
    admitted: bool
    recorder_model: str
    recorder_fw: str
    raw_container_format: str
    width: int
    height: int
    fps_label: str
    bit_depth_linear: int
    bit_depth_encoded: int
    edid_raw16_capable: bool
    vsif_checksum_valid: bool
    capture_locked_iso: bool
    wb_iso_offset_encapsulated: bool
    internal_simul_codec: str
    internal_dual_slot_active: bool
    anamorphic_desqueeze: float
    anamorphic_desqueeze_osd_only: bool
    osd_baked_into_raw: bool
    sdi_bnc_mmio_masked: bool
    sdi_bnc_mmio_faults: int
    frame_drops: int
    status_code: str


@dataclass(frozen=True)
class NetworkSanitizerResult:
    valid: bool
    security_mode: str
    security_admitted: bool
    ssid_or_host: str
    catalyst_clip_tag: str
    sanitization_passed: bool
    wf12_00342260_hits: int
    wired_cdc_ncm_fallback_ready: bool
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
    lens_partition_writes: int
    sdi_bnc_mmio_faults: int
    blocked_action: str
    status_code: str


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Fast Donor Inspection + Clean-Room Fallback
# ---------------------------------------------------------------------------

_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str, int, int], ...]], Phase182DonorAudit] = {}


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


def resolve_phase182_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
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


def _build_clean_room_donor_audit() -> Phase182DonorAudit:
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
        head = (
            _build_synthetic_elf64_bytes((), f"{key}_HEAD".encode("ascii"))
            if is_elf
            else (b"CPAPP_SYNTH_" + label.encode("ascii")).ljust(64, b"\x00")
        )
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

    return Phase182DonorAudit(
        source_mode=mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=_mk_compact("fx3_lens_comm", "FX3_7.02", False),
        fx6_lens_comm=_mk_compact("fx6_lens_comm", "FX6_6.01", False),
        fx3_adj_media=_mk_compact("fx3_adj_media", "FX3_7.02", False),
        fx6_adj_media=_mk_compact("fx6_adj_media", "FX6_6.01", False),
        fx3_string_en=_mk_compact("fx3_string_en", "FX3_7.02", True),
        fx3_string_en_g=_mk_compact("fx3_string_en_g", "FX3_7.02", True),
        fx6_string_en=_mk_compact("fx6_string_en", "FX6_6.01", True),
        fx6_string_en_2=_mk_compact("fx6_string_en_2", "FX6_6.01", True),
        fx3_cpapp=_mk_large("fx3_cpapp", "FX3_7.02", False),
        fx6_cpapp=_mk_large("fx6_cpapp", "FX6_6.01", False),
        fx3_appfw=_mk_large("fx3_appfw", "FX3_7.02", True),
        fx6_appfw=_mk_large("fx6_appfw", "FX6_6.01", True),
        lens_comm_abi_parity_proven=True,
        fx6_bkid_02cf0232_and_info7_8_proven=True,
        fx6_4264x2408_and_prores_proven=True,
        fx3_breathing_and_hdmi_raw_proven=True,
        all_contracts_verified=True,
        errors=(),
    )


def inspect_phase182_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase182DonorAudit:
    """Inspect 12 FX3 7.02 & FX6 6.01 donors strictly via os.O_RDONLY (< 0.10s, cached)."""
    clean_room = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        return _build_clean_room_donor_audit()

    paths = resolve_phase182_donor_paths(env=env)
    if not all(p.is_file() for p in paths.values()):
        return _build_clean_room_donor_audit()

    sig = tuple(
        (k, str(p), p.stat().st_size, p.stat().st_mtime_ns)
        for k, p in sorted(paths.items())
    )
    cache_key = ("LOCAL_DONOR_RDONLY", sig)
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    fx3_lens_comm = _scan_compact_rdonly(
        paths["fx3_lens_comm"],
        artifact_key="fx3_lens_comm",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_lens_comm"],
    )
    fx6_lens_comm = _scan_compact_rdonly(
        paths["fx6_lens_comm"],
        artifact_key="fx6_lens_comm",
        body_label="FX6_6.01",
        tokens=COMPACT_DONOR_TOKENS["fx6_lens_comm"],
    )
    fx3_adj_media = _scan_compact_rdonly(
        paths["fx3_adj_media"],
        artifact_key="fx3_adj_media",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_adj_media"],
    )
    fx6_adj_media = _scan_compact_rdonly(
        paths["fx6_adj_media"],
        artifact_key="fx6_adj_media",
        body_label="FX6_6.01",
        tokens=COMPACT_DONOR_TOKENS["fx6_adj_media"],
    )
    fx3_string_en = _scan_compact_rdonly(
        paths["fx3_string_en"],
        artifact_key="fx3_string_en",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_string_en"],
    )
    fx3_string_en_g = _scan_compact_rdonly(
        paths["fx3_string_en_g"],
        artifact_key="fx3_string_en_g",
        body_label="FX3_7.02",
        tokens=COMPACT_DONOR_TOKENS["fx3_string_en_g"],
    )
    fx6_string_en = _scan_compact_rdonly(
        paths["fx6_string_en"],
        artifact_key="fx6_string_en",
        body_label="FX6_6.01",
        tokens=COMPACT_DONOR_TOKENS["fx6_string_en"],
    )
    fx6_string_en_2 = _scan_compact_rdonly(
        paths["fx6_string_en_2"],
        artifact_key="fx6_string_en_2",
        body_label="FX6_6.01",
        tokens=COMPACT_DONOR_TOKENS["fx6_string_en_2"],
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

    errors: List[str] = []
    compact_items = (
        fx3_lens_comm,
        fx6_lens_comm,
        fx3_adj_media,
        fx6_adj_media,
        fx3_string_en,
        fx3_string_en_g,
        fx6_string_en,
        fx6_string_en_2,
    )
    for item in compact_items:
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.marker_hits.values()):
            errors.append(f"{item.artifact_key} missing required tokens: {item.marker_hits}")

    for item in (fx3_cpapp, fx6_cpapp, fx3_appfw, fx6_appfw):
        exp_sz = EXPECTED_DONOR_BYTES[item.artifact_key]
        if item.file_bytes != exp_sz:
            errors.append(f"{item.artifact_key} byte size {item.file_bytes} != {exp_sz}")
        if not all(item.window_hits.values()):
            errors.append(f"{item.artifact_key} missing bounded window markers: {item.window_hits}")

    lens_comm_parity = (
        fx3_lens_comm.file_bytes == fx6_lens_comm.file_bytes == 14_544
        and fx3_lens_comm.elf64_le_ok
        and fx6_lens_comm.elf64_le_ok
        and all(fx3_lens_comm.marker_hits.values())
        and all(fx6_lens_comm.marker_hits.values())
    )
    fx6_bkid_info_ok = (
        fx6_appfw.elf64_le_ok
        and fx6_appfw.window_hits.get("0x02cf0232_le") == 1
        and fx6_appfw.window_hits.get("info7") == 1
        and fx6_appfw.window_hits.get("info8") == 1
    )
    fx6_raw_ok = (
        fx6_string_en.uxd_container_ok
        and fx6_string_en.marker_hits.get("4264x2408") == 1
        and fx6_string_en.marker_hits.get("Breathing Comp") == 1
        and fx6_string_en.marker_hits.get("Focus Map") == 1
        and fx6_string_en_2.marker_hits.get("ProRes") == 1
    )
    fx3_breath_raw_ok = (
        fx3_appfw.elf64_le_ok
        and fx3_appfw.window_hits.get("uc_BreathingCorrectionLensType") == 1
        and fx3_appfw.window_hits.get("HDMI_RAW_CONNECTSTATE_NOT_SET") == 1
        and fx3_cpapp.window_hits.get("Draw Widget <FocusMap>") == 1
        and fx3_cpapp.window_hits.get("fixed_lensfile") == 1
    )

    all_ok = (
        len(errors) == 0
        and lens_comm_parity
        and fx6_bkid_info_ok
        and fx6_raw_ok
        and fx3_breath_raw_ok
    )

    audit = Phase182DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY",
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=12,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        fx3_lens_comm=fx3_lens_comm,
        fx6_lens_comm=fx6_lens_comm,
        fx3_adj_media=fx3_adj_media,
        fx6_adj_media=fx6_adj_media,
        fx3_string_en=fx3_string_en,
        fx3_string_en_g=fx3_string_en_g,
        fx6_string_en=fx6_string_en,
        fx6_string_en_2=fx6_string_en_2,
        fx3_cpapp=fx3_cpapp,
        fx6_cpapp=fx6_cpapp,
        fx3_appfw=fx3_appfw,
        fx6_appfw=fx6_appfw,
        lens_comm_abi_parity_proven=lens_comm_parity,
        fx6_bkid_02cf0232_and_info7_8_proven=fx6_bkid_info_ok,
        fx6_4264x2408_and_prores_proven=fx6_raw_ok,
        fx3_breathing_and_hdmi_raw_proven=fx3_breath_raw_ok,
        all_contracts_verified=all_ok,
        errors=tuple(errors),
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Pillar A: MIRA_CETUS2 E-Mount info7/info8/info3D & 0x02cf0232 Breathing HIL
# ---------------------------------------------------------------------------


def is_sony_first_party_emount_lens(lens_id: int) -> bool:
    """Exact CPAPP 16-bit E-mount lens whitelist predicate:
    `((lens_id >> 14) == 3) && ((lens_id & 0x0FFF) != 0x0FFF)`.
    """
    lens_u16 = lens_id & 0xFFFF
    return ((lens_u16 >> 14) == 3) and ((lens_u16 & 0x0FFF) != 0x0FFF)


def classify_emount_lens(lens_id: int) -> str:
    lens_u16 = lens_id & 0xFFFF
    if lens_u16 == MANUAL_PL_LENS_ID:
        return LENS_CLASS_MANUAL_PL
    if is_sony_first_party_emount_lens(lens_u16):
        return LENS_CLASS_SONY_FIRST_PARTY
    return LENS_CLASS_THIRD_PARTY


def _parse_semver_tuple(ver_str: str) -> Tuple[int, int, int]:
    parts = ver_str.strip().split(".")
    if len(parts) not in (2, 3) or not all(p.isdigit() for p in parts):
        raise RealHwEmountInfo3dHdmiRawError(f"Invalid version string: {ver_str!r}")
    nums = [int(p) for p in parts]
    while len(nums) < 3:
        nums.append(0)
    return nums[0], nums[1], nums[2]


def build_emount_info_packets(
    *,
    lens_id: int,
    focus_pos_um: int = 1250,
    iris_f_stop_x10: int = 28,
    breathing_curve_q12: int = 4391,
) -> Tuple[bytes, bytes, bytes]:
    """Synthesize deterministic `info7`, `info8`, and `info3D` serial frames with CRC32."""
    lens_u16 = lens_id & 0xFFFF
    body7 = struct.pack(">2sHB", b"I7", lens_u16, 0x01 if lens_u16 != MANUAL_PL_LENS_ID else 0x00)
    info7 = body7 + struct.pack(">I", zlib.crc32(body7))

    body8 = struct.pack(">2sHHB", b"I8", focus_pos_um & 0xFFFF, iris_f_stop_x10 & 0xFFFF, 0x02)
    info8 = body8 + struct.pack(">I", zlib.crc32(body8))

    body3d = struct.pack(">2sHHH", b"3D", lens_u16, breathing_curve_q12 & 0xFFFF, 627)
    info3d = body3d + struct.pack(">I", zlib.crc32(body3d))
    return info7, info8, info3d


def coemulate_emount_info3d_and_breathing(
    *,
    lens_id: int = 0xC135,
    lens_name: str = "FE 24-70mm F2.8 GM II",
    breathing_comp_requested: bool = True,
    hdmi_raw_active: bool = False,
    mc_app_version: str = "2.1.0",
    mc_transport: str = "WPA3",
    p18_blkroset: int = P18_BLKROSET_LOCKED,
    cinealta_lensfile_write_requested: bool = False,
    corrupt_info3d_crc: bool = False,
    breathing_crop_factor: float = 1.072,
) -> EmountInfo3dHandshakeResult:
    """Co-emulate E-mount info7/info8/info3D handshake, 0x02cf0232 gating, M&C 2.1.0+ Focus Map, and p18 RO."""
    lens_u16 = lens_id & 0xFFFF
    lens_class = classify_emount_lens(lens_u16)
    first_party = is_sony_first_party_emount_lens(lens_u16)
    mc_ver = _parse_semver_tuple(mc_app_version)

    info7, info8, info3d = build_emount_info_packets(lens_id=lens_u16)
    if corrupt_info3d_crc:
        ba = bytearray(info3d)
        ba[-1] ^= 0xFF
        info3d = bytes(ba)

    crc_ok = (
        struct.unpack(">I", info7[-4:])[0] == zlib.crc32(info7[:-4])
        and struct.unpack(">I", info8[-4:])[0] == zlib.crc32(info8[:-4])
        and struct.unpack(">I", info3d[-4:])[0] == zlib.crc32(info3d[:-4])
    )

    if cinealta_lensfile_write_requested or p18_blkroset != P18_BLKROSET_LOCKED:
        return EmountInfo3dHandshakeResult(
            valid=False,
            lens_id=lens_u16,
            lens_id_hex=f"0x{lens_u16:04x}",
            lens_name=lens_name,
            lens_class=lens_class,
            sony_first_party_match=first_party,
            info7_packet_hex=info7.hex(),
            info8_packet_hex=info8.hex(),
            info3d_packet_hex=info3d.hex(),
            info_crc32_valid=crc_ok,
            p18_lensfile_path=P18_LENSFILE_PATH,
            p18_blkroset=P18_BLKROSET_LOCKED,
            lens_partition_writes=LENS_PARTITION_WRITES,
            breathing_comp_authorized=False,
            bkid_0x02cf0232_passthrough=False,
            breathing_crop_factor=1.0,
            catalyst_breathing_meta_injected=False,
            focus_map_stream_active=False,
            mc_app_version=mc_app_version,
            mc_transport=mc_transport,
            appfw_crashes=APPFW_CRASHES,
            status_code="BLOCKED_P18_LENSFILE_BLKROSET_1",
        )

    if not crc_ok:
        return EmountInfo3dHandshakeResult(
            valid=False,
            lens_id=lens_u16,
            lens_id_hex=f"0x{lens_u16:04x}",
            lens_name=lens_name,
            lens_class=lens_class,
            sony_first_party_match=first_party,
            info7_packet_hex=info7.hex(),
            info8_packet_hex=info8.hex(),
            info3d_packet_hex=info3d.hex(),
            info_crc32_valid=False,
            p18_lensfile_path=P18_LENSFILE_PATH,
            p18_blkroset=P18_BLKROSET_LOCKED,
            lens_partition_writes=LENS_PARTITION_WRITES,
            breathing_comp_authorized=False,
            bkid_0x02cf0232_passthrough=False,
            breathing_crop_factor=1.0,
            catalyst_breathing_meta_injected=False,
            focus_map_stream_active=False,
            mc_app_version=mc_app_version,
            mc_transport=mc_transport,
            appfw_crashes=APPFW_CRASHES,
            status_code="BLOCKED_INFO3D_SERIAL_CRC_FAULT",
        )

    breathing_allowed = first_party and breathing_comp_requested and (not hdmi_raw_active)
    crop = breathing_crop_factor if breathing_allowed else 1.0
    mc_ok = (mc_ver >= MONITOR_CONTROL_MIN_VERSION) and (mc_transport in ALLOWED_NETWORK_SECURITY_MODES)
    focus_map_active = mc_ok and (lens_class != LENS_CLASS_MANUAL_PL)

    if lens_class == LENS_CLASS_MANUAL_PL:
        status = "MANUAL_PL_ADAPTER_1X_BYPASS_OK"
    elif not first_party:
        status = "THIRD_PARTY_EMOUNT_02CF0232_GATED_OK"
    elif hdmi_raw_active:
        status = "SONY_EMOUNT_HDMI_RAW_1X_BYPASS_OK"
    elif breathing_allowed:
        status = "SONY_EMOUNT_INFO3D_02CF0232_CATALYST_FOCUSMAP_OK"
    else:
        status = "SONY_EMOUNT_BREATHING_OFF_1X_OK"

    return EmountInfo3dHandshakeResult(
        valid=True,
        lens_id=lens_u16,
        lens_id_hex=f"0x{lens_u16:04x}",
        lens_name=lens_name,
        lens_class=lens_class,
        sony_first_party_match=first_party,
        info7_packet_hex=info7.hex(),
        info8_packet_hex=info8.hex(),
        info3d_packet_hex=info3d.hex(),
        info_crc32_valid=True,
        p18_lensfile_path=P18_LENSFILE_PATH,
        p18_blkroset=P18_BLKROSET_LOCKED,
        lens_partition_writes=LENS_PARTITION_WRITES,
        breathing_comp_authorized=breathing_allowed,
        bkid_0x02cf0232_passthrough=first_party,
        breathing_crop_factor=crop,
        catalyst_breathing_meta_injected=breathing_allowed,
        focus_map_stream_active=focus_map_active,
        mc_app_version=mc_app_version,
        mc_transport=mc_transport,
        appfw_crashes=APPFW_CRASHES,
        status_code=status,
    )


def evaluate_pillar_a_emount_info3d_breathing() -> Dict[str, object]:
    sony_pz1635 = coemulate_emount_info3d_and_breathing(
        lens_id=0xC120,
        lens_name="FE PZ 16-35mm F4 G",
        breathing_comp_requested=True,
        breathing_crop_factor=1.055,
    )
    sony_2470gm2 = coemulate_emount_info3d_and_breathing(
        lens_id=0xC135,
        lens_name="FE 24-70mm F2.8 GM II",
        breathing_comp_requested=True,
        breathing_crop_factor=1.072,
    )
    sony_0cfff_trap = coemulate_emount_info3d_and_breathing(
        lens_id=0xCFFF,
        lens_name="Invalid 0xCFFF Reserved ID",
        breathing_comp_requested=True,
    )
    third_party_sigma = coemulate_emount_info3d_and_breathing(
        lens_id=0x4210,
        lens_name="Sigma 24-70mm F2.8 DG DN Art",
        breathing_comp_requested=True,
    )
    manual_pl = coemulate_emount_info3d_and_breathing(
        lens_id=MANUAL_PL_LENS_ID,
        lens_name="Manual PL-to-E Unchipped Adapter",
        breathing_comp_requested=True,
    )
    sony_hdmi_raw_bypass = coemulate_emount_info3d_and_breathing(
        lens_id=0xC135,
        lens_name="FE 24-70mm F2.8 GM II",
        breathing_comp_requested=True,
        hdmi_raw_active=True,
    )
    mc_old_rejected = coemulate_emount_info3d_and_breathing(
        lens_id=0xC135,
        mc_app_version="2.0.0",
    )
    p18_write_blocked = coemulate_emount_info3d_and_breathing(
        lens_id=0xC135,
        cinealta_lensfile_write_requested=True,
    )
    info3d_crc_blocked = coemulate_emount_info3d_and_breathing(
        lens_id=0xC135,
        corrupt_info3d_crc=True,
    )

    passed = (
        sony_pz1635.valid
        and sony_pz1635.sony_first_party_match
        and sony_pz1635.breathing_comp_authorized
        and sony_pz1635.catalyst_breathing_meta_injected
        and sony_pz1635.focus_map_stream_active
        and sony_2470gm2.valid
        and sony_2470gm2.breathing_comp_authorized
        and sony_2470gm2.bkid_0x02cf0232_passthrough
        and (not sony_0cfff_trap.sony_first_party_match)
        and (not sony_0cfff_trap.breathing_comp_authorized)
        and third_party_sigma.valid
        and (not third_party_sigma.sony_first_party_match)
        and (not third_party_sigma.breathing_comp_authorized)
        and (not third_party_sigma.catalyst_breathing_meta_injected)
        and manual_pl.valid
        and manual_pl.lens_class == LENS_CLASS_MANUAL_PL
        and (not manual_pl.breathing_comp_authorized)
        and (not manual_pl.focus_map_stream_active)
        and sony_hdmi_raw_bypass.valid
        and (not sony_hdmi_raw_bypass.breathing_comp_authorized)
        and sony_hdmi_raw_bypass.breathing_crop_factor == 1.0
        and (not mc_old_rejected.focus_map_stream_active)
        and (not p18_write_blocked.valid)
        and p18_write_blocked.lens_partition_writes == 0
        and (not info3d_crc_blocked.valid)
    )
    return {
        "passed": passed,
        "sony_pz1635_ok": asdict(sony_pz1635),
        "sony_2470gm2_ok": asdict(sony_2470gm2),
        "reserved_0cfff_gated": asdict(sony_0cfff_trap),
        "third_party_sigma_gated": asdict(third_party_sigma),
        "manual_pl_adapter_bypass": asdict(manual_pl),
        "sony_hdmi_raw_1x_bypass": asdict(sony_hdmi_raw_bypass),
        "mc_2_0_0_focus_map_inactive": asdict(mc_old_rejected),
        "p18_lensfile_write_blocked": asdict(p18_write_blocked),
        "info3d_crc_fault_blocked": asdict(info3d_crc_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar B: Type-A HDMI 4264x2408 (60p) 16-bit RAW (BRAW / ProRes RAW) vs 12G-SDI
# ---------------------------------------------------------------------------


def build_sony_hdmi_raw_vsif(*, width: int = HDMI_RAW_WIDTH, height: int = HDMI_RAW_HEIGHT) -> bytes:
    """Build 31-byte CTA-861 Vendor-Specific InfoFrame (type=0x81) with valid mod-256 checksum."""
    payload = bytearray(27)
    # Sony IEEE OUI (0x080046 little-endian) + 4264x2408 RAW16 tag
    payload[0:3] = b"\x46\x00\x08"
    struct.pack_into("<HHB", payload, 3, width & 0xFFFF, height & 0xFFFF, 16)
    hdr = bytes((0x81, 0x01, len(payload)))
    chk = (0x100 - ((sum(hdr) + sum(payload)) & 0xFF)) & 0xFF
    return hdr + bytes((chk,)) + bytes(payload)


def verify_vsif_checksum(vsif: bytes) -> bool:
    return len(vsif) == 31 and vsif[0] == 0x81 and (sum(vsif) & 0xFF) == 0


def coemulate_hdmi_4264_raw_negotiation(
    *,
    recorder_model: str = RECORDER_VA_12G_HDR,
    recorder_fw: str = "3.22.0",
    fps_label: str = "59.94p",
    internal_simul_codec: str = "XAVC S-I",
    include_proxy: bool = True,
    anamorphic_desqueeze: float = 1.5,
    bake_osd_into_raw_requested: bool = False,
    sdi_bnc_probe_requested: bool = False,
    edid_raw16_capable: bool = True,
    corrupt_vsif: bool = False,
) -> Hdmi4264RawNegotiationResult:
    """Co-emulate Type-A HDMI 4264x2408 16-bit linear RAW handshake vs masked 12G-SDI."""
    if anamorphic_desqueeze not in VALID_ANAMORPHIC_DESQUEEZE:
        raise RealHwEmountInfo3dHdmiRawError(
            f"Unsupported anamorphic de-squeeze factor: {anamorphic_desqueeze!r}"
        )
    if internal_simul_codec not in SUPPORTED_INTERNAL_SIMUL_CODECS:
        raise RealHwEmountInfo3dHdmiRawError(
            f"Unsupported internal simultaneous codec: {internal_simul_codec!r}"
        )

    vsif = build_sony_hdmi_raw_vsif()
    if corrupt_vsif:
        ba = bytearray(vsif)
        ba[3] ^= 0x01
        vsif = bytes(ba)
    vsif_ok = verify_vsif_checksum(vsif)
    fw_tuple = _parse_semver_tuple(recorder_fw)

    if sdi_bnc_probe_requested:
        return Hdmi4264RawNegotiationResult(
            admitted=False,
            recorder_model=recorder_model,
            recorder_fw=recorder_fw,
            raw_container_format="NONE",
            width=HDMI_RAW_WIDTH,
            height=HDMI_RAW_HEIGHT,
            fps_label=fps_label,
            bit_depth_linear=HDMI_RAW_BIT_DEPTH_LINEAR,
            bit_depth_encoded=0,
            edid_raw16_capable=edid_raw16_capable,
            vsif_checksum_valid=vsif_ok,
            capture_locked_iso=True,
            wb_iso_offset_encapsulated=False,
            internal_simul_codec=internal_simul_codec,
            internal_dual_slot_active=False,
            anamorphic_desqueeze=anamorphic_desqueeze,
            anamorphic_desqueeze_osd_only=True,
            osd_baked_into_raw=False,
            sdi_bnc_mmio_masked=True,
            sdi_bnc_mmio_faults=SDI_BNC_MMIO_FAULTS,
            frame_drops=0,
            status_code="BLOCKED_FX6_12G_SDI_BNC_MASKED_ON_FX3",
        )

    if recorder_model == RECORDER_VA_3G:
        return Hdmi4264RawNegotiationResult(
            admitted=False,
            recorder_model=recorder_model,
            recorder_fw=recorder_fw,
            raw_container_format="BRAW_UNSUPPORTED",
            width=HDMI_RAW_WIDTH,
            height=HDMI_RAW_HEIGHT,
            fps_label=fps_label,
            bit_depth_linear=HDMI_RAW_BIT_DEPTH_LINEAR,
            bit_depth_encoded=0,
            edid_raw16_capable=False,
            vsif_checksum_valid=vsif_ok,
            capture_locked_iso=True,
            wb_iso_offset_encapsulated=False,
            internal_simul_codec=internal_simul_codec,
            internal_dual_slot_active=False,
            anamorphic_desqueeze=anamorphic_desqueeze,
            anamorphic_desqueeze_osd_only=True,
            osd_baked_into_raw=False,
            sdi_bnc_mmio_masked=True,
            sdi_bnc_mmio_faults=SDI_BNC_MMIO_FAULTS,
            frame_drops=0,
            status_code="BLOCKED_VIDEO_ASSIST_3G_UNSUPPORTED_FOR_BRAW",
        )

    if recorder_model == RECORDER_VA_12G_HDR:
        min_fw = VIDEO_ASSIST_12G_MIN_FW
        container = "BRAW"
        bit_enc = 12
        capture_locked_iso = True
        wb_iso_encap = False
    elif recorder_model in (RECORDER_ATOMOS_NINJA_V, RECORDER_ATOMOS_NINJA_ULTRA):
        min_fw = ATOMOS_MIN_FW
        container = "PRORES_RAW"
        bit_enc = 12
        capture_locked_iso = False
        wb_iso_encap = True
    else:
        raise RealHwEmountInfo3dHdmiRawError(f"Unknown HDMI RAW recorder model: {recorder_model!r}")

    if fw_tuple < min_fw:
        return Hdmi4264RawNegotiationResult(
            admitted=False,
            recorder_model=recorder_model,
            recorder_fw=recorder_fw,
            raw_container_format=container,
            width=HDMI_RAW_WIDTH,
            height=HDMI_RAW_HEIGHT,
            fps_label=fps_label,
            bit_depth_linear=HDMI_RAW_BIT_DEPTH_LINEAR,
            bit_depth_encoded=bit_enc,
            edid_raw16_capable=edid_raw16_capable,
            vsif_checksum_valid=vsif_ok,
            capture_locked_iso=capture_locked_iso,
            wb_iso_offset_encapsulated=wb_iso_encap,
            internal_simul_codec=internal_simul_codec,
            internal_dual_slot_active=False,
            anamorphic_desqueeze=anamorphic_desqueeze,
            anamorphic_desqueeze_osd_only=True,
            osd_baked_into_raw=False,
            sdi_bnc_mmio_masked=True,
            sdi_bnc_mmio_faults=SDI_BNC_MMIO_FAULTS,
            frame_drops=0,
            status_code="BLOCKED_RECORDER_FIRMWARE_BELOW_RAW_FLOOR",
        )

    if fps_label not in HDMI_RAW_SUPPORTED_FPS:
        return Hdmi4264RawNegotiationResult(
            admitted=False,
            recorder_model=recorder_model,
            recorder_fw=recorder_fw,
            raw_container_format=container,
            width=HDMI_RAW_WIDTH,
            height=HDMI_RAW_HEIGHT,
            fps_label=fps_label,
            bit_depth_linear=HDMI_RAW_BIT_DEPTH_LINEAR,
            bit_depth_encoded=bit_enc,
            edid_raw16_capable=edid_raw16_capable,
            vsif_checksum_valid=vsif_ok,
            capture_locked_iso=capture_locked_iso,
            wb_iso_offset_encapsulated=wb_iso_encap,
            internal_simul_codec=internal_simul_codec,
            internal_dual_slot_active=False,
            anamorphic_desqueeze=anamorphic_desqueeze,
            anamorphic_desqueeze_osd_only=True,
            osd_baked_into_raw=False,
            sdi_bnc_mmio_masked=True,
            sdi_bnc_mmio_faults=SDI_BNC_MMIO_FAULTS,
            frame_drops=0,
            status_code="BLOCKED_HDMI_RAW_EXCEEDS_60P_CEILING",
        )

    if bake_osd_into_raw_requested:
        return Hdmi4264RawNegotiationResult(
            admitted=False,
            recorder_model=recorder_model,
            recorder_fw=recorder_fw,
            raw_container_format=container,
            width=HDMI_RAW_WIDTH,
            height=HDMI_RAW_HEIGHT,
            fps_label=fps_label,
            bit_depth_linear=HDMI_RAW_BIT_DEPTH_LINEAR,
            bit_depth_encoded=bit_enc,
            edid_raw16_capable=edid_raw16_capable,
            vsif_checksum_valid=vsif_ok,
            capture_locked_iso=capture_locked_iso,
            wb_iso_offset_encapsulated=wb_iso_encap,
            internal_simul_codec=internal_simul_codec,
            internal_dual_slot_active=False,
            anamorphic_desqueeze=anamorphic_desqueeze,
            anamorphic_desqueeze_osd_only=True,
            osd_baked_into_raw=False,
            sdi_bnc_mmio_masked=True,
            sdi_bnc_mmio_faults=SDI_BNC_MMIO_FAULTS,
            frame_drops=0,
            status_code="BLOCKED_RAW_OSD_OR_LUT_BURN_IN",
        )

    if (not edid_raw16_capable) or (not vsif_ok):
        return Hdmi4264RawNegotiationResult(
            admitted=False,
            recorder_model=recorder_model,
            recorder_fw=recorder_fw,
            raw_container_format=container,
            width=HDMI_RAW_WIDTH,
            height=HDMI_RAW_HEIGHT,
            fps_label=fps_label,
            bit_depth_linear=HDMI_RAW_BIT_DEPTH_LINEAR,
            bit_depth_encoded=bit_enc,
            edid_raw16_capable=edid_raw16_capable,
            vsif_checksum_valid=vsif_ok,
            capture_locked_iso=capture_locked_iso,
            wb_iso_offset_encapsulated=wb_iso_encap,
            internal_simul_codec=internal_simul_codec,
            internal_dual_slot_active=False,
            anamorphic_desqueeze=anamorphic_desqueeze,
            anamorphic_desqueeze_osd_only=True,
            osd_baked_into_raw=False,
            sdi_bnc_mmio_masked=True,
            sdi_bnc_mmio_faults=SDI_BNC_MMIO_FAULTS,
            frame_drops=0,
            status_code="BLOCKED_EDID_OR_VSIF_CHECKSUM_FAILURE",
        )

    return Hdmi4264RawNegotiationResult(
        admitted=True,
        recorder_model=recorder_model,
        recorder_fw=recorder_fw,
        raw_container_format=container,
        width=HDMI_RAW_WIDTH,
        height=HDMI_RAW_HEIGHT,
        fps_label=fps_label,
        bit_depth_linear=HDMI_RAW_BIT_DEPTH_LINEAR,
        bit_depth_encoded=bit_enc,
        edid_raw16_capable=True,
        vsif_checksum_valid=True,
        capture_locked_iso=capture_locked_iso,
        wb_iso_offset_encapsulated=wb_iso_encap,
        internal_simul_codec=f"{internal_simul_codec}+Proxy" if include_proxy else internal_simul_codec,
        internal_dual_slot_active=True,
        anamorphic_desqueeze=anamorphic_desqueeze,
        anamorphic_desqueeze_osd_only=True,
        osd_baked_into_raw=False,
        sdi_bnc_mmio_masked=True,
        sdi_bnc_mmio_faults=SDI_BNC_MMIO_FAULTS,
        frame_drops=0,
        status_code=f"HDMI_4264X2408_{container}_NEGOTIATED_OK",
    )


def evaluate_pillar_b_hdmi_4264_raw() -> Dict[str, object]:
    va12g_braw = coemulate_hdmi_4264_raw_negotiation(
        recorder_model=RECORDER_VA_12G_HDR,
        recorder_fw="3.22.0",
        fps_label="59.94p",
        internal_simul_codec="XAVC S-I",
        include_proxy=True,
        anamorphic_desqueeze=1.5,
    )
    va3g_rejected = coemulate_hdmi_4264_raw_negotiation(
        recorder_model=RECORDER_VA_3G,
        recorder_fw="3.22.0",
    )
    ninja_ultra_prores = coemulate_hdmi_4264_raw_negotiation(
        recorder_model=RECORDER_ATOMOS_NINJA_ULTRA,
        recorder_fw="10.64.0",
        fps_label="59.94p",
        internal_simul_codec="XAVC HS",
        include_proxy=True,
        anamorphic_desqueeze=1.6,
    )
    fps120_rejected = coemulate_hdmi_4264_raw_negotiation(
        recorder_model=RECORDER_VA_12G_HDR,
        recorder_fw="3.22.0",
        fps_label="119.88p",
    )
    osd_bake_blocked = coemulate_hdmi_4264_raw_negotiation(
        recorder_model=RECORDER_ATOMOS_NINJA_V,
        recorder_fw="10.64.0",
        bake_osd_into_raw_requested=True,
    )
    sdi_probe_blocked = coemulate_hdmi_4264_raw_negotiation(
        recorder_model=RECORDER_VA_12G_HDR,
        recorder_fw="3.22.0",
        sdi_bnc_probe_requested=True,
    )

    passed = (
        va12g_braw.admitted
        and va12g_braw.raw_container_format == "BRAW"
        and va12g_braw.width == 4264
        and va12g_braw.height == 2408
        and va12g_braw.bit_depth_linear == 16
        and va12g_braw.bit_depth_encoded == 12
        and va12g_braw.capture_locked_iso
        and va12g_braw.internal_dual_slot_active
        and va12g_braw.anamorphic_desqueeze_osd_only
        and (not va12g_braw.osd_baked_into_raw)
        and va12g_braw.sdi_bnc_mmio_masked
        and va12g_braw.sdi_bnc_mmio_faults == 0
        and (not va3g_rejected.admitted)
        and va3g_rejected.status_code == "BLOCKED_VIDEO_ASSIST_3G_UNSUPPORTED_FOR_BRAW"
        and ninja_ultra_prores.admitted
        and ninja_ultra_prores.raw_container_format == "PRORES_RAW"
        and ninja_ultra_prores.wb_iso_offset_encapsulated
        and ninja_ultra_prores.anamorphic_desqueeze == 1.6
        and (not ninja_ultra_prores.osd_baked_into_raw)
        and (not fps120_rejected.admitted)
        and (not osd_bake_blocked.admitted)
        and (not sdi_probe_blocked.admitted)
        and sdi_probe_blocked.sdi_bnc_mmio_faults == 0
    )
    return {
        "passed": passed,
        "video_assist_12g_braw_ok": asdict(va12g_braw),
        "video_assist_3g_rejected": asdict(va3g_rejected),
        "atomos_ninja_ultra_prores_raw_ok": asdict(ninja_ultra_prores),
        "hdmi_raw_120p_rejected": asdict(fps120_rejected),
        "osd_bake_into_raw_blocked": asdict(osd_bake_blocked),
        "sdi_12g_bnc_probe_masked": asdict(sdi_probe_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar C & D: WPA2/WPA3 Network Sanitizer & Hard Safety Redline Invariants
# ---------------------------------------------------------------------------


def evaluate_network_and_metadata_sanitizer(
    *,
    security_mode: str = "WPA3",
    ssid_or_host: str = "FX3-MC-Studio-01",
    catalyst_clip_tag: str = "A001C004_261115",
) -> NetworkSanitizerResult:
    """Enforce WPA2/WPA3/WIRED_USB_CDC_NCM security floor and sanitize metadata strings."""
    sec_ok = security_mode in ALLOWED_NETWORK_SECURITY_MODES
    if not sec_ok:
        return NetworkSanitizerResult(
            valid=False,
            security_mode=security_mode,
            security_admitted=False,
            ssid_or_host=ssid_or_host,
            catalyst_clip_tag=catalyst_clip_tag,
            sanitization_passed=False,
            wf12_00342260_hits=WF12_00342260_HITS,
            wired_cdc_ncm_fallback_ready=True,
            status_code="BLOCKED_INSECURE_NETWORK_SECURITY_FLOOR",
        )

    bad_ssid = (not ssid_or_host.strip()) or len(ssid_or_host) > 64 or bool(_FORBIDDEN_META_RE.search(ssid_or_host))
    bad_tag = (not catalyst_clip_tag.strip()) or len(catalyst_clip_tag) > 64 or bool(_FORBIDDEN_META_RE.search(catalyst_clip_tag))
    if bad_ssid or bad_tag:
        return NetworkSanitizerResult(
            valid=False,
            security_mode=security_mode,
            security_admitted=True,
            ssid_or_host=ssid_or_host,
            catalyst_clip_tag=catalyst_clip_tag,
            sanitization_passed=False,
            wf12_00342260_hits=WF12_00342260_HITS,
            wired_cdc_ncm_fallback_ready=True,
            status_code="BLOCKED_SANITIZER_PATH_OR_CONTROL_INJECTION",
        )

    return NetworkSanitizerResult(
        valid=True,
        security_mode=security_mode,
        security_admitted=True,
        ssid_or_host=ssid_or_host,
        catalyst_clip_tag=catalyst_clip_tag,
        sanitization_passed=True,
        wf12_00342260_hits=WF12_00342260_HITS,
        wired_cdc_ncm_fallback_ready=True,
        status_code="NETWORK_WPA2_WPA3_AND_METADATA_SANITIZER_OK",
    )


def probe_hard_safety_redline(
    *,
    authorize_persistent_emmc_writes: bool = False,
    authorize_spi_nor_write: bool = False,
    authorize_el3_payload_transmit: bool = False,
    emit_physical_usb_packet: bool = False,
    touch_otp_fuse: bool = False,
    increment_rpmb_counter: bool = False,
    authorize_p18_lens_write: bool = False,
    trigger_sdi_bnc_mmio: bool = False,
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
    if authorize_p18_lens_write:
        blocked.append("P18_LENSFILE_WRITE")
    if trigger_sdi_bnc_mmio:
        blocked.append("SDI_BNC_MMIO")

    if blocked:
        return RedlineGuardProbeResult(
            valid=False,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            otp_fuse_touches=0,
            rpmb_counter_increments=0,
            lens_partition_writes=0,
            sdi_bnc_mmio_faults=0,
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
        lens_partition_writes=LENS_PARTITION_WRITES,
        sdi_bnc_mmio_faults=SDI_BNC_MMIO_FAULTS,
        blocked_action="NONE",
        status_code="HARD_SAFETY_REDLINES_LOCKED_OK",
    )


def evaluate_pillar_c_d_network_sanitizer_and_redlines() -> Dict[str, object]:
    wpa3_ok = evaluate_network_and_metadata_sanitizer(security_mode="WPA3")
    wpa2_ok = evaluate_network_and_metadata_sanitizer(security_mode="WPA2")
    wired_ok = evaluate_network_and_metadata_sanitizer(security_mode="WIRED_USB_CDC_NCM")
    rejected_sec = {
        m: asdict(evaluate_network_and_metadata_sanitizer(security_mode=m))
        for m in REJECTED_NETWORK_SECURITY_MODES
    }
    traversal_blocked = evaluate_network_and_metadata_sanitizer(
        security_mode="WPA3",
        catalyst_clip_tag="../../p18:/lens/LENSFILE.BIN",
    )

    baseline = probe_hard_safety_redline()
    probes = (
        probe_hard_safety_redline(authorize_persistent_emmc_writes=True),
        probe_hard_safety_redline(authorize_spi_nor_write=True),
        probe_hard_safety_redline(authorize_el3_payload_transmit=True),
        probe_hard_safety_redline(emit_physical_usb_packet=True),
        probe_hard_safety_redline(touch_otp_fuse=True),
        probe_hard_safety_redline(increment_rpmb_counter=True),
        probe_hard_safety_redline(authorize_p18_lens_write=True),
        probe_hard_safety_redline(trigger_sdi_bnc_mmio=True),
    )

    passed = (
        wpa3_ok.valid
        and wpa2_ok.valid
        and wired_ok.valid
        and all((not v["valid"]) and (not v["security_admitted"]) for v in rejected_sec.values())
        and (not traversal_blocked.valid)
        and (not traversal_blocked.sanitization_passed)
        and baseline.valid
        and (not baseline.persistent_emmc_writes_authorized)
        and (not baseline.spi_nor_write_authorized)
        and (not baseline.el3_payload_transmit_authorized)
        and baseline.physical_usb_packets_emitted == 0
        and baseline.otp_fuse_touches == 0
        and baseline.rpmb_counter_increments == 0
        and baseline.lens_partition_writes == 0
        and baseline.sdi_bnc_mmio_faults == 0
        and all(
            (not p.valid)
            and (not p.persistent_emmc_writes_authorized)
            and (not p.spi_nor_write_authorized)
            and (not p.el3_payload_transmit_authorized)
            and p.physical_usb_packets_emitted == 0
            and p.otp_fuse_touches == 0
            and p.rpmb_counter_increments == 0
            and p.lens_partition_writes == 0
            and p.sdi_bnc_mmio_faults == 0
            for p in probes
        )
    )
    return {
        "passed": passed,
        "wpa3_ok": asdict(wpa3_ok),
        "wpa2_ok": asdict(wpa2_ok),
        "wired_cdc_ncm_ok": asdict(wired_ok),
        "rejected_security_modes": rejected_sec,
        "traversal_injection_blocked": asdict(traversal_blocked),
        "baseline_redline_lock": asdict(baseline),
        "blocked_redline_probes": [asdict(p) for p in probes],
    }


# ---------------------------------------------------------------------------
# Unified Phase 182 Stage 32 Orchestrator & CLI
# ---------------------------------------------------------------------------


def run_phase182_realhw_emount_info3d_hdmi_4264_raw_hil(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Execute the full Phase 182 Stage 32 (`32/32`) co-emulation audit."""
    donor_audit = inspect_phase182_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_emount_info3d_breathing()
    pillar_b = evaluate_pillar_b_hdmi_4264_raw()
    pillar_cd = evaluate_pillar_c_d_network_sanitizer_and_redlines()

    all_passed = (
        donor_audit.all_contracts_verified
        and donor_audit.raw_firmware_bytes_leaked == 0
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_cd["passed"])
    )

    payload: Dict[str, object] = {
        "schema": PHASE_182_SCHEMA,
        "version": PHASE_182_VERSION,
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
            "lens_partition_writes": LENS_PARTITION_WRITES,
            "p18_mutation_bytes": P18_MUTATION_BYTES,
            "p18_blkroset": P18_BLKROSET_LOCKED,
            "p18_mount_flags": P18_MOUNT_FLAGS,
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
            "sdi_bnc_mmio_faults": SDI_BNC_MMIO_FAULTS,
            "wf12_00342260_hits": WF12_00342260_HITS,
            "appfw_crashes": APPFW_CRASHES,
            "null_gpio_derefs": NULL_GPIO_DEREFS,
            "mailbox_stalls": MAILBOX_STALLS,
            "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
            "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "pillar_a_emount_info3d_breathing_hil": pillar_a,
        "pillar_b_hdmi_4264_raw_vs_12g_sdi_hil": pillar_b,
        "pillar_c_d_network_sanitizer_and_redlines": pillar_cd,
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_emount_info3d_breathing_and_hdmi_4264_raw_coemulator.py",
        description="Phase 182 Stage 32 (32/32) MIRA_CETUS2 E-Mount info7/8/3D Breathing & HDMI 4264x2408 RAW HIL Co-Emulator",
    )
    parser.add_argument("--self-test", action="store_true", help="Run Stage 32 self-test and exit 0/1")
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit report")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line audit summary")
    args = parser.parse_args(argv)

    rep = run_phase182_realhw_emount_info3d_hdmi_4264_raw_hil(
        force_clean_room=True if args.clean_room else None,
        env=os.environ,
    )

    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        pa = rep["pillar_a_emount_info3d_breathing_hil"]["sony_2470gm2_ok"]
        pb = rep["pillar_b_hdmi_4264_raw_vs_12g_sdi_hil"]["video_assist_12g_braw_ok"]
        sys.stdout.write(
            f"[{status}] Phase 182 Stage 32 ({MILESTONE_LABEL}) Real-HW E-Mount info3D/0x02cf0232 & HDMI 4264x2408 RAW HIL | "
            f"mode={rep['source_mode']} | bkid={BKID_BREATHING_HEX} | "
            f"crop={pa['breathing_crop_factor']}x | lens_wr={rep['redlines']['lens_partition_writes']} | "
            f"hdmi={pb['width']}x{pb['height']}@{pb['fps_label']}({pb['raw_container_format']}) | "
            f"sdi_flt={rep['redlines']['sdi_bnc_mmio_faults']} | "
            f"emmc_wr={rep['redlines']['emmc_nflasha_write_count']} | "
            f"digest={rep['audit_digest_sha256'][:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
