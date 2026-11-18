"""Phase 307 — 12th Real-Hardware Physical Bench Readiness Verifier (`preflight-dial-customize-lut-embed-steadyshot-and-streaming`).

Dedicated host-side read-only 12th physical bench & pre-shoot readiness verifier for Sony
`ILME-FX3` (`Ver. 7.02`, `ilc/2210`, Model `0x91030080`) vs `ILME-FX6` (`Ver. 6.01`),
extending the 12-stage operator bench preflight series (`preflight-card-insert` ->
`preflight-bench-cable-fan-slot1` -> `preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp` ->
`preflight-imagedb-touch-shoeaudio-and-lockop` ->
`preflight-diffset-customkey-autoslow-and-apsc` ->
`preflight-file-settings-gamma-assist-focus-mag-and-videolight` ->
`preflight-usb-mode-hdmi-info-protect-and-network-reset` ->
`preflight-pp-scinetone-wb-metering-and-shutter-type` ->
`preflight-focus-area-zoom-dci4k-and-sensor-cleaning` ->
`preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence` ->
`preflight-dial-customize-lut-embed-steadyshot-and-streaming`) by synthesizing Waves 56-57
official Sony `ILME-FX3` Help Guide (`ilc/2210`), `appFw.so`, `BK4`, and `.uxc` hardware
boundaries into 4 deterministic fail-closed check groups (`A..D`), bounded `O_RDONLY`
donor inspection (`< 0.15s`), `16/16 H0 == H3` baseline invariance, and dual-media
`528 B FX3RCPT1` Tier-0 receipt gating:

1. **Check Group A (`GROUP_A_DIAL_CUSTOMIZE_3DIAL_MYDIAL_FN12X2_LIVEVIEW_GRID_AND_EMBED_LUT` — Wave 56)**:
   - `[Dial Customize]` exposes the exact 5 Initialize-only items (`Custom Key/Dial Set.`
     replacing Ver. 1.xx `Dial Setup`, `My Dial Settings`, `Av/Tv Rotate`,
     `Function Ring(Lens)` restricted to `Power Focus` / `APS-C/S35/FF`, and
     `Lock Operation Parts` replacing Ver. 1.xx `Dial / Wheel Lock`).
   - `ILME-FX3` has ONLY **3 physical dials** (`Front Dial`, single `Rear Dial`,
     `Control Wheel`) — rejects dormant 4-dial Alpha `Rear Dial L` (`_f.uxc 0x6a5c`) and
     `Rear Dial R` (`_f.uxc 0x680d`) phantom bench bindings (`EOPNOTSUPP=95`), plus FX6
     dial/HOLD confusion. `My Dial 1..3` shared NVRAM banks temporarily override
     `[Lock Operation Parts]` while recalled, and `[Fn Menu Settings]` strictly splits
     `12 Still + 12 Movie` slots (rejecting all-12 `Not set` state `0x6220`).
   - `[Live View Display Set.]` exposes all 3 sub-items (`Live View Display` forced to
     `Setting Effect OFF` during `[Bright Monitoring]`, `Exposure Effect`, and resettable
     `Frame Rate Low Limit`) + `[Grid Line]` isolated from clean HDMI (zero FX6 custom PNG).
   - `[Manage User LUTs]` (`User1..16` `.cube` `<=63` chars, 17/33-pt) read-only import from
     SD `/Private/Sony/PRO/LUT` or CFexpress `/Sony/PRO/LUT` (`O_RDONLY`,
     `slot1_data_sector_writes == 0`) vs `[Embed LUT File]` (`0x680f` under
     `Log Shooting Setting`, locked `Off` on SD/SDHC `_g.uxc 0x61a0`, container metadata
     without pixel baking) vs `PPLUT1..4` (irreversible pixel baking, cleared on
     `Camera Settings Reset`/`Initialize`) + fail-closed `EROFS=30` on Slot-1 Tier-0 Vault.

2. **Check Group B (`GROUP_B_STEADYSHOT_4LOCK_ACTIVE_47FOCAL_DORMANT_SELFTIMER_AND_ZEBRA_CUSTOM` — Wave 57 §§1-3)**:
   - FX3 Movie `[SteadyShot]` (`Active` / `Standard` / `Off`) locks out `[Active]` in all
     4 conditions (`>= 119.88p/100p`, `S&Q >= 120/100fps`, `HDMI RAW Output = On`,
     `De-Squeeze Display 1.3x..2.0x`) and rejects dormant `[Dynamic active]`
     (`_f.uxc 0x741c`, `EOPNOTSUPP=95`). Exact 47-entry `[Focal Length]` table (`8mm..1000mm`),
     contrasted with IBIS-less `FX6` (`TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED`).
   - Dormant Movie `[Self-timer]` (`_f.uxc 0x7192` `Rec Start delay`) rejected fail-closed
     (`EOPNOTSUPP=95`) vs active Still `[Drive Mode]` `Self-timer(Single/Cont)` + front LED
     `#8` & Initialize-only `[Audio signals]` (suppressed under `Silent Mode=On`, dormant volume
     slider rejected) vs FX6 `Picture Cache Rec` & `Interval Rec`.
   - `[Zebra Level]` (`70..100+` + switchable `Custom1` `Std+Range` `0..109% +- 1..10%` &
     `Custom2` `Lower Limit` `0..109+`) and 4-color `Peaking` (`Red`/`Yellow`/`Blue`/`White`)
     isolated from clean HDMI, vs FX6 3-way `Off/Zebra1/Zebra2` selector & `B&W` peaking.

3. **Check Group C (`GROUP_C_NETWORK_STREAMING_FTP_ZERO_RF_AIRPLANE_AND_SLOT1_VAULT_FIREWALL` — Wave 57 §4)**:
   - `[Network Streaming]` (`RTMP`/`RTMPS`/`SRT`, fps strictly `59.94p/50p/29.97p/25p` —
     **NO `23.98p / 24.00p`**!) & `[Movie Rec During Streaming]` (`4K`/`S&Q` limits) vs FX6
     built-in streaming absence, plus `[FTP Transfer Func.]` (Passive Mode only, `(Network)`
     3-way reset boundary).
   - **CRITICAL BENCH FIREWALL**: Wireless TX for `[Network Streaming]` & `[FTP Transfer Func.]`
     blocked fail-closed by mandatory `[Airplane Mode] = On` (`0 RF packets`, `P12/P13` NVS
     untouched) AND `[Movie Rec During Streaming] = Enable` (or FTP write) targeting `Slot 1`
     blocked fail-closed (`EROFS=30` / `EBUSY=16`) on Slot-1 Tier-0 recovery vaults!

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
- `fx3_four_dial_rear_lr_present = False`
- `fx3_movie_selftimer_present = False`
- `fx6_builtin_ibis_present = False`
- `slot1_tier0_vault_mutated = False`
- `rf_nvs_p12_p13_writes_authorized = False`
- `wireless_rf_packets_emitted = 0`
- `slot1_data_sector_writes = 0`
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
# Schema, Verdicts & Non-Shadowing P307_* Domain Constants
# ---------------------------------------------------------------------------

PHASE_307_SCHEMA: str = "realhw_dial_customize_lut_embed_steadyshot_and_streaming_verifier_v1"
P307_SCHEMA: str = PHASE_307_SCHEMA
REALHW_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_SCHEMA: str = PHASE_307_SCHEMA
PHASE_307_VERSION: str = "307.0.0"
P307_VERSION: str = PHASE_307_VERSION
P307_SONY_HELP_GUIDE_ID: str = "ilc/2210"

P307_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS: str = (
    "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
)
P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED: str = (
    "GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_READONLY_PREFLIGHT_VERIFIED"
)
P307_GO_NO_GO_BLOCKED_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_FAILURE: str = (
    "BLOCKED_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_CHECK_FAILURE"
)
PHASE_307_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    P307_GO_NO_GO_BLOCKED_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED,
)

P307_CHECK_GROUP_A_ID: str = (
    "GROUP_A_DIAL_CUSTOMIZE_3DIAL_MYDIAL_FN12X2_LIVEVIEW_GRID_AND_EMBED_LUT"
)
P307_CHECK_GROUP_B_ID: str = (
    "GROUP_B_STEADYSHOT_4LOCK_ACTIVE_47FOCAL_DORMANT_SELFTIMER_AND_ZEBRA_CUSTOM"
)
P307_CHECK_GROUP_C_ID: str = (
    "GROUP_C_NETWORK_STREAMING_FTP_ZERO_RF_AIRPLANE_AND_SLOT1_VAULT_FIREWALL"
)
P307_CHECK_GROUP_D_ID: str = (
    "GROUP_D_PHYSICAL_BENCH_READINESS_TIER0_16H0H3_AND_FAIL_CLOSED_REDLINES"
)
PHASE_307_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P307_CHECK_GROUP_A_ID,
    P307_CHECK_GROUP_B_ID,
    P307_CHECK_GROUP_C_ID,
    P307_CHECK_GROUP_D_ID,
)

PHASE307_RAW_FIRMWARE_BYTES_LEAKED: int = 0
PHASE307_PASSIVE_TX_BYTES_EMITTED: int = 0
PHASE307_USB_PACKETS_TRANSMITTED: int = 0
PHASE307_WIRELESS_RF_PACKETS_EMITTED: int = 0
PHASE307_SLOT1_DATA_SECTOR_WRITES: int = 0

P307_ERRNO_EBUSY: int = 16
P307_ERRNO_EROFS: int = 30
P307_ERRNO_EOPNOTSUPP: int = 95

P307_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P307_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P307_VALID_ON_OFF: Tuple[str, ...] = ("ON", "OFF")

# Check Group A Constants (Wave 56)
P307_DIAL_CUSTOMIZE_FIVE_ITEMS: Tuple[str, ...] = (
    "CUSTOM_KEY_DIAL_SET",
    "MY_DIAL_SETTINGS",
    "AV_TV_ROTATE",
    "FUNCTION_RING_LENS",
    "LOCK_OPERATION_PARTS",
)
P307_DIAL_CUSTOMIZE_LEGACY_SYMBOLS: Tuple[str, ...] = (
    "DIAL_SETUP",
    "DIAL_WHEEL_SETUP",
    "DIAL_WHEEL_LOCK",
    "DIALCUSTOMIZE_DIAL_SETUP_LEFT_SHUTTER_RIGHT_F_NO",
)
P307_FX3_THREE_PHYSICAL_DIALS: Tuple[str, ...] = (
    "FRONT_DIAL",
    "REAR_DIAL",
    "CONTROL_WHEEL",
)
P307_DORMANT_REAR_DIAL_LR_RESIDS: Tuple[str, ...] = ("0x6a5c", "0x680d")
P307_VALID_AV_TV_ROTATE_MODES: Tuple[str, ...] = ("NORMAL", "REVERSE")
P307_VALID_FUNCTION_RING_LENS_MODES: Tuple[str, ...] = (
    "POWER_FOCUS",
    "APSC_S35_FF",
)
P307_VALID_LOCK_OPERATION_PARTS_MODES: Tuple[str, ...] = (
    "OFF",
    "MULTI_SELECTOR_ONLY",
    "DIAL_PLUS_WHEEL",
    "ALL",
)
P307_MY_DIAL_SLOTS: Tuple[int, ...] = (1, 2, 3)
P307_FN_MENU_STILL_SLOTS: int = 12
P307_FN_MENU_MOVIE_SLOTS: int = 12

P307_LIVE_VIEW_DISPLAY_SUBITEMS: Tuple[str, ...] = (
    "LIVE_VIEW_DISPLAY",
    "EXPOSURE_EFFECT",
    "FRAME_RATE_LOW_LIMIT",
)
P307_VALID_LIVE_VIEW_DISPLAY_MODES: Tuple[str, ...] = (
    "SETTING_EFFECT_ON",
    "SETTING_EFFECT_OFF",
)
P307_VALID_EXPOSURE_EFFECT_MODES: Tuple[str, ...] = (
    "EXPOSURE_SET_AND_FLASH",
    "EXPOSURE_SETTING_ONLY",
)
P307_GRID_LINE_THREE_TYPES: Tuple[str, ...] = (
    "RULE_OF_3RDS",
    "SQUARE",
    "DIAG_AND_SQUARE",
)

P307_USER_LUT_SLOT_MIN: int = 1
P307_USER_LUT_SLOT_MAX: int = 16
P307_USER_LUT_MAX_FILENAME_CHARS: int = 63
P307_USER_LUT_CUBE_SIZES: Tuple[int, ...] = (17, 33)
P307_USER_LUT_SD_DIR: str = "/Private/Sony/PRO/LUT"
P307_USER_LUT_CFEXPRESS_DIR: str = "/Sony/PRO/LUT"
P307_VALID_MEDIA_TYPES: Tuple[str, ...] = ("CFEXPRESS_A", "SDXC", "SDHC", "NONE")
P307_EMBED_LUT_RESID16_HEX: str = "0x680f"
P307_EMBED_LUT_SDHC_LOCK_RESID16_HEX: str = "0x61a0"
P307_PPLUT_PROFILES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P307_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "FLEXIBLE_ISO",
    "CINE_EI_QUICK",
    "CINE_EI",
)
P307_VALID_HDMI_INFO_DISPLAY_MODES: Tuple[str, ...] = ("ON", "OFF")
P307_VALID_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("ON", "OFF_HDMI_ONLY")

# Check Group B Constants (Wave 57 §§1-3)
P307_VALID_MOVIE_STEADYSHOT_MODES: Tuple[str, ...] = ("OFF", "STANDARD", "ACTIVE")
P307_DORMANT_DYNAMIC_ACTIVE_RESID16_HEX: str = "0x741c"
P307_VALID_STEADYSHOT_ADJUST_MODES: Tuple[str, ...] = ("AUTO", "MANUAL")
P307_VALID_DESQUEEZE_MODES: Tuple[str, ...] = (
    "OFF",
    "1.3x",
    "1.5x",
    "1.6x",
    "1.8x",
    "2.0x",
)
P307_STEADYSHOT_47_FOCAL_LENGTHS_MM: Tuple[int, ...] = (
    8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 24, 25, 28,
    30, 32, 35, 40, 45, 50, 55, 60, 70, 75, 80, 85, 90, 100, 105, 120,
    135, 150, 180, 200, 210, 250, 300, 350, 400, 450, 500, 600, 800, 1000,
)
P307_ACTIVE_LOCKOUT_MIN_FPS: float = 100.0
P307_FX6_IBIS_UNSUPPORTED_ENUM: str = "TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED"

P307_DORMANT_MOVIE_SELFTIMER_RESID16_HEX: str = "0x7192"
P307_VALID_STILL_DRIVE_MODES: Tuple[str, ...] = (
    "SINGLE_SHOOTING",
    "CONT_HI_PLUS",
    "CONT_HI",
    "CONT_MID",
    "CONT_LO",
    "SELF_TIMER_SINGLE",
    "SELF_TIMER_CONT",
    "BRACKET",
)
P307_VALID_AUDIO_SIGNAL_MODES: Tuple[str, ...] = ("ON", "OFF_SHUTTER_ONLY", "OFF")

P307_ZEBRA_FIXED_PRESETS: Tuple[str, ...] = (
    "70",
    "75",
    "80",
    "85",
    "90",
    "95",
    "100",
    "100+",
)
P307_ZEBRA_CUSTOM_SLOTS: Tuple[str, ...] = ("CUSTOM_1", "CUSTOM_2")
P307_ZEBRA_CUSTOM_TYPES: Tuple[str, ...] = ("STD_RANGE", "LOWER_LIMIT")
P307_ZEBRA_LEVEL_MIN: int = 0
P307_ZEBRA_LEVEL_MAX: int = 109
P307_ZEBRA_RANGE_MIN: int = 1
P307_ZEBRA_RANGE_MAX: int = 10
P307_PEAKING_THREE_LEVELS: Tuple[str, ...] = ("HIGH", "MID", "LOW")
P307_PEAKING_FOUR_COLORS: Tuple[str, ...] = ("RED", "YELLOW", "BLUE", "WHITE")

# Check Group C Constants (Wave 57 §4)
P307_STREAMING_RESID16_HEX: str = "0x6cb2"
P307_MOVIE_REC_DURING_STREAMING_RESID16_HEX: str = "0x79d5"
P307_FTP_TRANSFER_FUNC_RESID16_HEX: str = "0x6317"
P307_VALID_STREAMING_PROTOCOLS: Tuple[str, ...] = ("DISABLED", "RTMP", "RTMPS", "SRT")
P307_VALID_STREAMING_RESOLUTIONS: Tuple[str, ...] = (
    "4K_2160P",
    "2K_1440P",
    "HD_1080P",
    "HD_720P",
)
P307_VALID_STREAMING_FPS: Tuple[float, ...] = (25.0, 29.97, 50.0, 59.94)
P307_FORBIDDEN_STREAMING_FPS: Tuple[float, ...] = (23.98, 24.0)
P307_VALID_MOVIE_REC_DURING_STREAMING: Tuple[str, ...] = ("DISABLE", "ENABLE")
P307_VALID_NETWORK_TRANSPORTS: Tuple[str, ...] = ("NONE", "USB_LAN_CDC_NCM", "WIRELESS_RF")

# Deterministic Error Codes
P307_GA_ERR_MODEL_OR_FW_FLOOR: str = "P307_GA_ERR_MODEL_OR_FW_FLOOR"
P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP: str = (
    "P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP_EOPNOTSUPP_95"
)
P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12: str = (
    "P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12_EOPNOTSUPP_95"
)
P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID: str = (
    "P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID"
)
P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT: str = (
    "P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT_EROFS_30"
)

P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL: str = (
    "P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL_EOPNOTSUPP_95"
)
P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE: str = (
    "P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE_EOPNOTSUPP_95"
)
P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI: str = (
    "P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI"
)

P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF: str = (
    "P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF"
)
P307_GC_ERR_FTP_PASSIVE_ONLY_OR_NETWORK_3WAY_RESET: str = (
    "P307_GC_ERR_FTP_PASSIVE_ONLY_OR_NETWORK_3WAY_RESET"
)
P307_GC_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL: str = (
    "P307_GC_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL_EROFS_30"
)
P307_GC_ERR_STREAMING_OR_FTP_SLOT1_VAULT_FIREWALL: str = (
    "P307_GC_ERR_STREAMING_OR_FTP_SLOT1_VAULT_FIREWALL_EROFS_30"
)

P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P307_GD_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "P307_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P307_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION: str = (
    "P307_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"
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


def _approx_in(val: float, candidates: Sequence[float], tol: float = 0.05) -> bool:
    return any(abs(float(val) - c) <= tol for c in candidates)


# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase307DonorInspectionResult:
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
class P307CheckGroupADialCustomizeLiveViewGridLutResult:
    check_group_id: str
    passed: bool
    sony_help_guide_id: str
    dial_customize_item_count: int
    fx3_physical_dial_count: int
    fx3_four_dial_rear_lr_present: bool
    dormant_dial_symbols_rejected: bool
    my_dial_slot: int
    my_dial_lock_override_verified: bool
    fn_menu_still_slots: int
    fn_menu_movie_slots: int
    live_view_display: str
    bright_monitoring_active: bool
    grid_line_display: str
    grid_line_type: str
    grid_clean_hdmi_isolated: bool
    user_lut_slot: int
    user_lut_readonly_import_safe: bool
    embed_lut_file: str
    embed_lut_media_type: str
    picture_profile: str
    slot1_lut_vault_firewall_enforced: bool
    slot1_data_sector_writes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P307CheckGroupBSteadyShotSelfTimerZebraPeakingResult:
    check_group_id: str
    passed: bool
    steadyshot_mode: str
    steadyshot_adjust: str
    steadyshot_focal_mm: int
    focal_length_table_count: int
    dormant_dynamic_active_rejected: bool
    steadyshot_active_4lock_enforced: bool
    fx3_builtin_5axis_ibis_present: bool
    fx6_builtin_ibis_present: bool
    fx3_movie_selftimer_present: bool
    dormant_movie_selftimer_rejected: bool
    still_drive_mode: str
    audio_signals: str
    zebra_display: str
    zebra_level_spec: str
    zebra_custom_type: str
    peaking_display: str
    peaking_color: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P307CheckGroupCStreamingFtpZeroRfSlot1FirewallResult:
    check_group_id: str
    passed: bool
    streaming_protocol: str
    streaming_resolution: str
    streaming_fps: float
    movie_rec_during_streaming: str
    movie_rec_during_streaming_slot: int
    ftp_transfer_func: str
    airplane_mode: str
    network_transport: str
    wireless_rf_packets_emitted: int
    rf_nvs_p12_p13_writes_authorized: bool
    zero_rf_airplane_firewall_enforced: bool
    slot1_streaming_ftp_firewall_enforced: bool
    slot1_data_sector_writes: int
    slot1_avf_info_mutated: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P307CheckGroupDPhysicalBenchAndTier0Result:
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
class Phase307ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwDialCustomizeLutEmbedSteadyshotStreamingReport:
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
    fx3_four_dial_rear_lr_present: bool
    fx3_movie_selftimer_present: bool
    fx6_builtin_ibis_present: bool
    slot1_tier0_vault_mutated: bool
    rf_nvs_p12_p13_writes_authorized: bool
    wireless_rf_packets_emitted: int
    slot1_data_sector_writes: int
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
    donor_inspection: Phase307DonorInspectionResult
    check_group_a_dial_customize_liveview_grid_lut: (
        P307CheckGroupADialCustomizeLiveViewGridLutResult
    )
    check_group_b_steadyshot_selftimer_zebra_peaking: (
        P307CheckGroupBSteadyShotSelfTimerZebraPeakingResult
    )
    check_group_c_streaming_ftp_zero_rf_slot1_firewall: (
        P307CheckGroupCStreamingFtpZeroRfSlot1FirewallResult
    )
    check_group_d_physical_bench_and_tier0: P307CheckGroupDPhysicalBenchAndTier0Result
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


def inspect_phase307_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
) -> Phase307DonorInspectionResult:
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
        return Phase307DonorInspectionResult(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            passed=False,
            elapsed_seconds=round(dt, 6),
            within_150ms_budget=(dt < DONOR_INSPECTION_MAX_SECONDS),
            raw_firmware_bytes_leaked=PHASE307_RAW_FIRMWARE_BYTES_LEAKED,
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
        return Phase307DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            passed=True,
            elapsed_seconds=round(dt, 6),
            within_150ms_budget=(dt < DONOR_INSPECTION_MAX_SECONDS),
            raw_firmware_bytes_leaked=PHASE307_RAW_FIRMWARE_BYTES_LEAKED,
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

    return Phase307DonorInspectionResult(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        passed=(len(errors) == 0),
        elapsed_seconds=round(dt, 6),
        within_150ms_budget=within_budget,
        raw_firmware_bytes_leaked=PHASE307_RAW_FIRMWARE_BYTES_LEAKED,
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
# Check Group A (Wave 56 — Dial Customize, 3-Dial Truth, My Dial, Fn 12+12,
#                Live View Display 3-Item, Grid Line & Embed LUT vs PPLUT1..4)
# ---------------------------------------------------------------------------


def evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P307_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Wave 56.1 Dial Customize 5-Item Topology & Legacy Rejections
    exposed_dial_customize_items: Sequence[str] = P307_DIAL_CUSTOMIZE_FIVE_ITEMS,
    dormant_dial_setup_or_wheel_lock_requested: bool = False,
    av_tv_rotate: str = "NORMAL",
    function_ring_lens: str = "POWER_FOCUS",
    lock_operation_parts: str = "OFF",
    claimed_dial_customize_wiped_by_camera_reset: bool = False,
    fx6_dial_topology_claimed: bool = False,
    # Wave 56.2 3-Dial Truth, My Dial 1..3 & Fn Menu 12+12
    exposed_physical_dials: Sequence[str] = P307_FX3_THREE_PHYSICAL_DIALS,
    fx3_four_dial_rear_lr_present: bool = False,
    dormant_rear_dial_lr_requested: bool = False,
    my_dial_slot: int = 1,
    my_dial_active_recalled: bool = False,
    expect_lock_blocks_recalled_my_dial: bool = False,
    fn_menu_still_slots: int = P307_FN_MENU_STILL_SLOTS,
    fn_menu_movie_slots: int = P307_FN_MENU_MOVIE_SLOTS,
    fn_menu_all_not_set_claimed: bool = False,
    # Wave 56.3 Live View Display Set. (3-Item) & Grid Line Clean HDMI
    exposed_live_view_subitems: Sequence[str] = P307_LIVE_VIEW_DISPLAY_SUBITEMS,
    live_view_display: str = "SETTING_EFFECT_ON",
    exposure_effect: str = "EXPOSURE_SET_AND_FLASH",
    frame_rate_low_limit: str = "OFF",
    bright_monitoring_active: bool = False,
    expect_setting_effect_on_during_bright_monitoring: bool = False,
    claimed_live_view_two_items_wiped_by_camera_reset: bool = False,
    grid_line_display: str = "OFF",
    grid_line_type: str = "RULE_OF_3RDS",
    hdmi_info_display: str = "OFF",
    hdmi_raw_output: bool = False,
    rec_media_dur_hdmi_output: str = "ON",
    expect_grid_line_on_clean_hdmi: bool = False,
    dormant_fx6_custom_png_grid_requested: bool = False,
    # Wave 56.4 Manage User LUTs, Embed LUT File vs PPLUT1..4 & Slot-1 Vault
    user_lut_slot: int = 1,
    user_lut_import_requested: bool = False,
    user_lut_source_media_type: str = "CFEXPRESS_A",
    user_lut_source_dir: str = P307_USER_LUT_CFEXPRESS_DIR,
    user_lut_filename: str = "FX3_BENCH_S709.cube",
    user_lut_cube_size: int = 33,
    user_lut_config_writeback_to_slot1: bool = False,
    log_shooting_mode: str = "CINE_EI",
    embed_lut_file: str = "ON",
    embed_lut_media_type: str = "CFEXPRESS_A",
    claimed_embed_lut_under_color_tone: bool = False,
    expect_embed_lut_bakes_pixels: bool = False,
    picture_profile: str = "OFF",
    expect_pplut_preserves_unbaked_slog3: bool = False,
    claimed_pplut_survives_reset: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    embed_lut_or_pplut_rec_requested: bool = False,
    rec_target_slot: int = 2,
) -> P307CheckGroupADialCustomizeLiveViewGridLutResult:
    """Validate Wave 56 Dial Customize, 3-Dial Truth, My Dial, Fn 12+12, Live View/Grid & LUT Embed."""
    errors: List[str] = []

    try:
        fw_tuple = _parse_fw_tuple(body_fw)
    except ValueError as exc:
        fw_tuple = (0, 0)
        errors.append(f"{P307_GA_ERR_MODEL_OR_FW_FLOOR}: invalid body_fw={body_fw!r}: {exc}")

    if int(body_model_id) != TARGET_MODEL_ID_INT:
        errors.append(
            f"{P307_GA_ERR_MODEL_OR_FW_FLOOR}: unexpected body_model_id={hex(int(body_model_id))}"
        )
    if fw_tuple < MIN_BODY_FW_TUPLE:
        errors.append(f"{P307_GA_ERR_MODEL_OR_FW_FLOOR}: body_fw={body_fw!r} below 2.04 floor")
    if str(sony_help_guide_id).strip() != P307_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P307_GA_ERR_MODEL_OR_FW_FLOOR}: expected sony_help_guide_id={P307_SONY_HELP_GUIDE_ID!r}, got {sony_help_guide_id!r}"
        )

    norm_reset = _norm_upper(reset_action)
    if norm_reset not in P307_VALID_RESET_ACTIONS:
        errors.append(f"{P307_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action={reset_action!r}")

    norm_shoot = _norm_upper(shoot_mode)
    if norm_shoot not in P307_VALID_SHOOT_MODES:
        errors.append(f"{P307_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode={shoot_mode!r}")

    # 1. Wave 56.1 Dial Customize 5-Item Topology & Legacy Rejection
    norm_dial_items = tuple(_norm_upper(x) for x in exposed_dial_customize_items)
    dormant_dial_rejected = True
    if dormant_dial_setup_or_wheel_lock_requested or any(
        leg in norm_dial_items for leg in P307_DIAL_CUSTOMIZE_LEGACY_SYMBOLS
    ):
        dormant_dial_rejected = False
        errors.append(
            f"{P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP}: legacy Ver. 1.xx Dial Setup / "
            f"Dial/Wheel Lock (0x6a89/0x625b/0xe352) rejected fail-closed (EOPNOTSUPP={P307_ERRNO_EOPNOTSUPP})"
        )
    elif norm_dial_items != P307_DIAL_CUSTOMIZE_FIVE_ITEMS:
        errors.append(
            f"{P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP}: [Dial Customize] must expose exact 5 items "
            f"{P307_DIAL_CUSTOMIZE_FIVE_ITEMS}, got {norm_dial_items}"
        )

    norm_av_tv = _norm_upper(av_tv_rotate)
    norm_func_ring = _norm_upper(function_ring_lens)
    norm_lock_op = _norm_upper(lock_operation_parts)
    if norm_av_tv not in P307_VALID_AV_TV_ROTATE_MODES:
        errors.append(
            f"{P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP}: invalid av_tv_rotate={av_tv_rotate!r}"
        )
    if norm_func_ring not in P307_VALID_FUNCTION_RING_LENS_MODES:
        errors.append(
            f"{P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP}: [Function Ring(Lens)] supports ONLY "
            f"{P307_VALID_FUNCTION_RING_LENS_MODES}, got {function_ring_lens!r}"
        )
    if norm_lock_op not in P307_VALID_LOCK_OPERATION_PARTS_MODES:
        errors.append(
            f"{P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP}: invalid lock_operation_parts={lock_operation_parts!r}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_dial_customize_wiped_by_camera_reset:
        errors.append(
            f"{P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP}: all 5 [Dial Customize] items are Initialize-only (survive Camera Settings Reset)"
        )
    if fx6_dial_topology_claimed:
        errors.append(
            f"{P307_GA_ERR_DIAL_CUSTOMIZE_5ITEM_OR_LEGACY_TRAP}: ILME-FX6 uses Multi Function/Grip/Handle/IRIS/ND dials + physical HOLD switch, not FX3 [Dial Customize]"
        )

    # 2. Wave 56.2 3-Dial Hardware Truth, My Dial 1..3 & Fn Menu 12+12
    norm_dials = tuple(_norm_upper(x) for x in exposed_physical_dials)
    if (
        fx3_four_dial_rear_lr_present
        or dormant_rear_dial_lr_requested
        or "REAR_DIAL_L" in norm_dials
        or "REAR_DIAL_R" in norm_dials
    ):
        dormant_dial_rejected = False
        errors.append(
            f"{P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12}: ILME-FX3 has ONLY 3 physical dials "
            f"(Front Dial, single Rear Dial, Control Wheel); dormant 4-dial Alpha Rear Dial L/R "
            f"({P307_DORMANT_REAR_DIAL_LR_RESIDS}) rejected fail-closed (EOPNOTSUPP={P307_ERRNO_EOPNOTSUPP})"
        )
    elif norm_dials != P307_FX3_THREE_PHYSICAL_DIALS:
        errors.append(
            f"{P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12}: expected exact 3 physical dials "
            f"{P307_FX3_THREE_PHYSICAL_DIALS}, got {norm_dials}"
        )

    if int(my_dial_slot) not in P307_MY_DIAL_SLOTS:
        errors.append(
            f"{P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12}: my_dial_slot must be 1..3, got {my_dial_slot}"
        )
    my_dial_override_ok = True
    if expect_lock_blocks_recalled_my_dial:
        my_dial_override_ok = False
        errors.append(
            f"{P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12}: recalling My Dial 1..3 temporarily overrides/unlocks [Lock Operation Parts]"
        )
    if (
        int(fn_menu_still_slots) != P307_FN_MENU_STILL_SLOTS
        or int(fn_menu_movie_slots) != P307_FN_MENU_MOVIE_SLOTS
    ):
        errors.append(
            f"{P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12}: [Fn Menu Settings] must split exact 12 Still + 12 Movie slots, "
            f"got {fn_menu_still_slots}+{fn_menu_movie_slots}"
        )
    if fn_menu_all_not_set_claimed:
        errors.append(
            f"{P307_GA_ERR_THREE_DIAL_TRUTH_REAR_LR_OR_MYDIAL_FN12}: all 12 Fn slots set to [Not set] triggers invalid prompt (0x6220)"
        )

    # 3. Wave 56.3 Live View Display Set. (3 sub-items) & Grid Line Clean HDMI Isolation
    norm_lv_subitems = tuple(_norm_upper(x) for x in exposed_live_view_subitems)
    norm_lv_disp = _norm_upper(live_view_display)
    norm_exp_eff = _norm_upper(exposure_effect)
    norm_fr_low = _norm_upper(frame_rate_low_limit)
    if norm_lv_subitems != P307_LIVE_VIEW_DISPLAY_SUBITEMS:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: [Live View Display Set.] must expose 3 sub-items "
            f"{P307_LIVE_VIEW_DISPLAY_SUBITEMS}, got {norm_lv_subitems}"
        )
    if norm_lv_disp not in P307_VALID_LIVE_VIEW_DISPLAY_MODES:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: invalid live_view_display={live_view_display!r}"
        )
    if norm_exp_eff not in P307_VALID_EXPOSURE_EFFECT_MODES:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: invalid exposure_effect={exposure_effect!r}"
        )
    if norm_fr_low not in P307_VALID_ON_OFF:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: invalid frame_rate_low_limit={frame_rate_low_limit!r}"
        )
    if bright_monitoring_active and (
        norm_lv_disp != "SETTING_EFFECT_OFF" or expect_setting_effect_on_during_bright_monitoring
    ):
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: [Bright Monitoring] forces [Live View Display]=[Setting Effect OFF]"
        )
    if expect_setting_effect_on_during_bright_monitoring and not bright_monitoring_active:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: cannot expect Setting Effect ON during Bright Monitoring"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_live_view_two_items_wiped_by_camera_reset:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: [Live View Display] & [Exposure Effect] survive Camera Settings Reset (only Frame Rate Low Limit resets)"
        )

    norm_grid_disp = _norm_upper(grid_line_display)
    norm_grid_type = _norm_upper(grid_line_type)
    norm_hdmi_info = _norm_upper(hdmi_info_display)
    norm_rec_dur_hdmi = _norm_upper(rec_media_dur_hdmi_output)
    if norm_grid_disp not in P307_VALID_ON_OFF:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: invalid grid_line_display={grid_line_display!r}"
        )
    if norm_grid_type not in P307_GRID_LINE_THREE_TYPES:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: [Grid Line Type] must be one of {P307_GRID_LINE_THREE_TYPES}, got {grid_line_type!r}"
        )
    if norm_hdmi_info not in P307_VALID_HDMI_INFO_DISPLAY_MODES:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: invalid hdmi_info_display={hdmi_info_display!r}"
        )
    if norm_rec_dur_hdmi not in P307_VALID_REC_MEDIA_DUR_HDMI_MODES:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: invalid rec_media_dur_hdmi_output={rec_media_dur_hdmi_output!r}"
        )
    grid_clean_ok = not expect_grid_line_on_clean_hdmi
    if expect_grid_line_on_clean_hdmi:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: [Grid Line] is isolated to camera monitor and NEVER exported to clean HDMI"
        )
    if dormant_fx6_custom_png_grid_requested:
        errors.append(
            f"{P307_GA_ERR_LIVEVIEW_BRIGHT_MON_OR_CLEAN_HDMI_GRID}: FX3 rejects dormant FX6 custom PNG grid overlays (EOPNOTSUPP={P307_ERRNO_EOPNOTSUPP})"
        )

    # 4. Wave 56.4 Manage User LUTs (O_RDONLY) vs Embed LUT File (SDHC locked Off) vs PPLUT1..4 & Slot-1 Vault
    norm_lut_src_media = _norm_upper(user_lut_source_media_type)
    norm_embed_media = _norm_upper(embed_lut_media_type)
    norm_log = _norm_upper(log_shooting_mode)
    norm_embed = _norm_upper(embed_lut_file)
    norm_pp = _norm_upper(picture_profile)

    if not (P307_USER_LUT_SLOT_MIN <= int(user_lut_slot) <= P307_USER_LUT_SLOT_MAX):
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: [Manage User LUTs] slot must be User1..User16, got {user_lut_slot}"
        )
    if norm_lut_src_media not in P307_VALID_MEDIA_TYPES:
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: invalid user_lut_source_media_type={user_lut_source_media_type!r}"
        )
    if user_lut_import_requested:
        if len(str(user_lut_filename)) == 0 or len(str(user_lut_filename)) > P307_USER_LUT_MAX_FILENAME_CHARS:
            errors.append(
                f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: .cube filename must be 1..63 ASCII chars, got {len(str(user_lut_filename))}"
            )
        if not str(user_lut_filename).lower().endswith(".cube"):
            errors.append(
                f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: User LUT must use .cube extension, got {user_lut_filename!r}"
            )
        if int(user_lut_cube_size) not in P307_USER_LUT_CUBE_SIZES:
            errors.append(
                f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: .cube grid size must be 17 or 33, got {user_lut_cube_size}"
            )
        if norm_lut_src_media == "CFEXPRESS_A" and str(user_lut_source_dir) != P307_USER_LUT_CFEXPRESS_DIR:
            errors.append(
                f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: CFexpress User LUT import path must be {P307_USER_LUT_CFEXPRESS_DIR!r}, got {user_lut_source_dir!r}"
            )
        if norm_lut_src_media in ("SDXC", "SDHC") and str(user_lut_source_dir) != P307_USER_LUT_SD_DIR:
            errors.append(
                f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: SD User LUT import path must be {P307_USER_LUT_SD_DIR!r}, got {user_lut_source_dir!r}"
            )

    if norm_log not in P307_VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: invalid log_shooting_mode={log_shooting_mode!r}"
        )
    if norm_embed not in P307_VALID_ON_OFF:
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: invalid embed_lut_file={embed_lut_file!r}"
        )
    if norm_embed_media not in P307_VALID_MEDIA_TYPES:
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: invalid embed_lut_media_type={embed_lut_media_type!r}"
        )
    if norm_embed == "ON" and norm_embed_media == "SDHC":
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: [Embed LUT File] ({P307_EMBED_LUT_RESID16_HEX}) is locked OFF on SD/SDHC ({P307_EMBED_LUT_SDHC_LOCK_RESID16_HEX}); requires SDXC or CFexpress Type A"
        )
    if claimed_embed_lut_under_color_tone:
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: [Embed LUT File] resides under [Image Quality/Rec] -> [Log Shooting Setting], NOT [Color/Tone]"
        )
    if expect_embed_lut_bakes_pixels:
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: [Embed LUT File] stores container metadata alongside lossless S-Log3 pixels without baking"
        )
    if norm_pp in P307_PPLUT_PROFILES:
        if norm_shoot != "MOVIE":
            errors.append(
                f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: {norm_pp} LUT pixel-baking is Movie-only"
            )
        if expect_pplut_preserves_unbaked_slog3:
            errors.append(
                f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: {norm_pp} irreversibly bakes the 3D LUT into recorded pixels (unlike [Embed LUT File])"
            )
    if claimed_pplut_survives_reset:
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: PPLUT1..4 slots are cleared by [Camera Settings Reset] and [Initialize]"
        )

    slot1_locked = bool(slot1_contains_tier0_dump or slot1_wp_locked)
    slot1_firewall_ok = True
    if slot1_locked and (
        user_lut_config_writeback_to_slot1
        or (embed_lut_or_pplut_rec_requested and int(rec_target_slot) == 1)
    ):
        slot1_firewall_ok = False
        errors.append(
            f"{P307_GA_ERR_USER_LUT_EMBED_SDHC_PPLUT_OR_SLOT1_VAULT}: write-back or LUT/PPLUT recording to Slot 1 Tier-0 Vault blocked fail-closed (EROFS={P307_ERRNO_EROFS}/EBUSY={P307_ERRNO_EBUSY})"
        )

    return P307CheckGroupADialCustomizeLiveViewGridLutResult(
        check_group_id=P307_CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        sony_help_guide_id=str(sony_help_guide_id),
        dial_customize_item_count=len(norm_dial_items),
        fx3_physical_dial_count=len(norm_dials),
        fx3_four_dial_rear_lr_present=False,
        dormant_dial_symbols_rejected=dormant_dial_rejected,
        my_dial_slot=int(my_dial_slot),
        my_dial_lock_override_verified=my_dial_override_ok,
        fn_menu_still_slots=int(fn_menu_still_slots),
        fn_menu_movie_slots=int(fn_menu_movie_slots),
        live_view_display=norm_lv_disp,
        bright_monitoring_active=bool(bright_monitoring_active),
        grid_line_display=norm_grid_disp,
        grid_line_type=norm_grid_type,
        grid_clean_hdmi_isolated=grid_clean_ok,
        user_lut_slot=int(user_lut_slot),
        user_lut_readonly_import_safe=(not user_lut_config_writeback_to_slot1),
        embed_lut_file=norm_embed,
        embed_lut_media_type=norm_embed_media,
        picture_profile=norm_pp,
        slot1_lut_vault_firewall_enforced=slot1_firewall_ok,
        slot1_data_sector_writes=PHASE307_SLOT1_DATA_SECTOR_WRITES,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group B (Wave 57 §§1-3 — SteadyShot 4-Lock Active & 47-Entry Focal Length,
#                Dormant Movie Self-Timer vs Still LED #8 & Audio Signals,
#                Custom 1/2 Zebra & 4-Color Peaking)
# ---------------------------------------------------------------------------


def evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
    *,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Wave 57.1 SteadyShot 5-Axis IBIS 4-Lock Active Matrix & 47-Entry Focal Length
    steadyshot_mode: str = "STANDARD",
    dormant_dynamic_active_requested: bool = False,
    steadyshot_adjust: str = "AUTO",
    steadyshot_focal_mm: int = 8,
    exposed_focal_length_table: Sequence[int] = P307_STEADYSHOT_47_FOCAL_LENGTHS_MM,
    rec_fps: float = 23.98,
    sq_mode_enabled: bool = False,
    sq_fps: float = 60.0,
    hdmi_raw_output: bool = False,
    desqueeze_display: str = "OFF",
    distortion_comp: str = "OFF",
    fx3_builtin_5axis_ibis_present: bool = True,
    fx6_builtin_ibis_claimed: bool = False,
    # Wave 57.2 Dormant Movie Self-Timer vs Still Drive Self-Timer, LED #8 & Audio Signals
    dormant_movie_selftimer_requested: bool = False,
    still_drive_mode: str = "SINGLE_SHOOTING",
    front_led8_selftimer_blink_expected: bool = False,
    silent_mode: str = "OFF",
    audio_signals: str = "ON",
    dormant_audio_signal_volume_requested: bool = False,
    claimed_audio_signals_wiped_by_camera_reset: bool = False,
    fx6_picture_cache_or_interval_rec_in_fx3_claimed: bool = False,
    # Wave 57.3 Custom 1/2 Zebra & 4-Color Peaking vs FX6 Dual-Register Selector
    zebra_display: str = "OFF",
    zebra_preset: str = "70",
    zebra_custom_slot: str = "CUSTOM_1",
    zebra_custom_type: str = "STD_RANGE",
    zebra_level_ire: int = 70,
    zebra_range_plus_minus: int = 5,
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "WHITE",
    expect_zebra_or_peaking_on_clean_hdmi: bool = False,
    fx6_zebra_both_mode_claimed: bool = False,
    claimed_zebra_peaking_wiped_by_camera_reset: bool = False,
) -> P307CheckGroupBSteadyShotSelfTimerZebraPeakingResult:
    """Validate Wave 57 SteadyShot 4-Lock Matrix, Dormant Movie Self-Timer, Zebra Custom 1/2 & Peaking."""
    errors: List[str] = []

    norm_reset = _norm_upper(reset_action)
    norm_shoot = _norm_upper(shoot_mode)
    norm_ss = _norm_upper(steadyshot_mode)
    norm_ss_adj = _norm_upper(steadyshot_adjust)
    norm_desq = str(desqueeze_display).strip()
    if norm_desq.upper() == "OFF":
        norm_desq = "OFF"
    norm_dist = _norm_upper(distortion_comp)

    # 1. Wave 57.1 SteadyShot 5-Axis IBIS 4-Lock Active Matrix & 47-Entry Focal Length
    dormant_dyn_rejected = True
    if dormant_dynamic_active_requested or norm_ss == "DYNAMIC_ACTIVE":
        dormant_dyn_rejected = False
        errors.append(
            f"{P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL}: dormant Movie SteadyShot [Dynamic active] "
            f"({P307_DORMANT_DYNAMIC_ACTIVE_RESID16_HEX}) rejected fail-closed (EOPNOTSUPP={P307_ERRNO_EOPNOTSUPP})"
        )
    elif norm_ss not in P307_VALID_MOVIE_STEADYSHOT_MODES:
        errors.append(
            f"{P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL}: invalid steadyshot_mode={steadyshot_mode!r}"
        )

    if norm_ss_adj not in P307_VALID_STEADYSHOT_ADJUST_MODES:
        errors.append(
            f"{P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL}: invalid steadyshot_adjust={steadyshot_adjust!r}"
        )
    if norm_desq not in P307_VALID_DESQUEEZE_MODES:
        errors.append(
            f"{P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL}: invalid desqueeze_display={desqueeze_display!r}"
        )

    norm_table = tuple(int(v) for v in exposed_focal_length_table)
    if norm_table != P307_STEADYSHOT_47_FOCAL_LENGTHS_MM:
        errors.append(
            f"{P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL}: [SteadyShot Focal Length] table must have exact 47 entries "
            f"(8mm..1000mm), got {len(norm_table)} entries"
        )
    if int(steadyshot_focal_mm) not in P307_STEADYSHOT_47_FOCAL_LENGTHS_MM:
        errors.append(
            f"{P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL}: steadyshot_focal_mm={steadyshot_focal_mm} not in exact 47-entry FX3 table"
        )

    active_4lock_ok = True
    if norm_ss == "ACTIVE":
        if (
            float(rec_fps) >= P307_ACTIVE_LOCKOUT_MIN_FPS
            or (sq_mode_enabled and float(sq_fps) >= P307_ACTIVE_LOCKOUT_MIN_FPS)
            or hdmi_raw_output
            or norm_desq != "OFF"
        ):
            active_4lock_ok = False
            errors.append(
                f"{P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL}: Movie [SteadyShot]=[Active] is locked out under "
                ">=119.88p/100p, S&Q>=120/100fps, HDMI RAW Output=On, or De-Squeeze Display"
            )
        if norm_dist != "AUTO":
            errors.append(
                f"{P307_GB_ERR_STEADYSHOT_4LOCK_DYNAMIC_ACTIVE_OR_47FOCAL}: Movie [SteadyShot]=[Active] locks [Distortion Comp.] to AUTO"
            )

    if not fx3_builtin_5axis_ibis_present:
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: ILME-FX3 requires built-in 5-axis IBIS"
        )
    if fx6_builtin_ibis_claimed:
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: ILME-FX6 is IBIS-less ({P307_FX6_IBIS_UNSUPPORTED_ENUM}: lens OSS + 6-axis gyro metadata only)"
        )

    # 2. Wave 57.2 Dormant Movie Self-Timer vs Still Drive Mode + LED #8 & Audio Signals
    dormant_selftimer_rejected = True
    if dormant_movie_selftimer_requested:
        dormant_selftimer_rejected = False
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: dormant Movie [Self-timer] ({P307_DORMANT_MOVIE_SELFTIMER_RESID16_HEX}) "
            f"does not exist on FX3 Ver. 7.02 (EOPNOTSUPP={P307_ERRNO_EOPNOTSUPP})"
        )

    norm_drive = _norm_upper(still_drive_mode)
    if norm_drive not in P307_VALID_STILL_DRIVE_MODES:
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: invalid still_drive_mode={still_drive_mode!r}"
        )
    if front_led8_selftimer_blink_expected and (
        norm_shoot != "PHOTO" or norm_drive not in ("SELF_TIMER_SINGLE", "SELF_TIMER_CONT", "BRACKET")
    ):
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: front LED #8 Self-timer lamp blinks ONLY during active Still self-timer"
        )

    norm_silent = _norm_upper(silent_mode)
    norm_audio_sig = _norm_upper(audio_signals)
    if norm_silent not in P307_VALID_ON_OFF:
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: invalid silent_mode={silent_mode!r}"
        )
    if norm_audio_sig not in P307_VALID_AUDIO_SIGNAL_MODES:
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: invalid audio_signals={audio_signals!r}"
        )
    if norm_silent == "ON" and norm_audio_sig != "OFF":
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: [Silent Mode]=On suppresses [Audio signals] (must be OFF)"
        )
    if dormant_audio_signal_volume_requested:
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: dormant [Audio Signal Volume] slider rejected (EOPNOTSUPP={P307_ERRNO_EOPNOTSUPP})"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_audio_signals_wiped_by_camera_reset:
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: [Audio signals] survives Camera Settings Reset (Initialize-only)"
        )
    if fx6_picture_cache_or_interval_rec_in_fx3_claimed:
        errors.append(
            f"{P307_GB_ERR_FX6_IBIS_ABSENCE_OR_SELFTIMER_AUDIO_GATE}: FX6 [Picture Cache Rec]/[Interval Rec] are not FX3 Ver. 7.02 menus"
        )

    # 3. Wave 57.3 Zebra Custom 1/2 & 4-Color Peaking
    norm_zebra_disp = _norm_upper(zebra_display)
    norm_zebra_preset = _norm_upper(zebra_preset)
    norm_zebra_slot = _norm_upper(zebra_custom_slot)
    norm_zebra_type = _norm_upper(zebra_custom_type)
    norm_peak_disp = _norm_upper(peaking_display)
    norm_peak_lvl = _norm_upper(peaking_level)
    norm_peak_col = _norm_upper(peaking_color)

    if norm_zebra_disp not in P307_VALID_ON_OFF:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: invalid zebra_display={zebra_display!r}"
        )
    valid_zebra_selectors = P307_ZEBRA_FIXED_PRESETS + P307_ZEBRA_CUSTOM_SLOTS
    if norm_zebra_preset not in valid_zebra_selectors:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: invalid zebra_preset={zebra_preset!r}"
        )
    if norm_zebra_slot not in P307_ZEBRA_CUSTOM_SLOTS:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: invalid zebra_custom_slot={zebra_custom_slot!r}"
        )
    if norm_zebra_type not in P307_ZEBRA_CUSTOM_TYPES:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: invalid zebra_custom_type={zebra_custom_type!r}"
        )
    if not (P307_ZEBRA_LEVEL_MIN <= int(zebra_level_ire) <= P307_ZEBRA_LEVEL_MAX):
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: zebra_level_ire must be 0..109, got {zebra_level_ire}"
        )
    if norm_zebra_type == "STD_RANGE" and not (
        P307_ZEBRA_RANGE_MIN <= int(zebra_range_plus_minus) <= P307_ZEBRA_RANGE_MAX
    ):
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: Custom Std+Range tolerance must be +-1..10%, got {zebra_range_plus_minus}"
        )

    if norm_peak_disp not in P307_VALID_ON_OFF:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: invalid peaking_display={peaking_display!r}"
        )
    if norm_peak_lvl not in P307_PEAKING_THREE_LEVELS:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: invalid peaking_level={peaking_level!r}"
        )
    if norm_peak_col not in P307_PEAKING_FOUR_COLORS:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: [Peaking Color] on FX3 must be one of {P307_PEAKING_FOUR_COLORS} (no B&W), got {peaking_color!r}"
        )
    if expect_zebra_or_peaking_on_clean_hdmi:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: Zebra & Peaking are excluded from clean HDMI output"
        )
    if fx6_zebra_both_mode_claimed:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: FX6 Monitoring>Zebra>Setting is 3-way Off/Zebra1/Zebra2 (NO Both mode)"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_zebra_peaking_wiped_by_camera_reset:
        errors.append(
            f"{P307_GB_ERR_ZEBRA_CUSTOM12_PEAKING_4COLOR_OR_CLEAN_HDMI}: Zebra & Peaking settings survive Camera Settings Reset (Initialize-only)"
        )

    return P307CheckGroupBSteadyShotSelfTimerZebraPeakingResult(
        check_group_id=P307_CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        steadyshot_mode=norm_ss,
        steadyshot_adjust=norm_ss_adj,
        steadyshot_focal_mm=int(steadyshot_focal_mm),
        focal_length_table_count=len(norm_table),
        dormant_dynamic_active_rejected=dormant_dyn_rejected,
        steadyshot_active_4lock_enforced=active_4lock_ok,
        fx3_builtin_5axis_ibis_present=bool(fx3_builtin_5axis_ibis_present),
        fx6_builtin_ibis_present=False,
        fx3_movie_selftimer_present=False,
        dormant_movie_selftimer_rejected=dormant_selftimer_rejected,
        still_drive_mode=norm_drive,
        audio_signals=norm_audio_sig,
        zebra_display=norm_zebra_disp,
        zebra_level_spec=f"{norm_zebra_preset}({zebra_level_ire}+-{zebra_range_plus_minus})"
        if norm_zebra_preset in P307_ZEBRA_CUSTOM_SLOTS
        else norm_zebra_preset,
        zebra_custom_type=norm_zebra_type,
        peaking_display=norm_peak_disp,
        peaking_color=norm_peak_col,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group C (Wave 57 §4 — Network Streaming RTMP/RTMPS/SRT, FTP Transfer Func.,
#                Zero-RF Airplane Mode Firewall & Slot-1 Tier-0 Vault EROFS=30)
# ---------------------------------------------------------------------------


def evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
    *,
    reset_action: str = "NONE",
    # Wave 57.4A Network Streaming & Movie Rec During Streaming
    streaming_protocol: str = "DISABLED",
    streaming_resolution: str = "HD_1080P",
    streaming_fps: float = 29.97,
    movie_rec_during_streaming: str = "DISABLE",
    internal_rec_resolution_class: str = "HD",
    internal_rec_fps: float = 29.97,
    sq_mode_enabled: bool = False,
    movie_rec_during_streaming_slot: int = 2,
    fx6_builtin_rtmp_srt_claimed: bool = False,
    # Wave 57.4B FTP Transfer Func. & 3-Way Network Reset Boundary
    ftp_transfer_func: str = "OFF",
    ftp_active_mode_requested: bool = False,
    ftp_slot1_write_requested: bool = False,
    claimed_network_wiped_by_camera_reset: bool = False,
    claimed_network_survives_reset_network_set: bool = False,
    # Critical Bench Firewall: Mandatory Airplane Mode=On (0 RF) & Slot-1 Vault
    airplane_mode: str = "ON",
    network_transport: str = "NONE",
    wireless_streaming_requested: bool = False,
    wireless_ftp_requested: bool = False,
    wireless_rf_packets_emitted: int = 0,
    rf_nvs_p12_p13_writes_requested: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
) -> P307CheckGroupCStreamingFtpZeroRfSlot1FirewallResult:
    """Validate Wave 57 §4 Network Streaming, FTP Transfer Func., Zero-RF & Slot-1 Vault Firewall."""
    errors: List[str] = []

    norm_reset = _norm_upper(reset_action)
    norm_proto = _norm_upper(streaming_protocol)
    norm_s_res = _norm_upper(streaming_resolution)
    norm_rec_dur = _norm_upper(movie_rec_during_streaming)
    norm_int_res = _norm_upper(internal_rec_resolution_class)
    norm_ftp = _norm_upper(ftp_transfer_func)
    norm_airplane = _norm_upper(airplane_mode)
    norm_transport = _norm_upper(network_transport)

    if norm_proto not in P307_VALID_STREAMING_PROTOCOLS:
        errors.append(
            f"{P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF}: invalid streaming_protocol={streaming_protocol!r}"
        )
    if norm_s_res not in P307_VALID_STREAMING_RESOLUTIONS:
        errors.append(
            f"{P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF}: invalid streaming_resolution={streaming_resolution!r}"
        )
    if norm_rec_dur not in P307_VALID_MOVIE_REC_DURING_STREAMING:
        errors.append(
            f"{P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF}: invalid movie_rec_during_streaming={movie_rec_during_streaming!r}"
        )
    if norm_ftp not in P307_VALID_ON_OFF:
        errors.append(
            f"{P307_GC_ERR_FTP_PASSIVE_ONLY_OR_NETWORK_3WAY_RESET}: invalid ftp_transfer_func={ftp_transfer_func!r}"
        )
    if norm_airplane not in P307_VALID_ON_OFF:
        errors.append(
            f"{P307_GC_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL}: invalid airplane_mode={airplane_mode!r}"
        )
    if norm_transport not in P307_VALID_NETWORK_TRANSPORTS:
        errors.append(
            f"{P307_GC_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL}: invalid network_transport={network_transport!r}"
        )

    # Streaming protocol & fps rules (NO 23.98p/24p!)
    if _approx_in(streaming_fps, P307_FORBIDDEN_STREAMING_FPS) or not _approx_in(
        streaming_fps, P307_VALID_STREAMING_FPS
    ):
        errors.append(
            f"{P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF}: [Network Streaming] supports ONLY "
            f"{P307_VALID_STREAMING_FPS} fps (23.98p / 24.00p UNSUPPORTED), got {streaming_fps}"
        )

    if norm_rec_dur == "ENABLE":
        if abs(float(internal_rec_fps) - float(streaming_fps)) > 0.05:
            errors.append(
                f"{P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF}: [Movie Rec During Streaming]=Enable requires internal rec fps ({internal_rec_fps}) == streaming fps ({streaming_fps})"
            )
        if norm_int_res == "4K" and (
            norm_s_res == "4K_2160P"
            or (norm_s_res == "2K_1440P" and float(streaming_fps) >= 50.0)
        ):
            errors.append(
                f"{P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF}: 4K internal [Movie Rec During Streaming] forbidden during 4K or 2K 50p/59.94p streaming"
            )
        if sq_mode_enabled:
            errors.append(
                f"{P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF}: [Movie Rec During Streaming] disables S&Q mode"
            )

    if fx6_builtin_rtmp_srt_claimed:
        errors.append(
            f"{P307_GC_ERR_STREAMING_2398P_REC_CONFLICT_OR_FX6_SPOOF}: ILME-FX6 Ver. 6.01 lacks FX3 built-in RTMP/RTMPS/SRT streaming (dormant BKID_APP_RTMP_SETTINGS)"
        )

    # FTP Passive Mode & 3-way reset boundary
    if ftp_active_mode_requested:
        errors.append(
            f"{P307_GC_ERR_FTP_PASSIVE_ONLY_OR_NETWORK_3WAY_RESET}: FX3 [FTP Transfer Func.] supports Passive Mode ONLY"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_network_wiped_by_camera_reset:
        errors.append(
            f"{P307_GC_ERR_FTP_PASSIVE_ONLY_OR_NETWORK_3WAY_RESET}: (Network) settings survive [Camera Settings Reset]"
        )
    if norm_reset == "RESET_NETWORK_SET" and claimed_network_survives_reset_network_set:
        errors.append(
            f"{P307_GC_ERR_FTP_PASSIVE_ONLY_OR_NETWORK_3WAY_RESET}: [Reset Network Set.] clears Wi-Fi/BT/FTP/Streaming credentials"
        )

    # CRITICAL FIREWALL #1: Mandatory Airplane Mode = ON & Zero-RF packets
    zero_rf_ok = True
    if (
        norm_airplane != "ON"
        or norm_transport == "WIRELESS_RF"
        or wireless_streaming_requested
        or wireless_ftp_requested
        or int(wireless_rf_packets_emitted) != 0
        or rf_nvs_p12_p13_writes_requested
    ):
        zero_rf_ok = False
        errors.append(
            f"{P307_GC_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL}: CRITICAL ZERO-RF FIREWALL: [Airplane Mode] must remain ON, "
            "wireless streaming/FTP TX and P12/P13 RF NVS writes are blocked fail-closed (0 RF packets)"
        )

    # CRITICAL FIREWALL #2: Slot-1 Tier-0 Vault EROFS=30 / EBUSY=16 Firewall
    slot1_locked = bool(slot1_contains_tier0_dump or slot1_wp_locked)
    slot1_firewall_ok = True
    if slot1_locked and (
        (norm_rec_dur == "ENABLE" and int(movie_rec_during_streaming_slot) == 1)
        or ftp_slot1_write_requested
    ):
        slot1_firewall_ok = False
        errors.append(
            f"{P307_GC_ERR_STREAMING_OR_FTP_SLOT1_VAULT_FIREWALL}: CRITICAL SLOT-1 VAULT FIREWALL: "
            f"[Movie Rec During Streaming]=Enable / FTP write onto Slot 1 Tier-0 Vault blocked fail-closed (EROFS={P307_ERRNO_EROFS}/EBUSY={P307_ERRNO_EBUSY})"
        )

    return P307CheckGroupCStreamingFtpZeroRfSlot1FirewallResult(
        check_group_id=P307_CHECK_GROUP_C_ID,
        passed=(len(errors) == 0),
        streaming_protocol=norm_proto,
        streaming_resolution=norm_s_res,
        streaming_fps=float(streaming_fps),
        movie_rec_during_streaming=norm_rec_dur,
        movie_rec_during_streaming_slot=int(movie_rec_during_streaming_slot),
        ftp_transfer_func=norm_ftp,
        airplane_mode=norm_airplane,
        network_transport=norm_transport,
        wireless_rf_packets_emitted=PHASE307_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_p12_p13_writes_authorized=False,
        zero_rf_airplane_firewall_enforced=zero_rf_ok,
        slot1_streaming_ftp_firewall_enforced=slot1_firewall_ok,
        slot1_data_sector_writes=PHASE307_SLOT1_DATA_SECTOR_WRITES,
        slot1_avf_info_mutated=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group D (Physical Bench Readiness Receipt, 16/16 H0 == H3 & Fail-Closed Redlines)
# ---------------------------------------------------------------------------


def build_simulated_phase307_tier0_receipts(
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
            f"PHASE307_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE307_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_p307_check_group_d_physical_bench_and_tier0(
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
) -> Tuple[P307CheckGroupDPhysicalBenchAndTier0Result, Tuple[str, ...]]:
    """Validate Check Group D: physical bench readiness, 16/16 H0==H3, dual 528B FX3RCPT1 & redlines."""
    errors: List[str] = []
    tier0_errors: List[str] = []
    warnings: List[str] = []

    if simulated_passive_tx_bytes != 0:
        errors.append(
            f"{P307_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: passive_tx_bytes_emitted={simulated_passive_tx_bytes} != 0"
        )
    if (
        claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P307_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: hardware_live_attach / persistent_emmc_writes / cross_model_flash are unconditionally LOCKED OFF"
        )

    surface_count = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_count, int(simulated_h0_h3_drifted_surfaces)))
    equals_count = max(0, surface_count - drifted)
    if drifted != 0:
        errors.append(
            f"{P307_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: {drifted} surfaces drifted between H0 and H3"
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
        raw_a, raw_b, sim_h0 = build_simulated_phase307_tier0_receipts(
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
                f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
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
                f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
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
            f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    elif raw_a is None or raw_b is None:
        tier0_errors.append(
            f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B 528B FX3RCPT1 receipts are required"
        )
    else:
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media_ok = True
            else:
                tier0_errors.append(
                    f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{P307_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    group_result = P307CheckGroupDPhysicalBenchAndTier0Result(
        check_group_id=P307_CHECK_GROUP_D_ID,
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


def evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P307_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Check Group A (Wave 56)
    exposed_dial_customize_items: Sequence[str] = P307_DIAL_CUSTOMIZE_FIVE_ITEMS,
    dormant_dial_setup_or_wheel_lock_requested: bool = False,
    av_tv_rotate: str = "NORMAL",
    function_ring_lens: str = "POWER_FOCUS",
    lock_operation_parts: str = "OFF",
    claimed_dial_customize_wiped_by_camera_reset: bool = False,
    fx6_dial_topology_claimed: bool = False,
    exposed_physical_dials: Sequence[str] = P307_FX3_THREE_PHYSICAL_DIALS,
    fx3_four_dial_rear_lr_present: bool = False,
    dormant_rear_dial_lr_requested: bool = False,
    my_dial_slot: int = 1,
    my_dial_active_recalled: bool = False,
    expect_lock_blocks_recalled_my_dial: bool = False,
    fn_menu_still_slots: int = P307_FN_MENU_STILL_SLOTS,
    fn_menu_movie_slots: int = P307_FN_MENU_MOVIE_SLOTS,
    fn_menu_all_not_set_claimed: bool = False,
    exposed_live_view_subitems: Sequence[str] = P307_LIVE_VIEW_DISPLAY_SUBITEMS,
    live_view_display: str = "SETTING_EFFECT_ON",
    exposure_effect: str = "EXPOSURE_SET_AND_FLASH",
    frame_rate_low_limit: str = "OFF",
    bright_monitoring_active: bool = False,
    expect_setting_effect_on_during_bright_monitoring: bool = False,
    claimed_live_view_two_items_wiped_by_camera_reset: bool = False,
    grid_line_display: str = "OFF",
    grid_line_type: str = "RULE_OF_3RDS",
    hdmi_info_display: str = "OFF",
    hdmi_raw_output: bool = False,
    rec_media_dur_hdmi_output: str = "ON",
    expect_grid_line_on_clean_hdmi: bool = False,
    dormant_fx6_custom_png_grid_requested: bool = False,
    user_lut_slot: int = 1,
    user_lut_import_requested: bool = False,
    user_lut_source_media_type: str = "CFEXPRESS_A",
    user_lut_source_dir: str = P307_USER_LUT_CFEXPRESS_DIR,
    user_lut_filename: str = "FX3_BENCH_S709.cube",
    user_lut_cube_size: int = 33,
    user_lut_config_writeback_to_slot1: bool = False,
    log_shooting_mode: str = "CINE_EI",
    embed_lut_file: str = "ON",
    embed_lut_media_type: str = "CFEXPRESS_A",
    claimed_embed_lut_under_color_tone: bool = False,
    expect_embed_lut_bakes_pixels: bool = False,
    picture_profile: str = "OFF",
    expect_pplut_preserves_unbaked_slog3: bool = False,
    claimed_pplut_survives_reset: bool = False,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    embed_lut_or_pplut_rec_requested: bool = False,
    rec_target_slot: int = 2,
    # Check Group B (Wave 57 §§1-3)
    steadyshot_mode: str = "STANDARD",
    dormant_dynamic_active_requested: bool = False,
    steadyshot_adjust: str = "AUTO",
    steadyshot_focal_mm: int = 8,
    exposed_focal_length_table: Sequence[int] = P307_STEADYSHOT_47_FOCAL_LENGTHS_MM,
    rec_fps: float = 23.98,
    sq_mode_enabled: bool = False,
    sq_fps: float = 60.0,
    desqueeze_display: str = "OFF",
    distortion_comp: str = "OFF",
    fx3_builtin_5axis_ibis_present: bool = True,
    fx6_builtin_ibis_claimed: bool = False,
    dormant_movie_selftimer_requested: bool = False,
    still_drive_mode: str = "SINGLE_SHOOTING",
    front_led8_selftimer_blink_expected: bool = False,
    silent_mode: str = "OFF",
    audio_signals: str = "ON",
    dormant_audio_signal_volume_requested: bool = False,
    claimed_audio_signals_wiped_by_camera_reset: bool = False,
    fx6_picture_cache_or_interval_rec_in_fx3_claimed: bool = False,
    zebra_display: str = "OFF",
    zebra_preset: str = "70",
    zebra_custom_slot: str = "CUSTOM_1",
    zebra_custom_type: str = "STD_RANGE",
    zebra_level_ire: int = 70,
    zebra_range_plus_minus: int = 5,
    peaking_display: str = "OFF",
    peaking_level: str = "MID",
    peaking_color: str = "WHITE",
    expect_zebra_or_peaking_on_clean_hdmi: bool = False,
    fx6_zebra_both_mode_claimed: bool = False,
    claimed_zebra_peaking_wiped_by_camera_reset: bool = False,
    # Check Group C (Wave 57 §4)
    streaming_protocol: str = "DISABLED",
    streaming_resolution: str = "HD_1080P",
    streaming_fps: float = 29.97,
    movie_rec_during_streaming: str = "DISABLE",
    internal_rec_resolution_class: str = "HD",
    internal_rec_fps: float = 29.97,
    movie_rec_during_streaming_slot: int = 2,
    fx6_builtin_rtmp_srt_claimed: bool = False,
    ftp_transfer_func: str = "OFF",
    ftp_active_mode_requested: bool = False,
    ftp_slot1_write_requested: bool = False,
    claimed_network_wiped_by_camera_reset: bool = False,
    claimed_network_survives_reset_network_set: bool = False,
    airplane_mode: str = "ON",
    network_transport: str = "NONE",
    wireless_streaming_requested: bool = False,
    wireless_ftp_requested: bool = False,
    wireless_rf_packets_emitted: int = 0,
    rf_nvs_p12_p13_writes_requested: bool = False,
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
) -> RealHwDialCustomizeLutEmbedSteadyshotStreamingReport:
    """Execute Phase 307 12th real-hardware physical bench readiness verifier (`A..D`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase307_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_p307_check_group_a_dial_customize_liveview_grid_lut(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        exposed_dial_customize_items=exposed_dial_customize_items,
        dormant_dial_setup_or_wheel_lock_requested=dormant_dial_setup_or_wheel_lock_requested,
        av_tv_rotate=av_tv_rotate,
        function_ring_lens=function_ring_lens,
        lock_operation_parts=lock_operation_parts,
        claimed_dial_customize_wiped_by_camera_reset=claimed_dial_customize_wiped_by_camera_reset,
        fx6_dial_topology_claimed=fx6_dial_topology_claimed,
        exposed_physical_dials=exposed_physical_dials,
        fx3_four_dial_rear_lr_present=fx3_four_dial_rear_lr_present,
        dormant_rear_dial_lr_requested=dormant_rear_dial_lr_requested,
        my_dial_slot=my_dial_slot,
        my_dial_active_recalled=my_dial_active_recalled,
        expect_lock_blocks_recalled_my_dial=expect_lock_blocks_recalled_my_dial,
        fn_menu_still_slots=fn_menu_still_slots,
        fn_menu_movie_slots=fn_menu_movie_slots,
        fn_menu_all_not_set_claimed=fn_menu_all_not_set_claimed,
        exposed_live_view_subitems=exposed_live_view_subitems,
        live_view_display=live_view_display,
        exposure_effect=exposure_effect,
        frame_rate_low_limit=frame_rate_low_limit,
        bright_monitoring_active=bright_monitoring_active,
        expect_setting_effect_on_during_bright_monitoring=expect_setting_effect_on_during_bright_monitoring,
        claimed_live_view_two_items_wiped_by_camera_reset=claimed_live_view_two_items_wiped_by_camera_reset,
        grid_line_display=grid_line_display,
        grid_line_type=grid_line_type,
        hdmi_info_display=hdmi_info_display,
        hdmi_raw_output=hdmi_raw_output,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        expect_grid_line_on_clean_hdmi=expect_grid_line_on_clean_hdmi,
        dormant_fx6_custom_png_grid_requested=dormant_fx6_custom_png_grid_requested,
        user_lut_slot=user_lut_slot,
        user_lut_import_requested=user_lut_import_requested,
        user_lut_source_media_type=user_lut_source_media_type,
        user_lut_source_dir=user_lut_source_dir,
        user_lut_filename=user_lut_filename,
        user_lut_cube_size=user_lut_cube_size,
        user_lut_config_writeback_to_slot1=user_lut_config_writeback_to_slot1,
        log_shooting_mode=log_shooting_mode,
        embed_lut_file=embed_lut_file,
        embed_lut_media_type=embed_lut_media_type,
        claimed_embed_lut_under_color_tone=claimed_embed_lut_under_color_tone,
        expect_embed_lut_bakes_pixels=expect_embed_lut_bakes_pixels,
        picture_profile=picture_profile,
        expect_pplut_preserves_unbaked_slog3=expect_pplut_preserves_unbaked_slog3,
        claimed_pplut_survives_reset=claimed_pplut_survives_reset,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        embed_lut_or_pplut_rec_requested=embed_lut_or_pplut_rec_requested,
        rec_target_slot=rec_target_slot,
    )
    gb = evaluate_p307_check_group_b_steadyshot_selftimer_zebra_peaking(
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        steadyshot_mode=steadyshot_mode,
        dormant_dynamic_active_requested=dormant_dynamic_active_requested,
        steadyshot_adjust=steadyshot_adjust,
        steadyshot_focal_mm=steadyshot_focal_mm,
        exposed_focal_length_table=exposed_focal_length_table,
        rec_fps=rec_fps,
        sq_mode_enabled=sq_mode_enabled,
        sq_fps=sq_fps,
        hdmi_raw_output=hdmi_raw_output,
        desqueeze_display=desqueeze_display,
        distortion_comp=distortion_comp,
        fx3_builtin_5axis_ibis_present=fx3_builtin_5axis_ibis_present,
        fx6_builtin_ibis_claimed=fx6_builtin_ibis_claimed,
        dormant_movie_selftimer_requested=dormant_movie_selftimer_requested,
        still_drive_mode=still_drive_mode,
        front_led8_selftimer_blink_expected=front_led8_selftimer_blink_expected,
        silent_mode=silent_mode,
        audio_signals=audio_signals,
        dormant_audio_signal_volume_requested=dormant_audio_signal_volume_requested,
        claimed_audio_signals_wiped_by_camera_reset=claimed_audio_signals_wiped_by_camera_reset,
        fx6_picture_cache_or_interval_rec_in_fx3_claimed=fx6_picture_cache_or_interval_rec_in_fx3_claimed,
        zebra_display=zebra_display,
        zebra_preset=zebra_preset,
        zebra_custom_slot=zebra_custom_slot,
        zebra_custom_type=zebra_custom_type,
        zebra_level_ire=zebra_level_ire,
        zebra_range_plus_minus=zebra_range_plus_minus,
        peaking_display=peaking_display,
        peaking_level=peaking_level,
        peaking_color=peaking_color,
        expect_zebra_or_peaking_on_clean_hdmi=expect_zebra_or_peaking_on_clean_hdmi,
        fx6_zebra_both_mode_claimed=fx6_zebra_both_mode_claimed,
        claimed_zebra_peaking_wiped_by_camera_reset=claimed_zebra_peaking_wiped_by_camera_reset,
    )
    gc = evaluate_p307_check_group_c_streaming_ftp_zero_rf_slot1_firewall(
        reset_action=reset_action,
        streaming_protocol=streaming_protocol,
        streaming_resolution=streaming_resolution,
        streaming_fps=streaming_fps,
        movie_rec_during_streaming=movie_rec_during_streaming,
        internal_rec_resolution_class=internal_rec_resolution_class,
        internal_rec_fps=internal_rec_fps,
        sq_mode_enabled=sq_mode_enabled,
        movie_rec_during_streaming_slot=movie_rec_during_streaming_slot,
        fx6_builtin_rtmp_srt_claimed=fx6_builtin_rtmp_srt_claimed,
        ftp_transfer_func=ftp_transfer_func,
        ftp_active_mode_requested=ftp_active_mode_requested,
        ftp_slot1_write_requested=ftp_slot1_write_requested,
        claimed_network_wiped_by_camera_reset=claimed_network_wiped_by_camera_reset,
        claimed_network_survives_reset_network_set=claimed_network_survives_reset_network_set,
        airplane_mode=airplane_mode,
        network_transport=network_transport,
        wireless_streaming_requested=wireless_streaming_requested,
        wireless_ftp_requested=wireless_ftp_requested,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        rf_nvs_p12_p13_writes_requested=rf_nvs_p12_p13_writes_requested,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
    )
    gd, tier0_errors = evaluate_p307_check_group_d_physical_bench_and_tier0(
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
            "Enforce 5-item [Dial Customize] & 3-dial truth (reject Rear Dial L/R 0x6a5c/0x680d & Ver. 1.xx Dial Setup/Wheel Lock), My Dial lock override, 12+12 Fn split, Live View 3-item/Grid isolation, and O_RDONLY LUT import / Embed LUT SDHC lock / Slot-1 EROFS=30 firewall."
        )
    if not gb.passed:
        remediations.append(
            "Enforce SteadyShot Active 4-lockout matrix (119.88p/S&Q>=120/RAW/De-Squeeze), reject dormant Dynamic active (0x741c) & Movie Self-timer (0x7192), preserve 47-entry Focal Length & IBIS-less FX6 split, and enforce Zebra Custom 1/2 + 4-color Peaking."
        )
    if not gc.passed:
        remediations.append(
            "Keep [Airplane Mode]=On (0 RF packets, P12/P13 untouched), block 23.98p/24p in [Network Streaming] & active FTP, and enforce fail-closed EROFS=30/EBUSY=16 firewall against Slot-1 [Movie Rec During Streaming] or FTP writes."
        )
    if not gd.passed or not gd.tier0_receipt_verified:
        remediations.append(
            "Verify 16/16 H0==H3 baseline invariance, keep all hardware attach / eMMC write / cross-model flash locks OFF, and supply dual-device 528B FX3RCPT1 Tier-0 receipts."
        )

    if not all_4_passed:
        verdict = P307_GO_NO_GO_BLOCKED_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_FAILURE
        overall_status = verdict
    elif not gd.tier0_receipt_verified:
        if not gd.tier0_receipt_present:
            verdict = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            overall_status = P307_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        else:
            verdict = P307_GO_NO_GO_BLOCKED_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_FAILURE
            overall_status = verdict
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED
        overall_status = P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED

    provisional = RealHwDialCustomizeLutEmbedSteadyshotStreamingReport(
        schema=PHASE_307_SCHEMA,
        phase_version=PHASE_307_VERSION,
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
        fx3_four_dial_rear_lr_present=False,
        fx3_movie_selftimer_present=False,
        fx6_builtin_ibis_present=False,
        slot1_tier0_vault_mutated=False,
        rf_nvs_p12_p13_writes_authorized=False,
        wireless_rf_packets_emitted=PHASE307_WIRELESS_RF_PACKETS_EMITTED,
        slot1_data_sector_writes=PHASE307_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE307_USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHASE307_USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=PHASE307_RAW_FIRMWARE_BYTES_LEAKED,
        passive_tx_bytes_emitted=gd.passive_tx_bytes_emitted,
        check_group_count=4,
        check_groups_passed=groups_passed,
        all_4_check_groups_passed=all_4_passed,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_dial_customize_liveview_grid_lut=ga,
        check_group_b_steadyshot_selftimer_zebra_peaking=gb,
        check_group_c_streaming_ftp_zero_rf_slot1_firewall=gc,
        check_group_d_physical_bench_and_tier0=gd,
        warnings=gd.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwDialCustomizeLutEmbedSteadyshotStreamingReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_dial_customize_liveview_grid_lut": ga,
            "check_group_b_steadyshot_selftimer_zebra_peaking": gb,
            "check_group_c_streaming_ftp_zero_rf_slot1_firewall": gc,
            "check_group_d_physical_bench_and_tier0": gd,
            "warnings": gd.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_dial_customize_lut_embed_steadyshot_and_streaming_preflight = (
    evaluate_realhw_dial_customize_lut_embed_steadyshot_and_streaming_readiness
)


def verify_phase307_report(payload: Mapping[str, Any]) -> Phase307ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 307 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_307_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_307_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_307_VALID_GO_NO_GO_VALUES:
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
        "fx3_four_dial_rear_lr_present",
        "fx3_movie_selftimer_present",
        "fx6_builtin_ibis_present",
        "slot1_tier0_vault_mutated",
        "rf_nvs_p12_p13_writes_authorized",
    ):
        if payload.get(lock_key) is not False:
            errors.append(f"Safety lock violated: {lock_key}={payload.get(lock_key)!r}")

    for zero_key in (
        "wireless_rf_packets_emitted",
        "slot1_data_sector_writes",
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
        payload.get("overall_status") != P307_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    ):
        errors.append(
            "Offline awaiting-receipt verdict must carry overall_status=READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
        )

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go")
        == P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == P307_GO_NO_GO_DIAL_CUSTOMIZE_LUT_EMBED_STEADYSHOT_STREAMING_VERIFIED and (
        payload.get("all_4_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 4 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase307ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase307_markdown(
    report: RealHwDialCustomizeLutEmbedSteadyshotStreamingReport,
) -> str:
    """Render concise deterministic Markdown summary for Phase 307 12th physical bench preflight."""
    ga = report.check_group_a_dial_customize_liveview_grid_lut
    gb = report.check_group_b_steadyshot_selftimer_zebra_peaking
    gc = report.check_group_c_streaming_ftp_zero_rf_slot1_firewall
    gd = report.check_group_d_physical_bench_and_tier0
    lines = [
        f"# Phase 307 12th Physical Bench Readiness (`{report.schema}`)",
        "",
        f"- **OVERALL**: `{report.overall_status}` (`go_no_go={report.go_no_go}`, mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `ready_attach={report.overall_ready_for_hardware_attach}`, `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `cross_model_flash={report.cross_model_flash_authorized}`, `rear_lr={report.fx3_four_dial_rear_lr_present}`, `movie_selftimer={report.fx3_movie_selftimer_present}`, `fx6_ibis={report.fx6_builtin_ibis_present}`, `slot1_mutated={report.slot1_tier0_vault_mutated}`, `rf_pkts={report.wireless_rf_packets_emitted}`, `slot1_writes={report.slot1_data_sector_writes}`, `usb_pkts={report.usb_packets_transmitted}`, `passive_tx={report.passive_tx_bytes_emitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | DialItems=`{ga.dial_customize_item_count}`, Dials=`{ga.fx3_physical_dial_count}` (RearLR=`{ga.fx3_four_dial_rear_lr_present}`), Fn=`{ga.fn_menu_still_slots}+{ga.fn_menu_movie_slots}`, LiveView=`{ga.live_view_display}`, EmbedLUT=`{ga.embed_lut_file}` (`{ga.embed_lut_media_type}`), Slot1Guard=`{ga.slot1_lut_vault_firewall_enforced}` |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | SteadyShot=`{gb.steadyshot_mode}` (`{gb.steadyshot_focal_mm}mm` in `{gb.focal_length_table_count}`, 4Lock=`{gb.steadyshot_active_4lock_enforced}`, FX6_IBIS=`{gb.fx6_builtin_ibis_present}`), MovieSelfTimer=`{gb.fx3_movie_selftimer_present}`, Zebra=`{gb.zebra_level_spec}`, Peaking=`{gb.peaking_color}` |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | Stream=`{gc.streaming_protocol}` (`{gc.streaming_resolution}`@{gc.streaming_fps}), RecDuring=`{gc.movie_rec_during_streaming}` (Slot {gc.movie_rec_during_streaming_slot}), FTP=`{gc.ftp_transfer_func}`, Airplane=`{gc.airplane_mode}` (ZeroRF=`{gc.zero_rf_airplane_firewall_enforced}`, Slot1Guard=`{gc.slot1_streaming_ftp_firewall_enforced}`) |",
        f"| `{gd.check_group_id}` | `{'PASS' if gd.passed else 'FAIL'}` | H0==H3=`{gd.h0_equals_h3_count}/{gd.h0_h3_surface_count}`, Tier0=`{gd.tier0_receipt_verified}`, DistinctMedia=`{gd.distinct_physical_media_verified}`, AttachAuth=`{gd.overall_ready_for_hardware_attach}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
