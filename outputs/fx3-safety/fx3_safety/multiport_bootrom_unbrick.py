"""FX3 15-Pin Multi-Terminal 48000-Baud BootROM Tier-3 Unbrick Verifier.

Provides clean-room hardware safety verification, BootROM address/watchdog guards,
48000-baud `uart_boot` frame codec, `0x100D` (13 short blinks) diagnostic decoding,
RP2040-Zero `-DOPEN_DRAIN` harness/firmware auditing, and read-only Fastboot v0.5
(`18D1:4EE0`) command firewalling.

Hardware Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED` and `ALLOW_DESTRUCTIVE_FASTBOOT` are
  hard-locked to `False`.
- Standard Raspberry Pi Pico (`GP29` `VSYS/3` voltage divider hazard) and any
  push-pull 3.3V GPIO configuration are deterministically rejected with
  `BLOCKED_ELECTRICAL_HAZARD`.
- Any BootROM/memory access reaching `>= 0xFFFFC000` is deterministically rejected
  with `BLOCKED_WDT_TRAP_HAZARD`.
"""

from __future__ import annotations

import re
import struct
import zlib
from dataclasses import dataclass, field
from enum import IntEnum
from typing import Dict, List, Optional, Sequence, Tuple


# Hard-locked read-only safety policy (cannot be overridden at runtime)
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False

# Hardware & BootROM memory map constants (CXD90057 "Mira" + CXD90058 "Cetus")
FX3_MODEL_ID: int = 0x91030080
SOC_AP_NAME: str = "CXD90057"
SOC_CP_NAME: str = "CXD90058"

UART_BOOT_BAUD: int = 48000
FASTBOOT_UART_BAUD: int = 115200
FASTBOOT_USB_VID_PID: str = "18D1:4EE0"

BOOTROM_START: int = 0xFFFF0000
BOOTROM_END: int = 0xFFFFBFFF
BOOTROM_SIZE_BYTES: int = 48 * 1024  # 48 KiB (0xC000)
BOOTROM_KEY_PAD_START: int = 0xFFFFB800
BOOTROM_KEY_PAD_END: int = 0xFFFFBC00

WDT_TRAP_START: int = 0xFFFFC000
WDT_TRAP_END: int = 0xFFFFFFFF

# Route A: Official signed Fastboot ("mira") SRAM load window
MIRA_SRAM_START: int = 0x92028000
MIRA_SRAM_END: int = 0x92427FFF  # 4 MiB SRAM window

# Route B: Open bare-metal eSRAM payload window (push_payload.py)
ESRAM_WINDOW_START: int = 0xFE000000
ESRAM_PAYLOAD_START: int = 0xFE020000
ESRAM_PAYLOAD_END: int = 0xFE047FFF  # Stops before loader_nor / DDR training
ESRAM_STACK_OVERFLOW_PTR: int = 0xFE02F398
DDR_TRAINING_ENTRY: int = 0xFE080000

SET_UNLOCK_MAGIC_DEAD: int = 0xDEADBEEF
SET_UNLOCK_MAGIC_REAL: int = 0x2CF25621

BAD_UART_BLINK_CODE: int = 0x100D
BAD_UART_SHORT_BLINKS: int = 13

UART_BOOT_FRAME_MAGIC: bytes = b"UB"
UART_BOOT_HEADER_SIZE: int = 14
UART_BOOT_TRAILER_SIZE: int = 4
UART_BOOT_MIN_FRAME_SIZE: int = UART_BOOT_HEADER_SIZE + UART_BOOT_TRAILER_SIZE
UART_BOOT_MAX_PAYLOAD: int = 4096

APPROVED_BOARDS: Tuple[str, ...] = (
    "rp2040_zero",
    "waveshare_rp2040_zero",
    "explicit_1v8_open_drain_buffer",
)
FORBIDDEN_BOARDS: Tuple[str, ...] = (
    "pico",
    "pico_w",
    "pico_2",
    "rp2040_pico",
    "raspberry_pi_pico",
    "raspberry_pi_pico_w",
)

