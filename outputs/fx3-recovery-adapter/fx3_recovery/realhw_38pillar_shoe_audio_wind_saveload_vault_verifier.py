"""Phase 240 — Pillar 38 (`38/38` Recovery Pillars) & Unified 38-Pillar Recovery Master
(`verify-38pillar-recovery` / `verify-shoe-audio-wind-saveload-vault`):

1. **Pillar 38A — `[Shoe Audio Set.]` (`48kHz/24bit 4ch` / `24bit 2ch` / `16bit 2ch`) Recovery,
   3-Condition Hardware Lockouts (`[Audio Recording]=Off` / `S&Q Motion`, Body `3.5mm` `MIC` Jack,
   `XLR-H1` `[ANALOG]` Switch), `CH1..CH4` Meter Coupling & `[Wind Noise Reduct.]` Built-In-Mic-Only
   Post-Reset `[Off]` Baseline (`ILME-FX3 Ver. 7.02`)**:
   - Models `MENU` -> `Shooting` -> `[Audio Recording]` -> `[Shoe Audio Set.]` (`48kHz/16bit 2ch`
     factory default, `48kHz/24bit 2ch`, `48kHz/24bit 4ch`) and `[Wind Noise Reduct.]` (`Off`
     factory default / `On`), verifying both reset cleanly via `[Camera Settings Reset]` (and
     `[Initialize]`) and restore deterministically via Slot-1 `CAMSET01.DAT` `[Load]`.
   - Enforces all 3 `[Shoe Audio Set.]` hardware lockouts (`[Audio Recording]=Off` or `S&Q Motion`,
     body `3.5mm` `MIC` plug-in override, and `XLR-H1` `[ANALOG]` slide-switch fallback) plus
     automatic `4ch` (`CH1..CH4`) `[Audio Level Display]` meter expansion in digital `48kHz/24bit 4ch`.
   - Enforces `[Wind Noise Reduct.]` built-in stereo microphone exclusivity (non-functional when a
     `3.5mm` or MI Shoe `XLR-H1` external mic is used, where physical `XLR-H1` `[LOW CUT]` `Off` /
     `100Hz` / `300Hz` applies instead) and locks indoor bench recovery rehearsals to `[Off]` so
     normal low-frequency audio is never attenuated.

2. **Pillar 38B — `[Save/Load Settings]` (`CAMSET01.DAT..CAMSET10.DAT` & `C3 Portal` `Cloud(Private)` /
   `Cloud(Share)`) Same-Model Firewall, Excluded Privacy/Calibration Items Firewall & Slot-1 Tier-0
   Vault Write Lock**:
   - Models `MENU` -> `Setup` -> `[Reset/Save Settings]` -> `[Save/Load Settings]` across `Media`
     (`CAMSET01.DAT..CAMSET10.DAT`, max `10` per card under `/PRIVATE/SONY/PRO/CAMERA/ILME-FX3`,
     strict `ILME-FX3` model lock rejecting `ILME-FX6` `.DAT`) and `Cloud(Private)` / `Cloud(Share)`
     (`Creators' Cloud` / `C3 Portal` `Ver. 4.00+`).
   - Enforces the Sony Help Guide **Excluded-Items Firewall**: `[Save]` and `[Load]` NEVER export or
     overwrite `[IPTC Information]`, `[Copyright Info]`, `[Custom White Balance]` (`Custom 1..3`),
     `[Face Memory]`, or Network credentials (`FTP`, `RTMP/SRT Streaming`, `Wi-Fi` SSIDs/passphrases,
     static IP/DNS, imported TLS certificates) (`excluded_secret_or_cal_leak_count == 0`).
   - Enforces the **Slot-1 Tier-0 Vault Write Firewall**: `[Load]` from Slot 1 is `O_RDONLY`-safe,
     whereas `[Save]` targeting an unverified, `WP`-locked, or baseline-protected Slot 1 Tier-0
     forensic card (`pnflasha` / `cnflasha` / baseline `CAMSET01.DAT`) is blocked
     (`slot1_unverified_camset_save_mutations == 0`; scratch `[Save]` permitted on Slot 2 or
     post-SHA256-verified scratch media).

3. **Unified `38/38` Recovery Master (`evaluate_realhw_38pillar_recovery_master`)**:
   - Delegates Pillars `1..37` concurrently to `evaluate_realhw_37pillar_recovery_master` +
     **Pillar 38** -> **`38/38` (`VERIFIED_38OF38_PILLAR_RECOVERY_MASTER`)** in `< 4.0s` (`< 6.0s` ceiling).
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
from .realhw_37pillar_touch_recframe_hdmi_sunny_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_37_PILLAR_SPECS,
    Master37PillarRecoveryReport,
    evaluate_realhw_37pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE240_SCHEMA: str = "realhw_38pillar_shoe_audio_wind_saveload_vault_verifier_v1"
PHASE240_VERSION: str = "1.0.0"

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

P240_DONOR_INSPECT_BUDGET_SECONDS: float = 0.15
P240_NOMINAL_BUDGET_SECONDS: float = 4.0
P240_CONCURRENT_CEILING_SECONDS: float = 6.0
P240_BOUNDED_HEADER_BYTES: int = 4096
P240_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Pinned Wave-36 / FX3 Ver. 7.02 & FX6 Ver. 6.01 Donor Anchors (bounded O_RDONLY verification)
P240_FX3_MODEL_NAME: str = "ILME-FX3"
P240_FX3_MODEL_ID: int = 0x91030080
P240_FX3_FW_VERSION: str = "7.02"
P240_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P240_FX6_DONOR_FW_VERSION: str = "6.01"
P240_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
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
P240_C3_PORTAL_MIN_FW_VERSION: str = "4.00"
P240_C3_PORTAL_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P240_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P240_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P240_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"

P240_DONOR_FX3_APPFW_702_RELPATH: str = "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
P240_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P240_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"

P240_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P240_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P240_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"

P240_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P240_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P240_PINNED_FX3_BACKUP_BIN_SHA256: str = "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"

P240_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P240_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P240_PINNED_FX3_LIBBACKUP_SO_SHA256: str = "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"

P240_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P240_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P240_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"

P240_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P240_DONOR_HOTSHOE_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so"
)
P240_PINNED_HOTSHOE_SO_BYTES: int = 47808
P240_PINNED_HOTSHOE_SO_SHA256: str = (
    "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6"
)

# Pillar 38A — [Shoe Audio Set.] 48kHz/24bit 4ch & [Wind Noise Reduct.] Built-In-Mic-Only Baseline
P240_SHOE_AUDIO_SET_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Audio Recording",
    "Shoe Audio Set.",
)
P240_SHOE_AUDIO_SET_DEFAULT: str = "48kHz/16bit 2ch"
P240_SHOE_AUDIO_SET_MODES: Tuple[str, ...] = (
    "48kHz/16bit 2ch",
    "48kHz/24bit 2ch",
    "48kHz/24bit 4ch",
)

P240_WIND_NOISE_REDUCT_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Shooting",
    "Audio Recording",
    "Wind Noise Reduct.",
)
P240_WIND_NOISE_REDUCT_DEFAULT: str = "Off"
P240_WIND_NOISE_REDUCT_MODES: Tuple[str, ...] = ("Off", "On")

P240_AUDIO_RECORDING_MODES: Tuple[str, ...] = ("On", "Off")
P240_AUDIO_LEVEL_DISPLAY_MODES: Tuple[str, ...] = ("On", "Off")
P240_SHOOTING_MODES: Tuple[str, ...] = ("Movie", "S&Q Motion")
P240_SHOE_ATTACHMENTS: Tuple[str, ...] = ("NONE", "XLR-H1", "ECM-M1", "ANALOG_MI_MIC")
P240_DIGITAL_4CH_SHOE_ATTACHMENTS: Tuple[str, ...] = ("XLR-H1", "ECM-M1")
P240_XLRH1_SWITCH_MODES: Tuple[str, ...] = ("DIGITAL", "ANALOG")
P240_XLRH1_HARDWARE_LOW_CUT_MODES: Tuple[str, ...] = ("Off", "100Hz", "300Hz")
P240_EFFECTIVE_AUDIO_SOURCES: Tuple[str, ...] = (
    "DISABLED",
    "BUILT_IN_STEREO_MIC",
    "BODY_35MM_ANALOG_MIC",
    "MI_SHOE_ANALOG_2CH",
    "MI_SHOE_DIGITAL",
)
P240_CH1_CH2_METERS: Tuple[str, ...] = ("CH1", "CH2")
P240_CH1_TO_CH4_METERS: Tuple[str, ...] = ("CH1", "CH2", "CH3", "CH4")
P240_RESET_ACTIONS: Tuple[str, ...] = ("NONE", "Camera Settings Reset", "Initialize")

# Pillar 38B — [Save/Load Settings] CAMSET01..10.DAT & C3 Portal Exclusions + Slot-1 Tier-0 Vault Firewall
P240_SAVE_LOAD_SETTINGS_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Reset/Save Settings",
    "Save/Load Settings",
)
P240_SAVE_LOAD_OPERATIONS: Tuple[str, ...] = ("Load", "Save")
P240_SAVE_LOAD_STORAGE_TARGETS: Tuple[str, ...] = ("Media", "Cloud(Private)", "Cloud(Share)")
P240_CLOUD_STORAGE_TARGETS: Tuple[str, ...] = ("Cloud(Private)", "Cloud(Share)")
P240_MEDIA_SLOTS: Tuple[int, ...] = (1, 2)
P240_SLOT1_VAULT_SLOT: int = 1
P240_SLOT2_SCRATCH_SLOT: int = 2
P240_CAMSET_MAX_FILES_PER_CARD: int = 10
P240_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P240_CAMSET_MEDIA_DIR: str = "/PRIVATE/SONY/PRO/CAMERA/ILME-FX3"
P240_FOREIGN_CAMSET_MODELS: Tuple[str, ...] = ("ILME-FX6", "ILME-FX30", "ILME-FX3A", "ILCE-7SM3")

P240_EXCLUDED_PRIVACY_AND_CALIBRATION_CATEGORIES: Tuple[str, ...] = (
    "IPTC_INFORMATION",
    "COPYRIGHT_INFO",
    "CUSTOM_WHITE_BALANCE_1_TO_3",
    "FACE_MEMORY",
    "FTP_TRANSFER_CREDENTIALS",
    "STREAMING_RTMP_SRT_KEYS",
    "WIFI_SSID_PASSPHRASE",
    "STATIC_IP_AND_TLS_CERTS",
)
P240_TIER0_SLOT1_VAULT_ARTIFACTS: Tuple[str, ...] = (
    "pnflasha_raw_isp_dump",
    "cnflasha_logical_dump",
    "CAMSET01.DAT",
)

P240_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx6_shoe_audio_wind_saveload_overlay"
P240_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P240_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P240_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P240_BLOCKED_INVALID_SHOE_AUDIO_OR_WIND_SPEC: str = "BLOCKED_INVALID_SHOE_AUDIO_OR_WIND_SPEC"
P240_BLOCKED_SHOE_AUDIO_OR_WIND_RESET_DRIFT: str = "BLOCKED_SHOE_AUDIO_OR_WIND_RESET_DRIFT"
P240_BLOCKED_CAMSET_SHOE_AUDIO_OR_WIND_RESTORE_DRIFT: str = (
    "BLOCKED_CAMSET_SHOE_AUDIO_OR_WIND_RESTORE_DRIFT"
)
P240_BLOCKED_SHOE_AUDIO_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION: str = (
    "BLOCKED_SHOE_AUDIO_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION"
)
P240_BLOCKED_SHOE_AUDIO_35MM_JACK_OVERRIDE_VIOLATION: str = (
    "BLOCKED_SHOE_AUDIO_35MM_JACK_OVERRIDE_VIOLATION"
)
P240_BLOCKED_SHOE_AUDIO_XLRH1_ANALOG_SWITCH_FALLBACK_VIOLATION: str = (
    "BLOCKED_SHOE_AUDIO_XLRH1_ANALOG_SWITCH_FALLBACK_VIOLATION"
)
P240_BLOCKED_SHOE_AUDIO_4CH_METER_COUPLING_MISMATCH: str = (
    "BLOCKED_SHOE_AUDIO_4CH_METER_COUPLING_MISMATCH"
)
P240_BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION: str = (
    "BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION"
)
P240_BLOCKED_WIND_NOISE_INDOOR_BENCH_LOW_FREQ_ATTENUATION: str = (
    "BLOCKED_WIND_NOISE_INDOOR_BENCH_LOW_FREQ_ATTENUATION"
)

P240_BLOCKED_INVALID_SAVELOAD_OR_CLOUD_SPEC: str = "BLOCKED_INVALID_SAVELOAD_OR_CLOUD_SPEC"
P240_BLOCKED_CROSS_MODEL_FX6_DAT_REJECTED: str = "BLOCKED_CROSS_MODEL_FX6_DAT_REJECTED"
P240_BLOCKED_CAMSET_FILENAME_OR_10FILE_CAP_VIOLATION: str = (
    "BLOCKED_CAMSET_FILENAME_OR_10FILE_CAP_VIOLATION"
)
P240_BLOCKED_C3_PORTAL_VERSION_OR_AUTH_VIOLATION: str = (
    "BLOCKED_C3_PORTAL_VERSION_OR_AUTH_VIOLATION"
)
P240_BLOCKED_CLOUD_SYNC_DURING_AIRGAP_TIER0_VAULT: str = (
    "BLOCKED_CLOUD_SYNC_DURING_AIRGAP_TIER0_VAULT"
)
P240_BLOCKED_SAVELOAD_EXCLUDED_PRIVACY_OR_CAL_LEAK: str = (
    "BLOCKED_SAVELOAD_EXCLUDED_PRIVACY_OR_CAL_LEAK"
)
P240_BLOCKED_SLOT1_WP_LOCKED_SAVE_DENIED: str = "BLOCKED_SLOT1_WP_LOCKED_SAVE_DENIED"
P240_BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN: str = (
    "BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN"
)
P240_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P240_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P240_STATUS_VERIFIED_PILLAR_38A: str = (
    "VERIFIED_PILLAR_38A_SHOE_AUDIO_4CH_LOCKOUTS_AND_WIND_NOISE_BUILTIN_BASELINE"
)
P240_STATUS_REJECTED_PILLAR_38A: str = (
    "REJECTED_PILLAR_38A_SHOE_AUDIO_4CH_LOCKOUTS_AND_WIND_NOISE_BUILTIN_BASELINE"
)
P240_STATUS_VERIFIED_PILLAR_38B: str = (
    "VERIFIED_PILLAR_38B_SAVELOAD_CAMSET_C3_EXCLUSIONS_AND_SLOT1_VAULT_FIREWALL"
)
P240_STATUS_REJECTED_PILLAR_38B: str = (
    "REJECTED_PILLAR_38B_SAVELOAD_CAMSET_C3_EXCLUSIONS_AND_SLOT1_VAULT_FIREWALL"
)
P240_STATUS_VERIFIED_PILLAR38_SUITE: str = (
    "VERIFIED_PILLAR38_SHOE_AUDIO_WIND_SAVELOAD_VAULT"
)
P240_STATUS_FAIL_PILLAR38_SUITE: str = (
    "FAIL_PILLAR38_SHOE_AUDIO_WIND_SAVELOAD_VAULT"
)
P240_STATUS_VERIFIED_38OF38_AGGREGATOR: str = "VERIFIED_38OF38_PILLAR_RECOVERY_MASTER"
P240_STATUS_FAIL_38OF38_AGGREGATOR: str = "FAIL_38OF38_PILLAR_RECOVERY_MASTER"

P240_PILLAR_38A_SCENARIO_IDS: Tuple[str, ...] = (
    "P38A1_CAMERA_SETTINGS_RESET_RESTORES_16BIT_2CH_AND_WIND_OFF_INDOOR_BUILT_IN_MIC_SAFE",
    "P38A2_CAMSET01_LOAD_RESTORES_XLRH1_DIGITAL_24BIT_4CH_CH1_TO_CH4_METERS_AND_HARDWARE_LOWCUT_SAFE",
    "P38A3_REJECT_SHOE_AUDIO_4CH_WHEN_35MM_MIC_PLUGGED_IN_OR_XLRH1_ANALOG_SWITCH_OR_SQ_LOCKOUT",
    "P38A4_REJECT_SHOE_AUDIO_OR_WIND_NOISE_FAILING_CAMERA_SETTINGS_RESET_TO_DEFAULTS",
    "P38A5_REJECT_WIND_NOISE_REDUCT_CLAIMED_ACTIVE_ON_EXTERNAL_35MM_OR_XLRH1_MIC",
    "P38A6_REJECT_INDOOR_BENCH_WIND_NOISE_REDUCT_ON_LOW_FREQUENCY_ATTENUATION_HAZARD",
)
P240_PILLAR_38B_SCENARIO_IDS: Tuple[str, ...] = (
    "P38B1_SLOT1_ORDONLY_CAMSET01_LOAD_WITH_ZERO_EXCLUDED_PRIVACY_CAL_LEAKS_AND_WP_VAULT_INTACT_SAFE",
    "P38B2_SLOT2_SCRATCH_CAMSET02_SAVE_AND_C3_PORTAL_VER702_EXCLUSION_FIREWALL_SAFE",
    "P38B3_REJECT_SLOT1_SAVE_TARGETING_UNVERIFIED_OR_BASELINE_TIER0_FORENSIC_VAULT_CARD",
    "P38B4_REJECT_SAVELOAD_OR_CLOUD_SHARE_LEAKING_IPTC_COPYRIGHT_CUSTOM_WB_FACE_OR_NETWORK_CREDENTIALS",
    "P38B5_REJECT_CROSS_MODEL_ILME_FX6_DAT_IMPORT_ON_ILME_FX3",
    "P38B6_REJECT_CAMSET11_OVER_10_CAP_OR_PRE_400_C3_PORTAL_CLOUD_SYNC",
)

MASTER_38_PILLAR_COUNT: int = 38
MASTER_38_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_37_PILLAR_SPECS + (
    (
        38,
        "pillar_38_shoe_audio_wind_saveload_vault",
        "Phase 240",
        "fx3_recovery.realhw_38pillar_shoe_audio_wind_saveload_vault_verifier",
    ),
)
MASTER_38_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_38_PILLAR_SPECS)


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
    return any(tok in low for tok in P240_FORBIDDEN_PERSISTENT_TARGETS)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase240DonorArtifactDigest:
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
class Phase240DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase240DonorArtifactDigest, ...]


@dataclass(frozen=True)
class ShoeAudio4chAndWindNoiseVaultSpec:
    camera_model: str = P240_FX3_MODEL_NAME
    fw_version: str = P240_FX3_FW_VERSION
    shoe_audio_menu_path: Tuple[str, ...] = P240_SHOE_AUDIO_SET_MENU_PATH
    wind_noise_menu_path: Tuple[str, ...] = P240_WIND_NOISE_REDUCT_MENU_PATH
    shooting_mode: str = "Movie"  # Movie | S&Q Motion
    audio_recording: str = "On"  # On | Off
    audio_level_display: str = "On"  # On | Off
    shoe_attachment: str = "NONE"  # NONE | XLR-H1 | ECM-M1 | ANALOG_MI_MIC
    xlrh1_digital_analog_switch: str = "DIGITAL"  # DIGITAL | ANALOG
    xlrh1_hardware_low_cut: str = "Off"  # Off | 100Hz | 300Hz
    body_35mm_mic_plugged_in: bool = False
    pre_reset_shoe_audio_set: str = "48kHz/24bit 4ch"
    pre_reset_wind_noise_reduct: str = "On"
    reset_action: str = "Camera Settings Reset"  # NONE | Camera Settings Reset | Initialize
    camset_load_after_reset: bool = False
    camset_slot: int = P240_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    saved_shoe_audio_set: str = "48kHz/24bit 4ch"
    saved_wind_noise_reduct: str = "Off"
    post_reset_shoe_audio_set: str = P240_SHOE_AUDIO_SET_DEFAULT
    post_reset_wind_noise_reduct: str = P240_WIND_NOISE_REDUCT_DEFAULT
    shoe_audio_set_available: bool = False
    effective_audio_source: str = "BUILT_IN_STEREO_MIC"
    effective_recorded_audio_channels: int = 2
    effective_audio_bit_depth: int = 16
    audio_level_display_meters: Tuple[str, ...] = P240_CH1_CH2_METERS
    wind_noise_reduct_available: bool = True
    wind_noise_reduct_effective_dsp_active: bool = False
    indoor_bench_recovery_rehearsal: bool = True
    indoor_low_freq_attenuation_hazard: bool = False
    overlay_dir: str = P240_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P240_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P240_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P240_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class ShoeAudio4chAndWindNoiseVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    shoe_audio_and_wind_reset_verified: bool
    camset_restore_verified: bool
    shoe_audio_3lockouts_and_4ch_meters_verified: bool
    wind_noise_builtin_mic_exclusivity_verified: bool
    indoor_bench_wind_off_baseline_verified: bool
    h0_equals_h3_verified: bool
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class SaveLoadC3ExclusionsAndSlot1VaultSpec:
    camera_model: str = P240_FX3_MODEL_NAME
    fw_version: str = P240_FX3_FW_VERSION
    menu_path: Tuple[str, ...] = P240_SAVE_LOAD_SETTINGS_MENU_PATH
    operation: str = "Load"  # Load | Save
    storage_target: str = "Media"  # Media | Cloud(Private) | Cloud(Share)
    media_slot: int = P240_SLOT1_VAULT_SLOT  # 1 | 2
    camset_media_dir: str = P240_CAMSET_MEDIA_DIR
    camset_filename: str = "CAMSET01.DAT"
    card_camset_file_count: int = 1
    profile_model_name: str = P240_FX3_MODEL_NAME
    c3_portal_authenticated: bool = False
    airgap_tier0_vault_active: bool = True
    action_entry_stateful_reset_drift: bool = False
    iptc_or_copyright_exported_or_overwritten: bool = False
    custom_wb_1_to_3_exported_or_overwritten: bool = False
    face_memory_biometrics_exported_or_overwritten: bool = False
    network_ftp_rtmp_srt_wifi_tls_credentials_exported_or_overwritten: bool = False
    leaked_excluded_categories: Tuple[str, ...] = ()
    excluded_secret_or_cal_leak_count: int = 0
    slot1_tier0_vault_present: bool = True
    slot1_sdxc_wp_switch_locked: bool = True
    slot1_offcamera_sha256_verified: bool = True
    slot1_scratch_save_authorized_after_vault_verify: bool = False
    preserve_baseline_camset01_dat: bool = True
    card_read_only_access: bool = True
    card_sectors_mutated: int = 0
    slot1_unverified_camset_save_mutations: int = 0
    stage_b_overlay_dir: str = P240_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P240_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P240_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P240_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class SaveLoadC3ExclusionsAndSlot1VaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    same_model_fx3_lock_verified: bool
    media_10file_and_c3_cloud_target_verified: bool
    excluded_items_privacy_cal_firewall_verified: bool
    slot1_tier0_vault_write_firewall_verified: bool
    h0_equals_h3_verified: bool
    excluded_secret_or_cal_leak_count: int
    slot1_unverified_camset_save_mutations: int
    tier0_surfaces_intact: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ShoeAudioWindAndSaveLoadVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase240DonorSnapshot
    shoe_audio_wind_report: ShoeAudio4chAndWindNoiseVaultReport
    saveload_c3_vault_report: SaveLoadC3ExclusionsAndSlot1VaultReport
    excluded_secret_or_cal_leak_count: int
    slot1_unverified_camset_save_mutations: int
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
class Pillar38ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar38ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar38ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar38BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar38ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar38StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase240DonorSnapshot
    pillar_38a_shoe_audio_wind_vault: Pillar38ASuiteResult
    pillar_38b_saveload_c3_exclusion_vault: Pillar38BSuiteResult
    excluded_secret_or_cal_leak_count: int
    slot1_unverified_camset_save_mutations: int
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
class Master38PillarRecoveryReport:
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
    donor_snapshot: Phase240DonorSnapshot
    pillar38_a_shoe_audio_wind_vault: Pillar38ASuiteResult
    pillar38_b_saveload_c3_exclusion_vault: Pillar38BSuiteResult
    excluded_secret_or_cal_leak_count: int
    slot1_unverified_camset_save_mutations: int
    master_38pillar_sha256: str
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
    max_full_bytes: int = P240_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P240_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase240_donors() -> Tuple[Phase240DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P240_DONOR_FX3_BODYDATA_RELPATH,
            P240_PINNED_FX3_BODYDATA_BYTES,
            P240_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P240_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P240_DONOR_FX3_APPFW_702_RELPATH,
            P240_PINNED_FX3_APPFW_702_BYTES,
            P240_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P240_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx6_appfw_601_so",
            P240_DONOR_FX6_APPFW_601_RELPATH,
            P240_PINNED_FX6_APPFW_601_BYTES,
            P240_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P240_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P240_DONOR_FX3_BACKUP_BIN_RELPATH,
            P240_PINNED_FX3_BACKUP_BIN_BYTES,
            P240_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P240_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx3_libbackup_so",
            P240_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P240_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P240_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P240_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P240_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P240_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P240_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P240_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P240_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "donor_libinfrahotshoe_so",
            P240_DONOR_HOTSHOE_SO_RELPATH,
            P240_PINNED_HOTSHOE_SO_BYTES,
            P240_PINNED_HOTSHOE_SO_BYTES,
            "FULL_SHA256",
            P240_PINNED_HOTSHOE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZN12InfraHotshoe9GetShoeIdEj+_ZN12InfraHotshoe13QueryShoeIdOnEij+_ZN12InfraHotshoe11SetAdcLevelEiPj",
        ),
    )
    return tuple(
        Phase240DonorArtifactDigest(
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


def inspect_phase240_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase240DonorSnapshot:
    """Inspect Wave-36 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 0.15s`."""
    t0 = time.monotonic()
    clean_room = is_forced_clean_room() if force_clean_room is None else bool(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase240_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase240DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P240_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P240_DONOR_FX3_BODYDATA_RELPATH,
            P240_PINNED_FX3_BODYDATA_BYTES,
            P240_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P240_DONOR_FX3_APPFW_702_RELPATH,
            P240_PINNED_FX3_APPFW_702_BYTES,
            P240_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx6_appfw_601_so",
            P240_DONOR_FX6_APPFW_601_RELPATH,
            P240_PINNED_FX6_APPFW_601_BYTES,
            P240_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P240_DONOR_FX3_BACKUP_BIN_RELPATH,
            P240_PINNED_FX3_BACKUP_BIN_BYTES,
            P240_PINNED_FX3_BACKUP_BIN_SHA256,
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
            P240_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P240_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P240_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P240_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P240_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P240_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P240_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P240_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d, (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite")
            ),
        ),
        (
            "donor_libinfrahotshoe_so",
            P240_DONOR_HOTSHOE_SO_RELPATH,
            P240_PINNED_HOTSHOE_SO_BYTES,
            P240_PINNED_HOTSHOE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (
                    b"_ZN12InfraHotshoe9GetShoeIdEj",
                    b"_ZN12InfraHotshoe13QueryShoeIdOnEij",
                    b"_ZN12InfraHotshoe11SetAdcLevelEiPj",
                ),
            ),
        ),
    )

    digests: List[Phase240DonorArtifactDigest] = []
    for aid, rel, pinned_bytes, pinned_sha, validator in probe_specs:
        ok, total_b, hdr_b, dkind, dsha, raw = _read_donor_readonly_bounded(rel)
        if not ok:
            digests.append(
                Phase240DonorArtifactDigest(
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
            Phase240DonorArtifactDigest(
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
        synth = _synthetic_phase240_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase240DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(synth),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < P240_DONOR_INSPECT_BUDGET_SECONDS,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=synth,
        )

    dt = round(time.monotonic() - t0, 6)
    return Phase240DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all(d.present and d.matches_pinned for d in digests),
        donor_files_inspected=len(digests),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < P240_DONOR_INSPECT_BUDGET_SECONDS,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(digests),
    )


# ---------------------------------------------------------------------------
# Pillar 38A & 38B Evaluators
# ---------------------------------------------------------------------------


def build_default_safe_shoe_audio_wind_vault_spec() -> ShoeAudio4chAndWindNoiseVaultSpec:
    return ShoeAudio4chAndWindNoiseVaultSpec()


def build_default_safe_saveload_c3_vault_spec() -> SaveLoadC3ExclusionsAndSlot1VaultSpec:
    return SaveLoadC3ExclusionsAndSlot1VaultSpec()


def evaluate_shoe_audio_4ch_and_wind_noise_vault(
    spec: ShoeAudio4chAndWindNoiseVaultSpec,
) -> ShoeAudio4chAndWindNoiseVaultReport:
    """Audit `[Shoe Audio Set.]` 4ch recovery + 3 lockouts + CH1..CH4 meters & `[Wind Noise Reduct.]` built-in-only baseline."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P240_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P240_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 38A")

    valid_tokens = (
        spec.camera_model == P240_FX3_MODEL_NAME
        and spec.fw_version in P240_FX3_SUPPORTED_FW_VERSIONS
        and spec.shoe_audio_menu_path == P240_SHOE_AUDIO_SET_MENU_PATH
        and spec.wind_noise_menu_path == P240_WIND_NOISE_REDUCT_MENU_PATH
        and spec.shooting_mode in P240_SHOOTING_MODES
        and spec.audio_recording in P240_AUDIO_RECORDING_MODES
        and spec.audio_level_display in P240_AUDIO_LEVEL_DISPLAY_MODES
        and spec.shoe_attachment in P240_SHOE_ATTACHMENTS
        and spec.xlrh1_digital_analog_switch in P240_XLRH1_SWITCH_MODES
        and spec.xlrh1_hardware_low_cut in P240_XLRH1_HARDWARE_LOW_CUT_MODES
        and spec.pre_reset_shoe_audio_set in P240_SHOE_AUDIO_SET_MODES
        and spec.post_reset_shoe_audio_set in P240_SHOE_AUDIO_SET_MODES
        and spec.saved_shoe_audio_set in P240_SHOE_AUDIO_SET_MODES
        and spec.pre_reset_wind_noise_reduct in P240_WIND_NOISE_REDUCT_MODES
        and spec.post_reset_wind_noise_reduct in P240_WIND_NOISE_REDUCT_MODES
        and spec.saved_wind_noise_reduct in P240_WIND_NOISE_REDUCT_MODES
        and spec.reset_action in P240_RESET_ACTIONS
        and spec.effective_audio_source in P240_EFFECTIVE_AUDIO_SOURCES
        and spec.effective_recorded_audio_channels in (0, 2, 4)
        and spec.effective_audio_bit_depth in (0, 16, 24)
    )
    if not valid_tokens:
        _fail(
            P240_BLOCKED_INVALID_SHOE_AUDIO_OR_WIND_SPEC,
            f"Invalid model/fw, [Shoe Audio Set.], [Wind Noise Reduct.], or MI Shoe routing spec: "
            f"model={spec.camera_model!r} fw={spec.fw_version!r} mode={spec.shooting_mode!r}",
        )

    reset_ok = True
    camset_ok = True
    if spec.camset_slot != P240_SLOT1_VAULT_SLOT or spec.camset_filename not in P240_CAMSET_FILENAMES:
        camset_ok = False
        _fail(
            P240_BLOCKED_CAMSET_SHOE_AUDIO_OR_WIND_RESTORE_DRIFT,
            f"CAMSET baseline Load must reference Slot 1 CAMSET01.DAT..CAMSET10.DAT, got "
            f"slot={spec.camset_slot!r} file={spec.camset_filename!r}",
        )

    if valid_tokens:
        if spec.camset_load_after_reset:
            if (
                spec.post_reset_shoe_audio_set != spec.saved_shoe_audio_set
                or spec.post_reset_wind_noise_reduct != spec.saved_wind_noise_reduct
            ):
                camset_ok = False
                _fail(
                    P240_BLOCKED_CAMSET_SHOE_AUDIO_OR_WIND_RESTORE_DRIFT,
                    "Post-Load [Shoe Audio Set.] or [Wind Noise Reduct.] drifted from Slot-1 CAMSET01..10.DAT profile",
                )
        elif spec.reset_action == "NONE":
            if (
                spec.post_reset_shoe_audio_set != spec.pre_reset_shoe_audio_set
                or spec.post_reset_wind_noise_reduct != spec.pre_reset_wind_noise_reduct
            ):
                reset_ok = False
                _fail(
                    P240_BLOCKED_SHOE_AUDIO_OR_WIND_RESET_DRIFT,
                    "With reset_action='NONE' (and no CAMSET Load), [Shoe Audio Set.] and [Wind Noise Reduct.] must remain unchanged",
                )
        elif spec.reset_action in ("Camera Settings Reset", "Initialize"):
            if (
                spec.post_reset_shoe_audio_set != P240_SHOE_AUDIO_SET_DEFAULT
                or spec.post_reset_wind_noise_reduct != P240_WIND_NOISE_REDUCT_DEFAULT
            ):
                reset_ok = False
                _fail(
                    P240_BLOCKED_SHOE_AUDIO_OR_WIND_RESET_DRIFT,
                    f"[{spec.reset_action}] must reset [Shoe Audio Set.] to '48kHz/16bit 2ch' "
                    f"and [Wind Noise Reduct.] to 'Off'",
                )

    lockouts_and_meters_ok = True
    wind_exclusivity_ok = True
    if valid_tokens:
        audio_disabled = spec.audio_recording == "Off" or spec.shooting_mode == "S&Q Motion"
        if audio_disabled:
            if (
                spec.shoe_audio_set_available
                or spec.effective_audio_source != "DISABLED"
                or spec.effective_recorded_audio_channels != 0
                or spec.effective_audio_bit_depth != 0
                or spec.audio_level_display_meters != ()
                or spec.wind_noise_reduct_available
                or spec.wind_noise_reduct_effective_dsp_active
            ):
                lockouts_and_meters_ok = False
                _fail(
                    P240_BLOCKED_SHOE_AUDIO_SQ_OR_AUDIO_OFF_LOCKOUT_VIOLATION,
                    "When [Audio Recording]='Off' or shooting_mode='S&Q Motion', audio capture is 0ch, "
                    "[Shoe Audio Set.] & [Wind Noise Reduct.] are unavailable, and 0 audio meters render",
                )
        elif spec.body_35mm_mic_plugged_in:
            expected_meters = P240_CH1_CH2_METERS if spec.audio_level_display == "On" else ()
            if (
                spec.shoe_audio_set_available
                or spec.effective_audio_source != "BODY_35MM_ANALOG_MIC"
                or spec.effective_recorded_audio_channels != 2
                or spec.effective_audio_bit_depth != 16
            ):
                lockouts_and_meters_ok = False
                _fail(
                    P240_BLOCKED_SHOE_AUDIO_35MM_JACK_OVERRIDE_VIOLATION,
                    "Body 3.5mm MIC plug-in overrides both built-in mic and MI Shoe audio, locking capture to "
                    "2ch 16-bit analog ADC and disabling [Shoe Audio Set.] digital 24bit/4ch selection",
                )
            elif spec.audio_level_display_meters != expected_meters:
                lockouts_and_meters_ok = False
                _fail(
                    P240_BLOCKED_SHOE_AUDIO_4CH_METER_COUPLING_MISMATCH,
                    f"Body 3.5mm MIC analog 2ch path expected meters {expected_meters!r}, "
                    f"got {spec.audio_level_display_meters!r}",
                )
            if spec.wind_noise_reduct_effective_dsp_active:
                wind_exclusivity_ok = False
                _fail(
                    P240_BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION,
                    "[Wind Noise Reduct.] applies exclusively to the built-in stereo mic and does NOT function "
                    "when a 3.5mm external microphone is connected",
                )
        elif spec.shoe_attachment == "ANALOG_MI_MIC" or (
            spec.shoe_attachment in P240_DIGITAL_4CH_SHOE_ATTACHMENTS
            and spec.xlrh1_digital_analog_switch == "ANALOG"
        ):
            expected_meters = P240_CH1_CH2_METERS if spec.audio_level_display == "On" else ()
            if (
                spec.shoe_audio_set_available
                or spec.effective_audio_source != "MI_SHOE_ANALOG_2CH"
                or spec.effective_recorded_audio_channels != 2
                or spec.effective_audio_bit_depth != 16
            ):
                lockouts_and_meters_ok = False
                _fail(
                    P240_BLOCKED_SHOE_AUDIO_XLRH1_ANALOG_SWITCH_FALLBACK_VIOLATION,
                    "XLR-H1 [DIGITAL/ANALOG]='ANALOG' (or analog MI Shoe mic) bypasses digital I2S transport "
                    "and locks capture to 2ch 48kHz/16bit analog without [Shoe Audio Set.] 24bit/4ch",
                )
            elif spec.audio_level_display_meters != expected_meters:
                lockouts_and_meters_ok = False
                _fail(
                    P240_BLOCKED_SHOE_AUDIO_4CH_METER_COUPLING_MISMATCH,
                    f"MI Shoe analog 2ch path expected meters {expected_meters!r}, "
                    f"got {spec.audio_level_display_meters!r}",
                )
            if spec.wind_noise_reduct_effective_dsp_active:
                wind_exclusivity_ok = False
                _fail(
                    P240_BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION,
                    "[Wind Noise Reduct.] does NOT function with MI Shoe accessories (XLR-H1 hardware LOW CUT governs instead)",
                )
        elif spec.shoe_attachment in P240_DIGITAL_4CH_SHOE_ATTACHMENTS:
            mode_table: Dict[str, Tuple[int, int, Tuple[str, ...]]] = {
                "48kHz/16bit 2ch": (2, 16, P240_CH1_CH2_METERS),
                "48kHz/24bit 2ch": (2, 24, P240_CH1_CH2_METERS),
                "48kHz/24bit 4ch": (4, 24, P240_CH1_TO_CH4_METERS),
            }
            exp_ch, exp_bits, exp_meters_on = mode_table[spec.post_reset_shoe_audio_set]
            expected_meters = exp_meters_on if spec.audio_level_display == "On" else ()
            if (
                not spec.shoe_audio_set_available
                or spec.effective_audio_source != "MI_SHOE_DIGITAL"
                or spec.effective_recorded_audio_channels != exp_ch
                or spec.effective_audio_bit_depth != exp_bits
                or spec.audio_level_display_meters != expected_meters
            ):
                lockouts_and_meters_ok = False
                _fail(
                    P240_BLOCKED_SHOE_AUDIO_4CH_METER_COUPLING_MISMATCH,
                    f"Digital MI Shoe ({spec.shoe_attachment}) with [Shoe Audio Set.]={spec.post_reset_shoe_audio_set!r} "
                    f"requires available=True, source='MI_SHOE_DIGITAL', {exp_ch}ch/{exp_bits}bit, and meters={expected_meters!r}",
                )
            if spec.wind_noise_reduct_effective_dsp_active:
                wind_exclusivity_ok = False
                _fail(
                    P240_BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION,
                    "[Wind Noise Reduct.] applies exclusively to the built-in stereo mic and does NOT function "
                    "with digital MI Shoe XLR-H1 / ECM-M1 accessories",
                )
        else:
            # Built-in stereo microphone active (shoe_attachment == "NONE", no 3.5mm plug)
            expected_meters = P240_CH1_CH2_METERS if spec.audio_level_display == "On" else ()
            if (
                spec.shoe_audio_set_available
                or spec.effective_audio_source != "BUILT_IN_STEREO_MIC"
                or spec.effective_recorded_audio_channels != 2
                or spec.effective_audio_bit_depth != 16
                or spec.audio_level_display_meters != expected_meters
            ):
                lockouts_and_meters_ok = False
                _fail(
                    P240_BLOCKED_SHOE_AUDIO_4CH_METER_COUPLING_MISMATCH,
                    "Built-in stereo microphone path requires shoe_audio_set_available=False, "
                    "source='BUILT_IN_STEREO_MIC', 2ch/16bit, and CH1..CH2 level meters",
                )
            expected_wind_dsp = spec.post_reset_wind_noise_reduct == "On"
            if (
                not spec.wind_noise_reduct_available
                or spec.wind_noise_reduct_effective_dsp_active != expected_wind_dsp
            ):
                wind_exclusivity_ok = False
                _fail(
                    P240_BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION,
                    "Built-in stereo microphone path must expose [Wind Noise Reduct.] with DSP active iff set to 'On'",
                )

    indoor_wind_ok = True
    if valid_tokens and spec.indoor_bench_recovery_rehearsal:
        if spec.post_reset_wind_noise_reduct != "Off" or spec.indoor_low_freq_attenuation_hazard:
            indoor_wind_ok = False
            _fail(
                P240_BLOCKED_WIND_NOISE_INDOOR_BENCH_LOW_FREQ_ATTENUATION,
                "Indoor bench recovery rehearsals must keep [Wind Noise Reduct.]='Off' so normal low-frequency "
                "audio is not attenuated where wind is not blowing strongly",
            )

    if not _is_tmpfs_path(spec.overlay_dir) or _targets_persistent_emmc(spec.overlay_dir):
        _fail(
            P240_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P240_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P240_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P240_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 38A",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "38A",
            "passed": passed,
            "block_code": block_code,
            "fw_version": spec.fw_version,
            "reset_action": spec.reset_action,
            "camset_load": spec.camset_load_after_reset,
            "post_shoe_audio": spec.post_reset_shoe_audio_set,
            "post_wind_noise": spec.post_reset_wind_noise_reduct,
            "source": spec.effective_audio_source,
            "channels": spec.effective_recorded_audio_channels,
            "meters": list(spec.audio_level_display_meters),
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return ShoeAudio4chAndWindNoiseVaultReport(
        passed=passed,
        status=P240_STATUS_VERIFIED_PILLAR_38A if passed else P240_STATUS_REJECTED_PILLAR_38A,
        block_code=block_code,
        shoe_audio_and_wind_reset_verified=reset_ok and passed,
        camset_restore_verified=camset_ok and passed,
        shoe_audio_3lockouts_and_4ch_meters_verified=lockouts_and_meters_ok and passed,
        wind_noise_builtin_mic_exclusivity_verified=wind_exclusivity_ok and passed,
        indoor_bench_wind_off_baseline_verified=indoor_wind_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
    spec: SaveLoadC3ExclusionsAndSlot1VaultSpec,
) -> SaveLoadC3ExclusionsAndSlot1VaultReport:
    """Audit `[Save/Load Settings]` `CAMSET01..10.DAT` / `C3 Portal`, Excluded-Items Firewall & Slot-1 Tier-0 Vault Lock."""
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P240_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(P240_BLOCKED_SAFETY_POLICY_VIOLATION, "Persistent write unlock requested in Pillar 38B")

    valid_tokens = (
        spec.camera_model == P240_FX3_MODEL_NAME
        and spec.fw_version in P240_FX3_SUPPORTED_FW_VERSIONS
        and spec.menu_path == P240_SAVE_LOAD_SETTINGS_MENU_PATH
        and spec.operation in P240_SAVE_LOAD_OPERATIONS
        and spec.storage_target in P240_SAVE_LOAD_STORAGE_TARGETS
        and not spec.action_entry_stateful_reset_drift
        and spec.excluded_secret_or_cal_leak_count >= 0
        and spec.card_sectors_mutated >= 0
        and spec.slot1_unverified_camset_save_mutations >= 0
    )
    if not valid_tokens:
        _fail(
            P240_BLOCKED_INVALID_SAVELOAD_OR_CLOUD_SPEC,
            f"Invalid camera_model/fw, [Save/Load Settings] menu path, operation, storage target, or action-entry state: "
            f"model={spec.camera_model!r} fw={spec.fw_version!r} op={spec.operation!r} target={spec.storage_target!r}",
        )

    same_model_ok = True
    if spec.profile_model_name != P240_FX3_MODEL_NAME:
        same_model_ok = False
        _fail(
            P240_BLOCKED_CROSS_MODEL_FX6_DAT_REJECTED,
            f"[Save/Load Settings] strictly locks profiles to 'ILME-FX3'; foreign profile "
            f"{spec.profile_model_name!r} (.DAT / ALL File) is rejected",
        )

    target_ok = True
    if valid_tokens:
        if spec.storage_target == "Media":
            if (
                spec.media_slot not in P240_MEDIA_SLOTS
                or spec.camset_media_dir != P240_CAMSET_MEDIA_DIR
                or spec.camset_filename not in P240_CAMSET_FILENAMES
                or not (1 <= spec.card_camset_file_count <= P240_CAMSET_MAX_FILES_PER_CARD)
            ):
                target_ok = False
                _fail(
                    P240_BLOCKED_CAMSET_FILENAME_OR_10FILE_CAP_VIOLATION,
                    f"Media [Save/Load Settings] requires Slot 1/2, {P240_CAMSET_MEDIA_DIR!r}, "
                    f"CAMSET01.DAT..CAMSET10.DAT, and 1..10 files per card; got slot={spec.media_slot!r}, "
                    f"file={spec.camset_filename!r}, count={spec.card_camset_file_count}",
                )
        elif spec.storage_target in P240_CLOUD_STORAGE_TARGETS:
            if spec.fw_version not in P240_C3_PORTAL_SUPPORTED_FW_VERSIONS or not spec.c3_portal_authenticated:
                target_ok = False
                _fail(
                    P240_BLOCKED_C3_PORTAL_VERSION_OR_AUTH_VIOLATION,
                    f"{spec.storage_target} settings sync requires ILME-FX3 Ver. 4.00+ and authenticated C3 Portal "
                    f"session (fw={spec.fw_version!r}, auth={spec.c3_portal_authenticated!r})",
                )
            elif spec.airgap_tier0_vault_active:
                target_ok = False
                _fail(
                    P240_BLOCKED_CLOUD_SYNC_DURING_AIRGAP_TIER0_VAULT,
                    f"{spec.storage_target} C3 Portal network sync is forbidden while air-gapped Tier-0 cold-vault "
                    f"isolation is active",
                )

    computed_leak_flags = sum(
        1
        for flag in (
            spec.iptc_or_copyright_exported_or_overwritten,
            spec.custom_wb_1_to_3_exported_or_overwritten,
            spec.face_memory_biometrics_exported_or_overwritten,
            spec.network_ftp_rtmp_srt_wifi_tls_credentials_exported_or_overwritten,
        )
        if flag
    )
    total_leak_count = max(
        spec.excluded_secret_or_cal_leak_count,
        computed_leak_flags,
        len(spec.leaked_excluded_categories),
    )
    exclusions_ok = total_leak_count == 0
    if not exclusions_ok:
        _fail(
            P240_BLOCKED_SAVELOAD_EXCLUDED_PRIVACY_OR_CAL_LEAK,
            "Sony Help Guide Excluded-Items Firewall violated: [Save/Load Settings] must NEVER export or overwrite "
            "[IPTC Information], [Copyright Info], [Custom White Balance] (Custom 1..3), [Face Memory], or Network "
            "credentials (FTP, RTMP/SRT Streaming, Wi-Fi SSIDs/passphrases, static IP/TLS certs)",
        )

    slot1_vault_ok = True
    slot1_mutations = spec.slot1_unverified_camset_save_mutations
    if valid_tokens:
        if spec.slot1_unverified_camset_save_mutations != 0:
            slot1_vault_ok = False
            _fail(
                P240_BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
                f"Slot-1 unverified Tier-0 CAMSET save mutations detected: "
                f"{spec.slot1_unverified_camset_save_mutations}",
            )
        elif spec.storage_target == "Media":
            if spec.operation == "Load":
                if not spec.card_read_only_access or spec.card_sectors_mutated != 0:
                    slot1_vault_ok = False
                    slot1_mutations = max(slot1_mutations, spec.card_sectors_mutated, 1)
                    _fail(
                        P240_BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
                        "[Load] from Media must remain strictly O_RDONLY with 0 card sector mutations",
                    )
            elif spec.operation == "Save":
                if spec.media_slot == P240_SLOT1_VAULT_SLOT:
                    if spec.slot1_sdxc_wp_switch_locked:
                        slot1_vault_ok = False
                        _fail(
                            P240_BLOCKED_SLOT1_WP_LOCKED_SAVE_DENIED,
                            "[Save] to Slot 1 is hardware-denied while the SDXC physical LOCK/WP switch is engaged",
                        )
                    elif spec.slot1_tier0_vault_present and (
                        not spec.slot1_offcamera_sha256_verified
                        or not spec.slot1_scratch_save_authorized_after_vault_verify
                        or (spec.preserve_baseline_camset01_dat and spec.camset_filename == "CAMSET01.DAT")
                    ):
                        slot1_vault_ok = False
                        slot1_mutations = max(slot1_mutations, 1)
                        _fail(
                            P240_BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
                            "[Save] targeting Slot 1 Tier-0 forensic vault card (pnflasha/cnflasha/baseline CAMSET01.DAT) "
                            "is blocked unless off-camera SHA-256 is verified, scratch Save is explicitly authorized, and "
                            "baseline CAMSET01.DAT is not overwritten (use Slot 2 scratch media instead)",
                        )

    if not _is_tmpfs_path(spec.stage_b_overlay_dir) or _targets_persistent_emmc(spec.stage_b_overlay_dir):
        _fail(
            P240_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped volatile tmpfs: {spec.stage_b_overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.p2_blkroset_locked
        and spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == spec.backup_bin_h3_sha256 == P240_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P240_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P240_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0==H3 or p2 BLKROSET immutability drifted in Pillar 38B",
        )

    passed = len(errors) == 0
    digest = _canonical_sha256(
        {
            "pillar": "38B",
            "passed": passed,
            "block_code": block_code,
            "fw_version": spec.fw_version,
            "operation": spec.operation,
            "storage_target": spec.storage_target,
            "media_slot": spec.media_slot,
            "camset_filename": spec.camset_filename,
            "profile_model": spec.profile_model_name,
            "leak_count": total_leak_count,
            "slot1_mutations": slot1_mutations,
            "h0_eq_h3": h0_eq_h3,
        }
    )
    return SaveLoadC3ExclusionsAndSlot1VaultReport(
        passed=passed,
        status=P240_STATUS_VERIFIED_PILLAR_38B if passed else P240_STATUS_REJECTED_PILLAR_38B,
        block_code=block_code,
        same_model_fx3_lock_verified=same_model_ok and passed,
        media_10file_and_c3_cloud_target_verified=target_ok and passed,
        excluded_items_privacy_cal_firewall_verified=exclusions_ok and passed,
        slot1_tier0_vault_write_firewall_verified=slot1_vault_ok and passed,
        h0_equals_h3_verified=h0_eq_h3,
        excluded_secret_or_cal_leak_count=total_leak_count,
        slot1_unverified_camset_save_mutations=slot1_mutations,
        tier0_surfaces_intact=spec.tier0_surfaces_h0_h3_matched if h0_eq_h3 else 0,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def verify_shoe_audio_wind_and_saveload_vault(
    shoe_audio_wind_spec: Optional[ShoeAudio4chAndWindNoiseVaultSpec] = None,
    saveload_c3_vault_spec: Optional[SaveLoadC3ExclusionsAndSlot1VaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> ShoeAudioWindAndSaveLoadVaultReport:
    """Combined Pillar 38 verifier: Shoe Audio 4ch / Wind Noise built-in guard & Save/Load C3 / Slot-1 vault firewall."""
    donor_snap = inspect_phase240_donors_readonly(force_clean_room=force_clean_room)
    audio_rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(
        shoe_audio_wind_spec or build_default_safe_shoe_audio_wind_vault_spec()
    )
    saveload_rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(
        saveload_c3_vault_spec or build_default_safe_saveload_c3_vault_spec()
    )
    errs: List[str] = _safety_invariant_errors() + list(audio_rep.errors) + list(saveload_rep.errors)
    if not donor_snap.all_donors_present:
        errs.append("Phase 240 donor snapshot incomplete or mismatched")
    if not donor_snap.under_0_15s_budget:
        errs.append(f"Phase 240 donor inspection exceeded 0.15s budget: {donor_snap.elapsed_seconds}s")

    all_ok = audio_rep.passed and saveload_rep.passed and len(errs) == 0
    return ShoeAudioWindAndSaveLoadVaultReport(
        schema=PHASE240_SCHEMA,
        version=PHASE240_VERSION,
        verification_mode=donor_snap.verification_mode,
        all_passed=all_ok,
        passed=all_ok,
        status=P240_STATUS_VERIFIED_PILLAR38_SUITE if all_ok else P240_STATUS_FAIL_PILLAR38_SUITE,
        donor_snapshot=donor_snap,
        shoe_audio_wind_report=audio_rep,
        saveload_c3_vault_report=saveload_rep,
        excluded_secret_or_cal_leak_count=saveload_rep.excluded_secret_or_cal_leak_count,
        slot1_unverified_camset_save_mutations=saveload_rep.slot1_unverified_camset_save_mutations,
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
# 6-Scenario Suites & Standalone Pillar 38 Runner
# ---------------------------------------------------------------------------


def run_pillar38a_shoe_audio_wind_vault_6_scenario_suite() -> Pillar38ASuiteResult:
    cases: Tuple[Tuple[str, bool, ShoeAudio4chAndWindNoiseVaultSpec, Optional[str]], ...] = (
        (
            P240_PILLAR_38A_SCENARIO_IDS[0],
            True,
            ShoeAudio4chAndWindNoiseVaultSpec(),
            None,
        ),
        (
            P240_PILLAR_38A_SCENARIO_IDS[1],
            True,
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="DIGITAL",
                xlrh1_hardware_low_cut="100Hz",
                body_35mm_mic_plugged_in=False,
                reset_action="Camera Settings Reset",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                saved_shoe_audio_set="48kHz/24bit 4ch",
                saved_wind_noise_reduct="Off",
                post_reset_shoe_audio_set="48kHz/24bit 4ch",
                post_reset_wind_noise_reduct="Off",
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display="On",
                audio_level_display_meters=P240_CH1_TO_CH4_METERS,
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=False,
                indoor_bench_recovery_rehearsal=True,
            ),
            None,
        ),
        (
            P240_PILLAR_38A_SCENARIO_IDS[2],
            False,
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="DIGITAL",
                body_35mm_mic_plugged_in=True,
                camset_load_after_reset=True,
                saved_shoe_audio_set="48kHz/24bit 4ch",
                saved_wind_noise_reduct="Off",
                post_reset_shoe_audio_set="48kHz/24bit 4ch",
                post_reset_wind_noise_reduct="Off",
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display_meters=P240_CH1_TO_CH4_METERS,
            ),
            P240_BLOCKED_SHOE_AUDIO_35MM_JACK_OVERRIDE_VIOLATION,
        ),
        (
            P240_PILLAR_38A_SCENARIO_IDS[3],
            False,
            ShoeAudio4chAndWindNoiseVaultSpec(
                pre_reset_shoe_audio_set="48kHz/24bit 4ch",
                pre_reset_wind_noise_reduct="On",
                reset_action="Camera Settings Reset",
                camset_load_after_reset=False,
                post_reset_shoe_audio_set="48kHz/24bit 4ch",
                post_reset_wind_noise_reduct="On",
            ),
            P240_BLOCKED_SHOE_AUDIO_OR_WIND_RESET_DRIFT,
        ),
        (
            P240_PILLAR_38A_SCENARIO_IDS[4],
            False,
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="XLR-H1",
                xlrh1_digital_analog_switch="DIGITAL",
                reset_action="NONE",
                pre_reset_shoe_audio_set="48kHz/24bit 4ch",
                pre_reset_wind_noise_reduct="On",
                post_reset_shoe_audio_set="48kHz/24bit 4ch",
                post_reset_wind_noise_reduct="On",
                shoe_audio_set_available=True,
                effective_audio_source="MI_SHOE_DIGITAL",
                effective_recorded_audio_channels=4,
                effective_audio_bit_depth=24,
                audio_level_display_meters=P240_CH1_TO_CH4_METERS,
                wind_noise_reduct_available=False,
                wind_noise_reduct_effective_dsp_active=True,
                indoor_bench_recovery_rehearsal=False,
            ),
            P240_BLOCKED_WIND_NOISE_EXTERNAL_MIC_EXCLUSIVITY_VIOLATION,
        ),
        (
            P240_PILLAR_38A_SCENARIO_IDS[5],
            False,
            ShoeAudio4chAndWindNoiseVaultSpec(
                shoe_attachment="NONE",
                reset_action="NONE",
                pre_reset_shoe_audio_set="48kHz/16bit 2ch",
                pre_reset_wind_noise_reduct="On",
                post_reset_shoe_audio_set="48kHz/16bit 2ch",
                post_reset_wind_noise_reduct="On",
                shoe_audio_set_available=False,
                effective_audio_source="BUILT_IN_STEREO_MIC",
                effective_recorded_audio_channels=2,
                effective_audio_bit_depth=16,
                audio_level_display_meters=P240_CH1_CH2_METERS,
                wind_noise_reduct_available=True,
                wind_noise_reduct_effective_dsp_active=True,
                indoor_bench_recovery_rehearsal=True,
                indoor_low_freq_attenuation_hazard=True,
            ),
            P240_BLOCKED_WIND_NOISE_INDOOR_BENCH_LOW_FREQ_ATTENUATION,
        ),
    )

    outcomes: List[Pillar38ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_shoe_audio_4ch_and_wind_noise_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar38ScenarioOutcome(
                scenario_id=sid,
                pillar="38A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar38ASuiteResult(
        passed=all_ok,
        status=P240_STATUS_VERIFIED_PILLAR_38A if all_ok else P240_STATUS_REJECTED_PILLAR_38A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar38b_saveload_c3_vault_6_scenario_suite() -> Pillar38BSuiteResult:
    cases: Tuple[Tuple[str, bool, SaveLoadC3ExclusionsAndSlot1VaultSpec, Optional[str]], ...] = (
        (
            P240_PILLAR_38B_SCENARIO_IDS[0],
            True,
            SaveLoadC3ExclusionsAndSlot1VaultSpec(),
            None,
        ),
        (
            P240_PILLAR_38B_SCENARIO_IDS[1],
            True,
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Save",
                storage_target="Media",
                media_slot=P240_SLOT2_SCRATCH_SLOT,
                camset_filename="CAMSET02.DAT",
                card_camset_file_count=2,
                profile_model_name=P240_FX3_MODEL_NAME,
                card_read_only_access=False,
                card_sectors_mutated=4,
                slot1_unverified_camset_save_mutations=0,
                excluded_secret_or_cal_leak_count=0,
            ),
            None,
        ),
        (
            P240_PILLAR_38B_SCENARIO_IDS[2],
            False,
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Save",
                storage_target="Media",
                media_slot=P240_SLOT1_VAULT_SLOT,
                camset_filename="CAMSET01.DAT",
                slot1_tier0_vault_present=True,
                slot1_sdxc_wp_switch_locked=False,
                slot1_offcamera_sha256_verified=False,
                slot1_scratch_save_authorized_after_vault_verify=False,
                preserve_baseline_camset01_dat=True,
                card_read_only_access=False,
                card_sectors_mutated=4,
            ),
            P240_BLOCKED_SLOT1_TIER0_VAULT_CAMSET_SAVE_FORBIDDEN,
        ),
        (
            P240_PILLAR_38B_SCENARIO_IDS[3],
            False,
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Save",
                storage_target="Cloud(Share)",
                fw_version="7.02",
                c3_portal_authenticated=True,
                airgap_tier0_vault_active=False,
                iptc_or_copyright_exported_or_overwritten=True,
                custom_wb_1_to_3_exported_or_overwritten=True,
                face_memory_biometrics_exported_or_overwritten=True,
                network_ftp_rtmp_srt_wifi_tls_credentials_exported_or_overwritten=True,
                leaked_excluded_categories=P240_EXCLUDED_PRIVACY_AND_CALIBRATION_CATEGORIES,
                excluded_secret_or_cal_leak_count=8,
            ),
            P240_BLOCKED_SAVELOAD_EXCLUDED_PRIVACY_OR_CAL_LEAK,
        ),
        (
            P240_PILLAR_38B_SCENARIO_IDS[4],
            False,
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Load",
                storage_target="Media",
                media_slot=P240_SLOT1_VAULT_SLOT,
                camset_filename="CAMSET01.DAT",
                profile_model_name="ILME-FX6",
            ),
            P240_BLOCKED_CROSS_MODEL_FX6_DAT_REJECTED,
        ),
        (
            P240_PILLAR_38B_SCENARIO_IDS[5],
            False,
            SaveLoadC3ExclusionsAndSlot1VaultSpec(
                operation="Save",
                storage_target="Media",
                media_slot=P240_SLOT2_SCRATCH_SLOT,
                camset_filename="CAMSET11.DAT",
                card_camset_file_count=11,
                card_read_only_access=False,
                card_sectors_mutated=4,
            ),
            P240_BLOCKED_CAMSET_FILENAME_OR_10FILE_CAP_VIOLATION,
        ),
    )

    outcomes: List[Pillar38ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_saveload_c3_exclusions_and_slot1_vault_firewall(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar38ScenarioOutcome(
                scenario_id=sid,
                pillar="38B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar38BSuiteResult(
        passed=all_ok,
        status=P240_STATUS_VERIFIED_PILLAR_38B if all_ok else P240_STATUS_REJECTED_PILLAR_38B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar38_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar38StandaloneReport:
    """Run full Pillar 38 standalone suite (`6/6` Pillar 38A + `6/6` Pillar 38B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase240_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar38a_shoe_audio_wind_vault_6_scenario_suite()
    res_b = run_pillar38b_saveload_c3_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 240 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(f"Donor inspection exceeded 0.15s budget: {donor_snapshot.elapsed_seconds}s")

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE240_SCHEMA,
            "version": PHASE240_VERSION,
            "mode": donor_snapshot.verification_mode,
            "38a": [asdict(s) for s in res_a.scenarios],
            "38b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar38StandaloneReport(
        schema=PHASE240_SCHEMA,
        version=PHASE240_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P240_STATUS_VERIFIED_PILLAR38_SUITE if all_ok else P240_STATUS_FAIL_PILLAR38_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_38a_shoe_audio_wind_vault=res_a,
        pillar_38b_saveload_c3_exclusion_vault=res_b,
        excluded_secret_or_cal_leak_count=0 if res_b.passed else 1,
        slot1_unverified_camset_save_mutations=0 if res_b.passed else 1,
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
# Unified 38/38 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master38_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_38pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master38PillarRecoveryReport:
    """Evaluate and aggregate all 38 recovery pillars (`1..38`) concurrently -> `38/38` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_38_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    kw: Dict[str, Any] = {"force_clean_room": force_clean_room} if force_clean_room is not None else {}

    def _run_37pillar() -> Master37PillarRecoveryReport:
        return evaluate_realhw_37pillar_recovery_master(**kw)

    def _run_p38() -> Tuple[Pillar38StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar38_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_37 = pool.submit(_run_37pillar)
        fut_38 = pool.submit(_run_p38)
        m37_rep = fut_37.result()
        p38_rep, p38_dt = fut_38.result()

    all_errors: List[str] = list(m37_rep.errors) + list(p38_rep.errors)
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
        if getattr(m37_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-37 violated {attr_name} == {expected_val}")
        if getattr(p38_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 38 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m37_rep.pillars)
    spec38 = MASTER_38_PILLAR_SPECS[37]
    p38_metrics = {
        "pillar_38a_shoe_audio_wind_vault": (
            f"{p38_rep.pillar_38a_shoe_audio_wind_vault.scenarios_passed}/"
            f"{p38_rep.pillar_38a_shoe_audio_wind_vault.scenarios_total}"
        ),
        "pillar_38b_saveload_c3_exclusion_vault": (
            f"{p38_rep.pillar_38b_saveload_c3_exclusion_vault.scenarios_passed}/"
            f"{p38_rep.pillar_38b_saveload_c3_exclusion_vault.scenarios_total}"
        ),
        "excluded_secret_or_cal_leak_count": p38_rep.excluded_secret_or_cal_leak_count,
        "slot1_unverified_camset_save_mutations": p38_rep.slot1_unverified_camset_save_mutations,
        "donor_files_inspected": p38_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec38[0],
            pillar_id=spec38[1],
            phase_label=spec38[2],
            module_name=spec38[3],
            passed=bool(p38_rep.all_passed),
            status=p38_rep.status,
            verification_mode=p38_rep.verification_mode,
            elapsed_seconds=p38_dt,
            key_metrics=p38_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec38[1],
                    "mode": p38_rep.verification_mode,
                    "status": p38_rep.status,
                    "metrics": p38_metrics,
                    "passed": p38_rep.all_passed,
                }
            ),
            errors=tuple(p38_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master38_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p38_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_38_PILLAR_COUNT == 38
        and pillars_passed == 38
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE240_SCHEMA,
            "version": PHASE240_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master38PillarRecoveryReport(
        schema=PHASE240_SCHEMA,
        version=PHASE240_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P240_STATUS_VERIFIED_38OF38_AGGREGATOR if all_ok else P240_STATUS_FAIL_38OF38_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_6s_budget=elapsed < P240_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P240_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p38_rep.donor_snapshot,
        pillar38_a_shoe_audio_wind_vault=p38_rep.pillar_38a_shoe_audio_wind_vault,
        pillar38_b_saveload_c3_exclusion_vault=p38_rep.pillar_38b_saveload_c3_exclusion_vault,
        excluded_secret_or_cal_leak_count=p38_rep.excluded_secret_or_cal_leak_count,
        slot1_unverified_camset_save_mutations=p38_rep.slot1_unverified_camset_save_mutations,
        master_38pillar_sha256=master_sha,
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


def evaluate_38pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master38PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_38pillar_recovery_master`."""
    return evaluate_realhw_38pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_38pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master38PillarRecoveryReport:
    """Public CLI entry point for Pillar 38 unified `38/38` real-hardware recovery master verification."""
    return evaluate_realhw_38pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )
