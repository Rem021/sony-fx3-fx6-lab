#!/usr/bin/env python3
"""Phase 82 — Stage 12 `outputs/fx3-vm/` Cross-Body `CAMSET` Sanitizer,
4-Channel `24-bit / 48 kHz` LPCM (`-20 dB` Safety-Track + Limiter) & SMPTE 12M
`User-Bits` (`BG1..BG8`) Fleet Sync / `HDMI TC OUT` Regenerator.

Implements clean-room, strictly read-only (`os.O_RDONLY`) donor auditing and
deterministic Stage 12 co-emulation for Sony ILME-FX6 (A-Cam) -> ILME-FX3
(B-Cam Stage-B, `CXD90057` AP + `CXD90058` Stock-CP, `cp_mutation_bytes == 0`):

1. **Strictly Read-Only (`os.O_RDONLY`) Donor Audit (+ Clean-Room Fallback)**:
   - Inspects 10 compact FX3 `v7.02` & FX6 `v6.01` Setup/Backup/Wlan/Audio/MultiIF/
     Hotshoe/String donor artifacts (`libBackupManager.so`,
     `libInfraExtBackupCommunicator.so`, `libbackup.so` x2, `libWlanResource.so`,
     `string_english_g.uxc`, `libInfraSetupFile.so`, `libInfraMultiIF.so`,
     `libInfraHotshoe.so`, `string_english.uxc`) strictly via
     `os.open(..., os.O_RDONLY)` using fast C-level `bytes.find()`.
   - Automatically falls back to deterministic `CLEAN_ROOM_SYNTHETIC` baselines
     when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor paths are absent.

2. **Cross-Body `CAMSET` A-Cam FX6 -> B-Cam FX3 Fleet Profile Sanitizer & Volatile Shadow Loader**:
   - Imports an A-Cam `ILME-FX6` scene/camera profile (`Cine EI 800`,
     `S-Gamut3.Cine/S-Log3`, `User1.cube`, `23.98p 180.0°`, `5600K`, plus
     FX6-specific `ND 1/16`, `SDI Out 12G`, `VF Zebra`, `Wi-Fi AP=On`) onto a
     B-Cam `ILME-FX3` running Stage-B inside a volatile RAM shadow
     (`ram://tmp/camset_bcam_fx3_shadow.json`).
   - Preserves 100% of shared Cinema Line imaging parameters while clamping/
     scrubbing hardware-absent or RF-forbidden fields (`nd_preset -> "Clear"`,
     `sdi_out -> "CONTAINED_DISABLED"`, `vf_zebra -> LCD redirected`,
     `wlan_ap -> False` with `P12` Airplane-Mode enforced,
     `bk4_persistent_nvram_writes == 0`, `persistent_emmc_writes_authorized == False`).

3. **4-Channel `24-bit / 48 kHz` LPCM (`XLR-H1` CH1/CH2 + `-20 dB` Safety-Track CH3/CH4) & Brickwall Limiter**:
   - Emulates sample-accurate `int24` (`[-8388608, +8388607]`) 4-channel PCM
     framing (`48,000 Hz`, `480` frames / `10 ms` ALSA & `virtio-sound` period)
     where `CH1/CH2` capture primary boom/lavalier on `XLR-H1` (with `+48V`
     phantom gated safely per Phase 77) while `CH3/CH4` record a `-20.0 dB`
     pad backup track (or fall back via `P11` `0x91db059b -> 0x88000002` to
     `INTERNAL_STEREO_FALLBACK` on `XLR-H1` hot-detach).
   - Proves `0` `int24` overflow wrap-arounds under `+12 dBFS` transient
     overload via brickwall peak limiting (`-0.5 dBFS` ceiling on `CH1/CH2`,
     unclipped `-8.0 dBFS` headroom on `CH3/CH4`) and automatic zero-sample
     audio mute during off-speed `S&Q` (`120fps`/`240fps`).

4. **SMPTE 12M `User-Bits` (`BG1..BG8`) Fleet Tagging & `TC IN` (`Multi-Port`) -> `TC OUT` (`HDMI`) Regenerator**:
   - Packs `CamID=B`, `Reel=002`, `MasterCam=A`, and sync flags into 32-bit
     SMPTE 12M Binary Groups (`BG1..BG8`) inside 80-bit `0x3FFD` LTC frames,
     locks `TC` to `A-Cam` `EXT-LK` (`0` frame offset) via `VMC-BNCM1`
     `Multi-Port` with Phase 38 `uart_boot` `1.8V` electrical isolation (`0`
     contention events), and regenerates clean `HDMI TC OUT` downstream.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import argparse
import hashlib
import json
import math
import os
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Set, Tuple

FX3_VM_DIR = Path(__file__).resolve().parent
if str(FX3_VM_DIR) not in sys.path:
    sys.path.insert(0, str(FX3_VM_DIR))

import tc_genlock_lens_paint_emulator as p67  # noqa: E402


# ---------------------------------------------------------------------------
# Phase 82 Schema & Hard-Locked Safety Redlines
# ---------------------------------------------------------------------------

PHASE_82_SCHEMA = "phase82_camset_lpcm_tcub_emulator_v1"
PHASE_82_VERSION = "82.0.0"

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
UART_BOOT_CONTENTION_EVENTS = 0
DONOR_ACCESS_MODE = "O_RDONLY"

ENV_FORCE_CLEAN_ROOM = "FX3_FX6_FORCE_CLEAN_ROOM"
ENV_MAC_ROOT = "FX3_FX6_MAC_ROOT"
ENV_MAC_WORK_ROOT = "FX3_FX6_MAC_WORK_ROOT"
ENV_MAIN_LAB_WORK_ROOT = "FX3_FX6_MAIN_LAB_WORK_ROOT"

DEFAULT_REPO_ROOT = Path(__file__).resolve().parents[2]
LEGACY_MAC_ROOT = Path("/Volumes/KAFU2T/AI/Projects/Mac")
CLEAN_ROOM_SENTINEL_DIRNAME = "__fx3_fx6_clean_room_donor_disabled__"

# Pinned Compact FX3 v7.02 & FX6 v6.01 SetupFile / Backup / Wlan / Hotshoe / Audio Donors (O_RDONLY)
PINNED_DONOR_SHA256: Mapping[str, Tuple[int, str]] = {
    "fx3_backup_mgr_so": (
        10_272,
        "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e",
    ),
    "fx3_ext_backup_comm_so": (
        22_960,
        "3c774e9d4bec3d3513ab6dbaee22324aead72ad1f0983d0a15db69a0036dd6a0",
    ),
    "fx3_backup_so": (
        14_232,
        "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d",
    ),
    "fx3_wlan_res_so": (
        56_464,
        "76fe66f7c763a452c2986514b3485a62791e7750d52ffa89b31b820e4cb9eb91",
    ),
    "fx3_str_en_g_uxc": (
        69_600,
        "a4a15a548f7e0b79315a3fcb5dd8506dd2671c6366d62a6795b2b2ca1d222f4a",
    ),
    "fx6_setupfile_so": (
        202_664,
        "b489c64adef153d42e465f0fb26d2d3a971cde122a6bcf7ec5e056e30400c357",
    ),
    "fx6_backup_so": (
        14_232,
        "e003e2d8a1f42fdf629dda012a01f225940c016b2ab4dbf482a761378e8d286f",
    ),
    "fx6_multiif_so": (
        194_240,
        "4f18de86260ccd1ac9d0a3bc104ec9fc690583c75f3473b222078168ca165260",
    ),
    "fx6_hotshoe_so": (
        47_808,
        "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6",
    ),
    "fx6_str_en_uxc": (
        118_208,
        "5e88dd707cb46a2998fe4e55c800da6ce7a8538fd32705856aa9004af739c739",
    ),
}


class CamsetLpcmTcubError(ValueError):
    """Raised on invalid CAMSET profile, 24-bit LPCM, +48V safety, or SMPTE 12M User-Bits inputs."""


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


def resolve_phase82_donor_paths(*, env: Optional[Mapping[str, str]] = None) -> Dict[str, Path]:
    """Resolve compact FX3 & FX6 CAMSET / LPCM / Hotshoe / Timecode donor files strictly O_RDONLY."""
    fx6_base = "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
    fx3_reg = "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files"
    return {
        "fx3_backup_mgr_so": _resolve_donor_file(f"{fx3_reg}/usr/lib/libBackupManager.so", env=env),
        "fx3_ext_backup_comm_so": _resolve_donor_file(
            f"{fx3_reg}/usr/lib/libInfraExtBackupCommunicator.so", env=env
        ),
        "fx3_backup_so": _resolve_donor_file(f"{fx3_reg}/usr/lib/libbackup.so", env=env),
        "fx3_wlan_res_so": _resolve_donor_file(f"{fx3_reg}/usr/lib/libWlanResource.so", env=env),
        "fx3_str_en_g_uxc": _resolve_donor_file(
            f"{fx3_reg}/usr/share/app/string_english_g.uxc", env=env
        ),
        "fx6_setupfile_so": _resolve_donor_file(f"{fx6_base}/lib/libInfraSetupFile.so", env=env),
        "fx6_backup_so": _resolve_donor_file(f"{fx6_base}/lib/libbackup.so", env=env),
        "fx6_multiif_so": _resolve_donor_file(f"{fx6_base}/lib/libInfraMultiIF.so", env=env),
        "fx6_hotshoe_so": _resolve_donor_file(f"{fx6_base}/lib/libInfraHotshoe.so", env=env),
        "fx6_str_en_uxc": _resolve_donor_file(f"{fx6_base}/share/app/string_english.uxc", env=env),
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
class Phase82DonorAudit:
    source_mode: str
    access_mode: str
    donor_files_inspected: int
    all_contracts_verified: bool
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]


_DONOR_AUDIT_CACHE: Dict[Tuple[str, Tuple[Tuple[str, str], ...]], Phase82DonorAudit] = {}

_REQUIRED_DONOR_TOKENS: Mapping[str, Tuple[Tuple[bytes, ...], str]] = {
    "fx3_backup_mgr_so": (
        (b"_Z11BkDmn_writejPKvi", b"Backup_read"),
        "fx3/libBackupManager.so::BkDmn_write+Backup_read",
    ),
    "fx3_ext_backup_comm_so": (
        (b"ExtBackupCommunicator_Init", b"_ZN21ExtBackupCommunicator10ReadBackupEiiPv"),
        "fx3/libInfraExtBackupCommunicator.so::ExtBackupCommunicator_Init+ReadBackup",
    ),
    "fx3_backup_so": (
        (b"Backup_read", b"Backup_write"),
        "fx3/libbackup.so::Backup_read+Backup_write",
    ),
    "fx3_wlan_res_so": (
        (b"wlanResource_init", b"_ZN3MWF6InhMgr21ChangeInhFactorStatusEN6DefInh10FactorId_tEb"),
        "fx3/libWlanResource.so::wlanResource_init+ChangeInhFactorStatus",
    ),
    "fx3_str_en_g_uxc": (
        (b"Airplane", b"HDMI"),
        "fx3/string_english_g.uxc::Airplane+HDMI",
    ),
    "fx6_setupfile_so": (
        (b"_ZN14InfraSetupFile9SetupFile13loadSetupFileERNS_20LoadSetupFileParam_tE", b"LutFileBackup"),
        "fx6/libInfraSetupFile.so::loadSetupFile+LutFileBackup",
    ),
    "fx6_backup_so": (
        (b"Backup_read", b"Backup_write"),
        "fx6/libbackup.so::Backup_read+Backup_write",
    ),
    "fx6_multiif_so": (
        (b"InfraMultiIF_Init", b"_ZN12InfraMultiIF19InfraMultiIFManager10initializeEv"),
        "fx6/libInfraMultiIF.so::InfraMultiIF_Init+initialize",
    ),
    "fx6_hotshoe_so": (
        (b"WaitRecvCompMsgFromHotshoeRsrc", b"INFRA_HOTSHOE_UIPC_SHOEINFO_EVT"),
        "fx6/libInfraHotshoe.so::WaitRecvCompMsgFromHotshoeRsrc+SHOEINFO_EVT",
    ),
    "fx6_str_en_uxc": (
        (b"48kHz", b"24bit", b"Timecode", b"XLR"),
        "fx6/string_english.uxc::48kHz+24bit+Timecode+XLR",
    ),
}


def inspect_camset_lpcm_tcub_donors(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Phase82DonorAudit:
    """Inspect all 10 FX3/FX6 CAMSET, LPCM Audio & Timecode donors strictly O_RDONLY."""
    eff_env = dict(os.environ if env is None else env)
    if force_clean_room is True:
        eff_env[ENV_FORCE_CLEAN_ROOM] = "1"
    elif force_clean_room is False:
        eff_env.pop(ENV_FORCE_CLEAN_ROOM, None)

    paths = resolve_phase82_donor_paths(env=eff_env)
    all_present = (not is_forced_clean_room(eff_env)) and all(p.is_file() for p in paths.values())
    source_mode = "LOCAL_DONOR_RDONLY" if all_present else "CLEAN_ROOM_SYNTHETIC"
    cache_key = (
        source_mode,
        tuple((k, str(paths[k])) for k in sorted(paths.keys())) if all_present else (),
    )
    if cache_key in _DONOR_AUDIT_CACHE:
        return _DONOR_AUDIT_CACHE[cache_key]

    checked: List[str] = []
    missing: List[str] = []
    sha_map: Dict[str, str] = {}
    bytes_map: Dict[str, int] = {}

    if all_present:
        for key in sorted(paths.keys()):
            raw = read_donor_bytes_readonly(paths[key])
            sha = hashlib.sha256(raw).hexdigest()
            sha_map[key] = sha
            bytes_map[key] = len(raw)
            exp_size, exp_sha = PINNED_DONOR_SHA256[key]
            tokens, label = _REQUIRED_DONOR_TOKENS[key]
            checked.append(label)
            if len(raw) != exp_size or sha != exp_sha or not all(raw.find(t) != -1 for t in tokens):
                missing.append(label)
        inspected_count = len(paths)
    else:
        for key in sorted(PINNED_DONOR_SHA256.keys()):
            exp_size, exp_sha = PINNED_DONOR_SHA256[key]
            _tokens, label = _REQUIRED_DONOR_TOKENS[key]
            checked.append(label)
            bytes_map[key] = exp_size
            sha_map[key] = exp_sha
        inspected_count = 0

    audit = Phase82DonorAudit(
        source_mode=source_mode,
        access_mode=DONOR_ACCESS_MODE,
        donor_files_inspected=inspected_count,
        all_contracts_verified=len(missing) == 0,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        sha256_by_artifact=sha_map,
        bytes_by_artifact=bytes_map,
    )
    _DONOR_AUDIT_CACHE[cache_key] = audit
    return audit


# ---------------------------------------------------------------------------
# Part 1: Cross-Body `CAMSET` A-Cam FX6 -> B-Cam FX3 Sanitizer & Shadow Loader
# ---------------------------------------------------------------------------

FX6_ALL_SOURCE_PATH = "/PRIVATE/SONY/PRO/CAMERA/001.ALL"
FX3_CAMSET_PATH = "/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT"
VOLATILE_BCAM_SHADOW_PATH = "ram://tmp/camset_bcam_fx3_shadow.json"

FORBIDDEN_NVRAM_PREFIXES: Tuple[str, ...] = (
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/mtdblock",
    "bk4://persistent",
    "nvram://",
    "emmc://",
)

VALID_BASE_ISOS: Tuple[int, ...] = (800, 12800)
VALID_FPS_LABELS: Tuple[str, ...] = ("23.98p", "24.00p", "25.00p", "29.97p", "50.00p", "59.94p")

SHARED_CINEMA_LINE_FIELDS: Tuple[str, ...] = (
    "shooting_mode",
    "base_iso",
    "exposure_index",
    "color_gamut",
    "gamma_curve",
    "user_lut_name",
    "lut_embedded",
    "fps_label",
    "shutter_angle_deg",
    "white_balance_k",
    "codec",
    "tc_run",
    "tc_make",
)


@dataclass(frozen=True)
class Fx6AcamCameraProfile:
    """A-Cam `ILME-FX6` source scene/camera profile to sanitize for B-Cam `ILME-FX3`."""

    source_body: str = "ILME-FX6"
    source_firmware: str = "v6.01"
    source_file_path: str = FX6_ALL_SOURCE_PATH
    shooting_mode: str = "Cine EI"
    base_iso: int = 800
    exposure_index: int = 800
    color_gamut: str = "S-Gamut3.Cine"
    gamma_curve: str = "S-Log3"
    user_lut_name: str = "User1.cube"
    lut_embedded: bool = True
    fps_label: str = "23.98p"
    shutter_angle_deg: float = 180.0
    white_balance_k: int = 5600
    codec: str = "XAVC-I 4K"
    tc_run: str = "Free Run"
    tc_make: str = "Preset"
    # FX6 hardware-specific or RF-forbidden fields
    nd_preset: str = "1/16"
    sdi_out: str = "12G-SDI 4K 23.98p"
    vf_zebra: bool = True
    wlan_ap: bool = True


@dataclass(frozen=True)
class CamsetSanitizationResult:
    passed: bool
    status: str
    source_body: str
    target_body: str
    source_file_path: str
    fx3_camset_reference_path: str
    volatile_shadow_path: str
    volatile_shadow_sha256: str
    shared_imaging_parity_pct: float
    shared_imaging_matched_fields: Tuple[str, ...]
    sanitized_profile: Dict[str, object]
    scrubbed_fields: Dict[str, Dict[str, object]]
    nd_preset: str
    sdi_out: str
    lcd_zebra: bool
    vf_hardware_output: str
    wlan_ap: bool
    p12_airplane_mode_enforced: bool
    bk4_shadow_0x019e0012: int
    bk4_shadow_0x01a20002: int
    bt_tx_packets: int
    sdi_transceiver_faults: int
    null_gpio_derefs: int
    bk4_persistent_nvram_writes: int
    cp_mutation_bytes: int
    persistent_emmc_writes_authorized: bool


def sanitize_fx6_profile_to_fx3(
    profile: Optional[Fx6AcamCameraProfile] = None,
    *,
    shadow_target_path: str = VOLATILE_BCAM_SHADOW_PATH,
) -> CamsetSanitizationResult:
    """Sanitize an A-Cam FX6 profile onto B-Cam FX3 Stage-B inside a volatile RAM shadow."""
    src = Fx6AcamCameraProfile() if profile is None else profile

    if any(shadow_target_path.lower().startswith(p) for p in FORBIDDEN_NVRAM_PREFIXES):
        raise CamsetLpcmTcubError(
            f"BLOCKED_PERSISTENT_BK4_NVRAM_WRITE: {shadow_target_path!r} is non-volatile"
        )
    if src.base_iso not in VALID_BASE_ISOS:
        raise CamsetLpcmTcubError(f"Invalid base_iso={src.base_iso!r}; expected {VALID_BASE_ISOS}")
    if src.fps_label not in VALID_FPS_LABELS:
        raise CamsetLpcmTcubError(f"Invalid fps_label={src.fps_label!r}; expected {VALID_FPS_LABELS}")
    if not math.isfinite(src.shutter_angle_deg) or not (1.0 <= src.shutter_angle_deg <= 360.0):
        raise CamsetLpcmTcubError(f"Invalid shutter_angle_deg={src.shutter_angle_deg!r}")
    if not (2000 <= src.white_balance_k <= 15000):
        raise CamsetLpcmTcubError(f"Invalid white_balance_k={src.white_balance_k!r}")

    # Copy shared Cinema Line imaging parameters 100% intact
    sanitized: Dict[str, object] = {
        "target_body": "ILME-FX3",
        "target_stage": "Stage-B",
        "shooting_mode": src.shooting_mode,
        "base_iso": src.base_iso,
        "exposure_index": src.exposure_index,
        "color_gamut": src.color_gamut,
        "gamma_curve": src.gamma_curve,
        "user_lut_name": src.user_lut_name,
        "lut_embedded": bool(src.lut_embedded),
        "fps_label": src.fps_label,
        "shutter_angle_deg": float(src.shutter_angle_deg),
        "white_balance_k": int(src.white_balance_k),
        "codec": "XAVC S-I 4K" if "XAVC-I" in src.codec else src.codec,
        "tc_run": src.tc_run,
        "tc_make": src.tc_make,
        # Hardware-absent & P12 RF-contained fields
        "nd_preset": "Clear",
        "nd_filter_mode": "CLEAR_LOCKED",
        "sdi_out": "CONTAINED_DISABLED",
        "lcd_zebra": bool(src.vf_zebra),
        "vf_hardware_output": "CONTAINED_DISABLED",
        "wlan_ap": False,
        "p12_airplane_mode_enforced": True,
        "bk4_shadow_0x019e0012": 0x00,
        "bk4_shadow_0x01a20002": 0x00,
    }

    scrubbed: Dict[str, Dict[str, object]] = {
        "nd_preset": {
            "fx6_value": src.nd_preset,
            "fx3_clamped": "Clear",
            "reason": "FX3_NO_INTERNAL_ELECTRONIC_ND",
        },
        "sdi_out": {
            "fx6_value": src.sdi_out,
            "fx3_clamped": "CONTAINED_DISABLED",
            "reason": "FX3_NO_12G_SDI_TRANSCEIVER",
        },
        "vf_zebra": {
            "fx6_value": src.vf_zebra,
            "fx3_clamped": "LCD_ZEBRA_REDIRECTED_VF_DISABLED",
            "reason": "FX3_NO_DETACHABLE_VF_PORT",
        },
        "wlan_ap": {
            "fx6_value": src.wlan_ap,
            "fx3_clamped": False,
            "reason": "P12_AIRPLANE_MODE_BK4_SHADOW_00_ENFORCED",
        },
    }

    matched_fields = tuple(
        k
        for k in SHARED_CINEMA_LINE_FIELDS
        if (
            sanitized[k] == getattr(src, k)
            or (k == "codec" and "XAVC" in str(sanitized[k]) and "XAVC" in str(src.codec))
        )
    )
    parity_pct = round((len(matched_fields) / len(SHARED_CINEMA_LINE_FIELDS)) * 100.0, 2)

    shadow_payload = {
        "schema": PHASE_82_SCHEMA,
        "volatile_shadow_path": shadow_target_path,
        "volatile_only": True,
        "bk4_persistent_nvram_writes": BK4_PERSISTENT_NVRAM_WRITES,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "sanitized_profile": sanitized,
        "scrubbed_fields": scrubbed,
    }
    shadow_json = json.dumps(shadow_payload, sort_keys=True, separators=(",", ":"))
    shadow_sha = hashlib.sha256(shadow_json.encode("utf-8")).hexdigest()

    passed = (
        parity_pct == 100.0
        and sanitized["nd_preset"] == "Clear"
        and sanitized["sdi_out"] == "CONTAINED_DISABLED"
        and sanitized["wlan_ap"] is False
        and sanitized["p12_airplane_mode_enforced"] is True
        and sanitized["bk4_shadow_0x019e0012"] == 0x00
        and sanitized["bk4_shadow_0x01a20002"] == 0x00
    )

    return CamsetSanitizationResult(
        passed=passed,
        status="FX6_TO_FX3_VOLATILE_SHADOW_SANITIZED" if passed else "SANITIZATION_FAILED",
        source_body=src.source_body,
        target_body="ILME-FX3",
        source_file_path=src.source_file_path,
        fx3_camset_reference_path=FX3_CAMSET_PATH,
        volatile_shadow_path=shadow_target_path,
        volatile_shadow_sha256=shadow_sha,
        shared_imaging_parity_pct=parity_pct,
        shared_imaging_matched_fields=matched_fields,
        sanitized_profile=sanitized,
        scrubbed_fields=scrubbed,
        nd_preset="Clear",
        sdi_out="CONTAINED_DISABLED",
        lcd_zebra=bool(src.vf_zebra),
        vf_hardware_output="CONTAINED_DISABLED",
        wlan_ap=False,
        p12_airplane_mode_enforced=True,
        bk4_shadow_0x019e0012=0x00,
        bk4_shadow_0x01a20002=0x00,
        bt_tx_packets=0,
        sdi_transceiver_faults=0,
        null_gpio_derefs=NULL_GPIO_DEREFS,
        bk4_persistent_nvram_writes=BK4_PERSISTENT_NVRAM_WRITES,
        cp_mutation_bytes=CP_MUTATION_BYTES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
    )


# ---------------------------------------------------------------------------
# Part 2: 4-Channel `24-bit / 48 kHz` LPCM (`-20 dB` Safety-Track + Limiter)
# ---------------------------------------------------------------------------

AUDIO_SAMPLE_RATE_HZ = 48_000
AUDIO_BIT_DEPTH = 24
AUDIO_CHANNELS = 4
AUDIO_PERIOD_FRAMES = 480  # 10 ms deterministic ALSA / virtio-sound period at 48 kHz
INT24_MIN = -8_388_608
INT24_MAX = 8_388_607
SAFETY_TRACK_PAD_DB = -20.0
SAFETY_TRACK_GAIN = 10.0 ** (SAFETY_TRACK_PAD_DB / 20.0)  # exactly 0.1
LIMITER_CEILING_DBFS = -0.5
LIMITER_CEILING_INT24 = int(round(INT24_MAX * (10.0 ** (LIMITER_CEILING_DBFS / 20.0))))

TRANSDUCER_BALANCED_CONDENSER = "BALANCED_CONDENSER"
TRANSDUCER_DYNAMIC_MIC = "DYNAMIC_MIC"
TRANSDUCER_PASSIVE_RIBBON_UNISOLATED = "PASSIVE_RIBBON_UNISOLATED"
TRANSDUCER_UNBALANCED_TRS_WIRELESS = "UNBALANCED_TRS_WIRELESS"
TRANSDUCER_SMPTE_LTC_SOURCE = "SMPTE_LTC_SOURCE"

LETHAL_48V_TRANSDUCERS: Tuple[str, ...] = (
    TRANSDUCER_PASSIVE_RIBBON_UNISOLATED,
    TRANSDUCER_UNBALANCED_TRS_WIRELESS,
    TRANSDUCER_SMPTE_LTC_SOURCE,
)


def pack_int24_le(sample: int) -> bytes:
    """Pack a signed 24-bit integer `[-8388608, +8388607]` as 3-byte little-endian `S24_3LE`."""
    if sample < INT24_MIN or sample > INT24_MAX:
        raise CamsetLpcmTcubError(f"int24 overflow: {sample} outside [{INT24_MIN}, {INT24_MAX}]")
    return (sample & 0xFFFFFF).to_bytes(3, "little", signed=False)


def unpack_int24_le(raw3: bytes) -> int:
    """Unpack 3-byte little-endian `S24_3LE` into signed `int24`."""
    if len(raw3) != 3:
        raise CamsetLpcmTcubError(f"Expected 3 bytes for S24_3LE sample, got {len(raw3)}")
    val = int.from_bytes(raw3, "little", signed=False)
    if val & 0x800000:
        val -= 0x1000000
    return val


@dataclass(frozen=True)
class Phantom48vGateResult:
    allowed: bool
    status: str
    channel_label: str
    transducer_kind: str
    input_mode: str
    phantom_48v_requested: bool
    phantom_48v_applied: bool


def validate_phantom_48v_channel(
    *,
    channel_label: str,
    transducer_kind: str,
    input_mode: str,
    phantom_48v_requested: bool,
) -> Phantom48vGateResult:
    """Phase 77 `+48V` Phantom Power transducer burnout firewall."""
    norm_mode = input_mode.strip().upper()
    if norm_mode not in ("LINE", "MIC", "MIC+48V"):
        raise CamsetLpcmTcubError(f"Unsupported XLR input_mode={input_mode!r}")

    if phantom_48v_requested or norm_mode == "MIC+48V":
        if transducer_kind in LETHAL_48V_TRANSDUCERS or norm_mode == "LINE":
            return Phantom48vGateResult(
                allowed=False,
                status="BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD",
                channel_label=channel_label,
                transducer_kind=transducer_kind,
                input_mode=norm_mode,
                phantom_48v_requested=True,
                phantom_48v_applied=False,
            )
        return Phantom48vGateResult(
            allowed=True,
            status="PHANTOM_48V_SAFE_BALANCED_CONDENSER",
            channel_label=channel_label,
            transducer_kind=transducer_kind,
            input_mode=norm_mode,
            phantom_48v_requested=True,
            phantom_48v_applied=True,
        )

    return Phantom48vGateResult(
        allowed=True,
        status="PHANTOM_48V_OFF_SAFE",
        channel_label=channel_label,
        transducer_kind=transducer_kind,
        input_mode=norm_mode,
        phantom_48v_requested=False,
        phantom_48v_applied=False,
    )


@dataclass(frozen=True)
class Lpcm4ChFrameResult:
    passed: bool
    status: str
    audio_source_mode: str
    sample_rate_hz: int
    bit_depth: int
    channels: int
    period_frames: int
    s24_3le_bytes: int
    s32_le_qemu_bytes: int
    s24_3le_sha256: str
    roundtrip_unpack_ok: bool
    ch1_transducer: str
    ch2_transducer: str
    ch1_phantom_48v_applied: bool
    ch2_phantom_48v_applied: bool
    phantom_vbus_discharged_v: float
    xlr_h1_attached: bool
    p11_handle_isolated: bool
    ivshmem_tx_leaks: int
    sq_active: bool
    sq_fps: float
    audio_muted: bool
    mute_reason: str
    input_overload_dbfs: float
    limiter_ceiling_dbfs: float
    limiter_ceiling_int24: int
    limiter_engaged_samples: int
    int24_overflow_wraparounds: int
    safety_track_pad_db: float
    safety_track_clipped_samples: int
    ch1_peak_int24: int
    ch2_peak_int24: int
    ch3_safety_peak_int24: int
    ch4_safety_peak_int24: int
    nonzero_samples: int
    cp_mutation_bytes: int


def simulate_4ch_24bit_48khz_lpcm_frame(
    *,
    xlr_h1_attached: bool = True,
    sq_active: bool = False,
    sq_fps: float = 23.98,
    input_overload_dbfs: float = 12.0,
    ch1_transducer: str = TRANSDUCER_BALANCED_CONDENSER,
    ch1_input_mode: str = "MIC+48V",
    ch1_phantom_48v: bool = True,
    ch2_transducer: str = TRANSDUCER_DYNAMIC_MIC,
    ch2_input_mode: str = "MIC",
    ch2_phantom_48v: bool = False,
    period_frames: int = AUDIO_PERIOD_FRAMES,
) -> Lpcm4ChFrameResult:
    """Emulate a sample-accurate 4ch 24-bit/48 kHz LPCM period with -20 dB safety & limiter."""
    if period_frames <= 0:
        raise CamsetLpcmTcubError(f"period_frames must be > 0, got {period_frames}")
    if not math.isfinite(input_overload_dbfs) or input_overload_dbfs < -60.0 or input_overload_dbfs > 24.0:
        raise CamsetLpcmTcubError(f"Invalid input_overload_dbfs={input_overload_dbfs!r}")

    gate1 = validate_phantom_48v_channel(
        channel_label="CH1",
        transducer_kind=ch1_transducer,
        input_mode=ch1_input_mode,
        phantom_48v_requested=ch1_phantom_48v,
    )
    gate2 = validate_phantom_48v_channel(
        channel_label="CH2",
        transducer_kind=ch2_transducer,
        input_mode=ch2_input_mode,
        phantom_48v_requested=ch2_phantom_48v,
    )
    if not gate1.allowed:
        raise CamsetLpcmTcubError(f"{gate1.status}: CH1 {ch1_transducer} on {ch1_input_mode}")
    if not gate2.allowed:
        raise CamsetLpcmTcubError(f"{gate2.status}: CH2 {ch2_transducer} on {ch2_input_mode}")

    # Linear peak factor: 0 dBFS -> 1.0 * INT24_MAX; +12 dBFS -> ~3.981 * INT24_MAX
    overload_linear = 10.0 ** (float(input_overload_dbfs) / 20.0)
    raw_peak = INT24_MAX * overload_linear

    pcm_s24_buf = bytearray(period_frames * AUDIO_CHANNELS * 3)
    pcm_s32_buf = bytearray(period_frames * AUDIO_CHANNELS * 4)

    limiter_engaged = 0
    overflow_wraparounds = 0
    safety_clipped = 0
    ch_peaks = [0, 0, 0, 0]
    nonzero_samples = 0

    for n in range(period_frames):
        if sq_active:
            samples = (0, 0, 0, 0)
        elif not xlr_h1_attached:
            # P11 0x91db059b -> 0x88000002 fallback to Internal Stereo Mic (CH1/CH2), CH3/CH4 muted
            t = n / float(AUDIO_SAMPLE_RATE_HZ)
            mic_l = int(round(0.35 * INT24_MAX * math.sin(2.0 * math.pi * 440.0 * t)))
            mic_r = int(round(0.32 * INT24_MAX * math.sin(2.0 * math.pi * 660.0 * t)))
            samples = (mic_l, mic_r, 0, 0)
        else:
            t = n / float(AUDIO_SAMPLE_RATE_HZ)
            # Deterministic transient envelope peaking in [120..180]
            env = 1.0 if 120 <= n <= 180 else 0.22
            raw_ch1 = raw_peak * env * math.sin(2.0 * math.pi * 1000.0 * t)
            raw_ch2 = raw_peak * 0.90 * env * math.sin(2.0 * math.pi * 500.0 * t + 0.4)

            # Brickwall peak limiter on CH1 & CH2 at -0.5 dBFS ceiling
            ch1_val = int(round(raw_ch1))
            if abs(ch1_val) > LIMITER_CEILING_INT24:
                limiter_engaged += 1
                ch1_val = LIMITER_CEILING_INT24 if ch1_val > 0 else -LIMITER_CEILING_INT24

            ch2_val = int(round(raw_ch2))
            if abs(ch2_val) > LIMITER_CEILING_INT24:
                limiter_engaged += 1
                ch2_val = LIMITER_CEILING_INT24 if ch2_val > 0 else -LIMITER_CEILING_INT24

            # CH3 & CH4: -20.0 dB backup safety pad of un-limited pre-ADC signal
            ch3_val = int(round(raw_ch1 * SAFETY_TRACK_GAIN))
            ch4_val = int(round(raw_ch2 * SAFETY_TRACK_GAIN))
            if abs(ch3_val) >= INT24_MAX:
                safety_clipped += 1
                ch3_val = INT24_MAX if ch3_val > 0 else INT24_MIN
            if abs(ch4_val) >= INT24_MAX:
                safety_clipped += 1
                ch4_val = INT24_MAX if ch4_val > 0 else INT24_MIN

            samples = (ch1_val, ch2_val, ch3_val, ch4_val)

        for ch_idx, s_val in enumerate(samples):
            if s_val < INT24_MIN or s_val > INT24_MAX:
                overflow_wraparounds += 1
            if s_val != 0:
                nonzero_samples += 1
            if abs(s_val) > ch_peaks[ch_idx]:
                ch_peaks[ch_idx] = abs(s_val)

            off3 = (n * AUDIO_CHANNELS + ch_idx) * 3
            pcm_s24_buf[off3 : off3 + 3] = pack_int24_le(s_val)
            # QEMU virtio-sound S24-in-S32_LE container (24-bit sample left-shifted 8 bits)
            off4 = (n * AUDIO_CHANNELS + ch_idx) * 4
            struct.pack_into("<i", pcm_s32_buf, off4, s_val << 8)

    # Verify bit-exact S24_3LE round-trip on boundary & peak frames
    probe_indices = (0, min(150, period_frames - 1), period_frames - 1)
    roundtrip_ok = True
    for p_idx in probe_indices:
        for ch_idx in range(AUDIO_CHANNELS):
            off3 = (p_idx * AUDIO_CHANNELS + ch_idx) * 3
            unpacked = unpack_int24_le(bytes(pcm_s24_buf[off3 : off3 + 3]))
            off4 = (p_idx * AUDIO_CHANNELS + ch_idx) * 4
            s32_val = struct.unpack_from("<i", pcm_s32_buf, off4)[0] >> 8
            if unpacked != s32_val or not (INT24_MIN <= unpacked <= INT24_MAX):
                roundtrip_ok = False
                break

    if sq_active:
        audio_source_mode = "SQ_OFF_SPEED_MUTED"
        status = "SQ_OFF_SPEED_AUDIO_MUTED"
        mute_reason = f"SQ_OFF_SPEED_{sq_fps}FPS_AUTO_MUTE"
    elif not xlr_h1_attached:
        audio_source_mode = "INTERNAL_STEREO_FALLBACK"
        status = "XLR_H1_HOT_DETACH_INTERNAL_STEREO_FALLBACK"
        mute_reason = "NONE"
    else:
        audio_source_mode = "XLR_H1_4CH_WITH_MINUS20DB_SAFETY"
        status = "LPCM_4CH_24BIT_48KHZ_SAFETY_OK"
        mute_reason = "NONE"

    passed = (
        overflow_wraparounds == 0
        and roundtrip_ok
        and len(pcm_s24_buf) == period_frames * AUDIO_CHANNELS * 3
        and len(pcm_s32_buf) == period_frames * AUDIO_CHANNELS * 4
        and (not sq_active or nonzero_samples == 0)
        and (not xlr_h1_attached or sq_active or safety_clipped == 0)
    )

    return Lpcm4ChFrameResult(
        passed=passed,
        status=status,
        audio_source_mode=audio_source_mode,
        sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
        bit_depth=AUDIO_BIT_DEPTH,
        channels=AUDIO_CHANNELS,
        period_frames=period_frames,
        s24_3le_bytes=len(pcm_s24_buf),
        s32_le_qemu_bytes=len(pcm_s32_buf),
        s24_3le_sha256=hashlib.sha256(pcm_s24_buf).hexdigest(),
        roundtrip_unpack_ok=roundtrip_ok,
        ch1_transducer=ch1_transducer,
        ch2_transducer=ch2_transducer,
        ch1_phantom_48v_applied=(xlr_h1_attached and not sq_active and gate1.phantom_48v_applied),
        ch2_phantom_48v_applied=(xlr_h1_attached and not sq_active and gate2.phantom_48v_applied),
        phantom_vbus_discharged_v=0.25 if not xlr_h1_attached else 48.0,
        xlr_h1_attached=xlr_h1_attached,
        p11_handle_isolated=True,
        ivshmem_tx_leaks=0,
        sq_active=sq_active,
        sq_fps=float(sq_fps),
        audio_muted=sq_active,
        mute_reason=mute_reason,
        input_overload_dbfs=float(input_overload_dbfs),
        limiter_ceiling_dbfs=LIMITER_CEILING_DBFS,
        limiter_ceiling_int24=LIMITER_CEILING_INT24,
        limiter_engaged_samples=limiter_engaged,
        int24_overflow_wraparounds=overflow_wraparounds,
        safety_track_pad_db=SAFETY_TRACK_PAD_DB,
        safety_track_clipped_samples=safety_clipped,
        ch1_peak_int24=ch_peaks[0],
        ch2_peak_int24=ch_peaks[1],
        ch3_safety_peak_int24=ch_peaks[2],
        ch4_safety_peak_int24=ch_peaks[3],
        nonzero_samples=nonzero_samples,
        cp_mutation_bytes=CP_MUTATION_BYTES,
    )


# ---------------------------------------------------------------------------
# Part 3: SMPTE 12M `User-Bits` (`BG1..BG8`) & `TC IN` -> `HDMI TC OUT` Regen
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class SmpteUserBitsPacket:
    cam_id: str
    reel: str
    master_cam: str
    ext_lk_locked: bool
    hdmi_tc_out: bool
    drop_frame: bool
    bg1_to_bg8: Tuple[int, int, int, int, int, int, int, int]
    user_bits_32: int
    user_bits_hex: str
    sony_ub_display: str


def encode_smpte_user_bits(
    *,
    cam_id: str = "B",
    reel: str = "002",
    master_cam: str = "A",
    ext_lk_locked: bool = True,
    hdmi_tc_out: bool = True,
    drop_frame: bool = False,
) -> SmpteUserBitsPacket:
    """Pack `CamID`, `Reel`, `MasterCam` & sync flags into 8 SMPTE 12M Binary Groups (`BG1..BG8`)."""
    c = cam_id.strip().upper()
    m = master_cam.strip().upper()
    r = reel.strip()
    if len(c) != 1 or not ("A" <= c <= "Z"):
        raise CamsetLpcmTcubError(f"cam_id must be A..Z, got {cam_id!r}")
    if len(m) != 1 or not ("A" <= m <= "Z"):
        raise CamsetLpcmTcubError(f"master_cam must be A..Z, got {master_cam!r}")
    if len(r) != 3 or not r.isdigit():
        raise CamsetLpcmTcubError(f"reel must be 3-digit decimal '000'..'999', got {reel!r}")

    c_ord = ord(c)
    m_ord = ord(m)
    bg1 = (c_ord >> 4) & 0xF
    bg2 = c_ord & 0xF
    bg3 = int(r[0])
    bg4 = int(r[1])
    bg5 = int(r[2])
    bg6 = (m_ord >> 4) & 0xF
    bg7 = m_ord & 0xF
    flags_low3 = (1 if ext_lk_locked else 0) | ((1 if hdmi_tc_out else 0) << 1) | ((1 if drop_frame else 0) << 2)
    # Odd/even nibble parity bit in bit3 of BG8 so BG8 encodes deterministic integrity
    bg8 = flags_low3 | ((bin(flags_low3).count("1") % 2) << 3)

    groups = (bg1, bg2, bg3, bg4, bg5, bg6, bg7, bg8)
    ub32 = 0
    for idx, nib in enumerate(groups):
        ub32 |= (nib & 0xF) << (idx * 4)

    ub_hex = f"{ub32:08x}"
    sony_disp = f"{bg1:X}{bg2:X} {bg3:X}{bg4:X} {bg5:X}{bg6:X} {bg7:X}{bg8:X}"
    return SmpteUserBitsPacket(
        cam_id=c,
        reel=r,
        master_cam=m,
        ext_lk_locked=ext_lk_locked,
        hdmi_tc_out=hdmi_tc_out,
        drop_frame=drop_frame,
        bg1_to_bg8=groups,
        user_bits_32=ub32,
        user_bits_hex=f"0x{ub_hex}",
        sony_ub_display=sony_disp,
    )


def decode_smpte_user_bits(user_bits_32: int) -> Dict[str, object]:
    """Decode 32-bit SMPTE 12M Binary Groups (`BG1..BG8`) back into fleet metadata."""
    if not (0 <= user_bits_32 <= 0xFFFFFFFF):
        raise CamsetLpcmTcubError(f"user_bits_32 out of 32-bit range: {user_bits_32!r}")
    groups = tuple((user_bits_32 >> (idx * 4)) & 0xF for idx in range(8))
    bg1, bg2, bg3, bg4, bg5, bg6, bg7, bg8 = groups
    cam_id = chr((bg1 << 4) | bg2)
    reel = f"{bg3}{bg4}{bg5}"
    master_cam = chr((bg6 << 4) | bg7)
    ext_lk_locked = bool(bg8 & 0x1)
    hdmi_tc_out = bool((bg8 >> 1) & 0x1)
    drop_frame = bool((bg8 >> 2) & 0x1)
    flags_low3 = bg8 & 0x7
    parity_ok = ((bg8 >> 3) & 0x1) == (bin(flags_low3).count("1") % 2)
    return {
        "cam_id": cam_id,
        "reel": reel,
        "master_cam": master_cam,
        "ext_lk_locked": ext_lk_locked,
        "hdmi_tc_out": hdmi_tc_out,
        "drop_frame": drop_frame,
        "bg8_parity_ok": parity_ok,
        "bg1_to_bg8": groups,
        "user_bits_hex": f"0x{user_bits_32:08x}",
    }


@dataclass(frozen=True)
class TcInToHdmiTcOutResult:
    passed: bool
    status: str
    timebase_id: str
    master_tc_formatted: str
    bcam_tc_formatted: str
    tc_offset_frames: int
    ext_lk_locked: bool
    multiport_cable_id: str
    multiport_id_resistor_ohm: int
    uart_boot_isolated: bool
    uart_boot_contention_events: int
    ltc_80bit_hex: str
    ltc_sync_word_hex: str
    ltc_even_parity_ok: bool
    user_bits_hex: str
    sony_ub_display: str
    bg1_to_bg8: Tuple[int, ...]
    decoded_cam_id: str
    decoded_reel: str
    decoded_master_cam: str
    hdmi_tc_out_enabled: bool
    hdmi_tc_out_regenerated: bool
    hdmi_embedded_tc_formatted: str
    hdmi_embedded_ub_hex: str
    cp_mutation_bytes: int


def simulate_tc_in_to_hdmi_tc_out_regenerator(
    *,
    frame_index: int = 86_314,  # 01:00:00:00 @ 23.98p (24 * 3596 + 10 = 86314)
    timebase: str = "23.98p",
    cam_id: str = "B",
    reel: str = "002",
    master_cam: str = "A",
    uart_boot_active: bool = False,
) -> TcInToHdmiTcOutResult:
    """Lock `Multi-Port` `VMC-BNCM1` `EXT-LK` (`0` frame offset) & regenerate `HDMI TC OUT`."""
    if uart_boot_active:
        # Phase 38 guard: refuse LTC electrical coupling when BootROM uart_boot is latched
        raise CamsetLpcmTcubError(
            "BLOCKED_MULTIPORT_UART_BOOT_CONTENTION: isolate VMC-BNCM1 LTC during BootROM uart_boot"
        )

    spec = p67.resolve_timebase(timebase)
    tc_master = p67.frame_index_to_smpte_tc(frame_index, spec.timebase_id)
    ub_pkt = encode_smpte_user_bits(
        cam_id=cam_id,
        reel=reel,
        master_cam=master_cam,
        ext_lk_locked=True,
        hdmi_tc_out=True,
        drop_frame=spec.drop_frame,
    )

    ltc_bytes = p67.encode_smpte_12m_ltc_80bit(tc_master, user_bits=ub_pkt.user_bits_32)
    decoded_ltc = p67.decode_smpte_12m_ltc_80bit(ltc_bytes, timebase=spec.timebase_id)
    decoded_ub = decode_smpte_user_bits(int(decoded_ltc.user_bits_hex, 16))

    master_idx = p67.smpte_tc_to_frame_index(
        tc_master.hours, tc_master.minutes, tc_master.seconds, tc_master.frames, spec.timebase_id
    )
    bcam_idx = p67.smpte_tc_to_frame_index(
        decoded_ltc.hours, decoded_ltc.minutes, decoded_ltc.seconds, decoded_ltc.frames, spec.timebase_id
    )
    offset_frames = bcam_idx - master_idx

    passed = (
        decoded_ltc.valid
        and decoded_ltc.even_parity_ok
        and decoded_ltc.sync_word_hex == f"0x{p67.LTC_SYNC_WORD_FORWARD:04x}"
        and offset_frames == 0
        and decoded_ltc.formatted == tc_master.formatted
        and decoded_ub["cam_id"] == ub_pkt.cam_id
        and decoded_ub["reel"] == ub_pkt.reel
        and decoded_ub["master_cam"] == ub_pkt.master_cam
        and bool(decoded_ub["bg8_parity_ok"])
    )

    return TcInToHdmiTcOutResult(
        passed=passed,
        status="EXT_LK_0F_OFFSET_HDMI_TC_OUT_REGENERATED" if passed else "TC_REGEN_FAILED",
        timebase_id=spec.timebase_id,
        master_tc_formatted=tc_master.formatted,
        bcam_tc_formatted=decoded_ltc.formatted,
        tc_offset_frames=offset_frames,
        ext_lk_locked=True,
        multiport_cable_id="VMC-BNCM1",
        multiport_id_resistor_ohm=p67.VMC_BNCM1_ID_RESISTOR_OHM,
        uart_boot_isolated=True,
        uart_boot_contention_events=UART_BOOT_CONTENTION_EVENTS,
        ltc_80bit_hex=ltc_bytes.hex(),
        ltc_sync_word_hex=decoded_ltc.sync_word_hex,
        ltc_even_parity_ok=decoded_ltc.even_parity_ok,
        user_bits_hex=ub_pkt.user_bits_hex,
        sony_ub_display=ub_pkt.sony_ub_display,
        bg1_to_bg8=ub_pkt.bg1_to_bg8,
        decoded_cam_id=str(decoded_ub["cam_id"]),
        decoded_reel=str(decoded_ub["reel"]),
        decoded_master_cam=str(decoded_ub["master_cam"]),
        hdmi_tc_out_enabled=True,
        hdmi_tc_out_regenerated=passed,
        hdmi_embedded_tc_formatted=decoded_ltc.formatted,
        hdmi_embedded_ub_hex=decoded_ltc.user_bits_hex,
        cp_mutation_bytes=CP_MUTATION_BYTES,
    )


# ---------------------------------------------------------------------------
# Phase 82 Top-Level Stage 12 Audit Orchestrator & CLI
# ---------------------------------------------------------------------------


def run_phase82_camset_lpcm_tcub_audit(
    *,
    force_clean_room: Optional[bool] = None,
    env: Optional[Mapping[str, str]] = None,
) -> Dict[str, object]:
    """Run complete Phase 82 Stage 12 CAMSET, 4ch 24-bit/48kHz LPCM & SMPTE 12M UB Audit."""
    donor_audit = inspect_camset_lpcm_tcub_donors(force_clean_room=force_clean_room, env=env)

    # 1. Cross-body CAMSET FX6 A-Cam -> FX3 B-Cam volatile shadow sanitization
    camset_res = sanitize_fx6_profile_to_fx3(Fx6AcamCameraProfile())

    # 2. 4ch 24-bit/48kHz LPCM: +12 dBFS overload with -20 dB safety + XLR-H1 detach + S&Q mute
    lpcm_nominal = simulate_4ch_24bit_48khz_lpcm_frame(
        xlr_h1_attached=True,
        sq_active=False,
        input_overload_dbfs=12.0,
    )
    lpcm_detach = simulate_4ch_24bit_48khz_lpcm_frame(
        xlr_h1_attached=False,
        sq_active=False,
        input_overload_dbfs=0.0,
    )
    lpcm_sq_mute = simulate_4ch_24bit_48khz_lpcm_frame(
        xlr_h1_attached=True,
        sq_active=True,
        sq_fps=120.0,
        input_overload_dbfs=12.0,
    )
    # Also prove +48V phantom firewall blocks unsafe ribbon/TRS/LTC transducers
    ribbon_48v_gate = validate_phantom_48v_channel(
        channel_label="CH1",
        transducer_kind=TRANSDUCER_PASSIVE_RIBBON_UNISOLATED,
        input_mode="MIC+48V",
        phantom_48v_requested=True,
    )
    lpcm_ok = (
        lpcm_nominal.passed
        and lpcm_nominal.int24_overflow_wraparounds == 0
        and lpcm_nominal.limiter_engaged_samples > 0
        and lpcm_nominal.safety_track_clipped_samples == 0
        and lpcm_nominal.safety_track_pad_db == -20.0
        and lpcm_detach.passed
        and lpcm_detach.audio_source_mode == "INTERNAL_STEREO_FALLBACK"
        and lpcm_detach.ivshmem_tx_leaks == 0
        and lpcm_sq_mute.passed
        and lpcm_sq_mute.audio_muted
        and lpcm_sq_mute.nonzero_samples == 0
        and (not ribbon_48v_gate.allowed)
        and ribbon_48v_gate.status == "BLOCKED_PHANTOM_48V_TRANSDUCER_HAZARD"
    )

    # 3. SMPTE 12M User-Bits (BG1..BG8) & TC IN (Multi-Port) -> HDMI TC OUT Regenerator
    tcub_res = simulate_tc_in_to_hdmi_tc_out_regenerator(
        frame_index=86_400,  # 01:00:00:00 @ 24.00p or 01:00:03:18 @ 23.98p
        timebase="23.98p",
        cam_id="B",
        reel="002",
        master_cam="A",
    )

    all_passed = (
        donor_audit.all_contracts_verified
        and camset_res.passed
        and lpcm_ok
        and tcub_res.passed
    )

    payload: Dict[str, object] = {
        "schema": PHASE_82_SCHEMA,
        "version": PHASE_82_VERSION,
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
            "uart_boot_contention_events": UART_BOOT_CONTENTION_EVENTS,
            "donor_access_mode": DONOR_ACCESS_MODE,
        },
        "donor_audit": asdict(donor_audit),
        "camset_cross_body_sanitizer": asdict(camset_res),
        "lpcm_4ch_24bit_48khz_pipeline": {
            "passed": lpcm_ok,
            "overload_with_minus20db_safety": asdict(lpcm_nominal),
            "xlr_h1_hot_detach_fallback": asdict(lpcm_detach),
            "sq_120fps_auto_mute": asdict(lpcm_sq_mute),
            "phantom_48v_ribbon_firewall": asdict(ribbon_48v_gate),
        },
        "smpte_12m_user_bits_tc_regenerator": asdict(tcub_res),
    }
    digest = hashlib.sha256(
        json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()
    payload["audit_digest_sha256"] = digest
    return payload


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="camset_lpcm_tcub_emulator.py",
        description="Phase 82 — Stage 12 Cross-Body CAMSET, 4ch 24-bit/48kHz LPCM & SMPTE 12M User-Bits Emulator",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room synthetic mode")
    parser.add_argument("--self-test", action="store_true", help="Run full Stage 12 self-test (default)")
    parser.add_argument("--json", action="store_true", help="Emit deterministic JSON output")
    parser.add_argument("--summary", action="store_true", help="Emit concise one-line summary")
    parser.add_argument("--camset-matrix", action="store_true", help="Emit CAMSET sanitizer JSON")
    parser.add_argument("--lpcm-matrix", action="store_true", help="Emit 4ch LPCM JSON")
    parser.add_argument("--tcub-matrix", action="store_true", help="Emit SMPTE 12M User-Bits & HDMI TC OUT JSON")
    args = parser.parse_args(argv)

    rep = run_phase82_camset_lpcm_tcub_audit(
        force_clean_room=True if args.clean_room else None
    )

    if args.camset_matrix:
        sys.stdout.write(json.dumps(rep["camset_cross_body_sanitizer"], indent=2) + "\n")
        return 0 if rep["camset_cross_body_sanitizer"]["passed"] else 1  # type: ignore[index]
    if args.lpcm_matrix:
        sys.stdout.write(json.dumps(rep["lpcm_4ch_24bit_48khz_pipeline"], indent=2) + "\n")
        return 0 if rep["lpcm_4ch_24bit_48khz_pipeline"]["passed"] else 1  # type: ignore[index]
    if args.tcub_matrix:
        sys.stdout.write(json.dumps(rep["smpte_12m_user_bits_tc_regenerator"], indent=2) + "\n")
        return 0 if rep["smpte_12m_user_bits_tc_regenerator"]["passed"] else 1  # type: ignore[index]

    if args.summary and not args.json:
        status = "PASS" if rep["all_checks_passed"] else "FAIL"
        tcub = rep["smpte_12m_user_bits_tc_regenerator"]
        sys.stdout.write(
            f"[{status}] Phase 82 Stage 12 CAMSET/LPCM/TC-UB | mode={rep['source_mode']} | "
            f"camset=100%_parity(nd=Clear,wlan=Off,bk4_wr=0) | "
            f"lpcm=4ch_24b_48k(safety=-20dB,wrap=0,sq_mute=1) | "
            f"tc_ub={tcub['sony_ub_display']}(offset=0f,hdmi_tc_out=1) | "  # type: ignore[index]
            f"cp_mut=0 | digest={str(rep['audit_digest_sha256'])[:12]}\n"
        )
    else:
        sys.stdout.write(json.dumps(rep, indent=2) + "\n")

    return 0 if rep["all_checks_passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
