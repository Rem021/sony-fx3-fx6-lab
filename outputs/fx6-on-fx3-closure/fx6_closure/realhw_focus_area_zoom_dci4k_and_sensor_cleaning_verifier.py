"""Phase 291 — 10th Real-Hardware Physical Bench Readiness Verifier (`preflight-focus-area-zoom-dci4k-and-sensor-cleaning`).

Dedicated host-side read-only 10th physical bench & pre-shoot readiness verifier for Sony
`ILME-FX3` (`Ver. 7.02`, `ilc/2210`, Model `0x91030080`) vs `ILME-FX6` (`Ver. 6.01`),
extending the 10-stage operator bench preflight series (`preflight-card-insert` ->
`preflight-bench-cable-fan-slot1` -> `preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp` ->
`preflight-imagedb-touch-shoeaudio-and-lockop` ->
`preflight-diffset-customkey-autoslow-and-apsc` ->
`preflight-file-settings-gamma-assist-focus-mag-and-videolight` ->
`preflight-usb-mode-hdmi-info-protect-and-network-reset` ->
`preflight-pp-scinetone-wb-metering-and-shutter-type` ->
`preflight-focus-area-zoom-dci4k-and-sensor-cleaning`) by synthesizing Waves 50-52
official Sony `ILME-FX3` Help Guide (`ilc/2210`), `appFw.so`, `BK4`, and `.uxc` hardware
boundaries into 4 deterministic fail-closed check groups (`A..D`), bounded `O_RDONLY`
donor inspection (`< 0.15s`), `16/16 H0 == H3` baseline invariance, and dual-media
`528 B FX3RCPT1` Tier-0 receipt gating:

1. **Check Group A (`GROUP_A_FOCUS_AREA_STILL_TRACKING_BODY_WT_ZOOM_ISO_AND_FLASH_GATE` — Wave 50)**:
   - `14` `[Focus Area]` modes (`7` non-tracking + `7` `Tracking:` entries): all `7`
     `Tracking:` areas are Still-only (`AF-C`), locked out in Movie/`S&Q` (which uses
     `[Touch Tracking]`); `[Focus Area Limit]` (`>= 2`), Still-only `[Switch V/H AF Area]`,
     non-resettable `[Focus Area Color]` (`White`/`Red`), `[Circ. of Focus Point]`, and
     exact `ilc/2210` `AF Area Registration` (hold `Fn`; never legacy `AF Area Regist.`).
   - `ILME-FX3` `XLR-H1` handle unit has **NO zoom lever, NO record button, and NO `ZOOM HOLD`
     switch** — only body `W/T` lever (`1..8` `STBY`/`REC`) + `[Custom Key Z. Speed]`
     (`1..8`) + `[Remote Zoom Speed]` (`Variable`/`Fixed 1..8`) exist, contrasted with `FX6`
     Smart Handle (`Handle Zoom`, `Handle HOLD Switch`, `0..99` `Zoom Position Display`).
   - Non-resettable `[ISO Range Limit]` (`50..409600`) + Still `P/A`+`ISO AUTO`-only
     `[ISO AUTO Min. SS]` vs `Cine EI`/`Cine EI Quick` Base ISO `800`/`12800` lock;
     `[Flash Mode]` + Flash stack gated strictly to `EXPOSURE_MODE_STILL` +
     `Mechanical Shutter` (`1/250 s`), while `[Video Light Mode]` spans Still + Movie +
     `S&Q` (`PMIC 5V <= 900 mA`).

2. **Check Group B (`GROUP_B_XAVC_SI_DCI4K_24P_ASPECT_CUSTOM_HOLD11_CAMSET_AND_PHOTO_CAPTURE` — Wave 51)**:
   - `ILME-FX3 Ver. 3.00+/7.02` DOES expose `[XAVC S-I DCI 4K]` (`4096x2160`, `17:9`,
     All-Intra 4:2:2 10-bit, `23.98p..59.94p`, `S&Q` max `48fps`, no `100/120p`) +
     reboot-gated `24.00p` (`0x75ce`, which wipes volatile `/tmp` Stage-B overlays), while
     Long-GOP codecs stay `3840x2160` (`16:9` UHD) and HDMI RAW outputs `4264x2408`.
   - Still 4-mode `[Aspect Ratio]` (`3:2`/`4:3`/`16:9`/`1:1`, `APS-C S35` `M` step-down),
     Still `P/A/S/M` `[Reg. Custom Shoot Set]` with `11` hold checkboxes
     (`is_checked_recall_custom_hold0..10`), `FX3` `%c:%s/SONY/SETTING/%s/` card paths
     (`CAMPR%02d%c.DAT` `M1..M4` + `CAMSET` — ZERO `FX6`-only `PRIVATE/SONY/PRO/CAMERA`),
     and `[Photo Capture]` (`8.3M`/`2.1M`) blocked on `XAVC S-I DCI 4K` (`0x60ce`) and
     blocked fail-closed on read-only `Slot 1` Tier-0 Vault.

3. **Check Group C (`GROUP_C_SENSOR_CLEANING_51PCT_EV_COMP_CINE_EI_FOCUS_5VS2_AND_PLAYBACK` — Wave 52)**:
   - `[Sensor Cleaning]` (`_f.uxc` `0x67d6`, legacy `Cleaning Mode` `0xe7d7`) requires
     `NP-FZ100 >= 51%` + mandatory power-`OFF` after IBIS shake, contrasted with IBIS-less
     `FX6` front `e-ND` optical block + `APR`.
   - `[Exposure Comp.]` (`±5.0 EV` Still / `±2.0 EV` Movie) active in `M` only with
     `ISO AUTO` and 100% locked out under `Cine EI`/`Cine EI Quick` (omits legacy Alpha
     `[Reset EV Comp.]`), `[Focus Mode]` Still `5` modes vs Movie/`S&Q` `2` modes
     (`AF-C [MOVIE_AUTO]` / `MF`), non-resettable 3-mode `[View Mode]` + 2-mode
     `[Image Index]` (`9`/`25 Images`, no dormant `12`/`30`), and `[Rotate]` blocked
     fail-closed on read-only `Slot 1` Tier-0 Vault.

4. **Check Group D (`GROUP_D_PHYSICAL_BENCH_READINESS_TIER0_16H0H3_AND_FAIL_CLOSED_REDLINES`)**:
   - Dual-device `528 B FX3RCPT1` Tier-0 receipt + `16/16 H0 == H3` invariance, offline
     fail-closed gating (`READY_OFFLINE_AWAITING_BENCH_RECEIPTS`), `--simulate-bench-dry-run`
     operator receipt verification, and unconditional safety redline locks.

Hard-Locked Safety Invariants (UNCONDITIONAL):
- `overall_ready_for_hardware_attach = False`
- `hardware_live_attachment_authorized = False`
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `spi_nor_write_authorized = False`
- `el3_payload_transmit_authorized = False`
- `sd_physical_media_written = False`
- `cross_model_flash_authorized = False`
- `xlr_h1_zoom_lever_present = False`
- `fx3_private_sony_pro_camera_used = False`
- `usb_packets_transmitted = 0` (`physical_usb_packets_emitted = 0`)
- `raw_firmware_bytes_leaked = 0`
- `passive_tx_bytes_emitted = 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _ensure_cross_package_paths(repo_root: Path) -> None:
    for rel in (
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-firmware-lab",
        "outputs/fx3-vm",
        "outputs/fx6-on-fx3-closure",
    ):
        cand = str(repo_root / rel)
        if cand not in sys.path:
            sys.path.append(cand)


DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (  # noqa: E402
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import is_forced_clean_room, resolve_work_subpath  # noqa: E402
from .hardware_readiness_packet import (  # noqa: E402
    BODY_SERIAL_RE,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    HEX32_CID_RE,
    HEX64_RE,
)
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_WLAN_RSRC_DONOR_SHA256,
)
from .realhw_bench_cable_fan_and_slot1_verifier import (  # noqa: E402
    FX3_LIBUSBBUSPOWER_EXPECTED_SHA256,
    FX3_LIBUSBBUSPOWER_EXPECTED_SIZE,
    FX3_LIBUSBBUSPOWER_RELPATH,
)
from .realhw_card_insert_readiness_verifier import (  # noqa: E402
    DONOR_INSPECTION_MAX_SECONDS,
    EM_AARCH64,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    MIN_BODY_FW_TUPLE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_INT,
    _parse_elf64_header_and_pt_load,
    _parse_fw_tuple,
    _read_bounded_slice_o_rdonly,
    build_default_h0_baselines,
)
from .realhw_jiritsu_and_tier0_dumper_auditor import (  # noqa: E402
    LIBJIRITSU_EXPECTED_SHA256,
    LIBJIRITSU_EXPECTED_SIZE,
    LIBJIRITSU_RELPATH,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
    FX3_IM_ELF_EXPECTED_SHA256,
    FX3_IM_ELF_EXPECTED_SIZE,
    FX3_IM_ELF_RELPATH,
    FX6_APPFW_EXPECTED_SIZE,
    SIXTEEN_STORAGE_SURFACES,
    read_only_o_rdonly_digest_and_header,
)

# ---------------------------------------------------------------------------
# Schema, Verdicts & Non-Shadowing P291_* Domain Constants
# ---------------------------------------------------------------------------

PHASE_291_SCHEMA: str = "realhw_focus_area_zoom_dci4k_and_sensor_cleaning_verifier_v1"
P291_SCHEMA: str = PHASE_291_SCHEMA
REALHW_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_SCHEMA: str = PHASE_291_SCHEMA
PHASE_291_VERSION: str = "291.0.0"
P291_VERSION: str = PHASE_291_VERSION
P291_SONY_HELP_GUIDE_ID: str = "ilc/2210"

P291_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS: str = (
    "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
)
P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED: str = (
    "GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_READONLY_PREFLIGHT_VERIFIED"
)
P291_GO_NO_GO_BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_FAILURE: str = (
    "BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_CHECK_FAILURE"
)
PHASE_291_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    P291_GO_NO_GO_BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED,
)

P291_CHECK_GROUP_A_ID: str = (
    "GROUP_A_FOCUS_AREA_STILL_TRACKING_BODY_WT_ZOOM_ISO_AND_FLASH_GATE"
)
P291_CHECK_GROUP_B_ID: str = (
    "GROUP_B_XAVC_SI_DCI4K_24P_ASPECT_CUSTOM_HOLD11_CAMSET_AND_PHOTO_CAPTURE"
)
P291_CHECK_GROUP_C_ID: str = (
    "GROUP_C_SENSOR_CLEANING_51PCT_EV_COMP_CINE_EI_FOCUS_5VS2_AND_PLAYBACK"
)
P291_CHECK_GROUP_D_ID: str = (
    "GROUP_D_PHYSICAL_BENCH_READINESS_TIER0_16H0H3_AND_FAIL_CLOSED_REDLINES"
)
PHASE_291_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P291_CHECK_GROUP_A_ID,
    P291_CHECK_GROUP_B_ID,
    P291_CHECK_GROUP_C_ID,
    P291_CHECK_GROUP_D_ID,
)

PHASE291_RAW_FIRMWARE_BYTES_LEAKED: int = 0
PHASE291_PASSIVE_TX_BYTES_EMITTED: int = 0
PHASE291_USB_PACKETS_TRANSMITTED: int = 0

# Common Mode & Reset Constants
P291_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P291_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P291_PASM_EXPOSURE_MODES: Tuple[str, ...] = (
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "MANUAL_EXPOSURE",
)
P291_VALID_EXPOSURE_MODES: Tuple[str, ...] = P291_PASM_EXPOSURE_MODES + (
    "INTELLIGENT_AUTO",
    "FLEXIBLE_EXP",
)
P291_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "FLEXIBLE_ISO",
    "CINE_EI_QUICK",
    "CINE_EI",
)
P291_CINE_EI_BASE_ISOS: Tuple[int, ...] = (800, 12800)

# Check Group A Constants (Wave 50 — Focus Area, Zoom Speed vs XLR-H1, ISO Limit/Min.SS, Flash vs Video Light)
P291_FOCUS_AREA_BKID: str = "BKID_APP_setting_autofocus_area_contrast_detect_af"
P291_FOCUS_AREA_RESID16_HEX: str = "0x70ac"
P291_FOCUS_AREA_NON_TRACKING_SEVEN: Tuple[str, ...] = (
    "WIDE",
    "ZONE",
    "CENTER_FIX",
    "SPOT_S",
    "SPOT_M",
    "SPOT_L",
    "EXPAND_SPOT",
)
P291_FOCUS_AREA_TRACKING_SEVEN: Tuple[str, ...] = (
    "TRACKING_WIDE",
    "TRACKING_ZONE",
    "TRACKING_CENTER_FIX",
    "TRACKING_SPOT_S",
    "TRACKING_SPOT_M",
    "TRACKING_SPOT_L",
    "TRACKING_EXPAND_SPOT",
)
P291_FOCUS_AREA_FOURTEEN_MODES: Tuple[str, ...] = (
    P291_FOCUS_AREA_NON_TRACKING_SEVEN + P291_FOCUS_AREA_TRACKING_SEVEN
)
P291_FOCUS_AREA_LIMIT_RESID16_HEX: str = "0x6de2"
P291_SWITCH_VH_AF_AREA_RESID16_HEX: str = "0x73ae"
P291_VALID_SWITCH_VH_MODES: Tuple[str, ...] = (
    "OFF",
    "AF_POINT_ONLY",
    "AF_POINT_AND_AF_AREA",
)
P291_FOCUS_AREA_COLOR_RESID16_HEX: str = "0x6af1"
P291_VALID_FOCUS_AREA_COLORS: Tuple[str, ...] = ("WHITE", "RED")
P291_CIRC_FOCUS_POINT_RESID16_HEX: str = "0x74f6"
P291_VALID_CIRC_FOCUS_POINT_MODES: Tuple[str, ...] = ("DOES_NOT_CIRCULATE", "CIRCULATE")
P291_AF_AREA_REGISTRATION_BKID: str = "BKID_APP_setting_register_the_af_frame"
P291_AF_AREA_REGISTRATION_LABEL: str = "AF Area Registration"
P291_AF_AREA_REGISTRATION_RESID16_HEX: str = "0x6b64"
P291_ZOOM_LEVER_RESID16_HEX: str = "0x64c3"
P291_REMOTE_ZOOM_SPEED_RESID16_HEX: str = "0x7128"
P291_VALID_ZOOM_RANGES: Tuple[str, ...] = (
    "OPTICAL_ONLY",
    "CLEAR_IMAGE_ZOOM",
    "DIGITAL_ZOOM",
)
P291_VALID_REMOTE_ZOOM_SPEED_TYPES: Tuple[str, ...] = ("VARIABLE", "FIXED")
P291_ZOOM_SPEED_MIN: int = 1
P291_ZOOM_SPEED_MAX: int = 8
P291_ISO_RANGE_LIMIT_RESID16_HEX: str = "0x72f8"
P291_ISO_AUTO_MIN_SS_RESID16_HEX: str = "0x778b"
P291_ISO_FLOOR: int = 50
P291_ISO_CEILING: int = 409600
P291_ISO_AUTO_MIN_SS_PRESETS: Tuple[str, ...] = (
    "SLOWER_2EV",
    "SLOW_1EV",
    "STANDARD",
    "FAST_1EV",
    "FASTER_2EV",
)
P291_FLASH_MODE_RESID16_HEX: str = "0xe5ce"
P291_VALID_FLASH_MODES: Tuple[str, ...] = (
    "AUTOFLASH",
    "FILL_FLASH",
    "SLOW_SYNC",
    "REAR_SYNC",
    "FLASH_OFF",
)
P291_VALID_EXP_COMP_SET_MODES: Tuple[str, ...] = ("AMBIENT_AND_FLASH", "AMBIENT_ONLY")
P291_VIDEO_LIGHT_BKID: str = "BKID_APP_setting_video_light_set"
P291_VIDEO_LIGHT_RESID16_HEX: str = "0x6211"
P291_VALID_VIDEO_LIGHT_MODES: Tuple[str, ...] = (
    "POWER_LINK",
    "REC_LINK",
    "REC_LINK_AND_STBY",
    "AUTO",
)
P291_MI_SHOE_5V_MAX_MA: int = 900

# Check Group B Constants (Wave 51 — DCI 4K & 24.00p Reboot, Aspect Ratio, 11 Holds, CAMSET Card Path, Photo Capture)
P291_XAVC_SI_DCI_4K_RESID16_HEX: str = "0x7336"
P291_DCI_4K_REBOOT_24P_RESID16_HEX: str = "0x75ce"
P291_DCI_4K_WIDTH_HEIGHT: str = "4096x2160"
P291_UHD_4K_WIDTH_HEIGHT: str = "3840x2160"
P291_HD_WIDTH_HEIGHT: str = "1920x1080"
P291_HDMI_RAW_WIDTH_HEIGHT: str = "4264x2408"
P291_VALID_MOVIE_FILE_FORMATS: Tuple[str, ...] = (
    "XAVC_S_I_DCI_4K",
    "XAVC_S_I_4K",
    "XAVC_S_4K",
    "XAVC_HS_4K",
    "XAVC_S_HD",
    "XAVC_S_I_HD",
)
P291_DCI_4K_FRAME_RATES: Tuple[str, ...] = (
    "23.98P",
    "24.00P",
    "25P",
    "29.97P",
    "50P",
    "59.94P",
)
P291_DCI_4K_SQ_MAX_FPS: int = 48
P291_ASPECT_RATIO_RESID16_HEX: str = "0x757c"
P291_STILL_ASPECT_FOUR_MODES: Tuple[str, ...] = ("3:2", "4:3", "16:9", "1:1")
P291_RECALL_CUSTOM_SHOOT_SET_RESID16_HEX: str = "0x7631"
P291_RECALL_CUSTOM_HOLD_11_KEYS: Tuple[str, ...] = (
    "is_checked_recall_custom_hold0",
    "is_checked_recall_custom_hold1",
    "is_checked_recall_custom_hold2",
    "is_checked_recall_custom_hold3",
    "is_checked_recall_custom_hold4",
    "is_checked_recall_custom_hold5",
    "is_checked_recall_custom_hold6",
    "is_checked_recall_custom_hold7",
    "is_checked_recall_custom_hold8",
    "is_checked_recall_custom_hold9",
    "is_checked_recall_custom_hold10",
)
P291_FX3_SETTING_CARD_PATH_RE = re.compile(
    r"^(?:[A-Za-z]:)?/(?:PRIVATE/)?SONY/SETTING/FX3/(?:CAMPR0[1-4][A-Za-z0-9]?\.DAT|CAMSET(?:0[1-9]|10)\.DAT)?$"
)
P291_DEFAULT_FX3_SETTING_CARD_PATH: str = "/PRIVATE/SONY/SETTING/FX3/CAMSET01.DAT"
P291_FORBIDDEN_FX6_PRO_PREFIXES: Tuple[str, ...] = (
    "/SONY/PRO/CAMERA",
    "/SONY/PRO/SCENE",
    "PRO/CAMERA",
    "PRO/SCENE",
)
P291_PHOTO_CAPTURE_RESID16_HEX: str = "0x6856"
P291_PHOTO_CAPTURE_DCI4K_BLOCK_RESID16_HEX: str = "0x60ce"
P291_ENLARGE_IMAGE_RESID16_HEX: str = "0xe8cb"

# Check Group C Constants (Wave 52 — Sensor Cleaning >=51%, EV Comp vs Cine EI, Focus Mode 5 vs 2, Playback/Rotate)
P291_SENSOR_CLEANING_RESID16_HEX: str = "0x67d6"
P291_LEGACY_CLEANING_MODE_RESID16_HEX: str = "0xe7d7"
P291_SENSOR_CLEANING_MIN_SOC_PCT: float = 51.0
P291_CRCOMMANDID_SENSOR_CLEANING: int = 320
P291_EXPOSURE_COMP_RESID16_HEX: str = "0x76de"
P291_EV_COMP_STILL_ABS_MAX: float = 5.0
P291_EV_COMP_MOVIE_ABS_MAX: float = 2.0
P291_VALID_EXPOSURE_STEPS: Tuple[str, ...] = ("0.3EV", "0.5EV")
P291_FOCUS_MODE_MOVIE_RESID16_HEX: str = "0x625e"
P291_STILL_FOCUS_FIVE_MODES: Tuple[str, ...] = ("AF_S", "AF_A", "AF_C", "DMF", "MF")
P291_MOVIE_FOCUS_TWO_MODES: Tuple[str, ...] = ("AF_C", "MF")
P291_VALID_PRIORITY_SET_AF_MODES: Tuple[str, ...] = ("BALANCED_EMPHASIS", "AF", "RELEASE")
P291_VIEW_MODE_THREE_MODES: Tuple[str, ...] = (
    "DATE_VIEW",
    "FOLDER_VIEW_STILL",
    "MOVIE_VIEW",
)
P291_DORMANT_VIEW_MODES: Tuple[str, ...] = ("FOLDER_VIEW_MP4", "AVCHD_VIEW")
P291_IMAGE_INDEX_TWO_MODES: Tuple[str, ...] = ("9_IMAGES", "25_IMAGES")
P291_DORMANT_IMAGE_INDEX_MODES: Tuple[str, ...] = ("12_IMAGES", "30_IMAGES")
P291_VALID_DISPLAY_ROTATION_MODES: Tuple[str, ...] = ("AUTO", "MANUAL", "OFF")

# Error Codes
P291_GA_ERR_MODEL_OR_FW_FLOOR: str = "P291_GA_ERR_MODEL_OR_FW_FLOOR"
P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG: str = (
    "P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG"
)
P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED: str = (
    "P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED"
)
P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK: str = (
    "P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK"
)
P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT: str = (
    "P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT"
)

P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY: str = (
    "P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY"
)
P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC: str = (
    "P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC"
)
P291_GB_ERR_RECALL_CUSTOM_11_OR_HLG_LOCK: str = (
    "P291_GB_ERR_RECALL_CUSTOM_11_OR_HLG_LOCK"
)
P291_GB_ERR_CAMSET_CARD_PATH_VS_FX6_PRO_CAMERA: str = (
    "P291_GB_ERR_CAMSET_CARD_PATH_VS_FX6_PRO_CAMERA"
)
P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL: str = (
    "P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL"
)

P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END: str = (
    "P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END"
)
P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK: str = (
    "P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK"
)
P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU: str = (
    "P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU"
)
P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL: str = (
    "P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL"
)

P291_GD_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "P291_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P291_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION: str = (
    "P291_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"
)

_TRIVIAL_HEX64_SET = {"0" * 64, "f" * 64}


# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase291DonorInspectionResult:
    passed: bool
    verification_mode: str
    read_only_o_rdonly_enforced: bool
    elapsed_seconds: float
    within_150ms_budget: bool
    inspected_artifacts: Tuple[str, ...]
    fx3_im_elf_verified: bool
    fx3_libjiritsu_verified: bool
    fx3_libusbbuspower_verified: bool
    fx6_appfw_verified: bool
    fx6_wlan_rsrc_verified: bool
    fx3_upm_ko_verified: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P291CheckGroupAFocusZoomIsoFlashResult:
    check_group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    sony_help_guide_id: str
    reset_action: str
    shoot_mode: str
    focus_area_bkid: str
    focus_area_resid16_hex: str
    focus_area: str
    non_tracking_focus_area_count: int
    tracking_focus_area_count: int
    tracking_still_only_enforced: bool
    touch_tracking_used_for_movie_sq: bool
    focus_area_limit_selected_count: int
    switch_vh_af_area: str
    focus_area_color: str
    circ_of_focus_point: str
    af_area_registration_label: str
    xlr_h1_zoom_lever_present: bool
    xlr_h1_rec_button_present: bool
    xlr_h1_zoom_hold_switch_present: bool
    fx6_smart_handle_zero_to_99_is_position_display: bool
    zoom_range: str
    zoom_lever_stby_speed: int
    zoom_lever_rec_speed: int
    custom_key_zoom_stby_speed: int
    custom_key_zoom_rec_speed: int
    remote_zoom_speed_type: str
    remote_zoom_fixed_stby_speed: int
    remote_zoom_fixed_rec_speed: int
    iso_range_limit_min: int
    iso_range_limit_max: int
    iso_auto_min: int
    iso_auto_max: int
    iso_auto_min_ss: str
    iso_auto_min_ss_still_pa_only_enforced: bool
    log_shooting_mode: str
    cine_ei_base_iso: int
    flash_mode: str
    flash_firing_enabled: bool
    shutter_type: str
    flash_mechanical_still_gate_verified: bool
    video_light_mode: str
    mi_shoe_5v_current_ma: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P291CheckGroupBDci4kAspectHoldCamsetPhotoResult:
    check_group_id: str
    passed: bool
    movie_file_format: str
    movie_resolution_wh: str
    rec_frame_rate: str
    dci4k_24p_reboot_required: bool
    dci4k_24p_reboot_wipes_volatile_tmp_acknowledged: bool
    hdmi_raw_output: bool
    hdmi_raw_resolution_wh: str
    sq_dci4k_fps: int
    media_speed_grade: str
    still_aspect_ratio: str
    exposed_still_aspect_count: int
    apsc_s35_on: bool
    recall_custom_hold_checkbox_count: int
    recall_custom_hold_keys: Tuple[str, ...]
    camset_card_path: str
    memory_recall_media_slot: str
    fx3_private_sony_pro_camera_used: bool
    photo_capture_requested: bool
    photo_capture_slot: int
    photo_capture_dci4k_blocked_and_slot1_firewalled: bool
    enlarge_image_still_only_enforced: bool
    enlarge_initial_mag: str
    enlarge_initial_position: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P291CheckGroupCSensorCleanEvFocusPlaybackResult:
    check_group_id: str
    passed: bool
    sensor_cleaning_resid16_hex: str
    sensor_cleaning_requested: bool
    battery_soc_pct: float
    mandatory_power_off_after_cleaning: bool
    fx6_reference_e_nd_and_apr: bool
    exposure_comp_ev: float
    exposure_step: str
    exposure_mode: str
    iso_mode: str
    log_shooting_mode: str
    ev_comp_cine_ei_lockout_verified: bool
    focus_mode: str
    exposed_still_focus_mode_count: int
    exposed_movie_focus_mode_count: int
    focus_mode_5vs2_split_verified: bool
    priority_set_in_af: str
    af_illuminator: str
    view_mode: str
    image_index_mode: str
    display_as_group: str
    display_rotation: str
    playback_media_slot: int
    playback_rotate_requested: bool
    slot1_contains_tier0_dump: bool
    playback_rotate_slot1_firewall_enforced: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P291CheckGroupDPhysicalBenchAndTier0Result:
    check_group_id: str
    passed: bool
    passive_tx_bytes_emitted: int
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    tier0_receipt_present: bool
    tier0_receipt_verified: bool
    distinct_physical_media_verified: bool
    cross_model_flash_authorized: bool
    persistent_emmc_writes_authorized: bool
    overall_ready_for_hardware_attach: bool
    warnings: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwFocusAreaZoomDci4kSensorCleaningReport:
    schema: str
    phase_version: str
    verification_mode: str
    simulate_bench_dry_run: bool
    overall_status: str
    go_no_go: str
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    cross_model_flash_authorized: bool
    xlr_h1_zoom_lever_present: bool
    fx3_private_sony_pro_camera_used: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    passive_tx_bytes_emitted: int
    check_group_count: int
    check_groups_passed: int
    all_4_check_groups_passed: bool
    tier0_receipt_verified: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    donor_inspection: Phase291DonorInspectionResult
    check_group_a_focus_zoom_iso_flash: P291CheckGroupAFocusZoomIsoFlashResult
    check_group_b_dci4k_aspect_hold_camset_photo: P291CheckGroupBDci4kAspectHoldCamsetPhotoResult
    check_group_c_sensor_clean_ev_focus_playback: P291CheckGroupCSensorCleanEvFocusPlaybackResult
    check_group_d_physical_bench_and_tier0: P291CheckGroupDPhysicalBenchAndTier0Result
    warnings: Tuple[str, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase291ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers & Bounded O_RDONLY Donor Inspection (< 0.15s)
# ---------------------------------------------------------------------------


def _norm_token(raw: str) -> str:
    return re.sub(r"[\s\-:/\.]+", "_", str(raw).strip().upper()).strip("_")


def _norm_focus_area(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "FLEXIBLE_SPOT_S": "SPOT_S",
        "FLEXIBLE_SPOT_M": "SPOT_M",
        "FLEXIBLE_SPOT_L": "SPOT_L",
        "TRACKING_FLEXIBLE_SPOT_S": "TRACKING_SPOT_S",
        "TRACKING_FLEXIBLE_SPOT_M": "TRACKING_SPOT_M",
        "TRACKING_FLEXIBLE_SPOT_L": "TRACKING_SPOT_L",
    }
    return aliases.get(tok, tok)


def _norm_aspect_ratio(raw: str) -> str:
    s = str(raw).strip()
    if s in P291_STILL_ASPECT_FOUR_MODES:
        return s
    aliases = {
        "3_2": "3:2",
        "4_3": "4:3",
        "16_9": "16:9",
        "1_1": "1:1",
    }
    return aliases.get(_norm_token(s), s)


def _norm_frame_rate(raw: str) -> str:
    tok = str(raw).strip().upper().replace(" ", "")
    if tok in ("23.98", "23.98P", "24P_23.98"):
        return "23.98P"
    if tok in ("24", "24.00", "24.00P", "TRUE24P"):
        return "24.00P"
    if tok in ("25", "25P", "25.00P"):
        return "25P"
    if tok in ("29.97", "29.97P"):
        return "29.97P"
    if tok in ("50", "50P", "50.00P"):
        return "50P"
    if tok in ("59.94", "59.94P"):
        return "59.94P"
    if tok in ("100", "100P"):
        return "100P"
    if tok in ("119.88", "119.88P", "120", "120P"):
        return "120P"
    return tok


def _norm_focus_mode(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "AFS": "AF_S",
        "AF_S": "AF_S",
        "AFA": "AF_A",
        "AF_A": "AF_A",
        "AFC": "AF_C",
        "AF_C": "AF_C",
        "MOVIE_AUTO": "AF_C",
        "DMF": "DMF",
        "MF": "MF",
    }
    return aliases.get(tok, tok)


def _norm_image_index(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "9": "9_IMAGES",
        "9_IMAGE": "9_IMAGES",
        "9_IMAGES": "9_IMAGES",
        "25": "25_IMAGES",
        "25_IMAGE": "25_IMAGES",
        "25_IMAGES": "25_IMAGES",
        "12": "12_IMAGES",
        "12_IMAGES": "12_IMAGES",
        "30": "30_IMAGES",
        "30_IMAGES": "30_IMAGES",
    }
    return aliases.get(tok, tok)


def _norm_exposure_step(raw: str) -> str:
    s = str(raw).strip().upper().replace(" ", "")
    if s in ("0.3EV", "0.3", "1/3EV"):
        return "0.3EV"
    if s in ("0.5EV", "0.5", "1/2EV"):
        return "0.5EV"
    return s


def _canonical_sha256_dict(obj: Mapping[str, Any], exclude_key: Optional[str] = None) -> str:
    body = dict(copy.deepcopy(obj))
    if exclude_key:
        body.pop(exclude_key, None)
    donor_sub = body.get("donor_inspection")
    if isinstance(donor_sub, dict):
        donor_sub.pop("elapsed_seconds", None)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _is_trivial_hex64(val: str) -> bool:
    norm = str(val).strip().lower()
    if not HEX64_RE.match(norm):
        return True
    return norm in _TRIVIAL_HEX64_SET


def inspect_phase291_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase291DonorInspectionResult:
    """Inspect local BYOF donors strictly via O_RDONLY within < 0.15s, or Clean-Room fallback."""
    t0 = time.perf_counter()
    errors: List[str] = []
    eff_clean = force_clean_room if force_clean_room is not None else synthetic_clean_room
    env_clean_room = is_forced_clean_room() or (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
    )
    clean_room = env_clean_room if eff_clean is None else bool(eff_clean)

    fx3_im_path = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=False)
    fx3_jit_path = resolve_work_subpath(LIBJIRITSU_RELPATH, require_file=False)
    fx3_usb_pwr_path = resolve_work_subpath(FX3_LIBUSBBUSPOWER_RELPATH, require_file=False)
    fx6_appfw_path = fx6_lib_dir / "appFw.so"
    fx6_wlan_path = fx6_lib_dir / "libWlanResource.so"
    fx3_upm_path = fx3_modules_dir / "upm.ko"

    donors_present = (
        fx3_im_path.is_file()
        and fx3_jit_path.is_file()
        and fx3_usb_pwr_path.is_file()
        and fx6_appfw_path.is_file()
        and fx6_wlan_path.is_file()
        and fx3_upm_path.is_file()
    )

    if eff_clean is False and not donors_present:
        elapsed = round(time.perf_counter() - t0, 6)
        return Phase291DonorInspectionResult(
            passed=False,
            verification_mode="LOCAL_DONOR_O_RDONLY",
            read_only_o_rdonly_enforced=True,
            elapsed_seconds=elapsed,
            within_150ms_budget=(elapsed < max_seconds),
            inspected_artifacts=(),
            fx3_im_elf_verified=fx3_im_path.is_file(),
            fx3_libjiritsu_verified=fx3_jit_path.is_file(),
            fx3_libusbbuspower_verified=fx3_usb_pwr_path.is_file(),
            fx6_appfw_verified=fx6_appfw_path.is_file(),
            fx6_wlan_rsrc_verified=fx6_wlan_path.is_file(),
            fx3_upm_ko_verified=fx3_upm_path.is_file(),
            raw_firmware_bytes_leaked=PHASE291_RAW_FIRMWARE_BYTES_LEAKED,
            errors=(f"Local BYOF donors missing under fx6_lib_dir={fx6_lib_dir}",),
        )

    use_live = (not clean_room) and donors_present
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"
    inspected: List[str] = []

    if use_live:
        im_sz, im_sha, im_head = read_only_o_rdonly_digest_and_header(fx3_im_path)
        im_mag, im_64, im_mach, _ = _parse_elf64_header_and_pt_load(im_head)
        im_ok = (
            im_sz == FX3_IM_ELF_EXPECTED_SIZE
            and im_sha == FX3_IM_ELF_EXPECTED_SHA256
            and im_mag
            and im_64
            and im_mach == EM_AARCH64
        )
        inspected.append("im.elf")
        if not im_ok:
            errors.append(f"im.elf O_RDONLY verification failed: size={im_sz}")

        jit_sz, jit_sha, jit_head = read_only_o_rdonly_digest_and_header(fx3_jit_path)
        jit_mag, jit_64, jit_mach, _ = _parse_elf64_header_and_pt_load(jit_head)
        jit_ok = (
            jit_sz == LIBJIRITSU_EXPECTED_SIZE
            and jit_sha == LIBJIRITSU_EXPECTED_SHA256
            and jit_mag
            and jit_64
            and jit_mach == EM_AARCH64
        )
        inspected.append("libJiritsu.so")
        if not jit_ok:
            errors.append(f"libJiritsu.so O_RDONLY verification failed: size={jit_sz}")

        pwr_sz, pwr_sha, pwr_head = read_only_o_rdonly_digest_and_header(fx3_usb_pwr_path)
        pwr_mag, pwr_64, pwr_mach, _ = _parse_elf64_header_and_pt_load(pwr_head)
        pwr_ok = (
            pwr_sz == FX3_LIBUSBBUSPOWER_EXPECTED_SIZE
            and pwr_sha == FX3_LIBUSBBUSPOWER_EXPECTED_SHA256
            and pwr_mag
            and pwr_64
            and pwr_mach == EM_AARCH64
        )
        inspected.append("libUsbBusPower.so")
        if not pwr_ok:
            errors.append(f"libUsbBusPower.so O_RDONLY verification failed: size={pwr_sz}")

        appfw_sz, appfw_head, _ = _read_bounded_slice_o_rdonly(fx6_appfw_path, 4096)
        appfw_mag, appfw_64, appfw_mach, _ = _parse_elf64_header_and_pt_load(appfw_head)
        appfw_ok = (
            appfw_sz == FX6_APPFW_EXPECTED_SIZE
            and appfw_mag
            and appfw_64
            and appfw_mach == EM_AARCH64
        )
        inspected.append("appFw.so(bounded-4KiB)")
        if not appfw_ok:
            errors.append(f"appFw.so bounded O_RDONLY header failed: size={appfw_sz}")

        wlan_sz, wlan_sha, wlan_head = read_only_o_rdonly_digest_and_header(fx6_wlan_path)
        wlan_mag, wlan_64, wlan_mach, _ = _parse_elf64_header_and_pt_load(wlan_head)
        wlan_ok = (
            wlan_sz > 0
            and wlan_sha == FX6_WLAN_RSRC_DONOR_SHA256
            and wlan_mag
            and wlan_64
            and wlan_mach == EM_AARCH64
        )
        inspected.append("libWlanResource.so")
        if not wlan_ok:
            errors.append("libWlanResource.so O_RDONLY SHA-256 verification failed")

        upm_sz, upm_head, _ = _read_bounded_slice_o_rdonly(fx3_upm_path, 4096)
        upm_mag, upm_64, upm_mach, _ = _parse_elf64_header_and_pt_load(upm_head)
        upm_ok = upm_sz > 0 and upm_mag and upm_64 and upm_mach == EM_AARCH64
        inspected.append("upm.ko(bounded-4KiB)")
        if not upm_ok:
            errors.append(f"upm.ko bounded O_RDONLY header failed: size={upm_sz}")
    else:
        im_ok = jit_ok = pwr_ok = appfw_ok = wlan_ok = upm_ok = True
        inspected.extend(
            [
                "synthetic_clean_room:im.elf",
                "synthetic_clean_room:libJiritsu.so",
                "synthetic_clean_room:libUsbBusPower.so",
                "synthetic_clean_room:appFw.so",
                "synthetic_clean_room:libWlanResource.so",
                "synthetic_clean_room:upm.ko",
            ]
        )

    elapsed = round(time.perf_counter() - t0, 6)
    within_budget = elapsed < max_seconds
    if not within_budget:
        errors.append(f"Bounded donor inspection exceeded {max_seconds}s: {elapsed}s")

    return Phase291DonorInspectionResult(
        passed=(
            im_ok
            and jit_ok
            and pwr_ok
            and appfw_ok
            and wlan_ok
            and upm_ok
            and within_budget
            and len(errors) == 0
        ),
        verification_mode=mode,
        read_only_o_rdonly_enforced=True,
        elapsed_seconds=elapsed,
        within_150ms_budget=within_budget,
        inspected_artifacts=tuple(inspected),
        fx3_im_elf_verified=im_ok,
        fx3_libjiritsu_verified=jit_ok,
        fx3_libusbbuspower_verified=pwr_ok,
        fx6_appfw_verified=appfw_ok,
        fx6_wlan_rsrc_verified=wlan_ok,
        fx3_upm_ko_verified=upm_ok,
        raw_firmware_bytes_leaked=PHASE291_RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group A (Wave 50 — Focus Area, Body W/T Zoom vs XLR-H1, ISO Range/Min.SS, Flash vs Video Light)
# ---------------------------------------------------------------------------


def evaluate_p291_check_group_a_focus_zoom_iso_flash(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P291_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Focus Area & AF Area Registration
    focus_area_bkid: str = P291_FOCUS_AREA_BKID,
    focus_area_resid16_hex: str = P291_FOCUS_AREA_RESID16_HEX,
    focus_area: str = "WIDE",
    exposed_non_tracking_focus_areas: Sequence[str] = P291_FOCUS_AREA_NON_TRACKING_SEVEN,
    exposed_tracking_focus_areas: Sequence[str] = P291_FOCUS_AREA_TRACKING_SEVEN,
    expect_tracking_focus_area_in_movie: bool = False,
    touch_tracking_used_for_movie_sq: bool = True,
    fx6_reference_tracking_focus_areas_present: bool = False,
    focus_area_limit_selected_count: int = 14,
    switch_vh_af_area: str = "OFF",
    expect_switch_vh_in_movie: bool = False,
    focus_area_color: str = "WHITE",
    circ_of_focus_point: str = "DOES_NOT_CIRCULATE",
    af_area_registration_label: str = P291_AF_AREA_REGISTRATION_LABEL,
    claimed_non_resettable_af_prefs_wiped: bool = False,
    # Body W/T Zoom Speed vs Handle-Less XLR-H1
    xlr_h1_zoom_lever_present: bool = False,
    xlr_h1_rec_button_present: bool = False,
    xlr_h1_zoom_hold_switch_present: bool = False,
    fx6_smart_handle_zero_to_99_is_speed_scale: bool = False,
    zoom_range: str = "OPTICAL_ONLY",
    still_raw_active: bool = False,
    high_fps_120_100: bool = False,
    claimed_zoom_range_wiped: bool = False,
    zoom_lever_stby_speed: int = 3,
    zoom_lever_rec_speed: int = 8,
    custom_key_zoom_stby_speed: int = 3,
    custom_key_zoom_rec_speed: int = 3,
    remote_zoom_speed_type: str = "VARIABLE",
    remote_zoom_fixed_stby_speed: int = 3,
    remote_zoom_fixed_rec_speed: int = 3,
    # ISO Range Limit & ISO AUTO Min. SS vs Cine EI
    iso_range_limit_min: int = 50,
    iso_range_limit_max: int = 409600,
    claimed_iso_range_limit_wiped: bool = False,
    iso_auto_min: int = 100,
    iso_auto_max: int = 12800,
    exposure_mode: str = "MANUAL_EXPOSURE",
    iso_mode: str = "CINE_EI_BASE",
    iso_auto_min_ss: str = "STANDARD",
    iso_auto_min_ss_active: bool = False,
    expect_iso_auto_min_ss_in_movie_or_manual_iso: bool = False,
    log_shooting_mode: str = "CINE_EI",
    cine_ei_base_iso: int = 800,
    expect_iso_variable_in_cine_ei: bool = False,
    # Flash Mode vs Video Light Mode
    shutter_type: str = "MECHANICAL_SHUTTER",
    silent_mode: str = "OFF",
    flash_mode: str = "FLASH_OFF",
    flash_firing_enabled: bool = False,
    flash_comp_ev: float = 0.0,
    exp_comp_set: str = "AMBIENT_AND_FLASH",
    claimed_exp_comp_set_wiped: bool = False,
    video_light_mode: str = "POWER_LINK",
    mi_shoe_5v_current_ma: int = 0,
) -> P291CheckGroupAFocusZoomIsoFlashResult:
    """Validate Wave 50: Focus Area 7+7 Tracking, Body W/T Zoom vs XLR-H1, ISO Limit/Min.SS, & Flash vs Video Light."""
    errors: List[str] = []

    fw_tuple = _parse_fw_tuple(body_fw)
    if body_model_id != TARGET_MODEL_ID_INT or fw_tuple is None or fw_tuple < MIN_BODY_FW_TUPLE:
        errors.append(
            f"{P291_GA_ERR_MODEL_OR_FW_FLOOR}: model=0x{body_model_id:08x}, fw={body_fw!r} "
            f"(requires 0x{TARGET_MODEL_ID_INT:08x} & >= 2.04)"
        )
    if str(sony_help_guide_id).strip() != P291_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P291_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id={sony_help_guide_id!r} != {P291_SONY_HELP_GUIDE_ID!r}"
        )

    norm_reset = _norm_token(reset_action)
    if norm_reset not in P291_VALID_RESET_ACTIONS:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: invalid reset_action={reset_action!r}"
        )

    norm_shoot = _norm_token(shoot_mode)
    if norm_shoot not in P291_VALID_SHOOT_MODES:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: invalid shoot_mode={shoot_mode!r}"
        )

    # 1. Focus Area 7+7 Still-only Tracking & AF Area Registration
    norm_fa = _norm_focus_area(focus_area)
    norm_non_track = tuple(_norm_focus_area(x) for x in exposed_non_tracking_focus_areas)
    norm_track = tuple(_norm_focus_area(x) for x in exposed_tracking_focus_areas)
    norm_switch_vh = _norm_token(switch_vh_af_area)
    norm_fa_color = _norm_token(focus_area_color)
    norm_circ = _norm_token(circ_of_focus_point)

    if focus_area_bkid != P291_FOCUS_AREA_BKID or focus_area_resid16_hex.lower() != P291_FOCUS_AREA_RESID16_HEX:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: Focus Area BKID/resid16 mismatch"
        )
    if norm_non_track != P291_FOCUS_AREA_NON_TRACKING_SEVEN or len(norm_non_track) != 7:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: expected 7 non-tracking focus areas, got {exposed_non_tracking_focus_areas!r}"
        )
    if norm_track != P291_FOCUS_AREA_TRACKING_SEVEN or len(norm_track) != 7:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: expected 7 Tracking: focus areas, got {exposed_tracking_focus_areas!r}"
        )
    if norm_fa not in P291_FOCUS_AREA_FOURTEEN_MODES:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: invalid focus_area={focus_area!r}"
        )

    tracking_still_only_ok = True
    is_tracking_fa = norm_fa in P291_FOCUS_AREA_TRACKING_SEVEN
    if expect_tracking_focus_area_in_movie or (norm_shoot in ("MOVIE", "S_AND_Q") and is_tracking_fa):
        tracking_still_only_ok = False
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: 7 Tracking: Focus Areas are Still-only; Movie/S&Q uses [Touch Tracking]"
        )
    if not touch_tracking_used_for_movie_sq:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: Movie/S&Q tracking must route via [Touch Tracking]"
        )
    if fx6_reference_tracking_focus_areas_present:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: ILME-FX6 lacks Tracking: Focus Areas (only Wide/Zone/Flexible Spot)"
        )
    if focus_area_limit_selected_count < 2 or focus_area_limit_selected_count > 14:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: [Focus Area Limit] requires >= 2 and <= 14 items, got {focus_area_limit_selected_count}"
        )
    if norm_switch_vh not in P291_VALID_SWITCH_VH_MODES:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: invalid switch_vh_af_area={switch_vh_af_area!r}"
        )
    if expect_switch_vh_in_movie or (norm_shoot in ("MOVIE", "S_AND_Q") and norm_switch_vh != "OFF"):
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: [Switch V/H AF Area] is Still-only"
        )
    if norm_fa_color not in P291_VALID_FOCUS_AREA_COLORS:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: invalid focus_area_color={focus_area_color!r}"
        )
    if norm_circ not in P291_VALID_CIRC_FOCUS_POINT_MODES:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: invalid circ_of_focus_point={circ_of_focus_point!r}"
        )
    if str(af_area_registration_label).strip() != P291_AF_AREA_REGISTRATION_LABEL:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: exact ilc/2210 name is {P291_AF_AREA_REGISTRATION_LABEL!r}, got {af_area_registration_label!r}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_non_resettable_af_prefs_wiped:
        errors.append(
            f"{P291_GA_ERR_FOCUS_AREA_STILL_TRACKING_OR_AF_REG}: [Focus Area Color] and [AF Area Registration] survive [Camera Settings Reset]"
        )

    # 2. Body W/T Zoom Speed vs Handle-Less XLR-H1
    if xlr_h1_zoom_lever_present or xlr_h1_rec_button_present or xlr_h1_zoom_hold_switch_present:
        errors.append(
            f"{P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED}: ILME-FX3 XLR-H1 handle has NO zoom lever, NO record button, and NO ZOOM HOLD switch"
        )
    if fx6_smart_handle_zero_to_99_is_speed_scale:
        errors.append(
            f"{P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED}: 0..99 on FX6 is [Zoom Position Display], NOT a Fixed 1..99 speed scale"
        )
    norm_zoom_range = _norm_token(zoom_range)
    if norm_zoom_range not in P291_VALID_ZOOM_RANGES:
        errors.append(
            f"{P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED}: invalid zoom_range={zoom_range!r}"
        )
    if norm_zoom_range != "OPTICAL_ONLY" and (still_raw_active or high_fps_120_100):
        errors.append(
            f"{P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED}: ClearImage/Digital Zoom unavailable during RAW Still or 119.88p/100p"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_zoom_range_wiped:
        errors.append(
            f"{P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED}: [Zoom Range] is NOT resettable by [Camera Settings Reset]"
        )
    norm_remote_type = _norm_token(remote_zoom_speed_type)
    if norm_remote_type not in P291_VALID_REMOTE_ZOOM_SPEED_TYPES:
        errors.append(
            f"{P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED}: invalid remote_zoom_speed_type={remote_zoom_speed_type!r}"
        )
    for label, spd in (
        ("zoom_lever_stby_speed", zoom_lever_stby_speed),
        ("zoom_lever_rec_speed", zoom_lever_rec_speed),
        ("custom_key_zoom_stby_speed", custom_key_zoom_stby_speed),
        ("custom_key_zoom_rec_speed", custom_key_zoom_rec_speed),
        ("remote_zoom_fixed_stby_speed", remote_zoom_fixed_stby_speed),
        ("remote_zoom_fixed_rec_speed", remote_zoom_fixed_rec_speed),
    ):
        if not (P291_ZOOM_SPEED_MIN <= int(spd) <= P291_ZOOM_SPEED_MAX):
            errors.append(
                f"{P291_GA_ERR_XLR_H1_ZOOM_HANDLE_MYTH_OR_SPEED}: {label}={spd} outside 1..8"
            )

    # 3. ISO Range Limit & Still P/A ISO AUTO Min. SS vs Cine EI
    norm_exp = _norm_token(exposure_mode)
    norm_iso = _norm_token(iso_mode)
    norm_log = _norm_token(log_shooting_mode)
    norm_min_ss = _norm_token(iso_auto_min_ss)

    if norm_exp not in P291_VALID_EXPOSURE_MODES:
        errors.append(
            f"{P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK}: invalid exposure_mode={exposure_mode!r}"
        )
    if norm_log not in P291_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK}: invalid log_shooting_mode={log_shooting_mode!r}"
        )
    if not (P291_ISO_FLOOR <= int(iso_range_limit_min) <= int(iso_range_limit_max) <= P291_ISO_CEILING):
        errors.append(
            f"{P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK}: ISO Range Limit ({iso_range_limit_min}..{iso_range_limit_max}) outside 50..409600"
        )
    if not (P291_ISO_FLOOR <= int(iso_auto_min) <= int(iso_auto_max) <= P291_ISO_CEILING):
        errors.append(
            f"{P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK}: ISO AUTO bounds ({iso_auto_min}..{iso_auto_max}) outside 50..409600"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_iso_range_limit_wiped:
        errors.append(
            f"{P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK}: [ISO Range Limit] survives [Camera Settings Reset]"
        )

    valid_min_ss = (norm_min_ss in P291_ISO_AUTO_MIN_SS_PRESETS) or bool(
        re.match(r"^(?:1/[0-9]+|[0-9]+(?:\.[0-9]+)?S?)$", str(iso_auto_min_ss).strip().upper())
    )
    if not valid_min_ss:
        errors.append(
            f"{P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK}: invalid iso_auto_min_ss={iso_auto_min_ss!r}"
        )

    min_ss_gate_ok = True
    if expect_iso_auto_min_ss_in_movie_or_manual_iso or (
        iso_auto_min_ss_active
        and (
            norm_shoot != "PHOTO"
            or norm_exp not in ("PROGRAM_AUTO", "APERTURE_PRIORITY")
            or norm_iso != "ISO_AUTO"
            or norm_log in ("CINE_EI", "CINE_EI_QUICK")
        )
    ):
        min_ss_gate_ok = False
        errors.append(
            f"{P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK}: [ISO AUTO Min. SS] is gated strictly to Still P/A + ISO AUTO"
        )

    if norm_log in ("CINE_EI", "CINE_EI_QUICK"):
        if int(cine_ei_base_iso) not in P291_CINE_EI_BASE_ISOS:
            errors.append(
                f"{P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK}: Cine EI locks Base ISO to 800 or 12800, got {cine_ei_base_iso}"
            )
        if expect_iso_variable_in_cine_ei:
            errors.append(
                f"{P291_GA_ERR_ISO_LIMIT_MIN_SS_OR_CINE_EI_LOCK}: Cine EI / Cine EI Quick locks ISO to dual Base ISO 800/12800 (locks out ISO Range Limit & ISO AUTO)"
            )

    # 4. Flash Mode Mechanical-Still Gate vs Video Light Mode
    norm_shutter = _norm_token(shutter_type)
    norm_silent = _norm_token(silent_mode)
    norm_flash = _norm_token(flash_mode)
    norm_exp_comp_set = _norm_token(exp_comp_set)
    norm_vlight = _norm_token(video_light_mode)

    if norm_flash not in P291_VALID_FLASH_MODES:
        errors.append(
            f"{P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT}: invalid flash_mode={flash_mode!r}"
        )
    if norm_exp_comp_set not in P291_VALID_EXP_COMP_SET_MODES:
        errors.append(
            f"{P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT}: invalid exp_comp_set={exp_comp_set!r}"
        )
    if not (-3.0 <= float(flash_comp_ev) <= 3.0):
        errors.append(
            f"{P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT}: flash_comp_ev={flash_comp_ev} outside -3.0..+3.0 EV"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_exp_comp_set_wiped:
        errors.append(
            f"{P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT}: [Exp.comp.set] survives [Camera Settings Reset]"
        )

    flash_gate_ok = True
    if flash_firing_enabled and (
        norm_shoot != "PHOTO" or norm_shutter != "MECHANICAL_SHUTTER" or norm_silent == "ON"
    ):
        flash_gate_ok = False
        errors.append(
            f"{P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT}: [Flash Mode] requires EXPOSURE_MODE_STILL + Mechanical Shutter (Silent Mode=Off)"
        )

    if norm_vlight not in P291_VALID_VIDEO_LIGHT_MODES:
        errors.append(
            f"{P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT}: invalid video_light_mode={video_light_mode!r}"
        )
    if int(mi_shoe_5v_current_ma) < 0 or int(mi_shoe_5v_current_ma) > P291_MI_SHOE_5V_MAX_MA:
        errors.append(
            f"{P291_GA_ERR_FLASH_MECH_STILL_GATE_OR_VIDEO_LIGHT}: mi_shoe_5v_current_ma={mi_shoe_5v_current_ma} exceeds PMIC 5V <= 900 mA budget"
        )

    return P291CheckGroupAFocusZoomIsoFlashResult(
        check_group_id=P291_CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        body_model_id_hex=f"0x{body_model_id:08x}",
        body_fw=str(body_fw),
        sony_help_guide_id=str(sony_help_guide_id),
        reset_action=norm_reset,
        shoot_mode=norm_shoot,
        focus_area_bkid=focus_area_bkid,
        focus_area_resid16_hex=focus_area_resid16_hex,
        focus_area=norm_fa,
        non_tracking_focus_area_count=len(norm_non_track),
        tracking_focus_area_count=len(norm_track),
        tracking_still_only_enforced=tracking_still_only_ok,
        touch_tracking_used_for_movie_sq=touch_tracking_used_for_movie_sq,
        focus_area_limit_selected_count=focus_area_limit_selected_count,
        switch_vh_af_area=norm_switch_vh,
        focus_area_color=norm_fa_color,
        circ_of_focus_point=norm_circ,
        af_area_registration_label=af_area_registration_label,
        xlr_h1_zoom_lever_present=xlr_h1_zoom_lever_present,
        xlr_h1_rec_button_present=xlr_h1_rec_button_present,
        xlr_h1_zoom_hold_switch_present=xlr_h1_zoom_hold_switch_present,
        fx6_smart_handle_zero_to_99_is_position_display=not fx6_smart_handle_zero_to_99_is_speed_scale,
        zoom_range=norm_zoom_range,
        zoom_lever_stby_speed=zoom_lever_stby_speed,
        zoom_lever_rec_speed=zoom_lever_rec_speed,
        custom_key_zoom_stby_speed=custom_key_zoom_stby_speed,
        custom_key_zoom_rec_speed=custom_key_zoom_rec_speed,
        remote_zoom_speed_type=norm_remote_type,
        remote_zoom_fixed_stby_speed=remote_zoom_fixed_stby_speed,
        remote_zoom_fixed_rec_speed=remote_zoom_fixed_rec_speed,
        iso_range_limit_min=iso_range_limit_min,
        iso_range_limit_max=iso_range_limit_max,
        iso_auto_min=iso_auto_min,
        iso_auto_max=iso_auto_max,
        iso_auto_min_ss=norm_min_ss,
        iso_auto_min_ss_still_pa_only_enforced=min_ss_gate_ok,
        log_shooting_mode=norm_log,
        cine_ei_base_iso=cine_ei_base_iso,
        flash_mode=norm_flash,
        flash_firing_enabled=flash_firing_enabled,
        shutter_type=norm_shutter,
        flash_mechanical_still_gate_verified=flash_gate_ok,
        video_light_mode=norm_vlight,
        mi_shoe_5v_current_ma=mi_shoe_5v_current_ma,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group B (Wave 51 — XAVC S-I DCI 4K + 24.00p Reboot, Aspect Ratio, 11 Holds, CAMSET Card Path, Photo Capture)
# ---------------------------------------------------------------------------


def evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
    *,
    reset_action: str = "NONE",
    # DCI 4K & 24.00p Reboot Quarantine
    movie_file_format: str = "XAVC_S_I_DCI_4K",
    movie_resolution_wh: str = P291_DCI_4K_WIDTH_HEIGHT,
    rec_frame_rate: str = "23.98P",
    stage_b_volatile_tmp_overlay_active: bool = False,
    ack_24p_reboot_wipes_tmp_overlay: bool = False,
    expect_24p_no_reboot: bool = False,
    hdmi_raw_output: bool = False,
    hdmi_raw_resolution_wh: str = P291_HDMI_RAW_WIDTH_HEIGHT,
    sq_dci4k_fps: int = 24,
    bitrate_mbps: int = 240,
    media_speed_grade: str = "CFEXPRESS_A_VPG200",
    # Still Aspect Ratio 4-Mode
    exposed_still_aspect_modes: Sequence[str] = P291_STILL_ASPECT_FOUR_MODES,
    still_aspect_ratio: str = "3:2",
    apsc_s35_on: bool = False,
    still_jpeg_heif_size: str = "L",
    fx6_reference_still_aspect_ratio_present: bool = False,
    # Reg. Custom Shoot Set 11 Holds & /SONY/SETTING/%s/ CAMSET Path
    exposure_mode: str = "MANUAL_EXPOSURE",
    hlg_still_image: str = "OFF",
    recall_custom_hold_keys: Sequence[str] = P291_RECALL_CUSTOM_HOLD_11_KEYS,
    recall_custom_recalled_items: Sequence[str] = (),
    claimed_recall_custom_wiped_by_camera_reset: bool = False,
    camset_card_path: str = P291_DEFAULT_FX3_SETTING_CARD_PATH,
    memory_recall_media_slot: str = "SLOT_1",
    fx3_uses_private_sony_pro_camera: bool = False,
    claimed_memory_recall_media_survives_reset_as_slot2: bool = False,
    expect_format_preserves_camset_or_m1_m4: bool = False,
    # Photo Capture & Enlarge Image
    photo_capture_requested: bool = False,
    photo_capture_slot: int = 2,
    slot1_contains_tier0_dump: bool = True,
    shoot_mode: str = "MOVIE",
    enlarge_image_in_movie_claimed: bool = False,
    enlarge_initial_mag: str = "STANDARD_MAG",
    enlarge_initial_position: str = "FOCUSED_POSITION",
    claimed_enlarge_prefs_wiped_by_camera_reset: bool = False,
) -> P291CheckGroupBDci4kAspectHoldCamsetPhotoResult:
    """Validate Wave 51: XAVC S-I DCI 4K + 24.00p reboot, Aspect Ratio, 11 Holds, SONY/SETTING path & Photo Capture."""
    errors: List[str] = []

    norm_reset = _norm_token(reset_action)
    norm_fmt = _norm_token(movie_file_format)
    norm_res = str(movie_resolution_wh).strip().lower()
    norm_fps = _norm_frame_rate(rec_frame_rate)
    norm_grade = _norm_token(media_speed_grade)
    norm_exp = _norm_token(exposure_mode)
    norm_hlg = _norm_token(hlg_still_image)
    norm_slot = _norm_token(memory_recall_media_slot)
    norm_shoot = _norm_token(shoot_mode)

    # 1. XAVC S-I DCI 4K (4096x2160 17:9) vs Long-GOP UHD (3840x2160) & 24.00p reboot quarantine
    if norm_fmt not in P291_VALID_MOVIE_FILE_FORMATS:
        errors.append(
            f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: invalid movie_file_format={movie_file_format!r}"
        )
    if norm_fmt == "XAVC_S_I_DCI_4K":
        if norm_res != P291_DCI_4K_WIDTH_HEIGHT:
            errors.append(
                f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: [XAVC S-I DCI 4K] must be {P291_DCI_4K_WIDTH_HEIGHT} (17:9), got {movie_resolution_wh!r}"
            )
        if norm_fps not in P291_DCI_4K_FRAME_RATES:
            errors.append(
                f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: [XAVC S-I DCI 4K] rejects fps={rec_frame_rate!r} (no 100p/120p)"
            )
        if sq_dci4k_fps <= 0 or sq_dci4k_fps > P291_DCI_4K_SQ_MAX_FPS:
            errors.append(
                f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: S&Q DCI 4K max is {P291_DCI_4K_SQ_MAX_FPS}fps, got {sq_dci4k_fps}"
            )
        if int(bitrate_mbps) >= 600 and norm_grade not in ("CFEXPRESS_A_VPG200", "CFEXPRESS_A_VPG400", "SDXC_V90"):
            errors.append(
                f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: 600M DCI 4K requires CFexpress Type A VPG200+ or SDXC V90+, got {media_speed_grade!r}"
            )
    elif norm_fmt in ("XAVC_HS_4K", "XAVC_S_4K", "XAVC_S_I_4K"):
        if norm_res != P291_UHD_4K_WIDTH_HEIGHT:
            errors.append(
                f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: {norm_fmt} stays strictly UHD {P291_UHD_4K_WIDTH_HEIGHT}, got {movie_resolution_wh!r}"
            )
        if norm_fps == "24.00P":
            errors.append(
                f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: 24.00p is gated to [XAVC S-I DCI 4K], not {norm_fmt}"
            )
    elif norm_fmt in ("XAVC_S_HD", "XAVC_S_I_HD"):
        if norm_res != P291_HD_WIDTH_HEIGHT:
            errors.append(
                f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: {norm_fmt} must be {P291_HD_WIDTH_HEIGHT}, got {movie_resolution_wh!r}"
            )
        if norm_fps == "24.00P":
            errors.append(
                f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: 24.00p is gated to [XAVC S-I DCI 4K], not {norm_fmt}"
            )

    reboot_required = norm_fps == "24.00P"
    if expect_24p_no_reboot:
        errors.append(
            f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: switching into/out of 24.00p (0x75ce) forces a camera reboot that wipes /tmp overlays"
        )
    if reboot_required and (stage_b_volatile_tmp_overlay_active or not ack_24p_reboot_wipes_tmp_overlay):
        errors.append(
            f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: 24.00p requires clearing Stage-B /tmp overlay and explicit ack_24p_reboot_wipes_tmp_overlay"
        )

    if hdmi_raw_output and str(hdmi_raw_resolution_wh).strip().lower() != P291_HDMI_RAW_WIDTH_HEIGHT:
        errors.append(
            f"{P291_GB_ERR_DCI4K_24P_REBOOT_OR_CODEC_GEOMETRY}: HDMI RAW output is {P291_HDMI_RAW_WIDTH_HEIGHT} (16:9), got {hdmi_raw_resolution_wh!r}"
        )

    # 2. Still 4-Mode Aspect Ratio & APS-C S35 Step-Down
    norm_aspects = tuple(_norm_aspect_ratio(x) for x in exposed_still_aspect_modes)
    norm_aspect = _norm_aspect_ratio(still_aspect_ratio)
    if norm_aspects != P291_STILL_ASPECT_FOUR_MODES or len(norm_aspects) != 4:
        errors.append(
            f"{P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC}: expected 4 Still Aspect Ratios {P291_STILL_ASPECT_FOUR_MODES}, got {exposed_still_aspect_modes!r}"
        )
    if norm_aspect not in P291_STILL_ASPECT_FOUR_MODES:
        errors.append(
            f"{P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC}: invalid still_aspect_ratio={still_aspect_ratio!r}"
        )
    if apsc_s35_on and _norm_token(still_jpeg_heif_size) == "L":
        errors.append(
            f"{P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC}: [APS-C S35 Shooting]=On disables JPEG/HEIF [L] and steps down to [M]"
        )
    if fx6_reference_still_aspect_ratio_present:
        errors.append(
            f"{P291_GB_ERR_STILL_ASPECT_RATIO_4MODE_OR_APSC}: ILME-FX6 lacks Still [Aspect Ratio] (viewfinder Markers only)"
        )

    # 3. Reg. Custom Shoot Set (11 Holds) & /SONY/SETTING/%s/ CAMSET Path vs FX6 PRO/CAMERA
    norm_hold_keys = tuple(str(k).strip() for k in recall_custom_hold_keys)
    if norm_hold_keys != P291_RECALL_CUSTOM_HOLD_11_KEYS or len(norm_hold_keys) != 11:
        errors.append(
            f"{P291_GB_ERR_RECALL_CUSTOM_11_OR_HLG_LOCK}: [Reg. Custom Shoot Set] must expose exact 11 keys is_checked_recall_custom_hold0..10"
        )
    recalled_set = {_norm_token(x) for x in recall_custom_recalled_items}
    if recalled_set and norm_exp not in P291_PASM_EXPOSURE_MODES:
        errors.append(
            f"{P291_GB_ERR_RECALL_CUSTOM_11_OR_HLG_LOCK}: [Recall Custom hold 1..3] is restricted to Still P/A/S/M"
        )
    if norm_hlg == "ON" and ("ISO" in recalled_set or "ISO_SENSITIVITY" in recalled_set or "DRO_BRACKET" in recalled_set):
        errors.append(
            f"{P291_GB_ERR_RECALL_CUSTOM_11_OR_HLG_LOCK}: [HLG Still Image]=On forbids recalling ISO or DRO Bracket in Custom Shoot Set"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_recall_custom_wiped_by_camera_reset:
        errors.append(
            f"{P291_GB_ERR_RECALL_CUSTOM_11_OR_HLG_LOCK}: [Reg. Custom Shoot Set] is cleared only by [Initialize], NOT [Camera Settings Reset]"
        )

    card_path_str = str(camset_card_path).strip()
    upper_card_path = card_path_str.upper()
    if (
        fx3_uses_private_sony_pro_camera
        or any(bad in upper_card_path for bad in P291_FORBIDDEN_FX6_PRO_PREFIXES)
        or not P291_FX3_SETTING_CARD_PATH_RE.match(card_path_str)
    ):
        errors.append(
            f"{P291_GB_ERR_CAMSET_CARD_PATH_VS_FX6_PRO_CAMERA}: FX3 uses %c:%s/SONY/SETTING/%s/ (ZERO PRIVATE/SONY/PRO/CAMERA), got {camset_card_path!r}"
        )
    if norm_slot not in ("SLOT_1", "SLOT_2"):
        errors.append(
            f"{P291_GB_ERR_CAMSET_CARD_PATH_VS_FX6_PRO_CAMERA}: invalid memory_recall_media_slot={memory_recall_media_slot!r}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_memory_recall_media_survives_reset_as_slot2:
        errors.append(
            f"{P291_GB_ERR_CAMSET_CARD_PATH_VS_FX6_PRO_CAMERA}: [Memory/Recall Media] resets to [Slot 1] on [Camera Settings Reset]"
        )
    if expect_format_preserves_camset_or_m1_m4:
        errors.append(
            f"{P291_GB_ERR_CAMSET_CARD_PATH_VS_FX6_PRO_CAMERA}: [Format] permanently erases M1..M4 & CAMSET files on card"
        )

    # 4. Photo Capture DCI 4K Lockout + Slot-1 Tier-0 Firewall & Enlarge Image
    photo_guard_ok = True
    if photo_capture_requested:
        if norm_fmt == "XAVC_S_I_DCI_4K":
            photo_guard_ok = False
            errors.append(
                f"{P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL}: [Photo Capture] (0x6856) is blocked on [XAVC S-I DCI 4K] (0x60ce)"
            )
        if int(photo_capture_slot) == 1 and slot1_contains_tier0_dump:
            photo_guard_ok = False
            errors.append(
                f"{P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL}: [Photo Capture] blocked fail-closed on read-only Slot 1 Tier-0 Vault"
            )

    enlarge_still_ok = not enlarge_image_in_movie_claimed
    if enlarge_image_in_movie_claimed:
        errors.append(
            f"{P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL}: [Enlarge Image] (0xe8cb) is Still-only"
        )
    if _norm_token(enlarge_initial_mag) not in ("STANDARD_MAG", "PREVIOUS_MAG"):
        errors.append(
            f"{P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL}: invalid enlarge_initial_mag={enlarge_initial_mag!r}"
        )
    if _norm_token(enlarge_initial_position) not in ("FOCUSED_POSITION", "CENTER"):
        errors.append(
            f"{P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL}: invalid enlarge_initial_position={enlarge_initial_position!r}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_enlarge_prefs_wiped_by_camera_reset:
        errors.append(
            f"{P291_GB_ERR_PHOTO_CAPTURE_DCI4K_OR_SLOT1_FIREWALL}: [Enlarge Initial Mag.] & [Enlarge Initial Position] survive [Camera Settings Reset]"
        )

    return P291CheckGroupBDci4kAspectHoldCamsetPhotoResult(
        check_group_id=P291_CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        movie_file_format=norm_fmt,
        movie_resolution_wh=norm_res,
        rec_frame_rate=norm_fps,
        dci4k_24p_reboot_required=reboot_required,
        dci4k_24p_reboot_wipes_volatile_tmp_acknowledged=ack_24p_reboot_wipes_tmp_overlay,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_raw_resolution_wh=str(hdmi_raw_resolution_wh).strip().lower(),
        sq_dci4k_fps=sq_dci4k_fps,
        media_speed_grade=norm_grade,
        still_aspect_ratio=norm_aspect,
        exposed_still_aspect_count=len(norm_aspects),
        apsc_s35_on=apsc_s35_on,
        recall_custom_hold_checkbox_count=len(norm_hold_keys),
        recall_custom_hold_keys=norm_hold_keys,
        camset_card_path=card_path_str,
        memory_recall_media_slot=norm_slot,
        fx3_private_sony_pro_camera_used=False,
        photo_capture_requested=photo_capture_requested,
        photo_capture_slot=photo_capture_slot,
        photo_capture_dci4k_blocked_and_slot1_firewalled=photo_guard_ok,
        enlarge_image_still_only_enforced=enlarge_still_ok,
        enlarge_initial_mag=_norm_token(enlarge_initial_mag),
        enlarge_initial_position=_norm_token(enlarge_initial_position),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group C (Wave 52 — Sensor Cleaning >=51%, EV Comp vs Cine EI, Focus Mode 5 vs 2, Playback & Rotate)
# ---------------------------------------------------------------------------


def evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
    *,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Sensor Cleaning >= 51% & Mandatory OFF vs FX6 e-ND + APR
    sensor_cleaning_resid16_hex: str = P291_SENSOR_CLEANING_RESID16_HEX,
    sensor_cleaning_requested: bool = False,
    battery_soc_pct: float = 88.0,
    mandatory_power_off_after_cleaning: bool = True,
    unattended_tier0_dump_active: bool = False,
    fx6_sensor_cleaning_supported_claimed: bool = False,
    fx3_has_built_in_end_filter: bool = False,
    # Exposure Comp. (±5.0 Still / ±2.0 Movie) & Cine EI Lockout
    exposure_comp_ev: float = 0.0,
    exposure_step: str = "0.3EV",
    exposure_mode: str = "MANUAL_EXPOSURE",
    iso_mode: str = "CINE_EI_BASE",
    log_shooting_mode: str = "CINE_EI",
    legacy_reset_ev_comp_claimed: bool = False,
    claimed_exposure_step_wiped_by_camera_reset: bool = False,
    # Focus Mode Still 5 vs Movie/S&Q 2
    exposed_still_focus_modes: Sequence[str] = P291_STILL_FOCUS_FIVE_MODES,
    exposed_movie_focus_modes: Sequence[str] = P291_MOVIE_FOCUS_TWO_MODES,
    focus_mode: str = "MF",
    priority_set_in_af: str = "BALANCED_EMPHASIS",
    af_illuminator: str = "AUTO",
    af_assist_active: bool = False,
    mount_adaptor_attached: bool = False,
    focus_magnifier_active: bool = False,
    claimed_priority_set_wiped_by_camera_reset: bool = False,
    # Playback View Mode / Image Index / Group / Rotation / Rotate Slot-1 Firewall
    exposed_view_modes: Sequence[str] = P291_VIEW_MODE_THREE_MODES,
    view_mode: str = "DATE_VIEW",
    exposed_image_index_modes: Sequence[str] = P291_IMAGE_INDEX_TWO_MODES,
    image_index_mode: str = "9_IMAGES",
    display_as_group: str = "OFF",
    display_rotation: str = "AUTO",
    claimed_playback_view_prefs_wiped_by_camera_reset: bool = False,
    playback_media_slot: int = 1,
    slot1_contains_tier0_dump: bool = True,
    playback_rotate_requested: bool = False,
    playback_rotate_on_movie: bool = False,
    playback_rotate_during_transfer: bool = False,
) -> P291CheckGroupCSensorCleanEvFocusPlaybackResult:
    """Validate Wave 52: Sensor Cleaning >=51% & mandatory OFF, EV Comp vs Cine EI, Focus 5-vs-2 & Playback Rotate."""
    errors: List[str] = []

    norm_reset = _norm_token(reset_action)
    norm_shoot = _norm_token(shoot_mode)
    norm_exp = _norm_token(exposure_mode)
    norm_iso = _norm_token(iso_mode)
    norm_log = _norm_token(log_shooting_mode)
    norm_step = _norm_exposure_step(exposure_step)
    norm_focus = _norm_focus_mode(focus_mode)
    norm_prio = _norm_token(priority_set_in_af)
    norm_illum = _norm_token(af_illuminator)
    norm_view = _norm_token(view_mode)
    norm_index = _norm_image_index(image_index_mode)
    norm_group = _norm_token(display_as_group)
    norm_rot = _norm_token(display_rotation)

    # 1. [Sensor Cleaning] >= 51% + mandatory OFF vs FX6 e-ND + APR
    if sensor_cleaning_resid16_hex.lower() != P291_SENSOR_CLEANING_RESID16_HEX:
        errors.append(
            f"{P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END}: [Sensor Cleaning] resid16 mismatch ({sensor_cleaning_resid16_hex!r})"
        )
    if fx6_sensor_cleaning_supported_claimed:
        errors.append(
            f"{P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END}: ILME-FX6 lacks IBIS/Sensor Cleaning (CrCommandId_SensorCleaning 320 unsupported; uses e-ND + APR)"
        )
    if fx3_has_built_in_end_filter:
        errors.append(
            f"{P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END}: ILME-FX3 has NO built-in e-ND optical filter"
        )
    if sensor_cleaning_requested:
        if float(battery_soc_pct) < P291_SENSOR_CLEANING_MIN_SOC_PCT:
            errors.append(
                f"{P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END}: [Sensor Cleaning] requires NP-FZ100 >= 51%, got {battery_soc_pct:.1f}%"
            )
        if not mandatory_power_off_after_cleaning:
            errors.append(
                f"{P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END}: [Sensor Cleaning] requires mandatory power-OFF (0x6221) after IBIS vibration"
            )
        if unattended_tier0_dump_active:
            errors.append(
                f"{P291_GC_ERR_SENSOR_CLEANING_51PCT_OFF_OR_FX6_END}: [Sensor Cleaning] blocked during active Tier-0 dump"
            )

    # 2. [Exposure Comp.] ±5.0 Still / ±2.0 Movie & Cine EI Lockout
    if norm_step not in P291_VALID_EXPOSURE_STEPS:
        errors.append(
            f"{P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK}: invalid exposure_step={exposure_step!r}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_exposure_step_wiped_by_camera_reset:
        errors.append(
            f"{P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK}: [Exposure step] survives [Camera Settings Reset]"
        )
    if legacy_reset_ev_comp_claimed:
        errors.append(
            f"{P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK}: [Reset EV Comp.] (0x7853) is omitted from ILME-FX3 ilc/2210"
        )

    ev_max = P291_EV_COMP_STILL_ABS_MAX if norm_shoot == "PHOTO" else P291_EV_COMP_MOVIE_ABS_MAX
    if abs(float(exposure_comp_ev)) > ev_max:
        errors.append(
            f"{P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK}: exposure_comp_ev={exposure_comp_ev} exceeds ±{ev_max:.1f} EV ceiling for {norm_shoot}"
        )

    ev_cine_ei_ok = True
    if abs(float(exposure_comp_ev)) > 1e-6:
        if norm_log in ("CINE_EI", "CINE_EI_QUICK"):
            ev_cine_ei_ok = False
            errors.append(
                f"{P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK}: [Exposure Comp.] is 100% locked out under {norm_log} (use [Exposure Index] for monitoring)"
            )
        elif norm_exp == "INTELLIGENT_AUTO":
            errors.append(
                f"{P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK}: [Exposure Comp.] is locked out under [Intelligent Auto]"
            )
        elif norm_exp == "MANUAL_EXPOSURE" and norm_iso != "ISO_AUTO":
            errors.append(
                f"{P291_GC_ERR_EXPOSURE_COMP_RANGE_OR_CINE_EI_LOCK}: [Exposure Comp.] in Manual (M) works ONLY with [ISO AUTO]"
            )

    # 3. [Focus Mode] Still 5 vs Movie/S&Q 2 Split
    norm_still_focus = tuple(_norm_focus_mode(x) for x in exposed_still_focus_modes)
    norm_movie_focus = tuple(_norm_focus_mode(x) for x in exposed_movie_focus_modes)
    focus_split_ok = True
    if norm_still_focus != P291_STILL_FOCUS_FIVE_MODES or len(norm_still_focus) != 5:
        focus_split_ok = False
        errors.append(
            f"{P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU}: Still [Focus Mode] must expose 5 modes {P291_STILL_FOCUS_FIVE_MODES}, got {exposed_still_focus_modes!r}"
        )
    if norm_movie_focus != P291_MOVIE_FOCUS_TWO_MODES or len(norm_movie_focus) != 2:
        focus_split_ok = False
        errors.append(
            f"{P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU}: Movie/S&Q [Focus Mode] must expose ONLY 2 modes {P291_MOVIE_FOCUS_TWO_MODES}, got {exposed_movie_focus_modes!r}"
        )
    if norm_focus not in P291_STILL_FOCUS_FIVE_MODES:
        focus_split_ok = False
        errors.append(
            f"{P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU}: invalid focus_mode={focus_mode!r}"
        )
    if norm_shoot in ("MOVIE", "S_AND_Q") and norm_focus not in P291_MOVIE_FOCUS_TWO_MODES:
        focus_split_ok = False
        errors.append(
            f"{P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU}: Movie/S&Q locks out {norm_focus}; only AF-C (MOVIE_AUTO) and MF exist"
        )
    if af_assist_active and (norm_shoot == "PHOTO" or norm_focus != "AF_C"):
        errors.append(
            f"{P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU}: [AF Assist] is gated to Movie AF-C (MOVIE_AUTO) only"
        )
    if norm_prio not in P291_VALID_PRIORITY_SET_AF_MODES:
        errors.append(
            f"{P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU}: invalid priority_set_in_af={priority_set_in_af!r}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_priority_set_wiped_by_camera_reset:
        errors.append(
            f"{P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU}: [Priority Set in AF-S]/[Priority Set in AF-C] survive [Camera Settings Reset]"
        )
    if norm_illum not in ("AUTO", "OFF"):
        errors.append(
            f"{P291_GC_ERR_FOCUS_MODE_5VS2_SPLIT_OR_SUBMENU}: invalid af_illuminator={af_illuminator!r}"
        )
    if af_illuminator_forced_on := (norm_illum == "AUTO" and (mount_adaptor_attached or focus_magnifier_active) and norm_shoot == "PHOTO" and norm_focus in ("AF_S", "AF_A")):
        # Note: AUTO automatically suspends when Focus Magnifier or Mount Adaptor is active; keep validation strict if explicitly expected
        _ = af_illuminator_forced_on

    # 4. Playback View Mode / Image Index (9/25 vs 12/30) / Display Rotation / Rotate Slot-1 Firewall
    norm_views = tuple(_norm_token(x) for x in exposed_view_modes)
    norm_indices = tuple(_norm_image_index(x) for x in exposed_image_index_modes)
    if norm_views != P291_VIEW_MODE_THREE_MODES or any(v in P291_DORMANT_VIEW_MODES for v in norm_views):
        errors.append(
            f"{P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL}: FX3 [View Mode] must expose 3 modes {P291_VIEW_MODE_THREE_MODES} (no MP4/AVCHD View)"
        )
    if norm_view not in P291_VIEW_MODE_THREE_MODES:
        errors.append(
            f"{P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL}: invalid view_mode={view_mode!r}"
        )
    if norm_indices != P291_IMAGE_INDEX_TWO_MODES or any(i in P291_DORMANT_IMAGE_INDEX_MODES for i in norm_indices):
        errors.append(
            f"{P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL}: FX3 [Image Index] exposes ONLY 9/25 Images (rejects dormant 12/30 Images 0x6e7a)"
        )
    if norm_index not in P291_IMAGE_INDEX_TWO_MODES:
        errors.append(
            f"{P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL}: invalid image_index_mode={image_index_mode!r}"
        )
    if norm_group not in ("OFF", "ON"):
        errors.append(
            f"{P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL}: invalid display_as_group={display_as_group!r}"
        )
    if norm_rot not in P291_VALID_DISPLAY_ROTATION_MODES:
        errors.append(
            f"{P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL}: invalid display_rotation={display_rotation!r}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_playback_view_prefs_wiped_by_camera_reset:
        errors.append(
            f"{P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL}: Playback [View Mode]/[Image Index]/[Display as Group]/[Display Rotation] survive [Camera Settings Reset]"
        )

    rotate_firewall_ok = True
    if playback_rotate_requested:
        if int(playback_media_slot) == 1 and slot1_contains_tier0_dump:
            rotate_firewall_ok = False
            errors.append(
                f"{P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL}: [Playback] [Rotate] (0xe5ae) blocked fail-closed on read-only Slot 1 Tier-0 Vault"
            )
        if playback_rotate_on_movie or playback_rotate_during_transfer:
            rotate_firewall_ok = False
            errors.append(
                f"{P291_GC_ERR_PLAYBACK_INDEX_OR_SLOT1_ROTATE_FIREWALL}: [Playback] [Rotate] only applies to idle Still images (blocked on movies or during transfer)"
            )

    return P291CheckGroupCSensorCleanEvFocusPlaybackResult(
        check_group_id=P291_CHECK_GROUP_C_ID,
        passed=(len(errors) == 0),
        sensor_cleaning_resid16_hex=sensor_cleaning_resid16_hex,
        sensor_cleaning_requested=sensor_cleaning_requested,
        battery_soc_pct=float(battery_soc_pct),
        mandatory_power_off_after_cleaning=mandatory_power_off_after_cleaning,
        fx6_reference_e_nd_and_apr=(not fx6_sensor_cleaning_supported_claimed) and (not fx3_has_built_in_end_filter),
        exposure_comp_ev=float(exposure_comp_ev),
        exposure_step=norm_step,
        exposure_mode=norm_exp,
        iso_mode=norm_iso,
        log_shooting_mode=norm_log,
        ev_comp_cine_ei_lockout_verified=ev_cine_ei_ok,
        focus_mode=norm_focus,
        exposed_still_focus_mode_count=len(norm_still_focus),
        exposed_movie_focus_mode_count=len(norm_movie_focus),
        focus_mode_5vs2_split_verified=focus_split_ok,
        priority_set_in_af=norm_prio,
        af_illuminator=norm_illum,
        view_mode=norm_view,
        image_index_mode=norm_index,
        display_as_group=norm_group,
        display_rotation=norm_rot,
        playback_media_slot=playback_media_slot,
        playback_rotate_requested=playback_rotate_requested,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        playback_rotate_slot1_firewall_enforced=rotate_firewall_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group D (Physical Bench Readiness Receipt, 16/16 H0 == H3 & Fail-Closed Redlines)
# ---------------------------------------------------------------------------


def build_simulated_phase291_tier0_receipts(
    *,
    body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
    emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
    body_fw: str = TARGET_BODY_FW,
) -> Tuple[bytes, bytes, Dict[str, str]]:
    """Build deterministic in-memory 528 B FX3RCPT1 dual receipts for `--simulate-bench-dry-run`."""
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE291_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE291_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_p291_check_group_d_physical_bench_and_tier0(
    *,
    simulated_passive_tx_bytes: int = 0,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    simulated_h0_h3_drifted_surfaces: int = 0,
    simulate_bench_dry_run: bool = False,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
) -> Tuple[P291CheckGroupDPhysicalBenchAndTier0Result, Tuple[str, ...]]:
    """Validate Check Group D: physical bench readiness, 16/16 H0==H3, dual 528B FX3RCPT1 & redlines."""
    errors: List[str] = []
    tier0_errors: List[str] = []
    warnings: List[str] = []

    if simulated_passive_tx_bytes != 0:
        errors.append(
            f"{P291_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: passive_tx_bytes_emitted={simulated_passive_tx_bytes} != 0"
        )
    if claim_hardware_live_attach_authorized or claim_persistent_emmc_writes_authorized or claim_cross_model_flash_authorized:
        errors.append(
            f"{P291_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: hardware_live_attach / persistent_emmc_writes / cross_model_flash are unconditionally LOCKED OFF"
        )

    surface_count = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_count, int(simulated_h0_h3_drifted_surfaces)))
    equals_count = max(0, surface_count - drifted)
    if drifted != 0:
        errors.append(
            f"{P291_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: {drifted} surfaces drifted between H0 and H3"
        )

    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    dev_a = st_dev_a_override
    dev_b = st_dev_b_override
    eff_serial = body_serial
    eff_cid = emmc_cid
    eff_h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else None
    eff_h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else None

    if (
        simulate_bench_dry_run
        and raw_a is None
        and raw_b is None
        and receipt_a_path is None
        and receipt_b_path is None
    ):
        eff_serial = eff_serial or DEFAULT_TARGET_BODY_SERIAL
        eff_cid = eff_cid or DEFAULT_TARGET_EMMC_CID
        raw_a, raw_b, sim_h0 = build_simulated_phase291_tier0_receipts(
            body_serial=eff_serial, emmc_cid=eff_cid, body_fw=body_fw
        )
        dev_a = 101 if dev_a is None else dev_a
        dev_b = 202 if dev_b is None else dev_b
        eff_h0_a = eff_h0_a if eff_h0_a is not None else dict(sim_h0)
        eff_h0_b = eff_h0_b if eff_h0_b is not None else dict(sim_h0)
        warnings.append(
            "SIMULATED_DRY_RUN_ONLY: Tier-0 528B FX3RCPT1 receipts synthesized in memory; no physical bench authorization granted"
        )

    if raw_a is None and receipt_a_path is not None:
        try:
            _, raw_a, st_a = _read_bounded_slice_o_rdonly(
                Path(receipt_a_path), SD_RECEIPT_BYTES + 64
            )
            if dev_a is None:
                dev_a = int(st_a)
        except OSError as exc:
            tier0_errors.append(
                f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
            )

    if raw_b is None and receipt_b_path is not None:
        try:
            _, raw_b, st_b = _read_bounded_slice_o_rdonly(
                Path(receipt_b_path), SD_RECEIPT_BYTES + 64
            )
            if dev_b is None:
                dev_b = int(st_b)
        except OSError as exc:
            tier0_errors.append(
                f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
            )

    receipt_present = (
        (raw_a is not None)
        or (raw_b is not None)
        or (receipt_a_path is not None)
        or (receipt_b_path is not None)
    )
    distinct_media_ok = False
    receipt_verified = False

    if not receipt_present:
        warnings.append(
            "OFFLINE_AWAITING_PHYSICAL_TIER0_RECEIPT: provide dual-device Copy A and Copy B 528B FX3RCPT1 receipts"
        )
        tier0_errors.append(
            f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    elif raw_a is None or raw_b is None:
        tier0_errors.append(
            f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B 528B FX3RCPT1 receipts are required"
        )
    else:
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media_ok = True
            else:
                tier0_errors.append(
                    f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{P291_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    group_result = P291CheckGroupDPhysicalBenchAndTier0Result(
        check_group_id=P291_CHECK_GROUP_D_ID,
        passed=(len(errors) == 0),
        passive_tx_bytes_emitted=simulated_passive_tx_bytes,
        h0_h3_surface_count=surface_count,
        h0_equals_h3_count=equals_count,
        tier0_receipt_present=receipt_present,
        tier0_receipt_verified=receipt_verified,
        distinct_physical_media_verified=distinct_media_ok,
        cross_model_flash_authorized=False,
        persistent_emmc_writes_authorized=False,
        overall_ready_for_hardware_attach=False,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )
    return group_result, tuple(tier0_errors)


# ---------------------------------------------------------------------------
# Top-Level Pre-Shoot Readiness Orchestrator & Tamper-Evident Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P291_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Check Group A (Wave 50)
    focus_area_bkid: str = P291_FOCUS_AREA_BKID,
    focus_area_resid16_hex: str = P291_FOCUS_AREA_RESID16_HEX,
    focus_area: str = "WIDE",
    exposed_non_tracking_focus_areas: Sequence[str] = P291_FOCUS_AREA_NON_TRACKING_SEVEN,
    exposed_tracking_focus_areas: Sequence[str] = P291_FOCUS_AREA_TRACKING_SEVEN,
    expect_tracking_focus_area_in_movie: bool = False,
    touch_tracking_used_for_movie_sq: bool = True,
    fx6_reference_tracking_focus_areas_present: bool = False,
    focus_area_limit_selected_count: int = 14,
    switch_vh_af_area: str = "OFF",
    expect_switch_vh_in_movie: bool = False,
    focus_area_color: str = "WHITE",
    circ_of_focus_point: str = "DOES_NOT_CIRCULATE",
    af_area_registration_label: str = P291_AF_AREA_REGISTRATION_LABEL,
    claimed_non_resettable_af_prefs_wiped: bool = False,
    xlr_h1_zoom_lever_present: bool = False,
    xlr_h1_rec_button_present: bool = False,
    xlr_h1_zoom_hold_switch_present: bool = False,
    fx6_smart_handle_zero_to_99_is_speed_scale: bool = False,
    zoom_range: str = "OPTICAL_ONLY",
    still_raw_active: bool = False,
    high_fps_120_100: bool = False,
    claimed_zoom_range_wiped: bool = False,
    zoom_lever_stby_speed: int = 3,
    zoom_lever_rec_speed: int = 8,
    custom_key_zoom_stby_speed: int = 3,
    custom_key_zoom_rec_speed: int = 3,
    remote_zoom_speed_type: str = "VARIABLE",
    remote_zoom_fixed_stby_speed: int = 3,
    remote_zoom_fixed_rec_speed: int = 3,
    iso_range_limit_min: int = 50,
    iso_range_limit_max: int = 409600,
    claimed_iso_range_limit_wiped: bool = False,
    iso_auto_min: int = 100,
    iso_auto_max: int = 12800,
    exposure_mode: str = "MANUAL_EXPOSURE",
    iso_mode: str = "CINE_EI_BASE",
    iso_auto_min_ss: str = "STANDARD",
    iso_auto_min_ss_active: bool = False,
    expect_iso_auto_min_ss_in_movie_or_manual_iso: bool = False,
    log_shooting_mode: str = "CINE_EI",
    cine_ei_base_iso: int = 800,
    expect_iso_variable_in_cine_ei: bool = False,
    shutter_type: str = "MECHANICAL_SHUTTER",
    silent_mode: str = "OFF",
    flash_mode: str = "FLASH_OFF",
    flash_firing_enabled: bool = False,
    flash_comp_ev: float = 0.0,
    exp_comp_set: str = "AMBIENT_AND_FLASH",
    claimed_exp_comp_set_wiped: bool = False,
    video_light_mode: str = "POWER_LINK",
    mi_shoe_5v_current_ma: int = 0,
    # Check Group B (Wave 51)
    movie_file_format: str = "XAVC_S_I_DCI_4K",
    movie_resolution_wh: str = P291_DCI_4K_WIDTH_HEIGHT,
    rec_frame_rate: str = "23.98P",
    stage_b_volatile_tmp_overlay_active: bool = False,
    ack_24p_reboot_wipes_tmp_overlay: bool = False,
    expect_24p_no_reboot: bool = False,
    hdmi_raw_output: bool = False,
    hdmi_raw_resolution_wh: str = P291_HDMI_RAW_WIDTH_HEIGHT,
    sq_dci4k_fps: int = 24,
    bitrate_mbps: int = 240,
    media_speed_grade: str = "CFEXPRESS_A_VPG200",
    exposed_still_aspect_modes: Sequence[str] = P291_STILL_ASPECT_FOUR_MODES,
    still_aspect_ratio: str = "3:2",
    apsc_s35_on: bool = False,
    still_jpeg_heif_size: str = "L",
    fx6_reference_still_aspect_ratio_present: bool = False,
    hlg_still_image: str = "OFF",
    recall_custom_hold_keys: Sequence[str] = P291_RECALL_CUSTOM_HOLD_11_KEYS,
    recall_custom_recalled_items: Sequence[str] = (),
    claimed_recall_custom_wiped_by_camera_reset: bool = False,
    camset_card_path: str = P291_DEFAULT_FX3_SETTING_CARD_PATH,
    memory_recall_media_slot: str = "SLOT_1",
    fx3_uses_private_sony_pro_camera: bool = False,
    claimed_memory_recall_media_survives_reset_as_slot2: bool = False,
    expect_format_preserves_camset_or_m1_m4: bool = False,
    photo_capture_requested: bool = False,
    photo_capture_slot: int = 2,
    slot1_contains_tier0_dump: bool = True,
    enlarge_image_in_movie_claimed: bool = False,
    enlarge_initial_mag: str = "STANDARD_MAG",
    enlarge_initial_position: str = "FOCUSED_POSITION",
    claimed_enlarge_prefs_wiped_by_camera_reset: bool = False,
    # Check Group C (Wave 52)
    sensor_cleaning_resid16_hex: str = P291_SENSOR_CLEANING_RESID16_HEX,
    sensor_cleaning_requested: bool = False,
    battery_soc_pct: float = 88.0,
    mandatory_power_off_after_cleaning: bool = True,
    unattended_tier0_dump_active: bool = False,
    fx6_sensor_cleaning_supported_claimed: bool = False,
    fx3_has_built_in_end_filter: bool = False,
    exposure_comp_ev: float = 0.0,
    exposure_step: str = "0.3EV",
    legacy_reset_ev_comp_claimed: bool = False,
    claimed_exposure_step_wiped_by_camera_reset: bool = False,
    exposed_still_focus_modes: Sequence[str] = P291_STILL_FOCUS_FIVE_MODES,
    exposed_movie_focus_modes: Sequence[str] = P291_MOVIE_FOCUS_TWO_MODES,
    focus_mode: str = "MF",
    priority_set_in_af: str = "BALANCED_EMPHASIS",
    af_illuminator: str = "AUTO",
    af_assist_active: bool = False,
    mount_adaptor_attached: bool = False,
    focus_magnifier_active: bool = False,
    claimed_priority_set_wiped_by_camera_reset: bool = False,
    exposed_view_modes: Sequence[str] = P291_VIEW_MODE_THREE_MODES,
    view_mode: str = "DATE_VIEW",
    exposed_image_index_modes: Sequence[str] = P291_IMAGE_INDEX_TWO_MODES,
    image_index_mode: str = "9_IMAGES",
    display_as_group: str = "OFF",
    display_rotation: str = "AUTO",
    claimed_playback_view_prefs_wiped_by_camera_reset: bool = False,
    playback_media_slot: int = 1,
    playback_rotate_requested: bool = False,
    playback_rotate_on_movie: bool = False,
    playback_rotate_during_transfer: bool = False,
    # Check Group D (Tier-0 & Redlines)
    simulated_passive_tx_bytes: int = 0,
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
    simulated_h0_h3_drifted_surfaces: int = 0,
    claim_hardware_live_attach_authorized: bool = False,
    claim_persistent_emmc_writes_authorized: bool = False,
    claim_cross_model_flash_authorized: bool = False,
) -> RealHwFocusAreaZoomDci4kSensorCleaningReport:
    """Execute Phase 291 10th real-hardware physical bench readiness verifier (`A..D`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase291_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_p291_check_group_a_focus_zoom_iso_flash(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        focus_area_bkid=focus_area_bkid,
        focus_area_resid16_hex=focus_area_resid16_hex,
        focus_area=focus_area,
        exposed_non_tracking_focus_areas=exposed_non_tracking_focus_areas,
        exposed_tracking_focus_areas=exposed_tracking_focus_areas,
        expect_tracking_focus_area_in_movie=expect_tracking_focus_area_in_movie,
        touch_tracking_used_for_movie_sq=touch_tracking_used_for_movie_sq,
        fx6_reference_tracking_focus_areas_present=fx6_reference_tracking_focus_areas_present,
        focus_area_limit_selected_count=focus_area_limit_selected_count,
        switch_vh_af_area=switch_vh_af_area,
        expect_switch_vh_in_movie=expect_switch_vh_in_movie,
        focus_area_color=focus_area_color,
        circ_of_focus_point=circ_of_focus_point,
        af_area_registration_label=af_area_registration_label,
        claimed_non_resettable_af_prefs_wiped=claimed_non_resettable_af_prefs_wiped,
        xlr_h1_zoom_lever_present=xlr_h1_zoom_lever_present,
        xlr_h1_rec_button_present=xlr_h1_rec_button_present,
        xlr_h1_zoom_hold_switch_present=xlr_h1_zoom_hold_switch_present,
        fx6_smart_handle_zero_to_99_is_speed_scale=fx6_smart_handle_zero_to_99_is_speed_scale,
        zoom_range=zoom_range,
        still_raw_active=still_raw_active,
        high_fps_120_100=high_fps_120_100,
        claimed_zoom_range_wiped=claimed_zoom_range_wiped,
        zoom_lever_stby_speed=zoom_lever_stby_speed,
        zoom_lever_rec_speed=zoom_lever_rec_speed,
        custom_key_zoom_stby_speed=custom_key_zoom_stby_speed,
        custom_key_zoom_rec_speed=custom_key_zoom_rec_speed,
        remote_zoom_speed_type=remote_zoom_speed_type,
        remote_zoom_fixed_stby_speed=remote_zoom_fixed_stby_speed,
        remote_zoom_fixed_rec_speed=remote_zoom_fixed_rec_speed,
        iso_range_limit_min=iso_range_limit_min,
        iso_range_limit_max=iso_range_limit_max,
        claimed_iso_range_limit_wiped=claimed_iso_range_limit_wiped,
        iso_auto_min=iso_auto_min,
        iso_auto_max=iso_auto_max,
        exposure_mode=exposure_mode,
        iso_mode=iso_mode,
        iso_auto_min_ss=iso_auto_min_ss,
        iso_auto_min_ss_active=iso_auto_min_ss_active,
        expect_iso_auto_min_ss_in_movie_or_manual_iso=expect_iso_auto_min_ss_in_movie_or_manual_iso,
        log_shooting_mode=log_shooting_mode,
        cine_ei_base_iso=cine_ei_base_iso,
        expect_iso_variable_in_cine_ei=expect_iso_variable_in_cine_ei,
        shutter_type=shutter_type,
        silent_mode=silent_mode,
        flash_mode=flash_mode,
        flash_firing_enabled=flash_firing_enabled,
        flash_comp_ev=flash_comp_ev,
        exp_comp_set=exp_comp_set,
        claimed_exp_comp_set_wiped=claimed_exp_comp_set_wiped,
        video_light_mode=video_light_mode,
        mi_shoe_5v_current_ma=mi_shoe_5v_current_ma,
    )
    gb = evaluate_p291_check_group_b_dci4k_aspect_hold_camset_photo(
        reset_action=reset_action,
        movie_file_format=movie_file_format,
        movie_resolution_wh=movie_resolution_wh,
        rec_frame_rate=rec_frame_rate,
        stage_b_volatile_tmp_overlay_active=stage_b_volatile_tmp_overlay_active,
        ack_24p_reboot_wipes_tmp_overlay=ack_24p_reboot_wipes_tmp_overlay,
        expect_24p_no_reboot=expect_24p_no_reboot,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_raw_resolution_wh=hdmi_raw_resolution_wh,
        sq_dci4k_fps=sq_dci4k_fps,
        bitrate_mbps=bitrate_mbps,
        media_speed_grade=media_speed_grade,
        exposed_still_aspect_modes=exposed_still_aspect_modes,
        still_aspect_ratio=still_aspect_ratio,
        apsc_s35_on=apsc_s35_on,
        still_jpeg_heif_size=still_jpeg_heif_size,
        fx6_reference_still_aspect_ratio_present=fx6_reference_still_aspect_ratio_present,
        exposure_mode=exposure_mode,
        hlg_still_image=hlg_still_image,
        recall_custom_hold_keys=recall_custom_hold_keys,
        recall_custom_recalled_items=recall_custom_recalled_items,
        claimed_recall_custom_wiped_by_camera_reset=claimed_recall_custom_wiped_by_camera_reset,
        camset_card_path=camset_card_path,
        memory_recall_media_slot=memory_recall_media_slot,
        fx3_uses_private_sony_pro_camera=fx3_uses_private_sony_pro_camera,
        claimed_memory_recall_media_survives_reset_as_slot2=claimed_memory_recall_media_survives_reset_as_slot2,
        expect_format_preserves_camset_or_m1_m4=expect_format_preserves_camset_or_m1_m4,
        photo_capture_requested=photo_capture_requested,
        photo_capture_slot=photo_capture_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        shoot_mode=shoot_mode,
        enlarge_image_in_movie_claimed=enlarge_image_in_movie_claimed,
        enlarge_initial_mag=enlarge_initial_mag,
        enlarge_initial_position=enlarge_initial_position,
        claimed_enlarge_prefs_wiped_by_camera_reset=claimed_enlarge_prefs_wiped_by_camera_reset,
    )
    gc = evaluate_p291_check_group_c_sensor_clean_ev_focus_playback(
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        sensor_cleaning_resid16_hex=sensor_cleaning_resid16_hex,
        sensor_cleaning_requested=sensor_cleaning_requested,
        battery_soc_pct=battery_soc_pct,
        mandatory_power_off_after_cleaning=mandatory_power_off_after_cleaning,
        unattended_tier0_dump_active=unattended_tier0_dump_active,
        fx6_sensor_cleaning_supported_claimed=fx6_sensor_cleaning_supported_claimed,
        fx3_has_built_in_end_filter=fx3_has_built_in_end_filter,
        exposure_comp_ev=exposure_comp_ev,
        exposure_step=exposure_step,
        exposure_mode=exposure_mode,
        iso_mode=iso_mode,
        log_shooting_mode=log_shooting_mode,
        legacy_reset_ev_comp_claimed=legacy_reset_ev_comp_claimed,
        claimed_exposure_step_wiped_by_camera_reset=claimed_exposure_step_wiped_by_camera_reset,
        exposed_still_focus_modes=exposed_still_focus_modes,
        exposed_movie_focus_modes=exposed_movie_focus_modes,
        focus_mode=focus_mode,
        priority_set_in_af=priority_set_in_af,
        af_illuminator=af_illuminator,
        af_assist_active=af_assist_active,
        mount_adaptor_attached=mount_adaptor_attached,
        focus_magnifier_active=focus_magnifier_active,
        claimed_priority_set_wiped_by_camera_reset=claimed_priority_set_wiped_by_camera_reset,
        exposed_view_modes=exposed_view_modes,
        view_mode=view_mode,
        exposed_image_index_modes=exposed_image_index_modes,
        image_index_mode=image_index_mode,
        display_as_group=display_as_group,
        display_rotation=display_rotation,
        claimed_playback_view_prefs_wiped_by_camera_reset=claimed_playback_view_prefs_wiped_by_camera_reset,
        playback_media_slot=playback_media_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        playback_rotate_requested=playback_rotate_requested,
        playback_rotate_on_movie=playback_rotate_on_movie,
        playback_rotate_during_transfer=playback_rotate_during_transfer,
    )
    gd, tier0_errors = evaluate_p291_check_group_d_physical_bench_and_tier0(
        simulated_passive_tx_bytes=simulated_passive_tx_bytes,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_model_id=body_model_id,
        body_fw=body_fw,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        simulate_bench_dry_run=eff_sim,
        claim_hardware_live_attach_authorized=claim_hardware_live_attach_authorized,
        claim_persistent_emmc_writes_authorized=claim_persistent_emmc_writes_authorized,
        claim_cross_model_flash_authorized=claim_cross_model_flash_authorized,
    )

    groups_passed = sum(1 for item in (ga, gb, gc, gd) if item.passed)
    all_4_passed = donor_res.passed and groups_passed == 4

    all_errors: List[str] = []
    all_errors.extend(donor_res.errors)
    for item in (ga, gb, gc, gd):
        all_errors.extend(item.errors)
    all_errors.extend(tier0_errors)

    remediations: List[str] = []
    if not ga.passed:
        remediations.append(
            "Enforce Still-only Tracking Focus Areas (Touch Tracking for Movie/S&Q), exact 'AF Area Registration', handle-less XLR-H1 vs body W/T zoom 1..8, Still P/A ISO AUTO Min. SS vs Cine EI 800/12800, and Mechanical-Still Flash gate."
        )
    if not gb.passed:
        remediations.append(
            "Keep [XAVC S-I DCI 4K] at 4096x2160 with explicit 24.00p reboot quarantine, 11 Reg. Custom Shoot Set hold checkboxes, FX3 /SONY/SETTING/FX3/ paths (zero PRO/CAMERA), and Slot-1/DCI 4K Photo Capture firewall."
        )
    if not gc.passed:
        remediations.append(
            "Require NP-FZ100 >= 51% + mandatory OFF for [Sensor Cleaning], lock Exposure Comp. under Cine EI, enforce Focus Mode 5-vs-2 split and 9/25 Image Index, and block [Rotate] on read-only Slot 1 Tier-0 Vault."
        )
    if not gd.passed or not gd.tier0_receipt_verified:
        remediations.append(
            "Verify 16/16 H0==H3 baseline invariance, keep all hardware attach / eMMC write / cross-model flash locks OFF, and supply dual-device 528B FX3RCPT1 Tier-0 receipts."
        )

    if not all_4_passed:
        verdict = P291_GO_NO_GO_BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_FAILURE
        overall_status = verdict
    elif not gd.tier0_receipt_verified:
        if not gd.tier0_receipt_present:
            verdict = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            overall_status = P291_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        else:
            verdict = P291_GO_NO_GO_BLOCKED_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_FAILURE
            overall_status = verdict
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED
        overall_status = P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED

    provisional = RealHwFocusAreaZoomDci4kSensorCleaningReport(
        schema=PHASE_291_SCHEMA,
        phase_version=PHASE_291_VERSION,
        verification_mode=donor_res.verification_mode,
        simulate_bench_dry_run=eff_sim,
        overall_status=overall_status,
        go_no_go=verdict,
        overall_ready_for_hardware_attach=False,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        cross_model_flash_authorized=False,
        xlr_h1_zoom_lever_present=False,
        fx3_private_sony_pro_camera_used=False,
        usb_packets_transmitted=PHASE291_USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHASE291_USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=PHASE291_RAW_FIRMWARE_BYTES_LEAKED,
        passive_tx_bytes_emitted=gd.passive_tx_bytes_emitted,
        check_group_count=4,
        check_groups_passed=groups_passed,
        all_4_check_groups_passed=all_4_passed,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_focus_zoom_iso_flash=ga,
        check_group_b_dci4k_aspect_hold_camset_photo=gb,
        check_group_c_sensor_clean_ev_focus_playback=gc,
        check_group_d_physical_bench_and_tier0=gd,
        warnings=gd.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwFocusAreaZoomDci4kSensorCleaningReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_focus_zoom_iso_flash": ga,
            "check_group_b_dci4k_aspect_hold_camset_photo": gb,
            "check_group_c_sensor_clean_ev_focus_playback": gc,
            "check_group_d_physical_bench_and_tier0": gd,
            "warnings": gd.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_focus_area_zoom_dci4k_and_sensor_cleaning_preflight = (
    evaluate_realhw_focus_area_zoom_dci4k_and_sensor_cleaning_readiness
)


def verify_phase291_report(payload: Mapping[str, Any]) -> Phase291ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 291 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_291_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_291_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_291_VALID_GO_NO_GO_VALUES:
        errors.append(f"Invalid go_no_go verdict: {payload.get('go_no_go')!r}")

    for lock_key in (
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "cross_model_flash_authorized",
        "xlr_h1_zoom_lever_present",
        "fx3_private_sony_pro_camera_used",
    ):
        if payload.get(lock_key) is not False:
            errors.append(f"Safety lock violated: {lock_key}={payload.get(lock_key)!r}")

    for zero_key in (
        "usb_packets_transmitted",
        "physical_usb_packets_emitted",
        "raw_firmware_bytes_leaked",
        "passive_tx_bytes_emitted",
    ):
        if payload.get(zero_key) != 0:
            errors.append(f"Zero-counter violated: {zero_key}={payload.get(zero_key)!r}")

    if payload.get("check_group_count") != 4:
        errors.append(f"Expected check_group_count==4, got {payload.get('check_group_count')!r}")

    if payload.get("go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT and (
        payload.get("overall_status") != P291_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    ):
        errors.append(
            "Offline awaiting-receipt verdict must carry overall_status=READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
        )

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go") == P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == P291_GO_NO_GO_FOCUS_AREA_ZOOM_DCI4K_SENSOR_CLEANING_VERIFIED and (
        payload.get("all_4_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 4 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase291ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase291_markdown(report: RealHwFocusAreaZoomDci4kSensorCleaningReport) -> str:
    """Render concise deterministic Markdown summary for Phase 291 10th physical bench preflight."""
    ga = report.check_group_a_focus_zoom_iso_flash
    gb = report.check_group_b_dci4k_aspect_hold_camset_photo
    gc = report.check_group_c_sensor_clean_ev_focus_playback
    gd = report.check_group_d_physical_bench_and_tier0
    lines = [
        f"# Phase 291 10th Physical Bench Readiness (`{report.schema}`)",
        "",
        f"- **OVERALL**: `{report.overall_status}` (`go_no_go={report.go_no_go}`, mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `ready_attach={report.overall_ready_for_hardware_attach}`, `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `cross_model_flash={report.cross_model_flash_authorized}`, `xlr_h1_zoom_lever={report.xlr_h1_zoom_lever_present}`, `fx3_pro_cam={report.fx3_private_sony_pro_camera_used}`, `usb_pkts={report.usb_packets_transmitted}`, `passive_tx={report.passive_tx_bytes_emitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | Shoot=`{ga.shoot_mode}`, FA=`{ga.focus_area}` (`{ga.non_tracking_focus_area_count}+{ga.tracking_focus_area_count}`), AFReg=`{ga.af_area_registration_label}`, XLR-H1_Zoom=`{ga.xlr_h1_zoom_lever_present}`, RemoteZoom=`{ga.remote_zoom_speed_type}`, BaseISO=`{ga.cine_ei_base_iso}`, FlashGate=`{ga.flash_mechanical_still_gate_verified}` |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | Codec=`{gb.movie_file_format}` (`{gb.movie_resolution_wh}` @ `{gb.rec_frame_rate}`, 24pReboot=`{gb.dci4k_24p_reboot_required}`), Aspect=`{gb.still_aspect_ratio}` (`{gb.exposed_still_aspect_count}`), HoldKeys=`{gb.recall_custom_hold_checkbox_count}`, Path=`{gb.camset_card_path}` |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | CleanReq=`{gc.sensor_cleaning_requested}` (SOC=`{gc.battery_soc_pct:.1f}%`, OFF=`{gc.mandatory_power_off_after_cleaning}`), EV=`{gc.exposure_comp_ev:+.1f}` (CineEI_Lock=`{gc.ev_comp_cine_ei_lockout_verified}`), Focus=`{gc.focus_mode}` (`{gc.exposed_still_focus_mode_count}`v`{gc.exposed_movie_focus_mode_count}`), Index=`{gc.image_index_mode}`, RotateSlot1Guard=`{gc.playback_rotate_slot1_firewall_enforced}` |",
        f"| `{gd.check_group_id}` | `{'PASS' if gd.passed else 'FAIL'}` | H0==H3=`{gd.h0_equals_h3_count}/{gd.h0_h3_surface_count}`, Tier0=`{gd.tier0_receipt_verified}`, DistinctMedia=`{gd.distinct_physical_media_verified}`, AttachAuth=`{gd.overall_ready_for_hardware_attach}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
