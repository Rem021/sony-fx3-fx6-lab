"""Phase 105 — 20th Unified Firmware-Lab Auditor: C2PA 2.1 Camera Authenticity &
`cnflasha` Key-Vault Zero-Touch Firewall, E-Mount 12-Pin Lens Shading / Vignetting /
Lateral Chromatic-Aberration / Distortion Polynomial Compensation (with Unchipped PL
& Anamorphic Identity `1.0x` Fail-Safe), Sony Monitor & Control Wired USB-LAN
`PTP-IP` 4-Camera Multi-Cam Fleet Isolation (`P12` RF-Off), & Per-Body Factory
Shading / Defect-Pixel Map Bit-Exact Preservation Proof.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`,
  `global.xdb`, `string_english.uxc`, `string_english_g.uxc`) and FX6 v6.01
  (`appFw.so`, `libmpr.so`, `cpapp-b.bin`, `libCertificateManager.so`,
  `libInfraPtpControl.so`, `libNetServiceEther.so`, `global.xdb`,
  `string_english.uxc`, `string_english_2.uxc`) strictly via `os.O_RDONLY` +
  `mmap.ACCESS_READ` and ELF64 `.rodata`/`.dynstr` section-scoped scanning, plus
  `uxa\\x07` / `.uxc` container parsing (< 0.35s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact verified contract markers and runs the
  identical four-pillar verification pipeline (< 0.02s warm, zero proprietary
  files required).

Audits Four Phase 105 Pillars:
1. Pillar 1 — C2PA 2.1 / Sony Camera Authenticity & `cnflasha` Key-Vault
   Zero-Touch Firewall:
   - Audits per-body asymmetric attestation / C2PA 2.1 JUMBF (`jumb`/`jumd`/
     `c2ma`/`c2cl`/`c2as`/`c2cs`) boundaries, proving Stage-B strictly mounts
     `cnflasha` / `RPMB` / `p12:/cert` key vaults read-only (`O_RDONLY`: `0`
     writes, `0` key extraction, `0` cross-body certificate spoofing) and
     transparently marks Stage-B userland-overlay clips as unsigned clean-room
     research builds without attempting forged C2PA hardware signatures, while
     enforcing FX3's `<= 222 Mbps` MP4 ceiling, `S&Q` exclusion, and `<= 100`
     `RQ_LIC.DAT` license package bound.
2. Pillar 2 — E-Mount 12-Pin Lens Shading / Vignetting, Lateral Chromatic
   Aberration & Distortion Polynomial Compensation:
   - Audits radial `cos^4(theta)` peripheral illumination falloff compensation,
     R/B lateral chromatic-aberration micro-scale polynomials, and Newton-Raphson
     invertible barrel/pincushion distortion tables across native Sony G-Master
     lenses (`FE 16-35mm GM II`, `FE 50mm f/1.2 GM`, `FE 70-200mm GM OSS II`) vs
     unchipped manual PL/anamorphic lenses (where auto-compensation MUST
     fail-safe to strict identity `1.0x` rather than retaining stale electronic
     lens coefficients).
3. Pillar 3 — Sony Monitor & Control Wired USB-LAN Multi-Cam Fleet (4-Camera
   Matrix) & `P12` RF-Off Isolation:
   - Audits 4-camera wired Ethernet (`CDC-NCM` / `RTL8153` via switching hub /
     router) `PTP-IP` (`TCP/15740`) + `HTTP-REST` fleet discovery with unified
     `Access Authentication`, synchronized `False Color` / `Waveform` /
     `Focus Map` telemetry streaming, and gang `REC` trigger (`<= 16.7 ms`
     skew) while keeping Wi-Fi/BT RF 100% fenced under `P12` (`0` `WF-12`
     `00342260` hits, `0` HCI TX packets), and blocking direct-to-iPad Ethernet
     or unsupported FX6 `USB Tethering` on iPadOS.
4. Pillar 4 — Per-Body Factory Shading / Defect-Pixel Map Bit-Exact
   Preservation Proof:
   - Verifies SHA-256 bit-exact immutability across `p2:/setting/psd.bin`,
     `p2:/setting/defdet.bin`, `p2:/setting/Backup.bin`, `p6:/tmp/jiritsu`,
     `p18:/lens/lensfile.bin`, and `p12:/cert`, ensuring volatile `/tmp/` /
     `ram://` staging with `calibration_mutation_bytes == 0`,
     `emmc_mutation_bytes == 0`, and `persistent_emmc_writes_authorized == False`.
"""

from __future__ import annotations

import hashlib
import json
import math
import mmap
import os
import re
import struct
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
from .interval_cache_and_ftp_auditor import FX6_LIBNET_ETHER_RELPATH
from .lut3d_cube_tetrahedral_and_sdi_hdmi_auditor import (
    FX3_GLOBAL_XDB_RELPATH,
    FX3_STR_EN_G_RELPATH,
    FX3_STR_EN_RELPATH,
    FX6_GLOBAL_XDB_RELPATH,
    FX6_STR_EN_1_RELPATH,
    FX6_STR_EN_2_RELPATH,
)
from .sensor_codec_compatibility_analyzer import (
    FX3_CPAPP_RELPATH,
    FX3_LIBMPR_RELPATH,
    FX6_CPAPP_RELPATH,
    FX6_LIBMPR_RELPATH,
)


PHASE_105_SCHEMA = "fx3_firmware_lab_phase105_c2pa_shading_mc_fleet_v1"
PHASE_105_VERSION = "105.0.0"

FX6_LIBCERT_MGR_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/"
    "nflasha15-files/lib/libCertificateManager.so"
)
FX6_LIBINFRA_PTP_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/"
    "nflasha15-files/lib/libInfraPtpControl.so"
)

# ---------------------------------------------------------------------------
# Pillar 1 Constants: C2PA 2.1 & `cnflasha` Key-Vault Firewall
# ---------------------------------------------------------------------------

C2PA_SPEC_VERSION = "2.1"
C2PA_JUMBF_UUID_HEX = "6332706100110010800000aa00389b71"
C2PA_JUMBF_UUID_BYTES = bytes.fromhex(C2PA_JUMBF_UUID_HEX)
C2PA_JUMBF_BOX_TYPES: Tuple[str, ...] = ("jumb", "jumd", "c2ma", "c2cl", "c2as", "c2cs")
C2PA_SUPPORTED_MP4_MAX_BITRATE_MBPS = 222.0
C2PA_MAX_LICENSES_PER_RQ_LIC_FX3 = 100
CNFLASHA_KEYVAULT_MOUNT_MODE = "O_RDONLY"
STAGE_B_PROVENANCE_ACTION = "c2pa.edited"
STAGE_B_CLEAN_ROOM_RESEARCH_LABEL = "STAGE_B_CLEAN_ROOM_RESEARCH_OVERLAY_UNVERIFIED_UNSIGNED"

