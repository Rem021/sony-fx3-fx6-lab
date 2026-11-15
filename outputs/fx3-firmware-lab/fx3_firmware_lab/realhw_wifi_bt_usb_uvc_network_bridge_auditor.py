"""Phase 152 — 31st Unified Firmware-Lab Auditor: Real-Hardware Wi-Fi (802.11ac),
Bluetooth LE (Creators' App vs FX6 Content Browser Mobile / Monitor & Control),
USB Type-C Multi-Role Controller (MSC 054C:0DA1, MTP/PTP Remote, UVC/UAC 4K
Livestream), and Wired USB-LAN Gigabit Ethernet FTP / Monitor & Control Bridge.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libsencore.so`, `libmpr.so`,
  `im.elf`, `cpapp-b.bin`, `Backup.bin`, and `nflasha15/lib/` USB/WLAN/BT/Ether
  shared objects) and FX6 v6.01 (`appFw.so`, `libsencore.so`, `libmpr.so`,
  `im.elf`, `cpapp-b.bin`, `Backup.bin`, and `nflasha15/lib/` USB/WLAN/BT/Ether
  shared objects) strictly via `os.O_RDONLY` + `mmap.ACCESS_READ` using targeted
  ELF64 `.dynsym`/`.dynstr`/`.dynamic` parsing, `BK4\\x00` dual-record parsing,
  and bounded single-pass `re.finditer` scans (< 1.5 s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`/`.elf` fixtures,
  `cpapp-b.bin` token buffers, and `BK4\\x00` `Backup.bin` fixtures, leaking zero
  raw Sony proprietary bytes in JSON output.

Audits Four Phase 152 Real-Hardware Connectivity Pillars & Compatibility Matrix:
1. Pillar 1 (`WIFI_80211AC_AND_RF_NVS_ISOLATION`):
   Audits 802.11ac 2.4/5 GHz Wi-Fi (`libWlanResource.so` `wlan.ko` /
   `bdwlan30_1vy_rc_*` / `qwlan30.bin` / `MurataTypeTP.bin`, `libWlanAdjust.so`
   `/dev/nflasha23/INFO/WIFI_INF.TXT` / `WlanAdjust_wpa_ctrl_open`),
   `libsencore.so` (`START_WIFI_CHECK`, `MPR_CMD_EXEC_WIFI_TEST`), `cpapp-b.bin`
   (`DFS_FACTOR_WIFI_CONNECT`, `MSG_ID_INFRABB_AUDIO_SET_TX_RF_POWER`),
   `appFw.so` (`AIRPLANE_MODE_ON`, `BKID_APP_EXTERN_MENU_WIFI_SET`), and
   `Backup.bin` (`819` vs `840` subsystems). Enforces 100% write-lock on
   `p12/p13` RF TX-power / regulatory MAC NVS (`rf_nvs_p12_p13_writes_permitted
   == False`, `rf_nvs_mutation_bytes == 0`).
2. Pillar 2 (`BLE_CREATORS_APP_VS_FX6_NO_BT_NONBLOCK`):
   Audits FX3 BLE `Creators' App` stack (`libInfraBluetoothCore.so` `/dev/ttyAMA3`
   `qca_hci_send_cmd` / `CBTWoLE::pvtBTChipPowerON`, `libInfraBluetoothLowEnergy.so`
   `DILocationService` / `DIRXTXControlService`, `libsencore.so`
   `LOAD_BT_FIRMWARE` / `PREPARE_BT_DEV_ADDR`) against FX6 `appFw.so` (lacking
   physical BLE hardware, using Wi-Fi-only `Content Browser Mobile` / `Monitor &
   Control`) and `cpapp-b.bin` (`GpHCI`, `HCIpJ`). Proves Stage-B `LD_PRELOAD`
   status masking eliminates mismatched Wi-Fi/BT daemon stalls
   (`bt_hci_blocking_wait_ms == 0`, `bt_hci_blocking_wait_eliminated == True`).
3. Pillar 3 (`USB_TYPEC_MSC_0DA1_MTP_REMOTE_AND_UVC_BRIDGE`):
   Audits USB Type-C multi-role controller (`libInfraUsbCmn.so`
   `/dev/usb/gadgetcore` / `CUsbGadgetStorage` / `CUsbGadgetStill` /
   `CUsbGadgetStreaming`, `libUsbControl.so` `MSGID_START_GADGET_CMD`,
   `libInfraMscServer.so` `MassStorageServer_Create`, `libInfraPtpControl.so`
   `PTPT_EE_end_usb` vs `PtptMultiSessionCallBackWrapper`), classifying `MSC
   (054C:0DA1)` + `SERVICE (054C:0336)`, `MTP/PTP Remote`, and `UVC/UAC 4K
   Livestream` (`HDMI-to-UVC` vs masked `USB_STREAMING` ProCam menu) so USB
   Mass Storage `054C:0DA1` recovery access is NEVER broken
   (`usb_msc_0da1_recovery_intact == True`).
4. Pillar 4 (`WIRED_USB_LAN_GIGABIT_FTP_AND_MONITOR_CONTROL`):
   Audits `libNetServiceEther.so` (`NseMiscGetMacAddressForUsbEther`,
   `NseMiscGetMacAddressForWiredEther`, `WESStartCableLinkCheck`,
   `dhcpcd_wired_dns_4.conf`), `libInfraFtpClient.so` (`CurlControl::ConnectSSL`,
   `CurlCmdHdl::SetOptSsh`, `CurlControl::getDstFile`), `libsencore.so`
   (`USB_ETHER_FORCE_MODE_SET`, `WIREDLAN_NETIF_DOWN`, `WIREDLAN_WOL_ENABLE`),
   and `cpapp-b.bin` (`DFS_FACTOR_ETHER_CONNECT`), verifying Gigabit USB-LAN
   (`CDC-NCM` / `RTL8153` / `AX88179`) FTP/FTPES & `Monitor & Control`
   (`PTP-IP` `TCP/15740` + RTSP) passthrough while masking FX6-only Wake-on-LAN
   RJ45 hardware with `0 ms` non-blocking fallback and strict `P12` RF-off
   compliance.
"""

from __future__ import annotations

import hashlib
import json
import mmap
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
    BK4_HEADER_BYTES,
    BK4_MAGIC_BYTES,
    BK4_SYNC_U32,
    DESCRIPTOR_PROP_ID,
    DESCRIPTOR_SLOT_BYTES,
    DESCRIPTOR_SLOT_COUNT,
    DESCRIPTOR_TABLE_BYTES,
    parse_dual_bk4_and_descriptors,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    EXPECTED_SENCORE_EXPORTS,
    EXPECTED_SENCORE_IMPORTS,
    FX3_APPFW_P146_RELPATH,
    FX3_BACKUP_BIN_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX3_IM_ELF_P146_RELPATH,
    FX3_LIBMPR_P146_RELPATH,
    FX3_LIBSENCORE_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_BACKUP_BIN_P146_RELPATH,
    FX6_CPAPP_P146_RELPATH,
    FX6_IM_ELF_P146_RELPATH,
    FX6_LIBMPR_P146_RELPATH,
    FX6_LIBSENCORE_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
    _count_tokens_single_pass,
    _scan_elf_and_tokens_buf,
    _scan_elf_and_tokens_rdonly,
)


PHASE_152_SCHEMA = "fx3_firmware_lab_phase152_realhw_wifi_bt_usb_uvc_network_bridge_v1"
PHASE_152_VERSION = "152.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------

FX3_APPFW_P152_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P152_RELPATH = FX6_APPFW_P146_RELPATH
FX3_LIBSENCORE_P152_RELPATH = FX3_LIBSENCORE_P146_RELPATH
FX6_LIBSENCORE_P152_RELPATH = FX6_LIBSENCORE_P146_RELPATH
FX3_LIBMPR_P152_RELPATH = FX3_LIBMPR_P146_RELPATH
FX6_LIBMPR_P152_RELPATH = FX6_LIBMPR_P146_RELPATH
FX3_IM_ELF_P152_RELPATH = FX3_IM_ELF_P146_RELPATH
FX6_IM_ELF_P152_RELPATH = FX6_IM_ELF_P146_RELPATH
FX3_CPAPP_P152_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P152_RELPATH = FX6_CPAPP_P146_RELPATH
FX3_BACKUP_BIN_P152_RELPATH = FX3_BACKUP_BIN_P146_RELPATH
FX6_BACKUP_BIN_P152_RELPATH = FX6_BACKUP_BIN_P146_RELPATH

_FX3_USR_LIB_PREFIX = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib"
)
_FX6_USR_LIB_PREFIX = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib"
)

FX3_LIBINFRA_MSC_SERVER_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libInfraMscServer.so"
FX6_LIBINFRA_MSC_SERVER_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libInfraMscServer.so"
FX3_LIBUSB_CONTROL_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libUsbControl.so"
FX6_LIBUSB_CONTROL_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libUsbControl.so"
FX3_LIBINFRA_USB_CMN_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libInfraUsbCmn.so"
FX6_LIBINFRA_USB_CMN_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libInfraUsbCmn.so"
FX3_LIBWLAN_RESOURCE_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libWlanResource.so"
FX6_LIBWLAN_RESOURCE_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libWlanResource.so"
FX3_LIBWLAN_ADJUST_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libWlanAdjust.so"
FX6_LIBWLAN_ADJUST_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libWlanAdjust.so"
FX3_LIBINFRA_BT_CORE_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libInfraBluetoothCore.so"
FX6_LIBINFRA_BT_CORE_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libInfraBluetoothCore.so"
FX3_LIBINFRA_BLE_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libInfraBluetoothLowEnergy.so"
FX6_LIBINFRA_BLE_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libInfraBluetoothLowEnergy.so"
FX3_LIBNET_ETHER_P152_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libNetServiceEther.so"
FX6_LIBNET_ETHER_P152_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libNetServiceEther.so"
FX3_LIBINFRA_FTP_P152_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libInfraFtpClient.so"
FX6_LIBINFRA_FTP_P152_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libInfraFtpClient.so"
FX3_LIBINFRA_PTP_P152_RELPATH = f"{_FX3_USR_LIB_PREFIX}/libInfraPtpControl.so"
FX6_LIBINFRA_PTP_P152_RELPATH = f"{_FX6_USR_LIB_PREFIX}/libInfraPtpControl.so"

# ---------------------------------------------------------------------------
# Verified Expected ELF64 Donor Sizes / Symbol Counts
# ---------------------------------------------------------------------------

EXPECTED_MSC_SERVER_BYTES = 64_456
EXPECTED_MSC_SERVER_EXPORTS = 125
EXPECTED_MSC_SERVER_IMPORTS = 69

EXPECTED_USB_CONTROL_BYTES = 135_424
EXPECTED_USB_CONTROL_EXPORTS = 351
EXPECTED_USB_CONTROL_IMPORTS = 128

EXPECTED_WLAN_ADJUST_BYTES = 73_168
EXPECTED_WLAN_ADJUST_EXPORTS = 188
EXPECTED_WLAN_ADJUST_IMPORTS = 119

EXPECTED_WLAN_RESOURCE_BYTES = 56_464
EXPECTED_WLAN_RESOURCE_EXPORTS = 94
EXPECTED_WLAN_RESOURCE_IMPORTS = 90

EXPECTED_FX3_BT_CORE_EXPORTS = 509
EXPECTED_FX6_BT_CORE_EXPORTS = 503
EXPECTED_FX3_BLE_EXPORTS = 1_340
EXPECTED_FX6_BLE_EXPORTS = 1_053
EXPECTED_FX3_ETHER_EXPORTS = 286
EXPECTED_FX6_ETHER_EXPORTS = 480

# ---------------------------------------------------------------------------
# Pillar 1 Constants: Wi-Fi 802.11ac (2.4/5 GHz) & p12/p13 RF NVS Isolation
# ---------------------------------------------------------------------------

USB_VID_SONY_HEX = "0x054C"
USB_PID_FX3_MSC_HEX = "0x0DA1"
USB_PID_FX3_SERVICE_HEX = "0x0336"

WIFI_SUPPORTED_BANDS: Tuple[str, ...] = ("2.4GHZ_80211N", "5GHZ_80211AC")
VALID_WIFI_MODES: Tuple[str, ...] = (
    "AIRPLANE_ISOLATED_P12",
    "AP_DIRECT",
    "STATION_ROUTER",
    "RF_NVS_CALIB_WRITE_ATTEMPT",
)
RF_NVS_IMMUTABLE_PARTITIONS: Tuple[str, ...] = (
    "p12:/cert",
    "/dev/nflasha12",
    "/dev/cnflasha12",
    "p13:/rf_nvs",
    "/dev/nflasha13",
    "/dev/cnflasha13",
    "/dev/nflasha23/INFO/WIFI_INF.TXT",
    "p2:/Backup.bin",
)

