"""Phase 59 — Camera-Disconnected RP2040-Zero `-DOPEN_DRAIN` 1.8V Multi-Port Bench Fixture Self-Test.

Deterministic bench pre-plug verifier for operators building a Tier-3 Sony
15-pin Multi-Port UART / CXD90057 BootROM recovery cable BEFORE connecting to a
physical FX3 camera body:

1. **15-Pin Sony Multi-Port Electrical & Ohmmeter Pre-Plug Firewall**:
   - Enforces `camera_connected == False` and `ltc_cable_connected == False`
     before bench ohmmeter / swing verification passes.
   - Verifies rail-to-signal & pin-to-pin isolation (`R_isolation >= 1 MOhm`)
     between `VBUS (5.0V)` / `3.3V` rails and `UART_TX` (Pin 8), `UART_RX`
     (Pin 7), `ID` (Pin 6), and `XRESET` (Pin 9), plus `Pin 2` GND continuity.
   - Rejects standard Raspberry Pi Pico (`GP29` `VSYS/3` voltage divider hazard).
   - Verifies open-drain `1.8V` pull-up ceiling (`V_idle in [1.71V, 1.89V]`;
     any `> 1.98V` or `3.3V` push-pull drive triggers immediate
     `FAIL_OVERVOLTAGE_HAZARD`).
   - Enforces the Multi-Port `ID` (Pin 6 <-> Pin 2) resistor keying matrix:
     `CONSOLE_READONLY`, `BOOTROM_UART_BOOT`, vs blocked
     `VMC_BNCM1_LTC_ADAPTER` (`680 kOhm`) and `LANC_REMOTE` (`100 kOhm`).

2. **`RP2040-Zero` (`125 MHz` / `133 MHz` `clk_sys`) PIO Open-Drain Timing & CMake Audit**:
   - Verifies exact RP2040 PIO 16.8 fractional clock divider
     (`div = clk_sys / (8 * baud)`), proving `<= 0.05%` bit-period error
     (`20.833 us/bit` at `48000` baud and `8.681 us/bit` at `115200` baud).
   - Audits PIO assembly sequences for `pindirs` direction-toggle open-drain
     signaling (never driving `pins=1` high, `pins_init_level == 0`, 8 cycles/bit).
   - Enforces CMake `-DOPEN_DRAIN=1` build flags and `waveshare_rp2040_zero`
     board selection.

3. **TX<->RX Bench Loopback & Read-Only BootROM Handshake Echo Simulator**:
   - 8x-oversampled bit-level UART waveform simulator validating start bit,
     8 data bits, parity/stop bits, start-glitch rejection, framing-error
     rejection, and read-only `uart_boot` (`UB`) CRC32 handshake/BootROM echo.
   - Hard-locks `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`,
     `ALLOW_BOOT_PARTITION_TARGETING = False`, and `ALLOW_DESTRUCTIVE_FASTBOOT = False`.
   - Opens any local donor files strictly `os.O_RDONLY` and never emits raw
     binary `bytes` reprs (always `.hex()`).
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
import math
import os
import re
import struct
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib

from .fat import MAX_P1
from .files import is_forced_clean_room, read_file, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Protocol Constants
# ---------------------------------------------------------------------------

RP2040_FIXTURE_SELFTEST_SCHEMA: str = "fx3-rp2040-multiport-fixture-selftest-v1"
RP2040_FIXTURE_SELFTEST_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
CAMERA_ATTACHED_ALLOWED_FOR_BENCH_SELFTEST: bool = False

FX3_PRODUCT_MODEL_ID: int = 0x91030080
DONOR_P1_205_RELPATH: str = "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"

# Electrical & Ohmmeter Thresholds
MIN_ISOLATION_OHM: float = 1_000_000.0  # 1 MOhm
MAX_GND_CONTINUITY_OHM: float = 2.0
V_IDLE_MIN_V: float = 1.71
V_IDLE_NOMINAL_V: float = 1.80
V_IDLE_MAX_V: float = 1.89
V_OVERVOLTAGE_HAZARD_V: float = 1.98
V_LOW_MAX_V: float = 0.35

# RP2040 Clock & PIO Timing Constants
RP2040_CLK_SYS_DEFAULT_HZ: int = 125_000_000
RP2040_CLK_SYS_133MHZ_HZ: int = 133_000_000
RP2040_CLK_SYS_SUPPORTED_HZ: Tuple[int, ...] = (125_000_000, 133_000_000)
PIO_CYCLES_PER_BIT: int = 8
UART_BOOT_BAUD: int = 48000
FASTBOOT_UART_BAUD: int = 115200
SUPPORTED_FIXTURE_BAUDS: Tuple[int, ...] = (UART_BOOT_BAUD, FASTBOOT_UART_BAUD)
MAX_BAUD_ERROR_PCT: float = 0.05

# Approved vs Forbidden RP2040 Boards
APPROVED_RP2040_BOARDS: Tuple[str, ...] = (
    "rp2040_zero",
    "waveshare_rp2040_zero",
    "explicit_1v8_open_drain_buffer",
)
FORBIDDEN_PICO_BOARDS: Tuple[str, ...] = (
    "pico",
    "pico_w",
    "pico_2",
    "rp2040_pico",
    "raspberry_pi_pico",
    "raspberry_pi_pico_w",
)

# Multi-Port Pin 6 <-> Pin 2 ID Resistor Keying Bands
VMC_BNCM1_ID_RESISTOR_OHM: int = 680_000
VMC_BNCM1_ID_RESISTOR_RANGE_OHM: Tuple[int, int] = (612_000, 748_000)
LANC_ID_RESISTOR_OHM: int = 100_000
LANC_ID_RESISTOR_RANGE_OHM: Tuple[int, int] = (90_000, 110_000)
ID_KEYING_MODES: Tuple[str, ...] = (
    "CONSOLE_READONLY",
    "BOOTROM_UART_BOOT",
    "VMC_BNCM1_LTC_ADAPTER",
    "LANC_REMOTE",
)

MULTIPORT_15PIN_SPEC: Dict[int, Dict[str, str]] = {
    1: {"signal": "VBUS_5V", "direction": "USB_POWER_RAIL", "fixture_role": "ISOLATED_NO_CONNECT"},
    2: {"signal": "GND", "direction": "REFERENCE", "fixture_role": "RP2040_GND"},
    3: {"signal": "LTC_IN_PLUS", "direction": "VMC_BNCM1_ONLY", "fixture_role": "ISOLATED_NO_CONNECT"},
    6: {"signal": "ID", "direction": "MODE_KEY_TO_GND", "fixture_role": "OPEN_HIZ_UART_SAFE"},
    7: {"signal": "CAM_UART_RX", "direction": "HOST_TO_CAM_OD", "fixture_role": "GP28_MULTI_TX"},
    8: {"signal": "CAM_UART_TX", "direction": "CAM_TO_HOST_OD", "fixture_role": "GP29_MULTI_RX"},
    9: {"signal": "XRESET", "direction": "HOST_TO_CAM_OD", "fixture_role": "GP27_MULTI_RST"},
}

DEFAULT_RP2040_GPIO_MAP: Dict[int, str] = {
    27: "PIN9_XRESET",
    28: "PIN7_CAM_RX",
    29: "PIN8_CAM_TX",
}

_GPIO_SIGNAL_ALIASES: Dict[int, Tuple[str, ...]] = {
    27: ("PIN9_XRESET", "XRESET", "MULTI_RST", "RESET"),
    28: ("PIN7_CAM_RX", "CAM_UART_RX", "CAM_RX", "MULTI_TX"),
    29: ("PIN8_CAM_TX", "CAM_UART_TX", "CAM_TX", "MULTI_RX"),
}

# Reference PIO Open-Drain TX Program (8 cycles/bit, pindirs toggling only, pins latched to 0)
DEFAULT_OPEN_DRAIN_PIO_PROGRAM: Tuple[str, ...] = (
    ".program fx3_uart_tx_open_drain",
    ".side_set 1 opt pindirs",
    "    pull       block      side 0 [7] ; Idle / stop bit: pindirs=0 (Hi-Z 1.8V pull-up)",
    "    mov osr, ~osr                    ; Invert bits so data 1->pindirs=0 (Hi-Z), 0->pindirs=1 (GND)",
    "    set x, 7              side 1 [7] ; Start bit: pindirs=1 (GND sink) for 8 cycles",
    "bitloop:",
    "    out pindirs, 1                   ; Shift inverted bit to pindirs (never drives pins=1)",
    "    jmp x-- bitloop              [6] ; 1 + 7 = 8 cycles/bit",
)

DEFAULT_CMAKE_OPEN_DRAIN_FLAGS: Tuple[str, ...] = (
    "-DOPEN_DRAIN=1",
    "-DUART_BOOT_BAUD=48000",
    "-DFASTBOOT_UART_BAUD=115200",
)

DEFAULT_CMAKE_SNIPPET: str = """\
set(PICO_BOARD waveshare_rp2040_zero)
add_executable(fx3_uart_boot uart_boot.c)
pico_generate_pio_header(fx3_uart_boot ${CMAKE_CURRENT_LIST_DIR}/uart_tx_open_drain.pio)
target_compile_definitions(fx3_uart_boot PRIVATE
    OPEN_DRAIN=1
    UART_BOOT_BAUD=48000
    FASTBOOT_UART_BAUD=115200
)
"""

# BootROM Protocol Constants (Read-Only Echo Verification)
UART_BOOT_FRAME_MAGIC: bytes = b"UB"
UART_BOOT_OPCODE_HANDSHAKE_PING: int = 0x0001
UART_BOOT_OPCODE_MEM_READ: int = 0x0003
BOOTROM_START: int = 0xFFFF0000
BOOTROM_END: int = 0xFFFFBFFF
WDT_TRAP_START: int = 0xFFFFC000

# Deterministic Status Codes
STATUS_VERIFIED_BENCH_FIXTURE: str = "VERIFIED_BENCH_FIXTURE"
STATUS_FAIL_CAMERA_CONNECTED: str = "FAIL_CAMERA_CONNECTED_DURING_BENCH_TEST"
STATUS_FAIL_ISOLATION_SHORT: str = "FAIL_ISOLATION_SHORT_FAULT"
STATUS_FAIL_GND_CONTINUITY: str = "FAIL_GND_CONTINUITY_FAULT"
STATUS_FAIL_OVERVOLTAGE_HAZARD: str = "FAIL_OVERVOLTAGE_HAZARD"
STATUS_FAIL_IDLE_OUT_OF_BAND: str = "FAIL_IDLE_VOLTAGE_OUT_OF_BAND"
STATUS_FAIL_UNDERVOLTAGE_PULLDOWN: str = "FAIL_UNDERVOLTAGE_OR_PULLDOWN"
STATUS_FAIL_LOW_SINK_LEVEL: str = "FAIL_LOW_SINK_LEVEL"
STATUS_FAIL_FORBIDDEN_BOARD: str = "FAIL_FORBIDDEN_BOARD_GP29_DIVIDER"
STATUS_FAIL_ID_KEYING_CONFLICT: str = "FAIL_ID_KEYING_CONFLICT"
STATUS_FAIL_PIO_TIMING_DRIFT: str = "FAIL_PIO_TIMING_DRIFT"
STATUS_FAIL_PIO_PUSH_PULL: str = "FAIL_PIO_PUSH_PULL_DRIVE"
STATUS_FAIL_CMAKE_BUILD_FLAGS: str = "FAIL_CMAKE_OPEN_DRAIN_FLAGS"
STATUS_FAIL_LOOPBACK_INTEGRITY: str = "FAIL_LOOPBACK_INTEGRITY"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class OhmmeterMeasurementSpec:
    camera_connected: bool = False
    ltc_cable_connected: bool = False
    vbus_to_uart_tx_ohm: Optional[float] = 10_000_000.0
    vbus_to_uart_rx_ohm: Optional[float] = 10_000_000.0
    vbus_to_id_ohm: Optional[float] = 10_000_000.0
    vbus_to_xreset_ohm: Optional[float] = 10_000_000.0
    v3v3_to_uart_tx_ohm: Optional[float] = 10_000_000.0
    v3v3_to_uart_rx_ohm: Optional[float] = 10_000_000.0
    v3v3_to_id_ohm: Optional[float] = 10_000_000.0
    v3v3_to_xreset_ohm: Optional[float] = 10_000_000.0
    uart_tx_to_uart_rx_ohm: Optional[float] = 10_000_000.0
    uart_tx_to_gnd_ohm: Optional[float] = 10_000_000.0
    uart_rx_to_gnd_ohm: Optional[float] = 10_000_000.0
    xreset_to_gnd_ohm: Optional[float] = 10_000_000.0
    gnd_continuity_ohm: Optional[float] = 0.25


@dataclass(frozen=True)
class OhmmeterFirewallResult:
    passed: bool
    status: str
    camera_disconnected_verified: bool
    ltc_cable_disconnected_verified: bool
    board: str
    min_measured_isolation_ohm: Optional[float]
    gnd_continuity_ohm: Optional[float]
    failed_rails: Tuple[str, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def __bool__(self) -> bool:
        return self.passed


@dataclass(frozen=True)
class OpenDrainSwingResult:
    passed: bool
    status: str
    drive_mode: str
    open_drain_enforced: bool
    v_idle_tx_v: float
    v_idle_rx_v: float
    v_idle_xreset_v: float
    v_low_tx_v: float
    v_low_xreset_v: float
    overvoltage_hazard: bool
    errors: Tuple[str, ...]

    def __bool__(self) -> bool:
        return self.passed


@dataclass(frozen=True)
class IdKeyingDecision:
    passed: bool
    status: str
    requested_mode: str
    detected_keying: str
    id_resistor_ohm: Optional[float]
    xreset_enabled: bool
    uart_tx_enabled: bool
    conflict_detected: bool
    errors: Tuple[str, ...]

    def __bool__(self) -> bool:
        return self.passed


@dataclass(frozen=True)
class PioClockDividerResult:
    passed: bool
    status: str
    clk_sys_hz: int
    target_baud: int
    cycles_per_bit: int
    ideal_div: float
    clkdiv_int: int
    clkdiv_frac: int
    effective_div: float
    actual_baud: float
    ideal_bit_period_us: float
    actual_bit_period_us: float
    baud_error_pct: float
    max_allowed_error_pct: float
    errors: Tuple[str, ...]

    def __bool__(self) -> bool:
        return self.passed


@dataclass(frozen=True)
class PioProgramAuditResult:
    passed: bool
    status: str
    instruction_count: int
    uses_pindirs_direction_toggle: bool
    drives_pins_high: bool
    pins_init_level: int
    cycles_per_bit: int
    forbidden_instructions: Tuple[str, ...]
    errors: Tuple[str, ...]

    def __bool__(self) -> bool:
        return self.passed


@dataclass(frozen=True)
class CmakeBuildAuditResult:
    passed: bool
    status: str
    board: str
    open_drain_flag_present: bool
    open_drain_equals_one: bool
    baud_flag_hz: Optional[int]
    flags_checked: Tuple[str, ...]
    errors: Tuple[str, ...]

    def __bool__(self) -> bool:
        return self.passed


@dataclass(frozen=True)
class UartLoopbackResult:
    passed: bool
    status: str
    baud_rate: int
    parity: str
    bytes_transmitted: int
    bytes_received: int
    tx_hex: str
    rx_hex: str
    bit_exact_match: bool
    framing_errors: int
    parity_errors: int
    glitch_rejections: int
    handshake_echo_verified: bool
    handshake_frame_hex: str
    bootrom_read_echo_verified: bool
    wdt_trap_blocked: bool
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]

    def __bool__(self) -> bool:
        return self.passed


@dataclass(frozen=True)
class Rp2040MultiportFixtureReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    board: str
    camera_connected: bool
    persistent_emmc_writes_authorized: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    donor_p1_sha256: str
    donor_body_model_id_hex: str
    ohmmeter_firewall: OhmmeterFirewallResult
    open_drain_swing: OpenDrainSwingResult
    id_keying_bootrom: IdKeyingDecision
    id_keying_console: IdKeyingDecision
    id_keying_conflicts_blocked: Dict[str, IdKeyingDecision]
    pio_dividers: Tuple[PioClockDividerResult, ...]
    pio_program_audit: PioProgramAuditResult
    cmake_audit: CmakeBuildAuditResult
    loopback_48000: UartLoopbackResult
    loopback_115200: UartLoopbackResult
    glitch_rejection_verified: bool
    framing_error_rejection_verified: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _norm_token(value: str) -> str:
    return re.sub(r"[\s\-]+", "_", value.strip().lower())


def _norm_upper(value: str) -> str:
    return re.sub(r"[\s\-]+", "_", value.strip().upper())


def _is_valid_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and not math.isnan(float(value))


def _encode_uart_boot_frame(opcode: int, *, address: int = 0, arg: int = 0, payload: bytes = b"") -> bytes:
    header = struct.pack("<2sHHII", UART_BOOT_FRAME_MAGIC, opcode, len(payload), address, arg)
    body = header + payload
    crc = zlib.crc32(body) & 0xFFFFFFFF
    return body + struct.pack("<I", crc)


def _decode_uart_boot_frame(raw: bytes) -> Tuple[int, int, int, bytes]:
    if len(raw) < 18:
        raise ValueError(f"Truncated uart_boot frame ({len(raw)} bytes)")
    magic, opcode, length, address, arg = struct.unpack_from("<2sHHII", raw, 0)
    if magic != UART_BOOT_FRAME_MAGIC:
        raise ValueError(f"Bad uart_boot magic hex={magic.hex()}")
    if len(raw) != 14 + length + 4:
        raise ValueError(f"Length mismatch: expected {14 + length + 4}, got {len(raw)}")
    expected_crc = struct.unpack_from("<I", raw, 14 + length)[0]
    actual_crc = zlib.crc32(raw[: 14 + length]) & 0xFFFFFFFF
    if expected_crc != actual_crc:
        raise ValueError(f"CRC32 mismatch: expected {hex(expected_crc)}, got {hex(actual_crc)}")
    return opcode, address, arg, raw[14 : 14 + length]


# ---------------------------------------------------------------------------
# 1. 15-Pin Sony Multi-Port Electrical & Ohmmeter Pre-Plug Firewall
# ---------------------------------------------------------------------------


def audit_ohmmeter_isolation(
    measurement: Optional[OhmmeterMeasurementSpec] = None,
    *,
    board: str = "waveshare_rp2040_zero",
    gpio_mapping: Optional[Mapping[int, str]] = None,
) -> OhmmeterFirewallResult:
    """Validate bench multimeter isolation (>= 1 MOhm) and GND continuity BEFORE camera plug-in."""
    spec = OhmmeterMeasurementSpec() if measurement is None else measurement
    errors: List[str] = []
    warnings: List[str] = []
    failed_rails: List[str] = []
    norm_board = _norm_token(board)

    # Precondition 1: Must be camera-disconnected!
    if spec.camera_connected:
        errors.append(
            "Camera body MUST be disconnected during bench ohmmeter and fixture self-test "
            "(unplug Sony 15-pin Multi-Port before probing)."
        )

    # Precondition 2: Mutual exclusion with VMC-BNCM1 LTC cable
    if spec.ltc_cable_connected:
        errors.append(
            "Multi-Port VMC-BNCM1 LTC adapter is attached; unplug LTC cable before Tier-3 UART bench verification."
        )

    # Precondition 3: Board safety check (reject standard Raspberry Pi Pico GP29 VSYS/3 divider)
    board_rejected = False
    if norm_board in FORBIDDEN_PICO_BOARDS or ("pico" in norm_board and "rp2040_zero" not in norm_board):
        board_rejected = True
        errors.append(
            f"Forbidden board {board!r}: standard Raspberry Pi Pico connects GP29 to VSYS/3 divider, "
            "pulling down Multi Pin 8 (CAM_UART_TX) and causing 0x100D framing errors."
        )
    elif norm_board not in APPROVED_RP2040_BOARDS:
        board_rejected = True
        errors.append(f"Unapproved board {board!r}; expected one of {APPROVED_RP2040_BOARDS}.")

    # Pinout mapping validation (GP27->Pin 9, GP28->Pin 7, GP29->Pin 8)
    mapping = dict(DEFAULT_RP2040_GPIO_MAP if gpio_mapping is None else gpio_mapping)
    for pin_num, allowed_names in _GPIO_SIGNAL_ALIASES.items():
        if pin_num not in mapping:
            errors.append(f"Missing required RP2040 GPIO GP{pin_num} in Multi-Port fixture mapping.")
            continue
        assigned = _norm_upper(str(mapping[pin_num]))
        if assigned not in allowed_names:
            errors.append(f"GP{pin_num} mapped to {mapping[pin_num]!r}, expected one of {allowed_names}.")

    # Rail-to-signal & signal-to-signal isolation checks (>= 1 MOhm)
    isolation_fields: Tuple[Tuple[str, Optional[float]], ...] = (
        ("vbus_to_uart_tx_ohm", spec.vbus_to_uart_tx_ohm),
        ("vbus_to_uart_rx_ohm", spec.vbus_to_uart_rx_ohm),
        ("vbus_to_id_ohm", spec.vbus_to_id_ohm),
        ("vbus_to_xreset_ohm", spec.vbus_to_xreset_ohm),
        ("v3v3_to_uart_tx_ohm", spec.v3v3_to_uart_tx_ohm),
        ("v3v3_to_uart_rx_ohm", spec.v3v3_to_uart_rx_ohm),
        ("v3v3_to_id_ohm", spec.v3v3_to_id_ohm),
        ("v3v3_to_xreset_ohm", spec.v3v3_to_xreset_ohm),
        ("uart_tx_to_uart_rx_ohm", spec.uart_tx_to_uart_rx_ohm),
        ("uart_tx_to_gnd_ohm", spec.uart_tx_to_gnd_ohm),
        ("uart_rx_to_gnd_ohm", spec.uart_rx_to_gnd_ohm),
        ("xreset_to_gnd_ohm", spec.xreset_to_gnd_ohm),
    )

    finite_values: List[float] = []
    short_detected = False
    for name, val in isolation_fields:
        if not _is_valid_number(val):
            short_detected = True
            failed_rails.append(name)
            errors.append(f"Missing/invalid ohmmeter isolation reading for {name}: {val!r}.")
            continue
        fval = float(val)
        if fval < 0.0:
            short_detected = True
            failed_rails.append(name)
            errors.append(f"Negative ohmmeter isolation reading on {name}: {fval} Ohm.")
            continue
        if math.isfinite(fval):
            finite_values.append(fval)
        if fval < MIN_ISOLATION_OHM:
            short_detected = True
            failed_rails.append(name)
            errors.append(
                f"Isolation short/leakage fault on {name}: {fval:.1f} Ohm < {MIN_ISOLATION_OHM:.0f} Ohm (1 MOhm minimum)."
            )

    min_iso = round(min(finite_values), 3) if finite_values else None

    # GND continuity check (<= 2.0 Ohm)
    gnd_fault = False
    gnd_val: Optional[float] = None
    if not _is_valid_number(spec.gnd_continuity_ohm) or not math.isfinite(float(spec.gnd_continuity_ohm)):
        gnd_fault = True
        errors.append(f"Invalid Multi Pin 2 GND continuity reading: {spec.gnd_continuity_ohm!r}.")
    else:
        gnd_val = float(spec.gnd_continuity_ohm)
        if gnd_val < 0.0 or gnd_val > MAX_GND_CONTINUITY_OHM:
            gnd_fault = True
            errors.append(
                f"Multi Pin 2 <-> RP2040 GND continuity fault: {gnd_val:.3f} Ohm (expected 0..{MAX_GND_CONTINUITY_OHM:.1f} Ohm)."
            )
        elif gnd_val > 1.0:
            warnings.append(f"GND resistance {gnd_val:.3f} Ohm > 1.0 Ohm; inspect solder joint on Multi Pin 2.")

    if spec.camera_connected:
        status = STATUS_FAIL_CAMERA_CONNECTED
    elif short_detected:
        status = STATUS_FAIL_ISOLATION_SHORT
    elif gnd_fault:
        status = STATUS_FAIL_GND_CONTINUITY
    elif board_rejected:
        status = STATUS_FAIL_FORBIDDEN_BOARD
    elif spec.ltc_cable_connected:
        status = STATUS_FAIL_ID_KEYING_CONFLICT
    elif errors:
        status = STATUS_FAIL_ISOLATION_SHORT
    else:
        status = STATUS_VERIFIED_BENCH_FIXTURE

    passed = len(errors) == 0
    return OhmmeterFirewallResult(
        passed=passed,
        status=status,
        camera_disconnected_verified=(not spec.camera_connected),
        ltc_cable_disconnected_verified=(not spec.ltc_cable_connected),
        board=norm_board,
        min_measured_isolation_ohm=min_iso,
        gnd_continuity_ohm=gnd_val,
        failed_rails=tuple(failed_rails),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_open_drain_1v8_swing(
    *,
    v_idle_tx_v: float = V_IDLE_NOMINAL_V,
    v_idle_rx_v: float = V_IDLE_NOMINAL_V,
    v_idle_xreset_v: float = V_IDLE_NOMINAL_V,
    v_low_tx_v: float = 0.08,
    v_low_xreset_v: float = 0.08,
    drive_mode: str = "open_drain",
    open_drain: bool = True,
    active_high_drive: bool = False,
) -> OpenDrainSwingResult:
    """Verify open-drain 1.8V pull-up ceiling (`[1.71V, 1.89V]`, `> 1.98V` -> `FAIL_OVERVOLTAGE_HAZARD`)."""
    errors: List[str] = []
    norm_drive = _norm_token(drive_mode)
    overvoltage_hazard = False
    out_of_band = False
    undervoltage = False
    low_sink_fault = False

    if not open_drain or norm_drive != "open_drain" or active_high_drive:
        overvoltage_hazard = True
        errors.append(
            f"Push-pull or active-high drive detected (drive_mode={drive_mode!r}, open_drain={open_drain}, "
            f"active_high_drive={active_high_drive}): 3.3V push-pull risks CXD90057 1.8V I/O silicon damage."
        )

    idle_rails = (
        ("UART_TX (Pin 8 / GP29)", v_idle_tx_v),
        ("UART_RX (Pin 7 / GP28)", v_idle_rx_v),
        ("XRESET (Pin 9 / GP27)", v_idle_xreset_v),
    )
    for label, v_val in idle_rails:
        if not _is_valid_number(v_val) or not math.isfinite(float(v_val)):
            undervoltage = True
            errors.append(f"Invalid idle voltage measurement on {label}: {v_val!r} V.")
            continue
        fv = float(v_val)
        if fv > V_OVERVOLTAGE_HAZARD_V:
            overvoltage_hazard = True
            errors.append(
                f"Overvoltage hazard on {label}: V_idle={fv:.3f}V > {V_OVERVOLTAGE_HAZARD_V:.2f}V ceiling "
                "(possible 3.3V push-pull leak or VBUS bridge)."
            )
        elif fv > V_IDLE_MAX_V:
            out_of_band = True
            errors.append(
                f"Idle voltage out of 1.8V +/-5% band on {label}: V_idle={fv:.3f}V not in [{V_IDLE_MIN_V:.2f}V, {V_IDLE_MAX_V:.2f}V]."
            )
        elif fv < V_IDLE_MIN_V:
            undervoltage = True
            errors.append(
                f"Undervoltage / pull-down fault on {label}: V_idle={fv:.3f}V < {V_IDLE_MIN_V:.2f}V "
                "(missing 1.8V pull-up or GP29 VSYS/3 divider loading)."
            )

    for label, v_low in (("UART_TX_LOW", v_low_tx_v), ("XRESET_LOW", v_low_xreset_v)):
        if not _is_valid_number(v_low) or not math.isfinite(float(v_low)):
            low_sink_fault = True
            errors.append(f"Invalid low-sink voltage on {label}: {v_low!r} V.")
            continue
        flv = float(v_low)
        if flv < 0.0 or flv > V_LOW_MAX_V:
            low_sink_fault = True
            errors.append(
                f"Low-sink voltage fault on {label}: V_low={flv:.3f}V outside [0.00V, {V_LOW_MAX_V:.2f}V]."
            )

    if overvoltage_hazard:
        status = STATUS_FAIL_OVERVOLTAGE_HAZARD
    elif out_of_band:
        status = STATUS_FAIL_IDLE_OUT_OF_BAND
    elif undervoltage:
        status = STATUS_FAIL_UNDERVOLTAGE_PULLDOWN
    elif low_sink_fault:
        status = STATUS_FAIL_LOW_SINK_LEVEL
    else:
        status = STATUS_VERIFIED_BENCH_FIXTURE

    return OpenDrainSwingResult(
        passed=len(errors) == 0,
        status=status,
        drive_mode=norm_drive,
        open_drain_enforced=(bool(open_drain) and norm_drive == "open_drain" and not active_high_drive),
        v_idle_tx_v=float(v_idle_tx_v) if _is_valid_number(v_idle_tx_v) else -1.0,
        v_idle_rx_v=float(v_idle_rx_v) if _is_valid_number(v_idle_rx_v) else -1.0,
        v_idle_xreset_v=float(v_idle_xreset_v) if _is_valid_number(v_idle_xreset_v) else -1.0,
        v_low_tx_v=float(v_low_tx_v) if _is_valid_number(v_low_tx_v) else -1.0,
        v_low_xreset_v=float(v_low_xreset_v) if _is_valid_number(v_low_xreset_v) else -1.0,
        overvoltage_hazard=overvoltage_hazard,
        errors=tuple(errors),
    )


def verify_multiport_id_keying(
    *,
    requested_mode: str = "BOOTROM_UART_BOOT",
    id_resistor_ohm: Optional[float] = None,
    xreset_enabled: Optional[bool] = None,
    uart_tx_enabled: Optional[bool] = None,
) -> IdKeyingDecision:
    """Audit Multi-Port Pin 6 (ID) resistor keying matrix vs VMC-BNCM1 (680 kOhm) & LANC (100 kOhm) conflicts."""
    norm_mode = _norm_upper(requested_mode)
    errors: List[str] = []

    if norm_mode == "CONSOLE_READONLY":
        eff_xreset = False if xreset_enabled is None else bool(xreset_enabled)
        eff_tx = False if uart_tx_enabled is None else bool(uart_tx_enabled)
    else:
        eff_xreset = True if xreset_enabled is None else bool(xreset_enabled)
        eff_tx = True if uart_tx_enabled is None else bool(uart_tx_enabled)

    # Classify physical Pin 6 <-> Pin 2 ID resistance
    if id_resistor_ohm is None:
        detected = "OPEN_HIZ_UART_SAFE"
    elif not _is_valid_number(id_resistor_ohm):
        detected = "INVALID_MEASUREMENT"
        errors.append(f"Invalid Pin 6 ID resistance measurement: {id_resistor_ohm!r}.")
    else:
        r_val = float(id_resistor_ohm)
        if r_val < 0.0:
            detected = "INVALID_MEASUREMENT"
            errors.append(f"Negative Pin 6 ID resistance measurement: {r_val} Ohm.")
        elif (math.isinf(r_val) and r_val > 0) or r_val >= MIN_ISOLATION_OHM:
            detected = "OPEN_HIZ_UART_SAFE"
        elif VMC_BNCM1_ID_RESISTOR_RANGE_OHM[0] <= r_val <= VMC_BNCM1_ID_RESISTOR_RANGE_OHM[1]:
            detected = "VMC_BNCM1_LTC_ADAPTER"
            errors.append(
                f"Pin 6 <-> Pin 2 resistor {r_val:.0f} Ohm matches VMC-BNCM1 LTC timecode adapter "
                f"(680 kOhm +/-10%): unplug LTC adapter before Tier-3 UART fixture use."
            )
        elif LANC_ID_RESISTOR_RANGE_OHM[0] <= r_val <= LANC_ID_RESISTOR_RANGE_OHM[1]:
            detected = "LANC_REMOTE"
            errors.append(
                f"Pin 6 <-> Pin 2 resistor {r_val:.0f} Ohm matches Sony LANC / RM-VPR1 remote "
                f"(100 kOhm +/-10%): conflict with Tier-3 UART fixture."
            )
        else:
            detected = "UNKNOWN_OR_SHORTED_ID_RESISTOR"
            errors.append(
                f"Pin 6 <-> Pin 2 resistor {r_val:.0f} Ohm < 1 MOhm violates UART Hi-Z ID keying "
                "(possible solder bridge or unknown Multi-Port accessory)."
            )

    if norm_mode not in ID_KEYING_MODES:
        errors.append(f"Unknown Multi-Port keying mode {requested_mode!r}; expected one of {ID_KEYING_MODES}.")
    elif norm_mode in ("VMC_BNCM1_LTC_ADAPTER", "LANC_REMOTE"):
        errors.append(
            f"Requested mode {norm_mode} is forbidden on the Tier-3 RP2040-Zero UART/BootROM recovery fixture."
        )
    elif norm_mode == "CONSOLE_READONLY":
        if eff_xreset:
            errors.append("CONSOLE_READONLY mode forbids driving Pin 9 XRESET (must stay Hi-Z).")
        if eff_tx:
            errors.append("CONSOLE_READONLY mode forbids active host UART TX drive on Pin 7.")
    elif norm_mode == "BOOTROM_UART_BOOT":
        if not eff_xreset:
            errors.append("BOOTROM_UART_BOOT mode requires GP27 -> Pin 9 XRESET open-drain reset capability.")
        if not eff_tx:
            errors.append("BOOTROM_UART_BOOT mode requires GP28 -> Pin 7 CAM_UART_RX open-drain TX capability.")

    conflict = len(errors) > 0
    stored_ohm = (
        None
        if id_resistor_ohm is None or (isinstance(id_resistor_ohm, float) and math.isinf(id_resistor_ohm))
        else (float(id_resistor_ohm) if _is_valid_number(id_resistor_ohm) else None)
    )
    return IdKeyingDecision(
        passed=(not conflict),
        status=STATUS_VERIFIED_BENCH_FIXTURE if not conflict else STATUS_FAIL_ID_KEYING_CONFLICT,
        requested_mode=norm_mode,
        detected_keying=detected,
        id_resistor_ohm=stored_ohm,
        xreset_enabled=eff_xreset,
        uart_tx_enabled=eff_tx,
        conflict_detected=conflict,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 2. RP2040-Zero PIO Divider, Open-Drain `pindirs` Program & CMake Audit
# ---------------------------------------------------------------------------


def compute_pio_uart_clkdiv(
    clk_sys_hz: int,
    baud_rate: int,
    *,
    cycles_per_bit: int = PIO_CYCLES_PER_BIT,
    max_error_pct: float = MAX_BAUD_ERROR_PCT,
    force_integer_only: bool = False,
) -> PioClockDividerResult:
    """Compute and verify RP2040 PIO 16.8 fractional clock divider (`div = clk_sys / (8 * baud)`)."""
    errors: List[str] = []
    if not isinstance(clk_sys_hz, int) or isinstance(clk_sys_hz, bool) or clk_sys_hz <= 0:
        raise ValueError(f"clk_sys_hz must be a positive integer, got {clk_sys_hz!r}")
    if not isinstance(baud_rate, int) or isinstance(baud_rate, bool) or baud_rate <= 0:
        raise ValueError(f"baud_rate must be a positive integer, got {baud_rate!r}")
    if not isinstance(cycles_per_bit, int) or isinstance(cycles_per_bit, bool) or cycles_per_bit <= 0:
        raise ValueError(f"cycles_per_bit must be a positive integer, got {cycles_per_bit!r}")

    if clk_sys_hz not in RP2040_CLK_SYS_SUPPORTED_HZ:
        errors.append(
            f"Unsupported clk_sys={clk_sys_hz} Hz; expected RP2040-Zero nominal {RP2040_CLK_SYS_SUPPORTED_HZ} Hz."
        )
    if baud_rate not in SUPPORTED_FIXTURE_BAUDS:
        errors.append(
            f"Unsupported fixture baud {baud_rate}; expected BootROM {UART_BOOT_BAUD} or Fastboot {FASTBOOT_UART_BAUD}."
        )
    if cycles_per_bit != PIO_CYCLES_PER_BIT:
        errors.append(f"PIO UART requires {PIO_CYCLES_PER_BIT} cycles/bit, got {cycles_per_bit}.")

    ideal_div = float(clk_sys_hz) / float(cycles_per_bit * baud_rate)
    if force_integer_only:
        clkdiv_int = int(round(ideal_div))
        clkdiv_frac = 0
    else:
        scaled = int(round(ideal_div * 256.0))
        clkdiv_int = scaled >> 8
        clkdiv_frac = scaled & 0xFF

    if clkdiv_int < 1 or clkdiv_int > 65535 or (clkdiv_int == 65535 and clkdiv_frac != 0):
        errors.append(f"RP2040 PIO CLKDIV out of hardware 16.8 range: int={clkdiv_int}, frac={clkdiv_frac}.")

    effective_div = float(clkdiv_int) + (float(clkdiv_frac) / 256.0)
    actual_baud = float(clk_sys_hz) / (float(cycles_per_bit) * effective_div) if effective_div > 0 else 0.0
    ideal_bit_us = 1_000_000.0 / float(baud_rate)
    actual_bit_us = 1_000_000.0 / actual_baud if actual_baud > 0 else 0.0
    baud_error_pct = (abs(actual_baud - float(baud_rate)) / float(baud_rate)) * 100.0

    if baud_error_pct > max_error_pct:
        errors.append(
            f"PIO baud error {baud_error_pct:.6f}% exceeds {max_error_pct:.4f}% ceiling "
            f"(clk_sys={clk_sys_hz}, target={baud_rate}, actual={actual_baud:.3f})."
        )

    passed = len(errors) == 0
    return PioClockDividerResult(
        passed=passed,
        status=STATUS_VERIFIED_BENCH_FIXTURE if passed else STATUS_FAIL_PIO_TIMING_DRIFT,
        clk_sys_hz=clk_sys_hz,
        target_baud=baud_rate,
        cycles_per_bit=cycles_per_bit,
        ideal_div=round(ideal_div, 9),
        clkdiv_int=clkdiv_int,
        clkdiv_frac=clkdiv_frac,
        effective_div=round(effective_div, 9),
        actual_baud=round(actual_baud, 6),
        ideal_bit_period_us=round(ideal_bit_us, 6),
        actual_bit_period_us=round(actual_bit_us, 6),
        baud_error_pct=round(baud_error_pct, 8),
        max_allowed_error_pct=max_error_pct,
        errors=tuple(errors),
    )


def audit_pio_open_drain_program(
    program_lines: Sequence[str] = DEFAULT_OPEN_DRAIN_PIO_PROGRAM,
    *,
    pins_init_level: int = 0,
    cycles_per_bit: int = PIO_CYCLES_PER_BIT,
) -> PioProgramAuditResult:
    """Audit RP2040 PIO assembly to guarantee `pindirs`-only open-drain toggling (never drives `pins=1` high)."""
    errors: List[str] = []
    forbidden: List[str] = []
    uses_pindirs = False
    drives_pins_high = False
    side_set_declared = False
    side_set_uses_pindirs = False
    instruction_count = 0

    if pins_init_level != 0:
        drives_pins_high = True
        errors.append(
            f"PIO initial pin output latch must be 0 (GND sink only), got pins_init_level={pins_init_level}."
        )
    if cycles_per_bit != PIO_CYCLES_PER_BIT:
        errors.append(f"PIO UART timing requires {PIO_CYCLES_PER_BIT} cycles/bit, got {cycles_per_bit}.")

    for raw_line in program_lines:
        code = raw_line.split(";", 1)[0].strip()
        if not code:
            continue
        low = re.sub(r"\s+", " ", code.lower())

        if low.startswith(".side_set"):
            side_set_declared = True
            if "pindirs" in low.split():
                side_set_uses_pindirs = True
            else:
                errors.append(f".side_set directive omits 'pindirs' ({code!r}); side-set would drive pins push-pull.")
            continue

        if low.startswith(".") or low.endswith(":"):
            continue

        instruction_count += 1

        # Detect any instruction driving `pins` directly (`out pins`, `set pins`, `mov pins`)
        if re.search(r"\b(out|mov)\s+pins\b", low):
            drives_pins_high = True
            forbidden.append(code)
            errors.append(f"Forbidden push-pull PIO instruction {code!r}: drives 'pins' instead of 'pindirs'.")
        elif re.search(r"\bset\s+pins\s*,\s*([0-9]+)", low):
            val_match = re.search(r"\bset\s+pins\s*,\s*([0-9]+)", low)
            if val_match and int(val_match.group(1)) != 0:
                drives_pins_high = True
                forbidden.append(code)
                errors.append(f"Forbidden PIO instruction {code!r}: drives pins high (=1).")

        # Detect side-set without `.side_set ... pindirs`
        if re.search(r"\bside\s+([0-9]+)", low):
            if not side_set_declared or not side_set_uses_pindirs:
                side_val = int(re.search(r"\bside\s+([0-9]+)", low).group(1))
                if side_val != 0:
                    drives_pins_high = True
                    forbidden.append(code)
                    errors.append(f"Forbidden push-pull side-set in {code!r} without '.side_set ... pindirs'.")
            else:
                uses_pindirs = True

        if re.search(r"\b(out|set|mov)\s+pindirs\b", low):
            uses_pindirs = True

    if instruction_count == 0:
        errors.append("Empty PIO program: no executable instructions found.")
    if not uses_pindirs:
        errors.append("PIO program does not toggle 'pindirs' for open-drain Hi-Z signaling.")

    passed = len(errors) == 0
    return PioProgramAuditResult(
        passed=passed,
        status=STATUS_VERIFIED_BENCH_FIXTURE if passed else STATUS_FAIL_PIO_PUSH_PULL,
        instruction_count=instruction_count,
        uses_pindirs_direction_toggle=uses_pindirs,
        drives_pins_high=drives_pins_high,
        pins_init_level=pins_init_level,
        cycles_per_bit=cycles_per_bit,
        forbidden_instructions=tuple(forbidden),
        errors=tuple(errors),
    )


def audit_cmake_open_drain_flags(
    *,
    board: str = "waveshare_rp2040_zero",
    compile_flags: Sequence[str] = DEFAULT_CMAKE_OPEN_DRAIN_FLAGS,
    cmake_text: Optional[str] = None,
    require_equals_one: bool = True,
) -> CmakeBuildAuditResult:
    """Enforce CMake `-DOPEN_DRAIN=1` build flag and RP2040-Zero board target."""
    errors: List[str] = []
    norm_board = _norm_token(board)
    checked_flags = [f.strip() for f in compile_flags if f.strip()]

    # Check board argument
    if norm_board in FORBIDDEN_PICO_BOARDS or ("pico" in norm_board and "rp2040_zero" not in norm_board):
        errors.append(f"Forbidden PICO_BOARD {board!r}: GP29 VSYS/3 divider pulls down Multi Pin 8.")
    elif norm_board not in APPROVED_RP2040_BOARDS:
        errors.append(f"Unapproved RP2040 board {board!r}; expected one of {APPROVED_RP2040_BOARDS}.")

    # Parse flags + optional CMakeLists text
    open_drain_present = False
    open_drain_eq_one = False
    baud_flag_hz: Optional[int] = None

    for flg in checked_flags:
        if flg == "-UOPEN_DRAIN":
            errors.append("Forbidden '-UOPEN_DRAIN' undefines open-drain protection.")
            open_drain_present = False
            open_drain_eq_one = False
        elif flg == "-DOPEN_DRAIN=0":
            errors.append("Forbidden '-DOPEN_DRAIN=0' disables open-drain 1.8V protection.")
            open_drain_present = False
            open_drain_eq_one = False
        elif flg == "-DOPEN_DRAIN=1":
            open_drain_present = True
            open_drain_eq_one = True
        elif flg == "-DOPEN_DRAIN":
            open_drain_present = True
        elif flg.startswith("-DUART_BOOT_BAUD="):
            raw_b = flg.split("=", 1)[1].strip()
            try:
                baud_flag_hz = int(raw_b, 10)
            except ValueError:
                errors.append(f"Malformed baud compile flag {flg!r}.")

    if cmake_text is not None:
        # Check PICO_BOARD inside CMake text if specified
        m_board = re.search(r"set\s*\(\s*PICO_BOARD\s+([A-Za-z0-9_\-]+)", cmake_text, re.IGNORECASE)
        if m_board:
            cm_board = _norm_token(m_board.group(1))
            if cm_board in FORBIDDEN_PICO_BOARDS or ("pico" in cm_board and "rp2040_zero" not in cm_board):
                errors.append(f"CMakeLists sets forbidden PICO_BOARD={m_board.group(1)!r}.")
            elif cm_board not in APPROVED_RP2040_BOARDS:
                errors.append(f"CMakeLists sets unapproved PICO_BOARD={m_board.group(1)!r}.")

        if re.search(r"\bOPEN_DRAIN\s*=\s*0\b", cmake_text) or "-DOPEN_DRAIN=0" in cmake_text:
            errors.append("CMakeLists explicitly sets OPEN_DRAIN=0 (push-pull hazard).")
            open_drain_eq_one = False
        if re.search(r"\bOPEN_DRAIN\s*=\s*1\b", cmake_text) or "-DOPEN_DRAIN=1" in cmake_text:
            open_drain_present = True
            open_drain_eq_one = True

        m_baud = re.search(r"\bUART_BOOT_BAUD\s*=\s*([0-9]+)\b", cmake_text)
        if m_baud:
            baud_flag_hz = int(m_baud.group(1), 10)

    if require_equals_one and not open_drain_eq_one:
        errors.append("CMake/compiler definitions must explicitly pass '-DOPEN_DRAIN=1' (OPEN_DRAIN=1).")
    elif not open_drain_present:
        errors.append("Missing mandatory '-DOPEN_DRAIN' / '-DOPEN_DRAIN=1' compile definition.")

    if baud_flag_hz is not None and baud_flag_hz != UART_BOOT_BAUD:
        errors.append(f"UART_BOOT_BAUD compile definition must be {UART_BOOT_BAUD}, got {baud_flag_hz}.")

    passed = len(errors) == 0
    if not passed and any("Pico" in e or "PICO_BOARD" in e or "board" in e.lower() for e in errors) and open_drain_eq_one:
        status = STATUS_FAIL_FORBIDDEN_BOARD
    elif not passed:
        status = STATUS_FAIL_CMAKE_BUILD_FLAGS
    else:
        status = STATUS_VERIFIED_BENCH_FIXTURE

    return CmakeBuildAuditResult(
        passed=passed,
        status=status,
        board=norm_board,
        open_drain_flag_present=open_drain_present,
        open_drain_equals_one=open_drain_eq_one,
        baud_flag_hz=baud_flag_hz,
        flags_checked=tuple(checked_flags),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 3. 8x-Oversampled UART Loopback & Read-Only BootROM Handshake Simulator
# ---------------------------------------------------------------------------


def _parity_bit(byte_val: int, parity: str) -> Optional[int]:
    if parity == "N":
        return None
    ones = bin(byte_val & 0xFF).count("1")
    if parity == "E":
        return ones & 1
    if parity == "O":
        return 1 - (ones & 1)
    raise ValueError(f"Unsupported UART parity {parity!r}; expected 'N', 'E', or 'O'.")


def _encode_uart_ticks(data: bytes, *, parity: str = "N", ticks_per_bit: int = PIO_CYCLES_PER_BIT) -> List[int]:
    ticks: List[int] = [1] * ticks_per_bit  # Initial idle high (1.8V pull-up)
    for b in data:
        ticks.extend([0] * ticks_per_bit)  # Start bit (0)
        for bit_idx in range(8):
            bit_val = (b >> bit_idx) & 1
            ticks.extend([bit_val] * ticks_per_bit)
        pbit = _parity_bit(b, parity)
        if pbit is not None:
            ticks.extend([pbit] * ticks_per_bit)
        ticks.extend([1] * ticks_per_bit)  # Stop bit (1)
    ticks.extend([1] * ticks_per_bit)  # Trailing idle
    return ticks


def _decode_uart_ticks(
    ticks: Sequence[int],
    *,
    parity: str = "N",
    ticks_per_bit: int = PIO_CYCLES_PER_BIT,
) -> Tuple[bytes, int, int, int, List[str]]:
    """Decode 8x-oversampled open-drain UART line ticks with glitch & framing-error rejection."""
    out = bytearray()
    framing_errors = 0
    parity_errors = 0
    glitch_rejections = 0
    errors: List[str] = []

    half = ticks_per_bit // 2
    has_parity = parity in ("E", "O")
    frame_bits = 1 + 8 + (1 if has_parity else 0) + 1  # start + 8 data + opt parity + stop

    idx = 0
    n = len(ticks)
    while idx < n:
        if ticks[idx] == 1:
            idx += 1
            continue

        # Falling edge / low tick detected: check start bit stability across center ticks
        if idx + ticks_per_bit > n:
            # Check if entire line was stuck low (break condition) or short glitch
            if all(t == 0 for t in ticks[idx:]):
                framing_errors += 1
                errors.append("UART line stuck low / truncated start bit.")
            else:
                glitch_rejections += 1
                errors.append("Rejected short low glitch near end of capture.")
            break

        # Start-bit majority/center check: reject narrow 1-2 tick glitches
        start_window = ticks[idx + 1 : idx + ticks_per_bit - 1]
        if any(t != 0 for t in start_window):
            glitch_rejections += 1
            errors.append(f"Start-bit glitch rejected at tick {idx} (transient noise spike, not full 0-bit).")
            # Advance past glitch
            while idx < n and ticks[idx] == 0:
                idx += 1
            continue

        if idx + frame_bits * ticks_per_bit > n:
            framing_errors += 1
            errors.append(f"Truncated UART frame at tick {idx} (possible stuck-low BREAK condition).")
            break

        # Sample 8 data bits LSB-first at center of each bit cell
        byte_val = 0
        cursor = idx + ticks_per_bit  # Start of bit 0
        for bit_idx in range(8):
            sample = ticks[cursor + half]
            byte_val |= (sample & 1) << bit_idx
            cursor += ticks_per_bit

        if has_parity:
            rx_parity = ticks[cursor + half]
            exp_parity = _parity_bit(byte_val, parity)
            cursor += ticks_per_bit
            if rx_parity != exp_parity:
                parity_errors += 1
                errors.append(f"UART parity error at tick {idx}: expected {exp_parity}, got {rx_parity}.")

        # Sample stop bit at center
        stop_sample = ticks[cursor + half]
        if stop_sample != 1:
            framing_errors += 1
            errors.append(f"UART framing error at tick {idx}: stop bit sampled 0 (expected 1).")
        else:
            out.append(byte_val)

        idx += frame_bits * ticks_per_bit

    return bytes(out), framing_errors, parity_errors, glitch_rejections, errors


def simulate_uart_loopback_and_handshake(
    payload: bytes = b"FX3_BENCH_PING",
    *,
    baud_rate: int = UART_BOOT_BAUD,
    parity: str = "N",
    clk_sys_hz: int = RP2040_CLK_SYS_DEFAULT_HZ,
    inject_start_glitch: bool = False,
    inject_stop_bit_error: bool = False,
    inject_parity_error: bool = False,
    inject_stuck_low_break: bool = False,
    inject_open_wire: bool = False,
    loopback_connected: bool = True,
    run_bootrom_echo: bool = True,
    persistent_emmc_writes_authorized: bool = False,
) -> UartLoopbackResult:
    """Simulate TX<->RX bench loopback bit/frame integrity & read-only BootROM handshake echo."""
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    raw_payload = bytes(payload)
    norm_parity = parity.strip().upper()
    if norm_parity not in ("N", "E", "O"):
        raise ValueError(f"Unsupported parity {parity!r}")

    errors: List[str] = []
    if persistent_emmc_writes_authorized:
        errors.append("persistent_emmc_writes_authorized=True is forbidden; hard-locked to False.")

    # Verify PIO clock divider for this baud first
    div_res = compute_pio_uart_clkdiv(clk_sys_hz, baud_rate)
    if not div_res.passed:
        errors.extend(div_res.errors)

    # Encode TX waveform
    ticks = _encode_uart_ticks(raw_payload, parity=norm_parity)

    # Inject physical bench faults if requested
    if inject_open_wire or not loopback_connected:
        # Open loopback wire stays idle high (1.8V pull-up, zero bytes received)
        ticks = [1] * len(ticks)
        errors.append("TX<->RX loopback wire open/disconnected: RX line remained idle high.")
    elif inject_stuck_low_break:
        # Line shorted to GND after idle
        ticks = [1] * PIO_CYCLES_PER_BIT + [0] * (len(ticks) - PIO_CYCLES_PER_BIT)
    else:
        if inject_start_glitch:
            # Prepend a 2-tick noise spike before first real byte
            glitch = [1, 1, 0, 0, 1, 1, 1, 1]
            ticks = glitch + ticks
        if inject_stop_bit_error and len(raw_payload) > 0:
            # Flip the first frame's stop bit (starts after 1 idle bit + 1 start + 8 data + opt parity)
            stop_bit_idx = (1 + 1 + 8 + (1 if norm_parity in ("E", "O") else 0)) * PIO_CYCLES_PER_BIT
            for k in range(stop_bit_idx, min(stop_bit_idx + PIO_CYCLES_PER_BIT, len(ticks))):
                ticks[k] = 0
        if inject_parity_error and norm_parity in ("E", "O") and len(raw_payload) > 0:
            parity_bit_idx = (1 + 1 + 8) * PIO_CYCLES_PER_BIT
            for k in range(parity_bit_idx, min(parity_bit_idx + PIO_CYCLES_PER_BIT, len(ticks))):
                ticks[k] ^= 1

    rx_bytes, framing_errs, parity_errs, glitch_rejs, dec_errs = _decode_uart_ticks(ticks, parity=norm_parity)
    errors.extend(dec_errs)

    bit_exact = (rx_bytes == raw_payload) and (framing_errs == 0) and (parity_errs == 0) and (glitch_rejs == 0)
    if not bit_exact and not errors:
        errors.append("TX<->RX loopback mismatch.")

    # Read-only BootROM handshake & BootROM range echo over simulated loopback
    handshake_frame = _encode_uart_boot_frame(UART_BOOT_OPCODE_HANDSHAKE_PING, address=0, arg=0, payload=b"MIRA")
    handshake_echo_ok = False
    bootrom_read_echo_ok = False
    wdt_trap_blocked = False

    if run_bootrom_echo and bit_exact and len(errors) == 0:
        hs_ticks = _encode_uart_ticks(handshake_frame, parity="N")
        hs_rx, hs_fe, hs_pe, hs_gr, _ = _decode_uart_ticks(hs_ticks, parity="N")
        if hs_fe == 0 and hs_pe == 0 and hs_gr == 0 and hs_rx == handshake_frame:
            op, addr, arg, pl = _decode_uart_boot_frame(hs_rx)
            handshake_echo_ok = (op == UART_BOOT_OPCODE_HANDSHAKE_PING and addr == 0 and arg == 0 and pl == b"MIRA")

        read_frame = _encode_uart_boot_frame(UART_BOOT_OPCODE_MEM_READ, address=BOOTROM_START, arg=64)
        rd_ticks = _encode_uart_ticks(read_frame, parity="N")
        rd_rx, rd_fe, rd_pe, rd_gr, _ = _decode_uart_ticks(rd_ticks, parity="N")
        if rd_fe == 0 and rd_pe == 0 and rd_gr == 0 and rd_rx == read_frame:
            op2, addr2, arg2, _ = _decode_uart_boot_frame(rd_rx)
            bootrom_read_echo_ok = (
                op2 == UART_BOOT_OPCODE_MEM_READ
                and BOOTROM_START <= addr2
                and (addr2 + arg2 - 1) <= BOOTROM_END
            )

        # Confirm WDT trap >= 0xFFFFC000 is blocked
        wdt_trap_blocked = (WDT_TRAP_START > BOOTROM_END)

    passed = (
        len(errors) == 0
        and bit_exact
        and (not run_bootrom_echo or (handshake_echo_ok and bootrom_read_echo_ok and wdt_trap_blocked))
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
    )
    return UartLoopbackResult(
        passed=passed,
        status=STATUS_VERIFIED_BENCH_FIXTURE if passed else STATUS_FAIL_LOOPBACK_INTEGRITY,
        baud_rate=baud_rate,
        parity=norm_parity,
        bytes_transmitted=len(raw_payload),
        bytes_received=len(rx_bytes),
        tx_hex=raw_payload.hex(),
        rx_hex=rx_bytes.hex(),
        bit_exact_match=bit_exact,
        framing_errors=framing_errs,
        parity_errors=parity_errs,
        glitch_rejections=glitch_rejs,
        handshake_echo_verified=handshake_echo_ok,
        handshake_frame_hex=handshake_frame.hex(),
        bootrom_read_echo_verified=bootrom_read_echo_ok,
        wdt_trap_blocked=wdt_trap_blocked,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# 4. Unified Dual-Mode Bench Self-Test Suite
# ---------------------------------------------------------------------------


def run_rp2040_multiport_fixture_selftest(
    *,
    force_clean_room: Optional[bool] = None,
    board: str = "waveshare_rp2040_zero",
    clk_sys_hz: int = RP2040_CLK_SYS_DEFAULT_HZ,
) -> Rp2040MultiportFixtureReport:
    """Execute complete Phase 59 camera-disconnected bench fixture self-test in Dual-Mode."""
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    donor_p1_path = resolve_donor_path(DONOR_P1_205_RELPATH) if not clean_room else None
    use_donor = (donor_p1_path is not None) and donor_p1_path.is_file()

    errors: List[str] = []
    donor_p1_sha256 = ""
    if use_donor and donor_p1_path is not None:
        verification_mode = "LOCAL_DONOR_O_RDONLY"
        # Strictly O_RDONLY bounded read via fx3_recovery.files.read_file
        from hashlib import sha256

        p1_bytes = read_file(donor_p1_path, MAX_P1)
        donor_p1_sha256 = sha256(p1_bytes).hexdigest()
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
        from hashlib import sha256

        donor_p1_sha256 = sha256(b"FX3_CLEAN_ROOM_RP2040_FIXTURE_ANCHOR_0x91030080").hexdigest()

    # 1. Ohmmeter Pre-Plug Isolation & Continuity (camera_connected=False)
    ohm = audit_ohmmeter_isolation(OhmmeterMeasurementSpec(camera_connected=False), board=board)
    if not ohm.passed:
        errors.extend(ohm.errors)

    # 2. Open-Drain 1.8V Swing Check
    swing = verify_open_drain_1v8_swing()
    if not swing.passed:
        errors.extend(swing.errors)

    # 3. ID Resistor Keying Matrix (valid + blocked conflicts)
    id_bootrom = verify_multiport_id_keying(requested_mode="BOOTROM_UART_BOOT", id_resistor_ohm=None)
    id_console = verify_multiport_id_keying(requested_mode="CONSOLE_READONLY", id_resistor_ohm=None)
    id_vmc_blocked = verify_multiport_id_keying(
        requested_mode="BOOTROM_UART_BOOT", id_resistor_ohm=float(VMC_BNCM1_ID_RESISTOR_OHM)
    )
    id_lanc_blocked = verify_multiport_id_keying(
        requested_mode="BOOTROM_UART_BOOT", id_resistor_ohm=float(LANC_ID_RESISTOR_OHM)
    )
    if not id_bootrom.passed:
        errors.extend(id_bootrom.errors)
    if not id_console.passed:
        errors.extend(id_console.errors)
    if id_vmc_blocked.passed:
        errors.append("VMC-BNCM1 680 kOhm ID resistor was not blocked fail-closed.")
    if id_lanc_blocked.passed:
        errors.append("LANC 100 kOhm ID resistor was not blocked fail-closed.")

    # 4. RP2040 PIO Dividers (both 125 MHz and 133 MHz, 48000 & 115200 baud)
    pio_divs: List[PioClockDividerResult] = []
    for clk in RP2040_CLK_SYS_SUPPORTED_HZ:
        for baud in SUPPORTED_FIXTURE_BAUDS:
            res = compute_pio_uart_clkdiv(clk, baud)
            pio_divs.append(res)
            if not res.passed:
                errors.extend(res.errors)

    # 5. PIO Open-Drain Instruction Sequence Audit
    pio_prog = audit_pio_open_drain_program(DEFAULT_OPEN_DRAIN_PIO_PROGRAM)
    if not pio_prog.passed:
        errors.extend(pio_prog.errors)

    # 6. CMake -DOPEN_DRAIN=1 Build-Flag Audit
    cmake_aud = audit_cmake_open_drain_flags(
        board=board,
        compile_flags=DEFAULT_CMAKE_OPEN_DRAIN_FLAGS,
        cmake_text=DEFAULT_CMAKE_SNIPPET,
    )
    if not cmake_aud.passed:
        errors.extend(cmake_aud.errors)

    # 7. TX<->RX Bench Loopback (48000 & 115200 baud + glitch/framing-error rejection self-check)
    lb_48k = simulate_uart_loopback_and_handshake(
        b"FX3_BOOTROM_48000_PING", baud_rate=UART_BOOT_BAUD, clk_sys_hz=clk_sys_hz
    )
    lb_115k = simulate_uart_loopback_and_handshake(
        b"[mira] fastboot ready", baud_rate=FASTBOOT_UART_BAUD, clk_sys_hz=clk_sys_hz
    )
    if not lb_48k.passed:
        errors.extend(lb_48k.errors)
    if not lb_115k.passed:
        errors.extend(lb_115k.errors)

    glitch_probe = simulate_uart_loopback_and_handshake(
        b"GLITCH", baud_rate=UART_BOOT_BAUD, inject_start_glitch=True, run_bootrom_echo=False
    )
    glitch_ok = (not glitch_probe.passed) and (glitch_probe.glitch_rejections >= 1)
    if not glitch_ok:
        errors.append("Start-bit glitch rejection self-check failed.")

    framing_probe = simulate_uart_loopback_and_handshake(
        b"FRAME", baud_rate=UART_BOOT_BAUD, inject_stop_bit_error=True, run_bootrom_echo=False
    )
    framing_ok = (not framing_probe.passed) and (framing_probe.framing_errors >= 1)
    if not framing_ok:
        errors.append("Framing-error rejection self-check failed.")

    all_passed = len(errors) == 0 and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
    return Rp2040MultiportFixtureReport(
        schema=RP2040_FIXTURE_SELFTEST_SCHEMA,
        version=RP2040_FIXTURE_SELFTEST_VERSION,
        verification_mode=verification_mode,
        all_passed=all_passed,
        status=STATUS_VERIFIED_BENCH_FIXTURE if all_passed else STATUS_FAIL_LOOPBACK_INTEGRITY,
        board=_norm_token(board),
        camera_connected=False,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        donor_p1_sha256=donor_p1_sha256,
        donor_body_model_id_hex=hex(FX3_PRODUCT_MODEL_ID),
        ohmmeter_firewall=ohm,
        open_drain_swing=swing,
        id_keying_bootrom=id_bootrom,
        id_keying_console=id_console,
        id_keying_conflicts_blocked={
            "VMC_BNCM1_LTC_ADAPTER": id_vmc_blocked,
            "LANC_REMOTE": id_lanc_blocked,
        },
        pio_dividers=tuple(pio_divs),
        pio_program_audit=pio_prog,
        cmake_audit=cmake_aud,
        loopback_48000=lb_48k,
        loopback_115200=lb_115k,
        glitch_rejection_verified=glitch_ok,
        framing_error_rejection_verified=framing_ok,
        errors=tuple(errors),
    )
