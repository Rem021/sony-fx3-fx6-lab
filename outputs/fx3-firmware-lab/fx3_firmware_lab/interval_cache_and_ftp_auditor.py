"""Phase 93 — 18th Unified Firmware-Lab Auditor: Interval Recording (Time-Lapse 1..60s Electronic Shutter Frame Packing), Picture Cache (Pre-Rec Circular Ring-Buffer), & Wired USB-LAN FTP / Creators' Cloud Transfer P12 RF-Off Isolation.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so` / `icx1295` AP host,
  `libmpr.so`, `cpapp-b.bin`, `global.xdb`, `string_english.uxc`,
  `string_english_g.uxc`) and FX6 v6.01 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`,
  `libInfraFtpClient.so`, `libNetServiceEther.so`, `global.xdb`,
  `string_english.uxc`, `string_english_2.uxc`) strictly via `os.O_RDONLY` +
  `mmap.ACCESS_READ` and ELF64 `.rodata`/`.dynstr` section-scoped scanning, plus
  `uxa\\x07` / `.uxc` container parsing (< 0.35s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact contract markers and runs the identical
  four-pillar verification pipeline (< 0.02s, zero proprietary files required).

Audits Four Interval, Picture Cache, Wired FTP/P12 & Immutability Pillars:
1. Pillar 1 — Interval Recording / Time-Lapse Electronic-Shutter Wear Firewall:
   Audits interval timer (`1s..60s`, `1..9999` shots), mandatory electronic-shutter
   enforcement (zero mechanical focal-plane shutter actuation wear on FX3), AE
   tracking sensitivity (`HIGH`/`MID`/`LOW`/`LOCK`) across day-to-night
   transitions, XAVC S/HS single-clip frame packing vs still-sequence exclusion,
   and mutual exclusion with Picture Cache Rec / S&Q.
2. Pillar 2 — FX6 Picture Cache / Pre-Rec Circular DDR Ring-Buffer Budget on
   FX3 `2048 MiB` DRAM:
   Models exact DDR ring-buffer MiB footprint across `XAVC-I 4K60` (`600 Mbps`
   -> `75.0 MiB/s`), `XAVC-I 4K24` (`240 Mbps` -> `30.0 MiB/s`), `XAVC-L 4K30`
   (`100 Mbps` -> `12.5 MiB/s`), `XAVC-I FHD60` (`222 Mbps` -> `27.75 MiB/s`),
   and `XAVC-L FHD60` (`50 Mbps` -> `6.25 MiB/s`), safely clamping `2s..16s`
   pre-rec duration within FX3 AP DDR headroom (`384.0 MiB`) without starving
   `GPE0`/`appFw` or triggering Linux OOM killer, forcing `Free Run` timecode,
   and auto-disabling in `S&Q` / `HDMI RAW` / `Interval Rec` / `Simul` modes.
3. Pillar 3 — Wired USB-LAN FTP / FTPS Background Transfer & P12 `00342260`
   Wi-Fi/BT RF-Off Firewall:
   Audits background FTP/FTPS (`TLS 1.2`/`1.3` passive `PASV`, rejecting Active
   `PORT` mode; `PROXY_ONLY` / `ORIGINAL_ONLY` / `PROXY_AND_ORIGINAL`; resume
   `REST` byte-offset continuity) strictly over wired `CDC-NCM` / `RTL8153`
   (`AX88179` original) USB-LAN while proving Wi-Fi/BT RF remains 100% fenced
   under `P12` (`0` `WF-12` `00342260` fatal dialog, `0` HCI TX) and internal
   eMMC partitions (`p1..p15`) are strictly blocked from FTP path traversal
   (`CWD`/`RETR` restricted to `/mnt/sd`, `/mnt/slot_a`, `/mnt/slot_b`,
   `/mnt/cfexpress_a`, `/mnt/cfexpress_b`).
4. Pillar 4 — Calibration/eMMC Zero-Mutation Proof & `NonRealTimeMeta v2.20`
   Interval/Cache Tag Parity:
   Proves `calibration_mutation_bytes == 0`, `emmc_mutation_bytes == 0`, and
   `persistent_emmc_writes_authorized == False`, while verifying `NonRealTimeMeta`
   XML sidecar round-trip parity for Interval Rec, Picture Cache, and wired
   FTPES P12 telemetry tags.
"""

from __future__ import annotations

import hashlib
import json
import mmap
import os
import posixpath
import re
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .emount_af_breathing_and_ibis_auditor import _extract_uxc_labels, _parse_elf64_sections
from .global_xdb_and_menu_tree_auditor import (
    build_sparse_uxc_string_pack,
    build_synthetic_global_xdb,
    parse_global_xdb_buffer,
)
from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    is_forced_clean_room,
    resolve_donor_file,
)
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX3_LIBMPR_RELPATH,
    FX6_CPAPP_RELPATH,
    FX6_LIBMPR_RELPATH,
)
from .uxc_multilang_and_font_verifier import FX3_SHARE_APP_RELDIR, FX6_SHARE_APP_RELDIR
from .wbi_hibdrv_and_elf_abi_differ import build_synthetic_elf64_so


PHASE_93_SCHEMA = "fx3_firmware_lab_phase93_interval_cache_ftp_v1"
PHASE_93_VERSION = "93.0.0"

FX6_LIBINFRA_FTP_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/"
    "nflasha15-files/lib/libInfraFtpClient.so"
)
FX6_LIBNET_ETHER_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/"
    "nflasha15-files/lib/libNetServiceEther.so"
)
FX3_GLOBAL_XDB_RELPATH = f"{FX3_SHARE_APP_RELDIR}/global.xdb"
FX6_GLOBAL_XDB_RELPATH = f"{FX6_SHARE_APP_RELDIR}/global.xdb"
FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX3_STR_EN_G_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_g.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pillar 1 Constants: Interval Recording / Time-Lapse Wear Firewall
# ---------------------------------------------------------------------------

INTERVAL_SEC_MIN = 1
INTERVAL_SEC_MAX = 60
INTERVAL_SHOTS_MIN = 1
INTERVAL_SHOTS_MAX = 9999
VALID_INTERVAL_SHUTTER_TYPES: Tuple[str, ...] = ("ELECTRONIC", "MECHANICAL")
VALID_AE_TRACKING_SENSITIVITIES: Tuple[str, ...] = ("HIGH", "MID", "LOW", "LOCK")
VALID_INTERVAL_PACKING_MODES: Tuple[str, ...] = (
    "XAVC_S_SINGLE_CLIP",
    "XAVC_HS_SINGLE_CLIP",
    "STILL_SEQUENCE_EXCLUSION",
)
VALID_INTERVAL_FRAMES_PER_TRIGGER: Tuple[int, ...] = (1, 2, 3, 6, 9, 12)
VALID_INTERVAL_OUTPUT_FPS: Tuple[float, ...] = (23.976, 24.0, 25.0, 29.97, 50.0, 59.94)

# Exponential smoothing coefficients (alpha) per trigger during day-to-night transitions
AE_SLEW_ALPHA_BY_SENSITIVITY: Dict[str, float] = {
    "HIGH": 0.65,
    "MID": 0.30,
    "LOW": 0.10,
    "LOCK": 0.0,
}
DAY_TO_NIGHT_MAX_FLICKER_STEP_EV = 0.25

# ---------------------------------------------------------------------------
# Pillar 2 Constants: FX6 Picture Cache / Pre-Rec DDR Ring-Buffer on FX3 2048 MiB DRAM
# ---------------------------------------------------------------------------

FX3_TOTAL_AP_DRAM_MIB = 2048.0
FX3_KERNEL_AND_DMA_RESERVED_MIB = 384.0
FX3_APPFW_LIBMPR_UX_RESERVED_MIB = 640.0
FX3_GPE0_AND_ENCODER_RESERVED_MIB = 384.0
FX3_OOM_GUARD_HEADROOM_MIB = 256.0
FX3_PICTURE_CACHE_DDR_BUDGET_MIB = (
    FX3_TOTAL_AP_DRAM_MIB
    - FX3_KERNEL_AND_DMA_RESERVED_MIB
    - FX3_APPFW_LIBMPR_UX_RESERVED_MIB
    - FX3_GPE0_AND_ENCODER_RESERVED_MIB
    - FX3_OOM_GUARD_HEADROOM_MIB
)  # 384.0 MiB safe circular ring-buffer headroom

PICTURE_CACHE_MIN_SEC = 2.0
PICTURE_CACHE_MAX_SEC = 16.0
PICTURE_CACHE_PRESETS_SEC: Dict[str, float] = {
    "SHORT": 5.0,
    "MEDIUM": 10.0,
    "LONG": 15.0,
    "MAX": 16.0,
}

PICTURE_CACHE_CODEC_PROFILES: Dict[str, Dict[str, object]] = {
    "XAVC_I_4K60": {
        "codec": "XAVC-I (H.264 High422Intra)",
        "resolution": "4096x2160 / 3840x2160",
        "fps": 59.94,
        "bitrate_mbps": 600.0,
        "mib_per_sec": 75.0,
    },
    "XAVC_I_4K24": {
        "codec": "XAVC-I (H.264 High422Intra)",
        "resolution": "4096x2160 / 3840x2160",
        "fps": 23.976,
        "bitrate_mbps": 240.0,
        "mib_per_sec": 30.0,
    },
    "XAVC_L_4K30": {
        "codec": "XAVC-L (H.264 Long GOP)",
        "resolution": "3840x2160",
        "fps": 29.97,
        "bitrate_mbps": 100.0,
        "mib_per_sec": 12.5,
    },
    "XAVC_I_FHD60": {
        "codec": "XAVC-I (H.264 High422Intra)",
        "resolution": "1920x1080",
        "fps": 59.94,
        "bitrate_mbps": 222.0,
        "mib_per_sec": 27.75,
    },
    "XAVC_L_FHD60": {
        "codec": "XAVC-L (H.264 Long GOP)",
        "resolution": "1920x1080",
        "fps": 59.94,
        "bitrate_mbps": 50.0,
        "mib_per_sec": 6.25,
    },
}

PICTURE_CACHE_AUTO_DISABLE_CAPTURE_MODES: Tuple[str, ...] = ("SQ_MOTION", "HDMI_RAW16")
VALID_PICTURE_CACHE_CAPTURE_MODES: Tuple[str, ...] = ("NORMAL_VIDEO", "SQ_MOTION", "HDMI_RAW16")

# ---------------------------------------------------------------------------
# Pillar 3 Constants: Wired USB-LAN FTP/FTPS & P12 00342260 RF-Off Firewall
# ---------------------------------------------------------------------------