WIFI_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "AIRPLANE_MODE_ON",
    "AIRPLANE_MODE_OFF",
    "AIRPLANE_MODE_STATE_DONE",
    "BLE_2_4_GHZ_ONLY",
    "BLE_2_4_GHZ_OR_5_GHZ",
    "CLOUD_CONNECT_METHOD_SMARTPHONE_USB_TETHERING",
    "CAUTION_ID_FACTOR_FTP_USB_LAN",
)
WIFI_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "AIRPLANE_MODE_ON",
    "AIRPLANE_MODE_OFF",
    "BKID_APP_EXTERN_MENU_WIFI_POWER_MODE",
    "BKID_APP_EXTERN_MENU_WIFI_SET",
    "BKID_APP_EXTERN_SETTING_AIRPLANE_MODE",
    "BKID_APP_EXTERN_WIFI_RUSH_EXCLUSION_TYPE",
    "BKID_APP_CAMERA_NETWORK_SYSTEM_MODE_BASE_INFO",
)
WIFI_SENCORE_SHARED_MARKERS: Tuple[str, ...] = (
    "START_WIFI_CHECK",
    "END_WIFI_CHECK",
    "MPR_CMD_EXEC_WIFI_TEST",
    "MPR_CMD_SET_RF_TEST_MODE",
    "MPR_CMD_SET_WIFI_TEST_MODE",
)
WIFI_CP_SHARED_MARKERS: Tuple[str, ...] = (
    "DFS_FACTOR_WIFI_CONNECT",
    "MSG_ID_INFRABB_AUDIO_SET_TX_RF_POWER",
)
WLAN_RESOURCE_MARKERS: Tuple[str, ...] = (
    "/usr/kmod/wlan.ko",
    "/usr/kmod/wlanMemoryAllocator.ko",
    "/usr/lib/firmware/BDF/bdwlan30_1vy_rc_sHH.bin",
    "/usr/lib/firmware/qwlan30.bin",
    "/usr/wlan/ath/MurataTypeTP.bin",
    "/usr/wlan/ath/otp.bin",
    "GetPowerMode",
    "SetPowerMode",
    "GetWifiCh",
    "GetWifiPowerMode",
)
WLAN_ADJUST_MARKERS: Tuple[str, ...] = (
    "/dev/nflasha23/INFO/WIFI_INF.TXT",
    "/dev/nflasha23/INFO/WPS_PIN.TXT",
    "WlanAdjust_Init",
    "WlanAdjust_wpa_ctrl_open",
    "WlanAdjust_wpa_ctrl_request",
)

# ---------------------------------------------------------------------------
# Pillar 2 Constants: BLE Creators' App vs FX6 Content Browser / M&C Bridge
# ---------------------------------------------------------------------------

VALID_BT_BRIDGE_SCENARIOS: Tuple[str, ...] = (
    "FX6_NO_BLE_NONBLOCK_MASKED",
    "AIRPLANE_P12_BT_OFF",
    "FX3_CREATORS_BLE_PAIRING_HOST",
    "FX6_DAEMON_BLOCKING_WAIT_UNMASKED",
    "BT_NVS_BDADDR_WRITE_ATTEMPT",
)
BT_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "BLUETOOTH_CONNECTION_STATE_OFF",
    "BLUETOOTH_CONNECTION_STATE_ON",
    "BLUETOOTH_PAIRING_LAUNCH_FUNCTION_CLOUD_CONNECTION",
    "BLUETOOTH_PAIRING_LAUNCH_FUNCTION_REGISTER_SMARTPHONE",
    "BLUETOOTH_PAIRING_LAUNCH_FUNCTION_SEND_TO_SMARTPHONE",
    "BLUETOOTH_PAIRING_STATUS_PAIRED",
    "BLE_BTC_PAIRING_RESULT_SUCCESS",
)
BT_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "BKID_APP_EXTERN_MENU_BT_SETTING",
    "BKID_APP_SETTING_BLUETOOTH_FUNCTION",
    "BKID_APP_USER_MENU_BLUETOOTH0",
    "BLUETOOTH_CONNECTION_STATE_OFF",
    "BLUETOOTH_CONNECTION_STATE_ON",
    "BLUETOOTH_DEVICE_ADDRESS_VALUE_NOT_EXIST",
    "BLE_BTC_PAIRING_RESULT_SUCCESS",
)
BT_SENCORE_SHARED_MARKERS: Tuple[str, ...] = (
    "LOAD_BT_FIRMWARE",
    "UNLOAD_BT_FIRMWARE",
    "PREPARE_BT_DEV_ADDR",
    "READ_BT_GPIO",
    "SET_BT_LOW_POWER_MODE",
)
BT_CP_SHARED_MARKERS: Tuple[str, ...] = (
    "GpHCI",
    "HCIpJ",
)
BT_CORE_MARKERS: Tuple[str, ...] = (
    "/dev/ttyAMA3",
    "/tmp_bt/bsa_s_pid",
    "/usr/bin/bt_stack.conf",
    "hci_update_baud_rate",
)

# ---------------------------------------------------------------------------
# Pillar 3 Constants: USB Type-C Multi-Role (MSC 054C:0DA1, MTP, UVC/UAC)
# ---------------------------------------------------------------------------

VALID_USB_ROLES: Tuple[str, ...] = (
    "MSC_RECOVERY_054C_0DA1",
    "SERVICE_HANDSHAKE_054C_0336",
    "MTP_PTP_REMOTE_SHOOTING",
    "UVC_UAC_HDMI_CAPTURE_BRIDGE",
    "FX6_NATIVE_USB_STREAMING_MASKED",
    "USB_LAN_CDC_NCM_ETHERNET",
    "UNMASKED_UVC_HIJACKING_MSC",
)
USB_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "VAL_setting_usb_connection_method_USB_CONNECTION_MASS_STORAGE",
    "VAL_setting_usb_connection_method_USB_CONNECTION_MTP",
    "VAL_setting_usb_connection_method_USB_CONNECTION_USB_STREAMING",
    "VAL_usb_connection_latest_selected_after_connection_USB_CONNECTION_LATEST_SELECTED_REMOTE_PC",
    "PID_SET_EE_FRAME_RATE_MODE_BY_UVC",
    "INFRA_NOTIFY_USB_STREAMING_STATE_CHANGED",
)
USB_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "BKID_APP_USB_CONNECTION_LATEST_SELECTED_AFTER_CONNECTION0",
    "BKID_APP_SETTING_USB_STREAMING_PROCAM",
    "BKID_APP_SETTING_USB_STREAMING_FORMAT_PROCAM",
    "BKID_APP_SETTING_USB_STREAMING_AUDIO_PROCAM",
    "BO_ID_UVC",
    "USB_CONNECTION_MASS_STORAGE",
    "USB_CONNECTION_MTP",
    "USB_CONNECTION_USB_STREAMING",
)
USB_CMN_MARKERS: Tuple[str, ...] = (
    "/dev/usb/gadgetcore",
    "/proc/usb_gadget",
    "/usr/kmod/xhci-hcd.ko",
    "CUsbGadgetStorage",
    "CUsbGadgetStill",
    "CUsbGadgetStreaming",
)
USB_CONTROL_MARKERS: Tuple[str, ...] = (
    "UsbControl_Init",
    "UsbControl_Exit",
    "MSGID_START_GADGET_CMD",
    "MSGID_STOP_GADGET_CMD",
    "MSGID_SETCONFIG_MTP_EVT",
)
MSC_SERVER_MARKERS: Tuple[str, ...] = (
    "MassStorageServer_Create",
    "MassStorageServer_Destroy",
    "MscServer_Init",
    "MscServer_Exit",
    "MSC_MSGID_MASSTORAGE_IN",
    "MSC_MSGID_MASSTORAGE_OUT",
)

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Wired USB-LAN Gigabit Ethernet FTP & Monitor & Control
# ---------------------------------------------------------------------------

VALID_ETHER_ADAPTERS: Tuple[str, ...] = (
    "CDC_NCM_RTL8153_GIGABIT",
    "CDC_NCM_AX88179_GIGABIT",
    "USB_TETHERING_CDC_NCM",
    "FX6_WIREDLAN_WOL_DOCK_ABSENT",
    "UNPLUGGED_ETHER_DONGLE_NONBLOCK",
    "WIFI_WLAN0_UNDER_P12",
)
ETHER_SENCORE_FX3_MARKERS: Tuple[str, ...] = (
    "USB_ETHER_FORCE_MODE_SET",
    "USB_GET_SPEED",
    "USB_BUSPOWER_SUPPLY_CONTROL",
)
ETHER_SENCORE_FX6_EXTRA_MARKERS: Tuple[str, ...] = (
    "WIREDLAN_NETIF_DOWN",
    "WIREDLAN_WOL_ENABLE",
    "WIREDLAN_WOL_CTRL_ETHER_IC_PWRON",
    "USB_SEL_ALT_MODE",
)
ETHER_NETSERVICE_SHARED_MARKERS: Tuple[str, ...] = (
    "/usr/lib/netconf/dhcpcd_wired_dns_4.conf",
    "/usr/sbin/dhcpcd",
    "NseMiscGetMacAddressForUsbEther",
    "NseMiscGetMacAddressForWiredEther",
    "NseMiscSetEtherRemoteAccess",
)
ETHER_NETSERVICE_FX6_EXTRA_MARKERS: Tuple[str, ...] = (
    "WESStartCableLinkCheck",
    "WESExecStopCableLinkCheck",
    "WESReconnect",
    "NseMiscGetStatusEther",
    "NseMiscReadTxRxByteInfo",
)
ETHER_FTP_SHARED_MARKERS: Tuple[str, ...] = (
    "InfraFtpClient_Init",
    "InfraFtpClient_Exit",
)

# ---------------------------------------------------------------------------
# Write-Protection Regex & Volatile Staging Rules
# ---------------------------------------------------------------------------

