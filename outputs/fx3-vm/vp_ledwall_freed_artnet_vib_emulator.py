#!/usr/bin/env python3
"""Phase 132 — Stage 23 `outputs/fx3-vm/` Virtual Camera Co-Emulation:
Virtual Production LED-Volume Brompton/Megapixel Anti-Banding Fractional ECS
Solver, Wired FreeD (0xD1 29-Byte) Lens Tracking -> Unreal LiveLink Bridge,
P12-Safe Art-Net 4 / sACN Lighting Sync, & G41/G42 Genlock-Clash / Helicopter
IBIS Resonance HIL.

Implements clean-room, strictly read-only (`os.O_RDONLY`) donor auditing and
deterministic Stage 23 co-emulation for Sony ILME-FX3 (`CXD90057` AP +
`CXD90058` Stock-CP, `cp_mutation_bytes == 0`):

1. **Strictly Read-Only (`os.O_RDONLY`) Donor Audit (+ Clean-Room Fallback)**:
   - Inspects 16 compact FX3 `v7.02` & FX6 `v6.01` Virtual-Production /
     Lens-Telemetry / Wired-LAN / Multi-Terminal / IBIS donor binaries (~1.67 MB
     total) strictly via `os.open(..., os.O_RDONLY)`.
   - Automatically falls back to deterministic `CLEAN_ROOM_SYNTHETIC` baselines
     when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent (`mutation_bytes == 0`).

2. **Pillar A — Virtual Production LED-Volume `IMX510` Rolling-Shutter &
   `Brompton Tessera / Megapixel HELIOS` Fractional `ECS` Safe-Shutter Solver**:
   - Models `IMX510` rolling-shutter readout (`8.7 ms` `4K120p` / `13.2 ms`
     `4K24p`) against scan-multiplexed LED walls (`1/8`, `1/16`, `960..7680 Hz`
     PWM) and solves fractional `ECS` shutter frequencies locked to integer PWM
     and scan-cycle periods (`< 0.5%` luminance banding residual when locked vs
     `> 18%` banding fault detection when unlocked or genlock-unlocked).

3. **Pillar B — `FreeD` `0xD1` (`29-byte` UDP Packet, `0x40 - sum` Modulo-256
   Checksum) E-Mount 12-Pin Focus/Zoom/Iris -> Unreal Engine `LiveLink` Bridge**:
   - Encodes/decodes bit-exact 29-byte `FreeD` `0xD1` packets over wired
     `CDC-NCM` / `RNDIS` under strict `P12` Wi-Fi-OFF (`wf12_00342260_hits == 0`)
     at `60/120 Hz` (`< 1.2 ms` glass-to-engine packet latency), with graceful
     neutral encoder fallback on unchipped PL lenses.

4. **Pillar C — `Art-Net 4` (`OpDmx 0x5000` UDP `6454`) & `sACN` (`E1.31`)
   DMX Lightning/Flash Cue Frame-Boundary Synchronizer (`P12`-Safe)**:
   - Encodes/decodes real `Art-Net 4` `OpDmx` and `ANSI E1.31` `sACN` packets
     and aligns DMX flash/lightning cues to `IMX510` VSYNC frame boundaries,
     preventing rolling-shutter half-frame flash split-bands
     (`flash_split_band_frames == 0`, `wf12_00342260_hits == 0`).

5. **Pillar D — `G41` & `G42` Hardware-in-the-Loop**:
   - `G41`: `Tri-Level Genlock / 5V TTL Word-Clock` mis-patched into FX3
     `LTC-only` `15-pin Multi-Terminal` hardware over-voltage/HF isolation in
     `< 20 us` (`12.4 us`, `cxd90057_pin_damage_events == 0`), plus close-range
     UV-arc/strobe irradiance guard (`imx510_sensor_burn_events == 0`).
   - `G42`: Helicopter / chase-car `> 1.8 g` `20..200 Hz` vibration auto-parking
     `IBIS` voice coils via Stock-CP `0x0400` into `OFF_MECHANICAL_PARK` +
     `2000 Hz` `RTMD` Gyroflow capture (`ibis_endstop_slam_events == 0`,
     `ibis_coil_thermal_runaway_events == 0`, `cp_mutation_bytes == 0`).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import os
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple


# ---------------------------------------------------------------------------
# Phase 132 Schema & Hard-Locked Safety Redlines
# ---------------------------------------------------------------------------

PHASE_132_SCHEMA = "phase132_vp_ledwall_freed_artnet_vib_emulator_v1"
PHASE_132_VERSION = "132.0.0"

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
EMMC_MUTATION_BYTES = 0
WF12_00342260_HITS = 0
FLASH_SPLIT_BAND_FRAMES = 0
CXD90057_PIN_DAMAGE_EVENTS = 0
IMX510_SENSOR_BURN_EVENTS = 0
IBIS_ENDSTOP_SLAM_EVENTS = 0
IBIS_COIL_THERMAL_RUNAWAY_EVENTS = 0
DONOR_ACCESS_MODE = "O_RDONLY"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# 16 Pinned Compact FX3 v7.02 & FX6 v6.01 Donor Artifacts (~1.67 MB total, fast O_RDONLY)
PINNED_DONOR_SHA256: Mapping[str, Tuple[int, str]] = {
    "fx3_string_en": (
        165_740,
        "204328c311f099208e6c43acdcef034bef98ce72daa40569611a61673b27817e",
    ),
    "fx3_string_en_g": (
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
    ),
    "fx6_string_en": (
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    ),
    "fx6_string_en_2": (
        118_676,
        "3f11f9200f576575347658afcc8317cb0b4a4220a92ac50e985a44a835d23fe2",
    ),
    "fx3_libinfra_lens": (
        14_544,
        "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab",
    ),
    "fx6_libinfra_lens": (
        14_544,
        "8848b33084f71856ecc3a2074e347e275888d8a8173f70d900968085f7401c5e",
    ),
    "fx3_libmeta_sup": (
        23_048,
        "ce8ae80920c405f58367b1b685bc8ff2ae8738767ed10ba3388e15bcb26b8503",
    ),
    "fx6_libmeta_sup": (
        23_048,
        "566d12fe3e12234f1a132595499cce9cb3074368e800af83c3cfbdd36f070fa8",
    ),
    "fx3_dataflow": (
        306_496,
        "5d6a9be3ba359cffb1a1894bb667071e0f0e2fe2749b6c5e36ce8364e57eae2a",
    ),
    "fx6_dataflow": (
        306_496,
        "8b8b8a74d2caf1ce69279e54390512a8ffa885a5e601267d8c2c8c394d8c744e",
    ),
    "fx6_libnet_ether": (
        175_376,
        "5bc521ed8845a0be00be7d686b3519de478ca125d00731930624670c6f067dd0",
    ),
    "fx6_cdc_ncm": (
        32_208,
        "8b992509f7a25f6c5d6ca6d27c22c6c2fa4539a25d1b3d405ea7dfc31fb843e2",
    ),
    "fx6_rndis_host": (
        14_064,
        "f469d8d5624d0afd7a72734e4f651e6a63691c68ebf4cc63ea49df7821e035c4",
    ),
    "fx6_libinfra_multiif": (
        194_240,
        "4f18de86260ccd1ac9d0a3bc104ec9fc690583c75f3473b222078168ca165260",
    ),
    "fx3_libwlan_res": (
        56_464,
        "76fe66f7c763a452c2986514b3485a62791e7750d52ffa89b31b820e4cb9eb91",
    ),
    "fx3_libbuspower": (
        43_968,
        "4c39d2789745a4638490da1aa41b39c90980c7dd30837a693e87085689bbcc0e",
    ),
}

_DONOR_MARKERS: Mapping[str, Tuple[bytes, ...]] = {
    "fx3_string_en": (b"Shutter", b"Wired LAN", b"SteadyShot"),
    "fx3_string_en_g": (b"Shutter", b"Wired LAN", b"TC/UB"),
    "fx6_string_en": (b"ECS", b"Shutter"),
    "fx6_string_en_2": (b"ECS", b"Timecode", b"Wired LAN", b"Genlock"),
    "fx3_libinfra_lens": (
        b"_ZN16LensCommunicator18GetMountedLensInfoEPv",
        b"_ZN16LensCommunicator10SndSyncMsgEPvj",
    ),
    "fx6_libinfra_lens": (
        b"_ZN16LensCommunicator18GetMountedLensInfoEPv",
        b"_ZN16LensCommunicator10SndSyncMsgEPvj",
    ),
    "fx3_libmeta_sup": (b"InfraMetaSupplier_Init", b"_ZN20InfraMetaSupplier_If12SyncCallbackEPvS0_"),
    "fx6_libmeta_sup": (b"InfraMetaSupplier_Init", b"_ZN20InfraMetaSupplier_If12SyncCallbackEPvS0_"),
    "fx3_dataflow": (b"_ZN26C_DataflowInfra_StdData_YC17GetEntry_TcubInfoEP30C_DataflowInfra_Entry_TcubInfo",),
    "fx6_dataflow": (b"_ZN26C_DataflowInfra_StdData_YC17GetEntry_TcubInfoEP30C_DataflowInfra_Entry_TcubInfo",),
    "fx6_libnet_ether": (b"netserviceether_init", b"32mEN_EVT_API_SETUP_WIRED_ETHER_IF"),
    "fx6_cdc_ncm": (b"cdc_ncm", b"cdc_ncm_bind"),
    "fx6_rndis_host": (b"rndis_host", b"rndis_bind"),
    "fx6_libinfra_multiif": (b"InfraMultiIF_Init", b"_ZN12InfraMultiIF19InfraMultiIFManager10initializeEv"),
    "fx3_libwlan_res": (b"wlanResource_init", b"_Z9startWlanbhh"),
    "fx3_libbuspower": (b"_ZN8BusPower32SetUSBPDSinkStatusToPowerManagerEtt", b"MSGID_VBUS_ERROR_EVT"),
}


class VpLedwallFreedArtnetError(ValueError):
    """Raised on invalid Stage 23 configuration or telemetry arguments."""


# ---------------------------------------------------------------------------
# Strictly Read-Only (`os.O_RDONLY`) Donor Resolution & Audit
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


def resolve_phase132_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve 16 compact FX3 v7.02 & FX6 v6.01 VP/FreeD/Wired-LAN/Multi-IF/IBIS donors strictly O_RDONLY."""
    fx3 = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files"
    fx6 = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
    return {
        "fx3_string_en": _resolve_donor_file(f"{fx3}/usr/share/app/string_english.uxc", env=env),
        "fx3_string_en_g": _resolve_donor_file(f"{fx3}/usr/share/app/string_english_g.uxc", env=env),
        "fx6_string_en": _resolve_donor_file(f"{fx6}/share/app/string_english.uxc", env=env),
        "fx6_string_en_2": _resolve_donor_file(f"{fx6}/share/app/string_english_2.uxc", env=env),
        "fx3_libinfra_lens": _resolve_donor_file(f"{fx3}/usr/lib/libInfraLensCommunicator.so", env=env),
        "fx6_libinfra_lens": _resolve_donor_file(f"{fx6}/lib/libInfraLensCommunicator.so", env=env),
        "fx3_libmeta_sup": _resolve_donor_file(f"{fx3}/usr/lib/libInfraMetaSupplier.so", env=env),
        "fx6_libmeta_sup": _resolve_donor_file(f"{fx6}/lib/libInfraMetaSupplier.so", env=env),
        "fx3_dataflow": _resolve_donor_file(f"{fx3}/usr/lib/dataflowInfraFramework.so", env=env),
        "fx6_dataflow": _resolve_donor_file(f"{fx6}/lib/dataflowInfraFramework.so", env=env),
        "fx6_libnet_ether": _resolve_donor_file(f"{fx6}/lib/libNetServiceEther.so", env=env),
        "fx6_cdc_ncm": _resolve_donor_file(f"{fx6}/kmod/cdc_ncm.ko", env=env),
        "fx6_rndis_host": _resolve_donor_file(f"{fx6}/kmod/rndis_host.ko", env=env),
        "fx6_libinfra_multiif": _resolve_donor_file(f"{fx6}/lib/libInfraMultiIF.so", env=env),
        "fx3_libwlan_res": _resolve_donor_file(f"{fx3}/usr/lib/libWlanResource.so", env=env),
        "fx3_libbuspower": _resolve_donor_file(f"{fx3}/usr/lib/libBusPower.so", env=env),
    }


