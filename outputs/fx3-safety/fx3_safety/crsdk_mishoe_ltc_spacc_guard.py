"""Phase 38 Executable CrSDK PTP2, 24-Pin MI-Shoe, Multi-Port LTC & SPACC Guard.

Turns the four hardware and protocol findings from Phase 34
(`reports/2026-11-14-global-sony-ptp-mishoe-rtmd-spacc-intel/`) into fast,
deterministic, fail-closed executable safety verifiers for Sony ILME-FX3
(`CXD90057` AP + `CXD90058` CP, `ALCIN_UUD`) Stage-A/B RAM-overlay sessions:

1. **Multi-Port 15-Pin `VMC-BNCM1` LTC Timecode vs `RP2040-Zero` `uart_boot` Guard**:
   - Prevents simultaneous or miswired `2Vpp-5Vpp` SMPTE LTC BNC injection or
     wrong ID-resistor keying (`680 kOhm` LTC vs `100 kOhm` LANC) on 15-pin
     Multi-Port pins shared with `CXD90057` `1.8V/3.15V` BootROM UART
     (`Pin 7 RX / Pin 8 TX / Pin 9 XReset / Pin 2 GND`).
   - Verifies FX3 Multi-Port LTC Timecode IN fallback (`Movie` + `Preset` +
     `Free Run` + matching fps + `P11` `0x92d2091c` `/dev/rtc0` shim) when
     FX6 dedicated bidirectional BNC TC In/Out is absent.

2. **24-Pin MI-Shoe Digital Audio (`XLR-H1` / `ECM-B1M`) & `P11` `0x91db059b` Verifier**:
   - Audits the 24-contact MI-Shoe electrical matrix (`ID1..ID3` 6-bin ladder,
     `LOGIC_VDD` `2.8V-3.15V`, `UNREG` `6.1V-8.4V` fused `1.6A` ceiling),
     digital I2S `48kHz / 24-bit` 4-channel (`CH1..CH4`) framing,
     `libInfraHotshoe.so` (`0x5d90`) `E_TMO = -50 -> 0x8000` non-blocking
     timeout safety, and `P11` detached Smart Handle (`0x91db059b` ->
     `0x88000002`) coexistence (`xlr_h1_preserved = True`).

3. **Sony `CrSDK` PTP2 (`0x9201..0x9209` `SDIOConnect` / `SetDevicePropValueEx`) Firewall**:
   - Enforces Sony Vendor Extension `0x00000011` (blocking Nikon `0x920a..0x920f`
     opcode collisions), 3-step `SDIOConnect` (`0x9201`) `(1,0,0)->(2,0,0)->(3,0,0)`
     handshake ordering, `0xc8` (`SONY_PROTOCOL_2_00`) `libgphoto2#676` fallback,
     and classifies safe live shooting PTP2 property writes (`ExposureIndex`,
     `ShutterAngle`, `WhiteBalance`, `LogShootingMode`, `MovieRec`) vs
     dangerous firmware-update, NVRAM `PRODUCT_MODEL` (`ALCIN_UUD`), or raw
     service-mode escalation (`054C:0336` / `SET_FILE_PATH` / `AdjustControl`)
     requests during Stage-A/B RAM-overlay sessions.

4. **`CXD90057` `SPACC` (`0xf7fc0000`) `AES-XTS-256` (`/dev/cnflasha*` vs `/dev/nflasha*`) Guard**:
   - Enforces the cryptographic block-layer boundary: raw `/dev/nflasha*`
     carries ciphertext on `AES-XTS-256` partitions (`type=5, flag&1`), whereas
     `/dev/cnflasha*` decrypts transparently using LBA sector-number tweaks via
     `SPACC`. Mixing raw `nflasha` vs `cnflasha` reads/mounts, mounting an XTS
     partition via raw `nflasha`, accessing a plaintext partition via `cnflasha`,
     or touching `SPACC` MMIO (`0xf7fc0000..0xf7fcffff`) from userland is
     deterministically blocked with `BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH`.

Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False` (hard-locked)
- `PERSISTENT_WRITE_RELEASE = False` (hard-locked)
- Zero raw binary `bytes` repr output (always `.hex()`).
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass, field
import json
import os
import re
import shlex
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from .boot_contracts import FX3_KEY_PARTITIONS, verify_sector0_partition_table
from .multiport_bootrom_unbrick import MULTIPORT_PINOUT


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

CRSDK_MISHOE_LTC_SPACC_GUARD_SCHEMA: str = "fx3-crsdk-mishoe-ltc-spacc-guard-v1"
CRSDK_MISHOE_LTC_SPACC_GUARD_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"

# Domain 1 status codes
STATUS_BLOCKED_MULTIPORT_PIN_SHARING: str = "BLOCKED_MULTIPORT_PIN_SHARING_HAZARD"
STATUS_BLOCKED_LTC_OVERVOLTAGE: str = "BLOCKED_LTC_OVERVOLTAGE_HAZARD"
STATUS_BLOCKED_WRONG_ID_RESISTOR: str = "BLOCKED_WRONG_ID_RESISTOR_KEYING"
STATUS_BLOCKED_FX3_NO_BNC_TC_OUT: str = "BLOCKED_FX3_NO_BNC_TC_OUT"
STATUS_BLOCKED_LTC_SYNC_CONTRACT: str = "BLOCKED_LTC_SYNC_CONTRACT"

# Domain 2 status codes
STATUS_BLOCKED_MISHOE_ELECTRICAL: str = "BLOCKED_MISHOE_ELECTRICAL_HAZARD"
STATUS_BLOCKED_MISHOE_ID_LADDER: str = "BLOCKED_MISHOE_ID_LADDER_INVALID"
STATUS_BLOCKED_MISHOE_AUDIO_FRAMING: str = "BLOCKED_MISHOE_I2S_AUDIO_FRAMING"
STATUS_BLOCKED_SMART_HANDLE_COLLISION: str = "BLOCKED_SMART_HANDLE_XLR_H1_SUPPRESSED"
STATUS_BLOCKED_HOTSHOE_TIMEOUT_HANG: str = "BLOCKED_LIBINFRAHOTSHOE_TIMEOUT_HANG"

# Domain 3 status codes
STATUS_BLOCKED_PTP_VENDOR_COLLISION: str = "BLOCKED_PTP_VENDOR_COLLISION"
STATUS_BLOCKED_SDIO_HANDSHAKE_INCOMPLETE: str = "BLOCKED_SDIO_HANDSHAKE_INCOMPLETE"
STATUS_BLOCKED_CRSDK_PROTOCOL_REGRESSION: str = "BLOCKED_CRSDK_PROTOCOL_3_00_REGRESSION"
STATUS_BLOCKED_CRSDK_FIRMWARE_FLASH: str = "BLOCKED_CRSDK_FIRMWARE_OR_FLASH_OP"
STATUS_BLOCKED_CRSDK_NVRAM_TAMPER: str = "BLOCKED_CRSDK_NVRAM_IDENTITY_TAMPER"
STATUS_BLOCKED_CRSDK_SERVICE_ESCALATION: str = "BLOCKED_CRSDK_SERVICE_ESCALATION"
STATUS_BLOCKED_CRSDK_NO_MEDIA_CARD: str = "BLOCKED_CRSDK_NO_MEDIA_CARD"
STATUS_BLOCKED_CRSDK_UNKNOWN_OP: str = "BLOCKED_UNKNOWN_CRSDK_OPERATION"

# Domain 4 status codes
STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH: str = "BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH"
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = "BLOCKED_PERSISTENT_EMMC_WRITE_FORBIDDEN"


# ---------------------------------------------------------------------------
# Domain 1 Constants: 15-Pin Multi-Port VMC-BNCM1 LTC vs uart_boot
# ---------------------------------------------------------------------------

MULTIPORT_LTC_PIN_GND: int = 2
MULTIPORT_LTC_PIN_PLUS: int = 3
MULTIPORT_LTC_PIN_ID: int = 6
MULTIPORT_UART_BOOT_PINS: Tuple[int, ...] = (7, 8, 9)

VMC_BNCM1_ID_RESISTOR_OHM: int = 680_000
VMC_BNCM1_ID_RESISTOR_MIN_OHM: int = 612_000
VMC_BNCM1_ID_RESISTOR_MAX_OHM: int = 748_000
LANC_ID_RESISTOR_OHM: int = 100_000
LANC_ID_RESISTOR_RANGE_OHM: Tuple[int, int] = (90_000, 110_000)

CXD90057_IO_MAX_VOLTAGE_V: float = 3.15
SMPTE_LTC_SAFE_PIN3_VPP_MIN: float = 0.2
SMPTE_LTC_TYPICAL_VPP_MIN: float = 0.5
SMPTE_LTC_SAFE_PIN3_VPP_MAX: float = 5.0

SUPPORTED_LTC_FRAME_RATES: Tuple[float, ...] = (
    23.976,
    24.0,
    25.0,
    29.97,
    30.0,
    50.0,
    59.94,
    60.0,
)


# ---------------------------------------------------------------------------
# Domain 2 Constants: 24-Pin MI-Shoe & P11 Smart Handle Coexistence
# ---------------------------------------------------------------------------

MISHOE_TOTAL_CONTACTS: int = 24
MISHOE_FRONT_VIEW_ORDER: Tuple[int, ...] = (23, *range(1, 22), 24)
MISHOE_ID_LADDER_OHMS: Tuple[Optional[int], ...] = (0, 22_000, 56_000, 150_000, 470_000, None)
MISHOE_LOGIC_VDD_RANGE_V: Tuple[float, float] = (2.8, 3.15)
MISHOE_UNREG_RANGE_V: Tuple[float, float] = (6.1, 8.4)
MISHOE_UNREG_MAX_CURRENT_A: float = 1.6

MISHOE_VALID_AUDIO_PROFILES: Dict[Tuple[int, int, int], str] = {
    (48000, 16, 2): "PCM_48KHZ_16BIT_2CH",
    (48000, 24, 2): "PCM_48KHZ_24BIT_2CH",
    (48000, 24, 4): "PCM_48KHZ_24BIT_4CH",
}

LIBINFRAHOTSHOE_WAIT_RECV_VMA: int = 0x5D90
LIBINFRAHOTSHOE_E_TMO: int = -50
LIBINFRAHOTSHOE_TMO_SAFE_RC: int = 0x8000

EVENT_XLR_H1_DIGMIC_ON: str = "EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_ON"
VAL_CONNECT_SHOE_MIC_DIGITAL_XLR: str = "VAL_connect_shoe_mic_CONNECT_SHOE_MIC_DIGITAL_XLR"

SMART_HANDLE_QUEUE_ID: int = 0x91DB059B
SMART_HANDLE_REG_CMD: int = 0x81000001
SMART_HANDLE_UNREG_CMD: int = 0x81000002
SMART_HANDLE_EVT_ATTACHED_CMD: int = 0x88000001
SMART_HANDLE_EVT_DETACHED_CMD: int = 0x88000002


# ---------------------------------------------------------------------------
# Domain 3 Constants: Sony CrSDK PTP2 (0x9201..0x9209) Firewall
# ---------------------------------------------------------------------------

SONY_PTP_VENDOR_EXT_ID: int = 0x00000011
SONY_PROTOCOL_2_00: int = 0xC8
SONY_PROTOCOL_3_00: int = 0x12C

PTP_OC_SONY_SDIO_CONNECT: int = 0x9201
PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO: int = 0x9202
PTP_OC_SONY_GET_DEVICE_PROP_DESC: int = 0x9203
PTP_OC_SONY_GET_DEVICE_PROPERTY_VALUE: int = 0x9204
PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE: int = 0x9205
PTP_OC_SONY_GET_CONTROL_DEVICE_DESC: int = 0x9206
PTP_OC_SONY_SDIO_CONTROL_DEVICE: int = 0x9207
PTP_OC_SONY_SDIO_GET_ALL_EXT_DEVICE_PROP_INFO: int = 0x9209

PTP_SONY_NIKON_COLLISION_RANGE: Tuple[int, int] = (0x920A, 0x920F)
PTP_SONY_READONLY_OPCODES: Dict[int, str] = {
    0x9202: "PTP_OC_SONY_SDIO_GetExtDeviceInfo",
    0x9203: "PTP_OC_SONY_GetDevicePropdesc",
    0x9204: "PTP_OC_SONY_GetDevicePropertyValue",
    0x9206: "PTP_OC_SONY_GetControlDeviceDesc",
    0x9209: "PTP_OC_SONY_SDIO_GetAllExtDevicePropInfo",
    0x9210: "PTP_OC_SONY_OpenSession",
    0x9211: "PTP_OC_SONY_GetPartialLargeObject",
    0x9215: "PTP_OC_SONY_GetDisplayStringList",
    0x9223: "PTP_OC_SONY_GetLensInformation",
    0x922F: "PTP_OC_SONY_OperationsResultsSupported",
}

SAFE_CRSDK_LIVE_SHOOTING_PROPERTIES: Tuple[str, ...] = (
    "CRDEVICEPROPERTY_EXPOSUREINDEX",
    "CRDEVICEPROPERTY_ISOSENSITIVITY",
    "CRDEVICEPROPERTY_GAINBASEISOSENSITIVITY",
    "CRDEVICEPROPERTY_GAINBASESENSITIVITY",
    "CRDEVICEPROPERTY_LOGSHOOTINGMODE",
    "CRDEVICEPROPERTY_LOGSHOOTINGMODECOLORGAMUT",
    "CRDEVICEPROPERTY_SHUTTERMODE",
    "CRDEVICEPROPERTY_SHUTTERANGLE",
    "CRDEVICEPROPERTY_SHUTTERSPEED",
    "CRDEVICEPROPERTY_SHUTTERSETTING",
    "CRDEVICEPROPERTY_WHITEBALANCE",
    "CRDEVICEPROPERTY_COLORTEMP",
    "CRDEVICEPROPERTY_CUSTOMWB_CAPTURE_STANDBY",
    "CRDEVICEPROPERTY_BASELOOKVALUE",
    "CRDEVICEPROPERTY_MONITORLUTSETTING",
    "CRDEVICEPROPERTY_EMBEDLUTFILE",
    "CRDEVICEPROPERTY_FNUMBER",
    "CRDEVICEPROPERTY_FOCUSMODE",
    "CRDEVICEPROPERTY_MOVIEFRAMERATE",
    "CRDEVICEPROPERTY_RECORDINGSTATE",
    "EXPOSUREINDEX",
    "ISOSENSITIVITY",
    "SHUTTERANGLE",
    "SHUTTERMODE",
    "SHUTTERSPEED",
    "WHITEBALANCE",
    "COLORTEMP",
    "LOGSHOOTINGMODE",
)

SAFE_CRSDK_CONTROL_ACTIONS: Tuple[str, ...] = (
    "MOVIEREC",
    "MOVIE_REC",
    "RECSTART",
    "REC_START",
    "RECSTOP",
    "REC_STOP",
    "S1",
    "S2",
    "AF_ON",
    "C1",
    "C2",
    "C3",
    "C4",
    "C5",
    "C6",
    "DPAD_UP",
    "DPAD_DOWN",
    "DPAD_LEFT",
    "DPAD_RIGHT",
    "DPAD_ENTER",
    "MENU",
    "CANCEL",
)

DANGEROUS_CRSDK_NVRAM_IDENTITY_TOKENS: Tuple[str, ...] = (
    "PRODUCT_MODEL",
    "ALCIN_UUD",
    "BKID_PRODUCT_MODEL",
    "MODEL_ID",
    "CAMERA_MODEL",
    "SERIAL_NO",
    "BACKUP_BIN",
    "BK4",
    "LENSFILE",
    "PSD_BIN",
    "DEFDET",
    "DDRTRAINING",
    "NVRAM",
    "0X00010000",
    "0X02CF0001",
)

DANGEROUS_CRSDK_SERVICE_ESCALATION_TOKENS: Tuple[str, ...] = (
    "054C:0336",
    "SET_FILE_PATH",
    "0X400F",
    "SERVICE_MODE",
    "SENSER",
    "ADJUST_CONTROL",
    "0X0040",
    "0X1001",
    "VENDOR_CTRL_0X43",
    "0X37FF",
    "0XD7AA",
    "PMCA",
    "UART_BOOT",
    "FASTBOOT",
    "CETUS_PEEK",
    "CETUS_POKE",
    "CETUS_EXEC",
)

DANGEROUS_CRSDK_FIRMWARE_TOKENS: Tuple[str, ...] = (
    "FIRMWARE",
    "STARTFIRMWAREUPDATE",
    "UPLOADFIRMWARE",
    "UPDATEFILETRANSFER",
    "FLASH",
    "FORMAT",
    "FACTORY_RESET",
    "INITIALIZECAMERASETTING",
    "RESETTODEFAULT",
    "UPLOADSETTINGFILE",
    "CAMSET",
    "REBOOT_UPDATER",
    "DELETEALLCONTENTS",
)


# ---------------------------------------------------------------------------
# Domain 4 Constants: CXD90057 SPACC (0xf7fc0000) AES-XTS-256 Block Guard
# ---------------------------------------------------------------------------

SPACC_MMIO_BASE: int = 0xF7FC0000
SPACC_MMIO_END: int = 0xF7FCFFFF
SCU_MMIO_BASE: int = 0xF1388000
EMMC_SDM2_MMIO_RANGE: Tuple[int, int] = (0xF10D6000, 0xF10E0FFF)
SPI_0_4_MMIO_RANGE: Tuple[int, int] = (0xF1017000, 0xF101BFFF)

SDM2_MAGIC_ASCII: str = "8246"
SDM2_VERSION_ASCII: str = "2.00"

# Canonical FX3 7.02 partition table flags (`boot_contracts.FX3_KEY_PARTITIONS` +
# non-calibration entries) used when no external Sector 0 image is passed.
DEFAULT_FX3_PARTITION_CRYPTO_MAP: Dict[int, Tuple[int, int, int, int, str]] = {
    **FX3_KEY_PARTITIONS,
    4: (0x0003B800, 0x00006800, 4, 1, "p4:/av_misc"),
    9: (0x0012F800, 0x00006400, 4, 1, "p9:/setting_extra"),
    10: (0x00135C00, 0x00006000, 4, 1, "p10:/setting (12 MiB shared VFAT)"),
    11: (0x0013BC00, 0x000D0400, 5, 1, "p11:/data (AES-XTS-256)"),
    13: (0x00220000, 0x00005000, 5, 1, "p13:/log (AES-XTS-256)"),
    14: (0x00225000, 0x00005000, 5, 1, "p14:/cache (AES-XTS-256)"),
    16: (0x00324000, 0x00008000, 5, 1, "p16:/app_ext (AES-XTS-256)"),
    17: (0x0032C000, 0x00008000, 5, 1, "p17:/app_ext2 (AES-XTS-256)"),
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class MultiportLtcGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    fx3_fallback_active: bool
    bnc_tc_in_out_available: bool
    ext_lk_ready: bool
    pin_map_checked: Dict[int, str]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.valid


@dataclass(frozen=True)
class MiShoeCoexistenceResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    accessory_model: str
    xlr_h1_preserved: bool
    audio_format_label: str
    sample_rate_hz: int
    bit_depth: int
    channels: int
    pcm_bitrate_bps: int
    frame_bytes_per_sample_period: int
    libinfrahotshoe_timeout_safe: bool
    p11_smart_handle_ack_cmd: str
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.valid


@dataclass(frozen=True)
class CrSdkRequestDecision:
    opcode_hex: str
    opcode_name: str
    classification: str
    allowed: bool
    status: str
    property_or_action: str
    reason: str


@dataclass(frozen=True)
class CrSdkFirewallResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    vendor_extension_id_hex: str
    sdio_handshake_complete: bool
    negotiated_protocol_hex: str
    permitted_requests: Tuple[str, ...]
    blocked_requests: Tuple[str, ...]
    decisions: Tuple[CrSdkRequestDecision, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.valid


@dataclass(frozen=True)
class SpaccBlockOpDecision:
    target: str
    operation: str
    partition_index: Optional[int]
    is_aes_xts_partition: Optional[bool]
    expected_plaintext_node: Optional[str]
    allowed: bool
    status: str
    reason: str


@dataclass(frozen=True)
class SpaccBlockGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    decisions: Tuple[SpaccBlockOpDecision, ...]
    xts_partitions: Tuple[int, ...]
    plaintext_partitions: Tuple[int, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    details: Dict[str, Any] = field(default_factory=dict)

    def __bool__(self) -> bool:
        return self.valid


@dataclass(frozen=True)
class Phase38GuardReport:
    schema: str
    version: str
    clean_room_forced: bool
    all_passed: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    ltc_guard: MultiportLtcGuardResult
    mishoe_guard: MiShoeCoexistenceResult
    crsdk_firewall: CrSdkFirewallResult
    spacc_guard: SpaccBlockGuardResult
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _is_forced_clean_room() -> bool:
    return os.environ.get("FX3_FX6_FORCE_CLEAN_ROOM", "").strip() == "1"


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _norm_token(value: str) -> str:
    return re.sub(r"[\s\-]+", "_", value.strip().upper())


# ---------------------------------------------------------------------------
# Domain 1: Multi-Port 15-Pin VMC-BNCM1 LTC vs uart_boot Guard
# ---------------------------------------------------------------------------


def verify_multiport_ltc_vs_uart_boot(
    *,
    ltc_cable_attached: bool = True,
    uart_boot_harness_attached: bool = False,
    ltc_pin_mapping: Optional[Mapping[int, str]] = None,
    id_resistor_ohm: Optional[int] = VMC_BNCM1_ID_RESISTOR_OHM,
    ltc_vpp: float = 2.5,
    ac_coupled: bool = True,
    gnd_connected: bool = True,
    target_body: str = "ILME-FX3",
    bnc_tc_port_present: bool = False,
    ltc_direction: str = "IN",
    camera_mode: str = "MOVIE",
    tc_preset_mode: str = "PRESET",
    tc_run_mode: str = "FREE_RUN",
    ltc_fps: float = 23.976,
    shooting_fps: float = 23.976,
    p11_rtc_shim_active: bool = True,
) -> MultiportLtcGuardResult:
    """Verify FX3 15-pin Multi-Port `VMC-BNCM1` LTC vs `RP2040-Zero` `uart_boot` safety."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    pin_map: Dict[int, str] = (
        {
            MULTIPORT_LTC_PIN_GND: "GND_LTC",
            MULTIPORT_LTC_PIN_PLUS: "LTC_IN_PLUS",
            MULTIPORT_LTC_PIN_ID: "ID_680K_TO_PIN2",
        }
        if ltc_pin_mapping is None
        else {int(k): str(v) for k, v in ltc_pin_mapping.items()}
    )

    # 1. Mutual exclusion with RP2040-Zero BootROM uart_boot harness (Pins 7/8/9)
    if ltc_cable_attached and uart_boot_harness_attached:
        _add_code(codes, STATUS_BLOCKED_MULTIPORT_PIN_SHARING)
        errors.append(
            "Simultaneous attachment of VMC-BNCM1 LTC adapter and RP2040-Zero uart_boot "
            "harness on the shared 15-pin Multi-Port shell is forbidden (Pin 2 shared GND + "
            "1.8V/3.15V CXD90057 UART Pin 7/8/9 ESD/back-power hazard)."
        )

    for uart_pin in MULTIPORT_UART_BOOT_PINS:
        if uart_pin in pin_map:
            sig = pin_map[uart_pin]
            uart_expected = MULTIPORT_PINOUT[uart_pin]["signal"]
            _add_code(codes, STATUS_BLOCKED_MULTIPORT_PIN_SHARING)
            errors.append(
                f"LTC wiring touches CXD90057 BootROM UART Pin {uart_pin} ({uart_expected}) "
                f"with {sig!r} (max 3.15V I/O): 2Vpp-5Vpp SMPTE LTC injection on Pin 7/8/9 risks silicon damage."
            )

    if MULTIPORT_LTC_PIN_PLUS in pin_map:
        p3_sig = _norm_token(pin_map[MULTIPORT_LTC_PIN_PLUS])
        if any(tok in p3_sig for tok in ("UART", "XRESET", "TX", "RX")):
            _add_code(codes, STATUS_BLOCKED_MULTIPORT_PIN_SHARING)
            errors.append(
                f"Multi Pin 3 (+ve LTC) miswired to UART/reset signal {pin_map[MULTIPORT_LTC_PIN_PLUS]!r}."
            )

    if not gnd_connected:
        _add_code(codes, STATUS_BLOCKED_MULTIPORT_PIN_SHARING)
        errors.append("Multi Pin 2 (GND / -ve LTC) is disconnected; floating ground breaks LTC and UART safety.")

    # 2. SMPTE LTC Vpp & AC-coupling overvoltage checks
    if ltc_cable_attached:
        if not isinstance(ltc_vpp, (int, float)) or ltc_vpp <= 0.0:
            _add_code(codes, STATUS_BLOCKED_LTC_OVERVOLTAGE)
            errors.append(f"Invalid SMPTE LTC peak-to-peak amplitude {ltc_vpp!r} Vpp.")
        else:
            if ltc_vpp > SMPTE_LTC_SAFE_PIN3_VPP_MAX:
                _add_code(codes, STATUS_BLOCKED_LTC_OVERVOLTAGE)
                errors.append(
                    f"SMPTE LTC amplitude {ltc_vpp:.2f} Vpp exceeds VMC-BNCM1 Pin 3 ceiling "
                    f"({SMPTE_LTC_SAFE_PIN3_VPP_MAX:.2f} Vpp)."
                )
            if not ac_coupled and ltc_vpp > CXD90057_IO_MAX_VOLTAGE_V:
                _add_code(codes, STATUS_BLOCKED_LTC_OVERVOLTAGE)
                errors.append(
                    f"DC-coupled {ltc_vpp:.2f} Vpp LTC exceeds CXD90057 {CXD90057_IO_MAX_VOLTAGE_V:.2f}V "
                    "rail ceiling; AC coupling / VMC-BNCM1 input network required."
                )
            if ltc_vpp < SMPTE_LTC_SAFE_PIN3_VPP_MIN:
                warnings.append(
                    f"LTC amplitude {ltc_vpp:.2f} Vpp is below 0.20 Vpp threshold; EXT-LK may fail to lock."
                )

    # 3. Pin 6 <-> Pin 2 ID resistor keying (680 kOhm LTC vs 100 kOhm LANC)
    if ltc_cable_attached:
        if id_resistor_ohm is None:
            _add_code(codes, STATUS_BLOCKED_WRONG_ID_RESISTOR)
            errors.append(
                "Missing Pin 6 <-> Pin 2 detection resistor (expected 680 kOhm for VMC-BNCM1 LTC)."
            )
        elif LANC_ID_RESISTOR_RANGE_OHM[0] <= id_resistor_ohm <= LANC_ID_RESISTOR_RANGE_OHM[1]:
            _add_code(codes, STATUS_BLOCKED_WRONG_ID_RESISTOR)
            errors.append(
                f"Pin 6 <-> Pin 2 resistor {id_resistor_ohm} Ohm selects LANC REMOTE mode (100 kOhm), "
                "NOT VMC-BNCM1 LTC mode (680 kOhm)."
            )
        elif not (VMC_BNCM1_ID_RESISTOR_MIN_OHM <= id_resistor_ohm <= VMC_BNCM1_ID_RESISTOR_MAX_OHM):
            _add_code(codes, STATUS_BLOCKED_WRONG_ID_RESISTOR)
            errors.append(
                f"Pin 6 <-> Pin 2 resistor {id_resistor_ohm} Ohm is outside 680 kOhm +/-10% "
                f"[{VMC_BNCM1_ID_RESISTOR_MIN_OHM}..{VMC_BNCM1_ID_RESISTOR_MAX_OHM}] VMC-BNCM1 LTC window."
            )

    # 4. FX3 Multi-Port LTC In fallback when FX6 dedicated BNC TC In/Out is absent
    norm_body = _norm_token(target_body)
    fx3_fallback_active = ltc_cable_attached and (not bnc_tc_port_present)
    norm_dir = _norm_token(ltc_direction)
    norm_cam_mode = _norm_token(camera_mode)
    norm_preset = _norm_token(tc_preset_mode)
    norm_run = _norm_token(tc_run_mode)

    if fx3_fallback_active:
        if norm_dir != "IN":
            _add_code(codes, STATUS_BLOCKED_FX3_NO_BNC_TC_OUT)
            errors.append(
                f"FX3 Multi-Port VMC-BNCM1 only supports unidirectional LTC IN (got direction={ltc_direction!r}); "
                "FX3 lacks FX6's dedicated bidirectional BNC TC IN/OUT port."
            )
        if norm_cam_mode != "MOVIE":
            _add_code(codes, STATUS_BLOCKED_LTC_SYNC_CONTRACT)
            errors.append(f"FX3 Multi-Port EXT-LK requires Movie mode, got {camera_mode!r}.")
        if norm_preset != "PRESET" or norm_run != "FREE_RUN":
            _add_code(codes, STATUS_BLOCKED_LTC_SYNC_CONTRACT)
            errors.append(
                f"FX3 Multi-Port EXT-LK requires TC/UB Preset + Free Run, got {tc_preset_mode!r}/{tc_run_mode!r}."
            )
        if abs(float(ltc_fps) - float(shooting_fps)) > 0.01:
            _add_code(codes, STATUS_BLOCKED_LTC_SYNC_CONTRACT)
            errors.append(
                f"LTC generator fps ({ltc_fps}) does not match shooting fps ({shooting_fps}); "
                "EXT-LK lock requires exact frame rate match."
            )
        if not p11_rtc_shim_active:
            _add_code(codes, STATUS_BLOCKED_LTC_SYNC_CONTRACT)
            errors.append(
                "Stage-B FX6-on-FX3 Multi-Port LTC fallback requires active P11 0x92d2091c (/dev/rtc0) "
                "shim so AP clock queue does not block."
            )

    valid = len(errors) == 0
    ext_lk_ready = valid and ltc_cable_attached
    status = STATUS_VERIFIED_SAFE if valid else codes[0]
    return MultiportLtcGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        fx3_fallback_active=fx3_fallback_active,
        bnc_tc_in_out_available=bool(bnc_tc_port_present),
        ext_lk_ready=ext_lk_ready,
        pin_map_checked=pin_map,
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "target_body": norm_body,
            "id_resistor_ohm": id_resistor_ohm,
            "ltc_vpp": ltc_vpp,
            "ac_coupled": ac_coupled,
            "uart_boot_protected_pins": list(MULTIPORT_UART_BOOT_PINS),
            "expected_ltc_id_resistor_ohm": VMC_BNCM1_ID_RESISTOR_OHM,
            "lanc_id_resistor_ohm": LANC_ID_RESISTOR_OHM,
        },
    )


