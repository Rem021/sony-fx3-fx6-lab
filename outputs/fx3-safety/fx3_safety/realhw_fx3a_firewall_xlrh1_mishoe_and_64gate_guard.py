"""Phase 187 — Real-Hardware Main Track Part 19:
Gate G63 (`ILME-FX3` vs `ILME-FX3A` LCD/NFC/IR Hardware-Branch Firewall &
`BODYDATA.DAT` / `CAMSET` Cross-Branch Isolation),
Gate G64 (`XLR-H1` MI-Shoe `48kHz/24bit 4ch` Digital Audio Routing vs Body `3.5mm`
Jack Physical Override, `S&Q` Mute Consistency, `+48V` Stage-Handoff Glitch &
Fake Standalone USB Payload Guard),
and 64-Gate Master Preflight (`G01..G64` / `verify-64-gates`).

Composes `realhw_emount_info3d_hdmi_braw_and_62gate_guard` (`G01..G62`, keeping
`evaluate_58gate_preflight`, `evaluate_60gate_preflight`, `evaluate_62gate_preflight`,
`verify-58-gates`, `verify-60-gates`, and `verify-62-gates` 100% intact) with
Wave-23 Sony Real-Hardware Intelligence (`G63` and `G64`) while hard-locking all
physical flash/write/transmit redlines:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED = False`
- `PHYSICAL_USB_PACKETS_EMITTED = 0`
- `RAW_FIRMWARE_BYTES_LEAKED = 0`
- `overall_ready_for_hardware_attach = False`
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
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
from .realhw_emount_info3d_hdmi_braw_and_62gate_guard import (
    Master62GateReport,
    evaluate_62gate_preflight,
    parse_semver_tuple,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_FX3A_FIREWALL_XLRH1_MISHOE_64GATE_SCHEMA: str = (
    "fx3-realhw-fx3a-firewall-xlrh1-mishoe-64gate-preflight-v1"
)
REALHW_FX3A_FIREWALL_XLRH1_MISHOE_64GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Gate IDs & Canonical Codes for G63..G64
G63_GATE_ID: str = "G63_fx3_vs_fx3a_lcd_nfc_ir_firmware_branch_firewall"
G63_GATE_CODE: str = (
    "GATE_G63_FX3_VS_FX3A_LCD_NFC_IR_FIRMWARE_BRANCH_FIREWALL"
)
GATE_G63_FX3_VS_FX3A_LCD_NFC_IR_FIRMWARE_BRANCH_FIREWALL: str = G63_GATE_CODE
G63: str = G63_GATE_CODE

G64_GATE_ID: str = "G64_xlrh1_mishoe_4ch_24bit_vs_body_35mm_override_guard"
G64_GATE_CODE: str = (
    "GATE_G64_XLRH1_MISHOE_4CH_24BIT_VS_BODY_35MM_OVERRIDE_GUARD"
)
GATE_G64_XLRH1_MISHOE_4CH_24BIT_VS_BODY_35MM_OVERRIDE_GUARD: str = G64_GATE_CODE
G64: str = G64_GATE_CODE

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G63: str = (
    "VERIFIED_FX3_VS_FX3A_LCD_NFC_IR_FIRMWARE_BRANCH_FIREWALL"
)
STATUS_VERIFIED_G64: str = (
    "VERIFIED_XLRH1_MISHOE_4CH_24BIT_VS_BODY_35MM_OVERRIDE_GUARD"
)

# Gate G63 Violation Codes
STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE: str = (
    "BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE"
)
STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH: str = (
    "BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH"
)
STATUS_BLOCKED_G63_BODYDATA_FX3A_OR_VER_1X_2X: str = (
    "BLOCKED_G63_BODYDATA_FX3A_OR_VER_1X_2X"
)
STATUS_BLOCKED_G63_CAMSET_CROSS_BRANCH_IMPORT: str = (
    "BLOCKED_G63_CAMSET_CROSS_BRANCH_IMPORT"
)
STATUS_BLOCKED_G63_TELEMETRY_INVALID: str = (
    "BLOCKED_G63_FX3_VS_FX3A_TELEMETRY_INVALID"
)

# Gate G64 Violation Codes
STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID: str = (
    "BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID"
)
STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE: str = (
    "BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE"
)
STATUS_BLOCKED_G64_SQ_AUDIO_MUTE_INCONSISTENCY: str = (
    "BLOCKED_G64_SQ_AUDIO_MUTE_INCONSISTENCY"
)
STATUS_BLOCKED_G64_PHANTOM_48V_STAGE_HANDOFF_GLITCH: str = (
    "BLOCKED_G64_PHANTOM_48V_STAGE_HANDOFF_GLITCH"
)
STATUS_BLOCKED_G64_FAKE_XLRH1_USB_FIRMWARE_PAYLOAD: str = (
    "BLOCKED_G64_FAKE_XLRH1_USB_FIRMWARE_PAYLOAD"
)
STATUS_BLOCKED_G64_TELEMETRY_INVALID: str = (
    "BLOCKED_G64_XLRH1_MISHOE_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE187_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE187_64GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G63 Constants — ILME-FX3 vs ILME-FX3A & ILME-FX30 Branch Firewall
FX3_MODEL_NAME: str = "ILME-FX3"
FX3_MODEL_ID: int = 0x91030080
FX3_MODEL_ID_HEX: str = "0x91030080"
FX3_TARGET_FIRMWARE_VERSION: str = "7.02"
FX3_MIN_BRANCH_MAJOR: int = 7
FX3_ORIGINAL_HW_REVISION: str = "ORIGINAL_2021_FX3"
FX3_LCD_DOT_COUNT: int = 1_440_000
FX3_LCD_PANEL_SPEC: str = "3.0_1440K_DOT"

FX3A_MODEL_NAME: str = "ILME-FX3A"
FX3A_HW_REVISION_2025: str = "REVISION_2025_FX3A"
FX3A_FIRMWARE_VERSION_202: str = "2.02"
FX3A_XGA_LCD_DOT_COUNT: int = 2_359_296
FX3A_XGA_LCD_PANEL_SPEC: str = "3.0_2359K_DOT_XGA"

FX30_MODEL_NAME: str = "ILME-FX30"
FX30_MODEL_ID: int = 0x91030084
FX30_MODEL_ID_HEX: str = "0x91030084"

REJECTED_CROSS_BRANCH_MODELS: Tuple[str, ...] = (
    "ILME-FX3A",
    "FX3A",
    "ILME-FX30",
    "FX30",
    "ILME-FX6",
    "FX6",
)
REJECTED_CROSS_BRANCH_MODEL_IDS: Tuple[int, ...] = (FX30_MODEL_ID,)
FX3_FAIL_CLOSED_MAX_LATENCY_US: float = 50.0
FX3_BRANCH_NAME: str = "FX3"
FX3A_BRANCH_NAME: str = "FX3A"
FX30_BRANCH_NAME: str = "FX30"

# Gate G64 Constants — XLR-H1 MI-Shoe Digital Audio vs Body 3.5mm Override Guard
XLRH1_HANDLE_MODEL: str = "XLR-H1"
XLRH1_AUDIO_SAMPLE_RATE_HZ: int = 48_000
XLRH1_VALID_AUDIO_PROFILES: Mapping[str, Tuple[int, int, int]] = {
    "48KHZ_24BIT_4CH": (48_000, 24, 4),
    "48KHZ_24BIT_2CH": (48_000, 24, 2),
    "48KHZ_16BIT_2CH": (48_000, 16, 2),
}
XLRH1_DEFAULT_FORMAT_MODE: str = "48KHZ_24BIT_4CH"
XLRH1_POST_BODYDATA_RESET_DEFAULT: str = "48KHZ_16BIT_2CH"
XLRH1_HEADPHONE_MONITOR_MATRICES: Tuple[str, ...] = (
    "CH1_2",
    "CH3_4",
    "CH1+3_CH2+4",
)
XLRH1_EXPECTED_IN1_IN2_ROUTE: str = "CH1_CH2"
XLRH1_EXPECTED_IN3_ROUTE: str = "CH3_CH4"
XLRH1_VALID_STAGE_TRANSITIONS: Tuple[str, ...] = (
    "STEADY_STAGE_A",
    "STAGE_A_TO_STAGE_B",
    "STEADY_STAGE_B",
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_FORBIDDEN_TRIVIAL_HEX64: Tuple[str, ...] = ("0" * 64, "f" * 64)

# Pinned FX3 v7.02 & Hotshoe Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE187_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"ILME-FX3A",
            b"ILME-FX30",
            b"MI_SHOE",
            b"HOTSHOE",
            b"48kHz",
            b"24bit",
            b"4ch",
            b"XLR",
            b"HANDLE",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,ILME-FX3A,ILME-FX30,MI_SHOE,HOTSHOE,48kHz,24bit,4ch,XLR,HANDLE}",
    ),
    "fx3_appfw_so": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so",
        79_015_712,
        "545c5053a74e04ffbf2bbaaf80f558092dd545ed2298b2395ca547dbba58290f",
        (
            b"\x7fELF",
            b"CAMSET",
            b"NFC",
            b"HOTSHOE",
            b"24bit",
            b"4ch",
            b"XLR",
            b"HANDLE",
            b"S&Q",
        ),
        "fx3/appFw.so::{79015712B,ELF,CAMSET,NFC,HOTSHOE,24bit,4ch,XLR,HANDLE,S&Q}",
    ),
    "fx6_hotshoe_so": (
        "hotshoe",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so",
        47_808,
        "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6",
        (
            b"\x7fELF",
            b"HOTSHOE",
            b"Hotshoe",
            b"HANDLE",
        ),
        "fx6/libInfraHotshoe.so::{47808B,ELF,HOTSHOE,Hotshoe,HANDLE}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase187DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    hotshoe_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Fx3VsFx3aBranchFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    body_model_name: str
    body_model_id: int
    body_model_id_hex: str
    donor_model_name: str
    donor_model_id_hex: str
    body_firmware_version: str
    body_branch: str
    hardware_revision: str
    lcd_dot_count: int
    lcd_panel_spec: str
    nfc_hardware_present: bool
    ir_receiver_present: bool
    display_shim_target: str
    fail_closed_latency_us: float
    stock_fallback_armed: bool
    body_signature_valid: bool
    lcd_nfc_ir_parity_valid: bool
    bodydata_present: bool
    bodydata_target_model: str
    bodydata_target_model_id_hex: str
    bodydata_version: str
    bodydata_branch: str
    bodydata_branch_valid: bool
    camset_import_requested: bool
    camset_source_model: str
    camset_target_model: str
    camset_source_branch: str
    camset_target_branch: str
    camset_cross_branch_blocked: bool
    camset_isolation_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class XlrH1MiShoeAudioGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    handle_model: str
    xlrh1_attached: bool
    handle_audio_enabled: bool
    audio_format_mode: str
    sample_rate_hz: int
    bit_depth: int
    channel_count: int
    in1_in2_xlr_route: str
    in3_35mm_route: str
    headphone_monitor_matrix: str
    post_bodydata_reset_unreconciled: bool
    routing_and_format_valid: bool
    body_35mm_mic_plugged: bool
    mi_shoe_audio_set_locked_out: bool
    body_35mm_override_detected: bool
    sq_mode_active: bool
    mi_shoe_audio_muted: bool
    body_35mm_and_sq_valid: bool
    stage_transition: str
    phantom_48v_enabled: bool
    phantom_48v_rail_stable: bool
    phantom_48v_glitch_events: int
    phantom_48v_slew_controlled: bool
    adc_soft_mute_during_handoff: bool
    hotshoe_gpio_glitch_detected: bool
    phantom_handoff_valid: bool
    xlrh1_usb_fw_update_attempted: bool
    xlrh1_standalone_usb_payload_present: bool
    xlrh1_usb_payload_filename: str
    xlrh1_standalone_usb_fw_rejected: bool
    usb_fw_payload_guard_valid: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G63Fx3aBranchFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    fx3a_branch_firewall: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G64XlrH1MiShoeGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    xlrh1_mishoe_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master64GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_61_gates_verified: bool
    all_64_gates_verified: bool
    g13_to_g64_all_passed: bool
    g63_to_g64_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_62_report: Dict[str, Any]
    g63_result: Dict[str, Any]
    g64_result: Dict[str, Any]
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
            chunk = os.read(fd, 1_048_576)
            if not chunk:
                break
            chunks.append(chunk)
        return b"".join(chunks)
    finally:
        os.close(fd)


def _is_non_negative_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val >= 0


def _is_finite_number(val: Any) -> bool:
    if isinstance(val, bool):
        return False
    if not isinstance(val, (int, float)):
        return False
    return abs(float(val)) < 1e12 and (float(val) == float(val))


def _normalize_int_value(val: Any) -> Optional[int]:
    if isinstance(val, bool):
        return None
    if isinstance(val, int):
        return val
    if isinstance(val, str):
        s = val.strip().lower()
        if not s:
            return None
        try:
            return int(s, 16) if s.startswith("0x") else int(s, 10)
        except ValueError:
            return None
    return None


def _norm_model(name: str) -> str:
    return name.strip().upper().replace("_", "-")


def _norm_branch(name: str) -> str:
    return name.strip().upper().replace("-", "").replace("_", "")


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase187_donor_contracts(
    *_,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase187DonorAuditResult:
    """Inspect FX3 `7.02` `cpapp-b.bin`, `appFw.so`, and `libInfraHotshoe.so`
    strictly via `os.open(..., os.O_RDONLY)` with deterministic clean-room
    fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.
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
        ) in PINNED_PHASE187_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase187DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE187_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            hotshoe_contracts_verified=True,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE187_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE187_DONOR_SPECS.items()
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
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE187_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
        files_inspected += 1
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
        k for k, spec in PINNED_PHASE187_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    hotshoe_keys = {
        k for k, spec in PINNED_PHASE187_DONOR_SPECS.items() if spec[0] == "hotshoe"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase187DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE187_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        hotshoe_contracts_verified=hotshoe_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Validators (G63 & G64)
# ---------------------------------------------------------------------------


def validate_fx3_vs_fx3a_body_hardware_signature(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int | str = FX3_MODEL_ID,
    donor_model_name: str = FX3_MODEL_NAME,
    donor_model_id: int | str = FX3_MODEL_ID,
    body_firmware_version: str = FX3_TARGET_FIRMWARE_VERSION,
    body_branch: str = FX3_BRANCH_NAME,
) -> Tuple[bool, str, List[str]]:
    """Hard-block accidental cross-model deployment between original `ILME-FX3`
    (`0x91030080`, `Ver. 7.02`) and `ILME-FX3A` (`2025` revision, `Ver. 1.xx/2.xx`)
    or `ILME-FX30` (`0x91030084`).
    """
    errors: List[str] = []
    b_model = _norm_model(body_model_name)
    d_model = _norm_model(donor_model_name)
    b_id = _normalize_int_value(body_model_id)
    d_id = _normalize_int_value(donor_model_id)
    b_branch = _norm_branch(body_branch)
    ver_tuple = parse_semver_tuple(body_firmware_version)

    rejected_model = (
        b_model in REJECTED_CROSS_BRANCH_MODELS
        or d_model in REJECTED_CROSS_BRANCH_MODELS
        or b_model != FX3_MODEL_NAME
        or d_model != FX3_MODEL_NAME
    )
    rejected_id = (
        b_id is None
        or d_id is None
        or b_id in REJECTED_CROSS_BRANCH_MODEL_IDS
        or d_id in REJECTED_CROSS_BRANCH_MODEL_IDS
        or b_id != FX3_MODEL_ID
        or d_id != FX3_MODEL_ID
    )
    # Reject FX3A Ver. 1.xx/2.xx (e.g., Ver. 2.02) or any non-FX3 branch
    ver_ok = ver_tuple is not None and ver_tuple[0] >= FX3_MIN_BRANCH_MAJOR
    branch_ok = b_branch == FX3_BRANCH_NAME

    ok = (not rejected_model) and (not rejected_id) and ver_ok and branch_ok
    if not ok:
        errors.append(
            f"FX3 vs FX3A/FX30 body/donor firewall triggered: "
            f"body={body_model_name!r}({body_model_id!r}), "
            f"donor={donor_model_name!r}({donor_model_id!r}), "
            f"fw={body_firmware_version!r} (requires FX3 >= {FX3_MIN_BRANCH_MAJOR}.00), "
            f"branch={body_branch!r}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G63_FX3A_OR_FX30_BODY_SIGNATURE),
        errors,
    )


def validate_fx3_lcd_nfc_ir_hardware_parity(
    *,
    hardware_revision: str = FX3_ORIGINAL_HW_REVISION,
    lcd_dot_count: int = FX3_LCD_DOT_COUNT,
    lcd_panel_spec: str = FX3_LCD_PANEL_SPEC,
    nfc_hardware_present: bool = True,
    ir_receiver_present: bool = True,
    display_shim_target: str = "FX3_1440K_LCD",
    fail_closed_latency_us: float = 18.0,
    stock_fallback_armed: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Enforce original `ILME-FX3` physical hardware parity (`1,440,000-dot` LCD,
    NFC present, IR receiver present) and `< 50 us` fail-closed stock fallback,
    rejecting `ILME-FX3A` (`2025` revision, `2,359,296-dot` XGA LCD, NFC & IR omitted).
    """
    errors: List[str] = []
    rev_norm = hardware_revision.strip().upper()
    panel_norm = lcd_panel_spec.strip().upper()
    shim_norm = display_shim_target.strip().upper()
    ok = (
        rev_norm == FX3_ORIGINAL_HW_REVISION
        and int(lcd_dot_count) == FX3_LCD_DOT_COUNT
        and int(lcd_dot_count) != FX3A_XGA_LCD_DOT_COUNT
        and panel_norm == FX3_LCD_PANEL_SPEC
        and ("XGA" not in panel_norm)
        and ("2359" not in panel_norm)
        and nfc_hardware_present is True
        and ir_receiver_present is True
        and shim_norm == "FX3_1440K_LCD"
        and 0.0 <= float(fail_closed_latency_us) < FX3_FAIL_CLOSED_MAX_LATENCY_US
        and stock_fallback_armed is True
    )
    if not ok:
        errors.append(
            f"FX3 LCD/NFC/IR hardware parity failed (possible ILME-FX3A 2025 revision): "
            f"rev={hardware_revision!r}, lcd_dots={lcd_dot_count}, "
            f"panel={lcd_panel_spec!r}, nfc={nfc_hardware_present}, "
            f"ir={ir_receiver_present}, shim={display_shim_target!r}, "
            f"latency_us={fail_closed_latency_us}, fallback={stock_fallback_armed}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G63_LCD_NFC_IR_HARDWARE_MISMATCH),
        errors,
    )


def validate_bodydata_fx3_vs_fx3a_branch(
    *,
    bodydata_present: bool = False,
    bodydata_target_model: str = FX3_MODEL_NAME,
    bodydata_target_model_id: int | str = FX3_MODEL_ID,
    bodydata_version: str = FX3_TARGET_FIRMWARE_VERSION,
    bodydata_branch: str = FX3_BRANCH_NAME,
) -> Tuple[bool, str, List[str]]:
    """Reject `FX3A` `Ver. 1.xx/2.xx` `BODYDATA.DAT` packages, `FX30` (`0x91030084`),
    and any cross-branch `BODYDATA.DAT` update targeting `ILME-FX3`.
    """
    errors: List[str] = []
    t_model = _norm_model(bodydata_target_model)
    t_id = _normalize_int_value(bodydata_target_model_id)
    t_branch = _norm_branch(bodydata_branch)
    ver_tuple = parse_semver_tuple(bodydata_version)

    # Even if bodydata_present=False, validate the pinned package descriptor fails closed
    # whenever cross-branch/FX3A/1.xx/2.xx/FX30 fields are supplied.
    ver_ok = (
        ver_tuple is not None
        and ver_tuple[0] >= FX3_MIN_BRANCH_MAJOR
        and ver_tuple[0] not in (1, 2)
    )
    ok = (
        t_model == FX3_MODEL_NAME
        and t_model not in REJECTED_CROSS_BRANCH_MODELS
        and t_id == FX3_MODEL_ID
        and t_id not in REJECTED_CROSS_BRANCH_MODEL_IDS
        and t_branch == FX3_BRANCH_NAME
        and ver_ok
    )
    if not ok:
        errors.append(
            f"BODYDATA.DAT branch firewall rejected package: "
            f"present={bodydata_present}, target_model={bodydata_target_model!r} "
            f"({bodydata_target_model_id!r}), version={bodydata_version!r} "
            f"(Ver. 1.xx/2.xx FX3A blocked), branch={bodydata_branch!r}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G63_BODYDATA_FX3A_OR_VER_1X_2X),
        errors,
    )


def validate_camset_branch_isolation(
    *,
    camset_import_requested: bool = False,
    camset_source_model: str = FX3_MODEL_NAME,
    camset_target_model: str = FX3_MODEL_NAME,
    camset_source_branch: str = FX3_BRANCH_NAME,
    camset_target_branch: str = FX3_BRANCH_NAME,
    camset_cross_branch_blocked: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Block cross-branch `CAMSET` camera settings imports (`FX3 <-> FX3A`,
    `FX3 <-> FX30`, `FX3 <-> FX6`).
    """
    errors: List[str] = []
    src_m = _norm_model(camset_source_model)
    dst_m = _norm_model(camset_target_model)
    src_b = _norm_branch(camset_source_branch)
    dst_b = _norm_branch(camset_target_branch)

    same_fx3_branch = (
        src_m == FX3_MODEL_NAME
        and dst_m == FX3_MODEL_NAME
        and src_b == FX3_BRANCH_NAME
        and dst_b == FX3_BRANCH_NAME
    )
    ok = same_fx3_branch and (camset_cross_branch_blocked is True)
    if not ok:
        errors.append(
            f"Cross-branch CAMSET settings import blocked: "
            f"requested={camset_import_requested}, "
            f"src={camset_source_model!r}/{camset_source_branch!r} -> "
            f"dst={camset_target_model!r}/{camset_target_branch!r}, "
            f"cross_branch_blocked={camset_cross_branch_blocked}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G63_CAMSET_CROSS_BRANCH_IMPORT),
        errors,
    )


def validate_xlrh1_mishoe_digital_audio_routing(
    *,
    handle_model: str = XLRH1_HANDLE_MODEL,
    xlrh1_attached: bool = True,
    handle_audio_enabled: bool = True,
    audio_format_mode: str = XLRH1_DEFAULT_FORMAT_MODE,
    sample_rate_hz: int = XLRH1_AUDIO_SAMPLE_RATE_HZ,
    bit_depth: int = 24,
    channel_count: int = 4,
    in1_in2_xlr_route: str = XLRH1_EXPECTED_IN1_IN2_ROUTE,
    in3_35mm_route: str = XLRH1_EXPECTED_IN3_ROUTE,
    headphone_monitor_matrix: str = "CH1+3_CH2+4",
    post_bodydata_reset_unreconciled: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Verify `XLR-H1` MI-Shoe digital audio safety & routing (`48kHz/24bit 4ch`,
    `48kHz/24bit 2ch`, `48kHz/16bit 2ch`; `HANDLE AUDIO = ON`; `IN1/IN2` XLR ->
    `CH1/CH2`, `IN3` 3.5mm -> `CH3/CH4`; headphone monitoring matrix `CH1/2`,
    `CH3/4`, `CH1+3/CH2+4`).
    """
    errors: List[str] = []
    mode_norm = audio_format_mode.strip().upper().replace("/", "_").replace(" ", "_")
    in12_norm = in1_in2_xlr_route.strip().upper()
    in3_norm = in3_35mm_route.strip().upper()
    hp_norm = headphone_monitor_matrix.strip().upper()

    expected_tuple = XLRH1_VALID_AUDIO_PROFILES.get(mode_norm)
    tuple_matches = expected_tuple is not None and (
        (int(sample_rate_hz), int(bit_depth), int(channel_count)) == expected_tuple
    )
    in3_ok = (in3_norm == XLRH1_EXPECTED_IN3_ROUTE) if int(channel_count) == 4 else (
        in3_norm in (XLRH1_EXPECTED_IN3_ROUTE, "DISABLED_2CH")
    )
    hp_ok = hp_norm in XLRH1_HEADPHONE_MONITOR_MATRICES and (
        True if int(channel_count) == 4 else hp_norm == "CH1_2"
    )
    handle_ok = (not xlrh1_attached) or handle_audio_enabled

    ok = (
        handle_model.strip().upper() == XLRH1_HANDLE_MODEL
        and handle_ok
        and tuple_matches
        and in12_norm == XLRH1_EXPECTED_IN1_IN2_ROUTE
        and in3_ok
        and hp_ok
        and (not post_bodydata_reset_unreconciled)
    )
    if not ok:
        errors.append(
            f"XLR-H1 MI-Shoe digital audio routing/format check failed: "
            f"attached={xlrh1_attached}, handle_audio={handle_audio_enabled}, "
            f"mode={audio_format_mode!r} ({sample_rate_hz}Hz/{bit_depth}bit/{channel_count}ch), "
            f"in1_in2={in1_in2_xlr_route!r}, in3={in3_35mm_route!r}, "
            f"hp_matrix={headphone_monitor_matrix!r}, "
            f"post_bodydata_reset_unreconciled={post_bodydata_reset_unreconciled}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G64_XLRH1_ROUTING_OR_FORMAT_INVALID),
        errors,
    )


def validate_body_35mm_jack_override_and_sq_mute(
    *,
    xlrh1_attached: bool = True,
    body_35mm_mic_plugged: bool = False,
    mi_shoe_audio_set_locked_out: bool = False,
    sq_mode_active: bool = False,
    mi_shoe_audio_muted: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Detect body `3.5mm` mic-jack physical override locking out `[MI Shoe Audio Set.]`
    and enforce `S&Q` audio mute consistency.
    """
    errors: List[str] = []

    # Physical 3.5mm body mic plug overrides and greys out [MI Shoe Audio Set.]
    if (body_35mm_mic_plugged and xlrh1_attached) or mi_shoe_audio_set_locked_out:
        errors.append(
            f"Body 3.5mm mic-jack physical override detected: "
            f"body_35mm_mic_plugged={body_35mm_mic_plugged}, "
            f"mi_shoe_audio_set_locked_out={mi_shoe_audio_set_locked_out}, "
            f"xlrh1_attached={xlrh1_attached}."
        )
        return (False, STATUS_BLOCKED_G64_BODY_35MM_OVERRIDE_LOCKS_MISHOE, errors)

    # S&Q mode forces MI-shoe audio mute; non-S&Q must not remain unexpectedly muted
    sq_consistent = (mi_shoe_audio_muted is True) if sq_mode_active else (
        mi_shoe_audio_muted is False
    )
    if not sq_consistent:
        errors.append(
            f"S&Q audio mute consistency check failed: "
            f"sq_mode_active={sq_mode_active}, mi_shoe_audio_muted={mi_shoe_audio_muted}."
        )
        return (False, STATUS_BLOCKED_G64_SQ_AUDIO_MUTE_INCONSISTENCY, errors)

    return (True, "", errors)


def validate_xlrh1_phantom_48v_stage_handoff(
    *,
    stage_transition: str = "STAGE_A_TO_STAGE_B",
    phantom_48v_enabled: bool = True,
    phantom_48v_rail_stable: bool = True,
    phantom_48v_glitch_events: int = 0,
    phantom_48v_slew_controlled: bool = True,
    adc_soft_mute_during_handoff: bool = True,
    hotshoe_gpio_glitch_detected: bool = False,
) -> Tuple[bool, str, List[str]]:
    """Block `+48V` phantom-power glitch transitions during Stage-A -> Stage-B handoff."""
    errors: List[str] = []
    tr_norm = stage_transition.strip().upper()
    handoff_clean = (
        phantom_48v_rail_stable is True
        and int(phantom_48v_glitch_events) == 0
        and phantom_48v_slew_controlled is True
        and adc_soft_mute_during_handoff is True
        and hotshoe_gpio_glitch_detected is False
    )
    ok = (tr_norm in XLRH1_VALID_STAGE_TRANSITIONS) and handoff_clean
    if not ok:
        errors.append(
            f"XLR-H1 +48V Stage-A -> Stage-B handoff glitch check failed: "
            f"transition={stage_transition!r}, phantom_enabled={phantom_48v_enabled}, "
            f"rail_stable={phantom_48v_rail_stable}, glitch_events={phantom_48v_glitch_events}, "
            f"slew_controlled={phantom_48v_slew_controlled}, "
            f"adc_soft_mute={adc_soft_mute_during_handoff}, "
            f"gpio_glitch={hotshoe_gpio_glitch_detected}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G64_PHANTOM_48V_STAGE_HANDOFF_GLITCH),
        errors,
    )


def validate_xlrh1_no_fake_usb_firmware_payload(
    *,
    xlrh1_usb_fw_update_attempted: bool = False,
    xlrh1_standalone_usb_payload_present: bool = False,
    xlrh1_usb_payload_filename: str = "",
    xlrh1_standalone_usb_fw_rejected: bool = True,
) -> Tuple[bool, str, List[str]]:
    """Reject fake standalone `XLR-H1` USB firmware payloads (Sony `XLR-H1` has no
    standalone USB firmware update package).
    """
    errors: List[str] = []
    has_filename = bool(xlrh1_usb_payload_filename.strip())
    ok = (
        (not xlrh1_usb_fw_update_attempted)
        and (not xlrh1_standalone_usb_payload_present)
        and (not has_filename)
        and (xlrh1_standalone_usb_fw_rejected is True)
    )
    if not ok:
        errors.append(
            f"Fake standalone XLR-H1 USB firmware payload rejected: "
            f"update_attempted={xlrh1_usb_fw_update_attempted}, "
            f"payload_present={xlrh1_standalone_usb_payload_present}, "
            f"filename={xlrh1_usb_payload_filename!r}, "
            f"rejected_flag={xlrh1_standalone_usb_fw_rejected}."
        )
    return (
        ok,
        ("" if ok else STATUS_BLOCKED_G64_FAKE_XLRH1_USB_FIRMWARE_PAYLOAD),
        errors,
    )


# ---------------------------------------------------------------------------
# 3. Core Guard Functions (`verify_fx3_vs_fx3a_branch_firewall`,
#    `verify_xlrh1_mishoe_4ch_vs_35mm_override_guard`)
# ---------------------------------------------------------------------------


def verify_fx3_vs_fx3a_branch_firewall(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: int | str = FX3_MODEL_ID,
    donor_model_name: str = FX3_MODEL_NAME,
    donor_model_id: int | str = FX3_MODEL_ID,
    body_firmware_version: str = FX3_TARGET_FIRMWARE_VERSION,
    body_branch: str = FX3_BRANCH_NAME,
    hardware_revision: str = FX3_ORIGINAL_HW_REVISION,
    lcd_dot_count: int = FX3_LCD_DOT_COUNT,
    lcd_panel_spec: str = FX3_LCD_PANEL_SPEC,
    nfc_hardware_present: bool = True,
    ir_receiver_present: bool = True,
    display_shim_target: str = "FX3_1440K_LCD",
    fail_closed_latency_us: float = 18.0,
    stock_fallback_armed: bool = True,
    bodydata_present: bool = False,
    bodydata_target_model: str = FX3_MODEL_NAME,
    bodydata_target_model_id: int | str = FX3_MODEL_ID,
    bodydata_version: str = FX3_TARGET_FIRMWARE_VERSION,
    bodydata_branch: str = FX3_BRANCH_NAME,
    camset_import_requested: bool = False,
    camset_source_model: str = FX3_MODEL_NAME,
    camset_target_model: str = FX3_MODEL_NAME,
    camset_source_branch: str = FX3_BRANCH_NAME,
    camset_target_branch: str = FX3_BRANCH_NAME,
    camset_cross_branch_blocked: bool = True,
    guard_profile: str = "FX3_REALHW_G63_FX3_VS_FX3A_BRANCH_FIREWALL_DEFAULT",
) -> Fx3VsFx3aBranchFirewallResult:
    """Verify Gate G63 (`ILME-FX3` vs `ILME-FX3A` Hardware-Branch Firewall) fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        body_model_name,
        donor_model_name,
        body_firmware_version,
        body_branch,
        hardware_revision,
        lcd_panel_spec,
        display_shim_target,
        bodydata_target_model,
        bodydata_version,
        bodydata_branch,
        camset_source_model,
        camset_target_model,
        camset_source_branch,
        camset_target_branch,
        guard_profile,
    )
    bools = (
        nfc_hardware_present,
        ir_receiver_present,
        stock_fallback_armed,
        bodydata_present,
        camset_import_requested,
        camset_cross_branch_blocked,
    )
    b_id = _normalize_int_value(body_model_id)
    d_id = _normalize_int_value(donor_model_id)
    bd_id = _normalize_int_value(bodydata_target_model_id)

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and all(isinstance(b, bool) for b in bools)
        and (b_id is not None and b_id >= 0)
        and (d_id is not None and d_id >= 0)
        and (bd_id is not None and bd_id >= 0)
        and _is_non_negative_int(lcd_dot_count)
        and _is_finite_number(fail_closed_latency_us)
        and float(fail_closed_latency_us) >= 0.0
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G63_TELEMETRY_INVALID)
        errors.append("Gate G63 received invalid or malformed FX3/FX3A firewall telemetry.")

    sig_ok = False
    hw_ok = False
    bd_ok = False
    camset_ok = False

    if telemetry_ok:
        sig_ok, sig_code, sig_errs = validate_fx3_vs_fx3a_body_hardware_signature(
            body_model_name=body_model_name,
            body_model_id=b_id,
            donor_model_name=donor_model_name,
            donor_model_id=d_id,
            body_firmware_version=body_firmware_version,
            body_branch=body_branch,
        )
        if not sig_ok:
            _add_code(codes, sig_code)
            errors.extend(sig_errs)

        hw_ok, hw_code, hw_errs = validate_fx3_lcd_nfc_ir_hardware_parity(
            hardware_revision=hardware_revision,
            lcd_dot_count=lcd_dot_count,
            lcd_panel_spec=lcd_panel_spec,
            nfc_hardware_present=nfc_hardware_present,
            ir_receiver_present=ir_receiver_present,
            display_shim_target=display_shim_target,
            fail_closed_latency_us=float(fail_closed_latency_us),
            stock_fallback_armed=stock_fallback_armed,
        )
        if not hw_ok:
            _add_code(codes, hw_code)
            errors.extend(hw_errs)

        bd_ok, bd_code, bd_errs = validate_bodydata_fx3_vs_fx3a_branch(
            bodydata_present=bodydata_present,
            bodydata_target_model=bodydata_target_model,
            bodydata_target_model_id=bd_id,
            bodydata_version=bodydata_version,
            bodydata_branch=bodydata_branch,
        )
        if not bd_ok:
            _add_code(codes, bd_code)
            errors.extend(bd_errs)

        camset_ok, cs_code, cs_errs = validate_camset_branch_isolation(
            camset_import_requested=camset_import_requested,
            camset_source_model=camset_source_model,
            camset_target_model=camset_target_model,
            camset_source_branch=camset_source_branch,
            camset_target_branch=camset_target_branch,
            camset_cross_branch_blocked=camset_cross_branch_blocked,
        )
        if not camset_ok:
            _add_code(codes, cs_code)
            errors.extend(cs_errs)

    valid = (
        telemetry_ok
        and sig_ok
        and hw_ok
        and bd_ok
        and camset_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G63 if valid else codes[0]

    return Fx3VsFx3aBranchFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        body_model_name=str(body_model_name) if isinstance(body_model_name, str) else "INVALID",
        body_model_id=int(b_id) if b_id is not None else -1,
        body_model_id_hex=f"0x{b_id:08x}" if b_id is not None else "INVALID",
        donor_model_name=str(donor_model_name) if isinstance(donor_model_name, str) else "INVALID",
        donor_model_id_hex=f"0x{d_id:08x}" if d_id is not None else "INVALID",
        body_firmware_version=str(body_firmware_version) if isinstance(body_firmware_version, str) else "INVALID",
        body_branch=str(body_branch) if isinstance(body_branch, str) else "INVALID",
        hardware_revision=str(hardware_revision) if isinstance(hardware_revision, str) else "INVALID",
        lcd_dot_count=int(lcd_dot_count) if _is_non_negative_int(lcd_dot_count) else -1,
        lcd_panel_spec=str(lcd_panel_spec) if isinstance(lcd_panel_spec, str) else "INVALID",
        nfc_hardware_present=bool(nfc_hardware_present) if isinstance(nfc_hardware_present, bool) else False,
        ir_receiver_present=bool(ir_receiver_present) if isinstance(ir_receiver_present, bool) else False,
        display_shim_target=str(display_shim_target) if isinstance(display_shim_target, str) else "INVALID",
        fail_closed_latency_us=float(fail_closed_latency_us) if _is_finite_number(fail_closed_latency_us) else -1.0,
        stock_fallback_armed=bool(stock_fallback_armed) if isinstance(stock_fallback_armed, bool) else False,
        body_signature_valid=sig_ok,
        lcd_nfc_ir_parity_valid=hw_ok,
        bodydata_present=bool(bodydata_present) if isinstance(bodydata_present, bool) else False,
        bodydata_target_model=str(bodydata_target_model) if isinstance(bodydata_target_model, str) else "INVALID",
        bodydata_target_model_id_hex=f"0x{bd_id:08x}" if bd_id is not None else "INVALID",
        bodydata_version=str(bodydata_version) if isinstance(bodydata_version, str) else "INVALID",
        bodydata_branch=str(bodydata_branch) if isinstance(bodydata_branch, str) else "INVALID",
        bodydata_branch_valid=bd_ok,
        camset_import_requested=bool(camset_import_requested) if isinstance(camset_import_requested, bool) else False,
        camset_source_model=str(camset_source_model) if isinstance(camset_source_model, str) else "INVALID",
        camset_target_model=str(camset_target_model) if isinstance(camset_target_model, str) else "INVALID",
        camset_source_branch=str(camset_source_branch) if isinstance(camset_source_branch, str) else "INVALID",
        camset_target_branch=str(camset_target_branch) if isinstance(camset_target_branch, str) else "INVALID",
        camset_cross_branch_blocked=bool(camset_cross_branch_blocked) if isinstance(camset_cross_branch_blocked, bool) else False,
        camset_isolation_valid=camset_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(
    *,
    handle_model: str = XLRH1_HANDLE_MODEL,
    xlrh1_attached: bool = True,
    handle_audio_enabled: bool = True,
    audio_format_mode: str = XLRH1_DEFAULT_FORMAT_MODE,
    sample_rate_hz: int = XLRH1_AUDIO_SAMPLE_RATE_HZ,
    bit_depth: int = 24,
    channel_count: int = 4,
    in1_in2_xlr_route: str = XLRH1_EXPECTED_IN1_IN2_ROUTE,
    in3_35mm_route: str = XLRH1_EXPECTED_IN3_ROUTE,
    headphone_monitor_matrix: str = "CH1+3_CH2+4",
    post_bodydata_reset_unreconciled: bool = False,
    body_35mm_mic_plugged: bool = False,
    mi_shoe_audio_set_locked_out: bool = False,
    sq_mode_active: bool = False,
    mi_shoe_audio_muted: bool = False,
    stage_transition: str = "STAGE_A_TO_STAGE_B",
    phantom_48v_enabled: bool = True,
    phantom_48v_rail_stable: bool = True,
    phantom_48v_glitch_events: int = 0,
    phantom_48v_slew_controlled: bool = True,
    adc_soft_mute_during_handoff: bool = True,
    hotshoe_gpio_glitch_detected: bool = False,
    xlrh1_usb_fw_update_attempted: bool = False,
    xlrh1_standalone_usb_payload_present: bool = False,
    xlrh1_usb_payload_filename: str = "",
    xlrh1_standalone_usb_fw_rejected: bool = True,
    guard_profile: str = "FX3_REALHW_G64_XLRH1_MISHOE_4CH_GUARD_DEFAULT",
) -> XlrH1MiShoeAudioGuardResult:
    """Verify Gate G64 (`XLR-H1` MI-Shoe `48kHz/24bit 4ch` Override Guard) fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    req_strs = (
        handle_model,
        audio_format_mode,
        in1_in2_xlr_route,
        in3_35mm_route,
        headphone_monitor_matrix,
        stage_transition,
        guard_profile,
    )
    bools = (
        xlrh1_attached,
        handle_audio_enabled,
        post_bodydata_reset_unreconciled,
        body_35mm_mic_plugged,
        mi_shoe_audio_set_locked_out,
        sq_mode_active,
        mi_shoe_audio_muted,
        phantom_48v_enabled,
        phantom_48v_rail_stable,
        phantom_48v_slew_controlled,
        adc_soft_mute_during_handoff,
        hotshoe_gpio_glitch_detected,
        xlrh1_usb_fw_update_attempted,
        xlrh1_standalone_usb_payload_present,
        xlrh1_standalone_usb_fw_rejected,
    )

    telemetry_ok = (
        all(isinstance(s, str) and bool(s.strip()) for s in req_strs)
        and isinstance(xlrh1_usb_payload_filename, str)
        and all(isinstance(b, bool) for b in bools)
        and _is_non_negative_int(sample_rate_hz)
        and _is_non_negative_int(bit_depth)
        and _is_non_negative_int(channel_count)
        and _is_non_negative_int(phantom_48v_glitch_events)
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G64_TELEMETRY_INVALID)
        errors.append("Gate G64 received invalid or malformed XLR-H1 / MI-Shoe telemetry.")

    routing_ok = False
    override_sq_ok = False
    phantom_ok = False
    usb_fw_ok = False

    if telemetry_ok:
        routing_ok, rt_code, rt_errs = validate_xlrh1_mishoe_digital_audio_routing(
            handle_model=handle_model,
            xlrh1_attached=xlrh1_attached,
            handle_audio_enabled=handle_audio_enabled,
            audio_format_mode=audio_format_mode,
            sample_rate_hz=sample_rate_hz,
            bit_depth=bit_depth,
            channel_count=channel_count,
            in1_in2_xlr_route=in1_in2_xlr_route,
            in3_35mm_route=in3_35mm_route,
            headphone_monitor_matrix=headphone_monitor_matrix,
            post_bodydata_reset_unreconciled=post_bodydata_reset_unreconciled,
        )
        if not routing_ok:
            _add_code(codes, rt_code)
            errors.extend(rt_errs)

        override_sq_ok, ov_code, ov_errs = validate_body_35mm_jack_override_and_sq_mute(
            xlrh1_attached=xlrh1_attached,
            body_35mm_mic_plugged=body_35mm_mic_plugged,
            mi_shoe_audio_set_locked_out=mi_shoe_audio_set_locked_out,
            sq_mode_active=sq_mode_active,
            mi_shoe_audio_muted=mi_shoe_audio_muted,
        )
        if not override_sq_ok:
            _add_code(codes, ov_code)
            errors.extend(ov_errs)

        phantom_ok, ph_code, ph_errs = validate_xlrh1_phantom_48v_stage_handoff(
            stage_transition=stage_transition,
            phantom_48v_enabled=phantom_48v_enabled,
            phantom_48v_rail_stable=phantom_48v_rail_stable,
            phantom_48v_glitch_events=phantom_48v_glitch_events,
            phantom_48v_slew_controlled=phantom_48v_slew_controlled,
            adc_soft_mute_during_handoff=adc_soft_mute_during_handoff,
            hotshoe_gpio_glitch_detected=hotshoe_gpio_glitch_detected,
        )
        if not phantom_ok:
            _add_code(codes, ph_code)
            errors.extend(ph_errs)

        usb_fw_ok, fw_code, fw_errs = validate_xlrh1_no_fake_usb_firmware_payload(
            xlrh1_usb_fw_update_attempted=xlrh1_usb_fw_update_attempted,
            xlrh1_standalone_usb_payload_present=xlrh1_standalone_usb_payload_present,
            xlrh1_usb_payload_filename=xlrh1_usb_payload_filename,
            xlrh1_standalone_usb_fw_rejected=xlrh1_standalone_usb_fw_rejected,
        )
        if not usb_fw_ok:
            _add_code(codes, fw_code)
            errors.extend(fw_errs)

    valid = (
        telemetry_ok
        and routing_ok
        and override_sq_ok
        and phantom_ok
        and usb_fw_ok
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G64 if valid else codes[0]
    body_override_detected = bool(
        isinstance(body_35mm_mic_plugged, bool)
        and isinstance(mi_shoe_audio_set_locked_out, bool)
        and (body_35mm_mic_plugged or mi_shoe_audio_set_locked_out)
    )

    return XlrH1MiShoeAudioGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        handle_model=str(handle_model) if isinstance(handle_model, str) else "INVALID",
        xlrh1_attached=bool(xlrh1_attached) if isinstance(xlrh1_attached, bool) else False,
        handle_audio_enabled=bool(handle_audio_enabled) if isinstance(handle_audio_enabled, bool) else False,
        audio_format_mode=str(audio_format_mode) if isinstance(audio_format_mode, str) else "INVALID",
        sample_rate_hz=int(sample_rate_hz) if _is_non_negative_int(sample_rate_hz) else -1,
        bit_depth=int(bit_depth) if _is_non_negative_int(bit_depth) else -1,
        channel_count=int(channel_count) if _is_non_negative_int(channel_count) else -1,
        in1_in2_xlr_route=str(in1_in2_xlr_route) if isinstance(in1_in2_xlr_route, str) else "INVALID",
        in3_35mm_route=str(in3_35mm_route) if isinstance(in3_35mm_route, str) else "INVALID",
        headphone_monitor_matrix=str(headphone_monitor_matrix) if isinstance(headphone_monitor_matrix, str) else "INVALID",
        post_bodydata_reset_unreconciled=bool(post_bodydata_reset_unreconciled) if isinstance(post_bodydata_reset_unreconciled, bool) else True,
        routing_and_format_valid=routing_ok,
        body_35mm_mic_plugged=bool(body_35mm_mic_plugged) if isinstance(body_35mm_mic_plugged, bool) else True,
        mi_shoe_audio_set_locked_out=bool(mi_shoe_audio_set_locked_out) if isinstance(mi_shoe_audio_set_locked_out, bool) else True,
        body_35mm_override_detected=body_override_detected,
        sq_mode_active=bool(sq_mode_active) if isinstance(sq_mode_active, bool) else False,
        mi_shoe_audio_muted=bool(mi_shoe_audio_muted) if isinstance(mi_shoe_audio_muted, bool) else False,
        body_35mm_and_sq_valid=override_sq_ok,
        stage_transition=str(stage_transition) if isinstance(stage_transition, str) else "INVALID",
        phantom_48v_enabled=bool(phantom_48v_enabled) if isinstance(phantom_48v_enabled, bool) else False,
        phantom_48v_rail_stable=bool(phantom_48v_rail_stable) if isinstance(phantom_48v_rail_stable, bool) else False,
        phantom_48v_glitch_events=int(phantom_48v_glitch_events) if _is_non_negative_int(phantom_48v_glitch_events) else -1,
        phantom_48v_slew_controlled=bool(phantom_48v_slew_controlled) if isinstance(phantom_48v_slew_controlled, bool) else False,
        adc_soft_mute_during_handoff=bool(adc_soft_mute_during_handoff) if isinstance(adc_soft_mute_during_handoff, bool) else False,
        hotshoe_gpio_glitch_detected=bool(hotshoe_gpio_glitch_detected) if isinstance(hotshoe_gpio_glitch_detected, bool) else True,
        phantom_handoff_valid=phantom_ok,
        xlrh1_usb_fw_update_attempted=bool(xlrh1_usb_fw_update_attempted) if isinstance(xlrh1_usb_fw_update_attempted, bool) else True,
        xlrh1_standalone_usb_payload_present=bool(xlrh1_standalone_usb_payload_present) if isinstance(xlrh1_standalone_usb_payload_present, bool) else True,
        xlrh1_usb_payload_filename=str(xlrh1_usb_payload_filename) if isinstance(xlrh1_usb_payload_filename, str) else "INVALID",
        xlrh1_standalone_usb_fw_rejected=bool(xlrh1_standalone_usb_fw_rejected) if isinstance(xlrh1_standalone_usb_fw_rejected, bool) else False,
        usb_fw_payload_guard_valid=usb_fw_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G63 & Gate G64 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g63_fx3a_branch_firewall(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    fx3a_firewall_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase187DonorAuditResult] = None,
) -> Tuple[GateVerdict, G63Fx3aBranchFirewallResult]:
    """Evaluate Gate G63 (`ILME-FX3` vs `ILME-FX3A` Hardware-Branch Firewall)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase187_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(fx3a_firewall_kwargs or {})
    guard = verify_fx3_vs_fx3a_branch_firewall(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE187_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G63 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G63 if valid else codes[0]

    res = G63Fx3aBranchFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        fx3a_branch_firewall=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, body={guard.body_model_name}({guard.body_model_id_hex}), "
        f"fw={guard.body_firmware_version}, lcd={guard.lcd_dot_count}, "
        f"nfc={guard.nfc_hardware_present}, ir={guard.ir_receiver_present}, "
        f"bodydata_ver={guard.bodydata_version}({guard.bodydata_branch}), "
        f"camset_isolated={guard.camset_isolation_valid}"
    )

    verdict = GateVerdict(
        gate_id=G63_GATE_ID,
        gate_code=G63_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g64_xlrh1_mishoe_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    xlrh1_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase187DonorAuditResult] = None,
) -> Tuple[GateVerdict, G64XlrH1MiShoeGuardResult]:
    """Evaluate Gate G64 (`XLR-H1` MI-Shoe `48kHz/24bit 4ch` Override Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase187_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(xlrh1_mishoe_kwargs or {})
    guard = verify_xlrh1_mishoe_4ch_vs_35mm_override_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE187_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G64 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G64 if valid else codes[0]

    res = G64XlrH1MiShoeGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        xlrh1_mishoe_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, handle={guard.handle_model}(on={guard.handle_audio_enabled}), "
        f"fmt={guard.audio_format_mode}, hp={guard.headphone_monitor_matrix}, "
        f"body_35mm={guard.body_35mm_mic_plugged}, sq={guard.sq_mode_active}(muted={guard.mi_shoe_audio_muted}), "
        f"48v_glitches={guard.phantom_48v_glitch_events}, usb_fw_rejected={guard.usb_fw_payload_guard_valid}"
    )

    verdict = GateVerdict(
        gate_id=G64_GATE_ID,
        gate_code=G64_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 64-Gate Master Safety Preflight (`G01..G64`)
# ---------------------------------------------------------------------------


def evaluate_64gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G62 pass-throughs
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
    ptpip_or_mc_requests: Optional[Sequence[Any]] = None,
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
    uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None,
    imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_ufu_kwargs: Optional[Mapping[str, Any]] = None,
    five_tier_el3_kwargs: Optional[Mapping[str, Any]] = None,
    cxd90058_sabin_kwargs: Optional[Mapping[str, Any]] = None,
    factory_seal_kwargs: Optional[Mapping[str, Any]] = None,
    c2pa_cert_kwargs: Optional[Mapping[str, Any]] = None,
    tc_gyro_meta_kwargs: Optional[Mapping[str, Any]] = None,
    dualmedia_vault_kwargs: Optional[Mapping[str, Any]] = None,
    bench_interlock_kwargs: Optional[Mapping[str, Any]] = None,
    ssboot_wbi2_kwargs: Optional[Mapping[str, Any]] = None,
    slot1_ufu_c2pa_kwargs: Optional[Mapping[str, Any]] = None,
    emount_breathing_kwargs: Optional[Mapping[str, Any]] = None,
    hdmi_raw_kwargs: Optional[Mapping[str, Any]] = None,
    # G63 inputs (ILME-FX3 vs ILME-FX3A LCD/NFC/IR & BODYDATA/CAMSET Firewall)
    fx3a_firewall_kwargs: Optional[Mapping[str, Any]] = None,
    # G64 inputs (XLR-H1 MI-Shoe 48kHz/24bit 4ch vs Body 3.5mm Override Guard)
    xlrh1_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master64GateReport:
    """Evaluate all 64 Master Safety Gates (`G01..G64`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        if dry_run_simulated_backup is None
        else (dry_run_simulated or dry_run_simulated_backup)
    )

    m62_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated": effective_dry_run,
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
        "uart1v8_isp_kwargs": uart1v8_isp_kwargs,
        "imx510_sensor_cal_kwargs": imx510_sensor_cal_kwargs,
        "cfexpress_ufu_kwargs": cfexpress_ufu_kwargs,
        "five_tier_el3_kwargs": five_tier_el3_kwargs,
        "cxd90058_sabin_kwargs": cxd90058_sabin_kwargs,
        "factory_seal_kwargs": factory_seal_kwargs,
        "c2pa_cert_kwargs": c2pa_cert_kwargs,
        "tc_gyro_meta_kwargs": tc_gyro_meta_kwargs,
        "dualmedia_vault_kwargs": dualmedia_vault_kwargs,
        "bench_interlock_kwargs": bench_interlock_kwargs,
        "ssboot_wbi2_kwargs": ssboot_wbi2_kwargs,
        "slot1_ufu_c2pa_kwargs": slot1_ufu_c2pa_kwargs,
        "emount_breathing_kwargs": emount_breathing_kwargs,
        "hdmi_raw_kwargs": hdmi_raw_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m62_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m62_report: Master62GateReport = evaluate_62gate_preflight(
        resolved_root, **m62_kwargs
    )

    phase187_audit = audit_phase187_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g63_verdict, g63_res = evaluate_g63_fx3a_branch_firewall(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        fx3a_firewall_kwargs=fx3a_firewall_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase187_audit,
    )

    g64_verdict, g64_res = evaluate_g64_xlrh1_mishoe_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        xlrh1_mishoe_kwargs=xlrh1_mishoe_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase187_audit,
    )

    gates_63_to_64 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g63_verdict, g64_verdict)
    ]
    all_gates = tuple(list(m62_report.gates) + gates_63_to_64)

    g01_to_g12_verified = int(m62_report.summary["g01_to_g12_verified"])
    g13_to_g62_verified = (
        int(m62_report.summary["g13_to_g60_verified"])
        + int(m62_report.summary["g61_to_g62_verified"])
    )
    g63_to_g64_verified = sum(1 for v in (g63_verdict, g64_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g62_verified + g63_to_g64_verified

    g63_to_g64_all_passed = g63_to_g64_verified == 2
    g13_to_g64_all_passed = (
        m62_report.g13_to_g62_all_passed and g63_to_g64_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m62_report.gates[:9])

    offline_61_verified = (
        g01_to_g09_ok
        and m62_report.offline_59_gates_verified
        and g63_to_g64_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_64_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g64_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes
    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m62_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_61_verified
        and m62_report.h0_h1_trial_entry_allowed
        and g63_to_g64_all_passed
        and agent_auto_flash_blocked
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m62_report.errors) + list(g63_verdict.errors) + list(g64_verdict.errors)
    )
    warnings: List[str] = (
        list(m62_report.warnings)
        + list(g63_verdict.warnings)
        + list(g64_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m62_report.g13_to_g62_all_passed:
        overall_status = m62_report.status
    elif not g63_verdict.passed:
        overall_status = g63_verdict.status
    elif not g64_verdict.passed:
        overall_status = g64_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_64_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_64_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_64_verified:
        overall_status = "VERIFIED_ALL_64_GATES"
    else:
        overall_status = "VERIFIED_61_OF_64_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m62_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g63_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g64_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 64,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 64 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g62_verified": g13_to_g62_verified,
        "g63_to_g64_verified": g63_to_g64_verified,
        "g13_to_g64_all_passed": g13_to_g64_all_passed,
        "g63_to_g64_all_passed": g63_to_g64_all_passed,
        "offline_61_gates_verified": offline_61_verified,
        "all_64_gates_verified": all_64_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master64GateReport(
        schema=REALHW_FX3A_FIREWALL_XLRH1_MISHOE_64GATE_SCHEMA,
        version=REALHW_FX3A_FIREWALL_XLRH1_MISHOE_64GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_61_gates_verified=offline_61_verified,
        all_64_gates_verified=all_64_verified,
        g13_to_g64_all_passed=g13_to_g64_all_passed,
        g63_to_g64_all_passed=g63_to_g64_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        summary=summary,
        gates=all_gates,
        master_62_report=m62_report.to_dict(),
        g63_result=g63_res.to_dict(),
        g64_result=g64_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_64_master_safety_gates = evaluate_64gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard",
        description=(
            "Phase 187 — ILME-FX3 vs ILME-FX3A Hardware-Branch Firewall (G63), "
            "XLR-H1 MI-Shoe 48kHz/24bit 4ch vs Body 3.5mm Override Guard (G64), "
            "and 64-Gate Master Preflight (G01..G64)"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G64 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_64gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/64 "
            f"g63_to_g64_all_passed={report.g63_to_g64_all_passed} "
            f"all_64_gates_verified={report.all_64_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized} "
            f"physical_usb_packets_emitted={report.physical_usb_packets_emitted} "
            f"raw_firmware_bytes_leaked={report.raw_firmware_bytes_leaked}\n"
        )
    ok = (
        report.all_64_gates_verified
        if args.dry_run_simulated
        else report.offline_61_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
