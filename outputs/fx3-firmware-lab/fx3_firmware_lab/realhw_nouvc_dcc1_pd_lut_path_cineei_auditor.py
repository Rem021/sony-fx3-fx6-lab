"""Phase 192 — 40th Milestone Firmware-Lab Auditor (40/40): Real-Hardware
`ILME-FX3` (`Ver. 7.02`) No-UVC USB Gadget Stack, `USB-PD` (`NP-FZ100`) vs
`DC-C1` (`>=65W / 5A`) Power-Budget, Dual-Media `.cube` User LUT Path-Asymmetry
(`SD` vs `CFexpress-A`) & `Cine EI` (`800 / 12800`) Auditor.

Strictly Read-Only (`os.O_RDONLY` + `os.pread` bounded section inspection) &
Clean-Room Dual-Mode:
- Local Donor Mode: inspects Stock FX3 `Ver. 7.02` (`4.9.337-scel+` init scripts
  `insmod_drv2`/`usb_insmod.sh` and `.ko` modules `usb_buspwr.ko`, `cdc_ncm.ko`,
  `usbg_storage.ko`, `usbg_stillimage.ko`, `usb_f_uvc.ko`; userland USB/streaming
  daemons `libInfraUsbCmn.so`, `libUsbControl.so`, `libUsbBusPower.so`,
  `libInfraVericLiveStreaming.so`, `libInfraRtmpLiveStreaming.so`,
  `libInfraSrtLiveStreaming.so`; `appFw.so`, `libmpr.so`, `cpapp-b.bin`) vs FX6
  `Ver. 6.01` (`appFw.so`, `libInfraUsbCmn.so`) strictly via `os.O_RDONLY` +
  bounded `os.pread` (< 0.15 s cold, cached per process).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room Elf64 `.so`, `cpapp-b.bin`
  token buffers, `4.9.337-scel+` `.ko` modinfo blobs, and init script buffers
  with zero proprietary bytes leaked (`raw_firmware_bytes_leaked == 0`).

Audits Four Core Real-Hardware Pillars:
1. Pillar 1 (`NOUVC_GADGET_AND_NETWORK_STREAMING`):
   Audits Stock FX3 `4.9.337-scel+` USB composite gadget stack (`Sel. When Connect`,
   `MassStorage(MSC)`, `MTP`, `Remote Shooting` `1024x576` no-audio legacy cap,
   and `USB-LAN` `CDC-NCM`/`RNDIS` auto-connect), proving native `[USB Streaming]`
   UVC/UAC gadget absence on `ILME-FX3` (`0x91030080`) / `ILME-FX3A` (`0x91030082`)
   vs `ILME-FX30` / `ILME-FX2` / `ILME-FX6`, masking Stage-B UVC descriptor calls
   while preserving `7.00/7.02` `USB-LAN` auto-connect and `4K 59.94p 38 Mbps`
   (`RTMP/RTMPS/SRT`, `HEVC/AVC`) Network Streaming.
2. Pillar 2 (`POWER_DELIVERY_USB_PD_VS_DCC1`):
   Models the exact electrical power-state machine: mandatory `NP-FZ100`
   presence for body Type-C `USB Power Supply = On`, charging pause while camera
   is powered on (resuming on power-off), strict rejection of Micro-USB power,
   and `DC-C1` DC coupler (`>=65W` USB-PD + `5A` e-Marker cable budget, freeing
   body Type-C for `USB-LAN` / `Creators' App`, and LCD max-brightness lock).
3. Pillar 3 (`LUT_PATH_ASYMMETRY_CINE_EI_AND_RMT_P1BT`):
   Audits `.cube` parser invariants (`LUT_3D_SIZE 17` / `33`, `<= 63` ASCII
   bytes filename, `User1..User16`, `AE Level Offset 0..+2 EV` in `1/3 EV` steps,
   zero direct Stage-B writes to Stock `p2:/setting`), dual-media path asymmetry
   (`SD: /Private/Sony/PRO/LUT/` vs `CFexpress-A: /Sony/PRO/LUT/`), `Cine EI`
   dual base ISO (`800` / `12800`, `3200..51200 EI` @ `12800` without CMOS gain
   pollution), `Creators' Cloud` `OK/NG/KEEP` clip-flag filter (`Creators' App >=
   3.1.0`, `M&C >= 2.4.0`), and `Bluetooth Rmt Ctrl = On` (`RMT-P1BT`) mutual
   exclusion disabling IR remote & GPS location link.
4. Pillar 4 (`ZERO_WRITE_FIREWALL_AND_12TP_MATRIX`):
   Enforces hard safety invariants (`persistent_emmc_writes_authorized = False`,
   `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`,
   `physical_usb_packets_emitted = 0`, `raw_firmware_bytes_leaked = 0`) and
   builds a 12-touchpoint 4-class compatibility matrix across Pillars 1..3.
"""

from __future__ import annotations

import hashlib
import json
import math
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
from .realhw_fx3_vs_fx3a_and_xlrh1_mishoe_auditor import (
    _count_tokens_ordered_single_pass,
    _scan_elf_buf_ordered,
    _scan_elf_fast_rdonly,
    _scan_flat_fast_rdonly,
)
from .realhw_hdmi_braw_wpa3_702_delta_auditor import (
    FX3_CDC_NCM_KO_RELPATH,
    SCEL_KERNEL_VERMAGIC_P179,
    KernelModuleInfoSummary,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    FX3_APPFW_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX3_LIBMPR_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
)
from .realhw_wifi_bt_usb_uvc_network_bridge_auditor import (
    FX3_LIBINFRA_USB_CMN_RELPATH,
    FX3_LIBUSB_CONTROL_RELPATH,
    FX6_LIBINFRA_USB_CMN_RELPATH,
)
from .ufu_container_auditor import MODEL_ID_FX3, MODEL_ID_FX3A, MODEL_ID_FX6


PHASE_192_SCHEMA = "fx3_firmware_lab_phase192_realhw_nouvc_dcc1_pd_lut_path_cineei_v1"
PHASE_192_VERSION = "192.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + bounded os.pread)
# ---------------------------------------------------------------------------

_FX3_USR_LIB_P192 = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
)
_FX3_FULLV4_P192 = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/full-v4/regular-files"
)

FX3_APPFW_P192_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P192_RELPATH = FX6_APPFW_P146_RELPATH
FX3_LIBMPR_P192_RELPATH = FX3_LIBMPR_P146_RELPATH
FX3_CPAPP_P192_RELPATH = FX3_CPAPP_P146_RELPATH
FX3_LIBINFRA_USB_CMN_P192_RELPATH = FX3_LIBINFRA_USB_CMN_RELPATH
FX6_LIBINFRA_USB_CMN_P192_RELPATH = FX6_LIBINFRA_USB_CMN_RELPATH
FX3_LIBUSB_CONTROL_P192_RELPATH = FX3_LIBUSB_CONTROL_RELPATH
FX3_LIBUSB_BUS_POWER_P192_RELPATH = f"{_FX3_USR_LIB_P192}/libUsbBusPower.so"
FX3_LIBINFRA_VERIC_STREAM_P192_RELPATH = f"{_FX3_USR_LIB_P192}/libInfraVericLiveStreaming.so"
FX3_LIBINFRA_RTMP_STREAM_P192_RELPATH = f"{_FX3_USR_LIB_P192}/libInfraRtmpLiveStreaming.so"
FX3_LIBINFRA_SRT_STREAM_P192_RELPATH = f"{_FX3_USR_LIB_P192}/libInfraSrtLiveStreaming.so"

FX3_USB_BUSPWR_KO_P192_RELPATH = f"{_FX3_FULLV4_P192}/usr/kmod/usb_buspwr.ko"
FX3_CDC_NCM_KO_P192_RELPATH = FX3_CDC_NCM_KO_RELPATH
FX3_USBG_STORAGE_KO_P192_RELPATH = f"{_FX3_FULLV4_P192}/usr/kmod/usbg_storage.ko"
FX3_USBG_STILLIMAGE_KO_P192_RELPATH = f"{_FX3_FULLV4_P192}/usr/kmod/usbg_stillimage.ko"
FX3_USB_F_UVC_KO_P192_RELPATH = f"{_FX3_FULLV4_P192}/usr/kmod/usb_f_uvc.ko"
FX3_INSMOD_DRV2_P192_RELPATH = f"{_FX3_FULLV4_P192}/sbin/initrc/insmod_drv2"
FX3_USB_INSMOD_SH_P192_RELPATH = f"{_FX3_FULLV4_P192}/usr/bin/usb_insmod.sh"

# ---------------------------------------------------------------------------
# Verified Expected Donor Sizes
# ---------------------------------------------------------------------------

EXPECTED_FX3_APPFW_BYTES_P192 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P192 = 50_520_424
EXPECTED_FX3_MPR_BYTES_P192 = 3_517_008
EXPECTED_FX3_CPAPP_BYTES_P192 = 15_980_568
EXPECTED_FX3_USBCMN_BYTES_P192 = 159_504
EXPECTED_FX6_USBCMN_BYTES_P192 = 164_144
EXPECTED_FX3_USBCTL_BYTES_P192 = 135_424
EXPECTED_FX3_USBBP_BYTES_P192 = 48_232
EXPECTED_FX3_VERIC_BYTES_P192 = 182_472
EXPECTED_FX3_RTMP_BYTES_P192 = 85_960
EXPECTED_FX3_SRT_BYTES_P192 = 90_248
EXPECTED_USB_BUSPWR_KO_BYTES_P192 = 27_728
EXPECTED_CDC_NCM_KO_BYTES_P192 = 32_208
EXPECTED_USBG_STORAGE_KO_BYTES_P192 = 104_288
EXPECTED_USBG_STILLIMAGE_KO_BYTES_P192 = 49_448
EXPECTED_USB_F_UVC_KO_BYTES_P192 = 78_840

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 1 (No-UVC, Network Streaming, USB-LAN)
# ---------------------------------------------------------------------------

MODEL_ID_FX3_P192 = MODEL_ID_FX3  # 0x91030080
MODEL_ID_FX3A_P192 = MODEL_ID_FX3A  # 0x91030082
MODEL_ID_FX30_P192 = 0x91030081
MODEL_ID_FX2_P192 = 0x91030085
MODEL_ID_FX6_P192 = MODEL_ID_FX6  # 0x91030060

SCEL_KERNEL_RELEASE_P192 = "4.9.337-scel+"
SCEL_KERNEL_VERMAGIC_P192 = SCEL_KERNEL_VERMAGIC_P179

NATIVE_UVC_ABSENT_BODIES_P192: Tuple[str, ...] = ("ILME-FX3", "ILME-FX3A")
NATIVE_UVC_CAPABLE_BODIES_P192: Tuple[str, ...] = ("ILME-FX30", "ILME-FX2", "ILME-FX6")

FX3_USB_CONNECTION_MODES_P192: Tuple[str, ...] = (
    "SEL_WHEN_CONNECT",
    "MASS_STORAGE_MSC",
    "MTP",
    "REMOTE_SHOOTING",
    "USB_LAN",
)
VALID_REQUESTED_USB_MODES_P192: Tuple[str, ...] = FX3_USB_CONNECTION_MODES_P192 + ("USB_STREAMING",)

REMOTE_SHOOTING_LEGACY_MAX_WIDTH = 1024
REMOTE_SHOOTING_LEGACY_MAX_HEIGHT = 576
REMOTE_SHOOTING_LEGACY_AUDIO_CHANNELS = 0

VALID_NETWORK_STREAMING_PROTOCOLS_P192: Tuple[str, ...] = ("RTMP", "RTMPS", "SRT")
VALID_NETWORK_STREAMING_CODECS_P192: Tuple[str, ...] = ("HEVC", "AVC")
NETWORK_STREAMING_MAX_WIDTH_P192 = 3840
NETWORK_STREAMING_MAX_HEIGHT_P192 = 2160
NETWORK_STREAMING_MAX_FPS_P192 = 59.94
NETWORK_STREAMING_MAX_BITRATE_MBPS_P192 = 38.0
VALID_USB_LAN_DRIVERS_P192: Tuple[str, ...] = ("CDC_NCM", "RNDIS", "RTL8153", "ASIX_AX88179")

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 2 (USB-PD NP-FZ100 vs DC-C1 >=65W/5A Power Matrix)
# ---------------------------------------------------------------------------

VALID_POWER_SOURCES_P192: Tuple[str, ...] = (
    "BODY_USBC_PD",
    "DC_C1_COUPLER",
    "MICRO_USB",
    "INTERNAL_BATTERY_ONLY",
)
USB_PD_BODY_MIN_WATTS_P192 = 18.0
USB_PD_BODY_REC_WATTS_P192 = 27.0
DCC1_MIN_PD_WATTS_P192 = 65.0
DCC1_REQUIRED_CABLE_CURRENT_A_P192 = 5.0

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 3 (LUT Path Asymmetry, Cine EI, RMT-P1BT, Cloud)
# ---------------------------------------------------------------------------