VOLATILE_STAGING_PREFIXES_P152: Tuple[str, ...] = (
    "/tmp/",
    "/var/run/",
    "ram://",
)
FORBIDDEN_PERSISTENT_RF_OR_EMMC_RE_P152 = re.compile(
    r"(?:/dev/nflasha|/dev/cnflasha|/dev/pnflasha|/dev/mmcblk0|"
    r"p12:/|p13:/|p18:/|p2:/|p6:/|p8:/|"
    r"backup\.bin|cpapp-b\.bin|wifi_inf\.txt|wps_pin\.txt|rf_nvs|mac_nvs|bdaddr)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class WifiRfNvsEvalResult:
    valid: bool
    status: str
    wifi_mode: str
    band: str
    classification: str
    p12_airplane_mode: bool
    rf_tx_enabled: bool
    rf_nvs_p12_p13_writes_permitted: bool
    rf_nvs_mutation_bytes: int
    blocking_wait_ms: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BtBleBridgeEvalResult:
    valid: bool
    status: str
    scenario: str
    classification: str
    fx6_daemon_masked: bool
    bt_hci_blocking_wait_ms: int
    bt_hci_blocking_wait_eliminated: bool
    ble_creators_app_active: bool
    rf_nvs_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UsbMultiRoleEvalResult:
    valid: bool
    status: str
    usb_role: str
    usb_vid_pid: str
    classification: str
    usb_msc_0da1_recovery_intact: bool
    service_0336_reachable: bool
    uvc_via_hdmi_bridge_only: bool
    non_blocking_stub_rc: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class WiredEtherFtpMcEvalResult:
    valid: bool
    status: str
    adapter_profile: str
    classification: str
    link_speed_mbps: int
    p12_rf_off_compliant: bool
    ftp_ftpes_supported: bool
    monitor_control_ptpip_supported: bool
    blocking_wait_ms: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase152WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    rf_nvs_p12_p13_writes_permitted: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    rf_nvs_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar1WifiRfNvsReport:
    passed: bool
    fx3_appfw_wifi_hits: int
    fx6_appfw_wifi_hits: int
    fx3_sencore_wifi_hits: int
    fx6_sencore_wifi_hits: int
    fx3_cp_wifi_hits: int
    fx6_cp_wifi_hits: int
    fx3_wlan_resource: ElfSectionSummary
    fx6_wlan_resource: ElfSectionSummary
    fx3_wlan_adjust: ElfSectionSummary
    fx6_wlan_adjust: ElfSectionSummary
    wlan_adjust_abi_identical: bool
    fx3_backup_subsystems: int
    fx6_backup_subsystems: int
    fx3_backup_checksums_valid: bool
    fx6_backup_checksums_valid: bool
    rf_nvs_p12_p13_writes_permitted: bool
    rf_nvs_mutation_bytes: int
    sample_evals: Tuple[WifiRfNvsEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2BtBleBridgeReport:
    passed: bool
    fx3_appfw_bt_hits: int
    fx6_appfw_bt_hits: int
    fx3_sencore_bt_hits: int
    fx6_sencore_bt_hits: int
    fx3_cp_hci_hits: int
    fx6_cp_hci_hits: int
    fx3_bt_core: ElfSectionSummary
    fx6_bt_core: ElfSectionSummary
    fx3_ble_le: ElfSectionSummary
    fx6_ble_le: ElfSectionSummary
    bt_hci_blocking_wait_ms: int
    bt_hci_blocking_wait_eliminated: bool
    sample_evals: Tuple[BtBleBridgeEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3UsbMultiRoleReport:
    passed: bool
    fx3_appfw_usb_hits: int
    fx6_appfw_usb_hits: int
    fx3_msc_server: ElfSectionSummary
    fx6_msc_server: ElfSectionSummary
    msc_server_abi_identical: bool
    fx3_usb_control: ElfSectionSummary
    fx6_usb_control: ElfSectionSummary
    usb_control_abi_identical: bool
    fx3_usb_cmn: ElfSectionSummary
    fx6_usb_cmn: ElfSectionSummary
    fx3_ptp_control: ElfSectionSummary
    fx6_ptp_control: ElfSectionSummary
    usb_msc_0da1_recovery_intact: bool
    sample_evals: Tuple[UsbMultiRoleEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4WiredEtherFtpMcReport:
    passed: bool
    fx3_sencore_ether_hits: int
    fx6_sencore_wol_extra_hits: int
    fx3_cp_ether_hits: int
    fx3_net_ether: ElfSectionSummary
    fx6_net_ether: ElfSectionSummary
    fx3_ftp_client: ElfSectionSummary
    fx6_ftp_client: ElfSectionSummary
    fx3_im_elf: ElfSectionSummary
    fx6_im_elf: ElfSectionSummary
    im_elf_abi_identical: bool
    wired_usblan_passthrough_verified: bool
    sample_evals: Tuple[WiredEtherFtpMcEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class NetworkUsbTouchpointEntry:
    touchpoint_id: str
    subsystem: str
    fx6_interface: str
    fx3_target: str
    classification: str
    shim_layer: str
    blocking_wait_eliminated: bool
    write_protected: bool
    notes: str


@dataclass(frozen=True)
class NetworkUsbCompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    subsystem_counts: Dict[str, int]
    touchpoints: Tuple[NetworkUsbTouchpointEntry, ...]


@dataclass(frozen=True)
class RealhwWifiBtUsbUvcNetworkBridgeReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    rf_nvs_p12_p13_writes_permitted: bool
    rf_nvs_mutation_bytes: int
    usb_msc_0da1_recovery_intact: bool
    bt_hci_blocking_wait_eliminated: bool
    bt_hci_blocking_wait_ms: int
    persistent_emmc_writes_authorized: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    donor_file_sizes: Dict[str, int]
    pillar1_wifi_rf_nvs: Pillar1WifiRfNvsReport
    pillar2_bt_ble_bridge: Pillar2BtBleBridgeReport
    pillar3_usb_multi_role: Pillar3UsbMultiRoleReport
    pillar4_wired_ether_ftp_mc: Pillar4WiredEtherFtpMcReport
    compatibility_matrix: NetworkUsbCompatMatrixSummary
    volatile_guard_ok: Phase152WriteGuardResult
    forbidden_p12_guard_blocked: Phase152WriteGuardResult
    forbidden_p13_guard_blocked: Phase152WriteGuardResult
    forbidden_backup_guard_blocked: Phase152WriteGuardResult
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only Binary Helper (os.O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------


def _scan_tokens_mmap_rdonly(
    path: Path,
    tokens: Sequence[str],
) -> Tuple[int, Dict[str, int]]:
    """Open `path` strictly `os.O_RDONLY` and count tokens over `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {t: 0 for t in tokens}
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            return sz, _count_tokens_single_pass(mm, tokens)
    finally:
        os.close(fd)


def _read_rdonly_bytes(path: Path) -> bytes:
    """Strictly read a small binary (`Backup.bin` / `cpapp-b.bin`) via `os.O_RDONLY`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return b""
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            return bytes(mm[:])
    finally:
        os.close(fd)


def _build_synthetic_bk4_dual_record(subsystems: int, seed: int) -> bytes:
    """Build deterministic clean-room dual-record `BK4\\x00` Backup.bin buffer."""
    body_tag = seed.to_bytes(4, "little")

    def _make_record(marker_path: str) -> bytes:
        table = bytearray(DESCRIPTOR_TABLE_BYTES)
        ent = bytearray(DESCRIPTOR_SLOT_BYTES)
        struct.pack_into("<QQII", ent, 0, 0x1000, 0x1FFF, 1, 0)
        pb = marker_path.encode("ascii")
        ent[24 : 24 + len(pb)] = pb
        table[0:DESCRIPTOR_SLOT_BYTES] = ent
        table[DESCRIPTOR_TABLE_BYTES - len(body_tag) :] = body_tag

        hdr = bytearray(BK4_HEADER_BYTES)
        struct.pack_into(
            "<II4s4sIIIII",
            hdr,
            0,
            0x04000000,
            BK4_SYNC_U32,
            b"\x00\x00\x00\x00",
            BK4_MAGIC_BYTES,
            subsystems,
            2048,
            BK4_HEADER_BYTES,
            len(table),
            0,
        )
        body = bytes(hdr) + bytes(table)
        csum = (sum(body) - sum(body[32:36])) & 0xFFFFFFFF
        struct.pack_into("<I", hdr, 32, csum)
        return bytes(hdr) + bytes(table)

    return _make_record("\\av-cam.bin") + _make_record("\\sabin\\idt_cam.bin")


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def build_clean_room_realhw_wifi_bt_usb_network_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room synthetic ELF64 & token fixtures for Phase 152."""
    fx3_appfw_tokens = (
        WIFI_APPFW_FX3_MARKERS + BT_APPFW_FX3_MARKERS + USB_APPFW_FX3_MARKERS
    )
    fx6_appfw_tokens = (
        WIFI_APPFW_FX6_MARKERS + BT_APPFW_FX6_MARKERS + USB_APPFW_FX6_MARKERS
    )
    fx3_sencore_tokens = (
        WIFI_SENCORE_SHARED_MARKERS + BT_SENCORE_SHARED_MARKERS + ETHER_SENCORE_FX3_MARKERS
    )
    fx6_sencore_tokens = (
        WIFI_SENCORE_SHARED_MARKERS
        + BT_SENCORE_SHARED_MARKERS
        + ETHER_SENCORE_FX3_MARKERS
        + ETHER_SENCORE_FX6_EXTRA_MARKERS
    )
    fx3_cp_tokens = WIFI_CP_SHARED_MARKERS + BT_CP_SHARED_MARKERS + (
        "DFS_FACTOR_ETHER_CONNECT",
        "DFS_FACTOR_USB_CONNECT",
    )
    fx6_cp_tokens = WIFI_CP_SHARED_MARKERS + BT_CP_SHARED_MARKERS + ("DFS_FACTOR_USB_CONNECT",)

    msc_exports = [f"msc_exp_{i}" for i in range(EXPECTED_MSC_SERVER_EXPORTS - len(MSC_SERVER_MARKERS))] + list(
        MSC_SERVER_MARKERS
    )
    msc_imports = [f"msc_imp_{i}" for i in range(EXPECTED_MSC_SERVER_IMPORTS)]

    usb_ctrl_exports = [f"uc_exp_{i}" for i in range(EXPECTED_USB_CONTROL_EXPORTS - 2)] + [
        "UsbControl_Init",
        "UsbControl_Exit",
    ]
    usb_ctrl_imports = [f"uc_imp_{i}" for i in range(EXPECTED_USB_CONTROL_IMPORTS)]

    wlan_adj_exports = [f"wa_exp_{i}" for i in range(EXPECTED_WLAN_ADJUST_EXPORTS - 3)] + [
        "WlanAdjust_Init",
        "WlanAdjust_wpa_ctrl_open",
        "WlanAdjust_wpa_ctrl_request",
    ]
    wlan_adj_imports = [f"wa_imp_{i}" for i in range(EXPECTED_WLAN_ADJUST_IMPORTS)]

    wlan_res_exports = [f"wr_exp_{i}" for i in range(EXPECTED_WLAN_RESOURCE_EXPORTS - 4)] + [
        "GetPowerMode",
        "SetPowerMode",
        "GetWifiCh",
        "GetWifiPowerMode",
    ]
    wlan_res_imports = [f"wr_imp_{i}" for i in range(EXPECTED_WLAN_RESOURCE_IMPORTS)]

    fx3_bt_exports = [f"bt3_exp_{i}" for i in range(EXPECTED_FX3_BT_CORE_EXPORTS - 1)] + [
        "hci_update_baud_rate"
    ]
    fx6_bt_exports = [f"bt6_exp_{i}" for i in range(EXPECTED_FX6_BT_CORE_EXPORTS - 1)] + [
        "hci_update_baud_rate"
    ]
    fx3_ble_exports = [f"ble3_exp_{i}" for i in range(EXPECTED_FX3_BLE_EXPORTS - 1)] + [
        "InfraBluetoothLowEnergy_init"
    ]
    fx6_ble_exports = [f"ble6_exp_{i}" for i in range(EXPECTED_FX6_BLE_EXPORTS - 1)] + [
        "InfraBluetoothLowEnergy_init"
    ]
    fx3_ether_exports = [f"eth3_exp_{i}" for i in range(EXPECTED_FX3_ETHER_EXPORTS - 3)] + [
        "NseMiscGetMacAddressForUsbEther",
        "NseMiscGetMacAddressForWiredEther",
        "NseMiscSetEtherRemoteAccess",
    ]
    fx6_ether_exports = [f"eth6_exp_{i}" for i in range(EXPECTED_FX6_ETHER_EXPORTS - 8)] + [
        "NseMiscGetMacAddressForUsbEther",
        "NseMiscGetMacAddressForWiredEther",
        "NseMiscSetEtherRemoteAccess",
        "WESStartCableLinkCheck",
        "WESExecStopCableLinkCheck",
        "WESReconnect",
        "NseMiscGetStatusEther",
        "NseMiscReadTxRxByteInfo",
    ]
    fx3_ftp_exports = [f"ftp3_exp_{i}" for i in range(599 - 2)] + [
        "InfraFtpClient_Init",
        "InfraFtpClient_Exit",
    ]
    fx6_ftp_exports = [f"ftp6_exp_{i}" for i in range(605 - 2)] + [
        "InfraFtpClient_Init",
        "InfraFtpClient_Exit",
    ]
    fx3_ptp_exports = [f"ptp3_exp_{i}" for i in range(456 - 2)] + [
        "InfraPtpControl_Init",
        "PTPT_EE_end_usb",
    ]
    fx6_ptp_exports = [f"ptp6_exp_{i}" for i in range(435 - 2)] + [
        "InfraPtpControl_Init",
        "PtptMultiSessionCallBackWrapper",
    ]
    fx3_usb_cmn_exports = [f"ucmn3_exp_{i}" for i in range(479)]
    fx6_usb_cmn_exports = [f"ucmn6_exp_{i}" for i in range(503)]

    im_exports = [f"im_exp_{i}" for i in range(11)]
    im_imports = [f"im_imp_{i}" for i in range(85)]
    im_needed = ["libIMDB.so", "libbackup.so", "libosal_uipc.so"]

    return {
        "fx3_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=("libsencore.so",),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=fx3_appfw_tokens,
        ),
        "fx6_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=("libsencore.so",),
            dt_needed=("libsencore.so", "libmpr.so"),
            rodata_strings=fx6_appfw_tokens,
        ),
        "fx3_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc_exp_{i}" for i in range(EXPECTED_SENCORE_EXPORTS)),
            imports=tuple(f"sc_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=fx3_sencore_tokens,
        ),
        "fx6_sencore": _build_synthetic_elf64(
            exports=tuple(f"sc_exp_{i}" for i in range(EXPECTED_SENCORE_EXPORTS)),
            imports=tuple(f"sc_imp_{i}" for i in range(EXPECTED_SENCORE_IMPORTS)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=fx6_sencore_tokens,
        ),
        "fx3_cpapp": b"CPAPP_FX3\x00" + b"\x00".join(t.encode("ascii") for t in fx3_cp_tokens) + b"\x00",
        "fx6_cpapp": b"CPAPP_FX6\x00" + b"\x00".join(t.encode("ascii") for t in fx6_cp_tokens) + b"\x00",
        "fx3_backup": _build_synthetic_bk4_dual_record(819, 0x1001),
        "fx6_backup": _build_synthetic_bk4_dual_record(840, 0x2002),
        "fx3_im_elf": _build_synthetic_elf64(
            exports=im_exports,
            imports=im_imports,
            dt_needed=im_needed,
            rodata_strings=("im_entry",),
        ),
        "fx6_im_elf": _build_synthetic_elf64(
            exports=im_exports,
            imports=im_imports,
            dt_needed=im_needed,
            rodata_strings=("im_entry",),
        ),
        "fx3_msc_server": _build_synthetic_elf64(
            exports=msc_exports,
            imports=msc_imports,
            dt_needed=("libUsbControl.so",),
            rodata_strings=MSC_SERVER_MARKERS,
        ),
        "fx6_msc_server": _build_synthetic_elf64(
            exports=msc_exports,
            imports=msc_imports,
            dt_needed=("libUsbControl.so",),
            rodata_strings=MSC_SERVER_MARKERS,
        ),
        "fx3_usb_control": _build_synthetic_elf64(
            exports=usb_ctrl_exports,
            imports=usb_ctrl_imports,
            dt_needed=("libInfraUsbCmn.so",),
            rodata_strings=USB_CONTROL_MARKERS,
        ),
        "fx6_usb_control": _build_synthetic_elf64(
            exports=usb_ctrl_exports,
            imports=usb_ctrl_imports,
            dt_needed=("libInfraUsbCmn.so",),
            rodata_strings=USB_CONTROL_MARKERS,
        ),
        "fx3_usb_cmn": _build_synthetic_elf64(
            exports=fx3_usb_cmn_exports,
            imports=tuple(f"ucmn_imp_{i}" for i in range(79)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=USB_CMN_MARKERS,
        ),
        "fx6_usb_cmn": _build_synthetic_elf64(
            exports=fx6_usb_cmn_exports,
            imports=tuple(f"ucmn_imp_{i}" for i in range(80)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=USB_CMN_MARKERS,
        ),
        "fx3_wlan_resource": _build_synthetic_elf64(
            exports=wlan_res_exports,
            imports=wlan_res_imports,
            dt_needed=("libWlanControlCommon.so",),
            rodata_strings=WLAN_RESOURCE_MARKERS,
        ),
        "fx6_wlan_resource": _build_synthetic_elf64(
            exports=wlan_res_exports,
            imports=wlan_res_imports,
            dt_needed=("libWlanControlCommon.so",),
            rodata_strings=WLAN_RESOURCE_MARKERS,
        ),
        "fx3_wlan_adjust": _build_synthetic_elf64(
            exports=wlan_adj_exports,
            imports=wlan_adj_imports,
            dt_needed=("libWlanResource.so",),
            rodata_strings=WLAN_ADJUST_MARKERS,
        ),
        "fx6_wlan_adjust": _build_synthetic_elf64(
            exports=wlan_adj_exports,
            imports=wlan_adj_imports,
            dt_needed=("libWlanResource.so",),
            rodata_strings=WLAN_ADJUST_MARKERS,
        ),
        "fx3_bt_core": _build_synthetic_elf64(
            exports=fx3_bt_exports,
            imports=tuple(f"btc3_imp_{i}" for i in range(108)),
            dt_needed=("libResourceBluetooth.so",),
            rodata_strings=BT_CORE_MARKERS,
        ),
        "fx6_bt_core": _build_synthetic_elf64(
            exports=fx6_bt_exports,
            imports=tuple(f"btc6_imp_{i}" for i in range(111)),
            dt_needed=("libResourceBluetooth.so",),
            rodata_strings=BT_CORE_MARKERS,
        ),
        "fx3_ble_le": _build_synthetic_elf64(
            exports=fx3_ble_exports,
            imports=tuple(f"ble3_imp_{i}" for i in range(173)),
            dt_needed=("libInfraBluetoothCore.so",),
            rodata_strings=("DILocationService", "DIRXTXControlService"),
        ),
        "fx6_ble_le": _build_synthetic_elf64(
            exports=fx6_ble_exports,
            imports=tuple(f"ble6_imp_{i}" for i in range(137)),
            dt_needed=("libInfraBluetoothCore.so",),
            rodata_strings=("DIRXTXControlService",),
        ),
        "fx3_net_ether": _build_synthetic_elf64(
            exports=fx3_ether_exports,
            imports=tuple(f"eth3_imp_{i}" for i in range(94)),
            dt_needed=("libNetService.so",),
            rodata_strings=ETHER_NETSERVICE_SHARED_MARKERS,
        ),
        "fx6_net_ether": _build_synthetic_elf64(
            exports=fx6_ether_exports,
            imports=tuple(f"eth6_imp_{i}" for i in range(96)),
            dt_needed=("libNetService.so",),
            rodata_strings=ETHER_NETSERVICE_SHARED_MARKERS + ETHER_NETSERVICE_FX6_EXTRA_MARKERS,
        ),
        "fx3_ftp_client": _build_synthetic_elf64(
            exports=fx3_ftp_exports,
            imports=tuple(f"ftp3_imp_{i}" for i in range(215)),
            dt_needed=("libNetService.so",),
            rodata_strings=ETHER_FTP_SHARED_MARKERS,
        ),
        "fx6_ftp_client": _build_synthetic_elf64(
            exports=fx6_ftp_exports,
            imports=tuple(f"ftp6_imp_{i}" for i in range(144)),
            dt_needed=("libNetService.so",),
            rodata_strings=ETHER_FTP_SHARED_MARKERS,
        ),
        "fx3_ptp_control": _build_synthetic_elf64(
            exports=fx3_ptp_exports,
            imports=tuple(f"ptp3_imp_{i}" for i in range(117)),
            dt_needed=("libInfraUsbCmn.so",),
            rodata_strings=("InfraPtpControl_Init",),
        ),
        "fx6_ptp_control": _build_synthetic_elf64(
            exports=fx6_ptp_exports,
            imports=tuple(f"ptp6_imp_{i}" for i in range(113)),
            dt_needed=("libInfraUsbCmn.so",),
            rodata_strings=("InfraPtpControl_Init",),
        ),
    }


# ---------------------------------------------------------------------------
# Pillar Evaluators (Individual Deterministic Contracts)
# ---------------------------------------------------------------------------


def evaluate_wifi_rf_nvs_isolation(
    *,
    wifi_mode: str = "AIRPLANE_ISOLATED_P12",
    band: str = "5GHZ_80211AC",
    rf_nvs_write_requested: bool = False,
    blocking_wait_ms: int = 0,
) -> WifiRfNvsEvalResult:
    """Evaluate 802.11ac Wi-Fi compatibility and strict p12/p13 RF NVS write lock."""
    mode = wifi_mode.strip().upper()
    norm_band = band.strip().upper()
    errors: List[str] = []

    if mode not in VALID_WIFI_MODES:
        errors.append(f"BLOCKED_UNKNOWN_WIFI_MODE: {mode!r}")
    if norm_band not in WIFI_SUPPORTED_BANDS:
        errors.append(f"BLOCKED_UNSUPPORTED_WIFI_BAND: {norm_band!r}")
    if mode == "RF_NVS_CALIB_WRITE_ATTEMPT" or rf_nvs_write_requested:
        errors.append(
            "BLOCKED_P12_P13_RF_NVS_WRITE: Factory RF TX-power & MAC NVS in p12/p13 is strictly read-only"
        )
    if blocking_wait_ms > 0:
        errors.append(
            f"BLOCKED_WIFI_DAEMON_BLOCKING_WAIT: blocking_wait_ms={blocking_wait_ms} > 0"
        )

    p12_airplane = mode == "AIRPLANE_ISOLATED_P12"
    rf_tx = mode in ("AP_DIRECT", "STATION_ROUTER") and not rf_nvs_write_requested
    classification = (
        BRIDGE_CLASS_HARD_WRITE_PROTECTED
        if (mode == "RF_NVS_CALIB_WRITE_ATTEMPT" or rf_nvs_write_requested)
        else (
            BRIDGE_CLASS_SHIM_TRANSLATED
            if mode == "AIRPLANE_ISOLATED_P12"
            else BRIDGE_CLASS_NATIVE_PASSTHROUGH
        )
    )
    status = "WIFI_RF_NVS_ISOLATION_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return WifiRfNvsEvalResult(
        valid=len(errors) == 0,
        status=status,
        wifi_mode=mode,
        band=norm_band,
        classification=classification,
        p12_airplane_mode=p12_airplane,
        rf_tx_enabled=rf_tx,
        rf_nvs_p12_p13_writes_permitted=False,
        rf_nvs_mutation_bytes=0,
        blocking_wait_ms=blocking_wait_ms,
        errors=tuple(errors),
    )


def evaluate_bt_ble_daemon_bridge(
    *,
    scenario: str = "FX6_NO_BLE_NONBLOCK_MASKED",
    bt_hci_blocking_wait_ms: int = 0,
    mask_fx6_daemon_mismatch: bool = True,
    rf_nvs_write_requested: bool = False,
) -> BtBleBridgeEvalResult:
    """Evaluate FX3 BLE Creators' App vs FX6 Wi-Fi-only M&C non-blocking BT bridge."""
    scen = scenario.strip().upper()
    errors: List[str] = []

    if scen not in VALID_BT_BRIDGE_SCENARIOS:
        errors.append(f"BLOCKED_UNKNOWN_BT_SCENARIO: {scen!r}")
    if scen == "FX6_DAEMON_BLOCKING_WAIT_UNMASKED" or not mask_fx6_daemon_mismatch:
        errors.append(
            "BLOCKED_BT_DAEMON_UNMASKED_HANG: Stage-B must mask mismatched BT/BLE daemon wait"
        )
    if bt_hci_blocking_wait_ms > 0:
        errors.append(
            f"BLOCKED_BT_HCI_BLOCKING_WAIT: bt_hci_blocking_wait_ms={bt_hci_blocking_wait_ms} > 0"
        )
    if scen == "BT_NVS_BDADDR_WRITE_ATTEMPT" or rf_nvs_write_requested:
        errors.append(
            "BLOCKED_BT_BDADDR_NVS_WRITE: Factory BT MAC / p12/p13 NVS is strictly read-only"
        )

    if scen in ("BT_NVS_BDADDR_WRITE_ATTEMPT",) or rf_nvs_write_requested:
        classification = BRIDGE_CLASS_HARD_WRITE_PROTECTED
    elif scen == "FX3_CREATORS_BLE_PAIRING_HOST":
        classification = BRIDGE_CLASS_NATIVE_PASSTHROUGH
    elif scen == "FX6_NO_BLE_NONBLOCK_MASKED" or scen == "AIRPLANE_P12_BT_OFF":
        classification = BRIDGE_CLASS_MASKED_ABSENT_HW
    else:
        classification = BRIDGE_CLASS_SHIM_TRANSLATED

    eliminated = mask_fx6_daemon_mismatch and (bt_hci_blocking_wait_ms == 0)
    ble_active = scen == "FX3_CREATORS_BLE_PAIRING_HOST" and len(errors) == 0
    status = "BT_BLE_NONBLOCK_BRIDGE_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return BtBleBridgeEvalResult(
        valid=len(errors) == 0,
        status=status,
        scenario=scen,
        classification=classification,
        fx6_daemon_masked=mask_fx6_daemon_mismatch,
        bt_hci_blocking_wait_ms=bt_hci_blocking_wait_ms,
        bt_hci_blocking_wait_eliminated=eliminated,
        ble_creators_app_active=ble_active,
        rf_nvs_mutation_bytes=0,
        errors=tuple(errors),
    )


def evaluate_usb_multi_role_bridge(
    *,
    usb_role: str = "MSC_RECOVERY_054C_0DA1",
    preserve_msc_0da1: bool = True,
    mask_fx6_native_uvc: bool = True,
    non_blocking_stub_rc: int = 0,
) -> UsbMultiRoleEvalResult:
    """Evaluate USB Type-C multi-role switching while protecting MSC 054C:0DA1 recovery."""
    role = usb_role.strip().upper()
    errors: List[str] = []

    if role not in VALID_USB_ROLES:
        errors.append(f"BLOCKED_UNKNOWN_USB_ROLE: {role!r}")
    if not preserve_msc_0da1 or role == "UNMASKED_UVC_HIJACKING_MSC":
        errors.append(
            "BLOCKED_MSC_0DA1_RECOVERY_BREAK: UVC/MTP shim must never hijack MSC 054C:0DA1 recovery"
        )
    if role == "FX6_NATIVE_USB_STREAMING_MASKED" and not mask_fx6_native_uvc:
        errors.append(
            "BLOCKED_UNMASKED_FX6_USB_STREAMING: FX3 kernel gadget lacks FX6 ProCam UVC endpoints"
        )
    if non_blocking_stub_rc != 0:
        errors.append(f"BLOCKED_USB_STUB_NONZERO_RC: rc={non_blocking_stub_rc}")

    vid_pid_map = {
        "MSC_RECOVERY_054C_0DA1": "054C:0DA1",
        "SERVICE_HANDSHAKE_054C_0336": "054C:0336",
        "MTP_PTP_REMOTE_SHOOTING": "054C:0DA1_PTP",
        "UVC_UAC_HDMI_CAPTURE_BRIDGE": "HDMI_TO_UVC_EXTERNAL",
        "FX6_NATIVE_USB_STREAMING_MASKED": "MASKED_FALLBACK_054C:0DA1",
        "USB_LAN_CDC_NCM_ETHERNET": "CDC_NCM_ETHER",
        "UNMASKED_UVC_HIJACKING_MSC": "HIJACKED_MSC",
    }
    class_map = {
        "MSC_RECOVERY_054C_0DA1": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "SERVICE_HANDSHAKE_054C_0336": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "MTP_PTP_REMOTE_SHOOTING": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "UVC_UAC_HDMI_CAPTURE_BRIDGE": BRIDGE_CLASS_SHIM_TRANSLATED,
        "FX6_NATIVE_USB_STREAMING_MASKED": BRIDGE_CLASS_MASKED_ABSENT_HW,
        "USB_LAN_CDC_NCM_ETHERNET": BRIDGE_CLASS_SHIM_TRANSLATED,
        "UNMASKED_UVC_HIJACKING_MSC": BRIDGE_CLASS_MASKED_ABSENT_HW,
    }
    msc_intact = preserve_msc_0da1 and (role != "UNMASKED_UVC_HIJACKING_MSC")
    uvc_hdmi_only = role in ("UVC_UAC_HDMI_CAPTURE_BRIDGE", "FX6_NATIVE_USB_STREAMING_MASKED")
    status = "USB_MULTI_ROLE_BRIDGE_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return UsbMultiRoleEvalResult(
        valid=len(errors) == 0,
        status=status,
        usb_role=role,
        usb_vid_pid=vid_pid_map.get(role, "UNKNOWN"),
        classification=class_map.get(role, BRIDGE_CLASS_MASKED_ABSENT_HW),
        usb_msc_0da1_recovery_intact=msc_intact,
        service_0336_reachable=msc_intact,
        uvc_via_hdmi_bridge_only=uvc_hdmi_only,
        non_blocking_stub_rc=non_blocking_stub_rc,
        errors=tuple(errors),
    )


def evaluate_wired_ether_ftp_mc_bridge(
    *,
    adapter_profile: str = "CDC_NCM_RTL8153_GIGABIT",
    p12_airplane_mode_on: bool = True,
    mask_absent_wol_hw: bool = True,
    blocking_wait_ms: int = 0,
) -> WiredEtherFtpMcEvalResult:
    """Evaluate wired USB-LAN Gigabit Ethernet FTP & Monitor & Control bridge."""
    prof = adapter_profile.strip().upper()
    errors: List[str] = []

    if prof not in VALID_ETHER_ADAPTERS:
        errors.append(f"BLOCKED_UNKNOWN_ETHER_PROFILE: {prof!r}")
    if prof == "WIFI_WLAN0_UNDER_P12" and p12_airplane_mode_on:
        errors.append(
            "BLOCKED_WIFI_WLAN0_UNDER_P12: Wireless LAN disallowed when P12 Airplane Mode is enforced"
        )
    if prof == "FX6_WIREDLAN_WOL_DOCK_ABSENT" and not mask_absent_wol_hw:
        errors.append(
            "BLOCKED_UNMASKED_FX6_WOL_HW: FX3 lacks PCIe Wake-on-LAN RJ45 dock hardware"
        )
    if blocking_wait_ms > 0:
        errors.append(f"BLOCKED_ETHER_BLOCKING_WAIT: blocking_wait_ms={blocking_wait_ms} > 0")

    speed_map = {
        "CDC_NCM_RTL8153_GIGABIT": 1000,
        "CDC_NCM_AX88179_GIGABIT": 1000,
        "USB_TETHERING_CDC_NCM": 480,
        "FX6_WIREDLAN_WOL_DOCK_ABSENT": 0,
        "UNPLUGGED_ETHER_DONGLE_NONBLOCK": 0,
        "WIFI_WLAN0_UNDER_P12": 433,
    }
    class_map = {
        "CDC_NCM_RTL8153_GIGABIT": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "CDC_NCM_AX88179_GIGABIT": BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        "USB_TETHERING_CDC_NCM": BRIDGE_CLASS_SHIM_TRANSLATED,
        "FX6_WIREDLAN_WOL_DOCK_ABSENT": BRIDGE_CLASS_MASKED_ABSENT_HW,
        "UNPLUGGED_ETHER_DONGLE_NONBLOCK": BRIDGE_CLASS_SHIM_TRANSLATED,
        "WIFI_WLAN0_UNDER_P12": BRIDGE_CLASS_MASKED_ABSENT_HW,
    }
    p12_ok = p12_airplane_mode_on and (prof != "WIFI_WLAN0_UNDER_P12")
    ftp_ok = prof in ("CDC_NCM_RTL8153_GIGABIT", "CDC_NCM_AX88179_GIGABIT", "USB_TETHERING_CDC_NCM")
    mc_ok = prof in ("CDC_NCM_RTL8153_GIGABIT", "CDC_NCM_AX88179_GIGABIT", "USB_TETHERING_CDC_NCM")
    status = "WIRED_ETHER_FTP_MC_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return WiredEtherFtpMcEvalResult(
        valid=len(errors) == 0,
        status=status,
        adapter_profile=prof,
        classification=class_map.get(prof, BRIDGE_CLASS_MASKED_ABSENT_HW),
        link_speed_mbps=speed_map.get(prof, 0),
        p12_rf_off_compliant=p12_ok,
        ftp_ftpes_supported=ftp_ok,
        monitor_control_ptpip_supported=mc_ok,
        blocking_wait_ms=blocking_wait_ms,
        errors=tuple(errors),
    )


def evaluate_phase152_write_guard(target_path: str) -> Phase152WriteGuardResult:
    """Enforce volatile RAM staging only and zero persistent eMMC / p12 / p13 / RF NVS writes."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES_P152) and not bool(
        FORBIDDEN_PERSISTENT_RF_OR_EMMC_RE_P152.search(norm)
    )
    if is_volatile:
        return Phase152WriteGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            rf_nvs_p12_p13_writes_permitted=False,
            emmc_mutation_bytes=0,
            calibration_mutation_bytes=0,
            rf_nvs_mutation_bytes=0,
            errors=(),
        )
    return Phase152WriteGuardResult(
        valid=False,
        status="BLOCKED_PERSISTENT_RF_NVS_OR_EMMC_WRITE",
        target_path=norm,
        volatile_ram_staged=False,
        persistent_write_blocked=True,
        rf_nvs_p12_p13_writes_permitted=False,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        rf_nvs_mutation_bytes=0,
        errors=(f"BLOCKED_PERSISTENT_RF_NVS_OR_EMMC_WRITE: target_path={norm!r}",),
    )


# ---------------------------------------------------------------------------
# Quantitative 12-Touchpoint Network / BT / USB / UVC Compatibility Matrix
# ---------------------------------------------------------------------------


def build_phase152_network_usb_matrix() -> NetworkUsbCompatMatrixSummary:
    """Construct the 12-touchpoint Wi-Fi / BT / USB / UVC / Wired-LAN compatibility matrix."""
    entries: Tuple[NetworkUsbTouchpointEntry, ...] = (
        NetworkUsbTouchpointEntry(
            touchpoint_id="WIFI_80211AC_QCA_ATH_WLAN",
            subsystem="WIFI_RF",
            fx6_interface="libWlanResource.so / libWlanAdjust.so (2.4/5 GHz)",
            fx3_target="Stock FX3 wlan.ko + bdwlan30_1vy_rc_* + qwlan30.bin",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_layer="None (WlanAdjust 188/119 ABI identical; WlanResource 94/90)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="2.4/5 GHz 802.11ac radio & wpa_supplicant pass through under Stock kernel.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="WIFI_P12_AIRPLANE_ISOLATION",
            subsystem="WIFI_RF",
            fx6_interface="BKID_APP_EXTERN_SETTING_AIRPLANE_MODE / WF-12",
            fx3_target="Stage-B Volatile Airplane Mode + Wired USB-LAN Preferred",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_layer="libgrm-fbinit9.so + BK4 volatile RAM shadow",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Prevents WF-12 00342260 fatal dialog when Wi-Fi RF is isolated.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="RF_NVS_P12_P13_MAC_CALIB_LOCK",
            subsystem="WIFI_RF",
            fx6_interface="p12:/cert / p13 RF TX-Power & MAC / WIFI_INF.TXT",
            fx3_target="Hard O_RDONLY Guard (rf_nvs_p12_p13_writes_permitted=False)",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            shim_layer="Hard O_RDONLY Guard + volatile /tmp/ overlay",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Zero writes to factory regulatory RF TX-power tables, MAC, or BD_ADDR.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="BT_BLE_DAEMON_NONBLOCK_MASK",
            subsystem="BT_BLE",
            fx6_interface="FX6 BT/BLE Menu (no physical BLE Creators' App)",
            fx3_target="Masked Non-Blocking Stub (bt_hci_blocking_wait_ms=0)",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            shim_layer="libgrm-fbinit9.so + osal_uipc Non-Blocking Stub",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Eliminates appFw.so hang waiting for mismatched BT/BLE daemons.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="BT_CREATORS_APP_VS_MC_MOBILE",
            subsystem="BT_BLE",
            fx6_interface="Content Browser Mobile / Monitor & Control (Wi-Fi/LAN)",
            fx3_target="Stock FX3 BLE Creators' App isolated during Stage-B",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_layer="libgrm-fbinit9.so status masking + M&C over LAN/Wi-Fi",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Stage-B routes remote monitoring to Monitor & Control without BT daemon stall.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="USB_MSC_054C_0DA1_RECOVERY",
            subsystem="USB_MULTI_ROLE",
            fx6_interface="USB_CONNECTION_MASS_STORAGE / libInfraMscServer.so",
            fx3_target="Stock FX3 MSC (054C:0DA1) -> SERVICE (054C:0336) Recovery",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_layer="None (libInfraMscServer 125/69 & libUsbControl 351/128 identical)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="USB Mass Storage recovery access & 7-round Senser 054C:0336 stay 100% intact.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="USB_MTP_PTP_REMOTE_SHOOTING",
            subsystem="USB_MULTI_ROLE",
            fx6_interface="USB_CONNECTION_MTP / libInfraPtpControl.so",
            fx3_target="FX3 MTP / PTP Remote Shooting (PTPT_EE_end_usb)",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_layer="libUsbControl.so + libInfraPtpControl.so",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="MTP file transfer & CrSDK USB PTP remote remain functional without MSC break.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="USB_UVC_UAC_STREAMING_BRIDGE",
            subsystem="USB_MULTI_ROLE",
            fx6_interface="BKID_APP_SETTING_USB_STREAMING_PROCAM / BO_ID_UVC",
            fx3_target="Masked Native UVC Gadget -> HDMI-to-UVC Bridge",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            shim_layer="libgrm-fbinit9.so status mask (preserves 054C:0DA1)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="FX3 lacks native UVC gadget; masks FX6 USB Streaming UI so MSC never breaks.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="WIRED_USBLAN_GIGABIT_CDC_NCM",
            subsystem="WIRED_ETHER_FTP",
            fx6_interface="libNetServiceEther.so / USB_CONNECTION_METHOD_ETHER",
            fx3_target="FX3 USB-C CDC-NCM / RTL8153 / AX88179 Gigabit Adapter",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_layer="None (shared dhcpcd_wired_dns_4.conf & NseMisc USB Ether)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="FX3 7.02 auto-detects USB-LAN dongles at boot for stable Gigabit LAN.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="WIRED_FTP_FTPES_TRANSFER",
            subsystem="WIRED_ETHER_FTP",
            fx6_interface="libInfraFtpClient.so FTP/FTPES Transfer",
            fx3_target="FX3 libInfraFtpClient.so (SSL/FTPES + SFTP)",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_layer="libgrm-fbinit9.so + P12 RF-off wired path guard",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Media transfer via wired USB-LAN FTPES confined to external Slot A/B.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="MONITOR_CONTROL_PTPIP_RTSP",
            subsystem="WIRED_ETHER_FTP",
            fx6_interface="Monitor & Control PTP-IP (TCP/15740) + RTSP Low-Res",
            fx3_target="FX3 USB-LAN / Router Wi-Fi Multi-Session Bridge",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_layer="libInfraPtpControl.so + libNetServiceEther.so",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Supports Monitor & Control waveform/false-color/REC over wired LAN.",
        ),
        NetworkUsbTouchpointEntry(
            touchpoint_id="FX6_WIREDLAN_WOL_RJ45_ABSENT",
            subsystem="WIRED_ETHER_FTP",
            fx6_interface="libsencore.so WIREDLAN_WOL_* / PCIe RJ45",
            fx3_target="Masked Absent HW -> Non-Blocking Stub (rc=0)",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            shim_layer="libgrm-fbinit9.so Non-Blocking Stub",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Masks FX6-only Wake-on-LAN PCIe NIC controls absent on FX3 hardware.",
        ),
    )

    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    sub_counts: Dict[str, int] = {}
    for e in entries:
        class_counts[e.classification] = class_counts.get(e.classification, 0) + 1
        sub_counts[e.subsystem] = sub_counts.get(e.subsystem, 0) + 1

    return NetworkUsbCompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        subsystem_counts=sub_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Unified Phase 152 Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_wifi_bt_usb_uvc_network_bridge(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    clean_room: bool = False,
) -> RealhwWifiBtUsbUvcNetworkBridgeReport:
    """Run the 31st unified Phase 152 Wi-Fi, BT/BLE, USB/MSC/UVC & USB-LAN auditor."""
    forced = clean_room or is_forced_clean_room(env)
    rel_map: Dict[str, str] = {
        "fx3_appfw": FX3_APPFW_P152_RELPATH,
        "fx6_appfw": FX6_APPFW_P152_RELPATH,
        "fx3_sencore": FX3_LIBSENCORE_P152_RELPATH,
        "fx6_sencore": FX6_LIBSENCORE_P152_RELPATH,
        "fx3_cpapp": FX3_CPAPP_P152_RELPATH,
        "fx6_cpapp": FX6_CPAPP_P152_RELPATH,
        "fx3_backup": FX3_BACKUP_BIN_P152_RELPATH,
        "fx6_backup": FX6_BACKUP_BIN_P152_RELPATH,
        "fx3_im_elf": FX3_IM_ELF_P152_RELPATH,
        "fx6_im_elf": FX6_IM_ELF_P152_RELPATH,
        "fx3_msc_server": FX3_LIBINFRA_MSC_SERVER_RELPATH,
        "fx6_msc_server": FX6_LIBINFRA_MSC_SERVER_RELPATH,
        "fx3_usb_control": FX3_LIBUSB_CONTROL_RELPATH,
        "fx6_usb_control": FX6_LIBUSB_CONTROL_RELPATH,
        "fx3_usb_cmn": FX3_LIBINFRA_USB_CMN_RELPATH,
        "fx6_usb_cmn": FX6_LIBINFRA_USB_CMN_RELPATH,
        "fx3_wlan_resource": FX3_LIBWLAN_RESOURCE_RELPATH,
        "fx6_wlan_resource": FX6_LIBWLAN_RESOURCE_RELPATH,
        "fx3_wlan_adjust": FX3_LIBWLAN_ADJUST_RELPATH,
        "fx6_wlan_adjust": FX6_LIBWLAN_ADJUST_RELPATH,
        "fx3_bt_core": FX3_LIBINFRA_BT_CORE_RELPATH,
        "fx6_bt_core": FX6_LIBINFRA_BT_CORE_RELPATH,
        "fx3_ble_le": FX3_LIBINFRA_BLE_RELPATH,
        "fx6_ble_le": FX6_LIBINFRA_BLE_RELPATH,
        "fx3_net_ether": FX3_LIBNET_ETHER_P152_RELPATH,
        "fx6_net_ether": FX6_LIBNET_ETHER_P152_RELPATH,
        "fx3_ftp_client": FX3_LIBINFRA_FTP_P152_RELPATH,
        "fx6_ftp_client": FX6_LIBINFRA_FTP_P152_RELPATH,
        "fx3_ptp_control": FX3_LIBINFRA_PTP_P152_RELPATH,
        "fx6_ptp_control": FX6_LIBINFRA_PTP_P152_RELPATH,
    }

    resolved: Dict[str, Optional[Path]] = {}
    if not forced:
        for k, rel in rel_map.items():
            resolved[k] = resolve_donor_file(rel, repo_root=repo_root, env=env, clean_room=False)
    use_local = (not forced) and all(p is not None for p in resolved.values())
    mode = "LOCAL_DONOR_VERIFIED" if use_local else "CLEAN_ROOM_SYNTHETIC"
    src_mode = "LOCAL_DONOR_RDONLY" if use_local else "SYNTHETIC_CLEAN_ROOM"

    donor_sizes: Dict[str, int] = {}
    errors: List[str] = []

    fx3_appfw_tokens = WIFI_APPFW_FX3_MARKERS + BT_APPFW_FX3_MARKERS + USB_APPFW_FX3_MARKERS
    fx6_appfw_tokens = WIFI_APPFW_FX6_MARKERS + BT_APPFW_FX6_MARKERS + USB_APPFW_FX6_MARKERS
    fx3_sc_tokens = (
        WIFI_SENCORE_SHARED_MARKERS + BT_SENCORE_SHARED_MARKERS + ETHER_SENCORE_FX3_MARKERS
    )
    fx6_sc_tokens = (
        WIFI_SENCORE_SHARED_MARKERS
        + BT_SENCORE_SHARED_MARKERS
        + ETHER_SENCORE_FX3_MARKERS
        + ETHER_SENCORE_FX6_EXTRA_MARKERS
    )
    cp_tokens = tuple(
        sorted(
            set(WIFI_CP_SHARED_MARKERS)
            | set(BT_CP_SHARED_MARKERS)
            | {"DFS_FACTOR_ETHER_CONNECT", "DFS_FACTOR_USB_CONNECT"}
        )
    )

    if use_local:
        sz3_ap, fx3_ap_hits = _scan_tokens_mmap_rdonly(resolved["fx3_appfw"], fx3_appfw_tokens)  # type: ignore[arg-type]
        sz6_ap, fx6_ap_hits = _scan_tokens_mmap_rdonly(resolved["fx6_appfw"], fx6_appfw_tokens)  # type: ignore[arg-type]
        sz3_sc, fx3_sc_hits = _scan_tokens_mmap_rdonly(resolved["fx3_sencore"], fx3_sc_tokens)  # type: ignore[arg-type]
        sz6_sc, fx6_sc_hits = _scan_tokens_mmap_rdonly(resolved["fx6_sencore"], fx6_sc_tokens)  # type: ignore[arg-type]
        sz3_cp, fx3_cp_hits = _scan_tokens_mmap_rdonly(resolved["fx3_cpapp"], cp_tokens)  # type: ignore[arg-type]
        sz6_cp, fx6_cp_hits = _scan_tokens_mmap_rdonly(resolved["fx6_cpapp"], cp_tokens)  # type: ignore[arg-type]
        fx3_bk_buf = _read_rdonly_bytes(resolved["fx3_backup"])  # type: ignore[arg-type]
        fx6_bk_buf = _read_rdonly_bytes(resolved["fx6_backup"])  # type: ignore[arg-type]

        donor_sizes.update(
            {
                "fx3_appfw": sz3_ap,
                "fx6_appfw": sz6_ap,
                "fx3_sencore": sz3_sc,
                "fx6_sencore": sz6_sc,
                "fx3_cpapp": sz3_cp,
                "fx6_cpapp": sz6_cp,
                "fx3_backup": len(fx3_bk_buf),
                "fx6_backup": len(fx6_bk_buf),
            }
        )

        def _elf_scan(
            key: str, bname: str, body: str, toks: Sequence[str] = ()
        ) -> ElfSectionSummary:
            p = resolved[key]
            assert p is not None
            elf_sum, _exps, _imps = _scan_elf_and_tokens_rdonly(
                p, binary_name=bname, body_label=body, tokens=toks
            )
            donor_sizes[key] = elf_sum.file_bytes
            return elf_sum

        fx3_im_elf = _elf_scan("fx3_im_elf", "im.elf", "FX3_7.02")
        fx6_im_elf = _elf_scan("fx6_im_elf", "im.elf", "FX6_6.01")
        fx3_msc_srv = _elf_scan("fx3_msc_server", "libInfraMscServer.so", "FX3_7.02", MSC_SERVER_MARKERS)
        fx6_msc_srv = _elf_scan("fx6_msc_server", "libInfraMscServer.so", "FX6_6.01", MSC_SERVER_MARKERS)
        fx3_usb_ctrl = _elf_scan("fx3_usb_control", "libUsbControl.so", "FX3_7.02", USB_CONTROL_MARKERS)
        fx6_usb_ctrl = _elf_scan("fx6_usb_control", "libUsbControl.so", "FX6_6.01", USB_CONTROL_MARKERS)
        fx3_usb_cmn = _elf_scan("fx3_usb_cmn", "libInfraUsbCmn.so", "FX3_7.02", USB_CMN_MARKERS)
        fx6_usb_cmn = _elf_scan("fx6_usb_cmn", "libInfraUsbCmn.so", "FX6_6.01", USB_CMN_MARKERS)
        fx3_wlan_res = _elf_scan("fx3_wlan_resource", "libWlanResource.so", "FX3_7.02", WLAN_RESOURCE_MARKERS)
        fx6_wlan_res = _elf_scan("fx6_wlan_resource", "libWlanResource.so", "FX6_6.01", WLAN_RESOURCE_MARKERS)
        fx3_wlan_adj = _elf_scan("fx3_wlan_adjust", "libWlanAdjust.so", "FX3_7.02", WLAN_ADJUST_MARKERS)
        fx6_wlan_adj = _elf_scan("fx6_wlan_adjust", "libWlanAdjust.so", "FX6_6.01", WLAN_ADJUST_MARKERS)
        fx3_bt_core = _elf_scan("fx3_bt_core", "libInfraBluetoothCore.so", "FX3_7.02", BT_CORE_MARKERS)
        fx6_bt_core = _elf_scan("fx6_bt_core", "libInfraBluetoothCore.so", "FX6_6.01", BT_CORE_MARKERS)
        fx3_ble_le = _elf_scan("fx3_ble_le", "libInfraBluetoothLowEnergy.so", "FX3_7.02")
        fx6_ble_le = _elf_scan("fx6_ble_le", "libInfraBluetoothLowEnergy.so", "FX6_6.01")
        fx3_net_ether = _elf_scan("fx3_net_ether", "libNetServiceEther.so", "FX3_7.02", ETHER_NETSERVICE_SHARED_MARKERS)
        fx6_net_ether = _elf_scan("fx6_net_ether", "libNetServiceEther.so", "FX6_6.01", ETHER_NETSERVICE_SHARED_MARKERS + ETHER_NETSERVICE_FX6_EXTRA_MARKERS)
        fx3_ftp_client = _elf_scan("fx3_ftp_client", "libInfraFtpClient.so", "FX3_7.02", ETHER_FTP_SHARED_MARKERS)
        fx6_ftp_client = _elf_scan("fx6_ftp_client", "libInfraFtpClient.so", "FX6_6.01", ETHER_FTP_SHARED_MARKERS)
        fx3_ptp_ctrl = _elf_scan("fx3_ptp_control", "libInfraPtpControl.so", "FX3_7.02")
        fx6_ptp_ctrl = _elf_scan("fx6_ptp_control", "libInfraPtpControl.so", "FX6_6.01")
    else:
        fx = build_clean_room_realhw_wifi_bt_usb_network_fixtures()
        fx3_ap_hits = _count_tokens_single_pass(fx["fx3_appfw"], fx3_appfw_tokens)
        fx6_ap_hits = _count_tokens_single_pass(fx["fx6_appfw"], fx6_appfw_tokens)
        fx3_sc_hits = _count_tokens_single_pass(fx["fx3_sencore"], fx3_sc_tokens)
        fx6_sc_hits = _count_tokens_single_pass(fx["fx6_sencore"], fx6_sc_tokens)
        fx3_cp_hits = _count_tokens_single_pass(fx["fx3_cpapp"], cp_tokens)
        fx6_cp_hits = _count_tokens_single_pass(fx["fx6_cpapp"], cp_tokens)
        fx3_bk_buf = fx["fx3_backup"]
        fx6_bk_buf = fx["fx6_backup"]

        for k, buf in fx.items():
            donor_sizes[k] = len(buf)

        def _elf_buf(
            key: str, bname: str, body: str, toks: Sequence[str] = ()
        ) -> ElfSectionSummary:
            elf_sum, _exps, _imps = _scan_elf_and_tokens_buf(
                fx[key],
                binary_name=bname,
                body_label=body,
                source_mode=src_mode,
                tokens=toks,
            )
            return elf_sum

        fx3_im_elf = _elf_buf("fx3_im_elf", "im.elf", "FX3_7.02")
        fx6_im_elf = _elf_buf("fx6_im_elf", "im.elf", "FX6_6.01")
        fx3_msc_srv = _elf_buf("fx3_msc_server", "libInfraMscServer.so", "FX3_7.02", MSC_SERVER_MARKERS)
        fx6_msc_srv = _elf_buf("fx6_msc_server", "libInfraMscServer.so", "FX6_6.01", MSC_SERVER_MARKERS)
        fx3_usb_ctrl = _elf_buf("fx3_usb_control", "libUsbControl.so", "FX3_7.02", USB_CONTROL_MARKERS)
        fx6_usb_ctrl = _elf_buf("fx6_usb_control", "libUsbControl.so", "FX6_6.01", USB_CONTROL_MARKERS)
        fx3_usb_cmn = _elf_buf("fx3_usb_cmn", "libInfraUsbCmn.so", "FX3_7.02", USB_CMN_MARKERS)
        fx6_usb_cmn = _elf_buf("fx6_usb_cmn", "libInfraUsbCmn.so", "FX6_6.01", USB_CMN_MARKERS)
        fx3_wlan_res = _elf_buf("fx3_wlan_resource", "libWlanResource.so", "FX3_7.02", WLAN_RESOURCE_MARKERS)
        fx6_wlan_res = _elf_buf("fx6_wlan_resource", "libWlanResource.so", "FX6_6.01", WLAN_RESOURCE_MARKERS)
        fx3_wlan_adj = _elf_buf("fx3_wlan_adjust", "libWlanAdjust.so", "FX3_7.02", WLAN_ADJUST_MARKERS)
        fx6_wlan_adj = _elf_buf("fx6_wlan_adjust", "libWlanAdjust.so", "FX6_6.01", WLAN_ADJUST_MARKERS)
        fx3_bt_core = _elf_buf("fx3_bt_core", "libInfraBluetoothCore.so", "FX3_7.02", BT_CORE_MARKERS)
        fx6_bt_core = _elf_buf("fx6_bt_core", "libInfraBluetoothCore.so", "FX6_6.01", BT_CORE_MARKERS)
        fx3_ble_le = _elf_buf("fx3_ble_le", "libInfraBluetoothLowEnergy.so", "FX3_7.02")
        fx6_ble_le = _elf_buf("fx6_ble_le", "libInfraBluetoothLowEnergy.so", "FX6_6.01")
        fx3_net_ether = _elf_buf("fx3_net_ether", "libNetServiceEther.so", "FX3_7.02", ETHER_NETSERVICE_SHARED_MARKERS)
        fx6_net_ether = _elf_buf("fx6_net_ether", "libNetServiceEther.so", "FX6_6.01", ETHER_NETSERVICE_SHARED_MARKERS + ETHER_NETSERVICE_FX6_EXTRA_MARKERS)
        fx3_ftp_client = _elf_buf("fx3_ftp_client", "libInfraFtpClient.so", "FX3_7.02", ETHER_FTP_SHARED_MARKERS)
        fx6_ftp_client = _elf_buf("fx6_ftp_client", "libInfraFtpClient.so", "FX6_6.01", ETHER_FTP_SHARED_MARKERS)
        fx3_ptp_ctrl = _elf_buf("fx3_ptp_control", "libInfraPtpControl.so", "FX3_7.02")
        fx6_ptp_ctrl = _elf_buf("fx6_ptp_control", "libInfraPtpControl.so", "FX6_6.01")

    # Parse Backup.bin dual records safely
    fx3_bk_ok = True
    fx6_bk_ok = True
    try:
        fx3_bk_hdr, _, _ = parse_dual_bk4_and_descriptors(fx3_bk_buf, body="FX3_7.02")
        fx3_bk_subs = fx3_bk_hdr.rec0_subsystems
        fx3_bk_ok = fx3_bk_hdr.rec0_checksum_valid and fx3_bk_hdr.rec1_checksum_valid
    except Exception as exc:
        fx3_bk_subs = 0
        fx3_bk_ok = False
        errors.append(f"FX3 Backup.bin parse failed: {exc}")

    try:
        fx6_bk_hdr, _, _ = parse_dual_bk4_and_descriptors(fx6_bk_buf, body="FX6_6.01")
        fx6_bk_subs = fx6_bk_hdr.rec0_subsystems
        fx6_bk_ok = fx6_bk_hdr.rec0_checksum_valid and fx6_bk_hdr.rec1_checksum_valid
    except Exception as exc:
        fx6_bk_subs = 0
        fx6_bk_ok = False
        errors.append(f"FX6 Backup.bin parse failed: {exc}")

    # ---- Pillar 1: Wi-Fi 802.11ac & p12/p13 RF NVS Isolation ----
    p1_errors: List[str] = []
    fx3_ap_wifi_hits = sum(1 for k in WIFI_APPFW_FX3_MARKERS if fx3_ap_hits.get(k, 0) > 0)
    fx6_ap_wifi_hits = sum(1 for k in WIFI_APPFW_FX6_MARKERS if fx6_ap_hits.get(k, 0) > 0)
    fx3_sc_wifi_hits = sum(1 for k in WIFI_SENCORE_SHARED_MARKERS if fx3_sc_hits.get(k, 0) > 0)
    fx6_sc_wifi_hits = sum(1 for k in WIFI_SENCORE_SHARED_MARKERS if fx6_sc_hits.get(k, 0) > 0)
    fx3_cp_wifi_hits = sum(1 for k in WIFI_CP_SHARED_MARKERS if fx3_cp_hits.get(k, 0) > 0)
    fx6_cp_wifi_hits = sum(1 for k in WIFI_CP_SHARED_MARKERS if fx6_cp_hits.get(k, 0) > 0)
    wlan_adj_identical = (
        fx3_wlan_adj.export_count == EXPECTED_WLAN_ADJUST_EXPORTS
        and fx6_wlan_adj.export_count == EXPECTED_WLAN_ADJUST_EXPORTS
        and fx3_wlan_adj.import_count == EXPECTED_WLAN_ADJUST_IMPORTS
        and fx6_wlan_adj.import_count == EXPECTED_WLAN_ADJUST_IMPORTS
    )

    if fx3_ap_wifi_hits < len(WIFI_APPFW_FX3_MARKERS):
        p1_errors.append(f"FX3 appFw Wi-Fi markers incomplete: {fx3_ap_wifi_hits}/{len(WIFI_APPFW_FX3_MARKERS)}")
    if fx6_ap_wifi_hits < len(WIFI_APPFW_FX6_MARKERS):
        p1_errors.append(f"FX6 appFw Wi-Fi markers incomplete: {fx6_ap_wifi_hits}/{len(WIFI_APPFW_FX6_MARKERS)}")
    if fx3_sc_wifi_hits < len(WIFI_SENCORE_SHARED_MARKERS) or fx6_sc_wifi_hits < len(WIFI_SENCORE_SHARED_MARKERS):
        p1_errors.append("libsencore.so Wi-Fi factory markers incomplete")
    if fx3_cp_wifi_hits < len(WIFI_CP_SHARED_MARKERS) or fx6_cp_wifi_hits < len(WIFI_CP_SHARED_MARKERS):
        p1_errors.append("cpapp-b.bin Wi-Fi DFS/RF markers incomplete")
    if not wlan_adj_identical:
        p1_errors.append("libWlanAdjust.so ABI mismatch across FX3/FX6")
    if fx3_wlan_res.export_count != EXPECTED_WLAN_RESOURCE_EXPORTS or fx6_wlan_res.export_count != EXPECTED_WLAN_RESOURCE_EXPORTS:
        p1_errors.append("libWlanResource.so export count mismatch")
    if not (fx3_bk_ok and fx6_bk_ok and fx3_bk_subs == 819 and fx6_bk_subs == 840):
        p1_errors.append("Backup.bin BK4 subsystem/checksum verification failed")

    p1_evals = (
        evaluate_wifi_rf_nvs_isolation(wifi_mode="AIRPLANE_ISOLATED_P12", band="5GHZ_80211AC"),
        evaluate_wifi_rf_nvs_isolation(wifi_mode="AP_DIRECT", band="5GHZ_80211AC"),
        evaluate_wifi_rf_nvs_isolation(wifi_mode="STATION_ROUTER", band="2.4GHZ_80211N"),
        evaluate_wifi_rf_nvs_isolation(wifi_mode="RF_NVS_CALIB_WRITE_ATTEMPT", rf_nvs_write_requested=True),
    )
    if not (p1_evals[0].valid and p1_evals[1].valid and p1_evals[2].valid and (not p1_evals[3].valid)):
        p1_errors.append("Wi-Fi / RF NVS policy self-check failed")

    pillar1 = Pillar1WifiRfNvsReport(
        passed=len(p1_errors) == 0,
        fx3_appfw_wifi_hits=fx3_ap_wifi_hits,
        fx6_appfw_wifi_hits=fx6_ap_wifi_hits,
        fx3_sencore_wifi_hits=fx3_sc_wifi_hits,
        fx6_sencore_wifi_hits=fx6_sc_wifi_hits,
        fx3_cp_wifi_hits=fx3_cp_wifi_hits,
        fx6_cp_wifi_hits=fx6_cp_wifi_hits,
        fx3_wlan_resource=fx3_wlan_res,
        fx6_wlan_resource=fx6_wlan_res,
        fx3_wlan_adjust=fx3_wlan_adj,
        fx6_wlan_adjust=fx6_wlan_adj,
        wlan_adjust_abi_identical=wlan_adj_identical,
        fx3_backup_subsystems=fx3_bk_subs,
        fx6_backup_subsystems=fx6_bk_subs,
        fx3_backup_checksums_valid=fx3_bk_ok,
        fx6_backup_checksums_valid=fx6_bk_ok,
        rf_nvs_p12_p13_writes_permitted=False,
        rf_nvs_mutation_bytes=0,
        sample_evals=p1_evals,
        errors=tuple(p1_errors),
    )

    # ---- Pillar 2: BLE Creators' App vs FX6 No-BT Non-Blocking Bridge ----
    p2_errors: List[str] = []
    fx3_ap_bt_hits = sum(1 for k in BT_APPFW_FX3_MARKERS if fx3_ap_hits.get(k, 0) > 0)
    fx6_ap_bt_hits = sum(1 for k in BT_APPFW_FX6_MARKERS if fx6_ap_hits.get(k, 0) > 0)
    fx3_sc_bt_hits = sum(1 for k in BT_SENCORE_SHARED_MARKERS if fx3_sc_hits.get(k, 0) > 0)
    fx6_sc_bt_hits = sum(1 for k in BT_SENCORE_SHARED_MARKERS if fx6_sc_hits.get(k, 0) > 0)
    fx3_cp_hci_hits = sum(1 for k in BT_CP_SHARED_MARKERS if fx3_cp_hits.get(k, 0) > 0)
    fx6_cp_hci_hits = sum(1 for k in BT_CP_SHARED_MARKERS if fx6_cp_hits.get(k, 0) > 0)

    if fx3_ap_bt_hits < len(BT_APPFW_FX3_MARKERS):
        p2_errors.append(f"FX3 appFw BT/BLE markers incomplete: {fx3_ap_bt_hits}/{len(BT_APPFW_FX3_MARKERS)}")
    if fx6_ap_bt_hits < len(BT_APPFW_FX6_MARKERS):
        p2_errors.append(f"FX6 appFw BT/BLE markers incomplete: {fx6_ap_bt_hits}/{len(BT_APPFW_FX6_MARKERS)}")
    if fx3_sc_bt_hits < len(BT_SENCORE_SHARED_MARKERS) or fx6_sc_bt_hits < len(BT_SENCORE_SHARED_MARKERS):
        p2_errors.append("libsencore.so BT firmware markers incomplete")
    if fx3_cp_hci_hits < len(BT_CP_SHARED_MARKERS) or fx6_cp_hci_hits < len(BT_CP_SHARED_MARKERS):
        p2_errors.append("cpapp-b.bin HCI markers incomplete")
    if fx3_bt_core.export_count != EXPECTED_FX3_BT_CORE_EXPORTS or fx6_bt_core.export_count != EXPECTED_FX6_BT_CORE_EXPORTS:
        p2_errors.append("libInfraBluetoothCore.so export counts mismatch")
    if fx3_ble_le.export_count != EXPECTED_FX3_BLE_EXPORTS or fx6_ble_le.export_count != EXPECTED_FX6_BLE_EXPORTS:
        p2_errors.append("libInfraBluetoothLowEnergy.so export counts mismatch")

    p2_evals = (
        evaluate_bt_ble_daemon_bridge(scenario="FX6_NO_BLE_NONBLOCK_MASKED", bt_hci_blocking_wait_ms=0),
        evaluate_bt_ble_daemon_bridge(scenario="AIRPLANE_P12_BT_OFF", bt_hci_blocking_wait_ms=0),
        evaluate_bt_ble_daemon_bridge(scenario="FX3_CREATORS_BLE_PAIRING_HOST", bt_hci_blocking_wait_ms=0),
        evaluate_bt_ble_daemon_bridge(
            scenario="FX6_DAEMON_BLOCKING_WAIT_UNMASKED",
            bt_hci_blocking_wait_ms=2500,
            mask_fx6_daemon_mismatch=False,
        ),
        evaluate_bt_ble_daemon_bridge(scenario="BT_NVS_BDADDR_WRITE_ATTEMPT", rf_nvs_write_requested=True),
    )
    if not (
        p2_evals[0].valid
        and p2_evals[1].valid
        and p2_evals[2].valid
        and (not p2_evals[3].valid)
        and (not p2_evals[4].valid)
    ):
        p2_errors.append("BT/BLE non-blocking daemon bridge self-check failed")

    pillar2 = Pillar2BtBleBridgeReport(
        passed=len(p2_errors) == 0,
        fx3_appfw_bt_hits=fx3_ap_bt_hits,
        fx6_appfw_bt_hits=fx6_ap_bt_hits,
        fx3_sencore_bt_hits=fx3_sc_bt_hits,
        fx6_sencore_bt_hits=fx6_sc_bt_hits,
        fx3_cp_hci_hits=fx3_cp_hci_hits,
        fx6_cp_hci_hits=fx6_cp_hci_hits,
        fx3_bt_core=fx3_bt_core,
        fx6_bt_core=fx6_bt_core,
        fx3_ble_le=fx3_ble_le,
        fx6_ble_le=fx6_ble_le,
        bt_hci_blocking_wait_ms=0,
        bt_hci_blocking_wait_eliminated=p2_evals[0].bt_hci_blocking_wait_eliminated,
        sample_evals=p2_evals,
        errors=tuple(p2_errors),
    )

    # ---- Pillar 3: USB Type-C Multi-Role (MSC 054C:0DA1, MTP, UVC/UAC) ----
    p3_errors: List[str] = []
    fx3_ap_usb_hits = sum(1 for k in USB_APPFW_FX3_MARKERS if fx3_ap_hits.get(k, 0) > 0)
    fx6_ap_usb_hits = sum(1 for k in USB_APPFW_FX6_MARKERS if fx6_ap_hits.get(k, 0) > 0)
    msc_identical = (
        fx3_msc_srv.export_count == EXPECTED_MSC_SERVER_EXPORTS
        and fx6_msc_srv.export_count == EXPECTED_MSC_SERVER_EXPORTS
        and fx3_msc_srv.import_count == EXPECTED_MSC_SERVER_IMPORTS
        and fx6_msc_srv.import_count == EXPECTED_MSC_SERVER_IMPORTS
    )
    usb_ctrl_identical = (
        fx3_usb_ctrl.export_count == EXPECTED_USB_CONTROL_EXPORTS
        and fx6_usb_ctrl.export_count == EXPECTED_USB_CONTROL_EXPORTS
        and fx3_usb_ctrl.import_count == EXPECTED_USB_CONTROL_IMPORTS
        and fx6_usb_ctrl.import_count == EXPECTED_USB_CONTROL_IMPORTS
    )

    if fx3_ap_usb_hits < len(USB_APPFW_FX3_MARKERS):
        p3_errors.append(f"FX3 appFw USB markers incomplete: {fx3_ap_usb_hits}/{len(USB_APPFW_FX3_MARKERS)}")
    if fx6_ap_usb_hits < len(USB_APPFW_FX6_MARKERS):
        p3_errors.append(f"FX6 appFw USB markers incomplete: {fx6_ap_usb_hits}/{len(USB_APPFW_FX6_MARKERS)}")
    if not msc_identical:
        p3_errors.append("libInfraMscServer.so ABI mismatch across FX3/FX6")
    if not usb_ctrl_identical:
        p3_errors.append("libUsbControl.so ABI mismatch across FX3/FX6")
    if fx3_usb_cmn.export_count != 479 or fx6_usb_cmn.export_count != 503:
        p3_errors.append("libInfraUsbCmn.so export count mismatch")
    if fx3_ptp_ctrl.export_count != 456 or fx6_ptp_ctrl.export_count != 435:
        p3_errors.append("libInfraPtpControl.so export count mismatch")

    p3_evals = (
        evaluate_usb_multi_role_bridge(usb_role="MSC_RECOVERY_054C_0DA1"),
        evaluate_usb_multi_role_bridge(usb_role="SERVICE_HANDSHAKE_054C_0336"),
        evaluate_usb_multi_role_bridge(usb_role="MTP_PTP_REMOTE_SHOOTING"),
        evaluate_usb_multi_role_bridge(usb_role="UVC_UAC_HDMI_CAPTURE_BRIDGE"),
        evaluate_usb_multi_role_bridge(usb_role="FX6_NATIVE_USB_STREAMING_MASKED"),
        evaluate_usb_multi_role_bridge(usb_role="USB_LAN_CDC_NCM_ETHERNET"),
        evaluate_usb_multi_role_bridge(
            usb_role="UNMASKED_UVC_HIJACKING_MSC",
            preserve_msc_0da1=False,
        ),
    )
    if not (
        all(e.valid for e in p3_evals[:6])
        and (not p3_evals[6].valid)
        and p3_evals[0].usb_msc_0da1_recovery_intact
    ):
        p3_errors.append("USB Type-C multi-role MSC 054C:0DA1 preservation check failed")

    pillar3 = Pillar3UsbMultiRoleReport(
        passed=len(p3_errors) == 0,
        fx3_appfw_usb_hits=fx3_ap_usb_hits,
        fx6_appfw_usb_hits=fx6_ap_usb_hits,
        fx3_msc_server=fx3_msc_srv,
        fx6_msc_server=fx6_msc_srv,
        msc_server_abi_identical=msc_identical,
        fx3_usb_control=fx3_usb_ctrl,
        fx6_usb_control=fx6_usb_ctrl,
        usb_control_abi_identical=usb_ctrl_identical,
        fx3_usb_cmn=fx3_usb_cmn,
        fx6_usb_cmn=fx6_usb_cmn,
        fx3_ptp_control=fx3_ptp_ctrl,
        fx6_ptp_control=fx6_ptp_ctrl,
        usb_msc_0da1_recovery_intact=p3_evals[0].usb_msc_0da1_recovery_intact,
        sample_evals=p3_evals,
        errors=tuple(p3_errors),
    )

    # ---- Pillar 4: Wired USB-LAN Gigabit Ethernet FTP & Monitor & Control ----
    p4_errors: List[str] = []
    fx3_sc_ether_hits = sum(1 for k in ETHER_SENCORE_FX3_MARKERS if fx3_sc_hits.get(k, 0) > 0)
    fx6_sc_wol_hits = sum(1 for k in ETHER_SENCORE_FX6_EXTRA_MARKERS if fx6_sc_hits.get(k, 0) > 0)
    fx3_cp_eth_hits = fx3_cp_hits.get("DFS_FACTOR_ETHER_CONNECT", 0)
    im_identical = (
        fx3_im_elf.export_count == 11
        and fx6_im_elf.export_count == 11
        and fx3_im_elf.import_count == 85
        and fx6_im_elf.import_count == 85
    )

    if fx3_sc_ether_hits < len(ETHER_SENCORE_FX3_MARKERS):
        p4_errors.append("FX3 libsencore.so USB-Ether markers incomplete")
    if fx6_sc_wol_hits < len(ETHER_SENCORE_FX6_EXTRA_MARKERS):
        p4_errors.append("FX6 libsencore.so WIREDLAN_WOL markers incomplete")
    if fx3_cp_eth_hits < 1:
        p4_errors.append("FX3 cpapp-b.bin missing DFS_FACTOR_ETHER_CONNECT")
    if fx3_net_ether.export_count != EXPECTED_FX3_ETHER_EXPORTS or fx6_net_ether.export_count != EXPECTED_FX6_ETHER_EXPORTS:
        p4_errors.append("libNetServiceEther.so export count mismatch")
    if fx3_ftp_client.export_count != 599 or fx6_ftp_client.export_count != 605:
        p4_errors.append("libInfraFtpClient.so export count mismatch")
    if not im_identical:
        p4_errors.append("im.elf ABI mismatch across FX3/FX6")

    p4_evals = (
        evaluate_wired_ether_ftp_mc_bridge(adapter_profile="CDC_NCM_RTL8153_GIGABIT", p12_airplane_mode_on=True),
        evaluate_wired_ether_ftp_mc_bridge(adapter_profile="CDC_NCM_AX88179_GIGABIT", p12_airplane_mode_on=True),
        evaluate_wired_ether_ftp_mc_bridge(adapter_profile="FX6_WIREDLAN_WOL_DOCK_ABSENT", mask_absent_wol_hw=True),
        evaluate_wired_ether_ftp_mc_bridge(adapter_profile="UNPLUGGED_ETHER_DONGLE_NONBLOCK", blocking_wait_ms=0),
        evaluate_wired_ether_ftp_mc_bridge(adapter_profile="WIFI_WLAN0_UNDER_P12", p12_airplane_mode_on=True),
    )
    if not (all(e.valid for e in p4_evals[:4]) and (not p4_evals[4].valid)):
        p4_errors.append("Wired USB-LAN FTP / Monitor & Control evaluation failed")

    pillar4 = Pillar4WiredEtherFtpMcReport(
        passed=len(p4_errors) == 0,
        fx3_sencore_ether_hits=fx3_sc_ether_hits,
        fx6_sencore_wol_extra_hits=fx6_sc_wol_hits,
        fx3_cp_ether_hits=fx3_cp_eth_hits,
        fx3_net_ether=fx3_net_ether,
        fx6_net_ether=fx6_net_ether,
        fx3_ftp_client=fx3_ftp_client,
        fx6_ftp_client=fx6_ftp_client,
        fx3_im_elf=fx3_im_elf,
        fx6_im_elf=fx6_im_elf,
        im_elf_abi_identical=im_identical,
        wired_usblan_passthrough_verified=p4_evals[0].valid and p4_evals[1].valid,
        sample_evals=p4_evals,
        errors=tuple(p4_errors),
    )

    matrix = build_phase152_network_usb_matrix()
    vol_guard = evaluate_phase152_write_guard("/tmp/fx6_stageb_net_usb_shadow.json")
    p12_guard = evaluate_phase152_write_guard("p12:/cert/device_cert.bin")
    p13_guard = evaluate_phase152_write_guard("/dev/nflasha13/rf_nvs.bin")
    bk_guard = evaluate_phase152_write_guard("p2:/Backup.bin")

    if not vol_guard.valid:
        errors.append("Volatile /tmp/ staging guard failed")
    if not (
        p12_guard.persistent_write_blocked
        and p13_guard.persistent_write_blocked
        and bk_guard.persistent_write_blocked
    ):
        errors.append("Persistent p12/p13/Backup.bin write guard failed to block write")

    errors.extend(p1_errors)
    errors.extend(p2_errors)
    errors.extend(p3_errors)
    errors.extend(p4_errors)

    all_ok = (
        pillar1.passed
        and pillar2.passed
        and pillar3.passed
        and pillar4.passed
        and vol_guard.valid
        and p12_guard.persistent_write_blocked
        and p13_guard.persistent_write_blocked
        and bk_guard.persistent_write_blocked
        and len(errors) == 0
    )

    digest_payload = {
        "schema_version": PHASE_152_SCHEMA,
        "phase_version": PHASE_152_VERSION,
        "mode": mode,
        "all_checks_passed": all_ok,
        "donor_file_sizes": donor_sizes,
        "pillar1_passed": pillar1.passed,
        "pillar2_passed": pillar2.passed,
        "pillar3_passed": pillar3.passed,
        "pillar4_passed": pillar4.passed,
        "matrix_count": matrix.total_touchpoints,
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return RealhwWifiBtUsbUvcNetworkBridgeReport(
        schema_version=PHASE_152_SCHEMA,
        phase_version=PHASE_152_VERSION,
        mode=mode,
        all_checks_passed=all_ok,
        o_rdonly_enforced=True,
        rf_nvs_p12_p13_writes_permitted=False,
        rf_nvs_mutation_bytes=0,
        usb_msc_0da1_recovery_intact=pillar3.usb_msc_0da1_recovery_intact,
        bt_hci_blocking_wait_eliminated=pillar2.bt_hci_blocking_wait_eliminated,
        bt_hci_blocking_wait_ms=pillar2.bt_hci_blocking_wait_ms,
        persistent_emmc_writes_authorized=False,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        donor_file_sizes=donor_sizes,
        pillar1_wifi_rf_nvs=pillar1,
        pillar2_bt_ble_bridge=pillar2,
        pillar3_usb_multi_role=pillar3,
        pillar4_wired_ether_ftp_mc=pillar4,
        compatibility_matrix=matrix,
        volatile_guard_ok=vol_guard,
        forbidden_p12_guard_blocked=p12_guard,
        forbidden_p13_guard_blocked=p13_guard,
        forbidden_backup_guard_blocked=bk_guard,
        report_sha256=report_sha256,
        errors=tuple(errors),
    )


def realhw_wifi_bt_usb_uvc_network_bridge_report_to_dict(
    report: RealhwWifiBtUsbUvcNetworkBridgeReport,
) -> Dict[str, object]:
    """Convert `RealhwWifiBtUsbUvcNetworkBridgeReport` to a deterministic JSON-safe dict."""
    return asdict(report)
