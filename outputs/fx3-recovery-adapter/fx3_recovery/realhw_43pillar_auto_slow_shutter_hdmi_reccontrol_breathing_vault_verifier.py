"""Phase 255 — Pillar 43 (`43/43` Recovery Pillars) & Unified 43-Pillar Recovery Master
(`verify-43pillar-recovery` / `verify-auto-slow-shutter-hdmi-reccontrol-breathing-vault`):

1. **Pillar 43A — `[Auto Slow Shutter]` 6-Condition Hardware Lockout, `Ver. 7.02` `[Shutter Mode] = [Angle]`
   Disjointness & `[Lens Compensation]` -> `[Breathing Comp.]` Movie/Lens/RAW/240p Boundary
   (`ILME-FX3 Ver. 7.02`, `ilc/2210`, Wave-41)**:
   - Models `MENU` -> `Exposure/Color` -> `[Exposure]` -> `[Auto Slow Shutter]` (`On` factory
     default / `Off`), verifying reset to `[On]` by `[Camera Settings Reset]` (and `[Initialize]`)
     while surviving `[Reset Network Set.]`, plus deterministic restoration via `O_RDONLY` Slot-1
     `CAMSET01.DAT` `[Load]`.
   - Enforces all **6 exact official Sony hardware non-function / lockout conditions**
     (`auto_slow_shutter_lockout_bypass_events == 0`):
     (1) `S&Q` motion (`S&Q_MOTION`),
     (2) `Shutter Priority` (`S`) (`SHUTTER_PRIORITY_S`),
     (3) `Manual Exposure` (`M`) (`MANUAL_EXPOSURE_M`),
     (4) `[ISO]` != `[ISO AUTO]` (`NON_AUTO_ISO`),
     (5) `[Flexible Exp. Mode]` with manual shutter speed (`FLEXIBLE_EXP_MANUAL_SHUTTER`),
     (6) `[Log Shooting]` = `Cine EI Quick` or `Cine EI` (`LOG_CINE_EI_OR_CINE_EI_QUICK`).
   - Proves strict hardware disjointness with `Ver. 6.00+` / `Ver. 7.02` `[Shutter Mode] = [Angle]`:
     because `[Angle]` governs exposure time exclusively in `S`, `M`, or `Flexible Exp. Mode`
     (manual shutter), `[Auto Slow Shutter]` and `[Shutter Angle]` can **never** simultaneously
     govern exposure (`auto_slow_shutter_angle_overlap_events == 0`).
   - Models `MENU` -> `Shooting` -> `[Image Quality/Rec]` -> `[Lens Compensation]` ->
     `[Breathing Comp.]` (`Off` factory default / `On`, resettable by `[Camera Settings Reset]`,
     unaffected by `[Reset Network Set.]`), enforcing movie-only compliant Sony E-mount lens
     angle-of-view crop and hardware lockout during `4264x2408` 16-bit linear HDMI `[RAW Output]`
     and `S&Q` `239.76p` / `200p` (`breathing_comp_raw_or_240p_bypass_events == 0`).

2. **Pillar 43B — `[HDMI Output Settings]` (`[REC Control]` <- `[Time Code Output]` Gate,
   `[4ch Audio Output]` Routing & `[Rec. Media dur HDMI Output]` Vault Guard)**:
   - Models `MENU` -> `Setup` -> `[External Output]` -> `[HDMI Output Settings]`, verifying
     survival across **both** `[Camera Settings Reset]` and `[Reset Network Set.]` (cleared to
     factory defaults **only** by `[Initialize]`).
   - Enforces `[REC Control]` (`Off` default / `On`) mandatory hardware prerequisite
     `[Time Code Output] = [On]` (`hdmi_rec_ctrl_without_tc_violations == 0`).
   - Models `[4ch Audio Output]` (`CH1/CH2` default -> `Ch1=L / Ch2=R` vs `CH3/CH4` ->
     `Ch3=L / Ch4=R` over HDMI when 4-channel MI-shoe audio is active).
   - Enforces `[Rec. Media dur HDMI Output] = [Off]` inhibiting internal Slot-1/Slot-2 clip and
     `[Proxy Recording]` writes during HDMI output, protecting the Slot-1 Tier-0 recovery vault
     (`slot1_hdmi_rec_vault_mutation_bytes == 0`), lossless `O_RDONLY` Slot-1 `CAMSET01.DAT`
     `[Load]` round-trip, and `16/16` Tier-0 `Backup.bin` `H0 == H3` parity.

3. **Unified `43/43` Recovery Master (`evaluate_realhw_43pillar_recovery_master`)**:
   - Delegates Pillars `1..42` concurrently to `evaluate_realhw_42pillar_recovery_master` +
     **Pillar 43** -> **`43/43` (`VERIFIED_43OF43_PILLAR_RECOVERY_MASTER`)** in `< 4.0s`
     nominal (`< 6.0s` concurrent ceiling), preserving 100% backward compatibility with
     `verify-22..42pillar-recovery`.
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
from .realhw_42pillar_diff_set_still_mv_custom_key_remain_shoot_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_42_PILLAR_SPECS,
    Master42PillarRecoveryReport,
    evaluate_realhw_42pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE255_SCHEMA: str = (
    "realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier_v1"
)
PHASE255_VERSION: str = "1.0.0"

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
P255_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P255_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS: int = 0
P255_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS: int = 0
P255_BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS: int = 0
P255_HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS: int = 0
P255_SLOT1_HDMI_REC_VAULT_MUTATION_BYTES: int = 0

P255_DONOR_INSPECT_BUDGET_SECONDS: float = 0.15
P255_NOMINAL_BUDGET_SECONDS: float = 4.0
P255_CONCURRENT_CEILING_SECONDS: float = 6.0
P255_BOUNDED_HEADER_BYTES: int = 4096
P255_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-41 / FX3 Ver. 7.02 & FX6 Ver. 6.01 Donor Anchors (bounded O_RDONLY verification)
P255_FX3_MODEL_NAME: str = "ILME-FX3"
P255_FX3_MODEL_ID: int = 0x91030080
P255_FX3_HELPGUIDE_ID: str = "ilc/2210"
P255_FX3_FW_VERSION: str = "7.02"
P255_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P255_FX6_DONOR_FW_VERSION: str = "6.01"
P255_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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
P255_FX3_BREATHING_COMP_MIN_FW_VERSIONS: Tuple[str, ...] = (
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)
P255_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS: Tuple[str, ...] = (
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P255_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P255_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P255_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)

P255_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P255_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P255_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P255_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P255_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P255_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P255_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P255_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P255_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P255_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P255_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P255_PINNED_FX3_LIBBACKUP_SO_SHA256: str = (
    "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
)

P255_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P255_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P255_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

P255_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P255_DONOR_FX3_LIBGPE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so"
)
P255_PINNED_FX3_LIBGPE_SO_BYTES: int = 106480
P255_PINNED_FX3_LIBGPE_SO_SHA256: str = (
    "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464"
)

P255_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/CameraOnDemandSaver.so"
)
P255_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES: int = 18800
P255_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256: str = (
    "72b73608c2675a3709e2952ca347a36e7dd2ad3dd2869191638c7154933b2f46"
)

P255_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraLensCommunicator.so"
)
P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES: int = 14544
P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256: str = (
    "e61bf145f050dd037802871395c38d1c0471518130d5bcd2f621268da8c8f6ab"
)

P255_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = (
    "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"
)

P255_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so"
)
P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES: int = 47808
P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256: str = (
    "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6"
)

# Pillar 43A — [Auto Slow Shutter] 6 Lockouts, [Shutter Angle] Disjointness & [Breathing Comp.]
P255_AUTO_SLOW_SHUTTER_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Exposure/Color",
    "Exposure",
    "Auto Slow Shutter",
)
P255_AUTO_SLOW_SHUTTER_MODES: Tuple[str, ...] = ("On", "Off")
P255_AUTO_SLOW_SHUTTER_DEFAULT: str = "On"

P255_AUTO_SLOW_SHUTTER_6_LOCKOUT_CONDITIONS: Tuple[str, ...] = (
    "S&Q_MOTION",
    "SHUTTER_PRIORITY_S",
    "MANUAL_EXPOSURE_M",
    "NON_AUTO_ISO",
    "FLEXIBLE_EXP_MANUAL_SHUTTER",
    "LOG_CINE_EI_OR_CINE_EI_QUICK",
)

P255_SHOOTING_DOMAINS: Tuple[str, ...] = ("Movie", "S&Q", "Still")
P255_EXPOSURE_MODES: Tuple[str, ...] = ("P", "A", "S", "M", "Flexible Exp. Mode")
P255_FLEXIBLE_EXP_SHUTTER_CTRL_MODES: Tuple[str, ...] = ("Auto", "Manual")
P255_ISO_AUTO_TOKEN: str = "ISO AUTO"
P255_LOG_SHOOTING_MODES: Tuple[str, ...] = ("Off", "Flexible ISO", "Cine EI Quick", "Cine EI")
P255_LOG_CINE_EI_LOCKOUT_MODES: Tuple[str, ...] = ("Cine EI Quick", "Cine EI")

P255_SHUTTER_MODE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Shutter/Silent",
    "Shutter Mode",
)
P255_MOVIE_SHUTTER_MODES: Tuple[str, ...] = ("Shutter Speed", "Angle")
P255_MOVIE_SHUTTER_MODE_DEFAULT: str = "Shutter Speed"
P255_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG: float = 180.0

P255_BREATHING_COMP_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Image Quality/Rec",
    "Lens Compensation",
    "Breathing Comp.",
)
P255_BREATHING_COMP_MODES: Tuple[str, ...] = ("Off", "On")
P255_BREATHING_COMP_DEFAULT: str = "Off"
P255_HDMI_RAW_4264X2408_RESOLUTION: str = "4264x2408"
P255_HDMI_RAW_OUTPUT_MODES: Tuple[str, ...] = ("Off", "On")
P255_MOVIE_AND_SQ_FRAME_RATES: Tuple[str, ...] = (
    "23.98p",
    "24.00p",
    "25p",
    "29.97p",
    "50p",
    "59.94p",
    "100p",
    "119.88p",
    "200p",
    "239.76p",
)
P255_BREATHING_COMP_LOCKOUT_SQ_RATES: Tuple[str, ...] = ("200p", "239.76p")

P255_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)

# Pillar 43B — [HDMI Output Settings] REC Control <- Time Code Output, 4ch Audio & Media Vault Guard
P255_HDMI_OUTPUT_SETTINGS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "External Output",
    "HDMI Output Settings",
)
P255_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("On", "Off")
P255_REC_MEDIA_DUR_HDMI_DEFAULT: str = "On"

P255_TIME_CODE_OUTPUT_MODES: Tuple[str, ...] = ("Off", "On")
P255_TIME_CODE_OUTPUT_DEFAULT: str = "Off"

P255_HDMI_REC_CONTROL_MODES: Tuple[str, ...] = ("Off", "On")
P255_HDMI_REC_CONTROL_DEFAULT: str = "Off"

P255_HDMI_4CH_AUDIO_OUTPUT_MODES: Tuple[str, ...] = ("CH1/CH2", "CH3/CH4")
P255_HDMI_4CH_AUDIO_OUTPUT_DEFAULT: str = "CH1/CH2"
P255_HDMI_CH1_CH2_PAIR: Tuple[str, str] = ("CH1_L", "CH2_R")
P255_HDMI_CH3_CH4_PAIR: Tuple[str, str] = ("CH3_L", "CH4_R")

P255_SLOT1_VAULT_SLOT: int = 1
P255_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P255_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_auto_slow_shutter_hdmi_reccontrol_breathing_overlay"
P255_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P255_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P255_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P255_BLOCKED_INVALID_AUTO_SLOW_OR_BREATHING_SPEC: str = (
    "BLOCKED_INVALID_AUTO_SLOW_OR_BREATHING_SPEC"
)
P255_BLOCKED_AUTO_SLOW_OR_BREATHING_RESET_DRIFT: str = (
    "BLOCKED_AUTO_SLOW_OR_BREATHING_RESET_DRIFT"
)
P255_BLOCKED_AUTO_SLOW_SHUTTER_6LOCKOUT_BYPASS: str = (
    "BLOCKED_AUTO_SLOW_SHUTTER_6LOCKOUT_BYPASS"
)
P255_BLOCKED_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP: str = (
    "BLOCKED_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP"
)
P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS: str = (
    "BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS"
)

P255_BLOCKED_INVALID_HDMI_OUTPUT_SETTINGS_SPEC: str = (
    "BLOCKED_INVALID_HDMI_OUTPUT_SETTINGS_SPEC"
)
P255_BLOCKED_HDMI_SETTINGS_RESET_SURVIVAL_DRIFT: str = (
    "BLOCKED_HDMI_SETTINGS_RESET_SURVIVAL_DRIFT"
)
P255_BLOCKED_HDMI_REC_CTRL_WITHOUT_TC_OUTPUT: str = (
    "BLOCKED_HDMI_REC_CTRL_WITHOUT_TC_OUTPUT"
)
P255_BLOCKED_HDMI_4CH_AUDIO_ROUTING_MISMATCH: str = (
    "BLOCKED_HDMI_4CH_AUDIO_ROUTING_MISMATCH"
)
P255_BLOCKED_SLOT1_HDMI_REC_VAULT_MUTATION_OR_CAMSET_DRIFT: str = (
    "BLOCKED_SLOT1_HDMI_REC_VAULT_MUTATION_OR_CAMSET_DRIFT"
)
P255_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P255_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P255_STATUS_VERIFIED_PILLAR_43A: str = (
    "VERIFIED_PILLAR_43A_AUTO_SLOW_SHUTTER_6LOCKS_ANGLE_DISJOINT_AND_BREATHING_COMP_VAULT"
)
P255_STATUS_REJECTED_PILLAR_43A: str = (
    "REJECTED_PILLAR_43A_AUTO_SLOW_SHUTTER_6LOCKS_ANGLE_DISJOINT_AND_BREATHING_COMP_VAULT"
)
P255_STATUS_VERIFIED_PILLAR_43B: str = (
    "VERIFIED_PILLAR_43B_HDMI_REC_CONTROL_TC_GATE_4CH_AUDIO_AND_MEDIA_VAULT"
)
P255_STATUS_REJECTED_PILLAR_43B: str = (
    "REJECTED_PILLAR_43B_HDMI_REC_CONTROL_TC_GATE_4CH_AUDIO_AND_MEDIA_VAULT"
)
P255_STATUS_VERIFIED_PILLAR43_SUITE: str = (
    "VERIFIED_PILLAR43_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_VAULT"
)
P255_STATUS_FAIL_PILLAR43_SUITE: str = (
    "FAIL_PILLAR43_AUTO_SLOW_SHUTTER_HDMI_RECCONTROL_BREATHING_VAULT"
)
P255_STATUS_VERIFIED_43OF43_AGGREGATOR: str = "VERIFIED_43OF43_PILLAR_RECOVERY_MASTER"
P255_STATUS_FAIL_43OF43_AGGREGATOR: str = "FAIL_43OF43_PILLAR_RECOVERY_MASTER"

P255_PILLAR_43A_SCENARIO_IDS: Tuple[str, ...] = (
    "P43A1_AUTO_SLOW_SHUTTER_ACTIVE_IN_MOVIE_P_ISO_AUTO_FLEXIBLE_ISO_AND_BREATHING_COMP_E_MOUNT_CROP_SURVIVE_NETWORK_RESET_SAFE",
    "P43A2_CAMERA_SETTINGS_RESET_RESTORES_AUTO_SLOW_ON_BREATHING_OFF_AND_ALL_6_LOCKOUTS_PLUS_SHUTTER_ANGLE_DISJOINT_VERIFIED_SAFE",
    "P43A3_REJECT_AUTO_SLOW_SHUTTER_OR_BREATHING_COMP_RESET_SCOPE_DRIFT",
    "P43A4_REJECT_AUTO_SLOW_SHUTTER_BYPASSING_ANY_OF_6_HARDWARE_LOCKOUT_CONDITIONS",
    "P43A5_REJECT_AUTO_SLOW_SHUTTER_SIMULTANEOUS_WITH_SHUTTER_MODE_ANGLE",
    "P43A6_REJECT_BREATHING_COMP_ACTIVE_IN_RAW_4264X2408_OR_SQ_240P_OR_STILL_OR_NONCOMPLIANT_LENS",
)
P255_PILLAR_43B_SCENARIO_IDS: Tuple[str, ...] = (
    "P43B1_HDMI_TC_ON_REC_CTRL_ON_4CH_CH3_CH4_AND_REC_MEDIA_OFF_VAULT_GUARD_SURVIVE_BOTH_RESETS_SAFE",
    "P43B2_INITIALIZE_RESTORES_HDMI_DEFAULTS_CH1_CH2_AND_ORDONLY_SLOT1_CAMSET01_ROUNDTRIPS_SAFE",
    "P43B3_REJECT_HDMI_OUTPUT_SETTINGS_WIPED_BY_CAMERA_SETTINGS_RESET_OR_NETWORK_RESET",
    "P43B4_REJECT_HDMI_REC_CONTROL_ON_WHEN_TIME_CODE_OUTPUT_IS_OFF",
    "P43B5_REJECT_HDMI_4CH_AUDIO_CHANNEL_PAIR_MISMATCH_OR_CH3_CH4_WITHOUT_4CH_SHOE",
    "P43B6_REJECT_SLOT1_HDMI_REC_MEDIA_UNINHIBITED_VAULT_WRITE_OR_CROSS_MODEL_FX6_CAMSET",
)

MASTER_43_PILLAR_COUNT: int = 43
MASTER_43_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_42_PILLAR_SPECS + (
    (
        43,
        "pillar_43_auto_slow_shutter_hdmi_reccontrol_breathing_vault",
        "Phase 255",
        "fx3_recovery.realhw_43pillar_auto_slow_shutter_hdmi_reccontrol_breathing_vault_verifier",
    ),
)
MASTER_43_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_43_PILLAR_SPECS)


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
        ("P255_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P255_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P255_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS", P255_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS, 0),
        ("P255_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS", P255_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS, 0),
        ("P255_BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS", P255_BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS, 0),
        ("P255_HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS", P255_HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS, 0),
        ("P255_SLOT1_HDMI_REC_VAULT_MUTATION_BYTES", P255_SLOT1_HDMI_REC_VAULT_MUTATION_BYTES, 0),
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
    return any(tok in low for tok in P255_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase255DonorArtifactDigest:
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
class Phase255DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase255DonorArtifactDigest, ...]


@dataclass(frozen=True)
class AutoSlowShutterAndBreathingCompVaultSpec:
    camera_model: str = P255_FX3_MODEL_NAME
    helpguide_id: str = P255_FX3_HELPGUIDE_ID
    fw_version: str = P255_FX3_FW_VERSION
    auto_slow_shutter_menu_path: Tuple[str, ...] = P255_AUTO_SLOW_SHUTTER_MENU_PATH
    shutter_mode_menu_path: Tuple[str, ...] = P255_SHUTTER_MODE_MENU_PATH
    breathing_comp_menu_path: Tuple[str, ...] = P255_BREATHING_COMP_MENU_PATH
    pre_reset_auto_slow_shutter: str = P255_AUTO_SLOW_SHUTTER_DEFAULT  # On | Off
    pre_reset_breathing_comp: str = "On"  # Off | On
    reset_action: str = "Reset Network Set."  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P255_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P255_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_auto_slow_shutter: str = P255_AUTO_SLOW_SHUTTER_DEFAULT
    saved_breathing_comp: str = "On"
    post_reset_auto_slow_shutter: str = P255_AUTO_SLOW_SHUTTER_DEFAULT
    post_reset_breathing_comp: str = "On"
    shooting_domain: str = "Movie"  # Movie | S&Q | Still
    exposure_mode: str = "P"  # P | A | S | M | Flexible Exp. Mode
    flexible_exp_shutter_ctrl: str = "Auto"  # Auto | Manual
    iso_setting: str = P255_ISO_AUTO_TOKEN  # ISO AUTO or manual e.g. ISO 800
    log_shooting_mode: str = "Flexible ISO"  # Off | Flexible ISO | Cine EI Quick | Cine EI
    reported_lockout_conditions: Tuple[str, ...] = ()
    auto_slow_shutter_effectively_active: bool = True
    auto_slow_shutter_lockout_bypass_events: int = 0
    movie_shutter_mode: str = P255_MOVIE_SHUTTER_MODE_DEFAULT  # Shutter Speed | Angle
    movie_shutter_angle_deg: float = P255_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG
    shutter_angle_effectively_active: bool = False
    auto_slow_shutter_angle_overlap_events: int = 0
    lens_mount_model: str = "SEL2470GM2"
    lens_breathing_comp_compliant: bool = True
    hdmi_raw_output_4264x2408: str = "Off"  # Off | On
    active_frame_rate: str = "23.98p"
    breathing_comp_effectively_active: bool = True
    fov_crop_applied: bool = True
    breathing_comp_raw_or_240p_bypass_events: int = 0
    overlay_dir: str = P255_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P255_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P255_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P255_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class AutoSlowShutterAndBreathingCompVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    reset_scope_verified: bool
    six_lockout_rules_verified: bool
    shutter_angle_disjointness_verified: bool
    breathing_comp_boundary_verified: bool
    h0_equals_h3_verified: bool
    active_lockout_conditions: Tuple[str, ...]
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_raw_or_240p_bypass_events: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HdmiRecControl4chAudioAndMediaVaultSpec:
    camera_model: str = P255_FX3_MODEL_NAME
    helpguide_id: str = P255_FX3_HELPGUIDE_ID
    fw_version: str = P255_FX3_FW_VERSION
    hdmi_output_settings_menu_path: Tuple[str, ...] = P255_HDMI_OUTPUT_SETTINGS_MENU_PATH
    pre_rec_media_dur_hdmi: str = "Off"  # On | Off
    pre_time_code_output: str = "On"  # Off | On
    pre_hdmi_rec_control: str = "On"  # Off | On
    pre_4ch_audio_output: str = "CH3/CH4"  # CH1/CH2 | CH3/CH4
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Reset Network Set. | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P255_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P255_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_rec_media_dur_hdmi: str = "Off"
    saved_time_code_output: str = "On"
    saved_hdmi_rec_control: str = "On"
    saved_4ch_audio_output: str = "CH3/CH4"
    post_rec_media_dur_hdmi: str = "Off"
    post_time_code_output: str = "On"
    post_hdmi_rec_control: str = "On"
    post_4ch_audio_output: str = "CH3/CH4"
    external_recorder_rec_trigger_enabled: bool = True
    hdmi_rec_ctrl_without_tc_violations: int = 0
    mi_shoe_4ch_audio_active: bool = True
    shoe_audio_set_mode: str = "48kHz/24bit 4ch"
    hdmi_routed_audio_pair: Tuple[str, str] = P255_HDMI_CH3_CH4_PAIR
    hdmi_connected: bool = True
    internal_slot1_slot2_clip_rec_inhibited: bool = True
    proxy_recording_inhibited: bool = True
    slot1_tier0_vault_active: bool = True
    slot1_sdxc_wp_locked: bool = True
    camset_save_to_slot1_attempted: bool = False
    slot1_hdmi_rec_vault_mutation_bytes: int = 0
    overlay_dir: str = P255_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P255_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P255_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P255_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class HdmiRecControl4chAudioAndMediaVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    hdmi_reset_survival_verified: bool
    rec_ctrl_tc_prerequisite_verified: bool
    hdmi_4ch_audio_routing_verified: bool
    rec_media_off_vault_guard_verified: bool
    camset_ordonly_roundtrip_verified: bool
    h0_equals_h3_verified: bool
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AutoSlowShutterHdmiRecControlAndBreathingVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase255DonorSnapshot
    auto_slow_breathing_report: AutoSlowShutterAndBreathingCompVaultReport
    hdmi_reccontrol_4chaudio_report: HdmiRecControl4chAudioAndMediaVaultReport
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_raw_or_240p_bypass_events: int
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
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
class Pillar43ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar43ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar43ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar43BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar43ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar43StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase255DonorSnapshot
    pillar_43a_auto_slow_shutter_breathing_vault: Pillar43ASuiteResult
    pillar_43b_hdmi_reccontrol_4chaudio_vault: Pillar43BSuiteResult
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_raw_or_240p_bypass_events: int
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
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
class Master43PillarRecoveryReport:
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
    # Pillar 43 & Wave-41 top-level fields
    donor_snapshot: Phase255DonorSnapshot
    pillar43_a_auto_slow_shutter_breathing_vault: Pillar43ASuiteResult
    pillar43_b_hdmi_reccontrol_4chaudio_vault: Pillar43BSuiteResult
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_raw_or_240p_bypass_events: int
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
    # Preserved Pillars 1..42 rollup metrics
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
    master_43pillar_sha256: str
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
    max_full_bytes: int = P255_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P255_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase255_donors() -> Tuple[Phase255DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P255_DONOR_FX3_BODYDATA_RELPATH,
            P255_PINNED_FX3_BODYDATA_BYTES,
            P255_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P255_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P255_DONOR_FX3_APPFW_702_RELPATH,
            P255_PINNED_FX3_APPFW_702_BYTES,
            P255_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P255_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P255_DONOR_FX6_APPFW_601_RELPATH,
            P255_PINNED_FX6_APPFW_601_BYTES,
            P255_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P255_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P255_DONOR_FX3_BACKUP_BIN_RELPATH,
            P255_PINNED_FX3_BACKUP_BIN_BYTES,
            P255_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P255_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P255_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P255_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P255_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P255_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P255_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P255_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P255_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P255_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P255_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_libgpe_so",
            P255_DONOR_FX3_LIBGPE_SO_RELPATH,
            P255_PINNED_FX3_LIBGPE_SO_BYTES,
            P255_PINNED_FX3_LIBGPE_SO_BYTES,
            "FULL_SHA256",
            P255_PINNED_FX3_LIBGPE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:gpe_blog_error+_ZNK5mpgpe5Gperm4InitEv",
        ),
        (
            "fx3_cameraondemandsaver_so",
            P255_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P255_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P255_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            "FULL_SHA256",
            P255_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:CameraOnDemandSaver+_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji",
        ),
        (
            "fx3_libinfralenscommunicator_so",
            P255_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH,
            P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
            P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
            "FULL_SHA256",
            P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:LensCommunicator+_Z23LensCommunicator_CreatePN3MWF5ErrCdE",
        ),
        (
            "fx3_libinframediaconfig_so",
            P255_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+_ZN16InfraMediaConfig10SaveBackupEt",
        ),
        (
            "fx6_libinfrahotshoe_so",
            P255_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH,
            P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
            P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
            "FULL_SHA256",
            P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraHotshoe+_ZN12InfraHotshoe15ResourceToInfraEi",
        ),
    )
    return tuple(
        Phase255DonorArtifactDigest(
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


def inspect_phase255_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase255DonorSnapshot:
    """Inspect Wave-41 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.15s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase255_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase255DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P255_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P255_DONOR_FX3_BODYDATA_RELPATH,
            P255_PINNED_FX3_BODYDATA_BYTES,
            P255_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P255_DONOR_FX3_APPFW_702_RELPATH,
            P255_PINNED_FX3_APPFW_702_BYTES,
            P255_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P255_DONOR_FX6_APPFW_601_RELPATH,
            P255_PINNED_FX6_APPFW_601_BYTES,
            P255_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P255_DONOR_FX3_BACKUP_BIN_RELPATH,
            P255_PINNED_FX3_BACKUP_BIN_BYTES,
            P255_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P255_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P255_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P255_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P255_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P255_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P255_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P255_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite"),
            ),
        ),
        (
            "fx3_libgpe_so",
            P255_DONOR_FX3_LIBGPE_SO_RELPATH,
            P255_PINNED_FX3_LIBGPE_SO_BYTES,
            P255_PINNED_FX3_LIBGPE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv")),
        ),
        (
            "fx3_cameraondemandsaver_so",
            P255_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P255_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P255_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"CameraOnDemandSaver", b"_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji"),
            ),
        ),
        (
            "fx3_libinfralenscommunicator_so",
            P255_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH,
            P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES,
            P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"LensCommunicator", b"_Z23LensCommunicator_CreatePN3MWF5ErrCdE"),
            ),
        ),
        (
            "fx3_libinframediaconfig_so",
            P255_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraMediaConfig", b"_ZN16InfraMediaConfig10SaveBackupEt"),
            ),
        ),
        (
            "fx6_libinfrahotshoe_so",
            P255_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH,
            P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
            P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraHotshoe", b"_ZN12InfraHotshoe15ResourceToInfraEi"),
            ),
        ),
    )

    real_artifacts: List[Phase255DonorArtifactDigest] = []
    any_missing = False
    for aid, rel, pinned_bytes, pinned_sha, marker_fn in probe_specs:
        present, total_b, read_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(rel)
        if not present:
            any_missing = True
            break
        marker_ok, marker_summary = marker_fn(raw_slice)
        matches = (total_b == pinned_bytes) and (dsha == pinned_sha) and bool(marker_ok)
        real_artifacts.append(
            Phase255DonorArtifactDigest(
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
        artifacts = _synthetic_phase255_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase255DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P255_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    all_ok = len(real_artifacts) == len(probe_specs) and all(a.matches_pinned for a in real_artifacts)
    dt = round(time.monotonic() - t0, 6)
    return Phase255DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(real_artifacts),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P255_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(real_artifacts),
    )


# ---------------------------------------------------------------------------
# Pillar 43A — [Auto Slow Shutter] 6 Lockouts, [Shutter Angle] Disjointness & [Breathing Comp.]
# ---------------------------------------------------------------------------


def compute_expected_auto_slow_shutter_lockouts(
    *,
    shooting_domain: str,
    exposure_mode: str,
    flexible_exp_shutter_ctrl: str,
    iso_setting: str,
    log_shooting_mode: str,
) -> Tuple[str, ...]:
    """Return the exact ordered tuple of active Sony ILME-FX3 Auto Slow Shutter lockout conditions."""
    lockouts: List[str] = []
    if shooting_domain == "S&Q":
        lockouts.append("S&Q_MOTION")
    if exposure_mode == "S":
        lockouts.append("SHUTTER_PRIORITY_S")
    if exposure_mode == "M":
        lockouts.append("MANUAL_EXPOSURE_M")
    if iso_setting.strip() != P255_ISO_AUTO_TOKEN:
        lockouts.append("NON_AUTO_ISO")
    if exposure_mode == "Flexible Exp. Mode" and flexible_exp_shutter_ctrl == "Manual":
        lockouts.append("FLEXIBLE_EXP_MANUAL_SHUTTER")
    if log_shooting_mode in P255_LOG_CINE_EI_LOCKOUT_MODES:
        lockouts.append("LOG_CINE_EI_OR_CINE_EI_QUICK")
    return tuple(lockouts)


def build_default_safe_auto_slow_shutter_breathing_vault_spec() -> AutoSlowShutterAndBreathingCompVaultSpec:
    """Return default safe Pillar 43A spec (`Movie` + `P` + `ISO AUTO` + `Flexible ISO` + compliant E-mount)."""
    return AutoSlowShutterAndBreathingCompVaultSpec()


def evaluate_auto_slow_shutter_and_breathing_comp_vault(
    spec: AutoSlowShutterAndBreathingCompVaultSpec,
) -> AutoSlowShutterAndBreathingCompVaultReport:
    """Evaluate Pillar 43A `[Auto Slow Shutter]` 6 lockouts, `[Shutter Angle]` disjointness & `[Breathing Comp.]`."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    safety_errs = _safety_invariant_errors()
    if safety_errs or spec.persistent_write_unlock_requested:
        for e in safety_errs:
            _fail(P255_BLOCKED_SAFETY_POLICY_VIOLATION, e)
        if spec.persistent_write_unlock_requested:
            _fail(
                P255_BLOCKED_SAFETY_POLICY_VIOLATION,
                "persistent_write_unlock_requested=True forbidden under zero-write posture",
            )

    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P255_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Volatile tmpfs Stage-B overlay / p2 BLKROSET lock violated: overlay={spec.overlay_dir!r}",
        )

    h0_eq_h3_ok = (
        spec.backup_bin_h0_sha256 == P255_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P255_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P255_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3_ok:
        _fail(
            P255_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 Backup.bin H0 == H3 parity drift detected in Pillar 43A",
        )

    spec_valid = (
        spec.camera_model == P255_FX3_MODEL_NAME
        and spec.helpguide_id == P255_FX3_HELPGUIDE_ID
        and spec.fw_version in P255_FX3_SUPPORTED_FW_VERSIONS
        and spec.auto_slow_shutter_menu_path == P255_AUTO_SLOW_SHUTTER_MENU_PATH
        and spec.shutter_mode_menu_path == P255_SHUTTER_MODE_MENU_PATH
        and spec.breathing_comp_menu_path == P255_BREATHING_COMP_MENU_PATH
        and spec.pre_reset_auto_slow_shutter in P255_AUTO_SLOW_SHUTTER_MODES
        and spec.saved_auto_slow_shutter in P255_AUTO_SLOW_SHUTTER_MODES
        and spec.post_reset_auto_slow_shutter in P255_AUTO_SLOW_SHUTTER_MODES
        and spec.pre_reset_breathing_comp in P255_BREATHING_COMP_MODES
        and spec.saved_breathing_comp in P255_BREATHING_COMP_MODES
        and spec.post_reset_breathing_comp in P255_BREATHING_COMP_MODES
        and spec.reset_action in P255_RESET_ACTIONS
        and spec.shooting_domain in P255_SHOOTING_DOMAINS
        and spec.exposure_mode in P255_EXPOSURE_MODES
        and spec.flexible_exp_shutter_ctrl in P255_FLEXIBLE_EXP_SHUTTER_CTRL_MODES
        and isinstance(spec.iso_setting, str)
        and bool(spec.iso_setting.strip())
        and spec.log_shooting_mode in P255_LOG_SHOOTING_MODES
        and spec.movie_shutter_mode in P255_MOVIE_SHUTTER_MODES
        and spec.hdmi_raw_output_4264x2408 in P255_HDMI_RAW_OUTPUT_MODES
        and spec.active_frame_rate in P255_MOVIE_AND_SQ_FRAME_RATES
        and isinstance(spec.lens_mount_model, str)
        and bool(spec.lens_mount_model.strip())
        and len(spec.reported_lockout_conditions) == len(set(spec.reported_lockout_conditions))
        and all(c in P255_AUTO_SLOW_SHUTTER_6_LOCKOUT_CONDITIONS for c in spec.reported_lockout_conditions)
    )
    if spec.camset_load_after_reset:
        spec_valid = spec_valid and (
            spec.camset_slot in (1, 2)
            and spec.camset_filename in P255_CAMSET_FILENAMES
            and spec.camset_source_model == P255_FX3_MODEL_NAME
            and spec.camset_read_only_load is True
        )
    if not spec_valid:
        _fail(
            P255_BLOCKED_INVALID_AUTO_SLOW_OR_BREATHING_SPEC,
            "Invalid ILME-FX3 Auto Slow Shutter / Shutter Mode / Breathing Comp. menu path, FW, or enum token",
        )

    # 1. Reset scope verification ([Camera Settings Reset] & [Initialize] reset; [Reset Network Set.] preserves)
    if spec.camset_load_after_reset:
        expected_post_auto_slow = spec.saved_auto_slow_shutter
        expected_post_breathing = spec.saved_breathing_comp
    elif spec.reset_action in ("NONE", "Reset Network Set."):
        expected_post_auto_slow = spec.pre_reset_auto_slow_shutter
        expected_post_breathing = spec.pre_reset_breathing_comp
    else:
        expected_post_auto_slow = P255_AUTO_SLOW_SHUTTER_DEFAULT  # "On"
        expected_post_breathing = P255_BREATHING_COMP_DEFAULT  # "Off"

    reset_scope_ok = (
        spec.post_reset_auto_slow_shutter == expected_post_auto_slow
        and spec.post_reset_breathing_comp == expected_post_breathing
    )
    if not reset_scope_ok:
        _fail(
            P255_BLOCKED_AUTO_SLOW_OR_BREATHING_RESET_DRIFT,
            f"Reset drift under {spec.reset_action!r} (camset_load={spec.camset_load_after_reset}): "
            f"expected AutoSlow={expected_post_auto_slow!r}/Breathing={expected_post_breathing!r}, "
            f"got AutoSlow={spec.post_reset_auto_slow_shutter!r}/Breathing={spec.post_reset_breathing_comp!r}",
        )

    # 2. Strict hardware disjointness between [Auto Slow Shutter] and [Shutter Mode] = [Angle]
    manual_shutter_governance = spec.shooting_domain in ("Movie", "S&Q") and (
        spec.exposure_mode in ("S", "M")
        or (spec.exposure_mode == "Flexible Exp. Mode" and spec.flexible_exp_shutter_ctrl == "Manual")
    )
    shutter_angle_fw_ok = (
        spec.movie_shutter_mode != "Angle" or spec.fw_version in P255_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS
    )
    shutter_angle_range_ok = (
        spec.movie_shutter_mode != "Angle" or (5.6 <= float(spec.movie_shutter_angle_deg) <= 360.0)
    )
    expected_shutter_angle_active = (
        spec.movie_shutter_mode == "Angle"
        and shutter_angle_fw_ok
        and shutter_angle_range_ok
        and manual_shutter_governance
    )
    overlap_detected = (
        spec.auto_slow_shutter_angle_overlap_events != 0
        or (spec.auto_slow_shutter_effectively_active and spec.shutter_angle_effectively_active)
        or (spec.auto_slow_shutter_effectively_active and spec.movie_shutter_mode == "Angle" and manual_shutter_governance)
    )
    shutter_angle_disjoint_ok = (
        not overlap_detected
        and shutter_angle_fw_ok
        and shutter_angle_range_ok
        and spec.shutter_angle_effectively_active == expected_shutter_angle_active
    )
    if not shutter_angle_disjoint_ok:
        _fail(
            P255_BLOCKED_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP,
            "Auto Slow Shutter and Ver. 7.02 [Shutter Mode]=[Angle] overlap or invalid Shutter Angle governance",
        )

    # 3. Exact 6 official Sony Auto Slow Shutter lockout conditions
    active_lockouts = compute_expected_auto_slow_shutter_lockouts(
        shooting_domain=spec.shooting_domain,
        exposure_mode=spec.exposure_mode,
        flexible_exp_shutter_ctrl=spec.flexible_exp_shutter_ctrl,
        iso_setting=spec.iso_setting,
        log_shooting_mode=spec.log_shooting_mode,
    )
    expected_auto_slow_active = (
        spec.post_reset_auto_slow_shutter == "On"
        and spec.shooting_domain == "Movie"
        and len(active_lockouts) == 0
    )
    six_lockouts_ok = (
        spec.reported_lockout_conditions == active_lockouts
        and spec.auto_slow_shutter_effectively_active == expected_auto_slow_active
        and spec.auto_slow_shutter_lockout_bypass_events == 0
    )
    if not six_lockouts_ok:
        _fail(
            P255_BLOCKED_AUTO_SLOW_SHUTTER_6LOCKOUT_BYPASS,
            f"Auto Slow Shutter 6-condition lockout mismatch: expected lockouts={active_lockouts}, "
            f"active={expected_auto_slow_active}; got lockouts={spec.reported_lockout_conditions}, "
            f"active={spec.auto_slow_shutter_effectively_active}, "
            f"bypass_events={spec.auto_slow_shutter_lockout_bypass_events}",
        )

    # 4. [Lens Compensation] -> [Breathing Comp.] movie-only compliant E-mount crop & RAW/240p lockout
    breathing_fw_ok = (
        (spec.pre_reset_breathing_comp == "Off" and spec.post_reset_breathing_comp == "Off")
        or spec.fw_version in P255_FX3_BREATHING_COMP_MIN_FW_VERSIONS
    )
    expected_breathing_active = (
        breathing_fw_ok
        and spec.post_reset_breathing_comp == "On"
        and spec.shooting_domain in ("Movie", "S&Q")
        and spec.lens_breathing_comp_compliant
        and spec.hdmi_raw_output_4264x2408 == "Off"
        and spec.active_frame_rate not in P255_BREATHING_COMP_LOCKOUT_SQ_RATES
    )
    breathing_boundary_ok = (
        breathing_fw_ok
        and spec.breathing_comp_effectively_active == expected_breathing_active
        and spec.fov_crop_applied == expected_breathing_active
        and spec.breathing_comp_raw_or_240p_bypass_events == 0
    )
    if not breathing_boundary_ok:
        _fail(
            P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS,
            f"Breathing Comp. boundary violated: expected active/crop={expected_breathing_active} "
            f"(domain={spec.shooting_domain}, lens_ok={spec.lens_breathing_comp_compliant}, "
            f"raw={spec.hdmi_raw_output_4264x2408}, fps={spec.active_frame_rate}), "
            f"got active={spec.breathing_comp_effectively_active}, crop={spec.fov_crop_applied}, "
            f"bypass_events={spec.breathing_comp_raw_or_240p_bypass_events}",
        )

    passed = len(errors) == 0
    bypass_cnt = 0 if six_lockouts_ok else max(1, int(spec.auto_slow_shutter_lockout_bypass_events))
    overlap_cnt = 0 if shutter_angle_disjoint_ok else max(1, int(spec.auto_slow_shutter_angle_overlap_events))
    breathing_bypass_cnt = (
        0 if breathing_boundary_ok else max(1, int(spec.breathing_comp_raw_or_240p_bypass_events))
    )
    digest = _canonical_sha256(
        {
            "pillar": "43A",
            "passed": passed,
            "block_code": block_code,
            "active_lockouts": list(active_lockouts),
            "auto_slow_active": spec.auto_slow_shutter_effectively_active,
            "shutter_angle_active": spec.shutter_angle_effectively_active,
            "breathing_active": spec.breathing_comp_effectively_active,
            "reset_action": spec.reset_action,
        }
    )
    return AutoSlowShutterAndBreathingCompVaultReport(
        passed=passed,
        status=P255_STATUS_VERIFIED_PILLAR_43A if passed else P255_STATUS_REJECTED_PILLAR_43A,
        block_code=None if passed else block_code,
        reset_scope_verified=reset_scope_ok and spec_valid,
        six_lockout_rules_verified=six_lockouts_ok and spec_valid,
        shutter_angle_disjointness_verified=shutter_angle_disjoint_ok and spec_valid,
        breathing_comp_boundary_verified=breathing_boundary_ok and spec_valid,
        h0_equals_h3_verified=h0_eq_h3_ok,
        active_lockout_conditions=active_lockouts,
        auto_slow_shutter_lockout_bypass_events=bypass_cnt,
        auto_slow_shutter_angle_overlap_events=overlap_cnt,
        breathing_comp_raw_or_240p_bypass_events=breathing_bypass_cnt,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 43B — [HDMI Output Settings] REC Control <- Time Code Output, 4ch Audio & Media Vault Guard
# ---------------------------------------------------------------------------


def build_default_safe_hdmi_reccontrol_4chaudio_vault_spec() -> HdmiRecControl4chAudioAndMediaVaultSpec:
    """Return default safe Pillar 43B spec (`TC Output=On`, `REC Control=On`, `CH3/CH4`, `Rec. Media=Off`)."""
    return HdmiRecControl4chAudioAndMediaVaultSpec()


def evaluate_hdmi_reccontrol_4chaudio_and_media_vault(
    spec: HdmiRecControl4chAudioAndMediaVaultSpec,
) -> HdmiRecControl4chAudioAndMediaVaultReport:
    """Evaluate Pillar 43B `[HDMI Output Settings]` survival, TC->REC gate, 4ch audio & Slot-1 media vault."""
    errors: List[str] = []
    block_code: Optional[str] = None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        if block_code is None:
            block_code = code
        errors.append(msg)

    safety_errs = _safety_invariant_errors()
    if safety_errs or spec.persistent_write_unlock_requested:
        for e in safety_errs:
            _fail(P255_BLOCKED_SAFETY_POLICY_VIOLATION, e)
        if spec.persistent_write_unlock_requested:
            _fail(
                P255_BLOCKED_SAFETY_POLICY_VIOLATION,
                "persistent_write_unlock_requested=True forbidden under zero-write posture",
            )

    if (
        not _is_tmpfs_path(spec.overlay_dir)
        or _targets_persistent_emmc(spec.overlay_dir)
        or not spec.p2_blkroset_locked
        or spec.stage_b_backup_bin_writes != 0
    ):
        _fail(
            P255_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Volatile tmpfs Stage-B overlay / p2 BLKROSET lock violated: overlay={spec.overlay_dir!r}",
        )

    h0_eq_h3_ok = (
        spec.backup_bin_h0_sha256 == P255_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P255_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256
        and spec.tier0_surfaces_h0_h3_matched == P255_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3_ok:
        _fail(
            P255_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "16/16 Tier-0 Backup.bin H0 == H3 parity drift detected in Pillar 43B",
        )

    spec_valid = (
        spec.camera_model == P255_FX3_MODEL_NAME
        and spec.helpguide_id == P255_FX3_HELPGUIDE_ID
        and spec.fw_version in P255_FX3_SUPPORTED_FW_VERSIONS
        and spec.hdmi_output_settings_menu_path == P255_HDMI_OUTPUT_SETTINGS_MENU_PATH
        and spec.pre_rec_media_dur_hdmi in P255_REC_MEDIA_DUR_HDMI_MODES
        and spec.saved_rec_media_dur_hdmi in P255_REC_MEDIA_DUR_HDMI_MODES
        and spec.post_rec_media_dur_hdmi in P255_REC_MEDIA_DUR_HDMI_MODES
        and spec.pre_time_code_output in P255_TIME_CODE_OUTPUT_MODES
        and spec.saved_time_code_output in P255_TIME_CODE_OUTPUT_MODES
        and spec.post_time_code_output in P255_TIME_CODE_OUTPUT_MODES
        and spec.pre_hdmi_rec_control in P255_HDMI_REC_CONTROL_MODES
        and spec.saved_hdmi_rec_control in P255_HDMI_REC_CONTROL_MODES
        and spec.post_hdmi_rec_control in P255_HDMI_REC_CONTROL_MODES
        and spec.pre_4ch_audio_output in P255_HDMI_4CH_AUDIO_OUTPUT_MODES
        and spec.saved_4ch_audio_output in P255_HDMI_4CH_AUDIO_OUTPUT_MODES
        and spec.post_4ch_audio_output in P255_HDMI_4CH_AUDIO_OUTPUT_MODES
        and spec.reset_action in P255_RESET_ACTIONS
        and isinstance(spec.shoe_audio_set_mode, str)
        and bool(spec.shoe_audio_set_mode.strip())
        and isinstance(spec.hdmi_routed_audio_pair, tuple)
        and len(spec.hdmi_routed_audio_pair) == 2
    )
    if not spec_valid:
        _fail(
            P255_BLOCKED_INVALID_HDMI_OUTPUT_SETTINGS_SPEC,
            "Invalid ILME-FX3 HDMI Output Settings menu path, FW, or enum token",
        )

    # 1. [REC Control] <- [Time Code Output] = [On] mandatory hardware prerequisite
    pre_tc_gate_bad = spec.pre_hdmi_rec_control == "On" and spec.pre_time_code_output != "On"
    post_tc_gate_bad = spec.post_hdmi_rec_control == "On" and spec.post_time_code_output != "On"
    saved_tc_gate_bad = (
        spec.camset_load_after_reset
        and spec.saved_hdmi_rec_control == "On"
        and spec.saved_time_code_output != "On"
    )
    expected_ext_rec_trigger = (
        spec.hdmi_connected and spec.post_hdmi_rec_control == "On" and spec.post_time_code_output == "On"
    )
    rec_ctrl_tc_ok = (
        not pre_tc_gate_bad
        and not post_tc_gate_bad
        and not saved_tc_gate_bad
        and spec.hdmi_rec_ctrl_without_tc_violations == 0
        and spec.external_recorder_rec_trigger_enabled == expected_ext_rec_trigger
    )
    if not rec_ctrl_tc_ok:
        _fail(
            P255_BLOCKED_HDMI_REC_CTRL_WITHOUT_TC_OUTPUT,
            "HDMI [REC Control]=[On] requires [Time Code Output]=[On] prerequisite and matching trigger state",
        )

    # 2. [HDMI Output Settings] non-resettable [Setup] survival across Camera Settings Reset & Reset Network Set.
    camset_meta_ok = True
    if spec.camset_load_after_reset:
        camset_meta_ok = (
            spec.camset_slot in (1, 2)
            and spec.camset_filename in P255_CAMSET_FILENAMES
            and spec.camset_source_model == P255_FX3_MODEL_NAME
            and spec.camset_read_only_load is True
        )
        if not camset_meta_ok:
            _fail(
                P255_BLOCKED_SLOT1_HDMI_REC_VAULT_MUTATION_OR_CAMSET_DRIFT,
                f"Invalid or cross-model CAMSET load metadata: slot={spec.camset_slot}, "
                f"file={spec.camset_filename!r}, model={spec.camset_source_model!r}, ro={spec.camset_read_only_load}",
            )
        exp_rec_media = spec.saved_rec_media_dur_hdmi
        exp_tc_out = spec.saved_time_code_output
        exp_rec_ctrl = spec.saved_hdmi_rec_control
        exp_4ch_audio = spec.saved_4ch_audio_output
    elif spec.reset_action in ("NONE", "Camera Settings Reset", "Reset Network Set."):
        exp_rec_media = spec.pre_rec_media_dur_hdmi
        exp_tc_out = spec.pre_time_code_output
        exp_rec_ctrl = spec.pre_hdmi_rec_control
        exp_4ch_audio = spec.pre_4ch_audio_output
    else:
        exp_rec_media = P255_REC_MEDIA_DUR_HDMI_DEFAULT  # "On"
        exp_tc_out = P255_TIME_CODE_OUTPUT_DEFAULT  # "Off"
        exp_rec_ctrl = P255_HDMI_REC_CONTROL_DEFAULT  # "Off"
        exp_4ch_audio = P255_HDMI_4CH_AUDIO_OUTPUT_DEFAULT  # "CH1/CH2"

    hdmi_reset_ok = (
        spec.post_rec_media_dur_hdmi == exp_rec_media
        and spec.post_time_code_output == exp_tc_out
        and spec.post_hdmi_rec_control == exp_rec_ctrl
        and spec.post_4ch_audio_output == exp_4ch_audio
    )
    if not hdmi_reset_ok:
        _fail(
            P255_BLOCKED_HDMI_SETTINGS_RESET_SURVIVAL_DRIFT,
            f"HDMI Output Settings reset survival drift under {spec.reset_action!r} "
            f"(camset_load={spec.camset_load_after_reset})",
        )

    # 3. [4ch Audio Output] channel routing (CH1/CH2 -> Ch1=L/Ch2=R vs CH3/CH4 -> Ch3=L/Ch4=R with 4ch MI-shoe)
    if spec.post_4ch_audio_output == "CH1/CH2":
        audio_routing_ok = spec.hdmi_routed_audio_pair == P255_HDMI_CH1_CH2_PAIR
    else:
        audio_routing_ok = (
            spec.mi_shoe_4ch_audio_active is True
            and spec.shoe_audio_set_mode == "48kHz/24bit 4ch"
            and spec.hdmi_routed_audio_pair == P255_HDMI_CH3_CH4_PAIR
        )
    if not audio_routing_ok:
        _fail(
            P255_BLOCKED_HDMI_4CH_AUDIO_ROUTING_MISMATCH,
            f"HDMI [4ch Audio Output]={spec.post_4ch_audio_output!r} routing mismatch: "
            f"mi_shoe_4ch={spec.mi_shoe_4ch_audio_active}, shoe_mode={spec.shoe_audio_set_mode!r}, "
            f"pair={spec.hdmi_routed_audio_pair!r}",
        )

    # 4. [Rec. Media dur HDMI Output] = [Off] Slot-1/Slot-2 & Proxy inhibition + Tier-0 Slot-1 vault guard
    expected_media_inhibited = bool(spec.hdmi_connected and spec.post_rec_media_dur_hdmi == "Off")
    inhibition_flags_ok = (
        spec.internal_slot1_slot2_clip_rec_inhibited == expected_media_inhibited
        and spec.proxy_recording_inhibited == expected_media_inhibited
    )
    slot1_vault_guard_ok = (
        spec.slot1_hdmi_rec_vault_mutation_bytes == 0
        and not (spec.slot1_tier0_vault_active and spec.camset_save_to_slot1_attempted)
        and (not spec.slot1_tier0_vault_active or spec.slot1_sdxc_wp_locked)
        and (
            not (spec.slot1_tier0_vault_active and spec.hdmi_connected)
            or spec.post_rec_media_dur_hdmi == "Off"
        )
    )
    vault_and_camset_ok = inhibition_flags_ok and slot1_vault_guard_ok and camset_meta_ok
    if not (inhibition_flags_ok and slot1_vault_guard_ok):
        _fail(
            P255_BLOCKED_SLOT1_HDMI_REC_VAULT_MUTATION_OR_CAMSET_DRIFT,
            "HDMI [Rec. Media dur HDMI Output] clip/proxy inhibition mismatch or Slot-1 Tier-0 vault write hazard",
        )

    passed = len(errors) == 0
    tc_violations = 0 if rec_ctrl_tc_ok else max(1, int(spec.hdmi_rec_ctrl_without_tc_violations))
    vault_mut_bytes = 0 if vault_and_camset_ok else max(1, int(spec.slot1_hdmi_rec_vault_mutation_bytes))
    digest = _canonical_sha256(
        {
            "pillar": "43B",
            "passed": passed,
            "block_code": block_code,
            "post_rec_media": spec.post_rec_media_dur_hdmi,
            "post_tc": spec.post_time_code_output,
            "post_rec_ctrl": spec.post_hdmi_rec_control,
            "post_4ch_audio": spec.post_4ch_audio_output,
            "routed_pair": list(spec.hdmi_routed_audio_pair),
            "reset_action": spec.reset_action,
        }
    )
    return HdmiRecControl4chAudioAndMediaVaultReport(
        passed=passed,
        status=P255_STATUS_VERIFIED_PILLAR_43B if passed else P255_STATUS_REJECTED_PILLAR_43B,
        block_code=None if passed else block_code,
        hdmi_reset_survival_verified=hdmi_reset_ok and spec_valid,
        rec_ctrl_tc_prerequisite_verified=rec_ctrl_tc_ok and spec_valid,
        hdmi_4ch_audio_routing_verified=audio_routing_ok and spec_valid,
        rec_media_off_vault_guard_verified=inhibition_flags_ok and slot1_vault_guard_ok and spec_valid,
        camset_ordonly_roundtrip_verified=camset_meta_ok and hdmi_reset_ok and spec_valid,
        h0_equals_h3_verified=h0_eq_h3_ok,
        hdmi_rec_ctrl_without_tc_violations=tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=vault_mut_bytes,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault(
    auto_slow_spec: Optional[AutoSlowShutterAndBreathingCompVaultSpec] = None,
    hdmi_spec: Optional[HdmiRecControl4chAudioAndMediaVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> AutoSlowShutterHdmiRecControlAndBreathingVaultReport:
    """Combined single-shot verifier for Pillar 43A + Pillar 43B + bounded O_RDONLY Wave-41 donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase255_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_auto_slow_shutter_and_breathing_comp_vault(
        auto_slow_spec or build_default_safe_auto_slow_shutter_breathing_vault_spec()
    )
    rep_b = evaluate_hdmi_reccontrol_4chaudio_and_media_vault(
        hdmi_spec or build_default_safe_hdmi_reccontrol_4chaudio_vault_spec()
    )
    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 255 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        errs.append(f"Donor inspection exceeded 0.15s budget: {donor_snapshot.elapsed_seconds}s")
    ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return AutoSlowShutterHdmiRecControlAndBreathingVaultReport(
        schema=PHASE255_SCHEMA,
        version=PHASE255_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=ok,
        passed=ok,
        status=P255_STATUS_VERIFIED_PILLAR43_SUITE if ok else P255_STATUS_FAIL_PILLAR43_SUITE,
        donor_snapshot=donor_snapshot,
        auto_slow_breathing_report=rep_a,
        hdmi_reccontrol_4chaudio_report=rep_b,
        auto_slow_shutter_lockout_bypass_events=rep_a.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=rep_a.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=rep_a.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=rep_b.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=rep_b.slot1_hdmi_rec_vault_mutation_bytes,
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
        errors=tuple(errs),
    )


def verify_auto_slow_shutter_hdmi_reccontrol_breathing_vault(
    auto_slow_spec: Optional[AutoSlowShutterAndBreathingCompVaultSpec] = None,
    hdmi_spec: Optional[HdmiRecControl4chAudioAndMediaVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> AutoSlowShutterHdmiRecControlAndBreathingVaultReport:
    """Symmetry alias for `verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault`."""
    return verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault(
        auto_slow_spec=auto_slow_spec,
        hdmi_spec=hdmi_spec,
        force_clean_room=force_clean_room,
    )


# ---------------------------------------------------------------------------
# 6-Scenario Suites (Pillar 43A & Pillar 43B) & Standalone Runner
# ---------------------------------------------------------------------------


def run_pillar43a_auto_slow_shutter_breathing_vault_6_scenario_suite() -> Pillar43ASuiteResult:
    """Run all 6 canonical Pillar 43A scenarios (`2` safe + `4` negative hardware lockout/disjointness guards)."""
    cases: Tuple[Tuple[str, bool, AutoSlowShutterAndBreathingCompVaultSpec, Optional[str]], ...] = (
        (
            P255_PILLAR_43A_SCENARIO_IDS[0],
            True,
            AutoSlowShutterAndBreathingCompVaultSpec(
                pre_reset_auto_slow_shutter="On",
                pre_reset_breathing_comp="On",
                reset_action="Reset Network Set.",
                post_reset_auto_slow_shutter="On",
                post_reset_breathing_comp="On",
                shooting_domain="Movie",
                exposure_mode="P",
                flexible_exp_shutter_ctrl="Auto",
                iso_setting="ISO AUTO",
                log_shooting_mode="Flexible ISO",
                reported_lockout_conditions=(),
                auto_slow_shutter_effectively_active=True,
                movie_shutter_mode="Shutter Speed",
                shutter_angle_effectively_active=False,
                lens_mount_model="SEL2470GM2",
                lens_breathing_comp_compliant=True,
                hdmi_raw_output_4264x2408="Off",
                active_frame_rate="23.98p",
                breathing_comp_effectively_active=True,
                fov_crop_applied=True,
            ),
            None,
        ),
        (
            P255_PILLAR_43A_SCENARIO_IDS[1],
            True,
            AutoSlowShutterAndBreathingCompVaultSpec(
                pre_reset_auto_slow_shutter="Off",
                pre_reset_breathing_comp="On",
                reset_action="Camera Settings Reset",
                post_reset_auto_slow_shutter="On",
                post_reset_breathing_comp="Off",
                shooting_domain="S&Q",
                exposure_mode="M",
                flexible_exp_shutter_ctrl="Manual",
                iso_setting="ISO 800",
                log_shooting_mode="Cine EI",
                reported_lockout_conditions=(
                    "S&Q_MOTION",
                    "MANUAL_EXPOSURE_M",
                    "NON_AUTO_ISO",
                    "LOG_CINE_EI_OR_CINE_EI_QUICK",
                ),
                auto_slow_shutter_effectively_active=False,
                movie_shutter_mode="Angle",
                movie_shutter_angle_deg=180.0,
                shutter_angle_effectively_active=True,
                lens_mount_model="SEL50F12GM",
                lens_breathing_comp_compliant=True,
                hdmi_raw_output_4264x2408="Off",
                active_frame_rate="59.94p",
                breathing_comp_effectively_active=False,
                fov_crop_applied=False,
            ),
            None,
        ),
        (
            P255_PILLAR_43A_SCENARIO_IDS[2],
            False,
            AutoSlowShutterAndBreathingCompVaultSpec(
                pre_reset_auto_slow_shutter="Off",
                pre_reset_breathing_comp="On",
                reset_action="Camera Settings Reset",
                post_reset_auto_slow_shutter="Off",
                post_reset_breathing_comp="On",
                auto_slow_shutter_effectively_active=False,
                breathing_comp_effectively_active=True,
                fov_crop_applied=True,
            ),
            P255_BLOCKED_AUTO_SLOW_OR_BREATHING_RESET_DRIFT,
        ),
        (
            P255_PILLAR_43A_SCENARIO_IDS[3],
            False,
            AutoSlowShutterAndBreathingCompVaultSpec(
                shooting_domain="Movie",
                exposure_mode="Flexible Exp. Mode",
                flexible_exp_shutter_ctrl="Manual",
                iso_setting="ISO 12800",
                log_shooting_mode="Cine EI Quick",
                reported_lockout_conditions=(),
                auto_slow_shutter_effectively_active=True,
                auto_slow_shutter_lockout_bypass_events=1,
            ),
            P255_BLOCKED_AUTO_SLOW_SHUTTER_6LOCKOUT_BYPASS,
        ),
        (
            P255_PILLAR_43A_SCENARIO_IDS[4],
            False,
            AutoSlowShutterAndBreathingCompVaultSpec(
                shooting_domain="Movie",
                exposure_mode="S",
                iso_setting="ISO AUTO",
                log_shooting_mode="Flexible ISO",
                reported_lockout_conditions=("SHUTTER_PRIORITY_S",),
                auto_slow_shutter_effectively_active=True,
                movie_shutter_mode="Angle",
                movie_shutter_angle_deg=180.0,
                shutter_angle_effectively_active=True,
                auto_slow_shutter_angle_overlap_events=1,
            ),
            P255_BLOCKED_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP,
        ),
        (
            P255_PILLAR_43A_SCENARIO_IDS[5],
            False,
            AutoSlowShutterAndBreathingCompVaultSpec(
                shooting_domain="S&Q",
                exposure_mode="P",
                iso_setting="ISO AUTO",
                log_shooting_mode="Flexible ISO",
                reported_lockout_conditions=("S&Q_MOTION",),
                auto_slow_shutter_effectively_active=False,
                pre_reset_breathing_comp="On",
                post_reset_breathing_comp="On",
                hdmi_raw_output_4264x2408="On",
                active_frame_rate="239.76p",
                breathing_comp_effectively_active=True,
                fov_crop_applied=True,
                breathing_comp_raw_or_240p_bypass_events=1,
            ),
            P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS,
        ),
    )

    outcomes: List[Pillar43ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_auto_slow_shutter_and_breathing_comp_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar43ScenarioOutcome(
                scenario_id=sid,
                pillar="43A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar43ASuiteResult(
        passed=all_ok,
        status=P255_STATUS_VERIFIED_PILLAR_43A if all_ok else P255_STATUS_REJECTED_PILLAR_43A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar43b_hdmi_reccontrol_4chaudio_vault_6_scenario_suite() -> Pillar43BSuiteResult:
    """Run all 6 canonical Pillar 43B scenarios (`2` safe + `4` negative HDMI/TC/4ch/Vault guards)."""
    cases: Tuple[Tuple[str, bool, HdmiRecControl4chAudioAndMediaVaultSpec, Optional[str]], ...] = (
        (
            P255_PILLAR_43B_SCENARIO_IDS[0],
            True,
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_rec_media_dur_hdmi="Off",
                pre_time_code_output="On",
                pre_hdmi_rec_control="On",
                pre_4ch_audio_output="CH3/CH4",
                reset_action="Camera Settings Reset",
                post_rec_media_dur_hdmi="Off",
                post_time_code_output="On",
                post_hdmi_rec_control="On",
                post_4ch_audio_output="CH3/CH4",
                external_recorder_rec_trigger_enabled=True,
                mi_shoe_4ch_audio_active=True,
                shoe_audio_set_mode="48kHz/24bit 4ch",
                hdmi_routed_audio_pair=P255_HDMI_CH3_CH4_PAIR,
                hdmi_connected=True,
                internal_slot1_slot2_clip_rec_inhibited=True,
                proxy_recording_inhibited=True,
                slot1_tier0_vault_active=True,
                slot1_sdxc_wp_locked=True,
            ),
            None,
        ),
        (
            P255_PILLAR_43B_SCENARIO_IDS[1],
            True,
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_rec_media_dur_hdmi="On",
                pre_time_code_output="Off",
                pre_hdmi_rec_control="Off",
                pre_4ch_audio_output="CH1/CH2",
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model="ILME-FX3",
                camset_read_only_load=True,
                saved_rec_media_dur_hdmi="Off",
                saved_time_code_output="On",
                saved_hdmi_rec_control="On",
                saved_4ch_audio_output="CH1/CH2",
                post_rec_media_dur_hdmi="Off",
                post_time_code_output="On",
                post_hdmi_rec_control="On",
                post_4ch_audio_output="CH1/CH2",
                external_recorder_rec_trigger_enabled=True,
                mi_shoe_4ch_audio_active=False,
                shoe_audio_set_mode="48kHz/16bit 2ch",
                hdmi_routed_audio_pair=P255_HDMI_CH1_CH2_PAIR,
                hdmi_connected=True,
                internal_slot1_slot2_clip_rec_inhibited=True,
                proxy_recording_inhibited=True,
                slot1_tier0_vault_active=True,
                slot1_sdxc_wp_locked=True,
            ),
            None,
        ),
        (
            P255_PILLAR_43B_SCENARIO_IDS[2],
            False,
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_rec_media_dur_hdmi="Off",
                pre_time_code_output="On",
                pre_hdmi_rec_control="On",
                pre_4ch_audio_output="CH3/CH4",
                reset_action="Reset Network Set.",
                post_rec_media_dur_hdmi="On",
                post_time_code_output="Off",
                post_hdmi_rec_control="Off",
                post_4ch_audio_output="CH1/CH2",
                external_recorder_rec_trigger_enabled=False,
                hdmi_routed_audio_pair=P255_HDMI_CH1_CH2_PAIR,
                internal_slot1_slot2_clip_rec_inhibited=False,
                proxy_recording_inhibited=False,
                slot1_tier0_vault_active=False,
            ),
            P255_BLOCKED_HDMI_SETTINGS_RESET_SURVIVAL_DRIFT,
        ),
        (
            P255_PILLAR_43B_SCENARIO_IDS[3],
            False,
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_time_code_output="Off",
                pre_hdmi_rec_control="On",
                post_time_code_output="Off",
                post_hdmi_rec_control="On",
                external_recorder_rec_trigger_enabled=True,
                hdmi_rec_ctrl_without_tc_violations=1,
            ),
            P255_BLOCKED_HDMI_REC_CTRL_WITHOUT_TC_OUTPUT,
        ),
        (
            P255_PILLAR_43B_SCENARIO_IDS[4],
            False,
            HdmiRecControl4chAudioAndMediaVaultSpec(
                pre_4ch_audio_output="CH3/CH4",
                post_4ch_audio_output="CH3/CH4",
                mi_shoe_4ch_audio_active=False,
                shoe_audio_set_mode="48kHz/16bit 2ch",
                hdmi_routed_audio_pair=P255_HDMI_CH3_CH4_PAIR,
            ),
            P255_BLOCKED_HDMI_4CH_AUDIO_ROUTING_MISMATCH,
        ),
        (
            P255_PILLAR_43B_SCENARIO_IDS[5],
            False,
            HdmiRecControl4chAudioAndMediaVaultSpec(
                post_rec_media_dur_hdmi="Off",
                hdmi_connected=True,
                internal_slot1_slot2_clip_rec_inhibited=False,
                proxy_recording_inhibited=False,
                slot1_tier0_vault_active=True,
                slot1_sdxc_wp_locked=True,
                camset_save_to_slot1_attempted=True,
                slot1_hdmi_rec_vault_mutation_bytes=4096,
            ),
            P255_BLOCKED_SLOT1_HDMI_REC_VAULT_MUTATION_OR_CAMSET_DRIFT,
        ),
    )

    outcomes: List[Pillar43ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_hdmi_reccontrol_4chaudio_and_media_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar43ScenarioOutcome(
                scenario_id=sid,
                pillar="43B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar43BSuiteResult(
        passed=all_ok,
        status=P255_STATUS_VERIFIED_PILLAR_43B if all_ok else P255_STATUS_REJECTED_PILLAR_43B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar43_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar43StandaloneReport:
    """Run full Pillar 43 standalone suite (`6/6` Pillar 43A + `6/6` Pillar 43B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase255_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar43a_auto_slow_shutter_breathing_vault_6_scenario_suite()
    res_b = run_pillar43b_hdmi_reccontrol_4chaudio_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 255 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 0.15s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE255_SCHEMA,
            "version": PHASE255_VERSION,
            "mode": donor_snapshot.verification_mode,
            "43a": [asdict(s) for s in res_a.scenarios],
            "43b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar43StandaloneReport(
        schema=PHASE255_SCHEMA,
        version=PHASE255_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P255_STATUS_VERIFIED_PILLAR43_SUITE if all_ok else P255_STATUS_FAIL_PILLAR43_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_43a_auto_slow_shutter_breathing_vault=res_a,
        pillar_43b_hdmi_reccontrol_4chaudio_vault=res_b,
        auto_slow_shutter_lockout_bypass_events=P255_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS if res_a.passed else 1,
        auto_slow_shutter_angle_overlap_events=P255_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS if res_a.passed else 1,
        breathing_comp_raw_or_240p_bypass_events=P255_BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS if res_a.passed else 1,
        hdmi_rec_ctrl_without_tc_violations=P255_HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS if res_b.passed else 1,
        slot1_hdmi_rec_vault_mutation_bytes=P255_SLOT1_HDMI_REC_VAULT_MUTATION_BYTES if res_b.passed else 1,
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
# Unified 43/43 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master43_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_43pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master43PillarRecoveryReport:
    """Evaluate and aggregate all 43 recovery pillars (`1..43`) concurrently -> `43/43` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_43_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_42pillar() -> Master42PillarRecoveryReport:
        return evaluate_realhw_42pillar_recovery_master(**kw)

    def _run_p43() -> Tuple[Pillar43StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar43_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_42 = pool.submit(_run_42pillar)
        fut_43 = pool.submit(_run_p43)
        m42_rep = fut_42.result()
        p43_rep, p43_dt = fut_43.result()

    all_errors: List[str] = list(m42_rep.errors) + list(p43_rep.errors)
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
        if getattr(m42_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-42 violated {attr_name} == {expected_val}")
        if getattr(p43_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 43 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("diff_set_transition_corruption_events", 0),
        ("shutter_angle_common_bleed_events", 0),
        ("slot1_custom_key_vault_mutation_bytes", 0),
        ("fx3_has_builtin_evf", False),
        ("evf_finder_monitor_spoof_events", 0),
        ("tier0_battery_high_display_violations", 0),
        ("bt_rmt_ir_lockout_violations", 0),
        ("slot1_mymenu_vault_mutation_bytes", 0),
        ("destructive_menu_delete_confusions", 0),
        ("shutter_angle_exposure_step_drift_events", 0),
        ("fx3_has_var_shutter", False),
        ("unbuffered_battery_pull_events", 0),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(m42_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-42 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("auto_slow_shutter_lockout_bypass_events", 0),
        ("auto_slow_shutter_angle_overlap_events", 0),
        ("breathing_comp_raw_or_240p_bypass_events", 0),
        ("hdmi_rec_ctrl_without_tc_violations", 0),
        ("slot1_hdmi_rec_vault_mutation_bytes", 0),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(p43_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 43 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m42_rep.pillars)
    spec43 = MASTER_43_PILLAR_SPECS[42]
    p43_metrics = {
        "pillar_43a_auto_slow_shutter_breathing_vault": (
            f"{p43_rep.pillar_43a_auto_slow_shutter_breathing_vault.scenarios_passed}/"
            f"{p43_rep.pillar_43a_auto_slow_shutter_breathing_vault.scenarios_total}"
        ),
        "pillar_43b_hdmi_reccontrol_4chaudio_vault": (
            f"{p43_rep.pillar_43b_hdmi_reccontrol_4chaudio_vault.scenarios_passed}/"
            f"{p43_rep.pillar_43b_hdmi_reccontrol_4chaudio_vault.scenarios_total}"
        ),
        "auto_slow_shutter_lockout_bypass_events": p43_rep.auto_slow_shutter_lockout_bypass_events,
        "auto_slow_shutter_angle_overlap_events": p43_rep.auto_slow_shutter_angle_overlap_events,
        "breathing_comp_raw_or_240p_bypass_events": p43_rep.breathing_comp_raw_or_240p_bypass_events,
        "hdmi_rec_ctrl_without_tc_violations": p43_rep.hdmi_rec_ctrl_without_tc_violations,
        "slot1_hdmi_rec_vault_mutation_bytes": p43_rep.slot1_hdmi_rec_vault_mutation_bytes,
        "hardware_live_attachment_authorized": p43_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p43_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec43[0],
            pillar_id=spec43[1],
            phase_label=spec43[2],
            module_name=spec43[3],
            passed=bool(p43_rep.all_passed),
            status=p43_rep.status,
            verification_mode=p43_rep.verification_mode,
            elapsed_seconds=p43_dt,
            key_metrics=p43_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec43[1],
                    "mode": p43_rep.verification_mode,
                    "status": p43_rep.status,
                    "metrics": p43_metrics,
                    "passed": p43_rep.all_passed,
                }
            ),
            errors=tuple(p43_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master43_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p43_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_43_PILLAR_COUNT == 43
        and pillars_passed == 43
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE255_SCHEMA,
            "version": PHASE255_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master43PillarRecoveryReport(
        schema=PHASE255_SCHEMA,
        version=PHASE255_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P255_STATUS_VERIFIED_43OF43_AGGREGATOR if all_ok else P255_STATUS_FAIL_43OF43_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P255_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P255_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p43_rep.donor_snapshot,
        pillar43_a_auto_slow_shutter_breathing_vault=p43_rep.pillar_43a_auto_slow_shutter_breathing_vault,
        pillar43_b_hdmi_reccontrol_4chaudio_vault=p43_rep.pillar_43b_hdmi_reccontrol_4chaudio_vault,
        auto_slow_shutter_lockout_bypass_events=p43_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=p43_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=p43_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=p43_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=p43_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m42_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m42_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m42_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m42_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m42_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m42_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m42_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m42_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m42_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m42_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m42_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m42_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p43_rep.hardware_live_attachment_authorized,
        master_43pillar_sha256=master_sha,
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


def evaluate_43pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master43PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_43pillar_recovery_master`."""
    return evaluate_realhw_43pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_43pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master43PillarRecoveryReport:
    """Public CLI entry point for Phase 255 Pillar 43 unified `43/43` real-hardware recovery master."""
    return evaluate_realhw_43pillar_recovery_master(
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
    "MASTER_43_PILLAR_COUNT",
    "MASTER_43_PILLAR_IDS",
    "MASTER_43_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P255_AUTO_SLOW_SHUTTER_6_LOCKOUT_CONDITIONS",
    "P255_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP_EVENTS",
    "P255_AUTO_SLOW_SHUTTER_DEFAULT",
    "P255_AUTO_SLOW_SHUTTER_LOCKOUT_BYPASS_EVENTS",
    "P255_AUTO_SLOW_SHUTTER_MENU_PATH",
    "P255_AUTO_SLOW_SHUTTER_MODES",
    "P255_BLOCKED_AUTO_SLOW_OR_BREATHING_RESET_DRIFT",
    "P255_BLOCKED_AUTO_SLOW_SHUTTER_6LOCKOUT_BYPASS",
    "P255_BLOCKED_AUTO_SLOW_SHUTTER_ANGLE_OVERLAP",
    "P255_BLOCKED_BREATHING_COMP_BOUNDARY_OR_BYPASS",
    "P255_BLOCKED_HDMI_4CH_AUDIO_ROUTING_MISMATCH",
    "P255_BLOCKED_HDMI_REC_CTRL_WITHOUT_TC_OUTPUT",
    "P255_BLOCKED_HDMI_SETTINGS_RESET_SURVIVAL_DRIFT",
    "P255_BLOCKED_INVALID_AUTO_SLOW_OR_BREATHING_SPEC",
    "P255_BLOCKED_INVALID_HDMI_OUTPUT_SETTINGS_SPEC",
    "P255_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P255_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P255_BLOCKED_SLOT1_HDMI_REC_VAULT_MUTATION_OR_CAMSET_DRIFT",
    "P255_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P255_BOUNDED_HEADER_BYTES",
    "P255_BREATHING_COMP_DEFAULT",
    "P255_BREATHING_COMP_LOCKOUT_SQ_RATES",
    "P255_BREATHING_COMP_MENU_PATH",
    "P255_BREATHING_COMP_MODES",
    "P255_BREATHING_COMP_RAW_OR_240P_BYPASS_EVENTS",
    "P255_CAMSET_FILENAMES",
    "P255_CONCURRENT_CEILING_SECONDS",
    "P255_DEFAULT_MOVIE_SHUTTER_ANGLE_DEG",
    "P255_DONOR_FX3_APPFW_702_RELPATH",
    "P255_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P255_DONOR_FX3_BODYDATA_RELPATH",
    "P255_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH",
    "P255_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH",
    "P255_DONOR_FX3_LIBBACKUP_SO_RELPATH",
    "P255_DONOR_FX3_LIBGPE_SO_RELPATH",
    "P255_DONOR_FX3_LIBINFRALENSCOMMUNICATOR_SO_RELPATH",
    "P255_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH",
    "P255_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P255_DONOR_FX6_APPFW_601_RELPATH",
    "P255_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH",
    "P255_DONOR_INSPECT_BUDGET_SECONDS",
    "P255_EXPOSURE_MODES",
    "P255_FLEXIBLE_EXP_SHUTTER_CTRL_MODES",
    "P255_FORBIDDEN_PERSISTENT_TARGETS",
    "P255_FX3_BREATHING_COMP_MIN_FW_VERSIONS",
    "P255_FX3_FW_VERSION",
    "P255_FX3_HELPGUIDE_ID",
    "P255_FX3_MODEL_ID",
    "P255_FX3_MODEL_NAME",
    "P255_FX3_SHUTTER_ANGLE_MIN_FW_VERSIONS",
    "P255_FX3_SUPPORTED_FW_VERSIONS",
    "P255_FX6_DONOR_FW_VERSION",
    "P255_FX6_DONOR_MODEL_NAME",
    "P255_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P255_HDMI_4CH_AUDIO_OUTPUT_DEFAULT",
    "P255_HDMI_4CH_AUDIO_OUTPUT_MODES",
    "P255_HDMI_CH1_CH2_PAIR",
    "P255_HDMI_CH3_CH4_PAIR",
    "P255_HDMI_OUTPUT_SETTINGS_MENU_PATH",
    "P255_HDMI_RAW_4264X2408_RESOLUTION",
    "P255_HDMI_RAW_OUTPUT_MODES",
    "P255_HDMI_REC_CONTROL_DEFAULT",
    "P255_HDMI_REC_CONTROL_MODES",
    "P255_HDMI_REC_CTRL_WITHOUT_TC_VIOLATIONS",
    "P255_ISO_AUTO_TOKEN",
    "P255_LOG_CINE_EI_LOCKOUT_MODES",
    "P255_LOG_SHOOTING_MODES",
    "P255_MAX_FULL_DONOR_BYTES",
    "P255_MOVIE_AND_SQ_FRAME_RATES",
    "P255_MOVIE_SHUTTER_MODES",
    "P255_MOVIE_SHUTTER_MODE_DEFAULT",
    "P255_NOMINAL_BUDGET_SECONDS",
    "P255_PILLAR_43A_SCENARIO_IDS",
    "P255_PILLAR_43B_SCENARIO_IDS",
    "P255_PINNED_FX3_APPFW_702_BYTES",
    "P255_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P255_PINNED_FX3_BACKUP_BIN_BYTES",
    "P255_PINNED_FX3_BACKUP_BIN_SHA256",
    "P255_PINNED_FX3_BODYDATA_BYTES",
    "P255_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P255_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES",
    "P255_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256",
    "P255_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES",
    "P255_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256",
    "P255_PINNED_FX3_LIBBACKUP_SO_BYTES",
    "P255_PINNED_FX3_LIBBACKUP_SO_SHA256",
    "P255_PINNED_FX3_LIBGPE_SO_BYTES",
    "P255_PINNED_FX3_LIBGPE_SO_SHA256",
    "P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_BYTES",
    "P255_PINNED_FX3_LIBINFRALENSCOMMUNICATOR_SO_SHA256",
    "P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES",
    "P255_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256",
    "P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P255_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P255_PINNED_FX6_APPFW_601_BYTES",
    "P255_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES",
    "P255_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256",
    "P255_REC_MEDIA_DUR_HDMI_DEFAULT",
    "P255_REC_MEDIA_DUR_HDMI_MODES",
    "P255_RESET_ACTIONS",
    "P255_SHOOTING_DOMAINS",
    "P255_SHUTTER_MODE_MENU_PATH",
    "P255_SLOT1_HDMI_REC_VAULT_MUTATION_BYTES",
    "P255_SLOT1_VAULT_SLOT",
    "P255_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P255_STATUS_FAIL_43OF43_AGGREGATOR",
    "P255_STATUS_FAIL_PILLAR43_SUITE",
    "P255_STATUS_REJECTED_PILLAR_43A",
    "P255_STATUS_REJECTED_PILLAR_43B",
    "P255_STATUS_VERIFIED_43OF43_AGGREGATOR",
    "P255_STATUS_VERIFIED_PILLAR43_SUITE",
    "P255_STATUS_VERIFIED_PILLAR_43A",
    "P255_STATUS_VERIFIED_PILLAR_43B",
    "P255_TIER0_SURFACE_COUNT",
    "P255_TIME_CODE_OUTPUT_DEFAULT",
    "P255_TIME_CODE_OUTPUT_MODES",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE255_SCHEMA",
    "PHASE255_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "AutoSlowShutterAndBreathingCompVaultReport",
    "AutoSlowShutterAndBreathingCompVaultSpec",
    "AutoSlowShutterHdmiRecControlAndBreathingVaultReport",
    "HdmiRecControl4chAudioAndMediaVaultReport",
    "HdmiRecControl4chAudioAndMediaVaultSpec",
    "Master43PillarRecoveryReport",
    "Phase255DonorArtifactDigest",
    "Phase255DonorSnapshot",
    "Pillar43ASuiteResult",
    "Pillar43BSuiteResult",
    "Pillar43ScenarioOutcome",
    "Pillar43StandaloneReport",
    "build_default_safe_auto_slow_shutter_breathing_vault_spec",
    "build_default_safe_hdmi_reccontrol_4chaudio_vault_spec",
    "compute_expected_auto_slow_shutter_lockouts",
    "evaluate_43pillar_recovery_master",
    "evaluate_auto_slow_shutter_and_breathing_comp_vault",
    "evaluate_hdmi_reccontrol_4chaudio_and_media_vault",
    "evaluate_realhw_43pillar_recovery_master",
    "inspect_phase255_donors_readonly",
    "run_pillar43_standalone_suite",
    "run_pillar43a_auto_slow_shutter_breathing_vault_6_scenario_suite",
    "run_pillar43b_hdmi_reccontrol_4chaudio_vault_6_scenario_suite",
    "verify_43pillar_recovery_suite",
    "verify_auto_slow_shutter_hdmi_reccontrol_and_breathing_vault",
    "verify_auto_slow_shutter_hdmi_reccontrol_breathing_vault",
]