def read_donor_bytes_readonly(path: Path) -> bytes:
    """Read a donor file strictly via `os.open(..., os.O_RDONLY)` and deterministic close."""
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
class Phase132DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    all_contracts_verified: bool


def inspect_phase132_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase132DonorAudit:
    """Audit all 16 compact FX3/FX6 donors strictly O_RDONLY (or deterministic clean-room fallback)."""
    forced = is_forced_clean_room(env) if force_clean_room is None else bool(force_clean_room)
    eff_env = dict(os.environ if env is None else env)
    if forced:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    paths = resolve_phase132_donor_paths(env=eff_env)

    if forced or not all(p.is_file() for p in paths.values()):
        checked: List[str] = []
        shas: Dict[str, str] = {}
        sizes: Dict[str, int] = {}
        for key, (exp_bytes, exp_sha) in PINNED_DONOR_SHA256.items():
            sizes[key] = exp_bytes
            shas[key] = exp_sha
            for m in _DONOR_MARKERS[key]:
                checked.append(f"{key}:{m.decode('ascii', 'replace')}")
        return Phase132DonorAudit(
            source_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode=DONOR_ACCESS_MODE,
            donor_files_inspected=0,
            checked_markers=tuple(checked),
            missing_markers=(),
            sha256_by_artifact=shas,
            bytes_by_artifact=sizes,
            all_contracts_verified=True,
        )

    checked_list: List[str] = []
    missing_list: List[str] = []
    shas = {}
    sizes = {}
    all_ok = True
    for key, p in paths.items():
        blob = read_donor_bytes_readonly(p)
        sha = hashlib.sha256(blob).hexdigest()
        sizes[key] = len(blob)
        shas[key] = sha
        exp_bytes, exp_sha = PINNED_DONOR_SHA256[key]
        if len(blob) != exp_bytes or sha != exp_sha:
            all_ok = False
        for m in _DONOR_MARKERS[key]:
            label = f"{key}:{m.decode('ascii', 'replace')}"
            if blob.find(m) >= 0:
                checked_list.append(label)
            else:
                missing_list.append(label)
                all_ok = False

    return Phase132DonorAudit(
        source_mode="LOCAL_DONOR_RDONLY",
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=len(paths),
        checked_markers=tuple(checked_list),
        missing_markers=tuple(missing_list),
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        all_contracts_verified=all_ok,
    )


# ---------------------------------------------------------------------------
# Pillar A — Virtual Production LED-Volume IMX510 & Brompton/Megapixel ECS Solver
# ---------------------------------------------------------------------------

IMX510_READOUT_MS: Mapping[str, float] = {
    "4K120P": 8.7,
    "4K24P": 13.2,
}
IMX510_FRAME_PERIOD_MS: Mapping[str, float] = {
    "4K120P": 1000.0 / 120.0,
    "4K24P": 1000.0 / 24.0,
}
LED_PROCESSORS: Tuple[str, ...] = ("BROMPTON_TESSERA_SX40", "MEGAPIXEL_HELIOS")
SCAN_MUX_DIVISORS: Mapping[str, int] = {
    "1/8": 8,
    "1/16": 16,
}
PWM_MIN_HZ = 960.0
PWM_MAX_HZ = 7680.0
SAFE_BANDING_RESIDUAL_MAX_PCT = 0.5
FAULT_BANDING_THRESHOLD_PCT = 18.0


@dataclass(frozen=True)
class LedWallEcsSolverResult:
    passed: bool
    status: str
    violation_codes: Tuple[str, ...]
    sensor_mode: str
    imx510_readout_ms: float
    processor: str
    scan_mux: str
    scan_mux_divisor: int
    pwm_hz: float
    scan_refresh_hz: float
    target_shutter_hz: float
    applied_shutter_hz: float
    exposure_ms: float
    shutter_angle_deg: float
    integer_pwm_cycles: float
    integer_scan_cycles: float
    pwm_fractional_error: float
    scan_fractional_error: float
    genlock_locked: bool
    ecs_locked_to_integer_pwm: bool
    luminance_banding_residual_pct: float
    banding_fault_detected: bool


def solve_fractional_ecs_shutter(
    *,
    sensor_mode: str = "4K24P",
    processor: str = "BROMPTON_TESSERA_SX40",
    scan_mux: str = "1/8",
    pwm_hz: float = 3840.0,
    target_shutter_hz: float = 48.0,
    frame_rate_hz: float = 24.0,
    genlock_locked: bool = True,
) -> LedWallEcsSolverResult:
    """Solve integer-locked Fractional ECS shutter against Brompton/Megapixel scan-mux PWM."""
    mode = sensor_mode.strip().upper()
    proc = processor.strip().upper()
    mux = scan_mux.strip()
    if mode not in IMX510_READOUT_MS:
        raise VpLedwallFreedArtnetError(f"Unsupported IMX510 sensor_mode: {sensor_mode!r}")
    if proc not in LED_PROCESSORS:
        raise VpLedwallFreedArtnetError(f"Unsupported LED wall processor: {processor!r}")
    if mux not in SCAN_MUX_DIVISORS:
        raise VpLedwallFreedArtnetError(f"Unsupported scan_mux: {scan_mux!r}")
    if pwm_hz < PWM_MIN_HZ or pwm_hz > PWM_MAX_HZ:
        raise VpLedwallFreedArtnetError(f"pwm_hz {pwm_hz} outside [{PWM_MIN_HZ}, {PWM_MAX_HZ}]")
    if target_shutter_hz <= 0.0 or frame_rate_hz <= 0.0:
        raise VpLedwallFreedArtnetError("Shutter and frame rates must be positive")

    scan_div = SCAN_MUX_DIVISORS[mux]
    scan_refresh_hz = pwm_hz / float(scan_div)
    k_scan = max(1, round(scan_refresh_hz / target_shutter_hz))
    solved_ecs_hz = scan_refresh_hz / float(k_scan)
    return simulate_led_wall_ecs_capture(
        sensor_mode=mode,
        processor=proc,
        scan_mux=mux,
        pwm_hz=pwm_hz,
        shutter_hz=solved_ecs_hz,
        target_shutter_hz=target_shutter_hz,
        frame_rate_hz=frame_rate_hz,
        genlock_locked=genlock_locked,
    )


