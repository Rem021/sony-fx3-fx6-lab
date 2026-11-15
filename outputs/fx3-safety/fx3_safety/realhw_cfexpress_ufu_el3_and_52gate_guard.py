"""Phase 161 — Real-Hardware Main Track Part 13:
Gate G51 (Dual-Slot `CFexpress Type A / SDXC V90` Bitrate Gate, Card-Door GPIO
FIFO Flush, `PRIVATE/M4ROOT` & `XDROOT` Clip Preservation & Official
`BODYDATA.DAT` `\\x89UFU` Pre-Update Clean-Uninstall `H0 == H3` Guard),
Gate G52 (5-Tier Unbrickable Recovery Escalation Ladder, `ILME-FX3`
`0x91030080` `BODYDATA.DAT` Model-ID Lock & `CXD90057` EL3 `0xfe020000`
Read-Only Guard), and Unified 52-Gate Master Safety Preflight (`G01..G52` /
`verify-52-gates`).

Operationalizes media, official-updater coexistence, and 5-tier recovery
escalation invariants on physical Sony ILME-FX3 (`Ver. 7.02`, Model ID
`0x91030080`, SoC `CXD90057`) while keeping all prior gate modules (`G01..G50`)
100% untouched and hard-locking:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `overall_ready_for_hardware_attach = False`

1. **Dual-Mode Donor Inspection (`os.O_RDONLY`) + Clean-Room Fallback (`FX3_FX6_FORCE_CLEAN_ROOM=1`)**:
   - Inspects FX3 `7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`,
     and `Backup.bin` (`FX3-CX95900_ALLLANG-Backup.bin`) strictly via
     `os.open(..., os.O_RDONLY)` when present and `FX3_FX6_FORCE_CLEAN_ROOM != "1"`,
     plus an optional bounded `4096 B` `os.O_RDONLY` header check of
     `fx3-7.02-BODYDATA.DAT` when present.
   - Falls back deterministically to pinned clean-room metadata when
     `FX3_FX6_FORCE_CLEAN_ROOM=1` or donor files are absent, leaking zero raw
     Sony firmware bytes in JSON output.

2. **Gate G51 — Dual-Slot `CFexpress Type A / SDXC V90` Bitrate Gate,\n   Card-Door GPIO Flush & Official `BODYDATA.DAT` (`\\x89UFU`) Pre-Update Guard**:
   - Enforces media speed-class bitrate gate (`XAVC S-I 4K 120p 600 Mbps`
     rejected on `< V90` or non-`CFexpress Type A` cards).
   - Enforces card-door open GPIO FIFO flush before unmount
     (`unflushed_fifo_bytes_on_door_open == 0`, `fifo_flushed_before_umount == True`).
   - Enforces user clip directory preservation (`PRIVATE/M4ROOT` & `XDROOT`
     untouched across dual-boot switches).
   - Enforces Stage-A `< 100 µs` stock bypass whenever
     `/mnt/sd/BODYDATA.DAT` (`\\x89UFU\\r\\n\\x1a\\n`) is detected on Slot A/B,
     and blocks official firmware update launch until `p15:/usr` `.orig`
     clean-uninstall `H0 == H3` is verified.

3. **Gate G52 — 5-Tier Unbrickable Recovery Escalation Ladder,\n   `ILME-FX3` (`0x91030080`) `BODYDATA.DAT` Model-ID Lock &\n   `CXD90057` EL3 (`0xfe020000`) Read-Only Guard**:
   - Verifies all 5 non-destructive recovery tiers:
     `Tier-1 SD 47 µs` -> `Tier-2 p15 .orig` -> `Tier-3 same-model BODYDATA.DAT`
     -> `Tier-4 Multi-USB 1.8V UART EL3 read-only` -> `Tier-5 CID-matched eMMC ISP`.
   - Hard-blocks cross-model `BODYDATA.DAT` (`target_model_id != 0x91030080`).
   - Hard-locks `el3_payload_transmit_authorized == False`,
     `spi_nor_write_authorized == False`, and
     `persistent_emmc_writes_authorized == False`.

4. **Unified 52-Gate Master Safety Preflight (`evaluate_52gate_preflight` / CLI `verify-52-gates`)**:
   - Offline default reports `49/52` (`G10..G12` physical Tier-0 gates `False`,
     `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`,
     `spi_nor_write_authorized = False`,
     `el3_payload_transmit_authorized = False`,
     `overall_ready_for_hardware_attach = False`).
   - `--dry-run-simulated-backup` reports `52/52` dry-run green while STILL
     hard-locking `el3_payload_transmit_authorized = False`,
     `spi_nor_write_authorized = False`,
     `persistent_emmc_writes_authorized = False`,
     `persistent_write_release = False`, and
     `overall_ready_for_hardware_attach = False`.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import sys
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from .exfat_media_integrity_guard import MediaSlotConfig
from .master_16gate_preflight import (
    DEFAULT_REPO_ROOT,
    GateVerdict,
    P12_WLAN_FATAL_GUARD_VMA,
)
from .realhw_uart1v8_imx510_cal_and_50gate_guard import (
    Master50GateReport,
    evaluate_50gate_preflight,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_CFEXPRESS_UFU_EL3_52GATE_SCHEMA: str = (
    "fx3-realhw-cfexpress-ufu-el3-52gate-preflight-v1"
)
REALHW_CFEXPRESS_UFU_EL3_52GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False

# Gate IDs & Canonical Codes for G51..G52
G51_GATE_ID: str = "G51_cfexpress_sdxc_v90_card_door_gpio_and_bodydata_ufu_guard"
G51_GATE_CODE: str = "CFEXPRESS_SDXC_V90_CARD_DOOR_GPIO_AND_BODYDATA_UFU_GUARD"

G52_GATE_ID: str = "G52_5tier_unbrickable_recovery_fx3_model_id_and_el3_ro_guard"
G52_GATE_CODE: str = "5TIER_UNBRICKABLE_RECOVERY_FX3_MODEL_ID_AND_EL3_RO_GUARD"

# Status Codes
STATUS_SAFE: str = "SAFE"
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G51: str = (
    "VERIFIED_CFEXPRESS_SDXC_V90_CARD_DOOR_GPIO_AND_BODYDATA_UFU_GUARD"
)
STATUS_VERIFIED_G52: str = (
    "VERIFIED_5TIER_UNBRICKABLE_RECOVERY_FX3_MODEL_ID_AND_EL3_RO_GUARD"
)

# Gate G51 Violation Codes
STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT: str = (
    "BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT"
)
STATUS_BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO: str = (
    "BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO"
)
STATUS_BLOCKED_G51_USER_CLIP_DIR_MUTATION: str = (
    "BLOCKED_G51_USER_CLIP_DIR_MUTATION"
)
STATUS_BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD: str = (
    "BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD"
)
STATUS_BLOCKED_G51_TELEMETRY_INVALID: str = (
    "BLOCKED_G51_CFEXPRESS_UFU_TELEMETRY_INVALID"
)

# Gate G52 Violation Codes
STATUS_BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE: str = (
    "BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE"
)
STATUS_BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH: str = (
    "BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH"
)
STATUS_BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED: str = (
    "BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED"
)
STATUS_BLOCKED_G52_TELEMETRY_INVALID: str = (
    "BLOCKED_G52_5TIER_EL3_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE161_52GATE_DONOR_INTEGRITY_MISMATCH"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G51 Constants — Media Bitrate, Card-Door GPIO Flush, Clip Dirs & UFU
MEDIA_TYPE_CFEXPRESS_A: str = "CFEXPRESS_TYPE_A"
MEDIA_TYPE_SDXC_V90: str = "SDXC_V90"
MEDIA_TYPE_SDXC_V60: str = "SDXC_V60"
MEDIA_TYPE_SDXC_V30: str = "SDXC_V30"
MEDIA_TYPE_SDXC_UHS1: str = "SDXC_UHS1"

G51_VALID_MEDIA_TYPES: Tuple[str, ...] = (
    MEDIA_TYPE_CFEXPRESS_A,
    MEDIA_TYPE_SDXC_V90,
    MEDIA_TYPE_SDXC_V60,
    MEDIA_TYPE_SDXC_V30,
    MEDIA_TYPE_SDXC_UHS1,
)
G51_CFEXPRESS_SPEED_CLASSES: Tuple[str, ...] = ("VPG200", "VPG400")
G51_VALID_SPEED_CLASSES: Tuple[str, ...] = (
    "VPG400",
    "VPG200",
    "V90",
    "V60",
    "V30",
    "U3",
    "U1",
)
G51_MEDIA_MIN_SUSTAINED_MB_S: Mapping[str, float] = {
    "VPG400": 400.0,
    "VPG200": 200.0,
    "V90": 90.0,
    "V60": 60.0,
    "V30": 30.0,
    "U3": 30.0,
    "U1": 10.0,
}

XAVC_SI_4K120P_CODEC_PROFILE: str = "XAVC_SI_4K120P"
G51_XAVC_SI_4K120P_BITRATE_MBPS: float = 600.0
G51_XAVC_SI_OVERHEAD_MARGIN: float = 1.25  # 600 Mbps / 8 * 1.25 = 93.75 MB/s (> V90 90 MB/s)

G51_PROTECTED_CLIP_DIRS: Tuple[str, ...] = (
    "PRIVATE/M4ROOT",
    "XDROOT",
)

BODYDATA_UFU_MAGIC_BYTES: bytes = b"\x89UFU\r\n\x1a\n"
BODYDATA_UFU_MAGIC_HEX_STR: str = "895546550d0a1a0a"
BODYDATA_SD_CANDIDATE_PATHS: Tuple[str, ...] = (
    "/mnt/sd/BODYDATA.DAT",
    "/mnt/slot_a/BODYDATA.DAT",
    "/mnt/slot_b/BODYDATA.DAT",
    "/mnt/sd_a/BODYDATA.DAT",
    "/mnt/sd_b/BODYDATA.DAT",
)
G51_STAGE_A_BYPASS_NOMINAL_US: float = 47.0
G51_STAGE_A_BYPASS_MAX_US: float = 100.0
P15_USR_ORIG_MARKER: str = "p15:/usr/*.orig"
DEFAULT_SYNTHETIC_H0_STOCK_SHA256: str = "a" * 64
DEFAULT_SYNTHETIC_H3_POST_UNINSTALL_SHA256: str = "a" * 64

# Gate G52 Constants — 5-Tier Unbrickable Recovery, ILME-FX3 Model ID & EL3 RO
FX3_MODEL_ID_INT: int = 0x91030080
FX3_MODEL_ID_HEX: str = "0x91030080"
FX3_MODEL_NAME: str = "ILME-FX3"

CXD90057_SOC_NAME: str = "CXD90057"
CXD90057_EL3_LOAD_ADDR_INT: int = 0xFE020000
CXD90057_EL3_LOAD_ADDR_HEX: str = "0xfe020000"

RECOVERY_TIER_1_SD_47US: str = "TIER_1_SD_47US_STOCK_BYPASS"
RECOVERY_TIER_2_P15_ORIG: str = "TIER_2_P15_USR_ORIG_CLEAN_RESTORE"
RECOVERY_TIER_3_BODYDATA_UFU: str = "TIER_3_SAME_MODEL_BODYDATA_DAT"
RECOVERY_TIER_4_UART_EL3_RO: str = "TIER_4_MULTI_USB_1V8_UART_EL3_READ_ONLY"
RECOVERY_TIER_5_CID_EMMC_ISP: str = "TIER_5_CID_MATCHED_EMMC_ISP"

CANONICAL_5_RECOVERY_TIERS: Tuple[str, ...] = (
    RECOVERY_TIER_1_SD_47US,
    RECOVERY_TIER_2_P15_ORIG,
    RECOVERY_TIER_3_BODYDATA_UFU,
    RECOVERY_TIER_4_UART_EL3_RO,
    RECOVERY_TIER_5_CID_EMMC_ISP,
)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")
_HEX16_RE = re.compile(r"^[0-9a-f]{16}$")

# Pinned FX3 v7.02 Donor Specs (verified strictly via os.O_RDONLY)
PINNED_PHASE161_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_libsencore": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libsencore.so",
        377_328,
        "a2907111c4a22314dcb12c25889e0e3142764c6a4a910a746e43908f76e7c410",
        (
            b"\x7fELF",
            b"GPIO",
            b"SLOT",
            b"MEDIA",
            b"UART",
            b"RECOVERY",
        ),
        "fx3/libsencore.so::{ELF,GPIO,SLOT,MEDIA,UART,RECOVERY}",
    ),
    "fx3_libmpr": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so",
        3_517_008,
        "9aeef3b9edb3d011c0c90cd2387b3a47bd3b506ebfa57be39ad1a9729771b57c",
        (
            b"\x7fELF",
            b"M4ROOT",
            b"PRIVATE",
            b"XAVC",
            b"exfat",
            b"Eject",
            b"Flush",
            b"Recovery",
        ),
        "fx3/libmpr.so::{ELF,M4ROOT,PRIVATE,XAVC,exfat,Eject,Flush,Recovery}",
    ),
    "fx3_im_elf": (
        "fx3",
        "fx3-vm-20261101/fx3-audit/original-members/nflasha15/bin/im.elf",
        40_920,
        "5171f576d8b76cfbf15581389183b390c445bd6ff9dd97fd6668c5f64e77dc91",
        (
            b"\x7fELF",
            b"libIMDB.so",
            b"libbackup.so",
            b"libosal_uipc.so",
        ),
        "fx3/im.elf::{40920B,ELF,libIMDB.so,libbackup.so,libosal_uipc.so}",
    ),
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"UFU",
            b"PRIVATE",
            b"GPIO",
            b"SLOT",
            b"Flush",
            b"UART",
            b"Updata",
            b"Recovery",
            b"\x80\x00\x03\x91",
        ),
        "fx3/cpapp-b.bin::{ILME-FX3,0x91030080,UFU,PRIVATE,GPIO,SLOT,Flush,UART,Updata,Recovery}",
    ),
    "fx3_backup_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (
            b"BK4\x00",
            b"ILME-FX3",
            b"psd.bin",
            b"defdet.bin",
            b"lensfile.bin",
        ),
        "fx3/Backup.bin::{2229740B,BK4\\0,ILME-FX3,psd.bin,defdet.bin,lensfile.bin}",
    ),
}

PINNED_BODYDATA_HEADER_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
PINNED_BODYDATA_HEADER_READ_BYTES: int = 4096
PINNED_BODYDATA_TOTAL_BYTES: int = 811_876_768
PINNED_BODYDATA_HEADER_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)
PINNED_BODYDATA_HEADER_MARKERS: Tuple[bytes, ...] = (
    BODYDATA_UFU_MAGIC_BYTES,
    b"DATV",
    b"PROV",
    b"UDID",
)


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase161DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    bodydata_header_checked: bool
    bodydata_header_sha256: str
    bodydata_total_bytes: int
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CfexpressUfuPreUpdateGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    codec_profile: str
    codec_bitrate_mbps: float
    required_sustained_mb_s: float
    slot_a_inserted: bool
    slot_a_active: bool
    slot_a_media_type: str
    slot_a_speed_class: str
    slot_a_sustained_write_mb_s: float
    slot_b_inserted: bool
    slot_b_active: bool
    slot_b_media_type: str
    slot_b_speed_class: str
    slot_b_sustained_write_mb_s: float
    dual_slot_bitrate_gate_safe: bool
    card_door_gpio_irq_armed: bool
    card_door_open_event: bool
    fifo_flushed_before_umount: bool
    unflushed_fifo_bytes_on_door_open: int
    umount_completed_before_power_cut: bool
    card_door_gpio_flush_safe: bool
    protected_clip_dirs: Tuple[str, ...]
    m4root_mutation_bytes: int
    xdroot_mutation_bytes: int
    dual_boot_switch_user_clip_untouched: bool
    user_clip_preservation_safe: bool
    bodydata_dat_present: bool
    bodydata_slot: str
    bodydata_path: str
    bodydata_ufu_magic_hex: str
    bodydata_ufu_magic_valid: bool
    stage_a_stock_bypass_triggered: bool
    stage_a_bypass_latency_us: float
    official_fw_update_launch_requested: bool
    p15_usr_orig_clean_uninstall_verified: bool
    h0_stock_sha256: str
    h3_post_uninstall_sha256: str
    h0_equals_h3_verified: bool
    bodydata_ufu_preupdate_safe: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FiveTierRecoveryEl3GuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    guard_profile: str
    recovery_ladder: Tuple[str, ...]
    tier1_sd_47us_ready: bool
    tier1_bypass_latency_us: float
    tier2_p15_orig_ready: bool
    tier3_same_model_bodydata_ready: bool
    tier4_uart_el3_ro_ready: bool
    tier5_cid_emmc_isp_ready: bool
    tier5_cid_matched: bool
    destructive_tier_action_requested: bool
    recovery_ladder_safe: bool
    expected_model_id_hex: str
    target_model_id_hex: str
    target_model_name: str
    bodydata_ufu_magic_valid: bool
    cross_model_bodydata_attempted: bool
    model_id_lock_safe: bool
    soc_name: str
    el3_entry_addr_hex: str
    el3_monitor_mode: str
    el3_uart_tx_bytes: int
    el3_payload_transmit_requested: bool
    spi_nor_write_requested: bool
    persistent_emmc_write_requested: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    el3_readonly_guard_safe: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G51CfexpressUfuResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    cfexpress_ufu_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G52FiveTierEl3GuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    five_tier_el3_guard: Dict[str, Any]
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master52GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    offline_49_gates_verified: bool
    all_52_gates_verified: bool
    g13_to_g52_all_passed: bool
    g51_to_g52_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_50_report: Dict[str, Any]
    g51_result: Dict[str, Any]
    g52_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers (Strict os.O_RDONLY, zero raw bytes printing)
# ---------------------------------------------------------------------------


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip().lower() in (
        "1",
        "true",
        "yes",
        "on",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    """Strictly read a file via `os.open(..., os.O_RDONLY)` without leaking raw bytes."""
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


def _read_bounded_header_o_rdonly(path: Path, max_bytes: int) -> Tuple[int, bytes]:
    """Strictly read up to `max_bytes` from `path` via `os.open(..., os.O_RDONLY)`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        remaining = max(0, int(max_bytes))
        chunks: List[bytes] = []
        while remaining > 0:
            chunk = os.read(fd, min(remaining, 4096))
            if not chunk:
                break
            chunks.append(chunk)
            remaining -= len(chunk)
        return int(st.st_size), b"".join(chunks)
    finally:
        os.close(fd)


