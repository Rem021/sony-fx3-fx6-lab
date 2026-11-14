"""Phase 50 — 16-Gate Master Safety Preflight Engine (`G1..G16`).

Composes `preflight.evaluate_12_safety_gates` (`G01..G12`) with four
deterministic Stage-B / Hardware-Session Safety Gates (`G13..G16`):

- `G13` (`MULTI_PORT_AND_MISHOE_FIXTURE_ISOLATION`):
  Integrates Phase 38 `crsdk_mishoe_ltc_spacc_guard` + `multiport_bootrom_unbrick`
  RP2040-Zero `-DOPEN_DRAIN` (`1.8V/3.15V`) verification: blocks `VMC-BNCM1` LTC
  pin-sharing conflicts during `uart_boot`, validates `1.8V/3.3V` open-drain
  electrical bounds, enforces `P11` `0x91db059b -> 0x88000002` + `XLR-H1`
  coexistence (`xlr_h1_preserved == True`), and audits CrSDK PTP2 & SPACC.
- `G14` (`THERMAL_PWM_AND_NPFZ100_USBPD_ENVELOPE`):
  Integrates Phase 44 `thermal_pwm_and_power_guard`: enforces `CXD90057`
  `SoC < 62.0°C` session start headroom, FX3 compact fan PWM envelope
  (`libfan.so` `@ 0x1dec`, 4 menu modes, `82°C` warning, `90°C` fail-closed
  graceful unmount & RAM-overlay teardown), `NP-FZ100 >= 80% / >= 7800 mV`
  InfoLITHIUM normalization (blocking `BP-U 11500 mV` comparators), and
  `USB-PD 9V/3A` (`>= 27W`) with VBUS droop `<= 450 mV`.
- `G15` (`C2PA_KEYSTORE_AND_FACTORY_CALIBRATION_IMMUTABILITY`):
  Verifies zero mount/write paths targeting `cnflasha*`, `RPMB`, TrustZone /
  OP-TEE keystore / Sony C2PA credentials (`RQ_LIC.DAT`, `sigcert.p12/.pfx`,
  `p12:/cert`), or factory IMX510/IBIS/lens calibration regions (`psd.bin`,
  `defdet.bin`, `Backup.bin`, `p6:/tmp/jiritsu`, `p18:/lens/lensfile.bin`,
  `SPI NOR ddrtraining.dat`, `adjstctl A_*`), enforces `calibration_mutation_bytes == 0`,
  and validates exFAT/media power-loss hygiene (`VolumeDirty` / unfinalized `.RSV`).
- `G16` (`STAGE_B_P12_WF12_AND_WBI2_COLD_BOOT_LOCK`):
  Verifies `P12` `0x70d4` (`libWlanResource.so::_Z16handleFatalErrorv` ->
  `mov w0, #0; ret`, `patched_rc == 0`) + `BK4\\0` Airplane-Mode RAM shadow
  (`0x019e0012=00`, `0x0051000f=00`, `0x01a20002=00` for Sony Notice `00342260`
  `WF-12` bootloop immunity), `wbi_mutation_bytes == 0` (`p5:/wbi` `WBI2` intact),
  `cp_mutation_bytes == 0` (`p8:/cp` `cpapp-b.bin` intact), and hard-locked
  `persistent_emmc_writes_authorized == False`.

Hard Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- All donor file reads strictly use `os.open(..., os.O_RDONLY)`.
- Zero raw binary `bytes` repr output (always `.hex()`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .brick_classifier import generate_failsafe_init2_overlay_hook
from .crsdk_mishoe_ltc_spacc_guard import (
    Phase38GuardReport,
    evaluate_phase38_safety_guards,
)
from .multiport_bootrom_unbrick import (
    HarnessValidationResult,
    validate_rp2040_multiport_harness,
)
from .preflight import TIER0_REQUIRED_BACKUPS, evaluate_12_safety_gates
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    Phase44ThermalPowerGuardReport,
    SOC_FAN_OVERRIDE_TEMP_C,
    evaluate_thermal_pwm_and_power_guard,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

MASTER_16GATE_PREFLIGHT_SCHEMA: str = "fx3-master-16gate-preflight-v1"
MASTER_16GATE_PREFLIGHT_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]

# Gate IDs & Canonical Codes for G13..G16
G13_GATE_ID: str = "G13_multi_port_and_mishoe_fixture_isolation"
G13_GATE_CODE: str = "MULTI_PORT_AND_MISHOE_FIXTURE_ISOLATION"

G14_GATE_ID: str = "G14_thermal_pwm_and_npfz100_usbpd_envelope"
G14_GATE_CODE: str = "THERMAL_PWM_AND_NPFZ100_USBPD_ENVELOPE"

G15_GATE_ID: str = "G15_c2pa_keystore_and_factory_calibration_immutability"
G15_GATE_CODE: str = "C2PA_KEYSTORE_AND_FACTORY_CALIBRATION_IMMUTABILITY"

G16_GATE_ID: str = "G16_stage_b_p12_wf12_and_wbi2_cold_boot_lock"
G16_GATE_CODE: str = "STAGE_B_P12_WF12_AND_WBI2_COLD_BOOT_LOCK"

# Status Codes
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G13: str = "VERIFIED_MULTI_PORT_AND_MISHOE_ISOLATED"
STATUS_VERIFIED_G14: str = "VERIFIED_THERMAL_AND_POWER_ENVELOPE"
STATUS_VERIFIED_G15: str = "VERIFIED_C2PA_AND_CALIBRATION_IMMUTABLE"
STATUS_VERIFIED_G16: str = "VERIFIED_STAGE_B_P12_AND_WBI2_LOCKED"

STATUS_BLOCKED_G13_FIXTURE_ISOLATION: str = "BLOCKED_BY_G13_MULTI_PORT_OR_MISHOE_ISOLATION"
STATUS_BLOCKED_G13_HARNESS_OPEN_DRAIN: str = "BLOCKED_BY_G13_HARNESS_OPEN_DRAIN_HAZARD"
STATUS_BLOCKED_G14_THERMAL_POWER: str = "BLOCKED_BY_G14_THERMAL_OR_POWER_ENVELOPE"
STATUS_BLOCKED_SOC_START_HEADROOM: str = "BLOCKED_BY_SOC_START_HEADROOM_EXCEEDED"
STATUS_BLOCKED_G15_C2PA_KEYSTORE: str = "BLOCKED_BY_G15_C2PA_KEYSTORE_OR_TZ_TARGET"
STATUS_BLOCKED_G15_CALIBRATION_MUTATION: str = "BLOCKED_BY_G15_FACTORY_CALIBRATION_MUTATION"
STATUS_BLOCKED_G15_CNFLASHA_OR_RPMB: str = "BLOCKED_BY_G15_CNFLASHA_OR_RPMB_TARGET"
STATUS_BLOCKED_G15_EXFAT_HYGIENE: str = "BLOCKED_BY_G15_EXFAT_MEDIA_HYGIENE"
STATUS_BLOCKED_G16_P12_WF12_GUARD: str = "BLOCKED_BY_G16_STAGE_B_P12_WF12_GUARD"
STATUS_BLOCKED_G16_WBI2_OR_CP_MUTATION: str = "BLOCKED_BY_G16_WBI2_OR_CP_MUTATION"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"

# Wave-4 / Stage-B P12 & Calibration Constants
SOC_START_HEADROOM_CEILING_C: float = SOC_FAN_OVERRIDE_TEMP_C  # 62.0 C

P12_WLAN_FATAL_GUARD_VMA: int = 0x70D4
FX6_WLAN_RSRC_DONOR_SIZE: int = 56464
FX6_WLAN_RSRC_DONOR_SHA256: str = (
    "eb7785e025d11eefced79de3a918034960422ee75dc09b0fead69646f7e8bd88"
)
FX6_WLAN_RSRC_P12_ORIG_HEX: str = "fd7bbea9fd030091"
FX6_WLAN_RSRC_P12_PATCHED_HEX: str = "00008052c0035fd6"

BK4_AIRPLANE_SHADOW_REQUIRED: Dict[int, int] = {
    0x019E0012: 0x00,
    0x0051000F: 0x00,
    0x01A20002: 0x00,
}

# Protected G15 path/token categories (lowercased substrings)
PROTECTED_CNFLASHA_TOKENS: Tuple[str, ...] = (
    "/dev/cnflasha",
    "cnflasha",
)

PROTECTED_RPMB_TOKENS: Tuple[str, ...] = (
    "rpmb",
    "mmcblk0rpmb",
    "ext_csd[179]=3",
    "partition_access=3",
)

PROTECTED_TRUSTZONE_C2PA_TOKENS: Tuple[str, ...] = (
    "trustzone",
    "optee",
    "/dev/tee",
    "bl31",
    "bl32",
    "c2pa",
    "keystore",
    "rq_lic.dat",
    "sigcert.p12",
    "sigcert.pfx",
    "p12:/cert",
    "/dev/nflasha12",
    "/dev/pnflasha12",
)

PROTECTED_FACTORY_CALIBRATION_TOKENS: Tuple[str, ...] = (
    "psd.bin",
    "defdet.bin",
    "backup.bin",
    "backup.bak",
    "p2:/setting",
    "/setting/psd",
    "/setting/defdet",
    "/setting/backup",
    "/dev/nflasha2",
    "/dev/pnflasha2",
    "p6:/tmp/jiritsu",
    "/tmp/jiritsu",
    "/dev/nflasha6",
    "/dev/pnflasha6",
    "p18:/lens",
    "lensfile.bin",
    "/lens/lensfile",
    "/dev/nflasha18",
    "/dev/pnflasha18",
    "ddrtraining",
    "/dev/mtd0",
    "spi_nor",
    "nflashab0",
    "nflashab1",
    "/dev/boot0",
    "/dev/boot1",
    "sector0",
    "adjstctl",
    "ibis_cal",
    "pixel_map",
)

SAFE_TMPFS_RAM_PREFIXES: Tuple[str, ...] = (
    "/tmp/",
    "/run/",
    "/var/tmp/",
)


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class GateVerdict:
    gate_id: str
    gate_code: str
    passed: bool
    status: str
    evidence: str
    violation_codes: Tuple[str, ...] = ()
    errors: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class C2paCalibrationImmutabilityResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    calibration_mutation_bytes: int
    cnflasha_protected: bool
    rpmb_protected: bool
    trustzone_c2pa_keystore_protected: bool
    factory_sensor_ibis_protected: bool
    exfat_media_hygiene_ok: bool
    volatile_tmpfs_ram_overlay_only: bool
    persistent_emmc_writes_authorized: bool
    blocked_targets: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageBP12Wbi2LockResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    p12_vma_hex: str
    p12_guard_verified: bool
    p12_patched_rc: int
    bk4_airplane_shadow_verified: bool
    wf12_bootloop_immune: bool
    wbi_mutation_bytes: int
    cp_mutation_bytes: int
    nvram_persistent_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master16GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    all_16_gates_verified: bool
    offline_13_gates_verified: bool
    g13_to_g16_all_passed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    g13_result: Dict[str, Any]
    g14_result: Dict[str, Any]
    g15_result: Dict[str, Any]
    g16_result: Dict[str, Any]
    preflight_12_report: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


def _read_file_o_rdonly(path: Path) -> bytes:
    """Strictly read a file via os.O_RDONLY without printing raw bytes repr."""
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


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _build_synthetic_dry_run_tier0_inputs() -> Tuple[Dict[str, object], List[Dict[str, object]], str]:
    items = {
        k: {
            "bytes": spec.get("exact_bytes") or spec.get("min_bytes") or 4096,
            "pass1_sha256": "a" * 64,
            "pass2_sha256": "a" * 64,
        }
        for k, spec in TIER0_REQUIRED_BACKUPS.items()
    }
    manifest: Dict[str, object] = {
        "camera_body_tag": "1" * 64,
        "model_id": "0x91030080",
        "items": items,
    }
    trace: List[Dict[str, object]] = [
        {"nr": 35, "dirfd": -100, "path": "/tmp/jiritsu/libJit.so", "flags": 0, "ret": 0}
    ]
    hook = generate_failsafe_init2_overlay_hook()
    return manifest, trace, hook


# ---------------------------------------------------------------------------
# Gate 13: MULTI_PORT_AND_MISHOE_FIXTURE_ISOLATION
# ---------------------------------------------------------------------------


def evaluate_g13_multiport_and_mishoe_isolation(
    *,
    ltc_kwargs: Optional[Mapping[str, Any]] = None,
    mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    crsdk_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    crsdk_kwargs: Optional[Mapping[str, Any]] = None,
    spacc_operations: Optional[Sequence[Mapping[str, Any]]] = None,
    spacc_script_text: str = "",
    spacc_sector0_bytes: Optional[bytes] = None,
    harness_kwargs: Optional[Mapping[str, Any]] = None,
) -> Tuple[GateVerdict, Phase38GuardReport, HarnessValidationResult]:
    """Evaluate Gate G13 (Phase 38 LTC/MI-Shoe/CrSDK/SPACC + RP2040 open-drain)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    p38: Phase38GuardReport = evaluate_phase38_safety_guards(
        ltc_kwargs=ltc_kwargs,
        mishoe_kwargs=mishoe_kwargs,
        crsdk_requests=crsdk_requests,
        crsdk_kwargs=crsdk_kwargs,
        spacc_operations=spacc_operations,
        spacc_script_text=spacc_script_text,
        spacc_sector0_bytes=spacc_sector0_bytes,
    )
    harness: HarnessValidationResult = validate_rp2040_multiport_harness(
        **dict(harness_kwargs or {})
    )

    if not p38.all_passed:
        _add_code(codes, p38.status)
        errors.extend(p38.errors)
    if not p38.mishoe_guard.xlr_h1_preserved:
        _add_code(codes, p38.mishoe_guard.status if not p38.mishoe_guard.valid else STATUS_BLOCKED_G13_FIXTURE_ISOLATION)
        errors.append("G13 requires P11 0x91db059b -> 0x88000002 XLR-H1 MI-Shoe coexistence preserved.")
    if not harness.valid:
        _add_code(codes, STATUS_BLOCKED_G13_HARNESS_OPEN_DRAIN)
        errors.extend(harness.errors)
    if not harness.open_drain_enforced:
        _add_code(codes, STATUS_BLOCKED_G13_HARNESS_OPEN_DRAIN)
        errors.append("G13 requires RP2040-Zero -DOPEN_DRAIN (1.8V/3.15V) open-drain signaling.")

    warnings.extend(p38.ltc_guard.warnings)
    warnings.extend(p38.mishoe_guard.warnings)
    warnings.extend(p38.crsdk_firewall.warnings)
    warnings.extend(p38.spacc_guard.warnings)
    warnings.extend(harness.warnings)

    passed = p38.all_passed and p38.mishoe_guard.xlr_h1_preserved and harness.valid and harness.open_drain_enforced and not errors
    status = STATUS_VERIFIED_G13 if passed else (codes[0] if codes else STATUS_BLOCKED_G13_FIXTURE_ISOLATION)

    verdict = GateVerdict(
        gate_id=G13_GATE_ID,
        gate_code=G13_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            "Phase 38 CrSDK/MI-Shoe/Multi-Port LTC/SPACC guard + RP2040-Zero -DOPEN_DRAIN "
            f"(board={harness.board}, io={harness.io_voltage_v}V, xlr_h1_preserved={p38.mishoe_guard.xlr_h1_preserved}, "
            f"ltc_status={p38.ltc_guard.status}, spacc_status={p38.spacc_guard.status})."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "phase38_status": p38.status,
            "ltc_guard_valid": p38.ltc_guard.valid,
            "mishoe_guard_valid": p38.mishoe_guard.valid,
            "xlr_h1_preserved": p38.mishoe_guard.xlr_h1_preserved,
            "crsdk_firewall_valid": p38.crsdk_firewall.valid,
            "spacc_guard_valid": p38.spacc_guard.valid,
            "harness_valid": harness.valid,
            "harness_board": harness.board,
            "harness_io_voltage_v": harness.io_voltage_v,
            "harness_open_drain_enforced": harness.open_drain_enforced,
        },
    )
    return verdict, p38, harness