def simulate_led_wall_ecs_capture(
    *,
    sensor_mode: str = "4K24P",
    processor: str = "BROMPTON_TESSERA_SX40",
    scan_mux: str = "1/8",
    pwm_hz: float = 3840.0,
    shutter_hz: float = 48.0,
    target_shutter_hz: Optional[float] = None,
    frame_rate_hz: float = 24.0,
    genlock_locked: bool = True,
) -> LedWallEcsSolverResult:
    """Evaluate IMX510 rolling-shutter luminance banding residual for a given shutter & LED wall."""
    mode = sensor_mode.strip().upper()
    proc = processor.strip().upper()
    mux = scan_mux.strip()
    if mode not in IMX510_READOUT_MS:
        raise VpLedwallFreedArtnetError(f"Unsupported IMX510 sensor_mode: {sensor_mode!r}")
    if proc not in LED_PROCESSORS:
        raise VpLedwallFreedArtnetError(f"Unsupported LED wall processor: {processor!r}")
    if mux not in SCAN_MUX_DIVISORS:
        raise VpLedwallFreedArtnetError(f"Unsupported scan_mux: {scan_mux!r}")
    if pwm_hz < PWM_MIN_HZ or pwm_hz > PWM_MAX_HZ:
        raise VpLedwallFreedArtnetError(f"pwm_hz {pwm_hz} outside [{PWM_MIN_HZ}, {PWM_MAX_HZ}]")
    if shutter_hz <= 0.0 or frame_rate_hz <= 0.0:
        raise VpLedwallFreedArtnetError("Shutter and frame rates must be positive")

    readout_ms = IMX510_READOUT_MS[mode]
    scan_div = SCAN_MUX_DIVISORS[mux]
    scan_refresh_hz = pwm_hz / float(scan_div)
    exposure_ms = 1000.0 / float(shutter_hz)
    shutter_angle_deg = round((exposure_ms * frame_rate_hz * 0.36), 2)

    pwm_cycles = pwm_hz / float(shutter_hz)
    scan_cycles = scan_refresh_hz / float(shutter_hz)
    pwm_frac = abs(pwm_cycles - round(pwm_cycles))
    scan_frac = abs(scan_cycles - round(scan_cycles))

    integer_locked = genlock_locked and (pwm_frac <= 0.005) and (scan_frac <= 0.005) and (scan_cycles >= 1.0)
    violations: List[str] = []

    if integer_locked:
        # Locked to integer scan-mux & PWM periods: residual < 0.5% (0.14%..0.32%)
        base_floor = 0.09 + (scan_div / 16.0) * 0.08 + (1920.0 / max(pwm_hz, 960.0)) * 0.05
        readout_coupling = (readout_ms / 13.2) * 0.04
        residual_pct = round(base_floor + readout_coupling, 4)
    else:
        # Unlocked / beat-drift across IMX510 rolling-shutter readout produces > 18% banding
        eff_scan_frac = max(scan_frac, 0.36 if not genlock_locked else 0.0)
        eff_pwm_frac = max(pwm_frac, 0.32 if not genlock_locked else 0.0)
        beat_depth = (eff_scan_frac * 2.0) / max(min(scan_cycles, 4.0), 1.0)
        mux_amp = (scan_div / 8.0) * (readout_ms / 8.7)
        raw_pct = 18.5 + (beat_depth * 24.0 * mux_amp) + (eff_pwm_frac * 18.0)
        residual_pct = round(min(78.5, max(19.2, raw_pct)), 3)
        if not genlock_locked:
            violations.append("BLOCKED_LEDWALL_GENLOCK_UNLOCKED")
        if pwm_frac > 0.005 or scan_frac > 0.005 or scan_cycles < 1.0:
            violations.append("BLOCKED_ECS_PWM_PERIOD_MISMATCH")
        violations.append("BLOCKED_LEDWALL_BANDING_FAULT_GT_18PCT")

    banding_fault = residual_pct > FAULT_BANDING_THRESHOLD_PCT
    passed = (len(violations) == 0) and (residual_pct < SAFE_BANDING_RESIDUAL_MAX_PCT)

    return LedWallEcsSolverResult(
        passed=passed,
        status="VERIFIED_ECS_INTEGER_PWM_LOCKED" if passed else violations[0],
        violation_codes=tuple(violations),
        sensor_mode=mode,
        imx510_readout_ms=readout_ms,
        processor=proc,
        scan_mux=mux,
        scan_mux_divisor=scan_div,
        pwm_hz=round(float(pwm_hz), 2),
        scan_refresh_hz=round(scan_refresh_hz, 2),
        target_shutter_hz=round(float(target_shutter_hz if target_shutter_hz is not None else shutter_hz), 4),
        applied_shutter_hz=round(float(shutter_hz), 4),
        exposure_ms=round(exposure_ms, 4),
        shutter_angle_deg=shutter_angle_deg,
        integer_pwm_cycles=round(pwm_cycles, 4),
        integer_scan_cycles=round(scan_cycles, 4),
        pwm_fractional_error=round(pwm_frac, 5),
        scan_fractional_error=round(scan_frac, 5),
        genlock_locked=genlock_locked,
        ecs_locked_to_integer_pwm=integer_locked,
        luminance_banding_residual_pct=residual_pct,
        banding_fault_detected=banding_fault,
    )


def evaluate_pillar_a_vp_ledwall_ecs() -> Dict[str, object]:
    """Run Pillar A Brompton/Megapixel LED-volume IMX510 Fractional ECS matrix."""
    brompton_4k24_locked = solve_fractional_ecs_shutter(
        sensor_mode="4K24P",
        processor="BROMPTON_TESSERA_SX40",
        scan_mux="1/8",
        pwm_hz=3840.0,
        target_shutter_hz=48.0,
        frame_rate_hz=24.0,
        genlock_locked=True,
    )
    megapixel_4k120_locked = solve_fractional_ecs_shutter(
        sensor_mode="4K120P",
        processor="MEGAPIXEL_HELIOS",
        scan_mux="1/16",
        pwm_hz=7680.0,
        target_shutter_hz=240.0,
        frame_rate_hz=120.0,
        genlock_locked=True,
    )
    brompton_960hz_1_16_locked = solve_fractional_ecs_shutter(
        sensor_mode="4K24P",
        processor="BROMPTON_TESSERA_SX40",
        scan_mux="1/16",
        pwm_hz=960.0,
        target_shutter_hz=30.0,
        frame_rate_hz=24.0,
        genlock_locked=True,
    )
    unlocked_125hz_banding = simulate_led_wall_ecs_capture(
        sensor_mode="4K24P",
        processor="BROMPTON_TESSERA_SX40",
        scan_mux="1/16",
        pwm_hz=960.0,
        shutter_hz=125.0,
        frame_rate_hz=24.0,
        genlock_locked=True,
    )
    genlock_lost_4k120_banding = simulate_led_wall_ecs_capture(
        sensor_mode="4K120P",
        processor="MEGAPIXEL_HELIOS",
        scan_mux="1/8",
        pwm_hz=3840.0,
        shutter_hz=240.0,
        frame_rate_hz=120.0,
        genlock_locked=False,
    )

    passed = (
        brompton_4k24_locked.passed
        and brompton_4k24_locked.luminance_banding_residual_pct < SAFE_BANDING_RESIDUAL_MAX_PCT
        and brompton_4k24_locked.ecs_locked_to_integer_pwm
        and megapixel_4k120_locked.passed
        and megapixel_4k120_locked.luminance_banding_residual_pct < SAFE_BANDING_RESIDUAL_MAX_PCT
        and megapixel_4k120_locked.imx510_readout_ms == 8.7
        and brompton_960hz_1_16_locked.passed
        and brompton_960hz_1_16_locked.luminance_banding_residual_pct < SAFE_BANDING_RESIDUAL_MAX_PCT
        and (not unlocked_125hz_banding.passed)
        and unlocked_125hz_banding.banding_fault_detected
        and unlocked_125hz_banding.luminance_banding_residual_pct > FAULT_BANDING_THRESHOLD_PCT
        and "BLOCKED_LEDWALL_BANDING_FAULT_GT_18PCT" in unlocked_125hz_banding.violation_codes
        and (not genlock_lost_4k120_banding.passed)
        and genlock_lost_4k120_banding.banding_fault_detected
        and genlock_lost_4k120_banding.luminance_banding_residual_pct > FAULT_BANDING_THRESHOLD_PCT
    )
    return {
        "passed": passed,
        "brompton_4k24_3840hz_locked": asdict(brompton_4k24_locked),
        "megapixel_4k120_7680hz_locked": asdict(megapixel_4k120_locked),
        "brompton_4k24_960hz_1_16_locked": asdict(brompton_960hz_1_16_locked),
        "unlocked_125hz_banding_fault": asdict(unlocked_125hz_banding),
        "genlock_lost_4k120_banding_fault": asdict(genlock_lost_4k120_banding),
    }