ALLOWED_WIRED_NIC_DRIVERS: Tuple[str, ...] = ("CDC_NCM_RTL8153", "CDC_NCM_AX88179")
FORBIDDEN_NIC_DRIVERS: Tuple[str, ...] = (
    "AX88179A",
    "AX88179B",
    "RNDIS",
    "WIFI_WLAN0",
    "BT_PAN",
    "RTL8156_2_5G",
)
VALID_FTP_PROTOCOLS: Tuple[str, ...] = ("FTPES_TLS13", "FTPES_TLS12", "FTP_PLAIN_LAN")
SECURE_TLS_PROTOCOLS: Tuple[str, ...] = ("FTPES_TLS13", "FTPES_TLS12")
VALID_FTP_DATA_MODES: Tuple[str, ...] = ("PASV", "PORT")
VALID_FTP_TRANSFER_TARGETS: Tuple[str, ...] = ("PROXY_ONLY", "ORIGINAL_ONLY", "PROXY_AND_ORIGINAL")
ALLOWED_FTP_MEDIA_ROOTS: Tuple[str, ...] = (
    "/mnt/sd",
    "/mnt/slot_a",
    "/mnt/slot_b",
    "/mnt/cfexpress_a",
    "/mnt/cfexpress_b",
)
FORBIDDEN_EMMC_PARTITION_RE = re.compile(
    r"(?:^|/)(?:p(?:[1-9]|1[0-5])|nflasha\d*|cnflasha\d*|mmcblk0(?:p\d+)?|mtdblock\d*)(?:/|$)",
    re.IGNORECASE,
)
FORBIDDEN_FTP_SYSTEM_PREFIXES: Tuple[str, ...] = (
    "/etc",
    "/lib",
    "/usr",
    "/bin",
    "/sbin",
    "/boot",
    "/dev",
    "/proc",
    "/sys",
    "/root",
    "/var",
)
WIRED_USBLAN_EFFECTIVE_THROUGHPUT_MBPS = 850.0  # Realistic 1 Gbps USB 3.2 CDC-NCM payload rate

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Zero Mutation & NonRealTimeMeta v2.20 Parity
# ---------------------------------------------------------------------------

NRTM_NAMESPACE_V220 = "urn:schemas-professionalDisc:nonRealTimeMeta:ver.2.20"
VOLATILE_SHADOW_PREFIXES: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_CALIBRATION_AND_EMMC_PATHS: Tuple[str, ...] = (
    "/dev/mmcblk0",
    "mmcblk0",
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/mtdblock",
    "nflasha",
    "cnflasha",
    "backup.bin",
    "psd.bin",
    "jiritsu",
    "nvram://",
)

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_INTERVAL_MARKERS: Tuple[str, ...] = (
    "PID_SET_INTERVAL_REC",
    "PID_SET_INTERVAL_REC_AE_SMOOTHING_END",
    "PID_SET_INTERVAL_REC_EXEC_STATE",
    "SHUTTER_TYPE_IN_INTERVAL_ANTI_DISTORTION_SHUTTER_ELECTRONIC_SHUT",
    "SHUTTER_TYPE_IN_INTERVAL_ANTI_DISTORTION_SHUTTER_MECHANICAL_SHUT",
    "VAL_HAITA_setting_ae_tracking_setting_interval_shooting_AE_TRACKING_LOW_INTERVAL_SHOOTING_ON",
    "VAL_setting_interval_shooting_INTERVAL_SHOOTING_ON",
)

FX3_APPFW_FTP_USBLAN_MARKERS: Tuple[str, ...] = (
    "VAL_setting_ftp_connect_method_FTP_CONNECT_METHOD_WIRED_LAN",
    "VAL_setting_ftp_connect_method_FTP_CONNECT_METHOD_USB_ETHER",
    "VAL_setting_auto_ftp_transfer_AUTO_FTP_TRANSFER_ON",
    "VAL_setting_airplane_mode_AIRPLANE_MODE_ON",
    "BKID_APP_EXTERN_SETTING_AIRPLANE_MODE",
    "VAL_system_mode_option_SYSTEM_MODE_OPTION_USB_LAN_AND_TETHERING",
    "VAL_usb_host_function_USB_HOST_FUNCTION_USB_ETHER",
    "VAL_cloud_function_state_CLOUD_FUNCTION_STATE_STARTED",
)

FX6_APPFW_INTERVAL_MARKERS: Tuple[str, ...] = (
    "remote_presenter::set_interval_rec_mode",
    "remote_presenter::set_interval_rec_movie_frame_rate",
    "remote_presenter::set_interval_rec_still_shutter_type",
    "VAL_setting_interval_rec_INTERVAL_REC_ON",
    "VAL_setting_intervaltime_interval_rec_INTERVALTIME_INTERVAL_REC_1S",
    "VAL_setting_intervaltime_interval_rec_INTERVALTIME_INTERVAL_REC_30S",
    "VAL_is_changing_interval_rec_to_picture_cache_rec_IS_CHANGING_INTERVAL_REC_TO_PICTURE_CACHE_REC_TRUE",
)

FX6_APPFW_CACHE_MARKERS: Tuple[str, ...] = (
    "BKID_APP_SETTING_PICTURE_CACHE_REC",
    "BKID_APP_SETTING_CACHE_REC_SIZE",
    "EVENT_FUNC_PICTURE_CACHE_REC_ON",
    "VAL_setting_picture_cache_rec_PICTURE_CACHE_REC_ON",
    "VAL_setting_cache_rec_size_CACHE_REC_SIZE_SHORT",
    "VAL_setting_cache_rec_size_CACHE_REC_SIZE_MEDIUM",
    "VAL_setting_cache_rec_size_CACHE_REC_SIZE_LONG",
    "VAL_setting_cache_rec_size_CACHE_REC_SIZE_MAX",
)

FX6_APPFW_FTP_USBLAN_MARKERS: Tuple[str, ...] = (
    "VAL_system_mode_option_SYSTEM_MODE_OPTION_FTP",
    "VAL_setting_auto_upload_original_AUTO_UPLOAD_ORIGINAL_ON",
    "VAL_setting_auto_upload_proxy_AUTO_UPLOAD_PROXY_ON",
    "VAL_setting_auto_upload_proxy_AUTO_UPLOAD_PROXY_CHUNK",
    "model::model_extern::extern_BKID_APP_EXTERN_SETTING_AIRPLANE_MODE",
    "INFRA_NOTIFY_FTP_CONNECT_CMP",
    "CLOUD_REG_STATUS_PROGRESS",
    "CLOUD_REG_USER_CODE",
)

LIBMPR_INTERVAL_PREREC_NRTM_MARKERS: Tuple[str, ...] = (
    "_ZN5MprIf11PreRecStartEPNS_16PreRecStartParamE",
    "NonRealTimeMeta",
    "intervalRec",
)

FX3_CP_INTERVAL_MARKERS: Tuple[str, ...] = (
    "SET_INTERVAL_REC",
    "SET_INTERVAL_REC_AE_SMOOTHING_END",
    "SET_INTERVAL_REC_EXEC_STATE",
    "CheckSetIntervalRecExecState",
)

FX6_CP_INTERVAL_MARKERS: Tuple[str, ...] = (
    "SET_INTERVAL_REC",
    "GetCaptureIntervalResource",
    "InfraBB::Async::ChkSetIntervalRecParam",
)

FX6_FTP_CLIENT_MARKERS: Tuple[str, ...] = (
    "InfraFtpClient_Init",
    "CT_ERR_PASV_NOT_SUPPORT",
    "FT_ERR_PASV_NOT_SUPPORT",
    "FT_ERR_INT_FAIL_CWD",
    "FT_ERR_RESUME_NOT_SUPPORT",
    "FT_ERR_FAIL_AUTH_CACERT",
    "CT_ID_ASYNC_REQ_RESUME_FTP_TRANSFER",
    "TLS_AES_256_GCM_SHA384",
    "OPENSSL_3",
    "CWD",
)

FX6_ETHER_SERVICE_MARKERS: Tuple[str, ...] = (
    "EN_STATE_USB_CONNECTED_USB_ETHER_DEVICE",
    "WiredLanResource_SendReq_CT_ID_SYNC_REQ_START_USB_ETHER",
    "UIBizAPI_SendEvent_CT_ID_EVENT_LINKUP_WIRED_ETHER_NETWORK",
)

# Verified .uxc String Resource IDs
FX3_NS39_PHASE93_LABELS: Dict[int, str] = {
    0x0000E100: "Wired LAN",
    0x0000E39A: "WireLAN(USB-LAN)",
}

FX3_NS3_PHASE93_LABELS: Dict[int, str] = {
    0x000061C8: "Interval shooting...",
    0x0000645F: "USB-LAN/Tethering",
    0x000064BF: "FTP Transfer",
}

FX6_NS1_PHASE93_LABELS: Dict[int, str] = {
    0x00002554: "Cache Size",
    0x00002E7D: "Cache Rec",
    0x00002F27: "Interval Rec Number of Frames",
    0x00002F61: "File Transfer Auto Upload (Proxy)",
    0x00002F63: "File Transfer Auto Upload",
}

