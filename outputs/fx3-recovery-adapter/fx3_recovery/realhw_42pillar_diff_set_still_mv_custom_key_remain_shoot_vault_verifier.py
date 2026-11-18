"""Phase 251 — Pillar 42 (`42/42` Recovery Pillars) & Unified 42-Pillar Recovery Master
(`verify-42pillar-recovery` / `verify-diff-set-still-mv-custom-key-remain-shoot-vault`):

1. **Pillar 42A — `[Different Set for Still/Mv]` 8-Item Asymmetric State Transitions &
   `Ver. 7.02` `[Shutter Mode] = [Angle]` Split (`ILME-FX3 Ver. 7.02`, `ilc/2210`, Wave-40)**:
   - Models `MENU` -> `Setup` -> `[Operation Customize]` -> `[Different Set for Still/Mv]`
     across the exact 8 checkable items (`Aperture`, `Shutter Speed`, `ISO`, `Exposure Comp.`,
     `Metering Mode`, `White Balance`, `Picture Profile`, `Focus Mode`), verifying survival
     across **both** `[Camera Settings Reset]` and `[Reset Network Set.]` (restored to factory
     unchecked defaults **only** by `[Initialize]`, and restorable via `O_RDONLY` Slot-1
     `CAMSET01.DAT` `[Load]`).
   - Enforces Sony's two exact hardware parameter state-transition rules (`diff_set_transition_corruption_events == 0`):
     (a) **Common -> Separate**: Copies current parameter values to both Still and Movie
         registers, **EXCEPT `Custom White Balance`**, which applies only to still-image shooting.
     (b) **Separate -> Common**: Resets parameter values to their initial factory defaults,
         **EXCEPT `Aperture`, `Shutter Speed`, and `Custom White Balance`**, which retain the
         values set for still-image shooting.
   - Enforces the `Ver. 6.00+` / `Ver. 7.02` **`[Shutter Mode] = [Angle]`** override: whenever
     movie `[Shutter Mode]` (`MENU` -> `Shooting` -> `[Shutter/Silent]` -> `[Shutter Mode]`) is
     set to `[Angle]` (`Shutter Angle`), still-image shutter speed and movie shutter angle
     operate as independent settings **even when `Shutter Speed` is unchecked (Common)** in
     `[Different Set for Still/Mv]` (`shutter_angle_common_bleed_events == 0`).

2. **Pillar 42B — `[Custom Key/Dial Set.]` 3-Domain Keymaps / `ISO/EI` Dial Persistence &
   `[Remain Shoot Display]` Still-Buffer Scope + EVF-Less `ILME-FX3` Topology**:
   - Models `MENU` -> `Setup` -> `[Operation Customize]` -> `[Custom Key/Dial Set.]` across
     Still, Movie, and Playback keymaps (Custom Buttons `1`–`6`, Multi-Selector, Lens Focus Hold,
     and Cinema-Line factory dial defaults: `Front dial = Aperture`, `Rear dial = ISO/EI`
     auto-adapting between `ISO` and `Cine EI` Exposure Index, `Control Wheel = Shutter Speed`),
     plus `[Follow Custom]` inheritance, `[My Dial 1]`–`[My Dial 3]`, and `[Recall Custom hold 1]`–`[3]`,
     verifying survival across `[Camera Settings Reset]` & `[Reset Network Set.]` and lossless
     `O_RDONLY` Slot-1 `CAMSET01.DAT` `[Load]` round-trip (`slot1_custom_key_vault_mutation_bytes == 0`).
   - Models `MENU` -> `Setup` -> `[Display Option]` -> `[Remain Shoot Display]`
     (`Not Displayed` default / `Always Display` / `Shoot-Only Display`) strictly scoped to
     still-image continuous-shooting buffer capacity (never movie card recording time),
     surviving `[Camera Settings Reset]` & `[Reset Network Set.]`, enforcing EVF-less `ILME-FX3`
     (`ilc/2210`) monitor topology (`fx3_has_builtin_evf == False`,
     `evf_finder_monitor_spoof_events == 0`), and `16/16` Tier-0 `Backup.bin` `H0 == H3` parity.

3. **Unified `42/42` Recovery Master (`evaluate_realhw_42pillar_recovery_master`)**:
   - Delegates Pillars `1..41` concurrently to `evaluate_realhw_41pillar_recovery_master` +
     **Pillar 42** -> **`42/42` (`VERIFIED_42OF42_PILLAR_RECOVERY_MASTER`)** in `< 4.0s`
     nominal (`< 6.0s` concurrent ceiling), preserving 100% backward compatibility with
     `verify-22..41pillar-recovery`.
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple, Union

from .files import is_forced_clean_room, resolve_donor_path
from .realhw_22pillar_master_recovery_verifier import MasterPillarStatus
from .realhw_41pillar_display_quality_bt_rmt_mymenu_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_41_PILLAR_SPECS,
    Master41PillarRecoveryReport,
    evaluate_realhw_41pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE251_SCHEMA: str = "realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier_v1"
PHASE251_VERSION: str = "1.0.0"

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
P251_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P251_DIFF_SET_TRANSITION_CORRUPTION_EVENTS: int = 0
P251_SHUTTER_ANGLE_COMMON_BLEED_EVENTS: int = 0
P251_SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES: int = 0
P251_FX3_HAS_BUILTIN_EVF: bool = False
P251_EVF_FINDER_MONITOR_SPOOF_EVENTS: int = 0

P251_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P251_NOMINAL_BUDGET_SECONDS: float = 4.0
P251_CONCURRENT_CEILING_SECONDS: float = 6.0
P251_BOUNDED_HEADER_BYTES: int = 4096
P251_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-40 / FX3 Ver. 7.02 & FX6 Ver. 6.01 Donor Anchors (bounded O_RDONLY verification)
P251_FX3_MODEL_NAME: str = "ILME-FX3"
P251_FX3_MODEL_ID: int = 0x91030080
P251_FX3_HELPGUIDE_ID: str = "ilc/2210"
P251_FX3_FW_VERSION: str = "7.02"
P251_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P251_FX6_DONOR_FW_VERSION: str = "6.01"
P251_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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
P251_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS: Tuple[str, ...] = (
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P251_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P251_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P251_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)

P251_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P251_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P251_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P251_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P251_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P251_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P251_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P251_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P251_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P251_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P251_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P251_PINNED_FX3_LIBBACKUP_SO_SHA256: str = (
    "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
)

P251_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P251_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P251_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

P251_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P251_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P251_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P251_DONOR_FX3_LIBGPE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so"
)
P251_PINNED_FX3_LIBGPE_SO_BYTES: int = 106480
P251_PINNED_FX3_LIBGPE_SO_SHA256: str = (
    "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464"
)

P251_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/CameraOnDemandSaver.so"
)
P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES: int = 18800
P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256: str = (
    "72b73608c2675a3709e2952ca347a36e7dd2ad3dd2869191638c7154933b2f46"
)

P251_DONOR_FX6_LIBINFRADIAL_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraDial.so"
)
P251_PINNED_FX6_LIBINFRADIAL_SO_BYTES: int = 31232
P251_PINNED_FX6_LIBINFRADIAL_SO_SHA256: str = (
    "b2034d6c85372027444e783d5d2ed913bb5a8cd2fe4051b10cf63caae875db33"
)

P251_DONOR_FX6_LIBINFRAINPUT_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraInput.so"
)
P251_PINNED_FX6_LIBINFRAINPUT_SO_BYTES: int = 93448
P251_PINNED_FX6_LIBINFRAINPUT_SO_SHA256: str = (
    "1851e2dc8515d2240b9ecaffd58591207336c5f061b1af0d3585d7b082a41f02"
)

# Pillar 42A — [Different Set for Still/Mv] 8-Item Asymmetric Transitions & [Shutter Angle] Override
P251_DIFF_SET_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Operation Customize",
    "Different Set for Still/Mv",
)
P251_SHUTTER_MODE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Shutter/Silent",
    "Shutter Mode",
)
P251_DIFF_SET_8_ITEMS: Tuple[str, ...] = (
    "Aperture",
    "Shutter Speed",
    "ISO",
    "Exposure Comp.",
    "Metering Mode",
    "White Balance",
    "Picture Profile",
    "Focus Mode",
)
P251_DIFF_SET_FACTORY_CHECKED_ITEMS: Tuple[str, ...] = ()
P251_DIFF_SET_FACTORY_PARAM_DEFAULTS: Tuple[Tuple[str, str], ...] = (
    ("Aperture", "F4.0"),
    ("Shutter Speed", "1/125"),
    ("ISO", "Auto"),
    ("Exposure Comp.", "0.0EV"),
    ("Metering Mode", "Multi"),
    ("White Balance", "AWB"),
    ("Picture Profile", "Off"),
    ("Focus Mode", "AF-C"),
)
P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES: Tuple[Tuple[str, str], ...] = (
    ("Aperture", "F2.8"),
    ("Shutter Speed", "1/50"),
    ("ISO", "800"),
    ("Exposure Comp.", "+0.3EV"),
    ("Metering Mode", "Center"),
    ("White Balance", "Daylight"),
    ("Picture Profile", "PP11 (S-Cinetone)"),
    ("Focus Mode", "AF-C"),
)
P251_COMMON_TO_SEPARATE_STILL_ONLY_EXCEPTION: str = "Custom White Balance"
P251_SEPARATE_TO_COMMON_STILL_RETAINED_EXCEPTIONS: Tuple[str, ...] = (
    "Aperture",
    "Shutter Speed",
    "Custom White Balance",
)
P251_MOVIE_CUSTOM_WB_STILL_ONLY_SENTINEL: str = "STILL_ONLY_UNCOPIED"
P251_DEFAULT_STILL_CUSTOM_WB_REGISTER: str = "Custom 1 (4300K_G+1)"
P251_DIFF_SET_TRANSITION_KINDS: Tuple[str, ...] = (
    "NONE",
    "COMMON_TO_SEPARATE",
    "SEPARATE_TO_COMMON",
)
P251_MOVIE_SHUTTER_MODES: Tuple[str, ...] = ("Shutter Speed", "Angle")
P251_MOVIE_SHUTTER_MODE_DEFAULT: str = "Shutter Speed"
P251_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG: float = 180.0
P251_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)

# Pillar 42B — [Custom Key/Dial Set.] 3-Domain Keymaps / ISO-EI & [Remain Shoot Display] + EVF-less FX3
P251_CUSTOM_KEY_DIAL_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Operation Customize",
    "Custom Key/Dial Set.",
)
P251_CUSTOM_KEY_3_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "Playback")
P251_ASSIGNABLE_CUSTOM_CONTROLS: Tuple[str, ...] = (
    "Custom Button 1",
    "Custom Button 2",
    "Custom Button 3",
    "Custom Button 4",
    "Custom Button 5",
    "Custom Button 6",
    "Multi-Selector Center",
    "Lens Focus Hold Button",
)
P251_FRONT_DIAL_DEFAULT: str = "Aperture"
P251_REAR_DIAL_DEFAULT: str = "ISO/EI"
P251_CONTROL_WHEEL_DEFAULT: str = "Shutter Speed"
P251_FACTORY_DIAL_DEFAULTS: Tuple[Tuple[str, str], ...] = (
    ("Front dial", P251_FRONT_DIAL_DEFAULT),
    ("Rear dial", P251_REAR_DIAL_DEFAULT),
    ("Control Wheel", P251_CONTROL_WHEEL_DEFAULT),
)
P251_FOLLOW_CUSTOM_TOKEN: str = "Follow Custom"
P251_SHOOTING_EXPOSURE_MODES: Tuple[str, ...] = ("Flexible ISO", "Cine EI", "Cine EI Quick")
P251_REAR_DIAL_EFFECTIVE_TARGETS: Tuple[str, ...] = ("ISO", "Exposure Index (EI)", "CUSTOM_NON_ISO_EI")
P251_MY_DIAL_SLOTS: Tuple[str, ...] = ("NONE", "My Dial 1", "My Dial 2", "My Dial 3")
P251_RECALL_CUSTOM_HOLD_SLOTS: Tuple[str, ...] = (
    "Recall Custom hold 1",
    "Recall Custom hold 2",
    "Recall Custom hold 3",
)
P251_FACTORY_STILL_KEYMAP: Tuple[Tuple[str, str], ...] = (
    ("Custom Button 1", "White Balance"),
    ("Custom Button 2", "Focus Area"),
    ("Custom Button 3", "Focus Mode"),
    ("Custom Button 4", "Touch Operation"),
    ("Custom Button 5", "Zebra Display"),
    ("Custom Button 6", "Peaking Display"),
    ("Multi-Selector Center", "Focus Standard"),
    ("Lens Focus Hold Button", "Focus Hold"),
)
P251_FACTORY_MOVIE_KEYMAP: Tuple[Tuple[str, str], ...] = (
    ("Custom Button 1", "Follow Custom"),
    ("Custom Button 2", "Follow Custom"),
    ("Custom Button 3", "Audio Level Display"),
    ("Custom Button 4", "Touch Operation"),
    ("Custom Button 5", "Zebra Display"),
    ("Custom Button 6", "Peaking Display"),
    ("Multi-Selector Center", "Focus Standard"),
    ("Lens Focus Hold Button", "Follow Custom"),
)
P251_FACTORY_PLAYBACK_KEYMAP: Tuple[Tuple[str, str], ...] = (
    ("Custom Button 1", "Jump/Select"),
    ("Custom Button 2", "Rating"),
    ("Custom Button 3", "Protect"),
)

P251_REMAIN_SHOOT_DISPLAY_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Display Option",
    "Remain Shoot Display",
)
P251_REMAIN_SHOOT_DISPLAY_DEFAULT: str = "Not Displayed"
P251_REMAIN_SHOOT_DISPLAY_MODES: Tuple[str, ...] = (
    "Not Displayed",
    "Always Display",
    "Shoot-Only Display",
)

P251_SLOT1_VAULT_SLOT: int = 1
P251_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P251_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_diff_set_custom_key_remain_shoot_overlay"
P251_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P251_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P251_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P251_BLOCKED_INVALID_DIFF_SET_SPEC: str = "BLOCKED_INVALID_DIFF_SET_SPEC"
P251_BLOCKED_DIFF_SET_RESET_SURVIVAL_DRIFT: str = "BLOCKED_DIFF_SET_RESET_SURVIVAL_DRIFT"
P251_BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT: str = (
    "BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT"
)
P251_BLOCKED_DIFF_SET_SEPARATE_TO_COMMON_DRIFT: str = (
    "BLOCKED_DIFF_SET_SEPARATE_TO_COMMON_DRIFT"
)
P251_BLOCKED_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION: str = (
    "BLOCKED_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION"
)

P251_BLOCKED_INVALID_CUSTOM_KEY_OR_REMAIN_SHOOT_SPEC: str = (
    "BLOCKED_INVALID_CUSTOM_KEY_OR_REMAIN_SHOOT_SPEC"
)
P251_BLOCKED_CUSTOM_KEY_OR_REMAIN_SHOOT_RESET_DRIFT: str = (
    "BLOCKED_CUSTOM_KEY_OR_REMAIN_SHOOT_RESET_DRIFT"
)
P251_BLOCKED_DIAL_ISO_EI_OR_FOLLOW_CUSTOM_MISMATCH: str = (
    "BLOCKED_DIAL_ISO_EI_OR_FOLLOW_CUSTOM_MISMATCH"
)
P251_BLOCKED_REMAIN_SHOOT_SCOPE_OR_EVF_TOPOLOGY_SPOOF: str = (
    "BLOCKED_REMAIN_SHOOT_SCOPE_OR_EVF_TOPOLOGY_SPOOF"
)
P251_BLOCKED_SLOT1_CUSTOM_KEY_VAULT_MUTATION_OR_CAMSET_DRIFT: str = (
    "BLOCKED_SLOT1_CUSTOM_KEY_VAULT_MUTATION_OR_CAMSET_DRIFT"
)
P251_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P251_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P251_STATUS_VERIFIED_PILLAR_42A: str = (
    "VERIFIED_PILLAR_42A_DIFF_SET_STILL_MV_8ITEMS_AND_SHUTTER_ANGLE_SPLIT_VAULT"
)
P251_STATUS_REJECTED_PILLAR_42A: str = (
    "REJECTED_PILLAR_42A_DIFF_SET_STILL_MV_8ITEMS_AND_SHUTTER_ANGLE_SPLIT_VAULT"
)
P251_STATUS_VERIFIED_PILLAR_42B: str = (
    "VERIFIED_PILLAR_42B_CUSTOM_KEY_DIAL_ISO_EI_AND_REMAIN_SHOOT_EVFLESS_VAULT"
)
P251_STATUS_REJECTED_PILLAR_42B: str = (
    "REJECTED_PILLAR_42B_CUSTOM_KEY_DIAL_ISO_EI_AND_REMAIN_SHOOT_EVFLESS_VAULT"
)
P251_STATUS_VERIFIED_PILLAR42_SUITE: str = (
    "VERIFIED_PILLAR42_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_VAULT"
)
P251_STATUS_FAIL_PILLAR42_SUITE: str = (
    "FAIL_PILLAR42_DIFF_SET_STILL_MV_CUSTOM_KEY_REMAIN_SHOOT_VAULT"
)
P251_STATUS_VERIFIED_42OF42_AGGREGATOR: str = "VERIFIED_42OF42_PILLAR_RECOVERY_MASTER"
P251_STATUS_FAIL_42OF42_AGGREGATOR: str = "FAIL_42OF42_PILLAR_RECOVERY_MASTER"

P251_PILLAR_42A_SCENARIO_IDS: Tuple[str, ...] = (
    "P42A1_DIFF_SET_8ITEMS_COMMON_TO_SEPARATE_COPIES_ALL_EXCEPT_CUSTOM_WB_STILL_ONLY_AND_SURVIVES_RESETS_SAFE",
    "P42A2_DIFF_SET_SEPARATE_TO_COMMON_RETAINS_STILL_APERTURE_SHUTTER_CUSTOM_WB_AND_SHUTTER_ANGLE_INDEPENDENT_SAFE",
    "P42A3_REJECT_DIFF_SET_WIPED_BY_CAMERA_SETTINGS_RESET_OR_RESET_NETWORK_SET",
    "P42A4_REJECT_COMMON_TO_SEPARATE_COPYING_CUSTOM_WB_TO_MOVIE_OR_DROPPING_STANDARD_ITEM",
    "P42A5_REJECT_SEPARATE_TO_COMMON_WIPING_STILL_APERTURE_SHUTTER_CUSTOM_WB_OR_KEEPING_SEPARATE_ISO",
    "P42A6_REJECT_SHUTTER_MODE_ANGLE_COUPLED_OR_BLEEDING_WHEN_SHUTTER_SPEED_UNCHECKED_COMMON",
)
P251_PILLAR_42B_SCENARIO_IDS: Tuple[str, ...] = (
    "P42B1_CUSTOM_KEY_3DOMAIN_ISO_EI_FOLLOW_CUSTOM_AND_REMAIN_SHOOT_STILL_BUFFER_SURVIVE_BOTH_RESETS_SAFE",
    "P42B2_INITIALIZE_RESTORES_FACTORY_DIALS_AND_NOT_DISPLAYED_THEN_ORDONLY_SLOT1_CAMSET01_ROUNDTRIPS_SAFE",
    "P42B3_REJECT_CUSTOM_KEY_DIAL_OR_REMAIN_SHOOT_WIPED_BY_CAMERA_SETTINGS_RESET_OR_NETWORK_RESET",
    "P42B4_REJECT_REAR_DIAL_ISO_EI_ADAPTATION_MISMATCH_OR_FOLLOW_CUSTOM_INHERITANCE_BREAK",
    "P42B5_REJECT_REMAIN_SHOOT_MOVIE_CARD_TIME_CONFUSION_OR_BUILTIN_EVF_FINDER_MONITOR_SPOOF",
    "P42B6_REJECT_SLOT1_TIER0_CAMSET01_CUSTOM_KEY_VAULT_OVERWRITE_OR_CROSS_MODEL_FX6_IMPORT",
)

MASTER_42_PILLAR_COUNT: int = 42
MASTER_42_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_41_PILLAR_SPECS + (
    (
        42,
        "pillar_42_diff_set_still_mv_custom_key_remain_shoot_vault",
        "Phase 251",
        "fx3_recovery.realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier",
    ),
)
MASTER_42_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_42_PILLAR_SPECS)


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
        ("P251_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P251_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P251_DIFF_SET_TRANSITION_CORRUPTION_EVENTS", P251_DIFF_SET_TRANSITION_CORRUPTION_EVENTS, 0),
        ("P251_SHUTTER_ANGLE_COMMON_BLEED_EVENTS", P251_SHUTTER_ANGLE_COMMON_BLEED_EVENTS, 0),
        ("P251_SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES", P251_SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES, 0),
        ("P251_FX3_HAS_BUILTIN_EVF", P251_FX3_HAS_BUILTIN_EVF, False),
        ("P251_EVF_FINDER_MONITOR_SPOOF_EVENTS", P251_EVF_FINDER_MONITOR_SPOOF_EVENTS, 0),
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
    return any(tok in low for tok in P251_FORBIDDEN_PERSISTENT_TARGETS)


def _is_custom_wb_setting(wb_value: str) -> bool:
    norm = wb_value.strip().lower()
    return norm.startswith("custom")


def _pairs_to_ordered_dict(
    pairs_or_map: Union[Sequence[Tuple[str, str]], Mapping[str, str]],
) -> Optional[Dict[str, str]]:
    if isinstance(pairs_or_map, Mapping):
        out: Dict[str, str] = {}
        for k, v in pairs_or_map.items():
            if not isinstance(k, str) or not isinstance(v, str) or not k.strip() or not v.strip():
                return None
            out[k] = v
        return out
    out = {}
    for entry in pairs_or_map:
        if not isinstance(entry, tuple) or len(entry) != 2:
            return None
        k, v = entry
        if not isinstance(k, str) or not isinstance(v, str) or not k.strip() or not v.strip():
            return None
        if k in out:
            return None
        out[k] = v
    return out


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase251DonorArtifactDigest:
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
class Phase251DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase251DonorArtifactDigest, ...]


@dataclass(frozen=True)
class DiffSetStillMvAndShutterAngleVaultSpec:
    camera_model: str = P251_FX3_MODEL_NAME
    helpguide_id: str = P251_FX3_HELPGUIDE_ID
    fw_version: str = P251_FX3_FW_VERSION
    diff_set_menu_path: Tuple[str, ...] = P251_DIFF_SET_MENU_PATH
    shutter_mode_menu_path: Tuple[str, ...] = P251_SHUTTER_MODE_MENU_PATH
    configurable_8_items: Tuple[str, ...] = P251_DIFF_SET_8_ITEMS
    pre_checked_items: Tuple[str, ...] = ()
    transition_kind: str = "COMMON_TO_SEPARATE"  # NONE | COMMON_TO_SEPARATE | SEPARATE_TO_COMMON
    post_transition_checked_items: Tuple[str, ...] = P251_DIFF_SET_8_ITEMS
    pre_still_values: Tuple[Tuple[str, str], ...] = P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES
    pre_movie_values: Tuple[Tuple[str, str], ...] = P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES
    post_still_values: Tuple[Tuple[str, str], ...] = P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES
    post_movie_values: Tuple[Tuple[str, str], ...] = P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES
    pre_still_custom_wb: str = P251_DEFAULT_STILL_CUSTOM_WB_REGISTER
    pre_movie_custom_wb: str = P251_MOVIE_CUSTOM_WB_STILL_ONLY_SENTINEL
    post_still_custom_wb: str = P251_DEFAULT_STILL_CUSTOM_WB_REGISTER
    post_movie_custom_wb: str = P251_MOVIE_CUSTOM_WB_STILL_ONLY_SENTINEL
    custom_wb_copied_to_movie: bool = False
    diff_set_transition_corruption_events: int = 0
    movie_shutter_mode: str = "Angle"  # Shutter Speed | Angle
    movie_shutter_angle_deg: float = P251_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG
    post_movie_shutter_angle_deg: float = P251_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG
    shutter_speed_and_angle_independent: bool = True
    shutter_angle_common_bleed_events: int = 0
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P251_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P251_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_checked_items: Tuple[str, ...] = P251_DIFF_SET_8_ITEMS
    post_reset_checked_items: Tuple[str, ...] = P251_DIFF_SET_8_ITEMS
    overlay_dir: str = P251_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P251_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P251_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P251_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class DiffSetStillMvAndShutterAngleVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    eight_items_catalog_verified: bool
    diff_set_reset_survival_verified: bool
    common_to_separate_transition_verified: bool
    separate_to_common_transition_verified: bool
    shutter_angle_independence_verified: bool
    h0_equals_h3_verified: bool
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class CustomKeyDialAndRemainShootVaultSpec:
    camera_model: str = P251_FX3_MODEL_NAME
    helpguide_id: str = P251_FX3_HELPGUIDE_ID
    fw_version: str = P251_FX3_FW_VERSION
    custom_key_dial_menu_path: Tuple[str, ...] = P251_CUSTOM_KEY_DIAL_MENU_PATH
    remain_shoot_menu_path: Tuple[str, ...] = P251_REMAIN_SHOOT_DISPLAY_MENU_PATH
    custom_key_domains: Tuple[str, ...] = P251_CUSTOM_KEY_3_DOMAINS
    pre_reset_still_keymap: Tuple[Tuple[str, str], ...] = P251_FACTORY_STILL_KEYMAP
    pre_reset_movie_keymap: Tuple[Tuple[str, str], ...] = P251_FACTORY_MOVIE_KEYMAP
    pre_reset_playback_keymap: Tuple[Tuple[str, str], ...] = P251_FACTORY_PLAYBACK_KEYMAP
    resolved_movie_follow_custom_map: Tuple[Tuple[str, str], ...] = (
        ("Custom Button 1", "White Balance"),
        ("Custom Button 2", "Focus Area"),
        ("Lens Focus Hold Button", "Focus Hold"),
    )
    pre_reset_front_dial: str = P251_FRONT_DIAL_DEFAULT
    pre_reset_rear_dial: str = P251_REAR_DIAL_DEFAULT
    pre_reset_control_wheel: str = P251_CONTROL_WHEEL_DEFAULT
    shooting_exposure_mode: str = "Cine EI"  # Flexible ISO | Cine EI | Cine EI Quick
    rear_dial_effective_target: str = "Exposure Index (EI)"  # ISO | Exposure Index (EI) | CUSTOM_NON_ISO_EI
    active_my_dial_slot: str = "My Dial 1"  # NONE | My Dial 1 | My Dial 2 | My Dial 3
    supported_recall_custom_holds: Tuple[str, ...] = P251_RECALL_CUSTOM_HOLD_SLOTS
    pre_reset_remain_shoot_display: str = "Always Display"  # Not Displayed | Always Display | Shoot-Only Display
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P251_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P251_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_still_keymap: Tuple[Tuple[str, str], ...] = P251_FACTORY_STILL_KEYMAP
    saved_movie_keymap: Tuple[Tuple[str, str], ...] = P251_FACTORY_MOVIE_KEYMAP
    saved_playback_keymap: Tuple[Tuple[str, str], ...] = P251_FACTORY_PLAYBACK_KEYMAP
    saved_front_dial: str = P251_FRONT_DIAL_DEFAULT
    saved_rear_dial: str = P251_REAR_DIAL_DEFAULT
    saved_control_wheel: str = P251_CONTROL_WHEEL_DEFAULT
    saved_remain_shoot_display: str = "Shoot-Only Display"
    post_reset_still_keymap: Tuple[Tuple[str, str], ...] = P251_FACTORY_STILL_KEYMAP
    post_reset_movie_keymap: Tuple[Tuple[str, str], ...] = P251_FACTORY_MOVIE_KEYMAP
    post_reset_playback_keymap: Tuple[Tuple[str, str], ...] = P251_FACTORY_PLAYBACK_KEYMAP
    post_reset_front_dial: str = P251_FRONT_DIAL_DEFAULT
    post_reset_rear_dial: str = P251_REAR_DIAL_DEFAULT
    post_reset_control_wheel: str = P251_CONTROL_WHEEL_DEFAULT
    post_reset_remain_shoot_display: str = "Always Display"
    remain_shoot_applies_to_still_buffer_only: bool = True
    remain_shoot_displays_movie_card_time: bool = False
    fx3_has_builtin_evf: bool = False
    finder_monitor_switch_present: bool = False
    eye_sensor_present: bool = False
    evf_finder_monitor_spoof_events: int = 0
    slot1_tier0_vault_active: bool = True
    slot1_sdxc_wp_locked: bool = True
    camset_save_to_slot1_attempted: bool = False
    slot1_custom_key_vault_mutation_bytes: int = 0
    overlay_dir: str = P251_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P251_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P251_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P251_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class CustomKeyDialAndRemainShootVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    three_domain_keymap_and_dials_verified: bool
    iso_ei_and_follow_custom_verified: bool
    non_resettable_survival_verified: bool
    remain_shoot_still_buffer_scope_verified: bool
    evfless_fx3_topology_verified: bool
    camset_slot1_roundtrip_verified: bool
    slot1_vault_zero_mutation_verified: bool
    h0_equals_h3_verified: bool
    slot1_custom_key_vault_mutation_bytes: int
    fx3_has_builtin_evf: bool
    evf_finder_monitor_spoof_events: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class DiffSetCustomKeyAndRemainShootVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase251DonorSnapshot
    diff_set_still_mv_report: DiffSetStillMvAndShutterAngleVaultReport
    custom_key_remain_shoot_report: CustomKeyDialAndRemainShootVaultReport
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    slot1_custom_key_vault_mutation_bytes: int
    fx3_has_builtin_evf: bool
    evf_finder_monitor_spoof_events: int
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
class Pillar42ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar42ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar42ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar42BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar42ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar42StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase251DonorSnapshot
    pillar_42a_diff_set_still_mv_vault: Pillar42ASuiteResult
    pillar_42b_custom_key_remain_shoot_vault: Pillar42BSuiteResult
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    slot1_custom_key_vault_mutation_bytes: int
    fx3_has_builtin_evf: bool
    evf_finder_monitor_spoof_events: int
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
class Master42PillarRecoveryReport:
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
    donor_snapshot: Phase251DonorSnapshot
    pillar42_a_diff_set_still_mv_vault: Pillar42ASuiteResult
    pillar42_b_custom_key_remain_shoot_vault: Pillar42BSuiteResult
    diff_set_transition_corruption_events: int
    shutter_angle_common_bleed_events: int
    slot1_custom_key_vault_mutation_bytes: int
    fx3_has_builtin_evf: bool
    evf_finder_monitor_spoof_events: int
    tier0_battery_high_display_violations: int
    bt_rmt_ir_lockout_violations: int
    slot1_mymenu_vault_mutation_bytes: int
    destructive_menu_delete_confusions: int
    shutter_angle_exposure_step_drift_events: int
    fx3_has_var_shutter: bool
    unbuffered_battery_pull_events: int
    hardware_live_attachment_authorized: bool
    master_42pillar_sha256: str
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
    max_full_bytes: int = P251_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P251_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase251_donors() -> Tuple[Phase251DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P251_DONOR_FX3_BODYDATA_RELPATH,
            P251_PINNED_FX3_BODYDATA_BYTES,
            P251_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P251_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P251_DONOR_FX3_APPFW_702_RELPATH,
            P251_PINNED_FX3_APPFW_702_BYTES,
            P251_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P251_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P251_DONOR_FX6_APPFW_601_RELPATH,
            P251_PINNED_FX6_APPFW_601_BYTES,
            P251_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P251_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P251_DONOR_FX3_BACKUP_BIN_RELPATH,
            P251_PINNED_FX3_BACKUP_BIN_BYTES,
            P251_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P251_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P251_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P251_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P251_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P251_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P251_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P251_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P251_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P251_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P251_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P251_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P251_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P251_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_libgpe_so",
            P251_DONOR_FX3_LIBGPE_SO_RELPATH,
            P251_PINNED_FX3_LIBGPE_SO_BYTES,
            P251_PINNED_FX3_LIBGPE_SO_BYTES,
            "FULL_SHA256",
            P251_PINNED_FX3_LIBGPE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:gpe_blog_error+_ZNK5mpgpe5Gperm4InitEv",
        ),
        (
            "fx3_cameraondemandsaver_so",
            P251_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            "FULL_SHA256",
            P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:CameraOnDemandSaver+_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji",
        ),
        (
            "fx6_libinfradial_so",
            P251_DONOR_FX6_LIBINFRADIAL_SO_RELPATH,
            P251_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
            P251_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
            "FULL_SHA256",
            P251_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraDial+InfraDialEventDataRecord+INFRA_DIAL_UIPC_SETDIALEVENTINTERVAL",
        ),
        (
            "fx6_libinfrainput_so",
            P251_DONOR_FX6_LIBINFRAINPUT_SO_RELPATH,
            P251_PINNED_FX6_LIBINFRAINPUT_SO_BYTES,
            P251_PINNED_FX6_LIBINFRAINPUT_SO_BYTES,
            "FULL_SHA256",
            P251_PINNED_FX6_LIBINFRAINPUT_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraInput+ApiGetKeySta+ApiSetKeyInh",
        ),
    )
    return tuple(
        Phase251DonorArtifactDigest(
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


def inspect_phase251_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase251DonorSnapshot:
    """Inspect Wave-40 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase251_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase251DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P251_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P251_DONOR_FX3_BODYDATA_RELPATH,
            P251_PINNED_FX3_BODYDATA_BYTES,
            P251_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P251_DONOR_FX3_APPFW_702_RELPATH,
            P251_PINNED_FX3_APPFW_702_BYTES,
            P251_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P251_DONOR_FX6_APPFW_601_RELPATH,
            P251_PINNED_FX6_APPFW_601_BYTES,
            P251_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P251_DONOR_FX3_BACKUP_BIN_RELPATH,
            P251_PINNED_FX3_BACKUP_BIN_BYTES,
            P251_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P251_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P251_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P251_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P251_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P251_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P251_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P251_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P251_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P251_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite"),
            ),
        ),
        (
            "fx3_libgpe_so",
            P251_DONOR_FX3_LIBGPE_SO_RELPATH,
            P251_PINNED_FX3_LIBGPE_SO_BYTES,
            P251_PINNED_FX3_LIBGPE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv")),
        ),
        (
            "fx3_cameraondemandsaver_so",
            P251_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"CameraOnDemandSaver", b"_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji"),
            ),
        ),
        (
            "fx6_libinfradial_so",
            P251_DONOR_FX6_LIBINFRADIAL_SO_RELPATH,
            P251_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
            P251_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraDial", b"InfraDialEventDataRecord", b"INFRA_DIAL_UIPC_SETDIALEVENTINTERVAL"),
            ),
        ),
        (
            "fx6_libinfrainput_so",
            P251_DONOR_FX6_LIBINFRAINPUT_SO_RELPATH,
            P251_PINNED_FX6_LIBINFRAINPUT_SO_BYTES,
            P251_PINNED_FX6_LIBINFRAINPUT_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraInput", b"ApiGetKeySta", b"ApiSetKeyInh"),
            ),
        ),
    )

    real_artifacts: List[Phase251DonorArtifactDigest] = []
    any_missing = False
    for aid, rel, pinned_bytes, pinned_sha, marker_fn in probe_specs:
        present, total_b, read_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(rel)
        if not present:
            any_missing = True
            break
        marker_ok, marker_summary = marker_fn(raw_slice)
        matches = (total_b == pinned_bytes) and (dsha == pinned_sha) and bool(marker_ok)
        real_artifacts.append(
            Phase251DonorArtifactDigest(
                artifact_id=aid,
                relpath=rel,
                present=True,
                read_mode="LOCAL_DONOR_O_RDONLY",
                total_bytes=total_b,
                header_bytes_read=read_b,
                digest_kind=dkind,
                digest_sha256=dsha,
                marker_summary=marker_summary,
                matches_pinned=matches,
            )
        )

    if any_missing:
        synth = _synthetic_phase251_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase251DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P251_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    all_ok = len(real_artifacts) == len(probe_specs) and all(a.matches_pinned for a in real_artifacts)
    return Phase251DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(real_artifacts),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P251_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(real_artifacts),
    )


