"""Phase 321: 14th Real-Hardware Physical Bench Readiness Verifier (Waves 60-61).

Verifies Sony ``ILME-FX3 Ver. 7.02`` (``ilc/2210``, Model ``0x91030080``) vs ``ILME-FX6`` (``Ver. 6.01``)
empirical hardware/firmware/menu invariants across Waves 60-61 before any physical bench session:

1. **Check Group A (Wave 60 §§1-2)** — ``[Rec. Media Settings]`` Overflow Trap, ``VPG200/VPG400`` Card-Speed
   Gates & ``[Proxy Settings]`` ``M4ROOT/SUB/*S03.MP4`` Firewall:
   - Dormant ``[Prioritize Rec. Media]`` (``_f 0x719e``, ``0`` hits in FX3 ``appFw.so``) rejected ``EOPNOTSUPP=95``.
   - Active Ver. 2.00+-7.02 ``[Recording Media]`` (Still 4 modes incl. ``Sort Recording`` vs Movie/S&Q 3 modes
     without movie sort; ``Simult. Recording`` requires matching ``exFAT`` or ``FAT32`` across both slots) +
     ``[Auto Switch Media]`` (``_f 0x6dd9``, ``BKID_APP_setting_relay_rec``, Initialize-only / survives
     ``[Camera Settings Reset]``).
   - **Slot-2 -> Slot-1 Overflow Trap Dual Lock**: Physical bench with a Slot-1 Tier-0 recovery vault requires
     ``Recording Media = Slot 2`` AND ``Auto Switch Media = Off`` (``RELAY_REC_OFF``) PLUS Slot-1 ``EROFS=30``
     (``slot1_data_sector_writes == 0``), vs ``FX6`` ``Simul Rec`` + independent ``Rec Button Set`` +
     ``Relay Rec`` (mutually exclusive with ``LAN``/``Streaming``/``Proxy Rec``/``Chunk``).
   - Card speed gates (``SDXC V60/V90`` vs mandatory ``CFexpress Type A VPG200+`` in ``S&Q XAVC S-I 4K 1200 Mbps``
     / ``S&Q HD 890 Mbps`` & ``base.uxc`` ``VPG400`` ``0xe224`` caution; ``CFexpress Type B`` rejected) +
     ``[Proxy Settings]`` (``BKID_APP_setting_sq_proxy_{recording,file_format,record_setting}``: ``XAVC S HD``
     ``1280x720 6M 8bit`` vs ``XAVC HS HD`` ``1920x1080 9M/16M 10bit``; blocked ONLY at ``100p/119.88p`` &
     S&Q ``100/120fps``, NOT directly disabled on ``XAVC S-I DCI 4K <= 59.94p``; ``M4ROOT/SUB/<Clip>S03.MP4``
     coupled delete/protect ``EROFS=30`` on Slot 1 vs ``FX6`` ``1920x1080 9M`` + ``Chunk``).

2. **Check Group B (Wave 60 §§3-4)** — ``[Creators' Cloud]`` / ``[C3 Portal]`` / ``[Cnct. while Power OFF]``
   Zero-RF BLE Hazard & Exact ``6 x 7 = 42`` ``[My Menu]`` vs ``FX6`` 20-Item PIN ``User Menu``:
   - ``[Cloud Connection *]`` & ``[Cloud Information *]`` (``BKID_APP_setting_cloud_connection``, mutually
     exclusive with FTP ``CLOUD_CONNECTION_ON_FTP_OFF``, Ver. 7.00+ ``Clip Flag OK/NG/KEEP`` filter,
     **survives BOTH ``[Camera Settings Reset]`` AND ``[Initialize]``** via ``*`` persistence) + ``[C3 Portal]``
     (``Ver. 4.00+`` LUT/settings sync).
   - **Zero-RF Bench Power-OFF BLE Guard**: ``[Cnct. while Power OFF]`` (``_f 0x6ab3``,
     ``BKID_APP_extern_menu_cnct_while_power_off`` / ``UIBIZ_KEY_BLUETOOTH_LOWENERGY_POWER``, survives
     ``[Camera Settings Reset]``) keeps BLE energized even with the power switch ``OFF``! Physical bench
     preflight requires BOTH ``Airplane Mode == ON`` AND ``Cnct. while Power OFF == OFF`` AND
     ``Bluetooth Function == OFF`` (``rf_packets_transmitted == 0``) vs Bluetooth-less ``ILME-FX6``.
   - Exact **``6 x 7 = 42`` ``[My Menu]`` NVRAM slots** (``BKID_APP_mymenu_group{1..6}_setting_list{0..6}``,
     ``group0/group7/list7 == 0`` hits; NOT 36 or 30; ``(Playback)`` items disallowed; survives
     ``[Camera Settings Reset]``) vs ``ILME-FX6`` ``20``-item ``User Menu`` + ``User Menu Only`` + 4-digit PIN
     (``0000..9999``, Dial+MENU unlock, excluded from ``All File``) ``User Menu with Lock``.

3. **Check Group C (Wave 61 §§1-2)** — Passive-Only ``FTP``/``FTPES`` 9-Server Vault + ``USB-LAN``
   Airplane-Mode Bypass & White Balance / ``Cine EI`` / ``Custom 1..3``:
   - ``FX3`` ``Server 1..9`` (``BKID_APP_ftp_server_settings_*0..8``): supports ONLY **Passive-Mode ``FTP`` and
     ``FTPES`` (``FTPS`` Explicit TLS, ``_f 0x6553``)** — ``0`` ``SFTP`` hits, ``0`` Active Mode hits, ``0``
     ``Transfer JPEG/HEIF Size`` hits in FX3 ``appFw.so`` (vs ``FX6`` ``Server 1..3`` + Active/Passive +
     ``certification.pem`` on ``Slot B`` + ``Chunk`` Auto Upload).
   - **Slot-1 ``AVF_INFO`` + ``cacert.pem`` Vault Guard & Zero-RF ``USB-LAN`` Disconnect**:
     ``save_ftp_transfer_list_to_media`` / ``CONTENT_INFO_FTP_TRANS_STAT_*`` mutates ``AVF_INFO`` (``EROFS=30`` on
     Slot 1); ``cacert.pem`` (``<= 1 MB``) imports read-only from Slot 1; AND **``[Airplane Mode] = On`` does
     NOT block wired ``USB-LAN`` FTP (``USB_ETHER``)** — bench preflight MUST verify ``USB-LAN/Tethering``
     disconnected/disabled!
   - White Balance (``2500K..9900K`` 100K steps, ``Custom 1..3`` excluded from ``CAMSET*.DAT`` & reset-resistant,
     ``Custom WB Error 0x0220`` under Log/S-Log3/PPLUT, ``Cine EI`` locks out ``Auto``/``Underwater Auto``,
     Still ``[Shutter AWB Lock]`` resists Reset vs Movie ``[Shockless WB]`` resets; ``FX6`` ``WHT BAL`` +
     ``Memory A..H`` + ``ATW Speed 1..5``).

4. **Check Group D (Wave 61 §§3-4 & Tier-0)** — ``1..7`` / ``1..5`` Movie AF, Ver. 6.00+ External ``Focus Map``,
   ``16``-State ``[Aspect Marker]`` + ``4``-Color ``[Peaking]``, ``16/16 H0 == H3`` & Dual-Media ``528 B FX3RCPT1``:
   - Movie AF: **BOTH ``FX3`` and ``FX6`` use ``1..7`` ``AF Transition Speed`` and ``1..5``
     ``AF Subj. Shift Sens.``** (never ``1..7``), ``SELP1650``/``SEL18200LE`` ``[AF Assist]`` incompatibility.
   - **ZERO in-body ``FX3 Focus Map``**: Ver. 6.00+ external *Monitor & Control* (``to_remote_event_focus_map``)
     blocked at ``>= 150 fps`` (``100p/119.88p < 150 fps`` allowed!), playback, non-PDAF/adapter/no-lens,
     ``Auto Framing``, USB remote/UVC (FX3 has zero UVC) vs native ``FX6 Focus Map``.
   - ``16``-state (``Off`` + ``15`` ratios) ``[Aspect Marker]`` + ``[Safety Zone]`` (``Off/80%/90%``) + ``4``-color
     ``[Peaking Display]`` (``Red/Yellow/Blue/White``, no FX6 ``B&W`` or ``User Box``; all ``8`` items resist
     ``[Camera Settings Reset]`` and never output over HDMI; Marker hides under ``[Focus Magnifier]``).
   - ``16/16 H0 == H3`` hardware topology invariants + dual-media ``528 B FX3RCPT1`` Tier-0 receipt gating
     (``BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT`` offline vs ``DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`` dry-run).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Tuple

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

P321_VERSION = "phase321_v1"
PHASE_321_VERSION = P321_VERSION
P321_SCHEMA = "realhw_preflight14_rec_media_proxy_cloud_mymenu_ftpes_v1"
P321_SCHEMA_VERSION = P321_SCHEMA
PHASE_321_SCHEMA = P321_SCHEMA
PHASE321_SCHEMA = P321_SCHEMA
REALHW_REC_MEDIA_AUTOSWITCH_PROXY_CLOUD_MYMENU_FTPES_SCHEMA = P321_SCHEMA
P321_SONY_HELP_GUIDE_ID = "ilc/2210"

P321_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED = (
    "READONLY_PREFLIGHT14_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED"
)
P321_GO_NO_GO_BLOCKED_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_FAILURE = (
    "BLOCKED_PREFLIGHT14_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_FAILURE"
)
PHASE_321_VALID_GO_NO_GO_VALUES = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED,
    P321_GO_NO_GO_BLOCKED_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_FAILURE,
)

# Bounded donor paths (read-only O_RDONLY)
P321_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
    ("fx6_appfw_so", "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"),
    ("fx3_im_elf", "sony-firmware-20261024/stage183-request-consumer-and-early-entry/evidence/usb-main-dependency/originals/bin/im.elf"),
    ("fx3_libjiritsu_so", "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libJiritsu.so"),
    ("fx3_libusbbuspower_so", "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libUsbBusPower.so"),
    ("fx3_upm_ko", "fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko"),
)
P321_HEADER_READ_BYTES = 64

# Unconditional safety / zero-leak constants
PHASE321_RAW_FIRMWARE_BYTES_LEAKED = 0
PHASE321_PASSIVE_TX_BYTES_EMITTED = 0
PHASE321_USB_PACKETS_TRANSMITTED = 0
PHASE321_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE321_SLOT1_DATA_SECTOR_WRITES = 0
PHASE321_E_ND_ACTUATOR_TX_COUNT = 0

P321_ERRNO_EOPNOTSUPP = 95
P321_ERRNO_EROFS = 30
P321_ERRNO_EBUSY = 16
P321_ERRNO_EINVAL = 22

# Check Group IDs
P321_CHECK_GROUP_A_ID = "GROUP_A_REC_MEDIA_OVERFLOW_TRAP_VPG400_AND_PROXY_SUB_FIREWALL"
P321_CHECK_GROUP_B_ID = "GROUP_B_CLOUD_POWEROFF_BLE_ZERO_RF_AND_MYMENU_42_SLOTS"
P321_CHECK_GROUP_C_ID = "GROUP_C_FTPES_PASSIVE_9SERVER_USBLAN_BYPASS_AND_WB_CINE_EI"
P321_CHECK_GROUP_D_ID = "GROUP_D_AF_SENS_1_5_MC_FOCUS_MAP_15RATIO_MARKER_AND_TIER0"
PHASE_321_CHECK_GROUP_IDS = (
    P321_CHECK_GROUP_A_ID,
    P321_CHECK_GROUP_B_ID,
    P321_CHECK_GROUP_C_ID,
    P321_CHECK_GROUP_D_ID,
)

# Common mode enums
P321_VALID_RESET_ACTIONS = ("NONE", "CAMERA_SETTINGS_RESET", "RESET_NETWORK_SET", "INITIALIZE")
P321_VALID_SHOOT_MODES = ("PHOTO", "MOVIE", "S_AND_Q")
P321_VALID_ON_OFF = ("ON", "OFF")
P321_VALID_LOG_SHOOTING_MODES = ("OFF", "FLEXIBLE_ISO", "CINE_EI_QUICK", "CINE_EI")

# Wave 60 Group A constants
P321_DORMANT_PRIORITIZE_REC_MEDIA_RESID16_HEX = "0x719e"
P321_AUTO_SWITCH_MEDIA_RESID16_HEX = "0x6dd9"
P321_VPG400_CAUTION_RESIDS = ("0xe224", "0xe93f", "0xe9aa")
P321_PROXY_SETTINGS_RESID16_HEX = "0x6e3f"
P321_DORMANT_PROXY_16M_8BIT_RESID16_HEX = "0x6b8f"

P321_STILL_RECORDING_MEDIA_FOUR_MODES = (
    "SLOT_1",
    "SLOT_2",
    "SIMULTANEOUS_RECORDING",
    "SORT_RECORDING",
)
P321_MOVIE_RECORDING_MEDIA_THREE_MODES = (
    "SLOT_1",
    "SLOT_2",
    "SIMULTANEOUS_RECORDING",
)
P321_VALID_SLOT_FILESYSTEMS = ("EXFAT", "FAT32")
P321_VALID_MEDIA_SPEED_GRADES = (
    "CFEXPRESS_A_VPG400",
    "CFEXPRESS_A_VPG200",
    "SDXC_V90",
    "SDXC_V60",
    "SDXC_V30",
    "SDHC_U3",
    "CFEXPRESS_TYPE_B",
)
P321_VALID_MOVIE_FILE_FORMATS = (
    "XAVC_S_I_DCI_4K",
    "XAVC_S_I_4K",
    "XAVC_S_I_HD",
    "XAVC_S_4K",
    "XAVC_HS_4K",
    "XAVC_S_HD",
)
P321_VALID_PROXY_FILE_FORMATS = ("XAVC_S_HD", "XAVC_HS_HD")
P321_VALID_PROXY_RECORD_SETTINGS = (
    "1280x720_6M_8BIT",
    "1920x1080_9M_10BIT",
    "1920x1080_16M_10BIT",
)
P321_DORMANT_PROXY_RECORD_SETTINGS = (
    "1920x1080_16M_8BIT",
    "1920x1080_9M_8BIT",
)
P321_PROXY_CUTOFF_FPS = 100.0
P321_PROXY_SUB_DIR_REL = "M4ROOT/SUB"
P321_PROXY_SUB_SUFFIX = "S03.MP4"

# Wave 60 Group B constants
P321_CNCT_WHILE_POWER_OFF_RESID16_HEX = "0x6ab3"
P321_VALID_CLIP_FLAGS = ("NONE", "OK", "NG", "KEEP")
P321_MYMENU_EXACT_PAGES = 6
P321_MYMENU_EXACT_SLOTS_PER_PAGE = 7
P321_MYMENU_EXACT_TOTAL_SLOTS = 42
P321_FX6_USER_MENU_MAX_ITEMS = 20
P321_PIN_4DIGIT_RE = re.compile(r"^[0-9]{4}$")

# Wave 61 Group C constants
P321_FTPES_TLS_RESID16_HEX = "0x6553"
P321_DORMANT_TRANSFER_JPEG_HEIF_RESIDS = ("0x6aed", "0x63dd")
P321_CUSTOM_WB_ERROR_RESID16_HEX = "0x0220"
P321_CUSTOM_WB_SETUP_RESID16_HEX = "0x63ac"
P321_FX3_FTP_SERVER_MIN = 1
P321_FX3_FTP_SERVER_MAX = 9
P321_FX6_FTP_SERVER_MAX = 3
P321_VALID_FTP_PROTOCOLS = ("NONE", "FTP", "FTPES", "SFTP")
P321_VALID_FTP_TRANSFER_MODES = ("PASSIVE", "ACTIVE")
P321_CACERT_FILENAME = "cacert.pem"
P321_CACERT_MAX_BYTES = 1_048_576  # 1 MiB
P321_VALID_NETWORK_TRANSPORTS = ("NONE", "USB_LAN", "WIRELESS_RF")

P321_WB_VALID_MODES = (
    "AUTO",
    "DAYLIGHT",
    "SHADE",
    "CLOUDY",
    "INCANDESCENT",
    "FLUORESCENT_WARM_WHITE",
    "FLUORESCENT_COOL_WHITE",
    "FLUORESCENT_DAY_WHITE",
    "FLUORESCENT_DAYLIGHT",
    "FLASH",
    "UNDERWATER_AUTO",
    "C_TEMP_FILTER",
    "CUSTOM_1",
    "CUSTOM_2",
    "CUSTOM_3",
)
P321_WB_CINE_EI_BLOCKED_MODES = ("AUTO", "UNDERWATER_AUTO")
P321_WB_KELVIN_MIN_K = 2500
P321_WB_KELVIN_MAX_K = 9900
P321_WB_KELVIN_STEP_K = 100
P321_WB_AB_MIN = -7
P321_WB_AB_MAX = 7
P321_WB_GM_MIN = -7
P321_WB_GM_MAX = 7
P321_VALID_PRIORITY_AWB_MODES = ("STANDARD", "AMBIENCE", "WHITE")
P321_VALID_SHUTTER_AWB_LOCK_MODES = ("OFF", "SHUT_HALF_DOWN", "CONT_SHOOTING", "BOTH")
P321_VALID_SHOCKLESS_WB_MODES = ("OFF", "1_FAST", "2", "3_SLOW")
P321_SLOG3_PICTURE_PROFILES = ("PP8", "PP9")
P321_PPLUT_PICTURE_PROFILES = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")

# Wave 61 Group D constants
P321_AF_TRANSITION_SPEED_MIN = 1
P321_AF_TRANSITION_SPEED_MAX = 7
P321_AF_TRANSITION_SPEED_DEFAULT = 5
P321_AF_SUBJ_SHIFT_SENS_MIN = 1
P321_AF_SUBJ_SHIFT_SENS_MAX = 5
P321_AF_SUBJ_SHIFT_SENS_DEFAULT = 5
P321_AF_ASSIST_INCOMPATIBLE_LENSES = ("SELP1650", "SEL18200LE")
P321_MC_FOCUS_MAP_FPS_CUTOFF = 150.0

P321_ASPECT_MARKER_16_STATES: Tuple[str, ...] = (
    "OFF",
    "9:16",
    "4:5",
    "1:1",
    "4:3",
    "13:9",
    "14:9",
    "15:9",
    "16:9",
    "17:9",
    "1.66:1",
    "1.85:1",
    "1.91:1",
    "2:1",
    "2.35:1",
    "2.39:1",
)
P321_MARKER_DISPLAY_FIVE_ITEMS: Tuple[str, ...] = (
    "MARKER_DISPLAY",
    "CENTER_MARKER",
    "ASPECT_MARKER",
    "SAFETY_ZONE",
    "GUIDEFRAME",
)
P321_PEAKING_DISPLAY_THREE_ITEMS: Tuple[str, ...] = (
    "PEAKING_DISPLAY",
    "PEAKING_LEVEL",
    "PEAKING_COLOR",
)
P321_VALID_SAFETY_ZONES = ("OFF", "80PCT", "90PCT")
P321_VALID_PEAKING_LEVELS = ("HIGH", "MID", "LOW")
P321_FX3_PEAKING_FOUR_COLORS = ("RED", "YELLOW", "BLUE", "WHITE")

# Deterministic Error Codes
P321_GA_ERR_MODEL_OR_FW_FLOOR = "P321_GA_ERR_MODEL_OR_FW_FLOOR"
P321_GA_ERR_PRIORITIZE_REC_MEDIA_DORMANT_OR_MOVIE_SORT = (
    "P321_GA_ERR_PRIORITIZE_REC_MEDIA_DORMANT_OR_MOVIE_SORT"
)
P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH = (
    "P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH"
)
P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE = (
    "P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE"
)
P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT = (
    "P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT"
)

P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION = (
    "P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION"
)
P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD = (
    "P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD"
)
P321_GB_ERR_MYMENU_42_SLOTS_PLAYBACK_OR_FX6_PIN_MENU = (
    "P321_GB_ERR_MYMENU_42_SLOTS_PLAYBACK_OR_FX6_PIN_MENU"
)

P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE = (
    "P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE"
)
P321_GC_ERR_SLOT1_AVF_INFO_CACERT_OR_USBLAN_AIRPLANE_BYPASS = (
    "P321_GC_ERR_SLOT1_AVF_INFO_CACERT_OR_USBLAN_AIRPLANE_BYPASS"
)
P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE = (
    "P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE"
)

P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS = (
    "P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS"
)
P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC = (
    "P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC"
)
P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET = (
    "P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET"
)
P321_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P321_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P321_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P321_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"


@dataclass(frozen=True)
class Phase321DonorInspectionResult:
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
class P321CheckGroupARecMediaOverflowProxyResult:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    shoot_mode: str
    recording_media: str
    auto_switch_media: str
    slot1_fs: str
    slot2_fs: str
    media_speed_grade: str
    movie_file_format: str
    movie_bitrate_mbps: int
    proxy_recording: str
    proxy_file_format: str
    proxy_record_setting: str
    rec_fps: float
    sq_enabled: bool
    sq_fps: float
    slot1_contains_tier0_dump: bool
    slot1_wp_locked: bool
    slot1_overflow_trap_locked_off: bool
    fx3_prioritize_rec_media_present: bool
    fx3_movie_sort_recording_present: bool
    proxy_allowed_on_dci4k_le60p: bool
    slot1_data_sector_writes: int
    slot1_tier0_vault_mutated: bool


@dataclass(frozen=True)
class P321CheckGroupBCloudBleZeroRfMyMenuResult:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    cloud_connection: str
    c3_portal_enabled: bool
    clip_flag_filter: str
    airplane_mode: str
    cnct_while_power_off: str
    bluetooth_function: str
    wifi_enabled: bool
    wireless_rf_packets_emitted: int
    rf_nvs_p12_p13_writes_authorized: bool
    mymenu_pages: int
    mymenu_slots_per_page: int
    mymenu_total_slots: int
    fx3_mymenu_30_or_36_slots_only: bool
    fx6_user_menu_max_items: int
    fx6_user_menu_pin_valid: bool


@dataclass(frozen=True)
class P321CheckGroupCFtpesPassiveUsbLanWbResult:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    ftp_transfer_func: str
    ftp_server_slot: int
    ftp_protocol: str
    ftp_transfer_mode: str
    fx3_ftp_sftp_present: bool
    fx3_ftp_active_mode_present: bool
    fx3_ftp_transfer_jpeg_size_present: bool
    usb_lan_tethering: str
    usb_lan_cnct_launch: str
    network_transport: str
    cacert_pem_size_bytes: int
    wb_mode: str
    wb_kelvin_k: int
    wb_ab_shift: int
    wb_gm_shift: int
    log_shooting_mode: str
    picture_profile: str
    priority_set_in_awb: str
    shutter_awb_lock: str
    shockless_wb: str
    slot1_tier0_vault_mutated: bool


@dataclass(frozen=True)
class P321CheckGroupDAfFocusMapMarkerTier0Result:
    group_id: str
    passed: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]
    af_transition_speed: int
    af_subj_shift_sens: int
    fx3_af_subj_shift_7_levels_present: bool
    af_assist: str
    lens_model: str
    fx3_in_body_focus_map_present: bool
    fx3_uvc_streaming_present: bool
    mc_focus_map_enabled: bool
    mc_focus_map_fps: float
    aspect_marker: str
    aspect_marker_state_count: int
    safety_zone: str
    peaking_display: str
    peaking_level: str
    peaking_color: str
    focus_magnifier_active: bool
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    e_nd_actuator_tx_count: int
    usb_packets_transmitted: int
    passive_tx_bytes_emitted: int
    raw_firmware_bytes_leaked: int


@dataclass(frozen=True)
class Phase321ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwRecMediaAutoswitchProxyCloudMyMenuFtpesReport:
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
    check_group_a: P321CheckGroupARecMediaOverflowProxyResult
    check_group_b: P321CheckGroupBCloudBleZeroRfMyMenuResult
    check_group_c: P321CheckGroupCFtpesPassiveUsbLanWbResult
    check_group_d: P321CheckGroupDAfFocusMapMarkerTier0Result
    donor_inspection: Phase321DonorInspectionResult
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
    fx3_prioritize_rec_media_present: bool
    fx3_movie_sort_recording_present: bool
    fx3_mymenu_30_or_36_slots_only: bool
    fx3_ftp_sftp_present: bool
    fx3_ftp_active_mode_present: bool
    fx3_ftp_transfer_jpeg_size_present: bool
    fx3_in_body_focus_map_present: bool
    fx3_uvc_streaming_present: bool
    fx3_af_subj_shift_7_levels_present: bool
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
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


def _canonical_sha256_dict(payload: Mapping[str, Any]) -> str:
    clone = json.loads(json.dumps(dict(payload)))
    clone.pop("report_sha256", None)
    donor_block = clone.get("donor_inspection")
    if isinstance(donor_block, dict):
        donor_block.pop("elapsed_seconds", None)
    encoded = json.dumps(clone, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _bounded_read_header(path: Path, max_bytes: int = P321_HEADER_READ_BYTES) -> int:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        data = os.read(fd, max_bytes)
        return len(data)
    finally:
        os.close(fd)


def _resolve_work_root_or_none(
    *,
    force_clean_room: bool = False,
) -> Optional[Path]:
    """Return the first ``work/`` root containing BYOF donor artifacts, or ``None`` on donorless CI / clean-room."""
    if force_clean_room or is_forced_clean_room():
        return None
    for candidate in iter_work_roots():
        if not candidate.is_dir():
            continue
        if any((candidate / rel).is_file() for _lbl, rel in P321_BOUNDED_DONOR_PATHS):
            return candidate
    return None


def inspect_phase321_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase321DonorInspectionResult:
    """Inspect local donor headers strictly via bounded O_RDONLY (< 50ms) with clean-room fallback."""
    t0 = time.monotonic()
    clean_room = bool(force_clean_room) if force_clean_room is not None else is_forced_clean_room()
    if clean_room:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase321DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_uxc_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE321_RAW_FIRMWARE_BYTES_LEAKED,
        )

    effective_work_root = work_root if work_root is not None else _resolve_work_root_or_none(force_clean_room=False)
    if effective_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase321DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_uxc_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE321_RAW_FIRMWARE_BYTES_LEAKED,
        )

    checked: List[str] = []
    bytes_total = 0
    found_map: Dict[str, bool] = {}
    for label, rel in P321_BOUNDED_DONOR_PATHS:
        resolved: Optional[Path] = None
        if label == "fx6_appfw_so" and fx6_lib_dir is not None:
            cand = fx6_lib_dir / "appFw.so"
            if cand.is_file():
                resolved = cand
        if label == "fx3_upm_ko" and fx3_modules_dir is not None:
            cand = fx3_modules_dir / "upm.ko"
            if cand.is_file():
                resolved = cand
        if resolved is None and effective_work_root is not None:
            cand = effective_work_root / rel
            if cand.is_file():
                resolved = cand
        if resolved is None:
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
    return Phase321DonorInspectionResult(
        verification_mode=mode,
        donor_tree_present=donor_present,
        fx3_appfw_present=found_map.get("fx3_libjiritsu_so", False) and found_map.get("fx3_im_elf", False),
        fx6_appfw_present=found_map.get("fx6_appfw_so", False),
        fx3_uxc_present=found_map.get("fx3_libusbbuspower_so", False) and found_map.get("fx3_upm_ko", False),
        checked_paths=tuple(checked),
        bytes_read_total=bytes_total,
        elapsed_seconds=elapsed,
        within_budget=elapsed <= max_seconds,
        raw_firmware_bytes_leaked=PHASE321_RAW_FIRMWARE_BYTES_LEAKED,
    )


def evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P321_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    recording_media: str = "SLOT_2",
    auto_switch_media: str = "OFF",
    dormant_prioritize_rec_media_requested: bool = False,
    fx3_prioritize_rec_media_present_claimed: bool = False,
    fx3_movie_sort_recording_present_claimed: bool = False,
    claimed_auto_switch_wiped_by_camera_reset: bool = False,
    slot1_fs: str = "EXFAT",
    slot2_fs: str = "EXFAT",
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_rec_write_requested: bool = False,
    slot1_data_sector_writes: int = 0,
    fx3_independent_rec_button_slot_set_claimed: bool = False,
    fx6_relay_with_proxy_streaming_chunk_claimed: bool = False,
    media_speed_grade: str = "CFEXPRESS_A_VPG200",
    movie_file_format: str = "XAVC_S_I_4K",
    movie_bitrate_mbps: int = 240,
    rec_fps: float = 23.98,
    sq_enabled: bool = False,
    sq_fps: float = 60.0,
    proxy_recording: str = "OFF",
    proxy_file_format: str = "XAVC_S_HD",
    proxy_record_setting: str = "1280x720_6M_8BIT",
    dormant_proxy_8bit_fhd_requested: bool = False,
    vpg400_caution_acknowledged: bool = True,
    claimed_sdhc_no_4gb_split: bool = False,
    claimed_proxy_blocked_on_dci4k_60p: bool = False,
    claimed_proxy_resists_camera_reset: bool = False,
    proxy_slot1_write_or_coupled_delete_requested: bool = False,
    claimed_fx3_has_fx6_chunk_upload: bool = False,
) -> P321CheckGroupARecMediaOverflowProxyResult:
    errors: List[str] = []
    warnings: List[str] = []

    if (
        body_model_id != TARGET_MODEL_ID_INT
        or body_fw != TARGET_BODY_FW
        or sony_help_guide_id != P321_SONY_HELP_GUIDE_ID
    ):
        errors.append(
            f"{P321_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX} fw={TARGET_BODY_FW} "
            f"help_guide={P321_SONY_HELP_GUIDE_ID}, got {hex(body_model_id)} fw={body_fw} "
            f"help_guide={sony_help_guide_id}"
        )

    if reset_action not in P321_VALID_RESET_ACTIONS:
        errors.append(f"{P321_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action={reset_action}")
    if shoot_mode not in P321_VALID_SHOOT_MODES:
        errors.append(f"{P321_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode={shoot_mode}")

    # Dormant [Prioritize Rec. Media] (_f 0x719e) & Movie Sort Recording
    if dormant_prioritize_rec_media_requested or fx3_prioritize_rec_media_present_claimed:
        errors.append(
            f"{P321_GA_ERR_PRIORITIZE_REC_MEDIA_DORMANT_OR_MOVIE_SORT}: "
            f"[Prioritize Rec. Media] ({P321_DORMANT_PRIORITIZE_REC_MEDIA_RESID16_HEX}) has 0 hits in FX3 appFw.so "
            f"(errno={P321_ERRNO_EOPNOTSUPP})"
        )
    if fx3_movie_sort_recording_present_claimed or (
        shoot_mode in ("MOVIE", "S_AND_Q") and recording_media == "SORT_RECORDING"
    ):
        errors.append(
            f"{P321_GA_ERR_PRIORITIZE_REC_MEDIA_DORMANT_OR_MOVIE_SORT}: "
            f"SORT_RECORDING is Still-only and not exposed in Movie/S&Q (errno={P321_ERRNO_EOPNOTSUPP})"
        )
    if recording_media not in P321_STILL_RECORDING_MEDIA_FOUR_MODES:
        errors.append(
            f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: invalid recording_media={recording_media}"
        )
    if auto_switch_media not in P321_VALID_ON_OFF:
        errors.append(
            f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: invalid auto_switch_media={auto_switch_media}"
        )
    if claimed_auto_switch_wiped_by_camera_reset:
        errors.append(
            f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: "
            "[Auto Switch Media] (0x6dd9) is Initialize-only and survives [Camera Settings Reset]"
        )

    # Simultaneous recording filesystem parity & Slot-2 -> Slot-1 overflow trap dual lock
    if slot1_fs not in P321_VALID_SLOT_FILESYSTEMS or slot2_fs not in P321_VALID_SLOT_FILESYSTEMS:
        errors.append(
            f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: invalid slot FS ({slot1_fs}, {slot2_fs})"
        )
    if recording_media == "SIMULTANEOUS_RECORDING" and slot1_fs != slot2_fs:
        errors.append(
            f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: "
            f"Simult. Recording requires matching exFAT or FAT32 across both slots ({slot1_fs} vs {slot2_fs}, errno={P321_ERRNO_EINVAL})"
        )

    slot1_overflow_trap_locked_off = (
        recording_media == "SLOT_2"
        and auto_switch_media == "OFF"
        and slot1_wp_locked
        and slot1_data_sector_writes == 0
        and not slot1_rec_write_requested
    )
    if slot1_contains_tier0_dump:
        if recording_media != "SLOT_2":
            errors.append(
                f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: "
                f"Slot-1 Tier-0 Vault forbids recording_media={recording_media} (must be SLOT_2, errno={P321_ERRNO_EROFS})"
            )
        if auto_switch_media != "OFF":
            errors.append(
                f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: "
                f"Slot-2 -> Slot-1 Overflow Trap requires Auto Switch Media=OFF (errno={P321_ERRNO_EROFS})"
            )
        if not slot1_wp_locked:
            errors.append(
                f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: "
                "Slot-1 physical WP lock must remain enabled when Tier-0 vault is loaded"
            )
        if slot1_rec_write_requested or slot1_data_sector_writes != 0:
            errors.append(
                f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: "
                f"Slot-1 Tier-0 vault write blocked (EROFS={P321_ERRNO_EROFS})"
            )

    if fx3_independent_rec_button_slot_set_claimed or fx6_relay_with_proxy_streaming_chunk_claimed:
        errors.append(
            f"{P321_GA_ERR_SLOT2_OVERFLOW_TRAP_OR_SIMULT_FS_MISMATCH}: "
            "FX6 Rec Button Slot A/B and Relay+Proxy/LAN/Streaming/Chunk mutual exclusions violated"
        )

    # Card speed gates & VPG200/VPG400
    if media_speed_grade not in P321_VALID_MEDIA_SPEED_GRADES:
        errors.append(f"{P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE}: unknown media_speed_grade={media_speed_grade}")
    if media_speed_grade == "CFEXPRESS_TYPE_B":
        errors.append(
            f"{P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE}: "
            "ILME-FX3 supports CFexpress Type A only (CFexpress Type B unsupported)"
        )
    if claimed_sdhc_no_4gb_split:
        errors.append(
            f"{P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE}: "
            "SDHC FAT32 splits movie files at 4 GB (unlike exFAT SDXC/CFexpress Type A)"
        )
    if movie_file_format not in P321_VALID_MOVIE_FILE_FORMATS:
        errors.append(
            f"{P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE}: invalid movie_file_format={movie_file_format}"
        )

    is_sq_1200_or_890 = sq_enabled and (
        (movie_file_format in ("XAVC_S_I_4K", "XAVC_S_I_DCI_4K") and sq_fps >= 100.0)
        or (movie_file_format == "XAVC_S_I_HD" and sq_fps >= 200.0)
        or movie_bitrate_mbps >= 890
    )
    if is_sq_1200_or_890 and media_speed_grade not in ("CFEXPRESS_A_VPG200", "CFEXPRESS_A_VPG400"):
        errors.append(
            f"{P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE}: "
            f"S&Q All-I 890/1200 Mbps requires mandatory CFexpress Type A VPG200+ (got {media_speed_grade})"
        )
    elif (movie_file_format in ("XAVC_S_I_4K", "XAVC_S_I_DCI_4K") or movie_bitrate_mbps >= 500) and media_speed_grade not in (
        "CFEXPRESS_A_VPG400",
        "CFEXPRESS_A_VPG200",
        "SDXC_V90",
    ):
        errors.append(
            f"{P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE}: "
            f"XAVC S-I 4K/DCI 4K requires >= SDXC V90 or CFexpress Type A VPG200+ (got {media_speed_grade})"
        )
    elif movie_bitrate_mbps >= 200 and media_speed_grade not in (
        "CFEXPRESS_A_VPG400",
        "CFEXPRESS_A_VPG200",
        "SDXC_V90",
        "SDXC_V60",
    ):
        errors.append(
            f"{P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE}: "
            f"200-280 Mbps 4K requires >= SDXC V60 (got {media_speed_grade})"
        )

    if media_speed_grade == "CFEXPRESS_A_VPG200" and movie_bitrate_mbps >= 600 and proxy_recording == "ON":
        if not vpg400_caution_acknowledged:
            errors.append(
                f"{P321_GA_ERR_CARD_SPEED_VPG200_VPG400_OR_TYPEB_GATE}: "
                f"VPG200 at >=600 Mbps + Proxy ON triggers base.uxc VPG400 (0xe224) caution without acknowledgment"
            )
        else:
            warnings.append("VPG400 caution (0xe224) acknowledged for VPG200 >=600 Mbps + Proxy ON")

    # [Proxy Settings] + M4ROOT/SUB/*S03.MP4
    if proxy_recording not in P321_VALID_ON_OFF:
        errors.append(f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: invalid proxy_recording={proxy_recording}")
    if proxy_file_format not in P321_VALID_PROXY_FILE_FORMATS:
        errors.append(
            f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: invalid proxy_file_format={proxy_file_format}"
        )
    if dormant_proxy_8bit_fhd_requested or proxy_record_setting in P321_DORMANT_PROXY_RECORD_SETTINGS:
        errors.append(
            f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: "
            f"dormant FHD 8-bit proxy ({P321_DORMANT_PROXY_16M_8BIT_RESID16_HEX}) rejected (errno={P321_ERRNO_EOPNOTSUPP})"
        )
    elif proxy_record_setting not in P321_VALID_PROXY_RECORD_SETTINGS:
        errors.append(
            f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: invalid proxy_record_setting={proxy_record_setting}"
        )
    else:
        if proxy_file_format == "XAVC_S_HD" and proxy_record_setting != "1280x720_6M_8BIT":
            errors.append(
                f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: "
                "XAVC_S_HD proxy must be 1280x720_6M_8BIT"
            )
        if proxy_file_format == "XAVC_HS_HD" and proxy_record_setting not in (
            "1920x1080_9M_10BIT",
            "1920x1080_16M_10BIT",
        ):
            errors.append(
                f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: "
                "XAVC_HS_HD proxy must be 1920x1080 9M/16M 10-bit"
            )

    proxy_cutoff_hit = rec_fps >= P321_PROXY_CUTOFF_FPS or (sq_enabled and sq_fps >= P321_PROXY_CUTOFF_FPS)
    if proxy_recording == "ON" and proxy_cutoff_hit:
        errors.append(
            f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: "
            f"Proxy Recording is blocked at >= 100p / S&Q >= 100fps (rec={rec_fps}, sq={sq_fps})"
        )
    if claimed_proxy_blocked_on_dci4k_60p:
        errors.append(
            f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: "
            "Proxy Recording is NOT directly disabled on XAVC S-I DCI 4K <= 59.94p"
        )
    if claimed_proxy_resists_camera_reset:
        errors.append(
            f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: "
            "[Proxy Settings] are resettable by [Camera Settings Reset]"
        )
    if proxy_slot1_write_or_coupled_delete_requested and slot1_contains_tier0_dump:
        errors.append(
            f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: "
            f"M4ROOT/SUB/*S03.MP4 coupled delete/protect blocked on Slot-1 Tier-0 Vault (EROFS={P321_ERRNO_EROFS})"
        )
    if claimed_fx3_has_fx6_chunk_upload:
        errors.append(
            f"{P321_GA_ERR_PROXY_SETTINGS_DCI4K_CUTOFF_OR_SUB_SLOT1_VAULT}: "
            "30s/1min/2min Chunk proxy recording on Slot B is FX6-only"
        )

    return P321CheckGroupARecMediaOverflowProxyResult(
        group_id=P321_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        shoot_mode=shoot_mode,
        recording_media=recording_media,
        auto_switch_media=auto_switch_media,
        slot1_fs=slot1_fs,
        slot2_fs=slot2_fs,
        media_speed_grade=media_speed_grade,
        movie_file_format=movie_file_format,
        movie_bitrate_mbps=movie_bitrate_mbps,
        proxy_recording=proxy_recording,
        proxy_file_format=proxy_file_format,
        proxy_record_setting=proxy_record_setting,
        rec_fps=rec_fps,
        sq_enabled=sq_enabled,
        sq_fps=sq_fps,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_overflow_trap_locked_off=slot1_overflow_trap_locked_off,
        fx3_prioritize_rec_media_present=False,
        fx3_movie_sort_recording_present=False,
        proxy_allowed_on_dci4k_le60p=True,
        slot1_data_sector_writes=slot1_data_sector_writes,
        slot1_tier0_vault_mutated=slot1_data_sector_writes != 0 or slot1_rec_write_requested,
    )


def evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
    *,
    cloud_connection: str = "OFF",
    c3_portal_enabled: bool = False,
    clip_flag_filter: str = "NONE",
    ftp_transfer_func: str = "OFF",
    claimed_cloud_wiped_by_camera_reset: bool = False,
    claimed_cloud_wiped_by_initialize: bool = False,
    claimed_c3_portal_before_v400: bool = False,
    claimed_fx3_cloud_does_not_exclude_ftp: bool = False,
    airplane_mode: str = "ON",
    cnct_while_power_off: str = "OFF",
    bluetooth_function: str = "OFF",
    wifi_enabled: bool = False,
    wireless_rf_packets_emitted: int = 0,
    rf_nvs_p12_p13_writes_requested: bool = False,
    claimed_cnct_while_power_off_wiped_by_camera_reset: bool = False,
    fx6_has_bluetooth_claimed: bool = False,
    mymenu_pages: int = P321_MYMENU_EXACT_PAGES,
    mymenu_slots_per_page: int = P321_MYMENU_EXACT_SLOTS_PER_PAGE,
    mymenu_total_slots: int = P321_MYMENU_EXACT_TOTAL_SLOTS,
    fx3_mymenu_30_or_36_slots_only_claimed: bool = False,
    mymenu_playback_item_requested: bool = False,
    claimed_mymenu_wiped_by_camera_reset: bool = False,
    fx6_user_menu_pin: str = "0000",
    claimed_fx3_has_pin_user_menu_with_lock: bool = False,
    claimed_fx6_user_menu_pin_included_in_all_file: bool = False,
) -> P321CheckGroupBCloudBleZeroRfMyMenuResult:
    errors: List[str] = []
    warnings: List[str] = []

    if cloud_connection not in P321_VALID_ON_OFF:
        errors.append(f"{P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION}: invalid cloud_connection={cloud_connection}")
    if clip_flag_filter not in P321_VALID_CLIP_FLAGS:
        errors.append(f"{P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION}: invalid clip_flag_filter={clip_flag_filter}")
    if cloud_connection == "ON" and ftp_transfer_func == "ON":
        errors.append(
            f"{P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION}: "
            "CLOUD_CONNECTION_ON_FTP_OFF mutual exclusion violated"
        )
    if cloud_connection == "ON" or c3_portal_enabled:
        errors.append(
            f"{P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION}: "
            "Zero-RF bench preflight requires [Cloud Connection *]=OFF and [C3 Portal]=disabled"
        )
    if claimed_cloud_wiped_by_camera_reset or claimed_cloud_wiped_by_initialize:
        errors.append(
            f"{P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION}: "
            "[Cloud Connection *]/[Cloud Information *] survive BOTH [Camera Settings Reset] AND [Initialize]"
        )
    if claimed_c3_portal_before_v400 or claimed_fx3_cloud_does_not_exclude_ftp:
        errors.append(
            f"{P321_GB_ERR_CLOUD_C3_PERSISTENCE_OR_FTP_EXCLUSION}: "
            "C3 Portal LUT sync requires Ver. 4.00+ and Cloud Connection=On locks out FTP"
        )

    # Zero-RF Power-OFF BLE guard
    if airplane_mode != "ON":
        errors.append(
            f"{P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD}: "
            f"Physical bench requires [Airplane Mode]=ON (got {airplane_mode})"
        )
    if cnct_while_power_off != "OFF":
        errors.append(
            f"{P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD}: "
            f"[Cnct. while Power OFF] ({P321_CNCT_WHILE_POWER_OFF_RESID16_HEX}) must be OFF to prevent Power-OFF BLE advertising"
        )
    if bluetooth_function != "OFF" or wifi_enabled:
        errors.append(
            f"{P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD}: "
            "Bluetooth and Wi-Fi radios must both remain OFF on bench"
        )
    if wireless_rf_packets_emitted != 0 or rf_nvs_p12_p13_writes_requested:
        errors.append(
            f"{P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD}: "
            "Zero-RF invariant violated (rf_packets_transmitted != 0 or p12/p13 NVS write requested)"
        )
    if claimed_cnct_while_power_off_wiped_by_camera_reset:
        errors.append(
            f"{P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD}: "
            "[Cnct. while Power OFF] survives [Camera Settings Reset]"
        )
    if fx6_has_bluetooth_claimed:
        errors.append(
            f"{P321_GB_ERR_ZERO_RF_POWEROFF_BLE_OR_AIRPLANE_GUARD}: "
            "ILME-FX6 lacks Bluetooth hardware"
        )

    # 6 x 7 = 42 [My Menu] NVRAM slots vs FX6 20-item PIN User Menu
    if (
        mymenu_pages != P321_MYMENU_EXACT_PAGES
        or mymenu_slots_per_page != P321_MYMENU_EXACT_SLOTS_PER_PAGE
        or mymenu_total_slots != P321_MYMENU_EXACT_TOTAL_SLOTS
        or fx3_mymenu_30_or_36_slots_only_claimed
    ):
        errors.append(
            f"{P321_GB_ERR_MYMENU_42_SLOTS_PLAYBACK_OR_FX6_PIN_MENU}: "
            f"FX3 [My Menu] must be exact 6x7=42 slots (got {mymenu_pages}x{mymenu_slots_per_page}={mymenu_total_slots})"
        )
    if mymenu_playback_item_requested:
        errors.append(
            f"{P321_GB_ERR_MYMENU_42_SLOTS_PLAYBACK_OR_FX6_PIN_MENU}: "
            "(Playback) items cannot be registered to FX3 [My Menu]"
        )
    if claimed_mymenu_wiped_by_camera_reset:
        errors.append(
            f"{P321_GB_ERR_MYMENU_42_SLOTS_PLAYBACK_OR_FX6_PIN_MENU}: "
            "[My Menu] survives [Camera Settings Reset] (cleared only by Initialize / Delete All)"
        )
    fx6_pin_valid = bool(P321_PIN_4DIGIT_RE.match(fx6_user_menu_pin))
    if not fx6_pin_valid:
        errors.append(
            f"{P321_GB_ERR_MYMENU_42_SLOTS_PLAYBACK_OR_FX6_PIN_MENU}: "
            f"FX6 User Menu with Lock requires 4-digit PIN 0000..9999 (got {fx6_user_menu_pin!r})"
        )
    if claimed_fx3_has_pin_user_menu_with_lock or claimed_fx6_user_menu_pin_included_in_all_file:
        errors.append(
            f"{P321_GB_ERR_MYMENU_42_SLOTS_PLAYBACK_OR_FX6_PIN_MENU}: "
            "FX3 lacks FX6 PIN-locked User Menu Only, and FX6 PIN is excluded from All File"
        )

    return P321CheckGroupBCloudBleZeroRfMyMenuResult(
        group_id=P321_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        cloud_connection=cloud_connection,
        c3_portal_enabled=c3_portal_enabled,
        clip_flag_filter=clip_flag_filter,
        airplane_mode=airplane_mode,
        cnct_while_power_off=cnct_while_power_off,
        bluetooth_function=bluetooth_function,
        wifi_enabled=wifi_enabled,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        rf_nvs_p12_p13_writes_authorized=False,
        mymenu_pages=mymenu_pages,
        mymenu_slots_per_page=mymenu_slots_per_page,
        mymenu_total_slots=mymenu_total_slots,
        fx3_mymenu_30_or_36_slots_only=False,
        fx6_user_menu_max_items=P321_FX6_USER_MENU_MAX_ITEMS,
        fx6_user_menu_pin_valid=fx6_pin_valid,
    )


def evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
    *,
    ftp_transfer_func: str = "OFF",
    ftp_server_slot: int = 1,
    ftp_protocol: str = "FTPES",
    ftp_transfer_mode: str = "PASSIVE",
    ftp_active_mode_requested: bool = False,
    fx3_sftp_present_claimed: bool = False,
    fx3_ftp_active_mode_present_claimed: bool = False,
    dormant_transfer_jpeg_heif_size_requested: bool = False,
    fx3_transfer_jpeg_heif_size_present_claimed: bool = False,
    claimed_fx3_uses_certification_pem_slot_b: bool = False,
    claimed_fx3_ftp_limited_to_3_servers: bool = False,
    slot1_contains_tier0_dump: bool = True,
    ftp_slot1_write_or_transfer_list_requested: bool = False,
    cacert_pem_size_bytes: int = 2048,
    cacert_write_to_slot1_requested: bool = False,
    usb_lan_tethering: str = "OFF",
    usb_lan_cnct_launch: str = "OFF",
    network_transport: str = "NONE",
    claimed_airplane_mode_blocks_usb_lan: bool = False,
    wb_mode: str = "C_TEMP_FILTER",
    wb_kelvin_k: int = 5600,
    wb_ab_shift: int = 0,
    wb_gm_shift: int = 0,
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    custom_wb_setup_requested: bool = False,
    claimed_custom_wb_saved_in_camset: bool = False,
    claimed_custom_wb_wiped_by_camera_reset: bool = False,
    priority_set_in_awb: str = "STANDARD",
    shutter_awb_lock: str = "OFF",
    shockless_wb: str = "1_FAST",
    claimed_shutter_awb_lock_wiped_by_camera_reset: bool = False,
    claimed_shockless_wb_resists_camera_reset: bool = False,
    claimed_fx3_has_atw_speed_or_memory_ah: bool = False,
) -> P321CheckGroupCFtpesPassiveUsbLanWbResult:
    errors: List[str] = []
    warnings: List[str] = []

    if ftp_transfer_func not in P321_VALID_ON_OFF:
        errors.append(f"{P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE}: invalid ftp_transfer_func={ftp_transfer_func}")
    if not (P321_FX3_FTP_SERVER_MIN <= ftp_server_slot <= P321_FX3_FTP_SERVER_MAX):
        errors.append(
            f"{P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE}: "
            f"FX3 FTP Server slot must be 1..9 (got {ftp_server_slot})"
        )
    if ftp_protocol not in P321_VALID_FTP_PROTOCOLS:
        errors.append(
            f"{P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE}: invalid ftp_protocol={ftp_protocol}"
        )
    if ftp_protocol == "SFTP" or fx3_sftp_present_claimed:
        errors.append(
            f"{P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE}: "
            f"FX3 appFw.so has 0 SFTP hits; only Passive FTP / FTPES ({P321_FTPES_TLS_RESID16_HEX}) supported (errno={P321_ERRNO_EOPNOTSUPP})"
        )
    if ftp_transfer_mode != "PASSIVE" or ftp_active_mode_requested or fx3_ftp_active_mode_present_claimed:
        errors.append(
            f"{P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE}: "
            f"FX3 supports Passive FTP/FTPES only (0 Active mode hits, errno={P321_ERRNO_EOPNOTSUPP})"
        )
    if dormant_transfer_jpeg_heif_size_requested or fx3_transfer_jpeg_heif_size_present_claimed:
        errors.append(
            f"{P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE}: "
            f"Transfer JPEG/HEIF Size ({'/'.join(P321_DORMANT_TRANSFER_JPEG_HEIF_RESIDS)}) has 0 hits in FX3 appFw.so (errno={P321_ERRNO_EOPNOTSUPP})"
        )
    if claimed_fx3_uses_certification_pem_slot_b or claimed_fx3_ftp_limited_to_3_servers:
        errors.append(
            f"{P321_GC_ERR_FTP_PASSIVE_ONLY_9SERVER_OR_NO_SFTP_JPEGSIZE}: "
            "FX3 has 9 FTP servers + cacert.pem (FX6 has Server 1..3 + certification.pem on Slot B)"
        )

    # Slot-1 AVF_INFO + cacert.pem + USB-LAN Airplane-mode bypass firewall
    if ftp_slot1_write_or_transfer_list_requested and slot1_contains_tier0_dump:
        errors.append(
            f"{P321_GC_ERR_SLOT1_AVF_INFO_CACERT_OR_USBLAN_AIRPLANE_BYPASS}: "
            f"FTP transfer-list/AVF_INFO write onto Slot-1 Tier-0 Vault blocked (EROFS={P321_ERRNO_EROFS})"
        )
    if cacert_pem_size_bytes <= 0 or cacert_pem_size_bytes > P321_CACERT_MAX_BYTES:
        errors.append(
            f"{P321_GC_ERR_SLOT1_AVF_INFO_CACERT_OR_USBLAN_AIRPLANE_BYPASS}: "
            f"cacert.pem size must be 1..{P321_CACERT_MAX_BYTES} B (got {cacert_pem_size_bytes})"
        )
    if cacert_write_to_slot1_requested and slot1_contains_tier0_dump:
        errors.append(
            f"{P321_GC_ERR_SLOT1_AVF_INFO_CACERT_OR_USBLAN_AIRPLANE_BYPASS}: "
            f"Writing cacert.pem onto Slot-1 Tier-0 Vault blocked (EROFS={P321_ERRNO_EROFS})"
        )
    if (
        usb_lan_tethering != "OFF"
        or usb_lan_cnct_launch != "OFF"
        or ftp_transfer_func != "OFF"
        or network_transport != "NONE"
    ):
        errors.append(
            f"{P321_GC_ERR_SLOT1_AVF_INFO_CACERT_OR_USBLAN_AIRPLANE_BYPASS}: "
            f"Airplane Mode does NOT block wired USB-LAN FTP: bench requires USB-LAN/Tethering/FTP=OFF & transport=NONE"
        )
    if claimed_airplane_mode_blocks_usb_lan:
        errors.append(
            f"{P321_GC_ERR_SLOT1_AVF_INFO_CACERT_OR_USBLAN_AIRPLANE_BYPASS}: "
            "False claim: [Airplane Mode]=On does NOT disconnect wired USB-LAN (USB_ETHER)"
        )

    # White Balance, Cine EI & Custom 1..3
    if wb_mode not in P321_WB_VALID_MODES:
        errors.append(f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: invalid wb_mode={wb_mode}")
    if not (P321_WB_KELVIN_MIN_K <= wb_kelvin_k <= P321_WB_KELVIN_MAX_K) or wb_kelvin_k % P321_WB_KELVIN_STEP_K != 0:
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: "
            f"WB Kelvin must be 2500..9900K in 100K steps (got {wb_kelvin_k})"
        )
    if not (P321_WB_AB_MIN <= wb_ab_shift <= P321_WB_AB_MAX) or not (P321_WB_GM_MIN <= wb_gm_shift <= P321_WB_GM_MAX):
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: "
            f"WB A-B/G-M shifts out of [-7, +7] range ({wb_ab_shift}, {wb_gm_shift})"
        )
    if log_shooting_mode in ("CINE_EI", "CINE_EI_QUICK") and wb_mode in P321_WB_CINE_EI_BLOCKED_MODES:
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: "
            f"{log_shooting_mode} locks out {wb_mode} White Balance"
        )
    if custom_wb_setup_requested and (
        log_shooting_mode != "OFF"
        or picture_profile in P321_SLOG3_PICTURE_PROFILES
        or picture_profile in P321_PPLUT_PICTURE_PROFILES
    ):
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: "
            f"[Custom Setup] ({P321_CUSTOM_WB_SETUP_RESID16_HEX}) triggers Custom WB Error ({P321_CUSTOM_WB_ERROR_RESID16_HEX}) under Log/S-Log3/PPLUT"
        )
    if claimed_custom_wb_saved_in_camset or claimed_custom_wb_wiped_by_camera_reset:
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: "
            "Custom 1..3 WB slots are excluded from CAMSET*.DAT and survive [Camera Settings Reset]"
        )
    if priority_set_in_awb not in P321_VALID_PRIORITY_AWB_MODES:
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: invalid priority_set_in_awb={priority_set_in_awb}"
        )
    if shutter_awb_lock not in P321_VALID_SHUTTER_AWB_LOCK_MODES:
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: invalid shutter_awb_lock={shutter_awb_lock}"
        )
    if shockless_wb not in P321_VALID_SHOCKLESS_WB_MODES:
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: invalid shockless_wb={shockless_wb}"
        )
    if claimed_shutter_awb_lock_wiped_by_camera_reset or claimed_shockless_wb_resists_camera_reset:
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: "
            "[Shutter AWB Lock] resists Camera Settings Reset whereas [Shockless WB] resets"
        )
    if claimed_fx3_has_atw_speed_or_memory_ah:
        errors.append(
            f"{P321_GC_ERR_WB_CINE_EI_CUSTOM_CAMSET_OR_RESET_PERSISTENCE}: "
            "WHT BAL PRST/A/B, Memory A..H, and ATW Speed 1..5 are FX6-only"
        )

    slot1_mutated = bool(
        slot1_contains_tier0_dump and (ftp_slot1_write_or_transfer_list_requested or cacert_write_to_slot1_requested)
    )

    return P321CheckGroupCFtpesPassiveUsbLanWbResult(
        group_id=P321_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        ftp_transfer_func=ftp_transfer_func,
        ftp_server_slot=ftp_server_slot,
        ftp_protocol=ftp_protocol,
        ftp_transfer_mode=ftp_transfer_mode,
        fx3_ftp_sftp_present=False,
        fx3_ftp_active_mode_present=False,
        fx3_ftp_transfer_jpeg_size_present=False,
        usb_lan_tethering=usb_lan_tethering,
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        network_transport=network_transport,
        cacert_pem_size_bytes=cacert_pem_size_bytes,
        wb_mode=wb_mode,
        wb_kelvin_k=wb_kelvin_k,
        wb_ab_shift=wb_ab_shift,
        wb_gm_shift=wb_gm_shift,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        priority_set_in_awb=priority_set_in_awb,
        shutter_awb_lock=shutter_awb_lock,
        shockless_wb=shockless_wb,
        slot1_tier0_vault_mutated=slot1_mutated,
    )


def _read_single_tier0_receipt_file(path: Path) -> Tuple[Optional[Tuple[bytes, int]], Tuple[str, ...]]:
    if not path.is_file():
        return None, (f"missing Tier-0 receipt file: {path}",)
    if path.is_symlink():
        return None, (f"symlink receipt rejected: {path}",)
    st = os.stat(path)
    if st.st_size != SD_RECEIPT_BYTES:
        return None, (f"invalid receipt size {st.st_size} != {SD_RECEIPT_BYTES}: {path}",)
    fd = os.open(str(path), os.O_RDONLY)
    try:
        raw = os.read(fd, SD_RECEIPT_BYTES)
    finally:
        os.close(fd)
    if len(raw) != SD_RECEIPT_BYTES:
        return None, (f"short receipt read ({len(raw)} != {SD_RECEIPT_BYTES}): {path}",)
    return (raw, int(st.st_dev)), ()


def evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    af_transition_speed: int = P321_AF_TRANSITION_SPEED_DEFAULT,
    af_subj_shift_sens: int = P321_AF_SUBJ_SHIFT_SENS_DEFAULT,
    fx3_af_subj_shift_7_levels_claimed: bool = False,
    fx6_af_subj_shift_7_levels_claimed: bool = False,
    af_assist: str = "OFF",
    lens_model: str = "SEL2470GM2",
    claimed_af_assist_resists_camera_reset: bool = False,
    in_body_focus_map_requested: bool = False,
    fx3_in_body_focus_map_present_claimed: bool = False,
    fx3_uvc_streaming_present_claimed: bool = False,
    mc_focus_map_enabled: bool = False,
    mc_focus_map_fps: float = 23.98,
    mc_focus_map_over_wifi_requested: bool = False,
    playback_control_active: bool = False,
    lens_pdaf_capable: bool = True,
    auto_framing_claimed: bool = False,
    usb_remote_or_uvc_active: bool = False,
    claimed_mc_focus_map_blocked_at_120p: bool = False,
    aspect_marker: str = "OFF",
    exposed_aspect_markers: Tuple[str, ...] = P321_ASPECT_MARKER_16_STATES,
    safety_zone: str = "OFF",
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "WHITE",
    focus_magnifier_active: bool = False,
    expect_marker_or_peaking_on_hdmi: bool = False,
    expect_marker_visible_during_focus_magnifier: bool = False,
    claimed_marker_or_peaking_wiped_by_camera_reset: bool = False,
    claimed_fx3_has_user_box_or_925_95_safety_or_bw_peaking: bool = False,
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
) -> P321CheckGroupDAfFocusMapMarkerTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    # Movie AF Transition Speed 1..7 & AF Subj. Shift Sens. 1..5
    if not (P321_AF_TRANSITION_SPEED_MIN <= af_transition_speed <= P321_AF_TRANSITION_SPEED_MAX):
        errors.append(
            f"{P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS}: "
            f"[AF Transition Speed] must be 1..7 (got {af_transition_speed})"
        )
    if not (P321_AF_SUBJ_SHIFT_SENS_MIN <= af_subj_shift_sens <= P321_AF_SUBJ_SHIFT_SENS_MAX):
        errors.append(
            f"{P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS}: "
            f"[AF Subj. Shift Sens.] must be 1..5 (got {af_subj_shift_sens})"
        )
    if fx3_af_subj_shift_7_levels_claimed or fx6_af_subj_shift_7_levels_claimed:
        errors.append(
            f"{P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS}: "
            "BOTH FX3 and FX6 use 1..5 for [AF Subj. Shift Sens.] (NOT 1..7)"
        )
    if af_assist not in P321_VALID_ON_OFF:
        errors.append(f"{P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS}: invalid af_assist={af_assist}")
    if af_assist == "ON" and lens_model in P321_AF_ASSIST_INCOMPATIBLE_LENSES:
        errors.append(
            f"{P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS}: "
            f"[AF Assist] incompatible with {lens_model}"
        )
    if claimed_af_assist_resists_camera_reset:
        errors.append(
            f"{P321_GD_ERR_AF_SENS_1_5_TRANSITION_1_7_OR_AF_ASSIST_LENS}: "
            "[AF Assist] resets to Off on [Camera Settings Reset]"
        )

    # Zero in-body Focus Map & Ver. 6.00+ external Monitor & Control Focus Map
    if in_body_focus_map_requested or fx3_in_body_focus_map_present_claimed:
        errors.append(
            f"{P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC}: "
            f"FX3 has ZERO in-body Focus Map (errno={P321_ERRNO_EOPNOTSUPP})"
        )
    if fx3_uvc_streaming_present_claimed:
        errors.append(
            f"{P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC}: "
            "FX3 has ZERO UVC [USB Streaming] support"
        )
    if mc_focus_map_enabled:
        if mc_focus_map_fps >= P321_MC_FOCUS_MAP_FPS_CUTOFF:
            errors.append(
                f"{P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC}: "
                f"External M&C Focus Map blocked at >= 150 fps (got {mc_focus_map_fps})"
            )
        if playback_control_active or not lens_pdaf_capable or auto_framing_claimed or usb_remote_or_uvc_active:
            errors.append(
                f"{P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC}: "
                "External M&C Focus Map blocked during playback, non-PDAF/adapter, Auto Framing, or USB remote/UVC"
            )
        if mc_focus_map_over_wifi_requested:
            errors.append(
                f"{P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC}: "
                "Zero-RF bench forbids Wi-Fi Monitor & Control Focus Map transport"
            )
    if claimed_mc_focus_map_blocked_at_120p:
        errors.append(
            f"{P321_GD_ERR_NO_INBODY_FOCUS_MAP_OR_MC_150FPS_UVC}: "
            "M&C Focus Map cutoff is >= 150 fps (100p/119.88p IS < 150 fps and allowed)"
        )

    # 16-state [Aspect Marker] + 4-color [Peaking Display]
    if aspect_marker not in P321_ASPECT_MARKER_16_STATES:
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: invalid aspect_marker={aspect_marker}"
        )
    if len(exposed_aspect_markers) != len(P321_ASPECT_MARKER_16_STATES) or set(exposed_aspect_markers) != set(
        P321_ASPECT_MARKER_16_STATES
    ):
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: "
            "FX3 [Aspect Marker] must expose exact 16 states (Off + 15 active ratios)"
        )
    if safety_zone not in P321_VALID_SAFETY_ZONES:
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: invalid safety_zone={safety_zone}"
        )
    if peaking_display not in P321_VALID_ON_OFF:
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: invalid peaking_display={peaking_display}"
        )
    if peaking_level not in P321_VALID_PEAKING_LEVELS:
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: invalid peaking_level={peaking_level}"
        )
    if peaking_color not in P321_FX3_PEAKING_FOUR_COLORS:
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: "
            f"FX3 [Peaking Color] must be one of {P321_FX3_PEAKING_FOUR_COLORS} (got {peaking_color})"
        )
    if expect_marker_or_peaking_on_hdmi:
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: "
            "[Marker Display] and [Peaking Display] are never output over HDMI"
        )
    if focus_magnifier_active and expect_marker_visible_during_focus_magnifier:
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: "
            "[Marker Display] auto-hides during [Focus Magnifier]"
        )
    if claimed_marker_or_peaking_wiped_by_camera_reset:
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: "
            "All 8 [Marker Display]/[Peaking Display] items survive [Camera Settings Reset]"
        )
    if claimed_fx3_has_user_box_or_925_95_safety_or_bw_peaking:
        errors.append(
            f"{P321_GD_ERR_ASPECT_MARKER_16STATE_PEAKING_4COLOR_OR_HDMI_RESET}: "
            "User Box, 92.5%/95% Safety Area, Aspect Mask 0..15, and B&W Peaking are FX6-only"
        )

    # Hardware redlines
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
            f"{P321_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: "
            "Unconditional safety redline violated (non-zero TX/writes or unauthorized live attach/flash claim)"
        )

    # 16/16 H0 == H3 + Dual-Media 528B FX3RCPT1 Tier-0 Receipt Gate
    surface_count = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, int(simulated_h0_h3_drifted_surfaces))
    if h3_baselines is not None and h0_baselines_a is not None:
        surface_mismatches = [
            s for s in SIXTEEN_STORAGE_SURFACES if h0_baselines_a.get(s) != h3_baselines.get(s)
        ]
        key_mismatches = [
            k for k in REQUIRED_H0_BASELINE_KEYS if h0_baselines_a.get(k) != h3_baselines.get(k)
        ]
        drifted = max(drifted, len(surface_mismatches), len(key_mismatches))
    h0_eq_h3_count = max(0, surface_count - drifted)
    if drifted != 0 or h0_eq_h3_count != surface_count:
        errors.append(
            f"{P321_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: "
            f"H0==H3 drift detected ({h0_eq_h3_count}/{surface_count})"
        )

    tier0_verified = False
    receipt_mode = "OFFLINE_AWAITING_PHYSICAL_TIER0_RECEIPT"
    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    dev_a = st_dev_a_override
    dev_b = st_dev_b_override
    eff_serial = body_serial
    eff_cid = emmc_cid
    eff_h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else None
    eff_h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else None

    if simulate_bench_dry_run and raw_a is None and raw_b is None and receipt_a_path is None and receipt_b_path is None:
        eff_serial = eff_serial or "FX3702SIM321"
        eff_cid = eff_cid or "150100424a4e42345201020304050607"
        sim = build_simulated_phase321_tier0_receipts(body_serial=eff_serial, emmc_cid=eff_cid)
        raw_a = sim["receipt_a_bytes"]
        raw_b = sim["receipt_b_bytes"]
        parsed_a = parse_sd_backup_receipt_bytes(raw_a)
        parsed_b = parse_sd_backup_receipt_bytes(raw_b)
        if raw_a == raw_b and parsed_a.valid and parsed_b.valid and drifted == 0:
            tier0_verified = True
            receipt_mode = "DRY_RUN_SIMULATED"
            warnings.append(
                "SIMULATED_DRY_RUN_ONLY: Tier-0 528B FX3RCPT1 receipts synthesized in memory; no physical attach authorized"
            )
        else:
            errors.append(
                f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: simulated receipt invalid"
            )
    elif raw_a is not None or raw_b is not None or receipt_a_path is not None or receipt_b_path is not None:
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
                f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {msg}"
                for msg in read_errs
            )
            receipt_mode = "INVALID_RECEIPT_PARSE_OR_IDENTITY"
        elif raw_a is None or raw_b is None:
            errors.append(
                f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                "both Copy A and Copy B 528B FX3RCPT1 receipts are required"
            )
            receipt_mode = "INVALID_RECEIPT_SINGLE_COPY"
        else:
            if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
                errors.append(
                    f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    "dual 528B FX3RCPT1 size/byte mismatch"
                )
            if dev_a is None or dev_b is None or int(dev_a) == int(dev_b):
                errors.append(
                    f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"dual-media receipts must reside on distinct physical devices (st_dev {dev_a} vs {dev_b})"
                )
            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                errors.append(
                    f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"trivial or invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                errors.append(
                    f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"trivial or invalid 128-bit emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                errors.append(
                    f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    f"receipt target model/fw mismatch ({hex(body_model_id)} / {body_fw})"
                )
            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    errors.append(
                        f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                        f"FX3RCPT1 integrity/header check failed ({parsed_a.errors or parsed_b.errors})"
                    )
            except Exception as exc:
                errors.append(
                    f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse failure: {exc}"
                )
            if eff_h0_a is None or eff_h0_b is None:
                errors.append(
                    f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                    "h0_baselines_a and h0_baselines_b required with physical receipts"
                )
            else:
                for key in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(key, "")
                    vb = eff_h0_b.get(key, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        errors.append(
                            f"{P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: "
                            f"H0 baseline invalid or mismatched for {key}"
                        )
                        break
            if not any(e.startswith(P321_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID) for e in errors):
                tier0_verified = True
                receipt_mode = "PHYSICAL_DUAL_MEDIA_528B"
            else:
                receipt_mode = "INVALID_RECEIPT_REJECTED"
    else:
        warnings.append("No physical 528B FX3RCPT1 Tier-0 receipts provided; status fail-closed offline")

    return P321CheckGroupDAfFocusMapMarkerTier0Result(
        group_id=P321_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        errors=tuple(errors),
        warnings=tuple(warnings),
        af_transition_speed=af_transition_speed,
        af_subj_shift_sens=af_subj_shift_sens,
        fx3_af_subj_shift_7_levels_present=False,
        af_assist=af_assist,
        lens_model=lens_model,
        fx3_in_body_focus_map_present=False,
        fx3_uvc_streaming_present=False,
        mc_focus_map_enabled=mc_focus_map_enabled,
        mc_focus_map_fps=mc_focus_map_fps,
        aspect_marker=aspect_marker,
        aspect_marker_state_count=len(P321_ASPECT_MARKER_16_STATES),
        safety_zone=safety_zone,
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        focus_magnifier_active=focus_magnifier_active,
        tier0_receipt_verified=tier0_verified,
        receipt_mode=receipt_mode,
        h0_equals_h3_count=h0_eq_h3_count,
        h0_h3_surface_count=surface_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        usb_packets_transmitted=usb_packets_transmitted,
        passive_tx_bytes_emitted=simulated_passive_tx_bytes,
        raw_firmware_bytes_leaked=PHASE321_RAW_FIRMWARE_BYTES_LEAKED,
    )


def build_simulated_phase321_tier0_receipts(
    *,
    body_serial: str = "FX3702SIM321",
    emmc_cid: str = "150100424a4e42345201020304050607",
) -> Dict[str, Any]:
    h0 = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE321_TIER0:{TARGET_BODY_FW}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode("ascii")
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE321_MANIFEST:{body_serial}:{TARGET_BODY_FW}:{emmc_cid.lower()}".encode("ascii")
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


def evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P321_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Group A
    recording_media: str = "SLOT_2",
    auto_switch_media: str = "OFF",
    dormant_prioritize_rec_media_requested: bool = False,
    fx3_prioritize_rec_media_present_claimed: bool = False,
    fx3_movie_sort_recording_present_claimed: bool = False,
    claimed_auto_switch_wiped_by_camera_reset: bool = False,
    slot1_fs: str = "EXFAT",
    slot2_fs: str = "EXFAT",
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_rec_write_requested: bool = False,
    slot1_data_sector_writes: int = 0,
    fx3_independent_rec_button_slot_set_claimed: bool = False,
    fx6_relay_with_proxy_streaming_chunk_claimed: bool = False,
    media_speed_grade: str = "CFEXPRESS_A_VPG200",
    movie_file_format: str = "XAVC_S_I_4K",
    movie_bitrate_mbps: int = 240,
    rec_fps: float = 23.98,
    sq_enabled: bool = False,
    sq_fps: float = 60.0,
    proxy_recording: str = "OFF",
    proxy_file_format: str = "XAVC_S_HD",
    proxy_record_setting: str = "1280x720_6M_8BIT",
    dormant_proxy_8bit_fhd_requested: bool = False,
    vpg400_caution_acknowledged: bool = True,
    claimed_sdhc_no_4gb_split: bool = False,
    claimed_proxy_blocked_on_dci4k_60p: bool = False,
    claimed_proxy_resists_camera_reset: bool = False,
    proxy_slot1_write_or_coupled_delete_requested: bool = False,
    claimed_fx3_has_fx6_chunk_upload: bool = False,
    # Group B
    cloud_connection: str = "OFF",
    c3_portal_enabled: bool = False,
    clip_flag_filter: str = "NONE",
    claimed_cloud_wiped_by_camera_reset: bool = False,
    claimed_cloud_wiped_by_initialize: bool = False,
    claimed_c3_portal_before_v400: bool = False,
    claimed_fx3_cloud_does_not_exclude_ftp: bool = False,
    airplane_mode: str = "ON",
    cnct_while_power_off: str = "OFF",
    bluetooth_function: str = "OFF",
    wifi_enabled: bool = False,
    wireless_rf_packets_emitted: int = 0,
    rf_nvs_p12_p13_writes_requested: bool = False,
    claimed_cnct_while_power_off_wiped_by_camera_reset: bool = False,
    fx6_has_bluetooth_claimed: bool = False,
    mymenu_pages: int = P321_MYMENU_EXACT_PAGES,
    mymenu_slots_per_page: int = P321_MYMENU_EXACT_SLOTS_PER_PAGE,
    mymenu_total_slots: int = P321_MYMENU_EXACT_TOTAL_SLOTS,
    fx3_mymenu_30_or_36_slots_only_claimed: bool = False,
    mymenu_playback_item_requested: bool = False,
    claimed_mymenu_wiped_by_camera_reset: bool = False,
    fx6_user_menu_pin: str = "0000",
    claimed_fx3_has_pin_user_menu_with_lock: bool = False,
    claimed_fx6_user_menu_pin_included_in_all_file: bool = False,
    # Group C
    ftp_transfer_func: str = "OFF",
    ftp_server_slot: int = 1,
    ftp_protocol: str = "FTPES",
    ftp_transfer_mode: str = "PASSIVE",
    ftp_active_mode_requested: bool = False,
    fx3_sftp_present_claimed: bool = False,
    fx3_ftp_active_mode_present_claimed: bool = False,
    dormant_transfer_jpeg_heif_size_requested: bool = False,
    fx3_transfer_jpeg_heif_size_present_claimed: bool = False,
    claimed_fx3_uses_certification_pem_slot_b: bool = False,
    claimed_fx3_ftp_limited_to_3_servers: bool = False,
    ftp_slot1_write_or_transfer_list_requested: bool = False,
    cacert_pem_size_bytes: int = 2048,
    cacert_write_to_slot1_requested: bool = False,
    usb_lan_tethering: str = "OFF",
    usb_lan_cnct_launch: str = "OFF",
    network_transport: str = "NONE",
    claimed_airplane_mode_blocks_usb_lan: bool = False,
    wb_mode: str = "C_TEMP_FILTER",
    wb_kelvin_k: int = 5600,
    wb_ab_shift: int = 0,
    wb_gm_shift: int = 0,
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    custom_wb_setup_requested: bool = False,
    claimed_custom_wb_saved_in_camset: bool = False,
    claimed_custom_wb_wiped_by_camera_reset: bool = False,
    priority_set_in_awb: str = "STANDARD",
    shutter_awb_lock: str = "OFF",
    shockless_wb: str = "1_FAST",
    claimed_shutter_awb_lock_wiped_by_camera_reset: bool = False,
    claimed_shockless_wb_resists_camera_reset: bool = False,
    claimed_fx3_has_atw_speed_or_memory_ah: bool = False,
    # Group D
    af_transition_speed: int = P321_AF_TRANSITION_SPEED_DEFAULT,
    af_subj_shift_sens: int = P321_AF_SUBJ_SHIFT_SENS_DEFAULT,
    fx3_af_subj_shift_7_levels_claimed: bool = False,
    fx6_af_subj_shift_7_levels_claimed: bool = False,
    af_assist: str = "OFF",
    lens_model: str = "SEL2470GM2",
    claimed_af_assist_resists_camera_reset: bool = False,
    in_body_focus_map_requested: bool = False,
    fx3_in_body_focus_map_present_claimed: bool = False,
    fx3_uvc_streaming_present_claimed: bool = False,
    mc_focus_map_enabled: bool = False,
    mc_focus_map_fps: float = 23.98,
    mc_focus_map_over_wifi_requested: bool = False,
    playback_control_active: bool = False,
    lens_pdaf_capable: bool = True,
    auto_framing_claimed: bool = False,
    usb_remote_or_uvc_active: bool = False,
    claimed_mc_focus_map_blocked_at_120p: bool = False,
    aspect_marker: str = "OFF",
    exposed_aspect_markers: Tuple[str, ...] = P321_ASPECT_MARKER_16_STATES,
    safety_zone: str = "OFF",
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "WHITE",
    focus_magnifier_active: bool = False,
    expect_marker_or_peaking_on_hdmi: bool = False,
    expect_marker_visible_during_focus_magnifier: bool = False,
    claimed_marker_or_peaking_wiped_by_camera_reset: bool = False,
    claimed_fx3_has_user_box_or_925_95_safety_or_bw_peaking: bool = False,
    e_nd_actuator_tx_count: int = 0,
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
) -> RealHwRecMediaAutoswitchProxyCloudMyMenuFtpesReport:
    donor = inspect_phase321_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p321_check_group_a_rec_media_overflow_and_proxy(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        recording_media=recording_media,
        auto_switch_media=auto_switch_media,
        dormant_prioritize_rec_media_requested=dormant_prioritize_rec_media_requested,
        fx3_prioritize_rec_media_present_claimed=fx3_prioritize_rec_media_present_claimed,
        fx3_movie_sort_recording_present_claimed=fx3_movie_sort_recording_present_claimed,
        claimed_auto_switch_wiped_by_camera_reset=claimed_auto_switch_wiped_by_camera_reset,
        slot1_fs=slot1_fs,
        slot2_fs=slot2_fs,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_rec_write_requested=slot1_rec_write_requested,
        slot1_data_sector_writes=slot1_data_sector_writes,
        fx3_independent_rec_button_slot_set_claimed=fx3_independent_rec_button_slot_set_claimed,
        fx6_relay_with_proxy_streaming_chunk_claimed=fx6_relay_with_proxy_streaming_chunk_claimed,
        media_speed_grade=media_speed_grade,
        movie_file_format=movie_file_format,
        movie_bitrate_mbps=movie_bitrate_mbps,
        rec_fps=rec_fps,
        sq_enabled=sq_enabled,
        sq_fps=sq_fps,
        proxy_recording=proxy_recording,
        proxy_file_format=proxy_file_format,
        proxy_record_setting=proxy_record_setting,
        dormant_proxy_8bit_fhd_requested=dormant_proxy_8bit_fhd_requested,
        vpg400_caution_acknowledged=vpg400_caution_acknowledged,
        claimed_sdhc_no_4gb_split=claimed_sdhc_no_4gb_split,
        claimed_proxy_blocked_on_dci4k_60p=claimed_proxy_blocked_on_dci4k_60p,
        claimed_proxy_resists_camera_reset=claimed_proxy_resists_camera_reset,
        proxy_slot1_write_or_coupled_delete_requested=proxy_slot1_write_or_coupled_delete_requested,
        claimed_fx3_has_fx6_chunk_upload=claimed_fx3_has_fx6_chunk_upload,
    )
    gb = evaluate_p321_check_group_b_cloud_ble_zerorf_and_mymenu(
        cloud_connection=cloud_connection,
        c3_portal_enabled=c3_portal_enabled,
        clip_flag_filter=clip_flag_filter,
        ftp_transfer_func=ftp_transfer_func,
        claimed_cloud_wiped_by_camera_reset=claimed_cloud_wiped_by_camera_reset,
        claimed_cloud_wiped_by_initialize=claimed_cloud_wiped_by_initialize,
        claimed_c3_portal_before_v400=claimed_c3_portal_before_v400,
        claimed_fx3_cloud_does_not_exclude_ftp=claimed_fx3_cloud_does_not_exclude_ftp,
        airplane_mode=airplane_mode,
        cnct_while_power_off=cnct_while_power_off,
        bluetooth_function=bluetooth_function,
        wifi_enabled=wifi_enabled,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        rf_nvs_p12_p13_writes_requested=rf_nvs_p12_p13_writes_requested,
        claimed_cnct_while_power_off_wiped_by_camera_reset=claimed_cnct_while_power_off_wiped_by_camera_reset,
        fx6_has_bluetooth_claimed=fx6_has_bluetooth_claimed,
        mymenu_pages=mymenu_pages,
        mymenu_slots_per_page=mymenu_slots_per_page,
        mymenu_total_slots=mymenu_total_slots,
        fx3_mymenu_30_or_36_slots_only_claimed=fx3_mymenu_30_or_36_slots_only_claimed,
        mymenu_playback_item_requested=mymenu_playback_item_requested,
        claimed_mymenu_wiped_by_camera_reset=claimed_mymenu_wiped_by_camera_reset,
        fx6_user_menu_pin=fx6_user_menu_pin,
        claimed_fx3_has_pin_user_menu_with_lock=claimed_fx3_has_pin_user_menu_with_lock,
        claimed_fx6_user_menu_pin_included_in_all_file=claimed_fx6_user_menu_pin_included_in_all_file,
    )
    gc = evaluate_p321_check_group_c_ftpes_passive_usblan_and_wb(
        ftp_transfer_func=ftp_transfer_func,
        ftp_server_slot=ftp_server_slot,
        ftp_protocol=ftp_protocol,
        ftp_transfer_mode=ftp_transfer_mode,
        ftp_active_mode_requested=ftp_active_mode_requested,
        fx3_sftp_present_claimed=fx3_sftp_present_claimed,
        fx3_ftp_active_mode_present_claimed=fx3_ftp_active_mode_present_claimed,
        dormant_transfer_jpeg_heif_size_requested=dormant_transfer_jpeg_heif_size_requested,
        fx3_transfer_jpeg_heif_size_present_claimed=fx3_transfer_jpeg_heif_size_present_claimed,
        claimed_fx3_uses_certification_pem_slot_b=claimed_fx3_uses_certification_pem_slot_b,
        claimed_fx3_ftp_limited_to_3_servers=claimed_fx3_ftp_limited_to_3_servers,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        ftp_slot1_write_or_transfer_list_requested=ftp_slot1_write_or_transfer_list_requested,
        cacert_pem_size_bytes=cacert_pem_size_bytes,
        cacert_write_to_slot1_requested=cacert_write_to_slot1_requested,
        usb_lan_tethering=usb_lan_tethering,
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        network_transport=network_transport,
        claimed_airplane_mode_blocks_usb_lan=claimed_airplane_mode_blocks_usb_lan,
        wb_mode=wb_mode,
        wb_kelvin_k=wb_kelvin_k,
        wb_ab_shift=wb_ab_shift,
        wb_gm_shift=wb_gm_shift,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        custom_wb_setup_requested=custom_wb_setup_requested,
        claimed_custom_wb_saved_in_camset=claimed_custom_wb_saved_in_camset,
        claimed_custom_wb_wiped_by_camera_reset=claimed_custom_wb_wiped_by_camera_reset,
        priority_set_in_awb=priority_set_in_awb,
        shutter_awb_lock=shutter_awb_lock,
        shockless_wb=shockless_wb,
        claimed_shutter_awb_lock_wiped_by_camera_reset=claimed_shutter_awb_lock_wiped_by_camera_reset,
        claimed_shockless_wb_resists_camera_reset=claimed_shockless_wb_resists_camera_reset,
        claimed_fx3_has_atw_speed_or_memory_ah=claimed_fx3_has_atw_speed_or_memory_ah,
    )
    gd = evaluate_p321_check_group_d_af_focus_map_marker_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        body_model_id=body_model_id,
        body_fw=body_fw,
        af_transition_speed=af_transition_speed,
        af_subj_shift_sens=af_subj_shift_sens,
        fx3_af_subj_shift_7_levels_claimed=fx3_af_subj_shift_7_levels_claimed,
        fx6_af_subj_shift_7_levels_claimed=fx6_af_subj_shift_7_levels_claimed,
        af_assist=af_assist,
        lens_model=lens_model,
        claimed_af_assist_resists_camera_reset=claimed_af_assist_resists_camera_reset,
        in_body_focus_map_requested=in_body_focus_map_requested,
        fx3_in_body_focus_map_present_claimed=fx3_in_body_focus_map_present_claimed,
        fx3_uvc_streaming_present_claimed=fx3_uvc_streaming_present_claimed,
        mc_focus_map_enabled=mc_focus_map_enabled,
        mc_focus_map_fps=mc_focus_map_fps,
        mc_focus_map_over_wifi_requested=mc_focus_map_over_wifi_requested,
        playback_control_active=playback_control_active,
        lens_pdaf_capable=lens_pdaf_capable,
        auto_framing_claimed=auto_framing_claimed,
        usb_remote_or_uvc_active=usb_remote_or_uvc_active,
        claimed_mc_focus_map_blocked_at_120p=claimed_mc_focus_map_blocked_at_120p,
        aspect_marker=aspect_marker,
        exposed_aspect_markers=exposed_aspect_markers,
        safety_zone=safety_zone,
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        focus_magnifier_active=focus_magnifier_active,
        expect_marker_or_peaking_on_hdmi=expect_marker_or_peaking_on_hdmi,
        expect_marker_visible_during_focus_magnifier=expect_marker_visible_during_focus_magnifier,
        claimed_marker_or_peaking_wiped_by_camera_reset=claimed_marker_or_peaking_wiped_by_camera_reset,
        claimed_fx3_has_user_box_or_925_95_safety_or_bw_peaking=claimed_fx3_has_user_box_or_925_95_safety_or_bw_peaking,
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
        overall_status = P321_GO_NO_GO_BLOCKED_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_FAILURE
        go_no_go = P321_GO_NO_GO_BLOCKED_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_FAILURE
    elif simulate_bench_dry_run and gd.tier0_receipt_verified:
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
    elif gd.tier0_receipt_verified:
        overall_status = P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED
        go_no_go = P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED
    else:
        overall_status = P321_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT

    slot1_mutated = bool(ga.slot1_tier0_vault_mutated or gc.slot1_tier0_vault_mutated)

    report = RealHwRecMediaAutoswitchProxyCloudMyMenuFtpesReport(
        schema_version=P321_SCHEMA,
        phase_version=P321_VERSION,
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
        fx3_prioritize_rec_media_present=False,
        fx3_movie_sort_recording_present=False,
        fx3_mymenu_30_or_36_slots_only=False,
        fx3_ftp_sftp_present=False,
        fx3_ftp_active_mode_present=False,
        fx3_ftp_transfer_jpeg_size_present=False,
        fx3_in_body_focus_map_present=False,
        fx3_uvc_streaming_present=False,
        fx3_af_subj_shift_7_levels_present=False,
        e_nd_actuator_tx_count=PHASE321_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=0,
        rf_packets_transmitted=PHASE321_WIRELESS_RF_PACKETS_EMITTED,
        wireless_rf_packets_emitted=PHASE321_WIRELESS_RF_PACKETS_EMITTED,
        slot1_data_sector_writes=PHASE321_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE321_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE321_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE321_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwRecMediaAutoswitchProxyCloudMyMenuFtpesReport(
        **{**report.to_dict(), "check_group_a": ga, "check_group_b": gb, "check_group_c": gc, "check_group_d": gd, "donor_inspection": donor, "report_sha256": digest}
    )


def run_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(
    **kwargs: Any,
) -> RealHwRecMediaAutoswitchProxyCloudMyMenuFtpesReport:
    return evaluate_realhw_rec_media_autoswitch_proxy_cloud_mymenu_and_ftpes_preflight(**kwargs)


def verify_phase321_report(
    payload: Union[Mapping[str, Any], RealHwRecMediaAutoswitchProxyCloudMyMenuFtpesReport],
) -> Phase321ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P321_SCHEMA:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r} != {P321_SCHEMA!r}")
    if payload.get("sony_help_guide_id") != P321_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_321_VALID_GO_NO_GO_VALUES:
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
        "fx3_prioritize_rec_media_present",
        "fx3_movie_sort_recording_present",
        "fx3_mymenu_30_or_36_slots_only",
        "fx3_ftp_sftp_present",
        "fx3_ftp_active_mode_present",
        "fx3_ftp_transfer_jpeg_size_present",
        "fx3_in_body_focus_map_present",
        "fx3_uvc_streaming_present",
        "fx3_af_subj_shift_7_levels_present",
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
        P321_GO_NO_GO_REC_MEDIA_PROXY_CLOUD_MYMENU_FTPES_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase321ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase321_markdown(report: RealHwRecMediaAutoswitchProxyCloudMyMenuFtpesReport) -> str:
    lines = [
        f"# Phase 321 — 14th Physical Bench Readiness Preflight (`{report.schema_version}`)",
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
        f"`e_nd_i2c={report.e_nd_i2c_tx_bytes}`, `leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"rec_media=`{report.check_group_a.recording_media}`, auto_switch=`{report.check_group_a.auto_switch_media}`, "
        f"proxy=`{report.check_group_a.proxy_recording}`",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"airplane=`{report.check_group_b.airplane_mode}`, cnct_power_off=`{report.check_group_b.cnct_while_power_off}`, "
        f"mymenu=`{report.check_group_b.mymenu_pages}x{report.check_group_b.mymenu_slots_per_page}={report.check_group_b.mymenu_total_slots}`",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"ftp=`{report.check_group_c.ftp_protocol}/{report.check_group_c.ftp_transfer_mode}`, "
        f"usb_lan=`{report.check_group_c.usb_lan_tethering}`, wb=`{report.check_group_c.wb_mode}/{report.check_group_c.wb_kelvin_k}K`",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"af_speed=`{report.check_group_d.af_transition_speed}`, af_sens=`{report.check_group_d.af_subj_shift_sens}`, "
        f"aspect_marker=`{report.check_group_d.aspect_marker}` (`{report.check_group_d.aspect_marker_state_count}` states)",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