# ---------------------------------------------------------------------------
# Domain 2: 24-Pin MI-Shoe (XLR-H1 / ECM-B1M) & P11 0x91db059b Verifier
# ---------------------------------------------------------------------------


def _matches_mishoe_id_bin(resistance_ohm: Optional[int], tolerance: float = 0.10) -> bool:
    if resistance_ohm is None:
        return True
    if not isinstance(resistance_ohm, int) or resistance_ohm < 0:
        return False
    if resistance_ohm == 0:
        return True
    for expected in MISHOE_ID_LADDER_OHMS:
        if expected is None or expected == 0:
            continue
        if expected * (1.0 - tolerance) <= resistance_ohm <= expected * (1.0 + tolerance):
            return True
    return False


def verify_mishoe_digital_audio_and_p11_coexistence(
    *,
    accessory_model: str = "XLR-H1",
    sample_rate_hz: int = 48000,
    bit_depth: int = 24,
    channels: int = 4,
    id_resistors_ohm: Sequence[Optional[int]] = (22_000, 56_000, 150_000),
    logic_vdd_v: float = 3.15,
    unreg_v: float = 7.2,
    unreg_current_a: float = 0.65,
    reg_gnd_connected: bool = True,
    pgnd_connected: bool = True,
    hotshoe_wait_rc_on_tmo: int = LIBINFRAHOTSHOE_TMO_SAFE_RC,
    hotshoe_wait_blocks_forever: bool = False,
    p11_smart_handle_shimmed: bool = True,
    p11_smart_handle_ack_cmd: int = SMART_HANDLE_EVT_DETACHED_CMD,
    host_event: str = EVENT_XLR_H1_DIGMIC_ON,
    host_enum: str = VAL_CONNECT_SHOE_MIC_DIGITAL_XLR,
) -> MiShoeCoexistenceResult:
    """Verify 24-pin MI-Shoe digital audio (`XLR-H1` / `ECM-B1M`) + `P11` `0x91db059b` coexistence."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    # 1. ID1..ID3 6-bin resistor ladder verification
    if len(id_resistors_ohm) != 3:
        _add_code(codes, STATUS_BLOCKED_MISHOE_ID_LADDER)
        errors.append(
            f"MI-Shoe requires exactly 3 ID resistors (ID3, ID2, ID1 on Pins 1..3), got {len(id_resistors_ohm)}."
        )
    else:
        for idx, r_val in enumerate(id_resistors_ohm, start=1):
            if not _matches_mishoe_id_bin(r_val):
                _add_code(codes, STATUS_BLOCKED_MISHOE_ID_LADDER)
                errors.append(
                    f"MI-Shoe Pin {idx} ID resistor {r_val!r} Ohm does not match any valid 6-bin ladder "
                    "step (0 / 22k / 56k / 150k / 470k / open)."
                )

    # 2. Electrical rails (Pin 13 LOGIC_VDD 2.8-3.15V, Pin 17 UNREG 6.1-8.4V <= 1.6A, Pin 7/15/21 GND)
    if not reg_gnd_connected or not pgnd_connected:
        _add_code(codes, STATUS_BLOCKED_MISHOE_ELECTRICAL)
        errors.append(
            "MI-Shoe ground return missing (REG_GND Pins 7/15 and PGND Pin 21 must both be connected)."
        )
    if not (2.65 <= logic_vdd_v <= 3.25):
        _add_code(codes, STATUS_BLOCKED_MISHOE_ELECTRICAL)
        errors.append(
            f"MI-Shoe Pin 13 LOGIC_VDD {logic_vdd_v:.2f}V out of safe 2.8V-3.15V operating envelope."
        )
    elif not (MISHOE_LOGIC_VDD_RANGE_V[0] <= logic_vdd_v <= MISHOE_LOGIC_VDD_RANGE_V[1]):
        warnings.append(f"MI-Shoe LOGIC_VDD {logic_vdd_v:.2f}V near boundary of 2.8V-3.15V spec.")

    if unreg_v <= 0.0 or unreg_v > 8.6:
        _add_code(codes, STATUS_BLOCKED_MISHOE_ELECTRICAL)
        errors.append(f"MI-Shoe Pin 17 UNREG battery bus {unreg_v:.2f}V exceeds 6.1V-8.4V safe envelope.")
    elif unreg_v < MISHOE_UNREG_RANGE_V[0]:
        warnings.append(f"MI-Shoe UNREG {unreg_v:.2f}V below 6.1V; 48V phantom boost may droop.")

    if unreg_current_a < 0.0 or unreg_current_a > MISHOE_UNREG_MAX_CURRENT_A:
        _add_code(codes, STATUS_BLOCKED_MISHOE_ELECTRICAL)
        errors.append(
            f"MI-Shoe Pin 17 UNREG current {unreg_current_a:.2f}A exceeds fused {MISHOE_UNREG_MAX_CURRENT_A:.1f}A ceiling."
        )

    # 3. Digital I2S / PCM audio framing verification
    profile_key = (int(sample_rate_hz), int(bit_depth), int(channels))
    audio_label = MISHOE_VALID_AUDIO_PROFILES.get(profile_key, "UNSUPPORTED_AUDIO_PROFILE")
    if profile_key not in MISHOE_VALID_AUDIO_PROFILES:
        _add_code(codes, STATUS_BLOCKED_MISHOE_AUDIO_FRAMING)
        errors.append(
            f"Unsupported MI-Shoe digital PCM format {sample_rate_hz}Hz/{bit_depth}-bit/{channels}ch; "
            "expected 48kHz/(16b-2ch | 24b-2ch | 24b-4ch)."
        )

    norm_acc = accessory_model.strip().upper()
    if norm_acc == "XLR-H1" and (sample_rate_hz != 48000 or bit_depth != 24 or channels != 4):
        _add_code(codes, STATUS_BLOCKED_MISHOE_AUDIO_FRAMING)
        errors.append(
            f"XLR-H1 4-channel digital audio requires 48kHz / 24-bit / 4ch (CH1..CH4), "
            f"got {sample_rate_hz}Hz / {bit_depth}-bit / {channels}ch."
        )

    pcm_bitrate_bps = int(sample_rate_hz) * int(bit_depth) * int(channels)
    frame_bytes_per_sample_period = (int(bit_depth) // 8) * int(channels)

    # 4. libInfraHotshoe.so (0x5d90) timeout behavior
    timeout_safe = (not hotshoe_wait_blocks_forever) and (hotshoe_wait_rc_on_tmo == LIBINFRAHOTSHOE_TMO_SAFE_RC)
    if not timeout_safe:
        _add_code(codes, STATUS_BLOCKED_HOTSHOE_TIMEOUT_HANG)
        errors.append(
            f"libInfraHotshoe.so::WaitRecvCompMsgFromHotshoeRsrc (0x5d90) must return 0x8000 on "
            f"E_TMO={LIBINFRAHOTSHOE_E_TMO} without blocking (got rc={hex(hotshoe_wait_rc_on_tmo)}, "
            f"blocks_forever={hotshoe_wait_blocks_forever})."
        )

    # 5. P11 0x91db059b Detached Smart Handle ACK coexistence (xlr_h1_preserved=True)
    if not p11_smart_handle_shimmed:
        _add_code(codes, STATUS_BLOCKED_SMART_HANDLE_COLLISION)
        errors.append(
            "P11 Smart Handle queue 0x91db059b is unshimmed; FX6 appFw.so will block/assert at "
            "line 123 (0x7b) and fail MI-Shoe XLR-H1 preservation."
        )
    elif p11_smart_handle_ack_cmd == SMART_HANDLE_EVT_ATTACHED_CMD:
        _add_code(codes, STATUS_BLOCKED_SMART_HANDLE_COLLISION)
        errors.append(
            "P11 0x91db059b spoofed ATTACHED ACK (0x88000001 -> event 0x0226/550); FX6 UI suppresses "
            "FX3 native XLR-H1 4ch MI-Shoe audio! Must send DETACHED ACK (0x88000002 -> event 0x0227/551)."
        )
    elif p11_smart_handle_ack_cmd != SMART_HANDLE_EVT_DETACHED_CMD:
        _add_code(codes, STATUS_BLOCKED_SMART_HANDLE_COLLISION)
        errors.append(
            f"Unexpected P11 0x91db059b Smart Handle ACK cmd {hex(p11_smart_handle_ack_cmd)}; "
            f"expected {hex(SMART_HANDLE_EVT_DETACHED_CMD)}."
        )

    if norm_acc in ("XLR-H1", "XLR-K3M"):
        if host_event != EVENT_XLR_H1_DIGMIC_ON:
            _add_code(codes, STATUS_BLOCKED_MISHOE_AUDIO_FRAMING)
            errors.append(f"Expected host event {EVENT_XLR_H1_DIGMIC_ON!r}, got {host_event!r}.")
        if host_enum != VAL_CONNECT_SHOE_MIC_DIGITAL_XLR:
            _add_code(codes, STATUS_BLOCKED_MISHOE_AUDIO_FRAMING)
            errors.append(f"Expected host enum {VAL_CONNECT_SHOE_MIC_DIGITAL_XLR!r}, got {host_enum!r}.")

    valid = len(errors) == 0
    xlr_h1_preserved = (
        valid
        and p11_smart_handle_shimmed
        and p11_smart_handle_ack_cmd == SMART_HANDLE_EVT_DETACHED_CMD
    )
    status = STATUS_VERIFIED_SAFE if valid else codes[0]
    return MiShoeCoexistenceResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        accessory_model=accessory_model,
        xlr_h1_preserved=xlr_h1_preserved,
        audio_format_label=audio_label,
        sample_rate_hz=sample_rate_hz,
        bit_depth=bit_depth,
        channels=channels,
        pcm_bitrate_bps=pcm_bitrate_bps,
        frame_bytes_per_sample_period=frame_bytes_per_sample_period,
        libinfrahotshoe_timeout_safe=timeout_safe,
        p11_smart_handle_ack_cmd=hex(p11_smart_handle_ack_cmd),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "total_contacts": MISHOE_TOTAL_CONTACTS,
            "front_view_order": list(MISHOE_FRONT_VIEW_ORDER),
            "libinfrahotshoe_vma": hex(LIBINFRAHOTSHOE_WAIT_RECV_VMA),
            "smart_handle_queue_id": hex(SMART_HANDLE_QUEUE_ID),
            "i2s_32bit_slot_bitrate_bps": int(sample_rate_hz) * 32 * int(channels),
            "clean_room_public_spec_note": (
                "Pins 5/6 wire-level GVIF/I2S clock waveform is only partially disclosed in public "
                "community docs (mungewell/pico-timecode#7); host-side framing & libInfraHotshoe 0x5d90 verified."
            ),
        },
    )


# ---------------------------------------------------------------------------
# Domain 3: Sony CrSDK PTP2 (0x9201..0x9209) Remote Control Firewall
# ---------------------------------------------------------------------------


def _parse_opcode(raw: Any) -> int:
    if isinstance(raw, int):
        return raw
    if isinstance(raw, str):
        return int(raw.strip(), 0)
    raise ValueError(f"Unsupported PTP2 opcode type: {type(raw).__name__}")


def classify_crsdk_ptp2_request(
    request: Mapping[str, Any],
    *,
    vendor_extension_id: int = SONY_PTP_VENDOR_EXT_ID,
    sdio_handshake_complete: bool = True,
    allow_protocol_3_00: bool = False,
) -> CrSdkRequestDecision:
    """Classify a single CrSDK / PTP2 (`0x9201..0x922f`) request in a Stage-A/B RAM-overlay session."""
    raw_op = request.get("opcode", 0)
    try:
        opcode = _parse_opcode(raw_op)
    except ValueError:
        return CrSdkRequestDecision(
            opcode_hex=str(raw_op),
            opcode_name="INVALID_OPCODE",
            classification="INVALID",
            allowed=False,
            status=STATUS_BLOCKED_CRSDK_UNKNOWN_OP,
            property_or_action=str(request.get("property", request.get("action", ""))),
            reason=f"Malformed PTP2 opcode {raw_op!r}.",
        )

    op_hex = hex(opcode)
    prop_or_action = str(
        request.get("property")
        or request.get("action")
        or request.get("api")
        or request.get("command")
        or ""
    ).strip()
    norm_target = _norm_token(prop_or_action)

    # 1. Sony Vendor Extension ID & Nikon 0x920a..0x920f collision guard
    if vendor_extension_id != SONY_PTP_VENDOR_EXT_ID:
        return CrSdkRequestDecision(
            opcode_hex=op_hex,
            opcode_name="VENDOR_MISMATCH",
            classification="VENDOR_COLLISION",
            allowed=False,
            status=STATUS_BLOCKED_PTP_VENDOR_COLLISION,
            property_or_action=prop_or_action,
            reason=(
                f"PTP Vendor Extension ID {hex(vendor_extension_id)} != Sony {hex(SONY_PTP_VENDOR_EXT_ID)}; "
                "refusing 0x92xx interpretation."
            ),
        )

    if PTP_SONY_NIKON_COLLISION_RANGE[0] <= opcode <= PTP_SONY_NIKON_COLLISION_RANGE[1]:
        if bool(request.get("interpreted_as_nikon", False)):
            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name="NIKON_OPCODE_COLLISION",
                classification="VENDOR_COLLISION",
                allowed=False,
                status=STATUS_BLOCKED_PTP_VENDOR_COLLISION,
                property_or_action=prop_or_action,
                reason=(
                    f"Opcode {op_hex} falls in 0x920a..0x920f Sony/Nikon collision zone; "
                    "Nikon StartMovieRecInCard..GetFhdPicture misinterpretation blocked."
                ),
            )
        return CrSdkRequestDecision(
            opcode_hex=op_hex,
            opcode_name="SONY_ADVERTISED_UNKNOWN_PTP_OC",
            classification="UNVERIFIED_OPCODE",
            allowed=False,
            status=STATUS_BLOCKED_CRSDK_UNKNOWN_OP,
            property_or_action=prop_or_action,
            reason=f"Sony vendor opcode {op_hex} (0x920a..0x920f) is unverified for Stage-A/B writes.",
        )

    # 2. Global dangerous-token scan (NVRAM identity tamper / service escalation / firmware update)
    for tok in DANGEROUS_CRSDK_NVRAM_IDENTITY_TOKENS:
        if tok in norm_target:
            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name="NVRAM_IDENTITY_TAMPER",
                classification="DANGEROUS_NVRAM_TAMPER",
                allowed=False,
                status=STATUS_BLOCKED_CRSDK_NVRAM_TAMPER,
                property_or_action=prop_or_action,
                reason=(
                    f"Request {prop_or_action!r} touches protected NVRAM/identity token {tok!r}; "
                    "PRODUCT_MODEL (ALCIN_UUD) / calibration tampering blocked."
                ),
            )

    for tok in DANGEROUS_CRSDK_SERVICE_ESCALATION_TOKENS:
        if tok in norm_target:
            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name="SERVICE_ESCALATION",
                classification="DANGEROUS_SERVICE_ESCALATION",
                allowed=False,
                status=STATUS_BLOCKED_CRSDK_SERVICE_ESCALATION,
                property_or_action=prop_or_action,
                reason=(
                    f"Request {prop_or_action!r} attempts raw service-mode / Senser / PMCA escalation "
                    f"({tok}) inside a CrSDK PTP2 live session."
                ),
            )

    for tok in DANGEROUS_CRSDK_FIRMWARE_TOKENS:
        if tok in norm_target:
            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name="FIRMWARE_OR_FLASH_OP",
                classification="DANGEROUS_FIRMWARE_FLASH",
                allowed=False,
                status=STATUS_BLOCKED_CRSDK_FIRMWARE_FLASH,
                property_or_action=prop_or_action,
                reason=(
                    f"Request {prop_or_action!r} attempts firmware update, media format, or persistent "
                    f"flash/CAMSET mutation ({tok}) during Stage-A/B RAM-overlay session."
                ),
            )

    # 3. Handle SDIO_Connect (0x9201)
    if opcode == PTP_OC_SONY_SDIO_CONNECT:
        phase = request.get("phase")
        if phase not in (1, 2, 3):
            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name="PTP_OC_SONY_SDIO_Connect",
                classification="HANDSHAKE_ERROR",
                allowed=False,
                status=STATUS_BLOCKED_SDIO_HANDSHAKE_INCOMPLETE,
                property_or_action=prop_or_action or f"phase={phase}",
                reason=f"0x9201 SDIOConnect requires phase 1, 2, or 3, got {phase!r}.",
            )
        return CrSdkRequestDecision(
            opcode_hex=op_hex,
            opcode_name="PTP_OC_SONY_SDIO_Connect",
            classification="SAFE_HANDSHAKE",
            allowed=True,
            status=STATUS_VERIFIED_SAFE,
            property_or_action=f"SDIOConnect_phase_{phase}",
            reason=f"Sony 0x9201 SDIOConnect phase {phase} permitted.",
        )

    # 4. Handle SDIO_GetExtDeviceInfo (0x9202) protocol 0xc8 vs 0x12c regression check
    if opcode == PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO:
        proto = request.get("protocol_version", SONY_PROTOCOL_2_00)
        if isinstance(proto, str):
            proto = int(proto, 0)
        if proto == SONY_PROTOCOL_3_00 and not allow_protocol_3_00:
            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name="PTP_OC_SONY_SDIO_GetExtDeviceInfo",
                classification="PROTOCOL_3_00_REGRESSION",
                allowed=False,
                status=STATUS_BLOCKED_CRSDK_PROTOCOL_REGRESSION,
                property_or_action=f"protocol={hex(proto)}",
                reason=(
                    "SONY_PROTOCOL_3_00 (0x12c) triggers capture regression (libgphoto2#676); "
                    "enforce fallback to SONY_PROTOCOL_2_00 (0xc8)."
                ),
            )
        return CrSdkRequestDecision(
            opcode_hex=op_hex,
            opcode_name="PTP_OC_SONY_SDIO_GetExtDeviceInfo",
            classification="SAFE_READONLY_QUERY",
            allowed=True,
            status=STATUS_VERIFIED_SAFE,
            property_or_action=f"protocol={hex(proto)}",
            reason="0x9202 SDIO_GetExtDeviceInfo read-only query permitted.",
        )

    # 5. Read-only PTP2 opcodes
    if opcode in PTP_SONY_READONLY_OPCODES:
        return CrSdkRequestDecision(
            opcode_hex=op_hex,
            opcode_name=PTP_SONY_READONLY_OPCODES[opcode],
            classification="SAFE_READONLY_QUERY",
            allowed=True,
            status=STATUS_VERIFIED_SAFE,
            property_or_action=prop_or_action or PTP_SONY_READONLY_OPCODES[opcode],
            reason="Read-only Sony PTP2 query permitted.",
        )

    # 6. CrSDK ImportLUTFile high-level request (safe only with media card & RAM/user LUT target)
    if norm_target in ("SCRSDK::IMPORTLUTFILE", "IMPORTLUTFILE"):
        if not bool(request.get("media_card_inserted", True)):
            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name="SCRSDK::ImportLUTFile",
                classification="NO_MEDIA_CARD",
                allowed=False,
                status=STATUS_BLOCKED_CRSDK_NO_MEDIA_CARD,
                property_or_action=prop_or_action,
                reason="SCRSDK::ImportLUTFile requires at least one media card inserted.",
            )
        return CrSdkRequestDecision(
            opcode_hex=op_hex,
            opcode_name="SCRSDK::ImportLUTFile",
            classification="SAFE_LIVE_SHOOTING",
            allowed=True,
            status=STATUS_VERIFIED_SAFE,
            property_or_action=prop_or_action,
            reason="ImportLUTFile permitted into user LUT slot with media card present.",
        )

    # 7. Write/Control opcodes (0x9205 SetExtDevicePropValue, 0x9207 ControlDevice) require completed SDIOConnect
    if opcode in (PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, PTP_OC_SONY_SDIO_CONTROL_DEVICE):
        if not sdio_handshake_complete:
            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name=(
                    "PTP_OC_SONY_SDIO_SetExtDevicePropValue"
                    if opcode == PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE
                    else "PTP_OC_SONY_SDIO_ControlDevice"
                ),
                classification="HANDSHAKE_INCOMPLETE",
                allowed=False,
                status=STATUS_BLOCKED_SDIO_HANDSHAKE_INCOMPLETE,
                property_or_action=prop_or_action,
                reason=(
                    f"Opcode {op_hex} requires completed 3-step 0x9201 SDIOConnect handshake "
                    "(1,0,0)->(2,0,0)->(3,0,0) first."
                ),
            )

        if opcode == PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE:
            if norm_target in SAFE_CRSDK_LIVE_SHOOTING_PROPERTIES:
                # Extra unit guard on ShutterAngle (CrSDK millidegrees vs RTMD 1/60 deg)
                if norm_target in ("CRDEVICEPROPERTY_SHUTTERANGLE", "SHUTTERANGLE"):
                    val = request.get("value")
                    unit = str(request.get("unit", "millidegrees")).strip().lower()
                    if unit != "millidegrees":
                        return CrSdkRequestDecision(
                            opcode_hex=op_hex,
                            opcode_name="PTP_OC_SONY_SDIO_SetExtDevicePropValue",
                            classification="UNIT_MISMATCH",
                            allowed=False,
                            status=STATUS_BLOCKED_CRSDK_UNKNOWN_OP,
                            property_or_action=prop_or_action,
                            reason=(
                                f"CrDeviceProperty_ShutterAngle requires millidegrees (e.g. 180000 = 180.0 deg), "
                                f"not {unit!r}."
                            ),
                        )
                    if isinstance(val, int) and not (1000 <= val <= 360000):
                        return CrSdkRequestDecision(
                            opcode_hex=op_hex,
                            opcode_name="PTP_OC_SONY_SDIO_SetExtDevicePropValue",
                            classification="OUT_OF_RANGE",
                            allowed=False,
                            status=STATUS_BLOCKED_CRSDK_UNKNOWN_OP,
                            property_or_action=prop_or_action,
                            reason=f"ShutterAngle millidegrees {val} out of range [1000..360000].",
                        )
                return CrSdkRequestDecision(
                    opcode_hex=op_hex,
                    opcode_name="PTP_OC_SONY_SDIO_SetExtDevicePropValue",
                    classification="SAFE_LIVE_SHOOTING",
                    allowed=True,
                    status=STATUS_VERIFIED_SAFE,
                    property_or_action=prop_or_action,
                    reason=f"Safe live-shooting PTP2 property write permitted ({prop_or_action}).",
                )

            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name="PTP_OC_SONY_SDIO_SetExtDevicePropValue",
                classification="UNVERIFIED_PROPERTY",
                allowed=False,
                status=STATUS_BLOCKED_CRSDK_UNKNOWN_OP,
                property_or_action=prop_or_action,
                reason=f"Unverified PTP2 property write {prop_or_action!r} rejected (fail-closed).",
            )

        # opcode == 0x9207 ControlDevice
        if norm_target in SAFE_CRSDK_CONTROL_ACTIONS:
            return CrSdkRequestDecision(
                opcode_hex=op_hex,
                opcode_name="PTP_OC_SONY_SDIO_ControlDevice",
                classification="SAFE_LIVE_SHOOTING",
                allowed=True,
                status=STATUS_VERIFIED_SAFE,
                property_or_action=prop_or_action,
                reason=f"Safe live-shooting control action permitted ({prop_or_action}).",
            )
        return CrSdkRequestDecision(
            opcode_hex=op_hex,
            opcode_name="PTP_OC_SONY_SDIO_ControlDevice",
            classification="UNVERIFIED_CONTROL",
            allowed=False,
            status=STATUS_BLOCKED_CRSDK_UNKNOWN_OP,
            property_or_action=prop_or_action,
            reason=f"Unverified PTP2 control action {prop_or_action!r} rejected (fail-closed).",
        )

    return CrSdkRequestDecision(
        opcode_hex=op_hex,
        opcode_name="UNKNOWN_PTP_OPCODE",
        classification="UNKNOWN_OPCODE",
        allowed=False,
        status=STATUS_BLOCKED_CRSDK_UNKNOWN_OP,
        property_or_action=prop_or_action,
        reason=f"Unsupported or unknown PTP2 opcode {op_hex} rejected (fail-closed).",
    )


def audit_crsdk_ptp2_session(
    requests: Sequence[Mapping[str, Any]],
    *,
    vendor_extension_id: int = SONY_PTP_VENDOR_EXT_ID,
    sdio_connect_phases: Sequence[int] = (1, 2, 3),
    protocol_version: int = SONY_PROTOCOL_2_00,
    allow_protocol_3_00: bool = False,
) -> CrSdkFirewallResult:
    """Firewall a CrSDK / PTP2 (`0x9201..0x9209`) remote control session during Stage-A/B RAM overlay."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    decisions: List[CrSdkRequestDecision] = []
    permitted: List[str] = []
    blocked: List[str] = []

    seen_phases: Set[int] = set(sdio_connect_phases)
    handshake_complete = (1 in seen_phases and 2 in seen_phases and 3 in seen_phases)

    if vendor_extension_id != SONY_PTP_VENDOR_EXT_ID:
        _add_code(codes, STATUS_BLOCKED_PTP_VENDOR_COLLISION)
        errors.append(
            f"Vendor Extension ID {hex(vendor_extension_id)} != Sony {hex(SONY_PTP_VENDOR_EXT_ID)}."
        )

    if protocol_version == SONY_PROTOCOL_3_00 and not allow_protocol_3_00:
        _add_code(codes, STATUS_BLOCKED_CRSDK_PROTOCOL_REGRESSION)
        errors.append(
            "Session protocol 0x12c (SONY_PROTOCOL_3_00) rejected due to libgphoto2#676 capture "
            "regression risk; negotiate 0xc8 (SONY_PROTOCOL_2_00)."
        )

    for req in requests:
        # Track progressive 0x9201 SDIOConnect phases if caller supplies them in-stream
        try:
            op = _parse_opcode(req.get("opcode", 0))
        except ValueError:
            op = -1
        if op == PTP_OC_SONY_SDIO_CONNECT and req.get("phase") in (1, 2, 3):
            phase_val = int(req["phase"])
            # Enforce ascending 1 -> 2 -> 3 phase ordering
            if (phase_val == 2 and 1 not in seen_phases) or (
                phase_val == 3 and (1 not in seen_phases or 2 not in seen_phases)
            ):
                dec = CrSdkRequestDecision(
                    opcode_hex=hex(op),
                    opcode_name="PTP_OC_SONY_SDIO_Connect",
                    classification="HANDSHAKE_ORDER_ERROR",
                    allowed=False,
                    status=STATUS_BLOCKED_SDIO_HANDSHAKE_INCOMPLETE,
                    property_or_action=f"SDIOConnect_phase_{phase_val}",
                    reason="0x9201 SDIOConnect phases must execute in strict order (1,0,0)->(2,0,0)->(3,0,0).",
                )
                decisions.append(dec)
                _add_code(codes, dec.status)
                blocked.append(dec.property_or_action)
                errors.append(dec.reason)
                continue
            seen_phases.add(phase_val)
            handshake_complete = (1 in seen_phases and 2 in seen_phases and 3 in seen_phases)

        dec = classify_crsdk_ptp2_request(
            req,
            vendor_extension_id=vendor_extension_id,
            sdio_handshake_complete=handshake_complete,
            allow_protocol_3_00=allow_protocol_3_00,
        )
        decisions.append(dec)
        label = f"{dec.opcode_hex}:{dec.property_or_action or dec.opcode_name}"
        if dec.allowed:
            permitted.append(label)
        else:
            _add_code(codes, dec.status)
            blocked.append(label)
            errors.append(dec.reason)

    valid = len(errors) == 0
    status = STATUS_VERIFIED_SAFE if valid else codes[0]
    return CrSdkFirewallResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        vendor_extension_id_hex=hex(vendor_extension_id),
        sdio_handshake_complete=handshake_complete,
        negotiated_protocol_hex=hex(protocol_version),
        permitted_requests=tuple(permitted),
        blocked_requests=tuple(blocked),
        decisions=tuple(decisions),
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "total_requests": len(decisions),
            "permitted_count": len(permitted),
            "blocked_count": len(blocked),
            "sdio_phases_seen": sorted(seen_phases),
        },
    )