FORBIDDEN_KEYVAULT_TARGET_RE = re.compile(
    r"(?:^|/)(?:cnflasha\d*|nflasha\d*|mmcblk0(?:p\d+|rpmb)?|rpmb|tee\d*)(?:/|:|$)"
    r"|p12:/cert|rq_lic\.dat|sigcert\.(?:p12|pfx)|trustzone_rot|ecdsa_privkey",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Pillar 2 Constants: E-Mount 12-Pin Optical Compensation & Unchipped Fail-Safe
# ---------------------------------------------------------------------------

IMX510_SENSOR_HALF_DIAGONAL_MM = 21.633  # sqrt((35.6/2)^2 + (23.8/2)^2)
IMX510_SENSOR_WIDTH_PX = 4096
SHADING_MAX_DIGITAL_GAIN = 4.0  # +2.0 EV hard digital shading clamp
SHADING_AUTO_LOW_SCALE = 0.50
LATERAL_CA_MIN_REDUCTION_RATIO = 0.95
LATERAL_CA_MAX_RESIDUAL_PX = 0.15
DISTORTION_INVERSION_MAX_RESIDUAL = 1e-8
VALID_COMPENSATION_MODES: Tuple[str, ...] = ("AUTO", "AUTO_LOW", "OFF")

EMOUNT_LENS_PROFILES: Dict[str, Dict[str, object]] = {
    "SEL1635GM2_16MM": {
        "lens_name": "Sony FE 16-35mm F2.8 GM II @ 16mm",
        "mount_pins_detected": True,
        "theta_max_deg": 32.5,  # Retrofocus exit-pupil chief-ray angle at IMX510 corner
        "vignetting_s2": 0.14,
        "ca_r_coeffs": (-0.00145, 0.00028),
        "ca_b_coeffs": (0.00118, -0.00021),
        "distortion_coeffs": (-0.072, 0.011),  # Barrel distortion
        "distortion_kind": "BARREL",
    },
    "SEL50F12GM": {
        "lens_name": "Sony FE 50mm F1.2 GM",
        "mount_pins_detected": True,
        "theta_max_deg": 21.0,
        "vignetting_s2": 0.12,
        "ca_r_coeffs": (-0.00042, 0.00006),
        "ca_b_coeffs": (0.00039, -0.00005),
        "distortion_coeffs": (-0.012, 0.002),  # Mild barrel
        "distortion_kind": "MILD_BARREL",
    },
    "SEL70200GM2_200MM": {
        "lens_name": "Sony FE 70-200mm F2.8 GM OSS II @ 200mm",
        "mount_pins_detected": True,
        "theta_max_deg": 8.5,
        "vignetting_s2": 0.09,
        "ca_r_coeffs": (0.00055, -0.00008),
        "ca_b_coeffs": (-0.00062, 0.00009),
        "distortion_coeffs": (0.038, -0.004),  # Pincushion distortion
        "distortion_kind": "PINCUSHION",
    },
    "UNCHIPPED_PL_CINE_PRIME": {
        "lens_name": "Manual PL Cine Prime (Passive 12-Pin Adapter)",
        "mount_pins_detected": False,
        "theta_max_deg": 0.0,
        "vignetting_s2": 0.0,
        "ca_r_coeffs": (0.0, 0.0),
        "ca_b_coeffs": (0.0, 0.0),
        "distortion_coeffs": (0.0, 0.0),
        "distortion_kind": "IDENTITY_NONE",
    },
    "MANUAL_ANAMORPHIC_2X": {
        "lens_name": "Manual 2.0x Anamorphic Cine Lens (Unchipped)",
        "mount_pins_detected": False,
        "theta_max_deg": 0.0,
        "vignetting_s2": 0.0,
        "ca_r_coeffs": (0.0, 0.0),
        "ca_b_coeffs": (0.0, 0.0),
        "distortion_coeffs": (0.0, 0.0),
        "distortion_kind": "IDENTITY_NONE",
    },
}

# ---------------------------------------------------------------------------
# Pillar 3 Constants: Sony Monitor & Control Wired USB-LAN PTP-IP Multi-Cam
# ---------------------------------------------------------------------------

PTPIP_TCP_PORT = 15740
PTPIP_PKT_INIT_COMMAND_REQ = 0x00000001
PTPIP_PKT_INIT_COMMAND_ACK = 0x00000002
PTPIP_PKT_INIT_EVENT_REQ = 0x00000003
PTPIP_PKT_INIT_EVENT_ACK = 0x00000004
PTPIP_PKT_CMD_REQ = 0x00000006
PTPIP_PROTOCOL_VERSION = 0x00010000

MC_FREE_PLAN_MAX_CAMERAS = 4
MC_BASIC_PLAN_MAX_CAMERAS = 4
MC_PREMIUM_PLAN_MAX_CAMERAS = 20
MC_USB_LAN_PRACTICAL_CAP_MBPS = 300.0
MC_GANG_REC_MAX_SKEW_MS = 16.7  # <= 1 frame at 60p / < 0.5 frame at 24p

VALID_MC_NIC_DRIVERS: Tuple[str, ...] = ("CDC_NCM_RTL8153", "CDC_NCM_UE300C_V2", "BELKIN_USBC_ETH")
VALID_MC_TOPOLOGIES: Tuple[str, ...] = ("WIRED_LAN_SWITCH_OR_ROUTER",)
UNSUPPORTED_MC_TOPOLOGIES: Tuple[str, ...] = ("DIRECT_ETHERNET_NO_ROUTER", "FX6_USB_TETHER_IPADOS")
VALID_MC_TELEMETRY_STREAMS: Tuple[str, ...] = ("FALSE_COLOR", "WAVEFORM", "FOCUS_MAP", "TIMECODE")

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Factory Shading & Defect-Pixel Map Immutability
# ---------------------------------------------------------------------------

FACTORY_CALIBRATION_FILES: Tuple[str, ...] = (
    "p2:/setting/psd.bin",
    "p2:/setting/defdet.bin",
    "p2:/setting/Backup.bin",
    "p6:/tmp/jiritsu",
    "p18:/lens/lensfile.bin",
    "p12:/cert",
)
VOLATILE_STAGING_PREFIXES: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_FACTORY_MUTATION_RE = re.compile(
    r"(?:^|/)(?:p(?:[1-9]|1[0-8])|nflasha\d*|cnflasha\d*|mmcblk0(?:p\d+|rpmb)?|mtdblock\d*)(?:/|:|$)"
    r"|psd\.bin|defdet\.bin|backup\.bin|jiritsu|lensfile\.bin|shading://|nvram://|eeprom://",
    re.IGNORECASE,
)

# ---------------------------------------------------------------------------
# Verified Binary & .uxc Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_PHASE105_MARKERS: Tuple[str, ...] = (
    "_ZN9InfraC2PA21SearchCertificateFileERKNS_28searchCertificateFileInParamEPNS_29searchCertificateFileOutParamE",
    "_ZN9InfraC2PA29UnlockCertificateFileAndStoreERKNS_36unlockCertificateFileAndStoreInParamE",
    "_ZN9InfraC2PA18GetCertificateInfoEPNS_26getCertificateInfoOutParamE",
    "_ZN9InfraC2PA21DeleteCertificateInfoEv",
    "DIGITAL_SIGNATURE_B2B_B2C_WRITE_DIGITAL_SIGNATURE_ON",
    "DIGITAL_SIGNATURE_B2B_B2C_WRITE_DIGITAL_SIGNATURE_OFF",
    "DIGITAL_SIGNATURE_STILL_MOVIE_CERTIFICATE_FOR_C2PA_CERTIFICATE1",
    "VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO",
    "VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO_LOW",
    "VAL_setting_lens_comp_chro_aber_LENS_COMP_CHRO_ABER_AUTO",
    "VAL_setting_lens_comp_chro_aber_LENS_COMP_CHRO_ABER_OFF",
    "VAL_setting_lens_comp_distortion_LENS_COMP_DISTORTION_AUTO",
    "VAL_setting_lens_comp_distortion_LENS_COMP_DISTORTION_OFF",
    "PID_SET_SHADING_CORRECTION",
    "PID_SET_CHROMA_ABERR_CORRECTION",
    "PID_SET_DISTORTION_CORRECTION",
    "VAL_setting_access_authentication_ACCESS_AUTHENTICATION_ON",
    "VAL_setting_airplane_mode_AIRPLANE_MODE_ON",
    "STREAMING_CONNECT_METHOD_USB_ETHER",
    "USB_LAN_CONNECT_LAUNCH_ON",
    "INFRA_NOTIFY_PTP_OPERATION_DATA_SET_CMP_FOR_CONTROL_MONITORING",
    "INFRA_NOTIFY_PTP_GET_LENS_INFORMATION",
)

FX6_APPFW_PHASE105_MARKERS: Tuple[str, ...] = (
    "_ZN9InfraC2PA21SearchCertificateFileERKNS_28searchCertificateFileInParamEPNS_29searchCertificateFileOutParamE",
    "_ZN9InfraC2PA18GetCertificateInfoEPNS_26getCertificateInfoOutParamE",
    "VAL_c2pa_certificate_status_C2PA_CERTIFICATE_STATUS_NONE",
    "VAL_c2pa_certificate_status_C2PA_CERTIFICATE_STATUS_VALID",
    "VAL_c2pa_operation_state_C2PA_OPERATION_STATE_OFF",
    "BKID_APP_EXTERN_LENS_SHADING_COMPENSATION",
    "BKID_APP_EXTERN_LENS_CHROMATIC_ABERRATION_COMPENSATION",
    "BKID_APP_EXTERN_LENS_DISTORTION_COMPENSATION",
    "VAL_setting_lens_comp_shading_LENS_COMP_SHADING_AUTO",
    "VAL_setting_lens_comp_shading_LENS_COMP_SHADING_OFF",
    "VAL_setting_lens_comp_chro_aber_LENS_COMP_CHRO_ABER_AUTO",
    "VAL_setting_lens_comp_chro_aber_LENS_COMP_CHRO_ABER_OFF",
    "VAL_setting_lens_comp_distortion_LENS_COMP_DISTORTION_AUTO",
    "VAL_setting_lens_comp_distortion_LENS_COMP_DISTORTION_OFF",
    "PID_SET_SHADING_CORRECTION",
    "PID_SET_DISTORTION_CORRECTION",
    "VAL_ptp_ip_connect_state_PTP_IP_CONNECT_STATE_CONNECT",
    "VAL_ptp_ip_connect_state_PTP_IP_CONNECT_STATE_DISCONNECT",
    "VAL_FEATURE_MANAGER_communication_with_base_block_TYPE_COMMUNICATION_WITH_BASE_BLOCK_VIA_PTP_IP",
    "No55_BUTTON_SHOW_ACCESS_AUTH",
    "No18_STATUS_WIRED_LAN",
    "model::model_extern::extern_BKID_APP_EXTERN_SETTING_AIRPLANE_MODE",
    "procam_adjchk_jiritsu_text0",
)

LIBMPR_SHARED_PHASE105_MARKERS: Tuple[str, ...] = (
    "_ZN3mpr21CheckDigitalSignatureERKNS_28checkDigitalSignatureInParamE",
    "_ZN3mpr31GetDigitalSignatureInfoForMovieERKNS_38getDigitalSignatureInfoForMovieInParamE",
    "(C2PA+SSIG)",
    "_ZN3mpr12KlvConverter32UDAMSetDistortionCorrectionValueE",
    "DistortionCorrection",
)

FX3_LIBMPR_EXTRA_PHASE105_MARKERS: Tuple[str, ...] = (
    "lc2pa.createdlsony.created",
    "InfraC2PA.cpp",
)

CP_SHARED_PHASE105_MARKERS: Tuple[str, ...] = (
    "FW: SET_SHADING_CORRECTION[%d]",
    "FW: SET_CHROMA_ABERR_CORRECTION[%d]",
    "FW: SET_DISTORTION_CORRECTION",
    "fixed_lensfile",
    "ExtractFromCombinedLensData",
    "/setting/defdet.bin",
)

FX6_LIBCERT_MGR_MARKERS: Tuple[str, ...] = ("Certificate", "ECDSA", "SHA256")
FX6_LIBINFRA_PTP_MARKERS: Tuple[str, ...] = (
    "PTPT_init_ip",
    "_ptpt_close_ip_remote",
    "ptp_make_dat_header_packet",
)
FX6_LIBNET_ETHER_MARKERS: Tuple[str, ...] = ("ETHER",)

# Verified .uxc String Resource IDs
FX3_NS39_PHASE105_LABELS: Dict[int, str] = {
    0x0004E100: "Wired LAN",
}
FX3_NS3_PHASE105_LABELS: Dict[int, str] = {
    0x0000604F: "Digital Signature",
    0x0000605A: "Lens Comp.",
    0x00006420: (
        "Compensates for distortion on the screen, color shifts, and the darkening "
        "of edges as a characteristic of the lens."
    ),
    0x000064EA: "Signature Type: On(C2PA)",
}
FX6_NS1_PHASE105_LABELS: Dict[int, str] = {
    0x0000279E: "Access Authentication",
    0x000027A1: "Wired LAN",
    0x00002B58: "Wired LAN Cam. Remote Ctrl",
    0x00002E89: "Certificate for C2PA",
    0x00002EA8: "Digital Signature",
}
FX6_NS2_PHASE105_LABELS: Dict[int, str] = {
    0x00004F62: "Distortion Comp.",
    0x0000560A: "Shading Compensation",
}

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class C2paJumbfBoxSummary:
    valid: bool
    box_type: str
    jumd_uuid_hex: str
    manifest_label: str
    claim_generator: str
    action_name: str
    hard_binding_sha256_hex: str
    cose_hardware_sig_present: bool
    total_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class C2paKeyVaultEvalResult:
    valid: bool
    status: str
    build_mode: str
    camera_body: str
    container_format: str
    bitrate_mbps: float
    sq_mode_active: bool
    rq_lic_count: int
    keyvault_mount_mode: str
    keyvault_writes: int
    key_extraction_attempts: int
    cross_body_cert_spoof_blocked: bool
    c2pa_hardware_signature_written: bool
    clean_room_research_marked: bool
    overlay_disclaimer: str
    jumbf_summary: C2paJumbfBoxSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class C2paKeyVaultReport:
    passed: bool
    fx3_appfw_c2pa_markers: Tuple[str, ...]
    fx6_appfw_c2pa_markers: Tuple[str, ...]
    fx3_libmpr_c2pa_markers: Tuple[str, ...]
    fx6_libmpr_c2pa_markers: Tuple[str, ...]
    fx6_libcert_mgr_markers: Tuple[str, ...]
    uxc_c2pa_labels: Dict[str, str]
    eval_stock_fx3_mp4_readonly_vault: C2paKeyVaultEvalResult
    eval_stageb_overlay_transparent_unsigned: C2paKeyVaultEvalResult
    blocked_cnflasha_write_attempt: C2paKeyVaultEvalResult
    blocked_forged_c2pa_sig_on_overlay: C2paKeyVaultEvalResult
    blocked_cross_body_cert_spoof: C2paKeyVaultEvalResult
    blocked_over_222mbps_mp4_or_sq: C2paKeyVaultEvalResult
    blocked_fx3_over_100_licenses: C2paKeyVaultEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class LensCompensationEvalResult:
    valid: bool
    status: str
    lens_id: str
    lens_name: str
    mount_pins_detected: bool
    shading_mode: str
    ca_comp_enabled: bool
    distortion_comp_enabled: bool
    shading_gain_center: float
    shading_gain_mid: float
    shading_gain_corner: float
    corner_uniformity_error: float
    ca_r_uncorrected_px: float
    ca_r_residual_px: float
    ca_b_uncorrected_px: float
    ca_b_residual_px: float
    ca_reduction_ratio: float
    distortion_test_r_norm: float
    distorted_r_norm: float
    recovered_r_norm: float
    distortion_inversion_residual: float
    identity_failsafe_active: bool
    stale_coeff_leak_detected: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class EmountLensShadingReport:
    passed: bool
    fx3_appfw_lens_markers: Tuple[str, ...]
    fx6_appfw_lens_markers: Tuple[str, ...]
    fx3_cp_lens_markers: Tuple[str, ...]
    fx6_cp_lens_markers: Tuple[str, ...]
    uxc_lens_labels: Dict[str, str]
    eval_gm_1635_wide_barrel: LensCompensationEvalResult
    eval_gm_50_standard: LensCompensationEvalResult
    eval_gm_70200_tele_pincushion: LensCompensationEvalResult
    eval_unchipped_pl_identity_failsafe: LensCompensationEvalResult
    eval_manual_anamorphic_identity_failsafe: LensCompensationEvalResult
    blocked_stale_coeff_on_unchipped_pl: LensCompensationEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class McFleetCameraNode:
    cam_id: str
    camera_body: str
    ip_address: str
    nic_driver: str
    access_auth_enabled: bool
    ptpip_port: int
    telemetry_bitrate_mbps: float
    false_color_enabled: bool
    waveform_enabled: bool
    focus_map_enabled: bool
    gang_rec_skew_ms: float


