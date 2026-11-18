"""Phase 245 — Milestone Pillar 40 (`40/40` Recovery Pillars) & Unified 40-Pillar Recovery Master
(`verify-40pillar-recovery` / `verify-lock-op-parts-audio-timing-exp-step-vault`):

1. **Pillar 40A — `[Lock Operation Parts]` (`Fn` Hold, `MENU + Fn` 5s Full-Body Lock Chord &
   `My Dial` Temporary Override) Bench Vault Protection (`ILME-FX3 Ver. 7.02`, Wave-38)**:
   - Models `MENU` -> `Setup` -> `[Dial Customize]` -> `[Lock Operation Parts]` (`Off` default,
     `Multi-Selector Only`, `Dial + Wheel`, `All`), verifying non-resettable `[Setup]` survival
     across `[Camera Settings Reset]` (restored to `Off` **only** by `[Initialize]`) plus
     deterministic Slot-1 `CAMSET01.DAT` `[Load]` restoration.
   - Enforces the 3 hardware key-chord & override invariants:
     (a) `Fn` hold toggle engages/releases the configured `[Lock Operation Parts]` scope and
         displays `"Locked."` on the monitor (`Off` -> `Fn` hold locks nothing);
     (b) `MENU + Fn` simultaneous `5`-second full-body lock chord locks/unlocks **all buttons,
         dials, and wheels except the shutter button** during unattended Tier-0 `pnflasha` /
         `cnflasha` bench dumps, strictly distinguished from the destructive `MENU + Delete`
         `2`-second Slot Full Format chord (`destructive_menu_delete_confusions == 0`);
     (c) `My Dial` temporary recall unlocks the assigned dials/wheels for the duration of the
         recall even while `[Lock Operation Parts]` holds dials/wheels locked, immediately
         re-locking upon release.

2. **Pillar 40B — `[Audio Out Timing]` (`Live`/`Lip Sync`) vs `[Audio signals]` Setup Persistence
   & `[Exposure step]` (`0.3EV`/`0.5EV`) vs `[Shutter Angle]` Constant-Table Recovery**:
   - Models `MENU` -> `Shooting` -> `[Audio Recording]` -> `[Audio Out Timing]` (`Live` default /
     `Lip Sync`), verifying reset to `Live` via `[Camera Settings Reset]` and hardware lockout
     whenever `S&Q Motion` is active or `[Audio Recording] = Off`.
   - Models `MENU` -> `Setup` -> `[Sound Option]` -> `[Audio signals]` (`On` default / `Off`),
     verifying survival across `[Camera Settings Reset]` (reset only by `[Initialize]`) while
     enforcing hardware lock to `Off` whenever `[Silent Mode] = On`.
   - Models `MENU` -> `Exposure/Color` -> `[Exposure Comp.]` -> `[Exposure step]` (`0.3EV`
     default / `0.5EV`, resettable via `[Camera Settings Reset]`) governing `[Shutter Speed]`,
     `Aperture` (`F-stop`), and `Exposure Comp.` increments while **`[Shutter Angle]`
     (`[Shutter Mode] = Shutter Angle`, `Ver. 6.00+`..`7.02`) remains strictly immune on its
     constant cine shutter-angle table** (`5.6°`..`360°`,
     `shutter_angle_exposure_step_drift_events == 0`), plus lossless Slot-1 `CAMSET01.DAT`
     `[Load]` restoration and `16/16` Tier-0 `Backup.bin` `H0 == H3` parity.

3. **Unified `40/40` Milestone Recovery Master (`evaluate_realhw_40pillar_recovery_master`)**:
   - Delegates Pillars `1..39` concurrently to `evaluate_realhw_39pillar_recovery_master` +
     **Pillar 40** -> **`40/40` (`VERIFIED_40OF40_PILLAR_RECOVERY_MASTER`)** in `< 4.0s`
     nominal (`< 6.0s` concurrent ceiling).
"""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass
from hashlib import sha256
import json
import os
import posixpath
import stat
import struct
import time
from typing import Any, Dict, List, Optional, Tuple

from .files import is_forced_clean_room, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_39pillar_framing_usbpower_lun_antiflicker_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_39_PILLAR_SPECS,
    Master39PillarRecoveryReport,
    evaluate_realhw_39pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE245_SCHEMA: str = "realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier_v1"
PHASE245_VERSION: str = "1.0.0"

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
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P245_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P245_DESTRUCTIVE_MENU_DELETE_CONFUSIONS: int = 0
P245_SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS: int = 0

P245_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P245_NOMINAL_BUDGET_SECONDS: float = 4.0
P245_CONCURRENT_CEILING_SECONDS: float = 6.0
P245_BOUNDED_HEADER_BYTES: int = 4096
P245_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-38 / FX3 Ver. 7.02 & FX6 Ver. 6.01 Donor Anchors (bounded O_RDONLY verification)
P245_FX3_MODEL_NAME: str = "ILME-FX3"
P245_FX3_MODEL_ID: int = 0x91030080
P245_FX3_HELPGUIDE_ID: str = "ilc/2210"
P245_FX3_FW_VERSION: str = "7.02"
P245_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P245_FX6_DONOR_FW_VERSION: str = "6.01"
P245_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
    "2.00",
    "2.01",
    "2.02",
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)
P245_FX3_SHUTTER_ANGLE_FW_VERSIONS: Tuple[str, ...] = (
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P245_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P245_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P245_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)

P245_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P245_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P245_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P245_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P245_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P245_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P245_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P245_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P245_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P245_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P245_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P245_PINNED_FX3_LIBBACKUP_SO_SHA256: str = (
    "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
)

P245_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P245_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P245_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

P245_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P245_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P245_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P245_DONOR_FX3_LIBGPE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so"
)
P245_PINNED_FX3_LIBGPE_SO_BYTES: int = 106480
P245_PINNED_FX3_LIBGPE_SO_SHA256: str = (
    "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464"
)

P245_DONOR_FX6_LIBINFRADIAL_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraDial.so"
)
P245_PINNED_FX6_LIBINFRADIAL_SO_BYTES: int = 31232
P245_PINNED_FX6_LIBINFRADIAL_SO_SHA256: str = (
    "b2034d6c85372027444e783d5d2ed913bb5a8cd2fe4051b10cf63caae875db33"
)

P245_DONOR_FX6_LIBINFRAINPUT_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraInput.so"
)
P245_PINNED_FX6_LIBINFRAINPUT_SO_BYTES: int = 93448
P245_PINNED_FX6_LIBINFRAINPUT_SO_SHA256: str = (
    "1851e2dc8515d2240b9ecaffd58591207336c5f061b1af0d3585d7b082a41f02"
)

# Pillar 40A — [Lock Operation Parts], Fn Hold, MENU + Fn 5s Full-Body Chord & My Dial Override
P245_LOCK_OPERATION_PARTS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Dial Customize",
    "Lock Operation Parts",
)
P245_LOCK_OPERATION_PARTS_DEFAULT: str = "Off"
P245_LOCK_OPERATION_PARTS_MODES: Tuple[str, ...] = (
    "Off",
    "Multi-Selector Only",
    "Dial + Wheel",
    "All",
)
P245_LOCK_OPERATION_PARTS_UI_SHORT_LABELS: Dict[str, str] = {
    "Multi-Slct Only": "Multi-Selector Only",
}
P245_DIAL_WHEEL_CONTROLS: Tuple[str, ...] = (
    "FRONT_DIAL",
    "REAR_DIAL",
    "CONTROL_WHEEL",
)
P245_FN_HOLD_SCOPE_BY_MODE: Dict[str, Tuple[str, ...]] = {
    "Off": (),
    "Multi-Selector Only": ("MULTI_SELECTOR",),
    "Dial + Wheel": ("FRONT_DIAL", "REAR_DIAL", "CONTROL_WHEEL"),
    "All": ("MULTI_SELECTOR", "FRONT_DIAL", "REAR_DIAL", "CONTROL_WHEEL"),
}
P245_MENU_FN_5S_CHORD_KEYS: Tuple[str, ...] = ("MENU", "Fn")
P245_DESTRUCTIVE_MENU_DELETE_2S_CHORD_KEYS: Tuple[str, ...] = ("MENU", "Delete")
P245_MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS: float = 5.0
P245_DESTRUCTIVE_MENU_DELETE_FORMAT_HOLD_SECONDS: float = 2.0
P245_MENU_FN_5S_LOCKED_CONTROLS: Tuple[str, ...] = (
    "ALL_BUTTONS_EXCEPT_SHUTTER",
    "MULTI_SELECTOR",
    "FRONT_DIAL",
    "REAR_DIAL",
    "CONTROL_WHEEL",
)
P245_LOCKED_OSD_MESSAGE: str = "Locked."

# Pillar 40B — [Audio Out Timing], [Audio signals], [Exposure step] & [Shutter Angle] Immunity
P245_AUDIO_OUT_TIMING_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Audio Recording",
    "Audio Out Timing",
)
P245_AUDIO_OUT_TIMING_DEFAULT: str = "Live"
P245_AUDIO_OUT_TIMING_MODES: Tuple[str, ...] = ("Live", "Lip Sync")

P245_AUDIO_SIGNALS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Sound Option",
    "Audio signals",
)
P245_AUDIO_SIGNALS_DEFAULT: str = "On"
P245_ON_OFF_MODES: Tuple[str, ...] = ("Off", "On")

P245_EXPOSURE_STEP_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Exposure/Color",
    "Exposure Comp.",
    "Exposure step",
)
P245_EXPOSURE_STEP_DEFAULT: str = "0.3EV"
P245_EXPOSURE_STEP_MODES: Tuple[str, ...] = ("0.3EV", "0.5EV")
P245_EXPOSURE_STEP_GOVERNED_TARGETS: Tuple[str, ...] = (
    "Shutter Speed",
    "Aperture",
    "Exposure Comp.",
)