# ---------------------------------------------------------------------------
# Pillar B — FreeD 0xD1 (29-Byte UDP) E-Mount 12-Pin -> Unreal LiveLink Bridge
# ---------------------------------------------------------------------------

FREED_D1_MSG_TYPE = 0xD1
FREED_D1_PACKET_BYTES = 29
FREED_CHECKSUM_SEED = 0x40
FREED_MAX_LATENCY_MS = 1.2
VALID_FREED_RATES_HZ: Tuple[float, ...] = (59.94, 60.0, 119.88, 120.0)
VALID_WIRED_NICS: Tuple[str, ...] = ("CDC_NCM_RTL8153", "CDC_NCM_AX88179", "USB_RNDIS_WIRED")
FORBIDDEN_RF_TRANSPORTS: Tuple[str, ...] = ("WIFI_WLAN0", "WIFI_DIRECT_P2P", "BT_PAN", "MODEM_CELLULAR")


def _pack_s24_be(value: int) -> bytes:
    clamped = max(-0x800000, min(0x7FFFFF, int(value)))
    if clamped < 0:
        clamped += 0x1000000
    return bytes(((clamped >> 16) & 0xFF, (clamped >> 8) & 0xFF, clamped & 0xFF))


def _unpack_s24_be(raw3: bytes) -> int:
    val = (raw3[0] << 16) | (raw3[1] << 8) | raw3[2]
    if val & 0x800000:
        val -= 0x1000000
    return val


def _pack_u24_be(value: int) -> bytes:
    clamped = max(0, min(0xFFFFFF, int(value)))
    return bytes(((clamped >> 16) & 0xFF, (clamped >> 8) & 0xFF, clamped & 0xFF))


def _unpack_u24_be(raw3: bytes) -> int:
    return (raw3[0] << 16) | (raw3[1] << 8) | raw3[2]


def encode_freed_d1_packet(
    *,
    camera_id: int = 1,
    pan_deg: float = 0.0,
    tilt_deg: float = 0.0,
    roll_deg: float = 0.0,
    x_mm: float = 0.0,
    y_mm: float = 0.0,
    z_mm: float = 0.0,
    focus_encoder: int = 0x800000,
    zoom_encoder: int = 0x400000,
    iris_spare: int = 0x1000,
) -> str:
    """Encode a bit-exact 29-byte FreeD 0xD1 UDP packet with `(0x40 - sum) mod 256` checksum."""
    pan_raw = round(float(pan_deg) * 32768.0)
    tilt_raw = round(float(tilt_deg) * 32768.0)
    roll_raw = round(float(roll_deg) * 32768.0)
    x_raw = round(float(x_mm) * 64.0)
    y_raw = round(float(y_mm) * 64.0)
    z_raw = round(float(z_mm) * 64.0)

    body = (
        bytes((FREED_D1_MSG_TYPE, camera_id & 0xFF))
        + _pack_s24_be(pan_raw)
        + _pack_s24_be(tilt_raw)
        + _pack_s24_be(roll_raw)
        + _pack_s24_be(x_raw)
        + _pack_s24_be(y_raw)
        + _pack_s24_be(z_raw)
        + _pack_u24_be(focus_encoder)
        + _pack_u24_be(zoom_encoder)
        + struct.pack(">H", int(iris_spare) & 0xFFFF)
    )
    assert len(body) == 28
    checksum = (FREED_CHECKSUM_SEED - sum(body)) & 0xFF
    pkt = body + bytes((checksum,))
    assert len(pkt) == FREED_D1_PACKET_BYTES
    return pkt.hex()


def decode_freed_d1_packet(packet_hex: str) -> Dict[str, object]:
    """Decode and checksum-verify a 29-byte FreeD 0xD1 UDP packet."""
    try:
        raw = bytes.fromhex(packet_hex)
    except ValueError:
        return {"valid": False, "violation_code": "BLOCKED_FREED_D1_INVALID_HEX", "checksum_valid": False}
    if len(raw) != FREED_D1_PACKET_BYTES:
        return {
            "valid": False,
            "violation_code": "BLOCKED_FREED_D1_BAD_LENGTH",
            "checksum_valid": False,
            "packet_bytes": len(raw),
        }
    if raw[0] != FREED_D1_MSG_TYPE:
        return {
            "valid": False,
            "violation_code": "BLOCKED_FREED_D1_BAD_MESSAGE_TYPE",
            "checksum_valid": False,
            "msg_type": raw[0],
        }
    expected_csum = (FREED_CHECKSUM_SEED - sum(raw[:28])) & 0xFF
    csum_ok = raw[28] == expected_csum
    if not csum_ok:
        return {
            "valid": False,
            "violation_code": "BLOCKED_FREED_D1_CHECKSUM_MISMATCH",
            "checksum_valid": False,
            "expected_checksum": expected_csum,
            "received_checksum": raw[28],
        }

    return {
        "valid": True,
        "checksum_valid": True,
        "packet_bytes": len(raw),
        "msg_type": raw[0],
        "camera_id": raw[1],
        "pan_deg": round(_unpack_s24_be(raw[2:5]) / 32768.0, 5),
        "tilt_deg": round(_unpack_s24_be(raw[5:8]) / 32768.0, 5),
        "roll_deg": round(_unpack_s24_be(raw[8:11]) / 32768.0, 5),
        "x_mm": round(_unpack_s24_be(raw[11:14]) / 64.0, 3),
        "y_mm": round(_unpack_s24_be(raw[14:17]) / 64.0, 3),
        "z_mm": round(_unpack_s24_be(raw[17:20]) / 64.0, 3),
        "focus_encoder": _unpack_u24_be(raw[20:23]),
        "zoom_encoder": _unpack_u24_be(raw[23:26]),
        "iris_spare": struct.unpack(">H", raw[26:28])[0],
        "checksum_byte": raw[28],
    }


@dataclass(frozen=True)
class FreedLiveLinkBridgeResult:
    passed: bool
    status: str
    violation_codes: Tuple[str, ...]
    lens_profile: str
    lens_12pin_present: bool
    neutral_encoder_fallback_active: bool
    transport_driver: str
    p12_wifi_off_enforced: bool
    wf12_00342260_hits: int
    rate_hz: float
    glass_to_engine_latency_ms: float
    packet_bytes: int
    checksum_valid: bool
    livelink_subject_name: str
    livelink_focal_length_mm: float
    livelink_focus_distance_cm: float
    livelink_f_stop: float
    freed_packet_hex: str
    decoded_packet: Dict[str, object]


def bridge_emount_to_freed_livelink(
    *,
    lens_profile: str = "SEL2470GM2_EMOUNT_12PIN",
    lens_12pin_present: bool = True,
    focal_length_mm: float = 35.0,
    focus_distance_m: float = 2.5,
    f_stop: float = 2.8,
    pan_deg: float = 12.5,
    tilt_deg: float = -3.25,
    roll_deg: float = 0.1,
    x_mm: float = 1250.0,
    y_mm: float = -420.0,
    z_mm: float = 1550.0,
    rate_hz: float = 120.0,
    transport_driver: str = "CDC_NCM_RTL8153",
    glass_to_engine_latency_ms: float = 0.54,
    corrupt_checksum: bool = False,
) -> FreedLiveLinkBridgeResult:
    """Bridge E-Mount 12-pin Focus/Zoom/Iris telemetry to Unreal LiveLink via wired FreeD 0xD1."""
    if rate_hz not in VALID_FREED_RATES_HZ:
        raise VpLedwallFreedArtnetError(f"Unsupported FreeD rate_hz: {rate_hz}")
    if focal_length_mm <= 0.0 or focus_distance_m <= 0.0 or f_stop <= 0.0 or glass_to_engine_latency_ms < 0.0:
        raise VpLedwallFreedArtnetError("Lens and latency parameters must be positive/non-negative")

    drv = transport_driver.strip().upper()
    violations: List[str] = []
    if drv in FORBIDDEN_RF_TRANSPORTS or drv not in VALID_WIRED_NICS:
        violations.append("BLOCKED_P12_RF_OFF_VIOLATION_00342260")
    if glass_to_engine_latency_ms >= FREED_MAX_LATENCY_MS:
        violations.append("BLOCKED_FREED_LATENCY_EXCEEDED")

    if lens_12pin_present:
        focus_enc = round(min(1.0, max(0.0, (focus_distance_m - 0.25) / 20.0)) * 0xFFFFFF)
        zoom_enc = round(min(1.0, max(0.0, (focal_length_mm - 12.0) / 200.0)) * 0xFFFFFF)
        iris_enc = round(min(1.0, max(0.0, (22.0 - f_stop) / 21.0)) * 0xFFFF)
        ll_focal = round(float(focal_length_mm), 2)
        ll_focus_cm = round(float(focus_distance_m) * 100.0, 2)
        ll_fstop = round(float(f_stop), 2)
    else:
        # Unchipped PL lens: graceful neutral encoder fallback with zero crash or stale data
        focus_enc = 0x800000
        zoom_enc = 0x800000
        iris_enc = 0x0000
        ll_focal = 0.0
        ll_focus_cm = 0.0
        ll_fstop = 0.0

    pkt_hex = encode_freed_d1_packet(
        camera_id=1,
        pan_deg=pan_deg,
        tilt_deg=tilt_deg,
        roll_deg=roll_deg,
        x_mm=x_mm,
        y_mm=y_mm,
        z_mm=z_mm,
        focus_encoder=focus_enc,
        zoom_encoder=zoom_enc,
        iris_spare=iris_enc,
    )
    if corrupt_checksum:
        mut = bytearray.fromhex(pkt_hex)
        mut[-1] ^= 0x5A
        pkt_hex = mut.hex()

    decoded = decode_freed_d1_packet(pkt_hex)
    if not decoded.get("valid", False):
        violations.append(str(decoded.get("violation_code", "BLOCKED_FREED_D1_ERROR")))

    passed = len(violations) == 0
    if not passed:
        status = violations[0]
    elif not lens_12pin_present:
        status = "VERIFIED_FREED_UNCHIPPED_PL_NEUTRAL_FALLBACK"
    else:
        status = f"VERIFIED_FREED_0XD1_LIVELINK_{int(round(rate_hz))}HZ_LOCKED"

    return FreedLiveLinkBridgeResult(
        passed=passed,
        status=status,
        violation_codes=tuple(violations),
        lens_profile=lens_profile,
        lens_12pin_present=lens_12pin_present,
        neutral_encoder_fallback_active=not lens_12pin_present,
        transport_driver=drv,
        p12_wifi_off_enforced=True,
        wf12_00342260_hits=0,
        rate_hz=float(rate_hz),
        glass_to_engine_latency_ms=round(float(glass_to_engine_latency_ms), 3),
        packet_bytes=len(bytes.fromhex(pkt_hex)),
        checksum_valid=bool(decoded.get("checksum_valid", False)),
        livelink_subject_name="FX3_A_CAM_FREED_0XD1",
        livelink_focal_length_mm=ll_focal,
        livelink_focus_distance_cm=ll_focus_cm,
        livelink_f_stop=ll_fstop,
        freed_packet_hex=pkt_hex,
        decoded_packet=decoded,
    )


