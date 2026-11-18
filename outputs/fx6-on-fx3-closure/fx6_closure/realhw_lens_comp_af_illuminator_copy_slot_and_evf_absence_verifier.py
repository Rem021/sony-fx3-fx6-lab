"""Phase 302 — 11th Real-Hardware Physical Bench Readiness Verifier (`preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence`).

Dedicated host-side read-only 11th physical bench & pre-shoot readiness verifier for Sony
`ILME-FX3` (`Ver. 7.02`, `ilc/2210`, Model `0x91030080`) vs `ILME-FX6` (`Ver. 6.01`),
extending the 11-stage operator bench preflight series (`preflight-card-insert` ->
`preflight-bench-cable-fan-slot1` -> `preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp` ->
`preflight-imagedb-touch-shoeaudio-and-lockop` ->
`preflight-diffset-customkey-autoslow-and-apsc` ->
`preflight-file-settings-gamma-assist-focus-mag-and-videolight` ->
`preflight-usb-mode-hdmi-info-protect-and-network-reset` ->
`preflight-pp-scinetone-wb-metering-and-shutter-type` ->
`preflight-focus-area-zoom-dci4k-and-sensor-cleaning` ->
`preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence`) by synthesizing Waves 53-55
official Sony `ILME-FX3` Help Guide (`ilc/2210`), `appFw.so`, `BK4`, and `.uxc` hardware
boundaries into 4 deterministic fail-closed check groups (`A..D`), bounded `O_RDONLY`
donor inspection (`< 0.15s`), `16/16 H0 == H3` baseline invariance, and dual-media
`528 B FX3RCPT1` Tier-0 receipt gating:

1. **Check Group A (`GROUP_A_LENS_COMP_BUILTIN_AF_ILLUMINATOR_AF_PERSISTENCE_AND_FOLDER_RATING_VAULT` — Wave 53)**:
   - `[Lens Compensation]` (`0x75c8`): FX3 Ver. 7.02 `[Shading Comp.]` (`0x64e1`,
     `BKID_APP_setting_lens_comp_shading`) exposes ONLY `Auto` / `Off` — dormant
     `Auto: Low` (`LENS_COMP_SHADING_AUTO_LOW`, `_f.uxc` `0x6c9c`) is rejected fail-closed
     with `EOPNOTSUPP=95`. `[Chromatic Aberration Comp.]` (`0x68cd`) and `[Distortion Comp.]`
     (`0x6200`) enforce `Auto`/`Off` lens-governed locks (`SteadyShot=Active` locks
     `Distortion Comp.=Auto`, unchipped manual lenses lock out compensation), and all 3
     static compensations survive `Camera Settings Reset` (Initialize-only), while
     `[Breathing Comp.]` (`0x73ea`) is Movie-only & resettable.
   - `ILME-FX3` possesses a physical front built-in AF illuminator / Self-timer lamp LED
     (*Front side* #8, `0.3..3.0 m`) + MI-Shoe Flash AF illuminator (`0x69c0`/`0xe07f`,
     `BKID_APP_setting_still_image_af_illuminator`) in Still `AF-S` (locked out in Movie,
     `S&Q`, `AF-C`, `MF`, Focus Magnifier, Mount Adaptor), whereas `ILME-FX6` has ZERO
     built-in AF illuminator. Contrasted with Movie/`S&Q` `[AF Transition Speed]` (`1..7`),
     `[AF Subj. Shift Sensitivity]` (`1..5`), and `[AF Assist]` (`0x64a9`).
   - `[Aperture Drive in AF]` (`0x7879`, `Focus Priority`/`Standard`/`Silent Priority`),
     `[AF w/ Shutter]` (`0x771d`), `[Pre-AF]` (`0x76d8`), `[Circ. of Focus Point]`
     (`0x74f6`, orthogonal wrap only), and `[Focus Area Color]` (`0x74ad`, `White`/`Red`)
     all survive `Camera Settings Reset` (Initialize-only) and are absent on `FX6`.
   - `[Create New Folder]` (max `4,000` images/folder) and Playback `[Rating]` (`1..5` stars)
     mutate DCIM/EXIF/`AVF_INFO` on card -> blocked fail-closed (`EROFS=30` / `EBUSY=16`)
     on read-only `Slot 1` Tier-0 Vault.

2. **Check Group B (`GROUP_B_SWITCH_VH_AF_14LIMIT_5MODE_STD_ADJ_TC_FORMAT_AND_COPY_REVERSE_SLOT1_TRAP` — Wave 54)**:
   - `[Switch V/H AF Area]` (`0x73ae`: `Off` / `AF Point Only` / `AF Point + AF Area`) in Still
     `AF-C` (`0_DEGREES`/`90_DEGREES`/`270_DEGREES` vs `INVALID_VERTICAL_PITCH`) and
     `[Focus Area Limit]` (`0x6de2`) exact `14` checkboxes (`>= 2` minimum via `.uxc 0xea28`;
     dormant `Spot: XL`/`Spot: XS`/`Custom 1..3` rejected as `EOPNOTSUPP=95`).
   - `[Exposure Std. Adjust]` (`0x6114`) exposes ALL `5` metering modes (`Multi` / `Center` /
     `Spot` / `Entire Screen Avg.` / `Highlight`, `-1.0..+1.0 EV` in `1/6 EV` steps,
     Initialize-only permanence) + Still-only `[Bracket Settings]`.
   - `[Time Code Format]` (`DF`/`NDF`) locks `NDF` in `23.98p`/`24.00p` and hides in `PAL`;
     `[User Bit Time Rec]` vs `FX6` dedicated physical BNC `TC IN/TC OUT` switch.
   - **CRITICAL BENCH FIREWALL**: Playback `[Copy]` (`_f.uxc` `0x79fc`, `FUNC_copy_content`)
     reverses write direction onto `Slot 1` (`Slot 2 -> Slot 1`) whenever
     `[Select Playback Media] == Slot 2`! Blocked fail-closed (`EROFS=30` / `EBUSY=16`)
     whenever `Slot 1` holds a Tier-0 recovery vault! Plus `[Slide Show]` (`1/3/5/10/30s`).

3. **Check Group C (`GROUP_C_TOUCH_SHOOTING_4MODE_DISP_ZERO_EVF_BLACKOUT_AEL_FLASH_AND_INTERVAL_PLAY` — Wave 55)**:
   - `[Touch Func. in Shooting]` exposes ONLY `Touch Focus` / `Touch Tracking` / `Off` across
     Still/Movie/`S&Q` (dormant `Touch Shutter`, `Touch AE`, `Touch Panel/Pad`, `Footer Icon Touch`
     rejected; `[Touch Sensitivity]` is `Standard` / `Sensitive`, NOT `Responsive`).
   - `[DISP (Screen Disp) Set]` under `[Operation Customize]` exposes `4` monitor shoot modes
     (`Display All Info.`, `No Disp. Info.`, `Histogram`, `Level`) and `3` playback modes;
     `ILME-FX3` has **ZERO EVF, ZERO eye sensor, ZERO `Select Finder/Monitor`, and ZERO
     `Graphic Display`** — activating dormant EVF/finder keys triggers a black-screen
     lockout trap and MUST be blocked fail-closed pre-bench (`fx3_builtin_evf_present == False`).
   - Still-only `[AEL w/ Shutter]` (`Auto`/`On`/`Off`, Initialize-only), `[Exp.comp.set]`,
     `[Wireless Flash]` (resettable), `[External Flash Set.]` (absent on `FX6`), Playback
     `[Play Speed for Interval]` `1..9` (default `5`), and dormant `[Beauty Effect]`/`[Trimming]`
     Edit traps rejected + Slot-1 vault writes blocked.

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
- `builtin_evf_present = False`
- `fx6_builtin_af_illuminator_present = False`
- `slot1_tier0_vault_mutated = False`
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
# Schema, Verdicts & Non-Shadowing P302_* Domain Constants
# ---------------------------------------------------------------------------

PHASE_302_SCHEMA: str = "realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_verifier_v1"
P302_SCHEMA: str = PHASE_302_SCHEMA
REALHW_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_SCHEMA: str = PHASE_302_SCHEMA
PHASE_302_VERSION: str = "302.0.0"
P302_VERSION: str = PHASE_302_VERSION
P302_SONY_HELP_GUIDE_ID: str = "ilc/2210"

P302_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS: str = (
    "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
)
P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED: str = (
    "GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_READONLY_PREFLIGHT_VERIFIED"
)
P302_GO_NO_GO_BLOCKED_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_FAILURE: str = (
    "BLOCKED_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_CHECK_FAILURE"
)
PHASE_302_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    P302_GO_NO_GO_BLOCKED_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED,
)

P302_CHECK_GROUP_A_ID: str = (
    "GROUP_A_LENS_COMP_BUILTIN_AF_ILLUMINATOR_AF_PERSISTENCE_AND_FOLDER_RATING_VAULT"
)
P302_CHECK_GROUP_B_ID: str = (
    "GROUP_B_SWITCH_VH_AF_14LIMIT_5MODE_STD_ADJ_TC_FORMAT_AND_COPY_REVERSE_SLOT1_TRAP"
)
P302_CHECK_GROUP_C_ID: str = (
    "GROUP_C_TOUCH_SHOOTING_4MODE_DISP_ZERO_EVF_BLACKOUT_AEL_FLASH_AND_INTERVAL_PLAY"
)
P302_CHECK_GROUP_D_ID: str = (
    "GROUP_D_PHYSICAL_BENCH_READINESS_TIER0_16H0H3_AND_FAIL_CLOSED_REDLINES"
)
PHASE_302_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P302_CHECK_GROUP_A_ID,
    P302_CHECK_GROUP_B_ID,
    P302_CHECK_GROUP_C_ID,
    P302_CHECK_GROUP_D_ID,
)

PHASE302_RAW_FIRMWARE_BYTES_LEAKED: int = 0
PHASE302_PASSIVE_TX_BYTES_EMITTED: int = 0
PHASE302_USB_PACKETS_TRANSMITTED: int = 0

P302_ERRNO_EBUSY: int = 16
P302_ERRNO_EROFS: int = 30
P302_ERRNO_EOPNOTSUPP: int = 95

# Common Mode & Reset Constants
P302_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P302_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P302_VALID_FOCUS_MODES: Tuple[str, ...] = ("AF_S", "AF_A", "AF_C", "DMF", "MF")

# Check Group A Constants (Wave 53)
P302_LENS_COMP_RESID16_HEX: str = "0x75c8"
P302_SHADING_COMP_RESID16_HEX: str = "0x64e1"
P302_SHADING_COMP_BKID: str = "BKID_APP_setting_lens_comp_shading"
P302_DORMANT_SHADING_AUTO_LOW_RESID16_HEX: str = "0x6c9c"
P302_DORMANT_SHADING_AUTO_LOW_SYMBOL: str = "LENS_COMP_SHADING_AUTO_LOW"
P302_SHADING_TWO_MODES: Tuple[str, ...] = ("AUTO", "OFF")
P302_CHROMA_ABERRATION_RESID16_HEX: str = "0x68cd"
P302_DISTORTION_COMP_RESID16_HEX: str = "0x6200"
P302_BREATHING_COMP_RESID16_HEX: str = "0x73ea"
P302_VALID_ON_OFF: Tuple[str, ...] = ("ON", "OFF")
P302_VALID_STEADYSHOT_MODES: Tuple[str, ...] = ("OFF", "STANDARD", "ACTIVE")

P302_AF_ILLUMINATOR_RESID16_HEX: str = "0x69c0"
P302_AF_ILLUMINATOR_UXC_RESID16_HEX: str = "0xe07f"
P302_AF_ILLUMINATOR_BKID: str = "BKID_APP_setting_still_image_af_illuminator"
P302_VALID_AF_ILLUMINATOR_MODES: Tuple[str, ...] = ("AUTO", "OFF")
P302_AF_ILLUMINATOR_RANGE_MIN_M: float = 0.3
P302_AF_ILLUMINATOR_RANGE_MAX_M: float = 3.0
P302_AF_ASSIST_RESID16_HEX: str = "0x64a9"
P302_AF_TRANSITION_SPEED_RESID16_HEX: str = "0x6e9d"
P302_AF_TRANSITION_SPEED_MIN: int = 1
P302_AF_TRANSITION_SPEED_MAX: int = 7
P302_AF_SUBJ_SHIFT_SENS_RESID16_HEX: str = "0x79d6"
P302_AF_SUBJ_SHIFT_SENS_MIN: int = 1
P302_AF_SUBJ_SHIFT_SENS_MAX: int = 5

P302_APERTURE_DRIVE_IN_AF_RESID16_HEX: str = "0x7879"
P302_APERTURE_DRIVE_THREE_MODES: Tuple[str, ...] = (
    "FOCUS_PRIORITY",
    "STANDARD",
    "SILENT_PRIORITY",
)
P302_AF_WITH_SHUTTER_RESID16_HEX: str = "0x771d"
P302_PRE_AF_RESID16_HEX: str = "0x76d8"
P302_CIRC_FOCUS_POINT_RESID16_HEX: str = "0x74f6"
P302_VALID_CIRC_FOCUS_POINT_MODES: Tuple[str, ...] = (
    "DOES_NOT_CIRCULATE",
    "CIRCULATE",
)
P302_FOCUS_AREA_COLOR_RESID16_HEX: str = "0x74ad"
P302_VALID_FOCUS_AREA_COLORS: Tuple[str, ...] = ("WHITE", "RED")

P302_VALID_STILL_FOLDER_NAME_MODES: Tuple[str, ...] = ("STANDARD_FORM", "DATE_FORM")
P302_VALID_STILL_FILE_NUMBER_MODES: Tuple[str, ...] = ("SERIES", "RESET")
P302_STILL_PREFIX_NO_LEADING_UNDERSCORE_RE: re.Pattern[str] = re.compile(
    r"^[A-Za-z0-9][A-Za-z0-9_]{2}$"
)
P302_FOLDER_NAME_MAX_IMAGES: int = 4000
P302_STILL_RATING_MIN_STARS: int = 1
P302_STILL_RATING_MAX_STARS: int = 5

# Check Group B Constants (Wave 54)
P302_SWITCH_VH_AF_AREA_RESID16_HEX: str = "0x73ae"
P302_VALID_SWITCH_VH_MODES: Tuple[str, ...] = (
    "OFF",
    "AF_POINT_ONLY",
    "AF_POINT_AND_AF_AREA",
)
P302_VALID_BODY_ROLL_STATES: Tuple[str, ...] = (
    "0_DEGREES",
    "90_DEGREES",
    "270_DEGREES",
    "INVALID_VERTICAL_PITCH",
)

P302_FOCUS_AREA_LIMIT_RESID16_HEX: str = "0x6de2"
P302_FOCUS_AREA_LIMIT_MIN_SELECTED_RESID16_HEX: str = "0xea28"
P302_FOCUS_AREA_LIMIT_MIN_SELECTED: int = 2
P302_FOCUS_AREA_LIMIT_14_ITEMS: Tuple[str, ...] = (
    "WIDE",
    "ZONE",
    "CENTER_FIX",
    "SPOT_S",
    "SPOT_M",
    "SPOT_L",
    "EXPAND_SPOT",
    "TRACKING_WIDE",
    "TRACKING_ZONE",
    "TRACKING_CENTER_FIX",
    "TRACKING_SPOT_S",
    "TRACKING_SPOT_M",
    "TRACKING_SPOT_L",
    "TRACKING_EXPAND_SPOT",
)
P302_DORMANT_FOCUS_AREAS: Tuple[str, ...] = (
    "SPOT_XL",
    "SPOT_XS",
    "CUSTOM_1",
    "CUSTOM_2",
    "CUSTOM_3",
)

P302_EXPOSURE_STD_ADJUST_RESID16_HEX: str = "0x6114"
P302_EXPOSURE_STD_ADJUST_5_METERING_MODES: Tuple[str, ...] = (
    "MULTI",
    "CENTER",
    "SPOT",
    "ENTIRE_SCREEN_AVG",
    "HIGHLIGHT",
)
P302_EXPOSURE_STD_ADJUST_EV_MIN: float = -1.0
P302_EXPOSURE_STD_ADJUST_EV_MAX: float = 1.0
P302_BRACKET_SELFTIMER_MODES: Tuple[str, ...] = ("OFF", "2_SEC", "5_SEC", "10_SEC")
P302_BRACKET_ORDER_MODES: Tuple[str, ...] = ("0_MINUS_PLUS", "MINUS_0_PLUS")

P302_VALID_VIDEO_SYSTEMS: Tuple[str, ...] = ("NTSC", "PAL")
P302_TC_FORMAT_MODES: Tuple[str, ...] = ("DF", "NDF", "UNAVAILABLE_PAL")
P302_TC_NDF_LOCKED_FRAME_RATES: Tuple[str, ...] = ("23.98P", "24.00P")
P302_VALID_TCUB_DISP_SETTINGS: Tuple[str, ...] = ("COUNTER", "TC", "U_BIT")

P302_PLAYBACK_COPY_RESID16_HEX: str = "0x79fc"
P302_PLAYBACK_COPY_FUNC: str = "FUNC_copy_content"
P302_SLIDE_SHOW_INTERVALS_SEC: Tuple[int, ...] = (1, 3, 5, 10, 30)
P302_SLIDE_SHOW_VIEW_MODES: Tuple[str, ...] = ("DATE_VIEW", "FOLDER_VIEW_STILL")

# Check Group C Constants (Wave 55)
P302_VALID_TOUCH_OPERATION_MODES: Tuple[str, ...] = ("ON", "ON_PLAYBACK_ONLY", "OFF")
P302_TOUCH_SENSITIVITY_TWO_MODES: Tuple[str, ...] = ("STANDARD", "SENSITIVE")
P302_TOUCH_FUNC_SHOOTING_THREE_MODES: Tuple[str, ...] = (
    "TOUCH_FOCUS",
    "TOUCH_TRACKING",
    "OFF",
)
P302_VALID_SWIPE_UP_MODES: Tuple[str, ...] = ("OPEN_THE_FN_MENU", "OFF")
P302_DORMANT_TOUCH_TRAPS: Tuple[str, ...] = (
    "NONE",
    "TOUCH_SHUTTER",
    "TOUCH_AE",
    "TOUCH_PANEL_PAD",
    "FOOTER_ICON_TOUCH",
    "RESPONSIVE_SENSITIVITY",
    "SWIPE_LEFT",
    "SWIPE_RIGHT",
)

P302_DISP_MONITOR_SHOOT_FOUR_MODES: Tuple[str, ...] = (
    "DISPLAY_ALL_INFO",
    "NO_DISP_INFO",
    "HISTOGRAM",
    "LEVEL",
)
P302_DISP_MONITOR_PLAYBACK_THREE_MODES: Tuple[str, ...] = (
    "DISPLAY_INFO",
    "HISTOGRAM",
    "NO_DISP_INFO",
)
P302_DORMANT_EVF_FINDER_TRAPS: Tuple[str, ...] = (
    "BKID_APP_setting_finder_monitor",
    "FINDER_MONITOR_SWITCH",
    "DISP_MODE_SHOOT_FINDER",
    "GRAPHIC_DISPLAY",
    "FOR_VIEWFINDER",
    "MONITOR_OFF_EVF_MODE",
)

P302_AEL_WITH_SHUTTER_THREE_MODES: Tuple[str, ...] = ("AUTO", "ON", "OFF")
P302_VALID_EXP_COMP_SET_MODES: Tuple[str, ...] = ("AMBIENT_AND_FLASH", "AMBIENT_ONLY")
P302_INTERVAL_PLAY_SPEED_MIN: int = 1
P302_INTERVAL_PLAY_SPEED_MAX: int = 9
P302_INTERVAL_PLAY_SPEED_DEFAULT: int = 5
P302_PLAYBACK_EDIT_ACTIVE_ITEMS: Tuple[str, ...] = ("ROTATE", "PHOTO_CAPTURE", "COPY")
P302_DORMANT_PLAYBACK_EDIT_TRAPS: Tuple[str, ...] = ("BEAUTY_EFFECT", "TRIMMING")

# Deterministic Error Codes
P302_GA_ERR_MODEL_OR_FW_FLOOR: str = "P302_GA_ERR_MODEL_OR_FW_FLOOR"
P302_GA_ERR_SHADING_AUTO_LOW_EOPNOTSUPP: str = (
    "P302_GA_ERR_SHADING_AUTO_LOW_EOPNOTSUPP_95"
)
P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY: str = (
    "P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY"
)
P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE: str = (
    "P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE"
)
P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC: str = (
    "P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC"
)
P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS: str = (
    "P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS_30"
)

P302_GB_ERR_SWITCH_VH_AF_AREA_GATE: str = "P302_GB_ERR_SWITCH_VH_AF_AREA_GATE"
P302_GB_ERR_FOCUS_AREA_LIMIT_14_OR_MIN2: str = (
    "P302_GB_ERR_FOCUS_AREA_LIMIT_14_OR_MIN2"
)
P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET: str = (
    "P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET"
)
P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE: str = (
    "P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE"
)
P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP: str = (
    "P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP_EROFS_30"
)
P302_GB_ERR_SLIDESHOW_BOUNDARY: str = "P302_GB_ERR_SLIDESHOW_BOUNDARY"

P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP: str = (
    "P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP"
)
P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP: str = (
    "P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP"
)
P302_GC_ERR_DISP_4MODE_SHOOT_3MODE_PLAYBACK: str = (
    "P302_GC_ERR_DISP_4MODE_SHOOT_3MODE_PLAYBACK"
)
P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE: str = (
    "P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE"
)
P302_GC_ERR_INTERVAL_SPEED_1TO9_OR_EDIT_VAULT_GUARD: str = (
    "P302_GC_ERR_INTERVAL_SPEED_1TO9_OR_EDIT_VAULT_GUARD"
)

P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P302_GD_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "P302_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P302_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION: str = (
    "P302_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"
)

# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _canonical_sha256_dict(payload: Mapping[str, Any], exclude_key: str = "report_sha256") -> str:
    clone = copy.deepcopy(dict(payload))
    clone.pop(exclude_key, None)
    donor_sub = clone.get("donor_inspection")
    if isinstance(donor_sub, dict):
        donor_sub.pop("elapsed_seconds", None)
    encoded = json.dumps(clone, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def _is_trivial_hex64(val: Any) -> bool:
    if not isinstance(val, str):
        return True
    norm = val.strip().lower()
    if not HEX64_RE.match(norm):
        return True
    return len(set(norm)) == 1


def _norm_upper(val: str) -> str:
    return str(val).strip().upper()


def _approx_sixth_ev_step(val: float) -> bool:
    scaled = float(val) * 6.0
    return abs(round(scaled) - scaled) < 1e-4


# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase302DonorInspectionResult:
    verification_mode: str
    passed: bool
    elapsed_seconds: float
    within_150ms_budget: bool
    raw_firmware_bytes_leaked: int
    im_elf_sha256: str
    libjiritsu_sha256: str
    libusbbuspower_sha256: str
    wlan_rsrc_sha256: str
    appfw_size_bytes: int
    appfw_is_aarch64_elf: bool
    upm_ko_size_bytes: int
    upm_ko_is_aarch64_elf: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P302CheckGroupALensCompAfIllumFolderRatingResult:
    check_group_id: str
    passed: bool
    sony_help_guide_id: str
    shading_comp: str
    dormant_auto_low_rejected: bool
    chromatic_aberration_comp: str
    distortion_comp: str
    breathing_comp: str
    fx3_builtin_af_illuminator_present: bool
    fx6_builtin_af_illuminator_present: bool
    af_illuminator: str
    af_illuminator_still_afs_gate_verified: bool
    aperture_drive_in_af: str
    af_with_shutter: str
    pre_af: str
    circ_of_focus_point: str
    focus_area_color: str
    five_af_params_survive_camera_reset: bool
    slot1_folder_rating_firewall_enforced: bool
    slot1_metadata_sector_writes: int
    slot1_avf_info_mutated: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P302CheckGroupBSwitchVhLimit14StdAdjTcCopyResult:
    check_group_id: str
    passed: bool
    switch_vh_af_area: str
    body_roll_orientation: str
    focus_area_limit_item_count: int
    focus_area_limit_selected_count: int
    dormant_focus_areas_rejected: bool
    exposure_std_metering_mode_count: int
    exposure_std_adjust_metering_mode: str
    exposure_std_adjust_ev: float
    tc_format: str
    video_system: str
    playback_media_slot: int
    copy_destination_slot: int
    playback_copy_requested: bool
    copy_reverse_slot1_firewall_enforced: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P302CheckGroupCTouchDispEvfAbsenceAelIntervalResult:
    check_group_id: str
    passed: bool
    touch_operation: str
    touch_sensitivity: str
    touch_func_in_shooting: str
    swipe_up: str
    dormant_touch_traps_rejected: bool
    exposed_disp_shoot_mode_count: int
    exposed_disp_playback_mode_count: int
    fx3_builtin_evf_present: bool
    fx3_eye_sensor_present: bool
    fx3_select_finder_monitor_present: bool
    fx3_graphic_display_present: bool
    zero_evf_blackout_firewall_enforced: bool
    ael_with_shutter: str
    wireless_flash: str
    interval_play_speed: int
    dormant_edit_traps_rejected: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P302CheckGroupDPhysicalBenchAndTier0Result:
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
class Phase302ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwLensCompAfIlluminatorCopySlotEvfAbsenceReport:
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
    builtin_evf_present: bool
    fx6_builtin_af_illuminator_present: bool
    slot1_tier0_vault_mutated: bool
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
    donor_inspection: Phase302DonorInspectionResult
    check_group_a_lens_comp_af_illum_folder_rating: (
        P302CheckGroupALensCompAfIllumFolderRatingResult
    )
    check_group_b_switch_vh_limit14_std_adj_tc_copy: (
        P302CheckGroupBSwitchVhLimit14StdAdjTcCopyResult
    )
    check_group_c_touch_disp_evf_absence_ael_interval: (
        P302CheckGroupCTouchDispEvfAbsenceAelIntervalResult
    )
    check_group_d_physical_bench_and_tier0: P302CheckGroupDPhysicalBenchAndTier0Result
    warnings: Tuple[str, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent) + "\n"


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection (< 0.15s)
# ---------------------------------------------------------------------------


def inspect_phase302_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
) -> Phase302DonorInspectionResult:
    """Inspect FX3/FX6 donor metadata strictly via O_RDONLY ELF headers & SHA-256 digests."""
    t0 = time.perf_counter()
    eff_clean = force_clean_room if force_clean_room is not None else synthetic_clean_room
    clean_room_env = (
        os.environ.get("FX3_CLEAN_ROOM_TEST", "").strip().lower() in ("1", "true", "yes")
        or is_forced_clean_room()
    )
    clean_room_req = clean_room_env if eff_clean is None else bool(eff_clean)

    im_path = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=False)
    jit_path = resolve_work_subpath(LIBJIRITSU_RELPATH, require_file=False)
    usb_path = resolve_work_subpath(FX3_LIBUSBBUSPOWER_RELPATH, require_file=False)
    wlan_path = fx6_lib_dir / "libWlanResource.so"
    appfw_path = fx6_lib_dir / "appFw.so"
    upm_path = fx3_modules_dir / "upm.ko"

    donors_present = (
        im_path.is_file()
        and jit_path.is_file()
        and usb_path.is_file()
        and wlan_path.is_file()
        and appfw_path.is_file()
        and upm_path.is_file()
    )

    if eff_clean is False and not donors_present:
        dt = time.perf_counter() - t0
        missing = [
            name
            for name, p in (
                ("im.elf", im_path),
                ("libJiritsu.so", jit_path),
                ("libUsbBusPower.so", usb_path),
                ("libWlanResource.so", wlan_path),
                ("appFw.so", appfw_path),
                ("upm.ko", upm_path),
            )
            if not p.is_file()
        ]
        return Phase302DonorInspectionResult(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            passed=False,
            elapsed_seconds=round(dt, 6),
            within_150ms_budget=(dt < DONOR_INSPECTION_MAX_SECONDS),
            raw_firmware_bytes_leaked=PHASE302_RAW_FIRMWARE_BYTES_LEAKED,
            im_elf_sha256="",
            libjiritsu_sha256="",
            libusbbuspower_sha256="",
            wlan_rsrc_sha256="",
            appfw_size_bytes=0,
            appfw_is_aarch64_elf=False,
            upm_ko_size_bytes=0,
            upm_ko_is_aarch64_elf=False,
            errors=(f"Local BYOF donors missing ({', '.join(missing)})",),
        )

    use_live = (not clean_room_req) and donors_present
    if not use_live:
        dt = time.perf_counter() - t0
        return Phase302DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            passed=True,
            elapsed_seconds=round(dt, 6),
            within_150ms_budget=(dt < DONOR_INSPECTION_MAX_SECONDS),
            raw_firmware_bytes_leaked=PHASE302_RAW_FIRMWARE_BYTES_LEAKED,
            im_elf_sha256=FX3_IM_ELF_EXPECTED_SHA256,
            libjiritsu_sha256=LIBJIRITSU_EXPECTED_SHA256,
            libusbbuspower_sha256=FX3_LIBUSBBUSPOWER_EXPECTED_SHA256,
            wlan_rsrc_sha256=FX6_WLAN_RSRC_DONOR_SHA256,
            appfw_size_bytes=FX6_APPFW_EXPECTED_SIZE,
            appfw_is_aarch64_elf=True,
            upm_ko_size_bytes=8192,
            upm_ko_is_aarch64_elf=True,
            errors=(),
        )

    errors: List[str] = []

    def _digest(path: Path, expected_sha: str, expected_sz: Optional[int], label: str) -> str:
        if not path.is_file():
            errors.append(f"missing {label}: {path}")
            return ""
        sz, sha, hdr = read_only_o_rdonly_digest_and_header(path)
        is_mag, is_64, e_mach, _ = _parse_elf64_header_and_pt_load(hdr)
        if not (is_mag and is_64 and e_mach == EM_AARCH64):
            errors.append(f"invalid AArch64 ELF header for {label}: {path}")
        if expected_sz is not None and sz != expected_sz:
            errors.append(f"size mismatch for {label}: {sz} != {expected_sz}")
        if sha != expected_sha:
            errors.append(f"sha256 mismatch for {label}: {sha[:16]} != {expected_sha[:16]}")
        return sha

    im_sha = _digest(im_path, FX3_IM_ELF_EXPECTED_SHA256, FX3_IM_ELF_EXPECTED_SIZE, "im.elf")
    jit_sha = _digest(jit_path, LIBJIRITSU_EXPECTED_SHA256, LIBJIRITSU_EXPECTED_SIZE, "libJiritsu.so")
    usb_sha = _digest(
        usb_path,
        FX3_LIBUSBBUSPOWER_EXPECTED_SHA256,
        FX3_LIBUSBBUSPOWER_EXPECTED_SIZE,
        "libUsbBusPower.so",
    )
    wlan_sha = _digest(wlan_path, FX6_WLAN_RSRC_DONOR_SHA256, None, "libWlanResource.so")

    appfw_sz = 0
    appfw_ok = False
    if not appfw_path.is_file():
        errors.append(f"missing appFw.so: {appfw_path}")
    else:
        appfw_sz, hdr, _ = _read_bounded_slice_o_rdonly(appfw_path, 4096)
        try:
            is_mag, is_64, e_mach, _ = _parse_elf64_header_and_pt_load(hdr)
            appfw_ok = bool(is_mag and is_64 and e_mach == EM_AARCH64)
            if not appfw_ok:
                errors.append("appFw.so is not an AArch64 ELF64 binary")
        except Exception as exc:
            errors.append(f"appFw.so ELF header parse error: {exc}")
        if appfw_sz != FX6_APPFW_EXPECTED_SIZE:
            errors.append(f"appFw.so size mismatch: {appfw_sz} != {FX6_APPFW_EXPECTED_SIZE}")

    upm_sz = 0
    upm_ok = False
    if not upm_path.is_file():
        errors.append(f"missing upm.ko: {upm_path}")
    else:
        upm_sz, hdr, _ = _read_bounded_slice_o_rdonly(upm_path, 4096)
        try:
            is_mag, is_64, e_mach, _ = _parse_elf64_header_and_pt_load(hdr)
            upm_ok = bool(is_mag and is_64 and e_mach == EM_AARCH64)
            if not upm_ok:
                errors.append("upm.ko is not an AArch64 ELF64 binary")
        except Exception as exc:
            errors.append(f"upm.ko ELF header parse error: {exc}")

    dt = time.perf_counter() - t0
    within_budget = dt < DONOR_INSPECTION_MAX_SECONDS
    if not within_budget:
        errors.append(f"bounded O_RDONLY inspection exceeded budget: {dt:.4f}s")

    return Phase302DonorInspectionResult(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        passed=(len(errors) == 0),
        elapsed_seconds=round(dt, 6),
        within_150ms_budget=within_budget,
        raw_firmware_bytes_leaked=PHASE302_RAW_FIRMWARE_BYTES_LEAKED,
        im_elf_sha256=im_sha,
        libjiritsu_sha256=jit_sha,
        libusbbuspower_sha256=usb_sha,
        wlan_rsrc_sha256=wlan_sha,
        appfw_size_bytes=appfw_sz,
        appfw_is_aarch64_elf=appfw_ok,
        upm_ko_size_bytes=upm_sz,
        upm_ko_is_aarch64_elf=upm_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group A (Wave 53 — Lens Comp, Built-in AF Illuminator LED & Folder/Rating Vault)
# ---------------------------------------------------------------------------


def evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P302_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    focus_mode: str = "MF",
    # Wave 53.1 Lens Compensation
    shading_comp: str = "AUTO",
    exposed_shading_modes: Sequence[str] = P302_SHADING_TWO_MODES,
    dormant_shading_auto_low_requested: bool = False,
    chromatic_aberration_comp: str = "AUTO",
    distortion_comp: str = "OFF",
    steadyshot_mode: str = "STANDARD",
    lens_distortion_comp_locked_auto: bool = False,
    unchipped_manual_lens_attached: bool = False,
    expect_lens_comp_active_on_manual_lens: bool = False,
    breathing_comp: str = "OFF",
    breathing_comp_compliant_lens: bool = True,
    hdmi_raw_output: bool = False,
    claimed_static_lens_comp_wiped_by_camera_reset: bool = False,
    fx6_lens_comp_in_scene_file_claimed: bool = False,
    # Wave 53.2 Built-in AF Illuminator LED vs FX6 Absence & Movie AF Params
    fx3_builtin_af_illuminator_present: bool = True,
    fx6_builtin_af_illuminator_present: bool = False,
    af_illuminator: str = "AUTO",
    af_illuminator_firing_requested: bool = False,
    af_illuminator_distance_m: float = 1.5,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    af_transition_speed: int = 5,
    af_subj_shift_sensitivity: int = 5,
    af_assist: str = "OFF",
    af_assist_compatible_lens: bool = True,
    # Wave 53.3 Non-Resettable AF Params
    aperture_drive_in_af: str = "STANDARD",
    af_with_shutter: str = "ON",
    pre_af: str = "OFF",
    lens_pre_af_supported: bool = True,
    circ_of_focus_point: str = "DOES_NOT_CIRCULATE",
    expect_diagonal_focus_wrap: bool = False,
    focus_area_color: str = "WHITE",
    claimed_af_five_params_wiped_by_camera_reset: bool = False,
    fx6_aperture_drive_in_af_claimed: bool = False,
    # Wave 53.4 File/Folder Settings & Playback Rating Slot-1 Vault Guard
    still_folder_name_mode: str = "STANDARD_FORM",
    select_rec_folder_enabled_claimed: bool = False,
    still_file_number_mode: str = "SERIES",
    still_file_prefix: str = "DSC",
    still_folder_image_count: int = 10,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    create_new_folder_requested: bool = False,
    create_new_folder_slot: int = 2,
    forced_file_number_reset_requested: bool = False,
    forced_file_number_reset_slot: int = 2,
    playback_media_slot: int = 1,
    playback_rating_requested: bool = False,
    rating_stars: int = 3,
    add_rating_requested: bool = False,
    target_image_already_rated: bool = False,
) -> P302CheckGroupALensCompAfIllumFolderRatingResult:
    """Validate Wave 53 Lens Comp, Built-in AF Illuminator LED, 5 AF params & Folder/Rating Guard."""
    errors: List[str] = []

    try:
        fw_tuple = _parse_fw_tuple(body_fw)
    except ValueError as exc:
        fw_tuple = (0, 0)
        errors.append(f"{P302_GA_ERR_MODEL_OR_FW_FLOOR}: invalid body_fw={body_fw!r}: {exc}")

    if int(body_model_id) != TARGET_MODEL_ID_INT:
        errors.append(
            f"{P302_GA_ERR_MODEL_OR_FW_FLOOR}: unexpected body_model_id={hex(int(body_model_id))}"
        )
    if fw_tuple < MIN_BODY_FW_TUPLE:
        errors.append(
            f"{P302_GA_ERR_MODEL_OR_FW_FLOOR}: body_fw={body_fw!r} below 2.04 floor"
        )
    if str(sony_help_guide_id).strip() != P302_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P302_GA_ERR_MODEL_OR_FW_FLOOR}: expected sony_help_guide_id={P302_SONY_HELP_GUIDE_ID!r}, got {sony_help_guide_id!r}"
        )

    norm_reset = _norm_upper(reset_action)
    if norm_reset not in P302_VALID_RESET_ACTIONS:
        errors.append(f"{P302_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action={reset_action!r}")

    norm_shoot = _norm_upper(shoot_mode)
    if norm_shoot not in P302_VALID_SHOOT_MODES:
        errors.append(f"{P302_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode={shoot_mode!r}")

    norm_focus = _norm_upper(focus_mode)
    if norm_focus not in P302_VALID_FOCUS_MODES:
        errors.append(f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: invalid focus_mode={focus_mode!r}")

    # 1. Lens Compensation & Dormant Auto: Low (0x6c9c)
    norm_shading = _norm_upper(shading_comp)
    norm_exposed_shading = tuple(_norm_upper(x) for x in exposed_shading_modes)
    dormant_auto_low_rejected = True
    if (
        norm_shading == "AUTO_LOW"
        or dormant_shading_auto_low_requested
        or "AUTO_LOW" in norm_exposed_shading
    ):
        dormant_auto_low_rejected = False
        errors.append(
            f"{P302_GA_ERR_SHADING_AUTO_LOW_EOPNOTSUPP}: dormant Shading Comp. [Auto: Low] "
            f"({P302_DORMANT_SHADING_AUTO_LOW_SYMBOL} / {P302_DORMANT_SHADING_AUTO_LOW_RESID16_HEX}) "
            f"rejected fail-closed with EOPNOTSUPP={P302_ERRNO_EOPNOTSUPP}"
        )
    elif norm_shading not in P302_SHADING_TWO_MODES or norm_exposed_shading != P302_SHADING_TWO_MODES:
        errors.append(
            f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: [Shading Comp.] ({P302_SHADING_COMP_RESID16_HEX}) "
            f"must expose exact 2 modes {P302_SHADING_TWO_MODES}, got {norm_shading!r} / {norm_exposed_shading}"
        )

    norm_chroma = _norm_upper(chromatic_aberration_comp)
    norm_dist = _norm_upper(distortion_comp)
    norm_ss = _norm_upper(steadyshot_mode)
    norm_breath = _norm_upper(breathing_comp)
    if norm_chroma not in P302_SHADING_TWO_MODES:
        errors.append(
            f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: invalid chromatic_aberration_comp={chromatic_aberration_comp!r}"
        )
    if norm_dist not in P302_SHADING_TWO_MODES:
        errors.append(
            f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: invalid distortion_comp={distortion_comp!r}"
        )
    if norm_ss not in P302_VALID_STEADYSHOT_MODES:
        errors.append(
            f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: invalid steadyshot_mode={steadyshot_mode!r}"
        )
    if (lens_distortion_comp_locked_auto or norm_ss == "ACTIVE") and norm_dist != "AUTO":
        errors.append(
            f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: [Distortion Comp.] ({P302_DISTORTION_COMP_RESID16_HEX}) "
            f"is force-locked to AUTO when SteadyShot=ACTIVE or lens requires auto distortion comp"
        )
    if unchipped_manual_lens_attached and expect_lens_comp_active_on_manual_lens:
        errors.append(
            f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: unchipped manual lenses lock out Lens Compensation items"
        )
    if norm_breath not in P302_VALID_ON_OFF:
        errors.append(
            f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: invalid breathing_comp={breathing_comp!r}"
        )
    elif norm_breath == "ON":
        if norm_shoot == "PHOTO" or hdmi_raw_output or not breathing_comp_compliant_lens:
            errors.append(
                f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: [Breathing Comp.] ({P302_BREATHING_COMP_RESID16_HEX})=ON "
                "is blocked in PHOTO, HDMI RAW, or non-compliant lenses"
            )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_static_lens_comp_wiped_by_camera_reset:
        errors.append(
            f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: Shading/Chromatic/Distortion Comp. survive [Camera Settings Reset] (Initialize-only)"
        )
    if fx6_lens_comp_in_scene_file_claimed:
        errors.append(
            f"{P302_GA_ERR_LENS_COMP_LOCK_OR_RESET_BOUNDARY}: ILME-FX6 places Lens Comp under Technical>Lens (All File), never Scene File"
        )

    # 2. Built-in AF Illuminator LED vs FX6 Absence & Movie AF Params
    if not fx3_builtin_af_illuminator_present:
        errors.append(
            f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: ILME-FX3 possesses physical front AF illuminator / Self-timer LED (#8, 0.3..3.0m)"
        )
    if fx6_builtin_af_illuminator_present:
        errors.append(
            f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: ILME-FX6 has ZERO built-in AF illuminator"
        )

    norm_illum = _norm_upper(af_illuminator)
    if norm_illum not in P302_VALID_AF_ILLUMINATOR_MODES:
        errors.append(
            f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: invalid af_illuminator={af_illuminator!r}"
        )

    illum_gate_ok = True
    if af_illuminator_firing_requested:
        if (
            norm_illum != "AUTO"
            or norm_shoot != "PHOTO"
            or norm_focus not in ("AF_S", "AF_A")
            or focus_magnifier_active
            or mount_adaptor_attached
        ):
            illum_gate_ok = False
            errors.append(
                f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: [AF Illuminator] ({P302_AF_ILLUMINATOR_RESID16_HEX}/{P302_AF_ILLUMINATOR_UXC_RESID16_HEX}) "
                "requires PHOTO + AF-S (or stationary AF-A) with Focus Magnifier OFF and no Mount Adaptor"
            )
        if not (
            P302_AF_ILLUMINATOR_RANGE_MIN_M
            <= float(af_illuminator_distance_m)
            <= P302_AF_ILLUMINATOR_RANGE_MAX_M
        ):
            illum_gate_ok = False
            errors.append(
                f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: AF illuminator effective range is 0.3..3.0 m, got {af_illuminator_distance_m} m"
            )

    if not (P302_AF_TRANSITION_SPEED_MIN <= int(af_transition_speed) <= P302_AF_TRANSITION_SPEED_MAX):
        errors.append(
            f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: [AF Transition Speed] ({P302_AF_TRANSITION_SPEED_RESID16_HEX}) must be 1..7, got {af_transition_speed}"
        )
    if not (P302_AF_SUBJ_SHIFT_SENS_MIN <= int(af_subj_shift_sensitivity) <= P302_AF_SUBJ_SHIFT_SENS_MAX):
        errors.append(
            f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: [AF Subj. Shift Sensitivity] ({P302_AF_SUBJ_SHIFT_SENS_RESID16_HEX}) must be 1..5, got {af_subj_shift_sensitivity}"
        )
    norm_assist = _norm_upper(af_assist)
    if norm_assist not in P302_VALID_ON_OFF:
        errors.append(f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: invalid af_assist={af_assist!r}")
    elif norm_assist == "ON" and (
        norm_shoot not in ("MOVIE", "S_AND_Q")
        or norm_focus != "AF_C"
        or not af_assist_compatible_lens
    ):
        errors.append(
            f"{P302_GA_ERR_AF_ILLUMINATOR_OR_FX6_ABSENCE}: [AF Assist] ({P302_AF_ASSIST_RESID16_HEX})=ON requires Movie/S&Q + AF-C + compatible lens"
        )

    # 3. Non-Resettable AF Params (Aperture Drive in AF, AF w/ Shutter, Pre-AF, Circ, Color)
    norm_ap_drv = _norm_upper(aperture_drive_in_af)
    norm_af_shutter = _norm_upper(af_with_shutter)
    norm_pre_af = _norm_upper(pre_af)
    norm_circ = _norm_upper(circ_of_focus_point)
    norm_color = _norm_upper(focus_area_color)

    if norm_ap_drv not in P302_APERTURE_DRIVE_THREE_MODES:
        errors.append(
            f"{P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC}: invalid aperture_drive_in_af={aperture_drive_in_af!r}"
        )
    if norm_af_shutter not in P302_VALID_ON_OFF:
        errors.append(
            f"{P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC}: invalid af_with_shutter={af_with_shutter!r}"
        )
    if norm_pre_af not in P302_VALID_ON_OFF:
        errors.append(f"{P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC}: invalid pre_af={pre_af!r}")
    elif norm_pre_af == "ON" and (norm_shoot != "PHOTO" or not lens_pre_af_supported):
        errors.append(
            f"{P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC}: [Pre-AF] ({P302_PRE_AF_RESID16_HEX})=ON requires PHOTO + LENS_PRE_AF_SUPPORT lens"
        )
    if norm_circ not in P302_VALID_CIRC_FOCUS_POINT_MODES:
        errors.append(
            f"{P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC}: invalid circ_of_focus_point={circ_of_focus_point!r}"
        )
    if expect_diagonal_focus_wrap:
        errors.append(
            f"{P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC}: [Circ. of Focus Point] ({P302_CIRC_FOCUS_POINT_RESID16_HEX}) wraps orthogonally ONLY (no diagonal wrap)"
        )
    if norm_color not in P302_VALID_FOCUS_AREA_COLORS:
        errors.append(
            f"{P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC}: invalid focus_area_color={focus_area_color!r}"
        )
    five_survive_reset = not (
        norm_reset == "CAMERA_SETTINGS_RESET" and claimed_af_five_params_wiped_by_camera_reset
    )
    if not five_survive_reset:
        errors.append(
            f"{P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC}: Aperture Drive in AF / AF w/ Shutter / Pre-AF / Circ. of Focus Point / Focus Area Color survive [Camera Settings Reset] (Initialize-only)"
        )
    if fx6_aperture_drive_in_af_claimed:
        errors.append(
            f"{P302_GA_ERR_AF_FIVE_PARAMS_PERSISTENCE_OR_CIRC}: ILME-FX6 lacks Aperture Drive in AF / AF w/ Shutter / Pre-AF / Circ. / Focus Area Color"
        )

    # 4. File/Folder Settings & Playback Rating Slot-1 Vault Guard
    norm_folder_mode = _norm_upper(still_folder_name_mode)
    norm_file_num = _norm_upper(still_file_number_mode)
    if norm_folder_mode not in P302_VALID_STILL_FOLDER_NAME_MODES:
        errors.append(
            f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: invalid still_folder_name_mode={still_folder_name_mode!r}"
        )
    if norm_folder_mode == "DATE_FORM" and select_rec_folder_enabled_claimed:
        errors.append(
            f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: [Select REC Folder] is disabled under [Folder Name]=[Date Form]"
        )
    if norm_file_num not in P302_VALID_STILL_FILE_NUMBER_MODES:
        errors.append(
            f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: invalid still_file_number_mode={still_file_number_mode!r}"
        )
    if not P302_STILL_PREFIX_NO_LEADING_UNDERSCORE_RE.match(still_file_prefix):
        errors.append(
            f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: [Set File Name] prefix {still_file_prefix!r} must be 3 chars without leading '_'"
        )
    if not (0 <= int(still_folder_image_count) <= P302_FOLDER_NAME_MAX_IMAGES):
        errors.append(
            f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: folder image count {still_folder_image_count} exceeds 4,000 limit"
        )

    vault_guard_ok = True
    slot1_locked = bool(slot1_contains_tier0_dump or slot1_wp_locked)
    if create_new_folder_requested and int(create_new_folder_slot) == 1 and slot1_locked:
        vault_guard_ok = False
        errors.append(
            f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: [Create New Folder] on Slot 1 blocked fail-closed (EROFS={P302_ERRNO_EROFS}/EBUSY={P302_ERRNO_EBUSY})"
        )
    if forced_file_number_reset_requested and int(forced_file_number_reset_slot) == 1 and slot1_locked:
        vault_guard_ok = False
        errors.append(
            f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: [Forced File Number Reset] on Slot 1 blocked fail-closed (EROFS={P302_ERRNO_EROFS}/EBUSY={P302_ERRNO_EBUSY})"
        )
    if playback_rating_requested:
        if not (P302_STILL_RATING_MIN_STARS <= int(rating_stars) <= P302_STILL_RATING_MAX_STARS):
            errors.append(
                f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: [Rating] stars must be 1..5, got {rating_stars}"
            )
        if int(playback_media_slot) == 1 and slot1_locked:
            vault_guard_ok = False
            errors.append(
                f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: Playback [Rating] EXIF/AVF_INFO write on Slot 1 Tier-0 Vault blocked fail-closed (EROFS={P302_ERRNO_EROFS}/EBUSY={P302_ERRNO_EBUSY})"
            )
    if add_rating_requested:
        if norm_shoot != "PHOTO" or target_image_already_rated:
            errors.append(
                f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: [Add Rating] applies to unrated Still images only"
            )
        if int(playback_media_slot) == 1 and slot1_locked:
            vault_guard_ok = False
            errors.append(
                f"{P302_GA_ERR_FOLDER_OR_RATING_SLOT1_VAULT_EROFS}: [Add Rating] write on Slot 1 Tier-0 Vault blocked fail-closed (EROFS={P302_ERRNO_EROFS})"
            )

    return P302CheckGroupALensCompAfIllumFolderRatingResult(
        check_group_id=P302_CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        sony_help_guide_id=sony_help_guide_id,
        shading_comp=norm_shading,
        dormant_auto_low_rejected=dormant_auto_low_rejected,
        chromatic_aberration_comp=norm_chroma,
        distortion_comp=norm_dist,
        breathing_comp=norm_breath,
        fx3_builtin_af_illuminator_present=bool(fx3_builtin_af_illuminator_present),
        fx6_builtin_af_illuminator_present=bool(fx6_builtin_af_illuminator_present),
        af_illuminator=norm_illum,
        af_illuminator_still_afs_gate_verified=illum_gate_ok,
        aperture_drive_in_af=norm_ap_drv,
        af_with_shutter=norm_af_shutter,
        pre_af=norm_pre_af,
        circ_of_focus_point=norm_circ,
        focus_area_color=norm_color,
        five_af_params_survive_camera_reset=five_survive_reset,
        slot1_folder_rating_firewall_enforced=vault_guard_ok,
        slot1_metadata_sector_writes=0,
        slot1_avf_info_mutated=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group B (Wave 54 — Switch V/H, 14-Limit, 5-Mode Std. Adj, TC & Copy Trap)
# ---------------------------------------------------------------------------


def evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
    *,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    focus_mode: str = "MF",
    exposure_mode: str = "MANUAL_EXPOSURE",
    digital_zoom_active: bool = False,
    focus_magnifier_active: bool = False,
    # Wave 54.1 Switch V/H AF Area & 14-item Focus Area Limit
    switch_vh_af_area: str = "OFF",
    body_roll_orientation: str = "0_DEGREES",
    fx6_switch_vh_af_area_claimed: bool = False,
    exposed_focus_area_limit_items: Sequence[str] = P302_FOCUS_AREA_LIMIT_14_ITEMS,
    focus_area_limit_selected_count: int = 14,
    dormant_focus_area_requested: str = "NONE",
    fx6_focus_area_limit_claimed: bool = False,
    # Wave 54.2 Exposure Std. Adjust (5 modes) & Bracket Settings
    exposed_exposure_std_metering_modes: Sequence[str] = P302_EXPOSURE_STD_ADJUST_5_METERING_MODES,
    exposure_std_adjust_metering_mode: str = "MULTI",
    exposure_std_adjust_ev: float = 0.0,
    expect_std_adjust_changes_exif_exposure_comp: bool = False,
    claimed_exposure_std_adjust_wiped_by_camera_reset: bool = False,
    fx6_exposure_std_adjust_claimed: bool = False,
    bracket_selftimer: str = "OFF",
    bracket_order: str = "0_MINUS_PLUS",
    bracket_settings_active_in_movie_claimed: bool = False,
    # Wave 54.3 TC/UB Format & BNC Absence
    video_system: str = "NTSC",
    rec_frame_rate: str = "23.98P",
    tc_format: str = "NDF",
    user_bit_time_rec: str = "OFF",
    tcub_disp_setting: str = "TC",
    fx3_builtin_bnc_tc_in_out_switch_claimed: bool = False,
    claimed_tcub_6items_wiped_by_camera_reset: bool = False,
    # Wave 54.4 CRITICAL BENCH FIREWALL: Playback [Copy] Reverse-Direction Slot-1 Trap & Slide Show
    playback_media_slot: int = 1,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    playback_copy_requested: bool = False,
    copy_battery_ok: bool = True,
    copy_target_media_speed_ok: bool = True,
    copy_dest_slot_present: bool = True,
    expect_copy_preserves_group_or_protect: bool = False,
    fx6_in_camera_copy_clip_claimed: bool = False,
    slide_show_requested: bool = False,
    slide_show_repeat: str = "OFF",
    slide_show_interval_sec: int = 3,
    slide_show_view_mode: str = "DATE_VIEW",
) -> P302CheckGroupBSwitchVhLimit14StdAdjTcCopyResult:
    """Validate Wave 54 Switch V/H, 14-item Focus Area Limit, 5-mode Std. Adjust, TC & Copy Slot-1 Trap."""
    errors: List[str] = []
    norm_reset = _norm_upper(reset_action)
    norm_shoot = _norm_upper(shoot_mode)
    norm_focus = _norm_upper(focus_mode)
    norm_exp = _norm_upper(exposure_mode)

    # 1. Switch V/H AF Area (Still AF-C + 0/90/270 deg roll)
    norm_vh = _norm_upper(switch_vh_af_area)
    norm_roll = _norm_upper(body_roll_orientation)
    if norm_vh not in P302_VALID_SWITCH_VH_MODES:
        errors.append(f"{P302_GB_ERR_SWITCH_VH_AF_AREA_GATE}: invalid switch_vh_af_area={switch_vh_af_area!r}")
    if norm_roll not in P302_VALID_BODY_ROLL_STATES:
        errors.append(f"{P302_GB_ERR_SWITCH_VH_AF_AREA_GATE}: invalid body_roll_orientation={body_roll_orientation!r}")
    if norm_vh != "OFF":
        if (
            norm_shoot != "PHOTO"
            or norm_focus != "AF_C"
            or norm_exp == "INTELLIGENT_AUTO"
            or digital_zoom_active
            or focus_magnifier_active
            or norm_roll == "INVALID_VERTICAL_PITCH"
        ):
            errors.append(
                f"{P302_GB_ERR_SWITCH_VH_AF_AREA_GATE}: [Switch V/H AF Area] ({P302_SWITCH_VH_AF_AREA_RESID16_HEX})={norm_vh} "
                "requires Still + AF-C + 0/90/270 deg orientation (not Movie/S&Q/iAuto/DigitalZoom/FocusMag/VerticalPitch)"
            )
    if fx6_switch_vh_af_area_claimed:
        errors.append(f"{P302_GB_ERR_SWITCH_VH_AF_AREA_GATE}: ILME-FX6 lacks [Switch V/H AF Area]")

    # 2. Focus Area Limit (14 exact checkboxes, >= 2 minimum, dormant XL/XS/Custom1..3 blocked)
    norm_limit_items = tuple(_norm_upper(x) for x in exposed_focus_area_limit_items)
    norm_dormant_fa = _norm_upper(dormant_focus_area_requested)
    dormant_fa_rejected = True
    if (
        norm_dormant_fa in P302_DORMANT_FOCUS_AREAS
        or any(d in norm_limit_items for d in P302_DORMANT_FOCUS_AREAS)
    ):
        dormant_fa_rejected = False
        errors.append(
            f"{P302_GB_ERR_FOCUS_AREA_LIMIT_14_OR_MIN2}: dormant Focus Area ({norm_dormant_fa}) rejected fail-closed with EOPNOTSUPP={P302_ERRNO_EOPNOTSUPP}"
        )
    if norm_limit_items != P302_FOCUS_AREA_LIMIT_14_ITEMS:
        errors.append(
            f"{P302_GB_ERR_FOCUS_AREA_LIMIT_14_OR_MIN2}: [Focus Area Limit] ({P302_FOCUS_AREA_LIMIT_RESID16_HEX}) must expose exact 14 checkboxes"
        )
    if not (
        P302_FOCUS_AREA_LIMIT_MIN_SELECTED
        <= int(focus_area_limit_selected_count)
        <= len(P302_FOCUS_AREA_LIMIT_14_ITEMS)
    ):
        errors.append(
            f"{P302_GB_ERR_FOCUS_AREA_LIMIT_14_OR_MIN2}: [Focus Area Limit] ({P302_FOCUS_AREA_LIMIT_MIN_SELECTED_RESID16_HEX}) requires >= 2 and <= 14 selected items, got {focus_area_limit_selected_count}"
        )
    if fx6_focus_area_limit_claimed:
        errors.append(f"{P302_GB_ERR_FOCUS_AREA_LIMIT_14_OR_MIN2}: ILME-FX6 lacks [Focus Area Limit]")

    # 3. Exposure Std. Adjust (5 metering modes, -1.0..+1.0 EV in 1/6 EV steps, Initialize-only)
    norm_std_modes = tuple(_norm_upper(x) for x in exposed_exposure_std_metering_modes)
    norm_std_mode = _norm_upper(exposure_std_adjust_metering_mode)
    if norm_std_modes != P302_EXPOSURE_STD_ADJUST_5_METERING_MODES:
        errors.append(
            f"{P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET}: [Exposure Std. Adjust] ({P302_EXPOSURE_STD_ADJUST_RESID16_HEX}) "
            f"must expose ALL 5 metering modes {P302_EXPOSURE_STD_ADJUST_5_METERING_MODES}, got {norm_std_modes}"
        )
    if norm_std_mode not in P302_EXPOSURE_STD_ADJUST_5_METERING_MODES:
        errors.append(
            f"{P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET}: invalid exposure_std_adjust_metering_mode={exposure_std_adjust_metering_mode!r}"
        )
    ev_f = float(exposure_std_adjust_ev)
    if not (P302_EXPOSURE_STD_ADJUST_EV_MIN - 1e-6 <= ev_f <= P302_EXPOSURE_STD_ADJUST_EV_MAX + 1e-6) or not _approx_sixth_ev_step(ev_f):
        errors.append(
            f"{P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET}: [Exposure Std. Adjust] EV={ev_f} must be within -1.0..+1.0 EV in 1/6 EV steps"
        )
    if expect_std_adjust_changes_exif_exposure_comp:
        errors.append(
            f"{P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET}: [Exposure Std. Adjust] does NOT alter EXIF Exposure Comp."
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_exposure_std_adjust_wiped_by_camera_reset:
        errors.append(
            f"{P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET}: [Exposure Std. Adjust] survives [Camera Settings Reset] (Initialize-only)"
        )
    if fx6_exposure_std_adjust_claimed:
        errors.append(f"{P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET}: ILME-FX6 lacks [Exposure Std. Adjust]")

    norm_b_timer = _norm_upper(bracket_selftimer)
    norm_b_order = _norm_upper(bracket_order)
    if norm_b_timer not in P302_BRACKET_SELFTIMER_MODES:
        errors.append(
            f"{P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET}: invalid bracket_selftimer={bracket_selftimer!r}"
        )
    if norm_b_order not in P302_BRACKET_ORDER_MODES:
        errors.append(
            f"{P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET}: invalid bracket_order={bracket_order!r}"
        )
    if bracket_settings_active_in_movie_claimed:
        errors.append(
            f"{P302_GB_ERR_EXPOSURE_STD_ADJUST_5MODE_OR_BRACKET}: [Bracket Settings] is Still-only (absent in Movie/S&Q)"
        )

    # 4. Time Code Format (NDF lock in 23.98p/24.00p, hidden in PAL), User Bit Time Rec & BNC Absence
    norm_sys = _norm_upper(video_system)
    norm_fps = _norm_upper(rec_frame_rate)
    norm_tc_fmt = _norm_upper(tc_format)
    norm_ub_rec = _norm_upper(user_bit_time_rec)
    norm_tc_disp = _norm_upper(tcub_disp_setting)

    if norm_sys not in P302_VALID_VIDEO_SYSTEMS:
        errors.append(f"{P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE}: invalid video_system={video_system!r}")
    if norm_tc_fmt not in P302_TC_FORMAT_MODES:
        errors.append(f"{P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE}: invalid tc_format={tc_format!r}")
    if norm_sys == "NTSC" and norm_fps in P302_TC_NDF_LOCKED_FRAME_RATES and norm_tc_fmt != "NDF":
        errors.append(
            f"{P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE}: [Time Code Format] locks to NDF in {norm_fps} (DF={norm_tc_fmt} forbidden)"
        )
    if norm_sys == "PAL" and norm_tc_fmt == "DF":
        errors.append(
            f"{P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE}: [Time Code Format] hides in PAL (DF invalid in PAL)"
        )
    if norm_ub_rec not in P302_VALID_ON_OFF:
        errors.append(f"{P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE}: invalid user_bit_time_rec={user_bit_time_rec!r}")
    if norm_tc_disp not in P302_VALID_TCUB_DISP_SETTINGS:
        errors.append(f"{P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE}: invalid tcub_disp_setting={tcub_disp_setting!r}")
    if fx3_builtin_bnc_tc_in_out_switch_claimed:
        errors.append(
            f"{P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE}: ILME-FX3 has no built-in BNC TC IN/TC OUT port or physical IN/OUT switch (uses VMC-BNCM1)"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_tcub_6items_wiped_by_camera_reset:
        errors.append(
            f"{P302_GB_ERR_TC_FORMAT_NDF_PAL_OR_BNC_ABSENCE}: TC/UB 6 menu settings survive [Camera Settings Reset] (Initialize-only)"
        )

    # 5. CRITICAL BENCH FIREWALL: Playback [Copy] Reverse-Direction Slot-1 Trap & Slide Show
    if int(playback_media_slot) not in (1, 2):
        errors.append(
            f"{P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP}: invalid playback_media_slot={playback_media_slot}"
        )
        dest_slot = 1
    else:
        dest_slot = 2 if int(playback_media_slot) == 1 else 1

    copy_firewall_ok = True
    slot1_locked = bool(slot1_contains_tier0_dump or slot1_wp_locked)
    if playback_copy_requested:
        if dest_slot == 1 and slot1_locked:
            copy_firewall_ok = False
            errors.append(
                f"{P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP}: CRITICAL REVERSE-DIRECTION TRAP: "
                f"[Select Playback Media]==Slot 2 causes Playback [Copy] ({P302_PLAYBACK_COPY_RESID16_HEX}/{P302_PLAYBACK_COPY_FUNC}) "
                f"to write Slot 2 -> Slot 1! Blocked fail-closed (EROFS={P302_ERRNO_EROFS}/EBUSY={P302_ERRNO_EBUSY}) on Slot 1 Tier-0 Vault"
            )
        if not copy_battery_ok or not copy_target_media_speed_ok or not copy_dest_slot_present:
            errors.append(
                f"{P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP}: Playback [Copy] preconditions failed (battery/target speed/dest slot)"
            )
    if expect_copy_preserves_group_or_protect:
        errors.append(
            f"{P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP}: Playback [Copy] ungroups Burst/Interval images and clears [Protect] on copied target"
        )
    if fx6_in_camera_copy_clip_claimed:
        errors.append(
            f"{P302_GB_ERR_PLAYBACK_COPY_REVERSE_SLOT1_VAULT_TRAP}: ILME-FX6 has NO in-camera Copy Clip function (dormant PXW-FX9 remnant)"
        )

    norm_ss_rep = _norm_upper(slide_show_repeat)
    norm_ss_vm = _norm_upper(slide_show_view_mode)
    if norm_ss_rep not in P302_VALID_ON_OFF:
        errors.append(f"{P302_GB_ERR_SLIDESHOW_BOUNDARY}: invalid slide_show_repeat={slide_show_repeat!r}")
    if int(slide_show_interval_sec) not in P302_SLIDE_SHOW_INTERVALS_SEC:
        errors.append(f"{P302_GB_ERR_SLIDESHOW_BOUNDARY}: slide_show_interval_sec must be in {P302_SLIDE_SHOW_INTERVALS_SEC}")
    if slide_show_requested and norm_ss_vm not in P302_SLIDE_SHOW_VIEW_MODES:
        errors.append(
            f"{P302_GB_ERR_SLIDESHOW_BOUNDARY}: [Slide Show] applies to Date View or Folder View(Still) only, got {slide_show_view_mode!r}"
        )

    return P302CheckGroupBSwitchVhLimit14StdAdjTcCopyResult(
        check_group_id=P302_CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        switch_vh_af_area=norm_vh,
        body_roll_orientation=norm_roll,
        focus_area_limit_item_count=len(norm_limit_items),
        focus_area_limit_selected_count=int(focus_area_limit_selected_count),
        dormant_focus_areas_rejected=dormant_fa_rejected,
        exposure_std_metering_mode_count=len(norm_std_modes),
        exposure_std_adjust_metering_mode=norm_std_mode,
        exposure_std_adjust_ev=ev_f,
        tc_format=norm_tc_fmt,
        video_system=norm_sys,
        playback_media_slot=int(playback_media_slot),
        copy_destination_slot=dest_slot,
        playback_copy_requested=bool(playback_copy_requested),
        copy_reverse_slot1_firewall_enforced=copy_firewall_ok,
        slot1_data_sector_writes=0,
        slot1_avf_info_mutated=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group C (Wave 55 — Touch, 4-Mode DISP / Zero-EVF Blackout, AEL/Flash & Interval Play)
# ---------------------------------------------------------------------------


def evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
    *,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Wave 55.1 Touch Func. in Shooting & Touch Operation
    touch_operation: str = "OFF",
    touch_sensitivity: str = "STANDARD",
    touch_func_in_shooting: str = "TOUCH_TRACKING",
    exposed_touch_func_modes: Sequence[str] = P302_TOUCH_FUNC_SHOOTING_THREE_MODES,
    swipe_up: str = "OPEN_THE_FN_MENU",
    dormant_touch_trap_requested: str = "NONE",
    touch_panel_pad_present_claimed: bool = False,
    footer_icon_touch_enabled_claimed: bool = False,
    claimed_touch_4items_wiped_by_camera_reset: bool = False,
    # Wave 55.2 DISP (Screen Disp) Set & Zero-EVF Black-Screen Lockout Trap
    exposed_disp_shoot_modes: Sequence[str] = P302_DISP_MONITOR_SHOOT_FOUR_MODES,
    exposed_disp_playback_modes: Sequence[str] = P302_DISP_MONITOR_PLAYBACK_THREE_MODES,
    fx3_builtin_evf_present: bool = False,
    fx3_eye_sensor_present: bool = False,
    fx3_select_finder_monitor_present: bool = False,
    fx3_graphic_display_present: bool = False,
    activate_dormant_evf_finder_mode: bool = False,
    finder_monitor_key_claimed: bool = False,
    graphic_display_claimed: bool = False,
    monitor_off_evf_trap_claimed: bool = False,
    for_viewfinder_disp_claimed: bool = False,
    fx6_detachable_evf_loupe_claimed: bool = False,
    claimed_disp_modes_wiped_by_camera_reset: bool = False,
    # Wave 55.3 Still-Only AEL w/ Shutter & Flash Sub-Items
    ael_with_shutter: str = "AUTO",
    ael_with_shutter_in_movie_claimed: bool = False,
    claimed_ael_with_shutter_wiped_by_camera_reset: bool = False,
    exp_comp_set: str = "AMBIENT_AND_FLASH",
    wireless_flash: str = "OFF",
    external_flash_set_requested: bool = False,
    mi_shoe_external_flash_attached: bool = False,
    fx6_still_ael_or_wireless_flash_claimed: bool = False,
    # Wave 55.4 Playback Interval Speed 1..9 & Dormant Edit Traps + Slot-1 Guard
    interval_play_speed: int = P302_INTERVAL_PLAY_SPEED_DEFAULT,
    interval_play_speed_capped_at_5_claimed: bool = False,
    in_camera_interval_to_video_render_claimed: bool = False,
    exposed_playback_edit_items: Sequence[str] = P302_PLAYBACK_EDIT_ACTIVE_ITEMS,
    dormant_beauty_effect_requested: bool = False,
    dormant_trimming_requested: bool = False,
    playback_media_slot: int = 1,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    playback_photo_capture_requested: bool = False,
    playback_rotate_requested: bool = False,
) -> P302CheckGroupCTouchDispEvfAbsenceAelIntervalResult:
    """Validate Wave 55 Touch Shooting, 4-mode DISP / Zero-EVF Blackout, AEL/Flash & Interval Play."""
    errors: List[str] = []
    norm_reset = _norm_upper(reset_action)
    norm_shoot = _norm_upper(shoot_mode)

    # 1. Touch Operation & Touch Func. in Shooting
    norm_touch_op = _norm_upper(touch_operation)
    norm_touch_sens = _norm_upper(touch_sensitivity)
    norm_touch_func = _norm_upper(touch_func_in_shooting)
    norm_exposed_touch = tuple(_norm_upper(x) for x in exposed_touch_func_modes)
    norm_swipe = _norm_upper(swipe_up)
    norm_dormant_touch = _norm_upper(dormant_touch_trap_requested)

    if norm_touch_op not in P302_VALID_TOUCH_OPERATION_MODES:
        errors.append(
            f"{P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP}: invalid touch_operation={touch_operation!r}"
        )
    if norm_touch_sens not in P302_TOUCH_SENSITIVITY_TWO_MODES:
        errors.append(
            f"{P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP}: [Touch Sensitivity] must be STANDARD or SENSITIVE (not Responsive), got {touch_sensitivity!r}"
        )
    if norm_touch_func not in P302_TOUCH_FUNC_SHOOTING_THREE_MODES:
        errors.append(
            f"{P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP}: [Touch Func. in Shooting] must be in {P302_TOUCH_FUNC_SHOOTING_THREE_MODES}, got {touch_func_in_shooting!r}"
        )
    if norm_exposed_touch != P302_TOUCH_FUNC_SHOOTING_THREE_MODES:
        errors.append(
            f"{P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP}: [Touch Func. in Shooting] must expose exact 3 options {P302_TOUCH_FUNC_SHOOTING_THREE_MODES}, got {norm_exposed_touch}"
        )
    if norm_swipe not in P302_VALID_SWIPE_UP_MODES:
        errors.append(
            f"{P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP}: invalid swipe_up={swipe_up!r}"
        )

    dormant_touch_rejected = True
    if (
        norm_dormant_touch != "NONE"
        or touch_panel_pad_present_claimed
        or footer_icon_touch_enabled_claimed
        or any(
            t in norm_exposed_touch
            for t in ("TOUCH_SHUTTER", "TOUCH_AE", "TOUCH_PANEL_PAD", "FOOTER_ICON_TOUCH")
        )
    ):
        dormant_touch_rejected = False
        errors.append(
            f"{P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP}: dormant Touch Shutter/AE/Panel+Pad/Footer/Responsive/Swipe-LR rejected fail-closed with EOPNOTSUPP={P302_ERRNO_EOPNOTSUPP}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_touch_4items_wiped_by_camera_reset:
        errors.append(
            f"{P302_GC_ERR_TOUCH_SHOOTING_3MODE_OR_DORMANT_TRAP}: Touch Operation 4 setup items survive [Camera Settings Reset] (Initialize-only)"
        )

    # 2. DISP (Screen Disp) Set (4 shoot / 3 playback) & Zero-EVF Black-Screen Lockout Trap
    norm_disp_shoot = tuple(_norm_upper(x) for x in exposed_disp_shoot_modes)
    norm_disp_pb = tuple(_norm_upper(x) for x in exposed_disp_playback_modes)
    if norm_disp_shoot != P302_DISP_MONITOR_SHOOT_FOUR_MODES:
        errors.append(
            f"{P302_GC_ERR_DISP_4MODE_SHOOT_3MODE_PLAYBACK}: [DISP (Screen Disp) Set] shoot monitor must expose exact 4 modes {P302_DISP_MONITOR_SHOOT_FOUR_MODES}, got {norm_disp_shoot}"
        )
    if norm_disp_pb != P302_DISP_MONITOR_PLAYBACK_THREE_MODES:
        errors.append(
            f"{P302_GC_ERR_DISP_4MODE_SHOOT_3MODE_PLAYBACK}: [DISP (Screen Disp) Set] playback must expose exact 3 modes {P302_DISP_MONITOR_PLAYBACK_THREE_MODES}, got {norm_disp_pb}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_disp_modes_wiped_by_camera_reset:
        errors.append(
            f"{P302_GC_ERR_DISP_4MODE_SHOOT_3MODE_PLAYBACK}: [DISP (Screen Disp) Set] survives [Camera Settings Reset] (Initialize-only)"
        )

    zero_evf_firewall_ok = True
    if (
        fx3_builtin_evf_present
        or fx3_eye_sensor_present
        or fx3_select_finder_monitor_present
        or fx3_graphic_display_present
        or activate_dormant_evf_finder_mode
        or finder_monitor_key_claimed
        or graphic_display_claimed
        or monitor_off_evf_trap_claimed
        or for_viewfinder_disp_claimed
        or any("FINDER" in m or "GRAPHIC" in m or "MONITOR_OFF" in m for m in norm_disp_shoot)
    ):
        zero_evf_firewall_ok = False
        errors.append(
            f"{P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP}: CRITICAL BLACK-SCREEN LOCKOUT FIREWALL: "
            "ILME-FX3 has ZERO EVF, ZERO eye sensor, ZERO [Select Finder/Monitor], and ZERO [Graphic Display]; "
            f"activating dormant EVF/finder keys is blocked fail-closed (EOPNOTSUPP={P302_ERRNO_EOPNOTSUPP})"
        )
    if fx6_detachable_evf_loupe_claimed:
        errors.append(
            f"{P302_GC_ERR_ZERO_EVF_BLACK_SCREEN_LOCKOUT_TRAP}: ILME-FX6 uses TYPE_BUILTIN_EVF_NOT_EXIST + detachable 3.5-inch LCD & Viewfinder Hood (not EVF loupe)"
        )

    # 3. Still-Only AEL w/ Shutter & Flash Sub-Items
    norm_ael = _norm_upper(ael_with_shutter)
    norm_exp_comp_set = _norm_upper(exp_comp_set)
    norm_w_flash = _norm_upper(wireless_flash)
    if norm_ael not in P302_AEL_WITH_SHUTTER_THREE_MODES:
        errors.append(
            f"{P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE}: invalid ael_with_shutter={ael_with_shutter!r}"
        )
    if ael_with_shutter_in_movie_claimed:
        errors.append(
            f"{P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE}: [AEL w/ Shutter] is Still-only (absent in Movie/S&Q)"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_ael_with_shutter_wiped_by_camera_reset:
        errors.append(
            f"{P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE}: [AEL w/ Shutter] survives [Camera Settings Reset] (Initialize-only)"
        )
    if norm_exp_comp_set not in P302_VALID_EXP_COMP_SET_MODES:
        errors.append(
            f"{P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE}: invalid exp_comp_set={exp_comp_set!r}"
        )
    if norm_w_flash not in P302_VALID_ON_OFF:
        errors.append(
            f"{P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE}: invalid wireless_flash={wireless_flash!r}"
        )
    if external_flash_set_requested and (norm_shoot != "PHOTO" or not mi_shoe_external_flash_attached):
        errors.append(
            f"{P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE}: [External Flash Set.] requires PHOTO + direct MI-Shoe flash attachment"
        )
    if fx6_still_ael_or_wireless_flash_claimed:
        errors.append(
            f"{P302_GC_ERR_AEL_SHUTTER_OR_FLASH_STILL_GATE}: ILME-FX6 lacks [AEL w/ Shutter], [Wireless Flash], and [External Flash Set.]"
        )

    # 4. Playback Interval Speed 1..9 & Dormant Edit Traps + Slot-1 Vault Guard
    if not (P302_INTERVAL_PLAY_SPEED_MIN <= int(interval_play_speed) <= P302_INTERVAL_PLAY_SPEED_MAX):
        errors.append(
            f"{P302_GC_ERR_INTERVAL_SPEED_1TO9_OR_EDIT_VAULT_GUARD}: [Play Speed for Interval] must be 1..9 (default 5), got {interval_play_speed}"
        )
    if interval_play_speed_capped_at_5_claimed or in_camera_interval_to_video_render_claimed:
        errors.append(
            f"{P302_GC_ERR_INTERVAL_SPEED_1TO9_OR_EDIT_VAULT_GUARD}: [Play Speed for Interval] spans 1..9 (not 1..5 cap) and FX3 has no in-camera interval-to-video render"
        )

    norm_edit = tuple(_norm_upper(x) for x in exposed_playback_edit_items)
    dormant_edit_rejected = True
    if (
        dormant_beauty_effect_requested
        or dormant_trimming_requested
        or any(d in norm_edit for d in P302_DORMANT_PLAYBACK_EDIT_TRAPS)
    ):
        dormant_edit_rejected = False
        errors.append(
            f"{P302_GC_ERR_INTERVAL_SPEED_1TO9_OR_EDIT_VAULT_GUARD}: dormant Playback [Edit] traps ([Beauty Effect]/[Trimming]) rejected fail-closed with EOPNOTSUPP={P302_ERRNO_EOPNOTSUPP}"
        )

    slot1_locked = bool(slot1_contains_tier0_dump or slot1_wp_locked)
    if (playback_photo_capture_requested or playback_rotate_requested) and int(playback_media_slot) == 1 and slot1_locked:
        errors.append(
            f"{P302_GC_ERR_INTERVAL_SPEED_1TO9_OR_EDIT_VAULT_GUARD}: Playback [Photo Capture]/[Rotate] blocked fail-closed (EROFS={P302_ERRNO_EROFS}/EBUSY={P302_ERRNO_EBUSY}) on Slot 1 Tier-0 Vault"
        )

    return P302CheckGroupCTouchDispEvfAbsenceAelIntervalResult(
        check_group_id=P302_CHECK_GROUP_C_ID,
        passed=(len(errors) == 0),
        touch_operation=norm_touch_op,
        touch_sensitivity=norm_touch_sens,
        touch_func_in_shooting=norm_touch_func,
        swipe_up=norm_swipe,
        dormant_touch_traps_rejected=dormant_touch_rejected,
        exposed_disp_shoot_mode_count=len(norm_disp_shoot),
        exposed_disp_playback_mode_count=len(norm_disp_pb),
        fx3_builtin_evf_present=bool(fx3_builtin_evf_present),
        fx3_eye_sensor_present=bool(fx3_eye_sensor_present),
        fx3_select_finder_monitor_present=bool(fx3_select_finder_monitor_present),
        fx3_graphic_display_present=bool(fx3_graphic_display_present),
        zero_evf_blackout_firewall_enforced=zero_evf_firewall_ok,
        ael_with_shutter=norm_ael,
        wireless_flash=norm_w_flash,
        interval_play_speed=int(interval_play_speed),
        dormant_edit_traps_rejected=dormant_edit_rejected,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group D (Physical Bench Readiness Receipt, 16/16 H0 == H3 & Fail-Closed Redlines)
# ---------------------------------------------------------------------------


def build_simulated_phase302_tier0_receipts(
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
            f"PHASE302_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE302_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_p302_check_group_d_physical_bench_and_tier0(
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
) -> Tuple[P302CheckGroupDPhysicalBenchAndTier0Result, Tuple[str, ...]]:
    """Validate Check Group D: physical bench readiness, 16/16 H0==H3, dual 528B FX3RCPT1 & redlines."""
    errors: List[str] = []
    tier0_errors: List[str] = []
    warnings: List[str] = []

    if simulated_passive_tx_bytes != 0:
        errors.append(
            f"{P302_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: passive_tx_bytes_emitted={simulated_passive_tx_bytes} != 0"
        )
    if (
        claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P302_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: hardware_live_attach / persistent_emmc_writes / cross_model_flash are unconditionally LOCKED OFF"
        )

    surface_count = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_count, int(simulated_h0_h3_drifted_surfaces)))
    equals_count = max(0, surface_count - drifted)
    if drifted != 0:
        errors.append(
            f"{P302_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: {drifted} surfaces drifted between H0 and H3"
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
        raw_a, raw_b, sim_h0 = build_simulated_phase302_tier0_receipts(
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
                f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
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
                f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
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
            f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    elif raw_a is None or raw_b is None:
        tier0_errors.append(
            f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B 528B FX3RCPT1 receipts are required"
        )
    else:
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media_ok = True
            else:
                tier0_errors.append(
                    f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{P302_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    group_result = P302CheckGroupDPhysicalBenchAndTier0Result(
        check_group_id=P302_CHECK_GROUP_D_ID,
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


def evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P302_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    focus_mode: str = "MF",
    exposure_mode: str = "MANUAL_EXPOSURE",
    # Check Group A (Wave 53)
    shading_comp: str = "AUTO",
    exposed_shading_modes: Sequence[str] = P302_SHADING_TWO_MODES,
    dormant_shading_auto_low_requested: bool = False,
    chromatic_aberration_comp: str = "AUTO",
    distortion_comp: str = "OFF",
    steadyshot_mode: str = "STANDARD",
    lens_distortion_comp_locked_auto: bool = False,
    unchipped_manual_lens_attached: bool = False,
    expect_lens_comp_active_on_manual_lens: bool = False,
    breathing_comp: str = "OFF",
    breathing_comp_compliant_lens: bool = True,
    hdmi_raw_output: bool = False,
    claimed_static_lens_comp_wiped_by_camera_reset: bool = False,
    fx6_lens_comp_in_scene_file_claimed: bool = False,
    fx3_builtin_af_illuminator_present: bool = True,
    fx6_builtin_af_illuminator_present: bool = False,
    af_illuminator: str = "AUTO",
    af_illuminator_firing_requested: bool = False,
    af_illuminator_distance_m: float = 1.5,
    focus_magnifier_active: bool = False,
    mount_adaptor_attached: bool = False,
    af_transition_speed: int = 5,
    af_subj_shift_sensitivity: int = 5,
    af_assist: str = "OFF",
    af_assist_compatible_lens: bool = True,
    aperture_drive_in_af: str = "STANDARD",
    af_with_shutter: str = "ON",
    pre_af: str = "OFF",
    lens_pre_af_supported: bool = True,
    circ_of_focus_point: str = "DOES_NOT_CIRCULATE",
    expect_diagonal_focus_wrap: bool = False,
    focus_area_color: str = "WHITE",
    claimed_af_five_params_wiped_by_camera_reset: bool = False,
    fx6_aperture_drive_in_af_claimed: bool = False,
    still_folder_name_mode: str = "STANDARD_FORM",
    select_rec_folder_enabled_claimed: bool = False,
    still_file_number_mode: str = "SERIES",
    still_file_prefix: str = "DSC",
    still_folder_image_count: int = 10,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    create_new_folder_requested: bool = False,
    create_new_folder_slot: int = 2,
    forced_file_number_reset_requested: bool = False,
    forced_file_number_reset_slot: int = 2,
    playback_media_slot: int = 1,
    playback_rating_requested: bool = False,
    rating_stars: int = 3,
    add_rating_requested: bool = False,
    target_image_already_rated: bool = False,
    # Check Group B (Wave 54)
    digital_zoom_active: bool = False,
    switch_vh_af_area: str = "OFF",
    body_roll_orientation: str = "0_DEGREES",
    fx6_switch_vh_af_area_claimed: bool = False,
    exposed_focus_area_limit_items: Sequence[str] = P302_FOCUS_AREA_LIMIT_14_ITEMS,
    focus_area_limit_selected_count: int = 14,
    dormant_focus_area_requested: str = "NONE",
    fx6_focus_area_limit_claimed: bool = False,
    exposed_exposure_std_metering_modes: Sequence[str] = P302_EXPOSURE_STD_ADJUST_5_METERING_MODES,
    exposure_std_adjust_metering_mode: str = "MULTI",
    exposure_std_adjust_ev: float = 0.0,
    expect_std_adjust_changes_exif_exposure_comp: bool = False,
    claimed_exposure_std_adjust_wiped_by_camera_reset: bool = False,
    fx6_exposure_std_adjust_claimed: bool = False,
    bracket_selftimer: str = "OFF",
    bracket_order: str = "0_MINUS_PLUS",
    bracket_settings_active_in_movie_claimed: bool = False,
    video_system: str = "NTSC",
    rec_frame_rate: str = "23.98P",
    tc_format: str = "NDF",
    user_bit_time_rec: str = "OFF",
    tcub_disp_setting: str = "TC",
    fx3_builtin_bnc_tc_in_out_switch_claimed: bool = False,
    claimed_tcub_6items_wiped_by_camera_reset: bool = False,
    playback_copy_requested: bool = False,
    copy_battery_ok: bool = True,
    copy_target_media_speed_ok: bool = True,
    copy_dest_slot_present: bool = True,
    expect_copy_preserves_group_or_protect: bool = False,
    fx6_in_camera_copy_clip_claimed: bool = False,
    slide_show_requested: bool = False,
    slide_show_repeat: str = "OFF",
    slide_show_interval_sec: int = 3,
    slide_show_view_mode: str = "DATE_VIEW",
    # Check Group C (Wave 55)
    touch_operation: str = "OFF",
    touch_sensitivity: str = "STANDARD",
    touch_func_in_shooting: str = "TOUCH_TRACKING",
    exposed_touch_func_modes: Sequence[str] = P302_TOUCH_FUNC_SHOOTING_THREE_MODES,
    swipe_up: str = "OPEN_THE_FN_MENU",
    dormant_touch_trap_requested: str = "NONE",
    touch_panel_pad_present_claimed: bool = False,
    footer_icon_touch_enabled_claimed: bool = False,
    claimed_touch_4items_wiped_by_camera_reset: bool = False,
    exposed_disp_shoot_modes: Sequence[str] = P302_DISP_MONITOR_SHOOT_FOUR_MODES,
    exposed_disp_playback_modes: Sequence[str] = P302_DISP_MONITOR_PLAYBACK_THREE_MODES,
    fx3_builtin_evf_present: bool = False,
    fx3_eye_sensor_present: bool = False,
    fx3_select_finder_monitor_present: bool = False,
    fx3_graphic_display_present: bool = False,
    activate_dormant_evf_finder_mode: bool = False,
    finder_monitor_key_claimed: bool = False,
    graphic_display_claimed: bool = False,
    monitor_off_evf_trap_claimed: bool = False,
    for_viewfinder_disp_claimed: bool = False,
    fx6_detachable_evf_loupe_claimed: bool = False,
    claimed_disp_modes_wiped_by_camera_reset: bool = False,
    ael_with_shutter: str = "AUTO",
    ael_with_shutter_in_movie_claimed: bool = False,
    claimed_ael_with_shutter_wiped_by_camera_reset: bool = False,
    exp_comp_set: str = "AMBIENT_AND_FLASH",
    wireless_flash: str = "OFF",
    external_flash_set_requested: bool = False,
    mi_shoe_external_flash_attached: bool = False,
    fx6_still_ael_or_wireless_flash_claimed: bool = False,
    interval_play_speed: int = P302_INTERVAL_PLAY_SPEED_DEFAULT,
    interval_play_speed_capped_at_5_claimed: bool = False,
    in_camera_interval_to_video_render_claimed: bool = False,
    exposed_playback_edit_items: Sequence[str] = P302_PLAYBACK_EDIT_ACTIVE_ITEMS,
    dormant_beauty_effect_requested: bool = False,
    dormant_trimming_requested: bool = False,
    playback_photo_capture_requested: bool = False,
    playback_rotate_requested: bool = False,
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
) -> RealHwLensCompAfIlluminatorCopySlotEvfAbsenceReport:
    """Execute Phase 302 11th real-hardware physical bench readiness verifier (`A..D`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase302_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_p302_check_group_a_lens_comp_af_illum_folder_rating(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        shading_comp=shading_comp,
        exposed_shading_modes=exposed_shading_modes,
        dormant_shading_auto_low_requested=dormant_shading_auto_low_requested,
        chromatic_aberration_comp=chromatic_aberration_comp,
        distortion_comp=distortion_comp,
        steadyshot_mode=steadyshot_mode,
        lens_distortion_comp_locked_auto=lens_distortion_comp_locked_auto,
        unchipped_manual_lens_attached=unchipped_manual_lens_attached,
        expect_lens_comp_active_on_manual_lens=expect_lens_comp_active_on_manual_lens,
        breathing_comp=breathing_comp,
        breathing_comp_compliant_lens=breathing_comp_compliant_lens,
        hdmi_raw_output=hdmi_raw_output,
        claimed_static_lens_comp_wiped_by_camera_reset=claimed_static_lens_comp_wiped_by_camera_reset,
        fx6_lens_comp_in_scene_file_claimed=fx6_lens_comp_in_scene_file_claimed,
        fx3_builtin_af_illuminator_present=fx3_builtin_af_illuminator_present,
        fx6_builtin_af_illuminator_present=fx6_builtin_af_illuminator_present,
        af_illuminator=af_illuminator,
        af_illuminator_firing_requested=af_illuminator_firing_requested,
        af_illuminator_distance_m=af_illuminator_distance_m,
        focus_magnifier_active=focus_magnifier_active,
        mount_adaptor_attached=mount_adaptor_attached,
        af_transition_speed=af_transition_speed,
        af_subj_shift_sensitivity=af_subj_shift_sensitivity,
        af_assist=af_assist,
        af_assist_compatible_lens=af_assist_compatible_lens,
        aperture_drive_in_af=aperture_drive_in_af,
        af_with_shutter=af_with_shutter,
        pre_af=pre_af,
        lens_pre_af_supported=lens_pre_af_supported,
        circ_of_focus_point=circ_of_focus_point,
        expect_diagonal_focus_wrap=expect_diagonal_focus_wrap,
        focus_area_color=focus_area_color,
        claimed_af_five_params_wiped_by_camera_reset=claimed_af_five_params_wiped_by_camera_reset,
        fx6_aperture_drive_in_af_claimed=fx6_aperture_drive_in_af_claimed,
        still_folder_name_mode=still_folder_name_mode,
        select_rec_folder_enabled_claimed=select_rec_folder_enabled_claimed,
        still_file_number_mode=still_file_number_mode,
        still_file_prefix=still_file_prefix,
        still_folder_image_count=still_folder_image_count,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        create_new_folder_requested=create_new_folder_requested,
        create_new_folder_slot=create_new_folder_slot,
        forced_file_number_reset_requested=forced_file_number_reset_requested,
        forced_file_number_reset_slot=forced_file_number_reset_slot,
        playback_media_slot=playback_media_slot,
        playback_rating_requested=playback_rating_requested,
        rating_stars=rating_stars,
        add_rating_requested=add_rating_requested,
        target_image_already_rated=target_image_already_rated,
    )
    gb = evaluate_p302_check_group_b_switch_vh_limit14_stdadj_tc_and_copy_slot1(
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        focus_mode=focus_mode,
        exposure_mode=exposure_mode,
        digital_zoom_active=digital_zoom_active,
        focus_magnifier_active=focus_magnifier_active,
        switch_vh_af_area=switch_vh_af_area,
        body_roll_orientation=body_roll_orientation,
        fx6_switch_vh_af_area_claimed=fx6_switch_vh_af_area_claimed,
        exposed_focus_area_limit_items=exposed_focus_area_limit_items,
        focus_area_limit_selected_count=focus_area_limit_selected_count,
        dormant_focus_area_requested=dormant_focus_area_requested,
        fx6_focus_area_limit_claimed=fx6_focus_area_limit_claimed,
        exposed_exposure_std_metering_modes=exposed_exposure_std_metering_modes,
        exposure_std_adjust_metering_mode=exposure_std_adjust_metering_mode,
        exposure_std_adjust_ev=exposure_std_adjust_ev,
        expect_std_adjust_changes_exif_exposure_comp=expect_std_adjust_changes_exif_exposure_comp,
        claimed_exposure_std_adjust_wiped_by_camera_reset=claimed_exposure_std_adjust_wiped_by_camera_reset,
        fx6_exposure_std_adjust_claimed=fx6_exposure_std_adjust_claimed,
        bracket_selftimer=bracket_selftimer,
        bracket_order=bracket_order,
        bracket_settings_active_in_movie_claimed=bracket_settings_active_in_movie_claimed,
        video_system=video_system,
        rec_frame_rate=rec_frame_rate,
        tc_format=tc_format,
        user_bit_time_rec=user_bit_time_rec,
        tcub_disp_setting=tcub_disp_setting,
        fx3_builtin_bnc_tc_in_out_switch_claimed=fx3_builtin_bnc_tc_in_out_switch_claimed,
        claimed_tcub_6items_wiped_by_camera_reset=claimed_tcub_6items_wiped_by_camera_reset,
        playback_media_slot=playback_media_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        playback_copy_requested=playback_copy_requested,
        copy_battery_ok=copy_battery_ok,
        copy_target_media_speed_ok=copy_target_media_speed_ok,
        copy_dest_slot_present=copy_dest_slot_present,
        expect_copy_preserves_group_or_protect=expect_copy_preserves_group_or_protect,
        fx6_in_camera_copy_clip_claimed=fx6_in_camera_copy_clip_claimed,
        slide_show_requested=slide_show_requested,
        slide_show_repeat=slide_show_repeat,
        slide_show_interval_sec=slide_show_interval_sec,
        slide_show_view_mode=slide_show_view_mode,
    )
    gc = evaluate_p302_check_group_c_touch_disp_evf_absence_ael_flash_and_interval(
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        touch_operation=touch_operation,
        touch_sensitivity=touch_sensitivity,
        touch_func_in_shooting=touch_func_in_shooting,
        exposed_touch_func_modes=exposed_touch_func_modes,
        swipe_up=swipe_up,
        dormant_touch_trap_requested=dormant_touch_trap_requested,
        touch_panel_pad_present_claimed=touch_panel_pad_present_claimed,
        footer_icon_touch_enabled_claimed=footer_icon_touch_enabled_claimed,
        claimed_touch_4items_wiped_by_camera_reset=claimed_touch_4items_wiped_by_camera_reset,
        exposed_disp_shoot_modes=exposed_disp_shoot_modes,
        exposed_disp_playback_modes=exposed_disp_playback_modes,
        fx3_builtin_evf_present=fx3_builtin_evf_present,
        fx3_eye_sensor_present=fx3_eye_sensor_present,
        fx3_select_finder_monitor_present=fx3_select_finder_monitor_present,
        fx3_graphic_display_present=fx3_graphic_display_present,
        activate_dormant_evf_finder_mode=activate_dormant_evf_finder_mode,
        finder_monitor_key_claimed=finder_monitor_key_claimed,
        graphic_display_claimed=graphic_display_claimed,
        monitor_off_evf_trap_claimed=monitor_off_evf_trap_claimed,
        for_viewfinder_disp_claimed=for_viewfinder_disp_claimed,
        fx6_detachable_evf_loupe_claimed=fx6_detachable_evf_loupe_claimed,
        claimed_disp_modes_wiped_by_camera_reset=claimed_disp_modes_wiped_by_camera_reset,
        ael_with_shutter=ael_with_shutter,
        ael_with_shutter_in_movie_claimed=ael_with_shutter_in_movie_claimed,
        claimed_ael_with_shutter_wiped_by_camera_reset=claimed_ael_with_shutter_wiped_by_camera_reset,
        exp_comp_set=exp_comp_set,
        wireless_flash=wireless_flash,
        external_flash_set_requested=external_flash_set_requested,
        mi_shoe_external_flash_attached=mi_shoe_external_flash_attached,
        fx6_still_ael_or_wireless_flash_claimed=fx6_still_ael_or_wireless_flash_claimed,
        interval_play_speed=interval_play_speed,
        interval_play_speed_capped_at_5_claimed=interval_play_speed_capped_at_5_claimed,
        in_camera_interval_to_video_render_claimed=in_camera_interval_to_video_render_claimed,
        exposed_playback_edit_items=exposed_playback_edit_items,
        dormant_beauty_effect_requested=dormant_beauty_effect_requested,
        dormant_trimming_requested=dormant_trimming_requested,
        playback_media_slot=playback_media_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        playback_photo_capture_requested=playback_photo_capture_requested,
        playback_rotate_requested=playback_rotate_requested,
    )
    gd, tier0_errors = evaluate_p302_check_group_d_physical_bench_and_tier0(
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
            "Keep [Shading Comp.] Auto/Off (block dormant Auto: Low 0x6c9c), gate built-in front AF illuminator LED to Still AF-S (zero on FX6), preserve 5 Initialize-only AF preferences, and block Folder/Rating writes on Slot 1 Tier-0 Vault."
        )
    if not gb.passed:
        remediations.append(
            "Enforce Still AF-C [Switch V/H AF Area], 14-item [Focus Area Limit] (>=2 min), 5-mode [Exposure Std. Adjust] 1/6 EV, NDF/PAL TC rules, and fail-closed reverse-direction firewall blocking Playback [Copy] Slot 2 -> Slot 1 onto Tier-0 Vault."
        )
    if not gc.passed:
        remediations.append(
            "Restrict [Touch Func. in Shooting] to 3 modes & Sensitivity to Standard/Sensitive, block Zero-EVF blackout finder/Graphic Display keys on EVF-less FX3, gate AEL/External Flash to Still, and enforce 1..9 Interval Play Speed + dormant Edit trap rejection."
        )
    if not gd.passed or not gd.tier0_receipt_verified:
        remediations.append(
            "Verify 16/16 H0==H3 baseline invariance, keep all hardware attach / eMMC write / cross-model flash locks OFF, and supply dual-device 528B FX3RCPT1 Tier-0 receipts."
        )

    if not all_4_passed:
        verdict = P302_GO_NO_GO_BLOCKED_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_FAILURE
        overall_status = verdict
    elif not gd.tier0_receipt_verified:
        if not gd.tier0_receipt_present:
            verdict = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            overall_status = P302_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        else:
            verdict = P302_GO_NO_GO_BLOCKED_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_FAILURE
            overall_status = verdict
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED
        overall_status = P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED

    provisional = RealHwLensCompAfIlluminatorCopySlotEvfAbsenceReport(
        schema=PHASE_302_SCHEMA,
        phase_version=PHASE_302_VERSION,
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
        builtin_evf_present=False,
        fx6_builtin_af_illuminator_present=False,
        slot1_tier0_vault_mutated=False,
        usb_packets_transmitted=PHASE302_USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHASE302_USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=PHASE302_RAW_FIRMWARE_BYTES_LEAKED,
        passive_tx_bytes_emitted=gd.passive_tx_bytes_emitted,
        check_group_count=4,
        check_groups_passed=groups_passed,
        all_4_check_groups_passed=all_4_passed,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_lens_comp_af_illum_folder_rating=ga,
        check_group_b_switch_vh_limit14_std_adj_tc_copy=gb,
        check_group_c_touch_disp_evf_absence_ael_interval=gc,
        check_group_d_physical_bench_and_tier0=gd,
        warnings=gd.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwLensCompAfIlluminatorCopySlotEvfAbsenceReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_lens_comp_af_illum_folder_rating": ga,
            "check_group_b_switch_vh_limit14_std_adj_tc_copy": gb,
            "check_group_c_touch_disp_evf_absence_ael_interval": gc,
            "check_group_d_physical_bench_and_tier0": gd,
            "warnings": gd.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_lens_comp_af_illuminator_copy_slot_and_evf_absence_preflight = (
    evaluate_realhw_lens_comp_af_illuminator_copy_slot_and_evf_absence_readiness
)


def verify_phase302_report(payload: Mapping[str, Any]) -> Phase302ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 302 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_302_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_302_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_302_VALID_GO_NO_GO_VALUES:
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
        "builtin_evf_present",
        "fx6_builtin_af_illuminator_present",
        "slot1_tier0_vault_mutated",
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
        payload.get("overall_status") != P302_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    ):
        errors.append(
            "Offline awaiting-receipt verdict must carry overall_status=READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
        )

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go") == P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == P302_GO_NO_GO_LENS_COMP_AF_ILLUMINATOR_COPY_SLOT_EVF_ABSENCE_VERIFIED and (
        payload.get("all_4_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 4 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase302ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase302_markdown(
    report: RealHwLensCompAfIlluminatorCopySlotEvfAbsenceReport,
) -> str:
    """Render concise deterministic Markdown summary for Phase 302 11th physical bench preflight."""
    ga = report.check_group_a_lens_comp_af_illum_folder_rating
    gb = report.check_group_b_switch_vh_limit14_std_adj_tc_copy
    gc = report.check_group_c_touch_disp_evf_absence_ael_interval
    gd = report.check_group_d_physical_bench_and_tier0
    lines = [
        f"# Phase 302 11th Physical Bench Readiness (`{report.schema}`)",
        "",
        f"- **OVERALL**: `{report.overall_status}` (`go_no_go={report.go_no_go}`, mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `ready_attach={report.overall_ready_for_hardware_attach}`, `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `cross_model_flash={report.cross_model_flash_authorized}`, `builtin_evf={report.builtin_evf_present}`, `fx6_af_illum={report.fx6_builtin_af_illuminator_present}`, `slot1_mutated={report.slot1_tier0_vault_mutated}`, `usb_pkts={report.usb_packets_transmitted}`, `passive_tx={report.passive_tx_bytes_emitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | Shading=`{ga.shading_comp}` (AutoLowRejected=`{ga.dormant_auto_low_rejected}`), FX3_AF_LED=`{ga.fx3_builtin_af_illuminator_present}` vs FX6=`{ga.fx6_builtin_af_illuminator_present}`, 5AFResetSafe=`{ga.five_af_params_survive_camera_reset}`, Slot1FolderRatingGuard=`{ga.slot1_folder_rating_firewall_enforced}` |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | SwitchVH=`{gb.switch_vh_af_area}`, FALimit=`{gb.focus_area_limit_selected_count}/{gb.focus_area_limit_item_count}`, ExpStd5Modes=`{gb.exposure_std_metering_mode_count}` (`{gb.exposure_std_adjust_ev:+.2f}EV`), TC=`{gb.tc_format}` ({gb.video_system}), CopyDst=`Slot {gb.copy_destination_slot}` (ReverseSlot1Guard=`{gb.copy_reverse_slot1_firewall_enforced}`) |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | Touch=`{gc.touch_func_in_shooting}` (`{gc.touch_sensitivity}`, DormantRejected=`{gc.dormant_touch_traps_rejected}`), DISP=`{gc.exposed_disp_shoot_mode_count}`v`{gc.exposed_disp_playback_mode_count}`, ZeroEVFFirewall=`{gc.zero_evf_blackout_firewall_enforced}`, AEL=`{gc.ael_with_shutter}`, IntervalSpd=`{gc.interval_play_speed}` |",
        f"| `{gd.check_group_id}` | `{'PASS' if gd.passed else 'FAIL'}` | H0==H3=`{gd.h0_equals_h3_count}/{gd.h0_h3_surface_count}`, Tier0=`{gd.tier0_receipt_verified}`, DistinctMedia=`{gd.distinct_physical_media_verified}`, AttachAuth=`{gd.overall_ready_for_hardware_attach}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
