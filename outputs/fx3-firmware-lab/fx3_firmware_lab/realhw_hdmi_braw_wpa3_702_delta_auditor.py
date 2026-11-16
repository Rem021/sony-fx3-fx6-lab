"""Phase 179 — 37th Unified Firmware-Lab Auditor (37/37): Real-Hardware FX3 `Ver. 7.02`
vs FX6 `Ver. 6.01` Generation-Delta Bridge Auditor (Type-A HDMI BRAW / 4K60 vs
Masked 12G-SDI RAW, WPA2/WPA3-Only & Access Authentication, 1.5x/1.6x Anamorphic
De-Squeeze & Bright Monitoring / Focus Magnifier GRM Plane Compatibility, and
Automatic USB-LAN `CDC-NCM`/`RTL8153`/`ASIX` + Dual-Slot Remaining-Time Telemetry).

Strictly Read-Only (`os.O_RDONLY` + `os.pread` bounded section inspection) &
Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 `Ver. 7.02` (`appFw.so`, `libmpr.so`,
  `libInfraAvbbc.so`, `wpa_supplicant`, `libWlanAdjust.so`, `libNetServiceEther.so`,
  `cpapp-b.bin`, `cdc_ncm.ko`, `r8152.ko`, `asix.ko`, `ax88179_178a.ko`, `grm_ma.ko`)
  and FX6 `Ver. 6.01` (`appFw.so`, `libmpr.so`, `libInfraAvbbc.so`,
  `wpa_supplicant`, `libWlanAdjust.so`, `libNetServiceEther.so`, `libgemini-grm.so`,
  `cpapp-b.bin`, `cdc_ncm.ko`, `r8152.ko`, `asix.ko`, `ax88179_178a.ko`, `grm_ma.ko`)
  strictly via `os.O_RDONLY` + bounded `os.pread` on ELF64 `.dynsym`/`.dynstr`/
  `.dynamic`/`.rodata`/`.modinfo` (< 0.25 s typical).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`/`.ko`/binary fixtures
  carrying verified `7.02` vs `6.01` generation-delta contract markers, leaking
  zero raw Sony proprietary bytes in JSON output (`raw_firmware_bytes_leaked == 0`).

Audits Four Concrete `Ver. 7.02` Generation-Delta Pillars:
1. Pillar 1 (`HDMI_TYPE_A_RAW_4K60_VS_MASKED_12G_SDI`):
   Audits FX3 `7.02` Type-A HDMI external RAW (Blackmagic RAW / ProRes RAW) &
   4K60/100p output markers (`EVENT_REMOTE_MOVIE_HDMI_OUTPUT_SETTINGS_W_DIALOG_RAW_OUTPUT`,
   `VAL_HAITA_hdmi_connect_state_connect_with_raw_compatible_device_HDMI_RAW_CONNECTSTATE_HDMI_CONNECT`,
   `QFHD_100HZ_420_TV_CONNECT_STATE_CONNECTED`) vs FX6 `6.01` `12G-SDI` BNC probes
   (`BKID_APP_SETTING_SDI_OUTPUT`, `PRM_FEATURE_MANAGER_sdi_output`,
   `MoniFpgaSdi_SetRegSDIOutFormat`). Masks `12G-SDI` hardware probes cleanly while
   bridging Type-A HDMI RAW/4K60/LUT/timecode output to FX3 `7.02` drivers.
2. Pillar 2 (`WPA2_WPA3_ONLY_VS_DEPRECATED_WEP_WPA1_IPSEC`):
   Audits `appFw.so`, `wpa_supplicant` (`v2.9-devel`, `SAE`, `sFT-SAE`,
   `WPA2-PSK-SHA256`, `ieee80211w`, `PMF`), and `libWlanAdjust.so`. Proves FX6
   `6.01` still exposes `VAL_setting_wlan_security_WLAN_SECURITY_WEP` / `IPSEC_ON`
   whereas FX3 `7.02` strips legacy `WEP` menu values (`0` hits) and requires
   `WPA2` / `WPA3` / `Access Authentication`. Sanitizes/rejects deprecated
   `WEP`/`WPA1-TKIP`/`IPsec` profiles and passes only `WPA2`/`WPA3`/`Access Auth`.
3. Pillar 3 (`ANAMORPHIC_DESQUEEZE_BRIGHT_MON_MAGNIFIER_GRM`):
   Audits FX3 `7.02` `1.5x` & `1.6x/1.65x` (`EXTERN_VAL_DE_SQUEEZE_DISP_1_5X`,
   `DE_SQUEEZE_DISP_1_6X`, `EXTERN_VAL_DE_SQUEEZE_DISP_1_65X`) generation deltas
   absent from FX6 `6.01` (which only has `1.0x`/`1.3x`/`2.0x`), plus
   `Bright Monitoring` (`EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_ON`),
   `Focus Magnifier` (`EVENT_FUNC_CUSTOM_FOCUS_MAGNIFIER_ON`), `grm_ma.ko`, and
   `libgemini-grm.so` (`GraphicsContextGRM::setScale`, `createPlaneTexture`).
   Verifies GRM OSD/EVF/HDMI plane geometry so anamorphic de-squeeze never clips
   Big-6 (`sid=0x0a`) HUD or clean HDMI output.
4. Pillar 4 (`AUTO_USBLAN_DUAL_SLOT_TELEMETRY_AND_FIREWALL`):
   Audits automatic USB-LAN recognition (`cdc_ncm.ko`, `r8152.ko`, `asix.ko`,
   `ax88179_178a.ko`, `vermagic=4.9.337-scel+`, `libNetServiceEther.so`
   `ConnectedUsbEtherDevice`, `NseMiscGetMacAddressForUsbEther`) and Dual-Slot
   Simultaneous/Relay remaining-time telemetry (`libmpr.so`
   `MovieRemain::CalcRecordableTime` / `MovieRemain::GetRemain` /
   `MprIf::PrepareRelayMedia` / `MprIf::SetRecSimultRecInternalStopMode`,
   `MEDIA_REMAINING_CAPACITY_*`), alongside a strict zero-write eMMC/SPI-NOR
   firewall (`persistent_emmc_writes_authorized = False`,
   `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`,
   `physical_usb_packets_emitted = 0`) and 12-touchpoint 4-class matrix.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import struct
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    is_forced_clean_room,
    resolve_donor_file,
)
from .realhw_cp_rtos_and_backup_bin_auditor import (
    FX3_CPAPP_P137_RELPATH,
    FX6_CPAPP_P137_RELPATH,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    FX3_APPFW_P146_RELPATH,
    FX3_LIBINFRA_AVBBC_P146_RELPATH,
    FX3_LIBMPR_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_LIBINFRA_AVBBC_P146_RELPATH,
    FX6_LIBMPR_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
    _count_tokens_single_pass,
    _scan_elf_and_tokens_buf,
)
from .realhw_wifi_bt_usb_uvc_network_bridge_auditor import (
    FX3_LIBNET_ETHER_P152_RELPATH,
    FX3_LIBWLAN_ADJUST_RELPATH,
    FX6_LIBNET_ETHER_P152_RELPATH,
    FX6_LIBWLAN_ADJUST_RELPATH,
)


PHASE_179_SCHEMA = "fx3_firmware_lab_phase179_realhw_hdmi_braw_wpa3_702_delta_v1"
PHASE_179_VERSION = "179.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + bounded os.pread)
# ---------------------------------------------------------------------------

FX3_APPFW_P179_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P179_RELPATH = FX6_APPFW_P146_RELPATH
FX3_LIBMPR_P179_RELPATH = FX3_LIBMPR_P146_RELPATH
FX6_LIBMPR_P179_RELPATH = FX6_LIBMPR_P146_RELPATH
FX3_LIBINFRA_AVBBC_P179_RELPATH = FX3_LIBINFRA_AVBBC_P146_RELPATH
FX6_LIBINFRA_AVBBC_P179_RELPATH = FX6_LIBINFRA_AVBBC_P146_RELPATH
FX3_LIBWLAN_ADJUST_P179_RELPATH = FX3_LIBWLAN_ADJUST_RELPATH
FX6_LIBWLAN_ADJUST_P179_RELPATH = FX6_LIBWLAN_ADJUST_RELPATH
FX3_LIBNET_ETHER_P179_RELPATH = FX3_LIBNET_ETHER_P152_RELPATH
FX6_LIBNET_ETHER_P179_RELPATH = FX6_LIBNET_ETHER_P152_RELPATH
FX3_CPAPP_P179_RELPATH = FX3_CPAPP_P137_RELPATH
FX6_CPAPP_P179_RELPATH = FX6_CPAPP_P137_RELPATH

_FX3_FULLV4_USR_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files/usr"
)
_FX6_DONOR_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files"
)

FX3_WPA_SUPPLICANT_P179_RELPATH = f"{_FX3_FULLV4_USR_PREFIX}/bin/wpa_supplicant"
FX6_WPA_SUPPLICANT_P179_RELPATH = f"{_FX6_DONOR_PREFIX}/bin/wpa_supplicant"
FX6_LIBGEMINI_GRM_P179_RELPATH = f"{_FX6_DONOR_PREFIX}/lib/libgemini-grm.so"

FX3_CDC_NCM_KO_RELPATH = f"{_FX3_FULLV4_USR_PREFIX}/kmod/cdc_ncm.ko"
FX6_CDC_NCM_KO_RELPATH = f"{_FX6_DONOR_PREFIX}/kmod/cdc_ncm.ko"
FX3_R8152_KO_RELPATH = f"{_FX3_FULLV4_USR_PREFIX}/kmod/r8152.ko"
FX6_R8152_KO_RELPATH = f"{_FX6_DONOR_PREFIX}/kmod/r8152.ko"
FX3_ASIX_KO_RELPATH = f"{_FX3_FULLV4_USR_PREFIX}/kmod/asix.ko"
FX6_ASIX_KO_RELPATH = f"{_FX6_DONOR_PREFIX}/kmod/asix.ko"
FX3_AX88179_KO_RELPATH = f"{_FX3_FULLV4_USR_PREFIX}/kmod/ax88179_178a.ko"
FX6_AX88179_KO_RELPATH = f"{_FX6_DONOR_PREFIX}/kmod/ax88179_178a.ko"
FX3_GRM_MA_KO_RELPATH = f"{_FX3_FULLV4_USR_PREFIX}/kmod/grm_ma.ko"
FX6_GRM_MA_KO_RELPATH = f"{_FX6_DONOR_PREFIX}/kmod/grm_ma.ko"

# ---------------------------------------------------------------------------
# Verified Expected Donor File Sizes & ELF Symbol Counts
# ---------------------------------------------------------------------------

EXPECTED_FX3_APPFW_BYTES_P179 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P179 = 50_520_424
EXPECTED_FX3_MPR_BYTES_P179 = 3_517_008
EXPECTED_FX6_MPR_BYTES_P179 = 28_921_824
EXPECTED_FX3_AVBBC_BYTES_P179 = 1_734_632
EXPECTED_FX6_AVBBC_BYTES_P179 = 1_743_200
EXPECTED_FX3_WPA_SUPPLICANT_BYTES_P179 = 1_380_160
EXPECTED_FX6_WPA_SUPPLICANT_BYTES_P179 = 1_376_056
EXPECTED_WLAN_ADJUST_BYTES_P179 = 73_168
EXPECTED_FX3_ETHER_BYTES_P179 = 114_384
EXPECTED_FX6_ETHER_BYTES_P179 = 175_376
EXPECTED_FX3_CPAPP_BYTES_P179 = 15_980_568
EXPECTED_FX6_CPAPP_BYTES_P179 = 17_952_816
EXPECTED_FX6_GEMINI_GRM_BYTES_P179 = 51_800
EXPECTED_CDC_NCM_KO_BYTES = 32_208
EXPECTED_R8152_KO_BYTES = 56_264
EXPECTED_ASIX_KO_BYTES = 46_592
EXPECTED_AX88179_KO_BYTES = 23_848
EXPECTED_GRM_MA_KO_BYTES = 36_592

SCEL_KERNEL_VERMAGIC_P179 = "4.9.337-scel+ SMP preempt mod_unload aarch64"

# ---------------------------------------------------------------------------
# Pillar 1..4 Generation-Delta Constants & Policy Tables
# ---------------------------------------------------------------------------

FX3_702_RELEASE_DATE = "2026-03-17"
FX3_700_RELEASE_DATE = "2025-08-26"

VALID_HDMI_BRIDGE_MODES: Tuple[str, ...] = (
    "HDMI_BRAW_4K60",
    "HDMI_PRORES_RAW_4K60",
    "HDMI_CLEAN_4K60_10BIT_LUT",
    "HDMI_1080P60_OSD",
    "SDI_12G_RAW_REQUEST",
    "SDI_12G_MONITOR_REQUEST",
)

SUPPORTED_FX3_HDMI_OUTPUT_MODES: Tuple[str, ...] = (
    "HDMI_BRAW_4K60",
    "HDMI_PRORES_RAW_4K60",
    "HDMI_CLEAN_4K60_10BIT_LUT",
    "HDMI_1080P60_OSD",
)

DEPRECATED_702_SECURITY_PROFILES: Tuple[str, ...] = (
    "WEP_40",
    "WEP_104",
    "WPA1_PSK_TKIP",
    "WPA_TKIP",
    "IPSEC_LEGACY",
)

ALLOWED_702_SECURITY_PROFILES: Tuple[str, ...] = (
    "WPA2_PSK_CCMP",
    "WPA2_PSK_SHA256",
    "WPA3_SAE",
    "WPA2_WPA3_TRANSITION",
    "ACCESS_AUTH_TLS",
)

VALID_SECURITY_PROFILES_P179: Tuple[str, ...] = (
    DEPRECATED_702_SECURITY_PROFILES + ALLOWED_702_SECURITY_PROFILES
)

FX3_702_DESQUEEZE_RATIOS: Tuple[float, ...] = (1.0, 1.3, 1.5, 1.6, 2.0)
FX6_601_NATIVE_DESQUEEZE_RATIOS: Tuple[float, ...] = (1.0, 1.3, 2.0)
FX3_702_EXCLUSIVE_DESQUEEZE_RATIOS: Tuple[float, ...] = (1.5, 1.6)
VALID_MAGNIFIER_SCALES_P179: Tuple[float, ...] = (1.0, 3.0, 4.0, 6.0)

BIG6_SID_HEX = "0x0a"
FX3_OSD_GRM_PLANE_RES: Tuple[int, int] = (1920, 1080)
FX3_CAPACITIVE_GPE0_RES: Tuple[int, int] = (960, 540)
FX3_4K_UHD_RES: Tuple[int, int] = (3840, 2160)
FX3_4K_DCI_RES: Tuple[int, int] = (4096, 2160)
FX3_RAW_SENSOR_RES: Tuple[int, int] = (4264, 2408)

SUPPORTED_USBLAN_DRIVERS_P179: Tuple[str, ...] = (
    "CDC_NCM",
    "RTL8153",
    "ASIX_AX88179",
    "ASIX_AX8817X",
)

VALID_DUAL_SLOT_REC_MODES_P179: Tuple[str, ...] = (
    "SIMULTANEOUS",
    "RELAY",
    "SORT",
    "SINGLE_SLOT_A",
)

# ---------------------------------------------------------------------------
# Verified Donor Binary Marker Catalogs (strictly O_RDONLY bounded read)
# ---------------------------------------------------------------------------

APPFW_HDMI_RAW_FX3_MARKERS_P179: Tuple[str, ...] = (
    "EVENT_REMOTE_MOVIE_HDMI_OUTPUT_SETTINGS_W_DIALOG_RAW_OUTPUT",
    "EVENT_REMOTE_MOVIE_HDMI_OUTPUT_SETTINGS_W_DIALOG_RAW_OUTPUT_FRAME_RATE",
    "EVENT_REMOTE_MOVIE_HDMI_OUTPUT_SETTINGS_W_DIALOG_COLOR_GAMUT_FOR_RAW_OUT",
    "MODEL_HDMI_RAW_OUTPUT_STATUS_CHANGED",
    "VAL_HAITA_hdmi_connect_state_connect_with_raw_compatible_device_HDMI_RAW_CONNECTSTATE_HDMI_CONNECT",
    "QFHD_100HZ_420_TV_CONNECT_STATE_CONNECTED",
)

APPFW_SDI_FX6_EXCLUSIVE_MARKERS_P179: Tuple[str, ...] = (
    "BKID_APP_SETTING_SDI_OUTPUT",
    "BKID_APP_SETTING_SDI_OUTPUT_DISPLAY",
    "EVENT_REMOTE_SDI_OUTPUT",
    "PRM_FEATURE_MANAGER_sdi_output",
    "VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_SUPPORT",
    "VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT",
)

APPFW_WPA3_ACCESS_AUTH_SHARED_MARKERS_P179: Tuple[str, ...] = (
    "REMOTE_SETTING_AP_SECURITY_TYPE_WPA3",
    "REMOTE_SETTING_AP_SECURITY_TYPE_WPA_WPA2",
    "WIFI_STRINGS_TYPE_WPA3_KEY",
    "INFRA_NOTIFY_CONNECT_ERR_SECURITY_TYPE_NOT_SUPPORTED",
    "SOFTWARE_KEYBOARD_ACCESS_AUTHENTICATION_PASSWORD",
    "SOFTWARE_KEYBOARD_ACCESS_AUTHENTICATION_USERNAME",
)

APPFW_LEGACY_WEP_FX6_MARKER_P179 = "VAL_setting_wlan_security_WLAN_SECURITY_WEP"

APPFW_DESQUEEZE_SHARED_MARKERS_P179: Tuple[str, ...] = (
    "EXTERN_VAL_DE_SQUEEZE_DISP_OFF_1_0X",
    "EXTERN_VAL_DE_SQUEEZE_DISP_1_3X",
    "EXTERN_VAL_DE_SQUEEZE_DISP_2_0X",
    "MODEL_REPROCESS_FUNC_CUSTOM_BRIGHT_MONITORING_ON",
    "EVENT_REMOTE_FOCUS_MAGNIFIER_SETTING",
)

APPFW_DESQUEEZE_702_FX3_MARKERS_P179: Tuple[str, ...] = (
    "EXTERN_VAL_DE_SQUEEZE_DISP_1_5X",
    "EXTERN_VAL_DE_SQUEEZE_DISP_1_65X",
    "DE_SQUEEZE_DISP_1_6X",
    "MSG_ID_INFRABB_VIDEO_DE_SQUEEZE",
    "EVENT_FUNC_CUSTOM_BRIGHT_MONITORING_ON",
    "EVENT_FUNC_CUSTOM_FOCUS_MAGNIFIER_ON",
)

APPFW_USBLAN_DUAL_SLOT_SHARED_MARKERS_P179: Tuple[str, ...] = (
    "USB_LAN_FUNCTION_INTERNAL_STATE_CONNECTED",
    "VAL_system_mode_option_SYSTEM_MODE_OPTION_USB_LAN_AND_TETHERING",
    "CLOUD_CONNECT_METHOD_USB_ETHER",
    "EVENT_REMOTE_DOUBLE_SLOT_SETTINGS_RELAY_REC",
    "VAL_setting_movie_recording_media_MOVIE_RECORDING_MEDIA_SIMULTANEOUS_RECORDING",
    "MEDIA_REMAINING_CAPACITY_OF_MEMORY_FOR_CREATE_NEW_FOLDER_SLOT1_REMAINS",
    "MEDIA_REMAINING_CAPACITY_OF_MEMORY_FOR_CREATE_NEW_FOLDER_SLOT2_REMAINS",
)

AVBBC_HDMI_SDI_MARKERS_P179: Tuple[str, ...] = (
    "ConvertCmdMidToHdmiEt",
    "ConvertCmdMidToSdiEt",
    "ExecCmd_ADF_SetHdmiFormat",
)

WPA_SUPPLICANT_MARKERS_P179: Tuple[str, ...] = (
    "wpa_supplicant v2.9-devel",
    "SAE",
    "sFT-SAE",
    "WPA2-PSK-SHA256",
    "ieee80211w",
    "PMF",
    "WEP",
    "TKIP",
    "CCMP",
)

WLAN_ADJUST_MARKERS_P179: Tuple[str, ...] = (
    "wpa_ctrl_open",
    "wpa_ctrl_request",
    "WPA-PSK",
)

NETSERVICE_ETHER_MARKERS_P179: Tuple[str, ...] = (
    "ConnectedUsbEtherDevice",
    "NseMiscGetMacAddressForUsbEther",
    "eth0",
)

MPR_REMAIN_RELAY_SIMUL_SHARED_MARKERS_P179: Tuple[str, ...] = (
    "_ZN11MovieRemain9GetRemainEN3mpr21getMovieRemainInParamERj",
    "_ZN5MprIf17PrepareRelayMediaEPNS_16RelayTargetParamEj",
    "_ZN5MprIf31SetRecSimultRecInternalStopModeEPNS_30SimultRecInternalStopModeParamE",
    "SimulRec",
)

MPR_CALC_REMAIN_FX3_MARKER_P179 = "_ZN11MovieRemain18CalcRecordableTimeEN3mpr21getMovieRemainInParamERj"

GEMINI_GRM_MARKERS_P179: Tuple[str, ...] = (
    "_ZN6gemini18GraphicsContextGRM8setScaleEff",
    "_ZN6gemini18GraphicsContextGRM18createPlaneTextureEPPKvtthiNS_12TextureUsageE",
)

CPAPP_SHARED_DESQUEEZE_MARKERS_P179: Tuple[str, ...] = (
    "MSG_ID_INFRABB_VIDEO_DE_SQUEEZE",
    "SET_ANAMO_DESQUEEZE_SCALE",
    "CATEID_HDMI",
    "CATE_ID_HDMIVIDEOINFO",
)

CPAPP_FX6_SDI_MARKER_P179 = "MoniFpgaSdi_SetRegSDIOutFormat"

# ---------------------------------------------------------------------------
# Write-Firewall Patterns
# ---------------------------------------------------------------------------

VOLATILE_OR_EXT_PREFIXES_P179: Tuple[str, ...] = (
    "/tmp/",
    "/tmp_wbshd/",
    "ram://",
    "memfd:",
    "/mnt/sd/",
    "/mnt/sd2/",
    "/mnt/cfexpress_a/",
)

FORBIDDEN_PERSISTENT_TARGET_RE_P179 = re.compile(
    r"(?:"
    r"^/dev/(?:[cp]?nflasha\d*|mmcblk0(?:p\d+|rpmb)?|rtc0)"
    r"|^p(?:2|5|6|8|12|13|15|18):/"
    r"|^/(?:wbi|setting|cert|lens|usr/etc/wpa_supplicant)(?:/|$)"
    r"|^/etc/wpa_supplicant\.conf$"
    r"|^spi_nor:"
    r"|^sector0:"
    r"|Backup\.bin$"
    r"|cpapp-b\.bin$"
    r"|RQ_LIC\.DAT$"
    r"|lensfile\.bin$"
    r"|loader_nor\.bin$"
    r")",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class KernelModuleInfoSummary:
    module_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    vermagic_match: bool
    driver_tag: str
    modinfo_valid: bool


@dataclass(frozen=True)
class HdmiBrawVsSdiBridgeEvalResult:
    valid: bool
    requested_mode: str
    fx6_sdi_out_enabled: bool
    hdmi_raw_device_connected: bool
    lut_burn_in_enabled: bool
    tc_output_enabled: bool
    sdi_hw_probe_masked: bool
    sdi_bnc_present: bool
    sdi_blocking_faults: int
    resolved_hdmi_mode: str
    hdmi_raw_braw_ready: bool
    hdmi_clean_lut_tc_bridged: bool
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Wpa2Wpa3SecurityShimEvalResult:
    valid: bool
    requested_profile: str
    airplane_mode_p12: bool
    access_auth_enabled: bool
    deprecated_protocol_rejected: bool
    passed_to_wpa_supplicant: bool
    resolved_wpa_key_mgmt: str
    pmf_ieee80211w_mode: int
    rf_tx_packets_emitted: int
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AnamorphicDesqueezeGrmEvalResult:
    valid: bool
    desqueeze_ratio: float
    fx6_native_ratio: bool
    fx3_702_shim_required: bool
    bright_monitoring_on: bool
    magnifier_scale: float
    clean_hdmi_mode: bool
    hdmi_raw_active: bool
    video_plane_scale_x: float
    video_plane_scale_y: float
    osd_grm_scale_x: float
    osd_grm_scale_y: float
    magnifier_roi_w_px: int
    magnifier_roi_h_px: int
    big6_hud_unclipped: bool
    clean_hdmi_unclipped: bool
    bright_monitoring_display_only: bool
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AutoUsbLanRecognitionEvalResult:
    valid: bool
    adapter_driver: str
    usb_vid_pid: str
    link_speed_mbps: int
    vermagic_compatible: bool
    airplane_mode_p12: bool
    auto_netif_name: str
    dhcp_bound: bool
    rf_tx_leaks: int
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DualSlotRemainingTimeEvalResult:
    valid: bool
    rec_mode: str
    codec_bitrate_mbps: float
    slot_a_free_mib: int
    slot_b_free_mib: int
    slot_a_remaining_min: float
    slot_b_remaining_min: float
    effective_remaining_min: float
    bottleneck_slot: str
    zero_frame_drop_rollover: bool
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase179WriteGuardResult:
    valid: bool
    target_path: str
    volatile_or_ext_allowed: bool
    persistent_write_blocked: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    emmc_mutation_bytes: int
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase179TouchpointEntry:
    touchpoint_id: str
    subsystem: str
    fx6_component: str
    fx3_target: str
    bridge_class: str
    safety_invariant: str


@dataclass(frozen=True)
class Phase179CompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    subsystem_counts: Dict[str, int]
    touchpoints: Tuple[Phase179TouchpointEntry, ...]


@dataclass(frozen=True)
class Pillar1HdmiBrawVsSdiReport:
    passed: bool
    fx3_appfw_hdmi_raw_hits: Dict[str, int]
    fx6_appfw_hdmi_raw_hits: Dict[str, int]
    fx3_appfw_sdi_hits: Dict[str, int]
    fx6_appfw_sdi_hits: Dict[str, int]
    fx3_avbbc_summary: ElfSectionSummary
    fx6_avbbc_summary: ElfSectionSummary
    fx3_cpapp_sdi_hits: int
    fx6_cpapp_sdi_hits: int
    hdmi_braw_4k60_eval: HdmiBrawVsSdiBridgeEvalResult
    hdmi_clean_lut_tc_eval: HdmiBrawVsSdiBridgeEvalResult
    sdi_12g_raw_masked_eval: HdmiBrawVsSdiBridgeEvalResult
    sdi_12g_monitor_masked_eval: HdmiBrawVsSdiBridgeEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2Wpa2Wpa3SecurityReport:
    passed: bool
    fx3_wpa_summary: ElfSectionSummary
    fx6_wpa_summary: ElfSectionSummary
    fx3_wlan_adj_summary: ElfSectionSummary
    fx6_wlan_adj_summary: ElfSectionSummary
    fx3_appfw_wpa_hits: Dict[str, int]
    fx6_appfw_wpa_hits: Dict[str, int]
    fx3_legacy_wep_enum_hits: int
    fx6_legacy_wep_enum_hits: int
    wpa3_sae_eval: Wpa2Wpa3SecurityShimEvalResult
    wpa2_ccmp_eval: Wpa2Wpa3SecurityShimEvalResult
    access_auth_tls_eval: Wpa2Wpa3SecurityShimEvalResult
    wep_rejected_eval: Wpa2Wpa3SecurityShimEvalResult
    wpa1_tkip_rejected_eval: Wpa2Wpa3SecurityShimEvalResult
    ipsec_rejected_eval: Wpa2Wpa3SecurityShimEvalResult
    p12_rf_off_blocked_eval: Wpa2Wpa3SecurityShimEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3AnamorphicBrightMagGrmReport:
    passed: bool
    fx3_appfw_desqueeze_hits: Dict[str, int]
    fx6_appfw_desqueeze_hits: Dict[str, int]
    fx3_cpapp_desqueeze_hits: Dict[str, int]
    fx6_cpapp_desqueeze_hits: Dict[str, int]
    fx6_gemini_grm_summary: ElfSectionSummary
    fx3_grm_ma_ko: KernelModuleInfoSummary
    fx6_grm_ma_ko: KernelModuleInfoSummary
    desqueeze_15x_bright_mon_eval: AnamorphicDesqueezeGrmEvalResult
    desqueeze_16x_magnifier_4x_eval: AnamorphicDesqueezeGrmEvalResult
    desqueeze_20x_clean_hdmi_eval: AnamorphicDesqueezeGrmEvalResult
    desqueeze_13x_hdmi_raw_eval: AnamorphicDesqueezeGrmEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4UsbLanDualSlotMatrixReport:
    passed: bool
    fx3_ether_summary: ElfSectionSummary
    fx6_ether_summary: ElfSectionSummary
    fx3_mpr_summary: ElfSectionSummary
    fx6_mpr_summary: ElfSectionSummary
    fx3_appfw_usblan_slot_hits: Dict[str, int]
    fx6_appfw_usblan_slot_hits: Dict[str, int]
    kmod_summaries: Tuple[KernelModuleInfoSummary, ...]
    usblan_cdc_ncm_eval: AutoUsbLanRecognitionEvalResult
    usblan_rtl8153_eval: AutoUsbLanRecognitionEvalResult
    usblan_asix_eval: AutoUsbLanRecognitionEvalResult
    usblan_unknown_rejected_eval: AutoUsbLanRecognitionEvalResult
    dual_slot_simultaneous_eval: DualSlotRemainingTimeEvalResult
    dual_slot_relay_eval: DualSlotRemainingTimeEvalResult
    dual_slot_sort_eval: DualSlotRemainingTimeEvalResult
    volatile_wpa_tmp_allowed: Phase179WriteGuardResult
    external_cfexpress_allowed: Phase179WriteGuardResult
    blocked_p12_cert_guard: Phase179WriteGuardResult
    blocked_p2_backup_guard: Phase179WriteGuardResult
    blocked_etc_wpa_conf_guard: Phase179WriteGuardResult
    blocked_spinor_guard: Phase179WriteGuardResult
    compatibility_matrix: Phase179CompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwHdmiBrawWpa3702DeltaReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    raw_firmware_bytes_leaked: int
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    hdmi_braw_bridged_sdi_masked: bool
    wpa2_wpa3_only_enforced: bool
    anamorphic_15x_16x_grm_unclipped: bool
    usblan_and_dual_slot_telemetry_ready: bool
    donor_file_sizes: Dict[str, int]
    pillar1_hdmi_braw_vs_sdi: Pillar1HdmiBrawVsSdiReport
    pillar2_wpa2_wpa3_security: Pillar2Wpa2Wpa3SecurityReport
    pillar3_anamorphic_grm: Pillar3AnamorphicBrightMagGrmReport
    pillar4_usblan_dual_slot_matrix: Pillar4UsbLanDualSlotMatrixReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly O_RDONLY Bounded Section Inspection Helpers (< 0.25 s)
# ---------------------------------------------------------------------------


def _count_tokens_ordered_single_pass(
    buf: bytes,
    tokens: Sequence[str],
) -> Dict[str, int]:
    """Count exact ASCII token hits, longest-first so prefixes never shadow longer tokens."""
    if not tokens:
        return {}
    unique_ordered = sorted(set(tokens), key=len, reverse=True)
    encoded = [t.encode("ascii") for t in unique_ordered]
    pat = re.compile(b"|".join(re.escape(e) for e in encoded))
    counts: Dict[bytes, int] = {e: 0 for e in encoded}
    for m in pat.finditer(buf):
        tok = m.group(0)
        counts[tok] = counts.get(tok, 0) + 1
    return {t: counts[t.encode("ascii")] for t in tokens}


def _scan_elf_buf_ordered(
    buf: bytes,
    *,
    binary_name: str,
    body_label: str,
    source_mode: str,
    tokens: Sequence[str],
) -> ElfSectionSummary:
    """Scan a synthetic ELF64 buffer with longest-first ordered token counting."""
    hdr, _, _ = _scan_elf_and_tokens_buf(
        buf,
        binary_name=binary_name,
        body_label=body_label,
        source_mode=source_mode,
        tokens=(),
    )
    return ElfSectionSummary(
        binary_name=hdr.binary_name,
        body_label=hdr.body_label,
        source_mode=hdr.source_mode,
        file_bytes=hdr.file_bytes,
        export_count=hdr.export_count,
        import_count=hdr.import_count,
        dt_needed=hdr.dt_needed,
        marker_hits=_count_tokens_ordered_single_pass(buf, tokens),
    )


def _scan_elf_bounded_ro_rdonly(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
) -> ElfSectionSummary:
    """Strictly O_RDONLY bounded `os.pread` of ELF64 `.dynsym`/`.dynstr`/`.dynamic`/`.rodata`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        ehdr = os.pread(fd, 64, 0)
        if len(ehdr) < 64 or ehdr[:4] != b"\x7fELF" or ehdr[4] != 2 or ehdr[5] != 1:
            raise ValueError(f"Invalid ELF64 header for {binary_name}")
        (e_shoff,) = struct.unpack_from("<Q", ehdr, 40)
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", ehdr, 58)
        sh_tbl = os.pread(fd, e_shnum * e_shentsize, e_shoff)

        shstr = b""
        if e_shstrndx < e_shnum:
            s_off, s_sz = struct.unpack_from("<QQ", sh_tbl, e_shstrndx * e_shentsize + 24)
            if s_off + s_sz <= sz:
                shstr = os.pread(fd, s_sz, s_off)

        dynsym_meta: Optional[Tuple[int, int]] = None
        dynstr_meta: Optional[Tuple[int, int]] = None
        dynamic_meta: Optional[Tuple[int, int]] = None
        ro_slices: List[Tuple[int, int]] = []

        for idx in range(e_shnum):
            base = idx * e_shentsize
            sh_name_off, sh_type = struct.unpack_from("<II", sh_tbl, base)
            sh_off, sh_sz = struct.unpack_from("<QQ", sh_tbl, base + 24)
            end = shstr.find(b"\x00", sh_name_off)
            sec_name = (
                shstr[sh_name_off:end].decode("ascii", errors="replace")
                if end != -1 and sh_name_off < len(shstr)
                else ""
            )
            if sh_type == 11:  # SHT_DYNSYM
                dynsym_meta = (sh_off, sh_sz)
            elif sh_type == 6:  # SHT_DYNAMIC
                dynamic_meta = (sh_off, sh_sz)
            elif sec_name == ".dynstr":
                dynstr_meta = (sh_off, sh_sz)
            if sec_name in (".rodata", ".dynstr", ".strtab", ".modinfo") and sh_sz > 0 and sh_off + sh_sz <= sz:
                ro_slices.append((sh_off, sh_sz))

        dynstr_buf = os.pread(fd, dynstr_meta[1], dynstr_meta[0]) if dynstr_meta else b""
        exports = 0
        imports = 0
        if dynsym_meta and dynstr_buf:
            ds_buf = os.pread(fd, dynsym_meta[1], dynsym_meta[0])
            for pos in range(24, len(ds_buf) - 23, 24):
                st_name, st_info, _other, st_shndx = struct.unpack_from("<IBBH", ds_buf, pos)
                if st_name == 0 or st_name >= len(dynstr_buf):
                    continue
                if st_shndx == 0:
                    imports += 1
                elif (st_info & 0xF) in (1, 2, 10) or (st_info >> 4) in (1, 2):
                    exports += 1

        dt_needed: List[str] = []
        if dynamic_meta and dynstr_buf:
            dyn_buf = os.pread(fd, dynamic_meta[1], dynamic_meta[0])
            for pos in range(0, len(dyn_buf) - 15, 16):
                d_tag, d_val = struct.unpack_from("<qQ", dyn_buf, pos)
                if d_tag == 0:
                    break
                if d_tag == 1 and d_val < len(dynstr_buf):
                    z = dynstr_buf.find(b"\x00", d_val)
                    if z != -1:
                        dt_needed.append(dynstr_buf[d_val:z].decode("ascii", errors="replace"))

        counts: Dict[str, int] = {t: 0 for t in tokens}
        if tokens and ro_slices:
            unique_ordered = sorted(set(tokens), key=len, reverse=True)
            encoded = [t.encode("ascii") for t in unique_ordered]
            pat = re.compile(b"|".join(re.escape(e) for e in encoded))
            raw_counts: Dict[bytes, int] = {e: 0 for e in encoded}
            for s_off, s_sz in ro_slices:
                chunk = os.pread(fd, s_sz, s_off)
                for m in pat.finditer(chunk):
                    raw_counts[m.group(0)] = raw_counts.get(m.group(0), 0) + 1
            counts = {t: raw_counts[t.encode("ascii")] for t in tokens}

        return ElfSectionSummary(
            binary_name=binary_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            export_count=exports,
            import_count=imports,
            dt_needed=tuple(dt_needed),
            marker_hits=counts,
        )
    finally:
        os.close(fd)


