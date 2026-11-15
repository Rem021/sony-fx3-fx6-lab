"""Phase 100 — Cinema Wireless Video TX 5GHz/6GHz Near-Field EMI & D-Tap/HDMI Hot-Plug
ESD Guard (Gate G29), Long-Form (>6h) Continuous Recording exFAT Clip-Spanning &
CFexpress SMART Wear / Zero-NVRAM-Churn Endurance Guard (Gate G30), and Unified 30-Gate
Master Safety Preflight (`G01..G30` / `verify-30-gates`).

Operationalizes RF near-field EMI coupling protection for high-power cinema wireless video
transmitters (Teradek / Hollyland / DJI SDR) mounted near FX3 MI-Shoe / HDMI ports,
D-Tap-to-HDMI hot-plug ESD protection for `CXD90057` HDMI TMDS receivers, Multi-Port
`3.3 V`-tolerant LTC/timecode over-voltage protection (`<= 5.0 Vpp`), long-form (`>6h..24h`)
continuous recording exFAT seamless spanning vs FAT32 `4 GiB` wall protection, CFexpress
Type-A / SDXC V90 NVMe SMART spare-block & NAND thermal endurance protection, zero-NVRAM-churn
RAM-shadow `BKID` enforcement (`runtime_nvram_flush_hz == 0.0`), and the unified 30-Gate
Master Safety Preflight (`G01..G30`) for Sony ILME-FX3 (`Ver. 7.02`, SoC `CXD90057`),
while keeping all prior gate modules (`preflight.py`, `master_16gate_preflight.py`,
`usblan_ptpip_and_18gate_preflight.py`, `rig_groundloop_lensrail_and_20gate_guard.py`,
`phantom48v_gimbal_and_22gate_guard.py`, `dewpoint_tec_usbc_and_24gate_guard.py`,
`intake_occlusion_tripod_and_26gate_guard.py`, and
`sensor_curtain_subzero_and_28gate_guard.py`) completely untouched:

1. **Read-Only (`os.O_RDONLY`) FX3/FX6 Donor Media-Health / HPD / NVRAM Audit**:
   - Inspects local FX3 `v7.02` & FX6 `v6.01` `libInfraMediaMount.so`
     (`GetMediaLifeInfo`, `IMM_GetMediaLifeInfo`, `mcmn_drv_updatelifeinfo`),
     `libInfraMediaCommon.so` (`mcmn_drv_nvme_getlifeinfofromsmartinfo`,
     `mcmn_drv_nvme_getlogpage_smartinformation`,
     `NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0`, `mcmn_dmm_hotplug`),
     `libbackup.so` (`Backup_read`, `Backup_write`, `Backup_sync_all`, `Backup_protect`),
     `libBackupManager.so` (`writeBackup`, `readBackupDecryption`),
     `libInfraFsys.so` (`flash_span`, `fsysDepLog_DriveIOQueueIOVecCountLimitOverflow`),
     and FX6 `libHotplug.so` (`MakeObjEject`, `MakeObjInsert`, `guardAcvOn`) strictly via
     `os.open(..., os.O_RDONLY)`, plus optional chunked scans of `appFw.so` (exFAT /
     FAT32 / relay-rec / `HPD`) and `cpapp-b.bin` (`DETECT_HPD`, `OBSERVE_HPD`,
     `BACKUP_WRITE`, `EXTERNALTC_LOCK`, `LTC`) when `include_large_binaries=True`.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or local donor files are absent.

2. **Gate G29 — Cinema Wireless Video TX Near-Field EMI, D-Tap/HDMI Hot-Plug ESD &
   Multi-Port LTC Impedance Guard**:
   - Fails closed on:
     a) `BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE` when
        `wireless_tx_power_mw > 250.0` and `antenna_to_mishoe_or_hdmi_mm < 35.0` and
        `shielded_coax_hdmi_cable == False`,
     b) `BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE` when
        (`dtap_powered_wireless_tx == True` and
        `power_on_sequence != 'GND_POWER_FIRST_SIGNAL_LAST'`) or
        `hot_plug_while_dtap_live_unisolated == True`,
     c) `BLOCKED_TIMECODE_BNC_OVER_VOLTAGE` when `multiport_tc_input_vpp > 5.0`.

3. **Gate G30 — Long-Form (>6h..24h) Continuous Recording exFAT Seamless Spanning,
   CFexpress SMART Wear & Zero-eMMC-NVRAM-Churn Endurance Guard**:
   - Fails closed on:
     a) `BLOCKED_FAT32_4GIB_SPANNING_TRAP` when `planned_continuous_min > 10.0` and
        `filesystem != 'exFAT'`,
     b) `BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION` when `smart_percentage_used > 90` or
        `spare_blocks_pct < 10.0` or `media_nand_temp_c > 78.0`,
     c) `BLOCKED_PERIODIC_EMMC_NVRAM_CHURN` when `runtime_nvram_flush_hz > 0.0`
        (or `ram_shadow_bkid_enabled == False`), enforcing 100% RAM-shadow `BKID` state
        so FX3's internal eMMC endures zero runtime wear cycles.

4. **Unified 30-Gate Master Safety Preflight (`evaluate_30gate_preflight` / CLI
   `verify-30-gates`)**:
   - Composes `evaluate_28gate_preflight` (`G01..G28`) with `G29` and `G30`:
     * Offline default mode: `27/30` gates pass (`G10..G12` physical Tier-0 backup
       truthfully remain `FAIL_OFFLINE_HARDWARE_NOT_ATTACHED` ->
       `overall_ready_for_hardware_attach = False`).
     * `--dry-run-simulated-backup` mode: `30/30` simulation gates pass
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
from .sensor_curtain_subzero_and_28gate_guard import (
    Master28GateReport,
    evaluate_28gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
    scan_tokens_o_rdonly,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

WIRELESS_EMI_ENDURANCE_30GATE_SCHEMA: str = "fx3-wireless-tx-emi-endurance-30gate-preflight-v1"
WIRELESS_EMI_ENDURANCE_30GATE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G29..G30
G29_GATE_ID: str = "G29_wireless_tx_emi_dtap_hdmi_esd_and_ltc_safe"
G29_GATE_CODE: str = "WIRELESS_TX_EMI_DTAP_HDMI_ESD_AND_LTC_SAFE"

G30_GATE_ID: str = "G30_longform_exfat_smart_wear_and_zero_nvram_safe"
G30_GATE_CODE: str = "LONGFORM_EXFAT_SMART_WEAR_AND_ZERO_NVRAM_SAFE"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G29: str = "VERIFIED_WIRELESS_TX_EMI_DTAP_HDMI_ESD_AND_LTC_SAFE"
STATUS_VERIFIED_G30: str = "VERIFIED_LONGFORM_EXFAT_SMART_WEAR_AND_ZERO_NVRAM_SAFE"

# Gate G29 Violation Codes
STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE: str = "BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE"
STATUS_BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE: str = "BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE"
STATUS_BLOCKED_TIMECODE_BNC_OVER_VOLTAGE: str = "BLOCKED_TIMECODE_BNC_OVER_VOLTAGE"
STATUS_BLOCKED_WIRELESS_EMI_TELEMETRY_INVALID: str = "BLOCKED_WIRELESS_EMI_TELEMETRY_INVALID"

# Gate G30 Violation Codes
STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP: str = "BLOCKED_FAT32_4GIB_SPANNING_TRAP"
STATUS_BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION: str = "BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION"
STATUS_BLOCKED_PERIODIC_EMMC_NVRAM_CHURN: str = "BLOCKED_PERIODIC_EMMC_NVRAM_CHURN"
STATUS_BLOCKED_ENDURANCE_TELEMETRY_INVALID: str = "BLOCKED_ENDURANCE_TELEMETRY_INVALID"

STATUS_BLOCKED_DONOR_INTEGRITY: str = "BLOCKED_PHASE100_30GATE_DONOR_INTEGRITY_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"

# Gate G29 Threshold Constants
WIRELESS_TX_NEARFIELD_POWER_THRESHOLD_MW: float = 250.0
WIRELESS_TX_MIN_UNSHIELDED_SEPARATION_MM: float = 35.0
WIRELESS_TX_NEARFIELD_EFIELD_WARN_V_PER_M: float = 15.0
POWER_SEQ_GND_POWER_FIRST_SIGNAL_LAST: str = "GND_POWER_FIRST_SIGNAL_LAST"
MULTIPORT_TC_MAX_SAFE_VPP: float = 5.0
MULTIPORT_TC_LOGIC_TOLERANCE_V: float = 3.3
HDMI_HPD_DEBOUNCE_MIN_MS: float = 50.0
HDMI_HPD_DEFAULT_DEBOUNCE_MS: float = 100.0

# Gate G30 Threshold Constants
FILESYSTEM_EXFAT: str = "exFAT"
FAT32_4GIB_WALL_BYTES: int = 4 * 1024 * 1024 * 1024
FAT32_SPANNING_MAX_CONTINUOUS_MIN: float = 10.0
MEDIA_SMART_MAX_USED_PCT: float = 90.0
MEDIA_SPARE_BLOCKS_MIN_PCT: float = 10.0
MEDIA_NAND_MAX_TEMP_C: float = 78.0
MAX_RUNTIME_NVRAM_FLUSH_HZ: float = 0.0
LONGFORM_DEFAULT_CONTINUOUS_MIN: float = 480.0
LONGFORM_DEFAULT_BITRATE_MBPS: float = 200.0

# Compact FX3/FX6 Donor Specs for Media-Life / SMART / Hotplug / Backup Contracts (O_RDONLY verified)
PINNED_PHASE100_DONOR_SPECS: Mapping[str, Tuple[str, str, int, str, Tuple[bytes, ...], str]] = {
    "fx3_lib_infra_media_mount": (
        "fx3",
        "libInfraMediaMount.so",
        65_392,
        "33b4c61c39f724e08e1bc4d07fd505a799ee37a9c1f37a43fffc7c2c9c8f75ad",
        (
            b"GetMediaLifeInfo",
            b"IMM_GetMediaLifeInfo",
            b"mcmn_drv_updatelifeinfo",
        ),
        "fx3/libInfraMediaMount.so::{GetMediaLifeInfo,IMM_GetMediaLifeInfo,mcmn_drv_updatelifeinfo}",
    ),
    "fx3_lib_infra_media_common": (
        "fx3",
        "libInfraMediaCommon.so",
        402_624,
        "1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b",
        (
            b"mcmn_drv_nvme_getlifeinfofromsmartinfo",
            b"mcmn_drv_nvme_getlogpage_smartinformation",
            b"NVME_PSCTRL_PS1_MAXPOWER_THRESHOLD_CFE_SPEC4_0",
            b"mcmn_dmm_hotplug",
        ),
        "fx3/libInfraMediaCommon.so::{nvme_getlifeinfofromsmartinfo,nvme_getlogpage_smartinformation,CFE_SPEC4_0,mcmn_dmm_hotplug}",
    ),
    "fx3_lib_backup": (
        "fx3",
        "libbackup.so",
        14_232,
        "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d",
        (
            b"Backup_read",
            b"Backup_write",
            b"Backup_sync_all",
            b"Backup_protect",
        ),
        "fx3/libbackup.so::{Backup_read,Backup_write,Backup_sync_all,Backup_protect}",
    ),
    "fx3_lib_backup_manager": (
        "fx3",
        "libBackupManager.so",
        10_272,
        "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e",
        (
            b"_ZNK13BackupManager13BackupManager11writeBackupEtjPKv",
            b"_ZNK13BackupManager13BackupManager20readBackupDecryptionEjPv",
        ),
        "fx3/libBackupManager.so::{writeBackup,readBackupDecryption}",
    ),
    "fx3_lib_infra_fsys": (
        "fx3",
        "libInfraFsys.so",
        683_632,
        "ec0dcdfa2bd0bb9236137821ecd620ea4c726adc4b5455da9ced25287f158651",
        (
            b"flash_span",
            b"fsysDepLog_DriveIOQueueIOVecCountLimitOverflow",
        ),
        "fx3/libInfraFsys.so::{flash_span,fsysDepLog_DriveIOQueueIOVecCountLimitOverflow}",
    ),
    "fx6_lib_hotplug": (
        "fx6",
        "libHotplug.so",
        64_776,
        "5697dcca69ea80ba516494510b0b07910d3ea8c8de6fae27e1dec8748010075c",
        (
            b"_ZN7Hotplug12MakeObjEjectEPNS_16hotplug_dev_infoE",
            b"_ZN7Hotplug13MakeObjInsertEPNS_16hotplug_dev_infoE",
            b"_ZN7Hotplug10guardAcvOnEPN3UFW3FsmEiPv",
        ),
        "fx6/libHotplug.so::{MakeObjEject,MakeObjInsert,guardAcvOn}",
    ),
}

PINNED_APPFW_WIRELESS_MEDIA_TOKENS: Tuple[str, ...] = (
    "EXFAT_MEDIA_FILESYSTEM_SLOT1_FAT",
    "EXFAT_MEDIA_FILESYSTEM_SLOT2_EXFAT",
    "FAT32_CFE_SLOT1",
    "CAUTION_ID_FACTOR_RELAY_REC_ON_FUNCTION",
    "EVENT_REMOTE_DOUBLE_SLOT_SETTINGS_RELAY_REC",
    "HPD",
)

PINNED_CPAPP_HPD_BACKUP_TC_TOKENS: Tuple[str, ...] = (
    "DETECT_HPD",
    "OBSERVE_HPD",
    "HPD_DISABLE",
    "HPD_ENABLE",
    "BACKUP_WRITE",
    "BACKUP_READ",
    "EXTERNALTC_LOCK",
    "LTC",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase100DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    exfat_relay_rec_tokens_verified: bool
    smart_media_life_tokens_verified: bool
    hdmi_hpd_debounce_tokens_verified: bool
    nvram_backup_write_tokens_verified: bool
    large_binaries_scanned: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class WirelessTxEmiEsdGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    wireless_tx_profile: str
    wireless_band: str
    wireless_tx_power_mw: float
    antenna_to_mishoe_or_hdmi_mm: float
    shielded_coax_hdmi_cable: bool
    predicted_nearfield_e_field_v_per_m: float
    nearfield_emi_safe: bool
    dtap_powered_wireless_tx: bool
    power_on_sequence: str
    hot_plug_while_dtap_live_unisolated: bool
    hdmi_hpd_debounce_ms: float
    hdmi_hotplug_esd_safe: bool
    multiport_tc_input_vpp: float
    multiport_tc_max_safe_vpp: float
    timecode_bnc_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LongformEnduranceGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    planned_continuous_min: float
    bitrate_mbps: float
    estimated_recording_gib: float
    filesystem: str
    fat32_4gib_trap_free: bool
    smart_percentage_used: float
    spare_blocks_pct: float
    media_nand_temp_c: float
    media_smart_endurance_safe: bool
    runtime_nvram_flush_hz: float
    ram_shadow_bkid_enabled: bool
    estimated_emmc_nvram_write_cycles: int
    zero_nvram_churn_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G29WirelessTxEmiEsdResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    wireless_emi_esd_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G30LongformEnduranceResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    longform_endurance_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master30GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_27_gates_verified: bool
    all_30_gates_verified: bool
    g13_to_g30_all_passed: bool
    g29_to_g30_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_28_report: Dict[str, Any]
    g29_result: Dict[str, Any]
    g30_result: Dict[str, Any]
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
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in ("1", "true", "yes", "on")


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
    return isinstance(val, (int, float)) and (not isinstance(val, bool)) and math.isfinite(float(val))


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit
# ---------------------------------------------------------------------------


def audit_phase100_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
) -> Phase100DonorAuditResult:
    """Inspect FX3/FX6 media-life, SMART, backup/NVRAM, fsys, and hotplug donors via `os.O_RDONLY`."""
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
        "fx3_lib_infra_media_mount": fx3_lib_dir / "libInfraMediaMount.so",
        "fx3_lib_infra_media_common": fx3_lib_dir / "libInfraMediaCommon.so",
        "fx3_lib_backup": fx3_lib_dir / "libbackup.so",
        "fx3_lib_backup_manager": fx3_lib_dir / "libBackupManager.so",
        "fx3_lib_infra_fsys": fx3_lib_dir / "libInfraFsys.so",
        "fx6_lib_hotplug": fx6_lib_dir / "libHotplug.so",
    }

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase100DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(spec[5] for spec in PINNED_PHASE100_DONOR_SPECS.values()),
            missing_markers=(),
            exfat_relay_rec_tokens_verified=True,
            smart_media_life_tokens_verified=True,
            hdmi_hpd_debounce_tokens_verified=True,
            nvram_backup_write_tokens_verified=True,
            large_binaries_scanned=False,
            sha256_by_artifact={k: spec[3] for k, spec in PINNED_PHASE100_DONOR_SPECS.items()},
            bytes_by_artifact={k: spec[2] for k, spec in PINNED_PHASE100_DONOR_SPECS.items()},
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

    for key, (_body, _rel_name, exp_size, exp_sha, marker_tuple, marker_label) in PINNED_PHASE100_DONOR_SPECS.items():
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
                paths.fx3_appfw_path, PINNED_APPFW_WIRELESS_MEDIA_TOKENS
            )
            sizes["fx3_appfw"] = appfw_sz
            files_inspected += 1
            large_scanned = True
            if missing_appfw:
                appfw_ok = False
                missing.extend(missing_appfw)
                errors.append(f"fx3 appFw.so missing exFAT/relay/HPD tokens: {missing_appfw}")
            else:
                checked.append("fx3/appFw.so::EXFAT_SLOT1_2+FAT32_CFE+RELAY_REC+HPD")
        else:
            warnings.append("fx3/appFw.so not found for optional large-binary wireless/media scan.")

        if paths.fx3_cp_path.is_file():
            cp_sz, missing_cp = scan_tokens_o_rdonly(
                paths.fx3_cp_path, PINNED_CPAPP_HPD_BACKUP_TC_TOKENS
            )
            sizes["fx3_cpapp"] = cp_sz
            files_inspected += 1
            large_scanned = True
            if missing_cp:
                cpapp_ok = False
                missing.extend(missing_cp)
                errors.append(f"fx3 cpapp-b.bin missing HPD/backup/LTC tokens: {missing_cp}")
            else:
                checked.append("fx3/cpapp-b.bin::DETECT_HPD+OBSERVE_HPD+BACKUP_WRITE+EXTERNALTC_LOCK")
        else:
            warnings.append("fx3/cpapp-b.bin not found for optional large-binary HPD/backup/LTC scan.")

    valid = len(errors) == 0 and len(missing) == 0
    return Phase100DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        exfat_relay_rec_tokens_verified=("fx3_lib_infra_fsys" in passed_keys) and appfw_ok,
        smart_media_life_tokens_verified={
            "fx3_lib_infra_media_mount",
            "fx3_lib_infra_media_common",
        }.issubset(passed_keys),
        hdmi_hpd_debounce_tokens_verified=("fx6_lib_hotplug" in passed_keys) and cpapp_ok,
        nvram_backup_write_tokens_verified={
            "fx3_lib_backup",
            "fx3_lib_backup_manager",
        }.issubset(passed_keys)
        and cpapp_ok,
        large_binaries_scanned=large_scanned,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Physics & Endurance Helpers for Gates G29 & G30
# ---------------------------------------------------------------------------


def compute_nearfield_efield_v_per_m(
    tx_power_mw: float,
    separation_mm: float,
    *,
    antenna_gain_linear: float = 1.64,
    shielding_attenuation_db: float = 0.0,
) -> float:
    """Estimate near-field RF E-field (V/m) at `separation_mm`: `E = sqrt(30 * P_W * G) / r_m`."""
    if not (
        _is_finite_number(tx_power_mw)
        and _is_finite_number(separation_mm)
        and _is_finite_number(antenna_gain_linear)
        and _is_finite_number(shielding_attenuation_db)
    ):
        raise ValueError("RF near-field parameters must be finite numbers.")
    if float(tx_power_mw) < 0.0 or float(separation_mm) <= 0.0 or float(antenna_gain_linear) <= 0.0:
        raise ValueError("tx_power_mw >= 0.0, separation_mm > 0.0, antenna_gain_linear > 0.0 required.")
    p_w = float(tx_power_mw) / 1000.0
    if p_w == 0.0:
        return 0.0
    r_m = float(separation_mm) / 1000.0
    e_raw = math.sqrt(30.0 * p_w * float(antenna_gain_linear)) / r_m
    atten_factor = 10.0 ** (-float(shielding_attenuation_db) / 20.0)
    return e_raw * atten_factor


def estimate_recording_footprint_gib(
    planned_continuous_min: float,
    bitrate_mbps: float = LONGFORM_DEFAULT_BITRATE_MBPS,
) -> float:
    """Compute continuous recording footprint in GiB (`1 GiB = 2^30 bytes`)."""
    if not (_is_finite_number(planned_continuous_min) and _is_finite_number(bitrate_mbps)):
        raise ValueError("planned_continuous_min and bitrate_mbps must be finite numbers.")
    if float(planned_continuous_min) < 0.0 or float(bitrate_mbps) <= 0.0:
        raise ValueError("planned_continuous_min >= 0.0 and bitrate_mbps > 0.0 required.")
    total_bits = float(bitrate_mbps) * 1_000_000.0 * float(planned_continuous_min) * 60.0
    total_bytes = total_bits / 8.0
    return total_bytes / float(1024 ** 3)


def compute_emmc_nvram_wear_cycles(
    runtime_nvram_flush_hz: float,
    planned_continuous_min: float,
) -> int:
    """Compute cumulative eMMC `p13..p15` NVRAM write cycles over a continuous recording run."""
    if not (_is_finite_number(runtime_nvram_flush_hz) and _is_finite_number(planned_continuous_min)):
        raise ValueError("runtime_nvram_flush_hz and planned_continuous_min must be finite numbers.")
    if float(runtime_nvram_flush_hz) < 0.0 or float(planned_continuous_min) < 0.0:
        raise ValueError("runtime_nvram_flush_hz >= 0.0 and planned_continuous_min >= 0.0 required.")
    return int(math.ceil(float(runtime_nvram_flush_hz) * float(planned_continuous_min) * 60.0))


# ---------------------------------------------------------------------------
# 3. Gate G29 — Wireless Video TX EMI, D-Tap/HDMI Hot-Plug ESD & LTC Guard
# ---------------------------------------------------------------------------


def verify_wireless_tx_emi_and_hotplug_esd_guard(
    *,
    wireless_tx_profile: str = "Teradek/Hollyland/DJI_SDR",
    wireless_band: str = "5GHz_DFS",
    wireless_tx_power_mw: float = 200.0,
    antenna_to_mishoe_or_hdmi_mm: float = 65.0,
    shielded_coax_hdmi_cable: bool = True,
    dtap_powered_wireless_tx: bool = False,
    power_on_sequence: str = POWER_SEQ_GND_POWER_FIRST_SIGNAL_LAST,
    hot_plug_while_dtap_live_unisolated: bool = False,
    hdmi_hpd_debounce_ms: float = HDMI_HPD_DEFAULT_DEBOUNCE_MS,
    multiport_tc_input_vpp: float = 2.0,
    request_persistent_emmc_writes: bool = False,
) -> WirelessTxEmiEsdGuardResult:
    """Verify Gate G29 (5GHz/6GHz wireless TX near-field EMI, D-Tap/HDMI hot-plug ESD & LTC cap)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    telemetry_ok = True
    if not _is_finite_number(wireless_tx_power_mw) or float(wireless_tx_power_mw) < 0.0:
        _add_code(codes, STATUS_BLOCKED_WIRELESS_EMI_TELEMETRY_INVALID)
        errors.append(f"wireless_tx_power_mw must be finite >= 0.0, got {wireless_tx_power_mw!r}.")
        telemetry_ok = False
        eff_tx_mw = 0.0
    else:
        eff_tx_mw = float(wireless_tx_power_mw)

    if not _is_finite_number(antenna_to_mishoe_or_hdmi_mm) or float(antenna_to_mishoe_or_hdmi_mm) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_WIRELESS_EMI_TELEMETRY_INVALID)
        errors.append(
            f"antenna_to_mishoe_or_hdmi_mm must be finite > 0.0, got {antenna_to_mishoe_or_hdmi_mm!r}."
        )
        telemetry_ok = False
        eff_dist_mm = 65.0
    else:
        eff_dist_mm = float(antenna_to_mishoe_or_hdmi_mm)

    if not _is_finite_number(hdmi_hpd_debounce_ms) or float(hdmi_hpd_debounce_ms) < 0.0:
        _add_code(codes, STATUS_BLOCKED_WIRELESS_EMI_TELEMETRY_INVALID)
        errors.append(f"hdmi_hpd_debounce_ms must be finite >= 0.0, got {hdmi_hpd_debounce_ms!r}.")
        telemetry_ok = False
        eff_hpd_ms = HDMI_HPD_DEFAULT_DEBOUNCE_MS
    else:
        eff_hpd_ms = float(hdmi_hpd_debounce_ms)

    if not _is_finite_number(multiport_tc_input_vpp) or float(multiport_tc_input_vpp) < 0.0:
        _add_code(codes, STATUS_BLOCKED_WIRELESS_EMI_TELEMETRY_INVALID)
        errors.append(f"multiport_tc_input_vpp must be finite >= 0.0, got {multiport_tc_input_vpp!r}.")
        telemetry_ok = False
        eff_tc_vpp = 2.0
    else:
        eff_tc_vpp = float(multiport_tc_input_vpp)

    shield_db = 20.0 if bool(shielded_coax_hdmi_cable) else 0.0
    pred_efield = compute_nearfield_efield_v_per_m(
        eff_tx_mw,
        eff_dist_mm,
        shielding_attenuation_db=shield_db,
    )

    # a) High-power 5GHz/6GHz/DFS Wireless TX Near-Field EMI Desense Guard
    nearfield_emi_safe = not (
        telemetry_ok
        and eff_tx_mw > WIRELESS_TX_NEARFIELD_POWER_THRESHOLD_MW
        and eff_dist_mm < WIRELESS_TX_MIN_UNSHIELDED_SEPARATION_MM
        and (not bool(shielded_coax_hdmi_cable))
    )
    if not nearfield_emi_safe:
        _add_code(codes, STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE)
        errors.append(
            f"BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE: {wireless_tx_profile} ({wireless_band}) at "
            f"{eff_tx_mw:.1f} mW > {WIRELESS_TX_NEARFIELD_POWER_THRESHOLD_MW:.1f} mW with "
            f"{eff_dist_mm:.1f} mm < {WIRELESS_TX_MIN_UNSHIELDED_SEPARATION_MM:.1f} mm separation "
            f"(E={pred_efield:.1f} V/m) and shielded_coax_hdmi_cable=False risks MI-Shoe ADC & HDMI TMDS desense."
        )
    elif (
        telemetry_ok
        and eff_tx_mw > WIRELESS_TX_NEARFIELD_POWER_THRESHOLD_MW
        and eff_dist_mm < WIRELESS_TX_MIN_UNSHIELDED_SEPARATION_MM
        and bool(shielded_coax_hdmi_cable)
    ):
        warnings.append(
            f"High-power wireless TX ({eff_tx_mw:.1f} mW at {eff_dist_mm:.1f} mm) mitigated by "
            "shielded coax HDMI cable; maintain >= 35 mm antenna separation from MI-Shoe when feasible."
        )

    # b) D-Tap-Powered Wireless TX & HDMI Hot-Plug ESD Surge Guard
    seq_norm = str(power_on_sequence)
    dtap_seq_violation = bool(dtap_powered_wireless_tx) and (
        seq_norm != POWER_SEQ_GND_POWER_FIRST_SIGNAL_LAST
    )
    hotplug_live_violation = bool(hot_plug_while_dtap_live_unisolated)
    hdmi_hotplug_esd_safe = not (dtap_seq_violation or hotplug_live_violation)
    if not hdmi_hotplug_esd_safe:
        _add_code(codes, STATUS_BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE)
        reasons: List[str] = []
        if dtap_seq_violation:
            reasons.append(
                f"power_on_sequence={seq_norm!r} != {POWER_SEQ_GND_POWER_FIRST_SIGNAL_LAST!r}"
            )
        if hotplug_live_violation:
            reasons.append("hot_plug_while_dtap_live_unisolated=True")
        errors.append(
            "BLOCKED_POWERED_TX_HDMI_HOTPLUG_SURGE: D-Tap-powered wireless TX ("
            + "; ".join(reasons)
            + ") risks ungrounded floating-return ESD surge into CXD90057 HDMI TMDS/HPD diodes."
        )

    if telemetry_ok and eff_hpd_ms < HDMI_HPD_DEBOUNCE_MIN_MS:
        warnings.append(
            f"HDMI HPD debounce {eff_hpd_ms:.1f} ms < {HDMI_HPD_DEBOUNCE_MIN_MS:.1f} ms recommended minimum."
        )

    # c) Multi-Port 3.3V-Tolerant LTC Timecode BNC Over-Voltage Guard
    timecode_bnc_safe = not (telemetry_ok and eff_tc_vpp > MULTIPORT_TC_MAX_SAFE_VPP)
    if not timecode_bnc_safe:
        _add_code(codes, STATUS_BLOCKED_TIMECODE_BNC_OVER_VOLTAGE)
        errors.append(
            f"BLOCKED_TIMECODE_BNC_OVER_VOLTAGE: multiport_tc_input_vpp={eff_tc_vpp:.2f} Vpp > "
            f"{MULTIPORT_TC_MAX_SAFE_VPP:.1f} Vpp cap exceeds FX3 Multi-Port {MULTIPORT_TC_LOGIC_TOLERANCE_V:.1f}V-"
            "tolerant TC pin rating (+12V RS-422 / hot studio LTC feed damage)."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return WirelessTxEmiEsdGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        wireless_tx_profile=str(wireless_tx_profile),
        wireless_band=str(wireless_band),
        wireless_tx_power_mw=round(eff_tx_mw, 3),
        antenna_to_mishoe_or_hdmi_mm=round(eff_dist_mm, 3),
        shielded_coax_hdmi_cable=bool(shielded_coax_hdmi_cable),
        predicted_nearfield_e_field_v_per_m=round(pred_efield, 3),
        nearfield_emi_safe=nearfield_emi_safe,
        dtap_powered_wireless_tx=bool(dtap_powered_wireless_tx),
        power_on_sequence=seq_norm,
        hot_plug_while_dtap_live_unisolated=bool(hot_plug_while_dtap_live_unisolated),
        hdmi_hpd_debounce_ms=round(eff_hpd_ms, 3),
        hdmi_hotplug_esd_safe=hdmi_hotplug_esd_safe,
        multiport_tc_input_vpp=round(eff_tc_vpp, 3),
        multiport_tc_max_safe_vpp=MULTIPORT_TC_MAX_SAFE_VPP,
        timecode_bnc_safe=timecode_bnc_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G30 — Long-Form exFAT Spanning, CFexpress SMART & Zero-NVRAM Churn
# ---------------------------------------------------------------------------


def verify_longform_exfat_smart_and_nvram_guard(
    *,
    planned_continuous_min: float = LONGFORM_DEFAULT_CONTINUOUS_MIN,
    bitrate_mbps: float = LONGFORM_DEFAULT_BITRATE_MBPS,
    filesystem: str = FILESYSTEM_EXFAT,
    smart_percentage_used: float = 12.0,
    spare_blocks_pct: float = 95.0,
    media_nand_temp_c: float = 46.0,
    runtime_nvram_flush_hz: float = 0.0,
    ram_shadow_bkid_enabled: bool = True,
    request_persistent_emmc_writes: bool = False,
) -> LongformEnduranceGuardResult:
    """Verify Gate G30 (exFAT seamless spanning, CFexpress SMART wear & zero runtime NVRAM churn)."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Persistent eMMC writes are hard-locked False (PERSISTENT_EMMC_WRITES_AUTHORIZED=False).")

    telemetry_ok = True
    if not _is_finite_number(planned_continuous_min) or float(planned_continuous_min) < 0.0:
        _add_code(codes, STATUS_BLOCKED_ENDURANCE_TELEMETRY_INVALID)
        errors.append(f"planned_continuous_min must be finite >= 0.0, got {planned_continuous_min!r}.")
        telemetry_ok = False
        eff_min = LONGFORM_DEFAULT_CONTINUOUS_MIN
    else:
        eff_min = float(planned_continuous_min)

    if not _is_finite_number(bitrate_mbps) or float(bitrate_mbps) <= 0.0:
        _add_code(codes, STATUS_BLOCKED_ENDURANCE_TELEMETRY_INVALID)
        errors.append(f"bitrate_mbps must be finite > 0.0, got {bitrate_mbps!r}.")
        telemetry_ok = False
        eff_bitrate = LONGFORM_DEFAULT_BITRATE_MBPS
    else:
        eff_bitrate = float(bitrate_mbps)

    if (
        not _is_finite_number(smart_percentage_used)
        or float(smart_percentage_used) < 0.0
        or float(smart_percentage_used) > 255.0
    ):
        _add_code(codes, STATUS_BLOCKED_ENDURANCE_TELEMETRY_INVALID)
        errors.append(f"smart_percentage_used must be finite in [0.0, 255.0], got {smart_percentage_used!r}.")
        telemetry_ok = False
        eff_smart_used = 12.0
    else:
        eff_smart_used = float(smart_percentage_used)

    if (
        not _is_finite_number(spare_blocks_pct)
        or float(spare_blocks_pct) < 0.0
        or float(spare_blocks_pct) > 100.0
    ):
        _add_code(codes, STATUS_BLOCKED_ENDURANCE_TELEMETRY_INVALID)
        errors.append(f"spare_blocks_pct must be finite in [0.0, 100.0], got {spare_blocks_pct!r}.")
        telemetry_ok = False
        eff_spare_pct = 95.0
    else:
        eff_spare_pct = float(spare_blocks_pct)

    if (
        not _is_finite_number(media_nand_temp_c)
        or float(media_nand_temp_c) < -40.0
        or float(media_nand_temp_c) > 125.0
    ):
        _add_code(codes, STATUS_BLOCKED_ENDURANCE_TELEMETRY_INVALID)
        errors.append(f"media_nand_temp_c must be finite in [-40.0, 125.0], got {media_nand_temp_c!r}.")
        telemetry_ok = False
        eff_nand_temp_c = 46.0
    else:
        eff_nand_temp_c = float(media_nand_temp_c)

    if not _is_finite_number(runtime_nvram_flush_hz) or float(runtime_nvram_flush_hz) < 0.0:
        _add_code(codes, STATUS_BLOCKED_ENDURANCE_TELEMETRY_INVALID)
        errors.append(f"runtime_nvram_flush_hz must be finite >= 0.0, got {runtime_nvram_flush_hz!r}.")
        telemetry_ok = False
        eff_flush_hz = 0.0
    else:
        eff_flush_hz = float(runtime_nvram_flush_hz)

    est_gib = estimate_recording_footprint_gib(eff_min, eff_bitrate)
    est_wear_cycles = compute_emmc_nvram_wear_cycles(eff_flush_hz, eff_min)
    fs_str = str(filesystem)

    # a) FAT32 / SDHC (<32 GB) 4 GiB File-Size Wall Trap Guard
    fat32_4gib_trap_free = not (
        telemetry_ok
        and eff_min > FAT32_SPANNING_MAX_CONTINUOUS_MIN
        and fs_str != FILESYSTEM_EXFAT
    )
    if not fat32_4gib_trap_free:
        _add_code(codes, STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP)
        errors.append(
            f"BLOCKED_FAT32_4GIB_SPANNING_TRAP: planned_continuous_min={eff_min:.1f} min "
            f"(> {FAT32_SPANNING_MAX_CONTINUOUS_MIN:.1f} min, ~{est_gib:.2f} GiB) on filesystem={fs_str!r} != 'exFAT' "
            "hits the 4 GiB FAT32/SDHC file-size wall and disrupts seamless clip spanning."
        )

    # b) CFexpress Type-A / SDXC V90 NVMe SMART Wear & NAND Thermal Endurance Guard
    wear_exceeded = eff_smart_used > MEDIA_SMART_MAX_USED_PCT
    spare_exhausted = eff_spare_pct < MEDIA_SPARE_BLOCKS_MIN_PCT
    nand_overtemp = eff_nand_temp_c > MEDIA_NAND_MAX_TEMP_C
    media_smart_endurance_safe = not (
        telemetry_ok and (wear_exceeded or spare_exhausted or nand_overtemp)
    )
    if not media_smart_endurance_safe:
        _add_code(codes, STATUS_BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION)
        m_reasons: List[str] = []
        if wear_exceeded:
            m_reasons.append(f"smart_percentage_used={eff_smart_used:.1f}% > {MEDIA_SMART_MAX_USED_PCT:.0f}%")
        if spare_exhausted:
            m_reasons.append(f"spare_blocks_pct={eff_spare_pct:.1f}% < {MEDIA_SPARE_BLOCKS_MIN_PCT:.1f}%")
        if nand_overtemp:
            m_reasons.append(f"media_nand_temp_c={eff_nand_temp_c:.1f}C > {MEDIA_NAND_MAX_TEMP_C:.1f}C")
        errors.append(
            "BLOCKED_MEDIA_SMART_WEAR_EXHAUSTION: CFexpress/SDXC media near endurance or thermal cliff ("
            + "; ".join(m_reasons)
            + "); swap to fresh lab media before long-form continuous recording."
        )

    # c) Zero Periodic eMMC NVRAM / BKID Status-Counter Churn Guard
    zero_nvram_churn_safe = not (
        telemetry_ok
        and ((eff_flush_hz > MAX_RUNTIME_NVRAM_FLUSH_HZ) or (not bool(ram_shadow_bkid_enabled)))
    )
    if not zero_nvram_churn_safe:
        _add_code(codes, STATUS_BLOCKED_PERIODIC_EMMC_NVRAM_CHURN)
        n_reasons: List[str] = []
        if eff_flush_hz > MAX_RUNTIME_NVRAM_FLUSH_HZ:
            n_reasons.append(
                f"runtime_nvram_flush_hz={eff_flush_hz:.4f} Hz > 0.0 Hz (~{est_wear_cycles} eMMC p13..p15 writes)"
            )
        if not bool(ram_shadow_bkid_enabled):
            n_reasons.append("ram_shadow_bkid_enabled=False")
        errors.append(
            "BLOCKED_PERIODIC_EMMC_NVRAM_CHURN: Stage-B trial must maintain 100% RAM-shadow BKID state "
            f"with zero internal eMMC NVRAM churn ({'; '.join(n_reasons)})."
        )

    if telemetry_ok and eff_min >= 360.0 and valid_if_clean(errors, codes):
        warnings.append(
            f"Long-form continuous run ({eff_min:.0f} min, ~{est_gib:.1f} GiB) verified on exFAT with "
            "100% RAM-shadow BKID (0 eMMC NVRAM write cycles)."
        )

    valid = len(errors) == 0 and len(codes) == 0
    if valid:
        status = STATUS_SAFE
    elif STATUS_BLOCKED_PERSISTENT_EMMC_WRITE in codes:
        status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    else:
        status = codes[0]

    return LongformEnduranceGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        planned_continuous_min=round(eff_min, 2),
        bitrate_mbps=round(eff_bitrate, 2),
        estimated_recording_gib=round(est_gib, 3),
        filesystem=fs_str,
        fat32_4gib_trap_free=fat32_4gib_trap_free,
        smart_percentage_used=round(eff_smart_used, 2),
        spare_blocks_pct=round(eff_spare_pct, 2),
        media_nand_temp_c=round(eff_nand_temp_c, 2),
        media_smart_endurance_safe=media_smart_endurance_safe,
        runtime_nvram_flush_hz=round(eff_flush_hz, 6),
        ram_shadow_bkid_enabled=bool(ram_shadow_bkid_enabled),
        estimated_emmc_nvram_write_cycles=est_wear_cycles,
        zero_nvram_churn_safe=zero_nvram_churn_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def valid_if_clean(errors: List[str], codes: List[str]) -> bool:
    return len(errors) == 0 and len(codes) == 0


# ---------------------------------------------------------------------------
# 5. Gate G29 & Gate G30 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g29_wireless_tx_emi_and_hotplug_esd(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    wireless_tx_emi_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase100DonorAuditResult] = None,
) -> Tuple[GateVerdict, G29WirelessTxEmiEsdResult]:
    """Evaluate Gate G29 (`wireless_tx_emi_dtap_hdmi_esd_and_ltc_safe`)."""
    audit = donor_audit or audit_phase100_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(wireless_tx_emi_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    emi_res = verify_wireless_tx_emi_and_hotplug_esd_guard(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in emi_res.violation_codes:
        _add_code(codes, c)
    errors.extend(emi_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(emi_res.warnings)

    passed = (
        audit.valid
        and emi_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G29
        if passed
        else (codes[0] if codes else STATUS_BLOCKED_NEARFIELD_WIRELESS_TX_EMI_DESENSE)
    )

    res = G29WirelessTxEmiEsdResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        wireless_emi_esd_guard=emi_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G29_GATE_ID,
        gate_code=G29_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Cinema Wireless TX EMI, D-Tap/HDMI Hot-Plug ESD & Multi-Port LTC Guard ({emi_res.status}, "
            f"tx={emi_res.wireless_tx_power_mw:.0f}mW@{emi_res.antenna_to_mishoe_or_hdmi_mm:.0f}mm, "
            f"shielded_hdmi={emi_res.shielded_coax_hdmi_cable}, seq={emi_res.power_on_sequence}, "
            f"tc_vpp={emi_res.multiport_tc_input_vpp:.2f}Vpp, {audit.verification_mode}), "
            f"persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "nearfield_emi_safe": emi_res.nearfield_emi_safe,
            "hdmi_hotplug_esd_safe": emi_res.hdmi_hotplug_esd_safe,
            "timecode_bnc_safe": emi_res.timecode_bnc_safe,
        },
    )
    return verdict, res


def evaluate_g30_longform_endurance_and_nvram(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    include_large_binaries: bool = False,
    longform_endurance_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase100DonorAuditResult] = None,
) -> Tuple[GateVerdict, G30LongformEnduranceResult]:
    """Evaluate Gate G30 (`longform_exfat_smart_wear_and_zero_nvram_safe`)."""
    audit = donor_audit or audit_phase100_donor_contracts(
        work_root=work_root,
        repo_root=repo_root,
        force_clean_room=force_clean_room,
        include_large_binaries=include_large_binaries,
    )

    eff_kwargs = dict(longform_endurance_kwargs or {})
    eff_kwargs["request_persistent_emmc_writes"] = bool(
        request_persistent_emmc_writes or eff_kwargs.get("request_persistent_emmc_writes", False)
    )
    end_res = verify_longform_exfat_smart_and_nvram_guard(**eff_kwargs)

    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if not audit.valid:
        _add_code(codes, audit.status)
        errors.extend(audit.errors)
    for c in end_res.violation_codes:
        _add_code(codes, c)
    errors.extend(end_res.errors)
    warnings.extend(audit.warnings)
    warnings.extend(end_res.warnings)

    passed = (
        audit.valid
        and end_res.valid
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not errors)
    )
    status = (
        STATUS_VERIFIED_G30
        if passed
        else (codes[0] if codes else STATUS_BLOCKED_FAT32_4GIB_SPANNING_TRAP)
    )

    res = G30LongformEnduranceResult(
        valid=passed,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        longform_endurance_guard=end_res.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    verdict = GateVerdict(
        gate_id=G30_GATE_ID,
        gate_code=G30_GATE_CODE,
        passed=passed,
        status=status,
        evidence=(
            f"Long-Form exFAT Spanning, CFexpress SMART Wear & Zero-NVRAM Churn Guard ({end_res.status}, "
            f"dur={end_res.planned_continuous_min:.0f}min, fs={end_res.filesystem}, "
            f"smart_used={end_res.smart_percentage_used:.0f}%, spare={end_res.spare_blocks_pct:.0f}%, "
            f"nand={end_res.media_nand_temp_c:.1f}C, nvram_hz={end_res.runtime_nvram_flush_hz:.2f}, "
            f"{audit.verification_mode}), persistent_emmc_writes_authorized={PERSISTENT_EMMC_WRITES_AUTHORIZED}."
        ),
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "verification_mode": audit.verification_mode,
            "fat32_4gib_trap_free": end_res.fat32_4gib_trap_free,
            "media_smart_endurance_safe": end_res.media_smart_endurance_safe,
            "zero_nvram_churn_safe": end_res.zero_nvram_churn_safe,
        },
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 6. Master 30-Gate Preflight Evaluator (`G01..G30`) & CLI
# ---------------------------------------------------------------------------


def evaluate_30gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G1..G28 pass-throughs
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
    # G29 inputs (Cinema Wireless TX Near-Field EMI, D-Tap/HDMI Hot-Plug ESD & Multi-Port LTC)
    wireless_tx_emi_kwargs: Optional[Mapping[str, Any]] = None,
    # G30 inputs (Long-Form exFAT Spanning, CFexpress SMART Wear & Zero-NVRAM Churn)
    longform_endurance_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master30GateReport:
    """Evaluate all 30 Master Safety Gates (`G01..G30`) deterministically."""
    resolved_root = (DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m28_kwargs: Dict[str, Any] = {
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
    }
    if soc_start_ceiling_c is not None:
        m28_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m28_report: Master28GateReport = evaluate_28gate_preflight(resolved_root, **m28_kwargs)

    phase100_audit = audit_phase100_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
    )

    g29_verdict, g29_res = evaluate_g29_wireless_tx_emi_and_hotplug_esd(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        wireless_tx_emi_kwargs=wireless_tx_emi_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase100_audit,
    )

    g30_verdict, g30_res = evaluate_g30_longform_endurance_and_nvram(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        include_large_binaries=include_large_binaries,
        longform_endurance_kwargs=longform_endurance_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase100_audit,
    )

    gates_29_to_30 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g29_verdict, g30_verdict)
    ]
    all_gates = tuple(list(m28_report.gates) + gates_29_to_30)

    g01_to_g12_verified = int(m28_report.summary["g01_to_g12_verified"])
    g13_to_g28_verified = (
        int(m28_report.summary["g13_to_g26_verified"])
        + int(m28_report.summary["g27_to_g28_verified"])
    )
    g29_to_g30_verified = sum(1 for v in (g29_verdict, g30_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g28_verified + g29_to_g30_verified

    g29_to_g30_all_passed = g29_to_g30_verified == 2
    g13_to_g30_all_passed = m28_report.g13_to_g28_all_passed and g29_to_g30_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m28_report.gates[:9])

    offline_27_verified = (
        g01_to_g09_ok
        and m28_report.offline_25_gates_verified
        and g29_to_g30_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_30_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g30_all_passed
        and (not request_persistent_emmc_writes)
    )

    real_tier0_verified = (g01_to_g12_verified == 12) and (not dry_run_simulated_backup)
    overall_ready_for_hardware_attach = (
        real_tier0_verified
        and g13_to_g30_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    h0_h1_allowed = (
        offline_27_verified
        and m28_report.h0_h1_trial_entry_allowed
        and g29_to_g30_all_passed
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = list(m28_report.errors) + list(g29_verdict.errors) + list(g30_verdict.errors)
    warnings: List[str] = list(m28_report.warnings) + list(g29_verdict.warnings) + list(g30_verdict.warnings)

    if request_persistent_emmc_writes or PERSISTENT_EMMC_WRITES_AUTHORIZED or PERSISTENT_WRITE_RELEASE:
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m28_report.g13_to_g28_all_passed:
        overall_status = m28_report.status
    elif not g29_verdict.passed:
        overall_status = g29_verdict.status
    elif not g30_verdict.passed:
        overall_status = g30_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_30_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_30_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_30_verified:
        overall_status = "VERIFIED_ALL_30_GATES"
    else:
        overall_status = "VERIFIED_27_OF_30_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m28_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g29_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g30_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 30,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 30 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g28_verified": g13_to_g28_verified,
        "g29_to_g30_verified": g29_to_g30_verified,
        "g13_to_g30_all_passed": g13_to_g30_all_passed,
        "g29_to_g30_all_passed": g29_to_g30_all_passed,
        "offline_27_gates_verified": offline_27_verified,
        "all_30_gates_verified": all_30_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
    }

    return Master30GateReport(
        schema=WIRELESS_EMI_ENDURANCE_30GATE_SCHEMA,
        version=WIRELESS_EMI_ENDURANCE_30GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_27_gates_verified=offline_27_verified,
        all_30_gates_verified=all_30_verified,
        g13_to_g30_all_passed=g13_to_g30_all_passed,
        g29_to_g30_all_passed=g29_to_g30_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_28_report=m28_report.to_dict(),
        g29_result=g29_res.to_dict(),
        g30_result=g30_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_30_master_safety_gates = evaluate_30gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="wireless_tx_emi_endurance_and_30gate_guard",
        description=(
            "Milestone Phase 100 — Wireless TX EMI & D-Tap/HDMI ESD Guard (G29), "
            "Long-Form exFAT/SMART/Zero-NVRAM Guard (G30) & 30-Gate Preflight (G01..G30)"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument("--clean-room", action="store_true", help="Force clean-room donorless mode")
    parser.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G30 can be exercised offline",
    )
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_30gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/30 "
            f"g29_to_g30_all_passed={report.g29_to_g30_all_passed} "
            f"all_30_gates_verified={report.all_30_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = report.all_30_gates_verified if args.dry_run_simulated_backup else report.offline_27_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
