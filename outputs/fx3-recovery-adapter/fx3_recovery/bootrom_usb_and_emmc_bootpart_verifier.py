"""Phase 124 — CXD90057 Mask-BootROM USB Cold-Plug Recovery Enumeration Verifier,
JEDEC eMMC 5.1 BOOT0/BOOT1 Hardware Boot-Partition (`EXT_CSD[179]` `PART_CONFIG`,
`EXT_CSD[177]` `BOOT_BUS_CONDITIONS`, `EXT_CSD[173]` `BOOT_WP`) Anti-Corruption
Triage, & 13-Pillar Recovery Master Suite.

Provides three deterministic, RAM-only, read-only-donor verification pillars for
Sony `ILME-FX3` (`0x91030080` / `ALCIN_UUD`, `CXD90057`) recovery safety:

1. **Read-Only (`O_RDONLY`) FX3/FX6 Bootloader & Partition-Config Donor Inspection**:
   - Opens local FX3 `v7.02` (`loader_nor.bin`, `pformat_config.txt`, `loader_nor.tar`,
     `partinf.conf`) and FX6 `v6.01` (`loader_nor.tar`, `partinf.conf`) donor artifacts
     strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, verifying cross-SKU
     separation (`101,888` B FX3 vs `92,448` B FX6 `loader_nor.bin`) and SRAM load
     anchors (`0xFE040800` / `0xFE049000`) with zero raw firmware bytes or keys emitted.
   - Deterministically falls back to pinned `CLEAN_ROOM_SYNTHETIC` metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent.

2. **Pillar A — JEDEC `eMMC 5.1` `BOOT0 / BOOT1` Hardware Boot-Partition & `EXT_CSD` Triage**:
   - Models `CXD90057` first-stage bootloader (`SBL` / `ipl` / `loader`) residency in
     dedicated eMMC hardware partitions `BOOT0` (`4 MiB`) and redundant `BOOT1` (`4 MiB`)
     under `EXT_CSD[179]` (`PART_CONFIG`), `EXT_CSD[177]` (`BOOT_BUS_CONDITIONS`),
     `EXT_CSD[173]` (`BOOT_WP`), and `EXT_CSD[226]` (`BOOT_SIZE_MULT`).
   - Detects fail-closed:
     a) `BOOT_PART_DISABLED_DEAD_BOOT_TRAP` (`BOOT_PARTITION_ENABLE == 0x0` or `0x7`
        user-area mismatch, or reserved values `0x3..0x6`),
     b) `BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE` (`BOOT0` SHA-256 / header
        mismatch while redundant `BOOT1` is intact),
     c) `BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD` if any `EXT_CSD[173]` byte or
        script/profile attempts to assert permanent `B_PERM_WP_EN` (`bit 2` or `bit 6`),
     d) `PARTITION_ACCESS_NONZERO_LEAK` if `PART_CONFIG[2:0] != 0`, plus dual
        `BOOT0/BOOT1` corruption escalation to Mask-BootROM recovery.

3. **Pillar B — `CXD90057` Mask-BootROM USB Cold-Plug Enumeration & `RAM_LOAD_ONLY` Sandbox**:
   - Models `CXD90057` Mask-BootROM fallback enumeration (`USB VID 0x054C` cold-plug
     descriptor & bulk IN/OUT endpoint handshake when `BOOT0/BOOT1` fail or lab
     test-pad strap is asserted) and verifies that any recovery payload staging targets
     SRAM/DRAM execute-in-place (`RAM_LOAD_ONLY`) with
     `emmc_persistent_program_commands == 0` and `physical_device_writes == 0`.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from hashlib import sha256
import io
import json
import os
from pathlib import Path
import re
import tarfile
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .files import is_forced_clean_room, read_file, require, resolve_donor_path


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

BOOTROM_USB_EMMC_BOOTPART_SCHEMA: str = "fx3-bootrom-usb-and-emmc-bootpart-verifier-v1"
BOOTROM_USB_EMMC_BOOTPART_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
READ_ONLY_DONOR_ACCESS: bool = True
OTP_FUSE_TOUCHES: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
EMMC_PERSISTENT_PROGRAM_COMMANDS: int = 0

STATUS_VERIFIED_BOOTROM_BOOTPART_GATE: str = "VERIFIED_BOOTROM_USB_AND_EMMC_BOOTPART_GATE"
STATUS_FAIL_BOOTROM_BOOTPART_GATE: str = "FAIL_BOOTROM_USB_AND_EMMC_BOOTPART_GATE"
STATUS_VERIFIED_EMMC_BOOTPART_HEALTHY: str = "VERIFIED_EMMC_BOOTPART_HEALTHY"
STATUS_EMMC_BOOT0_FAILOVER_TO_BOOT1: str = "EMMC_BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE"
STATUS_EMMC_BOOTPART_REJECTED: str = "REJECTED_EMMC_BOOTPART_OR_EXT_CSD_HAZARD"
STATUS_VERIFIED_BOOTROM_RAM_LOAD_ONLY: str = "VERIFIED_BOOTROM_USB_RAM_LOAD_ONLY_SANDBOX"
STATUS_REJECTED_BOOTROM_SANDBOX: str = "REJECTED_BOOTROM_USB_OR_PERSISTENT_WRITE_ATTEMPT"
STATUS_BLOCKED_BOOT_WP_FUSE_HAZARD: str = "BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD"

# Local Donor Relative Paths (strictly read-only via os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK)
DONOR_FX3_LOADER_NOR_BIN_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/loader_nor.bin"
)
DONOR_FX3_PFORMAT_CONFIG_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/nor-loader-members/pformat_config.txt"
)
DONOR_FX3_LOADER_NOR_TAR_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0750_nor_loader/loader_nor.tar"
)
DONOR_FX6_LOADER_NOR_TAR_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0750_nor_loader/loader_nor.tar"
)
DONOR_FX3_PARTINF_CONF_RELPATH: str = (
    "sony-firmware-20261024/stage182-boot-selector-and-recovery-admission/"
    "current-updater-evidence/tar-selected/0300_partconf/partinf.conf"
)
DONOR_FX6_PARTINF_CONF_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0300_partconf/partinf.conf"
)

# Pinned Integrity Anchors (Zero Proprietary Keys / Zero Raw Firmware Bytes)
PINNED_FX3_LOADER_NOR_BIN_BYTES: int = 101888
PINNED_FX3_LOADER_NOR_BIN_SHA256: str = "4358c839cfb1f22d5eb4e53d67817c42c4e877ba8b0aff375d355ce6294c4942"
PINNED_FX3_PFORMAT_CONFIG_BYTES: int = 1274
PINNED_FX3_PFORMAT_CONFIG_SHA256: str = "21cd5b29dd165c322f5b00bb057802c377ff94af15f95881e150a32130302ece"
PINNED_FX3_LOADER_NOR_TAR_BYTES: int = 112640
PINNED_FX3_LOADER_NOR_TAR_SHA256: str = "913d1a3271f855b90192d84fbbdb224533c8d8493833d0c194b3d14fdad4dd3f"
PINNED_FX6_LOADER_NOR_TAR_BYTES: int = 102400
PINNED_FX6_LOADER_NOR_TAR_SHA256: str = "67e7b9cd0b6a40f59963fc6abb1fffad4cd0aaed575de543c8de22569399873b"
PINNED_FX6_INTERNAL_LOADER_NOR_BIN_BYTES: int = 92448
PINNED_FX6_INTERNAL_LOADER_NOR_BIN_SHA256: str = "d91d21a80afbad0053c95ba59129b97d59fd4feedf0cb4a0c01eac7ef7cebe08"
PINNED_FX3_PARTINF_CONF_BYTES: int = 3999
PINNED_FX3_PARTINF_CONF_SHA256: str = "3d96228d4ed2db3cb4295aa854edf0ad8895440167f132144cdec4f8cfdad189"
PINNED_FX6_PARTINF_CONF_BYTES: int = 3990
PINNED_FX6_PARTINF_CONF_SHA256: str = "e05b53d1f739968510dd24d62cd38426772fe3e50fe463a3d260c5f113e17ec9"

# ---------------------------------------------------------------------------
# Pillar A Constants — JEDEC eMMC 5.1 BOOT0/BOOT1 & EXT_CSD Boot Config
# ---------------------------------------------------------------------------

EMMC_EXT_CSD_BYTES: int = 512
EMMC_EXT_CSD_RST_N_IDX: int = 162
EMMC_EXT_CSD_BOOT_WP_IDX: int = 173
EMMC_EXT_CSD_BOOT_WP_STATUS_IDX: int = 174
EMMC_EXT_CSD_BOOT_BUS_COND_IDX: int = 177
EMMC_EXT_CSD_PART_CONFIG_IDX: int = 179
EMMC_EXT_CSD_REV_IDX: int = 192
EMMC_EXT_CSD_BOOT_SIZE_MULT_IDX: int = 226

EMMC_BOOT_PARTITION_MIB: int = 4
EMMC_BOOT_PARTITION_BYTES: int = 4 * 1024 * 1024  # 4 MiB hardware BOOT0 / BOOT1
EMMC_BOOT_SIZE_UNIT_BYTES: int = 128 * 1024
EMMC_EXPECTED_BOOT_SIZE_MULT: int = 32  # 32 * 128 KiB = 4 MiB

# EXT_CSD[179] PART_CONFIG fields
PART_CONFIG_ACCESS_MASK: int = 0x07
PART_CONFIG_ENABLE_MASK: int = 0x38
PART_CONFIG_ENABLE_SHIFT: int = 3
PART_CONFIG_BOOT_ACK_BIT: int = 0x40
PART_CONFIG_RESERVED_BIT7: int = 0x80

BOOT_PART_ENABLE_DISABLED: int = 0x0
BOOT_PART_ENABLE_BOOT0: int = 0x1
BOOT_PART_ENABLE_BOOT1: int = 0x2
BOOT_PART_ENABLE_UDA: int = 0x7
VALID_EMMC_BOOT_PART_ENABLES: Tuple[int, ...] = (BOOT_PART_ENABLE_BOOT0, BOOT_PART_ENABLE_BOOT1)

PART_ACCESS_USER_AREA: int = 0x0
PART_ACCESS_BOOT0: int = 0x1
PART_ACCESS_BOOT1: int = 0x2
PART_ACCESS_RPMB: int = 0x3

# EXT_CSD[177] BOOT_BUS_CONDITIONS fields
BOOT_BUS_WIDTH_MASK: int = 0x03  # 0=x1/x4 DDR, 1=x4, 2=x8
BOOT_BUS_RESET_BIT: int = 0x04
BOOT_BUS_MODE_MASK: int = 0x18  # bits [4:3]: 0=SDR backward-compat, 1=SDR HS, 2=DDR, 3=reserved
BOOT_BUS_MODE_SHIFT: int = 3
BOOT_BUS_RESERVED_MASK: int = 0xE0

BOOT_BUS_WIDTH_NAMES: Dict[int, str] = {
    0: "X1_SDR_OR_X4_DDR",
    1: "X4_SDR_OR_DDR",
    2: "X8_SDR_OR_DDR",
    3: "RESERVED_WIDTH_3",
}
BOOT_BUS_MODE_NAMES: Dict[int, str] = {
    0: "SDR_BACKWARD_COMPATIBLE",
    1: "SDR_HIGH_SPEED_TIMING",
    2: "DDR_DUAL_DATA_RATE",
    3: "RESERVED_MODE_3",
}

# EXT_CSD[173] BOOT_WP permanent OTP fuse hazard bits (bit 2 & bit 6)
EXT_CSD_BOOT_WP_PWR_EN_BIT0: int = 1 << 0
EXT_CSD_BOOT_WP_PWR_DIS_BIT1: int = 1 << 1
EXT_CSD_BOOT_WP_PERM_EN_BIT2: int = 1 << 2  # 0x04 B_PERM_WP_EN
EXT_CSD_BOOT_WP_PERM_DIS_BIT3: int = 1 << 3
EXT_CSD_BOOT_WP_SEC_SEL_BIT4: int = 1 << 4
EXT_CSD_BOOT_WP_PERM_EN_BIT6: int = 1 << 6  # 0x40 B_PERM_WP_EN extended/secondary profile bit
EXT_CSD_BOOT_PERM_WP_HAZARD_MASK: int = EXT_CSD_BOOT_WP_PERM_EN_BIT2 | EXT_CSD_BOOT_WP_PERM_EN_BIT6

FX3_DEFAULT_PART_CONFIG: int = 0x48  # BOOT_ACK=1 (bit6), BOOT_PARTITION_ENABLE=1 (BOOT0), PARTITION_ACCESS=0 (UDA)
FX3_DEFAULT_BOOT_BUS_CONDITIONS: int = 0x02  # x8 boot bus width, reset to x1 after boot, SDR backward-compatible

# Required Pillar A Detection Codes (exact names per Phase 124 spec)
BOOT_PART_DISABLED_DEAD_BOOT_TRAP: str = "BOOT_PART_DISABLED_DEAD_BOOT_TRAP"
BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE: str = "BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE"
BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD: str = "BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD"
PARTITION_ACCESS_NONZERO_LEAK: str = "PARTITION_ACCESS_NONZERO_LEAK"

ERR_BOOTPART_BOTH_CORRUPTED_MASK_BOOTROM_REQUIRED: str = "BOTH_BOOT0_BOOT1_CORRUPTED_MASK_BOOTROM_REQUIRED"
ERR_BOOTPART_EXT_CSD_BAD_LENGTH: str = "EXT_CSD_BAD_LENGTH_NOT_512B"
ERR_BOOTPART_INVALID_BOOT_BUS_CONDITIONS: str = "EXT_CSD_177_INVALID_BOOT_BUS_CONDITIONS"
ERR_BOOTPART_BOOT_SIZE_MULT_MISMATCH: str = "EXT_CSD_226_BOOT_SIZE_MULT_NOT_4MIB"
ERR_BOOTPART_CROSS_SKU_TRANSPLANT: str = "CROSS_SKU_FX6_LOADER_IN_FX3_BOOTPART_REJECTED"
ERR_BOOTPART_RESERVED_PART_CONFIG_BITS: str = "EXT_CSD_179_RESERVED_BITS_SET"

BOOTPART_SCENARIO_IDS: Tuple[str, ...] = (
    "B1_HEALTHY_STOCK_BOOT0_ACTIVE",
    "B2_BOOT_PART_DISABLED_DEAD_BOOT_TRAP",
    "B3_BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE",
    "B4_PARTITION_ACCESS_NONZERO_LEAK",
    "B5_PERMANENT_BOOT_WP_FUSE_HAZARD_BLOCKED",
    "B6_BOTH_BOOT0_BOOT1_CORRUPTED_BOOTROM_FALLBACK",
)

# ---------------------------------------------------------------------------
# Pillar B Constants — CXD90057 Mask-BootROM USB Cold-Plug & RAM_LOAD_ONLY
# ---------------------------------------------------------------------------

SONY_USB_VENDOR_ID: int = 0x054C
SONY_USB_VENDOR_ID_HEX: str = "0x054c"
CXD90057_BOOTROM_COLDPLUG_PID: int = 0x0C90
CXD90057_BOOTROM_USB_PIDS: Tuple[int, ...] = (0x0C90, 0x0336, 0x0DA1)
CXD90057_VALID_USB_MAX_PACKET_SIZES: Tuple[int, ...] = (64, 512, 1024)

BOOTROM_VALID_TRIGGERS: Tuple[str, ...] = (
    "BOOT0_AND_BOOT1_FAILED",
    "BOOT_PART_DISABLED_DEAD_BOOT_TRAP",
    "LAB_TEST_PAD_STRAP_SIMULATION",
    "COLD_PLUG_RECOVERY_BUTTON",
)

RAM_LOAD_ONLY: str = "RAM_LOAD_ONLY"
CXD90057_SRAM_WINDOW_START: int = 0xFE040000
CXD90057_SRAM_WINDOW_END: int = 0xFE100000
CXD90057_SRAM_AWAKE_MEMADDR: int = 0xFE040800
CXD90057_SRAM_LOADER_ENTRY: int = 0xFE049000
CXD90057_DRAM_WINDOW_START: int = 0x40000000
CXD90057_DRAM_WINDOW_END: int = 0xC0000000
CXD90057_DRAM_STAGE_B_BASE: int = 0x40080000
BOOTROM_MAX_STAGE_PAYLOAD_BYTES: int = 64 * 1024 * 1024

FORBIDDEN_BOOTROM_PROGRAM_VERBS: Tuple[str, ...] = (
    "emmc_program",
    "mmc_write",
    "flash_boot0",
    "flash_boot1",
    "write_boot0",
    "write_boot1",
    "erase",
    "blkdiscard",
    "rpmb_write",
    "burn_otp",
    "fuse_blow",
    "cmd42",
    "ext_csd_write",
    "boot_wp_perm",
    "fastboot_flash",
    "dd_emmc",
)

ERR_BOOTROM_NON_SONY_USB_VID: str = "BOOTROM_NON_SONY_USB_VID_REJECTED"
ERR_BOOTROM_UNSUPPORTED_PID: str = "BOOTROM_UNSUPPORTED_USB_PID_REJECTED"
ERR_BOOTROM_INVALID_BULK_ENDPOINTS: str = "BOOTROM_INVALID_USB_BULK_ENDPOINTS"
ERR_BOOTROM_UNRECOGNIZED_TRIGGER: str = "BOOTROM_UNRECOGNIZED_COLDPLUG_TRIGGER"
ERR_BOOTROM_NON_RAM_LOAD_MODE_FORBIDDEN: str = "BOOTROM_NON_RAM_LOAD_ONLY_MODE_FORBIDDEN"
ERR_BOOTROM_PERSISTENT_PROGRAM_COMMAND_FORBIDDEN: str = "BOOTROM_PERSISTENT_EMMC_PROGRAM_COMMAND_FORBIDDEN"
ERR_BOOTROM_INVALID_RAM_XIP_WINDOW: str = "BOOTROM_INVALID_SRAM_DRAM_XIP_WINDOW"
ERR_BOOTROM_CROSS_SKU_PAYLOAD_REJECTED: str = "BOOTROM_CROSS_SKU_FX6_PAYLOAD_REJECTED"

BOOTROM_SCENARIO_IDS: Tuple[str, ...] = (
    "M1_BOOT0_BOOT1_FAILED_USB_054C_SRAM_XIP",
    "M2_TEST_PAD_STRAP_DRAM_XIP_STAGE_B",
    "M3_EMMC_PERSISTENT_PROGRAM_COMMAND_BLOCKED",
    "M4_NON_SONY_USB_VID_REJECTED",
    "M5_CROSS_SKU_FX6_SRAM_PAYLOAD_REJECTED",
)

SYNTHETIC_BOOT_LOADER_HEADER_MAGIC: str = "FX3SBLv7"


# ---------------------------------------------------------------------------
# Internal Helpers (Zero raw bytes fields emitted)
# ---------------------------------------------------------------------------


def _canonical_sha256(obj: Any) -> str:
    encoded = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(encoded).hexdigest()


def _parse_partinf_partition_count(text: str) -> int:
    return sum(
        1
        for line in text.splitlines()
        if line.strip().startswith("0x") and "," in line
    )


# ---------------------------------------------------------------------------
# Structured Dataclasses (Zero raw bytes fields)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BootromBootpartDonorArtifactDigest:
    label: str
    relpath: str
    source_mode: str
    byte_length: int
    sha256: str
    details: str


@dataclass(frozen=True)
class DonorBootromBootpartSnapshot:
    verification_mode: str
    read_only_access: bool
    fx3_loader_nor_bin_bytes: int
    fx3_loader_nor_bin_sha256: str
    fx3_pformat_config_sha256: str
    fx3_loader_nor_tar_sha256: str
    fx6_loader_nor_tar_sha256: str
    fx6_internal_loader_nor_bin_bytes: int
    fx6_internal_loader_nor_bin_sha256: str
    fx3_partinf_conf_sha256: str
    fx6_partinf_conf_sha256: str
    cross_sku_loader_distinct: bool
    artifacts: Tuple[BootromBootpartDonorArtifactDigest, ...]
    snapshot_sha256: str


@dataclass(frozen=True)
class BootPartitionSlotState:
    partition_name: str
    size_bytes: int
    sha256: str
    expected_sha256: str
    header_magic_valid: bool
    blank_or_erased: bool
    sector_aligned: bool
    sku_code: str = "ILME-FX3"


@dataclass(frozen=True)
class ExtCsdBootConfigView:
    part_config_raw: int
    part_config_hex: str
    boot_ack: int
    boot_partition_enable: int
    boot_partition_target: str
    partition_access: int
    partition_access_name: str
    boot_bus_conditions_raw: int
    boot_bus_conditions_hex: str
    boot_bus_width: int
    boot_bus_width_name: str
    boot_bus_reset: int
    boot_bus_mode: int
    boot_bus_mode_name: str
    boot_wp_raw: int
    boot_wp_hex: str
    boot_perm_wp_asserted: bool
    boot_size_mult: int
    boot_partition_capacity_bytes: int


@dataclass(frozen=True)
class BootWpFirewallDecision:
    allowed: bool
    status: str
    profile_or_command: str
    ext_csd_boot_wp_byte: int
    ext_csd_boot_wp_hex: str
    perm_wp_bit2_set: bool
    perm_wp_bit6_set: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EmmcBootPartitionTriageReport:
    passed: bool
    triage_classified: bool
    status: str
    scenario_id: str
    ext_csd_view: Optional[ExtCsdBootConfigView]
    boot0_intact: bool
    boot1_intact: bool
    dead_boot_trap_detected: bool
    failover_to_boot1_available: bool
    permanent_boot_wp_hazard_detected: bool
    partition_access_nonzero_leak: bool
    mask_bootrom_fallback_required: bool
    recommended_action: str
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class EmmcBootpart6ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[EmmcBootPartitionTriageReport, ...]
    wp_bit2_firewall: BootWpFirewallDecision
    wp_bit6_firewall: BootWpFirewallDecision
    wp_script_firewall: BootWpFirewallDecision
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class UsbDeviceDescriptorSpec:
    vid: int = SONY_USB_VENDOR_ID
    pid: int = CXD90057_BOOTROM_COLDPLUG_PID
    bcd_usb: int = 0x0200
    device_class: int = 0xFF
    bulk_in_ep: int = 0x81
    bulk_out_ep: int = 0x01
    max_packet_size: int = 512
    manufacturer: str = "Sony Corporation"
    product: str = "CXD90057 Mask-BootROM"
    trigger_reason: str = "BOOT0_AND_BOOT1_FAILED"


@dataclass(frozen=True)
class BootromPayloadStageRequest:
    payload_name: str
    target_mode: str = RAM_LOAD_ONLY
    load_address: int = CXD90057_SRAM_AWAKE_MEMADDR
    entry_address: int = CXD90057_SRAM_LOADER_ENTRY
    payload_size: int = PINNED_FX3_LOADER_NOR_BIN_BYTES
    payload_sha256: str = PINNED_FX3_LOADER_NOR_BIN_SHA256
    sku_code: str = "ILME-FX3"
    commands: Tuple[str, ...] = ("USB_COLD_PLUG_ENUMERATE", "RAM_DOWNLOAD_XIP", "JUMP_RAM_ENTRY")


@dataclass(frozen=True)
class BootromUsbEnumerationReport:
    passed: bool
    status: str
    scenario_id: str
    vid_hex: str
    pid_hex: str
    cold_plug_authenticated: bool
    bulk_endpoints_valid: bool
    trigger_reason: str
    ram_load_only_verified: bool
    target_mode: str
    memory_region: str
    load_address_hex: str
    entry_address_hex: str
    emmc_persistent_program_commands: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    error_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BootromUsb5ScenarioSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenario_results: Tuple[BootromUsbEnumerationReport, ...]
    emmc_persistent_program_commands: int
    errors: Tuple[str, ...]
    suite_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class BootromUsbAndEmmcBootpartSuiteReport:
    schema: str
    version: str
    status: str
    verification_mode: str
    all_passed: bool
    read_only_donor_access: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    otp_fuse_touches: int
    passive_tx_bytes_emitted: int
    physical_device_writes: int
    emmc_persistent_program_commands: int
    donor_snapshot: DonorBootromBootpartSnapshot
    emmc_bootpart_6_scenario_suite: EmmcBootpart6ScenarioSuiteResult
    bootrom_usb_5_scenario_suite: BootromUsb5ScenarioSuiteResult
    suite_sha256: str
    elapsed_seconds: float
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Pillar A — JEDEC eMMC 5.1 EXT_CSD & BOOT0/BOOT1 Builders & Triage
# ---------------------------------------------------------------------------


def build_synthetic_ext_csd_boot_config(
    *,
    part_config: int = FX3_DEFAULT_PART_CONFIG,
    boot_bus_conditions: int = FX3_DEFAULT_BOOT_BUS_CONDITIONS,
    boot_wp: int = 0x00,
    boot_wp_status: int = 0x00,
    boot_size_mult: int = EMMC_EXPECTED_BOOT_SIZE_MULT,
    rst_n_function: int = 0x01,
    ext_csd_rev: int = 0x08,
) -> bytes:
    """Build a synthetic 512-byte JEDEC eMMC 5.1 EXT_CSD buffer in RAM."""
    buf = bytearray(EMMC_EXT_CSD_BYTES)
    buf[EMMC_EXT_CSD_RST_N_IDX] = rst_n_function & 0xFF
    buf[EMMC_EXT_CSD_BOOT_WP_IDX] = boot_wp & 0xFF
    buf[EMMC_EXT_CSD_BOOT_WP_STATUS_IDX] = boot_wp_status & 0xFF
    buf[EMMC_EXT_CSD_BOOT_BUS_COND_IDX] = boot_bus_conditions & 0xFF
    buf[EMMC_EXT_CSD_PART_CONFIG_IDX] = part_config & 0xFF
    buf[EMMC_EXT_CSD_REV_IDX] = ext_csd_rev & 0xFF
    buf[EMMC_EXT_CSD_BOOT_SIZE_MULT_IDX] = boot_size_mult & 0xFF
    return bytes(buf)


def build_synthetic_boot_partition_image(
    *,
    partition_name: str = "BOOT0",
    size_bytes: int = EMMC_BOOT_PARTITION_BYTES,
    sku_code: str = "ILME-FX3",
    corrupt_payload: bool = False,
    blank_fill: Optional[int] = None,
) -> Tuple[bytes, BootPartitionSlotState]:
    """Build a synthetic 4 MiB BOOT0/BOOT1 hardware boot-partition descriptor in RAM."""
    require(partition_name in ("BOOT0", "BOOT1"), "partition_name must be BOOT0 or BOOT1")
    require(size_bytes >= 512 and size_bytes % 512 == 0, "boot partition size must be 512B-aligned")

    # Build a deterministic compact header+body representation for fast unit execution
    # while recording exact hardware partition geometry (4 MiB).
    sample_len = min(size_bytes, 4096)
    if blank_fill is not None:
        buf = bytearray([blank_fill & 0xFF]) * sample_len
        actual_sha = sha256(buf).hexdigest()
        expected_sha = sha256(
            (f"{SYNTHETIC_BOOT_LOADER_HEADER_MAGIC}:{sku_code}:{partition_name}").encode("utf-8").ljust(sample_len, b"\x5a")
        ).hexdigest()
        return bytes(buf), BootPartitionSlotState(
            partition_name=partition_name,
            size_bytes=size_bytes,
            sha256=actual_sha,
            expected_sha256=expected_sha,
            header_magic_valid=False,
            blank_or_erased=True,
            sector_aligned=(size_bytes % 512 == 0),
            sku_code=sku_code,
        )

    canonical_buf = (
        f"{SYNTHETIC_BOOT_LOADER_HEADER_MAGIC}:{sku_code}:{partition_name}:SBL_IPL_LOADER"
    ).encode("utf-8").ljust(sample_len, b"\x5a")
    expected_sha = sha256(canonical_buf).hexdigest()

    if corrupt_payload:
        mutated = bytearray(canonical_buf)
        mutated[0:8] = b"BAD!CORR"
        mutated[-16:] = b"\xff" * 16
        actual_sha = sha256(mutated).hexdigest()
        return bytes(mutated), BootPartitionSlotState(
            partition_name=partition_name,
            size_bytes=size_bytes,
            sha256=actual_sha,
            expected_sha256=expected_sha,
            header_magic_valid=False,
            blank_or_erased=False,
            sector_aligned=(size_bytes % 512 == 0),
            sku_code=sku_code,
        )

    return canonical_buf, BootPartitionSlotState(
        partition_name=partition_name,
        size_bytes=size_bytes,
        sha256=expected_sha,
        expected_sha256=expected_sha,
        header_magic_valid=True,
        blank_or_erased=False,
        sector_aligned=(size_bytes % 512 == 0),
        sku_code=sku_code,
    )


def parse_ext_csd_boot_config(ext_csd: bytes) -> Tuple[Optional[ExtCsdBootConfigView], List[str], List[str]]:
    """Parse 512-byte EXT_CSD registers [173], [177], [179], [226] strictly in RAM."""
    error_codes: List[str] = []
    errors: List[str] = []

    if len(ext_csd) != EMMC_EXT_CSD_BYTES:
        error_codes.append(ERR_BOOTPART_EXT_CSD_BAD_LENGTH)
        errors.append(f"EXT_CSD length must be {EMMC_EXT_CSD_BYTES} bytes, got {len(ext_csd)}.")
        return None, error_codes, errors

    part_cfg = ext_csd[EMMC_EXT_CSD_PART_CONFIG_IDX]
    boot_ack = 1 if (part_cfg & PART_CONFIG_BOOT_ACK_BIT) else 0
    boot_en = (part_cfg & PART_CONFIG_ENABLE_MASK) >> PART_CONFIG_ENABLE_SHIFT
    part_acc = part_cfg & PART_CONFIG_ACCESS_MASK

    boot_bus = ext_csd[EMMC_EXT_CSD_BOOT_BUS_COND_IDX]
    bus_width = boot_bus & BOOT_BUS_WIDTH_MASK
    bus_reset = 1 if (boot_bus & BOOT_BUS_RESET_BIT) else 0
    bus_mode = (boot_bus & BOOT_BUS_MODE_MASK) >> BOOT_BUS_MODE_SHIFT

    boot_wp = ext_csd[EMMC_EXT_CSD_BOOT_WP_IDX]
    boot_size_mult = ext_csd[EMMC_EXT_CSD_BOOT_SIZE_MULT_IDX]
    boot_cap = boot_size_mult * EMMC_BOOT_SIZE_UNIT_BYTES

    boot_target_names = {
        0: "DISABLED_NO_BOOT",
        1: "BOOT0",
        2: "BOOT1",
        7: "USER_AREA_UDA_MISMATCH",
    }
    part_access_names = {
        0: "USER_AREA_UDA",
        1: "BOOT0",
        2: "BOOT1",
        3: "RPMB",
    }

    perm_wp_asserted = bool(boot_wp & EXT_CSD_BOOT_PERM_WP_HAZARD_MASK)
    view = ExtCsdBootConfigView(
        part_config_raw=part_cfg,
        part_config_hex=f"0x{part_cfg:02x}",
        boot_ack=boot_ack,
        boot_partition_enable=boot_en,
        boot_partition_target=boot_target_names.get(boot_en, f"RESERVED_{boot_en}"),
        partition_access=part_acc,
        partition_access_name=part_access_names.get(part_acc, f"GP_{part_acc - 3}"),
        boot_bus_conditions_raw=boot_bus,
        boot_bus_conditions_hex=f"0x{boot_bus:02x}",
        boot_bus_width=bus_width,
        boot_bus_width_name=BOOT_BUS_WIDTH_NAMES.get(bus_width, f"UNKNOWN_{bus_width}"),
        boot_bus_reset=bus_reset,
        boot_bus_mode=bus_mode,
        boot_bus_mode_name=BOOT_BUS_MODE_NAMES.get(bus_mode, f"UNKNOWN_{bus_mode}"),
        boot_wp_raw=boot_wp,
        boot_wp_hex=f"0x{boot_wp:02x}",
        boot_perm_wp_asserted=perm_wp_asserted,
        boot_size_mult=boot_size_mult,
        boot_partition_capacity_bytes=boot_cap,
    )

    if part_cfg & PART_CONFIG_RESERVED_BIT7:
        error_codes.append(ERR_BOOTPART_RESERVED_PART_CONFIG_BITS)
        errors.append(f"EXT_CSD[179] PART_CONFIG bit 7 reserved bit set (0x{part_cfg:02x}).")

    if boot_en not in VALID_EMMC_BOOT_PART_ENABLES:
        error_codes.append(BOOT_PART_DISABLED_DEAD_BOOT_TRAP)
        errors.append(
            f"EXT_CSD[179] BOOT_PARTITION_ENABLE=0x{boot_en:x} ({view.boot_partition_target}) "
            "disables CXD90057 hardware SBL boot -> dead boot trap."
        )

    if part_acc != PART_ACCESS_USER_AREA:
        error_codes.append(PARTITION_ACCESS_NONZERO_LEAK)
        errors.append(
            f"EXT_CSD[179] PARTITION_ACCESS=0x{part_acc:x} ({view.partition_access_name}) leaked non-zero; "
            "must return to 0x0 (USER_AREA) after read."
        )

    if (boot_bus & BOOT_BUS_RESERVED_MASK) != 0 or bus_width == 3 or bus_mode == 3:
        error_codes.append(ERR_BOOTPART_INVALID_BOOT_BUS_CONDITIONS)
        errors.append(
            f"EXT_CSD[177] BOOT_BUS_CONDITIONS=0x{boot_bus:02x} uses reserved width/mode bits."
        )

    if perm_wp_asserted:
        error_codes.append(BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD)
        errors.append(
            f"EXT_CSD[173] BOOT_WP=0x{boot_wp:02x} asserts irreversible permanent B_PERM_WP_EN (bit 2 or bit 6)."
        )

    if boot_cap != EMMC_BOOT_PARTITION_BYTES:
        error_codes.append(ERR_BOOTPART_BOOT_SIZE_MULT_MISMATCH)
        errors.append(
            f"EXT_CSD[226] BOOT_SIZE_MULT={boot_size_mult} ({boot_cap} B) != expected 4 MiB ({EMMC_BOOT_PARTITION_BYTES} B)."
        )

    return view, error_codes, errors


def audit_boot_wp_script_or_profile(
    profile_or_command: str,
    *,
    ext_csd_boot_wp: int = 0x00,
) -> BootWpFirewallDecision:
    """Fail-closed firewall blocking any script, profile, or EXT_CSD[173] setting B_PERM_WP_EN (bit 2 or bit 6)."""
    raw = (profile_or_command or "").strip()
    lower = raw.lower()
    bit2 = bool(ext_csd_boot_wp & EXT_CSD_BOOT_WP_PERM_EN_BIT2)
    bit6 = bool(ext_csd_boot_wp & EXT_CSD_BOOT_WP_PERM_EN_BIT6)

    perm_tokens = (
        "b_perm_wp_en",
        "writeprotect boot set",
        "boot_wp_perm",
        "ext_csd[173]",
        "ext_csd_173",
        "mmc switch 173",
        "switch 173",
    )
    has_perm_cmd = any(tok in lower for tok in perm_tokens) and (
        "-p" in lower
        or "perm" in lower
        or "0x04" in lower
        or "0x40" in lower
        or "0x44" in lower
        or "bit2" in lower
        or "bit 2" in lower
        or "bit6" in lower
        or "bit 6" in lower
    )
    # Also catch explicit `mmc writeprotect boot set -p` or `perm_wp` anywhere
    if re.search(r"writeprotect\s+boot\s+set\b.*\s-p(\s|$)", lower) or "b_perm_wp_en" in lower:
        has_perm_cmd = True

    hazard = bit2 or bit6 or has_perm_cmd
    error_codes: List[str] = []
    errors: List[str] = []
    if hazard:
        error_codes.append(BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD)
        errors.append(
            f"Blocked irreversible eMMC BOOT_WP permanent fuse hazard (EXT_CSD[173]=0x{ext_csd_boot_wp:02x}, "
            f"bit2={bit2}, bit6={bit6}, cmd='{raw[:80]}')."
        )
    elif not PERSISTENT_EMMC_WRITES_AUTHORIZED and any(
        verb in lower for verb in ("bootpart enable", "bootbus set", "write", "switch", "mmc")
    ):
        error_codes.append("PERSISTENT_EXT_CSD_MUTATION_LOCKED")
        errors.append(
            f"Persistent EXT_CSD write operation blocked under read-only safety lock (cmd='{raw[:80]}')."
        )

    allowed = (not hazard) and (len(errors) == 0)
    return BootWpFirewallDecision(
        allowed=allowed,
        status=STATUS_BLOCKED_BOOT_WP_FUSE_HAZARD if hazard else ("ALLOWED_READONLY_INSPECTION" if allowed else "BLOCKED_READONLY_POLICY"),
        profile_or_command=raw,
        ext_csd_boot_wp_byte=ext_csd_boot_wp & 0xFF,
        ext_csd_boot_wp_hex=f"0x{ext_csd_boot_wp & 0xFF:02x}",
        perm_wp_bit2_set=bit2,
        perm_wp_bit6_set=bit6,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
    )


def _is_boot_slot_intact(slot: BootPartitionSlotState) -> bool:
    return (
        slot.size_bytes == EMMC_BOOT_PARTITION_BYTES
        and slot.sector_aligned
        and (not slot.blank_or_erased)
        and slot.header_magic_valid
        and slot.sha256 == slot.expected_sha256
        and slot.sku_code == "ILME-FX3"
    )


def triage_emmc_boot_partitions_and_ext_csd(
    ext_csd: bytes,
    boot0_slot: BootPartitionSlotState,
    boot1_slot: BootPartitionSlotState,
    *,
    scenario_id: str = "CUSTOM_BOOTPART_TRIAGE",
) -> EmmcBootPartitionTriageReport:
    """Audit JEDEC eMMC BOOT0/BOOT1 hardware boot partitions & EXT_CSD [179]/[177]/[173]."""
    view, parse_codes, parse_errors = parse_ext_csd_boot_config(ext_csd)
    error_codes: List[str] = list(parse_codes)
    errors: List[str] = list(parse_errors)

    def _add(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    if boot0_slot.sku_code != "ILME-FX3" or boot1_slot.sku_code != "ILME-FX3":
        _add(
            ERR_BOOTPART_CROSS_SKU_TRANSPLANT,
            f"Cross-SKU boot partition transplant rejected (BOOT0={boot0_slot.sku_code}, BOOT1={boot1_slot.sku_code}).",
        )

    boot0_ok = _is_boot_slot_intact(boot0_slot)
    boot1_ok = _is_boot_slot_intact(boot1_slot)

    dead_trap = BOOT_PART_DISABLED_DEAD_BOOT_TRAP in error_codes
    perm_wp_hazard = BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD in error_codes
    part_acc_leak = PARTITION_ACCESS_NONZERO_LEAK in error_codes

    failover_to_boot1 = False
    mask_bootrom_required = False

    active_boot_en = view.boot_partition_enable if view is not None else BOOT_PART_ENABLE_DISABLED
    if active_boot_en == BOOT_PART_ENABLE_BOOT0 and (not boot0_ok) and boot1_ok:
        failover_to_boot1 = True
        _add(
            BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE,
            "Primary BOOT0 failed header/SHA-256 integrity while redundant 4 MiB BOOT1 is intact; "
            "offline failover to BOOT1 (PART_CONFIG BOOT_PARTITION_ENABLE=0x2) is viable.",
        )
    elif (not boot0_ok) and (not boot1_ok):
        mask_bootrom_required = True
        _add(
            ERR_BOOTPART_BOTH_CORRUPTED_MASK_BOOTROM_REQUIRED,
            "Both BOOT0 and BOOT1 failed integrity checks; CXD90057 falls back to Mask-BootROM USB 0x054C RAM-load recovery.",
        )
    elif active_boot_en == BOOT_PART_ENABLE_BOOT1 and (not boot1_ok) and boot0_ok:
        _add(
            "BOOT1_CORRUPTED_FALLBACK_TO_BOOT0_AVAILABLE",
            "Active BOOT1 failed integrity while BOOT0 is intact.",
        )

    if dead_trap and (not boot0_ok) and (not boot1_ok):
        mask_bootrom_required = True

    if perm_wp_hazard:
        status = STATUS_BLOCKED_BOOT_WP_FUSE_HAZARD
        recommended_action = "ABORT_IMMEDIATELY_REMOVE_B_PERM_WP_EN_BIT2_OR_BIT6_BEFORE_ANY_MMC_CMD"
    elif failover_to_boot1 and not (dead_trap or part_acc_leak):
        status = STATUS_EMMC_BOOT0_FAILOVER_TO_BOOT1
        recommended_action = "FAILOVER_TO_INTACT_BOOT1_OR_VERIFY_STAGE_B_ZERO_PERSISTENT_WRITES"
    elif len(error_codes) == 0 and boot0_ok and boot1_ok:
        status = STATUS_VERIFIED_EMMC_BOOTPART_HEALTHY
        recommended_action = "EMMC_BOOT0_BOOT1_AND_EXT_CSD_HEALTHY_ZERO_WRITES"
    else:
        status = STATUS_EMMC_BOOTPART_REJECTED
        recommended_action = (
            "ENTER_CXD90057_MASK_BOOTROM_USB_054C_RAM_LOAD_ONLY_SANDBOX"
            if mask_bootrom_required
            else "RESTORE_PART_CONFIG_PARTITION_ACCESS_0X0_AND_BOOT_ENABLE"
        )

    passed = (len(error_codes) == 0) and boot0_ok and boot1_ok
    payload_for_hash = {
        "scenario_id": scenario_id,
        "status": status,
        "passed": passed,
        "boot0_ok": boot0_ok,
        "boot1_ok": boot1_ok,
        "dead_trap": dead_trap,
        "failover_to_boot1": failover_to_boot1,
        "perm_wp_hazard": perm_wp_hazard,
        "part_acc_leak": part_acc_leak,
        "mask_bootrom_required": mask_bootrom_required,
        "error_codes": error_codes,
    }
    return EmmcBootPartitionTriageReport(
        passed=passed,
        triage_classified=True,
        status=status,
        scenario_id=scenario_id,
        ext_csd_view=view,
        boot0_intact=boot0_ok,
        boot1_intact=boot1_ok,
        dead_boot_trap_detected=dead_trap,
        failover_to_boot1_available=failover_to_boot1,
        permanent_boot_wp_hazard_detected=perm_wp_hazard,
        partition_access_nonzero_leak=part_acc_leak,
        mask_bootrom_fallback_required=mask_bootrom_required,
        recommended_action=recommended_action,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(payload_for_hash),
    )


def run_emmc_bootpart_6_scenario_triage() -> EmmcBootpart6ScenarioSuiteResult:
    """Execute the 6 canonical JEDEC eMMC BOOT0/BOOT1 & EXT_CSD anti-corruption scenarios."""
    _, healthy_b0 = build_synthetic_boot_partition_image(partition_name="BOOT0")
    _, healthy_b1 = build_synthetic_boot_partition_image(partition_name="BOOT1")
    _, corrupt_b0 = build_synthetic_boot_partition_image(partition_name="BOOT0", corrupt_payload=True)
    _, corrupt_b1 = build_synthetic_boot_partition_image(partition_name="BOOT1", corrupt_payload=True)

    # B1: Healthy stock BOOT0 active (0x48 = BOOT_ACK=1, BOOT0 enable=1, ACCESS=0)
    r1 = triage_emmc_boot_partitions_and_ext_csd(
        build_synthetic_ext_csd_boot_config(part_config=0x48, boot_bus_conditions=0x02, boot_wp=0x00),
        healthy_b0,
        healthy_b1,
        scenario_id=BOOTPART_SCENARIO_IDS[0],
    )
    # B2: Dead-boot trap (BOOT_PARTITION_ENABLE == 0x0 or 0x7 UDA mismatch)
    r2 = triage_emmc_boot_partitions_and_ext_csd(
        build_synthetic_ext_csd_boot_config(part_config=0x78),  # BOOT_PARTITION_ENABLE=0x7 (UDA mismatch)
        healthy_b0,
        healthy_b1,
        scenario_id=BOOTPART_SCENARIO_IDS[1],
    )
    # B3: BOOT0 corrupted while redundant BOOT1 intact
    r3 = triage_emmc_boot_partitions_and_ext_csd(
        build_synthetic_ext_csd_boot_config(part_config=0x48),
        corrupt_b0,
        healthy_b1,
        scenario_id=BOOTPART_SCENARIO_IDS[2],
    )
    # B4: PARTITION_ACCESS[2:0] != 0 leak after raw BOOT0 read
    r4 = triage_emmc_boot_partitions_and_ext_csd(
        build_synthetic_ext_csd_boot_config(part_config=0x49),  # ACCESS=1 (BOOT0) left active
        healthy_b0,
        healthy_b1,
        scenario_id=BOOTPART_SCENARIO_IDS[3],
    )
    # B5: Permanent BOOT_WP fuse hazard (EXT_CSD[173] bit 2 or bit 6)
    r5 = triage_emmc_boot_partitions_and_ext_csd(
        build_synthetic_ext_csd_boot_config(part_config=0x48, boot_wp=EXT_CSD_BOOT_WP_PERM_EN_BIT2),
        healthy_b0,
        healthy_b1,
        scenario_id=BOOTPART_SCENARIO_IDS[4],
    )
    # B6: Both BOOT0 and BOOT1 corrupted -> Mask-BootROM fallback required
    r6 = triage_emmc_boot_partitions_and_ext_csd(
        build_synthetic_ext_csd_boot_config(part_config=0x48),
        corrupt_b0,
        corrupt_b1,
        scenario_id=BOOTPART_SCENARIO_IDS[5],
    )

    wp_bit2_fw = audit_boot_wp_script_or_profile("ext_csd_173_write", ext_csd_boot_wp=EXT_CSD_BOOT_WP_PERM_EN_BIT2)
    wp_bit6_fw = audit_boot_wp_script_or_profile("ext_csd_173_write", ext_csd_boot_wp=EXT_CSD_BOOT_WP_PERM_EN_BIT6)
    wp_script_fw = audit_boot_wp_script_or_profile("mmc writeprotect boot set /dev/mmcblk0boot0 -p")

    results = (r1, r2, r3, r4, r5, r6)
    suite_errors: List[str] = []
    passed_count = 0

    if r1.passed and r1.status == STATUS_VERIFIED_EMMC_BOOTPART_HEALTHY:
        passed_count += 1
    else:
        suite_errors.append(f"B1 failed: {r1.error_codes}")

    if (not r2.passed) and r2.dead_boot_trap_detected and (BOOT_PART_DISABLED_DEAD_BOOT_TRAP in r2.error_codes):
        passed_count += 1
    else:
        suite_errors.append("B2 failed to detect BOOT_PART_DISABLED_DEAD_BOOT_TRAP")

    if (not r3.passed) and r3.failover_to_boot1_available and (BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE in r3.error_codes):
        passed_count += 1
    else:
        suite_errors.append("B3 failed to detect BOOT0_CORRUPTED_FAILOVER_TO_BOOT1_AVAILABLE")

    if (not r4.passed) and r4.partition_access_nonzero_leak and (PARTITION_ACCESS_NONZERO_LEAK in r4.error_codes):
        passed_count += 1
    else:
        suite_errors.append("B4 failed to detect PARTITION_ACCESS_NONZERO_LEAK")

    if (not r5.passed) and r5.permanent_boot_wp_hazard_detected and (BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD in r5.error_codes):
        passed_count += 1
    else:
        suite_errors.append("B5 failed to detect BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD")

    if (not r6.passed) and r6.mask_bootrom_fallback_required and (ERR_BOOTPART_BOTH_CORRUPTED_MASK_BOOTROM_REQUIRED in r6.error_codes):
        passed_count += 1
    else:
        suite_errors.append("B6 failed to trigger Mask-BootROM fallback on dual boot-partition corruption")

    for label, fw in (("bit2", wp_bit2_fw), ("bit6", wp_bit6_fw), ("script", wp_script_fw)):
        if fw.allowed or BLOCKED_PERMANENT_BOOT_WP_FUSE_HAZARD not in fw.error_codes or fw.physical_device_writes != 0:
            suite_errors.append(f"BOOT_WP firewall {label} failed to block permanent fuse hazard")

    for r in results:
        if r.physical_device_writes != 0 or r.persistent_emmc_writes_authorized or r.persistent_write_release:
            suite_errors.append(f"{r.scenario_id} violated zero-write invariant")

    all_ok = len(suite_errors) == 0 and passed_count == len(BOOTPART_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {
                "id": r.scenario_id,
                "status": r.status,
                "passed": r.passed,
                "error_codes": list(r.error_codes),
            }
            for r in results
        ],
        "wp_firewalls_blocked": [not wp_bit2_fw.allowed, not wp_bit6_fw.allowed, not wp_script_fw.allowed],
    }
    return EmmcBootpart6ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_BOOTROM_BOOTPART_GATE if all_ok else STATUS_FAIL_BOOTROM_BOOTPART_GATE,
        scenarios_passed=passed_count,
        scenarios_total=len(BOOTPART_SCENARIO_IDS),
        scenario_results=results,
        wp_bit2_firewall=wp_bit2_fw,
        wp_bit6_firewall=wp_bit6_fw,
        wp_script_firewall=wp_script_fw,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Pillar B — CXD90057 Mask-BootROM USB Cold-Plug & RAM_LOAD_ONLY Sandbox
# ---------------------------------------------------------------------------


def _classify_ram_xip_window(load_addr: int, entry_addr: int, payload_size: int) -> Tuple[bool, str]:
    if payload_size <= 0 or payload_size > BOOTROM_MAX_STAGE_PAYLOAD_BYTES:
        return False, "OUT_OF_RANGE"
    end_addr = load_addr + payload_size
    if CXD90057_SRAM_WINDOW_START <= load_addr and end_addr <= CXD90057_SRAM_WINDOW_END:
        if load_addr <= entry_addr < end_addr:
            return True, "SRAM_XIP"
        return False, "SRAM_ENTRY_OUT_OF_BOUNDS"
    if CXD90057_DRAM_WINDOW_START <= load_addr and end_addr <= CXD90057_DRAM_WINDOW_END:
        if load_addr <= entry_addr < end_addr:
            return True, "DRAM_XIP"
        return False, "DRAM_ENTRY_OUT_OF_BOUNDS"
    return False, "OUTSIDE_CXD90057_SRAM_DRAM"


def verify_bootrom_usb_coldplug_and_ram_sandbox(
    descriptor: UsbDeviceDescriptorSpec,
    stage_request: BootromPayloadStageRequest,
    *,
    scenario_id: str = "CUSTOM_BOOTROM_USB_SANDBOX",
) -> BootromUsbEnumerationReport:
    """Verify CXD90057 Mask-BootROM USB 0x054C cold-plug handshake & RAM_LOAD_ONLY XIP sandbox."""
    error_codes: List[str] = []
    errors: List[str] = []

    def _add(code: str, msg: str) -> None:
        if code not in error_codes:
            error_codes.append(code)
        errors.append(msg)

    if descriptor.vid != SONY_USB_VENDOR_ID:
        _add(
            ERR_BOOTROM_NON_SONY_USB_VID,
            f"USB Vendor ID 0x{descriptor.vid:04x} != Sony VID 0x054c.",
        )

    if descriptor.pid not in CXD90057_BOOTROM_USB_PIDS:
        _add(
            ERR_BOOTROM_UNSUPPORTED_PID,
            f"USB Product ID 0x{descriptor.pid:04x} is not a recognized CXD90057 BootROM/service PID.",
        )

    bulk_in_ok = (descriptor.bulk_in_ep & 0x80) == 0x80 and (descriptor.bulk_in_ep & 0x0F) != 0
    bulk_out_ok = (descriptor.bulk_out_ep & 0x80) == 0x00 and (descriptor.bulk_out_ep & 0x0F) != 0
    pkt_ok = descriptor.max_packet_size in CXD90057_VALID_USB_MAX_PACKET_SIZES
    bulk_ok = bulk_in_ok and bulk_out_ok and pkt_ok
    if not bulk_ok:
        _add(
            ERR_BOOTROM_INVALID_BULK_ENDPOINTS,
            f"Invalid USB bulk endpoints: IN=0x{descriptor.bulk_in_ep:02x}, OUT=0x{descriptor.bulk_out_ep:02x}, mps={descriptor.max_packet_size}.",
        )

    if descriptor.trigger_reason not in BOOTROM_VALID_TRIGGERS:
        _add(
            ERR_BOOTROM_UNRECOGNIZED_TRIGGER,
            f"Unrecognized Mask-BootROM cold-plug trigger '{descriptor.trigger_reason}'.",
        )

    if stage_request.target_mode != RAM_LOAD_ONLY:
        _add(
            ERR_BOOTROM_NON_RAM_LOAD_MODE_FORBIDDEN,
            f"Mask-BootROM target_mode '{stage_request.target_mode}' rejected; only '{RAM_LOAD_ONLY}' is permitted.",
        )

    for cmd in stage_request.commands:
        norm = cmd.strip().lower()
        if any(verb in norm for verb in FORBIDDEN_BOOTROM_PROGRAM_VERBS):
            _add(
                ERR_BOOTROM_PERSISTENT_PROGRAM_COMMAND_FORBIDDEN,
                f"Persistent eMMC/NOR/OTP program command '{cmd}' blocked in RAM_LOAD_ONLY BootROM sandbox.",
            )

    if stage_request.sku_code != "ILME-FX3":
        _add(
            ERR_BOOTROM_CROSS_SKU_PAYLOAD_REJECTED,
            f"Cross-SKU Mask-BootROM payload '{stage_request.sku_code}' rejected for FX3 CXD90057.",
        )

    ram_window_ok, mem_region = _classify_ram_xip_window(
        stage_request.load_address,
        stage_request.entry_address,
        stage_request.payload_size,
    )
    if not ram_window_ok:
        _add(
            ERR_BOOTROM_INVALID_RAM_XIP_WINDOW,
            f"Staging load=0x{stage_request.load_address:08x}, entry=0x{stage_request.entry_address:08x}, "
            f"size={stage_request.payload_size} outside valid CXD90057 SRAM/DRAM XIP window ({mem_region}).",
        )

    cold_plug_auth = (
        descriptor.vid == SONY_USB_VENDOR_ID
        and descriptor.pid in CXD90057_BOOTROM_USB_PIDS
        and bulk_ok
        and descriptor.trigger_reason in BOOTROM_VALID_TRIGGERS
    )
    ram_load_verified = (
        stage_request.target_mode == RAM_LOAD_ONLY
        and ram_window_ok
        and ERR_BOOTROM_PERSISTENT_PROGRAM_COMMAND_FORBIDDEN not in error_codes
        and ERR_BOOTROM_CROSS_SKU_PAYLOAD_REJECTED not in error_codes
    )
    passed = len(errors) == 0 and cold_plug_auth and ram_load_verified
    status = STATUS_VERIFIED_BOOTROM_RAM_LOAD_ONLY if passed else STATUS_REJECTED_BOOTROM_SANDBOX

    digest_payload = {
        "scenario_id": scenario_id,
        "status": status,
        "passed": passed,
        "vid": descriptor.vid,
        "pid": descriptor.pid,
        "trigger": descriptor.trigger_reason,
        "target_mode": stage_request.target_mode,
        "mem_region": mem_region,
        "load_addr": stage_request.load_address,
        "entry_addr": stage_request.entry_address,
        "emmc_persistent_program_commands": EMMC_PERSISTENT_PROGRAM_COMMANDS,
        "error_codes": error_codes,
    }
    return BootromUsbEnumerationReport(
        passed=passed,
        status=status,
        scenario_id=scenario_id,
        vid_hex=f"0x{descriptor.vid:04x}",
        pid_hex=f"0x{descriptor.pid:04x}",
        cold_plug_authenticated=cold_plug_auth,
        bulk_endpoints_valid=bulk_ok,
        trigger_reason=descriptor.trigger_reason,
        ram_load_only_verified=ram_load_verified,
        target_mode=stage_request.target_mode,
        memory_region=mem_region,
        load_address_hex=f"0x{stage_request.load_address:08x}",
        entry_address_hex=f"0x{stage_request.entry_address:08x}",
        emmc_persistent_program_commands=EMMC_PERSISTENT_PROGRAM_COMMANDS,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        error_codes=tuple(error_codes),
        errors=tuple(errors),
        report_sha256=_canonical_sha256(digest_payload),
    )


def run_bootrom_usb_5_scenario_sandbox() -> BootromUsb5ScenarioSuiteResult:
    """Execute the 5 canonical CXD90057 Mask-BootROM USB 0x054C & RAM_LOAD_ONLY scenarios."""
    r1 = verify_bootrom_usb_coldplug_and_ram_sandbox(
        UsbDeviceDescriptorSpec(trigger_reason="BOOT0_AND_BOOT1_FAILED"),
        BootromPayloadStageRequest(
            payload_name="fx3_sram_loader_xip",
            target_mode=RAM_LOAD_ONLY,
            load_address=CXD90057_SRAM_AWAKE_MEMADDR,
            entry_address=CXD90057_SRAM_LOADER_ENTRY,
            payload_size=PINNED_FX3_LOADER_NOR_BIN_BYTES,
            payload_sha256=PINNED_FX3_LOADER_NOR_BIN_SHA256,
        ),
        scenario_id=BOOTROM_SCENARIO_IDS[0],
    )
    r2 = verify_bootrom_usb_coldplug_and_ram_sandbox(
        UsbDeviceDescriptorSpec(trigger_reason="LAB_TEST_PAD_STRAP_SIMULATION"),
        BootromPayloadStageRequest(
            payload_name="fx3_stage_b_dram_xip",
            target_mode=RAM_LOAD_ONLY,
            load_address=CXD90057_DRAM_STAGE_B_BASE,
            entry_address=CXD90057_DRAM_STAGE_B_BASE,
            payload_size=6_610_952,
            payload_sha256=PINNED_FX3_LOADER_NOR_BIN_SHA256,
        ),
        scenario_id=BOOTROM_SCENARIO_IDS[1],
    )
    r3 = verify_bootrom_usb_coldplug_and_ram_sandbox(
        UsbDeviceDescriptorSpec(trigger_reason="BOOT0_AND_BOOT1_FAILED"),
        BootromPayloadStageRequest(
            payload_name="illegal_boot0_flasher",
            target_mode="EMMC_BOOT0_PROGRAM",
            commands=("emmc_program", "flash_boot0"),
        ),
        scenario_id=BOOTROM_SCENARIO_IDS[2],
    )
    r4 = verify_bootrom_usb_coldplug_and_ram_sandbox(
        UsbDeviceDescriptorSpec(vid=0x1234, pid=0x5678, trigger_reason="COLD_PLUG_RECOVERY_BUTTON"),
        BootromPayloadStageRequest(payload_name="unknown_vid_probe"),
        scenario_id=BOOTROM_SCENARIO_IDS[3],
    )
    r5 = verify_bootrom_usb_coldplug_and_ram_sandbox(
        UsbDeviceDescriptorSpec(trigger_reason="BOOT0_AND_BOOT1_FAILED"),
        BootromPayloadStageRequest(
            payload_name="fx6_cross_sku_loader",
            sku_code="ILME-FX6",
            payload_size=PINNED_FX6_INTERNAL_LOADER_NOR_BIN_BYTES,
            payload_sha256=PINNED_FX6_INTERNAL_LOADER_NOR_BIN_SHA256,
        ),
        scenario_id=BOOTROM_SCENARIO_IDS[4],
    )

    results = (r1, r2, r3, r4, r5)
    suite_errors: List[str] = []
    passed_count = 0

    if r1.passed and r1.memory_region == "SRAM_XIP" and r1.ram_load_only_verified:
        passed_count += 1
    else:
        suite_errors.append(f"M1 failed: {r1.error_codes}")

    if r2.passed and r2.memory_region == "DRAM_XIP" and r2.ram_load_only_verified:
        passed_count += 1
    else:
        suite_errors.append(f"M2 failed: {r2.error_codes}")

    if (
        (not r3.passed)
        and (ERR_BOOTROM_NON_RAM_LOAD_MODE_FORBIDDEN in r3.error_codes)
        and (ERR_BOOTROM_PERSISTENT_PROGRAM_COMMAND_FORBIDDEN in r3.error_codes)
    ):
        passed_count += 1
    else:
        suite_errors.append("M3 failed to block persistent eMMC program command")

    if (not r4.passed) and (ERR_BOOTROM_NON_SONY_USB_VID in r4.error_codes):
        passed_count += 1
    else:
        suite_errors.append("M4 failed to reject non-Sony USB VID")

    if (not r5.passed) and (ERR_BOOTROM_CROSS_SKU_PAYLOAD_REJECTED in r5.error_codes):
        passed_count += 1
    else:
        suite_errors.append("M5 failed to reject cross-SKU FX6 payload")

    for r in results:
        if (
            r.emmc_persistent_program_commands != 0
            or r.physical_device_writes != 0
            or r.persistent_emmc_writes_authorized
            or r.persistent_write_release
        ):
            suite_errors.append(f"{r.scenario_id} violated zero persistent eMMC program invariant")

    all_ok = len(suite_errors) == 0 and passed_count == len(BOOTROM_SCENARIO_IDS)
    suite_payload = {
        "scenarios": [
            {
                "id": r.scenario_id,
                "status": r.status,
                "passed": r.passed,
                "region": r.memory_region,
                "emmc_cmds": r.emmc_persistent_program_commands,
                "error_codes": list(r.error_codes),
            }
            for r in results
        ]
    }
    return BootromUsb5ScenarioSuiteResult(
        passed=all_ok,
        status=STATUS_VERIFIED_BOOTROM_BOOTPART_GATE if all_ok else STATUS_FAIL_BOOTROM_BOOTPART_GATE,
        scenarios_passed=passed_count,
        scenarios_total=len(BOOTROM_SCENARIO_IDS),
        scenario_results=results,
        emmc_persistent_program_commands=EMMC_PERSISTENT_PROGRAM_COMMANDS,
        errors=tuple(suite_errors),
        suite_sha256=_canonical_sha256(suite_payload),
    )


# ---------------------------------------------------------------------------
# Donor Read-Only Inspection & Clean-Room Synthetic Fallback
# ---------------------------------------------------------------------------


def inspect_bootrom_and_bootpart_donors_readonly(*, force_clean_room: Optional[bool] = None) -> DonorBootromBootpartSnapshot:
    """Inspect local FX3 v7.02 & FX6 v6.01 loader_nor / pformat_config / partinf.conf artifacts
    strictly via `os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`, with deterministic `CLEAN_ROOM_SYNTHETIC`
    fallback when forced or donor files are absent.
    """
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if not clean_room:
        fx3_ldr_bin_p = resolve_donor_path(DONOR_FX3_LOADER_NOR_BIN_RELPATH, require_file=True)
        fx3_pfmt_p = resolve_donor_path(DONOR_FX3_PFORMAT_CONFIG_RELPATH, require_file=True)
        fx3_ldr_tar_p = resolve_donor_path(DONOR_FX3_LOADER_NOR_TAR_RELPATH, require_file=True)
        fx6_ldr_tar_p = resolve_donor_path(DONOR_FX6_LOADER_NOR_TAR_RELPATH, require_file=True)
        fx3_part_p = resolve_donor_path(DONOR_FX3_PARTINF_CONF_RELPATH, require_file=True)
        fx6_part_p = resolve_donor_path(DONOR_FX6_PARTINF_CONF_RELPATH, require_file=True)
        all_present = all(
            p.is_file()
            for p in (fx3_ldr_bin_p, fx3_pfmt_p, fx3_ldr_tar_p, fx6_ldr_tar_p, fx3_part_p, fx6_part_p)
        )
    else:
        fx3_ldr_bin_p = fx3_pfmt_p = fx3_ldr_tar_p = fx6_ldr_tar_p = fx3_part_p = fx6_part_p = Path()
        all_present = False

    if all_present:
        mode = "LOCAL_DONOR_O_RDONLY"
        fx3_ldr_bytes = read_file(fx3_ldr_bin_p, 1024 * 1024)
        fx3_pfmt_bytes = read_file(fx3_pfmt_p, 256 * 1024)
        fx3_tar_bytes = read_file(fx3_ldr_tar_p, 1024 * 1024)
        fx6_tar_bytes = read_file(fx6_ldr_tar_p, 1024 * 1024)
        fx3_part_bytes = read_file(fx3_part_p, 256 * 1024)
        fx6_part_bytes = read_file(fx6_part_p, 256 * 1024)

        require(len(fx3_ldr_bytes) % 512 == 0 and len(fx3_ldr_bytes) > 0, "FX3 loader_nor.bin not 512B-aligned")
        require(not all(x in (0x00, 0xFF) for x in fx3_ldr_bytes[:512]), "FX3 loader_nor.bin header blank")

        pfmt_text = fx3_pfmt_bytes.decode("utf-8", errors="replace")
        require(
            "0xFE040800" in pfmt_text and "0xFE049000" in pfmt_text and "loader_nor.bin" in pfmt_text,
            "FX3 pformat_config.txt missing expected SRAM load anchors",
        )

        fx3_part_text = fx3_part_bytes.decode("utf-8", errors="replace")
        fx6_part_text = fx6_part_bytes.decode("utf-8", errors="replace")
        require(_parse_partinf_partition_count(fx3_part_text) >= 15, "FX3 partinf.conf partition count unexpected")
        require(_parse_partinf_partition_count(fx6_part_text) >= 15, "FX6 partinf.conf partition count unexpected")

        with tarfile.open(fileobj=io.BytesIO(fx6_tar_bytes), mode="r:*") as tf:
            member = tf.extractfile("loader_nor.bin")
            require(member is not None, "FX6 loader_nor.tar missing loader_nor.bin")
            assert member is not None
            fx6_internal_ldr = member.read()

        fx3_ldr_len = len(fx3_ldr_bytes)
        fx3_ldr_sha = sha256(fx3_ldr_bytes).hexdigest()
        fx3_pfmt_sha = sha256(fx3_pfmt_bytes).hexdigest()
        fx3_tar_sha = sha256(fx3_tar_bytes).hexdigest()
        fx6_tar_sha = sha256(fx6_tar_bytes).hexdigest()
        fx6_int_len = len(fx6_internal_ldr)
        fx6_int_sha = sha256(fx6_internal_ldr).hexdigest()
        fx3_part_sha = sha256(fx3_part_bytes).hexdigest()
        fx6_part_sha = sha256(fx6_part_bytes).hexdigest()
        fx3_pfmt_len = len(fx3_pfmt_bytes)
        fx3_tar_len = len(fx3_tar_bytes)
        fx6_tar_len = len(fx6_tar_bytes)
        fx3_part_len = len(fx3_part_bytes)
        fx6_part_len = len(fx6_part_bytes)
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx3_ldr_len = PINNED_FX3_LOADER_NOR_BIN_BYTES
        fx3_ldr_sha = PINNED_FX3_LOADER_NOR_BIN_SHA256
        fx3_pfmt_len = PINNED_FX3_PFORMAT_CONFIG_BYTES
        fx3_pfmt_sha = PINNED_FX3_PFORMAT_CONFIG_SHA256
        fx3_tar_len = PINNED_FX3_LOADER_NOR_TAR_BYTES
        fx3_tar_sha = PINNED_FX3_LOADER_NOR_TAR_SHA256
        fx6_tar_len = PINNED_FX6_LOADER_NOR_TAR_BYTES
        fx6_tar_sha = PINNED_FX6_LOADER_NOR_TAR_SHA256
        fx6_int_len = PINNED_FX6_INTERNAL_LOADER_NOR_BIN_BYTES
        fx6_int_sha = PINNED_FX6_INTERNAL_LOADER_NOR_BIN_SHA256
        fx3_part_len = PINNED_FX3_PARTINF_CONF_BYTES
        fx3_part_sha = PINNED_FX3_PARTINF_CONF_SHA256
        fx6_part_len = PINNED_FX6_PARTINF_CONF_BYTES
        fx6_part_sha = PINNED_FX6_PARTINF_CONF_SHA256

    cross_sku_distinct = (fx3_ldr_sha != fx6_int_sha) and (fx3_part_sha != fx6_part_sha)
    artifacts = (
        BootromBootpartDonorArtifactDigest(
            label="fx3_v702_loader_nor_bin",
            relpath=DONOR_FX3_LOADER_NOR_BIN_RELPATH,
            source_mode=mode,
            byte_length=fx3_ldr_len,
            sha256=fx3_ldr_sha,
            details="FX3 v7.02 SBL/loader_nor.bin SRAM load=0xFE049000",
        ),
        BootromBootpartDonorArtifactDigest(
            label="fx3_v702_pformat_config",
            relpath=DONOR_FX3_PFORMAT_CONFIG_RELPATH,
            source_mode=mode,
            byte_length=fx3_pfmt_len,
            sha256=fx3_pfmt_sha,
            details="FX3 v7.02 IPS-X pformat_config.txt (awake_memaddr=0xFE040800, start=72, size=200)",
        ),
        BootromBootpartDonorArtifactDigest(
            label="fx3_v702_loader_nor_tar",
            relpath=DONOR_FX3_LOADER_NOR_TAR_RELPATH,
            source_mode=mode,
            byte_length=fx3_tar_len,
            sha256=fx3_tar_sha,
            details="FX3 v7.02 0750_nor_loader/loader_nor.tar package",
        ),
        BootromBootpartDonorArtifactDigest(
            label="fx6_v601_loader_nor_tar",
            relpath=DONOR_FX6_LOADER_NOR_TAR_RELPATH,
            source_mode=mode,
            byte_length=fx6_tar_len,
            sha256=fx6_tar_sha,
            details=f"FX6 v6.01 loader_nor.tar (internal loader_nor.bin={fx6_int_len} B, sha256={fx6_int_sha[:16]})",
        ),
        BootromBootpartDonorArtifactDigest(
            label="fx3_v702_partinf_conf",
            relpath=DONOR_FX3_PARTINF_CONF_RELPATH,
            source_mode=mode,
            byte_length=fx3_part_len,
            sha256=fx3_part_sha,
            details="FX3 v7.02 UDA partition configuration table",
        ),
        BootromBootpartDonorArtifactDigest(
            label="fx6_v601_partinf_conf",
            relpath=DONOR_FX6_PARTINF_CONF_RELPATH,
            source_mode=mode,
            byte_length=fx6_part_len,
            sha256=fx6_part_sha,
            details="Cross-SKU FX6 v6.01 UDA partition configuration table",
        ),
    )

    snap_payload = {
        "mode": mode,
        "fx3_ldr_sha": fx3_ldr_sha,
        "fx3_pfmt_sha": fx3_pfmt_sha,
        "fx3_tar_sha": fx3_tar_sha,
        "fx6_tar_sha": fx6_tar_sha,
        "fx6_int_sha": fx6_int_sha,
        "fx3_part_sha": fx3_part_sha,
        "fx6_part_sha": fx6_part_sha,
    }
    return DonorBootromBootpartSnapshot(
        verification_mode=mode,
        read_only_access=READ_ONLY_DONOR_ACCESS,
        fx3_loader_nor_bin_bytes=fx3_ldr_len,
        fx3_loader_nor_bin_sha256=fx3_ldr_sha,
        fx3_pformat_config_sha256=fx3_pfmt_sha,
        fx3_loader_nor_tar_sha256=fx3_tar_sha,
        fx6_loader_nor_tar_sha256=fx6_tar_sha,
        fx6_internal_loader_nor_bin_bytes=fx6_int_len,
        fx6_internal_loader_nor_bin_sha256=fx6_int_sha,
        fx3_partinf_conf_sha256=fx3_part_sha,
        fx6_partinf_conf_sha256=fx6_part_sha,
        cross_sku_loader_distinct=cross_sku_distinct,
        artifacts=artifacts,
        snapshot_sha256=_canonical_sha256(snap_payload),
    )


# ---------------------------------------------------------------------------
# Master Suite Entrypoint (Pillar 13)
# ---------------------------------------------------------------------------


def run_bootrom_usb_and_emmc_bootpart_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> BootromUsbAndEmmcBootpartSuiteReport:
    """Run Phase 124 Pillar 13: O_RDONLY donor inspection, eMMC BOOT0/BOOT1 triage,
    and CXD90057 Mask-BootROM USB 0x054C RAM_LOAD_ONLY sandbox verification.
    """
    t0 = time.monotonic()
    donor_snap = inspect_bootrom_and_bootpart_donors_readonly(force_clean_room=force_clean_room)
    bootpart_suite = run_emmc_bootpart_6_scenario_triage()
    bootrom_suite = run_bootrom_usb_5_scenario_sandbox()

    errors: List[str] = []
    if not donor_snap.cross_sku_loader_distinct:
        errors.append("Cross-SKU FX3/FX6 loader_nor separation check failed.")
    errors.extend(bootpart_suite.errors)
    errors.extend(bootrom_suite.errors)

    all_passed = (
        donor_snap.cross_sku_loader_distinct
        and bootpart_suite.passed
        and bootrom_suite.passed
        and (PHYSICAL_DEVICE_WRITES == 0)
        and (EMMC_PERSISTENT_PROGRAM_COMMANDS == 0)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
    )
    suite_payload = {
        "schema": BOOTROM_USB_EMMC_BOOTPART_SCHEMA,
        "version": BOOTROM_USB_EMMC_BOOTPART_VERSION,
        "mode": donor_snap.verification_mode,
        "donor_sha256": donor_snap.snapshot_sha256,
        "bootpart_sha256": bootpart_suite.suite_sha256,
        "bootrom_sha256": bootrom_suite.suite_sha256,
        "all_passed": all_passed,
    }
    elapsed = round(time.monotonic() - t0, 4)
    return BootromUsbAndEmmcBootpartSuiteReport(
        schema=BOOTROM_USB_EMMC_BOOTPART_SCHEMA,
        version=BOOTROM_USB_EMMC_BOOTPART_VERSION,
        status=STATUS_VERIFIED_BOOTROM_BOOTPART_GATE if all_passed else STATUS_FAIL_BOOTROM_BOOTPART_GATE,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_passed,
        read_only_donor_access=READ_ONLY_DONOR_ACCESS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        emmc_persistent_program_commands=EMMC_PERSISTENT_PROGRAM_COMMANDS,
        donor_snapshot=donor_snap,
        emmc_bootpart_6_scenario_suite=bootpart_suite,
        bootrom_usb_5_scenario_suite=bootrom_suite,
        suite_sha256=_canonical_sha256(suite_payload),
        elapsed_seconds=elapsed,
        errors=tuple(errors),
    )