# ---------------------------------------------------------------------------
# Domain 4: CXD90057 SPACC (0xf7fc0000) AES-XTS-256 Block-Layer Guard
# ---------------------------------------------------------------------------


def is_aes_xts_partition(part_type: int, flag: int) -> bool:
    """Return True iff partition uses CXD90057 SPACC AES-XTS-256 (`type == 5 and flag & 1`)."""
    return (int(part_type) == 5) and ((int(flag) & 1) != 0)


def _resolve_partition_crypto_map(
    sector0_bytes: Optional[bytes],
) -> Tuple[Dict[int, Tuple[int, int, str]], List[str]]:
    """Build `{part_index: (part_type, flag, expected_node)}` from Sector 0 or canonical FX3 map."""
    errors: List[str] = []
    if sector0_bytes is not None:
        sec_res = verify_sector0_partition_table(sector0_bytes)
        if not sec_res.magic_ok or not sec_res.version_ok:
            errors.append(f"Invalid Sector 0 table passed to SPACC guard: {sec_res.errors}")
        mapping: Dict[int, Tuple[int, int, str]] = {}
        for p in sec_res.partitions:
            idx = int(p["index"])  # type: ignore[arg-type]
            ptype = int(p["type"])  # type: ignore[arg-type]
            flag = int(p["flag"])  # type: ignore[arg-type]
            node = str(p["device_node"])
            mapping[idx] = (ptype, flag, node)
        return mapping, errors

    fallback: Dict[int, Tuple[int, int, str]] = {}
    for idx, (_start, _size, ptype, flag, _label) in DEFAULT_FX3_PARTITION_CRYPTO_MAP.items():
        node = f"/dev/cnflasha{idx}" if is_aes_xts_partition(ptype, flag) else f"/dev/pnflasha{idx}"
        fallback[idx] = (ptype, flag, node)
    return fallback, errors


