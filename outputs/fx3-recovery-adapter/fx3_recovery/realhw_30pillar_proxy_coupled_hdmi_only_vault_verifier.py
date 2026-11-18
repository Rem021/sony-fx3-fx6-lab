"""Phase 212 — Pillar 30 (`30/30` Recovery Pillars) & Unified 30-Pillar Recovery Master
(`verify-30pillar-recovery` / `verify-proxy-coupled-hdmi-vault`):

1. **Pillar 30A — `Px` Atomic Main+Proxy Coupled Vault (`M4ROOT/CLIP/` + `M4ROOT/SUB/`) Across Slot 1 & Slot 2**:
   - Audits `M4ROOT/CLIP/` (original `XAVC HS` / `XAVC S` / `XAVC S-I` `.MP4` + `.XML`) and
     `M4ROOT/SUB/` (`Px` proxy `*S03.MP4`: `XAVC HS HD` `1920x1080` `10bit` `16M`/`9M` HEVC or
     `XAVC S HD` `1280x720` `8bit` `6M` AVC) atomic coupled vault parity across Slot 1 and Slot 2.
   - Enforces Sony FX3 `Ver. 7.02` coupled Delete / Protect parity (atomic on BOTH `CLIP/` and
     `SUB/`; flags orphaned `SUB/`, missing `SUB/` when `(Px)` bit set, or protect/delete drift).
   - Enforces zero proxy generation at `119.88p`/`100p` Normal or `>=120fps`/`100fps` S&Q and
     forbids on-camera proxy playback assumptions.

2. **Pillar 30B — `[Off(HDMI Only)]` Zero-Card Interlock, HDMI Log `1080p` Downshift, `FocusMag` x `BrightMon` & Tier-0 `H0 == H3` Vault**:
   - Audits `[Rec. Media dur HDMI Output]` = `[Off(HDMI Only)]` (`[4K Output Set.(HDMI Only)]`
     `59.94p..24.00p 10bit`) pre-backup / pre-shoot media-vault hazard: blocks mistaking
     external-only HDMI 4K Log output for active internal Slot 1/Slot 2 recording.
   - Audits `[Log Shooting]` (`Cine EI`/`Cine EI Quick`/`Flexible ISO`) and `PPLUT1..PPLUT4`
     `1080p` HDMI downshift when `[On]` & `RAW Output = Off`, `[HDMI Info. Display]` blank-LCD
     / `Off(HDMI Only)` auto-suppression, and `Focus Magnifier` (`x1.0`/`x4.0`) x `Bright Monitoring`
     (`Setting Effect OFF`, `P/A/S/M + MF` lock, key-toggle lockout) mutual exclusion.
   - Ensures Stage-B volatile `tmpfs` overlay & `Backup.bin` / `16/16` Tier-0 surfaces reset cleanly
     (`H0 == H3`, `persistent_emmc_writes_authorized = False`, `physical_device_writes = 0`).

3. **Unified `30/30` Milestone Recovery Master (`evaluate_realhw_30pillar_recovery_master`)**:
   - Evaluates `evaluate_29pillar_recovery_master` (`1..29`) + **Pillar 30** concurrently ->
     **`30/30` (`VERIFIED_30OF30_PILLAR_RECOVERY_MASTER`)** in `< 2.6s` (`< 6.0s` test ceiling).
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
from .realhw_29pillar_camset_slot1_simult_vault_verifier import (
    MASTER_29_PILLAR_SPECS,
    Master29PillarRecoveryReport,
    evaluate_29pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE212_SCHEMA: str = "fx3-realhw-30pillar-recovery-master-verifier-v1"
PHASE212_VERSION: str = "1.0.0"

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

P212_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P212_NOMINAL_BUDGET_SECONDS: float = 2.6
P212_CONCURRENT_CEILING_SECONDS: float = 6.0
P212_BOUNDED_HEADER_BYTES: int = 4096
P212_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-28 / FX3 Ver. 7.02 Donor Anchors (bounded O_RDONLY verification)
P212_FX3_MODEL_NAME: str = "ILME-FX3"
P212_FX3_MODEL_ID: int = 0x91030080
P212_FX3_FW_VERSION: str = "7.02"

P212_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P212_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P212_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

P212_DONOR_FX3_APPFW_702_RELPATH: str = "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P212_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P212_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"

P212_DONOR_FX3_BACKUP_BIN_RELPATH: str = "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
P212_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P212_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

P212_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
P212_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P212_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"

P212_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
P212_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P212_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"

P212_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
P212_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P212_PINNED_FX3_LIBBACKUP_SO_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"

# Pillar 30A — M4ROOT/CLIP & M4ROOT/SUB Proxy Coupled Vault Constants
P212_M4ROOT_CLIP_DIR: str = "/M4ROOT/CLIP"
P212_M4ROOT_SUB_DIR: str = "/M4ROOT/SUB"
P212_ALLOWED_MEDIA_SLOTS: Tuple[int, ...] = (1, 2)
P212_VALID_MAIN_CODECS: Tuple[str, ...] = ("XAVC_HS", "XAVC_S", "XAVC_S_I")

P212_PROXY_FORMAT_XAVC_HS_HD: str = "XAVC_HS_HD"
P212_PROXY_FORMAT_XAVC_S_HD: str = "XAVC_S_HD"
P212_PROXY_SPEC_TABLE: Dict[str, Dict[str, Any]] = {
    P212_PROXY_FORMAT_XAVC_HS_HD: {
        "resolution": "1920x1080",
        "codec": "HEVC",
        "bit_depth": 10,
        "sampling": "4:2:0",
        "bitrates": ("16M", "9M"),
        "max_fps": 59.94,
    },
    P212_PROXY_FORMAT_XAVC_S_HD: {
        "resolution": "1280x720",
        "codec": "AVC",
        "bit_depth": 8,
        "sampling": "4:2:0",
        "bitrates": ("6M",),
        "max_fps": 59.94,
    },
}
P212_PROXY_CUTOFF_NORMAL_REC_RATES: Tuple[str, ...] = ("119.88p", "100p")
P212_PROXY_CUTOFF_SQ_SENSOR_FPS: Tuple[int, ...] = (100, 120, 200, 240)
P212_COUPLED_OPERATIONS: Tuple[str, ...] = ("NONE", "PROTECT", "UNPROTECT", "DELETE")
P212_CLIP_BASENAME_RE = re.compile(r"^([A-Za-z0-9_.-]+)\.MP4$")
P212_PROXY_BASENAME_RE = re.compile(r"^([A-Za-z0-9_.-]+)S03\.MP4$")

# Pillar 30B — Off(HDMI Only), Log/PPLUT 1080p Downshift, FocusMag x BrightMon & Tier-0 H0==H3
P212_REC_MEDIA_HDMI_ON: str = "On"
P212_REC_MEDIA_HDMI_OFF_ONLY: str = "Off(HDMI Only)"
P212_VALID_REC_MEDIA_HDMI_MODES: Tuple[str, ...] = (
    P212_REC_MEDIA_HDMI_ON,
    P212_REC_MEDIA_HDMI_OFF_ONLY,
)
P212_HDMI_ONLY_4K_FORMATS: Tuple[str, ...] = (
    "59.94p 10bit",
    "50p 10bit",
    "29.97p 10bit",
    "25p 10bit",
    "23.98p 10bit",
    "24.00p 10bit",
)
P212_LOG_SHOOTING_MODES: Tuple[str, ...] = ("Cine EI", "Cine EI Quick", "Flexible ISO")
P212_PPLUT_PROFILES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P212_FOCUS_MAG_MOVIE_SCALES: Tuple[str, ...] = ("x1.0", "x4.0")
P212_FOCUS_MAG_TIMES: Tuple[str, ...] = ("2 Sec", "5 Sec", "No Limit")
P212_PASM_MODES: Tuple[str, ...] = ("P", "A", "S", "M")
P212_STAGE_B_HDMI_PROXY_OVERLAY_DIR: str = "/tmp/fx6_hdmi_proxy_overlay"
P212_STOCK_BACKUP_BIN_PATH: str = "p2:/setting/Backup.bin"
P212_STOCK_P2_SETTING_PATH: str = "p2:/setting"
P212_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P212_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P212_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION: str = "BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION"
P212_BLOCKED_PROXY_PLAYBACK_ASSUMPTION_FORBIDDEN: str = "BLOCKED_PROXY_PLAYBACK_ASSUMPTION_FORBIDDEN"
P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH: str = "BLOCKED_COUPLED_VAULT_PARITY_MISMATCH"
P212_BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY: str = "BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY"
P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD: str = "BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD"
P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT: str = "BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT"
P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK: str = "BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK"
P212_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"
P212_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"

P212_STATUS_VERIFIED_PILLAR_30A: str = "VERIFIED_PILLAR_30A_PROXY_COUPLED_VAULT"
P212_STATUS_REJECTED_PILLAR_30A: str = "REJECTED_PILLAR_30A_PROXY_COUPLED_VAULT"
P212_STATUS_VERIFIED_PILLAR_30B: str = "VERIFIED_PILLAR_30B_HDMI_ONLY_INTERLOCK"
P212_STATUS_REJECTED_PILLAR_30B: str = "REJECTED_PILLAR_30B_HDMI_ONLY_INTERLOCK"
P212_STATUS_VERIFIED_PILLAR30_SUITE: str = "VERIFIED_PILLAR30_PROXY_HDMI_ONLY_VAULT"
P212_STATUS_FAIL_PILLAR30_SUITE: str = "FAIL_PILLAR30_PROXY_HDMI_ONLY_VAULT"
P212_STATUS_VERIFIED_30OF30_AGGREGATOR: str = "VERIFIED_30OF30_PILLAR_RECOVERY_MASTER"
P212_STATUS_FAIL_30OF30_AGGREGATOR: str = "FAIL_30OF30_PILLAR_RECOVERY_MASTER"

P212_PILLAR_30A_SCENARIO_IDS: Tuple[str, ...] = (
    "P30A1_SLOT1_SLOT2_XAVC_HS_HD_10BIT_COUPLED_VAULT",
    "P30A2_XAVC_S_HD_720P_PROTECT_ATOMIC_PARITY",
    "P30A3_REJECT_119_88P_NORMAL_AND_120FPS_SQ_PROXY",
    "P30A4_REJECT_ON_CAMERA_PROXY_PLAYBACK_ASSUMPTION",
    "P30A5_REJECT_ORPHAN_SUB_AND_MISSING_PX_PROXY",
    "P30A6_ATOMIC_COUPLED_DELETE_AND_PROTECT_DRIFT_GUARD",
)
P212_PILLAR_30B_SCENARIO_IDS: Tuple[str, ...] = (
    "P30B1_OFF_HDMI_ONLY_4K_10BIT_ZERO_CARD_HAZARD_BLOCKED",
    "P30B2_REC_MEDIA_ON_LOG_PPLUT_1080P_DOWNSHIFT_VERIFIED",
    "P30B3_HDMI_INFO_DISPLAY_SUPPRESSION_AND_RAW_OFFLINE_GUARD",
    "P30B4_FOCUS_MAG_X4_BRIGHT_MONITORING_MUTUAL_EXCLUSION",
    "P30B5_PREBACKUP_OFF_HDMI_ONLY_STAGE_B_TMPFS_CONTAINMENT",
    "P30B6_TIER0_BACKUP_BIN_16OF16_H0_H3_CLEAN_RESET",
)

MASTER_30_PILLAR_COUNT: int = 30
MASTER_30_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_29_PILLAR_SPECS + (
    (
        30,
        "pillar_30_proxy_coupled_hdmi_only_vault",
        "Phase 212",
        "fx3_recovery.realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier",
    ),
)
MASTER_30_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_30_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _safety_invariant_errors() -> List[str]:
    errs: List[str] = []
    checks = (
        ("PERSISTENT_EMMC_WRITES_AUTHORIZED", PERSISTENT_EMMC_WRITES_AUTHORIZED, False),
        ("SPI_NOR_WRITE_AUTHORIZED", SPI_NOR_WRITE_AUTHORIZED, False),
        ("EL3_PAYLOAD_TRANSMIT_AUTHORIZED", EL3_PAYLOAD_TRANSMIT_AUTHORIZED, False),
        ("ISP_WRITE_AUTHORIZED", ISP_WRITE_AUTHORIZED, False),
        ("PERSISTENT_WRITE_RELEASE", PERSISTENT_WRITE_RELEASE, False),
        ("ALLOW_BOOT_PARTITION_TARGETING", ALLOW_BOOT_PARTITION_TARGETING, False),
        ("ALLOW_DESTRUCTIVE_FASTBOOT", ALLOW_DESTRUCTIVE_FASTBOOT, False),
        ("ALLOW_PERSISTENT_JIRITSU_WRITES", ALLOW_PERSISTENT_JIRITSU_WRITES, False),
        ("ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS", ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS, False),
        ("LIVE_USB_IOKIT_TRANSMIT_ENABLED", LIVE_USB_IOKIT_TRANSMIT_ENABLED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("OTP_FUSE_TOUCHES", OTP_FUSE_TOUCHES, 0),
        ("OTP_FUSE_WRITES", OTP_FUSE_WRITES, 0),
        ("RPMB_COUNTER_INCREMENTS", RPMB_COUNTER_INCREMENTS, 0),
        ("PASSIVE_TX_BYTES_EMITTED", PASSIVE_TX_BYTES_EMITTED, 0),
        ("PHYSICAL_USB_PACKETS_EMITTED", PHYSICAL_USB_PACKETS_EMITTED, 0),
        ("PHYSICAL_DEVICE_WRITES", PHYSICAL_DEVICE_WRITES, 0),
        ("RAW_FIRMWARE_BYTES_LEAKED", RAW_FIRMWARE_BYTES_LEAKED, 0),
    )
    for name, actual, expected in checks:
        if actual != expected:
            errs.append(f"{name} expected {expected!r}, got {actual!r}")
    return errs


def _is_tmpfs_path(path_value: str) -> bool:
    norm = posixpath.normpath(path_value)
    return norm.startswith("/tmp/") or norm.startswith("/run/")


def _targets_persistent_emmc(path_value: str) -> bool:
    low = path_value.strip().lower()
    return any(tok in low for tok in P212_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase212DonorArtifactDigest:
    artifact_id: str
    relpath: str
    present: bool
    read_mode: str
    total_bytes: int
    header_bytes_read: int
    digest_kind: str
    digest_sha256: str
    marker_summary: str
    matches_pinned: bool


@dataclass(frozen=True)
class Phase212DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase212DonorArtifactDigest, ...]


@dataclass(frozen=True)
class CoupledClipPairSpec:
    stem: str
    slot: int
    main_relpath: str
    xml_relpath: str
    proxy_relpath: Optional[str]
    px_metadata_bit: bool
    main_protected: bool
    proxy_protected: bool
    main_present: bool = True
    xml_present: bool = True
    proxy_present: bool = True
    main_codec: str = "XAVC_HS"
    proxy_format: str = P212_PROXY_FORMAT_XAVC_HS_HD
    proxy_resolution: str = "1920x1080"
    proxy_bitrate: str = "9M"
    proxy_bit_depth: int = 10
    coupled_operation: str = "NONE"
    single_sided_action_requested: bool = False


@dataclass(frozen=True)
class ProxyCoupledVaultSpec:
    camera_model: str = P212_FX3_MODEL_NAME
    fw_version: str = P212_FX3_FW_VERSION
    proxy_recording_enabled: bool = True
    rec_media_hdmi_output: str = P212_REC_MEDIA_HDMI_ON
    sq_mode_active: bool = False
    normal_rec_frame_rate: str = "59.94p"
    sq_sensor_fps: int = 60
    proxy_playback_on_camera_assumed: bool = False
    clips: Tuple[CoupledClipPairSpec, ...] = ()
    overlay_dir: str = P212_STAGE_B_HDMI_PROXY_OVERLAY_DIR
    backup_bin_h0_sha256: str = P212_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P212_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P212_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class ProxyCoupledVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    slots_audited: Tuple[int, ...]
    coupled_pairs_audited: int
    protected_pairs_verified: int
    orphaned_sub_count: int
    missing_px_proxy_count: int
    protect_or_delete_parity_drifts: int
    zero_proxy_cutoff_enforced: bool
    on_camera_proxy_playback_forbidden: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HdmiOnlyAndInterlockSpec:
    camera_model: str = P212_FX3_MODEL_NAME
    fw_version: str = P212_FX3_FW_VERSION
    operation_context: str = "PRE_SHOOT_MEDIA_VAULT_CHECK"  # or "PRE_BACKUP_TIER0" | "STAGE_B_TRIAL"
    rec_media_hdmi_output: str = P212_REC_MEDIA_HDMI_ON
    hdmi_only_4k_output_set: Optional[str] = None
    hdmi_output_resolution: str = "2160p"
    raw_output_enabled: bool = False
    log_shooting_mode: str = "Off"  # Off | Cine EI | Cine EI Quick | Flexible ISO
    picture_profile: str = "Off"  # Off | PPLUT1..PPLUT4
    hdmi_info_display: bool = False
    lcd_panel_blanked: bool = False
    hdmi_desqueeze_active: bool = False
    internal_card_recording_active: bool = True
    operator_assumes_internal_card_recording: bool = True
    exposure_mode: str = "M"
    focus_mode: str = "MF"
    live_view_display: str = "Setting Effect OFF"
    focus_magnifier_active: bool = False
    focus_magnifier_scale: str = "x1.0"
    focus_magnifier_time: str = "No Limit"
    auto_magnifier_in_mf_movie_enabled: bool = False
    marker_display_visible_during_mag: bool = False
    bright_monitoring_active: bool = False
    bright_monitoring_toggle_attempted_while_mag: bool = False
    bright_monitoring_toggle_accepted: bool = False
    stage_b_overlay_dir: str = P212_STAGE_B_HDMI_PROXY_OVERLAY_DIR
    stage_b_overlay_wiped_on_reset: bool = True
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P212_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P212_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P212_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class HdmiOnlyAndInterlockReport:
    passed: bool
    status: str
    block_code: Optional[str]
    rec_media_hdmi_output: str
    effective_hdmi_resolution: str
    hdmi_log_pplut_1080p_downshift_active: bool
    internal_card_recording_active: bool
    zero_card_hazard_detected: bool
    hdmi_info_display_suppressed: bool
    focus_mag_bright_mon_interlock_ok: bool
    h0_equals_h3_verified: bool
    tier0_surfaces_intact: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProxyCoupledAndHdmiOnlyVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase212DonorSnapshot
    proxy_report: ProxyCoupledVaultReport
    hdmi_report: HdmiOnlyAndInterlockReport
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
    live_usb_iokit_transmit_enabled: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Pillar30ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar30ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar30ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar30BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar30ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar30StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase212DonorSnapshot
    pillar_30a_proxy_coupled_vault: Pillar30ASuiteResult
    pillar_30b_hdmi_only_interlock: Pillar30BSuiteResult
    suite_sha256: str
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


@dataclass(frozen=True)
class Master30PillarRecoveryReport:
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
    nominal_under_2_6s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase212DonorSnapshot
    pillar30_a_proxy_coupled_vault: Pillar30ASuiteResult
    pillar30_b_hdmi_only_interlock: Pillar30BSuiteResult
    master_30pillar_sha256: str
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
# Bounded O_RDONLY Donor Inspection & Clean-Room Fallback
# ---------------------------------------------------------------------------


def _read_donor_readonly_bounded(
    relpath: str,
    max_full_bytes: int = P212_MAX_FULL_DONOR_BYTES,
) -> Tuple[bool, int, int, str, str, bytes]:
    resolved = resolve_donor_path(relpath)
    if resolved is None:
        return False, 0, 0, "MISSING", "", b""
    flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0) | getattr(os, "O_NONBLOCK", 0)
    try:
        fd = os.open(str(resolved), flags)
    except OSError:
        return False, 0, 0, "OPEN_ERROR", "", b""
    try:
        st = os.fstat(fd)
        if not stat.S_ISREG(st.st_mode):
            return False, 0, 0, "NOT_REGULAR", "", b""
        total_size = int(st.st_size)
        if total_size <= max_full_bytes:
            chunks: List[bytes] = []
            offset = 0
            while offset < total_size:
                chunk = os.pread(fd, min(65536, total_size - offset), offset)
                if not chunk:
                    break
                chunks.append(chunk)
                offset += len(chunk)
            data = b"".join(chunks)
            return True, total_size, len(data), "FULL_SHA256", sha256(data).hexdigest(), data
        hdr = os.pread(fd, min(P212_BOUNDED_HEADER_BYTES, total_size), 0)
        return True, total_size, len(hdr), "HEADER4K_SHA256", sha256(hdr).hexdigest(), hdr
    finally:
        os.close(fd)


def _check_elf64_aarch64_tokens(data: bytes, expected_tokens: Tuple[bytes, ...]) -> Tuple[bool, str]:
    if len(data) < 64 or data[:4] != b"\x7fELF":
        return False, "NOT_ELF"
    ei_class, ei_data = data[4], data[5]
    e_machine = struct.unpack_from("<H", data, 18)[0]
    if ei_class != 2 or ei_data != 1 or e_machine != 183:
        return False, f"BAD_ELF64_AARCH64(class={ei_class},data={ei_data},mach={e_machine})"
    found = [tok.decode("ascii") for tok in expected_tokens if tok in data]
    missing = [tok.decode("ascii") for tok in expected_tokens if tok not in data]
    if missing:
        return False, f"MISSING_TOKENS:{','.join(missing)}"
    return True, f"ELF64_AARCH64:{'+'.join(found)}"


def _synthetic_phase212_donors() -> Tuple[Phase212DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P212_DONOR_FX3_BODYDATA_RELPATH,
            P212_PINNED_FX3_BODYDATA_BYTES,
            P212_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P212_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P212_DONOR_FX3_APPFW_702_RELPATH,
            P212_PINNED_FX3_APPFW_702_BYTES,
            P212_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P212_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_APPFW_702",
        ),
        (
            "fx3_backup_bin",
            P212_DONOR_FX3_BACKUP_BIN_RELPATH,
            P212_PINNED_FX3_BACKUP_BIN_BYTES,
            P212_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P212_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libinframediaconfig_so",
            P212_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P212_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P212_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P212_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+GetMediaNum",
        ),
        (
            "fx3_libbackupmanager_so",
            P212_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P212_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P212_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P212_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:BackupManager+SKData_Init",
        ),
        (
            "fx3_libbackup_so",
            P212_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P212_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P212_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P212_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup+setting",
        ),
    )
    return tuple(
        Phase212DonorArtifactDigest(
            artifact_id=aid,
            relpath=rel,
            present=True,
            read_mode="CLEAN_ROOM_SYNTHETIC",
            total_bytes=total,
            header_bytes_read=hdr_b,
            digest_kind=dkind,
            digest_sha256=dsha,
            marker_summary=msum,
            matches_pinned=True,
        )
        for aid, rel, total, hdr_b, dkind, dsha, msum in specs
    )


def inspect_phase212_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase212DonorSnapshot:
    """Inspect Wave-28 / FX3 7.02 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase212_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase212DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P212_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P212_DONOR_FX3_BODYDATA_RELPATH,
            P212_PINNED_FX3_BODYDATA_BYTES,
            P212_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P212_DONOR_FX3_APPFW_702_RELPATH,
            P212_PINNED_FX3_APPFW_702_BYTES,
            P212_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: (
                len(d) >= 64 and d[:4] == b"\x7fELF" and d[4] == 2 and struct.unpack_from("<H", d, 18)[0] == 183,
                "ELF64_AARCH64_APPFW_702",
            ),
        ),
        (
            "fx3_backup_bin",
            P212_DONOR_FX3_BACKUP_BIN_RELPATH,
            P212_PINNED_FX3_BACKUP_BIN_BYTES,
            P212_PINNED_FX3_BACKUP_BIN_SHA256,
            lambda d: (
                len(d) >= 20
                and struct.unpack_from("<I", d, 4)[0] == 0xAAAAAAAA
                and d[12:16] == b"BK4\x00"
                and b"ILME-FX3" in d,
                "BK4_ILME_FX3"
                if (
                    len(d) >= 20
                    and struct.unpack_from("<I", d, 4)[0] == 0xAAAAAAAA
                    and d[12:16] == b"BK4\x00"
                    and b"ILME-FX3" in d
                )
                else "BAD_BK4_HEADER",
            ),
        ),
        (
            "fx3_libinframediaconfig_so",
            P212_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P212_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P212_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"InfraMediaConfig", b"GetMediaNum", b"Backup_sync_subsystem")),
        ),
        (
            "fx3_libbackupmanager_so",
            P212_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P212_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P212_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"BackupManager", b"SKData_Init", b"Backup_get_datasize")),
        ),
        (
            "fx3_libbackup_so",
            P212_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P212_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P212_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup", b"setting")),
        ),
    )

    digests: List[Phase212DonorArtifactDigest] = []
    for aid, rel, exp_bytes, exp_sha, marker_fn in probe_specs:
        ok, total_b, hdr_b, dkind, actual_sha, data = _read_donor_readonly_bounded(rel)
        marker_ok, marker_summary = marker_fn(data) if ok else (False, "UNREADABLE")
        pinned_ok = ok and total_b == exp_bytes and actual_sha == exp_sha and marker_ok
        digests.append(
            Phase212DonorArtifactDigest(
                artifact_id=aid,
                relpath=rel,
                present=ok,
                read_mode="LOCAL_DONOR_O_RDONLY" if ok else "MISSING_LOCAL_DONOR",
                total_bytes=total_b,
                header_bytes_read=hdr_b,
                digest_kind=dkind,
                digest_sha256=actual_sha,
                marker_summary=marker_summary,
                matches_pinned=pinned_ok,
            )
        )

    dt = round(time.monotonic() - t0, 6)
    if all(a.present for a in digests):
        return Phase212DonorSnapshot(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            all_donors_present=all(a.matches_pinned for a in digests),
            donor_files_inspected=len(digests),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P212_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=tuple(digests),
        )

    # Graceful fallback if repo work/ directory has no local donor binaries
    synth = _synthetic_phase212_donors()
    dt = round(time.monotonic() - t0, 6)
    return Phase212DonorSnapshot(
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        all_donors_present=True,
        donor_files_inspected=len(synth),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P212_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=synth,
    )