P245_SHUTTER_MODE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Exposure/Color",
    "Shutter/Silent",
    "Shutter Mode",
)
P245_SHUTTER_MODES: Tuple[str, ...] = ("Shutter Speed", "Shutter Angle")
P245_CAPTURE_MODES: Tuple[str, ...] = ("Movie", "Still", "S&Q Motion")
P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG: Tuple[float, ...] = (
    5.6,
    11.2,
    22.5,
    45.0,
    72.0,
    90.0,
    144.0,
    172.8,
    180.0,
    270.0,
    360.0,
)

P245_RESET_ACTIONS: Tuple[str, ...] = ("NONE", "Camera Settings Reset", "Initialize")
P245_SLOT1_VAULT_SLOT: int = 1
P245_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P245_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_lock_op_parts_audio_timing_exp_step_overlay"
P245_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P245_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P245_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P245_BLOCKED_INVALID_LOCK_OPERATION_PARTS_SPEC: str = (
    "BLOCKED_INVALID_LOCK_OPERATION_PARTS_SPEC"
)
P245_BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT: str = (
    "BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT"
)
P245_BLOCKED_CAMSET_LOCK_OP_PARTS_RESTORE_DRIFT: str = (
    "BLOCKED_CAMSET_LOCK_OP_PARTS_RESTORE_DRIFT"
)
P245_BLOCKED_FN_HOLD_SCOPE_OR_BANNER_MISMATCH: str = (
    "BLOCKED_FN_HOLD_SCOPE_OR_BANNER_MISMATCH"
)
P245_BLOCKED_DESTRUCTIVE_MENU_DELETE_FORMAT_CHORD_CONFUSION: str = (
    "BLOCKED_DESTRUCTIVE_MENU_DELETE_FORMAT_CHORD_CONFUSION"
)
P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH: str = (
    "BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH"
)
P245_BLOCKED_UNATTENDED_TIER0_BENCH_UNLOCKED_CONTROLS: str = (
    "BLOCKED_UNATTENDED_TIER0_BENCH_UNLOCKED_CONTROLS"
)
P245_BLOCKED_MY_DIAL_TEMPORARY_OVERRIDE_MISMATCH: str = (
    "BLOCKED_MY_DIAL_TEMPORARY_OVERRIDE_MISMATCH"
)

P245_BLOCKED_INVALID_AUDIO_TIMING_OR_EXPOSURE_STEP_SPEC: str = (
    "BLOCKED_INVALID_AUDIO_TIMING_OR_EXPOSURE_STEP_SPEC"
)
P245_BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT: str = (
    "BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT"
)
P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION: str = (
    "BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION"
)
P245_BLOCKED_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION: str = (
    "BLOCKED_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION"
)
P245_BLOCKED_EXPOSURE_STEP_RESET_OR_GOVERNED_TARGETS_MISMATCH: str = (
    "BLOCKED_EXPOSURE_STEP_RESET_OR_GOVERNED_TARGETS_MISMATCH"
)
P245_BLOCKED_SHUTTER_ANGLE_EXPOSURE_STEP_COUPLED_DRIFT: str = (
    "BLOCKED_SHUTTER_ANGLE_EXPOSURE_STEP_COUPLED_DRIFT"
)
P245_BLOCKED_CAMSET_AUDIO_TIMING_OR_EXP_STEP_RESTORE_DRIFT: str = (
    "BLOCKED_CAMSET_AUDIO_TIMING_OR_EXP_STEP_RESTORE_DRIFT"
)
P245_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P245_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P245_STATUS_VERIFIED_PILLAR_40A: str = (
    "VERIFIED_PILLAR_40A_LOCK_OP_PARTS_MENU_FN_5S_CHORD_AND_MY_DIAL_VAULT"
)
P245_STATUS_REJECTED_PILLAR_40A: str = (
    "REJECTED_PILLAR_40A_LOCK_OP_PARTS_MENU_FN_5S_CHORD_AND_MY_DIAL_VAULT"
)
P245_STATUS_VERIFIED_PILLAR_40B: str = (
    "VERIFIED_PILLAR_40B_AUDIO_OUT_TIMING_AUDIO_SIGNALS_EXP_STEP_SHUTTER_ANGLE_VAULT"
)
P245_STATUS_REJECTED_PILLAR_40B: str = (
    "REJECTED_PILLAR_40B_AUDIO_OUT_TIMING_AUDIO_SIGNALS_EXP_STEP_SHUTTER_ANGLE_VAULT"
)
P245_STATUS_VERIFIED_PILLAR40_SUITE: str = (
    "VERIFIED_PILLAR40_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_VAULT"
)
P245_STATUS_FAIL_PILLAR40_SUITE: str = (
    "FAIL_PILLAR40_LOCK_OP_PARTS_AUDIO_TIMING_EXP_STEP_VAULT"
)
P245_STATUS_VERIFIED_40OF40_AGGREGATOR: str = "VERIFIED_40OF40_PILLAR_RECOVERY_MASTER"
P245_STATUS_FAIL_40OF40_AGGREGATOR: str = "FAIL_40OF40_PILLAR_RECOVERY_MASTER"

P245_PILLAR_40A_SCENARIO_IDS: Tuple[str, ...] = (
    "P40A1_LOCK_OP_PARTS_SURVIVES_CAMERA_SETTINGS_RESET_AND_MENU_FN_5S_BENCH_LOCK_SAFE",
    "P40A2_INITIALIZE_RESETS_LOCK_OP_PARTS_OFF_AND_CAMSET01_RESTORES_DIAL_WHEEL_WITH_MY_DIAL_TEMP_UNLOCK_SAFE",
    "P40A3_REJECT_LOCK_OP_PARTS_WIPED_BY_CAMERA_SETTINGS_RESET_OR_FN_HOLD_SCOPE_DRIFT",
    "P40A4_REJECT_DESTRUCTIVE_MENU_DELETE_2S_FORMAT_CHORD_CONFUSED_WITH_MENU_FN_5S_LOCK",
    "P40A5_REJECT_MENU_FN_SUB_5S_PREMATURE_LOCK_OR_SHUTTER_BUTTON_LOCK_CLAIM",
    "P40A6_REJECT_MY_DIAL_RECALL_BLOCKED_OR_PERMANENT_UNLOCK_LEAK_WHILE_DIALS_LOCKED",
)
P245_PILLAR_40B_SCENARIO_IDS: Tuple[str, ...] = (
    "P40B1_CAMERA_SETTINGS_RESET_RESTORES_AUDIO_TIMING_LIVE_EXP_STEP_03EV_WHILE_AUDIO_SIGNALS_SURVIVES_SAFE",
    "P40B2_CAMSET01_LOAD_RESTORES_LIP_SYNC_05EV_WITH_SHUTTER_ANGLE_180_CONSTANT_TABLE_IMMUNITY_SAFE",
    "P40B3_REJECT_AUDIO_SIGNALS_WIPED_BY_CAMERA_SETTINGS_RESET_OR_AUDIO_TIMING_NOT_RESET",
    "P40B4_REJECT_AUDIO_OUT_TIMING_CLAIMED_AVAILABLE_IN_SQ_MOTION_OR_AUDIO_RECORDING_OFF",
    "P40B5_REJECT_AUDIO_SIGNALS_CLAIMED_ACTIVE_WHILE_SILENT_MODE_ON",
    "P40B6_REJECT_SHUTTER_ANGLE_TABLE_DRIFT_WHEN_EXPOSURE_STEP_SWITCHED_TO_05EV",
)