# ---------------------------------------------------------------------------
# Gate 14: THERMAL_PWM_AND_NPFZ100_USBPD_ENVELOPE
# ---------------------------------------------------------------------------


def evaluate_g14_thermal_and_power_envelope(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    fan_kwargs: Optional[Mapping[str, Any]] = None,
    power_kwargs: Optional[Mapping[str, Any]] = None,
    soc_start_ceiling_c: float = SOC_START_HEADROOM_CEILING_C,
) -> Tuple[GateVerdict, Phase44ThermalPowerGuardReport]:
    """Evaluate Gate G14 (Phase 44 Thermal PWM + SoC < 62C start headroom + NP-FZ100 + USB-PD)."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    eff_fan_kwargs = dict(fan_kwargs or {})
    eff_power_kwargs = dict(power_kwargs or {})

    p44: Phase44ThermalPowerGuardReport = evaluate_thermal_pwm_and_power_guard(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        fan_kwargs=eff_fan_kwargs,
        power_kwargs=eff_power_kwargs,
    )

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = list(p44.warnings)

    if not p44.all_passed:
        _add_code(codes, p44.status)
        errors.extend(p44.errors)

    # Enforce SoC < 62.0C session start headroom in addition to Phase 44 envelope
    soc_temp = p44.thermal_envelope.zone_temps_c.get("cxd90057_soc_c")
    soc_start_headroom_ok = isinstance(soc_temp, (int, float)) and (float(soc_temp) < float(soc_start_ceiling_c))
    if not soc_start_headroom_ok:
        _add_code(codes, STATUS_BLOCKED_SOC_START_HEADROOM)
        errors.append(
            f"G14 start headroom violation: CXD90057 SoC={soc_temp!r}C must be strictly < "
            f"{soc_start_ceiling_c:.1f}C before starting Stage-B / hardware session."
        )

    if not p44.power_firewall.rehearsal_battery_gate_passed:
        _add_code(codes, p44.power_firewall.status if not p44.power_firewall.valid else STATUS_BLOCKED_G14_THERMAL_POWER)
        if p44.power_firewall.valid:
            errors.append("G14 requires NP-FZ100 >= 80% SOC and >= 7800 mV for hardware session.")

    if not p44.power_firewall.usbpd_stability_passed:
        _add_code(codes, p44.power_firewall.status if not p44.power_firewall.valid else STATUS_BLOCKED_G14_THERMAL_POWER)
        if p44.power_firewall.valid:
            errors.append("G14 requires USB-PD 9V/3A (27W) contract with VBUS droop <= 450 mV.")

    passed = (
        p44.all_passed
        and soc_start_headroom_ok
        and p44.power_firewall.rehearsal_battery_gate_passed
        and p44.power_firewall.usbpd_stability_passed
        and len(errors) == 0
    )
    status = STATUS_VERIFIED_G14 if passed else (codes[0] if codes else STATUS_BLOCKED_G14_THERMAL_POWER)

    verdict = GateVerdict(
        gate_id=G14_GATE_ID,
        gate_code=G14_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Phase 44 ({p44.verification_mode}): SoC={soc_temp}C (<{soc_start_ceiling_c}C start headroom), "
            f"fan_pwm={p44.thermal_envelope.target_pwm_duty_pct}%, "
            f"NP-FZ100={p44.power_firewall.infolithium_soc_pct}%/{p44.power_firewall.raw_batt_mv}mV, "
            f"USB-PD={p44.power_firewall.usbpd_contract_mw / 1000.0:.1f}W droop={p44.power_firewall.usbpd_vbus_droop_mv}mV."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": p44.verification_mode,
            "phase44_status": p44.status,
            "soc_c": soc_temp,
            "soc_start_ceiling_c": soc_start_ceiling_c,
            "soc_start_headroom_ok": soc_start_headroom_ok,
            "target_pwm_duty_pct": p44.thermal_envelope.target_pwm_duty_pct,
            "npfz100_soc_pct": p44.power_firewall.infolithium_soc_pct,
            "npfz100_mv": p44.power_firewall.raw_batt_mv,
            "usbpd_contract_mw": p44.power_firewall.usbpd_contract_mw,
            "usbpd_vbus_droop_mv": p44.power_firewall.usbpd_vbus_droop_mv,
        },
    )
    return verdict, p44


# ---------------------------------------------------------------------------
# Gate 15: C2PA_KEYSTORE_AND_FACTORY_CALIBRATION_IMMUTABILITY
# ---------------------------------------------------------------------------


def _scan_target_tokens(entry: str) -> Tuple[str, ...]:
    low = entry.strip().lower()
    hits: List[str] = []
    for cat, toks in (
        ("CNFLASHA", PROTECTED_CNFLASHA_TOKENS),
        ("RPMB", PROTECTED_RPMB_TOKENS),
        ("TRUSTZONE_C2PA", PROTECTED_TRUSTZONE_C2PA_TOKENS),
        ("FACTORY_CAL", PROTECTED_FACTORY_CALIBRATION_TOKENS),
    ):
        for tok in toks:
            if tok in low:
                hits.append(f"{cat}:{tok}")
    return tuple(hits)


def verify_c2pa_and_factory_calibration_immutability(
    *,
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    c2pa_calibration_script_text: str = "",
    calibration_mutation_bytes: int = 0,
    c2pa_keystore_writes_attempted: bool = False,
    exfat_dirty_bit_present: bool = False,
    exfat_unfinalized_rsv_present: bool = False,
    allow_c2pa_or_calibration_write: bool = False,
) -> C2paCalibrationImmutabilityResult:
    """Verify Gate G15: zero mount/write paths to cnflasha*, RPMB, TrustZone/C2PA, or calibration."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    blocked_targets: List[str] = []

    cnflasha_ok = True
    rpmb_ok = True
    tz_c2pa_ok = True
    cal_ok = True
    exfat_ok = True

    if allow_c2pa_or_calibration_write:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        cal_ok = False
        tz_c2pa_ok = False
        errors.append(
            "allow_c2pa_or_calibration_write=True is forbidden: PERSISTENT_EMMC_WRITES_AUTHORIZED=False."
        )

    if not isinstance(calibration_mutation_bytes, int) or calibration_mutation_bytes != 0:
        _add_code(codes, STATUS_BLOCKED_G15_CALIBRATION_MUTATION)
        cal_ok = False
        errors.append(
            f"calibration_mutation_bytes must equal 0 (got {calibration_mutation_bytes!r})."
        )

    if c2pa_keystore_writes_attempted:
        _add_code(codes, STATUS_BLOCKED_G15_C2PA_KEYSTORE)
        tz_c2pa_ok = False
        errors.append(
            "Attempted write to C2PA / TrustZone keystore / RQ_LIC.DAT / sigcert is strictly forbidden."
        )

    def _record_hits(label: str, raw_entry: str, hits: Tuple[str, ...]) -> None:
        nonlocal cnflasha_ok, rpmb_ok, tz_c2pa_ok, cal_ok
        if not hits:
            return
        blocked_targets.append(f"{label}:{raw_entry}")
        for h in hits:
            cat = h.split(":", 1)[0]
            if cat == "CNFLASHA":
                cnflasha_ok = False
                _add_code(codes, STATUS_BLOCKED_G15_CNFLASHA_OR_RPMB)
            elif cat == "RPMB":
                rpmb_ok = False
                _add_code(codes, STATUS_BLOCKED_G15_CNFLASHA_OR_RPMB)
            elif cat == "TRUSTZONE_C2PA":
                tz_c2pa_ok = False
                _add_code(codes, STATUS_BLOCKED_G15_C2PA_KEYSTORE)
            else:
                cal_ok = False
                _add_code(codes, STATUS_BLOCKED_G15_CALIBRATION_MUTATION)
        errors.append(
            f"Protected G15 {label} target rejected ({raw_entry!r}): matched {', '.join(hits)}."
        )

    for mnt in planned_mounts:
        _record_hits("mount", str(mnt), _scan_target_tokens(str(mnt)))

    for wr in planned_writes:
        _record_hits("write", str(wr), _scan_target_tokens(str(wr)))

    # Scan non-comment script lines for mount / write / dd / mkfs / rm / adjstctl targeting protected zones
    write_or_mount_verbs = re.compile(
        r"\b(mount|umount|dd|flashcp|mkfs|format|erase|poke|rm|mv|cp|chmod|chown|echo|tee|adjstctl)\b",
        re.IGNORECASE,
    )
    for raw_line in c2pa_calibration_script_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        hits = _scan_target_tokens(line)
        if hits and (write_or_mount_verbs.search(line) or "of=" in line.lower() or ">" in line):
            _record_hits("script", line, hits)
        elif "adjstctl" in line.lower() and re.search(r"\bA_[A-Z0-9_]+", line):
            _record_hits("script", line, ("FACTORY_CAL:adjstctl_A_cmd",))

    # Media exFAT / VFAT power-loss & dirty-bit hygiene checks
    if exfat_dirty_bit_present:
        exfat_ok = False
        _add_code(codes, STATUS_BLOCKED_G15_EXFAT_HYGIENE)
        errors.append(
            "exFAT VolumeDirty flag (VBR offset 0x6A) is set on media card; "
            "capture byte-exact image before Stage-A/B trial or recovery."
        )
    if exfat_unfinalized_rsv_present:
        exfat_ok = False
        _add_code(codes, STATUS_BLOCKED_G15_EXFAT_HYGIENE)
        errors.append(
            "Unfinalized .RSV media clip detected on CFexpress/SDXC card; "
            "archive card before running Stage-A/B trials."
        )

    valid = (
        cnflasha_ok
        and rpmb_ok
        and tz_c2pa_ok
        and cal_ok
        and exfat_ok
        and len(errors) == 0
    )
    status = STATUS_VERIFIED_G15 if valid else (codes[0] if codes else STATUS_BLOCKED_G15_CALIBRATION_MUTATION)

    return C2paCalibrationImmutabilityResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        calibration_mutation_bytes=int(calibration_mutation_bytes),
        cnflasha_protected=cnflasha_ok,
        rpmb_protected=rpmb_ok,
        trustzone_c2pa_keystore_protected=tz_c2pa_ok,
        factory_sensor_ibis_protected=cal_ok,
        exfat_media_hygiene_ok=exfat_ok,
        volatile_tmpfs_ram_overlay_only=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        blocked_targets=tuple(blocked_targets),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "fx3_c2pa_firmware_support": "v7.00..v7.02 (Write Digital Signature, paid RQ_LIC.DAT, MP4 <= 222 Mbps)",
            "fx6_c2pa_firmware_support": "NONE (v5.00..v6.02 not on Sony Camera Authenticity Solution list)",
            "protected_calibration_assets": [
                "p2:/setting/psd.bin",
                "p2:/setting/defdet.bin",
                "p2:/setting/Backup.bin",
                "p6:/tmp/jiritsu",
                "p12:/cert",
                "p18:/lens/lensfile.bin",
                "SPI_NOR:ddrtraining.dat",
            ],
            "safe_overlay_prefixes": list(SAFE_TMPFS_RAM_PREFIXES),
        },
    )


