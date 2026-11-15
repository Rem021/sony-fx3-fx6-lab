"""Phase 158 — Real-Hardware Main Track Part 12:
Gate G49 (`1.8V CMOS ttyAMA0 460800 8N1` RX-Only Passive Tap, Multi-USB
`VMC-BNCM1` Timecode Contention Firewall & Off-Chip `1.8V 8-bit` eMMC ISP
Passive Read Guard), Gate G50 (`IMX510` `p2:/setting/psd.bin & defdet.bin`
Per-Sensor Calibration NVS Immutability, Dual-Base ISO `800/12800` Gain Guard &
`.cube` 3D MLUT Non-Double-Bake Guard), and Unified 50-Gate Master Safety
Preflight (`G01..G50` / `verify-50-gates`).

Operationalizes the final two bench electrical & imaging-sensor NVS invariants on
physical Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057`)
while keeping all prior gate modules (`G01..G48`) 100% untouched and hard-locking:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `overall_ready_for_hardware_attach = False`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects BOTH FX3 `7.02` AND FX6 `6.01` `libsencore.so`, `libmpr.so`,
     `im.elf`, `cpapp-b.bin`, and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin`
     & `CX95898_NTSC.bin`) strictly via `os.open(..., os.O_RDONLY)` when present
     and `FX3_FX6_FORCE_CLEAN_ROOM != "1"`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent, leaking zero raw
     Sony firmware bytes in JSON output.

2. **Gate G49 — `1.8V CMOS ttyAMA0 (460800 8N1)` Passive RX-Only Tap,
   `VMC-BNCM1` Contention & `1.8V 8-bit` eMMC ISP Passive Read Firewall**:
   - Enforces strict `1.8V` CMOS UART logic (`1620..1950 mV`), passive high-Z
     `RX + GND` monitoring (`tx_line_connected == False`), `backpower_leakage_ua <= 5.0`,
     and `460800 8N1` framing on `ttyAMA0`.
   - Hard-blocks simultaneous Multi-USB `VMC-BNCM1` BNC Timecode attachment with
     a Multi-USB UART tap (`vmc_bncm1_simultaneous_attach == True`).
   - Validates off-chip `8-bit` eMMC ISP low-VCCQ (`1.8V`, `1650..1950 mV`)
     passive read parameters (`isp_clk_mhz <= 26.0`, `emmc_rst_n_held_low == True`
     during off-board ISP read, `isp_write_cmd24_cmd25_blocked == True`).

3. **Gate G50 — `IMX510` `p2:/setting/psd.bin & defdet.bin` NVS Lock,
   Dual-Base ISO `800/12800` Gain Guard & `.cube` 3D MLUT Non-Double-Bake Guard**:
   - Enforces zero mutation (`sensor_cal_mutation_bytes == 0`) and same-body
     SHA-256 identity (`same_body_sensor_cal_sha256_match == True`) across
     `p2:/setting/psd.bin`, `p2:/setting/defdet.bin`, and E-Mount
     `p18:/lens/LENSFILE.BIN`.
   - Enforces `IMX510` Dual-Base ISO (`800` LCG / `12800` HCG) legal analog gain
     bounds (`LCG: [-6.0, 22.0] dB` / `ISO 160..10000`; `HCG: [0.0, 30.2] dB` /
     `ISO 12800..409600`).
   - Validates `17^3` or `33^3` `.cube` 3D LUT tables (rejecting NaN, Inf, and
     out-of-range values) and hard-blocks double-baking a monitoring MLUT into the
     recorded `S-Log3 / S-Gamut3.Cine` XAVC master when
     `mlut_burn_in_authorized == False`.

4. **Unified 50-Gate Master Safety Preflight (`evaluate_50gate_preflight` / CLI
   `verify-50-gates`)**:
   - Offline default reports `47/50` (`G10..G12` physical Tier-0 gates `False`,
     `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`,
     `spi_nor_write_authorized = False`,
     `overall_ready_for_hardware_attach = False`).
   - `--dry-run-simulated-backup` reports `50/50` dry-run green while STILL
     hard-locking `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`, `spi_nor_write_authorized = False`,
     and `overall_ready_for_hardware_attach = False`.
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
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_pnflasha_mtdro_rfnvs_and_48gate_guard import (
    Master48GateReport,
    evaluate_48gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_UART1V8_IMX510_50GATE_SCHEMA: str = (
    "fx3-realhw-uart1v8-imx510-50gate-preflight-v1"
)
REALHW_UART1V8_IMX510_50GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False

# Gate IDs & Canonical Codes for G49..G50
G49_GATE_ID: str = "G49_uart1v8_ttyama0_passive_rx_vmc_bncm1_and_emmc_isp_firewall"
G49_GATE_CODE: str = "UART1V8_TTYAMA0_PASSIVE_RX_VMC_BNCM1_AND_EMMC_ISP_FIREWALL"

G50_GATE_ID: str = "G50_imx510_psd_defdet_nvs_lock_dual_iso_and_mlut_guard"
G50_GATE_CODE: str = "IMX510_PSD_DEFDET_NVS_LOCK_DUAL_ISO_AND_MLUT_GUARD"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G49: str = (
    "VERIFIED_UART1V8_TTYAMA0_PASSIVE_RX_VMC_BNCM1_AND_EMMC_ISP_FIREWALL"
)
STATUS_VERIFIED_G50: str = (
    "VERIFIED_IMX510_PSD_DEFDET_NVS_LOCK_DUAL_ISO_AND_MLUT_GUARD"
)

# Gate G49 Violation Codes
STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE: str = (
    "BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE"
)
STATUS_BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION: str = (
    "BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION"
)
STATUS_BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD: str = (
    "BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD"
)
STATUS_BLOCKED_G49_TELEMETRY_INVALID: str = (
    "BLOCKED_G49_UART1V8_ISP_TELEMETRY_INVALID"
)

# Gate G50 Violation Codes
STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY: str = (
    "BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY"
)
STATUS_BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS: str = (
    "BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS"
)
STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE: str = (
    "BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE"
)
STATUS_BLOCKED_G50_TELEMETRY_INVALID: str = (
    "BLOCKED_G50_IMX510_CAL_MLUT_TELEMETRY_INVALID"
)

STATUS_BLOCKED_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE158_50GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G49 Constants — 1.8V ttyAMA0 UART & 1.8V 8-bit eMMC ISP
UART_CANONICAL_DEVICES: Tuple[str, ...] = ("ttyAMA0", "/dev/ttyAMA0")
UART_CANONICAL_BAUD: int = 460800
UART_CANONICAL_FRAMING: str = "8N1"
UART_IO_MIN_MV: float = 1620.0
UART_IO_NOMINAL_MV: float = 1800.0
UART_IO_MAX_MV: float = 1950.0
UART_MAX_BACKPOWER_LEAKAGE_UA: float = 5.0

EMMC_ISP_VCCQ_MIN_MV: float = 1650.0
EMMC_ISP_VCCQ_NOMINAL_MV: float = 1800.0
EMMC_ISP_VCCQ_MAX_MV: float = 1950.0
EMMC_ISP_MAX_CLK_MHZ: float = 26.0
EMMC_ISP_REQUIRED_BUS_WIDTH_BITS: int = 8

# Gate G50 Constants — IMX510 Sensor NVS, Dual-Base ISO & .cube 3D MLUT
SENSOR_CAL_NVS_FILES: Tuple[str, ...] = (
    "p2:/setting/psd.bin",
    "p2:/setting/defdet.bin",
    "p18:/lens/LENSFILE.BIN",
)
DEFAULT_SYNTHETIC_PSD_SHA256: str = "1" * 64
DEFAULT_SYNTHETIC_DEFDET_SHA256: str = "2" * 64
DEFAULT_SYNTHETIC_LENSFILE_SHA256: str = "3" * 64

IMX510_BASE_ISO_LOW: int = 800
IMX510_BASE_ISO_HIGH: int = 12800
IMX510_VALID_BASE_ISOS: Tuple[int, ...] = (IMX510_BASE_ISO_LOW, IMX510_BASE_ISO_HIGH)
IMX510_GAIN_MODE_LCG: str = "LCG"
IMX510_GAIN_MODE_HCG: str = "HCG"
IMX510_LCG_MIN_ISO: int = 160
IMX510_LCG_MAX_ISO: int = 10000
IMX510_LCG_MIN_ANALOG_GAIN_DB: float = -6.0
IMX510_LCG_MAX_ANALOG_GAIN_DB: float = 22.0
IMX510_HCG_MIN_ISO: int = 12800
IMX510_HCG_MAX_ISO: int = 409600
IMX510_HCG_MIN_ANALOG_GAIN_DB: float = 0.0
IMX510_HCG_MAX_ANALOG_GAIN_DB: float = 30.2

CUBE_VALID_GRID_SIZES: Tuple[int, ...] = (17, 33)
CUBE_DOMAIN_MIN_VALUE: float = 0.0
CUBE_DOMAIN_MAX_VALUE: float = 1.0
SLOG3_RECORDING_COLOR_SPACES: Tuple[str, ...] = (
    "S-Log3/S-Gamut3.Cine",
    "S-Log3/S-Gamut3",
    "SLOG3_SGAMUT3_CINE",
    "SLOG3_SGAMUT3",
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE158_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_libsencore": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so",
        377_328,
        "a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410",
        (
            b"\x7fELF",
            b"AdjustControlFunc",
            b"SenserIfStart",
            b"SenserPacket",
            b"UART",
            b"USB_BUSPOWER_SUPPLY_CONTROL",
        ),
        "fx3/libsencore.so::{AdjustControlFunc,SenserIfStart,SenserPacket,UART,USB_BUSPOWER_SUPPLY_CONTROL}",
    ),
    "fx3_libmpr": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
        3_517_008,
        "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
        (
            b"\x7fELF",
            b"DmmMemInfo",
            b"GetUnitInfo",
            b"EncWfiStop",
            b"ExecEncStart",
        ),
        "fx3/libmpr.so::{DmmMemInfo,GetUnitInfo,EncWfiStop,ExecEncStart}",
    ),
    "fx3_im_elf": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/bin/im.elf",
        40_920,
        "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91",
        (
            b"\x7fELF",
            b"libIMDB.so",
            b"libbackup.so",
            b"libosal_uipc.so",
        ),
        "fx3/im.elf::{40920B,ELF,libIMDB.so,libbackup.so,libosal_uipc.so}",
    ),
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"/setting/defdet.bin",
            b"IMX510",
            b"ddl_VfxSetMlutUser3D",
            b"S-Log3/S-Gamut3.Cine",
            b"MLUT_L1D_A_ON",
        ),
        "fx3/cpapp-b.bin::{/setting/defdet.bin,IMX510,ddl_VfxSetMlutUser3D,S-Log3/S-Gamut3.Cine,MLUT_L1D_A_ON}",
    ),
    "fx3_backup_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (
            b"BK4\x00",
            b"psd.bin",
            b"defdet.bin",
            b"lensfile.bin",
        ),
        "fx3/Backup.bin::{2229740B,BK4\\0,psd.bin,defdet.bin,lensfile.bin}",
    ),
    "fx6_libsencore": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libsencore.so",
        401_952,
        "0bb14b72ac75840de801a63d51a1bd9b6772c5ba9fc0293c416f2b5ed3b4bee1",
        (
            b"\x7fELF",
            b"AdjustControlFunc",
            b"SenserIfStart",
            b"SenserPacket",
            b"UART",
            b"USB_BUSPOWER_SUPPLY_CONTROL",
        ),
        "fx6/libsencore.so::{AdjustControlFunc,SenserIfStart,SenserPacket,UART,USB_BUSPOWER_SUPPLY_CONTROL}",
    ),
    "fx6_libmpr": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so",
        28_921_824,
        "814dfff34cac6517d71f659fce8d1ead0bb7ee52b8a9ac1a4e25aa9f83ac2d4e",
        (
            b"\x7fELF",
            b"DmmMemInfo",
            b"GetUnitInfo",
            b"EncWfiStop",
            b"ExecEncStart",
            b"S-Log3",
        ),
        "fx6/libmpr.so::{DmmMemInfo,GetUnitInfo,EncWfiStop,ExecEncStart,S-Log3}",
    ),
    "fx6_im_elf": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/bin/im.elf",
        40_920,
        "87d672bd6abbcf695c0a773cb096d72d18429e5107846a2f0d3e8add87e400ec",
        (
            b"\x7fELF",
            b"libIMDB.so",
            b"libbackup.so",
            b"libosal_uipc.so",
        ),
        "fx6/im.elf::{40920B,ELF,libIMDB.so,libbackup.so,libosal_uipc.so}",
    ),
    "fx6_cpapp_b": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin",
        17_952_816,
        "60de0ab5544749dd50d8245f573c0994573fef349186efe20b502c42e3289668",
        (
            b"/setting/defdet.bin",
            b"IMX510",
            b"ddl_VfxSetMlutUser3D",
            b"S-Log3/S-Gamut3.Cine",
            b"MLUT_L1D_A_ON",
        ),
        "fx6/cpapp-b.bin::{/setting/defdet.bin,IMX510,ddl_VfxSetMlutUser3D,S-Log3/S-Gamut3.Cine,MLUT_L1D_A_ON}",
    ),
    "fx6_backup_bin": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (
            b"BK4\x00",
            b"psd.bin",
            b"defdet.bin",
            b"lensfile.bin",
        ),
        "fx6/Backup.bin::{2253333B,BK4\\0,psd.bin,defdet.bin,lensfile.bin}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase158DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Cube3dLutValidationResult:
    valid: bool
    grid_size: int
    expected_entries: int
    parsed_entries: int
    nan_count: int
    inf_count: int
    out_of_range_count: int
    domain_min: float
    domain_max: float
    reason: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Uart1v8VmcBncm1IspGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    uart_device: str
    uart_baud_rate: int
    uart_framing: str
    uart_tap_attached: bool
    uart_io_voltage_mv: float
    tx_line_connected: bool
    rx_high_z_passive: bool
    camera_vcc_mv: float
    backpower_leakage_ua: float
    vmc_bncm1_attached: bool
    vmc_bncm1_simultaneous_attach: bool
    offchip_emmc_isp_active: bool
    isp_vccq_mv: float
    isp_clk_mhz: float
    isp_bus_width_bits: int
    emmc_rst_n_held_low: bool
    isp_write_cmd24_cmd25_blocked: bool
    isp_mutation_bytes: int
    uart_1v8_passive_rx_safe: bool
    vmc_bncm1_isolation_safe: bool
    emmc_isp_1v8_passive_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Imx510SensorCalMlutGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    p2_setting_ro_locked: bool
    p18_lens_ro_locked: bool
    same_body_sensor_cal_sha256_match: bool
    psd_bin_sha256: str
    expected_psd_bin_sha256: str
    defdet_bin_sha256: str
    expected_defdet_bin_sha256: str
    lensfile_bin_sha256: str
    expected_lensfile_bin_sha256: str
    sensor_cal_mutation_bytes: int
    sensor_cal_writes_requested: int
    cross_body_or_fx6_cal_import_attempted: bool
    base_iso: int
    conversion_gain_mode: str
    target_iso: int
    analog_gain_db: float
    recording_color_space: str
    cube_grid_size: int
    cube_entries_verified: int
    cube_nan_count: int
    cube_inf_count: int
    cube_out_of_range_count: int
    mlut_monitoring_enabled: bool
    mlut_burn_in_to_xavc_master: bool
    mlut_burn_in_authorized: bool
    mlut_double_bake_blocked: bool
    sensor_cal_nvs_lock_safe: bool
    dual_base_iso_gain_safe: bool
    cube_3dlut_and_non_double_bake_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G49Uart1v8IspResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    uart1v8_isp_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G50Imx510SensorCalResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    imx510_sensor_cal_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master50GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_47_gates_verified: bool
    all_50_gates_verified: bool
    g13_to_g50_all_passed: bool
    g49_to_g50_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_48_report: Dict[str, Any]
    g49_result: Dict[str, Any]
    g50_result: Dict[str, Any]
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
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without leaking raw bytes."""
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


