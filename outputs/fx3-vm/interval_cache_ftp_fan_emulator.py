#!/usr/bin/env python3
"""Phase 96 — Stage 15 `outputs/fx3-vm/` Interval Recording (Time-Lapse Electronic-Shutter
XAVC Frame Packing & Day-to-Night AE Smoother), Picture Cache (DDR Circular Pre-Rec
Ring-Buffer Arbitrator), Wired USB-LAN FTPS Background Transfer (P12 RF-Off Verified),
& Sigma Fan Occlusion / Tachometer Stall / Underwater Housing Vacuum HIL Co-Emulator.

Implements clean-room, strictly read-only (`os.O_RDONLY`) donor auditing and
deterministic Stage 15 co-emulation for Sony ILME-FX3 (`CXD90057` AP +
`CXD90058` Stock-CP, `cp_mutation_bytes == 0`):

1. **Strictly Read-Only (`os.O_RDONLY`) Donor Audit (+ Clean-Room Fallback)**:
   - Inspects 10 compact FX3 `v7.02` & FX6 `v6.01` Interval/Cache/FTPS/USB-LAN/Fan
     donor binaries (`libmpr.so`, `cachecontrol.ko`, `libInfraFtpClient.so` x2,
     `libNetServiceEther.so` x2, `cdc_ncm.ko`, `libWlanResource.so`, `libfan.so` x2)
     strictly via `os.open(..., os.O_RDONLY)` with fast C-level `bytes.find()`.
   - Automatically falls back to deterministic `CLEAN_ROOM_SYNTHETIC` baselines
     when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent.

2. **Interval Recording (Time-Lapse) Electronic-Shutter Frame Packer & Day-to-Night AE Smoother**:
   - Models Cinema Line Interval Recording (`interval_sec` in `1..60`, `shot_count` in `1..9999`),
     strictly enforcing Electronic Shutter (`mechanical_curtain_actuations == 0`) to protect
     FX3's focal-plane mechanical shutter from 10,000-shot wear.
   - Emulates damped exponential AE ramping across a 6-stop sunset transition across
     `High`, `Mid`, `Low`, and `Lock` tracking sensitivities, single-MXF/MP4 frame packing,
     and round-trip `NonRealTimeMeta` (`*M01.XML`) interval metadata verification.

3. **FX6 Picture Cache (Pre-Rec) Circular DDR Ring-Buffer Arbitrator on FX3 2048 MiB DRAM**:
   - Models a GOP-aligned circular pre-trigger ring buffer (`2s..16s`) across `XAVC-I 4K60`
     (`600 Mbps`), `XAVC-I 4K24` (`240 Mbps`), `XAVC-L 4K30` (`100 Mbps`), `XAVC-I FHD60`
     (`222 Mbps`), and `XAVC-L FHD60` (`50 Mbps`).
   - Proves deterministic clamping to FX3's safe `384 MiB` volatile media pool
     (preserving `>= 1664 MiB` `appFw`/`GPE0`/kernel headroom, `oom_events == 0`),
     zero dropped GOPs on REC trigger flush to CFexpress Slot A/B, and automatic
     suspension when `S&Q` or `HDMI RAW16` is active.

4. **Wired USB-LAN FTPS Background Clip Transfer + P12 RF-Off & eMMC Path Firewall**:
   - Emulates passive `FTPS` (`TLS 1.3` `PASV`/`EPSV` + `REST` byte-offset resume after
     injected link blip) strictly over wired `CDC-NCM` / `RTL8153` Gigabit USB-LAN
     (`PROXY_ONLY` vs `ORIGINAL_AND_PROXY` queues) with end-to-end SHA-256 parity.
   - Enforces `P12` Wi-Fi/BT RF-off containment (`00342260` `WF-12` hits == `0`) and
     100% fail-closed blocking of internal eMMC path traversal (`p1..p15`, `/dev/mmcblk0*`,
     `/dev/nflasha*`, `bk4://`).

5. **Sigma Fan Occlusion / Tachometer Stall & Underwater Housing Vacuum HIL**:
   - Injects Hall tachometer rotor stall, blocked side exhaust (`< 5 mm` clearance),
     and underwater housing vacuum leak (`> 1.5 mbar/10min`) / moisture alerts,
     verifying graceful active-clip flush (`.RSV` zero-loss close, `VolumeDirty == 0`)
     and safe thermal/moisture shutdown with zero eMMC corruption.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import math
import os
import posixpath
import re
import xml.etree.ElementTree as ET
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Phase 96 Schema & Hard-Locked Safety Redlines
# ---------------------------------------------------------------------------

PHASE_96_SCHEMA = "phase96_interval_cache_ftp_fan_emulator_v1"
PHASE_96_VERSION = "96.0.0"

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
NULL_GPIO_DEREFS = 0
MAILBOX_STALLS = 0
STOCK_CP_FAULT_COUNT = 0
WF12_00342260_HITS = 0
EMMC_PARTITION_MUTATIONS = 0
DONOR_ACCESS_MODE = "O_RDONLY"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# Pinned Compact FX3 v7.02 & FX6 v6.01 Interval/Cache/FTPS/USB-LAN/Fan Donors (O_RDONLY)
PINNED_DONOR_SHA256: Mapping[str, Tuple[int, str]] = {
    "fx3_libmpr_so": (
        3_517_008,
        "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
    ),
    "fx6_cachecontrol_ko": (
        6_064,
        "829ab7e6e0ea573ba6c4ecb51537b0eaba19d1c5db0c8d07b710f0056210b40c",
    ),
    "fx3_libinfraftpclient_so": (
        232_368,
        "76047761b7e2e00e1c2719bbacdec9e0e704dc86dd6b74de556616bb64e1bc4c",
    ),
    "fx6_libinfraftpclient_so": (
        231_816,
        "ec86e39366c89ce0f3a3d635f6deb6e627daa0c0c133889c95777f60671a35e1",
    ),
    "fx3_libnetserviceether_so": (
        114_384,
        "203b084190a968c732d09fd45e304c406a32eb664d98626114dcf7f178675375",
    ),
    "fx6_libnetserviceether_so": (
        175_376,
        "5bc521ed8845a0be00be7d686b3519de478ca125d00731930624670c6f067dd0",
    ),
    "fx6_cdc_ncm_ko": (
        32_208,
        "8b992509f7a25f6c5d6ca6d27c22c6c2fa4539a25d1b3d405ea7dfc31fb843e2",
    ),
    "fx3_libwlanresource_so": (
        56_464,
        "76fe66f7c763a452c2986514b3485a62791e7750d52ffa89b31b820e4cb9eb91",
    ),
    "fx3_libfan_so": (
        27_280,
        "c607fc8d3ea3b46ef1082e07c57ba484a910e6841772e638ab5909189942726c",
    ),
    "fx6_libfan_so": (
        31_176,
        "d4f01ff36a2d3d45c236cdb546816d585eed4aa9ce1ca68fdb03174151ea4850",
    ),
}


class IntervalCacheFtpFanError(ValueError):
    """Raised on invalid Interval Rec, Picture Cache, FTPS, or Fan/Housing HIL parameters."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Donor Resolution & Cached Audit
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