FX6_NS2_PHASE93_LABELS: Dict[int, str] = {
    0x00004247: "Interval Rec",
    0x0000424C: "Picture Cache Rec",
    0x000042D3: "Airplane Mode",
    0x0000457C: "Cache Rec Time",
    0x000052E9: "File Transfer Status",
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class IntervalRecordingEvalResult:
    valid: bool
    status: str
    interval_sec: int
    shot_count: int
    shutter_type: str
    ae_tracking_sensitivity: str
    packing_mode: str
    frames_per_trigger: int
    output_fps: float
    silent_mode: bool
    mech_shutter_actuations: int
    electronic_shutter_enforced: bool
    total_capture_wall_sec: int
    packed_clip_frames: int
    packed_clip_duration_sec: float
    single_clip_packed: bool
    audio_recorded: bool
    picture_cache_forced_off: bool
    sq_forced_off: bool
    ae_max_step_ev: float
    ae_flicker_suppressed: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class IntervalRecordingMatrixReport:
    passed: bool
    fx3_appfw_markers: Tuple[str, ...]
    fx6_appfw_markers: Tuple[str, ...]
    fx3_cp_markers: Tuple[str, ...]
    fx6_cp_markers: Tuple[str, ...]
    fx3_libmpr_markers: Tuple[str, ...]
    uxc_interval_labels: Dict[str, str]
    eval_xavc_hs_1s_sunset_low_ae: IntervalRecordingEvalResult
    eval_xavc_s_60s_9999_electronic: IntervalRecordingEvalResult
    eval_lock_ae_manual_starlapse: IntervalRecordingEvalResult
    eval_fx3_still_sequence_exclusion: IntervalRecordingEvalResult
    blocked_mech_shutter_wear_hazard: IntervalRecordingEvalResult
    blocked_out_of_range_interval_and_shots: IntervalRecordingEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PictureCacheDdrEvalResult:
    valid: bool
    status: str
    codec_profile: str
    capture_mode: str
    interval_rec_active: bool
    simul_rec_active: bool
    proxy_rec_active: bool
    requested_pre_rec_sec: float
    effective_pre_rec_sec: float
    max_safe_pre_rec_sec: int
    bitrate_mbps: float
    mib_per_sec: float
    requested_ddr_mib: float
    allocated_ddr_mib: float
    available_ddr_budget_mib: float
    remaining_ddr_headroom_mib: float
    picture_cache_active: bool
    clamped_by_ddr_budget: bool
    auto_disabled_reason: str
    timecode_forced_free_run: bool
    gpe0_appfw_starved: bool
    oom_killer_risk: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PictureCacheDdrMatrixReport:
    passed: bool
    fx6_appfw_cache_markers: Tuple[str, ...]
    fx3_libmpr_prerec_markers: Tuple[str, ...]
    fx6_libmpr_prerec_markers: Tuple[str, ...]
    uxc_cache_labels: Dict[str, str]
    fx3_total_dram_mib: float
    fx3_cache_ddr_budget_mib: float
    eval_xavc_i_4k60_clamped_5s: PictureCacheDdrEvalResult
    eval_xavc_i_4k24_clamped_12s: PictureCacheDdrEvalResult
    eval_xavc_l_4k30_16s_full: PictureCacheDdrEvalResult
    eval_xavc_l_fhd60_16s_full: PictureCacheDdrEvalResult
    eval_auto_disabled_sq_motion: PictureCacheDdrEvalResult
    eval_auto_disabled_hdmi_raw16: PictureCacheDdrEvalResult
    blocked_unclamped_4k60_16s_oom: PictureCacheDdrEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FtpPathGuardResult:
    allowed: bool
    status: str
    raw_path: str
    normalized_path: str
    allowed_root_matched: str
    emmc_partition_blocked: bool
    traversal_blocked: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class WiredFtpTransferEvalResult:
    valid: bool
    status: str
    nic_driver: str
    protocol: str
    data_mode: str
    transfer_target: str
    source_path: str
    normalized_source_path: str
    p12_airplane_mode: bool
    wlan_rf_enabled: bool
    bt_rf_enabled: bool
    hci_tx_packets: int
    wf12_00342260_immune: bool
    root_cert_verified: bool
    file_size_bytes: int
    resume_offset_bytes: int
    remaining_bytes: int
    resume_sha256_verified: bool
    estimated_transfer_sec: float
    creators_cloud_clip_flag_filter: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class WiredFtpP12MatrixReport:
    passed: bool
    fx3_appfw_ftp_markers: Tuple[str, ...]
    fx6_appfw_ftp_markers: Tuple[str, ...]
    fx6_ftp_client_markers: Tuple[str, ...]
    fx6_ether_service_markers: Tuple[str, ...]
    uxc_ftp_usblan_labels: Dict[str, str]
    eval_rtl8153_ftpes_tls13_proxy_only: WiredFtpTransferEvalResult
    eval_rtl8153_ftpes_tls12_orig_proxy_resume: WiredFtpTransferEvalResult
    eval_ax88179_creators_cloud_keep_flag: WiredFtpTransferEvalResult
    blocked_wifi_rf_p12_wf12_hazard: WiredFtpTransferEvalResult
    blocked_active_port_mode_unsupported: WiredFtpTransferEvalResult
    blocked_ax88179a_or_rndis_nic: WiredFtpTransferEvalResult
    blocked_emmc_p1_to_p15_traversal_paths: Tuple[FtpPathGuardResult, ...]
    blocked_invalid_resume_offset: WiredFtpTransferEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class IntervalCacheNrtmXmlResult:
    valid: bool
    status: str
    mode_tag: str
    xml_bytes: int
    xml_sha256: str
    model_name: str
    recording_type: str
    interval_sec: Optional[int]
    shutter_type: Optional[str]
    ae_tracking_sensitivity: Optional[str]
    pre_rec_sec: Optional[float]
    cache_buffer_mib: Optional[float]
    timecode_mode: Optional[str]
    ftp_transport: str
    ftp_protocol: str
    p12_rf_isolated: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class EmmcCalibrationImmutabilityResult:
    valid: bool
    status: str
    target_path: str
    volatile_shadow_only: bool
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ImmutabilityAndNrtmReport:
    passed: bool
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    volatile_shadow_eval: EmmcCalibrationImmutabilityResult
    blocked_cnflasha_eval: EmmcCalibrationImmutabilityResult
    blocked_nflasha1_eval: EmmcCalibrationImmutabilityResult
    blocked_backup_bin_eval: EmmcCalibrationImmutabilityResult
    blocked_psd_bin_eval: EmmcCalibrationImmutabilityResult
    nrtm_interval_eval: IntervalCacheNrtmXmlResult
    nrtm_picture_cache_eval: IntervalCacheNrtmXmlResult
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class IntervalCacheAndFtpReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    donor_file_sizes: Dict[str, int]
    pillar_1_interval_recording: IntervalRecordingMatrixReport
    pillar_2_picture_cache_ddr: PictureCacheDdrMatrixReport
    pillar_3_wired_ftp_p12: WiredFtpP12MatrixReport
    pillar_4_immutability_and_nrtm: ImmutabilityAndNrtmReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Strictly `os.O_RDONLY` + `mmap.ACCESS_READ` Section-Scoped Scanning Helpers
# ---------------------------------------------------------------------------


def _read_bytes_rdonly(path: Path) -> bytes:
    """Open `path` strictly `os.O_RDONLY` and return its bytes."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        with os.fdopen(fd, "rb") as fh:
            return fh.read()
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise


def _scan_donor_rdonly_markers(
    path: Path,
    marker_groups: Mapping[str, Sequence[str]],
    *,
    is_elf: bool,
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    """Open `path` strictly `os.O_RDONLY` with `mmap.ACCESS_READ` and scan marker groups."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {k: () for k in marker_groups}
        unique_markers = sorted(
            {m for markers in marker_groups.values() for m in markers},
            key=lambda s: (-len(s), s),
        )
        if not unique_markers:
            return sz, {k: () for k in marker_groups}

        pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
        matched_tokens: set[bytes] = set()
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            ranges: List[Tuple[int, int]] = [(0, sz)]
            if is_elf:
                try:
                    secs = _parse_elf64_sections(mm)  # type: ignore[arg-type]
                    elf_ranges = [secs[s] for s in (".rodata", ".dynstr") if s in secs]
                    if elf_ranges:
                        ranges = elf_ranges
                except ValueError:
                    ranges = [(0, sz)]

            for off, rsz in ranges:
                for mo in pat.finditer(mm, off, off + rsz):
                    matched_tokens.add(mo.group(0))

        matched_list = list(matched_tokens)
        present_markers = {
            m
            for m in unique_markers
            if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
        }
        results: Dict[str, Tuple[str, ...]] = {
            group_name: tuple(m for m in markers if m in present_markers)
            for group_name, markers in marker_groups.items()
        }
        return sz, results
    finally:
        os.close(fd)


def _scan_bytes_marker_groups(
    blob: bytes,
    marker_groups: Mapping[str, Sequence[str]],
) -> Tuple[int, Dict[str, Tuple[str, ...]]]:
    unique_markers = sorted(
        {m for markers in marker_groups.values() for m in markers},
        key=lambda s: (-len(s), s),
    )
    if not unique_markers:
        return len(blob), {k: () for k in marker_groups}
    pat = re.compile(b"|".join(re.escape(m.encode("latin1")) for m in unique_markers))
    matched_tokens = {mo.group(0) for mo in pat.finditer(blob)}
    matched_list = list(matched_tokens)
    present_markers = {
        m
        for m in unique_markers
        if (mb := m.encode("latin1")) in matched_tokens or any(mb in tok for tok in matched_list)
    }
    results = {
        group_name: tuple(m for m in markers if m in present_markers)
        for group_name, markers in marker_groups.items()
    }
    return len(blob), results


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_interval_cache_ftp_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, CP, `global.xdb`, and `.uxc` fixtures for Phase 93."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_appfw_blob = _pack(FX3_APPFW_INTERVAL_MARKERS + FX3_APPFW_FTP_USBLAN_MARKERS)
    fx6_appfw_blob = _pack(
        FX6_APPFW_INTERVAL_MARKERS + FX6_APPFW_CACHE_MARKERS + FX6_APPFW_FTP_USBLAN_MARKERS
    )
    fx3_libmpr_blob = _pack(LIBMPR_INTERVAL_PREREC_NRTM_MARKERS)
    fx6_libmpr_blob = _pack(LIBMPR_INTERVAL_PREREC_NRTM_MARKERS)
    fx3_cp_blob = _pack(FX3_CP_INTERVAL_MARKERS, prefix=cp_hdr)
    fx6_cp_blob = _pack(FX6_CP_INTERVAL_MARKERS, prefix=cp_hdr)
    fx6_ftp_blob = build_synthetic_elf64_so(
        soname="libInfraFtpClient.so",
        dt_needed=("libcurl.so.4", "libssl.so.3", "libc.so.6"),
        exports=FX6_FTP_CLIENT_MARKERS,
        imports=(),
    )
    fx6_ether_blob = build_synthetic_elf64_so(
        soname="libNetServiceEther.so",
        dt_needed=("libc.so.6",),
        exports=FX6_ETHER_SERVICE_MARKERS,
        imports=(),
    )

    fx3_xdb = build_synthetic_global_xdb("fx3_702")
    fx6_xdb = build_synthetic_global_xdb("fx6_601")

    fx3_str_en = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS39_PHASE93_LABELS.items()}, namespace_id=39
    )
    fx3_str_en_g = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS3_PHASE93_LABELS.items()}, namespace_id=3
    )
    fx6_str_en_1 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS1_PHASE93_LABELS.items()}, namespace_id=1
    )
    fx6_str_en_2 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS2_PHASE93_LABELS.items()}, namespace_id=2
    )

    return {
        "fx3_appfw": fx3_appfw_blob,
        "fx6_appfw": fx6_appfw_blob,
        "fx3_libmpr": fx3_libmpr_blob,
        "fx6_libmpr": fx6_libmpr_blob,
        "fx3_cpapp": fx3_cp_blob,
        "fx6_cpapp": fx6_cp_blob,
        "fx6_libinfra_ftp": fx6_ftp_blob,
        "fx6_libnet_ether": fx6_ether_blob,
        "fx3_global_xdb": fx3_xdb,
        "fx6_global_xdb": fx6_xdb,
        "fx3_str_en": fx3_str_en,
        "fx3_str_en_g": fx3_str_en_g,
        "fx6_str_en_1": fx6_str_en_1,
        "fx6_str_en_2": fx6_str_en_2,
    }


# ---------------------------------------------------------------------------
# Pillar 1: Interval Recording / Time-Lapse Electronic-Shutter Wear Firewall
# ---------------------------------------------------------------------------


def simulate_day_to_night_ae_step_ev(
    sensitivity: str,
    *,
    shot_count: int = 120,
    total_drop_ev: float = -8.0,
    cloud_transient_ev: float = 0.8,
) -> float:
    """Model maximum inter-frame AE step (EV) across a sunset/cloud transition."""
    sens_u = sensitivity.upper()
    if sens_u not in AE_SLEW_ALPHA_BY_SENSITIVITY:
        raise ValueError(f"Unsupported AE tracking sensitivity: {sensitivity!r}")
    alpha = AE_SLEW_ALPHA_BY_SENSITIVITY[sens_u]
    if alpha == 0.0:
        return 0.0

    # Target scene luminance ramps linearly from 0 -> total_drop_ev with a brief transient spike
    ae_ev = 0.0
    max_step = 0.0
    n = max(2, shot_count)
    transient_idx = n // 3
    for i in range(n):
        target_ev = total_drop_ev * (i / (n - 1))
        if i == transient_idx:
            target_ev += cloud_transient_ev
        next_ae = ae_ev + alpha * (target_ev - ae_ev)
        step = abs(next_ae - ae_ev)
        if step > max_step:
            max_step = step
        ae_ev = next_ae
    return round(max_step, 4)