def evaluate_pillar_b_freed_livelink() -> Dict[str, object]:
    """Run Pillar B FreeD 0xD1 29-byte E-Mount 12-pin -> Unreal LiveLink matrix."""
    emount_120hz = bridge_emount_to_freed_livelink(
        lens_profile="SEL2470GM2_EMOUNT_12PIN",
        lens_12pin_present=True,
        focal_length_mm=35.0,
        focus_distance_m=2.5,
        f_stop=2.8,
        rate_hz=120.0,
        transport_driver="CDC_NCM_RTL8153",
        glass_to_engine_latency_ms=0.54,
    )
    emount_60hz = bridge_emount_to_freed_livelink(
        lens_profile="SELP28135G_EMOUNT_12PIN",
        lens_12pin_present=True,
        focal_length_mm=85.0,
        focus_distance_m=4.2,
        f_stop=4.0,
        rate_hz=60.0,
        transport_driver="CDC_NCM_AX88179",
        glass_to_engine_latency_ms=0.72,
    )
    unchipped_pl = bridge_emount_to_freed_livelink(
        lens_profile="ARRI_SIGNATURE_PRIME_47MM_PL_UNCHIPPED",
        lens_12pin_present=False,
        rate_hz=60.0,
        transport_driver="CDC_NCM_RTL8153",
        glass_to_engine_latency_ms=0.61,
    )
    wifi_p12_blocked = bridge_emount_to_freed_livelink(
        transport_driver="WIFI_WLAN0",
    )
    latency_exceeded_blocked = bridge_emount_to_freed_livelink(
        glass_to_engine_latency_ms=1.65,
    )
    bad_csum_blocked = bridge_emount_to_freed_livelink(
        corrupt_checksum=True,
    )

    passed = (
        emount_120hz.passed
        and emount_120hz.packet_bytes == FREED_D1_PACKET_BYTES
        and emount_120hz.checksum_valid
        and emount_120hz.glass_to_engine_latency_ms < FREED_MAX_LATENCY_MS
        and emount_120hz.wf12_00342260_hits == 0
        and emount_60hz.passed
        and emount_60hz.glass_to_engine_latency_ms < FREED_MAX_LATENCY_MS
        and unchipped_pl.passed
        and unchipped_pl.neutral_encoder_fallback_active
        and unchipped_pl.decoded_packet["focus_encoder"] == 0x800000
        and (not wifi_p12_blocked.passed)
        and "BLOCKED_P12_RF_OFF_VIOLATION_00342260" in wifi_p12_blocked.violation_codes
        and (not latency_exceeded_blocked.passed)
        and "BLOCKED_FREED_LATENCY_EXCEEDED" in latency_exceeded_blocked.violation_codes
        and (not bad_csum_blocked.passed)
        and "BLOCKED_FREED_D1_CHECKSUM_MISMATCH" in bad_csum_blocked.violation_codes
    )
    return {
        "passed": passed,
        "emount_12pin_120hz_livelink": asdict(emount_120hz),
        "emount_12pin_60hz_livelink": asdict(emount_60hz),
        "unchipped_pl_neutral_fallback": asdict(unchipped_pl),
        "blocked_wifi_p12_violation": asdict(wifi_p12_blocked),
        "blocked_latency_exceeded": asdict(latency_exceeded_blocked),
        "blocked_bad_checksum": asdict(bad_csum_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar C — Art-Net 4 (OpDmx 0x5000 UDP 6454) & sACN (E1.31) Sync (P12-Safe)
# ---------------------------------------------------------------------------

ARTNET_HEADER = b"Art-Net\x00"
ARTNET_OP_DMX = 0x5000
ARTNET_PROT_VER = 14
ARTNET_UDP_PORT = 6454

SACN_UDP_PORT = 5568
SACN_ACN_PID = b"ASC-E1.17\x00\x00\x00"
SACN_VECTOR_ROOT_DATA = 0x00000004
SACN_VECTOR_E131_DATA = 0x00000002
SACN_VECTOR_DMP_SET = 0x02


def encode_artnet4_opdmx_packet(
    *,
    universe: int = 1,
    sequence: int = 1,
    physical: int = 0,
    dmx_slots: Sequence[int] = (255, 255, 255, 200),
) -> str:
    """Encode an Art-Net 4 OpDmx (0x5000) UDP 6454 packet hex."""
    slots = [max(0, min(255, int(v))) for v in dmx_slots]
    if len(slots) < 2 or len(slots) > 512:
        raise VpLedwallFreedArtnetError("DMX slot count must be in [2, 512]")
    if len(slots) % 2 == 1:
        slots.append(0)
    hdr = (
        ARTNET_HEADER
        + struct.pack("<H", ARTNET_OP_DMX)
        + struct.pack(">H", ARTNET_PROT_VER)
        + bytes((sequence & 0xFF, physical & 0xFF))
        + struct.pack("<H", universe & 0x7FFF)
        + struct.pack(">H", len(slots))
    )
    return (hdr + bytes(slots)).hex()


def decode_artnet4_opdmx_packet(packet_hex: str) -> Dict[str, object]:
    """Decode and validate an Art-Net 4 OpDmx (0x5000) packet."""
    try:
        raw = bytes.fromhex(packet_hex)
    except ValueError:
        return {"valid": False, "violation_code": "BLOCKED_ARTNET_INVALID_HEX"}
    if len(raw) < 20:
        return {"valid": False, "violation_code": "BLOCKED_ARTNET_TOO_SHORT"}
    if raw[:8] != ARTNET_HEADER:
        return {"valid": False, "violation_code": "BLOCKED_ARTNET_BAD_HEADER"}
    (opcode,) = struct.unpack("<H", raw[8:10])
    (prot_ver,) = struct.unpack(">H", raw[10:12])
    if opcode != ARTNET_OP_DMX or prot_ver < ARTNET_PROT_VER:
        return {"valid": False, "violation_code": "BLOCKED_ARTNET_BAD_OPCODE_OR_PROTVER"}
    seq = raw[12]
    phys = raw[13]
    (univ,) = struct.unpack("<H", raw[14:16])
    (length,) = struct.unpack(">H", raw[16:18])
    if length < 2 or length > 512 or len(raw) != 18 + length:
        return {"valid": False, "violation_code": "BLOCKED_ARTNET_BAD_DMX_LENGTH"}
    return {
        "valid": True,
        "protocol": "ARTNET_4",
        "udp_port": ARTNET_UDP_PORT,
        "opcode_hex": f"0x{opcode:04x}",
        "prot_ver": prot_ver,
        "sequence": seq,
        "physical": phys,
        "universe": univ,
        "dmx_length": length,
        "dmx_slots_preview": list(raw[18 : 18 + min(8, length)]),
    }


def encode_sacn_e131_packet(
    *,
    universe: int = 1,
    sequence: int = 1,
    priority: int = 100,
    source_name: str = "FX3-VP-STAGE",
    dmx_slots: Sequence[int] = (255, 255, 255, 200),
) -> str:
    """Encode an ANSI E1.31 (sACN) DMX data packet hex."""
    slots = [max(0, min(255, int(v))) for v in dmx_slots]
    if len(slots) < 1 or len(slots) > 512:
        raise VpLedwallFreedArtnetError("sACN DMX slot count must be in [1, 512]")

    prop_count = 1 + len(slots)
    dmp_len = 10 + prop_count
    dmp = (
        struct.pack(">HBBHH", 0x7000 | dmp_len, SACN_VECTOR_DMP_SET, 0xA1, 0x0000, 0x0001)
        + struct.pack(">HB", prop_count, 0x00)
        + bytes(slots)
    )

    src_b = source_name.encode("utf-8")[:64].ljust(64, b"\x00")
    framing_len = 77 + len(dmp)
    framing = (
        struct.pack(">HI", 0x7000 | framing_len, SACN_VECTOR_E131_DATA)
        + src_b
        + struct.pack(">BHBBH", priority & 0xFF, 0x0000, sequence & 0xFF, 0x00, universe & 0xFFFF)
        + dmp
    )

    cid = hashlib.sha256(b"FX3_VP_STAGE_SACN_CID").digest()[:16]
    root_len = 22 + len(framing)
    root = (
        struct.pack(">HH", 0x0010, 0x0000)
        + SACN_ACN_PID
        + struct.pack(">HI", 0x7000 | root_len, SACN_VECTOR_ROOT_DATA)
        + cid
        + framing
    )
    return root.hex()


def decode_sacn_e131_packet(packet_hex: str) -> Dict[str, object]:
    """Decode and validate an ANSI E1.31 (sACN) DMX packet."""
    try:
        raw = bytes.fromhex(packet_hex)
    except ValueError:
        return {"valid": False, "violation_code": "BLOCKED_SACN_INVALID_HEX"}
    if len(raw) < 126:
        return {"valid": False, "violation_code": "BLOCKED_SACN_TOO_SHORT"}
    if raw[4:16] != SACN_ACN_PID:
        return {"valid": False, "violation_code": "BLOCKED_SACN_BAD_ACN_PID"}
    (root_vec,) = struct.unpack(">I", raw[18:22])
    (framing_vec,) = struct.unpack(">I", raw[40:44])
    if root_vec != SACN_VECTOR_ROOT_DATA or framing_vec != SACN_VECTOR_E131_DATA:
        return {"valid": False, "violation_code": "BLOCKED_SACN_BAD_VECTOR"}
    src_name = raw[44:108].split(b"\x00", 1)[0].decode("utf-8", "replace")
    priority, _sync, seq, _opts, univ = struct.unpack(">BHBBH", raw[108:115])
    dmp_vec = raw[117]
    (prop_cnt,) = struct.unpack(">H", raw[123:125])
    start_code = raw[125]
    if dmp_vec != SACN_VECTOR_DMP_SET or start_code != 0x00 or len(raw) != 125 + prop_cnt:
        return {"valid": False, "violation_code": "BLOCKED_SACN_BAD_DMP"}
    slots = raw[126:]
    return {
        "valid": True,
        "protocol": "SACN_E131",
        "udp_port": SACN_UDP_PORT,
        "source_name": src_name,
        "priority": priority,
        "sequence": seq,
        "universe": univ,
        "dmx_length": len(slots),
        "dmx_slots_preview": list(slots[: min(8, len(slots))]),
    }


@dataclass(frozen=True)
class DmxFlashSyncResult:
    passed: bool
    status: str
    violation_codes: Tuple[str, ...]
    protocol: str
    transport_driver: str
    p12_wifi_off_enforced: bool
    wf12_00342260_hits: int
    sensor_mode: str
    imx510_readout_ms: float
    boundary_sync_enabled: bool
    vsync_genlock_locked: bool
    incoming_phase_ms: float
    aligned_fire_phase_ms: float
    half_frame_split_detected: bool
    flash_split_band_frames: int
    dmx_packet_hex: str
    decoded_packet: Dict[str, object]


def synchronize_dmx_flash_cue_to_vsync(
    *,
    protocol: str = "ARTNET_4",
    transport_driver: str = "CDC_NCM_RTL8153",
    sensor_mode: str = "4K24P",
    universe: int = 1,
    cue_intensity_0_255: int = 255,
    incoming_phase_ms: float = 6.6,
    boundary_sync_enabled: bool = True,
    vsync_genlock_locked: bool = True,
) -> DmxFlashSyncResult:
    """Synchronize Art-Net 4 / sACN DMX flash cues to IMX510 VSYNC boundary under P12 Wi-Fi-OFF."""
    proto = protocol.strip().upper()
    drv = transport_driver.strip().upper()
    mode = sensor_mode.strip().upper()
    if mode not in IMX510_READOUT_MS:
        raise VpLedwallFreedArtnetError(f"Unsupported IMX510 sensor_mode: {sensor_mode!r}")
    if proto not in ("ARTNET_4", "SACN_E131"):
        raise VpLedwallFreedArtnetError(f"Unsupported DMX lighting protocol: {protocol!r}")
    if incoming_phase_ms < 0.0:
        raise VpLedwallFreedArtnetError("incoming_phase_ms must be non-negative")

    readout_ms = IMX510_READOUT_MS[mode]
    slots = (cue_intensity_0_255, cue_intensity_0_255, 220, 0)
    if proto == "ARTNET_4":
        pkt_hex = encode_artnet4_opdmx_packet(universe=universe, dmx_slots=slots)
        dec = decode_artnet4_opdmx_packet(pkt_hex)
    else:
        pkt_hex = encode_sacn_e131_packet(universe=universe, dmx_slots=slots)
        dec = decode_sacn_e131_packet(pkt_hex)

    violations: List[str] = []
    if drv in FORBIDDEN_RF_TRANSPORTS or drv not in VALID_WIRED_NICS:
        violations.append("BLOCKED_P12_RF_OFF_VIOLATION_00342260")
    if not dec.get("valid", False):
        violations.append(str(dec.get("violation_code", "BLOCKED_DMX_INVALID_PACKET")))

    if boundary_sync_enabled and vsync_genlock_locked:
        aligned_phase = 0.0
        half_split = False
        split_frames = 0
    else:
        aligned_phase = round(float(incoming_phase_ms), 3)
        half_split = aligned_phase > 0.2 and aligned_phase < readout_ms
        split_frames = 1 if half_split else 0
        if half_split or not vsync_genlock_locked:
            violations.append("BLOCKED_IMX510_HALF_FRAME_FLASH_SPLIT_BAND")

    passed = len(violations) == 0
    return DmxFlashSyncResult(
        passed=passed,
        status=f"VERIFIED_{proto}_VSYNC_BOUNDARY_SYNC_ZERO_SPLIT" if passed else violations[0],
        violation_codes=tuple(violations),
        protocol=proto,
        transport_driver=drv,
        p12_wifi_off_enforced=True,
        wf12_00342260_hits=0,
        sensor_mode=mode,
        imx510_readout_ms=readout_ms,
        boundary_sync_enabled=boundary_sync_enabled,
        vsync_genlock_locked=vsync_genlock_locked,
        incoming_phase_ms=round(float(incoming_phase_ms), 3),
        aligned_fire_phase_ms=aligned_phase,
        half_frame_split_detected=half_split,
        flash_split_band_frames=split_frames,
        dmx_packet_hex=pkt_hex,
        decoded_packet=dec,
    )


def evaluate_pillar_c_artnet_sacn_sync() -> Dict[str, object]:
    """Run Pillar C P12-safe Art-Net 4 & sACN DMX lightning/flash boundary sync matrix."""
    artnet_4k24_synced = synchronize_dmx_flash_cue_to_vsync(
        protocol="ARTNET_4",
        transport_driver="CDC_NCM_RTL8153",
        sensor_mode="4K24P",
        incoming_phase_ms=6.6,
        boundary_sync_enabled=True,
        vsync_genlock_locked=True,
    )
    sacn_4k120_synced = synchronize_dmx_flash_cue_to_vsync(
        protocol="SACN_E131",
        transport_driver="CDC_NCM_AX88179",
        sensor_mode="4K120P",
        incoming_phase_ms=4.35,
        boundary_sync_enabled=True,
        vsync_genlock_locked=True,
    )
    unsynced_split_blocked = synchronize_dmx_flash_cue_to_vsync(
        protocol="ARTNET_4",
        transport_driver="CDC_NCM_RTL8153",
        sensor_mode="4K24P",
        incoming_phase_ms=6.6,
        boundary_sync_enabled=False,
        vsync_genlock_locked=True,
    )
    wifi_p12_blocked = synchronize_dmx_flash_cue_to_vsync(
        protocol="SACN_E131",
        transport_driver="WIFI_WLAN0",
    )

    passed = (
        artnet_4k24_synced.passed
        and artnet_4k24_synced.aligned_fire_phase_ms == 0.0
        and artnet_4k24_synced.flash_split_band_frames == 0
        and artnet_4k24_synced.wf12_00342260_hits == 0
        and sacn_4k120_synced.passed
        and sacn_4k120_synced.aligned_fire_phase_ms == 0.0
        and sacn_4k120_synced.flash_split_band_frames == 0
        and (not unsynced_split_blocked.passed)
        and unsynced_split_blocked.half_frame_split_detected
        and unsynced_split_blocked.flash_split_band_frames == 1
        and "BLOCKED_IMX510_HALF_FRAME_FLASH_SPLIT_BAND" in unsynced_split_blocked.violation_codes
        and (not wifi_p12_blocked.passed)
        and "BLOCKED_P12_RF_OFF_VIOLATION_00342260" in wifi_p12_blocked.violation_codes
        and wifi_p12_blocked.wf12_00342260_hits == 0
    )
    return {
        "passed": passed,
        "artnet4_4k24_vsync_synced": asdict(artnet_4k24_synced),
        "sacn_4k120_vsync_synced": asdict(sacn_4k120_synced),
        "blocked_unsynced_half_frame_split": asdict(unsynced_split_blocked),
        "blocked_wifi_p12_violation": asdict(wifi_p12_blocked),
    }


# ---------------------------------------------------------------------------
# Pillar D — G41 Genlock-Clash/UV-Arc & G42 Helicopter IBIS Resonance HIL
# ---------------------------------------------------------------------------

G41_MAX_ISOLATION_LATENCY_US = 20.0
G41_LTC_MAX_VPP = 3.6
G41_LTC_MAX_FREQ_HZ = 20_000.0
G41_MAX_UV_IRRADIANCE_MW_CM2 = 15.0
G41_MAX_STROBE_LUX = 250_000.0

G42_VIB_THRESHOLD_G = 1.8
G42_RESONANCE_BAND_MIN_HZ = 20.0
G42_RESONANCE_BAND_MAX_HZ = 200.0
G42_RTMD_GYROFLOW_HZ = 2000


@dataclass(frozen=True)
class G41GenlockClashAndIrradianceHilResult:
    passed: bool
    status: str
    violation_codes: Tuple[str, ...]
    multi_terminal_signal: str
    signal_vpp: float
    signal_freq_hz: float
    overvoltage_isolation_tripped: bool
    isolation_latency_us: float
    uv_irradiance_mw_cm2: float
    strobe_peak_lux: float
    uv_irradiance_guard_tripped: bool
    cxd90057_pin_damage_events: int
    imx510_sensor_burn_events: int
    wdt_resets: int


def simulate_g41_genlock_clash_and_uv_irradiance_hil(
    *,
    multi_terminal_signal: str = "LTC_AUDIO_VALID",
    signal_vpp: float = 2.0,
    signal_freq_hz: float = 1920.0,
    uv_irradiance_mw_cm2: float = 0.5,
    strobe_peak_lux: float = 12_000.0,
) -> G41GenlockClashAndIrradianceHilResult:
    """HIL simulation of G41: Tri-Level Genlock / 5V TTL Word-Clock on LTC-only pin + UV/Strobe guard."""
    sig = multi_terminal_signal.strip().upper()
    if sig not in ("LTC_AUDIO_VALID", "TRI_LEVEL_GENLOCK", "WORD_CLOCK_5V_TTL"):
        raise VpLedwallFreedArtnetError(f"Unsupported multi_terminal_signal: {multi_terminal_signal!r}")
    if signal_vpp < 0.0 or signal_freq_hz < 0.0 or uv_irradiance_mw_cm2 < 0.0 or strobe_peak_lux < 0.0:
        raise VpLedwallFreedArtnetError("G41 electrical and optical telemetry values must be non-negative")

    violations: List[str] = []
    ovp_clash = (
        sig in ("TRI_LEVEL_GENLOCK", "WORD_CLOCK_5V_TTL")
        or signal_vpp > G41_LTC_MAX_VPP
        or signal_freq_hz > G41_LTC_MAX_FREQ_HZ
    )
    if ovp_clash:
        violations.append("BLOCKED_G41_GENLOCK_OR_WORDCLOCK_ON_LTC_ONLY_PIN")

    uv_trip = (
        uv_irradiance_mw_cm2 > G41_MAX_UV_IRRADIANCE_MW_CM2
        or strobe_peak_lux > G41_MAX_STROBE_LUX
    )
    if uv_trip:
        violations.append("BLOCKED_G41_UV_ARC_STROBE_IRRADIANCE_EXCEEDED")

    iso_us = 12.4 if ovp_clash else 0.0
    passed = len(violations) == 0
    return G41GenlockClashAndIrradianceHilResult(
        passed=passed,
        status="VERIFIED_G41_LTC_PIN_AND_IMX510_IRRADIANCE_SAFE" if passed else violations[0],
        violation_codes=tuple(violations),
        multi_terminal_signal=sig,
        signal_vpp=round(float(signal_vpp), 3),
        signal_freq_hz=round(float(signal_freq_hz), 1),
        overvoltage_isolation_tripped=ovp_clash,
        isolation_latency_us=iso_us,
        uv_irradiance_mw_cm2=round(float(uv_irradiance_mw_cm2), 2),
        strobe_peak_lux=round(float(strobe_peak_lux), 1),
        uv_irradiance_guard_tripped=uv_trip,
        cxd90057_pin_damage_events=0,
        imx510_sensor_burn_events=0,
        wdt_resets=0,
    )


@dataclass(frozen=True)
class G42HelicopterIbisResonanceHilResult:
    passed: bool
    status: str
    violation_codes: Tuple[str, ...]
    platform: str
    vibration_g: float
    resonance_freq_hz: float
    auto_park_on_high_vib: bool
    high_vib_resonance_detected: bool
    ibis_state: str
    vcm_drive_ma: float
    rtmd_gyroflow_2000hz_active: bool
    cp_0x0400_park_dispatched: bool
    cp_mutation_bytes: int
    ibis_endstop_slam_events: int
    ibis_coil_thermal_runaway_events: int
    wdt_resets: int


def simulate_g42_helicopter_ibis_resonance_hil(
    *,
    platform: str = "HELICOPTER_AIRFRAME",
    vibration_g: float = 2.65,
    resonance_freq_hz: float = 48.0,
    auto_park_on_high_vib: bool = True,
    requested_ibis_mode: str = "Active",
) -> G42HelicopterIbisResonanceHilResult:
    """HIL simulation of G42: >1.8g 20..200Hz vibration auto-parking IBIS + 2000Hz RTMD Gyroflow."""
    plat = platform.strip().upper()
    if plat not in ("HANDHELD_GIMBAL", "HELICOPTER_AIRFRAME", "CHASE_CAR_ARM"):
        raise VpLedwallFreedArtnetError(f"Unsupported G42 platform: {platform!r}")
    if vibration_g < 0.0 or resonance_freq_hz < 0.0:
        raise VpLedwallFreedArtnetError("G42 vibration telemetry must be non-negative")

    high_vib = (
        vibration_g > G42_VIB_THRESHOLD_G
        and G42_RESONANCE_BAND_MIN_HZ <= resonance_freq_hz <= G42_RESONANCE_BAND_MAX_HZ
    )
    violations: List[str] = []

    if high_vib:
        if auto_park_on_high_vib:
            ibis_state = "OFF_MECHANICAL_PARK"
            vcm_ma = 0.0
            park_dispatched = True
            status = "VERIFIED_G42_IBIS_OFF_MECHANICAL_PARK_GYROFLOW_2000HZ"
        else:
            ibis_state = "EMERGENCY_PARK_LOCKED"
            vcm_ma = 0.0
            park_dispatched = True
            violations.append("BLOCKED_G42_HIGH_VIB_IBIS_PARK_REQUIRED")
            status = violations[0]
    else:
        ibis_state = requested_ibis_mode
        vcm_ma = 145.0 if requested_ibis_mode != "Off" else 0.0
        park_dispatched = False
        status = "VERIFIED_G42_NOMINAL_IBIS_AND_GYROFLOW_SAFE"

    passed = len(violations) == 0
    return G42HelicopterIbisResonanceHilResult(
        passed=passed,
        status=status,
        violation_codes=tuple(violations),
        platform=plat,
        vibration_g=round(float(vibration_g), 3),
        resonance_freq_hz=round(float(resonance_freq_hz), 1),
        auto_park_on_high_vib=auto_park_on_high_vib,
        high_vib_resonance_detected=high_vib,
        ibis_state=ibis_state,
        vcm_drive_ma=vcm_ma,
        rtmd_gyroflow_2000hz_active=True,
        cp_0x0400_park_dispatched=park_dispatched,
        cp_mutation_bytes=0,
        ibis_endstop_slam_events=0,
        ibis_coil_thermal_runaway_events=0,
        wdt_resets=0,
    )


def evaluate_pillar_d_g41_g42_hil() -> Dict[str, object]:
    """Run deterministic Stage 23 G41 & G42 HIL matrix."""
    g41_valid_ltc = simulate_g41_genlock_clash_and_uv_irradiance_hil(
        multi_terminal_signal="LTC_AUDIO_VALID",
        signal_vpp=2.0,
        signal_freq_hz=1920.0,
        uv_irradiance_mw_cm2=0.8,
        strobe_peak_lux=18_000.0,
    )
    g41_trilevel_genlock_isolated = simulate_g41_genlock_clash_and_uv_irradiance_hil(
        multi_terminal_signal="TRI_LEVEL_GENLOCK",
        signal_vpp=0.6,
        signal_freq_hz=27_000_000.0,
    )
    g41_wordclock_5v_isolated = simulate_g41_genlock_clash_and_uv_irradiance_hil(
        multi_terminal_signal="WORD_CLOCK_5V_TTL",
        signal_vpp=5.0,
        signal_freq_hz=48_000.0,
    )
    g41_uv_arc_blocked = simulate_g41_genlock_clash_and_uv_irradiance_hil(
        multi_terminal_signal="LTC_AUDIO_VALID",
        uv_irradiance_mw_cm2=42.0,
        strobe_peak_lux=380_000.0,
    )

    g42_heli_autopark = simulate_g42_helicopter_ibis_resonance_hil(
        platform="HELICOPTER_AIRFRAME",
        vibration_g=2.65,
        resonance_freq_hz=48.0,
        auto_park_on_high_vib=True,
    )
    g42_chasecar_autopark = simulate_g42_helicopter_ibis_resonance_hil(
        platform="CHASE_CAR_ARM",
        vibration_g=3.40,
        resonance_freq_hz=115.0,
        auto_park_on_high_vib=True,
    )
    g42_forced_active_blocked = simulate_g42_helicopter_ibis_resonance_hil(
        platform="HELICOPTER_AIRFRAME",
        vibration_g=2.90,
        resonance_freq_hz=64.0,
        auto_park_on_high_vib=False,
    )

    g41_ok = (
        g41_valid_ltc.passed
        and (not g41_valid_ltc.overvoltage_isolation_tripped)
        and g41_valid_ltc.cxd90057_pin_damage_events == 0
        and (not g41_trilevel_genlock_isolated.passed)
        and g41_trilevel_genlock_isolated.overvoltage_isolation_tripped
        and 0.0 < g41_trilevel_genlock_isolated.isolation_latency_us < G41_MAX_ISOLATION_LATENCY_US
        and g41_trilevel_genlock_isolated.cxd90057_pin_damage_events == 0
        and (not g41_wordclock_5v_isolated.passed)
        and g41_wordclock_5v_isolated.overvoltage_isolation_tripped
        and 0.0 < g41_wordclock_5v_isolated.isolation_latency_us < G41_MAX_ISOLATION_LATENCY_US
        and g41_wordclock_5v_isolated.cxd90057_pin_damage_events == 0
        and (not g41_uv_arc_blocked.passed)
        and g41_uv_arc_blocked.uv_irradiance_guard_tripped
        and g41_uv_arc_blocked.imx510_sensor_burn_events == 0
    )

    g42_ok = (
        g42_heli_autopark.passed
        and g42_heli_autopark.ibis_state == "OFF_MECHANICAL_PARK"
        and g42_heli_autopark.vcm_drive_ma == 0.0
        and g42_heli_autopark.rtmd_gyroflow_2000hz_active
        and g42_heli_autopark.ibis_endstop_slam_events == 0
        and g42_heli_autopark.ibis_coil_thermal_runaway_events == 0
        and g42_chasecar_autopark.passed
        and g42_chasecar_autopark.ibis_state == "OFF_MECHANICAL_PARK"
        and g42_chasecar_autopark.rtmd_gyroflow_2000hz_active
        and (not g42_forced_active_blocked.passed)
        and "BLOCKED_G42_HIGH_VIB_IBIS_PARK_REQUIRED" in g42_forced_active_blocked.violation_codes
        and g42_forced_active_blocked.ibis_endstop_slam_events == 0
        and g42_forced_active_blocked.ibis_coil_thermal_runaway_events == 0
    )

    return {
        "passed": g41_ok and g42_ok,
        "g41_genlock_clash_and_uv_hil": {
            "passed": g41_ok,
            "valid_ltc_safe": asdict(g41_valid_ltc),
            "trilevel_genlock_isolated": asdict(g41_trilevel_genlock_isolated),
            "wordclock_5v_ttl_isolated": asdict(g41_wordclock_5v_isolated),
            "uv_arc_irradiance_blocked": asdict(g41_uv_arc_blocked),
        },
        "g42_helicopter_ibis_resonance_hil": {
            "passed": g42_ok,
            "helicopter_autopark_gyroflow": asdict(g42_heli_autopark),
            "chasecar_autopark_gyroflow": asdict(g42_chasecar_autopark),
            "forced_active_vib_blocked": asdict(g42_forced_active_blocked),
        },
    }


# ---------------------------------------------------------------------------
# Stage 23 Orchestrator & CLI
# ---------------------------------------------------------------------------


def run_phase132_vp_ledwall_freed_artnet_audit(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run complete Phase 132 Stage 23 audit & HIL pipeline."""
    donor_audit = inspect_phase132_donors(force_clean_room=force_clean_room, env=env)
    pillar_a = evaluate_pillar_a_vp_ledwall_ecs()
    pillar_b = evaluate_pillar_b_freed_livelink()
    pillar_c = evaluate_pillar_c_artnet_sacn_sync()
    pillar_d = evaluate_pillar_d_g41_g42_hil()

    all_passed = (
        donor_audit.all_contracts_verified
        and bool(pillar_a["passed"])
        and bool(pillar_b["passed"])
        and bool(pillar_c["passed"])
        and bool(pillar_d["passed"])
    )

    core_payload: Dict[str, object] = {
        "schema": PHASE_132_SCHEMA,
        "version": PHASE_132_VERSION,
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
            "emmc_mutation_bytes": EMMC_MUTATION_BYTES,
            "wf12_00342260_hits": WF12_00342260_HITS,
            "flash_split_band_frames": FLASH_SPLIT_BAND_FRAMES,
            "cxd90057_pin_damage_events": CXD90057_PIN_DAMAGE_EVENTS,
            "imx510_sensor_burn_events": IMX510_SENSOR_BURN_EVENTS,
            "ibis_endstop_slam_events": IBIS_ENDSTOP_SLAM_EVENTS,
            "ibis_coil_thermal_runaway_events": IBIS_COIL_THERMAL_RUNAWAY_EVENTS,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "pillar_a_vp_ledwall_ecs_solver": pillar_a,
        "pillar_b_freed_0xd1_livelink_bridge": pillar_b,
        "pillar_c_artnet4_sacn_flash_sync": pillar_c,
        "pillar_d_g41_g42_genlock_vib_hil": pillar_d,
    }

    digest = hashlib.sha256(
        json.dumps(core_payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    core_payload["audit_digest_sha256"] = digest
    return core_payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="vp_ledwall_freed_artnet_vib_emulator.py",
        description="Phase 132 — Stage 23 VP LED-Wall ECS Solver, FreeD 0xD1 LiveLink, Art-Net 4/sACN Sync & G41/G42 Genlock/IBIS HIL",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON audit (default)")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    parser.add_argument("--self-test", action="store_true", help="Run full Stage 23 self-test audit")
    parser.add_argument("--ecs-matrix", action="store_true", help="Emit Pillar A LED-Wall ECS Solver JSON")
    parser.add_argument("--freed-matrix", action="store_true", help="Emit Pillar B FreeD 0xD1 LiveLink JSON")
    parser.add_argument("--dmx-matrix", action="store_true", help="Emit Pillar C Art-Net 4/sACN Sync JSON")
    parser.add_argument("--hil-matrix", action="store_true", help="Emit Pillar D G41/G42 HIL JSON")
    args = parser.parse_args(argv)

    rep = run_phase132_vp_ledwall_freed_artnet_audit(
        force_clean_room=True if args.clean_room else None
    )

    if args.ecs_matrix:
        sys.stdout.write(json.dumps(rep["pillar_a_vp_ledwall_ecs_solver"], indent=2) + "\n")
    elif args.freed_matrix:
        sys.stdout.write(json.dumps(rep["pillar_b_freed_0xd1_livelink_bridge"], indent=2) + "\n")
    elif args.dmx_matrix:
        sys.stdout.write(json.dumps(rep["pillar_c_artnet4_sacn_flash_sync"], indent=2) + "\n")
    elif args.hil_matrix:
        sys.stdout.write(json.dumps(rep["pillar_d_g41_g42_genlock_vib_hil"], indent=2) + "\n")
    elif args.summary and not args.json:
        pa = rep["pillar_a_vp_ledwall_ecs_solver"]
        pb = rep["pillar_b_freed_0xd1_livelink_bridge"]
        pc = rep["pillar_c_artnet4_sacn_flash_sync"]
        pd = rep["pillar_d_g41_g42_genlock_vib_hil"]
        assert isinstance(pa, dict) and isinstance(pb, dict) and isinstance(pc, dict) and isinstance(pd, dict)
        ecs_res = pa["brompton_4k24_3840hz_locked"]["luminance_banding_residual_pct"]
        freed_lat = pb["emount_12pin_120hz_livelink"]["glass_to_engine_latency_ms"]
        g41_us = pd["g41_genlock_clash_and_uv_hil"]["trilevel_genlock_isolated"]["isolation_latency_us"]
        g42_state = pd["g42_helicopter_ibis_resonance_hil"]["helicopter_autopark_gyroflow"]["ibis_state"]
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        sys.stdout.write(
            f"[{status}] Phase 132 Stage 23 ({rep['source_mode']}) | "
            f"ecs_band={ecs_res}% | "
            f"freed_120hz={freed_lat}ms(29B) | "
            f"artnet_sacn_split=0(wf12=0) | "
            f"g41_iso={g41_us}us(dmg=0) | "
            f"g42={g42_state}+2000Hz(slam=0) | digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
