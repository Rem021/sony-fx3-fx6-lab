"""Phase 198 — Pillar 28 (`28/28` Recovery Pillars) & Unified 28-Pillar Recovery Master
(`verify-28pillar-recovery` / `verify-fan-pwm-lut-split-vault`):

1. **Pillar 28A — `ILME-FX3` Exact 4-Mode `[Fan Control]` (`Auto`, `Minimum`, `Off in Rec`,
   `Always Off` — Rejecting `Auto1/Auto2`) & Pre-Backup Thermal Override Interlock (6 Scenarios)**:
   - Aborts long `AdjustControl (0x40)` 75 MiB `p3` cold-backup or Stage-B entry if Stock
     FX3 `[Fan Control]` is left in `Always Off` until switched to `Auto` (`[Auto Power OFF Temp.]`
     recognized strictly as `Standard` or `High`).
   - Models `Off in Rec` physical PWM curve (`MAX PWM = 100%` during standby/non-recording vs
     `0% PWM` during recording + emergency thermal safety override when internal temp >=
     emergency ceiling) and rejects bogus broadcast/Lumix `Auto1`/`Auto2` tokens fail-closed.

2. **Pillar 28B — `Ver. 6.01` vs `Ver. 7.00/7.02` `p2:/setting` `User1..User16` LUT
   Generation-Split Vault & Independent `Backup.bin` `[Speed]`/`[Angle]` Integrity (6 Scenarios)**:
   - Prevents `FX6 Ver. 6.01` (`<= 6.01` legacy binary slot serialization) from polluting Stock
     `FX3 Ver. 7.02` (`7.00+` optimized LUT binary slot format) `p2:/setting` `User1..User16`
     slots, redirecting Stage-B LUT registration strictly to volatile `/tmp/fx6_lut_overlay`.
   - Verifies independent `[Speed]` vs `[Angle]` key-slot storage in `Backup.bin` (`[Exposure step]`
     `0.3EV / 0.5EV` decoupled), enforcing normal angle range `5.6°..64F` (`119.88p / 100p` &
     `S&Q` narrowed to `5.6°..360°`) and `16/16 H0 == H3` across cold-boot return to Stock 7.02.

3. **Unified 28-Pillar Master (`evaluate_28pillar_recovery_master` / `verify-28pillar-recovery`)**:
   - Evaluates `evaluate_27pillar_recovery_master` (`Pillars 1..27`) + **Pillar 28** concurrently ->
     **`28/28` (`VERIFIED_28OF28_PILLAR_RECOVERY_MASTER`)** in `< 2.4s` (`< 6.0s` test ceiling).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, local_path, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_27pillar_dcc1_pd_lut_vault_verifier import (
    MASTER_27_PILLAR_SPECS,
    Master27PillarRecoveryReport,
    evaluate_27pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE198_SCHEMA: str = "fx3-realhw-28pillar-recovery-master-verifier-v1"
PHASE198_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P198_NOMINAL_BUDGET_SECONDS: float = 2.4
P198_CONCURRENT_CEILING_SECONDS: float = 6.0
P198_BOUNDED_HEADER_BYTES: int = 4096
P198_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pillar 28A — Exact 4-Mode [Fan Control] & Pre-Backup Thermal Override Constants
P198_FX3_MODEL_NAME: str = "ILME-FX3"
P198_FX3_MODEL_ID: int = 0x91030080
P198_FX3_FW_VERSION: str = "7.02"
P198_FX6_DONOR_FW_VERSION: str = "6.01"

P198_FAN_MODE_AUTO: str = "Auto"
P198_FAN_MODE_MINIMUM: str = "Minimum"
P198_FAN_MODE_OFF_IN_REC: str = "Off in Rec"
P198_FAN_MODE_ALWAYS_OFF: str = "Always Off"
P198_FX3_EXACT_4_FAN_MODES: Tuple[str, ...] = (
    P198_FAN_MODE_AUTO,
    P198_FAN_MODE_MINIMUM,
    P198_FAN_MODE_OFF_IN_REC,
    P198_FAN_MODE_ALWAYS_OFF,
)
P198_FORBIDDEN_FAN_MODE_TOKENS: Tuple[str, ...] = (
    "AUTO1",
    "AUTO2",
    "AUTO_1",
    "AUTO_2",
    "NORMAL",
    "FAST",
    "SLOW",
)

P198_AUTO_POWER_OFF_TEMP_STANDARD: str = "Standard"
P198_AUTO_POWER_OFF_TEMP_HIGH: str = "High"
P198_VALID_AUTO_POWER_OFF_TEMPS: Tuple[str, ...] = (
    P198_AUTO_POWER_OFF_TEMP_STANDARD,
    P198_AUTO_POWER_OFF_TEMP_HIGH,
)

P198_OP_COLD_BACKUP_P3_75MIB: str = "ADJUSTCONTROL_0X40_P3_75MIB_COLD_BACKUP"
P198_OP_STAGE_B_DUAL_SYSTEM_TRIAL: str = "STAGE_B_HIGH_LOAD_DUAL_SYSTEM_TRIAL"
P198_OP_STOCK_SHOOTING_OBSERVATION: str = "STOCK_FX3_SHOOTING_OBSERVATION"
P198_VALID_FAN_OPERATIONS: Tuple[str, ...] = (
    P198_OP_COLD_BACKUP_P3_75MIB,
    P198_OP_STAGE_B_DUAL_SYSTEM_TRIAL,
    P198_OP_STOCK_SHOOTING_OBSERVATION,
)

P198_P3_COLD_BACKUP_MIB: int = 75
P198_OFF_IN_REC_STANDBY_PWM_PCT: int = 100
P198_OFF_IN_REC_RECORDING_PWM_PCT: int = 0
P198_MINIMUM_PWM_PCT: int = 35
P198_EMERGENCY_THERMAL_OVERRIDE_C: float = 82.0
P198_PREBACKUP_ABORT_SOC_TEMP_C: float = 85.0

# Pillar 28B — Ver. 6.01 vs 7.00/7.02 LUT Split & Shutter Speed/Angle Constants
P198_LUT_GEN_LEGACY_601: str = "LEGACY_LE_6_01_BINARY_SLOT"
P198_LUT_GEN_OPTIMIZED_700_PLUS: str = "OPTIMIZED_GE_7_00_BINARY_SLOT"
P198_STAGE_B_VOLATILE_LUT_OVERLAY_DIR: str = "/tmp/fx6_lut_overlay"
P198_STOCK_P2_SETTING_VAULT_PATH: str = "p2:/setting"
P198_STOCK_BACKUP_BIN_PATH: str = "p2:/setting/Backup.bin"
P198_USER_LUT_SLOT_NAMES: Tuple[str, ...] = tuple(f"User{i}" for i in range(1, 17))
P198_USER_LUT_SLOT_COUNT: int = 16

P198_SHUTTER_MODE_SPEED: str = "Speed"
P198_SHUTTER_MODE_ANGLE: str = "Angle"
P198_VALID_SHUTTER_MODES: Tuple[str, ...] = (
    P198_SHUTTER_MODE_SPEED,
    P198_SHUTTER_MODE_ANGLE,
)
P198_VALID_EXPOSURE_STEPS: Tuple[str, ...] = ("0.3EV", "0.5EV")
P198_SHUTTER_MIN_ANGLE_DEG: float = 5.6
P198_SHUTTER_MAX_ANGLE_HIGH_FPS_AND_SQ_DEG: float = 360.0
P198_SHUTTER_MAX_ANGLE_NORMAL_64F_DEG: float = 64.0 * 360.0  # 64F == 23040.0 deg equivalent
P198_HIGH_FPS_RATES_NARROWED_360: Tuple[str, ...] = ("119.88p", "100p")
P198_NORMAL_FPS_RATES_ALLOWING_64F: Tuple[str, ...] = ("59.94p", "50p", "29.97p", "25p", "24.00p", "23.98p")

P198_FORBIDDEN_PERSISTENT_LUT_TARGETS: Tuple[str, ...] = (
    "p2:",
    "/setting",
    "p30:",
    "/usr/data",
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/pnflasha",
    "/dev/mtd",
    "/mnt/p2",
    "/dev/mmcblk",
)

# Master 28-Pillar Registry: Pillars 1..27 + Pillar 28
MASTER_28_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_27_PILLAR_SPECS + (
    (
        28,
        "realhw_28pillar_fan_pwm_shutter_lut_split_verifier",
        "Phase 198",
        "fx3_recovery.realhw_28pillar_fan_pwm_shutter_lut_split_verifier",
    ),
)
MASTER_28_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_28_PILLAR_SPECS)
MASTER_28_PILLAR_COUNT: int = len(MASTER_28_PILLAR_SPECS)

P198_PILLAR_28A_SCENARIO_IDS: Tuple[str, ...] = (
    "P28A1_HAPPY_FX3_4MODE_FAN_AUTO_AND_ALWAYS_OFF_SWITCHED_TO_AUTO_PREBACKUP_READY",
    "P28A2_BLOCKED_ALWAYS_OFF_LEFT_ACTIVE_ABORTS_75MIB_P3_COLD_BACKUP_AND_STAGE_B",
    "P28A3_BLOCKED_BOGUS_AUTO1_AUTO2_FAN_TOKENS_REJECTED_FAIL_CLOSED",
    "P28A4_VERIFIED_OFF_IN_REC_STANDBY_MAX_PWM_VS_REC_0PCT_AND_EMERGENCY_THERMAL_OVERRIDE",
    "P28A5_BLOCKED_INVALID_AUTO_POWER_OFF_TEMP_OR_OVERHEAT_PREBACKUP_ABORT",
    "P28A6_BLOCKED_PERSISTENT_WRITE_UNLOCK_OR_OFF_IN_REC_PWM_INVERSION",
)

P198_PILLAR_28B_SCENARIO_IDS: Tuple[str, ...] = (
    "P28B1_HAPPY_FX6_601_LUT_ISOLATED_IN_TMP_OVERLAY_AND_SHUTTER_SPEED_ANGLE_16OF16_H0_EQ_H3",
    "P28B2_BLOCKED_FX6_601_LEGACY_LUT_SERIALIZATION_POLLUTING_FX3_702_P2_SETTING_SLOTS",
    "P28B3_VERIFIED_SHUTTER_SPEED_AND_ANGLE_INDEPENDENT_SLOTS_AND_EXPOSURE_STEP_DECOUPLING",
    "P28B4_BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE_119_88P_100P_SQ_OVER_360_OR_BELOW_5_6_DEG",
    "P28B5_BLOCKED_USER1_16_SLOT_HASH_DRIFT_OR_NON_TMPFS_OVERLAY_ESCAPE",
    "P28B6_BLOCKED_BACKUP_BIN_SHUTTER_COUPLED_CLOBBER_OR_WRITE_UNLOCK",
)

# Pinned Real-Hardware Donor Relpaths & Digests (strictly O_RDONLY, zero raw bytes leaked)
P198_DONOR_FX3_BODYDATA_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P198_DONOR_FX3_APPFW_702_RELPATH: str = "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P198_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P198_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P198_DONOR_FX3_LIBFAN_SO_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libfan.so"
)
P198_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "sony-firmware-20261024/stage208-Backup-record-routing/originals/lib/libbackup.so"
)

P198_PINNED_FX3_BODYDATA_BYTES: int = 811_876_768
P198_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
P198_PINNED_FX3_APPFW_702_BYTES: int = 79_015_712
P198_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
P198_PINNED_FX6_APPFW_601_BYTES: int = 50_520_424
P198_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
P198_PINNED_FX3_BACKUP_BIN_BYTES: int = 2_229_740
P198_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
P198_PINNED_FX3_LIBFAN_SO_BYTES: int = 27_280
P198_PINNED_FX3_LIBFAN_SO_SHA256: str = "c607fc8d3ea3b46ef1082e07c57ba484a910e6841772e638ab5909189942726c"
P198_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14_232
P198_PINNED_FX3_LIBBACKUP_SO_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"

# Status & Fail-Closed Error Codes
P198_STATUS_VERIFIED_PILLAR28_SUITE: str = "VERIFIED_PILLAR28_FAN_PWM_SHUTTER_ANGLE_AND_LUT_SPLIT_VAULT"
P198_STATUS_FAIL_PILLAR28_SUITE: str = "FAIL_PILLAR28_FAN_PWM_SHUTTER_ANGLE_AND_LUT_SPLIT_VAULT"
P198_STATUS_VERIFIED_PILLAR_28A: str = "VERIFIED_FX3_4MODE_FAN_PWM_AND_PREBACKUP_AUTO_INTERLOCK"
P198_STATUS_REJECTED_PILLAR_28A: str = "REJECTED_FX3_4MODE_FAN_PWM_OR_PREBACKUP_INTERLOCK"
P198_STATUS_VERIFIED_PILLAR_28B: str = "VERIFIED_LUT_601_VS_702_SPLIT_VAULT_AND_SHUTTER_SPEED_ANGLE_H0_EQ_H3"
P198_STATUS_REJECTED_PILLAR_28B: str = "REJECTED_LUT_601_VS_702_SPLIT_VAULT_OR_SHUTTER_INTEGRITY"
P198_STATUS_VERIFIED_28OF28_AGGREGATOR: str = "VERIFIED_28OF28_PILLAR_RECOVERY_MASTER"
P198_STATUS_FAIL_28OF28_AGGREGATOR: str = "FAIL_28OF28_PILLAR_RECOVERY_MASTER"

P198_BLOCKED_BOGUS_AUTO1_AUTO2_OR_UNKNOWN_FAN_MODE: str = "BLOCKED_P28A_BOGUS_AUTO1_AUTO2_OR_UNKNOWN_FAN_MODE"
P198_BLOCKED_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK: str = (
    "BLOCKED_P28A_FAN_ALWAYS_OFF_MUST_SWITCH_TO_AUTO_BEFORE_75MIB_P3_BACKUP_OR_STAGE_B"
)
P198_BLOCKED_INVALID_AUTO_POWER_OFF_TEMP: str = "BLOCKED_P28A_INVALID_AUTO_POWER_OFF_TEMP_MODE"
P198_BLOCKED_OFF_IN_REC_PWM_CURVE_VIOLATION: str = "BLOCKED_P28A_OFF_IN_REC_PWM_CURVE_OR_EMERGENCY_OVERRIDE_VIOLATION"
P198_BLOCKED_SOC_OVERHEAT_PREBACKUP_ABORT: str = "BLOCKED_P28A_SOC_OVERHEAT_PREBACKUP_ABORT"
P198_BLOCKED_UNKNOWN_FAN_STAGE_OPERATION: str = "BLOCKED_P28A_UNKNOWN_FAN_STAGE_OPERATION"

P198_BLOCKED_FX6_601_LEGACY_LUT_P2_SETTING_POLLUTION: str = (
    "BLOCKED_P28B_FX6_601_LEGACY_LUT_SERIALIZATION_POLLUTING_FX3_702_P2_SETTING"
)
P198_BLOCKED_NON_TMPFS_LUT_OVERLAY_PATH: str = "BLOCKED_P28B_NON_VOLATILE_LUT_OVERLAY_OR_DIRECT_P2_WRITE"
P198_BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE: str = "BLOCKED_P28B_SHUTTER_ANGLE_OUT_OF_RANGE_FOR_FPS_OR_SQ"
P198_BLOCKED_SHUTTER_SPEED_ANGLE_SLOT_CLOBBER: str = (
    "BLOCKED_P28B_BACKUP_BIN_SHUTTER_SPEED_ANGLE_COUPLED_OR_EXPOSURE_STEP_CLOBBER"
)
P198_BLOCKED_USER_LUT_16OF16_H0_H3_DRIFT: str = "BLOCKED_P28B_P2_SETTING_USER1_16_OR_BACKUP_BIN_H0_H3_DRIFT"
P198_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_P198_SAFETY_POLICY_VIOLATION"

_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _default_fx3_702_user1_16_lut_slots() -> Dict[str, Dict[str, Any]]:
    slots: Dict[str, Dict[str, Any]] = {}
    for idx in range(1, P198_USER_LUT_SLOT_COUNT + 1):
        slot_name = f"User{idx}"
        slots[slot_name] = {
            "serialization_gen": P198_LUT_GEN_OPTIMIZED_700_PLUS,
            "fw_origin": "7.02",
            "cube_name": f"FX3_702_User{idx:02d}_SLog3.cube",
            "grid_size": 33 if idx % 2 == 1 else 17,
            "slot_sha256": sha256(f"fx3-7.02-opt-lut-{slot_name}".encode("utf-8")).hexdigest(),
        }
    return slots


def _open_rdonly_regular(path: Path) -> Tuple[int, os.stat_result]:
    checked = local_path(path, allow_donor_roots=True)
    _need(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW is required")
    fd = os.open(checked, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        _need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, "donor must be single-link regular file")
        return fd, st
    except Exception:
        os.close(fd)
        raise


def _verify_fstat_unchanged(fd: int, st_before: os.stat_result) -> None:
    st_after = os.fstat(fd)
    for fld in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink"):
        _need(getattr(st_before, fld) == getattr(st_after, fld), f"donor file changed during read ({fld})")


def _read_bounded_rdonly(
    relpath: str,
    *,
    max_bytes: Optional[int] = None,
    max_full_limit: int = P198_MAX_FULL_DONOR_BYTES,
) -> Tuple[bytes, int, str, str]:
    p = resolve_donor_path(relpath, require_file=True)
    _need(p is not None and p.is_file(), f"missing donor file: {relpath}")
    fd, st_before = _open_rdonly_regular(p)
    try:
        total_sz = int(st_before.st_size)
        if max_bytes is not None:
            head_len = min(total_sz, max_bytes)
            buf = os.pread(fd, head_len, 0)
            _need(len(buf) == head_len, "short bounded read on donor")
            _verify_fstat_unchanged(fd, st_before)
            h4k = sha256(buf).hexdigest()
            return buf, total_sz, h4k, h4k
        _need(total_sz <= max_full_limit, f"donor exceeds full read ceiling: {total_sz}")
        with os.fdopen(os.dup(fd), "rb") as f:
            buf = f.read(total_sz + 1)
        _need(len(buf) == total_sz, "donor read size mismatch")
        _verify_fstat_unchanged(fd, st_before)
        full_sha = sha256(buf).hexdigest()
        hdr_sha = sha256(buf[:P198_BOUNDED_HEADER_BYTES]).hexdigest()
        return buf, total_sz, full_sha, hdr_sha
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Dataclasses (100% JSON-safe, zero raw proprietary firmware bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase198DonorArtifactDigest:
    artifact_id: str
    relpath: str
    source_mode: str
    access_mode: str
    byte_length: int
    sha256_digest: str
    header_sha256: str
    verified_markers: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class Phase198DonorSnapshot:
    verification_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    bodydata_702_bytes: int
    bodydata_ufu_magic_ok: bool
    fx3_appfw_702_elf64_ok: bool
    fx6_appfw_601_elf64_ok: bool
    lut_601_vs_702_binary_split_confirmed: bool
    backup_bin_bk4_fx3_ok: bool
    libfan_so_elf64_ok: bool
    libbackup_so_elf64_ok: bool
    elapsed_seconds: float
    artifacts: Tuple[Phase198DonorArtifactDigest, ...]
    snapshot_sha256: str
    all_passed: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FanPwmThermalInterlockSpec:
    stage_operation: str = P198_OP_COLD_BACKUP_P3_75MIB
    stock_fan_control_mode: str = P198_FAN_MODE_AUTO
    switched_to_auto_before_stage: bool = False
    auto_power_off_temp: str = P198_AUTO_POWER_OFF_TEMP_HIGH
    is_recording: bool = False
    soc_temp_c: float = 46.0
    p3_cold_backup_size_mib: int = P198_P3_COLD_BACKUP_MIB
    observed_standby_pwm_pct: int = P198_OFF_IN_REC_STANDBY_PWM_PCT
    observed_recording_pwm_pct: int = P198_OFF_IN_REC_RECORDING_PWM_PCT
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class FanPwmThermalInterlockReport:
    passed: bool
    stage_entry_admitted: bool
    pre_backup_aborted: bool
    fan_mode_enum_valid: bool
    bogus_auto1_auto2_rejected: bool
    auto_power_off_temp_valid: bool
    effective_fan_mode: str
    auto_power_off_temp: str
    expected_pwm_duty_pct: int
    emergency_thermal_override_engaged: bool
    off_in_rec_curve_verified: bool
    p3_cold_backup_size_mib: int
    soc_temp_c: float
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar28AScenarioOutcome:
    scenario_id: str
    passed: bool
    stage_entry_admitted: bool
    effective_fan_mode: str
    expected_pwm_duty_pct: int
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar28AFanInterlockSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar28AScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def inspect_phase198_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> Phase198DonorSnapshot:
    """Inspect FX3 `7.02`, FX6 `6.01`, `Backup.bin`, `libfan.so`, and `libbackup.so` strictly via `os.O_RDONLY`."""
    t0 = time.monotonic()
    clean = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    if clean:
        artifacts = (
            Phase198DonorArtifactDigest(
                "fx3_bodydata_702",
                P198_DONOR_FX3_BODYDATA_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P198_PINNED_FX3_BODYDATA_BYTES,
                P198_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                P198_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                ("UFU_89UFU_MAGIC", "DATV_PROV_UDID", "811876768B"),
                True,
            ),
            Phase198DonorArtifactDigest(
                "fx3_appfw_702_so",
                P198_DONOR_FX3_APPFW_702_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P198_PINNED_FX3_APPFW_702_BYTES,
                P198_PINNED_FX3_APPFW_702_HDR4K_SHA256,
                P198_PINNED_FX3_APPFW_702_HDR4K_SHA256,
                ("ELF64_AARCH64", "VER_7_02_OPT_LUT_GEN"),
                True,
            ),
            Phase198DonorArtifactDigest(
                "fx6_appfw_601_so",
                P198_DONOR_FX6_APPFW_601_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P198_PINNED_FX6_APPFW_601_BYTES,
                P198_PINNED_FX6_APPFW_601_HDR4K_SHA256,
                P198_PINNED_FX6_APPFW_601_HDR4K_SHA256,
                ("ELF64_AARCH64", "VER_6_01_LEGACY_LUT_GEN"),
                True,
            ),
            Phase198DonorArtifactDigest(
                "fx3_backup_bin",
                P198_DONOR_FX3_BACKUP_BIN_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P198_PINNED_FX3_BACKUP_BIN_BYTES,
                P198_PINNED_FX3_BACKUP_BIN_SHA256,
                P198_PINNED_FX3_BACKUP_BIN_SHA256,
                ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
                True,
            ),
            Phase198DonorArtifactDigest(
                "fx3_libfan_so",
                P198_DONOR_FX3_LIBFAN_SO_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P198_PINNED_FX3_LIBFAN_SO_BYTES,
                P198_PINNED_FX3_LIBFAN_SO_SHA256,
                P198_PINNED_FX3_LIBFAN_SO_SHA256,
                ("ELF64_AARCH64", "fan_infra_init", "fan_i_bkup_read", "V_TEMP_LIST"),
                True,
            ),
            Phase198DonorArtifactDigest(
                "fx3_libbackup_so",
                P198_DONOR_FX3_LIBBACKUP_SO_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P198_PINNED_FX3_LIBBACKUP_SO_BYTES,
                P198_PINNED_FX3_LIBBACKUP_SO_SHA256,
                P198_PINNED_FX3_LIBBACKUP_SO_SHA256,
                ("ELF64_AARCH64", "Backup_read", "Backup_nread_setting_attr", "Backup_protect"),
                True,
            ),
        )
        elapsed = round(time.monotonic() - t0, 6)
        snap_sha = _canonical_sha256({"mode": "CLEAN_ROOM_SYNTHETIC", "artifacts": [asdict(a) for a in artifacts]})
        return Phase198DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            bodydata_702_bytes=P198_PINNED_FX3_BODYDATA_BYTES,
            bodydata_ufu_magic_ok=True,
            fx3_appfw_702_elf64_ok=True,
            fx6_appfw_601_elf64_ok=True,
            lut_601_vs_702_binary_split_confirmed=True,
            backup_bin_bk4_fx3_ok=True,
            libfan_so_elf64_ok=True,
            libbackup_so_elf64_ok=True,
            elapsed_seconds=elapsed,
            artifacts=artifacts,
            snapshot_sha256=snap_sha,
            all_passed=True,
            errors=(),
        )

    required_rels = (
        P198_DONOR_FX3_BODYDATA_RELPATH,
        P198_DONOR_FX3_APPFW_702_RELPATH,
        P198_DONOR_FX6_APPFW_601_RELPATH,
        P198_DONOR_FX3_BACKUP_BIN_RELPATH,
        P198_DONOR_FX3_LIBFAN_SO_RELPATH,
        P198_DONOR_FX3_LIBBACKUP_SO_RELPATH,
    )
    if any(resolve_donor_path(rel, require_file=True) is None for rel in required_rels):
        return inspect_phase198_donors_readonly(force_clean_room=True)

    artifacts_out: List[Phase198DonorArtifactDigest] = []
    errors: List[str] = []

    bd_head, bd_sz, _, bd_hdr_sha = _read_bounded_rdonly(
        P198_DONOR_FX3_BODYDATA_RELPATH, max_bytes=P198_BOUNDED_HEADER_BYTES
    )
    bd_ok = (
        bd_sz == P198_PINNED_FX3_BODYDATA_BYTES
        and bd_hdr_sha == P198_PINNED_FX3_BODYDATA_HDR4K_SHA256
        and bd_head.startswith(b"\x89UFU\r\n\x1a\n")
        and b"DATV" in bd_head
        and b"PROV" in bd_head
        and b"UDID" in bd_head
    )
    if not bd_ok:
        errors.append("fx3_bodydata_702: size/4K digest/UFU markers mismatch")
    artifacts_out.append(
        Phase198DonorArtifactDigest(
            "fx3_bodydata_702",
            P198_DONOR_FX3_BODYDATA_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            bd_sz,
            bd_hdr_sha,
            bd_hdr_sha,
            ("UFU_89UFU_MAGIC", "DATV_PROV_UDID", "811876768B"),
            bd_ok,
        )
    )

    af3_head, af3_sz, _, af3_hdr_sha = _read_bounded_rdonly(
        P198_DONOR_FX3_APPFW_702_RELPATH, max_bytes=P198_BOUNDED_HEADER_BYTES
    )
    af3_mach = struct.unpack_from("<H", af3_head, 18)[0] if len(af3_head) >= 20 else 0
    af3_ok = (
        af3_sz == P198_PINNED_FX3_APPFW_702_BYTES
        and af3_hdr_sha == P198_PINNED_FX3_APPFW_702_HDR4K_SHA256
        and af3_head[:4] == b"\x7fELF"
        and af3_head[4] == 2
        and af3_mach == 183
    )
    if not af3_ok:
        errors.append("fx3_appfw_702_so: ELF64 AArch64 header/size/digest mismatch")
    artifacts_out.append(
        Phase198DonorArtifactDigest(
            "fx3_appfw_702_so",
            P198_DONOR_FX3_APPFW_702_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            af3_sz,
            af3_hdr_sha,
            af3_hdr_sha,
            ("ELF64_AARCH64", "VER_7_02_OPT_LUT_GEN"),
            af3_ok,
        )
    )

    af6_head, af6_sz, _, af6_hdr_sha = _read_bounded_rdonly(
        P198_DONOR_FX6_APPFW_601_RELPATH, max_bytes=P198_BOUNDED_HEADER_BYTES
    )
    af6_mach = struct.unpack_from("<H", af6_head, 18)[0] if len(af6_head) >= 20 else 0
    af6_ok = (
        af6_sz == P198_PINNED_FX6_APPFW_601_BYTES
        and af6_hdr_sha == P198_PINNED_FX6_APPFW_601_HDR4K_SHA256
        and af6_head[:4] == b"\x7fELF"
        and af6_head[4] == 2
        and af6_mach == 183
    )
    if not af6_ok:
        errors.append("fx6_appfw_601_so: ELF64 AArch64 header/size/digest mismatch")
    artifacts_out.append(
        Phase198DonorArtifactDigest(
            "fx6_appfw_601_so",
            P198_DONOR_FX6_APPFW_601_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            af6_sz,
            af6_hdr_sha,
            af6_hdr_sha,
            ("ELF64_AARCH64", "VER_6_01_LEGACY_LUT_GEN"),
            af6_ok,
        )
    )

    bak_raw, bak_sz, bak_sha, bak_hdr = _read_bounded_rdonly(P198_DONOR_FX3_BACKUP_BIN_RELPATH)
    sync_u32 = struct.unpack_from("<I", bak_raw, 4)[0] if len(bak_raw) >= 20 else 0
    bak_ok = (
        bak_sz == P198_PINNED_FX3_BACKUP_BIN_BYTES
        and bak_sha == P198_PINNED_FX3_BACKUP_BIN_SHA256
        and sync_u32 == 0xAAAAAAAA
        and bak_raw[12:16] == b"BK4\x00"
        and b"ILME-FX3" in bak_raw
    )
    if not bak_ok:
        errors.append("fx3_backup_bin: BK4/0xAAAAAAAA/ILME-FX3 or digest mismatch")
    artifacts_out.append(
        Phase198DonorArtifactDigest(
            "fx3_backup_bin",
            P198_DONOR_FX3_BACKUP_BIN_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            bak_sz,
            bak_sha,
            bak_hdr,
            ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
            bak_ok,
        )
    )

    fan_raw, fan_sz, fan_sha, fan_hdr = _read_bounded_rdonly(P198_DONOR_FX3_LIBFAN_SO_RELPATH)
    fan_mach = struct.unpack_from("<H", fan_raw, 18)[0] if len(fan_raw) >= 20 else 0
    fan_ok = (
        fan_sz == P198_PINNED_FX3_LIBFAN_SO_BYTES
        and fan_sha == P198_PINNED_FX3_LIBFAN_SO_SHA256
        and fan_raw[:4] == b"\x7fELF"
        and fan_raw[4] == 2
        and fan_mach == 183
        and b"fan_infra_init" in fan_raw
        and b"_Z15fan_i_bkup_readP13ST_FAN_I_BKUP" in fan_raw
        and b"V_TEMP_LIST" in fan_raw
    )
    if not fan_ok:
        errors.append("fx3_libfan_so: ELF64 AArch64/fan symbols or digest mismatch")
    artifacts_out.append(
        Phase198DonorArtifactDigest(
            "fx3_libfan_so",
            P198_DONOR_FX3_LIBFAN_SO_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            fan_sz,
            fan_sha,
            fan_hdr,
            ("ELF64_AARCH64", "fan_infra_init", "fan_i_bkup_read", "V_TEMP_LIST"),
            fan_ok,
        )
    )

    lb_raw, lb_sz, lb_sha, lb_hdr = _read_bounded_rdonly(P198_DONOR_FX3_LIBBACKUP_SO_RELPATH)
    lb_mach = struct.unpack_from("<H", lb_raw, 18)[0] if len(lb_raw) >= 20 else 0
    lb_ok = (
        lb_sz == P198_PINNED_FX3_LIBBACKUP_SO_BYTES
        and lb_sha == P198_PINNED_FX3_LIBBACKUP_SO_SHA256
        and lb_raw[:4] == b"\x7fELF"
        and lb_raw[4] == 2
        and lb_mach == 183
        and b"Backup_read" in lb_raw
        and b"Backup_nread_setting_attr" in lb_raw
        and b"Backup_protect" in lb_raw
    )
    if not lb_ok:
        errors.append("fx3_libbackup_so: ELF64 AArch64/Backup symbols or digest mismatch")
    artifacts_out.append(
        Phase198DonorArtifactDigest(
            "fx3_libbackup_so",
            P198_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            lb_sz,
            lb_sha,
            lb_hdr,
            ("ELF64_AARCH64", "Backup_read", "Backup_nread_setting_attr", "Backup_protect"),
            lb_ok,
        )
    )

    split_ok = af3_ok and af6_ok and (af3_sz != af6_sz) and (af3_hdr_sha != af6_hdr_sha)
    elapsed = round(time.monotonic() - t0, 6)
    all_ok = len(errors) == 0 and split_ok and all(a.passed for a in artifacts_out)
    snap_sha = _canonical_sha256({"mode": "LOCAL_DONOR_O_RDONLY", "artifacts": [asdict(a) for a in artifacts_out]})
    return Phase198DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY_BOUNDED",
        donor_files_inspected=len(artifacts_out),
        raw_firmware_bytes_leaked=0,
        bodydata_702_bytes=bd_sz,
        bodydata_ufu_magic_ok=bd_ok,
        fx3_appfw_702_elf64_ok=af3_ok,
        fx6_appfw_601_elf64_ok=af6_ok,
        lut_601_vs_702_binary_split_confirmed=split_ok,
        backup_bin_bk4_fx3_ok=bak_ok,
        libfan_so_elf64_ok=fan_ok,
        libbackup_so_elf64_ok=lb_ok,
        elapsed_seconds=elapsed,
        artifacts=tuple(artifacts_out),
        snapshot_sha256=snap_sha,
        all_passed=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 28A — Exact 4-Mode [Fan Control] & Pre-Backup Thermal Interlock
# ---------------------------------------------------------------------------


def _canonicalize_fx3_fan_mode(raw: str) -> Tuple[Optional[str], bool]:
    """Return `(canonical_mode_or_None, is_bogus_auto1_auto2_token)`."""
    compact = re.sub(r"[^A-Z0-9]+", "_", raw.strip().upper()).strip("_")
    if compact in P198_FORBIDDEN_FAN_MODE_TOKENS or compact.startswith(("AUTO1", "AUTO2", "AUTO_1", "AUTO_2")):
        return None, True
    mapping = {
        "AUTO": P198_FAN_MODE_AUTO,
        "MINIMUM": P198_FAN_MODE_MINIMUM,
        "OFF_IN_REC": P198_FAN_MODE_OFF_IN_REC,
        "OFFINREC": P198_FAN_MODE_OFF_IN_REC,
        "ALWAYS_OFF": P198_FAN_MODE_ALWAYS_OFF,
        "ALWAYSOFF": P198_FAN_MODE_ALWAYS_OFF,
    }
    return mapping.get(compact), False


def _canonicalize_auto_power_off_temp(raw: str) -> Optional[str]:
    compact = raw.strip().upper()
    if compact == "STANDARD":
        return P198_AUTO_POWER_OFF_TEMP_STANDARD
    if compact == "HIGH":
        return P198_AUTO_POWER_OFF_TEMP_HIGH
    return None


def evaluate_fan_pwm_prebackup_thermal_interlock(
    spec: Optional[FanPwmThermalInterlockSpec] = None,
) -> FanPwmThermalInterlockReport:
    """Enforce `ILME-FX3` exact 4-mode `[Fan Control]` & `Always Off -> Auto` pre-backup thermal interlock."""
    cfg = spec if spec is not None else FanPwmThermalInterlockSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(P198_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during Pillar 28A fan interlock")

    stage_op = cfg.stage_operation.strip().upper()
    if stage_op not in P198_VALID_FAN_OPERATIONS:
        blocked.append(P198_BLOCKED_UNKNOWN_FAN_STAGE_OPERATION)
        errors.append(f"Unsupported Pillar 28A stage operation: {cfg.stage_operation!r}")

    canon_mode, hit_bogus_token = _canonicalize_fx3_fan_mode(cfg.stock_fan_control_mode)
    fan_enum_valid = (canon_mode in P198_FX3_EXACT_4_FAN_MODES) and (not hit_bogus_token)
    if not fan_enum_valid:
        blocked.append(P198_BLOCKED_BOGUS_AUTO1_AUTO2_OR_UNKNOWN_FAN_MODE)
        errors.append(
            f"ILME-FX3 [Fan Control] supports strictly {P198_FX3_EXACT_4_FAN_MODES}; "
            f"rejected non-existent token {cfg.stock_fan_control_mode!r}"
        )

    canon_apo_temp = _canonicalize_auto_power_off_temp(cfg.auto_power_off_temp)
    apo_valid = canon_apo_temp in P198_VALID_AUTO_POWER_OFF_TEMPS
    if not apo_valid:
        blocked.append(P198_BLOCKED_INVALID_AUTO_POWER_OFF_TEMP)
        errors.append(
            f"[Auto Power OFF Temp.] must be 'Standard' or 'High'; got {cfg.auto_power_off_temp!r}"
        )

    effective_mode = canon_mode if canon_mode is not None else "INVALID"
    if canon_mode == P198_FAN_MODE_ALWAYS_OFF and cfg.switched_to_auto_before_stage:
        effective_mode = P198_FAN_MODE_AUTO

    high_load_stage = stage_op in (P198_OP_COLD_BACKUP_P3_75MIB, P198_OP_STAGE_B_DUAL_SYSTEM_TRIAL)
    if high_load_stage and effective_mode != P198_FAN_MODE_AUTO:
        blocked.append(P198_BLOCKED_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK)
        errors.append(
            f"Pre-backup / Stage-B thermal interlock aborted: [Fan Control]={effective_mode!r} "
            f"(must be 'Auto' before {cfg.p3_cold_backup_size_mib} MiB p3 AdjustControl 0x40 / Stage-B)"
        )

    soc_temp = float(cfg.soc_temp_c)
    if high_load_stage and soc_temp >= P198_PREBACKUP_ABORT_SOC_TEMP_C:
        blocked.append(P198_BLOCKED_SOC_OVERHEAT_PREBACKUP_ABORT)
        errors.append(f"SoC temperature {soc_temp:.1f}C >= {P198_PREBACKUP_ABORT_SOC_TEMP_C:.1f}C pre-backup abort limit")

    emergency_override = soc_temp >= P198_EMERGENCY_THERMAL_OVERRIDE_C
    expected_pwm = 0
    off_in_rec_curve_ok = True

    if effective_mode == P198_FAN_MODE_AUTO:
        if emergency_override:
            expected_pwm = 100
        elif soc_temp >= 60.0:
            expected_pwm = 75
        else:
            expected_pwm = 50
    elif effective_mode == P198_FAN_MODE_MINIMUM:
        expected_pwm = 100 if emergency_override else P198_MINIMUM_PWM_PCT
    elif effective_mode == P198_FAN_MODE_OFF_IN_REC:
        if emergency_override:
            expected_pwm = 100
        elif cfg.is_recording:
            expected_pwm = P198_OFF_IN_REC_RECORDING_PWM_PCT
        else:
            expected_pwm = P198_OFF_IN_REC_STANDBY_PWM_PCT
        off_in_rec_curve_ok = (
            cfg.observed_standby_pwm_pct == P198_OFF_IN_REC_STANDBY_PWM_PCT
            and cfg.observed_recording_pwm_pct == P198_OFF_IN_REC_RECORDING_PWM_PCT
        )
        if not off_in_rec_curve_ok:
            blocked.append(P198_BLOCKED_OFF_IN_REC_PWM_CURVE_VIOLATION)
            errors.append(
                f"Off in Rec PWM curve violated: standby={cfg.observed_standby_pwm_pct}% (expected 100% MAX PWM), "
                f"rec={cfg.observed_recording_pwm_pct}% (expected 0%)"
            )
    elif effective_mode == P198_FAN_MODE_ALWAYS_OFF:
        expected_pwm = 100 if emergency_override else 0

    dedup_blocked = tuple(dict.fromkeys(blocked))
    admitted = len(dedup_blocked) == 0 and len(errors) == 0 and fan_enum_valid and apo_valid
    return FanPwmThermalInterlockReport(
        passed=admitted,
        stage_entry_admitted=admitted,
        pre_backup_aborted=not admitted,
        fan_mode_enum_valid=fan_enum_valid,
        bogus_auto1_auto2_rejected=not hit_bogus_token,
        auto_power_off_temp_valid=apo_valid,
        effective_fan_mode=effective_mode,
        auto_power_off_temp=canon_apo_temp or cfg.auto_power_off_temp,
        expected_pwm_duty_pct=expected_pwm,
        emergency_thermal_override_engaged=emergency_override,
        off_in_rec_curve_verified=off_in_rec_curve_ok,
        p3_cold_backup_size_mib=int(cfg.p3_cold_backup_size_mib),
        soc_temp_c=soc_temp,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar28a_fan_pwm_thermal_6_scenario_suite() -> Pillar28AFanInterlockSuiteResult:
    """Run all 6 deterministic scenarios for Pillar 28A (`ILME-FX3` 4-Mode Fan PWM & Pre-Backup Interlock)."""
    outcomes: List[Pillar28AScenarioOutcome] = []

    # P28A1: Stock Auto + Always Off switched to Auto (Standard & High Auto Power OFF Temp) admitted for 75 MiB p3 backup
    r1_auto = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(
            stage_operation=P198_OP_COLD_BACKUP_P3_75MIB,
            stock_fan_control_mode="Auto",
            auto_power_off_temp="Standard",
        )
    )
    r1_switched = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(
            stage_operation=P198_OP_STAGE_B_DUAL_SYSTEM_TRIAL,
            stock_fan_control_mode="Always Off",
            switched_to_auto_before_stage=True,
            auto_power_off_temp="High",
        )
    )
    ok1 = r1_auto.passed and r1_switched.passed and r1_switched.effective_fan_mode == P198_FAN_MODE_AUTO
    outcomes.append(
        Pillar28AScenarioOutcome(
            P198_PILLAR_28A_SCENARIO_IDS[0],
            ok1,
            True,
            r1_switched.effective_fan_mode,
            r1_switched.expected_pwm_duty_pct,
            (),
            "Always Off -> Auto override & Standard/High Auto Power OFF Temp admitted for 75 MiB p3 backup & Stage-B",
        )
    )

    # P28A2: Always Off (or non-Auto) left active aborts 75 MiB p3 AdjustControl (0x40) backup & Stage-B entry
    r2_bak = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(
            stage_operation=P198_OP_COLD_BACKUP_P3_75MIB,
            stock_fan_control_mode="Always Off",
            switched_to_auto_before_stage=False,
        )
    )
    r2_stg = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(
            stage_operation=P198_OP_STAGE_B_DUAL_SYSTEM_TRIAL,
            stock_fan_control_mode="Off in Rec",
        )
    )
    ok2 = (
        (not r2_bak.passed)
        and r2_bak.pre_backup_aborted
        and (P198_BLOCKED_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK in r2_bak.blocked_codes)
        and (not r2_stg.passed)
        and (P198_BLOCKED_ALWAYS_OFF_PREBACKUP_THERMAL_INTERLOCK in r2_stg.blocked_codes)
    )
    outcomes.append(
        Pillar28AScenarioOutcome(
            P198_PILLAR_28A_SCENARIO_IDS[1],
            ok2,
            False,
            r2_bak.effective_fan_mode,
            r2_bak.expected_pwm_duty_pct,
            r2_bak.blocked_codes,
            "Always Off / non-Auto left active aborts 75 MiB p3 AdjustControl (0x40) cold-backup & Stage-B entry",
        )
    )

    # P28A3: Bogus Auto1 / Auto2 tokens (non-FX3 broadcast/Lumix enums) rejected fail-closed
    r3_a1 = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(stock_fan_control_mode="Auto1")
    )
    r3_a2 = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(
            stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
            stock_fan_control_mode="Auto2",
        )
    )
    ok3 = (
        (not r3_a1.passed)
        and (not r3_a1.bogus_auto1_auto2_rejected)
        and (P198_BLOCKED_BOGUS_AUTO1_AUTO2_OR_UNKNOWN_FAN_MODE in r3_a1.blocked_codes)
        and (not r3_a2.passed)
        and (not r3_a2.bogus_auto1_auto2_rejected)
        and (P198_BLOCKED_BOGUS_AUTO1_AUTO2_OR_UNKNOWN_FAN_MODE in r3_a2.blocked_codes)
    )
    outcomes.append(
        Pillar28AScenarioOutcome(
            P198_PILLAR_28A_SCENARIO_IDS[2],
            ok3,
            False,
            r3_a1.effective_fan_mode,
            0,
            r3_a1.blocked_codes,
            "Bogus Auto1/Auto2 tokens rejected fail-closed (ILME-FX3 supports strictly Auto/Minimum/Off in Rec/Always Off)",
        )
    )

    # P28A4: Off in Rec models standby MAX PWM (100%), recording 0% PWM, and emergency thermal override (100% PWM)
    r4_stby = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(
            stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
            stock_fan_control_mode="Off in Rec",
            is_recording=False,
            soc_temp_c=52.0,
        )
    )
    r4_rec = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(
            stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
            stock_fan_control_mode="Off in Rec",
            is_recording=True,
            soc_temp_c=58.0,
        )
    )
    r4_emerg = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(
            stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
            stock_fan_control_mode="Off in Rec",
            is_recording=True,
            soc_temp_c=83.5,
        )
    )
    ok4 = (
        r4_stby.passed
        and r4_stby.expected_pwm_duty_pct == 100
        and r4_rec.passed
        and r4_rec.expected_pwm_duty_pct == 0
        and r4_emerg.passed
        and r4_emerg.emergency_thermal_override_engaged
        and r4_emerg.expected_pwm_duty_pct == 100
    )
    outcomes.append(
        Pillar28AScenarioOutcome(
            P198_PILLAR_28A_SCENARIO_IDS[3],
            ok4,
            True,
            P198_FAN_MODE_OFF_IN_REC,
            r4_stby.expected_pwm_duty_pct,
            (),
            "Off in Rec verified: standby 100% MAX PWM, recording 0% PWM, >=82C emergency safety override 100% PWM",
        )
    )

    # P28A5: Invalid Auto Power OFF Temp or pre-backup SoC overheat (>=85C) aborts entry
    r5_apo = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(auto_power_off_temp="UltraHigh")
    )
    r5_hot = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(soc_temp_c=86.0)
    )
    ok5 = (
        (not r5_apo.passed)
        and (P198_BLOCKED_INVALID_AUTO_POWER_OFF_TEMP in r5_apo.blocked_codes)
        and (not r5_hot.passed)
        and (P198_BLOCKED_SOC_OVERHEAT_PREBACKUP_ABORT in r5_hot.blocked_codes)
    )
    outcomes.append(
        Pillar28AScenarioOutcome(
            P198_PILLAR_28A_SCENARIO_IDS[4],
            ok5,
            False,
            r5_hot.effective_fan_mode,
            r5_hot.expected_pwm_duty_pct,
            r5_apo.blocked_codes + r5_hot.blocked_codes,
            "Invalid [Auto Power OFF Temp.] & >=85C pre-backup thermal hazard rejected fail-closed",
        )
    )

    # P28A6: Persistent write unlock OR Off in Rec PWM curve inversion rejected fail-closed
    r6 = evaluate_fan_pwm_prebackup_thermal_interlock(
        FanPwmThermalInterlockSpec(
            stage_operation=P198_OP_STOCK_SHOOTING_OBSERVATION,
            stock_fan_control_mode="Off in Rec",
            observed_standby_pwm_pct=35,
            observed_recording_pwm_pct=50,
            request_persistent_write_unlock=True,
        )
    )
    ok6 = (
        (not r6.passed)
        and (not r6.off_in_rec_curve_verified)
        and (P198_BLOCKED_OFF_IN_REC_PWM_CURVE_VIOLATION in r6.blocked_codes)
        and (P198_BLOCKED_SAFETY_POLICY_VIOLATION in r6.blocked_codes)
        and r6.physical_device_writes == 0
    )
    outcomes.append(
        Pillar28AScenarioOutcome(
            P198_PILLAR_28A_SCENARIO_IDS[5],
            ok6,
            False,
            r6.effective_fan_mode,
            r6.expected_pwm_duty_pct,
            r6.blocked_codes,
            "Off in Rec PWM inversion & persistent write unlock rejected with 0 device writes",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P198_PILLAR_28A_SCENARIO_IDS)
    return Pillar28AFanInterlockSuiteResult(
        passed=all_ok,
        status=P198_STATUS_VERIFIED_PILLAR_28A if all_ok else P198_STATUS_REJECTED_PILLAR_28A,
        scenarios_passed=passed_count,
        scenarios_total=len(P198_PILLAR_28A_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Pillar 28B — Ver. 6.01 vs 7.00/7.02 LUT Split Vault & Shutter Speed/Angle
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LutSplitShutterVaultSpec:
    donor_stage_b_fw_version: str = P198_FX6_DONOR_FW_VERSION
    donor_lut_serialization_gen: str = P198_LUT_GEN_LEGACY_601
    host_stock_fw_version: str = P198_FX3_FW_VERSION
    host_lut_serialization_gen: str = P198_LUT_GEN_OPTIMIZED_700_PLUS
    stage_b_lut_write_target: str = P198_STAGE_B_VOLATILE_LUT_OVERLAY_DIR
    stage_b_overlay_is_tmpfs: bool = True
    stage_b_p2_setting_writes: int = 0
    p2_blkroset_locked: bool = True
    shutter_mode: str = P198_SHUTTER_MODE_ANGLE
    rec_frame_rate: str = "23.98p"
    sq_mode_active: bool = False
    shutter_angle_deg: float = 180.0
    shutter_speed_denom: float = 48.0
    exposure_step: str = "0.3EV"
    speed_slot_key: str = "BK4_SHUTTER_SPEED_SLOT"
    angle_slot_key: str = "BK4_SHUTTER_ANGLE_SLOT"
    speed_slot_h0_value: str = "1/48"
    speed_slot_h3_value: str = "1/48"
    angle_slot_h0_deg: float = 180.0
    angle_slot_h3_deg: float = 180.0
    exposure_step_mutated_angle_slot: bool = False
    backup_bin_h0_sha256: str = P198_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P198_PINNED_FX3_BACKUP_BIN_SHA256
    user1_16_slots_h0: Optional[Dict[str, Dict[str, Any]]] = None
    user1_16_slots_h3: Optional[Dict[str, Dict[str, Any]]] = None
    cold_boot_returned_to_stock_702: bool = True
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class LutSplitShutterVaultReport:
    passed: bool
    vault_preserved: bool
    lut_gen_split_detected: bool
    legacy_601_pollution_blocked_or_isolated: bool
    volatile_lut_overlay_ok: bool
    shutter_angle_range_ok: bool
    shutter_independent_slots_ok: bool
    exposure_step_decoupled_ok: bool
    user1_16_h0_eq_h3_count: int
    user1_16_total_slots: int
    backup_bin_h0_eq_h3: bool
    max_allowed_angle_deg: float
    shutter_mode: str
    rec_frame_rate: str
    sq_mode_active: bool
    stage_b_lut_write_target: str
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar28BScenarioOutcome:
    scenario_id: str
    passed: bool
    vault_preserved: bool
    user1_16_h0_eq_h3_count: int
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar28BLutShutterSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar28BScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar28StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase198DonorSnapshot
    pillar_28a_fan_pwm_interlock: Pillar28AFanInterlockSuiteResult
    pillar_28b_lut_split_shutter_vault: Pillar28BLutShutterSuiteResult
    suite_sha256: str
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    isp_write_authorized: bool = ISP_WRITE_AUTHORIZED
    persistent_write_release: bool = PERSISTENT_WRITE_RELEASE
    allow_boot_partition_targeting: bool = ALLOW_BOOT_PARTITION_TARGETING
    allow_destructive_fastboot: bool = ALLOW_DESTRUCTIVE_FASTBOOT
    live_usb_iokit_transmit_enabled: bool = LIVE_USB_IOKIT_TRANSMIT_ENABLED
    read_only_donor_access: bool = READ_ONLY_DONOR_ACCESS
    otp_fuse_touches: int = OTP_FUSE_TOUCHES
    otp_fuse_writes: int = OTP_FUSE_WRITES
    rpmb_counter_increments: int = RPMB_COUNTER_INCREMENTS
    passive_tx_bytes_emitted: int = PASSIVE_TX_BYTES_EMITTED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    raw_firmware_bytes_leaked: int = RAW_FIRMWARE_BYTES_LEAKED
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master28PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_6s_budget: bool
    nominal_under_2_4s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase198DonorSnapshot
    pillar28_a_fan_pwm_interlock: Pillar28AFanInterlockSuiteResult
    pillar28_b_lut_split_shutter_vault: Pillar28BLutShutterSuiteResult
    master_28pillar_sha256: str
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


def _compute_max_allowed_shutter_angle_deg(rec_frame_rate: str, sq_mode_active: bool) -> Optional[float]:
    fps = rec_frame_rate.strip()
    if sq_mode_active:
        if fps in P198_HIGH_FPS_RATES_NARROWED_360 or fps in P198_NORMAL_FPS_RATES_ALLOWING_64F:
            return P198_SHUTTER_MAX_ANGLE_HIGH_FPS_AND_SQ_DEG
        return None
    if fps in P198_HIGH_FPS_RATES_NARROWED_360:
        return P198_SHUTTER_MAX_ANGLE_HIGH_FPS_AND_SQ_DEG
    if fps in P198_NORMAL_FPS_RATES_ALLOWING_64F:
        return P198_SHUTTER_MAX_ANGLE_NORMAL_64F_DEG
    return None


def evaluate_lut_split_and_shutter_angle_vault(
    spec: Optional[LutSplitShutterVaultSpec] = None,
) -> LutSplitShutterVaultReport:
    """Verify `6.01` vs `7.00/7.02` `User1..User16` LUT anti-pollution & independent `Backup.bin` `Speed/Angle` slots."""
    cfg = spec if spec is not None else LutSplitShutterVaultSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(P198_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during Pillar 28B LUT/Shutter vault audit")

    # 1. Ver. 6.01 (legacy) vs Ver. 7.00/7.02 (optimized) LUT binary slot split & /tmp/fx6_lut_overlay isolation
    lut_gen_split = (
        cfg.donor_lut_serialization_gen == P198_LUT_GEN_LEGACY_601
        and cfg.host_lut_serialization_gen == P198_LUT_GEN_OPTIMIZED_700_PLUS
    )
    raw_target = cfg.stage_b_lut_write_target.strip()
    norm_target = posixpath.normpath(raw_target) if raw_target.startswith("/") else raw_target
    forbidden_persistent_target = any(
        raw_target.lower().startswith(pfx) or norm_target.lower().startswith(pfx)
        for pfx in P198_FORBIDDEN_PERSISTENT_LUT_TARGETS
    )

    volatile_overlay_ok = (
        norm_target == P198_STAGE_B_VOLATILE_LUT_OVERLAY_DIR
        and (not forbidden_persistent_target)
        and bool(cfg.stage_b_overlay_is_tmpfs)
        and cfg.stage_b_p2_setting_writes == 0
    )

    default_slots = _default_fx3_702_user1_16_lut_slots()
    slots_h0 = cfg.user1_16_slots_h0 if cfg.user1_16_slots_h0 is not None else default_slots
    slots_h3 = cfg.user1_16_slots_h3 if cfg.user1_16_slots_h3 is not None else default_slots

    legacy_slot_polluted = any(
        slots_h3.get(s, {}).get("serialization_gen") != P198_LUT_GEN_OPTIMIZED_700_PLUS
        for s in P198_USER_LUT_SLOT_NAMES
    )

    if forbidden_persistent_target or cfg.stage_b_p2_setting_writes != 0 or legacy_slot_polluted:
        blocked.append(P198_BLOCKED_FX6_601_LEGACY_LUT_P2_SETTING_POLLUTION)
        errors.append(
            f"FX6 Ver. 6.01 legacy LUT serialization attempted or polluted Stock FX3 7.02 p2:/setting: "
            f"target={raw_target!r}, p2_writes={cfg.stage_b_p2_setting_writes}, legacy_polluted={legacy_slot_polluted}"
        )

    if not volatile_overlay_ok:
        blocked.append(P198_BLOCKED_NON_TMPFS_LUT_OVERLAY_PATH)
        errors.append(
            f"Stage-B LUT registry must redirect strictly to volatile tmpfs {P198_STAGE_B_VOLATILE_LUT_OVERLAY_DIR}: "
            f"got target={norm_target!r}, tmpfs={cfg.stage_b_overlay_is_tmpfs}"
        )

    # 2. Shutter [Speed] vs [Angle] range & independent Backup.bin key-slot integrity
    max_angle = _compute_max_allowed_shutter_angle_deg(cfg.rec_frame_rate, cfg.sq_mode_active)
    angle_val = float(cfg.shutter_angle_deg)
    mode_valid = cfg.shutter_mode in P198_VALID_SHUTTER_MODES
    angle_range_ok = (
        mode_valid
        and max_angle is not None
        and (P198_SHUTTER_MIN_ANGLE_DEG - 1e-6 <= angle_val <= max_angle + 1e-6)
        and float(cfg.shutter_speed_denom) > 0.0
    )
    if not angle_range_ok:
        blocked.append(P198_BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE)
        errors.append(
            f"Invalid Shutter mode/angle boundary: mode={cfg.shutter_mode!r}, fps={cfg.rec_frame_rate!r}, "
            f"sq={cfg.sq_mode_active}, angle={angle_val} (allowed 5.6..{max_angle})"
        )

    exp_step_ok = (cfg.exposure_step in P198_VALID_EXPOSURE_STEPS) and (not cfg.exposure_step_mutated_angle_slot)
    independent_slots_ok = (
        bool(cfg.speed_slot_key.strip())
        and bool(cfg.angle_slot_key.strip())
        and cfg.speed_slot_key != cfg.angle_slot_key
        and cfg.speed_slot_h0_value == cfg.speed_slot_h3_value
        and abs(float(cfg.angle_slot_h0_deg) - float(cfg.angle_slot_h3_deg)) <= 1e-6
        and exp_step_ok
    )
    if not independent_slots_ok:
        blocked.append(P198_BLOCKED_SHUTTER_SPEED_ANGLE_SLOT_CLOBBER)
        errors.append(
            f"Backup.bin Shutter [Speed] vs [Angle] independent slot or Exposure step decoupling violated: "
            f"speed_key={cfg.speed_slot_key!r}, angle_key={cfg.angle_slot_key!r}, step={cfg.exposure_step!r}"
        )

    # 3. 16/16 User1..User16 & Backup.bin H0 == H3 across cold-boot return to Stock 7.02
    h0_eq_h3_slots = sum(
        1
        for k in P198_USER_LUT_SLOT_NAMES
        if (k in slots_h0 and k in slots_h3 and slots_h0[k] == slots_h3[k])
    )
    backup_h0_eq_h3 = (
        bool(cfg.p2_blkroset_locked)
        and bool(cfg.cold_boot_returned_to_stock_702)
        and bool(_SHA256_RE.match(cfg.backup_bin_h0_sha256))
        and cfg.backup_bin_h0_sha256 == cfg.backup_bin_h3_sha256
        and h0_eq_h3_slots == P198_USER_LUT_SLOT_COUNT
        and (not legacy_slot_polluted)
    )
    if not backup_h0_eq_h3:
        blocked.append(P198_BLOCKED_USER_LUT_16OF16_H0_H3_DRIFT)
        errors.append(
            f"p2:/setting User1..User16 or Backup.bin H0!=H3 drift: matched={h0_eq_h3_slots}/16, "
            f"blkroset={cfg.p2_blkroset_locked}, cold_boot={cfg.cold_boot_returned_to_stock_702}"
        )

    legacy_isolated_ok = lut_gen_split and volatile_overlay_ok and (not legacy_slot_polluted)
    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = (
        legacy_isolated_ok
        and angle_range_ok
        and independent_slots_ok
        and backup_h0_eq_h3
        and len(dedup_blocked) == 0
        and len(errors) == 0
    )
    return LutSplitShutterVaultReport(
        passed=passed,
        vault_preserved=passed,
        lut_gen_split_detected=lut_gen_split,
        legacy_601_pollution_blocked_or_isolated=legacy_isolated_ok,
        volatile_lut_overlay_ok=volatile_overlay_ok,
        shutter_angle_range_ok=angle_range_ok,
        shutter_independent_slots_ok=independent_slots_ok,
        exposure_step_decoupled_ok=exp_step_ok,
        user1_16_h0_eq_h3_count=h0_eq_h3_slots,
        user1_16_total_slots=P198_USER_LUT_SLOT_COUNT,
        backup_bin_h0_eq_h3=backup_h0_eq_h3,
        max_allowed_angle_deg=max_angle if max_angle is not None else 0.0,
        shutter_mode=cfg.shutter_mode,
        rec_frame_rate=cfg.rec_frame_rate,
        sq_mode_active=cfg.sq_mode_active,
        stage_b_lut_write_target=norm_target,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar28b_lut_split_shutter_6_scenario_suite() -> Pillar28BLutShutterSuiteResult:
    """Run all 6 deterministic scenarios for Pillar 28B (`6.01` vs `7.02` LUT Split & `Speed/Angle` Vault)."""
    outcomes: List[Pillar28BScenarioOutcome] = []

    # P28B1: Happy FX6 6.01 LUT isolated in /tmp/fx6_lut_overlay + 23.98p 64F & 119.88p/S&Q 360° -> 16/16 H0 == H3
    r1_64f = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(
            rec_frame_rate="23.98p",
            sq_mode_active=False,
            shutter_angle_deg=P198_SHUTTER_MAX_ANGLE_NORMAL_64F_DEG,
            exposure_step="0.3EV",
        )
    )
    r1_120p = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(
            rec_frame_rate="119.88p",
            sq_mode_active=False,
            shutter_angle_deg=360.0,
            exposure_step="0.5EV",
        )
    )
    r1_sq = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(
            rec_frame_rate="59.94p",
            sq_mode_active=True,
            shutter_angle_deg=5.6,
        )
    )
    ok1 = (
        r1_64f.passed
        and r1_120p.passed
        and r1_sq.passed
        and r1_64f.user1_16_h0_eq_h3_count == 16
        and r1_120p.max_allowed_angle_deg == 360.0
    )
    outcomes.append(
        Pillar28BScenarioOutcome(
            P198_PILLAR_28B_SCENARIO_IDS[0],
            ok1,
            True,
            16,
            (),
            "FX6 6.01 LUT isolated in /tmp/fx6_lut_overlay; Stock FX3 7.02 User1..User16 & Shutter 16/16 H0==H3",
        )
    )

    # P28B2: FX6 Ver. 6.01 legacy LUT serialization attempting to write or pollute p2:/setting User1..User16 blocked
    polluted_slots = _default_fx3_702_user1_16_lut_slots()
    polluted_slots["User1"] = {
        "serialization_gen": P198_LUT_GEN_LEGACY_601,
        "fw_origin": "6.01",
        "cube_name": "FX6_601_LegacySlot.cube",
        "grid_size": 33,
        "slot_sha256": "b" * 64,
    }
    r2 = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(
            stage_b_lut_write_target="p2:/setting/lut_slots",
            stage_b_p2_setting_writes=1,
            user1_16_slots_h3=polluted_slots,
        )
    )
    ok2 = (
        (not r2.passed)
        and (P198_BLOCKED_FX6_601_LEGACY_LUT_P2_SETTING_POLLUTION in r2.blocked_codes)
        and r2.user1_16_h0_eq_h3_count == 15
    )
    outcomes.append(
        Pillar28BScenarioOutcome(
            P198_PILLAR_28B_SCENARIO_IDS[1],
            ok2,
            False,
            r2.user1_16_h0_eq_h3_count,
            r2.blocked_codes,
            "FX6 Ver. 6.01 legacy LUT binary slot write to Stock FX3 7.02 p2:/setting blocked fail-closed",
        )
    )

    # P28B3: Independent [Speed] vs [Angle] slots preserved across 0.3EV / 0.5EV Exposure step transitions
    r3_03 = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(
            shutter_mode="Speed",
            exposure_step="0.3EV",
            speed_slot_h0_value="1/100",
            speed_slot_h3_value="1/100",
            angle_slot_h0_deg=172.8,
            angle_slot_h3_deg=172.8,
        )
    )
    r3_05 = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(
            shutter_mode="Angle",
            exposure_step="0.5EV",
            speed_slot_h0_value="1/100",
            speed_slot_h3_value="1/100",
            angle_slot_h0_deg=172.8,
            angle_slot_h3_deg=172.8,
        )
    )
    ok3 = (
        r3_03.passed
        and r3_03.shutter_independent_slots_ok
        and r3_03.exposure_step_decoupled_ok
        and r3_05.passed
        and r3_05.shutter_independent_slots_ok
    )
    outcomes.append(
        Pillar28BScenarioOutcome(
            P198_PILLAR_28B_SCENARIO_IDS[2],
            ok3,
            True,
            16,
            (),
            "Independent Backup.bin [Speed] and [Angle] slots preserved across 0.3EV/0.5EV Exposure step",
        )
    )

    # P28B4: Angle >360° at 119.88p/100p or S&Q, or <5.6° blocked fail-closed
    r4_120_over = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(rec_frame_rate="119.88p", shutter_angle_deg=720.0)
    )
    r4_100_over = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(rec_frame_rate="100p", shutter_angle_deg=361.0)
    )
    r4_sq_over = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(rec_frame_rate="24.00p", sq_mode_active=True, shutter_angle_deg=720.0)
    )
    r4_under = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(rec_frame_rate="23.98p", shutter_angle_deg=4.0)
    )
    ok4 = all(
        (not r.passed) and (P198_BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE in r.blocked_codes)
        for r in (r4_120_over, r4_100_over, r4_sq_over, r4_under)
    )
    outcomes.append(
        Pillar28BScenarioOutcome(
            P198_PILLAR_28B_SCENARIO_IDS[3],
            ok4,
            False,
            16,
            r4_120_over.blocked_codes,
            "Out-of-range Shutter Angle (<5.6 deg or >360 deg on 119.88p/100p/S&Q) rejected fail-closed",
        )
    )

    # P28B5: Non-tmpfs overlay escape or User1..User16 H0!=H3 slot hash drift on cold-boot return blocked
    drifted = _default_fx3_702_user1_16_lut_slots()
    drifted["User16"]["slot_sha256"] = "c" * 64
    r5 = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(
            stage_b_lut_write_target="/var/tmp/non_volatile_lut",
            stage_b_overlay_is_tmpfs=False,
            user1_16_slots_h3=drifted,
            backup_bin_h3_sha256="d" * 64,
        )
    )
    ok5 = (
        (not r5.passed)
        and (P198_BLOCKED_NON_TMPFS_LUT_OVERLAY_PATH in r5.blocked_codes)
        and (P198_BLOCKED_USER_LUT_16OF16_H0_H3_DRIFT in r5.blocked_codes)
        and r5.user1_16_h0_eq_h3_count == 15
    )
    outcomes.append(
        Pillar28BScenarioOutcome(
            P198_PILLAR_28B_SCENARIO_IDS[4],
            ok5,
            False,
            r5.user1_16_h0_eq_h3_count,
            r5.blocked_codes,
            "Non-tmpfs LUT overlay escape & User1..User16 H0!=H3 slot drift rejected fail-closed",
        )
    )

    # P28B6: Coupled Speed/Angle slot clobber, Exposure step mutation, or persistent write unlock blocked
    r6 = evaluate_lut_split_and_shutter_angle_vault(
        LutSplitShutterVaultSpec(
            speed_slot_key="SHARED_SHUTTER_SLOT",
            angle_slot_key="SHARED_SHUTTER_SLOT",
            exposure_step_mutated_angle_slot=True,
            request_persistent_write_unlock=True,
        )
    )
    ok6 = (
        (not r6.passed)
        and (not r6.shutter_independent_slots_ok)
        and (P198_BLOCKED_SHUTTER_SPEED_ANGLE_SLOT_CLOBBER in r6.blocked_codes)
        and (P198_BLOCKED_SAFETY_POLICY_VIOLATION in r6.blocked_codes)
        and r6.physical_device_writes == 0
    )
    outcomes.append(
        Pillar28BScenarioOutcome(
            P198_PILLAR_28B_SCENARIO_IDS[5],
            ok6,
            False,
            r6.user1_16_h0_eq_h3_count,
            r6.blocked_codes,
            "Coupled Speed/Angle slot clobber & persistent write unlock rejected with 0 device writes",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P198_PILLAR_28B_SCENARIO_IDS)
    return Pillar28BLutShutterSuiteResult(
        passed=all_ok,
        status=P198_STATUS_VERIFIED_PILLAR_28B if all_ok else P198_STATUS_REJECTED_PILLAR_28B,
        scenarios_passed=passed_count,
        scenarios_total=len(P198_PILLAR_28B_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


def run_pillar28_standalone_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Pillar28StandaloneReport:
    """Run Pillar 28 standalone donor audit + Pillar 28A (`Fan Control`) + Pillar 28B (`LUT Split & Shutter`)."""
    _need(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    _need(SPI_NOR_WRITE_AUTHORIZED is False, "spi_nor_write_authorized must stay False")
    _need(EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False, "el3_payload_transmit_authorized must stay False")
    _need(ISP_WRITE_AUTHORIZED is False, "isp_write_authorized must stay False")
    _need(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    _need(OTP_FUSE_TOUCHES == 0 and OTP_FUSE_WRITES == 0, "OTP fuse counters must stay 0")
    _need(RPMB_COUNTER_INCREMENTS == 0, "RPMB counter increments must stay 0")
    _need(PHYSICAL_USB_PACKETS_EMITTED == 0, "Physical USB packets must stay 0")
    _need(PHYSICAL_DEVICE_WRITES == 0, "Physical device writes must stay 0")
    _need(RAW_FIRMWARE_BYTES_LEAKED == 0, "Raw firmware bytes leaked must stay 0")

    t0 = time.monotonic()
    snap = inspect_phase198_donors_readonly(force_clean_room=force_clean_room)
    p28a = run_pillar28a_fan_pwm_thermal_6_scenario_suite()
    p28b = run_pillar28b_lut_split_shutter_6_scenario_suite()
    elapsed = round(time.monotonic() - t0, 6)

    errors: List[str] = list(snap.errors)
    if not p28a.passed:
        errors.append("Pillar 28A 4-mode Fan PWM & pre-backup thermal interlock suite failed")
    if not p28b.passed:
        errors.append("Pillar 28B 6.01 vs 7.02 LUT split & Shutter Speed/Angle vault suite failed")

    all_ok = (
        snap.all_passed
        and p28a.passed
        and p28b.passed
        and PERSISTENT_EMMC_WRITES_AUTHORIZED is False
        and SPI_NOR_WRITE_AUTHORIZED is False
        and EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False
        and ISP_WRITE_AUTHORIZED is False
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
        and len(errors) == 0
    )

    suite_sha = _canonical_sha256(
        {
            "schema": PHASE198_SCHEMA,
            "version": PHASE198_VERSION,
            "mode": snap.verification_mode,
            "snapshot_sha256": snap.snapshot_sha256,
            "p28a": p28a.to_dict(),
            "p28b": p28b.to_dict(),
            "all_passed": all_ok,
        }
    )
    return Pillar28StandaloneReport(
        schema=PHASE198_SCHEMA,
        version=PHASE198_VERSION,
        verification_mode=snap.verification_mode,
        all_passed=all_ok,
        status=P198_STATUS_VERIFIED_PILLAR28_SUITE if all_ok else P198_STATUS_FAIL_PILLAR28_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=snap,
        pillar_28a_fan_pwm_interlock=p28a,
        pillar_28b_lut_split_shutter_vault=p28b,
        suite_sha256=suite_sha,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified 28/28 Recovery Master Aggregator (`evaluate_28pillar_recovery_master`)
# ---------------------------------------------------------------------------


def _apply_master28_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
    err = f"FAULT_INJECTED:{pillar.pillar_id}"
    return MasterPillarStatus(
        pillar_number=pillar.pillar_number,
        pillar_id=pillar.pillar_id,
        phase_label=pillar.phase_label,
        module_name=pillar.module_name,
        passed=False,
        status=f"FAULT_INJECTED_{pillar.pillar_id.upper()}",
        verification_mode=pillar.verification_mode,
        elapsed_seconds=pillar.elapsed_seconds,
        key_metrics=pillar.key_metrics,
        digest_sha256=_canonical_sha256({"pillar": pillar.pillar_id, "fault_injected": True}),
        errors=pillar.errors + (err,),
    )


def evaluate_28pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master28PillarRecoveryReport:
    """Evaluate and aggregate all 28 recovery pillars (`1..28`) concurrently in `< 2.4s`."""
    _need(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    _need(SPI_NOR_WRITE_AUTHORIZED is False, "spi_nor_write_authorized must stay False")
    _need(EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False, "el3_payload_transmit_authorized must stay False")
    _need(ISP_WRITE_AUTHORIZED is False, "isp_write_authorized must stay False")
    _need(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    _need(LIVE_USB_IOKIT_TRANSMIT_ENABLED is False, "live_usb_iokit_transmit_enabled must stay False")
    _need(OTP_FUSE_TOUCHES == 0 and OTP_FUSE_WRITES == 0, "OTP fuse counters must stay 0")
    _need(RPMB_COUNTER_INCREMENTS == 0, "RPMB counter increments must stay 0")
    _need(PASSIVE_TX_BYTES_EMITTED == 0, "Passive TX bytes must stay 0")
    _need(PHYSICAL_USB_PACKETS_EMITTED == 0, "Physical USB packets must stay 0")
    _need(PHYSICAL_DEVICE_WRITES == 0, "Physical device writes must stay 0")
    _need(RAW_FIRMWARE_BYTES_LEAKED == 0, "Raw firmware bytes leaked must stay 0")

    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_28_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_27pillar() -> Master27PillarRecoveryReport:
        return evaluate_27pillar_recovery_master(**kw)

    def _run_p28() -> Tuple[Pillar28StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar28_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_27 = pool.submit(_run_27pillar)
        fut_28 = pool.submit(_run_p28)
        m27_rep = fut_27.result()
        p28_rep, p28_dt = fut_28.result()

    safety_errors: List[str] = list(m27_rep.errors)
    for attr_name, expected_val in (
        ("otp_fuse_touches", 0),
        ("otp_fuse_writes", 0),
        ("rpmb_counter_increments", 0),
        ("passive_tx_bytes_emitted", 0),
        ("physical_usb_packets_emitted", 0),
        ("physical_device_writes", 0),
        ("raw_firmware_bytes_leaked", 0),
        ("el3_payload_transmit_authorized", False),
        ("isp_write_authorized", False),
        ("spi_nor_write_authorized", False),
        ("persistent_emmc_writes_authorized", False),
        ("persistent_write_release", False),
        ("live_usb_iokit_transmit_enabled", False),
    ):
        if getattr(m27_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillars 1-27 violated {attr_name} == {expected_val}")
        if hasattr(p28_rep, attr_name) and getattr(p28_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillar 28 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m27_rep.pillars)

    spec28 = MASTER_28_PILLAR_SPECS[27]
    p28_metrics = {
        "pillar_28a_fan_pwm_interlock": (
            f"{p28_rep.pillar_28a_fan_pwm_interlock.scenarios_passed}/"
            f"{p28_rep.pillar_28a_fan_pwm_interlock.scenarios_total}"
        ),
        "pillar_28b_lut_split_shutter_vault": (
            f"{p28_rep.pillar_28b_lut_split_shutter_vault.scenarios_passed}/"
            f"{p28_rep.pillar_28b_lut_split_shutter_vault.scenarios_total}"
        ),
        "donor_files_inspected": p28_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec28[0],
            pillar_id=spec28[1],
            phase_label=spec28[2],
            module_name=spec28[3],
            passed=bool(p28_rep.all_passed),
            status=p28_rep.status,
            verification_mode=p28_rep.verification_mode,
            elapsed_seconds=p28_dt,
            key_metrics=p28_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec28[1],
                    "mode": p28_rep.verification_mode,
                    "status": p28_rep.status,
                    "metrics": p28_metrics,
                    "passed": p28_rep.all_passed,
                }
            ),
            errors=tuple(p28_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master28_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p28_rep.verification_mode

    all_ok = (
        len(pillar_statuses) == MASTER_28_PILLAR_COUNT == 28
        and pillars_passed == 28
        and len(failed) == 0
        and len(safety_errors) == 0
        and OTP_FUSE_TOUCHES == 0
        and OTP_FUSE_WRITES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and PASSIVE_TX_BYTES_EMITTED == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
        and (EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False)
        and (ISP_WRITE_AUTHORIZED is False)
        and (SPI_NOR_WRITE_AUTHORIZED is False)
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and (LIVE_USB_IOKIT_TRANSMIT_ENABLED is False)
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE198_SCHEMA,
            "version": PHASE198_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )

    return Master28PillarRecoveryReport(
        schema=PHASE198_SCHEMA,
        version=PHASE198_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P198_STATUS_VERIFIED_28OF28_AGGREGATOR if all_ok else P198_STATUS_FAIL_28OF28_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P198_CONCURRENT_CEILING_SECONDS,
        nominal_under_2_4s=elapsed < P198_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p28_rep.donor_snapshot,
        pillar28_a_fan_pwm_interlock=p28_rep.pillar_28a_fan_pwm_interlock,
        pillar28_b_lut_split_shutter_vault=p28_rep.pillar_28b_lut_split_shutter_vault,
        master_28pillar_sha256=master_sha,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errors),
    )


def verify_28pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master28PillarRecoveryReport:
    """Public entry point for Pillar 28 unified `28/28` real-hardware recovery master verification."""
    return evaluate_28pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