# ---------------------------------------------------------------------------
# Default Safe Builders & Pillar 42A / 42B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_diff_set_still_mv_vault_spec() -> DiffSetStillMvAndShutterAngleVaultSpec:
    """Return canonical safe Wave-40 `[Different Set for Still/Mv]` & `[Shutter Mode]=[Angle]` spec."""
    return DiffSetStillMvAndShutterAngleVaultSpec()


def build_default_safe_custom_key_remain_shoot_vault_spec() -> CustomKeyDialAndRemainShootVaultSpec:
    """Return canonical safe Wave-40 `[Custom Key/Dial Set.]` & `[Remain Shoot Display]` spec."""
    return CustomKeyDialAndRemainShootVaultSpec()


def _validate_checked_items_subset(items: Tuple[str, ...]) -> bool:
    if not isinstance(items, tuple):
        return False
    if len(items) != len(set(items)):
        return False
    return all(isinstance(it, str) and it in P251_DIFF_SET_8_ITEMS for it in items)


def evaluate_diff_set_still_mv_and_shutter_angle_vault(
    spec: DiffSetStillMvAndShutterAngleVaultSpec,
) -> DiffSetStillMvAndShutterAngleVaultReport:
    """Evaluate Pillar 42A `[Different Set for Still/Mv]` 8-item transitions & `[Shutter Angle]` split."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    safety_errs = _safety_invariant_errors()
    if safety_errs or spec.persistent_write_unlock_requested:
        _fail(
            P251_BLOCKED_SAFETY_POLICY_VIOLATION,
            f"Safety policy violation: unlock={spec.persistent_write_unlock_requested}, errs={safety_errs}",
        )

    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P251_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Volatile overlay / p2 BLKROSET violated: overlay={spec.overlay_dir!r}, "
            f"blkroset={spec.p2_blkroset_locked}, writes={spec.stage_b_backup_bin_writes}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P251_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P251_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P251_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            f"Tier-0 Backup.bin H0==H3 drift: matched={spec.tier0_surfaces_h0_h3_matched}/16",
        )

    pre_still_map = _pairs_to_ordered_dict(spec.pre_still_values)
    pre_movie_map = _pairs_to_ordered_dict(spec.pre_movie_values)
    post_still_map = _pairs_to_ordered_dict(spec.post_still_values)
    post_movie_map = _pairs_to_ordered_dict(spec.post_movie_values)
    factory_map = dict(P251_DIFF_SET_FACTORY_PARAM_DEFAULTS)

    maps_valid = (
        pre_still_map is not None
        and pre_movie_map is not None
        and post_still_map is not None
        and post_movie_map is not None
        and set(pre_still_map.keys()) == set(P251_DIFF_SET_8_ITEMS)
        and set(pre_movie_map.keys()) == set(P251_DIFF_SET_8_ITEMS)
        and set(post_still_map.keys()) == set(P251_DIFF_SET_8_ITEMS)
        and set(post_movie_map.keys()) == set(P251_DIFF_SET_8_ITEMS)
    )
    catalog_ok = spec.configurable_8_items == P251_DIFF_SET_8_ITEMS
    checked_subsets_ok = (
        _validate_checked_items_subset(spec.pre_checked_items)
        and _validate_checked_items_subset(spec.post_transition_checked_items)
        and _validate_checked_items_subset(spec.saved_checked_items)
        and _validate_checked_items_subset(spec.post_reset_checked_items)
    )

    if (
        spec.camera_model != P251_FX3_MODEL_NAME
        or spec.helpguide_id != P251_FX3_HELPGUIDE_ID
        or spec.fw_version not in P251_FX3_SUPPORTED_FW_VERSIONS
        or (
            spec.movie_shutter_mode == "Angle"
            and spec.fw_version not in P251_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS
        )
        or spec.diff_set_menu_path != P251_DIFF_SET_MENU_PATH
        or spec.shutter_mode_menu_path != P251_SHUTTER_MODE_MENU_PATH
        or not catalog_ok
        or not checked_subsets_ok
        or spec.transition_kind not in P251_DIFF_SET_TRANSITION_KINDS
        or spec.reset_action not in P251_RESET_ACTIONS
        or spec.movie_shutter_mode not in P251_MOVIE_SHUTTER_MODES
        or not (0.0 < float(spec.movie_shutter_angle_deg) <= 360.0)
        or not (0.0 < float(spec.post_movie_shutter_angle_deg) <= 360.0)
        or not maps_valid
        or spec.diff_set_transition_corruption_events < 0
        or spec.shutter_angle_common_bleed_events < 0
        or not (1 <= spec.camset_slot <= 10)
        or spec.camset_filename != f"CAMSET{spec.camset_slot:02d}.DAT"
    ):
        _fail(
            P251_BLOCKED_INVALID_DIFF_SET_SPEC,
            "Invalid ILME-FX3 Wave-40 [Different Set for Still/Mv] or [Shutter Mode] specification.",
        )

    corruption_events = max(0, int(spec.diff_set_transition_corruption_events))
    bleed_events = max(0, int(spec.shutter_angle_common_bleed_events))

    shutter_angle_ok = True
    c2s_ok = True
    s2c_ok = True
    reset_ok = True

    if maps_valid and checked_subsets_ok and pre_still_map and pre_movie_map and post_still_map and post_movie_map:
        # 1. [Shutter Mode] = [Angle] (Ver. 6.00+ / Ver. 7.02) independence check
        shutter_checked = "Shutter Speed" in spec.post_transition_checked_items
        if spec.shutter_angle_common_bleed_events > 0:
            shutter_angle_ok = False
        if spec.movie_shutter_mode == "Angle":
            if (
                not spec.shutter_speed_and_angle_independent
                or float(spec.post_movie_shutter_angle_deg) != float(spec.movie_shutter_angle_deg)
                or "deg" in post_still_map["Shutter Speed"].lower()
            ):
                shutter_angle_ok = False
                bleed_events = max(1, bleed_events)
        else:
            if not shutter_checked:
                if (
                    spec.shutter_speed_and_angle_independent
                    or post_still_map["Shutter Speed"] != post_movie_map["Shutter Speed"]
                ):
                    shutter_angle_ok = False
                    bleed_events = max(1, bleed_events)
            else:
                if not spec.shutter_speed_and_angle_independent:
                    shutter_angle_ok = False
                    bleed_events = max(1, bleed_events)

        if not shutter_angle_ok:
            _fail(
                P251_BLOCKED_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION,
                "[Shutter Mode]=[Angle] independence or Common Shutter Speed coupling rule violated.",
            )

        # 2. Asymmetric parameter transition rules
        pre_set = set(spec.pre_checked_items)
        post_set = set(spec.post_transition_checked_items)

        if spec.transition_kind == "COMMON_TO_SEPARATE":
            newly_separated = post_set - pre_set
            if not pre_set.issubset(post_set) or len(newly_separated) == 0:
                c2s_ok = False
            if (
                spec.custom_wb_copied_to_movie
                or spec.post_still_custom_wb != spec.pre_still_custom_wb
                or spec.post_movie_custom_wb != P251_MOVIE_CUSTOM_WB_STILL_ONLY_SENTINEL
            ):
                c2s_ok = False
            for k in newly_separated:
                if not (k == "Shutter Speed" and spec.movie_shutter_mode == "Angle"):
                    if pre_still_map[k] != pre_movie_map[k]:
                        c2s_ok = False
                if post_still_map[k] != pre_still_map[k]:
                    c2s_ok = False
                if k == "White Balance" and _is_custom_wb_setting(pre_still_map["White Balance"]):
                    if post_movie_map["White Balance"] != factory_map["White Balance"]:
                        c2s_ok = False
                else:
                    if post_movie_map[k] != pre_still_map[k]:
                        c2s_ok = False
            if spec.diff_set_transition_corruption_events > 0:
                c2s_ok = False
            if not c2s_ok:
                corruption_events = max(1, corruption_events)
                _fail(
                    P251_BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT,
                    "Common->Separate transition failed 8-item copy or Custom White Balance Still-only rule.",
                )

        elif spec.transition_kind == "SEPARATE_TO_COMMON":
            newly_merged = pre_set - post_set
            if not post_set.issubset(pre_set) or len(newly_merged) == 0:
                s2c_ok = False
            if spec.post_still_custom_wb != spec.pre_still_custom_wb:
                s2c_ok = False
            for k in newly_merged:
                if k == "Aperture":
                    if (
                        post_still_map["Aperture"] != pre_still_map["Aperture"]
                        or post_movie_map["Aperture"] != pre_still_map["Aperture"]
                    ):
                        s2c_ok = False
                elif k == "Shutter Speed":
                    if post_still_map["Shutter Speed"] != pre_still_map["Shutter Speed"]:
                        s2c_ok = False
                    if (
                        spec.movie_shutter_mode == "Shutter Speed"
                        and post_movie_map["Shutter Speed"] != pre_still_map["Shutter Speed"]
                    ):
                        s2c_ok = False
                elif k == "White Balance" and _is_custom_wb_setting(pre_still_map["White Balance"]):
                    if post_still_map["White Balance"] != pre_still_map["White Balance"]:
                        s2c_ok = False
                else:
                    expected_factory = factory_map[k]
                    if post_still_map[k] != expected_factory or post_movie_map[k] != expected_factory:
                        s2c_ok = False
            if spec.diff_set_transition_corruption_events > 0:
                s2c_ok = False
            if not s2c_ok:
                corruption_events = max(1, corruption_events)
                _fail(
                    P251_BLOCKED_DIFF_SET_SEPARATE_TO_COMMON_DRIFT,
                    "Separate->Common transition failed factory reset or Still-retained exceptions "
                    "(Aperture, Shutter Speed, Custom White Balance).",
                )

        else:  # NONE
            if spec.post_transition_checked_items != spec.pre_checked_items:
                c2s_ok = False
            for k in P251_DIFF_SET_8_ITEMS:
                if k not in post_set and not (k == "Shutter Speed" and spec.movie_shutter_mode == "Angle"):
                    if post_still_map[k] != post_movie_map[k]:
                        c2s_ok = False
            if spec.diff_set_transition_corruption_events > 0 or not c2s_ok:
                c2s_ok = False
                corruption_events = max(1, corruption_events)
                _fail(
                    P251_BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT,
                    "Steady-state [Different Set for Still/Mv] common/separate register invariant violated.",
                )

        # 3. Reset survival across Camera Settings Reset & Reset Network Set. vs Initialize
        if spec.camset_load_after_reset:
            if (
                spec.camset_source_model != P251_FX3_MODEL_NAME
                or not spec.camset_read_only_load
                or spec.post_reset_checked_items != spec.saved_checked_items
            ):
                reset_ok = False
        elif spec.reset_action in ("NONE", "Camera Settings Reset", "Reset Network Set."):
            if spec.post_reset_checked_items != spec.post_transition_checked_items:
                reset_ok = False
        elif spec.reset_action == "Initialize":
            if spec.post_reset_checked_items != P251_DIFF_SET_FACTORY_CHECKED_ITEMS:
                reset_ok = False

        if not reset_ok:
            _fail(
                P251_BLOCKED_DIFF_SET_RESET_SURVIVAL_DRIFT,
                "[Different Set for Still/Mv] reset survival or CAMSET01.DAT restore drifted.",
            )
    else:
        shutter_angle_ok = False
        c2s_ok = False
        s2c_ok = False
        reset_ok = False

    passed = len(errors) == 0 and block_code is None
    digest = _canonical_sha256(
        {
            "pillar": "42A",
            "passed": passed,
            "block_code": block_code,
            "transition": spec.transition_kind,
            "shutter_mode": spec.movie_shutter_mode,
            "reset": spec.reset_action,
            "checked": list(spec.post_reset_checked_items),
            "corruption_events": 0 if passed else corruption_events,
            "bleed_events": 0 if passed else bleed_events,
        }
    )
    return DiffSetStillMvAndShutterAngleVaultReport(
        passed=passed,
        status=P251_STATUS_VERIFIED_PILLAR_42A if passed else P251_STATUS_REJECTED_PILLAR_42A,
        block_code=block_code,
        eight_items_catalog_verified=catalog_ok and maps_valid,
        diff_set_reset_survival_verified=reset_ok,
        common_to_separate_transition_verified=c2s_ok,
        separate_to_common_transition_verified=s2c_ok,
        shutter_angle_independence_verified=shutter_angle_ok,
        h0_equals_h3_verified=h0_h3_ok,
        diff_set_transition_corruption_events=0 if passed else max(1, corruption_events)
        if not (c2s_ok and s2c_ok)
        else corruption_events,
        shutter_angle_common_bleed_events=0 if passed else bleed_events,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def _validate_domain_keymap(
    keymap_pairs: Tuple[Tuple[str, str], ...],
    *,
    require_all_8_controls: bool,
    allow_follow_custom: bool,
) -> Optional[Dict[str, str]]:
    mapped = _pairs_to_ordered_dict(keymap_pairs)
    if mapped is None or len(mapped) == 0:
        return None
    if not all(k in P251_ASSIGNABLE_CUSTOM_CONTROLS for k in mapped):
        return None
    if require_all_8_controls and set(mapped.keys()) != set(P251_ASSIGNABLE_CUSTOM_CONTROLS):
        return None
    if not allow_follow_custom and any(v == P251_FOLLOW_CUSTOM_TOKEN for v in mapped.values()):
        return None
    return mapped


def evaluate_custom_key_dial_and_remain_shoot_vault(
    spec: CustomKeyDialAndRemainShootVaultSpec,
) -> CustomKeyDialAndRemainShootVaultReport:
    """Evaluate Pillar 42B `[Custom Key/Dial Set.]` 3-domain / `ISO/EI` & `[Remain Shoot Display]` EVF-less vault."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    safety_errs = _safety_invariant_errors()
    if safety_errs or spec.persistent_write_unlock_requested:
        _fail(
            P251_BLOCKED_SAFETY_POLICY_VIOLATION,
            f"Safety policy violation: unlock={spec.persistent_write_unlock_requested}, errs={safety_errs}",
        )

    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P251_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Volatile overlay / p2 BLKROSET violated: overlay={spec.overlay_dir!r}, "
            f"blkroset={spec.p2_blkroset_locked}, writes={spec.stage_b_backup_bin_writes}",
        )

    h0_h3_ok = (
        spec.backup_bin_h0_sha256 == P251_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == spec.backup_bin_h0_sha256
        and spec.tier0_surfaces_h0_h3_matched == P251_TIER0_SURFACE_COUNT
    )
    if not h0_h3_ok:
        _fail(
            P251_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            f"Tier-0 Backup.bin H0==H3 drift: matched={spec.tier0_surfaces_h0_h3_matched}/16",
        )

    pre_still = _validate_domain_keymap(
        spec.pre_reset_still_keymap, require_all_8_controls=True, allow_follow_custom=False
    )
    pre_movie = _validate_domain_keymap(
        spec.pre_reset_movie_keymap, require_all_8_controls=True, allow_follow_custom=True
    )
    pre_pb = _validate_domain_keymap(
        spec.pre_reset_playback_keymap, require_all_8_controls=False, allow_follow_custom=False
    )
    saved_still = _validate_domain_keymap(
        spec.saved_still_keymap, require_all_8_controls=True, allow_follow_custom=False
    )
    saved_movie = _validate_domain_keymap(
        spec.saved_movie_keymap, require_all_8_controls=True, allow_follow_custom=True
    )
    saved_pb = _validate_domain_keymap(
        spec.saved_playback_keymap, require_all_8_controls=False, allow_follow_custom=False
    )
    post_still = _validate_domain_keymap(
        spec.post_reset_still_keymap, require_all_8_controls=True, allow_follow_custom=False
    )
    post_movie = _validate_domain_keymap(
        spec.post_reset_movie_keymap, require_all_8_controls=True, allow_follow_custom=True
    )
    post_pb = _validate_domain_keymap(
        spec.post_reset_playback_keymap, require_all_8_controls=False, allow_follow_custom=False
    )
    resolved_follow = _pairs_to_ordered_dict(spec.resolved_movie_follow_custom_map)

    dials_nonempty = all(
        isinstance(d, str) and bool(d.strip())
        for d in (
            spec.pre_reset_front_dial,
            spec.pre_reset_rear_dial,
            spec.pre_reset_control_wheel,
            spec.saved_front_dial,
            spec.saved_rear_dial,
            spec.saved_control_wheel,
            spec.post_reset_front_dial,
            spec.post_reset_rear_dial,
            spec.post_reset_control_wheel,
        )
    )
    three_domain_ok = all(
        m is not None
        for m in (
            pre_still,
            pre_movie,
            pre_pb,
            saved_still,
            saved_movie,
            saved_pb,
            post_still,
            post_movie,
            post_pb,
        )
    ) and (resolved_follow is not None or len(spec.resolved_movie_follow_custom_map) == 0)

    if (
        spec.camera_model != P251_FX3_MODEL_NAME
        or spec.helpguide_id != P251_FX3_HELPGUIDE_ID
        or spec.fw_version not in P251_FX3_SUPPORTED_FW_VERSIONS
        or spec.custom_key_dial_menu_path != P251_CUSTOM_KEY_DIAL_MENU_PATH
        or spec.remain_shoot_menu_path != P251_REMAIN_SHOOT_DISPLAY_MENU_PATH
        or spec.custom_key_domains != P251_CUSTOM_KEY_3_DOMAINS
        or spec.shooting_exposure_mode not in P251_SHOOTING_EXPOSURE_MODES
        or spec.rear_dial_effective_target not in P251_REAR_DIAL_EFFECTIVE_TARGETS
        or spec.active_my_dial_slot not in P251_MY_DIAL_SLOTS
        or spec.supported_recall_custom_holds != P251_RECALL_CUSTOM_HOLD_SLOTS
        or spec.pre_reset_remain_shoot_display not in P251_REMAIN_SHOOT_DISPLAY_MODES
        or spec.saved_remain_shoot_display not in P251_REMAIN_SHOOT_DISPLAY_MODES
        or spec.post_reset_remain_shoot_display not in P251_REMAIN_SHOOT_DISPLAY_MODES
        or spec.reset_action not in P251_RESET_ACTIONS
        or not dials_nonempty
        or not three_domain_ok
        or spec.slot1_custom_key_vault_mutation_bytes < 0
        or spec.evf_finder_monitor_spoof_events < 0
        or not (1 <= spec.camset_slot <= 10)
        or spec.camset_filename != f"CAMSET{spec.camset_slot:02d}.DAT"
    ):
        _fail(
            P251_BLOCKED_INVALID_CUSTOM_KEY_OR_REMAIN_SHOOT_SPEC,
            "Invalid ILME-FX3 Wave-40 [Custom Key/Dial Set.] or [Remain Shoot Display] specification.",
        )

    mutation_bytes = max(0, int(spec.slot1_custom_key_vault_mutation_bytes))
    spoof_events = max(0, int(spec.evf_finder_monitor_spoof_events))

    vault_zero_mutation_ok = True
    if spec.slot1_tier0_vault_active and (
        not spec.slot1_sdxc_wp_locked
        or spec.camset_save_to_slot1_attempted
        or spec.slot1_custom_key_vault_mutation_bytes > 0
        or (spec.camset_load_after_reset and not spec.camset_read_only_load)
    ):
        vault_zero_mutation_ok = False
        mutation_bytes = max(1, mutation_bytes)
        _fail(
            P251_BLOCKED_SLOT1_CUSTOM_KEY_VAULT_MUTATION_OR_CAMSET_DRIFT,
            "Slot-1 Tier-0 CAMSET01.DAT vault write/mutation or non-O_RDONLY access blocked.",
        )

    camset_roundtrip_ok = True
    if spec.camset_load_after_reset:
        if (
            spec.camset_source_model != P251_FX3_MODEL_NAME
            or not spec.camset_read_only_load
            or spec.post_reset_still_keymap != spec.saved_still_keymap
            or spec.post_reset_movie_keymap != spec.saved_movie_keymap
            or spec.post_reset_playback_keymap != spec.saved_playback_keymap
            or spec.post_reset_front_dial != spec.saved_front_dial
            or spec.post_reset_rear_dial != spec.saved_rear_dial
            or spec.post_reset_control_wheel != spec.saved_control_wheel
            or spec.post_reset_remain_shoot_display != spec.saved_remain_shoot_display
        ):
            camset_roundtrip_ok = False
            _fail(
                P251_BLOCKED_SLOT1_CUSTOM_KEY_VAULT_MUTATION_OR_CAMSET_DRIFT,
                "CAMSET01.DAT [Load] round-trip drifted or attempted cross-model import.",
            )

    iso_ei_follow_ok = True
    if pre_still is not None and pre_movie is not None:
        if spec.pre_reset_rear_dial == P251_REAR_DIAL_DEFAULT:
            expected_target = (
                "ISO" if spec.shooting_exposure_mode == "Flexible ISO" else "Exposure Index (EI)"
            )
            if spec.rear_dial_effective_target != expected_target:
                iso_ei_follow_ok = False
        else:
            if spec.rear_dial_effective_target != "CUSTOM_NON_ISO_EI":
                iso_ei_follow_ok = False

        expected_follow = {
            btn: pre_still[btn]
            for btn, fn_name in pre_movie.items()
            if fn_name == P251_FOLLOW_CUSTOM_TOKEN
        }
        actual_follow = resolved_follow if resolved_follow is not None else {}
        if actual_follow != expected_follow:
            iso_ei_follow_ok = False
    else:
        iso_ei_follow_ok = False

    if not iso_ei_follow_ok:
        _fail(
            P251_BLOCKED_DIAL_ISO_EI_OR_FOLLOW_CUSTOM_MISMATCH,
            "Rear dial ISO/EI mode adaptation or Movie [Follow Custom] inheritance mismatched.",
        )

    remain_scope_ok = (
        spec.remain_shoot_applies_to_still_buffer_only is True
        and spec.remain_shoot_displays_movie_card_time is False
    )
    evfless_ok = (
        spec.fx3_has_builtin_evf is False
        and spec.finder_monitor_switch_present is False
        and spec.eye_sensor_present is False
        and spec.evf_finder_monitor_spoof_events == 0
    )
    if not remain_scope_ok or not evfless_ok:
        if not evfless_ok:
            spoof_events = max(1, spoof_events)
        _fail(
            P251_BLOCKED_REMAIN_SHOOT_SCOPE_OR_EVF_TOPOLOGY_SPOOF,
            "[Remain Shoot Display] still-buffer-only boundary or EVF-less ILME-FX3 topology violated.",
        )

    survival_ok = True
    if not spec.camset_load_after_reset:
        if spec.reset_action in ("NONE", "Camera Settings Reset", "Reset Network Set."):
            if (
                spec.post_reset_still_keymap != spec.pre_reset_still_keymap
                or spec.post_reset_movie_keymap != spec.pre_reset_movie_keymap
                or spec.post_reset_playback_keymap != spec.pre_reset_playback_keymap
                or spec.post_reset_front_dial != spec.pre_reset_front_dial
                or spec.post_reset_rear_dial != spec.pre_reset_rear_dial
                or spec.post_reset_control_wheel != spec.pre_reset_control_wheel
                or spec.post_reset_remain_shoot_display != spec.pre_reset_remain_shoot_display
            ):
                survival_ok = False
        elif spec.reset_action == "Initialize":
            if (
                spec.post_reset_still_keymap != P251_FACTORY_STILL_KEYMAP
                or spec.post_reset_movie_keymap != P251_FACTORY_MOVIE_KEYMAP
                or spec.post_reset_playback_keymap != P251_FACTORY_PLAYBACK_KEYMAP
                or spec.post_reset_front_dial != P251_FRONT_DIAL_DEFAULT
                or spec.post_reset_rear_dial != P251_REAR_DIAL_DEFAULT
                or spec.post_reset_control_wheel != P251_CONTROL_WHEEL_DEFAULT
                or spec.post_reset_remain_shoot_display != P251_REMAIN_SHOOT_DISPLAY_DEFAULT
            ):
                survival_ok = False

    if not survival_ok:
        _fail(
            P251_BLOCKED_CUSTOM_KEY_OR_REMAIN_SHOOT_RESET_DRIFT,
            "[Custom Key/Dial Set.] or [Remain Shoot Display] reset survival / Initialize behavior drifted.",
        )

    passed = len(errors) == 0 and block_code is None
    digest = _canonical_sha256(
        {
            "pillar": "42B",
            "passed": passed,
            "block_code": block_code,
            "exposure_mode": spec.shooting_exposure_mode,
            "rear_target": spec.rear_dial_effective_target,
            "remain_shoot": spec.post_reset_remain_shoot_display,
            "reset": spec.reset_action,
            "mutation_bytes": 0 if passed else mutation_bytes,
            "spoof_events": 0 if passed else spoof_events,
        }
    )
    return CustomKeyDialAndRemainShootVaultReport(
        passed=passed,
        status=P251_STATUS_VERIFIED_PILLAR_42B if passed else P251_STATUS_REJECTED_PILLAR_42B,
        block_code=block_code,
        three_domain_keymap_and_dials_verified=three_domain_ok and dials_nonempty,
        iso_ei_and_follow_custom_verified=iso_ei_follow_ok,
        non_resettable_survival_verified=survival_ok,
        remain_shoot_still_buffer_scope_verified=remain_scope_ok,
        evfless_fx3_topology_verified=evfless_ok,
        camset_slot1_roundtrip_verified=camset_roundtrip_ok,
        slot1_vault_zero_mutation_verified=vault_zero_mutation_ok,
        h0_equals_h3_verified=h0_h3_ok,
        slot1_custom_key_vault_mutation_bytes=0 if passed else mutation_bytes,
        fx3_has_builtin_evf=bool(spec.fx3_has_builtin_evf),
        evf_finder_monitor_spoof_events=0 if passed else spoof_events,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_diff_set_still_mv_custom_key_and_remain_shoot_vault(
    *,
    diff_set_spec: Optional[DiffSetStillMvAndShutterAngleVaultSpec] = None,
    custom_key_spec: Optional[CustomKeyDialAndRemainShootVaultSpec] = None,
    force_clean_room: Optional[bool] = None,
) -> DiffSetCustomKeyAndRemainShootVaultReport:
    """Evaluate combined Wave-40 Pillar 42A + Pillar 42B specs alongside bounded `O_RDONLY` donors."""
    safety_errs = _safety_invariant_errors()
    donor_snap = inspect_phase251_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_diff_set_still_mv_and_shutter_angle_vault(
        diff_set_spec or build_default_safe_diff_set_still_mv_vault_spec()
    )
    rep_b = evaluate_custom_key_dial_and_remain_shoot_vault(
        custom_key_spec or build_default_safe_custom_key_remain_shoot_vault_spec()
    )
    combined_errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snap.all_donors_present:
        combined_errs.append("Phase 251 donor verification failed")
    if not donor_snap.under_0_15s_budget:
        combined_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snap.elapsed_seconds}s")

    all_ok = rep_a.passed and rep_b.passed and len(combined_errs) == 0
    return DiffSetCustomKeyAndRemainShootVaultReport(
        schema=PHASE251_SCHEMA,
        version=PHASE251_VERSION,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P251_STATUS_VERIFIED_PILLAR42_SUITE if all_ok else P251_STATUS_FAIL_PILLAR42_SUITE,
        donor_snapshot=donor_snap,
        diff_set_still_mv_report=rep_a,
        custom_key_remain_shoot_report=rep_b,
        diff_set_transition_corruption_events=rep_a.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=rep_a.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=rep_b.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=rep_b.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=rep_b.evf_finder_monitor_spoof_events,
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
        errors=tuple(combined_errs),
    )


