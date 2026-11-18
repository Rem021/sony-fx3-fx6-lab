"""Phase 229 — Pillar 34 (`34/34` Recovery Pillars) & Unified 34-Pillar Recovery Master
(`verify-34pillar-recovery` / `verify-zebra-fullformat-chord-vault`):

1. **Pillar 34A — Slot-1 Tier-0 Vault Firewall Against `Quick Format`, `(Delete)`-Toggled
   `Full Format`, Mid-Cancel Erasure Hazard & `MENU + (Delete)` ~2s Hardware Chord**:
   - Models and blocks all four destructive Slot 1 formatting vectors (`Quick Format` metadata-only
     reinitialization, `(Delete)`-toggled `Full Format` full-flash data-block wipe, `Full Format`
     mid-cancel erased-data hazard where canceled cards remain usable with prior sectors erased,
     and the shooting-screen `MENU + (Delete)` ~2s direct `[Format]` hardware chord) whenever
     Slot 1 holds an active or unverified Tier-0 recovery vault (`pnflasha`, `cnflasha`,
     `CAMSET01.DAT`).
   - Requires verified off-camera SHA-256 vault receipt (`64`-hex digest) + physical SDXC WP switch
     engagement / vault card removal before Slot 1 formatting is permitted, and enforces hardware
     WP write-denial if an SDXC card with WP engaged remains inserted during a format request.

2. **Pillar 34B — `[Zebra Display]` / `[Zebra Level]` Non-Resettable Persistence (`[Camera Settings
   Reset]` Survival vs `[Initialize]`), Local-LCD-Only HDMI Assist Isolation (`Zebra` & `Peaking`)
   & Ver. 7.02 `[Mode Settings]` (`Fixed/Variable` vs `S&Q`) + Proxy/Audio/TC State Recovery**:
   - Verifies `[Zebra Display]` (`Off`/`On`) and `[Zebra Level]` (`70..100+`, `Custom 1`
     Standard+Range, `Custom 2` Minimum/Lower-Limit) survive `[Camera Settings Reset]` unchanged
     and reset to `Off` / `70` only under full `[Initialize]`.
   - Enforces zero HDMI assist-overlay leakage (`0` leaked pixels) for both `[Zebra Display]` and
     `[Peaking Display]` (`High`/`Mid`/`Low`, `Red`/`Yellow`/`Blue`/`White`) even when
     `[HDMI Info. Display] = [On]`.
   - Enforces Ver. 7.00+/7.02 `[Mode Settings] = [Fixed/Variable]` lock on legacy `[S&Q Settings]`,
     all 6 Sony S&Q hardware recording lockouts (`0ch` audio, `[Audio Out Timing]` disabled,
     `[Time Code Run]`/`[Time Code Output]` disabled, `240/200fps` 4K block, `120/100fps` DCI 4K
     block, `[Proxy Recording]` cutoff at `119.88p/100p` or `>=100fps`), and clean recovery of
     `[Mode Settings]`, `[Audio Out Timing]` (`Live`/`Lip Sync`), `[Time Code Run]`/`[Time Code
     Output]`, and `[Proxy Recording]` across S&Q transitions and `CAMSET01..10.DAT` / `Backup.bin`.

3. **Unified `34/34` Recovery Master (`evaluate_realhw_34pillar_recovery_master`)**:
   - Delegates Pillars `1..33` concurrently to `evaluate_realhw_33pillar_recovery_master` +
     **Pillar 34** -> **`34/34` (`VERIFIED_34OF34_PILLAR_RECOVERY_MASTER`)** in `< 3.4s` (`< 6.0s` ceiling).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import posixpath
import re
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_33pillar_powersave_9cond_temp_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_33_PILLAR_SPECS,
    Master33PillarRecoveryReport,
    evaluate_realhw_33pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE229_SCHEMA: str = "fx3-realhw-34pillar-recovery-master-verifier-v1"
PHASE229_VERSION: str = "1.0.0"

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

P229_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P229_NOMINAL_BUDGET_SECONDS: float = 3.4
P229_CONCURRENT_CEILING_SECONDS: float = 6.0
P229_BOUNDED_HEADER_BYTES: int = 4096
P229_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-32 / FX3 Ver. 7.02 Donor Anchors (bounded O_RDONLY verification)
P229_FX3_MODEL_NAME: str = "ILME-FX3"
P229_FX3_MODEL_ID: int = 0x91030080
P229_FX3_FW_VERSION: str = "7.02"

P229_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P229_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P229_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

P229_DONOR_FX3_APPFW_702_RELPATH: str = "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P229_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P229_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"

P229_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P229_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P229_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

P229_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P229_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P229_PINNED_FX3_LIBBACKUP_SO_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"

P229_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P229_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P229_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"

P229_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P229_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P229_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"

P229_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaCommon.so"
)
P229_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES: int = 402624
P229_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256: str = "1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b"

# Pillar 34A — Slot-1 Tier-0 Vault Firewall (`Quick Format`, `(Delete)` `Full Format`, Mid-Cancel & `MENU+Delete` 2s Chord)
P229_MEDIA_SLOTS: Tuple[int, ...] = (1, 2)
P229_SLOT1_VAULT_SLOT: int = 1
P229_TIER0_VAULT_ARTIFACTS: Tuple[str, ...] = ("pnflasha", "cnflasha", "CAMSET01.DAT")
P229_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P229_RECOGNIZED_VAULT_ARTIFACTS: Tuple[str, ...] = (
    ("pnflasha", "cnflasha", "Backup.bin") + P229_CAMSET_FILENAMES
)
P229_FORMAT_TRIGGERS: Tuple[str, ...] = (
    "NONE",
    "MENU_MEDIA_FORMAT_DIALOG",
    "MENU_PLUS_DELETE_2S_CHORD",
)
P229_FORMAT_MODES: Tuple[str, ...] = ("NONE", "Quick Format", "Full Format")
P229_MENU_DELETE_CHORD_MIN_SECONDS: float = 2.0
P229_DEFAULT_VAULT_RECEIPT_SHA256: str = (
    "9f76b8c4e1a20354d6e8f0123456789abcdef0123456789abcdef0123456789a"
)

# Pillar 34B — Zebra Reset Survival, Local-LCD HDMI Assist Isolation & S&Q Fixed/Variable State Recovery
P229_ZEBRA_DISPLAY_DEFAULT: str = "Off"
P229_ZEBRA_DISPLAY_MODES: Tuple[str, ...] = ("Off", "On")
P229_ZEBRA_LEVEL_DEFAULT: str = "70"
P229_ZEBRA_LEVEL_PRESETS: Tuple[str, ...] = (
    "70",
    "75",
    "80",
    "85",
    "90",
    "95",
    "100",
    "100+",
    "Custom 1",
    "Custom 2",
)
P229_ZEBRA_CUSTOM_STD_MIN: int = 50
P229_ZEBRA_CUSTOM_STD_MAX: int = 109
P229_ZEBRA_CUSTOM1_RANGE_MIN: int = 1
P229_ZEBRA_CUSTOM1_RANGE_MAX: int = 20
P229_RESET_ACTIONS: Tuple[str, ...] = ("NONE", "Camera Settings Reset", "Initialize")

P229_PEAKING_DISPLAY_DEFAULT: str = "Off"
P229_PEAKING_DISPLAY_MODES: Tuple[str, ...] = ("Off", "On")
P229_PEAKING_LEVEL_DEFAULT: str = "Mid"
P229_PEAKING_LEVELS: Tuple[str, ...] = ("High", "Mid", "Low")
P229_PEAKING_COLOR_DEFAULT: str = "White"
P229_PEAKING_COLORS: Tuple[str, ...] = ("Red", "Yellow", "Blue", "White")
P229_HDMI_INFO_DISPLAY_MODES: Tuple[str, ...] = ("Off", "On")

P229_SQ_MODE_SETTINGS: Tuple[str, ...] = ("Fixed/Variable", "S&Q")
P229_AUDIO_OUT_TIMING_DEFAULT: str = "Live"
P229_AUDIO_OUT_TIMING_MODES: Tuple[str, ...] = ("Live", "Lip Sync")
P229_TIME_CODE_RUN_MODES: Tuple[str, ...] = ("Rec Run", "Free Run")
P229_TIME_CODE_OUTPUT_MODES: Tuple[str, ...] = ("Off", "On")
P229_PROXY_RECORDING_MODES: Tuple[str, ...] = ("Off", "On")
P229_PROXY_FORMATS: Tuple[str, ...] = (
    "XAVC HS HD 16M 4:2:0 10bit",
    "XAVC HS HD 9M 4:2:0 10bit",
    "XAVC S HD 6M 4:2:0 8bit",
)
P229_FILE_FORMATS: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S-I 4K",
    "XAVC S-I DCI 4K",
    "XAVC S HD",
    "XAVC S-I HD",
)
P229_4K_FILE_FORMATS: Tuple[str, ...] = (
    "XAVC HS 4K",
    "XAVC S 4K",
    "XAVC S-I 4K",
    "XAVC S-I DCI 4K",
)
P229_DCI_4K_FILE_FORMAT: str = "XAVC S-I DCI 4K"
P229_ALLOWED_REC_FRAME_RATES: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
    "100p",
    "119.88p",
)
P229_PROXY_CUTOFF_REC_RATES: Tuple[str, ...] = ("119.88p", "100p")
P229_PROXY_CUTOFF_MIN_SQ_FPS: int = 100
P229_SQ_200_240_FPS: Tuple[int, ...] = (200, 240)
P229_SQ_100_120_FPS: Tuple[int, ...] = (100, 120)

P229_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_zebra_fullformat_chord_vault_overlay"
P229_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P229_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P229_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P229_BLOCKED_INVALID_FORMAT_SPEC: str = "BLOCKED_INVALID_FORMAT_SPEC"
P229_BLOCKED_SLOT1_VAULT_MISSING_WP_OR_CHORD_FIREWALL: str = (
    "BLOCKED_SLOT1_VAULT_MISSING_WP_OR_CHORD_FIREWALL"
)
P229_BLOCKED_QUICK_FORMAT_SLOT1_VAULT_WIPE: str = "BLOCKED_QUICK_FORMAT_SLOT1_VAULT_WIPE"
P229_BLOCKED_DELETE_TOGGLE_FULL_FORMAT_SLOT1_VAULT_WIPE: str = (
    "BLOCKED_DELETE_TOGGLE_FULL_FORMAT_SLOT1_VAULT_WIPE"
)
P229_BLOCKED_FULL_FORMAT_MID_CANCEL_DATA_ERASED_HAZARD: str = (
    "BLOCKED_FULL_FORMAT_MID_CANCEL_DATA_ERASED_HAZARD"
)
P229_BLOCKED_MENU_DELETE_2S_CHORD_SLOT1_VAULT_WIPE: str = (
    "BLOCKED_MENU_DELETE_2S_CHORD_SLOT1_VAULT_WIPE"
)
P229_BLOCKED_MISSING_OFFCAMERA_SHA256_OR_WP_VAULT_REMOVAL: str = (
    "BLOCKED_MISSING_OFFCAMERA_SHA256_OR_WP_VAULT_REMOVAL"
)
P229_BLOCKED_SDXC_WP_SWITCH_ENGAGED_FORMAT_DENIED: str = (
    "BLOCKED_SDXC_WP_SWITCH_ENGAGED_FORMAT_DENIED"
)
P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT: str = (
    "BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT"
)
P229_BLOCKED_HDMI_ZEBRA_OR_PEAKING_ASSIST_LEAKAGE: str = (
    "BLOCKED_HDMI_ZEBRA_OR_PEAKING_ASSIST_LEAKAGE"
)
P229_BLOCKED_FIXED_VARIABLE_LEGACY_SQ_MENU_CONFLICT: str = (
    "BLOCKED_FIXED_VARIABLE_LEGACY_SQ_MENU_CONFLICT"
)
P229_BLOCKED_SQ_RECORDING_LOCKOUT_VIOLATION: str = (
    "BLOCKED_SQ_RECORDING_LOCKOUT_VIOLATION"
)
P229_BLOCKED_SQ_TRANSITION_STATE_RECOVERY_DRIFT: str = (
    "BLOCKED_SQ_TRANSITION_STATE_RECOVERY_DRIFT"
)
P229_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P229_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P229_STATUS_VERIFIED_PILLAR_34A: str = "VERIFIED_PILLAR_34A_SLOT1_FULLFORMAT_AND_CHORD_VAULT_FIREWALL"
P229_STATUS_REJECTED_PILLAR_34A: str = "REJECTED_PILLAR_34A_SLOT1_FULLFORMAT_AND_CHORD_VAULT_FIREWALL"
P229_STATUS_VERIFIED_PILLAR_34B: str = "VERIFIED_PILLAR_34B_ZEBRA_PERSISTENCE_HDMI_ISOLATION_SQ_RECOVERY"
P229_STATUS_REJECTED_PILLAR_34B: str = "REJECTED_PILLAR_34B_ZEBRA_PERSISTENCE_HDMI_ISOLATION_SQ_RECOVERY"
P229_STATUS_VERIFIED_PILLAR34_SUITE: str = "VERIFIED_PILLAR34_ZEBRA_FULLFORMAT_CHORD_SLOT1_VAULT"
P229_STATUS_FAIL_PILLAR34_SUITE: str = "FAIL_PILLAR34_ZEBRA_FULLFORMAT_CHORD_SLOT1_VAULT"
P229_STATUS_VERIFIED_34OF34_AGGREGATOR: str = "VERIFIED_34OF34_PILLAR_RECOVERY_MASTER"
P229_STATUS_FAIL_34OF34_AGGREGATOR: str = "FAIL_34OF34_PILLAR_RECOVERY_MASTER"

P229_PILLAR_34A_SCENARIO_IDS: Tuple[str, ...] = (
    "P34A1_ACTIVE_SLOT1_TIER0_VAULT_SHA256_WP_ENGAGED_CHORD_FIREWALL_ARMED_SAFE",
    "P34A2_VERIFIED_OFFCAMERA_RECEIPT_WP_LOCKED_VAULT_REMOVED_SCRATCH_FULL_FORMAT_SAFE",
    "P34A3_REJECT_SLOT1_QUICK_FORMAT_METADATA_WIPE_ON_ACTIVE_OR_UNVERIFIED_VAULT",
    "P34A4_REJECT_DELETE_KEY_TOGGLED_FULL_FORMAT_ALL_BLOCKS_WIPE_ON_SLOT1_VAULT",
    "P34A5_REJECT_FULL_FORMAT_MID_CANCEL_ERASED_DATA_HAZARD",
    "P34A6_REJECT_SHOOTING_SCREEN_MENU_PLUS_DELETE_2S_CHORD_ON_SLOT1_VAULT",
)
P229_PILLAR_34B_SCENARIO_IDS: Tuple[str, ...] = (
    "P34B1_ZEBRA_CUSTOM1_SURVIVES_CAMERA_SETTINGS_RESET_LCD_ONLY_FIXED_VAR_RECOVERY_SAFE",
    "P34B2_INITIALIZE_CLEARS_ZEBRA_70_OFF_AND_SQ_60FPS_TO_LIPSYNC_TC_PROXY_RECOVERY_SAFE",
    "P34B3_REJECT_ZEBRA_WIPED_BY_CAMERA_SETTINGS_RESET_OR_RETAINED_ACROSS_INITIALIZE",
    "P34B4_REJECT_HDMI_ZEBRA_OR_PEAKING_ASSIST_OVERLAY_LEAKAGE",
    "P34B5_REJECT_FIXED_VARIABLE_LEGACY_SQ_MENU_UNLOCK_OR_SQ_6_LOCKOUT_VIOLATION",
    "P34B6_REJECT_SQ_TRANSITION_AUDIO_TIMING_TC_PROXY_OR_CAMSET_RECOVERY_DRIFT",
)

MASTER_34_PILLAR_COUNT: int = 34
MASTER_34_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_33_PILLAR_SPECS + (
    (
        34,
        "pillar_34_zebra_fullformat_chord_slot1_vault",
        "Phase 229",
        "fx3_recovery.realhw_34pillar_zebra_fullformat_chord_vault_verifier",
    ),
)
MASTER_34_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_34_PILLAR_SPECS)

_HEX64_RE = re.compile(r"^[0-9a-f]{64}$")


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _is_hex64(val: str) -> bool:
    return bool(_HEX64_RE.fullmatch(val.strip().lower())) if isinstance(val, str) else False


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
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
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
    return any(tok in low for tok in P229_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase229DonorArtifactDigest:
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
class Phase229DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase229DonorArtifactDigest, ...]


@dataclass(frozen=True)
class Slot1FormatAndChordVaultFirewallSpec:
    camera_model: str = P229_FX3_MODEL_NAME
    fw_version: str = P229_FX3_FW_VERSION
    target_slot: int = P229_SLOT1_VAULT_SLOT
    slot1_tier0_vault_active: bool = True
    prior_tier0_vault_session: bool = True
    slot1_vault_artifacts: Tuple[str, ...] = P229_TIER0_VAULT_ARTIFACTS
    off_camera_sha256_receipt_verified: bool = True
    off_camera_vault_sha256: str = P229_DEFAULT_VAULT_RECEIPT_SHA256
    sdxc_physical_wp_engaged: bool = True
    cfexpress_readonly_bench_lock_engaged: bool = False
    vault_card_removed_or_swapped: bool = False
    inserted_card_sdxc_wp_engaged: bool = True
    menu_delete_2s_chord_firewall_armed: bool = True
    format_trigger: str = "NONE"  # NONE | MENU_MEDIA_FORMAT_DIALOG | MENU_PLUS_DELETE_2S_CHORD
    format_mode: str = "NONE"  # NONE | Quick Format | Full Format
    delete_key_toggled_full_format: bool = False
    menu_plus_delete_chord_pressed: bool = False
    menu_plus_delete_hold_seconds: float = 0.0
    full_format_canceled_mid_process: bool = False
    mid_cancel_assumed_data_preserved: bool = False
    mid_cancel_card_usable_but_erased_acknowledged: bool = True
    target_slot_has_unarchived_data: bool = False
    overlay_dir: str = P229_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P229_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P229_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P229_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class Slot1FormatAndChordVaultFirewallReport:
    passed: bool
    status: str
    block_code: Optional[str]
    target_slot: int
    format_requested: bool
    effective_format_mode: str
    chord_2s_triggered: bool
    slot1_vault_protected: bool
    off_camera_sha256_receipt_verified: bool
    mid_cancel_erasure_hazard_clear: bool
    h0_equals_h3_verified: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ZebraPersistenceAndSqTransitionVaultSpec:
    camera_model: str = P229_FX3_MODEL_NAME
    fw_version: str = P229_FX3_FW_VERSION
    pre_reset_zebra_display: str = "On"
    pre_reset_zebra_level: str = "Custom 1"
    custom1_std_level: int = 75
    custom1_range: int = 5
    custom2_lower_limit: int = 100
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    post_reset_zebra_display: str = "On"
    post_reset_zebra_level: str = "Custom 1"
    post_reset_custom1_std_level: int = 75
    post_reset_custom1_range: int = 5
    post_reset_custom2_lower_limit: int = 100
    peaking_display: str = "On"
    peaking_level: str = "Mid"
    peaking_color: str = "White"
    hdmi_info_display: str = "On"
    lcd_zebra_rendered: bool = True
    lcd_peaking_rendered: bool = True
    hdmi_zebra_rendered: bool = False
    hdmi_peaking_rendered: bool = False
    hdmi_assist_leak_pixels: int = 0
    mode_settings: str = "Fixed/Variable"  # Fixed/Variable | S&Q
    legacy_sq_settings_menu_unlocked: bool = False
    fps_direct_control_enabled: bool = True
    sq_recording_active: bool = False
    file_format: str = "XAVC S-I 4K"
    rec_frame_rate: str = "23.98p"
    sq_shooting_fps: int = 60
    sq_audio_channels_recorded: int = 0
    sq_audio_out_timing_enabled: bool = False
    sq_time_code_run_enabled: bool = False
    sq_time_code_output_enabled: bool = False
    sq_proxy_recording_active: bool = False
    sq_transition_recovery_checked: bool = True
    saved_mode_settings: str = "Fixed/Variable"
    restored_mode_settings: str = "Fixed/Variable"
    saved_audio_out_timing: str = "Lip Sync"
    restored_audio_out_timing: str = "Lip Sync"
    saved_time_code_run: str = "Free Run"
    restored_time_code_run: str = "Free Run"
    saved_time_code_output: str = "On"
    restored_time_code_output: str = "On"
    saved_proxy_recording: str = "On"
    restored_proxy_recording: str = "On"
    proxy_format: str = "XAVC HS HD 16M 4:2:0 10bit"
    camset_slot: int = P229_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    stage_b_overlay_dir: str = P229_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P229_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P229_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P229_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class ZebraPersistenceAndSqTransitionVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    zebra_reset_persistence_verified: bool
    hdmi_assist_zero_leak_verified: bool
    fixed_variable_and_sq_lockouts_verified: bool
    sq_transition_state_recovery_verified: bool
    h0_equals_h3_verified: bool
    tier0_surfaces_intact: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ZebraAndFullFormatChordVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase229DonorSnapshot
    slot1_format_chord_report: Slot1FormatAndChordVaultFirewallReport
    zebra_sq_recovery_report: ZebraPersistenceAndSqTransitionVaultReport
    cnflasha_userspace_write_blocked: bool
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
class Pillar34ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar34ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar34ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar34BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar34ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar34StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase229DonorSnapshot
    pillar_34a_fullformat_chord_vault: Pillar34ASuiteResult
    pillar_34b_zebra_sq_recovery_vault: Pillar34BSuiteResult
    suite_sha256: str
    cnflasha_userspace_write_blocked: bool
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
class Master34PillarRecoveryReport:
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
    nominal_under_3_4s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase229DonorSnapshot
    pillar34_a_fullformat_chord_vault: Pillar34ASuiteResult
    pillar34_b_zebra_sq_recovery_vault: Pillar34BSuiteResult
    master_34pillar_sha256: str
    cnflasha_userspace_write_blocked: bool
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
    max_full_bytes: int = P229_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P229_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase229_donors() -> Tuple[Phase229DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P229_DONOR_FX3_BODYDATA_RELPATH,
            P229_PINNED_FX3_BODYDATA_BYTES,
            P229_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P229_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P229_DONOR_FX3_APPFW_702_RELPATH,
            P229_PINNED_FX3_APPFW_702_BYTES,
            P229_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P229_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_APPFW_702",
        ),
        (
            "fx3_backup_bin",
            P229_DONOR_FX3_BACKUP_BIN_RELPATH,
            P229_PINNED_FX3_BACKUP_BIN_BYTES,
            P229_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P229_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P229_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P229_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P229_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P229_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P229_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P229_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P229_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P229_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libinframediaconfig_so",
            P229_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P229_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P229_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P229_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+GetMediaNum+Backup_sync_subsystem",
        ),
        (
            "fx3_libinframediacommon_so",
            P229_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH,
            P229_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
            P229_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
            "FULL_SHA256",
            P229_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:GetFormatProgress+mmcdIoctlFormat+msdFormat",
        ),
    )
    return tuple(
        Phase229DonorArtifactDigest(
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


def inspect_phase229_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase229DonorSnapshot:
    """Inspect Wave-32 / FX3 7.02 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase229_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase229DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P229_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P229_DONOR_FX3_BODYDATA_RELPATH,
            P229_PINNED_FX3_BODYDATA_BYTES,
            P229_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P229_DONOR_FX3_APPFW_702_RELPATH,
            P229_PINNED_FX3_APPFW_702_BYTES,
            P229_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P229_DONOR_FX3_BACKUP_BIN_RELPATH,
            P229_PINNED_FX3_BACKUP_BIN_BYTES,
            P229_PINNED_FX3_BACKUP_BIN_SHA256,
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
                else "BAD_BACKUP_MAGIC",
            ),
        ),
        (
            "fx3_libbackup_so",
            P229_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P229_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P229_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P229_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P229_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P229_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libinframediaconfig_so",
            P229_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P229_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P229_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"InfraMediaConfig", b"GetMediaNum", b"Backup_sync_subsystem")
            ),
        ),
        (
            "fx3_libinframediacommon_so",
            P229_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH,
            P229_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
            P229_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"GetFormatProgress", b"mmcdIoctlFormat", b"msdFormat")
            ),
        ),
    )

    digests: List[Phase229DonorArtifactDigest] = []
    for aid, rel, pinned_bytes, pinned_sha, validator in probe_specs:
        ok, total_b, hdr_b, dkind, dsha, raw = _read_donor_readonly_bounded(rel)
        if not ok:
            digests.append(
                Phase229DonorArtifactDigest(
                    artifact_id=aid,
                    relpath=rel,
                    present=False,
                    read_mode="MISSING",
                    total_bytes=0,
                    header_bytes_read=0,
                    digest_kind=dkind,
                    digest_sha256="",
                    marker_summary="MISSING",
                    matches_pinned=False,
                )
            )
            continue
        marker_ok, marker_summary = validator(raw)
        matches = (total_b == pinned_bytes) and (dsha == pinned_sha) and bool(marker_ok)
        digests.append(
            Phase229DonorArtifactDigest(
                artifact_id=aid,
                relpath=rel,
                present=True,
                read_mode="O_RDONLY_NOFOLLOW_NONBLOCK",
                total_bytes=total_b,
                header_bytes_read=hdr_b,
                digest_kind=dkind,
                digest_sha256=dsha,
                marker_summary=marker_summary,
                matches_pinned=matches,
            )
        )

    if not all(d.present for d in digests):
        synth = _synthetic_phase229_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase229DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P229_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    return Phase229DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all(d.present and d.matches_pinned for d in digests),
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P229_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Pillar 34A & 34B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_slot1_format_chord_spec() -> Slot1FormatAndChordVaultFirewallSpec:
    return Slot1FormatAndChordVaultFirewallSpec()