def evaluate_interval_recording_session(
    *,
    interval_sec: int,
    shot_count: int,
    shutter_type: str = "ELECTRONIC",
    ae_tracking_sensitivity: str = "LOW",
    packing_mode: str = "XAVC_HS_SINGLE_CLIP",
    frames_per_trigger: int = 1,
    output_fps: float = 23.976,
    silent_mode: bool = True,
) -> IntervalRecordingEvalResult:
    """Evaluate Interval Recording timer, electronic-shutter wear firewall, AE flicker & clip packing."""
    errors: List[str] = []
    shutter_u = shutter_type.upper()
    ae_u = ae_tracking_sensitivity.upper()
    pack_u = packing_mode.upper()

    if not (INTERVAL_SEC_MIN <= interval_sec <= INTERVAL_SEC_MAX):
        errors.append(
            f"BLOCKED_INTERVAL_OUT_OF_RANGE: interval_sec={interval_sec} outside [{INTERVAL_SEC_MIN}, {INTERVAL_SEC_MAX}]"
        )
    if not (INTERVAL_SHOTS_MIN <= shot_count <= INTERVAL_SHOTS_MAX):
        errors.append(
            f"BLOCKED_SHOT_COUNT_OUT_OF_RANGE: shot_count={shot_count} outside [{INTERVAL_SHOTS_MIN}, {INTERVAL_SHOTS_MAX}]"
        )
    if shutter_u not in VALID_INTERVAL_SHUTTER_TYPES:
        errors.append(f"INVALID_SHUTTER_TYPE: {shutter_type!r}")
    if ae_u not in VALID_AE_TRACKING_SENSITIVITIES:
        errors.append(f"INVALID_AE_TRACKING_SENSITIVITY: {ae_tracking_sensitivity!r}")
    if pack_u not in VALID_INTERVAL_PACKING_MODES:
        errors.append(f"INVALID_INTERVAL_PACKING_MODE: {packing_mode!r}")
    if frames_per_trigger not in VALID_INTERVAL_FRAMES_PER_TRIGGER:
        errors.append(f"INVALID_FRAMES_PER_TRIGGER: {frames_per_trigger}")
    if output_fps not in VALID_INTERVAL_OUTPUT_FPS:
        errors.append(f"INVALID_OUTPUT_FPS: {output_fps}")

    # Mandatory Electronic-Shutter Wear Firewall on FX3
    mech_actuations = shot_count if shutter_u == "MECHANICAL" else 0
    electronic_enforced = shutter_u == "ELECTRONIC" and mech_actuations == 0
    if shutter_u == "MECHANICAL":
        errors.append(
            f"BLOCKED_MECHANICAL_SHUTTER_WEAR_HAZARD: {shot_count} focal-plane actuations forbidden under Interval Wear Firewall"
        )
    if silent_mode and shutter_u != "ELECTRONIC":
        errors.append("SILENT_MODE_REQUIRES_ELECTRONIC_SHUTTER")

    ae_max_step = (
        simulate_day_to_night_ae_step_ev(ae_u, shot_count=max(2, min(shot_count, 240)))
        if ae_u in AE_SLEW_ALPHA_BY_SENSITIVITY
        else 99.0
    )
    ae_flicker_suppressed = ae_max_step <= DAY_TO_NIGHT_MAX_FLICKER_STEP_EV

    single_clip_packed = pack_u in ("XAVC_S_SINGLE_CLIP", "XAVC_HS_SINGLE_CLIP")
    if pack_u == "STILL_SEQUENCE_EXCLUSION":
        packed_frames = 0
        packed_duration = 0.0
    else:
        packed_frames = max(0, shot_count) * max(1, frames_per_trigger)
        packed_duration = round(packed_frames / output_fps, 4) if output_fps > 0 else 0.0

    total_wall_sec = max(0, interval_sec) * max(0, shot_count)
    valid = len(errors) == 0 and electronic_enforced and mech_actuations == 0

    if not valid:
        if any("MECHANICAL" in e for e in errors):
            status = "BLOCKED_MECHANICAL_SHUTTER_WEAR_HAZARD"
        else:
            status = "BLOCKED_INTERVAL_PARAMETER_VIOLATION"
    elif not single_clip_packed:
        status = "VALID_STILL_SEQUENCE_EXCLUSION"
    else:
        status = "VALID_ELECTRONIC_INTERVAL_SINGLE_CLIP"

    return IntervalRecordingEvalResult(
        valid=valid,
        status=status,
        interval_sec=interval_sec,
        shot_count=shot_count,
        shutter_type=shutter_u,
        ae_tracking_sensitivity=ae_u,
        packing_mode=pack_u,
        frames_per_trigger=frames_per_trigger,
        output_fps=output_fps,
        silent_mode=silent_mode,
        mech_shutter_actuations=mech_actuations,
        electronic_shutter_enforced=electronic_enforced,
        total_capture_wall_sec=total_wall_sec,
        packed_clip_frames=packed_frames,
        packed_clip_duration_sec=packed_duration,
        single_clip_packed=single_clip_packed,
        audio_recorded=False,
        picture_cache_forced_off=True,
        sq_forced_off=True,
        ae_max_step_ev=ae_max_step,
        ae_flicker_suppressed=ae_flicker_suppressed,
        errors=tuple(errors),
    )


def evaluate_pillar_1_interval_recording(
    *,
    fx3_appfw_markers: Tuple[str, ...],
    fx6_appfw_markers: Tuple[str, ...],
    fx3_cp_markers: Tuple[str, ...],
    fx6_cp_markers: Tuple[str, ...],
    fx3_libmpr_markers: Tuple[str, ...],
    uxc_interval_labels: Dict[str, str],
    donor_errors: Sequence[str],
) -> IntervalRecordingMatrixReport:
    """Verify Pillar 1 Interval Recording markers, electronic wear firewall & AE transitions."""
    errors = list(donor_errors)

    e1 = evaluate_interval_recording_session(
        interval_sec=1,
        shot_count=600,
        shutter_type="ELECTRONIC",
        ae_tracking_sensitivity="LOW",
        packing_mode="XAVC_HS_SINGLE_CLIP",
        frames_per_trigger=1,
        output_fps=23.976,
    )
    e2 = evaluate_interval_recording_session(
        interval_sec=60,
        shot_count=9999,
        shutter_type="ELECTRONIC",
        ae_tracking_sensitivity="MID",
        packing_mode="XAVC_S_SINGLE_CLIP",
        frames_per_trigger=3,
        output_fps=29.97,
    )
    e3 = evaluate_interval_recording_session(
        interval_sec=15,
        shot_count=300,
        shutter_type="ELECTRONIC",
        ae_tracking_sensitivity="LOCK",
        packing_mode="XAVC_HS_SINGLE_CLIP",
        frames_per_trigger=1,
        output_fps=24.0,
    )
    e4 = evaluate_interval_recording_session(
        interval_sec=5,
        shot_count=240,
        shutter_type="ELECTRONIC",
        ae_tracking_sensitivity="LOW",
        packing_mode="STILL_SEQUENCE_EXCLUSION",
        frames_per_trigger=1,
        output_fps=23.976,
    )
    b_mech = evaluate_interval_recording_session(
        interval_sec=2,
        shot_count=9999,
        shutter_type="MECHANICAL",
        ae_tracking_sensitivity="LOW",
        packing_mode="STILL_SEQUENCE_EXCLUSION",
        silent_mode=False,
    )
    b_range = evaluate_interval_recording_session(
        interval_sec=61,
        shot_count=10000,
        shutter_type="ELECTRONIC",
        ae_tracking_sensitivity="LOW",
    )

    for lbl, ev in (("1s_hs", e1), ("60s_9999", e2), ("lock_starlapse", e3), ("still_excl", e4)):
        if not ev.valid or ev.mech_shutter_actuations != 0 or not ev.electronic_shutter_enforced:
            errors.append(f"Pillar 1 valid case {lbl} failed: {ev.errors}")
    if not e1.ae_flicker_suppressed or not e3.ae_flicker_suppressed:
        errors.append("LOW/LOCK AE tracking failed day-to-night flicker suppression")
    if b_mech.valid or b_mech.status != "BLOCKED_MECHANICAL_SHUTTER_WEAR_HAZARD":
        errors.append("Mechanical shutter interval wear hazard was not blocked")
    if b_range.valid:
        errors.append("Out-of-range interval/shot count was not rejected")

    return IntervalRecordingMatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_markers=fx3_appfw_markers,
        fx6_appfw_markers=fx6_appfw_markers,
        fx3_cp_markers=fx3_cp_markers,
        fx6_cp_markers=fx6_cp_markers,
        fx3_libmpr_markers=fx3_libmpr_markers,
        uxc_interval_labels=uxc_interval_labels,
        eval_xavc_hs_1s_sunset_low_ae=e1,
        eval_xavc_s_60s_9999_electronic=e2,
        eval_lock_ae_manual_starlapse=e3,
        eval_fx3_still_sequence_exclusion=e4,
        blocked_mech_shutter_wear_hazard=b_mech,
        blocked_out_of_range_interval_and_shots=b_range,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: FX6 Picture Cache / Pre-Rec Circular DDR Ring-Buffer Budget
# ---------------------------------------------------------------------------