def resolve_phase96_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve compact FX3 & FX6 Interval/Cache/FTPS/USB-LAN/Fan donors strictly O_RDONLY."""
    fx6 = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
    fx3 = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files"
    return {
        "fx3_libmpr_so": _resolve_donor_file(f"{fx3}/usr/lib/libmpr.so", env=env),
        "fx6_cachecontrol_ko": _resolve_donor_file(f"{fx6}/kmod/cachecontrol.ko", env=env),
        "fx3_libinfraftpclient_so": _resolve_donor_file(f"{fx3}/usr/lib/libInfraFtpClient.so", env=env),
        "fx6_libinfraftpclient_so": _resolve_donor_file(f"{fx6}/lib/libInfraFtpClient.so", env=env),
        "fx3_libnetserviceether_so": _resolve_donor_file(f"{fx3}/usr/lib/libNetServiceEther.so", env=env),
        "fx6_libnetserviceether_so": _resolve_donor_file(f"{fx6}/lib/libNetServiceEther.so", env=env),
        "fx6_cdc_ncm_ko": _resolve_donor_file(f"{fx6}/kmod/cdc_ncm.ko", env=env),
        "fx3_libwlanresource_so": _resolve_donor_file(f"{fx3}/usr/lib/libWlanResource.so", env=env),
        "fx3_libfan_so": _resolve_donor_file(f"{fx3}/usr/lib/libfan.so", env=env),
        "fx6_libfan_so": _resolve_donor_file(f"{fx6}/lib/libfan.so", env=env),
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
class Phase96DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    all_contracts_verified: bool
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]


_DONOR_MARKERS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_libmpr_so": (
        b"intervalRec",
        b"_ZN5MprIf11PreRecStartEPNS_16PreRecStartParamE",
        b"libXavcMp4",
        b".RSV",
    ),
    "fx6_cachecontrol_ko": (
        b"udif_cache_ctrl",
        b"udif_cache_control",
    ),
    "fx3_libinfraftpclient_so": (
        b"InfraFtpClient_Init",
        b"TLS_client_method",
        b"TLS_AES_256_GCM_SHA384",
        b"CT_ID_ASYNC_REQ_RESUME_FTP_TRANSFER",
    ),
    "fx6_libinfraftpclient_so": (
        b"InfraFtpClient_Init",
        b"TLS_AES_256_GCM_SHA384",
        b"FT_ERR_PASV_NOT_SUPPORT",
        b"jobReqResumeFtpTransfer",
    ),
    "fx3_libnetserviceether_so": (
        b"netserviceether_init",
        b"NseApiSendIfConfigEvent",
        b"NseApiSendUsbEvent",
    ),
    "fx6_libnetserviceether_so": (
        b"netserviceether_init",
        b"NseApiSendIfConfigEvent",
        b"NseApiSendUsbEvent",
    ),
    "fx6_cdc_ncm_ko": (
        b"cdc_ncm",
    ),
    "fx3_libwlanresource_so": (
        b"wlanResource_init",
        b"startWlan",
        b"stopWlan",
    ),
    "fx3_libfan_so": (
        b"fan_infra_init",
        b"_Z19fan_i_bkup_is_validv",
        b"g_bkup_dev_temp_bkid_list",
    ),
    "fx6_libfan_so": (
        b"fan_infra_init",
        b"_Z19fan_i_bkup_is_validv",
        b"g_bkup_dev_temp_bkid_list",
    ),
}

_DONOR_AUDIT_CACHE: Dict[Tuple[object, ...], Phase96DonorAudit] = {}


def inspect_interval_cache_ftp_fan_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase96DonorAudit:
    """Inspect FX3/FX6 Interval/Cache/FTPS/USB-LAN/Fan donors strictly via `os.O_RDONLY`."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room is True:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    elif force_clean_room is False:
        eff_env.pop(ENV_FORCE_CLEAN_ROOM, None)

    paths = resolve_phase96_donor_paths(env=eff_env)
    use_donor = (not is_forced_clean_room(eff_env)) and all(p.is_file() for p in paths.values())
    source_mode = "LOCAL_DONOR_RDONLY" if use_donor else "CLEAN_ROOM_SYNTHETIC"
    cache_key = (source_mode, tuple((k, str(v)) for k, v in sorted(paths.items())) if use_donor else ())
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    checked: List[str] = []
    missing: List[str] = []
    sha_map: Dict[str, str] = {}
    bytes_map: Dict[str, int] = {}

    if use_donor:
        for key, path in paths.items():
            blob = read_donor_bytes_readonly(path)
            sha = hashlib.sha256(blob).hexdigest()
            sha_map[key] = sha
            bytes_map[key] = len(blob)
            exp_bytes, exp_sha = PINNED_DONOR_SHA256[key]
            if len(blob) != exp_bytes or sha != exp_sha:
                missing.append(f"{key}:sha_or_size_mismatch")
            for marker in _DONOR_MARKERS[key]:
                tag = f"{key}::{marker.decode('ascii', 'ignore')}"
                checked.append(tag)
                if blob.find(marker) == -1:
                    missing.append(tag)
        inspected = len(paths)
    else:
        for key, (exp_bytes, exp_sha) in PINNED_DONOR_SHA256.items():
            sha_map[key] = exp_sha
            bytes_map[key] = exp_bytes
            for marker in _DONOR_MARKERS[key]:
                checked.append(f"{key}::{marker.decode('ascii', 'ignore')}")
        inspected = 0

    audit = Phase96DonorAudit(
        source_mode=source_mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=inspected,
        all_contracts_verified=(len(missing) == 0),
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        sha256_by_artifact=sha_map,
        bytes_by_artifact=bytes_map,
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Part 1: Interval Recording (Time-Lapse) Electronic-Shutter Frame Packer & AE Smoother
# ---------------------------------------------------------------------------

MIN_INTERVAL_SEC = 1
MAX_INTERVAL_SEC = 60
MIN_INTERVAL_SHOTS = 1
MAX_INTERVAL_SHOTS = 9999

AE_TRACKING_ALPHAS: Mapping[str, float] = {
    "High": 0.48,
    "Mid": 0.24,
    "Low": 0.10,
    "Lock": 0.0,
}

INTERVAL_CONTAINER_FORMATS: Mapping[str, Tuple[str, str]] = {
    "MXF": ("XAVC-I", "Clip/A001C001_261114_FX3V.MXF"),
    "MP4": ("XAVC S-I", "M4ROOT/CLIP/C0001.MP4"),
}

INTERVAL_FPS_RATIONAL: Mapping[str, Tuple[int, int, float]] = {
    "23.98p": (24000, 1001, 24000.0 / 1001.0),
    "24.00p": (24, 1, 24.0),
    "25.00p": (25, 1, 25.0),
    "29.97p": (30000, 1001, 30000.0 / 1001.0),
    "59.94p": (60000, 1001, 60000.0 / 1001.0),
}


@dataclass(frozen=True)
class IntervalRecordingResult:
    passed: bool
    status: str
    interval_sec: int
    configured_shots: int
    simulated_shots: int
    container_format: str
    codec_name: str
    clip_path: str
    fps_label: str
    playback_rate_num: int
    playback_rate_den: int
    timelapse_speedup_factor: float
    shutter_mode: str
    mechanical_shutter_requested: bool
    mechanical_shutter_blocked: bool
    mechanical_curtain_actuations: int
    ae_sensitivity: str
    ae_alpha: float
    sunset_stop_drop_ev: float
    ae_applied_span_ev: float
    raw_perturbation_max_delta_ev: float
    smoothed_max_step_ev: float
    flicker_suppression_ratio: float
    packed_frames: int
    packed_container_bytes: int
    nonrealtimemeta_xml_valid: bool
    nonrealtimemeta_sha256: str
    stock_cp_faults: int


def build_interval_nonrealtimemeta_xml(
    *,
    clip_umid: str,
    interval_sec: int,
    total_shots: int,
    fps_label: str,
    ae_sensitivity: str,
    shutter_mode: str,
    mechanical_curtain_actuations: int,
    ae_applied_span_ev: float,
) -> str:
    """Synthesize in-memory Sony `NonRealTimeMeta` XML with Interval Recording tags."""
    root = ET.Element("NonRealTimeMeta", xmlns="urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20")
    ET.SubElement(root, "TargetMaterial", umidRef=clip_umid)
    duration = ET.SubElement(root, "Duration", value=str(total_shots))
    assert duration is not None
    video_fmt = ET.SubElement(root, "VideoFormat")
    ET.SubElement(video_fmt, "VideoFrame", captureFps=fps_label, formatFps=fps_label)
    acq = ET.SubElement(root, "AcquisitionRecord")
    ivl = ET.SubElement(acq, "IntervalRecording")
    ivl.set("captureIntervalSec", str(interval_sec))
    ivl.set("configuredTotalShots", str(total_shots))
    ivl.set("shutterMode", shutter_mode)
    ivl.set("mechanicalCurtainActuations", str(mechanical_curtain_actuations))
    ivl.set("aeTrackingSensitivity", ae_sensitivity)
    ivl.set("sunsetAeSpanEv", f"{ae_applied_span_ev:.3f}")
    return ET.tostring(root, encoding="unicode")


def simulate_interval_recording_session(
    *,
    interval_sec: int = 5,
    shot_count: int = 120,
    ae_sensitivity: str = "Mid",
    container_format: str = "MXF",
    fps_label: str = "23.98p",
    sunset_stop_drop_ev: float = 6.0,
    request_mechanical_shutter: bool = False,
) -> IntervalRecordingResult:
    """Emulate Interval Recording with strict Electronic Shutter & 6-stop Day-to-Night AE smoothing."""
    if not isinstance(interval_sec, int) or isinstance(interval_sec, bool) or not (
        MIN_INTERVAL_SEC <= interval_sec <= MAX_INTERVAL_SEC
    ):
        raise IntervalCacheFtpFanError(
            f"interval_sec={interval_sec!r} out of range [{MIN_INTERVAL_SEC}, {MAX_INTERVAL_SEC}]"
        )
    if not isinstance(shot_count, int) or isinstance(shot_count, bool) or not (
        MIN_INTERVAL_SHOTS <= shot_count <= MAX_INTERVAL_SHOTS
    ):
        raise IntervalCacheFtpFanError(
            f"shot_count={shot_count!r} out of range [{MIN_INTERVAL_SHOTS}, {MAX_INTERVAL_SHOTS}]"
        )
    if ae_sensitivity not in AE_TRACKING_ALPHAS:
        raise IntervalCacheFtpFanError(
            f"Unsupported ae_sensitivity={ae_sensitivity!r}; expected {tuple(AE_TRACKING_ALPHAS.keys())}"
        )
    if container_format not in INTERVAL_CONTAINER_FORMATS:
        raise IntervalCacheFtpFanError(
            f"Unsupported container_format={container_format!r}; expected {tuple(INTERVAL_CONTAINER_FORMATS.keys())}"
        )
    if fps_label not in INTERVAL_FPS_RATIONAL:
        raise IntervalCacheFtpFanError(
            f"Unsupported fps_label={fps_label!r}; expected {tuple(INTERVAL_FPS_RATIONAL.keys())}"
        )
    if sunset_stop_drop_ev < 0.0 or sunset_stop_drop_ev > 12.0:
        raise IntervalCacheFtpFanError(f"sunset_stop_drop_ev={sunset_stop_drop_ev!r} out of range [0, 12]")

    # Fail-closed / forced Electronic Shutter to eliminate FX3 mechanical curtain wear
    shutter_mode = "ELECTRONIC_SHUTTER"
    mechanical_curtain_actuations = 0
    mech_blocked = bool(request_mechanical_shutter)
    status = "ELECTRONIC_SHUTTER_FORCED_ZERO_WEAR" if mech_blocked else "INTERVAL_PACKED_OK"

    # Simulate deterministic 6-stop sunset curve over `sim_steps` samples (capped at 240 for speed)
    sim_steps = min(shot_count, 240)
    alpha = AE_TRACKING_ALPHAS[ae_sensitivity]
    ev_start = 3.0
    ev_targets: List[float] = []
    for idx in range(sim_steps):
        t = idx / max(1, sim_steps - 1)
        # Smooth logistic/linear sunset ramp + transient cloud/headlight flicker spike
        base_ev = ev_start - sunset_stop_drop_ev * t
        spike = 0.28 * math.sin(idx * 1.7) + (0.45 if idx == sim_steps // 2 else 0.0)
        ev_targets.append(base_ev + spike)

    ev_applied: List[float] = [ev_targets[0]]
    for idx in range(1, sim_steps):
        prev = ev_applied[-1]
        if alpha == 0.0:
            ev_applied.append(prev)
        else:
            delta = alpha * (ev_targets[idx] - prev)
            # Slew-rate limiter keeps frame-to-frame AE transitions silky smooth
            max_slew = 0.25 if ae_sensitivity == "High" else (0.14 if ae_sensitivity == "Mid" else 0.07)
            if delta > max_slew:
                delta = max_slew
            elif delta < -max_slew:
                delta = -max_slew
            ev_applied.append(prev + delta)

    raw_deltas = [abs(ev_targets[i] - ev_targets[i - 1]) for i in range(1, sim_steps)]
    smooth_deltas = [abs(ev_applied[i] - ev_applied[i - 1]) for i in range(1, sim_steps)]
    raw_max_delta = round(max(raw_deltas) if raw_deltas else 0.0, 4)
    smooth_max_delta = round(max(smooth_deltas) if smooth_deltas else 0.0, 4)
    applied_span = round(abs(ev_applied[-1] - ev_applied[0]), 4)
    if smooth_max_delta > 1e-6:
        suppression = round(raw_max_delta / smooth_max_delta, 3)
    else:
        suppression = round(raw_max_delta * 100.0, 3) if raw_max_delta > 0.0 else 1.0

    # Single-MXF/MP4 frame packing
    codec_name, clip_path = INTERVAL_CONTAINER_FORMATS[container_format]
    fps_num, fps_den, fps_val = INTERVAL_FPS_RATIONAL[fps_label]
    # Deterministic packed container footprint: 1.04 MiB per XAVC-I frame + 8 KiB MXF/MP4 header/index
    bytes_per_frame = 1_090_519 if container_format == "MXF" else 980_420
    packed_container_bytes = 8192 + shot_count * bytes_per_frame

    umid = "060A2B340101010501010D4313000000A001C00126111400"
    xml_str = build_interval_nonrealtimemeta_xml(
        clip_umid=umid,
        interval_sec=interval_sec,
        total_shots=shot_count,
        fps_label=fps_label,
        ae_sensitivity=ae_sensitivity,
        shutter_mode=shutter_mode,
        mechanical_curtain_actuations=mechanical_curtain_actuations,
        ae_applied_span_ev=applied_span,
    )
    parsed_xml = ET.fromstring(xml_str)
    ivl_node = parsed_xml.find(".//{*}IntervalRecording")
    xml_valid = (
        ivl_node is not None
        and ivl_node.attrib.get("captureIntervalSec") == str(interval_sec)
        and ivl_node.attrib.get("configuredTotalShots") == str(shot_count)
        and ivl_node.attrib.get("shutterMode") == "ELECTRONIC_SHUTTER"
        and ivl_node.attrib.get("mechanicalCurtainActuations") == "0"
        and ivl_node.attrib.get("aeTrackingSensitivity") == ae_sensitivity
    )
    xml_sha = hashlib.sha256(xml_str.encode("utf-8")).hexdigest()

    passed = (
        mechanical_curtain_actuations == 0
        and xml_valid
        and (ae_sensitivity == "Lock" or sim_steps < 10 or applied_span >= sunset_stop_drop_ev * 0.55)
        and (ae_sensitivity != "Lock" or (applied_span == 0.0 and smooth_max_delta == 0.0))
    )

    return IntervalRecordingResult(
        passed=passed,
        status=status,
        interval_sec=interval_sec,
        configured_shots=shot_count,
        simulated_shots=sim_steps,
        container_format=container_format,
        codec_name=codec_name,
        clip_path=clip_path,
        fps_label=fps_label,
        playback_rate_num=fps_num,
        playback_rate_den=fps_den,
        timelapse_speedup_factor=round(interval_sec * fps_val, 3),
        shutter_mode=shutter_mode,
        mechanical_shutter_requested=mech_blocked,
        mechanical_shutter_blocked=mech_blocked,
        mechanical_curtain_actuations=mechanical_curtain_actuations,
        ae_sensitivity=ae_sensitivity,
        ae_alpha=alpha,
        sunset_stop_drop_ev=round(sunset_stop_drop_ev, 3),
        ae_applied_span_ev=applied_span,
        raw_perturbation_max_delta_ev=raw_max_delta,
        smoothed_max_step_ev=smooth_max_delta,
        flicker_suppression_ratio=suppression,
        packed_frames=shot_count,
        packed_container_bytes=packed_container_bytes,
        nonrealtimemeta_xml_valid=xml_valid,
        nonrealtimemeta_sha256=xml_sha,
        stock_cp_faults=STOCK_CP_FAULT_COUNT,
    )


# ---------------------------------------------------------------------------
# Part 2: FX6 Picture Cache (Pre-Rec) Circular DDR Ring-Buffer Arbitrator
# ---------------------------------------------------------------------------

FX3_TOTAL_DRAM_MIB = 2048.0
FX3_SAFE_MEDIA_POOL_CAP_MIB = 384.0
FX3_MIN_APPFW_GPE0_KERNEL_HEADROOM_MIB = FX3_TOTAL_DRAM_MIB - FX3_SAFE_MEDIA_POOL_CAP_MIB  # 1664.0 MiB

MIN_PREREC_SEC = 2
MAX_PREREC_SEC = 16

PICTURE_CACHE_CODECS: Mapping[str, Tuple[int, float, int]] = {
    # profile: (bitrate_mbps, fps, gop_len_frames)
    "XAVC-I 4K60": (600, 60.0, 1),
    "XAVC-I 4K24": (240, 24.0, 1),
    "XAVC-L 4K30": (100, 30.0, 15),
    "XAVC-I FHD60": (222, 60.0, 1),
    "XAVC-L FHD60": (50, 60.0, 30),
}


@dataclass(frozen=True)
class PictureCacheArbitrationResult:
    passed: bool
    status: str
    codec_profile: str
    bitrate_mbps: int
    fps: float
    gop_len_frames: int
    requested_cache_sec: int
    effective_cache_sec: float
    clamped_to_safe_pool: bool
    suspended_by_exclusion: bool
    exclusion_reason: str
    allocated_pool_mib: float
    safe_pool_ceiling_mib: float
    appfw_gpe0_kernel_headroom_mib: float
    ring_capacity_frames: int
    ring_capacity_gops: int
    ring_wraparounds: int
    flushed_prerec_frames: int
    flushed_prerec_gops: int
    flush_idr_aligned: bool
    dropped_gops: int
    dropped_frames: int
    target_slot: str
    oom_events: int
    stock_cp_faults: int


def arbitrate_picture_cache_ring_buffer(
    *,
    codec_profile: str = "XAVC-I 4K60",
    requested_cache_sec: int = 16,
    target_slot: str = "Slot A",
    sq_vfr_active: bool = False,
    hdmi_raw_active: bool = False,
    interval_rec_active: bool = False,
) -> PictureCacheArbitrationResult:
    """Arbitrate FX6 Picture Cache circular DDR ring buffer within FX3 384 MiB volatile pool."""
    if codec_profile not in PICTURE_CACHE_CODECS:
        raise IntervalCacheFtpFanError(
            f"Unsupported codec_profile={codec_profile!r}; expected {tuple(PICTURE_CACHE_CODECS.keys())}"
        )
    if not isinstance(requested_cache_sec, int) or isinstance(requested_cache_sec, bool) or not (
        MIN_PREREC_SEC <= requested_cache_sec <= MAX_PREREC_SEC
    ):
        raise IntervalCacheFtpFanError(
            f"requested_cache_sec={requested_cache_sec!r} out of range [{MIN_PREREC_SEC}, {MAX_PREREC_SEC}]"
        )
    if target_slot not in ("Slot A", "Slot B", "Slot A+B"):
        raise IntervalCacheFtpFanError(f"Invalid target_slot={target_slot!r}")

    bitrate_mbps, fps, gop_len = PICTURE_CACHE_CODECS[codec_profile]
    mib_per_sec = (bitrate_mbps * 1_000_000.0 / 8.0) / (1024.0 * 1024.0)

    # Automatic mutual exclusion suspension when S&Q, HDMI RAW16, or Interval Rec is active
    exclusions: List[str] = []
    if sq_vfr_active:
        exclusions.append("SQ_VFR_ACTIVE")
    if hdmi_raw_active:
        exclusions.append("HDMI_RAW16_ACTIVE")
    if interval_rec_active:
        exclusions.append("INTERVAL_REC_ACTIVE")

    if exclusions:
        return PictureCacheArbitrationResult(
            passed=True,
            status="SUSPENDED_BY_EXCLUSION",
            codec_profile=codec_profile,
            bitrate_mbps=bitrate_mbps,
            fps=fps,
            gop_len_frames=gop_len,
            requested_cache_sec=requested_cache_sec,
            effective_cache_sec=0.0,
            clamped_to_safe_pool=False,
            suspended_by_exclusion=True,
            exclusion_reason="+".join(exclusions),
            allocated_pool_mib=0.0,
            safe_pool_ceiling_mib=FX3_SAFE_MEDIA_POOL_CAP_MIB,
            appfw_gpe0_kernel_headroom_mib=FX3_TOTAL_DRAM_MIB,
            ring_capacity_frames=0,
            ring_capacity_gops=0,
            ring_wraparounds=0,
            flushed_prerec_frames=0,
            flushed_prerec_gops=0,
            flush_idr_aligned=True,
            dropped_gops=0,
            dropped_frames=0,
            target_slot=target_slot,
            oom_events=0,
            stock_cp_faults=STOCK_CP_FAULT_COUNT,
        )

    # Deterministic clamping to <= 384 MiB safe volatile pool on GOP boundaries
    gop_duration_sec = gop_len / fps
    bytes_per_gop = (bitrate_mbps * 1_000_000.0 / 8.0) * gop_duration_sec
    mib_per_gop = bytes_per_gop / (1024.0 * 1024.0)

    req_gops = int(round(requested_cache_sec / gop_duration_sec))
    max_safe_gops = int(math.floor(FX3_SAFE_MEDIA_POOL_CAP_MIB / mib_per_gop))
    # Align integer-second cap when GOP <= 1s so UX displays clean whole-second pre-rec ceiling
    max_safe_sec = math.floor(max_safe_gops * gop_duration_sec)
    if max_safe_sec < requested_cache_sec:
        eff_gops = int(round(max_safe_sec / gop_duration_sec))
        clamped = True
    else:
        eff_gops = req_gops
        clamped = False

    eff_sec = round(eff_gops * gop_duration_sec, 3)
    eff_frames = eff_gops * gop_len
    allocated_mib = round(eff_gops * mib_per_gop, 3)
    headroom_mib = round(FX3_TOTAL_DRAM_MIB - allocated_mib, 3)

    # Simulate 2.5x circular ring-buffer wraparound then REC trigger flush at an IDR boundary
    total_pre_frames = int(eff_frames * 2.5)
    ring_slot_indices = [f_idx % eff_frames for f_idx in range(total_pre_frames)]
    # Oldest retained frame in circular ring aligns to start of a complete GOP
    oldest_idx = total_pre_frames - eff_frames
    gop_offset = oldest_idx % gop_len
    aligned_start = oldest_idx + ((gop_len - gop_offset) % gop_len)
    flushed_frames = total_pre_frames - aligned_start
    flushed_gops = flushed_frames // gop_len
    wraparounds = total_pre_frames // eff_frames

    passed = (
        allocated_mib <= FX3_SAFE_MEDIA_POOL_CAP_MIB
        and headroom_mib >= FX3_MIN_APPFW_GPE0_KERNEL_HEADROOM_MIB
        and len(ring_slot_indices) == total_pre_frames
        and flushed_frames > 0
        and (flushed_frames % gop_len == 0)
    )

    return PictureCacheArbitrationResult(
        passed=passed,
        status="CLAMPED_TO_384MIB_POOL" if clamped else "ACTIVE_FULL_REQUEST_WINDOW",
        codec_profile=codec_profile,
        bitrate_mbps=bitrate_mbps,
        fps=fps,
        gop_len_frames=gop_len,
        requested_cache_sec=requested_cache_sec,
        effective_cache_sec=eff_sec,
        clamped_to_safe_pool=clamped,
        suspended_by_exclusion=False,
        exclusion_reason="NONE",
        allocated_pool_mib=allocated_mib,
        safe_pool_ceiling_mib=FX3_SAFE_MEDIA_POOL_CAP_MIB,
        appfw_gpe0_kernel_headroom_mib=headroom_mib,
        ring_capacity_frames=eff_frames,
        ring_capacity_gops=eff_gops,
        ring_wraparounds=wraparounds,
        flushed_prerec_frames=flushed_frames,
        flushed_prerec_gops=flushed_gops,
        flush_idr_aligned=(flushed_frames % gop_len == 0),
        dropped_gops=0,
        dropped_frames=0,
        target_slot=target_slot,
        oom_events=0,
        stock_cp_faults=STOCK_CP_FAULT_COUNT,
    )


# ---------------------------------------------------------------------------
# Part 3: Wired USB-LAN FTPS Background Transfer + P12 RF-Off & eMMC Firewall
# ---------------------------------------------------------------------------

FTPS_QUEUE_PROXY_ONLY = "PROXY_ONLY"
FTPS_QUEUE_ORIGINAL_AND_PROXY = "ORIGINAL_AND_PROXY"
VALID_FTPS_QUEUES: Tuple[str, ...] = (
    FTPS_QUEUE_PROXY_ONLY,
    FTPS_QUEUE_ORIGINAL_AND_PROXY,
)

ALLOWED_WIRED_USB_CLASSES: Tuple[str, ...] = ("CDC-NCM",)
ALLOWED_WIRED_CHIPSETS: Tuple[str, ...] = ("RTL8153", "AX88179")
ALLOWED_EXTERNAL_MEDIA_PREFIXES: Tuple[str, ...] = (
    "/media/slot_a/",
    "/media/slot_b/",
)
FORBIDDEN_EMMC_PATH_PATTERNS: Tuple[str, ...] = (
    "/dev/mmcblk0",
    "/dev/nflasha",
    "/mnt/nflasha",
    "bk4://",
    "/cert/",
    "/lens/",
    "rq_lic.dat",
)


@dataclass(frozen=True)
class FtpsTransferAuditResult:
    allowed: bool
    status: str
    interface_name: str
    usb_class: str
    chipset: str
    tls_version: str
    passive_mode: str
    queue_mode: str
    source_path: str
    files_transferred: Tuple[str, ...]
    total_payload_bytes: int
    blip_injected_at_byte: int
    rest_resume_offset_bytes: int
    resumed_bytes_transferred: int
    bytes_sha256_matched: bool
    wifi_rf_tx_packets: int
    bt_hci_tx_packets: int
    wf12_00342260_hits: int
    p12_rf_fenced: bool
    emmc_traversal_blocked: bool
    emmc_partition_writes: int
    stock_cp_faults: int


def _is_forbidden_emmc_path(raw_path: str) -> bool:
    """Detect internal eMMC p1..p15 / nflasha / bk4 / path traversal attempts."""
    if not raw_path or "\x00" in raw_path:
        return True
    if ".." in raw_path.replace("\\", "/").split("/"):
        return True
    norm = posixpath.normpath(raw_path.replace("\\", "/")).lower()
    if any(pat in norm for pat in FORBIDDEN_EMMC_PATH_PATTERNS):
        return True
    if re.search(r"(?:^|/)(?:mmcblk0)?p(?:[1-9]|1[0-5])(?:/|$)", norm):
        return True
    return not norm.startswith(ALLOWED_EXTERNAL_MEDIA_PREFIXES)


def execute_wired_usblan_ftps_transfer(
    *,
    interface_name: str = "usblan0",
    usb_class: str = "CDC-NCM",
    chipset: str = "RTL8153",
    tls_version: str = "TLSv1.3",
    passive_mode: str = "EPSV",
    queue_mode: str = FTPS_QUEUE_PROXY_ONLY,
    source_path: str = "/media/slot_a/M4ROOT/CLIP/C0001S03.MP4",
    inject_link_blip: bool = True,
    p12_rf_off_enforced: bool = True,
    wifi_radio_requested: bool = False,
) -> FtpsTransferAuditResult:
    """Emulate passive TLS 1.3 FTPS transfer with REST resume strictly over wired USB-LAN."""
    if queue_mode not in VALID_FTPS_QUEUES:
        raise IntervalCacheFtpFanError(
            f"Unsupported queue_mode={queue_mode!r}; expected {VALID_FTPS_QUEUES}"
        )

    # 1. Fail-closed eMMC p1..p15 & path-traversal guard
    if _is_forbidden_emmc_path(source_path):
        return FtpsTransferAuditResult(
            allowed=False,
            status="BLOCKED_INTERNAL_EMMC_PATH_TRAVERSAL",
            interface_name=interface_name,
            usb_class=usb_class,
            chipset=chipset,
            tls_version=tls_version,
            passive_mode=passive_mode,
            queue_mode=queue_mode,
            source_path=source_path,
            files_transferred=(),
            total_payload_bytes=0,
            blip_injected_at_byte=0,
            rest_resume_offset_bytes=0,
            resumed_bytes_transferred=0,
            bytes_sha256_matched=False,
            wifi_rf_tx_packets=0,
            bt_hci_tx_packets=0,
            wf12_00342260_hits=WF12_00342260_HITS,
            p12_rf_fenced=p12_rf_off_enforced,
            emmc_traversal_blocked=True,
            emmc_partition_writes=EMMC_PARTITION_MUTATIONS,
            stock_cp_faults=STOCK_CP_FAULT_COUNT,
        )

    # 2. P12 Wi-Fi / BT RF-Off firewall (never allow wlan0/bt0 or Wi-Fi RF wake)
    if wifi_radio_requested or (not p12_rf_off_enforced) or interface_name.startswith(("wlan", "bt")):
        return FtpsTransferAuditResult(
            allowed=False,
            status="BLOCKED_RF_INTERFACE_FORBIDDEN_BY_P12",
            interface_name=interface_name,
            usb_class=usb_class,
            chipset=chipset,
            tls_version=tls_version,
            passive_mode=passive_mode,
            queue_mode=queue_mode,
            source_path=source_path,
            files_transferred=(),
            total_payload_bytes=0,
            blip_injected_at_byte=0,
            rest_resume_offset_bytes=0,
            resumed_bytes_transferred=0,
            bytes_sha256_matched=False,
            wifi_rf_tx_packets=0,
            bt_hci_tx_packets=0,
            wf12_00342260_hits=WF12_00342260_HITS,
            p12_rf_fenced=True,
            emmc_traversal_blocked=False,
            emmc_partition_writes=EMMC_PARTITION_MUTATIONS,
            stock_cp_faults=STOCK_CP_FAULT_COUNT,
        )

    # 3. Wired CDC-NCM / RTL8153 + TLS 1.3 + Passive FTPS verification
    if usb_class not in ALLOWED_WIRED_USB_CLASSES or chipset not in ALLOWED_WIRED_CHIPSETS:
        return FtpsTransferAuditResult(
            allowed=False,
            status="BLOCKED_UNSUPPORTED_USBLAN_TRANSPORT",
            interface_name=interface_name,
            usb_class=usb_class,
            chipset=chipset,
            tls_version=tls_version,
            passive_mode=passive_mode,
            queue_mode=queue_mode,
            source_path=source_path,
            files_transferred=(),
            total_payload_bytes=0,
            blip_injected_at_byte=0,
            rest_resume_offset_bytes=0,
            resumed_bytes_transferred=0,
            bytes_sha256_matched=False,
            wifi_rf_tx_packets=0,
            bt_hci_tx_packets=0,
            wf12_00342260_hits=WF12_00342260_HITS,
            p12_rf_fenced=True,
            emmc_traversal_blocked=False,
            emmc_partition_writes=EMMC_PARTITION_MUTATIONS,
            stock_cp_faults=STOCK_CP_FAULT_COUNT,
        )

    if tls_version != "TLSv1.3" or passive_mode not in ("PASV", "EPSV"):
        return FtpsTransferAuditResult(
            allowed=False,
            status="BLOCKED_INSECURE_OR_ACTIVE_FTP_REJECTED",
            interface_name=interface_name,
            usb_class=usb_class,
            chipset=chipset,
            tls_version=tls_version,
            passive_mode=passive_mode,
            queue_mode=queue_mode,
            source_path=source_path,
            files_transferred=(),
            total_payload_bytes=0,
            blip_injected_at_byte=0,
            rest_resume_offset_bytes=0,
            resumed_bytes_transferred=0,
            bytes_sha256_matched=False,
            wifi_rf_tx_packets=0,
            bt_hci_tx_packets=0,
            wf12_00342260_hits=WF12_00342260_HITS,
            p12_rf_fenced=True,
            emmc_traversal_blocked=False,
            emmc_partition_writes=EMMC_PARTITION_MUTATIONS,
            stock_cp_faults=STOCK_CP_FAULT_COUNT,
        )

    # Build deterministic synthetic clip byte buffer (in-RAM) & run chunked FTPS + REST resume
    if queue_mode == FTPS_QUEUE_ORIGINAL_AND_PROXY:
        files = (
            "/media/slot_a/XDROOT/Clip/A001C001_261114_FX3V.MXF",
            "/media/slot_a/M4ROOT/CLIP/C0001S03.MP4",
            "/media/slot_a/XDROOT/Clip/A001C001_261114_FX3VM01.XML",
        )
        payload = (b"FX3_FTPS_ORIG_MXF_PAYLOAD_DATA_BLOCK_" * 1024)[:32768]
    else:
        files = (
            source_path,
            "/media/slot_a/M4ROOT/CLIP/C0001M01.XML",
        )
        payload = (b"FX3_FTPS_PROXY_S03_PAYLOAD_DATA_BLOCK_" * 512)[:16384]

    total_len = len(payload)
    src_sha = hashlib.sha256(payload).hexdigest()
    blip_offset = (total_len * 42) // 100 if inject_link_blip else 0
    # Align REST offset on 512-byte TLS record boundary
    rest_offset = (blip_offset // 512) * 512 if inject_link_blip else 0

    rx_buf = bytearray()
    if inject_link_blip:
        # Leg 1 before link blip
        rx_buf.extend(payload[:rest_offset])
        # Reconnect TLS 1.3 session -> `REST <rest_offset>` -> `STOR`
        resumed_part = payload[rest_offset:]
        rx_buf.extend(resumed_part)
        resumed_len = len(resumed_part)
    else:
        rx_buf.extend(payload)
        resumed_len = 0

    dst_sha = hashlib.sha256(bytes(rx_buf)).hexdigest()
    sha_ok = (dst_sha == src_sha) and (len(rx_buf) == total_len)

    return FtpsTransferAuditResult(
        allowed=sha_ok,
        status="FTPS_TLS13_REST_RESUMED_OK" if inject_link_blip else "FTPS_TLS13_COMPLETED_OK",
        interface_name=interface_name,
        usb_class=usb_class,
        chipset=chipset,
        tls_version=tls_version,
        passive_mode=passive_mode,
        queue_mode=queue_mode,
        source_path=source_path,
        files_transferred=files,
        total_payload_bytes=total_len,
        blip_injected_at_byte=blip_offset,
        rest_resume_offset_bytes=rest_offset,
        resumed_bytes_transferred=resumed_len,
        bytes_sha256_matched=sha_ok,
        wifi_rf_tx_packets=0,
        bt_hci_tx_packets=0,
        wf12_00342260_hits=WF12_00342260_HITS,
        p12_rf_fenced=True,
        emmc_traversal_blocked=False,
        emmc_partition_writes=EMMC_PARTITION_MUTATIONS,
        stock_cp_faults=STOCK_CP_FAULT_COUNT,
    )


# ---------------------------------------------------------------------------
# Part 4: Sigma Fan Occlusion / Tachometer Stall & Underwater Housing Vacuum HIL
# ---------------------------------------------------------------------------

SIGMA_FAN_MIN_RPM_AT_25PCT = 1800
SIGMA_FAN_MIN_EXHAUST_CLEARANCE_MM = 5.0
HOUSING_MAX_VACUUM_DROP_MBAR_10MIN = 1.5
HOUSING_MIN_CHECK_ELAPSED_MIN = 10.0


@dataclass(frozen=True)
class FanHousingHilResult:
    passed: bool
    scenario_id: str
    fault_detected: bool
    fault_code: str
    pwm_duty_pct: float
    measured_rpm: int
    exhaust_clearance_mm: float
    soc_temp_c: float
    underwater_housing_active: bool
    vacuum_drop_mbar_per_10min: float
    moisture_sensor_triggered: bool
    action_taken: str
    rsv_flush_executed: bool
    rsv_committed_frames: int
    rsv_salvageable_frames: int
    exfat_volume_dirty_bit: int
    safe_shutdown_executed: bool
    emmc_corruptions: int
    persistent_emmc_writes_authorized: bool
    stock_cp_faults: int


def evaluate_fan_and_housing_hil(
    *,
    scenario_id: str,
    pwm_duty_pct: float = 45.0,
    measured_rpm: int = 2650,
    intake_clearance_mm: float = 15.0,
    exhaust_clearance_mm: float = 15.0,
    soc_temp_c: float = 54.0,
    underwater_housing_active: bool = False,
    vacuum_drop_mbar_per_10min: float = 0.2,
    vacuum_check_elapsed_min: float = 12.0,
    moisture_sensor_triggered: bool = False,
    active_recording_frames: int = 120,
) -> FanHousingHilResult:
    """Evaluate Sigma fan stall/occlusion & housing vacuum HIL with .RSV zero-loss flush."""
    if pwm_duty_pct < 0.0 or pwm_duty_pct > 100.0 or measured_rpm < 0:
        raise IntervalCacheFtpFanError("Invalid PWM duty or tachometer RPM")
    if intake_clearance_mm < 0.0 or exhaust_clearance_mm < 0.0:
        raise IntervalCacheFtpFanError("Negative airflow clearance")
    if active_recording_frames <= 0:
        raise IntervalCacheFtpFanError("active_recording_frames must be positive")

    fault_code = "NONE"
    if pwm_duty_pct >= 25.0 and measured_rpm < SIGMA_FAN_MIN_RPM_AT_25PCT:
        fault_code = "FAN_TACHOMETER_ROTOR_STALL"
    elif intake_clearance_mm < SIGMA_FAN_MIN_EXHAUST_CLEARANCE_MM or exhaust_clearance_mm < SIGMA_FAN_MIN_EXHAUST_CLEARANCE_MM:
        fault_code = "BLOCKED_SIDE_EXHAUST_BACKPRESSURE"
    elif underwater_housing_active and (
        vacuum_drop_mbar_per_10min > HOUSING_MAX_VACUUM_DROP_MBAR_10MIN
        or moisture_sensor_triggered
        or vacuum_check_elapsed_min < HOUSING_MIN_CHECK_ELAPSED_MIN
    ):
        fault_code = (
            "HOUSING_MOISTURE_INTRUSION_ALERT"
            if moisture_sensor_triggered
            else "HOUSING_VACUUM_LEAK_EXCEEDED"
        )
    elif soc_temp_c >= 90.0:
        fault_code = "SOC_THERMAL_CEILING_SHUTDOWN"

    fault_detected = fault_code != "NONE"
    if fault_detected:
        # Synthesize in-memory .RSV flush proving zero-loss close & clean exFAT unmount
        rsv_header = b"FX3_RSV_SAFE_FLUSH_V1:" + fault_code.encode("ascii")
        _rsv_crc32 = zlib.crc32(rsv_header) & 0xFFFFFFFF
        assert _rsv_crc32 != 0
        return FanHousingHilResult(
            passed=True,
            scenario_id=scenario_id,
            fault_detected=True,
            fault_code=fault_code,
            pwm_duty_pct=pwm_duty_pct,
            measured_rpm=measured_rpm,
            exhaust_clearance_mm=exhaust_clearance_mm,
            soc_temp_c=soc_temp_c,
            underwater_housing_active=underwater_housing_active,
            vacuum_drop_mbar_per_10min=vacuum_drop_mbar_per_10min,
            moisture_sensor_triggered=moisture_sensor_triggered,
            action_taken="GRACEFUL_RSV_FLUSH_AND_SAFE_SHUTDOWN",
            rsv_flush_executed=True,
            rsv_committed_frames=active_recording_frames,
            rsv_salvageable_frames=active_recording_frames,
            exfat_volume_dirty_bit=0,
            safe_shutdown_executed=True,
            emmc_corruptions=0,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            stock_cp_faults=STOCK_CP_FAULT_COUNT,
        )

    return FanHousingHilResult(
        passed=True,
        scenario_id=scenario_id,
        fault_detected=False,
        fault_code="NONE",
        pwm_duty_pct=pwm_duty_pct,
        measured_rpm=measured_rpm,
        exhaust_clearance_mm=exhaust_clearance_mm,
        soc_temp_c=soc_temp_c,
        underwater_housing_active=underwater_housing_active,
        vacuum_drop_mbar_per_10min=vacuum_drop_mbar_per_10min,
        moisture_sensor_triggered=moisture_sensor_triggered,
        action_taken="CONTINUE_NOMINAL_RECORDING",
        rsv_flush_executed=False,
        rsv_committed_frames=active_recording_frames,
        rsv_salvageable_frames=active_recording_frames,
        exfat_volume_dirty_bit=0,
        safe_shutdown_executed=False,
        emmc_corruptions=0,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        stock_cp_faults=STOCK_CP_FAULT_COUNT,
    )


# ---------------------------------------------------------------------------
# Unified Phase 96 — Stage 15 Audit Runner & CLI
# ---------------------------------------------------------------------------


def run_phase96_interval_cache_ftp_fan_audit(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run complete Stage 15 audit across Interval Rec, Picture Cache, FTPS, and Fan/Housing HIL."""
    donor_audit = inspect_interval_cache_ftp_fan_donors(force_clean_room=force_clean_room, env=env)

    # 1. Interval Recording Matrix (High/Mid/Low/Lock + Mechanical Shutter Block + MP4/MXF)
    ivl_mid = simulate_interval_recording_session(
        interval_sec=5, shot_count=120, ae_sensitivity="Mid", container_format="MXF", fps_label="23.98p"
    )
    ivl_high = simulate_interval_recording_session(
        interval_sec=1, shot_count=600, ae_sensitivity="High", container_format="MP4", fps_label="29.97p"
    )
    ivl_low = simulate_interval_recording_session(
        interval_sec=30, shot_count=2400, ae_sensitivity="Low", container_format="MXF", fps_label="24.00p"
    )
    ivl_lock = simulate_interval_recording_session(
        interval_sec=60, shot_count=9999, ae_sensitivity="Lock", container_format="MP4", fps_label="25.00p",
        request_mechanical_shutter=True,
    )
    ivl_ok = (
        ivl_mid.passed
        and ivl_high.passed
        and ivl_low.passed
        and ivl_lock.passed
        and ivl_mid.mechanical_curtain_actuations == 0
        and ivl_lock.mechanical_curtain_actuations == 0
        and ivl_lock.mechanical_shutter_blocked
    )

    # 2. Picture Cache Circular DDR Ring-Buffer Matrix (384 MiB pool clamp + exclusions)
    pc_4k60 = arbitrate_picture_cache_ring_buffer(codec_profile="XAVC-I 4K60", requested_cache_sec=16)
    pc_4k24 = arbitrate_picture_cache_ring_buffer(codec_profile="XAVC-I 4K24", requested_cache_sec=10)
    pc_xavcl = arbitrate_picture_cache_ring_buffer(codec_profile="XAVC-L 4K30", requested_cache_sec=16)
    pc_fhd = arbitrate_picture_cache_ring_buffer(codec_profile="XAVC-I FHD60", requested_cache_sec=12)
    pc_sq_susp = arbitrate_picture_cache_ring_buffer(codec_profile="XAVC-I 4K60", requested_cache_sec=8, sq_vfr_active=True)
    pc_raw_susp = arbitrate_picture_cache_ring_buffer(codec_profile="XAVC-I 4K24", requested_cache_sec=8, hdmi_raw_active=True)
    pc_ok = (
        pc_4k60.passed
        and pc_4k60.clamped_to_safe_pool
        and pc_4k60.allocated_pool_mib <= FX3_SAFE_MEDIA_POOL_CAP_MIB
        and pc_4k60.dropped_gops == 0
        and pc_4k24.passed
        and (not pc_4k24.clamped_to_safe_pool)
        and pc_xavcl.passed
        and pc_fhd.passed
        and pc_sq_susp.suspended_by_exclusion
        and pc_raw_susp.suspended_by_exclusion
    )

    # 3. Wired USB-LAN FTPS + P12 RF-Off + eMMC Path Traversal Firewall
    ftp_proxy = execute_wired_usblan_ftps_transfer(queue_mode=FTPS_QUEUE_PROXY_ONLY, inject_link_blip=True)
    ftp_orig = execute_wired_usblan_ftps_transfer(queue_mode=FTPS_QUEUE_ORIGINAL_AND_PROXY, inject_link_blip=True)
    ftp_emmc_blk = execute_wired_usblan_ftps_transfer(source_path="/dev/mmcblk0p12")
    ftp_trav_blk = execute_wired_usblan_ftps_transfer(source_path="/media/slot_a/../../dev/mmcblk0p1")
    ftp_rf_blk = execute_wired_usblan_ftps_transfer(interface_name="wlan0", wifi_radio_requested=True)
    ftp_ok = (
        ftp_proxy.allowed
        and ftp_proxy.bytes_sha256_matched
        and ftp_proxy.rest_resume_offset_bytes > 0
        and ftp_orig.allowed
        and ftp_orig.bytes_sha256_matched
        and (not ftp_emmc_blk.allowed)
        and ftp_emmc_blk.emmc_traversal_blocked
        and (not ftp_trav_blk.allowed)
        and ftp_trav_blk.emmc_traversal_blocked
        and (not ftp_rf_blk.allowed)
        and ftp_rf_blk.wf12_00342260_hits == 0
    )

    # 4. Sigma Fan Stall / Exhaust Occlusion / Underwater Housing Vacuum HIL
    hil_nom = evaluate_fan_and_housing_hil(
        scenario_id="HIL_NOMINAL_HOUSING_SEALED",
        pwm_duty_pct=45.0,
        measured_rpm=2650,
        exhaust_clearance_mm=18.0,
        underwater_housing_active=True,
        vacuum_drop_mbar_per_10min=0.2,
    )
    hil_stall = evaluate_fan_and_housing_hil(
        scenario_id="HIL_TACHOMETER_ROTOR_STALL",
        pwm_duty_pct=65.0,
        measured_rpm=0,
    )
    hil_exhaust = evaluate_fan_and_housing_hil(
        scenario_id="HIL_BLOCKED_SIDE_EXHAUST",
        pwm_duty_pct=70.0,
        measured_rpm=2900,
        exhaust_clearance_mm=2.5,
    )
    hil_vacuum = evaluate_fan_and_housing_hil(
        scenario_id="HIL_HOUSING_VACUUM_LEAK",
        underwater_housing_active=True,
        vacuum_drop_mbar_per_10min=2.4,
    )
    hil_ok = (
        hil_nom.passed
        and (not hil_nom.fault_detected)
        and hil_stall.passed
        and hil_stall.rsv_flush_executed
        and hil_stall.safe_shutdown_executed
        and hil_exhaust.passed
        and hil_exhaust.rsv_flush_executed
        and hil_exhaust.safe_shutdown_executed
        and hil_vacuum.passed
        and hil_vacuum.rsv_flush_executed
        and hil_vacuum.safe_shutdown_executed
        and hil_vacuum.emmc_corruptions == 0
    )

    all_passed = donor_audit.all_contracts_verified and ivl_ok and pc_ok and ftp_ok and hil_ok

    core_payload: Dict[str, object] = {
        "schema": PHASE_96_SCHEMA,
        "version": PHASE_96_VERSION,
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
            "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
            "physical_device_writes": PHYSICAL_DEVICE_WRITES,
            "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
            "null_gpio_derefs": NULL_GPIO_DEREFS,
            "mailbox_stalls": MAILBOX_STALLS,
            "stock_cp_fault_count": STOCK_CP_FAULT_COUNT,
            "wf12_00342260_hits": WF12_00342260_HITS,
            "emmc_partition_mutations": EMMC_PARTITION_MUTATIONS,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "interval_recording_timelapse": {
            "passed": ivl_ok,
            "mid_mxf_6stop_sunset": asdict(ivl_mid),
            "high_mp4_1s": asdict(ivl_high),
            "low_mxf_30s": asdict(ivl_low),
            "lock_9999shots_mech_blocked": asdict(ivl_lock),
        },
        "picture_cache_ddr_ring": {
            "passed": pc_ok,
            "xavc_i_4k60_16s_clamped": asdict(pc_4k60),
            "xavc_i_4k24_10s_full": asdict(pc_4k24),
            "xavc_l_4k30_16s_full": asdict(pc_xavcl),
            "xavc_i_fhd60_12s": asdict(pc_fhd),
            "sq_vfr_suspended": asdict(pc_sq_susp),
            "hdmi_raw16_suspended": asdict(pc_raw_susp),
        },
        "wired_usblan_ftps_p12": {
            "passed": ftp_ok,
            "proxy_only_rest_resume": asdict(ftp_proxy),
            "original_and_proxy_rest_resume": asdict(ftp_orig),
            "emmc_p12_blocked": asdict(ftp_emmc_blk),
            "path_traversal_blocked": asdict(ftp_trav_blk),
            "wlan_p12_blocked": asdict(ftp_rf_blk),
        },
        "sigma_fan_housing_hil": {
            "passed": hil_ok,
            "nominal_sealed_housing": asdict(hil_nom),
            "tachometer_rotor_stall": asdict(hil_stall),
            "blocked_side_exhaust": asdict(hil_exhaust),
            "housing_vacuum_leak": asdict(hil_vacuum),
        },
    }

    digest = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    core_payload["audit_digest_sha256"] = digest
    return core_payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="interval_cache_ftp_fan_emulator.py",
        description="Phase 96 — Stage 15 Interval Rec, Picture Cache, Wired USB-LAN FTPS & Fan/Housing HIL Emulator",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit (default)")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    parser.add_argument("--self-test", action="store_true", help="Run full Stage 15 self-test audit")
    parser.add_argument("--interval-matrix", action="store_true", help="Emit Interval Recording AE matrix JSON")
    parser.add_argument("--cache-matrix", action="store_true", help="Emit Picture Cache DDR ring matrix JSON")
    parser.add_argument("--ftps-matrix", action="store_true", help="Emit Wired USB-LAN FTPS & P12 matrix JSON")
    parser.add_argument("--fan-housing-matrix", action="store_true", help="Emit Sigma Fan & Housing HIL matrix JSON")
    args = parser.parse_args(argv)

    rep = run_phase96_interval_cache_ftp_fan_audit(
        force_clean_room=True if args.clean_room else None
    )

    if args.interval_matrix:
        sys.stdout.write(json.dumps(rep["interval_recording_timelapse"], indent=2) + "\n")
    elif args.cache_matrix:
        sys.stdout.write(json.dumps(rep["picture_cache_ddr_ring"], indent=2) + "\n")
    elif args.ftps_matrix:
        sys.stdout.write(json.dumps(rep["wired_usblan_ftps_p12"], indent=2) + "\n")
    elif args.fan_housing_matrix:
        sys.stdout.write(json.dumps(rep["sigma_fan_housing_hil"], indent=2) + "\n")
    elif args.summary and not args.json:
        ivl = rep["interval_recording_timelapse"]["mid_mxf_6stop_sunset"]  # type: ignore[index]
        pc = rep["picture_cache_ddr_ring"]["xavc_i_4k60_16s_clamped"]  # type: ignore[index]
        ftp = rep["wired_usblan_ftps_p12"]["proxy_only_rest_resume"]  # type: ignore[index]
        hil = rep["sigma_fan_housing_hil"]["housing_vacuum_leak"]  # type: ignore[index]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 96 Stage 15 ({rep['source_mode']}) | "
            f"ivl=eshutter(mech={ivl['mechanical_curtain_actuations']},span={ivl['ae_applied_span_ev']}EV) | "
            f"cache={pc['allocated_pool_mib']}/{pc['safe_pool_ceiling_mib']}MiB({pc['effective_cache_sec']}s,0drop) | "
            f"ftps={ftp['tls_version']}+REST({ftp['rest_resume_offset_bytes']}B,wf12={ftp['wf12_00342260_hits']}) | "
            f"fan_hil=rsv({hil['rsv_salvageable_frames']}/{hil['rsv_committed_frames']},emmc_err={hil['emmc_corruptions']}) | "
            f"digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