VALID_LUT_MEDIA_TYPES_P192: Tuple[str, ...] = ("SD", "CFEXPRESS_A")
SD_USER_LUT_DIR_P192 = "/Private/Sony/PRO/LUT/"
CFEXPRESS_A_USER_LUT_DIR_P192 = "/Sony/PRO/LUT/"
SUPPORTED_CUBE_3D_SIZES_P192: Tuple[int, ...] = (17, 33)
MAX_CUBE_FILENAME_ASCII_BYTES_P192 = 63
MAX_USER_LUT_SLOTS_P192 = 16
VALID_AE_LEVEL_OFFSET_THIRDS_P192: Tuple[int, ...] = (0, 1, 2, 3, 4, 5, 6)  # 0 .. +2.0 EV (1/3 steps)

CINE_EI_BASE_ISOS_P192: Tuple[int, ...] = (800, 12800)
CINE_EI_LOW_BASE_RANGE_P192: Tuple[int, int] = (200, 3200)
CINE_EI_HIGH_BASE_RANGE_P192: Tuple[int, int] = (3200, 51200)

CREATORS_APP_MIN_VERSION_P192: Tuple[int, int, int] = (3, 1, 0)
MONITOR_CONTROL_MIN_VERSION_P192: Tuple[int, int, int] = (2, 4, 0)
VALID_CLIP_FLAG_FILTERS_P192: Tuple[str, ...] = ("NONE", "OK", "NG", "KEEP", "ALL")

# ---------------------------------------------------------------------------
# Verified Donor Binary Marker Catalogs (strictly O_RDONLY bounded read)
# ---------------------------------------------------------------------------

APPFW_FX3_NOUVC_STREAMING_MARKERS_P192: Tuple[str, ...] = (
    "USB_CONNECTION_METHOD_MASS_STRAGE",
    "USB_CONNECTION_METHOD_MTP",
    "USB_CONNECTION_METHOD_ETHER",
    "USB_CONNECTION_SELECT_AFTER_CONNECTION",
    "USB_CONNECTION_REMOTE_PC",
    "USB_LAN_CONNECT_LAUNCH_ON",
    "USB_LAN_CONNECT_LAUNCH_OFF",
    "USB_LAN_FUNCTION_INTERNAL_STATE_CONNECTED",
    "VAL_system_mode_option_SYSTEM_MODE_OPTION_USB_LAN_AND_TETHERING",
    "MODEL_NETWORK_STREAMING_STATE_CHANGED",
    "NOT_DELAY_NETWORK_STREAMING_MODE_ON",
    "USB_STREAMING_STATE_OFF",
)

APPFW_FX6_PROCAM_UVC_MARKERS_P192: Tuple[str, ...] = (
    "BKID_APP_SETTING_USB_STREAMING_PROCAM",
    "BKID_APP_SETTING_USB_STREAMING_FORMAT_PROCAM",
    "BKID_APP_SETTING_USB_STREAMING_AUDIO_PROCAM",
    "USB_CONNECTION_USB_STREAMING",
    "USB_CONNECTION_PORT1_USB_STREAMING",
)

APPFW_FX3_USB_POWER_MARKERS_P192: Tuple[str, ...] = (
    "VAL_supplying_usb_power_state_SUPPLYING_USB_POWER_STATE_ON",
    "VAL_supplying_usb_power_state_SUPPLYING_USB_POWER_STATE_OFF",
    "USB_CONNECTED_PORT_TYPE_C",
    "USB_CONNECTED_PORT_MULTI_MICRO",
    "LOW_BATT",
    "OFF_BY_BATT_END",
    "OFF_BY_BATT_END_FAKE",
    "INFRA_NOTIFY_BATTERY_REMAIN",
)

APPFW_FX3_LUT_CINEEI_BT_MARKERS_P192: Tuple[str, ...] = (
    "/Private/Sony/PRO/LUT",
    "LUT_3D_SIZE",
    "VAL_HAITA_is_exist_user_lut_cube_file_import_to_user_lut_id_req_IS_EXIST_USER_LUT_EMPTY_SELECT_LUT_USER1",
    "VAL_HAITA_is_exist_user_lut_cube_file_import_to_user_lut_id_req_IS_EXIST_USER_LUT_EMPTY_SELECT_LUT_USER16",
    "VAL_setting_ae_level_offset_AE_LEVEL_OFFSET_0EV",
    "VAL_setting_ae_level_offset_AE_LEVEL_OFFSET_1_3EV",
    "VAL_setting_ae_level_offset_AE_LEVEL_OFFSET_2EV",
    "VAL_setting_log_shooting_LOG_SHOOTING_CINE_EI",
    "VAL_setting_log_shooting_LOG_SHOOTING_CINE_EI_QUICK",
    "FTP_TRANSFER_FUNC_TARGET_IMG_CLIP_FLAG_OK",
    "FTP_TRANSFER_FUNC_TARGET_IMG_CLIP_FLAG_NG",
    "FTP_TRANSFER_FUNC_TARGET_IMG_CLIP_FLAG_KEEP",
    "VAL_setting_bluetooth_remote_ctrl_BLUETOOTH_REMOTE_CTRL_ON",
    "CAUTION_ID_FACTOR_BLUETOOTH_REMOTE_CTRL_ON_MSG",
    "VAL_setting_ir_remote_ctrl_IR_REMOTE_CTRL_OFF",
    "VAL_setting_ir_remote_ctrl_IR_REMOTE_CTRL_ON",
    "LOCATION_INFO_LINK_START",
    "EVENT_REMOTE_LOCATION_INFO_LINK",
)

USB_CMN_GADGET_MARKERS_P192: Tuple[str, ...] = (
    "CUsbGadgetStorage",
    "CUsbGadgetStill",
    "CUsbGadgetStreaming",
)

USB_CTL_MARKERS_P192: Tuple[str, ...] = (
    "GADGET_CMD",
    "GADGET_CMP",
    "MTP_EVT",
)

USB_BUSPOWER_MARKERS_P192: Tuple[str, ...] = (
    "_ZN11UsbBusPower11IsVbusReadyEv",
    "_ZN11UsbBusPower11SetPortRoleEi",
    "_ZN11UsbBusPower15GetCurrentLimitEv",
    "_ZN11UsbBusPower12IgnoreCurLmtEv",
    "USB_BUSPW_VBUS_STATUS",
    "USB_BUSPW_BUSPOWER_STATUS",
)

VERIC_STREAMING_MARKERS_P192: Tuple[str, ...] = (
    "VericLiveStreaming",
    "VericEsCodecLibrary",
)

RTMP_STREAMING_MARKERS_P192: Tuple[str, ...] = (
    "RtmpLiveStreaming",
    "RTMP_GST_ERR_CONNECT_FAIL",
)

SRT_STREAMING_MARKERS_P192: Tuple[str, ...] = (
    "SrtLiveStreaming",
    "SRT_PKTLOSS",
    "SRT_MSRTT",
)

MPR_LUT_CINE_MARKERS_P192: Tuple[str, ...] = (
    "LUT_3D_SIZE",
    "_ZN3mpr10SetLutData",
    "GetCubeFilePath",
)

CPAPP_BATT_MARKERS_P192: Tuple[str, ...] = (
    "ACV_BATT_Snd",
    "BATT_AUTH_Snd",
    "C_ImagerCtrl_IMX510",
)

# ---------------------------------------------------------------------------
# Write-Firewall Patterns
# ---------------------------------------------------------------------------

VOLATILE_OR_EXT_PREFIXES_P192: Tuple[str, ...] = (
    "/tmp/",
    "/tmp_wbshd/",
    "ram://",
    "memfd:",
    "/mnt/sd/",
    "/mnt/sd2/",
    "/mnt/cfexpress_a/",
)

FORBIDDEN_PERSISTENT_TARGET_RE_P192 = re.compile(
    r"(?:"
    r"^/dev/(?:[cp]?nflasha\d*|mmcblk0(?:p\d+|rpmb)?|rtc0)"
    r"|^p(?:0|1|2|3|5|6|7|8|12|13|15|18):/"
    r"|^/(?:wbi|setting|cert|lens)(?:/|$)"
    r"|^spi_nor:"
    r"|^sector0:"
    r"|Backup\.bin$"
    r"|cpapp-b\.bin$"
    r"|BODYDATA\.DAT$"
    r"|CAMSET.*\.DAT$"
    r"|loader_nor\.bin$"
    r")",
    re.IGNORECASE,
)

_CUBE_FILENAME_ASCII_RE = re.compile(r"^[A-Za-z0-9._-]+\.cube$")

# In-process cache for O_RDONLY donor inspection (< 0.15s cold, < 1ms warm)
_DONOR_SCAN_CACHE: Dict[Tuple[str, ...], Dict[str, object]] = {}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class NoUvcGadgetAndStreamingEvalResult:
    valid: bool
    body_model: str
    model_id_hex: str
    requested_usb_mode: str
    native_uvc_supported: bool
    uvc_masked_by_stage_b: bool
    uvc_gadget_rejected: bool
    usb_phy_lockup_prevented: bool
    legacy_imaging_edge_cap: str
    streaming_protocol: str
    streaming_resolution: str
    streaming_fps: float
    streaming_bitrate_mbps: float
    streaming_codec: str
    usb_lan_auto_connect_702: bool
    usb_lan_driver: str
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PowerDeliveryMatrixEvalResult:
    valid: bool
    power_source: str
    np_fz100_inserted: bool
    pd_adapter_watts: float
    cable_current_rating_a: float
    cable_has_emarker: bool
    camera_powered_on: bool
    power_accepted: bool
    internal_charging_active: bool
    charging_paused_during_operation: bool
    micro_usb_power_rejected: bool
    type_c_freed_for_usblan: bool
    dcc1_led_blinking_warning: bool
    lcd_max_brightness_locked: bool
    brownout_shutdown_risk: bool
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UserLutPathAndCineEiEvalResult:
    valid: bool
    media_type: str
    submitted_dir: str
    expected_dir: str
    path_asymmetry_ok: bool
    cube_filename: str
    filename_ascii_bytes: int
    lut_3d_size: int
    cube_voxel_count: int
    user_lut_slot: str
    ae_level_offset_ev: float
    cine_ei_base_iso: int
    cine_ei_index: int
    cmos_analog_gain_polluted: bool
    stage_b_target_path: str
    volatile_staged: bool
    persistent_writes: int
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RmtP1btAndCloudClipFlagEvalResult:
    valid: bool
    body_model: str
    bluetooth_rmt_ctrl_on: bool
    ir_remote_requested: bool
    gps_link_requested: bool
    effective_ir_remote_active: bool
    effective_gps_link_active: bool
    hardware_ir_present: bool
    hardware_nfc_present: bool
    bt_ir_gps_mutual_exclusion_enforced: bool
    creators_app_version: str
    monitor_control_version: str
    clip_flag_filter: str
    cloud_version_gate_ok: bool
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase192WriteGuardResult:
    valid: bool
    target_path: str
    volatile_or_ext_allowed: bool
    persistent_write_blocked: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    persistent_writes: int
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase192TouchpointEntry:
    touchpoint_id: str
    pillar: str
    fx6_or_host_component: str
    fx3_target: str
    bridge_class: str
    safety_invariant: str


@dataclass(frozen=True)
class Phase192CompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    pillar_counts: Dict[str, int]
    touchpoints: Tuple[Phase192TouchpointEntry, ...]


