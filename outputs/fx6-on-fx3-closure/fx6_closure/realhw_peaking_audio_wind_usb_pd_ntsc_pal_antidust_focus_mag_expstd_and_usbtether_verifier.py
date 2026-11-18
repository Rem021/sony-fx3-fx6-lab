"""Phase 342: 19th Real-Hardware Physical Bench & Pre-Shoot Readiness Verifier (Waves 70-71).

Verifies Sony ``ILME-FX3 Ver. 7.02`` (``ilc/2210``, Model ``0x91030080``) vs ``ILME-FX6`` (``Ver. 6.01``)
empirical hardware/firmware/menu invariants across Global Sony Waves 70-71 before any physical bench session:

1. **Check Group A (Wave 70 §§1-2)** — Reset-Immune ``Shooting -> [Focus] -> [Peaking Display]``
   (``Off/On``, ``High/Mid/Low``, ``Red/Yellow/Blue/White``, ``0`` px HDMI output, coexists with
   ``Focus Magnifier``, body-dormant ``Focus Map`` ``EOPNOTSUPP=95`` wireless *Monitor & Control* only)
   vs Debunking FX6 ``Peaking Type/Freq`` Myth (``0`` hits in ``FX6 appFw.so``; FX6 exposes only
   ``Setting`` / ``Peaking Level`` / ``Color`` ``B&W/Red/Yellow/Blue``) + Ver. 2.00+ Removal of
   Standalone ``[Audio Level Display]`` (exact 5 Resettable ``[Audio Recording]`` items) &
   Debunking FX3 ``[Wind Noise Reduct.]`` ``Auto`` Myth (``On/Off`` ONLY on built-in stereo mic,
   auto-bypassed under ``XLR-H1`` / ``3.5mm`` mic) vs ``FX6`` ``CH1..CH4 Wind Filter`` & 6-step ``Limiter Mode``:
   - ``[Peaking Display]`` (``0x6fe5``/``0x6798``/``0x6d4e``, ``_g 0x6050``, ``BKID_APP_setting_peaking_display``,
     right control-wheel key ``[Peaking Display Select]`` ``0x62a8``/``0x7b12``), ``[Peaking Level]``
     (``0xe14c``: ``High`` / ``Mid`` default / ``Low``), ``[Peaking Color]`` (``0xe14d``/``0xe52f``:
     ``Red`` / ``Yellow`` / ``Blue`` / ``White`` default). All 3 are **Reset-immune**, **never output
     over HDMI** (``0`` px regardless of ``[HDMI Info. Display]`` or ``RAW Output``), coexist with
     ``[Focus Magnifier]`` (``0`` ``PRM_HAITA_*`` exclusions), and work in MF/DMF and Movie AF.
     In-body ``Focus Map`` (``0x61f9``/``0x6247``, ``view_mp_focus_map``) is 100% dormant (``EOPNOTSUPP=95``)
     and lives only in wireless *Monitor & Control* Ver. 2.1.0+ (unavailable over USB M&C).
   - ``FX6 appFw.so`` has ``0`` ``PEAKING_TYPE``/``PEAKING_FREQ`` symbols (dormant FS7/F5/F55 UXC strings
     ``ns2 0x4501/0x4503``); FX6 exposes ONLY ``Setting`` / ``Peaking Level`` / ``Color`` (``B&W``, not ``White``).
   - Ver. 2.00+–7.02 (``ilc/2210``) removed standalone ``[Audio Level Display]`` (``0x7a36``), leaving
     exact **5 Resettable** ``[Audio Recording]`` items: ``[Audio Recording]``, ``[Audio Rec Level]``
     (``0..31``, default ``26``, ELF typo ``adj_audio_rec_level_defult``, non-disableable limiter),
     ``[Audio Out Timing]`` (``Live``/``Lip Sync`` in ``Shooting``, not ``Setup -> [Sound Option]``),
     ``[Wind Noise Reduct.]`` (``Off``/``On`` ONLY — **zero ``Auto``**, ``MSG_ID_INFRABB_ADF_IN_SET_LOW_CUT``
     applies ONLY to internal stereo mic, bypassed under ``3.5mm``/``XLR-H1``/MI-Shoe mic, disabled in S&Q),
     and ``[Shoe Audio Set.]``. Contrast FX6 standard handle (zero hardware ``LOW CUT`` switch) vs
     ``CH1..CH4 Wind Filter`` & 6-step ``Limiter Mode`` (``Off / -6..-17 dB``).

2. **Check Group B (Wave 70 §§3-4)** — ``[USB Power Supply]`` (``9V/3A 27W+`` Type-C PD, Mandatory
   ``NP-FZ100`` Insertion Law via ``libUsbBusPower.so``, Zero Charging While Camera ``ON``, ``DC-C1``
   ``>= 65W PD + 5A`` Cable) vs ``FX6`` ``19.5V`` EIAJ ``DC IN`` Battery-Less Boot + ``[NTSC/PAL Selector]``
   (``J1`` NTSC-Locked vs ``CE/E33`` ``Running on NTSC.`` vs ``U2`` ``Running on PAL.``, XAVC Reboot +
   ``AVF_INFO`` ``Create?`` Without Mandatory Format, Tier-0 ``Slot 1`` ``EROFS=30``) vs ``FX6`` ``System Frequency``:
   - ``Setup -> [USB] -> [USB Power Supply]`` (``0x721e``/``0x7309``, ``BKID_APP_setting_usb_supply``, Reset-immune):
     USB Type-C ONLY (``base 0xe931`` rejects Multi/Micro USB); ``9V/3A`` (``27W+``) USB PD recommended;
     ``libUsbBusPower.so`` (``GetCurrentBattState``, ``IsSinkReady``,
     ``VAL_battery_inserted_BATTERY_IS_INSERTED``) enforces **mandatory ``NP-FZ100`` insertion**
     (zero battery-less boot, cuts power on removal); **zero battery charging while camera ``ON``**
     (amber ``CHARGE`` LED stays ``OFF`` when ``ON``, charges only when ``OFF`` at ``10..30 C``);
     ``DC-C1`` requires ``>= 65W`` USB PD + ``5A`` cable. Contrast FX6 ``19.5V`` EIAJ ``DC IN`` (true
     battery-less boot, forbids hot-replug during ``REC``).
   - ``[NTSC/PAL Selector]`` (``0x6b6f``, ``lib::backup_get_ntsc_pal_selector_dst``, Reset-immune):
     ``J1`` is NTSC-locked (``EOPNOTSUPP=95``); ``CE``/``E33`` shows ``"Running on NTSC."`` (``0xe77a``)
     when switched to NTSC; ``U2`` shows ``"Running on PAL."`` (``0xe0b6``) when switched to PAL;
     forces cold reboot, Ver. 7.02 pure XAVC does NOT require formatting card, ``AVF_INFO`` prompts
     ``Create?``/``Update?`` (blocked on ``Slot 1`` Tier-0 vault via ``EROFS=30``), vs FX6
     ``System Frequency`` (6 freqs, ``Thumbnail`` clip visibility filter hazard).

3. **Check Group C (Wave 71 §§1-2)** — Dormant ``[Anti-Dust Function]`` / ``[Shutter When Pwr OFF]``
   Myth-Busting (``0`` Hits in ``ilc/2210``, ``ALCIN_UUD`` Mask, Mechanical Shutter Parks **OPEN**,
   Only ``[Sensor Cleaning]`` ``>= 51%`` IBIS Shake) vs ``FX6`` Sealed ``e-ND`` + ``APR`` & Reset-Immune
   ``[Focus Assistant]`` (FF ``x1.0->x2.1->x4.1``, APS-C ``x1.0->x1.5->x3.0``, Movie ``x1.0->x4.0``,
   Still-Only ``AF in Focus Mag.``/``Auto Magnifier in MF``, Movie ``REC`` Persistence + Clean-HDMI Isolation):
   - ``[Anti-Dust Function]`` (``0x7495``) & ``[Shutter When Pwr OFF]`` (``0x709f``,
     ``BKID_APP_setting_image_sensor_barrier``, ``PID_SET_IMAGE_SENSOR_BARRIER``) are masked by
     ``VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD`` (``0`` hits in ``ilc/2210`` -> ``EOPNOTSUPP=95``).
     FX3 mechanical focal-plane shutter curtains park **OPEN** on power-off; sole active cleaning
     entry is ``Setup -> [Setup Option] -> [Sensor Cleaning]`` (``0x67d6``, ``>= 51%`` battery + IBIS shake +
     mandatory power ``OFF``). Contrast FX6 sealed ``1/4..1/128 + CLEAR`` ``e-ND`` + IR-cut & ``Technical > APR``.
   - ``[Focus Assistant]`` (``Focus Magnifier``, ``Focus Magnif. Time`` ``2s/5s/No Limit``,
     ``Initial Focus Mag.``, ``AF in Focus Mag.`` Still-only, ``Auto Magnifier in MF`` Still-only):
     ALL **Reset-immune**; exact scales FF ``x1.0->x2.1->x4.1``, APS-C ``x1.0->x1.5->x3.0``, Movie ``x1.0->x4.0``
     (dormant high-MP scales ``EOPNOTSUPP=95``); persists through Movie ``REC``; **0** Clean-HDMI or
     internal-REC crop; contrast FX6 VF ``x3/x6`` & Ver. 6.0+ HDMI ``x2/x4``.

4. **Check Group D (Wave 71 §§3-4 & Tier-0 ``H0 == H3`` Gate)** — ``[Exposure Std. Adjust]``
   (``-1..+1 EV`` in ``1/6 EV`` Across 5 Metering Modes, Reset-Immune Operator Calibration Trap!)
   vs Debunking FX6 ``±2.0`` Myth (``FX6 Auto Exposure > Level`` is ``-3.0..+3.0`` in ``0.25`` Step, 25 Steps)
   + Wired Smartphone ``[USB-LAN/Tethering]`` (``libNetServiceTethering.so`` + ``cdc_ncm/rndis_host/ipheth.ko``
   Driving ``RTMP/RTMPS/SRT`` & ``FTP`` While ``[Airplane Mode]=On`` Zero-RF) + Tier-0 ``Slot 1`` ``EROFS=30``
   & ``usbgmscif_setReadOnly`` Blocking ``MTP``/``MSC`` Host Writes (``16/16 H0 == H3``) vs ``FX6`` ``usbg_iap.ko``:
   - ``[Exposure Std. Adjust]`` (``0x6f71``): all 5 metering modes (``Multi/Center/Spot/Entire Screen Avg./Highlight``)
     support ``-1..+1 EV`` in ``1/6 EV`` (``13`` steps, ``EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_6``; ``1/8 EV`` dormant);
     **Reset-immune** trap (``Camera Settings Reset`` = ``Not available``; shifts ``M.M.`` zero without modifying
     EXIF ``ExposureBiasValue``; non-zero warning icon ``0xe567``); bench preflight enforces ``0 EV`` unless
     explicitly acknowledged. Debunks FX6 ``±2.0`` myth: FX6 ``Auto Exposure > Level`` is ``-3.0..+3.0``
     (``0.25`` step, 25 steps) + per-LUT ``AE Level Offset``.
   - Wired smartphone ``[USB-LAN/Tethering]`` (``0x7d2a``, ``libNetServiceTethering.so``, ``libTetheringResource.so``,
     ``cdc_ncm/cdc_ether/rndis_host/ipheth.ko``) drives ``RTMP/RTMPS/SRT`` & ``FTP`` while ``[Airplane Mode]=On``
     (zero RF), forbids simultaneous Type-C + Multi USB, warns on ``[Reset Network Set.]`` auto-reboot
     re-enabling RF unless ``[Airplane Mode]=On`` is re-asserted, enforces ``usbgmscif_setReadOnly`` + ``EROFS=30``
     on ``Slot 1`` ``MTP``/``MSC`` host writes (``16/16 H0 == H3``, ``emmc_write_count=0``), and verifies FX3
     stripped ``CUsbGadgetIAP`` (``0`` hits) vs FX6 ``usbg_iap.ko``.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import hashlib
import json
import os
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

P342_VERSION = "phase342_v1"
PHASE_342_VERSION = P342_VERSION
P342_SCHEMA = (
    "realhw_preflight19_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_usbtether_v1"
)
P342_SCHEMA_VERSION = P342_SCHEMA
PHASE_342_SCHEMA = P342_SCHEMA
REALHW_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_SCHEMA = (
    P342_SCHEMA
)
P342_SONY_HELP_GUIDE_ID = "ilc/2210"

P342_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS = "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
P342_GO_NO_GO_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED = (
    "READONLY_PREFLIGHT19_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED"
)
P342_GO_NO_GO_BLOCKED_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_FAILURE = (
    "BLOCKED_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_FAILURE"
)
PHASE_342_VALID_GO_NO_GO_VALUES = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P342_GO_NO_GO_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED,
    P342_GO_NO_GO_BLOCKED_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_FAILURE,
)

P342_CHECK_GROUP_A_ID = (
    "P342_GA_PEAKING_HDMI_ISOLATION_AUDIO_LEVEL_REMOVAL_WIND_NOISE_AND_FX6_PARITY"
)
P342_CHECK_GROUP_B_ID = (
    "P342_GB_USB_PD_NP_FZ100_LAW_DC_C1_NTSC_PAL_AVF_INFO_AND_SLOT1_EROFS"
)
P342_CHECK_GROUP_C_ID = (
    "P342_GC_DORMANT_ANTIDUST_SHUTTER_PWROFF_OPEN_PARK_AND_FOCUS_ASSISTANT"
)
P342_CHECK_GROUP_D_ID = (
    "P342_GD_EXP_STD_ADJUST_1_6_EV_USBLAN_TETHERING_EROFS_AND_TIER0_H0_H3"
)
PHASE_342_CHECK_GROUP_IDS = (
    P342_CHECK_GROUP_A_ID,
    P342_CHECK_GROUP_B_ID,
    P342_CHECK_GROUP_C_ID,
    P342_CHECK_GROUP_D_ID,
)

P342_ERRNO_EPERM = 1
P342_ERRNO_EBUSY = 16
P342_ERRNO_EINVAL = 22
P342_ERRNO_EROFS = 30
P342_ERRNO_EOPNOTSUPP = 95

P342_STORAGE_SURFACE_COUNT = 16
P342_HEADER_READ_BYTES = 64

PHASE342_EMMC_WRITE_COUNT = 0
PHASE342_E_ND_ACTUATOR_TX_COUNT = 0
PHASE342_WIRELESS_RF_PACKETS_EMITTED = 0
PHASE342_SLOT1_DATA_SECTOR_WRITES = 0
PHASE342_USB_PACKETS_TRANSMITTED = 0
PHASE342_PASSIVE_TX_BYTES_EMITTED = 0
PHASE342_RAW_FIRMWARE_BYTES_LEAKED = 0

P342_BOUNDED_DONOR_PATHS: Tuple[Tuple[str, str], ...] = (
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
        "fx3_libnetservicetethering_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libNetServiceTethering.so",
    ),
    (
        "fx3_libtetheringresource_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libTetheringResource.so",
    ),
    (
        "fx3_libinfrausbcmn_so",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraUsbCmn.so",
    ),
    (
        "fx3_upm_ko",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-modules/upm.ko",
    ),
)

# ---------------------------------------------------------------------------
# Common & Wave 70-71 Technical Constants
# ---------------------------------------------------------------------------
P342_VALID_ON_OFF = ("ON", "OFF")
P342_VALID_RESET_ACTIONS = ("NONE", "CAMERA_SETTINGS_RESET", "RESET_NETWORK_SET", "INITIALIZE")
P342_VALID_SHOOT_MODES = ("PHOTO", "MOVIE", "S_AND_Q")
P342_VALID_FOCUS_MODES = ("AF_S", "AF_C", "DMF", "MF")
P342_VALID_LOG_SHOOTING_MODES = ("OFF", "FLEXIBLE_ISO", "CINE_EI_QUICK", "CINE_EI")

# Group A: Peaking Display & Audio Recording / Wind Noise Reduct. (Wave 70 §§1-2)
P342_PEAKING_EXACT_THREE_ITEMS = ("PEAKING_DISPLAY", "PEAKING_LEVEL", "PEAKING_COLOR")
P342_PEAKING_THREE_LEVELS = ("HIGH", "MID", "LOW")
P342_PEAKING_FOUR_COLORS = ("RED", "YELLOW", "BLUE", "WHITE")
P342_PEAKING_DISPLAY_RESIDS = ("0x6fe5", "0x6798", "0x6d4e")
P342_PEAKING_DISPLAY_G_RESID16_HEX = "0x6050"
P342_PEAKING_LEVEL_RESID16_HEX = "0xe14c"
P342_PEAKING_COLOR_RESIDS = ("0xe14d", "0xe52f")
P342_PEAKING_SELECT_KEY_RESIDS = ("0x62a8", "0x7b12")
P342_PEAKING_BKID = "BKID_APP_setting_peaking_display"
P342_FX3_PEAKING_OUTPUTS_TO_HDMI = False
P342_PEAKING_COEXISTS_WITH_FOCUS_MAGNIFIER = True
P342_FX3_IN_BODY_FOCUS_MAP_PRESENT = False
P342_DORMANT_FOCUS_MAP_RESIDS = ("0x61f9", "0x6247")
P342_FX6_PEAKING_TYPE_FREQ_SYMBOL_HITS = 0
P342_FX6_PEAKING_EXACT_THREE_ITEMS = ("SETTING", "PEAKING_LEVEL", "COLOR")
P342_FX6_PEAKING_FOUR_COLORS = ("BW", "RED", "YELLOW", "BLUE")
P342_FX6_PEAKING_DORMANT_UXC_RESIDS = ("0x4501", "0x4503")

P342_REMOVED_AUDIO_LEVEL_DISPLAY_RESID16_HEX = "0x7a36"
P342_REMOVED_AUDIO_LEVEL_DISPLAY_BKID = "BKID_APP_setting_audio_recording_level_display"
P342_FX3_AUDIO_LEVEL_DISPLAY_MENU_PRESENT = False
P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS = (
    "AUDIO_RECORDING",
    "AUDIO_REC_LEVEL",
    "AUDIO_OUT_TIMING",
    "WIND_NOISE_REDUCT",
    "SHOE_AUDIO_SET",
)
P342_AUDIO_REC_LEVEL_MIN = 0
P342_AUDIO_REC_LEVEL_MAX = 31
P342_AUDIO_REC_LEVEL_DEFAULT = 26
P342_AUDIO_REC_LEVEL_ELF_TYPO_SYMBOL = "adj_audio_rec_level_defult"
P342_VALID_AUDIO_OUT_TIMINGS = ("LIVE", "LIP_SYNC")
P342_WIND_NOISE_REDUCT_EXACT_TWO_MODES = ("OFF", "ON")
P342_WIND_NOISE_REDUCT_DORMANT_AUTO_RESID16_HEX = "0x623c"
P342_WIND_NOISE_REDUCT_LOW_CUT_MSG = "MSG_ID_INFRABB_ADF_IN_SET_LOW_CUT"
P342_FX3_WIND_NOISE_AUTO_PRESENT = False
P342_SHOE_AUDIO_MODES = ("48KHZ_24BIT_4CH", "48KHZ_24BIT_2CH", "48KHZ_16BIT_2CH")
P342_PROXY_AUDIO_CODEC = "MPEG-4 AAC-LC 2ch 128kbps"
P342_FX6_HANDLE_PHYSICAL_LOW_CUT_SWITCH_PRESENT = False
P342_FX6_LIMITER_MODE_SIX_STEPS = ("OFF", "-6dB", "-9dB", "-12dB", "-15dB", "-17dB")
P342_FX6_AUDIO_LEVEL_METER_UXC_RESID16_HEX = "0x454e"

# Group B: USB Power Supply & NTSC/PAL Selector (Wave 70 §§3-4)
P342_USB_POWER_SUPPLY_RESIDS = ("0x721e", "0x7309")
P342_USB_POWER_SUPPLY_BKID = "BKID_APP_setting_usb_supply"
P342_USB_POWER_TERMINAL_ALLOWED = "USB_TYPE_C"
P342_VALID_USB_POWER_TERMINALS = ("USB_TYPE_C", "MULTI_MICRO_USB")
P342_VALID_CAMERA_POWER_STATES = ("ON", "OFF")
P342_USB_PD_RECOMMENDED_VOLTS = 9
P342_USB_PD_RECOMMENDED_AMPS = 3
P342_USB_PD_RECOMMENDED_WATTS = 27.0
P342_DC_C1_MIN_PD_WATTS = 65.0
P342_DC_C1_MIN_CABLE_AMPS = 5
P342_USB_BUS_POWER_REQUIRED_SYMBOLS = (
    "GetCurrentBattState",
    "IsSinkReady",
    "VAL_battery_inserted_BATTERY_IS_INSERTED",
    "VAL_battery_inserted_BATTERY_IS_NOT_INSERTED",
    "UPM_PS_TYPE_BATTERY",
    "UPM_PS_TYPE_ACV",
)
P342_FX3_CHARGES_BATTERY_WHILE_ON = False
P342_FX3_SUPPORTS_BATTERYLESS_USB_PD_BOOT = False
P342_CHARGE_LED_COLOR = "AMBER"
P342_FX6_DC_IN_NOMINAL_VOLTS = 19.5
P342_FX6_DC_IN_MIN_VOLTS = 18.0
P342_FX6_DC_IN_MAX_VOLTS = 20.5
P342_FX6_BATTERYLESS_DC_IN_BOOT_SUPPORTED = True
P342_FX6_USB_C_POWERS_BODY = False

P342_NTSCPAL_RESID16_HEX = "0x6b6f"
P342_NTSCPAL_DST_SYMBOL = "backup_get_ntsc_pal_selector_dst"
P342_VALID_NTSC_PAL_SKUS = ("CE", "E33", "U2", "J1")
P342_VALID_VIDEO_SYSTEMS = ("NTSC", "PAL")
P342_RUNNING_ON_NTSC_BANNER = "Running on NTSC."
P342_RUNNING_ON_PAL_BANNER = "Running on PAL."
P342_RUNNING_ON_NTSC_RESID16_HEX = "0xe77a"
P342_RUNNING_ON_PAL_RESID16_HEX = "0xe0b6"
P342_AVF_INFO_CREATE_PROMPT = "Image Database File not found. Create?"
P342_AVF_INFO_CREATE_RESID16_HEX = "0xea23"
P342_AVF_INFO_UPDATE_RESID16_HEX = "0xea24"
P342_RECOVER_IMAGE_DB_RESID16_HEX = "0xe918"
P342_XAVC_REQUIRES_MANDATORY_CARD_FORMAT = False
P342_FX6_SYSTEM_FREQUENCIES_HZ = (59.94, 50.0, 29.97, 25.0, 24.0, 23.98)

# Group C: Dormant Anti-Dust/Shutter Pwr OFF & Focus Assistant (Wave 71 §§1-2)
P342_DORMANT_ANTI_DUST_FUNCTION_RESID16_HEX = "0x7495"
P342_DORMANT_SHUTTER_WHEN_PWR_OFF_RESID16_HEX = "0x709f"
P342_SHUTTER_BARRIER_BKID = "BKID_APP_setting_image_sensor_barrier"
P342_SHUTTER_BARRIER_PID = "PID_SET_IMAGE_SENSOR_BARRIER"
P342_ALCIN_UUD_MASK_ENUM = "VAL_FEATURE_MANAGER_menu_item_TYPE_MENU_ITEM_ALCIN_UUD"
P342_FX3_SHUTTER_WHEN_PWR_OFF_PRESENT = False
P342_FX3_ILC2210_SHUTTER_PWROFF_HITS = 0
P342_FX3_POWER_OFF_SHUTTER_PARK_STATE = "OPEN"
P342_SENSOR_CLEANING_RESID16_HEX = "0x67d6"
P342_SENSOR_CLEANING_MIN_BATTERY_PCT = 51
P342_FX6_SHUTTER_WHEN_PWR_OFF_HITS = 0
P342_FX6_SENSOR_CLEANING_PRESENT = False
P342_FX6_E_ND_STEPS = ("CLEAR", "1/4", "1/16", "1/64", "1/128")

P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS = (
    "FOCUS_MAGNIFIER",
    "FOCUS_MAGNIF_TIME",
    "INITIAL_FOCUS_MAG",
    "AF_IN_FOCUS_MAG",
    "AUTO_MAGNIFIER_IN_MF",
)
P342_VALID_FOCUS_MAGNIF_TIMES = ("2_SEC", "5_SEC", "NO_LIMIT")
P342_STILL_FF_INITIAL_MAG_SCALES = (1.0, 2.1)
P342_STILL_FF_MAG_CYCLE_SCALES = (1.0, 2.1, 4.1)
P342_STILL_APSC_INITIAL_MAG_SCALES = (1.0, 1.5)
P342_STILL_APSC_MAG_CYCLE_SCALES = (1.0, 1.5, 3.0)
P342_MOVIE_MAG_CYCLE_SCALES = (1.0, 4.0)
P342_DORMANT_HIGH_MP_MAG_SCALES = (1.6, 2.7, 3.1, 3.6, 3.7, 4.2, 4.7, 5.3, 5.5, 6.1)
P342_FOCUS_MAG_PERSISTS_DURING_MOVIE_REC = True
P342_FOCUS_MAG_OUTPUTS_TO_HDMI = False
P342_FX6_VF_FOCUS_MAG_SCALES = (3.0, 6.0)
P342_FX6_HDMI_FOCUS_MAG_SCALES = (2.0, 4.0)

# Group D: Exposure Std. Adjust, Wired USB-LAN/Tethering & Tier-0 H0 == H3 (Wave 71 §§3-4)
P342_EXP_STD_ADJ_RESID16_HEX = "0x6f71"
P342_EXP_STD_ADJ_FIVE_METERING_MODES = (
    "MULTI",
    "CENTER",
    "SPOT",
    "ENTIRE_SCREEN_AVG",
    "HIGHLIGHT",
)
P342_EXP_STD_ADJ_MIN_SIXTHS = -6
P342_EXP_STD_ADJ_MAX_SIXTHS = 6
P342_EXP_STD_ADJ_EXACT_STEPS = 13
P342_EXP_STD_ADJ_STEP_ENUM = "EXTERN_VAL_STANDARD_EXPOSURE_STEP_1_6"
P342_EXP_STD_ADJ_RESET_IMMUNE = True
P342_EXP_STD_ADJ_MODIFIES_EXIF_BIAS = False
P342_EXP_STD_ADJ_WARNING_RESID16_HEX = "0xe567"
P342_FX6_AE_LEVEL_MIN_EV = -3.0
P342_FX6_AE_LEVEL_MAX_EV = 3.0
P342_FX6_AE_LEVEL_STEP_EV = 0.25
P342_FX6_AE_LEVEL_EXACT_STEPS = 25
P342_FX6_BASE_LOOK_AE_LEVEL_OFFSET_SYMBOL = "AE Level Offset"

P342_USB_CONN_MODE_RESID16_HEX = "0x69a2"
P342_USB_CONN_VALID_MODES = (
    "SEL_WHEN_CONNECT",
    "MASS_STORAGE",
    "MTP",
    "REMOTE_SHOOTING",
    "USB_STREAMING",
)
P342_USB_LUN_VALID_MODES = ("MULTI", "SINGLE")
P342_USB_LAN_CNCT_LAUNCH_RESID16_HEX = "0x7d2a"
P342_USB_LAN_LIBS = ("libNetServiceTethering.so", "libTetheringResource.so")
P342_USB_LAN_KERNEL_MODULES = ("cdc_ncm.ko", "cdc_ether.ko", "rndis_host.ko", "ipheth.ko")
P342_USB_LAN_VALID_SERVICES = ("NONE", "RTMP", "RTMPS", "SRT", "FTP", "MONITOR_AND_CONTROL")
P342_USBGMSCIF_READONLY_SYMBOL = "usbgmscif_setReadOnly"
P342_FX3_CUSB_GADGET_IAP_HITS = 0
P342_FX6_CUSB_GADGET_IAP_PRESENT = True
P342_FX3_USB_STREAMING_UVC_ACTIVE = False

# Error Prefix Constants
P342_GA_ERR_MODEL_OR_FW_FLOOR = "P342_GA_ERR_MODEL_OR_FW_FLOOR"
P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP = "P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP"
P342_GA_ERR_FX6_PEAKING_TYPE_FREQ_MYTH = "P342_GA_ERR_FX6_PEAKING_TYPE_FREQ_MYTH"
P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH = (
    "P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH"
)

P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW = "P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW"
P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY = "P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY"
P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO = "P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO"
P342_GB_ERR_SLOT1_TIER0_VAULT_EROFS = "P342_GB_ERR_SLOT1_TIER0_VAULT_EROFS"

P342_GC_ERR_DORMANT_ANTIDUST_OR_SHUTTER_PWROFF = (
    "P342_GC_ERR_DORMANT_ANTIDUST_OR_SHUTTER_PWROFF"
)
P342_GC_ERR_SENSOR_CLEANING_OR_FX6_E_ND_APR = "P342_GC_ERR_SENSOR_CLEANING_OR_FX6_E_ND_APR"
P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI = "P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI"
P342_GC_ERR_FOCUS_ASSISTANT_RESET_OR_FX6_PARITY = (
    "P342_GC_ERR_FOCUS_ASSISTANT_RESET_OR_FX6_PARITY"
)

P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP = "P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP"
P342_GD_ERR_FX6_AE_LEVEL_3EV_MYTH = "P342_GD_ERR_FX6_AE_LEVEL_3EV_MYTH"
P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX = (
    "P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX"
)
P342_GD_ERR_SLOT1_USB_WRITE_EROFS_OR_FX6_IAP = "P342_GD_ERR_SLOT1_USB_WRITE_EROFS_OR_FX6_IAP"
P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID = (
    "P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P342_GD_ERR_H0_H3_IMMUTABILITY_DRIFT = "P342_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P342_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION = "P342_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class Phase342DonorInspectionResult:
    verification_mode: str
    donor_tree_present: bool
    fx3_appfw_present: bool
    fx6_appfw_present: bool
    fx3_libusbbuspower_present: bool
    fx3_libnetservicetethering_present: bool
    fx3_libinfrausbcmn_present: bool
    checked_paths: Tuple[str, ...]
    bytes_read_total: int
    elapsed_seconds: float
    within_budget: bool
    raw_firmware_bytes_leaked: int


@dataclass(frozen=True)
class P342CheckGroupAPeakingAudioWindResult:
    group_id: str
    passed: bool
    peaking_display: str
    peaking_level: str
    peaking_color: str
    fx3_peaking_outputs_to_hdmi: bool
    peaking_coexists_with_focus_magnifier: bool
    fx3_in_body_focus_map_present: bool
    fx6_peaking_type_freq_hits: int
    fx6_peaking_colors: Tuple[str, ...]
    fx3_audio_level_display_menu_present: bool
    exposed_audio_recording_items: Tuple[str, ...]
    audio_recording: str
    audio_rec_level: int
    audio_out_timing: str
    wind_noise_reduct: str
    fx3_wind_noise_auto_present: bool
    wind_noise_internal_mic_active: bool
    mic_35mm_inserted: bool
    xlr_h1_attached: bool
    xlr_h1_handle_audio: str
    shoe_audio_set: str
    fx6_handle_physical_low_cut_switch: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class P342CheckGroupBUsbPdNtscPalSlot1Result:
    group_id: str
    passed: bool
    usb_power_supply: str
    usb_power_terminal: str
    camera_power_state: str
    usb_pd_watts: float
    usb_c_cable_amps: int
    np_fz100_inserted: bool
    battery_soc_pct: int
    dc_c1_coupler_attached: bool
    fx3_charges_battery_while_on: bool
    fx3_supports_batteryless_usb_pd_boot: bool
    fx6_dc_in_nominal_volts: float
    fx6_batteryless_dc_in_boot_supported: bool
    ntsc_pal_sku: str
    video_system: str
    ntsc_pal_boot_banner: str
    xavc_requires_mandatory_format: bool
    slot1_contains_tier0_dump: bool
    slot1_tier0_vault_mutated: bool
    slot1_data_sector_writes: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class P342CheckGroupCAntiDustFocusAssistantResult:
    group_id: str
    passed: bool
    fx3_shutter_when_pwr_off_present: bool
    fx3_ilc2210_shutter_pwroff_hits: int
    fx3_power_off_shutter_park_state: str
    alcin_uud_mask_enum: str
    sensor_cleaning_requested: bool
    sensor_cleaning_min_battery_pct: int
    battery_soc_pct: int
    fx6_shutter_when_pwr_off_hits: int
    fx6_sensor_cleaning_present: bool
    shoot_mode: str
    apsc_s35_shooting: str
    focus_magnif_time: str
    initial_focus_mag_x: float
    requested_focus_mag_x: float
    af_in_focus_mag: str
    auto_magnifier_in_mf: str
    focus_mag_persists_during_movie_rec: bool
    focus_mag_outputs_to_hdmi: bool
    fx6_vf_focus_mag_scales: Tuple[float, ...]
    fx6_hdmi_focus_mag_scales: Tuple[float, ...]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class P342CheckGroupDExpStdUsbLanTier0Result:
    group_id: str
    passed: bool
    exp_std_adjust_metering_mode: str
    exp_std_adjust_sixths: int
    exp_std_adjust_ev: float
    exp_std_adjust_reset_immune: bool
    exp_std_adjust_modifies_exif_bias: bool
    fx6_ae_level_ev: float
    fx6_ae_level_min_ev: float
    fx6_ae_level_max_ev: float
    fx6_ae_level_step_ev: float
    usb_connection_mode: str
    usb_lun_setting: str
    usb_lan_tethering: str
    usb_lan_cnct_launch: str
    usb_lan_service: str
    airplane_mode: str
    wireless_rf_packets_emitted: int
    fx3_cusb_gadget_iap_hits: int
    fx6_cusb_gadget_iap_present: bool
    usbgmscif_readonly_enforced: bool
    slot1_data_sector_writes: int
    tier0_receipt_verified: bool
    receipt_mode: str
    h0_equals_h3_count: int
    h0_h3_surface_count: int
    emmc_write_count: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]


@dataclass(frozen=True)
class Phase342ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwPeakingAudioWindUsbPdNtscPalAntiDustFocusMagExpStdUsbTetherReport:
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
    check_group_a: P342CheckGroupAPeakingAudioWindResult
    check_group_b: P342CheckGroupBUsbPdNtscPalSlot1Result
    check_group_c: P342CheckGroupCAntiDustFocusAssistantResult
    check_group_d: P342CheckGroupDExpStdUsbLanTier0Result
    donor_inspection: Phase342DonorInspectionResult
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
    fx3_peaking_outputs_to_hdmi: bool
    fx3_in_body_focus_map_present: bool
    fx6_peaking_type_freq_present: bool
    fx3_audio_level_display_menu_present: bool
    fx3_wind_noise_auto_present: bool
    fx3_charges_battery_while_on: bool
    fx3_supports_batteryless_usb_pd_boot: bool
    fx3_shutter_when_pwr_off_present: bool
    fx3_focus_mag_outputs_to_hdmi: bool
    fx3_exp_std_modifies_exif_bias: bool
    fx3_cusb_gadget_iap_present: bool
    emmc_write_count: int
    e_nd_actuator_tx_count: int
    e_nd_i2c_tx_bytes: int
    rf_packets_transmitted: int
    wireless_rf_packets_emitted: int
    rf_nvs_mutation_bytes: int
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
        """Return deterministic JSON with all timing fields (elapsed_seconds, etc.) stripped recursively."""
        return json.dumps(_strip_timing_fields(self.to_dict()), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Timing Stripping, SHA-256 & Bounded Donor Inspection Helpers
# ---------------------------------------------------------------------------
def _is_timing_key(key: str) -> bool:
    return key in (
        "elapsed_seconds",
        "elapsed_s",
        "elapsed_ms",
        "inspection_elapsed_ms",
        "wall_seconds",
    ) or key.endswith(("_elapsed_ms", "_elapsed_s", "_elapsed_seconds"))


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


def _bounded_read_header(path: Path, max_bytes: int = P342_HEADER_READ_BYTES) -> int:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        data = os.read(fd, max_bytes)
        return len(data)
    finally:
        os.close(fd)


def resolve_phase342_donor_file_or_none(
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
        if any(
            resolve_phase342_donor_file_or_none(candidate, rel) is not None
            for _lbl, rel in P342_BOUNDED_DONOR_PATHS
        ):
            return candidate
    return None


def inspect_phase342_donors_bounded(
    *,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase342DonorInspectionResult:
    """Inspect local donor headers strictly via bounded O_RDONLY (< 0.20s) with clean-room fallback."""
    t0 = time.monotonic()
    clean_room = bool(force_clean_room) if force_clean_room is not None else _is_clean_room_env()
    if clean_room:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase342DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_libusbbuspower_present=False,
            fx3_libnetservicetethering_present=False,
            fx3_libinfrausbcmn_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE342_RAW_FIRMWARE_BYTES_LEAKED,
        )

    effective_work_root = (
        work_root if work_root is not None else _resolve_work_root_or_none(force_clean_room=False)
    )
    if effective_work_root is None and fx6_lib_dir is None and fx3_modules_dir is None:
        elapsed = round(time.monotonic() - t0, 6)
        return Phase342DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            donor_tree_present=False,
            fx3_appfw_present=False,
            fx6_appfw_present=False,
            fx3_libusbbuspower_present=False,
            fx3_libnetservicetethering_present=False,
            fx3_libinfrausbcmn_present=False,
            checked_paths=(),
            bytes_read_total=0,
            elapsed_seconds=elapsed,
            within_budget=elapsed <= max_seconds,
            raw_firmware_bytes_leaked=PHASE342_RAW_FIRMWARE_BYTES_LEAKED,
        )

    checked: List[str] = []
    bytes_total = 0
    found_map: Dict[str, bool] = {}
    for label, rel in P342_BOUNDED_DONOR_PATHS:
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
            resolved = resolve_phase342_donor_file_or_none(effective_work_root, rel)
        if resolved is None and work_root is None and effective_work_root is not None:
            try:
                cand = resolve_work_subpath(rel, require_file=True)
                if cand.is_file():
                    resolved = cand
            except Exception:
                resolved = None
        if resolved is not None and resolved.is_file():
            checked.append(label)
            bytes_total += _bounded_read_header(resolved)
            found_map[label] = True
        else:
            found_map[label] = False

    donor_present = any(found_map.values())
    mode = "LOCAL_DONOR_O_RDONLY" if donor_present else "CLEAN_ROOM_SYNTHETIC"
    elapsed = round(time.monotonic() - t0, 6)
    return Phase342DonorInspectionResult(
        verification_mode=mode,
        donor_tree_present=donor_present,
        fx3_appfw_present=found_map.get("fx3_libjiritsu_so", False) and found_map.get("fx3_im_elf", False),
        fx6_appfw_present=found_map.get("fx6_appfw_so", False),
        fx3_libusbbuspower_present=found_map.get("fx3_libusbbuspower_so", False),
        fx3_libnetservicetethering_present=found_map.get("fx3_libnetservicetethering_so", False)
        and found_map.get("fx3_libtetheringresource_so", False),
        fx3_libinfrausbcmn_present=found_map.get("fx3_libinfrausbcmn_so", False),
        checked_paths=tuple(checked),
        bytes_read_total=bytes_total,
        elapsed_seconds=elapsed,
        within_budget=elapsed <= max_seconds,
        raw_firmware_bytes_leaked=PHASE342_RAW_FIRMWARE_BYTES_LEAKED,
    )


# ---------------------------------------------------------------------------
# Check Group A Evaluator (Wave 70 §§1-2: Peaking Display & Audio / Wind Noise)
# ---------------------------------------------------------------------------
def evaluate_p342_check_group_a_peaking_audio_and_wind(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P342_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    focus_mode: str = "MF",
    # Peaking Display (Wave 70 §1)
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "WHITE",
    hdmi_info_display: str = "ON",
    hdmi_raw_output: str = "OFF",
    focus_magnifier_active: bool = False,
    expect_peaking_outputs_over_hdmi: bool = False,
    claimed_peaking_blocks_focus_magnifier: bool = False,
    claimed_peaking_disabled_in_movie_af: bool = False,
    claimed_peaking_wiped_by_camera_reset: bool = False,
    in_body_focus_map_requested: bool = False,
    claimed_fx3_has_in_body_focus_map: bool = False,
    claimed_mc_focus_map_works_over_usb: bool = False,
    fx6_peaking_type_or_freq_requested: bool = False,
    claimed_fx6_has_peaking_type_or_freq: bool = False,
    claimed_fx6_peaking_has_white_not_bw: bool = False,
    # Audio Level Display removal & Wind Noise Reduct. (Wave 70 §2)
    exposed_audio_recording_items: Tuple[str, ...] = P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS,
    audio_recording: str = "ON",
    audio_rec_level: int = P342_AUDIO_REC_LEVEL_DEFAULT,
    audio_out_timing: str = "LIVE",
    wind_noise_reduct: str = "OFF",
    shoe_audio_set: str = "48KHZ_16BIT_2CH",
    mic_35mm_inserted: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_handle_audio: str = "OFF",
    mi_shoe_mic_attached: bool = False,
    dormant_audio_level_display_requested: bool = False,
    claimed_fx3_has_audio_level_display_menu: bool = False,
    claimed_audio_recording_resists_camera_reset: bool = False,
    claimed_audio_out_timing_under_setup_sound_option: bool = False,
    fx3_disable_builtin_limiter_requested: bool = False,
    dormant_wind_noise_auto_requested: bool = False,
    claimed_fx3_wind_noise_has_auto: bool = False,
    expect_wind_noise_applies_to_external_mic: bool = False,
    expect_wind_noise_active_in_sq: bool = False,
    claimed_fx6_handle_has_physical_low_cut_switch: bool = False,
    claimed_fx3_has_fx6_6step_limiter: bool = False,
) -> P342CheckGroupAPeakingAudioWindResult:
    errors: List[str] = []
    warnings: List[str] = []

    if body_model_id != TARGET_MODEL_ID_INT:
        errors.append(
            f"{P342_GA_ERR_MODEL_OR_FW_FLOOR}: expected {TARGET_MODEL_ID_HEX}, got {hex(body_model_id)}"
        )
    if body_fw != TARGET_BODY_FW:
        errors.append(
            f"{P342_GA_ERR_MODEL_OR_FW_FLOOR}: expected FX3 Ver. {TARGET_BODY_FW}, got {body_fw!r}"
        )
    if sony_help_guide_id != P342_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P342_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id must be {P342_SONY_HELP_GUIDE_ID!r}, "
            f"got {sony_help_guide_id!r}"
        )
    if reset_action not in P342_VALID_RESET_ACTIONS:
        errors.append(f"{P342_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action={reset_action!r}")
    if shoot_mode not in P342_VALID_SHOOT_MODES:
        errors.append(f"{P342_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode={shoot_mode!r}")
    if focus_mode not in P342_VALID_FOCUS_MODES:
        errors.append(f"{P342_GA_ERR_MODEL_OR_FW_FLOOR}: invalid focus_mode={focus_mode!r}")

    # Peaking Display checks
    if peaking_display not in P342_VALID_ON_OFF:
        errors.append(
            f"{P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP}: invalid peaking_display={peaking_display!r}"
        )
    if peaking_level not in P342_PEAKING_THREE_LEVELS:
        errors.append(
            f"{P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP}: invalid peaking_level={peaking_level!r}"
        )
    if peaking_color not in P342_PEAKING_FOUR_COLORS:
        errors.append(
            f"{P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP}: invalid peaking_color={peaking_color!r}"
        )
    if hdmi_info_display not in P342_VALID_ON_OFF or hdmi_raw_output not in P342_VALID_ON_OFF:
        errors.append(
            f"{P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP}: invalid HDMI state "
            f"(info={hdmi_info_display!r}, raw={hdmi_raw_output!r})"
        )
    if expect_peaking_outputs_over_hdmi:
        errors.append(
            f"{P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"FX3 [Peaking Display] outputs 0 pixels over HDMI regardless of HDMI Info. Display or RAW Output"
        )
    if claimed_peaking_blocks_focus_magnifier:
        errors.append(
            f"{P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP}: [Peaking Display] coexists with "
            f"[Focus Magnifier] (0 PRM_HAITA exclusions in FX3 appFw.so)"
        )
    if claimed_peaking_disabled_in_movie_af:
        errors.append(
            f"{P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP}: [Peaking Display] remains active in Movie AF "
            f"as well as Still MF/DMF"
        )
    if claimed_peaking_wiped_by_camera_reset:
        errors.append(
            f"{P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP}: all 3 [Peaking Display] items are Reset-immune "
            f"([Camera Settings Reset] = Not available; cleared only by [Initialize])"
        )
    if in_body_focus_map_requested or claimed_fx3_has_in_body_focus_map or claimed_mc_focus_map_works_over_usb:
        errors.append(
            f"{P342_GA_ERR_PEAKING_HDMI_COEXIST_OR_FOCUS_MAP}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"[Focus Map] ({P342_DORMANT_FOCUS_MAP_RESIDS}) is 100% body-dormant (0 hits in ilc/2210); "
            f"available only in wireless Monitor & Control Ver. 2.1.0+ (not over USB)"
        )

    # Debunking FX6 Peaking Type/Freq myth
    if fx6_peaking_type_or_freq_requested or claimed_fx6_has_peaking_type_or_freq:
        errors.append(
            f"{P342_GA_ERR_FX6_PEAKING_TYPE_FREQ_MYTH}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"FX6 appFw.so contains 0 PEAKING_TYPE/PEAKING_FREQ symbols (dormant FS7 UXC "
            f"{P342_FX6_PEAKING_DORMANT_UXC_RESIDS}); FX6 exposes only {P342_FX6_PEAKING_EXACT_THREE_ITEMS}"
        )
    if claimed_fx6_peaking_has_white_not_bw:
        errors.append(
            f"{P342_GA_ERR_FX6_PEAKING_TYPE_FREQ_MYTH}: FX6 Peaking Color exposes "
            f"{P342_FX6_PEAKING_FOUR_COLORS} (BW, not White)"
        )

    # Ver. 2.00+ Audio Level Display removal & Wind Noise Reduct.
    if dormant_audio_level_display_requested or claimed_fx3_has_audio_level_display_menu:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"[Audio Level Display] ({P342_REMOVED_AUDIO_LEVEL_DISPLAY_RESID16_HEX}) was removed in FX3 Ver. 2.00+ "
            f"(auto-shown on DISP/BIG6; 0ch hidden in S&Q)"
        )
    if tuple(exposed_audio_recording_items) != P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: Shooting -> [Audio Recording] must expose "
            f"exact 5 items {P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS}, got {tuple(exposed_audio_recording_items)!r}"
        )
    if audio_recording not in P342_VALID_ON_OFF:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: invalid audio_recording={audio_recording!r}"
        )
    if not (P342_AUDIO_REC_LEVEL_MIN <= audio_rec_level <= P342_AUDIO_REC_LEVEL_MAX):
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: audio_rec_level={audio_rec_level} "
            f"out of range {P342_AUDIO_REC_LEVEL_MIN}..{P342_AUDIO_REC_LEVEL_MAX}"
        )
    if audio_out_timing not in P342_VALID_AUDIO_OUT_TIMINGS:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: invalid audio_out_timing={audio_out_timing!r}"
        )
    if shoe_audio_set not in P342_SHOE_AUDIO_MODES:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: invalid shoe_audio_set={shoe_audio_set!r}"
        )
    if xlr_h1_handle_audio not in P342_VALID_ON_OFF:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: invalid xlr_h1_handle_audio={xlr_h1_handle_audio!r}"
        )
    if wind_noise_reduct == "AUTO" or dormant_wind_noise_auto_requested or claimed_fx3_wind_noise_has_auto:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"FX3 [Wind Noise Reduct.] supports ONLY {P342_WIND_NOISE_REDUCT_EXACT_TWO_MODES} "
            f"(dormant {P342_WIND_NOISE_REDUCT_DORMANT_AUTO_RESID16_HEX} Auto has 0 active UXC menu hits)"
        )
    elif wind_noise_reduct not in P342_WIND_NOISE_REDUCT_EXACT_TWO_MODES:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: invalid wind_noise_reduct={wind_noise_reduct!r}"
        )

    external_mic_active = bool(
        mic_35mm_inserted or (xlr_h1_attached and xlr_h1_handle_audio == "ON") or mi_shoe_mic_attached
    )
    wind_internal_active = (
        wind_noise_reduct == "ON"
        and audio_recording == "ON"
        and shoot_mode != "S_AND_Q"
        and not external_mic_active
    )

    if expect_wind_noise_applies_to_external_mic:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: {P342_WIND_NOISE_REDUCT_LOW_CUT_MSG} "
            f"applies ONLY to built-in stereo mic and is auto-bypassed under 3.5mm/XLR-H1/MI-Shoe mics"
        )
    if expect_wind_noise_active_in_sq:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: [Wind Noise Reduct.] is disabled in S&Q "
            f"(0ch audio)"
        )
    if claimed_audio_recording_resists_camera_reset:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: all 5 [Audio Recording] items are Resettable "
            f"under [Camera Settings Reset]"
        )
    if claimed_audio_out_timing_under_setup_sound_option:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: [Audio Out Timing] lives under "
            f"Shooting -> [Audio Recording], NOT Setup -> [Sound Option]"
        )
    if fx3_disable_builtin_limiter_requested:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"FX3 built-in audio limiter is always active and non-disableable"
        )
    if claimed_fx6_handle_has_physical_low_cut_switch:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: FX6 standard handle has NO physical "
            f"LOW CUT switch (uses menu Audio > Audio Input > CH1..CH4 Wind Filter)"
        )
    if claimed_fx3_has_fx6_6step_limiter:
        errors.append(
            f"{P342_GA_ERR_AUDIO_LEVEL_REMOVAL_OR_WIND_AUTO_MYTH}: FX3 lacks FX6 6-step Limiter Mode "
            f"{P342_FX6_LIMITER_MODE_SIX_STEPS}"
        )

    if peaking_display == "ON" and focus_magnifier_active:
        warnings.append("Peaking Display coexists with Focus Magnifier on local LCD only (0 px on HDMI)")

    return P342CheckGroupAPeakingAudioWindResult(
        group_id=P342_CHECK_GROUP_A_ID,
        passed=len(errors) == 0,
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        fx3_peaking_outputs_to_hdmi=P342_FX3_PEAKING_OUTPUTS_TO_HDMI,
        peaking_coexists_with_focus_magnifier=P342_PEAKING_COEXISTS_WITH_FOCUS_MAGNIFIER,
        fx3_in_body_focus_map_present=P342_FX3_IN_BODY_FOCUS_MAP_PRESENT,
        fx6_peaking_type_freq_hits=P342_FX6_PEAKING_TYPE_FREQ_SYMBOL_HITS,
        fx6_peaking_colors=P342_FX6_PEAKING_FOUR_COLORS,
        fx3_audio_level_display_menu_present=P342_FX3_AUDIO_LEVEL_DISPLAY_MENU_PRESENT,
        exposed_audio_recording_items=tuple(exposed_audio_recording_items),
        audio_recording=audio_recording,
        audio_rec_level=audio_rec_level,
        audio_out_timing=audio_out_timing,
        wind_noise_reduct=wind_noise_reduct,
        fx3_wind_noise_auto_present=P342_FX3_WIND_NOISE_AUTO_PRESENT,
        wind_noise_internal_mic_active=wind_internal_active,
        mic_35mm_inserted=mic_35mm_inserted,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_handle_audio=xlr_h1_handle_audio,
        shoe_audio_set=shoe_audio_set,
        fx6_handle_physical_low_cut_switch=P342_FX6_HANDLE_PHYSICAL_LOW_CUT_SWITCH_PRESENT,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group B Evaluator (Wave 70 §§3-4: USB PD, NP-FZ100 Law, DC-C1, NTSC/PAL)
# ---------------------------------------------------------------------------
def evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
    *,
    # USB Power Supply & DC-C1 (Wave 70 §3)
    usb_power_supply: str = "ON",
    usb_power_terminal: str = P342_USB_POWER_TERMINAL_ALLOWED,
    camera_power_state: str = "ON",
    usb_pd_supply_active: bool = True,
    usb_pd_watts: float = P342_USB_PD_RECOMMENDED_WATTS,
    usb_c_cable_amps: int = 3,
    np_fz100_inserted: bool = True,
    battery_soc_pct: int = 85,
    dc_c1_coupler_attached: bool = False,
    charge_led_active_while_on: bool = False,
    expect_battery_charges_while_camera_on: bool = False,
    claimed_multi_micro_usb_powers_camera: bool = False,
    claimed_fx3_supports_batteryless_usb_pd_boot: bool = False,
    claimed_np_fz100_hot_swap_under_usb_pd: bool = False,
    claimed_usb_power_supply_wiped_by_camera_reset: bool = False,
    fx6_dc_in_volts: float = P342_FX6_DC_IN_NOMINAL_VOLTS,
    fx6_dc_in_hot_replug_during_rec: bool = False,
    claimed_fx6_usb_c_powers_body: bool = False,
    claimed_fx6_lacks_batteryless_dc_in_boot: bool = False,
    # NTSC/PAL Selector & Slot-1 Tier-0 Firewall (Wave 70 §4)
    ntsc_pal_sku: str = "CE",
    video_system: str = "PAL",
    ntsc_pal_switch_requested: bool = False,
    ntsc_pal_reboot_acknowledged: bool = True,
    ntsc_pal_avf_info_write_requested: bool = False,
    ntsc_pal_avf_target_slot: int = 2,
    slot1_format_requested: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_data_sector_writes: int = 0,
    claimed_j1_supports_pal_selector: bool = False,
    expect_non_default_system_lacks_banner: bool = False,
    claimed_xavc_requires_mandatory_card_format: bool = False,
    expect_cross_system_playback_allowed: bool = False,
    claimed_ntsc_pal_wiped_by_camera_reset: bool = False,
    claimed_fx6_shows_running_on_ntsc_pal_banner: bool = False,
    claimed_fx6_thumbnail_shows_all_freq_simultaneously: bool = False,
) -> P342CheckGroupBUsbPdNtscPalSlot1Result:
    errors: List[str] = []
    warnings: List[str] = []

    if usb_power_supply not in P342_VALID_ON_OFF:
        errors.append(
            f"{P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW}: invalid usb_power_supply={usb_power_supply!r}"
        )
    if camera_power_state not in P342_VALID_CAMERA_POWER_STATES:
        errors.append(
            f"{P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW}: invalid camera_power_state={camera_power_state!r}"
        )
    if usb_power_terminal != P342_USB_POWER_TERMINAL_ALLOWED or claimed_multi_micro_usb_powers_camera:
        errors.append(
            f"{P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"[USB Power Supply] is restricted strictly to {P342_USB_POWER_TERMINAL_ALLOWED} "
            f"(Multi/Micro USB unsupported)"
        )
    if not np_fz100_inserted or battery_soc_pct <= 0:
        errors.append(
            f"{P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW}: libUsbBusPower.so VAL_battery_inserted_BATTERY_IS_INSERTED "
            f"failed — charged NP-FZ100 MUST remain inserted (np_fz100_inserted={np_fz100_inserted}, "
            f"soc={battery_soc_pct}%)"
        )
    if usb_pd_supply_active and usb_power_supply == "ON" and camera_power_state == "ON":
        if usb_pd_watts < P342_USB_PD_RECOMMENDED_WATTS:
            errors.append(
                f"{P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW}: camera ON under USB PD requires >= 9V/3A "
                f"({P342_USB_PD_RECOMMENDED_WATTS}W), got {usb_pd_watts}W"
            )
    if camera_power_state == "ON" and (charge_led_active_while_on or expect_battery_charges_while_camera_on):
        errors.append(
            f"{P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW}: FX3 does NOT charge NP-FZ100 while camera is ON "
            f"(amber CHARGE LED stays OFF; charges only when camera is OFF)"
        )
    if claimed_fx3_supports_batteryless_usb_pd_boot or claimed_np_fz100_hot_swap_under_usb_pd:
        errors.append(
            f"{P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"FX3 USB Type-C PD cuts power immediately if NP-FZ100 is absent/removed (no battery-less boot)"
        )
    if claimed_usb_power_supply_wiped_by_camera_reset:
        errors.append(
            f"{P342_GB_ERR_USB_PD_OR_NP_FZ100_LAW}: [USB Power Supply] is Reset-immune "
            f"(cleared only by [Initialize])"
        )

    if dc_c1_coupler_attached and (
        usb_pd_watts < P342_DC_C1_MIN_PD_WATTS or usb_c_cable_amps < P342_DC_C1_MIN_CABLE_AMPS
    ):
        errors.append(
            f"{P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY}: DC-C1 requires >= {P342_DC_C1_MIN_PD_WATTS}W USB PD "
            f"and {P342_DC_C1_MIN_CABLE_AMPS}A rated cable (got {usb_pd_watts}W / {usb_c_cable_amps}A)"
        )
    if not (P342_FX6_DC_IN_MIN_VOLTS <= fx6_dc_in_volts <= P342_FX6_DC_IN_MAX_VOLTS):
        errors.append(
            f"{P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY}: FX6 EIAJ DC IN out of {P342_FX6_DC_IN_MIN_VOLTS}.."
            f"{P342_FX6_DC_IN_MAX_VOLTS}V range: {fx6_dc_in_volts}V"
        )
    if fx6_dc_in_hot_replug_during_rec:
        errors.append(
            f"{P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY}: FX6 forbids hot-replugging 19.5V DC IN during active REC "
            f"(unexpected reboot hazard)"
        )
    if claimed_fx6_usb_c_powers_body or claimed_fx6_lacks_batteryless_dc_in_boot:
        errors.append(
            f"{P342_GB_ERR_DC_C1_OR_FX6_DC_IN_PARITY}: FX6 supports battery-less 19.5V DC IN boot, "
            f"whereas FX6 USB-C does NOT supply body power"
        )

    # NTSC/PAL Selector & Slot-1 Tier-0 firewall
    if ntsc_pal_sku not in P342_VALID_NTSC_PAL_SKUS:
        errors.append(f"{P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO}: invalid ntsc_pal_sku={ntsc_pal_sku!r}")
    if video_system not in P342_VALID_VIDEO_SYSTEMS:
        errors.append(f"{P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO}: invalid video_system={video_system!r}")

    if ntsc_pal_sku == "J1" and (
        video_system == "PAL" or ntsc_pal_switch_requested or claimed_j1_supports_pal_selector
    ):
        errors.append(
            f"{P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"J1 (Japan) SKU is hardware/NVRAM locked to NTSC with [NTSC/PAL Selector] hidden"
        )

    banner = ""
    if ntsc_pal_sku in ("CE", "E33") and video_system == "NTSC":
        banner = P342_RUNNING_ON_NTSC_BANNER
    elif ntsc_pal_sku == "U2" and video_system == "PAL":
        banner = P342_RUNNING_ON_PAL_BANNER

    if expect_non_default_system_lacks_banner:
        errors.append(
            f"{P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO}: non-default system displays mandatory boot banner "
            f"({P342_RUNNING_ON_NTSC_BANNER!r} on CE/E33, {P342_RUNNING_ON_PAL_BANNER!r} on U2)"
        )
    if ntsc_pal_switch_requested and not ntsc_pal_reboot_acknowledged:
        errors.append(
            f"{P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO}: switching [NTSC/PAL Selector] requires mandatory cold reboot"
        )
    if claimed_xavc_requires_mandatory_card_format:
        errors.append(
            f"{P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO}: FX3 Ver. 7.02 pure XAVC (/PRIVATE/M4ROOT/) "
            f"does NOT require formatting card after NTSC/PAL switch (only AVF_INFO Create?/Update?)"
        )
    if expect_cross_system_playback_allowed:
        errors.append(
            f"{P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"cross-system playback is blocked when clips from the other TV system coexist on card"
        )
    if claimed_ntsc_pal_wiped_by_camera_reset:
        errors.append(
            f"{P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO}: [NTSC/PAL Selector] is Reset-immune "
            f"(cleared only by [Initialize])"
        )
    if claimed_fx6_shows_running_on_ntsc_pal_banner or claimed_fx6_thumbnail_shows_all_freq_simultaneously:
        errors.append(
            f"{P342_GB_ERR_NTSC_PAL_SKU_OR_AVF_INFO}: FX6 System Frequency shows NO 'Running on NTSC/PAL' "
            f"boot banner and filters Thumbnail clips by active Frequency"
        )

    slot1_mutated = False
    if slot1_contains_tier0_dump and (
        (ntsc_pal_avf_info_write_requested and ntsc_pal_avf_target_slot == 1)
        or slot1_format_requested
        or slot1_data_sector_writes != 0
    ):
        slot1_mutated = slot1_data_sector_writes != 0
        errors.append(
            f"{P342_GB_ERR_SLOT1_TIER0_VAULT_EROFS}: errno={P342_ERRNO_EROFS} "
            f"Tier-0 Slot-1 firewall blocked AVF_INFO Create?/Update? or Format write onto Slot 1 "
            f"(writes={slot1_data_sector_writes})"
        )

    if banner:
        warnings.append(f"Non-default TV system active ({ntsc_pal_sku} -> {video_system}): banner={banner!r}")

    return P342CheckGroupBUsbPdNtscPalSlot1Result(
        group_id=P342_CHECK_GROUP_B_ID,
        passed=len(errors) == 0,
        usb_power_supply=usb_power_supply,
        usb_power_terminal=usb_power_terminal,
        camera_power_state=camera_power_state,
        usb_pd_watts=usb_pd_watts,
        usb_c_cable_amps=usb_c_cable_amps,
        np_fz100_inserted=np_fz100_inserted,
        battery_soc_pct=battery_soc_pct,
        dc_c1_coupler_attached=dc_c1_coupler_attached,
        fx3_charges_battery_while_on=P342_FX3_CHARGES_BATTERY_WHILE_ON,
        fx3_supports_batteryless_usb_pd_boot=P342_FX3_SUPPORTS_BATTERYLESS_USB_PD_BOOT,
        fx6_dc_in_nominal_volts=fx6_dc_in_volts,
        fx6_batteryless_dc_in_boot_supported=P342_FX6_BATTERYLESS_DC_IN_BOOT_SUPPORTED,
        ntsc_pal_sku=ntsc_pal_sku,
        video_system=video_system,
        ntsc_pal_boot_banner=banner,
        xavc_requires_mandatory_format=P342_XAVC_REQUIRES_MANDATORY_CARD_FORMAT,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_tier0_vault_mutated=slot1_mutated,
        slot1_data_sector_writes=slot1_data_sector_writes,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group C Evaluator (Wave 71 §§1-2: Dormant Anti-Dust/Shutter Pwr OFF & Focus Assistant)
# ---------------------------------------------------------------------------
def evaluate_p342_check_group_c_antidust_and_focus_assistant(
    *,
    shoot_mode: str = "MOVIE",
    apsc_s35_shooting: str = "OFF",
    battery_soc_pct: int = 85,
    # Dormant Anti-Dust / Shutter When Pwr OFF (Wave 71 §1)
    dormant_anti_dust_function_requested: bool = False,
    dormant_shutter_when_pwr_off_requested: bool = False,
    claimed_fx3_shutter_when_pwr_off_present: bool = False,
    claimed_fx3_shutter_closes_on_power_off: bool = False,
    sensor_cleaning_requested: bool = False,
    sensor_cleaning_power_off_completed: bool = True,
    claimed_fx6_has_shutter_when_pwr_off_or_ibis_cleaning: bool = False,
    claimed_fx3_has_e_nd_or_apr: bool = False,
    # Focus Assistant (Wave 71 §2)
    exposed_focus_assistant_items: Tuple[str, ...] = P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS,
    focus_magnif_time: str = "NO_LIMIT",
    initial_focus_mag_x: float = 1.0,
    requested_focus_mag_x: float = 1.0,
    af_in_focus_mag: str = "ON",
    auto_magnifier_in_mf: str = "ON",
    dormant_high_mp_focus_mag_scale_requested: bool = False,
    expect_af_in_focus_mag_or_auto_mag_in_movie: bool = False,
    claimed_movie_rec_cancels_focus_mag: bool = False,
    expect_focus_mag_crops_hdmi_or_internal_rec: bool = False,
    claimed_focus_assistant_wiped_by_camera_reset: bool = False,
    claimed_fx6_hdmi_focus_mag_is_3x_6x: bool = False,
    claimed_fx6_vf_focus_mag_is_2_1x_4_1x: bool = False,
) -> P342CheckGroupCAntiDustFocusAssistantResult:
    errors: List[str] = []
    warnings: List[str] = []

    if shoot_mode not in P342_VALID_SHOOT_MODES:
        errors.append(f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: invalid shoot_mode={shoot_mode!r}")
    if apsc_s35_shooting not in P342_VALID_ON_OFF:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: invalid apsc_s35_shooting={apsc_s35_shooting!r}"
        )

    # Anti-Dust / Shutter When Pwr OFF myth-bust
    if (
        dormant_anti_dust_function_requested
        or dormant_shutter_when_pwr_off_requested
        or claimed_fx3_shutter_when_pwr_off_present
    ):
        errors.append(
            f"{P342_GC_ERR_DORMANT_ANTIDUST_OR_SHUTTER_PWROFF}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"[Anti-Dust Function] ({P342_DORMANT_ANTI_DUST_FUNCTION_RESID16_HEX}) / [Shutter When Pwr OFF] "
            f"({P342_DORMANT_SHUTTER_WHEN_PWR_OFF_RESID16_HEX}, {P342_SHUTTER_BARRIER_BKID}) are 100% dormant "
            f"on FX3 (0 hits in ilc/2210, masked by {P342_ALCIN_UUD_MASK_ENUM})"
        )
    if claimed_fx3_shutter_closes_on_power_off:
        errors.append(
            f"{P342_GC_ERR_DORMANT_ANTIDUST_OR_SHUTTER_PWROFF}: FX3 mechanical focal-plane shutter "
            f"always parks {P342_FX3_POWER_OFF_SHUTTER_PARK_STATE} on power-off"
        )
    if sensor_cleaning_requested:
        if battery_soc_pct < P342_SENSOR_CLEANING_MIN_BATTERY_PCT:
            errors.append(
                f"{P342_GC_ERR_SENSOR_CLEANING_OR_FX6_E_ND_APR}: [Sensor Cleaning] "
                f"({P342_SENSOR_CLEANING_RESID16_HEX}) requires >= {P342_SENSOR_CLEANING_MIN_BATTERY_PCT}% "
                f"battery (got {battery_soc_pct}%)"
            )
        if not sensor_cleaning_power_off_completed:
            errors.append(
                f"{P342_GC_ERR_SENSOR_CLEANING_OR_FX6_E_ND_APR}: [Sensor Cleaning] requires mandatory "
                f"physical power OFF after IBIS ultrasonic shake"
            )
    if claimed_fx6_has_shutter_when_pwr_off_or_ibis_cleaning or claimed_fx3_has_e_nd_or_apr:
        errors.append(
            f"{P342_GC_ERR_SENSOR_CLEANING_OR_FX6_E_ND_APR}: FX6 lacks IBIS/Sensor Cleaning & "
            f"Shutter When Pwr OFF (uses sealed e-ND {P342_FX6_E_ND_STEPS} + Technical > APR), while FX3 lacks e-ND/APR"
        )

    # Focus Assistant checks
    if tuple(exposed_focus_assistant_items) != P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: [Focus Assistant] must expose exact 5 items "
            f"{P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS}, got {tuple(exposed_focus_assistant_items)!r}"
        )
    if focus_magnif_time not in P342_VALID_FOCUS_MAGNIF_TIMES:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: invalid focus_magnif_time={focus_magnif_time!r}"
        )
    if af_in_focus_mag not in P342_VALID_ON_OFF or auto_magnifier_in_mf not in P342_VALID_ON_OFF:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: invalid Focus Assistant toggle "
            f"(af={af_in_focus_mag!r}, auto_mf={auto_magnifier_in_mf!r})"
        )

    if shoot_mode == "PHOTO":
        if apsc_s35_shooting == "ON":
            valid_initial = P342_STILL_APSC_INITIAL_MAG_SCALES
            valid_cycle = P342_STILL_APSC_MAG_CYCLE_SCALES
            scale_label = "Still APS-C/S35"
        else:
            valid_initial = P342_STILL_FF_INITIAL_MAG_SCALES
            valid_cycle = P342_STILL_FF_MAG_CYCLE_SCALES
            scale_label = "Still FF"
    else:
        valid_initial = P342_MOVIE_MAG_CYCLE_SCALES
        valid_cycle = P342_MOVIE_MAG_CYCLE_SCALES
        scale_label = "Movie/S&Q"

    if initial_focus_mag_x not in valid_initial:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: invalid {scale_label} initial_focus_mag_x="
            f"{initial_focus_mag_x} (allowed: {valid_initial})"
        )
    if requested_focus_mag_x not in valid_cycle or dormant_high_mp_focus_mag_scale_requested:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"invalid {scale_label} requested_focus_mag_x={requested_focus_mag_x} (allowed: {valid_cycle}; "
            f"high-MP scales {P342_DORMANT_HIGH_MP_MAG_SCALES} dormant)"
        )
    if expect_af_in_focus_mag_or_auto_mag_in_movie:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: [AF in Focus Mag.] & [Auto Magnifier in MF] "
            f"are strictly Still-only (disabled in Movie/S&Q)"
        )
    if claimed_movie_rec_cancels_focus_mag:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: FX3 [Focus Magnifier] persists across MOVIE REC "
            f"unless 2s/5s timer expires (zero magnif x movie_rec mutex)"
        )
    if expect_focus_mag_crops_hdmi_or_internal_rec:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_SCALES_OR_HDMI}: [Focus Magnifier] never magnifies Clean-HDMI or "
            f"internal recorded frames"
        )
    if claimed_focus_assistant_wiped_by_camera_reset:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_RESET_OR_FX6_PARITY}: [Focus Magnif. Time], [Initial Focus Mag.], "
            f"[AF in Focus Mag.], and [Auto Magnifier in MF] are all Reset-immune (Ver. 2.00+)"
        )
    if claimed_fx6_hdmi_focus_mag_is_3x_6x or claimed_fx6_vf_focus_mag_is_2_1x_4_1x:
        errors.append(
            f"{P342_GC_ERR_FOCUS_ASSISTANT_RESET_OR_FX6_PARITY}: FX6 uses VF x3/x6 and Ver. 6.0+ HDMI x2/x4 "
            f"(not FX3 x1.0->x2.1->x4.1)"
        )

    return P342CheckGroupCAntiDustFocusAssistantResult(
        group_id=P342_CHECK_GROUP_C_ID,
        passed=len(errors) == 0,
        fx3_shutter_when_pwr_off_present=P342_FX3_SHUTTER_WHEN_PWR_OFF_PRESENT,
        fx3_ilc2210_shutter_pwroff_hits=P342_FX3_ILC2210_SHUTTER_PWROFF_HITS,
        fx3_power_off_shutter_park_state=P342_FX3_POWER_OFF_SHUTTER_PARK_STATE,
        alcin_uud_mask_enum=P342_ALCIN_UUD_MASK_ENUM,
        sensor_cleaning_requested=sensor_cleaning_requested,
        sensor_cleaning_min_battery_pct=P342_SENSOR_CLEANING_MIN_BATTERY_PCT,
        battery_soc_pct=battery_soc_pct,
        fx6_shutter_when_pwr_off_hits=P342_FX6_SHUTTER_WHEN_PWR_OFF_HITS,
        fx6_sensor_cleaning_present=P342_FX6_SENSOR_CLEANING_PRESENT,
        shoot_mode=shoot_mode,
        apsc_s35_shooting=apsc_s35_shooting,
        focus_magnif_time=focus_magnif_time,
        initial_focus_mag_x=initial_focus_mag_x,
        requested_focus_mag_x=requested_focus_mag_x,
        af_in_focus_mag=af_in_focus_mag,
        auto_magnifier_in_mf=auto_magnifier_in_mf,
        focus_mag_persists_during_movie_rec=P342_FOCUS_MAG_PERSISTS_DURING_MOVIE_REC,
        focus_mag_outputs_to_hdmi=P342_FOCUS_MAG_OUTPUTS_TO_HDMI,
        fx6_vf_focus_mag_scales=P342_FX6_VF_FOCUS_MAG_SCALES,
        fx6_hdmi_focus_mag_scales=P342_FX6_HDMI_FOCUS_MAG_SCALES,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# Check Group D Evaluator (Wave 71 §§3-4 + Tier-0 H0 == H3)
# ---------------------------------------------------------------------------
def _verify_single_receipt(
    raw: Optional[bytes],
    *,
    label: str,
) -> Tuple[Optional[Dict[str, Any]], List[str]]:
    errs: List[str] = []
    if raw is None:
        errs.append(f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing {label}")
        return None, errs
    if len(raw) != SD_RECEIPT_BYTES:
        errs.append(
            f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} length={len(raw)} != {SD_RECEIPT_BYTES}"
        )
        return None, errs
    try:
        parsed = parse_sd_backup_receipt_bytes(raw)
        if not parsed.valid:
            errs.append(
                f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} invalid ({'; '.join(parsed.errors)})"
            )
            return None, errs
        if _is_trivial_hex64(str(parsed.manifest_sha256)):
            errs.append(
                f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} trivial manifest_sha256"
            )
            return None, errs
        return asdict(parsed), errs
    except Exception as exc:
        errs.append(
            f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: {label} invalid FX3RCPT1 ({exc})"
        )
        return None, errs


def evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
    *,
    simulate_bench_dry_run: bool = False,
    reset_action: str = "NONE",
    log_shooting_mode: str = "OFF",
    # Exposure Std. Adjust (Wave 71 §3)
    exp_std_adjust_metering_mode: str = "MULTI",
    exp_std_adjust_sixths: int = 0,
    exp_std_nonzero_acknowledged: bool = False,
    dormant_1_8_ev_step_requested: bool = False,
    expect_exp_std_adjust_modifies_exif_bias: bool = False,
    expect_exp_std_changes_cine_ei_iso: bool = False,
    claimed_exp_std_adjust_wiped_by_camera_reset: bool = False,
    claimed_exp_std_adjust_resets_exposure_comp: bool = False,
    fx6_ae_level_ev: float = 0.0,
    claimed_fx6_ae_level_limited_to_2ev: bool = False,
    # Wired USB-LAN/Tethering & Slot-1 Firewall (Wave 71 §4)
    usb_connection_mode: str = "SEL_WHEN_CONNECT",
    usb_lun_setting: str = "MULTI",
    usb_lan_tethering: str = "OFF",
    usb_lan_cnct_launch: str = "OFF",
    usb_lan_service: str = "NONE",
    airplane_mode: str = "ON",
    dual_usb_typec_and_multi_simultaneous: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_host_usb_write_requested: bool = False,
    slot1_data_sector_writes: int = 0,
    claimed_airplane_mode_blocks_usb_lan: bool = False,
    claimed_creators_app_allows_guided_live_over_usb: bool = False,
    claimed_usb_streaming_uvc_active_on_fx3: bool = False,
    claimed_reset_network_preserves_airplane_mode: bool = False,
    claimed_camera_reset_wipes_usb_tethering: bool = False,
    claimed_fx3_links_cusbgadgetiap: bool = False,
    claimed_fx6_lacks_cusbgadgetiap: bool = False,
    # Tier-0 Dual-Media & Fail-Closed Redlines
    emmc_write_count: int = 0,
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
) -> P342CheckGroupDExpStdUsbLanTier0Result:
    errors: List[str] = []
    warnings: List[str] = []

    if log_shooting_mode not in P342_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP}: invalid log_shooting_mode={log_shooting_mode!r}"
        )

    # Exposure Std. Adjust
    if exp_std_adjust_metering_mode not in P342_EXP_STD_ADJ_FIVE_METERING_MODES:
        errors.append(
            f"{P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP}: invalid metering mode="
            f"{exp_std_adjust_metering_mode!r} (expected one of {P342_EXP_STD_ADJ_FIVE_METERING_MODES})"
        )
    if not (P342_EXP_STD_ADJ_MIN_SIXTHS <= exp_std_adjust_sixths <= P342_EXP_STD_ADJ_MAX_SIXTHS):
        errors.append(
            f"{P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP}: exp_std_adjust_sixths={exp_std_adjust_sixths} "
            f"out of range {P342_EXP_STD_ADJ_MIN_SIXTHS}..{P342_EXP_STD_ADJ_MAX_SIXTHS} (1/6 EV steps)"
        )
    if exp_std_adjust_sixths != 0 and not exp_std_nonzero_acknowledged:
        errors.append(
            f"{P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP}: non-zero [Exposure Std. Adjust] "
            f"({exp_std_adjust_sixths}/6 EV on {exp_std_adjust_metering_mode}) is a Reset-immune operator "
            f"calibration trap (shifts M.M. zero with 0 EV EXIF ExposureBiasValue); reset to 0 or acknowledge"
        )
    if dormant_1_8_ev_step_requested:
        errors.append(
            f"{P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"1/8 EV Exposure Std. Adjust step is dormant; FX3 uses {P342_EXP_STD_ADJ_STEP_ENUM}"
        )
    if expect_exp_std_adjust_modifies_exif_bias:
        errors.append(
            f"{P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP}: [Exposure Std. Adjust] NEVER modifies EXIF "
            f"ExposureBiasValue (remains 0 EV)"
        )
    if expect_exp_std_changes_cine_ei_iso:
        errors.append(
            f"{P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP}: under Cine EI / Cine EI Quick, Base ISO is locked "
            f"and [Exposure Std. Adjust] shifts only M.M. meter display"
        )
    if claimed_exp_std_adjust_wiped_by_camera_reset or claimed_exp_std_adjust_resets_exposure_comp:
        errors.append(
            f"{P342_GD_ERR_EXP_STD_ADJUST_CALIBRATION_TRAP}: [Exposure Std. Adjust] is Reset-immune "
            f"([Camera Settings Reset] = Not available) and decoupled from [Exposure Comp.]"
        )

    # FX6 Auto Exposure > Level (-3.0..+3.0 in 0.25 step, 25 steps)
    quarter_steps = round(fx6_ae_level_ev * 4.0)
    if (
        fx6_ae_level_ev < P342_FX6_AE_LEVEL_MIN_EV
        or fx6_ae_level_ev > P342_FX6_AE_LEVEL_MAX_EV
        or abs(fx6_ae_level_ev - quarter_steps / 4.0) > 1e-9
    ):
        errors.append(
            f"{P342_GD_ERR_FX6_AE_LEVEL_3EV_MYTH}: fx6_ae_level_ev={fx6_ae_level_ev} out of "
            f"{P342_FX6_AE_LEVEL_MIN_EV}..+{P342_FX6_AE_LEVEL_MAX_EV} EV (0.25 step, 25 steps)"
        )
    if claimed_fx6_ae_level_limited_to_2ev:
        errors.append(
            f"{P342_GD_ERR_FX6_AE_LEVEL_3EV_MYTH}: FX6 Auto Exposure > Level spans -3.0..+3.0 EV "
            f"(0.25 step, 25 steps: LEVEL_MINUS_3_0..LEVEL_3_0), NOT +-2.0 EV"
        )

    # Wired USB-LAN/Tethering & Slot-1 Firewall
    if usb_connection_mode not in P342_USB_CONN_VALID_MODES:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: invalid usb_connection_mode="
            f"{usb_connection_mode!r}"
        )
    if usb_connection_mode == "USB_STREAMING" or claimed_usb_streaming_uvc_active_on_fx3:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: errno={P342_ERRNO_EOPNOTSUPP} "
            f"FX3 Ver. 7.02 USB Streaming (UVC) is dormant (NOUVC)"
        )
    if usb_lun_setting not in P342_USB_LUN_VALID_MODES:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: invalid usb_lun_setting={usb_lun_setting!r}"
        )
    if usb_lan_tethering not in P342_VALID_ON_OFF or usb_lan_cnct_launch not in P342_VALID_ON_OFF:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: invalid USB-LAN flags "
            f"(tethering={usb_lan_tethering!r}, cnct_launch={usb_lan_cnct_launch!r})"
        )
    if usb_lan_service not in P342_USB_LAN_VALID_SERVICES:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: invalid usb_lan_service={usb_lan_service!r}"
        )
    if airplane_mode != "ON":
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: [Airplane Mode] must remain ON "
            f"(Zero-RF bench firewall; note [Reset Network Set.] resets Airplane Mode to OFF -> must re-arm)"
        )
    if reset_action == "RESET_NETWORK_SET":
        warnings.append(
            "RESET_NETWORK_SET triggers auto-reboot and resets [Airplane Mode] to OFF -> bench must re-arm ON"
        )
    if dual_usb_typec_and_multi_simultaneous:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: errno={P342_ERRNO_EBUSY} "
            f"simultaneous USB Type-C and Multi/Micro USB communication is forbidden"
        )
    if claimed_airplane_mode_blocks_usb_lan:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: wired [USB-LAN/Tethering] operates "
            f"normally for RTMP/RTMPS/SRT/FTP even when [Airplane Mode] = ON (Zero-RF)"
        )
    if claimed_creators_app_allows_guided_live_over_usb:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: Creators' App guided live streaming "
            f"requires Bluetooth + Wi-Fi and rejects wired USB direct"
        )
    if claimed_reset_network_preserves_airplane_mode:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: [Reset Network Set.] auto-reboots and "
            f"clears [Airplane Mode] back to OFF (unlike [Camera Settings Reset])"
        )
    if claimed_camera_reset_wipes_usb_tethering:
        errors.append(
            f"{P342_GD_ERR_USBLAN_TETHERING_AIRPLANE_OR_PORT_MUTEX}: [Camera Settings Reset] preserves "
            f"[USB Connection Mode] and [USB-LAN/Tethering]"
        )

    # Slot-1 USB write firewall & FX3 vs FX6 CUsbGadgetIAP
    if slot1_contains_tier0_dump and (slot1_host_usb_write_requested or slot1_data_sector_writes != 0):
        errors.append(
            f"{P342_GD_ERR_SLOT1_USB_WRITE_EROFS_OR_FX6_IAP}: errno={P342_ERRNO_EROFS} "
            f"Tier-0 Slot-1 firewall + {P342_USBGMSCIF_READONLY_SYMBOL} blocked MTP/MSC host writes to Slot 1 "
            f"(writes={slot1_data_sector_writes})"
        )
    if claimed_fx3_links_cusbgadgetiap or claimed_fx6_lacks_cusbgadgetiap:
        errors.append(
            f"{P342_GD_ERR_SLOT1_USB_WRITE_EROFS_OR_FX6_IAP}: FX3 libInfraUsbCmn.so stripped CUsbGadgetIAP "
            f"(0 hits), whereas FX6 actively links usbg_iap.ko / CUsbGadgetIAP"
        )

    # Fail-closed hardware/write/packet redlines
    if (
        emmc_write_count != 0
        or e_nd_actuator_tx_count != 0
        or wireless_rf_packets_emitted != 0
        or usb_packets_transmitted != 0
        or simulated_passive_tx_bytes != 0
        or claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P342_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: fail-closed hardware/write/packet redline violated"
        )

    # Dual-media Tier-0 FX3RCPT1 & 16/16 H0 == H3
    tier0_verified = False
    receipt_mode = "NONE_AWAITING_PHYSICAL_TIER0"
    h0_eq_h3 = 0

    if simulate_bench_dry_run:
        receipt_mode = "SIMULATED_BENCH_DRY_RUN"
        sim = build_simulated_phase342_tier0_receipts(
            body_serial=body_serial or "FX3BENCH70200342",
            emmc_cid=emmc_cid or "11010030303847333000a1b2c3d40342",
        )
        drifted = max(0, int(simulated_h0_h3_drifted_surfaces))
        h0_eq_h3 = max(0, P342_STORAGE_SURFACE_COUNT - drifted)
        if h0_eq_h3 != P342_STORAGE_SURFACE_COUNT:
            errors.append(
                f"{P342_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: simulated H0 == H3 parity drift "
                f"({h0_eq_h3}/{P342_STORAGE_SURFACE_COUNT})"
            )
        else:
            tier0_verified = True
        _ = sim
    elif receipt_a_bytes is not None or receipt_b_bytes is not None or receipt_a_path is not None or receipt_b_path is not None:
        receipt_mode = "PHYSICAL_DUAL_MEDIA_RECEIPT"
        raw_a = receipt_a_bytes
        raw_b = receipt_b_bytes
        st_dev_a = st_dev_a_override
        st_dev_b = st_dev_b_override
        if raw_a is None and receipt_a_path is not None:
            if not receipt_a_path.is_file():
                errors.append(
                    f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a not found ({receipt_a_path})"
                )
            else:
                st_dev_a = st_dev_a if st_dev_a is not None else os.stat(receipt_a_path).st_dev
                raw_a = receipt_a_path.read_bytes()
        if raw_b is None and receipt_b_path is not None:
            if not receipt_b_path.is_file():
                errors.append(
                    f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b not found ({receipt_b_path})"
                )
            else:
                st_dev_b = st_dev_b if st_dev_b is not None else os.stat(receipt_b_path).st_dev
                raw_b = receipt_b_path.read_bytes()

        if body_serial is not None and (
            not BODY_SERIAL_RE.match(body_serial)
            or body_serial in FORBIDDEN_TRIVIAL_SERIALS
            or len(set(body_serial)) <= 1
        ):
            errors.append(
                f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid or trivial body_serial={body_serial!r}"
            )
        if emmc_cid is not None and (
            not HEX32_CID_RE.match(emmc_cid) or emmc_cid.lower() in FORBIDDEN_TRIVIAL_CIDS
        ):
            errors.append(
                f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid or trivial emmc_cid={emmc_cid!r}"
            )

        parsed_a, errs_a = _verify_single_receipt(raw_a, label="receipt_a")
        parsed_b, errs_b = _verify_single_receipt(raw_b, label="receipt_b")
        errors.extend(errs_a)
        errors.extend(errs_b)

        if raw_a is not None and raw_b is not None and raw_a != raw_b:
            errors.append(
                f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a != receipt_b byte mismatch"
            )
        if st_dev_a is None or st_dev_b is None or st_dev_a == st_dev_b:
            errors.append(
                f"{P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-media receipts must reside on "
                f"distinct physical devices (st_dev_a={st_dev_a}, st_dev_b={st_dev_b})"
            )

        if h0_baselines_a is None or h0_baselines_b is None or h3_baselines is None:
            if parsed_a is not None and parsed_b is not None and not errs_a and not errs_b:
                eff_serial = body_serial or "FX3BENCH70200342"
                eff_cid = emmc_cid or "11010030303847333000a1b2c3d40342"
                auto_h0 = build_default_h0_baselines(body_serial=eff_serial, emmc_cid=eff_cid)
                h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else dict(auto_h0)
                h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else dict(auto_h0)
                h3_map = dict(h3_baselines) if h3_baselines is not None else dict(auto_h0)
            else:
                h0_a, h0_b, h3_map = {}, {}, {}
        else:
            h0_a = dict(h0_baselines_a)
            h0_b = dict(h0_baselines_b)
            h3_map = dict(h3_baselines)

        if not h0_a or not h0_b or not h3_map:
            h0_eq_h3 = 0
        else:
            key_mismatches = sum(
                1
                for key in REQUIRED_H0_BASELINE_KEYS
                if _is_trivial_hex64(h0_a.get(key, ""))
                or h0_a.get(key, "").lower() != h0_b.get(key, "").lower()
                or h0_a.get(key, "").lower() != h3_map.get(key, "").lower()
            )
            surface_mismatches = sum(
                1
                for surf in SIXTEEN_STORAGE_SURFACES
                if h0_a.get(surf) != h0_b.get(surf) or h0_a.get(surf) != h3_map.get(surf)
            )
            extra_keys = set(h0_a.keys()) | set(h0_b.keys()) | set(h3_map.keys())
            extra_mismatches = sum(
                1
                for k in extra_keys
                if (k in h0_a) != (k in h3_map)
                or (k in h0_a) != (k in h0_b)
                or str(h0_a.get(k, "")).lower() != str(h3_map.get(k, "")).lower()
                or str(h0_a.get(k, "")).lower() != str(h0_b.get(k, "")).lower()
            )
            drifted = max(
                0,
                int(simulated_h0_h3_drifted_surfaces),
                key_mismatches,
                surface_mismatches,
                extra_mismatches,
            )
            h0_eq_h3 = max(0, P342_STORAGE_SURFACE_COUNT - drifted)
        if h0_eq_h3 != P342_STORAGE_SURFACE_COUNT:
            errors.append(
                f"{P342_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 surface parity failed "
                f"({h0_eq_h3}/{P342_STORAGE_SURFACE_COUNT})"
            )

        if not any(
            e.startswith(P342_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID)
            or e.startswith(P342_GD_ERR_H0_H3_IMMUTABILITY_DRIFT)
            for e in errors
        ):
            tier0_verified = True
    else:
        if simulated_h0_h3_drifted_surfaces > 0:
            errors.append(
                f"{P342_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: simulated H0/H3 drift ({simulated_h0_h3_drifted_surfaces} surfaces)"
            )

    return P342CheckGroupDExpStdUsbLanTier0Result(
        group_id=P342_CHECK_GROUP_D_ID,
        passed=len(errors) == 0,
        exp_std_adjust_metering_mode=exp_std_adjust_metering_mode,
        exp_std_adjust_sixths=exp_std_adjust_sixths,
        exp_std_adjust_ev=round(exp_std_adjust_sixths / 6.0, 4),
        exp_std_adjust_reset_immune=P342_EXP_STD_ADJ_RESET_IMMUNE,
        exp_std_adjust_modifies_exif_bias=P342_EXP_STD_ADJ_MODIFIES_EXIF_BIAS,
        fx6_ae_level_ev=fx6_ae_level_ev,
        fx6_ae_level_min_ev=P342_FX6_AE_LEVEL_MIN_EV,
        fx6_ae_level_max_ev=P342_FX6_AE_LEVEL_MAX_EV,
        fx6_ae_level_step_ev=P342_FX6_AE_LEVEL_STEP_EV,
        usb_connection_mode=usb_connection_mode,
        usb_lun_setting=usb_lun_setting,
        usb_lan_tethering=usb_lan_tethering,
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        usb_lan_service=usb_lan_service,
        airplane_mode=airplane_mode,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        fx3_cusb_gadget_iap_hits=P342_FX3_CUSB_GADGET_IAP_HITS,
        fx6_cusb_gadget_iap_present=P342_FX6_CUSB_GADGET_IAP_PRESENT,
        usbgmscif_readonly_enforced=True,
        slot1_data_sector_writes=slot1_data_sector_writes,
        tier0_receipt_verified=tier0_verified,
        receipt_mode=receipt_mode,
        h0_equals_h3_count=h0_eq_h3,
        h0_h3_surface_count=P342_STORAGE_SURFACE_COUNT,
        emmc_write_count=emmc_write_count,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


def build_simulated_phase342_tier0_receipts(
    *,
    body_serial: str = "FX3BENCH70200342",
    emmc_cid: str = "11010030303847333000a1b2c3d40342",
) -> Dict[str, Any]:
    """Build synthetic deterministic dual-media H0/H3 baseline maps + 528-byte FX3RCPT1 receipts."""
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE342_TIER0:{TARGET_BODY_FW}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE342_MANIFEST:{body_serial}:{TARGET_BODY_FW}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    raw_receipt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    assert len(raw_receipt) == SD_RECEIPT_BYTES
    base = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return {
        "body_serial": body_serial,
        "emmc_cid": emmc_cid,
        "receipt_a_bytes": raw_receipt,
        "receipt_b_bytes": bytes(raw_receipt),
        "st_dev_a": 1001,
        "st_dev_b": 1002,
        "h0_baselines_a": dict(base),
        "h0_baselines_b": dict(base),
        "h3_baselines": dict(base),
    }


# ---------------------------------------------------------------------------
# Master Preflight Orchestrator, Verifier & Markdown Renderer
# ---------------------------------------------------------------------------
def evaluate_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    force_clean_room: Optional[bool] = None,
    work_root: Optional[Path] = None,
    fx6_lib_dir: Optional[Path] = None,
    fx3_modules_dir: Optional[Path] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P342_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    focus_mode: str = "MF",
    log_shooting_mode: str = "OFF",
    # Group A (Wave 70 §§1-2)
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "WHITE",
    hdmi_info_display: str = "ON",
    hdmi_raw_output: str = "OFF",
    focus_magnifier_active: bool = False,
    expect_peaking_outputs_over_hdmi: bool = False,
    claimed_peaking_blocks_focus_magnifier: bool = False,
    claimed_peaking_disabled_in_movie_af: bool = False,
    claimed_peaking_wiped_by_camera_reset: bool = False,
    in_body_focus_map_requested: bool = False,
    claimed_fx3_has_in_body_focus_map: bool = False,
    claimed_mc_focus_map_works_over_usb: bool = False,
    fx6_peaking_type_or_freq_requested: bool = False,
    claimed_fx6_has_peaking_type_or_freq: bool = False,
    claimed_fx6_peaking_has_white_not_bw: bool = False,
    exposed_audio_recording_items: Tuple[str, ...] = P342_AUDIO_RECORDING_EXACT_FIVE_ITEMS,
    audio_recording: str = "ON",
    audio_rec_level: int = P342_AUDIO_REC_LEVEL_DEFAULT,
    audio_out_timing: str = "LIVE",
    wind_noise_reduct: str = "OFF",
    shoe_audio_set: str = "48KHZ_16BIT_2CH",
    mic_35mm_inserted: bool = False,
    xlr_h1_attached: bool = True,
    xlr_h1_handle_audio: str = "OFF",
    mi_shoe_mic_attached: bool = False,
    dormant_audio_level_display_requested: bool = False,
    claimed_fx3_has_audio_level_display_menu: bool = False,
    claimed_audio_recording_resists_camera_reset: bool = False,
    claimed_audio_out_timing_under_setup_sound_option: bool = False,
    fx3_disable_builtin_limiter_requested: bool = False,
    dormant_wind_noise_auto_requested: bool = False,
    claimed_fx3_wind_noise_has_auto: bool = False,
    expect_wind_noise_applies_to_external_mic: bool = False,
    expect_wind_noise_active_in_sq: bool = False,
    claimed_fx6_handle_has_physical_low_cut_switch: bool = False,
    claimed_fx3_has_fx6_6step_limiter: bool = False,
    # Group B (Wave 70 §§3-4)
    usb_power_supply: str = "ON",
    usb_power_terminal: str = P342_USB_POWER_TERMINAL_ALLOWED,
    camera_power_state: str = "ON",
    usb_pd_supply_active: bool = True,
    usb_pd_watts: float = P342_USB_PD_RECOMMENDED_WATTS,
    usb_c_cable_amps: int = 3,
    np_fz100_inserted: bool = True,
    battery_soc_pct: int = 85,
    dc_c1_coupler_attached: bool = False,
    charge_led_active_while_on: bool = False,
    expect_battery_charges_while_camera_on: bool = False,
    claimed_multi_micro_usb_powers_camera: bool = False,
    claimed_fx3_supports_batteryless_usb_pd_boot: bool = False,
    claimed_np_fz100_hot_swap_under_usb_pd: bool = False,
    claimed_usb_power_supply_wiped_by_camera_reset: bool = False,
    fx6_dc_in_volts: float = P342_FX6_DC_IN_NOMINAL_VOLTS,
    fx6_dc_in_hot_replug_during_rec: bool = False,
    claimed_fx6_usb_c_powers_body: bool = False,
    claimed_fx6_lacks_batteryless_dc_in_boot: bool = False,
    ntsc_pal_sku: str = "CE",
    video_system: str = "PAL",
    ntsc_pal_switch_requested: bool = False,
    ntsc_pal_reboot_acknowledged: bool = True,
    ntsc_pal_avf_info_write_requested: bool = False,
    ntsc_pal_avf_target_slot: int = 2,
    slot1_format_requested: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_data_sector_writes: int = 0,
    claimed_j1_supports_pal_selector: bool = False,
    expect_non_default_system_lacks_banner: bool = False,
    claimed_xavc_requires_mandatory_card_format: bool = False,
    expect_cross_system_playback_allowed: bool = False,
    claimed_ntsc_pal_wiped_by_camera_reset: bool = False,
    claimed_fx6_shows_running_on_ntsc_pal_banner: bool = False,
    claimed_fx6_thumbnail_shows_all_freq_simultaneously: bool = False,
    # Group C (Wave 71 §§1-2)
    apsc_s35_shooting: str = "OFF",
    dormant_anti_dust_function_requested: bool = False,
    dormant_shutter_when_pwr_off_requested: bool = False,
    claimed_fx3_shutter_when_pwr_off_present: bool = False,
    claimed_fx3_shutter_closes_on_power_off: bool = False,
    sensor_cleaning_requested: bool = False,
    sensor_cleaning_power_off_completed: bool = True,
    claimed_fx6_has_shutter_when_pwr_off_or_ibis_cleaning: bool = False,
    claimed_fx3_has_e_nd_or_apr: bool = False,
    exposed_focus_assistant_items: Tuple[str, ...] = P342_FOCUS_ASSISTANT_EXACT_FIVE_ITEMS,
    focus_magnif_time: str = "NO_LIMIT",
    initial_focus_mag_x: float = 1.0,
    requested_focus_mag_x: float = 1.0,
    af_in_focus_mag: str = "ON",
    auto_magnifier_in_mf: str = "ON",
    dormant_high_mp_focus_mag_scale_requested: bool = False,
    expect_af_in_focus_mag_or_auto_mag_in_movie: bool = False,
    claimed_movie_rec_cancels_focus_mag: bool = False,
    expect_focus_mag_crops_hdmi_or_internal_rec: bool = False,
    claimed_focus_assistant_wiped_by_camera_reset: bool = False,
    claimed_fx6_hdmi_focus_mag_is_3x_6x: bool = False,
    claimed_fx6_vf_focus_mag_is_2_1x_4_1x: bool = False,
    # Group D (Wave 71 §§3-4 + Tier-0)
    exp_std_adjust_metering_mode: str = "MULTI",
    exp_std_adjust_sixths: int = 0,
    exp_std_nonzero_acknowledged: bool = False,
    dormant_1_8_ev_step_requested: bool = False,
    expect_exp_std_adjust_modifies_exif_bias: bool = False,
    expect_exp_std_changes_cine_ei_iso: bool = False,
    claimed_exp_std_adjust_wiped_by_camera_reset: bool = False,
    claimed_exp_std_adjust_resets_exposure_comp: bool = False,
    fx6_ae_level_ev: float = 0.0,
    claimed_fx6_ae_level_limited_to_2ev: bool = False,
    usb_connection_mode: str = "SEL_WHEN_CONNECT",
    usb_lun_setting: str = "MULTI",
    usb_lan_tethering: str = "OFF",
    usb_lan_cnct_launch: str = "OFF",
    usb_lan_service: str = "NONE",
    airplane_mode: str = "ON",
    dual_usb_typec_and_multi_simultaneous: bool = False,
    slot1_host_usb_write_requested: bool = False,
    claimed_airplane_mode_blocks_usb_lan: bool = False,
    claimed_creators_app_allows_guided_live_over_usb: bool = False,
    claimed_usb_streaming_uvc_active_on_fx3: bool = False,
    claimed_reset_network_preserves_airplane_mode: bool = False,
    claimed_camera_reset_wipes_usb_tethering: bool = False,
    claimed_fx3_links_cusbgadgetiap: bool = False,
    claimed_fx6_lacks_cusbgadgetiap: bool = False,
    emmc_write_count: int = 0,
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
) -> RealHwPeakingAudioWindUsbPdNtscPalAntiDustFocusMagExpStdUsbTetherReport:
    donor = inspect_phase342_donors_bounded(
        force_clean_room=force_clean_room,
        work_root=work_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
    )

    ga = evaluate_p342_check_group_a_peaking_audio_and_wind(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        hdmi_info_display=hdmi_info_display,
        hdmi_raw_output=hdmi_raw_output,
        focus_magnifier_active=focus_magnifier_active,
        expect_peaking_outputs_over_hdmi=expect_peaking_outputs_over_hdmi,
        claimed_peaking_blocks_focus_magnifier=claimed_peaking_blocks_focus_magnifier,
        claimed_peaking_disabled_in_movie_af=claimed_peaking_disabled_in_movie_af,
        claimed_peaking_wiped_by_camera_reset=claimed_peaking_wiped_by_camera_reset,
        in_body_focus_map_requested=in_body_focus_map_requested,
        claimed_fx3_has_in_body_focus_map=claimed_fx3_has_in_body_focus_map,
        claimed_mc_focus_map_works_over_usb=claimed_mc_focus_map_works_over_usb,
        fx6_peaking_type_or_freq_requested=fx6_peaking_type_or_freq_requested,
        claimed_fx6_has_peaking_type_or_freq=claimed_fx6_has_peaking_type_or_freq,
        claimed_fx6_peaking_has_white_not_bw=claimed_fx6_peaking_has_white_not_bw,
        exposed_audio_recording_items=exposed_audio_recording_items,
        audio_recording=audio_recording,
        audio_rec_level=audio_rec_level,
        audio_out_timing=audio_out_timing,
        wind_noise_reduct=wind_noise_reduct,
        shoe_audio_set=shoe_audio_set,
        mic_35mm_inserted=mic_35mm_inserted,
        xlr_h1_attached=xlr_h1_attached,
        xlr_h1_handle_audio=xlr_h1_handle_audio,
        mi_shoe_mic_attached=mi_shoe_mic_attached,
        dormant_audio_level_display_requested=dormant_audio_level_display_requested,
        claimed_fx3_has_audio_level_display_menu=claimed_fx3_has_audio_level_display_menu,
        claimed_audio_recording_resists_camera_reset=claimed_audio_recording_resists_camera_reset,
        claimed_audio_out_timing_under_setup_sound_option=claimed_audio_out_timing_under_setup_sound_option,
        fx3_disable_builtin_limiter_requested=fx3_disable_builtin_limiter_requested,
        dormant_wind_noise_auto_requested=dormant_wind_noise_auto_requested,
        claimed_fx3_wind_noise_has_auto=claimed_fx3_wind_noise_has_auto,
        expect_wind_noise_applies_to_external_mic=expect_wind_noise_applies_to_external_mic,
        expect_wind_noise_active_in_sq=expect_wind_noise_active_in_sq,
        claimed_fx6_handle_has_physical_low_cut_switch=claimed_fx6_handle_has_physical_low_cut_switch,
        claimed_fx3_has_fx6_6step_limiter=claimed_fx3_has_fx6_6step_limiter,
    )

    gb = evaluate_p342_check_group_b_usb_pd_and_ntsc_pal(
        usb_power_supply=usb_power_supply,
        usb_power_terminal=usb_power_terminal,
        camera_power_state=camera_power_state,
        usb_pd_supply_active=usb_pd_supply_active,
        usb_pd_watts=usb_pd_watts,
        usb_c_cable_amps=usb_c_cable_amps,
        np_fz100_inserted=np_fz100_inserted,
        battery_soc_pct=battery_soc_pct,
        dc_c1_coupler_attached=dc_c1_coupler_attached,
        charge_led_active_while_on=charge_led_active_while_on,
        expect_battery_charges_while_camera_on=expect_battery_charges_while_camera_on,
        claimed_multi_micro_usb_powers_camera=claimed_multi_micro_usb_powers_camera,
        claimed_fx3_supports_batteryless_usb_pd_boot=claimed_fx3_supports_batteryless_usb_pd_boot,
        claimed_np_fz100_hot_swap_under_usb_pd=claimed_np_fz100_hot_swap_under_usb_pd,
        claimed_usb_power_supply_wiped_by_camera_reset=claimed_usb_power_supply_wiped_by_camera_reset,
        fx6_dc_in_volts=fx6_dc_in_volts,
        fx6_dc_in_hot_replug_during_rec=fx6_dc_in_hot_replug_during_rec,
        claimed_fx6_usb_c_powers_body=claimed_fx6_usb_c_powers_body,
        claimed_fx6_lacks_batteryless_dc_in_boot=claimed_fx6_lacks_batteryless_dc_in_boot,
        ntsc_pal_sku=ntsc_pal_sku,
        video_system=video_system,
        ntsc_pal_switch_requested=ntsc_pal_switch_requested,
        ntsc_pal_reboot_acknowledged=ntsc_pal_reboot_acknowledged,
        ntsc_pal_avf_info_write_requested=ntsc_pal_avf_info_write_requested,
        ntsc_pal_avf_target_slot=ntsc_pal_avf_target_slot,
        slot1_format_requested=slot1_format_requested,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_data_sector_writes=slot1_data_sector_writes,
        claimed_j1_supports_pal_selector=claimed_j1_supports_pal_selector,
        expect_non_default_system_lacks_banner=expect_non_default_system_lacks_banner,
        claimed_xavc_requires_mandatory_card_format=claimed_xavc_requires_mandatory_card_format,
        expect_cross_system_playback_allowed=expect_cross_system_playback_allowed,
        claimed_ntsc_pal_wiped_by_camera_reset=claimed_ntsc_pal_wiped_by_camera_reset,
        claimed_fx6_shows_running_on_ntsc_pal_banner=claimed_fx6_shows_running_on_ntsc_pal_banner,
        claimed_fx6_thumbnail_shows_all_freq_simultaneously=claimed_fx6_thumbnail_shows_all_freq_simultaneously,
    )

    gc = evaluate_p342_check_group_c_antidust_and_focus_assistant(
        shoot_mode=shoot_mode,
        apsc_s35_shooting=apsc_s35_shooting,
        battery_soc_pct=battery_soc_pct,
        dormant_anti_dust_function_requested=dormant_anti_dust_function_requested,
        dormant_shutter_when_pwr_off_requested=dormant_shutter_when_pwr_off_requested,
        claimed_fx3_shutter_when_pwr_off_present=claimed_fx3_shutter_when_pwr_off_present,
        claimed_fx3_shutter_closes_on_power_off=claimed_fx3_shutter_closes_on_power_off,
        sensor_cleaning_requested=sensor_cleaning_requested,
        sensor_cleaning_power_off_completed=sensor_cleaning_power_off_completed,
        claimed_fx6_has_shutter_when_pwr_off_or_ibis_cleaning=claimed_fx6_has_shutter_when_pwr_off_or_ibis_cleaning,
        claimed_fx3_has_e_nd_or_apr=claimed_fx3_has_e_nd_or_apr,
        exposed_focus_assistant_items=exposed_focus_assistant_items,
        focus_magnif_time=focus_magnif_time,
        initial_focus_mag_x=initial_focus_mag_x,
        requested_focus_mag_x=requested_focus_mag_x,
        af_in_focus_mag=af_in_focus_mag,
        auto_magnifier_in_mf=auto_magnifier_in_mf,
        dormant_high_mp_focus_mag_scale_requested=dormant_high_mp_focus_mag_scale_requested,
        expect_af_in_focus_mag_or_auto_mag_in_movie=expect_af_in_focus_mag_or_auto_mag_in_movie,
        claimed_movie_rec_cancels_focus_mag=claimed_movie_rec_cancels_focus_mag,
        expect_focus_mag_crops_hdmi_or_internal_rec=expect_focus_mag_crops_hdmi_or_internal_rec,
        claimed_focus_assistant_wiped_by_camera_reset=claimed_focus_assistant_wiped_by_camera_reset,
        claimed_fx6_hdmi_focus_mag_is_3x_6x=claimed_fx6_hdmi_focus_mag_is_3x_6x,
        claimed_fx6_vf_focus_mag_is_2_1x_4_1x=claimed_fx6_vf_focus_mag_is_2_1x_4_1x,
    )

    gd = evaluate_p342_check_group_d_exp_std_usblan_and_tier0(
        simulate_bench_dry_run=simulate_bench_dry_run,
        reset_action=reset_action,
        log_shooting_mode=log_shooting_mode,
        exp_std_adjust_metering_mode=exp_std_adjust_metering_mode,
        exp_std_adjust_sixths=exp_std_adjust_sixths,
        exp_std_nonzero_acknowledged=exp_std_nonzero_acknowledged,
        dormant_1_8_ev_step_requested=dormant_1_8_ev_step_requested,
        expect_exp_std_adjust_modifies_exif_bias=expect_exp_std_adjust_modifies_exif_bias,
        expect_exp_std_changes_cine_ei_iso=expect_exp_std_changes_cine_ei_iso,
        claimed_exp_std_adjust_wiped_by_camera_reset=claimed_exp_std_adjust_wiped_by_camera_reset,
        claimed_exp_std_adjust_resets_exposure_comp=claimed_exp_std_adjust_resets_exposure_comp,
        fx6_ae_level_ev=fx6_ae_level_ev,
        claimed_fx6_ae_level_limited_to_2ev=claimed_fx6_ae_level_limited_to_2ev,
        usb_connection_mode=usb_connection_mode,
        usb_lun_setting=usb_lun_setting,
        usb_lan_tethering=usb_lan_tethering,
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        usb_lan_service=usb_lan_service,
        airplane_mode=airplane_mode,
        dual_usb_typec_and_multi_simultaneous=dual_usb_typec_and_multi_simultaneous,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_host_usb_write_requested=slot1_host_usb_write_requested,
        slot1_data_sector_writes=slot1_data_sector_writes,
        claimed_airplane_mode_blocks_usb_lan=claimed_airplane_mode_blocks_usb_lan,
        claimed_creators_app_allows_guided_live_over_usb=claimed_creators_app_allows_guided_live_over_usb,
        claimed_usb_streaming_uvc_active_on_fx3=claimed_usb_streaming_uvc_active_on_fx3,
        claimed_reset_network_preserves_airplane_mode=claimed_reset_network_preserves_airplane_mode,
        claimed_camera_reset_wipes_usb_tethering=claimed_camera_reset_wipes_usb_tethering,
        claimed_fx3_links_cusbgadgetiap=claimed_fx3_links_cusbgadgetiap,
        claimed_fx6_lacks_cusbgadgetiap=claimed_fx6_lacks_cusbgadgetiap,
        emmc_write_count=emmc_write_count,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
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
        overall_status = (
            P342_GO_NO_GO_BLOCKED_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_FAILURE
        )
        go_no_go = (
            P342_GO_NO_GO_BLOCKED_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_FAILURE
        )
    elif simulate_bench_dry_run and gd.tier0_receipt_verified:
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
        go_no_go = GO_NO_GO_DRY_RUN_SIMULATED_READY
    elif gd.tier0_receipt_verified:
        overall_status = (
            P342_GO_NO_GO_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED
        )
        go_no_go = (
            P342_GO_NO_GO_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED
        )
    else:
        overall_status = P342_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        go_no_go = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT

    report = RealHwPeakingAudioWindUsbPdNtscPalAntiDustFocusMagExpStdUsbTetherReport(
        schema_version=P342_SCHEMA,
        phase_version=P342_VERSION,
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
        slot1_tier0_vault_mutated=gb.slot1_tier0_vault_mutated,
        rf_nvs_p12_p13_writes_authorized=False,
        fx3_peaking_outputs_to_hdmi=False,
        fx3_in_body_focus_map_present=False,
        fx6_peaking_type_freq_present=False,
        fx3_audio_level_display_menu_present=False,
        fx3_wind_noise_auto_present=False,
        fx3_charges_battery_while_on=False,
        fx3_supports_batteryless_usb_pd_boot=False,
        fx3_shutter_when_pwr_off_present=False,
        fx3_focus_mag_outputs_to_hdmi=False,
        fx3_exp_std_modifies_exif_bias=False,
        fx3_cusb_gadget_iap_present=False,
        emmc_write_count=PHASE342_EMMC_WRITE_COUNT,
        e_nd_actuator_tx_count=PHASE342_E_ND_ACTUATOR_TX_COUNT,
        e_nd_i2c_tx_bytes=0,
        rf_packets_transmitted=PHASE342_WIRELESS_RF_PACKETS_EMITTED,
        wireless_rf_packets_emitted=PHASE342_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_mutation_bytes=0,
        slot1_data_sector_writes=PHASE342_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE342_USB_PACKETS_TRANSMITTED,
        passive_tx_bytes_emitted=PHASE342_PASSIVE_TX_BYTES_EMITTED,
        raw_firmware_bytes_leaked=PHASE342_RAW_FIRMWARE_BYTES_LEAKED,
        errors=all_errors,
        warnings=all_warnings,
        report_sha256="",
    )
    digest = _canonical_sha256_dict(report.to_dict())
    return RealHwPeakingAudioWindUsbPdNtscPalAntiDustFocusMagExpStdUsbTetherReport(
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


def run_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
    **kwargs: Any,
) -> RealHwPeakingAudioWindUsbPdNtscPalAntiDustFocusMagExpStdUsbTetherReport:
    return evaluate_realhw_peaking_audio_wind_usb_pd_ntsc_pal_antidust_focus_mag_expstd_and_usbtether_preflight(
        **kwargs
    )


def verify_phase342_report(
    payload: Union[
        Mapping[str, Any],
        RealHwPeakingAudioWindUsbPdNtscPalAntiDustFocusMagExpStdUsbTetherReport,
    ],
) -> Phase342ReportVerifyResult:
    if hasattr(payload, "to_dict"):
        payload = payload.to_dict()  # type: ignore[union-attr]
    errors: List[str] = []
    if payload.get("schema_version") != P342_SCHEMA:
        errors.append(f"schema_version mismatch: {payload.get('schema_version')!r} != {P342_SCHEMA!r}")
    if payload.get("sony_help_guide_id") != P342_SONY_HELP_GUIDE_ID:
        errors.append("sony_help_guide_id must remain ilc/2210")
    if payload.get("go_no_go") not in PHASE_342_VALID_GO_NO_GO_VALUES:
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
        "fx3_peaking_outputs_to_hdmi",
        "fx3_in_body_focus_map_present",
        "fx6_peaking_type_freq_present",
        "fx3_audio_level_display_menu_present",
        "fx3_wind_noise_auto_present",
        "fx3_charges_battery_while_on",
        "fx3_supports_batteryless_usb_pd_boot",
        "fx3_shutter_when_pwr_off_present",
        "fx3_focus_mag_outputs_to_hdmi",
        "fx3_exp_std_modifies_exif_bias",
        "fx3_cusb_gadget_iap_present",
    )
    for field in locked_false_fields:
        if payload.get(field) is not False:
            errors.append(f"hard-locked boolean {field} must be False")

    locked_zero_fields = (
        "emmc_write_count",
        "e_nd_actuator_tx_count",
        "e_nd_i2c_tx_bytes",
        "rf_packets_transmitted",
        "wireless_rf_packets_emitted",
        "rf_nvs_mutation_bytes",
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
        P342_GO_NO_GO_PEAKING_AUDIO_WIND_USB_PD_NTSC_PAL_ANTIDUST_FOCUS_MAG_EXPSTD_AND_USBTETHER_VERIFIED,
    ):
        if payload.get("check_groups_passed") != 4 or payload.get("check_group_count") != 4:
            errors.append("verified report must pass 4/4 check groups")
        if payload.get("tier0_receipt_verified") is not True:
            errors.append("verified report must have tier0_receipt_verified=True")
        if payload.get("h0_equals_h3_count") != 16 or payload.get("h0_h3_surface_count") != 16:
            errors.append("verified report must have 16/16 H0 == H3")
        if payload.get("slot1_tier0_vault_mutated") is not False:
            errors.append("verified report must have slot1_tier0_vault_mutated=False")

    return Phase342ReportVerifyResult(valid=len(errors) == 0, errors=tuple(errors))


def render_phase342_markdown(
    report: RealHwPeakingAudioWindUsbPdNtscPalAntiDustFocusMagExpStdUsbTetherReport,
) -> str:
    lines = [
        f"# Phase 342 — 19th Physical Bench Readiness Preflight (`{report.schema_version}`)",
        "",
        f"- **Overall Status**: `{report.overall_status}`",
        f"- **Go/No-Go**: `{report.go_no_go}`",
        f"- **Verification Mode**: `{report.verification_mode}` (Dry Run: `{report.simulate_bench_dry_run}`)",
        f"- **Check Groups Passed**: `{report.check_groups_passed}/{report.check_group_count}`",
        f"- **Tier-0 Receipt Verified**: `{report.tier0_receipt_verified}` (`{report.receipt_mode}`)",
        f"- **H0 == H3 Surfaces**: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`",
        f"- **Safety Redlines**: `ready_attach={report.overall_ready_for_hardware_attach}`, "
        f"`emmc_writes={report.persistent_emmc_writes_authorized}`, "
        f"`emmc_write_count={report.emmc_write_count}`, "
        f"`cross_model_flash={report.cross_model_flash_authorized}`, "
        f"`rf_pkts={report.rf_packets_transmitted}`, `slot1_writes={report.slot1_data_sector_writes}`, "
        f"`usb_pkts={report.usb_packets_transmitted}`, `leaked={report.raw_firmware_bytes_leaked}`",
        f"- **Report SHA-256**: `{report.report_sha256}`",
        "",
        "## Check Groups",
        f"- **Group A (`{report.check_group_a.group_id}`)**: passed=`{report.check_group_a.passed}`, "
        f"peaking=`{report.check_group_a.peaking_display}` ({report.check_group_a.peaking_level}/"
        f"{report.check_group_a.peaking_color}, hdmi=`{report.check_group_a.fx3_peaking_outputs_to_hdmi}`, "
        f"fx6_type_freq_hits=`{report.check_group_a.fx6_peaking_type_freq_hits}`), "
        f"audio_level_menu=`{report.check_group_a.fx3_audio_level_display_menu_present}`, "
        f"wind=`{report.check_group_a.wind_noise_reduct}` (auto=`{report.check_group_a.fx3_wind_noise_auto_present}`, "
        f"internal_active=`{report.check_group_a.wind_noise_internal_mic_active}`)",
        f"- **Group B (`{report.check_group_b.group_id}`)**: passed=`{report.check_group_b.passed}`, "
        f"usb_pd=`{report.check_group_b.usb_power_supply}` ({report.check_group_b.usb_pd_watts}W / "
        f"{report.check_group_b.usb_c_cable_amps}A, np_fz100=`{report.check_group_b.np_fz100_inserted}`, "
        f"charge_while_on=`{report.check_group_b.fx3_charges_battery_while_on}`), "
        f"ntsc_pal=`{report.check_group_b.ntsc_pal_sku}/{report.check_group_b.video_system}` "
        f"(banner=`{report.check_group_b.ntsc_pal_boot_banner!r}`, slot1_mut=`{report.check_group_b.slot1_tier0_vault_mutated}`)",
        f"- **Group C (`{report.check_group_c.group_id}`)**: passed=`{report.check_group_c.passed}`, "
        f"shutter_pwroff=`{report.check_group_c.fx3_shutter_when_pwr_off_present}` "
        f"(park=`{report.check_group_c.fx3_power_off_shutter_park_state}`, "
        f"ilc2210_hits=`{report.check_group_c.fx3_ilc2210_shutter_pwroff_hits}`), "
        f"focus_mag=`x{report.check_group_c.requested_focus_mag_x}` "
        f"(init=`x{report.check_group_c.initial_focus_mag_x}`, time=`{report.check_group_c.focus_magnif_time}`, "
        f"hdmi=`{report.check_group_c.focus_mag_outputs_to_hdmi}`)",
        f"- **Group D (`{report.check_group_d.group_id}`)**: passed=`{report.check_group_d.passed}`, "
        f"exp_std=`{report.check_group_d.exp_std_adjust_sixths}/6 EV` "
        f"({report.check_group_d.exp_std_adjust_metering_mode}, reset_immune=`{report.check_group_d.exp_std_adjust_reset_immune}`, "
        f"fx6_ae=`{report.check_group_d.fx6_ae_level_ev} EV` in "
        f"[{report.check_group_d.fx6_ae_level_min_ev}, +{report.check_group_d.fx6_ae_level_max_ev}]), "
        f"usb_lan=`{report.check_group_d.usb_lan_tethering}`/{report.check_group_d.usb_lan_service} "
        f"(airplane=`{report.check_group_d.airplane_mode}`, iap_hits=`{report.check_group_d.fx3_cusb_gadget_iap_hits}`)",
    ]
    if report.errors:
        lines.extend(["", "## Errors"] + [f"- `{err}`" for err in report.errors])
    if report.warnings:
        lines.extend(["", "## Warnings"] + [f"- {warn}" for warn in report.warnings])
    return "\n".join(lines) + "\n"
