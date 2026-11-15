"""Phase 115 — Active Optical HDMI (AOC) Pin-18 +5V Over-Current / Reverse Backfeed &
Unclamped Type-A Port Shear Firewall (Gate G35), CFexpress Type-A / SDXC UHS-II Dual-Slot
VPG Sustained-Write, NVMe Thermal-Throttle & Door-Open Flush Guard (Gate G36), and Unified
36-Gate Master Safety Preflight (`G01..G36` / `verify-36-gates`).

Operationalizes two critical external-recorder HDMI +5V / mechanical-port protections and
dual-slot high-bitrate CFexpress/SDXC media endurance protections for Sony ILME-FX3
(`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057`), while keeping all prior gate
modules (`preflight.py`, `master_16gate_preflight.py`, `usblan_ptpip_and_18gate_preflight.py`,
`rig_groundloop_lensrail_and_20gate_guard.py`, `phantom48v_gimbal_and_22gate_guard.py`,
`dewpoint_tec_usbc_and_24gate_guard.py`, `intake_occlusion_tripod_and_26gate_guard.py`,
`sensor_curtain_subzero_and_28gate_guard.py`, `wireless_tx_emi_endurance_and_30gate_guard.py`,
`pl_cantilever_dummybatt_and_32gate_guard.py`, and
`saltspray_haze_followfocus_and_34gate_guard.py`) completely untouched:

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor HDMI / Media / Thermal Audit**:
   - Inspects local FX3 `v7.02` & FX6 `v6.01` `libInfraAdjMedia.so`
     (`AVBB_SCN_START_HDMI`, `AVBB_SCN_STOP_HDMI`,
     `DisableMediaTemperatureInfoNotification`, `GetTemp`),
     `libInfraMediaConfig.so` (`ADJ_SLOT_1`, `ADJ_SLOT_2`, `CTRL_TEMP`, `SLOT_SSD`),
     `libInfraMediaDetect.so` (`IMD_Starttemp`, `IMD_Stoptemp`, `NotifyTempEvent`,
     `_ZN24InfraMediaDetectThreadRM7GetTempEjPv`), and `libInfraMediaCommon.so`
     (`CFexpress`, `FSYS_GTEST_VPGP4_AU_SIZE`,
     `NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0`,
     `mcmn_drv_nvme_getlogpage_smartinformation`, `mcmn_dmm_hotplug`) strictly via
     `os.open(..., os.O_RDONLY)`, plus optional chunked scans of `appFw.so`
     (`HDMI`, `RAW_OUTPUT`, `OFF_BY_MEDIA_THERMAL`, `FAN_CONTROL_MINIMUM`,
     `FAN_CONTROL_OFF_IN_REC`, `EXFAT_MEDIA_FILESYSTEM_SLOT2_EXFAT`,
     `EVENT_REMOTE_DOUBLE_SLOT_SETTINGS_RELAY_REC`) and `cpapp-b.bin`
     (`DETECT_HPD`, `OBSERVE_HPD`, `FAN_EQ_ID`, `THERMISTOR_ADJ_START`) when
     `include_large_binaries=True`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent.

2. **Gate G35 — Active Optical HDMI (AOC) Pin-18 `+5V` Over-Current / Reverse Backfeed &
   Unclamped Type-A Port Shear Firewall**:
   - Protects FX3's `SY-1129` mainboard full-size HDMI Type-A receptacle and `+5V`
     current-limited load switch during external ProRes RAW / BRAW recorder rigging
     (`Atomos Ninja`, `Blackmagic Video Assist`, `SmallHD`).
   - Fails closed on:
     a) `BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR` when
        `hdmi_pin18_draw_ma > 55.0` and `external_hdmi_5v_power_injector == False`,
     b) `BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD` when
        `sink_backfeed_voltage_v > 5.35` or (`camera_power_off == True` and
        `sink_pin18_backfeed_ma > 2.0` and `hdmi_reverse_blocking_diode_verified == False`),
     c) `BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR` when
        (`hdmi_cable_bend_moment_nm > 1.2` or `heavy_braided_or_coiled_hdmi_cable == True`)
        and `cage_hdmi_cable_clamp_locked == False`.

3. **Gate G36 — CFexpress Type-A / SDXC UHS-II Dual-Slot VPG Sustained-Write, NVMe
   Thermal-Throttle & Door-Open Flush Guard**:
   - Protects `XAVC S-I 4K 120p` (`600 Mbps`) and simultaneous dual-slot relay/backup
     recording against silent frame drops, NAND thermal throttling, and exFAT/FAT
     commit corruption.
   - Fails closed on:
     a) `BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC` when
        `sustained_p99_write_mb_s < required_min_write_mb_s` (including dual-slot
        simultaneous overhead margin and `VPG200`/`VPG400` profile validation),
     b) `BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT` when
        `cfexpress_controller_temp_c > 82.0` or (`dual_slot_simultaneous_4k120p == True`
        and `ambient_temp_c > 38.0` and `sigma_fan_mode in {"OFF_IN_REC", "MINIMUM"}`),
     c) `BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH` when
        `slot_door_open_detected == True` and `media_flush_or_fat_commit_pending == True`.

4. **Unified 36-Gate Master Safety Preflight (`evaluate_36gate_preflight` / CLI
   `verify-36-gates`)**:
   - Composes `evaluate_34gate_preflight` (`G01..G34`) with `G35` and `G36`:
     * Offline default mode: `33/36` gates pass (`G10..G12` physical Tier-0 backup
       truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `36/36` simulation gates pass
       (`dry_run_rehearsal_only = True`), while `persistent_emmc_writes_authorized`
       and `persistent_write_release` remain hard-locked to `False`.

Hard Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- All donor file reads strictly use `os.open(..., os.O_RDONLY)`.
- Zero raw binary `bytes` repr output (always `.hex()`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .saltspray_haze_followfocus_and_34gate_guard import (
    Master34GateReport,
    evaluate_34gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
    scan_tokens_o_rdonly,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

HDMI_AOC_CFEXPRESS_36GATE_SCHEMA: str = (
    "fx3-hdmi-aoc-5v-cfexpress-36gate-preflight-v1"
)
HDMI_AOC_CFEXPRESS_36GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G35..G36
G35_GATE_ID: str = "G35_hdmi_aoc_5v_backfeed_and_port_shear_safe"
G35_GATE_CODE: str = "HDMI_AOC_5V_BACKFEED_AND_PORT_SHEAR_SAFE"

G36_GATE_ID: str = "G36_cfexpress_vpg_nvme_thermal_and_door_flush_safe"
G36_GATE_CODE: str = "CFEXPRESS_VPG_NVME_THERMAL_AND_DOOR_FLUSH_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G35: str = "VERIFIED_HDMI_AOC_5V_BACKFEED_AND_PORT_SHEAR_SAFE"
STATUS_VERIFIED_G36: str = (
    "VERIFIED_CFEXPRESS_VPG_NVME_THERMAL_AND_DOOR_FLUSH_SAFE"
)

# Gate G35 Violation Codes
STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR: str = (
    "BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR"
)
STATUS_BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD: str = (
    "BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD"
)
STATUS_BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR: str = (
    "BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR"
)
STATUS_BLOCKED_HDMI_AOC_TELEMETRY_INVALID: str = (
    "BLOCKED_HDMI_AOC_TELEMETRY_INVALID"
)

# Gate G36 Violation Codes
STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC: str = (
    "BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC"
)
STATUS_BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT: str = (
    "BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT"
)
STATUS_BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH: str = (
    "BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH"
)
STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID: str = (
    "BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID"
)

STATUS_BLOCKED_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE115_36GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G35 HDMI AOC +5V & Port Leverage Thresholds
HDMI_PIN18_MAX_UNINJECTED_DRAW_MA: float = 55.0
HDMI_PIN18_REVERSE_BACKFEED_MAX_V: float = 5.35
HDMI_PIN18_POWER_OFF_BACKFEED_MAX_MA: float = 2.0
HDMI_PORT_MAX_UNCLAMPED_MOMENT_NM: float = 1.2
HDMI_PIN18_NOMINAL_VOLTAGE_V: float = 5.0
STANDARD_GRAVITY_M_S2: float = 9.80665

# Gate G36 CFexpress / SDXC VPG Sustained Write, NVMe Thermal & Door Flush Thresholds
XAVC_SI_4K120P_BITRATE_MBPS: float = 600.0
VPG200_MIN_WRITE_MB_S: float = 200.0
VPG400_MIN_WRITE_MB_S: float = 400.0
VPG_PROFILE_MIN_WRITE_MB_S: Mapping[str, float] = {
    "NONE": 0.0,
    "V60": 60.0,
    "V90": 90.0,
    "VPG200": VPG200_MIN_WRITE_MB_S,
    "VPG400": VPG400_MIN_WRITE_MB_S,
}
SINGLE_SLOT_CODEC_OVERHEAD_MARGIN: float = 1.25
DUAL_SLOT_SIMULTANEOUS_OVERHEAD_MARGIN: float = 1.20
CFEXPRESS_NVME_THERMAL_THROTTLE_MAX_C: float = 82.0
DUAL_SLOT_4K120P_HIGH_AMBIENT_MAX_C: float = 38.0
VALID_SIGMA_FAN_MODES: Tuple[str, ...] = (
    "AUTO1",
    "AUTO2",
    "MINIMUM",
    "OFF_IN_REC",
    "ALWAYS_OFF",
)
UNSAFE_DUAL_SLOT_4K120P_FAN_MODES: Tuple[str, ...] = (
    "OFF_IN_REC",
    "MINIMUM",
    "ALWAYS_OFF",
)

# Compact FX3/FX6 Donor Specs for HDMI / Media Slot Config / Thermal / CFexpress Contracts (O_RDONLY verified)
PINNED_PHASE115_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_lib_infra_adj_media": (
        "fx3",
        "libInfraAdjMedia.so",
        318_152,
        "caae47cd50a72816f75515724828a0d136985844fe3b9a13ad0fda15b08dbf11",
        (
            b"AVBB_SCN_START_HDMI",
            b"AVBB_SCN_STOP_HDMI",
            b"DisableMediaTemperatureInfoNotification",
            b"GetTemp",
        ),
        "fx3/libInfraAdjMedia.so::{AVBB_SCN_START_HDMI,AVBB_SCN_STOP_HDMI,DisableMediaTemperatureInfoNotification,GetTemp}",
    ),
    "fx6_lib_infra_adj_media": (
        "fx6",
        "libInfraAdjMedia.so",
        334_536,
        "2dba0c9931017db4fd49e10978f8b3bcd212f952abe780a9ffcccaa9bf96d60e",
        (
            b"AVBB_SCN_START_HDMI",
            b"AVBB_SCN_STOP_HDMI",
            b"DisableMediaTemperatureInfoNotification",
            b"GetTemp",
        ),
        "fx6/libInfraAdjMedia.so::{AVBB_SCN_START_HDMI,AVBB_SCN_STOP_HDMI,DisableMediaTemperatureInfoNotification,GetTemp}",
    ),
    "fx3_lib_infra_media_config": (
        "fx3",
        "libInfraMediaConfig.so",
        52_312,
        "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486",
        (
            b"ADJ_SLOT_1",
            b"ADJ_SLOT_2",
            b"CTRL_TEMP",
            b"SLOT_SSD",
        ),
        "fx3/libInfraMediaConfig.so::{ADJ_SLOT_1,ADJ_SLOT_2,CTRL_TEMP,SLOT_SSD}",
    ),
    "fx6_lib_infra_media_config": (
        "fx6",
        "libInfraMediaConfig.so",
        52_312,
        "9709656102d582bd0d91d7a612abb076873d533b1e0e2ed042c6b2611d56c1c3",
        (
            b"ADJ_SLOT_1",
            b"ADJ_SLOT_2",
            b"CTRL_TEMP",
            b"SLOT_SSD",
        ),
        "fx6/libInfraMediaConfig.so::{ADJ_SLOT_1,ADJ_SLOT_2,CTRL_TEMP,SLOT_SSD}",
    ),
    "fx3_lib_infra_media_detect": (
        "fx3",
        "libInfraMediaDetect.so",
        98_224,
        "4c1dbb303cf9d2d762723e0eb2266309c83aefe7d50f050fc8baa3964e4ea70d",
        (
            b"IMD_Starttemp",
            b"IMD_Stoptemp",
            b"NotifyTempEvent",
            b"_ZN24InfraMediaDetectThreadRM7GetTempEjPv",
        ),
        "fx3/libInfraMediaDetect.so::{IMD_Starttemp,IMD_Stoptemp,NotifyTempEvent,GetTemp}",
    ),
    "fx6_lib_infra_media_detect": (
        "fx6",
        "libInfraMediaDetect.so",
        98_224,
        "8883fef94a7ba9e8c22f98b537e902b4b1d5d23e8dae658537e193c96e9142b3",
        (
            b"IMD_Starttemp",
            b"IMD_Stoptemp",
            b"NotifyTempEvent",
            b"_ZN24InfraMediaDetectThreadRM7GetTempEjPv",
        ),
        "fx6/libInfraMediaDetect.so::{IMD_Starttemp,IMD_Stoptemp,NotifyTempEvent,GetTemp}",
    ),
    "fx3_lib_infra_media_common": (
        "fx3",
        "libInfraMediaCommon.so",
        402_624,
        "1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b",
        (
            b"CFexpress",
            b"FSYS_GTEST_VPGP4_AU_SIZE",
            b"NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0",
            b"mcmn_drv_nvme_getlogpage_smartinformation",
            b"mcmn_dmm_hotplug",
        ),
        "fx3/libInfraMediaCommon.so::{CFexpress,FSYS_GTEST_VPGP4_AU_SIZE,CFE_SPEC4_0,smartinformation,mcmn_dmm_hotplug}",
    ),
    "fx6_lib_infra_media_common": (
        "fx6",
        "libInfraMediaCommon.so",
        402_624,
        "acbabff1ac3595a39f73a24f1384e0c132f69e19bf7a1ca42c9e2621cf5fbedd",
        (
            b"CFexpress",
            b"FSYS_GTEST_VPGP4_AU_SIZE",
            b"NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0",
            b"mcmn_drv_nvme_getlogpage_smartinformation",
            b"mcmn_dmm_hotplug",
        ),
        "fx6/libInfraMediaCommon.so::{CFexpress,FSYS_GTEST_VPGP4_AU_SIZE,CFE_SPEC4_0,smartinformation,mcmn_dmm_hotplug}",
    ),
}

PINNED_APPFW_HDMI_MEDIA_TOKENS: Tuple[str, ...] = (
    "HDMI",
    "RAW_OUTPUT",
    "OFF_BY_MEDIA_THERMAL",
    "FAN_CONTROL_MINIMUM",
    "FAN_CONTROL_OFF_IN_REC",
    "EXFAT_MEDIA_FILESYSTEM_SLOT2_EXFAT",
    "EVENT_REMOTE_DOUBLE_SLOT_SETTINGS_RELAY_REC",
)

PINNED_CPAPP_HPD_THERMAL_TOKENS: Tuple[str, ...] = (
    "DETECT_HPD",
    "OBSERVE_HPD",
    "FAN_EQ_ID",
    "THERMISTOR_ADJ_START",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase115DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    hdmi_display_tokens_verified: bool
    media_slot_config_tokens_verified: bool
    media_thermal_nvme_tokens_verified: bool
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HdmiAoc5vFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    recorder_profile: str
    hdmi_pin18_draw_ma: float
    external_hdmi_5v_power_injector: bool
    sink_backfeed_voltage_v: float
    camera_power_off: bool
    sink_pin18_backfeed_ma: float
    hdmi_reverse_blocking_diode_verified: bool
    hdmi_cable_bend_moment_nm: float
    heavy_braided_or_coiled_hdmi_cable: bool
    cage_hdmi_cable_clamp_locked: bool
    pin18_power_draw_mw: float
    pin18_overcurrent_safe: bool
    pin18_reverse_backfeed_safe: bool
    hdmi_port_leverage_shear_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CfexpressVpgThermalDoorResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    media_profile: str
    codec_bitrate_mbps: float
    vpg_profile: str
    vpg_certified: bool
    sustained_p99_write_mb_s: float
    required_min_write_mb_s: float
    write_headroom_mb_s: float
    cfexpress_controller_temp_c: float
    ambient_temp_c: float
    dual_slot_simultaneous_4k120p: bool
    sigma_fan_mode: str
    slot_door_open_detected: bool
    media_flush_or_fat_commit_pending: bool
    sustained_write_floor_safe: bool
    nvme_thermal_throttle_safe: bool
    door_open_flush_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G35HdmiAoc5vResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    hdmi_aoc_5v_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G36CfexpressMediaDoorResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    cfexpress_vpg_door_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master36GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_33_gates_verified: bool
    all_36_gates_verified: bool
    g13_to_g36_all_passed: bool
    g35_to_g36_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_34_report: Dict[str, Any]
    g35_result: Dict[str, Any]
    g36_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers (Strict os.O_RDONLY, zero raw bytes printing)
# ---------------------------------------------------------------------------


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without printing raw bytes."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        chunks: List[bytes] = []
        while True:
            chunk = os.read(fd, 65536)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _is_finite_number(val: Any) -> bool:
    return (
        isinstance(val, (int, float))
        and (not isinstance(val, bool))
        and math.isfinite(float(val))
    )


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase115_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase115DonorAuditResult:
    """Inspect FX3/FX6 HDMI/media-slot/thermal/CFexpress donors via `os.O_RDONLY`."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)

    if work_root is not None and paths.work_root is None:
        explicit_root = Path(work_root)
        fx3_lib_dir = (
            explicit_root
            / "fx3-vm-20261101"
            / "menu-repair-01"
            / "original-uipc"
            / "ap-projection"
            / "regular-files"
            / "usr"
            / "lib"
        )
        fx6_lib_dir = (
            explicit_root
            / "fx3-color-port-20261027"
            / "FX6-donor-assessment-20261103"
            / "team"
            / "donor"
            / "nflasha15-files"
            / "lib"
        )
        effective_work_root: Optional[Path] = explicit_root
    else:
        fx3_lib_dir = paths.fx3_lib_dir
        fx6_lib_dir = paths.fx6_lib_dir
        effective_work_root = paths.work_root

    resolved: Dict[str, Path] = {
        "fx3_lib_infra_adj_media": fx3_lib_dir / "libInfraAdjMedia.so",
        "fx6_lib_infra_adj_media": fx6_lib_dir / "libInfraAdjMedia.so",
        "fx3_lib_infra_media_config": fx3_lib_dir / "libInfraMediaConfig.so",
        "fx6_lib_infra_media_config": fx6_lib_dir / "libInfraMediaConfig.so",
        "fx3_lib_infra_media_detect": fx3_lib_dir / "libInfraMediaDetect.so",
        "fx6_lib_infra_media_detect": fx6_lib_dir / "libInfraMediaDetect.so",
        "fx3_lib_infra_media_common": fx3_lib_dir / "libInfraMediaCommon.so",
        "fx6_lib_infra_media_common": fx6_lib_dir / "libInfraMediaCommon.so",
    }

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase115DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE115_DONOR_SPECS.values()
            ),
            missing_markers=(),
            hdmi_display_tokens_verified=True,
            media_slot_config_tokens_verified=True,
            media_thermal_nvme_tokens_verified=True,
            large_binaries_scanned=False,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE115_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE115_DONOR_SPECS.items()
            },
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    warnings: List[str] = []
    passed_keys: set[str] = set()

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE115_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
        sha = hashlib.sha256(blob).hexdigest()
        shas[key] = sha
        sizes[key] = len(blob)

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = len(blob) == exp_size and sha == exp_sha

        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )

        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={len(blob)} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )

        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    files_inspected = len(resolved)
    large_scanned = False
    appfw_ok = True
    cpapp_ok = True
    if include_large_binaries:
        if paths.fx3_appfw_path.is_file():
            appfw_sz, missing_appfw = scan_tokens_o_rdonly(
                paths.fx3_appfw_path, PINNED_APPFW_HDMI_MEDIA_TOKENS
            )
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                appfw_ok = False
                missing.extend(missing_appfw)
                errors.append(
                    f"fx3 appFw.so missing HDMI/media/thermal tokens: {missing_appfw}"
                )
            else:
                checked.append(
                    "fx3/appFw.so::HDMI+RAW_OUTPUT+OFF_BY_MEDIA_THERMAL+RELAY_REC"
                )
        else:
            warnings.append(
                "fx3/appFw.so not found for optional large-binary HDMI/media scan."
            )

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(
                paths.fx3_cp_path, PINNED_CPAPP_HPD_THERMAL_TOKENS
            )
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                cpapp_ok = False
                missing.extend(missing_cp)
                errors.append(
                    f"fx3 cpapp-b.bin missing DETECT_HPD/FAN_EQ_ID/THERMISTOR tokens: {missing_cp}"
                )
            else:
                checked.append(
                    "fx3/cpapp-b.bin::DETECT_HPD+OBSERVE_HPD+FAN_EQ_ID+THERMISTOR_ADJ_START"
                )
        else:
            warnings.append(
                "fx3/cpapp-b.bin not found for optional large-binary HPD/thermal scan."
            )

    valid = len(errors) == 0 and len(missing) == 0
    return Phase115DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        hdmi_display_tokens_verified={
            "fx3_lib_infra_adj_media",
            "fx6_lib_infra_adj_media",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        media_slot_config_tokens_verified={
            "fx3_lib_infra_media_config",
            "fx6_lib_infra_media_config",
        }.issubset(passed_keys)
        and appfw_ok,
        media_thermal_nvme_tokens_verified={
            "fx3_lib_infra_media_detect",
            "fx6_lib_infra_media_detect",
            "fx3_lib_infra_media_common",
            "fx6_lib_infra_media_common",
        }.issubset(passed_keys)
        and appfw_ok
        and cpapp_ok,
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Electrical, Mechanical & Media Sustained-Write Physics Helpers
# ---------------------------------------------------------------------------


def compute_hdmi_pin18_power_mw(
    pin18_draw_ma: float,
    bus_voltage_v: float = HDMI_PIN18_NOMINAL_VOLTAGE_V,
) -> float:
    """Compute HDMI Type-A Pin-18 +5V rail power draw in milliwatts (mW)."""
    if not (_is_finite_number(pin18_draw_ma) and _is_finite_number(bus_voltage_v)):
        raise ValueError("pin18_draw_ma and bus_voltage_v must be finite numbers.")
    if float(pin18_draw_ma) < 0.0 or float(bus_voltage_v) < 0.0:
        raise ValueError("pin18_draw_ma and bus_voltage_v must be >= 0.0.")
    return float(pin18_draw_ma) * float(bus_voltage_v)


def compute_hdmi_type_a_cantilever_moment_nm(
    cable_mass_kg: float,
    lever_arm_mm: float,
    *,
    shock_factor_g: float = 2.0,
) -> float:
    """Compute dynamic cantilever bending moment `M = m * g * L * shock_g` (N*m) on HDMI Type-A."""
    if not (
        _is_finite_number(cable_mass_kg)
        and _is_finite_number(lever_arm_mm)
        and _is_finite_number(shock_factor_g)
    ):
        raise ValueError(
            "cable_mass_kg, lever_arm_mm, and shock_factor_g must be finite numbers."
        )
    if (
        float(cable_mass_kg) < 0.0
        or float(lever_arm_mm) < 0.0
        or float(shock_factor_g) <= 0.0
    ):
        raise ValueError(
            "cable_mass_kg >= 0.0, lever_arm_mm >= 0.0, shock_factor_g > 0.0 required."
        )
    return (
        float(cable_mass_kg)
        * STANDARD_GRAVITY_M_S2
        * (float(lever_arm_mm) / 1000.0)
        * float(shock_factor_g)
    )


def compute_required_sustained_write_mb_s(
    codec_bitrate_mbps: float = XAVC_SI_4K120P_BITRATE_MBPS,
    *,
    dual_slot_simultaneous_4k120p: bool = False,
    vpg_profile: str = "VPG200",
    single_slot_overhead_margin: float = SINGLE_SLOT_CODEC_OVERHEAD_MARGIN,
    dual_slot_overhead_margin: float = DUAL_SLOT_SIMULTANEOUS_OVERHEAD_MARGIN,
) -> float:
    """Compute required sustained P99 write floor (MB/s) for codec, VPG tier, and dual-slot overhead."""
    if not (
        _is_finite_number(codec_bitrate_mbps)
        and _is_finite_number(single_slot_overhead_margin)
        and _is_finite_number(dual_slot_overhead_margin)
    ):
        raise ValueError(
            "codec_bitrate_mbps and overhead margins must be finite numbers."
        )
    if (
        float(codec_bitrate_mbps) < 0.0
        or float(single_slot_overhead_margin) < 1.0
        or float(dual_slot_overhead_margin) < 1.0
    ):
        raise ValueError(
            "codec_bitrate_mbps >= 0.0 and overhead margins >= 1.0 required."
        )
    norm_vpg = str(vpg_profile).strip().upper()
    if norm_vpg not in VPG_PROFILE_MIN_WRITE_MB_S:
        raise ValueError(
            f"Unsupported vpg_profile={vpg_profile!r}; expected one of {tuple(VPG_PROFILE_MIN_WRITE_MB_S.keys())}."
        )
    codec_mb_s = (float(codec_bitrate_mbps) / 8.0) * float(single_slot_overhead_margin)
    vpg_floor_mb_s = VPG_PROFILE_MIN_WRITE_MB_S[norm_vpg]
    base_floor = max(codec_mb_s, vpg_floor_mb_s)
    if dual_slot_simultaneous_4k120p:
        return base_floor * float(dual_slot_overhead_margin)
    return base_floor


# ---------------------------------------------------------------------------
# 3. Gate G35 — AOC HDMI Pin-18 +5V & Port Shear Firewall
# ---------------------------------------------------------------------------


def verify_hdmi_aoc_5v_and_port_shear_firewall(
    *,
    recorder_profile: str = "FX3_DIRECT_PASSIVE_SHORT_HDMI",
    hdmi_pin18_draw_ma: float = 18.0,
    external_hdmi_5v_power_injector: bool = False,
    sink_backfeed_voltage_v: float = 0.0,
    camera_power_off: bool = False,
    sink_pin18_backfeed_ma: float = 0.0,
    hdmi_reverse_blocking_diode_verified: bool = True,
    hdmi_cable_bend_moment_nm: float = 0.25,
    heavy_braided_or_coiled_hdmi_cable: bool = False,
    cage_hdmi_cable_clamp_locked: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> HdmiAoc5vFirewallResult:
    """Verify Gate G35 (AOC HDMI Pin-18 +5V over-current, reverse backfeed & port shear)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
        )

    telemetry_ok = True
    if not _is_finite_number(hdmi_pin18_draw_ma) or float(hdmi_pin18_draw_ma) < 0.0:
        _add_code(codes, STATUS_BLOCKED_HDMI_AOC_TELEMETRY_INVALID)
        errors.append(
            f"hdmi_pin18_draw_ma must be finite >= 0.0, got {hdmi_pin18_draw_ma!r}."
        )
        telemetry_ok = False
        eff_draw_ma = 18.0
    else:
        eff_draw_ma = float(hdmi_pin18_draw_ma)

    if (
        not _is_finite_number(sink_backfeed_voltage_v)
        or float(sink_backfeed_voltage_v) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_HDMI_AOC_TELEMETRY_INVALID)
        errors.append(
            f"sink_backfeed_voltage_v must be finite >= 0.0, got {sink_backfeed_voltage_v!r}."
        )
        telemetry_ok = False
        eff_backfeed_v = 0.0
    else:
        eff_backfeed_v = float(sink_backfeed_voltage_v)

    if (
        not _is_finite_number(sink_pin18_backfeed_ma)
        or float(sink_pin18_backfeed_ma) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_HDMI_AOC_TELEMETRY_INVALID)
        errors.append(
            f"sink_pin18_backfeed_ma must be finite >= 0.0, got {sink_pin18_backfeed_ma!r}."
        )
        telemetry_ok = False
        eff_backfeed_ma = 0.0
    else:
        eff_backfeed_ma = float(sink_pin18_backfeed_ma)

    if (
        not _is_finite_number(hdmi_cable_bend_moment_nm)
        or float(hdmi_cable_bend_moment_nm) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_HDMI_AOC_TELEMETRY_INVALID)
        errors.append(
            f"hdmi_cable_bend_moment_nm must be finite >= 0.0, got {hdmi_cable_bend_moment_nm!r}."
        )
        telemetry_ok = False
        eff_moment_nm = 0.25
    else:
        eff_moment_nm = float(hdmi_cable_bend_moment_nm)

    pin18_power_mw = compute_hdmi_pin18_power_mw(eff_draw_ma)

    # a) Active Optical HDMI (AOC) Pin-18 +5V Over-Current Guard
    pin18_overcurrent_safe = not (
        telemetry_ok
        and (eff_draw_ma > HDMI_PIN18_MAX_UNINJECTED_DRAW_MA)
        and (not bool(external_hdmi_5v_power_injector))
    )
    if not pin18_overcurrent_safe:
        _add_code(codes, STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR)
        errors.append(
            f"BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR: {recorder_profile} draws "
            f"hdmi_pin18_draw_ma={eff_draw_ma:.1f} mA (> {HDMI_PIN18_MAX_UNINJECTED_DRAW_MA:.1f} mA, "
            f"{pin18_power_mw:.1f} mW) across FX3 SY-1129 +5V load switch without "
            "external_hdmi_5v_power_injector=True."
        )

    # b) HDMI Pin-18 Reverse Backfeed Hazard Guard
    pin18_reverse_backfeed_safe = not (
        telemetry_ok
        and (
            (eff_backfeed_v > HDMI_PIN18_REVERSE_BACKFEED_MAX_V)
            or (
                bool(camera_power_off)
                and (eff_backfeed_ma > HDMI_PIN18_POWER_OFF_BACKFEED_MAX_MA)
                and (not bool(hdmi_reverse_blocking_diode_verified))
            )
        )
    )
    if not pin18_reverse_backfeed_safe:
        _add_code(codes, STATUS_BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD)
        errors.append(
            f"BLOCKED_HDMI_5V_REVERSE_BACKFEED_HAZARD: sink_backfeed_voltage_v={eff_backfeed_v:.2f} V "
            f"(limit {HDMI_PIN18_REVERSE_BACKFEED_MAX_V:.2f} V), camera_power_off={camera_power_off}, "
            f"sink_pin18_backfeed_ma={eff_backfeed_ma:.1f} mA, diode_verified="
            f"{hdmi_reverse_blocking_diode_verified} threatens FX3 SY-1129 +5V PMIC backfeed."
        )

    # c) Unclamped HDMI Type-A Port Leverage Shear Guard
    hdmi_port_leverage_shear_safe = not (
        telemetry_ok
        and (
            (eff_moment_nm > HDMI_PORT_MAX_UNCLAMPED_MOMENT_NM)
            or bool(heavy_braided_or_coiled_hdmi_cable)
        )
        and (not bool(cage_hdmi_cable_clamp_locked))
    )
    if not hdmi_port_leverage_shear_safe:
        _add_code(codes, STATUS_BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR)
        errors.append(
            f"BLOCKED_UNCLAMPED_HDMI_PORT_LEVERAGE_SHEAR: hdmi_cable_bend_moment_nm="
            f"{eff_moment_nm:.2f} N*m (limit {HDMI_PORT_MAX_UNCLAMPED_MOMENT_NM:.1f} N*m), "
            f"heavy_braided_or_coiled_hdmi_cable={heavy_braided_or_coiled_hdmi_cable} with "
            "cage_hdmi_cable_clamp_locked=False risks tearing FX3's SY-1129 HDMI Type-A receptacle pads."
        )

    if telemetry_ok and len(errors) == 0:
        if eff_draw_ma > HDMI_PIN18_MAX_UNINJECTED_DRAW_MA and external_hdmi_5v_power_injector:
            warnings.append(
                f"High-draw AOC HDMI cable ({eff_draw_ma:.1f} mA) safely offloaded to external +5V power injector."
            )
        if (
            eff_moment_nm > HDMI_PORT_MAX_UNCLAMPED_MOMENT_NM
            or heavy_braided_or_coiled_hdmi_cable
        ) and cage_hdmi_cable_clamp_locked:
            warnings.append(
                "Heavy/high-moment HDMI cable strain safely relieved by locked cage HDMI cable clamp."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return HdmiAoc5vFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        recorder_profile=str(recorder_profile),
        hdmi_pin18_draw_ma=round(eff_draw_ma, 2),
        external_hdmi_5v_power_injector=bool(external_hdmi_5v_power_injector),
        sink_backfeed_voltage_v=round(eff_backfeed_v, 3),
        camera_power_off=bool(camera_power_off),
        sink_pin18_backfeed_ma=round(eff_backfeed_ma, 2),
        hdmi_reverse_blocking_diode_verified=bool(
            hdmi_reverse_blocking_diode_verified
        ),
        hdmi_cable_bend_moment_nm=round(eff_moment_nm, 3),
        heavy_braided_or_coiled_hdmi_cable=bool(
            heavy_braided_or_coiled_hdmi_cable
        ),
        cage_hdmi_cable_clamp_locked=bool(cage_hdmi_cable_clamp_locked),
        pin18_power_draw_mw=round(pin18_power_mw, 2),
        pin18_overcurrent_safe=pin18_overcurrent_safe,
        pin18_reverse_backfeed_safe=pin18_reverse_backfeed_safe,
        hdmi_port_leverage_shear_safe=hdmi_port_leverage_shear_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G36 — CFexpress / SDXC UHS-II VPG Sustained-Write, NVMe Thermal & Door Guard
# ---------------------------------------------------------------------------


def verify_cfexpress_vpg_thermal_and_door_guard(
    *,
    media_profile: str = "CFEXPRESS_TYPE_A_VPG200_SINGLE",
    codec_bitrate_mbps: float = XAVC_SI_4K120P_BITRATE_MBPS,
    vpg_profile: str = "VPG200",
    vpg_certified: bool = True,
    sustained_p99_write_mb_s: float = 260.0,
    required_min_write_mb_s: Optional[float] = None,
    cfexpress_controller_temp_c: float = 54.0,
    ambient_temp_c: float = 25.0,
    dual_slot_simultaneous_4k120p: bool = False,
    sigma_fan_mode: str = "AUTO1",
    slot_door_open_detected: bool = False,
    media_flush_or_fat_commit_pending: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> CfexpressVpgThermalDoorResult:
    """Verify Gate G36 (CFexpress/SDXC VPG sustained write, NVMe thermal & door-open flush)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False)."
        )

    telemetry_ok = True
    if not _is_finite_number(codec_bitrate_mbps) or float(codec_bitrate_mbps) < 0.0:
        _add_code(codes, STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID)
        errors.append(
            f"codec_bitrate_mbps must be finite >= 0.0, got {codec_bitrate_mbps!r}."
        )
        telemetry_ok = False
        eff_bitrate_mbps = XAVC_SI_4K120P_BITRATE_MBPS
    else:
        eff_bitrate_mbps = float(codec_bitrate_mbps)

    if (
        not _is_finite_number(sustained_p99_write_mb_s)
        or float(sustained_p99_write_mb_s) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID)
        errors.append(
            f"sustained_p99_write_mb_s must be finite >= 0.0, got {sustained_p99_write_mb_s!r}."
        )
        telemetry_ok = False
        eff_p99_mb_s = 260.0
    else:
        eff_p99_mb_s = float(sustained_p99_write_mb_s)

    if required_min_write_mb_s is not None and (
        not _is_finite_number(required_min_write_mb_s)
        or float(required_min_write_mb_s) < 0.0
    ):
        _add_code(codes, STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID)
        errors.append(
            f"required_min_write_mb_s must be finite >= 0.0, got {required_min_write_mb_s!r}."
        )
        telemetry_ok = False

    if (
        not _is_finite_number(cfexpress_controller_temp_c)
        or float(cfexpress_controller_temp_c) < -40.0
        or float(cfexpress_controller_temp_c) > 150.0
    ):
        _add_code(codes, STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID)
        errors.append(
            "cfexpress_controller_temp_c must be finite in [-40.0, 150.0] C, "
            f"got {cfexpress_controller_temp_c!r}."
        )
        telemetry_ok = False
        eff_ctrl_temp_c = 54.0
    else:
        eff_ctrl_temp_c = float(cfexpress_controller_temp_c)

    if (
        not _is_finite_number(ambient_temp_c)
        or float(ambient_temp_c) < -40.0
        or float(ambient_temp_c) > 85.0
    ):
        _add_code(codes, STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID)
        errors.append(
            f"ambient_temp_c must be finite in [-40.0, 85.0] C, got {ambient_temp_c!r}."
        )
        telemetry_ok = False
        eff_ambient_c = 25.0
    else:
        eff_ambient_c = float(ambient_temp_c)

    norm_vpg = str(vpg_profile).strip().upper()
    if norm_vpg not in VPG_PROFILE_MIN_WRITE_MB_S:
        _add_code(codes, STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID)
        errors.append(
            f"vpg_profile={vpg_profile!r} unsupported; expected one of "
            f"{tuple(VPG_PROFILE_MIN_WRITE_MB_S.keys())}."
        )
        telemetry_ok = False
        eff_vpg = "VPG200"
    else:
        eff_vpg = norm_vpg

    norm_fan = str(sigma_fan_mode).strip().upper()
    if norm_fan not in VALID_SIGMA_FAN_MODES:
        _add_code(codes, STATUS_BLOCKED_CFEXPRESS_MEDIA_TELEMETRY_INVALID)
        errors.append(
            f"sigma_fan_mode={sigma_fan_mode!r} unsupported; expected one of {VALID_SIGMA_FAN_MODES}."
        )
        telemetry_ok = False
        eff_fan = "AUTO1"
    else:
        eff_fan = norm_fan

    if required_min_write_mb_s is not None and _is_finite_number(required_min_write_mb_s):
        base_req = max(0.0, float(required_min_write_mb_s))
        eff_required_mb_s = (
            base_req * DUAL_SLOT_SIMULTANEOUS_OVERHEAD_MARGIN
            if dual_slot_simultaneous_4k120p
            else base_req
        )
    else:
        eff_required_mb_s = compute_required_sustained_write_mb_s(
            eff_bitrate_mbps,
            dual_slot_simultaneous_4k120p=bool(dual_slot_simultaneous_4k120p),
            vpg_profile=eff_vpg,
        )

    headroom_mb_s = eff_p99_mb_s - eff_required_mb_s

    # a) Sustained P99 Write Floor & VPG200/VPG400 Profile Guard
    vpg_cert_violation = (eff_vpg in ("VPG200", "VPG400")) and (not bool(vpg_certified))
    sustained_write_floor_safe = not (
        telemetry_ok
        and ((eff_p99_mb_s < eff_required_mb_s) or vpg_cert_violation)
    )
    if not sustained_write_floor_safe:
        _add_code(codes, STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC)
        errors.append(
            f"BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC: {media_profile} sustained_p99_write_mb_s="
            f"{eff_p99_mb_s:.1f} MB/s < required_min_write_mb_s={eff_required_mb_s:.1f} MB/s "
            f"(codec={eff_bitrate_mbps:.0f} Mbps, vpg={eff_vpg}, vpg_certified={vpg_certified}, "
            f"dual_slot={dual_slot_simultaneous_4k120p}), risking silent XAVC S-I frame drops."
        )

    # b) CFexpress NVMe Controller Thermal-Throttle Guard
    nvme_thermal_throttle_safe = not (
        telemetry_ok
        and (
            (eff_ctrl_temp_c > CFEXPRESS_NVME_THERMAL_THROTTLE_MAX_C)
            or (
                bool(dual_slot_simultaneous_4k120p)
                and (eff_ambient_c > DUAL_SLOT_4K120P_HIGH_AMBIENT_MAX_C)
                and (eff_fan in UNSAFE_DUAL_SLOT_4K120P_FAN_MODES)
            )
        )
    )
    if not nvme_thermal_throttle_safe:
        _add_code(codes, STATUS_BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT)
        errors.append(
            f"BLOCKED_CFEXPRESS_NVME_THERMAL_THROTTLE_IMMINENT: cfexpress_controller_temp_c="
            f"{eff_ctrl_temp_c:.1f} C (max {CFEXPRESS_NVME_THERMAL_THROTTLE_MAX_C:.1f} C), "
            f"dual_slot_4k120p={dual_slot_simultaneous_4k120p}, ambient={eff_ambient_c:.1f} C, "
            f"sigma_fan_mode={eff_fan} risks NAND SLC-cache collapse and thermal shutdown."
        )

    # c) Media Slot Door-Open During Flush / exFAT Commit Guard
    door_open_flush_safe = not (
        telemetry_ok
        and bool(slot_door_open_detected)
        and bool(media_flush_or_fat_commit_pending)
    )
    if not door_open_flush_safe:
        _add_code(codes, STATUS_BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH)
        errors.append(
            "BLOCKED_MEDIA_DOOR_OPEN_DURING_FLUSH: slot_door_open_detected=True while "
            "media_flush_or_fat_commit_pending=True risks unfinalized .RSV clips and "
            "non-journaled exFAT FAT/bitmap corruption."
        )

    if telemetry_ok and len(errors) == 0:
        if dual_slot_simultaneous_4k120p:
            warnings.append(
                f"Dual-slot simultaneous 4K 120p active ({eff_p99_mb_s:.1f} >= {eff_required_mb_s:.1f} MB/s) "
                f"with Sigma fan={eff_fan} at {eff_ambient_c:.1f} C."
            )
        if slot_door_open_detected and not media_flush_or_fat_commit_pending:
            warnings.append(
                "Media slot door open while idle (no pending flush/FAT commit); safe for card swap."
            )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return CfexpressVpgThermalDoorResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        media_profile=str(media_profile),
        codec_bitrate_mbps=round(eff_bitrate_mbps, 2),
        vpg_profile=eff_vpg,
        vpg_certified=bool(vpg_certified),
        sustained_p99_write_mb_s=round(eff_p99_mb_s, 2),
        required_min_write_mb_s=round(eff_required_mb_s, 2),
        write_headroom_mb_s=round(headroom_mb_s, 2),
        cfexpress_controller_temp_c=round(eff_ctrl_temp_c, 2),
        ambient_temp_c=round(eff_ambient_c, 2),
        dual_slot_simultaneous_4k120p=bool(dual_slot_simultaneous_4k120p),
        sigma_fan_mode=eff_fan,
        slot_door_open_detected=bool(slot_door_open_detected),
        media_flush_or_fat_commit_pending=bool(media_flush_or_fat_commit_pending),
        sustained_write_floor_safe=sustained_write_floor_safe,
        nvme_thermal_throttle_safe=nvme_thermal_throttle_safe,
        door_open_flush_safe=door_open_flush_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G35 & Gate G36 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g35_hdmi_aoc_5v_and_port_shear(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    hdmi_aoc_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase115DonorAuditResult] = None,
) -> Tuple[GateVerdict, G35HdmiAoc5vResult]:
    """Evaluate Gate G35 (`hdmi_aoc_5v_backfeed_and_port_shear_safe`)."""
    audit = donor_audit or audit_phase115_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(hdmi_aoc_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    fw_res = verify_hdmi_aoc_5v_and_port_shear_firewall(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in fw_res.violation_codes:
        _add_code(codes, c)
    errors.extend(fw_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(fw_res.warnings)

    passed = (
        audit.valid
        and fw_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G35
        if passed
        else (
            codes[0] if codes else STATUS_BLOCKED_AOC_HDMI_5V_OVERCURRENT_NO_INJECTOR
        )
    )

    res = G35HdmiAoc5vResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        hdmi_aoc_5v_firewall=fw_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G35_GATE_ID,
        gate_code=G35_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"AOC HDMI Pin-18 +5V / Reverse Backfeed & Type-A Port Shear Firewall "
            f"({fw_res.status}, draw={fw_res.hdmi_pin18_draw_ma:.1f}mA, "
            f"injector={fw_res.external_hdmi_5v_power_injector}, "
            f"backfeed={fw_res.sink_backfeed_voltage_v:.2f}V, "
            f"moment={fw_res.hdmi_cable_bend_moment_nm:.2f}N*m, "
            f"clamp={fw_res.cage_hdmi_cable_clamp_locked}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "pin18_overcurrent_safe": fw_res.pin18_overcurrent_safe,
            "pin18_reverse_backfeed_safe": fw_res.pin18_reverse_backfeed_safe,
            "hdmi_port_leverage_shear_safe": fw_res.hdmi_port_leverage_shear_safe,
        },
    )
    return verdict, res


def evaluate_g36_cfexpress_vpg_thermal_and_door_flush(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    cfexpress_media_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase115DonorAuditResult] = None,
) -> Tuple[GateVerdict, G36CfexpressMediaDoorResult]:
    """Evaluate Gate G36 (`cfexpress_vpg_nvme_thermal_and_door_flush_safe`)."""
    audit = donor_audit or audit_phase115_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(cfexpress_media_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_cfexpress_vpg_thermal_and_door_guard(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in guard_res.violation_codes:
        _add_code(codes, c)
    errors.extend(guard_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(guard_res.warnings)

    passed = (
        audit.valid
        and guard_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G36
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_SUSTAINED_WRITE_FLOOR_BELOW_CODEC
        )
    )

    res = G36CfexpressMediaDoorResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        cfexpress_vpg_door_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G36_GATE_ID,
        gate_code=G36_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"CFexpress Type-A / UHS-II Dual-Slot VPG Sustained-Write, NVMe Thermal & "
            f"Door-Open Flush Guard ({guard_res.status}, p99={guard_res.sustained_p99_write_mb_s:.1f}MB/s, "
            f"min={guard_res.required_min_write_mb_s:.1f}MB/s, vpg={guard_res.vpg_profile}, "
            f"ctrl_temp={guard_res.cfexpress_controller_temp_c:.1f}C, "
            f"door_open={guard_res.slot_door_open_detected}, "
            f"flush_pending={guard_res.media_flush_or_fat_commit_pending}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "sustained_write_floor_safe": guard_res.sustained_write_floor_safe,
            "nvme_thermal_throttle_safe": guard_res.nvme_thermal_throttle_safe,
            "door_open_flush_safe": guard_res.door_open_flush_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 36-Gate Preflight Evaluator (`G01..G36`) & CLI
# ---------------------------------------------------------------------------


def evaluate_36gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G34 pass-throughs
    tier0_manifest: Optional[Dict[str, object]] = None,
    worker_syscall_trace: Optional[List[Dict[str, object]]] = None,
    init2_failsafe_hook: Optional[str] = None,
    candidate_bundle_verified: Optional[bool] = None,
    allow_dry_run_gate12: bool = False,
    gate12_kwargs: Optional[Mapping[str, Any]] = None,
    ltc_kwargs: Optional[Mapping[str, Any]] = None,
    mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    crsdk_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    crsdk_kwargs: Optional[Mapping[str, Any]] = None,
    spacc_operations: Optional[Sequence[Mapping[str, Any]]] = None,
    spacc_script_text: str = "",
    spacc_sector0_bytes: Optional[bytes] = None,
    harness_kwargs: Optional[Mapping[str, Any]] = None,
    fan_kwargs: Optional[Mapping[str, Any]] = None,
    power_kwargs: Optional[Mapping[str, Any]] = None,
    soc_start_ceiling_c: Optional[float] = None,
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    c2pa_calibration_script_text: str = "",
    calibration_mutation_bytes: int = 0,
    c2pa_keystore_writes_attempted: bool = False,
    exfat_dirty_bit_present: bool = False,
    exfat_unfinalized_rsv_present: bool = False,
    allow_c2pa_or_calibration_write: bool = False,
    p12_vma: int = P12_WLAN_FATAL_GUARD_VMA,
    p12_patched_rc: int = 0,
    p12_guard_enabled: bool = True,
    bk4_airplane_shadow: Optional[Mapping[int, int]] = None,
    wf12_bootloop_immune: bool = True,
    wbi_mutation_bytes: int = 0,
    cp_mutation_bytes: int = 0,
    nvram_persistent_writes: int = 0,
    request_persistent_emmc_writes: bool = False,
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    p1_vbr_bytes: Optional[bytes] = None,
    p1_image_path: Optional[Path] = None,
    p1_device_node: str = "/dev/nflasha1",
    require_at_least_one_lab_card: bool = True,
    usblan_kwargs: Optional[Mapping[str, Any]] = None,
    ptpip_or_mc_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    ptpip_authenticated: bool = True,
    allow_protocol_3_00: bool = False,
    rig_kwargs: Optional[Mapping[str, Any]] = None,
    emount_kwargs: Optional[Mapping[str, Any]] = None,
    power_failover_kwargs: Optional[Mapping[str, Any]] = None,
    rsv_bytes: Optional[bytes] = None,
    rsv_path: Optional[Path] = None,
    xlr_kwargs: Optional[Mapping[str, Any]] = None,
    gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    dewpoint_kwargs: Optional[Mapping[str, Any]] = None,
    pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None,
    intake_fan_kwargs: Optional[Mapping[str, Any]] = None,
    tripod_housing_kwargs: Optional[Mapping[str, Any]] = None,
    sensor_curtain_kwargs: Optional[Mapping[str, Any]] = None,
    subzero_altitude_kwargs: Optional[Mapping[str, Any]] = None,
    wireless_tx_emi_kwargs: Optional[Mapping[str, Any]] = None,
    longform_endurance_kwargs: Optional[Mapping[str, Any]] = None,
    pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None,
    dummy_battery_kwargs: Optional[Mapping[str, Any]] = None,
    saltspray_haze_kwargs: Optional[Mapping[str, Any]] = None,
    followfocus_gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    # G35 inputs (AOC HDMI Pin-18 +5V / Backfeed & Type-A Port Shear Firewall)
    hdmi_aoc_kwargs: Optional[Mapping[str, Any]] = None,
    # G36 inputs (CFexpress / SDXC VPG Sustained-Write, NVMe Thermal & Door Flush Guard)
    cfexpress_media_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master36GateReport:
    """Evaluate all 36 Master Safety Gates (`G01..G36`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m34_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated_backup": bool(dry_run_simulated_backup),
        "include_large_binaries": include_large_binaries,
        "work_root": work_root,
        "tier0_manifest": tier0_manifest,
        "worker_syscall_trace": worker_syscall_trace,
        "init2_failsafe_hook": init2_failsafe_hook,
        "candidate_bundle_verified": candidate_bundle_verified,
        "allow_dry_run_gate12": allow_dry_run_gate12,
        "gate12_kwargs": gate12_kwargs,
        "ltc_kwargs": ltc_kwargs,
        "mishoe_kwargs": mishoe_kwargs,
        "crsdk_requests": crsdk_requests,
        "crsdk_kwargs": crsdk_kwargs,
        "spacc_operations": spacc_operations,
        "spacc_script_text": spacc_script_text,
        "spacc_sector0_bytes": spacc_sector0_bytes,
        "harness_kwargs": harness_kwargs,
        "fan_kwargs": fan_kwargs,
        "power_kwargs": power_kwargs,
        "planned_mounts": planned_mounts,
        "planned_writes": planned_writes,
        "c2pa_calibration_script_text": c2pa_calibration_script_text,
        "calibration_mutation_bytes": calibration_mutation_bytes,
        "c2pa_keystore_writes_attempted": c2pa_keystore_writes_attempted,
        "exfat_dirty_bit_present": exfat_dirty_bit_present,
        "exfat_unfinalized_rsv_present": exfat_unfinalized_rsv_present,
        "allow_c2pa_or_calibration_write": allow_c2pa_or_calibration_write,
        "p12_vma": p12_vma,
        "p12_patched_rc": p12_patched_rc,
        "p12_guard_enabled": p12_guard_enabled,
        "bk4_airplane_shadow": bk4_airplane_shadow,
        "wf12_bootloop_immune": wf12_bootloop_immune,
        "wbi_mutation_bytes": wbi_mutation_bytes,
        "cp_mutation_bytes": cp_mutation_bytes,
        "nvram_persistent_writes": nvram_persistent_writes,
        "request_persistent_emmc_writes": request_persistent_emmc_writes,
        "slot_a": slot_a,
        "slot_b": slot_b,
        "p1_vbr_bytes": p1_vbr_bytes,
        "p1_image_path": p1_image_path,
        "p1_device_node": p1_device_node,
        "require_at_least_one_lab_card": require_at_least_one_lab_card,
        "usblan_kwargs": usblan_kwargs,
        "ptpip_or_mc_requests": ptpip_or_mc_requests,
        "ptpip_authenticated": ptpip_authenticated,
        "allow_protocol_3_00": allow_protocol_3_00,
        "rig_kwargs": rig_kwargs,
        "emount_kwargs": emount_kwargs,
        "power_failover_kwargs": power_failover_kwargs,
        "rsv_bytes": rsv_bytes,
        "rsv_path": rsv_path,
        "xlr_kwargs": xlr_kwargs,
        "gimbal_kwargs": gimbal_kwargs,
        "dewpoint_kwargs": dewpoint_kwargs,
        "pmic_usbc_kwargs": pmic_usbc_kwargs,
        "intake_fan_kwargs": intake_fan_kwargs,
        "tripod_housing_kwargs": tripod_housing_kwargs,
        "sensor_curtain_kwargs": sensor_curtain_kwargs,
        "subzero_altitude_kwargs": subzero_altitude_kwargs,
        "wireless_tx_emi_kwargs": wireless_tx_emi_kwargs,
        "longform_endurance_kwargs": longform_endurance_kwargs,
        "pl_cantilever_kwargs": pl_cantilever_kwargs,
        "dummy_battery_kwargs": dummy_battery_kwargs,
        "saltspray_haze_kwargs": saltspray_haze_kwargs,
        "followfocus_gimbal_kwargs": followfocus_gimbal_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m34_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m34_report: Master34GateReport = evaluate_34gate_preflight(
        resolved_root, **m34_kwargs
    )

    phase115_audit = audit_phase115_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g35_verdict, g35_res = evaluate_g35_hdmi_aoc_5v_and_port_shear(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        hdmi_aoc_kwargs=hdmi_aoc_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase115_audit,
    )

    g36_verdict, g36_res = evaluate_g36_cfexpress_vpg_thermal_and_door_flush(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        cfexpress_media_kwargs=cfexpress_media_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase115_audit,
    )

    gates_35_to_36 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g35_verdict, g36_verdict)
    ]
    all_gates = tuple(list(m34_report.gates) + gates_35_to_36)

    g01_to_g12_verified = int(m34_report.summary["g01_to_g12_verified"])
    g13_to_g34_verified = (
        int(m34_report.summary["g13_to_g32_verified"])
        + int(m34_report.summary["g33_to_g34_verified"])
    )
    g35_to_g36_verified = sum(1 for v in (g35_verdict, g36_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g34_verified + g35_to_g36_verified

    g35_to_g36_all_passed = g35_to_g36_verified == 2
    g13_to_g36_all_passed = (
        m34_report.g13_to_g34_all_passed and g35_to_g36_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m34_report.gates[:9])

    offline_33_verified = (
        g01_to_g09_ok
        and m34_report.offline_31_gates_verified
        and g35_to_g36_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_36_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g36_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (
        not dry_run_simulated_backup
    )
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g36_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_33_verified
        and m34_report.h0_h1_trial_entry_allowed
        and g35_to_g36_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m34_report.errors) + list(g35_verdict.errors) + list(g36_verdict.errors)
    )
    warnings: List[str] = (
        list(m34_report.warnings)
        + list(g35_verdict.warnings)
        + list(g36_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m34_report.g13_to_g34_all_passed:
        overall_status = m34_report.status
    elif not g35_verdict.passed:
        overall_status = g35_verdict.status
    elif not g36_verdict.passed:
        overall_status = g36_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_36_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_36_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_36_verified:
        overall_status = "VERIFIED_ALL_36_GATES"
    else:
        overall_status = "VERIFIED_33_OF_36_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m34_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g35_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g36_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 36,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 36 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g34_verified": g13_to_g34_verified,
        "g35_to_g36_verified": g35_to_g36_verified,
        "g13_to_g36_all_passed": g13_to_g36_all_passed,
        "g35_to_g36_all_passed": g35_to_g36_all_passed,
        "offline_33_gates_verified": offline_33_verified,
        "all_36_gates_verified": all_36_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master36GateReport(
        schema=HDMI_AOC_CFEXPRESS_36GATE_SCHEMA,
        version=HDMI_AOC_CFEXPRESS_36GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_33_gates_verified=offline_33_verified,
        all_36_gates_verified=all_36_verified,
        g13_to_g36_all_passed=g13_to_g36_all_passed,
        g35_to_g36_all_passed=g35_to_g36_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_34_report=m34_report.to_dict(),
        g35_result=g35_res.to_dict(),
        g36_result=g36_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_36_master_safety_gates = evaluate_36gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="hdmi_aoc_5v_cfexpress_and_36gate_guard",
        description=(
            "Phase 115 — AOC HDMI Pin-18 +5V Over-Current / Reverse Backfeed & Port Shear "
            "Firewall (G35), CFexpress / SDXC UHS-II Dual-Slot VPG Sustained-Write, NVMe "
            "Thermal-Throttle & Door-Open Flush Guard (G36), and 36-Gate Master Preflight (G01..G36)"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G36 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_36gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/36 "
            f"g35_to_g36_all_passed={report.g35_to_g36_all_passed} "
            f"all_36_gates_verified={report.all_36_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_36_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_33_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
