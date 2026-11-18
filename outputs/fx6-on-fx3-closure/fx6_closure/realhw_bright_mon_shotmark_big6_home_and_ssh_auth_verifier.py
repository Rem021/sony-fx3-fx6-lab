"""Phase 316 — 13th Real-Hardware Physical Bench Readiness Verifier (`preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth`).

Dedicated host-side read-only 13th physical bench & pre-shoot readiness verifier for Sony
`ILME-FX3` (`Ver. 7.02`, `ilc/2210`, Model `0x91030080`) vs `ILME-FX6` (`Ver. 6.01`),
extending the 13-stage operator bench preflight series (`preflight-card-insert` ->
`preflight-bench-cable-fan-slot1` -> `preflight-hdmi-proxy-desqueeze-and-simult` ->
`preflight-pixelmap-ntscpal-powersave-and-autotemp` ->
`preflight-imagedb-touch-shoeaudio-and-lockop` ->
`preflight-diffset-customkey-autoslow-and-apsc` ->
`preflight-file-settings-gamma-assist-focus-mag-and-videolight` ->
`preflight-usb-mode-hdmi-info-protect-and-network-reset` ->
`preflight-pp-scinetone-wb-metering-and-shutter-type` ->
`preflight-focus-area-zoom-dci4k-and-sensor-cleaning` ->
`preflight-lens-comp-af-illuminator-copy-slot-and-evf-absence` ->
`preflight-dial-customize-lut-embed-steadyshot-and-streaming` ->
`preflight-bright-monitoring-shot-mark-big6-home-and-ssh-auth`) by synthesizing Waves
58-59 official Sony `ILME-FX3` Help Guide (`ilc/2210`), `appFw.so`, `BK4`, and `.uxc`
hardware boundaries into 4 deterministic fail-closed check groups (`A..D`), bounded
`O_RDONLY` donor inspection (`< 0.15s`), `16/16 H0 == H3` baseline invariance, and
dual-media `528 B FX3RCPT1` Tier-0 receipt gating:

1. **Check Group A (`GROUP_A_BRIGHT_MONITORING_LCD_SUNNY_SHOTMARK_AND_DORMANT_EDIT_BULB_HDR` — Wave 58 §§1,2,4)**:
   - Custom-key-only `[Bright Monitoring]` (`_f 0x701f`, forces `[Live View Display] =
     Setting Effect OFF`, requires `P/A/S/M + MF`, auto-cancels on power off, Ver. 7.00+
     coexists with `[Focus Magnifier]` / `[Auto Magnifier in MF]`), Initialize-only
     `[Monitor Brightness]` (`Manual -2..+2` default `0` / `Sunny Weather`, dormant
     `AUTO/BRIGHT/NORMAL` rejected `EOPNOTSUPP=95`) vs `FX6` `VF Setting > Brightness
     1..15` & AE `Backlight` disambiguation.
   - Zero in-camera `[Divide]`/`[Extract]` & dormant FTP 15/30/60s cut (`EOPNOTSUPP=95`);
     `[Shot Mark 1/2]` (`*M01.XML` + `AVF_INFO`), Ver. 7.00+ `[Clip Flag]` (`OK/NG/KEEP`),
     Playback `[Photo Capture]`/`[Rotate]`/`[Copy]`, and Custom-Key `[Create Divider Frame]`
     card-write paths fail-closed (`EROFS=30`/`EBUSY=16`) on `Slot-1` Tier-0 Vault
     (`slot1_data_sector_writes == 0`).
   - Mechanical-shutter-only Still `[BULB]` (clamped to `30"` in Electronic Shutter / Cont /
     Interval, disables Anti-flicker) + active `DRO` / `DRO Bracket` vs dormant
     `[Bulb Timer]` (`_f 0x630f`) and dormant `[Auto HDR]` (`0xe49d`) rejected
     `EOPNOTSUPP=95`.

2. **Check Group B (`GROUP_B_ZERO_BT_TCLINK_WPA3_USBLAN_AND_AIRPLANE_ZERO_RF` — Wave 58 §3)**:
   - Zero Bluetooth `[Timecode Link]` (`0` `tc_link`/`UltraSync` hits -> `EOPNOTSUPP=95`),
     wired `VMC-BNCM1` LTC (`Preset + Free Run` -> `EXT-LK`) vs `FX6` physical BNC
     `TC IN/OUT` switch & zero-BT `FX6`.
   - Dual-SKU Wi-Fi (`WW728473` `2.4/5GHz` indoor `5GHz` W52 `0x6953` vs `WW558244`
     `2.4GHz`), Ver. 7.00+ removal of `WEP`/`WPA-PSK`/`IPsec` (`EOPNOTSUPP=95`, enforcing
     `WPA2-PSK`/`WPA3-SAE`), USB-C `USB-LAN` (`cdc_ncm.ko`/`r8152.ko`/`asix.ko`,
     `[USB-LAN Cnct. Launch]` `0x7d2a`, mutually exclusive with Multi/Micro USB & Wi-Fi),
     and mandatory physical bench Zero-RF lock (`[Airplane Mode] = On`, persisting across
     `Reset Network Set.` & `Initialize`, `wireless_rf_packets_emitted == 0`).

3. **Check Group C (`GROUP_C_BIG6_HOME_FIXED_VAR_MANUAL_ND_FRAMING_AND_INTERVAL_9999_VAULT` — Wave 59 §§1-2)**:
   - Ver. 7.00+ `HOME` (`BIG6`) screen gated on `[Mode Settings] = Fixed/Variable`
     (`_f 0x7d0d`), 6 dynamic tiles (`FPS`, `ISO / Base ISO·EI`, `Shutter Speed/Angle`,
     `Aperture / Manual ND Filter` metadata — **zero physical e-ND actuator**
     `e_nd_actuator_tx_count == 0` vs real `FX6` `e-ND`!, `PP / Select LUT`, `WB`).
   - Active manual `[Framing Settings]` (`_f 0x7d18`, independent `Recording/Streaming =
     Full/Crop` vs `HDMI = Crop/Full`, disables `APS-C S35`, locked at `100p/120p` or
     active rec/stream) vs **DORMANT AI `[Auto Framing]`**
     (`TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY` -> `EOPNOTSUPP=95`).
   - Still `[Interval Shoot Func.]` (`_f 0x7027`, 7 resettable params, up to `9,999` shots /
     `19,998` `RAW+JPEG/HEIF` files + `AVF_INFO` burst writes -> fail-closed `EROFS=30` on
     `Slot-1` Tier-0 Vault!) vs `FX6` single-MXF `Interval Rec`.

4. **Check Group D (`GROUP_D_TC_REGENERATE_HDMI_REC_CTRL_SSH_AUTH_AND_ZERO_FAN_MAX` — Wave 59 §§3-4 & Tier-0)**:
   - `[Time Code Make] = Regenerate` forces `Rec Run` (deterministically reads `Slot 1` on
     `Simult. Recording`, cannot coexist with `VMC-BNCM1 EXT-LK`); HDMI `[REC Control]`
     gated on `[Time Code Output] = On` (works in both `Rec. Media dur HDMI Output = On`
     and `Off(HDMI Only)`), `[4ch Audio Output]` (`CH1/CH2` vs `CH3/CH4`) vs `FX6` `Clock`
     TC & `SDI/HDMI Remote I/F` vs `Parallel Rec`.
   - Ver. 7.00+ `[Access Authen.]` uses **SSH** (`MSGID_SSHD_START_CMD` / `sshd_start` +
     host key fingerprint `_g 0x610b`, `0` hits for `HTTPS`/`HTTP_DIGEST`/`BASIC_AUTH` ->
     `EOPNOTSUPP=95`; `[Import Root Certificate]` `_f 0x7940` applies to outbound client
     `FTPS`/`RTMPS`/`Cloud` TLS only).
   - **Thermal Fan Myth-Bust**: NEITHER `FX3` (`Auto`/`Minimum`/`Off in Rec`/`Always Off`)
     NOR `FX6` (`Auto`/`Minimum`/`Off in Rec`, `Always Off` dormant) has `Fan Control = Max`
     (`FAN_CONTROL_MAX = 0` hits -> `EINVAL=22` / `EOPNOTSUPP=95`), plus
     `[Auto Power OFF Temp.]` (`Standard` / `High` tripod thermal guard), `16/16 H0 == H3`,
     dual-device `528 B FX3RCPT1` Tier-0 receipt gating, and unconditional safety redlines.

Hard-Locked Safety Invariants (UNCONDITIONAL):
- `overall_ready_for_hardware_attach = False`
- `hardware_live_attachment_authorized = False`
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `spi_nor_write_authorized = False`
- `el3_payload_transmit_authorized = False`
- `sd_physical_media_written = False`
- `cross_model_flash_authorized = False`
- `slot1_tier0_vault_mutated = False`
- `rf_nvs_p12_p13_writes_authorized = False`
- `fx3_bt_tc_link_present = False`
- `fx3_auto_framing_present = False`
- `fx3_bulb_timer_present = False`
- `fx3_auto_hdr_present = False`
- `fx3_in_camera_divide_extract_present = False`
- `fx3_physical_e_nd_present = False`
- `fx3_fan_control_max_present = False`
- `fx6_fan_control_max_present = False`
- `e_nd_actuator_tx_count = 0`
- `wireless_rf_packets_emitted = 0` (`rf_packets_transmitted = 0`)
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
# Schema, Verdicts & Non-Shadowing P316_* Domain Constants
# ---------------------------------------------------------------------------

PHASE_316_SCHEMA: str = "realhw_preflight13_bright_mon_shotmark_big6_ssh_v1"
P316_SCHEMA: str = PHASE_316_SCHEMA
P316_SCHEMA_VERSION: str = PHASE_316_SCHEMA
REALHW_BRIGHT_MON_SHOTMARK_BIG6_HOME_SSH_AUTH_SCHEMA: str = PHASE_316_SCHEMA
PHASE_316_VERSION: str = "316.0.0"
P316_VERSION: str = PHASE_316_VERSION
P316_SONY_HELP_GUIDE_ID: str = "ilc/2210"

P316_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS: str = (
    "READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
)
P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED: str = (
    "GO_BRIGHT_MON_SHOTMARK_BIG6_HOME_SSH_AUTH_READONLY_PREFLIGHT_VERIFIED"
)
P316_GO_NO_GO_BLOCKED_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_FAILURE: str = (
    "BLOCKED_BRIGHT_MON_SHOTMARK_BIG6_HOME_SSH_AUTH_CHECK_FAILURE"
)
PHASE_316_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    P316_GO_NO_GO_BLOCKED_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED,
)

P316_CHECK_GROUP_A_ID: str = (
    "GROUP_A_BRIGHT_MONITORING_LCD_SUNNY_SHOTMARK_AND_DORMANT_EDIT_BULB_HDR"
)
P316_CHECK_GROUP_B_ID: str = (
    "GROUP_B_ZERO_BT_TCLINK_WPA3_USBLAN_AND_AIRPLANE_ZERO_RF"
)
P316_CHECK_GROUP_C_ID: str = (
    "GROUP_C_BIG6_HOME_FIXED_VAR_MANUAL_ND_FRAMING_AND_INTERVAL_9999_VAULT"
)
P316_CHECK_GROUP_D_ID: str = (
    "GROUP_D_TC_REGENERATE_HDMI_REC_CTRL_SSH_AUTH_AND_ZERO_FAN_MAX"
)
PHASE_316_CHECK_GROUP_IDS: Tuple[str, ...] = (
    P316_CHECK_GROUP_A_ID,
    P316_CHECK_GROUP_B_ID,
    P316_CHECK_GROUP_C_ID,
    P316_CHECK_GROUP_D_ID,
)

PHASE316_RAW_FIRMWARE_BYTES_LEAKED: int = 0
PHASE316_PASSIVE_TX_BYTES_EMITTED: int = 0
PHASE316_USB_PACKETS_TRANSMITTED: int = 0
PHASE316_WIRELESS_RF_PACKETS_EMITTED: int = 0
PHASE316_SLOT1_DATA_SECTOR_WRITES: int = 0
PHASE316_E_ND_ACTUATOR_TX_COUNT: int = 0

P316_ERRNO_EBUSY: int = 16
P316_ERRNO_EINVAL: int = 22
P316_ERRNO_EROFS: int = 30
P316_ERRNO_EOPNOTSUPP: int = 95

P316_VALID_SHOOT_MODES: Tuple[str, ...] = ("PHOTO", "MOVIE", "S_AND_Q")
P316_VALID_RESET_ACTIONS: Tuple[str, ...] = (
    "NONE",
    "CAMERA_SETTINGS_RESET",
    "RESET_NETWORK_SET",
    "INITIALIZE",
)
P316_VALID_ON_OFF: Tuple[str, ...] = ("ON", "OFF")
P316_PASM_EXPOSURE_MODES: Tuple[str, ...] = (
    "PROGRAM_AUTO",
    "APERTURE_PRIORITY",
    "SHUTTER_PRIORITY",
    "MANUAL_EXPOSURE",
)
P316_VALID_EXPOSURE_MODES: Tuple[str, ...] = P316_PASM_EXPOSURE_MODES + (
    "INTELLIGENT_AUTO",
    "FLEXIBLE_EXP",
)
P316_VALID_FOCUS_MODES: Tuple[str, ...] = ("AF_S", "AF_A", "AF_C", "DMF", "MF")

# Check Group A Constants (Wave 58 §§1,2,4)
P316_BRIGHT_MONITORING_RESID16_HEX: str = "0x701f"
P316_MONITOR_BRIGHTNESS_BASE_RESID16_HEX: str = "0xe44b"
P316_SUNNY_WEATHER_BASE_RESID16_HEX: str = "0xe1da"
P316_VALID_MONITOR_BRIGHTNESS_MODES: Tuple[str, ...] = ("MANUAL", "SUNNY_WEATHER")
P316_DORMANT_LCD_BRIGHTNESS_MODES: Tuple[str, ...] = ("AUTO", "BRIGHT", "NORMAL")
P316_MONITOR_BRIGHTNESS_MIN: int = -2
P316_MONITOR_BRIGHTNESS_MAX: int = 2

P316_DORMANT_FTP_CUT_RESIDS: Tuple[str, ...] = ("0x7005", "0x6e38", "0x6c2a", "0x74a9")
P316_SHOT_MARK_REC_RESIDS: Tuple[str, ...] = ("0x628b", "0x628a")
P316_SHOT_MARK_PB_RESIDS: Tuple[str, ...] = ("0x6143", "0x6142")
P316_PHOTO_CAPTURE_RESID16_HEX: str = "0x6856"
P316_JPEG_HEIF_SWITCH_RESID16_HEX: str = "0x7175"
P316_CREATE_DIVIDER_FRAME_RESID16_HEX: str = "0x747a"
P316_VALID_CLIP_FLAGS: Tuple[str, ...] = ("NONE", "OK", "NG", "KEEP")
P316_VALID_SHUTTER_TYPES: Tuple[str, ...] = ("MECHANICAL_SHUTTER", "ELECTRONIC_SHUTTER")
P316_VALID_STILL_DRIVE_MODES: Tuple[str, ...] = (
    "SINGLE_SHOOTING",
    "CONT_HI_PLUS",
    "CONT_HI",
    "CONT_MID",
    "CONT_LO",
    "SELF_TIMER_SINGLE",
    "SELF_TIMER_CONT",
    "BRACKET",
    "INTERVAL",
)
P316_BULB_BASE_RESID16_HEX: str = "0xe916"
P316_DORMANT_BULB_TIMER_RESID16_HEX: str = "0x630f"
P316_DORMANT_AUTO_HDR_RESID16_HEX: str = "0xe49d"
P316_VALID_DRO_MODES: Tuple[str, ...] = (
    "OFF",
    "AUTO",
    "LV1",
    "LV2",
    "LV3",
    "LV4",
    "LV5",
)
P316_VALID_DRO_BRACKET_MODES: Tuple[str, ...] = (
    "OFF",
    "DRO_BRK_LO_1",
    "DRO_BRK_LO_2",
    "DRO_BRK_LO_3",
    "DRO_BRK_HI_1",
    "DRO_BRK_HI_3",
    "DRO_BRK_HI_5",
)

# Check Group B Constants (Wave 58 §3)
P316_VMC_BNCM1_PART_NUMBER: str = "VMC-BNCM1"
P316_VMC_BNCM1_ACCESSORY_CODE: str = "A-5051-506-A"
P316_INDOOR_5GHZ_RESID16_HEX: str = "0x6953"
P316_USB_LAN_CNCT_LAUNCH_RESID16_HEX: str = "0x7d2a"
P316_VALID_WIFI_SKUS: Tuple[str, ...] = ("NONE", "WW728473", "WW558244")
P316_VALID_WIFI_SECURITY_PROTOCOLS: Tuple[str, ...] = (
    "NONE",
    "WPA2_PSK",
    "WPA3_SAE",
)
P316_REMOVED_LEGACY_WIFI_PROTOCOLS: Tuple[str, ...] = (
    "WEP",
    "WPA_PSK",
    "IPSEC",
)
P316_VALID_NETWORK_TRANSPORTS: Tuple[str, ...] = (
    "NONE",
    "USB_LAN",
    "WIRELESS_RF",
)
P316_USB_LAN_KERNEL_MODULES: Tuple[str, ...] = (
    "cdc_ncm.ko",
    "r8152.ko",
    "asix.ko",
    "ax88179_178a.ko",
    "cdc_ether.ko",
    "usbnet.ko",
    "ipheth.ko",
    "rndis_host.ko",
)

# Check Group C Constants (Wave 59 §§1-2)
P316_MODE_SETTINGS_RESID16_HEX: str = "0x7d0d"
P316_HOME_KEY_RESIDS: Tuple[str, ...] = ("0x7cad", "0x7cb1")
P316_SWIPE_DOWN_RESID16_HEX: str = "0x7cdd"
P316_HOME_LOWER_LEFT_RESID16_HEX: str = "0x7ce3"
P316_FRAMING_SETTINGS_RESID16_HEX: str = "0x7d18"
P316_FRAMING_SUPPORT_ENUM: str = "TYPE_EFRAMING_SUPPORT_TYPE_MANUAL_ONLY"
P316_DORMANT_AUTO_FRAMING_RESIDS: Tuple[str, ...] = (
    "0x6be6",
    "0x79bc",
    "0x6c9d",
    "0x69cc",
    "0x7566",
)
P316_INTERVAL_SHOOT_FUNC_RESID16_HEX: str = "0x7027"
P316_VALID_MODE_SETTINGS: Tuple[str, ...] = ("FIXED_VARIABLE", "LEGACY")
P316_VALID_HOME_TRIGGERS: Tuple[str, ...] = ("NONE", "CUSTOM_KEY_HOME", "SWIPE_DOWN")
P316_VALID_HOME_LOWER_LEFT_MODES: Tuple[str, ...] = ("APERTURE", "ND_FILTER")
P316_BIG6_SIX_TILES: Tuple[str, ...] = (
    "FPS",
    "ISO_OR_BASE_ISO_EI",
    "SHUTTER_SPEED_OR_ANGLE",
    "APERTURE_OR_MANUAL_ND",
    "PP_OR_SELECT_LUT",
    "WB",
)
P316_VALID_FRAMING_AREAS: Tuple[str, ...] = ("FULL", "CROP")
P316_INTERVAL_SHOOT_7_PARAMS: Tuple[str, ...] = (
    "INTERVAL_SHOOTING",
    "SHOOTING_START_TIME",
    "SHOOTING_INTERVAL",
    "NUMBER_OF_SHOTS",
    "AE_TRACKING_SENSITIVITY",
    "SHUTTER_TYPE_IN_INTERVAL",
    "SHOOT_INTERVAL_PRIORITY",
)
P316_INTERVAL_MAX_SHOTS: int = 9999
P316_INTERVAL_MAX_FILES_RAW_JH: int = 19998
P316_INTERVAL_START_MAX_SEC: int = 5999
P316_INTERVAL_SEC_MAX: int = 60
P316_VALID_INTERVAL_AE_TRACKING: Tuple[str, ...] = ("HIGH", "MID", "LOW")
P316_VALID_INTERVAL_SHUTTER_TYPES: Tuple[str, ...] = ("MECHANICAL", "ELECTRONIC")

# Check Group D Constants (Wave 59 §§3-4)
P316_VALID_TC_MAKE_MODES: Tuple[str, ...] = ("PRESET", "REGENERATE")
P316_VALID_TC_RUN_MODES: Tuple[str, ...] = ("FREE_RUN", "REC_RUN")
P316_VALID_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = ("ON", "OFF", "OFF_HDMI_ONLY")
P316_VALID_4CH_AUDIO_OUTPUT_MODES: Tuple[str, ...] = ("CH1_CH2", "CH3_CH4")
P316_SSHD_HOSTKEY_FINGERPRINT_RESID16_HEX: str = "0x610b"
P316_IMPORT_ROOT_CERT_RESID16_HEX: str = "0x7940"
P316_VALID_ACCESS_AUTHEN_PROTOCOLS: Tuple[str, ...] = ("SSH",)
P316_DORMANT_HTTP_AUTH_PROTOCOLS: Tuple[str, ...] = (
    "HTTPS",
    "HTTP_DIGEST",
    "BASIC_AUTH",
)
P316_FX3_VALID_4_FAN_MODES: Tuple[str, ...] = (
    "AUTO",
    "MINIMUM",
    "OFF_IN_REC",
    "ALWAYS_OFF",
)
P316_FX6_VALID_3_FAN_MODES: Tuple[str, ...] = (
    "AUTO",
    "MINIMUM",
    "OFF_IN_REC",
)
P316_VALID_AUTO_POWER_OFF_TEMPS: Tuple[str, ...] = ("STANDARD", "HIGH")

# Deterministic Error Codes
P316_GA_ERR_MODEL_OR_FW_FLOOR: str = "P316_GA_ERR_MODEL_OR_FW_FLOOR"
P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST: str = (
    "P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST_EOPNOTSUPP_95"
)
P316_GA_ERR_MONITOR_BRIGHTNESS_SUNNY_OR_FX6_BACKLIGHT_CONFUSION: str = (
    "P316_GA_ERR_MONITOR_BRIGHTNESS_SUNNY_OR_FX6_BACKLIGHT_CONFUSION_EOPNOTSUPP_95"
)
P316_GA_ERR_DORMANT_DIVIDE_EXTRACT_FTPCUT_OR_SLOT1_VAULT_WRITE: str = (
    "P316_GA_ERR_DORMANT_DIVIDE_EXTRACT_FTPCUT_OR_SLOT1_VAULT_WRITE_EROFS_30"
)
P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR: str = (
    "P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR_EOPNOTSUPP_95"
)

P316_GB_ERR_DORMANT_BT_TC_LINK_OR_VMC_BNCM1_EXT_LK_PREREQ: str = (
    "P316_GB_ERR_DORMANT_BT_TC_LINK_OR_VMC_BNCM1_EXT_LK_PREREQ_EOPNOTSUPP_95"
)
P316_GB_ERR_WIFI_SKU_OR_REMOVED_WEP_WPA_IPSEC: str = (
    "P316_GB_ERR_WIFI_SKU_OR_REMOVED_WEP_WPA_IPSEC_EOPNOTSUPP_95"
)
P316_GB_ERR_USBLAN_MUTUAL_EXCLUSION_OR_KMOD_MISMATCH: str = (
    "P316_GB_ERR_USBLAN_MUTUAL_EXCLUSION_OR_KMOD_MISMATCH"
)
P316_GB_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL: str = (
    "P316_GB_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL_EROFS_30"
)

P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION: str = (
    "P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION_EOPNOTSUPP_95"
)
P316_GC_ERR_MANUAL_FRAMING_LOCK_OR_DORMANT_AI_AUTO_FRAMING: str = (
    "P316_GC_ERR_MANUAL_FRAMING_LOCK_OR_DORMANT_AI_AUTO_FRAMING_EOPNOTSUPP_95"
)
P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL: str = (
    "P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL_EROFS_30"
)

P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO: str = (
    "P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO"
)
P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH: str = (
    "P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH_EOPNOTSUPP_95"
)
P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD: str = (
    "P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD_EINVAL_22_EOPNOTSUPP_95"
)
P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)
P316_GD_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "P316_GD_ERR_H0_H3_IMMUTABILITY_DRIFT"
P316_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION: str = (
    "P316_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION"
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


# ---------------------------------------------------------------------------
# Frozen Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase316DonorInspectionResult:
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
class P316CheckGroupABrightMonitoringLcdShotMarkResult:
    check_group_id: str
    passed: bool
    sony_help_guide_id: str
    bright_monitoring_active: bool
    bright_monitoring_custom_key_only: bool
    bright_monitoring_focus_mag_coexist: bool
    live_view_display: str
    monitor_brightness_mode: str
    monitor_brightness_level: int
    dormant_lcd_brightness_rejected: bool
    dormant_divide_extract_ftp_cut_rejected: bool
    clip_flag: str
    bulb_enabled: bool
    dro_mode: str
    dro_bracket_mode: str
    fx3_bulb_timer_present: bool
    fx3_auto_hdr_present: bool
    fx3_in_camera_divide_extract_present: bool
    slot1_vault_firewall_enforced: bool
    slot1_data_sector_writes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P316CheckGroupBZeroBtTcLinkWifiUsbLanAirplaneResult:
    check_group_id: str
    passed: bool
    fx3_bt_tc_link_present: bool
    dormant_bt_tc_link_rejected: bool
    vmc_bncm1_ext_lk_active: bool
    wifi_sku: str
    wifi_security_protocol: str
    dormant_legacy_wifi_sec_rejected: bool
    usb_lan_cnct_launch: str
    usb_lan_kernel_module_count: int
    network_transport: str
    airplane_mode: str
    zero_rf_airplane_firewall_enforced: bool
    wireless_rf_packets_emitted: int
    rf_nvs_p12_p13_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P316CheckGroupCBig6HomeManualNdFramingIntervalResult:
    check_group_id: str
    passed: bool
    mode_settings: str
    big6_home_screen_active: bool
    big6_tile_count: int
    home_lower_left_mode: str
    fx3_physical_e_nd_present: bool
    e_nd_actuator_tx_count: int
    framing_enabled: str
    framing_rec_stream_area: str
    framing_hdmi_area: str
    fx3_auto_framing_present: bool
    dormant_auto_framing_rejected: bool
    interval_shooting_active: bool
    interval_param_count: int
    interval_num_shots: int
    interval_target_slot: int
    slot1_interval_vault_firewall_enforced: bool
    slot1_data_sector_writes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class P316CheckGroupDTcRegenHdmiRecSshAuthZeroFanMaxTier0Result:
    check_group_id: str
    passed: bool
    tc_make: str
    tc_run: str
    simult_recording: bool
    tc_regen_source_slot: int
    hdmi_tc_output: str
    hdmi_rec_control: str
    hdmi_4ch_audio_output: str
    access_authen: str
    access_authen_protocol: str
    dormant_http_auth_rejected: bool
    fx3_fan_control: str
    fx6_fan_control: str
    fx3_fan_control_max_present: bool
    fx6_fan_control_max_present: bool
    dormant_fan_control_max_rejected: bool
    auto_power_off_temp: str
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
class Phase316ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwBrightMonShotMarkBig6HomeAndSshAuthReport:
    schema: str
    schema_version: str
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
    slot1_tier0_vault_mutated: bool
    rf_nvs_p12_p13_writes_authorized: bool
    fx3_bt_tc_link_present: bool
    fx3_auto_framing_present: bool
    fx3_bulb_timer_present: bool
    fx3_auto_hdr_present: bool
    fx3_in_camera_divide_extract_present: bool
    fx3_physical_e_nd_present: bool
    fx3_fan_control_max_present: bool
    fx6_fan_control_max_present: bool
    e_nd_actuator_tx_count: int
    wireless_rf_packets_emitted: int
    rf_packets_transmitted: int
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
    donor_inspection: Phase316DonorInspectionResult
    check_group_a_bright_monitoring_lcd_shotmark: (
        P316CheckGroupABrightMonitoringLcdShotMarkResult
    )
    check_group_b_zero_bt_tclink_wifi_usblan_airplane: (
        P316CheckGroupBZeroBtTcLinkWifiUsbLanAirplaneResult
    )
    check_group_c_big6_home_manual_nd_framing_interval: (
        P316CheckGroupCBig6HomeManualNdFramingIntervalResult
    )
    check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0: (
        P316CheckGroupDTcRegenHdmiRecSshAuthZeroFanMaxTier0Result
    )
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


def inspect_phase316_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
) -> Phase316DonorInspectionResult:
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
        return Phase316DonorInspectionResult(
            verification_mode="LOCAL_DONOR_O_RDONLY",
            passed=False,
            elapsed_seconds=round(dt, 6),
            within_150ms_budget=(dt < DONOR_INSPECTION_MAX_SECONDS),
            raw_firmware_bytes_leaked=PHASE316_RAW_FIRMWARE_BYTES_LEAKED,
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
        return Phase316DonorInspectionResult(
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            passed=True,
            elapsed_seconds=round(dt, 6),
            within_150ms_budget=(dt < DONOR_INSPECTION_MAX_SECONDS),
            raw_firmware_bytes_leaked=PHASE316_RAW_FIRMWARE_BYTES_LEAKED,
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

    return Phase316DonorInspectionResult(
        verification_mode="LOCAL_DONOR_O_RDONLY",
        passed=(len(errors) == 0),
        elapsed_seconds=round(dt, 6),
        within_150ms_budget=within_budget,
        raw_firmware_bytes_leaked=PHASE316_RAW_FIRMWARE_BYTES_LEAKED,
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
# Check Group A (Wave 58 §§1,2,4 — Bright Monitoring, Monitor Brightness,
#                Shot Mark / Dormant Edit, Still BULB & DRO vs Bulb Timer/HDR)
# ---------------------------------------------------------------------------


def evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P316_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    focus_mode: str = "MF",
    # Wave 58 §1: Bright Monitoring (_f 0x701f) & Monitor Brightness (0xe44b / 0xe1da)
    bright_monitoring_active: bool = False,
    bright_monitoring_in_shoot_menu_claimed: bool = False,
    live_view_display: str = "SETTING_EFFECT_ON",
    expect_setting_effect_on_during_bright_monitoring: bool = False,
    expect_bright_monitoring_blocks_focus_magnifier: bool = False,
    claimed_bright_monitoring_persists_after_power_cycle: bool = False,
    monitor_brightness_mode: str = "MANUAL",
    monitor_brightness_level: int = 0,
    dormant_lcd_brightness_mode_requested: bool = False,
    claimed_monitor_brightness_wiped_by_camera_reset: bool = False,
    fx6_backlight_is_lcd_brightness_claimed: bool = False,
    fx6_vf_brightness_1_15_in_fx3_claimed: bool = False,
    # Wave 58 §2: Zero Divide/Extract & FTP Cut, Shot Mark / Clip Flag / Edit Slot-1 Vault
    dormant_divide_or_extract_requested: bool = False,
    dormant_ftp_cut_15_30_60s_requested: bool = False,
    shot_mark_write_requested: bool = False,
    shot_mark_slot: int = 2,
    clip_flag: str = "NONE",
    clip_flag_write_requested: bool = False,
    clip_flag_slot: int = 2,
    photo_capture_requested: bool = False,
    photo_capture_slot: int = 2,
    create_divider_frame_requested: bool = False,
    divider_frame_slot: int = 2,
    edit_write_requested: bool = False,
    edit_write_slot: int = 2,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    # Wave 58 §4: Mechanical-only Still BULB + DRO vs Dormant Bulb Timer & Auto HDR
    bulb_enabled: bool = False,
    shutter_type: str = "MECHANICAL_SHUTTER",
    still_drive_mode: str = "SINGLE_SHOOTING",
    anti_flicker_shoot: str = "OFF",
    expect_bulb_in_electronic_or_cont_or_interval: bool = False,
    dro_mode: str = "OFF",
    dro_bracket_mode: str = "OFF",
    picture_profile: str = "OFF",
    log_shooting_mode: str = "CINE_EI",
    hlg_still_image: str = "OFF",
    expect_dro_active_with_pp_or_hlg: bool = False,
    dormant_bulb_timer_requested: bool = False,
    dormant_auto_hdr_requested: bool = False,
) -> P316CheckGroupABrightMonitoringLcdShotMarkResult:
    """Validate Wave 58 §§1,2,4 Bright Monitoring, Monitor Brightness, Shot Mark & BULB/DRO."""
    errors: List[str] = []

    norm_reset = _norm_upper(reset_action)
    norm_shoot = _norm_upper(shoot_mode)
    norm_exp = _norm_upper(exposure_mode)
    norm_focus = _norm_upper(focus_mode)
    norm_lv = _norm_upper(live_view_display)
    norm_mb_mode = _norm_upper(monitor_brightness_mode)
    norm_clip_flag = _norm_upper(clip_flag)
    norm_shutter = _norm_upper(shutter_type)
    norm_drive = _norm_upper(still_drive_mode)
    norm_antiflicker = _norm_upper(anti_flicker_shoot)
    norm_dro = _norm_upper(dro_mode)
    norm_dro_brk = _norm_upper(dro_bracket_mode)
    norm_pp = _norm_upper(picture_profile)
    norm_log = _norm_upper(log_shooting_mode)
    norm_hlg = _norm_upper(hlg_still_image)

    fw_tuple = _parse_fw_tuple(body_fw)
    if (
        int(body_model_id) != TARGET_MODEL_ID_INT
        or fw_tuple is None
        or fw_tuple < MIN_BODY_FW_TUPLE
    ):
        errors.append(
            f"{P316_GA_ERR_MODEL_OR_FW_FLOOR}: model_id={hex(int(body_model_id))}, body_fw={body_fw!r}"
        )
    if sony_help_guide_id != P316_SONY_HELP_GUIDE_ID:
        errors.append(
            f"{P316_GA_ERR_MODEL_OR_FW_FLOOR}: sony_help_guide_id={sony_help_guide_id!r} != {P316_SONY_HELP_GUIDE_ID!r}"
        )
    if norm_reset not in P316_VALID_RESET_ACTIONS:
        errors.append(f"{P316_GA_ERR_MODEL_OR_FW_FLOOR}: invalid reset_action={reset_action!r}")
    if norm_shoot not in P316_VALID_SHOOT_MODES:
        errors.append(f"{P316_GA_ERR_MODEL_OR_FW_FLOOR}: invalid shoot_mode={shoot_mode!r}")
    if norm_exp not in P316_VALID_EXPOSURE_MODES:
        errors.append(f"{P316_GA_ERR_MODEL_OR_FW_FLOOR}: invalid exposure_mode={exposure_mode!r}")
    if norm_focus not in P316_VALID_FOCUS_MODES:
        errors.append(f"{P316_GA_ERR_MODEL_OR_FW_FLOOR}: invalid focus_mode={focus_mode!r}")

    # Bright Monitoring (_f 0x701f)
    if bright_monitoring_in_shoot_menu_claimed:
        errors.append(
            f"{P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST}: "
            f"[Bright Monitoring] ({P316_BRIGHT_MONITORING_RESID16_HEX}) is Custom-Key-only "
            f"(no shooting menu toggle, EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )
    if bright_monitoring_active:
        if norm_exp not in P316_PASM_EXPOSURE_MODES or norm_focus != "MF":
            errors.append(
                f"{P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST}: "
                f"[Bright Monitoring] requires P/A/S/M + MF, got exposure={norm_exp}, focus={norm_focus}"
            )
        if norm_lv != "SETTING_EFFECT_OFF" or expect_setting_effect_on_during_bright_monitoring:
            errors.append(
                f"{P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST}: "
                "[Bright Monitoring] forces [Live View Display] = SETTING_EFFECT_OFF"
            )
    elif expect_setting_effect_on_during_bright_monitoring:
        errors.append(
            f"{P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST}: "
            "Setting Effect ON cannot remain active during Bright Monitoring"
        )
    if expect_bright_monitoring_blocks_focus_magnifier:
        errors.append(
            f"{P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST}: "
            "Ver. 7.00+ [Bright Monitoring] coexists with [Focus Magnifier] / [Auto Magnifier in MF]"
        )
    if claimed_bright_monitoring_persists_after_power_cycle:
        errors.append(
            f"{P316_GA_ERR_BRIGHT_MONITORING_CUSTOM_KEY_PASM_MF_OR_MAG_COEXIST}: "
            "[Bright Monitoring] auto-cancels on power off"
        )

    # Monitor Brightness (0xe44b / 0xe1da) & FX6 disambiguation
    dormant_mb_rejected = True
    if dormant_lcd_brightness_mode_requested or norm_mb_mode in P316_DORMANT_LCD_BRIGHTNESS_MODES:
        dormant_mb_rejected = False
        errors.append(
            f"{P316_GA_ERR_MONITOR_BRIGHTNESS_SUNNY_OR_FX6_BACKLIGHT_CONFUSION}: "
            f"dormant LCD_BRIGHTNESS AUTO/BRIGHT/NORMAL unsupported (EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )
    elif norm_mb_mode not in P316_VALID_MONITOR_BRIGHTNESS_MODES:
        errors.append(
            f"{P316_GA_ERR_MONITOR_BRIGHTNESS_SUNNY_OR_FX6_BACKLIGHT_CONFUSION}: "
            f"invalid monitor_brightness_mode={monitor_brightness_mode!r}"
        )
    if not (P316_MONITOR_BRIGHTNESS_MIN <= int(monitor_brightness_level) <= P316_MONITOR_BRIGHTNESS_MAX):
        errors.append(
            f"{P316_GA_ERR_MONITOR_BRIGHTNESS_SUNNY_OR_FX6_BACKLIGHT_CONFUSION}: "
            f"Manual Monitor Brightness level must be -2..+2, got {monitor_brightness_level}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_monitor_brightness_wiped_by_camera_reset:
        errors.append(
            f"{P316_GA_ERR_MONITOR_BRIGHTNESS_SUNNY_OR_FX6_BACKLIGHT_CONFUSION}: "
            "[Monitor Brightness] is Initialize-only and survives Camera Settings Reset"
        )
    if fx6_backlight_is_lcd_brightness_claimed or fx6_vf_brightness_1_15_in_fx3_claimed:
        errors.append(
            f"{P316_GA_ERR_MONITOR_BRIGHTNESS_SUNNY_OR_FX6_BACKLIGHT_CONFUSION}: "
            "FX6 AE Mode > Backlight is AE compensation (VF Brightness 1..15 is FX6-only)"
        )

    # Dormant Divide/Extract, FTP Cut & Slot-1 Tier-0 Vault Write Firewall
    dormant_edit_rejected = True
    if dormant_divide_or_extract_requested or dormant_ftp_cut_15_30_60s_requested:
        dormant_edit_rejected = False
        errors.append(
            f"{P316_GA_ERR_DORMANT_DIVIDE_EXTRACT_FTPCUT_OR_SLOT1_VAULT_WRITE}: "
            f"FX3 has zero in-camera [Divide]/[Extract] & dormant FTP 15/30/60s cut "
            f"(EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )
    if norm_clip_flag not in P316_VALID_CLIP_FLAGS:
        errors.append(
            f"{P316_GA_ERR_DORMANT_DIVIDE_EXTRACT_FTPCUT_OR_SLOT1_VAULT_WRITE}: "
            f"invalid clip_flag={clip_flag!r} (valid: {P316_VALID_CLIP_FLAGS})"
        )

    slot1_locked = bool(slot1_contains_tier0_dump or slot1_wp_locked)
    slot1_firewall_ok = True
    slot1_write_attempts = [
        label
        for label, req, slot in (
            ("Shot Mark", shot_mark_write_requested, shot_mark_slot),
            ("Clip Flag", clip_flag_write_requested, clip_flag_slot),
            ("Photo Capture", photo_capture_requested, photo_capture_slot),
            ("Create Divider Frame", create_divider_frame_requested, divider_frame_slot),
            ("Playback Edit", edit_write_requested, edit_write_slot),
        )
        if req and int(slot) == 1
    ]
    if slot1_locked and slot1_write_attempts:
        slot1_firewall_ok = False
        errors.append(
            f"{P316_GA_ERR_DORMANT_DIVIDE_EXTRACT_FTPCUT_OR_SLOT1_VAULT_WRITE}: "
            f"CRITICAL SLOT-1 TIER-0 VAULT FIREWALL: card-write path(s) {slot1_write_attempts} "
            f"blocked fail-closed on Slot 1 (EROFS={P316_ERRNO_EROFS}/EBUSY={P316_ERRNO_EBUSY})"
        )

    # Still BULB (0xe916) + DRO vs Dormant Bulb Timer (0x630f) & Auto HDR (0xe49d)
    if norm_shutter not in P316_VALID_SHUTTER_TYPES:
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: invalid shutter_type={shutter_type!r}"
        )
    if norm_drive not in P316_VALID_STILL_DRIVE_MODES:
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: invalid still_drive_mode={still_drive_mode!r}"
        )
    if norm_antiflicker not in P316_VALID_ON_OFF:
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: invalid anti_flicker_shoot={anti_flicker_shoot!r}"
        )
    if norm_dro not in P316_VALID_DRO_MODES:
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: invalid dro_mode={dro_mode!r}"
        )
    if norm_dro_brk not in P316_VALID_DRO_BRACKET_MODES:
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: invalid dro_bracket_mode={dro_bracket_mode!r}"
        )

    if expect_bulb_in_electronic_or_cont_or_interval:
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: "
            "Still [BULB] clamps to 30\" in Electronic Shutter / Continuous / Interval Shooting"
        )
    if bulb_enabled:
        if norm_shoot != "PHOTO" or norm_exp != "MANUAL_EXPOSURE":
            errors.append(
                f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: "
                "[BULB] requires Still PHOTO + MANUAL_EXPOSURE"
            )
        if norm_shutter != "MECHANICAL_SHUTTER":
            errors.append(
                f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: "
                "[BULB] is Mechanical-Shutter-only (clamps to 30\" in Electronic Shutter)"
            )
        if norm_drive not in ("SINGLE_SHOOTING", "SELF_TIMER_SINGLE"):
            errors.append(
                f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: "
                f"[BULB] disallowed under drive mode {norm_drive} (clamped to 30\")"
            )
        if norm_antiflicker == "ON":
            errors.append(
                f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: "
                "[BULB] disables [Anti-flicker Shoot.]"
            )

    if expect_dro_active_with_pp_or_hlg:
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: "
            "DRO / DRO Bracket is locked out when Picture Profile != Off, HLG Still = On, or Log != Off"
        )
    if (norm_dro != "OFF" or norm_dro_brk != "OFF") and (
        norm_pp != "OFF" or norm_hlg == "ON" or norm_log != "OFF"
    ):
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: "
            f"DRO={norm_dro}/DRO_Bracket={norm_dro_brk} blocked while PP={norm_pp}, HLG={norm_hlg}, Log={norm_log}"
        )

    if dormant_bulb_timer_requested:
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: "
            f"dormant [Bulb Timer] ({P316_DORMANT_BULB_TIMER_RESID16_HEX}) rejected (EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )
    if dormant_auto_hdr_requested:
        errors.append(
            f"{P316_GA_ERR_BULB_MECH_STILL_DRO_OR_DORMANT_BULB_TIMER_AUTO_HDR}: "
            f"dormant [Auto HDR] ({P316_DORMANT_AUTO_HDR_RESID16_HEX}) rejected (EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )

    return P316CheckGroupABrightMonitoringLcdShotMarkResult(
        check_group_id=P316_CHECK_GROUP_A_ID,
        passed=(len(errors) == 0),
        sony_help_guide_id=sony_help_guide_id,
        bright_monitoring_active=bool(bright_monitoring_active),
        bright_monitoring_custom_key_only=(not bright_monitoring_in_shoot_menu_claimed),
        bright_monitoring_focus_mag_coexist=(not expect_bright_monitoring_blocks_focus_magnifier),
        live_view_display=norm_lv,
        monitor_brightness_mode=norm_mb_mode,
        monitor_brightness_level=int(monitor_brightness_level),
        dormant_lcd_brightness_rejected=dormant_mb_rejected,
        dormant_divide_extract_ftp_cut_rejected=dormant_edit_rejected,
        clip_flag=norm_clip_flag,
        bulb_enabled=bool(bulb_enabled),
        dro_mode=norm_dro,
        dro_bracket_mode=norm_dro_brk,
        fx3_bulb_timer_present=False,
        fx3_auto_hdr_present=False,
        fx3_in_camera_divide_extract_present=False,
        slot1_vault_firewall_enforced=slot1_firewall_ok,
        slot1_data_sector_writes=PHASE316_SLOT1_DATA_SECTOR_WRITES,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group B (Wave 58 §3 — Zero BT Timecode Link, Wired VMC-BNCM1, Dual-SKU
#                Wi-Fi WPA2/WPA3, USB-LAN Mutual Exclusion & Airplane Zero-RF)
# ---------------------------------------------------------------------------


def evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
    *,
    reset_action: str = "NONE",
    # Bluetooth Timecode Link absence & Wired VMC-BNCM1 LTC
    dormant_bt_tc_link_requested: bool = False,
    fx3_bt_tc_link_present_claimed: bool = False,
    fx6_bt_tc_link_claimed: bool = False,
    fx3_builtin_bnc_tc_in_out_switch_claimed: bool = False,
    vmc_bncm1_ext_lk_active: bool = False,
    tc_make: str = "PRESET",
    tc_run: str = "FREE_RUN",
    # Dual-SKU Wi-Fi & Ver. 7.00+ Removal of WEP / WPA-PSK / IPsec
    wifi_sku: str = "WW728473",
    wifi_band_5ghz_requested: bool = False,
    outdoor_5ghz_w52_requested: bool = False,
    wifi_security_protocol: str = "WPA3_SAE",
    dormant_legacy_wifi_sec_requested: bool = False,
    wifi_enabled: bool = False,
    # USB-C USB-LAN (cdc_ncm.ko / r8152.ko / asix.ko, 0x7d2a)
    usb_lan_cnct_launch: str = "OFF",
    network_transport: str = "NONE",
    multi_micro_usb_device_attached: bool = False,
    exposed_usb_lan_kmods: Sequence[str] = P316_USB_LAN_KERNEL_MODULES,
    # Mandatory Physical Bench Zero-RF Lock (Airplane Mode = On)
    airplane_mode: str = "ON",
    bluetooth_enabled: bool = False,
    wireless_rf_packets_emitted: int = 0,
    rf_nvs_p12_p13_writes_requested: bool = False,
    claimed_airplane_wiped_by_reset: bool = False,
) -> P316CheckGroupBZeroBtTcLinkWifiUsbLanAirplaneResult:
    """Validate Wave 58 §3 zero BT Timecode Link, WPA2/WPA3, USB-LAN & Airplane Zero-RF."""
    errors: List[str] = []

    norm_reset = _norm_upper(reset_action)
    norm_tc_make = _norm_upper(tc_make)
    norm_tc_run = _norm_upper(tc_run)
    norm_sku = _norm_upper(wifi_sku)
    norm_sec = _norm_upper(wifi_security_protocol)
    norm_usblan_launch = _norm_upper(usb_lan_cnct_launch)
    norm_transport = _norm_upper(network_transport)
    norm_airplane = _norm_upper(airplane_mode)

    if norm_reset not in P316_VALID_RESET_ACTIONS:
        errors.append(
            f"{P316_GB_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL}: invalid reset_action={reset_action!r}"
        )

    # Zero Bluetooth Timecode Link & Wired VMC-BNCM1
    dormant_bt_rejected = True
    if dormant_bt_tc_link_requested or fx3_bt_tc_link_present_claimed:
        dormant_bt_rejected = False
        errors.append(
            f"{P316_GB_ERR_DORMANT_BT_TC_LINK_OR_VMC_BNCM1_EXT_LK_PREREQ}: "
            f"FX3 has ZERO Bluetooth [Timecode Link] (0 tc_link/UltraSync hits, EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )
    if fx6_bt_tc_link_claimed or fx3_builtin_bnc_tc_in_out_switch_claimed:
        errors.append(
            f"{P316_GB_ERR_DORMANT_BT_TC_LINK_OR_VMC_BNCM1_EXT_LK_PREREQ}: "
            "FX6 has physical BNC TC IN/OUT switch & zero BT; FX3 uses wired VMC-BNCM1 only"
        )
    if vmc_bncm1_ext_lk_active and (norm_tc_make != "PRESET" or norm_tc_run != "FREE_RUN"):
        errors.append(
            f"{P316_GB_ERR_DORMANT_BT_TC_LINK_OR_VMC_BNCM1_EXT_LK_PREREQ}: "
            f"wired {P316_VMC_BNCM1_PART_NUMBER} ({P316_VMC_BNCM1_ACCESSORY_CODE}) EXT-LK requires "
            f"Preset + Free Run, got {norm_tc_make}/{norm_tc_run}"
        )

    # Dual-SKU Wi-Fi & Removed Legacy WEP/WPA-PSK/IPsec
    if norm_sku not in P316_VALID_WIFI_SKUS:
        errors.append(
            f"{P316_GB_ERR_WIFI_SKU_OR_REMOVED_WEP_WPA_IPSEC}: invalid wifi_sku={wifi_sku!r}"
        )
    if norm_sku == "WW558244" and wifi_band_5ghz_requested:
        errors.append(
            f"{P316_GB_ERR_WIFI_SKU_OR_REMOVED_WEP_WPA_IPSEC}: "
            f"SKU WW558244 is 2.4GHz-only (5GHz unsupported, EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )
    if outdoor_5ghz_w52_requested:
        errors.append(
            f"{P316_GB_ERR_WIFI_SKU_OR_REMOVED_WEP_WPA_IPSEC}: "
            f"5GHz W52 ({P316_INDOOR_5GHZ_RESID16_HEX}) is restricted to indoor use"
        )

    dormant_sec_rejected = True
    if dormant_legacy_wifi_sec_requested or norm_sec in P316_REMOVED_LEGACY_WIFI_PROTOCOLS:
        dormant_sec_rejected = False
        errors.append(
            f"{P316_GB_ERR_WIFI_SKU_OR_REMOVED_WEP_WPA_IPSEC}: "
            f"Ver. 7.00+ removed WEP / WPA-PSK / Security(IPsec) (EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP}); "
            "only WPA2-PSK / WPA3-SAE allowed"
        )
    elif norm_sec not in P316_VALID_WIFI_SECURITY_PROTOCOLS:
        errors.append(
            f"{P316_GB_ERR_WIFI_SKU_OR_REMOVED_WEP_WPA_IPSEC}: invalid wifi_security_protocol={wifi_security_protocol!r}"
        )

    # USB-C USB-LAN (cdc_ncm.ko/r8152.ko/asix.ko) & Mutual Exclusion
    if norm_usblan_launch not in P316_VALID_ON_OFF:
        errors.append(
            f"{P316_GB_ERR_USBLAN_MUTUAL_EXCLUSION_OR_KMOD_MISMATCH}: invalid usb_lan_cnct_launch={usb_lan_cnct_launch!r}"
        )
    if norm_transport not in P316_VALID_NETWORK_TRANSPORTS:
        errors.append(
            f"{P316_GB_ERR_USBLAN_MUTUAL_EXCLUSION_OR_KMOD_MISMATCH}: invalid network_transport={network_transport!r}"
        )
    norm_kmods = tuple(str(k).strip() for k in exposed_usb_lan_kmods if str(k).strip())
    missing_kmods = [k for k in ("cdc_ncm.ko", "r8152.ko", "asix.ko") if k not in norm_kmods]
    if missing_kmods:
        errors.append(
            f"{P316_GB_ERR_USBLAN_MUTUAL_EXCLUSION_OR_KMOD_MISMATCH}: missing USB-LAN kernel modules {missing_kmods}"
        )
    if norm_transport == "USB_LAN" and (
        wifi_enabled or multi_micro_usb_device_attached or vmc_bncm1_ext_lk_active
    ):
        errors.append(
            f"{P316_GB_ERR_USBLAN_MUTUAL_EXCLUSION_OR_KMOD_MISMATCH}: "
            "USB-C USB-LAN is mutually exclusive with Wi-Fi and Multi/Micro USB devices (incl. VMC-BNCM1)"
        )

    # CRITICAL ZERO-RF FIREWALL: Mandatory Airplane Mode = On
    if norm_airplane not in P316_VALID_ON_OFF:
        errors.append(
            f"{P316_GB_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL}: invalid airplane_mode={airplane_mode!r}"
        )
    if norm_reset in ("RESET_NETWORK_SET", "INITIALIZE") and claimed_airplane_wiped_by_reset:
        errors.append(
            f"{P316_GB_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL}: "
            "[Airplane Mode] persists across Reset Network Set. and Initialize"
        )

    zero_rf_ok = True
    if (
        norm_airplane != "ON"
        or norm_transport == "WIRELESS_RF"
        or wifi_enabled
        or bluetooth_enabled
        or int(wireless_rf_packets_emitted) != 0
        or rf_nvs_p12_p13_writes_requested
    ):
        zero_rf_ok = False
        errors.append(
            f"{P316_GB_ERR_ZERO_RF_AIRPLANE_MODE_FIREWALL}: CRITICAL ZERO-RF FIREWALL: "
            "[Airplane Mode] must remain ON with zero Wi-Fi/BT TX and zero P12/P13 RF NVS writes"
        )

    return P316CheckGroupBZeroBtTcLinkWifiUsbLanAirplaneResult(
        check_group_id=P316_CHECK_GROUP_B_ID,
        passed=(len(errors) == 0),
        fx3_bt_tc_link_present=False,
        dormant_bt_tc_link_rejected=dormant_bt_rejected,
        vmc_bncm1_ext_lk_active=bool(vmc_bncm1_ext_lk_active),
        wifi_sku=norm_sku,
        wifi_security_protocol=norm_sec,
        dormant_legacy_wifi_sec_rejected=dormant_sec_rejected,
        usb_lan_cnct_launch=norm_usblan_launch,
        usb_lan_kernel_module_count=len(norm_kmods),
        network_transport=norm_transport,
        airplane_mode=norm_airplane,
        zero_rf_airplane_firewall_enforced=zero_rf_ok,
        wireless_rf_packets_emitted=PHASE316_WIRELESS_RF_PACKETS_EMITTED,
        rf_nvs_p12_p13_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group C (Wave 59 §§1-2 — Ver. 7.00+ BIG6 HOME, Zero Physical e-ND,
#                Manual Framing vs Dormant AI Auto Framing & 9,999-Shot Interval
#                vs Slot-1 Tier-0 Vault EROFS=30)
# ---------------------------------------------------------------------------


def evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
    *,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    log_shooting_mode: str = "CINE_EI",
    # Wave 59 §1: BIG6 HOME (_f 0x7d0d Fixed/Variable, 0x7ce3 Lower Left, ZERO e-ND)
    mode_settings: str = "FIXED_VARIABLE",
    big6_home_screen_active: bool = False,
    home_trigger_method: str = "NONE",
    exposed_big6_tiles: Sequence[str] = P316_BIG6_SIX_TILES,
    home_lower_left_mode: str = "APERTURE",
    fx3_physical_e_nd_claimed: bool = False,
    e_nd_actuator_tx_count: int = 0,
    expect_big6_displays_pp_during_log: bool = False,
    expect_big6_displays_variable_iso_in_cine_ei: bool = False,
    claimed_menu_fn_do_not_exit_home: bool = False,
    # Wave 59 §2A: Manual Framing Settings (_f 0x7d18) vs Dormant AI Auto Framing
    framing_enabled: str = "OFF",
    framing_rec_stream_area: str = "FULL",
    framing_hdmi_area: str = "CROP",
    apsc_s35_on: bool = False,
    rec_fps: float = 23.98,
    sq_fps: float = 60.0,
    active_rec_or_stream_during_framing_toggle: bool = False,
    dormant_auto_framing_requested: bool = False,
    fx3_auto_framing_present_claimed: bool = False,
    # Wave 59 §2B: Still Interval Shoot Func. (_f 0x7027, 7 resettable params, 9,999)
    interval_shooting_active: bool = False,
    exposure_mode: str = "MANUAL_EXPOSURE",
    bulb_enabled: bool = False,
    exposed_interval_params: Sequence[str] = P316_INTERVAL_SHOOT_7_PARAMS,
    interval_start_sec: int = 1,
    interval_sec: int = 3,
    interval_num_shots: int = 30,
    interval_ae_tracking: str = "MID",
    interval_shutter_type: str = "ELECTRONIC",
    interval_shoot_priority: str = "OFF",
    interval_target_slot: int = 2,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    claimed_interval_7params_survive_camera_reset: bool = False,
    fx3_interval_outputs_single_mxf_claimed: bool = False,
) -> P316CheckGroupCBig6HomeManualNdFramingIntervalResult:
    """Validate Wave 59 §§1-2 BIG6 HOME, Zero e-ND, Manual Framing & 9,999-shot Interval."""
    errors: List[str] = []

    norm_reset = _norm_upper(reset_action)
    norm_shoot = _norm_upper(shoot_mode)
    norm_log = _norm_upper(log_shooting_mode)
    norm_mode_set = _norm_upper(mode_settings)
    norm_trigger = _norm_upper(home_trigger_method)
    norm_lower_left = _norm_upper(home_lower_left_mode)
    norm_framing = _norm_upper(framing_enabled)
    norm_rec_area = _norm_upper(framing_rec_stream_area)
    norm_hdmi_area = _norm_upper(framing_hdmi_area)
    norm_exp = _norm_upper(exposure_mode)
    norm_int_ae = _norm_upper(interval_ae_tracking)
    norm_int_shut = _norm_upper(interval_shutter_type)
    norm_int_prio = _norm_upper(interval_shoot_priority)

    if norm_mode_set not in P316_VALID_MODE_SETTINGS:
        errors.append(
            f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: invalid mode_settings={mode_settings!r}"
        )
    if norm_trigger not in P316_VALID_HOME_TRIGGERS:
        errors.append(
            f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: invalid home_trigger_method={home_trigger_method!r}"
        )
    if norm_lower_left not in P316_VALID_HOME_LOWER_LEFT_MODES:
        errors.append(
            f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: invalid home_lower_left_mode={home_lower_left_mode!r}"
        )

    norm_tiles = tuple(str(t).strip().upper() for t in exposed_big6_tiles if str(t).strip())
    if norm_tiles != P316_BIG6_SIX_TILES:
        errors.append(
            f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: "
            f"BIG6 HOME must expose exact 6 tiles {P316_BIG6_SIX_TILES}, got {norm_tiles}"
        )

    if big6_home_screen_active:
        if norm_mode_set != "FIXED_VARIABLE":
            errors.append(
                f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: "
                f"Ver. 7.00+ BIG6 HOME screen requires [Mode Settings] ({P316_MODE_SETTINGS_RESID16_HEX}) = FIXED_VARIABLE"
            )
        if norm_shoot not in ("MOVIE", "S_AND_Q"):
            errors.append(
                f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: "
                f"BIG6 HOME screen operates in MOVIE/S_AND_Q, got {norm_shoot}"
            )
    if claimed_menu_fn_do_not_exit_home:
        errors.append(
            f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: "
            "MENU / Fn exits the BIG6 HOME screen"
        )
    if expect_big6_displays_pp_during_log and norm_log != "OFF":
        errors.append(
            f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: "
            "BIG6 displays [Select LUT] when Log Shooting != Off (not Picture Profile)"
        )
    elif expect_big6_displays_pp_during_log:
        errors.append(
            f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: "
            "BIG6 displays [Select LUT] (not PP) during Log Shooting"
        )
    if expect_big6_displays_variable_iso_in_cine_ei:
        errors.append(
            f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: "
            "BIG6 displays Base ISO + EI under Cine EI / Cine EI Quick (no variable ISO)"
        )

    # CRITICAL ZERO E-ND ACTUATOR FIREWALL
    if fx3_physical_e_nd_claimed or int(e_nd_actuator_tx_count) != 0:
        errors.append(
            f"{P316_GC_ERR_BIG6_HOME_FIXED_VAR_OR_ZERO_E_ND_VIOLATION}: "
            "ILME-FX3 has ZERO physical built-in e-ND actuator (BIG6 ND Filter is manual metadata only; "
            f"e_nd_actuator_tx_count must be 0, EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )

    # Manual Framing Settings (_f 0x7d18) vs Dormant AI Auto Framing
    if norm_framing not in P316_VALID_ON_OFF:
        errors.append(
            f"{P316_GC_ERR_MANUAL_FRAMING_LOCK_OR_DORMANT_AI_AUTO_FRAMING}: invalid framing_enabled={framing_enabled!r}"
        )
    if norm_rec_area not in P316_VALID_FRAMING_AREAS or norm_hdmi_area not in P316_VALID_FRAMING_AREAS:
        errors.append(
            f"{P316_GC_ERR_MANUAL_FRAMING_LOCK_OR_DORMANT_AI_AUTO_FRAMING}: invalid framing area rec={framing_rec_stream_area!r}, hdmi={framing_hdmi_area!r}"
        )
    if norm_framing == "ON":
        if apsc_s35_on:
            errors.append(
                f"{P316_GC_ERR_MANUAL_FRAMING_LOCK_OR_DORMANT_AI_AUTO_FRAMING}: "
                "[Framing Settings]=On disables [APS-C S35 Shooting]"
            )
        if float(rec_fps) >= 99.9 or float(sq_fps) >= 99.9 or active_rec_or_stream_during_framing_toggle:
            errors.append(
                f"{P316_GC_ERR_MANUAL_FRAMING_LOCK_OR_DORMANT_AI_AUTO_FRAMING}: "
                "[Framing Settings] is locked at 100p/120p or during active recording/streaming"
            )

    dormant_auto_framing_rejected = True
    if dormant_auto_framing_requested or fx3_auto_framing_present_claimed:
        dormant_auto_framing_rejected = False
        errors.append(
            f"{P316_GC_ERR_MANUAL_FRAMING_LOCK_OR_DORMANT_AI_AUTO_FRAMING}: "
            f"AI [Auto Framing] is DORMANT on FX3 ({P316_FRAMING_SUPPORT_ENUM}, 0 AUTO_FRAMING_AFR hits, "
            f"EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )

    # Still Interval Shoot Func. (_f 0x7027, 7 resettable params, 9,999 shots) + Slot-1 Firewall
    norm_int_params = tuple(str(p).strip().upper() for p in exposed_interval_params if str(p).strip())
    if norm_int_params != P316_INTERVAL_SHOOT_7_PARAMS:
        errors.append(
            f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: "
            f"[Interval Shoot Func.] must expose exact 7 params {P316_INTERVAL_SHOOT_7_PARAMS}, got {norm_int_params}"
        )
    if not (1 <= int(interval_start_sec) <= P316_INTERVAL_START_MAX_SEC):
        errors.append(
            f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: "
            f"Shooting Start Time must be 1..5999s (1s..99m59s), got {interval_start_sec}"
        )
    if not (1 <= int(interval_sec) <= P316_INTERVAL_SEC_MAX):
        errors.append(
            f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: "
            f"Shooting Interval must be 1..60s, got {interval_sec}"
        )
    if not (1 <= int(interval_num_shots) <= P316_INTERVAL_MAX_SHOTS):
        errors.append(
            f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: "
            f"Number of Shots must be 1..{P316_INTERVAL_MAX_SHOTS}, got {interval_num_shots}"
        )
    if norm_int_ae not in P316_VALID_INTERVAL_AE_TRACKING:
        errors.append(
            f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: invalid interval_ae_tracking={interval_ae_tracking!r}"
        )
    if norm_int_shut not in P316_VALID_INTERVAL_SHUTTER_TYPES:
        errors.append(
            f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: invalid interval_shutter_type={interval_shutter_type!r}"
        )
    if norm_int_prio not in P316_VALID_ON_OFF:
        errors.append(
            f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: invalid interval_shoot_priority={interval_shoot_priority!r}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_interval_7params_survive_camera_reset:
        errors.append(
            f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: "
            "all 7 [Interval Shoot Func.] params reset under Camera Settings Reset"
        )
    if fx3_interval_outputs_single_mxf_claimed:
        errors.append(
            f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: "
            "FX3 [Interval Shoot Func.] writes discrete still sequences (FX6 Interval Rec writes single MXF)"
        )

    slot1_locked = bool(slot1_contains_tier0_dump or slot1_wp_locked)
    slot1_interval_firewall_ok = True
    if interval_shooting_active:
        if norm_shoot != "PHOTO" or norm_exp == "INTELLIGENT_AUTO":
            errors.append(
                f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: "
                "[Interval Shoot Func.] requires Still PHOTO and is unavailable in Intelligent Auto"
            )
        if bulb_enabled:
            errors.append(
                f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: "
                "[Interval Shoot Func.] exits BULB to 30\""
            )
        if slot1_locked and int(interval_target_slot) == 1:
            slot1_interval_firewall_ok = False
            errors.append(
                f"{P316_GC_ERR_INTERVAL_7PARAM_9999_OR_SLOT1_VAULT_FIREWALL}: "
                f"CRITICAL SLOT-1 TIER-0 VAULT FIREWALL: Still [Interval Shoot Func.] up to 9,999 shots / "
                f"19,998 RAW+JPEG files + AVF_INFO burst blocked fail-closed on Slot 1 "
                f"(EROFS={P316_ERRNO_EROFS}/EBUSY={P316_ERRNO_EBUSY})"
            )

    return P316CheckGroupCBig6HomeManualNdFramingIntervalResult(
        check_group_id=P316_CHECK_GROUP_C_ID,
        passed=(len(errors) == 0),
        mode_settings=norm_mode_set,
        big6_home_screen_active=bool(big6_home_screen_active),
        big6_tile_count=len(norm_tiles),
        home_lower_left_mode=norm_lower_left,
        fx3_physical_e_nd_present=False,
        e_nd_actuator_tx_count=PHASE316_E_ND_ACTUATOR_TX_COUNT,
        framing_enabled=norm_framing,
        framing_rec_stream_area=norm_rec_area,
        framing_hdmi_area=norm_hdmi_area,
        fx3_auto_framing_present=False,
        dormant_auto_framing_rejected=dormant_auto_framing_rejected,
        interval_shooting_active=bool(interval_shooting_active),
        interval_param_count=len(norm_int_params),
        interval_num_shots=int(interval_num_shots),
        interval_target_slot=int(interval_target_slot),
        slot1_interval_vault_firewall_enforced=slot1_interval_firewall_ok,
        slot1_data_sector_writes=PHASE316_SLOT1_DATA_SECTOR_WRITES,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Check Group D (Wave 59 §§3-4 — TC Regenerate, HDMI REC Control, SSH Access
#                Authen., Zero Fan Control = Max + Tier-0 Dual-Media & 16/16 H0==H3)
# ---------------------------------------------------------------------------


def build_simulated_phase316_tier0_receipts(
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
            f"PHASE316_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE316_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
    *,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    # Wave 59 §3: Time Code Make=Regenerate, HDMI REC Control, 4ch Audio Output
    tc_make: str = "PRESET",
    tc_run: str = "FREE_RUN",
    simult_recording: bool = False,
    tc_regen_source_slot: int = 1,
    vmc_bncm1_ext_lk_active: bool = False,
    claimed_tc_make_run_wiped_by_camera_reset: bool = False,
    fx3_has_clock_tc_mode_claimed: bool = False,
    hdmi_tc_output: str = "OFF",
    hdmi_rec_control: str = "OFF",
    rec_media_dur_hdmi_output: str = "ON",
    streaming_active: bool = False,
    hdmi_4ch_audio_output: str = "CH1_CH2",
    # Wave 59 §4A: SSH Access Authen. (0 HTTPS/HTTP_DIGEST/BASIC_AUTH)
    access_authen: str = "ON",
    access_authen_protocol: str = "SSH",
    dormant_http_https_camera_auth_claimed: bool = False,
    claimed_access_authen_wiped_by_camera_reset: bool = False,
    expect_root_cert_authenticates_inbound_http_server: bool = False,
    # Wave 59 §4B: Thermal Fan Myth-Bust (ZERO Fan Control = Max on BOTH FX3 & FX6)
    fx3_fan_control: str = "AUTO",
    fx6_fan_control: str = "AUTO",
    dormant_fan_control_max_requested: bool = False,
    auto_power_off_temp: str = "HIGH",
    handheld_bare_skin_unacknowledged: bool = False,
    claimed_fan_or_autotemp_wiped_by_camera_reset: bool = False,
    # Tier-0 Receipt, 16/16 H0 == H3 & Unconditional Safety Redlines
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
) -> Tuple[P316CheckGroupDTcRegenHdmiRecSshAuthZeroFanMaxTier0Result, Tuple[str, ...]]:
    """Validate Wave 59 §§3-4 TC Regenerate, HDMI REC Control, SSH Auth, Zero Fan Max & Tier-0."""
    errors: List[str] = []
    tier0_errors: List[str] = []
    warnings: List[str] = []

    norm_reset = _norm_upper(reset_action)
    norm_shoot = _norm_upper(shoot_mode)
    norm_tc_make = _norm_upper(tc_make)
    norm_tc_run = _norm_upper(tc_run)
    norm_hdmi_tc = _norm_upper(hdmi_tc_output)
    norm_hdmi_rec = _norm_upper(hdmi_rec_control)
    norm_rec_media_hdmi = _norm_upper(rec_media_dur_hdmi_output)
    norm_4ch_out = _norm_upper(hdmi_4ch_audio_output)
    norm_auth = _norm_upper(access_authen)
    norm_auth_proto = _norm_upper(access_authen_protocol)
    norm_fx3_fan = _norm_upper(fx3_fan_control)
    norm_fx6_fan = _norm_upper(fx6_fan_control)
    norm_auto_temp = _norm_upper(auto_power_off_temp)

    # Wave 59 §3: Time Code Make=Regenerate & HDMI REC Control
    if norm_tc_make not in P316_VALID_TC_MAKE_MODES:
        errors.append(
            f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: invalid tc_make={tc_make!r}"
        )
    if norm_tc_run not in P316_VALID_TC_RUN_MODES:
        errors.append(
            f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: invalid tc_run={tc_run!r}"
        )
    if norm_tc_make == "REGENERATE":
        if norm_tc_run != "REC_RUN":
            errors.append(
                f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: "
                "[Time Code Make]=REGENERATE forces [Time Code Run]=REC_RUN"
            )
        if simult_recording and int(tc_regen_source_slot) != 1:
            errors.append(
                f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: "
                f"[Time Code Make]=REGENERATE on Simult. Recording deterministically reads Slot 1, got Slot {tc_regen_source_slot}"
            )
        if vmc_bncm1_ext_lk_active:
            errors.append(
                f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: "
                "[Time Code Make]=REGENERATE cannot coexist with VMC-BNCM1 EXT-LK (needs Preset + Free Run)"
            )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_tc_make_run_wiped_by_camera_reset:
        errors.append(
            f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: "
            "neither Time Code Make nor Time Code Run resets under Camera Settings Reset"
        )
    if fx3_has_clock_tc_mode_claimed:
        errors.append(
            f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: "
            "Clock TC mode belongs to FX6 (absent on ILME-FX3)"
        )

    if norm_hdmi_tc not in P316_VALID_ON_OFF:
        errors.append(
            f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: invalid hdmi_tc_output={hdmi_tc_output!r}"
        )
    if norm_hdmi_rec not in P316_VALID_ON_OFF:
        errors.append(
            f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: invalid hdmi_rec_control={hdmi_rec_control!r}"
        )
    if norm_rec_media_hdmi not in P316_VALID_REC_MEDIA_DUR_HDMI_MODES:
        errors.append(
            f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: invalid rec_media_dur_hdmi_output={rec_media_dur_hdmi_output!r}"
        )
    if norm_4ch_out not in P316_VALID_4CH_AUDIO_OUTPUT_MODES:
        errors.append(
            f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: invalid hdmi_4ch_audio_output={hdmi_4ch_audio_output!r}"
        )
    if norm_hdmi_rec == "ON":
        if norm_hdmi_tc != "ON":
            errors.append(
                f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: "
                "HDMI [REC Control]=On is gated on [Time Code Output]=On"
            )
        if norm_rec_media_hdmi not in ("ON", "OFF_HDMI_ONLY"):
            errors.append(
                f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: "
                "HDMI [REC Control]=On requires [Rec. Media dur HDMI Output]=On or Off(HDMI Only)"
            )
        if norm_shoot == "S_AND_Q" or streaming_active:
            errors.append(
                f"{P316_GD_ERR_TC_REGEN_HDMI_REC_CTRL_OR_4CH_AUDIO}: "
                "HDMI [REC Control] is disabled in S&Q or active Network Streaming"
            )

    # Wave 59 §4A: Ver. 7.00+ SSH Access Authen. (Zero HTTPS/HTTP_DIGEST/BASIC_AUTH)
    if norm_auth not in P316_VALID_ON_OFF:
        errors.append(
            f"{P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH}: invalid access_authen={access_authen!r}"
        )
    dormant_http_rejected = True
    if dormant_http_https_camera_auth_claimed or norm_auth_proto in P316_DORMANT_HTTP_AUTH_PROTOCOLS:
        dormant_http_rejected = False
        errors.append(
            f"{P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH}: "
            f"[Access Authen.] uses SSH (MSGID_SSHD_START_CMD / sshd_start); "
            f"0 hits for HTTPS/HTTP_DIGEST/BASIC_AUTH (EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )
    elif norm_auth_proto not in P316_VALID_ACCESS_AUTHEN_PROTOCOLS:
        errors.append(
            f"{P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH}: invalid access_authen_protocol={access_authen_protocol!r}"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_access_authen_wiped_by_camera_reset:
        errors.append(
            f"{P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH}: "
            "[Access Authen. Settings] survives Camera Settings Reset (Initialize / Reset Network Set. only)"
        )
    if expect_root_cert_authenticates_inbound_http_server:
        errors.append(
            f"{P316_GD_ERR_SSH_ACCESS_AUTHEN_OR_DORMANT_HTTPS_HTTP_AUTH}: "
            f"[Import Root Certificate] ({P316_IMPORT_ROOT_CERT_RESID16_HEX}) applies to outbound client "
            "FTPS/RTMPS/Cloud TLS only"
        )

    # Wave 59 §4B: Thermal Fan Myth-Bust (ZERO Fan Control = Max on FX3 AND FX6)
    dormant_fan_max_rejected = True
    if (
        dormant_fan_control_max_requested
        or norm_fx3_fan == "MAX"
        or norm_fx6_fan == "MAX"
    ):
        dormant_fan_max_rejected = False
        errors.append(
            f"{P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD}: "
            f"NEITHER FX3 NOR FX6 exposes Fan Control = Max (FAN_CONTROL_MAX = 0 hits; "
            f"EINVAL={P316_ERRNO_EINVAL}/EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )
    elif norm_fx3_fan not in P316_FX3_VALID_4_FAN_MODES:
        errors.append(
            f"{P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD}: "
            f"invalid fx3_fan_control={fx3_fan_control!r} (valid 4 modes: {P316_FX3_VALID_4_FAN_MODES})"
        )
    if norm_fx6_fan == "ALWAYS_OFF":
        errors.append(
            f"{P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD}: "
            f"FX6 Fan Control Always Off is dormant (valid 3 modes: {P316_FX6_VALID_3_FAN_MODES}, EOPNOTSUPP={P316_ERRNO_EOPNOTSUPP})"
        )
    elif norm_fx6_fan != "MAX" and norm_fx6_fan not in P316_FX6_VALID_3_FAN_MODES:
        errors.append(
            f"{P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD}: invalid fx6_fan_control={fx6_fan_control!r}"
        )
    if norm_auto_temp not in P316_VALID_AUTO_POWER_OFF_TEMPS:
        errors.append(
            f"{P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD}: invalid auto_power_off_temp={auto_power_off_temp!r}"
        )
    if norm_auto_temp == "HIGH" and handheld_bare_skin_unacknowledged:
        errors.append(
            f"{P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD}: "
            "[Auto Power OFF Temp.]=High requires tripod / non-handheld thermal guard acknowledgement"
        )
    if norm_reset == "CAMERA_SETTINGS_RESET" and claimed_fan_or_autotemp_wiped_by_camera_reset:
        errors.append(
            f"{P316_GD_ERR_ZERO_FAN_CONTROL_MAX_OR_THERMAL_GUARD}: "
            "[Fan Control] & [Auto Power OFF Temp.] survive Camera Settings Reset"
        )

    # Unconditional Safety Redlines & 16/16 H0 == H3
    if simulated_passive_tx_bytes != 0:
        errors.append(
            f"{P316_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: passive_tx_bytes_emitted={simulated_passive_tx_bytes} != 0"
        )
    if (
        claim_hardware_live_attach_authorized
        or claim_persistent_emmc_writes_authorized
        or claim_cross_model_flash_authorized
    ):
        errors.append(
            f"{P316_GD_ERR_FAIL_CLOSED_REDLINE_VIOLATION}: hardware_live_attach / persistent_emmc_writes / cross_model_flash are unconditionally LOCKED OFF"
        )

    surface_count = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_count, int(simulated_h0_h3_drifted_surfaces)))
    equals_count = max(0, surface_count - drifted)
    if drifted != 0:
        errors.append(
            f"{P316_GD_ERR_H0_H3_IMMUTABILITY_DRIFT}: {drifted} surfaces drifted between H0 and H3"
        )

    # Dual-Media 528 B FX3RCPT1 Tier-0 Receipt Gating
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
        raw_a, raw_b, sim_h0 = build_simulated_phase316_tier0_receipts(
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
                f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
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
                f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
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
            f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    elif raw_a is None or raw_b is None:
        tier0_errors.append(
            f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: both Copy A and Copy B 528B FX3RCPT1 receipts are required"
        )
    else:
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media_ok = True
            else:
                tier0_errors.append(
                    f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{P316_GD_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    group_result = P316CheckGroupDTcRegenHdmiRecSshAuthZeroFanMaxTier0Result(
        check_group_id=P316_CHECK_GROUP_D_ID,
        passed=(len(errors) == 0),
        tc_make=norm_tc_make,
        tc_run=norm_tc_run,
        simult_recording=bool(simult_recording),
        tc_regen_source_slot=int(tc_regen_source_slot),
        hdmi_tc_output=norm_hdmi_tc,
        hdmi_rec_control=norm_hdmi_rec,
        hdmi_4ch_audio_output=norm_4ch_out,
        access_authen=norm_auth,
        access_authen_protocol=norm_auth_proto,
        dormant_http_auth_rejected=dormant_http_rejected,
        fx3_fan_control=norm_fx3_fan,
        fx6_fan_control=norm_fx6_fan,
        fx3_fan_control_max_present=False,
        fx6_fan_control_max_present=False,
        dormant_fan_control_max_rejected=dormant_fan_max_rejected,
        auto_power_off_temp=norm_auto_temp,
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


def evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    sony_help_guide_id: str = P316_SONY_HELP_GUIDE_ID,
    reset_action: str = "NONE",
    shoot_mode: str = "MOVIE",
    exposure_mode: str = "MANUAL_EXPOSURE",
    focus_mode: str = "MF",
    # Check Group A (Wave 58 §§1,2,4)
    bright_monitoring_active: bool = False,
    bright_monitoring_in_shoot_menu_claimed: bool = False,
    live_view_display: str = "SETTING_EFFECT_ON",
    expect_setting_effect_on_during_bright_monitoring: bool = False,
    expect_bright_monitoring_blocks_focus_magnifier: bool = False,
    claimed_bright_monitoring_persists_after_power_cycle: bool = False,
    monitor_brightness_mode: str = "MANUAL",
    monitor_brightness_level: int = 0,
    dormant_lcd_brightness_mode_requested: bool = False,
    claimed_monitor_brightness_wiped_by_camera_reset: bool = False,
    fx6_backlight_is_lcd_brightness_claimed: bool = False,
    fx6_vf_brightness_1_15_in_fx3_claimed: bool = False,
    dormant_divide_or_extract_requested: bool = False,
    dormant_ftp_cut_15_30_60s_requested: bool = False,
    shot_mark_write_requested: bool = False,
    shot_mark_slot: int = 2,
    clip_flag: str = "NONE",
    clip_flag_write_requested: bool = False,
    clip_flag_slot: int = 2,
    photo_capture_requested: bool = False,
    photo_capture_slot: int = 2,
    create_divider_frame_requested: bool = False,
    divider_frame_slot: int = 2,
    edit_write_requested: bool = False,
    edit_write_slot: int = 2,
    slot1_contains_tier0_dump: bool = True,
    slot1_wp_locked: bool = True,
    bulb_enabled: bool = False,
    shutter_type: str = "MECHANICAL_SHUTTER",
    still_drive_mode: str = "SINGLE_SHOOTING",
    anti_flicker_shoot: str = "OFF",
    expect_bulb_in_electronic_or_cont_or_interval: bool = False,
    dro_mode: str = "OFF",
    dro_bracket_mode: str = "OFF",
    picture_profile: str = "OFF",
    log_shooting_mode: str = "CINE_EI",
    hlg_still_image: str = "OFF",
    expect_dro_active_with_pp_or_hlg: bool = False,
    dormant_bulb_timer_requested: bool = False,
    dormant_auto_hdr_requested: bool = False,
    # Check Group B (Wave 58 §3)
    dormant_bt_tc_link_requested: bool = False,
    fx3_bt_tc_link_present_claimed: bool = False,
    fx6_bt_tc_link_claimed: bool = False,
    fx3_builtin_bnc_tc_in_out_switch_claimed: bool = False,
    vmc_bncm1_ext_lk_active: bool = False,
    tc_make: str = "PRESET",
    tc_run: str = "FREE_RUN",
    wifi_sku: str = "WW728473",
    wifi_band_5ghz_requested: bool = False,
    outdoor_5ghz_w52_requested: bool = False,
    wifi_security_protocol: str = "WPA3_SAE",
    dormant_legacy_wifi_sec_requested: bool = False,
    wifi_enabled: bool = False,
    usb_lan_cnct_launch: str = "OFF",
    network_transport: str = "NONE",
    multi_micro_usb_device_attached: bool = False,
    exposed_usb_lan_kmods: Sequence[str] = P316_USB_LAN_KERNEL_MODULES,
    airplane_mode: str = "ON",
    bluetooth_enabled: bool = False,
    wireless_rf_packets_emitted: int = 0,
    rf_nvs_p12_p13_writes_requested: bool = False,
    claimed_airplane_wiped_by_reset: bool = False,
    # Check Group C (Wave 59 §§1-2)
    mode_settings: str = "FIXED_VARIABLE",
    big6_home_screen_active: bool = False,
    home_trigger_method: str = "NONE",
    exposed_big6_tiles: Sequence[str] = P316_BIG6_SIX_TILES,
    home_lower_left_mode: str = "APERTURE",
    fx3_physical_e_nd_claimed: bool = False,
    e_nd_actuator_tx_count: int = 0,
    expect_big6_displays_pp_during_log: bool = False,
    expect_big6_displays_variable_iso_in_cine_ei: bool = False,
    claimed_menu_fn_do_not_exit_home: bool = False,
    framing_enabled: str = "OFF",
    framing_rec_stream_area: str = "FULL",
    framing_hdmi_area: str = "CROP",
    apsc_s35_on: bool = False,
    rec_fps: float = 23.98,
    sq_fps: float = 60.0,
    active_rec_or_stream_during_framing_toggle: bool = False,
    dormant_auto_framing_requested: bool = False,
    fx3_auto_framing_present_claimed: bool = False,
    interval_shooting_active: bool = False,
    exposed_interval_params: Sequence[str] = P316_INTERVAL_SHOOT_7_PARAMS,
    interval_start_sec: int = 1,
    interval_sec: int = 3,
    interval_num_shots: int = 30,
    interval_ae_tracking: str = "MID",
    interval_shutter_type: str = "ELECTRONIC",
    interval_shoot_priority: str = "OFF",
    interval_target_slot: int = 2,
    claimed_interval_7params_survive_camera_reset: bool = False,
    fx3_interval_outputs_single_mxf_claimed: bool = False,
    # Check Group D (Wave 59 §§3-4 + Tier-0)
    simult_recording: bool = False,
    tc_regen_source_slot: int = 1,
    claimed_tc_make_run_wiped_by_camera_reset: bool = False,
    fx3_has_clock_tc_mode_claimed: bool = False,
    hdmi_tc_output: str = "OFF",
    hdmi_rec_control: str = "OFF",
    rec_media_dur_hdmi_output: str = "ON",
    streaming_active: bool = False,
    hdmi_4ch_audio_output: str = "CH1_CH2",
    access_authen: str = "ON",
    access_authen_protocol: str = "SSH",
    dormant_http_https_camera_auth_claimed: bool = False,
    claimed_access_authen_wiped_by_camera_reset: bool = False,
    expect_root_cert_authenticates_inbound_http_server: bool = False,
    fx3_fan_control: str = "AUTO",
    fx6_fan_control: str = "AUTO",
    dormant_fan_control_max_requested: bool = False,
    auto_power_off_temp: str = "HIGH",
    handheld_bare_skin_unacknowledged: bool = False,
    claimed_fan_or_autotemp_wiped_by_camera_reset: bool = False,
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
) -> RealHwBrightMonShotMarkBig6HomeAndSshAuthReport:
    """Execute Phase 316 13th real-hardware physical bench readiness verifier (`A..D`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase316_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    ga = evaluate_p316_check_group_a_bright_monitoring_lcd_shotmark(
        body_model_id=body_model_id,
        body_fw=body_fw,
        sony_help_guide_id=sony_help_guide_id,
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        exposure_mode=exposure_mode,
        focus_mode=focus_mode,
        bright_monitoring_active=bright_monitoring_active,
        bright_monitoring_in_shoot_menu_claimed=bright_monitoring_in_shoot_menu_claimed,
        live_view_display=live_view_display,
        expect_setting_effect_on_during_bright_monitoring=expect_setting_effect_on_during_bright_monitoring,
        expect_bright_monitoring_blocks_focus_magnifier=expect_bright_monitoring_blocks_focus_magnifier,
        claimed_bright_monitoring_persists_after_power_cycle=claimed_bright_monitoring_persists_after_power_cycle,
        monitor_brightness_mode=monitor_brightness_mode,
        monitor_brightness_level=monitor_brightness_level,
        dormant_lcd_brightness_mode_requested=dormant_lcd_brightness_mode_requested,
        claimed_monitor_brightness_wiped_by_camera_reset=claimed_monitor_brightness_wiped_by_camera_reset,
        fx6_backlight_is_lcd_brightness_claimed=fx6_backlight_is_lcd_brightness_claimed,
        fx6_vf_brightness_1_15_in_fx3_claimed=fx6_vf_brightness_1_15_in_fx3_claimed,
        dormant_divide_or_extract_requested=dormant_divide_or_extract_requested,
        dormant_ftp_cut_15_30_60s_requested=dormant_ftp_cut_15_30_60s_requested,
        shot_mark_write_requested=shot_mark_write_requested,
        shot_mark_slot=shot_mark_slot,
        clip_flag=clip_flag,
        clip_flag_write_requested=clip_flag_write_requested,
        clip_flag_slot=clip_flag_slot,
        photo_capture_requested=photo_capture_requested,
        photo_capture_slot=photo_capture_slot,
        create_divider_frame_requested=create_divider_frame_requested,
        divider_frame_slot=divider_frame_slot,
        edit_write_requested=edit_write_requested,
        edit_write_slot=edit_write_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        bulb_enabled=bulb_enabled,
        shutter_type=shutter_type,
        still_drive_mode=still_drive_mode,
        anti_flicker_shoot=anti_flicker_shoot,
        expect_bulb_in_electronic_or_cont_or_interval=expect_bulb_in_electronic_or_cont_or_interval,
        dro_mode=dro_mode,
        dro_bracket_mode=dro_bracket_mode,
        picture_profile=picture_profile,
        log_shooting_mode=log_shooting_mode,
        hlg_still_image=hlg_still_image,
        expect_dro_active_with_pp_or_hlg=expect_dro_active_with_pp_or_hlg,
        dormant_bulb_timer_requested=dormant_bulb_timer_requested,
        dormant_auto_hdr_requested=dormant_auto_hdr_requested,
    )
    gb = evaluate_p316_check_group_b_zero_bt_tclink_wifi_usblan_airplane(
        reset_action=reset_action,
        dormant_bt_tc_link_requested=dormant_bt_tc_link_requested,
        fx3_bt_tc_link_present_claimed=fx3_bt_tc_link_present_claimed,
        fx6_bt_tc_link_claimed=fx6_bt_tc_link_claimed,
        fx3_builtin_bnc_tc_in_out_switch_claimed=fx3_builtin_bnc_tc_in_out_switch_claimed,
        vmc_bncm1_ext_lk_active=vmc_bncm1_ext_lk_active,
        tc_make=tc_make,
        tc_run=tc_run,
        wifi_sku=wifi_sku,
        wifi_band_5ghz_requested=wifi_band_5ghz_requested,
        outdoor_5ghz_w52_requested=outdoor_5ghz_w52_requested,
        wifi_security_protocol=wifi_security_protocol,
        dormant_legacy_wifi_sec_requested=dormant_legacy_wifi_sec_requested,
        wifi_enabled=wifi_enabled,
        usb_lan_cnct_launch=usb_lan_cnct_launch,
        network_transport=network_transport,
        multi_micro_usb_device_attached=multi_micro_usb_device_attached,
        exposed_usb_lan_kmods=exposed_usb_lan_kmods,
        airplane_mode=airplane_mode,
        bluetooth_enabled=bluetooth_enabled,
        wireless_rf_packets_emitted=wireless_rf_packets_emitted,
        rf_nvs_p12_p13_writes_requested=rf_nvs_p12_p13_writes_requested,
        claimed_airplane_wiped_by_reset=claimed_airplane_wiped_by_reset,
    )
    gc = evaluate_p316_check_group_c_big6_home_manual_nd_framing_interval(
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        log_shooting_mode=log_shooting_mode,
        mode_settings=mode_settings,
        big6_home_screen_active=big6_home_screen_active,
        home_trigger_method=home_trigger_method,
        exposed_big6_tiles=exposed_big6_tiles,
        home_lower_left_mode=home_lower_left_mode,
        fx3_physical_e_nd_claimed=fx3_physical_e_nd_claimed,
        e_nd_actuator_tx_count=e_nd_actuator_tx_count,
        expect_big6_displays_pp_during_log=expect_big6_displays_pp_during_log,
        expect_big6_displays_variable_iso_in_cine_ei=expect_big6_displays_variable_iso_in_cine_ei,
        claimed_menu_fn_do_not_exit_home=claimed_menu_fn_do_not_exit_home,
        framing_enabled=framing_enabled,
        framing_rec_stream_area=framing_rec_stream_area,
        framing_hdmi_area=framing_hdmi_area,
        apsc_s35_on=apsc_s35_on,
        rec_fps=rec_fps,
        sq_fps=sq_fps,
        active_rec_or_stream_during_framing_toggle=active_rec_or_stream_during_framing_toggle,
        dormant_auto_framing_requested=dormant_auto_framing_requested,
        fx3_auto_framing_present_claimed=fx3_auto_framing_present_claimed,
        interval_shooting_active=interval_shooting_active,
        exposure_mode=exposure_mode,
        bulb_enabled=bulb_enabled,
        exposed_interval_params=exposed_interval_params,
        interval_start_sec=interval_start_sec,
        interval_sec=interval_sec,
        interval_num_shots=interval_num_shots,
        interval_ae_tracking=interval_ae_tracking,
        interval_shutter_type=interval_shutter_type,
        interval_shoot_priority=interval_shoot_priority,
        interval_target_slot=interval_target_slot,
        slot1_contains_tier0_dump=slot1_contains_tier0_dump,
        slot1_wp_locked=slot1_wp_locked,
        claimed_interval_7params_survive_camera_reset=claimed_interval_7params_survive_camera_reset,
        fx3_interval_outputs_single_mxf_claimed=fx3_interval_outputs_single_mxf_claimed,
    )
    gd, tier0_errors = evaluate_p316_check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0(
        reset_action=reset_action,
        shoot_mode=shoot_mode,
        tc_make=tc_make,
        tc_run=tc_run,
        simult_recording=simult_recording,
        tc_regen_source_slot=tc_regen_source_slot,
        vmc_bncm1_ext_lk_active=vmc_bncm1_ext_lk_active,
        claimed_tc_make_run_wiped_by_camera_reset=claimed_tc_make_run_wiped_by_camera_reset,
        fx3_has_clock_tc_mode_claimed=fx3_has_clock_tc_mode_claimed,
        hdmi_tc_output=hdmi_tc_output,
        hdmi_rec_control=hdmi_rec_control,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        streaming_active=streaming_active,
        hdmi_4ch_audio_output=hdmi_4ch_audio_output,
        access_authen=access_authen,
        access_authen_protocol=access_authen_protocol,
        dormant_http_https_camera_auth_claimed=dormant_http_https_camera_auth_claimed,
        claimed_access_authen_wiped_by_camera_reset=claimed_access_authen_wiped_by_camera_reset,
        expect_root_cert_authenticates_inbound_http_server=expect_root_cert_authenticates_inbound_http_server,
        fx3_fan_control=fx3_fan_control,
        fx6_fan_control=fx6_fan_control,
        dormant_fan_control_max_requested=dormant_fan_control_max_requested,
        auto_power_off_temp=auto_power_off_temp,
        handheld_bare_skin_unacknowledged=handheld_bare_skin_unacknowledged,
        claimed_fan_or_autotemp_wiped_by_camera_reset=claimed_fan_or_autotemp_wiped_by_camera_reset,
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
            "Enforce custom-key-only [Bright Monitoring] (Setting Effect OFF, P/A/S/M+MF, Focus Magnifier coexistence), Initialize-only [Monitor Brightness] Manual/Sunny Weather (reject AUTO/BRIGHT/NORMAL), reject dormant Divide/Extract & FTP cut, enforce Slot-1 Tier-0 EROFS=30 firewall on Shot Mark/Clip Flag/Edit, and keep Still-Mechanical BULB + DRO vs dormant Bulb Timer/Auto HDR."
        )
    if not gb.passed:
        remediations.append(
            "Reject dormant Bluetooth [Timecode Link] (VMC-BNCM1 wired Preset+FreeRun only), enforce dual-SKU Wi-Fi & WPA2-PSK/WPA3-SAE (reject WEP/WPA-PSK/IPsec), keep USB-C USB-LAN mutually exclusive with Multi/Micro USB & Wi-Fi, and keep mandatory [Airplane Mode]=On (0 RF packets, P12/P13 untouched)."
        )
    if not gc.passed:
        remediations.append(
            "Gate Ver. 7.00+ BIG6 HOME screen on [Mode Settings]=Fixed/Variable with zero physical e-ND actuator (e_nd_actuator_tx_count==0), keep manual [Framing Settings] vs dormant AI [Auto Framing] (EOPNOTSUPP=95), and enforce 7-param 9,999-shot [Interval Shoot Func.] Slot-1 Tier-0 Vault EROFS=30 firewall."
        )
    if not gd.passed or not gd.tier0_receipt_verified:
        remediations.append(
            "Enforce [Time Code Make]=Regenerate -> Rec Run & Slot 1 on Simult., HDMI [REC Control] <- [Time Code Output]=On, SSH-only [Access Authen.] (reject HTTPS/HTTP_DIGEST/BASIC_AUTH), zero Fan Control=Max on both FX3 & FX6, 16/16 H0==H3 invariance, and dual-device 528B FX3RCPT1 Tier-0 receipts."
        )

    if not all_4_passed:
        verdict = P316_GO_NO_GO_BLOCKED_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_FAILURE
        overall_status = verdict
    elif not gd.tier0_receipt_verified:
        if not gd.tier0_receipt_present:
            verdict = GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            overall_status = P316_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
        else:
            verdict = P316_GO_NO_GO_BLOCKED_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_FAILURE
            overall_status = verdict
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
        overall_status = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED
        overall_status = P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED

    provisional = RealHwBrightMonShotMarkBig6HomeAndSshAuthReport(
        schema=PHASE_316_SCHEMA,
        schema_version=PHASE_316_SCHEMA,
        phase_version=PHASE_316_VERSION,
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
        slot1_tier0_vault_mutated=False,
        rf_nvs_p12_p13_writes_authorized=False,
        fx3_bt_tc_link_present=False,
        fx3_auto_framing_present=False,
        fx3_bulb_timer_present=False,
        fx3_auto_hdr_present=False,
        fx3_in_camera_divide_extract_present=False,
        fx3_physical_e_nd_present=False,
        fx3_fan_control_max_present=False,
        fx6_fan_control_max_present=False,
        e_nd_actuator_tx_count=PHASE316_E_ND_ACTUATOR_TX_COUNT,
        wireless_rf_packets_emitted=PHASE316_WIRELESS_RF_PACKETS_EMITTED,
        rf_packets_transmitted=PHASE316_WIRELESS_RF_PACKETS_EMITTED,
        slot1_data_sector_writes=PHASE316_SLOT1_DATA_SECTOR_WRITES,
        usb_packets_transmitted=PHASE316_USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHASE316_USB_PACKETS_TRANSMITTED,
        raw_firmware_bytes_leaked=PHASE316_RAW_FIRMWARE_BYTES_LEAKED,
        passive_tx_bytes_emitted=gd.passive_tx_bytes_emitted,
        check_group_count=4,
        check_groups_passed=groups_passed,
        all_4_check_groups_passed=all_4_passed,
        tier0_receipt_verified=gd.tier0_receipt_verified,
        h0_h3_surface_count=gd.h0_h3_surface_count,
        h0_equals_h3_count=gd.h0_equals_h3_count,
        donor_inspection=donor_res,
        check_group_a_bright_monitoring_lcd_shotmark=ga,
        check_group_b_zero_bt_tclink_wifi_usblan_airplane=gb,
        check_group_c_big6_home_manual_nd_framing_interval=gc,
        check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0=gd,
        warnings=gd.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwBrightMonShotMarkBig6HomeAndSshAuthReport(
        **{
            **provisional.to_dict(),
            "donor_inspection": donor_res,
            "check_group_a_bright_monitoring_lcd_shotmark": ga,
            "check_group_b_zero_bt_tclink_wifi_usblan_airplane": gb,
            "check_group_c_big6_home_manual_nd_framing_interval": gc,
            "check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0": gd,
            "warnings": gd.warnings,
            "remediation_actions": tuple(remediations),
            "errors": tuple(all_errors),
            "report_sha256": digest,
        }
    )


run_bright_mon_shotmark_big6_home_and_ssh_auth_preflight = (
    evaluate_realhw_bright_mon_shotmark_big6_home_and_ssh_auth_preflight
)


def verify_phase316_report(payload: Mapping[str, Any]) -> Phase316ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 316 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_316_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("schema_version") != PHASE_316_SCHEMA:
        errors.append(f"Invalid schema_version: {payload.get('schema_version')!r}")
    if payload.get("phase_version") != PHASE_316_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_316_VALID_GO_NO_GO_VALUES:
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
        "slot1_tier0_vault_mutated",
        "rf_nvs_p12_p13_writes_authorized",
        "fx3_bt_tc_link_present",
        "fx3_auto_framing_present",
        "fx3_bulb_timer_present",
        "fx3_auto_hdr_present",
        "fx3_in_camera_divide_extract_present",
        "fx3_physical_e_nd_present",
        "fx3_fan_control_max_present",
        "fx6_fan_control_max_present",
    ):
        if payload.get(lock_key) is not False:
            errors.append(f"Safety lock violated: {lock_key}={payload.get(lock_key)!r}")

    for zero_key in (
        "e_nd_actuator_tx_count",
        "wireless_rf_packets_emitted",
        "rf_packets_transmitted",
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
        payload.get("overall_status") != P316_OVERALL_READY_OFFLINE_AWAITING_BENCH_RECEIPTS
    ):
        errors.append(
            "Offline awaiting-receipt verdict must carry overall_status=READY_OFFLINE_AWAITING_BENCH_RECEIPTS"
        )

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go") == P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if payload.get("go_no_go") == P316_GO_NO_GO_BRIGHT_MON_SHOTMARK_BIG6_SSH_AUTH_VERIFIED and (
        payload.get("all_4_check_groups_passed") is not True
        or payload.get("tier0_receipt_verified") is not True
    ):
        errors.append("Verified verdict requires all 4 check groups and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase316ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase316_markdown(
    report: RealHwBrightMonShotMarkBig6HomeAndSshAuthReport,
) -> str:
    """Render concise deterministic Markdown summary for Phase 316 13th physical bench preflight."""
    ga = report.check_group_a_bright_monitoring_lcd_shotmark
    gb = report.check_group_b_zero_bt_tclink_wifi_usblan_airplane
    gc = report.check_group_c_big6_home_manual_nd_framing_interval
    gd = report.check_group_d_tc_regen_hdmi_rec_ssh_auth_zero_fan_tier0
    lines = [
        f"# Phase 316 13th Physical Bench Readiness (`{report.schema_version}`)",
        "",
        f"- **OVERALL**: `{report.overall_status}` (`go_no_go={report.go_no_go}`, mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Check Groups**: `{report.check_groups_passed}/{report.check_group_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `ready_attach={report.overall_ready_for_hardware_attach}`, `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `cross_model_flash={report.cross_model_flash_authorized}`, `bt_tc_link={report.fx3_bt_tc_link_present}`, `auto_framing={report.fx3_auto_framing_present}`, `bulb_timer={report.fx3_bulb_timer_present}`, `auto_hdr={report.fx3_auto_hdr_present}`, `divide_extract={report.fx3_in_camera_divide_extract_present}`, `e_nd={report.fx3_physical_e_nd_present}`, `fx3_fan_max={report.fx3_fan_control_max_present}`, `fx6_fan_max={report.fx6_fan_control_max_present}`, `slot1_mutated={report.slot1_tier0_vault_mutated}`, `e_nd_tx={report.e_nd_actuator_tx_count}`, `rf_pkts={report.rf_packets_transmitted}`, `slot1_writes={report.slot1_data_sector_writes}`, `usb_pkts={report.usb_packets_transmitted}`, `passive_tx={report.passive_tx_bytes_emitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Check Group | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{ga.check_group_id}` | `{'PASS' if ga.passed else 'FAIL'}` | BrightMon=`{ga.bright_monitoring_active}`, LCD=`{ga.monitor_brightness_mode}({ga.monitor_brightness_level})`, ClipFlag=`{ga.clip_flag}`, BULB=`{ga.bulb_enabled}`, DRO=`{ga.dro_mode}`, Slot1Guard=`{ga.slot1_vault_firewall_enforced}` |",
        f"| `{gb.check_group_id}` | `{'PASS' if gb.passed else 'FAIL'}` | BT_TCLink=`{gb.fx3_bt_tc_link_present}`, VMC_EXT_LK=`{gb.vmc_bncm1_ext_lk_active}`, SKU=`{gb.wifi_sku}`, Sec=`{gb.wifi_security_protocol}`, USB_LAN=`{gb.usb_lan_cnct_launch}` (`{gb.usb_lan_kernel_module_count} ko`), Airplane=`{gb.airplane_mode}` |",
        f"| `{gc.check_group_id}` | `{'PASS' if gc.passed else 'FAIL'}` | Mode=`{gc.mode_settings}`, BIG6=`{gc.big6_tile_count} tiles ({gc.home_lower_left_mode})`, e_ND=`{gc.fx3_physical_e_nd_present}`, Framing=`{gc.framing_enabled}` (AutoFraming=`{gc.fx3_auto_framing_present}`), Interval=`{gc.interval_param_count} params/{gc.interval_num_shots} shots`, Slot1Guard=`{gc.slot1_interval_vault_firewall_enforced}` |",
        f"| `{gd.check_group_id}` | `{'PASS' if gd.passed else 'FAIL'}` | TC=`{gd.tc_make}/{gd.tc_run}`, HDMI_REC=`{gd.hdmi_rec_control}`, Auth=`{gd.access_authen}/{gd.access_authen_protocol}`, Fan=`FX3:{gd.fx3_fan_control}/FX6:{gd.fx6_fan_control}` (Max=`{gd.fx3_fan_control_max_present}/{gd.fx6_fan_control_max_present}`), H0==H3=`{gd.h0_equals_h3_count}/{gd.h0_h3_surface_count}`, Tier0=`{gd.tier0_receipt_verified}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