def evaluate_g15_c2pa_and_calibration(
    **kwargs: Any,
) -> Tuple[GateVerdict, C2paCalibrationImmutabilityResult]:
    res = verify_c2pa_and_factory_calibration_immutability(**kwargs)
    verdict = GateVerdict(
        gate_id=G15_GATE_ID,
        gate_code=G15_GATE_CODE,
        passed=res.valid,
        status=res.status,
        evidence=(
            f"Volatile tmpfs RAM overlay only: cnflasha_protected={res.cnflasha_protected}, "
            f"rpmb_protected={res.rpmb_protected}, tz_c2pa_protected={res.trustzone_c2pa_keystore_protected}, "
            f"factory_cal_protected={res.factory_sensor_ibis_protected}, "
            f"calibration_mutation_bytes={res.calibration_mutation_bytes}, exfat_hygiene_ok={res.exfat_media_hygiene_ok}."
        ),
        violation_codes=res.violation_codes,
        errors=res.errors,
        warnings=res.warnings,
        details=res.details,
    )
    return verdict, res


# ---------------------------------------------------------------------------
# Gate 16: STAGE_B_P12_WF12_AND_WBI2_COLD_BOOT_LOCK
# ---------------------------------------------------------------------------


def verify_stage_b_p12_wf12_and_wbi2_lock(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    p12_vma: int = P12_WLAN_FATAL_GUARD_VMA,
    p12_patched_rc: int = 0,
    p12_guard_enabled: bool = True,
    bk4_airplane_shadow: Optional[Mapping[int, int]] = None,
    wf12_bootloop_immune: bool = True,
    wbi_mutation_bytes: int = 0,
    cp_mutation_bytes: int = 0,
    nvram_persistent_writes: int = 0,
    request_persistent_emmc_writes: bool = False,
) -> StageBP12Wbi2LockResult:
    """Verify Gate G16: P12 0x70d4 + BK4 Airplane shadow + WBI2/CP/eMMC immutability."""
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    wlan_so_path = paths.fx6_lib_dir / "libWlanResource.so"

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    donor_checked = False
    donor_sha256 = FX6_WLAN_RSRC_DONOR_SHA256
    donor_orig_hex = FX6_WLAN_RSRC_P12_ORIG_HEX
    if (not clean_forced) and wlan_so_path.is_file():
        mode = "LOCAL_DONOR_O_RDONLY"
        blob = _read_file_o_rdonly(wlan_so_path)
        donor_sha256 = hashlib.sha256(blob).hexdigest()
        donor_orig_hex = blob[P12_WLAN_FATAL_GUARD_VMA : P12_WLAN_FATAL_GUARD_VMA + 8].hex()
        donor_checked = True
        if len(blob) != FX6_WLAN_RSRC_DONOR_SIZE or donor_sha256 != FX6_WLAN_RSRC_DONOR_SHA256:
            _add_code(codes, STATUS_BLOCKED_G16_P12_WF12_GUARD)
            errors.append(
                f"FX6 libWlanResource.so donor mismatch: size={len(blob)} sha256={donor_sha256}."
            )
        if donor_orig_hex != FX6_WLAN_RSRC_P12_ORIG_HEX:
            _add_code(codes, STATUS_BLOCKED_G16_P12_WF12_GUARD)
            errors.append(
                f"FX6 libWlanResource.so @ {hex(P12_WLAN_FATAL_GUARD_VMA)} hex={donor_orig_hex} != {FX6_WLAN_RSRC_P12_ORIG_HEX}."
            )
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"

    p12_ok = bool(p12_guard_enabled) and (p12_vma == P12_WLAN_FATAL_GUARD_VMA) and (p12_patched_rc == 0) and bool(wf12_bootloop_immune)
    if not p12_ok:
        _add_code(codes, STATUS_BLOCKED_G16_P12_WF12_GUARD)
        errors.append(
            f"P12 WF-12 guard invalid: enabled={p12_guard_enabled}, vma={hex(p12_vma)}, "
            f"patched_rc={p12_patched_rc}, wf12_bootloop_immune={wf12_bootloop_immune}."
        )

    shadow = dict(BK4_AIRPLANE_SHADOW_REQUIRED if bk4_airplane_shadow is None else bk4_airplane_shadow)
    bk4_ok = all(shadow.get(k) == expected for k, expected in BK4_AIRPLANE_SHADOW_REQUIRED.items())
    if not bk4_ok:
        _add_code(codes, STATUS_BLOCKED_G16_P12_WF12_GUARD)
        errors.append(
            "BK4 Airplane-Mode RAM shadow mismatch: expected "
            "{0x019e0012: 0, 0x0051000f: 0, 0x01a20002: 0}, got "
            + str({hex(k): v for k, v in shadow.items()})
        )

    wbi_cp_ok = True
    if not isinstance(wbi_mutation_bytes, int) or wbi_mutation_bytes != 0:
        wbi_cp_ok = False
        _add_code(codes, STATUS_BLOCKED_G16_WBI2_OR_CP_MUTATION)
        errors.append(f"wbi_mutation_bytes must equal 0 (got {wbi_mutation_bytes!r}).")
    if not isinstance(cp_mutation_bytes, int) or cp_mutation_bytes != 0:
        wbi_cp_ok = False
        _add_code(codes, STATUS_BLOCKED_G16_WBI2_OR_CP_MUTATION)
        errors.append(f"cp_mutation_bytes must equal 0 (got {cp_mutation_bytes!r}).")
    if not isinstance(nvram_persistent_writes, int) or nvram_persistent_writes != 0:
        wbi_cp_ok = False
        _add_code(codes, STATUS_BLOCKED_G16_WBI2_OR_CP_MUTATION)
        errors.append(f"nvram_persistent_writes must equal 0 (got {nvram_persistent_writes!r}).")

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Persistent eMMC write authorization request blocked: "
            "PERSISTENT_EMMC_WRITES_AUTHORIZED=False, PERSISTENT_WRITE_RELEASE=False."
        )

    valid = p12_ok and bk4_ok and wbi_cp_ok and (not request_persistent_emmc_writes) and len(errors) == 0
    status = STATUS_VERIFIED_G16 if valid else (codes[0] if codes else STATUS_BLOCKED_G16_P12_WF12_GUARD)

    return StageBP12Wbi2LockResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=mode,
        p12_vma_hex=hex(p12_vma),
        p12_guard_verified=p12_ok,
        p12_patched_rc=int(p12_patched_rc),
        bk4_airplane_shadow_verified=bk4_ok,
        wf12_bootloop_immune=bool(wf12_bootloop_immune),
        wbi_mutation_bytes=int(wbi_mutation_bytes),
        cp_mutation_bytes=int(cp_mutation_bytes),
        nvram_persistent_writes=int(nvram_persistent_writes),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "donor_o_rdonly_checked": donor_checked,
            "libwlan_resource_sha256": donor_sha256,
            "p12_orig_hex": donor_orig_hex,
            "p12_patched_hex": FX6_WLAN_RSRC_P12_PATCHED_HEX,
            "sony_notice_id": "00342260",
            "bk4_airplane_shadow": {hex(k): v for k, v in shadow.items()},
        },
    )