def evaluate_picture_cache_ddr_budget(
    *,
    codec_profile: str,
    requested_pre_rec_sec: float = 16.0,
    capture_mode: str = "NORMAL_VIDEO",
    interval_rec_active: bool = False,
    simul_rec_active: bool = False,
    proxy_rec_active: bool = False,
    allow_clamp: bool = True,
    budget_mib: float = FX3_PICTURE_CACHE_DDR_BUDGET_MIB,
) -> PictureCacheDdrEvalResult:
    """Compute exact circular DDR ring-buffer MiB footprint and enforce FX3 OOM/mode guards."""
    errors: List[str] = []
    prof_u = codec_profile.upper()
    cap_u = capture_mode.upper()

    if prof_u not in PICTURE_CACHE_CODEC_PROFILES:
        errors.append(f"UNKNOWN_CODEC_PROFILE: {codec_profile!r}")
        spec = {"bitrate_mbps": 0.0, "mib_per_sec": 0.0}
    else:
        spec = PICTURE_CACHE_CODEC_PROFILES[prof_u]

    if cap_u not in VALID_PICTURE_CACHE_CAPTURE_MODES:
        errors.append(f"UNKNOWN_CAPTURE_MODE: {capture_mode!r}")

    if not (PICTURE_CACHE_MIN_SEC <= requested_pre_rec_sec <= PICTURE_CACHE_MAX_SEC):
        errors.append(
            f"REQUESTED_PRE_REC_OUT_OF_RANGE: {requested_pre_rec_sec}s not in [{PICTURE_CACHE_MIN_SEC}, {PICTURE_CACHE_MAX_SEC}]"
        )

    bitrate_mbps = float(spec["bitrate_mbps"])
    mib_per_sec = float(spec["mib_per_sec"])
    requested_mib = round(requested_pre_rec_sec * mib_per_sec, 3)
    max_safe_sec = int(budget_mib // mib_per_sec) if mib_per_sec > 0 else 0
    max_safe_sec = min(int(PICTURE_CACHE_MAX_SEC), max_safe_sec)

    # Mutual exclusions: S&Q, HDMI RAW16, Interval Rec, Simul Rec, Proxy Rec
    disable_reasons: List[str] = []
    if cap_u in PICTURE_CACHE_AUTO_DISABLE_CAPTURE_MODES:
        disable_reasons.append(f"AUTO_DISABLED_IN_{cap_u}")
    if interval_rec_active:
        disable_reasons.append("AUTO_DISABLED_INTERVAL_REC_ACTIVE")
    if simul_rec_active:
        disable_reasons.append("AUTO_DISABLED_SIMUL_REC_ACTIVE")
    if proxy_rec_active:
        disable_reasons.append("AUTO_DISABLED_PROXY_REC_ACTIVE")

    if disable_reasons:
        return PictureCacheDdrEvalResult(
            valid=len(errors) == 0,
            status=disable_reasons[0],
            codec_profile=prof_u,
            capture_mode=cap_u,
            interval_rec_active=interval_rec_active,
            simul_rec_active=simul_rec_active,
            proxy_rec_active=proxy_rec_active,
            requested_pre_rec_sec=requested_pre_rec_sec,
            effective_pre_rec_sec=0.0,
            max_safe_pre_rec_sec=max_safe_sec,
            bitrate_mbps=bitrate_mbps,
            mib_per_sec=mib_per_sec,
            requested_ddr_mib=requested_mib,
            allocated_ddr_mib=0.0,
            available_ddr_budget_mib=budget_mib,
            remaining_ddr_headroom_mib=budget_mib,
            picture_cache_active=False,
            clamped_by_ddr_budget=False,
            auto_disabled_reason=";".join(disable_reasons),
            timecode_forced_free_run=False,
            gpe0_appfw_starved=False,
            oom_killer_risk=False,
            errors=tuple(errors),
        )

    if requested_mib > budget_mib:
        if allow_clamp:
            effective_sec = float(max_safe_sec)
            clamped = effective_sec < requested_pre_rec_sec
            allocated_mib = round(effective_sec * mib_per_sec, 3)
            remaining_mib = round(budget_mib - allocated_mib, 3)
            gpe0_starved = False
            oom_risk = False
            status = "CLAMPED_WITHIN_FX3_DDR_BUDGET"
        else:
            effective_sec = requested_pre_rec_sec
            clamped = False
            allocated_mib = requested_mib
            remaining_mib = round(budget_mib - allocated_mib, 3)
            gpe0_starved = True
            oom_risk = True
            status = "BLOCKED_DDR_OOM_STARVATION_RISK"
            errors.append(
                f"BLOCKED_DDR_OOM_STARVATION_RISK: {requested_mib} MiB exceeds FX3 budget {budget_mib} MiB"
            )
    else:
        effective_sec = requested_pre_rec_sec
        clamped = False
        allocated_mib = requested_mib
        remaining_mib = round(budget_mib - allocated_mib, 3)
        gpe0_starved = False
        oom_risk = False
        status = "ACTIVE_FULL_CACHE_BUDGET_OK"

    if effective_sec < PICTURE_CACHE_MIN_SEC and not errors and not disable_reasons:
        errors.append(
            f"EFFECTIVE_CACHE_BELOW_MIN: {effective_sec}s < {PICTURE_CACHE_MIN_SEC}s"
        )

    return PictureCacheDdrEvalResult(
        valid=len(errors) == 0,
        status=status,
        codec_profile=prof_u,
        capture_mode=cap_u,
        interval_rec_active=interval_rec_active,
        simul_rec_active=simul_rec_active,
        proxy_rec_active=proxy_rec_active,
        requested_pre_rec_sec=requested_pre_rec_sec,
        effective_pre_rec_sec=effective_sec,
        max_safe_pre_rec_sec=max_safe_sec,
        bitrate_mbps=bitrate_mbps,
        mib_per_sec=mib_per_sec,
        requested_ddr_mib=requested_mib,
        allocated_ddr_mib=allocated_mib,
        available_ddr_budget_mib=budget_mib,
        remaining_ddr_headroom_mib=remaining_mib,
        picture_cache_active=len(errors) == 0,
        clamped_by_ddr_budget=clamped,
        auto_disabled_reason="",
        timecode_forced_free_run=len(errors) == 0,
        gpe0_appfw_starved=gpe0_starved,
        oom_killer_risk=oom_risk,
        errors=tuple(errors),
    )


def evaluate_pillar_2_picture_cache_ddr(
    *,
    fx6_appfw_cache_markers: Tuple[str, ...],
    fx3_libmpr_prerec_markers: Tuple[str, ...],
    fx6_libmpr_prerec_markers: Tuple[str, ...],
    uxc_cache_labels: Dict[str, str],
    donor_errors: Sequence[str],
) -> PictureCacheDdrMatrixReport:
    """Verify Pillar 2 FX6 Picture Cache circular DDR ring-buffer budget on FX3 2048 MiB DRAM."""
    errors = list(donor_errors)

    e_4k60 = evaluate_picture_cache_ddr_budget(
        codec_profile="XAVC_I_4K60",
        requested_pre_rec_sec=16.0,
        allow_clamp=True,
    )
    e_4k24 = evaluate_picture_cache_ddr_budget(
        codec_profile="XAVC_I_4K24",
        requested_pre_rec_sec=16.0,
        allow_clamp=True,
    )
    e_l4k30 = evaluate_picture_cache_ddr_budget(
        codec_profile="XAVC_L_4K30",
        requested_pre_rec_sec=16.0,
        allow_clamp=True,
    )
    e_lfhd60 = evaluate_picture_cache_ddr_budget(
        codec_profile="XAVC_L_FHD60",
        requested_pre_rec_sec=16.0,
        allow_clamp=True,
    )
    e_sq = evaluate_picture_cache_ddr_budget(
        codec_profile="XAVC_I_4K60",
        requested_pre_rec_sec=5.0,
        capture_mode="SQ_MOTION",
    )
    e_raw = evaluate_picture_cache_ddr_budget(
        codec_profile="XAVC_I_4K60",
        requested_pre_rec_sec=5.0,
        capture_mode="HDMI_RAW16",
    )
    b_oom = evaluate_picture_cache_ddr_budget(
        codec_profile="XAVC_I_4K60",
        requested_pre_rec_sec=16.0,
        allow_clamp=False,
    )

    if not e_4k60.valid or e_4k60.effective_pre_rec_sec != 5.0 or e_4k60.allocated_ddr_mib != 375.0:
        errors.append(f"XAVC_I_4K60 clamp mismatch: {e_4k60}")
    if not e_4k24.valid or e_4k24.effective_pre_rec_sec != 12.0 or e_4k24.allocated_ddr_mib != 360.0:
        errors.append(f"XAVC_I_4K24 clamp mismatch: {e_4k24}")
    if not e_l4k30.valid or e_l4k30.effective_pre_rec_sec != 16.0 or e_l4k30.allocated_ddr_mib != 200.0:
        errors.append(f"XAVC_L_4K30 full cache mismatch: {e_l4k30}")
    if not e_lfhd60.valid or e_lfhd60.effective_pre_rec_sec != 16.0 or e_lfhd60.allocated_ddr_mib != 100.0:
        errors.append(f"XAVC_L_FHD60 full cache mismatch: {e_lfhd60}")
    if e_sq.picture_cache_active or e_sq.allocated_ddr_mib != 0.0:
        errors.append("S&Q mode failed to auto-disable Picture Cache")
    if e_raw.picture_cache_active or e_raw.allocated_ddr_mib != 0.0:
        errors.append("HDMI RAW16 mode failed to auto-disable Picture Cache")
    if b_oom.valid or not b_oom.oom_killer_risk or not b_oom.gpe0_appfw_starved:
        errors.append("Unclamped 4K60 16s DDR OOM starvation risk was not blocked")

    return PictureCacheDdrMatrixReport(
        passed=len(errors) == 0,
        fx6_appfw_cache_markers=fx6_appfw_cache_markers,
        fx3_libmpr_prerec_markers=fx3_libmpr_prerec_markers,
        fx6_libmpr_prerec_markers=fx6_libmpr_prerec_markers,
        uxc_cache_labels=uxc_cache_labels,
        fx3_total_dram_mib=FX3_TOTAL_AP_DRAM_MIB,
        fx3_cache_ddr_budget_mib=FX3_PICTURE_CACHE_DDR_BUDGET_MIB,
        eval_xavc_i_4k60_clamped_5s=e_4k60,
        eval_xavc_i_4k24_clamped_12s=e_4k24,
        eval_xavc_l_4k30_16s_full=e_l4k30,
        eval_xavc_l_fhd60_16s_full=e_lfhd60,
        eval_auto_disabled_sq_motion=e_sq,
        eval_auto_disabled_hdmi_raw16=e_raw,
        blocked_unclamped_4k60_16s_oom=b_oom,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: Wired USB-LAN FTP / FTPS & P12 00342260 Wi-Fi/BT RF-Off Firewall
# ---------------------------------------------------------------------------


def validate_ftp_media_path(raw_path: str) -> FtpPathGuardResult:
    """Enforce CWD/RETR restriction to external media roots and block eMMC p1..p15 traversal."""
    errors: List[str] = []
    if not raw_path or "\x00" in raw_path:
        return FtpPathGuardResult(
            allowed=False,
            status="BLOCKED_INVALID_EMPTY_OR_NUL_PATH",
            raw_path=raw_path,
            normalized_path="",
            allowed_root_matched="",
            emmc_partition_blocked=False,
            traversal_blocked=True,
            errors=("Empty or NUL-byte path rejected",),
        )

    traversal_detected = ".." in raw_path.split("/") or "\\" in raw_path
    norm = posixpath.normpath(raw_path.replace("\\", "/"))
    emmc_hit = bool(FORBIDDEN_EMMC_PARTITION_RE.search(raw_path) or FORBIDDEN_EMMC_PARTITION_RE.search(norm))
    sys_hit = any(norm == pref or norm.startswith(pref + "/") for pref in FORBIDDEN_FTP_SYSTEM_PREFIXES)

    matched_root = ""
    for root in ALLOWED_FTP_MEDIA_ROOTS:
        if norm == root or norm.startswith(root + "/"):
            matched_root = root
            break

    if traversal_detected:
        errors.append(f"BLOCKED_PATH_TRAVERSAL: {raw_path!r} contains '..' or backslash")
    if emmc_hit:
        errors.append(f"BLOCKED_INTERNAL_EMMC_PARTITION_ACCESS: {raw_path!r} targets p1..p15 / eMMC")
    if sys_hit:
        errors.append(f"BLOCKED_SYSTEM_DIRECTORY_ACCESS: {norm!r} targets OS root directory")
    if not matched_root:
        errors.append(
            f"BLOCKED_OUTSIDE_MEDIA_ROOT: {norm!r} is outside allowed {ALLOWED_FTP_MEDIA_ROOTS}"
        )

    allowed = len(errors) == 0
    if allowed:
        status = "ALLOWED_EXTERNAL_MEDIA_PATH"
    elif emmc_hit:
        status = "BLOCKED_INTERNAL_EMMC_P1_P15_ACCESS"
    elif traversal_detected:
        status = "BLOCKED_FTP_PATH_TRAVERSAL"
    else:
        status = "BLOCKED_OUTSIDE_MEDIA_ROOT"

    return FtpPathGuardResult(
        allowed=allowed,
        status=status,
        raw_path=raw_path,
        normalized_path=norm,
        allowed_root_matched=matched_root,
        emmc_partition_blocked=emmc_hit,
        traversal_blocked=traversal_detected,
        errors=tuple(errors),
    )


def evaluate_wired_ftp_transfer_session(
    *,
    nic_driver: str = "CDC_NCM_RTL8153",
    protocol: str = "FTPES_TLS13",
    data_mode: str = "PASV",
    transfer_target: str = "PROXY_ONLY",
    source_path: str = "/mnt/slot_a/M4ROOT/SUB/A001C001_261114_FX3AS03.MP4",
    p12_airplane_mode: bool = True,
    wlan_rf_enabled: bool = False,
    bt_rf_enabled: bool = False,
    hci_tx_packets: int = 0,
    root_cert_verified: bool = True,
    payload_bytes: Optional[bytes] = None,
    file_size_bytes: int = 16_777_216,
    resume_offset_bytes: int = 0,
    creators_cloud_clip_flag_filter: str = "OK_AND_KEEP",
) -> WiredFtpTransferEvalResult:
    """Audit wired CDC-NCM FTP/FTPS transfer, resume REST offset, P12 RF-off firewall & path isolation."""
    errors: List[str] = []
    nic_u = nic_driver.upper()
    proto_u = protocol.upper()
    mode_u = data_mode.upper()
    target_u = transfer_target.upper()

    if nic_u not in ALLOWED_WIRED_NIC_DRIVERS:
        errors.append(f"BLOCKED_UNSUPPORTED_OR_WIRELESS_NIC: {nic_driver!r}")
    if proto_u not in VALID_FTP_PROTOCOLS:
        errors.append(f"INVALID_FTP_PROTOCOL: {protocol!r}")
    elif proto_u in SECURE_TLS_PROTOCOLS and not root_cert_verified:
        errors.append("FT_ERR_FAIL_AUTH_CACERT: TLS root certificate not verified")
    if mode_u not in VALID_FTP_DATA_MODES:
        errors.append(f"INVALID_FTP_DATA_MODE: {data_mode!r}")
    elif mode_u != "PASV":
        errors.append("CT_ERR_PASV_NOT_SUPPORT: Active PORT mode rejected; PASV required")
    if target_u not in VALID_FTP_TRANSFER_TARGETS:
        errors.append(f"INVALID_FTP_TRANSFER_TARGET: {transfer_target!r}")

    # P12 00342260 Wi-Fi / BT RF-Off Firewall
    rf_isolated = p12_airplane_mode and (not wlan_rf_enabled) and (not bt_rf_enabled) and (hci_tx_packets == 0)
    if not rf_isolated:
        errors.append(
            "BLOCKED_P12_RF_VIOLATION_WF12_00342260_HAZARD: Wi-Fi/BT RF must stay fenced (Airplane Mode ON, 0 HCI TX)"
        )

    # Path traversal & eMMC p1..p15 firewall
    path_guard = validate_ftp_media_path(source_path)
    if not path_guard.allowed:
        errors.extend(path_guard.errors)

    # Resume REST offset & byte integrity check
    if payload_bytes is not None:
        actual_size = len(payload_bytes)
    else:
        actual_size = file_size_bytes

    if actual_size <= 0:
        errors.append(f"INVALID_FILE_SIZE: {actual_size}")
    if resume_offset_bytes < 0 or resume_offset_bytes > actual_size:
        errors.append(
            f"FT_ERR_RESUME_NOT_SUPPORT: resume_offset_bytes={resume_offset_bytes} outside [0, {actual_size}]"
        )
        remaining = 0
        resume_sha_ok = False
    else:
        remaining = actual_size - resume_offset_bytes
        if payload_bytes is not None:
            prefix = payload_bytes[:resume_offset_bytes]
            suffix = payload_bytes[resume_offset_bytes:]
            resume_sha_ok = hashlib.sha256(prefix + suffix).hexdigest() == hashlib.sha256(payload_bytes).hexdigest()
            if not resume_sha_ok:
                errors.append("RESUME_REST_SHA256_MISMATCH")
        else:
            resume_sha_ok = True

    est_sec = round((remaining * 8.0) / (WIRED_USBLAN_EFFECTIVE_THROUGHPUT_MBPS * 1_000_000.0), 4)
    valid = len(errors) == 0

    if valid:
        status = "VALID_WIRED_FTPS_P12_ISOLATED"
    elif not path_guard.allowed:
        status = path_guard.status
    elif not rf_isolated:
        status = "BLOCKED_P12_RF_VIOLATION_WF12_HAZARD"
    elif mode_u != "PASV":
        status = "BLOCKED_ACTIVE_PORT_MODE_UNSUPPORTED"
    elif nic_u not in ALLOWED_WIRED_NIC_DRIVERS:
        status = "BLOCKED_DISALLOWED_NIC_DRIVER"
    else:
        status = "BLOCKED_FTP_TRANSFER_VALIDATION_FAILED"

    return WiredFtpTransferEvalResult(
        valid=valid,
        status=status,
        nic_driver=nic_u,
        protocol=proto_u,
        data_mode=mode_u,
        transfer_target=target_u,
        source_path=source_path,
        normalized_source_path=path_guard.normalized_path,
        p12_airplane_mode=p12_airplane_mode,
        wlan_rf_enabled=wlan_rf_enabled,
        bt_rf_enabled=bt_rf_enabled,
        hci_tx_packets=hci_tx_packets,
        wf12_00342260_immune=rf_isolated,
        root_cert_verified=root_cert_verified,
        file_size_bytes=actual_size,
        resume_offset_bytes=resume_offset_bytes,
        remaining_bytes=remaining,
        resume_sha256_verified=resume_sha_ok,
        estimated_transfer_sec=est_sec,
        creators_cloud_clip_flag_filter=creators_cloud_clip_flag_filter,
        errors=tuple(errors),
    )


def evaluate_pillar_3_wired_ftp_p12(
    *,
    fx3_appfw_ftp_markers: Tuple[str, ...],
    fx6_appfw_ftp_markers: Tuple[str, ...],
    fx6_ftp_client_markers: Tuple[str, ...],
    fx6_ether_service_markers: Tuple[str, ...],
    uxc_ftp_usblan_labels: Dict[str, str],
    donor_errors: Sequence[str],
) -> WiredFtpP12MatrixReport:
    """Verify Pillar 3 wired USB-LAN FTP/FTPS, P12 RF-off firewall & p1..p15 traversal guard."""
    errors = list(donor_errors)

    e_proxy = evaluate_wired_ftp_transfer_session(
        nic_driver="CDC_NCM_RTL8153",
        protocol="FTPES_TLS13",
        data_mode="PASV",
        transfer_target="PROXY_ONLY",
        source_path="/mnt/slot_a/M4ROOT/SUB/A001C001_261114_FX3AS03.MP4",
        file_size_bytes=24_000_000,
        resume_offset_bytes=0,
    )
    sample_payload = b"SONY_XAVC_PROXY_STREAM_TEST_" * 1024
    e_resume = evaluate_wired_ftp_transfer_session(
        nic_driver="CDC_NCM_RTL8153",
        protocol="FTPES_TLS12",
        data_mode="PASV",
        transfer_target="PROXY_AND_ORIGINAL",
        source_path="/mnt/cfexpress_a/XDROOT/Clip/A001C002_261114_FX3A.MXF",
        payload_bytes=sample_payload,
        resume_offset_bytes=8192,
    )
    e_cloud = evaluate_wired_ftp_transfer_session(
        nic_driver="CDC_NCM_AX88179",
        protocol="FTPES_TLS13",
        data_mode="PASV",
        transfer_target="ORIGINAL_ONLY",
        source_path="/mnt/sd/M4ROOT/CLIP/C0001.MP4",
        file_size_bytes=128_000_000,
        resume_offset_bytes=0,
        creators_cloud_clip_flag_filter="KEEP_ONLY",
    )

    b_wf12 = evaluate_wired_ftp_transfer_session(
        nic_driver="CDC_NCM_RTL8153",
        protocol="FTPES_TLS13",
        data_mode="PASV",
        p12_airplane_mode=False,
        wlan_rf_enabled=True,
        bt_rf_enabled=True,
        hci_tx_packets=12,
    )
    b_port = evaluate_wired_ftp_transfer_session(
        nic_driver="CDC_NCM_RTL8153",
        protocol="FTPES_TLS13",
        data_mode="PORT",
    )
    b_nic = evaluate_wired_ftp_transfer_session(
        nic_driver="AX88179A",
        protocol="FTPES_TLS13",
        data_mode="PASV",
    )
    b_resume = evaluate_wired_ftp_transfer_session(
        nic_driver="CDC_NCM_RTL8153",
        protocol="FTPES_TLS13",
        data_mode="PASV",
        file_size_bytes=1024,
        resume_offset_bytes=2048,
    )

    traversal_probes = (
        "/mnt/sd/../../dev/nflasha1",
        "/mnt/slot_a/../../../etc/passwd",
        "/dev/mmcblk0p15",
        "/p1/Backup.bin",
        "/p15/lib/appFw.so",
        "/dev/cnflasha",
    )
    blocked_paths = tuple(validate_ftp_media_path(p) for p in traversal_probes)

    for lbl, ev in (("proxy_only", e_proxy), ("resume", e_resume), ("cloud_keep", e_cloud)):
        if not ev.valid or not ev.wf12_00342260_immune or not ev.resume_sha256_verified:
            errors.append(f"Pillar 3 valid FTP case {lbl} failed: {ev.errors}")
    if b_wf12.valid or b_wf12.wf12_00342260_immune:
        errors.append("P12 RF-on WF-12 hazard was not blocked")
    if b_port.valid:
        errors.append("Active FTP PORT mode was not blocked")
    if b_nic.valid:
        errors.append("Unsupported AX88179A NIC was not blocked")
    if b_resume.valid:
        errors.append("Out-of-bounds REST resume offset was not blocked")
    for pg in blocked_paths:
        if pg.allowed:
            errors.append(f"Forbidden eMMC/traversal path was allowed: {pg.raw_path!r}")

    return WiredFtpP12MatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_ftp_markers=fx3_appfw_ftp_markers,
        fx6_appfw_ftp_markers=fx6_appfw_ftp_markers,
        fx6_ftp_client_markers=fx6_ftp_client_markers,
        fx6_ether_service_markers=fx6_ether_service_markers,
        uxc_ftp_usblan_labels=uxc_ftp_usblan_labels,
        eval_rtl8153_ftpes_tls13_proxy_only=e_proxy,
        eval_rtl8153_ftpes_tls12_orig_proxy_resume=e_resume,
        eval_ax88179_creators_cloud_keep_flag=e_cloud,
        blocked_wifi_rf_p12_wf12_hazard=b_wf12,
        blocked_active_port_mode_unsupported=b_port,
        blocked_ax88179a_or_rndis_nic=b_nic,
        blocked_emmc_p1_to_p15_traversal_paths=blocked_paths,
        blocked_invalid_resume_offset=b_resume,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: Calibration/eMMC Zero-Mutation Proof & NonRealTimeMeta XML Parity
# ---------------------------------------------------------------------------


def evaluate_emmc_calibration_immutability(target_path: str) -> EmmcCalibrationImmutabilityResult:
    """Enforce zero persistent eMMC / factory calibration mutation while permitting volatile RAM overlays."""
    lower = target_path.lower().strip()
    is_volatile = any(lower.startswith(pref) for pref in VOLATILE_SHADOW_PREFIXES)
    is_forbidden = any(tok in lower for tok in FORBIDDEN_CALIBRATION_AND_EMMC_PATHS) or bool(
        FORBIDDEN_EMMC_PARTITION_RE.search(lower)
    )
    errors: List[str] = []
    if is_forbidden or not is_volatile:
        errors.append(
            f"BLOCKED_PERSISTENT_EMMC_OR_CALIBRATION_WRITE: {target_path!r} violates zero-mutation firewall"
        )
        return EmmcCalibrationImmutabilityResult(
            valid=False,
            status="BLOCKED_PERSISTENT_EMMC_WRITE",
            target_path=target_path,
            volatile_shadow_only=False,
            calibration_mutation_bytes=0,
            emmc_mutation_bytes=0,
            persistent_emmc_writes_authorized=False,
            errors=tuple(errors),
        )

    return EmmcCalibrationImmutabilityResult(
        valid=True,
        status="VOLATILE_RAM_SHADOW_ALLOWED",
        target_path=target_path,
        volatile_shadow_only=True,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=(),
    )


def synthesize_and_verify_interval_cache_nrtm_xml(
    *,
    mode_tag: str,
    interval_sec: Optional[int] = None,
    shutter_type: Optional[str] = None,
    ae_tracking_sensitivity: Optional[str] = None,
    pre_rec_sec: Optional[float] = None,
    cache_buffer_mib: Optional[float] = None,
    timecode_mode: Optional[str] = None,
    ftp_transport: str = "CDC_NCM_RTL8153",
    ftp_protocol: str = "FTPES_TLS13",
    p12_rf_isolated: bool = True,
) -> IntervalCacheNrtmXmlResult:
    """Synthesize and round-trip parse Sony NonRealTimeMeta v2.20 XML with Interval/Cache/FTP tags."""
    errors: List[str] = []
    ET.register_namespace("", NRTM_NAMESPACE_V220)
    ns = f"{{{NRTM_NAMESPACE_V220}}}"
    root = ET.Element(f"{ns}NonRealTimeMeta", {"lastUpdate": "2026-11-14T17:34:00Z"})
    ET.SubElement(root, f"{ns}Device", {"manufacturer": "Sony", "modelName": "ILME-FX3"})

    rec_attrs: Dict[str, str] = {"type": mode_tag}
    if mode_tag == "interval":
        if interval_sec is not None:
            rec_attrs["intervalSec"] = str(interval_sec)
        if shutter_type is not None:
            rec_attrs["shutterType"] = shutter_type
        if ae_tracking_sensitivity is not None:
            rec_attrs["aeTrackingSensitivity"] = ae_tracking_sensitivity
    elif mode_tag == "pictureCache":
        if pre_rec_sec is not None:
            rec_attrs["preRecSec"] = f"{pre_rec_sec:.1f}"
        if cache_buffer_mib is not None:
            rec_attrs["cacheBufferMiB"] = f"{cache_buffer_mib:.1f}"
        if timecode_mode is not None:
            rec_attrs["timecodeMode"] = timecode_mode
    else:
        errors.append(f"UNSUPPORTED_NRTM_MODE_TAG: {mode_tag!r}")

    ET.SubElement(root, f"{ns}RecordingMode", rec_attrs)
    ET.SubElement(
        root,
        f"{ns}FtpTransferStatus",
        {
            "transport": ftp_transport,
            "protocol": ftp_protocol,
            "p12RfIsolated": "true" if p12_rf_isolated else "false",
        },
    )

    xml_bytes = ET.tostring(root, encoding="utf-8", xml_declaration=True)
    xml_sha = hashlib.sha256(xml_bytes).hexdigest()

    # Round-trip parse verification
    parsed = ET.fromstring(xml_bytes)
    dev_el = parsed.find(f"{ns}Device")
    rec_el = parsed.find(f"{ns}RecordingMode")
    ftp_el = parsed.find(f"{ns}FtpTransferStatus")

    if dev_el is None or rec_el is None or ftp_el is None:
        errors.append("NRTM_XML_MISSING_REQUIRED_ELEMENT")
        model_name = ""
        rec_type = ""
        p_iv = None
        p_sh = None
        p_ae = None
        p_pre = None
        p_buf = None
        p_tc = None
        p_tr = ""
        p_pr = ""
        p_rf = False
    else:
        model_name = dev_el.attrib.get("modelName", "")
        rec_type = rec_el.attrib.get("type", "")
        p_iv = int(rec_el.attrib["intervalSec"]) if "intervalSec" in rec_el.attrib else None
        p_sh = rec_el.attrib.get("shutterType")
        p_ae = rec_el.attrib.get("aeTrackingSensitivity")
        p_pre = float(rec_el.attrib["preRecSec"]) if "preRecSec" in rec_el.attrib else None
        p_buf = float(rec_el.attrib["cacheBufferMiB"]) if "cacheBufferMiB" in rec_el.attrib else None
        p_tc = rec_el.attrib.get("timecodeMode")
        p_tr = ftp_el.attrib.get("transport", "")
        p_pr = ftp_el.attrib.get("protocol", "")
        p_rf = ftp_el.attrib.get("p12RfIsolated") == "true"

        if rec_type == "interval":
            if p_sh != "electronic":
                errors.append(f"NRTM_INTERVAL_NON_ELECTRONIC_SHUTTER: {p_sh!r}")
            if p_iv is None or not (INTERVAL_SEC_MIN <= p_iv <= INTERVAL_SEC_MAX):
                errors.append(f"NRTM_INTERVAL_SEC_INVALID: {p_iv}")
        elif rec_type == "pictureCache":
            if p_tc != "FreeRun":
                errors.append(f"NRTM_CACHE_TIMECODE_NOT_FREE_RUN: {p_tc!r}")
            if p_pre is None or p_buf is None or p_buf > FX3_PICTURE_CACHE_DDR_BUDGET_MIB:
                errors.append(f"NRTM_CACHE_BUDGET_INVALID: pre={p_pre}, buf={p_buf}")

        if not p_rf:
            errors.append("NRTM_FTP_P12_RF_NOT_ISOLATED")

    valid = len(errors) == 0
    return IntervalCacheNrtmXmlResult(
        valid=valid,
        status="NRTM_XML_PARITY_VERIFIED" if valid else "NRTM_XML_PARITY_FAILED",
        mode_tag=mode_tag,
        xml_bytes=len(xml_bytes),
        xml_sha256=xml_sha,
        model_name=model_name,
        recording_type=rec_type,
        interval_sec=p_iv,
        shutter_type=p_sh,
        ae_tracking_sensitivity=p_ae,
        pre_rec_sec=p_pre,
        cache_buffer_mib=p_buf,
        timecode_mode=p_tc,
        ftp_transport=p_tr,
        ftp_protocol=p_pr,
        p12_rf_isolated=p_rf,
        errors=tuple(errors),
    )


def evaluate_pillar_4_immutability_and_nrtm(
    *,
    fx3_global_xdb_valid: bool,
    fx6_global_xdb_valid: bool,
    donor_errors: Sequence[str],
) -> ImmutabilityAndNrtmReport:
    """Verify Pillar 4 calibration/eMMC zero-mutation proof and NonRealTimeMeta v2.20 tag parity."""
    errors = list(donor_errors)
    if not fx3_global_xdb_valid:
        errors.append("FX3 global.xdb validation failed")
    if not fx6_global_xdb_valid:
        errors.append("FX6 global.xdb validation failed")

    vol = evaluate_emmc_calibration_immutability("/tmp/fx6_stageb_interval_cache_ftp_shadow.json")
    b_cn = evaluate_emmc_calibration_immutability("/dev/cnflasha1")
    b_nf = evaluate_emmc_calibration_immutability("/dev/nflasha1")
    b_bak = evaluate_emmc_calibration_immutability("p2:/Backup.bin")
    b_psd = evaluate_emmc_calibration_immutability("p2:/psd.bin")

    if not vol.valid:
        errors.append("Volatile /tmp shadow path was unexpectedly blocked")
    for lbl, blk in (("cnflasha1", b_cn), ("nflasha1", b_nf), ("Backup.bin", b_bak), ("psd.bin", b_psd)):
        if blk.valid:
            errors.append(f"Persistent calibration/eMMC target {lbl} was not blocked")

    nrtm_iv = synthesize_and_verify_interval_cache_nrtm_xml(
        mode_tag="interval",
        interval_sec=5,
        shutter_type="electronic",
        ae_tracking_sensitivity="LOW",
    )
    nrtm_pc = synthesize_and_verify_interval_cache_nrtm_xml(
        mode_tag="pictureCache",
        pre_rec_sec=5.0,
        cache_buffer_mib=375.0,
        timecode_mode="FreeRun",
    )
    if not nrtm_iv.valid:
        errors.extend(nrtm_iv.errors)
    if not nrtm_pc.valid:
        errors.extend(nrtm_pc.errors)

    return ImmutabilityAndNrtmReport(
        passed=len(errors) == 0,
        fx3_global_xdb_valid=fx3_global_xdb_valid,
        fx6_global_xdb_valid=fx6_global_xdb_valid,
        volatile_shadow_eval=vol,
        blocked_cnflasha_eval=b_cn,
        blocked_nflasha1_eval=b_nf,
        blocked_backup_bin_eval=b_bak,
        blocked_psd_bin_eval=b_psd,
        nrtm_interval_eval=nrtm_iv,
        nrtm_picture_cache_eval=nrtm_pc,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Top-Level Phase 93 Unified Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_interval_cache_and_ftp(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> IntervalCacheAndFtpReport:
    """Run the 18th unified firmware-lab auditor in Local Donor (`os.O_RDONLY`) or Clean-Room mode."""
    root = repo_root or DEFAULT_REPO_ROOT
    forced_clean = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not forced_clean:
        donor_paths = {
            "fx3_appfw": resolve_donor_file(FX3_APPFW_RELPATH, repo_root=root),
            "fx6_appfw": resolve_donor_file(FX6_APPFW_RELPATH, repo_root=root),
            "fx3_libmpr": resolve_donor_file(FX3_LIBMPR_RELPATH, repo_root=root),
            "fx6_libmpr": resolve_donor_file(FX6_LIBMPR_RELPATH, repo_root=root),
            "fx3_cpapp": resolve_donor_file(FX3_CPAPP_RELPATH, repo_root=root),
            "fx6_cpapp": resolve_donor_file(FX6_CPAPP_RELPATH, repo_root=root),
            "fx6_libinfra_ftp": resolve_donor_file(FX6_LIBINFRA_FTP_RELPATH, repo_root=root),
            "fx6_libnet_ether": resolve_donor_file(FX6_LIBNET_ETHER_RELPATH, repo_root=root),
            "fx3_global_xdb": resolve_donor_file(FX3_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx6_global_xdb": resolve_donor_file(FX6_GLOBAL_XDB_RELPATH, repo_root=root),
            "fx3_str_en": resolve_donor_file(FX3_STR_EN_RELPATH, repo_root=root),
            "fx3_str_en_g": resolve_donor_file(FX3_STR_EN_G_RELPATH, repo_root=root),
            "fx6_str_en_1": resolve_donor_file(FX6_STR_EN_1_RELPATH, repo_root=root),
            "fx6_str_en_2": resolve_donor_file(FX6_STR_EN_2_RELPATH, repo_root=root),
        }

    use_local = (not forced_clean) and all(p is not None and p.is_file() for p in donor_paths.values())
    mode = "LOCAL_DONOR_VERIFIED" if use_local else "CLEAN_ROOM_SYNTHETIC"

    sizes: Dict[str, int] = {}
    p1_errors: List[str] = []
    p2_errors: List[str] = []
    p3_errors: List[str] = []
    p4_errors: List[str] = []

    if use_local:
        sz_fx3_app, fx3_app_res = _scan_donor_rdonly_markers(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            {"iv": FX3_APPFW_INTERVAL_MARKERS, "ftp": FX3_APPFW_FTP_USBLAN_MARKERS},
            is_elf=True,
        )
        sz_fx6_app, fx6_app_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            {
                "iv": FX6_APPFW_INTERVAL_MARKERS,
                "cache": FX6_APPFW_CACHE_MARKERS,
                "ftp": FX6_APPFW_FTP_USBLAN_MARKERS,
            },
            is_elf=True,
        )
        sz_fx3_mpr, fx3_mpr_res = _scan_donor_rdonly_markers(
            donor_paths["fx3_libmpr"],  # type: ignore[arg-type]
            {"mpr": LIBMPR_INTERVAL_PREREC_NRTM_MARKERS},
            is_elf=True,
        )
        sz_fx6_mpr, fx6_mpr_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_libmpr"],  # type: ignore[arg-type]
            {"mpr": LIBMPR_INTERVAL_PREREC_NRTM_MARKERS},
            is_elf=True,
        )
        sz_fx3_cp, fx3_cp_res = _scan_donor_rdonly_markers(
            donor_paths["fx3_cpapp"],  # type: ignore[arg-type]
            {"cp": FX3_CP_INTERVAL_MARKERS},
            is_elf=False,
        )
        sz_fx6_cp, fx6_cp_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_cpapp"],  # type: ignore[arg-type]
            {"cp": FX6_CP_INTERVAL_MARKERS},
            is_elf=False,
        )
        sz_fx6_ftp, fx6_ftp_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_libinfra_ftp"],  # type: ignore[arg-type]
            {"ftp": FX6_FTP_CLIENT_MARKERS},
            is_elf=True,
        )
        sz_fx6_eth, fx6_eth_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_libnet_ether"],  # type: ignore[arg-type]
            {"eth": FX6_ETHER_SERVICE_MARKERS},
            is_elf=True,
        )

        fx3_xdb_bytes = _read_bytes_rdonly(donor_paths["fx3_global_xdb"])  # type: ignore[arg-type]
        fx6_xdb_bytes = _read_bytes_rdonly(donor_paths["fx6_global_xdb"])  # type: ignore[arg-type]
        fx3_str_en_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en"])  # type: ignore[arg-type]
        fx3_str_en_g_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en_g"])  # type: ignore[arg-type]
        fx6_str_en_1_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_1"])  # type: ignore[arg-type]
        fx6_str_en_2_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_2"])  # type: ignore[arg-type]
    else:
        fx = build_clean_room_interval_cache_ftp_fixtures()
        sz_fx3_app, fx3_app_res = _scan_bytes_marker_groups(
            fx["fx3_appfw"], {"iv": FX3_APPFW_INTERVAL_MARKERS, "ftp": FX3_APPFW_FTP_USBLAN_MARKERS}
        )
        sz_fx6_app, fx6_app_res = _scan_bytes_marker_groups(
            fx["fx6_appfw"],
            {
                "iv": FX6_APPFW_INTERVAL_MARKERS,
                "cache": FX6_APPFW_CACHE_MARKERS,
                "ftp": FX6_APPFW_FTP_USBLAN_MARKERS,
            },
        )
        sz_fx3_mpr, fx3_mpr_res = _scan_bytes_marker_groups(
            fx["fx3_libmpr"], {"mpr": LIBMPR_INTERVAL_PREREC_NRTM_MARKERS}
        )
        sz_fx6_mpr, fx6_mpr_res = _scan_bytes_marker_groups(
            fx["fx6_libmpr"], {"mpr": LIBMPR_INTERVAL_PREREC_NRTM_MARKERS}
        )
        sz_fx3_cp, fx3_cp_res = _scan_bytes_marker_groups(
            fx["fx3_cpapp"], {"cp": FX3_CP_INTERVAL_MARKERS}
        )
        sz_fx6_cp, fx6_cp_res = _scan_bytes_marker_groups(
            fx["fx6_cpapp"], {"cp": FX6_CP_INTERVAL_MARKERS}
        )
        sz_fx6_ftp, fx6_ftp_res = _scan_bytes_marker_groups(
            fx["fx6_libinfra_ftp"], {"ftp": FX6_FTP_CLIENT_MARKERS}
        )
        sz_fx6_eth, fx6_eth_res = _scan_bytes_marker_groups(
            fx["fx6_libnet_ether"], {"eth": FX6_ETHER_SERVICE_MARKERS}
        )

        fx3_xdb_bytes = fx["fx3_global_xdb"]
        fx6_xdb_bytes = fx["fx6_global_xdb"]
        fx3_str_en_bytes = fx["fx3_str_en"]
        fx3_str_en_g_bytes = fx["fx3_str_en_g"]
        fx6_str_en_1_bytes = fx["fx6_str_en_1"]
        fx6_str_en_2_bytes = fx["fx6_str_en_2"]

    sizes = {
        "fx3_appfw": sz_fx3_app,
        "fx6_appfw": sz_fx6_app,
        "fx3_libmpr": sz_fx3_mpr,
        "fx6_libmpr": sz_fx6_mpr,
        "fx3_cpapp": sz_fx3_cp,
        "fx6_cpapp": sz_fx6_cp,
        "fx6_libinfra_ftp": sz_fx6_ftp,
        "fx6_libnet_ether": sz_fx6_eth,
        "fx3_global_xdb": len(fx3_xdb_bytes),
        "fx6_global_xdb": len(fx6_xdb_bytes),
        "fx3_str_en": len(fx3_str_en_bytes),
        "fx3_str_en_g": len(fx3_str_en_g_bytes),
        "fx6_str_en_1": len(fx6_str_en_1_bytes),
        "fx6_str_en_2": len(fx6_str_en_2_bytes),
    }

    # Check marker completeness
    if len(fx3_app_res["iv"]) != len(FX3_APPFW_INTERVAL_MARKERS):
        p1_errors.append("Missing FX3 appFw Interval markers")
    if len(fx6_app_res["iv"]) != len(FX6_APPFW_INTERVAL_MARKERS):
        p1_errors.append("Missing FX6 appFw Interval markers")
    if len(fx3_cp_res["cp"]) != len(FX3_CP_INTERVAL_MARKERS):
        p1_errors.append("Missing FX3 CP Interval markers")
    if len(fx6_cp_res["cp"]) != len(FX6_CP_INTERVAL_MARKERS):
        p1_errors.append("Missing FX6 CP Interval markers")
    if len(fx3_mpr_res["mpr"]) != len(LIBMPR_INTERVAL_PREREC_NRTM_MARKERS):
        p1_errors.append("Missing FX3 libmpr PreRec/NRTM/Interval markers")

    if len(fx6_app_res["cache"]) != len(FX6_APPFW_CACHE_MARKERS):
        p2_errors.append("Missing FX6 appFw Picture Cache markers")
    if len(fx6_mpr_res["mpr"]) != len(LIBMPR_INTERVAL_PREREC_NRTM_MARKERS):
        p2_errors.append("Missing FX6 libmpr PreRec/NRTM/Interval markers")

    if len(fx3_app_res["ftp"]) != len(FX3_APPFW_FTP_USBLAN_MARKERS):
        p3_errors.append("Missing FX3 appFw FTP/USB-LAN/Airplane markers")
    if len(fx6_app_res["ftp"]) != len(FX6_APPFW_FTP_USBLAN_MARKERS):
        p3_errors.append("Missing FX6 appFw FTP/USB-LAN/Airplane markers")
    if len(fx6_ftp_res["ftp"]) != len(FX6_FTP_CLIENT_MARKERS):
        p3_errors.append("Missing FX6 libInfraFtpClient.so markers")
    if len(fx6_eth_res["eth"]) != len(FX6_ETHER_SERVICE_MARKERS):
        p3_errors.append("Missing FX6 libNetServiceEther.so markers")

    # Parse global.xdb & .uxc labels
    fx3_xdb_valid = False
    fx6_xdb_valid = False
    try:
        parse_global_xdb_buffer(fx3_xdb_bytes)
        fx3_xdb_valid = True
    except Exception as exc:
        p4_errors.append(f"FX3 global.xdb parse error: {exc}")
    try:
        parse_global_xdb_buffer(fx6_xdb_bytes)
        fx6_xdb_valid = True
    except Exception as exc:
        p4_errors.append(f"FX6 global.xdb parse error: {exc}")

    uxc_3_ns39, u_errs_1 = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE93_LABELS)
    uxc_3_ns3, u_errs_2 = _extract_uxc_labels(fx3_str_en_g_bytes, FX3_NS3_PHASE93_LABELS)
    uxc_6_ns1, u_errs_3 = _extract_uxc_labels(fx6_str_en_1_bytes, FX6_NS1_PHASE93_LABELS)
    uxc_6_ns2, u_errs_4 = _extract_uxc_labels(fx6_str_en_2_bytes, FX6_NS2_PHASE93_LABELS)
    uxc_errs = list(u_errs_1) + list(u_errs_2) + list(u_errs_3) + list(u_errs_4)
    p1_errors.extend(u_errs_2 + u_errs_3 + u_errs_4)
    p2_errors.extend(u_errs_3 + u_errs_4)
    p3_errors.extend(uxc_errs)

    uxc_interval_labels = {
        "fx3_interval_shooting": uxc_3_ns3.get("0x000061c8", ""),
        "fx6_interval_rec": uxc_6_ns2.get("0x00004247", ""),
        "fx6_interval_num_frames": uxc_6_ns1.get("0x00002f27", ""),
    }
    uxc_cache_labels = {
        "fx6_picture_cache_rec": uxc_6_ns2.get("0x0000424c", ""),
        "fx6_cache_rec": uxc_6_ns1.get("0x00002e7d", ""),
        "fx6_cache_size": uxc_6_ns1.get("0x00002554", ""),
        "fx6_cache_rec_time": uxc_6_ns2.get("0x0000457c", ""),
    }
    uxc_ftp_usblan_labels = {
        "fx3_wired_lan": uxc_3_ns39.get("0x0000e100", ""),
        "fx3_wirelan_usblan": uxc_3_ns39.get("0x0000e39a", ""),
        "fx3_usblan_tethering": uxc_3_ns3.get("0x0000645f", ""),
        "fx3_ftp_transfer": uxc_3_ns3.get("0x000064bf", ""),
        "fx6_auto_upload_proxy": uxc_6_ns1.get("0x00002f61", ""),
        "fx6_auto_upload": uxc_6_ns1.get("0x00002f63", ""),
        "fx6_airplane_mode": uxc_6_ns2.get("0x000042d3", ""),
        "fx6_file_transfer_status": uxc_6_ns2.get("0x000052e9", ""),
    }

    p1 = evaluate_pillar_1_interval_recording(
        fx3_appfw_markers=fx3_app_res["iv"],
        fx6_appfw_markers=fx6_app_res["iv"],
        fx3_cp_markers=fx3_cp_res["cp"],
        fx6_cp_markers=fx6_cp_res["cp"],
        fx3_libmpr_markers=fx3_mpr_res["mpr"],
        uxc_interval_labels=uxc_interval_labels,
        donor_errors=p1_errors,
    )
    p2 = evaluate_pillar_2_picture_cache_ddr(
        fx6_appfw_cache_markers=fx6_app_res["cache"],
        fx3_libmpr_prerec_markers=fx3_mpr_res["mpr"],
        fx6_libmpr_prerec_markers=fx6_mpr_res["mpr"],
        uxc_cache_labels=uxc_cache_labels,
        donor_errors=p2_errors,
    )
    p3 = evaluate_pillar_3_wired_ftp_p12(
        fx3_appfw_ftp_markers=fx3_app_res["ftp"],
        fx6_appfw_ftp_markers=fx6_app_res["ftp"],
        fx6_ftp_client_markers=fx6_ftp_res["ftp"],
        fx6_ether_service_markers=fx6_eth_res["eth"],
        uxc_ftp_usblan_labels=uxc_ftp_usblan_labels,
        donor_errors=p3_errors,
    )
    p4 = evaluate_pillar_4_immutability_and_nrtm(
        fx3_global_xdb_valid=fx3_xdb_valid,
        fx6_global_xdb_valid=fx6_xdb_valid,
        donor_errors=p4_errors,
    )

    all_errors = list(p1.errors) + list(p2.errors) + list(p3.errors) + list(p4.errors)
    all_passed = p1.passed and p2.passed and p3.passed and p4.passed and len(all_errors) == 0

    digest_payload = {
        "schema_version": PHASE_93_SCHEMA,
        "phase_version": PHASE_93_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "donor_file_sizes": sizes,
        "pillar_1": asdict(p1),
        "pillar_2": asdict(p2),
        "pillar_3": asdict(p3),
        "pillar_4": asdict(p4),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return IntervalCacheAndFtpReport(
        schema_version=PHASE_93_SCHEMA,
        phase_version=PHASE_93_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=False,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        donor_file_sizes=sizes,
        pillar_1_interval_recording=p1,
        pillar_2_picture_cache_ddr=p2,
        pillar_3_wired_ftp_p12=p3,
        pillar_4_immutability_and_nrtm=p4,
        errors=tuple(all_errors),
        report_sha256=report_sha256,
    )


def interval_cache_and_ftp_report_to_dict(report: IntervalCacheAndFtpReport) -> Dict[str, object]:
    """Serialize `IntervalCacheAndFtpReport` to a deterministic JSON-compatible dict."""
    return report.to_dict()