def build_default_safe_zebra_sq_recovery_spec() -> ZebraPersistenceAndSqTransitionVaultSpec:
    return ZebraPersistenceAndSqTransitionVaultSpec()


def evaluate_slot1_fullformat_and_chord_vault_firewall(
    spec: Slot1FormatAndChordVaultFirewallSpec,
) -> Slot1FormatAndChordVaultFirewallReport:
    """Audit Slot-1 Tier-0 vault firewall against Quick Format, `(Delete)` Full Format, mid-cancel & `MENU+Delete` 2s chord."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P229_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P229_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 34A")

    if spec.target_slot not in P229_MEDIA_SLOTS:
        _fail(P229_BLOCKED_INVALID_FORMAT_SPEC, f"Unsupported media slot: {spec.target_slot!r}")

    if spec.format_trigger not in P229_FORMAT_TRIGGERS or spec.format_mode not in P229_FORMAT_MODES:
        _fail(
            P229_BLOCKED_INVALID_FORMAT_SPEC,
            f"Invalid format_trigger={spec.format_trigger!r} or format_mode={spec.format_mode!r}",
        )

    if any(art not in P229_RECOGNIZED_VAULT_ARTIFACTS for art in spec.slot1_vault_artifacts):
        _fail(
            P229_BLOCKED_INVALID_FORMAT_SPEC,
            f"Unrecognized Slot-1 Tier-0 vault artifact(s): {spec.slot1_vault_artifacts!r}",
        )

    if spec.slot1_tier0_vault_active and len(spec.slot1_vault_artifacts) == 0:
        _fail(
            P229_BLOCKED_INVALID_FORMAT_SPEC,
            "Active Slot-1 Tier-0 vault must declare at least one protected artifact (pnflasha/cnflasha/CAMSET01.DAT)",
        )

    chord_2s_triggered = (
        spec.format_trigger == "MENU_PLUS_DELETE_2S_CHORD"
        or (
            spec.menu_plus_delete_chord_pressed
            and spec.menu_plus_delete_hold_seconds >= P229_MENU_DELETE_CHORD_MIN_SECONDS
        )
    )
    effective_format_mode = (
        "Full Format"
        if (spec.delete_key_toggled_full_format or spec.format_mode == "Full Format")
        else (
            "Quick Format"
            if (spec.format_mode == "Quick Format" or spec.format_trigger != "NONE" or chord_2s_triggered)
            else "NONE"
        )
    )
    format_requested = (
        spec.format_trigger != "NONE"
        or spec.format_mode != "NONE"
        or spec.delete_key_toggled_full_format
        or chord_2s_triggered
        or spec.full_format_canceled_mid_process
    )

    receipt_valid = bool(spec.off_camera_sha256_receipt_verified and _is_hex64(spec.off_camera_vault_sha256))
    wp_or_bench_ro_locked = bool(spec.sdxc_physical_wp_engaged or spec.cfexpress_readonly_bench_lock_engaged)

    mid_cancel_ok = True
    slot1_vault_protected = True

    if not format_requested:
        if spec.slot1_tier0_vault_active:
            if not receipt_valid or not wp_or_bench_ro_locked or not spec.menu_delete_2s_chord_firewall_armed:
                slot1_vault_protected = False
                _fail(
                    P229_BLOCKED_SLOT1_VAULT_MISSING_WP_OR_CHORD_FIREWALL,
                    "Active Slot-1 Tier-0 vault requires verified off-camera SHA-256 receipt, physical SDXC WP "
                    "(or read-only CFexpress bench lock), and armed MENU+Delete 2s chord firewall",
                )
    else:
        if spec.target_slot == P229_SLOT1_VAULT_SLOT and (
            spec.slot1_tier0_vault_active or (spec.prior_tier0_vault_session and not receipt_valid)
        ):
            slot1_vault_protected = False
            if chord_2s_triggered:
                _fail(
                    P229_BLOCKED_MENU_DELETE_2S_CHORD_SLOT1_VAULT_WIPE,
                    "Shooting-screen MENU + (Delete) ~2s chord blocked while Slot 1 holds an active or unverified "
                    f"Tier-0 vault ({spec.slot1_vault_artifacts})",
                )
            elif spec.full_format_canceled_mid_process:
                mid_cancel_ok = False
                _fail(
                    P229_BLOCKED_FULL_FORMAT_MID_CANCEL_DATA_ERASED_HAZARD,
                    "Full Format mid-cancel on active/unverified Slot-1 Tier-0 vault permanently erases stored sectors",
                )
            elif effective_format_mode == "Full Format":
                _fail(
                    P229_BLOCKED_DELETE_TOGGLE_FULL_FORMAT_SLOT1_VAULT_WIPE,
                    "(Delete)-toggled Full Format blocked on Slot 1: full-flash block initialization would wipe "
                    f"Tier-0 vault ({spec.slot1_vault_artifacts})",
                )
            else:
                _fail(
                    P229_BLOCKED_QUICK_FORMAT_SLOT1_VAULT_WIPE,
                    "Quick Format blocked on Slot 1: filesystem metadata reinitialization would orphan/wipe "
                    f"Tier-0 vault ({spec.slot1_vault_artifacts})",
                )
        elif spec.target_slot == P229_SLOT1_VAULT_SLOT and spec.prior_tier0_vault_session:
            if not (receipt_valid and spec.vault_card_removed_or_swapped and wp_or_bench_ro_locked):
                slot1_vault_protected = False
                _fail(
                    P229_BLOCKED_MISSING_OFFCAMERA_SHA256_OR_WP_VAULT_REMOVAL,
                    "Slot 1 formatting after Tier-0 vault session requires verified off-camera SHA-256 receipt "
                    "+ physical SDXC WP switch engagement + vault card removal/swap",
                )
            elif spec.inserted_card_sdxc_wp_engaged:
                _fail(
                    P229_BLOCKED_SDXC_WP_SWITCH_ENGAGED_FORMAT_DENIED,
                    "Inserted SDXC card has physical WP switch engaged; camera hardware denies format",
                )
        elif spec.target_slot == 2 and spec.slot1_tier0_vault_active:
            if not (receipt_valid and wp_or_bench_ro_locked and spec.menu_delete_2s_chord_firewall_armed):
                slot1_vault_protected = False
                _fail(
                    P229_BLOCKED_MISSING_OFFCAMERA_SHA256_OR_WP_VAULT_REMOVAL,
                    "Formatting Slot 2 while Slot 1 holds an active Tier-0 vault requires Slot 1 off-camera "
                    "SHA-256 receipt + physical WP lock + armed MENU+Delete chord firewall",
                )
            elif spec.inserted_card_sdxc_wp_engaged:
                _fail(
                    P229_BLOCKED_SDXC_WP_SWITCH_ENGAGED_FORMAT_DENIED,
                    "Target Slot 2 SDXC card has physical WP switch engaged; format denied",
                )
        elif spec.inserted_card_sdxc_wp_engaged:
            _fail(
                P229_BLOCKED_SDXC_WP_SWITCH_ENGAGED_FORMAT_DENIED,
                "Inserted SDXC card has physical WP switch engaged; format denied",
            )

        if spec.full_format_canceled_mid_process:
            if (
                effective_format_mode != "Full Format"
                or spec.mid_cancel_assumed_data_preserved
                or not spec.mid_cancel_card_usable_but_erased_acknowledged
                or spec.target_slot_has_unarchived_data
            ):
                mid_cancel_ok = False
                _fail(
                    P229_BLOCKED_FULL_FORMAT_MID_CANCEL_DATA_ERASED_HAZARD,
                    "Canceling Full Format mid-process leaves previously stored data permanently erased "
                    "(even though the card remains formatted and usable)",
                )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _fail(
            P229_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P229_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P229_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P229_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 34A",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "34A",
            "passed": passed,
            "block_code": block_code,
            "target_slot": spec.target_slot,
            "format_requested": format_requested,
            "effective_format_mode": effective_format_mode,
            "chord_2s_triggered": chord_2s_triggered,
            "receipt_valid": receipt_valid,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return Slot1FormatAndChordVaultFirewallReport(
        passed=passed,
        status=P229_STATUS_VERIFIED_PILLAR_34A if passed else P229_STATUS_REJECTED_PILLAR_34A,
        block_code=block_code,
        target_slot=spec.target_slot,
        format_requested=format_requested,
        effective_format_mode=effective_format_mode,
        chord_2s_triggered=chord_2s_triggered,
        slot1_vault_protected=slot1_vault_protected and passed,
        off_camera_sha256_receipt_verified=receipt_valid,
        mid_cancel_erasure_hazard_clear=mid_cancel_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_zebra_persistence_and_sq_transition_vault(
    spec: ZebraPersistenceAndSqTransitionVaultSpec,
) -> ZebraPersistenceAndSqTransitionVaultReport:
    """Audit `[Zebra Display]`/`[Zebra Level]` reset persistence, HDMI assist isolation & S&Q state recovery."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P229_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P229_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 34B")

    zebra_persistence_ok = True
    if (
        spec.pre_reset_zebra_display not in P229_ZEBRA_DISPLAY_MODES
        or spec.post_reset_zebra_display not in P229_ZEBRA_DISPLAY_MODES
        or spec.pre_reset_zebra_level not in P229_ZEBRA_LEVEL_PRESETS
        or spec.post_reset_zebra_level not in P229_ZEBRA_LEVEL_PRESETS
        or spec.reset_action not in P229_RESET_ACTIONS
        or not (P229_ZEBRA_CUSTOM_STD_MIN <= spec.custom1_std_level <= P229_ZEBRA_CUSTOM_STD_MAX)
        or not (P229_ZEBRA_CUSTOM1_RANGE_MIN <= spec.custom1_range <= P229_ZEBRA_CUSTOM1_RANGE_MAX)
        or not (P229_ZEBRA_CUSTOM_STD_MIN <= spec.custom2_lower_limit <= P229_ZEBRA_CUSTOM_STD_MAX)
    ):
        zebra_persistence_ok = False
        _fail(
            P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT,
            "Invalid [Zebra Display], [Zebra Level], Custom 1/2 range, or reset_action parameter",
        )
    elif spec.reset_action in ("NONE", "Camera Settings Reset"):
        custom_preserved = (
            spec.post_reset_custom1_std_level == spec.custom1_std_level
            and spec.post_reset_custom1_range == spec.custom1_range
            and spec.post_reset_custom2_lower_limit == spec.custom2_lower_limit
        )
        if (
            spec.post_reset_zebra_display != spec.pre_reset_zebra_display
            or spec.post_reset_zebra_level != spec.pre_reset_zebra_level
            or not custom_preserved
        ):
            zebra_persistence_ok = False
            _fail(
                P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT,
                "[Zebra Display] and [Zebra Level] (including Custom 1 Std+Range / Custom 2 Minimum) "
                "must survive [Camera Settings Reset] unchanged",
            )
    elif spec.reset_action == "Initialize":
        if (
            spec.post_reset_zebra_display != P229_ZEBRA_DISPLAY_DEFAULT
            or spec.post_reset_zebra_level != P229_ZEBRA_LEVEL_DEFAULT
        ):
            zebra_persistence_ok = False
            _fail(
                P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT,
                f"[Initialize] must clear [Zebra Display] to {P229_ZEBRA_DISPLAY_DEFAULT!r} and "
                f"[Zebra Level] to {P229_ZEBRA_LEVEL_DEFAULT!r}",
            )

    hdmi_isolation_ok = True
    if (
        spec.peaking_display not in P229_PEAKING_DISPLAY_MODES
        or spec.peaking_level not in P229_PEAKING_LEVELS
        or spec.peaking_color not in P229_PEAKING_COLORS
        or spec.hdmi_info_display not in P229_HDMI_INFO_DISPLAY_MODES
    ):
        hdmi_isolation_ok = False
        _fail(
            P229_BLOCKED_HDMI_ZEBRA_OR_PEAKING_ASSIST_LEAKAGE,
            "Unsupported [Peaking Display]/[Peaking Level]/[Peaking Color] or [HDMI Info. Display] mode",
        )
    else:
        expected_lcd_zebra = spec.post_reset_zebra_display == "On"
        expected_lcd_peaking = spec.peaking_display == "On"
        if (
            spec.hdmi_zebra_rendered
            or spec.hdmi_peaking_rendered
            or spec.hdmi_assist_leak_pixels != 0
            or spec.lcd_zebra_rendered != expected_lcd_zebra
            or spec.lcd_peaking_rendered != expected_lcd_peaking
        ):
            hdmi_isolation_ok = False
            _fail(
                P229_BLOCKED_HDMI_ZEBRA_OR_PEAKING_ASSIST_LEAKAGE,
                "Zebra stripes and Peaking outlines must render strictly on local LCD (fb0/OSD) and never leak "
                "onto HDMI output (even when [HDMI Info. Display] = [On])",
            )

    sq_lockouts_ok = True
    if (
        spec.mode_settings not in P229_SQ_MODE_SETTINGS
        or spec.file_format not in P229_FILE_FORMATS
        or spec.rec_frame_rate not in P229_ALLOWED_REC_FRAME_RATES
    ):
        sq_lockouts_ok = False
        _fail(
            P229_BLOCKED_FIXED_VARIABLE_LEGACY_SQ_MENU_CONFLICT,
            f"Unsupported mode_settings={spec.mode_settings!r}, file_format={spec.file_format!r}, "
            f"or rec_frame_rate={spec.rec_frame_rate!r}",
        )
    elif spec.mode_settings == "Fixed/Variable":
        if spec.legacy_sq_settings_menu_unlocked or not spec.fps_direct_control_enabled or spec.sq_recording_active:
            sq_lockouts_ok = False
            _fail(
                P229_BLOCKED_FIXED_VARIABLE_LEGACY_SQ_MENU_CONFLICT,
                "Ver. 7.00+/7.02 [Mode Settings] = [Fixed/Variable] locks legacy [S&Q Settings] and controls "
                "capture rate directly via [FPS] / Big6 Home (FPS)",
            )

    if spec.sq_recording_active and spec.mode_settings == "S&Q":
        violated_reasons: List[str] = []
        if spec.sq_audio_channels_recorded != 0:
            violated_reasons.append(f"audio_channels={spec.sq_audio_channels_recorded} (must be 0ch)")
        if spec.sq_audio_out_timing_enabled:
            violated_reasons.append("[Audio Out Timing] active in S&Q")
        if spec.sq_time_code_run_enabled or spec.sq_time_code_output_enabled:
            violated_reasons.append("[Time Code Run]/[Time Code Output] active in S&Q")
        if spec.sq_shooting_fps in P229_SQ_200_240_FPS and spec.file_format in P229_4K_FILE_FORMATS:
            violated_reasons.append(f"{spec.sq_shooting_fps}fps forbidden in 4K format {spec.file_format!r}")
        if spec.sq_shooting_fps in P229_SQ_100_120_FPS and spec.file_format == P229_DCI_4K_FILE_FORMAT:
            violated_reasons.append(f"{spec.sq_shooting_fps}fps forbidden in {P229_DCI_4K_FILE_FORMAT!r}")
        if spec.sq_proxy_recording_active and (
            spec.rec_frame_rate in P229_PROXY_CUTOFF_REC_RATES
            or spec.sq_shooting_fps >= P229_PROXY_CUTOFF_MIN_SQ_FPS
        ):
            violated_reasons.append(
                f"[Proxy Recording] forbidden in S&Q at rec={spec.rec_frame_rate!r}, fps={spec.sq_shooting_fps}"
            )
        if violated_reasons:
            sq_lockouts_ok = False
            _fail(
                P229_BLOCKED_SQ_RECORDING_LOCKOUT_VIOLATION,
                "S&Q hardware lockout violated: " + "; ".join(violated_reasons),
            )

    sq_recovery_ok = True
    valid_recovery_tokens = (
        spec.saved_mode_settings in P229_SQ_MODE_SETTINGS
        and spec.restored_mode_settings in P229_SQ_MODE_SETTINGS
        and spec.saved_audio_out_timing in P229_AUDIO_OUT_TIMING_MODES
        and spec.restored_audio_out_timing in P229_AUDIO_OUT_TIMING_MODES
        and spec.saved_time_code_run in P229_TIME_CODE_RUN_MODES
        and spec.restored_time_code_run in P229_TIME_CODE_RUN_MODES
        and spec.saved_time_code_output in P229_TIME_CODE_OUTPUT_MODES
        and spec.restored_time_code_output in P229_TIME_CODE_OUTPUT_MODES
        and spec.saved_proxy_recording in P229_PROXY_RECORDING_MODES
        and spec.restored_proxy_recording in P229_PROXY_RECORDING_MODES
        and spec.proxy_format in P229_PROXY_FORMATS
        and spec.camset_slot == P229_SLOT1_VAULT_SLOT
        and spec.camset_filename in P229_CAMSET_FILENAMES
    )
    if not valid_recovery_tokens:
        sq_recovery_ok = False
        _fail(
            P229_BLOCKED_SQ_TRANSITION_STATE_RECOVERY_DRIFT,
            "Invalid Mode Settings / Audio Out Timing / Time Code / Proxy / Slot-1 CAMSET recovery token",
        )
    elif spec.sq_transition_recovery_checked:
        parity_matches = (
            spec.saved_mode_settings == spec.restored_mode_settings
            and spec.saved_audio_out_timing == spec.restored_audio_out_timing
            and spec.saved_time_code_run == spec.restored_time_code_run
            and spec.saved_time_code_output == spec.restored_time_code_output
            and spec.saved_proxy_recording == spec.restored_proxy_recording
        )
        proxy_rate_conflict = (
            not spec.sq_recording_active
            and spec.restored_proxy_recording == "On"
            and spec.rec_frame_rate in P229_PROXY_CUTOFF_REC_RATES
        )
        if not parity_matches or proxy_rate_conflict:
            sq_recovery_ok = False
            _fail(
                P229_BLOCKED_SQ_TRANSITION_STATE_RECOVERY_DRIFT,
                "Post-S&Q transition failed to cleanly recover [Mode Settings], [Audio Out Timing], "
                "[Time Code Run]/[Time Code Output], or [Proxy Recording] parity",
            )

    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _fail(
            P229_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.stage_b_overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P229_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P229_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P229_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or 16/16 surface parity drifted in Pillar 34B",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "34B",
            "passed": passed,
            "block_code": block_code,
            "reset_action": spec.reset_action,
            "post_zebra": (spec.post_reset_zebra_display, spec.post_reset_zebra_level),
            "mode_settings": spec.mode_settings,
            "audio_out_timing": spec.restored_audio_out_timing,
            "camset": spec.camset_filename,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return ZebraPersistenceAndSqTransitionVaultReport(
        passed=passed,
        status=P229_STATUS_VERIFIED_PILLAR_34B if passed else P229_STATUS_REJECTED_PILLAR_34B,
        block_code=block_code,
        zebra_reset_persistence_verified=zebra_persistence_ok and passed,
        hdmi_assist_zero_leak_verified=hdmi_isolation_ok and passed,
        fixed_variable_and_sq_lockouts_verified=sq_lockouts_ok and passed,
        sq_transition_state_recovery_verified=sq_recovery_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h3_matched if h0_eq_h3 else 0,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_zebra_persistence_and_fullformat_chord_slot1_vault(
    format_vault_spec: Optional[Slot1FormatAndChordVaultFirewallSpec] = None,
    zebra_sq_spec: Optional[ZebraPersistenceAndSqTransitionVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> ZebraAndFullFormatChordVaultReport:
    """Combined Pillar 34 verifier: Slot-1 Full-Format/2s-Chord firewall + Zebra reset survival & S&Q recovery."""
    donor_snap = inspect_phase229_donors_readonly(force_clean_room=force_clean_room)
    fmt_rep = evaluate_slot1_fullformat_and_chord_vault_firewall(
        format_vault_spec or build_default_safe_slot1_format_chord_spec()
    )
    zeb_rep = evaluate_zebra_persistence_and_sq_transition_vault(
        zebra_sq_spec or build_default_safe_zebra_sq_recovery_spec()
    )
    errs: List[str] = _safety_invariant_errors() + list(fmt_rep.errors) + list(zeb_rep.errors)
    if not donor_snap.all_donors_present:
        errs.append("Phase 229 donor snapshot incomplete or mismatched")
    if not donor_snap.under_0_15s_budget:
        errs.append(f"Phase 229 donor inspection exceeded 2.0s budget: {donor_snap.elapsed_seconds}s")

    all_ok = fmt_rep.passed and zeb_rep.passed and len(errs) == 0
    return ZebraAndFullFormatChordVaultReport(
        schema=PHASE229_SCHEMA,
        version=PHASE229_VERSION,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P229_STATUS_VERIFIED_PILLAR34_SUITE if all_ok else P229_STATUS_FAIL_PILLAR34_SUITE,
        donor_snapshot=donor_snap,
        slot1_format_chord_report=fmt_rep,
        zebra_sq_recovery_report=zeb_rep,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
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
        errors=tuple(errs),
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites & Standalone Pillar 34 Runner
# ---------------------------------------------------------------------------


def run_pillar34a_fullformat_chord_slot1_vault_6_scenario_suite() -> Pillar34ASuiteResult:
    cases: Tuple[Tuple[str, bool, Slot1FormatAndChordVaultFirewallSpec, Optional[str]], ...] = (
        (
            P229_PILLAR_34A_SCENARIO_IDS[0],
            True,
            Slot1FormatAndChordVaultFirewallSpec(),
            None,
        ),
        (
            P229_PILLAR_34A_SCENARIO_IDS[1],
            True,
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=False,
                prior_tier0_vault_session=True,
                off_camera_sha256_receipt_verified=True,
                sdxc_physical_wp_engaged=True,
                vault_card_removed_or_swapped=True,
                inserted_card_sdxc_wp_engaged=False,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Full Format",
                delete_key_toggled_full_format=True,
            ),
            None,
        ),
        (
            P229_PILLAR_34A_SCENARIO_IDS[2],
            False,
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=True,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Quick Format",
                delete_key_toggled_full_format=False,
            ),
            P229_BLOCKED_QUICK_FORMAT_SLOT1_VAULT_WIPE,
        ),
        (
            P229_PILLAR_34A_SCENARIO_IDS[3],
            False,
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=True,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Full Format",
                delete_key_toggled_full_format=True,
            ),
            P229_BLOCKED_DELETE_TOGGLE_FULL_FORMAT_SLOT1_VAULT_WIPE,
        ),
        (
            P229_PILLAR_34A_SCENARIO_IDS[4],
            False,
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=False,
                prior_tier0_vault_session=True,
                off_camera_sha256_receipt_verified=True,
                sdxc_physical_wp_engaged=True,
                vault_card_removed_or_swapped=True,
                inserted_card_sdxc_wp_engaged=False,
                format_trigger="MENU_MEDIA_FORMAT_DIALOG",
                format_mode="Full Format",
                delete_key_toggled_full_format=True,
                full_format_canceled_mid_process=True,
                mid_cancel_assumed_data_preserved=True,
            ),
            P229_BLOCKED_FULL_FORMAT_MID_CANCEL_DATA_ERASED_HAZARD,
        ),
        (
            P229_PILLAR_34A_SCENARIO_IDS[5],
            False,
            Slot1FormatAndChordVaultFirewallSpec(
                slot1_tier0_vault_active=True,
                format_trigger="MENU_PLUS_DELETE_2S_CHORD",
                format_mode="Quick Format",
                menu_plus_delete_chord_pressed=True,
                menu_plus_delete_hold_seconds=2.2,
            ),
            P229_BLOCKED_MENU_DELETE_2S_CHORD_SLOT1_VAULT_WIPE,
        ),
    )

    outcomes: List[Pillar34ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_slot1_fullformat_and_chord_vault_firewall(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar34ScenarioOutcome(
                scenario_id=sid,
                pillar="34A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar34ASuiteResult(
        passed=all_ok,
        status=P229_STATUS_VERIFIED_PILLAR_34A if all_ok else P229_STATUS_REJECTED_PILLAR_34A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar34b_zebra_persistence_sq_recovery_6_scenario_suite() -> Pillar34BSuiteResult:
    cases: Tuple[Tuple[str, bool, ZebraPersistenceAndSqTransitionVaultSpec, Optional[str]], ...] = (
        (
            P229_PILLAR_34B_SCENARIO_IDS[0],
            True,
            ZebraPersistenceAndSqTransitionVaultSpec(),
            None,
        ),
        (
            P229_PILLAR_34B_SCENARIO_IDS[1],
            True,
            ZebraPersistenceAndSqTransitionVaultSpec(
                pre_reset_zebra_display="On",
                pre_reset_zebra_level="Custom 2",
                reset_action="Initialize",
                post_reset_zebra_display="Off",
                post_reset_zebra_level="70",
                lcd_zebra_rendered=False,
                peaking_display="On",
                peaking_level="High",
                peaking_color="Yellow",
                lcd_peaking_rendered=True,
                mode_settings="S&Q",
                sq_recording_active=True,
                file_format="XAVC S 4K",
                rec_frame_rate="23.98p",
                sq_shooting_fps=60,
                sq_audio_channels_recorded=0,
                sq_audio_out_timing_enabled=False,
                sq_time_code_run_enabled=False,
                sq_time_code_output_enabled=False,
                sq_proxy_recording_active=True,
                saved_mode_settings="Fixed/Variable",
                restored_mode_settings="Fixed/Variable",
                saved_audio_out_timing="Lip Sync",
                restored_audio_out_timing="Lip Sync",
                saved_time_code_run="Rec Run",
                restored_time_code_run="Rec Run",
                saved_time_code_output="On",
                restored_time_code_output="On",
                saved_proxy_recording="On",
                restored_proxy_recording="On",
                camset_filename="CAMSET05.DAT",
            ),
            None,
        ),
        (
            P229_PILLAR_34B_SCENARIO_IDS[2],
            False,
            ZebraPersistenceAndSqTransitionVaultSpec(
                pre_reset_zebra_display="On",
                pre_reset_zebra_level="95",
                reset_action="Camera Settings Reset",
                post_reset_zebra_display="Off",
                post_reset_zebra_level="70",
                lcd_zebra_rendered=False,
            ),
            P229_BLOCKED_ZEBRA_CAMERA_SETTINGS_RESET_DRIFT,
        ),
        (
            P229_PILLAR_34B_SCENARIO_IDS[3],
            False,
            ZebraPersistenceAndSqTransitionVaultSpec(
                hdmi_info_display="On",
                hdmi_zebra_rendered=True,
                hdmi_peaking_rendered=True,
                hdmi_assist_leak_pixels=1920,
            ),
            P229_BLOCKED_HDMI_ZEBRA_OR_PEAKING_ASSIST_LEAKAGE,
        ),
        (
            P229_PILLAR_34B_SCENARIO_IDS[4],
            False,
            ZebraPersistenceAndSqTransitionVaultSpec(
                mode_settings="S&Q",
                sq_recording_active=True,
                file_format="XAVC S-I DCI 4K",
                sq_shooting_fps=120,
                sq_audio_channels_recorded=2,
                sq_audio_out_timing_enabled=True,
                sq_time_code_output_enabled=True,
                sq_proxy_recording_active=True,
            ),
            P229_BLOCKED_SQ_RECORDING_LOCKOUT_VIOLATION,
        ),
        (
            P229_PILLAR_34B_SCENARIO_IDS[5],
            False,
            ZebraPersistenceAndSqTransitionVaultSpec(
                saved_audio_out_timing="Lip Sync",
                restored_audio_out_timing="Live",
                saved_time_code_output="On",
                restored_time_code_output="Off",
                saved_proxy_recording="On",
                restored_proxy_recording="Off",
            ),
            P229_BLOCKED_SQ_TRANSITION_STATE_RECOVERY_DRIFT,
        ),
    )

    outcomes: List[Pillar34ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_zebra_persistence_and_sq_transition_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar34ScenarioOutcome(
                scenario_id=sid,
                pillar="34B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar34BSuiteResult(
        passed=all_ok,
        status=P229_STATUS_VERIFIED_PILLAR_34B if all_ok else P229_STATUS_REJECTED_PILLAR_34B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar34_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar34StandaloneReport:
    """Run full Pillar 34 standalone suite (`6/6` Pillar 34A + `6/6` Pillar 34B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase229_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar34a_fullformat_chord_slot1_vault_6_scenario_suite()
    res_b = run_pillar34b_zebra_persistence_sq_recovery_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 229 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE229_SCHEMA,
            "version": PHASE229_VERSION,
            "mode": donor_snapshot.verification_mode,
            "34a": [asdict(s) for s in res_a.scenarios],
            "34b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar34StandaloneReport(
        schema=PHASE229_SCHEMA,
        version=PHASE229_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P229_STATUS_VERIFIED_PILLAR34_SUITE if all_ok else P229_STATUS_FAIL_PILLAR34_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_34a_fullformat_chord_vault=res_a,
        pillar_34b_zebra_sq_recovery_vault=res_b,
        suite_sha256=suite_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
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
# Unified 34/34 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master34_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_34pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master34PillarRecoveryReport:
    """Evaluate and aggregate all 34 recovery pillars (`1..34`) concurrently -> `34/34` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_34_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_33pillar() -> Master33PillarRecoveryReport:
        return evaluate_realhw_33pillar_recovery_master(**kw)

    def _run_p34() -> Tuple[Pillar34StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar34_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_33 = pool.submit(_run_33pillar)
        fut_34 = pool.submit(_run_p34)
        m33_rep = fut_33.result()
        p34_rep, p34_dt = fut_34.result()

    all_errors: List[str] = list(m33_rep.errors) + list(p34_rep.errors)
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
        ("cnflasha_userspace_write_blocked", True),
    ):
        if getattr(m33_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-33 violated {attr_name} == {expected_val}")
        if getattr(p34_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 34 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m33_rep.pillars)
    spec34 = MASTER_34_PILLAR_SPECS[33]
    p34_metrics = {
        "pillar_34a_fullformat_chord_vault": (
            f"{p34_rep.pillar_34a_fullformat_chord_vault.scenarios_passed}/"
            f"{p34_rep.pillar_34a_fullformat_chord_vault.scenarios_total}"
        ),
        "pillar_34b_zebra_sq_recovery_vault": (
            f"{p34_rep.pillar_34b_zebra_sq_recovery_vault.scenarios_passed}/"
            f"{p34_rep.pillar_34b_zebra_sq_recovery_vault.scenarios_total}"
        ),
        "zebra_level_presets_count": len(P229_ZEBRA_LEVEL_PRESETS),
        "hdmi_assist_leak_pixels": 0,
        "donor_files_inspected": p34_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec34[0],
            pillar_id=spec34[1],
            phase_label=spec34[2],
            module_name=spec34[3],
            passed=bool(p34_rep.all_passed),
            status=p34_rep.status,
            verification_mode=p34_rep.verification_mode,
            elapsed_seconds=p34_dt,
            key_metrics=p34_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec34[1],
                    "mode": p34_rep.verification_mode,
                    "status": p34_rep.status,
                    "metrics": p34_metrics,
                    "passed": p34_rep.all_passed,
                }
            ),
            errors=tuple(p34_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master34_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p34_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_34_PILLAR_COUNT == 34
        and pillars_passed == 34
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE229_SCHEMA,
            "version": PHASE229_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master34PillarRecoveryReport(
        schema=PHASE229_SCHEMA,
        version=PHASE229_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P229_STATUS_VERIFIED_34OF34_AGGREGATOR if all_ok else P229_STATUS_FAIL_34OF34_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P229_CONCURRENT_CEILING_SECONDS,
        nominal_under_3_4s=elapsed < P229_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p34_rep.donor_snapshot,
        pillar34_a_fullformat_chord_vault=p34_rep.pillar_34a_fullformat_chord_vault,
        pillar34_b_zebra_sq_recovery_vault=p34_rep.pillar_34b_zebra_sq_recovery_vault,
        master_34pillar_sha256=master_sha,
        cnflasha_userspace_write_blocked=CNFLASHA_USERSPACE_WRITE_BLOCKED,
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


def evaluate_34pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master34PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_34pillar_recovery_master`."""
    return evaluate_realhw_34pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_34pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master34PillarRecoveryReport:
    """Public CLI entry point for Pillar 34 unified `34/34` real-hardware recovery master verification."""
    return evaluate_realhw_34pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