def _is_finite_number(val: Any) -> bool:
    return (
        isinstance(val, (int, float))
        and (not isinstance(val, bool))
        and math.isfinite(float(val))
    )


def _is_non_negative_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool)) and val >= 0


def _is_strict_int(val: Any) -> bool:
    return isinstance(val, int) and (not isinstance(val, bool))


def _parse_uint_or_hex(val: Any) -> Optional[int]:
    if _is_strict_int(val):
        return int(val) if int(val) >= 0 else None
    if isinstance(val, str):
        s = val.strip().lower()
        if not s:
            return None
        try:
            parsed = int(s, 16) if s.startswith("0x") else int(s, 10)
            return parsed if parsed >= 0 else None
        except ValueError:
            return None
    return None


# ---------------------------------------------------------------------------
# 1. Strictly Read-Only (O_RDONLY) Donor Contract Audit (FX3 7.02)
# ---------------------------------------------------------------------------


def audit_phase161_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
) -> Phase161DonorAuditResult:
    """Inspect FX3 `7.02` `libsencore.so`, `libmpr.so`, `im.elf`, `cpapp-b.bin`,
    and `Backup.bin` strictly via `os.open(..., os.O_RDONLY)` with deterministic
    clean-room fallback (plus optional bounded `4096 B` `BODYDATA.DAT` UFU header
    check when present).
    """
    clean_forced = _is_forced_clean_room(force_clean_room)
    paths = resolve_donor_thermal_power_paths(work_root=work_root, repo_root=repo_root)
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (
            _body,
            rel_path,
            _sz,
            _sha,
            _toks,
            _lbl,
        ) in PINNED_PHASE161_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        return Phase161DonorAuditResult(
            valid=True,
            status=STATUS_VERIFIED_SAFE,
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE161_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=True,
            bodydata_header_checked=False,
            bodydata_header_sha256=PINNED_BODYDATA_HEADER_SHA256,
            bodydata_total_bytes=PINNED_BODYDATA_TOTAL_BYTES,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE161_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE161_DONOR_SPECS.items()
            },
            errors=(),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    warnings: List[str] = []
    passed_keys: set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE161_DONOR_SPECS.items():
        blob = _read_file_o_rdonly(resolved[key])
        files_inspected += 1
        sha = hashlib.sha256(blob).hexdigest()
        shas[key] = sha
        sizes[key] = len(blob)

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = len(blob) == exp_size and sha == exp_sha

        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )

        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={len(blob)} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )

        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    bodydata_header_checked = False
    bodydata_header_sha = PINNED_BODYDATA_HEADER_SHA256
    bodydata_total_bytes = PINNED_BODYDATA_TOTAL_BYTES
    assert effective_work_root is not None
    bodydata_path = effective_work_root / PINNED_BODYDATA_HEADER_RELPATH
    if bodydata_path.is_file():
        bodydata_header_checked = True
        bd_total, bd_hdr = _read_bounded_header_o_rdonly(
            bodydata_path, PINNED_BODYDATA_HEADER_READ_BYTES
        )
        files_inspected += 1
        bd_sha = hashlib.sha256(bd_hdr).hexdigest()
        bodydata_header_sha = bd_sha
        bodydata_total_bytes = bd_total
        bd_label = "fx3/fx3-7.02-BODYDATA.DAT::{4096B_hdr,89UFU,DATV,PROV,UDID}"
        bd_missing = [m for m in PINNED_BODYDATA_HEADER_MARKERS if m not in bd_hdr]
        bd_ok = (
            bd_total == PINNED_BODYDATA_TOTAL_BYTES
            and bd_sha == PINNED_BODYDATA_HEADER_SHA256
            and bd_hdr.startswith(BODYDATA_UFU_MAGIC_BYTES)
            and (not bd_missing)
        )
        if not bd_missing:
            checked.append(bd_label)
        else:
            missing.append(bd_label)
            errors.append(
                f"Donor fx3-7.02-BODYDATA.DAT header missing {len(bd_missing)} marker(s)."
            )
        if not bd_ok:
            errors.append(
                f"Donor fx3-7.02-BODYDATA.DAT header mismatch: total={bd_total} "
                f"(expected {PINNED_BODYDATA_TOTAL_BYTES}), hdr_sha256={bd_sha} "
                f"(expected {PINNED_BODYDATA_HEADER_SHA256})."
            )

    fx3_keys = {
        k for k, spec in PINNED_PHASE161_DONOR_SPECS.items() if spec[0] == "fx3"
    }
    valid = len(errors) == 0 and len(missing) == 0
    return Phase161DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        bodydata_header_checked=bodydata_header_checked,
        bodydata_header_sha256=bodydata_header_sha,
        bodydata_total_bytes=bodydata_total_bytes,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 2. Pure Helper Functions