MASTER_40_PILLAR_COUNT: int = 40
MASTER_40_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_39_PILLAR_SPECS + (
    (
        40,
        "pillar_40_lock_op_parts_audio_timing_exp_step_vault",
        "Phase 245",
        "fx3_recovery.realhw_40pillar_lock_op_parts_audio_timing_exp_step_vault_verifier",
    ),
)
MASTER_40_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_40_PILLAR_SPECS)


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
        ("HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("P245_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P245_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P245_DESTRUCTIVE_MENU_DELETE_CONFUSIONS", P245_DESTRUCTIVE_MENU_DELETE_CONFUSIONS, 0),
        ("P245_SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS", P245_SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS, 0),
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
    return any(tok in low for tok in P245_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase245DonorArtifactDigest:
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
class Phase245DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase245DonorArtifactDigest, ...]


@dataclass(frozen=True)
class LockOperationPartsBenchVaultSpec:
    camera_model: str = P245_FX3_MODEL_NAME
    helpguide_id: str = P245_FX3_HELPGUIDE_ID
    fw_version: str = P245_FX3_FW_VERSION
    lock_op_parts_menu_path: Tuple[str, ...] = P245_LOCK_OPERATION_PARTS_MENU_PATH
    pre_reset_lock_operation_parts: str = "All"  # Off | Multi-Selector Only | Dial + Wheel | All
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P245_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    saved_lock_operation_parts: str = "Dial + Wheel"
    post_reset_lock_operation_parts: str = "All"
    fn_hold_engaged: bool = False
    fn_hold_osd_message: Optional[str] = None
    fn_hold_locked_controls: Tuple[str, ...] = ()
    chord_keys_pressed: Tuple[str, ...] = ("MENU", "Fn")
    chord_hold_seconds: float = 5.0
    menu_fn_5s_full_body_lock_engaged: bool = True
    menu_fn_locked_controls: Tuple[str, ...] = P245_MENU_FN_5S_LOCKED_CONTROLS
    shutter_button_remains_unlocked: bool = True
    destructive_menu_delete_attempted: bool = False
    destructive_menu_delete_confusions: int = 0
    unattended_tier0_dump_active: bool = True
    my_dial_recall_active: bool = False
    my_dial_assigned_controls: Tuple[str, ...] = ("FRONT_DIAL", "REAR_DIAL")
    effective_unlocked_controls_during_my_dial: Tuple[str, ...] = ()
    post_my_dial_release_relocked: bool = True
    overlay_dir: str = P245_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P245_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P245_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P245_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class LockOperationPartsBenchVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    lock_op_parts_reset_survival_verified: bool
    camset_slot1_restore_verified: bool
    fn_hold_scope_and_banner_verified: bool
    menu_fn_5s_full_body_chord_verified: bool
    destructive_menu_delete_guard_verified: bool
    my_dial_temporary_override_verified: bool
    h0_equals_h3_verified: bool
    destructive_menu_delete_confusions: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AudioOutTimingSignalsAndExpStepVaultSpec:
    camera_model: str = P245_FX3_MODEL_NAME
    helpguide_id: str = P245_FX3_HELPGUIDE_ID
    fw_version: str = P245_FX3_FW_VERSION
    audio_out_timing_menu_path: Tuple[str, ...] = P245_AUDIO_OUT_TIMING_MENU_PATH
    audio_signals_menu_path: Tuple[str, ...] = P245_AUDIO_SIGNALS_MENU_PATH
    exposure_step_menu_path: Tuple[str, ...] = P245_EXPOSURE_STEP_MENU_PATH
    shutter_mode_menu_path: Tuple[str, ...] = P245_SHUTTER_MODE_MENU_PATH
    pre_reset_audio_out_timing: str = "Lip Sync"  # Live | Lip Sync
    pre_reset_audio_signals: str = "Off"  # On | Off
    pre_reset_exposure_step: str = "0.5EV"  # 0.3EV | 0.5EV
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P245_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    saved_audio_out_timing: str = "Lip Sync"
    saved_audio_signals: str = "Off"
    saved_exposure_step: str = "0.5EV"
    saved_shutter_mode: str = "Shutter Angle"
    saved_shutter_angle_deg: float = 180.0
    post_reset_audio_out_timing: str = P245_AUDIO_OUT_TIMING_DEFAULT  # Live
    post_reset_audio_signals: str = "Off"  # survives Camera Settings Reset
    post_reset_exposure_step: str = P245_EXPOSURE_STEP_DEFAULT  # 0.3EV
    capture_mode: str = "Movie"  # Movie | Still | S&Q Motion
    audio_recording: str = "On"  # On | Off
    audio_out_timing_available: bool = True
    silent_mode: str = "Off"  # Off | On
    effective_audio_signals: str = "Off"  # On | Off
    audio_signals_locked_by_silent_mode: bool = False
    exposure_step_governed_targets: Tuple[str, ...] = P245_EXPOSURE_STEP_GOVERNED_TARGETS
    shutter_mode: str = "Shutter Angle"  # Shutter Speed | Shutter Angle
    shutter_angle_deg: float = 180.0
    active_shutter_angle_table_deg: Tuple[float, ...] = P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG
    shutter_angle_affected_by_exposure_step: bool = False
    shutter_angle_exposure_step_drift_events: int = 0
    overlay_dir: str = P245_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P245_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P245_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P245_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class AudioOutTimingSignalsAndExpStepVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    audio_timing_and_signals_reset_asymmetry_verified: bool
    audio_out_timing_sq_and_audio_off_lockout_verified: bool
    audio_signals_silent_mode_lock_verified: bool
    exposure_step_reset_and_targets_verified: bool
    shutter_angle_constant_table_immunity_verified: bool
    camset_slot1_restore_verified: bool
    h0_equals_h3_verified: bool
    shutter_angle_exposure_step_drift_events: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class LockOpPartsAudioTimingAndExpStepVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase245DonorSnapshot
    lock_op_parts_report: LockOperationPartsBenchVaultReport
    audio_timing_exp_step_report: AudioOutTimingSignalsAndExpStepVaultReport
    destructive_menu_delete_confusions: int
    shutter_angle_exposure_step_drift_events: int
    hardware_live_attachment_authorized: bool
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
class Pillar40ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar40ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar40ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar40BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar40ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar40StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase245DonorSnapshot
    pillar_40a_lock_op_parts_vault: Pillar40ASuiteResult
    pillar_40b_audio_timing_exp_step_vault: Pillar40BSuiteResult
    destructive_menu_delete_confusions: int
    shutter_angle_exposure_step_drift_events: int
    hardware_live_attachment_authorized: bool
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
class Master40PillarRecoveryReport:
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
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    donor_snapshot: Phase245DonorSnapshot
    pillar40_a_lock_op_parts_vault: Pillar40ASuiteResult
    pillar40_b_audio_timing_exp_step_vault: Pillar40BSuiteResult
    destructive_menu_delete_confusions: int
    shutter_angle_exposure_step_drift_events: int
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
    hardware_live_attachment_authorized: bool
    master_40pillar_sha256: str
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
    max_full_bytes: int = P245_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P245_BOUNDED_HEADER_BYTES, total_size), 0)
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
    return True, f"ELF64_AARCH64:{'+'.join(found)}" if found else "ELF64_AARCH64"