MULTIPORT_PINOUT: Dict[int, Dict[str, str]] = {
    2: {"signal": "GND", "direction": "REFERENCE", "rp2040_zero_pin": "GND"},
    7: {"signal": "CAM_UART_RX", "direction": "HOST_TO_CAM", "rp2040_zero_pin": "GP28 (MULTI_TX)"},
    8: {"signal": "CAM_UART_TX", "direction": "CAM_TO_HOST", "rp2040_zero_pin": "GP29 (MULTI_RX)"},
    9: {"signal": "XRESET", "direction": "HOST_TO_CAM_OD", "rp2040_zero_pin": "GP27 (MULTI_RST)"},
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

# Fastboot v0.5 firewall rule sets
DESTRUCTIVE_FASTBOOT_PREFIXES: Tuple[str, ...] = (
    "flash:",
    "erase:",
    "oem format",
    "format:",
    "oem cetus poke",
    "oem cetus exec",
    "download:",
    "boot",
)

READONLY_FASTBOOT_PREFIXES: Tuple[str, ...] = (
    "getvar:",
    "oem dumpbrom",
    "oem partition dump",
    "oem partition",
    "oem cetus dumpnor",
    "oem cetus peek",
    "reboot",
)


class UartBootOpcode(IntEnum):
    SET_UNLOCK = 0x0000
    HANDSHAKE_PING = 0x0001
    MEM_WRITE = 0x0002
    MEM_READ = 0x0003
    JUMP_EXEC = 0x0004


@dataclass(frozen=True)
class HarnessValidationResult:
    valid: bool
    status: str  # "VERIFIED_SAFE" or "BLOCKED_ELECTRICAL_HAZARD"
    board: str
    open_drain_enforced: bool
    baud_rate: int
    io_voltage_v: float
    pin_mapping: Dict[int, str]
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class AddressValidationResult:
    valid: bool
    status: str
    address: int
    size: int
    end_address: int
    route: str
    errors: List[str] = field(default_factory=list)


@dataclass(frozen=True)
class UartBootFrame:
    opcode: UartBootOpcode
    address: int
    arg: int
    payload: bytes
    crc32: int


@dataclass(frozen=True)
class BootromDiagnosticResult:
    recognized: bool
    code_hex: str
    short_blinks: int
    long_blinks: int
    category: str
    severity: str
    summary: str
    likely_causes: List[str]
    remediation_steps: List[str]


@dataclass(frozen=True)
class FastbootCommandDecision:
    command: str
    allowed: bool
    status: str
    reason: str


@dataclass(frozen=True)
class FastbootFirewallAudit:
    allowed: bool
    status: str
    usb_vid_pid: str
    persistent_emmc_writes_authorized: bool
    allow_destructive_fastboot: bool
    decisions: List[FastbootCommandDecision]
    blocked_commands: List[str]
    permitted_commands: List[str]
    errors: List[str]
    warnings: List[str]


def _normalize_board_name(board: str) -> str:
    return re.sub(r"[\s\-]+", "_", board.strip().lower())


def validate_rp2040_multiport_harness(
    *,
    board: str = "rp2040_zero",
    compile_flags: Sequence[str] = ("-DOPEN_DRAIN",),
    open_drain: bool = True,
    gpio_drive_mode: str = "open_drain",
    io_voltage_v: float = 1.8,
    gpio_mapping: Optional[Dict[int, str]] = None,
    gnd_connected: bool = True,
    baud_rate: int = UART_BOOT_BAUD,
) -> HarnessValidationResult:
    """Validate FX3 15-pin Multi-Terminal RP2040 harness electrical & pinout safety."""
    errors: List[str] = []
    warnings: List[str] = []
    norm_board = _normalize_board_name(board)
    norm_drive = _normalize_board_name(gpio_drive_mode)
    mapping = dict(DEFAULT_RP2040_GPIO_MAP if gpio_mapping is None else gpio_mapping)
    flags_set = {f.strip() for f in compile_flags}

    # 1. Reject standard Pico (GP29 wired to VSYS/3 divider pulls down Cam UART TX)
    if norm_board in FORBIDDEN_BOARDS or ("pico" in norm_board and "rp2040_zero" not in norm_board):
        errors.append(
            f"Board {board!r} is forbidden: standard Raspberry Pi Pico connects GP29 to an internal "
            "VSYS/3 voltage divider, pulling down FX3 Multi Pin 8 (Cam UART TX) and corrupting 48000-baud BootROM handshake."
        )
    elif norm_board not in APPROVED_BOARDS:
        errors.append(
            f"Unsupported/unverified board {board!r}: only {APPROVED_BOARDS} are permitted for FX3 Multi-Terminal UART."
        )

    # 2. Enforce -DOPEN_DRAIN & reject push-pull 3.3V GPIO
    if "-DOPEN_DRAIN" not in flags_set:
        errors.append("Missing mandatory compile flag '-DOPEN_DRAIN' for open-drain High-Z signaling.")
    if not open_drain:
        errors.append("open_drain=False is forbidden: push-pull GPIO risks electrical damage on 1.8V/3.15V Multi-Terminal pins.")
    if norm_drive != "open_drain":
        errors.append(
            f"gpio_drive_mode={gpio_drive_mode!r} is forbidden: push-pull 3.3V drive can back-power or overstress CXD90057 I/O."
        )

    # 3. Voltage domain safety
    if not isinstance(io_voltage_v, (int, float)) or io_voltage_v <= 0.0:
        errors.append(f"Invalid I/O voltage {io_voltage_v!r}V.")
    elif norm_board == "explicit_1v8_open_drain_buffer" and io_voltage_v > 1.95:
        errors.append(f"explicit_1v8_open_drain_buffer requires <= 1.95V rail, got {io_voltage_v}V.")
    elif io_voltage_v > 3.15:
        errors.append(
            f"I/O voltage {io_voltage_v}V exceeds 3.15V Multi-Terminal ceiling (push-pull 3.3V hazard)."
        )
    elif io_voltage_v > 1.95:
        warnings.append(
            f"I/O pull-up voltage {io_voltage_v}V relies on strict -DOPEN_DRAIN High-Z release; verify no active 3.3V drive."
        )

    # 4. Ground & GP27/GP28/GP29 pin mapping check
    if not gnd_connected:
        errors.append("Multi Pin 2 GND reference is disconnected; floating ground breaks 48000-baud UART framing.")

    for pin_num, allowed_names in _GPIO_SIGNAL_ALIASES.items():
        if pin_num not in mapping:
            errors.append(f"Missing required GPIO pin GP{pin_num} in harness mapping.")
            continue
        assigned = re.sub(r"[\s\-]+", "_", str(mapping[pin_num]).strip().upper())
        if assigned not in allowed_names:
            errors.append(
                f"GP{pin_num} mapped to {mapping[pin_num]!r}, expected one of {allowed_names}."
            )

    # 5. Baud rate check
    if baud_rate != UART_BOOT_BAUD:
        errors.append(f"Initial BootROM handshake requires {UART_BOOT_BAUD} baud, got {baud_rate}.")

    open_drain_ok = ("-DOPEN_DRAIN" in flags_set) and bool(open_drain) and (norm_drive == "open_drain")
    valid = len(errors) == 0
    return HarnessValidationResult(
        valid=valid,
        status="VERIFIED_SAFE" if valid else "BLOCKED_ELECTRICAL_HAZARD",
        board=norm_board,
        open_drain_enforced=open_drain_ok,
        baud_rate=baud_rate,
        io_voltage_v=float(io_voltage_v),
        pin_mapping=mapping,
        errors=errors,
        warnings=warnings,
    )


def _overlaps(a_start: int, a_end: int, b_start: int, b_end: int) -> bool:
    return not (a_end < b_start or a_start > b_end)


def validate_mem_write_range(
    address: int,
    size: int,
    *,
    route: str = "auto",
) -> AddressValidationResult:
    """Validate CXD90057 BootROM `MEM_WRITE` target range against SRAM/eSRAM & WDT trap bounds."""
    errors: List[str] = []
    if not isinstance(address, int) or not isinstance(size, int) or address < 0 or size <= 0:
        return AddressValidationResult(
            valid=False,
            status="BLOCKED_INVALID_RANGE",
            address=address if isinstance(address, int) else -1,
            size=size if isinstance(size, int) else -1,
            end_address=-1,
            route=route,
            errors=["MEM_WRITE requires non-negative integer address and positive size."],
        )

    end_addr = address + size - 1
    if end_addr > 0xFFFFFFFF:
        return AddressValidationResult(
            valid=False,
            status="BLOCKED_INVALID_RANGE",
            address=address,
            size=size,
            end_address=end_addr,
            route=route,
            errors=[f"Address span [{hex(address)}..{hex(end_addr)}] overflows 32-bit address space."],
        )

    if _overlaps(address, end_addr, WDT_TRAP_START, WDT_TRAP_END):
        return AddressValidationResult(
            valid=False,
            status="BLOCKED_WDT_TRAP_HAZARD",
            address=address,
            size=size,
            end_address=end_addr,
            route=route,
            errors=[
                f"Target [{hex(address)}..{hex(end_addr)}] enters CXD90057 watchdog trap >= {hex(WDT_TRAP_START)}."
            ],
        )

    if _overlaps(address, end_addr, BOOTROM_START, BOOTROM_END):
        return AddressValidationResult(
            valid=False,
            status="BLOCKED_IMMUTABLE_BOOTROM",
            address=address,
            size=size,
            end_address=end_addr,
            route=route,
            errors=[
                f"Target [{hex(address)}..{hex(end_addr)}] overlaps immutable 48 KiB BootROM [{hex(BOOTROM_START)}..{hex(BOOTROM_END)}]."
            ],
        )

    if address % 4 != 0:
        return AddressValidationResult(
            valid=False,
            status="BLOCKED_ALIGNMENT_ERROR",
            address=address,
            size=size,
            end_address=end_addr,
            route=route,
            errors=[f"MEM_WRITE address {hex(address)} must be 4-byte aligned."],
        )

    in_mira = MIRA_SRAM_START <= address and end_addr <= MIRA_SRAM_END
    in_esram = ESRAM_PAYLOAD_START <= address and end_addr <= ESRAM_PAYLOAD_END

    norm_route = route.strip().lower()
    detected_route = "mira" if in_mira else ("esram" if in_esram else "out_of_bounds")

    if norm_route == "mira" and not in_mira:
        errors.append(
            f"Route 'mira' requires [{hex(MIRA_SRAM_START)}..{hex(MIRA_SRAM_END)}], got [{hex(address)}..{hex(end_addr)}]."
        )
    elif norm_route == "esram" and not in_esram:
        errors.append(
            f"Route 'esram' requires [{hex(ESRAM_PAYLOAD_START)}..{hex(ESRAM_PAYLOAD_END)}], got [{hex(address)}..{hex(end_addr)}]."
        )
    elif norm_route == "auto" and not (in_mira or in_esram):
        errors.append(
            f"MEM_WRITE [{hex(address)}..{hex(end_addr)}] is outside both Mira SRAM "
            f"[{hex(MIRA_SRAM_START)}..{hex(MIRA_SRAM_END)}] and eSRAM payload [{hex(ESRAM_PAYLOAD_START)}..{hex(ESRAM_PAYLOAD_END)}]."
        )
    elif norm_route not in ("auto", "mira", "esram"):
        errors.append(f"Unknown MEM_WRITE route {route!r}; expected 'auto', 'mira', or 'esram'.")

    valid = len(errors) == 0
    return AddressValidationResult(
        valid=valid,
        status="VERIFIED_RANGE" if valid else "BLOCKED_OUT_OF_BOUNDS_ADDRESS",
        address=address,
        size=size,
        end_address=end_addr,
        route=detected_route if valid else norm_route,
        errors=errors,
    )


def validate_bootrom_read_range(address: int, size: int) -> AddressValidationResult:
    """Validate read-only BootROM dump range (`0xFFFF0000..0xFFFFBFFF`), guarding `>= 0xFFFFC000`."""
    if not isinstance(address, int) or not isinstance(size, int) or address < 0 or size <= 0:
        return AddressValidationResult(
            valid=False,
            status="BLOCKED_INVALID_RANGE",
            address=address if isinstance(address, int) else -1,
            size=size if isinstance(size, int) else -1,
            end_address=-1,
            route="bootrom_read",
            errors=["BootROM read requires non-negative integer address and positive size."],
        )

    end_addr = address + size - 1
    if end_addr > 0xFFFFFFFF:
        return AddressValidationResult(
            valid=False,
            status="BLOCKED_INVALID_RANGE",
            address=address,
            size=size,
            end_address=end_addr,
            route="bootrom_read",
            errors=[f"Read span [{hex(address)}..{hex(end_addr)}] overflows 32-bit space."],
        )

    if _overlaps(address, end_addr, WDT_TRAP_START, WDT_TRAP_END):
        return AddressValidationResult(
            valid=False,
            status="BLOCKED_WDT_TRAP_HAZARD",
            address=address,
            size=size,
            end_address=end_addr,
            route="bootrom_read",
            errors=[
                f"BootROM read [{hex(address)}..{hex(end_addr)}] hits hardware watchdog trap >= {hex(WDT_TRAP_START)}!"
            ],
        )

    if address < BOOTROM_START or end_addr > BOOTROM_END:
        return AddressValidationResult(
            valid=False,
            status="BLOCKED_OUT_OF_BOUNDS_ADDRESS",
            address=address,
            size=size,
            end_address=end_addr,
            route="bootrom_read",
            errors=[
                f"BootROM read [{hex(address)}..{hex(end_addr)}] is outside [{hex(BOOTROM_START)}..{hex(BOOTROM_END)}]."
            ],
        )

    return AddressValidationResult(
        valid=True,
        status="VERIFIED_BOOTROM_READ",
        address=address,
        size=size,
        end_address=end_addr,
        route="bootrom_read",
        errors=[],
    )


def encode_uart_boot_frame(
    opcode: UartBootOpcode | int,
    *,
    address: int = 0,
    arg: int = 0,
    payload: bytes = b"",
    enforce_bounds: bool = True,
) -> bytes:
    """Encode a 48000-baud `uart_boot` protocol frame with CRC32 and safety range checks."""
    op = UartBootOpcode(opcode)
    if not isinstance(payload, (bytes, bytearray)):
        raise TypeError("payload must be bytes")
    raw_payload = bytes(payload)
    if len(raw_payload) > UART_BOOT_MAX_PAYLOAD:
        raise ValueError(f"Payload length {len(raw_payload)} exceeds max frame size {UART_BOOT_MAX_PAYLOAD}")
    if not (0 <= address <= 0xFFFFFFFF) or not (0 <= arg <= 0xFFFFFFFF):
        raise ValueError("address and arg must fit in unsigned 32-bit integers")

    if enforce_bounds:
        if op == UartBootOpcode.MEM_WRITE:
            res = validate_mem_write_range(address, len(raw_payload))
            if not res.valid:
                raise ValueError(f"{res.status}: {'; '.join(res.errors)}")
        elif op == UartBootOpcode.MEM_READ:
            read_len = arg if arg > 0 else len(raw_payload)
            res = validate_bootrom_read_range(address, read_len)
            if not res.valid:
                raise ValueError(f"{res.status}: {'; '.join(res.errors)}")
        elif op == UartBootOpcode.JUMP_EXEC:
            res = validate_mem_write_range(address, 4)
            if not res.valid:
                raise ValueError(f"{res.status}: {'; '.join(res.errors)}")
        elif op == UartBootOpcode.SET_UNLOCK:
            if arg not in (SET_UNLOCK_MAGIC_DEAD, SET_UNLOCK_MAGIC_REAL):
                raise ValueError(
                    f"SET_UNLOCK requires magic {hex(SET_UNLOCK_MAGIC_DEAD)} or {hex(SET_UNLOCK_MAGIC_REAL)}, got {hex(arg)}"
                )

    header = struct.pack(
        "<2sHHII",
        UART_BOOT_FRAME_MAGIC,
        int(op),
        len(raw_payload),
        address,
        arg,
    )
    body = header + raw_payload
    crc = zlib.crc32(body) & 0xFFFFFFFF
    return body + struct.pack("<I", crc)


def decode_uart_boot_frame(raw: bytes, *, enforce_bounds: bool = True) -> UartBootFrame:
    """Decode and verify a 48000-baud `uart_boot` frame, failing closed on corruption or unsafe address."""
    if len(raw) < UART_BOOT_MIN_FRAME_SIZE:
        raise ValueError(f"Frame truncated: got {len(raw)} bytes, minimum is {UART_BOOT_MIN_FRAME_SIZE}")

    magic, op_val, length, address, arg = struct.unpack_from("<2sHHII", raw, 0)
    if magic != UART_BOOT_FRAME_MAGIC:
        raise ValueError(f"Invalid uart_boot frame magic {magic!r}, expected {UART_BOOT_FRAME_MAGIC!r}")
    if length > UART_BOOT_MAX_PAYLOAD:
        raise ValueError(f"Frame payload length {length} exceeds maximum {UART_BOOT_MAX_PAYLOAD}")
    expected_total = UART_BOOT_HEADER_SIZE + length + UART_BOOT_TRAILER_SIZE
    if len(raw) != expected_total:
        raise ValueError(f"Frame length mismatch: header declares {expected_total} bytes, got {len(raw)}")

    try:
        op = UartBootOpcode(op_val)
    except ValueError as exc:
        raise ValueError(f"Unknown uart_boot opcode {hex(op_val)}") from exc

    expected_crc = struct.unpack_from("<I", raw, UART_BOOT_HEADER_SIZE + length)[0]
    computed_crc = zlib.crc32(raw[: UART_BOOT_HEADER_SIZE + length]) & 0xFFFFFFFF
    if computed_crc != expected_crc:
        raise ValueError(f"uart_boot frame CRC32 mismatch: expected {hex(expected_crc)}, computed {hex(computed_crc)}")

    payload = raw[UART_BOOT_HEADER_SIZE : UART_BOOT_HEADER_SIZE + length]

    if enforce_bounds:
        if op == UartBootOpcode.MEM_WRITE:
            res = validate_mem_write_range(address, len(payload))
            if not res.valid:
                raise ValueError(f"{res.status}: {'; '.join(res.errors)}")
        elif op == UartBootOpcode.MEM_READ:
            res = validate_bootrom_read_range(address, arg)
            if not res.valid:
                raise ValueError(f"{res.status}: {'; '.join(res.errors)}")
        elif op == UartBootOpcode.JUMP_EXEC:
            res = validate_mem_write_range(address, 4)
            if not res.valid:
                raise ValueError(f"{res.status}: {'; '.join(res.errors)}")

    return UartBootFrame(
        opcode=op,
        address=address,
        arg=arg,
        payload=payload,
        crc32=computed_crc,
    )


def estimate_uart_transfer_time_ms(byte_count: int, baud_rate: int = UART_BOOT_BAUD) -> float:
    """Compute 8N1 (10 bits/byte) UART transfer duration in milliseconds."""
    if byte_count < 0 or baud_rate <= 0:
        raise ValueError("byte_count must be >= 0 and baud_rate must be > 0")
    return round((byte_count * 10.0 * 1000.0) / float(baud_rate), 3)


def decode_bootrom_diagnostic_code(
    *,
    code: Optional[int | str] = None,
    short_blinks: Optional[int] = None,
    long_blinks: int = 0,
) -> BootromDiagnosticResult:
    """Decode CXD90057 BootROM diagnostic codes / blink patterns (notably 0x100D = 13 short blinks)."""
    parsed_code: Optional[int] = None
    if isinstance(code, int):
        parsed_code = code
    elif isinstance(code, str) and code.strip():
        try:
            parsed_code = int(code.strip(), 16 if not code.strip().startswith("0x") else 0)
        except ValueError:
            parsed_code = None

    if parsed_code == BAD_UART_BLINK_CODE or (short_blinks == BAD_UART_SHORT_BLINKS and long_blinks == 0):
        return BootromDiagnosticResult(
            recognized=True,
            code_hex="0x100D",
            short_blinks=13,
            long_blinks=0,
            category="BAD_UART_HANDSHAKE",
            severity="RECOVERABLE_HARDWARE_WIRING",
            summary=(
                "CXD90057 BootROM diagnostic 0x100D (13 short blinks): 48,000-baud Multi-Terminal "
                "UART framing/handshake failure."
            ),
            likely_causes=[
                "Standard Raspberry Pi Pico used instead of RP2040-Zero (GP29 VSYS/3 divider pulls down Cam UART TX).",
                "Missing -DOPEN_DRAIN compile flag or 3.3V push-pull GPIO contention on Multi Pin 7/8/9.",
                "Swapped Multi Pin 7 (Cam UART RX) and Pin 8 (Cam UART TX) or disconnected Pin 2 GND.",
                "Bit-banged UART clock drift away from 48,000 baud.",
            ],
            remediation_steps=[
                "Switch hardware bridge to Waveshare RP2040-Zero compiled with -DOPEN_DRAIN.",
                "Verify pinout: GP27->Pin 9 (XReset), GP28->Pin 7 (Cam RX), GP29->Pin 8 (Cam TX), GND->Pin 2.",
                "Power-cycle camera (battery pull 15s) and retry 48,000-baud handshake.",
            ],
        )

    if parsed_code == 0x0000 and (short_blinks is None or short_blinks == 0) and long_blinks == 0:
        return BootromDiagnosticResult(
            recognized=True,
            code_hex="0x0000",
            short_blinks=0,
            long_blinks=0,
            category="HANDSHAKE_OK",
            severity="INFO",
            summary="BootROM 48,000-baud handshake / SET_UNLOCK (0x0000) accepted.",
            likely_causes=["Valid RP2040-Zero open-drain framing and XReset timing."],
            remediation_steps=["Proceed with read-only payload injection (SRAM 0x92028000 or eSRAM 0xFE020000)."],
        )

    if (isinstance(code, str) and code.strip().lower() in ("wdt_reset", "wdt_trap")) or parsed_code == 0xDEAD:
        return BootromDiagnosticResult(
            recognized=True,
            code_hex="0xDEAD",
            short_blinks=0,
            long_blinks=0,
            category="WDT_TRAP_RESET",
            severity="HIGH",
            summary="Hardware watchdog reset triggered by reading >= 0xFFFFC000 inside CXD90057 BootROM.",
            likely_causes=["oem dumpbrom or MEM_READ crossed 0xFFFFBFFF into 0xFFFFC000..0xFFFFFFFF."],
            remediation_steps=["Clamp BootROM read end address strictly to <= 0xFFFFBFFF (48 KiB)."],
        )

    return BootromDiagnosticResult(
        recognized=False,
        code_hex=hex(parsed_code) if parsed_code is not None else "UNKNOWN",
        short_blinks=short_blinks or 0,
        long_blinks=long_blinks,
        category="UNKNOWN_BOOTROM_DIAGNOSTIC",
        severity="HIGH",
        summary="Unrecognized BootROM diagnostic code/blink pattern (fail-closed).",
        likely_causes=["Unhandled hardware fault or non-BootROM blink sequence."],
        remediation_steps=["Cross-check with brick_classifier.classify_brick_state() for 5L+6S / 7L+7S / 6L."],
    )


def _normalize_fastboot_cmd(cmd: str) -> str:
    return " ".join(cmd.strip().split())


def audit_fastboot_command_sequence(
    commands: Sequence[str],
    *,
    persistent_emmc_writes_authorized: bool = False,
    allow_destructive_fastboot: bool = False,
    usb_vid_pid: str = FASTBOOT_USB_VID_PID,
) -> FastbootFirewallAudit:
    """Firewall simulated Fastboot v0.5 (`18D1:4EE0`) commands against hard-locked read-only policy."""
    errors: List[str] = []
    warnings: List[str] = []
    decisions: List[FastbootCommandDecision] = []
    blocked: List[str] = []
    permitted: List[str] = []

    # Hard-lock enforcement: never allow persistent eMMC writes or destructive fastboot
    if persistent_emmc_writes_authorized or allow_destructive_fastboot:
        warnings.append(
            "Caller attempted to enable persistent_emmc_writes_authorized/allow_destructive_fastboot; "
            "hardware safety policy hard-locks both to False."
        )

    effective_emmc_auth = PERSISTENT_EMMC_WRITES_AUTHORIZED  # Always False
    effective_destructive = ALLOW_DESTRUCTIVE_FASTBOOT       # Always False

    norm_vid_pid = usb_vid_pid.strip().upper()
    if norm_vid_pid != FASTBOOT_USB_VID_PID:
        errors.append(
            f"Unexpected Fastboot USB VID:PID {usb_vid_pid!r}; expected {FASTBOOT_USB_VID_PID!r}."
        )

    for raw_cmd in commands:
        cmd = _normalize_fastboot_cmd(raw_cmd)
        cmd_lower = cmd.lower()

        if not cmd:
            decisions.append(
                FastbootCommandDecision(
                    command=raw_cmd,
                    allowed=False,
                    status="BLOCKED_EMPTY_COMMAND",
                    reason="Empty Fastboot command rejected.",
                )
            )
            blocked.append(raw_cmd)
            errors.append("Empty Fastboot command rejected.")
            continue

        destructive_hit = next(
            (p for p in DESTRUCTIVE_FASTBOOT_PREFIXES if cmd_lower.startswith(p)),
            None,
        )
        if destructive_hit is not None:
            reason = (
                f"Command {cmd!r} matches destructive prefix {destructive_hit!r}; "
                "blocked under hard-locked read-only BootROM probe/backup policy."
            )
            decisions.append(
                FastbootCommandDecision(
                    command=cmd,
                    allowed=False,
                    status="BLOCKED_DESTRUCTIVE_COMMAND",
                    reason=reason,
                )
            )
            blocked.append(cmd)
            errors.append(reason)
            continue

        readonly_hit = next(
            (p for p in READONLY_FASTBOOT_PREFIXES if cmd_lower.startswith(p)),
            None,
        )
        if readonly_hit is not None:
            # Guard `oem dumpbrom <addr> <len>` if range args are provided
            if cmd_lower.startswith("oem dumpbrom"):
                parts = cmd.split()
                if len(parts) >= 4:
                    try:
                        addr = int(parts[2], 0)
                        length = int(parts[3], 0)
                    except ValueError:
                        reason = f"Malformed oem dumpbrom range arguments in {cmd!r}."
                        decisions.append(
                            FastbootCommandDecision(
                                command=cmd,
                                allowed=False,
                                status="BLOCKED_INVALID_RANGE",
                                reason=reason,
                            )
                        )
                        blocked.append(cmd)
                        errors.append(reason)
                        continue
                    r_check = validate_bootrom_read_range(addr, length)
                    if not r_check.valid:
                        reason = f"{r_check.status}: {'; '.join(r_check.errors)}"
                        decisions.append(
                            FastbootCommandDecision(
                                command=cmd,
                                allowed=False,
                                status=r_check.status,
                                reason=reason,
                            )
                        )
                        blocked.append(cmd)
                        errors.append(reason)
                        continue

            decisions.append(
                FastbootCommandDecision(
                    command=cmd,
                    allowed=True,
                    status="PERMITTED_READONLY_COMMAND",
                    reason=f"Read-only probe/backup command permitted ({readonly_hit}).",
                )
            )
            permitted.append(cmd)
            continue

        reason = f"Unrecognized Fastboot command {cmd!r} rejected (fail-closed)."
        decisions.append(
            FastbootCommandDecision(
                command=cmd,
                allowed=False,
                status="BLOCKED_UNKNOWN_COMMAND",
                reason=reason,
            )
        )
        blocked.append(cmd)
        errors.append(reason)

    overall_allowed = len(errors) == 0 and len(blocked) == 0 and norm_vid_pid == FASTBOOT_USB_VID_PID
    if blocked:
        # Surface BLOCKED_DESTRUCTIVE_COMMAND if any command hit destructive rules
        if any(d.status == "BLOCKED_DESTRUCTIVE_COMMAND" for d in decisions):
            overall_status = "BLOCKED_DESTRUCTIVE_COMMAND"
        else:
            overall_status = "BLOCKED_COMMAND_SEQUENCE"
    elif errors:
        overall_status = "BLOCKED_USB_IDENTITY"
    else:
        overall_status = "PERMITTED_READONLY_SESSION"

    return FastbootFirewallAudit(
        allowed=overall_allowed,
        status=overall_status,
        usb_vid_pid=norm_vid_pid,
        persistent_emmc_writes_authorized=effective_emmc_auth,
        allow_destructive_fastboot=effective_destructive,
        decisions=decisions,
        blocked_commands=blocked,
        permitted_commands=permitted,
        errors=errors,
        warnings=warnings,
    )


def generate_rp2040_zero_open_drain_probe_spec(
    *,
    baud_rate: int = UART_BOOT_BAUD,
    handoff_baud_rate: int = FASTBOOT_UART_BAUD,
) -> Dict[str, object]:
    """Generate and self-audit the RP2040-Zero `-DOPEN_DRAIN` Multi-Port reference probe spec."""
    if baud_rate != UART_BOOT_BAUD:
        raise ValueError(f"Initial BootROM probe spec requires {UART_BOOT_BAUD} baud, got {baud_rate}")

    c_snippet = """/* FX3 Multi-Terminal 48000-baud BootROM Probe (RP2040-Zero ONLY)
 * Build with: -DOPEN_DRAIN -DUART_BOOT_BAUD=48000
 * NEVER build for standard Raspberry Pi Pico (GP29 VSYS/3 divider hazard)!
 */
#ifndef OPEN_DRAIN
#error "Refusing to compile push-pull GPIO driver for 1.8V/3.15V FX3 Multi port; pass -DOPEN_DRAIN"
#endif

#define PIN_MULTI_RST 27  /* -> Multi Back Row Pin 9 (XReset) */
#define PIN_MULTI_TX  28  /* -> Multi Back Row Pin 7 (Cam UART RX) */
#define PIN_MULTI_RX  29  /* <- Multi Back Row Pin 8 (Cam UART TX) */

static inline void od_write_bit(unsigned int gpio, bool level_high) {
    if (level_high) {
        gpio_set_dir(gpio, GPIO_IN);   /* High-Z: let camera pull-up hold 1.8V/3.15V */
    } else {
        gpio_put(gpio, 0);
        gpio_set_dir(gpio, GPIO_OUT);  /* Drive GND sink only */
    }
}
"""

    return {
        "schema": "fx3-rp2040-zero-open-drain-probe-v1",
        "board": "waveshare_rp2040_zero",
        "forbidden_boards": list(FORBIDDEN_BOARDS),
        "forbidden_board_reason": (
            "Standard Raspberry Pi Pico wires GP29 to internal VSYS/3 ADC divider, "
            "pulling down Multi Pin 8 (Cam UART TX) and triggering 0x100D (13 short blinks)."
        ),
        "compile_flags": ["-DOPEN_DRAIN", f"-DUART_BOOT_BAUD={baud_rate}", f"-DFASTBOOT_UART_BAUD={handoff_baud_rate}"],
        "open_drain": True,
        "gpio_drive_mode": "open_drain",
        "baud_rate": baud_rate,
        "handoff_baud_rate": handoff_baud_rate,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "allow_destructive_fastboot": ALLOW_DESTRUCTIVE_FASTBOOT,
        "pinout": [
            {"rp2040_gpio": "GP27", "macro": "PIN_MULTI_RST", "multi_pin": 9, "camera_signal": "XReset"},
            {"rp2040_gpio": "GP28", "macro": "PIN_MULTI_TX", "multi_pin": 7, "camera_signal": "Cam UART RX"},
            {"rp2040_gpio": "GP29", "macro": "PIN_MULTI_RX", "multi_pin": 8, "camera_signal": "Cam UART TX"},
            {"rp2040_gpio": "GND", "macro": "GND", "multi_pin": 2, "camera_signal": "GND"},
        ],
        "routes": {
            "route_a_mira_sram": {
                "load_address": hex(MIRA_SRAM_START),
                "payload": "signed fastboot.bin (mira)",
                "usb_enumeration": FASTBOOT_USB_VID_PID,
                "permitted_commands": ["getvar:version", "oem partition dump"],
            },
            "route_b_esram_open": {
                "load_address": hex(ESRAM_PAYLOAD_START),
                "unlock_opcode": hex(UartBootOpcode.SET_UNLOCK),
                "overflow_ptr": hex(ESRAM_STACK_OVERFLOW_PTR),
                "unlock_magics": [hex(SET_UNLOCK_MAGIC_DEAD), hex(SET_UNLOCK_MAGIC_REAL)],
                "usb_enumeration": FASTBOOT_USB_VID_PID,
                "permitted_commands": [
                    "getvar:version",
                    "oem dumpbrom",
                    "oem partition dump",
                    "oem cetus dumpnor",
                ],
            },
        },
        "firmware_c_snippet": c_snippet,
    }


def audit_rp2040_firmware_spec(spec: Dict[str, object]) -> HarnessValidationResult:
    """Audit a generated or external RP2040 probe spec dictionary through the electrical harness gate."""
    board = str(spec.get("board", ""))
    flags = [str(f) for f in spec.get("compile_flags", [])]  # type: ignore[union-attr]
    open_drain = bool(spec.get("open_drain", False))
    drive_mode = str(spec.get("gpio_drive_mode", ""))
    baud_rate = int(spec.get("baud_rate", 0))  # type: ignore[arg-type]
    snippet = str(spec.get("firmware_c_snippet", ""))

    res = validate_rp2040_multiport_harness(
        board=board,
        compile_flags=flags,
        open_drain=open_drain,
        gpio_drive_mode=drive_mode,
        baud_rate=baud_rate,
    )
    if res.valid and ("#ifndef OPEN_DRAIN" not in snippet or "GPIO_IN" not in snippet):
        return HarnessValidationResult(
            valid=False,
            status="BLOCKED_ELECTRICAL_HAZARD",
            board=res.board,
            open_drain_enforced=False,
            baud_rate=res.baud_rate,
            io_voltage_v=res.io_voltage_v,
            pin_mapping=res.pin_mapping,
            errors=res.errors + ["Firmware C snippet lacks '#ifndef OPEN_DRAIN' guard or High-Z 'GPIO_IN' release."],
            warnings=res.warnings,
        )
    return res