# ---------------------------------------------------------------------------


def compute_required_media_write_mb_s(
    codec_bitrate_mbps: float,
    overhead_margin: float = G51_XAVC_SI_OVERHEAD_MARGIN,
) -> float:
    """Compute required sustained media write rate in MB/s for a codec bitrate."""
    if (not _is_finite_number(codec_bitrate_mbps)) or (
        not _is_finite_number(overhead_margin)
    ):
        return 0.0
    if float(codec_bitrate_mbps) <= 0.0 or float(overhead_margin) < 1.0:
        return 0.0
    return round((float(codec_bitrate_mbps) / 8.0) * float(overhead_margin), 3)


def validate_dual_slot_media_bitrate(
    codec_profile: str = XAVC_SI_4K120P_CODEC_PROFILE,
    codec_bitrate_mbps: float = G51_XAVC_SI_4K120P_BITRATE_MBPS,
    *,
    slot_a_inserted: bool = True,
    slot_a_active: bool = True,
    slot_a_media_type: str = MEDIA_TYPE_CFEXPRESS_A,
    slot_a_speed_class: str = "VPG400",
    slot_a_sustained_write_mb_s: float = 400.0,
    slot_b_inserted: bool = True,
    slot_b_active: bool = False,
    slot_b_media_type: str = MEDIA_TYPE_SDXC_V90,
    slot_b_speed_class: str = "V90",
    slot_b_sustained_write_mb_s: float = 90.0,
) -> bool:
    """Enforce media speed-class bitrate gate across Slot A & Slot B.

    - `XAVC S-I 4K 120p 600 Mbps` is strictly rejected on `< V90` cards and on
      any non-`CFexpress Type A` card on an active recording slot.
    - Every active recording slot must meet both speed-class floor and
      `sustained_write_mb_s >= required_sustained_mb_s`.
    """
    if not isinstance(codec_profile, str) or not codec_profile.strip():
        return False
    if not _is_finite_number(codec_bitrate_mbps) or float(codec_bitrate_mbps) <= 0.0:
        return False
    for b in (slot_a_inserted, slot_a_active, slot_b_inserted, slot_b_active):
        if not isinstance(b, bool):
            return False

    if (not slot_a_active) and (not slot_b_active):
        return False

    required_mb_s = compute_required_media_write_mb_s(float(codec_bitrate_mbps))
    if required_mb_s <= 0.0:
        return False

    norm_profile = codec_profile.strip().upper().replace(" ", "_").replace("-", "_")
    is_4k120p_600m = (
        norm_profile in ("XAVC_SI_4K120P", "XAVC_S_I_4K120P", "XAVC_S_I_4K_120P")
        or ("4K120P" in norm_profile)
        or (float(codec_bitrate_mbps) >= G51_XAVC_SI_4K120P_BITRATE_MBPS)
    )

    slots = (
        (
            slot_a_inserted,
            slot_a_active,
            slot_a_media_type,
            slot_a_speed_class,
            slot_a_sustained_write_mb_s,
        ),
        (
            slot_b_inserted,
            slot_b_active,
            slot_b_media_type,
            slot_b_speed_class,
            slot_b_sustained_write_mb_s,
        ),
    )

    for inserted, active, mtype, sclass, write_mb_s in slots:
        if not isinstance(mtype, str) or mtype.strip().upper() not in G51_VALID_MEDIA_TYPES:
            if inserted or active:
                return False
            continue
        if not isinstance(sclass, str) or sclass.strip().upper() not in G51_VALID_SPEED_CLASSES:
            if inserted or active:
                return False
            continue
        if (not _is_finite_number(write_mb_s)) or float(write_mb_s) < 0.0:
            return False

        if not active:
            continue
        if not inserted:
            return False

        norm_type = mtype.strip().upper()
        norm_class = sclass.strip().upper()
        floor_mb_s = G51_MEDIA_MIN_SUSTAINED_MB_S[norm_class]

        if norm_type == MEDIA_TYPE_CFEXPRESS_A:
            if norm_class not in G51_CFEXPRESS_SPEED_CLASSES:
                return False
        else:
            # Non-CFexpress-A card cannot accept XAVC S-I 4K 120p 600 Mbps
            if is_4k120p_600m:
                return False
            if norm_type == MEDIA_TYPE_SDXC_V90 and norm_class != "V90":
                return False
            if norm_class not in ("V90",):
                # < V90 cards (V60/V30/U3/U1) rejected for high-bitrate XAVC S-I
                if float(codec_bitrate_mbps) >= 240.0 or "XAVC_S_I" in norm_profile or "XAVC_SI" in norm_profile:
                    return False

        if float(write_mb_s) < required_mb_s or float(write_mb_s) < floor_mb_s:
            return False

    return True


def validate_card_door_gpio_flush(
    *,
    card_door_gpio_irq_armed: bool = True,
    card_door_open_event: bool = False,
    fifo_flushed_before_umount: bool = True,
    unflushed_fifo_bytes_on_door_open: int = 0,
    umount_completed_before_power_cut: bool = True,
) -> bool:
    """Verify card-door open GPIO interrupt triggers FIFO flush before unmount."""
    for b in (
        card_door_gpio_irq_armed,
        card_door_open_event,
        fifo_flushed_before_umount,
        umount_completed_before_power_cut,
    ):
        if not isinstance(b, bool):
            return False
    if not _is_non_negative_int(unflushed_fifo_bytes_on_door_open):
        return False

    if not card_door_gpio_irq_armed:
        return False
    if int(unflushed_fifo_bytes_on_door_open) != 0:
        return False
    if not fifo_flushed_before_umount:
        return False
    if card_door_open_event and (not umount_completed_before_power_cut):
        return False
    return True


def validate_user_clip_dirs_untouched(
    *,
    m4root_mutation_bytes: int = 0,
    xdroot_mutation_bytes: int = 0,
    dual_boot_switch_user_clip_untouched: bool = True,
    protected_clip_dirs: Sequence[str] = G51_PROTECTED_CLIP_DIRS,
) -> bool:
    """Verify `PRIVATE/M4ROOT` & `XDROOT` remain untouched across dual-boot switches."""
    if not _is_non_negative_int(m4root_mutation_bytes):
        return False
    if not _is_non_negative_int(xdroot_mutation_bytes):
        return False
    if not isinstance(dual_boot_switch_user_clip_untouched, bool):
        return False
    norm_dirs = {str(d).strip().strip("/") for d in protected_clip_dirs if str(d).strip()}
    if not {"PRIVATE/M4ROOT", "XDROOT"}.issubset(norm_dirs):
        return False
    return (
        int(m4root_mutation_bytes) == 0
        and int(xdroot_mutation_bytes) == 0
        and dual_boot_switch_user_clip_untouched
    )


