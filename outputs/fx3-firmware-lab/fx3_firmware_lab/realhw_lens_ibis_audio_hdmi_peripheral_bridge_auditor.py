"""Phase 146 — 29th Unified Firmware-Lab Auditor: Real-Hardware Stage-B Peripheral Bridge
(E-Mount Lens `p18:/lens`, 5-Axis Physical IBIS vs Catalyst, MI-Shoe `XLR-H1` 4ch Audio,
and HDMI Type-A / Multi-USB `TC-IN` vs `12G-SDI` / `BNC TC` Bridge).

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so`, `libsencore.so`, `libmpr.so`,
  `im.elf`, `cpapp-b.bin`, `Backup.bin`, `libInfraLensCommunicator.so`,
  `libInfraAvbbc.so`) and FX6 v6.01 (`appFw.so`, `libsencore.so`, `libmpr.so`,
  `im.elf`, `cpapp-b.bin`, `Backup.bin`, `libInfraLensCommunicator.so`,
  `libInfraHotshoe.so`, `AVBB_SCN_START_AUDIO.so`, `libInfraAvbbc.so`) strictly
  via `os.O_RDONLY` + `mmap.ACCESS_READ` using targeted ELF64 `.dynsym`/`.dynstr`
  parsing, `BK4\\x00` parsing, and bounded single-pass `re.finditer` scans (< 1.5 s).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`/`.elf` fixtures,
  `cpapp-b.bin` token buffers, and `BK4\\x00` `Backup.bin` fixtures, leaking zero
  raw Sony proprietary bytes in JSON output.

Audits Four Phase 146 Real-Hardware Peripheral Pillars & 4-Class Compatibility Matrix:
1. Pillar 1 (`E_MOUNT_LENS_AND_P18_CALIBRATION_COMPAT`):
   Verifies `libInfraLensCommunicator.so` (`14,544 B`, `27` exports, `25` imports)
   parity, `libsencore.so` (`355` exports, `130` imports) factory-service isolation,
   E-Mount lens metadata (`focal_length`, `F/T-stop`, `ft/m`, `breathing_comp`,
   `distortion_comp`, `shading_comp`, `PowerZoom`), and strict read-only
   write-protection of `p18:/lens/lensfile.bin` (`/dev/nflasha18`, FX3 LBA
   `0x0031C000` vs FX6 LBA `0x00312000`, `p18_lens_writes_permitted = False`).
2. Pillar 2 (`IBIS_5AXIS_VS_CATALYST_GYRO_BRIDGE`):
   Audits FX6 rigid-sensor flag (`PRM_is_imager_stabilization_unit_fixed`) vs
   FX3 energized 5-axis physical IBIS (`LiroSeq: Restore.`, `0x0400 -> 0x1400`
   Center-Lock park, `Off / Standard / Active`) and Catalyst/Gyroflow `UDAM`
   2000 Hz gyro/accel telemetry (`libmpr.so`), enforcing safe `libgrm-fbinit9.so`
   Stage-B parking/IBIS policy (`ibis_coil_safe_park_verified = True`) and zero
   writes to `p2:/Backup.bin`, `p2:/psd.bin`, and `p6:Jiritsu`.
3. Pillar 3 (`MISHOE_XLR_H1_4CH_AUDIO_ROUTING_BRIDGE`):
   Audits `libInfraHotshoe.so` (`47,808 B`, `76` exports), `AVBB_SCN_START_AUDIO.so`
   (`70,096 B`), `appFw.so`, and `libmpr.so` 4-ch `24-bit 48 kHz LPCM` (`4,608,000 bps`)
   routing across `XLR-H1` MI-Shoe attached, 3.5 mm TRS jack, and internal stereo
   mic fallback, enforcing `P11` `0x91db059b` (`E_TMO = -50 -> 0x8000`)
   non-blocking hot-detach containment (`phantom_device_timeout_eliminated = True`).
4. Pillar 4 (`HDMI_TYPE_A_TC_IN_VS_SDI_BNC_BRIDGE`):
   Audits `appFw.so`, `libInfraAvbbc.so` (`ConvertCmdMidToSdi`/`Hdmi`/`Tcub`),
   and `cpapp-b.bin` for `12G-SDI` (`mew.bin`), `BNC TC OUT`, `BNC Genlock`, and
   `DARWIN_ND`, synthesizing non-blocking `LD_PRELOAD` (`libgrm-fbinit9.so`) /
   `osal_uipc` stub rules (`sdi_blocking_wait_eliminated = True`) while preserving
   native FX3 HDMI Type-A (`4K60 / 16-bit RAW / Clean OSD`) and Multi-USB
   `VMC-BNCM1` `TC-IN` (`Pin 3 LTC+`, `680 kOhm ID`, `P11 0x92d2091c`).
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

from .audio_tc_hdmi_sdi_routing_auditor import (
    FX6_AVBB_AUDIO_RELPATH,
    FX6_HOTSHOE_RELPATH,
)
from .emount_af_breathing_and_ibis_auditor import (
    FX3_LENS_COMM_RELPATH,
    FX6_LENS_COMM_RELPATH,
)
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
    FX3_BACKUP_BIN_RELPATH,
    FX3_CPAPP_P137_RELPATH,
    FX6_BACKUP_BIN_RELPATH,
    FX6_CPAPP_P137_RELPATH,
    parse_dual_bk4_and_descriptors,
)
from .realhw_mpr_dmm_rec_pipeline_bridge_auditor import (
    FX3_APPFW_P140_RELPATH,
    FX3_IM_ELF_RELPATH,
    FX3_LIBINFRA_AVBBC_RELPATH,
    FX3_LIBMPR_P140_RELPATH,
    FX6_APPFW_P140_RELPATH,
    FX6_IM_ELF_RELPATH,
    FX6_LIBINFRA_AVBBC_RELPATH,
    FX6_LIBMPR_P140_RELPATH,
)


PHASE_146_SCHEMA = "fx3_firmware_lab_phase146_realhw_peripheral_bridge_v1"
PHASE_146_VERSION = "146.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------

FX3_APPFW_P146_RELPATH = FX3_APPFW_P140_RELPATH
FX6_APPFW_P146_RELPATH = FX6_APPFW_P140_RELPATH
FX3_LIBSENCORE_P146_RELPATH = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libsencore.so"
)
FX6_LIBSENCORE_P146_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libsencore.so"
)
FX3_LIBMPR_P146_RELPATH = FX3_LIBMPR_P140_RELPATH
FX6_LIBMPR_P146_RELPATH = FX6_LIBMPR_P140_RELPATH
FX3_IM_ELF_P146_RELPATH = FX3_IM_ELF_RELPATH
FX6_IM_ELF_P146_RELPATH = FX6_IM_ELF_RELPATH
FX3_CPAPP_P146_RELPATH = FX3_CPAPP_P137_RELPATH
FX6_CPAPP_P146_RELPATH = FX6_CPAPP_P137_RELPATH
FX3_BACKUP_BIN_P146_RELPATH = FX3_BACKUP_BIN_RELPATH
FX6_BACKUP_BIN_P146_RELPATH = FX6_BACKUP_BIN_RELPATH
FX3_LENS_COMM_P146_RELPATH = FX3_LENS_COMM_RELPATH
FX6_LENS_COMM_P146_RELPATH = FX6_LENS_COMM_RELPATH
FX6_HOTSHOE_P146_RELPATH = FX6_HOTSHOE_RELPATH
FX6_AVBB_AUDIO_P146_RELPATH = FX6_AVBB_AUDIO_RELPATH
FX3_LIBINFRA_AVBBC_P146_RELPATH = FX3_LIBINFRA_AVBBC_RELPATH
FX6_LIBINFRA_AVBBC_P146_RELPATH = FX6_LIBINFRA_AVBBC_RELPATH

# ---------------------------------------------------------------------------
# 4-Class Cross-Body Peripheral Bridge Taxonomy
# ---------------------------------------------------------------------------

BRIDGE_CLASS_NATIVE_PASSTHROUGH = "NATIVE_PASSTHROUGH"
BRIDGE_CLASS_SHIM_TRANSLATED = "SHIM_TRANSLATED"
BRIDGE_CLASS_MASKED_ABSENT_HW = "MASKED_ABSENT_HW"
BRIDGE_CLASS_HARD_WRITE_PROTECTED = "HARD_WRITE_PROTECTED"

VALID_BRIDGE_CLASSES: Tuple[str, ...] = (
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
)

# ---------------------------------------------------------------------------
# Pillar 1 Constants: E-Mount Lens & p18:/lens Calibration
# ---------------------------------------------------------------------------

P18_LENS_PARTITION_DEVICE = "/dev/nflasha18"
P18_LENS_MOUNT_PATH = "/lens"
P18_LENS_CALIB_FILE = "p18:/lens/lensfile.bin"
P18_FX3_START_LBA = 0x0031C000
P18_FX3_SECTORS = 0x0000A000
P18_FX6_START_LBA = 0x00312000

EXPECTED_LENS_COMM_BYTES = 14_544
EXPECTED_LENS_COMM_EXPORTS = 27
EXPECTED_LENS_COMM_IMPORTS = 25
EXPECTED_SENCORE_EXPORTS = 355
EXPECTED_SENCORE_IMPORTS = 130

VALID_FOCUS_DISTANCE_UNITS: Tuple[str, ...] = ("METER", "FEET")
VALID_IRIS_DISPLAY_UNITS: Tuple[str, ...] = ("F_STOP", "T_STOP")

LENS_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "EVENT_FUNC_LENS_COMP_LENS_COMP_BREATHING_ON",
    "EVENT_FUNC_CUSTOM_ZOOM_TELE_ON",
    "EVENT_FUNC_STEP_ZOOM_TOGGLE_ON",
    "PID_SET_DISTORTION_CORRECTION",
    "PID_SET_SHADING_CORRECTION",
)
LENS_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "EVENT_FUNC_LENS_INFO_ON",
    "EVENT_FUNC_SETTING_ZOOM_TYPE_ON",
    "EVENT_FUNC_PRESET_FOCUS_ZOOM_EXECUTION1",
    "EVENT_REMOTE_LENS_COMP_LENS_COMP_DISTORTION",
    "EVENT_REMOTE_LENS_COMP_LENS_COMP_SHADING",
    "PID_SET_DISTORTION_CORRECTION",
    "PID_SET_SHADING_CORRECTION",
    "BREATHING_CORRECTION",
)
SENCORE_SHARED_MARKERS: Tuple[str, ...] = (
    "SenserIfStart",
    "SenserIfSend",
    "MiconAccessFunc",
    "AdjustControlFunc",
    "/dev/nflasha5",
    "/dev/nflasha8",
)

# ---------------------------------------------------------------------------
# Pillar 2 Constants: 5-Axis Physical IBIS vs FX6 Gyro-Only Catalyst
# ---------------------------------------------------------------------------

IBIS_MODES_FX3: Tuple[str, ...] = ("OFF", "STANDARD", "ACTIVE")
IBIS_MODES_FX6_UI: Tuple[str, ...] = ("OFF", "STANDARD", "ACTIVE", "ACTIVE_PLUS")
IBIS_CENTER_LOCK_CMD_OPCODE = 0x0400
IBIS_CENTER_LOCK_DONE_OPCODE = 0x1400
CATALYST_IMU_SAMPLE_RATE_HZ = 2000
FX6_RIGID_SENSOR_PARAM = "PRM_is_imager_stabilization_unit_fixed"

IBIS_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "PID_SET_STEADYSHOT_ADVANCED_MOVIE",
    "PID_SET_FRAME_LOCK_STEADYSHOT",
    "EVENT_FUNC_MOVIE_STEADYSHOT_ON",
    "EVENT_FUNC_STEADYSHOT_FOCAL_LENGTH_ON",
)
IBIS_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "PRM_is_imager_stabilization_unit_fixed",
    "VAL_FEATURE_MANAGER_steadyshot_equip_with_body_TYPE_STEADYSHOT_EQUIP_WITH_BODY_SUPPORTED",
    "VAL_FEATURE_MANAGER_steadyshot_equip_with_body_TYPE_STEADYSHOT_EQUIP_WITH_BODY_UNSUPPORTED",
    "EVENT_FUNC_SETTING_STEADYSHOT_ACTIVE_ON",
    "EVENT_FUNC_SETTING_STEADYSHOT_STANDARD_ON",
    "EVENT_FUNC_SETTING_STEADYSHOT_OFF",
    "EVENT_REMOTE_STEADYSHOT_FOCAL_LENGTH",
)
IBIS_CP_SHARED_MARKERS: Tuple[str, ...] = (
    "LiroSeq",
    "SteadyShot",
    "GyroPIDOUT_0",
    "GyroStart",
    "GyroStop",
)
IBIS_MPR_GYRO_FX3_MARKERS: Tuple[str, ...] = (
    "UDAMSetGyroscopeValue",
    "UDAMSetAccelerometerValue",
    "Gyroscope",
)
IBIS_MPR_GYRO_FX6_MARKERS: Tuple[str, ...] = (
    "UDAMSetGyroscopeValue",
    "UDAMSetAccelerometerValue",
    "Gyroscope_GyroscopeSamplingRateWrite",
    "MetaConverterImpl::ConvertReadoutDuration",
)

# ---------------------------------------------------------------------------
# Pillar 3 Constants: MI-Shoe XLR-H1 4ch Audio vs FX6 Smart Top Handle
# ---------------------------------------------------------------------------

AUDIO_LPCM_SAMPLE_RATE_HZ = 48_000
AUDIO_LPCM_BIT_DEPTH = 24
AUDIO_LPCM_4CH_COUNT = 4
AUDIO_LPCM_4CH_BPS = AUDIO_LPCM_SAMPLE_RATE_HZ * AUDIO_LPCM_BIT_DEPTH * AUDIO_LPCM_4CH_COUNT
P11_SMART_HANDLE_QUEUE_ID = 0x91DB059B
P11_HOTSHOE_ATTACHED_EVT = 0x88000001
P11_HOTSHOE_DETACHED_EVT = 0x88000002
HOTSHOE_E_TMO = -50
HOTSHOE_NONBLOCK_SAFE_RC = 0x8000

VALID_AUDIO_HANDLE_STATES: Tuple[str, ...] = (
    "XLR_H1_ATTACHED",
    "XLR_H1_DETACHED",
    "TRS_JACK_ONLY",
)
AUDIO_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "EVENT_INPUT_INP_HOTSHOE_XLRMIC_ON",
    "EVENT_INPUT_INP_HOTSHOE_CH4MIC_ON",
    "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
    "VAL_setting_4ch_output_ch_E_4CH_OUTPUT_CH_1CH_2CH",
    "VAL_setting_4ch_output_ch_E_4CH_OUTPUT_CH_3CH_4CH",
    "EVENT_INPUT_KEY_JACK_MICJACK_IN",
    "HEADPHONE_CONNECT",
)
AUDIO_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "EVENT_INPUT_INP_HOTSHOE_XLRMIC_ON",
    "UIBIZ_INP_HOTSHOE_CH4MIC",
    "EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
    "E_4CH_OUTPUT_CH_1CH_2CH",
    "E_4CH_OUTPUT_CH_3CH_4CH",
    "UIBIZ_KEY_JACK_MICJACK_IN",
    "HEADPHONE_CONNECT",
)
HOTSHOE_MARKERS: Tuple[str, ...] = (
    "INFRA_HOTSHOE_UIPC_GETSHOEID",
    "INFRA_HOTSHOE_UIPC_GETUARTWAITMS",
    "INFRA_HOTSHOE_UIPC_SETCTRL_BCK_LRCK",
    "INFRA_HOTSHOE_UIPC_SETSHOEON",
    "INFRA_HOTSHOE_UIPC_SHOEINFO_EVT",
)
AVBB_AUDIO_MARKERS: Tuple[str, ...] = (
    "AvbbScnStartAudio",
    "BO_ID_MIC",
    "BO_ID_SHOE_MIC",
)

# ---------------------------------------------------------------------------
# Pillar 4 Constants: HDMI Type-A & Multi-USB TC-IN vs 12G-SDI & BNC TC/Genlock
# ---------------------------------------------------------------------------

VMC_BNCM1_ID_OHM = 680_000
VMC_BNCM1_LTC_PIN = 3
VMC_BNCM1_ID_PIN = 6
UART_BOOT_SHARED_PINS: Tuple[int, ...] = (7, 8, 9)
P11_RTC_UDATE_QUEUE_ID = 0x92D2091C

FX6_ABSENT_HW_PERIPHERALS: Tuple[str, ...] = (
    "12G_SDI_OUT",
    "BNC_TC_OUT",
    "BNC_GENLOCK_IN",
    "DARWIN_ND",
)
HDMI_TYPE_A_CAPABILITIES: Tuple[str, ...] = (
    "4K60_422_10BIT",
    "HDMI_RAW_16BIT_4264X2408",
    "CLEAN_OSD_TOGGLE",
    "HDMI_TC_TRIGGER",
)
HDMI_SDI_APPFW_FX6_MARKERS: Tuple[str, ...] = (
    "PRM_FEATURE_MANAGER_sdi_output",
    "VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT",
    "EVENT_REMOTE_SDI_OUTPUT",
    "PRM_HAITA_setting_sdi_hdmi_rec_control_movie_recording_state",
    "PRM_genlock_detect_ref_notify_receive_state",
    "EVENT_REMOTE_MOVIE_HDMI_OUTPUT_SETTINGS_W_DIALOG_HDMI_TC_OUTPUT",
    "HDMI_INFO_DISPLAY",
    "HDMI_RAW",
)
HDMI_APPFW_FX3_MARKERS: Tuple[str, ...] = (
    "HDMI_INFO_DISPLAY",
    "HDMI_RAW",
    "TC_IN",
    "TC_OUT",
)
AVBBC_BRIDGE_SYMBOLS: Tuple[str, ...] = (
    "_ZN11ObjAvbbcCmn18ConvertCmdMidToSdiEt",
    "_ZN11ObjAvbbcCmn19ConvertCmdMidToHdmiEt",
    "_ZN11ObjAvbbcCmn19ConvertCmdMidToTcubEt",
    "_ZN11ObjAvbbcCmn20ConvertResMidFromSdiEtPtPh",
    "_ZN11ObjAvbbcCmn21ConvertResMidFromHdmiEtPtPh",
)

# ---------------------------------------------------------------------------
# Write-Guard Constants
# ---------------------------------------------------------------------------

VOLATILE_STAGING_PREFIXES_P146: Tuple[str, ...] = ("/tmp/", "ram://", "ramdisk://", "mem://")
FORBIDDEN_PERSISTENT_NVS_OR_EMMC_RE_P146 = re.compile(
    r"(^/dev/(nflash|cnflash|mmcblk0)|^/lens\b|/lensfile\.bin|Backup\.bin|psd\.bin|defdet\.bin|cpapp-b\.bin|loader_nor\.bin|^p[0-9]+:|jiritsu|/cert\b)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ElfSectionSummary:
    binary_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    export_count: int
    import_count: int
    dt_needed: Tuple[str, ...]
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class PeripheralTouchpointEntry:
    touchpoint_id: str
    subsystem: str  # "LENS_P18", "IBIS_IMU", "AUDIO_XLRH1", "HDMI_SDI_TC"
    fx6_interface: str
    fx3_target: str
    classification: str  # One of VALID_BRIDGE_CLASSES
    shim_layer: str
    blocking_wait_eliminated: bool
    write_protected: bool
    notes: str


@dataclass(frozen=True)
class LensP18BridgeEvalResult:
    valid: bool
    status: str
    lens_mounted: bool
    focal_length_mm: float
    aperture_display_unit: str
    focus_distance_unit: str
    breathing_comp_enabled: bool
    distortion_comp_enabled: bool
    shading_comp_enabled: bool
    classification: str
    p18_lens_writes_permitted: bool
    write_attempt_blocked: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class IbisCatalystBridgeEvalResult:
    valid: bool
    status: str
    requested_mode: str
    fx3_effective_mode: str
    classification: str
    coil_parked_center_lock: bool
    ibis_coil_safe_park_verified: bool
    gyro_rtmd_2000hz_active: bool
    rigid_sensor_query_masked: bool
    nvs_calibration_writes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AudioXlrh1BridgeEvalResult:
    valid: bool
    status: str
    handle_state: str
    sample_rate_hz: int
    bit_depth: int
    active_channels: int
    bitrate_bps: int
    channel_routing: Dict[str, str]
    classification: str
    p11_nonblock_rc_hex: str
    phantom_device_timeout_eliminated: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class HdmiSdiTcBridgeEvalResult:
    valid: bool
    status: str
    requested_interface: str
    fx3_target_interface: str
    classification: str
    non_blocking_stub_rc: int
    stub_blocking_wait_ms: int
    sdi_blocking_wait_eliminated: bool
    in_uart_boot_safe: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase146WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    p18_lens_writes_permitted: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar1LensP18Report:
    passed: bool
    fx3_lens_comm: ElfSectionSummary
    fx6_lens_comm: ElfSectionSummary
    lens_comm_exports_identical: bool
    fx3_sencore: ElfSectionSummary
    fx6_sencore: ElfSectionSummary
    sencore_exports_identical: bool
    fx3_appfw_lens_marker_hits: int
    fx6_appfw_lens_marker_hits: int
    p18_fx3_lba_hex: str
    p18_fx6_lba_hex: str
    p18_lens_writes_permitted: bool
    sample_evals: Tuple[LensP18BridgeEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2IbisCatalystReport:
    passed: bool
    fx3_appfw_ibis_marker_hits: int
    fx6_appfw_ibis_marker_hits: int
    fx3_cp_liroseq_hits: int
    fx6_cp_liroseq_hits: int
    fx3_mpr_gyro_hits: int
    fx6_mpr_gyro_hits: int
    fx3_backup_subsystems: int
    fx6_backup_subsystems: int
    fx3_backup_checksums_valid: bool
    fx6_backup_checksums_valid: bool
    ibis_coil_safe_park_verified: bool
    sample_evals: Tuple[IbisCatalystBridgeEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3AudioXlrh1Report:
    passed: bool
    fx3_appfw_audio_marker_hits: int
    fx6_appfw_audio_marker_hits: int
    fx6_hotshoe: ElfSectionSummary
    fx6_avbb_audio: ElfSectionSummary
    lpcm_4ch_bitrate_bps: int
    p11_nonblock_safe_rc_hex: str
    phantom_device_timeout_eliminated: bool
    sample_evals: Tuple[AudioXlrh1BridgeEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4HdmiSdiTcReport:
    passed: bool
    fx3_appfw_hdmi_marker_hits: int
    fx6_appfw_sdi_hdmi_marker_hits: int
    fx3_avbbc: ElfSectionSummary
    fx6_avbbc: ElfSectionSummary
    fx3_cp_hdmi_hits: int
    fx3_cp_sdi_hits: int
    fx6_cp_hdmi_hits: int
    fx6_cp_sdi_hits: int
    sdi_blocking_wait_eliminated: bool
    sample_evals: Tuple[HdmiSdiTcBridgeEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PeripheralCompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    subsystem_counts: Dict[str, int]
    touchpoints: Tuple[PeripheralTouchpointEntry, ...]


@dataclass(frozen=True)
class RealhwLensIbisAudioHdmiPeripheralBridgeReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    p18_lens_writes_permitted: bool
    ibis_coil_safe_park_verified: bool
    sdi_blocking_wait_eliminated: bool
    persistent_emmc_writes_authorized: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    donor_file_sizes: Dict[str, int]
    pillar1_lens_p18: Pillar1LensP18Report
    pillar2_ibis_catalyst: Pillar2IbisCatalystReport
    pillar3_audio_xlrh1: Pillar3AudioXlrh1Report
    pillar4_hdmi_sdi_tc: Pillar4HdmiSdiTcReport
    compatibility_matrix: PeripheralCompatMatrixSummary
    volatile_guard_ok: Phase146WriteGuardResult
    forbidden_p18_guard_blocked: Phase146WriteGuardResult
    forbidden_p12_guard_blocked: Phase146WriteGuardResult
    forbidden_backup_guard_blocked: Phase146WriteGuardResult
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only Binary Helpers (os.O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------


def _read_bytes_rdonly(path: Path) -> bytes:
    """Strictly open and read a donor file via `os.O_RDONLY` + `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return b""
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            return bytes(mm[:])
    finally:
        os.close(fd)


def _count_tokens_single_pass(buf: bytes | mmap.mmap, tokens: Sequence[str]) -> Dict[str, int]:
    """Count exact ASCII token hits in a single compiled regex pass."""
    if not tokens:
        return {}
    encoded = [t.encode("ascii") for t in tokens]
    pat = re.compile(b"|".join(re.escape(e) for e in encoded))
    counts: Dict[bytes, int] = {e: 0 for e in encoded}
    for m in pat.finditer(buf):
        tok = m.group(0)
        counts[tok] = counts.get(tok, 0) + 1
    return {t: counts[t.encode("ascii")] for t in tokens}


def _scan_elf_and_tokens_buf(
    buf: bytes | mmap.mmap,
    *,
    binary_name: str,
    body_label: str,
    source_mode: str,
    tokens: Sequence[str] = (),
) -> Tuple[ElfSectionSummary, set[str], set[str]]:
    """Fast pure-Python ELF64 `.dynsym`/`.dynstr`/`.dynamic` + single-pass token scan."""
    sz = len(buf)
    if sz < 64 or buf[:4] != b"\x7fELF" or buf[4] != 2 or buf[5] != 1:
        raise ValueError(f"Invalid ELF64 LSB header for {binary_name}")

    (e_shoff,) = struct.unpack_from("<Q", buf, 40)
    e_shentsize, e_shnum, _ = struct.unpack_from("<HHH", buf, 58)

    dynsym_sh: Optional[Tuple[int, int, int]] = None
    dynamic_sh: Optional[Tuple[int, int, int]] = None
    for idx in range(e_shnum):
        off = e_shoff + idx * e_shentsize
        if off + 64 > sz:
            break
        (sh_type,) = struct.unpack_from("<I", buf, off + 4)
        if sh_type == 11:  # SHT_DYNSYM
            _, d_off, d_sz, d_link = struct.unpack_from("<QQQI", buf, off + 16)
            dynsym_sh = (d_off, d_sz, d_link)
        elif sh_type == 6:  # SHT_DYNAMIC
            _, d_off, d_sz, d_link = struct.unpack_from("<QQQI", buf, off + 16)
            dynamic_sh = (d_off, d_sz, d_link)

    exports: set[str] = set()
    imports: set[str] = set()
    if dynsym_sh is not None:
        d_off, d_sz, d_link = dynsym_sh
        str_hdr = e_shoff + d_link * e_shentsize
        _, s_off, s_sz = struct.unpack_from("<QQQ", buf, str_hdr + 16)
        dynstr = buf[s_off : s_off + s_sz]
        dynsym = buf[d_off : d_off + d_sz]
        for st_name, _st_info, _st_other, st_shndx, _st_val, _st_size in struct.iter_unpack(
            "<IBBHQQ", dynsym
        ):
            if st_name == 0 or st_name >= len(dynstr):
                continue
            end = dynstr.find(b"\x00", st_name)
            if end == -1:
                continue
            name = dynstr[st_name:end].decode("ascii", errors="replace")
            if st_shndx == 0:
                imports.add(name)
            else:
                exports.add(name)

    dt_needed: List[str] = []
    if dynamic_sh is not None:
        dyn_off, dyn_sz, dyn_link = dynamic_sh
        str_hdr = e_shoff + dyn_link * e_shentsize
        _, s_off, s_sz = struct.unpack_from("<QQQ", buf, str_hdr + 16)
        dynstr = buf[s_off : s_off + s_sz]
        dyn_bytes = buf[dyn_off : dyn_off + dyn_sz]
        for d_tag, d_val in struct.iter_unpack("<Qq", dyn_bytes):
            if d_tag == 0:
                break
            if d_tag == 1 and 0 <= d_val < len(dynstr):
                end = dynstr.find(b"\x00", d_val)
                if end != -1:
                    dt_needed.append(dynstr[d_val:end].decode("ascii", errors="replace"))

    hits = _count_tokens_single_pass(buf, tokens)
    summary = ElfSectionSummary(
        binary_name=binary_name,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=sz,
        export_count=len(exports),
        import_count=len(imports),
        dt_needed=tuple(dt_needed),
        marker_hits=hits,
    )
    return summary, exports, imports


def _scan_elf_and_tokens_rdonly(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str] = (),
) -> Tuple[ElfSectionSummary, set[str], set[str]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            return _scan_elf_and_tokens_buf(
                mm,
                binary_name=binary_name,
                body_label=body_label,
                source_mode="LOCAL_DONOR_RDONLY",
                tokens=tokens,
            )
    finally:
        os.close(fd)


def _scan_binary_tokens_rdonly(path: Path, tokens: Sequence[str]) -> Tuple[int, Dict[str, int]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {t: 0 for t in tokens}
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            return sz, _count_tokens_single_pass(mm, tokens)
    finally:
        os.close(fd)


def _scan_elf_ro_markers_rdonly(path: Path, tokens: Sequence[str]) -> Tuple[int, Dict[str, int]]:
    """Fast targeted ELF `.dynstr`/`.rodata`/`.strtab` single-pass scan (for 79 MB appFw.so)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = os.fstat(fd).st_size
        if sz == 0:
            return 0, {t: 0 for t in tokens}
        with mmap.mmap(fd, sz, access=mmap.ACCESS_READ) as mm:
            encoded = [t.encode("ascii") for t in tokens]
            pat = re.compile(b"|".join(re.escape(e) for e in encoded))
            counts: Dict[bytes, int] = {e: 0 for e in encoded}
            scanned_sections = False
            if sz >= 64 and mm[:4] == b"\x7fELF" and mm[4] == 2 and mm[5] == 1:
                (e_shoff,) = struct.unpack_from("<Q", mm, 40)
                e_shentsize, e_shnum, e_shstrndx = struct.unpack_from("<HHH", mm, 58)
                if e_shoff > 0 and e_shnum > 0 and e_shstrndx < e_shnum:
                    shstr_hdr = e_shoff + e_shstrndx * e_shentsize
                    if shstr_hdr + 40 <= sz:
                        _, s_off, s_sz = struct.unpack_from("<QQQ", mm, shstr_hdr + 16)
                        if s_off + s_sz <= sz:
                            shstr = mm[s_off : s_off + s_sz]
                            for idx in range(e_shnum):
                                off = e_shoff + idx * e_shentsize
                                if off + 64 > sz:
                                    break
                                sh_name, sh_type = struct.unpack_from("<II", mm, off)
                                if sh_type == 8:
                                    continue
                                _, sec_off, sec_sz = struct.unpack_from("<QQQ", mm, off + 16)
                                if sec_off + sec_sz <= sz and sh_name < len(shstr):
                                    end_n = shstr.find(b"\x00", sh_name)
                                    sname = shstr[sh_name:end_n] if end_n != -1 else b""
                                    if sname.startswith((b".dynstr", b".rodata", b".strtab")):
                                        scanned_sections = True
                                        for m in pat.finditer(mm, sec_off, sec_off + sec_sz):
                                            tok = m.group(0)
                                            counts[tok] = counts.get(tok, 0) + 1
            if not scanned_sections:
                for m in pat.finditer(mm):
                    tok = m.group(0)
                    counts[tok] = counts.get(tok, 0) + 1
            return sz, {t: counts[t.encode("ascii")] for t in tokens}
    finally:
        os.close(fd)


# ---------------------------------------------------------------------------
# Clean-Room Fixture Builders (Zero Proprietary Files Required)
# ---------------------------------------------------------------------------


def _build_synthetic_elf64(
    *,
    exports: Sequence[str],
    imports: Sequence[str],
    dt_needed: Sequence[str],
    rodata_strings: Sequence[str] = (),
) -> bytes:
    """Build a valid minimal ELF64 AArch64 ET_DYN binary parseable by `_scan_elf_and_tokens_buf`."""
    dynstr = bytearray(b"\x00")
    str_offsets: Dict[str, int] = {}

    def intern(s: str) -> int:
        if s not in str_offsets:
            str_offsets[s] = len(dynstr)
            dynstr.extend(s.encode("ascii") + b"\x00")
        return str_offsets[s]

    for s in dt_needed:
        intern(s)
    for s in exports:
        intern(s)
    for s in imports:
        intern(s)

    dynsym = bytearray(24)  # STN_UNDEF
    for name in exports:
        dynsym.extend(struct.pack("<IBBHQQ", intern(name), 0x12, 0, 1, 0x1000, 0))
    for name in imports:
        dynsym.extend(struct.pack("<IBBHQQ", intern(name), 0x10, 0, 0, 0, 0))

    dynamic = bytearray()
    for dep in dt_needed:
        dynamic.extend(struct.pack("<Qq", 1, intern(dep)))
    dynamic.extend(struct.pack("<Qq", 0, 0))

    rodata = b"\x00".join(s.encode("ascii") for s in rodata_strings) + b"\x00"
    shstrtab = b"\x00.dynstr\x00.dynsym\x00.dynamic\x00.rodata\x00.shstrtab\x00"

    off_dynstr = 64
    off_dynsym = off_dynstr + len(dynstr)
    off_dynamic = off_dynsym + len(dynsym)
    off_rodata = off_dynamic + len(dynamic)
    off_shstr = off_rodata + len(rodata)
    e_shoff = off_shstr + len(shstrtab)

    ehdr = bytearray(64)
    ehdr[0:16] = b"\x7fELF\x02\x01\x01\x00" + bytes(8)
    struct.pack_into("<HHIQQQIHHHHHH", ehdr, 16, 3, 183, 1, 0, 0, e_shoff, 0, 64, 0, 0, 64, 6, 5)

    sh_null = bytes(64)
    sh_dynstr = struct.pack("<IIQQQQIIQQ", 1, 3, 2, off_dynstr, off_dynstr, len(dynstr), 0, 0, 1, 0)
    sh_dynsym = struct.pack("<IIQQQQIIQQ", 9, 11, 2, off_dynsym, off_dynsym, len(dynsym), 1, 1, 8, 24)
    sh_dynamic = struct.pack("<IIQQQQIIQQ", 17, 6, 3, off_dynamic, off_dynamic, len(dynamic), 1, 0, 8, 16)
    sh_rodata = struct.pack("<IIQQQQIIQQ", 26, 1, 2, off_rodata, off_rodata, len(rodata), 0, 0, 1, 0)
    sh_shstr = struct.pack("<IIQQQQIIQQ", 34, 3, 0, off_shstr, off_shstr, len(shstrtab), 0, 0, 1, 0)

    return (
        bytes(ehdr)
        + bytes(dynstr)
        + bytes(dynsym)
        + bytes(dynamic)
        + rodata
        + shstrtab
        + sh_null
        + sh_dynstr
        + sh_dynsym
        + sh_dynamic
        + sh_rodata
        + sh_shstr
    )


def _build_synthetic_bk4_backup_bin(*, subsystem_count: int, body_tag: bytes) -> bytes:
    """Build a valid dual-record `BK4\\x00` + `0x00fa0080` descriptor Backup.bin fixture."""
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
            subsystem_count,
            2048,
            BK4_HEADER_BYTES,
            len(table),
            0,
        )
        body = bytes(hdr) + bytes(table)
        csum = (sum(body) - sum(body[32:36])) & 0xFFFFFFFF
        struct.pack_into("<I", hdr, 32, csum)
        return bytes(hdr) + bytes(table)

    rec0 = _make_record("\\av-cam.bin")
    rec1 = _make_record("\\sabin\\idt_cam.bin")
    return rec0 + rec1


def build_clean_room_realhw_peripheral_bridge_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room fixtures covering all 4 Phase 146 subsystems."""
    lens_exports = [f"LensComm_Export_{i:02d}" for i in range(EXPECTED_LENS_COMM_EXPORTS)]
    lens_imports = [f"LensComm_Import_{i:02d}" for i in range(EXPECTED_LENS_COMM_IMPORTS)]
    lens_deps = ("libpthread.so.0", "libstdc++.so.6", "libm.so.6", "libc.so.6")
    fx3_lens_comm = _build_synthetic_elf64(exports=lens_exports, imports=lens_imports, dt_needed=lens_deps)
    fx6_lens_comm = _build_synthetic_elf64(exports=lens_exports, imports=lens_imports, dt_needed=lens_deps)

    sencore_exports = [
        "SenserIfStart",
        "SenserIfStop",
        "SenserIfSend",
        "MiconAccessFunc",
        "AdjustControlFunc",
    ] + [f"Sencore_Sym_{i:03d}" for i in range(EXPECTED_SENCORE_EXPORTS - 5)]
    sencore_imports = [f"Sencore_Imp_{i:03d}" for i in range(EXPECTED_SENCORE_IMPORTS)]
    sencore_deps = ("libosal_uipc.so", "libInfraUsbCmn.so", "libpthread.so.0", "libc.so.6")
    sencore_ro = list(SENCORE_SHARED_MARKERS)
    fx3_sencore = _build_synthetic_elf64(
        exports=sencore_exports, imports=sencore_imports, dt_needed=sencore_deps, rodata_strings=sencore_ro
    )
    fx6_sencore = _build_synthetic_elf64(
        exports=sencore_exports, imports=sencore_imports, dt_needed=sencore_deps, rodata_strings=sencore_ro
    )

    fx3_appfw = _build_synthetic_elf64(
        exports=["appFw_main"],
        imports=["SenserIfSend"],
        dt_needed=("libmpr.so",),
        rodata_strings=(
            list(LENS_APPFW_FX3_MARKERS)
            + list(IBIS_APPFW_FX3_MARKERS)
            + list(AUDIO_APPFW_FX3_MARKERS)
            + list(HDMI_APPFW_FX3_MARKERS)
        ),
    )
    fx6_appfw = _build_synthetic_elf64(
        exports=["appFw_main"],
        imports=["SenserIfSend"],
        dt_needed=("libmpr.so",),
        rodata_strings=(
            list(LENS_APPFW_FX6_MARKERS)
            + list(IBIS_APPFW_FX6_MARKERS)
            + list(AUDIO_APPFW_FX6_MARKERS)
            + list(HDMI_SDI_APPFW_FX6_MARKERS)
        ),
    )

    fx3_libmpr = _build_synthetic_elf64(
        exports=list(IBIS_MPR_GYRO_FX3_MARKERS),
        imports=["osal_valloc_msg_wait"],
        dt_needed=("libosal_uipc.so", "libc.so.6"),
        rodata_strings=list(IBIS_MPR_GYRO_FX3_MARKERS),
    )
    fx6_libmpr = _build_synthetic_elf64(
        exports=list(IBIS_MPR_GYRO_FX6_MARKERS),
        imports=["osal_valloc_msg_wait"],
        dt_needed=("libosal_uipc.so", "libc.so.6"),
        rodata_strings=list(IBIS_MPR_GYRO_FX6_MARKERS),
    )

    hotshoe_exports = list(HOTSHOE_MARKERS) + [f"Hotshoe_Exp_{i:02d}" for i in range(76 - len(HOTSHOE_MARKERS))]
    hotshoe_imports = [f"Hotshoe_Imp_{i:02d}" for i in range(44)]
    fx6_hotshoe = _build_synthetic_elf64(
        exports=hotshoe_exports,
        imports=hotshoe_imports,
        dt_needed=("libInfraInput.so", "libc.so.6"),
        rodata_strings=list(HOTSHOE_MARKERS),
    )
    fx6_avbb_audio = _build_synthetic_elf64(
        exports=["AvbbScnStartAudio"],
        imports=["Backup_read"],
        dt_needed=("libInfraAvbbc.so", "libc.so.6"),
        rodata_strings=list(AVBB_AUDIO_MARKERS),
    )

    fx3_avbbc = _build_synthetic_elf64(
        exports=list(AVBBC_BRIDGE_SYMBOLS) + ["ParameterControl"],
        imports=[],
        dt_needed=("libMWF.so", "libc.so.6"),
        rodata_strings=list(AVBBC_BRIDGE_SYMBOLS),
    )
    fx6_avbbc = _build_synthetic_elf64(
        exports=list(AVBBC_BRIDGE_SYMBOLS) + ["ParameterControl"],
        imports=[],
        dt_needed=("libMWF.so", "libc.so.6"),
        rodata_strings=list(AVBBC_BRIDGE_SYMBOLS),
    )

    fx3_cpapp = (
        b"SYNTH_FX3_CPAPP\x00"
        + (b"LiroSeq\x00" * 10)
        + b"SteadyShot\x00GyroPIDOUT_0\x00GyroStart\x00GyroStop\x00"
        + (b"HDMI\x00" * 4)
        + b"SDI\x00Tcub\x00"
    )
    fx6_cpapp = (
        b"SYNTH_FX6_CPAPP\x00"
        + (b"LiroSeq\x00" * 4)
        + b"SteadyShot\x00GyroPIDOUT_0\x00GyroStart\x00GyroStop\x00"
        + (b"HDMI\x00" * 4)
        + (b"SDI\x00" * 6)
        + b"Tcub\x00"
    )

    fx3_backup = _build_synthetic_bk4_backup_bin(subsystem_count=819, body_tag=b"ALCIN_UUD")
    fx6_backup = _build_synthetic_bk4_backup_bin(subsystem_count=840, body_tag=b"CHAPLIN")

    return {
        "fx3_lens_comm": fx3_lens_comm,
        "fx6_lens_comm": fx6_lens_comm,
        "fx3_sencore": fx3_sencore,
        "fx6_sencore": fx6_sencore,
        "fx3_appfw": fx3_appfw,
        "fx6_appfw": fx6_appfw,
        "fx3_libmpr": fx3_libmpr,
        "fx6_libmpr": fx6_libmpr,
        "fx6_hotshoe": fx6_hotshoe,
        "fx6_avbb_audio": fx6_avbb_audio,
        "fx3_avbbc": fx3_avbbc,
        "fx6_avbbc": fx6_avbbc,
        "fx3_cpapp": fx3_cpapp,
        "fx6_cpapp": fx6_cpapp,
        "fx3_backup": fx3_backup,
        "fx6_backup": fx6_backup,
    }


# ---------------------------------------------------------------------------
# Public Evaluators (Positive & Negative Test Surfaces)
# ---------------------------------------------------------------------------


def evaluate_emount_lens_p18_bridge(
    *,
    lens_mounted: bool = True,
    focal_length_mm: float = 35.0,
    aperture_display_unit: str = "T_STOP",
    focus_distance_unit: str = "METER",
    breathing_comp_enabled: bool = True,
    distortion_comp_enabled: bool = True,
    shading_comp_enabled: bool = True,
    write_target: Optional[str] = None,
) -> LensP18BridgeEvalResult:
    """Evaluate E-Mount lens metadata / compensation compatibility & p18:/lens RO protection."""
    errors: List[str] = []
    ap_unit = aperture_display_unit.strip().upper()
    fd_unit = focus_distance_unit.strip().upper()

    if ap_unit not in VALID_IRIS_DISPLAY_UNITS:
        errors.append(f"BLOCKED_INVALID_IRIS_DISPLAY_UNIT: {ap_unit!r}")
    if fd_unit not in VALID_FOCUS_DISTANCE_UNITS:
        errors.append(f"BLOCKED_INVALID_FOCUS_DISTANCE_UNIT: {fd_unit!r}")
    if lens_mounted and (focal_length_mm <= 0.0 or focal_length_mm > 2000.0):
        errors.append(f"BLOCKED_INVALID_LENS_FOCAL_LENGTH_MM: {focal_length_mm}")

    write_blocked = False
    if write_target is not None:
        target = write_target.strip()
        if FORBIDDEN_PERSISTENT_NVS_OR_EMMC_RE_P146.search(target) or "lens" in target.lower():
            write_blocked = True
            errors.append(
                f"BLOCKED_P18_LENS_WRITE_PROTECTED: p18 (/dev/nflasha18, /lens) is strictly O_RDONLY ({target!r})"
            )
            return LensP18BridgeEvalResult(
                valid=False,
                status="BLOCKED_P18_LENS_WRITE_PROTECTED",
                lens_mounted=lens_mounted,
                focal_length_mm=focal_length_mm,
                aperture_display_unit=ap_unit,
                focus_distance_unit=fd_unit,
                breathing_comp_enabled=breathing_comp_enabled,
                distortion_comp_enabled=distortion_comp_enabled,
                shading_comp_enabled=shading_comp_enabled,
                classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
                p18_lens_writes_permitted=False,
                write_attempt_blocked=True,
                errors=tuple(errors),
            )

    classification = (
        BRIDGE_CLASS_SHIM_TRANSLATED
        if ap_unit == "T_STOP" or breathing_comp_enabled
        else BRIDGE_CLASS_NATIVE_PASSTHROUGH
    )
    status = "EMOUNT_LENS_P18_READONLY_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return LensP18BridgeEvalResult(
        valid=len(errors) == 0,
        status=status,
        lens_mounted=lens_mounted,
        focal_length_mm=focal_length_mm,
        aperture_display_unit=ap_unit,
        focus_distance_unit=fd_unit,
        breathing_comp_enabled=breathing_comp_enabled,
        distortion_comp_enabled=distortion_comp_enabled,
        shading_comp_enabled=shading_comp_enabled,
        classification=classification,
        p18_lens_writes_permitted=False,
        write_attempt_blocked=write_blocked,
        errors=tuple(errors),
    )


def evaluate_ibis_vs_catalyst_bridge(
    *,
    requested_mode: str = "OFF",
    catalyst_gyro_metadata: bool = True,
    park_coils_on_off: bool = True,
    mask_rigid_sensor_query: bool = True,
    direct_nvs_write: bool = False,
) -> IbisCatalystBridgeEvalResult:
    """Evaluate FX3 5-axis physical IBIS vs FX6 rigid-CMOS Catalyst gyro bridge & coil park safety."""
    req = requested_mode.strip().upper()
    errors: List[str] = []

    if req not in IBIS_MODES_FX6_UI:
        errors.append(f"BLOCKED_UNKNOWN_STEADYSHOT_MODE: {req!r}")
    if direct_nvs_write:
        errors.append("BLOCKED_NVS_IBIS_CALIBRATION_WRITE: Backup.bin/psd.bin/Jiritsu strictly read-only")
    if not mask_rigid_sensor_query:
        errors.append("BLOCKED_UNMASKED_RIGID_SENSOR_FAULT: FX6 PRM_is_imager_stabilization_unit_fixed would conflict")

    if req in ("OFF",):
        fx3_mode = "OFF"
        coil_parked = park_coils_on_off
        classification = BRIDGE_CLASS_SHIM_TRANSLATED
        if not park_coils_on_off:
            errors.append("BLOCKED_UNPARKED_FLOATING_IBIS_COILS: Off mode must issue 0x0400->0x1400 Center-Lock")
    elif req == "STANDARD":
        fx3_mode = "STANDARD"
        coil_parked = False
        classification = BRIDGE_CLASS_NATIVE_PASSTHROUGH if not mask_rigid_sensor_query else BRIDGE_CLASS_SHIM_TRANSLATED
    elif req == "ACTIVE":
        fx3_mode = "ACTIVE"
        coil_parked = False
        classification = BRIDGE_CLASS_SHIM_TRANSLATED
    elif req == "ACTIVE_PLUS":
        # FX6/newer hybrid electronic gyro-crop mode clamps safely to FX3 5-axis ACTIVE
        fx3_mode = "ACTIVE"
        coil_parked = False
        classification = BRIDGE_CLASS_SHIM_TRANSLATED
    else:
        fx3_mode = "OFF"
        coil_parked = False
        classification = BRIDGE_CLASS_HARD_WRITE_PROTECTED

    if direct_nvs_write:
        classification = BRIDGE_CLASS_HARD_WRITE_PROTECTED

    safe_park_verified = (req != "OFF") or (coil_parked and not direct_nvs_write)
    status = "IBIS_CATALYST_BRIDGE_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return IbisCatalystBridgeEvalResult(
        valid=len(errors) == 0,
        status=status,
        requested_mode=req,
        fx3_effective_mode=fx3_mode,
        classification=classification,
        coil_parked_center_lock=coil_parked,
        ibis_coil_safe_park_verified=safe_park_verified and len(errors) == 0,
        gyro_rtmd_2000hz_active=catalyst_gyro_metadata,
        rigid_sensor_query_masked=mask_rigid_sensor_query,
        nvs_calibration_writes=0,
        errors=tuple(errors),
    )


def evaluate_mishoe_xlrh1_audio_bridge(
    *,
    handle_state: str = "XLR_H1_ATTACHED",
    sample_rate_hz: int = AUDIO_LPCM_SAMPLE_RATE_HZ,
    bit_depth: int = AUDIO_LPCM_BIT_DEPTH,
    enable_nonblock_hot_detach: bool = True,
) -> AudioXlrh1BridgeEvalResult:
    """Evaluate MI-Shoe XLR-H1 4ch 24-bit LPCM vs internal/TRS fallback & P11 E_TMO containment."""
    hs = handle_state.strip().upper()
    errors: List[str] = []

    if hs not in VALID_AUDIO_HANDLE_STATES:
        errors.append(f"BLOCKED_UNKNOWN_AUDIO_HANDLE_STATE: {hs!r}")
    if sample_rate_hz != AUDIO_LPCM_SAMPLE_RATE_HZ:
        errors.append(f"BLOCKED_INVALID_AUDIO_SAMPLE_RATE: {sample_rate_hz} != {AUDIO_LPCM_SAMPLE_RATE_HZ}")
    if bit_depth != AUDIO_LPCM_BIT_DEPTH:
        errors.append(f"BLOCKED_INVALID_AUDIO_BIT_DEPTH: {bit_depth} != {AUDIO_LPCM_BIT_DEPTH}")
    if hs != "XLR_H1_ATTACHED" and not enable_nonblock_hot_detach:
        errors.append("BLOCKED_PHANTOM_SMART_HANDLE_TIMEOUT: P11 0x91db059b E_TMO=-50 requires 0x8000 non-blocking rc")

    if hs == "XLR_H1_ATTACHED":
        routing = {
            "CH1": "XLR_H1_INPUT_1",
            "CH2": "XLR_H1_INPUT_2",
            "CH3": "XLR_H1_35MM_OR_INTERNAL_L",
            "CH4": "XLR_H1_35MM_OR_INTERNAL_R",
        }
        active_ch = 4
        classification = BRIDGE_CLASS_NATIVE_PASSTHROUGH
    elif hs == "TRS_JACK_ONLY":
        routing = {
            "CH1": "BODY_35MM_TRS_L",
            "CH2": "BODY_35MM_TRS_R",
            "CH3": "SILENCE_ZERO_PADDED",
            "CH4": "SILENCE_ZERO_PADDED",
        }
        active_ch = 2
        classification = BRIDGE_CLASS_SHIM_TRANSLATED
    else:  # XLR_H1_DETACHED
        routing = {
            "CH1": "BODY_INTERNAL_MIC_L",
            "CH2": "BODY_INTERNAL_MIC_R",
            "CH3": "SILENCE_ZERO_PADDED",
            "CH4": "SILENCE_ZERO_PADDED",
        }
        active_ch = 2
        classification = BRIDGE_CLASS_SHIM_TRANSLATED

    bitrate = sample_rate_hz * bit_depth * 4 if hs == "XLR_H1_ATTACHED" else sample_rate_hz * bit_depth * active_ch
    timeout_eliminated = enable_nonblock_hot_detach and len(errors) == 0
    status = "MISHOE_AUDIO_4CH_BRIDGE_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return AudioXlrh1BridgeEvalResult(
        valid=len(errors) == 0,
        status=status,
        handle_state=hs,
        sample_rate_hz=sample_rate_hz,
        bit_depth=bit_depth,
        active_channels=active_ch,
        bitrate_bps=bitrate,
        channel_routing=routing,
        classification=classification,
        p11_nonblock_rc_hex=f"0x{HOTSHOE_NONBLOCK_SAFE_RC:04x}",
        phantom_device_timeout_eliminated=timeout_eliminated,
        errors=tuple(errors),
    )


def evaluate_hdmi_sdi_tc_bridge(
    *,
    requested_interface: str = "12G_SDI_OUT",
    mask_absent_hw: bool = True,
    stub_blocking_wait_ms: int = 0,
    in_uart_boot: bool = False,
) -> HdmiSdiTcBridgeEvalResult:
    """Evaluate HDMI Type-A + Multi-USB TC-IN vs FX6 12G-SDI / BNC TC / Genlock / Darwin ND."""
    req = requested_interface.strip().upper()
    errors: List[str] = []

    if req in FX6_ABSENT_HW_PERIPHERALS:
        fx3_target = "HDMI_TYPE_A" if req == "12G_SDI_OUT" else (
            "MULTI_USB_VMC_BNCM1_TC_IN" if req == "BNC_TC_OUT" else "NO_OP_STUB"
        )
        if not mask_absent_hw:
            errors.append(
                f"BLOCKED_UNMASKED_ABSENT_FX6_HW: {req} missing on FX3; appFw would hang waiting for FPGA/BNC"
            )
        if stub_blocking_wait_ms > 0:
            errors.append(
                f"BLOCKED_SDI_BLOCKING_WAIT_TIMEOUT: stub_blocking_wait_ms={stub_blocking_wait_ms} > 0"
            )
        classification = BRIDGE_CLASS_MASKED_ABSENT_HW
        sdi_eliminated = mask_absent_hw and (stub_blocking_wait_ms == 0)
        status = "ABSENT_HW_NONBLOCKING_STUB_VERIFIED" if not errors else errors[0].split(":", 1)[0]
        return HdmiSdiTcBridgeEvalResult(
            valid=len(errors) == 0,
            status=status,
            requested_interface=req,
            fx3_target_interface=fx3_target,
            classification=classification,
            non_blocking_stub_rc=0 if not errors else -1,
            stub_blocking_wait_ms=stub_blocking_wait_ms,
            sdi_blocking_wait_eliminated=sdi_eliminated,
            in_uart_boot_safe=True,
            errors=tuple(errors),
        )

    if req == "MULTI_USB_TC_IN":
        if in_uart_boot:
            errors.append(
                "BLOCKED_VMC_BNCM1_DURING_UART_BOOT: Disconnect VMC-BNCM1 from Multi-Port (shared pins 7/8/9)"
            )
        if stub_blocking_wait_ms > 0:
            errors.append(f"BLOCKED_TC_BLOCKING_WAIT: stub_blocking_wait_ms={stub_blocking_wait_ms} > 0")
        status = "MULTI_USB_TC_IN_VERIFIED" if not errors else errors[0].split(":", 1)[0]
        return HdmiSdiTcBridgeEvalResult(
            valid=len(errors) == 0,
            status=status,
            requested_interface=req,
            fx3_target_interface="MULTI_USB_VMC_BNCM1_LTC_IN",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            non_blocking_stub_rc=0,
            stub_blocking_wait_ms=stub_blocking_wait_ms,
            sdi_blocking_wait_eliminated=True,
            in_uart_boot_safe=not in_uart_boot,
            errors=tuple(errors),
        )

    if req in HDMI_TYPE_A_CAPABILITIES or req in ("HDMI_CLEAN_OSD", "HDMI_4K60", "HDMI_RAW16"):
        if stub_blocking_wait_ms > 0:
            errors.append(f"BLOCKED_HDMI_BLOCKING_WAIT: stub_blocking_wait_ms={stub_blocking_wait_ms} > 0")
        status = "HDMI_TYPE_A_NATIVE_VERIFIED" if not errors else errors[0].split(":", 1)[0]
        return HdmiSdiTcBridgeEvalResult(
            valid=len(errors) == 0,
            status=status,
            requested_interface=req,
            fx3_target_interface="HDMI_TYPE_A",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            non_blocking_stub_rc=0,
            stub_blocking_wait_ms=stub_blocking_wait_ms,
            sdi_blocking_wait_eliminated=True,
            in_uart_boot_safe=True,
            errors=tuple(errors),
        )

    errors.append(f"BLOCKED_UNKNOWN_VIDEO_TC_INTERFACE: {req!r}")
    return HdmiSdiTcBridgeEvalResult(
        valid=False,
        status="BLOCKED_UNKNOWN_VIDEO_TC_INTERFACE",
        requested_interface=req,
        fx3_target_interface="UNKNOWN",
        classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
        non_blocking_stub_rc=-1,
        stub_blocking_wait_ms=stub_blocking_wait_ms,
        sdi_blocking_wait_eliminated=False,
        in_uart_boot_safe=not in_uart_boot,
        errors=tuple(errors),
    )


def evaluate_phase146_write_guard(target_path: str) -> Phase146WriteGuardResult:
    """Enforce volatile RAM staging only and zero persistent eMMC / p18:/lens / NVS mutations."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES_P146) and not bool(
        FORBIDDEN_PERSISTENT_NVS_OR_EMMC_RE_P146.search(norm)
    )
    if is_volatile:
        return Phase146WriteGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            p18_lens_writes_permitted=False,
            emmc_mutation_bytes=0,
            calibration_mutation_bytes=0,
            errors=(),
        )
    return Phase146WriteGuardResult(
        valid=False,
        status="BLOCKED_PERSISTENT_EMMC_OR_P18_WRITE",
        target_path=norm,
        volatile_ram_staged=False,
        persistent_write_blocked=True,
        p18_lens_writes_permitted=False,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        errors=(f"BLOCKED_PERSISTENT_EMMC_OR_P18_WRITE: target_path={norm!r}",),
    )


def build_phase146_compatibility_matrix() -> PeripheralCompatMatrixSummary:
    """Construct the quantitative 16-touchpoint cross-body peripheral compatibility matrix."""
    entries: Tuple[PeripheralTouchpointEntry, ...] = (
        PeripheralTouchpointEntry(
            touchpoint_id="LENS_COMM_ELF_IPC",
            subsystem="LENS_P18",
            fx6_interface="libInfraLensCommunicator.so E-Mount 12-pin",
            fx3_target="Stock FX3 libInfraLensCommunicator.so + cpapp-b.bin",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_layer="None (ABI identical: 27 exports / 25 imports)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="AF, Iris, PowerZoom, and FocalLength read-only IPC pass through natively.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="LENS_METADATA_T_STOP_FT_M",
            subsystem="LENS_P18",
            fx6_interface="T/F-Stop, ft/m Focus Distance, Breathing/Distortion/Shading",
            fx3_target="FX3 appFw/libmpr UDAM & RTMD Lens Meta",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_layer="libgrm-fbinit9.so + BK4 volatile RAM shadow",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Unit conversion (T/F-stop, ft/m) and breathing crop gated in volatile RAM.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="LENS_P18_FACTORY_CALIB",
            subsystem="LENS_P18",
            fx6_interface="p18:/lens/lensfile.bin (FX6 LBA 0x00312000)",
            fx3_target="/dev/nflasha18 p18:/lens (FX3 LBA 0x0031C000)",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            shim_layer="Hard O_RDONLY Guard (p18_lens_writes_permitted=False)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Factory E-Mount optical calibration partition is strictly read-only.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="IBIS_STANDARD_5AXIS",
            subsystem="IBIS_IMU",
            fx6_interface="SteadyShot Standard (Rigid-CMOS query)",
            fx3_target="FX3 Stock-CP 5-Axis Physical IBIS (LiroSeq)",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_layer="libgrm-fbinit9.so ParameterControl + Stock-CP",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Masks PRM_is_imager_stabilization_unit_fixed so FX3 5-axis IBIS engages cleanly.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="IBIS_OFF_CENTER_LOCK_PARK",
            subsystem="IBIS_IMU",
            fx6_interface="SteadyShot Off / Catalyst Gyro-Only",
            fx3_target="Stock-CP 0x0400 -> 0x1400 Center-Lock + 2000Hz RTMD",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_layer="libgrm-fbinit9.so Safe-Park Policy",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Prevents floating/unparked voice-coils by energizing 0x0400->0x1400 Center-Lock.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="IBIS_CATALYST_UDAM_RTMD",
            subsystem="IBIS_IMU",
            fx6_interface="libmpr UDAMSetGyroscopeValue / Accelerometer",
            fx3_target="FX3 libmpr.so 2000Hz Gyro/Accel KLV RTMD",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_layer="None (shared libmpr UDAM serializers)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Catalyst Browse / Gyroflow 2000 Hz metadata shares identical UDAM KLV paths.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="IBIS_FACTORY_NVS_CALIB",
            subsystem="IBIS_IMU",
            fx6_interface="p2:/Backup.bin + p2:/psd.bin + p6:Jiritsu",
            fx3_target="FX3 Stock-CP factory gyro/hall calibration NVS",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            shim_layer="Hard O_RDONLY Guard + BK4 RAM shadow",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Zero mutations to Backup.bin, psd.bin, defdet.bin, or p6 Jiritsu.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="AUDIO_XLR_H1_4CH_LPCM",
            subsystem="AUDIO_XLRH1",
            fx6_interface="FX6 Smart Handle CH1..CH4 24-bit 48kHz LPCM",
            fx3_target="FX3 XLR-H1 MI-Shoe Digital Audio (4.608 Mbps)",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_layer="None (shared 48kHz/24bit/4ch AVBB/MPR contract)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Physical XLR-H1 top handle maps directly to CH1..CH4 audio status & OSD.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="AUDIO_DETACHED_FALLBACK",
            subsystem="AUDIO_XLRH1",
            fx6_interface="libInfraHotshoe.so P11 0x91db059b (E_TMO=-50)",
            fx3_target="FX3 Internal Stereo Mic / 3.5mm TRS + CH3/CH4 Mute",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_layer="libgrm-fbinit9.so + P11 0x8000 Non-Blocking Rc",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Eliminates phantom Smart-Handle timeout when XLR-H1 is detached.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="AUDIO_35MM_HEADPHONE_JACK",
            subsystem="AUDIO_XLRH1",
            fx6_interface="Headphone Monitor & Mic-In Jack Events",
            fx3_target="FX3 Body 3.5mm Mic-In & Headphone Jacks",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_layer="None (shared EVENT_INPUT_KEY_JACK_MICJACK_IN / HEADPHONE_CONNECT)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Direct body jack detection without handle dependency.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="HDMI_TYPE_A_4K60_RAW_OSD",
            subsystem="HDMI_SDI_TC",
            fx6_interface="HDMI Monitor Out (4K60 / 16-bit RAW / Clean OSD)",
            fx3_target="FX3 Full-Size HDMI Type-A Output",
            classification=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            shim_layer="None (shared HDMI_RAW / HDMI_INFO_DISPLAY / AvbbcCmn)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="4264x2408 16-bit RAW, 4K60 10-bit 4:2:2, and Clean/OSD toggle work natively.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="MULTI_USB_VMC_BNCM1_TC_IN",
            subsystem="HDMI_SDI_TC",
            fx6_interface="BNC TC IN / P11 0x92d2091c udate",
            fx3_target="FX3 Multi-Terminal VMC-BNCM1 LTC IN (Pin 3, 680k ID)",
            classification=BRIDGE_CLASS_SHIM_TRANSLATED,
            shim_layer="osal_uipc P11 0x92d2091c + HDMI TC Trigger",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="LTC IN supported in normal mode; must unplug during H0 uart_boot (Pins 7/8/9).",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="FX6_12G_SDI_SERIALIZER",
            subsystem="HDMI_SDI_TC",
            fx6_interface="12G-SDI Out (mew.bin FPGA / MoniFpgaSdi)",
            fx3_target="Masked Absent HW -> Non-blocking Stub + HDMI Fallback",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            shim_layer="libgrm-fbinit9.so + osal_uipc Non-Blocking Stub (rc=0)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Prevents appFw.so hanging on missing mew.bin SDI serializer.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="FX6_BNC_TC_OUT_GENLOCK",
            subsystem="HDMI_SDI_TC",
            fx6_interface="Dedicated BNC TC OUT & Genlock Ref In",
            fx3_target="Masked Absent HW -> Non-blocking Stub (rc=0)",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            shim_layer="libgrm-fbinit9.so + osal_uipc Non-Blocking Stub",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Prevents genlock wait stalls when PRM_genlock_detect_ref_* is queried.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="FX6_DARWIN_ELECTRONIC_ND",
            subsystem="HDMI_SDI_TC",
            fx6_interface="DARWIN Electronic Variable ND Filter",
            fx3_target="Masked Absent HW -> Locked Clear (0)",
            classification=BRIDGE_CLASS_MASKED_ABSENT_HW,
            shim_layer="libgrm-fbinit9.so Non-Blocking Stub",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="FX3 lacks electronic ND; Push Auto ND redirects to E-Mount Iris.",
        ),
        PeripheralTouchpointEntry(
            touchpoint_id="P12_P13_CERT_NVS_FIREWALL",
            subsystem="LENS_P18",
            fx6_interface="p12:/cert / p13 / Backup.bin NVS",
            fx3_target="Hard Write-Protected eMMC & Calibration Partitions",
            classification=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            shim_layer="Hard O_RDONLY Guard (persistent_emmc_writes_authorized=False)",
            blocking_wait_eliminated=True,
            write_protected=True,
            notes="Zero persistent writes authorized across all Stage-B peripheral bridges.",
        ),
    )

    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    sub_counts: Dict[str, int] = {}
    for e in entries:
        class_counts[e.classification] = class_counts.get(e.classification, 0) + 1
        sub_counts[e.subsystem] = sub_counts.get(e.subsystem, 0) + 1

    return PeripheralCompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        subsystem_counts=sub_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Unified Phase 146 Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_lens_ibis_audio_hdmi_peripheral_bridge(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwLensIbisAudioHdmiPeripheralBridgeReport:
    """Run all 4 Phase 146 peripheral bridge pillars in Local Donor (O_RDONLY+mmap) or Clean-Room mode."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    forced = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not forced:
        rel_map = {
            "fx3_lens_comm": FX3_LENS_COMM_P146_RELPATH,
            "fx6_lens_comm": FX6_LENS_COMM_P146_RELPATH,
            "fx3_sencore": FX3_LIBSENCORE_P146_RELPATH,
            "fx6_sencore": FX6_LIBSENCORE_P146_RELPATH,
            "fx3_appfw": FX3_APPFW_P146_RELPATH,
            "fx6_appfw": FX6_APPFW_P146_RELPATH,
            "fx3_libmpr": FX3_LIBMPR_P146_RELPATH,
            "fx6_libmpr": FX6_LIBMPR_P146_RELPATH,
            "fx6_hotshoe": FX6_HOTSHOE_P146_RELPATH,
            "fx6_avbb_audio": FX6_AVBB_AUDIO_P146_RELPATH,
            "fx3_avbbc": FX3_LIBINFRA_AVBBC_P146_RELPATH,
            "fx6_avbbc": FX6_LIBINFRA_AVBBC_P146_RELPATH,
            "fx3_cpapp": FX3_CPAPP_P146_RELPATH,
            "fx6_cpapp": FX6_CPAPP_P146_RELPATH,
            "fx3_backup": FX3_BACKUP_BIN_P146_RELPATH,
            "fx6_backup": FX6_BACKUP_BIN_P146_RELPATH,
        }
        donor_paths = {k: resolve_donor_file(v, repo_root=root) for k, v in rel_map.items()}

    use_local = (not forced) and bool(donor_paths) and all(p is not None for p in donor_paths.values())
    mode = "LOCAL_DONOR_VERIFIED" if use_local else "CLEAN_ROOM_SYNTHETIC"
    source_mode = "LOCAL_DONOR_RDONLY" if use_local else "SYNTHETIC_CLEAN_ROOM"

    fx3_appfw_tokens = tuple(
        dict.fromkeys(
            LENS_APPFW_FX3_MARKERS + IBIS_APPFW_FX3_MARKERS + AUDIO_APPFW_FX3_MARKERS + HDMI_APPFW_FX3_MARKERS
        )
    )
    fx6_appfw_tokens = tuple(
        dict.fromkeys(
            LENS_APPFW_FX6_MARKERS + IBIS_APPFW_FX6_MARKERS + AUDIO_APPFW_FX6_MARKERS + HDMI_SDI_APPFW_FX6_MARKERS
        )
    )
    cp_tokens = tuple(dict.fromkeys(IBIS_CP_SHARED_MARKERS + ("HDMI", "SDI", "Tcub")))

    donor_sizes: Dict[str, int] = {}
    if use_local:
        p = {k: v for k, v in donor_paths.items() if v is not None}
        fx3_lc_sum, fx3_lc_exp, fx3_lc_imp = _scan_elf_and_tokens_rdonly(
            p["fx3_lens_comm"], binary_name="libInfraLensCommunicator.so", body_label="FX3_7.02"
        )
        fx6_lc_sum, fx6_lc_exp, fx6_lc_imp = _scan_elf_and_tokens_rdonly(
            p["fx6_lens_comm"], binary_name="libInfraLensCommunicator.so", body_label="FX6_6.01"
        )
        fx3_sc_sum, fx3_sc_exp, fx3_sc_imp = _scan_elf_and_tokens_rdonly(
            p["fx3_sencore"],
            binary_name="libsencore.so",
            body_label="FX3_7.02",
            tokens=SENCORE_SHARED_MARKERS,
        )
        fx6_sc_sum, fx6_sc_exp, fx6_sc_imp = _scan_elf_and_tokens_rdonly(
            p["fx6_sencore"],
            binary_name="libsencore.so",
            body_label="FX6_6.01",
            tokens=SENCORE_SHARED_MARKERS,
        )
        _, fx3_app_hits = _scan_elf_ro_markers_rdonly(p["fx3_appfw"], fx3_appfw_tokens)
        _, fx6_app_hits = _scan_elf_ro_markers_rdonly(p["fx6_appfw"], fx6_appfw_tokens)
        _, fx3_mpr_hits = _scan_elf_ro_markers_rdonly(p["fx3_libmpr"], IBIS_MPR_GYRO_FX3_MARKERS)
        _, fx6_mpr_hits = _scan_elf_ro_markers_rdonly(p["fx6_libmpr"], IBIS_MPR_GYRO_FX6_MARKERS)
        fx6_hs_sum, _, _ = _scan_elf_and_tokens_rdonly(
            p["fx6_hotshoe"],
            binary_name="libInfraHotshoe.so",
            body_label="FX6_6.01",
            tokens=HOTSHOE_MARKERS,
        )
        fx6_aa_sum, _, _ = _scan_elf_and_tokens_rdonly(
            p["fx6_avbb_audio"],
            binary_name="AVBB_SCN_START_AUDIO.so",
            body_label="FX6_6.01",
            tokens=AVBB_AUDIO_MARKERS,
        )
        fx3_av_sum, _, _ = _scan_elf_and_tokens_rdonly(
            p["fx3_avbbc"],
            binary_name="libInfraAvbbc.so",
            body_label="FX3_7.02",
            tokens=AVBBC_BRIDGE_SYMBOLS,
        )
        fx6_av_sum, _, _ = _scan_elf_and_tokens_rdonly(
            p["fx6_avbbc"],
            binary_name="libInfraAvbbc.so",
            body_label="FX6_6.01",
            tokens=AVBBC_BRIDGE_SYMBOLS,
        )
        _, fx3_cp_hits = _scan_binary_tokens_rdonly(p["fx3_cpapp"], cp_tokens)
        _, fx6_cp_hits = _scan_binary_tokens_rdonly(p["fx6_cpapp"], cp_tokens)
        fx3_bk_raw = _read_bytes_rdonly(p["fx3_backup"])
        fx6_bk_raw = _read_bytes_rdonly(p["fx6_backup"])

        for k, path_obj in p.items():
            donor_sizes[k] = path_obj.stat().st_size
    else:
        fx = build_clean_room_realhw_peripheral_bridge_fixtures()
        fx3_lc_sum, fx3_lc_exp, fx3_lc_imp = _scan_elf_and_tokens_buf(
            fx["fx3_lens_comm"],
            binary_name="libInfraLensCommunicator.so",
            body_label="FX3_7.02",
            source_mode=source_mode,
        )
        fx6_lc_sum, fx6_lc_exp, fx6_lc_imp = _scan_elf_and_tokens_buf(
            fx["fx6_lens_comm"],
            binary_name="libInfraLensCommunicator.so",
            body_label="FX6_6.01",
            source_mode=source_mode,
        )
        fx3_sc_sum, fx3_sc_exp, fx3_sc_imp = _scan_elf_and_tokens_buf(
            fx["fx3_sencore"],
            binary_name="libsencore.so",
            body_label="FX3_7.02",
            source_mode=source_mode,
            tokens=SENCORE_SHARED_MARKERS,
        )
        fx6_sc_sum, fx6_sc_exp, fx6_sc_imp = _scan_elf_and_tokens_buf(
            fx["fx6_sencore"],
            binary_name="libsencore.so",
            body_label="FX6_6.01",
            source_mode=source_mode,
            tokens=SENCORE_SHARED_MARKERS,
        )
        fx3_app_hits = _count_tokens_single_pass(fx["fx3_appfw"], fx3_appfw_tokens)
        fx6_app_hits = _count_tokens_single_pass(fx["fx6_appfw"], fx6_appfw_tokens)
        fx3_mpr_hits = _count_tokens_single_pass(fx["fx3_libmpr"], IBIS_MPR_GYRO_FX3_MARKERS)
        fx6_mpr_hits = _count_tokens_single_pass(fx["fx6_libmpr"], IBIS_MPR_GYRO_FX6_MARKERS)
        fx6_hs_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_hotshoe"],
            binary_name="libInfraHotshoe.so",
            body_label="FX6_6.01",
            source_mode=source_mode,
            tokens=HOTSHOE_MARKERS,
        )
        fx6_aa_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_avbb_audio"],
            binary_name="AVBB_SCN_START_AUDIO.so",
            body_label="FX6_6.01",
            source_mode=source_mode,
            tokens=AVBB_AUDIO_MARKERS,
        )
        fx3_av_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx3_avbbc"],
            binary_name="libInfraAvbbc.so",
            body_label="FX3_7.02",
            source_mode=source_mode,
            tokens=AVBBC_BRIDGE_SYMBOLS,
        )
        fx6_av_sum, _, _ = _scan_elf_and_tokens_buf(
            fx["fx6_avbbc"],
            binary_name="libInfraAvbbc.so",
            body_label="FX6_6.01",
            source_mode=source_mode,
            tokens=AVBBC_BRIDGE_SYMBOLS,
        )
        fx3_cp_hits = _count_tokens_single_pass(fx["fx3_cpapp"], cp_tokens)
        fx6_cp_hits = _count_tokens_single_pass(fx["fx6_cpapp"], cp_tokens)
        fx3_bk_raw = fx["fx3_backup"]
        fx6_bk_raw = fx["fx6_backup"]

        for k, buf in fx.items():
            donor_sizes[k] = len(buf)

    # ---- Pillar 1: E-Mount Lens & p18:/lens Calibration ----
    p1_errors: List[str] = []
    lc_identical = (
        fx3_lc_exp == fx6_lc_exp
        and fx3_lc_imp == fx6_lc_imp
        and fx3_lc_sum.export_count == EXPECTED_LENS_COMM_EXPORTS
        and fx3_lc_sum.import_count == EXPECTED_LENS_COMM_IMPORTS
    )
    if not lc_identical:
        p1_errors.append(
            f"libInfraLensCommunicator.so ABI mismatch: fx3=({fx3_lc_sum.export_count},{fx3_lc_sum.import_count}), "
            f"fx6=({fx6_lc_sum.export_count},{fx6_lc_sum.import_count})"
        )

    sc_identical = (
        fx3_sc_exp == fx6_sc_exp
        and fx3_sc_imp == fx6_sc_imp
        and fx3_sc_sum.export_count == EXPECTED_SENCORE_EXPORTS
        and fx3_sc_sum.import_count == EXPECTED_SENCORE_IMPORTS
    )
    if not sc_identical:
        p1_errors.append(
            f"libsencore.so ABI mismatch: fx3=({fx3_sc_sum.export_count},{fx3_sc_sum.import_count}), "
            f"fx6=({fx6_sc_sum.export_count},{fx6_sc_sum.import_count})"
        )
    if not all(fx3_sc_sum.marker_hits.get(m, 0) > 0 for m in SENCORE_SHARED_MARKERS):
        p1_errors.append("FX3 libsencore.so missing expected service markers")
    if not all(fx6_sc_sum.marker_hits.get(m, 0) > 0 for m in SENCORE_SHARED_MARKERS):
        p1_errors.append("FX6 libsencore.so missing expected service markers")

    fx3_lens_hits = sum(1 for m in LENS_APPFW_FX3_MARKERS if fx3_app_hits.get(m, 0) > 0)
    fx6_lens_hits = sum(1 for m in LENS_APPFW_FX6_MARKERS if fx6_app_hits.get(m, 0) > 0)
    if fx3_lens_hits < len(LENS_APPFW_FX3_MARKERS) or fx6_lens_hits < len(LENS_APPFW_FX6_MARKERS):
        p1_errors.append(f"Incomplete appFw lens marker coverage: fx3={fx3_lens_hits}, fx6={fx6_lens_hits}")

    p1_evals = (
        evaluate_emount_lens_p18_bridge(
            lens_mounted=True,
            focal_length_mm=35.0,
            aperture_display_unit="T_STOP",
            focus_distance_unit="METER",
            breathing_comp_enabled=True,
        ),
        evaluate_emount_lens_p18_bridge(
            lens_mounted=True,
            focal_length_mm=50.0,
            aperture_display_unit="F_STOP",
            focus_distance_unit="FEET",
            breathing_comp_enabled=False,
        ),
    )
    for ev in p1_evals:
        if not ev.valid or ev.p18_lens_writes_permitted:
            p1_errors.extend(ev.errors)

    p1_report = Pillar1LensP18Report(
        passed=len(p1_errors) == 0,
        fx3_lens_comm=fx3_lc_sum,
        fx6_lens_comm=fx6_lc_sum,
        lens_comm_exports_identical=lc_identical,
        fx3_sencore=fx3_sc_sum,
        fx6_sencore=fx6_sc_sum,
        sencore_exports_identical=sc_identical,
        fx3_appfw_lens_marker_hits=fx3_lens_hits,
        fx6_appfw_lens_marker_hits=fx6_lens_hits,
        p18_fx3_lba_hex=f"0x{P18_FX3_START_LBA:08x}",
        p18_fx6_lba_hex=f"0x{P18_FX6_START_LBA:08x}",
        p18_lens_writes_permitted=False,
        sample_evals=p1_evals,
        errors=tuple(p1_errors),
    )

    # ---- Pillar 2: 5-Axis Physical IBIS vs Catalyst Gyro ----
    p2_errors: List[str] = []
    fx3_ibis_hits = sum(1 for m in IBIS_APPFW_FX3_MARKERS if fx3_app_hits.get(m, 0) > 0)
    fx6_ibis_hits = sum(1 for m in IBIS_APPFW_FX6_MARKERS if fx6_app_hits.get(m, 0) > 0)
    if fx3_ibis_hits < len(IBIS_APPFW_FX3_MARKERS) or fx6_ibis_hits < len(IBIS_APPFW_FX6_MARKERS):
        p2_errors.append(f"Incomplete appFw IBIS marker coverage: fx3={fx3_ibis_hits}, fx6={fx6_ibis_hits}")

    fx3_liro = fx3_cp_hits.get("LiroSeq", 0)
    fx6_liro = fx6_cp_hits.get("LiroSeq", 0)
    if fx3_liro == 0 or fx6_liro == 0 or fx3_liro <= fx6_liro:
        p2_errors.append(f"Unexpected cpapp LiroSeq counts (expected fx3 > fx6 > 0): fx3={fx3_liro}, fx6={fx6_liro}")
    for cm in IBIS_CP_SHARED_MARKERS:
        if fx3_cp_hits.get(cm, 0) == 0 or fx6_cp_hits.get(cm, 0) == 0:
            p2_errors.append(f"Missing shared CP IBIS/Gyro marker {cm!r}")

    fx3_mpr_gyro_hits = sum(1 for m in IBIS_MPR_GYRO_FX3_MARKERS if fx3_mpr_hits.get(m, 0) > 0)
    fx6_mpr_gyro_hits = sum(1 for m in IBIS_MPR_GYRO_FX6_MARKERS if fx6_mpr_hits.get(m, 0) > 0)
    if fx3_mpr_gyro_hits < len(IBIS_MPR_GYRO_FX3_MARKERS) or fx6_mpr_gyro_hits < len(IBIS_MPR_GYRO_FX6_MARKERS):
        p2_errors.append(
            f"Incomplete libmpr UDAM gyro coverage: fx3={fx3_mpr_gyro_hits}, fx6={fx6_mpr_gyro_hits}"
        )

    fx3_bk_sum, _, _ = parse_dual_bk4_and_descriptors(fx3_bk_raw, body="FX3_7.02")
    fx6_bk_sum, _, _ = parse_dual_bk4_and_descriptors(fx6_bk_raw, body="FX6_6.01")
    if not (fx3_bk_sum.rec0_checksum_valid and fx3_bk_sum.rec1_checksum_valid):
        p2_errors.append("FX3 Backup.bin BK4 dual checksum failed")
    if not (fx6_bk_sum.rec0_checksum_valid and fx6_bk_sum.rec1_checksum_valid):
        p2_errors.append("FX6 Backup.bin BK4 dual checksum failed")

    p2_evals = (
        evaluate_ibis_vs_catalyst_bridge(requested_mode="OFF", catalyst_gyro_metadata=True, park_coils_on_off=True),
        evaluate_ibis_vs_catalyst_bridge(requested_mode="STANDARD", catalyst_gyro_metadata=True),
        evaluate_ibis_vs_catalyst_bridge(requested_mode="ACTIVE", catalyst_gyro_metadata=True),
        evaluate_ibis_vs_catalyst_bridge(requested_mode="ACTIVE_PLUS", catalyst_gyro_metadata=True),
    )
    for ev in p2_evals:
        if not ev.valid or not ev.ibis_coil_safe_park_verified or ev.nvs_calibration_writes != 0:
            p2_errors.extend(ev.errors)

    p2_report = Pillar2IbisCatalystReport(
        passed=len(p2_errors) == 0,
        fx3_appfw_ibis_marker_hits=fx3_ibis_hits,
        fx6_appfw_ibis_marker_hits=fx6_ibis_hits,
        fx3_cp_liroseq_hits=fx3_liro,
        fx6_cp_liroseq_hits=fx6_liro,
        fx3_mpr_gyro_hits=fx3_mpr_gyro_hits,
        fx6_mpr_gyro_hits=fx6_mpr_gyro_hits,
        fx3_backup_subsystems=fx3_bk_sum.rec0_subsystems,
        fx6_backup_subsystems=fx6_bk_sum.rec0_subsystems,
        fx3_backup_checksums_valid=fx3_bk_sum.rec0_checksum_valid and fx3_bk_sum.rec1_checksum_valid,
        fx6_backup_checksums_valid=fx6_bk_sum.rec0_checksum_valid and fx6_bk_sum.rec1_checksum_valid,
        ibis_coil_safe_park_verified=all(ev.ibis_coil_safe_park_verified for ev in p2_evals),
        sample_evals=p2_evals,
        errors=tuple(p2_errors),
    )

    # ---- Pillar 3: MI-Shoe XLR-H1 4ch Audio ----
    p3_errors: List[str] = []
    fx3_aud_hits = sum(1 for m in AUDIO_APPFW_FX3_MARKERS if fx3_app_hits.get(m, 0) > 0)
    fx6_aud_hits = sum(1 for m in AUDIO_APPFW_FX6_MARKERS if fx6_app_hits.get(m, 0) > 0)
    if fx3_aud_hits < len(AUDIO_APPFW_FX3_MARKERS) or fx6_aud_hits < len(AUDIO_APPFW_FX6_MARKERS):
        p3_errors.append(f"Incomplete appFw audio marker coverage: fx3={fx3_aud_hits}, fx6={fx6_aud_hits}")
    if not all(fx6_hs_sum.marker_hits.get(m, 0) > 0 for m in HOTSHOE_MARKERS):
        p3_errors.append("FX6 libInfraHotshoe.so missing expected UIPC/shoe markers")
    if not all(fx6_aa_sum.marker_hits.get(m, 0) > 0 for m in AVBB_AUDIO_MARKERS):
        p3_errors.append("FX6 AVBB_SCN_START_AUDIO.so missing expected audio scenario markers")

    p3_evals = (
        evaluate_mishoe_xlrh1_audio_bridge(handle_state="XLR_H1_ATTACHED"),
        evaluate_mishoe_xlrh1_audio_bridge(handle_state="XLR_H1_DETACHED", enable_nonblock_hot_detach=True),
        evaluate_mishoe_xlrh1_audio_bridge(handle_state="TRS_JACK_ONLY", enable_nonblock_hot_detach=True),
    )
    for ev in p3_evals:
        if not ev.valid or not ev.phantom_device_timeout_eliminated:
            p3_errors.extend(ev.errors)

    p3_report = Pillar3AudioXlrh1Report(
        passed=len(p3_errors) == 0,
        fx3_appfw_audio_marker_hits=fx3_aud_hits,
        fx6_appfw_audio_marker_hits=fx6_aud_hits,
        fx6_hotshoe=fx6_hs_sum,
        fx6_avbb_audio=fx6_aa_sum,
        lpcm_4ch_bitrate_bps=AUDIO_LPCM_4CH_BPS,
        p11_nonblock_safe_rc_hex=f"0x{HOTSHOE_NONBLOCK_SAFE_RC:04x}",
        phantom_device_timeout_eliminated=all(ev.phantom_device_timeout_eliminated for ev in p3_evals),
        sample_evals=p3_evals,
        errors=tuple(p3_errors),
    )

    # ---- Pillar 4: HDMI Type-A + Multi-USB TC-IN vs 12G-SDI & BNC ----
    p4_errors: List[str] = []
    fx3_hdmi_hits = sum(1 for m in HDMI_APPFW_FX3_MARKERS if fx3_app_hits.get(m, 0) > 0)
    fx6_sdi_hdmi_hits = sum(1 for m in HDMI_SDI_APPFW_FX6_MARKERS if fx6_app_hits.get(m, 0) > 0)
    if fx3_hdmi_hits < len(HDMI_APPFW_FX3_MARKERS) or fx6_sdi_hdmi_hits < len(HDMI_SDI_APPFW_FX6_MARKERS):
        p4_errors.append(
            f"Incomplete appFw HDMI/SDI marker coverage: fx3={fx3_hdmi_hits}, fx6={fx6_sdi_hdmi_hits}"
        )
    if not all(fx3_av_sum.marker_hits.get(m, 0) > 0 for m in AVBBC_BRIDGE_SYMBOLS):
        p4_errors.append("FX3 libInfraAvbbc.so missing ObjAvbbcCmn SDI/HDMI/TCUB bridge symbols")
    if not all(fx6_av_sum.marker_hits.get(m, 0) > 0 for m in AVBBC_BRIDGE_SYMBOLS):
        p4_errors.append("FX6 libInfraAvbbc.so missing ObjAvbbcCmn SDI/HDMI/TCUB bridge symbols")

    fx3_cp_hdmi = fx3_cp_hits.get("HDMI", 0)
    fx3_cp_sdi = fx3_cp_hits.get("SDI", 0)
    fx6_cp_hdmi = fx6_cp_hits.get("HDMI", 0)
    fx6_cp_sdi = fx6_cp_hits.get("SDI", 0)
    if fx3_cp_hdmi == 0 or fx6_cp_hdmi == 0 or fx6_cp_sdi <= fx3_cp_sdi:
        p4_errors.append(
            f"Unexpected cpapp HDMI/SDI density: fx3=({fx3_cp_hdmi},{fx3_cp_sdi}), fx6=({fx6_cp_hdmi},{fx6_cp_sdi})"
        )

    p4_evals = (
        evaluate_hdmi_sdi_tc_bridge(requested_interface="HDMI_4K60"),
        evaluate_hdmi_sdi_tc_bridge(requested_interface="HDMI_RAW_16BIT_4264X2408"),
        evaluate_hdmi_sdi_tc_bridge(requested_interface="MULTI_USB_TC_IN", in_uart_boot=False),
        evaluate_hdmi_sdi_tc_bridge(requested_interface="12G_SDI_OUT", mask_absent_hw=True, stub_blocking_wait_ms=0),
        evaluate_hdmi_sdi_tc_bridge(requested_interface="BNC_TC_OUT", mask_absent_hw=True, stub_blocking_wait_ms=0),
        evaluate_hdmi_sdi_tc_bridge(requested_interface="BNC_GENLOCK_IN", mask_absent_hw=True, stub_blocking_wait_ms=0),
        evaluate_hdmi_sdi_tc_bridge(requested_interface="DARWIN_ND", mask_absent_hw=True, stub_blocking_wait_ms=0),
    )
    for ev in p4_evals:
        if not ev.valid or not ev.sdi_blocking_wait_eliminated:
            p4_errors.extend(ev.errors)

    p4_report = Pillar4HdmiSdiTcReport(
        passed=len(p4_errors) == 0,
        fx3_appfw_hdmi_marker_hits=fx3_hdmi_hits,
        fx6_appfw_sdi_hdmi_marker_hits=fx6_sdi_hdmi_hits,
        fx3_avbbc=fx3_av_sum,
        fx6_avbbc=fx6_av_sum,
        fx3_cp_hdmi_hits=fx3_cp_hdmi,
        fx3_cp_sdi_hits=fx3_cp_sdi,
        fx6_cp_hdmi_hits=fx6_cp_hdmi,
        fx6_cp_sdi_hits=fx6_cp_sdi,
        sdi_blocking_wait_eliminated=all(ev.sdi_blocking_wait_eliminated for ev in p4_evals),
        sample_evals=p4_evals,
        errors=tuple(p4_errors),
    )

    compat_matrix = build_phase146_compatibility_matrix()

    vol_guard = evaluate_phase146_write_guard("/tmp/stage_b/peripheral_bridge_shadow.json")
    p18_guard = evaluate_phase146_write_guard("/dev/nflasha18/lensfile.bin")
    p12_guard = evaluate_phase146_write_guard("p12:/cert/device_key.bin")
    bk_guard = evaluate_phase146_write_guard("p2:/setting/Backup.bin")

    guard_errors: List[str] = []
    if not vol_guard.valid:
        guard_errors.append("Volatile RAM staging guard unexpectedly rejected /tmp path")
    if not p18_guard.persistent_write_blocked or p18_guard.p18_lens_writes_permitted:
        guard_errors.append("p18:/lens write guard failed to block persistent write")
    if not p12_guard.persistent_write_blocked or not bk_guard.persistent_write_blocked:
        guard_errors.append("p12:/cert or Backup.bin write guard failed to block persistent write")

    all_errors = tuple(p1_errors + p2_errors + p3_errors + p4_errors + guard_errors)
    all_passed = (
        p1_report.passed
        and p2_report.passed
        and p3_report.passed
        and p4_report.passed
        and len(all_errors) == 0
    )

    draft_dict = {
        "schema_version": PHASE_146_SCHEMA,
        "phase_version": PHASE_146_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "p18_lens_writes_permitted": False,
        "ibis_coil_safe_park_verified": p2_report.ibis_coil_safe_park_verified,
        "sdi_blocking_wait_eliminated": p4_report.sdi_blocking_wait_eliminated,
        "persistent_emmc_writes_authorized": False,
        "emmc_mutation_bytes": 0,
        "calibration_mutation_bytes": 0,
        "donor_file_sizes": donor_sizes,
        "pillar1_lens_p18": asdict(p1_report),
        "pillar2_ibis_catalyst": asdict(p2_report),
        "pillar3_audio_xlrh1": asdict(p3_report),
        "pillar4_hdmi_sdi_tc": asdict(p4_report),
        "compatibility_matrix": asdict(compat_matrix),
        "volatile_guard_ok": asdict(vol_guard),
        "forbidden_p18_guard_blocked": asdict(p18_guard),
        "forbidden_p12_guard_blocked": asdict(p12_guard),
        "forbidden_backup_guard_blocked": asdict(bk_guard),
        "errors": list(all_errors),
    }
    digest = hashlib.sha256(
        json.dumps(draft_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return RealhwLensIbisAudioHdmiPeripheralBridgeReport(
        schema_version=PHASE_146_SCHEMA,
        phase_version=PHASE_146_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        p18_lens_writes_permitted=False,
        ibis_coil_safe_park_verified=p2_report.ibis_coil_safe_park_verified,
        sdi_blocking_wait_eliminated=p4_report.sdi_blocking_wait_eliminated,
        persistent_emmc_writes_authorized=False,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        donor_file_sizes=donor_sizes,
        pillar1_lens_p18=p1_report,
        pillar2_ibis_catalyst=p2_report,
        pillar3_audio_xlrh1=p3_report,
        pillar4_hdmi_sdi_tc=p4_report,
        compatibility_matrix=compat_matrix,
        volatile_guard_ok=vol_guard,
        forbidden_p18_guard_blocked=p18_guard,
        forbidden_p12_guard_blocked=p12_guard,
        forbidden_backup_guard_blocked=bk_guard,
        report_sha256=digest,
        errors=all_errors,
    )


def realhw_lens_ibis_audio_hdmi_peripheral_bridge_report_to_dict(
    report: RealhwLensIbisAudioHdmiPeripheralBridgeReport,
) -> Dict[str, object]:
    """Convert `RealhwLensIbisAudioHdmiPeripheralBridgeReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