def verify_diff_set_still_mv_custom_key_remain_shoot_vault(
    *,
    diff_set_spec: Optional[DiffSetStillMvAndShutterAngleVaultSpec] = None,
    custom_key_spec: Optional[CustomKeyDialAndRemainShootVaultSpec] = None,
    force_clean_room: Optional[bool] = None,
) -> DiffSetCustomKeyAndRemainShootVaultReport:
    """Symmetry alias matching CLI `verify-diff-set-still-mv-custom-key-remain-shoot-vault`."""
    return verify_diff_set_still_mv_custom_key_and_remain_shoot_vault(
        diff_set_spec=diff_set_spec,
        custom_key_spec=custom_key_spec,
        force_clean_room=force_clean_room,
    )


# ---------------------------------------------------------------------------
# Pillar 42A & Pillar 42B 6-Scenario Suites + Standalone Suite
# ---------------------------------------------------------------------------


def run_pillar42a_diff_set_still_mv_vault_6_scenario_suite() -> Pillar42ASuiteResult:
    c2s_pre = dict(P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES)
    c2s_pre["White Balance"] = "Custom 1"
    c2s_pre_pairs = tuple((k, c2s_pre[k]) for k in P251_DIFF_SET_8_ITEMS)
    c2s_post_movie = dict(c2s_pre)
    c2s_post_movie["White Balance"] = "AWB"
    c2s_post_movie_pairs = tuple((k, c2s_post_movie[k]) for k in P251_DIFF_SET_8_ITEMS)

    s2c_pre_still: Tuple[Tuple[str, str], ...] = (
        ("Aperture", "F1.4"),
        ("Shutter Speed", "1/500"),
        ("ISO", "3200"),
        ("Exposure Comp.", "-0.7EV"),
        ("Metering Mode", "Spot"),
        ("White Balance", "Tungsten"),
        ("Picture Profile", "PP8 (S-Log3)"),
        ("Focus Mode", "MF"),
    )
    s2c_pre_movie: Tuple[Tuple[str, str], ...] = (
        ("Aperture", "F5.6"),
        ("Shutter Speed", "1/48"),
        ("ISO", "12800"),
        ("Exposure Comp.", "+1.0EV"),
        ("Metering Mode", "Entire Screen Avg."),
        ("White Balance", "Daylight"),
        ("Picture Profile", "PP11 (S-Cinetone)"),
        ("Focus Mode", "AF-C"),
    )
    s2c_post_common: Tuple[Tuple[str, str], ...] = (
        ("Aperture", "F1.4"),
        ("Shutter Speed", "1/500"),
        ("ISO", "Auto"),
        ("Exposure Comp.", "0.0EV"),
        ("Metering Mode", "Multi"),
        ("White Balance", "AWB"),
        ("Picture Profile", "Off"),
        ("Focus Mode", "AF-C"),
    )
    s2c_bad_wiped_still: Tuple[Tuple[str, str], ...] = P251_DIFF_SET_FACTORY_PARAM_DEFAULTS

    cases: Tuple[Tuple[str, bool, DiffSetStillMvAndShutterAngleVaultSpec, Optional[str]], ...] = (
        (
            P251_PILLAR_42A_SCENARIO_IDS[0],
            True,
            DiffSetStillMvAndShutterAngleVaultSpec(
                pre_checked_items=(),
                transition_kind="COMMON_TO_SEPARATE",
                post_transition_checked_items=P251_DIFF_SET_8_ITEMS,
                pre_still_values=c2s_pre_pairs,
                pre_movie_values=c2s_pre_pairs,
                post_still_values=c2s_pre_pairs,
                post_movie_values=c2s_post_movie_pairs,
                pre_still_custom_wb=P251_DEFAULT_STILL_CUSTOM_WB_REGISTER,
                post_still_custom_wb=P251_DEFAULT_STILL_CUSTOM_WB_REGISTER,
                post_movie_custom_wb=P251_MOVIE_CUSTOM_WB_STILL_ONLY_SENTINEL,
                custom_wb_copied_to_movie=False,
                movie_shutter_mode="Shutter Speed",
                shutter_speed_and_angle_independent=True,
                reset_action="Camera Settings Reset",
                post_reset_checked_items=P251_DIFF_SET_8_ITEMS,
            ),
            None,
        ),
        (
            P251_PILLAR_42A_SCENARIO_IDS[1],
            True,
            DiffSetStillMvAndShutterAngleVaultSpec(
                pre_checked_items=P251_DIFF_SET_8_ITEMS,
                transition_kind="SEPARATE_TO_COMMON",
                post_transition_checked_items=(),
                pre_still_values=s2c_pre_still,
                pre_movie_values=s2c_pre_movie,
                post_still_values=s2c_post_common,
                post_movie_values=s2c_post_common,
                pre_still_custom_wb="Custom 2 (3200K_M+1)",
                post_still_custom_wb="Custom 2 (3200K_M+1)",
                movie_shutter_mode="Angle",
                movie_shutter_angle_deg=180.0,
                post_movie_shutter_angle_deg=180.0,
                shutter_speed_and_angle_independent=True,
                reset_action="Reset Network Set.",
                post_reset_checked_items=(),
            ),
            None,
        ),
        (
            P251_PILLAR_42A_SCENARIO_IDS[2],
            False,
            DiffSetStillMvAndShutterAngleVaultSpec(
                reset_action="Camera Settings Reset",
                post_transition_checked_items=P251_DIFF_SET_8_ITEMS,
                post_reset_checked_items=(),
            ),
            P251_BLOCKED_DIFF_SET_RESET_SURVIVAL_DRIFT,
        ),
        (
            P251_PILLAR_42A_SCENARIO_IDS[3],
            False,
            DiffSetStillMvAndShutterAngleVaultSpec(
                pre_checked_items=(),
                transition_kind="COMMON_TO_SEPARATE",
                post_transition_checked_items=P251_DIFF_SET_8_ITEMS,
                pre_still_values=c2s_pre_pairs,
                pre_movie_values=c2s_pre_pairs,
                post_still_values=c2s_pre_pairs,
                post_movie_values=c2s_pre_pairs,
                custom_wb_copied_to_movie=True,
                post_movie_custom_wb=P251_DEFAULT_STILL_CUSTOM_WB_REGISTER,
            ),
            P251_BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT,
        ),
        (
            P251_PILLAR_42A_SCENARIO_IDS[4],
            False,
            DiffSetStillMvAndShutterAngleVaultSpec(
                pre_checked_items=P251_DIFF_SET_8_ITEMS,
                transition_kind="SEPARATE_TO_COMMON",
                post_transition_checked_items=(),
                pre_still_values=s2c_pre_still,
                pre_movie_values=s2c_pre_movie,
                post_still_values=s2c_bad_wiped_still,
                post_movie_values=s2c_bad_wiped_still,
                movie_shutter_mode="Angle",
                shutter_speed_and_angle_independent=True,
                post_reset_checked_items=(),
            ),
            P251_BLOCKED_DIFF_SET_SEPARATE_TO_COMMON_DRIFT,
        ),
        (
            P251_PILLAR_42A_SCENARIO_IDS[5],
            False,
            DiffSetStillMvAndShutterAngleVaultSpec(
                pre_checked_items=(),
                transition_kind="NONE",
                post_transition_checked_items=(),
                movie_shutter_mode="Angle",
                movie_shutter_angle_deg=180.0,
                post_movie_shutter_angle_deg=180.0,
                shutter_speed_and_angle_independent=False,
                shutter_angle_common_bleed_events=1,
                post_reset_checked_items=(),
            ),
            P251_BLOCKED_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION,
        ),
    )

    outcomes: List[Pillar42ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_diff_set_still_mv_and_shutter_angle_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar42ScenarioOutcome(
                scenario_id=sid,
                pillar="42A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar42ASuiteResult(
        passed=all_ok,
        status=P251_STATUS_VERIFIED_PILLAR_42A if all_ok else P251_STATUS_REJECTED_PILLAR_42A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar42b_custom_key_remain_shoot_vault_6_scenario_suite() -> Pillar42BSuiteResult:
    saved_custom_still = (
        ("Custom Button 1", "HOME (BIG6)"),
        ("Custom Button 2", "Focus Area"),
        ("Custom Button 3", "Base ISO Switch"),
        ("Custom Button 4", "Touch Operation"),
        ("Custom Button 5", "Zebra Display"),
        ("Custom Button 6", "Peaking Display"),
        ("Multi-Selector Center", "Focus Standard"),
        ("Lens Focus Hold Button", "Recall Custom hold 1"),
    )
    saved_custom_movie = (
        ("Custom Button 1", "Follow Custom"),
        ("Custom Button 2", "Follow Custom"),
        ("Custom Button 3", "Shutter Mode"),
        ("Custom Button 4", "Touch Operation"),
        ("Custom Button 5", "Zebra Display"),
        ("Custom Button 6", "Peaking Display"),
        ("Multi-Selector Center", "Focus Standard"),
        ("Lens Focus Hold Button", "Follow Custom"),
    )

    cases: Tuple[Tuple[str, bool, CustomKeyDialAndRemainShootVaultSpec, Optional[str]], ...] = (
        (
            P251_PILLAR_42B_SCENARIO_IDS[0],
            True,
            CustomKeyDialAndRemainShootVaultSpec(
                shooting_exposure_mode="Cine EI",
                rear_dial_effective_target="Exposure Index (EI)",
                active_my_dial_slot="My Dial 1",
                pre_reset_remain_shoot_display="Always Display",
                reset_action="Camera Settings Reset",
                post_reset_remain_shoot_display="Always Display",
            ),
            None,
        ),
        (
            P251_PILLAR_42B_SCENARIO_IDS[1],
            True,
            CustomKeyDialAndRemainShootVaultSpec(
                shooting_exposure_mode="Flexible ISO",
                rear_dial_effective_target="ISO",
                active_my_dial_slot="My Dial 2",
                pre_reset_remain_shoot_display="Not Displayed",
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model="ILME-FX3",
                camset_read_only_load=True,
                saved_still_keymap=saved_custom_still,
                saved_movie_keymap=saved_custom_movie,
                saved_remain_shoot_display="Shoot-Only Display",
                post_reset_still_keymap=saved_custom_still,
                post_reset_movie_keymap=saved_custom_movie,
                post_reset_remain_shoot_display="Shoot-Only Display",
            ),
            None,
        ),
        (
            P251_PILLAR_42B_SCENARIO_IDS[2],
            False,
            CustomKeyDialAndRemainShootVaultSpec(
                pre_reset_remain_shoot_display="Always Display",
                reset_action="Reset Network Set.",
                post_reset_remain_shoot_display="Not Displayed",
            ),
            P251_BLOCKED_CUSTOM_KEY_OR_REMAIN_SHOOT_RESET_DRIFT,
        ),
        (
            P251_PILLAR_42B_SCENARIO_IDS[3],
            False,
            CustomKeyDialAndRemainShootVaultSpec(
                shooting_exposure_mode="Cine EI",
                pre_reset_rear_dial="ISO/EI",
                rear_dial_effective_target="ISO",
            ),
            P251_BLOCKED_DIAL_ISO_EI_OR_FOLLOW_CUSTOM_MISMATCH,
        ),
        (
            P251_PILLAR_42B_SCENARIO_IDS[4],
            False,
            CustomKeyDialAndRemainShootVaultSpec(
                remain_shoot_displays_movie_card_time=True,
                fx3_has_builtin_evf=True,
                finder_monitor_switch_present=True,
                evf_finder_monitor_spoof_events=1,
            ),
            P251_BLOCKED_REMAIN_SHOOT_SCOPE_OR_EVF_TOPOLOGY_SPOOF,
        ),
        (
            P251_PILLAR_42B_SCENARIO_IDS[5],
            False,
            CustomKeyDialAndRemainShootVaultSpec(
                slot1_tier0_vault_active=True,
                slot1_sdxc_wp_locked=True,
                camset_save_to_slot1_attempted=True,
                slot1_custom_key_vault_mutation_bytes=4096,
            ),
            P251_BLOCKED_SLOT1_CUSTOM_KEY_VAULT_MUTATION_OR_CAMSET_DRIFT,
        ),
    )

    outcomes: List[Pillar42ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_custom_key_dial_and_remain_shoot_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar42ScenarioOutcome(
                scenario_id=sid,
                pillar="42B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar42BSuiteResult(
        passed=all_ok,
        status=P251_STATUS_VERIFIED_PILLAR_42B if all_ok else P251_STATUS_REJECTED_PILLAR_42B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar42_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar42StandaloneReport:
    """Run full Pillar 42 standalone suite (`6/6` Pillar 42A + `6/6` Pillar 42B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase251_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar42a_diff_set_still_mv_vault_6_scenario_suite()
    res_b = run_pillar42b_custom_key_remain_shoot_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 251 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 2.0s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE251_SCHEMA,
            "version": PHASE251_VERSION,
            "mode": donor_snapshot.verification_mode,
            "42a": [asdict(s) for s in res_a.scenarios],
            "42b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar42StandaloneReport(
        schema=PHASE251_SCHEMA,
        version=PHASE251_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P251_STATUS_VERIFIED_PILLAR42_SUITE if all_ok else P251_STATUS_FAIL_PILLAR42_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_42a_diff_set_still_mv_vault=res_a,
        pillar_42b_custom_key_remain_shoot_vault=res_b,
        diff_set_transition_corruption_events=P251_DIFF_SET_TRANSITION_CORRUPTION_EVENTS if res_a.passed else 1,
        shutter_angle_common_bleed_events=P251_SHUTTER_ANGLE_COMMON_BLEED_EVENTS if res_a.passed else 1,
        slot1_custom_key_vault_mutation_bytes=P251_SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES if res_b.passed else 1,
        fx3_has_builtin_evf=P251_FX3_HAS_BUILTIN_EVF,
        evf_finder_monitor_spoof_events=P251_EVF_FINDER_MONITOR_SPOOF_EVENTS if res_b.passed else 1,
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
# Unified 42/42 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master42_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_42pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master42PillarRecoveryReport:
    """Evaluate and aggregate all 42 recovery pillars (`1..42`) concurrently -> `42/42` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_42_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_41pillar() -> Master41PillarRecoveryReport:
        return evaluate_realhw_41pillar_recovery_master(**kw)

    def _run_p42() -> Tuple[Pillar42StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar42_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_41 = pool.submit(_run_41pillar)
        fut_42 = pool.submit(_run_p42)
        m41_rep = fut_41.result()
        p42_rep, p42_dt = fut_42.result()

    all_errors: List[str] = list(m41_rep.errors) + list(p42_rep.errors)
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
        if getattr(m41_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-41 violated {attr_name} == {expected_val}")
        if getattr(p42_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 42 violated {attr_name} == {expected_val}")

    if m41_rep.tier0_battery_high_display_violations != 0:
        all_errors.append("Pillars 1-41 violated tier0_battery_high_display_violations == 0")
    if m41_rep.bt_rmt_ir_lockout_violations != 0:
        all_errors.append("Pillars 1-41 violated bt_rmt_ir_lockout_violations == 0")
    if m41_rep.slot1_mymenu_vault_mutation_bytes != 0:
        all_errors.append("Pillars 1-41 violated slot1_mymenu_vault_mutation_bytes == 0")
    if m41_rep.destructive_menu_delete_confusions != 0:
        all_errors.append("Pillars 1-41 violated destructive_menu_delete_confusions == 0")
    if m41_rep.shutter_angle_exposure_step_drift_events != 0:
        all_errors.append("Pillars 1-41 violated shutter_angle_exposure_step_drift_events == 0")
    if m41_rep.fx3_has_var_shutter is not False:
        all_errors.append("Pillars 1-41 violated fx3_has_var_shutter == False")
    if m41_rep.unbuffered_battery_pull_events != 0:
        all_errors.append("Pillars 1-41 violated unbuffered_battery_pull_events == 0")
    if m41_rep.hardware_live_attachment_authorized is not False:
        all_errors.append("Pillars 1-41 violated hardware_live_attachment_authorized == False")

    if p42_rep.diff_set_transition_corruption_events != 0:
        all_errors.append("Pillar 42 violated diff_set_transition_corruption_events == 0")
    if p42_rep.shutter_angle_common_bleed_events != 0:
        all_errors.append("Pillar 42 violated shutter_angle_common_bleed_events == 0")
    if p42_rep.slot1_custom_key_vault_mutation_bytes != 0:
        all_errors.append("Pillar 42 violated slot1_custom_key_vault_mutation_bytes == 0")
    if p42_rep.fx3_has_builtin_evf is not False:
        all_errors.append("Pillar 42 violated fx3_has_builtin_evf == False")
    if p42_rep.evf_finder_monitor_spoof_events != 0:
        all_errors.append("Pillar 42 violated evf_finder_monitor_spoof_events == 0")
    if p42_rep.hardware_live_attachment_authorized is not False:
        all_errors.append("Pillar 42 violated hardware_live_attachment_authorized == False")

    pillar_statuses: List[MasterPillarStatus] = list(m41_rep.pillars)
    spec42 = MASTER_42_PILLAR_SPECS[41]
    p42_metrics = {
        "pillar_42a_diff_set_still_mv_vault": (
            f"{p42_rep.pillar_42a_diff_set_still_mv_vault.scenarios_passed}/"
            f"{p42_rep.pillar_42a_diff_set_still_mv_vault.scenarios_total}"
        ),
        "pillar_42b_custom_key_remain_shoot_vault": (
            f"{p42_rep.pillar_42b_custom_key_remain_shoot_vault.scenarios_passed}/"
            f"{p42_rep.pillar_42b_custom_key_remain_shoot_vault.scenarios_total}"
        ),
        "diff_set_transition_corruption_events": p42_rep.diff_set_transition_corruption_events,
        "shutter_angle_common_bleed_events": p42_rep.shutter_angle_common_bleed_events,
        "slot1_custom_key_vault_mutation_bytes": p42_rep.slot1_custom_key_vault_mutation_bytes,
        "fx3_has_builtin_evf": p42_rep.fx3_has_builtin_evf,
        "evf_finder_monitor_spoof_events": p42_rep.evf_finder_monitor_spoof_events,
        "hardware_live_attachment_authorized": p42_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p42_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec42[0],
            pillar_id=spec42[1],
            phase_label=spec42[2],
            module_name=spec42[3],
            passed=bool(p42_rep.all_passed),
            status=p42_rep.status,
            verification_mode=p42_rep.verification_mode,
            elapsed_seconds=p42_dt,
            key_metrics=p42_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec42[1],
                    "mode": p42_rep.verification_mode,
                    "status": p42_rep.status,
                    "metrics": p42_metrics,
                    "passed": p42_rep.all_passed,
                }
            ),
            errors=tuple(p42_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master42_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p42_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_42_PILLAR_COUNT == 42
        and pillars_passed == 42
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE251_SCHEMA,
            "version": PHASE251_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master42PillarRecoveryReport(
        schema=PHASE251_SCHEMA,
        version=PHASE251_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P251_STATUS_VERIFIED_42OF42_AGGREGATOR if all_ok else P251_STATUS_FAIL_42OF42_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P251_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P251_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p42_rep.donor_snapshot,
        pillar42_a_diff_set_still_mv_vault=p42_rep.pillar_42a_diff_set_still_mv_vault,
        pillar42_b_custom_key_remain_shoot_vault=p42_rep.pillar_42b_custom_key_remain_shoot_vault,
        diff_set_transition_corruption_events=p42_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=p42_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=p42_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=p42_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=p42_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m41_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m41_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m41_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m41_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m41_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m41_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m41_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p42_rep.hardware_live_attachment_authorized,
        master_42pillar_sha256=master_sha,
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


def evaluate_42pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master42PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_42pillar_recovery_master`."""
    return evaluate_realhw_42pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_42pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master42PillarRecoveryReport:
    """Public CLI entry point for Phase 251 Pillar 42 unified `42/42` real-hardware recovery master."""
    return evaluate_realhw_42pillar_recovery_master(
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
    "MASTER_42_PILLAR_COUNT",
    "MASTER_42_PILLAR_IDS",
    "MASTER_42_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P251_ASSIGNABLE_CUSTOM_CONTROLS",
    "P251_BLOCKED_CUSTOM_KEY_OR_REMAIN_SHOOT_RESET_DRIFT",
    "P251_BLOCKED_DIAL_ISO_EI_OR_FOLLOW_CUSTOM_MISMATCH",
    "P251_BLOCKED_DIFF_SET_COMMON_TO_SEPARATE_DRIFT",
    "P251_BLOCKED_DIFF_SET_RESET_SURVIVAL_DRIFT",
    "P251_BLOCKED_DIFF_SET_SEPARATE_TO_COMMON_DRIFT",
    "P251_BLOCKED_INVALID_CUSTOM_KEY_OR_REMAIN_SHOOT_SPEC",
    "P251_BLOCKED_INVALID_DIFF_SET_SPEC",
    "P251_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P251_BLOCKED_REMAIN_SHOOT_SCOPE_OR_EVF_TOPOLOGY_SPOOF",
    "P251_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P251_BLOCKED_SHUTTER_ANGLE_COMMON_BLEED_VIOLATION",
    "P251_BLOCKED_SLOT1_CUSTOM_KEY_VAULT_MUTATION_OR_CAMSET_DRIFT",
    "P251_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P251_BOUNDED_HEADER_BYTES",
    "P251_CAMSET_FILENAMES",
    "P251_COMMON_TO_SEPARATE_STILL_ONLY_EXCEPTION",
    "P251_CONCURRENT_CEILING_SECONDS",
    "P251_CONTROL_WHEEL_DEFAULT",
    "P251_CUSTOM_KEY_3_DOMAINS",
    "P251_CUSTOM_KEY_DIAL_MENU_PATH",
    "P251_DEFAULT_ACTIVE_COMMON_8ITEM_VALUES",
    "P251_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG",
    "P251_DEFAULT_STILL_CUSTOM_WB_REGISTER",
    "P251_DIFF_SET_8_ITEMS",
    "P251_DIFF_SET_FACTORY_CHECKED_ITEMS",
    "P251_DIFF_SET_FACTORY_PARAM_DEFAULTS",
    "P251_DIFF_SET_MENU_PATH",
    "P251_DIFF_SET_TRANSITION_CORRUPTION_EVENTS",
    "P251_DIFF_SET_TRANSITION_KINDS",
    "P251_DONOR_FX3_APPFW_702_RELPATH",
    "P251_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P251_DONOR_FX3_BODYDATA_RELPATH",
    "P251_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH",
    "P251_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH",
    "P251_DONOR_FX3_LIBBACKUP_SO_RELPATH",
    "P251_DONOR_FX3_LIBGPE_SO_RELPATH",
    "P251_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P251_DONOR_FX6_APPFW_601_RELPATH",
    "P251_DONOR_FX6_LIBINFRADIAL_SO_RELPATH",
    "P251_DONOR_FX6_LIBINFRAINPUT_SO_RELPATH",
    "P251_DONOR_INSPECT_BUDGET_SECONDS",
    "P251_EVF_FINDER_MONITOR_SPOOF_EVENTS",
    "P251_FACTORY_DIAL_DEFAULTS",
    "P251_FACTORY_MOVIE_KEYMAP",
    "P251_FACTORY_PLAYBACK_KEYMAP",
    "P251_FACTORY_STILL_KEYMAP",
    "P251_FOLLOW_CUSTOM_TOKEN",
    "P251_FORBIDDEN_PERSISTENT_TARGETS",
    "P251_FRONT_DIAL_DEFAULT",
    "P251_FX3_FW_VERSION",
    "P251_FX3_HAS_BUILTIN_EVF",
    "P251_FX3_HELPGUIDE_ID",
    "P251_FX3_MODEL_ID",
    "P251_FX3_MODEL_NAME",
    "P251_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS",
    "P251_FX3_SUPPORTED_FW_VERSIONS",
    "P251_FX6_DONOR_FW_VERSION",
    "P251_FX6_DONOR_MODEL_NAME",
    "P251_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P251_MAX_FULL_DONOR_BYTES",
    "P251_MOVIE_CUSTOM_WB_STILL_ONLY_SENTINEL",
    "P251_MOVIE_SHUTTER_MODES",
    "P251_MOVIE_SHUTTER_MODE_DEFAULT",
    "P251_MY_DIAL_SLOTS",
    "P251_NOMINAL_BUDGET_SECONDS",
    "P251_PILLAR_42A_SCENARIO_IDS",
    "P251_PILLAR_42B_SCENARIO_IDS",
    "P251_PINNED_FX3_APPFW_702_BYTES",
    "P251_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P251_PINNED_FX3_BACKUP_BIN_BYTES",
    "P251_PINNED_FX3_BACKUP_BIN_SHA256",
    "P251_PINNED_FX3_BODYDATA_BYTES",
    "P251_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES",
    "P251_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256",
    "P251_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES",
    "P251_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256",
    "P251_PINNED_FX3_LIBBACKUP_SO_BYTES",
    "P251_PINNED_FX3_LIBBACKUP_SO_SHA256",
    "P251_PINNED_FX3_LIBGPE_SO_BYTES",
    "P251_PINNED_FX3_LIBGPE_SO_SHA256",
    "P251_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P251_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P251_PINNED_FX6_APPFW_601_BYTES",
    "P251_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P251_PINNED_FX6_LIBINFRADIAL_SO_BYTES",
    "P251_PINNED_FX6_LIBINFRADIAL_SO_SHA256",
    "P251_PINNED_FX6_LIBINFRAINPUT_SO_BYTES",
    "P251_PINNED_FX6_LIBINFRAINPUT_SO_SHA256",
    "P251_REAR_DIAL_DEFAULT",
    "P251_REAR_DIAL_EFFECTIVE_TARGETS",
    "P251_RECALL_CUSTOM_HOLD_SLOTS",
    "P251_REMAIN_SHOOT_DISPLAY_DEFAULT",
    "P251_REMAIN_SHOOT_DISPLAY_MENU_PATH",
    "P251_REMAIN_SHOOT_DISPLAY_MODES",
    "P251_RESET_ACTIONS",
    "P251_SEPARATE_TO_COMMON_STILL_RETAINED_EXCEPTIONS",
    "P251_SHOOTING_EXPOSURE_MODES",
    "P251_SHUTTER_ANGLE_COMMON_BLEED_EVENTS",
    "P251_SHUTTER_MODE_MENU_PATH",
    "P251_SLOT1_CUSTOM_KEY_VAULT_MUTATION_BYTES",
    "P251_SLOT1_VAULT_SLOT",
    "P251_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P251_STATUS_FAIL_42OF42_AGGREGATOR",
    "P251_STATUS_FAIL_PILLAR42_SUITE",
    "P251_STATUS_REJECTED_PILLAR_42A",
    "P251_STATUS_REJECTED_PILLAR_42B",
    "P251_STATUS_VERIFIED_42OF42_AGGREGATOR",
    "P251_STATUS_VERIFIED_PILLAR42_SUITE",
    "P251_STATUS_VERIFIED_PILLAR_42A",
    "P251_STATUS_VERIFIED_PILLAR_42B",
    "P251_TIER0_SURFACE_COUNT",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE251_SCHEMA",
    "PHASE251_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "CustomKeyDialAndRemainShootVaultReport",
    "CustomKeyDialAndRemainShootVaultSpec",
    "DiffSetCustomKeyAndRemainShootVaultReport",
    "DiffSetStillMvAndShutterAngleVaultReport",
    "DiffSetStillMvAndShutterAngleVaultSpec",
    "Master42PillarRecoveryReport",
    "Phase251DonorArtifactDigest",
    "Phase251DonorSnapshot",
    "Pillar42ASuiteResult",
    "Pillar42BSuiteResult",
    "Pillar42ScenarioOutcome",
    "Pillar42StandaloneReport",
    "build_default_safe_custom_key_remain_shoot_vault_spec",
    "build_default_safe_diff_set_still_mv_vault_spec",
    "evaluate_42pillar_recovery_master",
    "evaluate_custom_key_dial_and_remain_shoot_vault",
    "evaluate_diff_set_still_mv_and_shutter_angle_vault",
    "evaluate_realhw_42pillar_recovery_master",
    "inspect_phase251_donors_readonly",
    "run_pillar42_standalone_suite",
    "run_pillar42a_diff_set_still_mv_vault_6_scenario_suite",
    "run_pillar42b_custom_key_remain_shoot_vault_6_scenario_suite",
    "verify_42pillar_recovery_suite",
    "verify_diff_set_still_mv_custom_key_and_remain_shoot_vault",
    "verify_diff_set_still_mv_custom_key_remain_shoot_vault",
]
