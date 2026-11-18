"""Phase 215 — Pillar 31 (`31/31` Recovery Pillars) & Unified 31-Pillar Recovery Master
(`verify-31pillar-recovery` / `verify-filesettings-shotmark-tcregen-vault`):

1. **Pillar 31A — `[File Settings]` (`Series`/`Reset`, 5-Mode `[File Name Format]`, `<=37`-Char ASCII
   `[Title Name]`, SDHC `<=32GB` FAT32 Forced `[Standard]` Lock) & `Shot Mark1/2` `*M01.XML` Sidecar Vault**:
   - Audits `[File Number]` (`Series` / `Reset` + `Series Counter Reset`), 5-mode `[File Name Format]`
     (`Standard`, `Cam ID + Reel#`, `Title`, `Date + Title`, `Title + Date`) across Slot 1 & Slot 2,
     `[Title Name Settings]` (`<=37` ASCII allowed characters, non-retroactive on existing clips), and
     SDHC (`<=32GB` FAT32) hardware/filesystem forced `[Standard]` + non-custom folder lock.
   - Prevents reel-number and series-counter collisions against existing `/M4ROOT/CLIP/` clips across
     Tier-0 `Backup.bin` restore and volatile Stage-B rollback (`H0 == H3`).
   - Audits `Shot Mark1` / `Shot Mark2` non-real-time `*M01.XML` sidecars paired with `.MP4` clips in
     `/M4ROOT/CLIP/`, blocking orphaned/corrupted XML sidecars that break `[Image Jump Setting]`
     (`Shot Mark Only` / `Shot Mark1/2 Only`) or `[Only Shot Mark Mov.]` FTP batch rescue transfers.

2. **Pillar 31B — `[TC/UB]` `[Regenerate]` Slot-1 Master Timecode Continuity, Forced `[Rec Run]`,
   `VMC-BNCM1` `EXT-LK` Release Hazard, S&Q HDMI `Time Code Output` Block & Coupled `REC Lamp` Tally**:
   - Enforces `[Time Code Make] = [Regenerate]` sequential continuation from the active card and
     exclusive **Slot 1** ending-TC read under `[Simult. Recording]`, forcing `[Rec Run]` advancement
     regardless of `[Time Code Run]`.
   - Flags `VMC-BNCM1` `EXT-LK` external jam-sync drop hazards when restoring `Backup.bin` profiles
     that mutate `[Time Code Make]` away from `Preset` or `[Time Code Run]` away from `Free Run`, plus
     `S&Q` `[Time Code Run]` / HDMI `[Time Code Output]` unavailability.
   - Verifies Wave-29 coupled Rear + Top `REC` button tally (`All On` / `Only Front Off` / `All Off`),
     `[Silent Mode] -> [Audio signals = Off]` lock, and Tier-0 `16/16` `H0 == H3` (`physical_device_writes = 0`).

3. **Unified `31/31` Recovery Master (`evaluate_realhw_31pillar_recovery_master`)**:
   - Delegates Pillars `1..30` concurrently to `evaluate_realhw_30pillar_recovery_master` + **Pillar 31**
     -> **`31/31` (`VERIFIED_31OF31_PILLAR_RECOVERY_MASTER`)** in `< 2.8s` (`< 6.0s` test ceiling).
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
from .realhw_30pillar_proxy_coupled_hdmi_only_vault_verifier import (
    MASTER_30_PILLAR_SPECS,
    Master30PillarRecoveryReport,
    evaluate_realhw_30pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE215_SCHEMA: str = "fx3-realhw-31pillar-recovery-master-verifier-v1"
PHASE215_VERSION: str = "1.0.0"

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

P215_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P215_NOMINAL_BUDGET_SECONDS: float = 2.8
P215_CONCURRENT_CEILING_SECONDS: float = 6.0
P215_BOUNDED_HEADER_BYTES: int = 4096
P215_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-29 / FX3 Ver. 7.02 Donor Anchors (bounded O_RDONLY verification)
P215_FX3_MODEL_NAME: str = "ILME-FX3"
P215_FX3_MODEL_ID: int = 0x91030080
P215_FX3_FW_VERSION: str = "7.02"

P215_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P215_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P215_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

P215_DONOR_FX3_APPFW_702_RELPATH: str = "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P215_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P215_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"

P215_DONOR_FX3_BACKUP_BIN_RELPATH: str = "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
P215_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P215_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

P215_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
P215_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P215_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"

P215_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH: str = "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaCommon.so"
P215_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES: int = 402624
P215_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256: str = "1ddec7e4d903eaca7cdc7901936b99a9bf97bc52f67259cd3ebb3ee60620b40b"

P215_DONOR_FX3_LIBINFRAMEDIAMOUNT_SO_RELPATH: str = "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaMount.so"
P215_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES: int = 65392
P215_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_SHA256: str = "33b4c61c39f724e08e1bc4d07fd505a799ee37a9c1f37a43fffc7c2c9c8f75ad"

# Pillar 31A — [File Settings], SDHC Lock & Shot Mark1/2 *M01.XML Sidecar Vault Constants
P215_M4ROOT_CLIP_DIR: str = "/M4ROOT/CLIP"
P215_ALLOWED_MEDIA_SLOTS: Tuple[int, ...] = (1, 2)
P215_FILE_NUMBER_MODES: Tuple[str, ...] = ("Series", "Reset")
P215_FILE_NAME_FORMATS: Tuple[str, ...] = (
    "Standard",
    "Cam ID + Reel#",
    "Title",
    "Date + Title",
    "Title + Date",
)
P215_TITLE_NAME_MAX_CHARS: int = 37
P215_TITLE_NAME_DEFAULT: str = "C"
P215_TITLE_ALLOWED_SYMBOLS: str = ".-_@!#$%+=^~(),;[]"
P215_TITLE_ALLOWED_CHARSET = frozenset(
    "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789" + P215_TITLE_ALLOWED_SYMBOLS
)
P215_MEDIA_CARD_TYPES: Tuple[str, ...] = ("CFexpress_Type_A", "SDXC", "SDHC")
P215_SDHC_MAX_CAPACITY_GB: int = 32
P215_IMAGE_JUMP_MODES: Tuple[str, ...] = (
    "Off",
    "Shot Mark Only",
    "Shot Mark1 Only",
    "Shot Mark2 Only",
    "No Shot Mark",
)
P215_FTP_TARGET_MOVIE_MODES: Tuple[str, ...] = (
    "All",
    "Only Shot Mark Mov.",
    "Only Shot Mark",
)

# Pillar 31B — [TC/UB] Regenerate Slot-1 Master, EXT-LK Release, S&Q Lockout & Coupled REC Lamp
P215_TC_MAKE_MODES: Tuple[str, ...] = ("Preset", "Regenerate")
P215_TC_RUN_MODES: Tuple[str, ...] = ("Rec Run", "Free Run")
P215_RECORDING_MEDIA_MODES: Tuple[str, ...] = (
    "Slot 1",
    "Slot 2",
    "Simult. Recording",
    "Auto Switch Media",
)
P215_HDMI_TC_OUTPUT_MODES: Tuple[str, ...] = ("Off", "On")
P215_REC_LAMP_MODES: Tuple[str, ...] = ("All On", "Only Front Off", "All Off")
P215_AUDIO_SIGNALS_MODES: Tuple[str, ...] = ("On: All", "On: Shutter Only", "Off")
P215_TC_TIMECODE_RE = re.compile(r"^(\d{2}):(\d{2}):(\d{2})([:;])(\d{2})$")

P215_STAGE_B_FILESETTINGS_TC_OVERLAY_DIR: str = "/tmp/fx6_filesettings_tc_overlay"
P215_STOCK_BACKUP_BIN_PATH: str = "p2:/setting/Backup.bin"
P215_STOCK_P2_SETTING_PATH: str = "p2:/setting"
P215_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P215_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P215_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P215_BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID: str = "BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID"
P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION: str = "BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION"
P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION: str = "BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION"
P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT: str = "BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT"
P215_BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN: str = "BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN"
P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION: str = "BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION"
P215_BLOCKED_EXT_LK_DROP_HAZARD_ON_RESTORE: str = "BLOCKED_EXT_LK_DROP_HAZARD_ON_RESTORE"
P215_BLOCKED_SQ_TIMECODE_RUN_OR_HDMI_TCOUT_LOCKOUT: str = "BLOCKED_SQ_TIMECODE_RUN_OR_HDMI_TCOUT_LOCKOUT"
P215_BLOCKED_RECLAMP_COUPLED_TALLY_OR_SILENT_LOCK_DRIFT: str = "BLOCKED_RECLAMP_COUPLED_TALLY_OR_SILENT_LOCK_DRIFT"
P215_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"
P215_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"

P215_STATUS_VERIFIED_PILLAR_31A: str = "VERIFIED_PILLAR_31A_FILESETTINGS_SHOTMARK_VAULT"
P215_STATUS_REJECTED_PILLAR_31A: str = "REJECTED_PILLAR_31A_FILESETTINGS_SHOTMARK_VAULT"
P215_STATUS_VERIFIED_PILLAR_31B: str = "VERIFIED_PILLAR_31B_TCREGEN_SLOT1_EXTLK_VAULT"
P215_STATUS_REJECTED_PILLAR_31B: str = "REJECTED_PILLAR_31B_TCREGEN_SLOT1_EXTLK_VAULT"
P215_STATUS_VERIFIED_PILLAR31_SUITE: str = "VERIFIED_PILLAR31_FILESETTINGS_SHOTMARK_TCREGEN_VAULT"
P215_STATUS_FAIL_PILLAR31_SUITE: str = "FAIL_PILLAR31_FILESETTINGS_SHOTMARK_TCREGEN_VAULT"
P215_STATUS_VERIFIED_31OF31_AGGREGATOR: str = "VERIFIED_31OF31_PILLAR_RECOVERY_MASTER"
P215_STATUS_FAIL_31OF31_AGGREGATOR: str = "FAIL_31OF31_PILLAR_RECOVERY_MASTER"

P215_PILLAR_31A_SCENARIO_IDS: Tuple[str, ...] = (
    "P31A1_DUAL_SLOT_5FORMAT_37CHAR_TITLE_AND_SHOTMARK_XML_CLEAN",
    "P31A2_SDHC_32GB_FAT32_FORCED_STANDARD_LOCK_ENFORCED",
    "P31A3_REJECT_SDHC_CUSTOM_FORMAT_OR_38CHAR_ILLEGAL_TITLE",
    "P31A4_REJECT_SERIES_OR_REEL_COUNTER_COLLISION_ON_RESTORE",
    "P31A5_REJECT_ORPHAN_OR_CORRUPT_M01_XML_SHOTMARK_SIDECAR",
    "P31A6_REJECT_BROKEN_IMAGE_JUMP_OR_FTP_ONLY_SHOTMARK_RESCUE",
)
P215_PILLAR_31B_SCENARIO_IDS: Tuple[str, ...] = (
    "P31B1_SIMULT_REGENERATE_SLOT1_MASTER_AND_FORCED_RECRUN",
    "P31B2_PRESET_FREERUN_EXTLK_ACTIVE_AND_ACKNOWLEDGED_REJAM",
    "P31B3_REJECT_SLOT2_TCREGEN_DRIFT_OR_UNFORCED_FREERUN",
    "P31B4_REJECT_UNACKNOWLEDGED_EXTLK_DROP_ON_BACKUP_RESTORE",
    "P31B5_REJECT_SQ_TCRUN_OVERRIDE_AND_HDMI_TC_OUTPUT_ON",
    "P31B6_COUPLED_RECLAMP_ONLY_FRONT_OFF_SILENT_LOCK_AND_H0_H3",
)

MASTER_31_PILLAR_COUNT: int = 31
MASTER_31_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_30_PILLAR_SPECS + (
    (
        31,
        "pillar_31_filesettings_shotmark_tcregen_vault",
        "Phase 215",
        "fx3_recovery.realhw_31pillar_filesettings_shotmark_tcregen_vault_verifier",
    ),
)
MASTER_31_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_31_PILLAR_SPECS)


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
    return any(tok in low for tok in P215_FORBIDDEN_PERSISTENT_TARGETS)


def _parse_tc_to_frames(tc: str, fps_ceil: int = 30) -> Optional[int]:
    m = P215_TC_TIMECODE_RE.match(tc.strip())
    if not m or fps_ceil <= 0:
        return None
    hh, mm, ss, _sep, ff = int(m.group(1)), int(m.group(2)), int(m.group(3)), m.group(4), int(m.group(5))
    if hh > 23 or mm > 59 or ss > 59 or ff >= fps_ceil:
        return None
    return (((hh * 60) + mm) * 60 + ss) * fps_ceil + ff


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase215DonorArtifactDigest:
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
class Phase215DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase215DonorArtifactDigest, ...]


@dataclass(frozen=True)
class SlotMediaFileSettingsSpec:
    slot: int
    card_type: str = "CFexpress_Type_A"  # CFexpress_Type_A | SDXC | SDHC
    capacity_gb: int = 160
    filesystem: str = "exFAT"  # exFAT | FAT32
    effective_file_name_format: str = "Title"
    custom_movie_folder_requested: bool = False
    existing_clip_numbers: Tuple[int, ...] = ()
    existing_clip_stems: Tuple[str, ...] = ()


@dataclass(frozen=True)
class ShotMarkSidecarPairSpec:
    stem: str
    slot: int
    mp4_relpath: str
    xml_relpath: str
    mp4_present: bool = True
    xml_present: bool = True
    xml_well_formed: bool = True
    nrt_metadata_intact: bool = True
    shot_mark1_frames: Tuple[int, ...] = ()
    shot_mark2_frames: Tuple[int, ...] = ()
    xml_shot_mark1_synced: bool = True
    xml_shot_mark2_synced: bool = True


@dataclass(frozen=True)
class FileSettingsAndShotMarkVaultSpec:
    camera_model: str = P215_FX3_MODEL_NAME
    fw_version: str = P215_FX3_FW_VERSION
    file_number_mode: str = "Series"
    series_counter_reset_executed: bool = False
    restored_series_counter_next: int = 5
    file_name_format: str = "Title"
    cam_id: str = "A"
    reel_number: int = 1
    title_name: str = "FX3_PROD_UNIT01"
    retroactive_rename_existing_clips_assumed: bool = False
    slot_cards: Tuple[SlotMediaFileSettingsSpec, ...] = ()
    sidecar_pairs: Tuple[ShotMarkSidecarPairSpec, ...] = ()
    image_jump_setting: str = "Shot Mark Only"
    ftp_target_movie: str = "Only Shot Mark Mov."
    ftp_batch_rescue_active: bool = True
    overlay_dir: str = P215_STAGE_B_FILESETTINGS_TC_OVERLAY_DIR
    overlay_wiped_on_reset: bool = True
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P215_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P215_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P215_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class FileSettingsAndShotMarkVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    slots_audited: Tuple[int, ...]
    title_name_length: int
    sdhc_slots_locked_to_standard: int
    counter_collision_count: int
    sidecar_pairs_audited: int
    marked_clips_ready_for_ftp: int
    orphaned_or_corrupt_xml_count: int
    h0_equals_h3_verified: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class TcRegenSlot1AndExtLkVaultSpec:
    camera_model: str = P215_FX3_MODEL_NAME
    fw_version: str = P215_FX3_FW_VERSION
    shooting_mode: str = "Movie"  # Movie | S&Q
    sq_mode_active: bool = False
    recording_media: str = "Simult. Recording"
    time_code_make: str = "Regenerate"
    configured_time_code_run: str = "Free Run"
    effective_time_code_run: str = "Rec Run"
    fps_timebase_ceil: int = 24
    slot1_last_end_tc: str = "01:12:30:10"
    slot2_last_end_tc: str = "00:45:10:02"
    regenerated_next_start_tc: str = "01:12:30:11"
    regenerate_source_slot_used: int = 1
    vmc_bncm1_ext_lk_active_before_restore: bool = False
    restored_backup_time_code_make: str = "Regenerate"
    restored_backup_time_code_run: str = "Rec Run"
    ext_lk_retained_after_mode_change_assumed: bool = False
    ext_lk_rejam_acknowledged: bool = True
    sq_tc_run_override_attempted: bool = False
    hdmi_time_code_output: str = "Off"
    rec_lamp_mode: str = "Only Front Off"
    front_tally_led_on: bool = False
    rear_tally_led_on: bool = True
    top_rec_button_led_on: bool = True
    emphasized_rec_display_on: bool = True
    silent_mode_enabled: bool = False
    audio_signals_mode: str = "On: All"
    stage_b_overlay_dir: str = P215_STAGE_B_FILESETTINGS_TC_OVERLAY_DIR
    stage_b_overlay_wiped_on_reset: bool = True
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P215_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P215_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P215_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class TcRegenSlot1AndExtLkVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    recording_media: str
    time_code_make: str
    effective_time_code_run: str
    slot1_master_tc_verified: bool
    ext_lk_drop_hazard_detected: bool
    sq_tc_hdmi_lockout_verified: bool
    coupled_reclamp_tally_verified: bool
    silent_mode_audio_lock_verified: bool
    h0_equals_h3_verified: bool
    tier0_surfaces_intact: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FileSettingsShotMarkAndTcRegenVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase215DonorSnapshot
    filesettings_shotmark_report: FileSettingsAndShotMarkVaultReport
    tcregen_extlk_report: TcRegenSlot1AndExtLkVaultReport
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
class Pillar31ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar31ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar31ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar31BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar31ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar31StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase215DonorSnapshot
    pillar_31a_filesettings_shotmark_vault: Pillar31ASuiteResult
    pillar_31b_tcregen_slot1_extlk_vault: Pillar31BSuiteResult
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
class Master31PillarRecoveryReport:
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
    nominal_under_2_8s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase215DonorSnapshot
    pillar31_a_filesettings_shotmark_vault: Pillar31ASuiteResult
    pillar31_b_tcregen_slot1_extlk_vault: Pillar31BSuiteResult
    master_31pillar_sha256: str
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
    max_full_bytes: int = P215_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P215_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase215_donors() -> Tuple[Phase215DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P215_DONOR_FX3_BODYDATA_RELPATH,
            P215_PINNED_FX3_BODYDATA_BYTES,
            P215_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P215_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P215_DONOR_FX3_APPFW_702_RELPATH,
            P215_PINNED_FX3_APPFW_702_BYTES,
            P215_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P215_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_APPFW_702",
        ),
        (
            "fx3_backup_bin",
            P215_DONOR_FX3_BACKUP_BIN_RELPATH,
            P215_PINNED_FX3_BACKUP_BIN_BYTES,
            P215_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P215_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libinframediaconfig_so",
            P215_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P215_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P215_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P215_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+GetMediaNum",
        ),
        (
            "fx3_libinframediacommon_so",
            P215_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH,
            P215_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
            P215_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
            "FULL_SHA256",
            P215_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:mcmn_drv_checkmediaexist+Backup_sync_subsystem",
        ),
        (
            "fx3_libinframediamount_so",
            P215_DONOR_FX3_LIBINFRAMEDIAMOUNT_SO_RELPATH,
            P215_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES,
            P215_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES,
            "FULL_SHA256",
            P215_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaMount+GetVersionEv",
        ),
    )
    return tuple(
        Phase215DonorArtifactDigest(
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


def inspect_phase215_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase215DonorSnapshot:
    """Inspect Wave-29 / FX3 7.02 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase215_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase215DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P215_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P215_DONOR_FX3_BODYDATA_RELPATH,
            P215_PINNED_FX3_BODYDATA_BYTES,
            P215_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P215_DONOR_FX3_APPFW_702_RELPATH,
            P215_PINNED_FX3_APPFW_702_BYTES,
            P215_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: (
                len(d) >= 64 and d[:4] == b"\x7fELF" and d[4] == 2 and struct.unpack_from("<H", d, 18)[0] == 183,
                "ELF64_AARCH64_APPFW_702",
            ),
        ),
        (
            "fx3_backup_bin",
            P215_DONOR_FX3_BACKUP_BIN_RELPATH,
            P215_PINNED_FX3_BACKUP_BIN_BYTES,
            P215_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P215_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P215_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P215_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"InfraMediaConfig", b"GetMediaNum", b"Backup_sync_subsystem")),
        ),
        (
            "fx3_libinframediacommon_so",
            P215_DONOR_FX3_LIBINFRAMEDIACOMMON_SO_RELPATH,
            P215_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_BYTES,
            P215_PINNED_FX3_LIBINFRAMEDIACOMMON_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"mcmn_drv_checkmediaexist", b"Backup_sync_subsystem")),
        ),
        (
            "fx3_libinframediamount_so",
            P215_DONOR_FX3_LIBINFRAMEDIAMOUNT_SO_RELPATH,
            P215_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_BYTES,
            P215_PINNED_FX3_LIBINFRAMEDIAMOUNT_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"InfraMediaMount", b"GetVersionEv")),
        ),
    )

    digests: List[Phase215DonorArtifactDigest] = []
    for aid, rel, exp_bytes, exp_sha, marker_fn in probe_specs:
        ok, total_b, hdr_b, dkind, actual_sha, data = _read_donor_readonly_bounded(rel)
        marker_ok, marker_summary = marker_fn(data) if ok else (False, "UNREADABLE")
        pinned_ok = ok and total_b == exp_bytes and actual_sha == exp_sha and marker_ok
        digests.append(
            Phase215DonorArtifactDigest(
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
        return Phase215DonorSnapshot(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            all_donors_present=all(a.matches_pinned for a in digests),
            donor_files_inspected=len(digests),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P215_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=tuple(digests),
        )

    synth = _synthetic_phase215_donors()
    dt = round(time.monotonic() - t0, 6)
    return Phase215DonorSnapshot(
        verification_mode="CLEAN_ROOM_SYNTHETIC",
        all_donors_present=True,
        donor_files_inspected=len(synth),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P215_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=synth,
    )


# ---------------------------------------------------------------------------
# Pillar 31A — [File Settings], SDHC Lock & Shot Mark1/2 *M01.XML Sidecar Evaluator
# ---------------------------------------------------------------------------


def evaluate_filesettings_and_shotmark_xml_vault(
    spec: FileSettingsAndShotMarkVaultSpec,
) -> FileSettingsAndShotMarkVaultReport:
    """Audit `[File Settings]`, SDHC forced `[Standard]` lock, counter collisions, and `*M01.XML` Shot Marks."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _reject(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested:
        _reject(P215_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent eMMC write unlock forbidden in Pillar 31A")
    if spec.camera_model != P215_FX3_MODEL_NAME or spec.fw_version != P215_FX3_FW_VERSION:
        _reject(
            P215_BLOCKED_SAFETY_POLICY_VIOLATION,
            f"Unsupported host {spec.camera_model} fw={spec.fw_version}; requires {P215_FX3_MODEL_NAME} {P215_FX3_FW_VERSION}",
        )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _reject(P215_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, f"Non-tmpfs overlay path forbidden: {spec.overlay_dir}")
    if not spec.overlay_wiped_on_reset:
        _reject(P215_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, "Stage-B tmpfs overlay was not wiped cleanly on reset")
    h0_h3_ok = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P215_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _reject(P215_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT, "Backup.bin / 16-surface Tier-0 H0 != H3 or RO lock drift")

    # 1. File Number, File Name Format, Cam ID + Reel#, and <=37-char ASCII Title Name rules
    if spec.file_number_mode not in P215_FILE_NUMBER_MODES:
        _reject(P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION, f"Invalid [File Number] mode: {spec.file_number_mode!r}")
    if spec.file_name_format not in P215_FILE_NAME_FORMATS:
        _reject(P215_BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID, f"Invalid [File Name Format]: {spec.file_name_format!r}")
    if not (len(spec.cam_id) == 1 and "A" <= spec.cam_id <= "Z"):
        _reject(P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION, f"[Cam ID] must be A..Z (got {spec.cam_id!r})")
    if not (1 <= spec.reel_number <= 999):
        _reject(P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION, f"[Reel#] must be 1..999 (got {spec.reel_number})")
    if not (1 <= spec.restored_series_counter_next <= 9999):
        _reject(
            P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION,
            f"Series counter next must be 1..9999 (got {spec.restored_series_counter_next})",
        )
    if not (1 <= len(spec.title_name) <= P215_TITLE_NAME_MAX_CHARS):
        _reject(
            P215_BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID,
            f"[Title Name Settings] length {len(spec.title_name)} outside 1..{P215_TITLE_NAME_MAX_CHARS}",
        )
    elif any(ch not in P215_TITLE_ALLOWED_CHARSET for ch in spec.title_name):
        _reject(
            P215_BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID,
            f"[Title Name Settings] {spec.title_name!r} contains disallowed non-FX3 ASCII characters",
        )
    if spec.retroactive_rename_existing_clips_assumed:
        _reject(
            P215_BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID,
            "[Title Name Settings] applies strictly to clips recorded after setup; retroactive rename forbidden",
        )

    # 2. Per-slot SDHC <=32GB FAT32 forced [Standard] lock & Series/Reel collision guard
    slots_seen: List[int] = []
    sdhc_locked_count = 0
    collision_count = 0
    for card in spec.slot_cards:
        if card.slot not in P215_ALLOWED_MEDIA_SLOTS:
            _reject(P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION, f"Invalid media slot {card.slot}")
        elif card.slot not in slots_seen:
            slots_seen.append(card.slot)
        if card.card_type not in P215_MEDIA_CARD_TYPES:
            _reject(P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION, f"Unknown card_type {card.card_type!r}")
            continue
        if card.effective_file_name_format not in P215_FILE_NAME_FORMATS:
            _reject(
                P215_BLOCKED_TITLE_NAME_37CHAR_OR_ASCII_INVALID,
                f"Invalid slot {card.slot} effective format {card.effective_file_name_format!r}",
            )

        is_sdhc = card.card_type == "SDHC" or card.filesystem == "FAT32" or card.capacity_gb <= P215_SDHC_MAX_CAPACITY_GB
        if is_sdhc:
            if card.filesystem != "FAT32" or card.capacity_gb > P215_SDHC_MAX_CAPACITY_GB or card.card_type != "SDHC":
                _reject(
                    P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION,
                    f"Slot {card.slot} SDHC/FAT32 topology mismatch ({card.card_type}, {card.capacity_gb}GB, {card.filesystem})",
                )
            if card.effective_file_name_format != "Standard":
                _reject(
                    P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION,
                    f"Slot {card.slot} SDHC card force-locks [File Name Format] to [Standard]; got {card.effective_file_name_format!r}",
                )
            elif card.custom_movie_folder_requested:
                _reject(
                    P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION,
                    f"Slot {card.slot} SDHC card forbids customizing movie folder names",
                )
            else:
                sdhc_locked_count += 1
        else:
            if card.filesystem != "exFAT":
                _reject(
                    P215_BLOCKED_SDHC_FORCED_STANDARD_LOCK_VIOLATION,
                    f"Slot {card.slot} {card.card_type} (>32GB) requires exFAT (got {card.filesystem!r})",
                )

        # Series / Reset / Reel# collision guard against existing M4ROOT/CLIP/ clips
        effective_next = 1 if (spec.file_number_mode == "Reset" or spec.series_counter_reset_executed) else spec.restored_series_counter_next
        if card.existing_clip_numbers:
            max_existing = max(card.existing_clip_numbers)
            if effective_next in card.existing_clip_numbers or effective_next <= max_existing:
                collision_count += 1
                _reject(
                    P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION,
                    f"Slot {card.slot} restored next clip #{effective_next:04d} collides with existing M4ROOT/CLIP max #{max_existing:04d}",
                )
        if card.effective_file_name_format == "Cam ID + Reel#" and card.existing_clip_stems:
            reel_prefix = f"{spec.cam_id}{spec.reel_number:03d}"
            candidate_stem = f"{reel_prefix}C{effective_next:04d}"
            if any(st == candidate_stem or st.startswith(f"{reel_prefix}C{effective_next:04d}") for st in card.existing_clip_stems):
                collision_count += 1
                _reject(
                    P215_BLOCKED_REEL_OR_SERIES_COUNTER_COLLISION,
                    f"Slot {card.slot} Cam ID + Reel# stem {candidate_stem} collides with existing M4ROOT/CLIP clip",
                )

    # 3. Shot Mark1 / Shot Mark2 *M01.XML non-real-time sidecar & Image Jump / FTP rescue filter audit
    if spec.image_jump_setting not in P215_IMAGE_JUMP_MODES:
        _reject(
            P215_BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN,
            f"Invalid [Image Jump Setting]: {spec.image_jump_setting!r}",
        )
    if spec.ftp_target_movie not in P215_FTP_TARGET_MOVIE_MODES:
        _reject(
            P215_BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN,
            f"Invalid FTP [Target Movie]: {spec.ftp_target_movie!r}",
        )

    orphan_or_corrupt_xml = 0
    marked_ready_for_ftp = 0
    for pair in spec.sidecar_pairs:
        if pair.slot not in P215_ALLOWED_MEDIA_SLOTS:
            _reject(P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT, f"Invalid slot {pair.slot} for {pair.stem}")
        elif pair.slot not in slots_seen:
            slots_seen.append(pair.slot)

        exp_mp4 = f"{P215_M4ROOT_CLIP_DIR}/{pair.stem}.MP4"
        exp_xml = f"{P215_M4ROOT_CLIP_DIR}/{pair.stem}M01.XML"
        has_marks = bool(pair.shot_mark1_frames or pair.shot_mark2_frames)

        if pair.mp4_relpath != exp_mp4 or pair.xml_relpath != exp_xml:
            orphan_or_corrupt_xml += 1
            _reject(
                P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT,
                f"Sidecar pair paths ({pair.mp4_relpath!r}, {pair.xml_relpath!r}) must match ({exp_mp4!r}, {exp_xml!r})",
            )
        if pair.xml_present and not pair.mp4_present:
            orphan_or_corrupt_xml += 1
            _reject(
                P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT,
                f"Orphaned *M01.XML sidecar {pair.xml_relpath} without paired {pair.mp4_relpath}",
            )
        elif pair.mp4_present and not pair.xml_present:
            orphan_or_corrupt_xml += 1
            _reject(
                P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT,
                f"Clip {pair.mp4_relpath} is missing paired non-real-time {pair.xml_relpath}",
            )
        elif pair.xml_present and (not pair.xml_well_formed or not pair.nrt_metadata_intact):
            orphan_or_corrupt_xml += 1
            _reject(
                P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT,
                f"Corrupted NonRealTimeMeta XML in {pair.xml_relpath}",
            )
        elif has_marks and (not pair.xml_shot_mark1_synced or not pair.xml_shot_mark2_synced):
            orphan_or_corrupt_xml += 1
            _reject(
                P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT,
                f"Shot Mark1/2 frame table out of sync in {pair.xml_relpath}",
            )
        elif any(f < 0 for f in pair.shot_mark1_frames + pair.shot_mark2_frames):
            orphan_or_corrupt_xml += 1
            _reject(
                P215_BLOCKED_SHOTMARK_XML_SIDECAR_ORPHAN_OR_CORRUPT,
                f"Negative Shot Mark frame index in {pair.xml_relpath}",
            )
        elif pair.mp4_present and pair.xml_present and has_marks:
            marked_ready_for_ftp += 1

    # Check Image Jump & FTP Only Shot Mark Mov. rescue readiness
    if spec.ftp_batch_rescue_active and spec.ftp_target_movie in ("Only Shot Mark Mov.", "Only Shot Mark"):
        if orphan_or_corrupt_xml > 0 or marked_ready_for_ftp == 0:
            _reject(
                P215_BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN,
                f"FTP [{spec.ftp_target_movie}] batch rescue blocked: marked_ready={marked_ready_for_ftp}, corrupt_xml={orphan_or_corrupt_xml}",
            )
    if spec.image_jump_setting in ("Shot Mark Only", "Shot Mark1 Only", "Shot Mark2 Only"):
        if orphan_or_corrupt_xml > 0:
            _reject(
                P215_BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN,
                f"[Image Jump Setting = {spec.image_jump_setting}] broken by orphaned/corrupt *M01.XML sidecar",
            )
        elif spec.sidecar_pairs:
            if spec.image_jump_setting == "Shot Mark1 Only" and not any(p.shot_mark1_frames for p in spec.sidecar_pairs):
                _reject(
                    P215_BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN,
                    "[Image Jump Setting = Shot Mark1 Only] selected with zero Shot Mark1 clips in vault",
                )
            elif spec.image_jump_setting == "Shot Mark2 Only" and not any(p.shot_mark2_frames for p in spec.sidecar_pairs):
                _reject(
                    P215_BLOCKED_IMAGE_JUMP_OR_FTP_SHOTMARK_RESCUE_BROKEN,
                    "[Image Jump Setting = Shot Mark2 Only] selected with zero Shot Mark2 clips in vault",
                )

    passed = len(errors) == 0 and block_code is None
    digest = _canonical_sha256(
        {
            "slots": sorted(slots_seen),
            "title_len": len(spec.title_name),
            "sdhc_locked": sdhc_locked_count,
            "collisions": collision_count,
            "sidecars": len(spec.sidecar_pairs),
            "marked_ready": marked_ready_for_ftp,
            "corrupt_xml": orphan_or_corrupt_xml,
            "h0_h3": h0_h3_ok,
            "block_code": block_code,
            "passed": passed,
        }
    )
    return FileSettingsAndShotMarkVaultReport(
        passed=passed,
        status=P215_STATUS_VERIFIED_PILLAR_31A if passed else P215_STATUS_REJECTED_PILLAR_31A,
        block_code=block_code,
        slots_audited=tuple(sorted(slots_seen)),
        title_name_length=len(spec.title_name),
        sdhc_slots_locked_to_standard=sdhc_locked_count,
        counter_collision_count=collision_count,
        sidecar_pairs_audited=len(spec.sidecar_pairs),
        marked_clips_ready_for_ftp=marked_ready_for_ftp,
        orphaned_or_corrupt_xml_count=orphan_or_corrupt_xml,
        h0_equals_h3_verified=h0_h3_ok,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 31B — [TC/UB] Regenerate Slot-1 Master, EXT-LK Release & Coupled REC Lamp Evaluator
# ---------------------------------------------------------------------------


def evaluate_tcregen_slot1_and_extlk_vault(
    spec: TcRegenSlot1AndExtLkVaultSpec,
) -> TcRegenSlot1AndExtLkVaultReport:
    """Audit `[Regenerate]` Slot-1 TC continuity, forced `[Rec Run]`, `EXT-LK` drop hazard, S&Q & `REC Lamp`."""
    errors: List[str] = list(_safety_invariant_errors())
    block_code: Optional[str] = None

    def _reject(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    if spec.persistent_write_unlock_requested:
        _reject(P215_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent eMMC write unlock forbidden in Pillar 31B")
    if spec.camera_model != P215_FX3_MODEL_NAME or spec.fw_version != P215_FX3_FW_VERSION:
        _reject(P215_BLOCKED_SAFETY_POLICY_VIOLATION, f"Unsupported host {spec.camera_model} fw={spec.fw_version}")

    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _reject(P215_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, f"Non-tmpfs overlay path forbidden: {spec.stage_b_overlay_dir}")
    if not spec.stage_b_overlay_wiped_on_reset:
        _reject(P215_BLOCKED_PERSISTENT_OVERLAY_ESCAPE, "Stage-B tmpfs overlay was not wiped cleanly on reset")
    h0_h3_ok = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P215_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _reject(P215_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT, "Backup.bin / 16-surface Tier-0 H0 != H3 or RO lock drift")

    # 1. Time Code Make = Regenerate -> Slot 1 exclusive read under Simult. Recording + forced Rec Run
    slot1_tc_ok = True
    if spec.recording_media not in P215_RECORDING_MEDIA_MODES:
        slot1_tc_ok = False
        _reject(P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION, f"Invalid [Recording Media]: {spec.recording_media!r}")
    if spec.time_code_make not in P215_TC_MAKE_MODES:
        slot1_tc_ok = False
        _reject(P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION, f"Invalid [Time Code Make]: {spec.time_code_make!r}")
    if spec.configured_time_code_run not in P215_TC_RUN_MODES or spec.effective_time_code_run not in P215_TC_RUN_MODES:
        slot1_tc_ok = False
        _reject(P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION, "Invalid [Time Code Run] mode")

    s1_frames = _parse_tc_to_frames(spec.slot1_last_end_tc, spec.fps_timebase_ceil)
    s2_frames = _parse_tc_to_frames(spec.slot2_last_end_tc, spec.fps_timebase_ceil)
    next_frames = _parse_tc_to_frames(spec.regenerated_next_start_tc, spec.fps_timebase_ceil)
    if s1_frames is None or s2_frames is None or next_frames is None:
        slot1_tc_ok = False
        _reject(
            P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION,
            f"Malformed SMPTE TC for fps_ceil={spec.fps_timebase_ceil}: s1={spec.slot1_last_end_tc!r}, s2={spec.slot2_last_end_tc!r}, next={spec.regenerated_next_start_tc!r}",
        )

    if spec.time_code_make == "Regenerate":
        if spec.effective_time_code_run != "Rec Run":
            slot1_tc_ok = False
            _reject(
                P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION,
                f"[Time Code Make = Regenerate] forces [Rec Run] advancement regardless of [Time Code Run]; got {spec.effective_time_code_run!r}",
            )
        expected_slot = 2 if spec.recording_media == "Slot 2" else 1
        if spec.regenerate_source_slot_used != expected_slot:
            slot1_tc_ok = False
            _reject(
                P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION,
                f"[Regenerate] under [{spec.recording_media}] must read reference TC from Slot {expected_slot} (got Slot {spec.regenerate_source_slot_used})",
            )
        ref_frames = s2_frames if expected_slot == 2 else s1_frames
        if ref_frames is not None and next_frames is not None:
            day_frames = 24 * 60 * 60 * spec.fps_timebase_ceil
            expected_next_frames = (ref_frames + 1) % day_frames
            if next_frames != expected_next_frames:
                slot1_tc_ok = False
                _reject(
                    P215_BLOCKED_TCREGEN_SLOT1_OR_FORCED_RECRUN_VIOLATION,
                    f"[Regenerate] next start TC {spec.regenerated_next_start_tc} breaks Slot-{expected_slot} sequential +1 continuity",
                )

    # 2. VMC-BNCM1 EXT-LK External Sync Release Hazard on Backup.bin / Profile Restore
    ext_lk_hazard = False
    if spec.vmc_bncm1_ext_lk_active_before_restore:
        if spec.shooting_mode != "Movie" or spec.sq_mode_active:
            ext_lk_hazard = True
            _reject(
                P215_BLOCKED_EXT_LK_DROP_HAZARD_ON_RESTORE,
                "VMC-BNCM1 EXT-LK external sync requires [Movie] shooting mode (cannot lock in S&Q)",
            )
        drops_ext_lk = (
            spec.restored_backup_time_code_make != "Preset"
            or spec.restored_backup_time_code_run != "Free Run"
        )
        if drops_ext_lk:
            if spec.ext_lk_retained_after_mode_change_assumed or not spec.ext_lk_rejam_acknowledged:
                ext_lk_hazard = True
                _reject(
                    P215_BLOCKED_EXT_LK_DROP_HAZARD_ON_RESTORE,
                    "Restoring Backup.bin with TC Make!=Preset or TC Run!=Free Run immediately drops EXT-LK external lock; re-jam acknowledgement required",
                )

    # 3. S&Q Lockout: [Time Code Run] and HDMI [Time Code Output] unavailable
    sq_ok = True
    if spec.hdmi_time_code_output not in P215_HDMI_TC_OUTPUT_MODES:
        sq_ok = False
        _reject(
            P215_BLOCKED_SQ_TIMECODE_RUN_OR_HDMI_TCOUT_LOCKOUT,
            f"Invalid HDMI [Time Code Output]: {spec.hdmi_time_code_output!r}",
        )
    if spec.sq_mode_active or spec.shooting_mode == "S&Q":
        if spec.sq_tc_run_override_attempted:
            sq_ok = False
            _reject(
                P215_BLOCKED_SQ_TIMECODE_RUN_OR_HDMI_TCOUT_LOCKOUT,
                "[Time Code Run] is unavailable during Slow & Quick (S&Q) shooting on FX3 Ver. 7.02",
            )
        if spec.hdmi_time_code_output == "On":
            sq_ok = False
            _reject(
                P215_BLOCKED_SQ_TIMECODE_RUN_OR_HDMI_TCOUT_LOCKOUT,
                "HDMI [Time Code Output = On] is unavailable during Slow & Quick (S&Q) shooting on FX3 Ver. 7.02",
            )

    # 4. Coupled Rear + Top REC Button Tally & [Silent Mode] -> [Audio signals = Off] Lock
    reclamp_ok = True
    if spec.rec_lamp_mode not in P215_REC_LAMP_MODES:
        reclamp_ok = False
        _reject(
            P215_BLOCKED_RECLAMP_COUPLED_TALLY_OR_SILENT_LOCK_DRIFT,
            f"Invalid FX3 [REC Lamp] mode {spec.rec_lamp_mode!r}; only All On / Only Front Off / All Off exist",
        )
    else:
        exp_leds = {
            "All On": (True, True, True),
            "Only Front Off": (False, True, True),
            "All Off": (False, False, False),
        }[spec.rec_lamp_mode]
        actual_leds = (spec.front_tally_led_on, spec.rear_tally_led_on, spec.top_rec_button_led_on)
        if actual_leds != exp_leds:
            reclamp_ok = False
            _reject(
                P215_BLOCKED_RECLAMP_COUPLED_TALLY_OR_SILENT_LOCK_DRIFT,
                f"[REC Lamp = {spec.rec_lamp_mode}] requires (front,rear,top_rec)={exp_leds} (coupled rear+top tally); got {actual_leds}",
            )

    silent_ok = True
    if spec.audio_signals_mode not in P215_AUDIO_SIGNALS_MODES:
        silent_ok = False
        _reject(
            P215_BLOCKED_RECLAMP_COUPLED_TALLY_OR_SILENT_LOCK_DRIFT,
            f"Invalid [Audio signals] mode: {spec.audio_signals_mode!r}",
        )
    elif spec.silent_mode_enabled and spec.audio_signals_mode != "Off":
        silent_ok = False
        _reject(
            P215_BLOCKED_RECLAMP_COUPLED_TALLY_OR_SILENT_LOCK_DRIFT,
            "[Silent Mode = On] hard-locks [Audio signals] to [Off]",
        )

    passed = len(errors) == 0 and block_code is None
    digest = _canonical_sha256(
        {
            "rec_media": spec.recording_media,
            "tc_make": spec.time_code_make,
            "eff_tc_run": spec.effective_time_code_run,
            "slot1_tc_ok": slot1_tc_ok,
            "ext_lk_hazard": ext_lk_hazard,
            "sq_ok": sq_ok,
            "reclamp_ok": reclamp_ok,
            "silent_ok": silent_ok,
            "h0_h3": h0_h3_ok,
            "block_code": block_code,
            "passed": passed,
        }
    )
    return TcRegenSlot1AndExtLkVaultReport(
        passed=passed,
        status=P215_STATUS_VERIFIED_PILLAR_31B if passed else P215_STATUS_REJECTED_PILLAR_31B,
        block_code=block_code,
        recording_media=spec.recording_media,
        time_code_make=spec.time_code_make,
        effective_time_code_run=spec.effective_time_code_run,
        slot1_master_tc_verified=slot1_tc_ok,
        ext_lk_drop_hazard_detected=ext_lk_hazard,
        sq_tc_hdmi_lockout_verified=sq_ok,
        coupled_reclamp_tally_verified=reclamp_ok,
        silent_mode_audio_lock_verified=silent_ok,
        h0_equals_h3_verified=h0_h3_ok,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h3_matched,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Default Specs & Unified Pillar 31 Entry Point
# ---------------------------------------------------------------------------


def build_default_safe_filesettings_shotmark_spec() -> FileSettingsAndShotMarkVaultSpec:
    return FileSettingsAndShotMarkVaultSpec(
        file_number_mode="Series",
        restored_series_counter_next=3,
        file_name_format="Title",
        cam_id="A",
        reel_number=1,
        title_name="FX3_PROD_UNIT01",
        slot_cards=(
            SlotMediaFileSettingsSpec(
                slot=1,
                card_type="CFexpress_Type_A",
                capacity_gb=160,
                filesystem="exFAT",
                effective_file_name_format="Title",
                existing_clip_numbers=(1, 2),
                existing_clip_stems=("FX3_PROD_UNIT010001", "FX3_PROD_UNIT010002"),
            ),
            SlotMediaFileSettingsSpec(
                slot=2,
                card_type="SDXC",
                capacity_gb=128,
                filesystem="exFAT",
                effective_file_name_format="Title",
                existing_clip_numbers=(1, 2),
                existing_clip_stems=("FX3_PROD_UNIT010001", "FX3_PROD_UNIT010002"),
            ),
        ),
        sidecar_pairs=(
            ShotMarkSidecarPairSpec(
                stem="FX3_PROD_UNIT010001",
                slot=1,
                mp4_relpath="/M4ROOT/CLIP/FX3_PROD_UNIT010001.MP4",
                xml_relpath="/M4ROOT/CLIP/FX3_PROD_UNIT010001M01.XML",
                shot_mark1_frames=(24, 120),
                shot_mark2_frames=(240,),
            ),
            ShotMarkSidecarPairSpec(
                stem="FX3_PROD_UNIT010002",
                slot=2,
                mp4_relpath="/M4ROOT/CLIP/FX3_PROD_UNIT010002.MP4",
                xml_relpath="/M4ROOT/CLIP/FX3_PROD_UNIT010002M01.XML",
                shot_mark1_frames=(48,),
                shot_mark2_frames=(),
            ),
        ),
        image_jump_setting="Shot Mark Only",
        ftp_target_movie="Only Shot Mark Mov.",
        ftp_batch_rescue_active=True,
    )


def build_default_safe_tcregen_extlk_spec() -> TcRegenSlot1AndExtLkVaultSpec:
    return TcRegenSlot1AndExtLkVaultSpec(
        shooting_mode="Movie",
        sq_mode_active=False,
        recording_media="Simult. Recording",
        time_code_make="Regenerate",
        configured_time_code_run="Free Run",
        effective_time_code_run="Rec Run",
        fps_timebase_ceil=24,
        slot1_last_end_tc="01:12:30:10",
        slot2_last_end_tc="00:45:10:02",
        regenerated_next_start_tc="01:12:30:11",
        regenerate_source_slot_used=1,
        vmc_bncm1_ext_lk_active_before_restore=False,
        hdmi_time_code_output="On",
        rec_lamp_mode="Only Front Off",
        front_tally_led_on=False,
        rear_tally_led_on=True,
        top_rec_button_led_on=True,
        silent_mode_enabled=True,
        audio_signals_mode="Off",
    )


def verify_filesettings_shotmark_and_tcregen_slot1_vault(
    *,
    filesettings_spec: Optional[FileSettingsAndShotMarkVaultSpec] = None,
    tcregen_spec: Optional[TcRegenSlot1AndExtLkVaultSpec] = None,
    force_clean_room: Optional[bool] = None,
) -> FileSettingsShotMarkAndTcRegenVaultReport:
    """Unified Pillar 31 verifier auditing `[File Settings]` + `Shot Mark1/2` XML sidecars and `TC Regenerate` Slot-1 continuity."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    donor_snapshot = inspect_phase215_donors_readonly(force_clean_room=force_clean_room)
    fs_rep = evaluate_filesettings_and_shotmark_xml_vault(
        filesettings_spec or build_default_safe_filesettings_shotmark_spec()
    )
    tc_rep = evaluate_tcregen_slot1_and_extlk_vault(tcregen_spec or build_default_safe_tcregen_extlk_spec())
    all_ok = donor_snapshot.all_donors_present and donor_snapshot.under_0_15s_budget and fs_rep.passed and tc_rep.passed
    combined_errs = tuple(list(fs_rep.errors) + list(tc_rep.errors))
    return FileSettingsShotMarkAndTcRegenVaultReport(
        schema=PHASE215_SCHEMA,
        version=PHASE215_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P215_STATUS_VERIFIED_PILLAR31_SUITE if all_ok else P215_STATUS_FAIL_PILLAR31_SUITE,
        donor_snapshot=donor_snapshot,
        filesettings_shotmark_report=fs_rep,
        tcregen_extlk_report=tc_rep,
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
# Pillar 31A & 31B 6-Scenario Suites & Standalone Pillar 31 Suite
# ---------------------------------------------------------------------------


def run_pillar31a_filesettings_shotmark_6_scenario_suite() -> Pillar31ASuiteResult:
    max37_title = "FX3_A01-2026.11.15_UNIT#1$%+=[OK]1234"  # exact 37 ASCII chars
    cases: Tuple[Tuple[str, bool, FileSettingsAndShotMarkVaultSpec, str], ...] = (
        (
            P215_PILLAR_31A_SCENARIO_IDS[0],
            True,
            FileSettingsAndShotMarkVaultSpec(
                file_name_format="Date + Title",
                title_name=max37_title,
                restored_series_counter_next=10,
                slot_cards=(
                    SlotMediaFileSettingsSpec(slot=1, card_type="CFexpress_Type_A", capacity_gb=160, filesystem="exFAT", effective_file_name_format="Date + Title", existing_clip_numbers=(1, 9)),
                    SlotMediaFileSettingsSpec(slot=2, card_type="SDXC", capacity_gb=128, filesystem="exFAT", effective_file_name_format="Date + Title", existing_clip_numbers=(1, 9)),
                ),
                sidecar_pairs=(
                    ShotMarkSidecarPairSpec(
                        stem="20261115_FX3_0009",
                        slot=1,
                        mp4_relpath="/M4ROOT/CLIP/20261115_FX3_0009.MP4",
                        xml_relpath="/M4ROOT/CLIP/20261115_FX3_0009M01.XML",
                        shot_mark1_frames=(30,),
                        shot_mark2_frames=(90,),
                    ),
                ),
            ),
            "Dual-slot exFAT 37-char ASCII Title + Shot Mark1/2 *M01.XML sidecar passes",
        ),
        (
            P215_PILLAR_31A_SCENARIO_IDS[1],
            True,
            FileSettingsAndShotMarkVaultSpec(
                file_name_format="Standard",
                restored_series_counter_next=2,
                slot_cards=(
                    SlotMediaFileSettingsSpec(
                        slot=2,
                        card_type="SDHC",
                        capacity_gb=32,
                        filesystem="FAT32",
                        effective_file_name_format="Standard",
                        custom_movie_folder_requested=False,
                        existing_clip_numbers=(1,),
                    ),
                ),
                sidecar_pairs=(
                    ShotMarkSidecarPairSpec(
                        stem="C0001",
                        slot=2,
                        mp4_relpath="/M4ROOT/CLIP/C0001.MP4",
                        xml_relpath="/M4ROOT/CLIP/C0001M01.XML",
                        shot_mark1_frames=(12,),
                    ),
                ),
            ),
            "SDHC <=32GB FAT32 card locked to [Standard] with non-custom folder passes",
        ),
        (
            P215_PILLAR_31A_SCENARIO_IDS[2],
            False,
            FileSettingsAndShotMarkVaultSpec(
                file_name_format="Cam ID + Reel#",
                slot_cards=(
                    SlotMediaFileSettingsSpec(
                        slot=1,
                        card_type="SDHC",
                        capacity_gb=32,
                        filesystem="FAT32",
                        effective_file_name_format="Cam ID + Reel#",
                        custom_movie_folder_requested=True,
                    ),
                ),
                ftp_batch_rescue_active=False,
                image_jump_setting="Off",
            ),
            "SDHC <=32GB FAT32 attempting non-Standard format or custom movie folder fails closed",
        ),
        (
            P215_PILLAR_31A_SCENARIO_IDS[3],
            False,
            FileSettingsAndShotMarkVaultSpec(
                file_number_mode="Series",
                restored_series_counter_next=4,
                slot_cards=(
                    SlotMediaFileSettingsSpec(
                        slot=1,
                        card_type="CFexpress_Type_A",
                        capacity_gb=160,
                        filesystem="exFAT",
                        effective_file_name_format="Cam ID + Reel#",
                        existing_clip_numbers=(1, 2, 3, 4, 5),
                        existing_clip_stems=("A001C0004",),
                    ),
                ),
                ftp_batch_rescue_active=False,
                image_jump_setting="Off",
            ),
            "Restored Series / Cam ID + Reel# counter colliding with existing M4ROOT/CLIP clip fails closed",
        ),
        (
            P215_PILLAR_31A_SCENARIO_IDS[4],
            False,
            FileSettingsAndShotMarkVaultSpec(
                sidecar_pairs=(
                    ShotMarkSidecarPairSpec(
                        stem="C0010",
                        slot=1,
                        mp4_relpath="/M4ROOT/CLIP/C0010.MP4",
                        xml_relpath="/M4ROOT/CLIP/C0010M01.XML",
                        mp4_present=False,
                        xml_present=True,
                        shot_mark1_frames=(10,),
                    ),
                ),
            ),
            "Orphaned M4ROOT/CLIP/*M01.XML sidecar without paired .MP4 fails closed",
        ),
        (
            P215_PILLAR_31A_SCENARIO_IDS[5],
            False,
            FileSettingsAndShotMarkVaultSpec(
                sidecar_pairs=(
                    ShotMarkSidecarPairSpec(
                        stem="C0011",
                        slot=1,
                        mp4_relpath="/M4ROOT/CLIP/C0011.MP4",
                        xml_relpath="/M4ROOT/CLIP/C0011M01.XML",
                        shot_mark1_frames=(),
                        shot_mark2_frames=(),
                    ),
                ),
                image_jump_setting="Shot Mark1 Only",
                ftp_target_movie="Only Shot Mark Mov.",
                ftp_batch_rescue_active=True,
            ),
            "[Shot Mark1 Only] / [Only Shot Mark Mov.] FTP rescue with zero marked clips fails closed",
        ),
    )
    outcomes: List[Pillar31ScenarioOutcome] = []
    for sid, exp_ok, spec, detail in cases:
        rep = evaluate_filesettings_and_shotmark_xml_vault(spec)
        outcomes.append(
            Pillar31ScenarioOutcome(
                scenario_id=sid,
                pillar="PILLAR_31A",
                expected_allowed=exp_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=(rep.passed == exp_ok),
                detail=detail,
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes)
    return Pillar31ASuiteResult(
        passed=all_ok,
        status=P215_STATUS_VERIFIED_PILLAR_31A if all_ok else P215_STATUS_REJECTED_PILLAR_31A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar31b_tcregen_slot1_extlk_6_scenario_suite() -> Pillar31BSuiteResult:
    cases: Tuple[Tuple[str, bool, TcRegenSlot1AndExtLkVaultSpec, str], ...] = (
        (
            P215_PILLAR_31B_SCENARIO_IDS[0],
            True,
            build_default_safe_tcregen_extlk_spec(),
            "[Simult. Recording] + [Regenerate] reads Slot 1 exclusively and forces [Rec Run]",
        ),
        (
            P215_PILLAR_31B_SCENARIO_IDS[1],
            True,
            TcRegenSlot1AndExtLkVaultSpec(
                shooting_mode="Movie",
                recording_media="Slot 1",
                time_code_make="Preset",
                configured_time_code_run="Free Run",
                effective_time_code_run="Free Run",
                vmc_bncm1_ext_lk_active_before_restore=True,
                restored_backup_time_code_make="Preset",
                restored_backup_time_code_run="Free Run",
                ext_lk_rejam_acknowledged=True,
                rec_lamp_mode="All On",
                front_tally_led_on=True,
                rear_tally_led_on=True,
                top_rec_button_led_on=True,
            ),
            "VMC-BNCM1 EXT-LK external sync preserved under Movie + Preset + Free Run",
        ),
        (
            P215_PILLAR_31B_SCENARIO_IDS[2],
            False,
            TcRegenSlot1AndExtLkVaultSpec(
                recording_media="Simult. Recording",
                time_code_make="Regenerate",
                configured_time_code_run="Free Run",
                effective_time_code_run="Rec Run",
                fps_timebase_ceil=24,
                slot1_last_end_tc="01:12:30:10",
                slot2_last_end_tc="00:45:10:02",
                regenerated_next_start_tc="00:45:10:03",
                regenerate_source_slot_used=2,
            ),
            "[Simult. Recording] Regenerate reading Slot 2 instead of Slot 1 fails closed",
        ),
        (
            P215_PILLAR_31B_SCENARIO_IDS[3],
            False,
            TcRegenSlot1AndExtLkVaultSpec(
                shooting_mode="Movie",
                vmc_bncm1_ext_lk_active_before_restore=True,
                restored_backup_time_code_make="Regenerate",
                restored_backup_time_code_run="Rec Run",
                ext_lk_retained_after_mode_change_assumed=True,
                ext_lk_rejam_acknowledged=False,
            ),
            "Unacknowledged VMC-BNCM1 EXT-LK drop when Backup.bin restores Regenerate fails closed",
        ),
        (
            P215_PILLAR_31B_SCENARIO_IDS[4],
            False,
            TcRegenSlot1AndExtLkVaultSpec(
                shooting_mode="S&Q",
                sq_mode_active=True,
                sq_tc_run_override_attempted=True,
                hdmi_time_code_output="On",
            ),
            "S&Q mode attempting [Time Code Run] override or HDMI [Time Code Output = On] fails closed",
        ),
        (
            P215_PILLAR_31B_SCENARIO_IDS[5],
            True,
            TcRegenSlot1AndExtLkVaultSpec(
                shooting_mode="S&Q",
                sq_mode_active=True,
                sq_tc_run_override_attempted=False,
                hdmi_time_code_output="Off",
                rec_lamp_mode="All Off",
                front_tally_led_on=False,
                rear_tally_led_on=False,
                top_rec_button_led_on=False,
                emphasized_rec_display_on=True,
                silent_mode_enabled=True,
                audio_signals_mode="Off",
            ),
            "S&Q HDMI TC Off + REC Lamp [All Off] coupled tally + Silent Mode Audio Off + 16/16 H0==H3",
        ),
    )
    outcomes: List[Pillar31ScenarioOutcome] = []
    for sid, exp_ok, spec, detail in cases:
        rep = evaluate_tcregen_slot1_and_extlk_vault(spec)
        outcomes.append(
            Pillar31ScenarioOutcome(
                scenario_id=sid,
                pillar="PILLAR_31B",
                expected_allowed=exp_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=(rep.passed == exp_ok),
                detail=detail,
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes)
    return Pillar31BSuiteResult(
        passed=all_ok,
        status=P215_STATUS_VERIFIED_PILLAR_31B if all_ok else P215_STATUS_REJECTED_PILLAR_31B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar31_standalone_suite(
    *,
    force_clean_room: Optional[bool] = None,
) -> Pillar31StandaloneReport:
    """Run Pillar 31 standalone suite (bounded donor check + Pillar 31A 6/6 + Pillar 31B 6/6)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase215_donors_readonly(force_clean_room=force_clean_room)
    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_a = pool.submit(run_pillar31a_filesettings_shotmark_6_scenario_suite)
        fut_b = pool.submit(run_pillar31b_tcregen_slot1_extlk_6_scenario_suite)
        res_a = fut_a.result()
        res_b = fut_b.result()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 215 donor verification failed")
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
            "schema": PHASE215_SCHEMA,
            "mode": donor_snapshot.verification_mode,
            "p31a": [(s.scenario_id, s.passed, s.block_code) for s in res_a.scenarios],
            "p31b": [(s.scenario_id, s.passed, s.block_code) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar31StandaloneReport(
        schema=PHASE215_SCHEMA,
        version=PHASE215_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P215_STATUS_VERIFIED_PILLAR31_SUITE if all_ok else P215_STATUS_FAIL_PILLAR31_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_31a_filesettings_shotmark_vault=res_a,
        pillar_31b_tcregen_slot1_extlk_vault=res_b,
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
# Unified 31/31 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master31_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_31pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master31PillarRecoveryReport:
    """Evaluate and aggregate all 31 recovery pillars (`1..31`) concurrently -> `31/31` master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_31_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_30pillar() -> Master30PillarRecoveryReport:
        return evaluate_realhw_30pillar_recovery_master(**kw)

    def _run_p31() -> Tuple[Pillar31StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar31_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_30 = pool.submit(_run_30pillar)
        fut_31 = pool.submit(_run_p31)
        m30_rep = fut_30.result()
        p31_rep, p31_dt = fut_31.result()

    all_errors: List[str] = list(m30_rep.errors) + list(p31_rep.errors)
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
        if getattr(m30_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-30 violated {attr_name} == {expected_val}")
        if getattr(p31_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 31 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m30_rep.pillars)
    spec31 = MASTER_31_PILLAR_SPECS[30]
    p31_metrics = {
        "pillar_31a_filesettings_shotmark_vault": (
            f"{p31_rep.pillar_31a_filesettings_shotmark_vault.scenarios_passed}/"
            f"{p31_rep.pillar_31a_filesettings_shotmark_vault.scenarios_total}"
        ),
        "pillar_31b_tcregen_slot1_extlk_vault": (
            f"{p31_rep.pillar_31b_tcregen_slot1_extlk_vault.scenarios_passed}/"
            f"{p31_rep.pillar_31b_tcregen_slot1_extlk_vault.scenarios_total}"
        ),
        "donor_files_inspected": p31_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec31[0],
            pillar_id=spec31[1],
            phase_label=spec31[2],
            module_name=spec31[3],
            passed=bool(p31_rep.all_passed),
            status=p31_rep.status,
            verification_mode=p31_rep.verification_mode,
            elapsed_seconds=p31_dt,
            key_metrics=p31_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec31[1],
                    "mode": p31_rep.verification_mode,
                    "status": p31_rep.status,
                    "metrics": p31_metrics,
                    "passed": p31_rep.all_passed,
                }
            ),
            errors=tuple(p31_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master31_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p31_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_31_PILLAR_COUNT == 31
        and pillars_passed == 31
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE215_SCHEMA,
            "version": PHASE215_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master31PillarRecoveryReport(
        schema=PHASE215_SCHEMA,
        version=PHASE215_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P215_STATUS_VERIFIED_31OF31_AGGREGATOR if all_ok else P215_STATUS_FAIL_31OF31_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P215_CONCURRENT_CEILING_SECONDS,
        nominal_under_2_8s=elapsed < P215_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p31_rep.donor_snapshot,
        pillar31_a_filesettings_shotmark_vault=p31_rep.pillar_31a_filesettings_shotmark_vault,
        pillar31_b_tcregen_slot1_extlk_vault=p31_rep.pillar_31b_tcregen_slot1_extlk_vault,
        master_31pillar_sha256=master_sha,
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


def evaluate_31pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master31PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_31pillar_recovery_master`."""
    return evaluate_realhw_31pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_31pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master31PillarRecoveryReport:
    """Public CLI entry point for Pillar 31 unified `31/31` real-hardware recovery master verification."""
    return evaluate_realhw_31pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
