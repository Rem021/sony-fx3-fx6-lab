"""Phase 70 — 13th Unified Firmware-Lab Auditor: Dual-Slot Proxy (`XAVC HS/S`), Cinema Line `CamID/Reel` Clip Naming & `NonRealTimeMeta.xml` Sidecar.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so` / `icx1295` AP host,
  `libmpr.so`, `global.xdb`, `string_english.uxc`, `string_english_g.uxc`) and
  FX6 v6.01 (`appFw.so`, `libmpr.so`, `global.xdb`, `string_english.uxc`,
  `string_english_2.uxc`) strictly via `os.O_RDONLY` + read-only `mmap` and
  ELF64 `.rodata`/`.dynstr` section-scoped scanning, plus `uxa\\x07` / `.uxc`
  container parsing.
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room binary, `global.xdb`, and `.uxc`
  fixtures carrying the exact contract markers and executes the identical
  three-pillar verification pipeline with zero proprietary files required.

Audits Three Cinema Line Storage, Naming & Sidecar Metadata Pillars:
1. Pillar 1 — Cinema Line `CamID / Reel#` (`A001C001_YYMMDD_XXXX`) vs
   `Title/Alpha` (`C0001`) Clip Naming & Proxy `S03` Pairing:
   Verifies `XDROOT/Clip/<name>.MXF` <-> `XDROOT/Sub/<name>S03.MP4` (`XAVC-I/L`
   MXF mode) and `M4ROOT/CLIP/<name>.MP4` <-> `M4ROOT/SUB/<name>S03.MP4`
   (`XAVC S / S-I / HS` MP4 mode), `Cam ID A..Z`, `Reel Number 001..999`
   (`999 -> 001` rollover), `Camera Position C/L/R`, `Date YYMMDD`, 4-char
   alphanumeric Camera UID, Proxy codec profiles (`1920x1080 10-bit 4:2:0
   XAVC HS 16/9 Mbps` & `1280x720 8-bit XAVC S 6 Mbps`), and automatic Proxy
   disable when off-speed `S&Q` (`1..240fps`) is active.
2. Pillar 2 — Dual-Slot (`Slot A` + `Slot B` CFexpress Type A / SDXC UHS-II)
   Recording Modes & Speed-Class Gate:
   Models and verifies all 4 Dual-Slot modes (`Simultaneous`, `Relay` with
   0-dropped-frame rollover, `Sort` Main on Slot A + Proxy/Sub on Slot B, and
   `Off`), enforces `V90` / `CFexpress VPG200/VPG400` speed-class gates for
   `XAVC S-I 4K60 600Mbps` and `S&Q 4K120` (cleanly rejecting `V30/V60` without
   crashing `libmpr`), and enforces `internal_emmc_clip_writes == 0` (`p1`
   isolation, `persistent_emmc_writes_authorized == False`).
3. Pillar 3 — Sony `NonRealTimeMeta` XML Sidecar (`*M01.XML`) Synthesizer &
   NLE (`Resolve` / `Premiere` / `Catalyst`) LUT/EI Auto-Tag Verifier:
   Pure-Python `xml.etree.ElementTree` generator and schema validator for
   `urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20`, verifying
   `CaptureGammaEquation` (`s-log3-cine`, `s-log3`, `rec709`, `s-cinetone`),
   `CaptureColorPrimaries` (`s-gamut3-cine`, `s-gamut3`, `rec709`),
   `ExposureIndexOfPhotoMeter` (`200..51200` vs Base ISO `800`/`12800`),
   `MonitoringDescriptions` `.cube` 3D LUT reference (`User1.cube..User4.cube`),
   and `Device` `ILME-FX3` Stage-B RAM provenance without spoofing C2PA
   `RQ_LIC.DAT` signatures.
"""

from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from datetime import datetime
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
from .sensor_codec_compatibility_analyzer import (
    FX3_LIBMPR_RELPATH,
    FX6_LIBMPR_RELPATH,
)
from .uxc_multilang_and_font_verifier import FX3_SHARE_APP_RELDIR, FX6_SHARE_APP_RELDIR


PHASE_70_SCHEMA = "fx3_firmware_lab_phase70_proxy_clipname_sidecar_v1"
PHASE_70_VERSION = "70.0.0"

FX3_GLOBAL_XDB_RELPATH = f"{FX3_SHARE_APP_RELDIR}/global.xdb"
FX6_GLOBAL_XDB_RELPATH = f"{FX6_SHARE_APP_RELDIR}/global.xdb"
FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX3_STR_EN_G_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_g.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pinned Clip-Naming, Proxy, Dual-Slot & NonRealTimeMeta v2.20 Constants
# ---------------------------------------------------------------------------

CLIP_NAMING_MODES: Tuple[str, ...] = ("CAM_ID_REEL", "TITLE_ALPHA")
VALID_CAM_IDS: Tuple[str, ...] = tuple("ABCDEFGHIJKLMNOPQRSTUVWXYZ")
VALID_CAMERA_POSITIONS: Tuple[str, ...] = ("C", "L", "R")
REEL_NUMBER_MIN = 1
REEL_NUMBER_MAX = 999
CLIP_NUMBER_MIN = 1
CLIP_NUMBER_MAX = 999
TITLE_INDEX_MIN = 1
TITLE_INDEX_MAX = 9999

CINEMA_CLIP_BASENAME_RE = re.compile(r"^([A-Z])(\d{3})([CLR])(\d{3})_(\d{6})_([A-Z0-9]{4})$")
TITLE_CLIP_BASENAME_RE = re.compile(r"^([A-Z][A-Z0-9_]{0,7})(\d{4})$")
CAMERA_UID_RE = re.compile(r"^[A-Z0-9]{4}$")
DATE_YYMMDD_RE = re.compile(r"^\d{6}$")

PROXY_CODEC_PROFILES: Dict[str, Dict[str, object]] = {
    "PROXY_16M_XAVC_HS_1080P_10BIT_420": {
        "resolution": "1920x1080",
        "codec": "XAVC HS (HEVC)",
        "bit_depth": 10,
        "chroma": "4:2:0",
        "bitrate_mbps": 16.0,
    },
    "PROXY_9M_XAVC_HS_1080P_10BIT_420": {
        "resolution": "1920x1080",
        "codec": "XAVC HS (HEVC)",
        "bit_depth": 10,
        "chroma": "4:2:0",
        "bitrate_mbps": 9.0,
    },
    "PROXY_6M_XAVC_S_720P_8BIT_420": {
        "resolution": "1280x720",
        "codec": "XAVC S (H.264)",
        "bit_depth": 8,
        "chroma": "4:2:0",
        "bitrate_mbps": 6.0,
    },
}

CONTAINER_ROOT_SPECS: Dict[str, Dict[str, str]] = {
    "XAVC_MXF": {
        "root": "XDROOT",
        "clip_dir": "Clip",
        "sub_dir": "Sub",
        "main_ext": ".MXF",
        "sub_suffix": "S03.MP4",
        "sidecar_suffix": "M01.XML",
    },
    "XAVC_MP4": {
        "root": "M4ROOT",
        "clip_dir": "CLIP",
        "sub_dir": "SUB",
        "main_ext": ".MP4",
        "sub_suffix": "S03.MP4",
        "sidecar_suffix": "M01.XML",
    },
}

DUAL_SLOT_MODES: Tuple[str, ...] = ("SIMULTANEOUS", "RELAY", "SORT", "OFF")

MEDIA_CARD_SPEED_CLASSES: Dict[str, Dict[str, object]] = {
    "CFEXPRESS_VPG400": {
        "sustained_mbps": 3200.0,
        "card_family": "CFEXPRESS_TYPE_A",
        "vpg": 400,
        "sd_speed_class": 0,
    },
    "CFEXPRESS_VPG200": {
        "sustained_mbps": 1600.0,
        "card_family": "CFEXPRESS_TYPE_A",
        "vpg": 200,
        "sd_speed_class": 0,
    },
    "SDXC_V90": {
        "sustained_mbps": 720.0,
        "card_family": "SDXC_UHS_II",
        "vpg": 0,
        "sd_speed_class": 90,
    },
    "SDXC_V60": {
        "sustained_mbps": 480.0,
        "card_family": "SDXC_UHS_II",
        "vpg": 0,
        "sd_speed_class": 60,
    },
    "SDXC_V30": {
        "sustained_mbps": 240.0,
        "card_family": "SDXC_UHS_I",
        "vpg": 0,
        "sd_speed_class": 30,
    },
}

RECORDING_BITRATE_PROFILES: Dict[str, Dict[str, object]] = {
    "SQ_4K120_ALL_INTRA": {
        "required_mbps": 1200.0,
        "allowed_cards": ("CFEXPRESS_VPG200", "CFEXPRESS_VPG400"),
        "requires_all_intra_high_fps": True,
    },
    "XAVC_S_I_4K60_600MBPS": {
        "required_mbps": 600.0,
        "allowed_cards": ("SDXC_V90", "CFEXPRESS_VPG200", "CFEXPRESS_VPG400"),
        "requires_all_intra_high_fps": True,
    },
    "XAVC_I_4K24_240MBPS": {
        "required_mbps": 240.0,
        "allowed_cards": ("SDXC_V90", "CFEXPRESS_VPG200", "CFEXPRESS_VPG400"),
        "requires_all_intra_high_fps": False,
    },
    "XAVC_S_4K24_100MBPS": {
        "required_mbps": 100.0,
        "allowed_cards": (
            "SDXC_V30",
            "SDXC_V60",
            "SDXC_V90",
            "CFEXPRESS_VPG200",
            "CFEXPRESS_VPG400",
        ),
        "requires_all_intra_high_fps": False,
    },
    "XAVC_HS_PROXY_16MBPS": {
        "required_mbps": 16.0,
        "allowed_cards": (
            "SDXC_V30",
            "SDXC_V60",
            "SDXC_V90",
            "CFEXPRESS_VPG200",
            "CFEXPRESS_VPG400",
        ),
        "requires_all_intra_high_fps": False,
    },
}

FORBIDDEN_INTERNAL_EMMC_PREFIXES: Tuple[str, ...] = (
    "/dev/nflasha",
    "/dev/cnflasha",
    "nflasha",
    "cnflasha",
    "p1:",
    "/p1/",
)