def validate_bodydata_ufu_and_clean_uninstall(
    *,
    bodydata_dat_present: bool = False,
    bodydata_path: str = "/mnt/sd/BODYDATA.DAT",
    bodydata_ufu_magic_hex: str = BODYDATA_UFU_MAGIC_HEX_STR,
    stage_a_stock_bypass_triggered: bool = True,
    stage_a_bypass_latency_us: float = G51_STAGE_A_BYPASS_NOMINAL_US,
    official_fw_update_launch_requested: bool = False,
    p15_usr_orig_clean_uninstall_verified: bool = True,
    h0_stock_sha256: str = DEFAULT_SYNTHETIC_H0_STOCK_SHA256,
    h3_post_uninstall_sha256: str = DEFAULT_SYNTHETIC_H3_POST_UNINSTALL_SHA256,
) -> bool:
    """Verify Stage-A `< 100 µs` stock bypass on `BODYDATA.DAT` (`\\x89UFU\\r\\n\\x1a\\n`)
    and block official firmware update launch until `p15:/usr` `.orig`
    clean-uninstall `H0 == H3` is verified.
    """
    for b in (
        bodydata_dat_present,
        stage_a_stock_bypass_triggered,
        official_fw_update_launch_requested,
        p15_usr_orig_clean_uninstall_verified,
    ):
        if not isinstance(b, bool):
            return False
    if not _is_finite_number(stage_a_bypass_latency_us):
        return False
    if float(stage_a_bypass_latency_us) < 0.0:
        return False
    if not isinstance(bodydata_path, str) or not bodydata_path.strip():
        return False
    if not isinstance(bodydata_ufu_magic_hex, str):
        return False
    norm_magic_hex = bodydata_ufu_magic_hex.strip().lower()
    if not _HEX16_RE.match(norm_magic_hex):
        return False
    if not isinstance(h0_stock_sha256, str) or not isinstance(h3_post_uninstall_sha256, str):
        return False
    h0_norm = h0_stock_sha256.strip().lower()
    h3_norm = h3_post_uninstall_sha256.strip().lower()
    if not (_HEX64_RE.match(h0_norm) and _HEX64_RE.match(h3_norm)):
        return False

    magic_ok = norm_magic_hex == BODYDATA_UFU_MAGIC_HEX_STR
    h0_eq_h3 = h0_norm == h3_norm

    if bodydata_dat_present:
        if not magic_ok:
            return False
        if not stage_a_stock_bypass_triggered:
            return False
        if float(stage_a_bypass_latency_us) >= G51_STAGE_A_BYPASS_MAX_US:
            return False

    if official_fw_update_launch_requested:
        if not magic_ok:
            return False
        if not stage_a_stock_bypass_triggered:
            return False
        if float(stage_a_bypass_latency_us) >= G51_STAGE_A_BYPASS_MAX_US:
            return False
        if not p15_usr_orig_clean_uninstall_verified:
            return False
        if not h0_eq_h3:
            return False

    return True


def validate_5tier_recovery_ladder(
    recovery_ladder: Sequence[str] = CANONICAL_5_RECOVERY_TIERS,
    *,
    tier1_sd_47us_ready: bool = True,
    tier1_bypass_latency_us: float = G51_STAGE_A_BYPASS_NOMINAL_US,
    tier2_p15_orig_ready: bool = True,
    tier3_same_model_bodydata_ready: bool = True,
    tier4_uart_el3_ro_ready: bool = True,
    tier5_cid_emmc_isp_ready: bool = True,
    tier5_cid_matched: bool = True,
    destructive_tier_action_requested: bool = False,
) -> bool:
    """Verify all 5 non-destructive recovery escalation tiers in exact order."""
    if tuple(str(t) for t in recovery_ladder) != CANONICAL_5_RECOVERY_TIERS:
        return False
    for b in (
        tier1_sd_47us_ready,
        tier2_p15_orig_ready,
        tier3_same_model_bodydata_ready,
        tier4_uart_el3_ro_ready,
        tier5_cid_emmc_isp_ready,
        tier5_cid_matched,
        destructive_tier_action_requested,
    ):
        if not isinstance(b, bool):
            return False
    if (not _is_finite_number(tier1_bypass_latency_us)) or float(tier1_bypass_latency_us) < 0.0:
        return False
    if float(tier1_bypass_latency_us) >= G51_STAGE_A_BYPASS_MAX_US:
        return False
    if destructive_tier_action_requested:
        return False
    return (
        tier1_sd_47us_ready
        and tier2_p15_orig_ready
        and tier3_same_model_bodydata_ready
        and tier4_uart_el3_ro_ready
        and tier5_cid_emmc_isp_ready
        and tier5_cid_matched
    )


def validate_fx3_model_id_bodydata_lock(
    target_model_id: Any = FX3_MODEL_ID_INT,
    target_model_name: str = FX3_MODEL_NAME,
    *,
    bodydata_ufu_magic_valid: bool = True,
    cross_model_bodydata_attempted: bool = False,
) -> bool:
    """Hard-block cross-model `BODYDATA.DAT` where `target_model_id != 0x91030080`."""
    if not isinstance(bodydata_ufu_magic_valid, bool) or not isinstance(
        cross_model_bodydata_attempted, bool
    ):
        return False
    if not isinstance(target_model_name, str):
        return False
    parsed_id = _parse_uint_or_hex(target_model_id)
    if parsed_id is None:
        return False
    if cross_model_bodydata_attempted:
        return False
    if not bodydata_ufu_magic_valid:
        return False
    if parsed_id != FX3_MODEL_ID_INT:
        return False
    if target_model_name.strip().upper() != FX3_MODEL_NAME:
        return False
    return True


def validate_cxd90057_el3_readonly_guard(
    *,
    soc_name: str = CXD90057_SOC_NAME,
    el3_entry_addr: Any = CXD90057_EL3_LOAD_ADDR_INT,
    el3_monitor_mode: str = "READ_ONLY",
    el3_uart_tx_bytes: int = 0,
    el3_payload_transmit_requested: bool = False,
    spi_nor_write_requested: bool = False,
    persistent_emmc_write_requested: bool = False,
) -> bool:
    """Enforce `CXD90057` EL3 (`0xfe020000`) strict read-only monitor lock."""
    if not isinstance(soc_name, str) or soc_name.strip().upper() != CXD90057_SOC_NAME:
        return False
    if not isinstance(el3_monitor_mode, str) or el3_monitor_mode.strip().upper() != "READ_ONLY":
        return False
    if not _is_non_negative_int(el3_uart_tx_bytes):
        return False
    for b in (
        el3_payload_transmit_requested,
        spi_nor_write_requested,
        persistent_emmc_write_requested,
    ):
        if not isinstance(b, bool):
            return False
    parsed_addr = _parse_uint_or_hex(el3_entry_addr)
    if parsed_addr is None or parsed_addr != CXD90057_EL3_LOAD_ADDR_INT:
        return False
    if int(el3_uart_tx_bytes) != 0:
        return False
    if el3_payload_transmit_requested or spi_nor_write_requested or persistent_emmc_write_requested:
        return False
    return True


# ---------------------------------------------------------------------------
# 3. Gate G51 & Gate G52 Core Evaluators
# ---------------------------------------------------------------------------


def verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(
    *,
    codec_profile: str = XAVC_SI_4K120P_CODEC_PROFILE,
    codec_bitrate_mbps: float = G51_XAVC_SI_4K120P_BITRATE_MBPS,
    slot_a_inserted: bool = True,
    slot_a_active: bool = True,
    slot_a_media_type: str = MEDIA_TYPE_CFEXPRESS_A,
    slot_a_speed_class: str = "VPG400",
    slot_a_sustained_write_mb_s: float = 400.0,
    slot_b_inserted: bool = True,
    slot_b_active: bool = False,
    slot_b_media_type: str = MEDIA_TYPE_SDXC_V90,
    slot_b_speed_class: str = "V90",
    slot_b_sustained_write_mb_s: float = 90.0,
    card_door_gpio_irq_armed: bool = True,
    card_door_open_event: bool = False,
    fifo_flushed_before_umount: bool = True,
    unflushed_fifo_bytes_on_door_open: int = 0,
    umount_completed_before_power_cut: bool = True,
    protected_clip_dirs: Sequence[str] = G51_PROTECTED_CLIP_DIRS,
    m4root_mutation_bytes: int = 0,
    xdroot_mutation_bytes: int = 0,
    dual_boot_switch_user_clip_untouched: bool = True,
    bodydata_dat_present: bool = False,
    bodydata_slot: str = "NONE",
    bodydata_path: str = "/mnt/sd/BODYDATA.DAT",
    bodydata_ufu_magic_hex: str = BODYDATA_UFU_MAGIC_HEX_STR,
    stage_a_stock_bypass_triggered: bool = True,
    stage_a_bypass_latency_us: float = G51_STAGE_A_BYPASS_NOMINAL_US,
    official_fw_update_launch_requested: bool = False,
    p15_usr_orig_clean_uninstall_verified: bool = True,
    h0_stock_sha256: str = DEFAULT_SYNTHETIC_H0_STOCK_SHA256,
    h3_post_uninstall_sha256: str = DEFAULT_SYNTHETIC_H3_POST_UNINSTALL_SHA256,
    guard_profile: str = "FX3_REALHW_G51_CFEXPRESS_V90_DOOR_UFU_DEFAULT",
) -> CfexpressUfuPreUpdateGuardResult:
    """Verify Gate G51 invariants fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    bool_inputs = (
        slot_a_inserted,
        slot_a_active,
        slot_b_inserted,
        slot_b_active,
        card_door_gpio_irq_armed,
        card_door_open_event,
        fifo_flushed_before_umount,
        umount_completed_before_power_cut,
        dual_boot_switch_user_clip_untouched,
        bodydata_dat_present,
        stage_a_stock_bypass_triggered,
        official_fw_update_launch_requested,
        p15_usr_orig_clean_uninstall_verified,
    )
    telemetry_ok = (
        all(isinstance(b, bool) for b in bool_inputs)
        and isinstance(codec_profile, str)
        and bool(codec_profile.strip())
        and _is_finite_number(codec_bitrate_mbps)
        and float(codec_bitrate_mbps) > 0.0
        and isinstance(slot_a_media_type, str)
        and slot_a_media_type.strip().upper() in G51_VALID_MEDIA_TYPES
        and isinstance(slot_a_speed_class, str)
        and slot_a_speed_class.strip().upper() in G51_VALID_SPEED_CLASSES
        and _is_finite_number(slot_a_sustained_write_mb_s)
        and float(slot_a_sustained_write_mb_s) >= 0.0
        and isinstance(slot_b_media_type, str)
        and slot_b_media_type.strip().upper() in G51_VALID_MEDIA_TYPES
        and isinstance(slot_b_speed_class, str)
        and slot_b_speed_class.strip().upper() in G51_VALID_SPEED_CLASSES
        and _is_finite_number(slot_b_sustained_write_mb_s)
        and float(slot_b_sustained_write_mb_s) >= 0.0
        and _is_non_negative_int(unflushed_fifo_bytes_on_door_open)
        and _is_non_negative_int(m4root_mutation_bytes)
        and _is_non_negative_int(xdroot_mutation_bytes)
        and isinstance(bodydata_slot, str)
        and isinstance(bodydata_path, str)
        and bool(bodydata_path.strip())
        and isinstance(bodydata_ufu_magic_hex, str)
        and _is_finite_number(stage_a_bypass_latency_us)
        and float(stage_a_bypass_latency_us) >= 0.0
        and isinstance(h0_stock_sha256, str)
        and bool(_HEX64_RE.match(h0_stock_sha256.strip().lower()))
        and isinstance(h3_post_uninstall_sha256, str)
        and bool(_HEX64_RE.match(h3_post_uninstall_sha256.strip().lower()))
        and isinstance(guard_profile, str)
        and bool(guard_profile.strip())
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G51_TELEMETRY_INVALID)
        errors.append("Gate G51 received invalid, non-finite, or malformed telemetry.")

    bitrate_safe = False
    door_flush_safe = False
    clip_safe = False
    ufu_safe = False

    req_mb_s = compute_required_media_write_mb_s(
        float(codec_bitrate_mbps) if _is_finite_number(codec_bitrate_mbps) else 0.0
    )

    norm_magic = (
        bodydata_ufu_magic_hex.strip().lower()
        if isinstance(bodydata_ufu_magic_hex, str)
        else ""
    )
    magic_valid = bool(_HEX16_RE.match(norm_magic)) and (
        norm_magic == BODYDATA_UFU_MAGIC_HEX_STR
    )
    h0_norm = h0_stock_sha256.strip().lower() if isinstance(h0_stock_sha256, str) else ""
    h3_norm = (
        h3_post_uninstall_sha256.strip().lower()
        if isinstance(h3_post_uninstall_sha256, str)
        else ""
    )
    h0_eq_h3 = (
        bool(_HEX64_RE.match(h0_norm))
        and bool(_HEX64_RE.match(h3_norm))
        and (h0_norm == h3_norm)
    )

    if telemetry_ok:
        bitrate_safe = validate_dual_slot_media_bitrate(
            codec_profile=codec_profile,
            codec_bitrate_mbps=float(codec_bitrate_mbps),
            slot_a_inserted=slot_a_inserted,
            slot_a_active=slot_a_active,
            slot_a_media_type=slot_a_media_type,
            slot_a_speed_class=slot_a_speed_class,
            slot_a_sustained_write_mb_s=float(slot_a_sustained_write_mb_s),
            slot_b_inserted=slot_b_inserted,
            slot_b_active=slot_b_active,
            slot_b_media_type=slot_b_media_type,
            slot_b_speed_class=slot_b_speed_class,
            slot_b_sustained_write_mb_s=float(slot_b_sustained_write_mb_s),
        )
        if not bitrate_safe:
            _add_code(codes, STATUS_BLOCKED_G51_MEDIA_SPEED_CLASS_INSUFFICIENT)
            errors.append(
                f"Active slot speed class/rate insufficient for {codec_profile} "
                f"({codec_bitrate_mbps} Mbps / req {req_mb_s} MB/s)."
            )

        door_flush_safe = validate_card_door_gpio_flush(
            card_door_gpio_irq_armed=card_door_gpio_irq_armed,
            card_door_open_event=card_door_open_event,
            fifo_flushed_before_umount=fifo_flushed_before_umount,
            unflushed_fifo_bytes_on_door_open=int(unflushed_fifo_bytes_on_door_open),
            umount_completed_before_power_cut=umount_completed_before_power_cut,
        )
        if not door_flush_safe:
            _add_code(codes, STATUS_BLOCKED_G51_CARD_DOOR_UNFLUSHED_FIFO)
            errors.append(
                f"Card-door GPIO flush violation: armed={card_door_gpio_irq_armed}, "
                f"flushed={fifo_flushed_before_umount}, unflushed={unflushed_fifo_bytes_on_door_open}B, "
                f"umount_ok={umount_completed_before_power_cut}."
            )

        clip_safe = validate_user_clip_dirs_untouched(
            m4root_mutation_bytes=int(m4root_mutation_bytes),
            xdroot_mutation_bytes=int(xdroot_mutation_bytes),
            dual_boot_switch_user_clip_untouched=dual_boot_switch_user_clip_untouched,
            protected_clip_dirs=protected_clip_dirs,
        )
        if not clip_safe:
            _add_code(codes, STATUS_BLOCKED_G51_USER_CLIP_DIR_MUTATION)
            errors.append(
                f"User clip directory preservation violation: PRIVATE/M4ROOT={m4root_mutation_bytes}B, "
                f"XDROOT={xdroot_mutation_bytes}B, untouched={dual_boot_switch_user_clip_untouched}."
            )

        ufu_safe = validate_bodydata_ufu_and_clean_uninstall(
            bodydata_dat_present=bodydata_dat_present,
            bodydata_path=bodydata_path,
            bodydata_ufu_magic_hex=bodydata_ufu_magic_hex,
            stage_a_stock_bypass_triggered=stage_a_stock_bypass_triggered,
            stage_a_bypass_latency_us=float(stage_a_bypass_latency_us),
            official_fw_update_launch_requested=official_fw_update_launch_requested,
            p15_usr_orig_clean_uninstall_verified=p15_usr_orig_clean_uninstall_verified,
            h0_stock_sha256=h0_stock_sha256,
            h3_post_uninstall_sha256=h3_post_uninstall_sha256,
        )
        if not ufu_safe:
            _add_code(codes, STATUS_BLOCKED_G51_BODYDATA_UFU_BYPASS_OR_UNINSTALL_GUARD)
            errors.append(
                f"BODYDATA.DAT UFU/clean-uninstall guard blocked: present={bodydata_dat_present}, "
                f"magic_valid={magic_valid}, bypass={stage_a_stock_bypass_triggered} "
                f"({stage_a_bypass_latency_us}us), update_launch={official_fw_update_launch_requested}, "
                f"orig_clean={p15_usr_orig_clean_uninstall_verified}, h0_eq_h3={h0_eq_h3}."
            )

    valid = (
        telemetry_ok
        and bitrate_safe
        and door_flush_safe
        and clip_safe
        and ufu_safe
        and (not codes)
    )
    status = STATUS_VERIFIED_G51 if valid else codes[0]

    return CfexpressUfuPreUpdateGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        codec_profile=str(codec_profile) if isinstance(codec_profile, str) else "INVALID",
        codec_bitrate_mbps=float(codec_bitrate_mbps) if _is_finite_number(codec_bitrate_mbps) else -1.0,
        required_sustained_mb_s=req_mb_s,
        slot_a_inserted=bool(slot_a_inserted) if isinstance(slot_a_inserted, bool) else False,
        slot_a_active=bool(slot_a_active) if isinstance(slot_a_active, bool) else False,
        slot_a_media_type=slot_a_media_type.strip().upper() if isinstance(slot_a_media_type, str) else "INVALID",
        slot_a_speed_class=slot_a_speed_class.strip().upper() if isinstance(slot_a_speed_class, str) else "INVALID",
        slot_a_sustained_write_mb_s=float(slot_a_sustained_write_mb_s) if _is_finite_number(slot_a_sustained_write_mb_s) else -1.0,
        slot_b_inserted=bool(slot_b_inserted) if isinstance(slot_b_inserted, bool) else False,
        slot_b_active=bool(slot_b_active) if isinstance(slot_b_active, bool) else False,
        slot_b_media_type=slot_b_media_type.strip().upper() if isinstance(slot_b_media_type, str) else "INVALID",
        slot_b_speed_class=slot_b_speed_class.strip().upper() if isinstance(slot_b_speed_class, str) else "INVALID",
        slot_b_sustained_write_mb_s=float(slot_b_sustained_write_mb_s) if _is_finite_number(slot_b_sustained_write_mb_s) else -1.0,
        dual_slot_bitrate_gate_safe=bitrate_safe,
        card_door_gpio_irq_armed=bool(card_door_gpio_irq_armed) if isinstance(card_door_gpio_irq_armed, bool) else False,
        card_door_open_event=bool(card_door_open_event) if isinstance(card_door_open_event, bool) else False,
        fifo_flushed_before_umount=bool(fifo_flushed_before_umount) if isinstance(fifo_flushed_before_umount, bool) else False,
        unflushed_fifo_bytes_on_door_open=int(unflushed_fifo_bytes_on_door_open) if _is_non_negative_int(unflushed_fifo_bytes_on_door_open) else -1,
        umount_completed_before_power_cut=bool(umount_completed_before_power_cut) if isinstance(umount_completed_before_power_cut, bool) else False,
        card_door_gpio_flush_safe=door_flush_safe,
        protected_clip_dirs=tuple(str(d) for d in protected_clip_dirs),
        m4root_mutation_bytes=int(m4root_mutation_bytes) if _is_non_negative_int(m4root_mutation_bytes) else -1,
        xdroot_mutation_bytes=int(xdroot_mutation_bytes) if _is_non_negative_int(xdroot_mutation_bytes) else -1,
        dual_boot_switch_user_clip_untouched=bool(dual_boot_switch_user_clip_untouched) if isinstance(dual_boot_switch_user_clip_untouched, bool) else False,
        user_clip_preservation_safe=clip_safe,
        bodydata_dat_present=bool(bodydata_dat_present) if isinstance(bodydata_dat_present, bool) else False,
        bodydata_slot=str(bodydata_slot) if isinstance(bodydata_slot, str) else "INVALID",
        bodydata_path=str(bodydata_path) if isinstance(bodydata_path, str) else "INVALID",
        bodydata_ufu_magic_hex=norm_magic,
        bodydata_ufu_magic_valid=magic_valid,
        stage_a_stock_bypass_triggered=bool(stage_a_stock_bypass_triggered) if isinstance(stage_a_stock_bypass_triggered, bool) else False,
        stage_a_bypass_latency_us=float(stage_a_bypass_latency_us) if _is_finite_number(stage_a_bypass_latency_us) else -1.0,
        official_fw_update_launch_requested=bool(official_fw_update_launch_requested) if isinstance(official_fw_update_launch_requested, bool) else False,
        p15_usr_orig_clean_uninstall_verified=bool(p15_usr_orig_clean_uninstall_verified) if isinstance(p15_usr_orig_clean_uninstall_verified, bool) else False,
        h0_stock_sha256=h0_norm,
        h3_post_uninstall_sha256=h3_norm,
        h0_equals_h3_verified=h0_eq_h3,
        bodydata_ufu_preupdate_safe=ufu_safe,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def verify_5tier_recovery_model_id_and_el3_ro_guard(
    *,
    recovery_ladder: Sequence[str] = CANONICAL_5_RECOVERY_TIERS,
    tier1_sd_47us_ready: bool = True,
    tier1_bypass_latency_us: float = G51_STAGE_A_BYPASS_NOMINAL_US,
    tier2_p15_orig_ready: bool = True,
    tier3_same_model_bodydata_ready: bool = True,
    tier4_uart_el3_ro_ready: bool = True,
    tier5_cid_emmc_isp_ready: bool = True,
    tier5_cid_matched: bool = True,
    destructive_tier_action_requested: bool = False,
    target_model_id: Any = FX3_MODEL_ID_INT,
    target_model_name: str = FX3_MODEL_NAME,
    bodydata_ufu_magic_valid: bool = True,
    cross_model_bodydata_attempted: bool = False,
    soc_name: str = CXD90057_SOC_NAME,
    el3_entry_addr: Any = CXD90057_EL3_LOAD_ADDR_INT,
    el3_monitor_mode: str = "READ_ONLY",
    el3_uart_tx_bytes: int = 0,
    el3_payload_transmit_requested: bool = False,
    spi_nor_write_requested: bool = False,
    persistent_emmc_write_requested: bool = False,
    guard_profile: str = "FX3_REALHW_G52_5TIER_MODEL_EL3_RO_DEFAULT",
) -> FiveTierRecoveryEl3GuardResult:
    """Verify Gate G52 invariants fail-closed."""
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    bool_inputs = (
        tier1_sd_47us_ready,
        tier2_p15_orig_ready,
        tier3_same_model_bodydata_ready,
        tier4_uart_el3_ro_ready,
        tier5_cid_emmc_isp_ready,
        tier5_cid_matched,
        destructive_tier_action_requested,
        bodydata_ufu_magic_valid,
        cross_model_bodydata_attempted,
        el3_payload_transmit_requested,
        spi_nor_write_requested,
        persistent_emmc_write_requested,
    )
    parsed_model_id = _parse_uint_or_hex(target_model_id)
    parsed_el3_addr = _parse_uint_or_hex(el3_entry_addr)

    telemetry_ok = (
        all(isinstance(b, bool) for b in bool_inputs)
        and isinstance(recovery_ladder, (tuple, list))
        and _is_finite_number(tier1_bypass_latency_us)
        and float(tier1_bypass_latency_us) >= 0.0
        and parsed_model_id is not None
        and isinstance(target_model_name, str)
        and bool(target_model_name.strip())
        and isinstance(soc_name, str)
        and bool(soc_name.strip())
        and parsed_el3_addr is not None
        and isinstance(el3_monitor_mode, str)
        and bool(el3_monitor_mode.strip())
        and _is_non_negative_int(el3_uart_tx_bytes)
        and isinstance(guard_profile, str)
        and bool(guard_profile.strip())
    )

    if not telemetry_ok:
        _add_code(codes, STATUS_BLOCKED_G52_TELEMETRY_INVALID)
        errors.append("Gate G52 received invalid, non-finite, or malformed telemetry.")

    ladder_safe = False
    model_lock_safe = False
    el3_ro_safe = False

    if telemetry_ok:
        ladder_safe = validate_5tier_recovery_ladder(
            recovery_ladder=recovery_ladder,
            tier1_sd_47us_ready=tier1_sd_47us_ready,
            tier1_bypass_latency_us=float(tier1_bypass_latency_us),
            tier2_p15_orig_ready=tier2_p15_orig_ready,
            tier3_same_model_bodydata_ready=tier3_same_model_bodydata_ready,
            tier4_uart_el3_ro_ready=tier4_uart_el3_ro_ready,
            tier5_cid_emmc_isp_ready=tier5_cid_emmc_isp_ready,
            tier5_cid_matched=tier5_cid_matched,
            destructive_tier_action_requested=destructive_tier_action_requested,
        )
        if not ladder_safe:
            _add_code(codes, STATUS_BLOCKED_G52_RECOVERY_LADDER_INCOMPLETE)
            errors.append(
                "5-tier unbrickable recovery escalation ladder incomplete, unordered, or destructive."
            )

        model_lock_safe = validate_fx3_model_id_bodydata_lock(
            target_model_id=target_model_id,
            target_model_name=target_model_name,
            bodydata_ufu_magic_valid=bodydata_ufu_magic_valid,
            cross_model_bodydata_attempted=cross_model_bodydata_attempted,
        )
        if not model_lock_safe:
            _add_code(codes, STATUS_BLOCKED_G52_CROSS_MODEL_BODYDATA_MISMATCH)
            errors.append(
                f"BODYDATA.DAT model lock mismatch: got {target_model_name} "
                f"(0x{parsed_model_id:08x}), expected {FX3_MODEL_NAME} ({FX3_MODEL_ID_HEX})."
            )

        el3_ro_safe = validate_cxd90057_el3_readonly_guard(
            soc_name=soc_name,
            el3_entry_addr=el3_entry_addr,
            el3_monitor_mode=el3_monitor_mode,
            el3_uart_tx_bytes=int(el3_uart_tx_bytes),
            el3_payload_transmit_requested=el3_payload_transmit_requested,
            spi_nor_write_requested=spi_nor_write_requested,
            persistent_emmc_write_requested=persistent_emmc_write_requested,
        )
        if not el3_ro_safe:
            _add_code(codes, STATUS_BLOCKED_G52_EL3_TRANSMIT_OR_WRITE_UNAUTHORIZED)
            errors.append(
                f"CXD90057 EL3 read-only guard blocked: mode={el3_monitor_mode}, "
                f"tx_bytes={el3_uart_tx_bytes}, el3_tx_req={el3_payload_transmit_requested}, "
                f"spi_nor_req={spi_nor_write_requested}, emmc_req={persistent_emmc_write_requested}."
            )

    valid = (
        telemetry_ok
        and ladder_safe
        and model_lock_safe
        and el3_ro_safe
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not PERSISTENT_WRITE_RELEASE)
        and (not codes)
    )
    status = STATUS_VERIFIED_G52 if valid else codes[0]

    return FiveTierRecoveryEl3GuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        guard_profile=str(guard_profile) if isinstance(guard_profile, str) else "INVALID",
        recovery_ladder=tuple(str(t) for t in recovery_ladder) if isinstance(recovery_ladder, (tuple, list)) else (),
        tier1_sd_47us_ready=bool(tier1_sd_47us_ready) if isinstance(tier1_sd_47us_ready, bool) else False,
        tier1_bypass_latency_us=float(tier1_bypass_latency_us) if _is_finite_number(tier1_bypass_latency_us) else -1.0,
        tier2_p15_orig_ready=bool(tier2_p15_orig_ready) if isinstance(tier2_p15_orig_ready, bool) else False,
        tier3_same_model_bodydata_ready=bool(tier3_same_model_bodydata_ready) if isinstance(tier3_same_model_bodydata_ready, bool) else False,
        tier4_uart_el3_ro_ready=bool(tier4_uart_el3_ro_ready) if isinstance(tier4_uart_el3_ro_ready, bool) else False,
        tier5_cid_emmc_isp_ready=bool(tier5_cid_emmc_isp_ready) if isinstance(tier5_cid_emmc_isp_ready, bool) else False,
        tier5_cid_matched=bool(tier5_cid_matched) if isinstance(tier5_cid_matched, bool) else False,
        destructive_tier_action_requested=bool(destructive_tier_action_requested) if isinstance(destructive_tier_action_requested, bool) else True,
        recovery_ladder_safe=ladder_safe,
        expected_model_id_hex=FX3_MODEL_ID_HEX,
        target_model_id_hex=f"0x{parsed_model_id:08x}" if parsed_model_id is not None else "INVALID",
        target_model_name=str(target_model_name) if isinstance(target_model_name, str) else "INVALID",
        bodydata_ufu_magic_valid=bool(bodydata_ufu_magic_valid) if isinstance(bodydata_ufu_magic_valid, bool) else False,
        cross_model_bodydata_attempted=bool(cross_model_bodydata_attempted) if isinstance(cross_model_bodydata_attempted, bool) else True,
        model_id_lock_safe=model_lock_safe,
        soc_name=str(soc_name) if isinstance(soc_name, str) else "INVALID",
        el3_entry_addr_hex=f"0x{parsed_el3_addr:08x}" if parsed_el3_addr is not None else "INVALID",
        el3_monitor_mode=str(el3_monitor_mode) if isinstance(el3_monitor_mode, str) else "INVALID",
        el3_uart_tx_bytes=int(el3_uart_tx_bytes) if _is_non_negative_int(el3_uart_tx_bytes) else -1,
        el3_payload_transmit_requested=bool(el3_payload_transmit_requested) if isinstance(el3_payload_transmit_requested, bool) else True,
        spi_nor_write_requested=bool(spi_nor_write_requested) if isinstance(spi_nor_write_requested, bool) else True,
        persistent_emmc_write_requested=bool(persistent_emmc_write_requested) if isinstance(persistent_emmc_write_requested, bool) else True,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        el3_readonly_guard_safe=el3_ro_safe,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G51 & Gate G52 Evaluators (Donor Audit + Guard -> GateVerdict)
# ---------------------------------------------------------------------------


def evaluate_g51_cfexpress_ufu(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    cfexpress_ufu_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase161DonorAuditResult] = None,
) -> Tuple[GateVerdict, G51CfexpressUfuResult]:
    """Evaluate Gate G51 (`CFexpress Type A / SDXC V90`, Card-Door GPIO Flush & `BODYDATA.DAT` UFU Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase161_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(cfexpress_ufu_kwargs or {})
    guard = verify_cfexpress_v90_door_gpio_and_bodydata_ufu_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Gate G51 blocked persistent eMMC write authorization request."
        )

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G51 if valid else codes[0]

    res = G51CfexpressUfuResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        cfexpress_ufu_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, codec={guard.codec_profile}@{guard.codec_bitrate_mbps:.0f}Mbps, "
        f"slotA={guard.slot_a_media_type}/{guard.slot_a_speed_class}(active={guard.slot_a_active}), "
        f"slotB={guard.slot_b_media_type}/{guard.slot_b_speed_class}(active={guard.slot_b_active}), "
        f"unflushed_fifo={guard.unflushed_fifo_bytes_on_door_open}B, "
        f"clip_mut={guard.m4root_mutation_bytes}/{guard.xdroot_mutation_bytes}B, "
        f"ufu_present={guard.bodydata_dat_present}, bypass_us={guard.stage_a_bypass_latency_us:.1f}, "
        f"h0_eq_h3={guard.h0_equals_h3_verified}"
    )

    verdict = GateVerdict(
        gate_id=G51_GATE_ID,
        gate_code=G51_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g52_5tier_el3_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    five_tier_el3_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase161DonorAuditResult] = None,
) -> Tuple[GateVerdict, G52FiveTierEl3GuardResult]:
    """Evaluate Gate G52 (`5-Tier Unbrickable Recovery`, `ILME-FX3` `0x91030080` & `CXD90057` EL3 RO Guard)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase161_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )

    guard_kwargs = dict(five_tier_el3_kwargs or {})
    if request_persistent_emmc_writes:
        guard_kwargs["persistent_emmc_write_requested"] = True
    guard = verify_5tier_recovery_model_id_and_el3_ro_guard(**guard_kwargs)

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE161_DONOR_INTEGRITY)

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append(
            "Gate G52 blocked persistent eMMC write authorization request."
        )

    valid = (
        audit.valid
        and guard.valid
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not codes)
    )
    status = STATUS_VERIFIED_G52 if valid else codes[0]

    res = G52FiveTierEl3GuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        five_tier_el3_guard=guard.to_dict(),
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )

    evidence = (
        f"mode={audit.verification_mode}, tiers=5/5, "
        f"model={guard.target_model_name}({guard.target_model_id_hex}), "
        f"el3={guard.soc_name}@{guard.el3_entry_addr_hex}({guard.el3_monitor_mode}, tx={guard.el3_uart_tx_bytes}B), "
        f"el3_tx_auth={EL3_PAYLOAD_TRANSMIT_AUTHORIZED}, "
        f"spi_nor_auth={SPI_NOR_WRITE_AUTHORIZED}, "
        f"emmc_auth={PERSISTENT_EMMC_WRITES_AUTHORIZED}"
    )

    verdict = GateVerdict(
        gate_id=G52_GATE_ID,
        gate_code=G52_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 52-Gate Master Safety Preflight (`G01..G52`)
# ---------------------------------------------------------------------------


def evaluate_52gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated_backup: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    # G01..G50 pass-throughs
    tier0_manifest: Optional[Dict[str, object]] = None,
    worker_syscall_trace: Optional[List[Dict[str, object]]] = None,
    init2_failsafe_hook: Optional[str] = None,
    candidate_bundle_verified: Optional[bool] = None,
    allow_dry_run_gate12: bool = False,
    gate12_kwargs: Optional[Mapping[str, Any]] = None,
    ltc_kwargs: Optional[Mapping[str, Any]] = None,
    mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    crsdk_requests: Optional[Sequence[Mapping[str, Any]]] = None,
    crsdk_kwargs: Optional[Mapping[str, Any]] = None,
    spacc_operations: Optional[Sequence[Mapping[str, Any]]] = None,
    spacc_script_text: str = "",
    spacc_sector0_bytes: Optional[bytes] = None,
    harness_kwargs: Optional[Mapping[str, Any]] = None,
    fan_kwargs: Optional[Mapping[str, Any]] = None,
    power_kwargs: Optional[Mapping[str, Any]] = None,
    soc_start_ceiling_c: Optional[float] = None,
    planned_mounts: Sequence[str] = (),
    planned_writes: Sequence[str] = (),
    c2pa_calibration_script_text: str = "",
    calibration_mutation_bytes: int = 0,
    c2pa_keystore_writes_attempted: bool = False,
    exfat_dirty_bit_present: bool = False,
    exfat_unfinalized_rsv_present: bool = False,
    allow_c2pa_or_calibration_write: bool = False,
    p12_vma: int = P12_WLAN_FATAL_GUARD_VMA,
    p12_patched_rc: int = 0,
    p12_guard_enabled: bool = True,
    bk4_airplane_shadow: Optional[Mapping[int, int]] = None,
    wf12_bootloop_immune: bool = True,
    wbi_mutation_bytes: int = 0,
    cp_mutation_bytes: int = 0,
    nvram_persistent_writes: int = 0,
    request_persistent_emmc_writes: bool = False,
    slot_a: Optional[MediaSlotConfig] = None,
    slot_b: Optional[MediaSlotConfig] = None,
    p1_vbr_bytes: Optional[bytes] = None,
    p1_image_path: Optional[Path] = None,
    p1_device_node: str = "/dev/nflasha1",
    require_at_least_one_lab_card: bool = True,
    usblan_kwargs: Optional[Mapping[str, Any]] = None,
    ptpip_or_mc_requests: Optional[Sequence[Any]] = None,
    ptpip_authenticated: bool = True,
    allow_protocol_3_00: bool = False,
    rig_kwargs: Optional[Mapping[str, Any]] = None,
    emount_kwargs: Optional[Mapping[str, Any]] = None,
    power_failover_kwargs: Optional[Mapping[str, Any]] = None,
    rsv_bytes: Optional[bytes] = None,
    rsv_path: Optional[Path] = None,
    xlr_kwargs: Optional[Mapping[str, Any]] = None,
    gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    dewpoint_kwargs: Optional[Mapping[str, Any]] = None,
    pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None,
    intake_fan_kwargs: Optional[Mapping[str, Any]] = None,
    tripod_housing_kwargs: Optional[Mapping[str, Any]] = None,
    sensor_curtain_kwargs: Optional[Mapping[str, Any]] = None,
    subzero_altitude_kwargs: Optional[Mapping[str, Any]] = None,
    wireless_tx_emi_kwargs: Optional[Mapping[str, Any]] = None,
    longform_endurance_kwargs: Optional[Mapping[str, Any]] = None,
    pl_cantilever_kwargs: Optional[Mapping[str, Any]] = None,
    dummy_battery_kwargs: Optional[Mapping[str, Any]] = None,
    saltspray_haze_kwargs: Optional[Mapping[str, Any]] = None,
    followfocus_gimbal_kwargs: Optional[Mapping[str, Any]] = None,
    hdmi_aoc_kwargs: Optional[Mapping[str, Any]] = None,
    cfexpress_media_kwargs: Optional[Mapping[str, Any]] = None,
    usbpd_uvc_kwargs: Optional[Mapping[str, Any]] = None,
    multiterminal_ptp_kwargs: Optional[Mapping[str, Any]] = None,
    monsoon_mishoe_kwargs: Optional[Mapping[str, Any]] = None,
    cagetwist_xlrh1_kwargs: Optional[Mapping[str, Any]] = None,
    vp_strobe_genlock_kwargs: Optional[Mapping[str, Any]] = None,
    vehiclerig_ibis_kwargs: Optional[Mapping[str, Any]] = None,
    jiritsu_service_kwargs: Optional[Mapping[str, Any]] = None,
    cnflasha_dualboot_kwargs: Optional[Mapping[str, Any]] = None,
    service_0336_canary_kwargs: Optional[Mapping[str, Any]] = None,
    stageb_mpr_ibis_p18_kwargs: Optional[Mapping[str, Any]] = None,
    pnflasha_mtdro_kwargs: Optional[Mapping[str, Any]] = None,
    rfnvs_fan_power_kwargs: Optional[Mapping[str, Any]] = None,
    uart1v8_isp_kwargs: Optional[Mapping[str, Any]] = None,
    imx510_sensor_cal_kwargs: Optional[Mapping[str, Any]] = None,
    # G51 inputs (CFexpress Type A / SDXC V90, card-door GPIO flush & BODYDATA.DAT UFU)
    cfexpress_ufu_kwargs: Optional[Mapping[str, Any]] = None,
    # G52 inputs (5-tier unbrickable recovery, ILME-FX3 0x91030080 & CXD90057 EL3 RO)
    five_tier_el3_kwargs: Optional[Mapping[str, Any]] = None,
) -> Master52GateReport:
    """Evaluate all 52 Master Safety Gates (`G01..G52`) deterministically."""
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)

    m50_kwargs: Dict[str, Any] = {
        "force_clean_room": clean_forced,
        "dry_run_simulated_backup": bool(dry_run_simulated_backup),
        "include_large_binaries": include_large_binaries,
        "work_root": work_root,
        "tier0_manifest": tier0_manifest,
        "worker_syscall_trace": worker_syscall_trace,
        "init2_failsafe_hook": init2_failsafe_hook,
        "candidate_bundle_verified": candidate_bundle_verified,
        "allow_dry_run_gate12": allow_dry_run_gate12,
        "gate12_kwargs": gate12_kwargs,
        "ltc_kwargs": ltc_kwargs,
        "mishoe_kwargs": mishoe_kwargs,
        "crsdk_requests": crsdk_requests,
        "crsdk_kwargs": crsdk_kwargs,
        "spacc_operations": spacc_operations,
        "spacc_script_text": spacc_script_text,
        "spacc_sector0_bytes": spacc_sector0_bytes,
        "harness_kwargs": harness_kwargs,
        "fan_kwargs": fan_kwargs,
        "power_kwargs": power_kwargs,
        "planned_mounts": planned_mounts,
        "planned_writes": planned_writes,
        "c2pa_calibration_script_text": c2pa_calibration_script_text,
        "calibration_mutation_bytes": calibration_mutation_bytes,
        "c2pa_keystore_writes_attempted": c2pa_keystore_writes_attempted,
        "exfat_dirty_bit_present": exfat_dirty_bit_present,
        "exfat_unfinalized_rsv_present": exfat_unfinalized_rsv_present,
        "allow_c2pa_or_calibration_write": allow_c2pa_or_calibration_write,
        "p12_vma": p12_vma,
        "p12_patched_rc": p12_patched_rc,
        "p12_guard_enabled": p12_guard_enabled,
        "bk4_airplane_shadow": bk4_airplane_shadow,
        "wf12_bootloop_immune": wf12_bootloop_immune,
        "wbi_mutation_bytes": wbi_mutation_bytes,
        "cp_mutation_bytes": cp_mutation_bytes,
        "nvram_persistent_writes": nvram_persistent_writes,
        "request_persistent_emmc_writes": request_persistent_emmc_writes,
        "slot_a": slot_a,
        "slot_b": slot_b,
        "p1_vbr_bytes": p1_vbr_bytes,
        "p1_image_path": p1_image_path,
        "p1_device_node": p1_device_node,
        "require_at_least_one_lab_card": require_at_least_one_lab_card,
        "usblan_kwargs": usblan_kwargs,
        "ptpip_or_mc_requests": ptpip_or_mc_requests,
        "ptpip_authenticated": ptpip_authenticated,
        "allow_protocol_3_00": allow_protocol_3_00,
        "rig_kwargs": rig_kwargs,
        "emount_kwargs": emount_kwargs,
        "power_failover_kwargs": power_failover_kwargs,
        "rsv_bytes": rsv_bytes,
        "rsv_path": rsv_path,
        "xlr_kwargs": xlr_kwargs,
        "gimbal_kwargs": gimbal_kwargs,
        "dewpoint_kwargs": dewpoint_kwargs,
        "pmic_usbc_kwargs": pmic_usbc_kwargs,
        "intake_fan_kwargs": intake_fan_kwargs,
        "tripod_housing_kwargs": tripod_housing_kwargs,
        "sensor_curtain_kwargs": sensor_curtain_kwargs,
        "subzero_altitude_kwargs": subzero_altitude_kwargs,
        "wireless_tx_emi_kwargs": wireless_tx_emi_kwargs,
        "longform_endurance_kwargs": longform_endurance_kwargs,
        "pl_cantilever_kwargs": pl_cantilever_kwargs,
        "dummy_battery_kwargs": dummy_battery_kwargs,
        "saltspray_haze_kwargs": saltspray_haze_kwargs,
        "followfocus_gimbal_kwargs": followfocus_gimbal_kwargs,
        "hdmi_aoc_kwargs": hdmi_aoc_kwargs,
        "cfexpress_media_kwargs": cfexpress_media_kwargs,
        "usbpd_uvc_kwargs": usbpd_uvc_kwargs,
        "multiterminal_ptp_kwargs": multiterminal_ptp_kwargs,
        "monsoon_mishoe_kwargs": monsoon_mishoe_kwargs,
        "cagetwist_xlrh1_kwargs": cagetwist_xlrh1_kwargs,
        "vp_strobe_genlock_kwargs": vp_strobe_genlock_kwargs,
        "vehiclerig_ibis_kwargs": vehiclerig_ibis_kwargs,
        "jiritsu_service_kwargs": jiritsu_service_kwargs,
        "cnflasha_dualboot_kwargs": cnflasha_dualboot_kwargs,
        "service_0336_canary_kwargs": service_0336_canary_kwargs,
        "stageb_mpr_ibis_p18_kwargs": stageb_mpr_ibis_p18_kwargs,
        "pnflasha_mtdro_kwargs": pnflasha_mtdro_kwargs,
        "rfnvs_fan_power_kwargs": rfnvs_fan_power_kwargs,
        "uart1v8_isp_kwargs": uart1v8_isp_kwargs,
        "imx510_sensor_cal_kwargs": imx510_sensor_cal_kwargs,
    }
    if soc_start_ceiling_c is not None:
        m50_kwargs["soc_start_ceiling_c"] = soc_start_ceiling_c

    m50_report: Master50GateReport = evaluate_50gate_preflight(
        resolved_root, **m50_kwargs
    )

    phase161_audit = audit_phase161_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g51_verdict, g51_res = evaluate_g51_cfexpress_ufu(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        cfexpress_ufu_kwargs=cfexpress_ufu_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase161_audit,
    )

    g52_verdict, g52_res = evaluate_g52_5tier_el3_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        five_tier_el3_kwargs=five_tier_el3_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase161_audit,
    )

    gates_51_to_52 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g51_verdict, g52_verdict)
    ]
    all_gates = tuple(list(m50_report.gates) + gates_51_to_52)

    g01_to_g12_verified = int(m50_report.summary["g01_to_g12_verified"])
    g13_to_g50_verified = (
        int(m50_report.summary["g13_to_g48_verified"])
        + int(m50_report.summary["g49_to_g50_verified"])
    )
    g51_to_g52_verified = sum(1 for v in (g51_verdict, g52_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g50_verified + g51_to_g52_verified

    g51_to_g52_all_passed = g51_to_g52_verified == 2
    g13_to_g52_all_passed = (
        m50_report.g13_to_g50_all_passed and g51_to_g52_all_passed
    )
    g01_to_g09_ok = all(bool(g["passed"]) for g in m50_report.gates[:9])

    offline_49_verified = (
        g01_to_g09_ok
        and m50_report.offline_47_gates_verified
        and g51_to_g52_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_52_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g52_all_passed
        and (not request_persistent_emmc_writes)
    )

    # Hard-locked False in offline and dry-run modes; never authorizes EL3 TX / eMMC / SPI-NOR writes
    overall_ready_for_hardware_attach = False

    h0_h1_allowed = (
        offline_49_verified
        and m50_report.h0_h1_trial_entry_allowed
        and g51_to_g52_all_passed
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m50_report.errors) + list(g51_verdict.errors) + list(g52_verdict.errors)
    )
    warnings: List[str] = (
        list(m50_report.warnings)
        + list(g51_verdict.warnings)
        + list(g52_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m50_report.g13_to_g50_all_passed:
        overall_status = m50_report.status
    elif not g51_verdict.passed:
        overall_status = g51_verdict.status
    elif not g52_verdict.passed:
        overall_status = g52_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_52_verified and dry_run_simulated_backup:
        overall_status = "VERIFIED_ALL_52_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_52_verified:
        overall_status = "VERIFIED_ALL_52_GATES"
    else:
        overall_status = "VERIFIED_49_OF_52_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m50_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g51_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g52_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 52,
        "verified_gates": total_verified,
        "blocked_or_pending_gates": 52 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g50_verified": g13_to_g50_verified,
        "g51_to_g52_verified": g51_to_g52_verified,
        "g13_to_g52_all_passed": g13_to_g52_all_passed,
        "g51_to_g52_all_passed": g51_to_g52_all_passed,
        "offline_49_gates_verified": offline_49_verified,
        "all_52_gates_verified": all_52_verified,
        "dry_run_rehearsal_only": bool(dry_run_simulated_backup),
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
    }

    return Master52GateReport(
        schema=REALHW_CFEXPRESS_UFU_EL3_52GATE_SCHEMA,
        version=REALHW_CFEXPRESS_UFU_EL3_52GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=bool(dry_run_simulated_backup),
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        offline_49_gates_verified=offline_49_verified,
        all_52_gates_verified=all_52_verified,
        g13_to_g52_all_passed=g13_to_g52_all_passed,
        g51_to_g52_all_passed=g51_to_g52_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        summary=summary,
        gates=all_gates,
        master_50_report=m50_report.to_dict(),
        g51_result=g51_res.to_dict(),
        g52_result=g52_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_52_master_safety_gates = evaluate_52gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_cfexpress_ufu_el3_and_52gate_guard",
        description=(
            "Phase 161 — Dual-Slot CFexpress Type A / SDXC V90 Bitrate, Card-Door GPIO Flush & "
            "BODYDATA.DAT UFU Pre-Update Guard (G51), 5-Tier Unbrickable Recovery, ILME-FX3 0x91030080 "
            "Model Lock & CXD90057 EL3 Read-Only Guard (G52), and 52-Gate Master Preflight (G01..G52)"
        ),
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=DEFAULT_REPO_ROOT,
        help="Path to sony-fx3-fx6-lab repository root",
    )
    parser.add_argument(
        "--clean-room",
        action="store_true",
        help="Force clean-room donorless mode",
    )
    parser.add_argument(
        "--dry-run-simulated-backup",
        action="store_true",
        help="Supply simulated dry-run Tier-0 backup inputs so G01..G52 can be exercised offline",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Emit structured JSON report",
    )
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_52gate_preflight(
        args.repo_root,
        force_clean_room=True if args.clean_room else None,
        dry_run_simulated_backup=bool(args.dry_run_simulated_backup),
    )
    if args.json:
        sys.stdout.write(
            json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n"
        )
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/52 "
            f"g51_to_g52_all_passed={report.g51_to_g52_all_passed} "
            f"all_52_gates_verified={report.all_52_gates_verified} "
            f"dry_run_rehearsal_only={report.dry_run_rehearsal_only} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach} "
            f"el3_payload_transmit_authorized={report.el3_payload_transmit_authorized} "
            f"spi_nor_write_authorized={report.spi_nor_write_authorized} "
            f"persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}\n"
        )
    ok = (
        report.all_52_gates_verified
        if args.dry_run_simulated_backup
        else report.offline_49_gates_verified
    )
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
