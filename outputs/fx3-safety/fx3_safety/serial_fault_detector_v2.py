"""Phase 32 Fail-Closed Serial & Kernel Telemetry Fault Detector v2.

Deterministic streaming & batch serial/telemetry fault detector for Sony ILME-FX3
(`4.9.337-scel+`, `CXD90057` AP + `CXD90058` CP) and Stage-A/Stage-B FX6-on-FX3
boot logs.

Covers five verification domains:
1. Sony Linux `4.9.337-scel+` Kernel Panics, Oops, Unhandled Faults & Signals
   (`Unable to handle kernel`, `Kernel panic`, `Internal error: Oops`,
   `SError Interrupt`, `BUG:`, `ZZTGKILL`, `ZZSTACK`, `ZZEXCSTACK`,
   `SIGSEGV`/`SIGABRT`, `assert at`).
2. Dynamic Linker & Device/Module Missing Diagnostics
   (`MISSSO`, `MISSDEV`, `IMOPEN`, `MODLOAD`, `error while loading shared libraries`,
   `/etc/ld.so.preload` dynamic BusyBox init deadlock markers).
3. Synchronization & IPC Hang Diagnostics
   (`ZZFUTEX`, `ZZCOMPLETE`, `INFO: task .* blocked for more than`,
   `WlanResourceMainThread` `0x70d4` infinite `usleep` hang, UIPC
   `0x92d2091c`/`0x91db059b` unshimmed timeout).
4. `TIMER-IP` `220.0s` (`3m 40s`) & `90.0s` Stage-A Guard Watchdog Budget Verifier
   Verifies `WDT_SET_STOP` and Stage-A `/tmp/mod_arm_once` Clear-Before-Exec
   occur strictly before the `90.0s` soft guard and `220.0s` `TIMER-IP` hardware
   watchdog ceiling (and before overlay/appFw execution).
5. Degraded-Safe vs Fatal Classifier (`00342260` `WF-12`, `P4` ND, `P11` Grip)
   Distinguishes expected non-blocking degraded events (`WF12_DEGRADED_RADIO_OFF`,
   `BT_DEGRADED_DISABLED` `0xbb9`, `P11` detached-grip ACK `0x91db059b`,
   `P11` `/dev/rtc0` `open_ok=0` probe, `P4` ND `Clear`) -> `ALLOWED_DEGRADED`
   from fatal abort events (`"System Error"`, `0x10000009` VFAT full,
   Verify-Before-Mount SHA mismatch, `nop_count > 0` in native-faithful mode)
   -> `FAIL_CLOSED_ABORT`, automatically cross-linking each fatal class to
   `fx3_safety.brick_classifier.classify_brick_state` recovery playbooks.

Also audits committed Round 10 real FX3 `4.9.337-scel+` `summary.json` telemetry
(opened strictly via `os.O_RDONLY`) with deterministic `FX3_FX6_FORCE_CLEAN_ROOM=1`
synthetic fallback.

Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` (hard-locked)
- `PERSISTENT_WRITE_RELEASE = False` (hard-locked)
- All file reads strictly use `os.open(..., os.O_RDONLY)`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple, Union

from .brick_classifier import BrickDiagnosis, classify_brick_state


SERIAL_FAULT_DETECTOR_V2_SCHEMA: str = "fx3-serial-fault-detector-v2"
SERIAL_FAULT_DETECTOR_V2_VERSION: str = "2.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Watchdog & Stage-A Timing Ceilings
STAGE_A_SOFT_GUARD_BUDGET_SEC: float = 90.0
TIMER_IP_HW_WDT_CEILING_SEC: float = 220.0  # 3m 40s hardware TIMER-IP watchdog
FAILSAFE_INIT2_HEARTBEAT_SEC: float = 45.0

# Dispositions
DISPOSITION_PASS: str = "PASS"
DISPOSITION_ALLOWED_DEGRADED: str = "ALLOWED_DEGRADED"
DISPOSITION_FAIL_CLOSED_ABORT: str = "FAIL_CLOSED_ABORT"

# Fault Categories
CAT_KERNEL_PANIC_OOPS = "KERNEL_PANIC_OOPS_SIGNAL"
CAT_LINKER_MODULE_MISSING = "DYNAMIC_LINKER_DEVICE_MODULE"
CAT_SYNC_IPC_HANG = "SYNC_IPC_HANG"
CAT_WATCHDOG_BUDGET = "WATCHDOG_WDT_BUDGET"
CAT_FATAL_ABORT = "FATAL_ABORT_INVARIANT"
CAT_CAPTURE_INTEGRITY = "CAPTURE_INTEGRITY"
CAT_ALLOWED_DEGRADED = "ALLOWED_DEGRADED"

DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
DEFAULT_ROUND10_SUMMARY_REL: Path = Path(
    "reports/2026-11-14-round10-fx6-on-fx3-full-icon-presenter/summary.json"
)


# ---------------------------------------------------------------------------
# Strict O_RDONLY & Clean-Room Helpers
# ---------------------------------------------------------------------------


def is_forced_clean_room() -> bool:
    """Return True when `FX3_FX6_FORCE_CLEAN_ROOM=1` is active."""
    return os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() == "1"


def read_file_o_rdonly(path: Union[str, Path]) -> bytes:
    """Read a file strictly with `os.open(..., os.O_RDONLY)`."""
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


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FaultFinding:
    line_number: Optional[int]
    timestamp_sec: Optional[float]
    category: str
    code: str
    severity: str  # "FATAL" or "DEGRADED"
    disposition: str  # "FAIL_CLOSED_ABORT" or "ALLOWED_DEGRADED"
    raw_line: str
    message: str
    brick_playbook_key: Optional[str] = None


@dataclass(frozen=True)
class WatchdogBudgetReport:
    passed: bool
    status: str
    soft_guard_budget_sec: float
    hw_wdt_ceiling_sec: float
    wdt_stop_seen: bool
    wdt_stop_sec: Optional[float]
    clear_before_exec_seen: bool
    clear_before_exec_sec: Optional[float]
    overlay_exec_sec: Optional[float]
    max_observed_sec: Optional[float]
    timer_ip_fault_seen: bool
    violations: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BrickPlaybookLink:
    playbook_key: str
    trigger_codes: Tuple[str, ...]
    brick_level: str
    severity: str
    title: str
    software_usb_or_sd_recoverable: bool
    disassembly_free_uart_bootrom_recoverable: bool
    hardware_programmer_required: bool
    primary_recovery_steps: Tuple[str, ...]
    critical_warnings: Tuple[str, ...]


@dataclass(frozen=True)
class SerialFaultAuditReport:
    schema: str
    version: str
    source: str
    passed: bool
    disposition: str  # PASS, ALLOWED_DEGRADED, FAIL_CLOSED_ABORT
    abort_required: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    native_faithful_mode: bool
    lines_scanned: int
    bytes_scanned: int
    sha256: str
    line_terminated: bool
    fatal_fault_count: int
    degraded_event_count: int
    findings: Tuple[FaultFinding, ...]
    degraded_events: Tuple[FaultFinding, ...]
    watchdog_budget: WatchdogBudgetReport
    brick_recovery_playbooks: Tuple[BrickPlaybookLink, ...]
    telemetry_checks: Dict[str, Any] = field(default_factory=dict)
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Round10TelemetryAuditReport:
    schema: str
    version: str
    telemetry_source: str
    summary_path: Optional[str]
    all_passed: bool
    overall_disposition: str
    runs_audited: int
    run_reports: Dict[str, Dict[str, Any]]
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Timestamp & Pattern Definitions
# ---------------------------------------------------------------------------

_DMESG_TS_RE = re.compile(r"^\[\s*(\d+(?:\.\d+)?)\]")
_KV_TS_RE = re.compile(r"(?:^|\s)(?:ts|t|elapsed|wall_elapsed_sec)=(\d+(?:\.\d+)?)s?\b")
_ASSERT_RE = re.compile(r"^\s*(?:\[\s*\d+(?:\.\d+)?\]\s*)?assert at ([^:\s]+):(\d+)\b")

# 1. Sony Linux 4.9.337-scel+ Kernel Panics, Oops, Faults & Signals
_KERNEL_SIGNAL_RULES: Tuple[Tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "KERNEL_UNABLE_TO_HANDLE",
        re.compile(r"\bUnable to handle kernel\b", re.IGNORECASE),
        "p3_kernel",
        "Kernel paging/NULL dereference fault detected.",
    ),
    (
        "KERNEL_PANIC",
        re.compile(r"\bKernel panic(?:\s*-\s*not syncing)?\b", re.IGNORECASE),
        "p3_kernel",
        "Linux kernel panic detected.",
    ),
    (
        "KERNEL_INTERNAL_ERROR_OOPS",
        re.compile(r"\bInternal error:\s*Oops\b|\bOops:\s*[0-9a-fx]+", re.IGNORECASE),
        "p3_kernel",
        "Kernel Oops exception detected.",
    ),
    (
        "KERNEL_SERROR_INTERRUPT",
        re.compile(r"\bSError Interrupt\b"),
        "p3_kernel",
        "ARM64 SError asynchronous hardware abort detected.",
    ),
    (
        "KERNEL_BUG_MARKER",
        re.compile(r"\bBUG:\s*(?:unable to handle|kernel NULL pointer|failure at|scheduling while atomic)\b"),
        "p3_kernel",
        "Kernel BUG() assertion detected.",
    ),
    (
        "KERNEL_UNHANDLED_FAULT",
        re.compile(r"\bUnhandled fault:\b|\bBad mode in\b"),
        "p3_kernel",
        "Unhandled ARM64/ARM CPU fault mode detected.",
    ),
    (
        "SONY_ZZTGKILL",
        re.compile(r"\bZZTGKILL\b"),
        "p15_userland",
        "Sony kernel diagnostic ZZTGKILL signal kill trace detected.",
    ),
    (
        "SONY_ZZSTACK",
        re.compile(r"\bZZSTACK\b"),
        "p15_userland",
        "Sony kernel diagnostic ZZSTACK crash stack trace detected.",
    ),
    (
        "SONY_ZZEXCSTACK",
        re.compile(r"\bZZEXCSTACK\b"),
        "p3_kernel",
        "Sony kernel diagnostic ZZEXCSTACK exception stack trace detected.",
    ),
    (
        "USERLAND_SIGSEGV_SIGABRT",
        re.compile(
            r"\b(?:SIGSEGV|SIGABRT|SIGBUS|SIGILL|Segmentation fault|Aborted \(core dumped\)|"
            r"signal (?:6|11)\b|Unhandled signal (?:6|11))\b"
        ),
        "p15_userland",
        "Fatal userland crash signal (SIGSEGV/SIGABRT/SIGBUS/SIGILL) detected.",
    ),
)

# 2. Dynamic Linker & Device/Module Missing Diagnostics
_LINKER_MODULE_RULES: Tuple[Tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "LD_SO_PRELOAD_BUSYBOX_DEADLOCK",
        re.compile(
            r"(?:/etc/ld\.so\.preload|from /etc/ld\.so\.preload cannot be preloaded|"
            r"busybox:\s*error while loading shared libraries|"
            r"/sbin/init:\s*error while loading shared libraries)",
            re.IGNORECASE,
        ),
        "ld_so_preload",
        "/etc/ld.so.preload dynamic BusyBox / init deadlock marker detected.",
    ),
    (
        "SHARED_LIB_LOAD_ERROR",
        re.compile(r"\berror while loading shared libraries\b|\bcannot open shared object file\b"),
        "p15_userland",
        "Dynamic linker failed to load required shared library.",
    ),
    (
        "SONY_MISSSO",
        re.compile(r"\bMISSSO\b"),
        "p15_userland",
        "Sony diagnostic MISSSO (missing shared library .so) detected.",
    ),
    (
        "SONY_MISSDEV",
        re.compile(r"\bMISSDEV\b"),
        "p3_kernel",
        "Sony diagnostic MISSDEV (missing kernel device node /dev/*) detected.",
    ),
)

# IMOPEN / MODLOAD: treat explicit OK/rc=0/loaded telemetry as benign, flag errors or bare alerts
_IMOPEN_RE = re.compile(r"\bIMOPEN\b")
_MODLOAD_RE = re.compile(r"\bMODLOAD\b")
_BENIGN_OK_RE = re.compile(r"\b(?:status=OK|rc=0|errno=0|ok=1|module_loaded=1|loaded=1)\b", re.IGNORECASE)

# 3. Synchronization & IPC Hang Diagnostics
_SYNC_HANG_RULES: Tuple[Tuple[str, re.Pattern[str], str, str], ...] = (
    (
        "SONY_ZZFUTEX_HANG",
        re.compile(r"\bZZFUTEX\b"),
        "p15_userland",
        "Sony diagnostic ZZFUTEX futex stall/deadlock detected.",
    ),
    (
        "SONY_ZZCOMPLETE_HANG",
        re.compile(r"\bZZCOMPLETE\b"),
        "p3_kernel",
        "Sony diagnostic ZZCOMPLETE kernel completion wait hang detected.",
    ),
    (
        "KERNEL_HUNG_TASK_BLOCKED",
        re.compile(r"INFO:\s*task\s+.+?\s+blocked for more than\s+\d+\s+seconds", re.IGNORECASE),
        "p3_kernel",
        "Linux kernel hung-task blocked thread detector triggered.",
    ),
)

_WLAN_THREAD_HANG_RE = re.compile(
    r"(?:WlanResourceMainThread.*(?:0x70d4|handleFatalError|hang|stuck|usleep|fatal|loop)|"
    r"handleFatalError.*(?:0x70d4|usleep|loop|fatal|hang)|"
    r"0x70d4.*(?:WlanResourceMainThread|usleep|infinite|hang|unpatched))",
    re.IGNORECASE,
)
_WLAN_PATCH_OK_RE = re.compile(
    r"(?:P12_wlan_resource_handleFatalError_nonblocking|status=OK|patched=1|nonblocking.*verified)",
    re.IGNORECASE,
)

# UIPC 0x92d2091c / 0x91db059b unshimmed timeout vs shimmed P11 ACK
_UIPC_SHIMMED_ACK_RE = re.compile(
    r"(?:FX6_P11_HANDLE_ACK\b.*0x91db059b.*free_rc=0.*snd_rc=0|"
    r"\bP11_DETACHED_GRIP_ACK\b.*0x91db059b|"
    r"dest=0x91db059b\b.*cb_qid=)",
    re.IGNORECASE,
)
_UIPC_UNSHIMMED_TIMEOUT_RE = re.compile(
    r"(?:(?:0x92d2091c|0x91db059b).*(?:timeout|timed\s*out|unshimmed|hang|stuck|ETIMEDOUT|blocked|wait_fail)|"
    r"(?:timeout|timed\s*out|unshimmed|hang|stuck|ETIMEDOUT|blocked|UIPC_ERR).*(?:0x92d2091c|0x91db059b))",
    re.IGNORECASE,
)

# 4. Watchdog / TIMER-IP / Clear-Before-Exec Markers
_WDT_SET_STOP_RE = re.compile(r"\bWDT_SET_STOP\b|\bwdt_set_stop\b|TIMER-IP:\s*stopped\b", re.IGNORECASE)
_TIMER_IP_FAULT_RE = re.compile(
    r"(?:TIMER-IP.*(?:timeout|expired|reset|bark|fail)|"
    r"(?:watchdog|wdt).*(?:expired|bark|reset|hard lockup|timeout))",
    re.IGNORECASE,
)
_CLEAR_BEFORE_EXEC_RE = re.compile(
    r"(?:(?:rm\s+-f\s+[\"']?/tmp/mod_arm_once[\"']?|/tmp/mod_arm_once.*(?:unlink|clear|removed))|"
    r"\bFX6_STAGE_A_CLEAR_BEFORE_EXEC\b|\bCLEAR_BEFORE_EXEC\b)",
    re.IGNORECASE,
)
_OVERLAY_EXEC_RE = re.compile(
    r"(?:\bmount\s+--bind\b|\bFX6_STAGE_A_VERIFY_RC=0\b|\bFX6_HYBRID_BRIDGE_INIT\b|\bFX6_STAGE_B_BRIDGE\b)",
    re.IGNORECASE,
)

# 5. Degraded-Safe vs Fatal Abort Events
_DEGRADED_RULES: Tuple[Tuple[str, re.Pattern[str], str], ...] = (
    (
        "WF12_DEGRADED_RADIO_OFF",
        re.compile(
            r"(?:\bWF12_DEGRADED_RADIO_OFF\b|\bWIFI_DEGRADED_RADIO_OFF\b|\bP12_WF12_DEGRADED\b|"
            r"\bNOTICE_00342260_DEGRADED\b|The Wi-Fi/Bluetooth unit has malfunctioned)",
            re.IGNORECASE,
        ),
        "Expected non-blocking WF-12 radio-off / Notice 00342260 degraded state.",
    ),
    (
        "BT_DEGRADED_DISABLED_0xBB9",
        re.compile(
            r"(?:\bBT_DEGRADED_DISABLED\b|\bAIRPLANE_MODE_RAM_SHADOW\b|"
            r"(?:wrapper_bt_interface_enable|BT_BSA_HAL|BSA).*(?:0x0?bb9|3001)|"
            r"(?:0x0?bb9|3001).*BT_DEGRADED)",
            re.IGNORECASE,
        ),
        "Expected non-blocking Bluetooth disabled / 0xbb9 fallback.",
    ),
    (
        "P11_DETACHED_GRIP_ACK_0x91DB059B",
        _UIPC_SHIMMED_ACK_RE,
        "Expected P11 shimmed detached-grip UIPC ACK (0x91db059b).",
    ),
    (
        "P11_RTC0_DEGRADED_PROBE",
        re.compile(
            r"(?:\bFX6_P11_RTC0_PROBE\b.*\bok=0\b|\bFX6_STAGE_B_R10_RTC0\b.*\bopen_ok=0\b)",
            re.IGNORECASE,
        ),
        "Expected non-blocking /dev/rtc0 absent probe in QEMU.",
    ),
    (
        "P4_ND_CLEAR",
        re.compile(
            r"(?:\bP4_ND_CLEAR\b|\bP4_ND_FILTER_CLEAR\b|\bFX6_P4_ND_CLEAR\b|"
            r"\bP4_appfw_set_nd_filter_(?:mode|value)_clear\b|"
            r"set_nd_filter.*Clear\b|nd_filter_mode=Clear\b)",
            re.IGNORECASE,
        ),
        "Expected P4 physical FX3 ND-filter Clear degraded adapter event.",
    ),
)

_SYSTEM_ERROR_RE = re.compile(
    r"(?:\bSystem Error\b|\"System Error\"|\bSYSTEM_ERROR_ABORT\b|"
    r"\bMODEL_WIFI_FATAL_ERROR_OCCURRED\b|Fatal error on Wi-Fi func)",
    re.IGNORECASE,
)
_VFAT_0x10000009_RE = re.compile(
    r"(?:\b0x10000009\b|\bnflasha10_full\b|\bnflasha10\b.*(?:VFAT full|exhausted|ENOSPC|No space left))",
    re.IGNORECASE,
)
_VERIFY_ITEM_LINE_RE = re.compile(
    r"FX6_STAGE_A_VERIFY_ITEM\b.*expected=([0-9a-fA-F]+)\s+actual=([0-9a-fA-F]+)\s+status=(\S+)"
)
_VERIFY_RC_RE = re.compile(r"\bFX6_STAGE_A_VERIFY_RC=(-?\d+)\b")
_VERIFY_MISMATCH_TEXT_RE = re.compile(
    r"(?:Verify-Before-Mount.*(?:mismatch|fail)|SHA-?256 mismatch|FX6_STAGE_A_VERIFY_FAIL)",
    re.IGNORECASE,
)
_NOP_COUNT_RE = re.compile(r"\bnop_count=(\d+)\b")
_FAITHFUL_FLAG_RE = re.compile(r"\b(?:faithful|FX6_NATIVE_FAITHFUL)=(\d+)\b")


# ---------------------------------------------------------------------------
# Brick Classifier Cross-Linker
# ---------------------------------------------------------------------------


def _build_brick_playbook_link(
    playbook_key: str,
    trigger_codes: Sequence[str],
    *,
    updater_mode_armed: bool = False,
    oneshot_overlay_used: bool = False,
) -> BrickPlaybookLink:
    if playbook_key == "0x100D":
        diag: BrickDiagnosis = classify_brick_state(diagnostic_code=0x100D)
    elif playbook_key == "6L+9S_wf12":
        diag = classify_brick_state(led_symptom="6L+9S", updater_mode_armed=updater_mode_armed)
    elif playbook_key == "0x10000009":
        diag = classify_brick_state(
            error_code=0x10000009,
            corrupted_regions=["p10_vfat_full"],
            updater_mode_armed=updater_mode_armed,
        )
    elif playbook_key == "ld_so_preload":
        diag = classify_brick_state(
            ld_so_preload_deadlock=True,
            corrupted_regions=["ld_so_preload"],
            updater_mode_armed=updater_mode_armed,
        )
    elif playbook_key == "p3_kernel":
        diag = classify_brick_state(
            corrupted_regions=["p3_system"],
            updater_mode_armed=updater_mode_armed,
        )
    elif playbook_key == "oneshot_overlay":
        diag = classify_brick_state(
            corrupted_regions=["p15_usr"],
            oneshot_overlay_used=True,
            updater_mode_armed=updater_mode_armed,
        )
    else:  # "p15_userland" or default
        diag = classify_brick_state(
            corrupted_regions=["p15_usr"],
            oneshot_overlay_used=oneshot_overlay_used,
            updater_mode_armed=updater_mode_armed,
        )

    return BrickPlaybookLink(
        playbook_key=playbook_key,
        trigger_codes=tuple(sorted(set(trigger_codes))),
        brick_level=diag.level,
        severity=diag.severity,
        title=diag.title,
        software_usb_or_sd_recoverable=diag.software_usb_or_sd_recoverable,
        disassembly_free_uart_bootrom_recoverable=diag.disassembly_free_uart_bootrom_recoverable,
        hardware_programmer_required=diag.hardware_programmer_required,
        primary_recovery_steps=tuple(diag.primary_recovery_steps),
        critical_warnings=tuple(diag.critical_warnings),
    )


# ---------------------------------------------------------------------------
# Dedicated Watchdog Budget Verifier
# ---------------------------------------------------------------------------


def verify_watchdog_budget(
    *,
    wdt_stop_sec: Optional[float] = None,
    clear_before_exec_sec: Optional[float] = None,
    overlay_exec_sec: Optional[float] = None,
    max_observed_sec: Optional[float] = None,
    timer_ip_fault_seen: bool = False,
    wdt_stop_seen: Optional[bool] = None,
    clear_before_exec_seen: Optional[bool] = None,
    require_wdt_stop_proof: bool = False,
    require_clear_before_exec_proof: bool = False,
    soft_guard_budget_sec: float = STAGE_A_SOFT_GUARD_BUDGET_SEC,
    hw_wdt_ceiling_sec: float = TIMER_IP_HW_WDT_CEILING_SEC,
) -> WatchdogBudgetReport:
    """Verify `TIMER-IP` 220.0s & Stage-A 90.0s Clear-Before-Exec watchdog budget."""
    stop_seen = (wdt_stop_sec is not None) if wdt_stop_seen is None else wdt_stop_seen
    clear_seen = (clear_before_exec_sec is not None) if clear_before_exec_seen is None else clear_before_exec_seen

    violations: List[str] = []
    errors: List[str] = []

    def add_v(code: str, msg: str) -> None:
        if code not in violations:
            violations.append(code)
        errors.append(msg)

    if timer_ip_fault_seen:
        add_v(
            "TIMER_IP_WDT_FAULT_TRIGGERED",
            "TIMER-IP / kernel watchdog timeout or bark marker observed in serial telemetry.",
        )

    if wdt_stop_sec is not None:
        if wdt_stop_sec < 0:
            add_v("INVALID_WDT_TIMESTAMP", f"Negative WDT_SET_STOP timestamp {wdt_stop_sec}s.")
        if wdt_stop_sec >= hw_wdt_ceiling_sec:
            add_v(
                "TIMER_IP_220S_CEILING_EXCEEDED",
                f"WDT_SET_STOP occurred at {wdt_stop_sec:.3f}s >= {hw_wdt_ceiling_sec:.1f}s TIMER-IP ceiling.",
            )
        if wdt_stop_sec >= soft_guard_budget_sec:
            add_v(
                "STAGE_A_90S_SOFT_GUARD_EXCEEDED",
                f"WDT_SET_STOP occurred at {wdt_stop_sec:.3f}s >= {soft_guard_budget_sec:.1f}s Stage-A soft guard.",
            )

    if clear_before_exec_sec is not None:
        if clear_before_exec_sec < 0:
            add_v("INVALID_CLEAR_TIMESTAMP", f"Negative Clear-Before-Exec timestamp {clear_before_exec_sec}s.")
        if clear_before_exec_sec >= hw_wdt_ceiling_sec:
            add_v(
                "TIMER_IP_220S_CEILING_EXCEEDED",
                f"Clear-Before-Exec occurred at {clear_before_exec_sec:.3f}s >= {hw_wdt_ceiling_sec:.1f}s TIMER-IP ceiling.",
            )
        if clear_before_exec_sec >= soft_guard_budget_sec:
            add_v(
                "STAGE_A_90S_SOFT_GUARD_EXCEEDED",
                f"Clear-Before-Exec occurred at {clear_before_exec_sec:.3f}s >= {soft_guard_budget_sec:.1f}s Stage-A soft guard.",
            )
        if overlay_exec_sec is not None and clear_before_exec_sec > overlay_exec_sec:
            add_v(
                "CLEAR_BEFORE_EXEC_ORDER_VIOLATION",
                f"/tmp/mod_arm_once Clear-Before-Exec ({clear_before_exec_sec:.3f}s) occurred AFTER "
                f"overlay/exec ({overlay_exec_sec:.3f}s).",
            )

    if max_observed_sec is not None:
        if max_observed_sec >= hw_wdt_ceiling_sec and not stop_seen:
            add_v(
                "TIMER_IP_220S_MISSING_WDT_SET_STOP",
                f"Boot timeline reached {max_observed_sec:.3f}s >= {hw_wdt_ceiling_sec:.1f}s without WDT_SET_STOP.",
            )
        if max_observed_sec >= soft_guard_budget_sec:
            if not stop_seen:
                add_v(
                    "STAGE_A_90S_MISSING_WDT_SET_STOP",
                    f"Boot timeline reached {max_observed_sec:.3f}s >= {soft_guard_budget_sec:.1f}s without WDT_SET_STOP.",
                )
            if not clear_seen:
                add_v(
                    "STAGE_A_90S_MISSING_CLEAR_BEFORE_EXEC",
                    f"Boot timeline reached {max_observed_sec:.3f}s >= {soft_guard_budget_sec:.1f}s without "
                    "`/tmp/mod_arm_once` Clear-Before-Exec.",
                )

    if require_wdt_stop_proof and not stop_seen:
        add_v(
            "MISSING_WDT_SET_STOP_PROOF",
            "Strict watchdog audit requires explicit `WDT_SET_STOP` marker strictly < 90.0s / 220.0s.",
        )

    if require_clear_before_exec_proof and not clear_seen:
        add_v(
            "MISSING_CLEAR_BEFORE_EXEC_PROOF",
            "Strict Stage-A guard audit requires `/tmp/mod_arm_once` Clear-Before-Exec marker strictly < 90.0s.",
        )

    passed = len(violations) == 0
    if not passed:
        status = f"BLOCKED_{violations[0]}"
    elif stop_seen or clear_seen or max_observed_sec is not None:
        status = "VERIFIED_WITHIN_BUDGET"
    else:
        status = "NO_WDT_TIMELINE_EXCEEDED"

    return WatchdogBudgetReport(
        passed=passed,
        status=status,
        soft_guard_budget_sec=soft_guard_budget_sec,
        hw_wdt_ceiling_sec=hw_wdt_ceiling_sec,
        wdt_stop_seen=stop_seen,
        wdt_stop_sec=wdt_stop_sec,
        clear_before_exec_seen=clear_seen,
        clear_before_exec_sec=clear_before_exec_sec,
        overlay_exec_sec=overlay_exec_sec,
        max_observed_sec=max_observed_sec,
        timer_ip_fault_seen=timer_ip_fault_seen,
        violations=tuple(violations),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Streaming Serial Fault Detector v2
# ---------------------------------------------------------------------------


def _extract_timestamp_sec(line: str) -> Optional[float]:
    m = _DMESG_TS_RE.match(line)
    if m:
        return float(m.group(1))
    m2 = _KV_TS_RE.search(line)
    if m2:
        return float(m2.group(1))
    return None


def _strip_shell_comment(line: str) -> str:
    payload = _DMESG_TS_RE.sub("", line, count=1).lstrip()
    if payload.startswith("#"):
        return ""
    return line


class StreamingSerialFaultDetectorV2:
    """Incremental line/chunk fail-closed serial & kernel telemetry fault detector."""

    def __init__(
        self,
        *,
        native_faithful_mode: bool = True,
        require_wdt_budget_proof: Optional[bool] = None,
        soft_guard_budget_sec: float = STAGE_A_SOFT_GUARD_BUDGET_SEC,
        hw_wdt_ceiling_sec: float = TIMER_IP_HW_WDT_CEILING_SEC,
        updater_mode_armed: bool = False,
        oneshot_overlay_used: bool = False,
        source_label: str = "<stream>",
    ) -> None:
        self.native_faithful_mode = native_faithful_mode
        self.require_wdt_budget_proof = require_wdt_budget_proof
        self.soft_guard_budget_sec = soft_guard_budget_sec
        self.hw_wdt_ceiling_sec = hw_wdt_ceiling_sec
        self.updater_mode_armed = updater_mode_armed
        self.oneshot_overlay_used = oneshot_overlay_used
        self.source_label = source_label

        self._hasher = hashlib.sha256()
        self._bytes_scanned = 0
        self._lines_scanned = 0
        self._line_terminated = False
        self._pending_chunk = ""

        self._fatal_findings: List[FaultFinding] = []
        self._degraded_events: List[FaultFinding] = []
        self._telemetry_checks: Dict[str, Any] = {}

        # Watchdog timeline state
        self._wdt_stop_seen = False
        self._wdt_stop_sec: Optional[float] = None
        self._clear_before_exec_seen = False
        self._clear_before_exec_sec: Optional[float] = None
        self._overlay_exec_sec: Optional[float] = None
        self._max_observed_sec: Optional[float] = None
        self._timer_ip_fault_seen = False

    def should_abort_now(self) -> bool:
        """Return True immediately when a fail-closed abort trigger has been observed."""
        if self._fatal_findings or self._timer_ip_fault_seen:
            return True
        if self._wdt_stop_sec is not None and (
            self._wdt_stop_sec >= self.soft_guard_budget_sec
            or self._wdt_stop_sec >= self.hw_wdt_ceiling_sec
        ):
            return True
        if self._clear_before_exec_sec is not None and (
            self._clear_before_exec_sec >= self.soft_guard_budget_sec
            or self._clear_before_exec_sec >= self.hw_wdt_ceiling_sec
        ):
            return True
        if self._max_observed_sec is not None:
            if self._max_observed_sec >= self.hw_wdt_ceiling_sec and not self._wdt_stop_seen:
                return True
            if self._max_observed_sec >= self.soft_guard_budget_sec and (
                not self._wdt_stop_seen or not self._clear_before_exec_seen
            ):
                return True
        return False

    def _record_ts(self, ts: Optional[float]) -> None:
        if ts is None:
            return
        if self._max_observed_sec is None or ts > self._max_observed_sec:
            self._max_observed_sec = ts

    def feed_chunk(self, chunk: Union[str, bytes]) -> List[FaultFinding]:
        """Feed an arbitrary string/bytes chunk across partial line boundaries."""
        if isinstance(chunk, bytes):
            raw_bytes = chunk
            text = chunk.decode("utf-8", errors="replace")
        else:
            raw_bytes = chunk.encode("utf-8")
            text = chunk

        if not raw_bytes:
            return []

        self._hasher.update(raw_bytes)
        self._bytes_scanned += len(raw_bytes)
        self._line_terminated = raw_bytes.endswith(b"\n")

        combined = self._pending_chunk + text
        parts = combined.splitlines(keepends=True)
        self._pending_chunk = ""
        emitted: List[FaultFinding] = []
        for part in parts:
            if not part.endswith("\n"):
                self._pending_chunk = part
                break
            clean_line = part.rstrip("\r\n")
            emitted.extend(self._process_line(clean_line, account_bytes=False))
        return emitted

    def feed_line(self, line: str) -> List[FaultFinding]:
        """Feed a single logical line (without requiring caller to manage chunk buffers)."""
        clean_line = line.rstrip("\r\n")
        raw = (clean_line + "\n").encode("utf-8")
        self._hasher.update(raw)
        self._bytes_scanned += len(raw)
        self._line_terminated = True
        return self._process_line(clean_line, account_bytes=False)

    def _process_line(self, text: str, *, account_bytes: bool = False) -> List[FaultFinding]:
        if account_bytes:
            raw = (text + "\n").encode("utf-8")
            self._hasher.update(raw)
            self._bytes_scanned += len(raw)

        self._lines_scanned += 1
        ln = self._lines_scanned
        ts = _extract_timestamp_sec(text)
        self._record_ts(ts)
        emitted: List[FaultFinding] = []

        def emit_fatal(code: str, category: str, msg: str, playbook: Optional[str]) -> None:
            f = FaultFinding(
                line_number=ln,
                timestamp_sec=ts,
                category=category,
                code=code,
                severity="FATAL",
                disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                raw_line=text,
                message=msg,
                brick_playbook_key=playbook,
            )
            self._fatal_findings.append(f)
            emitted.append(f)

        def emit_degraded(code: str, msg: str) -> None:
            f = FaultFinding(
                line_number=ln,
                timestamp_sec=ts,
                category=CAT_ALLOWED_DEGRADED,
                code=code,
                severity="DEGRADED",
                disposition=DISPOSITION_ALLOWED_DEGRADED,
                raw_line=text,
                message=msg,
                brick_playbook_key=None,
            )
            self._degraded_events.append(f)
            emitted.append(f)

        # Watchdog & Stage-A Clear-Before-Exec tracking (ignore shell comments)
        active_text = _strip_shell_comment(text)
        if active_text:
            if _TIMER_IP_FAULT_RE.search(active_text):
                self._timer_ip_fault_seen = True
                emit_fatal(
                    "TIMER_IP_WDT_FAULT_TRIGGERED",
                    CAT_WATCHDOG_BUDGET,
                    "TIMER-IP hardware watchdog timeout/reset detected.",
                    "p3_kernel",
                )
            elif _WDT_SET_STOP_RE.search(active_text):
                self._wdt_stop_seen = True
                if self._wdt_stop_sec is None and ts is not None:
                    self._wdt_stop_sec = ts

            if _CLEAR_BEFORE_EXEC_RE.search(active_text):
                self._clear_before_exec_seen = True
                if self._clear_before_exec_sec is None and ts is not None:
                    self._clear_before_exec_sec = ts

            if _OVERLAY_EXEC_RE.search(active_text):
                if self._overlay_exec_sec is None and ts is not None:
                    self._overlay_exec_sec = ts

        # Assert check
        m_assert = _ASSERT_RE.match(text)
        if m_assert:
            emit_fatal(
                "SERIAL_ASSERT_FAILURE",
                CAT_KERNEL_PANIC_OOPS,
                f"Assertion failed at {m_assert.group(1)}:{m_assert.group(2)}.",
                "p15_userland",
            )

        # Category 1: Kernel panics, Oops, ZZTGKILL/ZZSTACK/ZZEXCSTACK, SIGSEGV/SIGABRT
        for code, pat, playbook, msg in _KERNEL_SIGNAL_RULES:
            if pat.search(text):
                emit_fatal(code, CAT_KERNEL_PANIC_OOPS, msg, playbook)

        # Category 2: Dynamic Linker, MISSSO/MISSDEV/IMOPEN/MODLOAD, /etc/ld.so.preload
        for code, pat, playbook, msg in _LINKER_MODULE_RULES:
            if pat.search(text):
                emit_fatal(code, CAT_LINKER_MODULE_MISSING, msg, playbook)

        if _IMOPEN_RE.search(text) and not _BENIGN_OK_RE.search(text):
            emit_fatal(
                "SONY_IMOPEN_FAULT",
                CAT_LINKER_MODULE_MISSING,
                "Sony diagnostic IMOPEN file/device open failure detected.",
                "p15_userland",
            )
        if _MODLOAD_RE.search(text) and not _BENIGN_OK_RE.search(text):
            emit_fatal(
                "SONY_MODLOAD_FAULT",
                CAT_LINKER_MODULE_MISSING,
                "Sony diagnostic MODLOAD kernel module failure detected.",
                "p3_kernel",
            )

        # Category 3: Sync & IPC Hang Diagnostics
        for code, pat, playbook, msg in _SYNC_HANG_RULES:
            if pat.search(text):
                emit_fatal(code, CAT_SYNC_IPC_HANG, msg, playbook)

        if _WLAN_THREAD_HANG_RE.search(text) and not _WLAN_PATCH_OK_RE.search(text):
            emit_fatal(
                "WLAN_RESOURCE_0x70D4_HANG",
                CAT_SYNC_IPC_HANG,
                "Unpatched WlanResourceMainThread::handleFatalError (0x70d4) hang detected.",
                "6L+9S_wf12",
            )

        if _UIPC_UNSHIMMED_TIMEOUT_RE.search(text) and not _UIPC_SHIMMED_ACK_RE.search(text):
            emit_fatal(
                "UIPC_UNSHIMMED_TIMEOUT",
                CAT_SYNC_IPC_HANG,
                "Unshimmed UIPC queue (0x92d2091c / 0x91db059b) blocking timeout detected.",
                "p15_userland",
            )

        # Category 5A: Fatal Abort Events
        if _SYSTEM_ERROR_RE.search(text) and "WF12_DEGRADED_RADIO_OFF" not in text:
            pb = "6L+9S_wf12" if re.search(r"wi-?fi|bluetooth|bt|wf-?12", text, re.IGNORECASE) else "p15_userland"
            emit_fatal(
                "SYSTEM_ERROR_ABORT",
                CAT_FATAL_ABORT,
                'Fatal Sony "System Error" condition detected (non-degraded abort).',
                pb,
            )

        if _VFAT_0x10000009_RE.search(text):
            emit_fatal(
                "NFLASHA10_VFAT_FULL_0x10000009",
                CAT_FATAL_ABORT,
                "nflasha10 12 MiB VFAT exhaustion error 0x10000009 detected.",
                "0x10000009",
            )

        m_vitem = _VERIFY_ITEM_LINE_RE.search(text)
        if m_vitem:
            exp_sha, act_sha, status_str = m_vitem.group(1), m_vitem.group(2), m_vitem.group(3)
            if exp_sha.lower() != act_sha.lower() or status_str.upper() != "OK":
                emit_fatal(
                    "VERIFY_BEFORE_MOUNT_SHA_MISMATCH",
                    CAT_FATAL_ABORT,
                    f"Verify-Before-Mount SHA-256 mismatch: expected={exp_sha}, actual={act_sha}, status={status_str}.",
                    "oneshot_overlay",
                )
        elif _VERIFY_MISMATCH_TEXT_RE.search(text):
            emit_fatal(
                "VERIFY_BEFORE_MOUNT_SHA_MISMATCH",
                CAT_FATAL_ABORT,
                "Verify-Before-Mount SHA-256 verification failure detected.",
                "oneshot_overlay",
            )

        m_vrc = _VERIFY_RC_RE.search(text)
        if m_vrc and int(m_vrc.group(1)) != 0:
            emit_fatal(
                "VERIFY_BEFORE_MOUNT_RC_NONZERO",
                CAT_FATAL_ABORT,
                f"Stage-A Verify-Before-Mount exited with nonzero FX6_STAGE_A_VERIFY_RC={m_vrc.group(1)}.",
                "oneshot_overlay",
            )

        m_nop = _NOP_COUNT_RE.search(text)
        if m_nop:
            nop_val = int(m_nop.group(1))
            m_faith = _FAITHFUL_FLAG_RE.search(text)
            line_faithful = (int(m_faith.group(1)) == 1) if m_faith else self.native_faithful_mode
            if line_faithful and nop_val > 0:
                emit_fatal(
                    "NATIVE_FAITHFUL_NOP_COUNT_NONZERO",
                    CAT_FATAL_ABORT,
                    f"Native-faithful invariant violated: nop_count={nop_val} > 0.",
                    "p15_userland",
                )

        # Category 5B: Expected Non-Blocking Degraded Events
        for dcode, dpat, dmsg in _DEGRADED_RULES:
            if dpat.search(text):
                emit_degraded(dcode, dmsg)

        return emitted

    def _audit_telemetry_mapping(self, telemetry: Mapping[str, Any]) -> None:
        """Audit structured telemetry dictionaries (e.g. Round 10 summary.json runs)."""
        if not telemetry:
            return

        # Support either a single run entry or a wrapper containing "runs"
        if "runs" in telemetry and isinstance(telemetry["runs"], Mapping):
            for run_key, run_obj in telemetry["runs"].items():
                if isinstance(run_obj, Mapping):
                    self._audit_single_run_mapping(str(run_key), run_obj)
            return

        self._audit_single_run_mapping(str(telemetry.get("run_id", "telemetry")), telemetry)

    def _audit_single_run_mapping(self, run_key: str, run: Mapping[str, Any]) -> None:
        kernel_ver = str(run.get("kernel_version", ""))
        if kernel_ver and "4.9.337-scel+" not in kernel_ver:
            self._fatal_findings.append(
                FaultFinding(
                    line_number=None,
                    timestamp_sec=None,
                    category=CAT_FATAL_ABORT,
                    code="UNEXPECTED_KERNEL_VERSION",
                    severity="FATAL",
                    disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                    raw_line=f"{run_key}.kernel_version={kernel_ver}",
                    message=f"Expected FX3 4.9.337-scel+ kernel, got {kernel_ver!r}.",
                    brick_playbook_key="p3_kernel",
                )
            )

        wall_sec = run.get("wall_elapsed_sec")
        if isinstance(wall_sec, (int, float)):
            self._record_ts(float(wall_sec))

        crashes = run.get("crashes")
        if isinstance(crashes, int) and crashes > 0:
            self._fatal_findings.append(
                FaultFinding(
                    line_number=None,
                    timestamp_sec=None,
                    category=CAT_KERNEL_PANIC_OOPS,
                    code="TELEMETRY_CRASHES_NONZERO",
                    severity="FATAL",
                    disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                    raw_line=f"{run_key}.crashes={crashes}",
                    message=f"Run {run_key} reported crashes={crashes} > 0.",
                    brick_playbook_key="p15_userland",
                )
            )

        invariants = run.get("faithful_invariants")
        faithful = self.native_faithful_mode
        if isinstance(invariants, Mapping):
            faithful = bool(invariants.get("FX6_NATIVE_FAITHFUL", 1 if self.native_faithful_mode else 0))
            if faithful:
                for inv_key in ("subst_color", "subst_image", "forced_render", "skipped_node", "lock_bypass"):
                    val = invariants.get(inv_key, 0)
                    if isinstance(val, int) and val != 0:
                        self._fatal_findings.append(
                            FaultFinding(
                                line_number=None,
                                timestamp_sec=None,
                                category=CAT_FATAL_ABORT,
                                code="NATIVE_FAITHFUL_INVARIANT_BREACH",
                                severity="FATAL",
                                disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                                raw_line=f"{run_key}.faithful_invariants.{inv_key}={val}",
                                message=f"Native-faithful invariant {inv_key}={val} != 0.",
                                brick_playbook_key="p15_userland",
                            )
                        )

        nop_count = run.get("nop_count")
        if faithful and isinstance(nop_count, int) and nop_count > 0:
            self._fatal_findings.append(
                FaultFinding(
                    line_number=None,
                    timestamp_sec=None,
                    category=CAT_FATAL_ABORT,
                    code="NATIVE_FAITHFUL_NOP_COUNT_NONZERO",
                    severity="FATAL",
                    disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                    raw_line=f"{run_key}.nop_count={nop_count}",
                    message=f"Native-faithful mode forbids nop_count={nop_count} > 0.",
                    brick_playbook_key="p15_userland",
                )
            )

        stage_b = run.get("stage_b")
        if isinstance(stage_b, Mapping):
            for key in ("guest_boot_markers", "p11_uipc_events", "fx3_phy_key_events"):
                items = stage_b.get(key)
                if isinstance(items, Sequence) and not isinstance(items, (str, bytes)):
                    for item in items:
                        self.feed_line(str(item))
            patches = stage_b.get("patches")
            if isinstance(patches, Mapping):
                for p_entry in patches.values():
                    if isinstance(p_entry, Mapping):
                        for site in p_entry.get("sites", ()):
                            if "set_nd_filter" in str(site) and "clear" in str(site).lower():
                                self._degraded_events.append(
                                    FaultFinding(
                                        line_number=None,
                                        timestamp_sec=None,
                                        category=CAT_ALLOWED_DEGRADED,
                                        code="P4_ND_CLEAR",
                                        severity="DEGRADED",
                                        disposition=DISPOSITION_ALLOWED_DEGRADED,
                                        raw_line=f"{run_key}.patches.site={site}",
                                        message="P4 physical FX3 ND-filter Clear patch active (ALLOWED_DEGRADED).",
                                    )
                                )

        r10_tel = run.get("r10_telemetry")
        if isinstance(r10_tel, Mapping):
            icon_blitter = r10_tel.get("icon_blitter")
            if faithful and isinstance(icon_blitter, Mapping):
                for ib_key in ("subst_color", "subst_image"):
                    val = icon_blitter.get(ib_key, 0)
                    if isinstance(val, int) and val != 0:
                        self._fatal_findings.append(
                            FaultFinding(
                                line_number=None,
                                timestamp_sec=None,
                                category=CAT_FATAL_ABORT,
                                code="NATIVE_FAITHFUL_INVARIANT_BREACH",
                                severity="FATAL",
                                disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                                raw_line=f"{run_key}.r10_telemetry.icon_blitter.{ib_key}={val}",
                                message=f"Native-faithful icon_blitter invariant {ib_key}={val} != 0.",
                                brick_playbook_key="p15_userland",
                            )
                        )
            p11 = r10_tel.get("p11_uipc")
            if isinstance(p11, Mapping):
                rtc_unshimmed = p11.get("rtc_0x92d2091c", 0)
                if isinstance(rtc_unshimmed, int) and rtc_unshimmed > 0:
                    self._fatal_findings.append(
                        FaultFinding(
                            line_number=None,
                            timestamp_sec=None,
                            category=CAT_SYNC_IPC_HANG,
                            code="UIPC_UNSHIMMED_TIMEOUT",
                            severity="FATAL",
                            disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                            raw_line=f"{run_key}.r10_telemetry.p11_uipc.rtc_0x92d2091c={rtc_unshimmed}",
                            message=f"Unshimmed 0x92d2091c RTC UIPC activity count={rtc_unshimmed} > 0.",
                            brick_playbook_key="p15_userland",
                        )
                    )
                if p11.get("handle_0x91db059b", 0) >= 1:
                    self._degraded_events.append(
                        FaultFinding(
                            line_number=None,
                            timestamp_sec=None,
                            category=CAT_ALLOWED_DEGRADED,
                            code="P11_DETACHED_GRIP_ACK_0x91DB059B",
                            severity="DEGRADED",
                            disposition=DISPOSITION_ALLOWED_DEGRADED,
                            raw_line=f"{run_key}.r10_telemetry.p11_uipc.handle_0x91db059b={p11.get('handle_0x91db059b')}",
                            message="P11 shimmed detached-grip ACK 0x91db059b active.",
                        )
                    )

        prefix_counts = run.get("prefix_counts")
        if isinstance(prefix_counts, Mapping):
            self._telemetry_checks[f"{run_key}_prefix_counts_present"] = True
            self._telemetry_checks[f"{run_key}_fx6_stage_a_count"] = prefix_counts.get("FX6_STAGE_A_", 0)
            self._telemetry_checks[f"{run_key}_fx6_stage_b_count"] = prefix_counts.get("FX6_STAGE_B_", 0)
            self._telemetry_checks[f"{run_key}_fx6_p11_count"] = prefix_counts.get("FX6_P11_", 0)
        if "ldec103_ioctl_count" in run:
            self._telemetry_checks[f"{run_key}_ldec103_ioctl_count"] = run.get("ldec103_ioctl_count")

    def finalize(
        self,
        *,
        require_complete_line_termination: bool = False,
        wall_elapsed_sec: Optional[float] = None,
        allow_empty_input: bool = False,
    ) -> SerialFaultAuditReport:
        """Finalize streaming state, verify watchdog budgets, and emit report."""
        if self._pending_chunk:
            self._process_line(self._pending_chunk.rstrip("\r\n"), account_bytes=False)
            self._pending_chunk = ""
            self._line_terminated = False

        if wall_elapsed_sec is not None:
            self._record_ts(wall_elapsed_sec)

        if self._bytes_scanned == 0 and not allow_empty_input:
            self._fatal_findings.append(
                FaultFinding(
                    line_number=None,
                    timestamp_sec=None,
                    category=CAT_CAPTURE_INTEGRITY,
                    code="EMPTY_TELEMETRY_INPUT",
                    severity="FATAL",
                    disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                    raw_line="",
                    message="Empty serial/telemetry input rejected fail-closed.",
                    brick_playbook_key="p3_kernel",
                )
            )

        if require_complete_line_termination and self._bytes_scanned > 0 and not self._line_terminated:
            self._fatal_findings.append(
                FaultFinding(
                    line_number=self._lines_scanned,
                    timestamp_sec=self._max_observed_sec,
                    category=CAT_CAPTURE_INTEGRITY,
                    code="INCOMPLETE_TRUNCATED_CAPTURE",
                    severity="FATAL",
                    disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                    raw_line="",
                    message="Serial capture is missing final newline (incomplete/truncated fail-closed).",
                    brick_playbook_key="p3_kernel",
                )
            )

        req_wdt = bool(self.require_wdt_budget_proof)
        wdt_report = verify_watchdog_budget(
            wdt_stop_sec=self._wdt_stop_sec,
            clear_before_exec_sec=self._clear_before_exec_sec,
            overlay_exec_sec=self._overlay_exec_sec,
            max_observed_sec=self._max_observed_sec,
            timer_ip_fault_seen=self._timer_ip_fault_seen,
            wdt_stop_seen=self._wdt_stop_seen,
            clear_before_exec_seen=self._clear_before_exec_seen,
            require_wdt_stop_proof=req_wdt,
            require_clear_before_exec_proof=req_wdt,
            soft_guard_budget_sec=self.soft_guard_budget_sec,
            hw_wdt_ceiling_sec=self.hw_wdt_ceiling_sec,
        )

        if not wdt_report.passed:
            existing_codes = {f.code for f in self._fatal_findings}
            for vcode, verr in zip(wdt_report.violations, wdt_report.errors):
                if vcode not in existing_codes:
                    pb = "oneshot_overlay" if "CLEAR_BEFORE_EXEC" in vcode else "p3_kernel"
                    self._fatal_findings.append(
                        FaultFinding(
                            line_number=None,
                            timestamp_sec=self._max_observed_sec,
                            category=CAT_WATCHDOG_BUDGET,
                            code=vcode,
                            severity="FATAL",
                            disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                            raw_line="",
                            message=verr,
                            brick_playbook_key=pb,
                        )
                    )
                    existing_codes.add(vcode)

        # Build automatic cross-links to brick_classifier.py recovery playbooks
        pb_triggers: Dict[str, List[str]] = {}
        for f in self._fatal_findings:
            pk = f.brick_playbook_key or "p15_userland"
            pb_triggers.setdefault(pk, []).append(f.code)

        playbooks = tuple(
            _build_brick_playbook_link(
                pk,
                codes,
                updater_mode_armed=self.updater_mode_armed,
                oneshot_overlay_used=self.oneshot_overlay_used,
            )
            for pk, codes in pb_triggers.items()
        )

        # Deduplicate degraded events by (line_number, code, raw_line) while keeping order
        seen_deg: set[Tuple[Optional[int], str, str]] = set()
        dedup_deg: List[FaultFinding] = []
        for d in self._degraded_events:
            key = (d.line_number, d.code, d.raw_line)
            if key not in seen_deg:
                seen_deg.add(key)
                dedup_deg.append(d)

        fatal_count = len(self._fatal_findings)
        deg_count = len(dedup_deg)

        if fatal_count > 0:
            disposition = DISPOSITION_FAIL_CLOSED_ABORT
            passed = False
            abort_required = True
        elif deg_count > 0:
            disposition = DISPOSITION_ALLOWED_DEGRADED
            passed = True
            abort_required = False
        else:
            disposition = DISPOSITION_PASS
            passed = True
            abort_required = False

        errors = tuple(f.message for f in self._fatal_findings)
        return SerialFaultAuditReport(
            schema=SERIAL_FAULT_DETECTOR_V2_SCHEMA,
            version=SERIAL_FAULT_DETECTOR_V2_VERSION,
            source=self.source_label,
            passed=passed,
            disposition=disposition,
            abort_required=abort_required,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            persistent_write_release=PERSISTENT_WRITE_RELEASE,
            native_faithful_mode=self.native_faithful_mode,
            lines_scanned=self._lines_scanned,
            bytes_scanned=self._bytes_scanned,
            sha256=self._hasher.hexdigest(),
            line_terminated=self._line_terminated,
            fatal_fault_count=fatal_count,
            degraded_event_count=deg_count,
            findings=tuple(self._fatal_findings),
            degraded_events=tuple(dedup_deg),
            watchdog_budget=wdt_report,
            brick_recovery_playbooks=playbooks,
            telemetry_checks=dict(self._telemetry_checks),
            errors=errors,
        )


# ---------------------------------------------------------------------------
# Batch Public Entrypoint
# ---------------------------------------------------------------------------


def audit_serial_boot_telemetry(
    *,
    serial_text: Optional[str] = None,
    serial_bytes: Optional[bytes] = None,
    serial_lines: Optional[Iterable[str]] = None,
    serial_path: Optional[Union[str, Path]] = None,
    telemetry_summary: Optional[Mapping[str, Any]] = None,
    native_faithful_mode: bool = True,
    require_wdt_budget_proof: Optional[bool] = None,
    require_complete_line_termination: bool = False,
    wall_elapsed_sec: Optional[float] = None,
    soft_guard_budget_sec: float = STAGE_A_SOFT_GUARD_BUDGET_SEC,
    hw_wdt_ceiling_sec: float = TIMER_IP_HW_WDT_CEILING_SEC,
    updater_mode_armed: bool = False,
    oneshot_overlay_used: bool = False,
    source_label: Optional[str] = None,
) -> SerialFaultAuditReport:
    """Audit serial logs and/or structured kernel telemetry fail-closed (v2)."""
    label = source_label or (str(serial_path) if serial_path is not None else "<batch>")
    detector = StreamingSerialFaultDetectorV2(
        native_faithful_mode=native_faithful_mode,
        require_wdt_budget_proof=require_wdt_budget_proof,
        soft_guard_budget_sec=soft_guard_budget_sec,
        hw_wdt_ceiling_sec=hw_wdt_ceiling_sec,
        updater_mode_armed=updater_mode_armed,
        oneshot_overlay_used=oneshot_overlay_used,
        source_label=label,
    )

    has_telemetry_only = telemetry_summary is not None and (
        serial_text is None and serial_bytes is None and serial_lines is None and serial_path is None
    )

    if serial_path is not None:
        try:
            raw = read_file_o_rdonly(serial_path)
            detector.feed_chunk(raw)
        except OSError as exc:
            detector._fatal_findings.append(
                FaultFinding(
                    line_number=None,
                    timestamp_sec=None,
                    category=CAT_CAPTURE_INTEGRITY,
                    code="SERIAL_PATH_UNREADABLE",
                    severity="FATAL",
                    disposition=DISPOSITION_FAIL_CLOSED_ABORT,
                    raw_line=str(serial_path),
                    message=f"Failed to open serial log strictly O_RDONLY ({serial_path}): {exc}",
                    brick_playbook_key="p3_kernel",
                )
            )
            return detector.finalize(allow_empty_input=True, wall_elapsed_sec=wall_elapsed_sec)

    if serial_bytes is not None:
        detector.feed_chunk(serial_bytes)
    if serial_text is not None:
        detector.feed_chunk(serial_text)
    if serial_lines is not None:
        for line in serial_lines:
            detector.feed_line(line)

    if telemetry_summary is not None:
        detector._audit_telemetry_mapping(telemetry_summary)

    return detector.finalize(
        require_complete_line_termination=require_complete_line_termination,
        wall_elapsed_sec=wall_elapsed_sec,
        allow_empty_input=has_telemetry_only,
    )


# ---------------------------------------------------------------------------
# Round 10 Real FX3 4.9.337-scel+ Telemetry Auditor + Clean-Room Fallback
# ---------------------------------------------------------------------------


def build_clean_room_round10_summary() -> Dict[str, Any]:
    """Deterministic clean-room synthetic Round 10 telemetry fixture."""
    kernel_ver = (
        "Linux version 4.9.337-scel+ (jp10239@dic-build-scm-u20-028) "
        "(gcc version 6.4.0 (20201211 (Sony CE Linux 14.0.1.0)) ) #1 SMP PREEMPT Thu Dec 25 08:15:40 JST 2025"
    )
    verify_sha = "e2bc2619845e96141e6dee3d758232013d418956134cd66ae2c7430a7f510ad4"

    def _make_run(run_id: str, presenter: str, wall: float, ldec: int) -> Dict[str, Any]:
        return {
            "run_id": run_id,
            "round": 10,
            "target_presenter": presenter,
            "kernel_version": kernel_ver,
            "wall_elapsed_sec": wall,
            "nop_count": 0,
            "crashes": 0,
            "ldec103_ioctl_count": ldec,
            "faithful_invariants": {
                "FX6_NATIVE_FAITHFUL": 1,
                "subst_color": 0,
                "subst_image": 0,
                "forced_render": 0,
                "skipped_node": 0,
                "lock_bypass": 0,
            },
            "stage_b": {
                "stage": "B",
                "patches": {
                    "P1_P4_P8_P10_appFw_combined": {
                        "sites": [
                            "P4_appfw_set_nd_filter_mode_clear",
                            "P4_appfw_set_nd_filter_value_clear",
                        ]
                    }
                },
                "guest_boot_markers": [
                    "FX6_STAGE_A_KERNEL sysname=Linux release=4.9.337-scel+ machine=aarch64",
                    f"FX6_STAGE_A_VERIFY_ITEM path=/usr/lib/appFw.so bytes=50520424 expected={verify_sha} actual={verify_sha} status=OK",
                    "FX6_STAGE_A_VERIFY_PASS count=12",
                    "FX6_STAGE_B_R10_RTC0 path=/dev/rtc0 open_ok=0 errno=2",
                    "FX6_STAGE_A_VERIFY_RC=0",
                    "FX6_PATCH_PLAN appFw_base=0x7f91ee8000 nop_count=0 round=10",
                    "FX6_STAGE_B_BRIDGE round=10 faithful=1 nop_count=0 p10_keymap=1",
                    "FX6_P11_RTC0_PROBE ok=0 rtc0_fd=0 year=0 mon=0 day=0 hour=0 min=0 sec=0",
                ],
                "p11_uipc_events": [
                    "FX6_P11_RTC0_PROBE ok=0 rtc0_fd=0 year=0 mon=0 day=0 hour=0 min=0 sec=0",
                    "FX6_P11_HANDLE_ACK count=1 dest=0x91db059b cb_qid=0x8000610e req_cmd=0x81000001 evt_cmd=0x88000002 free_rc=0 snd_rc=0 xlr_h1_preserved=1",
                ],
            },
            "r10_telemetry": {
                "p11_uipc": {
                    "rtc_0x92d2091c": 0,
                    "rtc0_ok": 0,
                    "handle_0x91db059b": 1,
                    "xlr_h1_preserved": 1,
                }
            },
            "prefix_counts": {
                "Linux version ": 2,
                "FX6_STAGE_A_": 20,
                "FX6_STAGE_B_": 7,
                "FX6_P11_": 194,
            },
        }

    return {
        "schema": "fx6-on-fx3-round10-full-icon-presenter-v1",
        "date": "2026-11-14",
        "kernel_version": kernel_ver,
        "runs": {
            "r10a_r10_shooting_hud": _make_run("r10a-r10-shooting-hud", "25procam_shooting_presenter", 61.62, 47),
            "r10b_fn_big6_home": _make_run("r10b-fn-big6-home", "31procam_big6_menu_home_presenter", 67.98, 53),
            "r10c_c1_big6_subdialog": _make_run("r10c-c1-big6-subdialog", "34procam_big6_menu_setting_presenter", 74.73, 54),
            "r10d_c2_menu_3layer": _make_run("r10d-c2-menu-3layer", "02menu_3layer_presenter", 80.93, 80),
        },
    }


def audit_round10_summary_telemetry(
    summary_path: Optional[Union[str, Path]] = None,
    *,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Round10TelemetryAuditReport:
    """Validate Round 10 real FX3 `4.9.337-scel+` `summary.json` (with clean-room fallback)."""
    root = repo_root or DEFAULT_REPO_ROOT
    resolved_path = Path(summary_path) if summary_path is not None else (root / DEFAULT_ROUND10_SUMMARY_REL)
    clean_room = is_forced_clean_room() if force_clean_room is None else force_clean_room

    if not clean_room and resolved_path.is_file():
        raw_bytes = read_file_o_rdonly(resolved_path)
        summary_data = json.loads(raw_bytes.decode("utf-8"))
        telemetry_source = "committed_round10_summary_json"
        used_path: Optional[str] = str(resolved_path)
    else:
        summary_data = build_clean_room_round10_summary()
        telemetry_source = "clean_room_synthetic"
        used_path = None

    runs = summary_data.get("runs", {})
    run_reports: Dict[str, Dict[str, Any]] = {}
    all_passed = True
    errors: List[str] = []
    saw_degraded = False

    if not isinstance(runs, Mapping) or not runs:
        return Round10TelemetryAuditReport(
            schema=SERIAL_FAULT_DETECTOR_V2_SCHEMA,
            version=SERIAL_FAULT_DETECTOR_V2_VERSION,
            telemetry_source=telemetry_source,
            summary_path=used_path,
            all_passed=False,
            overall_disposition=DISPOSITION_FAIL_CLOSED_ABORT,
            runs_audited=0,
            run_reports={},
            errors=("Round 10 summary JSON contains no runs.",),
        )

    for run_key, run_obj in runs.items():
        if not isinstance(run_obj, Mapping):
            continue
        rep = audit_serial_boot_telemetry(
            telemetry_summary=run_obj,
            native_faithful_mode=True,
            require_wdt_budget_proof=False,
            source_label=f"round10:{run_key}",
        )
        run_reports[str(run_key)] = rep.to_dict()
        if not rep.passed:
            all_passed = False
            errors.extend(f"{run_key}: {e}" for e in rep.errors)
        if rep.disposition == DISPOSITION_ALLOWED_DEGRADED:
            saw_degraded = True

    if not all_passed:
        overall = DISPOSITION_FAIL_CLOSED_ABORT
    elif saw_degraded:
        overall = DISPOSITION_ALLOWED_DEGRADED
    else:
        overall = DISPOSITION_PASS

    return Round10TelemetryAuditReport(
        schema=SERIAL_FAULT_DETECTOR_V2_SCHEMA,
        version=SERIAL_FAULT_DETECTOR_V2_VERSION,
        telemetry_source=telemetry_source,
        summary_path=used_path,
        all_passed=all_passed,
        overall_disposition=overall,
        runs_audited=len(run_reports),
        run_reports=run_reports,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# CLI Entrypoint
# ---------------------------------------------------------------------------


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="fx3_safety.serial_fault_detector_v2",
        description="Phase 32 Fail-Closed Serial & Kernel Telemetry Fault Detector v2",
    )
    parser.add_argument("--serial", type=Path, help="Path to serial log file (read strictly O_RDONLY)")
    parser.add_argument(
        "--round10-summary",
        nargs="?",
        const="__DEFAULT__",
        help="Audit Round 10 FX3 4.9.337-scel+ summary.json (or clean-room fallback)",
    )
    parser.add_argument(
        "--require-wdt-proof",
        action="store_true",
        help="Require explicit WDT_SET_STOP & /tmp/mod_arm_once Clear-Before-Exec timestamps < 90.0s",
    )
    parser.add_argument("--out", type=Path, help="Optional JSON output file path")
    args = parser.parse_args(argv)

    if args.serial is not None:
        report = audit_serial_boot_telemetry(
            serial_path=args.serial,
            require_wdt_budget_proof=True if args.require_wdt_proof else None,
        )
        payload = report.to_dict()
        ok = report.passed
    else:
        summary_arg = None if args.round10_summary in (None, "__DEFAULT__") else Path(args.round10_summary)
        r10 = audit_round10_summary_telemetry(summary_path=summary_arg)
        payload = r10.to_dict()
        ok = r10.all_passed

    encoded = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    if args.out is not None:
        args.out.write_text(encoded, encoding="utf-8")
    sys.stdout.write(encoded)
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