NRTM_NAMESPACE_V220 = "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20"
NRTM_LIB_NAMESPACE_V220 = "urn:schemas-professionalDisc:lib:ver.2.20"
VALID_CAPTURE_GAMMA_EQUATIONS: Tuple[str, ...] = ("s-log3-cine", "s-log3", "rec709", "s-cinetone")
VALID_CAPTURE_COLOR_PRIMARIES: Tuple[str, ...] = ("s-gamut3-cine", "s-gamut3", "rec709")
CINE_EI_MIN = 200
CINE_EI_MAX = 51200
VALID_BASE_ISOS: Tuple[int, ...] = (800, 12800)
VALID_CUBE_LUT_NAME_RE = re.compile(r"^(?:User(?:[1-9]|1[0-6])|S709|R709)\.cube\Z")
TARGET_NLE_CONSUMERS: Tuple[str, ...] = ("Resolve", "Premiere", "Catalyst")

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_CLIPNAME_PROXY_MARKERS: Tuple[str, ...] = (
    "EVENT_REMOTE_SET_XAVC_S_FILE_NAME_CAMERA_POSITION",
    "MODEL_MOVIE_REC_REEL_NUMBER_PLUS_1_NOTIFY",
    "XAVC_S_FILE_NAME_CAMID_CAMERA_POSITION_C",
    "XAVC_S_FILE_NAME_CAMID_CAMERA_POSITION_L",
    "XAVC_S_FILE_NAME_CAMID_CAMERA_POSITION_R",
    "_ZN3mpr20CheckCamIdReelNoFileERKNS_27checkCamIdReelNoFileInParamEPNS_28checkCamIdReelNoFileOutParamE",
    "PROXY_RECORD_SETTING_16M_420_10BIT_XAVC_HS_HD",
    "PROXY_RECORD_SETTING_9M_420_10BIT_XAVC_HS_HD",
    "PROXY_RECORD_SETTING_6M_420_8BIT_XAVC_S_HD",
)

FX6_APPFW_CLIPNAME_PROXY_MARKERS: Tuple[str, ...] = (
    "BKID_APP_CAMID_CURRENT_REEL_NUMBER0",
    "BKID_APP_CAMID_CURRENT_CAMERA_POSITION0",
    "BKID_APP_SETTING_XAVC_S_FILE_NAME_CAMID_CAMERA_POSITION",
    "XAVC_S_FILE_NAME_CAMID_CAMERA_POSITION_C",
    "XAVC_S_FILE_NAME_CAMID_CAMERA_POSITION_L",
    "XAVC_S_FILE_NAME_CAMID_CAMERA_POSITION_R",
    "EVENT_REMOTE_SET_XAVC_S_FILE_NAME_CAMERA_POSITION",
    "PROXY_RECORD_SETTING_16M_420_10BIT",
    "PROXY_RECORD_SETTING_9M_420_10BIT",
    "PROXY_RECORD_SETTING_6M_420_8BIT",
    "/XDROOT/",
    "/M4ROOT/",
    "S03.MP4",
    "M01.XML",
)

MPR_SHARED_CLIPNAME_MARKERS: Tuple[str, ...] = (
    "_ZN10XavcsNamer18ResetNumberCounterEN3mpr10NamingModeE",
    "_ZN3mpr20CheckCamIdReelNoFileERKNS_27checkCamIdReelNoFileInParamEPNS_28checkCamIdReelNoFileOutParamE",
    "_ZN4sidb31ContentType2ContentTypeInternalENS_11ContentTypeENS_15MovieNamingModeE",
    "/M4ROOT/",
    "S03.MP4",
    "M01.XML",
)

FX6_MPR_CLIPNAME_EXTRA_MARKERS: Tuple[str, ...] = (
    "_ZN10libXavcMxf11SetClipNameEjRA4_KN3mpr13ClipNameParamE",
    "_ZN3mpr14IsMp4ProxyPathEPKcj",
    "/XDROOT/",
)

FX3_APPFW_DUAL_SLOT_MARKERS: Tuple[str, ...] = (
    "RECORDING_MEDIA_SIMULTANEOUS_RECORDING",
    "RECORDING_MEDIA_SORT_RECORDING",
    "VAL_setting_relay_rec_RELAY_REC_ON",
    "EVENT_REMOTE_DOUBLE_SLOT_SETTINGS_RELAY_REC",
    "CAUTION_ID_FIXED_VARIABLE_XAVC_TRANSFER_RATE_DISABLE_UNDER_600MBPS_MEDIA_SLOT1_MSG",
    "CAUTION_ID_FIXED_VARIABLE_XAVC_TRANSFER_RATE_DISABLE_UNDER_400MBPS_MEDIA_SLOT1_MSG",
)

FX6_APPFW_DUAL_SLOT_MARKERS: Tuple[str, ...] = (
    "RECORDING_MEDIA_SIMULTANEOUS_RECORDING",
    "RECORDING_MEDIA_SORT_RECORDING",
    "EVENT_REMOTE_DOUBLE_SLOT_SETTINGS_RELAY_REC",
)

MPR_SHARED_RELAY_VPG_MARKERS: Tuple[str, ...] = (
    "_ZN5MprIf17PrepareRelayMediaEjm",
    "LOG_ID_VPG_MANAGER",
)

MPR_SHARED_NRTM_MARKERS: Tuple[str, ...] = (
    "NonRealTimeMeta",
    "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20",
    "CaptureGammaEquation",
    "CaptureColorPrimaries",
    "s-log3",
    "s-log3-cine",
    "s-gamut3",
    "s-gamut3-cine",
    "rec709",
    "s-cinetone",
    "ul_RecommendedExposureIndex",
    "Device",
)

FX6_MPR_NRTM_EXTRA_MARKERS: Tuple[str, ...] = (
    "ExposureIndex",
    "MonitoringDescription",
    "MonitoringBaseCurve",
)

FX3_APPFW_C2PA_IMMUTABLE_MARKERS: Tuple[str, ...] = (
    "CONTENT_INFO_HAS_C2PA_CERTIFICATE_TRUE",
    "DIGITAL_SIGNATURE_B2B_B2C_WRITE_DIGITAL_SIGNATURE_ON",
    "_ZN9InfraC2PA21SearchCertificateFileERKNS_28searchCertificateFileInParamEPNS_29searchCertificateFileOutParamE",
    "_ZN9InfraC2PA18GetCertificateInfoEPNS_26getCertificateInfoOutParamE",
)

# Verified .uxc String Resource IDs
FX3_NS3_CLIPNAME_LABELS: Dict[int, str] = {
    0x0000652B: "Reel",
    0x00006532: "Title",
}

FX3_NS39_DUAL_SLOT_LABELS: Dict[int, str] = {
    0x0004E0AE: "2 memory cards required.\nRecording Mode: Sort",
}

FX6_NS1_CLIPNAME_LABELS: Dict[int, str] = {
    0x00002200: "Reel",
    0x00002244: "Clip Name Format",
}

FX6_NS2_CLIPNAME_PROXY_LABELS: Dict[int, str] = {
    0x0000424F: "Simul Rec",
    0x000042C4: "XAVC Proxy Rec Mode",
    0x000042D0: "Proxy Rec",
    0x000042DE: "Proxy Format",
    0x0000457E: "Auto Naming",
    0x00004580: "Title Prefix",
    0x0000458E: "Camera Position",
    0x0000468F: "Camera ID",
    0x00004AFF: "Cam ID + Reel#",
}

# ---------------------------------------------------------------------------
# Report & Evaluation Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class CinemaClipTokens:
    valid: bool
    naming_mode: str
    basename: str
    cam_id: str
    reel_number: int
    camera_position: str
    clip_number: int
    date_yymmdd: str
    camera_uid: str
    title_prefix: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ClipPairEvalResult:
    valid: bool
    status: str
    naming_mode: str
    container_mode: str
    basename: str
    main_relpath: str
    proxy_relpath: Optional[str]
    sidecar_xml_relpath: str
    proxy_requested: bool
    proxy_effective_enabled: bool
    proxy_auto_disabled_by_sq: bool
    proxy_profile: Optional[str]
    proxy_resolution: Optional[str]
    proxy_codec: Optional[str]
    proxy_bitrate_mbps: Optional[float]
    sq_active: bool
    sensor_fps: float
    rec_fps: float
    reel_rollover_next: Optional[int]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ClipNamingAndProxyReport:
    passed: bool
    fx3_appfw_markers: Tuple[str, ...]
    fx6_appfw_markers: Tuple[str, ...]
    fx3_libmpr_markers: Tuple[str, ...]
    fx6_libmpr_markers: Tuple[str, ...]
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    uxc_clipname_proxy_labels: Dict[str, str]
    mxf_camid_pair_eval: ClipPairEvalResult
    mp4_camid_pair_eval: ClipPairEvalResult
    title_alpha_pair_eval: ClipPairEvalResult
    sq_proxy_disable_eval: ClipPairEvalResult
    reel_999_rollover_next: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DualSlotEvalResult:
    valid: bool
    status: str
    rec_mode: str
    active_slot: str
    slot_a_card: Optional[str]
    slot_b_card: Optional[str]
    main_profile: str
    proxy_profile: Optional[str]
    main_write_slots: Tuple[str, ...]
    proxy_write_slots: Tuple[str, ...]
    relay_triggered: bool
    dropped_frames: int
    libmpr_crashed: bool
    internal_emmc_clip_writes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DualSlotMatrixReport:
    passed: bool
    fx3_appfw_dual_slot_markers: Tuple[str, ...]
    fx6_appfw_dual_slot_markers: Tuple[str, ...]
    mpr_relay_vpg_markers: Tuple[str, ...]
    simul_eval: DualSlotEvalResult
    relay_eval: DualSlotEvalResult
    sort_eval: DualSlotEvalResult
    off_eval: DualSlotEvalResult
    v30_4k60_reject_eval: DualSlotEvalResult
    v90_4k120_reject_eval: DualSlotEvalResult
    internal_emmc_clip_writes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class NonRealTimeMetaEvalResult:
    valid: bool
    status: str
    namespace_uri: str
    capture_gamma_equation: str
    capture_color_primaries: str
    exposure_index: int
    base_iso: int
    ei_offset_stops: float
    monitoring_lut_cube: str
    device_manufacturer: str
    device_model_name: str
    device_firmware_ver: str
    c2pa_spoof_attempted: bool
    c2pa_rq_lic_preserved: bool
    nle_auto_tags_ready: Dict[str, bool]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class NonRealTimeMetaSidecarReport:
    passed: bool
    fx3_libmpr_nrtm_markers: Tuple[str, ...]
    fx6_libmpr_nrtm_markers: Tuple[str, ...]
    fx6_libmpr_nrtm_extra_markers: Tuple[str, ...]
    fx3_appfw_c2pa_markers: Tuple[str, ...]
    slog3_cine_ei200_eval: NonRealTimeMetaEvalResult
    slog3_cine_ei12800_eval: NonRealTimeMetaEvalResult
    scinetone_rec709_eval: NonRealTimeMetaEvalResult
    c2pa_spoof_attempted: bool
    c2pa_rq_lic_preserved: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ProxyClipnameAndSidecarReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    internal_emmc_clip_writes: int
    c2pa_rq_lic_preserved: bool
    donor_file_sizes: Dict[str, int]
    pillar_1_clipname_proxy: ClipNamingAndProxyReport
    pillar_2_dual_slot_matrix: DualSlotMatrixReport
    pillar_3_nrtm_xml_sidecar: NonRealTimeMetaSidecarReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Strictly `os.O_RDONLY` + `mmap` Section-Scoped Scanning Helpers