@dataclass(frozen=True)
class Pillar1NoUvcGadgetStreamingReport:
    passed: bool
    fx3_appfw_usb_stream_hits: Dict[str, int]
    fx6_appfw_procam_uvc_hits: Dict[str, int]
    fx3_usbcmn_summary: ElfSectionSummary
    fx6_usbcmn_summary: ElfSectionSummary
    fx3_usbctl_summary: ElfSectionSummary
    fx3_veric_summary: ElfSectionSummary
    fx3_rtmp_summary: ElfSectionSummary
    fx3_srt_summary: ElfSectionSummary
    kmod_cdc_ncm: KernelModuleInfoSummary
    kmod_usbg_storage: KernelModuleInfoSummary
    kmod_usbg_stillimage: KernelModuleInfoSummary
    kmod_usb_f_uvc: KernelModuleInfoSummary
    uvc_loaded_in_boot_insmod: bool
    eval_fx3_uvc_unmasked_rejected: NoUvcGadgetAndStreamingEvalResult
    eval_fx3_stage_b_uvc_masked: NoUvcGadgetAndStreamingEvalResult
    eval_fx3_4k60_srt_usblan_auto: NoUvcGadgetAndStreamingEvalResult
    eval_fx3_remote_shooting_legacy: NoUvcGadgetAndStreamingEvalResult
    eval_fx30_native_uvc_allowed: NoUvcGadgetAndStreamingEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2PowerDeliveryMatrixReport:
    passed: bool
    fx3_appfw_power_hits: Dict[str, int]
    fx3_usbbp_summary: ElfSectionSummary
    fx3_cpapp_batt_hits: Dict[str, int]
    kmod_usb_buspwr: KernelModuleInfoSummary
    eval_body_pd_with_battery_on: PowerDeliveryMatrixEvalResult
    eval_body_pd_with_battery_off_charging: PowerDeliveryMatrixEvalResult
    eval_body_pd_without_battery_rejected: PowerDeliveryMatrixEvalResult
    eval_micro_usb_rejected: PowerDeliveryMatrixEvalResult
    eval_dcc1_65w_5a_emarker_accepted: PowerDeliveryMatrixEvalResult
    eval_dcc1_45w_3a_rejected: PowerDeliveryMatrixEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3LutPathCineEiRmtReport:
    passed: bool
    fx3_appfw_lut_cine_bt_hits: Dict[str, int]
    fx3_mpr_lut_summary: ElfSectionSummary
    eval_sd_33pt_cine_ei_12800_ok: UserLutPathAndCineEiEvalResult
    eval_cfexpress_17pt_ok: UserLutPathAndCineEiEvalResult
    eval_cfexpress_wrong_private_prefix_rejected: UserLutPathAndCineEiEvalResult
    eval_sd_missing_private_prefix_rejected: UserLutPathAndCineEiEvalResult
    eval_filename_over_63b_rejected: UserLutPathAndCineEiEvalResult
    eval_p2_setting_direct_write_blocked: UserLutPathAndCineEiEvalResult
    eval_rmt_p1bt_fx3_bt_excludes_ir_gps: RmtP1btAndCloudClipFlagEvalResult
    eval_rmt_p1bt_fx3a_no_ir_nfc: RmtP1btAndCloudClipFlagEvalResult
    eval_creators_cloud_clip_flag_ok: RmtP1btAndCloudClipFlagEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4WriteGuardAndMatrixReport:
    passed: bool
    blocked_p2_setting_eval: Phase192WriteGuardResult
    blocked_emmc_nflasha_eval: Phase192WriteGuardResult
    blocked_backup_bin_eval: Phase192WriteGuardResult
    allowed_tmp_overlay_eval: Phase192WriteGuardResult
    allowed_sd_lut_eval: Phase192WriteGuardResult
    compatibility_matrix: Phase192CompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwNouvcDcc1PdLutPathCineeiReport:
    schema_version: str
    phase_version: str
    mode: str
    cache_hit: bool
    all_checks_passed: bool
    o_rdonly_enforced: bool
    raw_firmware_bytes_leaked: int
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    persistent_writes: int
    nouvc_and_network_streaming_verified: bool
    power_delivery_pd_vs_dcc1_verified: bool
    lut_path_cine_ei_and_rmt_p1bt_verified: bool
    write_firewall_and_matrix_verified: bool
    donor_file_sizes: Dict[str, int]
    pillar_1_nouvc_streaming: Pillar1NoUvcGadgetStreamingReport
    pillar_2_power_delivery: Pillar2PowerDeliveryMatrixReport
    pillar_3_lut_cine_ei_rmt: Pillar3LutPathCineEiRmtReport
    pillar_4_write_guard_matrix: Pillar4WriteGuardAndMatrixReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Helpers — Path Normalization, .cube Validation & Bounded O_RDONLY Scanners
# ---------------------------------------------------------------------------


def _normalize_lut_dir(path_str: str) -> str:
    clean = path_str.strip().replace("\\", "/")
    if not clean.startswith("/"):
        clean = "/" + clean
    if not clean.endswith("/"):
        clean = clean + "/"
    return clean


def _parse_semver(ver: str) -> Tuple[int, int, int]:
    parts = [int(p) for p in ver.strip().split(".")]
    while len(parts) < 3:
        parts.append(0)
    return (parts[0], parts[1], parts[2])


def validate_cube_text_bounded(cube_text: str) -> Tuple[bool, int, int, Tuple[str, ...]]:
    """Validate `.cube` header (`LUT_3D_SIZE 17|33`) and finite RGB voxel count."""
    size = 0
    voxels = 0
    errors: List[str] = []
    for raw_ln in cube_text.splitlines():
        ln = raw_ln.strip()
        if not ln or ln.startswith("#"):
            continue
        if ln.startswith(("TITLE", "DOMAIN_MIN", "DOMAIN_MAX", "LUT_3D_INPUT_RANGE")):
            continue
        if ln.startswith("LUT_1D_SIZE"):
            errors.append("UNSUPPORTED_1D_CUBE_LUT")
            continue
        if ln.startswith("LUT_3D_SIZE"):
            parts = ln.split()
            if len(parts) != 2 or not parts[1].isdigit():
                errors.append(f"MALFORMED_LUT_3D_SIZE: {ln}")
            else:
                size = int(parts[1])
                if size not in SUPPORTED_CUBE_3D_SIZES_P192:
                    errors.append(f"UNSUPPORTED_LUT_3D_SIZE: {size}")
            continue
        cols = ln.split()
        if len(cols) != 3:
            errors.append(f"MALFORMED_CUBE_VOXEL_ROW: {ln}")
            break
        for c in cols:
            try:
                val = float(c)
            except ValueError:
                errors.append(f"NON_NUMERIC_CUBE_VOXEL: {c}")
                break
            if not math.isfinite(val):
                errors.append("NON_FINITE_CUBE_VOXEL")
                break
        if errors:
            break
        voxels += 1

    if size not in SUPPORTED_CUBE_3D_SIZES_P192:
        if not any("LUT_3D_SIZE" in e for e in errors):
            errors.append("MISSING_VALID_LUT_3D_SIZE")
    elif voxels != size ** 3:
        errors.append(f"VOXEL_COUNT_MISMATCH: got {voxels}, expected {size ** 3}")
    return len(errors) == 0, size, voxels, tuple(errors)


# ---------------------------------------------------------------------------
# Pillar 1..4 Evaluators
# ---------------------------------------------------------------------------


def evaluate_nouvc_gadget_and_network_streaming(
    *,
    body_model: str = "ILME-FX3",
    requested_usb_mode: str = "USB_LAN",
    stage_b_mask_uvc: bool = True,
    streaming_protocol: str = "SRT",
    streaming_width: int = 3840,
    streaming_height: int = 2160,
    streaming_fps: float = 59.94,
    streaming_bitrate_mbps: float = 38.0,
    streaming_codec: str = "HEVC",
    usb_lan_auto_connect: bool = True,
    usb_lan_driver: str = "CDC_NCM",
) -> NoUvcGadgetAndStreamingEvalResult:
    """Audit FX3 native UVC absence vs Network Streaming (RTMP/RTMPS/SRT <=38Mbps) & USB-LAN."""
    errors: List[str] = []
    body = body_model.strip().upper()
    usb_mode = requested_usb_mode.strip().upper()
    proto = streaming_protocol.strip().upper()
    codec = streaming_codec.strip().upper()
    drv = usb_lan_driver.strip().upper()

    model_id_map = {
        "ILME-FX3": MODEL_ID_FX3_P192,
        "ILME-FX3A": MODEL_ID_FX3A_P192,
        "ILME-FX30": MODEL_ID_FX30_P192,
        "ILME-FX2": MODEL_ID_FX2_P192,
        "ILME-FX6": MODEL_ID_FX6_P192,
    }
    if body not in model_id_map:
        errors.append(f"UNKNOWN_BODY_MODEL: {body_model}")
    if usb_mode not in VALID_REQUESTED_USB_MODES_P192:
        errors.append(f"UNKNOWN_USB_CONNECTION_MODE: {requested_usb_mode}")
    if proto not in VALID_NETWORK_STREAMING_PROTOCOLS_P192:
        errors.append(f"UNKNOWN_STREAMING_PROTOCOL: {streaming_protocol}")
    if codec not in VALID_NETWORK_STREAMING_CODECS_P192:
        errors.append(f"UNKNOWN_STREAMING_CODEC: {streaming_codec}")
    if drv not in VALID_USB_LAN_DRIVERS_P192:
        errors.append(f"UNKNOWN_USBLAN_DRIVER: {usb_lan_driver}")

    if (
        streaming_width <= 0
        or streaming_height <= 0
        or streaming_width > NETWORK_STREAMING_MAX_WIDTH_P192
        or streaming_height > NETWORK_STREAMING_MAX_HEIGHT_P192
    ):
        errors.append(f"STREAMING_RESOLUTION_OUT_OF_RANGE: {streaming_width}x{streaming_height}")
    if streaming_fps <= 0.0 or streaming_fps > NETWORK_STREAMING_MAX_FPS_P192 + 0.01:
        errors.append(f"STREAMING_FPS_OUT_OF_RANGE: {streaming_fps}")
    if streaming_bitrate_mbps <= 0.0 or streaming_bitrate_mbps > NETWORK_STREAMING_MAX_BITRATE_MBPS_P192:
        errors.append(
            f"STREAMING_BITRATE_EXCEEDS_38MBPS: {streaming_bitrate_mbps}"
        )

    native_uvc = body in NATIVE_UVC_CAPABLE_BODIES_P192
    model_id = model_id_map.get(body, 0)
    model_id_hex = f"0x{model_id:08x}"
    res_str = f"{streaming_width}x{streaming_height}"

    if errors:
        return NoUvcGadgetAndStreamingEvalResult(
            valid=False,
            body_model=body,
            model_id_hex=model_id_hex,
            requested_usb_mode=usb_mode,
            native_uvc_supported=native_uvc,
            uvc_masked_by_stage_b=False,
            uvc_gadget_rejected=True,
            usb_phy_lockup_prevented=True,
            legacy_imaging_edge_cap="NONE",
            streaming_protocol=proto,
            streaming_resolution=res_str,
            streaming_fps=streaming_fps,
            streaming_bitrate_mbps=streaming_bitrate_mbps,
            streaming_codec=codec,
            usb_lan_auto_connect_702=usb_lan_auto_connect,
            usb_lan_driver=drv,
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            status=errors[0],
            errors=tuple(errors),
        )

    if usb_mode == "USB_STREAMING" and not native_uvc:
        if stage_b_mask_uvc:
            return NoUvcGadgetAndStreamingEvalResult(
                valid=True,
                body_model=body,
                model_id_hex=model_id_hex,
                requested_usb_mode=usb_mode,
                native_uvc_supported=False,
                uvc_masked_by_stage_b=True,
                uvc_gadget_rejected=False,
                usb_phy_lockup_prevented=True,
                legacy_imaging_edge_cap="REMOTE_SHOOTING_1024x576_NO_AUDIO",
                streaming_protocol=proto,
                streaming_resolution=res_str,
                streaming_fps=streaming_fps,
                streaming_bitrate_mbps=streaming_bitrate_mbps,
                streaming_codec=codec,
                usb_lan_auto_connect_702=usb_lan_auto_connect,
                usb_lan_driver=drv,
                bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
                status="STAGE_B_UVC_CALL_MASKED_ON_FX3_OK",
                errors=(),
            )
        return NoUvcGadgetAndStreamingEvalResult(
            valid=False,
            body_model=body,
            model_id_hex=model_id_hex,
            requested_usb_mode=usb_mode,
            native_uvc_supported=False,
            uvc_masked_by_stage_b=False,
            uvc_gadget_rejected=True,
            usb_phy_lockup_prevented=True,
            legacy_imaging_edge_cap="REMOTE_SHOOTING_1024x576_NO_AUDIO",
            streaming_protocol=proto,
            streaming_resolution=res_str,
            streaming_fps=streaming_fps,
            streaming_bitrate_mbps=streaming_bitrate_mbps,
            streaming_codec=codec,
            usb_lan_auto_connect_702=usb_lan_auto_connect,
            usb_lan_driver=drv,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status="BLOCKED_NATIVE_UVC_ABSENT_ON_FX3",
            errors=("NATIVE_UVC_GADGET_ABSENT_ON_FX3_FX3A",),
        )

    legacy_cap = (
        "1024x576_NO_AUDIO"
        if usb_mode == "REMOTE_SHOOTING"
        else "NOT_APPLICABLE"
    )
    return NoUvcGadgetAndStreamingEvalResult(
        valid=True,
        body_model=body,
        model_id_hex=model_id_hex,
        requested_usb_mode=usb_mode,
        native_uvc_supported=native_uvc,
        uvc_masked_by_stage_b=False,
        uvc_gadget_rejected=False,
        usb_phy_lockup_prevented=True,
        legacy_imaging_edge_cap=legacy_cap,
        streaming_protocol=proto,
        streaming_resolution=res_str,
        streaming_fps=streaming_fps,
        streaming_bitrate_mbps=streaming_bitrate_mbps,
        streaming_codec=codec,
        usb_lan_auto_connect_702=usb_lan_auto_connect,
        usb_lan_driver=drv,
        bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        status=f"{body}_{usb_mode}_{proto}_{res_str}_{streaming_bitrate_mbps:.0f}MBPS_OK",
        errors=(),
    )