def evaluate_g16_stage_b_p12_and_wbi2_lock(
    **kwargs: Any,
) -> Tuple[GateVerdict, StageBP12Wbi2LockResult]:
    res = verify_stage_b_p12_wf12_and_wbi2_lock(**kwargs)
    verdict = GateVerdict(
        gate_id=G16_GATE_ID,
        gate_code=G16_GATE_CODE,
        passed=res.valid,
        status=res.status,
        evidence=(
            f"Stage-B P12 @ {res.p12_vma_hex} (rc={res.p12_patched_rc}) + BK4 Airplane shadow "
            f"(Notice 00342260 WF-12 immune={res.wf12_bootloop_immune}): "
            f"wbi_mutation_bytes={res.wbi_mutation_bytes}, cp_mutation_bytes={res.cp_mutation_bytes}, "
            f"persistent_emmc_writes_authorized={res.persistent_emmc_writes_authorized}."
        ),
        violation_codes=res.violation_codes,
        errors=res.errors,
        warnings=res.warnings,
        details=res.details,
    )
    return verdict, res


# ---------------------------------------------------------------------------
# Master 16-Gate Evaluator & CLI
# ---------------------------------------------------------------------------


def evaluate_16_master_safety_gates(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G12 pass-throughs
    tier0_manifest: Optional[Dict[str, object]] = None,
    worker_syscall_trace: Optional[List[Dict[str, object]]] = None,
    init2_failsafe_hook: Optional[str] = None,
    candidate_bundle_verified: Optional[bool] = None,
    allow_dry_run_gate12: bool = False,
    use_synthetic_dry_run_tier0: bool = False,
    gate12_kwargs: Optional[Mapping[str, Any]] = None,
    # G13 inputs
    ltc_kwargs: Optional[Mapping[str, Any]] = None,
    mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    crsdk_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    crsdk_kwargs: Optional[Mapping[str, Any]] = None,
    spacc_operations: Optional[Sequence[Mapping[str, Any]]] = None,
    spacc_script_text: str = "",
    spacc_sector0_bytes: Optional[bytes] = None,
    harness_kwargs: Optional[Mapping[str, Any]] = None,
    # G14 inputs
    fan_kwargs: Optional[Mapping[str, Any]] = None,
    power_kwargs: Optional[Mapping[str, Any]] = None,
    soc_start_ceiling_c: float = SOC_START_HEADROOM_CEILING_C,
    # G15 inputs
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    c2pa_calibration_script_text: str = "",
    calibration_mutation_bytes: int = 0,
    c2pa_keystore_writes_attempted: bool = False,
    exfat_dirty_bit_present: bool = False,
    exfat_unfinalized_rsv_present: bool = False,
    allow_c2pa_or_calibration_write: bool = False,
    # G16 inputs
    p12_vma: int = P12_WLAN_FATAL_GUARD_VMA,
    p12_patched_rc: int = 0,
    p12_guard_enabled: bool = True,
    bk4_airplane_shadow: Optional[Mapping[int, int]] = None,
    wf12_bootloop_immune: bool = True,
    wbi_mutation_bytes: int = 0,
    cp_mutation_bytes: int = 0,
    nvram_persistent_writes: int = 0,
    request_persistent_emmc_writes: bool = False,
) -> Master16GateReport:
    """Evaluate all 16 Master Safety Gates (`G01..G16`) deterministically."""
    resolved_root = (DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    eff_manifest = tier0_manifest
    eff_trace = worker_syscall_trace
    eff_hook = init2_failsafe_hook
    eff_cand = candidate_bundle_verified
    eff_allow_dry = allow_dry_run_gate12
    if use_synthetic_dry_run_tier0:
        syn_m, syn_t, syn_h = _build_synthetic_dry_run_tier0_inputs()
        if eff_manifest is None:
            eff_manifest = syn_m
        if eff_trace is None:
            eff_trace = syn_t
        if eff_hook is None:
            eff_hook = syn_h
        if eff_cand is None:
            eff_cand = True
        eff_allow_dry = True

    preflight_12 = evaluate_12_safety_gates(
        resolved_root,
        tier0_manifest=eff_manifest,
        worker_syscall_trace=eff_trace,
        init2_failsafe_hook=eff_hook,
        candidate_bundle_verified=eff_cand,
        allow_dry_run_gate12=eff_allow_dry,
        **dict(gate12_kwargs or {}),
    )

    g13_verdict, _, _ = evaluate_g13_multiport_and_mishoe_isolation(
        ltc_kwargs=ltc_kwargs,
        mishoe_kwargs=mishoe_kwargs,
        crsdk_requests=crsdk_requests,
        crsdk_kwargs=crsdk_kwargs,
        spacc_operations=spacc_operations,
        spacc_script_text=spacc_script_text,
        spacc_sector0_bytes=spacc_sector0_bytes,
        harness_kwargs=harness_kwargs,
    )
    g14_verdict, p44_rep = evaluate_g14_thermal_and_power_envelope(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        fan_kwargs=fan_kwargs,
        power_kwargs=power_kwargs,
        soc_start_ceiling_c=soc_start_ceiling_c,
    )
    g15_verdict, g15_res = evaluate_g15_c2pa_and_calibration(
        planned_mounts=planned_mounts,
        planned_writes=planned_writes,
        c2pa_calibration_script_text=c2pa_calibration_script_text,
        calibration_mutation_bytes=calibration_mutation_bytes,
        c2pa_keystore_writes_attempted=c2pa_keystore_writes_attempted,
        exfat_dirty_bit_present=exfat_dirty_bit_present,
        exfat_unfinalized_rsv_present=exfat_unfinalized_rsv_present,
        allow_c2pa_or_calibration_write=allow_c2pa_or_calibration_write,
    )
    g16_verdict, g16_res = evaluate_g16_stage_b_p12_and_wbi2_lock(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        p12_vma=p12_vma,
        p12_patched_rc=p12_patched_rc,
        p12_guard_enabled=p12_guard_enabled,
        bk4_airplane_shadow=bk4_airplane_shadow,
        wf12_bootloop_immune=wf12_bootloop_immune,
        wbi_mutation_bytes=wbi_mutation_bytes,
        cp_mutation_bytes=cp_mutation_bytes,
        nvram_persistent_writes=nvram_persistent_writes,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
    )

    gates_12 = list(preflight_12["gates"])
    g13_to_g16_verdicts = (g13_verdict, g14_verdict, g15_verdict, g16_verdict)
    gates_13_to_16 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in g13_to_g16_verdicts
    ]
    all_gates = tuple(gates_12 + gates_13_to_16)

    g01_to_g09_ok = all(str(g["status"]).startswith("VERIFIED") for g in gates_12[:9])
    g01_to_g12_verified = sum(1 for g in gates_12 if str(g["status"]).startswith("VERIFIED"))
    g13_to_g16_verified = sum(1 for v in g13_to_g16_verdicts if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g16_verified

    g13_to_g16_all_passed = g13_to_g16_verified == 4
    offline_13_verified = g01_to_g09_ok and g13_to_g16_all_passed
    all_16_verified = (g01_to_g12_verified == 12) and g13_to_g16_all_passed

    errors: List[str] = []
    for v in g13_to_g16_verdicts:
        errors.extend(v.errors)
    warnings: List[str] = []
    for v in g13_to_g16_verdicts:
        warnings.extend(v.warnings)

    if not g13_to_g16_all_passed:
        first_fail = next(v for v in g13_to_g16_verdicts if not v.passed)
        overall_status = first_fail.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_16_verified:
        overall_status = "VERIFIED_ALL_16_GATES_OFFLINE_DRY_RUN"
    else:
        overall_status = "VERIFIED_G01_G09_AND_G13_G16_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif p44_rep.verification_mode == "LOCAL_DONOR_O_RDONLY" or g16_res.verification_mode == "LOCAL_DONOR_O_RDONLY":
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 16,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 16 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g16_verified": g13_to_g16_verified,
        "g13_to_g16_all_passed": g13_to_g16_all_passed,
        "offline_13_gates_verified": offline_13_verified,
        "all_16_gates_verified": all_16_verified,
    }

    return Master16GateReport(
        schema=MASTER_16GATE_PREFLIGHT_SCHEMA,
        version=MASTER_16GATE_PREFLIGHT_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        all_16_gates_verified=all_16_verified,
        offline_13_gates_verified=offline_13_verified,
        g13_to_g16_all_passed=g13_to_g16_all_passed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        g13_result=asdict(g13_verdict),
        g14_result=asdict(g14_verdict),
        g15_result=g15_res.to_dict(),
        g16_result=g16_res.to_dict(),
        preflight_12_report=preflight_12,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="master_16gate_preflight",
        description="Phase 50 — 16-Gate Master Safety Preflight Engine (G01..G16)",
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    parser.add_argument(
        "--dry-run-tier0",
        action="store_true",
        help="Supply synthetic dry-run Tier-0 inputs so G01..G16 can be exercised offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_16_master_safety_gates(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        use_synthetic_dry_run_tier0=bool(args.dry_run_tier0),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/16 "
            f"g13_to_g16_all_passed={report.g13_to_g16_all_passed} "
            f"all_16_gates_verified={report.all_16_gates_verified} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = report.all_16_gates_verified if args.dry_run_tier0 else report.offline_13_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
