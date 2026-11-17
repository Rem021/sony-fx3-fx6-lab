"""Phase 279 — 8th Real-Hardware Physical Bench Readiness Verifier (`preflight-usb-mode-hdmi-info-protect-and-network-reset`).

Dedicated host-side read-only 8th physical bench & pre-shoot readiness verifier for Sony
`ILME-FX3` (`Ver. 7.02`, `ilc/2210`, Model `0x91030080`) vs `ILME-FX6` (`Ver. 6.01`),
extending the operator bench preflight series (`preflight-card-insert` ->
`preflight-bench-cable-fan-slot1` -> `preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp` ->
`preflight-imagedb-touch-shoeaudio-and-lockop` ->
`preflight-diffset-customkey-autoslow-and-apsc` ->
`preflight-file-settings-gamma-assist-focus-mag-and-videolight` ->
`preflight-usb-mode-hdmi-info-protect-and-network-reset`) by synthesizing Wave 47 official
Sony `ILME-FX3` Help Guide (`ilc/2210`), `appFw.so`, `BK4`, `/usr/kmod`, and `.uxc` hardware
boundaries into 4 deterministic fail-closed check groups (`A..D`), bounded `O_RDONLY` donor
inspection (`< 0.15s`), `16/16 H0 == H3` baseline invariance, and dual-media `528 B FX3RCPT1`
Tier-0 receipt gating:

1. **Check Group A (`GROUP_A_USB_CONNECTION_MODE_NOUVC_AND_DATA_ISOLATED_USB_PD` — Wave 47 §1)**:
   - Stock `ILME-FX3 Ver. 7.02` `(Setup) -> [USB] -> [USB Connection Mode]`
     (`BKID_APP_setting_usb_connection_method`, `_f.uxc` `0x69a2`) exposes ONLY **4** modes
     (`Sel. When Connect` `0x7738` default, `MassStorage(MSC)` `0x6c54` `054C:0DA1`, `MTP`
     `0xe24b`, `Remote Shoot (PC Remote)` `0x60aa`); rejects any spoofed `[USB Streaming]`
     UVC/UAC mode on `ILME-FX3` despite dormant `usb_f_uvc.ko` (`78,840 B`) / `_f.uxc` `0x7399`
     tokens compiled in firmware (`NOUVC`).
   - Air-gapped Tier-0 bench rule: blocks `MassStorage(MSC)`, `MTP`, `Remote Shoot`, and
     `USB-LAN` host data enumeration; permits `[USB Power Supply] = [On]` (`0x721e`, Type-C +
     NP-FZ100 inserted; `[USB LUN Setting]` `Multi` default `0xe631` / `Single` `0x776d`) ONLY
     when USB `D+/D-` & SuperSpeed data lines are physically isolated; verifies `(Setup)->[USB]`
     survival across `[Camera Settings Reset]` & `[Reset Network Set.]` (reset only on
     `[Initialize]`).

2. **Check Group B (`GROUP_B_HDMI_INFO_DISPLAY_CLEAN_FEED_AND_LOG_1080_VS_4K_OVERRIDE` — Wave 47 §2)**:
   - `[HDMI Info. Display]` (`On` default `0xe07c` blanks built-in LCD & disables touch-focus
     `CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON` with letterboxed OSD; `Off` `0xe297` outputs clean
     HDMI feed while keeping LCD active).
   - Internal recording (`Rec. Media dur HDMI Output = On`) + `Log Shooting != Off` or `PPLUT1..4`
     clamps HDMI output to `1080` regardless of `[Output Resolution]`, while `Off(HDMI Only)`
     (`0x6573`) OR `RAW Output = On` (`0x6e97`) outputs `4K` and automatically forces
     `[HDMI Info. Display] = [Off]` (`S&Q` locks out `Off(HDMI Only)` & `RAW Output`). Verifies
     `(Setup)` survival across `[Camera Settings Reset]` (with `[Framing Settings (HDMI)]`
     reset exception).

3. **Check Group C (`GROUP_C_PROTECT_4SCOPES_VS_FORMAT_OVERRIDE_AND_DUAL_LAYER_SLOT1_WP` — Wave 47 §3)**:
   - All 4 `ILME-FX3` `[Protect]` scopes (`Single`/`Multiple Img.` `0xe2ca`, `All in this Folder`
     `0x6848`, `All with this date` `0x69f7`, `All Images in This Group` `0xe826`) block
     `[Delete]` / `[Delete pressing twice]` while copy strips protection, yet **`[Format]`
     (`0xe449`/`0xe414`, Quick `0xe792` / Full `0xe8f5`) wipes protected files AND `M1..M4` card
     settings** — so `Slot 1` recovery media requires BOTH physical SD `WP` lock
     (`MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1`) AND `slot1_format_hard_locked == True`.

4. **Check Group D (`GROUP_D_RESET_NETWORK_AUTOREBOOT_AIRPLANE_ZERO_RF_AND_TIER0` — Wave 47 §4 + Tier-0)**:
   - Verifies exact 3-way reset boundary (`[Reset Network Set.]` clears Wi-Fi/BT/FTP/Cloud/
     Streaming/Certs, preserves Shooting/Setup/Playback/CAMSET, triggers mandatory auto-reboot
     `BKID_APP_is_shutdown_factor_network_reset` / `0x65d3`, and resets `[Airplane Mode]` to
     `Off`), requiring post-reboot `[Airplane Mode] = [On]` (`0x6df9`) + `passive_tx_bytes == 0`
     before zero-RF bench authorization, alongside `16/16 H0 == H3` and dual-media `528 B`
     `FX3RCPT1` Tier-0 receipt gating.

Hard-Locked Safety Invariants (UNCONDITIONAL):
- `overall_ready_for_hardware_attach = False`
- `hardware_live_attachment_authorized = False`
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `spi_nor_write_authorized = False`
- `el3_payload_transmit_authorized = False`
- `sd_physical_media_written = False`
- `usb_streaming_exposed_in_fx3_ui = False`
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
# Schema, Verdicts & Non-Shadowing P279_* Domain Constants
# ---------------------------------------------------------------------------

PHASE_279_SCHEMA: str = "realhw_usb_mode_hdmi_info_protect_and_network_reset_verifier_v1"
P279_SCHEMA: str = PHASE_279_SCHEMA
REALHW_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_SCHEMA: str = PHASE_279_SCHEMA
PHASE_279_VERSION: str = "279.0.0"
P279_VERSION: str = PHASE_279_VERSION
P279_SONY_HELP_GUIDE_ID: str = "ilc/2210"

P279_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS: str = (
    "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
)
P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED: str = (
    "GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_READONLY_PREFLIGHT_VERIFIED"
)
P279_GO_NO_GO_BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_FAILURE: str = (
    "BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_CHECK_FAILURE"
)
PHASE_279_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    P279_GO_NO_GO_BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED,
)

P279_CHECK_GROUP_A_ID: str = (
    "GROUP_A_USB_CONNECTION_MODE_NOUVC_AND_DATA_ISOLATED_USB_PD"
)
P279_CHECK_GROUP_B_ID: str = (
    "GROUP_B_HDMI_INFO_DISPLAY_CLEAN_FEED_AND_LOG_1080_VS_4K_OVERRIDE"
)
P279_CHECK_GROUP_C_ID: str = (
    "GROUP_C_PROTECT_4SCOPES_VS_FORMAT_OVERRIDE_AND_DUAL_LAYER_SLOT1_WP"
)
P279_CHECK_GROUP_D_ID: str = (
    "GROUP_D_RESET_NETWORK_AUTOREBOOT_AIRPLANE_ZERO_RF_AND_TIER0"
)
PHASE_279_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P279_CHECK_GROUP_A_ID,
    P279_CHECK_GROUP_B_ID,
    P279_CHECK_GROUP_C_ID,
    P279_CHECK_GROUP_D_ID,
)

PHASE279_RAW_FIRMWARE_BYTES_LEAKED: int = 0
PHASE279_PASSIVE_TX_BYTES_EMITTED: int = 0
PHASE279_USB_PACKETS_TRANSMITTED: int = 0

# Group A Constants (Wave 47 §1 — USB Connection Mode 4-Mode, NOUVC, LUN, USB PD)
P279_USB_CONN_BKID: str = "BKID_APP_setting_usb_connection_method"
P279_USB_CONN_RESID16_HEX: str = "0x69a2"
P279_FX3_USB_FOUR_MODES: Tuple[str, ...] = (
    "SEL_WHEN_CONNECT",
    "MASS_STORAGE",
    "MTP",
    "REMOTE_SHOOTING",
)
P279_FX3_USB_MODE_RESIDS: Dict[str, str] = {
    "SEL_WHEN_CONNECT": "0x7738",
    "MASS_STORAGE": "0x6c54",
    "MTP": "0xe24b",
    "REMOTE_SHOOTING": "0x60aa",
}
P279_FX3_MSC_VID_PID: str = "054C:0DA1"
P279_DORMANT_NOUVC_MODES: Tuple[str, ...] = (
    "USB_STREAMING",
    "UVC",
    "UAC",
    "UVC_UAC",
    "WEBCAM",
)
P279_DORMANT_UVC_KMOD_NAME: str = "usb_f_uvc.ko"
P279_DORMANT_UVC_KMOD_BYTES: int = 78840
P279_DORMANT_UVC_RESID16_HEX: str = "0x7399"
P279_FX6_USB_TETHERING_RESID16_HEX: str = "0x29c9"
P279_AIRGAP_BLOCKED_DATA_USB_MODES: Tuple[str, ...] = (
    "MASS_STORAGE",
    "MTP",
    "REMOTE_SHOOTING",
    "USB_LAN",
)
P279_USB_LUN_BKID: str = "BKID_APP_setting_lun_settings"
P279_USB_LUN_RESID16_HEX: str = "0x6b19"
P279_VALID_USB_LUN_MODES: Tuple[str, ...] = ("MULTI", "SINGLE")
P279_USB_LUN_RESIDS: Dict[str, str] = {
    "MULTI": "0xe631",
    "SINGLE": "0x776d",
}
P279_USB_SUPPLY_BKID: str = "BKID_APP_setting_usb_supply"
P279_USB_SUPPLY_RESID16_HEX: str = "0x721e"
P279_VALID_USB_POWER_TERMINALS: Tuple[str, ...] = ("USB_TYPE_C", "NONE")
P279_FORBIDDEN_USB_POWER_TERMINALS: Tuple[str, ...] = ("MULTI_MICRO_USB",)
P279_VALID_POWER_SOURCES: Tuple[str, ...] = (
    "INTERNAL_NP_FZ100",
    "USB_PD_BODY",
    "DC_C1_COUPLER",
)
P279_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)

# Group B Constants (Wave 47 §2 — HDMI Info. Display, Clean Feed, 1080 Clamp vs 4K Override)
P279_HDMI_INFO_BKID: str = "BKID_APP_setting_hdmi_info_display"
P279_HDMI_INFO_RESID16_HEX: str = "0x6e7c"
P279_HDMI_INFO_MODES: Tuple[str, ...] = ("ON", "OFF")
P279_HDMI_INFO_RESIDS: Dict[str, str] = {
    "ON": "0xe07c",
    "OFF": "0xe297",
}
P279_HDMI_INFO_CAUTION_ID: str = "CAUTION_ID_FACTOR_HDMI_INFO_DISPLAY_ON"
P279_VALID_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("ON", "OFF", "OFF_HDMI_ONLY")
P279_OFF_HDMI_ONLY_RESID16_HEX: str = "0x6573"
P279_HDMI_RAW_OUTPUT_RESID16_HEX: str = "0x6e97"
P279_VALID_OUTPUT_RESOLUTIONS: Tuple[str, ...] = ("AUTO", "2160P", "1080P", "1080I")
P279_VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "CINE_EI_QUICK",
    "CINE_EI",
    "FLEXIBLE_ISO",
)
P279_ACTIVE_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "CINE_EI_QUICK",
    "CINE_EI",
    "FLEXIBLE_ISO",
)
P279_PPLUT_PROFILES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
P279_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P279_FRAMING_SETTINGS_HDMI_RESET_EXCEPTION: str = "Framing Settings (HDMI)"

# Group C Constants (Wave 47 §3 — Protect 4 Scopes vs Format Override & Dual-Layer Slot-1 WP)
P279_PROTECT_FOUR_SCOPES: Tuple[str, ...] = (
    "SINGLE_OR_MULTIPLE_IMG",
    "ALL_IN_THIS_FOLDER",
    "ALL_WITH_THIS_DATE",
    "ALL_IMAGES_IN_THIS_GROUP",
)
P279_PROTECT_SCOPE_RESIDS: Dict[str, str] = {
    "SINGLE_OR_MULTIPLE_IMG": "0xe2ca",
    "ALL_IN_THIS_FOLDER": "0x6848",
    "ALL_WITH_THIS_DATE": "0x69f7",
    "ALL_IMAGES_IN_THIS_GROUP": "0xe826",
}
P279_FORMAT_RESID16_HEX: str = "0xe449"
P279_FORMAT_PROMPT_RESID16_HEX: str = "0xe414"
P279_FORMAT_MODES: Tuple[str, ...] = ("NONE", "QUICK", "FULL")
P279_FORMAT_MODE_RESIDS: Dict[str, str] = {
    "QUICK": "0xe792",
    "FULL": "0xe8f5",
}
P279_SLOT1_WP_ERROR_STATUS: str = "MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1"
P279_IMAGE_JUMP_PROTECT_ONLY_RESID16_HEX: str = "0x72d1"
P279_FTP_TARGET_PROTECT_RESID16_HEX: str = "0x694a"
P279_FX6_LOCK_UNLOCK_CLIP_RESID16_HEX: str = "0x42af"
P279_FX6_FORMAT_MEDIA_RESID16_HEX: str = "0x4254"

# Group D Constants (Wave 47 §4 — Reset Network Set. Auto-Reboot, Airplane Mode, 3-Way Reset & Tier-0)
P279_RESET_NW_MENU_RESID16_HEX: str = "0x60d3"
P279_RESET_NW_SHUTDOWN_BKID: str = "BKID_APP_is_shutdown_factor_network_reset"
P279_RESET_NW_AUTOREBOOT_PROMPT_RESID16_HEX: str = "0x65d3"
P279_AIRPLANE_MODE_BKID: str = "BKID_APP_setting_airplane_mode"
P279_AIRPLANE_MODE_ON_RESID16_HEX: str = "0x6df9"
P279_RESET_NW_CLEARED_DOMAINS: Tuple[str, ...] = (
    "WIFI_SSID_PSK_DIRECT_IP",
    "BLUETOOTH_PAIRING_FUNC_RMT_CTRL",
    "FTP_PROFILES_0_TO_8_AUTOSAVE",
    "CREATORS_CLOUD_REMOTE_IPSEC_USBLAN",
    "NETWORK_STREAMING_RTMP_RTMPS_SRT_CERTS",
    "AIRPLANE_MODE_RESET_TO_OFF",
)
P279_RESET_NW_PRESERVED_DOMAINS: Tuple[str, ...] = (
    "SHOOTING_EXPOSURE_FOCUS",
    "SETUP_USB_HDMI_LANGUAGE_VOLUME",
    "PLAYBACK_PROTECT_DELETE_CONFIRM",
    "CAMSET_M1_TO_M4_CARD_SETTINGS",
    "REGISTERED_FACES",
    "USER_CUBE_LUTS",
)
P279_FX6_NETWORK_RESET_RESID16_HEX: str = "0x4291"

# Error Codes
P279_GA_ERR_MODEL_OR_FW_FLOOR: str = "P279_GA_ERR_MODEL_OR_FW_FLOOR"
P279_GA_ERR_USB_MODE_4MODE_OR_NOUVC_STREAMING_SPOOF: str = (
    "P279_GA_ERR_USB_MODE_4MODE_OR_NOUVC_STREAMING_SPOOF"
)
P279_GA_ERR_AIRGAP_DATA_ENUMERATION_OR_UNISOLATED_LINES: str = (
    "P279_GA_ERR_AIRGAP_DATA_ENUMERATION_OR_UNISOLATED_LINES"
)
P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE: str = (
    "P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE"
)

P279_GB_ERR_HDMI_INFO_DISPLAY_LCD_BLANK_OR_CLEAN_FEED_CONFLICT: str = (
    "P279_GB_ERR_HDMI_INFO_DISPLAY_LCD_BLANK_OR_CLEAN_FEED_CONFLICT"
)
P279_GB_ERR_LOG_PPLUT_1080_CLAMP_OR_HDMI_ONLY_RAW_4K_OVERRIDE: str = (
    "P279_GB_ERR_LOG_PPLUT_1080_CLAMP_OR_HDMI_ONLY_RAW_4K_OVERRIDE"
)
P279_GB_ERR_SETUP_RESET_SURVIVAL_OR_FRAMING_HDMI_EXCEPTION: str = (
    "P279_GB_ERR_SETUP_RESET_SURVIVAL_OR_FRAMING_HDMI_EXCEPTION"
)

P279_GC_ERR_PROTECT_4SCOPES_DELETE_BLOCK_OR_COPY_STRIP_INVALID: str = (
    "P279_GC_ERR_PROTECT_4SCOPES_DELETE_BLOCK_OR_COPY_STRIP_INVALID"
)
P279_GC_ERR_FORMAT_OVERRIDE_OR_DUAL_LAYER_SLOT1_WP_FIREWALL: str = (
    "P279_GC_ERR_FORMAT_OVERRIDE_OR_DUAL_LAYER_SLOT1_WP_FIREWALL"
)

P279_GD_ERR_RESET_NETWORK_AUTOREBOOT_OR_3WAY_BOUNDARY_VIOLATION: str = (
    "P279_GD_ERR_RESET_NETWORK_AUTOREBOOT_OR_3WAY_BOUNDARY_VIOLATION"
)
P279_GD_ERR_POST_REBOOT_AIRPLANE_ON_OR_ZERO_RF_VIOLATION: str = (
    "P279_GD_ERR_POST_REBOOT_AIRPLANE_ON_OR_ZERO_RF_VIOLATION"
)
P279_GD_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "P279_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)

_TRIVIAL_HEX64_SET = {"0" * 64, "f" * 64}


# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase279DonorInspectionResult:
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
class P279CheckGroupAUsbConnectionModeResult:
    check_group_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    sony_help_guide_id: str
    reset_action: str
    usb_conn_bkid: str
    usb_conn_resid16_hex: str
    exposed_usb_modes: Tuple[str, ...]
    usb_connection_mode: str
    usb_streaming_exposed_in_fx3_ui: bool
    dormant_uvc_kmod_name: str
    dormant_uvc_kmod_bytes: int
    dormant_uvc_kmod_insmodded: bool
    air_gapped_bench: bool
    usb_data_lines_physically_isolated: bool
    host_usb_data_enumeration_active: bool
    usb_lun_setting: str
    usb_power_supply: str
    power_source: str
    usb_power_terminal: str
    np_fz100_battery_inserted: bool
    usb_setup_survives_camera_and_network_reset: bool
    usb_setup_resets_on_initialize: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P279CheckGroupBHdmiInfoCleanFeedResult:
    check_group_id: str
    passed: bool
    hdmi_info_bkid: str
    hdmi_info_resid16_hex: str
    hdmi_info_display_requested: str
    effective_hdmi_info_display: str
    hdmi_info_forced_off_by_raw_or_hdmi_only: bool
    built_in_lcd_blanked: bool
    touch_focus_disabled: bool
    hdmi_osd_letterboxed: bool
    clean_hdmi_feed_active: bool
    rec_media_dur_hdmi_output: str
    hdmi_raw_output: bool
    shoot_mode: str
    log_shooting_mode: str
    picture_profile: str
    hdmi_output_resolution: str
    effective_hdmi_output_resolution: str
    hdmi_clamped_to_1080_by_log_or_pplut: bool
    hdmi_setup_survives_camera_and_network_reset: bool
    framing_settings_hdmi_resets_on_camera_reset: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P279CheckGroupCProtectVsFormatSlot1Result:
    check_group_id: str
    passed: bool
    protect_four_scopes: Tuple[str, ...]
    protect_scope_selected: str
    protected_items_block_delete: bool
    copy_strips_protection_verified: bool
    format_resid16_hex: str
    format_overrides_protect_and_m1_m4_verified: bool
    slot1_contains_tier0_dump: bool
    slot1_wp_locked: bool
    slot1_wp_error_status: str
    slot1_format_hard_locked: bool
    slot1_vault_write_firewall_enforced: bool
    slot1_format_mode: str
    slot1_delete_requested: bool
    slot1_vault_delete_events: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P279CheckGroupDResetNetworkZeroRfTier0Result:
    check_group_id: str
    passed: bool
    reset_network_set_executed: bool
    auto_reboot_triggered_on_network_reset: bool
    reset_nw_shutdown_bkid: str
    reset_nw_autoreboot_prompt_resid16_hex: str
    wifi_psks_cleared: bool
    bt_pairings_cleared: bool
    ftp_cloud_certs_cleared: bool
    streaming_rtmp_srt_cleared: bool
    network_reset_resets_airplane_to_off: bool
    three_way_reset_boundary_verified: bool
    post_reboot_airplane_mode: str
    airplane_mode_on_resid16_hex: str
    zero_rf_bench_authorized: bool
    passive_tx_bytes_emitted: int
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    tier0_receipt_present: bool
    tier0_receipt_verified: bool
    distinct_physical_media_verified: bool
    warnings: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwUsbModeHdmiInfoProtectNetworkResetReport:
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
    usb_streaming_exposed_in_fx3_ui: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    passive_tx_bytes_emitted: int
    slot1_wp_locked: bool
    slot1_format_hard_locked: bool
    slot1_vault_delete_events: int
    check_group_count: int
    check_groups_passed: int
    all_4_check_groups_passed: bool
    tier0_receipt_verified: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    donor_inspection: Phase279DonorInspectionResult
    check_group_a_usb_connection_mode: P279CheckGroupAUsbConnectionModeResult
    check_group_b_hdmi_info_clean_feed: P279CheckGroupBHdmiInfoCleanFeedResult
    check_group_c_protect_vs_format_slot1: P279CheckGroupCProtectVsFormatSlot1Result
    check_group_d_reset_network_zero_rf_tier0: P279CheckGroupDResetNetworkZeroRfTier0Result
    warnings: Tuple[str, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase279ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers & Bounded O_RDONLY Donor Inspection (< 0.15s)
# ---------------------------------------------------------------------------


def _norm_token(raw: str) -> str:
    return re.sub(r"[\s\-:/\.]+", "_", str(raw).strip().upper()).strip("_")


def _norm_usb_mode(raw: str) -> str:
    s = str(raw).strip()
    tok = re.sub(r"[\s\-:/\.()]+", "_", s.upper()).strip("_")
    aliases = {
        "SEL_WHEN_CONNECT": "SEL_WHEN_CONNECT",
        "SELECT_WHEN_CONNECT": "SEL_WHEN_CONNECT",
        "SELECT_AFTER_CONNECTION": "SEL_WHEN_CONNECT",
        "MASS_STORAGE": "MASS_STORAGE",
        "MASSSTORAGE": "MASS_STORAGE",
        "MASSSTORAGE_MSC": "MASS_STORAGE",
        "MASS_STORAGE_MSC": "MASS_STORAGE",
        "MSC": "MASS_STORAGE",
        "MTP": "MTP",
        "REMOTE_SHOOTING": "REMOTE_SHOOTING",
        "REMOTE_SHOOT": "REMOTE_SHOOTING",
        "REMOTE_SHOOT_PC_REMOTE": "REMOTE_SHOOTING",
        "PC_REMOTE": "REMOTE_SHOOTING",
        "REMOTE_PC": "REMOTE_SHOOTING",
        "USB_STREAMING": "USB_STREAMING",
        "STREAMING": "USB_STREAMING",
        "UVC": "UVC",
        "UAC": "UAC",
        "UVC_UAC": "UVC_UAC",
        "WEBCAM": "WEBCAM",
        "USB_LAN": "USB_LAN",
        "USBLAN": "USB_LAN",
    }
    return aliases.get(tok, tok)


def _norm_rec_media_hdmi(raw: str) -> str:
    s = str(raw).strip().upper()
    aliases = {
        "ON": "ON",
        "OFF": "OFF",
        "OFF(HDMI ONLY)": "OFF_HDMI_ONLY",
        "OFF_HDMI_ONLY": "OFF_HDMI_ONLY",
    }
    return aliases.get(s, _norm_token(s))


def _norm_protect_scope(raw: str) -> str:
    tok = _norm_token(raw)
    aliases = {
        "SINGLE": "SINGLE_OR_MULTIPLE_IMG",
        "MULTIPLE_IMG": "SINGLE_OR_MULTIPLE_IMG",
        "SINGLE_MULTIPLE_IMG": "SINGLE_OR_MULTIPLE_IMG",
        "SINGLE_OR_MULTIPLE_IMG": "SINGLE_OR_MULTIPLE_IMG",
        "SINGLE_IMAGE": "SINGLE_OR_MULTIPLE_IMG",
        "ALL_IN_THIS_FOLDER": "ALL_IN_THIS_FOLDER",
        "ALL_WITH_THIS_DATE": "ALL_WITH_THIS_DATE",
        "ALL_IMAGES_IN_THIS_GROUP": "ALL_IMAGES_IN_THIS_GROUP",
    }
    return aliases.get(tok, tok)


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


def inspect_phase279_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase279DonorInspectionResult:
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
        return Phase279DonorInspectionResult(
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
            raw_firmware_bytes_leaked=PHASE279_RAW_FIRMWARE_BYTES_LEAKED,
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
                "synthetic:im.elf",
                "synthetic:libJiritsu.so",
                "synthetic:libUsbBusPower.so",
                "synthetic:appFw.so",
                "synthetic:libWlanResource.so",
                "synthetic:upm.ko",
            ]
        )

    elapsed = round(time.perf_counter() - t0, 6)
    within_budget = elapsed < max_seconds
    if not within_budget:
        errors.append(f"Donor inspection exceeded {max_seconds:.3f}s budget: {elapsed:.6f}s")

    return Phase279DonorInspectionResult(
        passed=(len(errors) == 0),
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
        raw_firmware_bytes_leaked=PHASE279_RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group A (Wave 47 §1): [USB Connection Mode] 4-Mode vs NOUVC & Data-Isolated USB PD
# ---------------------------------------------------------------------------


def evaluate_p279_check_group_a_usb_connection_mode(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P279_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    usb_conn_bkid: str = P279_USB_CONN_BKID,
    usb_conn_resid16_hex: str = P279_USB_CONN_RESID16_HEX,
    exposed_usb_modes: Sequence[str] = P279_FX3_USB_FOUR_MODES,
    usb_connection_mode: str = "SEL_WHEN_CONNECT",
    expect_usb_streaming_uvc: bool = False,
    usb_streaming_exposed_in_fx3_ui: bool = False,
    dormant_uvc_kmod_name: str = P279_DORMANT_UVC_KMOD_NAME,
    dormant_uvc_kmod_bytes: int = P279_DORMANT_UVC_KMOD_BYTES,
    dormant_uvc_kmod_insmodded: bool = False,
    air_gapped_bench: bool = True,
    usb_data_lines_physically_isolated: bool = True,
    host_usb_data_enumeration_active: bool = False,
    usb_lun_setting: str = "MULTI",
    usb_power_supply: str = "ON",
    power_source: str = "USB_PD_BODY",
    usb_power_terminal: str = "USB_TYPE_C",
    np_fz100_battery_inserted: bool = True,
    claimed_usb_setup_reset_on_camera_reset: bool = False,
    claimed_usb_setup_reset_on_network_reset: bool = False,
    claimed_usb_setup_survives_initialize: bool = False,
) -> P279CheckGroupAUsbConnectionModeResult:
    """Verify Wave 47 [USB Connection Mode] 4-mode reality, NOUVC guard & data-isolated USB PD."""
    errors: List[str] = []

    fw_tuple = _parse_fw_tuple(body_fw)
    if (
        int(body_model_id) != TARGET_MODEL_ID_INT
        or fw_tuple is None
        or fw_tuple < MIN_BODY_FW_TUPLE
        or str(sony_help_guide_id).strip() != P279_SONY_HELP_GUIDE_ID
    ):
        errors.append(
            f"{P279_GA_ERR_MODEL_OR_FW_FLOOR}: expected ILME-FX3 (0x{TARGET_MODEL_ID_INT:08x}), "
            f"fw >= 2.04, guide={P279_SONY_HELP_GUIDE_ID!r}; got model=0x{int(body_model_id):08x}, "
            f"fw={body_fw!r}, guide={sony_help_guide_id!r}"
        )

    rst_norm = _norm_token(reset_action)
    if rst_norm not in P279_VALID_RESET_ACTIONS:
        errors.append(
            f"{P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE}: "
            f"invalid reset_action={reset_action!r}"
        )

    bkid_norm = str(usb_conn_bkid).strip()
    resid_norm = str(usb_conn_resid16_hex).strip().lower()
    exposed_norm = tuple(_norm_usb_mode(m) for m in exposed_usb_modes)
    usb_mode_norm = _norm_usb_mode(usb_connection_mode)
    kmod_name = str(dormant_uvc_kmod_name).strip()
    kmod_bytes = int(dormant_uvc_kmod_bytes)

    nouvc_spoof = (
        bool(expect_usb_streaming_uvc)
        or bool(usb_streaming_exposed_in_fx3_ui)
        or bool(dormant_uvc_kmod_insmodded)
        or usb_mode_norm in P279_DORMANT_NOUVC_MODES
        or any(m in P279_DORMANT_NOUVC_MODES for m in exposed_norm)
    )
    if (
        bkid_norm != P279_USB_CONN_BKID
        or resid_norm != P279_USB_CONN_RESID16_HEX
        or exposed_norm != P279_FX3_USB_FOUR_MODES
        or kmod_name != P279_DORMANT_UVC_KMOD_NAME
        or kmod_bytes != P279_DORMANT_UVC_KMOD_BYTES
        or nouvc_spoof
        or usb_mode_norm not in (*P279_FX3_USB_FOUR_MODES, "USB_LAN")
    ):
        errors.append(
            f"{P279_GA_ERR_USB_MODE_4MODE_OR_NOUVC_STREAMING_SPOOF}: stock ILME-FX3 Ver. 7.02 "
            f"exposes only 4 USB Connection Modes (NOUVC dormant {kmod_name}={kmod_bytes}B); "
            f"got mode={usb_connection_mode!r}, exposed={exposed_norm}, "
            f"expect_uvc={expect_usb_streaming_uvc}, ui_exposed={usb_streaming_exposed_in_fx3_ui}, "
            f"insmodded={dormant_uvc_kmod_insmodded}"
        )

    usb_sup_norm = _norm_token(usb_power_supply)
    pwr_src_norm = _norm_token(power_source)
    usb_pd_in_use = (usb_sup_norm == "ON") or (pwr_src_norm == "USB_PD_BODY")
    data_enum_blocked_violation = bool(air_gapped_bench) and (
        usb_mode_norm in P279_AIRGAP_BLOCKED_DATA_USB_MODES
        or bool(host_usb_data_enumeration_active)
        or (usb_pd_in_use and not bool(usb_data_lines_physically_isolated))
    )
    if data_enum_blocked_violation:
        errors.append(
            f"{P279_GA_ERR_AIRGAP_DATA_ENUMERATION_OR_UNISOLATED_LINES}: air-gapped Tier-0 bench "
            f"forbids MSC/MTP/Remote/USB-LAN enumeration and permits USB PD only with isolated D+/D-/SS "
            f"data lines (mode={usb_mode_norm}, host_enum={host_usb_data_enumeration_active}, "
            f"usb_pd_in_use={usb_pd_in_use}, data_isolated={usb_data_lines_physically_isolated})"
        )

    lun_norm = _norm_token(usb_lun_setting)
    term_norm = _norm_token(usb_power_terminal)
    usb_survives = (not bool(claimed_usb_setup_reset_on_camera_reset)) and (
        not bool(claimed_usb_setup_reset_on_network_reset)
    )
    usb_resets_init = not bool(claimed_usb_setup_survives_initialize)

    if (
        lun_norm not in P279_VALID_USB_LUN_MODES
        or usb_sup_norm not in ("ON", "OFF")
        or pwr_src_norm not in P279_VALID_POWER_SOURCES
        or term_norm in P279_FORBIDDEN_USB_POWER_TERMINALS
        or term_norm not in P279_VALID_USB_POWER_TERMINALS
        or (usb_pd_in_use and term_norm != "USB_TYPE_C")
        or (usb_pd_in_use and not bool(np_fz100_battery_inserted))
        or not usb_survives
        or not usb_resets_init
    ):
        errors.append(
            f"{P279_GA_ERR_USB_POWER_NPFZ100_TYPEC_LUN_OR_RESET_PERSISTENCE}: [USB LUN Setting], "
            f"[USB Power Supply] (Type-C + NP-FZ100), or (Setup)->[USB] reset persistence violated "
            f"(lun={usb_lun_setting!r}, supply={usb_power_supply!r}, src={power_source!r}, "
            f"term={usb_power_terminal!r}, np_fz100={np_fz100_battery_inserted}, "
            f"survives_cam_nw={usb_survives}, resets_init={usb_resets_init})"
        )

    return P279CheckGroupAUsbConnectionModeResult(
        check_group_id=P279_CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        body_model_id_hex=f"0x{int(body_model_id):08x}",
        body_fw=str(body_fw).strip(),
        sony_help_guide_id=str(sony_help_guide_id).strip(),
        reset_action=rst_norm,
        usb_conn_bkid=bkid_norm,
        usb_conn_resid16_hex=resid_norm,
        exposed_usb_modes=exposed_norm,
        usb_connection_mode=usb_mode_norm,
        usb_streaming_exposed_in_fx3_ui=bool(usb_streaming_exposed_in_fx3_ui),
        dormant_uvc_kmod_name=kmod_name,
        dormant_uvc_kmod_bytes=kmod_bytes,
        dormant_uvc_kmod_insmodded=bool(dormant_uvc_kmod_insmodded),
        air_gapped_bench=bool(air_gapped_bench),
        usb_data_lines_physically_isolated=bool(usb_data_lines_physically_isolated),
        host_usb_data_enumeration_active=bool(host_usb_data_enumeration_active),
        usb_lun_setting=lun_norm,
        usb_power_supply=usb_sup_norm,
        power_source=pwr_src_norm,
        usb_power_terminal=term_norm,
        np_fz100_battery_inserted=bool(np_fz100_battery_inserted),
        usb_setup_survives_camera_and_network_reset=usb_survives,
        usb_setup_resets_on_initialize=usb_resets_init,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group B (Wave 47 §2): [HDMI Info. Display] Clean Feed & Log 1080 Clamp vs 4K Override
# ---------------------------------------------------------------------------


def evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
    *,
    hdmi_info_bkid: str = P279_HDMI_INFO_BKID,
    hdmi_info_resid16_hex: str = P279_HDMI_INFO_RESID16_HEX,
    hdmi_info_display: str = "OFF",
    require_clean_hdmi_feed: bool = True,
    require_unblanked_lcd: bool = True,
    allow_lcd_blanking_and_osd: bool = False,
    expect_touch_focus_active_when_hdmi_info_on: bool = False,
    expect_full_raster_clean_feed_when_hdmi_info_on: bool = False,
    rec_media_dur_hdmi_output: str = "ON",
    hdmi_raw_output: bool = False,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    hdmi_output_resolution: str = "AUTO",
    expect_4k_hdmi_during_internal_log_or_pplut: bool = False,
    expect_hdmi_info_on_during_raw_or_hdmi_only: bool = False,
    expect_sq_allows_hdmi_only_or_raw: bool = False,
    reset_action: str = "NONE",
    claimed_hdmi_setup_reset_on_camera_reset: bool = False,
    claimed_hdmi_setup_reset_on_network_reset: bool = False,
    claimed_framing_settings_hdmi_survives_camera_reset: bool = False,
) -> P279CheckGroupBHdmiInfoCleanFeedResult:
    """Verify Wave 47 [HDMI Info. Display] LCD-blanking vs clean feed & Log 1080 vs 4K override."""
    errors: List[str] = []

    bkid_norm = str(hdmi_info_bkid).strip()
    resid_norm = str(hdmi_info_resid16_hex).strip().lower()
    hdmi_info_req = _norm_token(hdmi_info_display)
    rec_media = _norm_rec_media_hdmi(rec_media_dur_hdmi_output)
    raw_out = bool(hdmi_raw_output)
    sh_mode = _norm_token(shoot_mode)
    log_mode = _norm_token(log_shooting_mode)
    pp_norm = _norm_token(picture_profile)
    out_res = _norm_token(hdmi_output_resolution)
    rst_norm = _norm_token(reset_action)

    forced_off = raw_out or (rec_media == "OFF_HDMI_ONLY")
    eff_hdmi_info = "OFF" if forced_off else hdmi_info_req
    lcd_blanked = eff_hdmi_info == "ON"
    touch_disabled = lcd_blanked
    osd_letterboxed = lcd_blanked
    clean_feed = eff_hdmi_info == "OFF"

    if (
        bkid_norm != P279_HDMI_INFO_BKID
        or resid_norm != P279_HDMI_INFO_RESID16_HEX
        or hdmi_info_req not in P279_HDMI_INFO_MODES
        or (forced_off and bool(expect_hdmi_info_on_during_raw_or_hdmi_only))
        or (hdmi_info_req == "ON" and bool(expect_touch_focus_active_when_hdmi_info_on))
        or (hdmi_info_req == "ON" and bool(expect_full_raster_clean_feed_when_hdmi_info_on))
        or (
            lcd_blanked
            and (bool(require_clean_hdmi_feed) or bool(require_unblanked_lcd))
            and not bool(allow_lcd_blanking_and_osd)
        )
    ):
        errors.append(
            f"{P279_GB_ERR_HDMI_INFO_DISPLAY_LCD_BLANK_OR_CLEAN_FEED_CONFLICT}: "
            f"[HDMI Info. Display] LCD-blanking / touch-focus / clean-feed conflict "
            f"(req={hdmi_info_display!r}, eff={eff_hdmi_info}, lcd_blanked={lcd_blanked}, "
            f"require_clean={require_clean_hdmi_feed}, require_unblanked={require_unblanked_lcd}, "
            f"allow_blank={allow_lcd_blanking_and_osd}, forced_off={forced_off}, "
            f"expect_on_in_raw_only={expect_hdmi_info_on_during_raw_or_hdmi_only})"
        )

    sq_conflict = (sh_mode == "S_AND_Q") and (
        raw_out or rec_media == "OFF_HDMI_ONLY" or bool(expect_sq_allows_hdmi_only_or_raw)
    )
    internal_rec = rec_media == "ON"
    log_or_pplut = (log_mode in P279_ACTIVE_LOG_SHOOTING_MODES) or (
        pp_norm in P279_PPLUT_PROFILES
    )
    clamped_1080 = internal_rec and log_or_pplut and (not raw_out)

    if raw_out:
        eff_res = "4K_16BIT_RAW"
    elif rec_media == "OFF_HDMI_ONLY":
        eff_res = "4K_HDMI_ONLY_10BIT"
    elif clamped_1080:
        eff_res = "1080_CLAMPED"
    elif out_res in ("1080P", "1080I"):
        eff_res = out_res
    else:
        eff_res = "4K_2160P_COMPATIBLE"

    if (
        rec_media not in P279_VALID_REC_MEDIA_DUR_HDMI_MODES
        or sh_mode not in P279_VALID_SHOOT_MODES
        or log_mode not in P279_VALID_LOG_SHOOTING_MODES
        or out_res not in P279_VALID_OUTPUT_RESOLUTIONS
        or sq_conflict
        or (clamped_1080 and out_res == "2160P")
        or (clamped_1080 and bool(expect_4k_hdmi_during_internal_log_or_pplut))
    ):
        errors.append(
            f"{P279_GB_ERR_LOG_PPLUT_1080_CLAMP_OR_HDMI_ONLY_RAW_4K_OVERRIDE}: "
            f"HDMI Log/PPLUT 1080 clamp or Off(HDMI Only)/RAW 4K/S&Q rule violated "
            f"(rec_media={rec_media_dur_hdmi_output!r}, raw={raw_out}, shoot={shoot_mode!r}, "
            f"log={log_shooting_mode!r}, pp={picture_profile!r}, out_res={hdmi_output_resolution!r}, "
            f"clamped_1080={clamped_1080}, expect_4k_internal_log={expect_4k_hdmi_during_internal_log_or_pplut})"
        )

    hdmi_survives = (not bool(claimed_hdmi_setup_reset_on_camera_reset)) and (
        not bool(claimed_hdmi_setup_reset_on_network_reset)
    )
    framing_resets = not bool(claimed_framing_settings_hdmi_survives_camera_reset)
    if (
        rst_norm not in P279_VALID_RESET_ACTIONS
        or not hdmi_survives
        or not framing_resets
    ):
        errors.append(
            f"{P279_GB_ERR_SETUP_RESET_SURVIVAL_OR_FRAMING_HDMI_EXCEPTION}: "
            f"(Setup)->[External Output] reset survival or [Framing Settings (HDMI)] exception violated "
            f"(reset_action={reset_action!r}, hdmi_survives={hdmi_survives}, "
            f"framing_resets={framing_resets})"
        )

    return P279CheckGroupBHdmiInfoCleanFeedResult(
        check_group_id=P279_CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        hdmi_info_bkid=bkid_norm,
        hdmi_info_resid16_hex=resid_norm,
        hdmi_info_display_requested=hdmi_info_req,
        effective_hdmi_info_display=eff_hdmi_info,
        hdmi_info_forced_off_by_raw_or_hdmi_only=forced_off,
        built_in_lcd_blanked=lcd_blanked,
        touch_focus_disabled=touch_disabled,
        hdmi_osd_letterboxed=osd_letterboxed,
        clean_hdmi_feed_active=clean_feed,
        rec_media_dur_hdmi_output=rec_media,
        hdmi_raw_output=raw_out,
        shoot_mode=sh_mode,
        log_shooting_mode=log_mode,
        picture_profile=pp_norm,
        hdmi_output_resolution=out_res,
        effective_hdmi_output_resolution=eff_res,
        hdmi_clamped_to_1080_by_log_or_pplut=clamped_1080,
        hdmi_setup_survives_camera_and_network_reset=hdmi_survives,
        framing_settings_hdmi_resets_on_camera_reset=framing_resets,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group C (Wave 47 §3): [Protect] 4 Scopes vs [Format] Override & Dual-Layer Slot-1 WP
# ---------------------------------------------------------------------------


def evaluate_p279_check_group_c_protect_vs_format_slot1(
    *,
    protect_exposed_scopes: Sequence[str] = P279_PROTECT_FOUR_SCOPES,
    protect_scope_selected: str = "ALL_IN_THIS_FOLDER",
    protected_items_block_delete: bool = True,
    expect_copy_preserves_protect: bool = False,
    expect_movie_key_mark_without_menu: bool = False,
    format_resid16_hex: str = P279_FORMAT_RESID16_HEX,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_wp_error_status: str = P279_SLOT1_WP_ERROR_STATUS,
    slot1_format_hard_locked: bool = True,
    slot1_vault_write_firewall_enforced: bool = True,
    slot1_format_mode: str = "NONE",
    slot1_delete_requested: bool = False,
    expect_protect_blocks_format: bool = False,
    expect_format_preserves_m1_m4_camset: bool = False,
    simulated_slot1_vault_delete_events: int = 0,
) -> P279CheckGroupCProtectVsFormatSlot1Result:
    """Verify Wave 47 [Protect] 4 scopes vs [Format] override & mandatory dual-layer Slot-1 WP."""
    errors: List[str] = []

    scopes_norm = tuple(_norm_protect_scope(s) for s in protect_exposed_scopes)
    sel_scope = _norm_protect_scope(protect_scope_selected)
    copy_strips = not bool(expect_copy_preserves_protect)

    if (
        scopes_norm != P279_PROTECT_FOUR_SCOPES
        or sel_scope not in P279_PROTECT_FOUR_SCOPES
        or not bool(protected_items_block_delete)
        or not copy_strips
        or bool(expect_movie_key_mark_without_menu)
    ):
        errors.append(
            f"{P279_GC_ERR_PROTECT_4SCOPES_DELETE_BLOCK_OR_COPY_STRIP_INVALID}: "
            f"[Protect] 4 scopes / delete-block / copy-strip rule violated "
            f"(scopes={scopes_norm}, selected={protect_scope_selected!r}, "
            f"blocks_delete={protected_items_block_delete}, "
            f"expect_copy_preserves={expect_copy_preserves_protect}, "
            f"expect_movie_no_menu={expect_movie_key_mark_without_menu})"
        )

    fmt_resid = str(format_resid16_hex).strip().lower()
    fmt_mode = _norm_token(slot1_format_mode)
    wp_status = str(slot1_wp_error_status).strip()
    fmt_overrides_verified = (
        (not bool(expect_protect_blocks_format))
        and (not bool(expect_format_preserves_m1_m4_camset))
        and fmt_resid == P279_FORMAT_RESID16_HEX
    )

    slot1_del_events = max(0, int(simulated_slot1_vault_delete_events))
    if bool(slot1_delete_requested) or fmt_mode != "NONE":
        slot1_del_events = max(1, slot1_del_events)

    dual_layer_ok = (
        bool(slot1_contains_tier0_dump)
        and bool(slot1_wp_locked)
        and wp_status == P279_SLOT1_WP_ERROR_STATUS
        and bool(slot1_format_hard_locked)
        and bool(slot1_vault_write_firewall_enforced)
    )

    if (
        fmt_mode not in P279_FORMAT_MODES
        or not fmt_overrides_verified
        or not dual_layer_ok
        or slot1_del_events > 0
    ):
        errors.append(
            f"{P279_GC_ERR_FORMAT_OVERRIDE_OR_DUAL_LAYER_SLOT1_WP_FIREWALL}: "
            f"[Format] overrides [Protect] & wipes M1..M4 — Slot-1 requires BOTH SD WP lock "
            f"({P279_SLOT1_WP_ERROR_STATUS}) AND slot1_format_hard_locked=True "
            f"(tier0={slot1_contains_tier0_dump}, wp_locked={slot1_wp_locked}, wp_status={wp_status!r}, "
            f"fmt_locked={slot1_format_hard_locked}, firewall={slot1_vault_write_firewall_enforced}, "
            f"fmt_mode={slot1_format_mode!r}, del_req={slot1_delete_requested}, "
            f"del_events={slot1_del_events}, fmt_overrides_ok={fmt_overrides_verified})"
        )

    return P279CheckGroupCProtectVsFormatSlot1Result(
        check_group_id=P279_CHECK_GROUP_C_ID,
        passed=(len(errors) == 0),
        protect_four_scopes=scopes_norm,
        protect_scope_selected=sel_scope,
        protected_items_block_delete=bool(protected_items_block_delete),
        copy_strips_protection_verified=copy_strips,
        format_resid16_hex=fmt_resid,
        format_overrides_protect_and_m1_m4_verified=fmt_overrides_verified,
        slot1_contains_tier0_dump=bool(slot1_contains_tier0_dump),
        slot1_wp_locked=bool(slot1_wp_locked),
        slot1_wp_error_status=wp_status,
        slot1_format_hard_locked=bool(slot1_format_hard_locked),
        slot1_vault_write_firewall_enforced=bool(slot1_vault_write_firewall_enforced),
        slot1_format_mode=fmt_mode,
        slot1_delete_requested=bool(slot1_delete_requested),
        slot1_vault_delete_events=slot1_del_events,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group D (Wave 47 §4 + Tier-0): [Reset Network Set.] Auto-Reboot, Airplane Mode & Tier-0
# ---------------------------------------------------------------------------


def build_simulated_phase279_tier0_receipts(
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
            f"PHASE279_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE279_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
    *,
    reset_network_set_executed: bool = True,
    auto_reboot_triggered_on_network_reset: bool = True,
    reset_nw_shutdown_bkid: str = P279_RESET_NW_SHUTDOWN_BKID,
    reset_nw_autoreboot_prompt_resid16_hex: str = P279_RESET_NW_AUTOREBOOT_PROMPT_RESID16_HEX,
    wifi_psks_cleared: bool = True,
    bt_pairings_cleared: bool = True,
    ftp_cloud_certs_cleared: bool = True,
    streaming_rtmp_srt_cleared: bool = True,
    network_reset_resets_airplane_to_off: bool = True,
    network_reset_preserves_shooting_setup_playback_camset: bool = True,
    camera_reset_resets_shooting_and_framing_hdmi: bool = True,
    camera_reset_preserves_network_setup_playback_camset: bool = True,
    initialize_clears_all_except_card_m1_m4: bool = True,
    post_reboot_airplane_mode: str = "ON",
    airplane_mode_on_resid16_hex: str = P279_AIRPLANE_MODE_ON_RESID16_HEX,
    require_post_reboot_airplane_on: bool = True,
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
) -> Tuple[P279CheckGroupDResetNetworkZeroRfTier0Result, Tuple[str, ...]]:
    """Verify Wave 47 [Reset Network Set.] 3-way reset boundary, post-reboot Airplane Mode & Tier-0."""
    errors: List[str] = []
    warnings: List[str] = []
    tier0_errors: List[str] = []

    bkid_norm = str(reset_nw_shutdown_bkid).strip()
    prompt_resid = str(reset_nw_autoreboot_prompt_resid16_hex).strip().lower()
    air_resid = str(airplane_mode_on_resid16_hex).strip().lower()

    three_way_ok = (
        bool(wifi_psks_cleared)
        and bool(bt_pairings_cleared)
        and bool(ftp_cloud_certs_cleared)
        and bool(streaming_rtmp_srt_cleared)
        and bool(network_reset_resets_airplane_to_off)
        and bool(network_reset_preserves_shooting_setup_playback_camset)
        and bool(camera_reset_resets_shooting_and_framing_hdmi)
        and bool(camera_reset_preserves_network_setup_playback_camset)
        and bool(initialize_clears_all_except_card_m1_m4)
    )

    if (
        bkid_norm != P279_RESET_NW_SHUTDOWN_BKID
        or prompt_resid != P279_RESET_NW_AUTOREBOOT_PROMPT_RESID16_HEX
        or not bool(reset_network_set_executed)
        or not bool(auto_reboot_triggered_on_network_reset)
        or not three_way_ok
    ):
        errors.append(
            f"{P279_GD_ERR_RESET_NETWORK_AUTOREBOOT_OR_3WAY_BOUNDARY_VIOLATION}: "
            f"[Reset Network Set.] auto-reboot or 3-way reset boundary violated "
            f"(executed={reset_network_set_executed}, auto_reboot={auto_reboot_triggered_on_network_reset}, "
            f"bkid={bkid_norm!r}, prompt={prompt_resid!r}, three_way_ok={three_way_ok})"
        )

    air_norm = _norm_token(post_reboot_airplane_mode)
    passive_tx = max(0, int(simulated_passive_tx_bytes))
    zero_rf_ok = (
        air_norm == "ON"
        and air_resid == P279_AIRPLANE_MODE_ON_RESID16_HEX
        and passive_tx == 0
    )

    if (
        air_norm not in ("ON", "OFF")
        or air_resid != P279_AIRPLANE_MODE_ON_RESID16_HEX
        or (bool(require_post_reboot_airplane_on) and air_norm != "ON")
        or passive_tx != 0
    ):
        errors.append(
            f"{P279_GD_ERR_POST_REBOOT_AIRPLANE_ON_OR_ZERO_RF_VIOLATION}: post-reboot "
            f"[Airplane Mode]=[On] ({P279_AIRPLANE_MODE_ON_RESID16_HEX}) required after "
            f"[Reset Network Set.] resets radio state to Off (airplane={post_reboot_airplane_mode!r}, "
            f"passive_tx={passive_tx})"
        )

    surface_total = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_total, int(simulated_h0_h3_drifted_surfaces)))
    h0_eq_h3 = surface_total - drifted
    if h0_eq_h3 != surface_total:
        errors.append(
            f"{P279_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 parity drift ({h0_eq_h3}/{surface_total})"
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
        raw_a, raw_b, sim_h0 = build_simulated_phase279_tier0_receipts(
            body_serial=eff_serial, emmc_cid=eff_cid, body_fw=body_fw
        )
        dev_a = 101 if dev_a is None else dev_a
        dev_b = 202 if dev_b is None else dev_b
        eff_h0_a = eff_h0_a if eff_h0_a is not None else dict(sim_h0)
        eff_h0_b = eff_h0_b if eff_h0_b is not None else dict(sim_h0)

    if receipt_a_path is not None:
        try:
            _, raw_a, st_a = _read_bounded_slice_o_rdonly(
                Path(receipt_a_path), SD_RECEIPT_BYTES + 64
            )
            if dev_a is None:
                dev_a = int(st_a)
        except OSError as exc:
            tier0_errors.append(
                f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
            )

    if receipt_b_path is not None:
        try:
            _, raw_b, st_b = _read_bounded_slice_o_rdonly(
                Path(receipt_b_path), SD_RECEIPT_BYTES + 64
            )
            if dev_b is None:
                dev_b = int(st_b)
        except OSError as exc:
            tier0_errors.append(
                f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
            )

    receipt_present = (raw_a is not None) and (raw_b is not None)
    distinct_media = False
    receipt_verified = False

    if not receipt_present:
        tier0_errors.append(
            f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    else:
        assert raw_a is not None and raw_b is not None
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media = True
            else:
                tier0_errors.append(
                    f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{P279_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    return (
        P279CheckGroupDResetNetworkZeroRfTier0Result(
            check_group_id=P279_CHECK_GROUP_D_ID,
            passed=(len(errors) == 0),
            reset_network_set_executed=bool(reset_network_set_executed),
            auto_reboot_triggered_on_network_reset=bool(auto_reboot_triggered_on_network_reset),
            reset_nw_shutdown_bkid=bkid_norm,
            reset_nw_autoreboot_prompt_resid16_hex=prompt_resid,
            wifi_psks_cleared=bool(wifi_psks_cleared),
            bt_pairings_cleared=bool(bt_pairings_cleared),
            ftp_cloud_certs_cleared=bool(ftp_cloud_certs_cleared),
            streaming_rtmp_srt_cleared=bool(streaming_rtmp_srt_cleared),
            network_reset_resets_airplane_to_off=bool(network_reset_resets_airplane_to_off),
            three_way_reset_boundary_verified=three_way_ok,
            post_reboot_airplane_mode=air_norm,
            airplane_mode_on_resid16_hex=air_resid,
            zero_rf_bench_authorized=zero_rf_ok,
            passive_tx_bytes_emitted=passive_tx,
            h0_h3_surface_count=surface_total,
            h0_equals_h3_count=h0_eq_h3,
            tier0_receipt_present=receipt_present,
            tier0_receipt_verified=receipt_verified,
            distinct_physical_media_verified=distinct_media,
            warnings=tuple(warnings),
            errors=tuple(errors),
        ),
        tuple(tier0_errors),
    )


# ---------------------------------------------------------------------------
# Top-Level Pre-Shoot Readiness Orchestrator & Tamper-Evident Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P279_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    # Check Group A (Wave 47 §1 — USB Connection Mode, NOUVC & Data-Isolated USB PD)
    usb_conn_bkid: str = P279_USB_CONN_BKID,
    usb_conn_resid16_hex: str = P279_USB_CONN_RESID16_HEX,
    exposed_usb_modes: Sequence[str] = P279_FX3_USB_FOUR_MODES,
    usb_connection_mode: str = "SEL_WHEN_CONNECT",
    expect_usb_streaming_uvc: bool = False,
    usb_streaming_exposed_in_fx3_ui: bool = False,
    dormant_uvc_kmod_name: str = P279_DORMANT_UVC_KMOD_NAME,
    dormant_uvc_kmod_bytes: int = P279_DORMANT_UVC_KMOD_BYTES,
    dormant_uvc_kmod_insmodded: bool = False,
    air_gapped_bench: bool = True,
    usb_data_lines_physically_isolated: bool = True,
    host_usb_data_enumeration_active: bool = False,
    usb_lun_setting: str = "MULTI",
    usb_power_supply: str = "ON",
    power_source: str = "USB_PD_BODY",
    usb_power_terminal: str = "USB_TYPE_C",
    np_fz100_battery_inserted: bool = True,
    claimed_usb_setup_reset_on_camera_reset: bool = False,
    claimed_usb_setup_reset_on_network_reset: bool = False,
    claimed_usb_setup_survives_initialize: bool = False,
    # Check Group B (Wave 47 §2 — HDMI Info. Display & Log 1080 Clamp vs 4K Override)
    hdmi_info_bkid: str = P279_HDMI_INFO_BKID,
    hdmi_info_resid16_hex: str = P279_HDMI_INFO_RESID16_HEX,
    hdmi_info_display: str = "OFF",
    require_clean_hdmi_feed: bool = True,
    require_unblanked_lcd: bool = True,
    allow_lcd_blanking_and_osd: bool = False,
    expect_touch_focus_active_when_hdmi_info_on: bool = False,
    expect_full_raster_clean_feed_when_hdmi_info_on: bool = False,
    rec_media_dur_hdmi_output: str = "ON",
    hdmi_raw_output: bool = False,
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    hdmi_output_resolution: str = "AUTO",
    expect_4k_hdmi_during_internal_log_or_pplut: bool = False,
    expect_hdmi_info_on_during_raw_or_hdmi_only: bool = False,
    expect_sq_allows_hdmi_only_or_raw: bool = False,
    claimed_hdmi_setup_reset_on_camera_reset: bool = False,
    claimed_hdmi_setup_reset_on_network_reset: bool = False,
    claimed_framing_settings_hdmi_survives_camera_reset: bool = False,
    # Check Group C (Wave 47 §3 — Protect 4 Scopes vs Format Override & Dual-Layer Slot-1 WP)
    protect_exposed_scopes: Sequence[str] = P279_PROTECT_FOUR_SCOPES,
    protect_scope_selected: str = "ALL_IN_THIS_FOLDER",
    protected_items_block_delete: bool = True,
    expect_copy_preserves_protect: bool = False,
    expect_movie_key_mark_without_menu: bool = False,
    format_resid16_hex: str = P279_FORMAT_RESID16_HEX,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    slot1_wp_error_status: str = P279_SLOT1_WP_ERROR_STATUS,
    slot1_format_hard_locked: bool = True,
    slot1_vault_write_firewall_enforced: bool = True,
    slot1_format_mode: str = "NONE",
    slot1_delete_requested: bool = False,
    expect_protect_blocks_format: bool = False,
    expect_format_preserves_m1_m4_camset: bool = False,
    simulated_slot1_vault_delete_events: int = 0,
    # Check Group D (Wave 47 §4 + Tier-0 — Reset Network Set., Post-Reboot Airplane On & Tier-0)
    reset_network_set_executed: bool = True,
    auto_reboot_triggered_on_network_reset: bool = True,
    reset_nw_shutdown_bkid: str = P279_RESET_NW_SHUTDOWN_BKID,
    reset_nw_autoreboot_prompt_resid16_hex: str = P279_RESET_NW_AUTOREBOOT_PROMPT_RESID16_HEX,
    wifi_psks_cleared: bool = True,
    bt_pairings_cleared: bool = True,
    ftp_cloud_certs_cleared: bool = True,
    streaming_rtmp_srt_cleared: bool = True,
    network_reset_resets_airplane_to_off: bool = True,
    network_reset_preserves_shooting_setup_playback_camset: bool = True,
    camera_reset_resets_shooting_and_framing_hdmi: bool = True,
    camera_reset_preserves_network_setup_playback_camset: bool = True,
    initialize_clears_all_except_card_m1_m4: bool = True,
    post_reboot_airplane_mode: str = "ON",
    airplane_mode_on_resid16_hex: str = P279_AIRPLANE_MODE_ON_RESID16_HEX,
    require_post_reboot_airplane_on: bool = True,
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
) -> RealHwUsbModeHdmiInfoProtectNetworkResetReport:
    """Execute Phase 279 read-only 8th physical bench readiness verifier (`A..D`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase279_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_p279_check_group_a_usb_connection_mode(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        usb_conn_bkid=usb_conn_bkid,
        usb_conn_resid16_hex=usb_conn_resid16_hex,
        exposed_usb_modes=exposed_usb_modes,
        usb_connection_mode=usb_connection_mode,
        expect_usb_streaming_uvc=expect_usb_streaming_uvc,
        usb_streaming_exposed_in_fx3_ui=usb_streaming_exposed_in_fx3_ui,
        dormant_uvc_kmod_name=dormant_uvc_kmod_name,
        dormant_uvc_kmod_bytes=dormant_uvc_kmod_bytes,
        dormant_uvc_kmod_insmodded=dormant_uvc_kmod_insmodded,
        air_gapped_bench=air_gapped_bench,
        usb_data_lines_physically_isolated=usb_data_lines_physically_isolated,
        host_usb_data_enumeration_active=host_usb_data_enumeration_active,
        usb_lun_setting=usb_lun_setting,
        usb_power_supply=usb_power_supply,
        power_source=power_source,
        usb_power_terminal=usb_power_terminal,
        np_fz100_battery_inserted=np_fz100_battery_inserted,
        claimed_usb_setup_reset_on_camera_reset=claimed_usb_setup_reset_on_camera_reset,
        claimed_usb_setup_reset_on_network_reset=claimed_usb_setup_reset_on_network_reset,
        claimed_usb_setup_survives_initialize=claimed_usb_setup_survives_initialize,
    )
    gb = evaluate_p279_check_group_b_hdmi_info_and_clean_feed(
        hdmi_info_bkid=hdmi_info_bkid,
        hdmi_info_resid16_hex=hdmi_info_resid16_hex,
        hdmi_info_display=hdmi_info_display,
        require_clean_hdmi_feed=require_clean_hdmi_feed,
        require_unblanked_lcd=require_unblanked_lcd,
        allow_lcd_blanking_and_osd=allow_lcd_blanking_and_osd,
        expect_touch_focus_active_when_hdmi_info_on=expect_touch_focus_active_when_hdmi_info_on,
        expect_full_raster_clean_feed_when_hdmi_info_on=expect_full_raster_clean_feed_when_hdmi_info_on,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        hdmi_raw_output=hdmi_raw_output,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        hdmi_output_resolution=hdmi_output_resolution,
        expect_4k_hdmi_during_internal_log_or_pplut=expect_4k_hdmi_during_internal_log_or_pplut,
        expect_hdmi_info_on_during_raw_or_hdmi_only=expect_hdmi_info_on_during_raw_or_hdmi_only,
        expect_sq_allows_hdmi_only_or_raw=expect_sq_allows_hdmi_only_or_raw,
        reset_action=reset_action,
        claimed_hdmi_setup_reset_on_camera_reset=claimed_hdmi_setup_reset_on_camera_reset,
        claimed_hdmi_setup_reset_on_network_reset=claimed_hdmi_setup_reset_on_network_reset,
        claimed_framing_settings_hdmi_survives_camera_reset=claimed_framing_settings_hdmi_survives_camera_reset,
    )
    gc = evaluate_p279_check_group_c_protect_vs_format_slot1(
        protect_exposed_scopes=protect_exposed_scopes,
        protect_scope_selected=protect_scope_selected,
        protected_items_block_delete=protected_items_block_delete,
        expect_copy_preserves_protect=expect_copy_preserves_protect,
        expect_movie_key_mark_without_menu=expect_movie_key_mark_without_menu,
        format_resid16_hex=format_resid16_hex,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        slot1_wp_error_status=slot1_wp_error_status,
        slot1_format_hard_locked=slot1_format_hard_locked,
        slot1_vault_write_firewall_enforced=slot1_vault_write_firewall_enforced,
        slot1_format_mode=slot1_format_mode,
        slot1_delete_requested=slot1_delete_requested,
        expect_protect_blocks_format=expect_protect_blocks_format,
        expect_format_preserves_m1_m4_camset=expect_format_preserves_m1_m4_camset,
        simulated_slot1_vault_delete_events=simulated_slot1_vault_delete_events,
    )
    gd, tier0_errors = evaluate_p279_check_group_d_reset_network_zero_rf_and_tier0(
        reset_network_set_executed=reset_network_set_executed,
        auto_reboot_triggered_on_network_reset=auto_reboot_triggered_on_network_reset,
        reset_nw_shutdown_bkid=reset_nw_shutdown_bkid,
        reset_nw_autoreboot_prompt_resid16_hex=reset_nw_autoreboot_prompt_resid16_hex,
        wifi_psks_cleared=wifi_psks_cleared,
        bt_pairings_cleared=bt_pairings_cleared,
        ftp_cloud_certs_cleared=ftp_cloud_certs_cleared,
        streaming_rtmp_srt_cleared=streaming_rtmp_srt_cleared,
        network_reset_resets_airplane_to_off=network_reset_resets_airplane_to_off,
        network_reset_preserves_shooting_setup_playback_camset=network_reset_preserves_shooting_setup_playback_camset,
        camera_reset_resets_shooting_and_framing_hdmi=camera_reset_resets_shooting_and_framing_hdmi,
        camera_reset_preserves_network_setup_playback_camset=camera_reset_preserves_network_setup_playback_camset,
        initialize_clears_all_except_card_m1_m4=initialize_clears_all_except_card_m1_m4,
        post_reboot_airplane_mode=post_reboot_airplane_mode,
        airplane_mode_on_resid16_hex=airplane_mode_on_resid16_hex,
        require_post_reboot_airplane_on=require_post_reboot_airplane_on,
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
            "Enforce stock FX3 4-mode [USB Connection Mode] (NOUVC dormant usb_f_uvc.ko masked), block MSC/MTP/Remote/USB-LAN enumeration, and permit Type-C [USB Power Supply]=On + NP-FZ100 ONLY with physically isolated USB data lines."
        )
    if not gb.passed:
        remediations.append(
            "Set [HDMI Info. Display]=Off for unblanked LCD/touch-focus + clean feed, honor 1080 clamp under internal Rec + Log/PPLUT1..4 vs Off(HDMI Only)/RAW 4K forced-Off, and preserve (Setup) across [Camera Settings Reset]."
        )
    if not gc.passed:
        remediations.append(
            "Enforce dual-layer Slot-1 defense: physical SD WP switch (MR_MEMORY_ERROR_CARD_WRITE_PROTECT_SLOT1) + slot1_format_hard_locked=True, because [Format] (0xe449) wipes [Protect] files and M1..M4 card settings."
        )
    if not gd.passed or not gd.tier0_receipt_verified:
        remediations.append(
            "Verify [Reset Network Set.] 3-way reset boundary & mandatory auto-reboot (0x65d3), re-enable [Airplane Mode]=On (0x6df9) post-reboot (passive_tx=0), keep 16/16 H0==H3, and provide dual-device 528B FX3RCPT1 Tier-0 receipts."
        )

    if not all_4_passed:
        verdict = P279_GO_NO_GO_BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_FAILURE
        overall_status = verdict
    elif not gd.tier0_receipt_verified:
        if not gd.tier0_receipt_present:
            verdict = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            overall_status = P279_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        else:
            verdict = P279_GO_NO_GO_BLOCKED_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_FAILURE
            overall_status = verdict
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED
        overall_status = P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED

    provisional = RealHwUsbModeHdmiInfoProtectNetworkResetReport(
        schema=PHASE_279_SCHEMA,
        phase_version=PHASE_279_VERSION,
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
        usb_streaming_exposed_in_fx3_ui=ga.usb_streaming_exposed_in_fx3_ui,
        usb_packets_transmitted=PHASE279_USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHASE279_USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=PHASE279_RAW_FIRMWARE_BYTES_LEAKED,
        passive_tx_bytes_emitted=gd.passive_tx_bytes_emitted,
        slot1_wp_locked=gc.slot1_wp_locked,
        slot1_format_hard_locked=gc.slot1_format_hard_locked,
        slot1_vault_delete_events=gc.slot1_vault_delete_events,
        check_group_count=4,
        check_groups_passed=groups_passed,
        all_4_check_groups_passed=all_4_passed,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_usb_connection_mode=ga,
        check_group_b_hdmi_info_clean_feed=gb,
        check_group_c_protect_vs_format_slot1=gc,
        check_group_d_reset_network_zero_rf_tier0=gd,
        warnings=gd.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwUsbModeHdmiInfoProtectNetworkResetReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_usb_connection_mode": ga,
            "check_group_b_hdmi_info_clean_feed": gb,
            "check_group_c_protect_vs_format_slot1": gc,
            "check_group_d_reset_network_zero_rf_tier0": gd,
            "warnings": gd.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_usb_mode_hdmi_info_protect_and_network_reset_preflight = (
    evaluate_realhw_usb_mode_hdmi_info_protect_and_network_reset_readiness
)


def verify_phase279_report(payload: Mapping[str, Any]) -> Phase279ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 279 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_279_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_279_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_279_VALID_GO_NO_GO_VALUES:
        errors.append(f"Invalid go_no_go verdict: {payload.get('go_no_go')!r}")

    for lock_key in (
        "overall_ready_for_hardware_attach",
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
        "usb_streaming_exposed_in_fx3_ui",
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

    if payload.get("go_no_go") in (
        GO_NO_GO_DRY_RUN_SIMULATED_READY,
        P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED,
    ):
        if payload.get("slot1_vault_delete_events") != 0:
            errors.append("Pass/dry-run verdict requires slot1_vault_delete_events==0")
        if payload.get("slot1_wp_locked") is not True:
            errors.append("Pass/dry-run verdict requires slot1_wp_locked==True")
        if payload.get("slot1_format_hard_locked") is not True:
            errors.append("Pass/dry-run verdict requires slot1_format_hard_locked==True")

    if payload.get("go_no_go") == GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT and (
        payload.get("overall_status") != P279_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    ):
        errors.append(
            "Offline awaiting-receipt verdict must carry overall_status=READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
        )

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go")
        == P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == P279_GO_NO_GO_USB_MODE_HDMI_INFO_PROTECT_NETWORK_RESET_VERIFIED and (
        payload.get("all_4_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 4 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase279ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase279_markdown(report: RealHwUsbModeHdmiInfoProtectNetworkResetReport) -> str:
    """Render concise deterministic Markdown summary for Phase 279 physical bench preflight."""
    ga = report.check_group_a_usb_connection_mode
    gb = report.check_group_b_hdmi_info_clean_feed
    gc = report.check_group_c_protect_vs_format_slot1
    gd = report.check_group_d_reset_network_zero_rf_tier0
    lines = [
        f"# Phase 279 8th Physical Bench Readiness (`{report.schema}`)",
        "",
        f"- **OVERALL**: `{report.overall_status}` (`go_no_go={report.go_no_go}`, mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `ready_attach={report.overall_ready_for_hardware_attach}`, `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `spi_nor={report.spi_nor_write_authorized}`, `el3_tx={report.el3_payload_transmit_authorized}`, `usb_pkts={report.usb_packets_transmitted}`, `passive_tx={report.passive_tx_bytes_emitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | Mode=`{ga.usb_connection_mode}` (`{len(ga.exposed_usb_modes)}` stock, NOUVC=`{not ga.usb_streaming_exposed_in_fx3_ui}`), LUN=`{ga.usb_lun_setting}`, USB_PD=`{ga.usb_power_supply}` (`{ga.usb_power_terminal}`+NP-FZ100=`{ga.np_fz100_battery_inserted}`, data_iso=`{ga.usb_data_lines_physically_isolated}`) |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | HDMI_Info=`{gb.effective_hdmi_info_display}` (clean_feed=`{gb.clean_hdmi_feed_active}`, lcd_blanked=`{gb.built_in_lcd_blanked}`), Out=`{gb.effective_hdmi_output_resolution}` (clamped_1080=`{gb.hdmi_clamped_to_1080_by_log_or_pplut}`), ResetSurvives=`{gb.hdmi_setup_survives_camera_and_network_reset}` |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | ProtectScopes=`{len(gc.protect_four_scopes)}` (`{gc.protect_scope_selected}`), FormatOverridesProtect=`{gc.format_overrides_protect_and_m1_m4_verified}`, Slot1_WP=`{gc.slot1_wp_locked}`, FormatHardLocked=`{gc.slot1_format_hard_locked}`, DelEvents=`{gc.slot1_vault_delete_events}` |",
        f"| `{gd.check_group_id}` | `{'PASS' if gd.passed else 'FAIL'}` | ResetNW_AutoReboot=`{gd.auto_reboot_triggered_on_network_reset}` (`{gd.reset_nw_autoreboot_prompt_resid16_hex}`), 3WayBoundary=`{gd.three_way_reset_boundary_verified}`, PostRebootAirplane=`{gd.post_reboot_airplane_mode}`, ZeroRF=`{gd.zero_rf_bench_authorized}`, Tier0=`{gd.tier0_receipt_verified}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