def evaluate_power_delivery_matrix(
    *,
    power_source: str = "BODY_USBC_PD",
    np_fz100_inserted: bool = True,
    pd_adapter_watts: float = 27.0,
    cable_current_rating_a: float = 3.0,
    cable_has_emarker: bool = False,
    camera_powered_on: bool = True,
) -> PowerDeliveryMatrixEvalResult:
    """Model FX3 USB-PD (NP-FZ100 mandatory) vs DC-C1 (>=65W + 5A e-Marker) & Micro-USB reject."""
    src = power_source.strip().upper()
    if src not in VALID_POWER_SOURCES_P192:
        return PowerDeliveryMatrixEvalResult(
            valid=False,
            power_source=src,
            np_fz100_inserted=np_fz100_inserted,
            pd_adapter_watts=pd_adapter_watts,
            cable_current_rating_a=cable_current_rating_a,
            cable_has_emarker=cable_has_emarker,
            camera_powered_on=camera_powered_on,
            power_accepted=False,
            internal_charging_active=False,
            charging_paused_during_operation=False,
            micro_usb_power_rejected=False,
            type_c_freed_for_usblan=False,
            dcc1_led_blinking_warning=False,
            lcd_max_brightness_locked=False,
            brownout_shutdown_risk=True,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status=f"UNKNOWN_POWER_SOURCE: {power_source}",
            errors=(f"UNKNOWN_POWER_SOURCE: {power_source}",),
        )

    if src == "MICRO_USB":
        return PowerDeliveryMatrixEvalResult(
            valid=False,
            power_source=src,
            np_fz100_inserted=np_fz100_inserted,
            pd_adapter_watts=pd_adapter_watts,
            cable_current_rating_a=cable_current_rating_a,
            cable_has_emarker=cable_has_emarker,
            camera_powered_on=camera_powered_on,
            power_accepted=False,
            internal_charging_active=False,
            charging_paused_during_operation=False,
            micro_usb_power_rejected=True,
            type_c_freed_for_usblan=False,
            dcc1_led_blinking_warning=False,
            lcd_max_brightness_locked=False,
            brownout_shutdown_risk=True,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status="BLOCKED_MICRO_USB_POWER_NOT_SUPPORTED",
            errors=("MICRO_USB_POWER_DELIVERY_NOT_SUPPORTED",),
        )

    if src == "INTERNAL_BATTERY_ONLY":
        if not np_fz100_inserted:
            return PowerDeliveryMatrixEvalResult(
                valid=False,
                power_source=src,
                np_fz100_inserted=False,
                pd_adapter_watts=0.0,
                cable_current_rating_a=0.0,
                cable_has_emarker=False,
                camera_powered_on=camera_powered_on,
                power_accepted=False,
                internal_charging_active=False,
                charging_paused_during_operation=False,
                micro_usb_power_rejected=False,
                type_c_freed_for_usblan=True,
                dcc1_led_blinking_warning=False,
                lcd_max_brightness_locked=False,
                brownout_shutdown_risk=True,
                bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
                status="BLOCKED_NO_NP_FZ100_BATTERY",
                errors=("NP_FZ100_REQUIRED",),
            )
        return PowerDeliveryMatrixEvalResult(
            valid=True,
            power_source=src,
            np_fz100_inserted=True,
            pd_adapter_watts=0.0,
            cable_current_rating_a=0.0,
            cable_has_emarker=False,
            camera_powered_on=camera_powered_on,
            power_accepted=True,
            internal_charging_active=False,
            charging_paused_during_operation=False,
            micro_usb_power_rejected=False,
            type_c_freed_for_usblan=True,
            dcc1_led_blinking_warning=False,
            lcd_max_brightness_locked=False,
            brownout_shutdown_risk=False,
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            status="INTERNAL_NP_FZ100_ONLY_OK",
            errors=(),
        )

    if src == "BODY_USBC_PD":
        errs: List[str] = []
        if not np_fz100_inserted:
            errs.append("NP_FZ100_MANDATORY_FOR_BODY_USBC_PD")
        if pd_adapter_watts < USB_PD_BODY_MIN_WATTS_P192:
            errs.append(f"INSUFFICIENT_USB_PD_WATTS: {pd_adapter_watts} < {USB_PD_BODY_MIN_WATTS_P192}")
        if errs:
            return PowerDeliveryMatrixEvalResult(
                valid=False,
                power_source=src,
                np_fz100_inserted=np_fz100_inserted,
                pd_adapter_watts=pd_adapter_watts,
                cable_current_rating_a=cable_current_rating_a,
                cable_has_emarker=cable_has_emarker,
                camera_powered_on=camera_powered_on,
                power_accepted=False,
                internal_charging_active=False,
                charging_paused_during_operation=False,
                micro_usb_power_rejected=False,
                type_c_freed_for_usblan=False,
                dcc1_led_blinking_warning=False,
                lcd_max_brightness_locked=False,
                brownout_shutdown_risk=True,
                bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
                status="BLOCKED_NP_FZ100_REQUIRED_FOR_BODY_USBC_PD"
                if not np_fz100_inserted
                else "BLOCKED_INSUFFICIENT_USB_PD_WATTS",
                errors=tuple(errs),
            )
        charging_active = not camera_powered_on
        charging_paused = camera_powered_on
        return PowerDeliveryMatrixEvalResult(
            valid=True,
            power_source=src,
            np_fz100_inserted=True,
            pd_adapter_watts=pd_adapter_watts,
            cable_current_rating_a=cable_current_rating_a,
            cable_has_emarker=cable_has_emarker,
            camera_powered_on=camera_powered_on,
            power_accepted=True,
            internal_charging_active=charging_active,
            charging_paused_during_operation=charging_paused,
            micro_usb_power_rejected=False,
            type_c_freed_for_usblan=False,
            dcc1_led_blinking_warning=False,
            lcd_max_brightness_locked=False,
            brownout_shutdown_risk=False,
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            status=(
                "BODY_USBC_PD_OPERATING_CHARGE_PAUSED_OK"
                if camera_powered_on
                else "BODY_USBC_PD_POWERED_OFF_CHARGING_OK"
            ),
            errors=(),
        )

    # DC_C1_COUPLER
    dcc1_errs: List[str] = []
    if pd_adapter_watts < DCC1_MIN_PD_WATTS_P192:
        dcc1_errs.append(f"DCC1_PD_UNDER_65W: {pd_adapter_watts} < {DCC1_MIN_PD_WATTS_P192}")
    if not cable_has_emarker:
        dcc1_errs.append("DCC1_5A_EMARKER_CHIP_MISSING")
    if cable_current_rating_a < DCC1_REQUIRED_CABLE_CURRENT_A_P192:
        dcc1_errs.append(
            f"DCC1_CABLE_CURRENT_UNDER_5A: {cable_current_rating_a} < {DCC1_REQUIRED_CABLE_CURRENT_A_P192}"
        )
    if dcc1_errs:
        return PowerDeliveryMatrixEvalResult(
            valid=False,
            power_source=src,
            np_fz100_inserted=False,
            pd_adapter_watts=pd_adapter_watts,
            cable_current_rating_a=cable_current_rating_a,
            cable_has_emarker=cable_has_emarker,
            camera_powered_on=camera_powered_on,
            power_accepted=False,
            internal_charging_active=False,
            charging_paused_during_operation=False,
            micro_usb_power_rejected=False,
            type_c_freed_for_usblan=True,
            dcc1_led_blinking_warning=True,
            lcd_max_brightness_locked=False,
            brownout_shutdown_risk=True,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status="BLOCKED_DCC1_INSUFFICIENT_PD_OR_5A_EMARKER",
            errors=tuple(dcc1_errs),
        )

    return PowerDeliveryMatrixEvalResult(
        valid=True,
        power_source=src,
        np_fz100_inserted=False,
        pd_adapter_watts=pd_adapter_watts,
        cable_current_rating_a=cable_current_rating_a,
        cable_has_emarker=True,
        camera_powered_on=camera_powered_on,
        power_accepted=True,
        internal_charging_active=False,
        charging_paused_during_operation=False,
        micro_usb_power_rejected=False,
        type_c_freed_for_usblan=True,
        dcc1_led_blinking_warning=False,
        lcd_max_brightness_locked=True,
        brownout_shutdown_risk=False,
        bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
        status="DCC1_65W_5A_EMARKER_TYPE_C_FREED_LCD_BRIGHTNESS_LOCK_OK",
        errors=(),
    )


def evaluate_user_lut_path_and_cine_ei(
    *,
    media_type: str = "SD",
    submitted_dir: str = SD_USER_LUT_DIR_P192,
    cube_filename: str = "FX3_SLog3_to_709.cube",
    lut_3d_size: int = 33,
    user_lut_slot: int = 1,
    ae_level_offset_thirds: int = 0,
    cine_ei_base_iso: int = 12800,
    cine_ei_index: int = 12800,
    stage_b_target_path: str = "/tmp/stage_b/user_lut_slot1.json",
    cube_text: Optional[str] = None,
) -> UserLutPathAndCineEiEvalResult:
    """Audit SD vs CFexpress-A LUT path asymmetry, .cube invariants, AE offset & Cine EI."""
    errors: List[str] = []
    media = media_type.strip().upper()
    norm_dir = _normalize_lut_dir(submitted_dir)
    expected_dir = (
        SD_USER_LUT_DIR_P192 if media == "SD" else CFEXPRESS_A_USER_LUT_DIR_P192
    )

    if media not in VALID_LUT_MEDIA_TYPES_P192:
        errors.append(f"UNKNOWN_LUT_MEDIA_TYPE: {media_type}")
    path_ok = (media in VALID_LUT_MEDIA_TYPES_P192) and (norm_dir == expected_dir)
    if media in VALID_LUT_MEDIA_TYPES_P192 and not path_ok:
        errors.append(f"LUT_MEDIA_PATH_ASYMMETRY: {media} requires {expected_dir}, got {norm_dir}")

    fname_bytes = len(cube_filename.encode("utf-8"))
    if fname_bytes == 0 or fname_bytes > MAX_CUBE_FILENAME_ASCII_BYTES_P192:
        errors.append(f"CUBE_FILENAME_EXCEEDS_63_BYTES: {fname_bytes}")
    if not _CUBE_FILENAME_ASCII_RE.match(cube_filename):
        errors.append(f"INVALID_ASCII_CUBE_FILENAME: {cube_filename}")

    if lut_3d_size not in SUPPORTED_CUBE_3D_SIZES_P192:
        errors.append(f"UNSUPPORTED_CUBE_3D_SIZE: {lut_3d_size}")

    voxel_count = lut_3d_size ** 3 if lut_3d_size in SUPPORTED_CUBE_3D_SIZES_P192 else 0
    if cube_text is not None:
        ok_cube, parsed_sz, parsed_vox, cube_errs = validate_cube_text_bounded(cube_text)
        if not ok_cube:
            errors.extend(cube_errs)
        elif parsed_sz != lut_3d_size:
            errors.append(f"CUBE_TEXT_SIZE_MISMATCH: {parsed_sz} != {lut_3d_size}")
        voxel_count = parsed_vox

    if not (1 <= user_lut_slot <= MAX_USER_LUT_SLOTS_P192):
        errors.append(f"USER_LUT_SLOT_OUT_OF_RANGE: {user_lut_slot}")
    if ae_level_offset_thirds not in VALID_AE_LEVEL_OFFSET_THIRDS_P192:
        errors.append(f"AE_LEVEL_OFFSET_OUT_OF_RANGE: {ae_level_offset_thirds}/3 EV")

    if cine_ei_base_iso not in CINE_EI_BASE_ISOS_P192:
        errors.append(f"INVALID_CINE_EI_BASE_ISO: {cine_ei_base_iso}")
    else:
        lo, hi = (
            CINE_EI_LOW_BASE_RANGE_P192
            if cine_ei_base_iso == 800
            else CINE_EI_HIGH_BASE_RANGE_P192
        )
        if not (lo <= cine_ei_index <= hi):
            errors.append(
                f"CINE_EI_INDEX_OUT_OF_RANGE_FOR_BASE_{cine_ei_base_iso}: {cine_ei_index} not in [{lo}, {hi}]"
            )

    wg = evaluate_phase192_write_guard(stage_b_target_path)
    if not wg.valid:
        errors.append(f"STAGE_B_PERSISTENT_LUT_WRITE_BLOCKED: {stage_b_target_path}")

    ae_ev = round(ae_level_offset_thirds / 3.0, 4)
    slot_label = f"User{user_lut_slot}"
    bclass = (
        BRIDGE_CLASS_HARD_WRITE_PROTECTED
        if not wg.valid
        else (BRIDGE_CLASS_NATIVE_PASSTHROUGH if len(errors) == 0 else BRIDGE_CLASS_SHIM_TRANSLATED)
    )
    return UserLutPathAndCineEiEvalResult(
        valid=len(errors) == 0,
        media_type=media,
        submitted_dir=norm_dir,
        expected_dir=expected_dir,
        path_asymmetry_ok=path_ok,
        cube_filename=cube_filename,
        filename_ascii_bytes=fname_bytes,
        lut_3d_size=lut_3d_size,
        cube_voxel_count=voxel_count,
        user_lut_slot=slot_label,
        ae_level_offset_ev=ae_ev,
        cine_ei_base_iso=cine_ei_base_iso,
        cine_ei_index=cine_ei_index,
        cmos_analog_gain_polluted=False,
        stage_b_target_path=wg.target_path,
        volatile_staged=wg.volatile_or_ext_allowed,
        persistent_writes=0,
        bridge_class=bclass,
        status=f"{media}_{slot_label}_LUT{lut_3d_size}_BASE{cine_ei_base_iso}_EI{cine_ei_index}_OK"
        if len(errors) == 0
        else errors[0],
        errors=tuple(errors),
    )