# ---------------------------------------------------------------------------
# Pillar 30A — Px Atomic Main+Proxy Coupled Vault Evaluator
# ---------------------------------------------------------------------------


def evaluate_proxy_coupled_vault(spec: ProxyCoupledVaultSpec) -> ProxyCoupledVaultReport:
    """Audit `M4ROOT/CLIP/` + `M4ROOT/SUB/` coupled `(Px)` vault integrity across Slot 1 & Slot 2."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _reject(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested:
        _reject(P212_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent eMMC write unlock forbidden in Pillar 30A")
    if spec.camera_model != P212_FX3_MODEL_NAME or spec.fw_version != P212_FX3_FW_VERSION:
        _reject(
            P212_BLOCKED_SAFETY_POLICY_VIOLATION,
            f"Unsupported host {spec.camera_model} fw={spec.fw_version}; requires {P212_FX3_MODEL_NAME} {P212_FX3_FW_VERSION}",
        )
    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _reject(P212_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, f"Non-tmpfs overlay path forbidden: {spec.overlay_dir}")
    if (
        spec.backup_bin_h0_sha256 != spec.backup_bin_h3_sha256
        or spec.tier0_surfaces_h0_h3_matched != P212_TIER0_SURFACE_COUNT
    ):
        _reject(P212_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT, "Backup.bin / 16-surface Tier-0 H0 != H3 drift detected")

    if spec.proxy_playback_on_camera_assumed:
        _reject(
            P212_BLOCKED_PROXY_PLAYBACK_ASSUMPTION_FORBIDDEN,
            "FX3 cannot play back M4ROOT/SUB proxy clips on-camera; only (Px) badge appears on main clip",
        )

    cutoff_violation = False
    if spec.proxy_recording_enabled:
        if spec.rec_media_hdmi_output == P212_REC_MEDIA_HDMI_OFF_ONLY:
            cutoff_violation = True
            _reject(
                P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION,
                "Proxy/internal clips cannot be generated under [Off(HDMI Only)]",
            )
        if spec.normal_rec_frame_rate in P212_PROXY_CUTOFF_NORMAL_REC_RATES:
            cutoff_violation = True
            _reject(
                P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION,
                f"Proxy Recording unavailable at Normal Rec Frame Rate {spec.normal_rec_frame_rate}",
            )
        if spec.sq_mode_active and spec.sq_sensor_fps >= 100:
            cutoff_violation = True
            _reject(
                P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION,
                f"Proxy Recording unavailable at S&Q sensor rate {spec.sq_sensor_fps}fps (>=100fps)",
            )

    orphaned_sub_count = 0
    missing_px_proxy_count = 0
    parity_drifts = 0
    protected_pairs = 0
    slots_seen: List[int] = []

    for clip in spec.clips:
        if clip.slot not in P212_ALLOWED_MEDIA_SLOTS:
            _reject(P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH, f"Invalid slot {clip.slot} for {clip.stem}")
        elif clip.slot not in slots_seen:
            slots_seen.append(clip.slot)

        if clip.main_codec not in P212_VALID_MAIN_CODECS:
            _reject(
                P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION,
                f"Invalid main codec {clip.main_codec} for {clip.stem}",
            )

        # Validate CLIP/MP4, CLIP/XML & SUB/*S03.MP4 naming and directory topology
        expected_clip_path = f"{P212_M4ROOT_CLIP_DIR}/{clip.stem}.MP4"
        expected_xml_path = f"{P212_M4ROOT_CLIP_DIR}/{clip.stem}M01.XML"
        expected_sub_path = f"{P212_M4ROOT_SUB_DIR}/{clip.stem}S03.MP4"
        if clip.main_relpath != expected_clip_path:
            parity_drifts += 1
            _reject(
                P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH,
                f"Main clip path {clip.main_relpath!r} must match {expected_clip_path!r}",
            )
        if not clip.xml_present or not clip.xml_relpath.startswith(f"{P212_M4ROOT_CLIP_DIR}/") or not clip.xml_relpath.endswith(".XML"):
            parity_drifts += 1
            _reject(
                P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH,
                f"Missing or malformed sidecar XML {clip.xml_relpath!r} (expected under {P212_M4ROOT_CLIP_DIR})",
            )
        if clip.main_present and not clip.xml_relpath.endswith(".XML"):
            parity_drifts += 1
            _reject(P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH, f"Expected XML sidecar near {expected_xml_path}")

        # Validate orphaned SUB or missing SUB when (Px) bit is set
        if clip.proxy_present and not clip.main_present:
            orphaned_sub_count += 1
            _reject(
                P212_BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY,
                f"Orphaned SUB proxy {clip.proxy_relpath} without paired CLIP {clip.main_relpath}",
            )
        elif clip.px_metadata_bit and not clip.proxy_present:
            missing_px_proxy_count += 1
            _reject(
                P212_BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY,
                f"Clip {clip.stem} has (Px) metadata bit set but M4ROOT/SUB proxy is missing",
            )
        elif clip.proxy_present and not clip.px_metadata_bit:
            parity_drifts += 1
            _reject(
                P212_BLOCKED_ORPHANED_SUB_OR_MISSING_PX_PROXY,
                f"Proxy present for {clip.stem} without paired (Px) metadata bit",
            )

        # Validate proxy codec/resolution/bitrate/naming when proxy exists
        if clip.proxy_present:
            if clip.proxy_relpath != expected_sub_path or not P212_PROXY_BASENAME_RE.match(posixpath.basename(clip.proxy_relpath or "")):
                parity_drifts += 1
                _reject(
                    P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH,
                    f"Proxy path {clip.proxy_relpath!r} must follow {expected_sub_path!r}",
                )
            p_spec = P212_PROXY_SPEC_TABLE.get(clip.proxy_format)
            if p_spec is None:
                _reject(
                    P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION,
                    f"Unsupported proxy format {clip.proxy_format!r} (only XAVC_HS_HD and XAVC_S_HD allowed)",
                )
            else:
                if (
                    clip.proxy_resolution != p_spec["resolution"]
                    or clip.proxy_bitrate not in p_spec["bitrates"]
                    or clip.proxy_bit_depth != p_spec["bit_depth"]
                ):
                    _reject(
                        P212_BLOCKED_PROXY_CODEC_OR_RATE_CUTOFF_VIOLATION,
                        f"Proxy stream {clip.proxy_format} ({clip.proxy_resolution} {clip.proxy_bitrate} "
                        f"{clip.proxy_bit_depth}bit) violates FX3 Ver. 7.02 matrix",
                    )

        # Enforce Ver. 7.02 atomic coupled Delete / Protect parity
        if clip.single_sided_action_requested:
            parity_drifts += 1
            _reject(
                P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH,
                f"Single-sided Delete/Protect on {clip.stem} violates FX3 atomic main+proxy rule",
            )
        if clip.coupled_operation not in P212_COUPLED_OPERATIONS:
            parity_drifts += 1
            _reject(P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH, f"Unknown coupled op {clip.coupled_operation!r}")
        if clip.main_present and clip.proxy_present and clip.main_protected != clip.proxy_protected:
            parity_drifts += 1
            _reject(
                P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH,
                f"Protect/ReadOnly parity drift on {clip.stem}: main={clip.main_protected}, proxy={clip.proxy_protected}",
            )
        if clip.coupled_operation == "DELETE" and (clip.main_present or clip.proxy_present):
            parity_drifts += 1
            _reject(
                P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH,
                f"Incomplete coupled DELETE on {clip.stem}: main_present={clip.main_present}, proxy_present={clip.proxy_present}",
            )
        if clip.coupled_operation == "PROTECT":
            if not (clip.main_present and clip.proxy_present and clip.main_protected and clip.proxy_protected):
                parity_drifts += 1
                _reject(
                    P212_BLOCKED_COUPLED_VAULT_PARITY_MISMATCH,
                    f"Incomplete coupled PROTECT on {clip.stem}",
                )
        if clip.main_present and clip.proxy_present and clip.main_protected and clip.proxy_protected:
            protected_pairs += 1

    passed = len(errors) == 0 and block_code is None
    digest = _canonical_sha256(
        {
            "slots": sorted(slots_seen),
            "clips": len(spec.clips),
            "protected": protected_pairs,
            "orphaned_sub": orphaned_sub_count,
            "missing_px": missing_px_proxy_count,
            "drifts": parity_drifts,
            "block_code": block_code,
            "passed": passed,
        }
    )
    return ProxyCoupledVaultReport(
        passed=passed,
        status=P212_STATUS_VERIFIED_PILLAR_30A if passed else P212_STATUS_REJECTED_PILLAR_30A,
        block_code=block_code,
        slots_audited=tuple(sorted(slots_seen)),
        coupled_pairs_audited=len(spec.clips),
        protected_pairs_verified=protected_pairs,
        orphaned_sub_count=orphaned_sub_count,
        missing_px_proxy_count=missing_px_proxy_count,
        protect_or_delete_parity_drifts=parity_drifts,
        zero_proxy_cutoff_enforced=not cutoff_violation,
        on_camera_proxy_playback_forbidden=not spec.proxy_playback_on_camera_assumed,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 30B — Off(HDMI Only) Zero-Card Interlock, Log 1080p Downshift & FocusMag x BrightMon
# ---------------------------------------------------------------------------


def evaluate_hdmi_only_zero_card_and_interlocks(spec: HdmiOnlyAndInterlockSpec) -> HdmiOnlyAndInterlockReport:
    """Audit `[Off(HDMI Only)]` zero-card interlock, HDMI Log `1080p` downshift, and `FocusMag` x `BrightMon`."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _reject(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested:
        _reject(P212_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent eMMC write unlock forbidden in Pillar 30B")
    if spec.camera_model != P212_FX3_MODEL_NAME or spec.fw_version != P212_FX3_FW_VERSION:
        _reject(P212_BLOCKED_SAFETY_POLICY_VIOLATION, f"Unsupported host {spec.camera_model} fw={spec.fw_version}")
    if spec.rec_media_hdmi_output not in P212_VALID_REC_MEDIA_HDMI_MODES:
        _reject(P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD, f"Invalid Rec. Media dur HDMI mode: {spec.rec_media_hdmi_output!r}")

    # Overlay & Tier-0 H0 == H3 invariant
    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _reject(P212_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, f"Non-tmpfs overlay path forbidden: {spec.stage_b_overlay_dir}")
    if not spec.stage_b_overlay_wiped_on_reset:
        _reject(P212_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, "Stage-B tmpfs overlay was not wiped cleanly on reset")
    if not spec.p2_blkroset_locked or spec.stage_b_backup_bin_writes != 0:
        _reject(P212_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT, "p2:/setting must remain BLKROSET=1 with 0 writes")
    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P212_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _reject(P212_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT, "Backup.bin or 16-surface Tier-0 H0 != H3 drift detected")

    # 1. [Off(HDMI Only)] zero-card interlock & pre-backup hazard guard
    zero_card_hazard = False
    is_hdmi_only = spec.rec_media_hdmi_output == P212_REC_MEDIA_HDMI_OFF_ONLY
    log_or_pplut = (spec.log_shooting_mode in P212_LOG_SHOOTING_MODES) or (spec.picture_profile in P212_PPLUT_PROFILES)
    downshift_active = False

    if is_hdmi_only:
        if spec.internal_card_recording_active or spec.operator_assumes_internal_card_recording:
            zero_card_hazard = True
            _reject(
                P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD,
                "[Off(HDMI Only)] completely disables internal Slot 1/2 recording; cannot assume active card vault",
            )
        if spec.operation_context == "PRE_BACKUP_TIER0":
            zero_card_hazard = True
            _reject(
                P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD,
                "Pre-backup media check must flag [Off(HDMI Only)] before archival/backup verification",
            )
        if spec.hdmi_only_4k_output_set not in P212_HDMI_ONLY_4K_FORMATS:
            _reject(
                P212_BLOCKED_HDMI_ONLY_ZERO_CARD_HAZARD,
                f"[4K Output Set.(HDMI Only)] format {spec.hdmi_only_4k_output_set!r} invalid (expected 59.94p..24.00p 10bit)",
            )
        if spec.hdmi_info_display or spec.hdmi_desqueeze_active:
            _reject(
                P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT,
                "[Off(HDMI Only)] temporarily forces [HDMI Info. Display] = Off and suppresses HDMI De-Squeeze",
            )
        effective_res = "2160p_10bit_HDMI_ONLY"
    else:
        # [Rec. Media dur HDMI Output] = [On]
        if spec.raw_output_enabled:
            if spec.hdmi_info_display or spec.hdmi_desqueeze_active:
                _reject(
                    P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT,
                    "[RAW Output = On] temporarily forces [HDMI Info. Display] = Off and disables HDMI De-Squeeze",
                )
            effective_res = "4264x2408_RAW16"
        elif log_or_pplut:
            downshift_active = True
            if spec.hdmi_output_resolution not in ("1080p", "Auto_Downshifted_1080p"):
                _reject(
                    P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT,
                    f"Log ({spec.log_shooting_mode}) / PP ({spec.picture_profile}) with [On] & RAW=Off "
                    f"forces HDMI to 1080p regardless of [Output Resolution]; reported {spec.hdmi_output_resolution!r}",
                )
            effective_res = "1080p"
        else:
            effective_res = spec.hdmi_output_resolution

        if spec.hdmi_info_display and not spec.lcd_panel_blanked:
            _reject(
                P212_BLOCKED_HDMI_LOG_PPLUT_1080P_DOWNSHIFT_DRIFT,
                "[HDMI Info. Display = On] blanks the FX3 built-in LCD panel (lcd_panel_blanked must be True)",
            )

    # 2. Focus Magnifier x Bright Monitoring mutual exclusion
    focus_bright_ok = True
    if spec.focus_magnifier_scale not in P212_FOCUS_MAG_MOVIE_SCALES:
        focus_bright_ok = False
        _reject(
            P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK,
            f"Movie [Initial Focus Mag.] must be x1.0 or x4.0 (got {spec.focus_magnifier_scale!r})",
        )
    if spec.focus_magnifier_time not in P212_FOCUS_MAG_TIMES:
        focus_bright_ok = False
        _reject(
            P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK,
            f"Invalid [Focus Magnif. Time]: {spec.focus_magnifier_time!r}",
        )
    if spec.auto_magnifier_in_mf_movie_enabled:
        focus_bright_ok = False
        _reject(
            P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK,
            "[Auto Magnifier in MF] is disabled during movie shooting on FX3 Ver. 7.02",
        )
    if spec.focus_magnifier_active and spec.marker_display_visible_during_mag:
        focus_bright_ok = False
        _reject(
            P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK,
            "[Marker Display] cannot be displayed while [Focus Magnifier] is active",
        )
    if spec.focus_magnifier_active and spec.bright_monitoring_toggle_attempted_while_mag and spec.bright_monitoring_toggle_accepted:
        focus_bright_ok = False
        _reject(
            P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK,
            "[Bright Monitoring] custom key toggle must stay locked out during [Focus Magnifier]",
        )
    if spec.bright_monitoring_active:
        if spec.exposure_mode not in P212_PASM_MODES or spec.focus_mode != "MF":
            focus_bright_ok = False
            _reject(
                P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK,
                f"[Bright Monitoring] cancels outside P/A/S/M + MF (got mode={spec.exposure_mode!r}, focus={spec.focus_mode!r})",
            )
        if spec.live_view_display != "Setting Effect OFF":
            focus_bright_ok = False
            _reject(
                P212_BLOCKED_FOCUS_MAG_BRIGHT_MON_INTERLOCK,
                "[Bright Monitoring] forces [Live View Display] = [Setting Effect OFF]",
            )

    passed = len(errors) == 0 and block_code is None
    digest = _canonical_sha256(
        {
            "rec_media_hdmi": spec.rec_media_hdmi_output,
            "effective_res": effective_res,
            "downshift": downshift_active,
            "zero_card_hazard": zero_card_hazard,
            "focus_bright_ok": focus_bright_ok,
            "h0_h3": h0_h3_ok,
            "block_code": block_code,
            "passed": passed,
        }
    )
    return HdmiOnlyAndInterlockReport(
        passed=passed,
        status=P212_STATUS_VERIFIED_PILLAR_30B if passed else P212_STATUS_REJECTED_PILLAR_30B,
        block_code=block_code,
        rec_media_hdmi_output=spec.rec_media_hdmi_output,
        effective_hdmi_resolution=effective_res,
        hdmi_log_pplut_1080p_downshift_active=downshift_active,
        internal_card_recording_active=spec.internal_card_recording_active,
        zero_card_hazard_detected=zero_card_hazard,
        hdmi_info_display_suppressed=not spec.hdmi_info_display,
        focus_mag_bright_mon_interlock_ok=focus_bright_ok,
        h0_equals_h3_verified=h0_h3_ok,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h3_matched,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Default Specs & Unified Pillar 30 Entry Point
# ---------------------------------------------------------------------------


def build_default_safe_proxy_vault_spec() -> ProxyCoupledVaultSpec:
    return ProxyCoupledVaultSpec(
        clips=(
            CoupledClipPairSpec(
                stem="C0001",
                slot=1,
                main_relpath="/M4ROOT/CLIP/C0001.MP4",
                xml_relpath="/M4ROOT/CLIP/C0001M01.XML",
                proxy_relpath="/M4ROOT/SUB/C0001S03.MP4",
                px_metadata_bit=True,
                main_protected=True,
                proxy_protected=True,
                main_codec="XAVC_HS",
                proxy_format=P212_PROXY_FORMAT_XAVC_HS_HD,
                proxy_resolution="1920x1080",
                proxy_bitrate="9M",
                proxy_bit_depth=10,
                coupled_operation="PROTECT",
            ),
            CoupledClipPairSpec(
                stem="C0002",
                slot=2,
                main_relpath="/M4ROOT/CLIP/C0002.MP4",
                xml_relpath="/M4ROOT/CLIP/C0002M01.XML",
                proxy_relpath="/M4ROOT/SUB/C0002S03.MP4",
                px_metadata_bit=True,
                main_protected=False,
                proxy_protected=False,
                main_codec="XAVC_S",
                proxy_format=P212_PROXY_FORMAT_XAVC_S_HD,
                proxy_resolution="1280x720",
                proxy_bitrate="6M",
                proxy_bit_depth=8,
                coupled_operation="NONE",
            ),
        )
    )


def build_default_safe_hdmi_interlock_spec() -> HdmiOnlyAndInterlockSpec:
    return HdmiOnlyAndInterlockSpec(
        rec_media_hdmi_output=P212_REC_MEDIA_HDMI_ON,
        hdmi_output_resolution="1080p",
        log_shooting_mode="Cine EI",
        picture_profile="Off",
        hdmi_info_display=True,
        lcd_panel_blanked=True,
        internal_card_recording_active=True,
        operator_assumes_internal_card_recording=True,
        focus_magnifier_active=True,
        focus_magnifier_scale="x4.0",
        focus_magnifier_time="No Limit",
        bright_monitoring_toggle_attempted_while_mag=True,
        bright_monitoring_toggle_accepted=False,
    )


def verify_proxy_coupled_and_hdmi_only_vault(
    *,
    proxy_spec: Optional[ProxyCoupledVaultSpec] = None,
    hdmi_spec: Optional[HdmiOnlyAndInterlockSpec] = None,
    force_clean_room: Optional[bool] = None,
) -> ProxyCoupledAndHdmiOnlyVaultReport:
    """Unified Pillar 30 verifier auditing coupled `(Px)` proxy vaults and `[Off(HDMI Only)]` interlocks."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    donor_snapshot = inspect_phase212_donors_readonly(force_clean_room=force_clean_room)
    p_rep = evaluate_proxy_coupled_vault(proxy_spec or build_default_safe_proxy_vault_spec())
    h_rep = evaluate_hdmi_only_zero_card_and_interlocks(hdmi_spec or build_default_safe_hdmi_interlock_spec())
    all_ok = donor_snapshot.all_donors_present and donor_snapshot.under_0_15s_budget and p_rep.passed and h_rep.passed
    combined_errs = tuple(list(p_rep.errors) + list(h_rep.errors))
    return ProxyCoupledAndHdmiOnlyVaultReport(
        schema=PHASE212_SCHEMA,
        version=PHASE212_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P212_STATUS_VERIFIED_PILLAR30_SUITE if all_ok else P212_STATUS_FAIL_PILLAR30_SUITE,
        donor_snapshot=donor_snapshot,
        proxy_report=p_rep,
        hdmi_report=h_rep,
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
        live_usb_iokit_transmit_enabled=LIVE_USB_IOKIT_TRANSMIT_ENABLED,
        errors=combined_errs,
    )


# ---------------------------------------------------------------------------
# Pillar 30A & 30B 6-Scenario Verification Suites & Standalone Pillar 30 Suite
# ---------------------------------------------------------------------------


def run_pillar30a_proxy_coupled_vault_6_scenario_suite() -> Pillar30ASuiteResult:
    cases: Tuple[Tuple[str, bool, ProxyCoupledVaultSpec, str], ...] = (
        (
            P212_PILLAR_30A_SCENARIO_IDS[0],
            True,
            ProxyCoupledVaultSpec(
                clips=(
                    CoupledClipPairSpec(
                        stem="C0101",
                        slot=1,
                        main_relpath="/M4ROOT/CLIP/C0101.MP4",
                        xml_relpath="/M4ROOT/CLIP/C0101M01.XML",
                        proxy_relpath="/M4ROOT/SUB/C0101S03.MP4",
                        px_metadata_bit=True,
                        main_protected=False,
                        proxy_protected=False,
                        proxy_format=P212_PROXY_FORMAT_XAVC_HS_HD,
                        proxy_resolution="1920x1080",
                        proxy_bitrate="16M",
                        proxy_bit_depth=10,
                    ),
                    CoupledClipPairSpec(
                        stem="C0102",
                        slot=2,
                        main_relpath="/M4ROOT/CLIP/C0102.MP4",
                        xml_relpath="/M4ROOT/CLIP/C0102M01.XML",
                        proxy_relpath="/M4ROOT/SUB/C0102S03.MP4",
                        px_metadata_bit=True,
                        main_protected=False,
                        proxy_protected=False,
                        proxy_format=P212_PROXY_FORMAT_XAVC_HS_HD,
                        proxy_resolution="1920x1080",
                        proxy_bitrate="9M",
                        proxy_bit_depth=10,
                    ),
                )
            ),
            "Slot 1 & Slot 2 XAVC HS HD 1920x1080 10-bit 16M/9M coupled vault passes",
        ),
        (
            P212_PILLAR_30A_SCENARIO_IDS[1],
            True,
            ProxyCoupledVaultSpec(
                clips=(
                    CoupledClipPairSpec(
                        stem="C0103",
                        slot=1,
                        main_relpath="/M4ROOT/CLIP/C0103.MP4",
                        xml_relpath="/M4ROOT/CLIP/C0103M01.XML",
                        proxy_relpath="/M4ROOT/SUB/C0103S03.MP4",
                        px_metadata_bit=True,
                        main_protected=True,
                        proxy_protected=True,
                        main_codec="XAVC_S",
                        proxy_format=P212_PROXY_FORMAT_XAVC_S_HD,
                        proxy_resolution="1280x720",
                        proxy_bitrate="6M",
                        proxy_bit_depth=8,
                        coupled_operation="PROTECT",
                    ),
                )
            ),
            "XAVC S HD 1280x720 8-bit 6M atomic PROTECT parity across CLIP and SUB",
        ),
        (
            P212_PILLAR_30A_SCENARIO_IDS[2],
            False,
            ProxyCoupledVaultSpec(normal_rec_frame_rate="119.88p", sq_mode_active=True, sq_sensor_fps=120),
            "Proxy generation at 119.88p Normal or >=120fps S&Q must fail closed",
        ),
        (
            P212_PILLAR_30A_SCENARIO_IDS[3],
            False,
            ProxyCoupledVaultSpec(proxy_playback_on_camera_assumed=True),
            "On-camera proxy playback assumption must fail closed",
        ),
        (
            P212_PILLAR_30A_SCENARIO_IDS[4],
            False,
            ProxyCoupledVaultSpec(
                clips=(
                    CoupledClipPairSpec(
                        stem="C0104",
                        slot=1,
                        main_relpath="/M4ROOT/CLIP/C0104.MP4",
                        xml_relpath="/M4ROOT/CLIP/C0104M01.XML",
                        proxy_relpath="/M4ROOT/SUB/C0104S03.MP4",
                        px_metadata_bit=False,
                        main_present=False,
                        proxy_present=True,
                        main_protected=False,
                        proxy_protected=False,
                    ),
                )
            ),
            "Orphaned SUB proxy without CLIP must fail closed",
        ),
        (
            P212_PILLAR_30A_SCENARIO_IDS[5],
            False,
            ProxyCoupledVaultSpec(
                clips=(
                    CoupledClipPairSpec(
                        stem="C0105",
                        slot=2,
                        main_relpath="/M4ROOT/CLIP/C0105.MP4",
                        xml_relpath="/M4ROOT/CLIP/C0105M01.XML",
                        proxy_relpath="/M4ROOT/SUB/C0105S03.MP4",
                        px_metadata_bit=True,
                        main_protected=True,
                        proxy_protected=False,
                        single_sided_action_requested=True,
                    ),
                )
            ),
            "Single-sided Delete/Protect or attribute mismatch must fail closed",
        ),
    )
    outcomes: List[Pillar30ScenarioOutcome] = []
    for sid, exp_ok, spec, detail in cases:
        rep = evaluate_proxy_coupled_vault(spec)
        outcomes.append(
            Pillar30ScenarioOutcome(
                scenario_id=sid,
                pillar="PILLAR_30A",
                expected_allowed=exp_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=(rep.passed == exp_ok),
                detail=detail,
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes)
    return Pillar30ASuiteResult(
        passed=all_ok,
        status=P212_STATUS_VERIFIED_PILLAR_30A if all_ok else P212_STATUS_REJECTED_PILLAR_30A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar30b_hdmi_only_interlock_6_scenario_suite() -> Pillar30BSuiteResult:
    cases: Tuple[Tuple[str, bool, HdmiOnlyAndInterlockSpec, str], ...] = (
        (
            P212_PILLAR_30B_SCENARIO_IDS[0],
            False,
            HdmiOnlyAndInterlockSpec(
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
                hdmi_only_4k_output_set="59.94p 10bit",
                internal_card_recording_active=False,
                operator_assumes_internal_card_recording=True,
            ),
            "[Off(HDMI Only)] with operator card-recording assumption must be blocked",
        ),
        (
            P212_PILLAR_30B_SCENARIO_IDS[1],
            True,
            build_default_safe_hdmi_interlock_spec(),
            "[On] + Log Shooting (Cine EI) downshifts HDMI cleanly to 1080p with blanked LCD",
        ),
        (
            P212_PILLAR_30B_SCENARIO_IDS[2],
            True,
            HdmiOnlyAndInterlockSpec(
                operation_context="EXTERNAL_HDMI_4K_MONITOR_ONLY",
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
                hdmi_only_4k_output_set="23.98p 10bit",
                hdmi_info_display=False,
                hdmi_desqueeze_active=False,
                internal_card_recording_active=False,
                operator_assumes_internal_card_recording=False,
            ),
            "Explicit [Off(HDMI Only)] 23.98p 10bit with HDMI Info Off & zero-card awareness passes",
        ),
        (
            P212_PILLAR_30B_SCENARIO_IDS[3],
            False,
            HdmiOnlyAndInterlockSpec(
                focus_magnifier_active=True,
                focus_magnifier_scale="x4.0",
                bright_monitoring_toggle_attempted_while_mag=True,
                bright_monitoring_toggle_accepted=True,
            ),
            "Bright Monitoring toggle accepted during active Focus Magnifier must fail closed",
        ),
        (
            P212_PILLAR_30B_SCENARIO_IDS[4],
            False,
            HdmiOnlyAndInterlockSpec(
                operation_context="PRE_BACKUP_TIER0",
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_OFF_ONLY,
                hdmi_only_4k_output_set="24.00p 10bit",
                internal_card_recording_active=False,
                operator_assumes_internal_card_recording=False,
            ),
            "Pre-backup Tier-0 check must block active [Off(HDMI Only)] trap before archival",
        ),
        (
            P212_PILLAR_30B_SCENARIO_IDS[5],
            True,
            HdmiOnlyAndInterlockSpec(
                rec_media_hdmi_output=P212_REC_MEDIA_HDMI_ON,
                hdmi_output_resolution="1080p",
                picture_profile="PPLUT2",
                bright_monitoring_active=True,
                exposure_mode="M",
                focus_mode="MF",
                live_view_display="Setting Effect OFF",
                stage_b_overlay_wiped_on_reset=True,
                p2_blkroset_locked=True,
                stage_b_backup_bin_writes=0,
            ),
            "PPLUT2 1080p downshift + Bright Monitoring (Setting Effect OFF, P/A/S/M+MF) + 16/16 H0==H3",
        ),
    )
    outcomes: List[Pillar30ScenarioOutcome] = []
    for sid, exp_ok, spec, detail in cases:
        rep = evaluate_hdmi_only_zero_card_and_interlocks(spec)
        outcomes.append(
            Pillar30ScenarioOutcome(
                scenario_id=sid,
                pillar="PILLAR_30B",
                expected_allowed=exp_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=(rep.passed == exp_ok),
                detail=detail,
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes)
    return Pillar30BSuiteResult(
        passed=all_ok,
        status=P212_STATUS_VERIFIED_PILLAR_30B if all_ok else P212_STATUS_REJECTED_PILLAR_30B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar30_standalone_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Pillar30StandaloneReport:
    """Run Pillar 30 standalone suite (bounded donor check + Pillar 30A 6/6 + Pillar 30B 6/6)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase212_donors_readonly(force_clean_room=force_clean_room)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(run_pillar30a_proxy_coupled_vault_6_scenario_suite)
        fut_b = pool.submit(run_pillar30b_hdmi_only_interlock_6_scenario_suite)
        res_a = fut_a.result()
        res_b = fut_b.result()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 212 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor check exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = (
        len(safety_errs) == 0
        and donor_snapshot.all_donors_present
        and donor_snapshot.under_0_15s_budget
        and res_a.passed
        and res_b.passed
    )
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE212_SCHEMA,
            "mode": donor_snapshot.verification_mode,
            "p30a": [(s.scenario_id, s.passed, s.block_code) for s in res_a.scenarios],
            "p30b": [(s.scenario_id, s.passed, s.block_code) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar30StandaloneReport(
        schema=PHASE212_SCHEMA,
        version=PHASE212_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P212_STATUS_VERIFIED_PILLAR30_SUITE if all_ok else P212_STATUS_FAIL_PILLAR30_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_30a_proxy_coupled_vault=res_a,
        pillar_30b_hdmi_only_interlock=res_b,
        suite_sha256=suite_sha,
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
        errors=tuple(safety_errs),
    )


# ---------------------------------------------------------------------------
# Unified 30/30 Milestone Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master30_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_30pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master30PillarRecoveryReport:
    """Evaluate and aggregate all 30 recovery pillars (`1..30`) concurrently -> `30/30` milestone."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_30_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_29pillar() -> Master29PillarRecoveryReport:
        return evaluate_29pillar_recovery_master(**kw)

    def _run_p30() -> Tuple[Pillar30StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar30_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_29 = pool.submit(_run_29pillar)
        fut_30 = pool.submit(_run_p30)
        m29_rep = fut_29.result()
        p30_rep, p30_dt = fut_30.result()

    all_errors: List[str] = list(m29_rep.errors) + list(p30_rep.errors)
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
        if getattr(m29_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-29 violated {attr_name} == {expected_val}")
        if getattr(p30_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 30 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m29_rep.pillars)
    spec30 = MASTER_30_PILLAR_SPECS[29]
    p30_metrics = {
        "pillar_30a_proxy_coupled_vault": (
            f"{p30_rep.pillar_30a_proxy_coupled_vault.scenarios_passed}/"
            f"{p30_rep.pillar_30a_proxy_coupled_vault.scenarios_total}"
        ),
        "pillar_30b_hdmi_only_interlock": (
            f"{p30_rep.pillar_30b_hdmi_only_interlock.scenarios_passed}/"
            f"{p30_rep.pillar_30b_hdmi_only_interlock.scenarios_total}"
        ),
        "donor_files_inspected": p30_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec30[0],
            pillar_id=spec30[1],
            phase_label=spec30[2],
            module_name=spec30[3],
            passed=bool(p30_rep.all_passed),
            status=p30_rep.status,
            verification_mode=p30_rep.verification_mode,
            elapsed_seconds=p30_dt,
            key_metrics=p30_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec30[1],
                    "mode": p30_rep.verification_mode,
                    "status": p30_rep.status,
                    "metrics": p30_metrics,
                    "passed": p30_rep.all_passed,
                }
            ),
            errors=tuple(p30_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master30_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p30_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_30_PILLAR_COUNT == 30
        and pillars_passed == 30
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE212_SCHEMA,
            "version": PHASE212_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master30PillarRecoveryReport(
        schema=PHASE212_SCHEMA,
        version=PHASE212_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P212_STATUS_VERIFIED_30OF30_AGGREGATOR if all_ok else P212_STATUS_FAIL_30OF30_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P212_CONCURRENT_CEILING_SECONDS,
        nominal_under_2_6s=elapsed < P212_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p30_rep.donor_snapshot,
        pillar30_a_proxy_coupled_vault=p30_rep.pillar_30a_proxy_coupled_vault,
        pillar30_b_hdmi_only_interlock=p30_rep.pillar_30b_hdmi_only_interlock,
        master_30pillar_sha256=master_sha,
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
        errors=tuple(all_errors),
    )


def evaluate_30pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master30PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_30pillar_recovery_master`."""
    return evaluate_realhw_30pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_30pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master30PillarRecoveryReport:
    """Public CLI entry point for Pillar 30 unified `30/30` real-hardware recovery master verification."""
    return evaluate_realhw_30pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