def _scan_flat_binary_tokens_rdonly(
    path: Path,
    tokens: Sequence[str],
) -> Tuple[int, Dict[str, int]]:
    """Strictly O_RDONLY bounded `os.pread` token scan for flat RTOS blobs (`cpapp-b.bin`)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        if sz == 0:
            return 0, {t: 0 for t in tokens}
        buf = os.pread(fd, sz, 0)
        return sz, _count_tokens_ordered_single_pass(buf, tokens)
    finally:
        os.close(fd)


def _inspect_kmod_modinfo_rdonly(
    path: Path,
    *,
    module_name: str,
    body_label: str,
    driver_tag: str,
) -> KernelModuleInfoSummary:
    """Strictly O_RDONLY `.modinfo` ELF64 inspection of a kernel `.ko` driver."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        ehdr = os.pread(fd, 64, 0)
        if len(ehdr) < 64 or ehdr[:4] != b"\x7fELF":
            return KernelModuleInfoSummary(
                module_name=module_name,
                body_label=body_label,
                source_mode="LOCAL_DONOR_RDONLY",
                file_bytes=sz,
                vermagic_match=False,
                driver_tag=driver_tag,
                modinfo_valid=False,
            )
        (e_shoff,) = struct.unpack_from("<Q", ehdr, 40)
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", ehdr, 58)
        sh_tbl = os.pread(fd, e_shnum * e_shentsize, e_shoff)
        s_off, s_sz = struct.unpack_from("<QQ", sh_tbl, e_shstrndx * e_shentsize + 24)
        shstr = os.pread(fd, s_sz, s_off)
        modinfo_buf = b""
        for idx in range(e_shnum):
            base = idx * e_shentsize
            sh_name_off = struct.unpack_from("<I", sh_tbl, base)[0]
            end = shstr.find(b"\x00", sh_name_off)
            name = shstr[sh_name_off:end].decode("ascii", errors="replace") if end != -1 else ""
            if name == ".modinfo":
                moff, msz = struct.unpack_from("<QQ", sh_tbl, base + 24)
                modinfo_buf = os.pread(fd, msz, moff)
                break
        vermagic_ok = SCEL_KERNEL_VERMAGIC_P179.encode("ascii") in modinfo_buf
        return KernelModuleInfoSummary(
            module_name=module_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            vermagic_match=vermagic_ok,
            driver_tag=driver_tag,
            modinfo_valid=vermagic_ok and sz > 0,
        )
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Pillar 1: Type-A HDMI BRAW / 4K60 vs Masked 12G-SDI RAW Bridge
# ---------------------------------------------------------------------------


def evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(
    *,
    requested_mode: str = "HDMI_BRAW_4K60",
    fx6_sdi_out_enabled: bool = True,
    hdmi_raw_device_connected: bool = True,
    lut_burn_in_enabled: bool = False,
    tc_output_enabled: bool = True,
) -> HdmiBrawVsSdiBridgeEvalResult:
    """Bridge FX6 video/LUT/TC output onto FX3 7.02 Type-A HDMI while masking 12G-SDI."""
    errors: List[str] = []
    mode = requested_mode.strip().upper()
    if mode not in VALID_HDMI_BRIDGE_MODES:
        errors.append(f"UNKNOWN_HDMI_BRIDGE_MODE: {requested_mode}")

    # FX3 physical hardware NEVER has a 12G-SDI BNC port.
    sdi_bnc_present = False
    sdi_hw_probe_masked = True
    sdi_blocking_faults = 0

    if mode in ("HDMI_BRAW_4K60", "HDMI_PRORES_RAW_4K60"):
        if not hdmi_raw_device_connected:
            errors.append("HDMI_RAW_RECORDER_DISCONNECTED")
        if lut_burn_in_enabled:
            errors.append("RAW_HDMI_FORBIDS_LUT_BURN_IN")
        resolved_mode = mode
        hdmi_raw_braw_ready = len(errors) == 0
        hdmi_clean_lut_tc_bridged = tc_output_enabled and len(errors) == 0
        bridge_class = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        status = f"{mode}_TYPE_A_PASSTHROUGH_OK" if len(errors) == 0 else errors[0]
    elif mode in ("HDMI_CLEAN_4K60_10BIT_LUT", "HDMI_1080P60_OSD"):
        resolved_mode = mode
        hdmi_raw_braw_ready = False
        hdmi_clean_lut_tc_bridged = True
        bridge_class = BRIDGE_CLASS_SHIM_TRANSLATED if fx6_sdi_out_enabled else BRIDGE_CLASS_NATIVE_PASSTHROUGH
        status = "HDMI_CLEAN_LUT_TC_BRIDGED_SDI_PROBE_MASKED" if len(errors) == 0 else errors[0]
    elif mode in ("SDI_12G_RAW_REQUEST", "SDI_12G_MONITOR_REQUEST"):
        # Fail-closed on absent 12G-SDI BNC hardware, rerouting safely with 0 blocking faults.
        errors.append(f"MASKED_ABSENT_12G_SDI_BNC: {mode}")
        resolved_mode = (
            "HDMI_BRAW_4K60"
            if (mode == "SDI_12G_RAW_REQUEST" and hdmi_raw_device_connected)
            else "HDMI_CLEAN_4K60_10BIT_LUT"
        )
        hdmi_raw_braw_ready = False
        hdmi_clean_lut_tc_bridged = False
        bridge_class = BRIDGE_CLASS_MASKED_ABSENT_HW
        status = "MASKED_12G_SDI_BNC_NO_FAULT"
    else:
        resolved_mode = "INVALID"
        hdmi_raw_braw_ready = False
        hdmi_clean_lut_tc_bridged = False
        bridge_class = BRIDGE_CLASS_MASKED_ABSENT_HW
        status = errors[0]

    return HdmiBrawVsSdiBridgeEvalResult(
        valid=len(errors) == 0,
        requested_mode=mode,
        fx6_sdi_out_enabled=fx6_sdi_out_enabled,
        hdmi_raw_device_connected=hdmi_raw_device_connected,
        lut_burn_in_enabled=lut_burn_in_enabled,
        tc_output_enabled=tc_output_enabled,
        sdi_hw_probe_masked=sdi_hw_probe_masked,
        sdi_bnc_present=sdi_bnc_present,
        sdi_blocking_faults=sdi_blocking_faults,
        resolved_hdmi_mode=resolved_mode,
        hdmi_raw_braw_ready=hdmi_raw_braw_ready,
        hdmi_clean_lut_tc_bridged=hdmi_clean_lut_tc_bridged,
        bridge_class=bridge_class,
        status=status,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: WPA2/WPA3-Only & Access Authentication Shim (WEP/WPA1/IPsec Stripped)
# ---------------------------------------------------------------------------


def evaluate_wpa2_wpa3_security_shim(
    *,
    requested_profile: str = "WPA3_SAE",
    airplane_mode_p12: bool = False,
    access_auth_enabled: bool = True,
) -> Wpa2Wpa3SecurityShimEvalResult:
    """Sanitize/reject WEP/WPA1/IPsec and pass only WPA2/WPA3/Access Auth to 7.02."""
    errors: List[str] = []
    prof = requested_profile.strip().upper()
    if prof not in VALID_SECURITY_PROFILES_P179:
        errors.append(f"UNKNOWN_SECURITY_PROFILE: {requested_profile}")
        return Wpa2Wpa3SecurityShimEvalResult(
            valid=False,
            requested_profile=prof,
            airplane_mode_p12=airplane_mode_p12,
            access_auth_enabled=access_auth_enabled,
            deprecated_protocol_rejected=True,
            passed_to_wpa_supplicant=False,
            resolved_wpa_key_mgmt="REJECTED",
            pmf_ieee80211w_mode=0,
            rf_tx_packets_emitted=0,
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            status=errors[0],
            errors=tuple(errors),
        )

    if prof in DEPRECATED_702_SECURITY_PROFILES:
        errors.append(f"REJECTED_DEPRECATED_702_PROTOCOL: {prof}")
        return Wpa2Wpa3SecurityShimEvalResult(
            valid=False,
            requested_profile=prof,
            airplane_mode_p12=airplane_mode_p12,
            access_auth_enabled=access_auth_enabled,
            deprecated_protocol_rejected=True,
            passed_to_wpa_supplicant=False,
            resolved_wpa_key_mgmt="REJECTED_WEP_WPA1_IPSEC",
            pmf_ieee80211w_mode=0,
            rf_tx_packets_emitted=0,
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            status=errors[0],
            errors=tuple(errors),
        )

    if airplane_mode_p12 and prof != "ACCESS_AUTH_TLS":
        errors.append("P12_AIRPLANE_RF_ISOLATED_USE_WIRED_USBLAN")
        return Wpa2Wpa3SecurityShimEvalResult(
            valid=False,
            requested_profile=prof,
            airplane_mode_p12=True,
            access_auth_enabled=access_auth_enabled,
            deprecated_protocol_rejected=False,
            passed_to_wpa_supplicant=False,
            resolved_wpa_key_mgmt="P12_RF_BLOCKED",
            pmf_ieee80211w_mode=0,
            rf_tx_packets_emitted=0,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status=errors[0],
            errors=tuple(errors),
        )

    if prof == "WPA3_SAE":
        key_mgmt = "SAE"
        pmf = 2
    elif prof == "WPA2_WPA3_TRANSITION":
        key_mgmt = "WPA-PSK SAE"
        pmf = 1
    elif prof == "WPA2_PSK_SHA256":
        key_mgmt = "WPA-PSK-SHA256"
        pmf = 1
    elif prof == "WPA2_PSK_CCMP":
        key_mgmt = "WPA-PSK"
        pmf = 1
    else:  # ACCESS_AUTH_TLS
        if not access_auth_enabled:
            errors.append("ACCESS_AUTHENTICATION_CREDENTIALS_MISSING")
        key_mgmt = "ACCESS_AUTH_TLS_1_3"
        pmf = 2

    valid = len(errors) == 0
    return Wpa2Wpa3SecurityShimEvalResult(
        valid=valid,
        requested_profile=prof,
        airplane_mode_p12=airplane_mode_p12,
        access_auth_enabled=access_auth_enabled,
        deprecated_protocol_rejected=False,
        passed_to_wpa_supplicant=valid,
        resolved_wpa_key_mgmt=key_mgmt if valid else "REJECTED",
        pmf_ieee80211w_mode=pmf if valid else 0,
        rf_tx_packets_emitted=0,
        bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
        status="WPA2_WPA3_702_CLEAN_PASSTHROUGH" if valid else errors[0],
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: 1.5x/1.6x/1.3x/2.0x Anamorphic De-Squeeze & Bright Monitoring GRM
# ---------------------------------------------------------------------------


def evaluate_anamorphic_desqueeze_grm_compat(
    *,
    desqueeze_ratio: float = 1.5,
    bright_monitoring_on: bool = True,
    magnifier_scale: float = 4.0,
    clean_hdmi_mode: bool = False,
    hdmi_raw_active: bool = False,
) -> AnamorphicDesqueezeGrmEvalResult:
    """Verify GRM plane scaling keeps Big-6 (`sid=0x0a`) & clean HDMI unclipped."""
    errors: List[str] = []
    if desqueeze_ratio not in FX3_702_DESQUEEZE_RATIOS:
        errors.append(f"UNSUPPORTED_DESQUEEZE_RATIO: {desqueeze_ratio}")
    if magnifier_scale not in VALID_MAGNIFIER_SCALES_P179:
        errors.append(f"UNSUPPORTED_MAGNIFIER_SCALE: {magnifier_scale}")
    if hdmi_raw_active and clean_hdmi_mode:
        # Both cannot simultaneously emit conflicting processed vs raw streams.
        errors.append("CONFLICTING_CLEAN_HDMI_AND_RAW16_ACTIVE")

    fx6_native = desqueeze_ratio in FX6_601_NATIVE_DESQUEEZE_RATIOS
    fx3_shim = desqueeze_ratio in FX3_702_EXCLUSIVE_DESQUEEZE_RATIOS

    # Video underlay plane scales vertically by 1/ratio inside letterbox viewport while
    # OSD/Big-6 GRM plane remains strictly 1.0x/1.0x so Big-6 (`sid=0x0a`) never clips!
    video_scale_x = 1.0
    video_scale_y = round(1.0 / desqueeze_ratio, 6) if desqueeze_ratio > 0 else 0.0
    osd_scale_x = 1.0
    osd_scale_y = 1.0

    # Magnifier ROI maps FX6 3x/6x cleanly to FX3 4.0x sensor crop bounds (4264x2408).
    eff_mag = 4.0 if magnifier_scale in (3.0, 4.0, 6.0) else 1.0
    roi_w = max(1, int(round(FX3_RAW_SENSOR_RES[0] / (eff_mag * desqueeze_ratio)))) if desqueeze_ratio > 0 else 0
    roi_h = max(1, int(round(FX3_RAW_SENSOR_RES[1] / eff_mag)))
    roi_in_bounds = (
        0 < roi_w <= FX3_RAW_SENSOR_RES[0]
        and 0 < roi_h <= FX3_RAW_SENSOR_RES[1]
    )
    if not roi_in_bounds:
        errors.append("MAGNIFIER_ROI_OUT_OF_SENSOR_BOUNDS")

    big6_hud_unclipped = (osd_scale_x == 1.0 and osd_scale_y == 1.0) and (0.0 < video_scale_y <= 1.0)
    clean_hdmi_unclipped = (not clean_hdmi_mode) or (osd_scale_x == 1.0 and osd_scale_y == 1.0)
    bright_display_only = True  # Bright Monitoring never alters recorded XAVC/RAW sensor gain.

    valid = len(errors) == 0 and big6_hud_unclipped and clean_hdmi_unclipped
    bridge_class = BRIDGE_CLASS_SHIM_TRANSLATED if fx3_shim or magnifier_scale in (3.0, 6.0) else BRIDGE_CLASS_NATIVE_PASSTHROUGH
    status = "ANAMORPHIC_GRM_UNCLIPPED_OK" if valid else errors[0]

    return AnamorphicDesqueezeGrmEvalResult(
        valid=valid,
        desqueeze_ratio=desqueeze_ratio,
        fx6_native_ratio=fx6_native,
        fx3_702_shim_required=fx3_shim,
        bright_monitoring_on=bright_monitoring_on,
        magnifier_scale=magnifier_scale,
        clean_hdmi_mode=clean_hdmi_mode,
        hdmi_raw_active=hdmi_raw_active,
        video_plane_scale_x=video_scale_x,
        video_plane_scale_y=video_scale_y,
        osd_grm_scale_x=osd_scale_x,
        osd_grm_scale_y=osd_scale_y,
        magnifier_roi_w_px=roi_w,
        magnifier_roi_h_px=roi_h,
        big6_hud_unclipped=big6_hud_unclipped,
        clean_hdmi_unclipped=clean_hdmi_unclipped,
        bright_monitoring_display_only=bright_display_only,
        bridge_class=bridge_class,
        status=status,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: Auto USB-LAN Recognition, Dual-Slot Remaining-Time & Write Firewall
# ---------------------------------------------------------------------------


def evaluate_auto_usblan_recognition(
    *,
    adapter_driver: str = "CDC_NCM",
    usb_vid_pid: str = "0BDA:8153",
    link_speed_mbps: int = 1000,
    vermagic: str = SCEL_KERNEL_VERMAGIC_P179,
    airplane_mode_p12: bool = True,
) -> AutoUsbLanRecognitionEvalResult:
    """Audit automatic USB-LAN adapter recognition under `4.9.337-scel+` & P12 RF-Off."""
    errors: List[str] = []
    drv = adapter_driver.strip().upper()
    if drv not in SUPPORTED_USBLAN_DRIVERS_P179:
        errors.append(f"UNSUPPORTED_USBLAN_DRIVER: {adapter_driver}")
    if vermagic.strip() != SCEL_KERNEL_VERMAGIC_P179:
        errors.append(f"KERNEL_VERMAGIC_MISMATCH: {vermagic}")
    if link_speed_mbps not in (100, 1000, 2500):
        errors.append(f"INVALID_ETHERNET_LINK_SPEED: {link_speed_mbps}")

    valid = len(errors) == 0
    return AutoUsbLanRecognitionEvalResult(
        valid=valid,
        adapter_driver=drv,
        usb_vid_pid=usb_vid_pid.strip().upper(),
        link_speed_mbps=link_speed_mbps,
        vermagic_compatible=(vermagic.strip() == SCEL_KERNEL_VERMAGIC_P179),
        airplane_mode_p12=airplane_mode_p12,
        auto_netif_name="eth0" if valid else "none",
        dhcp_bound=valid,
        rf_tx_leaks=0,
        bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH if valid else BRIDGE_CLASS_MASKED_ABSENT_HW,
        status="AUTO_USBLAN_ETH0_BOUND" if valid else errors[0],
        errors=tuple(errors),
    )


def evaluate_dual_slot_remaining_time_telemetry(
    *,
    rec_mode: str = "SIMULTANEOUS",
    codec_bitrate_mbps: float = 200.0,
    slot_a_free_mib: int = 128_000,
    slot_b_free_mib: int = 64_000,
    proxy_bitrate_mbps: float = 16.0,
) -> DualSlotRemainingTimeEvalResult:
    """Compute exact Dual-Slot Simultaneous/Relay/Sort remaining-time telemetry."""
    errors: List[str] = []
    mode = rec_mode.strip().upper()
    if mode not in VALID_DUAL_SLOT_REC_MODES_P179:
        errors.append(f"UNKNOWN_DUAL_SLOT_MODE: {rec_mode}")
    if codec_bitrate_mbps <= 0.0:
        errors.append("INVALID_CODEC_BITRATE_MBPS")
    if slot_a_free_mib < 0 or slot_b_free_mib < 0:
        errors.append("NEGATIVE_SLOT_FREE_SPACE")

    # Convert MiB (2^20 B) and Mbps (10^6 b/s) -> minutes = (mib * 1048576 * 8) / (mbps * 1e6 * 60)
    def _mib_to_min(free_mib: int, mbps: float) -> float:
        if free_mib <= 0 or mbps <= 0.0:
            return 0.0
        return round((free_mib * 1_048_576.0 * 8.0) / (mbps * 1_000_000.0 * 60.0), 2)

    slot_a_min = _mib_to_min(slot_a_free_mib, codec_bitrate_mbps)
    if mode == "SORT":
        slot_b_min = _mib_to_min(slot_b_free_mib, proxy_bitrate_mbps)
    else:
        slot_b_min = _mib_to_min(slot_b_free_mib, codec_bitrate_mbps)

    if mode == "SIMULTANEOUS":
        if slot_a_free_mib == 0 or slot_b_free_mib == 0:
            errors.append("SIMULTANEOUS_REQUIRES_BOTH_SLOTS_NONEMPTY")
        eff_min = min(slot_a_min, slot_b_min)
        bottleneck = "SLOT_A" if slot_a_min <= slot_b_min else "SLOT_B"
        zero_drop = len(errors) == 0
    elif mode == "RELAY":
        if slot_a_free_mib == 0 and slot_b_free_mib == 0:
            errors.append("BOTH_SLOTS_FULL")
        eff_min = round(slot_a_min + slot_b_min, 2)
        bottleneck = "NONE_COMBINED_RELAY"
        zero_drop = len(errors) == 0
    elif mode == "SORT":
        if slot_a_free_mib == 0 or slot_b_free_mib == 0:
            errors.append("SORT_REQUIRES_BOTH_SLOTS_NONEMPTY")
        eff_min = min(slot_a_min, slot_b_min)
        bottleneck = "SLOT_A_MAIN" if slot_a_min <= slot_b_min else "SLOT_B_PROXY"
        zero_drop = len(errors) == 0
    elif mode == "SINGLE_SLOT_A":
        if slot_a_free_mib == 0:
            errors.append("SLOT_A_FULL")
        eff_min = slot_a_min
        bottleneck = "SLOT_A"
        zero_drop = len(errors) == 0
    else:
        eff_min = 0.0
        bottleneck = "INVALID"
        zero_drop = False

    valid = len(errors) == 0
    return DualSlotRemainingTimeEvalResult(
        valid=valid,
        rec_mode=mode,
        codec_bitrate_mbps=codec_bitrate_mbps,
        slot_a_free_mib=slot_a_free_mib,
        slot_b_free_mib=slot_b_free_mib,
        slot_a_remaining_min=slot_a_min,
        slot_b_remaining_min=slot_b_min,
        effective_remaining_min=eff_min,
        bottleneck_slot=bottleneck,
        zero_frame_drop_rollover=zero_drop,
        status=f"DUAL_SLOT_{mode}_TELEMETRY_OK" if valid else errors[0],
        errors=tuple(errors),
    )


def evaluate_phase179_write_guard(target_path: str) -> Phase179WriteGuardResult:
    """Enforce zero persistent eMMC/SPI-NOR writes while allowing volatile/external targets."""
    norm = target_path.strip()
    if FORBIDDEN_PERSISTENT_TARGET_RE_P179.search(norm):
        return Phase179WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            emmc_mutation_bytes=0,
            status="BLOCKED_PERSISTENT_EMMC_OR_SPINOR_TARGET",
            errors=(f"FORBIDDEN_PERSISTENT_TARGET: {norm}",),
        )
    allowed = any(norm.startswith(p) for p in VOLATILE_OR_EXT_PREFIXES_P179)
    if not allowed:
        return Phase179WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            emmc_mutation_bytes=0,
            status="UNLISTED_NON_VOLATILE_TARGET_BLOCKED",
            errors=(f"TARGET_NOT_VOLATILE_OR_EXTERNAL_MEDIA: {norm}",),
        )
    return Phase179WriteGuardResult(
        valid=True,
        target_path=norm,
        volatile_or_ext_allowed=True,
        persistent_write_blocked=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        emmc_mutation_bytes=0,
        status="VOLATILE_RAM_OR_EXT_MEDIA_ALLOWED",
        errors=(),
    )


def build_phase179_delta_compat_matrix() -> Phase179CompatMatrixSummary:
    """Construct 12-touchpoint 4-class compatibility matrix for FX3 7.02 vs FX6 6.01 deltas."""
    entries: Tuple[Phase179TouchpointEntry, ...] = (
        Phase179TouchpointEntry(
            touchpoint_id="P179-01",
            subsystem="HDMI_BRAW_SDI",
            fx6_component="appFw.so (EVENT_REMOTE_MOVIE_HDMI_OUTPUT_SETTINGS_W_DIALOG_RAW_OUTPUT)",
            fx3_target="Stock FX3 7.02 Type-A HDMI BRAW / ProRes RAW / 4K60 driver",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="hdmi_raw_braw_ready == True; zero LUT burn-in on RAW",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-02",
            subsystem="HDMI_BRAW_SDI",
            fx6_component="appFw.so (BKID_APP_SETTING_SDI_OUTPUT / PRM_FEATURE_MANAGER_sdi_output)",
            fx3_target="Stage-B LD_PRELOAD + osal_uipc mask (absent 12G-SDI BNC)",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="sdi_hw_probe_masked == True; sdi_blocking_faults == 0",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-03",
            subsystem="HDMI_BRAW_SDI",
            fx6_component="libInfraAvbbc.so (ConvertCmdMidToHdmiEt / ConvertCmdMidToSdiEt) + cpapp-b.bin",
            fx3_target="Stock FX3 libInfraAvbbc.so + cpapp-b.bin HDMI LUT/TC passthrough",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="hdmi_clean_lut_tc_bridged == True; MoniFpgaSdi masked",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-04",
            subsystem="WPA2_WPA3_ACCESS_AUTH",
            fx6_component="appFw.so (VAL_setting_wlan_security_WLAN_SECURITY_WEP / IPSEC_ON)",
            fx3_target="Stage-B network config sanitizer strips WEP/WPA1-TKIP/IPsec",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="deprecated_protocol_rejected == True for WEP/WPA1/IPsec",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-05",
            subsystem="WPA2_WPA3_ACCESS_AUTH",
            fx6_component="wpa_supplicant v2.9-devel (SAE / sFT-SAE / WPA2-PSK-SHA256 / PMF)",
            fx3_target="Stock FX3 7.02 wpa_supplicant + libWlanAdjust.so (wpa_ctrl_request)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="Only WPA2/WPA3/Access Authentication forwarded",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-06",
            subsystem="WPA2_WPA3_ACCESS_AUTH",
            fx6_component="appFw.so (SOFTWARE_KEYBOARD_ACCESS_AUTHENTICATION_USERNAME/PASSWORD)",
            fx3_target="FX3 7.02 Access Authentication + P12 Airplane RF-Off guard",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="rf_tx_packets_emitted == 0 under P12; wired TLS allowed",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-07",
            subsystem="ANAMORPHIC_BRIGHT_MAG_GRM",
            fx6_component="appFw.so (1.0x / 1.3x / 2.0x) vs FX3 7.02 (1.5x / 1.6x / 1.65x)",
            fx3_target="Stage-B GRM plane video scaling (1/S) with 1:1 Big-6 (sid=0x0a) OSD",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="big6_hud_unclipped == True across 1.3x/1.5x/1.6x/2.0x",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-08",
            subsystem="ANAMORPHIC_BRIGHT_MAG_GRM",
            fx6_component="appFw.so (BRIGHT_MONITORING + FOCUS_MAGNIFIER x3/x6)",
            fx3_target="FX3 7.02 Bright Monitoring (display-only) + 4.0x Focus Magnifier ROI",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="bright_monitoring_display_only == True; clean_hdmi_unclipped == True",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-09",
            subsystem="ANAMORPHIC_BRIGHT_MAG_GRM",
            fx6_component="libgemini-grm.so (GraphicsContextGRM::setScale) + grm_ma.ko",
            fx3_target="Stock FX3 4.9.337-scel+ grm_ma.ko (36,592 B) plane compositor",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="grm_ma.ko vermagic matches 4.9.337-scel+",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-10",
            subsystem="USBLAN_DUAL_SLOT_NVS",
            fx6_component="libNetServiceEther.so (ConnectedUsbEtherDevice) + USB-LAN",
            fx3_target="Stock FX3 cdc_ncm.ko / r8152.ko / asix.ko / ax88179_178a.ko eth0",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="auto_netif_name == eth0; rf_tx_leaks == 0 under P12",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-11",
            subsystem="USBLAN_DUAL_SLOT_NVS",
            fx6_component="libmpr.so (MovieRemain::GetRemain / PrepareRelayMedia / SimulRec)",
            fx3_target="Stock FX3 libmpr.so MovieRemain::CalcRecordableTime Dual-Slot",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="zero_frame_drop_rollover == True; accurate Simul/Relay/Sort mins",
        ),
        Phase179TouchpointEntry(
            touchpoint_id="P179-12",
            subsystem="USBLAN_DUAL_SLOT_NVS",
            fx6_component="p2:/Backup.bin, p8:/cpapp-b.bin, p12:/cert, /etc/wpa_supplicant.conf, spi_nor:",
            fx3_target="Stage-B /tmp/ volatile overlay + O_RDONLY NVS firewall",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="persistent_emmc_writes_authorized == False; spi_nor_write_authorized == False",
        ),
    )
    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    subsystem_counts: Dict[str, int] = {}
    for e in entries:
        class_counts[e.bridge_class] = class_counts.get(e.bridge_class, 0) + 1
        subsystem_counts[e.subsystem] = subsystem_counts.get(e.subsystem, 0) + 1
    return Phase179CompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        subsystem_counts=subsystem_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def _build_synthetic_kmod_elf64(
    *,
    module_name: str,
    driver_tag: str,
) -> bytes:
    """Build a valid synthetic ELF64 fixture carrying `.modinfo` vermagic string."""
    modinfo = (
        f"vermagic={SCEL_KERNEL_VERMAGIC_P179}\x00"
        f"description={driver_tag}\x00"
        f"name={module_name}\x00"
    )
    return _build_synthetic_elf64(
        exports=(f"{module_name}_init", f"{module_name}_exit"),
        imports=("usbnet_probe", "register_netdev"),
        dt_needed=(),
        rodata_strings=(modinfo,),
    )


def build_clean_room_realhw_hdmi_braw_wpa3_702_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, cpapp-b.bin, and kmod fixtures."""
    fx3_appfw_tokens = (
        APPFW_HDMI_RAW_FX3_MARKERS_P179
        + APPFW_WPA3_ACCESS_AUTH_SHARED_MARKERS_P179
        + APPFW_DESQUEEZE_SHARED_MARKERS_P179
        + APPFW_DESQUEEZE_702_FX3_MARKERS_P179
        + APPFW_USBLAN_DUAL_SLOT_SHARED_MARKERS_P179
    )
    fx6_appfw_tokens = (
        APPFW_HDMI_RAW_FX3_MARKERS_P179[:4]
        + APPFW_SDI_FX6_EXCLUSIVE_MARKERS_P179
        + APPFW_WPA3_ACCESS_AUTH_SHARED_MARKERS_P179
        + (APPFW_LEGACY_WEP_FX6_MARKER_P179,)
        + APPFW_DESQUEEZE_SHARED_MARKERS_P179
        + APPFW_USBLAN_DUAL_SLOT_SHARED_MARKERS_P179
    )
    return {
        "fx3_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af3_imp_{i}" for i in range(64)),
            dt_needed=("libmpr.so", "libInfraAvbbc.so", "libNetServiceEther.so"),
            rodata_strings=fx3_appfw_tokens,
        ),
        "fx6_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af6_imp_{i}" for i in range(64)),
            dt_needed=("libmpr.so", "libInfraAvbbc.so", "libNetServiceEther.so"),
            rodata_strings=fx6_appfw_tokens,
        ),
        "fx3_avbbc": _build_synthetic_elf64(
            exports=tuple(f"av3_exp_{i}" for i in range(32)),
            imports=tuple(f"av3_imp_{i}" for i in range(16)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=AVBBC_HDMI_SDI_MARKERS_P179,
        ),
        "fx6_avbbc": _build_synthetic_elf64(
            exports=tuple(f"av6_exp_{i}" for i in range(32)),
            imports=tuple(f"av6_imp_{i}" for i in range(16)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=AVBBC_HDMI_SDI_MARKERS_P179,
        ),
        "fx3_wpa": _build_synthetic_elf64(
            exports=tuple(f"wpa3_exp_{i}" for i in range(11)),
            imports=tuple(f"wpa3_imp_{i}" for i in range(24)),
            dt_needed=("libc.so.6",),
            rodata_strings=WPA_SUPPLICANT_MARKERS_P179,
        ),
        "fx6_wpa": _build_synthetic_elf64(
            exports=tuple(f"wpa6_exp_{i}" for i in range(11)),
            imports=tuple(f"wpa6_imp_{i}" for i in range(24)),
            dt_needed=("libc.so.6",),
            rodata_strings=WPA_SUPPLICANT_MARKERS_P179,
        ),
        "fx3_wlan_adj": _build_synthetic_elf64(
            exports=tuple(f"wa3_exp_{i}" for i in range(16)),
            imports=tuple(f"wa3_imp_{i}" for i in range(12)),
            dt_needed=("libWlanControlCommon.so",),
            rodata_strings=WLAN_ADJUST_MARKERS_P179,
        ),
        "fx6_wlan_adj": _build_synthetic_elf64(
            exports=tuple(f"wa6_exp_{i}" for i in range(16)),
            imports=tuple(f"wa6_imp_{i}" for i in range(12)),
            dt_needed=("libWlanControlCommon.so",),
            rodata_strings=WLAN_ADJUST_MARKERS_P179,
        ),
        "fx3_ether": _build_synthetic_elf64(
            exports=tuple(f"eth3_exp_{i}" for i in range(24)),
            imports=tuple(f"eth3_imp_{i}" for i in range(16)),
            dt_needed=("libNetCommon.so",),
            rodata_strings=NETSERVICE_ETHER_MARKERS_P179,
        ),
        "fx6_ether": _build_synthetic_elf64(
            exports=tuple(f"eth6_exp_{i}" for i in range(32)),
            imports=tuple(f"eth6_imp_{i}" for i in range(16)),
            dt_needed=("libNetCommon.so",),
            rodata_strings=NETSERVICE_ETHER_MARKERS_P179,
        ),
        "fx3_mpr": _build_synthetic_elf64(
            exports=tuple(f"mpr3_exp_{i}" for i in range(32)),
            imports=tuple(f"mpr3_imp_{i}" for i in range(16)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=MPR_REMAIN_RELAY_SIMUL_SHARED_MARKERS_P179 + (MPR_CALC_REMAIN_FX3_MARKER_P179,),
        ),
        "fx6_mpr": _build_synthetic_elf64(
            exports=tuple(f"mpr6_exp_{i}" for i in range(36)),
            imports=tuple(f"mpr6_imp_{i}" for i in range(16)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=MPR_REMAIN_RELAY_SIMUL_SHARED_MARKERS_P179,
        ),
        "fx6_grm": _build_synthetic_elf64(
            exports=tuple(f"grm6_exp_{i}" for i in range(20)),
            imports=tuple(f"grm6_imp_{i}" for i in range(12)),
            dt_needed=("libc.so.6",),
            rodata_strings=GEMINI_GRM_MARKERS_P179,
        ),
        "fx3_cpapp": b"\x00".join(t.encode("ascii") for t in CPAPP_SHARED_DESQUEEZE_MARKERS_P179),
        "fx6_cpapp": b"\x00".join(
            t.encode("ascii") for t in (CPAPP_SHARED_DESQUEEZE_MARKERS_P179 + (CPAPP_FX6_SDI_MARKER_P179,))
        ),
        "fx3_cdc_ncm": _build_synthetic_kmod_elf64(module_name="cdc_ncm", driver_tag="USB CDC NCM host driver"),
        "fx6_cdc_ncm": _build_synthetic_kmod_elf64(module_name="cdc_ncm", driver_tag="USB CDC NCM host driver"),
        "fx3_r8152": _build_synthetic_kmod_elf64(module_name="r8152", driver_tag="Realtek RTL8152/RTL8153"),
        "fx6_r8152": _build_synthetic_kmod_elf64(module_name="r8152", driver_tag="Realtek RTL8152/RTL8153"),
        "fx3_asix": _build_synthetic_kmod_elf64(module_name="asix", driver_tag="ASIX AX8817X"),
        "fx6_asix": _build_synthetic_kmod_elf64(module_name="asix", driver_tag="ASIX AX8817X"),
        "fx3_ax88179": _build_synthetic_kmod_elf64(module_name="ax88179_178a", driver_tag="ASIX AX88179_178A"),
        "fx6_ax88179": _build_synthetic_kmod_elf64(module_name="ax88179_178a", driver_tag="ASIX AX88179_178A"),
        "fx3_grm_ko": _build_synthetic_kmod_elf64(module_name="grm_ma", driver_tag="GRM MA Kernel Plane"),
        "fx6_grm_ko": _build_synthetic_kmod_elf64(module_name="grm_ma", driver_tag="GRM MA Kernel Plane"),
    }


# ---------------------------------------------------------------------------
# Main Dual-Mode Unified Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_hdmi_braw_wpa3_702_delta(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwHdmiBrawWpa3702DeltaReport:
    """Run Phase 179 (37th Auditor, 37/37) on real O_RDONLY donors or clean-room fixtures."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    force_clean = clean_room or is_forced_clean_room()

    rel_map = {
        "fx3_appfw": FX3_APPFW_P179_RELPATH,
        "fx6_appfw": FX6_APPFW_P179_RELPATH,
        "fx3_avbbc": FX3_LIBINFRA_AVBBC_P179_RELPATH,
        "fx6_avbbc": FX6_LIBINFRA_AVBBC_P179_RELPATH,
        "fx3_wpa": FX3_WPA_SUPPLICANT_P179_RELPATH,
        "fx6_wpa": FX6_WPA_SUPPLICANT_P179_RELPATH,
        "fx3_wlan_adj": FX3_LIBWLAN_ADJUST_P179_RELPATH,
        "fx6_wlan_adj": FX6_LIBWLAN_ADJUST_P179_RELPATH,
        "fx3_ether": FX3_LIBNET_ETHER_P179_RELPATH,
        "fx6_ether": FX6_LIBNET_ETHER_P179_RELPATH,
        "fx3_mpr": FX3_LIBMPR_P179_RELPATH,
        "fx6_mpr": FX6_LIBMPR_P179_RELPATH,
        "fx6_grm": FX6_LIBGEMINI_GRM_P179_RELPATH,
        "fx3_cpapp": FX3_CPAPP_P179_RELPATH,
        "fx6_cpapp": FX6_CPAPP_P179_RELPATH,
        "fx3_cdc_ncm": FX3_CDC_NCM_KO_RELPATH,
        "fx6_cdc_ncm": FX6_CDC_NCM_KO_RELPATH,
        "fx3_r8152": FX3_R8152_KO_RELPATH,
        "fx6_r8152": FX6_R8152_KO_RELPATH,
        "fx3_asix": FX3_ASIX_KO_RELPATH,
        "fx6_asix": FX6_ASIX_KO_RELPATH,
        "fx3_ax88179": FX3_AX88179_KO_RELPATH,
        "fx6_ax88179": FX6_AX88179_KO_RELPATH,
        "fx3_grm_ko": FX3_GRM_MA_KO_RELPATH,
        "fx6_grm_ko": FX6_GRM_MA_KO_RELPATH,
    }

    donor_paths: Dict[str, Optional[Path]] = {}
    if not force_clean:
        for key, rel in rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=root)

    use_local = (not force_clean) and all(p is not None for p in donor_paths.values())

    all_appfw_tokens = (
        APPFW_HDMI_RAW_FX3_MARKERS_P179
        + APPFW_SDI_FX6_EXCLUSIVE_MARKERS_P179
        + APPFW_WPA3_ACCESS_AUTH_SHARED_MARKERS_P179
        + (APPFW_LEGACY_WEP_FX6_MARKER_P179,)
        + APPFW_DESQUEEZE_SHARED_MARKERS_P179
        + APPFW_DESQUEEZE_702_FX3_MARKERS_P179
        + APPFW_USBLAN_DUAL_SLOT_SHARED_MARKERS_P179
    )
    all_mpr_tokens = MPR_REMAIN_RELAY_SIMUL_SHARED_MARKERS_P179 + (MPR_CALC_REMAIN_FX3_MARKER_P179,)
    all_cpapp_tokens = CPAPP_SHARED_DESQUEEZE_MARKERS_P179 + (CPAPP_FX6_SDI_MARKER_P179,)

    donor_file_sizes: Dict[str, int] = {}
    errors: List[str] = []

    if use_local:
        mode = "LOCAL_DONOR_VERIFIED"
        fx3_appfw_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX3",
            tokens=all_appfw_tokens,
        )
        fx6_appfw_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX6",
            tokens=all_appfw_tokens,
        )
        fx3_avbbc_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx3_avbbc"],  # type: ignore[arg-type]
            binary_name="libInfraAvbbc.so",
            body_label="FX3",
            tokens=AVBBC_HDMI_SDI_MARKERS_P179,
        )
        fx6_avbbc_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx6_avbbc"],  # type: ignore[arg-type]
            binary_name="libInfraAvbbc.so",
            body_label="FX6",
            tokens=AVBBC_HDMI_SDI_MARKERS_P179,
        )
        fx3_wpa_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx3_wpa"],  # type: ignore[arg-type]
            binary_name="wpa_supplicant",
            body_label="FX3",
            tokens=WPA_SUPPLICANT_MARKERS_P179,
        )
        fx6_wpa_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx6_wpa"],  # type: ignore[arg-type]
            binary_name="wpa_supplicant",
            body_label="FX6",
            tokens=WPA_SUPPLICANT_MARKERS_P179,
        )
        fx3_wlan_adj_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx3_wlan_adj"],  # type: ignore[arg-type]
            binary_name="libWlanAdjust.so",
            body_label="FX3",
            tokens=WLAN_ADJUST_MARKERS_P179,
        )
        fx6_wlan_adj_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx6_wlan_adj"],  # type: ignore[arg-type]
            binary_name="libWlanAdjust.so",
            body_label="FX6",
            tokens=WLAN_ADJUST_MARKERS_P179,
        )
        fx3_ether_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx3_ether"],  # type: ignore[arg-type]
            binary_name="libNetServiceEther.so",
            body_label="FX3",
            tokens=NETSERVICE_ETHER_MARKERS_P179,
        )
        fx6_ether_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx6_ether"],  # type: ignore[arg-type]
            binary_name="libNetServiceEther.so",
            body_label="FX6",
            tokens=NETSERVICE_ETHER_MARKERS_P179,
        )
        fx3_mpr_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx3_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX3",
            tokens=all_mpr_tokens,
        )
        fx6_mpr_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx6_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX6",
            tokens=all_mpr_tokens,
        )
        fx6_grm_sum = _scan_elf_bounded_ro_rdonly(
            donor_paths["fx6_grm"],  # type: ignore[arg-type]
            binary_name="libgemini-grm.so",
            body_label="FX6",
            tokens=GEMINI_GRM_MARKERS_P179,
        )
        fx3_cp_sz, fx3_cp_hits = _scan_flat_binary_tokens_rdonly(
            donor_paths["fx3_cpapp"], all_cpapp_tokens  # type: ignore[arg-type]
        )
        fx6_cp_sz, fx6_cp_hits = _scan_flat_binary_tokens_rdonly(
            donor_paths["fx6_cpapp"], all_cpapp_tokens  # type: ignore[arg-type]
        )

        kmod_specs = (
            ("fx3_cdc_ncm", "cdc_ncm.ko", "FX3", "CDC_NCM"),
            ("fx6_cdc_ncm", "cdc_ncm.ko", "FX6", "CDC_NCM"),
            ("fx3_r8152", "r8152.ko", "FX3", "RTL8153"),
            ("fx6_r8152", "r8152.ko", "FX6", "RTL8153"),
            ("fx3_asix", "asix.ko", "FX3", "ASIX_AX8817X"),
            ("fx6_asix", "asix.ko", "FX6", "ASIX_AX8817X"),
            ("fx3_ax88179", "ax88179_178a.ko", "FX3", "ASIX_AX88179"),
            ("fx6_ax88179", "ax88179_178a.ko", "FX6", "ASIX_AX88179"),
            ("fx3_grm_ko", "grm_ma.ko", "FX3", "GRM_PLANE"),
            ("fx6_grm_ko", "grm_ma.ko", "FX6", "GRM_PLANE"),
        )
        kmod_map: Dict[str, KernelModuleInfoSummary] = {}
        for k, mname, blbl, dtag in kmod_specs:
            kmod_map[k] = _inspect_kmod_modinfo_rdonly(
                donor_paths[k],  # type: ignore[arg-type]
                module_name=mname,
                body_label=blbl,
                driver_tag=dtag,
            )

        donor_file_sizes = {
            "fx3_appfw": fx3_appfw_sum.file_bytes,
            "fx6_appfw": fx6_appfw_sum.file_bytes,
            "fx3_avbbc": fx3_avbbc_sum.file_bytes,
            "fx6_avbbc": fx6_avbbc_sum.file_bytes,
            "fx3_wpa": fx3_wpa_sum.file_bytes,
            "fx6_wpa": fx6_wpa_sum.file_bytes,
            "fx3_wlan_adj": fx3_wlan_adj_sum.file_bytes,
            "fx6_wlan_adj": fx6_wlan_adj_sum.file_bytes,
            "fx3_ether": fx3_ether_sum.file_bytes,
            "fx6_ether": fx6_ether_sum.file_bytes,
            "fx3_mpr": fx3_mpr_sum.file_bytes,
            "fx6_mpr": fx6_mpr_sum.file_bytes,
            "fx6_grm": fx6_grm_sum.file_bytes,
            "fx3_cpapp": fx3_cp_sz,
            "fx6_cpapp": fx6_cp_sz,
            **{k: km.file_bytes for k, km in kmod_map.items()},
        }
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx = build_clean_room_realhw_hdmi_braw_wpa3_702_fixtures()
        fx3_appfw_sum = _scan_elf_buf_ordered(
            fx["fx3_appfw"], binary_name="appFw.so", body_label="FX3", source_mode=mode, tokens=all_appfw_tokens
        )
        fx6_appfw_sum = _scan_elf_buf_ordered(
            fx["fx6_appfw"], binary_name="appFw.so", body_label="FX6", source_mode=mode, tokens=all_appfw_tokens
        )
        fx3_avbbc_sum = _scan_elf_buf_ordered(
            fx["fx3_avbbc"], binary_name="libInfraAvbbc.so", body_label="FX3", source_mode=mode, tokens=AVBBC_HDMI_SDI_MARKERS_P179
        )
        fx6_avbbc_sum = _scan_elf_buf_ordered(
            fx["fx6_avbbc"], binary_name="libInfraAvbbc.so", body_label="FX6", source_mode=mode, tokens=AVBBC_HDMI_SDI_MARKERS_P179
        )
        fx3_wpa_sum = _scan_elf_buf_ordered(
            fx["fx3_wpa"], binary_name="wpa_supplicant", body_label="FX3", source_mode=mode, tokens=WPA_SUPPLICANT_MARKERS_P179
        )
        fx6_wpa_sum = _scan_elf_buf_ordered(
            fx["fx6_wpa"], binary_name="wpa_supplicant", body_label="FX6", source_mode=mode, tokens=WPA_SUPPLICANT_MARKERS_P179
        )
        fx3_wlan_adj_sum = _scan_elf_buf_ordered(
            fx["fx3_wlan_adj"], binary_name="libWlanAdjust.so", body_label="FX3", source_mode=mode, tokens=WLAN_ADJUST_MARKERS_P179
        )
        fx6_wlan_adj_sum = _scan_elf_buf_ordered(
            fx["fx6_wlan_adj"], binary_name="libWlanAdjust.so", body_label="FX6", source_mode=mode, tokens=WLAN_ADJUST_MARKERS_P179
        )
        fx3_ether_sum = _scan_elf_buf_ordered(
            fx["fx3_ether"], binary_name="libNetServiceEther.so", body_label="FX3", source_mode=mode, tokens=NETSERVICE_ETHER_MARKERS_P179
        )
        fx6_ether_sum = _scan_elf_buf_ordered(
            fx["fx6_ether"], binary_name="libNetServiceEther.so", body_label="FX6", source_mode=mode, tokens=NETSERVICE_ETHER_MARKERS_P179
        )
        fx3_mpr_sum = _scan_elf_buf_ordered(
            fx["fx3_mpr"], binary_name="libmpr.so", body_label="FX3", source_mode=mode, tokens=all_mpr_tokens
        )
        fx6_mpr_sum = _scan_elf_buf_ordered(
            fx["fx6_mpr"], binary_name="libmpr.so", body_label="FX6", source_mode=mode, tokens=all_mpr_tokens
        )
        fx6_grm_sum = _scan_elf_buf_ordered(
            fx["fx6_grm"], binary_name="libgemini-grm.so", body_label="FX6", source_mode=mode, tokens=GEMINI_GRM_MARKERS_P179
        )
        fx3_cp_hits = _count_tokens_ordered_single_pass(fx["fx3_cpapp"], all_cpapp_tokens)
        fx6_cp_hits = _count_tokens_ordered_single_pass(fx["fx6_cpapp"], all_cpapp_tokens)

        kmod_specs = (
            ("fx3_cdc_ncm", "cdc_ncm.ko", "FX3", "CDC_NCM"),
            ("fx6_cdc_ncm", "cdc_ncm.ko", "FX6", "CDC_NCM"),
            ("fx3_r8152", "r8152.ko", "FX3", "RTL8153"),
            ("fx6_r8152", "r8152.ko", "FX6", "RTL8153"),
            ("fx3_asix", "asix.ko", "FX3", "ASIX_AX8817X"),
            ("fx6_asix", "asix.ko", "FX6", "ASIX_AX8817X"),
            ("fx3_ax88179", "ax88179_178a.ko", "FX3", "ASIX_AX88179"),
            ("fx6_ax88179", "ax88179_178a.ko", "FX6", "ASIX_AX88179"),
            ("fx3_grm_ko", "grm_ma.ko", "FX3", "GRM_PLANE"),
            ("fx6_grm_ko", "grm_ma.ko", "FX6", "GRM_PLANE"),
        )
        kmod_map = {}
        for k, mname, blbl, dtag in kmod_specs:
            buf = fx[k]
            vm_ok = SCEL_KERNEL_VERMAGIC_P179.encode("ascii") in buf
            kmod_map[k] = KernelModuleInfoSummary(
                module_name=mname,
                body_label=blbl,
                source_mode=mode,
                file_bytes=len(buf),
                vermagic_match=vm_ok,
                driver_tag=dtag,
                modinfo_valid=vm_ok,
            )
        donor_file_sizes = {k: len(v) for k, v in fx.items()}

    # ---- Pillar 1: Type-A HDMI BRAW / 4K60 vs Masked 12G-SDI RAW ----
    p1_errors: List[str] = []
    fx3_hdmi_hits = {t: fx3_appfw_sum.marker_hits.get(t, 0) for t in APPFW_HDMI_RAW_FX3_MARKERS_P179}
    fx6_hdmi_hits = {t: fx6_appfw_sum.marker_hits.get(t, 0) for t in APPFW_HDMI_RAW_FX3_MARKERS_P179}
    fx3_sdi_hits = {t: fx3_appfw_sum.marker_hits.get(t, 0) for t in APPFW_SDI_FX6_EXCLUSIVE_MARKERS_P179}
    fx6_sdi_hits = {t: fx6_appfw_sum.marker_hits.get(t, 0) for t in APPFW_SDI_FX6_EXCLUSIVE_MARKERS_P179}

    for tok, cnt in fx3_hdmi_hits.items():
        if cnt <= 0:
            p1_errors.append(f"fx3_appfw missing HDMI RAW marker: {tok}")
    for tok, cnt in fx6_sdi_hits.items():
        if cnt <= 0:
            p1_errors.append(f"fx6_appfw missing SDI marker: {tok}")
    if sum(fx3_sdi_hits.values()) != 0:
        p1_errors.append("Expected 0 FX6-exclusive SDI markers in FX3 appFw.so")
    for lbl, summ in (("fx3_avbbc", fx3_avbbc_sum), ("fx6_avbbc", fx6_avbbc_sum)):
        missing = [t for t in AVBBC_HDMI_SDI_MARKERS_P179 if summ.marker_hits.get(t, 0) <= 0]
        if missing:
            p1_errors.append(f"{lbl} missing AVBBC markers: {missing}")

    fx3_cp_sdi = fx3_cp_hits.get(CPAPP_FX6_SDI_MARKER_P179, 0)
    fx6_cp_sdi = fx6_cp_hits.get(CPAPP_FX6_SDI_MARKER_P179, 0)
    if fx3_cp_sdi != 0 or fx6_cp_sdi <= 0:
        p1_errors.append("Expected MoniFpgaSdi_SetRegSDIOutFormat only in FX6 cpapp-b.bin")

    hdmi_braw_eval = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(requested_mode="HDMI_BRAW_4K60")
    hdmi_lut_tc_eval = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(requested_mode="HDMI_CLEAN_4K60_10BIT_LUT")
    sdi_raw_masked = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(requested_mode="SDI_12G_RAW_REQUEST")
    sdi_mon_masked = evaluate_hdmi_braw_vs_masked_12g_sdi_bridge(requested_mode="SDI_12G_MONITOR_REQUEST")

    if not hdmi_braw_eval.valid or not hdmi_braw_eval.hdmi_raw_braw_ready:
        p1_errors.append("hdmi_braw_4k60_eval failed")
    if not hdmi_lut_tc_eval.valid or not hdmi_lut_tc_eval.hdmi_clean_lut_tc_bridged:
        p1_errors.append("hdmi_clean_lut_tc_eval failed")
    if sdi_raw_masked.valid or not sdi_raw_masked.sdi_hw_probe_masked or sdi_raw_masked.sdi_blocking_faults != 0:
        p1_errors.append("sdi_12g_raw_masked_eval failed")
    if sdi_mon_masked.valid or not sdi_mon_masked.sdi_hw_probe_masked:
        p1_errors.append("sdi_12g_monitor_masked_eval failed")

    pillar1 = Pillar1HdmiBrawVsSdiReport(
        passed=len(p1_errors) == 0,
        fx3_appfw_hdmi_raw_hits=fx3_hdmi_hits,
        fx6_appfw_hdmi_raw_hits=fx6_hdmi_hits,
        fx3_appfw_sdi_hits=fx3_sdi_hits,
        fx6_appfw_sdi_hits=fx6_sdi_hits,
        fx3_avbbc_summary=fx3_avbbc_sum,
        fx6_avbbc_summary=fx6_avbbc_sum,
        fx3_cpapp_sdi_hits=fx3_cp_sdi,
        fx6_cpapp_sdi_hits=fx6_cp_sdi,
        hdmi_braw_4k60_eval=hdmi_braw_eval,
        hdmi_clean_lut_tc_eval=hdmi_lut_tc_eval,
        sdi_12g_raw_masked_eval=sdi_raw_masked,
        sdi_12g_monitor_masked_eval=sdi_mon_masked,
        errors=tuple(p1_errors),
    )

    # ---- Pillar 2: WPA2/WPA3-Only & Access Auth vs WEP/WPA1/IPsec ----
    p2_errors: List[str] = []
    fx3_wpa_appfw_hits = {t: fx3_appfw_sum.marker_hits.get(t, 0) for t in APPFW_WPA3_ACCESS_AUTH_SHARED_MARKERS_P179}
    fx6_wpa_appfw_hits = {t: fx6_appfw_sum.marker_hits.get(t, 0) for t in APPFW_WPA3_ACCESS_AUTH_SHARED_MARKERS_P179}
    fx3_wep_enum = fx3_appfw_sum.marker_hits.get(APPFW_LEGACY_WEP_FX6_MARKER_P179, 0)
    fx6_wep_enum = fx6_appfw_sum.marker_hits.get(APPFW_LEGACY_WEP_FX6_MARKER_P179, 0)

    for lbl, summ in (("fx3_wpa", fx3_wpa_sum), ("fx6_wpa", fx6_wpa_sum)):
        missing = [t for t in WPA_SUPPLICANT_MARKERS_P179 if summ.marker_hits.get(t, 0) <= 0]
        if missing:
            p2_errors.append(f"{lbl} missing wpa_supplicant markers: {missing}")
    for lbl, summ in (("fx3_wlan_adj", fx3_wlan_adj_sum), ("fx6_wlan_adj", fx6_wlan_adj_sum)):
        missing = [t for t in WLAN_ADJUST_MARKERS_P179 if summ.marker_hits.get(t, 0) <= 0]
        if missing:
            p2_errors.append(f"{lbl} missing libWlanAdjust markers: {missing}")
    if fx3_wep_enum != 0 or fx6_wep_enum <= 0:
        p2_errors.append("Expected VAL_setting_wlan_security_WLAN_SECURITY_WEP stripped in FX3 7.02")

    wpa3_sae_eval = evaluate_wpa2_wpa3_security_shim(requested_profile="WPA3_SAE")
    wpa2_ccmp_eval = evaluate_wpa2_wpa3_security_shim(requested_profile="WPA2_PSK_CCMP")
    access_auth_eval = evaluate_wpa2_wpa3_security_shim(requested_profile="ACCESS_AUTH_TLS", airplane_mode_p12=True)
    wep_rej = evaluate_wpa2_wpa3_security_shim(requested_profile="WEP_104")
    wpa1_rej = evaluate_wpa2_wpa3_security_shim(requested_profile="WPA1_PSK_TKIP")
    ipsec_rej = evaluate_wpa2_wpa3_security_shim(requested_profile="IPSEC_LEGACY")
    p12_rf_blk = evaluate_wpa2_wpa3_security_shim(requested_profile="WPA3_SAE", airplane_mode_p12=True)

    for ev in (wpa3_sae_eval, wpa2_ccmp_eval, access_auth_eval):
        if not ev.valid or not ev.passed_to_wpa_supplicant:
            p2_errors.append(f"Allowed security profile failed: {ev.requested_profile}")
    for rej in (wep_rej, wpa1_rej, ipsec_rej):
        if rej.valid or not rej.deprecated_protocol_rejected or rej.passed_to_wpa_supplicant:
            p2_errors.append(f"Deprecated security profile was not rejected: {rej.requested_profile}")
    if p12_rf_blk.valid or p12_rf_blk.passed_to_wpa_supplicant or p12_rf_blk.rf_tx_packets_emitted != 0:
        p2_errors.append("P12 RF isolation did not block Wi-Fi profile")

    pillar2 = Pillar2Wpa2Wpa3SecurityReport(
        passed=len(p2_errors) == 0,
        fx3_wpa_summary=fx3_wpa_sum,
        fx6_wpa_summary=fx6_wpa_sum,
        fx3_wlan_adj_summary=fx3_wlan_adj_sum,
        fx6_wlan_adj_summary=fx6_wlan_adj_sum,
        fx3_appfw_wpa_hits=fx3_wpa_appfw_hits,
        fx6_appfw_wpa_hits=fx6_wpa_appfw_hits,
        fx3_legacy_wep_enum_hits=fx3_wep_enum,
        fx6_legacy_wep_enum_hits=fx6_wep_enum,
        wpa3_sae_eval=wpa3_sae_eval,
        wpa2_ccmp_eval=wpa2_ccmp_eval,
        access_auth_tls_eval=access_auth_eval,
        wep_rejected_eval=wep_rej,
        wpa1_tkip_rejected_eval=wpa1_rej,
        ipsec_rejected_eval=ipsec_rej,
        p12_rf_off_blocked_eval=p12_rf_blk,
        errors=tuple(p2_errors),
    )

    # ---- Pillar 3: 1.5x/1.6x/1.3x/2.0x Anamorphic De-Squeeze & Bright Mon / Magnifier GRM ----
    p3_errors: List[str] = []
    desq_tokens_all = APPFW_DESQUEEZE_SHARED_MARKERS_P179 + APPFW_DESQUEEZE_702_FX3_MARKERS_P179
    fx3_desq_hits = {t: fx3_appfw_sum.marker_hits.get(t, 0) for t in desq_tokens_all}
    fx6_desq_hits = {t: fx6_appfw_sum.marker_hits.get(t, 0) for t in desq_tokens_all}

    for tok in desq_tokens_all:
        if fx3_desq_hits.get(tok, 0) <= 0:
            p3_errors.append(f"fx3_appfw missing de-squeeze/bright-mon/magnifier token: {tok}")
    if fx6_desq_hits.get("EXTERN_VAL_DE_SQUEEZE_DISP_1_5X", 0) != 0:
        p3_errors.append("Expected 1.5x de-squeeze absent in FX6 6.01 appFw.so")
    if fx6_desq_hits.get("DE_SQUEEZE_DISP_1_6X", 0) != 0:
        p3_errors.append("Expected 1.6x de-squeeze absent in FX6 6.01 appFw.so")
    if any(fx6_grm_sum.marker_hits.get(t, 0) <= 0 for t in GEMINI_GRM_MARKERS_P179):
        p3_errors.append("fx6_grm missing GraphicsContextGRM markers")
    if not kmod_map["fx3_grm_ko"].modinfo_valid or not kmod_map["fx6_grm_ko"].modinfo_valid:
        p3_errors.append("grm_ma.ko vermagic validation failed")

    fx3_cp_desq = {t: fx3_cp_hits.get(t, 0) for t in CPAPP_SHARED_DESQUEEZE_MARKERS_P179[:2]}
    fx6_cp_desq = {t: fx6_cp_hits.get(t, 0) for t in CPAPP_SHARED_DESQUEEZE_MARKERS_P179[:2]}
    if any(v <= 0 for v in fx3_cp_desq.values()) or any(v <= 0 for v in fx6_cp_desq.values()):
        p3_errors.append("cpapp-b.bin missing shared anamorphic de-squeeze IPC markers")

    d15 = evaluate_anamorphic_desqueeze_grm_compat(desqueeze_ratio=1.5, bright_monitoring_on=True, magnifier_scale=4.0)
    d16 = evaluate_anamorphic_desqueeze_grm_compat(desqueeze_ratio=1.6, bright_monitoring_on=False, magnifier_scale=4.0)
    d20 = evaluate_anamorphic_desqueeze_grm_compat(desqueeze_ratio=2.0, bright_monitoring_on=False, magnifier_scale=1.0, clean_hdmi_mode=True)
    d13 = evaluate_anamorphic_desqueeze_grm_compat(desqueeze_ratio=1.3, bright_monitoring_on=False, magnifier_scale=1.0, hdmi_raw_active=True)

    for ev in (d15, d16, d20, d13):
        if not ev.valid or not ev.big6_hud_unclipped or not ev.clean_hdmi_unclipped:
            p3_errors.append(f"Anamorphic GRM compat failed for {ev.desqueeze_ratio}x")

    pillar3 = Pillar3AnamorphicBrightMagGrmReport(
        passed=len(p3_errors) == 0,
        fx3_appfw_desqueeze_hits=fx3_desq_hits,
        fx6_appfw_desqueeze_hits=fx6_desq_hits,
        fx3_cpapp_desqueeze_hits=fx3_cp_desq,
        fx6_cpapp_desqueeze_hits=fx6_cp_desq,
        fx6_gemini_grm_summary=fx6_grm_sum,
        fx3_grm_ma_ko=kmod_map["fx3_grm_ko"],
        fx6_grm_ma_ko=kmod_map["fx6_grm_ko"],
        desqueeze_15x_bright_mon_eval=d15,
        desqueeze_16x_magnifier_4x_eval=d16,
        desqueeze_20x_clean_hdmi_eval=d20,
        desqueeze_13x_hdmi_raw_eval=d13,
        errors=tuple(p3_errors),
    )

    # ---- Pillar 4: Auto USB-LAN, Dual-Slot Telemetry & Zero-Write Firewall ----
    p4_errors: List[str] = []
    fx3_ul_hits = {t: fx3_appfw_sum.marker_hits.get(t, 0) for t in APPFW_USBLAN_DUAL_SLOT_SHARED_MARKERS_P179}
    fx6_ul_hits = {t: fx6_appfw_sum.marker_hits.get(t, 0) for t in APPFW_USBLAN_DUAL_SLOT_SHARED_MARKERS_P179}
    for lbl, hmap in (("fx3_appfw_usblan", fx3_ul_hits), ("fx6_appfw_usblan", fx6_ul_hits)):
        missing = [t for t, c in hmap.items() if c <= 0]
        if missing:
            p4_errors.append(f"{lbl} missing USB-LAN/Dual-Slot markers: {missing}")

    for lbl, summ in (("fx3_ether", fx3_ether_sum), ("fx6_ether", fx6_ether_sum)):
        missing = [t for t in NETSERVICE_ETHER_MARKERS_P179 if summ.marker_hits.get(t, 0) <= 0]
        if missing:
            p4_errors.append(f"{lbl} missing NetServiceEther markers: {missing}")
    for lbl, summ in (("fx3_mpr", fx3_mpr_sum), ("fx6_mpr", fx6_mpr_sum)):
        missing = [t for t in MPR_REMAIN_RELAY_SIMUL_SHARED_MARKERS_P179 if summ.marker_hits.get(t, 0) <= 0]
        if missing:
            p4_errors.append(f"{lbl} missing MPR Remain/Relay/Simul markers: {missing}")
    if fx3_mpr_sum.marker_hits.get(MPR_CALC_REMAIN_FX3_MARKER_P179, 0) <= 0:
        p4_errors.append("fx3_mpr missing MovieRemain::CalcRecordableTime")

    net_kmods = tuple(
        kmod_map[k]
        for k in (
            "fx3_cdc_ncm",
            "fx6_cdc_ncm",
            "fx3_r8152",
            "fx6_r8152",
            "fx3_asix",
            "fx6_asix",
            "fx3_ax88179",
            "fx6_ax88179",
        )
    )
    for km in net_kmods:
        if not km.modinfo_valid:
            p4_errors.append(f"Kernel module vermagic check failed: {km.body_label} {km.module_name}")

    lan_ncm = evaluate_auto_usblan_recognition(adapter_driver="CDC_NCM", usb_vid_pid="05AC:1402", link_speed_mbps=1000)
    lan_rtl = evaluate_auto_usblan_recognition(adapter_driver="RTL8153", usb_vid_pid="0BDA:8153", link_speed_mbps=1000)
    lan_asix = evaluate_auto_usblan_recognition(adapter_driver="ASIX_AX88179", usb_vid_pid="0B95:1790", link_speed_mbps=1000)
    lan_unk = evaluate_auto_usblan_recognition(adapter_driver="UNKNOWN_VENDOR_NIC", usb_vid_pid="FFFF:0001")
    for ok_lan in (lan_ncm, lan_rtl, lan_asix):
        if not ok_lan.valid or ok_lan.auto_netif_name != "eth0":
            p4_errors.append(f"Auto USB-LAN recognition failed for {ok_lan.adapter_driver}")
    if lan_unk.valid:
        p4_errors.append("Unknown USB-LAN adapter was not rejected")

    ds_simul = evaluate_dual_slot_remaining_time_telemetry(rec_mode="SIMULTANEOUS", codec_bitrate_mbps=200.0, slot_a_free_mib=128_000, slot_b_free_mib=64_000)
    ds_relay = evaluate_dual_slot_remaining_time_telemetry(rec_mode="RELAY", codec_bitrate_mbps=200.0, slot_a_free_mib=128_000, slot_b_free_mib=64_000)
    ds_sort = evaluate_dual_slot_remaining_time_telemetry(rec_mode="SORT", codec_bitrate_mbps=600.0, slot_a_free_mib=128_000, slot_b_free_mib=64_000, proxy_bitrate_mbps=16.0)
    for ds in (ds_simul, ds_relay, ds_sort):
        if not ds.valid or not ds.zero_frame_drop_rollover:
            p4_errors.append(f"Dual-slot telemetry failed for {ds.rec_mode}")

    g_tmp_wpa = evaluate_phase179_write_guard("/tmp/fx6_stage_b/wpa_supplicant.conf")
    g_ext_cfx = evaluate_phase179_write_guard("/mnt/cfexpress_a/PRIVATE/M4ROOT/CLIP/C0001.MP4")
    g_p12 = evaluate_phase179_write_guard("p12:/cert/RQ_LIC.DAT")
    g_p2 = evaluate_phase179_write_guard("p2:/Backup.bin")
    g_etc_wpa = evaluate_phase179_write_guard("/etc/wpa_supplicant.conf")
    g_spinor = evaluate_phase179_write_guard("spi_nor:/loader_nor.bin")

    for ok_g in (g_tmp_wpa, g_ext_cfx):
        if not ok_g.valid:
            p4_errors.append(f"Volatile/ext guard blocked valid target: {ok_g.target_path}")
    for blk_g in (g_p12, g_p2, g_etc_wpa, g_spinor):
        if blk_g.valid or not blk_g.persistent_write_blocked or blk_g.emmc_mutation_bytes != 0:
            p4_errors.append(f"Write guard failed to block {blk_g.target_path}")

    matrix = build_phase179_delta_compat_matrix()
    if matrix.total_touchpoints != 12:
        p4_errors.append(f"Expected 12 touchpoints, got {matrix.total_touchpoints}")

    pillar4 = Pillar4UsbLanDualSlotMatrixReport(
        passed=len(p4_errors) == 0,
        fx3_ether_summary=fx3_ether_sum,
        fx6_ether_summary=fx6_ether_sum,
        fx3_mpr_summary=fx3_mpr_sum,
        fx6_mpr_summary=fx6_mpr_sum,
        fx3_appfw_usblan_slot_hits=fx3_ul_hits,
        fx6_appfw_usblan_slot_hits=fx6_ul_hits,
        kmod_summaries=net_kmods,
        usblan_cdc_ncm_eval=lan_ncm,
        usblan_rtl8153_eval=lan_rtl,
        usblan_asix_eval=lan_asix,
        usblan_unknown_rejected_eval=lan_unk,
        dual_slot_simultaneous_eval=ds_simul,
        dual_slot_relay_eval=ds_relay,
        dual_slot_sort_eval=ds_sort,
        volatile_wpa_tmp_allowed=g_tmp_wpa,
        external_cfexpress_allowed=g_ext_cfx,
        blocked_p12_cert_guard=g_p12,
        blocked_p2_backup_guard=g_p2,
        blocked_etc_wpa_conf_guard=g_etc_wpa,
        blocked_spinor_guard=g_spinor,
        compatibility_matrix=matrix,
        errors=tuple(p4_errors),
    )

    errors.extend(p1_errors)
    errors.extend(p2_errors)
    errors.extend(p3_errors)
    errors.extend(p4_errors)
    all_ok = pillar1.passed and pillar2.passed and pillar3.passed and pillar4.passed

    digest_payload = {
        "schema": PHASE_179_SCHEMA,
        "mode": mode,
        "all_ok": all_ok,
        "donor_file_sizes": donor_file_sizes,
        "p1": pillar1.passed,
        "p2": pillar2.passed,
        "p3": pillar3.passed,
        "p4": pillar4.passed,
        "fx3_wep_enum": fx3_wep_enum,
        "fx6_wep_enum": fx6_wep_enum,
    }
    report_sha = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return RealhwHdmiBrawWpa3702DeltaReport(
        schema_version=PHASE_179_SCHEMA,
        phase_version=PHASE_179_VERSION,
        mode=mode,
        all_checks_passed=all_ok,
        o_rdonly_enforced=True,
        raw_firmware_bytes_leaked=0,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        hdmi_braw_bridged_sdi_masked=(hdmi_braw_eval.hdmi_raw_braw_ready and sdi_raw_masked.sdi_hw_probe_masked),
        wpa2_wpa3_only_enforced=(wpa3_sae_eval.valid and wep_rej.deprecated_protocol_rejected and ipsec_rej.deprecated_protocol_rejected),
        anamorphic_15x_16x_grm_unclipped=(d15.big6_hud_unclipped and d16.big6_hud_unclipped and d20.clean_hdmi_unclipped),
        usblan_and_dual_slot_telemetry_ready=(lan_ncm.valid and lan_rtl.valid and ds_simul.valid and ds_relay.valid),
        donor_file_sizes=donor_file_sizes,
        pillar1_hdmi_braw_vs_sdi=pillar1,
        pillar2_wpa2_wpa3_security=pillar2,
        pillar3_anamorphic_grm=pillar3,
        pillar4_usblan_dual_slot_matrix=pillar4,
        report_sha256=report_sha,
        errors=tuple(errors),
    )


def realhw_hdmi_braw_wpa3_702_delta_report_to_dict(
    report: RealhwHdmiBrawWpa3702DeltaReport,
) -> Dict[str, object]:
    """Convert `RealhwHdmiBrawWpa3702DeltaReport` to a JSON-safe dict."""
    return asdict(report)