def _is_non_negative_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val >= 0


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool))


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit (FX3 7.02 & FX6 6.01)
# ---------------------------------------------------------------------------


def audit_phase158_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase158DonorAuditResult:
    """Inspect FX3 `7.02` & FX6 `6.01` `libsencore.so`, `libmpr.so`, `im.elf`,
    `cpapp-b.bin`, and `Backup.bin` strictly via `os.open(..., os.O_RDONLY)`
    with deterministic clean-room fallback.
    """
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (
            _body,
            rel_path,
            _sz,
            _sha,
            _toks,
            _lbl,
        ) in PINNED_PHASE158_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase158DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE158_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            fx6_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE158_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE158_DONOR_SPECS.items()
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
    ) in PINNED_PHASE158_DONOR_SPECS.items():
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

    fx3_keys = {
        k for k, spec in PINNED_PHASE158_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    fx6_keys = {
        k for k, spec in PINNED_PHASE158_DONOR_SPECS.items() if spec[0] == "fx6"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase158DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=len(resolved),
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys),
        fx6_contracts_verified=fx6_keys.issubset(passed_keys),
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Functions
# ---------------------------------------------------------------------------


def validate_uart_1v8_passive_rx(
    uart_device: str = "/dev/ttyAMA0",
    baud_rate: int = UART_CANONICAL_BAUD,
    framing: str = UART_CANONICAL_FRAMING,
    uart_io_voltage_mv: float = UART_IO_NOMINAL_MV,
    tx_line_connected: bool = False,
    backpower_leakage_ua: float = 0.0,
    *,
    rx_high_z_passive: bool = True,
    uart_tap_attached: bool = True,
) -> bool:
    """Validate strict `1.8V` CMOS `ttyAMA0` `460800 8N1` passive RX-only tap."""
    if not (
        isinstance(uart_device, str)
        and isinstance(framing, str)
        and _is_strict_int(baud_rate)
        and _is_finite_number(uart_io_voltage_mv)
        and _is_finite_number(backpower_leakage_ua)
    ):
        return False

    dev = uart_device.strip()
    frm = framing.strip().upper()
    mv = float(uart_io_voltage_mv)
    leak_ua = float(backpower_leakage_ua)

    if dev not in UART_CANONICAL_DEVICES:
        return False
    if baud_rate != UART_CANONICAL_BAUD or frm != UART_CANONICAL_FRAMING:
        return False
    if leak_ua < 0.0 or leak_ua > UART_MAX_BACKPOWER_LEAKAGE_UA:
        return False
    if bool(tx_line_connected):
        return False
    if not bool(rx_high_z_passive):
        return False
    if bool(uart_tap_attached):
        if mv < UART_IO_MIN_MV or mv > UART_IO_MAX_MV:
            return False
    else:
        if mv < 0.0 or mv > UART_IO_MAX_MV:
            return False
    return True


def validate_emmc_isp_1v8_passive_read(
    isp_vccq_mv: float = EMMC_ISP_VCCQ_NOMINAL_MV,
    isp_clk_mhz: float = 24.0,
    emmc_rst_n_held_low: bool = True,
    isp_write_cmd24_cmd25_blocked: bool = True,
    *,
    offchip_emmc_isp_active: bool = False,
    isp_bus_width_bits: int = EMMC_ISP_REQUIRED_BUS_WIDTH_BITS,
    isp_mutation_bytes: int = 0,
) -> bool:
    """Validate off-chip `8-bit` eMMC ISP `1.8V` VCCQ passive read parameters."""
    if not (
        _is_finite_number(isp_vccq_mv)
        and _is_finite_number(isp_clk_mhz)
        and _is_strict_int(isp_bus_width_bits)
        and _is_non_negative_int(isp_mutation_bytes)
    ):
        return False

    vccq = float(isp_vccq_mv)
    clk = float(isp_clk_mhz)

    if vccq < EMMC_ISP_VCCQ_MIN_MV or vccq > EMMC_ISP_VCCQ_MAX_MV:
        return False
    if clk <= 0.0 or clk > EMMC_ISP_MAX_CLK_MHZ:
        return False
    if isp_bus_width_bits != EMMC_ISP_REQUIRED_BUS_WIDTH_BITS:
        return False
    if not bool(isp_write_cmd24_cmd25_blocked):
        return False
    if isp_mutation_bytes != 0:
        return False
    if bool(offchip_emmc_isp_active) and not bool(emmc_rst_n_held_low):
        return False
    return True


def validate_sensor_calibration_nvs_lock(
    *,
    psd_bin_sha256: str = DEFAULT_SYNTHETIC_PSD_SHA256,
    expected_psd_bin_sha256: str = DEFAULT_SYNTHETIC_PSD_SHA256,
    defdet_bin_sha256: str = DEFAULT_SYNTHETIC_DEFDET_SHA256,
    expected_defdet_bin_sha256: str = DEFAULT_SYNTHETIC_DEFDET_SHA256,
    lensfile_bin_sha256: str = DEFAULT_SYNTHETIC_LENSFILE_SHA256,
    expected_lensfile_bin_sha256: str = DEFAULT_SYNTHETIC_LENSFILE_SHA256,
    same_body_sensor_cal_sha256_match: bool = True,
    sensor_cal_mutation_bytes: int = 0,
    sensor_cal_writes_requested: int = 0,
    p2_setting_ro_locked: bool = True,
    p18_lens_ro_locked: bool = True,
    cross_body_or_fx6_cal_import_attempted: bool = False,
) -> bool:
    """Validate `p2:/setting/{psd.bin,defdet.bin}` & `p18:/lens/LENSFILE.BIN` immutability."""
    for s in (
        psd_bin_sha256,
        expected_psd_bin_sha256,
        defdet_bin_sha256,
        expected_defdet_bin_sha256,
        lensfile_bin_sha256,
        expected_lensfile_bin_sha256,
    ):
        if not isinstance(s, str) or not _HEX64_RE.match(s.strip().lower()):
            return False

    if not (
        _is_non_negative_int(sensor_cal_mutation_bytes)
        and _is_non_negative_int(sensor_cal_writes_requested)
    ):
        return False

    if sensor_cal_mutation_bytes != 0 or sensor_cal_writes_requested != 0:
        return False
    if not bool(same_body_sensor_cal_sha256_match):
        return False
    if not (bool(p2_setting_ro_locked) and bool(p18_lens_ro_locked)):
        return False
    if bool(cross_body_or_fx6_cal_import_attempted):
        return False

    if psd_bin_sha256.strip().lower() != expected_psd_bin_sha256.strip().lower():
        return False
    if defdet_bin_sha256.strip().lower() != expected_defdet_bin_sha256.strip().lower():
        return False
    if (
        lensfile_bin_sha256.strip().lower()
        != expected_lensfile_bin_sha256.strip().lower()
    ):
        return False
    return True


def validate_imx510_dual_base_iso_gain(
    base_iso: int = IMX510_BASE_ISO_LOW,
    conversion_gain_mode: str = IMX510_GAIN_MODE_LCG,
    target_iso: int = IMX510_BASE_ISO_LOW,
    analog_gain_db: float = 0.0,
) -> Tuple[bool, str]:
    """Validate `IMX510` Dual-Base ISO (`800` LCG / `12800` HCG) legal analog gain bounds."""
    if not (
        _is_strict_int(base_iso)
        and isinstance(conversion_gain_mode, str)
        and _is_strict_int(target_iso)
        and _is_finite_number(analog_gain_db)
    ):
        return False, "IMX510 ISO/gain telemetry has invalid type or non-finite value."

    mode = conversion_gain_mode.strip().upper()
    gain_db = float(analog_gain_db)

    if base_iso not in IMX510_VALID_BASE_ISOS:
        return (
            False,
            f"Unsupported IMX510 base_iso={base_iso}; expected one of {IMX510_VALID_BASE_ISOS}.",
        )

    if base_iso == IMX510_BASE_ISO_LOW:
        if mode != IMX510_GAIN_MODE_LCG:
            return (
                False,
                f"IMX510 base_iso={base_iso} requires conversion_gain_mode={IMX510_GAIN_MODE_LCG}, got {mode!r}.",
            )
        if not (IMX510_LCG_MIN_ISO <= target_iso <= IMX510_LCG_MAX_ISO):
            return (
                False,
                f"IMX510 LCG target_iso={target_iso} outside [{IMX510_LCG_MIN_ISO}, {IMX510_LCG_MAX_ISO}] (use HCG base ISO 12800).",
            )
        if not (IMX510_LCG_MIN_ANALOG_GAIN_DB <= gain_db <= IMX510_LCG_MAX_ANALOG_GAIN_DB):
            return (
                False,
                f"IMX510 LCG analog_gain_db={gain_db:.2f} outside [{IMX510_LCG_MIN_ANALOG_GAIN_DB}, {IMX510_LCG_MAX_ANALOG_GAIN_DB}] dB.",
            )
        return True, "IMX510_LCG_BASE800_LEGAL"

    # IMX510_BASE_ISO_HIGH == 12800
    if mode != IMX510_GAIN_MODE_HCG:
        return (
            False,
            f"IMX510 base_iso={base_iso} requires conversion_gain_mode={IMX510_GAIN_MODE_HCG}, got {mode!r}.",
        )
    if not (IMX510_HCG_MIN_ISO <= target_iso <= IMX510_HCG_MAX_ISO):
        return (
            False,
            f"IMX510 HCG target_iso={target_iso} outside [{IMX510_HCG_MIN_ISO}, {IMX510_HCG_MAX_ISO}].",
        )
    if not (IMX510_HCG_MIN_ANALOG_GAIN_DB <= gain_db <= IMX510_HCG_MAX_ANALOG_GAIN_DB):
        return (
            False,
            f"IMX510 HCG analog_gain_db={gain_db:.2f} outside [{IMX510_HCG_MIN_ANALOG_GAIN_DB}, {IMX510_HCG_MAX_ANALOG_GAIN_DB}] dB.",
        )
    return True, "IMX510_HCG_BASE12800_LEGAL"


def validate_cube_3dlut(
    *,
    cube_text: Optional[str] = None,
    lut_triplets: Optional[Sequence[Sequence[float]]] = None,
    grid_size: int = 17,
    domain_min: float = CUBE_DOMAIN_MIN_VALUE,
    domain_max: float = CUBE_DOMAIN_MAX_VALUE,
) -> Cube3dLutValidationResult:
    """Validate `.cube` 3D LUT (`17^3` or `33^3`), rejecting NaN/Inf/out-of-range."""
    if not (
        _is_strict_int(grid_size)
        and _is_finite_number(domain_min)
        and _is_finite_number(domain_max)
    ):
        return Cube3dLutValidationResult(
            valid=False,
            grid_size=0,
            expected_entries=0,
            parsed_entries=0,
            nan_count=0,
            inf_count=0,
            out_of_range_count=0,
            domain_min=CUBE_DOMAIN_MIN_VALUE,
            domain_max=CUBE_DOMAIN_MAX_VALUE,
            reason="Invalid grid_size or domain bounds.",
        )

    eff_dmin = float(domain_min)
    eff_dmax = float(domain_max)
    if eff_dmin < CUBE_DOMAIN_MIN_VALUE or eff_dmax > CUBE_DOMAIN_MAX_VALUE or eff_dmin >= eff_dmax:
        return Cube3dLutValidationResult(
            valid=False,
            grid_size=int(grid_size),
            expected_entries=0,
            parsed_entries=0,
            nan_count=0,
            inf_count=0,
            out_of_range_count=0,
            domain_min=eff_dmin,
            domain_max=eff_dmax,
            reason="DOMAIN_MIN/DOMAIN_MAX must satisfy 0.0 <= min < max <= 1.0.",
        )

    parsed_rows: List[Tuple[float, float, float]] = []
    nan_count = 0
    inf_count = 0
    oor_count = 0
    eff_grid = int(grid_size)

    if cube_text is not None:
        if not isinstance(cube_text, str):
            return Cube3dLutValidationResult(
                valid=False,
                grid_size=0,
                expected_entries=0,
                parsed_entries=0,
                nan_count=0,
                inf_count=0,
                out_of_range_count=0,
                domain_min=eff_dmin,
                domain_max=eff_dmax,
                reason="cube_text must be str.",
            )
        found_size: Optional[int] = None
        for raw_line in cube_text.splitlines():
            line = raw_line.split("#", 1)[0].strip()
            if not line:
                continue
            parts = line.split()
            head = parts[0].upper()
            if head in ("TITLE", "LUT_1D_SIZE"):
                if head == "LUT_1D_SIZE":
                    return Cube3dLutValidationResult(
                        valid=False,
                        grid_size=0,
                        expected_entries=0,
                        parsed_entries=0,
                        nan_count=0,
                        inf_count=0,
                        out_of_range_count=0,
                        domain_min=eff_dmin,
                        domain_max=eff_dmax,
                        reason="LUT_1D_SIZE is not a 3D .cube LUT.",
                    )
                continue
            if head == "LUT_3D_SIZE":
                if len(parts) != 2:
                    return Cube3dLutValidationResult(
                        valid=False,
                        grid_size=0,
                        expected_entries=0,
                        parsed_entries=0,
                        nan_count=0,
                        inf_count=0,
                        out_of_range_count=0,
                        domain_min=eff_dmin,
                        domain_max=eff_dmax,
                        reason="Malformed LUT_3D_SIZE header.",
                    )
                try:
                    found_size = int(parts[1])
                except ValueError:
                    return Cube3dLutValidationResult(
                        valid=False,
                        grid_size=0,
                        expected_entries=0,
                        parsed_entries=0,
                        nan_count=0,
                        inf_count=0,
                        out_of_range_count=0,
                        domain_min=eff_dmin,
                        domain_max=eff_dmax,
                        reason="Non-integer LUT_3D_SIZE.",
                    )
                continue
            if head == "DOMAIN_MIN":
                if len(parts) != 4:
                    return Cube3dLutValidationResult(
                        valid=False,
                        grid_size=eff_grid,
                        expected_entries=0,
                        parsed_entries=0,
                        nan_count=0,
                        inf_count=0,
                        out_of_range_count=0,
                        domain_min=eff_dmin,
                        domain_max=eff_dmax,
                        reason="Malformed DOMAIN_MIN header.",
                    )
                try:
                    mins = [float(x) for x in parts[1:]]
                except ValueError:
                    return Cube3dLutValidationResult(
                        valid=False,
                        grid_size=eff_grid,
                        expected_entries=0,
                        parsed_entries=0,
                        nan_count=0,
                        inf_count=0,
                        out_of_range_count=0,
                        domain_min=eff_dmin,
                        domain_max=eff_dmax,
                        reason="Non-numeric DOMAIN_MIN.",
                    )
                if any(not math.isfinite(x) or x < CUBE_DOMAIN_MIN_VALUE for x in mins):
                    return Cube3dLutValidationResult(
                        valid=False,
                        grid_size=eff_grid,
                        expected_entries=0,
                        parsed_entries=0,
                        nan_count=0,
                        inf_count=0,
                        out_of_range_count=0,
                        domain_min=eff_dmin,
                        domain_max=eff_dmax,
                        reason="Invalid DOMAIN_MIN value (< 0.0 or non-finite).",
                    )
                eff_dmin = min(mins)
                continue
            if head == "DOMAIN_MAX":
                if len(parts) != 4:
                    return Cube3dLutValidationResult(
                        valid=False,
                        grid_size=eff_grid,
                        expected_entries=0,
                        parsed_entries=0,
                        nan_count=0,
                        inf_count=0,
                        out_of_range_count=0,
                        domain_min=eff_dmin,
                        domain_max=eff_dmax,
                        reason="Malformed DOMAIN_MAX header.",
                    )
                try:
                    maxs = [float(x) for x in parts[1:]]
                except ValueError:
                    return Cube3dLutValidationResult(
                        valid=False,
                        grid_size=eff_grid,
                        expected_entries=0,
                        parsed_entries=0,
                        nan_count=0,
                        inf_count=0,
                        out_of_range_count=0,
                        domain_min=eff_dmin,
                        domain_max=eff_dmax,
                        reason="Non-numeric DOMAIN_MAX.",
                    )
                if any(not math.isfinite(x) or x > CUBE_DOMAIN_MAX_VALUE for x in maxs):
                    return Cube3dLutValidationResult(
                        valid=False,
                        grid_size=eff_grid,
                        expected_entries=0,
                        parsed_entries=0,
                        nan_count=0,
                        inf_count=0,
                        out_of_range_count=0,
                        domain_min=eff_dmin,
                        domain_max=eff_dmax,
                        reason="Invalid DOMAIN_MAX value (> 1.0 or non-finite).",
                    )
                eff_dmax = max(maxs)
                continue

            if len(parts) != 3:
                return Cube3dLutValidationResult(
                    valid=False,
                    grid_size=found_size or eff_grid,
                    expected_entries=0,
                    parsed_entries=len(parsed_rows),
                    nan_count=nan_count,
                    inf_count=inf_count,
                    out_of_range_count=oor_count,
                    domain_min=eff_dmin,
                    domain_max=eff_dmax,
                    reason=f"Unexpected .cube line token count ({len(parts)}).",
                )
            try:
                triplet = tuple(float(x) for x in parts)
            except ValueError:
                return Cube3dLutValidationResult(
                    valid=False,
                    grid_size=found_size or eff_grid,
                    expected_entries=0,
                    parsed_entries=len(parsed_rows),
                    nan_count=nan_count,
                    inf_count=inf_count,
                    out_of_range_count=oor_count,
                    domain_min=eff_dmin,
                    domain_max=eff_dmax,
                    reason="Non-numeric RGB triplet in .cube table.",
                )
            parsed_rows.append((triplet[0], triplet[1], triplet[2]))

        if found_size is None:
            return Cube3dLutValidationResult(
                valid=False,
                grid_size=0,
                expected_entries=0,
                parsed_entries=len(parsed_rows),
                nan_count=0,
                inf_count=0,
                out_of_range_count=0,
                domain_min=eff_dmin,
                domain_max=eff_dmax,
                reason="Missing LUT_3D_SIZE header.",
            )
        eff_grid = found_size
    elif lut_triplets is not None:
        if isinstance(lut_triplets, (str, bytes)) or not isinstance(
            lut_triplets, Sequence
        ):
            return Cube3dLutValidationResult(
                valid=False,
                grid_size=eff_grid,
                expected_entries=0,
                parsed_entries=0,
                nan_count=0,
                inf_count=0,
                out_of_range_count=0,
                domain_min=eff_dmin,
                domain_max=eff_dmax,
                reason="lut_triplets must be a sequence of 3-float sequences.",
            )
        for row in lut_triplets:
            if (
                isinstance(row, (str, bytes))
                or not isinstance(row, Sequence)
                or len(row) != 3
                or not all(
                    isinstance(c, (int, float)) and not isinstance(c, bool) for c in row
                )
            ):
                return Cube3dLutValidationResult(
                    valid=False,
                    grid_size=eff_grid,
                    expected_entries=0,
                    parsed_entries=len(parsed_rows),
                    nan_count=nan_count,
                    inf_count=inf_count,
                    out_of_range_count=oor_count,
                    domain_min=eff_dmin,
                    domain_max=eff_dmax,
                    reason="Each LUT entry must be a 3-number RGB triplet.",
                )
            parsed_rows.append((float(row[0]), float(row[1]), float(row[2])))
    else:
        # Synthetic clean-room identity summary mode when caller supplies grid_size only
        if eff_grid not in CUBE_VALID_GRID_SIZES:
            return Cube3dLutValidationResult(
                valid=False,
                grid_size=eff_grid,
                expected_entries=0,
                parsed_entries=0,
                nan_count=0,
                inf_count=0,
                out_of_range_count=0,
                domain_min=eff_dmin,
                domain_max=eff_dmax,
                reason=f"Unsupported .cube 3D LUT size={eff_grid}; must be in {CUBE_VALID_GRID_SIZES}.",
            )
        exp = eff_grid**3
        return Cube3dLutValidationResult(
            valid=True,
            grid_size=eff_grid,
            expected_entries=exp,
            parsed_entries=exp,
            nan_count=0,
            inf_count=0,
            out_of_range_count=0,
            domain_min=eff_dmin,
            domain_max=eff_dmax,
            reason="SYNTHETIC_CUBE_3DLUT_VALID",
        )

    if eff_grid not in CUBE_VALID_GRID_SIZES:
        return Cube3dLutValidationResult(
            valid=False,
            grid_size=eff_grid,
            expected_entries=0,
            parsed_entries=len(parsed_rows),
            nan_count=0,
            inf_count=0,
            out_of_range_count=0,
            domain_min=eff_dmin,
            domain_max=eff_dmax,
            reason=f"Unsupported .cube 3D LUT size={eff_grid}; must be in {CUBE_VALID_GRID_SIZES}.",
        )

    expected_entries = eff_grid**3
    for r, g, b in parsed_rows:
        for val in (r, g, b):
            if math.isnan(val):
                nan_count += 1
            elif math.isinf(val):
                inf_count += 1
            elif val < eff_dmin or val > eff_dmax:
                oor_count += 1

    count_ok = len(parsed_rows) == expected_entries
    values_ok = nan_count == 0 and inf_count == 0 and oor_count == 0
    valid = count_ok and values_ok
    if valid:
        reason = f"CUBE_3DLUT_{eff_grid}x{eff_grid}x{eff_grid}_VALID"
    elif not count_ok:
        reason = f"Entry count mismatch: got {len(parsed_rows)}, expected {expected_entries} ({eff_grid}^3)."
    else:
        reason = (
            f"Invalid LUT samples: nan={nan_count}, inf={inf_count}, "
            f"out_of_range={oor_count} (domain [{eff_dmin}, {eff_dmax}])."
        )

    return Cube3dLutValidationResult(
        valid=valid,
        grid_size=eff_grid,
        expected_entries=expected_entries,
        parsed_entries=len(parsed_rows),
        nan_count=nan_count,
        inf_count=inf_count,
        out_of_range_count=oor_count,
        domain_min=eff_dmin,
        domain_max=eff_dmax,
        reason=reason,
    )


def build_synthetic_identity_cube_text(grid_size: int = 17) -> str:
    """Build a valid synthetic identity `.cube` 3D LUT (`17^3` or `33^3`)."""
    if grid_size not in CUBE_VALID_GRID_SIZES:
        raise ValueError(f"grid_size must be in {CUBE_VALID_GRID_SIZES}")
    lines = [
        'TITLE "FX3_MONITORING_IDENTITY_MLUT"',
        f"LUT_3D_SIZE {grid_size}",
        "DOMAIN_MIN 0.0 0.0 0.0",
        "DOMAIN_MAX 1.0 1.0 1.0",
    ]
    denom = float(grid_size - 1)
    for b in range(grid_size):
        fb = b / denom
        for g in range(grid_size):
            fg = g / denom
            for r in range(grid_size):
                fr = r / denom
                lines.append(f"{fr:.6f} {fg:.6f} {fb:.6f}")
    return "\n".join(lines) + "\n"


# ---------------------------------------------------------------------------
# 3. Gate G49 — 1.8V ttyAMA0 Passive RX, VMC-BNCM1 Contention & 1.8V eMMC ISP
# ---------------------------------------------------------------------------


def verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(
    *,
    guard_profile: str = "FX3_REALHW_UART1V8_TTYAMA0_VMC_BNCM1_AND_ISP_GUARD",
    uart_device: str = "/dev/ttyAMA0",
    uart_baud_rate: int = UART_CANONICAL_BAUD,
    uart_framing: str = UART_CANONICAL_FRAMING,
    uart_tap_attached: bool = True,
    uart_io_voltage_mv: float = UART_IO_NOMINAL_MV,
    tx_line_connected: bool = False,
    rx_high_z_passive: bool = True,
    camera_vcc_mv: float = 0.0,
    backpower_leakage_ua: float = 0.0,
    vmc_bncm1_attached: bool = False,
    vmc_bncm1_simultaneous_attach: Optional[bool] = None,
    offchip_emmc_isp_active: bool = False,
    isp_vccq_mv: float = EMMC_ISP_VCCQ_NOMINAL_MV,
    isp_clk_mhz: float = 24.0,
    isp_bus_width_bits: int = EMMC_ISP_REQUIRED_BUS_WIDTH_BITS,
    emmc_rst_n_held_low: bool = False,
    isp_write_cmd24_cmd25_blocked: bool = True,
    isp_mutation_bytes: int = 0,
    request_persistent_emmc_writes: bool = False,
) -> Uart1v8VmcBncm1IspGuardResult:
    """Verify Gate G49 (`1.8V CMOS ttyAMA0 460800 8N1` passive RX-only tap,
    Multi-USB `VMC-BNCM1` contention firewall & off-chip `1.8V 8-bit` eMMC ISP guard).
    """
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
    if not isinstance(uart_device, str) or not uart_device.strip():
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("uart_device must be non-empty string.")
        telemetry_ok = False
        eff_uart_dev = "/dev/ttyAMA0"
    else:
        eff_uart_dev = uart_device.strip()

    if not isinstance(uart_framing, str) or not uart_framing.strip():
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("uart_framing must be non-empty string.")
        telemetry_ok = False
        eff_framing = UART_CANONICAL_FRAMING
    else:
        eff_framing = uart_framing.strip().upper()

    if not _is_strict_int(uart_baud_rate) or uart_baud_rate <= 0:
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("uart_baud_rate must be positive integer.")
        telemetry_ok = False
        eff_baud = UART_CANONICAL_BAUD
    else:
        eff_baud = int(uart_baud_rate)

    if not _is_finite_number(uart_io_voltage_mv) or float(uart_io_voltage_mv) < 0.0:
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("uart_io_voltage_mv must be finite >= 0.0.")
        telemetry_ok = False
        eff_uart_mv = UART_IO_NOMINAL_MV
    else:
        eff_uart_mv = float(uart_io_voltage_mv)

    if not _is_finite_number(camera_vcc_mv) or float(camera_vcc_mv) < 0.0:
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("camera_vcc_mv must be finite >= 0.0.")
        telemetry_ok = False
        eff_cam_vcc = 0.0
    else:
        eff_cam_vcc = float(camera_vcc_mv)

    if not _is_finite_number(backpower_leakage_ua) or float(backpower_leakage_ua) < 0.0:
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("backpower_leakage_ua must be finite >= 0.0.")
        telemetry_ok = False
        eff_leak_ua = 0.0
    else:
        eff_leak_ua = float(backpower_leakage_ua)

    if not _is_finite_number(isp_vccq_mv) or float(isp_vccq_mv) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("isp_vccq_mv must be finite > 0.0.")
        telemetry_ok = False
        eff_isp_vccq = EMMC_ISP_VCCQ_NOMINAL_MV
    else:
        eff_isp_vccq = float(isp_vccq_mv)

    if not _is_finite_number(isp_clk_mhz) or float(isp_clk_mhz) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("isp_clk_mhz must be finite > 0.0.")
        telemetry_ok = False
        eff_isp_clk = 24.0
    else:
        eff_isp_clk = float(isp_clk_mhz)

    if not _is_strict_int(isp_bus_width_bits) or isp_bus_width_bits <= 0:
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("isp_bus_width_bits must be positive integer.")
        telemetry_ok = False
        eff_bus_bits = EMMC_ISP_REQUIRED_BUS_WIDTH_BITS
    else:
        eff_bus_bits = int(isp_bus_width_bits)

    if not _is_non_negative_int(isp_mutation_bytes):
        _add_code(codes, STATUS_BLOCKED_G49_TELEMETRY_INVALID)
        errors.append("isp_mutation_bytes must be non-negative integer.")
        telemetry_ok = False
        eff_isp_mut = 0
    else:
        eff_isp_mut = int(isp_mutation_bytes)

    eff_simultaneous = (
        bool(vmc_bncm1_simultaneous_attach)
        if vmc_bncm1_simultaneous_attach is not None
        else (bool(uart_tap_attached) and bool(vmc_bncm1_attached))
    )

    # 1) 1.8V CMOS ttyAMA0 (460800 8N1) Passive RX-Only Tap
    uart_ok = validate_uart_1v8_passive_rx(
        uart_device=eff_uart_dev,
        baud_rate=eff_baud,
        framing=eff_framing,
        uart_io_voltage_mv=eff_uart_mv,
        tx_line_connected=bool(tx_line_connected),
        backpower_leakage_ua=eff_leak_ua,
        rx_high_z_passive=bool(rx_high_z_passive),
        uart_tap_attached=bool(uart_tap_attached),
    )
    uart_1v8_passive_rx_safe = (not telemetry_ok) or uart_ok
    if telemetry_ok and not uart_ok:
        _add_code(codes, STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE)
        errors.append(
            f"BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE: dev={eff_uart_dev!r}, "
            f"baud={eff_baud} {eff_framing}, uart_io_voltage_mv={eff_uart_mv:.1f}mV "
            f"(strict 1.8V CMOS [{UART_IO_MIN_MV:.0f}..{UART_IO_MAX_MV:.0f}mV]), "
            f"tx_line_connected={bool(tx_line_connected)}, rx_high_z_passive={bool(rx_high_z_passive)}, "
            f"camera_vcc_mv={eff_cam_vcc:.1f}mV, backpower_leakage_ua={eff_leak_ua:.2f}uA (max {UART_MAX_BACKPOWER_LEAKAGE_UA}uA)."
        )

    # 2) Multi-USB VMC-BNCM1 Timecode Contention Firewall
    vmc_ok = (not eff_simultaneous) and not (
        bool(uart_tap_attached) and bool(vmc_bncm1_attached)
    )
    vmc_bncm1_isolation_safe = (not telemetry_ok) or vmc_ok
    if telemetry_ok and not vmc_ok:
        _add_code(codes, STATUS_BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION)
        errors.append(
            f"BLOCKED_G49_VMC_BNCM1_MULTIPORT_CONTENTION: uart_tap_attached={bool(uart_tap_attached)}, "
            f"vmc_bncm1_attached={bool(vmc_bncm1_attached)}, "
            f"vmc_bncm1_simultaneous_attach={eff_simultaneous}; "
            f"Multi-USB UART tap and VMC-BNCM1 BNC Timecode adapter are mutually exclusive."
        )

    # 3) Off-chip 8-bit eMMC ISP 1.8V VCCQ Passive Read Guard
    isp_ok = validate_emmc_isp_1v8_passive_read(
        isp_vccq_mv=eff_isp_vccq,
        isp_clk_mhz=eff_isp_clk,
        emmc_rst_n_held_low=bool(emmc_rst_n_held_low),
        isp_write_cmd24_cmd25_blocked=bool(isp_write_cmd24_cmd25_blocked),
        offchip_emmc_isp_active=bool(offchip_emmc_isp_active),
        isp_bus_width_bits=eff_bus_bits,
        isp_mutation_bytes=eff_isp_mut,
    )
    emmc_isp_1v8_passive_safe = (not telemetry_ok) or isp_ok
    if telemetry_ok and not isp_ok:
        _add_code(codes, STATUS_BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD)
        errors.append(
            f"BLOCKED_G49_EMMC_ISP_1V8_OR_WRITE_CMD_HAZARD: active={bool(offchip_emmc_isp_active)}, "
            f"vccq={eff_isp_vccq:.1f}mV (expected [{EMMC_ISP_VCCQ_MIN_MV:.0f}..{EMMC_ISP_VCCQ_MAX_MV:.0f}mV]), "
            f"clk={eff_isp_clk:.2f}MHz (max {EMMC_ISP_MAX_CLK_MHZ}MHz), "
            f"bus_width={eff_bus_bits}bit, rst_n_low={bool(emmc_rst_n_held_low)}, "
            f"cmd24_cmd25_blocked={bool(isp_write_cmd24_cmd25_blocked)}, mutation_bytes={eff_isp_mut}."
        )

    if telemetry_ok and len(errors) == 0 and bool(offchip_emmc_isp_active):
        warnings.append(
            f"Off-chip 8-bit eMMC ISP passive read active at {eff_isp_vccq:.0f}mV / {eff_isp_clk:.1f}MHz "
            f"with SoC RESET# held low and CMD24/CMD25 blocked."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return Uart1v8VmcBncm1IspGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile),
        uart_device=eff_uart_dev,
        uart_baud_rate=eff_baud,
        uart_framing=eff_framing,
        uart_tap_attached=bool(uart_tap_attached),
        uart_io_voltage_mv=round(eff_uart_mv, 2),
        tx_line_connected=bool(tx_line_connected),
        rx_high_z_passive=bool(rx_high_z_passive),
        camera_vcc_mv=round(eff_cam_vcc, 2),
        backpower_leakage_ua=round(eff_leak_ua, 3),
        vmc_bncm1_attached=bool(vmc_bncm1_attached),
        vmc_bncm1_simultaneous_attach=eff_simultaneous,
        offchip_emmc_isp_active=bool(offchip_emmc_isp_active),
        isp_vccq_mv=round(eff_isp_vccq, 2),
        isp_clk_mhz=round(eff_isp_clk, 3),
        isp_bus_width_bits=eff_bus_bits,
        emmc_rst_n_held_low=bool(emmc_rst_n_held_low),
        isp_write_cmd24_cmd25_blocked=bool(isp_write_cmd24_cmd25_blocked),
        isp_mutation_bytes=eff_isp_mut,
        uart_1v8_passive_rx_safe=uart_1v8_passive_rx_safe,
        vmc_bncm1_isolation_safe=vmc_bncm1_isolation_safe,
        emmc_isp_1v8_passive_safe=emmc_isp_1v8_passive_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G50 — IMX510 Sensor NVS Lock, Dual-Base ISO & .cube 3D MLUT Guard
# ---------------------------------------------------------------------------


def verify_imx510_sensor_cal_and_mlut_guard(
    *,
    guard_profile: str = "FX3_REALHW_IMX510_SENSOR_CAL_DUAL_ISO_AND_MLUT_GUARD",
    p2_setting_ro_locked: bool = True,
    p18_lens_ro_locked: bool = True,
    same_body_sensor_cal_sha256_match: bool = True,
    psd_bin_sha256: str = DEFAULT_SYNTHETIC_PSD_SHA256,
    expected_psd_bin_sha256: str = DEFAULT_SYNTHETIC_PSD_SHA256,
    defdet_bin_sha256: str = DEFAULT_SYNTHETIC_DEFDET_SHA256,
    expected_defdet_bin_sha256: str = DEFAULT_SYNTHETIC_DEFDET_SHA256,
    lensfile_bin_sha256: str = DEFAULT_SYNTHETIC_LENSFILE_SHA256,
    expected_lensfile_bin_sha256: str = DEFAULT_SYNTHETIC_LENSFILE_SHA256,
    sensor_cal_mutation_bytes: int = 0,
    sensor_cal_writes_requested: int = 0,
    cross_body_or_fx6_cal_import_attempted: bool = False,
    base_iso: int = IMX510_BASE_ISO_LOW,
    conversion_gain_mode: str = IMX510_GAIN_MODE_LCG,
    target_iso: int = IMX510_BASE_ISO_LOW,
    analog_gain_db: float = 0.0,
    recording_color_space: str = "S-Log3/S-Gamut3.Cine",
    cube_text: Optional[str] = None,
    lut_triplets: Optional[Sequence[Sequence[float]]] = None,
    cube_grid_size: int = 17,
    cube_domain_min: float = CUBE_DOMAIN_MIN_VALUE,
    cube_domain_max: float = CUBE_DOMAIN_MAX_VALUE,
    mlut_monitoring_enabled: bool = True,
    mlut_burn_in_to_xavc_master: bool = False,
    mlut_burn_in_authorized: bool = False,
    mlut_double_bake_detected: bool = False,
    request_persistent_emmc_writes: bool = False,
) -> Imx510SensorCalMlutGuardResult:
    """Verify Gate G50 (`IMX510` `p2:/setting/psd.bin & defdet.bin` per-sensor
    calibration NVS immutability, Dual-Base ISO `800/12800` gain bounds & `.cube`
    3D MLUT non-double-bake guard).
    """
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
    for lbl, val in (
        ("psd_bin_sha256", psd_bin_sha256),
        ("expected_psd_bin_sha256", expected_psd_bin_sha256),
        ("defdet_bin_sha256", defdet_bin_sha256),
        ("expected_defdet_bin_sha256", expected_defdet_bin_sha256),
        ("lensfile_bin_sha256", lensfile_bin_sha256),
        ("expected_lensfile_bin_sha256", expected_lensfile_bin_sha256),
    ):
        if not isinstance(val, str) or not _HEX64_RE.match(val.strip().lower()):
            _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
            errors.append(f"{lbl} must be 64-char hex SHA-256.")
            telemetry_ok = False

    if not isinstance(conversion_gain_mode, str) or not conversion_gain_mode.strip():
        _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
        errors.append("conversion_gain_mode must be non-empty string.")
        telemetry_ok = False
        eff_gain_mode = IMX510_GAIN_MODE_LCG
    else:
        eff_gain_mode = conversion_gain_mode.strip().upper()

    if not isinstance(recording_color_space, str) or not recording_color_space.strip():
        _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
        errors.append("recording_color_space must be non-empty string.")
        telemetry_ok = False
        eff_cs = "S-Log3/S-Gamut3.Cine"
    else:
        eff_cs = recording_color_space.strip()

    if not _is_non_negative_int(sensor_cal_mutation_bytes):
        _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
        errors.append("sensor_cal_mutation_bytes must be non-negative int.")
        telemetry_ok = False
        eff_cal_mut = 0
    else:
        eff_cal_mut = int(sensor_cal_mutation_bytes)

    if not _is_non_negative_int(sensor_cal_writes_requested):
        _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
        errors.append("sensor_cal_writes_requested must be non-negative int.")
        telemetry_ok = False
        eff_cal_req = 0
    else:
        eff_cal_req = int(sensor_cal_writes_requested)

    if not _is_strict_int(base_iso) or base_iso <= 0:
        _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
        errors.append("base_iso must be positive int.")
        telemetry_ok = False
        eff_base_iso = IMX510_BASE_ISO_LOW
    else:
        eff_base_iso = int(base_iso)

    if not _is_strict_int(target_iso) or target_iso <= 0:
        _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
        errors.append("target_iso must be positive int.")
        telemetry_ok = False
        eff_target_iso = IMX510_BASE_ISO_LOW
    else:
        eff_target_iso = int(target_iso)

    if not _is_finite_number(analog_gain_db):
        _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
        errors.append("analog_gain_db must be finite float.")
        telemetry_ok = False
        eff_gain_db = 0.0
    else:
        eff_gain_db = float(analog_gain_db)

    if not _is_strict_int(cube_grid_size) or cube_grid_size <= 0:
        _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
        errors.append("cube_grid_size must be positive int.")
        telemetry_ok = False
        eff_grid_arg = 17
    else:
        eff_grid_arg = int(cube_grid_size)

    if not (_is_finite_number(cube_domain_min) and _is_finite_number(cube_domain_max)):
        _add_code(codes, STATUS_BLOCKED_G50_TELEMETRY_INVALID)
        errors.append("cube_domain_min and cube_domain_max must be finite floats.")
        telemetry_ok = False
        eff_dmin = CUBE_DOMAIN_MIN_VALUE
        eff_dmax = CUBE_DOMAIN_MAX_VALUE
    else:
        eff_dmin = float(cube_domain_min)
        eff_dmax = float(cube_domain_max)

    eff_psd = psd_bin_sha256.strip().lower() if isinstance(psd_bin_sha256, str) else ""
    eff_exp_psd = (
        expected_psd_bin_sha256.strip().lower()
        if isinstance(expected_psd_bin_sha256, str)
        else ""
    )
    eff_defdet = (
        defdet_bin_sha256.strip().lower() if isinstance(defdet_bin_sha256, str) else ""
    )
    eff_exp_defdet = (
        expected_defdet_bin_sha256.strip().lower()
        if isinstance(expected_defdet_bin_sha256, str)
        else ""
    )
    eff_lens = (
        lensfile_bin_sha256.strip().lower()
        if isinstance(lensfile_bin_sha256, str)
        else ""
    )
    eff_exp_lens = (
        expected_lensfile_bin_sha256.strip().lower()
        if isinstance(expected_lensfile_bin_sha256, str)
        else ""
    )

    # 1) Per-Sensor Calibration NVS Immutability (psd.bin, defdet.bin, LENSFILE.BIN)
    cal_ok = validate_sensor_calibration_nvs_lock(
        psd_bin_sha256=eff_psd,
        expected_psd_bin_sha256=eff_exp_psd,
        defdet_bin_sha256=eff_defdet,
        expected_defdet_bin_sha256=eff_exp_defdet,
        lensfile_bin_sha256=eff_lens,
        expected_lensfile_bin_sha256=eff_exp_lens,
        same_body_sensor_cal_sha256_match=bool(same_body_sensor_cal_sha256_match),
        sensor_cal_mutation_bytes=eff_cal_mut,
        sensor_cal_writes_requested=eff_cal_req,
        p2_setting_ro_locked=bool(p2_setting_ro_locked),
        p18_lens_ro_locked=bool(p18_lens_ro_locked),
        cross_body_or_fx6_cal_import_attempted=bool(
            cross_body_or_fx6_cal_import_attempted
        ),
    )
    sensor_cal_nvs_lock_safe = (not telemetry_ok) or cal_ok
    if telemetry_ok and not cal_ok:
        _add_code(codes, STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY)
        errors.append(
            f"BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY: p2_ro={bool(p2_setting_ro_locked)}, "
            f"p18_ro={bool(p18_lens_ro_locked)}, same_body_match={bool(same_body_sensor_cal_sha256_match)}, "
            f"mutation_bytes={eff_cal_mut}, writes_req={eff_cal_req}, "
            f"cross_body_import={bool(cross_body_or_fx6_cal_import_attempted)}, "
            f"psd_match={eff_psd == eff_exp_psd}, defdet_match={eff_defdet == eff_exp_defdet}, "
            f"lensfile_match={eff_lens == eff_exp_lens}."
        )

    # 2) IMX510 Dual-Base ISO (800 LCG / 12800 HCG) Legal Analog Gain Bounds
    iso_ok, iso_reason = validate_imx510_dual_base_iso_gain(
        base_iso=eff_base_iso,
        conversion_gain_mode=eff_gain_mode,
        target_iso=eff_target_iso,
        analog_gain_db=eff_gain_db,
    )
    dual_base_iso_gain_safe = (not telemetry_ok) or iso_ok
    if telemetry_ok and not iso_ok:
        _add_code(codes, STATUS_BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS)
        errors.append(
            f"BLOCKED_G50_IMX510_DUAL_BASE_ISO_GAIN_OUT_OF_BOUNDS: {iso_reason}"
        )

    # 3) .cube 3D LUT Validation (17^3 / 33^3) & S-Log3 XAVC Master Non-Double-Bake Guard
    cube_res = validate_cube_3dlut(
        cube_text=cube_text,
        lut_triplets=lut_triplets,
        grid_size=eff_grid_arg,
        domain_min=eff_dmin,
        domain_max=eff_dmax,
    )
    is_slog3_master = eff_cs in SLOG3_RECORDING_COLOR_SPACES or "s-log3" in eff_cs.lower() or "slog3" in eff_cs.lower()
    double_bake_violation = (
        bool(mlut_double_bake_detected)
        or (
            bool(mlut_burn_in_to_xavc_master)
            and (not bool(mlut_burn_in_authorized))
            and (is_slog3_master or bool(mlut_monitoring_enabled))
        )
    )
    mlut_double_bake_blocked = not double_bake_violation
    cube_and_mlut_ok = cube_res.valid and mlut_double_bake_blocked
    cube_3dlut_and_non_double_bake_safe = (not telemetry_ok) or cube_and_mlut_ok
    if telemetry_ok and not cube_and_mlut_ok:
        _add_code(codes, STATUS_BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE)
        errors.append(
            f"BLOCKED_G50_CUBE_3DLUT_INVALID_OR_DOUBLE_BAKE: cube_valid={cube_res.valid} "
            f"({cube_res.reason}), recording_color_space={eff_cs!r}, "
            f"mlut_monitoring_enabled={bool(mlut_monitoring_enabled)}, "
            f"mlut_burn_in_to_xavc_master={bool(mlut_burn_in_to_xavc_master)}, "
            f"mlut_burn_in_authorized={bool(mlut_burn_in_authorized)}, "
            f"mlut_double_bake_detected={bool(mlut_double_bake_detected)}."
        )

    if (
        telemetry_ok
        and len(errors) == 0
        and bool(mlut_burn_in_to_xavc_master)
        and bool(mlut_burn_in_authorized)
    ):
        warnings.append(
            "Explicit mlut_burn_in_authorized=True override supplied: monitoring MLUT burn-in allowed for non-S-Log3 master test."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return Imx510SensorCalMlutGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile),
        p2_setting_ro_locked=bool(p2_setting_ro_locked),
        p18_lens_ro_locked=bool(p18_lens_ro_locked),
        same_body_sensor_cal_sha256_match=bool(same_body_sensor_cal_sha256_match),
        psd_bin_sha256=eff_psd,
        expected_psd_bin_sha256=eff_exp_psd,
        defdet_bin_sha256=eff_defdet,
        expected_defdet_bin_sha256=eff_exp_defdet,
        lensfile_bin_sha256=eff_lens,
        expected_lensfile_bin_sha256=eff_exp_lens,
        sensor_cal_mutation_bytes=eff_cal_mut,
        sensor_cal_writes_requested=eff_cal_req,
        cross_body_or_fx6_cal_import_attempted=bool(
            cross_body_or_fx6_cal_import_attempted
        ),
        base_iso=eff_base_iso,
        conversion_gain_mode=eff_gain_mode,
        target_iso=eff_target_iso,
        analog_gain_db=round(eff_gain_db, 3),
        recording_color_space=eff_cs,
        cube_grid_size=cube_res.grid_size,
        cube_entries_verified=cube_res.parsed_entries,
        cube_nan_count=cube_res.nan_count,
        cube_inf_count=cube_res.inf_count,
        cube_out_of_range_count=cube_res.out_of_range_count,
        mlut_monitoring_enabled=bool(mlut_monitoring_enabled),
        mlut_burn_in_to_xavc_master=bool(mlut_burn_in_to_xavc_master),
        mlut_burn_in_authorized=bool(mlut_burn_in_authorized),
        mlut_double_bake_blocked=mlut_double_bake_blocked,
        sensor_cal_nvs_lock_safe=sensor_cal_nvs_lock_safe,
        dual_base_iso_gain_safe=dual_base_iso_gain_safe,
        cube_3dlut_and_non_double_bake_safe=cube_3dlut_and_non_double_bake_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 5. Gate G49 & Gate G50 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g49_uart1v8_isp(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase158DonorAuditResult] = None,
) -> Tuple[GateVerdict, G49Uart1v8IspResult]:
    """Evaluate Gate G49 (`uart1v8_ttyama0_passive_rx_vmc_bncm1_and_emmc_isp_firewall`)."""
    audit = donor_audit or audit_phase158_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_kwargs = dict(uart1v8_isp_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_uart1v8_vmc_bncm1_and_emmc_isp_guard(**eff_kwargs)

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
        STATUS_VERIFIED_G49
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_G49_UART_1V8_OVERVOLTAGE_OR_TX_ACTIVE
        )
    )

    res = G49Uart1v8IspResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        uart1v8_isp_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G49_GATE_ID,
        gate_code=G49_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"1.8V ttyAMA0 ({guard_res.uart_baud_rate} {guard_res.uart_framing}, "
            f"{guard_res.uart_io_voltage_mv:.0f}mV, tx={guard_res.tx_line_connected}, "
            f"leak={guard_res.backpower_leakage_ua:.1f}uA), VMC-BNCM1 simultaneous="
            f"{guard_res.vmc_bncm1_simultaneous_attach}, 8-bit 1.8V ISP={guard_res.isp_vccq_mv:.0f}mV@"
            f"{guard_res.isp_clk_mhz:.1f}MHz ({guard_res.status}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "uart_1v8_passive_rx_safe": guard_res.uart_1v8_passive_rx_safe,
            "vmc_bncm1_isolation_safe": guard_res.vmc_bncm1_isolation_safe,
            "emmc_isp_1v8_passive_safe": guard_res.emmc_isp_1v8_passive_safe,
        },
    )
    return verdict, res