def _parse_flash_device_node(path: str) -> Optional[Tuple[str, int]]:
    m = re.search(r"/dev/(cnflasha|pnflasha|nflasha)(\d+)\b", path)
    if not m:
        return None
    return m.group(1), int(m.group(2))


def _overlaps_spacc_mmio(addr: int, size: int = 4) -> bool:
    end_addr = addr + max(1, size) - 1
    return not (end_addr < SPACC_MMIO_BASE or addr > SPACC_MMIO_END)


def audit_spacc_block_layer(
    *,
    operations: Sequence[Mapping[str, Any]] = (),
    script_text: str = "",
    sector0_bytes: Optional[bytes] = None,
    allow_raw_ciphertext_backup_read: bool = False,
) -> SpaccBlockGuardResult:
    """Enforce `SPACC` (`0xf7fc0000`) `AES-XTS-256` `/dev/cnflasha*` vs `/dev/nflasha*` boundary."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []
    decisions: List[SpaccBlockOpDecision] = []

    part_map, map_errs = _resolve_partition_crypto_map(sector0_bytes)
    for me in map_errs:
        _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
        errors.append(me)

    xts_parts = tuple(sorted(idx for idx, (pt, fl, _) in part_map.items() if is_aes_xts_partition(pt, fl)))
    plain_parts = tuple(sorted(idx for idx, (pt, fl, _) in part_map.items() if not is_aes_xts_partition(pt, fl)))

    # Track per-partition node usage across the whole session/script to catch nflasha vs cnflasha mixing
    partition_nodes_seen: Dict[int, Set[str]] = {}

    def record_node(p_idx: int, node_kind: str) -> None:
        partition_nodes_seen.setdefault(p_idx, set()).add(node_kind)

    # 1. Inspect structured operations
    for op_item in operations:
        op_name = _norm_token(str(op_item.get("operation", "read_plaintext")))

        # 1a. SPACC MMIO userland touch guard (0xf7fc0000..0xf7fcffff)
        if "mmio_addr" in op_item:
            raw_addr = op_item["mmio_addr"]
            addr = int(raw_addr, 0) if isinstance(raw_addr, str) else int(raw_addr)
            size = int(op_item.get("size", 4))
            ring = _norm_token(str(op_item.get("ring", "userland")))
            if _overlaps_spacc_mmio(addr, size) and ring != "KERNEL_SPACC_DRIVER":
                reason = (
                    f"Userland access to SPACC MMIO {hex(addr)} (size={size}) blocked: "
                    "AES-XTS-256 hardware key slots at 0xf7fc0000 are kernel-only."
                )
                _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
                errors.append(reason)
                decisions.append(
                    SpaccBlockOpDecision(
                        target=hex(addr),
                        operation=op_name,
                        partition_index=None,
                        is_aes_xts_partition=None,
                        expected_plaintext_node=None,
                        allowed=False,
                        status=STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
                        reason=reason,
                    )
                )
                continue

        dev_str = str(op_item.get("device", "")).strip()
        other_dev_str = str(op_item.get("other_device", "")).strip()
        parsed = _parse_flash_device_node(dev_str)
        if parsed is None:
            if dev_str:
                reason = f"Unrecognized block device target {dev_str!r} rejected (fail-closed)."
                _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
                errors.append(reason)
                decisions.append(
                    SpaccBlockOpDecision(
                        target=dev_str,
                        operation=op_name,
                        partition_index=None,
                        is_aes_xts_partition=None,
                        expected_plaintext_node=None,
                        allowed=False,
                        status=STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
                        reason=reason,
                    )
                )
            continue

        node_kind, p_idx = parsed
        record_node(p_idx, node_kind)
        if other_dev_str:
            other_parsed = _parse_flash_device_node(other_dev_str)
            if other_parsed is not None:
                record_node(other_parsed[1], other_parsed[0])
                if other_parsed[0] != node_kind:
                    reason = (
                        f"Mixed raw {node_kind} ({dev_str}) vs {other_parsed[0]} ({other_dev_str}) "
                        "cross-layer read/comparison blocked."
                    )
                    _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
                    errors.append(reason)
                    decisions.append(
                        SpaccBlockOpDecision(
                            target=f"{dev_str}<->{other_dev_str}",
                            operation=op_name,
                            partition_index=p_idx,
                            is_aes_xts_partition=None,
                            expected_plaintext_node=None,
                            allowed=False,
                            status=STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
                            reason=reason,
                        )
                    )
                    continue

        if p_idx not in part_map:
            reason = f"Partition p{p_idx} ({dev_str}) has no verified Sector 0 type/flag metadata (fail-closed)."
            _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
            errors.append(reason)
            decisions.append(
                SpaccBlockOpDecision(
                    target=dev_str,
                    operation=op_name,
                    partition_index=p_idx,
                    is_aes_xts_partition=None,
                    expected_plaintext_node=None,
                    allowed=False,
                    status=STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
                    reason=reason,
                )
            )
            continue

        ptype, flag, expected_node = part_map[p_idx]
        xts = is_aes_xts_partition(ptype, flag)

        # Write operations to eMMC devices are always forbidden under hard-locked policy
        is_write = op_name in ("WRITE", "DD_WRITE", "MOUNT_RW", "MKFS", "FORMAT", "FLASH") or bool(
            op_item.get("writable", False)
        )

        # Layer mismatch check:
        # - XTS partition accessed via nflasha/pnflasha for mount/plaintext/verify -> MISMATCH
        # - Non-XTS partition accessed via cnflasha -> MISMATCH (SPACC double/bogus decrypt!)
        layer_mismatch = False
        mismatch_reason = ""
        if xts and node_kind in ("nflasha", "pnflasha"):
            if op_name == "RAW_CIPHERTEXT_BACKUP_READ" and allow_raw_ciphertext_backup_read and not is_write:
                pass
            else:
                layer_mismatch = True
                mismatch_reason = (
                    f"{dev_str} targets AES-XTS-256 partition p{p_idx} (type={ptype}, flag={flag}) "
                    f"as raw ciphertext for {op_name}; must use {expected_node} for SPACC sector-tweak decryption."
                )
        elif (not xts) and node_kind == "cnflasha":
            layer_mismatch = True
            mismatch_reason = (
                f"{dev_str} uses /dev/cnflasha* on plaintext/non-XTS partition p{p_idx} "
                f"(type={ptype}, flag={flag}); must use /dev/pnflasha{p_idx} or /dev/nflasha{p_idx}."
            )

        if layer_mismatch:
            _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
            errors.append(mismatch_reason)
            decisions.append(
                SpaccBlockOpDecision(
                    target=dev_str,
                    operation=op_name,
                    partition_index=p_idx,
                    is_aes_xts_partition=xts,
                    expected_plaintext_node=expected_node,
                    allowed=False,
                    status=STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
                    reason=mismatch_reason,
                )
            )
            continue

        if is_write:
            reason = (
                f"Write operation {op_name} to {dev_str} blocked: PERSISTENT_EMMC_WRITES_AUTHORIZED=False."
            )
            _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
            errors.append(reason)
            decisions.append(
                SpaccBlockOpDecision(
                    target=dev_str,
                    operation=op_name,
                    partition_index=p_idx,
                    is_aes_xts_partition=xts,
                    expected_plaintext_node=expected_node,
                    allowed=False,
                    status=STATUS_BLOCKED_PERSISTENT_EMMC_WRITE,
                    reason=reason,
                )
            )
            continue

        decisions.append(
            SpaccBlockOpDecision(
                target=dev_str,
                operation=op_name,
                partition_index=p_idx,
                is_aes_xts_partition=xts,
                expected_plaintext_node=expected_node,
                allowed=True,
                status=STATUS_VERIFIED_SAFE,
                reason=f"Read-only {op_name} on {dev_str} matches cryptographic layer ({'AES-XTS-256' if xts else 'plaintext'}).",
            )
        )

    # 2. Inspect shell script lines for nflasha/cnflasha/SPACC hazards
    for raw_line in script_text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        # Detect SPACC MMIO 0xf7fcxxxx touch in userland shell
        for hex_match in re.findall(r"0x[0-9a-fA-F]{6,8}", line):
            val = int(hex_match, 16)
            if _overlaps_spacc_mmio(val, 4):
                reason = (
                    f"Userland script references SPACC MMIO address {hex(val)} ({line!r}); "
                    "direct userland SPACC access is forbidden."
                )
                _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
                errors.append(reason)
                decisions.append(
                    SpaccBlockOpDecision(
                        target=hex(val),
                        operation="SCRIPT_SPACC_MMIO",
                        partition_index=None,
                        is_aes_xts_partition=None,
                        expected_plaintext_node=None,
                        allowed=False,
                        status=STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
                        reason=reason,
                    )
                )

        # Detect flash device nodes referenced in shell commands
        for m in re.finditer(r"/dev/(cnflasha|pnflasha|nflasha)(\d+)\b", line):
            node_kind = m.group(1)
            p_idx = int(m.group(2))
            full_dev = m.group(0)
            record_node(p_idx, node_kind)

            ptype, flag, expected_node = part_map.get(p_idx, (-1, 0, ""))
            xts = is_aes_xts_partition(ptype, flag) if p_idx in part_map else False
            lower_line = line.lower()

            if p_idx in part_map:
                if xts and node_kind in ("nflasha", "pnflasha"):
                    reason = (
                        f"Script accesses AES-XTS-256 partition p{p_idx} via raw {full_dev} ({line!r}); "
                        f"must use {expected_node}."
                    )
                    _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
                    errors.append(reason)
                    decisions.append(
                        SpaccBlockOpDecision(
                            target=full_dev,
                            operation="SCRIPT_RAW_NFLASHA_ON_XTS",
                            partition_index=p_idx,
                            is_aes_xts_partition=True,
                            expected_plaintext_node=expected_node,
                            allowed=False,
                            status=STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
                            reason=reason,
                        )
                    )
                elif (not xts) and node_kind == "cnflasha":
                    reason = (
                        f"Script uses /dev/cnflasha{p_idx} on non-XTS plaintext partition p{p_idx} ({line!r}); "
                        f"must use {expected_node}."
                    )
                    _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
                    errors.append(reason)
                    decisions.append(
                        SpaccBlockOpDecision(
                            target=full_dev,
                            operation="SCRIPT_CNFLASHA_ON_PLAINTEXT",
                            partition_index=p_idx,
                            is_aes_xts_partition=False,
                            expected_plaintext_node=expected_node,
                            allowed=False,
                            status=STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH,
                            reason=reason,
                        )
                    )

            # Flag persistent writes onto any flash node in script
            if f"of={full_dev}" in lower_line or "mkfs" in lower_line or "-o rw" in lower_line:
                reason = f"Persistent write command onto {full_dev} blocked ({line!r})."
                _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
                errors.append(reason)

    # 3. Cross-check same-partition node mixing (e.g., nflasha15 + cnflasha15 in same audit)
    for p_idx, kinds in sorted(partition_nodes_seen.items()):
        if "cnflasha" in kinds and ("nflasha" in kinds or "pnflasha" in kinds):
            reason = (
                f"Partition p{p_idx} mixes raw {sorted(kinds)} device nodes in the same session; "
                "cannot mix ciphertext nflasha* and decrypted cnflasha* layers."
            )
            _add_code(codes, STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH)
            errors.append(reason)

    valid = len(errors) == 0
    if not valid and STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH in codes:
        status = STATUS_BLOCKED_CNFLASHA_XTS_LAYER_MISMATCH
    elif not valid:
        status = codes[0]
    else:
        status = STATUS_VERIFIED_SAFE

    return SpaccBlockGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        decisions=tuple(decisions),
        xts_partitions=xts_parts,
        plaintext_partitions=plain_parts,
        errors=tuple(errors),
        warnings=tuple(warnings),
        details={
            "spacc_mmio_range": [hex(SPACC_MMIO_BASE), hex(SPACC_MMIO_END)],
            "scu_mmio_base": hex(SCU_MMIO_BASE),
            "sdm2_magic": SDM2_MAGIC_ASCII,
            "sdm2_version": SDM2_VERSION_ASCII,
            "partitions_checked": len(part_map),
        },
    )


# ---------------------------------------------------------------------------
# Unified Phase 38 Safety Evaluator & CLI
# ---------------------------------------------------------------------------


def evaluate_phase38_safety_guards(
    *,
    ltc_kwargs: Optional[Mapping[str, Any]] = None,
    mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    crsdk_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    crsdk_kwargs: Optional[Mapping[str, Any]] = None,
    spacc_operations: Optional[Sequence[Mapping[str, Any]]] = None,
    spacc_script_text: str = "",
    spacc_sector0_bytes: Optional[bytes] = None,
) -> Phase38GuardReport:
    """Run all 4 Phase 38 hardware/protocol safety verifiers in fail-closed mode."""
    ltc_res = verify_multiport_ltc_vs_uart_boot(**dict(ltc_kwargs or {}))
    mishoe_res = verify_mishoe_digital_audio_and_p11_coexistence(**dict(mishoe_kwargs or {}))

    default_crsdk_reqs: Tuple[Mapping[str, Any], ...] = (
        {"opcode": PTP_OC_SONY_SDIO_GET_EXT_DEVICE_INFO, "protocol_version": SONY_PROTOCOL_2_00},
        {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "CrDeviceProperty_ExposureIndex", "value": 800},
        {"opcode": PTP_OC_SONY_SDIO_SET_EXT_DEVICE_PROP_VALUE, "property": "CrDeviceProperty_ShutterAngle", "value": 180000, "unit": "millidegrees"},
        {"opcode": PTP_OC_SONY_SDIO_CONTROL_DEVICE, "action": "MovieRec"},
    )
    crsdk_res = audit_crsdk_ptp2_session(
        default_crsdk_reqs if crsdk_requests is None else crsdk_requests,
        **dict(crsdk_kwargs or {}),
    )

    default_spacc_ops: Tuple[Mapping[str, Any], ...] = (
        {"device": "/dev/cnflasha15", "operation": "read_plaintext"},
        {"device": "/dev/pnflasha2", "operation": "read_plaintext"},
    )
    spacc_res = audit_spacc_block_layer(
        operations=default_spacc_ops if spacc_operations is None else spacc_operations,
        script_text=spacc_script_text,
        sector0_bytes=spacc_sector0_bytes,
    )

    all_errors = (
        *ltc_res.errors,
        *mishoe_res.errors,
        *crsdk_res.errors,
        *spacc_res.errors,
    )
    all_passed = ltc_res.valid and mishoe_res.valid and crsdk_res.valid and spacc_res.valid
    if all_passed:
        overall_status = STATUS_VERIFIED_SAFE
    else:
        for r in (ltc_res, mishoe_res, crsdk_res, spacc_res):
            if not r.valid:
                overall_status = r.status
                break
        else:
            overall_status = "BLOCKED_PHASE38_GUARD"

    return Phase38GuardReport(
        schema=CRSDK_MISHOE_LTC_SPACC_GUARD_SCHEMA,
        version=CRSDK_MISHOE_LTC_SPACC_GUARD_VERSION,
        clean_room_forced=_is_forced_clean_room(),
        all_passed=all_passed,
        status=overall_status,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        ltc_guard=ltc_res,
        mishoe_guard=mishoe_res,
        crsdk_firewall=crsdk_res,
        spacc_guard=spacc_res,
        errors=all_errors,
    )


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="crsdk_mishoe_ltc_spacc_guard",
        description="Phase 38 CrSDK PTP2 / MI-Shoe / Multi-Port LTC / SPACC Safety Verifier",
    )
    parser.add_argument("--self-check", action="store_true", help="Run baseline Phase 38 safety self-check")
    parser.add_argument("--json", action="store_true", help="Emit structured JSON report")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_phase38_safety_guards()
    if args.json or args.self_check:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(f"status={report.status} all_passed={report.all_passed}\n")
    return 0 if report.all_passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
