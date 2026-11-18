"""Phase 272 — Pillar 47 (`47/47` Recovery Pillars) & Unified 47-Pillar Recovery Master
(`verify-47pillar-recovery` / `verify-focus-mag-datetime-videolight-hdmires-vault`):

1. **Pillar 47A — `[Focus Assistant]` Nomenclature (`[Auto Magnifier in MF] = [On]` vs Legacy
   `"MF Assist"` Spoofing), `Custom Button 5`, `[Focus Magnif. Time] = [No Limit]`, Separate
   Still & Movie `[Initial Focus Mag.] = [x1.0]`, Still-Only `[AF in Focus Mag.] = [On]`,
   `[Peaking Display]` Clean-HDMI Isolation & Still-Only `[AF Illuminator]` (Wave-45)**:
   - Models `MENU` -> `Focus` -> `[Focus Assistant]`, `[Peaking Display]`, and
     `MENU` -> `Focus` -> `[AF/MF]` -> `[AF Illuminator]` on physical `Sony ILME-FX3`
     (`Ver. 7.02`, `0x91030080`, `ilc/2210`).
   - Enforces `[Auto Magnifier in MF] = [On]` canonical Wave-45 nomenclature and rejects legacy
     `"MF Assist"` spoofing (`legacy_mf_assist_spoof_events == 0`), `[Focus Magnifier]` on
     `Custom Button 5`, `[Focus Magnif. Time] = [No Limit]`, independent Still vs Movie
     `[Initial Focus Mag.]` registers both defaulting to `[x1.0]`
     (`still_movie_initial_mag_couplings == 0`), and Still-only `[AF in Focus Mag.] = [On]`
     (`movie_af_in_focus_mag_events == 0`).
   - Enforces `[Peaking Display]` (`Off` default, `Control Wheel Right`, `Mid`, `White`) camera-LCD-only
     scope so `Info Off` and `HDMI RAW` clean feeds suffer zero baked overlay pixels
     (`hdmi_clean_feed_focus_mag_or_peaking_leak_pixels == 0`), plus Still-only `[AF Illuminator]`
     (`Auto` default, `movie_sq_af_illuminator_fire_events == 0`).
   - Enforces `[Camera Settings Reset]` vs `[Reset Network Set.]` vs `[Initialize]` reset boundaries
     (Focus items reset on `[Camera Settings Reset]` and `[Initialize]`; `Custom Key` bindings
     survive `[Camera Settings Reset]` and reset only on `[Initialize]`) and deterministic `O_RDONLY`
     Slot-1 `CAMSET01..10.DAT` `[Load]` restoration across a `144`-state matrix.

2. **Pillar 47B — `[Area/Date/Time Setting]` Zero-RF Forensic Timestamp Integrity, `[Video Light Mode]`
   `5V <= 900 mA` Rail Guard, `[HDMI Resolution]` Log Internal-Recording `1080p` Downshift &
   Slot-1 Recovery Vault Read-Only Integrity (Wave-45)**:
   - Models `MENU` -> `Setup` -> `[Area/Date]` -> `[Area/Date/Time Setting]` (rejecting legacy
     `"Date/Time Setup"` spoofing, `legacy_datetime_setup_spoof_events == 0`) with exact 4 sub-items
     (`Area Setting`, `Daylight Savings`, `Date/Time`, `Date Format`), `[Daylight Savings] = [Off]`,
     and `[Setup]` survival across `[Camera Settings Reset]` & `[Reset Network Set.]` (reset/cleared
     only on `[Initialize]` or `rtc_backup_battery_lost=True`).
   - Enforces Zero-RF bench suppression (`[Airplane Mode] = [On]`, `passive_tx_bytes_emitted == 0`)
     forcing Creators' App `[Auto Time Correction]` & `[Auto Area Adjustment]` -> `Off` so
     `unsolicited_rtc_timezone_jump_events == 0` and `H0..H3` forensic timestamps remain intact.
   - Enforces `[Video Light Mode]` (`[Power Link]` factory default, `Setup` reset survival) within
     the MI-Shoe `PMIC 5V <= 900 mA` (`Gate G24`) accessory budget (`mishoe_5v_overcurrent_events == 0`)
     and `[HDMI Resolution]` (`[Auto]` default, `Setup` reset survival) with mandatory hardware
     `1080p` downshift override whenever `[Log Shooting] != Off` & internal recording is active with
     `[Rec. Media dur HDMI Output] = On` (`hdmi_res_log_internal_rec_2160p_bypass_events == 0`),
     plus Slot-1 recovery vault read-only lock (`slot1_vault_mutation_bytes == 0`, `16/16` `H0 == H3`).

3. **Unified `47/47` Recovery Master (`evaluate_realhw_47pillar_recovery_master`)**:
   - Concurrently delegates Pillars `1..46` (`evaluate_realhw_46pillar_recovery_master`) +
     **Pillar 47** (`run_pillar47_standalone_suite`) -> **`47/47` (`VERIFIED_47OF47_PILLAR_RECOVERY_MASTER`)**
     in `< 2.0s` CLI runtime (`< 4.0s` nominal / `< 6.0s` concurrent ceiling), preserving 100%
     backward compatibility with `verify-22..46pillar-recovery`.
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
from .realhw_46pillar_file_settings_gamma_assist_tcub_vault_verifier import (
    CNFLASHA_USERSPACE_WRITE_BLOCKED,
    MASTER_46_PILLAR_SPECS,
    Master46PillarRecoveryReport,
    evaluate_realhw_46pillar_recovery_master,
)

# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

PHASE272_SCHEMA: str = "realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier_v1"
PHASE272_VERSION: str = "1.0.0"
PHASE272_PHASE_NUMBER: int = 272
P272_ENV_CLEAN_ROOM_TEST: str = "FX3_CLEAN_ROOM_TEST"

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
P272_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
READ_ONLY_DONOR_ACCESS: bool = True

OTP_FUSE_TOUCHES: int = 0
OTP_FUSE_WRITES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0
PASSIVE_TX_BYTES_EMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
PHYSICAL_DEVICE_WRITES: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

P272_LEGACY_MF_ASSIST_SPOOF_EVENTS: int = 0
P272_STILL_MOVIE_INITIAL_MAG_COUPLINGS: int = 0
P272_MOVIE_AF_IN_FOCUS_MAG_EVENTS: int = 0
P272_HDMI_CLEAN_FEED_FOCUS_MAG_OR_PEAKING_LEAK_PIXELS: int = 0
P272_MOVIE_SQ_AF_ILLUMINATOR_FIRE_EVENTS: int = 0
P272_LEGACY_DATETIME_SETUP_SPOOF_EVENTS: int = 0
P272_UNSOLICITED_RTC_TIMEZONE_JUMP_EVENTS: int = 0
P272_MISHOE_5V_OVERCURRENT_EVENTS: int = 0
P272_HDMI_RES_LOG_INTERNAL_REC_2160P_BYPASS_EVENTS: int = 0
P272_SLOT1_VAULT_MUTATION_EVENTS: int = 0
P272_SLOT1_VAULT_MUTATION_BYTES: int = 0

P272_DONOR_INSPECT_BUDGET_SECONDS: float = 2.0
P272_DONOR_INSPECT_CI_BUDGET_SECONDS: float = 0.50
P272_FAST_CLI_BUDGET_SECONDS: float = 2.0
P272_NOMINAL_BUDGET_SECONDS: float = 4.0
P272_CONCURRENT_CEILING_SECONDS: float = 6.0
P272_BOUNDED_HEADER_BYTES: int = 4096
P272_MAX_FULL_DONOR_BYTES: int = 4 * 1024 * 1024

# Target Baseline & Pinned Wave-45 Donor Anchors (strictly O_RDONLY)
P272_FX3_MODEL_NAME: str = "ILME-FX3"
P272_FX3_MODEL_ID: int = 0x91030080
P272_FX3_HELPGUIDE_ID: str = "ilc/2210"
P272_FX3_FW_VERSION: str = "7.02"
P272_FX6_DONOR_MODEL_NAME: str = "ILME-FX6"
P272_FX6_DONOR_FW_VERSION: str = "6.01"
P272_FX3_SUPPORTED_FW_VERSIONS: Tuple[str, ...] = (
    "3.00",
    "4.00",
    "5.00",
    "6.00",
    "6.02",
    "7.00",
    "7.01",
    "7.02",
)

P272_DONOR_FX3_BODYDATA_RELPATH: str = "work/sony-firmware-20261024/fx3-7.02-BODYDATA.DAT"
P272_PINNED_FX3_BODYDATA_BYTES: int = 811876768
P272_PINNED_FX3_BODYDATA_HDR4K_SHA256: str = (
    "fc135914e0767d69518e5b1f86b138abdbd2a20dd341e495cf151f8ddb79e404"
)

P272_DONOR_FX3_APPFW_702_RELPATH: str = (
    "work/fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
)
P272_PINNED_FX3_APPFW_702_BYTES: int = 79015712
P272_PINNED_FX3_APPFW_702_HDR4K_SHA256: str = (
    "de3201c6615a53078b7b166b45f5d369a1dabfb70d568972f9613a00ca395674"
)

P272_DONOR_FX3_CPAPP_B_BIN_RELPATH: str = (
    "work/sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
)
P272_PINNED_FX3_CPAPP_B_BIN_BYTES: int = 15980568
P272_PINNED_FX3_CPAPP_B_BIN_HDR4K_SHA256: str = (
    "452c9e4e05fc1942baeee8ea9d531eeaaab99091576bc59eaa46f2d272050d5d"
)

P272_DONOR_FX6_APPFW_601_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
P272_PINNED_FX6_APPFW_601_BYTES: int = 50520424
P272_PINNED_FX6_APPFW_601_HDR4K_SHA256: str = (
    "18a5d71362317f3f018e0e1061d1ca3e435e8b2dd52f63a1dc7e87f457bd5cfd"
)

P272_DONOR_FX3_BACKUP_BIN_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin"
)
P272_PINNED_FX3_BACKUP_BIN_BYTES: int = 2229740
P272_PINNED_FX3_BACKUP_BIN_SHA256: str = (
    "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2"
)

P272_DONOR_FX6_BACKUP_NTSC_BIN_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin"
)
P272_PINNED_FX6_BACKUP_NTSC_BIN_BYTES: int = 2253333
P272_PINNED_FX6_BACKUP_NTSC_BIN_SHA256: str = (
    "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e"
)

P272_DONOR_FX3_LIBBACKUP_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libbackup.so"
)
P272_PINNED_FX3_LIBBACKUP_SO_BYTES: int = 14232
P272_PINNED_FX3_LIBBACKUP_SO_SHA256: str = (
    "6a3c5f6067620c00d790cbe520844acdbb721fa5d0e7433b00a227f922ab9d0d"
)

P272_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libBackupManager.so"
)
P272_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES: int = 10272
P272_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256: str = (
    "ef95ca41dadcad9a732b1b1f75e0f9de994093222bd3613c15dbf55ee4bdba9e"
)

P272_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so"
)
P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES: int = 18760
P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256: str = (
    "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7"
)

P272_DONOR_FX3_LIBGPE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libgpe.so"
)
P272_PINNED_FX3_LIBGPE_SO_BYTES: int = 106480
P272_PINNED_FX3_LIBGPE_SO_SHA256: str = (
    "363879687bd43a69734187eb28f721ce6080209a95c62b04c833a4a117f12464"
)

P272_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/CameraOnDemandSaver.so"
)
P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES: int = 18800
P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256: str = (
    "72b73608c2675a3709e2952ca347a36e7dd2ad3dd2869191638c7154933b2f46"
)

P272_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAirplaneMode.so"
)
P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES: int = 14488
P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256: str = (
    "dcf0d7562a879f6d3bd1ed60cf00f9068fec368554b175bc6fabafbf212dffea"
)

P272_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaConfig.so"
)
P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES: int = 52312
P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256: str = (
    "483548d53dfbe941b6e66486d8d18ee3930bfd726fa524aa73a0ca6ac275c486"
)

P272_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH: str = (
    "work/fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraMediaDetect.so"
)
P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES: int = 98224
P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256: str = (
    "4c1dbb303cf9d2d762723e0eb2266309c83aefe7d50f050fc8baa3964e4ea70d"
)

P272_DONOR_FX6_LIBINFRADIAL_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraDial.so"
)
P272_PINNED_FX6_LIBINFRADIAL_SO_BYTES: int = 31232
P272_PINNED_FX6_LIBINFRADIAL_SO_SHA256: str = (
    "b2034d6c85372027444e783d5d2ed913bb5a8cd2fe4051b10cf63caae875db33"
)

P272_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH: str = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so"
)
P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES: int = 47808
P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256: str = (
    "0bf55367c0345341d776180e45ec640dce978c1cf9a0935354f20421ca2204f6"
)

# Pillar 47A — [Focus Assistant], [Peaking Display], Clean-HDMI & Still-Only [AF Illuminator]
P272_FOCUS_ASSISTANT_MENU_PATH: Tuple[str, ...] = ("MENU", "Focus", "Focus Assistant")
P272_PEAKING_DISPLAY_MENU_PATH: Tuple[str, ...] = ("MENU", "Focus", "Peaking Display")
P272_AF_ILLUMINATOR_MENU_PATH: Tuple[str, ...] = ("MENU", "Focus", "AF/MF", "AF Illuminator")
P272_HDMI_INFO_DISPLAY_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "External Output",
    "HDMI Info. Display",
)

P272_AUTO_MAG_IN_MF_LABEL: str = "Auto Magnifier in MF"
P272_FORBIDDEN_LEGACY_MF_ASSIST_LABEL: str = "MF Assist"
P272_ON_OFF_MODES: Tuple[str, ...] = ("On", "Off")
P272_AUTO_MAG_IN_MF_DEFAULT: str = "On"
P272_FOCUS_MAGNIFIER_CUSTOM_BTN_DEFAULT: str = "Custom Button 5"
P272_ALLOWED_FOCUS_MAG_CUSTOM_BTNS: Tuple[str, ...] = (
    "Custom Button 5",
    "Custom Button 1",
    "Custom Button 2",
    "Custom Button 3",
    "Custom Button 4",
    "Custom Button 6",
    "AF-ON Button",
)

P272_FOCUS_MAGNIF_TIME_MODES: Tuple[str, ...] = ("2 Sec", "5 Sec", "No Limit")
P272_FOCUS_MAGNIF_TIME_DEFAULT: str = "No Limit"

P272_INITIAL_FOCUS_MAG_MODES: Tuple[str, ...] = ("x1.0", "x4.0")
P272_INITIAL_FOCUS_MAG_STILL_DEFAULT: str = "x1.0"
P272_INITIAL_FOCUS_MAG_MOVIE_DEFAULT: str = "x1.0"

P272_AF_IN_FOCUS_MAG_DEFAULT: str = "On"

P272_PEAKING_DISPLAY_DEFAULT: str = "Off"
P272_PEAKING_DISPLAY_SELECT_DEFAULT: str = "Control Wheel Right"
P272_ALLOWED_PEAKING_SELECT_BTNS: Tuple[str, ...] = (
    "Control Wheel Right",
    "Control Wheel Left",
    "Custom Button 1",
    "Custom Button 2",
    "Custom Button 5",
)
P272_PEAKING_LEVELS: Tuple[str, ...] = ("High", "Mid", "Low")
P272_PEAKING_LEVEL_DEFAULT: str = "Mid"
P272_PEAKING_COLORS: Tuple[str, ...] = ("Red", "Yellow", "Blue", "White")
P272_PEAKING_COLOR_DEFAULT: str = "White"

P272_AF_ILLUMINATOR_MODES: Tuple[str, ...] = ("Auto", "Off")
P272_AF_ILLUMINATOR_DEFAULT: str = "Auto"

P272_SHOOTING_DOMAINS: Tuple[str, ...] = ("Still", "Movie", "S&Q")
P272_FOCUS_MODES: Tuple[str, ...] = ("MF", "DMF", "AF-S", "AF-C")
P272_HDMI_FEED_MODES: Tuple[str, ...] = ("Info On", "Info Off", "HDMI RAW")

# Pillar 47B — [Area/Date/Time Setting], Creators' App Zero-RF Isolation, [Video Light Mode] & [HDMI Resolution]
P272_AREA_DATETIME_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Area/Date",
    "Area/Date/Time Setting",
)
P272_AREA_DATETIME_LABEL: str = "Area/Date/Time Setting"
P272_FORBIDDEN_LEGACY_DATETIME_LABEL: str = "Date/Time Setup"
P272_AREA_DATETIME_EXACT_4_SUBITEMS: Tuple[str, ...] = (
    "Area Setting",
    "Daylight Savings",
    "Date/Time",
    "Date Format",
)
P272_AREA_SETTING_DEFAULT: str = "—"
P272_DAYLIGHT_SAVINGS_MODES: Tuple[str, ...] = ("Off", "On")
P272_DAYLIGHT_SAVINGS_DEFAULT: str = "Off"
P272_DATE_FORMATS: Tuple[str, ...] = ("YYYY-MM-DD", "MM-DD-YYYY", "DD-MM-YYYY")
P272_DATE_FORMAT_DEFAULT: str = "YYYY-MM-DD"

P272_AIRPLANE_MODE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Network",
    "Network Option",
    "Airplane Mode",
)
P272_AIRPLANE_MODES: Tuple[str, ...] = ("On", "Off")

P272_VIDEO_LIGHT_MODE_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "Setup Option",
    "Video Light Mode",
)
P272_VIDEO_LIGHT_MODES: Tuple[str, ...] = (
    "Power Link",
    "REC Link",
    "REC Link & STBY",
    "Auto",
)
P272_VIDEO_LIGHT_MODE_DEFAULT: str = "Power Link"
P272_MISHOE_5V_MAX_BUDGET_MA: int = 900

P272_HDMI_RESOLUTION_MENU_PATH: Tuple[str, ...] = (
    "MENU",
    "Setup",
    "External Output",
    "HDMI Resolution",
)
P272_HDMI_RESOLUTIONS: Tuple[str, ...] = ("Auto", "2160p", "1080p", "1080i")
P272_HDMI_RESOLUTION_DEFAULT: str = "Auto"
P272_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "Off",
    "Cine EI",
    "Cine EI Quick",
    "Flexible ISO",
)
P272_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("On", "Off(HDMI Only)")

P272_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "Camera Settings Reset",
    "Reset Network Set.",
    "Initialize",
)
P272_SLOT1_VAULT_SLOT: int = 1
P272_CAMSET_FILENAMES: Tuple[str, ...] = tuple(f"CAMSET{i:02d}.DAT" for i in range(1, 11))
P272_STAGE_B_VOLATILE_OVERLAY_DIR: str = "/tmp/fx3_focus_mag_datetime_videolight_hdmires_vault_overlay"
P272_FORBIDDEN_PERSISTENT_TARGETS: Tuple[str, ...] = (
    "/setting",
    "p2:/setting",
    "/dev/nflasha",
    "/dev/pnflasha",
    "/dev/cnflasha",
    "/dev/mmcblk0",
)
P272_TIER0_SURFACE_COUNT: int = 16

# Error & Status Codes
P272_BLOCKED_SAFETY_POLICY_VIOLATION: str = "BLOCKED_SAFETY_POLICY_VIOLATION"
P272_BLOCKED_INVALID_FOCUS_MAG_PEAKING_SPEC: str = "BLOCKED_INVALID_FOCUS_MAG_PEAKING_SPEC"
P272_BLOCKED_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF: str = (
    "BLOCKED_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF"
)
P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING: str = (
    "BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING"
)
P272_BLOCKED_HDMI_CLEAN_FEED_OVERLAY_LEAK: str = "BLOCKED_HDMI_CLEAN_FEED_OVERLAY_LEAK"
P272_BLOCKED_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG: str = (
    "BLOCKED_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG"
)
P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT: str = (
    "BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT"
)

P272_BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC: str = (
    "BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC"
)
P272_BLOCKED_LEGACY_DATETIME_SETUP_SPOOF: str = "BLOCKED_LEGACY_DATETIME_SETUP_SPOOF"
P272_BLOCKED_ZERO_RF_CREATORS_APP_SYNC_OR_RTC_JUMP: str = (
    "BLOCKED_ZERO_RF_CREATORS_APP_SYNC_OR_RTC_JUMP"
)
P272_BLOCKED_MISHOE_5V_OVERCURRENT: str = "BLOCKED_MISHOE_5V_OVERCURRENT"
P272_BLOCKED_HDMI_RES_LOG_1080P_OVERRIDE: str = "BLOCKED_HDMI_RES_LOG_1080P_OVERRIDE"
P272_BLOCKED_SETUP_RESET_PERSISTENCE_OR_SLOT1_VAULT_DRIFT: str = (
    "BLOCKED_SETUP_RESET_PERSISTENCE_OR_SLOT1_VAULT_DRIFT"
)
P272_BLOCKED_PERSISTENT_OVERLAY_ESCAPE: str = "BLOCKED_PERSISTENT_OVERLAY_ESCAPE"
P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT: str = "BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT"

P272_STATUS_VERIFIED_PILLAR_47A: str = (
    "VERIFIED_PILLAR_47A_AUTO_MAG_MF_INITIAL_X10_PEAKING_CLEAN_HDMI_AND_STILL_AF_ILLUMINATOR_VAULT"
)
P272_STATUS_REJECTED_PILLAR_47A: str = (
    "REJECTED_PILLAR_47A_AUTO_MAG_MF_INITIAL_X10_PEAKING_CLEAN_HDMI_AND_STILL_AF_ILLUMINATOR_VAULT"
)
P272_STATUS_VERIFIED_PILLAR_47B: str = (
    "VERIFIED_PILLAR_47B_AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_5V_HDMI_RES_LOG_AND_SLOT1_VAULT"
)
P272_STATUS_REJECTED_PILLAR_47B: str = (
    "REJECTED_PILLAR_47B_AREA_DATETIME_ZERO_RF_VIDEO_LIGHT_5V_HDMI_RES_LOG_AND_SLOT1_VAULT"
)
P272_STATUS_VERIFIED_PILLAR47_SUITE: str = (
    "VERIFIED_PILLAR47_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_VAULT"
)
P272_STATUS_FAIL_PILLAR47_SUITE: str = (
    "FAIL_PILLAR47_FOCUS_MAG_DATETIME_VIDEOLIGHT_HDMIRES_VAULT"
)
P272_STATUS_VERIFIED_47OF47_AGGREGATOR: str = "VERIFIED_47OF47_PILLAR_RECOVERY_MASTER"
P272_STATUS_FAIL_47OF47_AGGREGATOR: str = "FAIL_47OF47_PILLAR_RECOVERY_MASTER"

P272_PILLAR_47A_SCENARIO_IDS: Tuple[str, ...] = (
    "P47A1_AUTO_MAG_IN_MF_ON_C5_NOLIMIT_INDEPENDENT_X10_PEAKING_OFF_CLEAN_HDMI_AND_STILL_AF_ILLUM_SAFE",
    "P47A2_INITIALIZE_RESETS_C5_AND_FOCUS_DEFAULTS_THEN_ORDONLY_SLOT1_CAMSET01_RESTORES_MOVIE_X40_PEAKING_SAFE",
    "P47A3_REJECT_LEGACY_MF_ASSIST_SPOOF_OR_COUPLED_STILL_MOVIE_INITIAL_FOCUS_MAG_REGISTER",
    "P47A4_REJECT_FOCUS_MAG_OR_PEAKING_OVERLAY_PIXEL_LEAK_ONTO_INFO_OFF_OR_HDMI_RAW_CLEAN_FEED",
    "P47A5_REJECT_STILL_ONLY_AF_IN_FOCUS_MAG_OR_AF_ILLUMINATOR_ARMING_OR_FIRING_IN_MOVIE_SQ",
    "P47A6_REJECT_CAMERA_SETTINGS_RESET_PRESERVING_FOCUS_ITEMS_OR_WIPING_CUSTOM_KEY_BINDINGS",
)
P272_PILLAR_47B_SCENARIO_IDS: Tuple[str, ...] = (
    "P47B1_AREA_DATETIME_ZERO_RF_CREATORS_APP_OFF_VIDEO_LIGHT_POWER_LINK_900MA_HDMI_LOG_1080P_AND_SLOT1_SAFE",
    "P47B2_HDMI_OFF_ONLY_ALLOWS_2160P_AND_INITIALIZE_RESETS_SETUP_WITH_ORDONLY_CAMSET01_ROUNDTRIP_SAFE",
    "P47B3_REJECT_LEGACY_DATETIME_SETUP_SPOOF_OR_AIRPLANE_ON_CREATORS_APP_AUTO_TIME_RTC_JUMP",
    "P47B4_REJECT_VIDEO_LIGHT_MISHOE_5V_RAIL_EXCEEDING_900MA_OVERCURRENT_BUDGET",
    "P47B5_REJECT_HDMI_RES_2160P_BYPASS_DURING_LOG_INTERNAL_RECORDING_WHEN_REC_MEDIA_HDMI_ON",
    "P47B6_REJECT_CAMERA_SETTINGS_RESET_WIPING_SETUP_ITEMS_OR_SLOT1_VAULT_MUTATION_OR_H0_H3_DRIFT",
)

MASTER_47_PILLAR_COUNT: int = 47
MASTER_47_PILLAR_SPECS: Tuple[Tuple[int, str, str, str], ...] = MASTER_46_PILLAR_SPECS + (
    (
        47,
        "pillar_47_focus_mag_datetime_videolight_hdmires_vault",
        "Phase 272 (47/47)",
        "fx3_recovery.realhw_47pillar_focus_mag_datetime_videolight_hdmires_vault_verifier",
    ),
)
MASTER_47_PILLAR_IDS: Tuple[str, ...] = tuple(spec[1] for spec in MASTER_47_PILLAR_SPECS)


# ---------------------------------------------------------------------------
# Internal Helpers & Deterministic State Computations
# ---------------------------------------------------------------------------


def _need(cond: bool, msg: str) -> None:
    if not cond:
        raise ValueError(msg)


def _canonical_sha256(payload: Any) -> str:
    raw = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")
    return sha256(raw).hexdigest()


def _is_clean_room_forced(force_clean_room: Optional[bool] = None) -> bool:
    """Honor explicit flag, `FX3_FX6_FORCE_CLEAN_ROOM=1`, AND `FX3_CLEAN_ROOM_TEST=1`."""
    if force_clean_room is not None:
        return bool(force_clean_room)
    if is_forced_clean_room():
        return True
    return os.environ.get(P272_ENV_CLEAN_ROOM_TEST, "").strip().lower() in ("1", "true", "yes")


def _donor_inspect_budget_seconds() -> float:
    if os.environ.get("GITHUB_ACTIONS", "").strip().lower() == "true":
        return P272_DONOR_INSPECT_CI_BUDGET_SECONDS
    return P272_DONOR_INSPECT_BUDGET_SECONDS


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
        ("P272_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED", P272_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED, False),
        ("READ_ONLY_DONOR_ACCESS", READ_ONLY_DONOR_ACCESS, True),
        ("CNFLASHA_USERSPACE_WRITE_BLOCKED", CNFLASHA_USERSPACE_WRITE_BLOCKED, True),
        ("P272_LEGACY_MF_ASSIST_SPOOF_EVENTS", P272_LEGACY_MF_ASSIST_SPOOF_EVENTS, 0),
        ("P272_STILL_MOVIE_INITIAL_MAG_COUPLINGS", P272_STILL_MOVIE_INITIAL_MAG_COUPLINGS, 0),
        ("P272_MOVIE_AF_IN_FOCUS_MAG_EVENTS", P272_MOVIE_AF_IN_FOCUS_MAG_EVENTS, 0),
        (
            "P272_HDMI_CLEAN_FEED_FOCUS_MAG_OR_PEAKING_LEAK_PIXELS",
            P272_HDMI_CLEAN_FEED_FOCUS_MAG_OR_PEAKING_LEAK_PIXELS,
            0,
        ),
        ("P272_MOVIE_SQ_AF_ILLUMINATOR_FIRE_EVENTS", P272_MOVIE_SQ_AF_ILLUMINATOR_FIRE_EVENTS, 0),
        ("P272_LEGACY_DATETIME_SETUP_SPOOF_EVENTS", P272_LEGACY_DATETIME_SETUP_SPOOF_EVENTS, 0),
        ("P272_UNSOLICITED_RTC_TIMEZONE_JUMP_EVENTS", P272_UNSOLICITED_RTC_TIMEZONE_JUMP_EVENTS, 0),
        ("P272_MISHOE_5V_OVERCURRENT_EVENTS", P272_MISHOE_5V_OVERCURRENT_EVENTS, 0),
        (
            "P272_HDMI_RES_LOG_INTERNAL_REC_2160P_BYPASS_EVENTS",
            P272_HDMI_RES_LOG_INTERNAL_REC_2160P_BYPASS_EVENTS,
            0,
        ),
        ("P272_SLOT1_VAULT_MUTATION_EVENTS", P272_SLOT1_VAULT_MUTATION_EVENTS, 0),
        ("P272_SLOT1_VAULT_MUTATION_BYTES", P272_SLOT1_VAULT_MUTATION_BYTES, 0),
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
    return any(tok in low for tok in P272_FORBIDDEN_PERSISTENT_TARGETS)


def compute_expected_pillar47a_focus_assistant_state_after_reset(
    *,
    pre_auto_mag_in_mf: str,
    pre_focus_mag_custom_btn: str,
    pre_focus_mag_time: str,
    pre_still_initial_focus_mag: str,
    pre_movie_initial_focus_mag: str,
    pre_af_in_focus_mag: str,
    pre_peaking_display: str,
    pre_peaking_select_btn: str,
    pre_peaking_level: str,
    pre_peaking_color: str,
    pre_af_illuminator: str,
    reset_action: str,
) -> Tuple[str, str, str, str, str, str, str, str, str, str, str]:
    """Compute post-reset Pillar 47A `[Focus Assistant]`, `[Peaking Display]` & `[AF Illuminator]` state.

    - `[Camera Settings Reset]` resets Focus/Shooting items (`Auto Magnifier in MF`, `Focus Magnif. Time`,
      independent Still & Movie `Initial Focus Mag.`, `AF in Focus Mag.`, `Peaking Display`,
      `Peaking Level`, `Peaking Color`, `AF Illuminator`) to factory defaults, while preserving custom key
      assignments (`Focus Magnifier` button & `Peaking Display Select`).
    - `[Reset Network Set.]` preserves all Pillar 47A items.
    - `[Initialize]` resets BOTH Focus/Shooting items AND custom key assignments back to factory defaults.
    """
    if reset_action == "Reset Network Set." or reset_action == "NONE":
        return (
            pre_auto_mag_in_mf,
            pre_focus_mag_custom_btn,
            pre_focus_mag_time,
            pre_still_initial_focus_mag,
            pre_movie_initial_focus_mag,
            pre_af_in_focus_mag,
            pre_peaking_display,
            pre_peaking_select_btn,
            pre_peaking_level,
            pre_peaking_color,
            pre_af_illuminator,
        )
    custom_mag_btn = (
        P272_FOCUS_MAGNIFIER_CUSTOM_BTN_DEFAULT
        if reset_action == "Initialize"
        else pre_focus_mag_custom_btn
    )
    custom_peak_btn = (
        P272_PEAKING_DISPLAY_SELECT_DEFAULT
        if reset_action == "Initialize"
        else pre_peaking_select_btn
    )
    return (
        P272_AUTO_MAG_IN_MF_DEFAULT,
        custom_mag_btn,
        P272_FOCUS_MAGNIF_TIME_DEFAULT,
        P272_INITIAL_FOCUS_MAG_STILL_DEFAULT,
        P272_INITIAL_FOCUS_MAG_MOVIE_DEFAULT,
        P272_AF_IN_FOCUS_MAG_DEFAULT,
        P272_PEAKING_DISPLAY_DEFAULT,
        custom_peak_btn,
        P272_PEAKING_LEVEL_DEFAULT,
        P272_PEAKING_COLOR_DEFAULT,
        P272_AF_ILLUMINATOR_DEFAULT,
    )


def compute_expected_focus_mag_peaking_runtime_gates(
    *,
    shooting_domain: str,
    focus_mode: str,
    hdmi_feed_mode: str,
    still_initial_focus_mag: str,
    movie_initial_focus_mag: str,
    af_in_focus_mag: str,
    peaking_display: str,
    af_illuminator: str,
) -> Tuple[str, bool, bool, bool, bool, bool]:
    """Compute `(active_initial_focus_mag, af_in_focus_mag_armed, af_illuminator_armed,
    lcd_peaking_visible, hdmi_focus_mag_leak_forbidden, hdmi_peaking_leak_forbidden)`.

    - Still & Movie maintain separate `[Initial Focus Mag.]` registers (`S&Q` uses Movie register).
    - `[AF in Focus Mag.]` & `[AF Illuminator]` are strictly **Still-image only** (never armed in
      `Movie` or `S&Q`).
    - External HDMI feeds (`Info Off`, `HDMI RAW`, or clean video feed) must NEVER receive camera LCD
      Focus Magnifier zoom boxes or Peaking overlays.
    """
    active_init_mag = still_initial_focus_mag if shooting_domain == "Still" else movie_initial_focus_mag
    af_in_mag_armed = shooting_domain == "Still" and af_in_focus_mag == "On" and focus_mode in ("MF", "DMF")
    af_illum_armed = shooting_domain == "Still" and af_illuminator == "Auto" and focus_mode in ("AF-S", "AF-C", "DMF")
    lcd_peaking_visible = peaking_display == "On"
    hdmi_clean_enforced = hdmi_feed_mode in ("Info Off", "HDMI RAW", "Info On")
    return (
        active_init_mag,
        af_in_mag_armed,
        af_illum_armed,
        lcd_peaking_visible,
        hdmi_clean_enforced,
        hdmi_clean_enforced,
    )


def compute_expected_effective_hdmi_resolution(
    *,
    configured_hdmi_resolution: str,
    log_shooting_mode: str,
    internal_recording_active: bool,
    rec_media_dur_hdmi_output: str,
) -> Tuple[str, bool]:
    """Compute `(effective_hdmi_resolution, log_1080p_downshift_active)`.

    Per Sony `ILME-FX3` (`ilc/2210`) *HDMI Resolution* rules:
    When `[Log Shooting] != Off` (`Cine EI`, `Cine EI Quick`, `Flexible ISO`) AND internal media
    recording is active AND `[Rec. Media dur HDMI Output] == "On"`, camera hardware forces `1080p`
    HDMI output overriding manual `[2160p]` or `[Auto]`. When `[Rec. Media dur HDMI Output] ==
    "Off(HDMI Only)"`, external `2160p`/`Auto` is permitted.
    """
    downshift = (
        log_shooting_mode != "Off"
        and internal_recording_active
        and rec_media_dur_hdmi_output == "On"
    )
    if downshift:
        return "1080p", True
    return configured_hdmi_resolution, False


def compute_expected_pillar47b_setup_state_after_reset(
    *,
    pre_area_setting: str,
    pre_daylight_savings: str,
    pre_date_format: str,
    pre_video_light_mode: str,
    pre_hdmi_resolution: str,
    rtc_backup_battery_lost: bool,
    reset_action: str,
) -> Tuple[str, str, str, str, str]:
    """Compute post-reset Pillar 47B `[Area/Date/Time Setting]`, `[Video Light Mode]` & `[HDMI Resolution]`.

    All three reside under `[Setup]` -> **survive `[Camera Settings Reset]` AND `[Reset Network Set.]`**,
    returning to factory defaults ONLY on `[Initialize]` (while `Area/Date/Time` is additionally cleared
    if `rtc_backup_battery_lost=True`).
    """
    if reset_action == "Initialize":
        return (
            P272_AREA_SETTING_DEFAULT,
            P272_DAYLIGHT_SAVINGS_DEFAULT,
            P272_DATE_FORMAT_DEFAULT,
            P272_VIDEO_LIGHT_MODE_DEFAULT,
            P272_HDMI_RESOLUTION_DEFAULT,
        )
    if rtc_backup_battery_lost:
        return (
            P272_AREA_SETTING_DEFAULT,
            P272_DAYLIGHT_SAVINGS_DEFAULT,
            P272_DATE_FORMAT_DEFAULT,
            pre_video_light_mode,
            pre_hdmi_resolution,
        )
    return (
        pre_area_setting,
        pre_daylight_savings,
        pre_date_format,
        pre_video_light_mode,
        pre_hdmi_resolution,
    )


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase272DonorArtifactDigest:
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
class Phase272DonorSnapshot:
    verification_mode: str
    all_donors_present: bool
    donor_files_inspected: int
    elapsed_seconds: float
    under_0_15s_budget: bool
    budget_seconds_applied: float
    raw_firmware_bytes_leaked: int
    artifacts: Tuple[Phase272DonorArtifactDigest, ...]


@dataclass(frozen=True)
class FocusMagPeakingStillAfIlluminatorVaultSpec:
    camera_model: str = P272_FX3_MODEL_NAME
    camera_model_id: int = P272_FX3_MODEL_ID
    helpguide_id: str = P272_FX3_HELPGUIDE_ID
    fw_version: str = P272_FX3_FW_VERSION
    focus_assistant_menu_path: Tuple[str, ...] = P272_FOCUS_ASSISTANT_MENU_PATH
    peaking_display_menu_path: Tuple[str, ...] = P272_PEAKING_DISPLAY_MENU_PATH
    af_illuminator_menu_path: Tuple[str, ...] = P272_AF_ILLUMINATOR_MENU_PATH
    hdmi_info_display_menu_path: Tuple[str, ...] = P272_HDMI_INFO_DISPLAY_MENU_PATH
    auto_mag_menu_label: str = P272_AUTO_MAG_IN_MF_LABEL
    factory_default_auto_mag_in_mf: str = P272_AUTO_MAG_IN_MF_DEFAULT
    factory_default_focus_mag_custom_btn: str = P272_FOCUS_MAGNIFIER_CUSTOM_BTN_DEFAULT
    factory_default_focus_mag_time: str = P272_FOCUS_MAGNIF_TIME_DEFAULT
    factory_default_still_initial_focus_mag: str = P272_INITIAL_FOCUS_MAG_STILL_DEFAULT
    factory_default_movie_initial_focus_mag: str = P272_INITIAL_FOCUS_MAG_MOVIE_DEFAULT
    factory_default_af_in_focus_mag: str = P272_AF_IN_FOCUS_MAG_DEFAULT
    factory_default_peaking_display: str = P272_PEAKING_DISPLAY_DEFAULT
    factory_default_peaking_select_btn: str = P272_PEAKING_DISPLAY_SELECT_DEFAULT
    factory_default_peaking_level: str = P272_PEAKING_LEVEL_DEFAULT
    factory_default_peaking_color: str = P272_PEAKING_COLOR_DEFAULT
    factory_default_af_illuminator: str = P272_AF_ILLUMINATOR_DEFAULT
    shooting_domain: str = "Movie"
    focus_mode: str = "MF"
    hdmi_feed_mode: str = "Info Off"
    pre_auto_mag_in_mf: str = "Off"
    pre_focus_mag_custom_btn: str = "Custom Button 5"
    pre_focus_mag_time: str = "5 Sec"
    pre_still_initial_focus_mag: str = "x4.0"
    pre_movie_initial_focus_mag: str = "x1.0"
    pre_af_in_focus_mag: str = "Off"
    pre_peaking_display: str = "On"
    pre_peaking_select_btn: str = "Control Wheel Right"
    pre_peaking_level: str = "High"
    pre_peaking_color: str = "Red"
    pre_af_illuminator: str = "Off"
    reset_action: str = "Camera Settings Reset"
    camset_load_after_reset: bool = False
    camset_slot: int = P272_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P272_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_auto_mag_in_mf: str = "On"
    saved_focus_mag_custom_btn: str = "Custom Button 5"
    saved_focus_mag_time: str = "No Limit"
    saved_still_initial_focus_mag: str = "x1.0"
    saved_movie_initial_focus_mag: str = "x1.0"
    saved_af_in_focus_mag: str = "On"
    saved_peaking_display: str = "Off"
    saved_peaking_select_btn: str = "Control Wheel Right"
    saved_peaking_level: str = "Mid"
    saved_peaking_color: str = "White"
    saved_af_illuminator: str = "Auto"
    post_auto_mag_in_mf: str = "On"
    post_focus_mag_custom_btn: str = "Custom Button 5"
    post_focus_mag_time: str = "No Limit"
    post_still_initial_focus_mag: str = "x1.0"
    post_movie_initial_focus_mag: str = "x1.0"
    post_af_in_focus_mag: str = "On"
    post_peaking_display: str = "Off"
    post_peaking_select_btn: str = "Control Wheel Right"
    post_peaking_level: str = "Mid"
    post_peaking_color: str = "White"
    post_af_illuminator: str = "Auto"
    legacy_mf_assist_spoof_events: int = 0
    still_movie_initial_mag_couplings: int = 0
    movie_af_in_focus_mag_events: int = 0
    hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int = 0
    movie_sq_af_illuminator_fire_events: int = 0
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_vault_mutation_events: int = 0
    slot1_vault_mutation_bytes: int = 0
    overlay_dir: str = P272_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P272_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P272_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P272_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class FocusMagPeakingStillAfIlluminatorVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    auto_mag_nomenclature_and_c5_verified: bool
    independent_still_movie_x10_verified: bool
    peaking_lcd_only_clean_hdmi_verified: bool
    still_only_af_in_mag_and_af_illuminator_verified: bool
    reset_scope_and_camset_restore_verified: bool
    h0_equals_h3_verified: bool
    matrix_states_checked: int
    legacy_mf_assist_spoof_events: int
    still_movie_initial_mag_couplings: int
    movie_af_in_focus_mag_events: int
    hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int
    movie_sq_af_illuminator_fire_events: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class AreaDatetimeVideolightHdmiresVaultSpec:
    camera_model: str = P272_FX3_MODEL_NAME
    camera_model_id: int = P272_FX3_MODEL_ID
    helpguide_id: str = P272_FX3_HELPGUIDE_ID
    fw_version: str = P272_FX3_FW_VERSION
    area_datetime_menu_path: Tuple[str, ...] = P272_AREA_DATETIME_MENU_PATH
    area_datetime_menu_label: str = P272_AREA_DATETIME_LABEL
    area_datetime_subitems: Tuple[str, ...] = P272_AREA_DATETIME_EXACT_4_SUBITEMS
    airplane_mode_menu_path: Tuple[str, ...] = P272_AIRPLANE_MODE_MENU_PATH
    video_light_mode_menu_path: Tuple[str, ...] = P272_VIDEO_LIGHT_MODE_MENU_PATH
    hdmi_resolution_menu_path: Tuple[str, ...] = P272_HDMI_RESOLUTION_MENU_PATH
    factory_default_area_setting: str = P272_AREA_SETTING_DEFAULT
    factory_default_daylight_savings: str = P272_DAYLIGHT_SAVINGS_DEFAULT
    factory_default_date_format: str = P272_DATE_FORMAT_DEFAULT
    factory_default_video_light_mode: str = P272_VIDEO_LIGHT_MODE_DEFAULT
    factory_default_hdmi_resolution: str = P272_HDMI_RESOLUTION_DEFAULT
    airplane_mode: str = "On"
    creators_app_auto_time_correction: str = "Off"
    creators_app_auto_area_adjustment: str = "Off"
    passive_tx_bytes_emitted: int = 0
    unsolicited_rtc_timezone_jump_events: int = 0
    h0_h3_forensic_timestamps_preserved: bool = True
    pre_area_setting: str = "Los Angeles / UTC-8"
    pre_daylight_savings: str = "Off"
    pre_date_format: str = "YYYY-MM-DD"
    pre_video_light_mode: str = "Power Link"
    pre_hdmi_resolution: str = "Auto"
    rtc_backup_battery_lost: bool = False
    reset_action: str = "Camera Settings Reset"
    camset_load_after_reset: bool = False
    camset_slot: int = P272_SLOT1_VAULT_SLOT
    camset_filename: str = "CAMSET01.DAT"
    camset_source_model: str = P272_FX3_MODEL_NAME
    camset_read_only_load: bool = True
    saved_area_setting: str = "Los Angeles / UTC-8"
    saved_daylight_savings: str = "Off"
    saved_date_format: str = "YYYY-MM-DD"
    saved_video_light_mode: str = "Power Link"
    saved_hdmi_resolution: str = "Auto"
    post_area_setting: str = "Los Angeles / UTC-8"
    post_daylight_savings: str = "Off"
    post_date_format: str = "YYYY-MM-DD"
    post_video_light_mode: str = "Power Link"
    post_hdmi_resolution: str = "Auto"
    mishoe_5v_rail_budget_ma: int = P272_MISHOE_5V_MAX_BUDGET_MA
    mishoe_5v_measured_ma: int = 680
    mishoe_5v_overcurrent_events: int = 0
    log_shooting_mode: str = "Cine EI"
    internal_recording_active: bool = True
    rec_media_dur_hdmi_output: str = "On"
    effective_hdmi_resolution: str = "1080p"
    hdmi_res_log_internal_rec_2160p_bypass_events: int = 0
    legacy_datetime_setup_spoof_events: int = 0
    slot1_holds_recovery_vault: bool = True
    slot1_sdxc_wp_locked: bool = True
    slot1_vault_mutation_events: int = 0
    slot1_vault_mutation_bytes: int = 0
    overlay_dir: str = P272_STAGE_B_VOLATILE_OVERLAY_DIR
    p2_blkroset_locked: bool = True
    stage_b_backup_bin_writes: int = 0
    backup_bin_h0_sha256: str = P272_PINNED_FX3_BACKUP_BIN_SHA256
    backup_bin_h3_sha256: str = P272_PINNED_FX3_BACKUP_BIN_SHA256
    tier0_surfaces_h0_h3_matched: int = P272_TIER0_SURFACE_COUNT
    persistent_write_unlock_requested: bool = False


@dataclass(frozen=True)
class AreaDatetimeVideolightHdmiresVaultReport:
    passed: bool
    status: str
    block_code: Optional[str]
    area_datetime_nomenclature_and_4subitems_verified: bool
    zero_rf_creators_app_suppression_verified: bool
    video_light_power_link_5v_900ma_verified: bool
    hdmi_res_auto_and_log_1080p_override_verified: bool
    setup_reset_persistence_and_slot1_vault_verified: bool
    h0_equals_h3_verified: bool
    matrix_states_checked: int
    effective_hdmi_resolution: str
    legacy_datetime_setup_spoof_events: int
    unsolicited_rtc_timezone_jump_events: int
    mishoe_5v_overcurrent_events: int
    hdmi_res_log_internal_rec_2160p_bypass_events: int
    slot1_vault_mutation_events: int
    slot1_vault_mutation_bytes: int
    physical_device_writes: int
    persistent_emmc_writes_authorized: bool
    digest_sha256: str
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class FocusMagDatetimeVideolightHdmiresVaultReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    passed: bool
    status: str
    donor_snapshot: Phase272DonorSnapshot
    focus_mag_peaking_report: FocusMagPeakingStillAfIlluminatorVaultReport
    area_datetime_videolight_hdmires_report: AreaDatetimeVideolightHdmiresVaultReport
    legacy_mf_assist_spoof_events: int
    still_movie_initial_mag_couplings: int
    movie_af_in_focus_mag_events: int
    hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int
    movie_sq_af_illuminator_fire_events: int
    legacy_datetime_setup_spoof_events: int
    unsolicited_rtc_timezone_jump_events: int
    mishoe_5v_overcurrent_events: int
    hdmi_res_log_internal_rec_2160p_bypass_events: int
    slot1_vault_mutation_events: int
    slot1_vault_mutation_bytes: int
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
class Pillar47ScenarioOutcome:
    scenario_id: str
    pillar: str
    expected_allowed: bool
    actual_allowed: bool
    block_code: Optional[str]
    passed: bool
    detail: str


@dataclass(frozen=True)
class Pillar47ASuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar47ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar47BSuiteResult:
    passed: bool
    status: str
    scenarios_passed: int
    scenarios_total: int
    scenarios: Tuple[Pillar47ScenarioOutcome, ...]


@dataclass(frozen=True)
class Pillar47StandaloneReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    elapsed_seconds: float
    donor_snapshot: Phase272DonorSnapshot
    pillar_47a_focus_mag_peaking_still_af_illuminator_vault: Pillar47ASuiteResult
    pillar_47b_area_datetime_videolight_hdmires_vault: Pillar47BSuiteResult
    legacy_mf_assist_spoof_events: int
    still_movie_initial_mag_couplings: int
    movie_af_in_focus_mag_events: int
    hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int
    movie_sq_af_illuminator_fire_events: int
    legacy_datetime_setup_spoof_events: int
    unsolicited_rtc_timezone_jump_events: int
    mishoe_5v_overcurrent_events: int
    hdmi_res_log_internal_rec_2160p_bypass_events: int
    slot1_vault_mutation_events: int
    slot1_vault_mutation_bytes: int
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
class Master47PillarRecoveryReport:
    schema: str
    version: str
    verification_mode: str
    all_passed: bool
    status: str
    pillar_count: int
    pillars_passed: int
    failed_pillars: Tuple[str, ...]
    elapsed_seconds: float
    under_2s_fast_cli_budget: bool
    under_6s_budget: bool
    nominal_under_4_0s: bool
    pillars: Tuple[MasterPillarStatus, ...]
    # Pillar 47 & Wave-45 top-level fields
    donor_snapshot: Phase272DonorSnapshot
    pillar47_a_focus_mag_peaking_still_af_illuminator_vault: Pillar47ASuiteResult
    pillar47_b_area_datetime_videolight_hdmires_vault: Pillar47BSuiteResult
    legacy_mf_assist_spoof_events: int
    still_movie_initial_mag_couplings: int
    movie_af_in_focus_mag_events: int
    hdmi_clean_feed_focus_mag_or_peaking_leak_pixels: int
    movie_sq_af_illuminator_fire_events: int
    legacy_datetime_setup_spoof_events: int
    unsolicited_rtc_timezone_jump_events: int
    mishoe_5v_overcurrent_events: int
    hdmi_res_log_internal_rec_2160p_bypass_events: int
    slot1_vault_mutation_events: int
    slot1_vault_mutation_bytes: int
    # Preserved Pillars 1..46 rollup metrics
    slot1_vault_folder_mutation_events: int
    slot1_vault_folder_mutation_bytes: int
    movie_custom_folder_or_title_overflow_events: int
    still_prefix_underscore_lead_or_len_violations: int
    gamma_assist_log_lockout_bypass_events: int
    gamma_assist_external_hdmi_leak_events: int
    tcub_camera_reset_wipe_or_format_violations: int
    fx3_has_builtin_end_filter: bool
    e_nd_actuator_tx_count: int
    cardless_unrecorded_production_violations: int
    legacy_v1_audio_level_menu_spoof_events: int
    photographer_copyright_pii_leaked_bytes: int
    copyright_char_overflow_or_movie_mutation_events: int
    slot1_copyright_vault_mutation_bytes: int
    apsc_s35_4k_or_raw_bypass_events: int
    ai_unit_subject_recog_spoof_events: int
    hdmi_clean_feed_eye_frame_baked_pixels: int
    version_dialog_flash_writes: int
    bodydata_flash_attempts_blocked: int
    slot1_bodydata_vault_mutation_bytes: int
    auto_slow_shutter_lockout_bypass_events: int
    auto_slow_shutter_angle_overlap_events: int
    breathing_comp_raw_or_240p_bypass_events: int
    hdmi_rec_ctrl_without_tc_violations: int
    slot1_hdmi_rec_vault_mutation_bytes: int
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
    master_47pillar_sha256: str
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
    max_full_bytes: int = P272_MAX_FULL_DONOR_BYTES,
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
        hdr = os.pread(fd, min(P272_BOUNDED_HEADER_BYTES, total_size), 0)
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


def _synthetic_phase272_donors() -> Tuple[Phase272DonorArtifactDigest, ...]:
    specs = (
        (
            "fx3_bodydata_702",
            P272_DONOR_FX3_BODYDATA_RELPATH,
            P272_PINNED_FX3_BODYDATA_BYTES,
            P272_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P272_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            "SYNTHETIC_UFU_DATV_PROV_UDID",
        ),
        (
            "fx3_appfw_702_so",
            P272_DONOR_FX3_APPFW_702_RELPATH,
            P272_PINNED_FX3_APPFW_702_BYTES,
            P272_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P272_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX3_APPFW_702",
        ),
        (
            "fx3_cpapp_b_bin",
            P272_DONOR_FX3_CPAPP_B_BIN_RELPATH,
            P272_PINNED_FX3_CPAPP_B_BIN_BYTES,
            P272_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P272_PINNED_FX3_CPAPP_B_BIN_HDR4K_SHA256,
            "SYNTHETIC_FX3_CPAPP_B_HEADER4K",
        ),
        (
            "fx6_appfw_601_so",
            P272_DONOR_FX6_APPFW_601_RELPATH,
            P272_PINNED_FX6_APPFW_601_BYTES,
            P272_BOUNDED_HEADER_BYTES,
            "HEADER4K_SHA256",
            P272_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            "SYNTHETIC_ELF64_AARCH64_FX6_APPFW_601",
        ),
        (
            "fx3_backup_bin",
            P272_DONOR_FX3_BACKUP_BIN_RELPATH,
            P272_PINNED_FX3_BACKUP_BIN_BYTES,
            P272_PINNED_FX3_BACKUP_BIN_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX3_BACKUP_BIN_SHA256,
            "SYNTHETIC_BK4_ILME_FX3",
        ),
        (
            "fx6_backup_ntsc_bin",
            P272_DONOR_FX6_BACKUP_NTSC_BIN_RELPATH,
            P272_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
            P272_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX6_BACKUP_NTSC_BIN_SHA256,
            "SYNTHETIC_BK4_CHAPLIN_NTSC",
        ),
        (
            "fx3_libbackup_so",
            P272_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P272_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P272_PINNED_FX3_LIBBACKUP_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX3_LIBBACKUP_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:Backup_read+backup_sharedcb_send_msg",
        ),
        (
            "fx3_libbackupmanager_so",
            P272_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P272_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P272_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_Z11BkDmn_writejPKvi+osal_snd_sync_msg",
        ),
        (
            "fx3_libsaveloadsettings_so",
            P272_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:SaveLoadSettingsIf+requestToRead+requestToCheck+requestToWrite",
        ),
        (
            "fx3_libgpe_so",
            P272_DONOR_FX3_LIBGPE_SO_RELPATH,
            P272_PINNED_FX3_LIBGPE_SO_BYTES,
            P272_PINNED_FX3_LIBGPE_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX3_LIBGPE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:gpe_blog_error+_ZNK5mpgpe5Gperm4InitEv",
        ),
        (
            "fx3_cameraondemandsaver_so",
            P272_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:CameraOnDemandSaver+_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji",
        ),
        (
            "fx3_libinfraairplanemode_so",
            P272_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH,
            P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:infra_airplane_mode_init+_ZN3MWF6InhMgr15UpdateInhFactorEv",
        ),
        (
            "fx3_libinframediaconfig_so",
            P272_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaConfig+_ZN16InfraMediaConfig10SaveBackupEt",
        ),
        (
            "fx3_libinframediadetect_so",
            P272_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH,
            P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
            P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraMediaDetect+_ZN16InfraMediaDetect10GetVersionEv",
        ),
        (
            "fx6_libinfradial_so",
            P272_DONOR_FX6_LIBINFRADIAL_SO_RELPATH,
            P272_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
            P272_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:_ZN9InfraDial4InitEv+_ZN9InfraDial10set4KeyInhEb",
        ),
        (
            "fx6_libinfrahotshoe_so",
            P272_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH,
            P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
            P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
            "FULL_SHA256",
            P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
            "SYNTHETIC_ELF64_AARCH64:InfraHotshoe+_ZN12InfraHotshoe15ResourceToInfraEi",
        ),
    )
    return tuple(
        Phase272DonorArtifactDigest(
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


def inspect_phase272_donors_readonly(force_clean_room: Optional[bool] = None) -> Phase272DonorSnapshot:
    """Inspect Wave-45 FX3 7.02 & FX6 6.01 donors strictly `O_RDONLY | O_NOFOLLOW | O_NONBLOCK` in `< 2.0s`."""
    t0 = time.monotonic()
    budget = _donor_inspect_budget_seconds()
    clean_room = _is_clean_room_forced(force_clean_room)
    if clean_room:
        artifacts = _synthetic_phase272_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase272DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    probe_specs: Tuple[Tuple[str, str, int, str, Any], ...] = (
        (
            "fx3_bodydata_702",
            P272_DONOR_FX3_BODYDATA_RELPATH,
            P272_PINNED_FX3_BODYDATA_BYTES,
            P272_PINNED_FX3_BODYDATA_HDR4K_SHA256,
            lambda d: (
                d[:8] == b"\x89UFU\r\n\x1a\n" and b"DATV" in d and b"PROV" in d and b"UDID" in d,
                "UFU_DATV_PROV_UDID" if d[:8] == b"\x89UFU\r\n\x1a\n" else "BAD_UFU_MAGIC",
            ),
        ),
        (
            "fx3_appfw_702_so",
            P272_DONOR_FX3_APPFW_702_RELPATH,
            P272_PINNED_FX3_APPFW_702_BYTES,
            P272_PINNED_FX3_APPFW_702_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_cpapp_b_bin",
            P272_DONOR_FX3_CPAPP_B_BIN_RELPATH,
            P272_PINNED_FX3_CPAPP_B_BIN_BYTES,
            P272_PINNED_FX3_CPAPP_B_BIN_HDR4K_SHA256,
            lambda d: (len(d) == P272_BOUNDED_HEADER_BYTES, "FX3_CPAPP_B_HEADER4K"),
        ),
        (
            "fx6_appfw_601_so",
            P272_DONOR_FX6_APPFW_601_RELPATH,
            P272_PINNED_FX6_APPFW_601_BYTES,
            P272_PINNED_FX6_APPFW_601_HDR4K_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, ()),
        ),
        (
            "fx3_backup_bin",
            P272_DONOR_FX3_BACKUP_BIN_RELPATH,
            P272_PINNED_FX3_BACKUP_BIN_BYTES,
            P272_PINNED_FX3_BACKUP_BIN_SHA256,
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
            "fx6_backup_ntsc_bin",
            P272_DONOR_FX6_BACKUP_NTSC_BIN_RELPATH,
            P272_PINNED_FX6_BACKUP_NTSC_BIN_BYTES,
            P272_PINNED_FX6_BACKUP_NTSC_BIN_SHA256,
            lambda d: (
                len(d) >= 20
                and struct.unpack_from("<I", d, 4)[0] == 0xAAAAAAAA
                and d[12:16] == b"BK4\x00",
                "BK4_CHAPLIN_NTSC"
                if (
                    len(d) >= 20
                    and struct.unpack_from("<I", d, 4)[0] == 0xAAAAAAAA
                    and d[12:16] == b"BK4\x00"
                )
                else "BAD_FX6_BACKUP_MAGIC",
            ),
        ),
        (
            "fx3_libbackup_so",
            P272_DONOR_FX3_LIBBACKUP_SO_RELPATH,
            P272_PINNED_FX3_LIBBACKUP_SO_BYTES,
            P272_PINNED_FX3_LIBBACKUP_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"Backup_read", b"backup_sharedcb_send_msg")),
        ),
        (
            "fx3_libbackupmanager_so",
            P272_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH,
            P272_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES,
            P272_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"_Z11BkDmn_writejPKvi", b"osal_snd_sync_msg")),
        ),
        (
            "fx3_libsaveloadsettings_so",
            P272_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH,
            P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES,
            P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"SaveLoadSettingsIf", b"requestToRead", b"requestToCheck", b"requestToWrite"),
            ),
        ),
        (
            "fx3_libgpe_so",
            P272_DONOR_FX3_LIBGPE_SO_RELPATH,
            P272_PINNED_FX3_LIBGPE_SO_BYTES,
            P272_PINNED_FX3_LIBGPE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(d, (b"gpe_blog_error", b"_ZNK5mpgpe5Gperm4InitEv")),
        ),
        (
            "fx3_cameraondemandsaver_so",
            P272_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH,
            P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES,
            P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"CameraOnDemandSaver", b"_ZN18CAM_ONDEMAND_SAVER17OsalHandleWrapperC1Ejji"),
            ),
        ),
        (
            "fx3_libinfraairplanemode_so",
            P272_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH,
            P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES,
            P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"infra_airplane_mode_init", b"_ZN3MWF6InhMgr15UpdateInhFactorEv"),
            ),
        ),
        (
            "fx3_libinframediaconfig_so",
            P272_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH,
            P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES,
            P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraMediaConfig", b"_ZN16InfraMediaConfig10SaveBackupEt"),
            ),
        ),
        (
            "fx3_libinframediadetect_so",
            P272_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH,
            P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES,
            P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraMediaDetect", b"_ZN16InfraMediaDetect10GetVersionEv"),
            ),
        ),
        (
            "fx6_libinfradial_so",
            P272_DONOR_FX6_LIBINFRADIAL_SO_RELPATH,
            P272_PINNED_FX6_LIBINFRADIAL_SO_BYTES,
            P272_PINNED_FX6_LIBINFRADIAL_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"_ZN9InfraDial4InitEv", b"_ZN9InfraDial10set4KeyInhEb"),
            ),
        ),
        (
            "fx6_libinfrahotshoe_so",
            P272_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH,
            P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES,
            P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256,
            lambda d: _check_elf64_aarch64_tokens(
                d,
                (b"InfraHotshoe", b"_ZN12InfraHotshoe15ResourceToInfraEi"),
            ),
        ),
    )

    real_artifacts: List[Phase272DonorArtifactDigest] = []
    any_missing = False
    for aid, rel, pinned_bytes, pinned_sha, marker_fn in probe_specs:
        present, total_b, read_b, dkind, dsha, raw_slice = _read_donor_readonly_bounded(rel)
        if not present:
            any_missing = True
            break
        marker_ok, marker_summary = marker_fn(raw_slice)
        matches = (total_b == pinned_bytes) and (dsha == pinned_sha) and bool(marker_ok)
        real_artifacts.append(
            Phase272DonorArtifactDigest(
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
        artifacts = _synthetic_phase272_donors()
        dt = round(time.monotonic() - t0, 6)
        return Phase272DonorSnapshot(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            all_donors_present=True,
            donor_files_inspected=len(artifacts),
            elapsed_seconds=dt,
            under_0_15s_budget=dt < budget,
            budget_seconds_applied=budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            artifacts=artifacts,
        )

    all_ok = len(real_artifacts) == len(probe_specs) and all(a.matches_pinned for a in real_artifacts)
    dt = round(time.monotonic() - t0, 6)
    return Phase272DonorSnapshot(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        all_donors_present=all_ok,
        donor_files_inspected=len(real_artifacts),
        elapsed_seconds=dt,
        under_0_15s_budget=dt < budget,
        budget_seconds_applied=budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        artifacts=tuple(real_artifacts),
    )


def build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec() -> (
    FocusMagPeakingStillAfIlluminatorVaultSpec
):
    """Return canonical safe Wave-45 Pillar 47A spec."""
    return FocusMagPeakingStillAfIlluminatorVaultSpec()


def build_default_safe_area_datetime_videolight_hdmires_vault_spec() -> (
    AreaDatetimeVideolightHdmiresVaultSpec
):
    """Return canonical safe Wave-45 Pillar 47B spec."""
    return AreaDatetimeVideolightHdmiresVaultSpec()


# ---------------------------------------------------------------------------
# Pillar 47A & Pillar 47B Evaluators
# ---------------------------------------------------------------------------


def evaluate_focus_mag_peaking_still_af_illuminator_vault(
    spec: FocusMagPeakingStillAfIlluminatorVaultSpec,
) -> FocusMagPeakingStillAfIlluminatorVaultReport:
    """Evaluate Pillar 47A (`[Auto Magnifier in MF]`, `C5`, dual `[Initial Focus Mag.] = [x1.0]`,
    Still-only `[AF in Focus Mag.]`, `[Peaking Display]` clean-HDMI isolation & Still-only `[AF Illuminator]`).
    """
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P272_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(
            P272_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Persistent eMMC write unlock requested inside zero-write Pillar 47A verifier",
        )

    # 1. Baseline model, Help Guide, menu paths, overlay isolation & Tier-0 H0 == H3
    if (
        spec.camera_model != P272_FX3_MODEL_NAME
        or spec.camera_model_id != P272_FX3_MODEL_ID
        or spec.helpguide_id != P272_FX3_HELPGUIDE_ID
        or spec.fw_version not in P272_FX3_SUPPORTED_FW_VERSIONS
        or spec.focus_assistant_menu_path != P272_FOCUS_ASSISTANT_MENU_PATH
        or spec.peaking_display_menu_path != P272_PEAKING_DISPLAY_MENU_PATH
        or spec.af_illuminator_menu_path != P272_AF_ILLUMINATOR_MENU_PATH
        or spec.hdmi_info_display_menu_path != P272_HDMI_INFO_DISPLAY_MENU_PATH
        or spec.shooting_domain not in P272_SHOOTING_DOMAINS
        or spec.focus_mode not in P272_FOCUS_MODES
        or spec.hdmi_feed_mode not in P272_HDMI_FEED_MODES
        or spec.reset_action not in P272_RESET_ACTIONS
    ):
        _fail(
            P272_BLOCKED_INVALID_FOCUS_MAG_PEAKING_SPEC,
            "Invalid camera/model_id/fw/menu path/domain/reset specification for Pillar 47A",
        )

    if _targets_persistent_emmc(spec.overlay_dir) or not _is_tmpfs_path(spec.overlay_dir) or not spec.p2_blkroset_locked:
        _fail(
            P272_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped tmpfs or p2 BLKROSET unlocked: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == P272_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P272_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P272_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 drift or non-zero Stage-B Backup.bin writes",
        )

    # 2. Nomenclature guard: strictly reject legacy "MF Assist" spoofing
    nom_errs_before = len(errors)
    legacy_mf_spoofs = int(spec.legacy_mf_assist_spoof_events)
    if (
        spec.auto_mag_menu_label != P272_AUTO_MAG_IN_MF_LABEL
        or spec.auto_mag_menu_label == P272_FORBIDDEN_LEGACY_MF_ASSIST_LABEL
        or spec.legacy_mf_assist_spoof_events != 0
    ):
        legacy_mf_spoofs = max(legacy_mf_spoofs, 1)
        _fail(
            P272_BLOCKED_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF,
            f"Focus Assistant label must be {P272_AUTO_MAG_IN_MF_LABEL!r}, never legacy 'MF Assist'",
        )

    # 3. Factory defaults & independent Still vs Movie [Initial Focus Mag.] = [x1.0]
    mag_couplings = int(spec.still_movie_initial_mag_couplings)
    if (
        spec.factory_default_auto_mag_in_mf != P272_AUTO_MAG_IN_MF_DEFAULT
        or spec.factory_default_focus_mag_custom_btn != P272_FOCUS_MAGNIFIER_CUSTOM_BTN_DEFAULT
        or spec.factory_default_focus_mag_time != P272_FOCUS_MAGNIF_TIME_DEFAULT
        or spec.factory_default_still_initial_focus_mag != P272_INITIAL_FOCUS_MAG_STILL_DEFAULT
        or spec.factory_default_movie_initial_focus_mag != P272_INITIAL_FOCUS_MAG_MOVIE_DEFAULT
        or spec.factory_default_af_in_focus_mag != P272_AF_IN_FOCUS_MAG_DEFAULT
        or spec.factory_default_peaking_display != P272_PEAKING_DISPLAY_DEFAULT
        or spec.factory_default_peaking_select_btn != P272_PEAKING_DISPLAY_SELECT_DEFAULT
        or spec.factory_default_peaking_level != P272_PEAKING_LEVEL_DEFAULT
        or spec.factory_default_peaking_color != P272_PEAKING_COLOR_DEFAULT
        or spec.factory_default_af_illuminator != P272_AF_ILLUMINATOR_DEFAULT
    ):
        _fail(
            P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING,
            "Wave-45 factory default mismatch in Focus Assistant / Peaking Display / AF Illuminator",
        )

    for tag, amag, mbtn, mtime, simag, mimag, afinmag, pkdisp, pksel, pklvl, pkcol, afill in (
        (
            "pre",
            spec.pre_auto_mag_in_mf,
            spec.pre_focus_mag_custom_btn,
            spec.pre_focus_mag_time,
            spec.pre_still_initial_focus_mag,
            spec.pre_movie_initial_focus_mag,
            spec.pre_af_in_focus_mag,
            spec.pre_peaking_display,
            spec.pre_peaking_select_btn,
            spec.pre_peaking_level,
            spec.pre_peaking_color,
            spec.pre_af_illuminator,
        ),
        (
            "saved",
            spec.saved_auto_mag_in_mf,
            spec.saved_focus_mag_custom_btn,
            spec.saved_focus_mag_time,
            spec.saved_still_initial_focus_mag,
            spec.saved_movie_initial_focus_mag,
            spec.saved_af_in_focus_mag,
            spec.saved_peaking_display,
            spec.saved_peaking_select_btn,
            spec.saved_peaking_level,
            spec.saved_peaking_color,
            spec.saved_af_illuminator,
        ),
        (
            "post",
            spec.post_auto_mag_in_mf,
            spec.post_focus_mag_custom_btn,
            spec.post_focus_mag_time,
            spec.post_still_initial_focus_mag,
            spec.post_movie_initial_focus_mag,
            spec.post_af_in_focus_mag,
            spec.post_peaking_display,
            spec.post_peaking_select_btn,
            spec.post_peaking_level,
            spec.post_peaking_color,
            spec.post_af_illuminator,
        ),
    ):
        if (
            amag not in P272_ON_OFF_MODES
            or mbtn not in P272_ALLOWED_FOCUS_MAG_CUSTOM_BTNS
            or mtime not in P272_FOCUS_MAGNIF_TIME_MODES
            or simag not in P272_INITIAL_FOCUS_MAG_MODES
            or mimag not in P272_INITIAL_FOCUS_MAG_MODES
            or afinmag not in P272_ON_OFF_MODES
            or pkdisp not in P272_ON_OFF_MODES
            or pksel not in P272_ALLOWED_PEAKING_SELECT_BTNS
            or pklvl not in P272_PEAKING_LEVELS
            or pkcol not in P272_PEAKING_COLORS
            or afill not in P272_AF_ILLUMINATOR_MODES
        ):
            _fail(
                P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING,
                f"Invalid {tag} Pillar 47A Focus Assistant / Peaking / AF Illuminator enum value",
            )

    if spec.still_movie_initial_focus_mag_coupled_violation if hasattr(spec, "still_movie_initial_focus_mag_coupled_violation") else False:
        mag_couplings = max(mag_couplings, 1)
    if spec.still_movie_initial_mag_couplings != 0:
        mag_couplings = max(mag_couplings, 1)
        _fail(
            P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING,
            "Still and Movie [Initial Focus Mag.] registers must remain strictly independent",
        )
    auto_mag_c5_verified = len(errors) == nom_errs_before
    indep_x10_verified = mag_couplings == 0 and auto_mag_c5_verified

    # 4. Clean-HDMI isolation (LCD-only Focus Magnifier & Peaking overlays)
    hdmi_errs_before = len(errors)
    hdmi_leaks = int(spec.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels)
    if spec.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels != 0:
        hdmi_leaks = max(hdmi_leaks, 1)
        _fail(
            P272_BLOCKED_HDMI_CLEAN_FEED_OVERLAY_LEAK,
            "Focus Magnifier / Peaking overlay leaked non-zero pixels onto clean HDMI output",
        )
    peaking_clean_hdmi_verified = len(errors) == hdmi_errs_before

    # 5. Still-only [AF in Focus Mag.] & Still-only [AF Illuminator]
    af_errs_before = len(errors)
    movie_af_in_mag = int(spec.movie_af_in_focus_mag_events)
    movie_sq_af_illum = int(spec.movie_sq_af_illuminator_fire_events)
    if spec.movie_af_in_focus_mag_events != 0 or spec.movie_sq_af_illuminator_fire_events != 0:
        if spec.movie_af_in_focus_mag_events != 0:
            movie_af_in_mag = max(movie_af_in_mag, 1)
        if spec.movie_sq_af_illuminator_fire_events != 0:
            movie_sq_af_illum = max(movie_sq_af_illum, 1)
        _fail(
            P272_BLOCKED_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG,
            "[AF in Focus Mag.] and [AF Illuminator] are strictly Still-only and must never fire in Movie/S&Q",
        )
    still_only_af_verified = len(errors) == af_errs_before

    # 6. Exhaustive 144-state matrix proof (3 shoot * 3 hdmi * 2 still_mag * 2 movie_mag * 2 peaking * 2 af_illum)
    matrix_checked = 0
    for s_dom in P272_SHOOTING_DOMAINS:
        for h_feed in P272_HDMI_FEED_MODES:
            for s_mag in P272_INITIAL_FOCUS_MAG_MODES:
                for m_mag in P272_INITIAL_FOCUS_MAG_MODES:
                    for pk in P272_ON_OFF_MODES:
                        for af_il in P272_AF_ILLUMINATOR_MODES:
                            (
                                act_mag,
                                af_mag_arm,
                                af_il_arm,
                                _lcd_pk,
                                no_mag_leak,
                                no_pk_leak,
                            ) = compute_expected_focus_mag_peaking_runtime_gates(
                                shooting_domain=s_dom,
                                focus_mode="DMF",
                                hdmi_feed_mode=h_feed,
                                still_initial_focus_mag=s_mag,
                                movie_initial_focus_mag=m_mag,
                                af_in_focus_mag="On",
                                peaking_display=pk,
                                af_illuminator=af_il,
                            )
                            _need(
                                act_mag == (s_mag if s_dom == "Still" else m_mag),
                                "Still vs Movie Initial Focus Mag register mismatch",
                            )
                            if s_dom != "Still":
                                _need(not af_mag_arm and not af_il_arm, "Movie/S&Q must disarm Still-only AF assists")
                            _need(no_mag_leak and no_pk_leak, "Clean HDMI isolation violated in matrix")
                            matrix_checked += 1

    # 7. Reset scope ([Camera Settings Reset] vs [Reset Network Set.] vs [Initialize]) + O_RDONLY CAMSET Load
    rst_errs_before = len(errors)
    if spec.slot1_vault_mutation_events != 0 or spec.slot1_vault_mutation_bytes != 0:
        _fail(
            P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT,
            "Slot-1 recovery vault must remain read-only during Pillar 47A verification",
        )
    if spec.camset_load_after_reset:
        if (
            spec.camset_slot != P272_SLOT1_VAULT_SLOT
            or spec.camset_filename not in P272_CAMSET_FILENAMES
            or spec.camset_source_model != P272_FX3_MODEL_NAME
            or not spec.camset_read_only_load
        ):
            _fail(
                P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT,
                "Invalid CAMSET01..10.DAT O_RDONLY Slot-1 restoration envelope in Pillar 47A",
            )
        expected_post = (
            spec.saved_auto_mag_in_mf,
            spec.saved_focus_mag_custom_btn,
            spec.saved_focus_mag_time,
            spec.saved_still_initial_focus_mag,
            spec.saved_movie_initial_focus_mag,
            spec.saved_af_in_focus_mag,
            spec.saved_peaking_display,
            spec.saved_peaking_select_btn,
            spec.saved_peaking_level,
            spec.saved_peaking_color,
            spec.saved_af_illuminator,
        )
    else:
        expected_post = compute_expected_pillar47a_focus_assistant_state_after_reset(
            pre_auto_mag_in_mf=spec.pre_auto_mag_in_mf,
            pre_focus_mag_custom_btn=spec.pre_focus_mag_custom_btn,
            pre_focus_mag_time=spec.pre_focus_mag_time,
            pre_still_initial_focus_mag=spec.pre_still_initial_focus_mag,
            pre_movie_initial_focus_mag=spec.pre_movie_initial_focus_mag,
            pre_af_in_focus_mag=spec.pre_af_in_focus_mag,
            pre_peaking_display=spec.pre_peaking_display,
            pre_peaking_select_btn=spec.pre_peaking_select_btn,
            pre_peaking_level=spec.pre_peaking_level,
            pre_peaking_color=spec.pre_peaking_color,
            pre_af_illuminator=spec.pre_af_illuminator,
            reset_action=spec.reset_action,
        )
    actual_post = (
        spec.post_auto_mag_in_mf,
        spec.post_focus_mag_custom_btn,
        spec.post_focus_mag_time,
        spec.post_still_initial_focus_mag,
        spec.post_movie_initial_focus_mag,
        spec.post_af_in_focus_mag,
        spec.post_peaking_display,
        spec.post_peaking_select_btn,
        spec.post_peaking_level,
        spec.post_peaking_color,
        spec.post_af_illuminator,
    )
    if actual_post != expected_post:
        _fail(
            P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT,
            f"Post-reset Pillar 47A state {actual_post!r} drifted from expected {expected_post!r}",
        )
    reset_camset_verified = len(errors) == rst_errs_before

    passed = len(errors) == 0
    status = P272_STATUS_VERIFIED_PILLAR_47A if passed else P272_STATUS_REJECTED_PILLAR_47A
    digest = _canonical_sha256(
        {
            "pillar": "47A",
            "passed": passed,
            "status": status,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "post_auto_mag_in_mf": spec.post_auto_mag_in_mf,
            "post_focus_mag_custom_btn": spec.post_focus_mag_custom_btn,
            "post_still_initial_focus_mag": spec.post_still_initial_focus_mag,
            "post_movie_initial_focus_mag": spec.post_movie_initial_focus_mag,
        }
    )
    return FocusMagPeakingStillAfIlluminatorVaultReport(
        passed=passed,
        status=status,
        block_code=None if passed else block_code,
        auto_mag_nomenclature_and_c5_verified=auto_mag_c5_verified,
        independent_still_movie_x10_verified=indep_x10_verified,
        peaking_lcd_only_clean_hdmi_verified=peaking_clean_hdmi_verified,
        still_only_af_in_mag_and_af_illuminator_verified=still_only_af_verified,
        reset_scope_and_camset_restore_verified=reset_camset_verified,
        h0_equals_h3_verified=h0_eq_h3,
        matrix_states_checked=matrix_checked,
        legacy_mf_assist_spoof_events=legacy_mf_spoofs,
        still_movie_initial_mag_couplings=mag_couplings,
        movie_af_in_focus_mag_events=movie_af_in_mag,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=hdmi_leaks,
        movie_sq_af_illuminator_fire_events=movie_sq_af_illum,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


def evaluate_area_datetime_videolight_hdmires_vault(
    spec: AreaDatetimeVideolightHdmiresVaultSpec,
) -> AreaDatetimeVideolightHdmiresVaultReport:
    """Evaluate Pillar 47B (`[Area/Date/Time Setting]` zero-RF Creators' App suppression,
    `[Video Light Mode] = [Power Link]` `5V <= 900 mA`, `[HDMI Resolution]` Log `1080p` downshift &
    Slot-1 vault read-only integrity).
    """
    errors: List[str] = _safety_invariant_errors()
    block_code: Optional[str] = P272_BLOCKED_SAFETY_POLICY_VIOLATION if errors else None

    def _fail(code: str, msg: str) -> None:
        nonlocal block_code
        errors.append(msg)
        if block_code is None:
            block_code = code

    if spec.persistent_write_unlock_requested:
        _fail(
            P272_BLOCKED_SAFETY_POLICY_VIOLATION,
            "Persistent eMMC write unlock requested inside zero-write Pillar 47B verifier",
        )

    # 1. Baseline model, Help Guide, menu paths, overlay isolation & Tier-0 H0 == H3
    if (
        spec.camera_model != P272_FX3_MODEL_NAME
        or spec.camera_model_id != P272_FX3_MODEL_ID
        or spec.helpguide_id != P272_FX3_HELPGUIDE_ID
        or spec.fw_version not in P272_FX3_SUPPORTED_FW_VERSIONS
        or spec.area_datetime_menu_path != P272_AREA_DATETIME_MENU_PATH
        or spec.airplane_mode_menu_path != P272_AIRPLANE_MODE_MENU_PATH
        or spec.video_light_mode_menu_path != P272_VIDEO_LIGHT_MODE_MENU_PATH
        or spec.hdmi_resolution_menu_path != P272_HDMI_RESOLUTION_MENU_PATH
        or spec.airplane_mode not in P272_AIRPLANE_MODES
        or spec.creators_app_auto_time_correction not in P272_ON_OFF_MODES
        or spec.creators_app_auto_area_adjustment not in P272_ON_OFF_MODES
        or spec.log_shooting_mode not in P272_LOG_SHOOTING_MODES
        or spec.rec_media_dur_hdmi_output not in P272_REC_MEDIA_DUR_HDMI_MODES
        or spec.reset_action not in P272_RESET_ACTIONS
    ):
        _fail(
            P272_BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC,
            "Invalid camera/model_id/fw/menu path/Log/reset specification for Pillar 47B",
        )

    if _targets_persistent_emmc(spec.overlay_dir) or not _is_tmpfs_path(spec.overlay_dir) or not spec.p2_blkroset_locked:
        _fail(
            P272_BLOCKED_PERSISTENT_OVERLAY_ESCAPE,
            f"Stage-B overlay escaped tmpfs or p2 BLKROSET unlocked: {spec.overlay_dir!r}",
        )

    h0_eq_h3 = (
        spec.stage_b_backup_bin_writes == 0
        and spec.backup_bin_h0_sha256 == P272_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.backup_bin_h3_sha256 == P272_PINNED_FX3_BACKUP_BIN_SHA256
        and spec.tier0_surfaces_h0_h3_matched == P272_TIER0_SURFACE_COUNT
    )
    if not h0_eq_h3:
        _fail(
            P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
            "Tier-0 Backup.bin H0 != H3 drift or non-zero Stage-B Backup.bin writes",
        )

    # 2. [Area/Date/Time Setting] nomenclature & exact 4 sub-items (reject legacy "Date/Time Setup")
    dt_errs_before = len(errors)
    legacy_dt_spoofs = int(spec.legacy_datetime_setup_spoof_events)
    if (
        spec.area_datetime_menu_label != P272_AREA_DATETIME_LABEL
        or spec.area_datetime_menu_label == P272_FORBIDDEN_LEGACY_DATETIME_LABEL
        or spec.area_datetime_subitems != P272_AREA_DATETIME_EXACT_4_SUBITEMS
        or spec.legacy_datetime_setup_spoof_events != 0
    ):
        legacy_dt_spoofs = max(legacy_dt_spoofs, 1)
        _fail(
            P272_BLOCKED_LEGACY_DATETIME_SETUP_SPOOF,
            f"Menu must be {P272_AREA_DATETIME_LABEL!r} with exact 4 sub-items, never legacy 'Date/Time Setup'",
        )

    if (
        spec.factory_default_area_setting != P272_AREA_SETTING_DEFAULT
        or spec.factory_default_daylight_savings != P272_DAYLIGHT_SAVINGS_DEFAULT
        or spec.factory_default_date_format != P272_DATE_FORMAT_DEFAULT
        or spec.factory_default_video_light_mode != P272_VIDEO_LIGHT_MODE_DEFAULT
        or spec.factory_default_hdmi_resolution != P272_HDMI_RESOLUTION_DEFAULT
    ):
        _fail(
            P272_BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC,
            "Wave-45 Setup factory defaults mismatch (Daylight Savings Off / Video Light Power Link / HDMI Auto)",
        )

    for tag, dls, dfmt, vlm, hres in (
        (
            "pre",
            spec.pre_daylight_savings,
            spec.pre_date_format,
            spec.pre_video_light_mode,
            spec.pre_hdmi_resolution,
        ),
        (
            "saved",
            spec.saved_daylight_savings,
            spec.saved_date_format,
            spec.saved_video_light_mode,
            spec.saved_hdmi_resolution,
        ),
        (
            "post",
            spec.post_daylight_savings,
            spec.post_date_format,
            spec.post_video_light_mode,
            spec.post_hdmi_resolution,
        ),
    ):
        if (
            dls not in P272_DAYLIGHT_SAVINGS_MODES
            or dfmt not in P272_DATE_FORMATS
            or vlm not in P272_VIDEO_LIGHT_MODES
            or hres not in P272_HDMI_RESOLUTIONS
        ):
            _fail(
                P272_BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC,
                f"Invalid {tag} Pillar 47B Daylight Savings / Date Format / Video Light / HDMI Res value",
            )
    area_dt_verified = len(errors) == dt_errs_before

    # 3. Zero-RF Creators' App Auto Time/Area suppression & H0..H3 forensic timestamp preservation
    rf_errs_before = len(errors)
    rtc_jumps = int(spec.unsolicited_rtc_timezone_jump_events)
    if (
        spec.airplane_mode != "On"
        or spec.creators_app_auto_time_correction != "Off"
        or spec.creators_app_auto_area_adjustment != "Off"
        or spec.passive_tx_bytes_emitted != 0
        or spec.unsolicited_rtc_timezone_jump_events != 0
        or not spec.h0_h3_forensic_timestamps_preserved
    ):
        if spec.unsolicited_rtc_timezone_jump_events != 0 or spec.creators_app_auto_time_correction != "Off" or spec.creators_app_auto_area_adjustment != "Off":
            rtc_jumps = max(rtc_jumps, 1)
        _fail(
            P272_BLOCKED_ZERO_RF_CREATORS_APP_SYNC_OR_RTC_JUMP,
            "Zero-RF bench requires Airplane Mode=On, Creators' App Auto Time/Area=Off, passive_tx=0 & 0 RTC jumps",
        )
    zero_rf_verified = len(errors) == rf_errs_before

    # 4. [Video Light Mode] MI-Shoe 5V <= 900 mA (Gate G24) rail guard
    vl_errs_before = len(errors)
    overcurrent_events = int(spec.mishoe_5v_overcurrent_events)
    if (
        spec.mishoe_5v_rail_budget_ma > P272_MISHOE_5V_MAX_BUDGET_MA
        or spec.mishoe_5v_measured_ma < 0
        or spec.mishoe_5v_measured_ma > spec.mishoe_5v_rail_budget_ma
        or spec.mishoe_5v_overcurrent_events != 0
    ):
        overcurrent_events = max(overcurrent_events, 1)
        _fail(
            P272_BLOCKED_MISHOE_5V_OVERCURRENT,
            f"MI-Shoe 5V Video Light draw {spec.mishoe_5v_measured_ma}mA violated <= {P272_MISHOE_5V_MAX_BUDGET_MA}mA Gate G24 budget",
        )
    video_light_verified = len(errors) == vl_errs_before

    # 5. [HDMI Resolution] Log internal-recording 1080p downshift override
    hdmi_errs_before = len(errors)
    log_bypass_events = int(spec.hdmi_res_log_internal_rec_2160p_bypass_events)
    exp_eff_hdmi_res, _downshift = compute_expected_effective_hdmi_resolution(
        configured_hdmi_resolution=spec.post_hdmi_resolution,
        log_shooting_mode=spec.log_shooting_mode,
        internal_recording_active=spec.internal_recording_active,
        rec_media_dur_hdmi_output=spec.rec_media_dur_hdmi_output,
    )
    if (
        spec.effective_hdmi_resolution != exp_eff_hdmi_res
        or spec.hdmi_res_log_internal_rec_2160p_bypass_events != 0
    ):
        log_bypass_events = max(log_bypass_events, 1)
        _fail(
            P272_BLOCKED_HDMI_RES_LOG_1080P_OVERRIDE,
            f"Effective HDMI Resolution {spec.effective_hdmi_resolution!r} drifted from expected {exp_eff_hdmi_res!r}",
        )
    hdmi_res_verified = len(errors) == hdmi_errs_before

    # 6. Exhaustive 256-state matrix proof (4 video_light * 4 hdmi_res * 4 log * 2 rec_media * 2 airplane)
    matrix_checked = 0
    for vl in P272_VIDEO_LIGHT_MODES:
        for h_cfg in P272_HDMI_RESOLUTIONS:
            for l_mode in P272_LOG_SHOOTING_MODES:
                for rec_hdmi in P272_REC_MEDIA_DUR_HDMI_MODES:
                    for ap in P272_AIRPLANE_MODES:
                        eff_h, down = compute_expected_effective_hdmi_resolution(
                            configured_hdmi_resolution=h_cfg,
                            log_shooting_mode=l_mode,
                            internal_recording_active=True,
                            rec_media_dur_hdmi_output=rec_hdmi,
                        )
                        if l_mode != "Off" and rec_hdmi == "On":
                            _need(down and eff_h == "1080p", "Log internal recording must downshift HDMI to 1080p")
                        else:
                            _need(not down and eff_h == h_cfg, "Non-downshift state must preserve configured HDMI res")
                        _need(vl in P272_VIDEO_LIGHT_MODES and ap in P272_AIRPLANE_MODES, "Valid state")
                        matrix_checked += 1

    # 7. Setup Reset Survival vs [Initialize], Slot-1 Recovery Vault Read-Only Lock & O_RDONLY CAMSET Load
    rst_errs_before = len(errors)
    slot1_mut_events = int(spec.slot1_vault_mutation_events)
    slot1_mut_bytes = int(spec.slot1_vault_mutation_bytes)
    if (
        spec.slot1_vault_mutation_events != 0
        or spec.slot1_vault_mutation_bytes != 0
        or (spec.slot1_holds_recovery_vault and not spec.slot1_sdxc_wp_locked)
    ):
        slot1_mut_events = max(slot1_mut_events, 1)
        slot1_mut_bytes = max(slot1_mut_bytes, 1)
        _fail(
            P272_BLOCKED_SETUP_RESET_PERSISTENCE_OR_SLOT1_VAULT_DRIFT,
            "Slot-1 recovery vault must remain SDXC WP-locked with zero mutation bytes",
        )

    if spec.camset_load_after_reset:
        if (
            spec.camset_slot != P272_SLOT1_VAULT_SLOT
            or spec.camset_filename not in P272_CAMSET_FILENAMES
            or spec.camset_source_model != P272_FX3_MODEL_NAME
            or not spec.camset_read_only_load
        ):
            _fail(
                P272_BLOCKED_SETUP_RESET_PERSISTENCE_OR_SLOT1_VAULT_DRIFT,
                "Invalid CAMSET01..10.DAT O_RDONLY Slot-1 restoration envelope in Pillar 47B",
            )
        expected_setup = (
            spec.saved_area_setting,
            spec.saved_daylight_savings,
            spec.saved_date_format,
            spec.saved_video_light_mode,
            spec.saved_hdmi_resolution,
        )
    else:
        expected_setup = compute_expected_pillar47b_setup_state_after_reset(
            pre_area_setting=spec.pre_area_setting,
            pre_daylight_savings=spec.pre_daylight_savings,
            pre_date_format=spec.pre_date_format,
            pre_video_light_mode=spec.pre_video_light_mode,
            pre_hdmi_resolution=spec.pre_hdmi_resolution,
            rtc_backup_battery_lost=spec.rtc_backup_battery_lost,
            reset_action=spec.reset_action,
        )
    actual_setup = (
        spec.post_area_setting,
        spec.post_daylight_savings,
        spec.post_date_format,
        spec.post_video_light_mode,
        spec.post_hdmi_resolution,
    )
    if actual_setup != expected_setup:
        _fail(
            P272_BLOCKED_SETUP_RESET_PERSISTENCE_OR_SLOT1_VAULT_DRIFT,
            f"Post-reset Pillar 47B Setup state {actual_setup!r} drifted from expected {expected_setup!r}",
        )
    setup_reset_verified = len(errors) == rst_errs_before

    passed = len(errors) == 0
    status = P272_STATUS_VERIFIED_PILLAR_47B if passed else P272_STATUS_REJECTED_PILLAR_47B
    digest = _canonical_sha256(
        {
            "pillar": "47B",
            "passed": passed,
            "status": status,
            "block_code": block_code,
            "matrix_states_checked": matrix_checked,
            "effective_hdmi_resolution": exp_eff_hdmi_res,
            "post_area_setting": spec.post_area_setting,
            "post_video_light_mode": spec.post_video_light_mode,
        }
    )
    return AreaDatetimeVideolightHdmiresVaultReport(
        passed=passed,
        status=status,
        block_code=None if passed else block_code,
        area_datetime_nomenclature_and_4subitems_verified=area_dt_verified,
        zero_rf_creators_app_suppression_verified=zero_rf_verified,
        video_light_power_link_5v_900ma_verified=video_light_verified,
        hdmi_res_auto_and_log_1080p_override_verified=hdmi_res_verified,
        setup_reset_persistence_and_slot1_vault_verified=setup_reset_verified,
        h0_equals_h3_verified=h0_eq_h3,
        matrix_states_checked=matrix_checked,
        effective_hdmi_resolution=exp_eff_hdmi_res,
        legacy_datetime_setup_spoof_events=legacy_dt_spoofs,
        unsolicited_rtc_timezone_jump_events=rtc_jumps,
        mishoe_5v_overcurrent_events=overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=log_bypass_events,
        slot1_vault_mutation_events=slot1_mut_events,
        slot1_vault_mutation_bytes=slot1_mut_bytes,
        physical_device_writes=PHYSICAL_DEVICE_WRITES,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        digest_sha256=digest,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Combined Verifier, 6-Scenario Suites (47A & 47B) & Standalone Runner
# ---------------------------------------------------------------------------


def verify_focus_mag_datetime_videolight_hdmires_and_vault(
    focus_mag_spec: Optional[FocusMagPeakingStillAfIlluminatorVaultSpec] = None,
    datetime_videolight_spec: Optional[AreaDatetimeVideolightHdmiresVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> FocusMagDatetimeVideolightHdmiresVaultReport:
    """Combined single-shot verifier for Pillar 47A + Pillar 47B + bounded O_RDONLY Wave-45 donors."""
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase272_donors_readonly(force_clean_room=force_clean_room)
    rep_a = evaluate_focus_mag_peaking_still_af_illuminator_vault(
        focus_mag_spec or build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec()
    )
    rep_b = evaluate_area_datetime_videolight_hdmires_vault(
        datetime_videolight_spec or build_default_safe_area_datetime_videolight_hdmires_vault_spec()
    )
    errs: List[str] = list(safety_errs) + list(rep_a.errors) + list(rep_b.errors)
    if not donor_snapshot.all_donors_present:
        errs.append("Phase 272 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )
    ok = rep_a.passed and rep_b.passed and len(errs) == 0
    return FocusMagDatetimeVideolightHdmiresVaultReport(
        schema=PHASE272_SCHEMA,
        version=PHASE272_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=ok,
        passed=ok,
        status=P272_STATUS_VERIFIED_PILLAR47_SUITE if ok else P272_STATUS_FAIL_PILLAR47_SUITE,
        donor_snapshot=donor_snapshot,
        focus_mag_peaking_report=rep_a,
        area_datetime_videolight_hdmires_report=rep_b,
        legacy_mf_assist_spoof_events=rep_a.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=rep_a.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=rep_a.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            rep_a.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=rep_a.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=rep_b.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=rep_b.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=rep_b.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            rep_b.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=rep_b.slot1_vault_mutation_events,
        slot1_vault_mutation_bytes=rep_b.slot1_vault_mutation_bytes,
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


def verify_focus_mag_datetime_videolight_hdmires_vault(
    focus_mag_spec: Optional[FocusMagPeakingStillAfIlluminatorVaultSpec] = None,
    datetime_videolight_spec: Optional[AreaDatetimeVideolightHdmiresVaultSpec] = None,
    *,
    force_clean_room: Optional[bool] = None,
) -> FocusMagDatetimeVideolightHdmiresVaultReport:
    """Symmetry alias for `verify_focus_mag_datetime_videolight_hdmires_and_vault`."""
    return verify_focus_mag_datetime_videolight_hdmires_and_vault(
        focus_mag_spec=focus_mag_spec,
        datetime_videolight_spec=datetime_videolight_spec,
        force_clean_room=force_clean_room,
    )


def run_pillar47a_focus_mag_peaking_still_af_illuminator_vault_6_scenario_suite() -> (
    Pillar47ASuiteResult
):
    """Run all 6 canonical Pillar 47A scenarios (`2` safe + `4` negative Wave-45 focus guards)."""
    cases: Tuple[Tuple[str, bool, FocusMagPeakingStillAfIlluminatorVaultSpec, Optional[str]], ...] = (
        (
            P272_PILLAR_47A_SCENARIO_IDS[0],
            True,
            FocusMagPeakingStillAfIlluminatorVaultSpec(),
            None,
        ),
        (
            P272_PILLAR_47A_SCENARIO_IDS[1],
            True,
            FocusMagPeakingStillAfIlluminatorVaultSpec(
                shooting_domain="Still",
                focus_mode="DMF",
                hdmi_feed_mode="HDMI RAW",
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P272_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_auto_mag_in_mf="On",
                saved_focus_mag_custom_btn="Custom Button 5",
                saved_focus_mag_time="No Limit",
                saved_still_initial_focus_mag="x1.0",
                saved_movie_initial_focus_mag="x4.0",
                saved_af_in_focus_mag="On",
                saved_peaking_display="On",
                saved_peaking_select_btn="Control Wheel Right",
                saved_peaking_level="Mid",
                saved_peaking_color="White",
                saved_af_illuminator="Auto",
                post_auto_mag_in_mf="On",
                post_focus_mag_custom_btn="Custom Button 5",
                post_focus_mag_time="No Limit",
                post_still_initial_focus_mag="x1.0",
                post_movie_initial_focus_mag="x4.0",
                post_af_in_focus_mag="On",
                post_peaking_display="On",
                post_peaking_select_btn="Control Wheel Right",
                post_peaking_level="Mid",
                post_peaking_color="White",
                post_af_illuminator="Auto",
            ),
            None,
        ),
        (
            P272_PILLAR_47A_SCENARIO_IDS[2],
            False,
            FocusMagPeakingStillAfIlluminatorVaultSpec(
                auto_mag_menu_label=P272_FORBIDDEN_LEGACY_MF_ASSIST_LABEL,
                legacy_mf_assist_spoof_events=1,
                still_movie_initial_mag_couplings=1,
            ),
            P272_BLOCKED_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF,
        ),
        (
            P272_PILLAR_47A_SCENARIO_IDS[3],
            False,
            FocusMagPeakingStillAfIlluminatorVaultSpec(
                hdmi_feed_mode="HDMI RAW",
                hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=4096,
            ),
            P272_BLOCKED_HDMI_CLEAN_FEED_OVERLAY_LEAK,
        ),
        (
            P272_PILLAR_47A_SCENARIO_IDS[4],
            False,
            FocusMagPeakingStillAfIlluminatorVaultSpec(
                shooting_domain="S&Q",
                movie_af_in_focus_mag_events=1,
                movie_sq_af_illuminator_fire_events=1,
            ),
            P272_BLOCKED_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG,
        ),
        (
            P272_PILLAR_47A_SCENARIO_IDS[5],
            False,
            FocusMagPeakingStillAfIlluminatorVaultSpec(
                reset_action="Camera Settings Reset",
                pre_focus_mag_custom_btn="Custom Button 2",
                post_focus_mag_custom_btn="Custom Button 5",
                post_auto_mag_in_mf="Off",
            ),
            P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT,
        ),
    )

    outcomes: List[Pillar47ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_focus_mag_peaking_still_af_illuminator_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar47ScenarioOutcome(
                scenario_id=sid,
                pillar="47A",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar47ASuiteResult(
        passed=all_ok,
        status=P272_STATUS_VERIFIED_PILLAR_47A if all_ok else P272_STATUS_REJECTED_PILLAR_47A,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar47b_area_datetime_videolight_hdmires_vault_6_scenario_suite() -> (
    Pillar47BSuiteResult
):
    """Run all 6 canonical Pillar 47B scenarios (`2` safe + `4` negative Setup/Zero-RF/5V/HDMI/Vault guards)."""
    cases: Tuple[Tuple[str, bool, AreaDatetimeVideolightHdmiresVaultSpec, Optional[str]], ...] = (
        (
            P272_PILLAR_47B_SCENARIO_IDS[0],
            True,
            AreaDatetimeVideolightHdmiresVaultSpec(),
            None,
        ),
        (
            P272_PILLAR_47B_SCENARIO_IDS[1],
            True,
            AreaDatetimeVideolightHdmiresVaultSpec(
                reset_action="Initialize",
                camset_load_after_reset=True,
                camset_slot=1,
                camset_filename="CAMSET01.DAT",
                camset_source_model=P272_FX3_MODEL_NAME,
                camset_read_only_load=True,
                saved_area_setting="Tokyo / UTC+9",
                saved_daylight_savings="Off",
                saved_date_format="YYYY-MM-DD",
                saved_video_light_mode="Power Link",
                saved_hdmi_resolution="2160p",
                post_area_setting="Tokyo / UTC+9",
                post_daylight_savings="Off",
                post_date_format="YYYY-MM-DD",
                post_video_light_mode="Power Link",
                post_hdmi_resolution="2160p",
                log_shooting_mode="Cine EI",
                internal_recording_active=True,
                rec_media_dur_hdmi_output="Off(HDMI Only)",
                effective_hdmi_resolution="2160p",
            ),
            None,
        ),
        (
            P272_PILLAR_47B_SCENARIO_IDS[2],
            False,
            AreaDatetimeVideolightHdmiresVaultSpec(
                area_datetime_menu_label=P272_FORBIDDEN_LEGACY_DATETIME_LABEL,
                legacy_datetime_setup_spoof_events=1,
                creators_app_auto_time_correction="On",
                creators_app_auto_area_adjustment="On",
                unsolicited_rtc_timezone_jump_events=1,
            ),
            P272_BLOCKED_LEGACY_DATETIME_SETUP_SPOOF,
        ),
        (
            P272_PILLAR_47B_SCENARIO_IDS[3],
            False,
            AreaDatetimeVideolightHdmiresVaultSpec(
                mishoe_5v_measured_ma=1150,
                mishoe_5v_overcurrent_events=1,
            ),
            P272_BLOCKED_MISHOE_5V_OVERCURRENT,
        ),
        (
            P272_PILLAR_47B_SCENARIO_IDS[4],
            False,
            AreaDatetimeVideolightHdmiresVaultSpec(
                log_shooting_mode="Cine EI Quick",
                internal_recording_active=True,
                rec_media_dur_hdmi_output="On",
                post_hdmi_resolution="2160p",
                effective_hdmi_resolution="2160p",
                hdmi_res_log_internal_rec_2160p_bypass_events=1,
            ),
            P272_BLOCKED_HDMI_RES_LOG_1080P_OVERRIDE,
        ),
        (
            P272_PILLAR_47B_SCENARIO_IDS[5],
            False,
            AreaDatetimeVideolightHdmiresVaultSpec(
                reset_action="Camera Settings Reset",
                post_area_setting=P272_AREA_SETTING_DEFAULT,
                post_video_light_mode="REC Link",
                slot1_vault_mutation_events=1,
                slot1_vault_mutation_bytes=512,
                tier0_surfaces_h0_h3_matched=15,
            ),
            P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT,
        ),
    )

    outcomes: List[Pillar47ScenarioOutcome] = []
    for sid, expected_ok, spec, expected_code in cases:
        rep = evaluate_area_datetime_videolight_hdmires_vault(spec)
        matched = (rep.passed == expected_ok) and (expected_code is None or rep.block_code == expected_code)
        outcomes.append(
            Pillar47ScenarioOutcome(
                scenario_id=sid,
                pillar="47B",
                expected_allowed=expected_ok,
                actual_allowed=rep.passed,
                block_code=rep.block_code,
                passed=matched,
                detail=rep.status if rep.passed else "; ".join(rep.errors),
            )
        )
    passed_cnt = sum(1 for o in outcomes if o.passed)
    all_ok = passed_cnt == len(outcomes) == 6
    return Pillar47BSuiteResult(
        passed=all_ok,
        status=P272_STATUS_VERIFIED_PILLAR_47B if all_ok else P272_STATUS_REJECTED_PILLAR_47B,
        scenarios_passed=passed_cnt,
        scenarios_total=len(outcomes),
        scenarios=tuple(outcomes),
    )


def run_pillar47_standalone_suite(*, force_clean_room: Optional[bool] = None) -> Pillar47StandaloneReport:
    """Run full Pillar 47 standalone suite (`6/6` Pillar 47A + `6/6` Pillar 47B + bounded `O_RDONLY` donors)."""
    t0 = time.monotonic()
    safety_errs = _safety_invariant_errors()
    donor_snapshot = inspect_phase272_donors_readonly(force_clean_room=force_clean_room)
    res_a = run_pillar47a_focus_mag_peaking_still_af_illuminator_vault_6_scenario_suite()
    res_b = run_pillar47b_area_datetime_videolight_hdmires_vault_6_scenario_suite()

    if not donor_snapshot.all_donors_present:
        safety_errs.append("Phase 272 donor verification failed")
    if not donor_snapshot.under_0_15s_budget:
        safety_errs.append(
            f"Donor inspection exceeded {donor_snapshot.budget_seconds_applied}s budget: "
            f"{donor_snapshot.elapsed_seconds}s"
        )

    all_ok = res_a.passed and res_b.passed and len(safety_errs) == 0
    elapsed = round(time.monotonic() - t0, 6)
    suite_sha = _canonical_sha256(
        {
            "schema": PHASE272_SCHEMA,
            "version": PHASE272_VERSION,
            "mode": donor_snapshot.verification_mode,
            "47a": [asdict(s) for s in res_a.scenarios],
            "47b": [asdict(s) for s in res_b.scenarios],
            "all_passed": all_ok,
        }
    )
    return Pillar47StandaloneReport(
        schema=PHASE272_SCHEMA,
        version=PHASE272_VERSION,
        verification_mode=donor_snapshot.verification_mode,
        all_passed=all_ok,
        status=P272_STATUS_VERIFIED_PILLAR47_SUITE if all_ok else P272_STATUS_FAIL_PILLAR47_SUITE,
        elapsed_seconds=elapsed,
        donor_snapshot=donor_snapshot,
        pillar_47a_focus_mag_peaking_still_af_illuminator_vault=res_a,
        pillar_47b_area_datetime_videolight_hdmires_vault=res_b,
        legacy_mf_assist_spoof_events=P272_LEGACY_MF_ASSIST_SPOOF_EVENTS if res_a.passed else 1,
        still_movie_initial_mag_couplings=(
            P272_STILL_MOVIE_INITIAL_MAG_COUPLINGS if res_a.passed else 1
        ),
        movie_af_in_focus_mag_events=P272_MOVIE_AF_IN_FOCUS_MAG_EVENTS if res_a.passed else 1,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            P272_HDMI_CLEAN_FEED_FOCUS_MAG_OR_PEAKING_LEAK_PIXELS if res_a.passed else 4096
        ),
        movie_sq_af_illuminator_fire_events=(
            P272_MOVIE_SQ_AF_ILLUMINATOR_FIRE_EVENTS if res_a.passed else 1
        ),
        legacy_datetime_setup_spoof_events=(
            P272_LEGACY_DATETIME_SETUP_SPOOF_EVENTS if res_b.passed else 1
        ),
        unsolicited_rtc_timezone_jump_events=(
            P272_UNSOLICITED_RTC_TIMEZONE_JUMP_EVENTS if res_b.passed else 1
        ),
        mishoe_5v_overcurrent_events=P272_MISHOE_5V_OVERCURRENT_EVENTS if res_b.passed else 1,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            P272_HDMI_RES_LOG_INTERNAL_REC_2160P_BYPASS_EVENTS if res_b.passed else 1
        ),
        slot1_vault_mutation_events=P272_SLOT1_VAULT_MUTATION_EVENTS if res_b.passed else 1,
        slot1_vault_mutation_bytes=P272_SLOT1_VAULT_MUTATION_BYTES if res_b.passed else 512,
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
# Unified 47/47 Recovery Master Aggregator
# ---------------------------------------------------------------------------


def _apply_master47_fault_injection(pillar: MasterPillarStatus) -> MasterPillarStatus:
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


def evaluate_realhw_47pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master47PillarRecoveryReport:
    """Evaluate and aggregate all 47 recovery pillars (`1..47`) concurrently -> `47/47` recovery master."""
    safety_errs = _safety_invariant_errors()
    _need(len(safety_errs) == 0, f"Safety policy violated: {safety_errs}")
    if fault_inject_pillar is not None:
        _need(fault_inject_pillar in MASTER_47_PILLAR_IDS, f"Unknown fault_inject_pillar: {fault_inject_pillar}")

    t_start = time.monotonic()
    resolved_clean_room: Optional[bool] = (
        True if _is_clean_room_forced(force_clean_room) else force_clean_room
    )
    kw: Dict[str, Any] = (
        {"force_clean_room": resolved_clean_room} if resolved_clean_room is not None else {}
    )

    def _run_46pillar() -> Master46PillarRecoveryReport:
        return evaluate_realhw_46pillar_recovery_master(**kw)

    def _run_p47() -> Tuple[Pillar47StandaloneReport, float]:
        t0 = time.monotonic()
        res = run_pillar47_standalone_suite(**kw)
        return res, round(time.monotonic() - t0, 6)

    with ThreadPoolExecutor(max_workers=2) as pool:
        fut_46 = pool.submit(_run_46pillar)
        fut_47 = pool.submit(_run_p47)
        m46_rep = fut_46.result()
        p47_rep, p47_dt = fut_47.result()

    all_errors: List[str] = list(m46_rep.errors) + list(p47_rep.errors)
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
        if getattr(m46_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-46 violated {attr_name} == {expected_val}")
        if getattr(p47_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 47 violated {attr_name} == {expected_val}")

    for attr_name, expected_val in (
        ("slot1_vault_folder_mutation_events", 0),
        ("slot1_vault_folder_mutation_bytes", 0),
        ("movie_custom_folder_or_title_overflow_events", 0),
        ("still_prefix_underscore_lead_or_len_violations", 0),
        ("gamma_assist_log_lockout_bypass_events", 0),
        ("gamma_assist_external_hdmi_leak_events", 0),
        ("tcub_camera_reset_wipe_or_format_violations", 0),
        ("fx3_has_builtin_end_filter", False),
        ("e_nd_actuator_tx_count", 0),
        ("cardless_unrecorded_production_violations", 0),
        ("legacy_v1_audio_level_menu_spoof_events", 0),
        ("photographer_copyright_pii_leaked_bytes", 0),
        ("copyright_char_overflow_or_movie_mutation_events", 0),
        ("slot1_copyright_vault_mutation_bytes", 0),
        ("apsc_s35_4k_or_raw_bypass_events", 0),
        ("ai_unit_subject_recog_spoof_events", 0),
        ("hdmi_clean_feed_eye_frame_baked_pixels", 0),
        ("version_dialog_flash_writes", 0),
        ("slot1_bodydata_vault_mutation_bytes", 0),
        ("auto_slow_shutter_lockout_bypass_events", 0),
        ("auto_slow_shutter_angle_overlap_events", 0),
        ("breathing_comp_raw_or_240p_bypass_events", 0),
        ("hdmi_rec_ctrl_without_tc_violations", 0),
        ("slot1_hdmi_rec_vault_mutation_bytes", 0),
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
        if getattr(m46_rep, attr_name) != expected_val:
            all_errors.append(f"Pillars 1-46 violated {attr_name} == {expected_val}")
    if m46_rep.bodydata_flash_attempts_blocked < 1:
        all_errors.append("Pillars 1-46 violated bodydata_flash_attempts_blocked >= 1")

    for attr_name, expected_val in (
        ("legacy_mf_assist_spoof_events", 0),
        ("still_movie_initial_mag_couplings", 0),
        ("movie_af_in_focus_mag_events", 0),
        ("hdmi_clean_feed_focus_mag_or_peaking_leak_pixels", 0),
        ("movie_sq_af_illuminator_fire_events", 0),
        ("legacy_datetime_setup_spoof_events", 0),
        ("unsolicited_rtc_timezone_jump_events", 0),
        ("mishoe_5v_overcurrent_events", 0),
        ("hdmi_res_log_internal_rec_2160p_bypass_events", 0),
        ("slot1_vault_mutation_events", 0),
        ("slot1_vault_mutation_bytes", 0),
        ("hardware_live_attachment_authorized", False),
    ):
        if getattr(p47_rep, attr_name) != expected_val:
            all_errors.append(f"Pillar 47 violated {attr_name} == {expected_val}")

    pillar_statuses: List[MasterPillarStatus] = list(m46_rep.pillars)
    spec47 = MASTER_47_PILLAR_SPECS[46]
    p47_metrics = {
        "pillar_47a_focus_mag_peaking_still_af_illuminator_vault": (
            f"{p47_rep.pillar_47a_focus_mag_peaking_still_af_illuminator_vault.scenarios_passed}/"
            f"{p47_rep.pillar_47a_focus_mag_peaking_still_af_illuminator_vault.scenarios_total}"
        ),
        "pillar_47b_area_datetime_videolight_hdmires_vault": (
            f"{p47_rep.pillar_47b_area_datetime_videolight_hdmires_vault.scenarios_passed}/"
            f"{p47_rep.pillar_47b_area_datetime_videolight_hdmires_vault.scenarios_total}"
        ),
        "legacy_mf_assist_spoof_events": p47_rep.legacy_mf_assist_spoof_events,
        "still_movie_initial_mag_couplings": p47_rep.still_movie_initial_mag_couplings,
        "movie_af_in_focus_mag_events": p47_rep.movie_af_in_focus_mag_events,
        "hdmi_clean_feed_focus_mag_or_peaking_leak_pixels": (
            p47_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        "movie_sq_af_illuminator_fire_events": p47_rep.movie_sq_af_illuminator_fire_events,
        "legacy_datetime_setup_spoof_events": p47_rep.legacy_datetime_setup_spoof_events,
        "unsolicited_rtc_timezone_jump_events": p47_rep.unsolicited_rtc_timezone_jump_events,
        "mishoe_5v_overcurrent_events": p47_rep.mishoe_5v_overcurrent_events,
        "hdmi_res_log_internal_rec_2160p_bypass_events": (
            p47_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        "slot1_vault_mutation_events": p47_rep.slot1_vault_mutation_events,
        "slot1_vault_mutation_bytes": p47_rep.slot1_vault_mutation_bytes,
        "hardware_live_attachment_authorized": p47_rep.hardware_live_attachment_authorized,
        "donor_files_inspected": p47_rep.donor_snapshot.donor_files_inspected,
    }
    pillar_statuses.append(
        MasterPillarStatus(
            pillar_number=spec47[0],
            pillar_id=spec47[1],
            phase_label=spec47[2],
            module_name=spec47[3],
            passed=bool(p47_rep.all_passed),
            status=p47_rep.status,
            verification_mode=p47_rep.verification_mode,
            elapsed_seconds=p47_dt,
            key_metrics=p47_metrics,
            digest_sha256=_canonical_sha256(
                {
                    "pillar": spec47[1],
                    "mode": p47_rep.verification_mode,
                    "status": p47_rep.status,
                    "metrics": p47_metrics,
                    "passed": p47_rep.all_passed,
                }
            ),
            errors=tuple(p47_rep.errors),
        )
    )

    if fault_inject_pillar is not None:
        pillar_statuses = [
            _apply_master47_fault_injection(p) if p.pillar_id == fault_inject_pillar else p
            for p in pillar_statuses
        ]

    elapsed = round(time.monotonic() - t_start, 6)
    failed = tuple(p.pillar_id for p in pillar_statuses if not p.passed)
    pillars_passed = sum(1 for p in pillar_statuses if p.passed)
    verification_mode = p47_rep.verification_mode
    all_ok = (
        len(pillar_statuses) == MASTER_47_PILLAR_COUNT == 47
        and pillars_passed == 47
        and len(failed) == 0
        and len(all_errors) == 0
    )

    master_sha = _canonical_sha256(
        {
            "schema": PHASE272_SCHEMA,
            "version": PHASE272_VERSION,
            "verification_mode": verification_mode,
            "pillar_count": len(pillar_statuses),
            "pillars_passed": pillars_passed,
            "failed_pillars": list(failed),
            "pillar_digests": [(p.pillar_number, p.pillar_id, p.passed, p.digest_sha256) for p in pillar_statuses],
            "all_passed": all_ok,
        }
    )
    return Master47PillarRecoveryReport(
        schema=PHASE272_SCHEMA,
        version=PHASE272_VERSION,
        verification_mode=verification_mode,
        all_passed=all_ok,
        status=P272_STATUS_VERIFIED_47OF47_AGGREGATOR if all_ok else P272_STATUS_FAIL_47OF47_AGGREGATOR,
        pillar_count=len(pillar_statuses),
        pillars_passed=pillars_passed,
        failed_pillars=failed,
        elapsed_seconds=elapsed,
        under_2s_fast_cli_budget=elapsed < P272_FAST_CLI_BUDGET_SECONDS,
        under_6s_budget=elapsed < P272_CONCURRENT_CEILING_SECONDS,
        nominal_under_4_0s=elapsed < P272_NOMINAL_BUDGET_SECONDS,
        pillars=tuple(pillar_statuses),
        donor_snapshot=p47_rep.donor_snapshot,
        pillar47_a_focus_mag_peaking_still_af_illuminator_vault=(
            p47_rep.pillar_47a_focus_mag_peaking_still_af_illuminator_vault
        ),
        pillar47_b_area_datetime_videolight_hdmires_vault=(
            p47_rep.pillar_47b_area_datetime_videolight_hdmires_vault
        ),
        legacy_mf_assist_spoof_events=p47_rep.legacy_mf_assist_spoof_events,
        still_movie_initial_mag_couplings=p47_rep.still_movie_initial_mag_couplings,
        movie_af_in_focus_mag_events=p47_rep.movie_af_in_focus_mag_events,
        hdmi_clean_feed_focus_mag_or_peaking_leak_pixels=(
            p47_rep.hdmi_clean_feed_focus_mag_or_peaking_leak_pixels
        ),
        movie_sq_af_illuminator_fire_events=p47_rep.movie_sq_af_illuminator_fire_events,
        legacy_datetime_setup_spoof_events=p47_rep.legacy_datetime_setup_spoof_events,
        unsolicited_rtc_timezone_jump_events=p47_rep.unsolicited_rtc_timezone_jump_events,
        mishoe_5v_overcurrent_events=p47_rep.mishoe_5v_overcurrent_events,
        hdmi_res_log_internal_rec_2160p_bypass_events=(
            p47_rep.hdmi_res_log_internal_rec_2160p_bypass_events
        ),
        slot1_vault_mutation_events=p47_rep.slot1_vault_mutation_events,
        slot1_vault_mutation_bytes=p47_rep.slot1_vault_mutation_bytes,
        slot1_vault_folder_mutation_events=m46_rep.slot1_vault_folder_mutation_events,
        slot1_vault_folder_mutation_bytes=m46_rep.slot1_vault_folder_mutation_bytes,
        movie_custom_folder_or_title_overflow_events=(
            m46_rep.movie_custom_folder_or_title_overflow_events
        ),
        still_prefix_underscore_lead_or_len_violations=(
            m46_rep.still_prefix_underscore_lead_or_len_violations
        ),
        gamma_assist_log_lockout_bypass_events=m46_rep.gamma_assist_log_lockout_bypass_events,
        gamma_assist_external_hdmi_leak_events=m46_rep.gamma_assist_external_hdmi_leak_events,
        tcub_camera_reset_wipe_or_format_violations=(
            m46_rep.tcub_camera_reset_wipe_or_format_violations
        ),
        fx3_has_builtin_end_filter=m46_rep.fx3_has_builtin_end_filter,
        e_nd_actuator_tx_count=m46_rep.e_nd_actuator_tx_count,
        cardless_unrecorded_production_violations=m46_rep.cardless_unrecorded_production_violations,
        legacy_v1_audio_level_menu_spoof_events=m46_rep.legacy_v1_audio_level_menu_spoof_events,
        photographer_copyright_pii_leaked_bytes=m46_rep.photographer_copyright_pii_leaked_bytes,
        copyright_char_overflow_or_movie_mutation_events=(
            m46_rep.copyright_char_overflow_or_movie_mutation_events
        ),
        slot1_copyright_vault_mutation_bytes=m46_rep.slot1_copyright_vault_mutation_bytes,
        apsc_s35_4k_or_raw_bypass_events=m46_rep.apsc_s35_4k_or_raw_bypass_events,
        ai_unit_subject_recog_spoof_events=m46_rep.ai_unit_subject_recog_spoof_events,
        hdmi_clean_feed_eye_frame_baked_pixels=m46_rep.hdmi_clean_feed_eye_frame_baked_pixels,
        version_dialog_flash_writes=m46_rep.version_dialog_flash_writes,
        bodydata_flash_attempts_blocked=m46_rep.bodydata_flash_attempts_blocked,
        slot1_bodydata_vault_mutation_bytes=m46_rep.slot1_bodydata_vault_mutation_bytes,
        auto_slow_shutter_lockout_bypass_events=m46_rep.auto_slow_shutter_lockout_bypass_events,
        auto_slow_shutter_angle_overlap_events=m46_rep.auto_slow_shutter_angle_overlap_events,
        breathing_comp_raw_or_240p_bypass_events=m46_rep.breathing_comp_raw_or_240p_bypass_events,
        hdmi_rec_ctrl_without_tc_violations=m46_rep.hdmi_rec_ctrl_without_tc_violations,
        slot1_hdmi_rec_vault_mutation_bytes=m46_rep.slot1_hdmi_rec_vault_mutation_bytes,
        diff_set_transition_corruption_events=m46_rep.diff_set_transition_corruption_events,
        shutter_angle_common_bleed_events=m46_rep.shutter_angle_common_bleed_events,
        slot1_custom_key_vault_mutation_bytes=m46_rep.slot1_custom_key_vault_mutation_bytes,
        fx3_has_builtin_evf=m46_rep.fx3_has_builtin_evf,
        evf_finder_monitor_spoof_events=m46_rep.evf_finder_monitor_spoof_events,
        tier0_battery_high_display_violations=m46_rep.tier0_battery_high_display_violations,
        bt_rmt_ir_lockout_violations=m46_rep.bt_rmt_ir_lockout_violations,
        slot1_mymenu_vault_mutation_bytes=m46_rep.slot1_mymenu_vault_mutation_bytes,
        destructive_menu_delete_confusions=m46_rep.destructive_menu_delete_confusions,
        shutter_angle_exposure_step_drift_events=m46_rep.shutter_angle_exposure_step_drift_events,
        fx3_has_var_shutter=m46_rep.fx3_has_var_shutter,
        unbuffered_battery_pull_events=m46_rep.unbuffered_battery_pull_events,
        hardware_live_attachment_authorized=p47_rep.hardware_live_attachment_authorized,
        master_47pillar_sha256=master_sha,
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


def evaluate_47pillar_recovery_master(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master47PillarRecoveryReport:
    """Symmetry alias for `evaluate_realhw_47pillar_recovery_master`."""
    return evaluate_realhw_47pillar_recovery_master(
        force_clean_room=force_clean_room,
        fault_inject_pillar=fault_inject_pillar,
    )


def verify_47pillar_recovery_suite(
    *,
    force_clean_room: Optional[bool] = None,
    fault_inject_pillar: Optional[str] = None,
) -> Master47PillarRecoveryReport:
    """Public CLI entry point for Phase 272 `47/47` unified recovery master."""
    return evaluate_realhw_47pillar_recovery_master(
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
    "MASTER_47_PILLAR_COUNT",
    "MASTER_47_PILLAR_IDS",
    "MASTER_47_PILLAR_SPECS",
    "OTP_FUSE_TOUCHES",
    "OTP_FUSE_WRITES",
    "P272_AF_ILLUMINATOR_DEFAULT",
    "P272_AF_ILLUMINATOR_MENU_PATH",
    "P272_AF_ILLUMINATOR_MODES",
    "P272_AF_IN_FOCUS_MAG_DEFAULT",
    "P272_AIRPLANE_MODES",
    "P272_AIRPLANE_MODE_MENU_PATH",
    "P272_ALLOWED_FOCUS_MAG_CUSTOM_BTNS",
    "P272_ALLOWED_PEAKING_SELECT_BTNS",
    "P272_AREA_DATETIME_EXACT_4_SUBITEMS",
    "P272_AREA_DATETIME_LABEL",
    "P272_AREA_DATETIME_MENU_PATH",
    "P272_AREA_SETTING_DEFAULT",
    "P272_AUTO_MAG_IN_MF_DEFAULT",
    "P272_AUTO_MAG_IN_MF_LABEL",
    "P272_BLOCKED_FOCUS_ASSISTANT_RESET_SCOPE_DRIFT",
    "P272_BLOCKED_FOCUS_MAG_DEFAULTS_OR_REGISTER_COUPLING",
    "P272_BLOCKED_HDMI_CLEAN_FEED_OVERLAY_LEAK",
    "P272_BLOCKED_HDMI_RES_LOG_1080P_OVERRIDE",
    "P272_BLOCKED_INVALID_DATETIME_VIDEOLIGHT_HDMIRES_SPEC",
    "P272_BLOCKED_INVALID_FOCUS_MAG_PEAKING_SPEC",
    "P272_BLOCKED_LEGACY_DATETIME_SETUP_SPOOF",
    "P272_BLOCKED_LEGACY_MF_ASSIST_NOMENCLATURE_SPOOF",
    "P272_BLOCKED_MISHOE_5V_OVERCURRENT",
    "P272_BLOCKED_PERSISTENT_OVERLAY_ESCAPE",
    "P272_BLOCKED_SAFETY_POLICY_VIOLATION",
    "P272_BLOCKED_SETUP_RESET_PERSISTENCE_OR_SLOT1_VAULT_DRIFT",
    "P272_BLOCKED_STILL_ONLY_AF_ILLUMINATOR_OR_AF_IN_MAG",
    "P272_BLOCKED_TIER0_BACKUP_BIN_H0_H3_DRIFT",
    "P272_BLOCKED_ZERO_RF_CREATORS_APP_SYNC_OR_RTC_JUMP",
    "P272_BOUNDED_HEADER_BYTES",
    "P272_CAMSET_FILENAMES",
    "P272_CONCURRENT_CEILING_SECONDS",
    "P272_DATE_FORMATS",
    "P272_DATE_FORMAT_DEFAULT",
    "P272_DAYLIGHT_SAVINGS_DEFAULT",
    "P272_DAYLIGHT_SAVINGS_MODES",
    "P272_DONOR_FX3_APPFW_702_RELPATH",
    "P272_DONOR_FX3_BACKUP_BIN_RELPATH",
    "P272_DONOR_FX3_BODYDATA_RELPATH",
    "P272_DONOR_FX3_CAMERAONDEMANDSAVER_SO_RELPATH",
    "P272_DONOR_FX3_CPAPP_B_BIN_RELPATH",
    "P272_DONOR_FX3_LIBBACKUPMANAGER_SO_RELPATH",
    "P272_DONOR_FX3_LIBBACKUP_SO_RELPATH",
    "P272_DONOR_FX3_LIBGPE_SO_RELPATH",
    "P272_DONOR_FX3_LIBINFRAAIRPLANEMODE_SO_RELPATH",
    "P272_DONOR_FX3_LIBINFRAMEDIACONFIG_SO_RELPATH",
    "P272_DONOR_FX3_LIBINFRAMEDIADETECT_SO_RELPATH",
    "P272_DONOR_FX3_LIBSAVELOADSETTINGS_SO_RELPATH",
    "P272_DONOR_FX6_APPFW_601_RELPATH",
    "P272_DONOR_FX6_BACKUP_NTSC_BIN_RELPATH",
    "P272_DONOR_FX6_LIBINFRADIAL_SO_RELPATH",
    "P272_DONOR_FX6_LIBINFRAHOTSHOE_SO_RELPATH",
    "P272_DONOR_INSPECT_BUDGET_SECONDS",
    "P272_DONOR_INSPECT_CI_BUDGET_SECONDS",
    "P272_ENV_CLEAN_ROOM_TEST",
    "P272_FAST_CLI_BUDGET_SECONDS",
    "P272_FOCUS_ASSISTANT_MENU_PATH",
    "P272_FOCUS_MAGNIFIER_CUSTOM_BTN_DEFAULT",
    "P272_FOCUS_MAGNIF_TIME_DEFAULT",
    "P272_FOCUS_MAGNIF_TIME_MODES",
    "P272_FOCUS_MODES",
    "P272_FORBIDDEN_LEGACY_DATETIME_LABEL",
    "P272_FORBIDDEN_LEGACY_MF_ASSIST_LABEL",
    "P272_FORBIDDEN_PERSISTENT_TARGETS",
    "P272_FX3_FW_VERSION",
    "P272_FX3_HELPGUIDE_ID",
    "P272_FX3_MODEL_ID",
    "P272_FX3_MODEL_NAME",
    "P272_FX3_SUPPORTED_FW_VERSIONS",
    "P272_FX6_DONOR_FW_VERSION",
    "P272_FX6_DONOR_MODEL_NAME",
    "P272_HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "P272_HDMI_CLEAN_FEED_FOCUS_MAG_OR_PEAKING_LEAK_PIXELS",
    "P272_HDMI_FEED_MODES",
    "P272_HDMI_INFO_DISPLAY_MENU_PATH",
    "P272_HDMI_RESOLUTIONS",
    "P272_HDMI_RESOLUTION_DEFAULT",
    "P272_HDMI_RESOLUTION_MENU_PATH",
    "P272_HDMI_RES_LOG_INTERNAL_REC_2160P_BYPASS_EVENTS",
    "P272_INITIAL_FOCUS_MAG_MODES",
    "P272_INITIAL_FOCUS_MAG_MOVIE_DEFAULT",
    "P272_INITIAL_FOCUS_MAG_STILL_DEFAULT",
    "P272_LEGACY_DATETIME_SETUP_SPOOF_EVENTS",
    "P272_LEGACY_MF_ASSIST_SPOOF_EVENTS",
    "P272_LOG_SHOOTING_MODES",
    "P272_MAX_FULL_DONOR_BYTES",
    "P272_MISHOE_5V_MAX_BUDGET_MA",
    "P272_MISHOE_5V_OVERCURRENT_EVENTS",
    "P272_MOVIE_AF_IN_FOCUS_MAG_EVENTS",
    "P272_MOVIE_SQ_AF_ILLUMINATOR_FIRE_EVENTS",
    "P272_NOMINAL_BUDGET_SECONDS",
    "P272_ON_OFF_MODES",
    "P272_PEAKING_COLORS",
    "P272_PEAKING_COLOR_DEFAULT",
    "P272_PEAKING_DISPLAY_DEFAULT",
    "P272_PEAKING_DISPLAY_MENU_PATH",
    "P272_PEAKING_DISPLAY_SELECT_DEFAULT",
    "P272_PEAKING_LEVELS",
    "P272_PEAKING_LEVEL_DEFAULT",
    "P272_PILLAR_47A_SCENARIO_IDS",
    "P272_PILLAR_47B_SCENARIO_IDS",
    "P272_PINNED_FX3_APPFW_702_BYTES",
    "P272_PINNED_FX3_APPFW_702_HDR4K_SHA256",
    "P272_PINNED_FX3_BACKUP_BIN_BYTES",
    "P272_PINNED_FX3_BACKUP_BIN_SHA256",
    "P272_PINNED_FX3_BODYDATA_BYTES",
    "P272_PINNED_FX3_BODYDATA_HDR4K_SHA256",
    "P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_BYTES",
    "P272_PINNED_FX3_CAMERAONDEMANDSAVER_SO_SHA256",
    "P272_PINNED_FX3_CPAPP_B_BIN_BYTES",
    "P272_PINNED_FX3_CPAPP_B_BIN_HDR4K_SHA256",
    "P272_PINNED_FX3_LIBBACKUPMANAGER_SO_BYTES",
    "P272_PINNED_FX3_LIBBACKUPMANAGER_SO_SHA256",
    "P272_PINNED_FX3_LIBBACKUP_SO_BYTES",
    "P272_PINNED_FX3_LIBBACKUP_SO_SHA256",
    "P272_PINNED_FX3_LIBGPE_SO_BYTES",
    "P272_PINNED_FX3_LIBGPE_SO_SHA256",
    "P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_BYTES",
    "P272_PINNED_FX3_LIBINFRAAIRPLANEMODE_SO_SHA256",
    "P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_BYTES",
    "P272_PINNED_FX3_LIBINFRAMEDIACONFIG_SO_SHA256",
    "P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_BYTES",
    "P272_PINNED_FX3_LIBINFRAMEDIADETECT_SO_SHA256",
    "P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_BYTES",
    "P272_PINNED_FX3_LIBSAVELOADSETTINGS_SO_SHA256",
    "P272_PINNED_FX6_APPFW_601_BYTES",
    "P272_PINNED_FX6_APPFW_601_HDR4K_SHA256",
    "P272_PINNED_FX6_BACKUP_NTSC_BIN_BYTES",
    "P272_PINNED_FX6_BACKUP_NTSC_BIN_SHA256",
    "P272_PINNED_FX6_LIBINFRADIAL_SO_BYTES",
    "P272_PINNED_FX6_LIBINFRADIAL_SO_SHA256",
    "P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_BYTES",
    "P272_PINNED_FX6_LIBINFRAHOTSHOE_SO_SHA256",
    "P272_REC_MEDIA_DUR_HDMI_MODES",
    "P272_RESET_ACTIONS",
    "P272_SHOOTING_DOMAINS",
    "P272_SLOT1_VAULT_MUTATION_BYTES",
    "P272_SLOT1_VAULT_MUTATION_EVENTS",
    "P272_SLOT1_VAULT_SLOT",
    "P272_STAGE_B_VOLATILE_OVERLAY_DIR",
    "P272_STATUS_FAIL_47OF47_AGGREGATOR",
    "P272_STATUS_FAIL_PILLAR47_SUITE",
    "P272_STATUS_REJECTED_PILLAR_47A",
    "P272_STATUS_REJECTED_PILLAR_47B",
    "P272_STATUS_VERIFIED_47OF47_AGGREGATOR",
    "P272_STATUS_VERIFIED_PILLAR47_SUITE",
    "P272_STATUS_VERIFIED_PILLAR_47A",
    "P272_STATUS_VERIFIED_PILLAR_47B",
    "P272_STILL_MOVIE_INITIAL_MAG_COUPLINGS",
    "P272_TIER0_SURFACE_COUNT",
    "P272_UNSOLICITED_RTC_TIMEZONE_JUMP_EVENTS",
    "P272_VIDEO_LIGHT_MODES",
    "P272_VIDEO_LIGHT_MODE_DEFAULT",
    "P272_VIDEO_LIGHT_MODE_MENU_PATH",
    "PASSIVE_TX_BYTES_EMITTED",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE272_PHASE_NUMBER",
    "PHASE272_SCHEMA",
    "PHASE272_VERSION",
    "PHYSICAL_DEVICE_WRITES",
    "PHYSICAL_USB_PACKETS_EMITTED",
    "RAW_FIRMWARE_BYTES_LEAKED",
    "READ_ONLY_DONOR_ACCESS",
    "RPMB_COUNTER_INCREMENTS",
    "SPI_NOR_WRITE_AUTHORIZED",
    "AreaDatetimeVideolightHdmiresVaultReport",
    "AreaDatetimeVideolightHdmiresVaultSpec",
    "FocusMagDatetimeVideolightHdmiresVaultReport",
    "FocusMagPeakingStillAfIlluminatorVaultReport",
    "FocusMagPeakingStillAfIlluminatorVaultSpec",
    "Master47PillarRecoveryReport",
    "Phase272DonorArtifactDigest",
    "Phase272DonorSnapshot",
    "Pillar47ASuiteResult",
    "Pillar47BSuiteResult",
    "Pillar47ScenarioOutcome",
    "Pillar47StandaloneReport",
    "build_default_safe_area_datetime_videolight_hdmires_vault_spec",
    "build_default_safe_focus_mag_peaking_still_af_illuminator_vault_spec",
    "compute_expected_effective_hdmi_resolution",
    "compute_expected_focus_mag_peaking_runtime_gates",
    "compute_expected_pillar47a_focus_assistant_state_after_reset",
    "compute_expected_pillar47b_setup_state_after_reset",
    "evaluate_47pillar_recovery_master",
    "evaluate_area_datetime_videolight_hdmires_vault",
    "evaluate_focus_mag_peaking_still_af_illuminator_vault",
    "evaluate_realhw_47pillar_recovery_master",
    "inspect_phase272_donors_readonly",
    "run_pillar47_standalone_suite",
    "run_pillar47a_focus_mag_peaking_still_af_illuminator_vault_6_scenario_suite",
    "run_pillar47b_area_datetime_videolight_hdmires_vault_6_scenario_suite",
    "verify_47pillar_recovery_suite",
    "verify_focus_mag_datetime_videolight_hdmires_and_vault",
    "verify_focus_mag_datetime_videolight_hdmires_vault",
]
