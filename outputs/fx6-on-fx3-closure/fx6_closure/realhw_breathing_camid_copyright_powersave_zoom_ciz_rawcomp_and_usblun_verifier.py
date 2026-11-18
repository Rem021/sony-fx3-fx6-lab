"""Phase 334: 16th Real-Hardware Physical Bench & Pre-Shoot Readiness Verifier (Waves 64-65).

Verifies Sony ``ILME-FX3 Ver. 7.02`` (``ilc/2210``, Model ``0x91030080``) vs ``ILME-FX6`` (``Ver. 6.01``)
empirical hardware/firmware/menu invariants across Waves 64-65 before any physical bench session:

1. **Check Group A (Wave 64 §§1-2)** — ``[Breathing Comp.]`` (``120p``/``100p`` & ``Catalyst Prepare`` vs
   free ``Catalyst Browse``) & Movie ``[File Settings]`` (``Cam ID + Reel#`` ``37``-Char Title,
   ``SDHC`` ``4 GB`` Split vs ``exFAT``):
   - ``[Breathing Comp.]`` (``Off`` default, **Resettable** via ``[Camera Settings Reset]`` unlike static
     ``Shading`` / ``Chromatic Aberration`` / ``Distortion Comp.``): electronic CIZ crop, disabled at
     regular Movie ``119.88p / 100p`` (``120p``), ``S&Q >= 100/120fps``, Still, HDMI 16-bit RAW output,
     macro ``SEL100F28GM`` ``0.57..1.0m``, teleconverters ``SEL14TC``/``SEL20TC``, 3rd-party/manual lenses,
     ``Auto Framing``, and CIZ/Digital Zoom coupling (``< 100fps`` S&Q IS allowed on FX3 vs FX6 locking
     ``Off`` for ALL ``S&Q = On``, ``Distortion Comp. = Off``, and ``RAW`` codecs).
   - Post-production metadata breathing comp requires paid ``Catalyst Prepare`` / ``Catalyst Prepare Plugin``
     (NOT free ``Catalyst Browse``) + in-body ``[Distortion Comp.] = Auto``.
   - Movie ``[File Settings]`` (ALL Initialize-only, fixed ``PRIVATE/M4ROOT/CLIP/*.MP4``):
     ``[File Number]`` (``Series``[def] / ``Reset``) + ``[Series Counter Reset]`` (``_f 0x6a52``),
     ``Standard`` / ``Cam ID + Reel#`` (``A..Z`` + ``001..999`` + ``C/L/R`` rollover ``C999->D001`` +
     ``YYMMDD``) / ``Title`` (``<= 37`` chars, def ``"C"``, ``YYYYMMDD`` for ``Date + Title``).
   - ``SDHC`` (``FAT32 <= 32 GB``) forces ``Standard``, splits XAVC S at ``4 GB``, and blocks
     ``Simult. Recording`` mixed with ``exFAT``. Fail-closed ``Slot-1`` Tier-0 Vault ``EROFS (errno 30)``
     firewall on reel/file counter writes, vs FX6 ``TC/Media > Clip Name Format`` (``4..46``-char
     ``Title Prefix`` def ``nnn_``).

2. **Check Group B (Wave 64 §§3-4)** — ``[Copyright Info]`` ``46``-Char Round-57 Errata, Active
   ``[Write Serial Number]``, ``[Power Setting Option]`` 9-Condition Bypass, Dormant
   ``[Power Save by Monitor]`` & ``[NTSC/PAL Selector]`` ``Slot-1`` Format Guard:
   - **Round-57 Errata**: ALL 4 ``[Copyright Info]`` items (``Write Copyright Info`` ``Off``[def],
     ``46``-char ``Set Photographer`` / ``Set Copyright``, ``Disp. Copyright Info``) AND active Still+Movie
     ``[Write Serial Number]`` (``BKID_APP_setting_write_serial_number_still_movie``) resist
     ``[Camera Settings Reset]`` (Initialize-only); ``Copyright Info`` is excluded from ``CAMSET*.DAT``,
     while ``Write Serial Number`` boolean is NOT.
   - ``[Power Setting Option]`` exposes ONLY 2 Initialize-only items: ``[Power Save Start Time]``
     (``Off/30/5[def]/2/1 Min/10 Sec``, 9 bypass conditions) and ``[Auto Power OFF Temp.]``
     (``Standard[def]/High`` tripod-only). ``[Power Save by Monitor]`` is strictly dormant
     (``EOPNOTSUPP=95``) on zero-EVF FX3.
   - ``[NTSC/PAL Selector]`` (Initialize-only, triggers reboot, cross-system playback blocked) retains
     ``base.uxc 0xe1e6..0xe9f6`` format prompts requiring hard ``Slot-1`` Tier-0 Vault ``EROFS=30``
     protection (``slot1_data_sector_writes == 0``).

3. **Check Group C (Wave 65 §§1-2)** — ``[Zoom Range]`` CIZ/Digital, 8-Step Speeds,
   ``[Auto Slow Shutter]`` 6-Lockout, ``[ISO Range Limit]``, Still ``[ISO AUTO Min. SS]`` & Dual Base ISO:
   - Initialize-only ``[Zoom Range]`` (``Optical zoom only``[def] / ``ClearImage Zoom`` [``1.5x`` 4K,
     ``2x`` HD] / ``Digital Zoom`` [``4x`` Movie]) & ``[Zoom Ring Rotate]`` vs Resettable 8-step
     ``[Zoom Lever Speed]`` (``1st=3``, ``2nd=8 Fast`` Standby/Rec), ``[Custom Key Z. Speed]`` (``3``),
     ``[Remote Zoom Speed]`` (``Variable``[def]/``Fixed 3``). CIZ/Digital locked out on RAW / ``120p/100p``
     / ``S&Q >= 100/120fps`` and forces Center AF + Multi Metering (disabling Face/Eye/Tracking), vs FX6
     zero ``Digital Zoom`` + dual physical rockers (``Handle Zoom``).
   - Movie ``[Auto Slow Shutter]`` (``On``[def], Resettable, 6+ lockouts: S&Q, S, M, Manual ISO, Flexible Exp
     Manual Shutter, Cine EI/Quick, + Angle), Initialize-only manual ``[ISO Range Limit]``, Still-only
     Resettable ``[ISO AUTO Min. SS]`` (``SLOWER..FASTER`` / ``1/8000..30"``), and exact Dual Base ISO
     (``Cine EI`` ``800 / 12800``; ``PP11 S-Cinetone`` / ``HLG`` / ``Cine4`` ``100 / 2000``;
     ``PP Off`` ``80 / 1600``) vs FX6 ``Base Sensitivity Low/High`` + ``AGC``.

4. **Check Group D (Wave 65 §§3-4 & Tier-0)** — Dormant ``Lossless Comp`` RAW Myth-Busting,
   ``[HLG Still Image]``, ``[USB LUN Setting] = Single`` ``Slot-1`` Hazard, ``NP-FZ100`` PD Gate,
   Dormant UVC & ``16/16 H0 == H3`` Dual-Media ``528 B FX3RCPT1`` Tier-0 Gate:
   - ``ILME-FX3 Ver. 7.02`` ``[RAW File Type]`` exposes ONLY Resettable ``Compressed``[def] &
     ``Uncompressed`` (``Lossless Comp L/M/S`` ``_f 0x6b56`` is strictly dormant ``EOPNOTSUPP=95``);
     ``[HLG Still Image]`` (``BT.2100``, requires ``HEIF`` + ``P/A/S/M``); ``Sort Recording`` +
     ``Auto Switch Media`` failover onto ``Slot 1`` blocked with ``EROFS=30``.
   - Initialize-only ``[USB Connection Mode]`` (``Sel. When Connect``[def] / ``MassStorage`` / ``MTP`` /
     ``Remote Shooting``); CRITICAL ``[USB LUN Setting] = Single`` exposes ONLY ``Slot 1`` (NOT
     ``Slot 2``!), requiring strict host MSC/Spotlight/``fseventsd``/``fsck`` isolation (``EROFS=30``);
     ``[USB Power Supply]`` requires charged ``NP-FZ100`` (or ``DC-C1`` coupler) unlike FX6 batteryless
     ``19.5V DC IN``; native ``[USB Streaming]`` (``UVC/UAC``) is strictly dormant (``EOPNOTSUPP=95``)
     on BOTH ``FX3 Ver. 7.02`` and ``FX6 Ver. 6.01``.
   - ``16/16 H0 == H3`` + dual-media ``528 B FX3RCPT1`` Tier-0 receipt gate + zero-write redlines.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple, Union

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import is_forced_clean_room, iter_work_roots, resolve_work_subpath
from .realhw_card_insert_readiness_verifier import (
    BODY_SERIAL_RE,
    DONOR_INSPECTION_MAX_SECONDS,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    HEX32_CID_RE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_HEX,
    TARGET_MODEL_ID_INT,
    _is_trivial_hex64,
    build_default_h0_baselines,
)
from .realhw_sd_stageb_bundle_and_uninstaller import SIXTEEN_STORAGE_SURFACES

P334_VERSION = "phase334_v1"
PHASE_334_VERSION = P334_VERSION
P334_SCHEMA = "realhw_preflight16_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_usblun_v1"
P334_SCHEMA_VERSION = P334_SCHEMA
PHASE_334_SCHEMA = P334_SCHEMA
REALHW_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_SCHEMA = P334_SCHEMA
P334_SONY_HELP_GUIDE_ID = "ilc/2210"

P334_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED = (
    "READONLY_PREFLIGHT16_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED"
)
P334_GO_NO_GO_BLOCKED_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_FAILURE = (
    "BLOCKED_PREFLIGHT16_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_FAILURE"
)
PHASE_334_VALID_GO_NO_GO_VALUES = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED,
    P334_GO_NO_GO_BLOCKED_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_FAILURE,
)

# Bounded donor paths (read-only O_RDONLY)
P334_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    (
        "fx6_appfw_so",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so",
    ),
    (
        "fx3_im_elf",
        "sony-firmware-20261024/stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/bin/im.elf",
    ),
    (
        "fx3_libjiritsu_so",
        "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so",
    ),
    (
        "fx3_libusbbuspower_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so",
    ),
    (
        "fx3_upm_ko",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko",
    ),
)
P334_HEADER_READ_BYTES = 64

# Unconditional safety / zero-leak constants
PHASE334_RAW_FIRMWARE_BYTES_LEAKED = 0
PHASE334_PASSIVE_TX_BYTES_EMITTED = 0
PHASE334_USB_PACKETS_TRANSMITTED = 0
PHASE334_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE334_SLOT1_DATA_SECTOR_WRITES = 0
PHASE334_E_ND_ACTUATOR_TX_COUNT = 0

P334_ERRNO_EPERM = 1
P334_ERRNO_EBUSY = 16
P334_ERRNO_EINVAL = 22
P334_ERRNO_EROFS = 30
P334_ERRNO_EOPNOTSUPP = 95

# Check Group IDs
P334_CHECK_GROUP_A_ID = (
    "GROUP_A_BREATHING_COMP_CATALYST_PREPARE_AND_MOVIE_FILE_SETTINGS_SDHC_VAULT"
)
P334_CHECK_GROUP_B_ID = (
    "GROUP_B_COPYRIGHT_46CH_ROUND57_ERRATA_POWERSAVE_9COND_AND_NTSCPAL_GUARD"
)
P334_CHECK_GROUP_C_ID = (
    "GROUP_C_ZOOM_CIZ_8STEP_SPEED_AUTO_SLOW_SHUTTER_AND_DUAL_BASE_ISO"
)
P334_CHECK_GROUP_D_ID = (
    "GROUP_D_DORMANT_LOSSLESS_RAW_USBLUN_SINGLE_NPFZ100_UVC_AND_TIER0"
)
PHASE_334_CHECK_GROUP_IDS = (
    P334_CHECK_GROUP_A_ID,
    P334_CHECK_GROUP_B_ID,
    P334_CHECK_GROUP_C_ID,
    P334_CHECK_GROUP_D_ID,
)

# Common enums
P334_VALID_RESET_ACTIONS = ("NONE", "CAMERA_SETTINGS_RESET", "RESET_NETWORK_SET", "INITIALIZE")
P334_VALID_SHOOT_MODES = ("PHOTO", "MOVIE", "S_AND_Q")
P334_VALID_ON_OFF = ("ON", "OFF")
P334_VALID_AUTO_OFF = ("AUTO", "OFF")
P334_VALID_EXPOSURE_MODES = (
    "MANUAL_EXPOSURE",
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "INTELLIGENT_AUTO",
    "FLEXIBLE_EXP",
)
P334_PASM_EXPOSURE_MODES = (
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "MANUAL_EXPOSURE",
)
P334_VALID_LOG_SHOOTING_MODES = ("OFF", "FLEXIBLE_ISO", "CINE_EI_QUICK", "CINE_EI")

# Wave 64 Group A constants: Breathing Comp & Movie File Settings
P334_BREATHING_COMP_RESID16_HEX = "0x73ea"
P334_BREATHING_COMP_BKID = "BKID_APP_setting_lens_comp_breathing"
P334_BREATHING_COMP_HIGH_FPS_CUTOFF = 100.0
P334_VALID_CATALYST_APPS = ("NONE", "CATALYST_BROWSE", "CATALYST_PREPARE", "CATALYST_PREPARE_PLUGIN")
P334_MOVIE_CLIP_ROOT_PATH = "PRIVATE/M4ROOT/CLIP/*.MP4"
P334_VALID_FILE_NUMBER_MODES = ("SERIES", "RESET")
P334_VALID_FILE_NAME_FORMATS = (
    "STANDARD",
    "CAM_ID_REEL",
    "TITLE",
    "DATE_TITLE",
    "TITLE_DATE",
)
P334_CAM_ID_REEL_POSITIONS = ("C", "L", "R")
P334_TITLE_MAX_CHARS = 37
P334_TITLE_ALLOWED_RE = re.compile(r"^[A-Za-z0-9._\-@#$%+=^~(),;\[\]]{1,37}$")
P334_CAMERA_ID_RE = re.compile(r"^[A-Z]$")
P334_VALID_MEDIA_TYPES = ("CFEXPRESS_A", "SDXC", "SDHC")
P334_VALID_SLOT_FILESYSTEMS = ("EXFAT", "FAT32")
P334_SDHC_SPLIT_GB = 4
P334_FX6_TITLE_PREFIX_MIN_CHARS = 4
P334_FX6_TITLE_PREFIX_MAX_CHARS = 46

# Wave 64 Group B constants: Copyright 46ch Round-57 Errata, Power Save 9-Cond & NTSC/PAL
P334_COPYRIGHT_EXACT_FOUR_ITEMS = (
    "WRITE_COPYRIGHT_INFO",
    "SET_PHOTOGRAPHER",
    "SET_COPYRIGHT",
    "DISP_COPYRIGHT_INFO",
)
P334_COPYRIGHT_MAX_CHARS = 46
P334_WRITE_SERIAL_BKID = "BKID_APP_setting_write_serial_number_still_movie"
P334_POWER_OPTION_EXACT_TWO_ITEMS = ("POWER_SAVE_START_TIME", "AUTO_POWER_OFF_TEMP")
P334_VALID_POWER_SAVE_START_TIMES = ("OFF", "30_MIN", "5_MIN", "2_MIN", "1_MIN", "10_SEC")
P334_DORMANT_POWER_SAVE_TIMERS = ("20_SEC", "NO_LIMIT", "30_SEC", "60_MIN", "240_MIN")
P334_POWER_SAVE_NINE_BYPASS_CONDITIONS = (
    "USB_POWER_SUPPLY",
    "SLIDESHOW",
    "FTP_TRANSFER",
    "MOVIE_RECORDING",
    "PC_CONNECTION",
    "TV_HDMI_CONNECTION",
    "IR_REMOTE_CTRL_ON",
    "BLUETOOTH_RMT_CTRL_ON",
    "STREAMING_OR_CREATORS_CLOUD_UPLOAD",
)
P334_VALID_AUTO_POWER_OFF_TEMPS = ("STANDARD", "HIGH")
P334_DORMANT_POWER_SAVE_BY_MONITOR_RESIDS = ("0x783f", "0x6db5", "0x6db6", "0x60a8", "0x6b2e")
P334_DORMANT_POWER_SAVE_BY_MONITOR_BKID = "BKID_APP_setting_monitor_power_linkage"
P334_VALID_VIDEO_SYSTEMS = ("NTSC", "PAL")
P334_NTSCPAL_RESID16_HEX = "0x6b6f"
P334_BASE_UXC_FORMAT_PROMPT_RESIDS = ("0xe1e6", "0xe373", "0xe51a", "0xe595", "0xe9f6")

# Wave 65 Group C constants: Zoom Range CIZ/Digital, Speeds, Auto Slow Shutter & Dual Base ISO
P334_VALID_ZOOM_RANGES = ("OPTICAL_ONLY", "CLEAR_IMAGE_ZOOM", "DIGITAL_ZOOM")
P334_VALID_ZOOM_RING_ROTATES = ("LEFT_W_RIGHT_T", "RIGHT_W_LEFT_T")
P334_ZOOM_SPEED_MIN = 1
P334_ZOOM_SPEED_MAX = 8
P334_ZOOM_LEVER_1ST_DEFAULT = 3
P334_ZOOM_LEVER_2ND_DEFAULT = 8
P334_CUSTOM_KEY_ZOOM_SPEED_DEFAULT = 3
P334_REMOTE_ZOOM_FIXED_DEFAULT = 3
P334_VALID_REMOTE_ZOOM_SPEED_TYPES = ("VARIABLE", "FIXED")
P334_CIZ_MOVIE_4K_MAX_ZOOM = 1.5
P334_CIZ_MOVIE_HD_MAX_ZOOM = 2.0
P334_DIGITAL_MOVIE_MAX_ZOOM = 4.0
P334_VALID_FLEXIBLE_SHUTTER_MODES = ("AUTO", "MANUAL")
P334_VALID_SHUTTER_MODES = ("SHUTTER_SPEED", "SHUTTER_ANGLE")
P334_VALID_ISO_MODES = ("CINE_EI_BASE", "ISO_AUTO", "MANUAL_ISO")
P334_ISO_MIN_FLOOR = 50
P334_ISO_MAX_CEILING = 409600
P334_VALID_ISO_AUTO_MIN_SS_MODES = (
    "SLOWER",
    "SLOW",
    "STD",
    "FAST",
    "FASTER",
    "1/8000",
    "1/4000",
    "1/2000",
    "1/1000",
    "1/500",
    "1/250",
    "1/125",
    "1/60",
    "1/30",
    "1/15",
    "1/8",
    "1/4",
    "1/2",
    "1",
    "2",
    "4",
    "8",
    "15",
    "30",
)
P334_DUAL_BASE_ISO_TABLE: Dict[str, Tuple[int, int]] = {
    "CINE_EI": (800, 12800),
    "SLOG3": (640, 12800),
    "SLOG2": (640, 12800),
    "ITU709_800": (640, 12800),
    "PP11_SCINETONE": (100, 2000),
    "HLG": (100, 2000),
    "HLG3": (100, 2000),
    "CINE4": (100, 2000),
    "PP_OFF": (80, 1600),
    "HLG2": (80, 1600),
    "CINE3": (80, 1600),
    "CINE1": (64, 1280),
    "HLG1": (50, 1000),
    "CINE2": (50, 1000),
}

# Wave 65 Group D constants: Dormant Lossless RAW, USB LUN Single, NP-FZ100 PD & Dormant UVC
P334_FX3_RAW_TWO_OPTIONS = ("COMPRESSED", "UNCOMPRESSED")
P334_DORMANT_LOSSLESS_RAW_OPTIONS = ("LOSSLESS_COMP", "LOSSLESS_COMP_L", "LOSSLESS_COMP_M", "LOSSLESS_COMP_S")
P334_DORMANT_LOSSLESS_RAW_RESID16_HEX = "0x6b56"
P334_VALID_JH_FILE_TYPES = ("JPEG", "HEIF_420", "HEIF_422")
P334_VALID_STILL_FILE_FORMATS = ("RAW", "RAW_AND_JH", "JPEG", "HEIF")
P334_VALID_RECORDING_MEDIA_MODES = ("SLOT_1", "SLOT_2", "SIMULTANEOUS_RECORDING", "SORT_RECORDING")
P334_USB_CONN_EXACT_FOUR_MODES = (
    "SEL_WHEN_CONNECT",
    "MASS_STORAGE",
    "MTP",
    "REMOTE_SHOOTING",
)
P334_FX3_MSC_VID_PID = "054C:0DA1"
P334_VALID_USB_LUN_MODES = ("MULTI", "SINGLE")
P334_VALID_POWER_SOURCES = ("INTERNAL_NP_FZ100", "USB_PD_BODY", "DC_C1_COUPLER")
P334_VALID_USB_POWER_TERMINALS = ("USB_TYPE_C",)
P334_DC_C1_MIN_PD_WATTS = 65.0
P334_DC_C1_MIN_CABLE_AMPS = 5.0
P334_FX6_DC_IN_NOMINAL_VOLTS = 19.5
P334_DORMANT_UVC_RESIDS = ("0x6216", "0x6194")
P334_DORMANT_UVC_BKID = "BKID_APP_SETTING_USB_STREAMING_PROCAM"
P334_MOVIE_REC_DURING_STREAMING_RESID16_HEX = "0x79d5"
P334_REC_MEDIA_DUR_HDMI_RESID16_HEX = "0x6144"
P334_VALID_MOVIE_REC_DURING_STREAMING = ("DISABLE", "ENABLE")
P334_VALID_STREAMING_PROTOCOLS = ("DISABLED", "RTMP", "RTMPS", "SRT")

# Error codes
P334_GA_ERR_MODEL_OR_FW_FLOOR = "P334_GA_ERR_MODEL_OR_FW_FLOOR"
P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST = (
    "P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST"
)
P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH = (
    "P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH"
)
P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT = (
    "P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT"
)

P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA = (
    "P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA"
)
P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE = (
    "P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE"
)
P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS = (
    "P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS"
)

P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL = (
    "P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL"
)
P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS = (
    "P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS"
)
P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION = (
    "P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION"
)

P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1 = (
    "P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1"
)
P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE = (
    "P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE"
)
P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT = (
    "P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT"
)
P334_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P334_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P334_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P334_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"


@dataclass(frozen=True)
class Phase334DonorInspectionResult:
    verification_mode: str
    donor_tree_present: bool
    fx3_appfw_present: bool
    fx6_appfw_present: bool
    fx3_uxc_present: bool
    checked_paths: Tuple[str, ...]
    bytes_read_total: int
    elapsed_seconds: float
    within_budget: bool
    raw_firmware_bytes_leaked: int


@dataclass(frozen=True)
class P334CheckGroupABreathingCamIdSdhcResult:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    breathing_comp: str
    breathing_comp_resettable: bool
    catalyst_app: str
    distortion_comp: str
    file_number_mode: str
    file_name_format: str
    camera_id: str
    reel_number: int
    camera_position: str
    title_name: str
    slot1_media_type: str
    slot2_media_type: str
    slot1_tier0_vault_mutated: bool


@dataclass(frozen=True)
class P334CheckGroupBCopyrightPowerSaveNtscPalResult:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    write_copyright_info: str
    photographer_len: int
    copyright_len: int
    write_serial_number: str
    copyright_and_serial_reset_immune: bool
    copyright_excluded_from_camset: bool
    power_save_start_time: str
    auto_power_off_temp: str
    fx3_power_save_by_monitor_present: bool
    video_system: str
    slot1_tier0_vault_mutated: bool


@dataclass(frozen=True)
class P334CheckGroupCZoomCizAutoSlowDualBaseIsoResult:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    zoom_range: str
    zoom_ring_rotate: str
    zoom_lever_stby_speed: int
    zoom_lever_rec_speed: int
    custom_key_zoom_speed: int
    remote_zoom_speed_type: str
    fx6_digital_zoom_present: bool
    auto_slow_shutter: str
    iso_range_limit_min: int
    iso_range_limit_max: int
    iso_auto_min_ss: str
    gamma_base_profile: str
    dual_base_iso_low: int
    dual_base_iso_high: int


@dataclass(frozen=True)
class P334CheckGroupDRawCompUsbLunUvcTier0Result:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    raw_file_type: str
    fx3_lossless_comp_raw_present: bool
    hlg_still_image: str
    jh_file_type: str
    usb_connection_mode: str
    usb_lun_setting: str
    usb_power_supply: str
    power_source: str
    fx3_native_uvc_present: bool
    fx6_native_uvc_present: bool
    movie_rec_during_streaming: str
    slot1_tier0_vault_mutated: bool
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    e_nd_actuator_tx_count: int
    usb_packets_transmitted: int
    passive_tx_bytes_emitted: int
    raw_firmware_bytes_leaked: int


@dataclass(frozen=True)
class Phase334ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwBreathingCamIdCopyrightPowerSaveZoomCizRawCompUsbLunReport:
    schema_version: str
    phase_version: str
    sony_help_guide_id: str
    verification_mode: str
    simulate_bench_dry_run: bool
    overall_status: str
    go_no_go: str
    body_model_id_hex: str
    body_fw: str
    reset_action: str
    check_group_count: int
    check_groups_passed: int
    check_group_a: P334CheckGroupABreathingCamIdSdhcResult
    check_group_b: P334CheckGroupBCopyrightPowerSaveNtscPalResult
    check_group_c: P334CheckGroupCZoomCizAutoSlowDualBaseIsoResult
    check_group_d: P334CheckGroupDRawCompUsbLunUvcTier0Result
    donor_inspection: Phase334DonorInspectionResult
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    cross_model_flash_authorized: bool
    slot1_tier0_vault_mutated: bool
    rf_nvs_p12_p13_writes_authorized: bool
    fx3_power_save_by_monitor_present: bool
    fx3_lossless_comp_raw_present: bool
    fx3_native_uvc_present: bool
    fx6_native_uvc_present: bool
    fx6_digital_zoom_present: bool
    fx3_copyright_resets_via_camera_settings_reset: bool
    fx3_write_serial_resets_via_camera_settings_reset: bool
    e_nd_actuator_tx_count: int
    e_nd_i2c_tx_bytes: int
    rf_packets_transmitted: int
    wireless_rf_packets_emitted: int
    slot1_data_sector_writes: int
    usb_packets_transmitted: int
    passive_tx_bytes_emitted: int
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    report_sha256: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(_zero_timing_fields(self.to_dict()), indent=indent, sort_keys=True) + "\n"


def _is_timing_key(key: str) -> bool:
    return key in (
        "elapsed_seconds",
        "elapsed_s",
        "elapsed_ms",
        "inspection_elapsed_ms",
        "wall_seconds",
    ) or key.endswith(("_elapsed_ms", "_elapsed_s", "_elapsed_seconds"))


def _zero_timing_fields(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k)
            if _is_timing_key(ks) and isinstance(v, (int, float)) and not isinstance(v, bool):
                out[ks] = 0.0
            else:
                out[ks] = _zero_timing_fields(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_zero_timing_fields(x) for x in obj]
    return obj


def _strip_timing_fields(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        out: Dict[str, Any] = {}
        for k, v in obj.items():
            ks = str(k)
            if _is_timing_key(ks):
                continue
            out[ks] = _strip_timing_fields(v)
        return out
    if isinstance(obj, (list, tuple)):
        return [_strip_timing_fields(x) for x in obj]
    return obj


def _canonical_sha256_dict(payload: Mapping[str, Any]) -> str:
    clone = json.loads(json.dumps(dict(payload)))
    clone.pop("report_sha256", None)
    clone = _strip_timing_fields(clone)
    encoded = json.dumps(clone, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_clean_room_env() -> bool:
    return is_forced_clean_room() or (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
    )


def _bounded_read_header(path: Path, max_bytes: int = P334_HEADER_READ_BYTES) -> int:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        data = os.read(fd, max_bytes)
        return len(data)
    finally:
        os.close(fd)


def resolve_phase334_donor_file_or_none(
    work_root: Optional[Path],
    rel_subpath: str,
) -> Optional[Path]:
    """Resolve a donor file under ``work_root``, returning ``None`` cleanly when ``work_root is None``."""
    if work_root is None:
        return None
    cand = Path(work_root) / rel_subpath
    return cand if cand.is_file() else None


def _resolve_work_root_or_none(*, force_clean_room: bool = False) -> Optional[Path]:
    """Return the first ``work/`` root containing BYOF donor artifacts, or ``None`` on donorless CI."""
    if force_clean_room or _is_clean_room_env():
        return None
    for candidate in iter_work_roots():
        if not candidate.is_dir():
            continue
        if any(resolve_phase334_donor_file_or_none(candidate, rel) is not None for _lbl, rel in P334_BOUNDED_DONOR_PATHS):
            return candidate
    return None


def inspect_phase334_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase334DonorInspectionResult:
    """Inspect local donor headers strictly via bounded O_RDONLY (< 0.20s) with clean-room fallback."""
    t0 = time.monotonic()
    clean_room = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    if clean_room:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase334DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_uxc_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE334_RAW_FIRMWARE_BYTES_LEAKED,
        )

    effective_work_root = (
        work_root if work_root is not None else _resolve_work_root_or_none(force_clean_room=False)
    )
    if effective_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase334DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_uxc_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE334_RAW_FIRMWARE_BYTES_LEAKED,
        )

    checked: List[str] = []
    bytes_total = 0
    found_map: Dict[str, bool] = {}
    for label, rel in P334_BOUNDED_DONOR_PATHS:
        resolved: Optional[Path] = None
        if label == "fx6_appfw_so" and fx6_lib_dir is not None:
            cand = fx6_lib_dir / "appFw.so"
            if cand.is_file():
                resolved = cand
        if label == "fx3_upm_ko" and fx3_modules_dir is not None:
            cand = fx3_modules_dir / "upm.ko"
            if cand.is_file():
                resolved = cand
        if resolved is None:
            resolved = resolve_phase334_donor_file_or_none(effective_work_root, rel)
        if resolved is None and effective_work_root is not None:
            cand = resolve_work_subpath(rel, require_file=True)
            if cand.is_file():
                resolved = cand
        if resolved is not None and resolved.is_file():
            checked.append(label)
            bytes_total += _bounded_read_header(resolved)
            found_map[label] = True
        else:
            found_map[label] = False

    donor_present = any(found_map.values())
    mode = "LOCAL_DONOR_O_RDONLY" if donor_present else "CLEAN_ROOM_SYNTHETIC"
    elapsed = round(time.monotonic() - t0, 6)
    return Phase334DonorInspectionResult(
        verification_mode=mode,
        donor_tree_present=donor_present,
        fx3_appfw_present=found_map.get("fx3_libjiritsu_so", False) and found_map.get("fx3_im_elf", False),
        fx6_appfw_present=found_map.get("fx6_appfw_so", False),
        fx3_uxc_present=found_map.get("fx3_libusbbuspower_so", False) and found_map.get("fx3_upm_ko", False),
        checked_paths=tuple(checked),
        bytes_read_total=bytes_total,
        elapsed_seconds=elapsed,
        within_budget=elapsed <= max_seconds,
        raw_firmware_bytes_leaked=PHASE334_RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_p334_check_group_a_breathing_camid_and_sdhc(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P334_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Wave 64 §1: Breathing Comp. & Catalyst Prepare vs Browse
    breathing_comp: str = "OFF",
    rec_fps: float = 23.98,
    sq_enabled: bool = False,
    sq_fps: float = 60.0,
    hdmi_raw_output: str = "OFF",
    zoom_range: str = "OPTICAL_ONLY",
    auto_framing_claimed: bool = False,
    non_compliant_or_teleconverter_lens: bool = False,
    claimed_breathing_comp_resists_camera_reset: bool = False,
    claimed_static_lens_comp_reset_by_camera_reset: bool = False,
    claimed_fx3_blocks_breathing_below_100fps_sq: bool = False,
    fx6_breathing_allows_sq_or_distortion_off_or_raw_claimed: bool = False,
    post_breathing_comp_requested: bool = False,
    catalyst_app: str = "NONE",
    distortion_comp: str = "AUTO",
    claimed_catalyst_browse_supports_breathing_comp: bool = False,
    # Wave 64 §2: Movie File Settings & SDHC vs exFAT
    file_number_mode: str = "SERIES",
    series_counter_reset_slot: int = 0,
    movie_file_counter_write_slot: int = 0,
    file_name_format: str = "STANDARD",
    camera_id: str = "A",
    reel_number: int = 1,
    camera_position: str = "C",
    title_name: str = "C",
    claimed_movie_file_settings_reset_by_camera_reset: bool = False,
    claimed_custom_movie_folder_supported: bool = False,
    claimed_file_number_reset_resets_reel: bool = False,
    expect_rollover_mutates_cam_id_menu: bool = False,
    claimed_cam_id_reel_uses_yyyymmdd_date: bool = False,
    fx6_clip_naming_uses_project_menu_or_37char_claimed: bool = False,
    recording_media: str = "SLOT_2",
    slot1_media_type: str = "CFEXPRESS_A",
    slot2_media_type: str = "CFEXPRESS_A",
    slot1_fs: str = "EXFAT",
    slot2_fs: str = "EXFAT",
    slot1_contains_tier0_dump: bool = True,
    slot1_data_sector_writes: int = 0,
    claimed_sdhc_no_4gb_split: bool = False,
) -> P334CheckGroupABreathingCamIdSdhcResult:
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_id != TARGET_MODEL_ID_INT
        or body_fw != TARGET_BODY_FW
        or sony_help_guide_id != P334_SONY_HELP_GUIDE_ID
    ):
        errors.append(
            f"{P334_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX} fw={TARGET_BODY_FW} "
            f"help_guide={P334_SONY_HELP_GUIDE_ID}, got {hex(body_model_id)} fw={body_fw} "
            f"help_guide={sony_help_guide_id}"
        )
    if reset_action not in P334_VALID_RESET_ACTIONS:
        errors.append(f"{P334_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action={reset_action}")
    if shoot_mode not in P334_VALID_SHOOT_MODES:
        errors.append(f"{P334_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode={shoot_mode}")

    # [Breathing Comp.]
    if breathing_comp not in P334_VALID_ON_OFF:
        errors.append(
            f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: invalid breathing_comp={breathing_comp}"
        )
    if hdmi_raw_output not in P334_VALID_ON_OFF:
        errors.append(
            f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: invalid hdmi_raw_output={hdmi_raw_output}"
        )
    if distortion_comp not in P334_VALID_AUTO_OFF:
        errors.append(
            f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: invalid distortion_comp={distortion_comp}"
        )
    if catalyst_app not in P334_VALID_CATALYST_APPS:
        errors.append(
            f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: invalid catalyst_app={catalyst_app}"
        )
    if breathing_comp == "ON":
        eff_sq = shoot_mode == "S_AND_Q" or sq_enabled
        if shoot_mode == "PHOTO":
            errors.append(
                f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: "
                f"[Breathing Comp.] ({P334_BREATHING_COMP_RESID16_HEX}) is disabled in Still mode "
                f"(errno={P334_ERRNO_EOPNOTSUPP})"
            )
        if not eff_sq and rec_fps >= P334_BREATHING_COMP_HIGH_FPS_CUTOFF:
            errors.append(
                f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: "
                f"[Breathing Comp.] is disabled at regular Movie >= {P334_BREATHING_COMP_HIGH_FPS_CUTOFF}p "
                f"(got {rec_fps}p)"
            )
        if eff_sq and sq_fps >= P334_BREATHING_COMP_HIGH_FPS_CUTOFF:
            errors.append(
                f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: "
                f"[Breathing Comp.] is disabled at S&Q >= {P334_BREATHING_COMP_HIGH_FPS_CUTOFF}fps "
                f"(got {sq_fps}fps)"
            )
        if hdmi_raw_output == "ON":
            errors.append(
                f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: "
                "[Breathing Comp.] is disabled during HDMI 16-bit RAW Output"
            )
        if zoom_range != "OPTICAL_ONLY" or auto_framing_claimed or non_compliant_or_teleconverter_lens:
            errors.append(
                f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: "
                "[Breathing Comp.] is locked out on CIZ/Digital Zoom, Auto Framing, macro SEL100F28GM, "
                "SEL14TC/SEL20TC teleconverters, or non-compliant lenses"
            )
    if reset_action == "CAMERA_SETTINGS_RESET" and breathing_comp != "OFF":
        errors.append(
            f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: "
            "[Breathing Comp.] resets to OFF on [Camera Settings Reset]"
        )
    if (
        claimed_breathing_comp_resists_camera_reset
        or claimed_static_lens_comp_reset_by_camera_reset
        or claimed_fx3_blocks_breathing_below_100fps_sq
        or fx6_breathing_allows_sq_or_distortion_off_or_raw_claimed
    ):
        errors.append(
            f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: "
            "[Breathing Comp.] IS Camera-Settings-Reset-capable (unlike Shading/CA/Distortion Comp.) and allows "
            "S&Q < 100fps on FX3, whereas FX6 locks Off for ALL S&Q=On, Distortion Comp=Off, and RAW codecs"
        )
    if claimed_catalyst_browse_supports_breathing_comp:
        errors.append(
            f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: "
            "Free Catalyst Browse does NOT support breathing compensation (requires paid Catalyst Prepare / Plugin)"
        )
    if post_breathing_comp_requested:
        if catalyst_app not in ("CATALYST_PREPARE", "CATALYST_PREPARE_PLUGIN") or distortion_comp != "AUTO":
            errors.append(
                f"{P334_GA_ERR_BREATHING_COMP_LOCKOUT_RESET_OR_CATALYST}: "
                "Post metadata breathing compensation requires Catalyst Prepare / Plugin AND in-body [Distortion Comp.]=Auto"
            )

    # Movie [File Settings]
    if file_number_mode not in P334_VALID_FILE_NUMBER_MODES:
        errors.append(
            f"{P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH}: invalid file_number_mode={file_number_mode}"
        )
    if file_name_format not in P334_VALID_FILE_NAME_FORMATS:
        errors.append(
            f"{P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH}: invalid file_name_format={file_name_format}"
        )
    if not P334_CAMERA_ID_RE.match(camera_id):
        errors.append(
            f"{P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH}: Camera ID must be A..Z (got {camera_id!r})"
        )
    if not (1 <= reel_number <= 999):
        errors.append(
            f"{P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH}: Reel Number must be 1..999 (got {reel_number})"
        )
    if camera_position not in P334_CAM_ID_REEL_POSITIONS:
        errors.append(
            f"{P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH}: Camera Position must be C/L/R (got {camera_position!r})"
        )
    if not P334_TITLE_ALLOWED_RE.match(title_name):
        errors.append(
            f"{P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH}: Title Name must be 1..{P334_TITLE_MAX_CHARS} "
            f"allowed ASCII chars (got {title_name!r})"
        )
    if (
        claimed_movie_file_settings_reset_by_camera_reset
        or claimed_custom_movie_folder_supported
        or claimed_file_number_reset_resets_reel
        or expect_rollover_mutates_cam_id_menu
        or claimed_cam_id_reel_uses_yyyymmdd_date
        or fx6_clip_naming_uses_project_menu_or_37char_claimed
    ):
        errors.append(
            f"{P334_GA_ERR_MOVIE_FILE_SETTINGS_CAMID_REEL_37CH}: "
            "Movie [File Settings] is Initialize-only under fixed PRIVATE/M4ROOT/CLIP; Cam ID+Reel# uses YYMMDD "
            "with C999->D001 output rollover (File Number=Reset does not reset Reel#), vs FX6 TC/Media > Clip Name Format "
            "(4..46-char Title Prefix def nnn_)"
        )

    # SDHC vs exFAT & Slot-1 Tier-0 Vault EROFS=30 firewall
    if slot1_media_type not in P334_VALID_MEDIA_TYPES or slot2_media_type not in P334_VALID_MEDIA_TYPES:
        errors.append(
            f"{P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT}: invalid media type "
            f"({slot1_media_type}, {slot2_media_type})"
        )
    if slot1_fs not in P334_VALID_SLOT_FILESYSTEMS or slot2_fs not in P334_VALID_SLOT_FILESYSTEMS:
        errors.append(
            f"{P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT}: invalid fs ({slot1_fs}, {slot2_fs})"
        )
    if (slot1_media_type == "SDHC" and slot1_fs != "FAT32") or (
        slot2_media_type == "SDHC" and slot2_fs != "FAT32"
    ):
        errors.append(
            f"{P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT}: "
            f"SDHC (<= 32 GB) requires FAT32 filesystem (got slot1={slot1_fs}, slot2={slot2_fs})"
        )
    if recording_media not in P334_VALID_RECORDING_MEDIA_MODES:
        errors.append(
            f"{P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT}: invalid recording_media={recording_media}"
        )

    target_sdhc = (
        (recording_media == "SLOT_1" and (slot1_media_type == "SDHC" or slot1_fs == "FAT32"))
        or (recording_media == "SLOT_2" and (slot2_media_type == "SDHC" or slot2_fs == "FAT32"))
        or (
            recording_media == "SIMULTANEOUS_RECORDING"
            and (
                slot1_media_type == "SDHC"
                or slot2_media_type == "SDHC"
                or slot1_fs == "FAT32"
                or slot2_fs == "FAT32"
            )
        )
    )
    if target_sdhc and file_name_format != "STANDARD":
        errors.append(
            f"{P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT}: "
            f"SDHC (FAT32 <= 32 GB) forces [File Name Format]=STANDARD (got {file_name_format})"
        )
    if claimed_sdhc_no_4gb_split:
        errors.append(
            f"{P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT}: "
            f"SDHC (FAT32) splits XAVC S movie files at {P334_SDHC_SPLIT_GB} GB"
        )
    if recording_media == "SIMULTANEOUS_RECORDING" and (
        slot1_fs != slot2_fs or (slot1_media_type == "SDHC") != (slot2_media_type == "SDHC")
    ):
        errors.append(
            f"{P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT}: "
            "[Simult. Recording] forbids mixing SDHC (FAT32) and exFAT across Slot 1 / Slot 2"
        )

    slot1_mutated = bool(
        slot1_contains_tier0_dump
        and (
            recording_media in ("SLOT_1", "SIMULTANEOUS_RECORDING")
            or series_counter_reset_slot == 1
            or movie_file_counter_write_slot == 1
            or slot1_data_sector_writes != 0
        )
    )
    if slot1_mutated:
        errors.append(
            f"{P334_GA_ERR_SDHC_4GB_EXFAT_SIMULT_OR_SLOT1_VAULT}: "
            f"Slot-1 Tier-0 Vault EROFS (errno={P334_ERRNO_EROFS}) blocks reel/file counter write or Slot-1 recording"
        )

    return P334CheckGroupABreathingCamIdSdhcResult(
        group_id=P334_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        breathing_comp=breathing_comp,
        breathing_comp_resettable=True,
        catalyst_app=catalyst_app,
        distortion_comp=distortion_comp,
        file_number_mode=file_number_mode,
        file_name_format=file_name_format,
        camera_id=camera_id,
        reel_number=reel_number,
        camera_position=camera_position,
        title_name=title_name,
        slot1_media_type=slot1_media_type,
        slot2_media_type=slot2_media_type,
        slot1_tier0_vault_mutated=slot1_mutated,
    )


def evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
    *,
    reset_action: str = "NONE",
    # Wave 64 §3: Round-57 Copyright 46-Char Errata & Write Serial Number
    exposed_copyright_items: Tuple[str, ...] = P334_COPYRIGHT_EXACT_FOUR_ITEMS,
    write_copyright_info: str = "OFF",
    set_photographer: str = "",
    set_copyright: str = "",
    disp_copyright_info_requested: bool = False,
    write_serial_number: str = "OFF",
    claimed_copyright_wiped_by_camera_reset: bool = False,
    claimed_write_serial_wiped_by_camera_reset: bool = False,
    claimed_write_serial_still_only_in_v702: bool = False,
    claimed_copyright_saved_in_camset: bool = False,
    claimed_write_serial_excluded_from_camset: bool = False,
    fx6_has_copyright_info_menu_claimed: bool = False,
    # Wave 64 §4: Power Setting Option 9-Cond, Dormant Power Save by Monitor & NTSC/PAL Format Guard
    exposed_power_option_items: Tuple[str, ...] = P334_POWER_OPTION_EXACT_TWO_ITEMS,
    power_save_start_time: str = "5_MIN",
    dormant_power_save_timer_requested: str = "NONE",
    power_save_active_bypass_conditions: Tuple[str, ...] = (),
    power_save_sleep_expected_during_bypass: bool = False,
    claimed_power_save_ignores_9_conditions: bool = False,
    auto_power_off_temp: str = "STANDARD",
    handheld_bare_skin_unacknowledged: bool = False,
    dormant_power_save_by_monitor_requested: bool = False,
    fx3_power_save_by_monitor_present_claimed: bool = False,
    fx3_builtin_evf_present: bool = False,
    claimed_power_option_wiped_by_camera_reset: bool = False,
    video_system: str = "NTSC",
    ntsc_pal_switch_requested: bool = False,
    expect_ntsc_pal_no_reboot: bool = False,
    expect_cross_system_playback_without_switch: bool = False,
    claimed_ntsc_pal_wiped_by_camera_reset: bool = False,
    fx6_has_ntsc_pal_selector_claimed: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_format_requested: bool = False,
    slot1_data_sector_writes: int = 0,
) -> P334CheckGroupBCopyrightPowerSaveNtscPalResult:
    errors: List[str] = []
    warnings: List[str] = []

    if reset_action not in P334_VALID_RESET_ACTIONS:
        errors.append(
            f"{P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA}: invalid reset_action={reset_action}"
        )

    # Round-57 Errata: Copyright Info (4 items) & Write Serial Number
    if tuple(exposed_copyright_items) != P334_COPYRIGHT_EXACT_FOUR_ITEMS:
        errors.append(
            f"{P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA}: "
            f"[Copyright Info] must expose exact 4 items {P334_COPYRIGHT_EXACT_FOUR_ITEMS}, "
            f"got {tuple(exposed_copyright_items)}"
        )
    if write_copyright_info not in P334_VALID_ON_OFF:
        errors.append(
            f"{P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA}: invalid write_copyright_info={write_copyright_info}"
        )
    if write_serial_number not in P334_VALID_ON_OFF:
        errors.append(
            f"{P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA}: invalid write_serial_number={write_serial_number}"
        )
    for label, text in (("Set Photographer", set_photographer), ("Set Copyright", set_copyright)):
        if len(text) > P334_COPYRIGHT_MAX_CHARS or not all(0x20 <= ord(ch) <= 0x7E for ch in text):
            errors.append(
                f"{P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA}: "
                f"{label} must be <= {P334_COPYRIGHT_MAX_CHARS} printable ASCII chars (len={len(text)})"
            )
    if disp_copyright_info_requested and not (set_photographer or set_copyright):
        warnings.append("Disp. Copyright Info requested with blank Photographer/Copyright fields")
    if (
        claimed_copyright_wiped_by_camera_reset
        or claimed_write_serial_wiped_by_camera_reset
        or claimed_write_serial_still_only_in_v702
        or claimed_copyright_saved_in_camset
        or claimed_write_serial_excluded_from_camset
        or fx6_has_copyright_info_menu_claimed
    ):
        errors.append(
            f"{P334_GB_ERR_ROUND57_COPYRIGHT_OR_SERIAL_RESET_ERRATA}: "
            "Round-57 Errata: ALL 4 [Copyright Info] items & Still+Movie [Write Serial Number] "
            f"({P334_WRITE_SERIAL_BKID}) are Initialize-only (resist [Camera Settings Reset]); "
            "Copyright Info is excluded from CAMSET*.DAT while Write Serial Number boolean is not"
        )

    # [Power Setting Option] 2 active items, 9 bypass conditions, dormant [Power Save by Monitor]
    if tuple(exposed_power_option_items) != P334_POWER_OPTION_EXACT_TWO_ITEMS:
        errors.append(
            f"{P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE}: "
            f"[Power Setting Option] exposes ONLY 2 items {P334_POWER_OPTION_EXACT_TWO_ITEMS}, "
            f"got {tuple(exposed_power_option_items)}"
        )
    if power_save_start_time not in P334_VALID_POWER_SAVE_START_TIMES:
        errors.append(
            f"{P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE}: "
            f"invalid power_save_start_time={power_save_start_time} (valid={P334_VALID_POWER_SAVE_START_TIMES})"
        )
    if dormant_power_save_timer_requested != "NONE":
        errors.append(
            f"{P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE}: "
            f"dormant timer {dormant_power_save_timer_requested} not exposed on FX3 Ver. 7.02 "
            f"(errno={P334_ERRNO_EOPNOTSUPP})"
        )
    for cond in power_save_active_bypass_conditions:
        if cond not in P334_POWER_SAVE_NINE_BYPASS_CONDITIONS:
            errors.append(
                f"{P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE}: invalid bypass condition {cond!r}"
            )
    if (
        (power_save_active_bypass_conditions and power_save_sleep_expected_during_bypass)
        or claimed_power_save_ignores_9_conditions
    ):
        errors.append(
            f"{P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE}: "
            "Power Save Start Time is bypassed under all 9 official deactivation conditions"
        )
    if auto_power_off_temp not in P334_VALID_AUTO_POWER_OFF_TEMPS:
        errors.append(
            f"{P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE}: "
            f"invalid auto_power_off_temp={auto_power_off_temp}"
        )
    if auto_power_off_temp == "HIGH" and handheld_bare_skin_unacknowledged:
        errors.append(
            f"{P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE}: "
            "[Auto Power OFF Temp.]=HIGH is restricted to tripod/non-handheld operation"
        )
    if (
        dormant_power_save_by_monitor_requested
        or fx3_power_save_by_monitor_present_claimed
        or fx3_builtin_evf_present
        or claimed_power_option_wiped_by_camera_reset
    ):
        errors.append(
            f"{P334_GB_ERR_POWERSAVE_9COND_OR_DORMANT_MONITOR_LINKAGE}: "
            f"[Power Save by Monitor] ({P334_DORMANT_POWER_SAVE_BY_MONITOR_BKID}, "
            f"{P334_DORMANT_POWER_SAVE_BY_MONITOR_RESIDS}) is strictly dormant on zero-EVF FX3 "
            f"(errno={P334_ERRNO_EOPNOTSUPP}); [Power Setting Option] is Initialize-only"
        )

    # [NTSC/PAL Selector] & Slot-1 Format Guard (EROFS=30)
    if video_system not in P334_VALID_VIDEO_SYSTEMS:
        errors.append(
            f"{P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS}: invalid video_system={video_system}"
        )
    if (
        (ntsc_pal_switch_requested and expect_ntsc_pal_no_reboot)
        or expect_cross_system_playback_without_switch
        or claimed_ntsc_pal_wiped_by_camera_reset
        or fx6_has_ntsc_pal_selector_claimed
    ):
        errors.append(
            f"{P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS}: "
            f"[NTSC/PAL Selector] ({P334_NTSCPAL_RESID16_HEX}) is Initialize-only, triggers full reboot, "
            "blocks cross-system playback, and is absent on FX6 (Project > Rec Format > Frequency)"
        )
    if not slot1_wp_locked or not slot1_contains_tier0_dump:
        errors.append(
            f"{P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS}: "
            f"Slot-1 Tier-0 Vault must be present and physically WP-locked (slot1_wp_locked={slot1_wp_locked}, "
            f"slot1_contains_tier0_dump={slot1_contains_tier0_dump})"
        )
    slot1_mutated = bool(
        (slot1_contains_tier0_dump and (slot1_format_requested or slot1_data_sector_writes != 0))
        or (slot1_format_requested and slot1_wp_locked)
    )
    if slot1_mutated:
        errors.append(
            f"{P334_GB_ERR_NTSCPAL_REBOOT_OR_SLOT1_FORMAT_EROFS}: "
            f"base.uxc format prompts {P334_BASE_UXC_FORMAT_PROMPT_RESIDS} hard-blocked on Slot-1 Tier-0 Vault "
            f"(errno={P334_ERRNO_EROFS})"
        )

    return P334CheckGroupBCopyrightPowerSaveNtscPalResult(
        group_id=P334_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        write_copyright_info=write_copyright_info,
        photographer_len=len(set_photographer),
        copyright_len=len(set_copyright),
        write_serial_number=write_serial_number,
        copyright_and_serial_reset_immune=True,
        copyright_excluded_from_camset=True,
        power_save_start_time=power_save_start_time,
        auto_power_off_temp=auto_power_off_temp,
        fx3_power_save_by_monitor_present=False,
        video_system=video_system,
        slot1_tier0_vault_mutated=slot1_mutated,
    )


def evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
    *,
    shoot_mode: str = "MOVIE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    flexible_shutter_mode: str = "MANUAL",
    shutter_mode: str = "SHUTTER_SPEED",
    # Wave 65 §1: Zoom Range CIZ/Digital & 8-Step Speeds
    zoom_range: str = "OPTICAL_ONLY",
    zoom_scale: float = 1.0,
    zoom_ring_rotate: str = "LEFT_W_RIGHT_T",
    zoom_lever_stby_speed: int = P334_ZOOM_LEVER_1ST_DEFAULT,
    zoom_lever_rec_speed: int = P334_ZOOM_LEVER_1ST_DEFAULT,
    zoom_lever_2nd_speed: int = P334_ZOOM_LEVER_2ND_DEFAULT,
    custom_key_zoom_stby_speed: int = P334_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    custom_key_zoom_rec_speed: int = P334_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    remote_zoom_speed_type: str = "VARIABLE",
    remote_zoom_fixed_stby_speed: int = P334_REMOTE_ZOOM_FIXED_DEFAULT,
    remote_zoom_fixed_rec_speed: int = P334_REMOTE_ZOOM_FIXED_DEFAULT,
    still_file_format: str = "RAW",
    rec_fps: float = 23.98,
    sq_enabled: bool = False,
    sq_fps: float = 60.0,
    focus_area: str = "WIDE",
    metering_mode: str = "MULTI",
    face_eye_prior_in_af: str = "ON",
    tracking_af_active: bool = False,
    claimed_zoom_range_wiped_by_camera_reset: bool = False,
    claimed_zoom_ring_rotate_wiped_by_camera_reset: bool = False,
    claimed_zoom_speeds_resist_camera_reset: bool = False,
    expect_smart_zoom_in_movie: bool = False,
    fx6_has_digital_zoom_claimed: bool = False,
    # Wave 65 §2: Auto Slow Shutter, ISO Range Limit, ISO AUTO Min. SS & Dual Base ISO
    auto_slow_shutter: str = "ON",
    expect_auto_slow_shutter_active: bool = False,
    claimed_auto_slow_shutter_resists_reset: bool = False,
    iso_mode: str = "CINE_EI_BASE",
    log_shooting_mode: str = "CINE_EI",
    iso_range_limit_min: int = 80,
    iso_range_limit_max: int = 102400,
    claimed_iso_range_limit_wiped_by_camera_reset: bool = False,
    expect_iso_range_limit_caps_iso_auto: bool = False,
    iso_auto_min_ss: str = "STD",
    flash_enabled: bool = False,
    expect_iso_auto_min_ss_in_movie_or_sq: bool = False,
    expect_iso_auto_min_ss_active_with_flash: bool = False,
    claimed_iso_auto_min_ss_resists_reset: bool = False,
    gamma_base_profile: str = "CINE_EI",
    dual_base_iso_low: int = 800,
    dual_base_iso_high: int = 12800,
    claimed_base_iso_menu_outside_cine_ei: bool = False,
    fx3_has_fx6_agc_claimed: bool = False,
) -> P334CheckGroupCZoomCizAutoSlowDualBaseIsoResult:
    errors: List[str] = []
    warnings: List[str] = []

    if zoom_range not in P334_VALID_ZOOM_RANGES:
        errors.append(
            f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: invalid zoom_range={zoom_range}"
        )
    if zoom_ring_rotate not in P334_VALID_ZOOM_RING_ROTATES:
        errors.append(
            f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: invalid zoom_ring_rotate={zoom_ring_rotate}"
        )
    if remote_zoom_speed_type not in P334_VALID_REMOTE_ZOOM_SPEED_TYPES:
        errors.append(
            f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: invalid remote_zoom_speed_type={remote_zoom_speed_type}"
        )
    for label, spd in (
        ("zoom_lever_stby_speed", zoom_lever_stby_speed),
        ("zoom_lever_rec_speed", zoom_lever_rec_speed),
        ("zoom_lever_2nd_speed", zoom_lever_2nd_speed),
        ("custom_key_zoom_stby_speed", custom_key_zoom_stby_speed),
        ("custom_key_zoom_rec_speed", custom_key_zoom_rec_speed),
        ("remote_zoom_fixed_stby_speed", remote_zoom_fixed_stby_speed),
        ("remote_zoom_fixed_rec_speed", remote_zoom_fixed_rec_speed),
    ):
        if not (P334_ZOOM_SPEED_MIN <= spd <= P334_ZOOM_SPEED_MAX):
            errors.append(
                f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: "
                f"{label}={spd} outside 1..8"
            )
    if (
        claimed_zoom_range_wiped_by_camera_reset
        or claimed_zoom_ring_rotate_wiped_by_camera_reset
        or claimed_zoom_speeds_resist_camera_reset
        or expect_smart_zoom_in_movie
        or fx6_has_digital_zoom_claimed
    ):
        errors.append(
            f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: "
            "[Zoom Range]/[Zoom Ring Rotate] are Initialize-only, 8-step speeds are Resettable, Smart Zoom is "
            "unavailable in Movie, and FX6 has ZERO Digital Zoom"
        )
    if zoom_scale < 1.0:
        errors.append(
            f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: zoom_scale={zoom_scale} < 1.0"
        )
    if zoom_range == "OPTICAL_ONLY" and zoom_scale > 1.0:
        errors.append(
            f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: "
            f"OPTICAL_ONLY forbids digital magnification (zoom_scale={zoom_scale} > 1.0)"
        )
    if zoom_range in ("CLEAR_IMAGE_ZOOM", "DIGITAL_ZOOM"):
        eff_sq = shoot_mode == "S_AND_Q" or sq_enabled
        if zoom_range == "CLEAR_IMAGE_ZOOM" and zoom_scale > P334_CIZ_MOVIE_4K_MAX_ZOOM:
            errors.append(
                f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: "
                f"CIZ 4K movie ceiling is {P334_CIZ_MOVIE_4K_MAX_ZOOM}x (HD ceiling {P334_CIZ_MOVIE_HD_MAX_ZOOM}x), got {zoom_scale}x"
            )
        if zoom_range == "DIGITAL_ZOOM" and zoom_scale > P334_DIGITAL_MOVIE_MAX_ZOOM:
            errors.append(
                f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: "
                f"Digital Zoom ceiling is {P334_DIGITAL_MOVIE_MAX_ZOOM}x, got {zoom_scale}x"
            )
        if shoot_mode == "PHOTO" and still_file_format in ("RAW", "RAW_AND_JH"):
            errors.append(
                f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: "
                f"{zoom_range} is locked out on Still {still_file_format}"
            )
        if not eff_sq and rec_fps >= P334_BREATHING_COMP_HIGH_FPS_CUTOFF:
            errors.append(
                f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: "
                f"{zoom_range} is locked out at Movie >= {P334_BREATHING_COMP_HIGH_FPS_CUTOFF}p (got {rec_fps}p)"
            )
        if eff_sq and sq_fps >= P334_BREATHING_COMP_HIGH_FPS_CUTOFF:
            errors.append(
                f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: "
                f"{zoom_range} is locked out at S&Q >= {P334_BREATHING_COMP_HIGH_FPS_CUTOFF}fps (got {sq_fps}fps)"
            )
        if zoom_scale > 1.0 and (
            focus_area != "CENTER_FIX"
            or metering_mode != "MULTI"
            or face_eye_prior_in_af != "OFF"
            or tracking_af_active
        ):
            errors.append(
                f"{P334_GC_ERR_ZOOM_CIZ_LOCKOUT_8STEP_SPEED_OR_FX6_DIGITAL}: "
                "Active CIZ/Digital Zoom forces Center AF + Multi Metering and disables Face/Eye & Tracking"
            )

    # [Auto Slow Shutter] 6+ lockouts & Still [ISO AUTO Min. SS]
    if auto_slow_shutter not in P334_VALID_ON_OFF:
        errors.append(
            f"{P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS}: invalid auto_slow_shutter={auto_slow_shutter}"
        )
    if claimed_auto_slow_shutter_resists_reset:
        errors.append(
            f"{P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS}: "
            "[Auto Slow Shutter] IS Resettable via [Camera Settings Reset]"
        )
    if auto_slow_shutter == "ON" and expect_auto_slow_shutter_active:
        locked_out = (
            shoot_mode == "S_AND_Q"
            or sq_enabled
            or exposure_mode in ("SHUTTER_PRIORITY", "MANUAL_EXPOSURE")
            or iso_mode == "MANUAL_ISO"
            or (exposure_mode == "FLEXIBLE_EXP" and flexible_shutter_mode == "MANUAL")
            or log_shooting_mode in ("CINE_EI", "CINE_EI_QUICK")
            or shutter_mode == "SHUTTER_ANGLE"
        )
        if locked_out:
            errors.append(
                f"{P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS}: "
                "[Auto Slow Shutter] cannot operate under S&Q / S / M / Manual ISO / Flexible Manual Shutter / "
                "Cine EI(-Quick) / Shutter Angle lockouts"
            )

    if iso_auto_min_ss not in P334_VALID_ISO_AUTO_MIN_SS_MODES:
        errors.append(
            f"{P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS}: invalid iso_auto_min_ss={iso_auto_min_ss}"
        )
    if (
        expect_iso_auto_min_ss_in_movie_or_sq
        or (flash_enabled and expect_iso_auto_min_ss_active_with_flash)
        or claimed_iso_auto_min_ss_resists_reset
    ):
        errors.append(
            f"{P334_GC_ERR_AUTO_SLOW_SHUTTER_6LOCK_OR_ISO_MIN_SS}: "
            "[ISO AUTO Min. SS] is Still-only (P/A + ISO AUTO, Resettable, overridden to 1/250 s with Flash)"
        )

    # [ISO Range Limit] & Dual Base ISO
    if (
        iso_range_limit_min < P334_ISO_MIN_FLOOR
        or iso_range_limit_max > P334_ISO_MAX_CEILING
        or iso_range_limit_min > iso_range_limit_max
    ):
        errors.append(
            f"{P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION}: "
            f"invalid [ISO Range Limit] {iso_range_limit_min}..{iso_range_limit_max}"
        )
    if claimed_iso_range_limit_wiped_by_camera_reset or expect_iso_range_limit_caps_iso_auto:
        errors.append(
            f"{P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION}: "
            "[ISO Range Limit] is Initialize-only and restricts Manual ISO only (not ISO AUTO)"
        )
    if gamma_base_profile not in P334_DUAL_BASE_ISO_TABLE:
        errors.append(
            f"{P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION}: "
            f"unknown gamma_base_profile={gamma_base_profile}"
        )
    else:
        exp_low, exp_high = P334_DUAL_BASE_ISO_TABLE[gamma_base_profile]
        if (dual_base_iso_low, dual_base_iso_high) != (exp_low, exp_high):
            errors.append(
                f"{P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION}: "
                f"{gamma_base_profile} dual base ISO is {exp_low}/{exp_high}, "
                f"got {dual_base_iso_low}/{dual_base_iso_high}"
            )
    if claimed_base_iso_menu_outside_cine_ei or fx3_has_fx6_agc_claimed:
        errors.append(
            f"{P334_GC_ERR_DUAL_BASE_ISO_OR_RANGE_LIMIT_VIOLATION}: "
            "[Base ISO] menu exists ONLY in Cine EI / Cine EI Quick (no FX6 AGC on FX3)"
        )

    return P334CheckGroupCZoomCizAutoSlowDualBaseIsoResult(
        group_id=P334_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        zoom_range=zoom_range,
        zoom_ring_rotate=zoom_ring_rotate,
        zoom_lever_stby_speed=zoom_lever_stby_speed,
        zoom_lever_rec_speed=zoom_lever_rec_speed,
        custom_key_zoom_speed=custom_key_zoom_stby_speed,
        remote_zoom_speed_type=remote_zoom_speed_type,
        fx6_digital_zoom_present=False,
        auto_slow_shutter=auto_slow_shutter,
        iso_range_limit_min=iso_range_limit_min,
        iso_range_limit_max=iso_range_limit_max,
        iso_auto_min_ss=iso_auto_min_ss,
        gamma_base_profile=gamma_base_profile,
        dual_base_iso_low=dual_base_iso_low,
        dual_base_iso_high=dual_base_iso_high,
    )


def evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    exposure_mode: str = "MANUAL_EXPOSURE",
    # Wave 65 §3: Dormant Lossless RAW, HLG Still & Sort Recording Failover
    raw_file_type: str = "COMPRESSED",
    dormant_lossless_comp_requested: bool = False,
    fx3_lossless_comp_present_claimed: bool = False,
    claimed_raw_file_type_resists_reset: bool = False,
    jh_file_type: str = "JPEG",
    still_file_format: str = "RAW",
    hlg_still_image: str = "OFF",
    recording_media: str = "SLOT_2",
    auto_switch_media: str = "OFF",
    auto_switch_failover_to_slot1_requested: bool = False,
    slot1_contains_tier0_dump: bool = True,
    # Wave 65 §4: USB LUN Single Slot-1 Hazard, NP-FZ100 PD Gate & Dormant UVC
    usb_connection_mode: str = "SEL_WHEN_CONNECT",
    usb_lun_setting: str = "MULTI",
    claimed_usb_lun_single_exposes_slot2: bool = False,
    host_msc_isolated: bool = True,
    host_spotlight_fseventsd_fsck_unblocked: bool = False,
    air_gapped_bench: bool = True,
    claimed_usb_settings_wiped_by_camera_reset: bool = False,
    usb_power_supply: str = "ON",
    usb_power_terminal: str = "USB_TYPE_C",
    power_source: str = "INTERNAL_NP_FZ100",
    np_fz100_inserted: bool = True,
    dc_c1_coupler_inserted: bool = False,
    dc_c1_pd_watts: float = 0.0,
    dc_c1_cable_amps: float = 0.0,
    expect_batteryless_usb_pd_without_dc_c1: bool = False,
    dormant_uvc_streaming_requested: bool = False,
    fx3_native_uvc_present_claimed: bool = False,
    fx6_native_uvc_present_claimed: bool = False,
    streaming_protocol: str = "DISABLED",
    movie_rec_during_streaming: str = "DISABLE",
    rec_media_dur_hdmi_output: str = "ON",
    rec_target_slot: int = 2,
    # Hardware & Tier-0 Gate
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    slot1_data_sector_writes: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> P334CheckGroupDRawCompUsbLunUvcTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    # Dormant Lossless RAW Myth-Busting
    if (
        raw_file_type not in P334_FX3_RAW_TWO_OPTIONS
        or dormant_lossless_comp_requested
        or fx3_lossless_comp_present_claimed
        or claimed_raw_file_type_resists_reset
    ):
        errors.append(
            f"{P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1}: "
            f"ILME-FX3 Ver. 7.02 [RAW File Type] exposes ONLY Resettable {P334_FX3_RAW_TWO_OPTIONS}; "
            f"Lossless Comp L/M/S ({P334_DORMANT_LOSSLESS_RAW_RESID16_HEX}) is strictly dormant "
            f"(errno={P334_ERRNO_EOPNOTSUPP})"
        )
    if jh_file_type not in P334_VALID_JH_FILE_TYPES:
        errors.append(
            f"{P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1}: invalid jh_file_type={jh_file_type}"
        )
    if still_file_format not in P334_VALID_STILL_FILE_FORMATS:
        errors.append(
            f"{P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1}: invalid still_file_format={still_file_format}"
        )
    if hlg_still_image not in P334_VALID_ON_OFF:
        errors.append(
            f"{P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1}: invalid hlg_still_image={hlg_still_image}"
        )
    if hlg_still_image == "ON":
        if (
            jh_file_type not in ("HEIF_420", "HEIF_422")
            or still_file_format != "HEIF"
            or exposure_mode not in P334_PASM_EXPOSURE_MODES
        ):
            errors.append(
                f"{P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1}: "
                "[HLG Still Image]=ON (BT.2100) requires HEIF (4:2:0/4:2:2), [File Format]=HEIF, and P/A/S/M"
            )
    if auto_switch_media not in P334_VALID_ON_OFF:
        errors.append(
            f"{P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1}: invalid auto_switch_media={auto_switch_media}"
        )

    sort_slot1_failover = bool(
        slot1_contains_tier0_dump
        and (
            auto_switch_failover_to_slot1_requested
            or auto_switch_media == "ON"
            or recording_media in ("SLOT_1", "SIMULTANEOUS_RECORDING", "SORT_RECORDING")
        )
    )
    if sort_slot1_failover:
        errors.append(
            f"{P334_GD_ERR_DORMANT_LOSSLESS_RAW_OR_HLG_OR_SORT_SLOT1}: "
            f"Sort/Simultaneous/Slot-1 Recording or Auto Switch Media failover onto Slot-1 Tier-0 Vault blocked (errno={P334_ERRNO_EROFS})"
        )

    # USB Connection Mode, USB LUN Single Slot-1 Hazard & NP-FZ100 PD Gate
    if usb_connection_mode not in P334_USB_CONN_EXACT_FOUR_MODES:
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: "
            f"invalid [USB Connection Mode]={usb_connection_mode} (valid={P334_USB_CONN_EXACT_FOUR_MODES})"
        )
    if usb_lun_setting not in P334_VALID_USB_LUN_MODES:
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: invalid usb_lun_setting={usb_lun_setting}"
        )
    if usb_lun_setting == "SINGLE" and slot1_contains_tier0_dump:
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: "
            f"[USB LUN Setting]=SINGLE exposes ONLY Slot-1 Tier-0 Vault and hides Slot 2 (errno={P334_ERRNO_EROFS})"
        )
    if claimed_usb_lun_single_exposes_slot2 or claimed_usb_settings_wiped_by_camera_reset:
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: "
            "[USB LUN Setting]=Single exposes ONLY Slot 1 (NOT Slot 2!); Setup->[USB] is Initialize-only"
        )
    usb_msc_hazard = bool(
        not host_msc_isolated
        or host_spotlight_fseventsd_fsck_unblocked
        or not air_gapped_bench
    )
    if usb_msc_hazard:
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: "
            f"{usb_connection_mode} (LUN={usb_lun_setting}, VID:PID={P334_FX3_MSC_VID_PID}) exposes Slot 1 "
            f"to macOS Spotlight/fseventsd/fsck writes without air-gapped MSC isolation (errno={P334_ERRNO_EROFS})"
        )
    if usb_power_supply not in P334_VALID_ON_OFF or usb_power_terminal not in P334_VALID_USB_POWER_TERMINALS:
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: invalid USB power supply/terminal"
        )
    if power_source not in P334_VALID_POWER_SOURCES:
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: invalid power_source={power_source}"
        )
    if expect_batteryless_usb_pd_without_dc_c1:
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: "
            "FX3 Type-C [USB Power Supply] requires charged NP-FZ100 inserted (or DC-C1 coupler), unlike FX6 19.5V DC IN"
        )
    if power_source == "USB_PD_BODY" and usb_power_supply == "ON" and not np_fz100_inserted and not dc_c1_coupler_inserted:
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: "
            "USB_PD_BODY without NP-FZ100 or DC-C1 cuts camera power"
        )
    if power_source == "DC_C1_COUPLER" and (
        not dc_c1_coupler_inserted
        or dc_c1_pd_watts < P334_DC_C1_MIN_PD_WATTS
        or dc_c1_cable_amps < P334_DC_C1_MIN_CABLE_AMPS
    ):
        errors.append(
            f"{P334_GD_ERR_USB_LUN_SINGLE_SLOT1_HAZARD_OR_PD_GATE}: "
            f"DC-C1 coupler requires >= {P334_DC_C1_MIN_PD_WATTS}W PD + {P334_DC_C1_MIN_CABLE_AMPS}A e-Marked cable"
        )

    # Dormant UVC/UAC vs Network Streaming & Slot-1 Firewall
    if dormant_uvc_streaming_requested or fx3_native_uvc_present_claimed or fx6_native_uvc_present_claimed:
        errors.append(
            f"{P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT}: "
            f"Native [USB Streaming] (UVC/UAC {P334_DORMANT_UVC_RESIDS}, {P334_DORMANT_UVC_BKID}) is strictly "
            f"dormant on BOTH ILME-FX3 Ver. 7.02 AND ILME-FX6 Ver. 6.01 (errno={P334_ERRNO_EOPNOTSUPP})"
        )
    if streaming_protocol not in P334_VALID_STREAMING_PROTOCOLS:
        errors.append(
            f"{P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT}: invalid streaming_protocol={streaming_protocol}"
        )
    if movie_rec_during_streaming not in P334_VALID_MOVIE_REC_DURING_STREAMING:
        errors.append(
            f"{P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT}: invalid movie_rec_during_streaming={movie_rec_during_streaming}"
        )
    if rec_media_dur_hdmi_output not in ("ON", "OFF_HDMI_ONLY"):
        errors.append(
            f"{P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT}: invalid rec_media_dur_hdmi_output={rec_media_dur_hdmi_output}"
        )
    streaming_slot1_write = bool(
        slot1_contains_tier0_dump
        and rec_target_slot == 1
        and (
            (movie_rec_during_streaming == "ENABLE" and streaming_protocol != "DISABLED")
            or rec_media_dur_hdmi_output == "ON"
        )
    )
    if streaming_slot1_write:
        errors.append(
            f"{P334_GD_ERR_DORMANT_UVC_OR_STREAMING_REC_SLOT1_VAULT}: "
            f"[Movie Rec During Streaming] ({P334_MOVIE_REC_DURING_STREAMING_RESID16_HEX}) / "
            f"[Rec. Media dur HDMI Output] ({P334_REC_MEDIA_DUR_HDMI_RESID16_HEX}) onto Slot 1 "
            f"Tier-0 Vault blocked (errno={P334_ERRNO_EROFS})"
        )

    slot1_mutated = bool(sort_slot1_failover or streaming_slot1_write or slot1_data_sector_writes != 0)

    # Zero-emission hardware redlines
    if (
        e_nd_actuator_tx_count != 0
        or wireless_rf_packets_emitted != 0
        or slot1_data_sector_writes != 0
        or usb_packets_transmitted != 0
        or simulated_passive_tx_bytes != 0
        or claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P334_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: "
            "Hardware safety redline violated (live_attach/emmc_writes/cross_model_flash must be False, "
            "all TX/write counters must be 0)"
        )

    # 16/16 H0 == H3 Surface Invariant
    surface_count = len(SIXTEEN_STORAGE_SURFACES)
    eff_serial = body_serial
    eff_cid = emmc_cid
    eff_h0_a = h0_baselines_a
    eff_h0_b = h0_baselines_b
    eff_h3 = h3_baselines

    sim_bundle: Optional[Dict[str, Any]] = None
    if (
        simulate_bench_dry_run
        and receipt_a_path is None
        and receipt_b_path is None
        and receipt_a_bytes is None
        and receipt_b_bytes is None
    ):
        sim_bundle = build_simulated_phase334_tier0_receipts()
        if eff_serial is None:
            eff_serial = sim_bundle["body_serial"]
        if eff_cid is None:
            eff_cid = sim_bundle["emmc_cid"]
        if eff_h0_a is None:
            eff_h0_a = sim_bundle["h0_baselines_a"]
        if eff_h0_b is None:
            eff_h0_b = sim_bundle["h0_baselines_b"]
        if eff_h3 is None:
            eff_h3 = sim_bundle["h3_baselines"]

    drifted = max(0, int(simulated_h0_h3_drifted_surfaces))
    if eff_h0_a is not None and eff_h3 is not None:
        key_mismatches = sum(
            1
            for key in REQUIRED_H0_BASELINE_KEYS
            if _is_trivial_hex64(eff_h0_a.get(key, ""))
            or eff_h0_a.get(key, "").lower() != eff_h3.get(key, "").lower()
        )
        surface_mismatches = sum(
            1
            for surf in SIXTEEN_STORAGE_SURFACES
            if eff_h0_a.get(surf) != eff_h3.get(surf)
        )
        extra_keys = set(eff_h0_a.keys()) | set(eff_h3.keys())
        extra_mismatches = sum(
            1
            for k in extra_keys
            if (k in eff_h0_a) != (k in eff_h3)
            or str(eff_h0_a.get(k, "")).lower() != str(eff_h3.get(k, "")).lower()
        )
        drifted = max(drifted, key_mismatches, surface_mismatches, extra_mismatches)
    h0_eq_h3_count = max(0, surface_count - drifted)

    if drifted != 0 or h0_eq_h3_count != surface_count:
        errors.append(
            f"{P334_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: "
            f"16/16 H0 == H3 invariant broken ({h0_eq_h3_count}/{surface_count})"
        )

    # Tier-0 Dual-Media 528B FX3RCPT1 Verification
    tier0_verified = False
    receipt_mode = "AWAITING_PHYSICAL_TIER0_RECEIPTS"

    def _read_single_tier0_receipt_file(path: Path) -> Tuple[Optional[Tuple[bytes, int]], List[str]]:
        errs: List[str] = []
        if not path.is_file():
            errs.append(f"Tier-0 receipt file not found: {path}")
            return None, errs
        st = path.stat()
        fd = os.open(str(path), os.O_RDONLY)
        try:
            raw = os.read(fd, SD_RECEIPT_BYTES + 64)
        finally:
            os.close(fd)
        if len(raw) != SD_RECEIPT_BYTES:
            errs.append(f"Tier-0 receipt {path} length {len(raw)} != {SD_RECEIPT_BYTES} bytes")
            return None, errs
        return (raw, int(st.st_dev)), errs

    if sim_bundle is not None:
        tier0_verified = True
        receipt_mode = "DRY_RUN_SIMULATED"
    elif (
        receipt_a_path is not None
        or receipt_b_path is not None
        or receipt_a_bytes is not None
        or receipt_b_bytes is not None
    ):
        raw_a = receipt_a_bytes
        raw_b = receipt_b_bytes
        dev_a = st_dev_a_override
        dev_b = st_dev_b_override
        read_errs: List[str] = []

        if raw_a is None and receipt_a_path is not None:
            res_a, err_a = _read_single_tier0_receipt_file(Path(receipt_a_path))
            if err_a or res_a is None:
                read_errs.extend(err_a)
            else:
                raw_a, st_a = res_a
                if dev_a is None:
                    dev_a = st_a
        if raw_b is None and receipt_b_path is not None:
            res_b, err_b = _read_single_tier0_receipt_file(Path(receipt_b_path))
            if err_b or res_b is None:
                read_errs.extend(err_b)
            else:
                raw_b, st_b = res_b
                if dev_b is None:
                    dev_b = st_b

        if read_errs:
            errors.extend(
                f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {msg}"
                for msg in read_errs
            )
            receipt_mode = "INVALID_RECEIPT_PARSE_OR_IDENTITY"
        elif raw_a is None or raw_b is None:
            errors.append(
                f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                "both Copy A and Copy B 528B FX3RCPT1 receipts are required"
            )
            receipt_mode = "INVALID_RECEIPT_SINGLE_COPY"
        else:
            if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
                errors.append(
                    f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    "dual 528B FX3RCPT1 size/byte mismatch"
                )
            if dev_a is None or dev_b is None or int(dev_a) == int(dev_b):
                errors.append(
                    f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"dual-media receipts must reside on distinct physical devices (st_dev {dev_a} vs {dev_b})"
                )
            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if (
                not BODY_SERIAL_RE.match(ser_norm)
                or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS
                or len(set(ser_norm.upper())) < 3
            ):
                errors.append(
                    f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"trivial or invalid body_serial={eff_serial!r}"
                )
            if (
                not HEX32_CID_RE.match(cid_norm)
                or cid_norm in FORBIDDEN_TRIVIAL_CIDS
                or len(set(cid_norm)) < 6
            ):
                errors.append(
                    f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"trivial or invalid 128-bit emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                errors.append(
                    f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"receipt target model/fw mismatch ({hex(body_model_id)} / {body_fw})"
                )
            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    errors.append(
                        f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                        f"FX3RCPT1 integrity/header check failed ({parsed_a.errors or parsed_b.errors})"
                    )
            except Exception as exc:
                errors.append(
                    f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse failure: {exc}"
                )
            if eff_h0_a is None or eff_h0_b is None:
                errors.append(
                    f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    "h0_baselines_a and h0_baselines_b required with physical receipts"
                )
            else:
                for key in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(key, "")
                    vb = eff_h0_b.get(key, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        errors.append(
                            f"{P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                            f"H0 baseline invalid or mismatched for {key}"
                        )
                        break
            if not any(e.startswith(P334_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID) for e in errors):
                tier0_verified = True
                receipt_mode = "PHYSICAL_DUAL_MEDIA_528B"
            else:
                receipt_mode = "INVALID_RECEIPT_REJECTED"
    else:
        warnings.append("No physical 528B FX3RCPT1 Tier-0 receipts provided; status fail-closed offline")

    return P334CheckGroupDRawCompUsbLunUvcTier0Result(
        group_id=P334_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        raw_file_type=raw_file_type,
        fx3_lossless_comp_raw_present=False,
        hlg_still_image=hlg_still_image,
        jh_file_type=jh_file_type,
        usb_connection_mode=usb_connection_mode,
        usb_lun_setting=usb_lun_setting,
        usb_power_supply=usb_power_supply,
        power_source=power_source,
        fx3_native_uvc_present=False,
        fx6_native_uvc_present=False,
        movie_rec_during_streaming=movie_rec_during_streaming,
        slot1_tier0_vault_mutated=slot1_mutated,
        tier0_receipt_verified=tier0_verified,
        receipt_mode=receipt_mode,
        h0_equals_h3_count=h0_eq_h3_count,
        h0_h3_surface_count=surface_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        usb_packets_transmitted=usb_packets_transmitted,
        passive_tx_bytes_emitted=simulated_passive_tx_bytes,
        raw_firmware_bytes_leaked=PHASE334_RAW_FIRMWARE_BYTES_LEAKED,
    )


def build_simulated_phase334_tier0_receipts(
    *,
    body_serial: str = "FX3702SIM334",
    emmc_cid: str = "150100424a4e42345201020304050609",
) -> Dict[str, Any]:
    h0 = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE334_TIER0:{TARGET_BODY_FW}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode("ascii")
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE334_MANIFEST:{body_serial}:{TARGET_BODY_FW}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    receipt_bytes = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    return {
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "receipt_a_bytes": receipt_bytes,
        "receipt_b_bytes": bytes(receipt_bytes),
        "st_dev_a_override": 101,
        "st_dev_b_override": 202,
        "h0_baselines_a": dict(h0),
        "h0_baselines_b": dict(h0),
        "h3_baselines": dict(h0),
    }


def evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P334_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    # Group A
    breathing_comp: str = "OFF",
    rec_fps: float = 23.98,
    sq_enabled: bool = False,
    sq_fps: float = 60.0,
    hdmi_raw_output: str = "OFF",
    zoom_range: str = "OPTICAL_ONLY",
    auto_framing_claimed: bool = False,
    non_compliant_or_teleconverter_lens: bool = False,
    claimed_breathing_comp_resists_camera_reset: bool = False,
    claimed_static_lens_comp_reset_by_camera_reset: bool = False,
    claimed_fx3_blocks_breathing_below_100fps_sq: bool = False,
    fx6_breathing_allows_sq_or_distortion_off_or_raw_claimed: bool = False,
    post_breathing_comp_requested: bool = False,
    catalyst_app: str = "NONE",
    distortion_comp: str = "AUTO",
    claimed_catalyst_browse_supports_breathing_comp: bool = False,
    file_number_mode: str = "SERIES",
    series_counter_reset_slot: int = 0,
    movie_file_counter_write_slot: int = 0,
    file_name_format: str = "STANDARD",
    camera_id: str = "A",
    reel_number: int = 1,
    camera_position: str = "C",
    title_name: str = "C",
    claimed_movie_file_settings_reset_by_camera_reset: bool = False,
    claimed_custom_movie_folder_supported: bool = False,
    claimed_file_number_reset_resets_reel: bool = False,
    expect_rollover_mutates_cam_id_menu: bool = False,
    claimed_cam_id_reel_uses_yyyymmdd_date: bool = False,
    fx6_clip_naming_uses_project_menu_or_37char_claimed: bool = False,
    recording_media: str = "SLOT_2",
    slot1_media_type: str = "CFEXPRESS_A",
    slot2_media_type: str = "CFEXPRESS_A",
    slot1_fs: str = "EXFAT",
    slot2_fs: str = "EXFAT",
    slot1_contains_tier0_dump: bool = True,
    slot1_data_sector_writes: int = 0,
    claimed_sdhc_no_4gb_split: bool = False,
    # Group B
    exposed_copyright_items: Tuple[str, ...] = P334_COPYRIGHT_EXACT_FOUR_ITEMS,
    write_copyright_info: str = "OFF",
    set_photographer: str = "",
    set_copyright: str = "",
    disp_copyright_info_requested: bool = False,
    write_serial_number: str = "OFF",
    claimed_copyright_wiped_by_camera_reset: bool = False,
    claimed_write_serial_wiped_by_camera_reset: bool = False,
    claimed_write_serial_still_only_in_v702: bool = False,
    claimed_copyright_saved_in_camset: bool = False,
    claimed_write_serial_excluded_from_camset: bool = False,
    fx6_has_copyright_info_menu_claimed: bool = False,
    exposed_power_option_items: Tuple[str, ...] = P334_POWER_OPTION_EXACT_TWO_ITEMS,
    power_save_start_time: str = "5_MIN",
    dormant_power_save_timer_requested: str = "NONE",
    power_save_active_bypass_conditions: Tuple[str, ...] = (),
    power_save_sleep_expected_during_bypass: bool = False,
    claimed_power_save_ignores_9_conditions: bool = False,
    auto_power_off_temp: str = "STANDARD",
    handheld_bare_skin_unacknowledged: bool = False,
    dormant_power_save_by_monitor_requested: bool = False,
    fx3_power_save_by_monitor_present_claimed: bool = False,
    fx3_builtin_evf_present: bool = False,
    claimed_power_option_wiped_by_camera_reset: bool = False,
    video_system: str = "NTSC",
    ntsc_pal_switch_requested: bool = False,
    expect_ntsc_pal_no_reboot: bool = False,
    expect_cross_system_playback_without_switch: bool = False,
    claimed_ntsc_pal_wiped_by_camera_reset: bool = False,
    fx6_has_ntsc_pal_selector_claimed: bool = False,
    slot1_wp_locked: bool = True,
    slot1_format_requested: bool = False,
    # Group C
    flexible_shutter_mode: str = "MANUAL",
    shutter_mode: str = "SHUTTER_SPEED",
    zoom_scale: float = 1.0,
    zoom_ring_rotate: str = "LEFT_W_RIGHT_T",
    zoom_lever_stby_speed: int = P334_ZOOM_LEVER_1ST_DEFAULT,
    zoom_lever_rec_speed: int = P334_ZOOM_LEVER_1ST_DEFAULT,
    zoom_lever_2nd_speed: int = P334_ZOOM_LEVER_2ND_DEFAULT,
    custom_key_zoom_stby_speed: int = P334_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    custom_key_zoom_rec_speed: int = P334_CUSTOM_KEY_ZOOM_SPEED_DEFAULT,
    remote_zoom_speed_type: str = "VARIABLE",
    remote_zoom_fixed_stby_speed: int = P334_REMOTE_ZOOM_FIXED_DEFAULT,
    remote_zoom_fixed_rec_speed: int = P334_REMOTE_ZOOM_FIXED_DEFAULT,
    still_file_format: str = "RAW",
    focus_area: str = "WIDE",
    metering_mode: str = "MULTI",
    face_eye_prior_in_af: str = "ON",
    tracking_af_active: bool = False,
    claimed_zoom_range_wiped_by_camera_reset: bool = False,
    claimed_zoom_ring_rotate_wiped_by_camera_reset: bool = False,
    claimed_zoom_speeds_resist_camera_reset: bool = False,
    expect_smart_zoom_in_movie: bool = False,
    fx6_has_digital_zoom_claimed: bool = False,
    auto_slow_shutter: str = "ON",
    expect_auto_slow_shutter_active: bool = False,
    claimed_auto_slow_shutter_resists_reset: bool = False,
    iso_mode: str = "CINE_EI_BASE",
    log_shooting_mode: str = "CINE_EI",
    iso_range_limit_min: int = 80,
    iso_range_limit_max: int = 102400,
    claimed_iso_range_limit_wiped_by_camera_reset: bool = False,
    expect_iso_range_limit_caps_iso_auto: bool = False,
    iso_auto_min_ss: str = "STD",
    flash_enabled: bool = False,
    expect_iso_auto_min_ss_in_movie_or_sq: bool = False,
    expect_iso_auto_min_ss_active_with_flash: bool = False,
    claimed_iso_auto_min_ss_resists_reset: bool = False,
    gamma_base_profile: str = "CINE_EI",
    dual_base_iso_low: int = 800,
    dual_base_iso_high: int = 12800,
    claimed_base_iso_menu_outside_cine_ei: bool = False,
    fx3_has_fx6_agc_claimed: bool = False,
    # Group D
    raw_file_type: str = "COMPRESSED",
    dormant_lossless_comp_requested: bool = False,
    fx3_lossless_comp_present_claimed: bool = False,
    claimed_raw_file_type_resists_reset: bool = False,
    jh_file_type: str = "JPEG",
    hlg_still_image: str = "OFF",
    auto_switch_media: str = "OFF",
    auto_switch_failover_to_slot1_requested: bool = False,
    usb_connection_mode: str = "SEL_WHEN_CONNECT",
    usb_lun_setting: str = "MULTI",
    claimed_usb_lun_single_exposes_slot2: bool = False,
    host_msc_isolated: bool = True,
    host_spotlight_fseventsd_fsck_unblocked: bool = False,
    air_gapped_bench: bool = True,
    claimed_usb_settings_wiped_by_camera_reset: bool = False,
    usb_power_supply: str = "ON",
    usb_power_terminal: str = "USB_TYPE_C",
    power_source: str = "INTERNAL_NP_FZ100",
    np_fz100_inserted: bool = True,
    dc_c1_coupler_inserted: bool = False,
    dc_c1_pd_watts: float = 0.0,
    dc_c1_cable_amps: float = 0.0,
    expect_batteryless_usb_pd_without_dc_c1: bool = False,
    dormant_uvc_streaming_requested: bool = False,
    fx3_native_uvc_present_claimed: bool = False,
    fx6_native_uvc_present_claimed: bool = False,
    streaming_protocol: str = "DISABLED",
    movie_rec_during_streaming: str = "DISABLE",
    rec_media_dur_hdmi_output: str = "ON",
    rec_target_slot: int = 2,
    e_nd_actuator_tx_count: int = 0,
    wireless_rf_packets_emitted: int = 0,
    usb_packets_transmitted: int = 0,
    simulated_passive_tx_bytes: int = 0,
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    h3_baselines: Optional[Mapping[str, str]] = None,
) -> RealHwBreathingCamIdCopyrightPowerSaveZoomCizRawCompUsbLunReport:
    donor = inspect_phase334_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p334_check_group_a_breathing_camid_and_sdhc(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        breathing_comp=breathing_comp,
        rec_fps=rec_fps,
        sq_enabled=sq_enabled,
        sq_fps=sq_fps,
        hdmi_raw_output=hdmi_raw_output,
        zoom_range=zoom_range,
        auto_framing_claimed=auto_framing_claimed,
        non_compliant_or_teleconverter_lens=non_compliant_or_teleconverter_lens,
        claimed_breathing_comp_resists_camera_reset=claimed_breathing_comp_resists_camera_reset,
        claimed_static_lens_comp_reset_by_camera_reset=claimed_static_lens_comp_reset_by_camera_reset,
        claimed_fx3_blocks_breathing_below_100fps_sq=claimed_fx3_blocks_breathing_below_100fps_sq,
        fx6_breathing_allows_sq_or_distortion_off_or_raw_claimed=fx6_breathing_allows_sq_or_distortion_off_or_raw_claimed,
        post_breathing_comp_requested=post_breathing_comp_requested,
        catalyst_app=catalyst_app,
        distortion_comp=distortion_comp,
        claimed_catalyst_browse_supports_breathing_comp=claimed_catalyst_browse_supports_breathing_comp,
        file_number_mode=file_number_mode,
        series_counter_reset_slot=series_counter_reset_slot,
        movie_file_counter_write_slot=movie_file_counter_write_slot,
        file_name_format=file_name_format,
        camera_id=camera_id,
        reel_number=reel_number,
        camera_position=camera_position,
        title_name=title_name,
        claimed_movie_file_settings_reset_by_camera_reset=claimed_movie_file_settings_reset_by_camera_reset,
        claimed_custom_movie_folder_supported=claimed_custom_movie_folder_supported,
        claimed_file_number_reset_resets_reel=claimed_file_number_reset_resets_reel,
        expect_rollover_mutates_cam_id_menu=expect_rollover_mutates_cam_id_menu,
        claimed_cam_id_reel_uses_yyyymmdd_date=claimed_cam_id_reel_uses_yyyymmdd_date,
        fx6_clip_naming_uses_project_menu_or_37char_claimed=fx6_clip_naming_uses_project_menu_or_37char_claimed,
        recording_media=recording_media,
        slot1_media_type=slot1_media_type,
        slot2_media_type=slot2_media_type,
        slot1_fs=slot1_fs,
        slot2_fs=slot2_fs,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_data_sector_writes=slot1_data_sector_writes,
        claimed_sdhc_no_4gb_split=claimed_sdhc_no_4gb_split,
    )
    gb = evaluate_p334_check_group_b_copyright_powersave_and_ntscpal(
        reset_action=reset_action,
        exposed_copyright_items=exposed_copyright_items,
        write_copyright_info=write_copyright_info,
        set_photographer=set_photographer,
        set_copyright=set_copyright,
        disp_copyright_info_requested=disp_copyright_info_requested,
        write_serial_number=write_serial_number,
        claimed_copyright_wiped_by_camera_reset=claimed_copyright_wiped_by_camera_reset,
        claimed_write_serial_wiped_by_camera_reset=claimed_write_serial_wiped_by_camera_reset,
        claimed_write_serial_still_only_in_v702=claimed_write_serial_still_only_in_v702,
        claimed_copyright_saved_in_camset=claimed_copyright_saved_in_camset,
        claimed_write_serial_excluded_from_camset=claimed_write_serial_excluded_from_camset,
        fx6_has_copyright_info_menu_claimed=fx6_has_copyright_info_menu_claimed,
        exposed_power_option_items=exposed_power_option_items,
        power_save_start_time=power_save_start_time,
        dormant_power_save_timer_requested=dormant_power_save_timer_requested,
        power_save_active_bypass_conditions=power_save_active_bypass_conditions,
        power_save_sleep_expected_during_bypass=power_save_sleep_expected_during_bypass,
        claimed_power_save_ignores_9_conditions=claimed_power_save_ignores_9_conditions,
        auto_power_off_temp=auto_power_off_temp,
        handheld_bare_skin_unacknowledged=handheld_bare_skin_unacknowledged,
        dormant_power_save_by_monitor_requested=dormant_power_save_by_monitor_requested,
        fx3_power_save_by_monitor_present_claimed=fx3_power_save_by_monitor_present_claimed,
        fx3_builtin_evf_present=fx3_builtin_evf_present,
        claimed_power_option_wiped_by_camera_reset=claimed_power_option_wiped_by_camera_reset,
        video_system=video_system,
        ntsc_pal_switch_requested=ntsc_pal_switch_requested,
        expect_ntsc_pal_no_reboot=expect_ntsc_pal_no_reboot,
        expect_cross_system_playback_without_switch=expect_cross_system_playback_without_switch,
        claimed_ntsc_pal_wiped_by_camera_reset=claimed_ntsc_pal_wiped_by_camera_reset,
        fx6_has_ntsc_pal_selector_claimed=fx6_has_ntsc_pal_selector_claimed,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_format_requested=slot1_format_requested,
        slot1_data_sector_writes=slot1_data_sector_writes,
    )
    gc = evaluate_p334_check_group_c_zoom_ciz_autoslow_and_dual_iso(
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        flexible_shutter_mode=flexible_shutter_mode,
        shutter_mode=shutter_mode,
        zoom_range=zoom_range,
        zoom_scale=zoom_scale,
        zoom_ring_rotate=zoom_ring_rotate,
        zoom_lever_stby_speed=zoom_lever_stby_speed,
        zoom_lever_rec_speed=zoom_lever_rec_speed,
        zoom_lever_2nd_speed=zoom_lever_2nd_speed,
        custom_key_zoom_stby_speed=custom_key_zoom_stby_speed,
        custom_key_zoom_rec_speed=custom_key_zoom_rec_speed,
        remote_zoom_speed_type=remote_zoom_speed_type,
        remote_zoom_fixed_stby_speed=remote_zoom_fixed_stby_speed,
        remote_zoom_fixed_rec_speed=remote_zoom_fixed_rec_speed,
        still_file_format=still_file_format,
        rec_fps=rec_fps,
        sq_enabled=sq_enabled,
        sq_fps=sq_fps,
        focus_area=focus_area,
        metering_mode=metering_mode,
        face_eye_prior_in_af=face_eye_prior_in_af,
        tracking_af_active=tracking_af_active,
        claimed_zoom_range_wiped_by_camera_reset=claimed_zoom_range_wiped_by_camera_reset,
        claimed_zoom_ring_rotate_wiped_by_camera_reset=claimed_zoom_ring_rotate_wiped_by_camera_reset,
        claimed_zoom_speeds_resist_camera_reset=claimed_zoom_speeds_resist_camera_reset,
        expect_smart_zoom_in_movie=expect_smart_zoom_in_movie,
        fx6_has_digital_zoom_claimed=fx6_has_digital_zoom_claimed,
        auto_slow_shutter=auto_slow_shutter,
        expect_auto_slow_shutter_active=expect_auto_slow_shutter_active,
        claimed_auto_slow_shutter_resists_reset=claimed_auto_slow_shutter_resists_reset,
        iso_mode=iso_mode,
        log_shooting_mode=log_shooting_mode,
        iso_range_limit_min=iso_range_limit_min,
        iso_range_limit_max=iso_range_limit_max,
        claimed_iso_range_limit_wiped_by_camera_reset=claimed_iso_range_limit_wiped_by_camera_reset,
        expect_iso_range_limit_caps_iso_auto=expect_iso_range_limit_caps_iso_auto,
        iso_auto_min_ss=iso_auto_min_ss,
        flash_enabled=flash_enabled,
        expect_iso_auto_min_ss_in_movie_or_sq=expect_iso_auto_min_ss_in_movie_or_sq,
        expect_iso_auto_min_ss_active_with_flash=expect_iso_auto_min_ss_active_with_flash,
        claimed_iso_auto_min_ss_resists_reset=claimed_iso_auto_min_ss_resists_reset,
        gamma_base_profile=gamma_base_profile,
        dual_base_iso_low=dual_base_iso_low,
        dual_base_iso_high=dual_base_iso_high,
        claimed_base_iso_menu_outside_cine_ei=claimed_base_iso_menu_outside_cine_ei,
        fx3_has_fx6_agc_claimed=fx3_has_fx6_agc_claimed,
    )
    gd = evaluate_p334_check_group_d_rawcomp_usblun_uvc_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        body_model_id=body_model_id,
        body_fw=body_fw,
        exposure_mode=exposure_mode,
        raw_file_type=raw_file_type,
        dormant_lossless_comp_requested=dormant_lossless_comp_requested,
        fx3_lossless_comp_present_claimed=fx3_lossless_comp_present_claimed,
        claimed_raw_file_type_resists_reset=claimed_raw_file_type_resists_reset,
        jh_file_type=jh_file_type,
        still_file_format=still_file_format,
        hlg_still_image=hlg_still_image,
        recording_media=recording_media,
        auto_switch_media=auto_switch_media,
        auto_switch_failover_to_slot1_requested=auto_switch_failover_to_slot1_requested,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        usb_connection_mode=usb_connection_mode,
        usb_lun_setting=usb_lun_setting,
        claimed_usb_lun_single_exposes_slot2=claimed_usb_lun_single_exposes_slot2,
        host_msc_isolated=host_msc_isolated,
        host_spotlight_fseventsd_fsck_unblocked=host_spotlight_fseventsd_fsck_unblocked,
        air_gapped_bench=air_gapped_bench,
        claimed_usb_settings_wiped_by_camera_reset=claimed_usb_settings_wiped_by_camera_reset,
        usb_power_supply=usb_power_supply,
        usb_power_terminal=usb_power_terminal,
        power_source=power_source,
        np_fz100_inserted=np_fz100_inserted,
        dc_c1_coupler_inserted=dc_c1_coupler_inserted,
        dc_c1_pd_watts=dc_c1_pd_watts,
        dc_c1_cable_amps=dc_c1_cable_amps,
        expect_batteryless_usb_pd_without_dc_c1=expect_batteryless_usb_pd_without_dc_c1,
        dormant_uvc_streaming_requested=dormant_uvc_streaming_requested,
        fx3_native_uvc_present_claimed=fx3_native_uvc_present_claimed,
        fx6_native_uvc_present_claimed=fx6_native_uvc_present_claimed,
        streaming_protocol=streaming_protocol,
        movie_rec_during_streaming=movie_rec_during_streaming,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        rec_target_slot=rec_target_slot,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        slot1_data_sector_writes=slot1_data_sector_writes,
        usb_packets_transmitted=usb_packets_transmitted,
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        claim_hardware_live_attach_authorized=claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=claim_cross_model_flash_authorized,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        h3_baselines=h3_baselines,
    )

    groups = (ga, gb, gc, gd)
    groups_passed = sum(1 for g in groups if g.passed)
    all_errors = (*ga.errors, *gb.errors, *gc.errors, *gd.errors)
    all_warnings = (*ga.warnings, *gb.warnings, *gc.warnings, *gd.warnings)

    if len(all_errors) > 0:
        overall_status = P334_GO_NO_GO_BLOCKED_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_FAILURE
        go_no_go = P334_GO_NO_GO_BLOCKED_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_FAILURE
    elif simulate_bench_dry_run and gd.tier0_receipt_verified:
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
    elif gd.tier0_receipt_verified:
        overall_status = P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED
        go_no_go = P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED
    else:
        overall_status = P334_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT

    slot1_mutated = bool(
        ga.slot1_tier0_vault_mutated or gb.slot1_tier0_vault_mutated or gd.slot1_tier0_vault_mutated
    )

    report = RealHwBreathingCamIdCopyrightPowerSaveZoomCizRawCompUsbLunReport(
        schema_version=P334_SCHEMA,
        phase_version=P334_VERSION,
        sony_help_guide_id=sony_help_guide_id,
        verification_mode=donor.verification_mode,
        simulate_bench_dry_run=bool(simulate_bench_dry_run),
        overall_status=overall_status,
        go_no_go=go_no_go,
        body_model_id_hex=hex(body_model_id),
        body_fw=body_fw,
        reset_action=reset_action,
        check_group_count=4,
        check_groups_passed=groups_passed,
        check_group_a=ga,
        check_group_b=gb,
        check_group_c=gc,
        check_group_d=gd,
        donor_inspection=donor,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        receipt_mode=gd.receipt_mode,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        cross_model_flash_authorized=False,
        slot1_tier0_vault_mutated=slot1_mutated,
        rf_nvs_p12_p13_writes_authorized=False,
        fx3_power_save_by_monitor_present=False,
        fx3_lossless_comp_raw_present=False,
        fx3_native_uvc_present=False,
        fx6_native_uvc_present=False,
        fx6_digital_zoom_present=False,
        fx3_copyright_resets_via_camera_settings_reset=False,
        fx3_write_serial_resets_via_camera_settings_reset=False,
        e_nd_actuator_tx_count=PHASE334_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=0,
        rf_packets_transmitted=PHASE334_WIRELESS_RF_PACKETS_EMITTED,
        wireless_rf_packets_emitted=PHASE334_WIRELESS_RF_PACKETS_EMITTED,
        slot1_data_sector_writes=PHASE334_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE334_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE334_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE334_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwBreathingCamIdCopyrightPowerSaveZoomCizRawCompUsbLunReport(
        **{
            **report.to_dict(),
            "check_group_a": ga,
            "check_group_b": gb,
            "check_group_c": gc,
            "check_group_d": gd,
            "donor_inspection": donor,
            "report_sha256": digest,
        }
    )


def run_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(
    **kwargs: Any,
) -> RealHwBreathingCamIdCopyrightPowerSaveZoomCizRawCompUsbLunReport:
    return evaluate_realhw_breathing_camid_copyright_powersave_zoom_ciz_rawcomp_and_usblun_preflight(**kwargs)


def verify_phase334_report(
    payload: Union[Mapping[str, Any], RealHwBreathingCamIdCopyrightPowerSaveZoomCizRawCompUsbLunReport],
) -> Phase334ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P334_SCHEMA:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r} != {P334_SCHEMA!r}")
    if payload.get("sony_help_guide_id") != P334_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_334_VALID_GO_NO_GO_VALUES:
        errors.append(f"invalid go_no_go: {payload.get('go_no_go')!r}")

    locked_false_fields = (
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "cross_model_flash_authorized",
        "rf_nvs_p12_p13_writes_authorized",
        "fx3_power_save_by_monitor_present",
        "fx3_lossless_comp_raw_present",
        "fx3_native_uvc_present",
        "fx6_native_uvc_present",
        "fx6_digital_zoom_present",
        "fx3_copyright_resets_via_camera_settings_reset",
        "fx3_write_serial_resets_via_camera_settings_reset",
    )
    for field in locked_false_fields:
        if payload.get(field) is not False:
            errors.append(f"hard-locked boolean {field} must be False")

    locked_zero_fields = (
        "e_nd_actuator_tx_count",
        "e_nd_i2c_tx_bytes",
        "rf_packets_transmitted",
        "wireless_rf_packets_emitted",
        "slot1_data_sector_writes",
        "usb_packets_transmitted",
        "passive_tx_bytes_emitted",
        "raw_firmware_bytes_leaked",
    )
    for field in locked_zero_fields:
        if payload.get(field) != 0:
            errors.append(f"hard-locked zero telemetry {field} must be 0")

    expected_sha = _canonical_sha256_dict(payload)
    if payload.get("report_sha256") != expected_sha:
        errors.append(f"report_sha256 mismatch: {payload.get('report_sha256')!r} != {expected_sha!r}")

    if payload.get("go_no_go") in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P334_GO_NO_GO_BREATHING_CAMID_COPYRIGHT_POWERSAVE_ZOOM_CIZ_RAWCOMP_USBLUN_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase334ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase334_markdown(
    report: RealHwBreathingCamIdCopyrightPowerSaveZoomCizRawCompUsbLunReport,
) -> str:
    lines = [
        f"# Phase 334 — 16th Physical Bench Readiness Preflight (`{report.schema_version}`)",
        "",
        f"- **Overall Status**: `{report.overall_status}`",
        f"- **Go/No-Go**: `{report.go_no_go}`",
        f"- **Verification Mode**: `{report.verification_mode}` (Dry Run: `{report.simulate_bench_dry_run}`)",
        f"- **Check Groups Passed**: `{report.check_groups_passed}/{report.check_group_count}`",
        f"- **Tier-0 Receipt Verified**: `{report.tier0_receipt_verified}` (`{report.receipt_mode}`)",
        f"- **H0 == H3 Surfaces**: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`",
        f"- **Safety Redlines**: `ready_attach={report.overall_ready_for_hardware_attach}`, "
        f"`emmc_writes={report.persistent_emmc_writes_authorized}`, "
        f"`cross_model_flash={report.cross_model_flash_authorized}`, "
        f"`rf_pkts={report.rf_packets_transmitted}`, `usb_pkts={report.usb_packets_transmitted}`, "
        f"`slot1_writes={report.slot1_data_sector_writes}`, `leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"breathing_comp=`{report.check_group_a.breathing_comp}` (Resettable, Catalyst Prepare/Plugin + Auto Distortion Comp), "
        f"file_name_format=`{report.check_group_a.file_name_format}` (`Cam ID + Reel#` `YYMMDD` / `<= 37` chars / `SDHC` `4 GB` split)",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"copyright=`{report.check_group_b.write_copyright_info}` (`<= 46` chars, Round-57 Reset-immune, CAMSET-excluded), "
        f"write_serial=`{report.check_group_b.write_serial_number}` (Reset-immune), "
        f"power_save=`{report.check_group_b.power_save_start_time}` (9-cond bypass; dormant `Power Save by Monitor` `EOPNOTSUPP=95`), "
        f"video_system=`{report.check_group_b.video_system}` (`base.uxc` format guard `EROFS=30`)",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"zoom=`{report.check_group_c.zoom_range}` (`1..8` speeds, CIZ `1.5x/2x`, FX6 zero Digital Zoom), "
        f"auto_slow_shutter=`{report.check_group_c.auto_slow_shutter}` (6+ lockouts), "
        f"dual_base_iso=`{report.check_group_c.gamma_base_profile}` (`{report.check_group_c.dual_base_iso_low}/{report.check_group_c.dual_base_iso_high}`)",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"raw_file_type=`{report.check_group_d.raw_file_type}` (dormant Lossless Comp `0x6b56` `EOPNOTSUPP=95`), "
        f"usb_mode=`{report.check_group_d.usb_connection_mode}`, usb_lun=`{report.check_group_d.usb_lun_setting}` "
        f"(`Single` = Slot 1 ONLY hazard), native_uvc=`{report.check_group_d.fx3_native_uvc_present}/{report.check_group_d.fx6_native_uvc_present}` (`EOPNOTSUPP=95`)",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