def evaluate_g50_imx510_sensor_cal(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase158DonorAuditResult] = None,
) -> Tuple[GateVerdict, G50Imx510SensorCalResult]:
    """Evaluate Gate G50 (`imx510_psd_defdet_nvs_lock_dual_iso_and_mlut_guard`)."""
    audit = donor_audit or audit_phase158_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
    )

    eff_kwargs = dict(imx510_sensor_cal_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes
        or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    guard_res = verify_imx510_sensor_cal_and_mlut_guard(**eff_kwargs)

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
        STATUS_VERIFIED_G50
        if passed
        else (
            codes[0]
            if codes
            else STATUS_BLOCKED_G50_SENSOR_CAL_NVS_MUTATION_OR_CROSS_BODY
        )
    )

    res = G50Imx510SensorCalResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        imx510_sensor_cal_guard=guard_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G50_GATE_ID,
        gate_code=G50_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"IMX510 p2:/setting/psd.bin+defdet.bin & p18:/lens/LENSFILE.BIN NVS Lock "
            f"(mut={guard_res.sensor_cal_mutation_bytes}B, same_body={guard_res.same_body_sensor_cal_sha256_match}), "
            f"Dual-Base ISO {guard_res.base_iso}/{guard_res.conversion_gain_mode} "
            f"(target={guard_res.target_iso}, gain={guard_res.analog_gain_db:.1f}dB), "
            f".cube={guard_res.cube_grid_size}^3 MLUT non-double-bake={guard_res.mlut_double_bake_blocked} "
            f"({guard_res.status}, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "sensor_cal_nvs_lock_safe": guard_res.sensor_cal_nvs_lock_safe,
            "dual_base_iso_gain_safe": guard_res.dual_base_iso_gain_safe,
            "cube_3dlut_and_non_double_bake_safe": guard_res.cube_3dlut_and_non_double_bake_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Unified 50-Gate Master Safety Preflight (`G01..G50`)