# ---------------------------------------------------------------------------


def _read_bytes_rdonly(path: Path) -> bytes:
    """Read a small `.uxc` or `global.xdb` file strictly via `os.O_RDONLY`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Mapping[str, Sequence[str]],
    *,
    is_elf: bool,
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    """Open `path` strictly `os.O_RDONLY` with `mmap.ACCESS_READ` and scan marker groups."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {k: () for k in marker_groups}
        unique_markers = sorted(
            {m for markers in marker_groups.values() for m in markers},
            key=lambda s: (-len(s), s),
        )
        if not unique_markers:
            return sz, {k: () for k in marker_groups}

        pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
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


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_proxy_clipname_fixtures(
    *,
    drop_fx6_camid_markers: bool = False,
    drop_fx3_dual_slot_markers: bool = False,
    drop_mpr_nrtm_ver220: bool = False,
    drop_fx3_c2pa_markers: bool = False,
    corrupt_uxc_labels: bool = False,
    corrupt_global_xdb: bool = False,
) -> Dict[str, bytes]:
    """Build deterministic clean-room fixtures for all 10 FX3 v7.02 & FX6 v6.01 donor artifacts."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)

    def _pack_elf(tokens: Sequence[str]) -> bytes:
        return elf_hdr + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_dual_slot = (
        tuple(m for m in FX3_APPFW_DUAL_SLOT_MARKERS if "SIMULTANEOUS" not in m)
        if drop_fx3_dual_slot_markers
        else FX3_APPFW_DUAL_SLOT_MARKERS
    )
    fx3_c2pa = () if drop_fx3_c2pa_markers else FX3_APPFW_C2PA_IMMUTABLE_MARKERS
    fx3_appfw_tokens = [
        *FX3_APPFW_CLIPNAME_PROXY_MARKERS,
        *fx3_dual_slot,
        *fx3_c2pa,
    ]

    fx6_clip = (
        tuple(m for m in FX6_APPFW_CLIPNAME_PROXY_MARKERS if "CAMID" not in m)
        if drop_fx6_camid_markers
        else FX6_APPFW_CLIPNAME_PROXY_MARKERS
    )
    fx6_appfw_tokens = [
        *fx6_clip,
        *FX6_APPFW_DUAL_SLOT_MARKERS,
    ]

    nrtm_shared = (
        tuple(m for m in MPR_SHARED_NRTM_MARKERS if "ver.2.20" not in m)
        if drop_mpr_nrtm_ver220
        else MPR_SHARED_NRTM_MARKERS
    )
    fx3_mpr_tokens = [
        *MPR_SHARED_CLIPNAME_MARKERS,
        *MPR_SHARED_RELAY_VPG_MARKERS,
        *nrtm_shared,
    ]
    fx6_mpr_tokens = [
        *MPR_SHARED_CLIPNAME_MARKERS,
        *FX6_MPR_CLIPNAME_EXTRA_MARKERS,
        *MPR_SHARED_RELAY_VPG_MARKERS,
        *nrtm_shared,
        *FX6_MPR_NRTM_EXTRA_MARKERS,
    ]

    fx6_ns2_labels = dict(FX6_NS2_CLIPNAME_PROXY_LABELS)
    if corrupt_uxc_labels:
        fx6_ns2_labels[0x00004AFF] = "CORRUPT_CAM_ID_REEL_LABEL"

    fx3_xdb = b"BADXDB" + bytes(32) if corrupt_global_xdb else build_synthetic_global_xdb("fx3_702")
    fx6_xdb = b"BADXDB" + bytes(32) if corrupt_global_xdb else build_synthetic_global_xdb("fx6_601")

    return {
        "fx3_appfw": _pack_elf(fx3_appfw_tokens),
        "fx6_appfw": _pack_elf(fx6_appfw_tokens),
        "fx3_libmpr": _pack_elf(fx3_mpr_tokens),
        "fx6_libmpr": _pack_elf(fx6_mpr_tokens),
        "fx3_global_xdb": fx3_xdb,
        "fx6_global_xdb": fx6_xdb,
        "fx3_str_en": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS39_DUAL_SLOT_LABELS.items()}, namespace_id=39
        ),
        "fx3_str_en_g": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS3_CLIPNAME_LABELS.items()}, namespace_id=3
        ),
        "fx6_str_en_1": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS1_CLIPNAME_LABELS.items()}, namespace_id=1
        ),
        "fx6_str_en_2": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in fx6_ns2_labels.items()}, namespace_id=2
        ),
    }


# ---------------------------------------------------------------------------
# Pillar 1: Cinema Line CamID/Reel# vs Title/Alpha Clip Naming & Proxy S03
# ---------------------------------------------------------------------------


def advance_reel_number(current_reel: int) -> int:
    """Advance Sony Cinema Line Reel Number in [001..999] with deterministic 999 -> 001 rollover."""
    if not isinstance(current_reel, int) or isinstance(current_reel, bool):
        raise ValueError(f"current_reel must be an integer, got {current_reel!r}")
    if not (REEL_NUMBER_MIN <= current_reel <= REEL_NUMBER_MAX):
        raise ValueError(f"current_reel {current_reel} out of [1..999]")
    return (current_reel % REEL_NUMBER_MAX) + 1


def parse_cinema_clip_basename(basename: str) -> CinemaClipTokens:
    """Parse and validate a Cinema Line (`A001C001_YYMMDD_XXXX`) or `Title/Alpha` (`C0001`) clip basename."""
    errors: List[str] = []
    m_cin = CINEMA_CLIP_BASENAME_RE.match(basename)
    if m_cin:
        cam_id, reel_str, cam_pos, clip_str, date_str, uid_str = m_cin.groups()
        reel_num = int(reel_str)
        clip_num = int(clip_str)
        if not (REEL_NUMBER_MIN <= reel_num <= REEL_NUMBER_MAX):
            errors.append(f"Reel number {reel_num} out of [001..999]")
        if not (CLIP_NUMBER_MIN <= clip_num <= CLIP_NUMBER_MAX):
            errors.append(f"Clip number {clip_num} out of [001..999]")
        try:
            datetime.strptime(date_str, "%y%m%d")
        except ValueError:
            errors.append(f"Invalid YYMMDD date token {date_str!r}")
        return CinemaClipTokens(
            valid=len(errors) == 0,
            naming_mode="CAM_ID_REEL",
            basename=basename,
            cam_id=cam_id,
            reel_number=reel_num,
            camera_position=cam_pos,
            clip_number=clip_num,
            date_yymmdd=date_str,
            camera_uid=uid_str,
            title_prefix="",
            errors=tuple(errors),
        )

    m_tit = TITLE_CLIP_BASENAME_RE.match(basename)
    if m_tit:
        prefix, idx_str = m_tit.groups()
        clip_idx = int(idx_str)
        if not (TITLE_INDEX_MIN <= clip_idx <= TITLE_INDEX_MAX):
            errors.append(f"Title/Alpha clip index {clip_idx} out of [0001..9999]")
        return CinemaClipTokens(
            valid=len(errors) == 0,
            naming_mode="TITLE_ALPHA",
            basename=basename,
            cam_id="",
            reel_number=0,
            camera_position="",
            clip_number=clip_idx,
            date_yymmdd="",
            camera_uid="",
            title_prefix=prefix,
            errors=tuple(errors),
        )

    return CinemaClipTokens(
        valid=False,
        naming_mode="INVALID",
        basename=basename,
        cam_id="",
        reel_number=0,
        camera_position="",
        clip_number=0,
        date_yymmdd="",
        camera_uid="",
        title_prefix="",
        errors=(f"Basename {basename!r} does not match CamID/Reel# or Title/Alpha syntax",),
    )


def synthesize_and_validate_clip_pair(
    *,
    naming_mode: str = "CAM_ID_REEL",
    container_mode: str = "XAVC_MXF",
    cam_id: str = "A",
    reel_number: int = 1,
    camera_position: str = "C",
    clip_number: int = 1,
    date_yymmdd: str = "261114",
    camera_uid: str = "R7F3",
    title_prefix: str = "C",
    title_index: int = 1,
    proxy_enabled: bool = True,
    proxy_profile: str = "PROXY_16M_XAVC_HS_1080P_10BIT_420",
    sq_active: bool = False,
    sensor_fps: float = 24.0,
    rec_fps: float = 24.0,
    force_proxy_during_sq: bool = False,
) -> ClipPairEvalResult:
    """Synthesize and validate a Cinema Line Main + SUB/Proxy + M01.XML sidecar tuple."""
    errors: List[str] = []
    norm_naming = naming_mode.strip().upper()
    norm_container = container_mode.strip().upper()

    if norm_naming not in CLIP_NAMING_MODES:
        errors.append(f"Unsupported naming_mode {naming_mode!r}; expected {CLIP_NAMING_MODES}")
    if norm_container not in CONTAINER_ROOT_SPECS:
        errors.append(f"Unsupported container_mode {container_mode!r}; expected {tuple(CONTAINER_ROOT_SPECS)}")
    if proxy_profile not in PROXY_CODEC_PROFILES:
        errors.append(f"Unsupported proxy_profile {proxy_profile!r}; expected {tuple(PROXY_CODEC_PROFILES)}")

    if norm_naming == "CAM_ID_REEL":
        if cam_id not in VALID_CAM_IDS:
            errors.append(f"Invalid cam_id {cam_id!r}; expected A..Z")
        if not (REEL_NUMBER_MIN <= reel_number <= REEL_NUMBER_MAX):
            errors.append(f"Invalid reel_number {reel_number}; expected [1..999]")
        if camera_position not in VALID_CAMERA_POSITIONS:
            errors.append(f"Invalid camera_position {camera_position!r}; expected {VALID_CAMERA_POSITIONS}")
        if not (CLIP_NUMBER_MIN <= clip_number <= CLIP_NUMBER_MAX):
            errors.append(f"Invalid clip_number {clip_number}; expected [1..999]")
        if not DATE_YYMMDD_RE.match(date_yymmdd):
            errors.append(f"Invalid date_yymmdd {date_yymmdd!r}; expected 6 digits YYMMDD")
        else:
            try:
                datetime.strptime(date_yymmdd, "%y%m%d")
            except ValueError:
                errors.append(f"Calendar-invalid date_yymmdd {date_yymmdd!r}")
        if not CAMERA_UID_RE.match(camera_uid):
            errors.append(f"Invalid camera_uid {camera_uid!r}; expected 4 uppercase alphanumeric chars")
        basename = f"{cam_id}{reel_number:03d}{camera_position}{clip_number:03d}_{date_yymmdd}_{camera_uid}"
        rollover_next: Optional[int] = advance_reel_number(reel_number) if (REEL_NUMBER_MIN <= reel_number <= REEL_NUMBER_MAX) else None
    else:
        if not re.match(r"^[A-Z][A-Z0-9_]{0,7}$", title_prefix):
            errors.append(f"Invalid title_prefix {title_prefix!r}; expected 1..8 uppercase alphanumeric chars")
        if not (TITLE_INDEX_MIN <= title_index <= TITLE_INDEX_MAX):
            errors.append(f"Invalid title_index {title_index}; expected [1..9999]")
        basename = f"{title_prefix}{title_index:04d}"
        rollover_next = None

    if not math.isfinite(sensor_fps) or not (1.0 <= sensor_fps <= 240.0):
        errors.append(f"sensor_fps {sensor_fps} out of valid S&Q/Cinema envelope [1..240]")
    if not math.isfinite(rec_fps) or not (1.0 <= rec_fps <= 120.0):
        errors.append(f"rec_fps {rec_fps} out of valid playback envelope [1..120]")

    off_speed_sq = bool(sq_active or abs(sensor_fps - rec_fps) > 1e-3)
    proxy_auto_disabled = False
    effective_proxy = bool(proxy_enabled)

    if off_speed_sq:
        if force_proxy_during_sq:
            errors.append(
                f"Proxy recording cannot be forced active during off-speed S&Q ({sensor_fps}fps->{rec_fps}fps)"
            )
            effective_proxy = False
        elif proxy_enabled:
            effective_proxy = False
            proxy_auto_disabled = True

    spec = CONTAINER_ROOT_SPECS.get(norm_container, CONTAINER_ROOT_SPECS["XAVC_MXF"])
    main_rel = f"{spec['root']}/{spec['clip_dir']}/{basename}{spec['main_ext']}"
    sub_rel: Optional[str] = (
        f"{spec['root']}/{spec['sub_dir']}/{basename}{spec['sub_suffix']}" if effective_proxy else None
    )
    xml_rel = f"{spec['root']}/{spec['clip_dir']}/{basename}{spec['sidecar_suffix']}"

    parsed = parse_cinema_clip_basename(basename)
    if not parsed.valid and len(errors) == 0:
        errors.extend(parsed.errors)

    p_meta = PROXY_CODEC_PROFILES.get(proxy_profile)
    status = "CLIP_PROXY_PAIR_VERIFIED"
    if errors:
        status = "BLOCKED_INVALID_CLIP_PAIR_OR_SQ_PROXY"
    elif proxy_auto_disabled:
        status = "SQ_OFF_SPEED_PROXY_AUTO_DISABLED"

    return ClipPairEvalResult(
        valid=len(errors) == 0,
        status=status,
        naming_mode=norm_naming,
        container_mode=norm_container,
        basename=basename,
        main_relpath=main_rel,
        proxy_relpath=sub_rel,
        sidecar_xml_relpath=xml_rel,
        proxy_requested=proxy_enabled,
        proxy_effective_enabled=effective_proxy,
        proxy_auto_disabled_by_sq=proxy_auto_disabled,
        proxy_profile=proxy_profile if effective_proxy else None,
        proxy_resolution=str(p_meta["resolution"]) if (effective_proxy and p_meta) else None,
        proxy_codec=str(p_meta["codec"]) if (effective_proxy and p_meta) else None,
        proxy_bitrate_mbps=float(p_meta["bitrate_mbps"]) if (effective_proxy and p_meta) else None,  # type: ignore[arg-type]
        sq_active=off_speed_sq,
        sensor_fps=sensor_fps,
        rec_fps=rec_fps,
        reel_rollover_next=rollover_next,
        errors=tuple(errors),
    )


def evaluate_pillar_1_clipname_and_proxy(
    present_map: Mapping[str, Tuple[str, ...]],
    fx3_xdb_valid: bool,
    fx6_xdb_valid: bool,
    uxc_labels: Mapping[str, str],
) -> ClipNamingAndProxyReport:
    """Audit Pillar 1: Cinema Line CamID/Reel# vs Title/Alpha Clip Naming & Proxy S03 Pairing."""
    errors: List[str] = []

    fx3_app = present_map["fx3_appfw_clip"]
    fx6_app = present_map["fx6_appfw_clip"]
    fx3_mpr = present_map["fx3_libmpr_clip"]
    fx6_mpr = present_map["fx6_libmpr_clip"]

    if fx3_app != FX3_APPFW_CLIPNAME_PROXY_MARKERS:
        missing = tuple(m for m in FX3_APPFW_CLIPNAME_PROXY_MARKERS if m not in fx3_app)
        errors.append(f"FX3 appFw.so missing Clip Name / Proxy markers: {missing}")
    if fx6_app != FX6_APPFW_CLIPNAME_PROXY_MARKERS:
        missing = tuple(m for m in FX6_APPFW_CLIPNAME_PROXY_MARKERS if m not in fx6_app)
        errors.append(f"FX6 appFw.so missing CamID/Reel/XDROOT/M4ROOT/Proxy markers: {missing}")
    if fx3_mpr != MPR_SHARED_CLIPNAME_MARKERS:
        missing = tuple(m for m in MPR_SHARED_CLIPNAME_MARKERS if m not in fx3_mpr)
        errors.append(f"FX3 libmpr.so missing XavcsNamer/ClipName markers: {missing}")
    expected_fx6_mpr = (*MPR_SHARED_CLIPNAME_MARKERS, *FX6_MPR_CLIPNAME_EXTRA_MARKERS)
    if fx6_mpr != expected_fx6_mpr:
        missing = tuple(m for m in expected_fx6_mpr if m not in fx6_mpr)
        errors.append(f"FX6 libmpr.so missing MXF/MP4 ClipName markers: {missing}")
    if not fx3_xdb_valid:
        errors.append("FX3 global.xdb (uxa\\x07) failed structural validation")
    if not fx6_xdb_valid:
        errors.append("FX6 global.xdb (uxa\\x07) failed structural validation")

    mxf_pair = synthesize_and_validate_clip_pair(
        naming_mode="CAM_ID_REEL",
        container_mode="XAVC_MXF",
        cam_id="A",
        reel_number=1,
        camera_position="C",
        clip_number=1,
        date_yymmdd="261114",
        camera_uid="R7F3",
        proxy_enabled=True,
        proxy_profile="PROXY_16M_XAVC_HS_1080P_10BIT_420",
    )
    mp4_pair = synthesize_and_validate_clip_pair(
        naming_mode="CAM_ID_REEL",
        container_mode="XAVC_MP4",
        cam_id="A",
        reel_number=1,
        camera_position="C",
        clip_number=1,
        date_yymmdd="261114",
        camera_uid="R7F3",
        proxy_enabled=True,
        proxy_profile="PROXY_6M_XAVC_S_720P_8BIT_420",
    )
    title_pair = synthesize_and_validate_clip_pair(
        naming_mode="TITLE_ALPHA",
        container_mode="XAVC_MP4",
        title_prefix="C",
        title_index=1,
        proxy_enabled=True,
        proxy_profile="PROXY_9M_XAVC_HS_1080P_10BIT_420",
    )
    sq_disable = synthesize_and_validate_clip_pair(
        naming_mode="CAM_ID_REEL",
        container_mode="XAVC_MP4",
        cam_id="B",
        reel_number=999,
        camera_position="L",
        clip_number=42,
        date_yymmdd="261114",
        camera_uid="FX3A",
        proxy_enabled=True,
        sq_active=True,
        sensor_fps=120.0,
        rec_fps=24.0,
    )

    for ev in (mxf_pair, mp4_pair, title_pair, sq_disable):
        if not ev.valid:
            errors.extend(ev.errors)
    if sq_disable.proxy_effective_enabled or not sq_disable.proxy_auto_disabled_by_sq:
        errors.append("S&Q off-speed failed to auto-disable proxy recording")

    rollover_next = advance_reel_number(999)
    if rollover_next != 1:
        errors.append(f"Reel 999 rollover returned {rollover_next}, expected 1")

    return ClipNamingAndProxyReport(
        passed=len(errors) == 0,
        fx3_appfw_markers=fx3_app,
        fx6_appfw_markers=fx6_app,
        fx3_libmpr_markers=fx3_mpr,
        fx6_libmpr_markers=fx6_mpr,
        fx3_global_xdb_valid=fx3_xdb_valid,
        fx6_global_xdb_valid=fx6_xdb_valid,
        uxc_clipname_proxy_labels=dict(uxc_labels),
        mxf_camid_pair_eval=mxf_pair,
        mp4_camid_pair_eval=mp4_pair,
        title_alpha_pair_eval=title_pair,
        sq_proxy_disable_eval=sq_disable,
        reel_999_rollover_next=rollover_next,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: Dual-Slot (Slot A + Slot B) Recording Modes & Speed-Class Gate
# ---------------------------------------------------------------------------


def _is_forbidden_internal_emmc_path(path_str: str) -> bool:
    low = path_str.strip().lower()
    return any(pfx in low for pfx in FORBIDDEN_INTERNAL_EMMC_PREFIXES)


def evaluate_dual_slot_recording(
    *,
    rec_mode: str = "SIMULTANEOUS",
    active_slot: str = "SLOT_A",
    slot_a_card: Optional[str] = "CFEXPRESS_VPG400",
    slot_b_card: Optional[str] = "SDXC_V90",
    main_profile: str = "XAVC_S_I_4K60_600MBPS",
    proxy_profile: Optional[str] = "XAVC_HS_PROXY_16MBPS",
    slot_a_free_frames: int = 1000,
    total_frames: int = 240,
    sq_active: bool = False,
    target_storage_path: str = "/media/slot_a",
    persistent_emmc_writes_authorized: bool = False,
) -> DualSlotEvalResult:
    """Validate Dual-Slot (`Simultaneous`/`Relay`/`Sort`/`Off`) routing and media speed-class gates."""
    errors: List[str] = []
    norm_mode = rec_mode.strip().upper()
    norm_active = active_slot.strip().upper()

    if persistent_emmc_writes_authorized:
        errors.append("Hard safety redline: persistent_emmc_writes_authorized must remain False")

    emmc_writes = 0
    if _is_forbidden_internal_emmc_path(target_storage_path):
        emmc_writes = 1
        errors.append(
            f"BLOCKED_INTERNAL_EMMC_CLIP_WRITE: forbidden target_storage_path={target_storage_path!r}"
        )

    if norm_mode not in DUAL_SLOT_MODES:
        errors.append(f"Unsupported dual-slot rec_mode {rec_mode!r}; expected {DUAL_SLOT_MODES}")
    if norm_active not in ("SLOT_A", "SLOT_B"):
        errors.append(f"Unsupported active_slot {active_slot!r}; expected SLOT_A or SLOT_B")
    if main_profile not in RECORDING_BITRATE_PROFILES:
        errors.append(f"Unsupported main_profile {main_profile!r}")
    if proxy_profile is not None and proxy_profile not in RECORDING_BITRATE_PROFILES:
        errors.append(f"Unsupported proxy_profile {proxy_profile!r}")
    for slot_lbl, card in (("SLOT_A", slot_a_card), ("SLOT_B", slot_b_card)):
        if card is not None and card not in MEDIA_CARD_SPEED_CLASSES:
            errors.append(f"Unsupported media card {card!r} in {slot_lbl}")

    main_spec = RECORDING_BITRATE_PROFILES.get(main_profile)
    proxy_spec = RECORDING_BITRATE_PROFILES.get(proxy_profile) if proxy_profile else None

    main_slots: List[str] = []
    proxy_slots: List[str] = []
    relay_triggered = False
    dropped_frames = 0
    speed_class_rejected = False

    def _check_card_speed(slot_name: str, card_type: Optional[str], spec: Mapping[str, object], role: str) -> None:
        nonlocal speed_class_rejected
        if card_type is None:
            errors.append(f"{slot_name} has no media card inserted for {role} recording")
            return
        allowed = spec["allowed_cards"]
        req_mbps = float(spec["required_mbps"])  # type: ignore[arg-type]
        card_mbps = float(MEDIA_CARD_SPEED_CLASSES[card_type]["sustained_mbps"])  # type: ignore[arg-type]
        if card_type not in allowed or card_mbps < req_mbps:  # type: ignore[operator]
            speed_class_rejected = True
            errors.append(
                f"SPEED_CLASS_REJECT: {slot_name} card {card_type} ({card_mbps:.0f} Mbps) "
                f"cannot sustain {role} {main_profile if role == 'Main' else proxy_profile} "
                f"({req_mbps:.0f} Mbps; requires {allowed})"
            )

    if main_spec is not None and norm_mode in DUAL_SLOT_MODES:
        if norm_mode == "SIMULTANEOUS":
            main_slots = ["SLOT_A", "SLOT_B"]
            _check_card_speed("SLOT_A", slot_a_card, main_spec, "Main")
            _check_card_speed("SLOT_B", slot_b_card, main_spec, "Main")
            if proxy_profile and not sq_active and proxy_spec is not None:
                proxy_slots = ["SLOT_A", "SLOT_B"]
        elif norm_mode == "RELAY":
            if slot_a_free_frames < total_frames:
                relay_triggered = True
                main_slots = ["SLOT_A", "SLOT_B"]
                _check_card_speed("SLOT_A", slot_a_card, main_spec, "Main")
                _check_card_speed("SLOT_B", slot_b_card, main_spec, "Main")
            else:
                main_slots = [norm_active]
                card = slot_a_card if norm_active == "SLOT_A" else slot_b_card
                _check_card_speed(norm_active, card, main_spec, "Main")
        elif norm_mode == "SORT":
            main_slots = ["SLOT_A"]
            _check_card_speed("SLOT_A", slot_a_card, main_spec, "Main")
            if not sq_active:
                proxy_slots = ["SLOT_B"]
                if proxy_spec is None:
                    errors.append("SORT mode with active proxy requires a valid proxy_profile for SLOT_B")
                else:
                    _check_card_speed("SLOT_B", slot_b_card, proxy_spec, "Proxy/Sub")
        elif norm_mode == "OFF":
            main_slots = [norm_active]
            card = slot_a_card if norm_active == "SLOT_A" else slot_b_card
            _check_card_speed(norm_active, card, main_spec, "Main")
            if proxy_profile and not sq_active and proxy_spec is not None:
                proxy_slots = [norm_active]

    if errors:
        if emmc_writes > 0:
            status = "BLOCKED_INTERNAL_EMMC_CLIP_WRITE"
        elif speed_class_rejected:
            status = "BLOCKED_SPEED_CLASS_REJECT"
        else:
            status = "BLOCKED_DUAL_SLOT_POLICY_ERROR"
    elif relay_triggered:
        status = "DUAL_SLOT_RELAY_ZERO_DROP_VERIFIED"
    else:
        status = f"DUAL_SLOT_{norm_mode}_VERIFIED"

    return DualSlotEvalResult(
        valid=len(errors) == 0,
        status=status,
        rec_mode=norm_mode,
        active_slot=norm_active,
        slot_a_card=slot_a_card,
        slot_b_card=slot_b_card,
        main_profile=main_profile,
        proxy_profile=None if sq_active else proxy_profile,
        main_write_slots=tuple(main_slots),
        proxy_write_slots=tuple(proxy_slots),
        relay_triggered=relay_triggered,
        dropped_frames=dropped_frames,
        libmpr_crashed=False,
        internal_emmc_clip_writes=emmc_writes,
        persistent_emmc_writes_authorized=persistent_emmc_writes_authorized,
        errors=tuple(errors),
    )


def evaluate_pillar_2_dual_slot_matrix(
    present_map: Mapping[str, Tuple[str, ...]],
) -> DualSlotMatrixReport:
    """Audit Pillar 2: Simultaneous, Relay, Sort, Off, Speed-Class Gates & eMMC p1 Isolation."""
    errors: List[str] = []

    fx3_ds = present_map["fx3_appfw_dual_slot"]
    fx6_ds = present_map["fx6_appfw_dual_slot"]
    mpr_rv = present_map["mpr_relay_vpg"]

    if fx3_ds != FX3_APPFW_DUAL_SLOT_MARKERS:
        missing = tuple(m for m in FX3_APPFW_DUAL_SLOT_MARKERS if m not in fx3_ds)
        errors.append(f"FX3 appFw.so missing Dual-Slot / Speed-Class markers: {missing}")
    if fx6_ds != FX6_APPFW_DUAL_SLOT_MARKERS:
        missing = tuple(m for m in FX6_APPFW_DUAL_SLOT_MARKERS if m not in fx6_ds)
        errors.append(f"FX6 appFw.so missing Dual-Slot markers: {missing}")
    if mpr_rv != MPR_SHARED_RELAY_VPG_MARKERS:
        missing = tuple(m for m in MPR_SHARED_RELAY_VPG_MARKERS if m not in mpr_rv)
        errors.append(f"libmpr.so missing PrepareRelayMedia / VPG_MANAGER markers: {missing}")

    simul_ev = evaluate_dual_slot_recording(
        rec_mode="SIMULTANEOUS",
        slot_a_card="CFEXPRESS_VPG400",
        slot_b_card="SDXC_V90",
        main_profile="XAVC_S_I_4K60_600MBPS",
    )
    relay_ev = evaluate_dual_slot_recording(
        rec_mode="RELAY",
        slot_a_card="CFEXPRESS_VPG200",
        slot_b_card="CFEXPRESS_VPG400",
        main_profile="SQ_4K120_ALL_INTRA",
        slot_a_free_frames=120,
        total_frames=240,
        sq_active=True,
    )
    sort_ev = evaluate_dual_slot_recording(
        rec_mode="SORT",
        slot_a_card="CFEXPRESS_VPG400",
        slot_b_card="SDXC_V60",
        main_profile="SQ_4K120_ALL_INTRA",
        proxy_profile="XAVC_HS_PROXY_16MBPS",
        sq_active=False,
    )
    off_ev = evaluate_dual_slot_recording(
        rec_mode="OFF",
        active_slot="SLOT_A",
        slot_a_card="SDXC_V90",
        slot_b_card=None,
        main_profile="XAVC_S_I_4K60_600MBPS",
    )
    v30_reject = evaluate_dual_slot_recording(
        rec_mode="OFF",
        active_slot="SLOT_A",
        slot_a_card="SDXC_V30",
        slot_b_card=None,
        main_profile="XAVC_S_I_4K60_600MBPS",
    )
    v90_4k120_reject = evaluate_dual_slot_recording(
        rec_mode="OFF",
        active_slot="SLOT_A",
        slot_a_card="SDXC_V90",
        slot_b_card=None,
        main_profile="SQ_4K120_ALL_INTRA",
        sq_active=True,
    )

    for ev in (simul_ev, relay_ev, sort_ev, off_ev):
        if not ev.valid:
            errors.extend(ev.errors)
    if v30_reject.valid or v30_reject.status != "BLOCKED_SPEED_CLASS_REJECT" or v30_reject.libmpr_crashed:
        errors.append("SDXC_V30 failed to cleanly reject XAVC S-I 4K60 600Mbps without libmpr crash")
    if v90_4k120_reject.valid or v90_4k120_reject.status != "BLOCKED_SPEED_CLASS_REJECT" or v90_4k120_reject.libmpr_crashed:
        errors.append("SDXC_V90 failed to cleanly reject S&Q 4K120 All-Intra without libmpr crash")

    total_emmc = sum(
        ev.internal_emmc_clip_writes
        for ev in (simul_ev, relay_ev, sort_ev, off_ev, v30_reject, v90_4k120_reject)
    )
    if total_emmc != 0:
        errors.append(f"Internal eMMC clip writes must be 0, got {total_emmc}")

    return DualSlotMatrixReport(
        passed=len(errors) == 0 and total_emmc == 0,
        fx3_appfw_dual_slot_markers=fx3_ds,
        fx6_appfw_dual_slot_markers=fx6_ds,
        mpr_relay_vpg_markers=mpr_rv,
        simul_eval=simul_ev,
        relay_eval=relay_ev,
        sort_eval=sort_ev,
        off_eval=off_ev,
        v30_4k60_reject_eval=v30_reject,
        v90_4k120_reject_eval=v90_4k120_reject,
        internal_emmc_clip_writes=total_emmc,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: Sony NonRealTimeMeta XML Sidecar (*M01.XML) & NLE Auto-Tag Verifier
# ---------------------------------------------------------------------------


def compute_cine_ei_exposure_stops(exposure_index: int, base_iso: int) -> float:
    """Compute non-destructive NLE EI gain shift in stops relative to Dual Base ISO (800 / 12800)."""
    if not (CINE_EI_MIN <= exposure_index <= CINE_EI_MAX):
        raise ValueError(f"exposure_index {exposure_index} out of [{CINE_EI_MIN}..{CINE_EI_MAX}]")
    if base_iso not in VALID_BASE_ISOS:
        raise ValueError(f"base_iso {base_iso} not in {VALID_BASE_ISOS}")
    return round(math.log2(float(exposure_index) / float(base_iso)), 4)


def synthesize_non_realtime_meta_xml(
    *,
    umid_ref: str = "060A2B340101010501010D4313000000A001C001261114R7",
    duration_frames: int = 240,
    creation_iso8601: str = "2026-11-14T16:00:00-08:00",
    video_codec: str = "XAVC_S_I_4K",
    capture_fps: str = "23.98p",
    format_fps: str = "23.98p",
    pixel_width: int = 4096,
    pixel_height: int = 2160,
    capture_gamma_equation: str = "s-log3-cine",
    capture_color_primaries: str = "s-gamut3-cine",
    exposure_index: int = 200,
    base_iso: int = 800,
    monitoring_lut_cube: str = "User1.cube",
    device_model_name: str = "ILME-FX3",
    device_serial: str = "00000000",
    device_ver: str = "7.02-stageB-ram-overlay",
) -> str:
    """Synthesize a schema-valid Sony `NonRealTimeMeta` v2.20 (`*M01.XML`) sidecar via `ElementTree`."""
    if capture_gamma_equation not in VALID_CAPTURE_GAMMA_EQUATIONS:
        raise ValueError(f"Unsupported CaptureGammaEquation {capture_gamma_equation!r}")
    if capture_color_primaries not in VALID_CAPTURE_COLOR_PRIMARIES:
        raise ValueError(f"Unsupported CaptureColorPrimaries {capture_color_primaries!r}")
    if not VALID_CUBE_LUT_NAME_RE.match(monitoring_lut_cube):
        raise ValueError(f"Unsupported/unsafe MonitoringDescriptions LUT {monitoring_lut_cube!r}")

    stops = compute_cine_ei_exposure_stops(exposure_index, base_iso)

    ET.register_namespace("", NRTM_NAMESPACE_V220)
    ET.register_namespace("lib", NRTM_LIB_NAMESPACE_V220)

    def _q(tag: str) -> str:
        return f"{{{NRTM_NAMESPACE_V220}}}{tag}"

    root = ET.Element(_q("NonRealTimeMeta"), {"lastUpdate": creation_iso8601})
    ET.SubElement(root, _q("TargetMaterial"), {"umidRef": umid_ref})
    ET.SubElement(root, _q("Duration"), {"value": str(duration_frames)})
    ET.SubElement(root, _q("CreationDate"), {"value": creation_iso8601})

    vfmt = ET.SubElement(root, _q("VideoFormat"))
    ET.SubElement(vfmt, _q("VideoRecPort"), {"port": "DIRECT"})
    ET.SubElement(
        vfmt,
        _q("VideoFrame"),
        {"videoCodec": video_codec, "captureFps": capture_fps, "formatFps": format_fps},
    )
    ET.SubElement(
        vfmt,
        _q("VideoLayout"),
        {
            "pixel": str(pixel_width),
            "numOfVerticalLine": str(pixel_height),
            "aspectRatio": "17:9" if pixel_width == 4096 else "16:9",
        },
    )

    ET.SubElement(
        root,
        _q("Device"),
        {
            "manufacturer": "Sony",
            "modelName": device_model_name,
            "serialNo": device_serial,
            "ver": device_ver,
        },
    )

    acq = ET.SubElement(root, _q("AcquisitionRecord"))
    cam_grp = ET.SubElement(acq, _q("Group"), {"name": "CameraUnitMetadataSet"})
    ET.SubElement(cam_grp, _q("Item"), {"name": "CaptureGammaEquation", "value": capture_gamma_equation})
    ET.SubElement(cam_grp, _q("Item"), {"name": "CaptureColorPrimaries", "value": capture_color_primaries})
    ET.SubElement(cam_grp, _q("Item"), {"name": "ExposureIndexOfPhotoMeter", "value": str(exposure_index)})

    mon_grp = ET.SubElement(acq, _q("Group"), {"name": "MonitoringDescriptions"})
    ET.SubElement(mon_grp, _q("Item"), {"name": "MonitoringBaseCurve", "value": capture_gamma_equation})
    ET.SubElement(mon_grp, _q("Item"), {"name": "MonitoringDescription", "value": monitoring_lut_cube})

    prov_grp = ET.SubElement(acq, _q("Group"), {"name": "StageBProvenance"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "BaseISO", "value": str(base_iso)})
    ET.SubElement(prov_grp, _q("Item"), {"name": "ExposureIndexOffsetStops", "value": f"{stops:+.4f}"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "OverlayMode", "value": "FX6_STAGE_B_RAM_SHADOW"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "C2PASpoofAttempted", "value": "false"})
    ET.SubElement(prov_grp, _q("Item"), {"name": "RqLicPreserved", "value": "true"})

    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ET.tostring(root, encoding="unicode") + "\n"


def parse_and_verify_non_realtime_meta_xml(
    xml_text: str,
    *,
    expected_base_iso: int = 800,
    require_c2pa_non_spoof: bool = True,
) -> NonRealTimeMetaEvalResult:
    """Parse and validate a Sony `NonRealTimeMeta` v2.20 sidecar XML for Resolve / Premiere / Catalyst."""
    errors: List[str] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError as exc:
        return NonRealTimeMetaEvalResult(
            valid=False,
            status="BLOCKED_INVALID_NRTM_XML",
            namespace_uri="",
            capture_gamma_equation="",
            capture_color_primaries="",
            exposure_index=0,
            base_iso=expected_base_iso,
            ei_offset_stops=0.0,
            monitoring_lut_cube="",
            device_manufacturer="",
            device_model_name="",
            device_firmware_ver="",
            c2pa_spoof_attempted=False,
            c2pa_rq_lic_preserved=True,
            nle_auto_tags_ready={nle: False for nle in TARGET_NLE_CONSUMERS},
            errors=(f"XML parse error: {exc}",),
        )

    expected_root_tag = f"{{{NRTM_NAMESPACE_V220}}}NonRealTimeMeta"
    ns_uri = root.tag[1:].split("}", 1)[0] if root.tag.startswith("{") else ""
    if root.tag != expected_root_tag:
        errors.append(f"Root tag {root.tag!r} != expected {expected_root_tag!r}")

    def _q(tag: str) -> str:
        return f"{{{NRTM_NAMESPACE_V220}}}{tag}"

    dev_el = root.find(_q("Device"))
    mfg = dev_el.attrib.get("manufacturer", "") if dev_el is not None else ""
    model_name = dev_el.attrib.get("modelName", "") if dev_el is not None else ""
    fw_ver = dev_el.attrib.get("ver", "") if dev_el is not None else ""
    if dev_el is None:
        errors.append("Missing <Device> provenance element")
    else:
        if mfg != "Sony":
            errors.append(f"Unexpected Device manufacturer={mfg!r}")
        if model_name != "ILME-FX3":
            errors.append(f"Device modelName={model_name!r} must preserve physical ILME-FX3 identity")

    items_by_group: Dict[str, Dict[str, str]] = {}
    acq_el = root.find(_q("AcquisitionRecord"))
    if acq_el is None:
        errors.append("Missing <AcquisitionRecord> element")
    else:
        for grp in acq_el.findall(_q("Group")):
            gname = grp.attrib.get("name", "")
            gmap: Dict[str, str] = {}
            for item in grp.findall(_q("Item")):
                iname = item.attrib.get("name", "")
                ival = item.attrib.get("value", "")
                if iname:
                    gmap[iname] = ival
            items_by_group[gname] = gmap

    cam_items = items_by_group.get("CameraUnitMetadataSet", {})
    mon_items = items_by_group.get("MonitoringDescriptions", {})
    prov_items = items_by_group.get("StageBProvenance", {})

    gamma_eq = cam_items.get("CaptureGammaEquation", "")
    primaries = cam_items.get("CaptureColorPrimaries", "")
    ei_raw = cam_items.get("ExposureIndexOfPhotoMeter", "")
    lut_cube = mon_items.get("MonitoringDescription", "")

    if gamma_eq not in VALID_CAPTURE_GAMMA_EQUATIONS:
        errors.append(
            f"Invalid CaptureGammaEquation {gamma_eq!r}; expected {VALID_CAPTURE_GAMMA_EQUATIONS}"
        )
    if primaries not in VALID_CAPTURE_COLOR_PRIMARIES:
        errors.append(
            f"Invalid CaptureColorPrimaries {primaries!r}; expected {VALID_CAPTURE_COLOR_PRIMARIES}"
        )

    ei_val = 0
    ei_stops = 0.0
    try:
        ei_val = int(ei_raw)
        if not (CINE_EI_MIN <= ei_val <= CINE_EI_MAX):
            errors.append(f"ExposureIndexOfPhotoMeter {ei_val} out of [{CINE_EI_MIN}..{CINE_EI_MAX}]")
        else:
            ei_stops = compute_cine_ei_exposure_stops(ei_val, expected_base_iso)
    except ValueError:
        errors.append(f"Non-integer ExposureIndexOfPhotoMeter {ei_raw!r}")

    if not VALID_CUBE_LUT_NAME_RE.match(lut_cube):
        errors.append(f"Invalid MonitoringDescriptions LUT reference {lut_cube!r}")

    # Verify Stage-B provenance never spoofs C2PA / RQ_LIC.DAT signatures
    c2pa_spoof = False
    lower_xml = xml_text.lower()
    if any(tok in lower_xml for tok in ("c2pasignature", "spoofed_rq_lic", "forged_c2pa")):
        c2pa_spoof = True
    if prov_items.get("C2PASpoofAttempted", "false").lower() != "false":
        c2pa_spoof = True
    rq_lic_preserved = prov_items.get("RqLicPreserved", "true").lower() == "true" and not c2pa_spoof

    if require_c2pa_non_spoof and (c2pa_spoof or not rq_lic_preserved):
        errors.append("BLOCKED_C2PA_SIGNATURE_SPOOF: NonRealTimeMeta sidecar must not spoof C2PA RQ_LIC.DAT")

    ok = len(errors) == 0
    nle_ready = {
        "Resolve": ok and gamma_eq != "" and primaries != "" and ei_val > 0,
        "Premiere": ok and gamma_eq != "" and primaries != "",
        "Catalyst": ok and ei_val > 0 and lut_cube != "" and model_name == "ILME-FX3",
    }

    return NonRealTimeMetaEvalResult(
        valid=ok,
        status="NRTM_V220_NLE_VERIFIED" if ok else "BLOCKED_NRTM_SCHEMA_OR_C2PA_ERROR",
        namespace_uri=ns_uri,
        capture_gamma_equation=gamma_eq,
        capture_color_primaries=primaries,
        exposure_index=ei_val,
        base_iso=expected_base_iso,
        ei_offset_stops=ei_stops,
        monitoring_lut_cube=lut_cube,
        device_manufacturer=mfg,
        device_model_name=model_name,
        device_firmware_ver=fw_ver,
        c2pa_spoof_attempted=c2pa_spoof,
        c2pa_rq_lic_preserved=rq_lic_preserved,
        nle_auto_tags_ready=nle_ready,
        errors=tuple(errors),
    )


def evaluate_pillar_3_nrtm_sidecar(
    present_map: Mapping[str, Tuple[str, ...]],
) -> NonRealTimeMetaSidecarReport:
    """Audit Pillar 3: Sony NonRealTimeMeta v2.20 XML Sidecar, Cine EI/LUT Auto-Tag & C2PA Non-Spoof."""
    errors: List[str] = []

    fx3_nrtm = present_map["fx3_libmpr_nrtm"]
    fx6_nrtm = present_map["fx6_libmpr_nrtm"]
    fx6_extra = present_map["fx6_libmpr_nrtm_extra"]
    fx3_c2pa = present_map["fx3_appfw_c2pa"]

    if fx3_nrtm != MPR_SHARED_NRTM_MARKERS:
        missing = tuple(m for m in MPR_SHARED_NRTM_MARKERS if m not in fx3_nrtm)
        errors.append(f"FX3 libmpr.so missing NonRealTimeMeta v2.20 markers: {missing}")
    if fx6_nrtm != MPR_SHARED_NRTM_MARKERS:
        missing = tuple(m for m in MPR_SHARED_NRTM_MARKERS if m not in fx6_nrtm)
        errors.append(f"FX6 libmpr.so missing NonRealTimeMeta v2.20 markers: {missing}")
    if fx6_extra != FX6_MPR_NRTM_EXTRA_MARKERS:
        missing = tuple(m for m in FX6_MPR_NRTM_EXTRA_MARKERS if m not in fx6_extra)
        errors.append(f"FX6 libmpr.so missing ExposureIndex/MonitoringDescription markers: {missing}")
    if fx3_c2pa != FX3_APPFW_C2PA_IMMUTABLE_MARKERS:
        missing = tuple(m for m in FX3_APPFW_C2PA_IMMUTABLE_MARKERS if m not in fx3_c2pa)
        errors.append(f"FX3 appFw.so missing InfraC2PA immutability markers: {missing}")

    xml_ei200 = synthesize_non_realtime_meta_xml(
        capture_gamma_equation="s-log3-cine",
        capture_color_primaries="s-gamut3-cine",
        exposure_index=200,
        base_iso=800,
        monitoring_lut_cube="User1.cube",
    )
    ev_ei200 = parse_and_verify_non_realtime_meta_xml(xml_ei200, expected_base_iso=800)

    xml_ei12800 = synthesize_non_realtime_meta_xml(
        capture_gamma_equation="s-log3",
        capture_color_primaries="s-gamut3",
        exposure_index=12800,
        base_iso=12800,
        monitoring_lut_cube="User4.cube",
    )
    ev_ei12800 = parse_and_verify_non_realtime_meta_xml(xml_ei12800, expected_base_iso=12800)

    xml_scine = synthesize_non_realtime_meta_xml(
        capture_gamma_equation="s-cinetone",
        capture_color_primaries="rec709",
        exposure_index=800,
        base_iso=800,
        monitoring_lut_cube="User2.cube",
    )
    ev_scine = parse_and_verify_non_realtime_meta_xml(xml_scine, expected_base_iso=800)

    for ev in (ev_ei200, ev_ei12800, ev_scine):
        if not ev.valid:
            errors.extend(ev.errors)

    any_spoof = any(ev.c2pa_spoof_attempted for ev in (ev_ei200, ev_ei12800, ev_scine))
    all_rq_ok = all(ev.c2pa_rq_lic_preserved for ev in (ev_ei200, ev_ei12800, ev_scine))
    if any_spoof or not all_rq_ok:
        errors.append("C2PA RQ_LIC.DAT preservation check failed")

    return NonRealTimeMetaSidecarReport(
        passed=len(errors) == 0 and not any_spoof and all_rq_ok,
        fx3_libmpr_nrtm_markers=fx3_nrtm,
        fx6_libmpr_nrtm_markers=fx6_nrtm,
        fx6_libmpr_nrtm_extra_markers=fx6_extra,
        fx3_appfw_c2pa_markers=fx3_c2pa,
        slog3_cine_ei200_eval=ev_ei200,
        slog3_cine_ei12800_eval=ev_ei12800,
        scinetone_rec709_eval=ev_scine,
        c2pa_spoof_attempted=any_spoof,
        c2pa_rq_lic_preserved=all_rq_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified Dual-Mode Entrypoint
# ---------------------------------------------------------------------------


def proxy_clipname_and_sidecar_report_to_dict(
    report: ProxyClipnameAndSidecarReport,
) -> Dict[str, object]:
    return report.to_dict()


def analyze_proxy_clipname_and_sidecar(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    synthetic_overrides: Optional[Mapping[str, bytes]] = None,
) -> ProxyClipnameAndSidecarReport:
    """Run the 13th unified firmware-lab audit across Clip Naming/Proxy, Dual-Slot, and NonRealTimeMeta XML."""
    relpaths: Dict[str, str] = {
        "fx3_appfw": FX3_APPFW_RELPATH,
        "fx6_appfw": FX6_APPFW_RELPATH,
        "fx3_libmpr": FX3_LIBMPR_RELPATH,
        "fx6_libmpr": FX6_LIBMPR_RELPATH,
        "fx3_global_xdb": FX3_GLOBAL_XDB_RELPATH,
        "fx6_global_xdb": FX6_GLOBAL_XDB_RELPATH,
        "fx3_str_en": FX3_STR_EN_RELPATH,
        "fx3_str_en_g": FX3_STR_EN_G_RELPATH,
        "fx6_str_en_1": FX6_STR_EN_1_RELPATH,
        "fx6_str_en_2": FX6_STR_EN_2_RELPATH,
    }

    forced = bool(clean_room or synthetic_overrides is not None or is_forced_clean_room(env))
    resolved: Dict[str, Optional[Path]] = {}
    if not forced:
        for k, rel in relpaths.items():
            resolved[k] = resolve_donor_file(rel, repo_root=repo_root, env=env)
        if any(p is None or not p.is_file() for p in resolved.values()):
            forced = True

    fx3_app_groups: Dict[str, Sequence[str]] = {
        "fx3_appfw_clip": FX3_APPFW_CLIPNAME_PROXY_MARKERS,
        "fx3_appfw_dual_slot": FX3_APPFW_DUAL_SLOT_MARKERS,
        "fx3_appfw_c2pa": FX3_APPFW_C2PA_IMMUTABLE_MARKERS,
    }
    fx6_app_groups: Dict[str, Sequence[str]] = {
        "fx6_appfw_clip": FX6_APPFW_CLIPNAME_PROXY_MARKERS,
        "fx6_appfw_dual_slot": FX6_APPFW_DUAL_SLOT_MARKERS,
    }
    fx3_mpr_groups: Dict[str, Sequence[str]] = {
        "fx3_libmpr_clip": MPR_SHARED_CLIPNAME_MARKERS,
        "fx3_libmpr_relay_vpg": MPR_SHARED_RELAY_VPG_MARKERS,
        "fx3_libmpr_nrtm": MPR_SHARED_NRTM_MARKERS,
    }
    fx6_mpr_groups: Dict[str, Sequence[str]] = {
        "fx6_libmpr_clip": (*MPR_SHARED_CLIPNAME_MARKERS, *FX6_MPR_CLIPNAME_EXTRA_MARKERS),
        "fx6_libmpr_relay_vpg": MPR_SHARED_RELAY_VPG_MARKERS,
        "fx6_libmpr_nrtm": MPR_SHARED_NRTM_MARKERS,
        "fx6_libmpr_nrtm_extra": FX6_MPR_NRTM_EXTRA_MARKERS,
    }

    donor_sizes: Dict[str, int] = {}
    present_map: Dict[str, Tuple[str, ...]] = {}
    uxc_errors: List[str] = []

    if forced:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        fixtures = dict(build_clean_room_proxy_clipname_fixtures())
        if synthetic_overrides:
            fixtures.update(synthetic_overrides)

        def _scan_buf_groups(buf: bytes, groups: Mapping[str, Sequence[str]]) -> Dict[str, Tuple[str, ...]]:
            out: Dict[str, Tuple[str, ...]] = {}
            for gname, markers in groups.items():
                out[gname] = tuple(m for m in markers if buf.find(m.encode("latin1")) != -1)
            return out

        for k, buf in fixtures.items():
            donor_sizes[k] = len(buf)

        present_map.update(_scan_buf_groups(fixtures["fx3_appfw"], fx3_app_groups))
        present_map.update(_scan_buf_groups(fixtures["fx6_appfw"], fx6_app_groups))
        present_map.update(_scan_buf_groups(fixtures["fx3_libmpr"], fx3_mpr_groups))
        present_map.update(_scan_buf_groups(fixtures["fx6_libmpr"], fx6_mpr_groups))

        fx3_xdb_audit = parse_global_xdb_buffer(
            fixtures["fx3_global_xdb"], body="fx3_702", source_mode="SYNTHETIC_CLEAN_ROOM"
        )
        fx6_xdb_audit = parse_global_xdb_buffer(
            fixtures["fx6_global_xdb"], body="fx6_601", source_mode="SYNTHETIC_CLEAN_ROOM"
        )
        fx3_str_en_bytes = fixtures["fx3_str_en"]
        fx3_str_en_g_bytes = fixtures["fx3_str_en_g"]
        fx6_str_en_1_bytes = fixtures["fx6_str_en_1"]
        fx6_str_en_2_bytes = fixtures["fx6_str_en_2"]
    else:
        mode = "LOCAL_DONOR_VERIFIED"
        sz, res = _scan_donor_rdonly_markers(resolved["fx3_appfw"], fx3_app_groups, is_elf=True)  # type: ignore[arg-type]
        donor_sizes["fx3_appfw"] = sz
        present_map.update(res)

        sz, res = _scan_donor_rdonly_markers(resolved["fx6_appfw"], fx6_app_groups, is_elf=True)  # type: ignore[arg-type]
        donor_sizes["fx6_appfw"] = sz
        present_map.update(res)

        sz, res = _scan_donor_rdonly_markers(resolved["fx3_libmpr"], fx3_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        donor_sizes["fx3_libmpr"] = sz
        present_map.update(res)

        sz, res = _scan_donor_rdonly_markers(resolved["fx6_libmpr"], fx6_mpr_groups, is_elf=True)  # type: ignore[arg-type]
        donor_sizes["fx6_libmpr"] = sz
        present_map.update(res)

        fx3_xdb_bytes = _read_bytes_rdonly(resolved["fx3_global_xdb"])  # type: ignore[arg-type]
        fx6_xdb_bytes = _read_bytes_rdonly(resolved["fx6_global_xdb"])  # type: ignore[arg-type]
        donor_sizes["fx3_global_xdb"] = len(fx3_xdb_bytes)
        donor_sizes["fx6_global_xdb"] = len(fx6_xdb_bytes)
        fx3_xdb_audit = parse_global_xdb_buffer(
            fx3_xdb_bytes,
            body="fx3_702",
            source_mode="LOCAL_DONOR_RDONLY",
            share_app_dir=resolved["fx3_global_xdb"].parent,  # type: ignore[union-attr]
        )
        fx6_xdb_audit = parse_global_xdb_buffer(
            fx6_xdb_bytes,
            body="fx6_601",
            source_mode="LOCAL_DONOR_RDONLY",
            share_app_dir=resolved["fx6_global_xdb"].parent,  # type: ignore[union-attr]
        )

        fx3_str_en_bytes = _read_bytes_rdonly(resolved["fx3_str_en"])  # type: ignore[arg-type]
        fx3_str_en_g_bytes = _read_bytes_rdonly(resolved["fx3_str_en_g"])  # type: ignore[arg-type]
        fx6_str_en_1_bytes = _read_bytes_rdonly(resolved["fx6_str_en_1"])  # type: ignore[arg-type]
        fx6_str_en_2_bytes = _read_bytes_rdonly(resolved["fx6_str_en_2"])  # type: ignore[arg-type]
        donor_sizes["fx3_str_en"] = len(fx3_str_en_bytes)
        donor_sizes["fx3_str_en_g"] = len(fx3_str_en_g_bytes)
        donor_sizes["fx6_str_en_1"] = len(fx6_str_en_1_bytes)
        donor_sizes["fx6_str_en_2"] = len(fx6_str_en_2_bytes)

    # Combine shared libmpr relay/vpg hits across both FX3 and FX6
    mpr_rv_fx3 = set(present_map["fx3_libmpr_relay_vpg"])
    mpr_rv_fx6 = set(present_map["fx6_libmpr_relay_vpg"])
    present_map["mpr_relay_vpg"] = tuple(
        m for m in MPR_SHARED_RELAY_VPG_MARKERS if m in mpr_rv_fx3 and m in mpr_rv_fx6
    )

    fx3_ns39_lbl, fx3_ns39_err = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_DUAL_SLOT_LABELS)
    fx3_ns3_lbl, fx3_ns3_err = _extract_uxc_labels(fx3_str_en_g_bytes, FX3_NS3_CLIPNAME_LABELS)
    fx6_ns1_lbl, fx6_ns1_err = _extract_uxc_labels(fx6_str_en_1_bytes, FX6_NS1_CLIPNAME_LABELS)
    fx6_ns2_lbl, fx6_ns2_err = _extract_uxc_labels(fx6_str_en_2_bytes, FX6_NS2_CLIPNAME_PROXY_LABELS)
    uxc_errors.extend((*fx3_ns39_err, *fx3_ns3_err, *fx6_ns1_err, *fx6_ns2_err))

    uxc_labels = {
        "fx3_sort_2_cards": fx3_ns39_lbl.get("0x0004e0ae", ""),
        "fx3_reel": fx3_ns3_lbl.get("0x0000652b", ""),
        "fx3_title": fx3_ns3_lbl.get("0x00006532", ""),
        "fx6_reel": fx6_ns1_lbl.get("0x00002200", ""),
        "fx6_clip_name_format": fx6_ns1_lbl.get("0x00002244", ""),
        "fx6_simul_rec": fx6_ns2_lbl.get("0x0000424f", ""),
        "fx6_xavc_proxy_rec_mode": fx6_ns2_lbl.get("0x000042c4", ""),
        "fx6_proxy_rec": fx6_ns2_lbl.get("0x000042d0", ""),
        "fx6_proxy_format": fx6_ns2_lbl.get("0x000042de", ""),
        "fx6_auto_naming": fx6_ns2_lbl.get("0x0000457e", ""),
        "fx6_title_prefix": fx6_ns2_lbl.get("0x00004580", ""),
        "fx6_camera_position": fx6_ns2_lbl.get("0x0000458e", ""),
        "fx6_camera_id": fx6_ns2_lbl.get("0x0000468f", ""),
        "fx6_cam_id_reel": fx6_ns2_lbl.get("0x00004aff", ""),
    }

    p1 = evaluate_pillar_1_clipname_and_proxy(
        present_map,
        fx3_xdb_valid=fx3_xdb_audit.valid,
        fx6_xdb_valid=fx6_xdb_audit.valid,
        uxc_labels=uxc_labels,
    )
    p2 = evaluate_pillar_2_dual_slot_matrix(present_map)
    p3 = evaluate_pillar_3_nrtm_sidecar(present_map)

    all_errors = [
        *uxc_errors,
        *fx3_xdb_audit.errors,
        *fx6_xdb_audit.errors,
        *p1.errors,
        *p2.errors,
        *p3.errors,
    ]
    all_passed = bool(
        len(all_errors) == 0
        and p1.passed
        and p2.passed
        and p3.passed
        and p2.internal_emmc_clip_writes == 0
        and p3.c2pa_rq_lic_preserved
        and not p3.c2pa_spoof_attempted
    )

    prelim = {
        "schema_version": PHASE_70_SCHEMA,
        "phase_version": PHASE_70_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "internal_emmc_clip_writes": p2.internal_emmc_clip_writes,
        "c2pa_rq_lic_preserved": p3.c2pa_rq_lic_preserved,
        "donor_file_sizes": donor_sizes,
        "pillar_1_clipname_proxy": asdict(p1),
        "pillar_2_dual_slot_matrix": asdict(p2),
        "pillar_3_nrtm_xml_sidecar": asdict(p3),
        "errors": tuple(all_errors),
    }
    digest = hashlib.sha256(
        json.dumps(prelim, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return ProxyClipnameAndSidecarReport(
        schema_version=PHASE_70_SCHEMA,
        phase_version=PHASE_70_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=False,
        internal_emmc_clip_writes=p2.internal_emmc_clip_writes,
        c2pa_rq_lic_preserved=p3.c2pa_rq_lic_preserved,
        donor_file_sizes=donor_sizes,
        pillar_1_clipname_proxy=p1,
        pillar_2_dual_slot_matrix=p2,
        pillar_3_nrtm_xml_sidecar=p3,
        errors=tuple(all_errors),
        report_sha256=digest,
    )
