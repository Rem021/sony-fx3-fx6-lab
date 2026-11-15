"""Phase 155 — Pillar 20 (20/20 Milestone): Real-Hardware CXD90057 1.8V ttyAMA0 460800n8
Passive Boot-Stage Triage Decoder, Multi-USB 1.8V Electrical Firewall & Last-Resort ISP Runbook Verifier.

Closes the real-hardware passive diagnostic and last-resort hardware-ISP triage chain for
Sony ILME-FX3 (`7.02`, `p1:/boot/kemco.txt` `cfg.uart=1 console=ttyAMA0,460800n8`) while
hard-locking all physical write/fuse safety gates:
- `PASSIVE_TX_BYTES_EMITTED = 0`
- `PHYSICAL_DEVICE_WRITES = 0`
- `OTP_FUSE_TOUCHES = 0`
- `OTP_FUSE_WRITES = 0`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects real FX3 `7.02` donor boot configs (`kemco.txt`, `tomco.txt`, `init`, `libsencore.so`,
     and bounded 4 KiB header of `cpapp-b.bin`) strictly via
     `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)`.
   - Validates `p1:/boot/kemco.txt` diagnostic console profile (`cfg.uart=1`,
     `console=ttyAMA0,460800n8`) against stock `console=ttynull0` baseline.
   - Falls back deterministically to pinned `CLEAN_ROOM_SYNTHETIC` descriptors when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donors are absent, leaking zero raw Sony firmware bytes.

2. **Pillar A — Passive `1.8V` RX-Only `460800 8N1` Boot-Stage Triage Engine (8 Scenarios)**:
   - Classifies live/captured FX3 `ttyAMA0` boot logs across all 6 boot stages:
     - `STAGE_0_BOOTROM_SPI_NOR_IPL`
     - `STAGE_1_BLOADER_BL31_ATF`
     - `STAGE_2_LINUX_4_9_337_SCEL_KERNEL`
     - `STAGE_3_SPACC_CNFLASHA15_EXT2_USR`
     - `STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER`
     - `STAGE_5_STAGEB_APPFW_BIG6_READY`
   - Maps any stall / panic / EROFS / manifest error to the exact lowest-impact
     deterministic recovery action (`EJECT_SD_47US_BYPASS`, `CREATE_STOP_STAGEB_FLAG`,
     `HOLD_MENU_SHUTTER_POWER`, `P1_LINE1_MODE_CLEAR`, or `TIER0_VAULT_RESTORE`).

3. **Pillar B — `1.8V` Logic-Level & Multi-USB `VMC-BNCM1` Contention Firewall (6 Scenarios)**:
   - Hard-blocks `3.3V` / `5.0V` UART adapters (fatal `CXD90057` `1.8V` IO pad over-voltage),
     under-voltage adapters (`< 1.65V`), physical TX-connected setups / active TX injection
     (`passive_tx_bytes_emitted == 0`), simultaneous `VMC-BNCM1` (`680 kOhm` LTC adapter) or
     `LANC` (`100 kOhm`) attachment, and competing multi-USB host bus contention during `H0`.

4. **Pillar C — Last-Resort Off-Chip Hardware ISP (`1.8V VCCQ` eMMC + `1.8V` SPI-NOR) Emergency Checklist (6 Scenarios)**:
   - Validates `1.8V VCCQ` eMMC + `1.8V` SPI-NOR rail voltage, SoC `RESET_N` isolation +
     battery/USB disconnect, fly-wire length (`<= 10.0 cm`), `EXT_CSD[179]`
     (`BOOT_PARTITION_ENABLE`, `BOOT_ACK`, `PARTITION_ACCESS == 0`), `EXT_CSD[177]`
     (`BOOT_BUS_CONDITIONS`), `EXT_CSD[162]` (`RST_n_FUNCTION`, blocking OTP mutation),
     and per-camera `CID`-bound `pnflasha*` + `/dev/mtd0ro` vault pairing with
     `persistent_emmc_writes_authorized = False` and `spi_nor_write_authorized = False`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import re
import stat
import struct
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .bootrom_usb_and_emmc_bootpart_verifier import (
    BOOT_BUS_RESERVED_MASK,
    BOOT_PART_ENABLE_BOOT0,
    BOOT_PART_ENABLE_BOOT1,
    EMMC_EXT_CSD_BOOT_BUS_COND_IDX,
    EMMC_EXT_CSD_BYTES,
    EMMC_EXT_CSD_PART_CONFIG_IDX,
    EMMC_EXT_CSD_RST_N_IDX,
    FX3_DEFAULT_BOOT_BUS_CONDITIONS,
    FX3_DEFAULT_PART_CONFIG,
    PART_CONFIG_ACCESS_MASK,
    PART_CONFIG_BOOT_ACK_BIT,
    PART_CONFIG_ENABLE_MASK,
    PART_CONFIG_ENABLE_SHIFT,
    PART_CONFIG_RESERVED_BIT7,
)
from .files import is_forced_clean_room, local_path, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE155_SCHEMA: str = "fx3-realhw-uart-460800-post-triage-and-isp-guard-v1"
PHASE155_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# UART Electrical & Framing Constants
UART_460800_BAUD: int = 460800
UART_460800_FRAMING: str = "8N1"
UART_460800_CONSOLE_ARG: str = "console=ttyAMA0,460800n8"
UART_1V8_NOMINAL_V: float = 1.80
UART_1V8_MIN_SAFE_V: float = 1.65
UART_1V8_MAX_SAFE_V: float = 1.98
UART_OVERVOLTAGE_3V3_V: float = 3.30
UART_OVERVOLTAGE_5V0_V: float = 5.00
VMC_BNCM1_LTC_OHM_MIN: float = 578_000.0
VMC_BNCM1_LTC_OHM_MAX: float = 782_000.0
LANC_ID_OHM_MIN: float = 85_000.0
LANC_ID_OHM_MAX: float = 115_000.0

# Off-Chip Hardware ISP Constants
ISP_VCCQ_NOMINAL_V: float = 1.80
ISP_VCCQ_MIN_SAFE_V: float = 1.65
ISP_VCCQ_MAX_SAFE_V: float = 1.98
ISP_SPI_NOR_NOMINAL_V: float = 1.80
ISP_MAX_FLYWIRE_CM: float = 10.0
ISP_VALID_EXT_CSD_162_RST_N_VALUES: Tuple[int, ...] = (0x00, 0x01, 0x02)

# 6 Boot Stages for ttyAMA0 460800n8 Triage
UART_460800_BOOT_STAGES: Tuple[str, ...] = (
    "STAGE_0_BOOTROM_SPI_NOR_IPL",
    "STAGE_1_BLOADER_BL31_ATF",
    "STAGE_2_LINUX_4_9_337_SCEL_KERNEL",
    "STAGE_3_SPACC_CNFLASHA15_EXT2_USR",
    "STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER",
    "STAGE_5_STAGEB_APPFW_BIG6_READY",
)
UART_460800_STAGE_INDEX_MAP: Dict[str, int] = {
    stage: idx for idx, stage in enumerate(UART_460800_BOOT_STAGES)
}

# Deterministic Lowest-Impact Recovery Actions
ACTION_NONE_HEALTHY: str = "NONE_HEALTHY"
ACTION_EJECT_SD_47US_BYPASS: str = "EJECT_SD_47US_BYPASS"
ACTION_CREATE_STOP_STAGEB_FLAG: str = "CREATE_STOP_STAGEB_FLAG"
ACTION_HOLD_MENU_SHUTTER_POWER: str = "HOLD_MENU_SHUTTER_POWER"
ACTION_P1_LINE1_MODE_CLEAR: str = "P1_LINE1_MODE_CLEAR"
ACTION_TIER0_VAULT_RESTORE: str = "TIER0_VAULT_RESTORE"
ACTION_DISCONNECT_ADAPTER_CHECK_1V8: str = "DISCONNECT_ADAPTER_CHECK_1V8"

VALID_460800_RECOVERY_ACTIONS: Tuple[str, ...] = (
    ACTION_EJECT_SD_47US_BYPASS,
    ACTION_CREATE_STOP_STAGEB_FLAG,
    ACTION_HOLD_MENU_SHUTTER_POWER,
    ACTION_P1_LINE1_MODE_CLEAR,
    ACTION_TIER0_VAULT_RESTORE,
)

# Pinned FX3 7.02 Donor Relpaths & Digests (Strictly O_RDONLY, 0 raw firmware bytes in JSON)
P155_DONOR_FX3_KEMCO_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0800_appli/setting/kemco.txt"
)
P155_DONOR_FX3_TOMCO_RELPATH: str = (
    "sony-firmware-20261024/stage198-AP-CP-loaders-and-partition-selection/"
    "originals/tomco.txt"
)
P155_DONOR_FX3_INIT_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha7/sbin/init"
)
P155_DONOR_FX3_LIBSENCORE_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so"
)
P155_DONOR_FX3_CPAPP_B_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
)

P155_PINNED_FX3_KEMCO_BYTES: int = 1736
P155_PINNED_FX3_KEMCO_SHA256: str = "555454e8b7db1461d6494e9ca9eb21f00918475af02557bc6ca3cedd309bcaf2"
P155_PINNED_FX3_TOMCO_BYTES: int = 710
P155_PINNED_FX3_TOMCO_SHA256: str = "42f1785422bce152dbb21c4e82f42dd4b053a1729c7694e54b7cc9f118592722"
P155_PINNED_FX3_INIT_BYTES: int = 735
P155_PINNED_FX3_INIT_SHA256: str = "c83de1abeeb779f7473181b51face32ecfedfa3bd5c0fc346ae0c628f1b0ac5e"
P155_PINNED_FX3_LIBSENCORE_BYTES: int = 377328
P155_PINNED_FX3_LIBSENCORE_SHA256: str = "a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410"
P155_PINNED_FX3_CPAPP_B_BYTES: int = 15980568
P155_PINNED_FX3_CPAPP_B_HDR4K_SHA256: str = "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d"

# Status & Fail-Closed Error Codes
P155_STATUS_VERIFIED_SUITE: str = "VERIFIED_UART_460800_POST_TRIAGE_AND_ISP_GATE"
P155_STATUS_FAIL_SUITE: str = "FAIL_UART_460800_POST_TRIAGE_AND_ISP_GATE"
P155_STATUS_VERIFIED_PILLAR_A: str = "VERIFIED_PASSIVE_460800_6STAGE_BOOT_TRIAGE"
P155_STATUS_REJECTED_PILLAR_A: str = "REJECTED_PASSIVE_460800_6STAGE_BOOT_TRIAGE"
P155_STATUS_VERIFIED_PILLAR_B: str = "VERIFIED_1V8_AND_MULTI_USB_VMC_BNCM1_FIREWALL"
P155_STATUS_REJECTED_PILLAR_B: str = "REJECTED_1V8_AND_MULTI_USB_VMC_BNCM1_FIREWALL"
P155_STATUS_VERIFIED_PILLAR_C: str = "VERIFIED_LAST_RESORT_1V8_ISP_CHECKLIST_READONLY"
P155_STATUS_REJECTED_PILLAR_C: str = "REJECTED_LAST_RESORT_1V8_ISP_CHECKLIST"

BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD: str = "BLOCKED_OVERVOLTAGE_3V3_5V0_CXD90057_1V8_PAD_HAZARD"
BLOCKED_UNDERVOLTAGE_1V8_TAP: str = "BLOCKED_UNDERVOLTAGE_BELOW_1V65_UART_TAP"
BLOCKED_PHYSICAL_TX_LINE_CONNECTED: str = "BLOCKED_PHYSICAL_TX_LINE_CONNECTED_RX_ONLY_REQUIRED"
BLOCKED_ACTIVE_TX_BYTES_ATTEMPTED: str = "BLOCKED_ACTIVE_TX_BYTES_ATTEMPTED_ZERO_REQUIRED"
BLOCKED_VMC_BNCM1_LTC_CONTENTION: str = "BLOCKED_VMC_BNCM1_680KOHM_LTC_H0_CONTENTION"
BLOCKED_MULTI_USB_BUS_CONTENTION: str = "BLOCKED_MULTI_USB_CONCURRENT_PORT_CONTENTION"
BLOCKED_UNSUPPORTED_460800_8N1_FRAMING: str = "BLOCKED_UNSUPPORTED_460800_8N1_UART_FRAMING"
BLOCKED_P1_KEMCO_MISSING_460800_CONSOLE: str = "BLOCKED_P1_KEMCO_MISSING_TTYAMA0_460800N8"

BLOCKED_ISP_1V8_RAIL_OVERVOLTAGE: str = "BLOCKED_ISP_3V3_5V0_VCCQ_OR_SPINOR_OVERVOLTAGE"
BLOCKED_ISP_BUS_CONTENTION_SOC_ACTIVE: str = "BLOCKED_ISP_SOC_RESET_NOT_HELD_OR_POWER_ATTACHED"
BLOCKED_ISP_FLYWIRE_TOO_LONG: str = "BLOCKED_ISP_FLYWIRE_EXCEEDS_10CM"
BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD: str = "BLOCKED_EXT_CSD_162_177_179_INTEGRITY_OR_OTP_WRITE"
BLOCKED_CROSS_CAMERA_CID_VAULT_MISMATCH: str = "BLOCKED_CROSS_CAMERA_CID_PNFLASHA_MTD0RO_PAIRING"
BLOCKED_PERSISTENT_ISP_WRITE_LOCKED: str = "BLOCKED_PERSISTENT_EMMC_AND_SPI_NOR_WRITES_LOCKED_FALSE"
ERR_UNKNOWN_OR_EMPTY_UART_LOG: str = "ERR_UNKNOWN_OR_EMPTY_TTYAMA0_BOOT_LOG"

P155_PILLAR_A_SCENARIO_IDS: Tuple[str, ...] = (
    "T01_HEALTHY_STAGE5_APPFW_BIG6_READY",
    "T02_STAGE4_MANIFEST_OR_SD_OVERLAY_EJECT_47US_BYPASS",
    "T03_STAGE5_APPFW_CRASH_LOOP_CREATE_STOP_STAGEB_FLAG",
    "T04_STAGE4_INIT2_EARLY_STALL_HOLD_MENU_SHUTTER_POWER",
    "T05_STAGE3_P1_LINE1_MODE_LATCH_P1_MODE_CLEAR",
    "T06_STAGE3_EXT2_EROFS_SPACC_PANIC_TIER0_VAULT_RESTORE",
    "T07_STAGE0_1_BOOTROM_BL31_HANG_TIER0_VAULT_RESTORE",
    "T08_FRAMING_GARBLE_OR_EMPTY_LOG_FAIL_CLOSED",
)

P155_PILLAR_B_SCENARIO_IDS: Tuple[str, ...] = (
    "E01_SAFE_1V8_RX_ONLY_460800_8N1_ISOLATED",
    "E02_BLOCKED_3V3_UART_ADAPTER_1V8_PAD_HAZARD",
    "E03_BLOCKED_5V0_TTL_ADAPTER_1V8_PAD_HAZARD",
    "E04_BLOCKED_PHYSICAL_TX_CONNECTED_OR_TX_ATTEMPT",
    "E05_BLOCKED_VMC_BNCM1_680KOHM_LTC_CONTENTION",
    "E06_BLOCKED_MULTI_USB_CONCURRENT_BUS_CONTENTION",
)

P155_PILLAR_C_SCENARIO_IDS: Tuple[str, ...] = (
    "I01_VALID_1V8_ISP_CID_PNFLASHA_MTD0RO_READONLY",
    "I02_BLOCKED_3V3_VCCQ_OR_SPINOR_OVERVOLTAGE",
    "I03_BLOCKED_SOC_NOT_ISOLATED_OR_BATTERY_ATTACHED",
    "I04_BLOCKED_EXT_CSD_179_177_162_CORRUPT_OR_OTP_MUTATION",
    "I05_BLOCKED_CROSS_CAMERA_CID_PNFLASHA_MTD0RO_MISMATCH",
    "I06_BLOCKED_PERSISTENT_EMMC_OR_SPI_NOR_WRITE_UNLOCK",
)

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")

_STAGE_MATCH_PATTERNS: Tuple[Tuple[str, Tuple[str, ...]], ...] = (
    (
        "STAGE_0_BOOTROM_SPI_NOR_IPL",
        ("STAGE_0_BOOTROM_SPI_NOR_IPL", "CXD90057", "BootROM", "SPI-NOR", "IPL", "EXBL"),
    ),
    (
        "STAGE_1_BLOADER_BL31_ATF",
        ("STAGE_1_BLOADER_BL31_ATF", "BLoader", "loader_nor", "BL31", "ATF", "OP-TEE", "[TOMCO]"),
    ),
    (
        "STAGE_2_LINUX_4_9_337_SCEL_KERNEL",
        ("STAGE_2_LINUX_4_9_337_SCEL_KERNEL", "4.9.337-scel+", "ttyAMA0", "460800", "Booting Linux"),
    ),
    (
        "STAGE_3_SPACC_CNFLASHA15_EXT2_USR",
        ("STAGE_3_SPACC_CNFLASHA15_EXT2_USR", "cnflasha15", "pnflasha15", "crypt-emmc", "spacc", "EXT2-fs", "/usr"),
    ),
    (
        "STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER",
        ("STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER", "im.elf", "/sbin/init2", "STOP_STAGEB", "47us", "sd_escape"),
    ),
    (
        "STAGE_5_STAGEB_APPFW_BIG6_READY",
        ("STAGE_5_STAGEB_APPFW_BIG6_READY", "appFw.so", "BIG6_READY", "Stage-B ready", "ProCam"),
    ),
)


# ---------------------------------------------------------------------------
# Structured Dataclasses (Zero Raw Firmware Bytes in Serialized Outputs)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class UartIspDonorArtifactDigest:
    artifact_id: str
    relpath: str
    source_mode: str
    access_mode: str
    byte_length: int
    sha256_digest: str
    header_4k_sha256: Optional[str]
    verified_tokens: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class UartIspDonorSnapshot:
    verification_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    stock_kemco_uart_cfg: Optional[int]
    stock_kemco_console: Optional[str]
    tomco_uart_baudrate: Optional[int]
    tomco_console_enable: Optional[str]
    p1_diagnostic_kemco_valid: bool
    artifacts: Tuple[UartIspDonorArtifactDigest, ...]
    all_passed: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Uart460800ElectricalConfig:
    io_voltage_v: float = UART_1V8_NOMINAL_V
    baud_rate: int = UART_460800_BAUD
    framing: str = UART_460800_FRAMING
    tx_line_connected: bool = False
    tx_bytes_attempted: int = 0
    vmc_bncm1_ltc_attached: bool = False
    pin6_id_resistor_ohm: Optional[float] = None
    multi_usb_ports_active: Tuple[str, ...] = ("ttyAMA0_RX_1V8",)


@dataclass(frozen=True)
class Uart460800FirewallDecision:
    safe: bool
    status: str
    blocked_codes: Tuple[str, ...]
    io_voltage_v: float
    baud_rate: int
    framing: str
    tx_line_connected: bool
    passive_tx_bytes_emitted: int
    tx_bytes_attempted: int
    vmc_bncm1_ltc_attached: bool
    pin6_id_resistor_ohm: Optional[float]
    multi_usb_ports_active: Tuple[str, ...]
    recommended_action: str
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BootStage6Trace:
    stages_observed: Tuple[str, ...]
    highest_stage_reached: Optional[str]
    highest_stage_index: int
    stage_transitions: Tuple[str, ...]
    stage_line_numbers: Dict[str, int]
    valid_monotonic_progression: bool
    framing_noise_ratio: float


@dataclass(frozen=True)
class Uart460800TriageResult:
    passed: bool
    classified: bool
    safe_to_operate: bool
    scenario_id: str
    fault_detected: bool
    fault_category: str
    highest_stage_reached: Optional[str]
    stages_observed: Tuple[str, ...]
    stage_transitions: Tuple[str, ...]
    valid_monotonic_progression: bool
    recovery_action: str
    recovery_tier: str
    prescribed_steps: Tuple[str, ...]
    firewall_decision: Uart460800FirewallDecision
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    log_sha256: str
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarATriageScenarioOutcome:
    scenario_id: str
    passed: bool
    expected_action: str
    observed_action: str
    highest_stage_reached: Optional[str]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PillarATriage8ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[PillarATriageScenarioOutcome, ...]
    passive_tx_bytes_emitted: int = PASSIVE_TX_BYTES_EMITTED
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarBFirewallScenarioOutcome:
    scenario_id: str
    passed: bool
    expected_safe: bool
    observed_safe: bool
    observed_codes: Tuple[str, ...]
    passive_tx_bytes_emitted: int


@dataclass(frozen=True)
class PillarBFirewall6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[PillarBFirewallScenarioOutcome, ...]
    passive_tx_bytes_emitted: int = PASSIVE_TX_BYTES_EMITTED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class IspBenchChecklistSpec:
    vccq_voltage_v: float
    spi_nor_voltage_v: float
    soc_reset_held_low: bool
    main_battery_and_usb_disconnected: bool
    flywire_length_cm: float
    ext_csd_bytes: bytes
    cid_sha256: str
    body_serial_sha256: str
    vault_cid_sha256: str
    vault_body_serial_sha256: str
    pnflasha_bundle_sha256: str
    pnflasha_readback_sha256: str
    mtd0ro_sha256: str
    mtd0ro_readback_sha256: str
    otp_162_write_requested: bool = False
    request_persistent_emmc_writes: bool = False
    request_spi_nor_write: bool = False


@dataclass(frozen=True)
class IspChecklistVerificationReport:
    passed: bool
    theoretical_bench_repair_eligible: bool
    ext_csd_179_part_config_hex: str
    boot_partition_enable: int
    boot_ack: int
    partition_access: int
    ext_csd_177_boot_bus_hex: str
    ext_csd_162_rst_n_hex: str
    cid_vault_paired: bool
    pnflasha_two_pass_verified: bool
    mtd0ro_two_pass_verified: bool
    electrical_isolation_ok: bool
    blocked_codes: Tuple[str, ...]
    otp_fuse_touches: int = OTP_FUSE_TOUCHES
    otp_fuse_writes: int = OTP_FUSE_WRITES
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    persistent_write_release: bool = PERSISTENT_WRITE_RELEASE
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarCIspScenarioOutcome:
    scenario_id: str
    passed: bool
    theoretical_bench_repair_eligible: bool
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PillarCIsp6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[PillarCIspScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwUart460800IspSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    otp_fuse_touches: int
    otp_fuse_writes: int
    raw_firmware_bytes_leaked: int
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    read_only_donor_access: bool
    donor_snapshot: UartIspDonorSnapshot
    pillar_a_triage_8_scenarios: PillarATriage8ScenarioSuiteResult
    pillar_b_firewall_6_scenarios: PillarBFirewall6ScenarioSuiteResult
    pillar_c_isp_6_scenarios: PillarCIsp6ScenarioSuiteResult
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Read-Only Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _read_regular_file_readonly(
    path: Path, max_bytes: int, bounded_head_bytes: Optional[int] = None
) -> Tuple[int, bytes]:
    """Open regular file strictly with O_RDONLY | O_NOFOLLOW | O_NONBLOCK."""
    checked = local_path(path, allow_donor_roots=True)
    fd = os.open(checked, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode) or st.st_nlink != 1:
            raise ValueError(f"Non-regular or multi-link donor rejected: {checked}")
        if st.st_size < 0 or st.st_size > max_bytes:
            raise ValueError(f"Donor size out of bounds ({st.st_size} > {max_bytes}): {checked}")
        to_read = st.st_size if bounded_head_bytes is None else min(st.st_size, bounded_head_bytes)
        chunks: List[bytes] = []
        remaining = to_read
        while remaining > 0:
            block = os.read(fd, remaining)
            if not block:
                break
            chunks.append(block)
            remaining -= len(block)
        return int(st.st_size), b"".join(chunks)
    finally:
        os.close(fd)


def validate_p1_diagnostic_kemco_profile(kemco_text: str) -> Tuple[bool, List[str]]:
    """Validate an FX3 p1:/boot/kemco.txt UART 460800n8 diagnostic profile."""
    errs: List[str] = []
    if "cfg.uart=1" not in kemco_text:
        errs.append(f"{BLOCKED_P1_KEMCO_MISSING_460800_CONSOLE}:missing_cfg_uart_1")
    if "cfg.uart=9" in kemco_text:
        errs.append(f"{BLOCKED_P1_KEMCO_MISSING_460800_CONSOLE}:forbidden_fx6_cfg_uart_9")
    if UART_460800_CONSOLE_ARG not in kemco_text:
        errs.append(f"{BLOCKED_P1_KEMCO_MISSING_460800_CONSOLE}:missing_ttyAMA0_460800n8")
    if "console=ttynull" in kemco_text:
        errs.append(f"{BLOCKED_P1_KEMCO_MISSING_460800_CONSOLE}:ttynull_silences_console")
    return len(errs) == 0, errs


def build_synthetic_p1_diagnostic_kemco_profile() -> str:
    """Build clean-room FX3 7.02 p1:/boot/kemco.txt diagnostic UART profile."""
    return (
        "kemco\n"
        "init=/sbin/init\n"
        "cfg.uart=1\n"
        "console=ttyAMA0,460800n8\n"
        "wdt.timeout=500\n"
        "wdt.mode=1\n"
        "root=/dev/ram0 rootfstype=ext2\n"
    )


def inspect_uart_460800_and_isp_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> UartIspDonorSnapshot:
    """Inspect real FX3 7.02 UART/boot donors via O_RDONLY, or clean-room fallback."""
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    p1_diag_ok, _ = validate_p1_diagnostic_kemco_profile(build_synthetic_p1_diagnostic_kemco_profile())
    if clean_room:
        synthetic_digests = (
            UartIspDonorArtifactDigest(
                "fx3_kemco_txt",
                P155_DONOR_FX3_KEMCO_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P155_PINNED_FX3_KEMCO_BYTES,
                P155_PINNED_FX3_KEMCO_SHA256,
                None,
                ("cfg.uart=1", "console=ttynull0", "wdt.timeout=500"),
                True,
            ),
            UartIspDonorArtifactDigest(
                "fx3_tomco_txt",
                P155_DONOR_FX3_TOMCO_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P155_PINNED_FX3_TOMCO_BYTES,
                P155_PINNED_FX3_TOMCO_SHA256,
                None,
                ("[TOMCO]", "uart_baudrate=460800", "console_enable=N"),
                True,
            ),
            UartIspDonorArtifactDigest(
                "fx3_sbin_init",
                P155_DONOR_FX3_INIT_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P155_PINNED_FX3_INIT_BYTES,
                P155_PINNED_FX3_INIT_SHA256,
                None,
                ("/sbin/initrc", "insmod_drv1", "setup_nflash", "/sbin/init2"),
                True,
            ),
            UartIspDonorArtifactDigest(
                "fx3_libsencore_so",
                P155_DONOR_FX3_LIBSENCORE_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P155_PINNED_FX3_LIBSENCORE_BYTES,
                P155_PINNED_FX3_LIBSENCORE_SHA256,
                None,
                ("ELF64_AArch64", "SET_SEL_UART_LANC", "SET_GRIP_UART_SEL"),
                True,
            ),
            UartIspDonorArtifactDigest(
                "fx3_cpapp_b_bin",
                P155_DONOR_FX3_CPAPP_B_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P155_PINNED_FX3_CPAPP_B_BYTES,
                P155_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                P155_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                ("ARMv7R_0x0010800C",),
                True,
            ),
        )
        return UartIspDonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            stock_kemco_uart_cfg=1,
            stock_kemco_console="ttynull0",
            tomco_uart_baudrate=UART_460800_BAUD,
            tomco_console_enable="N",
            p1_diagnostic_kemco_valid=p1_diag_ok,
            artifacts=synthetic_digests,
            all_passed=p1_diag_ok,
            errors=(),
        )

    relpaths = (
        P155_DONOR_FX3_KEMCO_RELPATH,
        P155_DONOR_FX3_TOMCO_RELPATH,
        P155_DONOR_FX3_INIT_RELPATH,
        P155_DONOR_FX3_LIBSENCORE_RELPATH,
        P155_DONOR_FX3_CPAPP_B_RELPATH,
    )
    resolved = [resolve_donor_path(rel, require_file=True) for rel in relpaths]
    if any(p is None or (not p.is_file()) for p in resolved):
        return inspect_uart_460800_and_isp_donors_readonly(force_clean_room=True)

    errors: List[str] = []
    artifacts: List[UartIspDonorArtifactDigest] = []

    # 1. kemco.txt
    sz_k, data_k = _read_regular_file_readonly(resolved[0], 1024 * 1024)
    sha_k = sha256(data_k).hexdigest()
    txt_k = data_k.decode("utf-8", errors="replace")
    uart_m = re.search(r"\bcfg\.uart=(\d+)\b", txt_k)
    cons_m = re.search(r"\bconsole=([^\s]+)", txt_k)
    uart_cfg = int(uart_m.group(1)) if uart_m else None
    stock_console = cons_m.group(1) if cons_m else None
    k_tokens = tuple(t for t in ("cfg.uart=1", "console=ttynull0", "wdt.timeout=500") if t in txt_k)
    k_ok = (sz_k == P155_PINNED_FX3_KEMCO_BYTES) and (sha_k == P155_PINNED_FX3_KEMCO_SHA256) and (len(k_tokens) == 3)
    if not k_ok:
        errors.append("DONOR_MISMATCH:fx3_kemco_txt")
    artifacts.append(
        UartIspDonorArtifactDigest(
            "fx3_kemco_txt",
            P155_DONOR_FX3_KEMCO_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY",
            sz_k,
            sha_k,
            None,
            k_tokens,
            k_ok,
        )
    )

    # 2. tomco.txt
    sz_t, data_t = _read_regular_file_readonly(resolved[1], 1024 * 1024)
    sha_t = sha256(data_t).hexdigest()
    txt_t = data_t.decode("utf-8", errors="replace")
    baud_m = re.search(r"\buart_baudrate=(\d+)\b", txt_t)
    c_en_m = re.search(r"\bconsole_enable=([YN])\b", txt_t)
    t_baud = int(baud_m.group(1)) if baud_m else None
    t_cen = c_en_m.group(1) if c_en_m else None
    t_tokens = tuple(t for t in ("[TOMCO]", "uart_baudrate=460800", "console_enable=N") if t in txt_t)
    t_ok = (sz_t == P155_PINNED_FX3_TOMCO_BYTES) and (sha_t == P155_PINNED_FX3_TOMCO_SHA256) and (len(t_tokens) == 3)
    if not t_ok:
        errors.append("DONOR_MISMATCH:fx3_tomco_txt")
    artifacts.append(
        UartIspDonorArtifactDigest(
            "fx3_tomco_txt",
            P155_DONOR_FX3_TOMCO_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY",
            sz_t,
            sha_t,
            None,
            t_tokens,
            t_ok,
        )
    )

    # 3. /sbin/init
    sz_i, data_i = _read_regular_file_readonly(resolved[2], 1024 * 1024)
    sha_i = sha256(data_i).hexdigest()
    txt_i = data_i.decode("utf-8", errors="replace")
    i_tokens = tuple(t for t in ("/sbin/initrc", "insmod_drv1", "setup_nflash", "/sbin/init2") if t in txt_i)
    i_ok = (sz_i == P155_PINNED_FX3_INIT_BYTES) and (sha_i == P155_PINNED_FX3_INIT_SHA256) and (len(i_tokens) == 4)
    if not i_ok:
        errors.append("DONOR_MISMATCH:fx3_sbin_init")
    artifacts.append(
        UartIspDonorArtifactDigest(
            "fx3_sbin_init",
            P155_DONOR_FX3_INIT_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY",
            sz_i,
            sha_i,
            None,
            i_tokens,
            i_ok,
        )
    )

    # 4. libsencore.so
    sz_s, data_s = _read_regular_file_readonly(resolved[3], 4 * 1024 * 1024)
    sha_s = sha256(data_s).hexdigest()
    is_a64 = len(data_s) >= 20 and data_s[:4] == b"\x7fELF" and struct.unpack_from("<H", data_s, 18)[0] == 183
    s_tokens: List[str] = ["ELF64_AArch64"] if is_a64 else []
    for sym in ("SET_SEL_UART_LANC", "SET_GRIP_UART_SEL"):
        if sym.encode("ascii") in data_s:
            s_tokens.append(sym)
    s_ok = (sz_s == P155_PINNED_FX3_LIBSENCORE_BYTES) and (sha_s == P155_PINNED_FX3_LIBSENCORE_SHA256) and (len(s_tokens) == 3)
    if not s_ok:
        errors.append("DONOR_MISMATCH:fx3_libsencore_so")
    artifacts.append(
        UartIspDonorArtifactDigest(
            "fx3_libsencore_so",
            P155_DONOR_FX3_LIBSENCORE_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY",
            sz_s,
            sha_s,
            None,
            tuple(s_tokens),
            s_ok,
        )
    )

    # 5. cpapp-b.bin (bounded 4 KiB header read)
    sz_cp, hdr_cp = _read_regular_file_readonly(resolved[4], 64 * 1024 * 1024, bounded_head_bytes=4096)
    sha_cp_hdr = sha256(hdr_cp).hexdigest()
    cp_words = struct.unpack_from("<4I", hdr_cp, 0) if len(hdr_cp) >= 16 else ()
    cp_ok = (
        sz_cp == P155_PINNED_FX3_CPAPP_B_BYTES
        and sha_cp_hdr == P155_PINNED_FX3_CPAPP_B_HDR4K_SHA256
        and len(cp_words) == 4
        and cp_words[3] == 0x0010800C
    )
    if not cp_ok:
        errors.append("DONOR_MISMATCH:fx3_cpapp_b_bin")
    artifacts.append(
        UartIspDonorArtifactDigest(
            "fx3_cpapp_b_bin",
            P155_DONOR_FX3_CPAPP_B_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY_BOUNDED_4K",
            sz_cp,
            sha_cp_hdr,
            sha_cp_hdr,
            ("ARMv7R_0x0010800C",) if cp_ok else (),
            cp_ok,
        )
    )

    all_ok = (len(errors) == 0) and p1_diag_ok and all(a.passed for a in artifacts)
    return UartIspDonorSnapshot(
        verification_mode="LOCAL_DONOR_RDONLY",
        access_mode="O_RDONLY_NOFOLLOW_NONBLOCK",
        donor_files_inspected=len(artifacts),
        raw_firmware_bytes_leaked=0,
        stock_kemco_uart_cfg=uart_cfg,
        stock_kemco_console=stock_console,
        tomco_uart_baudrate=t_baud,
        tomco_console_enable=t_cen,
        p1_diagnostic_kemco_valid=p1_diag_ok,
        artifacts=tuple(artifacts),
        all_passed=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar B — 1.8V Logic-Level & Multi-USB VMC-BNCM1 Contention Firewall
# ---------------------------------------------------------------------------


def audit_1v8_uart_and_multi_usb_firewall(
    cfg: Uart460800ElectricalConfig,
    *,
    active_tx_payload: bytes = b"",
) -> Uart460800FirewallDecision:
    """Enforce 1.8V logic level, physical TX-disconnected RX-only discipline, and VMC-BNCM1/Multi-USB isolation."""
    blocked: List[str] = []
    errors: List[str] = []
    tx_attempted = max(0, int(cfg.tx_bytes_attempted)) + len(active_tx_payload)

    # 1. 1.8V Pad Over-Voltage / Under-Voltage Firewall
    if cfg.io_voltage_v > UART_1V8_MAX_SAFE_V:
        blocked.append(BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD)
        errors.append(
            f"IO voltage {cfg.io_voltage_v:.2f}V exceeds CXD90057 1.8V pad ceiling ({UART_1V8_MAX_SAFE_V:.2f}V)."
        )
    elif cfg.io_voltage_v < UART_1V8_MIN_SAFE_V:
        blocked.append(BLOCKED_UNDERVOLTAGE_1V8_TAP)
        errors.append(
            f"IO voltage {cfg.io_voltage_v:.2f}V below 1.8V RX threshold ({UART_1V8_MIN_SAFE_V:.2f}V)."
        )

    # 2. Physical TX-Disconnected RX-Only Discipline (passive_tx_bytes_emitted == 0)
    if cfg.tx_line_connected:
        blocked.append(BLOCKED_PHYSICAL_TX_LINE_CONNECTED)
        errors.append("Physical TX line must remain disconnected during passive H0 ttyAMA0 diagnostics.")
    if tx_attempted > 0:
        blocked.append(BLOCKED_ACTIVE_TX_BYTES_ATTEMPTED)
        errors.append(f"Active TX injection attempt rejected ({tx_attempted} bytes attempted; 0 allowed).")

    # 3. VMC-BNCM1 (680 kOhm LTC) / LANC Contention Firewall
    id_ohm = cfg.pin6_id_resistor_ohm
    is_ltc_resistor = id_ohm is not None and (VMC_BNCM1_LTC_OHM_MIN <= id_ohm <= VMC_BNCM1_LTC_OHM_MAX)
    is_lanc_resistor = id_ohm is not None and (LANC_ID_OHM_MIN <= id_ohm <= LANC_ID_OHM_MAX)
    if cfg.vmc_bncm1_ltc_attached or is_ltc_resistor or is_lanc_resistor:
        blocked.append(BLOCKED_VMC_BNCM1_LTC_CONTENTION)
        errors.append("Simultaneous VMC-BNCM1 (680 kOhm LTC) or LANC attachment blocked during H0 boot diagnostics.")

    # 4. Multi-USB Concurrent Bus Contention Firewall
    ports = tuple(p.strip() for p in cfg.multi_usb_ports_active if p.strip())
    conflicting_usb = any(
        any(tok in port.upper() for tok in ("MSC_054C_0DA1", "SERVICE_054C_0336", "VMC_BNCM1", "USB_C_DUAL_HOST"))
        for port in ports
    )
    if conflicting_usb or len(ports) > 1 and "ttyAMA0_RX_1V8" in ports and any(p != "ttyAMA0_RX_1V8" for p in ports):
        # Allow pure host ground/power-off reference markers only; block competing active USB/Multi-Port interfaces
        competing = [p for p in ports if p != "ttyAMA0_RX_1V8"]
        if competing:
            blocked.append(BLOCKED_MULTI_USB_BUS_CONTENTION)
            errors.append(f"Competing Multi-USB / Multi-Port ports active during H0 UART capture: {competing}")

    # 5. Baud / Framing Validation (460800 8N1)
    if cfg.baud_rate != UART_460800_BAUD or cfg.framing.upper() != UART_460800_FRAMING:
        blocked.append(BLOCKED_UNSUPPORTED_460800_8N1_FRAMING)
        errors.append(
            f"Expected {UART_460800_BAUD} {UART_460800_FRAMING} for ttyAMA0 diagnostics (got {cfg.baud_rate} {cfg.framing})."
        )

    dedup_blocked = tuple(dict.fromkeys(blocked))
    safe = len(dedup_blocked) == 0
    status = "VERIFIED_1V8_RX_ONLY_460800_FIREWALL" if safe else dedup_blocked[0]
    rec_action = ACTION_NONE_HEALTHY if safe else ACTION_DISCONNECT_ADAPTER_CHECK_1V8
    return Uart460800FirewallDecision(
        safe=safe,
        status=status,
        blocked_codes=dedup_blocked,
        io_voltage_v=cfg.io_voltage_v,
        baud_rate=cfg.baud_rate,
        framing=cfg.framing,
        tx_line_connected=cfg.tx_line_connected,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        tx_bytes_attempted=tx_attempted,
        vmc_bncm1_ltc_attached=cfg.vmc_bncm1_ltc_attached,
        pin6_id_resistor_ohm=cfg.pin6_id_resistor_ohm,
        multi_usb_ports_active=ports,
        recommended_action=rec_action,
        errors=tuple(errors),
    )


def run_pillar_b_firewall_6_scenario_suite() -> PillarBFirewall6ScenarioSuiteResult:
    """Execute 6-scenario 1.8V electrical & Multi-USB VMC-BNCM1 contention firewall suite."""
    cases = (
        (
            P155_PILLAR_B_SCENARIO_IDS[0],
            True,
            None,
            Uart460800ElectricalConfig(),
            b"",
        ),
        (
            P155_PILLAR_B_SCENARIO_IDS[1],
            False,
            BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD,
            Uart460800ElectricalConfig(io_voltage_v=UART_OVERVOLTAGE_3V3_V),
            b"",
        ),
        (
            P155_PILLAR_B_SCENARIO_IDS[2],
            False,
            BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD,
            Uart460800ElectricalConfig(io_voltage_v=UART_OVERVOLTAGE_5V0_V),
            b"",
        ),
        (
            P155_PILLAR_B_SCENARIO_IDS[3],
            False,
            BLOCKED_PHYSICAL_TX_LINE_CONNECTED,
            Uart460800ElectricalConfig(tx_line_connected=True, tx_bytes_attempted=4),
            b"AT\r\n",
        ),
        (
            P155_PILLAR_B_SCENARIO_IDS[4],
            False,
            BLOCKED_VMC_BNCM1_LTC_CONTENTION,
            Uart460800ElectricalConfig(vmc_bncm1_ltc_attached=True, pin6_id_resistor_ohm=680_000.0),
            b"",
        ),
        (
            P155_PILLAR_B_SCENARIO_IDS[5],
            False,
            BLOCKED_MULTI_USB_BUS_CONTENTION,
            Uart460800ElectricalConfig(multi_usb_ports_active=("ttyAMA0_RX_1V8", "MSC_054C_0DA1")),
            b"",
        ),
    )

    outcomes: List[PillarBFirewallScenarioOutcome] = []
    for sid, exp_safe, exp_code, cfg, payload in cases:
        dec = audit_1v8_uart_and_multi_usb_firewall(cfg, active_tx_payload=payload)
        ok = (
            dec.safe == exp_safe
            and dec.passive_tx_bytes_emitted == 0
            and (exp_code is None or exp_code in dec.blocked_codes)
        )
        outcomes.append(
            PillarBFirewallScenarioOutcome(
                scenario_id=sid,
                passed=ok,
                expected_safe=exp_safe,
                observed_safe=dec.safe,
                observed_codes=dec.blocked_codes,
                passive_tx_bytes_emitted=dec.passive_tx_bytes_emitted,
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(P155_PILLAR_B_SCENARIO_IDS)
    return PillarBFirewall6ScenarioSuiteResult(
        passed=all_ok,
        status=P155_STATUS_VERIFIED_PILLAR_B if all_ok else P155_STATUS_REJECTED_PILLAR_B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(P155_PILLAR_B_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Pillar A — Passive 460800 8N1 6-Stage Boot-Stage Decoder & Triage Engine
# ---------------------------------------------------------------------------


def _compute_framing_noise_ratio(log_text: str) -> float:
    if not log_text:
        return 0.0
    total = len(log_text)
    bad = sum(1 for ch in log_text if ch == "\ufffd" or (ord(ch) < 32 and ch not in ("\n", "\r", "\t")))
    return round(bad / max(total, 1), 4)


def parse_ttyama0_460800_boot_stages(log_text: str) -> BootStage6Trace:
    """Parse captured/live FX3 ttyAMA0 460800n8 boot log across STAGE_0..STAGE_5."""
    observed: List[str] = []
    line_map: Dict[str, int] = {}
    last_idx = -1
    monotonic = True
    wdt_seen = False

    for line_no, raw_line in enumerate(log_text.splitlines(), start=1):
        line_lower = raw_line.lower()
        if "wdt reset" in line_lower or "watchdog reset" in line_lower:
            wdt_seen = True
        matched_stage: Optional[str] = None
        for stage, _patterns in _STAGE_MATCH_PATTERNS:
            if stage.lower() in line_lower:
                matched_stage = stage
                break
        if matched_stage is None:
            for stage, patterns in _STAGE_MATCH_PATTERNS:
                if any(pat.lower() in line_lower for pat in patterns):
                    matched_stage = stage
                    break
        if matched_stage is not None:
            idx = UART_460800_STAGE_INDEX_MAP[matched_stage]
            if matched_stage not in line_map:
                observed.append(matched_stage)
                line_map[matched_stage] = line_no
            if idx < last_idx and not wdt_seen:
                monotonic = False
            last_idx = max(last_idx, idx) if not wdt_seen else idx

    ordered = tuple(sorted(observed, key=lambda s: UART_460800_STAGE_INDEX_MAP[s]))
    highest = ordered[-1] if ordered else None
    highest_idx = UART_460800_STAGE_INDEX_MAP[highest] if highest is not None else -1
    transitions = tuple(f"{ordered[i]}->{ordered[i + 1]}" for i in range(len(ordered) - 1))
    noise = _compute_framing_noise_ratio(log_text)
    return BootStage6Trace(
        stages_observed=ordered,
        highest_stage_reached=highest,
        highest_stage_index=highest_idx,
        stage_transitions=transitions,
        stage_line_numbers=line_map,
        valid_monotonic_progression=monotonic,
        framing_noise_ratio=noise,
    )


def triage_ttyama0_460800_boot_log(
    log_text: str,
    *,
    electrical_cfg: Optional[Uart460800ElectricalConfig] = None,
    scenario_id: str = "AD_HOC_TTYAMA0_460800_LOG",
) -> Uart460800TriageResult:
    """Decode 6-stage ttyAMA0 460800n8 log and prescribe lowest-impact recovery action."""
    cfg = electrical_cfg or Uart460800ElectricalConfig()
    fw = audit_1v8_uart_and_multi_usb_firewall(cfg)
    trace = parse_ttyama0_460800_boot_stages(log_text)
    log_digest = sha256(log_text.encode("utf-8", errors="replace")).hexdigest()

    if not fw.safe:
        return Uart460800TriageResult(
            passed=False,
            classified=True,
            safe_to_operate=False,
            scenario_id=scenario_id,
            fault_detected=True,
            fault_category=fw.status,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_action=ACTION_DISCONNECT_ADAPTER_CHECK_1V8,
            recovery_tier="ELECTRICAL_FIREWALL_BLOCK",
            prescribed_steps=(
                "Immediately disconnect UART / VMC-BNCM1 / competing USB cables.",
                "Verify 1.8V logic level (1.65V..1.98V) and physically disconnect TX pin.",
            ),
            firewall_decision=fw,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
            log_sha256=log_digest,
            errors=fw.errors,
        )

    lower = log_text.lower()
    if not log_text.strip() or trace.framing_noise_ratio >= 0.25 or len(trace.stages_observed) == 0:
        return Uart460800TriageResult(
            passed=False,
            classified=False,
            safe_to_operate=True,
            scenario_id=scenario_id,
            fault_detected=True,
            fault_category=ERR_UNKNOWN_OR_EMPTY_UART_LOG,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_action=ACTION_DISCONNECT_ADAPTER_CHECK_1V8,
            recovery_tier="FAIL_CLOSED_NO_GUESS",
            prescribed_steps=(
                "Verify ttyAMA0 460800 8N1 ground continuity and 1.8V RX tap.",
                "Do not guess or trigger persistent writes on garbled/empty logs.",
            ),
            firewall_decision=fw,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
            log_sha256=log_digest,
            errors=(ERR_UNKNOWN_OR_EMPTY_UART_LOG,),
        )

    # Deterministic Fault -> Lowest-Impact Recovery Action Mapping
    # 1. p1 line-1 mode latch / boot counter sticky
    if (
        "p1_line1_mode_latch" in lower
        or "boot_attempts=" in lower
        or "mode=1 sticky" in lower
        or "p1:/boot/kemco.txt line1" in lower
    ):
        action = ACTION_P1_LINE1_MODE_CLEAR
        tier = "TIER_1_P1_MODE_CLEAR"
        fault_cat = "P1_LINE1_MODE_LATCH"
        fault = True
        steps = (
            "Boot stock via SD sentinel or Service USB read-only session.",
            "Clear p1 line-1 mode latch back to stock clear state (0x00) and verify readback SHA-256.",
        )
    # 2. SD-resident Stage-B manifest / 47us escape stall -> Eject SD card for 47us bypass
    elif (
        "47us_bypass_needed" in lower
        or "manifest_sha256_mismatch" in lower
        or "sd_stageb_overlay_stall" in lower
        or "cpio magic mismatch" in lower
    ):
        action = ACTION_EJECT_SD_47US_BYPASS
        tier = "TIER_0_EJECT_SD_47US"
        fault_cat = "STAGE4_SD_OVERLAY_MANIFEST_OR_STALL"
        fault = True
        steps = (
            "Power off camera and eject SD card from Slot A/B.",
            "Cold boot: im.elf / init2 falls through in ~47 us to untouched stock FX3 7.02.",
        )
    # 3. appFw / Stage-5 crash loop -> Create STOP_STAGEB flag on SD card
    elif (
        "appfw" in lower and ("crash" in lower or "segfault" in lower or "loop" in lower or "panic" in lower)
    ) or "stop_stageb_flag_requested" in lower:
        action = ACTION_CREATE_STOP_STAGEB_FLAG
        tier = "TIER_0_SD_FLAG"
        fault_cat = "STAGE5_APPFW_CRASH_LOOP"
        fault = True
        steps = (
            "Create empty STOP_STAGEB sentinel file at SD card root on host.",
            "Insert SD card and cold-boot straight into stock FX3 7.02 (0 eMMC writes).",
        )
    # 4. Stage-4 early init2 GPIO stall -> Hold MENU + SHUTTER + POWER key chord
    elif (
        "init2_early_stall" in lower
        or "gpio_escape_ready" in lower
        or ("init2" in lower and ("hang" in lower or "timeout" in lower))
    ):
        action = ACTION_HOLD_MENU_SHUTTER_POWER
        tier = "TIER_0_HARDWARE_KEY_CHORD"
        fault_cat = "STAGE4_INIT2_HANG_GPIO_ESCAPE"
        fault = True
        steps = (
            "Hold MENU + SHUTTER + POWER simultaneously while cold-booting.",
            "Release after stock Sony splash appears; confirm Stage-B bypassed.",
        )
    # 5. Deep Stage 0..3 BootROM / SPI-NOR / Kernel panic / EROFS / SPACC fatal -> Tier-0 Vault Restore checklist
    elif (
        "kernel panic" in lower
        or "erofs" in lower
        or "ext2-fs error" in lower
        or "spacc_mount_fail" in lower
        or "spi-nor crc fail" in lower
        or "bloader_corrupt" in lower
        or "bootrom_usb_fallback" in lower
        or (trace.highest_stage_index <= 3 and ("panic" in lower or "fatal" in lower or "stall" in lower or "error" in lower))
    ):
        action = ACTION_TIER0_VAULT_RESTORE
        tier = "TIER_4_LAST_RESORT_VAULT_CHECKLIST"
        fault_cat = "STAGE0_3_BOOTCHAIN_OR_EXT2_EROFS_FATAL"
        fault = True
        steps = (
            "Do NOT attempt blind writes; run Pillar C 1.8V ISP & CID-bound Tier-0 vault checklist.",
            "Verify per-camera pnflasha* + /dev/mtd0ro dual-copy SHA-256 before human-approved bench recovery.",
        )
    # 6. Healthy full progression through STAGE_5
    elif trace.highest_stage_reached == "STAGE_5_STAGEB_APPFW_BIG6_READY" and trace.valid_monotonic_progression:
        action = ACTION_NONE_HEALTHY
        tier = "NONE"
        fault_cat = "HEALTHY_STAGE5_BIG6_READY"
        fault = False
        steps = ("No recovery needed; CXD90057 reached STAGE_5_STAGEB_APPFW_BIG6_READY cleanly.",)
    else:
        return Uart460800TriageResult(
            passed=False,
            classified=False,
            safe_to_operate=True,
            scenario_id=scenario_id,
            fault_detected=True,
            fault_category=ERR_UNKNOWN_OR_EMPTY_UART_LOG,
            highest_stage_reached=trace.highest_stage_reached,
            stages_observed=trace.stages_observed,
            stage_transitions=trace.stage_transitions,
            valid_monotonic_progression=trace.valid_monotonic_progression,
            recovery_action=ACTION_TIER0_VAULT_RESTORE,
            recovery_tier="FAIL_CLOSED_INCOMPLETE_BOOT",
            prescribed_steps=("Incomplete boot trace without explicit fault signature; escalate to Tier-0 read-only audit.",),
            firewall_decision=fw,
            passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
            physical_device_writes=PHYSICAL_DEVICE_WRITES,
            persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
            spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
            log_sha256=log_digest,
            errors=(ERR_UNKNOWN_OR_EMPTY_UART_LOG,),
        )

    return Uart460800TriageResult(
        passed=True,
        classified=True,
        safe_to_operate=True,
        scenario_id=scenario_id,
        fault_detected=fault,
        fault_category=fault_cat,
        highest_stage_reached=trace.highest_stage_reached,
        stages_observed=trace.stages_observed,
        stage_transitions=trace.stage_transitions,
        valid_monotonic_progression=trace.valid_monotonic_progression,
        recovery_action=action,
        recovery_tier=tier,
        prescribed_steps=steps,
        firewall_decision=fw,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        log_sha256=log_digest,
        errors=(),
    )


def build_default_8_triage_scenarios() -> Tuple[Tuple[str, str, str, str], ...]:
    """Return 8 deterministic 460800n8 ttyAMA0 boot-stage triage test vectors.

    Tuple: (scenario_id, expected_action, expected_highest_stage_or_empty, log_text)
    """
    hdr = (
        "[0.001] STAGE_0_BOOTROM_SPI_NOR_IPL: CXD90057 BootROM IPL OK\n"
        "[0.045] STAGE_1_BLOADER_BL31_ATF: BLoader + BL31 ATF handoff [TOMCO]\n"
        "[0.210] STAGE_2_LINUX_4_9_337_SCEL_KERNEL: Linux version 4.9.337-scel+ console=ttyAMA0,460800n8\n"
    )
    return (
        (
            P155_PILLAR_A_SCENARIO_IDS[0],
            ACTION_NONE_HEALTHY,
            "STAGE_5_STAGEB_APPFW_BIG6_READY",
            hdr
            + "[0.650] STAGE_3_SPACC_CNFLASHA15_EXT2_USR: spacc cnflasha15 ext2 /usr mounted ro\n"
            + "[0.810] STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER: im.elf /sbin/init2 47us check clear\n"
            + "[1.420] STAGE_5_STAGEB_APPFW_BIG6_READY: appFw.so BIG6_READY\n",
        ),
        (
            P155_PILLAR_A_SCENARIO_IDS[1],
            ACTION_EJECT_SD_47US_BYPASS,
            "STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER",
            hdr
            + "[0.650] STAGE_3_SPACC_CNFLASHA15_EXT2_USR: spacc cnflasha15 ext2 /usr mounted ro\n"
            + "[0.815] STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER: im.elf manifest_sha256_mismatch sd_stageb_overlay_stall\n",
        ),
        (
            P155_PILLAR_A_SCENARIO_IDS[2],
            ACTION_CREATE_STOP_STAGEB_FLAG,
            "STAGE_5_STAGEB_APPFW_BIG6_READY",
            hdr
            + "[0.650] STAGE_3_SPACC_CNFLASHA15_EXT2_USR: spacc cnflasha15 ext2 /usr mounted ro\n"
            + "[0.810] STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER: im.elf /sbin/init2 overlay active\n"
            + "[1.900] STAGE_5_STAGEB_APPFW_BIG6_READY: appFw.so segfault crash loop detected\n",
        ),
        (
            P155_PILLAR_A_SCENARIO_IDS[3],
            ACTION_HOLD_MENU_SHUTTER_POWER,
            "STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER",
            hdr
            + "[0.650] STAGE_3_SPACC_CNFLASHA15_EXT2_USR: spacc cnflasha15 ext2 /usr mounted ro\n"
            + "[0.830] STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER: /sbin/init2 init2_early_stall gpio_escape_ready\n",
        ),
        (
            P155_PILLAR_A_SCENARIO_IDS[4],
            ACTION_P1_LINE1_MODE_CLEAR,
            "STAGE_3_SPACC_CNFLASHA15_EXT2_USR",
            hdr
            + "[0.690] STAGE_3_SPACC_CNFLASHA15_EXT2_USR: p1_line1_mode_latch mode=1 sticky boot_attempts=3\n",
        ),
        (
            P155_PILLAR_A_SCENARIO_IDS[5],
            ACTION_TIER0_VAULT_RESTORE,
            "STAGE_3_SPACC_CNFLASHA15_EXT2_USR",
            hdr
            + "[0.660] STAGE_3_SPACC_CNFLASHA15_EXT2_USR: EXT2-fs error EROFS spacc_mount_fail Kernel panic\n",
        ),
        (
            P155_PILLAR_A_SCENARIO_IDS[6],
            ACTION_TIER0_VAULT_RESTORE,
            "STAGE_1_BLOADER_BL31_ATF",
            "[0.001] STAGE_0_BOOTROM_SPI_NOR_IPL: CXD90057 BootROM IPL\n"
            "[0.045] STAGE_1_BLOADER_BL31_ATF: BLoader spi-nor crc fail bloader_corrupt stall\n",
        ),
        (
            P155_PILLAR_A_SCENARIO_IDS[7],
            ACTION_DISCONNECT_ADAPTER_CHECK_1V8,
            "",
            "\ufffd\ufffd\ufffd\x00\x01\ufffd\ufffd\ufffd",
        ),
    )


def run_pillar_a_triage_8_scenario_suite() -> PillarATriage8ScenarioSuiteResult:
    """Execute the 8-scenario ttyAMA0 460800n8 6-stage triage suite."""
    outcomes: List[PillarATriageScenarioOutcome] = []
    for sid, exp_action, exp_stage, log_text in build_default_8_triage_scenarios():
        res = triage_ttyama0_460800_boot_log(log_text, scenario_id=sid)
        if sid == P155_PILLAR_A_SCENARIO_IDS[7]:
            ok = (not res.passed) and (not res.classified) and res.recovery_action == exp_action
        else:
            ok = (
                res.passed
                and res.classified
                and res.recovery_action == exp_action
                and (res.highest_stage_reached or "") == exp_stage
                and res.passive_tx_bytes_emitted == 0
                and not res.persistent_emmc_writes_authorized
                and not res.spi_nor_write_authorized
            )
        outcomes.append(
            PillarATriageScenarioOutcome(
                scenario_id=sid,
                passed=ok,
                expected_action=exp_action,
                observed_action=res.recovery_action,
                highest_stage_reached=res.highest_stage_reached,
                errors=res.errors,
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(P155_PILLAR_A_SCENARIO_IDS)
    return PillarATriage8ScenarioSuiteResult(
        passed=all_ok,
        status=P155_STATUS_VERIFIED_PILLAR_A if all_ok else P155_STATUS_REJECTED_PILLAR_A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(P155_PILLAR_A_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Pillar C — Last-Resort Off-Chip Hardware ISP Emergency Checklist
# ---------------------------------------------------------------------------


def build_synthetic_isp_ext_csd(
    *,
    part_config: int = FX3_DEFAULT_PART_CONFIG,
    boot_bus_conditions: int = FX3_DEFAULT_BOOT_BUS_CONDITIONS,
    rst_n_function: int = 0x01,
) -> bytes:
    """Build deterministic 512 B JEDEC EXT_CSD register dump for FX3 ISP checklist."""
    buf = bytearray(EMMC_EXT_CSD_BYTES)
    buf[EMMC_EXT_CSD_RST_N_IDX] = rst_n_function & 0xFF
    buf[EMMC_EXT_CSD_BOOT_BUS_COND_IDX] = boot_bus_conditions & 0xFF
    buf[EMMC_EXT_CSD_PART_CONFIG_IDX] = part_config & 0xFF
    buf[192] = 8  # EXT_CSD_REV v1.8 (eMMC 5.1)
    buf[226] = 32  # BOOT_SIZE_MULT = 32 * 128 KiB = 4 MiB
    return bytes(buf)


def build_synthetic_isp_checklist_spec(
    *,
    vccq_voltage_v: float = ISP_VCCQ_NOMINAL_V,
    spi_nor_voltage_v: float = ISP_SPI_NOR_NOMINAL_V,
    soc_reset_held_low: bool = True,
    main_battery_and_usb_disconnected: bool = True,
    flywire_length_cm: float = 6.5,
    part_config: int = FX3_DEFAULT_PART_CONFIG,
    boot_bus_conditions: int = FX3_DEFAULT_BOOT_BUS_CONDITIONS,
    rst_n_function: int = 0x01,
    cross_camera_cid_mismatch: bool = False,
    otp_162_write_requested: bool = False,
    request_persistent_emmc_writes: bool = False,
    request_spi_nor_write: bool = False,
) -> IspBenchChecklistSpec:
    cid_a = sha256(b"fx3-camera-emmc-cid-A").hexdigest()
    cid_b = sha256(b"fx3-camera-emmc-cid-B").hexdigest()
    body_a = sha256(b"fx3-camera-body-serial-A").hexdigest()
    pn_sha = sha256(b"fx3-pnflasha-isp-vault-A").hexdigest()
    nor_sha = sha256(b"fx3-mtd0ro-spi-nor-vault-A").hexdigest()
    return IspBenchChecklistSpec(
        vccq_voltage_v=vccq_voltage_v,
        spi_nor_voltage_v=spi_nor_voltage_v,
        soc_reset_held_low=soc_reset_held_low,
        main_battery_and_usb_disconnected=main_battery_and_usb_disconnected,
        flywire_length_cm=flywire_length_cm,
        ext_csd_bytes=build_synthetic_isp_ext_csd(
            part_config=part_config,
            boot_bus_conditions=boot_bus_conditions,
            rst_n_function=rst_n_function,
        ),
        cid_sha256=cid_a,
        body_serial_sha256=body_a,
        vault_cid_sha256=cid_b if cross_camera_cid_mismatch else cid_a,
        vault_body_serial_sha256=body_a,
        pnflasha_bundle_sha256=pn_sha,
        pnflasha_readback_sha256=pn_sha,
        mtd0ro_sha256=nor_sha,
        mtd0ro_readback_sha256=nor_sha,
        otp_162_write_requested=otp_162_write_requested,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        request_spi_nor_write=request_spi_nor_write,
    )


def verify_last_resort_isp_checklist(spec: IspBenchChecklistSpec) -> IspChecklistVerificationReport:
    """Validate 1.8V VCCQ eMMC + 1.8V SPI-NOR ISP electrical isolation, EXT_CSD[179/177/162], and CID-bound vault pairing."""
    blocked: List[str] = []
    errors: List[str] = []

    # 1. Hard-locked write authorization guard
    if spec.request_persistent_emmc_writes or spec.request_spi_nor_write:
        blocked.append(BLOCKED_PERSISTENT_ISP_WRITE_LOCKED)
        errors.append("Persistent eMMC and SPI-NOR writes are hard-locked False in offline verification.")

    # 2. 1.8V VCCQ eMMC & 1.8V SPI-NOR Rail Firewall
    if not (ISP_VCCQ_MIN_SAFE_V <= spec.vccq_voltage_v <= ISP_VCCQ_MAX_SAFE_V) or not (
        ISP_VCCQ_MIN_SAFE_V <= spec.spi_nor_voltage_v <= ISP_VCCQ_MAX_SAFE_V
    ):
        blocked.append(BLOCKED_ISP_1V8_RAIL_OVERVOLTAGE)
        errors.append(
            f"ISP rail voltage out of 1.8V safe window: vccq={spec.vccq_voltage_v:.2f}V, spi_nor={spec.spi_nor_voltage_v:.2f}V."
        )

    # 3. SoC Reset Isolation & Power Disconnect + Fly-wire length
    electrical_iso = spec.soc_reset_held_low and spec.main_battery_and_usb_disconnected
    if not electrical_iso:
        blocked.append(BLOCKED_ISP_BUS_CONTENTION_SOC_ACTIVE)
        errors.append("CXD90057 RESET_N must be held low with battery & USB disconnected before ISP attach.")
    if spec.flywire_length_cm <= 0.0 or spec.flywire_length_cm > ISP_MAX_FLYWIRE_CM:
        blocked.append(BLOCKED_ISP_FLYWIRE_TOO_LONG)
        errors.append(f"ISP fly-wire length {spec.flywire_length_cm:.1f} cm exceeds {ISP_MAX_FLYWIRE_CM:.1f} cm ceiling.")

    # 4. EXT_CSD[179] BOOT_PARTITION_ENABLE, [177] BOOT_BUS_CONDITIONS, [162] RST_n_FUNCTION
    if len(spec.ext_csd_bytes) != EMMC_EXT_CSD_BYTES:
        blocked.append(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD)
        errors.append(f"EXT_CSD must be 512 bytes (got {len(spec.ext_csd_bytes)}).")
        part_cfg = 0
        boot_bus = 0
        rst_n = 0
        boot_en = 0
        boot_ack = 0
        part_acc = 0
    else:
        part_cfg = spec.ext_csd_bytes[EMMC_EXT_CSD_PART_CONFIG_IDX]
        boot_bus = spec.ext_csd_bytes[EMMC_EXT_CSD_BOOT_BUS_COND_IDX]
        rst_n = spec.ext_csd_bytes[EMMC_EXT_CSD_RST_N_IDX]
        boot_en = (part_cfg & PART_CONFIG_ENABLE_MASK) >> PART_CONFIG_ENABLE_SHIFT
        boot_ack = 1 if (part_cfg & PART_CONFIG_BOOT_ACK_BIT) else 0
        part_acc = part_cfg & PART_CONFIG_ACCESS_MASK

        if (part_cfg & PART_CONFIG_RESERVED_BIT7) != 0 or boot_en not in (BOOT_PART_ENABLE_BOOT0, BOOT_PART_ENABLE_BOOT1):
            blocked.append(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD)
            errors.append(f"EXT_CSD[179] invalid BOOT_PARTITION_ENABLE={boot_en} (part_config=0x{part_cfg:02x}).")
        if part_acc != 0:
            blocked.append(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD)
            errors.append(f"EXT_CSD[179] PARTITION_ACCESS={part_acc} leaked non-zero (expected 0=UDA).")
        if (boot_bus & BOOT_BUS_RESERVED_MASK) != 0 or (boot_bus & 0x03) == 3 or ((boot_bus >> 3) & 0x03) == 3:
            blocked.append(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD)
            errors.append(f"EXT_CSD[177] BOOT_BUS_CONDITIONS=0x{boot_bus:02x} invalid/reserved.")
        if rst_n not in ISP_VALID_EXT_CSD_162_RST_N_VALUES:
            blocked.append(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD)
            errors.append(f"EXT_CSD[162] RST_n_FUNCTION=0x{rst_n:02x} reserved/corrupt.")
        if spec.otp_162_write_requested:
            blocked.append(BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD)
            errors.append("Attempt to write OTP EXT_CSD[162] RST_n_FUNCTION is permanently forbidden.")

    # 5. Per-Camera CID-Bound pnflasha* + /dev/mtd0ro Vault Pairing & Two-Pass SHA-256
    cid_paired = (
        bool(_SHA256_HEX_RE.match(spec.cid_sha256))
        and bool(_SHA256_HEX_RE.match(spec.body_serial_sha256))
        and spec.cid_sha256 == spec.vault_cid_sha256
        and spec.body_serial_sha256 == spec.vault_body_serial_sha256
    )
    pn_ok = bool(_SHA256_HEX_RE.match(spec.pnflasha_bundle_sha256)) and spec.pnflasha_bundle_sha256 == spec.pnflasha_readback_sha256
    mtd_ok = bool(_SHA256_HEX_RE.match(spec.mtd0ro_sha256)) and spec.mtd0ro_sha256 == spec.mtd0ro_readback_sha256
    if not (cid_paired and pn_ok and mtd_ok):
        blocked.append(BLOCKED_CROSS_CAMERA_CID_VAULT_MISMATCH)
        errors.append("Per-camera CID-bound pnflasha* and /dev/mtd0ro two-pass vault pairing failed.")

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = len(dedup_blocked) == 0 and len(errors) == 0
    return IspChecklistVerificationReport(
        passed=passed,
        theoretical_bench_repair_eligible=passed,
        ext_csd_179_part_config_hex=f"0x{part_cfg:02x}",
        boot_partition_enable=boot_en,
        boot_ack=boot_ack,
        partition_access=part_acc,
        ext_csd_177_boot_bus_hex=f"0x{boot_bus:02x}",
        ext_csd_162_rst_n_hex=f"0x{rst_n:02x}",
        cid_vault_paired=cid_paired,
        pnflasha_two_pass_verified=pn_ok,
        mtd0ro_two_pass_verified=mtd_ok,
        electrical_isolation_ok=electrical_iso,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar_c_isp_6_scenario_suite() -> PillarCIsp6ScenarioSuiteResult:
    """Execute 6-scenario last-resort off-chip 1.8V ISP verification checklist."""
    cases = (
        (
            P155_PILLAR_C_SCENARIO_IDS[0],
            True,
            None,
            build_synthetic_isp_checklist_spec(),
        ),
        (
            P155_PILLAR_C_SCENARIO_IDS[1],
            False,
            BLOCKED_ISP_1V8_RAIL_OVERVOLTAGE,
            build_synthetic_isp_checklist_spec(vccq_voltage_v=3.30, spi_nor_voltage_v=3.30),
        ),
        (
            P155_PILLAR_C_SCENARIO_IDS[2],
            False,
            BLOCKED_ISP_BUS_CONTENTION_SOC_ACTIVE,
            build_synthetic_isp_checklist_spec(soc_reset_held_low=False, main_battery_and_usb_disconnected=False),
        ),
        (
            P155_PILLAR_C_SCENARIO_IDS[3],
            False,
            BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD,
            build_synthetic_isp_checklist_spec(part_config=0x01, rst_n_function=0x03, otp_162_write_requested=True),
        ),
        (
            P155_PILLAR_C_SCENARIO_IDS[4],
            False,
            BLOCKED_CROSS_CAMERA_CID_VAULT_MISMATCH,
            build_synthetic_isp_checklist_spec(cross_camera_cid_mismatch=True),
        ),
        (
            P155_PILLAR_C_SCENARIO_IDS[5],
            False,
            BLOCKED_PERSISTENT_ISP_WRITE_LOCKED,
            build_synthetic_isp_checklist_spec(request_persistent_emmc_writes=True, request_spi_nor_write=True),
        ),
    )

    outcomes: List[PillarCIspScenarioOutcome] = []
    for sid, exp_ok, exp_code, spec in cases:
        rep = verify_last_resort_isp_checklist(spec)
        ok = (
            rep.passed == exp_ok
            and rep.theoretical_bench_repair_eligible == exp_ok
            and not rep.persistent_emmc_writes_authorized
            and not rep.spi_nor_write_authorized
            and rep.otp_fuse_touches == 0
            and rep.physical_device_writes == 0
            and (exp_code is None or exp_code in rep.blocked_codes)
        )
        outcomes.append(
            PillarCIspScenarioOutcome(
                scenario_id=sid,
                passed=ok,
                theoretical_bench_repair_eligible=rep.theoretical_bench_repair_eligible,
                blocked_codes=rep.blocked_codes,
                errors=rep.errors,
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(P155_PILLAR_C_SCENARIO_IDS)
    return PillarCIsp6ScenarioSuiteResult(
        passed=all_ok,
        status=P155_STATUS_VERIFIED_PILLAR_C if all_ok else P155_STATUS_REJECTED_PILLAR_C,
        scenarios_passed=passed_cnt,
        scenarios_total=len(P155_PILLAR_C_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Unified Phase 155 (Pillar 20) Suite Entrypoint
# ---------------------------------------------------------------------------


def run_realhw_uart_460800_post_triage_and_isp_suite(
    force_clean_room: Optional[bool] = None,
) -> RealHwUart460800IspSuiteReport:
    """Run all Phase 155 (Pillar 20) real-hardware 460800n8 UART triage, 1.8V firewall & ISP checklist gates."""
    donor_snap = inspect_uart_460800_and_isp_donors_readonly(force_clean_room=force_clean_room)
    pa = run_pillar_a_triage_8_scenario_suite()
    pb = run_pillar_b_firewall_6_scenario_suite()
    pc = run_pillar_c_isp_6_scenario_suite()

    all_ok = donor_snap.all_passed and pa.passed and pb.passed and pc.passed
    status = P155_STATUS_VERIFIED_SUITE if all_ok else P155_STATUS_FAIL_SUITE
    digest_payload = {
        "schema": PHASE155_SCHEMA,
        "version": PHASE155_VERSION,
        "status": status,
        "verification_mode": donor_snap.verification_mode,
        "donor_snapshot": donor_snap.to_dict(),
        "pillar_a": pa.to_dict(),
        "pillar_b": pb.to_dict(),
        "pillar_c": pc.to_dict(),
        "passive_tx_bytes_emitted": PASSIVE_TX_BYTES_EMITTED,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
        "otp_fuse_touches": OTP_FUSE_TOUCHES,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
    }
    suite_sha = sha256(
        json.dumps(digest_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return RealHwUart460800IspSuiteReport(
        schema=PHASE155_SCHEMA,
        version=PHASE155_VERSION,
        status=status,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        donor_snapshot=donor_snap,
        pillar_a_triage_8_scenarios=pa,
        pillar_b_firewall_6_scenarios=pb,
        pillar_c_isp_6_scenarios=pc,
        suite_sha256=suite_sha,
    )


__all__ = [
    "ACTION_CREATE_STOP_STAGEB_FLAG",
    "ACTION_DISCONNECT_ADAPTER_CHECK_1V8",
    "ACTION_EJECT_SD_47US_BYPASS",
    "ACTION_HOLD_MENU_SHUTTER_POWER",
    "ACTION_NONE_HEALTHY",
    "ACTION_P1_LINE1_MODE_CLEAR",
    "ACTION_TIER0_VAULT_RESTORE",
    "BLOCKED_ACTIVE_TX_BYTES_ATTEMPTED",
    "BLOCKED_CROSS_CAMERA_CID_VAULT_MISMATCH",
    "BLOCKED_EXT_CSD_162_OTP_OR_179_177_GUARD",
    "BLOCKED_ISP_1V8_RAIL_OVERVOLTAGE",
    "BLOCKED_ISP_BUS_CONTENTION_SOC_ACTIVE",
    "BLOCKED_ISP_FLYWIRE_TOO_LONG",
    "BLOCKED_MULTI_USB_BUS_CONTENTION",
    "BLOCKED_OVERVOLTAGE_1V8_PAD_HAZARD",
    "BLOCKED_P1_KEMCO_MISSING_460800_CONSOLE",
    "BLOCKED_PERSISTENT_ISP_WRITE_LOCKED",
    "BLOCKED_PHYSICAL_TX_LINE_CONNECTED",
    "BLOCKED_UNDERVOLTAGE_1V8_TAP",
    "BLOCKED_UNSUPPORTED_460800_8N1_FRAMING",
    "BLOCKED_VMC_BNCM1_LTC_CONTENTION",
    "BootStage6Trace",
    "ERR_UNKNOWN_OR_EMPTY_UART_LOG",
    "ISP_MAX_FLYWIRE_CM",
    "ISP_SPI_NOR_NOMINAL_V",
    "ISP_VALID_EXT_CSD_162_RST_N_VALUES",
    "ISP_VCCQ_MAX_SAFE_V",
    "ISP_VCCQ_MIN_SAFE_V",
    "ISP_VCCQ_NOMINAL_V",
    "IspBenchChecklistSpec",
    "IspChecklistVerificationReport",
    "LANC_ID_OHM_MAX",
    "LANC_ID_OHM_MIN",
    "P155_DONOR_FX3_CPAPP_B_RELPATH",
    "P155_DONOR_FX3_INIT_RELPATH",
    "P155_DONOR_FX3_KEMCO_RELPATH",
    "P155_DONOR_FX3_LIBSENCORE_RELPATH",
    "P155_DONOR_FX3_TOMCO_RELPATH",
    "P155_PILLAR_A_SCENARIO_IDS",
    "P155_PILLAR_B_SCENARIO_IDS",
    "P155_PILLAR_C_SCENARIO_IDS",
    "P155_PINNED_FX3_CPAPP_B_BYTES",
    "P155_PINNED_FX3_CPAPP_B_HDR4K_SHA256",
    "P155_PINNED_FX3_INIT_BYTES",
    "P155_PINNED_FX3_INIT_SHA256",
    "P155_PINNED_FX3_KEMCO_BYTES",
    "P155_PINNED_FX3_KEMCO_SHA256",
    "P155_PINNED_FX3_LIBSENCORE_BYTES",
    "P155_PINNED_FX3_LIBSENCORE_SHA256",
    "P155_PINNED_FX3_TOMCO_BYTES",
    "P155_PINNED_FX3_TOMCO_SHA256",
    "P155_STATUS_FAIL_SUITE",
    "P155_STATUS_REJECTED_PILLAR_A",
    "P155_STATUS_REJECTED_PILLAR_B",
    "P155_STATUS_REJECTED_PILLAR_C",
    "P155_STATUS_VERIFIED_PILLAR_A",
    "P155_STATUS_VERIFIED_PILLAR_B",
    "P155_STATUS_VERIFIED_PILLAR_C",
    "P155_STATUS_VERIFIED_SUITE",
    "PHASE155_SCHEMA",
    "PHASE155_VERSION",
    "PillarATriage8ScenarioSuiteResult",
    "PillarATriageScenarioOutcome",
    "PillarBFirewall6ScenarioSuiteResult",
    "PillarBFirewallScenarioOutcome",
    "PillarCIsp6ScenarioSuiteResult",
    "PillarCIspScenarioOutcome",
    "RealHwUart460800IspSuiteReport",
    "UART_1V8_MAX_SAFE_V",
    "UART_1V8_MIN_SAFE_V",
    "UART_1V8_NOMINAL_V",
    "UART_460800_BAUD",
    "UART_460800_BOOT_STAGES",
    "UART_460800_CONSOLE_ARG",
    "UART_460800_FRAMING",
    "UART_460800_STAGE_INDEX_MAP",
    "UART_OVERVOLTAGE_3V3_V",
    "UART_OVERVOLTAGE_5V0_V",
    "Uart460800ElectricalConfig",
    "Uart460800FirewallDecision",
    "Uart460800TriageResult",
    "UartIspDonorArtifactDigest",
    "UartIspDonorSnapshot",
    "VALID_460800_RECOVERY_ACTIONS",
    "VMC_BNCM1_LTC_OHM_MAX",
    "VMC_BNCM1_LTC_OHM_MIN",
    "audit_1v8_uart_and_multi_usb_firewall",
    "build_default_8_triage_scenarios",
    "build_synthetic_isp_checklist_spec",
    "build_synthetic_isp_ext_csd",
    "build_synthetic_p1_diagnostic_kemco_profile",
    "inspect_uart_460800_and_isp_donors_readonly",
    "parse_ttyama0_460800_boot_stages",
    "run_pillar_a_triage_8_scenario_suite",
    "run_pillar_b_firewall_6_scenario_suite",
    "run_pillar_c_isp_6_scenario_suite",
    "run_realhw_uart_460800_post_triage_and_isp_suite",
    "triage_ttyama0_460800_boot_log",
    "validate_p1_diagnostic_kemco_profile",
    "verify_last_resort_isp_checklist",
]