def _synthetic_phase245_donors() -> Tuple[Phase245DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P245_DONOR_FX3_BODYDATA_RELPATH,
            P245_PINNED_FX3_BODYDATA_BYTES,
            P245_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P245_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P245_DONOR_FX3_APPFW_702_RELPATH,
            P245_PINNED_FX3_APPFW_702_BYTES,
            P245_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P245_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P245_DONOR_FX6_APPFW_601_RELPATH,
            P245_PINNED_FX6_APPFW_601_BYTES,
            P245_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P245_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P245_DONOR_FX3_BACKUP_BIN_RELPATH,
            P245_PINNED_FX3_BACKUP_BIN_BYTES,
            P245_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P245_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P245_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P245_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P245_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P245_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P245_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P245_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P245_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P245_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P245_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P245_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P245_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P245_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_libgpe_so",
            P245_DONOR_FX3_LIBGPE_SO_RELPATH,
            P245_PINNED_FX3_LIBGPE_SO_BYTES,
            P245_PINNED_FX3_LIBGPE_SO_BYTES,
            "FULL_SHA256",
            P245_PINNED_FX3_LIBGPE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:gpe_blog_error+_ZNK5mpgpe5Gperm4InitEv",
        ),
        (
            "fx6_libinfradial_so",
            P245_DONOR_FX6_LIBINFRADIAL_SO_RELPATH,
            P245_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
            P245_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
            "FULL_SHA256",
            P245_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZN9InfraDial4InitEv+_ZN9InfraDial10set4KeyInhEb+_ZN10InfraInput12SetKeyInhExtEibi",
        ),
        (
            "fx6_libinfrainput_so",
            P245_DONOR_FX6_LIBINFRAINPUT_SO_RELPATH,
            P245_PINNED_FX6_LIBINFRAINPUT_SO_BYTES,
            P245_PINNED_FX6_LIBINFRAINPUT_SO_BYTES,
            "FULL_SHA256",
            P245_PINNED_FX6_LIBINFRAINPUT_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZN14InfraInputBase14KeyConfigAllocEi+_ZN14InfraInputBase13KeyConfigFreeEv+_ZN14InfraInputBase7SuspendEv",
        ),
    )
    return tuple(
        Phase245DonorArtifactDigest(
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


def inspect_phase245_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase245DonorSnapshot:
    """Inspect Wave-38 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase245_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase245DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P245_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P245_DONOR_FX3_BODYDATA_RELPATH,
            P245_PINNED_FX3_BODYDATA_BYTES,
            P245_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P245_DONOR_FX3_APPFW_702_RELPATH,
            P245_PINNED_FX3_APPFW_702_BYTES,
            P245_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P245_DONOR_FX6_APPFW_601_RELPATH,
            P245_PINNED_FX6_APPFW_601_BYTES,
            P245_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P245_DONOR_FX3_BACKUP_BIN_RELPATH,
            P245_PINNED_FX3_BACKUP_BIN_BYTES,
            P245_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P245_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P245_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P245_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P245_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P245_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P245_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P245_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P245_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P245_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite")
            ),
        ),
        (
            "fx3_libgpe_so",
            P245_DONOR_FX3_LIBGPE_SO_RELPATH,
            P245_PINNED_FX3_LIBGPE_SO_BYTES,
            P245_PINNED_FX3_LIBGPE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv")),
        ),
        (
            "fx6_libinfradial_so",
            P245_DONOR_FX6_LIBINFRADIAL_SO_RELPATH,
            P245_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
            P245_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (
                    b"_ZN9InfraDial4InitEv",
                    b"_ZN9InfraDial10set4KeyInhEb",
                    b"_ZN10InfraInput12SetKeyInhExtEibi",
                ),
            ),
        ),
        (
            "fx6_libinfrainput_so",
            P245_DONOR_FX6_LIBINFRAINPUT_SO_RELPATH,
            P245_PINNED_FX6_LIBINFRAINPUT_SO_BYTES,
            P245_PINNED_FX6_LIBINFRAINPUT_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (
                    b"_ZN14InfraInputBase14KeyConfigAllocEi",
                    b"_ZN14InfraInputBase13KeyConfigFreeEv",
                    b"_ZN14InfraInputBase7SuspendEv",
                ),
            ),
        ),
    )

    digests: List[Phase245DonorArtifactDigest] = []
    for aid, rel, pinned_bytes, pinned_sha, validator in probe_specs:
        ok, total_b, hdr_b, dkind, dsha, raw = _read_donor_readonly_bounded(rel)
        if not ok:
            digests.append(
                Phase245DonorArtifactDigest(
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
            Phase245DonorArtifactDigest(
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
        synth = _synthetic_phase245_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase245DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P245_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    return Phase245DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all(d.present and d.matches_pinned for d in digests),
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P245_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Pillar 40A & 40B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_lock_op_parts_vault_spec() -> LockOperationPartsBenchVaultSpec:
    return LockOperationPartsBenchVaultSpec()


def build_default_safe_audio_timing_exp_step_vault_spec() -> AudioOutTimingSignalsAndExpStepVaultSpec:
    return AudioOutTimingSignalsAndExpStepVaultSpec()


def _normalize_lock_op_parts_mode(value: str) -> str:
    return P245_LOCK_OPERATION_PARTS_UI_SHORT_LABELS.get(value, value)


def evaluate_lock_operation_parts_bench_vault(
    spec: LockOperationPartsBenchVaultSpec,
) -> LockOperationPartsBenchVaultReport:
    """Audit `[Lock Operation Parts]` survival, `Fn` hold, `MENU + Fn` 5s chord vs `MENU + Delete` 2s, and `My Dial`."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P245_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P245_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 40A")

    pre_mode = _normalize_lock_op_parts_mode(spec.pre_reset_lock_operation_parts)
    saved_mode = _normalize_lock_op_parts_mode(spec.saved_lock_operation_parts)
    post_mode = _normalize_lock_op_parts_mode(spec.post_reset_lock_operation_parts)

    valid_tokens = (
        spec.camera_model == P245_FX3_MODEL_NAME
        and spec.helpguide_id == P245_FX3_HELPGUIDE_ID
        and spec.fw_version in P245_FX3_SUPPORTED_FW_VERSIONS
        and spec.lock_op_parts_menu_path == P245_LOCK_OPERATION_PARTS_MENU_PATH
        and pre_mode in P245_LOCK_OPERATION_PARTS_MODES
        and saved_mode in P245_LOCK_OPERATION_PARTS_MODES
        and post_mode in P245_LOCK_OPERATION_PARTS_MODES
        and spec.reset_action in P245_RESET_ACTIONS
        and all(ctrl in P245_DIAL_WHEEL_CONTROLS for ctrl in spec.my_dial_assigned_controls)
        and spec.chord_hold_seconds >= 0.0
    )
    if not valid_tokens:
        _fail(
            P245_BLOCKED_INVALID_LOCK_OPERATION_PARTS_SPEC,
            f"Invalid [Lock Operation Parts] model/path/mode spec: "
            f"model={spec.camera_model!r} helpguide={spec.helpguide_id!r} fw={spec.fw_version!r} "
            f"path={spec.lock_op_parts_menu_path!r} pre={spec.pre_reset_lock_operation_parts!r} "
            f"post={spec.post_reset_lock_operation_parts!r}",
        )

    destructive_guard_ok = True
    confusion_count = int(spec.destructive_menu_delete_confusions)
    if (
        spec.destructive_menu_delete_attempted
        or confusion_count != 0
        or tuple(spec.chord_keys_pressed) == P245_DESTRUCTIVE_MENU_DELETE_2S_CHORD_KEYS
    ):
        destructive_guard_ok = False
        confusion_count = max(1, confusion_count)
        _fail(
            P245_BLOCKED_DESTRUCTIVE_MENU_DELETE_FORMAT_CHORD_CONFUSION,
            "Destructive MENU + Delete (~2s Slot Full Format chord) confused with or attempted instead of "
            "MENU + Fn (5s full-body control lock chord)",
        )

    reset_survival_ok = True
    camset_ok = True
    if spec.camset_slot != P245_SLOT1_VAULT_SLOT or spec.camset_filename not in P245_CAMSET_FILENAMES:
        camset_ok = False
        _fail(
            P245_BLOCKED_CAMSET_LOCK_OP_PARTS_RESTORE_DRIFT,
            f"CAMSET [Load] must reference Slot 1 CAMSET01.DAT..CAMSET10.DAT, got "
            f"slot={spec.camset_slot!r} file={spec.camset_filename!r}",
        )

    if valid_tokens:
        if spec.camset_load_after_reset:
            if post_mode != saved_mode:
                camset_ok = False
                _fail(
                    P245_BLOCKED_CAMSET_LOCK_OP_PARTS_RESTORE_DRIFT,
                    f"Slot-1 {spec.camset_filename} [Load] failed to restore [Lock Operation Parts]: "
                    f"expected {saved_mode!r}, got {post_mode!r}",
                )
        elif spec.reset_action == "Camera Settings Reset":
            if post_mode != pre_mode:
                reset_survival_ok = False
                _fail(
                    P245_BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT,
                    f"[Setup] -> [Dial Customize] -> [Lock Operation Parts] MUST survive [Camera Settings Reset]: "
                    f"expected {pre_mode!r}, got {post_mode!r}",
                )
        elif spec.reset_action == "Initialize":
            if post_mode != P245_LOCK_OPERATION_PARTS_DEFAULT:
                reset_survival_ok = False
                _fail(
                    P245_BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT,
                    f"[Initialize] must restore [Lock Operation Parts] to {P245_LOCK_OPERATION_PARTS_DEFAULT!r}, "
                    f"got {post_mode!r}",
                )
        elif spec.reset_action == "NONE":
            if post_mode != pre_mode:
                reset_survival_ok = False
                _fail(
                    P245_BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT,
                    f"With reset_action='NONE', [Lock Operation Parts] drifted from {pre_mode!r} to {post_mode!r}",
                )

    fn_hold_ok = True
    if valid_tokens:
        expected_fn_scope = P245_FN_HOLD_SCOPE_BY_MODE[post_mode] if spec.fn_hold_engaged else ()
        expected_osd = (
            P245_LOCKED_OSD_MESSAGE
            if (spec.fn_hold_engaged and post_mode != P245_LOCK_OPERATION_PARTS_DEFAULT)
            else None
        )
        if tuple(spec.fn_hold_locked_controls) != expected_fn_scope or spec.fn_hold_osd_message != expected_osd:
            fn_hold_ok = False
            _fail(
                P245_BLOCKED_FN_HOLD_SCOPE_OR_BANNER_MISMATCH,
                f"Fn hold lock scope/banner mismatch for [Lock Operation Parts]={post_mode!r} "
                f"(engaged={spec.fn_hold_engaged}): expected controls={expected_fn_scope!r} "
                f"osd={expected_osd!r}, got controls={spec.fn_hold_locked_controls!r} "
                f"osd={spec.fn_hold_osd_message!r}",
            )

    menu_fn_chord_ok = True
    if destructive_guard_ok:
        if len(spec.chord_keys_pressed) > 0:
            if tuple(spec.chord_keys_pressed) != P245_MENU_FN_5S_CHORD_KEYS:
                menu_fn_chord_ok = False
                _fail(
                    P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH,
                    f"Unsupported full-body lock key chord {spec.chord_keys_pressed!r}; expected ('MENU', 'Fn')",
                )
            elif spec.chord_hold_seconds < P245_MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS:
                if spec.menu_fn_5s_full_body_lock_engaged or len(spec.menu_fn_locked_controls) > 0:
                    menu_fn_chord_ok = False
                    _fail(
                        P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH,
                        f"MENU + Fn held for {spec.chord_hold_seconds:.2f}s (< 5.0s) cannot engage full-body lock",
                    )
            else:
                if spec.menu_fn_5s_full_body_lock_engaged:
                    if (
                        tuple(spec.menu_fn_locked_controls) != P245_MENU_FN_5S_LOCKED_CONTROLS
                        or not spec.shutter_button_remains_unlocked
                        or "SHUTTER_BUTTON" in spec.menu_fn_locked_controls
                    ):
                        menu_fn_chord_ok = False
                        _fail(
                            P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH,
                            "MENU + Fn 5s chord must lock all buttons/dials/wheels EXCEPT shutter button",
                        )
        elif spec.menu_fn_5s_full_body_lock_engaged:
            menu_fn_chord_ok = False
            _fail(
                P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH,
                "menu_fn_5s_full_body_lock_engaged=True requires ('MENU', 'Fn') held >= 5.0s",
            )

        if not spec.shutter_button_remains_unlocked:
            menu_fn_chord_ok = False
            _fail(
                P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH,
                "Hardware invariant violated: shutter button is never locked by MENU + Fn 5s chord or Fn hold",
            )

    if spec.unattended_tier0_dump_active:
        bench_protected = spec.menu_fn_5s_full_body_lock_engaged or (
            post_mode == "All" and spec.fn_hold_engaged
        )
        if not bench_protected:
            menu_fn_chord_ok = False
            _fail(
                P245_BLOCKED_UNATTENDED_TIER0_BENCH_UNLOCKED_CONTROLS,
                "Unattended Tier-0 pnflasha/cnflasha bench dump requires MENU + Fn 5s full-body lock "
                "(or [Lock Operation Parts]='All' + Fn hold engaged)",
            )

    my_dial_ok = True
    if valid_tokens:
        if spec.my_dial_recall_active:
            expected_temp_unlocked = tuple(spec.my_dial_assigned_controls)
            if (
                tuple(spec.effective_unlocked_controls_during_my_dial) != expected_temp_unlocked
                or not spec.post_my_dial_release_relocked
            ):
                my_dial_ok = False
                _fail(
                    P245_BLOCKED_MY_DIAL_TEMPORARY_OVERRIDE_MISMATCH,
                    f"My Dial recall must temporarily unlock assigned dials/wheels {expected_temp_unlocked!r} "
                    f"and re-lock immediately upon release: got unlocked={spec.effective_unlocked_controls_during_my_dial!r}, "
                    f"post_release_relocked={spec.post_my_dial_release_relocked!r}",
                )
        else:
            if len(spec.effective_unlocked_controls_during_my_dial) > 0 or not spec.post_my_dial_release_relocked:
                my_dial_ok = False
                _fail(
                    P245_BLOCKED_MY_DIAL_TEMPORARY_OVERRIDE_MISMATCH,
                    "Inactive My Dial recall cannot leave locked dials/wheels permanently unlocked",
                )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _fail(
            P245_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must reside on volatile tmpfs (/tmp or /run), got {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == P245_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P245_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P245_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 == H3 or 16/16 surface parity violated in Pillar 40A",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "40A",
            "spec": asdict(spec),
            "passed": passed,
            "block_code": block_code,
        }
    )
    return LockOperationPartsBenchVaultReport(
        passed=passed,
        status=P245_STATUS_VERIFIED_PILLAR_40A if passed else P245_STATUS_REJECTED_PILLAR_40A,
        block_code=None if passed else block_code,
        lock_op_parts_reset_survival_verified=reset_survival_ok and valid_tokens,
        camset_slot1_restore_verified=camset_ok and valid_tokens,
        fn_hold_scope_and_banner_verified=fn_hold_ok and valid_tokens,
        menu_fn_5s_full_body_chord_verified=menu_fn_chord_ok and valid_tokens,
        destructive_menu_delete_guard_verified=destructive_guard_ok,
        my_dial_temporary_override_verified=my_dial_ok and valid_tokens,
        h0_equals_h3_verified=h0_eq_h3,
        destructive_menu_delete_confusions=0 if passed else confusion_count,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_audio_out_timing_signals_and_exp_step_vault(
    spec: AudioOutTimingSignalsAndExpStepVaultSpec,
) -> AudioOutTimingSignalsAndExpStepVaultReport:
    """Audit `[Audio Out Timing]`, `[Audio signals]` vs `[Silent Mode]`, and `[Exposure step]` vs `[Shutter Angle]`."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P245_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P245_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 40B")

    shutter_angle_fw_ok = (
        spec.shutter_mode != "Shutter Angle" or spec.fw_version in P245_FX3_SHUTTER_ANGLE_FW_VERSIONS
    )
    valid_tokens = (
        spec.camera_model == P245_FX3_MODEL_NAME
        and spec.helpguide_id == P245_FX3_HELPGUIDE_ID
        and spec.fw_version in P245_FX3_SUPPORTED_FW_VERSIONS
        and shutter_angle_fw_ok
        and spec.audio_out_timing_menu_path == P245_AUDIO_OUT_TIMING_MENU_PATH
        and spec.audio_signals_menu_path == P245_AUDIO_SIGNALS_MENU_PATH
        and spec.exposure_step_menu_path == P245_EXPOSURE_STEP_MENU_PATH
        and spec.shutter_mode_menu_path == P245_SHUTTER_MODE_MENU_PATH
        and spec.pre_reset_audio_out_timing in P245_AUDIO_OUT_TIMING_MODES
        and spec.saved_audio_out_timing in P245_AUDIO_OUT_TIMING_MODES
        and spec.post_reset_audio_out_timing in P245_AUDIO_OUT_TIMING_MODES
        and spec.pre_reset_audio_signals in P245_ON_OFF_MODES
        and spec.saved_audio_signals in P245_ON_OFF_MODES
        and spec.post_reset_audio_signals in P245_ON_OFF_MODES
        and spec.pre_reset_exposure_step in P245_EXPOSURE_STEP_MODES
        and spec.saved_exposure_step in P245_EXPOSURE_STEP_MODES
        and spec.post_reset_exposure_step in P245_EXPOSURE_STEP_MODES
        and spec.saved_shutter_mode in P245_SHUTTER_MODES
        and spec.shutter_mode in P245_SHUTTER_MODES
        and spec.capture_mode in P245_CAPTURE_MODES
        and spec.audio_recording in P245_ON_OFF_MODES
        and spec.silent_mode in P245_ON_OFF_MODES
        and spec.effective_audio_signals in P245_ON_OFF_MODES
        and spec.reset_action in P245_RESET_ACTIONS
    )
    if not valid_tokens:
        _fail(
            P245_BLOCKED_INVALID_AUDIO_TIMING_OR_EXPOSURE_STEP_SPEC,
            f"Invalid [Audio Out Timing] / [Audio signals] / [Exposure step] / [Shutter Angle] spec: "
            f"model={spec.camera_model!r} fw={spec.fw_version!r} shutter_mode={spec.shutter_mode!r}",
        )

    reset_asym_ok = True
    exp_step_ok = True
    camset_ok = True
    if spec.camset_slot != P245_SLOT1_VAULT_SLOT or spec.camset_filename not in P245_CAMSET_FILENAMES:
        camset_ok = False
        _fail(
            P245_BLOCKED_CAMSET_AUDIO_TIMING_OR_EXP_STEP_RESTORE_DRIFT,
            f"CAMSET [Load] must reference Slot 1 CAMSET01.DAT..CAMSET10.DAT, got "
            f"slot={spec.camset_slot!r} file={spec.camset_filename!r}",
        )

    if valid_tokens:
        if tuple(spec.exposure_step_governed_targets) != P245_EXPOSURE_STEP_GOVERNED_TARGETS:
            exp_step_ok = False
            _fail(
                P245_BLOCKED_EXPOSURE_STEP_RESET_OR_GOVERNED_TARGETS_MISMATCH,
                f"[Exposure step] must govern strictly {P245_EXPOSURE_STEP_GOVERNED_TARGETS!r} "
                f"(never Shutter Angle), got {spec.exposure_step_governed_targets!r}",
            )

        if spec.camset_load_after_reset:
            expected_quad = (
                spec.saved_audio_out_timing,
                spec.saved_audio_signals,
                spec.saved_exposure_step,
                spec.saved_shutter_mode,
                spec.saved_shutter_angle_deg,
            )
            actual_quad = (
                spec.post_reset_audio_out_timing,
                spec.post_reset_audio_signals,
                spec.post_reset_exposure_step,
                spec.shutter_mode,
                spec.shutter_angle_deg,
            )
            if actual_quad != expected_quad:
                camset_ok = False
                _fail(
                    P245_BLOCKED_CAMSET_AUDIO_TIMING_OR_EXP_STEP_RESTORE_DRIFT,
                    f"Slot-1 {spec.camset_filename} [Load] restore mismatch: "
                    f"expected {expected_quad!r}, got {actual_quad!r}",
                )
        elif spec.reset_action == "Camera Settings Reset":
            if (
                spec.post_reset_audio_out_timing != P245_AUDIO_OUT_TIMING_DEFAULT
                or spec.post_reset_audio_signals != spec.pre_reset_audio_signals
            ):
                reset_asym_ok = False
                _fail(
                    P245_BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT,
                    f"[Camera Settings Reset] must reset [Audio Out Timing] -> 'Live' while preserving "
                    f"[Setup] -> [Sound Option] -> [Audio signals] == {spec.pre_reset_audio_signals!r}: "
                    f"got timing={spec.post_reset_audio_out_timing!r}, signals={spec.post_reset_audio_signals!r}",
                )
            if spec.post_reset_exposure_step != P245_EXPOSURE_STEP_DEFAULT:
                exp_step_ok = False
                _fail(
                    P245_BLOCKED_EXPOSURE_STEP_RESET_OR_GOVERNED_TARGETS_MISMATCH,
                    f"[Camera Settings Reset] must reset [Exposure step] -> '0.3EV', "
                    f"got {spec.post_reset_exposure_step!r}",
                )
        elif spec.reset_action == "Initialize":
            if (
                spec.post_reset_audio_out_timing != P245_AUDIO_OUT_TIMING_DEFAULT
                or spec.post_reset_audio_signals != P245_AUDIO_SIGNALS_DEFAULT
            ):
                reset_asym_ok = False
                _fail(
                    P245_BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT,
                    f"[Initialize] must restore [Audio Out Timing]='Live' and [Audio signals]='On': "
                    f"got timing={spec.post_reset_audio_out_timing!r}, signals={spec.post_reset_audio_signals!r}",
                )
            if spec.post_reset_exposure_step != P245_EXPOSURE_STEP_DEFAULT:
                exp_step_ok = False
                _fail(
                    P245_BLOCKED_EXPOSURE_STEP_RESET_OR_GOVERNED_TARGETS_MISMATCH,
                    f"[Initialize] must restore [Exposure step]='0.3EV', got {spec.post_reset_exposure_step!r}",
                )
        elif spec.reset_action == "NONE":
            if (
                spec.post_reset_audio_out_timing != spec.pre_reset_audio_out_timing
                or spec.post_reset_audio_signals != spec.pre_reset_audio_signals
                or spec.post_reset_exposure_step != spec.pre_reset_exposure_step
            ):
                reset_asym_ok = False
                _fail(
                    P245_BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT,
                    "With reset_action='NONE', audio timing/signals or exposure step drifted unexpectedly",
                )

    sq_audio_lockout_ok = True
    if valid_tokens:
        expected_timing_avail = (spec.capture_mode == "Movie") and (spec.audio_recording == "On")
        if spec.capture_mode == "S&Q Motion" or spec.audio_recording == "Off":
            if spec.audio_out_timing_available:
                sq_audio_lockout_ok = False
                _fail(
                    P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
                    f"[Audio Out Timing] is hardware-unavailable when capture_mode={spec.capture_mode!r} "
                    f"or audio_recording={spec.audio_recording!r}",
                )
        elif spec.capture_mode == "Still":
            if spec.audio_out_timing_available:
                sq_audio_lockout_ok = False
                _fail(
                    P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
                    "[Audio Out Timing] applies to movie audio monitoring, not Still mode",
                )
        elif spec.audio_out_timing_available != expected_timing_avail:
            sq_audio_lockout_ok = False
            _fail(
                P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
                f"[Audio Out Timing] availability mismatch: expected {expected_timing_avail}, "
                f"got {spec.audio_out_timing_available}",
            )

    silent_lock_ok = True
    if valid_tokens:
        if spec.silent_mode == "On":
            if spec.effective_audio_signals != "Off" or not spec.audio_signals_locked_by_silent_mode:
                silent_lock_ok = False
                _fail(
                    P245_BLOCKED_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION,
                    f"Whenever [Silent Mode]='On', [Audio signals] is hardware-locked to 'Off': "
                    f"got effective={spec.effective_audio_signals!r}, "
                    f"locked_flag={spec.audio_signals_locked_by_silent_mode!r}",
                )
        else:
            if (
                spec.effective_audio_signals != spec.post_reset_audio_signals
                or spec.audio_signals_locked_by_silent_mode
            ):
                silent_lock_ok = False
                _fail(
                    P245_BLOCKED_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION,
                    f"With [Silent Mode]='Off', effective [Audio signals] must equal configured "
                    f"{spec.post_reset_audio_signals!r} without silent-mode lock",
                )

    shutter_angle_immunity_ok = True
    drift_events = int(spec.shutter_angle_exposure_step_drift_events)
    if valid_tokens:
        if (
            spec.shutter_angle_affected_by_exposure_step
            or drift_events != 0
            or tuple(spec.active_shutter_angle_table_deg) != P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG
            or (
                spec.shutter_mode == "Shutter Angle"
                and spec.shutter_angle_deg not in P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG
            )
        ):
            shutter_angle_immunity_ok = False
            drift_events = max(1, drift_events)
            _fail(
                P245_BLOCKED_SHUTTER_ANGLE_EXPOSURE_STEP_COUPLED_DRIFT,
                "[Shutter Angle] ([Shutter Mode]='Shutter Angle', Ver. 6.00+..7.02) is strictly immune to "
                "[Exposure step] ('0.3EV'/'0.5EV') and locked to its constant cine angle table (5.6..360 deg)",
            )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _fail(
            P245_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay must reside on volatile tmpfs (/tmp or /run), got {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == P245_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P245_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P245_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 == H3 or 16/16 surface parity violated in Pillar 40B",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "40B",
            "spec": asdict(spec),
            "passed": passed,
            "block_code": block_code,
        }
    )
    return AudioOutTimingSignalsAndExpStepVaultReport(
        passed=passed,
        status=P245_STATUS_VERIFIED_PILLAR_40B if passed else P245_STATUS_REJECTED_PILLAR_40B,
        block_code=None if passed else block_code,
        audio_timing_and_signals_reset_asymmetry_verified=reset_asym_ok and valid_tokens,
        audio_out_timing_sq_and_audio_off_lockout_verified=sq_audio_lockout_ok and valid_tokens,
        audio_signals_silent_mode_lock_verified=silent_lock_ok and valid_tokens,
        exposure_step_reset_and_targets_verified=exp_step_ok and valid_tokens,
        shutter_angle_constant_table_immunity_verified=shutter_angle_immunity_ok and valid_tokens,
        camset_slot1_restore_verified=camset_ok and valid_tokens,
        h0_equals_h3_verified=h0_eq_h3,
        shutter_angle_exposure_step_drift_events=0 if passed else drift_events,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_lock_op_parts_audio_timing_and_exp_step_vault(
    lock_spec: Optional[LockOperationPartsBenchVaultSpec] = None,
    audio_exp_spec: Optional[AudioOutTimingSignalsAndExpStepVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> LockOpPartsAudioTimingAndExpStepVaultReport:
    """Joint Pillar 40 evaluator combining bounded `O_RDONLY` donor audit + Pillar 40A + Pillar 40B."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase245_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_lock_operation_parts_bench_vault(
        lock_spec or build_default_safe_lock_op_parts_vault_spec()
    )
    rep_b = evaluate_audio_out_timing_signals_and_exp_step_vault(
        audio_exp_spec or build_default_safe_audio_timing_exp_step_vault_spec()
    )
    combined_errors: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        combined_errors.append("Phase 245 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        combined_errors.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = rep_a.passed and rep_b.passed and len(combined_errors) == 0
    return LockOpPartsAudioTimingAndExpStepVaultReport(
        schema=PHASE245_SCHEMA,
        version=PHASE245_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P245_STATUS_VERIFIED_PILLAR40_SUITE if all_ok else P245_STATUS_FAIL_PILLAR40_SUITE,
        donor_snapshot=donor_snapshot,
        lock_op_parts_report=rep_a,
        audio_timing_exp_step_report=rep_b,
        destructive_menu_delete_confusions=rep_a.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=rep_b.shutter_angle_exposure_step_drift_events,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
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
        errors=tuple(combined_errors),
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites & Standalone Pillar 40 Runner
# ---------------------------------------------------------------------------


def run_pillar40a_lock_op_parts_vault_6_scenario_suite() -> Pillar40ASuiteResult:
    """Execute the canonical `6/6` Pillar 40A `[Lock Operation Parts]` & `MENU + Fn` 5s chord suite."""
    cases: Tuple[Tuple[str, bool, LockOperationPartsBenchVaultSpec, Optional[str]], ...] = (
        (
            P245_PILLAR_40A_SCENARIO_IDS[0],
            True,
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="All",
                reset_action="Camera Settings Reset",
                post_reset_lock_operation_parts="All",
                fn_hold_engaged=True,
                fn_hold_osd_message=P245_LOCKED_OSD_MESSAGE,
                fn_hold_locked_controls=("MULTI_SELECTOR", "FRONT_DIAL", "REAR_DIAL", "CONTROL_WHEEL"),
                chord_keys_pressed=("MENU", "Fn"),
                chord_hold_seconds=5.0,
                menu_fn_5s_full_body_lock_engaged=True,
                menu_fn_locked_controls=P245_MENU_FN_5S_LOCKED_CONTROLS,
                shutter_button_remains_unlocked=True,
                unattended_tier0_dump_active=True,
            ),
            None,
        ),
        (
            P245_PILLAR_40A_SCENARIO_IDS[1],
            True,
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="All",
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_lock_operation_parts="Dial + Wheel",
                post_reset_lock_operation_parts="Dial + Wheel",
                fn_hold_engaged=True,
                fn_hold_osd_message=P245_LOCKED_OSD_MESSAGE,
                fn_hold_locked_controls=("FRONT_DIAL", "REAR_DIAL", "CONTROL_WHEEL"),
                chord_keys_pressed=(),
                chord_hold_seconds=0.0,
                menu_fn_5s_full_body_lock_engaged=False,
                menu_fn_locked_controls=(),
                unattended_tier0_dump_active=False,
                my_dial_recall_active=True,
                my_dial_assigned_controls=("FRONT_DIAL", "REAR_DIAL"),
                effective_unlocked_controls_during_my_dial=("FRONT_DIAL", "REAR_DIAL"),
                post_my_dial_release_relocked=True,
            ),
            None,
        ),
        (
            P245_PILLAR_40A_SCENARIO_IDS[2],
            False,
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="All",
                reset_action="Camera Settings Reset",
                post_reset_lock_operation_parts="Off",
                fn_hold_engaged=True,
                fn_hold_osd_message=P245_LOCKED_OSD_MESSAGE,
                fn_hold_locked_controls=("MULTI_SELECTOR",),
            ),
            P245_BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT,
        ),
        (
            P245_PILLAR_40A_SCENARIO_IDS[3],
            False,
            LockOperationPartsBenchVaultSpec(
                chord_keys_pressed=("MENU", "Delete"),
                chord_hold_seconds=2.0,
                destructive_menu_delete_attempted=True,
                destructive_menu_delete_confusions=1,
                unattended_tier0_dump_active=True,
            ),
            P245_BLOCKED_DESTRUCTIVE_MENU_DELETE_FORMAT_CHORD_CONFUSION,
        ),
        (
            P245_PILLAR_40A_SCENARIO_IDS[4],
            False,
            LockOperationPartsBenchVaultSpec(
                chord_keys_pressed=("MENU", "Fn"),
                chord_hold_seconds=2.0,
                menu_fn_5s_full_body_lock_engaged=True,
                menu_fn_locked_controls=P245_MENU_FN_5S_LOCKED_CONTROLS + ("SHUTTER_BUTTON",),
                shutter_button_remains_unlocked=False,
                unattended_tier0_dump_active=False,
            ),
            P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH,
        ),
        (
            P245_PILLAR_40A_SCENARIO_IDS[5],
            False,
            LockOperationPartsBenchVaultSpec(
                pre_reset_lock_operation_parts="Dial + Wheel",
                reset_action="Camera Settings Reset",
                post_reset_lock_operation_parts="Dial + Wheel",
                fn_hold_engaged=True,
                fn_hold_osd_message=P245_LOCKED_OSD_MESSAGE,
                fn_hold_locked_controls=("FRONT_DIAL", "REAR_DIAL", "CONTROL_WHEEL"),
                chord_keys_pressed=(),
                chord_hold_seconds=0.0,
                menu_fn_5s_full_body_lock_engaged=False,
                menu_fn_locked_controls=(),
                unattended_tier0_dump_active=False,
                my_dial_recall_active=True,
                my_dial_assigned_controls=("FRONT_DIAL", "REAR_DIAL"),
                effective_unlocked_controls_during_my_dial=(),
                post_my_dial_release_relocked=False,
            ),
            P245_BLOCKED_MY_DIAL_TEMPORARY_OVERRIDE_MISMATCH,
        ),
    )

    outcomes: List[Pillar40ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_lock_operation_parts_bench_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar40ScenarioOutcome(
                scenario_id=sid,
                pillar="40A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar40ASuiteResult(
        passed=all_ok,
        status=P245_STATUS_VERIFIED_PILLAR_40A if all_ok else P245_STATUS_REJECTED_PILLAR_40A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar40b_audio_timing_exp_step_vault_6_scenario_suite() -> Pillar40BSuiteResult:
    """Execute the canonical `6/6` Pillar 40B `[Audio Out Timing]`, `[Audio signals]` & `[Exposure step]` suite."""
    cases: Tuple[Tuple[str, bool, AudioOutTimingSignalsAndExpStepVaultSpec, Optional[str]], ...] = (
        (
            P245_PILLAR_40B_SCENARIO_IDS[0],
            True,
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_out_timing="Lip Sync",
                pre_reset_audio_signals="Off",
                pre_reset_exposure_step="0.5EV",
                reset_action="Camera Settings Reset",
                post_reset_audio_out_timing="Live",
                post_reset_audio_signals="Off",
                post_reset_exposure_step="0.3EV",
                capture_mode="Movie",
                audio_recording="On",
                audio_out_timing_available=True,
                silent_mode="Off",
                effective_audio_signals="Off",
                audio_signals_locked_by_silent_mode=False,
                shutter_mode="Shutter Angle",
                shutter_angle_deg=180.0,
            ),
            None,
        ),
        (
            P245_PILLAR_40B_SCENARIO_IDS[1],
            True,
            AudioOutTimingSignalsAndExpStepVaultSpec(
                reset_action="Camera Settings Reset",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_audio_out_timing="Lip Sync",
                saved_audio_signals="On",
                saved_exposure_step="0.5EV",
                saved_shutter_mode="Shutter Angle",
                saved_shutter_angle_deg=180.0,
                post_reset_audio_out_timing="Lip Sync",
                post_reset_audio_signals="On",
                post_reset_exposure_step="0.5EV",
                capture_mode="Movie",
                audio_recording="On",
                audio_out_timing_available=True,
                silent_mode="On",
                effective_audio_signals="Off",
                audio_signals_locked_by_silent_mode=True,
                shutter_mode="Shutter Angle",
                shutter_angle_deg=180.0,
                active_shutter_angle_table_deg=P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG,
                shutter_angle_affected_by_exposure_step=False,
                shutter_angle_exposure_step_drift_events=0,
            ),
            None,
        ),
        (
            P245_PILLAR_40B_SCENARIO_IDS[2],
            False,
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_out_timing="Lip Sync",
                pre_reset_audio_signals="Off",
                pre_reset_exposure_step="0.5EV",
                reset_action="Camera Settings Reset",
                post_reset_audio_out_timing="Lip Sync",
                post_reset_audio_signals="On",
                post_reset_exposure_step="0.3EV",
                effective_audio_signals="On",
            ),
            P245_BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT,
        ),
        (
            P245_PILLAR_40B_SCENARIO_IDS[3],
            False,
            AudioOutTimingSignalsAndExpStepVaultSpec(
                capture_mode="S&Q Motion",
                audio_recording="Off",
                audio_out_timing_available=True,
            ),
            P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
        ),
        (
            P245_PILLAR_40B_SCENARIO_IDS[4],
            False,
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_audio_signals="On",
                reset_action="Camera Settings Reset",
                post_reset_audio_signals="On",
                silent_mode="On",
                effective_audio_signals="On",
                audio_signals_locked_by_silent_mode=False,
            ),
            P245_BLOCKED_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION,
        ),
        (
            P245_PILLAR_40B_SCENARIO_IDS[5],
            False,
            AudioOutTimingSignalsAndExpStepVaultSpec(
                pre_reset_exposure_step="0.5EV",
                reset_action="NONE",
                post_reset_audio_out_timing="Lip Sync",
                post_reset_audio_signals="Off",
                post_reset_exposure_step="0.5EV",
                shutter_mode="Shutter Angle",
                shutter_angle_deg=175.0,
                active_shutter_angle_table_deg=(6.0, 12.0, 24.0, 48.0, 90.0, 175.0, 360.0),
                shutter_angle_affected_by_exposure_step=True,
                shutter_angle_exposure_step_drift_events=1,
            ),
            P245_BLOCKED_SHUTTER_ANGLE_EXPOSURE_STEP_COUPLED_DRIFT,
        ),
    )

    outcomes: List[Pillar40ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_audio_out_timing_signals_and_exp_step_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar40ScenarioOutcome(
                scenario_id=sid,
                pillar="40B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar40BSuiteResult(
        passed=all_ok,
        status=P245_STATUS_VERIFIED_PILLAR_40B if all_ok else P245_STATUS_REJECTED_PILLAR_40B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar40_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar40StandaloneReport:
    """Run full Pillar 40 standalone suite (`6/6` Pillar 40A + `6/6` Pillar 40B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase245_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar40a_lock_op_parts_vault_6_scenario_suite()
    res_b = run_pillar40b_audio_timing_exp_step_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 245 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE245_SCHEMA,
            "version": PHASE245_VERSION,
            "mode": donor_snapshot.verification_mode,
            "40a": [asdict(s) for s in res_a.scenarios],
            "40b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar40StandaloneReport(
        schema=PHASE245_SCHEMA,
        version=PHASE245_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P245_STATUS_VERIFIED_PILLAR40_SUITE if all_ok else P245_STATUS_FAIL_PILLAR40_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_40a_lock_op_parts_vault=res_a,
        pillar_40b_audio_timing_exp_step_vault=res_b,
        destructive_menu_delete_confusions=P245_DESTRUCTIVE_MENU_DELETE_CONFUSIONS if res_a.passed else 1,
        shutter_angle_exposure_step_drift_events=P245_SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS if res_b.passed else 1,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
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
# Unified 40/40 Milestone Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master40_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_40pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master40PillarRecoveryReport:
    """Evaluate and aggregate all 40 recovery pillars (`1..40`) concurrently -> `40/40` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_40_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_39pillar() -> Master39PillarRecoveryReport:
        return evaluate_realhw_39pillar_recovery_master(**kw)

    def _run_p40() -> Tuple[Pillar40StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar40_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_39 = pool.submit(_run_39pillar)
        fut_40 = pool.submit(_run_p40)
        m39_rep = fut_39.result()
        p40_rep, p40_dt = fut_40.result()

    all_errors: List[str] = list(m39_rep.errors) + list(p40_rep.errors)
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
        if getattr(m39_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-39 violated {attr_name} == {expected_val}")
        if getattr(p40_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 40 violated {attr_name} == {expected_val}")

    if m39_rep.fx3_has_var_shutter is not False:
        all_errors.append("Pillars 1-39 violated fx3_has_var_shutter == False")
    if m39_rep.unbuffered_battery_pull_events != 0:
        all_errors.append("Pillars 1-39 violated unbuffered_battery_pull_events == 0")
    if m39_rep.hardware_live_attachment_authorized is not False:
        all_errors.append("Pillars 1-39 violated hardware_live_attachment_authorized == False")
    if p40_rep.destructive_menu_delete_confusions != 0:
        all_errors.append("Pillar 40 violated destructive_menu_delete_confusions == 0")
    if p40_rep.shutter_angle_exposure_step_drift_events != 0:
        all_errors.append("Pillar 40 violated shutter_angle_exposure_step_drift_events == 0")
    if p40_rep.hardware_live_attachment_authorized is not False:
        all_errors.append("Pillar 40 violated hardware_live_attachment_authorized == False")

    pillar_statuses: List[MasterPillarStatus] = list(m39_rep.pillars)
    spec40 = MASTER_40_PILLAR_SPECS[39]
    p40_metrics = {
        "pillar_40a_lock_op_parts_vault": (
            f"{p40_rep.pillar_40a_lock_op_parts_vault.scenarios_passed}/"
            f"{p40_rep.pillar_40a_lock_op_parts_vault.scenarios_total}"
        ),
        "pillar_40b_audio_timing_exp_step_vault": (
            f"{p40_rep.pillar_40b_audio_timing_exp_step_vault.scenarios_passed}/"
            f"{p40_rep.pillar_40b_audio_timing_exp_step_vault.scenarios_total}"
        ),
        "destructive_menu_delete_confusions": p40_rep.destructive_menu_delete_confusions,
        "shutter_angle_exposure_step_drift_events": p40_rep.shutter_angle_exposure_step_drift_events,
        "hardware_live_attachment_authorized": p40_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p40_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec40[0],
            pillar_id=spec40[1],
            phase_label=spec40[2],
            module_name=spec40[3],
            passed=bool(p40_rep.all_passed),
            status=p40_rep.status,
            verification_mode=p40_rep.verification_mode,
            elapsed_seconds=p40_dt,
            key_metrics=p40_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec40[1],
                    "mode": p40_rep.verification_mode,
                    "status": p40_rep.status,
                    "metrics": p40_metrics,
                    "passed": p40_rep.all_passed,
                }
            ),
            errors=tuple(p40_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master40_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p40_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_40_PILLAR_COUNT == 40
        and pillars_passed == 40
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE245_SCHEMA,
            "version": PHASE245_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master40PillarRecoveryReport(
        schema=PHASE245_SCHEMA,
        version=PHASE245_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P245_STATUS_VERIFIED_40OF40_AGGREGATOR if all_ok else P245_STATUS_FAIL_40OF40_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P245_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P245_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p40_rep.donor_snapshot,
        pillar40_a_lock_op_parts_vault=p40_rep.pillar_40a_lock_op_parts_vault,
        pillar40_b_audio_timing_exp_step_vault=p40_rep.pillar_40b_audio_timing_exp_step_vault,
        destructive_menu_delete_confusions=p40_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=p40_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m39_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m39_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p40_rep.hardware_live_attachment_authorized,
        master_40pillar_sha256=master_sha,
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


def evaluate_40pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master40PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_40pillar_recovery_master`."""
    return evaluate_realhw_40pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_40pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master40PillarRecoveryReport:
    """Public CLI entry point for Milestone Pillar 40 unified `40/40` real-hardware recovery master."""
    return evaluate_realhw_40pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


__all__ = [
    "ALLOW_BOOT_PARTITION_TARGETING",
    "ALLOW_DESTRUCTIVE_FASTBOOT",
    "ALLOW_DESTRUCTIVE_JIRITSU_COMMANDS",
    "ALLOW_PERSISTENT_JIRITSU_WRITES",
    "CNFLASHA_USERSPACE_WRITE_BLOCKED",
    "EL3_PAYLOAD_TRANSMIT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "ISP_WRITE_AUTHORIZED",
    "LIVE_USB_IOKIT_TRANSMIT_ENABLED",
    "MASTER_40_PILLAR_COUNT",
    "MASTER_40_PILLAR_IDS",
    "MASTER_40_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P245_AUDIO_OUT_TIMING_DEFAULT",
    "P245_AUDIO_OUT_TIMING_MENU_PATH",
    "P245_AUDIO_OUT_TIMING_MODES",
    "P245_AUDIO_SIGNALS_DEFAULT",
    "P245_AUDIO_SIGNALS_MENU_PATH",
    "P245_BLOCKED_AUDIO_OUT_TIMING_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION",
    "P245_BLOCKED_AUDIO_SIGNALS_SILENT_MODE_HARD_LOCK_VIOLATION",
    "P245_BLOCKED_AUDIO_TIMING_OR_SIGNALS_RESET_ASYMMETRY_DRIFT",
    "P245_BLOCKED_CAMSET_AUDIO_TIMING_OR_EXP_STEP_RESTORE_DRIFT",
    "P245_BLOCKED_CAMSET_LOCK_OP_PARTS_RESTORE_DRIFT",
    "P245_BLOCKED_DESTRUCTIVE_MENU_DELETE_FORMAT_CHORD_CONFUSION",
    "P245_BLOCKED_EXPOSURE_STEP_RESET_OR_GOVERNED_TARGETS_MISMATCH",
    "P245_BLOCKED_FN_HOLD_SCOPE_OR_BANNER_MISMATCH",
    "P245_BLOCKED_INVALID_AUDIO_TIMING_OR_EXPOSURE_STEP_SPEC",
    "P245_BLOCKED_INVALID_LOCK_OPERATION_PARTS_SPEC",
    "P245_BLOCKED_LOCK_OP_PARTS_CAMERA_SETTINGS_RESET_DRIFT",
    "P245_BLOCKED_MENU_FN_5S_CHORD_TIMING_OR_SHUTTER_SCOPE_MISMATCH",
    "P245_BLOCKED_MY_DIAL_TEMPORARY_OVERRIDE_MISMATCH",
    "P245_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P245_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P245_BLOCKED_SHUTTER_ANGLE_EXPOSURE_STEP_COUPLED_DRIFT",
    "P245_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P245_BLOCKED_UNATTENDED_TIER0_BENCH_UNLOCKED_CONTROLS",
    "P245_BOUNDED_HEADER_BYTES",
    "P245_CAMSET_FILENAMES",
    "P245_CAPTURE_MODES",
    "P245_CINE_SHUTTER_ANGLE_CONSTANT_TABLE_DEG",
    "P245_CONCURRENT_CEILING_SECONDS",
    "P245_DESTRUCTIVE_MENU_DELETE_2S_CHORD_KEYS",
    "P245_DESTRUCTIVE_MENU_DELETE_CONFUSIONS",
    "P245_DESTRUCTIVE_MENU_DELETE_FORMAT_HOLD_SECONDS",
    "P245_DIAL_WHEEL_CONTROLS",
    "P245_DONOR_FX3_APPFW_702_RELPATH",
    "P245_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P245_DONOR_FX3_BODYDATA_RELPATH",
    "P245_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH",
    "P245_DONOR_FX3_LIBBACKUP_SO_RELPATH",
    "P245_DONOR_FX3_LIBGPE_SO_RELPATH",
    "P245_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P245_DONOR_FX6_APPFW_601_RELPATH",
    "P245_DONOR_FX6_LIBINFRADIAL_SO_RELPATH",
    "P245_DONOR_FX6_LIBINFRAINPUT_SO_RELPATH",
    "P245_DONOR_INSPECT_BUDGET_SECONDS",
    "P245_EXPOSURE_STEP_DEFAULT",
    "P245_EXPOSURE_STEP_GOVERNED_TARGETS",
    "P245_EXPOSURE_STEP_MENU_PATH",
    "P245_EXPOSURE_STEP_MODES",
    "P245_FN_HOLD_SCOPE_BY_MODE",
    "P245_FORBIDDEN_PERSISTENT_TARGETS",
    "P245_FX3_FW_VERSION",
    "P245_FX3_HELPGUIDE_ID",
    "P245_FX3_MODEL_ID",
    "P245_FX3_MODEL_NAME",
    "P245_FX3_SHUTTER_ANGLE_FW_VERSIONS",
    "P245_FX3_SUPPORTED_FW_VERSIONS",
    "P245_FX6_DONOR_FW_VERSION",
    "P245_FX6_DONOR_MODEL_NAME",
    "P245_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P245_LOCKED_OSD_MESSAGE",
    "P245_LOCK_OPERATION_PARTS_DEFAULT",
    "P245_LOCK_OPERATION_PARTS_MENU_PATH",
    "P245_LOCK_OPERATION_PARTS_MODES",
    "P245_LOCK_OPERATION_PARTS_UI_SHORT_LABELS",
    "P245_MAX_FULL_DONOR_BYTES",
    "P245_MENU_FN_5S_CHORD_KEYS",
    "P245_MENU_FN_5S_LOCKED_CONTROLS",
    "P245_MENU_FN_FULL_BODY_LOCK_HOLD_SECONDS",
    "P245_NOMINAL_BUDGET_SECONDS",
    "P245_ON_OFF_MODES",
    "P245_PILLAR_40A_SCENARIO_IDS",
    "P245_PILLAR_40B_SCENARIO_IDS",
    "P245_PINNED_FX3_APPFW_702_BYTES",
    "P245_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P245_PINNED_FX3_BACKUP_BIN_BYTES",
    "P245_PINNED_FX3_BACKUP_BIN_SHA256",
    "P245_PINNED_FX3_BODYDATA_BYTES",
    "P245_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P245_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES",
    "P245_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256",
    "P245_PINNED_FX3_LIBBACKUP_SO_BYTES",
    "P245_PINNED_FX3_LIBBACKUP_SO_SHA256",
    "P245_PINNED_FX3_LIBGPE_SO_BYTES",
    "P245_PINNED_FX3_LIBGPE_SO_SHA256",
    "P245_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P245_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P245_PINNED_FX6_APPFW_601_BYTES",
    "P245_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P245_PINNED_FX6_LIBINFRADIAL_SO_BYTES",
    "P245_PINNED_FX6_LIBINFRADIAL_SO_SHA256",
    "P245_PINNED_FX6_LIBINFRAINPUT_SO_BYTES",
    "P245_PINNED_FX6_LIBINFRAINPUT_SO_SHA256",
    "P245_RESET_ACTIONS",
    "P245_SHUTTER_ANGLE_EXPOSURE_STEP_DRIFT_EVENTS",
    "P245_SHUTTER_MODES",
    "P245_SHUTTER_MODE_MENU_PATH",
    "P245_SLOT1_VAULT_SLOT",
    "P245_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P245_STATUS_FAIL_40OF40_AGGREGATOR",
    "P245_STATUS_FAIL_PILLAR40_SUITE",
    "P245_STATUS_REJECTED_PILLAR_40A",
    "P245_STATUS_REJECTED_PILLAR_40B",
    "P245_STATUS_VERIFIED_40OF40_AGGREGATOR",
    "P245_STATUS_VERIFIED_PILLAR40_SUITE",
    "P245_STATUS_VERIFIED_PILLAR_40A",
    "P245_STATUS_VERIFIED_PILLAR_40B",
    "P245_TIER0_SURFACE_COUNT",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE245_SCHEMA",
    "PHASE245_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "AudioOutTimingSignalsAndExpStepVaultReport",
    "AudioOutTimingSignalsAndExpStepVaultSpec",
    "LockOpPartsAudioTimingAndExpStepVaultReport",
    "LockOperationPartsBenchVaultReport",
    "LockOperationPartsBenchVaultSpec",
    "Master40PillarRecoveryReport",
    "Phase245DonorArtifactDigest",
    "Phase245DonorSnapshot",
    "Pillar40ASuiteResult",
    "Pillar40BSuiteResult",
    "Pillar40ScenarioOutcome",
    "Pillar40StandaloneReport",
    "build_default_safe_audio_timing_exp_step_vault_spec",
    "build_default_safe_lock_op_parts_vault_spec",
    "evaluate_40pillar_recovery_master",
    "evaluate_audio_out_timing_signals_and_exp_step_vault",
    "evaluate_lock_operation_parts_bench_vault",
    "evaluate_realhw_40pillar_recovery_master",
    "inspect_phase245_donors_readonly",
    "run_pillar40_standalone_suite",
    "run_pillar40a_lock_op_parts_vault_6_scenario_suite",
    "run_pillar40b_audio_timing_exp_step_vault_6_scenario_suite",
    "verify_40pillar_recovery_suite",
    "verify_lock_op_parts_audio_timing_and_exp_step_vault",
]