def evaluate_rmt_p1bt_and_clip_flag_matrix(
    *,
    body_model: str = "ILME-FX3",
    bluetooth_rmt_ctrl_on: bool = True,
    ir_remote_requested: bool = True,
    gps_link_requested: bool = True,
    creators_app_version: str = "3.1.0",
    monitor_control_version: str = "2.4.0",
    clip_flag_filter: str = "OK",
) -> RmtP1btAndCloudClipFlagEvalResult:
    """Audit RMT-P1BT Bluetooth mutual exclusion (IR + GPS disabled) & Creators' Cloud clip flags."""
    errors: List[str] = []
    body = body_model.strip().upper()
    flag = clip_flag_filter.strip().upper()

    if body not in ("ILME-FX3", "ILME-FX3A"):
        errors.append(f"UNSUPPORTED_BODY_FOR_RMT_P1BT_AUDIT: {body_model}")
    if flag not in VALID_CLIP_FLAG_FILTERS_P192:
        errors.append(f"UNKNOWN_CLIP_FLAG_FILTER: {clip_flag_filter}")

    ca_ver = _parse_semver(creators_app_version)
    mc_ver = _parse_semver(monitor_control_version)
    cloud_ok = (ca_ver >= CREATORS_APP_MIN_VERSION_P192) and (
        mc_ver >= MONITOR_CONTROL_MIN_VERSION_P192
    )
    if not cloud_ok:
        errors.append(
            f"CLOUD_APP_VERSION_BELOW_702_FLOOR: CA={creators_app_version}, MC={monitor_control_version}"
        )

    hw_ir = body == "ILME-FX3"
    hw_nfc = body == "ILME-FX3"

    # Physical FX3 invariant: Bluetooth Rmt Ctrl = On disables both IR remote and GPS link
    effective_ir = (not bluetooth_rmt_ctrl_on) and ir_remote_requested and hw_ir
    effective_gps = (not bluetooth_rmt_ctrl_on) and gps_link_requested
    mutex_enforced = (not bluetooth_rmt_ctrl_on) or (not effective_ir and not effective_gps)

    return RmtP1btAndCloudClipFlagEvalResult(
        valid=len(errors) == 0 and mutex_enforced,
        body_model=body,
        bluetooth_rmt_ctrl_on=bluetooth_rmt_ctrl_on,
        ir_remote_requested=ir_remote_requested,
        gps_link_requested=gps_link_requested,
        effective_ir_remote_active=effective_ir,
        effective_gps_link_active=effective_gps,
        hardware_ir_present=hw_ir,
        hardware_nfc_present=hw_nfc,
        bt_ir_gps_mutual_exclusion_enforced=mutex_enforced,
        creators_app_version=creators_app_version,
        monitor_control_version=monitor_control_version,
        clip_flag_filter=flag,
        cloud_version_gate_ok=cloud_ok,
        bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED if bluetooth_rmt_ctrl_on else BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        status=f"{body}_BT_RMT_{'ON_IR_GPS_MUTEX' if bluetooth_rmt_ctrl_on else 'OFF'}_FLAG_{flag}_OK"
        if len(errors) == 0
        else errors[0],
        errors=tuple(errors),
    )


def evaluate_phase192_write_guard(target_path: str) -> Phase192WriteGuardResult:
    """Hard write-firewall blocking p2:/setting, Backup.bin, BODYDATA.DAT, eMMC & SPI-NOR."""
    norm = target_path.strip()
    if FORBIDDEN_PERSISTENT_TARGET_RE_P192.search(norm):
        return Phase192WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            status="BLOCKED_PERSISTENT_EMMC_OR_P2_SETTING_TARGET",
            errors=(f"FORBIDDEN_PERSISTENT_TARGET: {norm}",),
        )
    allowed = any(norm.startswith(p) for p in VOLATILE_OR_EXT_PREFIXES_P192)
    if not allowed:
        return Phase192WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            status="UNLISTED_NON_VOLATILE_TARGET_BLOCKED",
            errors=(f"TARGET_NOT_VOLATILE_OR_EXT: {norm}",),
        )
    return Phase192WriteGuardResult(
        valid=True,
        target_path=norm,
        volatile_or_ext_allowed=True,
        persistent_write_blocked=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        persistent_writes=0,
        status="VOLATILE_TMPFS_OR_EXT_MEDIA_ALLOWED",
        errors=(),
    )


def build_phase192_compat_matrix() -> Phase192CompatMatrixSummary:
    """Construct 12-touchpoint 4-class compatibility matrix across Pillars 1..4."""
    entries: Tuple[Phase192TouchpointEntry, ...] = (
        Phase192TouchpointEntry(
            touchpoint_id="P192-01",
            pillar="NOUVC_GADGET_AND_STREAMING",
            fx6_or_host_component="FX6 ProCam [USB Streaming] UVC/UAC composite descriptor",
            fx3_target="Stage-B masks UVC descriptor calls on ILME-FX3 / ILME-FX3A",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="uvc_masked_by_stage_b == True; usb_phy_lockup_prevented == True",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-02",
            pillar="NOUVC_GADGET_AND_STREAMING",
            fx6_or_host_component="Stock FX3 4.9.337-scel+ MSC / MTP / Remote Shooting",
            fx3_target="CUsbGadgetStorage / CUsbGadgetStill + 1024x576 no-audio legacy cap",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="MSC/MTP intact; unmasked FX3 UVC rejected",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-03",
            pillar="NOUVC_GADGET_AND_STREAMING",
            fx6_or_host_component="FX3 7.02 4K 59.94p 38Mbps RTMP/RTMPS/SRT & USB-LAN auto-connect",
            fx3_target="libInfraVeric/Rtmp/SrtLiveStreaming.so + cdc_ncm.ko power-on launch",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="bitrate <= 38.0 Mbps; USB_LAN_CONNECT_LAUNCH_ON preserved",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-04",
            pillar="POWER_DELIVERY_PD_VS_DCC1",
            fx6_or_host_component="Body Type-C USB-PD + NP-FZ100 battery presence",
            fx3_target="NP-FZ100 mandatory; charging paused when powered on, resumes off",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="np_fz100_inserted == False -> brownout reject",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-05",
            pillar="POWER_DELIVERY_PD_VS_DCC1",
            fx6_or_host_component="Sony DC-C1 DC Coupler (>=65W USB-PD + 5A e-Marker cable)",
            fx3_target="Frees Type-C for USB-LAN/Creators' App; LCD max-brightness lock aware",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="<65W or non-5A/no-eMarker rejected with blinking warning",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-06",
            pillar="POWER_DELIVERY_PD_VS_DCC1",
            fx6_or_host_component="Micro-USB port power delivery request",
            fx3_target="Hard electrical rejection (VBUS power unsupported on Micro-USB)",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="micro_usb_power_rejected == True",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-07",
            pillar="LUT_PATH_CINE_EI_RMT_P1BT",
            fx6_or_host_component="SDXC card .cube User LUT import path",
            fx3_target="SD strict path /Private/Sony/PRO/LUT/ (17/33pt, <=63 ASCII B)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="missing /Private prefix on SD rejected fail-closed",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-08",
            pillar="LUT_PATH_CINE_EI_RMT_P1BT",
            fx6_or_host_component="CFexpress Type A card .cube User LUT import path",
            fx3_target="CFexpress-A strict path /Sony/PRO/LUT/ (no /Private prefix!)",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="/Private/Sony/PRO/LUT/ on CFexpress-A rejected fail-closed",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-09",
            pillar="LUT_PATH_CINE_EI_RMT_P1BT",
            fx6_or_host_component="Cine EI Dual Base ISO (800 / 12800) & AE Offset 0..+2 EV",
            fx3_target="3200..51200 EI @ Base 12800 metadata/LUT-only (zero CMOS gain shift)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="cmos_analog_gain_polluted == False",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-10",
            pillar="LUT_PATH_CINE_EI_RMT_P1BT",
            fx6_or_host_component="RMT-P1BT Bluetooth 4.2 Remote + Creators' Cloud OK/NG/KEEP",
            fx3_target="Bluetooth Rmt Ctrl = On disables IR remote & GPS link; CA>=3.1/MC>=2.4",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="effective_ir == False and effective_gps == False when BT On",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-11",
            pillar="ZERO_WRITE_FIREWALL",
            fx6_or_host_component="Stage-B User1..User16 LUT & power/streaming overlays",
            fx3_target="Volatile /tmp/ / ram:// / external ExFAT staging only",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="volatile_staged == True; persistent_writes == 0",
        ),
        Phase192TouchpointEntry(
            touchpoint_id="P192-12",
            pillar="ZERO_WRITE_FIREWALL",
            fx6_or_host_component="Stock p2:/setting, Backup.bin, /dev/nflasha*, spi_nor:",
            fx3_target="Strict O_RDONLY write-firewall blocking all persistent flash targets",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="persistent_emmc_writes_authorized == False; spi_nor == False",
        ),
    )
    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    pillar_counts: Dict[str, int] = {}
    for e in entries:
        class_counts[e.bridge_class] = class_counts.get(e.bridge_class, 0) + 1
        pillar_counts[e.pillar] = pillar_counts.get(e.pillar, 0) + 1
    return Phase192CompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        pillar_counts=pillar_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Kernel Module / Init Script Helpers & Clean-Room Fixtures
# ---------------------------------------------------------------------------