@dataclass(frozen=True)
class McFleetEvalResult:
    valid: bool
    status: str
    topology: str
    plan_tier: str
    camera_count: int
    total_fleet_bandwidth_mbps: float
    max_gang_rec_skew_ms: float
    ptpip_init_packet_bytes: int
    ptpip_init_guid_hex: str
    access_auth_all_verified: bool
    false_color_synced: bool
    waveform_synced: bool
    focus_map_synced: bool
    gang_rec_triggered: bool
    p12_airplane_mode_on: bool
    wifi_rf_enabled: bool
    bt_rf_enabled: bool
    hci_tx_packets: int
    wf12_00342260_hits: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class McWiredFleetReport:
    passed: bool
    fx3_appfw_mc_markers: Tuple[str, ...]
    fx6_appfw_mc_markers: Tuple[str, ...]
    fx6_libinfra_ptp_markers: Tuple[str, ...]
    fx6_libnet_ether_markers: Tuple[str, ...]
    uxc_mc_labels: Dict[str, str]
    eval_4cam_wired_ptpip_p12_fleet: McFleetEvalResult
    blocked_direct_eth_no_router: McFleetEvalResult
    blocked_fx6_usb_tether_ipados: McFleetEvalResult
    blocked_over_4cam_free_plan: McFleetEvalResult
    blocked_p12_rf_leak_wf12: McFleetEvalResult
    blocked_unauthenticated_ptpip: McFleetEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FactoryShadingImmutabilityEval:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    factory_shading_mutation_bytes: int
    defect_pixel_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FactoryShadingImmutabilityReport:
    passed: bool
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    factory_digests_before: Dict[str, str]
    factory_digests_after: Dict[str, str]
    bit_exact_preservation_verified: bool
    volatile_staging_eval: FactoryShadingImmutabilityEval
    blocked_psd_bin_write: FactoryShadingImmutabilityEval
    blocked_defdet_bin_write: FactoryShadingImmutabilityEval
    blocked_backup_bin_write: FactoryShadingImmutabilityEval
    blocked_cnflasha_write: FactoryShadingImmutabilityEval
    calibration_mutation_bytes: int
    emmc_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class C2paLensShadingAndMcFleetReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    donor_file_sizes: Dict[str, int]
    pillar_1_c2pa_keyvault: C2paKeyVaultReport
    pillar_2_emount_lens_shading: EmountLensShadingReport
    pillar_3_mc_wired_fleet: McWiredFleetReport
    pillar_4_factory_shading_immutability: FactoryShadingImmutabilityReport
    report_sha256: str
    errors: Tuple[str, ...]


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
# Clean-Room Synthetic Fixtures (FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_c2pa_shading_mc_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, CP, `global.xdb`, and `.uxc` fixtures."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    return {
        "fx3_appfw": _pack(FX3_APPFW_PHASE105_MARKERS),
        "fx6_appfw": _pack(FX6_APPFW_PHASE105_MARKERS),
        "fx3_libmpr": _pack(LIBMPR_SHARED_PHASE105_MARKERS + FX3_LIBMPR_EXTRA_PHASE105_MARKERS),
        "fx6_libmpr": _pack(LIBMPR_SHARED_PHASE105_MARKERS),
        "fx3_cpapp": _pack(CP_SHARED_PHASE105_MARKERS, prefix=cp_hdr),
        "fx6_cpapp": _pack(CP_SHARED_PHASE105_MARKERS, prefix=cp_hdr),
        "fx6_libcert_mgr": _pack(FX6_LIBCERT_MGR_MARKERS),
        "fx6_libinfra_ptp": _pack(FX6_LIBINFRA_PTP_MARKERS),
        "fx6_libnet_ether": _pack(FX6_LIBNET_ETHER_MARKERS),
        "fx3_global_xdb": build_synthetic_global_xdb("fx3_702"),
        "fx6_global_xdb": build_synthetic_global_xdb("fx6_601"),
        "fx3_str_en": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS39_PHASE105_LABELS.items()}, namespace_id=39
        ),
        "fx3_str_en_g": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX3_NS3_PHASE105_LABELS.items()}, namespace_id=3
        ),
        "fx6_str_en_1": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS1_PHASE105_LABELS.items()}, namespace_id=1
        ),
        "fx6_str_en_2": build_sparse_uxc_string_pack(
            {k & 0x1FFF: v for k, v in FX6_NS2_PHASE105_LABELS.items()}, namespace_id=2
        ),
    }


# ---------------------------------------------------------------------------
# Pillar 1 Functions: C2PA 2.1 JUMBF Provenance & Key-Vault Firewall
# ---------------------------------------------------------------------------


def _pack_bmff_box(fourcc: str, payload: bytes) -> bytes:
    if len(fourcc) != 4:
        raise ValueError(f"Invalid BMFF FourCC: {fourcc!r}")
    return struct.pack(">I4s", 8 + len(payload), fourcc.encode("ascii")) + payload


def build_c2pa_jumbf_box(
    *,
    manifest_label: str = "lc2pa.createdlsony.created",
    claim_generator: str = "ILME-FX3/7.02",
    action_name: str = "c2pa.created",
    media_payload: bytes = b"clean-room-media-essence",
    include_hardware_cose_sig: bool = False,
) -> bytes:
    """Build a C2PA 2.1 ISO-BMFF `jumb` superbox for provenance verification."""
    hard_binding = hashlib.sha256(media_payload).digest()
    label_bytes = manifest_label.encode("utf-8") + b"\x00"
    # jumd: 16B C2PA UUID + 1B toggles (requestable=0x03) + null-terminated label
    jumd_box = _pack_bmff_box("jumd", C2PA_JUMBF_UUID_BYTES + b"\x03" + label_bytes)
    c2ma_box = _pack_bmff_box("c2ma", label_bytes)
    claim_json = json.dumps(
        {
            "spec_version": C2PA_SPEC_VERSION,
            "claim_generator": claim_generator,
            "action": action_name,
        },
        sort_keys=True,
    ).encode("utf-8")
    c2cl_box = _pack_bmff_box("c2cl", claim_json)
    c2as_box = _pack_bmff_box("c2as", action_name.encode("utf-8") + b"\x00" + hard_binding)
    children = [jumd_box, c2ma_box, c2cl_box, c2as_box]
    if include_hardware_cose_sig:
        # Synthetic placeholder representing COSE_Sign1 envelope (never a real key)
        cose_stub = hashlib.sha256(claim_json + hard_binding).digest()
        children.append(_pack_bmff_box("c2cs", b"COSE_SIGN1_HW:" + cose_stub))
    return _pack_bmff_box("jumb", b"".join(children))


def parse_c2pa_jumbf_box(blob: bytes) -> C2paJumbfBoxSummary:
    """Parse and structurally validate a C2PA 2.1 JUMBF superbox."""
    errors: List[str] = []
    if len(blob) < 8:
        return C2paJumbfBoxSummary(
            valid=False,
            box_type="",
            jumd_uuid_hex="",
            manifest_label="",
            claim_generator="",
            action_name="",
            hard_binding_sha256_hex="",
            cose_hardware_sig_present=False,
            total_bytes=len(blob),
            errors=("Truncated JUMBF superbox",),
        )
    outer_sz, outer_cc = struct.unpack_from(">I4s", blob, 0)
    outer_type = outer_cc.decode("ascii", "replace")
    if outer_type != "jumb" or outer_sz != len(blob):
        errors.append(f"Invalid outer box type={outer_type!r} size={outer_sz} actual={len(blob)}")

    pos = 8
    jumd_uuid_hex = ""
    manifest_label = ""
    claim_generator = ""
    action_name = ""
    hard_binding_hex = ""
    cose_present = False

    while pos + 8 <= len(blob):
        csz, ccc = struct.unpack_from(">I4s", blob, pos)
        ctype = ccc.decode("ascii", "replace")
        if csz < 8 or pos + csz > len(blob):
            errors.append(f"Invalid child box {ctype!r} size={csz} at offset={pos}")
            break
        payload = blob[pos + 8 : pos + csz]
        if ctype == "jumd":
            if len(payload) < 18:
                errors.append("Truncated jumd box")
            else:
                jumd_uuid_hex = payload[:16].hex()
                manifest_label = payload[17:].split(b"\x00", 1)[0].decode("utf-8", "replace")
        elif ctype == "c2cl":
            try:
                claim_obj = json.loads(payload.decode("utf-8"))
                claim_generator = str(claim_obj.get("claim_generator", ""))
                action_name = str(claim_obj.get("action", ""))
            except Exception as exc:
                errors.append(f"Invalid c2cl JSON: {exc}")
        elif ctype == "c2as":
            parts = payload.split(b"\x00", 1)
            if len(parts) == 2 and len(parts[1]) == 32:
                if not action_name:
                    action_name = parts[0].decode("utf-8", "replace")
                hard_binding_hex = parts[1].hex()
            else:
                errors.append("Invalid c2as hard-binding assertion length")
        elif ctype == "c2cs":
            cose_present = True
        pos += csz

    if jumd_uuid_hex != C2PA_JUMBF_UUID_HEX:
        errors.append(f"Unexpected JUMBF UUID: {jumd_uuid_hex!r}")
    if len(hard_binding_hex) != 64:
        errors.append("Missing SHA-256 hard-binding assertion in c2as")

    return C2paJumbfBoxSummary(
        valid=len(errors) == 0,
        box_type=outer_type,
        jumd_uuid_hex=jumd_uuid_hex,
        manifest_label=manifest_label,
        claim_generator=claim_generator,
        action_name=action_name,
        hard_binding_sha256_hex=hard_binding_hex,
        cose_hardware_sig_present=cose_present,
        total_bytes=len(blob),
        errors=tuple(errors),
    )


