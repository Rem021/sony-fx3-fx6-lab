"""Phase 86 — Passive 1.8V RX-Only UART Boot-Stage Decoder (S0..S6) & Unified fx3_recovery Master Self-Audit.

Delivers two integrated offline recovery & diagnostics pillars for Sony ILME-FX3 (`0x91030080`):

1. **Passive `1.8V` RX-Only `CXD90057` Boot-Stage State Machine (`S0..S6`) & 10-Signature Fault Triage**:
   - Enforces **RX-Only Passive Tap Safety** (`tx_line_connected == False` or
     `open_drain_tx_idle_1v8 == True`, `passive_tx_bytes_emitted == 0`, `io_voltage_v in [1.65V, 1.98V]`)
     so `CXD90057` BootROM `uart_boot` is never accidentally triggered during normal boot monitoring,
     and rejects any active TX injection attempt fail-closed.
   - Deterministically parses serial boot traces across all 7 stages:
     `S0_BOOTROM_ENTRY` -> `S1_NBL_OPTEE_TRUSTZONE` -> `S2_UBOOT_BOOT_AB` ->
     `S3_LINUX_4_9_337_SCEL` -> `S4_INIT2_SENTINEL_CHECK` ->
     `S5_STAGE_B_TMPFS_MOUNT` -> `S6_ICX1295_BIG6_READY`.
   - Classifies 10 deterministic boot/runtime fault signatures and prescribes minimal
     zero-eMMC-write recovery actions (`HEALTHY_STAGE_B_LIVE`, `CLEAN_SD_SENTINEL_STOCK_ESCAPE`,
     `CLEAN_HASH_FAILOPEN_STOCK_BOOT`, `NO_EMMC_FLASH_NEEDED`, `TIER0_CRASH_BREAKER_RECOVERED`,
     `TIER0_COLD_REBOOT_WIPES_TMPFS`, `NEVER_CROSS_FLASH_FX6_WBI2`,
     `TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK`, `CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN`,
     `DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN`).

2. **Unified `fx3_recovery` 7-Pillar Master Readiness Audit (`run_recovery_master_suite`)**:
   - Executes and aggregates all 7 `fx3_recovery` safety & recovery pillars in `< 1.0s`
     across both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:
     1. `macos_usb_transport_guard`
     2. `rp2040_multiport_fixture_selftest` (`camera_connected == False`)
     3. `init2_escape_and_watchdog_simulator` (`7/7` escape drills, `5/5` WDT drills)
     4. `tier0_backup_parity_and_manifest_guard` (`GF(256)` P+Q bit-rot heal + anti-transplant lock)
     5. `firmware_updata_and_antirollback_guard` (`otp_fuse_touches == 0`, `rpmb_counter_increments == 0`, `EXT_CSD` perm-WP blocked)
     6. `unbrick_ladder_and_capsule_verifier` (`Tier-0..4` 12-scenario ladder + `p1` VFAT capsules)
     7. Passive `S0..S6` UART 10-scenario boot-stage decoder (`passive_tx_bytes_emitted == 0`)
   - Emits deterministic `recovery_master_sha256` with `persistent_emmc_writes_authorized = False`
     and `persistent_write_release = False` hard-locked.
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import re
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from .fat import MAX_P1
from .files import is_forced_clean_room, read_file, require, resolve_donor_path
from .firmware_updata_and_antirollback_guard import run_antirollback_and_byof_guard_suite
from .init2_escape_and_watchdog_simulator import run_init2_escape_and_watchdog_suite
from .macos_usb_transport_guard import (
    ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    ALLOW_PERSISTENT_JIRITSU_WRITES,
    FX3_MODEL_ID,
    FX3_MSC_VID_PID,
    JIRITSU_BLOCK,
    JIRITSU_CODE_FORMAT,
    JIRITSU_CODE_FIRMUP,
    JIRITSU_CODE_GET_FILE,
    JIRITSU_CODE_GET_FILE2,
    JIRITSU_CODE_MOUNT,
    JIRITSU_CODE_SET_FILE_PATH,
    JIRITSU_PFUNC,
    K_IORETURN_EXCLUSIVE_ACCESS,
    K_IORETURN_SUCCESS,
    SONY_SERVICE_VID_PID,
    JiritsuCommand,
    MacOSUSBTransportSession,
    SenserChallenge,
    TransportState,
)
from .rp2040_multiport_fixture_selftest import run_rp2040_multiport_fixture_selftest
from .tier0_backup_parity_and_manifest_guard import run_tier0_backup_parity_suite
from .unbrick_ladder_and_capsule_verifier import run_unbrick_ladder_and_capsule_suite


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Protocol Constants
# ---------------------------------------------------------------------------

RECOVERY_MASTER_SUITE_SCHEMA: str = "fx3-recovery-master-suite-and-uart-decoder-v1"
RECOVERY_MASTER_SUITE_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
PHYSICAL_DEVICE_WRITES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0

UART_TAP_NOMINAL_VOLTAGE_V: float = 1.80
UART_TAP_MIN_SAFE_VOLTAGE_V: float = 1.65
UART_TAP_MAX_SAFE_VOLTAGE_V: float = 1.98
UART_CONSOLE_BAUD: int = 115200
UART_BOOTROM_BAUD: int = 48000
SUPPORTED_PASSIVE_UART_BAUDS: Tuple[int, ...] = (UART_BOOTROM_BAUD, UART_CONSOLE_BAUD)
FRAMING_NOISE_BURST_RATIO_THRESHOLD: float = 0.25

DONOR_P1_205_RELPATH: str = "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"

STATUS_VERIFIED_RECOVERY_MASTER_SUITE: str = "VERIFIED_RECOVERY_MASTER_SUITE"
STATUS_FAIL_RECOVERY_MASTER_SUITE: str = "FAIL_RECOVERY_MASTER_SUITE"
STATUS_VERIFIED_UART_DECODER_SUITE: str = "VERIFIED_UART_BOOT_DECODER_SUITE"
STATUS_FAIL_UART_DECODER_SUITE: str = "FAIL_UART_BOOT_DECODER_SUITE"
STATUS_VERIFIED_PASSIVE_RX_TAP: str = "VERIFIED_PASSIVE_RX_ONLY_1V8_TAP"

# 7 Deterministic CXD90057 Boot Stages (S0..S6)
BOOT_STAGES: Tuple[str, ...] = (
    "S0_BOOTROM_ENTRY",
    "S1_NBL_OPTEE_TRUSTZONE",
    "S2_UBOOT_BOOT_AB",
    "S3_LINUX_4_9_337_SCEL",
    "S4_INIT2_SENTINEL_CHECK",
    "S5_STAGE_B_TMPFS_MOUNT",
    "S6_ICX1295_BIG6_READY",
)
STAGE_INDEX_MAP: Dict[str, int] = {stage: idx for idx, stage in enumerate(BOOT_STAGES)}

# 10 Deterministic Triage Outcomes + Fail-Closed Guards
OUTCOME_HEALTHY_STAGE_B_LIVE: str = "HEALTHY_STAGE_B_LIVE"
OUTCOME_CLEAN_SD_SENTINEL_STOCK_ESCAPE: str = "CLEAN_SD_SENTINEL_STOCK_ESCAPE"
OUTCOME_CLEAN_HASH_FAILOPEN_STOCK_BOOT: str = "CLEAN_HASH_FAILOPEN_STOCK_BOOT"
OUTCOME_NO_EMMC_FLASH_NEEDED: str = "NO_EMMC_FLASH_NEEDED"
OUTCOME_TIER0_CRASH_BREAKER_RECOVERED: str = "TIER0_CRASH_BREAKER_RECOVERED"
OUTCOME_TIER0_COLD_REBOOT_WIPES_TMPFS: str = "TIER0_COLD_REBOOT_WIPES_TMPFS"
OUTCOME_NEVER_CROSS_FLASH_FX6_WBI2: str = "NEVER_CROSS_FLASH_FX6_WBI2"
OUTCOME_TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK: str = "TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK"
OUTCOME_CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN: str = "CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN"
OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN: str = "DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN"

OUTCOME_BLOCKED_ACTIVE_TX_INJECTION: str = "BLOCKED_ACTIVE_TX_INJECTION"
OUTCOME_BLOCKED_UNSAFE_TX_LINE: str = "BLOCKED_UNSAFE_TX_LINE_CONNECTED"
OUTCOME_BLOCKED_UNDERVOLTAGE_TAP: str = "BLOCKED_UNDERVOLTAGE_UART_TAP"
OUTCOME_BLOCKED_LTC_CONFLICT: str = "BLOCKED_LTC_CABLE_CONFLICT"
OUTCOME_BLOCKED_UNSUPPORTED_BAUD: str = "BLOCKED_UNSUPPORTED_UART_BAUD"
OUTCOME_UNKNOWN_OR_INCOMPLETE_BOOT_LOG: str = "UNKNOWN_OR_INCOMPLETE_BOOT_LOG"

TEN_OUTCOME_CODES: Tuple[str, ...] = (
    OUTCOME_HEALTHY_STAGE_B_LIVE,
    OUTCOME_CLEAN_SD_SENTINEL_STOCK_ESCAPE,
    OUTCOME_CLEAN_HASH_FAILOPEN_STOCK_BOOT,
    OUTCOME_NO_EMMC_FLASH_NEEDED,
    OUTCOME_TIER0_CRASH_BREAKER_RECOVERED,
    OUTCOME_TIER0_COLD_REBOOT_WIPES_TMPFS,
    OUTCOME_NEVER_CROSS_FLASH_FX6_WBI2,
    OUTCOME_TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK,
    OUTCOME_CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN,
    OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN,
)

UART_SCENARIO_IDS: Tuple[str, ...] = (
    "U01_HEALTHY_STAGE_B_LIVE",
    "U02_SD_SENTINEL_STOCK_ESCAPE",
    "U03_CPIO_SHA256_MISMATCH_FAILOPEN",
    "U04_ICX1295_WF12_00342260_ASSERT",
    "U05_PROCAM_3X_15S_CRASH_BREAKER",
    "U06_KERNEL_PAGING_OOPS_WDT_WIPES_H1",
    "U07_WBI2_HIBERNATE_MISMATCH",
    "U08_P1_INIT2_SH_SYNTAX_OR_HANG",
    "U09_OTP_RPMB_ANTIROLLBACK_REJECT",
    "U10_3V3_OVERVOLTAGE_FRAMING_BURST",
)

PILLAR_IDS: Tuple[str, ...] = (
    "macos_usb_transport_guard",
    "rp2040_multiport_fixture_selftest",
    "init2_escape_and_watchdog_simulator",
    "tier0_backup_parity_and_manifest_guard",
    "firmware_updata_and_antirollback_guard",
    "unbrick_ladder_and_capsule_verifier",
    "passive_uart_boot_stage_decoder",
)


# ---------------------------------------------------------------------------
# Structured Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class PassiveTapConfig:
    tx_line_connected: bool = False
    open_drain_tx_idle_1v8: bool = True
    tx_bytes_attempted: int = 0
    io_voltage_v: float = UART_TAP_NOMINAL_VOLTAGE_V
    baud_rate: int = UART_CONSOLE_BAUD
    ltc_cable_connected: bool = False


@dataclass(frozen=True)
class PassiveTapSafetyResult:
    safe: bool
    status: str
    tx_line_connected: bool
    open_drain_tx_idle_1v8: bool
    passive_tx_bytes_emitted: int
    tx_bytes_attempted: int
    io_voltage_v: float
    baud_rate: int
    ltc_cable_connected: bool
    bootrom_uart_boot_trigger_risk: bool
    recommended_action: str
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class UartBootStageTrace:
    stages_observed: Tuple[str, ...]
    highest_stage_reached: Optional[str]
    highest_stage_index: int
    stage_transitions: Tuple[str, ...]
    stage_line_numbers: Dict[str, int]
    wdt_reset_observed: bool
    stock_fallback_observed: bool
    valid_monotonic_progression: bool


@dataclass(frozen=True)
class UartBootDecodeResult:
    passed: bool
    triage_classified: bool
    safe_to_operate: bool
    scenario_id: str
    outcome_code: str
    fault_detected: bool
    critical_hazard: bool
    highest_stage_reached: Optional[str]
    stages_observed: Tuple[str, ...]
    stage_transitions: Tuple[str, ...]
    valid_monotonic_progression: bool
    recovery_tier: str
    recovery_action: str
    prescribed_steps: Tuple[str, ...]
    matched_signature: str
    framing_noise_ratio: float
    passive_tap_safety: PassiveTapSafetyResult
    passive_tx_bytes_emitted: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int
    emmc_write_bytes: int
    log_sha256: str
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UartBootScenarioSpec:
    scenario_number: int
    scenario_id: str
    expected_outcome_code: str
    expected_highest_stage: Optional[str]
    expected_recovery_tier: str
    log_text: str
    tap: PassiveTapConfig = PassiveTapConfig()


@dataclass(frozen=True)
class UartDecoderSuiteResult:
    passed: bool
    status: str
    verification_mode: str
    scenarios_total: int
    scenarios_passed: int
    active_tx_rejection_verified: bool
    unsafe_tx_line_rejection_verified: bool
    overvoltage_3v3_tap_rejection_verified: bool
    passive_tx_bytes_emitted: int
    scenario_results: Tuple[UartBootDecodeResult, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_device_writes: int
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarAuditSummary:
    pillar_number: int
    pillar_id: str
    module_name: str
    passed: bool
    status: str
    verification_mode: str
    summary_metrics: Dict[str, Any]
    deterministic_digest_sha256: str
    elapsed_seconds: float
    errors: Tuple[str, ...] = ()


@dataclass(frozen=True)
class RecoveryMasterSuiteReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    recovery_master_sha256: str
    donor_p1_sha256: str
    elapsed_seconds: float
    passive_tx_bytes_emitted: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    allow_persistent_jiritsu_writes: bool
    allow_destructive_jiritsu_commands: bool
    physical_device_writes: int
    pillars: Tuple[PillarAuditSummary, ...]
    uart_decoder_suite: UartDecoderSuiteResult
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    encoded = json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False).encode(
        "utf-8"
    )
    return sha256(encoded).hexdigest()


def _normalize_log_input(log_data: Union[str, bytes, bytearray]) -> str:
    if isinstance(log_data, (bytes, bytearray)):
        text = bytes(log_data).decode("utf-8", errors="replace")
    elif isinstance(log_data, str):
        text = log_data
    else:
        raise TypeError("log_data must be str or bytes")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def _compute_framing_noise_ratio(text: str) -> float:
    if not text:
        return 0.0
    noisy = 0
    total = 0
    for ch in text:
        if ch in ("\n", "\r", "\t"):
            continue
        total += 1
        code = ord(ch)
        if ch == "\ufffd" or code < 0x20 or code == 0x7F or (0x80 <= code <= 0x9F):
            noisy += 1
    if total == 0:
        return 0.0
    return round(noisy / float(total), 6)


# ---------------------------------------------------------------------------
# 1. Passive 1.8V RX-Only Tap Safety Firewall
# ---------------------------------------------------------------------------


def audit_passive_rx_tap_safety(
    tap: Optional[PassiveTapConfig] = None,
    *,
    active_tx_payload: bytes = b"",
) -> PassiveTapSafetyResult:
    """Enforce passive 1.8V RX-only monitoring invariants (`passive_tx_bytes_emitted == 0`).

    BootROM `uart_boot` on `CXD90057` must NEVER be inadvertently triggered during normal
    boot monitoring. Passive tap requires either `tx_line_connected == False` OR
    `open_drain_tx_idle_1v8 == True`, zero TX bytes attempted, safe `1.8V` logic level,
    and no conflicting `VMC-BNCM1` LTC adapter.
    """
    cfg = PassiveTapConfig() if tap is None else tap
    if not isinstance(active_tx_payload, (bytes, bytearray)):
        raise TypeError("active_tx_payload must be bytes")
    if cfg.tx_bytes_attempted < 0:
        raise ValueError("tx_bytes_attempted must be >= 0")

    attempted = cfg.tx_bytes_attempted + len(active_tx_payload)
    errors: List[str] = []

    if attempted > 0:
        errors.append(
            f"Active TX injection rejected in passive RX-only tap mode (attempted={attempted} bytes); "
            "passive_tx_bytes_emitted locked to 0."
        )
        return PassiveTapSafetyResult(
            safe=False,
            status=OUTCOME_BLOCKED_ACTIVE_TX_INJECTION,
            tx_line_connected=cfg.tx_line_connected,
            open_drain_tx_idle_1v8=cfg.open_drain_tx_idle_1v8,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            tx_bytes_attempted=attempted,
            io_voltage_v=cfg.io_voltage_v,
            baud_rate=cfg.baud_rate,
            ltc_cable_connected=cfg.ltc_cable_connected,
            bootrom_uart_boot_trigger_risk=True,
            recommended_action="ABORT_TX_INJECTION_DISCONNECT_TX_PIN7_RX_ONLY",
            errors=tuple(errors),
        )

    if cfg.io_voltage_v > UART_TAP_MAX_SAFE_VOLTAGE_V:
        errors.append(
            f"UART tap overvoltage hazard: {cfg.io_voltage_v:.2f}V > {UART_TAP_MAX_SAFE_VOLTAGE_V:.2f}V "
            "(1.8V CXD90057 RX/TX tolerance exceeded; 3.3V TTL will damage SoC)."
        )
        return PassiveTapSafetyResult(
            safe=False,
            status=OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN,
            tx_line_connected=cfg.tx_line_connected,
            open_drain_tx_idle_1v8=cfg.open_drain_tx_idle_1v8,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            tx_bytes_attempted=0,
            io_voltage_v=cfg.io_voltage_v,
            baud_rate=cfg.baud_rate,
            ltc_cable_connected=cfg.ltc_cable_connected,
            bootrom_uart_boot_trigger_risk=True,
            recommended_action=OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN,
            errors=tuple(errors),
        )

    if cfg.io_voltage_v < UART_TAP_MIN_SAFE_VOLTAGE_V:
        errors.append(
            f"UART tap undervoltage: {cfg.io_voltage_v:.2f}V < {UART_TAP_MIN_SAFE_VOLTAGE_V:.2f}V."
        )
        return PassiveTapSafetyResult(
            safe=False,
            status=OUTCOME_BLOCKED_UNDERVOLTAGE_TAP,
            tx_line_connected=cfg.tx_line_connected,
            open_drain_tx_idle_1v8=cfg.open_drain_tx_idle_1v8,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            tx_bytes_attempted=0,
            io_voltage_v=cfg.io_voltage_v,
            baud_rate=cfg.baud_rate,
            ltc_cable_connected=cfg.ltc_cable_connected,
            bootrom_uart_boot_trigger_risk=False,
            recommended_action="CHECK_1V8_OPEN_DRAIN_PULLUP_AND_GND",
            errors=tuple(errors),
        )

    if cfg.tx_line_connected and not cfg.open_drain_tx_idle_1v8:
        errors.append(
            "Host TX line connected without 1.8V open-drain Hi-Z idle; risk of driving BootROM uart_boot."
        )
        return PassiveTapSafetyResult(
            safe=False,
            status=OUTCOME_BLOCKED_UNSAFE_TX_LINE,
            tx_line_connected=cfg.tx_line_connected,
            open_drain_tx_idle_1v8=cfg.open_drain_tx_idle_1v8,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            tx_bytes_attempted=0,
            io_voltage_v=cfg.io_voltage_v,
            baud_rate=cfg.baud_rate,
            ltc_cable_connected=cfg.ltc_cable_connected,
            bootrom_uart_boot_trigger_risk=True,
            recommended_action="UNPLUG_TX_PIN7_OR_ENABLE_OPEN_DRAIN_1V8_IDLE",
            errors=tuple(errors),
        )

    if cfg.ltc_cable_connected:
        errors.append("VMC-BNCM1 LTC cable conflict on Sony 15-pin Multi-Port during UART tap.")
        return PassiveTapSafetyResult(
            safe=False,
            status=OUTCOME_BLOCKED_LTC_CONFLICT,
            tx_line_connected=cfg.tx_line_connected,
            open_drain_tx_idle_1v8=cfg.open_drain_tx_idle_1v8,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            tx_bytes_attempted=0,
            io_voltage_v=cfg.io_voltage_v,
            baud_rate=cfg.baud_rate,
            ltc_cable_connected=cfg.ltc_cable_connected,
            bootrom_uart_boot_trigger_risk=False,
            recommended_action="UNPLUG_VMC_BNCM1_LTC_CABLE_BEFORE_UART_TAP",
            errors=tuple(errors),
        )

    if cfg.baud_rate not in SUPPORTED_PASSIVE_UART_BAUDS:
        errors.append(
            f"Unsupported passive UART baud {cfg.baud_rate}; expected one of {SUPPORTED_PASSIVE_UART_BAUDS}."
        )
        return PassiveTapSafetyResult(
            safe=False,
            status=OUTCOME_BLOCKED_UNSUPPORTED_BAUD,
            tx_line_connected=cfg.tx_line_connected,
            open_drain_tx_idle_1v8=cfg.open_drain_tx_idle_1v8,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            tx_bytes_attempted=0,
            io_voltage_v=cfg.io_voltage_v,
            baud_rate=cfg.baud_rate,
            ltc_cable_connected=cfg.ltc_cable_connected,
            bootrom_uart_boot_trigger_risk=False,
            recommended_action="SET_PASSIVE_UART_BAUD_115200_OR_48000",
            errors=tuple(errors),
        )

    return PassiveTapSafetyResult(
        safe=True,
        status=STATUS_VERIFIED_PASSIVE_RX_TAP,
        tx_line_connected=cfg.tx_line_connected,
        open_drain_tx_idle_1v8=cfg.open_drain_tx_idle_1v8,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        tx_bytes_attempted=0,
        io_voltage_v=cfg.io_voltage_v,
        baud_rate=cfg.baud_rate,
        ltc_cable_connected=cfg.ltc_cable_connected,
        bootrom_uart_boot_trigger_risk=False,
        recommended_action="PASSIVE_RX_ONLY_MONITORING_SAFE",
        errors=(),
    )


# ---------------------------------------------------------------------------
# 2. CXD90057 Boot-Stage State Machine (S0..S6) & 10-Signature Fault Triage
# ---------------------------------------------------------------------------

_STAGE_PATTERNS: Tuple[Tuple[str, re.Pattern[str]], ...] = (
    (
        "S0_BOOTROM_ENTRY",
        re.compile(r"(?:\bS0_BOOTROM_ENTRY\b|CXD90057\s+BootROM|ROM:\s*eMMC\s+boot|BootROM:\s+emmc)", re.I),
    ),
    (
        "S1_NBL_OPTEE_TRUSTZONE",
        re.compile(r"(?:\bS1_NBL_OPTEE_TRUSTZONE\b|\bNBL:|NBL\s+verified|OP-TEE|TrustZone|\btz_optee\b)", re.I),
    ),
    (
        "S2_UBOOT_BOOT_AB",
        re.compile(r"(?:\bS2_UBOOT_BOOT_AB\b|\bU-Boot\b|Starting\s+kernel|\bUBOOT\b)", re.I),
    ),
    (
        "S3_LINUX_4_9_337_SCEL",
        re.compile(r"(?:\bS3_LINUX_4_9_337_SCEL\b|4\.9\.337-scel\+?|\bLinux version 4\.9\.337\b)", re.I),
    ),
    (
        "S4_INIT2_SENTINEL_CHECK",
        re.compile(
            r"(?:\bS4_INIT2_SENTINEL_CHECK\b|/sbin/init2\b|\binit2:\s*(?!STAGE_B_CRASH_BREAKER)|INIT2\.SH\b|FX3_SAFE_STOCK\.FLG|DISABLE_STAGE_B\.TXT)",
            re.I,
        ),
    ),
    (
        "S5_STAGE_B_TMPFS_MOUNT",
        re.compile(
            r"(?:\bS5_STAGE_B_TMPFS_MOUNT\b|mount\s+-t\s+tmpfs|mount\s+--bind|/tmp/fx6_stage_b|stage_b\s+tmpfs\s+mounted)",
            re.I,
        ),
    ),
    (
        "S6_ICX1295_BIG6_READY",
        re.compile(
            r"(?:\bS6_ICX1295_BIG6_READY\b|icx1295.*big6\s+ready|BIG6_READY|appFw.*Big6.*ready|procam_app.*stage_b.*live)",
            re.I,
        ),
    ),
)

_WDT_RESET_PATTERN = re.compile(
    r"(?:CXD90057\s+WDT|watchdog\s+reset|WDT\s+reset|resetting\s+system|cold\s+reset\s+to\s+stock)",
    re.I,
)
_STOCK_FALLBACK_PATTERN = re.compile(
    r"(?:stock\s+FX3|v7\.02\s+stock|handoff\s+to\s+stock|exec\s+/sbin/init2\.stock|fallback.*stock|H2\s+stock)",
    re.I,
)

# 10 Triage Signature Matchers (evaluated in priority order)
_RE_OVERVOLTAGE_OR_FRAMING = re.compile(
    r"(?:3\.3V\s+UART|UART_OVERVOLTAGE_3V3|overvoltage|framing[-_\s]+noise\s+burst|repeated\s+framing\s+error|baud/level\s+mismatch)",
    re.I,
)
_RE_OTP_RPMB_REJECT = re.compile(
    r"(?:OTP/RPMB|RPMB\s+anti-rollback|anti-rollback\s+reject|rollback\s+index\s+mismatch|epoch\s+downgrade\s+rejected|OTP\s+fuse\s+epoch\s+mismatch)",
    re.I,
)
_RE_WBI2_MISMATCH = re.compile(
    r"(?:WBI2.*mismatch|WBI2\s+hibernate\s+snapshot\s+mismatch|invalid\s+WBI2|WBI3|hibdrv.*mismatch|FX6\s+WBI2)",
    re.I,
)
_RE_KERNEL_OOPS = re.compile(
    r"(?:Unable to handle kernel paging request|Internal error:\s*Oops|Kernel panic\s*-\s*not syncing)",
    re.I,
)
_RE_WF12_ASSERT = re.compile(
    r"(?:WF-12|00342260|icx1295.*wireless.*assert)",
    re.I,
)
_RE_PROCAM_CRASH_LOOP = re.compile(
    r"(?:procam_app.*3x.*15s|crash[-_\s]+loop\s+breaker|STAGE_B_CRASH_BREAKER|3/3\s+exits\s+in\s+15s|auto-unmount.*procam_app)",
    re.I,
)
_RE_INIT2_SH_SYNTAX_OR_HANG = re.compile(
    r"(?:INIT2\.SH.*syntax\s+error|syntax\s+error.*INIT2\.SH|INIT2\.SH.*hung|p1\s+INIT2\.SH\s+hang|/bin/sh:\s+INIT2\.SH)",
    re.I,
)
_RE_CPIO_SHA_MISMATCH = re.compile(
    r"(?:cpio.*SHA-?256\s+mismatch|stage[-_\s]?b\s+cpio.*mismatch|070701\s+magic\s+mismatch|SHA-?256\s+verify\s+failed.*fail-open)",
    re.I,
)
_RE_SD_SENTINEL = re.compile(
    r"(?:FX3_SAFE_STOCK\.FLG|DISABLE_STAGE_B\.TXT|SD[-_\s]*card\s+sentinel\s+bypass)",
    re.I,
)


def parse_cxd90057_boot_stages(log_data: Union[str, bytes, bytearray]) -> UartBootStageTrace:
    """Parse a `CXD90057` serial boot log across deterministic stages `S0..S6`."""
    text = _normalize_log_input(log_data)
    observed: List[str] = []
    line_numbers: Dict[str, int] = {}
    transitions: List[str] = []
    highest_idx = -1
    highest_stage: Optional[str] = None
    monotonic = True
    wdt_reset = bool(_WDT_RESET_PATTERN.search(text))
    stock_fallback = bool(_STOCK_FALLBACK_PATTERN.search(text))

    for lineno, line in enumerate(text.splitlines(), start=1):
        matched_in_line: List[str] = []
        for stage, pat in _STAGE_PATTERNS:
            if pat.search(line):
                matched_in_line.append(stage)
        for stage in matched_in_line:
            idx = STAGE_INDEX_MAP[stage]
            if observed:
                prev_stage = observed[-1]
                prev_idx = STAGE_INDEX_MAP[prev_stage]
                if idx < prev_idx and not wdt_reset:
                    monotonic = False
                if stage != prev_stage:
                    transitions.append(f"{prev_stage}->{stage}")
            if stage not in line_numbers:
                line_numbers[stage] = lineno
            if not observed or observed[-1] != stage:
                observed.append(stage)
            if idx > highest_idx:
                highest_idx = idx
                highest_stage = stage

    return UartBootStageTrace(
        stages_observed=tuple(observed),
        highest_stage_reached=highest_stage,
        highest_stage_index=highest_idx,
        stage_transitions=tuple(transitions),
        stage_line_numbers=line_numbers,
        wdt_reset_observed=wdt_reset,
        stock_fallback_observed=stock_fallback,
        valid_monotonic_progression=monotonic,
    )


def decode_uart_boot_log(
    log_data: Union[str, bytes, bytearray],
    *,
    tap: Optional[PassiveTapConfig] = None,
    active_tx_payload: bytes = b"",
    scenario_id: str = "AD_HOC_TRACE",
) -> UartBootDecodeResult:
    """Decode a passive `1.8V` RX-only UART trace (`S0..S6`) & prescribe minimal zero-write recovery."""
    text = _normalize_log_input(log_data)
    log_sha = sha256(text.encode("utf-8", errors="replace")).hexdigest()
    noise_ratio = _compute_framing_noise_ratio(text)
    tap_safety = audit_passive_rx_tap_safety(tap, active_tx_payload=active_tx_payload)
    trace = parse_cxd90057_boot_stages(text)

    # 1. Fail-closed active TX / unsafe TX line / LTC / undervoltage enforcement FIRST
    if not tap_safety.safe and tap_safety.status != OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN:
        return UartBootDecodeResult(
            passed=False,
            triage_classified=False,
            safe_to_operate=False,
            scenario_id=scenario_id,
            outcome_code=tap_safety.status,
            fault_detected=True,
            critical_hazard=tap_safety.bootrom_uart_boot_trigger_risk,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_3",
            recovery_action=tap_safety.recommended_action,
            prescribed_steps=(
                "1. Immediately block/abort host UART TX transmission.",
                "2. Disconnect Pin 7 (CAM_UART_RX) or assert open-drain 1.8V Hi-Z idle.",
                "3. Keep passive_tx_bytes_emitted == 0 and re-verify tap safety before monitoring.",
            ),
            matched_signature=f"PASSIVE_TAP_SAFETY_BLOCK:{tap_safety.status}",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=tap_safety.errors,
        )

    # 2. Check #10: 3.3V UART overvoltage warning / framing-noise burst (physical hardware hazard!)
    if (
        tap_safety.status == OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN
        or _RE_OVERVOLTAGE_OR_FRAMING.search(text)
        or noise_ratio >= FRAMING_NOISE_BURST_RATIO_THRESHOLD
    ):
        err_msgs = list(tap_safety.errors)
        if not err_msgs:
            err_msgs.append(
                f"3.3V UART overvoltage / framing-noise burst detected (noise_ratio={noise_ratio:.3f}); "
                "disconnect cable immediately."
            )
        return UartBootDecodeResult(
            passed=tap_safety.safe,
            triage_classified=True,
            safe_to_operate=False,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN,
            fault_detected=True,
            critical_hazard=True,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_3",
            recovery_action=OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN,
            prescribed_steps=(
                "1. IMMEDIATELY disconnect the 15-pin Multi-Port UART cable from the FX3 body.",
                "2. Measure idle voltage with camera disconnected: verify V_idle in [1.71V, 1.89V] open-drain.",
                "3. Verify -DOPEN_DRAIN=1 RP2040-Zero firmware (never 3.3V push-pull) and 115200/48000 baud before reconnecting.",
            ),
            matched_signature="3V3_OVERVOLTAGE_OR_FRAMING_NOISE_BURST",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=tuple(err_msgs),
        )

    # 3. Check #9: OTP/RPMB anti-rollback rejection signature
    if _RE_OTP_RPMB_REJECT.search(text):
        return UartBootDecodeResult(
            passed=True,
            triage_classified=True,
            safe_to_operate=True,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN,
            fault_detected=True,
            critical_hazard=True,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_4",
            recovery_action=OUTCOME_CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN,
            prescribed_steps=(
                "1. DO NOT attempt to downgrade or cross-flash nbl_a/b, tz/optee, uboot_a/b, or boot_a/b.",
                "2. Keep FX3 v7.02 stock bootchain intact and use volatile Stage-B tmpfs overlay only (otp_fuse_touches == 0).",
                "3. Verify host/donor version matrix with `verify-antirollback-guard` before any offline packaging.",
            ),
            matched_signature="OTP_RPMB_ANTIROLLBACK_REJECTION",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=(),
        )

    # 4. Check #7: WBI2 hibernate snapshot mismatch
    if _RE_WBI2_MISMATCH.search(text):
        return UartBootDecodeResult(
            passed=True,
            triage_classified=True,
            safe_to_operate=True,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_NEVER_CROSS_FLASH_FX6_WBI2,
            fault_detected=True,
            critical_hazard=False,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_0",
            recovery_action=OUTCOME_NEVER_CROSS_FLASH_FX6_WBI2,
            prescribed_steps=(
                "1. Perform Stock FX3 cold boot (remove battery >= 60s to discard stale WBI2 hibernate resume).",
                "2. NEVER cross-flash FX6 WBI2 (`nflasha5`, 1197 sections) onto FX3 (1399 sections).",
                "3. Re-verify Tier-0 backup p5 WBI2 integrity with `verify-emmc-forensics`.",
            ),
            matched_signature="WBI2_HIBERNATE_SNAPSHOT_MISMATCH",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=(),
        )

    # 5. Check #6: Kernel Oops / paging request during volatile H1 -> CXD90057 WDT wipes tmpfs -> stock H2
    if _RE_KERNEL_OOPS.search(text):
        return UartBootDecodeResult(
            passed=True,
            triage_classified=True,
            safe_to_operate=True,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_TIER0_COLD_REBOOT_WIPES_TMPFS,
            fault_detected=True,
            critical_hazard=False,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_0",
            recovery_action=OUTCOME_TIER0_COLD_REBOOT_WIPES_TMPFS,
            prescribed_steps=(
                "1. Allow CXD90057 hardware WDT reset (10s) or battery pull cold reboot to wipe volatile tmpfs H1.",
                "2. Confirm clean fallback to stock FX3 H2 (zero persistent eMMC writes occurred).",
                "3. Capture kernel Oops backtrace passively over RX-only UART before re-arming Stage-B.",
            ),
            matched_signature="KERNEL_PAGING_REQUEST_OR_OOPS_WDT",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=(),
        )

    # 6. Check #4: icx1295 WF-12 00342260 assertion
    if _RE_WF12_ASSERT.search(text):
        return UartBootDecodeResult(
            passed=True,
            triage_classified=True,
            safe_to_operate=True,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_NO_EMMC_FLASH_NEEDED,
            fault_detected=True,
            critical_hazard=False,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_0",
            recovery_action="ENABLE_P12_AIRPLANE_MODE_AND_TIER0_COLD_REBOOT",
            prescribed_steps=(
                "1. Do NOT flash eMMC (`NO_EMMC_FLASH_NEEDED`).",
                "2. Power off and remove NP-FZ100 battery >= 60s for Tier-0 Cold Reboot.",
                "3. Enable P12 Airplane-Mode shadow guard (`0x70d4` + BK4) before launching Stage-B Big6.",
            ),
            matched_signature="ICX1295_WF12_00342260_ASSERT",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=(),
        )

    # 7. Check #5: procam_app 3x-in-15s crash loop -> init2 auto-unmount + stock fallback
    if _RE_PROCAM_CRASH_LOOP.search(text):
        return UartBootDecodeResult(
            passed=True,
            triage_classified=True,
            safe_to_operate=True,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_TIER0_CRASH_BREAKER_RECOVERED,
            fault_detected=True,
            critical_hazard=False,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_0",
            recovery_action="INSPECT_VOLATILE_CRASH_LOG_AND_STAY_IN_STOCK_FX3",
            prescribed_steps=(
                "1. Verify init2 crash-breaker auto-unmounted Stage-B tmpfs bind mounts and booted stock FX3.",
                "2. Inspect `/tmp/stage_b_crash.cnt` / RX log to diagnose procam_app abort without eMMC writes.",
                "3. Fix Stage-B overlay bundle on host and re-verify with `verify-init2-escape`.",
            ),
            matched_signature="PROCAM_APP_3X_15S_CRASH_BREAKER",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=(),
        )

    # 8. Check #8: p1 INIT2.SH script syntax error or hang -> FX3_SAFE_STOCK.FLG SD OR Tier-1 p1 8.3 rollback
    if _RE_INIT2_SH_SYNTAX_OR_HANG.search(text):
        return UartBootDecodeResult(
            passed=True,
            triage_classified=True,
            safe_to_operate=True,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK,
            fault_detected=True,
            critical_hazard=False,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_1",
            recovery_action="INSERT_FX3_SAFE_STOCK_FLG_SD_OR_TIER1_P1_83_POINTER_ROLLBACK",
            prescribed_steps=(
                "1. Place empty `FX3_SAFE_STOCK.FLG` sentinel on SD/CFexpress card and cold-boot to bypass Stage-B.",
                "2. If `INIT2.SH` fails before sentinel check, run Tier-1 Multi-Port/Jiritsu atomic `p1` 8.3 pointer rollback (`INIT2.SH` <-> `INIT2BAK.SH`).",
                "3. Validate fixed `INIT2.SH` syntax in sandbox via `verify-init2-escape` before re-arming.",
            ),
            matched_signature="P1_INIT2_SH_SYNTAX_OR_HANG",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=(),
        )

    # 9. Check #3: Stage-B cpio SHA-256 mismatch at S4 -> automatic fail-open handoff to stock FX3
    if _RE_CPIO_SHA_MISMATCH.search(text):
        return UartBootDecodeResult(
            passed=True,
            triage_classified=True,
            safe_to_operate=True,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_CLEAN_HASH_FAILOPEN_STOCK_BOOT,
            fault_detected=True,
            critical_hazard=False,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_0",
            recovery_action="REBUILD_STAGE_B_CPIO_AND_VERIFY_SHA256_ON_HOST",
            prescribed_steps=(
                "1. Stock FX3 boot proceeded automatically via S4 fail-open hash guard (zero brick risk).",
                "2. Regenerate Stage-B `.cpio` archive and matching `.sha256` sidecar on host.",
                "3. Re-verify archive `070701` magic and digest before next Stage-B rehearsal.",
            ),
            matched_signature="STAGE_B_CPIO_SHA256_MISMATCH_FAILOPEN",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=(),
        )

    # 10. Check #2: Clean FX3_SAFE_STOCK.FLG SD-card sentinel bypass at S4 -> 100% stock FX3 v7.02 boot
    if _RE_SD_SENTINEL.search(text):
        return UartBootDecodeResult(
            passed=True,
            triage_classified=True,
            safe_to_operate=True,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_CLEAN_SD_SENTINEL_STOCK_ESCAPE,
            fault_detected=False,
            critical_hazard=False,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="TIER_0",
            recovery_action="STOCK_FX3_V702_ACTIVE_REMOVE_SENTINEL_TO_REARM",
            prescribed_steps=(
                "1. Confirmed clean S4 SD-card sentinel bypass to 100% stock FX3 v7.02 (zero Stage-B mounts).",
                "2. Keep `FX3_SAFE_STOCK.FLG` in place for stock shooting, or remove it when ready to test Stage-B.",
            ),
            matched_signature="SD_SENTINEL_FX3_SAFE_STOCK_ESCAPE",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=(),
        )

    # 11. Check #1: Clean Stage-B H1 boot reaching S6_ICX1295_BIG6_READY
    if (
        trace.highest_stage_reached == "S6_ICX1295_BIG6_READY"
        and trace.valid_monotonic_progression
        and "S5_STAGE_B_TMPFS_MOUNT" in trace.stages_observed
    ):
        return UartBootDecodeResult(
            passed=True,
            triage_classified=True,
            safe_to_operate=True,
            scenario_id=scenario_id,
            outcome_code=OUTCOME_HEALTHY_STAGE_B_LIVE,
            fault_detected=False,
            critical_hazard=False,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_tier="NONE",
            recovery_action="NONE_STAGE_B_LIVE_HEALTHY",
            prescribed_steps=(
                "1. Stage-B volatile H1 reached S6_ICX1295_BIG6_READY cleanly.",
                "2. Zero persistent eMMC writes performed; cold reboot restores stock FX3 H2.",
            ),
            matched_signature="HEALTHY_S0_TO_S6_STAGE_B_LIVE",
            framing_noise_ratio=noise_ratio,
            passive_tap_safety=tap_safety,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            emmc_write_bytes=0,
            log_sha256=log_sha,
            errors=(),
        )

    # 12. Unknown or incomplete trace -> fail closed
    return UartBootDecodeResult(
        passed=False,
        triage_classified=False,
        safe_to_operate=tap_safety.safe,
        scenario_id=scenario_id,
        outcome_code=OUTCOME_UNKNOWN_OR_INCOMPLETE_BOOT_LOG,
        fault_detected=True,
        critical_hazard=False,
        highest_stage_reached=trace.highest_stage_reached,
        stages_observed=trace.stages_observed,
        stage_transitions=trace.stage_transitions,
        valid_monotonic_progression=trace.valid_monotonic_progression,
        recovery_tier="TIER_0",
        recovery_action="CAPTURE_FULL_PASSIVE_1V8_RX_BOOT_LOG_BEFORE_ACTION",
        prescribed_steps=(
            "1. Boot log did not reach S6 or match a known fault signature.",
            "2. Keep persistent eMMC writes disabled and capture a complete 115200/48000 passive RX log.",
        ),
        matched_signature="UNKNOWN_OR_INCOMPLETE_BOOT_LOG",
        framing_noise_ratio=noise_ratio,
        passive_tap_safety=tap_safety,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        emmc_write_bytes=0,
        log_sha256=log_sha,
        errors=("Unrecognized or incomplete CXD90057 boot log.",),
    )


def build_default_10_uart_scenarios() -> Tuple[UartBootScenarioSpec, ...]:
    """Build deterministic clean-room serial boot traces for all 10 CXD90057 fault/live scenarios."""
    rx_only_tap = PassiveTapConfig(tx_line_connected=False, open_drain_tx_idle_1v8=True, io_voltage_v=1.80)
    od_idle_tap = PassiveTapConfig(tx_line_connected=True, open_drain_tx_idle_1v8=True, io_voltage_v=1.80)

    return (
        UartBootScenarioSpec(
            scenario_number=1,
            scenario_id="U01_HEALTHY_STAGE_B_LIVE",
            expected_outcome_code=OUTCOME_HEALTHY_STAGE_B_LIVE,
            expected_highest_stage="S6_ICX1295_BIG6_READY",
            expected_recovery_tier="NONE",
            tap=rx_only_tap,
            log_text=(
                "[0.001] S0_BOOTROM_ENTRY: CXD90057 BootROM eMMC boot_a\n"
                "[0.045] S1_NBL_OPTEE_TRUSTZONE: NBL verified, OP-TEE TrustZone initialized\n"
                "[0.180] S2_UBOOT_BOOT_AB: U-Boot selecting boot_a, Starting kernel\n"
                "[0.520] S3_LINUX_4_9_337_SCEL: Linux version 4.9.337-scel+ #1 SMP PREEMPT aarch64\n"
                "[1.110] S4_INIT2_SENTINEL_CHECK: /sbin/init2 no sentinel; stage_b_overlay SHA-256 OK\n"
                "[1.340] S5_STAGE_B_TMPFS_MOUNT: mount -t tmpfs /tmp/fx6_stage_b; mount --bind OK\n"
                "[2.950] S6_ICX1295_BIG6_READY: icx1295 appFw Big6 ready (Stage-B H1 live)\n"
            ),
        ),
        UartBootScenarioSpec(
            scenario_number=2,
            scenario_id="U02_SD_SENTINEL_STOCK_ESCAPE",
            expected_outcome_code=OUTCOME_CLEAN_SD_SENTINEL_STOCK_ESCAPE,
            expected_highest_stage="S4_INIT2_SENTINEL_CHECK",
            expected_recovery_tier="TIER_0",
            tap=rx_only_tap,
            log_text=(
                "[0.001] S0_BOOTROM_ENTRY: CXD90057 BootROM eMMC boot_a\n"
                "[0.044] S1_NBL_OPTEE_TRUSTZONE: NBL verified, OP-TEE OK\n"
                "[0.175] S2_UBOOT_BOOT_AB: U-Boot boot_a Starting kernel\n"
                "[0.515] S3_LINUX_4_9_337_SCEL: Linux version 4.9.337-scel+ #1 SMP\n"
                "[1.090] S4_INIT2_SENTINEL_CHECK: /sbin/init2 detected /media/slot_a/FX3_SAFE_STOCK.FLG -> exec /sbin/init2.stock (100% stock FX3 v7.02)\n"
            ),
        ),
        UartBootScenarioSpec(
            scenario_number=3,
            scenario_id="U03_CPIO_SHA256_MISMATCH_FAILOPEN",
            expected_outcome_code=OUTCOME_CLEAN_HASH_FAILOPEN_STOCK_BOOT,
            expected_highest_stage="S4_INIT2_SENTINEL_CHECK",
            expected_recovery_tier="TIER_0",
            tap=od_idle_tap,
            log_text=(
                "[0.001] S0_BOOTROM_ENTRY: CXD90057 BootROM eMMC boot_a\n"
                "[0.044] S1_NBL_OPTEE_TRUSTZONE: NBL + OP-TEE OK\n"
                "[0.179] S2_UBOOT_BOOT_AB: U-Boot boot_a Starting kernel\n"
                "[0.518] S3_LINUX_4_9_337_SCEL: Linux version 4.9.337-scel+ #1 SMP\n"
                "[1.120] S4_INIT2_SENTINEL_CHECK: stage_b cpio SHA-256 mismatch (070701 verify failed) -> automatic fail-open handoff to stock FX3\n"
            ),
        ),
        UartBootScenarioSpec(
            scenario_number=4,
            scenario_id="U04_ICX1295_WF12_00342260_ASSERT",
            expected_outcome_code=OUTCOME_NO_EMMC_FLASH_NEEDED,
            expected_highest_stage="S5_STAGE_B_TMPFS_MOUNT",
            expected_recovery_tier="TIER_0",
            tap=rx_only_tap,
            log_text=(
                "[0.001] S0_BOOTROM_ENTRY: CXD90057 BootROM eMMC boot_a\n"
                "[0.045] S1_NBL_OPTEE_TRUSTZONE: NBL + OP-TEE OK\n"
                "[0.181] S2_UBOOT_BOOT_AB: U-Boot boot_a Starting kernel\n"
                "[0.522] S3_LINUX_4_9_337_SCEL: Linux version 4.9.337-scel+ #1 SMP\n"
                "[1.105] S4_INIT2_SENTINEL_CHECK: /sbin/init2 Stage-B hash OK\n"
                "[1.345] S5_STAGE_B_TMPFS_MOUNT: mount -t tmpfs /tmp/fx6_stage_b OK\n"
                "[2.410] icx1295 wireless assert: WF-12 00342260 (6L+9S LED) without P12 Airplane-Mode shadow\n"
            ),
        ),
        UartBootScenarioSpec(
            scenario_number=5,
            scenario_id="U05_PROCAM_3X_15S_CRASH_BREAKER",
            expected_outcome_code=OUTCOME_TIER0_CRASH_BREAKER_RECOVERED,
            expected_highest_stage="S5_STAGE_B_TMPFS_MOUNT",
            expected_recovery_tier="TIER_0",
            tap=rx_only_tap,
            log_text=(
                "[0.001] S0_BOOTROM_ENTRY: CXD90057 BootROM eMMC boot_a\n"
                "[0.045] S1_NBL_OPTEE_TRUSTZONE: NBL + OP-TEE OK\n"
                "[0.180] S2_UBOOT_BOOT_AB: U-Boot boot_a Starting kernel\n"
                "[0.520] S3_LINUX_4_9_337_SCEL: Linux version 4.9.337-scel+ #1 SMP\n"
                "[1.100] S4_INIT2_SENTINEL_CHECK: /sbin/init2 Stage-B armed\n"
                "[1.330] S5_STAGE_B_TMPFS_MOUNT: mount -t tmpfs /tmp/fx6_stage_b OK\n"
                "[4.820] init2: STAGE_B_CRASH_BREAKER procam_app 3/3 exits in 15s -> auto-unmount + fallback to stock FX3\n"
            ),
        ),
        UartBootScenarioSpec(
            scenario_number=6,
            scenario_id="U06_KERNEL_PAGING_OOPS_WDT_WIPES_H1",
            expected_outcome_code=OUTCOME_TIER0_COLD_REBOOT_WIPES_TMPFS,
            expected_highest_stage="S5_STAGE_B_TMPFS_MOUNT",
            expected_recovery_tier="TIER_0",
            tap=rx_only_tap,
            log_text=(
                "[0.001] S0_BOOTROM_ENTRY: CXD90057 BootROM eMMC boot_a\n"
                "[0.045] S1_NBL_OPTEE_TRUSTZONE: NBL + OP-TEE OK\n"
                "[0.180] S2_UBOOT_BOOT_AB: U-Boot boot_a Starting kernel\n"
                "[0.520] S3_LINUX_4_9_337_SCEL: Linux version 4.9.337-scel+ #1 SMP\n"
                "[1.100] S4_INIT2_SENTINEL_CHECK: /sbin/init2 Stage-B armed\n"
                "[1.330] S5_STAGE_B_TMPFS_MOUNT: mount -t tmpfs /tmp/fx6_stage_b OK\n"
                "[3.012] Unable to handle kernel paging request at virtual address 00000000deadbeef\n"
                "[3.015] Internal error: Oops: 96000005 [#1] PREEMPT SMP\n"
                "[13.020] CXD90057 WDT reset wipes volatile RAM -> booting stock H2\n"
            ),
        ),
        UartBootScenarioSpec(
            scenario_number=7,
            scenario_id="U07_WBI2_HIBERNATE_MISMATCH",
            expected_outcome_code=OUTCOME_NEVER_CROSS_FLASH_FX6_WBI2,
            expected_highest_stage="S2_UBOOT_BOOT_AB",
            expected_recovery_tier="TIER_0",
            tap=rx_only_tap,
            log_text=(
                "[0.001] S0_BOOTROM_ENTRY: CXD90057 BootROM eMMC boot_a\n"
                "[0.045] S1_NBL_OPTEE_TRUSTZONE: NBL + OP-TEE OK\n"
                "[0.182] S2_UBOOT_BOOT_AB: U-Boot probing nflasha5 WBI2 hibernate snapshot mismatch (FX6 WBI2 1197 != FX3 1399)\n"
            ),
        ),
        UartBootScenarioSpec(
            scenario_number=8,
            scenario_id="U08_P1_INIT2_SH_SYNTAX_OR_HANG",
            expected_outcome_code=OUTCOME_TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK,
            expected_highest_stage="S4_INIT2_SENTINEL_CHECK",
            expected_recovery_tier="TIER_1",
            tap=rx_only_tap,
            log_text=(
                "[0.001] S0_BOOTROM_ENTRY: CXD90057 BootROM eMMC boot_a\n"
                "[0.045] S1_NBL_OPTEE_TRUSTZONE: NBL + OP-TEE OK\n"
                "[0.180] S2_UBOOT_BOOT_AB: U-Boot boot_a Starting kernel\n"
                "[0.520] S3_LINUX_4_9_337_SCEL: Linux version 4.9.337-scel+ #1 SMP\n"
                "[1.102] S4_INIT2_SENTINEL_CHECK: /bin/sh: INIT2.SH line 14: syntax error: unexpected end of file\n"
            ),
        ),
        UartBootScenarioSpec(
            scenario_number=9,
            scenario_id="U09_OTP_RPMB_ANTIROLLBACK_REJECT",
            expected_outcome_code=OUTCOME_CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN,
            expected_highest_stage="S1_NBL_OPTEE_TRUSTZONE",
            expected_recovery_tier="TIER_4",
            tap=rx_only_tap,
            log_text=(
                "[0.001] S0_BOOTROM_ENTRY: CXD90057 BootROM eMMC boot_a\n"
                "[0.042] S1_NBL_OPTEE_TRUSTZONE: OTP/RPMB anti-rollback rejection: nbl_a epoch 2 < fuse epoch 5\n"
            ),
        ),
        UartBootScenarioSpec(
            scenario_number=10,
            scenario_id="U10_3V3_OVERVOLTAGE_FRAMING_BURST",
            expected_outcome_code=OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN,
            expected_highest_stage=None,
            expected_recovery_tier="TIER_3",
            tap=rx_only_tap,
            log_text=(
                "UART_OVERVOLTAGE_3V3 WARNING: 3.3V UART push-pull / framing-noise burst detected on Pin 8: "
                "\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\ufffd\n"
            ),
        ),
    )


def run_uart_boot_decoder_10_scenario_suite(
    *,
    verification_mode: str = "CLEAN_ROOM_SYNTHETIC",
) -> UartDecoderSuiteResult:
    """Execute all 10 UART boot-stage triage scenarios plus TX=0 & 3.3V safety enforcement probes."""
    scenarios = build_default_10_uart_scenarios()
    results: List[UartBootDecodeResult] = []
    errors: List[str] = []

    for spec in scenarios:
        res = decode_uart_boot_log(spec.log_text, tap=spec.tap, scenario_id=spec.scenario_id)
        results.append(res)
        if not res.triage_classified:
            errors.append(f"{spec.scenario_id}: failed to classify")
        if res.outcome_code != spec.expected_outcome_code:
            errors.append(
                f"{spec.scenario_id}: expected outcome {spec.expected_outcome_code}, got {res.outcome_code}"
            )
        if res.highest_stage_reached != spec.expected_highest_stage:
            errors.append(
                f"{spec.scenario_id}: expected highest stage {spec.expected_highest_stage}, got {res.highest_stage_reached}"
            )
        if res.recovery_tier != spec.expected_recovery_tier:
            errors.append(
                f"{spec.scenario_id}: expected tier {spec.expected_recovery_tier}, got {res.recovery_tier}"
            )
        if res.passive_tx_bytes_emitted != 0:
            errors.append(f"{spec.scenario_id}: passive_tx_bytes_emitted != 0")
        if res.persistent_emmc_writes_authorized is not False or res.persistent_write_release is not False:
            errors.append(f"{spec.scenario_id}: persistent write lock violated")

    # Probe 1: Active TX injection must be rejected fail-closed with passive_tx_bytes_emitted == 0
    tx_probe = decode_uart_boot_log(
        scenarios[0].log_text,
        tap=PassiveTapConfig(tx_line_connected=True, open_drain_tx_idle_1v8=True, tx_bytes_attempted=4),
        active_tx_payload=b"UB\x00\x01",
        scenario_id="PROBE_ACTIVE_TX_INJECTION",
    )
    active_tx_ok = (
        (not tx_probe.passed)
        and (not tx_probe.safe_to_operate)
        and tx_probe.outcome_code == OUTCOME_BLOCKED_ACTIVE_TX_INJECTION
        and tx_probe.passive_tx_bytes_emitted == 0
    )
    if not active_tx_ok:
        errors.append("Active TX injection probe was not rejected fail-closed.")

    # Probe 2: Connected TX line without open-drain 1.8V idle must be rejected fail-closed
    unsafe_tx_probe = decode_uart_boot_log(
        scenarios[0].log_text,
        tap=PassiveTapConfig(tx_line_connected=True, open_drain_tx_idle_1v8=False, io_voltage_v=1.80),
        scenario_id="PROBE_UNSAFE_PUSH_PULL_TX",
    )
    unsafe_tx_ok = (
        (not unsafe_tx_probe.passed)
        and (not unsafe_tx_probe.safe_to_operate)
        and unsafe_tx_probe.outcome_code == OUTCOME_BLOCKED_UNSAFE_TX_LINE
        and unsafe_tx_probe.passive_tx_bytes_emitted == 0
    )
    if not unsafe_tx_ok:
        errors.append("Unsafe TX line probe was not rejected fail-closed.")

    # Probe 3: 3.3V IO voltage tap config must immediately trigger DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN
    ov_probe = decode_uart_boot_log(
        scenarios[0].log_text,
        tap=PassiveTapConfig(tx_line_connected=False, open_drain_tx_idle_1v8=True, io_voltage_v=3.30),
        scenario_id="PROBE_3V3_TAP_VOLTAGE",
    )
    ov_ok = (
        (not ov_probe.passed)
        and (not ov_probe.safe_to_operate)
        and ov_probe.critical_hazard
        and ov_probe.outcome_code == OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN
        and ov_probe.passive_tx_bytes_emitted == 0
    )
    if not ov_ok:
        errors.append("3.3V tap overvoltage probe was not rejected with DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN.")

    scenarios_passed = sum(
        1
        for spec, res in zip(scenarios, results)
        if (
            res.triage_classified
            and res.outcome_code == spec.expected_outcome_code
            and res.highest_stage_reached == spec.expected_highest_stage
            and res.recovery_tier == spec.expected_recovery_tier
            and res.passive_tx_bytes_emitted == 0
        )
    )
    all_ok = (
        len(errors) == 0
        and scenarios_passed == len(scenarios) == 10
        and active_tx_ok
        and unsafe_tx_ok
        and ov_ok
        and PASSIVE_TX_BYTES_EMITTED == 0
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and PHYSICAL_DEVICE_WRITES == 0
    )
    return UartDecoderSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_UART_DECODER_SUITE if all_ok else STATUS_FAIL_UART_DECODER_SUITE,
        verification_mode=verification_mode,
        scenarios_total=len(scenarios),
        scenarios_passed=scenarios_passed,
        active_tx_rejection_verified=active_tx_ok,
        unsafe_tx_line_rejection_verified=unsafe_tx_ok,
        overvoltage_3v3_tap_rejection_verified=ov_ok,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        scenario_results=tuple(results),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 3. Unified 7-Pillar Master Readiness Audit (`run_recovery_master_suite`)
# ---------------------------------------------------------------------------


def _run_pillar_1_macos_usb_transport(verification_mode: str) -> PillarAuditSummary:
    t0 = time.monotonic()
    errors: List[str] = []

    session = MacOSUSBTransportSession(macos_major=26)
    session.attach_msc(vid_pid=FX3_MSC_VID_PID, model_name="ILME-FX3", model_id=FX3_MODEL_ID)
    q_ok, q_msg = session.wait_for_msc_quiescence(waited_ms=400, driver_quiescent=True)
    if not q_ok:
        errors.append(f"macOS quiescence failed: {q_msg}")

    claim = session.claim_interface([K_IORETURN_EXCLUSIVE_ACCESS, K_IORETURN_SUCCESS], use_iousbhost_fallback=True)
    if not claim.success or claim.active_backend != "IOUSBHost" or claim.exclusive_access_retries != 1:
        errors.append("macOS 0xe00002be IOUSBHost claim fallback failed")

    # USB STALL non-retransmit probe on separate session
    stall_sess = MacOSUSBTransportSession(macos_major=26)
    stall_sess.attach_msc()
    stall_sess.wait_for_msc_quiescence(waited_ms=400, driver_quiescent=True)
    stall_sess.claim_interface([K_IORETURN_SUCCESS])
    stall_res = stall_sess.send_vendor_control(usb_stall=True)
    if stall_res.success or stall_res.retransmit_count != 0 or stall_sess.state != TransportState.STALL_ABORTED_NO_RETRANSMIT:
        errors.append("USB STALL non-retransmit rule failed")

    vc = session.send_vendor_control(usb_stall=False)
    if not vc.success:
        errors.extend(vc.errors)

    senser_v1 = session.authenticate_senser(SenserChallenge(senser_version=1, model_name="ILME-FX3", model_id=FX3_MODEL_ID))
    if not senser_v1.supported or senser_v1.service_vid_pid != SONY_SERVICE_VID_PID:
        errors.append("Senser v1 FX3 authentication failed")

    # Senser v2 must fail closed
    v2_sess = MacOSUSBTransportSession(macos_major=26)
    v2_sess.attach_msc()
    v2_sess.wait_for_msc_quiescence(waited_ms=400, driver_quiescent=True)
    v2_sess.claim_interface([K_IORETURN_SUCCESS])
    v2_sess.send_vendor_control()
    senser_v2 = v2_sess.authenticate_senser(
        SenserChallenge(senser_version=2, auth_scheme="rsa_signature", model_name="ILCE-7M5", rsa_modulus_bits=2048)
    )
    if senser_v2.supported or not senser_v2.fail_closed:
        errors.append("Senser v2 fail-closed check failed")

    # Jiritsu read-only allowed vs destructive blocked
    ro_audit = session.audit_jiritsu_flow(
        [
            JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_MOUNT),
            JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_SET_FILE_PATH, "/tmp/jiritsu/p1.bin"),
            JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_GET_FILE),
            JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_GET_FILE2),
        ]
    )
    rw_blocked = session.audit_jiritsu_flow(
        [
            JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_FORMAT),
            JiritsuCommand(JIRITSU_PFUNC, JIRITSU_BLOCK, JIRITSU_CODE_FIRMUP),
        ]
    )
    if not ro_audit.allowed:
        errors.extend(ro_audit.errors)
    if rw_blocked.allowed or ALLOW_PERSISTENT_JIRITSU_WRITES or ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS:
        errors.append("Destructive Jiritsu commands were not blocked fail-closed")

    metrics: Dict[str, Any] = {
        "fx3_msc_vid_pid": FX3_MSC_VID_PID,
        "service_vid_pid": SONY_SERVICE_VID_PID,
        "claim_backend": claim.active_backend,
        "backoff_schedule_ms": claim.backoff_schedule_ms,
        "stall_retransmit_count": stall_res.retransmit_count,
        "senser_v1_rounds": senser_v1.rounds_required,
        "senser_v2_fail_closed": senser_v2.fail_closed,
        "jiritsu_ro_permitted": ro_audit.permitted_codes,
        "jiritsu_destructive_blocked": rw_blocked.blocked_codes,
        "allow_persistent_jiritsu_writes": ALLOW_PERSISTENT_JIRITSU_WRITES,
        "allow_destructive_jiritsu_commands": ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
    }
    passed = len(errors) == 0
    return PillarAuditSummary(
        pillar_number=1,
        pillar_id="macos_usb_transport_guard",
        module_name="fx3_recovery.macos_usb_transport_guard",
        passed=passed,
        status="VERIFIED_MACOS_USB_TRANSPORT_GUARD" if passed else "FAIL_MACOS_USB_TRANSPORT_GUARD",
        verification_mode=verification_mode,
        summary_metrics=metrics,
        deterministic_digest_sha256=_canonical_sha256({"pillar": "macos_usb_transport_guard", "mode": verification_mode, "metrics": metrics, "passed": passed}),
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


def _run_pillar_2_rp2040_fixture(force_clean_room: Optional[bool]) -> PillarAuditSummary:
    t0 = time.monotonic()
    rep = run_rp2040_multiport_fixture_selftest(force_clean_room=force_clean_room)
    errors = list(rep.errors)
    if rep.camera_connected is not False:
        errors.append("RP2040 bench fixture violated camera_connected == False")
    if rep.persistent_emmc_writes_authorized is not False:
        errors.append("RP2040 bench fixture violated persistent_emmc_writes_authorized == False")
    passed = bool(rep.all_passed) and len(errors) == 0
    metrics: Dict[str, Any] = {
        "board": rep.board,
        "camera_connected": rep.camera_connected,
        "donor_p1_sha256": rep.donor_p1_sha256,
        "pio_dividers_count": len(rep.pio_dividers),
        "loopback_48000_exact": rep.loopback_48000.bit_exact_match,
        "loopback_115200_exact": rep.loopback_115200.bit_exact_match,
        "glitch_rejection_verified": rep.glitch_rejection_verified,
        "framing_error_rejection_verified": rep.framing_error_rejection_verified,
        "persistent_emmc_writes_authorized": rep.persistent_emmc_writes_authorized,
    }
    return PillarAuditSummary(
        pillar_number=2,
        pillar_id="rp2040_multiport_fixture_selftest",
        module_name="fx3_recovery.rp2040_multiport_fixture_selftest",
        passed=passed,
        status=rep.status,
        verification_mode=rep.verification_mode,
        summary_metrics=metrics,
        deterministic_digest_sha256=_canonical_sha256({"pillar": "rp2040_multiport_fixture_selftest", "mode": rep.verification_mode, "status": rep.status, "metrics": metrics, "passed": passed}),
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


def _run_pillar_3_init2_escape(force_clean_room: Optional[bool]) -> PillarAuditSummary:
    t0 = time.monotonic()
    rep = run_init2_escape_and_watchdog_suite(force_clean_room=force_clean_room)
    errors = list(rep.errors)
    if rep.escape_sandbox_suite.drills_passed != 7 or rep.escape_sandbox_suite.drills_total != 7:
        errors.append(
            f"Expected 7/7 init2 escape drills, got {rep.escape_sandbox_suite.drills_passed}/{rep.escape_sandbox_suite.drills_total}"
        )
    if rep.watchdog_suite.scenarios_passed != 5 or rep.watchdog_suite.scenarios_total != 5:
        errors.append(
            f"Expected 5/5 CXD90057 WDT drills, got {rep.watchdog_suite.scenarios_passed}/{rep.watchdog_suite.scenarios_total}"
        )
    if rep.physical_writes != 0 or rep.persistent_emmc_writes_authorized is not False or rep.persistent_write_release is not False:
        errors.append("init2 escape suite violated zero-write safety invariants")
    passed = bool(rep.all_passed) and len(errors) == 0
    # Exclude ephemeral trace_lines temp paths so digest is 100% deterministic
    metrics: Dict[str, Any] = {
        "donor_p1_sha256": rep.donor_p1_sha256,
        "script_sha256": rep.escape_sandbox_suite.script_sha256,
        "escape_drills_passed": rep.escape_sandbox_suite.drills_passed,
        "escape_drills_total": rep.escape_sandbox_suite.drills_total,
        "wdt_scenarios_passed": rep.watchdog_suite.scenarios_passed,
        "wdt_scenarios_total": rep.watchdog_suite.scenarios_total,
        "fat12_swap_roundtrip_exact": rep.fat12_atomic_swap.roundtrip_sha256_exact,
        "fat16_swap_roundtrip_exact": rep.fat16_atomic_swap.roundtrip_sha256_exact,
        "physical_writes": rep.physical_writes,
        "persistent_emmc_writes_authorized": rep.persistent_emmc_writes_authorized,
        "persistent_write_release": rep.persistent_write_release,
    }
    return PillarAuditSummary(
        pillar_number=3,
        pillar_id="init2_escape_and_watchdog_simulator",
        module_name="fx3_recovery.init2_escape_and_watchdog_simulator",
        passed=passed,
        status=rep.status,
        verification_mode=rep.verification_mode,
        summary_metrics=metrics,
        deterministic_digest_sha256=_canonical_sha256({"pillar": "init2_escape_and_watchdog_simulator", "mode": rep.verification_mode, "status": rep.status, "metrics": metrics, "passed": passed}),
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


def _run_pillar_4_tier0_backup(force_clean_room: Optional[bool]) -> PillarAuditSummary:
    t0 = time.monotonic()
    rep = run_tier0_backup_parity_suite(force_clean_room=force_clean_room)
    errors = list(rep.errors)
    if not rep.heal_1_silent_bitrot.passed:
        errors.append("GF(256) P+Q 1-shard silent bit-rot heal failed")
    if rep.anti_transplant_cross_body_blocked.allowed:
        errors.append("Cross-body anti-transplant lock failed to block Body-A -> Body-B")
    if rep.reject_3_losses.passed:
        errors.append("3-shard quorum loss did not fail closed")
    if rep.physical_device_writes != 0 or rep.persistent_emmc_writes_authorized is not False or rep.persistent_write_release is not False:
        errors.append("Tier-0 backup suite violated zero-write safety invariants")
    passed = bool(rep.all_passed) and len(errors) == 0
    metrics: Dict[str, Any] = {
        "donor_p1_sha256": rep.donor_p1_sha256,
        "donor_p5_wbi2_sha256": rep.donor_p5_wbi2_sha256,
        "partition_count": rep.bundle_validation.partition_count,
        "body_identity_binding_sha256": rep.manifest.body_identity_binding_sha256,
        "heal_1_erasure_exact": rep.heal_1_erasure.bit_exact_match,
        "heal_2_erasures_exact": rep.heal_2_erasures.bit_exact_match,
        "heal_1_bitrot_exact": rep.heal_1_silent_bitrot.bit_exact_match,
        "cross_body_blocked": not rep.anti_transplant_cross_body_blocked.allowed,
        "physical_device_writes": rep.physical_device_writes,
        "persistent_emmc_writes_authorized": rep.persistent_emmc_writes_authorized,
        "persistent_write_release": rep.persistent_write_release,
    }
    return PillarAuditSummary(
        pillar_number=4,
        pillar_id="tier0_backup_parity_and_manifest_guard",
        module_name="fx3_recovery.tier0_backup_parity_and_manifest_guard",
        passed=passed,
        status=rep.status,
        verification_mode=rep.verification_mode,
        summary_metrics=metrics,
        deterministic_digest_sha256=_canonical_sha256({"pillar": "tier0_backup_parity_and_manifest_guard", "mode": rep.verification_mode, "status": rep.status, "metrics": metrics, "passed": passed}),
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


def _run_pillar_5_antirollback_guard(force_clean_room: Optional[bool]) -> PillarAuditSummary:
    t0 = time.monotonic()
    rep = run_antirollback_and_byof_guard_suite(force_clean_room=force_clean_room)
    errors = list(rep.errors)
    if rep.otp_fuse_touches != 0 or rep.rpmb_counter_increments != 0:
        errors.append("Anti-rollback guard violated zero OTP/RPMB touch invariant")
    if rep.ext_csd_boot_perm_wp_blocked.safe or rep.ext_csd_user_perm_wp_blocked.safe or rep.mmc_perm_wp_cmd_blocked.safe:
        errors.append("EXT_CSD permanent write-protect trap was not blocked")
    if rep.physical_device_writes != 0 or rep.persistent_emmc_writes_authorized is not False or rep.persistent_write_release is not False:
        errors.append("Anti-rollback guard violated zero-write safety invariants")
    passed = bool(rep.all_passed) and len(errors) == 0
    metrics: Dict[str, Any] = {
        "fx3_wbi2_sections": rep.donor_snapshot.fx3_wbi2_sections,
        "fx6_wbi2_sections": rep.donor_snapshot.fx6_wbi2_sections,
        "fx3_kernel_release": rep.donor_snapshot.fx3_kernel_release,
        "fx6_kernel_release": rep.donor_snapshot.fx6_kernel_release,
        "otp_fuse_touches": rep.otp_fuse_touches,
        "rpmb_counter_increments": rep.rpmb_counter_increments,
        "antirollback_brick_risk": rep.antirollback_brick_risk,
        "ext_csd_perm_wp_blocked": (
            not rep.ext_csd_boot_perm_wp_blocked.safe
            and not rep.ext_csd_user_perm_wp_blocked.safe
            and not rep.mmc_perm_wp_cmd_blocked.safe
        ),
        "physical_device_writes": rep.physical_device_writes,
        "persistent_emmc_writes_authorized": rep.persistent_emmc_writes_authorized,
        "persistent_write_release": rep.persistent_write_release,
    }
    return PillarAuditSummary(
        pillar_number=5,
        pillar_id="firmware_updata_and_antirollback_guard",
        module_name="fx3_recovery.firmware_updata_and_antirollback_guard",
        passed=passed,
        status=rep.status,
        verification_mode=rep.verification_mode,
        summary_metrics=metrics,
        deterministic_digest_sha256=_canonical_sha256({"pillar": "firmware_updata_and_antirollback_guard", "mode": rep.verification_mode, "status": rep.status, "metrics": metrics, "passed": passed}),
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


def _run_pillar_6_unbrick_ladder(force_clean_room: Optional[bool]) -> PillarAuditSummary:
    t0 = time.monotonic()
    rep = run_unbrick_ladder_and_capsule_suite(force_clean_room=force_clean_room)
    errors = list(rep.errors)
    if rep.scenarios_passed != 12 or rep.scenario_count != 12:
        errors.append(f"Expected 12/12 unbrick ladder scenarios, got {rep.scenarios_passed}/{rep.scenario_count}")
    if rep.wbi_mutation_bytes != 0 or rep.emmc_write_bytes != 0 or rep.persistent_emmc_writes_authorized is not False:
        errors.append("Unbrick ladder violated zero-write safety invariants")
    passed = bool(rep.all_passed) and len(errors) == 0
    metrics: Dict[str, Any] = {
        "donor_source_sha256": rep.donor_audit.source_sha256,
        "scenarios_passed": rep.scenarios_passed,
        "scenario_count": rep.scenario_count,
        "capsule_fat12_armed_sha256": rep.capsule_fat12_armed.capsule_sha256,
        "capsule_fat12_tripped_sha256": rep.capsule_fat12_tripped.capsule_sha256,
        "capsule_fat16_tripped_sha256": rep.capsule_fat16_tripped.capsule_sha256,
        "wbi_mutation_bytes": rep.wbi_mutation_bytes,
        "emmc_write_bytes": rep.emmc_write_bytes,
        "persistent_emmc_writes_authorized": rep.persistent_emmc_writes_authorized,
    }
    return PillarAuditSummary(
        pillar_number=6,
        pillar_id="unbrick_ladder_and_capsule_verifier",
        module_name="fx3_recovery.unbrick_ladder_and_capsule_verifier",
        passed=passed,
        status=rep.status,
        verification_mode=rep.verification_mode,
        summary_metrics=metrics,
        deterministic_digest_sha256=_canonical_sha256({"pillar": "unbrick_ladder_and_capsule_verifier", "mode": rep.verification_mode, "status": rep.status, "metrics": metrics, "passed": passed}),
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=tuple(errors),
    )


def _run_pillar_7_uart_decoder(verification_mode: str) -> Tuple[PillarAuditSummary, UartDecoderSuiteResult]:
    t0 = time.monotonic()
    uart_rep = run_uart_boot_decoder_10_scenario_suite(verification_mode=verification_mode)
    metrics: Dict[str, Any] = {
        "scenarios_passed": uart_rep.scenarios_passed,
        "scenarios_total": uart_rep.scenarios_total,
        "active_tx_rejection_verified": uart_rep.active_tx_rejection_verified,
        "unsafe_tx_line_rejection_verified": uart_rep.unsafe_tx_line_rejection_verified,
        "overvoltage_3v3_tap_rejection_verified": uart_rep.overvoltage_3v3_tap_rejection_verified,
        "passive_tx_bytes_emitted": uart_rep.passive_tx_bytes_emitted,
        "scenario_outcomes": {r.scenario_id: r.outcome_code for r in uart_rep.scenario_results},
        "persistent_emmc_writes_authorized": uart_rep.persistent_emmc_writes_authorized,
        "persistent_write_release": uart_rep.persistent_write_release,
    }
    pillar = PillarAuditSummary(
        pillar_number=7,
        pillar_id="passive_uart_boot_stage_decoder",
        module_name="fx3_recovery.recovery_master_suite_and_uart_decoder",
        passed=uart_rep.passed,
        status=uart_rep.status,
        verification_mode=verification_mode,
        summary_metrics=metrics,
        deterministic_digest_sha256=_canonical_sha256({"pillar": "passive_uart_boot_stage_decoder", "mode": verification_mode, "status": uart_rep.status, "metrics": metrics, "passed": uart_rep.passed}),
        elapsed_seconds=round(time.monotonic() - t0, 6),
        errors=uart_rep.errors,
    )
    return pillar, uart_rep


def _inject_pillar_fault(pillar: PillarAuditSummary) -> PillarAuditSummary:
    err = f"FAULT_INJECTED:{pillar.pillar_id}"
    return PillarAuditSummary(
        pillar_number=pillar.pillar_number,
        pillar_id=pillar.pillar_id,
        module_name=pillar.module_name,
        passed=False,
        status=f"FAULT_INJECTED_{pillar.pillar_id.upper()}",
        verification_mode=pillar.verification_mode,
        summary_metrics=pillar.summary_metrics,
        deterministic_digest_sha256=_canonical_sha256({"pillar": pillar.pillar_id, "fault_injected": True, "mode": pillar.verification_mode}),
        elapsed_seconds=pillar.elapsed_seconds,
        errors=pillar.errors + (err,),
    )


def run_recovery_master_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> RecoveryMasterSuiteReport:
    """Execute the unified 7-pillar `fx3_recovery` master readiness audit in `< 1.0s`.

    Runs in `LOCAL_DONOR_O_RDONLY` when local donor files exist and `FX3_FX6_FORCE_CLEAN_ROOM`
    is not set, or `CLEAN_ROOM_SYNTHETIC` when `force_clean_room=True` or donors are absent.
    """
    require(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    require(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    require(ALLOW_BOOT_PARTITION_TARGETING is False, "allow_boot_partition_targeting must stay False")
    require(ALLOW_DESTRUCTIVE_FASTBOOT is False, "allow_destructive_fastboot must stay False")
    require(PASSIVE_TX_BYTES_EMITTED == 0, "passive_tx_bytes_emitted must stay 0")

    if fault_inject_pillar is not None and fault_inject_pillar not in PILLAR_IDS:
        raise ValueError(f"Unknown fault_inject_pillar {fault_inject_pillar!r}; expected one of {PILLAR_IDS}")

    t_start = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    donor_p1_path = resolve_donor_path(DONOR_P1_205_RELPATH) if not clean_room else None
    use_donor = (donor_p1_path is not None) and donor_p1_path.is_file()

    if use_donor and donor_p1_path is not None:
        verification_mode = "LOCAL_DONOR_O_RDONLY"
        donor_p1_sha256 = sha256(read_file(donor_p1_path, MAX_P1)).hexdigest()
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
        donor_p1_sha256 = sha256(b"FX3_CLEAN_ROOM_PHASE86_MASTER_ANCHOR_0x91030080").hexdigest()

    with ThreadPoolExecutor(max_workers=4) as executor:
        f1 = executor.submit(_run_pillar_1_macos_usb_transport, verification_mode)
        f2 = executor.submit(_run_pillar_2_rp2040_fixture, clean_room)
        f3 = executor.submit(_run_pillar_3_init2_escape, clean_room)
        f4 = executor.submit(_run_pillar_4_tier0_backup, clean_room)
        f5 = executor.submit(_run_pillar_5_antirollback_guard, clean_room)
        f6 = executor.submit(_run_pillar_6_unbrick_ladder, clean_room)
        f7 = executor.submit(_run_pillar_7_uart_decoder, verification_mode)
        p1 = f1.result()
        p2 = f2.result()
        p3 = f3.result()
        p4 = f4.result()
        p5 = f5.result()
        p6 = f6.result()
        p7, uart_suite = f7.result()

    pillars_list: List[PillarAuditSummary] = [p1, p2, p3, p4, p5, p6, p7]
    if fault_inject_pillar is not None:
        pillars_list = [
            _inject_pillar_fault(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillars_list
        ]

    errors: List[str] = []
    failed_pillars: List[str] = []
    for p in pillars_list:
        if not p.passed:
            failed_pillars.append(p.pillar_id)
            if p.errors:
                errors.extend(f"[{p.pillar_id}] {e}" for e in p.errors)
            else:
                errors.append(f"[{p.pillar_id}] failed with status={p.status}")

    pillars_passed = sum(1 for p in pillars_list if p.passed)
    all_passed = (
        len(errors) == 0
        and len(failed_pillars) == 0
        and pillars_passed == len(pillars_list) == 7
        and uart_suite.passed
        and PASSIVE_TX_BYTES_EMITTED == 0
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and (ALLOW_BOOT_PARTITION_TARGETING is False)
        and (ALLOW_DESTRUCTIVE_FASTBOOT is False)
        and PHYSICAL_DEVICE_WRITES == 0
    )

    recovery_master_sha256 = _canonical_sha256(
        {
            "schema": RECOVERY_MASTER_SUITE_SCHEMA,
            "version": RECOVERY_MASTER_SUITE_VERSION,
            "verification_mode": verification_mode,
            "donor_p1_sha256": donor_p1_sha256,
            "all_passed": all_passed,
            "pillar_digests": {p.pillar_id: p.deterministic_digest_sha256 for p in pillars_list},
            "pillar_passed": {p.pillar_id: p.passed for p in pillars_list},
            "safety_locks": {
                "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
                "persistent_write_release": PERSISTENT_WRITE_RELEASE,
                "allow_boot_partition_targeting": ALLOW_BOOT_PARTITION_TARGETING,
                "allow_destructive_fastboot": ALLOW_DESTRUCTIVE_FASTBOOT,
                "allow_persistent_jiritsu_writes": ALLOW_PERSISTENT_JIRITSU_WRITES,
                "allow_destructive_jiritsu_commands": ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
                "physical_device_writes": PHYSICAL_DEVICE_WRITES,
                "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
            },
        }
    )

    return RecoveryMasterSuiteReport(
        schema=RECOVERY_MASTER_SUITE_SCHEMA,
        version=RECOVERY_MASTER_SUITE_VERSION,
        verification_mode=verification_mode,
        all_passed=all_passed,
        status=STATUS_VERIFIED_RECOVERY_MASTER_SUITE if all_passed else STATUS_FAIL_RECOVERY_MASTER_SUITE,
        pillar_count=len(pillars_list),
        pillars_passed=pillars_passed,
        failed_pillars=tuple(failed_pillars),
        recovery_master_sha256=recovery_master_sha256,
        donor_p1_sha256=donor_p1_sha256,
        elapsed_seconds=round(time.monotonic() - t_start, 6),
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        allow_persistent_jiritsu_writes=ALLOW_PERSISTENT_JIRITSU_WRITES,
        allow_destructive_jiritsu_commands=ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        pillars=tuple(pillars_list),
        uart_decoder_suite=uart_suite,
        errors=tuple(errors),
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "BOOT_STAGES",
    "DONOR_P1_205_RELPATH",
    "FRAMING_NOISE_BURST_RATIO_THRESHOLD",
    "OUTCOME_BLOCKED_ACTIVE_TX_INJECTION",
    "OUTCOME_BLOCKED_LTC_CONFLICT",
    "OUTCOME_BLOCKED_UNDERVOLTAGE_TAP",
    "OUTCOME_BLOCKED_UNSAFE_TX_LINE",
    "OUTCOME_BLOCKED_UNSUPPORTED_BAUD",
    "OUTCOME_CLEAN_HASH_FAILOPEN_STOCK_BOOT",
    "OUTCOME_CLEAN_SD_SENTINEL_STOCK_ESCAPE",
    "OUTCOME_CRITICAL_DO_NOT_DOWNGRADE_BOOTCHAIN",
    "OUTCOME_DISCONNECT_CABLE_CHECK_1V8_OPEN_DRAIN",
    "OUTCOME_HEALTHY_STAGE_B_LIVE",
    "OUTCOME_NEVER_CROSS_FLASH_FX6_WBI2",
    "OUTCOME_NO_EMMC_FLASH_NEEDED",
    "OUTCOME_TIER0_COLD_REBOOT_WIPES_TMPFS",
    "OUTCOME_TIER0_CRASH_BREAKER_RECOVERED",
    "OUTCOME_TIER1_SD_SENTINEL_OR_P1_83_ROLLBACK",
    "OUTCOME_UNKNOWN_OR_INCOMPLETE_BOOT_LOG",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHYSICAL_DEVICE_WRITES",
    "PILLAR_IDS",
    "READ_ONLY_DONOR_ACCESS",
    "RECOVERY_MASTER_SUITE_SCHEMA",
    "RECOVERY_MASTER_SUITE_VERSION",
    "STAGE_INDEX_MAP",
    "STATUS_FAIL_RECOVERY_MASTER_SUITE",
    "STATUS_FAIL_UART_DECODER_SUITE",
    "STATUS_VERIFIED_PASSIVE_RX_TAP",
    "STATUS_VERIFIED_RECOVERY_MASTER_SUITE",
    "STATUS_VERIFIED_UART_DECODER_SUITE",
    "SUPPORTED_PASSIVE_UART_BAUDS",
    "TEN_OUTCOME_CODES",
    "UART_BOOTROM_BAUD",
    "UART_CONSOLE_BAUD",
    "UART_SCENARIO_IDS",
    "UART_TAP_MAX_SAFE_VOLTAGE_V",
    "UART_TAP_MIN_SAFE_VOLTAGE_V",
    "UART_TAP_NOMINAL_VOLTAGE_V",
    "PassiveTapConfig",
    "PassiveTapSafetyResult",
    "PillarAuditSummary",
    "RecoveryMasterSuiteReport",
    "UartBootDecodeResult",
    "UartBootScenarioSpec",
    "UartBootStageTrace",
    "UartDecoderSuiteResult",
    "audit_passive_rx_tap_safety",
    "build_default_10_uart_scenarios",
    "decode_uart_boot_log",
    "parse_cxd90057_boot_stages",
    "run_recovery_master_suite",
    "run_uart_boot_decoder_10_scenario_suite",
]