def _scan_kmod_rdonly(path: Path, *, module_name: str, driver_tag: str) -> KernelModuleInfoSummary:
    """Inspect kernel module `.modinfo` and module descriptor strictly `os.O_RDONLY` via bounded `os.pread`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        ehdr = os.pread(fd, 64, 0)
        if len(ehdr) < 64 or ehdr[:4] != b"\x7fELF":
            return KernelModuleInfoSummary(
                module_name=module_name,
                body_label="FX3",
                source_mode="LOCAL_DONOR_RDONLY",
                file_bytes=sz,
                vermagic_match=False,
                driver_tag=driver_tag,
                modinfo_valid=False,
            )
        (e_shoff,) = struct.unpack_from("<Q", ehdr, 40)
        e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", ehdr, 58)
        sh_tbl = os.pread(fd, e_shnum * e_shentsize, e_shoff)
        shstr = b""
        if e_shstrndx < e_shnum:
            s_off, s_sz = struct.unpack_from("<QQ", sh_tbl, e_shstrndx * e_shentsize + 24)
            if s_off + s_sz <= sz:
                shstr = os.pread(fd, s_sz, s_off)

        ver_bytes = SCEL_KERNEL_VERMAGIC_P192.encode("ascii")
        tag_bytes = driver_tag.encode("ascii")
        vermagic_ok = False
        tag_ok = False
        kmod_sections = {
            ".modinfo",
            ".gnu.linkonce.this_module",
            ".rodata",
            ".rodata.str",
            ".rodata.str1.1",
            ".rodata.str1.8",
            ".strtab",
            ".dynstr",
            "__ksymtab_strings",
        }
        for idx in range(e_shnum):
            base = idx * e_shentsize
            sh_name_off = struct.unpack_from("<I", sh_tbl, base)[0]
            sh_off, sh_sz = struct.unpack_from("<QQ", sh_tbl, base + 24)
            end = shstr.find(b"\x00", sh_name_off)
            sec_name = (
                shstr[sh_name_off:end].decode("ascii", errors="replace")
                if end != -1 and sh_name_off < len(shstr)
                else ""
            )
            if sec_name in kmod_sections and sh_sz > 0 and sh_off + sh_sz <= sz:
                chunk = os.pread(fd, sh_sz, sh_off)
                if sec_name == ".modinfo" and ver_bytes in chunk:
                    vermagic_ok = True
                if tag_bytes in chunk:
                    tag_ok = True
        return KernelModuleInfoSummary(
            module_name=module_name,
            body_label="FX3",
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            vermagic_match=vermagic_ok,
            driver_tag=driver_tag,
            modinfo_valid=vermagic_ok and tag_ok,
        )
    finally:
        os.close(fd)


def _scan_kmod_buf(buf: bytes, *, module_name: str, driver_tag: str) -> KernelModuleInfoSummary:
    elf_sum = _scan_elf_buf_ordered(
        buf,
        binary_name=module_name,
        body_label="FX3",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        tokens=(SCEL_KERNEL_VERMAGIC_P192, driver_tag),
    )
    vermagic_ok = elf_sum.marker_hits.get(SCEL_KERNEL_VERMAGIC_P192, 0) > 0
    tag_ok = elf_sum.marker_hits.get(driver_tag, 0) > 0
    return KernelModuleInfoSummary(
        module_name=module_name,
        body_label="FX3",
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=len(buf),
        vermagic_match=vermagic_ok,
        driver_tag=driver_tag,
        modinfo_valid=vermagic_ok and tag_ok,
    )


def _read_text_bounded_rdonly(path: Path, max_bytes: int = 16384) -> str:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        buf = os.pread(fd, min(sz, max_bytes), 0)
        return buf.decode("utf-8", errors="replace")
    finally:
        os.close(fd)


def build_clean_room_realhw_nouvc_dcc1_lut_cineei_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room Elf64, CP, kmod, and init-script fixtures."""
    fx3_appfw_tokens = (
        APPFW_FX3_NOUVC_STREAMING_MARKERS_P192
        + APPFW_FX3_USB_POWER_MARKERS_P192
        + APPFW_FX3_LUT_CINEEI_BT_MARKERS_P192
    )
    return {
        "fx3_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af3_imp_{i}" for i in range(48)),
            dt_needed=("libmpr.so", "libInfraUsbCmn.so", "libUsbBusPower.so"),
            rodata_strings=fx3_appfw_tokens,
        ),
        "fx6_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af6_imp_{i}" for i in range(48)),
            dt_needed=("libmpr.so", "libInfraUsbCmn.so"),
            rodata_strings=APPFW_FX6_PROCAM_UVC_MARKERS_P192,
        ),
        "fx3_usbcmn": _build_synthetic_elf64(
            exports=tuple(f"usbcmn3_exp_{i}" for i in range(40)),
            imports=tuple(f"usbcmn3_imp_{i}" for i in range(16)),
            dt_needed=("libbackup.so",),
            rodata_strings=USB_CMN_GADGET_MARKERS_P192,
        ),
        "fx6_usbcmn": _build_synthetic_elf64(
            exports=tuple(f"usbcmn6_exp_{i}" for i in range(44)),
            imports=tuple(f"usbcmn6_imp_{i}" for i in range(16)),
            dt_needed=("libbackup.so",),
            rodata_strings=USB_CMN_GADGET_MARKERS_P192,
        ),
        "fx3_usbctl": _build_synthetic_elf64(
            exports=tuple(f"usbctl_exp_{i}" for i in range(32)),
            imports=tuple(f"usbctl_imp_{i}" for i in range(16)),
            dt_needed=("libInfraUsbCmn.so",),
            rodata_strings=USB_CTL_MARKERS_P192,
        ),
        "fx3_usbbp": _build_synthetic_elf64(
            exports=tuple(f"usbbp_exp_{i}" for i in range(28)),
            imports=tuple(f"usbbp_imp_{i}" for i in range(14)),
            dt_needed=("libUsbControl.so", "libbackup.so"),
            rodata_strings=USB_BUSPOWER_MARKERS_P192,
        ),
        "fx3_veric": _build_synthetic_elf64(
            exports=tuple(f"veric_exp_{i}" for i in range(32)),
            imports=tuple(f"veric_imp_{i}" for i in range(16)),
            dt_needed=("libInfraVericEsCodecLibrary.so",),
            rodata_strings=VERIC_STREAMING_MARKERS_P192,
        ),
        "fx3_rtmp": _build_synthetic_elf64(
            exports=tuple(f"rtmp_exp_{i}" for i in range(28)),
            imports=tuple(f"rtmp_imp_{i}" for i in range(14)),
            dt_needed=("libgstreamer-1.0.so.0", "libCertificateManager.so"),
            rodata_strings=RTMP_STREAMING_MARKERS_P192,
        ),
        "fx3_srt": _build_synthetic_elf64(
            exports=tuple(f"srt_exp_{i}" for i in range(28)),
            imports=tuple(f"srt_imp_{i}" for i in range(14)),
            dt_needed=("libgstreamer-1.0.so.0",),
            rodata_strings=SRT_STREAMING_MARKERS_P192,
        ),
        "fx3_mpr": _build_synthetic_elf64(
            exports=tuple(f"mpr3_exp_{i}" for i in range(32)),
            imports=tuple(f"mpr3_imp_{i}" for i in range(16)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=MPR_LUT_CINE_MARKERS_P192,
        ),
        "fx3_cpapp": b"\x00".join(t.encode("ascii") for t in CPAPP_BATT_MARKERS_P192),
        "kmod_cdc_ncm": _build_synthetic_elf64(
            exports=("cdc_ncm_bind",),
            imports=("usbnet_probe",),
            dt_needed=(),
            rodata_strings=(SCEL_KERNEL_VERMAGIC_P192, "cdc_ncm"),
        ),
        "kmod_usbg_storage": _build_synthetic_elf64(
            exports=("usbg_storage_init",),
            imports=("usb_gadget_probe",),
            dt_needed=(),
            rodata_strings=(SCEL_KERNEL_VERMAGIC_P192, "usbg_storage"),
        ),
        "kmod_usbg_stillimage": _build_synthetic_elf64(
            exports=("usbg_stillimage_init",),
            imports=("usb_gadget_probe",),
            dt_needed=(),
            rodata_strings=(SCEL_KERNEL_VERMAGIC_P192, "usbg_stillimage"),
        ),
        "kmod_usb_f_uvc": _build_synthetic_elf64(
            exports=("uvc_alloc_inst",),
            imports=("usb_function_register",),
            dt_needed=(),
            rodata_strings=(SCEL_KERNEL_VERMAGIC_P192, "usb_f_uvc"),
        ),
        "kmod_usb_buspwr": _build_synthetic_elf64(
            exports=("UsbBusPowerDriver_PortStatusRcv",),
            imports=("usb_register_notify",),
            dt_needed=(),
            rodata_strings=(SCEL_KERNEL_VERMAGIC_P192, "UsbBusPowerDriver_PortStatusRcv"),
        ),
        "insmod_drv2": (
            b"#!/bin/sh\n"
            b"insmod /usr/kmod/usb_portMonitor.ko\n"
            b"insmod /usr/kmod/usbg_sen.ko\n"
            b"insmod /usr/kmod/usb_extcmd.ko\n"
        ),
        "usb_insmod_sh": (
            b"#!/bin/sh\n"
            b"insmod /kmod/usb_gadgetcore.ko\n"
            b"insmod /kmod/usb_portMonitor.ko\n"
            b"insmod /kmod/usbg_sen.ko\n"
        ),
    }


def _collect_local_donor_scan(
    donor_paths: Dict[str, Path],
    root: Path,
) -> Tuple[Dict[str, object], bool]:
    """Perform bounded O_RDONLY donor scan with in-process caching."""
    cache_key = (
        str(root),
        tuple(f"{k}={donor_paths[k]}" for k in sorted(donor_paths.keys())),
    )
    cached = _DONOR_SCAN_CACHE.get(cache_key)
    if cached is not None:
        return cached, True

    all_fx3_appfw_tokens = tuple(
        sorted(
            set(
                APPFW_FX3_NOUVC_STREAMING_MARKERS_P192
                + APPFW_FX3_USB_POWER_MARKERS_P192
                + APPFW_FX3_LUT_CINEEI_BT_MARKERS_P192
            ),
            key=len,
            reverse=True,
        )
    )

    fx3_appfw_sum = _scan_elf_fast_rdonly(
        donor_paths["fx3_appfw"],
        binary_name="appFw.so",
        body_label="FX3",
        tokens=all_fx3_appfw_tokens,
    )
    fx6_appfw_sum = _scan_elf_fast_rdonly(
        donor_paths["fx6_appfw"],
        binary_name="appFw.so",
        body_label="FX6",
        tokens=APPFW_FX6_PROCAM_UVC_MARKERS_P192,
    )
    fx3_usbcmn_sum = _scan_elf_fast_rdonly(
        donor_paths["fx3_usbcmn"],
        binary_name="libInfraUsbCmn.so",
        body_label="FX3",
        tokens=USB_CMN_GADGET_MARKERS_P192,
    )
    fx6_usbcmn_sum = _scan_elf_fast_rdonly(
        donor_paths["fx6_usbcmn"],
        binary_name="libInfraUsbCmn.so",
        body_label="FX6",
        tokens=USB_CMN_GADGET_MARKERS_P192,
    )
    fx3_usbctl_sum = _scan_elf_fast_rdonly(
        donor_paths["fx3_usbctl"],
        binary_name="libUsbControl.so",
        body_label="FX3",
        tokens=USB_CTL_MARKERS_P192,
    )
    fx3_usbbp_sum = _scan_elf_fast_rdonly(
        donor_paths["fx3_usbbp"],
        binary_name="libUsbBusPower.so",
        body_label="FX3",
        tokens=USB_BUSPOWER_MARKERS_P192,
    )
    fx3_veric_sum = _scan_elf_fast_rdonly(
        donor_paths["fx3_veric"],
        binary_name="libInfraVericLiveStreaming.so",
        body_label="FX3",
        tokens=VERIC_STREAMING_MARKERS_P192,
    )
    fx3_rtmp_sum = _scan_elf_fast_rdonly(
        donor_paths["fx3_rtmp"],
        binary_name="libInfraRtmpLiveStreaming.so",
        body_label="FX3",
        tokens=RTMP_STREAMING_MARKERS_P192,
    )
    fx3_srt_sum = _scan_elf_fast_rdonly(
        donor_paths["fx3_srt"],
        binary_name="libInfraSrtLiveStreaming.so",
        body_label="FX3",
        tokens=SRT_STREAMING_MARKERS_P192,
    )
    fx3_mpr_sum = _scan_elf_fast_rdonly(
        donor_paths["fx3_mpr"],
        binary_name="libmpr.so",
        body_label="FX3",
        tokens=MPR_LUT_CINE_MARKERS_P192,
    )
    fx3_cp_sz, fx3_cp_hits = _scan_flat_fast_rdonly(
        donor_paths["fx3_cpapp"],
        CPAPP_BATT_MARKERS_P192,
    )
    km_cdc_ncm = _scan_kmod_rdonly(
        donor_paths["kmod_cdc_ncm"],
        module_name="cdc_ncm.ko",
        driver_tag="cdc_ncm",
    )
    km_usbg_storage = _scan_kmod_rdonly(
        donor_paths["kmod_usbg_storage"],
        module_name="usbg_storage.ko",
        driver_tag="usbg_storage",
    )
    km_usbg_still = _scan_kmod_rdonly(
        donor_paths["kmod_usbg_stillimage"],
        module_name="usbg_stillimage.ko",
        driver_tag="usbg_stillimage",
    )
    km_uvc = _scan_kmod_rdonly(
        donor_paths["kmod_usb_f_uvc"],
        module_name="usb_f_uvc.ko",
        driver_tag="usb_f_uvc",
    )
    km_buspwr = _scan_kmod_rdonly(
        donor_paths["kmod_usb_buspwr"],
        module_name="usb_buspwr.ko",
        driver_tag="UsbBusPowerDriver_PortStatusRcv",
    )
    insmod_drv2_txt = _read_text_bounded_rdonly(donor_paths["insmod_drv2"])
    usb_insmod_txt = _read_text_bounded_rdonly(donor_paths["usb_insmod_sh"])

    payload: Dict[str, object] = {
        "fx3_appfw_sum": fx3_appfw_sum,
        "fx6_appfw_sum": fx6_appfw_sum,
        "fx3_usbcmn_sum": fx3_usbcmn_sum,
        "fx6_usbcmn_sum": fx6_usbcmn_sum,
        "fx3_usbctl_sum": fx3_usbctl_sum,
        "fx3_usbbp_sum": fx3_usbbp_sum,
        "fx3_veric_sum": fx3_veric_sum,
        "fx3_rtmp_sum": fx3_rtmp_sum,
        "fx3_srt_sum": fx3_srt_sum,
        "fx3_mpr_sum": fx3_mpr_sum,
        "fx3_cp_sz": fx3_cp_sz,
        "fx3_cp_hits": fx3_cp_hits,
        "km_cdc_ncm": km_cdc_ncm,
        "km_usbg_storage": km_usbg_storage,
        "km_usbg_still": km_usbg_still,
        "km_uvc": km_uvc,
        "km_buspwr": km_buspwr,
        "insmod_drv2_txt": insmod_drv2_txt,
        "usb_insmod_txt": usb_insmod_txt,
    }
    _DONOR_SCAN_CACHE[cache_key] = payload
    return payload, False


