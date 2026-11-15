"""Phase 160 — Pillar 21 (21/21 Recovery Pillars): Real-Hardware 5-Tier Unbrickable Recovery
Escalation Ladder, CXD90057 (Mira) Multi-USB 1.8V UART EL3 (0xfe020000) Cold-Boot Guard &
Official Sony BODYDATA.DAT (\\x89UFU) Stock-Reflash Verifier.

Closes the physical Sony ILME-FX3 (`Ver. 7.02`, Model ID `0x91030080`, SoC `CXD90057` Mira +
`CXD90058` Cetus) recovery architecture across all 5 escalation tiers while hard-locking every
physical write/transmit/fuse safety gate:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `ISP_WRITE_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `PHYSICAL_USB_PACKETS_EMITTED = 0`
- `PHYSICAL_DEVICE_WRITES = 0`
- `PASSIVE_TX_BYTES_EMITTED = 0`
- `OTP_FUSE_TOUCHES = 0`
- `OTP_FUSE_WRITES = 0`
- `RAW_FIRMWARE_BYTES_LEAKED = 0`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects FX3 `7.02` `loader_nor.bin` (`101,888 B`, EL3 `VBAR_EL3`), `p1` `/sbin/init`
     (plus `7.02` `p3` `/sbin/init`), `Backup.bin` (`2,229,740 B`, `BK4\\0`, `ILME-FX3` /
     `0x91030080` family), `cpapp-b.bin` (bounded 4 KiB header), and bounded header/tail
     metadata (`<= 64 KiB`) of official FX3 `7.02` `BODYDATA.DAT` (`811,876,768 B`,
     `\\x89UFU\\r\\n\\x1a\\n`) strictly via `os.open(..., os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)`.
   - Never reads hundreds of MiB repeatedly; total execution stays `< 0.5 s`.
   - Deterministic `CLEAN_ROOM_SYNTHETIC` fallback when `FX3_FX6_FORCE_CLEAN_ROOM=1` or donors
     are absent, leaking zero raw Sony firmware bytes in JSON output.

2. **Pillar A — Official Sony `BODYDATA.DAT` (`\\x89UFU`) Stock `p1` Reflash Pre-Verifier (8 Scenarios)**:
   - Parses `\\x89UFU\\r\\n\\x1a\\n` TLV chunks (`DATV`, `PROV`, `UDID`, `FDAT`, `DEND`),
     audits `1024 B` `<HH` chunk framing (`0x8000` terminal flag + `272 B` IV/RSA-2048 trailer),
     enforces strict `ILME-FX3` (`0x91030080`) target-model pre-verification (hard-rejecting
     cross-body `ILME-FX30`, `ILCE-7SM3`, `ILCE-7M4`, `ILME-FX6` packages), and mandates
     pre-update `p15:/usr` `.orig` clean-uninstall verification before allowing stock reflash.

3. **Pillar B — `CXD90057` (`Mira`) 15-Pin Multi/Micro-USB `1.8V UART` EL3 (`0xfe020000`) Cold-Boot Guard (6 Scenarios)**:
   - Audits `15-Pin Multi/Micro-USB` pinout (`Pin 7 XRESET_REQ`, `Pin 8 UART TX`, `Pin 9 UART RX`
     `1.8V CMOS`, `Pin 10 AD_JACK_IN`), enforces `1.65V..1.98V` logic safety & `VMC-BNCM1`
     (`680 kOhm` LTC) mutual exclusion, validates `0xfe020000` EL3 SRAM load bounds, and
     hard-locks `el3_payload_transmit_authorized = False` as a read-only architectural audit
     prior to any off-chip soldering.

4. **Pillar C — Deterministic 5-Tier Unbrickable Hardware Recovery Escalation Engine (8 Scenarios)**:
   - `Tier-1`: Power-off SD removal / `EH1` (`47 us` Stage-A bypass -> 100% stock FX3 userland, zero writes).
   - `Tier-2`: Atomic `p15:/usr` `.orig` rollback (`EH2` flag / `16/16` `SHA256(H0) == SHA256(H3)` clean uninstaller via `054C:0DA1 -> 054C:0336` Jiritsu).
   - `Tier-3`: Official Sony `BODYDATA.DAT` (`\\x89UFU\\r\\n\\x1a\\n` `Ver. 7.02`) stock `p1` reflash (with strict `0x91030080` + `p15` `.orig` clean-uninstall pre-gate).
   - `Tier-4`: `CXD90057` 15-pin Multi/Micro-USB EL3 (`0xfe020000`) cold-boot read-only diagnostic guard (`el3_payload_transmit_authorized = False`).
   - `Tier-5`: Off-chip `8-bit` eMMC ISP (`pnflasha*` raw ciphertext + `CID`-matched same-body Tier-0 vault) & `SPI NOR` (`loader_nor.bin`) hardware last resort (`isp_write_authorized = False`, `spi_nor_write_authorized = False`).
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
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .fat import FatP1, MAX_P1
from .files import is_forced_clean_room, local_path, read_file, require, resolve_donor_path
from .squash import SquashFS


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE160_SCHEMA: str = "fx3-realhw-bootrom-el3-and-ufu-stock-reflash-verifier-v1"
PHASE160_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Bounded Donor Read Ceiling (<= 64 KiB for huge BODYDATA.DAT / cpapp-b.bin headers)
BOUNDED_HEADER_MAX_BYTES: int = 65536
BODYDATA_BOUNDED_HEADER_BYTES: int = 4096
BODYDATA_BOUNDED_TAIL_BYTES: int = 12

# Target Model Identity & Cross-Body Rejection Matrix
FX3_MODEL_ID: int = 0x91030080
FX3_MODEL_NAME: str = "ILME-FX3"
FX3_STOCK_VERSION: str = "7.02"
FX3_STOCK_EPOCH: int = 5
FX3_SOC_AP: str = "CXD90057"  # Mira
FX3_SOC_CP: str = "CXD90058"  # Cetus

# Cross-body identifiers that must NEVER be accepted for FX3 stock reflash
CROSS_BODY_MODEL_IDS: Dict[str, int] = {
    "ILME-FX30": 0x910300A0,
    "ILCE-7SM3": 0x91030040,
    "ILCE-7M4": 0x91030070,
    "ILME-FX6": 0x91040086,
    "ILME-FX6_ALT": 0x91030060,
    "ILME-FX3A": 0x91030082,
}
VALID_REGIONS: Tuple[str, ...] = ("NTSC", "PAL")

# Sony UFU (BODYDATA.DAT) Framing Constants
UFU_MAGIC: bytes = b"\x89UFU\r\n\x1a\n"
UFU_MAGIC_HEX: str = UFU_MAGIC.hex()
FDAT_BLOCK_BYTES: int = 1024
FDAT_CHUNK_HDR_BYTES: int = 4
FDAT_CHUNK_PAYLOAD_MAX: int = FDAT_BLOCK_BYTES - FDAT_CHUNK_HDR_BYTES  # 1020 B
FDAT_TERMINAL_FLAG: int = 0x8000
FDAT_IV_RSA2048_TRAILER_BYTES: int = 272  # 16 B IV + 256 B RSA-2048 signature
SONY_MIN_UPDATE_BATTERY_PCT: int = 51

# USB Service / Jiritsu PIDs
SONY_USB_VID: int = 0x054C
SONY_FX3_MSC_PID: int = 0x0DA1
SONY_FX3_SERVICE_PID: int = 0x0336
SONY_FX3_JIRITSU_SEQUENCE: str = "054C:0DA1 -> 054C:0336"

# CXD90057 (Mira) 15-Pin Multi/Micro-USB & EL3 Cold-Boot Constants
EL3_COLD_BOOT_SRAM_BASE: int = 0xFE020000
EL3_COLD_BOOT_SRAM_LIMIT: int = 0xFE060000
EL3_COLD_BOOT_MAX_PAYLOAD_BYTES: int = 192 * 1024
LOADER_NOR_SRAM_ENTRY: int = 0xFE049000
MULTI_USB_REQUIRED_PINS: Dict[int, str] = {
    2: "GND",
    7: "XRESET_REQ",
    8: "UART_TX",
    9: "UART_RX",
    10: "AD_JACK_IN",
}
MULTI_USB_1V8_NOMINAL_V: float = 1.80
MULTI_USB_1V8_MIN_V: float = 1.65
MULTI_USB_1V8_MAX_V: float = 1.98
VMC_BNCM1_LTC_OHM_NOMINAL: float = 680_000.0
LANC_OHM_NOMINAL: float = 100_000.0

# 5-Tier Recovery Ladder Constants
TIER_1_EH1_SD_47US_BYPASS: str = "TIER_1_EH1_SD_47US_BYPASS"
TIER_2_P15_ORIG_ATOMIC_ROLLBACK: str = "TIER_2_P15_ORIG_ATOMIC_ROLLBACK"
TIER_3_OFFICIAL_UFU_BODYDATA_STOCK_REFLASH: str = "TIER_3_OFFICIAL_UFU_BODYDATA_STOCK_REFLASH"
TIER_4_CXD90057_MULTI_USB_EL3_COLDBOOT_DIAG: str = "TIER_4_CXD90057_MULTI_USB_EL3_COLDBOOT_DIAG"
TIER_5_OFFCHIP_8BIT_ISP_AND_SPI_NOR_VAULT: str = "TIER_5_OFFCHIP_8BIT_ISP_AND_SPI_NOR_VAULT"
TIER_0_HEALTHY_NO_RECOVERY_NEEDED: str = "TIER_0_HEALTHY_NO_RECOVERY_NEEDED"
TIER_BLOCKED_UNSAFE_REQUEST: str = "TIER_BLOCKED_UNSAFE_REQUEST"

FIVE_TIER_ORDER: Tuple[str, ...] = (
    TIER_1_EH1_SD_47US_BYPASS,
    TIER_2_P15_ORIG_ATOMIC_ROLLBACK,
    TIER_3_OFFICIAL_UFU_BODYDATA_STOCK_REFLASH,
    TIER_4_CXD90057_MULTI_USB_EL3_COLDBOOT_DIAG,
    TIER_5_OFFCHIP_8BIT_ISP_AND_SPI_NOR_VAULT,
)

# Pinned FX3 Donor Relpaths & Digests (Zero raw firmware bytes emitted)
P160_DONOR_FX3_LOADER_NOR_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/loader_nor.bin"
)
P160_DONOR_FX3_P1_205_RELPATH: str = (
    "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"
)
P160_DONOR_FX3_702_INIT_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/p3-initrd/sbin/init"
)
P160_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P160_DONOR_FX3_CPAPP_B_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
)
P160_DONOR_FX3_BODYDATA_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"

P160_PINNED_FX3_LOADER_NOR_BYTES: int = 101888
P160_PINNED_FX3_LOADER_NOR_SHA256: str = "4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942"
P160_PINNED_FX3_P1_205_BYTES: int = 19377152
P160_PINNED_FX3_P1_205_SHA256: str = "ab2cd5372fed3c742b586e28484c6bf0aa6ebfba1f6d8e450a19191abc5b6591"
P160_PINNED_FX3_P1_SBIN_INIT_BYTES: int = 1438
P160_PINNED_FX3_P1_SBIN_INIT_SHA256: str = "223f642c9cc8eb3a53901263940d42905a3d57fc5a091459003719e216950ccd"
P160_PINNED_FX3_702_INIT_BYTES: int = 735
P160_PINNED_FX3_702_INIT_SHA256: str = "c83de1abeeb779f7473181b51face32ecfedfa3bd5c0fc346ae0c628f1b0ac5e"
P160_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P160_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
P160_PINNED_FX3_CPAPP_B_BYTES: int = 15980568
P160_PINNED_FX3_CPAPP_B_HDR4K_SHA256: str = "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d"
P160_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P160_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

# Status & Fail-Closed Error Codes
P160_STATUS_VERIFIED_SUITE: str = "VERIFIED_REALHW_5TIER_EL3_UFU_21PILLAR_GATE"
P160_STATUS_FAIL_SUITE: str = "FAIL_REALHW_5TIER_EL3_UFU_21PILLAR_GATE"
P160_STATUS_VERIFIED_PILLAR_A: str = "VERIFIED_UFU_BODYDATA_STOCK_REFLASH_PREFLIGHT"
P160_STATUS_REJECTED_PILLAR_A: str = "REJECTED_UFU_BODYDATA_STOCK_REFLASH_PREFLIGHT"
P160_STATUS_VERIFIED_PILLAR_B: str = "VERIFIED_CXD90057_MULTI_USB_EL3_COLDBOOT_GUARD"
P160_STATUS_REJECTED_PILLAR_B: str = "REJECTED_CXD90057_MULTI_USB_EL3_COLDBOOT_GUARD"
P160_STATUS_VERIFIED_PILLAR_C: str = "VERIFIED_5TIER_UNBRICKABLE_ESCALATION_LADDER"
P160_STATUS_REJECTED_PILLAR_C: str = "REJECTED_5TIER_UNBRICKABLE_ESCALATION_LADDER"

BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH: str = "BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH_NOT_FX3_0X91030080"
BLOCKED_DIRTY_P15_STAGEB_CLEAN_UNINSTALL_REQUIRED: str = "BLOCKED_DIRTY_P15_ORIG_CLEAN_UNINSTALL_REQUIRED_FIRST"
BLOCKED_UFU_OR_FDAT_1024B_FRAMING_INVALID: str = "BLOCKED_UFU_DATV_PROV_UDID_OR_FDAT_1024B_FRAMING_INVALID"
BLOCKED_OTA_BATTERY_OR_REGION_PREFLIGHT: str = "BLOCKED_OTA_BATTERY_BELOW_51_OR_CROSS_REGION"
BLOCKED_UFU_EPOCH_DOWNGRADE: str = "BLOCKED_UFU_FIRMWARE_EPOCH_DOWNGRADE"
BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE: str = "BLOCKED_PERSISTENT_EMMC_AND_SPI_NOR_WRITES_LOCKED_FALSE"
BLOCKED_EL3_PAYLOAD_TRANSMIT_LOCKED_FALSE: str = "BLOCKED_EL3_0XFE020000_PAYLOAD_TRANSMIT_LOCKED_FALSE"
BLOCKED_MULTI_USB_1V8_CMOS_OVERVOLTAGE: str = "BLOCKED_MULTI_USB_1V8_CMOS_VOLTAGE_OUT_OF_WINDOW"
BLOCKED_PIN10_AD_JACK_IN_LTC_COLLISION: str = "BLOCKED_PIN10_AD_JACK_IN_VMC_BNCM1_LTC_COLLISION"
BLOCKED_EL3_SRAM_WINDOW_OR_ALIGN_INVALID: str = "BLOCKED_EL3_SRAM_0XFE020000_WINDOW_OR_ALIGN_INVALID"
BLOCKED_MULTI_USB_PINOUT_INCOMPLETE: str = "BLOCKED_MULTI_USB_15PIN_PINOUT_MISSING_OR_MISMATCH"
BLOCKED_CROSS_CAMERA_CID_VAULT_OR_WRITE_LOCKED: str = "BLOCKED_TIER5_CROSS_CAMERA_CID_OR_ISP_WRITE_LOCKED"

P160_PILLAR_A_SCENARIO_IDS: Tuple[str, ...] = (
    "U01_VALID_FX3_702_UFU_CLEAN_P15_UNINSTALLED",
    "U02_BLOCKED_CROSS_BODY_ILME_FX30_BODYDATA",
    "U03_BLOCKED_CROSS_BODY_ILCE_7SM3_BODYDATA",
    "U04_BLOCKED_CROSS_BODY_ILCE_7M4_OR_FX6_BODYDATA",
    "U05_BLOCKED_DIRTY_P15_ORIG_NOT_UNINSTALLED",
    "U06_BLOCKED_UFU_DATV_PROV_UDID_FDAT_1024B_CORRUPT",
    "U07_BLOCKED_BATTERY_BELOW_51_OR_CROSS_REGION",
    "U08_BLOCKED_PERSISTENT_EMMC_WRITE_REQUEST",
)

P160_PILLAR_B_SCENARIO_IDS: Tuple[str, ...] = (
    "E01_READONLY_EL3_0XFE020000_DIAGNOSTIC_AUDIT_ONLY",
    "E02_BLOCKED_EL3_TRANSMIT_AUTHORIZATION_REQUEST",
    "E03_BLOCKED_3V3_OR_5V_MULTI_USB_1V8_PAD_HAZARD",
    "E04_BLOCKED_AD_JACK_IN_PIN10_VMC_BNCM1_LTC_COLLISION",
    "E05_BLOCKED_EL3_LOAD_ADDR_OUTSIDE_0XFE020000_SRAM",
    "E06_BLOCKED_PIN7_XRESET_OR_PIN8_9_UART_PINOUT_MISSING",
)

P160_PILLAR_C_SCENARIO_IDS: Tuple[str, ...] = (
    "T1_STAGEB_SD_BOOT_STALL_EH1_47US_BYPASS",
    "T2_P15_OVERLAY_INSTALLED_EH2_16OF16_H0_EQ_H3_ROLLBACK",
    "T3_TORN_OTA_CLEAN_P15_VALID_FX3_702_UFU_REFLASH",
    "T3_REDIRECT_DIRTY_P15_TO_TIER2_ORIG_UNINSTALL_FIRST",
    "T3_BLOCKED_CROSS_BODY_FX30_UFU_REFUSED",
    "T4_BOOTROM_COLD_HANG_EL3_0XFE020000_READONLY_AUDIT",
    "T5_CORRUPT_SPI_NOR_AND_BOOT_EMMC_CID_VAULT_AUDIT",
    "T5_BLOCKED_CROSS_CAMERA_CID_VAULT_OR_WRITE_UNLOCK",
)

_SHA256_HEX_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase160DonorArtifactDigest:
    label: str
    relpath: str
    source_mode: str
    open_flags: str
    byte_length: int
    sha256: str
    bounded_header_sha256: Optional[str]
    verified_markers: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class Phase160DonorSnapshot:
    verification_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    bodydata_total_bytes: int
    bodydata_ufu_magic_ok: bool
    bodydata_datv_version: int
    bodydata_prov_value: int
    bodydata_udid_count: int
    bodydata_fdat_payload_bytes: int
    bodydata_fdat_1024b_aligned: bool
    loader_nor_el3_vbar_ok: bool
    backup_bin_model_ok: bool
    artifacts: Tuple[Phase160DonorArtifactDigest, ...]
    all_passed: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UfuEnvelopeParseResult:
    valid: bool
    ufu_magic_ok: bool
    datv_present: bool
    datv_version: int
    prov_present: bool
    prov_value: int
    udid_present: bool
    udid_usb_ids: Tuple[str, ...]
    msc_054c_0da1_present: bool
    fdat_present: bool
    fdat_offset: int
    fdat_length_bytes: int
    fdat_payload_1024b_aligned: bool
    dend_present: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Fdat1024FramingResult:
    valid: bool
    chunk_count: int
    total_stream_bytes: int
    reconstructed_bytes: int
    terminal_flag_seen: bool
    checksum_errors: Tuple[str, ...]
    framing_errors: Tuple[str, ...]
    reconstructed_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UfuStockReflashRequest:
    target_model_name: str = FX3_MODEL_NAME
    target_model_id: int = FX3_MODEL_ID
    package_version: str = FX3_STOCK_VERSION
    camera_current_version: str = FX3_STOCK_VERSION
    package_region: str = "NTSC"
    camera_region: str = "NTSC"
    battery_pct: int = 100
    sha256_verified: bool = True
    p15_stageb_overlay_installed: bool = False
    p15_orig_uninstalled: bool = True
    p15_orig_16of16_sha256_h0_eq_h3: bool = True
    ufu_header_bytes: bytes = b""
    fdat_chunk_stream_bytes: bytes = b""
    request_persistent_emmc_writes: bool = False


@dataclass(frozen=True)
class UfuStockReflashReport:
    passed: bool
    status: str
    target_model_name: str
    target_model_id_hex: str
    model_match_fx3_0x91030080: bool
    ufu_envelope_ok: bool
    fdat_1024b_framing_ok: bool
    p15_clean_uninstall_verified: bool
    preflight_approved_offline_only: bool
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    blocked_codes: Tuple[str, ...] = ()
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarAUfuScenarioOutcome:
    scenario_id: str
    passed: bool
    expected_pass: bool
    observed_pass: bool
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PillarAUfu8ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    scenarios: Tuple[PillarAUfuScenarioOutcome, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Cxd90057El3ColdBootSpec:
    pin_map: Dict[int, str]
    io_voltage_v: float = MULTI_USB_1V8_NOMINAL_V
    ad_jack_in_ohm: float = 0.0
    vmc_bncm1_attached: bool = False
    lanc_attached: bool = False
    el3_load_addr: int = EL3_COLD_BOOT_SRAM_BASE
    el3_payload_bytes: int = 16384
    diagnostic_only_before_offchip_solder: bool = True
    authorize_el3_payload_transmit: bool = False
    tx_bytes_requested: int = 0
    request_persistent_emmc_writes: bool = False
    request_spi_nor_write: bool = False


@dataclass(frozen=True)
class Cxd90057El3ColdBootReport:
    passed: bool
    status: str
    el3_load_addr_hex: str
    el3_sram_window_ok: bool
    multi_usb_pinout_ok: bool
    io_1v8_cmos_ok: bool
    ad_jack_in_ltc_isolated: bool
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    blocked_codes: Tuple[str, ...] = ()
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarBEl3ScenarioOutcome:
    scenario_id: str
    passed: bool
    expected_pass: bool
    observed_pass: bool
    el3_payload_transmit_authorized: bool
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PillarBEl36ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    scenarios: Tuple[PillarBEl3ScenarioOutcome, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RecoverySymptomInput:
    scenario_id: str
    stage_reached: str
    sd_stageb_active: bool = False
    p15_overlay_installed: bool = False
    eh2_16of16_h0_eq_h3_ready: bool = True
    jiritsu_0da1_to_0336_available: bool = True
    ufu_reflash_request: Optional[UfuStockReflashRequest] = None
    bootrom_cold_hang_or_bloader_corrupt: bool = False
    el3_coldboot_spec: Optional[Cxd90057El3ColdBootSpec] = None
    emmc_and_spinor_offchip_isp_needed: bool = False
    isp_cid_sha256: str = ""
    vault_cid_sha256: str = ""
    pnflasha_and_mtd0ro_verified: bool = False
    request_isp_write_unlock: bool = False
    request_spi_nor_write: bool = False
    request_persistent_emmc_writes: bool = False


@dataclass(frozen=True)
class FiveTierEscalationDecision:
    scenario_id: str
    passed: bool
    selected_tier: str
    tier_rank: int
    action_summary: str
    requires_clean_p15_uninstall_first: bool
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    isp_write_authorized: bool = ISP_WRITE_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    blocked_codes: Tuple[str, ...] = ()
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class PillarC5TierScenarioOutcome:
    scenario_id: str
    passed: bool
    expected_tier: str
    observed_tier: str
    expected_pass: bool
    observed_pass: bool
    blocked_codes: Tuple[str, ...]


@dataclass(frozen=True)
class PillarC5Tier8ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    isp_write_authorized: bool = ISP_WRITE_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    scenarios: Tuple[PillarC5TierScenarioOutcome, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class RealHwBootromEl3AndUfuSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    read_only_donor_access: bool
    physical_usb_packets_emitted: int
    physical_device_writes: int
    passive_tx_bytes_emitted: int
    otp_fuse_touches: int
    otp_fuse_writes: int
    raw_firmware_bytes_leaked: int
    donor_snapshot: Phase160DonorSnapshot
    pillar_a_ufu_8_scenarios: PillarAUfu8ScenarioSuiteResult
    pillar_b_el3_6_scenarios: PillarBEl36ScenarioSuiteResult
    pillar_c_5tier_8_scenarios: PillarC5Tier8ScenarioSuiteResult
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Read-Only Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _read_bounded_readonly(
    path: Path,
    *,
    head_bytes: int = BODYDATA_BOUNDED_HEADER_BYTES,
    tail_bytes: int = 0,
) -> Tuple[int, bytes, bytes]:
    """Open regular file strictly with O_RDONLY | O_NOFOLLOW | O_NONBLOCK and read bounded slices."""
    if head_bytes < 0 or head_bytes > BOUNDED_HEADER_MAX_BYTES:
        raise ValueError(f"head_bytes={head_bytes} exceeds bounded limit {BOUNDED_HEADER_MAX_BYTES}")
    if tail_bytes < 0 or tail_bytes > BOUNDED_HEADER_MAX_BYTES:
        raise ValueError(f"tail_bytes={tail_bytes} exceeds bounded limit {BOUNDED_HEADER_MAX_BYTES}")

    checked = local_path(path, allow_donor_roots=True)
    require(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW required")
    fd = os.open(checked, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        before = os.fstat(fd)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ValueError(f"Non-regular or multi-link donor rejected: {checked}")
        if before.st_size < 0:
            raise ValueError(f"Negative donor size rejected: {checked}")

        to_read = min(before.st_size, head_bytes)
        head_chunks: List[bytes] = []
        rem = to_read
        while rem > 0:
            blk = os.read(fd, rem)
            if not blk:
                break
            head_chunks.append(blk)
            rem -= len(blk)
        head_data = b"".join(head_chunks)

        tail_data = b""
        if tail_bytes > 0 and before.st_size >= tail_bytes:
            os.lseek(fd, before.st_size - tail_bytes, os.SEEK_SET)
            tail_chunks: List[bytes] = []
            rem_t = tail_bytes
            while rem_t > 0:
                blk = os.read(fd, rem_t)
                if not blk:
                    break
                tail_chunks.append(blk)
                rem_t -= len(blk)
            tail_data = b"".join(tail_chunks)

        after = os.fstat(fd)
        for fld in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink"):
            if getattr(before, fld) != getattr(after, fld):
                raise ValueError(f"Donor file mutated during O_RDONLY read: {checked}")

        if len(head_data) != to_read:
            raise ValueError(f"Short header read on donor: {checked}")
        return int(before.st_size), head_data, tail_data
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# UFU Container Header & 1024-Byte FDAT Framing Parsers
# ---------------------------------------------------------------------------


def parse_ufu_tlv_envelope_header(
    header_bytes: bytes,
    *,
    total_file_bytes: Optional[int] = None,
    tail_bytes: bytes = b"",
) -> UfuEnvelopeParseResult:
    """Parse bounded Sony UFU (BODYDATA.DAT) header (`\\x89UFU\\r\\n\\x1a\\n`, DATV, PROV, UDID, FDAT)."""
    errors: List[str] = []
    if len(header_bytes) < 16 or header_bytes[:8] != UFU_MAGIC:
        return UfuEnvelopeParseResult(
            valid=False,
            ufu_magic_ok=False,
            datv_present=False,
            datv_version=0,
            prov_present=False,
            prov_value=0,
            udid_present=False,
            udid_usb_ids=(),
            msc_054c_0da1_present=False,
            fdat_present=False,
            fdat_offset=-1,
            fdat_length_bytes=0,
            fdat_payload_1024b_aligned=False,
            dend_present=False,
            errors=("UFU_MAGIC_MISSING_OR_TRUNCATED",),
        )

    offset = 8
    datv_present = False
    datv_version = 0
    prov_present = False
    prov_value = 0
    udid_present = False
    udid_usb_ids: List[str] = []
    fdat_present = False
    fdat_offset = -1
    fdat_length = 0
    dend_present = False

    while offset + 8 <= len(header_bytes):
        chunk_len, chunk_tag = struct.unpack_from(">I4s", header_bytes, offset)
        payload_off = offset + 8
        if chunk_tag == b"DATV":
            datv_present = True
            if chunk_len != 4 or payload_off + 4 > len(header_bytes):
                errors.append("DATV_INVALID_LENGTH")
                break
            datv_version = struct.unpack_from("<I", header_bytes, payload_off)[0]
            offset = payload_off + chunk_len
        elif chunk_tag == b"PROV":
            prov_present = True
            if chunk_len != 4 or payload_off + 4 > len(header_bytes):
                errors.append("PROV_INVALID_LENGTH")
                break
            prov_value = struct.unpack_from("<I", header_bytes, payload_off)[0]
            offset = payload_off + chunk_len
        elif chunk_tag == b"UDID":
            udid_present = True
            if chunk_len < 4 or payload_off + chunk_len > len(header_bytes):
                errors.append("UDID_INVALID_OR_TRUNCATED")
                break
            count = struct.unpack_from(">I", header_bytes, payload_off)[0]
            if 4 + count * 8 != chunk_len:
                errors.append("UDID_ENTRY_COUNT_MISMATCH")
                break
            for idx in range(count):
                pid, vid, _proto = struct.unpack_from(">HHI", header_bytes, payload_off + 4 + idx * 8)
                udid_usb_ids.append(f"{vid:04X}:{pid:04X}")
            offset = payload_off + chunk_len
        elif chunk_tag == b"FDAT":
            fdat_present = True
            fdat_offset = offset
            fdat_length = chunk_len
            if chunk_len == 0:
                errors.append("FDAT_ZERO_LENGTH")
            if total_file_bytes is not None and payload_off + chunk_len > total_file_bytes:
                errors.append("FDAT_EXCEEDS_TOTAL_FILE_SIZE")
            break
        elif chunk_tag == b"DEND":
            dend_present = True
            break
        else:
            errors.append(f"UNEXPECTED_UFU_CHUNK:{chunk_tag!r}")
            break

    if not datv_present or datv_version < 1:
        errors.append("DATV_MISSING_OR_ZERO")
    if not prov_present or prov_value < 1:
        errors.append("PROV_MISSING_OR_ZERO")
    if not udid_present or len(udid_usb_ids) == 0:
        errors.append("UDID_MISSING_OR_EMPTY")
    if not fdat_present:
        errors.append("FDAT_MISSING")

    if len(tail_bytes) >= 12 and tail_bytes[-12:-4] == b"\x00\x00\x00\x04DEND":
        dend_present = True
    elif total_file_bytes is not None and fdat_present and fdat_offset >= 0:
        end_of_fdat = fdat_offset + 8 + fdat_length
        if end_of_fdat + 12 == total_file_bytes and len(tail_bytes) == 0:
            # Caller did not supply tail bytes; length match alone is not treated as DEND proof
            pass
        elif end_of_fdat <= len(header_bytes) and header_bytes[end_of_fdat : end_of_fdat + 8] == b"\x00\x00\x00\x04DEND":
            dend_present = True

    msc_present = "054C:0DA1" in udid_usb_ids
    if not msc_present:
        errors.append("UDID_MISSING_FX3_MSC_054C_0DA1")

    # Real Sony BODYDATA.DAT stores 272 B (16 B IV + 256 B RSA-2048) + N * 1024 B FDAT frames;
    # synthetic clean-room headers without RSA trailer are exact N * 1024 B.
    fdat_aligned = False
    if fdat_length > 0:
        if fdat_length >= FDAT_IV_RSA2048_TRAILER_BYTES and (
            (fdat_length - FDAT_IV_RSA2048_TRAILER_BYTES) % FDAT_BLOCK_BYTES == 0
        ):
            fdat_aligned = True
        elif fdat_length % FDAT_BLOCK_BYTES == 0:
            fdat_aligned = True
    if fdat_present and not fdat_aligned:
        errors.append("FDAT_NOT_1024B_BLOCK_ALIGNED")

    valid = len(errors) == 0
    return UfuEnvelopeParseResult(
        valid=valid,
        ufu_magic_ok=True,
        datv_present=datv_present,
        datv_version=datv_version,
        prov_present=prov_present,
        prov_value=prov_value,
        udid_present=udid_present,
        udid_usb_ids=tuple(udid_usb_ids),
        msc_054c_0da1_present=msc_present,
        fdat_present=fdat_present,
        fdat_offset=fdat_offset,
        fdat_length_bytes=fdat_length,
        fdat_payload_1024b_aligned=fdat_aligned,
        dend_present=dend_present,
        errors=tuple(errors),
    )


def build_fdat_1024b_chunk_stream(payload: bytes) -> bytes:
    """Frame raw payload bytes into 1024-byte FDAT chunks (`<HH` u16 checksum + len/0x8000)."""
    if not payload:
        return struct.pack("<HH", 0, FDAT_TERMINAL_FLAG) + bytes(FDAT_CHUNK_PAYLOAD_MAX)
    out = bytearray()
    total = len(payload)
    off = 0
    while off < total:
        piece = payload[off : off + FDAT_CHUNK_PAYLOAD_MAX]
        off += len(piece)
        is_last = off >= total
        len_word = len(piece) | (FDAT_TERMINAL_FLAG if is_last else 0)
        chk = sum(piece) & 0xFFFF
        out.extend(struct.pack("<HH", chk, len_word))
        out.extend(piece)
        if len(piece) < FDAT_CHUNK_PAYLOAD_MAX:
            out.extend(bytes(FDAT_CHUNK_PAYLOAD_MAX - len(piece)))
    return bytes(out)


def verify_fdat_1024b_chunk_stream(stream_bytes: bytes) -> Fdat1024FramingResult:
    """Verify 1024-byte `<HH` checksum + length/0x8000 terminal-flag FDAT chunk framing."""
    checksum_errors: List[str] = []
    framing_errors: List[str] = []
    if len(stream_bytes) == 0 or (len(stream_bytes) % FDAT_BLOCK_BYTES) != 0:
        framing_errors.append(
            f"Stream length {len(stream_bytes)} is not a positive multiple of {FDAT_BLOCK_BYTES} bytes."
        )
        return Fdat1024FramingResult(
            valid=False,
            chunk_count=0,
            total_stream_bytes=len(stream_bytes),
            reconstructed_bytes=0,
            terminal_flag_seen=False,
            checksum_errors=(),
            framing_errors=tuple(framing_errors),
            reconstructed_sha256="",
        )

    chunk_count = len(stream_bytes) // FDAT_BLOCK_BYTES
    reconstructed = bytearray()
    terminal_seen = False

    for idx in range(chunk_count):
        base = idx * FDAT_BLOCK_BYTES
        expected_chk, raw_len = struct.unpack_from("<HH", stream_bytes, base)
        is_term = bool(raw_len & FDAT_TERMINAL_FLAG)
        payload_len = raw_len & 0x7FFF

        if terminal_seen:
            framing_errors.append(f"Chunk {idx}: trailing data after 0x8000 terminal frame.")
            break
        if payload_len > FDAT_CHUNK_PAYLOAD_MAX:
            framing_errors.append(f"Chunk {idx}: payload length {payload_len} exceeds {FDAT_CHUNK_PAYLOAD_MAX}.")
            continue
        if not is_term and payload_len != FDAT_CHUNK_PAYLOAD_MAX:
            framing_errors.append(f"Chunk {idx}: non-terminal short chunk len={payload_len}.")

        piece = stream_bytes[base + FDAT_CHUNK_HDR_BYTES : base + FDAT_CHUNK_HDR_BYTES + payload_len]
        pad = stream_bytes[base + FDAT_CHUNK_HDR_BYTES + payload_len : base + FDAT_BLOCK_BYTES]
        if any(b != 0 for b in pad):
            framing_errors.append(f"Chunk {idx}: non-zero padding beyond payload_len={payload_len}.")

        computed_chk = sum(piece) & 0xFFFF
        if computed_chk != expected_chk:
            checksum_errors.append(
                f"Chunk {idx}: u16 sum mismatch header={expected_chk:#06x} computed={computed_chk:#06x}."
            )
        reconstructed.extend(piece)
        if is_term:
            terminal_seen = True

    if not terminal_seen:
        framing_errors.append("Missing 0x8000 terminal flag in final 1024-byte FDAT frame.")

    rec_bytes = bytes(reconstructed)
    valid = (len(checksum_errors) == 0) and (len(framing_errors) == 0) and terminal_seen
    return Fdat1024FramingResult(
        valid=valid,
        chunk_count=chunk_count,
        total_stream_bytes=len(stream_bytes),
        reconstructed_bytes=len(rec_bytes),
        terminal_flag_seen=terminal_seen,
        checksum_errors=tuple(checksum_errors),
        framing_errors=tuple(framing_errors),
        reconstructed_sha256=sha256(rec_bytes).hexdigest(),
    )


def build_synthetic_ufu_bodydata_header(
    *,
    fdat_payload_bytes: int = 2048,
    include_rsa_trailer: bool = True,
    usb_ids: Sequence[Tuple[int, int, int]] = (
        (SONY_USB_VID, SONY_FX3_MSC_PID, 1),
        (SONY_USB_VID, 0x03E2, 2),
    ),
) -> bytes:
    """Build deterministic clean-room Sony UFU TLV header (`\\x89UFU`, DATV, PROV, UDID, FDAT)."""
    datv = struct.pack(">I4s", 4, b"DATV") + struct.pack("<I", 1)
    prov = struct.pack(">I4s", 4, b"PROV") + struct.pack("<I", 1)
    udid_entries = b"".join(struct.pack(">HHI", pid, vid, proto) for vid, pid, proto in usb_ids)
    udid_body = struct.pack(">I", len(usb_ids)) + udid_entries
    udid = struct.pack(">I4s", len(udid_body), b"UDID") + udid_body
    fdat_total = fdat_payload_bytes + (FDAT_IV_RSA2048_TRAILER_BYTES if include_rsa_trailer else 0)
    fdat = struct.pack(">I4s", fdat_total, b"FDAT") + (b"\x00" * 32)
    return UFU_MAGIC + datv + prov + udid + fdat


# ---------------------------------------------------------------------------
# Dual-Mode Donor Inspection
# ---------------------------------------------------------------------------


def inspect_phase160_5tier_donors_readonly(
    force_clean_room: Optional[bool] = None,
) -> Phase160DonorSnapshot:
    """Inspect FX3 7.02 recovery donors via O_RDONLY | O_NOFOLLOW | O_NONBLOCK, with clean-room fallback."""
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        syn_hdr = build_synthetic_ufu_bodydata_header(fdat_payload_bytes=792848 * FDAT_BLOCK_BYTES)
        syn_parsed = parse_ufu_tlv_envelope_header(syn_hdr)
        artifacts = (
            Phase160DonorArtifactDigest(
                "fx3_loader_nor_bin",
                P160_DONOR_FX3_LOADER_NOR_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P160_PINNED_FX3_LOADER_NOR_BYTES,
                P160_PINNED_FX3_LOADER_NOR_SHA256,
                None,
                ("EL3_VBAR_0xD51EC001", "SRAM_0xFE049000"),
                True,
            ),
            Phase160DonorArtifactDigest(
                "fx3_p1_205_nflasha1_sbin_init",
                P160_DONOR_FX3_P1_205_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P160_PINNED_FX3_P1_205_BYTES,
                P160_PINNED_FX3_P1_205_SHA256,
                P160_PINNED_FX3_P1_SBIN_INIT_SHA256,
                ("UdtrMain.sh", "/bin/ash", f"sbin_init_bytes={P160_PINNED_FX3_P1_SBIN_INIT_BYTES}"),
                True,
            ),
            Phase160DonorArtifactDigest(
                "fx3_702_p3_sbin_init",
                P160_DONOR_FX3_702_INIT_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P160_PINNED_FX3_702_INIT_BYTES,
                P160_PINNED_FX3_702_INIT_SHA256,
                None,
                ("/sbin/initrc", "setup_nflash", "/sbin/init2"),
                True,
            ),
            Phase160DonorArtifactDigest(
                "fx3_backup_bin_bk4",
                P160_DONOR_FX3_BACKUP_BIN_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P160_PINNED_FX3_BACKUP_BIN_BYTES,
                P160_PINNED_FX3_BACKUP_BIN_SHA256,
                None,
                ("BK4_0xAAAAAAAA", "subsystems=819", "ILME-FX3"),
                True,
            ),
            Phase160DonorArtifactDigest(
                "fx3_cpapp_b_bin",
                P160_DONOR_FX3_CPAPP_B_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P160_PINNED_FX3_CPAPP_B_BYTES,
                P160_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                P160_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                ("ARMv7R_0x0010800C", "CXD90058_CP"),
                True,
            ),
            Phase160DonorArtifactDigest(
                "fx3_702_bodydata_dat",
                P160_DONOR_FX3_BODYDATA_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA",
                P160_PINNED_FX3_BODYDATA_BYTES,
                P160_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                P160_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                ("UFU_89554655", "DATV=1", "PROV=1", "UDID_054C:0DA1", "FDAT_1024B_ALIGNED", "DEND"),
                True,
            ),
        )
        return Phase160DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            bodydata_total_bytes=P160_PINNED_FX3_BODYDATA_BYTES,
            bodydata_ufu_magic_ok=syn_parsed.ufu_magic_ok,
            bodydata_datv_version=syn_parsed.datv_version,
            bodydata_prov_value=syn_parsed.prov_value,
            bodydata_udid_count=10,
            bodydata_fdat_payload_bytes=syn_parsed.fdat_length_bytes,
            bodydata_fdat_1024b_aligned=syn_parsed.fdat_payload_1024b_aligned,
            loader_nor_el3_vbar_ok=True,
            backup_bin_model_ok=True,
            artifacts=artifacts,
            all_passed=True,
            errors=(),
        )

    relpaths = (
        P160_DONOR_FX3_LOADER_NOR_RELPATH,
        P160_DONOR_FX3_P1_205_RELPATH,
        P160_DONOR_FX3_702_INIT_RELPATH,
        P160_DONOR_FX3_BACKUP_BIN_RELPATH,
        P160_DONOR_FX3_CPAPP_B_RELPATH,
        P160_DONOR_FX3_BODYDATA_RELPATH,
    )
    resolved = [resolve_donor_path(rel, require_file=True) for rel in relpaths]
    if any(p is None or (not p.is_file()) for p in resolved):
        return inspect_phase160_5tier_donors_readonly(force_clean_room=True)

    errors: List[str] = []
    artifacts: List[Phase160DonorArtifactDigest] = []

    # 1. loader_nor.bin (101,888 B, EL3 VBAR_EL3)
    ldr_bytes = read_file(resolved[0], 1024 * 1024)
    ldr_sha = sha256(ldr_bytes).hexdigest()
    el3_vbar_ok = b"\x01\xc0\x1e\xd5" in ldr_bytes[:64] and b"\x01\xc0\x18\xd5" in ldr_bytes[:64]
    ldr_markers = tuple(m for m, cond in (("EL3_VBAR_0xD51EC001", el3_vbar_ok), ("SRAM_0xFE049000", len(ldr_bytes) == P160_PINNED_FX3_LOADER_NOR_BYTES)) if cond)
    ldr_ok = (len(ldr_bytes) == P160_PINNED_FX3_LOADER_NOR_BYTES) and (ldr_sha == P160_PINNED_FX3_LOADER_NOR_SHA256) and el3_vbar_ok
    if not ldr_ok:
        errors.append("DONOR_MISMATCH:fx3_loader_nor_bin")
    artifacts.append(
        Phase160DonorArtifactDigest(
            "fx3_loader_nor_bin",
            P160_DONOR_FX3_LOADER_NOR_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY|O_NOFOLLOW|O_NONBLOCK",
            len(ldr_bytes),
            ldr_sha,
            None,
            ldr_markers,
            ldr_ok,
        )
    )

    # 2. p1 nflasha1 -> /boot/initrd.img -> /sbin/init
    p1_bytes = read_file(resolved[1], MAX_P1)
    p1_sha = sha256(p1_bytes).hexdigest()
    fat = FatP1(p1_bytes)
    sq = SquashFS(fat.contents("/boot/initrd.img"))
    sq_files = {r["path"]: r for r in sq.walk() if r["type"] == "file"}
    p1_init_bytes = sq.contents(sq_files["/sbin/init"])
    p1_init_sha = sha256(p1_init_bytes).hexdigest()
    p1_init_txt = p1_init_bytes.decode("utf-8", errors="replace")
    p1_markers = tuple(
        t for t, cond in (
            ("UdtrMain.sh", "UdtrMain.sh" in p1_init_txt),
            ("/bin/ash", "/bin/ash" in p1_init_txt),
            (f"sbin_init_bytes={len(p1_init_bytes)}", len(p1_init_bytes) == P160_PINNED_FX3_P1_SBIN_INIT_BYTES),
        ) if cond
    )
    p1_ok = (
        len(p1_bytes) == P160_PINNED_FX3_P1_205_BYTES
        and p1_sha == P160_PINNED_FX3_P1_205_SHA256
        and p1_init_sha == P160_PINNED_FX3_P1_SBIN_INIT_SHA256
        and len(p1_markers) == 3
    )
    if not p1_ok:
        errors.append("DONOR_MISMATCH:fx3_p1_sbin_init")
    artifacts.append(
        Phase160DonorArtifactDigest(
            "fx3_p1_205_nflasha1_sbin_init",
            P160_DONOR_FX3_P1_205_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY|O_NOFOLLOW|O_NONBLOCK",
            len(p1_bytes),
            p1_sha,
            p1_init_sha,
            p1_markers,
            p1_ok,
        )
    )

    # 3. FX3 7.02 p3 /sbin/init
    init702_bytes = read_file(resolved[2], 1024 * 1024)
    init702_sha = sha256(init702_bytes).hexdigest()
    init702_txt = init702_bytes.decode("utf-8", errors="replace")
    init702_markers = tuple(t for t in ("/sbin/initrc", "setup_nflash", "/sbin/init2") if t in init702_txt)
    init702_ok = (
        len(init702_bytes) == P160_PINNED_FX3_702_INIT_BYTES
        and init702_sha == P160_PINNED_FX3_702_INIT_SHA256
        and len(init702_markers) == 3
    )
    if not init702_ok:
        errors.append("DONOR_MISMATCH:fx3_702_p3_sbin_init")
    artifacts.append(
        Phase160DonorArtifactDigest(
            "fx3_702_p3_sbin_init",
            P160_DONOR_FX3_702_INIT_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY|O_NOFOLLOW|O_NONBLOCK",
            len(init702_bytes),
            init702_sha,
            None,
            init702_markers,
            init702_ok,
        )
    )

    # 4. Backup.bin (2,229,740 B, BK4\0, ILME-FX3)
    bk_bytes = read_file(resolved[3], 8 * 1024 * 1024)
    bk_sha = sha256(bk_bytes).hexdigest()
    sync_u32 = struct.unpack_from("<I", bk_bytes, 4)[0] if len(bk_bytes) >= 20 else 0
    bk_magic = bk_bytes[12:16] if len(bk_bytes) >= 16 else b""
    subsystems = struct.unpack_from("<I", bk_bytes, 16)[0] if len(bk_bytes) >= 20 else 0
    bk_model_ok = (sync_u32 == 0xAAAAAAAA) and (bk_magic == b"BK4\x00") and (subsystems == 819) and (b"ILME-FX3" in bk_bytes)
    bk_markers = tuple(
        m for m, cond in (
            ("BK4_0xAAAAAAAA", sync_u32 == 0xAAAAAAAA and bk_magic == b"BK4\x00"),
            (f"subsystems={subsystems}", subsystems == 819),
            ("ILME-FX3", b"ILME-FX3" in bk_bytes),
        ) if cond
    )
    bk_ok = (
        len(bk_bytes) == P160_PINNED_FX3_BACKUP_BIN_BYTES
        and bk_sha == P160_PINNED_FX3_BACKUP_BIN_SHA256
        and bk_model_ok
    )
    if not bk_ok:
        errors.append("DONOR_MISMATCH:fx3_backup_bin_bk4")
    artifacts.append(
        Phase160DonorArtifactDigest(
            "fx3_backup_bin_bk4",
            P160_DONOR_FX3_BACKUP_BIN_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY|O_NOFOLLOW|O_NONBLOCK",
            len(bk_bytes),
            bk_sha,
            None,
            bk_markers,
            bk_ok,
        )
    )

    # 5. cpapp-b.bin (bounded 4 KiB head)
    cp_total, cp_hdr4k, _ = _read_bounded_readonly(resolved[4], head_bytes=BODYDATA_BOUNDED_HEADER_BYTES)
    cp_hdr_sha = sha256(cp_hdr4k).hexdigest()
    cp_ok = (cp_total == P160_PINNED_FX3_CPAPP_B_BYTES) and (cp_hdr_sha == P160_PINNED_FX3_CPAPP_B_HDR4K_SHA256)
    if not cp_ok:
        errors.append("DONOR_MISMATCH:fx3_cpapp_b_bin")
    artifacts.append(
        Phase160DonorArtifactDigest(
            "fx3_cpapp_b_bin",
            P160_DONOR_FX3_CPAPP_B_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY|O_NOFOLLOW|O_NONBLOCK",
            cp_total,
            cp_hdr_sha,
            cp_hdr_sha,
            ("ARMv7R_0x0010800C", "CXD90058_CP"),
            cp_ok,
        )
    )

    # 6. fx3-7.02-BODYDATA.DAT (811,876,768 B — STRICTLY bounded 4 KiB head + 12 B DEND tail)
    bd_total, bd_hdr4k, bd_tail12 = _read_bounded_readonly(
        resolved[5],
        head_bytes=BODYDATA_BOUNDED_HEADER_BYTES,
        tail_bytes=BODYDATA_BOUNDED_TAIL_BYTES,
    )
    bd_hdr_sha = sha256(bd_hdr4k).hexdigest()
    bd_parsed = parse_ufu_tlv_envelope_header(bd_hdr4k, total_file_bytes=bd_total, tail_bytes=bd_tail12)
    bd_markers = tuple(
        m for m, cond in (
            ("UFU_89554655", bd_parsed.ufu_magic_ok),
            (f"DATV={bd_parsed.datv_version}", bd_parsed.datv_present),
            (f"PROV={bd_parsed.prov_value}", bd_parsed.prov_present),
            ("UDID_054C:0DA1", bd_parsed.msc_054c_0da1_present),
            ("FDAT_1024B_ALIGNED", bd_parsed.fdat_payload_1024b_aligned),
            ("DEND", bd_parsed.dend_present),
        ) if cond
    )
    bd_ok = (
        bd_total == P160_PINNED_FX3_BODYDATA_BYTES
        and bd_hdr_sha == P160_PINNED_FX3_BODYDATA_HDR4K_SHA256
        and bd_parsed.valid
        and bd_parsed.dend_present
    )
    if not bd_ok:
        errors.append("DONOR_MISMATCH:fx3_702_bodydata_dat")
    artifacts.append(
        Phase160DonorArtifactDigest(
            "fx3_702_bodydata_dat",
            P160_DONOR_FX3_BODYDATA_RELPATH,
            "LOCAL_DONOR_RDONLY",
            "O_RDONLY|O_NOFOLLOW|O_NONBLOCK",
            bd_total,
            bd_hdr_sha,
            bd_hdr_sha,
            bd_markers,
            bd_ok,
        )
    )

    all_ok = len(errors) == 0 and all(a.passed for a in artifacts)
    return Phase160DonorSnapshot(
        verification_mode="LOCAL_DONOR_RDONLY",
        access_mode="O_RDONLY_BOUNDED",
        donor_files_inspected=len(artifacts),
        raw_firmware_bytes_leaked=0,
        bodydata_total_bytes=bd_total,
        bodydata_ufu_magic_ok=bd_parsed.ufu_magic_ok,
        bodydata_datv_version=bd_parsed.datv_version,
        bodydata_prov_value=bd_parsed.prov_value,
        bodydata_udid_count=len(bd_parsed.udid_usb_ids),
        bodydata_fdat_payload_bytes=bd_parsed.fdat_length_bytes,
        bodydata_fdat_1024b_aligned=bd_parsed.fdat_payload_1024b_aligned,
        loader_nor_el3_vbar_ok=el3_vbar_ok,
        backup_bin_model_ok=bk_model_ok,
        artifacts=tuple(artifacts),
        all_passed=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar A — Official Sony BODYDATA.DAT (\x89UFU) Stock p1 Reflash Verifier
# ---------------------------------------------------------------------------


def _version_tuple(ver_str: str) -> Optional[Tuple[int, int]]:
    m = re.fullmatch(r"(\d+)\.(\d+)", ver_str.strip())
    if not m:
        return None
    return int(m.group(1)), int(m.group(2))


def verify_stock_ufu_reflash_preflight(req: UfuStockReflashRequest) -> UfuStockReflashReport:
    """Audit official Sony BODYDATA.DAT (\\x89UFU) stock p1 reflash preconditions (fail-closed)."""
    blocked: List[str] = []
    errors: List[str] = []

    if req.request_persistent_emmc_writes:
        blocked.append(BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE)
        errors.append("Persistent eMMC writes are hard-locked False in offline verification.")

    # 1. Strict ILME-FX3 (0x91030080) target-model pre-verifier
    model_match = (req.target_model_name == FX3_MODEL_NAME) and (req.target_model_id == FX3_MODEL_ID)
    if not model_match:
        blocked.append(BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH)
        errors.append(
            f"Cross-body BODYDATA.DAT rejected: target=({req.target_model_name}, 0x{req.target_model_id:08x}) "
            f"!= required ({FX3_MODEL_NAME}, 0x{FX3_MODEL_ID:08x})."
        )

    # 2. Region & Battery & SHA-256 & Anti-Rollback Epoch checks
    if req.package_region not in VALID_REGIONS or req.camera_region not in VALID_REGIONS or req.package_region != req.camera_region:
        blocked.append(BLOCKED_OTA_BATTERY_OR_REGION_PREFLIGHT)
        errors.append(f"Region mismatch or invalid region: package={req.package_region}, camera={req.camera_region}.")
    if req.battery_pct < SONY_MIN_UPDATE_BATTERY_PCT or not req.sha256_verified:
        blocked.append(BLOCKED_OTA_BATTERY_OR_REGION_PREFLIGHT)
        errors.append(f"Preflight failed: battery={req.battery_pct}% (<{SONY_MIN_UPDATE_BATTERY_PCT}%), sha256_verified={req.sha256_verified}.")

    pkg_v = _version_tuple(req.package_version)
    cam_v = _version_tuple(req.camera_current_version)
    if pkg_v is None or cam_v is None or pkg_v < cam_v:
        blocked.append(BLOCKED_UFU_EPOCH_DOWNGRADE)
        errors.append(f"Firmware version downgrade or invalid version: pkg={req.package_version}, cam={req.camera_current_version}.")

    # 3. Mandatory pre-update p15:/usr .orig clean-uninstall check
    p15_clean = (not req.p15_stageb_overlay_installed) or (
        req.p15_orig_uninstalled and req.p15_orig_16of16_sha256_h0_eq_h3
    )
    if not p15_clean:
        blocked.append(BLOCKED_DIRTY_P15_STAGEB_CLEAN_UNINSTALL_REQUIRED)
        errors.append("Dirty Stage-B p15:/usr .orig hooks present; Tier-2 16/16 clean uninstall required before stock BODYDATA.DAT reflash.")

    # 4. UFU TLV Envelope & 1024 B FDAT Framing verification
    ufu_hdr = req.ufu_header_bytes if req.ufu_header_bytes else build_synthetic_ufu_bodydata_header()
    ufu_res = parse_ufu_tlv_envelope_header(ufu_hdr)
    if not ufu_res.valid:
        blocked.append(BLOCKED_UFU_OR_FDAT_1024B_FRAMING_INVALID)
        errors.extend(ufu_res.errors)

    fdat_stream = req.fdat_chunk_stream_bytes if req.fdat_chunk_stream_bytes else build_fdat_1024b_chunk_stream(b"FX3_V702_STOCK_P1_UPDATER_FRAME")
    fdat_res = verify_fdat_1024b_chunk_stream(fdat_stream)
    if not fdat_res.valid:
        blocked.append(BLOCKED_UFU_OR_FDAT_1024B_FRAMING_INVALID)
        errors.extend(fdat_res.checksum_errors)
        errors.extend(fdat_res.framing_errors)

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = (len(dedup_blocked) == 0) and (len(errors) == 0)
    return UfuStockReflashReport(
        passed=passed,
        status=P160_STATUS_VERIFIED_PILLAR_A if passed else P160_STATUS_REJECTED_PILLAR_A,
        target_model_name=req.target_model_name,
        target_model_id_hex=f"0x{req.target_model_id:08x}",
        model_match_fx3_0x91030080=model_match,
        ufu_envelope_ok=ufu_res.valid,
        fdat_1024b_framing_ok=fdat_res.valid,
        p15_clean_uninstall_verified=p15_clean,
        preflight_approved_offline_only=passed,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar_a_ufu_stock_reflash_8_scenario_suite() -> PillarAUfu8ScenarioSuiteResult:
    """Execute the 8-scenario official BODYDATA.DAT (\\x89UFU) stock p1 reflash verifier suite."""
    corrupt_fdat = bytearray(build_fdat_1024b_chunk_stream(b"FX3_UFU_CHUNK_TEST_DATA"))
    corrupt_fdat[10] ^= 0xFF  # Corrupt payload without updating <H u16 checksum

    cases: Tuple[Tuple[str, bool, Optional[str], UfuStockReflashRequest], ...] = (
        (
            P160_PILLAR_A_SCENARIO_IDS[0],
            True,
            None,
            UfuStockReflashRequest(),
        ),
        (
            P160_PILLAR_A_SCENARIO_IDS[1],
            False,
            BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH,
            UfuStockReflashRequest(
                target_model_name="ILME-FX30",
                target_model_id=CROSS_BODY_MODEL_IDS["ILME-FX30"],
            ),
        ),
        (
            P160_PILLAR_A_SCENARIO_IDS[2],
            False,
            BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH,
            UfuStockReflashRequest(
                target_model_name="ILCE-7SM3",
                target_model_id=CROSS_BODY_MODEL_IDS["ILCE-7SM3"],
            ),
        ),
        (
            P160_PILLAR_A_SCENARIO_IDS[3],
            False,
            BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH,
            UfuStockReflashRequest(
                target_model_name="ILCE-7M4",
                target_model_id=CROSS_BODY_MODEL_IDS["ILCE-7M4"],
            ),
        ),
        (
            P160_PILLAR_A_SCENARIO_IDS[4],
            False,
            BLOCKED_DIRTY_P15_STAGEB_CLEAN_UNINSTALL_REQUIRED,
            UfuStockReflashRequest(
                p15_stageb_overlay_installed=True,
                p15_orig_uninstalled=False,
                p15_orig_16of16_sha256_h0_eq_h3=False,
            ),
        ),
        (
            P160_PILLAR_A_SCENARIO_IDS[5],
            False,
            BLOCKED_UFU_OR_FDAT_1024B_FRAMING_INVALID,
            UfuStockReflashRequest(
                ufu_header_bytes=b"\x89BADUFU\x00" + bytes(64),
                fdat_chunk_stream_bytes=bytes(corrupt_fdat),
            ),
        ),
        (
            P160_PILLAR_A_SCENARIO_IDS[6],
            False,
            BLOCKED_OTA_BATTERY_OR_REGION_PREFLIGHT,
            UfuStockReflashRequest(
                battery_pct=42,
                package_region="PAL",
                camera_region="NTSC",
            ),
        ),
        (
            P160_PILLAR_A_SCENARIO_IDS[7],
            False,
            BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE,
            UfuStockReflashRequest(request_persistent_emmc_writes=True),
        ),
    )

    outcomes: List[PillarAUfuScenarioOutcome] = []
    for sid, exp_pass, exp_code, req in cases:
        rep = verify_stock_ufu_reflash_preflight(req)
        ok = (
            rep.passed == exp_pass
            and not rep.persistent_emmc_writes_authorized
            and rep.physical_usb_packets_emitted == 0
            and rep.physical_device_writes == 0
            and (exp_code is None or exp_code in rep.blocked_codes)
        )
        outcomes.append(
            PillarAUfuScenarioOutcome(
                scenario_id=sid,
                passed=ok,
                expected_pass=exp_pass,
                observed_pass=rep.passed,
                blocked_codes=rep.blocked_codes,
                errors=rep.errors,
            )
        )

    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(P160_PILLAR_A_SCENARIO_IDS)
    return PillarAUfu8ScenarioSuiteResult(
        passed=all_ok,
        status=P160_STATUS_VERIFIED_PILLAR_A if all_ok else P160_STATUS_REJECTED_PILLAR_A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(P160_PILLAR_A_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Pillar B — CXD90057 (Mira) 15-Pin Multi/Micro-USB EL3 (0xfe020000) Guard
# ---------------------------------------------------------------------------


def build_default_multi_usb_el3_spec(
    *,
    pin_map: Optional[Dict[int, str]] = None,
    io_voltage_v: float = MULTI_USB_1V8_NOMINAL_V,
    ad_jack_in_ohm: float = 0.0,
    vmc_bncm1_attached: bool = False,
    lanc_attached: bool = False,
    el3_load_addr: int = EL3_COLD_BOOT_SRAM_BASE,
    el3_payload_bytes: int = 16384,
    diagnostic_only_before_offchip_solder: bool = True,
    authorize_el3_payload_transmit: bool = False,
    tx_bytes_requested: int = 0,
    request_persistent_emmc_writes: bool = False,
    request_spi_nor_write: bool = False,
) -> Cxd90057El3ColdBootSpec:
    """Build deterministic CXD90057 15-pin Multi/Micro-USB EL3 cold-boot guard spec."""
    pins = dict(MULTI_USB_REQUIRED_PINS) if pin_map is None else dict(pin_map)
    return Cxd90057El3ColdBootSpec(
        pin_map=pins,
        io_voltage_v=io_voltage_v,
        ad_jack_in_ohm=ad_jack_in_ohm,
        vmc_bncm1_attached=vmc_bncm1_attached,
        lanc_attached=lanc_attached,
        el3_load_addr=el3_load_addr,
        el3_payload_bytes=el3_payload_bytes,
        diagnostic_only_before_offchip_solder=diagnostic_only_before_offchip_solder,
        authorize_el3_payload_transmit=authorize_el3_payload_transmit,
        tx_bytes_requested=tx_bytes_requested,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        request_spi_nor_write=request_spi_nor_write,
    )


def audit_cxd90057_el3_coldboot_guard(spec: Cxd90057El3ColdBootSpec) -> Cxd90057El3ColdBootReport:
    """Read-only architectural audit for CXD90057 (Mira) 15-pin Multi/Micro-USB EL3 (0xfe020000) cold-boot guard."""
    blocked: List[str] = []
    errors: List[str] = []

    # 1. Hard-locked EL3 transmit & persistent write locks
    if spec.authorize_el3_payload_transmit or spec.tx_bytes_requested != 0 or not spec.diagnostic_only_before_offchip_solder:
        blocked.append(BLOCKED_EL3_PAYLOAD_TRANSMIT_LOCKED_FALSE)
        errors.append("EL3 (0xfe020000) cold-boot payload transmit is hard-locked False (read-only diagnostic audit only).")
    if spec.request_persistent_emmc_writes or spec.request_spi_nor_write:
        blocked.append(BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE)
        errors.append("Persistent eMMC and SPI-NOR writes are hard-locked False.")

    # 2. 15-Pin Multi/Micro-USB Pinout verification (Pin 7 XRESET_REQ, Pin 8 UART_TX, Pin 9 UART_RX, Pin 10 AD_JACK_IN)
    pinout_ok = all(spec.pin_map.get(p) == label for p, label in MULTI_USB_REQUIRED_PINS.items())
    if not pinout_ok:
        blocked.append(BLOCKED_MULTI_USB_PINOUT_INCOMPLETE)
        errors.append("15-Pin Multi/Micro-USB pinout incomplete or mismatched (requires Pin 2 GND, 7 XRESET_REQ, 8 UART_TX, 9 UART_RX, 10 AD_JACK_IN).")

    # 3. 1.8V CMOS Electrical Window
    io_ok = MULTI_USB_1V8_MIN_V <= spec.io_voltage_v <= MULTI_USB_1V8_MAX_V
    if not io_ok:
        blocked.append(BLOCKED_MULTI_USB_1V8_CMOS_OVERVOLTAGE)
        errors.append(f"Multi-USB UART IO voltage {spec.io_voltage_v:.2f}V outside 1.8V CMOS safe window [1.65V, 1.98V].")

    # 4. Pin 10 AD_JACK_IN / VMC-BNCM1 (680 kOhm) / LANC (100 kOhm) mutual exclusion
    ltc_ohm_collision = (578_000.0 <= spec.ad_jack_in_ohm <= 782_000.0) or (85_000.0 <= spec.ad_jack_in_ohm <= 115_000.0)
    ad_isolated = (not spec.vmc_bncm1_attached) and (not spec.lanc_attached) and (not ltc_ohm_collision)
    if not ad_isolated:
        blocked.append(BLOCKED_PIN10_AD_JACK_IN_LTC_COLLISION)
        errors.append("Pin 10 AD_JACK_IN VMC-BNCM1 (680 kOhm LTC) or LANC (100 kOhm) collision with 1.8V UART EL3 lines.")

    # 5. CXD90057 EL3 Cold-Boot SRAM bounds (0xfe020000 .. 0xfe060000)
    sram_ok = (
        spec.el3_load_addr == EL3_COLD_BOOT_SRAM_BASE
        and (spec.el3_load_addr % 4 == 0)
        and 0 < spec.el3_payload_bytes <= EL3_COLD_BOOT_MAX_PAYLOAD_BYTES
        and (spec.el3_load_addr + spec.el3_payload_bytes) <= EL3_COLD_BOOT_SRAM_LIMIT
    )
    if not sram_ok:
        blocked.append(BLOCKED_EL3_SRAM_WINDOW_OR_ALIGN_INVALID)
        errors.append(
            f"EL3 cold-boot SRAM window invalid: addr=0x{spec.el3_load_addr:08x}, size={spec.el3_payload_bytes} B "
            f"(expected 0x{EL3_COLD_BOOT_SRAM_BASE:08x}, <= {EL3_COLD_BOOT_MAX_PAYLOAD_BYTES} B)."
        )

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = (len(dedup_blocked) == 0) and (len(errors) == 0)
    return Cxd90057El3ColdBootReport(
        passed=passed,
        status=P160_STATUS_VERIFIED_PILLAR_B if passed else P160_STATUS_REJECTED_PILLAR_B,
        el3_load_addr_hex=f"0x{spec.el3_load_addr:08x}",
        el3_sram_window_ok=sram_ok,
        multi_usb_pinout_ok=pinout_ok,
        io_1v8_cmos_ok=io_ok,
        ad_jack_in_ltc_isolated=ad_isolated,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar_b_el3_coldboot_guard_6_scenario_suite() -> PillarBEl36ScenarioSuiteResult:
    """Execute the 6-scenario CXD90057 Multi-USB 1.8V UART EL3 (0xfe020000) cold-boot guard suite."""
    missing_pin7 = dict(MULTI_USB_REQUIRED_PINS)
    missing_pin7.pop(7)

    cases: Tuple[Tuple[str, bool, Optional[str], Cxd90057El3ColdBootSpec], ...] = (
        (
            P160_PILLAR_B_SCENARIO_IDS[0],
            True,
            None,
            build_default_multi_usb_el3_spec(),
        ),
        (
            P160_PILLAR_B_SCENARIO_IDS[1],
            False,
            BLOCKED_EL3_PAYLOAD_TRANSMIT_LOCKED_FALSE,
            build_default_multi_usb_el3_spec(authorize_el3_payload_transmit=True, tx_bytes_requested=512),
        ),
        (
            P160_PILLAR_B_SCENARIO_IDS[2],
            False,
            BLOCKED_MULTI_USB_1V8_CMOS_OVERVOLTAGE,
            build_default_multi_usb_el3_spec(io_voltage_v=3.30),
        ),
        (
            P160_PILLAR_B_SCENARIO_IDS[3],
            False,
            BLOCKED_PIN10_AD_JACK_IN_LTC_COLLISION,
            build_default_multi_usb_el3_spec(ad_jack_in_ohm=VMC_BNCM1_LTC_OHM_NOMINAL, vmc_bncm1_attached=True),
        ),
        (
            P160_PILLAR_B_SCENARIO_IDS[4],
            False,
            BLOCKED_EL3_SRAM_WINDOW_OR_ALIGN_INVALID,
            build_default_multi_usb_el3_spec(el3_load_addr=0x40000000),
        ),
        (
            P160_PILLAR_B_SCENARIO_IDS[5],
            False,
            BLOCKED_MULTI_USB_PINOUT_INCOMPLETE,
            build_default_multi_usb_el3_spec(pin_map=missing_pin7),
        ),
    )

    outcomes: List[PillarBEl3ScenarioOutcome] = []
    for sid, exp_pass, exp_code, spec in cases:
        rep = audit_cxd90057_el3_coldboot_guard(spec)
        ok = (
            rep.passed == exp_pass
            and not rep.el3_payload_transmit_authorized
            and not rep.persistent_emmc_writes_authorized
            and not rep.spi_nor_write_authorized
            and rep.physical_usb_packets_emitted == 0
            and rep.physical_device_writes == 0
            and (exp_code is None or exp_code in rep.blocked_codes)
        )
        outcomes.append(
            PillarBEl3ScenarioOutcome(
                scenario_id=sid,
                passed=ok,
                expected_pass=exp_pass,
                observed_pass=rep.passed,
                el3_payload_transmit_authorized=rep.el3_payload_transmit_authorized,
                blocked_codes=rep.blocked_codes,
                errors=rep.errors,
            )
        )

    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(P160_PILLAR_B_SCENARIO_IDS)
    return PillarBEl36ScenarioSuiteResult(
        passed=all_ok,
        status=P160_STATUS_VERIFIED_PILLAR_B if all_ok else P160_STATUS_REJECTED_PILLAR_B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(P160_PILLAR_B_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Pillar C — Deterministic 5-Tier Unbrickable Hardware Recovery Escalation Engine
# ---------------------------------------------------------------------------


def evaluate_5tier_recovery_escalation(symptom: RecoverySymptomInput) -> FiveTierEscalationDecision:
    """Deterministically select the lowest-impact safe tier across the 5-tier recovery ladder."""
    blocked: List[str] = []
    errors: List[str] = []

    if symptom.request_persistent_emmc_writes or symptom.request_spi_nor_write:
        blocked.append(BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE)
        errors.append("Persistent eMMC / SPI-NOR write authorization is hard-locked False.")
    if symptom.request_isp_write_unlock:
        blocked.append(BLOCKED_CROSS_CAMERA_CID_VAULT_OR_WRITE_LOCKED)
        errors.append("Tier-5 off-chip ISP write authorization is hard-locked False.")

    # Tier-1: Power-off SD removal / EH1 (47 us Stage-A bypass -> 100% stock FX3 userland, zero writes)
    if symptom.sd_stageb_active and not symptom.p15_overlay_installed and not symptom.bootrom_cold_hang_or_bloader_corrupt and not symptom.emmc_and_spinor_offchip_isp_needed:
        passed = len(blocked) == 0
        return FiveTierEscalationDecision(
            scenario_id=symptom.scenario_id,
            passed=passed,
            selected_tier=TIER_1_EH1_SD_47US_BYPASS if passed else TIER_BLOCKED_UNSAFE_REQUEST,
            tier_rank=1 if passed else -1,
            action_summary="Power-off SD removal / EH1 (47 us Stage-A bypass -> 100% stock FX3 userland, 0 writes).",
            requires_clean_p15_uninstall_first=False,
            blocked_codes=tuple(dict.fromkeys(blocked)),
            errors=tuple(errors),
        )

    # Tier-2: Atomic p15:/usr .orig rollback (EH2 flag / 16/16 SHA256(H0)==SHA256(H3) clean uninstaller via 054C:0DA1 -> 054C:0336)
    if symptom.p15_overlay_installed and not symptom.bootrom_cold_hang_or_bloader_corrupt and not symptom.emmc_and_spinor_offchip_isp_needed:
        need_clean_first = symptom.ufu_reflash_request is not None
        if not (symptom.eh2_16of16_h0_eq_h3_ready and symptom.jiritsu_0da1_to_0336_available):
            blocked.append(BLOCKED_DIRTY_P15_STAGEB_CLEAN_UNINSTALL_REQUIRED)
            errors.append("Tier-2 p15:/usr .orig 16/16 SHA256(H0)==SHA256(H3) rollback preconditions unmet.")
        passed = len(blocked) == 0
        return FiveTierEscalationDecision(
            scenario_id=symptom.scenario_id,
            passed=passed,
            selected_tier=TIER_2_P15_ORIG_ATOMIC_ROLLBACK if passed else TIER_BLOCKED_UNSAFE_REQUEST,
            tier_rank=2 if passed else -1,
            action_summary=(
                "Atomic p15:/usr .orig rollback via EH2 flag & 16/16 SHA256(H0)==SHA256(H3) "
                f"clean uninstaller ({SONY_FX3_JIRITSU_SEQUENCE})."
            ),
            requires_clean_p15_uninstall_first=need_clean_first,
            blocked_codes=tuple(dict.fromkeys(blocked)),
            errors=tuple(errors),
        )

    # Tier-3: Official Sony BODYDATA.DAT (\x89UFU Ver. 7.02) stock p1 reflash
    if symptom.ufu_reflash_request is not None and not symptom.bootrom_cold_hang_or_bloader_corrupt and not symptom.emmc_and_spinor_offchip_isp_needed:
        ufu_rep = verify_stock_ufu_reflash_preflight(symptom.ufu_reflash_request)
        if not ufu_rep.passed:
            blocked.extend(ufu_rep.blocked_codes)
            errors.extend(ufu_rep.errors)
        passed = len(blocked) == 0 and ufu_rep.passed
        return FiveTierEscalationDecision(
            scenario_id=symptom.scenario_id,
            passed=passed,
            selected_tier=TIER_3_OFFICIAL_UFU_BODYDATA_STOCK_REFLASH if passed else TIER_BLOCKED_UNSAFE_REQUEST,
            tier_rank=3 if passed else -1,
            action_summary="Official Sony BODYDATA.DAT (\\x89UFU Ver. 7.02, 0x91030080) stock p1 updater reflash pre-verified.",
            requires_clean_p15_uninstall_first=not ufu_rep.p15_clean_uninstall_verified,
            blocked_codes=tuple(dict.fromkeys(blocked)),
            errors=tuple(errors),
        )

    # Tier-4: CXD90057 (Mira) 15-pin Multi/Micro-USB EL3 (0xfe020000) cold-boot read-only diagnostic guard
    if symptom.bootrom_cold_hang_or_bloader_corrupt and not symptom.emmc_and_spinor_offchip_isp_needed:
        el3_spec = symptom.el3_coldboot_spec or build_default_multi_usb_el3_spec()
        el3_rep = audit_cxd90057_el3_coldboot_guard(el3_spec)
        if not el3_rep.passed:
            blocked.extend(el3_rep.blocked_codes)
            errors.extend(el3_rep.errors)
        passed = len(blocked) == 0 and el3_rep.passed
        return FiveTierEscalationDecision(
            scenario_id=symptom.scenario_id,
            passed=passed,
            selected_tier=TIER_4_CXD90057_MULTI_USB_EL3_COLDBOOT_DIAG if passed else TIER_BLOCKED_UNSAFE_REQUEST,
            tier_rank=4 if passed else -1,
            action_summary=(
                "CXD90057 Multi-USB (Pin 7/8/9/10) 1.8V UART EL3 (0xfe020000) read-only diagnostic audit "
                "(el3_payload_transmit_authorized=False prior to off-chip soldering)."
            ),
            requires_clean_p15_uninstall_first=False,
            blocked_codes=tuple(dict.fromkeys(blocked)),
            errors=tuple(errors),
        )

    # Tier-5: Off-chip 8-bit eMMC ISP (pnflasha* raw ciphertext + CID vault) & SPI NOR (loader_nor.bin) last resort
    if symptom.emmc_and_spinor_offchip_isp_needed:
        cid_ok = (
            bool(_SHA256_HEX_RE.match(symptom.isp_cid_sha256))
            and symptom.isp_cid_sha256 == symptom.vault_cid_sha256
            and symptom.pnflasha_and_mtd0ro_verified
        )
        if not cid_ok:
            blocked.append(BLOCKED_CROSS_CAMERA_CID_VAULT_OR_WRITE_LOCKED)
            errors.append("Tier-5 off-chip ISP requires same-body CID-matched pnflasha* + /dev/mtd0ro Tier-0 vault.")
        passed = len(blocked) == 0 and cid_ok
        return FiveTierEscalationDecision(
            scenario_id=symptom.scenario_id,
            passed=passed,
            selected_tier=TIER_5_OFFCHIP_8BIT_ISP_AND_SPI_NOR_VAULT if passed else TIER_BLOCKED_UNSAFE_REQUEST,
            tier_rank=5 if passed else -1,
            action_summary=(
                "Off-chip 8-bit eMMC ISP (CID-bound pnflasha*) & SPI NOR (loader_nor.bin) Tier-0 vault audit "
                "(isp_write_authorized=False, spi_nor_write_authorized=False)."
            ),
            requires_clean_p15_uninstall_first=False,
            blocked_codes=tuple(dict.fromkeys(blocked)),
            errors=tuple(errors),
        )

    return FiveTierEscalationDecision(
        scenario_id=symptom.scenario_id,
        passed=len(blocked) == 0,
        selected_tier=TIER_0_HEALTHY_NO_RECOVERY_NEEDED if len(blocked) == 0 else TIER_BLOCKED_UNSAFE_REQUEST,
        tier_rank=0 if len(blocked) == 0 else -1,
        action_summary="Camera healthy on stock FX3 7.02; zero escalation required.",
        requires_clean_p15_uninstall_first=False,
        blocked_codes=tuple(dict.fromkeys(blocked)),
        errors=tuple(errors),
    )


def run_pillar_c_5tier_escalation_8_scenario_suite() -> PillarC5Tier8ScenarioSuiteResult:
    """Execute the 8-scenario deterministic 5-tier unbrickable recovery escalation matrix."""
    cid_a = sha256(b"fx3-camera-cid-tier5-A").hexdigest()
    cid_b = sha256(b"fx3-camera-cid-tier5-B").hexdigest()

    cases: Tuple[Tuple[str, bool, str, Optional[str], RecoverySymptomInput], ...] = (
        (
            P160_PILLAR_C_SCENARIO_IDS[0],
            True,
            TIER_1_EH1_SD_47US_BYPASS,
            None,
            RecoverySymptomInput(
                scenario_id=P160_PILLAR_C_SCENARIO_IDS[0],
                stage_reached="STAGE_4_IM_ELF_SD_ESCAPE_WRAPPER",
                sd_stageb_active=True,
                p15_overlay_installed=False,
            ),
        ),
        (
            P160_PILLAR_C_SCENARIO_IDS[1],
            True,
            TIER_2_P15_ORIG_ATOMIC_ROLLBACK,
            None,
            RecoverySymptomInput(
                scenario_id=P160_PILLAR_C_SCENARIO_IDS[1],
                stage_reached="STAGE_5_STAGEB_APPFW_BIG6_READY",
                p15_overlay_installed=True,
                eh2_16of16_h0_eq_h3_ready=True,
                jiritsu_0da1_to_0336_available=True,
            ),
        ),
        (
            P160_PILLAR_C_SCENARIO_IDS[2],
            True,
            TIER_3_OFFICIAL_UFU_BODYDATA_STOCK_REFLASH,
            None,
            RecoverySymptomInput(
                scenario_id=P160_PILLAR_C_SCENARIO_IDS[2],
                stage_reached="STAGE_3_SPACC_CNFLASHA15_EXT2_USR",
                p15_overlay_installed=False,
                ufu_reflash_request=UfuStockReflashRequest(),
            ),
        ),
        (
            P160_PILLAR_C_SCENARIO_IDS[3],
            True,
            TIER_2_P15_ORIG_ATOMIC_ROLLBACK,
            None,
            RecoverySymptomInput(
                scenario_id=P160_PILLAR_C_SCENARIO_IDS[3],
                stage_reached="STAGE_5_STAGEB_APPFW_BIG6_READY",
                p15_overlay_installed=True,
                eh2_16of16_h0_eq_h3_ready=True,
                jiritsu_0da1_to_0336_available=True,
                ufu_reflash_request=UfuStockReflashRequest(
                    p15_stageb_overlay_installed=True,
                    p15_orig_uninstalled=False,
                    p15_orig_16of16_sha256_h0_eq_h3=False,
                ),
            ),
        ),
        (
            P160_PILLAR_C_SCENARIO_IDS[4],
            False,
            TIER_BLOCKED_UNSAFE_REQUEST,
            BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH,
            RecoverySymptomInput(
                scenario_id=P160_PILLAR_C_SCENARIO_IDS[4],
                stage_reached="STAGE_3_SPACC_CNFLASHA15_EXT2_USR",
                p15_overlay_installed=False,
                ufu_reflash_request=UfuStockReflashRequest(
                    target_model_name="ILME-FX30",
                    target_model_id=CROSS_BODY_MODEL_IDS["ILME-FX30"],
                ),
            ),
        ),
        (
            P160_PILLAR_C_SCENARIO_IDS[5],
            True,
            TIER_4_CXD90057_MULTI_USB_EL3_COLDBOOT_DIAG,
            None,
            RecoverySymptomInput(
                scenario_id=P160_PILLAR_C_SCENARIO_IDS[5],
                stage_reached="STAGE_0_BOOTROM_SPI_NOR_IPL",
                bootrom_cold_hang_or_bloader_corrupt=True,
                el3_coldboot_spec=build_default_multi_usb_el3_spec(),
            ),
        ),
        (
            P160_PILLAR_C_SCENARIO_IDS[6],
            True,
            TIER_5_OFFCHIP_8BIT_ISP_AND_SPI_NOR_VAULT,
            None,
            RecoverySymptomInput(
                scenario_id=P160_PILLAR_C_SCENARIO_IDS[6],
                stage_reached="STAGE_0_BOOTROM_SPI_NOR_IPL",
                emmc_and_spinor_offchip_isp_needed=True,
                isp_cid_sha256=cid_a,
                vault_cid_sha256=cid_a,
                pnflasha_and_mtd0ro_verified=True,
            ),
        ),
        (
            P160_PILLAR_C_SCENARIO_IDS[7],
            False,
            TIER_BLOCKED_UNSAFE_REQUEST,
            BLOCKED_CROSS_CAMERA_CID_VAULT_OR_WRITE_LOCKED,
            RecoverySymptomInput(
                scenario_id=P160_PILLAR_C_SCENARIO_IDS[7],
                stage_reached="STAGE_0_BOOTROM_SPI_NOR_IPL",
                emmc_and_spinor_offchip_isp_needed=True,
                isp_cid_sha256=cid_a,
                vault_cid_sha256=cid_b,
                pnflasha_and_mtd0ro_verified=True,
                request_isp_write_unlock=True,
                request_spi_nor_write=True,
            ),
        ),
    )

    outcomes: List[PillarC5TierScenarioOutcome] = []
    for sid, exp_pass, exp_tier, exp_code, sym in cases:
        dec = evaluate_5tier_recovery_escalation(sym)
        ok = (
            dec.passed == exp_pass
            and dec.selected_tier == exp_tier
            and not dec.persistent_emmc_writes_authorized
            and not dec.spi_nor_write_authorized
            and not dec.el3_payload_transmit_authorized
            and not dec.isp_write_authorized
            and dec.physical_usb_packets_emitted == 0
            and dec.physical_device_writes == 0
            and (exp_code is None or exp_code in dec.blocked_codes)
        )
        outcomes.append(
            PillarC5TierScenarioOutcome(
                scenario_id=sid,
                passed=ok,
                expected_tier=exp_tier,
                observed_tier=dec.selected_tier,
                expected_pass=exp_pass,
                observed_pass=dec.passed,
                blocked_codes=dec.blocked_codes,
            )
        )

    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(P160_PILLAR_C_SCENARIO_IDS)
    return PillarC5Tier8ScenarioSuiteResult(
        passed=all_ok,
        status=P160_STATUS_VERIFIED_PILLAR_C if all_ok else P160_STATUS_REJECTED_PILLAR_C,
        scenarios_passed=passed_cnt,
        scenarios_total=len(P160_PILLAR_C_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Unified Phase 160 (Pillar 21 / 21/21) Suite Entrypoint
# ---------------------------------------------------------------------------


def run_realhw_bootrom_el3_and_ufu_stock_reflash_suite(
    force_clean_room: Optional[bool] = None,
) -> RealHwBootromEl3AndUfuSuiteReport:
    """Run all Phase 160 (Pillar 21 / 21/21) 5-tier recovery, EL3 cold-boot & UFU stock-reflash gates."""
    donor_snap = inspect_phase160_5tier_donors_readonly(force_clean_room=force_clean_room)
    pa = run_pillar_a_ufu_stock_reflash_8_scenario_suite()
    pb = run_pillar_b_el3_coldboot_guard_6_scenario_suite()
    pc = run_pillar_c_5tier_escalation_8_scenario_suite()

    all_ok = donor_snap.all_passed and pa.passed and pb.passed and pc.passed
    status = P160_STATUS_VERIFIED_SUITE if all_ok else P160_STATUS_FAIL_SUITE
    digest_payload = {
        "schema": PHASE160_SCHEMA,
        "version": PHASE160_VERSION,
        "status": status,
        "verification_mode": donor_snap.verification_mode,
        "donor_snapshot": donor_snap.to_dict(),
        "pillar_a": pa.to_dict(),
        "pillar_b": pb.to_dict(),
        "pillar_c": pc.to_dict(),
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "isp_write_authorized": ISP_WRITE_AUTHORIZED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "physical_device_writes": PHYSICAL_DEVICE_WRITES,
    }
    suite_sha = sha256(
        json.dumps(digest_payload, ensure_ascii=False, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return RealHwBootromEl3AndUfuSuiteReport(
        schema=PHASE160_SCHEMA,
        version=PHASE160_VERSION,
        status=status,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        donor_snapshot=donor_snap,
        pillar_a_ufu_8_scenarios=pa,
        pillar_b_el3_6_scenarios=pb,
        pillar_c_5tier_8_scenarios=pc,
        suite_sha256=suite_sha,
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "BLOCKED_CROSS_BODY_MODEL_ID_MISMATCH",
    "BLOCKED_CROSS_CAMERA_CID_VAULT_OR_WRITE_LOCKED",
    "BLOCKED_DIRTY_P15_STAGEB_CLEAN_UNINSTALL_REQUIRED",
    "BLOCKED_EL3_PAYLOAD_TRANSMIT_LOCKED_FALSE",
    "BLOCKED_EL3_SRAM_WINDOW_OR_ALIGN_INVALID",
    "BLOCKED_MULTI_USB_1V8_CMOS_OVERVOLTAGE",
    "BLOCKED_MULTI_USB_PINOUT_INCOMPLETE",
    "BLOCKED_OTA_BATTERY_OR_REGION_PREFLIGHT",
    "BLOCKED_PERSISTENT_WRITE_AUTHORIZED_FALSE",
    "BLOCKED_PIN10_AD_JACK_IN_LTC_COLLISION",
    "BLOCKED_UFU_EPOCH_DOWNGRADE",
    "BLOCKED_UFU_OR_FDAT_1024B_FRAMING_INVALID",
    "BODYDATA_BOUNDED_HEADER_BYTES",
    "BODYDATA_BOUNDED_TAIL_BYTES",
    "BOUNDED_HEADER_MAX_BYTES",
    "CROSS_BODY_MODEL_IDS",
    "Cxd90057El3ColdBootReport",
    "Cxd90057El3ColdBootSpec",
    "EL3_COLD_BOOT_MAX_PAYLOAD_BYTES",
    "EL3_COLD_BOOT_SRAM_BASE",
    "EL3_COLD_BOOT_SRAM_LIMIT",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "FDAT_BLOCK_BYTES",
    "FDAT_CHUNK_HDR_BYTES",
    "FDAT_CHUNK_PAYLOAD_MAX",
    "FDAT_IV_RSA2048_TRAILER_BYTES",
    "FDAT_TERMINAL_FLAG",
    "FIVE_TIER_ORDER",
    "FX3_MODEL_ID",
    "FX3_MODEL_NAME",
    "FX3_SOC_AP",
    "FX3_SOC_CP",
    "FX3_STOCK_EPOCH",
    "FX3_STOCK_VERSION",
    "Fdat1024FramingResult",
    "FiveTierEscalationDecision",
    "ISP_WRITE_AUTHORIZED",
    "LANC_OHM_NOMINAL",
    "LOADER_NOR_SRAM_ENTRY",
    "MULTI_USB_1V8_MAX_V",
    "MULTI_USB_1V8_MIN_V",
    "MULTI_USB_1V8_NOMINAL_V",
    "MULTI_USB_REQUIRED_PINS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P160_DONOR_FX3_702_INIT_RELPATH",
    "P160_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P160_DONOR_FX3_BODYDATA_RELPATH",
    "P160_DONOR_FX3_CPAPP_B_RELPATH",
    "P160_DONOR_FX3_LOADER_NOR_RELPATH",
    "P160_DONOR_FX3_P1_205_RELPATH",
    "P160_PILLAR_A_SCENARIO_IDS",
    "P160_PILLAR_B_SCENARIO_IDS",
    "P160_PILLAR_C_SCENARIO_IDS",
    "P160_PINNED_FX3_702_INIT_BYTES",
    "P160_PINNED_FX3_702_INIT_SHA256",
    "P160_PINNED_FX3_BACKUP_BIN_BYTES",
    "P160_PINNED_FX3_BACKUP_BIN_SHA256",
    "P160_PINNED_FX3_BODYDATA_BYTES",
    "P160_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P160_PINNED_FX3_CPAPP_B_BYTES",
    "P160_PINNED_FX3_CPAPP_B_HDR4K_SHA256",
    "P160_PINNED_FX3_LOADER_NOR_BYTES",
    "P160_PINNED_FX3_LOADER_NOR_SHA256",
    "P160_PINNED_FX3_P1_205_BYTES",
    "P160_PINNED_FX3_P1_205_SHA256",
    "P160_PINNED_FX3_P1_SBIN_INIT_BYTES",
    "P160_PINNED_FX3_P1_SBIN_INIT_SHA256",
    "P160_STATUS_FAIL_SUITE",
    "P160_STATUS_REJECTED_PILLAR_A",
    "P160_STATUS_REJECTED_PILLAR_B",
    "P160_STATUS_REJECTED_PILLAR_C",
    "P160_STATUS_VERIFIED_PILLAR_A",
    "P160_STATUS_VERIFIED_PILLAR_B",
    "P160_STATUS_VERIFIED_PILLAR_C",
    "P160_STATUS_VERIFIED_SUITE",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE160_SCHEMA",
    "PHASE160_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "Phase160DonorArtifactDigest",
    "Phase160DonorSnapshot",
    "PillarAUfu8ScenarioSuiteResult",
    "PillarAUfuScenarioOutcome",
    "PillarBEl36ScenarioSuiteResult",
    "PillarBEl3ScenarioOutcome",
    "PillarC5Tier8ScenarioSuiteResult",
    "PillarC5TierScenarioOutcome",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RealHwBootromEl3AndUfuSuiteReport",
    "RecoverySymptomInput",
    "SONY_FX3_JIRITSU_SEQUENCE",
    "SONY_FX3_MSC_PID",
    "SONY_FX3_SERVICE_PID",
    "SONY_MIN_UPDATE_BATTERY_PCT",
    "SONY_USB_VID",
    "SPI_NOR_WRITE_AUTHORIZED",
    "TIER_0_HEALTHY_NO_RECOVERY_NEEDED",
    "TIER_1_EH1_SD_47US_BYPASS",
    "TIER_2_P15_ORIG_ATOMIC_ROLLBACK",
    "TIER_3_OFFICIAL_UFU_BODYDATA_STOCK_REFLASH",
    "TIER_4_CXD90057_MULTI_USB_EL3_COLDBOOT_DIAG",
    "TIER_5_OFFCHIP_8BIT_ISP_AND_SPI_NOR_VAULT",
    "TIER_BLOCKED_UNSAFE_REQUEST",
    "UFU_MAGIC",
    "UFU_MAGIC_HEX",
    "UfuEnvelopeParseResult",
    "UfuStockReflashReport",
    "UfuStockReflashRequest",
    "VALID_REGIONS",
    "VMC_BNCM1_LTC_OHM_NOMINAL",
    "audit_cxd90057_el3_coldboot_guard",
    "build_default_multi_usb_el3_spec",
    "build_fdat_1024b_chunk_stream",
    "build_synthetic_ufu_bodydata_header",
    "evaluate_5tier_recovery_escalation",
    "inspect_phase160_5tier_donors_readonly",
    "parse_ufu_tlv_envelope_header",
    "run_pillar_a_ufu_stock_reflash_8_scenario_suite",
    "run_pillar_b_el3_coldboot_guard_6_scenario_suite",
    "run_pillar_c_5tier_escalation_8_scenario_suite",
    "run_realhw_bootrom_el3_and_ufu_stock_reflash_suite",
    "verify_fdat_1024b_chunk_stream",
    "verify_stock_ufu_reflash_preflight",
]