# ---------------------------------------------------------------------------


def evaluate_50gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G48 pass-throughs
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
    hdmi_aoc_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_media_kwargs: Optional[Mapping[str, Any]] = None,
    usbpd_uvc_kwargs: Optional[Mapping[str, Any]] = None,
    multiterminal_ptp_kwargs: Optional[Mapping[str, Any]] = None,
    monsoon_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    cagetwist_xlrh1_kwargs: Optional[Mapping[str, Any]] = None,
    vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None,
    vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None,
    jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None,
    cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None,
    service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None,
    stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None,
    pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None,
    rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None,
    # G49 inputs (1.8V ttyAMA0 passive RX, VMC-BNCM1 contention & 1.8V eMMC ISP)
    uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None,
    # G50 inputs (IMX510 psd.bin/defdet.bin NVS lock, Dual-Base ISO & .cube MLUT)
    imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master50GateReport:
    """Evaluate all 50 Master Safety Gates (`G01..G50`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m48_kwargs: Dict[str, Any] = {
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
        "hdmi_aoc_kwargs": hdmi_aoc_kwargs,
        "cfexpress_media_kwargs": cfexpress_media_kwargs,
        "usbpd_uvc_kwargs": usbpd_uvc_kwargs,
        "multiterminal_ptp_kwargs": multiterminal_ptp_kwargs,
        "monsoon_mishoe_kwargs": monsoon_mishoe_kwargs,
        "cagetwist_xlrh1_kwargs": cagetwist_xlrh1_kwargs,
        "vp_strobe_genlock_kwargs": vp_strobe_genlock_kwargs,
        "vehiclerig_ibis_kwargs": vehiclerig_ibis_kwargs,
        "jiritsu_service_kwargs": jiritsu_service_kwargs,
        "cnflasha_dualboot_kwargs": cnflasha_dualboot_kwargs,
        "service_0336_canary_kwargs": service_0336_canary_kwargs,
        "stageb_mpr_ibis_p18_kwargs": stageb_mpr_ibis_p18_kwargs,
        "pnflasha_mtdro_kwargs": pnflasha_mtdro_kwargs,
        "rfnvs_fan_power_kwargs": rfnvs_fan_power_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m48_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m48_report: Master48GateReport = evaluate_48gate_preflight(
        resolved_root, **m48_kwargs
    )

    phase158_audit = audit_phase158_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g49_verdict, g49_res = evaluate_g49_uart1v8_isp(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        uart1v8_isp_kwargs=uart1v8_isp_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase158_audit,
    )

    g50_verdict, g50_res = evaluate_g50_imx510_sensor_cal(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        imx510_sensor_cal_kwargs=imx510_sensor_cal_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase158_audit,
    )

    gates_49_to_50 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g49_verdict, g50_verdict)
    ]
    all_gates = tuple(list(m48_report.gates) + gates_49_to_50)

    g01_to_g12_verified = int(m48_report.summary["g01_to_g12_verified"])
    g13_to_g48_verified = (
        int(m48_report.summary["g13_to_g46_verified"])
        + int(m48_report.summary["g47_to_g48_verified"])
    )
    g49_to_g50_verified = sum(1 for v in (g49_verdict, g50_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g48_verified + g49_to_g50_verified

    g49_to_g50_all_passed = g49_to_g50_verified == 2
    g13_to_g50_all_passed = (
        m48_report.g13_to_g48_all_passed and g49_to_g50_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m48_report.gates[:9])

    offline_47_verified = (
        g01_to_g09_ok
        and m48_report.offline_45_gates_verified
        and g49_to_g50_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_50_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g50_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes; never authorizes eMMC/SPI-NOR writes
    overall_ready_for_hardware_attach = False

    h0_h1_allowed = (
        offline_47_verified
        and m48_report.h0_h1_trial_entry_allowed
        and g49_to_g50_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m48_report.errors) + list(g49_verdict.errors) + list(g50_verdict.errors)
    )
    warnings: List[str] = (
        list(m48_report.warnings)
        + list(g49_verdict.warnings)
        + list(g50_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m48_report.g13_to_g48_all_passed:
        overall_status = m48_report.status
    elif not g49_verdict.passed:
        overall_status = g49_verdict.status
    elif not g50_verdict.passed:
        overall_status = g50_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_50_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_50_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_50_verified:
        overall_status = "VERIFIED_ALL_50_GATES"
    else:
        overall_status = "VERIFIED_47_OF_50_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m48_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g49_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g50_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 50,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 50 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g48_verified": g13_to_g48_verified,
        "g49_to_g50_verified": g49_to_g50_verified,
        "g13_to_g50_all_passed": g13_to_g50_all_passed,
        "g49_to_g50_all_passed": g49_to_g50_all_passed,
        "offline_47_gates_verified": offline_47_verified,
        "all_50_gates_verified": all_50_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
    }

    return Master50GateReport(
        schema=REALHW_UART1V8_IMX510_50GATE_SCHEMA,
        version=REALHW_UART1V8_IMX510_50GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_47_gates_verified=offline_47_verified,
        all_50_gates_verified=all_50_verified,
        g13_to_g50_all_passed=g13_to_g50_all_passed,
        g49_to_g50_all_passed=g49_to_g50_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_48_report=m48_report.to_dict(),
        g49_result=g49_res.to_dict(),
        g50_result=g50_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_50_master_safety_gates = evaluate_50gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_uart1v8_imx510_cal_and_50gate_guard",
        description=(
            "Phase 158 — 1.8V ttyAMA0 Passive RX & VMC-BNCM1 Contention / 1.8V eMMC ISP "
            "Firewall (G49), IMX510 psd.bin/defdet.bin NVS Lock, Dual-Base ISO & .cube 3D MLUT "
            "Non-Double-Bake Guard (G50), and 50-Gate Master Preflight (G01..G50)"
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
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G50 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_50gate_preflight(
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
            f"verified={report.summary['verified_gates']}/50 "
            f"g49_to_g50_all_passed={report.g49_to_g50_all_passed} "
            f"all_50_gates_verified={report.all_50_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_50_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_47_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