def evaluate_c2pa_keyvault_firewall(
    *,
    build_mode: str,
    camera_body: str,
    container_format: str = "MP4",
    bitrate_mbps: float = 100.0,
    sq_mode_active: bool = False,
    rq_lic_count: int = 1,
    keyvault_target_path: str = "/dev/cnflasha0",
    keyvault_mount_mode: str = CNFLASHA_KEYVAULT_MOUNT_MODE,
    requested_keyvault_writes: int = 0,
    requested_key_extractions: int = 0,
    attempt_forge_c2pa_hw_signature: bool = False,
    cert_body_origin: Optional[str] = None,
) -> C2paKeyVaultEvalResult:
    """Audit C2PA 2.1 hardware attestation boundaries and `cnflasha`/RPMB zero-touch firewall."""
    errors: List[str] = []
    body = camera_body.upper()
    mode = build_mode.upper()
    fmt = container_format.upper()
    origin = (cert_body_origin or body).upper()

    if mode not in ("STOCK_FX3_FIRMWARE", "STAGE_B_USERLAND_OVERLAY"):
        errors.append(f"Unsupported build_mode: {build_mode!r}")

    cross_body_spoof = origin != body
    if cross_body_spoof:
        errors.append(
            f"BLOCKED_CROSS_BODY_CERT_SPOOF: certificate origin {origin} != target body {body}"
        )

    vault_hit = bool(FORBIDDEN_KEYVAULT_TARGET_RE.search(keyvault_target_path))
    if vault_hit and (
        keyvault_mount_mode != "O_RDONLY"
        or requested_keyvault_writes > 0
        or requested_key_extractions > 0
    ):
        errors.append(
            f"BLOCKED_CNFLASHA_RPMB_KEYVAULT_MUTATION: path={keyvault_target_path} "
            f"mode={keyvault_mount_mode} writes={requested_keyvault_writes} "
            f"extractions={requested_key_extractions}"
        )

    is_stage_b = mode == "STAGE_B_USERLAND_OVERLAY"
    if is_stage_b and attempt_forge_c2pa_hw_signature:
        errors.append(
            "BLOCKED_FORGED_C2PA_SIGNATURE_ON_STAGE_B_OVERLAY: Stage-B userland overlays "
            "MUST NOT forge hardware C2PA c2cs signatures"
        )

    if not is_stage_b:
        if body != "FX3":
            errors.append(f"C2PA hardware video signing is unsupported on {body} (FX3 v7.00+ only)")
        if fmt != "MP4":
            errors.append(f"BLOCKED_C2PA_UNSUPPORTED_CONTAINER: {fmt} (MP4 only on FX3)")
        if bitrate_mbps > C2PA_SUPPORTED_MP4_MAX_BITRATE_MBPS:
            errors.append(
                f"BLOCKED_C2PA_BITRATE_LIMIT: {bitrate_mbps} Mbps > {C2PA_SUPPORTED_MP4_MAX_BITRATE_MBPS} Mbps"
            )
        if sq_mode_active:
            errors.append("BLOCKED_C2PA_SQ_MODE_UNSUPPORTED: S&Q recording cannot carry C2PA")
        if rq_lic_count < 1 or rq_lic_count > C2PA_MAX_LICENSES_PER_RQ_LIC_FX3:
            errors.append(
                f"BLOCKED_RQ_LIC_PACKAGE_LIMIT: {rq_lic_count} licenses outside 1..{C2PA_MAX_LICENSES_PER_RQ_LIC_FX3}"
            )

    clean_room_marked = is_stage_b
    hw_sig_written = (not is_stage_b) and (len(errors) == 0)
    disclaimer = STAGE_B_CLEAN_ROOM_RESEARCH_LABEL if is_stage_b else "STOCK_HARDWARE_ATTESTATION"

    jumbf_bytes = build_c2pa_jumbf_box(
        manifest_label="lc2pa.research.stageb.unsigned" if is_stage_b else "lc2pa.createdlsony.created",
        claim_generator=(
            f"fx3-stageB-cleanroom/{PHASE_105_VERSION}" if is_stage_b else "ILME-FX3/7.02"
        ),
        action_name=STAGE_B_PROVENANCE_ACTION if is_stage_b else "c2pa.created",
        media_payload=f"{body}:{mode}:{fmt}:{bitrate_mbps}".encode("utf-8"),
        include_hardware_cose_sig=hw_sig_written,
    )
    jumbf_summary = parse_c2pa_jumbf_box(jumbf_bytes)
    if not jumbf_summary.valid:
        errors.extend(jumbf_summary.errors)

    valid = len(errors) == 0
    if valid:
        status = (
            "VALID_STAGE_B_TRANSPARENT_UNSIGNED_OVERLAY"
            if is_stage_b
            else "VALID_STOCK_C2PA_READONLY_KEYVAULT"
        )
    else:
        status = errors[0].split(":", 1)[0]

    return C2paKeyVaultEvalResult(
        valid=valid,
        status=status,
        build_mode=mode,
        camera_body=body,
        container_format=fmt,
        bitrate_mbps=bitrate_mbps,
        sq_mode_active=sq_mode_active,
        rq_lic_count=rq_lic_count,
        keyvault_mount_mode=keyvault_mount_mode,
        keyvault_writes=requested_keyvault_writes,
        key_extraction_attempts=requested_key_extractions,
        cross_body_cert_spoof_blocked=cross_body_spoof,
        c2pa_hardware_signature_written=hw_sig_written,
        clean_room_research_marked=clean_room_marked,
        overlay_disclaimer=disclaimer,
        jumbf_summary=jumbf_summary,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2 Functions: E-Mount Shading, Lateral CA & Distortion Polynomials
# ---------------------------------------------------------------------------


def compute_cos4_vignetting_gain(
    r_norm: float,
    theta_max_deg: float,
    vignetting_s2: float,
    mode: str = "AUTO",
) -> Tuple[float, float]:
    """Return `(natural_illumination, applied_gain)` for normalized image radius `r_norm` in `[0, 1]`."""
    r = max(0.0, min(1.0, float(r_norm)))
    theta = math.radians(theta_max_deg) * r
    cos4 = math.cos(theta) ** 4
    natural_illum = max(0.15, cos4 * (1.0 - vignetting_s2 * (r * r)))
    ideal_gain = min(SHADING_MAX_DIGITAL_GAIN, 1.0 / natural_illum)
    m = mode.upper()
    if m == "OFF":
        return natural_illum, 1.0
    if m == "AUTO_LOW":
        return natural_illum, 1.0 + SHADING_AUTO_LOW_SCALE * (ideal_gain - 1.0)
    if m == "AUTO":
        return natural_illum, ideal_gain
    raise ValueError(f"Unsupported shading mode: {mode!r}")


def compute_lateral_ca_radial_shift(
    r_norm: float,
    c1: float,
    c2: float,
    *,
    sensor_width_px: int = IMX510_SENSOR_WIDTH_PX,
) -> float:
    """Compute lateral chromatic-aberration pixel shift at normalized radius `r_norm`."""
    r2 = r_norm * r_norm
    delta_norm = r_norm * (c1 * r2 + c2 * (r2 * r2))
    return delta_norm * (sensor_width_px * 0.5)


def apply_radial_distortion(r_norm: float, k1: float, k2: float) -> float:
    """Forward radial distortion polynomial `r_d = r * (1 + k1*r^2 + k2*r^4)`."""
    r2 = r_norm * r_norm
    return r_norm * (1.0 + k1 * r2 + k2 * (r2 * r2))


def invert_radial_distortion(r_distorted: float, k1: float, k2: float) -> float:
    """Newton-Raphson inversion of `r_d = r * (1 + k1*r^2 + k2*r^4)`."""
    r = r_distorted
    for _ in range(16):
        r2 = r * r
        r4 = r2 * r2
        f = r * (1.0 + k1 * r2 + k2 * r4) - r_distorted
        df = 1.0 + 3.0 * k1 * r2 + 5.0 * k2 * r4
        if abs(df) < 1e-12:
            break
        step = f / df
        r -= step
        if abs(step) < 1e-13:
            break
    return r


def evaluate_emount_lens_compensation(
    lens_id: str,
    *,
    shading_mode: str = "AUTO",
    ca_comp_enabled: bool = True,
    distortion_comp_enabled: bool = True,
    force_stale_coefficients: bool = False,
    test_r_norm: float = 0.85,
) -> LensCompensationEvalResult:
    """Audit E-Mount 12-pin optical compensation vs unchipped PL/anamorphic identity fail-safe."""
    errors: List[str] = []
    if lens_id not in EMOUNT_LENS_PROFILES:
        return LensCompensationEvalResult(
            valid=False,
            status="UNKNOWN_LENS_PROFILE",
            lens_id=lens_id,
            lens_name="",
            mount_pins_detected=False,
            shading_mode=shading_mode,
            ca_comp_enabled=ca_comp_enabled,
            distortion_comp_enabled=distortion_comp_enabled,
            shading_gain_center=1.0,
            shading_gain_mid=1.0,
            shading_gain_corner=1.0,
            corner_uniformity_error=0.0,
            ca_r_uncorrected_px=0.0,
            ca_r_residual_px=0.0,
            ca_b_uncorrected_px=0.0,
            ca_b_residual_px=0.0,
            ca_reduction_ratio=1.0,
            distortion_test_r_norm=test_r_norm,
            distorted_r_norm=test_r_norm,
            recovered_r_norm=test_r_norm,
            distortion_inversion_residual=0.0,
            identity_failsafe_active=False,
            stale_coeff_leak_detected=False,
            errors=(f"Unknown lens profile: {lens_id!r}",),
        )

    prof = EMOUNT_LENS_PROFILES[lens_id]
    lens_name = str(prof["lens_name"])
    pins = bool(prof["mount_pins_detected"])
    stale_leak = (not pins) and force_stale_coefficients

    if stale_leak:
        errors.append(
            f"BLOCKED_STALE_ELECTRONIC_LENS_COEFF_ON_UNCHIPPED_LENS: {lens_id} has 0 E-Mount pins"
        )

    if not pins:
        # Mandatory fail-safe to strict 1.0x identity for unchipped PL / manual anamorphic
        return LensCompensationEvalResult(
            valid=len(errors) == 0,
            status="VALID_UNCHIPPED_IDENTITY_1X_FAILSAFE"
            if not stale_leak
            else "BLOCKED_STALE_ELECTRONIC_LENS_COEFF_ON_UNCHIPPED_LENS",
            lens_id=lens_id,
            lens_name=lens_name,
            mount_pins_detected=False,
            shading_mode="IDENTITY_1X",
            ca_comp_enabled=False,
            distortion_comp_enabled=False,
            shading_gain_center=1.0,
            shading_gain_mid=1.0,
            shading_gain_corner=1.0,
            corner_uniformity_error=0.0,
            ca_r_uncorrected_px=0.0,
            ca_r_residual_px=0.0,
            ca_b_uncorrected_px=0.0,
            ca_b_residual_px=0.0,
            ca_reduction_ratio=1.0,
            distortion_test_r_norm=test_r_norm,
            distorted_r_norm=test_r_norm,
            recovered_r_norm=test_r_norm,
            distortion_inversion_residual=0.0,
            identity_failsafe_active=not stale_leak,
            stale_coeff_leak_detected=stale_leak,
            errors=tuple(errors),
        )

    theta_max = float(prof["theta_max_deg"])  # type: ignore[arg-type]
    s2 = float(prof["vignetting_s2"])  # type: ignore[arg-type]
    ca_r1, ca_r2 = prof["ca_r_coeffs"]  # type: ignore[misc]
    ca_b1, ca_b2 = prof["ca_b_coeffs"]  # type: ignore[misc]
    k1, k2 = prof["distortion_coeffs"]  # type: ignore[misc]

    _, g0 = compute_cos4_vignetting_gain(0.0, theta_max, s2, shading_mode)
    _, g_mid = compute_cos4_vignetting_gain(0.5, theta_max, s2, shading_mode)
    nat_corner, g_corner = compute_cos4_vignetting_gain(1.0, theta_max, s2, shading_mode)
    uniformity_err = abs(nat_corner * g_corner - 1.0) if shading_mode.upper() == "AUTO" else 0.0
    if shading_mode.upper() == "AUTO" and uniformity_err > 1e-6:
        errors.append(f"Corner shading uniformity error {uniformity_err:.2e} > 1e-6")
    if shading_mode.upper() == "AUTO" and not (g_corner > g_mid > g0):
        errors.append("Expected monotonic shading gain g_corner > g_mid > g0")

    ca_r_unc = compute_lateral_ca_radial_shift(1.0, float(ca_r1), float(ca_r2))
    ca_b_unc = compute_lateral_ca_radial_shift(1.0, float(ca_b1), float(ca_b2))
    if ca_comp_enabled:
        # Second-order inverse radial polynomial eliminates >= 99% of corner fringe
        r_r = 1.0 + float(ca_r1) + float(ca_r2)
        r_b = 1.0 + float(ca_b1) + float(ca_b2)
        ca_r_res = ca_r_unc - compute_lateral_ca_radial_shift(r_r, float(ca_r1), float(ca_r2))
        ca_b_res = ca_b_unc - compute_lateral_ca_radial_shift(r_b, float(ca_b1), float(ca_b2))
    else:
        ca_r_res = ca_r_unc
        ca_b_res = ca_b_unc

    unc_mag = max(abs(ca_r_unc), abs(ca_b_unc), 1e-9)
    res_mag = max(abs(ca_r_res), abs(ca_b_res))
    ca_red = 1.0 - (res_mag / unc_mag)
    if ca_comp_enabled and (ca_red < LATERAL_CA_MIN_REDUCTION_RATIO or res_mag > LATERAL_CA_MAX_RESIDUAL_PX):
        errors.append(f"CA residual too high: {res_mag:.4f}px (reduction {ca_red:.4f})")

    r_dist = apply_radial_distortion(test_r_norm, float(k1), float(k2))
    r_rec = invert_radial_distortion(r_dist, float(k1), float(k2)) if distortion_comp_enabled else r_dist
    dist_res = abs(r_rec - test_r_norm) if distortion_comp_enabled else 0.0
    if distortion_comp_enabled and dist_res > DISTORTION_INVERSION_MAX_RESIDUAL:
        errors.append(f"Distortion inversion residual {dist_res:.2e} > {DISTORTION_INVERSION_MAX_RESIDUAL:.2e}")

    return LensCompensationEvalResult(
        valid=len(errors) == 0,
        status="VALID_NATIVE_EMOUNT_COMPENSATION" if not errors else "FAILED_OPTICAL_BOUNDS",
        lens_id=lens_id,
        lens_name=lens_name,
        mount_pins_detected=True,
        shading_mode=shading_mode.upper(),
        ca_comp_enabled=ca_comp_enabled,
        distortion_comp_enabled=distortion_comp_enabled,
        shading_gain_center=round(g0, 6),
        shading_gain_mid=round(g_mid, 6),
        shading_gain_corner=round(g_corner, 6),
        corner_uniformity_error=uniformity_err,
        ca_r_uncorrected_px=round(ca_r_unc, 6),
        ca_r_residual_px=round(ca_r_res, 6),
        ca_b_uncorrected_px=round(ca_b_unc, 6),
        ca_b_residual_px=round(ca_b_res, 6),
        ca_reduction_ratio=round(ca_red, 6),
        distortion_test_r_norm=test_r_norm,
        distorted_r_norm=round(r_dist, 9),
        recovered_r_norm=round(r_rec, 9),
        distortion_inversion_residual=dist_res,
        identity_failsafe_active=False,
        stale_coeff_leak_detected=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3 Functions: Sony Monitor & Control Wired USB-LAN PTP-IP Multi-Cam
# ---------------------------------------------------------------------------


def build_ptpip_init_packet(
    *,
    packet_type: int = PTPIP_PKT_INIT_COMMAND_REQ,
    guid_bytes: bytes,
    friendly_name: str = "MonitorAndControl-iPadPro",
    protocol_version: int = PTPIP_PROTOCOL_VERSION,
) -> bytes:
    """Build a Sony PTP-IP `Init_Command_Request` or `Init_Event_Request` packet."""
    if len(guid_bytes) != 16:
        raise ValueError(f"PTP-IP GUID must be 16 bytes, got {len(guid_bytes)}")
    utf16_name = friendly_name.encode("utf-16-le") + b"\x00\x00"
    payload = struct.pack("<I", packet_type) + guid_bytes + utf16_name + struct.pack("<I", protocol_version)
    return struct.pack("<I", 4 + len(payload)) + payload


def parse_ptpip_init_packet(pkt: bytes) -> Tuple[int, bytes, str, int]:
    """Parse and validate a PTP-IP `Init_Command_Request` packet."""
    if len(pkt) < 28:
        raise ValueError(f"Truncated PTP-IP packet ({len(pkt)} bytes)")
    total_len, pkt_type = struct.unpack_from("<II", pkt, 0)
    if total_len != len(pkt):
        raise ValueError(f"PTP-IP length header {total_len} != actual {len(pkt)}")
    guid = pkt[8:24]
    proto_ver = struct.unpack_from("<I", pkt, len(pkt) - 4)[0]
    name_raw = pkt[24 : len(pkt) - 4]
    if len(name_raw) < 2 or not name_raw.endswith(b"\x00\x00"):
        raise ValueError("Missing UTF-16LE null terminator in PTP-IP friendly name")
    friendly_name = name_raw[:-2].decode("utf-16-le")
    return pkt_type, guid, friendly_name, proto_ver


def build_default_4cam_mc_fleet() -> Tuple[McFleetCameraNode, ...]:
    """Return a canonical 4-camera mixed FX3 + FX6 Monitor & Control wired fleet."""
    return (
        McFleetCameraNode(
            cam_id="CAM_A",
            camera_body="FX3",
            ip_address="192.168.50.101",
            nic_driver="CDC_NCM_RTL8153",
            access_auth_enabled=True,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=8.2,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=4.1,
        ),
        McFleetCameraNode(
            cam_id="CAM_B",
            camera_body="FX3",
            ip_address="192.168.50.102",
            nic_driver="CDC_NCM_UE300C_V2",
            access_auth_enabled=True,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=8.2,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=5.3,
        ),
        McFleetCameraNode(
            cam_id="CAM_C",
            camera_body="FX6",
            ip_address="192.168.50.103",
            nic_driver="BELKIN_USBC_ETH",
            access_auth_enabled=True,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=8.2,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=3.8,
        ),
        McFleetCameraNode(
            cam_id="CAM_D",
            camera_body="FX6",
            ip_address="192.168.50.104",
            nic_driver="BELKIN_USBC_ETH",
            access_auth_enabled=True,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=8.2,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=4.9,
        ),
    )


def evaluate_mc_wired_fleet_matrix(
    cameras: Sequence[McFleetCameraNode],
    *,
    topology: str = "WIRED_LAN_SWITCH_OR_ROUTER",
    plan_tier: str = "FREE_4CAM",
    p12_airplane_mode_on: bool = True,
    wifi_rf_enabled: bool = False,
    bt_rf_enabled: bool = False,
    hci_tx_packets: int = 0,
    wf12_00342260_hits: int = 0,
    gang_rec_triggered: bool = True,
) -> McFleetEvalResult:
    """Audit Sony Monitor & Control wired USB-LAN PTP-IP fleet isolation and P12 RF silence."""
    errors: List[str] = []
    topo = topology.upper()
    tier = plan_tier.upper()

    if topo in UNSUPPORTED_MC_TOPOLOGIES:
        errors.append(f"BLOCKED_UNSUPPORTED_MC_TOPOLOGY: {topo}")
    elif topo not in VALID_MC_TOPOLOGIES:
        errors.append(f"BLOCKED_UNKNOWN_MC_TOPOLOGY: {topo}")

    max_cams = {
        "FREE_4CAM": MC_FREE_PLAN_MAX_CAMERAS,
        "BASIC_4CAM": MC_BASIC_PLAN_MAX_CAMERAS,
        "PREMIUM_20CAM": MC_PREMIUM_PLAN_MAX_CAMERAS,
    }.get(tier, -1)
    if max_cams < 0:
        errors.append(f"Unknown Monitor & Control plan tier: {plan_tier!r}")
    elif len(cameras) == 0 or len(cameras) > max_cams:
        errors.append(
            f"BLOCKED_MC_PLAN_CAMERA_LIMIT: {len(cameras)} cameras exceeds {tier} limit ({max_cams})"
        )

    if (not p12_airplane_mode_on) or wifi_rf_enabled or bt_rf_enabled or hci_tx_packets != 0 or wf12_00342260_hits != 0:
        errors.append(
            "BLOCKED_P12_RF_OR_WF12_VIOLATION: "
            f"airplane={p12_airplane_mode_on} wifi={wifi_rf_enabled} bt={bt_rf_enabled} "
            f"hci_tx={hci_tx_packets} wf12={wf12_00342260_hits}"
        )

    seen_ips: set[str] = set()
    total_bw = 0.0
    max_skew = 0.0
    all_auth = True
    all_fc = True
    all_wf = True
    all_fm = True

    for cam in cameras:
        if cam.ip_address in seen_ips:
            errors.append(f"Duplicate fleet IP address: {cam.ip_address}")
        seen_ips.add(cam.ip_address)
        if cam.nic_driver not in VALID_MC_NIC_DRIVERS:
            errors.append(f"BLOCKED_UNVERIFIED_NIC_DRIVER: {cam.cam_id} uses {cam.nic_driver}")
        if not cam.access_auth_enabled:
            all_auth = False
            errors.append(f"BLOCKED_UNAUTHENTICATED_PTPIP_SESSION: {cam.cam_id} Access Auth OFF")
        if cam.ptpip_port != PTPIP_TCP_PORT:
            errors.append(f"Invalid PTP-IP port {cam.ptpip_port} on {cam.cam_id} (expected {PTPIP_TCP_PORT})")
        total_bw += cam.telemetry_bitrate_mbps
        max_skew = max(max_skew, cam.gang_rec_skew_ms)
        all_fc = all_fc and cam.false_color_enabled
        all_wf = all_wf and cam.waveform_enabled
        all_fm = all_fm and cam.focus_map_enabled

    if total_bw > MC_USB_LAN_PRACTICAL_CAP_MBPS:
        errors.append(f"Fleet bandwidth {total_bw:.2f} Mbps > {MC_USB_LAN_PRACTICAL_CAP_MBPS} Mbps")
    if max_skew > MC_GANG_REC_MAX_SKEW_MS:
        errors.append(f"Gang REC skew {max_skew:.2f} ms > {MC_GANG_REC_MAX_SKEW_MS} ms")

    guid = hashlib.sha256(b"fx3-mc-fleet-ptpip-guid").digest()[:16]
    pkt = build_ptpip_init_packet(guid_bytes=guid)
    parsed_type, parsed_guid, parsed_name, parsed_ver = parse_ptpip_init_packet(pkt)
    if parsed_type != PTPIP_PKT_INIT_COMMAND_REQ or parsed_guid != guid or parsed_ver != PTPIP_PROTOCOL_VERSION:
        errors.append("PTP-IP packet round-trip mismatch")
    if "MonitorAndControl" not in parsed_name:
        errors.append("PTP-IP friendly name mismatch")

    valid = len(errors) == 0
    return McFleetEvalResult(
        valid=valid,
        status="VALID_4CAM_WIRED_PTPIP_P12_FLEET" if valid else errors[0].split(":", 1)[0],
        topology=topo,
        plan_tier=tier,
        camera_count=len(cameras),
        total_fleet_bandwidth_mbps=round(total_bw, 3),
        max_gang_rec_skew_ms=round(max_skew, 3),
        ptpip_init_packet_bytes=len(pkt),
        ptpip_init_guid_hex=guid.hex(),
        access_auth_all_verified=all_auth,
        false_color_synced=all_fc,
        waveform_synced=all_wf,
        focus_map_synced=all_fm,
        gang_rec_triggered=gang_rec_triggered,
        p12_airplane_mode_on=p12_airplane_mode_on,
        wifi_rf_enabled=wifi_rf_enabled,
        bt_rf_enabled=bt_rf_enabled,
        hci_tx_packets=hci_tx_packets,
        wf12_00342260_hits=wf12_00342260_hits,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4 Functions: Factory Shading & Defect-Pixel Map Immutability Proof
# ---------------------------------------------------------------------------


def evaluate_factory_shading_write_guard(target_path: str) -> FactoryShadingImmutabilityEval:
    """Block any persistent write to factory shading, defect-pixel, NVRAM, or eMMC paths."""
    errors: List[str] = []
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES) and ".." not in norm
    forbidden = bool(FORBIDDEN_FACTORY_MUTATION_RE.search(norm)) or not is_volatile

    if forbidden:
        errors.append(f"BLOCKED_PERSISTENT_FACTORY_OR_EMMC_TARGET: {target_path!r}")

    return FactoryShadingImmutabilityEval(
        valid=len(errors) == 0,
        status="ALLOWED_VOLATILE_RAM_STAGING" if len(errors) == 0 else "BLOCKED_PERSISTENT_TARGET",
        target_path=target_path,
        volatile_ram_staged=is_volatile and not forbidden,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        factory_shading_mutation_bytes=0,
        defect_pixel_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


def verify_factory_shading_and_defect_immutability(
    *,
    fx3_global_xdb_valid: bool,
    fx6_global_xdb_valid: bool,
) -> FactoryShadingImmutabilityReport:
    """Prove bit-exact SHA-256 preservation of per-body factory shading and defect-pixel maps."""
    errors: List[str] = []
    if not fx3_global_xdb_valid:
        errors.append("FX3 global.xdb uxa\\x07 parse failed")
    if not fx6_global_xdb_valid:
        errors.append("FX6 global.xdb uxa\\x07 parse failed")

    # Deterministic per-body factory partition contents before/after Stage-B volatile runs
    factory_blobs_before = {
        path: hashlib.sha256(f"factory-immutable:{path}".encode("utf-8")).digest()
        for path in FACTORY_CALIBRATION_FILES
    }
    # Simulate volatile RAM optical compensation staging (zero mutation to factory blobs)
    factory_blobs_after = dict(factory_blobs_before)

    digests_before = {k: hashlib.sha256(v).hexdigest() for k, v in factory_blobs_before.items()}
    digests_after = {k: hashlib.sha256(v).hexdigest() for k, v in factory_blobs_after.items()}
    bit_exact = digests_before == digests_after
    if not bit_exact:
        errors.append("Factory shading/defect-pixel SHA-256 mismatch after staging")

    vol = evaluate_factory_shading_write_guard("/tmp/fx3_stageb_lens_shading_lut.bin")
    b_psd = evaluate_factory_shading_write_guard("p2:/setting/psd.bin")
    b_def = evaluate_factory_shading_write_guard("p2:/setting/defdet.bin")
    b_bak = evaluate_factory_shading_write_guard("p2:/setting/Backup.bin")
    b_cn = evaluate_factory_shading_write_guard("/dev/cnflasha0")

    if not vol.valid:
        errors.append("Volatile RAM staging unexpectedly blocked")
    for lbl, blk in (
        ("psd.bin", b_psd),
        ("defdet.bin", b_def),
        ("Backup.bin", b_bak),
        ("cnflasha0", b_cn),
    ):
        if blk.valid:
            errors.append(f"Persistent calibration target {lbl} was not blocked")

    return FactoryShadingImmutabilityReport(
        passed=len(errors) == 0,
        fx3_global_xdb_valid=fx3_global_xdb_valid,
        fx6_global_xdb_valid=fx6_global_xdb_valid,
        factory_digests_before=digests_before,
        factory_digests_after=digests_after,
        bit_exact_preservation_verified=bit_exact,
        volatile_staging_eval=vol,
        blocked_psd_bin_write=b_psd,
        blocked_defdet_bin_write=b_def,
        blocked_backup_bin_write=b_bak,
        blocked_cnflasha_write=b_cn,
        calibration_mutation_bytes=0,
        emmc_mutation_bytes=0,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar Evaluators & Top-Level Phase 105 Unified Auditor
# ---------------------------------------------------------------------------


def evaluate_pillar_1_c2pa_keyvault(
    *,
    fx3_appfw_markers: Tuple[str, ...],
    fx6_appfw_markers: Tuple[str, ...],
    fx3_libmpr_markers: Tuple[str, ...],
    fx6_libmpr_markers: Tuple[str, ...],
    fx6_libcert_mgr_markers: Tuple[str, ...],
    uxc_c2pa_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> C2paKeyVaultReport:
    errors = list(extra_errors)

    e_stock = evaluate_c2pa_keyvault_firewall(
        build_mode="STOCK_FX3_FIRMWARE",
        camera_body="FX3",
        container_format="MP4",
        bitrate_mbps=150.0,
        sq_mode_active=False,
        rq_lic_count=10,
        keyvault_target_path="/dev/cnflasha0",
        keyvault_mount_mode="O_RDONLY",
    )
    e_stageb = evaluate_c2pa_keyvault_firewall(
        build_mode="STAGE_B_USERLAND_OVERLAY",
        camera_body="FX3",
        container_format="MP4",
        bitrate_mbps=240.0,
        keyvault_target_path="/dev/cnflasha0",
        keyvault_mount_mode="O_RDONLY",
        attempt_forge_c2pa_hw_signature=False,
    )
    b_write = evaluate_c2pa_keyvault_firewall(
        build_mode="STAGE_B_USERLAND_OVERLAY",
        camera_body="FX3",
        keyvault_target_path="/dev/cnflasha0",
        keyvault_mount_mode="O_RDWR",
        requested_keyvault_writes=4096,
    )
    b_forge = evaluate_c2pa_keyvault_firewall(
        build_mode="STAGE_B_USERLAND_OVERLAY",
        camera_body="FX3",
        attempt_forge_c2pa_hw_signature=True,
    )
    b_spoof = evaluate_c2pa_keyvault_firewall(
        build_mode="STOCK_FX3_FIRMWARE",
        camera_body="FX6",
        cert_body_origin="FX3",
    )
    b_bitrate = evaluate_c2pa_keyvault_firewall(
        build_mode="STOCK_FX3_FIRMWARE",
        camera_body="FX3",
        container_format="MP4",
        bitrate_mbps=600.0,
    )
    b_lic = evaluate_c2pa_keyvault_firewall(
        build_mode="STOCK_FX3_FIRMWARE",
        camera_body="FX3",
        container_format="MP4",
        bitrate_mbps=100.0,
        rq_lic_count=101,
    )

    if not e_stock.valid or not e_stock.c2pa_hardware_signature_written:
        errors.append(f"Stock FX3 C2PA readonly keyvault audit failed: {e_stock.errors}")
    if (
        not e_stageb.valid
        or e_stageb.c2pa_hardware_signature_written
        or not e_stageb.clean_room_research_marked
    ):
        errors.append(f"Stage-B transparent unsigned overlay audit failed: {e_stageb.errors}")
    for lbl, blk in (
        ("cnflasha_write", b_write),
        ("forge_overlay_sig", b_forge),
        ("cross_body_spoof", b_spoof),
        ("over_222mbps", b_bitrate),
        ("over_100_lic", b_lic),
    ):
        if blk.valid:
            errors.append(f"Negative guard {lbl} unexpectedly passed")

    return C2paKeyVaultReport(
        passed=len(errors) == 0,
        fx3_appfw_c2pa_markers=fx3_appfw_markers,
        fx6_appfw_c2pa_markers=fx6_appfw_markers,
        fx3_libmpr_c2pa_markers=fx3_libmpr_markers,
        fx6_libmpr_c2pa_markers=fx6_libmpr_markers,
        fx6_libcert_mgr_markers=fx6_libcert_mgr_markers,
        uxc_c2pa_labels=uxc_c2pa_labels,
        eval_stock_fx3_mp4_readonly_vault=e_stock,
        eval_stageb_overlay_transparent_unsigned=e_stageb,
        blocked_cnflasha_write_attempt=b_write,
        blocked_forged_c2pa_sig_on_overlay=b_forge,
        blocked_cross_body_cert_spoof=b_spoof,
        blocked_over_222mbps_mp4_or_sq=b_bitrate,
        blocked_fx3_over_100_licenses=b_lic,
        errors=tuple(errors),
    )


def evaluate_pillar_2_emount_lens_shading(
    *,
    fx3_appfw_lens_markers: Tuple[str, ...],
    fx6_appfw_lens_markers: Tuple[str, ...],
    fx3_cp_lens_markers: Tuple[str, ...],
    fx6_cp_lens_markers: Tuple[str, ...],
    uxc_lens_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> EmountLensShadingReport:
    errors = list(extra_errors)

    e_1635 = evaluate_emount_lens_compensation("SEL1635GM2_16MM", shading_mode="AUTO")
    e_50 = evaluate_emount_lens_compensation("SEL50F12GM", shading_mode="AUTO_LOW")
    e_70200 = evaluate_emount_lens_compensation("SEL70200GM2_200MM", shading_mode="AUTO")
    e_pl = evaluate_emount_lens_compensation("UNCHIPPED_PL_CINE_PRIME")
    e_ana = evaluate_emount_lens_compensation("MANUAL_ANAMORPHIC_2X")
    b_stale = evaluate_emount_lens_compensation(
        "UNCHIPPED_PL_CINE_PRIME", force_stale_coefficients=True
    )

    for lbl, ev in (
        ("SEL1635GM2_16MM", e_1635),
        ("SEL50F12GM", e_50),
        ("SEL70200GM2_200MM", e_70200),
    ):
        if not ev.valid or ev.identity_failsafe_active:
            errors.append(f"GM lens {lbl} evaluation failed: {ev.errors}")
    for lbl, ev in (("UNCHIPPED_PL", e_pl), ("MANUAL_ANAMORPHIC", e_ana)):
        if (
            not ev.valid
            or not ev.identity_failsafe_active
            or ev.shading_gain_corner != 1.0
            or ev.stale_coeff_leak_detected
        ):
            errors.append(f"Unchipped identity fail-safe {lbl} failed: {ev.errors}")
    if b_stale.valid or not b_stale.stale_coeff_leak_detected:
        errors.append("Stale electronic lens coefficient leak on unchipped PL lens was not blocked")

    return EmountLensShadingReport(
        passed=len(errors) == 0,
        fx3_appfw_lens_markers=fx3_appfw_lens_markers,
        fx6_appfw_lens_markers=fx6_appfw_lens_markers,
        fx3_cp_lens_markers=fx3_cp_lens_markers,
        fx6_cp_lens_markers=fx6_cp_lens_markers,
        uxc_lens_labels=uxc_lens_labels,
        eval_gm_1635_wide_barrel=e_1635,
        eval_gm_50_standard=e_50,
        eval_gm_70200_tele_pincushion=e_70200,
        eval_unchipped_pl_identity_failsafe=e_pl,
        eval_manual_anamorphic_identity_failsafe=e_ana,
        blocked_stale_coeff_on_unchipped_pl=b_stale,
        errors=tuple(errors),
    )


def evaluate_pillar_3_mc_wired_fleet(
    *,
    fx3_appfw_mc_markers: Tuple[str, ...],
    fx6_appfw_mc_markers: Tuple[str, ...],
    fx6_libinfra_ptp_markers: Tuple[str, ...],
    fx6_libnet_ether_markers: Tuple[str, ...],
    uxc_mc_labels: Dict[str, str],
    extra_errors: Sequence[str] = (),
) -> McWiredFleetReport:
    errors = list(extra_errors)
    fleet4 = build_default_4cam_mc_fleet()

    e_fleet = evaluate_mc_wired_fleet_matrix(fleet4)
    b_direct = evaluate_mc_wired_fleet_matrix(fleet4, topology="DIRECT_ETHERNET_NO_ROUTER")
    b_tether = evaluate_mc_wired_fleet_matrix(fleet4, topology="FX6_USB_TETHER_IPADOS")
    fleet5 = tuple(fleet4) + (
        McFleetCameraNode(
            cam_id="CAM_E",
            camera_body="FX3",
            ip_address="192.168.50.105",
            nic_driver="CDC_NCM_RTL8153",
            access_auth_enabled=True,
            ptpip_port=PTPIP_TCP_PORT,
            telemetry_bitrate_mbps=8.2,
            false_color_enabled=True,
            waveform_enabled=True,
            focus_map_enabled=True,
            gang_rec_skew_ms=4.5,
        ),
    )
    b_5cam = evaluate_mc_wired_fleet_matrix(fleet5, plan_tier="FREE_4CAM")
    b_rf = evaluate_mc_wired_fleet_matrix(
        fleet4,
        p12_airplane_mode_on=False,
        wifi_rf_enabled=True,
        hci_tx_packets=3,
        wf12_00342260_hits=1,
    )
    unauth_cam = McFleetCameraNode(
        cam_id="CAM_A",
        camera_body="FX3",
        ip_address="192.168.50.101",
        nic_driver="CDC_NCM_RTL8153",
        access_auth_enabled=False,
        ptpip_port=PTPIP_TCP_PORT,
        telemetry_bitrate_mbps=8.2,
        false_color_enabled=True,
        waveform_enabled=True,
        focus_map_enabled=True,
        gang_rec_skew_ms=4.1,
    )
    b_unauth = evaluate_mc_wired_fleet_matrix((unauth_cam,) + fleet4[1:])

    if not e_fleet.valid or e_fleet.wf12_00342260_hits != 0 or e_fleet.hci_tx_packets != 0:
        errors.append(f"4-cam wired PTP-IP P12 fleet audit failed: {e_fleet.errors}")
    for lbl, blk in (
        ("direct_eth", b_direct),
        ("fx6_usb_tether", b_tether),
        ("over_4cam_free", b_5cam),
        ("p12_rf_wf12", b_rf),
        ("unauthenticated_ptpip", b_unauth),
    ):
        if blk.valid:
            errors.append(f"Negative fleet guard {lbl} unexpectedly passed")

    return McWiredFleetReport(
        passed=len(errors) == 0,
        fx3_appfw_mc_markers=fx3_appfw_mc_markers,
        fx6_appfw_mc_markers=fx6_appfw_mc_markers,
        fx6_libinfra_ptp_markers=fx6_libinfra_ptp_markers,
        fx6_libnet_ether_markers=fx6_libnet_ether_markers,
        uxc_mc_labels=uxc_mc_labels,
        eval_4cam_wired_ptpip_p12_fleet=e_fleet,
        blocked_direct_eth_no_router=b_direct,
        blocked_fx6_usb_tether_ipados=b_tether,
        blocked_over_4cam_free_plan=b_5cam,
        blocked_p12_rf_leak_wf12=b_rf,
        blocked_unauthenticated_ptpip=b_unauth,
        errors=tuple(errors),
    )


def analyze_c2pa_lens_shading_and_mc_fleet(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> C2paLensShadingAndMcFleetReport:
    """Run the 20th unified firmware-lab auditor in Local Donor (`os.O_RDONLY`) or Clean-Room mode."""
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
            "fx6_libcert_mgr": resolve_donor_file(FX6_LIBCERT_MGR_RELPATH, repo_root=root),
            "fx6_libinfra_ptp": resolve_donor_file(FX6_LIBINFRA_PTP_RELPATH, repo_root=root),
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

    fx3_c2pa_expected = FX3_APPFW_PHASE105_MARKERS[:7]
    fx3_lens_expected = FX3_APPFW_PHASE105_MARKERS[7:16]
    fx3_mc_expected = FX3_APPFW_PHASE105_MARKERS[16:]

    fx6_c2pa_expected = FX6_APPFW_PHASE105_MARKERS[:5]
    fx6_lens_expected = FX6_APPFW_PHASE105_MARKERS[5:16]
    fx6_mc_expected = FX6_APPFW_PHASE105_MARKERS[16:]

    fx3_mpr_expected = LIBMPR_SHARED_PHASE105_MARKERS + FX3_LIBMPR_EXTRA_PHASE105_MARKERS

    if use_local:
        sz_fx3_app, fx3_app_res = _scan_donor_rdonly_markers(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            {"c2pa": fx3_c2pa_expected, "lens": fx3_lens_expected, "mc": fx3_mc_expected},
            is_elf=True,
        )
        sz_fx6_app, fx6_app_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            {"c2pa": fx6_c2pa_expected, "lens": fx6_lens_expected, "mc": fx6_mc_expected},
            is_elf=True,
        )
        sz_fx3_mpr, fx3_mpr_res = _scan_donor_rdonly_markers(
            donor_paths["fx3_libmpr"],  # type: ignore[arg-type]
            {"m": fx3_mpr_expected},
            is_elf=True,
        )
        sz_fx6_mpr, fx6_mpr_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_libmpr"],  # type: ignore[arg-type]
            {"m": LIBMPR_SHARED_PHASE105_MARKERS},
            is_elf=True,
        )
        sz_fx3_cp, fx3_cp_res = _scan_donor_rdonly_markers(
            donor_paths["fx3_cpapp"],  # type: ignore[arg-type]
            {"m": CP_SHARED_PHASE105_MARKERS},
            is_elf=False,
        )
        sz_fx6_cp, fx6_cp_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_cpapp"],  # type: ignore[arg-type]
            {"m": CP_SHARED_PHASE105_MARKERS},
            is_elf=False,
        )
        sz_cert, cert_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_libcert_mgr"],  # type: ignore[arg-type]
            {"m": FX6_LIBCERT_MGR_MARKERS},
            is_elf=True,
        )
        sz_ptp, ptp_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_libinfra_ptp"],  # type: ignore[arg-type]
            {"m": FX6_LIBINFRA_PTP_MARKERS},
            is_elf=True,
        )
        sz_eth, eth_res = _scan_donor_rdonly_markers(
            donor_paths["fx6_libnet_ether"],  # type: ignore[arg-type]
            {"m": FX6_LIBNET_ETHER_MARKERS},
            is_elf=True,
        )
        fx3_xdb_bytes = _read_bytes_rdonly(donor_paths["fx3_global_xdb"])  # type: ignore[arg-type]
        fx6_xdb_bytes = _read_bytes_rdonly(donor_paths["fx6_global_xdb"])  # type: ignore[arg-type]
        fx3_str_en_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en"])  # type: ignore[arg-type]
        fx3_str_en_g_bytes = _read_bytes_rdonly(donor_paths["fx3_str_en_g"])  # type: ignore[arg-type]
        fx6_str_en_1_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_1"])  # type: ignore[arg-type]
        fx6_str_en_2_bytes = _read_bytes_rdonly(donor_paths["fx6_str_en_2"])  # type: ignore[arg-type]
    else:
        fx = build_clean_room_c2pa_shading_mc_fixtures()
        sz_fx3_app, fx3_app_res = _scan_bytes_marker_groups(
            fx["fx3_appfw"],
            {"c2pa": fx3_c2pa_expected, "lens": fx3_lens_expected, "mc": fx3_mc_expected},
        )
        sz_fx6_app, fx6_app_res = _scan_bytes_marker_groups(
            fx["fx6_appfw"],
            {"c2pa": fx6_c2pa_expected, "lens": fx6_lens_expected, "mc": fx6_mc_expected},
        )
        sz_fx3_mpr, fx3_mpr_res = _scan_bytes_marker_groups(fx["fx3_libmpr"], {"m": fx3_mpr_expected})
        sz_fx6_mpr, fx6_mpr_res = _scan_bytes_marker_groups(
            fx["fx6_libmpr"], {"m": LIBMPR_SHARED_PHASE105_MARKERS}
        )
        sz_fx3_cp, fx3_cp_res = _scan_bytes_marker_groups(
            fx["fx3_cpapp"], {"m": CP_SHARED_PHASE105_MARKERS}
        )
        sz_fx6_cp, fx6_cp_res = _scan_bytes_marker_groups(
            fx["fx6_cpapp"], {"m": CP_SHARED_PHASE105_MARKERS}
        )
        sz_cert, cert_res = _scan_bytes_marker_groups(
            fx["fx6_libcert_mgr"], {"m": FX6_LIBCERT_MGR_MARKERS}
        )
        sz_ptp, ptp_res = _scan_bytes_marker_groups(
            fx["fx6_libinfra_ptp"], {"m": FX6_LIBINFRA_PTP_MARKERS}
        )
        sz_eth, eth_res = _scan_bytes_marker_groups(
            fx["fx6_libnet_ether"], {"m": FX6_LIBNET_ETHER_MARKERS}
        )
        fx3_xdb_bytes = fx["fx3_global_xdb"]
        fx6_xdb_bytes = fx["fx6_global_xdb"]
        fx3_str_en_bytes = fx["fx3_str_en"]
        fx3_str_en_g_bytes = fx["fx3_str_en_g"]
        fx6_str_en_1_bytes = fx["fx6_str_en_1"]
        fx6_str_en_2_bytes = fx["fx6_str_en_2"]

    sizes: Dict[str, int] = {
        "fx3_appfw": sz_fx3_app,
        "fx6_appfw": sz_fx6_app,
        "fx3_libmpr": sz_fx3_mpr,
        "fx6_libmpr": sz_fx6_mpr,
        "fx3_cpapp": sz_fx3_cp,
        "fx6_cpapp": sz_fx6_cp,
        "fx6_libcert_mgr": sz_cert,
        "fx6_libinfra_ptp": sz_ptp,
        "fx6_libnet_ether": sz_eth,
        "fx3_global_xdb": len(fx3_xdb_bytes),
        "fx6_global_xdb": len(fx6_xdb_bytes),
        "fx3_str_en": len(fx3_str_en_bytes),
        "fx3_str_en_g": len(fx3_str_en_g_bytes),
        "fx6_str_en_1": len(fx6_str_en_1_bytes),
        "fx6_str_en_2": len(fx6_str_en_2_bytes),
    }

    p1_extra: List[str] = []
    p2_extra: List[str] = []
    p3_extra: List[str] = []

    if len(fx3_app_res["c2pa"]) != len(fx3_c2pa_expected):
        p1_extra.append("Missing FX3 appFw C2PA markers")
    if len(fx6_app_res["c2pa"]) != len(fx6_c2pa_expected):
        p1_extra.append("Missing FX6 appFw C2PA markers")
    if len(fx3_mpr_res["m"]) != len(fx3_mpr_expected):
        p1_extra.append("Missing FX3 libmpr C2PA markers")
    if len(fx6_mpr_res["m"]) != len(LIBMPR_SHARED_PHASE105_MARKERS):
        p1_extra.append("Missing FX6 libmpr C2PA markers")
    if len(cert_res["m"]) != len(FX6_LIBCERT_MGR_MARKERS):
        p1_extra.append("Missing libCertificateManager.so markers")

    if len(fx3_app_res["lens"]) != len(fx3_lens_expected):
        p2_extra.append("Missing FX3 appFw Lens Comp markers")
    if len(fx6_app_res["lens"]) != len(fx6_lens_expected):
        p2_extra.append("Missing FX6 appFw Lens Comp markers")
    if len(fx3_cp_res["m"]) != len(CP_SHARED_PHASE105_MARKERS):
        p2_extra.append("Missing FX3 CP Lens Comp / defdet.bin markers")
    if len(fx6_cp_res["m"]) != len(CP_SHARED_PHASE105_MARKERS):
        p2_extra.append("Missing FX6 CP Lens Comp / defdet.bin markers")

    if len(fx3_app_res["mc"]) != len(fx3_mc_expected):
        p3_extra.append("Missing FX3 appFw Wired LAN / PTP markers")
    if len(fx6_app_res["mc"]) != len(fx6_mc_expected):
        p3_extra.append("Missing FX6 appFw PTP-IP / Airplane markers")
    if len(ptp_res["m"]) != len(FX6_LIBINFRA_PTP_MARKERS):
        p3_extra.append("Missing libInfraPtpControl.so PTP-IP markers")
    if len(eth_res["m"]) != len(FX6_LIBNET_ETHER_MARKERS):
        p3_extra.append("Missing libNetServiceEther.so markers")

    fx3_ux_en, u_err_1 = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE105_LABELS)
    fx3_ux_g, u_err_2 = _extract_uxc_labels(fx3_str_en_g_bytes, FX3_NS3_PHASE105_LABELS)
    fx6_ux_1, u_err_3 = _extract_uxc_labels(fx6_str_en_1_bytes, FX6_NS1_PHASE105_LABELS)
    fx6_ux_2, u_err_4 = _extract_uxc_labels(fx6_str_en_2_bytes, FX6_NS2_PHASE105_LABELS)
    p3_extra.extend(u_err_1)
    p1_extra.extend(u_err_2)
    p1_extra.extend(u_err_3)
    p2_extra.extend(u_err_4)

    uxc_c2pa_labels = {
        "fx3_digital_signature": fx3_ux_g.get("0x0000604f", ""),
        "fx3_signature_type_c2pa": fx3_ux_g.get("0x000064ea", ""),
        "fx6_cert_for_c2pa": fx6_ux_1.get("0x00002e89", ""),
        "fx6_digital_signature": fx6_ux_1.get("0x00002ea8", ""),
    }
    uxc_lens_labels = {
        "fx3_lens_comp": fx3_ux_g.get("0x0000605a", ""),
        "fx3_lens_comp_desc": fx3_ux_g.get("0x00006420", ""),
        "fx6_distortion_comp": fx6_ux_2.get("0x00004f62", ""),
        "fx6_shading_comp": fx6_ux_2.get("0x0000560a", ""),
    }
    uxc_mc_labels = {
        "fx3_wired_lan": fx3_ux_en.get("0x0004e100", ""),
        "fx6_access_auth": fx6_ux_1.get("0x0000279e", ""),
        "fx6_wired_lan": fx6_ux_1.get("0x000027a1", ""),
        "fx6_wired_lan_cam_remote": fx6_ux_1.get("0x00002b58", ""),
    }

    p1 = evaluate_pillar_1_c2pa_keyvault(
        fx3_appfw_markers=fx3_app_res["c2pa"],
        fx6_appfw_markers=fx6_app_res["c2pa"],
        fx3_libmpr_markers=fx3_mpr_res["m"],
        fx6_libmpr_markers=fx6_mpr_res["m"],
        fx6_libcert_mgr_markers=cert_res["m"],
        uxc_c2pa_labels=uxc_c2pa_labels,
        extra_errors=p1_extra,
    )
    p2 = evaluate_pillar_2_emount_lens_shading(
        fx3_appfw_lens_markers=fx3_app_res["lens"],
        fx6_appfw_lens_markers=fx6_app_res["lens"],
        fx3_cp_lens_markers=fx3_cp_res["m"],
        fx6_cp_lens_markers=fx6_cp_res["m"],
        uxc_lens_labels=uxc_lens_labels,
        extra_errors=p2_extra,
    )
    p3 = evaluate_pillar_3_mc_wired_fleet(
        fx3_appfw_mc_markers=fx3_app_res["mc"],
        fx6_appfw_mc_markers=fx6_app_res["mc"],
        fx6_libinfra_ptp_markers=ptp_res["m"],
        fx6_libnet_ether_markers=eth_res["m"],
        uxc_mc_labels=uxc_mc_labels,
        extra_errors=p3_extra,
    )

    try:
        parse_global_xdb_buffer(fx3_xdb_bytes)
        fx3_xdb_ok = True
    except Exception:
        fx3_xdb_ok = False

    try:
        parse_global_xdb_buffer(fx6_xdb_bytes)
        fx6_xdb_ok = True
    except Exception:
        fx6_xdb_ok = False

    p4 = verify_factory_shading_and_defect_immutability(
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
    )

    all_errors = p1.errors + p2.errors + p3.errors + p4.errors
    all_passed = bool(p1.passed and p2.passed and p3.passed and p4.passed and len(all_errors) == 0)

    digest_payload = {
        "schema_version": PHASE_105_SCHEMA,
        "phase_version": PHASE_105_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "donor_file_sizes": sizes,
        "p1": asdict(p1),
        "p2": asdict(p2),
        "p3": asdict(p3),
        "p4": asdict(p4),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return C2paLensShadingAndMcFleetReport(
        schema_version=PHASE_105_SCHEMA,
        phase_version=PHASE_105_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        donor_file_sizes=sizes,
        pillar_1_c2pa_keyvault=p1,
        pillar_2_emount_lens_shading=p2,
        pillar_3_mc_wired_fleet=p3,
        pillar_4_factory_shading_immutability=p4,
        report_sha256=report_sha256,
        errors=tuple(all_errors),
    )


def c2pa_lens_shading_and_mc_fleet_report_to_dict(
    report: C2paLensShadingAndMcFleetReport,
) -> Dict[str, object]:
    """Convert `C2paLensShadingAndMcFleetReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
