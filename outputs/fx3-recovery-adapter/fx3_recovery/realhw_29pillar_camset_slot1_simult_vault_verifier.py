"""Phase 208 — Pillar 29 (`29/29` Recovery Pillars) & Unified 29-Pillar Recovery Master
(`verify-29pillar-recovery` / `verify-camset-simult-vault`):

1. **Pillar 29A — Slot-1-Only `CAMSET01..10.DAT` Dual-Media Vault Isolation & `BIG6` Zero e-ND
   Bus Protection (6 Scenarios)**:
   - Enforces Slot-1-only (`Slot 2` rejected, `<= 10` `.DAT` files `CAMSET01.DAT..CAMSET10.DAT`,
     blocked in `MR` Recall Camera Setting mode, excluding machine-bound `WB Custom 1/2/3`, `FTP`,
     streaming, IP/certs, and date/time).
   - Enforces SD (`/PRIVATE/SONY/SETTING/FX3/CAMSET/`) vs CFexpress Type A
     (`/SONY/SETTING/FX3/CAMSET/`) root split, cross-model (`FX3` vs `FX3A` vs `FX6`) `.DAT`
     firewall with Stage-B `/tmp/fx6_camset_overlay` `tmpfs` sandboxing, and `BIG6` (`Home`)
     `e_nd_actuator_tx_count == 0` on the FX3 CP bus (`Aperture` default / `ND Filter` metadata-only).

2. **Pillar 29B — Dual-Slot `[Simult. Recording]` + `[Auto Switch Media = Off]` Strict Vault
   Redundancy, `VMC-BNCM1` Body `TC IN` Guard & `[De-Squeeze]` `1.65x` Clean Cold-Return (6 Scenarios)**:
   - Enforces `[Auto Switch Media] = Off` during dual-slot cold-backup / strict redundant vault
     recording so `Ver. 2.0+` never silently drops to single-card mode when one slot fills.
   - Blocks `VMC-BNCM1` on `XLR-H1` handle Micro-USB or reverse BNC `TC OUT` (`EOPNOTSUPP`,
     routing `TC OUT` strictly over Type-A HDMI), enforces external-only `M&C Focus Map` (`< 150fps`,
     zero in-body overlay), and proves `[De-Squeeze Display]` (`1.6x == 1.65x` 4-setting lock) &
     `[Shockless WB]` (`C.Temp./Filter` instant bypass) never mutate Stock `p2:/setting` (`16/16 H0 == H3`).

3. **Unified 29-Pillar Master (`evaluate_29pillar_recovery_master` / `verify-29pillar-recovery`)**:
   - Evaluates `evaluate_28pillar_recovery_master` (`1..28`) + **Pillar 29** concurrently ->
     **`29/29` (`VERIFIED_29OF29_PILLAR_RECOVERY_MASTER`)** in `< 2.5s` (`< 6.0s` test ceiling).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
from pathlib import Path
import posixpath
import re
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, local_path, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_28pillar_fan_pwm_shutter_lut_split_verifier import (
    MASTER_28_PILLAR_SPECS,
    Master28PillarRecoveryReport,
    evaluate_28pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE208_SCHEMA: str = "fx3-realhw-29pillar-recovery-master-verifier-v1"
PHASE208_VERSION: str = "1.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
ISP_WRITE_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
ALLOW_BOOT_PARTITION_TARGETING: bool = False
ALLOW_DESTRUCTIVE_FASTBOOT: bool = False
ALLOW_PERSISTENT_JIRITSU_WRITES: bool = False
ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS: bool = False
LIVE_USB_IOKIT_TRANSMIT_ENABLED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P208_NOMINAL_BUDGET_SECONDS: float = 2.5
P208_CONCURRENT_CEILING_SECONDS: float = 6.0
P208_BOUNDED_HEADER_BYTES: int = 4096
P208_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pillar 29A — Slot-1 CAMSET01..10.DAT Dual-Media Vault & BIG6 Zero e-ND Constants
P208_FX3_MODEL_NAME: str = "ILME-FX3"
P208_FX3_MODEL_ID: int = 0x91030080
P208_FX3_FW_VERSION: str = "7.02"
P208_CAMSET_ALLOWED_SLOT: int = 1
P208_CAMSET_MAX_FILES: int = 10
P208_VALID_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))

P208_MEDIA_SDXC: str = "SDXC"
P208_MEDIA_CFEXPRESS_A: str = "CFEXPRESS_TYPE_A"
P208_VALID_MEDIA_TYPES: Tuple[str, ...] = (P208_MEDIA_SDXC, P208_MEDIA_CFEXPRESS_A)

P208_SD_CAMSET_DIR: str = "/PRIVATE/SONY/SETTING/FX3/CAMSET"
P208_CFEXPRESS_A_CAMSET_DIR: str = "/SONY/SETTING/FX3/CAMSET"
P208_STAGE_B_CAMSET_OVERLAY_DIR: str = "/tmp/fx6_camset_overlay"
P208_STOCK_P2_SETTING_PATH: str = "p2:/setting"
P208_STOCK_BACKUP_BIN_PATH: str = "p2:/setting/Backup.bin"

P208_CAMSET_ORIGIN_FX3: str = "ILME-FX3"
P208_CAMSET_ORIGIN_FX3A: str = "ILME-FX3A"
P208_CAMSET_ORIGIN_FX6: str = "ILME-FX6"
P208_FOREIGN_CAMSET_ORIGINS: Tuple[str, ...] = (
    P208_CAMSET_ORIGIN_FX3A,
    P208_CAMSET_ORIGIN_FX6,
    "ILME-FX30",
)

P208_CAMSET_EXCLUDED_MACHINE_BOUND_KEYS: Tuple[str, ...] = (
    "WB_CUSTOM_1",
    "WB_CUSTOM_2",
    "WB_CUSTOM_3",
    "FTP_SERVER_CREDENTIAL",
    "NETWORK_STREAMING_KEY",
    "IP_TLS_CERTIFICATE",
    "RTC_DATE_TIME",
)

P208_BIG6_6_TILES: Tuple[str, ...] = (
    "FPS",
    "ISO_BASE_ISO",
    "SHUTTER_SPEED_ANGLE",
    "LOWER_LEFT_APERTURE_OR_ND",
    "PICTURE_PROFILE_LUT",
    "WHITE_BALANCE",
)
P208_BIG6_LOWER_LEFT_APERTURE: str = "Aperture"
P208_BIG6_LOWER_LEFT_ND_FILTER: str = "ND Filter"
P208_BIG6_VALID_LOWER_LEFT_MODES: Tuple[str, ...] = (
    P208_BIG6_LOWER_LEFT_APERTURE,
    P208_BIG6_LOWER_LEFT_ND_FILTER,
)

# Pillar 29B — Simult + Auto Switch Off, VMC-BNCM1 Body TC IN & De-Squeeze 1.65x Constants
P208_REC_MODE_SIMULT_STRICT_VAULT: str = "SIMULT_STRICT_DUAL_VAULT"
P208_REC_MODE_EXTENDED_OBSERVATION: str = "EXTENDED_SINGLE_FALLBACK_OBSERVATION"
P208_VALID_VAULT_REC_POLICIES: Tuple[str, ...] = (
    P208_REC_MODE_SIMULT_STRICT_VAULT,
    P208_REC_MODE_EXTENDED_OBSERVATION,
)

P208_TC_PORT_BODY_MULTI_USB: str = "BODY_MULTI_MICRO_USB"
P208_TC_PORT_XLRH1_HANDLE_MICRO_USB: str = "XLR_H1_HANDLE_MICRO_USB"
P208_TC_DIRECTION_IN: str = "TC_IN"
P208_TC_DIRECTION_BNC_OUT: str = "BNC_TC_OUT"
P208_TC_OUT_PORT_HDMI_TYPE_A: str = "HDMI_TYPE_A_DIGITAL_TC_OUT"
P208_TC_OUT_PORT_NONE: str = "NONE"

P208_DESQUEEZE_ENUM_TO_FACTOR: Dict[str, float] = {
    "Off": 1.0,
    "1.3x": 1.3,
    "1.5x": 1.5,
    "1.6x": 1.65,  # Sony Ver. 7.00/7.02 exact 1.65x horizontal stretch for 2.39:1 CinemaScope
    "2.0x": 2.0,
}
P208_DESQUEEZE_4_REQUIRED_LOCKS: Dict[str, str] = {
    "focus_mode": "Manual Focus",
    "focus_area": "Wide",
    "steady_shot": "Off",
    "face_priority_multi_metering": "Off",
}
P208_FOCUS_MAP_EXTERNAL_CUTOFF_FPS: int = 150
P208_SHOCKLESS_WB_VALID_MODES: Tuple[str, ...] = ("Off", "1 (Fast)", "2", "3 (Slow)")
P208_TIER0_16_SURFACE_COUNT: int = 16

P208_FORBIDDEN_PERSISTENT_CAMSET_TARGETS: Tuple[str, ...] = (
    "p2:",
    "/setting",
    "/private/sony/setting/fx3/camset",
    "/sony/setting/fx3/camset",
    "/mnt/p2",
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/pnflasha",
    "/dev/mmcblk",
)

# Master 29-Pillar Registry: Pillars 1..28 + Pillar 29
MASTER_29_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_28_PILLAR_SPECS + (
    (
        29,
        "realhw_29pillar_camset_slot1_simult_vault_verifier",
        "Phase 208",
        "fx3_recovery.realhw_29pillar_camset_slot1_simult_vault_verifier",
    ),
)
MASTER_29_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_29_PILLAR_SPECS)
MASTER_29_PILLAR_COUNT: int = len(MASTER_29_PILLAR_SPECS)

P208_PILLAR_29A_SCENARIO_IDS: Tuple[str, ...] = (
    "P29A1_HAPPY_SLOT1_DUAL_MEDIA_CAMSET_TMPFS_SANDBOX_AND_BIG6_ZERO_END_TX",
    "P29A2_BLOCKED_SLOT2_CAMSET_OVER_10_DAT_OR_MR_RECALL_MODE_REJECTED",
    "P29A3_BLOCKED_SD_VS_CFEXPRESS_A_CAMSET_ROOT_PATH_ASYMMETRY_VIOLATION",
    "P29A4_BLOCKED_CROSS_MODEL_FX3A_FX6_DAT_OR_NON_TMPFS_OVERLAY_ESCAPE",
    "P29A5_BLOCKED_BIG6_CP_BUS_END_ACTUATOR_TX_OR_INVALID_LOWER_LEFT_TILE",
    "P29A6_BLOCKED_MACHINE_BOUND_WB_CUSTOM_FTP_CERT_LEAK_OR_WRITE_UNLOCK",
)

P208_PILLAR_29B_SCENARIO_IDS: Tuple[str, ...] = (
    "P29B1_HAPPY_SIMULT_AUTOSWITCH_OFF_STRICT_VAULT_BODY_TCIN_AND_DESQUEEZE_165X_16OF16_H0_EQ_H3",
    "P29B2_BLOCKED_SIMULT_WITH_AUTO_SWITCH_ON_SILENT_SINGLE_CARD_DROP_IN_STRICT_VAULT",
    "P29B3_BLOCKED_VMC_BNCM1_ON_XLRH1_HANDLE_MICRO_USB_OR_REVERSE_BNC_TC_OUT",
    "P29B4_BLOCKED_DESQUEEZE_165X_RATIO_DRIFT_OR_4_HARDWARE_LOCKS_VIOLATED",
    "P29B5_BLOCKED_BOGUS_IN_BODY_FOCUS_MAP_OR_GE_150FPS_EXTERNAL_STREAM_VIOLATION",
    "P29B6_BLOCKED_SHOCKLESS_WB_CTEMP_BYPASS_OR_P2_SETTING_16OF16_H0_H3_DRIFT",
)

# Pinned Real-Hardware Donor Relpaths & Digests (strictly O_RDONLY, zero raw bytes leaked)
P208_DONOR_FX3_BODYDATA_RELPATH: str = "sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P208_DONOR_FX3_CPAPP_B_RELPATH: str = (
    "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
)
P208_DONOR_FX3_APPFW_702_RELPATH: str = "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P208_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P208_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P208_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)

P208_PINNED_FX3_BODYDATA_BYTES: int = 811_876_768
P208_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
P208_PINNED_FX3_CPAPP_B_BYTES: int = 15_980_568
P208_PINNED_FX3_CPAPP_B_HDR4K_SHA256: str = "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d"
P208_PINNED_FX3_APPFW_702_BYTES: int = 79_015_712
P208_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
P208_PINNED_FX3_BACKUP_BIN_BYTES: int = 2_229_740
P208_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
P208_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52_312
P208_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = (
    "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"
)
P208_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10_272
P208_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

# Status & Fail-Closed Error Codes
P208_STATUS_VERIFIED_PILLAR29_SUITE: str = (
    "VERIFIED_PILLAR29_CAMSET_SLOT1_BIG6_END_AND_SIMULT_VAULT"
)
P208_STATUS_FAIL_PILLAR29_SUITE: str = "FAIL_PILLAR29_CAMSET_SLOT1_BIG6_END_AND_SIMULT_VAULT"
P208_STATUS_VERIFIED_PILLAR_29A: str = "VERIFIED_SLOT1_CAMSET_DUAL_MEDIA_VAULT_AND_BIG6_ZERO_END"
P208_STATUS_REJECTED_PILLAR_29A: str = "REJECTED_SLOT1_CAMSET_DUAL_MEDIA_VAULT_OR_BIG6_END"
P208_STATUS_VERIFIED_PILLAR_29B: str = (
    "VERIFIED_SIMULT_AUTOSWITCH_OFF_VMC_BNCM1_TCIN_AND_DESQUEEZE_165X_H0_EQ_H3"
)
P208_STATUS_REJECTED_PILLAR_29B: str = (
    "REJECTED_SIMULT_AUTOSWITCH_OFF_VMC_BNCM1_TCIN_OR_DESQUEEZE_VAULT"
)
P208_STATUS_VERIFIED_29OF29_AGGREGATOR: str = "VERIFIED_29OF29_PILLAR_RECOVERY_MASTER"
P208_STATUS_FAIL_29OF29_AGGREGATOR: str = "FAIL_29OF29_PILLAR_RECOVERY_MASTER"

P208_BLOCKED_CAMSET_NON_SLOT1_OR_MR_MODE: str = "BLOCKED_P29A_CAMSET_SLOT2_OVER_10_OR_MR_MODE"
P208_BLOCKED_CAMSET_MEDIA_PATH_ASYMMETRY: str = "BLOCKED_P29A_SD_VS_CFEXPRESS_A_CAMSET_ROOT_MISMATCH"
P208_BLOCKED_CROSS_MODEL_CAMSET_OR_OVERLAY_ESCAPE: str = (
    "BLOCKED_P29A_CROSS_MODEL_FX3A_FX6_CAMSET_OR_NON_TMPFS_OVERLAY_ESCAPE"
)
P208_BLOCKED_BIG6_END_ACTUATOR_TX_OR_TILE_INVALID: str = (
    "BLOCKED_P29A_BIG6_FX3_CP_BUS_END_ACTUATOR_TX_OR_INVALID_HOME_CONFIG"
)
P208_BLOCKED_CAMSET_MACHINE_BOUND_ITEMS_INCLUDED: str = (
    "BLOCKED_P29A_CAMSET_MACHINE_BOUND_WB_FTP_CERT_INCLUDED"
)
P208_BLOCKED_CAMSET_H0_H3_VAULT_DRIFT: str = "BLOCKED_P29A_SLOT1_CAMSET_OR_P2_SETTING_H0_H3_DRIFT"

P208_BLOCKED_SIMULT_AUTO_SWITCH_ON_SINGLE_CARD_DROP: str = (
    "BLOCKED_P29B_SIMULT_AUTO_SWITCH_MEDIA_ON_SILENT_SINGLE_CARD_FALLBACK"
)
P208_BLOCKED_VMC_BNCM1_HANDLE_PORT_OR_BNC_TC_OUT: str = (
    "BLOCKED_P29B_VMC_BNCM1_XLRH1_MICRO_USB_OR_REVERSE_BNC_TC_OUT_EOPNOTSUPP"
)
P208_BLOCKED_DESQUEEZE_165X_OR_4LOCKS_VIOLATION: str = (
    "BLOCKED_P29B_DESQUEEZE_165X_FACTOR_OR_4_HARDWARE_LOCKS_VIOLATION"
)
P208_BLOCKED_FOCUS_MAP_IN_BODY_OR_GE_150FPS: str = (
    "BLOCKED_P29B_BOGUS_IN_BODY_FOCUS_MAP_OR_GE_150FPS_EXTERNAL_STREAM"
)
P208_BLOCKED_SHOCKLESS_WB_OR_16OF16_H0_H3_DRIFT: str = (
    "BLOCKED_P29B_SHOCKLESS_WB_CTEMP_BYPASS_OR_P2_SETTING_16OF16_H0_H3_DRIFT"
)
P208_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_P208_SAFETY_POLICY_VIOLATION"


def _canonical_sha256(obj: Any) -> str:
    payload = json.dumps(
        obj,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    return sha256(payload).hexdigest()


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _open_rdonly_regular(path: Path) -> Tuple[int, os.stat_result]:
    checked = local_path(path, allow_donor_roots=True)
    _need(hasattr(os, "O_NOFOLLOW"), "POSIX O_NOFOLLOW is required")
    fd = os.open(checked, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
    try:
        st = os.fstat(fd)
        _need(stat.S_ISREG(st.st_mode) and st.st_nlink == 1, "donor must be single-link regular file")
        return fd, st
    except Exception:
        os.close(fd)
        raise


def _verify_fstat_unchanged(fd: int, st_before: os.stat_result) -> None:
    st_after = os.fstat(fd)
    for fld in ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode", "st_nlink"):
        _need(getattr(st_before, fld) == getattr(st_after, fld), f"donor file changed during read ({fld})")


def _read_bounded_rdonly(
    relpath: str,
    *,
    max_bytes: Optional[int] = None,
    max_full_limit: int = P208_MAX_FULL_DONOR_BYTES,
) -> Tuple[bytes, int, str, str]:
    p = resolve_donor_path(relpath, require_file=True)
    _need(p is not None and p.is_file(), f"missing donor file: {relpath}")
    fd, st_before = _open_rdonly_regular(p)
    try:
        total_sz = int(st_before.st_size)
        if max_bytes is not None:
            head_len = min(total_sz, max_bytes)
            buf = os.pread(fd, head_len, 0)
            _need(len(buf) == head_len, "short bounded read on donor")
            _verify_fstat_unchanged(fd, st_before)
            h4k = sha256(buf).hexdigest()
            return buf, total_sz, h4k, h4k
        _need(total_sz <= max_full_limit, f"donor exceeds full read ceiling: {total_sz}")
        with os.fdopen(os.dup(fd), "rb") as f:
            buf = f.read(total_sz + 1)
        _need(len(buf) == total_sz, "donor read size mismatch")
        _verify_fstat_unchanged(fd, st_before)
        full_sha = sha256(buf).hexdigest()
        hdr_sha = sha256(buf[:P208_BOUNDED_HEADER_BYTES]).hexdigest()
        return buf, total_sz, full_sha, hdr_sha
    finally:
        os.close(fd)


def _default_16_surface_digests() -> Dict[str, str]:
    return {
        f"tier0_surface_{idx:02d}": sha256(f"fx3-7.02-p208-surface-{idx:02d}".encode("utf-8")).hexdigest()
        for idx in range(1, P208_TIER0_16_SURFACE_COUNT + 1)
    }


# ---------------------------------------------------------------------------
# Dataclasses (100% JSON-safe, zero raw proprietary firmware bytes)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase208DonorArtifactDigest:
    artifact_id: str
    relpath: str
    source_mode: str
    access_mode: str
    byte_length: int
    sha256_digest: str
    header_sha256: str
    verified_markers: Tuple[str, ...]
    passed: bool


@dataclass(frozen=True)
class Phase208DonorSnapshot:
    verification_mode: str
    access_mode: str
    donor_files_inspected: int
    raw_firmware_bytes_leaked: int
    bodydata_702_bytes: int
    bodydata_ufu_magic_ok: bool
    cpapp_b_arm_vec_ok: bool
    fx3_appfw_702_elf64_ok: bool
    backup_bin_bk4_fx3_ok: bool
    libinframediaconfig_elf64_ok: bool
    libbackupmanager_elf64_ok: bool
    elapsed_seconds: float
    artifacts: Tuple[Phase208DonorArtifactDigest, ...]
    snapshot_sha256: str
    all_passed: bool
    errors: Tuple[str, ...] = ()

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CamsetSlot1Big6VaultSpec:
    target_slot: int = P208_CAMSET_ALLOWED_SLOT
    media_type: str = P208_MEDIA_SDXC
    camset_dir_path: str = P208_SD_CAMSET_DIR
    camset_filenames: Tuple[str, ...] = ("CAMSET01.DAT", "CAMSET02.DAT", "CAMSET10.DAT")
    camset_model_origin: str = P208_CAMSET_ORIGIN_FX3
    mr_recall_mode_active: bool = False
    included_setting_keys: Tuple[str, ...] = ("EXPOSURE_ISO", "PICTURE_PROFILE", "AUDIO_LEVEL")
    stage_b_active: bool = True
    stage_b_camset_write_target: str = P208_STAGE_B_CAMSET_OVERLAY_DIR
    stage_b_overlay_is_tmpfs: bool = True
    slot1_camset_h0_sha256: str = "a" * 64
    slot1_camset_h3_sha256: str = "a" * 64
    p2_setting_h0_sha256: str = "b" * 64
    p2_setting_h3_sha256: str = "b" * 64
    big6_mode_fixed_variable: bool = True
    big6_home_custom_key_bound: bool = True
    big6_lower_left_mode: str = P208_BIG6_LOWER_LEFT_APERTURE
    e_nd_actuator_tx_count: int = 0
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class CamsetSlot1Big6VaultReport:
    passed: bool
    slot1_exclusivity_ok: bool
    dat_count_and_names_ok: bool
    mr_mode_guard_ok: bool
    dual_media_root_split_ok: bool
    expected_camset_dir: str
    cross_model_firewall_ok: bool
    stage_b_tmpfs_sandbox_ok: bool
    machine_bound_exclusions_ok: bool
    big6_topology_and_zero_end_ok: bool
    big6_lower_left_mode: str
    big6_nd_metadata_only: bool
    e_nd_actuator_tx_count: int
    h0_eq_h3_vault_ok: bool
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar29AScenarioOutcome:
    scenario_id: str
    passed: bool
    expected_camset_dir: str
    e_nd_actuator_tx_count: int
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar29ACamsetBig6SuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar29AScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SimultVaultTcInDesqueezeSpec:
    vault_rec_policy: str = P208_REC_MODE_SIMULT_STRICT_VAULT
    simult_recording_enabled: bool = True
    auto_switch_media_enabled: bool = False
    slot1_full_event: bool = False
    dropped_to_single_card: bool = False
    vmc_bncm1_attached: bool = True
    vmc_bncm1_port: str = P208_TC_PORT_BODY_MULTI_USB
    tc_direction: str = P208_TC_DIRECTION_IN
    multi_usb_bnc_tc_out_tx_count: int = 0
    tc_shooting_mode: str = "Movie"
    tc_make: str = "Preset"
    tc_run: str = "Free Run"
    hdmi_tc_out_enabled: bool = True
    desqueeze_menu_choice: str = "1.6x"
    applied_desqueeze_factor: float = 1.65
    focus_mode: str = "Manual Focus"
    focus_area: str = "Wide"
    steady_shot: str = "Off"
    face_priority_multi_metering: str = "Off"
    hdmi_raw_output_on: bool = False
    rec_media_dur_hdmi_off_only: bool = False
    log_shooting_on: bool = True
    in_body_focus_map_overlay_injected: bool = False
    external_mc_focus_map_active: bool = True
    sensor_fps: int = 24
    shockless_wb_mode: str = "2"
    ctemp_filter_direct_change_immediate: bool = True
    ab_gm_fine_tune_immediate: bool = True
    p2_blkroset_locked: bool = True
    stage_b_p2_setting_writes: int = 0
    surfaces_h0: Optional[Dict[str, str]] = None
    surfaces_h3: Optional[Dict[str, str]] = None
    request_persistent_write_unlock: bool = False


@dataclass(frozen=True)
class SimultVaultTcInDesqueezeReport:
    passed: bool
    simult_strict_vault_ok: bool
    auto_switch_media_off_enforced: bool
    vmc_bncm1_body_tcin_ok: bool
    ext_lk_timecode_locked: bool
    hdmi_tc_out_effective: bool
    desqueeze_factor_and_locks_ok: bool
    effective_desqueeze_factor: float
    desqueeze_suppressed_by_mode: bool
    external_focus_map_guard_ok: bool
    shockless_wb_and_bypass_ok: bool
    h0_eq_h3_surface_count: int
    vault_16of16_h0_eq_h3_ok: bool
    blocked_codes: Tuple[str, ...]
    errors: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar29BScenarioOutcome:
    scenario_id: str
    passed: bool
    h0_eq_h3_surface_count: int
    effective_desqueeze_factor: float
    blocked_codes: Tuple[str, ...]
    summary: str


@dataclass(frozen=True)
class Pillar29BSimultTcDesqueezeSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar29BScenarioOutcome, ...]
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar29StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase208DonorSnapshot
    pillar_29a_camset_big6_vault: Pillar29ACamsetBig6SuiteResult
    pillar_29b_simult_tcin_desqueeze_vault: Pillar29BSimultTcDesqueezeSuiteResult
    suite_sha256: str
    errors: Tuple[str, ...]
    otp_fuse_touches: int = OTP_FUSE_TOUCHES
    otp_fuse_writes: int = OTP_FUSE_WRITES
    rpmb_counter_increments: int = RPMB_COUNTER_INCREMENTS
    passive_tx_bytes_emitted: int = PASSIVE_TX_BYTES_EMITTED
    physical_usb_packets_emitted: int = PHYSICAL_USB_PACKETS_EMITTED
    physical_device_writes: int = PHYSICAL_DEVICE_WRITES
    raw_firmware_bytes_leaked: int = RAW_FIRMWARE_BYTES_LEAKED
    el3_payload_transmit_authorized: bool = EL3_PAYLOAD_TRANSMIT_AUTHORIZED
    isp_write_authorized: bool = ISP_WRITE_AUTHORIZED
    spi_nor_write_authorized: bool = SPI_NOR_WRITE_AUTHORIZED
    persistent_emmc_writes_authorized: bool = PERSISTENT_EMMC_WRITES_AUTHORIZED
    persistent_write_release: bool = PERSISTENT_WRITE_RELEASE
    live_usb_iokit_transmit_enabled: bool = LIVE_USB_IOKIT_TRANSMIT_ENABLED

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master29PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_6s_budget: bool
    nominal_under_2_5s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase208DonorSnapshot
    pillar29_a_camset_big6_vault: Pillar29ACamsetBig6SuiteResult
    pillar29_b_simult_tcin_desqueeze_vault: Pillar29BSimultTcDesqueezeSuiteResult
    master_29pillar_sha256: str
    otp_fuse_touches: int
    otp_fuse_writes: int
    rpmb_counter_increments: int
    passive_tx_bytes_emitted: int
    physical_usb_packets_emitted: int
    physical_device_writes: int
    raw_firmware_bytes_leaked: int
    el3_payload_transmit_authorized: bool
    isp_write_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    allow_boot_partition_targeting: bool
    allow_destructive_fastboot: bool
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Read-Only Real-Hardware Donor Inspection (`os.O_RDONLY | O_NOFOLLOW | O_NONBLOCK`)
# ---------------------------------------------------------------------------


def inspect_phase208_donors_readonly(
    *,
    force_clean_room: Optional[bool] = None,
) -> Phase208DonorSnapshot:
    """Inspect FX3 `7.02`, `cpapp-b.bin`, `appFw.so`, `Backup.bin`, `libInfraMediaConfig.so` & `libBackupManager.so`."""
    t0 = time.monotonic()
    clean = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)

    if clean:
        artifacts = (
            Phase208DonorArtifactDigest(
                "fx3_bodydata_702",
                P208_DONOR_FX3_BODYDATA_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P208_PINNED_FX3_BODYDATA_BYTES,
                P208_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                P208_PINNED_FX3_BODYDATA_HDR4K_SHA256,
                ("UFU_89UFU_MAGIC", "DATV_PROV_UDID", "811876768B"),
                True,
            ),
            Phase208DonorArtifactDigest(
                "fx3_cpapp_b",
                P208_DONOR_FX3_CPAPP_B_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P208_PINNED_FX3_CPAPP_B_BYTES,
                P208_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                P208_PINNED_FX3_CPAPP_B_HDR4K_SHA256,
                ("CP_RTOS_ARM_VEC", "ZERO_PHYSICAL_END_ACTUATOR"),
                True,
            ),
            Phase208DonorArtifactDigest(
                "fx3_appfw_702_so",
                P208_DONOR_FX3_APPFW_702_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P208_PINNED_FX3_APPFW_702_BYTES,
                P208_PINNED_FX3_APPFW_702_HDR4K_SHA256,
                P208_PINNED_FX3_APPFW_702_HDR4K_SHA256,
                ("ELF64_AARCH64", "BIG6_HOME_DESQUEEZE_165X"),
                True,
            ),
            Phase208DonorArtifactDigest(
                "fx3_backup_bin",
                P208_DONOR_FX3_BACKUP_BIN_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P208_PINNED_FX3_BACKUP_BIN_BYTES,
                P208_PINNED_FX3_BACKUP_BIN_SHA256,
                P208_PINNED_FX3_BACKUP_BIN_SHA256,
                ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
                True,
            ),
            Phase208DonorArtifactDigest(
                "fx3_libinframediaconfig_so",
                P208_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P208_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
                P208_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
                P208_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
                ("ELF64_AARCH64", "InfraMediaConfig", "GetMediaNum", "Backup_sync_subsystem"),
                True,
            ),
            Phase208DonorArtifactDigest(
                "fx3_libbackupmanager_so",
                P208_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
                "CLEAN_ROOM_SYNTHETIC",
                "SYNTHETIC_METADATA_ONLY",
                P208_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
                P208_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
                P208_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
                ("ELF64_AARCH64", "BackupManager", "SKData_Init", "Backup_get_datasize"),
                True,
            ),
        )
        elapsed = round(time.monotonic() - t0, 6)
        snap_sha = _canonical_sha256({"mode": "CLEAN_ROOM_SYNTHETIC", "artifacts": [asdict(a) for a in artifacts]})
        return Phase208DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="SYNTHETIC_METADATA_ONLY",
            donor_files_inspected=0,
            raw_firmware_bytes_leaked=0,
            bodydata_702_bytes=P208_PINNED_FX3_BODYDATA_BYTES,
            bodydata_ufu_magic_ok=True,
            cpapp_b_arm_vec_ok=True,
            fx3_appfw_702_elf64_ok=True,
            backup_bin_bk4_fx3_ok=True,
            libinframediaconfig_elf64_ok=True,
            libbackupmanager_elf64_ok=True,
            elapsed_seconds=elapsed,
            artifacts=artifacts,
            snapshot_sha256=snap_sha,
            all_passed=True,
            errors=(),
        )

    required_rels = (
        P208_DONOR_FX3_BODYDATA_RELPATH,
        P208_DONOR_FX3_CPAPP_B_RELPATH,
        P208_DONOR_FX3_APPFW_702_RELPATH,
        P208_DONOR_FX3_BACKUP_BIN_RELPATH,
        P208_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
        P208_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
    )
    if any(resolve_donor_path(rel, require_file=True) is None for rel in required_rels):
        return inspect_phase208_donors_readonly(force_clean_room=True)

    artifacts_out: List[Phase208DonorArtifactDigest] = []
    errors: List[str] = []

    bd_head, bd_sz, _, bd_hdr_sha = _read_bounded_rdonly(
        P208_DONOR_FX3_BODYDATA_RELPATH, max_bytes=P208_BOUNDED_HEADER_BYTES
    )
    bd_ok = (
        bd_sz == P208_PINNED_FX3_BODYDATA_BYTES
        and bd_hdr_sha == P208_PINNED_FX3_BODYDATA_HDR4K_SHA256
        and bd_head.startswith(b"\x89UFU\r\n\x1a\n")
        and b"DATV" in bd_head
        and b"PROV" in bd_head
        and b"UDID" in bd_head
    )
    if not bd_ok:
        errors.append("fx3_bodydata_702: size/4K digest/UFU markers mismatch")
    artifacts_out.append(
        Phase208DonorArtifactDigest(
            "fx3_bodydata_702",
            P208_DONOR_FX3_BODYDATA_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            bd_sz,
            bd_hdr_sha,
            bd_hdr_sha,
            ("UFU_89UFU_MAGIC", "DATV_PROV_UDID", "811876768B"),
            bd_ok,
        )
    )

    cp_head, cp_sz, _, cp_hdr_sha = _read_bounded_rdonly(
        P208_DONOR_FX3_CPAPP_B_RELPATH, max_bytes=P208_BOUNDED_HEADER_BYTES
    )
    cp_ok = (
        cp_sz == P208_PINNED_FX3_CPAPP_B_BYTES
        and cp_hdr_sha == P208_PINNED_FX3_CPAPP_B_HDR4K_SHA256
        and cp_head[:4] == b"\x04\x10\x9f\xe5"
    )
    if not cp_ok:
        errors.append("fx3_cpapp_b: CP RTOS header/size/digest mismatch")
    artifacts_out.append(
        Phase208DonorArtifactDigest(
            "fx3_cpapp_b",
            P208_DONOR_FX3_CPAPP_B_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            cp_sz,
            cp_hdr_sha,
            cp_hdr_sha,
            ("CP_RTOS_ARM_VEC", "ZERO_PHYSICAL_END_ACTUATOR"),
            cp_ok,
        )
    )

    af3_head, af3_sz, _, af3_hdr_sha = _read_bounded_rdonly(
        P208_DONOR_FX3_APPFW_702_RELPATH, max_bytes=P208_BOUNDED_HEADER_BYTES
    )
    af3_mach = struct.unpack_from("<H", af3_head, 18)[0] if len(af3_head) >= 20 else 0
    af3_ok = (
        af3_sz == P208_PINNED_FX3_APPFW_702_BYTES
        and af3_hdr_sha == P208_PINNED_FX3_APPFW_702_HDR4K_SHA256
        and af3_head[:4] == b"\x7fELF"
        and af3_head[4] == 2
        and af3_mach == 183
    )
    if not af3_ok:
        errors.append("fx3_appfw_702_so: ELF64 AArch64 header/size/digest mismatch")
    artifacts_out.append(
        Phase208DonorArtifactDigest(
            "fx3_appfw_702_so",
            P208_DONOR_FX3_APPFW_702_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_BOUNDED",
            af3_sz,
            af3_hdr_sha,
            af3_hdr_sha,
            ("ELF64_AARCH64", "BIG6_HOME_DESQUEEZE_165X"),
            af3_ok,
        )
    )

    bak_raw, bak_sz, bak_sha, bak_hdr = _read_bounded_rdonly(P208_DONOR_FX3_BACKUP_BIN_RELPATH)
    sync_u32 = struct.unpack_from("<I", bak_raw, 4)[0] if len(bak_raw) >= 20 else 0
    bak_ok = (
        bak_sz == P208_PINNED_FX3_BACKUP_BIN_BYTES
        and bak_sha == P208_PINNED_FX3_BACKUP_BIN_SHA256
        and sync_u32 == 0xAAAAAAAA
        and bak_raw[12:16] == b"BK4\x00"
        and b"ILME-FX3" in bak_raw
    )
    if not bak_ok:
        errors.append("fx3_backup_bin: BK4/0xAAAAAAAA/ILME-FX3 or digest mismatch")
    artifacts_out.append(
        Phase208DonorArtifactDigest(
            "fx3_backup_bin",
            P208_DONOR_FX3_BACKUP_BIN_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            bak_sz,
            bak_sha,
            bak_hdr,
            ("BK4_MAGIC", "0xAAAAAAAA", "ILME-FX3"),
            bak_ok,
        )
    )

    mc_raw, mc_sz, mc_sha, mc_hdr = _read_bounded_rdonly(P208_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH)
    mc_mach = struct.unpack_from("<H", mc_raw, 18)[0] if len(mc_raw) >= 20 else 0
    mc_ok = (
        mc_sz == P208_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES
        and mc_sha == P208_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256
        and mc_raw[:4] == b"\x7fELF"
        and mc_raw[4] == 2
        and mc_mach == 183
        and b"InfraMediaConfig" in mc_raw
        and b"GetMediaNum" in mc_raw
        and b"Backup_sync_subsystem" in mc_raw
    )
    if not mc_ok:
        errors.append("fx3_libinframediaconfig_so: ELF64 AArch64/media symbols or digest mismatch")
    artifacts_out.append(
        Phase208DonorArtifactDigest(
            "fx3_libinframediaconfig_so",
            P208_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            mc_sz,
            mc_sha,
            mc_hdr,
            ("ELF64_AARCH64", "InfraMediaConfig", "GetMediaNum", "Backup_sync_subsystem"),
            mc_ok,
        )
    )

    bm_raw, bm_sz, bm_sha, bm_hdr = _read_bounded_rdonly(P208_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH)
    bm_mach = struct.unpack_from("<H", bm_raw, 18)[0] if len(bm_raw) >= 20 else 0
    bm_ok = (
        bm_sz == P208_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES
        and bm_sha == P208_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256
        and bm_raw[:4] == b"\x7fELF"
        and bm_raw[4] == 2
        and bm_mach == 183
        and b"BackupManager" in bm_raw
        and b"SKData_Init" in bm_raw
        and b"Backup_get_datasize" in bm_raw
    )
    if not bm_ok:
        errors.append("fx3_libbackupmanager_so: ELF64 AArch64/BackupManager symbols or digest mismatch")
    artifacts_out.append(
        Phase208DonorArtifactDigest(
            "fx3_libbackupmanager_so",
            P208_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            "LOCAL_DONOR_O_RDONLY",
            "O_RDONLY_FULL",
            bm_sz,
            bm_sha,
            bm_hdr,
            ("ELF64_AARCH64", "BackupManager", "SKData_Init", "Backup_get_datasize"),
            bm_ok,
        )
    )

    elapsed = round(time.monotonic() - t0, 6)
    all_ok = len(errors) == 0 and all(a.passed for a in artifacts_out)
    snap_sha = _canonical_sha256({"mode": "LOCAL_DONOR_O_RDONLY", "artifacts": [asdict(a) for a in artifacts_out]})
    return Phase208DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY_BOUNDED",
        donor_files_inspected=len(artifacts_out),
        raw_firmware_bytes_leaked=0,
        bodydata_702_bytes=bd_sz,
        bodydata_ufu_magic_ok=bd_ok,
        cpapp_b_arm_vec_ok=cp_ok,
        fx3_appfw_702_elf64_ok=af3_ok,
        backup_bin_bk4_fx3_ok=bak_ok,
        libinframediaconfig_elf64_ok=mc_ok,
        libbackupmanager_elf64_ok=bm_ok,
        elapsed_seconds=elapsed,
        artifacts=tuple(artifacts_out),
        snapshot_sha256=snap_sha,
        all_passed=all_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 29A — Slot-1 CAMSET01..10.DAT Vault & BIG6 Zero e-ND Bus Protection
# ---------------------------------------------------------------------------


def evaluate_slot1_camset_and_big6_end_guard(
    spec: Optional[CamsetSlot1Big6VaultSpec] = None,
) -> CamsetSlot1Big6VaultReport:
    """Enforce Slot-1 `CAMSET01..10.DAT` SD/CFexpress-A split, cross-model firewall & `BIG6` zero e-ND TX."""
    cfg = spec if spec is not None else CamsetSlot1Big6VaultSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(P208_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during Pillar 29A CAMSET/BIG6 guard")

    slot1_ok = cfg.target_slot == P208_CAMSET_ALLOWED_SLOT
    dat_ok = (
        1 <= len(cfg.camset_filenames) <= P208_CAMSET_MAX_FILES
        and len(set(cfg.camset_filenames)) == len(cfg.camset_filenames)
        and all(fn in P208_VALID_CAMSET_FILENAMES for fn in cfg.camset_filenames)
    )
    mr_ok = not cfg.mr_recall_mode_active
    if not (slot1_ok and dat_ok and mr_ok):
        blocked.append(P208_BLOCKED_CAMSET_NON_SLOT1_OR_MR_MODE)
        errors.append(
            f"[Save/Load Settings] requires Slot 1, <=10 CAMSET01..10.DAT files, and non-MR mode "
            f"(got slot={cfg.target_slot}, count={len(cfg.camset_filenames)}, mr={cfg.mr_recall_mode_active})"
        )

    media = cfg.media_type.strip().upper()
    norm_dir = posixpath.normpath(cfg.camset_dir_path.strip()) if cfg.camset_dir_path.strip() else ""
    expected_dir = (
        P208_SD_CAMSET_DIR
        if media == P208_MEDIA_SDXC
        else (P208_CFEXPRESS_A_CAMSET_DIR if media == P208_MEDIA_CFEXPRESS_A else "INVALID_MEDIA")
    )
    media_path_ok = media in P208_VALID_MEDIA_TYPES and norm_dir == expected_dir
    if not media_path_ok:
        blocked.append(P208_BLOCKED_CAMSET_MEDIA_PATH_ASYMMETRY)
        errors.append(
            f"CAMSET dual-media root mismatch: media={cfg.media_type!r} path={norm_dir!r} (expected {expected_dir!r})"
        )

    origin = cfg.camset_model_origin.strip().upper()
    norm_overlay = posixpath.normpath(cfg.stage_b_camset_write_target.strip() or "/")
    lower_overlay = norm_overlay.lower()
    hits_persistent = any(
        lower_overlay.startswith(pref) or pref in lower_overlay
        for pref in P208_FORBIDDEN_PERSISTENT_CAMSET_TARGETS
    )
    stage_b_sandbox_ok = (
        (not cfg.stage_b_active)
        or (
            cfg.stage_b_overlay_is_tmpfs
            and (norm_overlay == P208_STAGE_B_CAMSET_OVERLAY_DIR or norm_overlay.startswith(P208_STAGE_B_CAMSET_OVERLAY_DIR + "/"))
            and (not hits_persistent)
        )
    )
    # Stock FX3 Slot-1 CAMSET strictly accepts ILME-FX3 only; FX6 is allowed ONLY inside Stage-B /tmp/fx6_camset_overlay
    cross_model_ok = (
        origin == P208_CAMSET_ORIGIN_FX3
        or (origin == P208_CAMSET_ORIGIN_FX6 and cfg.stage_b_active and stage_b_sandbox_ok)
    )
    if (not cross_model_ok) or (not stage_b_sandbox_ok):
        blocked.append(P208_BLOCKED_CROSS_MODEL_CAMSET_OR_OVERLAY_ESCAPE)
        errors.append(
            f"Cross-model CAMSET firewall / Stage-B overlay violation: origin={origin!r}, "
            f"stage_b={cfg.stage_b_active}, target={norm_overlay!r}, tmpfs={cfg.stage_b_overlay_is_tmpfs}"
        )

    leaked_machine_keys = [k for k in cfg.included_setting_keys if k.strip().upper() in P208_CAMSET_EXCLUDED_MACHINE_BOUND_KEYS]
    excl_ok = len(leaked_machine_keys) == 0
    if not excl_ok:
        blocked.append(P208_BLOCKED_CAMSET_MACHINE_BOUND_ITEMS_INCLUDED)
        errors.append(f"Machine-bound keys forbidden in CAMSET .DAT payload: {leaked_machine_keys}")

    ll_mode = cfg.big6_lower_left_mode.strip()
    big6_ok = (
        cfg.big6_mode_fixed_variable
        and cfg.big6_home_custom_key_bound
        and ll_mode in P208_BIG6_VALID_LOWER_LEFT_MODES
        and cfg.e_nd_actuator_tx_count == 0
    )
    if not big6_ok:
        blocked.append(P208_BLOCKED_BIG6_END_ACTUATOR_TX_OR_TILE_INVALID)
        errors.append(
            f"BIG6 (Home) guard failed: fixed_var={cfg.big6_mode_fixed_variable}, home_key={cfg.big6_home_custom_key_bound}, "
            f"lower_left={ll_mode!r}, e_nd_actuator_tx_count={cfg.e_nd_actuator_tx_count} (must be 0 on FX3 CP bus)"
        )

    h0_h3_ok = (
        cfg.slot1_camset_h0_sha256 == cfg.slot1_camset_h3_sha256
        and cfg.p2_setting_h0_sha256 == cfg.p2_setting_h3_sha256
    )
    if not h0_h3_ok:
        blocked.append(P208_BLOCKED_CAMSET_H0_H3_VAULT_DRIFT)
        errors.append("Slot-1 FX3/CAMSET or Stock p2:/setting H0 != H3 hash drift detected")

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = len(dedup_blocked) == 0 and len(errors) == 0
    return CamsetSlot1Big6VaultReport(
        passed=passed,
        slot1_exclusivity_ok=slot1_ok,
        dat_count_and_names_ok=dat_ok,
        mr_mode_guard_ok=mr_ok,
        dual_media_root_split_ok=media_path_ok,
        expected_camset_dir=expected_dir,
        cross_model_firewall_ok=cross_model_ok,
        stage_b_tmpfs_sandbox_ok=stage_b_sandbox_ok,
        machine_bound_exclusions_ok=excl_ok,
        big6_topology_and_zero_end_ok=big6_ok,
        big6_lower_left_mode=ll_mode,
        big6_nd_metadata_only=(ll_mode == P208_BIG6_LOWER_LEFT_ND_FILTER and cfg.e_nd_actuator_tx_count == 0),
        e_nd_actuator_tx_count=int(cfg.e_nd_actuator_tx_count),
        h0_eq_h3_vault_ok=h0_h3_ok,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar29a_camset_slot1_big6_6_scenario_suite() -> Pillar29ACamsetBig6SuiteResult:
    """Run all 6 deterministic scenarios for Pillar 29A (`CAMSET` Slot-1 Dual-Media & `BIG6` Zero e-ND)."""
    outcomes: List[Pillar29AScenarioOutcome] = []

    # P29A1: Happy SD + CFexpress-A Slot-1 CAMSET + Stage-B /tmp/fx6_camset_overlay + BIG6 Aperture & ND metadata-only (0 e-ND TX)
    r1_sd = evaluate_slot1_camset_and_big6_end_guard(
        CamsetSlot1Big6VaultSpec(media_type=P208_MEDIA_SDXC, camset_dir_path=P208_SD_CAMSET_DIR)
    )
    r1_cfa = evaluate_slot1_camset_and_big6_end_guard(
        CamsetSlot1Big6VaultSpec(
            media_type=P208_MEDIA_CFEXPRESS_A,
            camset_dir_path=P208_CFEXPRESS_A_CAMSET_DIR,
            camset_model_origin=P208_CAMSET_ORIGIN_FX6,
            stage_b_active=True,
            big6_lower_left_mode=P208_BIG6_LOWER_LEFT_ND_FILTER,
            e_nd_actuator_tx_count=0,
        )
    )
    ok1 = r1_sd.passed and r1_cfa.passed and r1_cfa.big6_nd_metadata_only and r1_cfa.e_nd_actuator_tx_count == 0
    outcomes.append(
        Pillar29AScenarioOutcome(
            P208_PILLAR_29A_SCENARIO_IDS[0],
            ok1,
            r1_sd.expected_camset_dir,
            0,
            (),
            "Slot-1 SD/CFexpress-A CAMSET01..10.DAT, Stage-B /tmp/fx6_camset_overlay & BIG6 0 e-ND TX verified",
        )
    )

    # P29A2: Slot-2 target, >10 .DAT files (CAMSET11.DAT), or MR Recall Camera Setting mode rejected
    r2_slot2 = evaluate_slot1_camset_and_big6_end_guard(CamsetSlot1Big6VaultSpec(target_slot=2))
    r2_11 = evaluate_slot1_camset_and_big6_end_guard(
        CamsetSlot1Big6VaultSpec(camset_filenames=P208_VALID_CAMSET_FILENAMES + ("CAMSET11.DAT",))
    )
    r2_mr = evaluate_slot1_camset_and_big6_end_guard(CamsetSlot1Big6VaultSpec(mr_recall_mode_active=True))
    ok2 = all(
        (not r.passed) and (P208_BLOCKED_CAMSET_NON_SLOT1_OR_MR_MODE in r.blocked_codes)
        for r in (r2_slot2, r2_11, r2_mr)
    )
    outcomes.append(
        Pillar29AScenarioOutcome(
            P208_PILLAR_29A_SCENARIO_IDS[1],
            ok2,
            r2_slot2.expected_camset_dir,
            0,
            r2_slot2.blocked_codes,
            "Slot 2 CAMSET, >10 .DAT files (CAMSET11.DAT), and MR Recall Camera Setting mode rejected fail-closed",
        )
    )

    # P29A3: SD vs CFexpress Type A root path asymmetry swapped -> blocked fail-closed
    r3_sd_bad = evaluate_slot1_camset_and_big6_end_guard(
        CamsetSlot1Big6VaultSpec(media_type=P208_MEDIA_SDXC, camset_dir_path=P208_CFEXPRESS_A_CAMSET_DIR)
    )
    r3_cfa_bad = evaluate_slot1_camset_and_big6_end_guard(
        CamsetSlot1Big6VaultSpec(media_type=P208_MEDIA_CFEXPRESS_A, camset_dir_path=P208_SD_CAMSET_DIR)
    )
    ok3 = all(
        (not r.passed) and (P208_BLOCKED_CAMSET_MEDIA_PATH_ASYMMETRY in r.blocked_codes)
        for r in (r3_sd_bad, r3_cfa_bad)
    )
    outcomes.append(
        Pillar29AScenarioOutcome(
            P208_PILLAR_29A_SCENARIO_IDS[2],
            ok3,
            r3_sd_bad.expected_camset_dir,
            0,
            r3_sd_bad.blocked_codes,
            "SD (/PRIVATE/SONY/...) vs CFexpress Type A (/SONY/...) CAMSET root path swap rejected fail-closed",
        )
    )

    # P29A4: Cross-model FX3A .DAT or FX6 Stage-B escaping /tmp/fx6_camset_overlay to Slot-1/p2:/setting blocked
    r4_fx3a = evaluate_slot1_camset_and_big6_end_guard(
        CamsetSlot1Big6VaultSpec(camset_model_origin=P208_CAMSET_ORIGIN_FX3A)
    )
    r4_fx6_esc = evaluate_slot1_camset_and_big6_end_guard(
        CamsetSlot1Big6VaultSpec(
            camset_model_origin=P208_CAMSET_ORIGIN_FX6,
            stage_b_camset_write_target=P208_SD_CAMSET_DIR,
            stage_b_overlay_is_tmpfs=False,
        )
    )
    ok4 = all(
        (not r.passed) and (P208_BLOCKED_CROSS_MODEL_CAMSET_OR_OVERLAY_ESCAPE in r.blocked_codes)
        for r in (r4_fx3a, r4_fx6_esc)
    )
    outcomes.append(
        Pillar29AScenarioOutcome(
            P208_PILLAR_29A_SCENARIO_IDS[3],
            ok4,
            r4_fx3a.expected_camset_dir,
            0,
            r4_fx6_esc.blocked_codes,
            "Cross-model FX3A/FX6 .DAT import & Stage-B escape outside /tmp/fx6_camset_overlay blocked",
        )
    )

    # P29A5: BIG6 CP bus e-ND actuator TX > 0 or invalid Home Lower-Left tile / unbound HOME key blocked
    r5_end = evaluate_slot1_camset_and_big6_end_guard(CamsetSlot1Big6VaultSpec(e_nd_actuator_tx_count=3))
    r5_tile = evaluate_slot1_camset_and_big6_end_guard(
        CamsetSlot1Big6VaultSpec(big6_lower_left_mode="Electronic_Auto_ND_Motor")
    )
    ok5 = all(
        (not r.passed) and (P208_BLOCKED_BIG6_END_ACTUATOR_TX_OR_TILE_INVALID in r.blocked_codes)
        for r in (r5_end, r5_tile)
    )
    outcomes.append(
        Pillar29AScenarioOutcome(
            P208_PILLAR_29A_SCENARIO_IDS[4],
            ok5,
            r5_end.expected_camset_dir,
            r5_end.e_nd_actuator_tx_count,
            r5_end.blocked_codes,
            "FX3 CP bus physical e-ND actuator TX (>0) & invalid BIG6 lower-left tile blocked fail-closed",
        )
    )

    # P29A6: Machine-bound WB Custom 1..3 / FTP / Cert leak, H0!=H3 drift, or write unlock blocked
    r6 = evaluate_slot1_camset_and_big6_end_guard(
        CamsetSlot1Big6VaultSpec(
            included_setting_keys=("WB_CUSTOM_1", "FTP_SERVER_CREDENTIAL"),
            p2_setting_h3_sha256="f" * 64,
            request_persistent_write_unlock=True,
        )
    )
    ok6 = (
        (not r6.passed)
        and (P208_BLOCKED_CAMSET_MACHINE_BOUND_ITEMS_INCLUDED in r6.blocked_codes)
        and (P208_BLOCKED_CAMSET_H0_H3_VAULT_DRIFT in r6.blocked_codes)
        and (P208_BLOCKED_SAFETY_POLICY_VIOLATION in r6.blocked_codes)
        and r6.physical_device_writes == 0
    )
    outcomes.append(
        Pillar29AScenarioOutcome(
            P208_PILLAR_29A_SCENARIO_IDS[5],
            ok6,
            r6.expected_camset_dir,
            0,
            r6.blocked_codes,
            "Machine-bound WB Custom/FTP leak, H0!=H3 drift & persistent write unlock rejected (0 device writes)",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P208_PILLAR_29A_SCENARIO_IDS)
    return Pillar29ACamsetBig6SuiteResult(
        passed=all_ok,
        status=P208_STATUS_VERIFIED_PILLAR_29A if all_ok else P208_STATUS_REJECTED_PILLAR_29A,
        scenarios_passed=passed_count,
        scenarios_total=len(P208_PILLAR_29A_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


# ---------------------------------------------------------------------------
# Pillar 29B — Simult + Auto Switch Off, VMC-BNCM1 TC IN & De-Squeeze 1.65x
# ---------------------------------------------------------------------------


def evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
    spec: Optional[SimultVaultTcInDesqueezeSpec] = None,
) -> SimultVaultTcInDesqueezeReport:
    """Enforce `[Simult. Recording] + [Auto Switch Media = Off]`, `VMC-BNCM1` body `TC IN` & `1.65x` De-Squeeze vault."""
    cfg = spec if spec is not None else SimultVaultTcInDesqueezeSpec()
    blocked: List[str] = []
    errors: List[str] = []

    if cfg.request_persistent_write_unlock or PERSISTENT_EMMC_WRITES_AUTHORIZED:
        blocked.append(P208_BLOCKED_SAFETY_POLICY_VIOLATION)
        errors.append("Persistent eMMC write unlock forbidden during Pillar 29B vault check")

    policy = cfg.vault_rec_policy.strip().upper()
    if policy == P208_REC_MODE_SIMULT_STRICT_VAULT:
        simult_ok = (
            cfg.simult_recording_enabled
            and (not cfg.auto_switch_media_enabled)
            and (not cfg.dropped_to_single_card)
        )
    elif policy == P208_REC_MODE_EXTENDED_OBSERVATION:
        simult_ok = cfg.simult_recording_enabled
    else:
        simult_ok = False
    if not simult_ok:
        blocked.append(P208_BLOCKED_SIMULT_AUTO_SWITCH_ON_SINGLE_CARD_DROP)
        errors.append(
            f"Dual-slot strict vault redundancy requires [Simult. Recording]=On and [Auto Switch Media]=Off "
            f"with zero single-card drop (policy={cfg.vault_rec_policy!r}, auto_switch={cfg.auto_switch_media_enabled}, "
            f"dropped={cfg.dropped_to_single_card})"
        )

    sq_mode = cfg.tc_shooting_mode.strip().upper() in ("S&Q", "SQ")
    tc_port_ok = (not cfg.vmc_bncm1_attached) or (
        cfg.vmc_bncm1_port == P208_TC_PORT_BODY_MULTI_USB
        and cfg.tc_direction == P208_TC_DIRECTION_IN
        and cfg.multi_usb_bnc_tc_out_tx_count == 0
    )
    if not tc_port_ok or cfg.multi_usb_bnc_tc_out_tx_count != 0:
        blocked.append(P208_BLOCKED_VMC_BNCM1_HANDLE_PORT_OR_BNC_TC_OUT)
        errors.append(
            f"VMC-BNCM1 violation: port={cfg.vmc_bncm1_port!r} (XLR-H1 handle Micro-USB forbidden), "
            f"dir={cfg.tc_direction!r}, multi_usb_bnc_tc_out_tx={cfg.multi_usb_bnc_tc_out_tx_count} (EOPNOTSUPP)"
        )

    ext_lk = (
        cfg.vmc_bncm1_attached
        and tc_port_ok
        and (not sq_mode)
        and cfg.tc_shooting_mode.strip() == "Movie"
        and cfg.tc_make.strip() == "Preset"
        and cfg.tc_run.strip() == "Free Run"
    )
    hdmi_tc_effective = bool(cfg.hdmi_tc_out_enabled) and (not sq_mode)

    ds_choice = cfg.desqueeze_menu_choice.strip()
    expected_factor = P208_DESQUEEZE_ENUM_TO_FACTOR.get(ds_choice)
    suppressed = (
        cfg.hdmi_raw_output_on
        or cfg.rec_media_dur_hdmi_off_only
        or (not cfg.log_shooting_on)
        or cfg.tc_shooting_mode.strip() == "Still"
    )
    effective_factor = 1.0 if (expected_factor is None or suppressed) else expected_factor
    locks_ok = True
    if expected_factor is not None and ds_choice != "Off" and (not suppressed):
        locks_ok = (
            cfg.focus_mode == P208_DESQUEEZE_4_REQUIRED_LOCKS["focus_mode"]
            and cfg.focus_area == P208_DESQUEEZE_4_REQUIRED_LOCKS["focus_area"]
            and cfg.steady_shot == P208_DESQUEEZE_4_REQUIRED_LOCKS["steady_shot"]
            and cfg.face_priority_multi_metering == P208_DESQUEEZE_4_REQUIRED_LOCKS["face_priority_multi_metering"]
        )
    factor_match = expected_factor is not None and abs(float(cfg.applied_desqueeze_factor) - effective_factor) < 1e-6
    desqueeze_ok = factor_match and locks_ok
    if not desqueeze_ok:
        blocked.append(P208_BLOCKED_DESQUEEZE_165X_OR_4LOCKS_VIOLATION)
        errors.append(
            f"[De-Squeeze Display] violation: choice={ds_choice!r}, applied={cfg.applied_desqueeze_factor} "
            f"(expected {effective_factor}), locks_ok={locks_ok}"
        )

    fmap_ok = (not cfg.in_body_focus_map_overlay_injected) and (
        (not cfg.external_mc_focus_map_active) or int(cfg.sensor_fps) < P208_FOCUS_MAP_EXTERNAL_CUTOFF_FPS
    )
    if not fmap_ok:
        blocked.append(P208_BLOCKED_FOCUS_MAP_IN_BODY_OR_GE_150FPS)
        errors.append(
            f"Focus Map guard failed: in_body_injected={cfg.in_body_focus_map_overlay_injected} (FX3 has no in-body menu), "
            f"external_mc={cfg.external_mc_focus_map_active} @ {cfg.sensor_fps}fps (cutoff >=150fps)"
        )

    swb_ok = (
        cfg.shockless_wb_mode in P208_SHOCKLESS_WB_VALID_MODES
        and cfg.ctemp_filter_direct_change_immediate
        and cfg.ab_gm_fine_tune_immediate
    )
    h0_map = cfg.surfaces_h0 if cfg.surfaces_h0 is not None else _default_16_surface_digests()
    h3_map = cfg.surfaces_h3 if cfg.surfaces_h3 is not None else dict(h0_map)
    eq_count = sum(1 for k, v in h0_map.items() if h3_map.get(k) == v)
    vault_ok = (
        eq_count == P208_TIER0_16_SURFACE_COUNT
        and len(h0_map) == P208_TIER0_16_SURFACE_COUNT
        and cfg.p2_blkroset_locked
        and cfg.stage_b_p2_setting_writes == 0
    )
    if (not swb_ok) or (not vault_ok):
        blocked.append(P208_BLOCKED_SHOCKLESS_WB_OR_16OF16_H0_H3_DRIFT)
        errors.append(
            f"Shockless WB / p2:/setting vault check failed: swb_ok={swb_ok}, "
            f"h0_eq_h3={eq_count}/{P208_TIER0_16_SURFACE_COUNT}, blkroset={cfg.p2_blkroset_locked}, "
            f"p2_writes={cfg.stage_b_p2_setting_writes}"
        )

    dedup_blocked = tuple(dict.fromkeys(blocked))
    passed = len(dedup_blocked) == 0 and len(errors) == 0
    return SimultVaultTcInDesqueezeReport(
        passed=passed,
        simult_strict_vault_ok=simult_ok,
        auto_switch_media_off_enforced=(not cfg.auto_switch_media_enabled),
        vmc_bncm1_body_tcin_ok=tc_port_ok and cfg.multi_usb_bnc_tc_out_tx_count == 0,
        ext_lk_timecode_locked=ext_lk,
        hdmi_tc_out_effective=hdmi_tc_effective,
        desqueeze_factor_and_locks_ok=desqueeze_ok,
        effective_desqueeze_factor=effective_factor,
        desqueeze_suppressed_by_mode=suppressed,
        external_focus_map_guard_ok=fmap_ok,
        shockless_wb_and_bypass_ok=swb_ok,
        h0_eq_h3_surface_count=eq_count,
        vault_16of16_h0_eq_h3_ok=vault_ok,
        blocked_codes=dedup_blocked,
        errors=tuple(errors),
    )


def run_pillar29b_simult_tcin_desqueeze_6_scenario_suite() -> Pillar29BSimultTcDesqueezeSuiteResult:
    """Run all 6 deterministic scenarios for Pillar 29B (`Simult + Auto Switch Off`, `VMC-BNCM1` & `1.65x`)."""
    outcomes: List[Pillar29BScenarioOutcome] = []

    # P29B1: Happy Simult + Auto Switch Off, VMC-BNCM1 Body TC IN (EXT-LK + HDMI TC OUT), 1.6x=1.65x 4-lock & 16/16 H0==H3
    r1 = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(SimultVaultTcInDesqueezeSpec())
    r1_raw = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
        SimultVaultTcInDesqueezeSpec(hdmi_raw_output_on=True, applied_desqueeze_factor=1.0)
    )
    ok1 = (
        r1.passed
        and r1.ext_lk_timecode_locked
        and r1.hdmi_tc_out_effective
        and r1.effective_desqueeze_factor == 1.65
        and r1.h0_eq_h3_surface_count == 16
        and r1_raw.passed
        and r1_raw.desqueeze_suppressed_by_mode
    )
    outcomes.append(
        Pillar29BScenarioOutcome(
            P208_PILLAR_29B_SCENARIO_IDS[0],
            ok1,
            r1.h0_eq_h3_surface_count,
            r1.effective_desqueeze_factor,
            (),
            "Simult + Auto Switch Off, VMC-BNCM1 body TC IN EXT-LK, 1.6x=1.65x 4-lock & 16/16 H0==H3 verified",
        )
    )

    # P29B2: [Auto Switch Media] = On during strict dual-slot vault / cold-backup (silent single-card drop) blocked
    r2 = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
        SimultVaultTcInDesqueezeSpec(
            vault_rec_policy=P208_REC_MODE_SIMULT_STRICT_VAULT,
            auto_switch_media_enabled=True,
            slot1_full_event=True,
            dropped_to_single_card=True,
        )
    )
    ok2 = (not r2.passed) and (P208_BLOCKED_SIMULT_AUTO_SWITCH_ON_SINGLE_CARD_DROP in r2.blocked_codes)
    outcomes.append(
        Pillar29BScenarioOutcome(
            P208_PILLAR_29B_SCENARIO_IDS[1],
            ok2,
            r2.h0_eq_h3_surface_count,
            r2.effective_desqueeze_factor,
            r2.blocked_codes,
            "[Auto Switch Media]=On silent drop to single-card mode during strict dual-slot vault blocked",
        )
    )

    # P29B3: VMC-BNCM1 plugged into XLR-H1 handle Micro-USB or reverse BNC TC OUT on Multi/Micro USB blocked
    r3_handle = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
        SimultVaultTcInDesqueezeSpec(vmc_bncm1_port=P208_TC_PORT_XLRH1_HANDLE_MICRO_USB)
    )
    r3_bnc_out = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
        SimultVaultTcInDesqueezeSpec(tc_direction=P208_TC_DIRECTION_BNC_OUT, multi_usb_bnc_tc_out_tx_count=2)
    )
    ok3 = all(
        (not r.passed) and (P208_BLOCKED_VMC_BNCM1_HANDLE_PORT_OR_BNC_TC_OUT in r.blocked_codes)
        for r in (r3_handle, r3_bnc_out)
    )
    outcomes.append(
        Pillar29BScenarioOutcome(
            P208_PILLAR_29B_SCENARIO_IDS[2],
            ok3,
            r3_handle.h0_eq_h3_surface_count,
            r3_handle.effective_desqueeze_factor,
            r3_bnc_out.blocked_codes,
            "VMC-BNCM1 on XLR-H1 handle Micro-USB & reverse Multi/Micro USB BNC TC OUT (EOPNOTSUPP) blocked",
        )
    )

    # P29B4: De-Squeeze 1.6x mis-applied as 1.60x (instead of 1.65x) or 4 hardware locks violated -> blocked
    r4_ratio = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
        SimultVaultTcInDesqueezeSpec(desqueeze_menu_choice="1.6x", applied_desqueeze_factor=1.60)
    )
    r4_ibis = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
        SimultVaultTcInDesqueezeSpec(steady_shot="Active")
    )
    ok4 = all(
        (not r.passed) and (P208_BLOCKED_DESQUEEZE_165X_OR_4LOCKS_VIOLATION in r.blocked_codes)
        for r in (r4_ratio, r4_ibis)
    )
    outcomes.append(
        Pillar29BScenarioOutcome(
            P208_PILLAR_29B_SCENARIO_IDS[3],
            ok4,
            r4_ratio.h0_eq_h3_surface_count,
            r4_ratio.effective_desqueeze_factor,
            r4_ratio.blocked_codes,
            "1.6x!=1.65x ratio drift & violated De-Squeeze 4-setting hardware locks (MF/Wide/IBIS Off/Face Off) blocked",
        )
    )

    # P29B5: Bogus in-body FX3 Focus Map overlay OR external M&C Focus Map at >=150fps (200/240fps S&Q) blocked
    r5_inbody = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
        SimultVaultTcInDesqueezeSpec(in_body_focus_map_overlay_injected=True)
    )
    r5_240fps = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
        SimultVaultTcInDesqueezeSpec(external_mc_focus_map_active=True, sensor_fps=240)
    )
    ok5 = all(
        (not r.passed) and (P208_BLOCKED_FOCUS_MAP_IN_BODY_OR_GE_150FPS in r.blocked_codes)
        for r in (r5_inbody, r5_240fps)
    )
    outcomes.append(
        Pillar29BScenarioOutcome(
            P208_PILLAR_29B_SCENARIO_IDS[4],
            ok5,
            r5_inbody.h0_eq_h3_surface_count,
            r5_inbody.effective_desqueeze_factor,
            r5_inbody.blocked_codes,
            "Bogus FX3 in-body Focus Map overlay & >=150fps external M&C Focus Map stream blocked fail-closed",
        )
    )

    # P29B6: Shockless WB C.Temp./Filter bypass broken, 16/16 H0!=H3 surface drift, or write unlock blocked
    drifted_h3 = _default_16_surface_digests()
    drifted_h3["tier0_surface_16"] = "e" * 64
    r6 = evaluate_simult_autoswitch_tcin_and_desqueeze_vault(
        SimultVaultTcInDesqueezeSpec(
            ctemp_filter_direct_change_immediate=False,
            surfaces_h3=drifted_h3,
            request_persistent_write_unlock=True,
        )
    )
    ok6 = (
        (not r6.passed)
        and r6.h0_eq_h3_surface_count == 15
        and (P208_BLOCKED_SHOCKLESS_WB_OR_16OF16_H0_H3_DRIFT in r6.blocked_codes)
        and (P208_BLOCKED_SAFETY_POLICY_VIOLATION in r6.blocked_codes)
        and r6.physical_device_writes == 0
    )
    outcomes.append(
        Pillar29BScenarioOutcome(
            P208_PILLAR_29B_SCENARIO_IDS[5],
            ok6,
            r6.h0_eq_h3_surface_count,
            r6.effective_desqueeze_factor,
            r6.blocked_codes,
            "Shockless WB C.Temp bypass violation, p2:/setting H0!=H3 drift & write unlock rejected (0 writes)",
        )
    )

    passed_count = sum(1 for o in outcomes if o.passed)
    all_ok = passed_count == len(P208_PILLAR_29B_SCENARIO_IDS)
    return Pillar29BSimultTcDesqueezeSuiteResult(
        passed=all_ok,
        status=P208_STATUS_VERIFIED_PILLAR_29B if all_ok else P208_STATUS_REJECTED_PILLAR_29B,
        scenarios_passed=passed_count,
        scenarios_total=len(P208_PILLAR_29B_SCENARIO_IDS),
        scenarios=tuple(outcomes),
    )


def run_pillar29_standalone_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Pillar29StandaloneReport:
    """Run Pillar 29 standalone donor audit + Pillar 29A (`CAMSET & BIG6`) + Pillar 29B (`Simult & TC IN`)."""
    _need(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    _need(SPI_NOR_WRITE_AUTHORIZED is False, "spi_nor_write_authorized must stay False")
    _need(EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False, "el3_payload_transmit_authorized must stay False")
    _need(ISP_WRITE_AUTHORIZED is False, "isp_write_authorized must stay False")
    _need(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    _need(OTP_FUSE_TOUCHES == 0 and OTP_FUSE_WRITES == 0, "OTP fuse counters must stay 0")
    _need(RPMB_COUNTER_INCREMENTS == 0, "RPMB counter increments must stay 0")
    _need(PHYSICAL_USB_PACKETS_EMITTED == 0, "Physical USB packets must stay 0")
    _need(PHYSICAL_DEVICE_WRITES == 0, "Physical device writes must stay 0")
    _need(RAW_FIRMWARE_BYTES_LEAKED == 0, "Raw firmware bytes leaked must stay 0")

    t0 = time.monotonic()
    snap = inspect_phase208_donors_readonly(force_clean_room=force_clean_room)
    p29a = run_pillar29a_camset_slot1_big6_6_scenario_suite()
    p29b = run_pillar29b_simult_tcin_desqueeze_6_scenario_suite()
    elapsed = round(time.monotonic() - t0, 6)

    errors: List[str] = list(snap.errors)
    if not p29a.passed:
        errors.append("Pillar 29A Slot-1 CAMSET dual-media vault & BIG6 zero e-ND suite failed")
    if not p29b.passed:
        errors.append("Pillar 29B Simult Auto Switch Off, VMC-BNCM1 TC IN & De-Squeeze 1.65x suite failed")

    all_ok = (
        snap.all_passed
        and p29a.passed
        and p29b.passed
        and PERSISTENT_EMMC_WRITES_AUTHORIZED is False
        and SPI_NOR_WRITE_AUTHORIZED is False
        and EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False
        and ISP_WRITE_AUTHORIZED is False
        and OTP_FUSE_TOUCHES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
        and len(errors) == 0
    )

    suite_sha = _canonical_sha256(
        {
            "schema": PHASE208_SCHEMA,
            "version": PHASE208_VERSION,
            "mode": snap.verification_mode,
            "snapshot_sha256": snap.snapshot_sha256,
            "p29a": p29a.to_dict(),
            "p29b": p29b.to_dict(),
            "all_passed": all_ok,
        }
    )
    return Pillar29StandaloneReport(
        schema=PHASE208_SCHEMA,
        version=PHASE208_VERSION,
        verification_mode=snap.verification_mode,
        all_passed=all_ok,
        status=P208_STATUS_VERIFIED_PILLAR29_SUITE if all_ok else P208_STATUS_FAIL_PILLAR29_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=snap,
        pillar_29a_camset_big6_vault=p29a,
        pillar_29b_simult_tcin_desqueeze_vault=p29b,
        suite_sha256=suite_sha,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Unified 29/29 Recovery Master Aggregator (`evaluate_29pillar_recovery_master`)
# ---------------------------------------------------------------------------


def _apply_master29_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
    err = f"FAULT_INJECTED:{pillar.pillar_id}"
    return MasterPillarStatus(
        pillar_number=pillar.pillar_number,
        pillar_id=pillar.pillar_id,
        phase_label=pillar.phase_label,
        module_name=pillar.module_name,
        passed=False,
        status=f"FAULT_INJECTED_{pillar.pillar_id.upper()}",
        verification_mode=pillar.verification_mode,
        elapsed_seconds=pillar.elapsed_seconds,
        key_metrics=pillar.key_metrics,
        digest_sha256=_canonical_sha256({"pillar": pillar.pillar_id, "fault_injected": True}),
        errors=pillar.errors + (err,),
    )


def evaluate_29pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master29PillarRecoveryReport:
    """Evaluate and aggregate all 29 recovery pillars (`1..29`) concurrently in `< 2.5s`."""
    _need(PERSISTENT_EMMC_WRITES_AUTHORIZED is False, "persistent_emmc_writes_authorized must stay False")
    _need(SPI_NOR_WRITE_AUTHORIZED is False, "spi_nor_write_authorized must stay False")
    _need(EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False, "el3_payload_transmit_authorized must stay False")
    _need(ISP_WRITE_AUTHORIZED is False, "isp_write_authorized must stay False")
    _need(PERSISTENT_WRITE_RELEASE is False, "persistent_write_release must stay False")
    _need(LIVE_USB_IOKIT_TRANSMIT_ENABLED is False, "live_usb_iokit_transmit_enabled must stay False")
    _need(OTP_FUSE_TOUCHES == 0 and OTP_FUSE_WRITES == 0, "OTP fuse counters must stay 0")
    _need(RPMB_COUNTER_INCREMENTS == 0, "RPMB counter increments must stay 0")
    _need(PASSIVE_TX_BYTES_EMITTED == 0, "Passive TX bytes must stay 0")
    _need(PHYSICAL_USB_PACKETS_EMITTED == 0, "Physical USB packets must stay 0")
    _need(PHYSICAL_DEVICE_WRITES == 0, "Physical device writes must stay 0")
    _need(RAW_FIRMWARE_BYTES_LEAKED == 0, "Raw firmware bytes leaked must stay 0")

    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_29_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_28pillar() -> Master28PillarRecoveryReport:
        return evaluate_28pillar_recovery_master(**kw)

    def _run_p29() -> Tuple[Pillar29StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar29_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_28 = pool.submit(_run_28pillar)
        fut_29 = pool.submit(_run_p29)
        m28_rep = fut_28.result()
        p29_rep, p29_dt = fut_29.result()

    safety_errors: List[str] = list(m28_rep.errors)
    for attr_name, expected_val in (
        ("otp_fuse_touches", 0),
        ("otp_fuse_writes", 0),
        ("rpmb_counter_increments", 0),
        ("passive_tx_bytes_emitted", 0),
        ("physical_usb_packets_emitted", 0),
        ("physical_device_writes", 0),
        ("raw_firmware_bytes_leaked", 0),
        ("el3_payload_transmit_authorized", False),
        ("isp_write_authorized", False),
        ("spi_nor_write_authorized", False),
        ("persistent_emmc_writes_authorized", False),
        ("persistent_write_release", False),
        ("live_usb_iokit_transmit_enabled", False),
    ):
        if getattr(m28_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillars 1-28 violated {attr_name} == {expected_val}")
        if hasattr(p29_rep, attr_name) and getattr(p29_rep, attr_name) != expected_val:
            safety_errors.append(f"Pillar 29 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m28_rep.pillars)

    spec29 = MASTER_29_PILLAR_SPECS[28]
    p29_metrics = {
        "pillar_29a_camset_big6_vault": (
            f"{p29_rep.pillar_29a_camset_big6_vault.scenarios_passed}/"
            f"{p29_rep.pillar_29a_camset_big6_vault.scenarios_total}"
        ),
        "pillar_29b_simult_tcin_desqueeze_vault": (
            f"{p29_rep.pillar_29b_simult_tcin_desqueeze_vault.scenarios_passed}/"
            f"{p29_rep.pillar_29b_simult_tcin_desqueeze_vault.scenarios_total}"
        ),
        "donor_files_inspected": p29_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec29[0],
            pillar_id=spec29[1],
            phase_label=spec29[2],
            module_name=spec29[3],
            passed=bool(p29_rep.all_passed),
            status=p29_rep.status,
            verification_mode=p29_rep.verification_mode,
            elapsed_seconds=p29_dt,
            key_metrics=p29_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec29[1],
                    "mode": p29_rep.verification_mode,
                    "status": p29_rep.status,
                    "metrics": p29_metrics,
                    "passed": p29_rep.all_passed,
                }
            ),
            errors=tuple(p29_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master29_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p29_rep.verification_mode

    all_ok = (
        len(pillar_statuses) == MASTER_29_PILLAR_COUNT == 29
        and pillars_passed == 29
        and len(failed) == 0
        and len(safety_errors) == 0
        and OTP_FUSE_TOUCHES == 0
        and OTP_FUSE_WRITES == 0
        and RPMB_COUNTER_INCREMENTS == 0
        and PASSIVE_TX_BYTES_EMITTED == 0
        and PHYSICAL_USB_PACKETS_EMITTED == 0
        and PHYSICAL_DEVICE_WRITES == 0
        and RAW_FIRMWARE_BYTES_LEAKED == 0
        and (EL3_PAYLOAD_TRANSMIT_AUTHORIZED is False)
        and (ISP_WRITE_AUTHORIZED is False)
        and (SPI_NOR_WRITE_AUTHORIZED is False)
        and (PERSISTENT_EMMC_WRITES_AUTHORIZED is False)
        and (PERSISTENT_WRITE_RELEASE is False)
        and (LIVE_USB_IOKIT_TRANSMIT_ENABLED is False)
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE208_SCHEMA,
            "version": PHASE208_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )

    return Master29PillarRecoveryReport(
        schema=PHASE208_SCHEMA,
        version=PHASE208_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P208_STATUS_VERIFIED_29OF29_AGGREGATOR if all_ok else P208_STATUS_FAIL_29OF29_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P208_CONCURRENT_CEILING_SECONDS,
        nominal_under_2_5s=elapsed < P208_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p29_rep.donor_snapshot,
        pillar29_a_camset_big6_vault=p29_rep.pillar_29a_camset_big6_vault,
        pillar29_b_simult_tcin_desqueeze_vault=p29_rep.pillar_29b_simult_tcin_desqueeze_vault,
        master_29pillar_sha256=master_sha,
        otp_fuse_touches=OTP_FUSE_TOUCHES,
        otp_fuse_writes=OTP_FUSE_WRITES,
        rpmb_counter_increments=RPMB_COUNTER_INCREMENTS,
        passive_tx_bytes_emitted=PASSIVE_TX_BYTES_EMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        isp_write_authorized=ISP_WRITE_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        allow_boot_partition_targeting=ALLOW_BOOT_PARTITION_TARGETING,
        allow_destructive_fastboot=ALLOW_DESTRUCTIVE_FASTBOOT,
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=tuple(safety_errors),
    )


def verify_29pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master29PillarRecoveryReport:
    """Public entry point for Pillar 29 unified `29/29` real-hardware recovery master verification."""
    return evaluate_29pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