# ---------------------------------------------------------------------------
# Main Dual-Mode Unified Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_nouvc_dcc1_pd_lut_path_cineei(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwNouvcDcc1PdLutPathCineeiReport:
    """Run Phase 192 (40th Milestone Auditor, 40/40) on O_RDONLY donors or clean-room fixtures."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    force_clean = clean_room or is_forced_clean_room()

    required_rel_map = {
        "fx3_appfw": FX3_APPFW_P192_RELPATH,
        "fx6_appfw": FX6_APPFW_P192_RELPATH,
        "fx3_usbcmn": FX3_LIBINFRA_USB_CMN_P192_RELPATH,
        "fx6_usbcmn": FX6_LIBINFRA_USB_CMN_P192_RELPATH,
        "fx3_usbctl": FX3_LIBUSB_CONTROL_P192_RELPATH,
        "fx3_usbbp": FX3_LIBUSB_BUS_POWER_P192_RELPATH,
        "fx3_veric": FX3_LIBINFRA_VERIC_STREAM_P192_RELPATH,
        "fx3_rtmp": FX3_LIBINFRA_RTMP_STREAM_P192_RELPATH,
        "fx3_srt": FX3_LIBINFRA_SRT_STREAM_P192_RELPATH,
        "fx3_mpr": FX3_LIBMPR_P192_RELPATH,
        "fx3_cpapp": FX3_CPAPP_P192_RELPATH,
        "kmod_cdc_ncm": FX3_CDC_NCM_KO_P192_RELPATH,
        "kmod_usbg_storage": FX3_USBG_STORAGE_KO_P192_RELPATH,
        "kmod_usbg_stillimage": FX3_USBG_STILLIMAGE_KO_P192_RELPATH,
        "kmod_usb_f_uvc": FX3_USB_F_UVC_KO_P192_RELPATH,
        "kmod_usb_buspwr": FX3_USB_BUSPWR_KO_P192_RELPATH,
        "insmod_drv2": FX3_INSMOD_DRV2_P192_RELPATH,
        "usb_insmod_sh": FX3_USB_INSMOD_SH_P192_RELPATH,
    }

    donor_paths: Dict[str, Optional[Path]] = {}
    if not force_clean:
        for key, rel in required_rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=root)

    use_local = (not force_clean) and all(p is not None for p in donor_paths.values())

    all_fx3_appfw_tokens = tuple(
        sorted(
            set(
                APPFW_FX3_NOUVC_STREAMING_MARKERS_P192
                + APPFW_FX3_USB_POWER_MARKERS_P192
                + APPFW_FX3_LUT_CINEEI_BT_MARKERS_P192
            ),
            key=len,
            reverse=True,
        )
    )

    cache_hit = False
    if use_local:
        mode = "LOCAL_DONOR_VERIFIED"
        resolved_only = {k: p for k, p in donor_paths.items() if p is not None}
        scan_data, cache_hit = _collect_local_donor_scan(resolved_only, root)
        fx3_appfw_sum: ElfSectionSummary = scan_data["fx3_appfw_sum"]  # type: ignore[assignment]
        fx6_appfw_sum: ElfSectionSummary = scan_data["fx6_appfw_sum"]  # type: ignore[assignment]
        fx3_usbcmn_sum: ElfSectionSummary = scan_data["fx3_usbcmn_sum"]  # type: ignore[assignment]
        fx6_usbcmn_sum: ElfSectionSummary = scan_data["fx6_usbcmn_sum"]  # type: ignore[assignment]
        fx3_usbctl_sum: ElfSectionSummary = scan_data["fx3_usbctl_sum"]  # type: ignore[assignment]
        fx3_usbbp_sum: ElfSectionSummary = scan_data["fx3_usbbp_sum"]  # type: ignore[assignment]
        fx3_veric_sum: ElfSectionSummary = scan_data["fx3_veric_sum"]  # type: ignore[assignment]
        fx3_rtmp_sum: ElfSectionSummary = scan_data["fx3_rtmp_sum"]  # type: ignore[assignment]
        fx3_srt_sum: ElfSectionSummary = scan_data["fx3_srt_sum"]  # type: ignore[assignment]
        fx3_mpr_sum: ElfSectionSummary = scan_data["fx3_mpr_sum"]  # type: ignore[assignment]
        fx3_cp_sz: int = scan_data["fx3_cp_sz"]  # type: ignore[assignment]
        fx3_cp_hits: Dict[str, int] = scan_data["fx3_cp_hits"]  # type: ignore[assignment]
        km_cdc_ncm: KernelModuleInfoSummary = scan_data["km_cdc_ncm"]  # type: ignore[assignment]
        km_usbg_storage: KernelModuleInfoSummary = scan_data["km_usbg_storage"]  # type: ignore[assignment]
        km_usbg_still: KernelModuleInfoSummary = scan_data["km_usbg_still"]  # type: ignore[assignment]
        km_uvc: KernelModuleInfoSummary = scan_data["km_uvc"]  # type: ignore[assignment]
        km_buspwr: KernelModuleInfoSummary = scan_data["km_buspwr"]  # type: ignore[assignment]
        insmod_drv2_txt: str = scan_data["insmod_drv2_txt"]  # type: ignore[assignment]
        usb_insmod_txt: str = scan_data["usb_insmod_txt"]  # type: ignore[assignment]
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx = build_clean_room_realhw_nouvc_dcc1_lut_cineei_fixtures()
        fx3_appfw_sum = _scan_elf_buf_ordered(
            fx["fx3_appfw"],
            binary_name="appFw.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=all_fx3_appfw_tokens,
        )
        fx6_appfw_sum = _scan_elf_buf_ordered(
            fx["fx6_appfw"],
            binary_name="appFw.so",
            body_label="FX6",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=APPFW_FX6_PROCAM_UVC_MARKERS_P192,
        )
        fx3_usbcmn_sum = _scan_elf_buf_ordered(
            fx["fx3_usbcmn"],
            binary_name="libInfraUsbCmn.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=USB_CMN_GADGET_MARKERS_P192,
        )
        fx6_usbcmn_sum = _scan_elf_buf_ordered(
            fx["fx6_usbcmn"],
            binary_name="libInfraUsbCmn.so",
            body_label="FX6",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=USB_CMN_GADGET_MARKERS_P192,
        )
        fx3_usbctl_sum = _scan_elf_buf_ordered(
            fx["fx3_usbctl"],
            binary_name="libUsbControl.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=USB_CTL_MARKERS_P192,
        )
        fx3_usbbp_sum = _scan_elf_buf_ordered(
            fx["fx3_usbbp"],
            binary_name="libUsbBusPower.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=USB_BUSPOWER_MARKERS_P192,
        )
        fx3_veric_sum = _scan_elf_buf_ordered(
            fx["fx3_veric"],
            binary_name="libInfraVericLiveStreaming.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=VERIC_STREAMING_MARKERS_P192,
        )
        fx3_rtmp_sum = _scan_elf_buf_ordered(
            fx["fx3_rtmp"],
            binary_name="libInfraRtmpLiveStreaming.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=RTMP_STREAMING_MARKERS_P192,
        )
        fx3_srt_sum = _scan_elf_buf_ordered(
            fx["fx3_srt"],
            binary_name="libInfraSrtLiveStreaming.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=SRT_STREAMING_MARKERS_P192,
        )
        fx3_mpr_sum = _scan_elf_buf_ordered(
            fx["fx3_mpr"],
            binary_name="libmpr.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=MPR_LUT_CINE_MARKERS_P192,
        )
        fx3_cp_sz = len(fx["fx3_cpapp"])
        fx3_cp_hits = _count_tokens_ordered_single_pass(fx["fx3_cpapp"], CPAPP_BATT_MARKERS_P192)
        km_cdc_ncm = _scan_kmod_buf(fx["kmod_cdc_ncm"], module_name="cdc_ncm.ko", driver_tag="cdc_ncm")
        km_usbg_storage = _scan_kmod_buf(
            fx["kmod_usbg_storage"], module_name="usbg_storage.ko", driver_tag="usbg_storage"
        )
        km_usbg_still = _scan_kmod_buf(
            fx["kmod_usbg_stillimage"], module_name="usbg_stillimage.ko", driver_tag="usbg_stillimage"
        )
        km_uvc = _scan_kmod_buf(fx["kmod_usb_f_uvc"], module_name="usb_f_uvc.ko", driver_tag="usb_f_uvc")
        km_buspwr = _scan_kmod_buf(
            fx["kmod_usb_buspwr"],
            module_name="usb_buspwr.ko",
            driver_tag="UsbBusPowerDriver_PortStatusRcv",
        )
        insmod_drv2_txt = fx["insmod_drv2"].decode("utf-8")
        usb_insmod_txt = fx["usb_insmod_sh"].decode("utf-8")

    donor_file_sizes: Dict[str, int] = {
        "fx3_appfw": fx3_appfw_sum.file_bytes,
        "fx6_appfw": fx6_appfw_sum.file_bytes,
        "fx3_usbcmn": fx3_usbcmn_sum.file_bytes,
        "fx6_usbcmn": fx6_usbcmn_sum.file_bytes,
        "fx3_usbctl": fx3_usbctl_sum.file_bytes,
        "fx3_usbbp": fx3_usbbp_sum.file_bytes,
        "fx3_veric": fx3_veric_sum.file_bytes,
        "fx3_rtmp": fx3_rtmp_sum.file_bytes,
        "fx3_srt": fx3_srt_sum.file_bytes,
        "fx3_mpr": fx3_mpr_sum.file_bytes,
        "fx3_cpapp": fx3_cp_sz,
        "kmod_cdc_ncm": km_cdc_ncm.file_bytes,
        "kmod_usbg_storage": km_usbg_storage.file_bytes,
        "kmod_usbg_stillimage": km_usbg_still.file_bytes,
        "kmod_usb_f_uvc": km_uvc.file_bytes,
        "kmod_usb_buspwr": km_buspwr.file_bytes,
    }

    # --- Pillar 1: No-UVC Gadget Stack & Network Streaming / USB-LAN ---
    p1_errors: List[str] = []
    fx3_usb_stream_hits = {
        t: fx3_appfw_sum.marker_hits[t] for t in APPFW_FX3_NOUVC_STREAMING_MARKERS_P192
    }
    fx6_procam_uvc_hits = {
        t: fx6_appfw_sum.marker_hits[t] for t in APPFW_FX6_PROCAM_UVC_MARKERS_P192
    }
    if not all(v > 0 for v in fx3_usb_stream_hits.values()):
        p1_errors.append("MISSING_FX3_APPFW_NOUVC_STREAMING_MARKERS")
    if not all(v > 0 for v in fx6_procam_uvc_hits.values()):
        p1_errors.append("MISSING_FX6_APPFW_PROCAM_UVC_MARKERS")
    for s_name, s_obj in (
        ("fx3_usbcmn", fx3_usbcmn_sum),
        ("fx6_usbcmn", fx6_usbcmn_sum),
        ("fx3_usbctl", fx3_usbctl_sum),
        ("fx3_veric", fx3_veric_sum),
        ("fx3_rtmp", fx3_rtmp_sum),
        ("fx3_srt", fx3_srt_sum),
    ):
        if not all(v > 0 for v in s_obj.marker_hits.values()):
            p1_errors.append(f"MISSING_MARKERS_{s_name.upper()}")
    for km_name, km_obj in (
        ("cdc_ncm", km_cdc_ncm),
        ("usbg_storage", km_usbg_storage),
        ("usbg_stillimage", km_usbg_still),
        ("usb_f_uvc", km_uvc),
    ):
        if not km_obj.modinfo_valid:
            p1_errors.append(f"INVALID_KMOD_MODINFO_{km_name.upper()}")

    boot_insmod_uvc = (
        ("g_webcam" in insmod_drv2_txt)
        or ("usb_f_uvc" in insmod_drv2_txt)
        or ("g_webcam" in usb_insmod_txt)
        or ("usb_f_uvc" in usb_insmod_txt)
    )
    if boot_insmod_uvc:
        p1_errors.append("UNEXPECTED_BOOT_INSMOD_UVC_MODULE")

    ev_uvc_unmasked = evaluate_nouvc_gadget_and_network_streaming(
        body_model="ILME-FX3",
        requested_usb_mode="USB_STREAMING",
        stage_b_mask_uvc=False,
    )
    ev_uvc_masked = evaluate_nouvc_gadget_and_network_streaming(
        body_model="ILME-FX3",
        requested_usb_mode="USB_STREAMING",
        stage_b_mask_uvc=True,
    )
    ev_srt_4k60 = evaluate_nouvc_gadget_and_network_streaming(
        body_model="ILME-FX3",
        requested_usb_mode="USB_LAN",
        streaming_protocol="SRT",
        streaming_width=3840,
        streaming_height=2160,
        streaming_fps=59.94,
        streaming_bitrate_mbps=38.0,
        streaming_codec="HEVC",
        usb_lan_auto_connect=True,
        usb_lan_driver="CDC_NCM",
    )
    ev_remote_legacy = evaluate_nouvc_gadget_and_network_streaming(
        body_model="ILME-FX3",
        requested_usb_mode="REMOTE_SHOOTING",
    )
    ev_fx30_uvc = evaluate_nouvc_gadget_and_network_streaming(
        body_model="ILME-FX30",
        requested_usb_mode="USB_STREAMING",
        stage_b_mask_uvc=False,
    )
    if not (
        (not ev_uvc_unmasked.valid and ev_uvc_unmasked.uvc_gadget_rejected)
        and (ev_uvc_masked.valid and ev_uvc_masked.uvc_masked_by_stage_b)
        and (ev_srt_4k60.valid and ev_srt_4k60.usb_lan_auto_connect_702)
        and (ev_remote_legacy.valid and ev_remote_legacy.legacy_imaging_edge_cap == "1024x576_NO_AUDIO")
        and (ev_fx30_uvc.valid and ev_fx30_uvc.native_uvc_supported)
    ):
        p1_errors.append("PILLAR_1_NOUVC_STREAMING_EVAL_FAILED")

    pillar_1 = Pillar1NoUvcGadgetStreamingReport(
        passed=len(p1_errors) == 0,
        fx3_appfw_usb_stream_hits=fx3_usb_stream_hits,
        fx6_appfw_procam_uvc_hits=fx6_procam_uvc_hits,
        fx3_usbcmn_summary=fx3_usbcmn_sum,
        fx6_usbcmn_summary=fx6_usbcmn_sum,
        fx3_usbctl_summary=fx3_usbctl_sum,
        fx3_veric_summary=fx3_veric_sum,
        fx3_rtmp_summary=fx3_rtmp_sum,
        fx3_srt_summary=fx3_srt_sum,
        kmod_cdc_ncm=km_cdc_ncm,
        kmod_usbg_storage=km_usbg_storage,
        kmod_usbg_stillimage=km_usbg_still,
        kmod_usb_f_uvc=km_uvc,
        uvc_loaded_in_boot_insmod=boot_insmod_uvc,
        eval_fx3_uvc_unmasked_rejected=ev_uvc_unmasked,
        eval_fx3_stage_b_uvc_masked=ev_uvc_masked,
        eval_fx3_4k60_srt_usblan_auto=ev_srt_4k60,
        eval_fx3_remote_shooting_legacy=ev_remote_legacy,
        eval_fx30_native_uvc_allowed=ev_fx30_uvc,
        errors=tuple(p1_errors),
    )

    # --- Pillar 2: Electrical Power-Delivery Matrix (USB-PD vs DC-C1) ---
    p2_errors: List[str] = []
    fx3_power_hits = {t: fx3_appfw_sum.marker_hits[t] for t in APPFW_FX3_USB_POWER_MARKERS_P192}
    if not all(v > 0 for v in fx3_power_hits.values()):
        p2_errors.append("MISSING_FX3_APPFW_POWER_MARKERS")
    if not all(v > 0 for v in fx3_usbbp_sum.marker_hits.values()):
        p2_errors.append("MISSING_FX3_USBBUSPOWER_MARKERS")
    if not all(v > 0 for v in fx3_cp_hits.values()):
        p2_errors.append("MISSING_FX3_CPAPP_BATT_MARKERS")
    if not km_buspwr.modinfo_valid:
        p2_errors.append("INVALID_USB_BUSPWR_KO_MODINFO")

    ev_pd_on = evaluate_power_delivery_matrix(
        power_source="BODY_USBC_PD",
        np_fz100_inserted=True,
        pd_adapter_watts=27.0,
        cable_current_rating_a=3.0,
        camera_powered_on=True,
    )
    ev_pd_off = evaluate_power_delivery_matrix(
        power_source="BODY_USBC_PD",
        np_fz100_inserted=True,
        pd_adapter_watts=27.0,
        cable_current_rating_a=3.0,
        camera_powered_on=False,
    )
    ev_pd_nobatt = evaluate_power_delivery_matrix(
        power_source="BODY_USBC_PD",
        np_fz100_inserted=False,
        pd_adapter_watts=65.0,
        cable_current_rating_a=5.0,
        cable_has_emarker=True,
        camera_powered_on=True,
    )
    ev_micro_usb = evaluate_power_delivery_matrix(
        power_source="MICRO_USB",
        np_fz100_inserted=True,
        pd_adapter_watts=10.0,
    )
    ev_dcc1_ok = evaluate_power_delivery_matrix(
        power_source="DC_C1_COUPLER",
        np_fz100_inserted=False,
        pd_adapter_watts=65.0,
        cable_current_rating_a=5.0,
        cable_has_emarker=True,
        camera_powered_on=True,
    )
    ev_dcc1_bad = evaluate_power_delivery_matrix(
        power_source="DC_C1_COUPLER",
        np_fz100_inserted=False,
        pd_adapter_watts=45.0,
        cable_current_rating_a=3.0,
        cable_has_emarker=False,
        camera_powered_on=True,
    )
    if not (
        (ev_pd_on.valid and ev_pd_on.charging_paused_during_operation and not ev_pd_on.internal_charging_active)
        and (ev_pd_off.valid and ev_pd_off.internal_charging_active)
        and (not ev_pd_nobatt.valid and ev_pd_nobatt.brownout_shutdown_risk)
        and (not ev_micro_usb.valid and ev_micro_usb.micro_usb_power_rejected)
        and (ev_dcc1_ok.valid and ev_dcc1_ok.type_c_freed_for_usblan and ev_dcc1_ok.lcd_max_brightness_locked)
        and (not ev_dcc1_bad.valid and ev_dcc1_bad.dcc1_led_blinking_warning)
    ):
        p2_errors.append("PILLAR_2_POWER_DELIVERY_EVAL_FAILED")

    pillar_2 = Pillar2PowerDeliveryMatrixReport(
        passed=len(p2_errors) == 0,
        fx3_appfw_power_hits=fx3_power_hits,
        fx3_usbbp_summary=fx3_usbbp_sum,
        fx3_cpapp_batt_hits=fx3_cp_hits,
        kmod_usb_buspwr=km_buspwr,
        eval_body_pd_with_battery_on=ev_pd_on,
        eval_body_pd_with_battery_off_charging=ev_pd_off,
        eval_body_pd_without_battery_rejected=ev_pd_nobatt,
        eval_micro_usb_rejected=ev_micro_usb,
        eval_dcc1_65w_5a_emarker_accepted=ev_dcc1_ok,
        eval_dcc1_45w_3a_rejected=ev_dcc1_bad,
        errors=tuple(p2_errors),
    )

    # --- Pillar 3: Dual-Media User LUT Path Asymmetry, Cine EI & RMT-P1BT ---
    p3_errors: List[str] = []
    fx3_lut_cine_bt_hits = {
        t: fx3_appfw_sum.marker_hits[t] for t in APPFW_FX3_LUT_CINEEI_BT_MARKERS_P192
    }
    if not all(v > 0 for v in fx3_lut_cine_bt_hits.values()):
        p3_errors.append("MISSING_FX3_APPFW_LUT_CINEEI_BT_MARKERS")
    if not all(v > 0 for v in fx3_mpr_sum.marker_hits.values()):
        p3_errors.append("MISSING_FX3_MPR_LUT_MARKERS")

    ev_sd_ok = evaluate_user_lut_path_and_cine_ei(
        media_type="SD",
        submitted_dir="/Private/Sony/PRO/LUT/",
        cube_filename="SLog3_S709_33.cube",
        lut_3d_size=33,
        user_lut_slot=1,
        ae_level_offset_thirds=2,
        cine_ei_base_iso=12800,
        cine_ei_index=51200,
    )
    ev_cfe_ok = evaluate_user_lut_path_and_cine_ei(
        media_type="CFEXPRESS_A",
        submitted_dir="/Sony/PRO/LUT/",
        cube_filename="SLog3_Rec709_17.cube",
        lut_3d_size=17,
        user_lut_slot=16,
        ae_level_offset_thirds=6,
        cine_ei_base_iso=12800,
        cine_ei_index=3200,
    )
    ev_cfe_bad = evaluate_user_lut_path_and_cine_ei(
        media_type="CFEXPRESS_A",
        submitted_dir="/Private/Sony/PRO/LUT/",
        cube_filename="SLog3_Rec709_17.cube",
    )
    ev_sd_bad = evaluate_user_lut_path_and_cine_ei(
        media_type="SD",
        submitted_dir="/Sony/PRO/LUT/",
        cube_filename="SLog3_Rec709_17.cube",
    )
    ev_long_name_bad = evaluate_user_lut_path_and_cine_ei(
        media_type="SD",
        submitted_dir="/Private/Sony/PRO/LUT/",
        cube_filename=("A" * 60) + ".cube",  # 65 bytes > 63
    )
    ev_p2_write_bad = evaluate_user_lut_path_and_cine_ei(
        media_type="SD",
        submitted_dir="/Private/Sony/PRO/LUT/",
        cube_filename="ValidLut.cube",
        stage_b_target_path="p2:/setting/UserLut01.bin",
    )
    ev_rmt_fx3 = evaluate_rmt_p1bt_and_clip_flag_matrix(
        body_model="ILME-FX3",
        bluetooth_rmt_ctrl_on=True,
        ir_remote_requested=True,
        gps_link_requested=True,
        creators_app_version="3.1.0",
        monitor_control_version="2.4.0",
        clip_flag_filter="KEEP",
    )
    ev_rmt_fx3a = evaluate_rmt_p1bt_and_clip_flag_matrix(
        body_model="ILME-FX3A",
        bluetooth_rmt_ctrl_on=True,
        ir_remote_requested=True,
        gps_link_requested=True,
        creators_app_version="3.1.0",
        monitor_control_version="2.4.0",
        clip_flag_filter="NG",
    )
    ev_cloud_ok = evaluate_rmt_p1bt_and_clip_flag_matrix(
        body_model="ILME-FX3",
        bluetooth_rmt_ctrl_on=False,
        ir_remote_requested=True,
        gps_link_requested=True,
        creators_app_version="3.1.0",
        monitor_control_version="2.4.0",
        clip_flag_filter="OK",
    )
    if not (
        (ev_sd_ok.valid and ev_sd_ok.path_asymmetry_ok and not ev_sd_ok.cmos_analog_gain_polluted)
        and (ev_cfe_ok.valid and ev_cfe_ok.path_asymmetry_ok)
        and (not ev_cfe_bad.valid and not ev_cfe_bad.path_asymmetry_ok)
        and (not ev_sd_bad.valid and not ev_sd_bad.path_asymmetry_ok)
        and (not ev_long_name_bad.valid)
        and (not ev_p2_write_bad.valid and ev_p2_write_bad.persistent_writes == 0)
        and (
            ev_rmt_fx3.valid
            and ev_rmt_fx3.bt_ir_gps_mutual_exclusion_enforced
            and not ev_rmt_fx3.effective_ir_remote_active
            and not ev_rmt_fx3.effective_gps_link_active
            and ev_rmt_fx3.hardware_ir_present
        )
        and (ev_rmt_fx3a.valid and not ev_rmt_fx3a.hardware_ir_present and not ev_rmt_fx3a.hardware_nfc_present)
        and (ev_cloud_ok.valid and ev_cloud_ok.effective_ir_remote_active and ev_cloud_ok.effective_gps_link_active)
    ):
        p3_errors.append("PILLAR_3_LUT_CINEEI_RMT_EVAL_FAILED")

    pillar_3 = Pillar3LutPathCineEiRmtReport(
        passed=len(p3_errors) == 0,
        fx3_appfw_lut_cine_bt_hits=fx3_lut_cine_bt_hits,
        fx3_mpr_lut_summary=fx3_mpr_sum,
        eval_sd_33pt_cine_ei_12800_ok=ev_sd_ok,
        eval_cfexpress_17pt_ok=ev_cfe_ok,
        eval_cfexpress_wrong_private_prefix_rejected=ev_cfe_bad,
        eval_sd_missing_private_prefix_rejected=ev_sd_bad,
        eval_filename_over_63b_rejected=ev_long_name_bad,
        eval_p2_setting_direct_write_blocked=ev_p2_write_bad,
        eval_rmt_p1bt_fx3_bt_excludes_ir_gps=ev_rmt_fx3,
        eval_rmt_p1bt_fx3a_no_ir_nfc=ev_rmt_fx3a,
        eval_creators_cloud_clip_flag_ok=ev_cloud_ok,
        errors=tuple(p3_errors),
    )

    # --- Pillar 4: Hard Zero-Write Firewall & 12-Touchpoint Compatibility Matrix ---
    p4_errors: List[str] = []
    blk_p2 = evaluate_phase192_write_guard("p2:/setting/UserLut.bin")
    blk_emmc = evaluate_phase192_write_guard("/dev/nflasha15")
    blk_bk = evaluate_phase192_write_guard("p2:/setting/Backup.bin")
    alw_tmp = evaluate_phase192_write_guard("/tmp/stage_b/nouvc_dcc1_overlay.json")
    alw_sd = evaluate_phase192_write_guard("/mnt/sd/Private/Sony/PRO/LUT/MyLut.cube")
    mat = build_phase192_compat_matrix()

    if (
        blk_p2.valid
        or not blk_p2.persistent_write_blocked
        or blk_emmc.valid
        or not blk_emmc.persistent_write_blocked
        or blk_bk.valid
        or not blk_bk.persistent_write_blocked
        or not alw_tmp.valid
        or not alw_sd.valid
        or mat.total_touchpoints != 12
    ):
        p4_errors.append("PILLAR_4_WRITE_FIREWALL_OR_MATRIX_FAILED")

    pillar_4 = Pillar4WriteGuardAndMatrixReport(
        passed=len(p4_errors) == 0,
        blocked_p2_setting_eval=blk_p2,
        blocked_emmc_nflasha_eval=blk_emmc,
        blocked_backup_bin_eval=blk_bk,
        allowed_tmp_overlay_eval=alw_tmp,
        allowed_sd_lut_eval=alw_sd,
        compatibility_matrix=mat,
        errors=tuple(p4_errors),
    )

    all_errors = list(p1_errors + p2_errors + p3_errors + p4_errors)
    all_passed = (
        pillar_1.passed
        and pillar_2.passed
        and pillar_3.passed
        and pillar_4.passed
        and len(all_errors) == 0
    )

    # Build deterministic SHA-256 over canonical report fields (excluding volatile cache_hit)
    digest_payload = {
        "schema_version": PHASE_192_SCHEMA,
        "phase_version": PHASE_192_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "donor_file_sizes": donor_file_sizes,
        "pillar_1_passed": pillar_1.passed,
        "pillar_2_passed": pillar_2.passed,
        "pillar_3_passed": pillar_3.passed,
        "pillar_4_passed": pillar_4.passed,
        "matrix_touchpoints": mat.total_touchpoints,
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return RealhwNouvcDcc1PdLutPathCineeiReport(
        schema_version=PHASE_192_SCHEMA,
        phase_version=PHASE_192_VERSION,
        mode=mode,
        cache_hit=cache_hit,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        raw_firmware_bytes_leaked=0,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        persistent_writes=0,
        nouvc_and_network_streaming_verified=pillar_1.passed,
        power_delivery_pd_vs_dcc1_verified=pillar_2.passed,
        lut_path_cine_ei_and_rmt_p1bt_verified=pillar_3.passed,
        write_firewall_and_matrix_verified=pillar_4.passed,
        donor_file_sizes=donor_file_sizes,
        pillar_1_nouvc_streaming=pillar_1,
        pillar_2_power_delivery=pillar_2,
        pillar_3_lut_cine_ei_rmt=pillar_3,
        pillar_4_write_guard_matrix=pillar_4,
        report_sha256=report_sha256,
        errors=tuple(all_errors),
    )


def realhw_nouvc_dcc1_pd_lut_path_cineei_report_to_dict(
    report: RealhwNouvcDcc1PdLutPathCineeiReport,
) -> Dict[str, object]:
    """Convert report dataclass tree into a deterministic JSON-serializable dict."""
    return asdict(report)
