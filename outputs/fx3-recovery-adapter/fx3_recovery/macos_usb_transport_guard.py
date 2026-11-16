"""macOS 26+ IOUSBHost (0xe00002be) Transport Guard, Senser v1/v2 Classifier & Jiritsu Auditor.

Aligned with `pmca-re-reloaded v1.12.1` and `JIRITSU_CHANNEL.md` findings:
1. Models the deterministic USB session state machine from MSC (`054C:0DA1`) ->
   macOS 26+ mass-storage driver quiescence wait -> `0xe00002be` (`kIOReturnExclusiveAccess`)
   exponential backoff + `IOUSBHost` claim fallback -> Vendor Control
   (`bmRequestType=0x43, bRequest=1, wValue=0x37FF, wIndex=0xD7AA`) ->
   USB STALL non-retransmit rule -> `054C:0336` service mode.
2. Classifies Senser v1 (3..7 round challenge supported on FX3 `0x91030080`) vs
   Senser v2 (RSA-signed challenge on newer bodies such as `ILCE-7M5`) and fails
   closed without attempting brute-force or forged signatures.
3. Audits `AdjustControl (PFUNC=0x40, block=0x1001)` Jiritsu commands under a
   hard-locked read-only Tier-0 capture policy: blocks `0x4003 FORMAT`, `0x4006 FIRMUP`,
   `0x4005 DEBUG`, `0x4007`/`0x4010` writes, and `/tmp/jiritsu/../..` path traversal,
   while permitting read-only Tier-0 capture flow (`0x4002 MOUNT`, `0x4008 GET_FILE`,
   `0x4011 GET_FILE2`, and safe read-only `0x400F SET_FILE_PATH`).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
import posixpath
from typing import Dict, List, Optional, Sequence, Tuple


# Hard-locked read-only safety policy
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False

# Sony USB identities
FX3_MSC_VID_PID: str = "054C:0DA1"
KNOWN_SONY_MSC_VID_PIDS: Tuple[str, ...] = (
    "054C:0DA1",  # ILME-FX3 MSC
    "054C:0E0E",  # ILME-FX30 MSC
    "054C:0E8A",  # ILCE-7CM2 (A7C II) MSC
    "054C:0DA3",  # PTP / MTP
    "054C:0994",  # Charging / legacy MSC
)
SONY_SERVICE_VID_PID: str = "054C:0336"
FX3_MODEL_ID: int = 0x91030080

# Vendor Control handshake (MSC -> Service Mode switch trigger)
VENDOR_CONTROL_BM_REQUEST_TYPE: int = 0x43
VENDOR_CONTROL_B_REQUEST: int = 1
VENDOR_CONTROL_W_VALUE: int = 0x37FF
VENDOR_CONTROL_W_INDEX: int = 0xD7AA

# macOS 26+ IOUSBHost / IOUSBLib status codes
K_IORETURN_SUCCESS: int = 0x00000000
K_IORETURN_EXCLUSIVE_ACCESS: int = 0xE00002BE
K_IOUSB_PIPE_STALLED: int = 0xE000404F

MACOS_CONTENTION_MIN_MAJOR: int = 26
DEFAULT_MSC_QUIESCENCE_MS: int = 350
DEFAULT_BACKOFF_BASE_MS: int = 50
DEFAULT_BACKOFF_CAP_MS: int = 800
DEFAULT_MAX_CLAIM_RETRIES: int = 4

# Senser authentication parameters
SENSER_V1_MIN_ROUNDS: int = 3
SENSER_V1_MAX_ROUNDS: int = 7
FX3_SENSER_V1_ROUNDS: int = 7
SENSER_V2_KNOWN_MODELS: Tuple[str, ...] = ("ILCE-7M5", "A7V", "A7_V")

# Jiritsu AdjustControl channel constants (libsencore.so command table)
JIRITSU_PFUNC: int = 0x40
JIRITSU_BLOCK: int = 0x1001
JIRITSU_SET_FILE_PATH_MIN_LEN: int = 2
JIRITSU_SET_FILE_PATH_MAX_LEN: int = 513

JIRITSU_CODE_MOUNT: int = 0x4002
JIRITSU_CODE_FORMAT: int = 0x4003
JIRITSU_CODE_DEBUG: int = 0x4005
JIRITSU_CODE_FIRMUP: int = 0x4006
JIRITSU_CODE_SET_FILE: int = 0x4007
JIRITSU_CODE_GET_FILE: int = 0x4008
JIRITSU_CODE_SET_FILE_PATH: int = 0x400F
JIRITSU_CODE_SET_FILE2: int = 0x4010
JIRITSU_CODE_GET_FILE2: int = 0x4011

JIRITSU_CODE_NAMES: Dict[int, str] = {
    JIRITSU_CODE_MOUNT: "MOUNT",
    JIRITSU_CODE_FORMAT: "FORMAT",
    JIRITSU_CODE_DEBUG: "DEBUG",
    JIRITSU_CODE_FIRMUP: "FIRMUP",
    JIRITSU_CODE_SET_FILE: "SET_FILE",
    JIRITSU_CODE_GET_FILE: "GET_FILE",
    JIRITSU_CODE_SET_FILE_PATH: "SET_FILE_PATH",
    JIRITSU_CODE_SET_FILE2: "SET_FILE2",
    JIRITSU_CODE_GET_FILE2: "GET_FILE2",
}

_SAFE_READONLY_PATH_PREFIXES: Tuple[str, ...] = (
    "/tmp/jiritsu/",
    "/mnt/fx3_tier0_backup/",
    "/log/",
)

_FORBIDDEN_TARGET_PATH_PREFIXES: Tuple[str, ...] = (
    "/etc/",
    "/usr/",
    "/bin/",
    "/sbin/",
    "/lib/",
    "/setting/",
    "/dev/",
    "/boot/",
)


class TransportState(str, Enum):
    DISCONNECTED = "DISCONNECTED"
    MSC_DETECTED = "MSC_DETECTED"
    WAITING_MSC_QUIESCENCE = "WAITING_MSC_QUIESCENCE"
    CLAIM_BACKOFF = "CLAIM_BACKOFF"
    IOUSBHOST_CLAIMED = "IOUSBHOST_CLAIMED"
    VENDOR_CONTROL_SENT = "VENDOR_CONTROL_SENT"
    SERVICE_MODE_ACTIVE = "SERVICE_MODE_ACTIVE"
    STALL_ABORTED_NO_RETRANSMIT = "STALL_ABORTED_NO_RETRANSMIT"
    FAILED_CLOSED_SENSER_V2 = "FAILED_CLOSED_SENSER_V2"
    FAILED_CLOSED_EXCLUSIVE_ACCESS = "FAILED_CLOSED_EXCLUSIVE_ACCESS"


@dataclass(frozen=True)
class SenserChallenge:
    senser_version: int = 1
    auth_scheme: str = "xor_round_challenge"  # or "rsa_signature"
    challenge_rounds: int = FX3_SENSER_V1_ROUNDS
    model_name: str = "ILME-FX3"
    model_id: int = FX3_MODEL_ID
    rsa_modulus_bits: int = 0


@dataclass(frozen=True)
class SenserClassification:
    supported: bool
    senser_version: int
    status: str
    service_vid_pid: str
    rounds_required: int
    fail_closed: bool
    reason: str


@dataclass(frozen=True)
class ClaimAttemptRecord:
    attempt: int
    backend: str
    return_code_hex: str
    backoff_ms: int
    claimed: bool


@dataclass(frozen=True)
class ClaimResult:
    success: bool
    status: str
    active_backend: str
    exclusive_access_retries: int
    backoff_schedule_ms: List[int]
    attempts: List[ClaimAttemptRecord]
    errors: List[str]


@dataclass(frozen=True)
class VendorControlResult:
    success: bool
    status: str
    bm_request_type: int
    b_request: int
    w_value: int
    w_index: int
    usb_stall_detected: bool
    retransmit_count: int
    errors: List[str]


@dataclass(frozen=True)
class JiritsuCommand:
    pfunc: int
    block: int
    code: int
    file_path: Optional[str] = None


@dataclass(frozen=True)
class JiritsuAuditDecision:
    allowed: bool
    status: str
    pfunc: int
    block: int
    code: int
    code_name: str
    file_path: Optional[str]
    reason: str


@dataclass(frozen=True)
class JiritsuSequenceAudit:
    allowed: bool
    status: str
    allow_persistent_writes: bool
    decisions: List[JiritsuAuditDecision]
    blocked_codes: List[str]
    permitted_codes: List[str]
    errors: List[str]
    warnings: List[str]


def compute_exclusive_access_backoff_ms(
    attempt_index: int,
    *,
    base_ms: int = DEFAULT_BACKOFF_BASE_MS,
    cap_ms: int = DEFAULT_BACKOFF_CAP_MS,
) -> int:
    """Compute bounded exponential backoff (ms) for macOS 26+ `0xe00002be` contention."""
    if attempt_index < 0 or base_ms <= 0 or cap_ms < base_ms:
        raise ValueError("Invalid backoff parameters")
    return min(cap_ms, base_ms * (1 << attempt_index))


def classify_senser_challenge(challenge: SenserChallenge) -> SenserClassification:
    """Classify `054C:0336` Senser v1 (FX3 3..7 round) vs Senser v2 (RSA challenge fail-closed)."""
    norm_model = challenge.model_name.strip().upper()
    norm_scheme = challenge.auth_scheme.strip().lower()

    is_v2 = (
        challenge.senser_version >= 2
        or "rsa" in norm_scheme
        or challenge.rsa_modulus_bits > 0
        or norm_model in SENSER_V2_KNOWN_MODELS
    )
    if is_v2:
        return SenserClassification(
            supported=False,
            senser_version=2 if challenge.senser_version < 2 else challenge.senser_version,
            status="BLOCKED_SENSER_V2_RSA_UNSUPPORTED",
            service_vid_pid="NONE_FAIL_CLOSED",
            rounds_required=0,
            fail_closed=True,
            reason=(
                f"Senser v2 RSA-signed service authentication detected (model={challenge.model_name!r}, "
                f"scheme={challenge.auth_scheme!r}): vendor private key is absent; failing closed without "
                "entering 054C:0336."
            ),
        )

    if challenge.senser_version != 1 or norm_scheme not in ("xor_round_challenge", "senser_v1", "challenge_response"):
        return SenserClassification(
            supported=False,
            senser_version=challenge.senser_version,
            status="BLOCKED_UNKNOWN_SENSER_SCHEME",
            service_vid_pid="NONE_FAIL_CLOSED",
            rounds_required=0,
            fail_closed=True,
            reason=f"Unrecognized Senser authentication scheme {challenge.auth_scheme!r} (fail-closed).",
        )

    if not (SENSER_V1_MIN_ROUNDS <= challenge.challenge_rounds <= SENSER_V1_MAX_ROUNDS):
        return SenserClassification(
            supported=False,
            senser_version=1,
            status="BLOCKED_INVALID_SENSER_V1_ROUNDS",
            service_vid_pid="NONE_FAIL_CLOSED",
            rounds_required=challenge.challenge_rounds,
            fail_closed=True,
            reason=(
                f"Senser v1 requires {SENSER_V1_MIN_ROUNDS}..{SENSER_V1_MAX_ROUNDS} challenge rounds, "
                f"got {challenge.challenge_rounds}."
            ),
        )

    return SenserClassification(
        supported=True,
        senser_version=1,
        status="SUPPORTED_SENSER_V1",
        service_vid_pid=SONY_SERVICE_VID_PID,
        rounds_required=challenge.challenge_rounds,
        fail_closed=False,
        reason=(
            f"Senser v1 {challenge.challenge_rounds}-round challenge supported for {challenge.model_name} "
            f"(Model ID {hex(challenge.model_id)}) -> transitions to {SONY_SERVICE_VID_PID}."
        ),
    )


def _validate_safe_jiritsu_read_path(path: Optional[str]) -> Tuple[bool, str, str]:
    if path is None or not isinstance(path, str):
        return False, "BLOCKED_INVALID_JIRITSU_PATH", "SET_FILE_PATH requires a non-empty string path."
    raw_len = len(path.encode("utf-8", errors="replace"))
    if raw_len < JIRITSU_SET_FILE_PATH_MIN_LEN or raw_len > JIRITSU_SET_FILE_PATH_MAX_LEN:
        return (
            False,
            "BLOCKED_INVALID_JIRITSU_PATH",
            f"SET_FILE_PATH length {raw_len} outside protocol bounds [{JIRITSU_SET_FILE_PATH_MIN_LEN}..{JIRITSU_SET_FILE_PATH_MAX_LEN}].",
        )
    if "\x00" in path or "\\" in path or not path.startswith("/"):
        return False, "BLOCKED_PATH_TRAVERSAL_OR_PERSISTENT_WRITE", f"Unsafe non-POSIX or relative path {path!r}."

    segments = [seg for seg in path.split("/") if seg]
    if ".." in segments or "." in segments:
        return (
            False,
            "BLOCKED_PATH_TRAVERSAL_OR_PERSISTENT_WRITE",
            f"Path traversal segment rejected in {path!r} (blocks /tmp/jiritsu/../.. exploit chain).",
        )

    normalized = posixpath.normpath(path)
    for forbidden in _FORBIDDEN_TARGET_PATH_PREFIXES:
        if normalized == forbidden.rstrip("/") or normalized.startswith(forbidden):
            return (
                False,
                "BLOCKED_PATH_TRAVERSAL_OR_PERSISTENT_WRITE",
                f"Target path {normalized!r} touches protected system prefix {forbidden!r}.",
            )

    if not any(normalized.startswith(prefix) for prefix in _SAFE_READONLY_PATH_PREFIXES):
        return (
            False,
            "BLOCKED_PATH_TRAVERSAL_OR_PERSISTENT_WRITE",
            f"Path {normalized!r} outside read-only Tier-0 capture prefixes {_SAFE_READONLY_PATH_PREFIXES}.",
        )

    return True, "PERMITTED_READONLY_JIRITSU", f"Read-only SET_FILE_PATH {normalized!r} validated."


def audit_jiritsu_command(
    pfunc: int,
    block: int,
    code: int,
    *,
    file_path: Optional[str] = None,
    allow_persistent_writes: bool = False,
) -> JiritsuAuditDecision:
    """Audit a single `AdjustControl (PFUNC=0x40, block=0x1001)` Jiritsu command."""
    _ = allow_persistent_writes  # Hard-locked to False
    code_name = JIRITSU_CODE_NAMES.get(code, f"UNKNOWN_{hex(code)}")

    if pfunc != JIRITSU_PFUNC or block != JIRITSU_BLOCK:
        return JiritsuAuditDecision(
            allowed=False,
            status="BLOCKED_INVALID_JIRITSU_TARGET",
            pfunc=pfunc,
            block=block,
            code=code,
            code_name=code_name,
            file_path=file_path,
            reason=f"Expected PFUNC={hex(JIRITSU_PFUNC)}, block={hex(JIRITSU_BLOCK)}; got ({hex(pfunc)}, {hex(block)}).",
        )

    if code == JIRITSU_CODE_FORMAT:
        return JiritsuAuditDecision(
            allowed=False,
            status="BLOCKED_DESTRUCTIVE_JIRITSU_FORMAT",
            pfunc=pfunc,
            block=block,
            code=code,
            code_name=code_name,
            file_path=file_path,
            reason="Jiritsu 0x4003 FORMAT is unconditionally blocked under Tier-0 read-only safety policy.",
        )

    if code == JIRITSU_CODE_FIRMUP:
        return JiritsuAuditDecision(
            allowed=False,
            status="BLOCKED_DESTRUCTIVE_JIRITSU_FIRMUP",
            pfunc=pfunc,
            block=block,
            code=code,
            code_name=code_name,
            file_path=file_path,
            reason="Jiritsu 0x4006 FIRMUP is unconditionally blocked under Tier-0 read-only safety policy.",
        )

    if code in (JIRITSU_CODE_SET_FILE, JIRITSU_CODE_SET_FILE2):
        return JiritsuAuditDecision(
            allowed=False,
            status="BLOCKED_PERSISTENT_JIRITSU_WRITE",
            pfunc=pfunc,
            block=block,
            code=code,
            code_name=code_name,
            file_path=file_path,
            reason=f"Jiritsu {hex(code)} {code_name} writes to camera filesystem and is blocked in read-only Tier-0 capture.",
        )

    if code == JIRITSU_CODE_DEBUG:
        return JiritsuAuditDecision(
            allowed=False,
            status="BLOCKED_JIRITSU_CODE_EXECUTION",
            pfunc=pfunc,
            block=block,
            code=code,
            code_name=code_name,
            file_path=file_path,
            reason="Jiritsu 0x4005 DEBUG triggers im.elf dlopen() EUID=0 payload execution and is blocked in read-only guard.",
        )

    if code == JIRITSU_CODE_SET_FILE_PATH:
        ok, status, reason = _validate_safe_jiritsu_read_path(file_path)
        return JiritsuAuditDecision(
            allowed=ok,
            status=status,
            pfunc=pfunc,
            block=block,
            code=code,
            code_name=code_name,
            file_path=file_path,
            reason=reason,
        )

    if code in (JIRITSU_CODE_MOUNT, JIRITSU_CODE_GET_FILE, JIRITSU_CODE_GET_FILE2):
        return JiritsuAuditDecision(
            allowed=True,
            status="PERMITTED_READONLY_JIRITSU",
            pfunc=pfunc,
            block=block,
            code=code,
            code_name=code_name,
            file_path=file_path,
            reason=f"Read-only Tier-0 capture command {hex(code)} ({code_name}) permitted.",
        )

    return JiritsuAuditDecision(
        allowed=False,
        status="BLOCKED_UNKNOWN_JIRITSU_COMMAND",
        pfunc=pfunc,
        block=block,
        code=code,
        code_name=code_name,
        file_path=file_path,
        reason=f"Unknown Jiritsu command code {hex(code)} rejected (fail-closed).",
    )


def audit_jiritsu_sequence(
    commands: Sequence[JiritsuCommand],
    *,
    allow_persistent_writes: bool = False,
) -> JiritsuSequenceAudit:
    """Audit a sequence of `AdjustControl` Jiritsu commands under hard-locked read-only policy."""
    warnings: List[str] = []
    if allow_persistent_writes:
        warnings.append(
            "Caller attempted to set allow_persistent_writes=True; policy hard-locks it to False."
        )

    decisions: List[JiritsuAuditDecision] = []
    blocked: List[str] = []
    permitted: List[str] = []
    errors: List[str] = []

    for cmd in commands:
        dec = audit_jiritsu_command(
            cmd.pfunc,
            cmd.block,
            cmd.code,
            file_path=cmd.file_path,
            allow_persistent_writes=False,
        )
        decisions.append(dec)
        if dec.allowed:
            permitted.append(f"{hex(cmd.code)}:{dec.code_name}")
        else:
            blocked.append(f"{hex(cmd.code)}:{dec.code_name}")
            errors.append(dec.reason)

    allowed = len(errors) == 0 and len(blocked) == 0
    if not allowed:
        status = decisions[[d.allowed for d in decisions].index(False)].status
    else:
        status = "PERMITTED_READONLY_JIRITSU_FLOW"

    return JiritsuSequenceAudit(
        allowed=allowed,
        status=status,
        allow_persistent_writes=ALLOW_PERSISTENT_JIRITSU_WRITES,
        decisions=decisions,
        blocked_codes=blocked,
        permitted_codes=permitted,
        errors=errors,
        warnings=warnings,
    )


class MacOSUSBTransportSession:
    """Deterministic macOS 26+ USB host session state machine for FX3 recovery/capture."""

    def __init__(self, *, macos_major: int = 26, min_quiescence_ms: int = DEFAULT_MSC_QUIESCENCE_MS) -> None:
        self.macos_major: int = macos_major
        self.min_quiescence_ms: int = min_quiescence_ms
        self.state: TransportState = TransportState.DISCONNECTED
        self.vid_pid: str = ""
        self.model_name: str = ""
        self.model_id: int = 0
        self.msc_quiescent: bool = False
        self.active_backend: str = ""
        self.total_backoff_ms: int = 0
        self.retransmit_count: int = 0
        self.history: List[str] = [self.state.value]

    def _transition(self, new_state: TransportState) -> None:
        self.state = new_state
        self.history.append(new_state.value)

    def attach_msc(
        self,
        *,
        vid_pid: str = FX3_MSC_VID_PID,
        model_name: str = "ILME-FX3",
        model_id: int = FX3_MODEL_ID,
    ) -> TransportState:
        norm_vp = vid_pid.strip().upper()
        if norm_vp not in KNOWN_SONY_MSC_VID_PIDS:
            raise ValueError(f"Unsupported Sony MSC/PTP VID:PID {vid_pid!r}")
        self.vid_pid = norm_vp
        self.model_name = model_name
        self.model_id = model_id
        self.msc_quiescent = False
        self._transition(TransportState.MSC_DETECTED)
        return self.state

    def wait_for_msc_quiescence(
        self,
        *,
        waited_ms: int,
        driver_quiescent: bool,
    ) -> Tuple[bool, str]:
        """Wait for macOS 26+ mass-storage driver quiescence prior to interface claim."""
        if self.state not in (TransportState.MSC_DETECTED, TransportState.WAITING_MSC_QUIESCENCE):
            return False, f"BLOCKED_INVALID_STATE_FOR_QUIESCENCE:{self.state.value}"

        self._transition(TransportState.WAITING_MSC_QUIESCENCE)
        if self.macos_major >= MACOS_CONTENTION_MIN_MAJOR:
            if not driver_quiescent or waited_ms < self.min_quiescence_ms:
                return (
                    False,
                    f"BLOCKED_MSC_DRIVER_ACTIVE: macOS {self.macos_major}+ requires driver_quiescent=True "
                    f"and waited_ms >= {self.min_quiescence_ms}ms (got driver_quiescent={driver_quiescent}, waited_ms={waited_ms})",
                )
        self.msc_quiescent = True
        return True, "MSC_QUIESCENT_READY"

    def claim_interface(
        self,
        attempt_return_codes: Sequence[int],
        *,
        use_iousbhost_fallback: bool = True,
        base_backoff_ms: int = DEFAULT_BACKOFF_BASE_MS,
        cap_backoff_ms: int = DEFAULT_BACKOFF_CAP_MS,
    ) -> ClaimResult:
        """Attempt USB interface claim with `0xe00002be` backoff and macOS 26+ `IOUSBHost` fallback."""
        errors: List[str] = []
        attempts: List[ClaimAttemptRecord] = []
        backoff_schedule: List[int] = []

        if self.state != TransportState.WAITING_MSC_QUIESCENCE or not self.msc_quiescent:
            errors.append(
                f"Cannot claim interface from state={self.state.value}, msc_quiescent={self.msc_quiescent}: "
                "must complete MSC quiescence wait first."
            )
            return ClaimResult(
                success=False,
                status="BLOCKED_QUIESCENCE_REQUIRED",
                active_backend="",
                exclusive_access_retries=0,
                backoff_schedule_ms=[],
                attempts=[],
                errors=errors,
            )

        if not attempt_return_codes:
            raise ValueError("attempt_return_codes must contain at least one outcome")

        exclusive_retries = 0
        for idx, rc in enumerate(attempt_return_codes):
            rc_u32 = rc & 0xFFFFFFFF
            # On macOS 26+, first attempt may probe IOUSBLib; upon 0xe00002be switch to native IOUSBHost
            backend = "IOUSBLib" if (idx == 0 and self.macos_major >= MACOS_CONTENTION_MIN_MAJOR and use_iousbhost_fallback) else "IOUSBHost"
            if not use_iousbhost_fallback:
                backend = "IOUSBLib"

            if rc_u32 == K_IORETURN_SUCCESS:
                attempts.append(
                    ClaimAttemptRecord(
                        attempt=idx + 1,
                        backend=backend,
                        return_code_hex=hex(rc_u32),
                        backoff_ms=0,
                        claimed=True,
                    )
                )
                self.active_backend = backend
                self._transition(TransportState.IOUSBHOST_CLAIMED)
                return ClaimResult(
                    success=True,
                    status="CLAIMED_VIA_" + backend.upper(),
                    active_backend=backend,
                    exclusive_access_retries=exclusive_retries,
                    backoff_schedule_ms=backoff_schedule,
                    attempts=attempts,
                    errors=[],
                )

            if rc_u32 == K_IORETURN_EXCLUSIVE_ACCESS:
                exclusive_retries += 1
                self._transition(TransportState.CLAIM_BACKOFF)
                delay = compute_exclusive_access_backoff_ms(
                    idx,
                    base_ms=base_backoff_ms,
                    cap_ms=cap_backoff_ms,
                )
                backoff_schedule.append(delay)
                self.total_backoff_ms += delay
                attempts.append(
                    ClaimAttemptRecord(
                        attempt=idx + 1,
                        backend=backend,
                        return_code_hex=hex(rc_u32),
                        backoff_ms=delay,
                        claimed=False,
                    )
                )
                continue

            # Unrecognized IOReturn error -> fail closed immediately
            err_msg = f"Unexpected IOReturn code {hex(rc_u32)} during {backend} claim."
            errors.append(err_msg)
            attempts.append(
                ClaimAttemptRecord(
                    attempt=idx + 1,
                    backend=backend,
                    return_code_hex=hex(rc_u32),
                    backoff_ms=0,
                    claimed=False,
                )
            )
            self._transition(TransportState.FAILED_CLOSED_EXCLUSIVE_ACCESS)
            return ClaimResult(
                success=False,
                status="BLOCKED_USB_CLAIM_ERROR",
                active_backend=backend,
                exclusive_access_retries=exclusive_retries,
                backoff_schedule_ms=backoff_schedule,
                attempts=attempts,
                errors=errors,
            )

        errors.append(
            f"Exhausted {len(attempt_return_codes)} claim retries under 0xe00002be (kIOReturnExclusiveAccess)."
        )
        self._transition(TransportState.FAILED_CLOSED_EXCLUSIVE_ACCESS)
        return ClaimResult(
            success=False,
            status="FAILED_CLOSED_EXCLUSIVE_ACCESS",
            active_backend="IOUSBHost" if use_iousbhost_fallback else "IOUSBLib",
            exclusive_access_retries=exclusive_retries,
            backoff_schedule_ms=backoff_schedule,
            attempts=attempts,
            errors=errors,
        )

    def send_vendor_control(
        self,
        *,
        bm_request_type: int = VENDOR_CONTROL_BM_REQUEST_TYPE,
        b_request: int = VENDOR_CONTROL_B_REQUEST,
        w_value: int = VENDOR_CONTROL_W_VALUE,
        w_index: int = VENDOR_CONTROL_W_INDEX,
        usb_stall: bool = False,
    ) -> VendorControlResult:
        """Send Sony Vendor Control packet; strictly suppress retransmission on USB STALL."""
        errors: List[str] = []
        if self.state != TransportState.IOUSBHOST_CLAIMED:
            errors.append(f"Cannot send Vendor Control from state={self.state.value}; claim interface first.")
            return VendorControlResult(
                success=False,
                status="BLOCKED_UNCLAIMED_INTERFACE",
                bm_request_type=bm_request_type,
                b_request=b_request,
                w_value=w_value,
                w_index=w_index,
                usb_stall_detected=usb_stall,
                retransmit_count=self.retransmit_count,
                errors=errors,
            )

        expected = (
            VENDOR_CONTROL_BM_REQUEST_TYPE,
            VENDOR_CONTROL_B_REQUEST,
            VENDOR_CONTROL_W_VALUE,
            VENDOR_CONTROL_W_INDEX,
        )
        actual = (bm_request_type, b_request, w_value, w_index)
        if actual != expected:
            errors.append(
                f"Invalid Sony Vendor Control tuple {tuple(hex(x) for x in actual)}, "
                f"expected {tuple(hex(x) for x in expected)}."
            )
            return VendorControlResult(
                success=False,
                status="BLOCKED_INVALID_VENDOR_CONTROL",
                bm_request_type=bm_request_type,
                b_request=b_request,
                w_value=w_value,
                w_index=w_index,
                usb_stall_detected=usb_stall,
                retransmit_count=self.retransmit_count,
                errors=errors,
            )

        if usb_stall:
            # pmca-re-reloaded v1.12.1 rule: NEVER retransmit control packets on USB STALL
            self._transition(TransportState.STALL_ABORTED_NO_RETRANSMIT)
            return VendorControlResult(
                success=False,
                status="STALL_ABORTED_NO_RETRANSMIT",
                bm_request_type=bm_request_type,
                b_request=b_request,
                w_value=w_value,
                w_index=w_index,
                usb_stall_detected=True,
                retransmit_count=0,
                errors=[
                    "USB STALL (0xe000404f) detected on control pipe; control packet retransmission suppressed."
                ],
            )

        self._transition(TransportState.VENDOR_CONTROL_SENT)
        return VendorControlResult(
            success=True,
            status="VENDOR_CONTROL_ACCEPTED",
            bm_request_type=bm_request_type,
            b_request=b_request,
            w_value=w_value,
            w_index=w_index,
            usb_stall_detected=False,
            retransmit_count=0,
            errors=[],
        )

    def authenticate_senser(self, challenge: SenserChallenge) -> SenserClassification:
        """Classify and authenticate Senser v1 vs Senser v2 (fail-closed) after Vendor Control."""
        if self.state != TransportState.VENDOR_CONTROL_SENT:
            return SenserClassification(
                supported=False,
                senser_version=challenge.senser_version,
                status="BLOCKED_INVALID_TRANSPORT_STATE",
                service_vid_pid="NONE_FAIL_CLOSED",
                rounds_required=0,
                fail_closed=True,
                reason=f"Cannot run Senser authentication from state={self.state.value}.",
            )

        classification = classify_senser_challenge(challenge)
        if not classification.supported:
            self._transition(TransportState.FAILED_CLOSED_SENSER_V2)
            return classification

        self.vid_pid = SONY_SERVICE_VID_PID
        self._transition(TransportState.SERVICE_MODE_ACTIVE)
        return classification

    def audit_jiritsu_flow(
        self,
        commands: Sequence[JiritsuCommand],
        *,
        allow_persistent_writes: bool = False,
    ) -> JiritsuSequenceAudit:
        """Audit Jiritsu commands, requiring active `054C:0336` Senser v1 service mode."""
        if self.state != TransportState.SERVICE_MODE_ACTIVE:
            return JiritsuSequenceAudit(
                allowed=False,
                status="BLOCKED_SERVICE_MODE_NOT_ACTIVE",
                allow_persistent_writes=ALLOW_PERSISTENT_JIRITSU_WRITES,
                decisions=[],
                blocked_codes=[],
                permitted_codes=[],
                errors=[
                    f"Jiritsu channel requires SERVICE_MODE_ACTIVE (054C:0336), current state={self.state.value}."
                ],
                warnings=[],
            )
        return audit_jiritsu_sequence(commands, allow_persistent_writes=allow_persistent_writes)
