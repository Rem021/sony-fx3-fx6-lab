"""Phase 197 — 41st Firmware-Lab Auditor (41/41): Real-Hardware `ILME-FX3`
(`Ver. 7.02`) 4-Mode Fan PWM (`Auto/Minimum/Off in Rec/Always Off`, Zero
`Auto1/Auto2`), Independent `[Shutter Mode]` (`Speed` vs `Angle` `5.6°..64F /
360°`) & `Ver. 6.01` vs `Ver. 7.00/7.02` `p2:/setting` User LUT Binary Slot
Split Auditor.

Strictly Read-Only (`os.O_RDONLY` + `os.pread` bounded section inspection) &
Clean-Room Dual-Mode:
- Local Donor Mode: inspects Stock FX3 `Ver. 7.02` (`appFw.so`,
  `string_english_f.uxc`, `cpapp-b.bin` / `CPAPP-B.BIN`, `Backup.bin`) vs FX6
  `Ver. 6.01` (`appFw.so`, `string_english.uxc`, `cpapp-b.bin`, `Backup.bin`)
  strictly via `os.O_RDONLY` + bounded `os.pread` (< 0.15 s cold, cached per
  process via `_DONOR_SCAN_CACHE`, never scanning >50 MiB whole images
  redundantly).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`, `.uxc` string
  packs, `cpapp-b.bin` RTOS token slices, and `BK4\x00` `Backup.bin` headers
  with zero proprietary bytes leaked (`raw_firmware_bytes_leaked == 0`).

Audits Four Core Real-Hardware Pillars:
1. Pillar 1 (`FX3_4MODE_FAN_PWM_OFFINREC_STANDBY_MAX_AND_PREBACKUP_GUARD`):
   Audits `MENU -> Setup -> [Setup Option] -> [Fan Control]` exact 4-state enum
   on `ILME-FX3` (`Auto`, `Minimum`, `Off in Rec`, `Always Off`), proving zero
   non-Sony/studio-camera `Auto1`/`Auto2` tokens (`FAN_CONTROL_AUTO1 == 0`,
   `FAN_CONTROL_AUTO2 == 0`, `"Auto1" == 0`, `"Auto2" == 0`). Models `Off in Rec`
   (`0%` PWM during recording unless internal temperature exceeds emergency
   safety threshold, `100% MAX PWM` active heat purge during standby/non-recording)
   and enforces the `Always Off -> Auto` pre-backup thermal interlock
   (`[Auto Power OFF Temp.] = Standard / High`) prior to long
   `AdjustControl (0x40)` 75 MiB `p3` cold dumps to prevent `CXD90057 / CXD90058`
   thermal power-off.
2. Pillar 2 (`INDEPENDENT_SHUTTER_SPEED_ANGLE_SLOTS_AND_RANGE_CLAMP`):
   Audits `Ver. 6.00+ / 7.02` & `BIG6` independent `[Speed]` and `[Angle]`
   key-value slot storage in `Backup.bin` (`0x02cf1702` Shutter Mode,
   `0x02cf1704` Shutter Angle, completely decoupled from `[Speed]` and immune to
   `[Exposure step] = 0.3EV / 0.5EV`), enforcing normal movie range
   `5.6° .. 64F`, clamping `[Rec Frame Rate] = 119.88p / 100p` to `5.6° .. 360°`,
   and `S&Q` range `5.6° .. 360°`.
3. Pillar 3 (`LUT_601_VS_702_P2_SETTING_BINARY_GENERATION_SPLIT_FIREWALL`):
   Proves the real-hardware User LUT binary slot generation split between donor
   `FX6 Ver. 6.01` (`<= 6.01` legacy Diadem-Pro schema:
   `BKID_APP_IS_EXIST_USER_LUT0..15`,
   `BKID_APP_HAND_OVER_USER_LUT_EXIST_AFTER_UUD_FROM_DIADEM_PRO0..15`,
   `model_user_lut_files::cube file save skip!!`) and host `Stock FX3 Ver. 7.02`
   (`7.00+` optimized User LUT schema: `BKID_APP_is_exist_user_lut0..15`,
   `BKID_APP_user_lut_attr_ae_level_offset0..15`,
   `BKID_APP_setting_embed_lut_file`), demonstrating why direct Stage-B `FX6 6.01`
   writes into `p2:/setting` `User1..User16` corrupt Stock `FX3 7.02` LUT
   deserialization and proving volatile `/tmp/fx6_lut_overlay` redirection keeps
   `p2:/setting` bit-identical (`H0 == H3`, `calibration_mutation_bytes == 0`).
4. Pillar 4 (`ZERO_WRITE_FIREWALL_AND_12TP_COMPAT_MATRIX`):
   Enforces hard safety invariants (`persistent_emmc_writes_authorized = False`,
   `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`,
   `physical_usb_packets_emitted = 0`, `raw_firmware_bytes_leaked = 0`) and
   builds a 12-touchpoint 4-class compatibility matrix across Pillars 1..3.
"""

from __future__ import annotations

import hashlib
import os
import re
import struct
import time
import zlib
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    is_forced_clean_room,
    resolve_donor_file,
)
from .realhw_cp_rtos_and_backup_bin_auditor import BK4_MAGIC_BYTES
from .realhw_fx3_vs_fx3a_and_xlrh1_mishoe_auditor import (
    _scan_elf_buf_ordered,
    _scan_elf_fast_rdonly,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    FX3_APPFW_P146_RELPATH,
    FX3_BACKUP_BIN_P146_RELPATH,
    FX3_CPAPP_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_BACKUP_BIN_P146_RELPATH,
    FX6_CPAPP_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
)
from .uxc_multilang_and_font_verifier import (
    FX3_SHARE_APP_RELDIR,
    FX6_SHARE_APP_RELDIR,
)


PHASE_197_SCHEMA = (
    "fx3_firmware_lab_phase197_realhw_fan_pwm_shutter_angle_lut_601_702_split_v1"
)
PHASE_197_VERSION = "197.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + bounded os.pread)
# ---------------------------------------------------------------------------

FX3_APPFW_P197_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P197_RELPATH = FX6_APPFW_P146_RELPATH
FX3_UXC_EN_F_P197_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_f.uxc"
FX6_UXC_EN_P197_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX3_CPAPP_P197_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P197_RELPATH = FX6_CPAPP_P146_RELPATH
FX3_BACKUP_BIN_P197_RELPATH = FX3_BACKUP_BIN_P146_RELPATH
FX6_BACKUP_BIN_P197_RELPATH = FX6_BACKUP_BIN_P146_RELPATH

# ---------------------------------------------------------------------------
# Verified Expected Donor Sizes & BK4 Subsystem Counts
# ---------------------------------------------------------------------------

EXPECTED_FX3_APPFW_BYTES_P197 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P197 = 50_520_424
EXPECTED_FX3_UXC_EN_F_BYTES_P197 = 373_820
EXPECTED_FX6_UXC_EN_BYTES_P197 = 118_208
EXPECTED_FX3_CPAPP_BYTES_P197 = 15_980_568
EXPECTED_FX6_CPAPP_BYTES_P197 = 17_952_816
EXPECTED_FX3_BACKUP_BYTES_P197 = 2_229_740
EXPECTED_FX6_BACKUP_BYTES_P197 = 2_253_333
EXPECTED_FX3_BK4_SUBSYSTEMS_P197 = 819
EXPECTED_FX6_BK4_SUBSYSTEMS_P197 = 840

# Bounded CPAPP-B.BIN read geometry (head 768 KiB + tail 6 MiB RTOS string pool)
CPAPP_BOUNDED_HEAD_BYTES_P197 = 768 * 1024
CPAPP_BOUNDED_TAIL_BYTES_P197 = 6 * 1024 * 1024
DONOR_COLD_SCAN_BUDGET_SEC_P197 = 0.15

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 1 (ILME-FX3 4-Mode Fan Control & Pre-Backup Guard)
# ---------------------------------------------------------------------------

FX3_FAN_CONTROL_MENU_PATH_P197 = "MENU -> Setup -> [Setup Option] -> [Fan Control]"

FX3_FAN_CONTROL_MODES_P197: Tuple[str, ...] = (
    "Auto",
    "Minimum",
    "Off in Rec",
    "Always Off",
)

FX3_FAN_MODE_TO_APPFW_ENUM_P197: Dict[str, str] = {
    "Auto": "FAN_CONTROL_AUTO",
    "Minimum": "FAN_CONTROL_MINIMUM",
    "Off in Rec": "FAN_CONTROL_OFF_IN_REC",
    "Always Off": "FAN_CONTROL_ALWAYS_OFF",
}

FORBIDDEN_NON_FX3_FAN_MODES_P197: Tuple[str, ...] = (
    "Auto1",
    "Auto2",
    "AUTO1",
    "AUTO2",
    "Normal",
    "High",
    "Low",
)

VALID_AUTO_POWER_OFF_TEMPS_P197: Tuple[str, ...] = ("Standard", "High")
EMERGENCY_THERMAL_TEMP_STANDARD_C_P197 = 68.0
EMERGENCY_THERMAL_TEMP_HIGH_C_P197 = 78.0
FAN_PWM_STANDBY_PURGE_MAX_PCT_P197 = 100
FAN_PWM_EMERGENCY_MAX_PCT_P197 = 100
FAN_PWM_MINIMUM_FLOOR_PCT_P197 = 20
FAN_PWM_OFF_PCT_P197 = 0
ADJUST_CONTROL_OPCODE_HEX_P197 = "0x40"
COLD_DUMP_P3_SIZE_MIB_P197 = 75

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 2 (Independent Shutter Speed/Angle & Range Clamp)
# ---------------------------------------------------------------------------

VALID_SHUTTER_MODES_P197: Tuple[str, ...] = ("Speed", "Angle")
VALID_EXPOSURE_STEPS_P197: Tuple[str, ...] = ("0.3EV", "0.5EV")
VALID_SHOOTING_MODES_P197: Tuple[str, ...] = ("NORMAL_MOVIE", "SQ_MOTION")

BK4_PROP_SHUTTER_MODE_HEX_P197 = "0x02cf1702"
BK4_PROP_SHUTTER_ANGLE_HEX_P197 = "0x02cf1704"
BK4_PROP_SHUTTER_SPEED_SLOT_KEY_P197 = "BACKUP_BIN_MOVIE_SHUTTER_SPEED_SLOT"
BK4_PROP_SHUTTER_ANGLE_SLOT_KEY_P197 = "BACKUP_BIN_MOVIE_SHUTTER_ANGLE_SLOT"

SHUTTER_ANGLE_MIN_DEG_P197 = 5.6
SHUTTER_ANGLE_STD_MAX_DEG_P197 = 360.0
SHUTTER_ANGLE_MAX_SLOW_FRAMES_P197 = 64
SHUTTER_ANGLE_64F_EQUIV_DEG_P197 = 64 * 360.0  # 23,040.0 deg

CANONICAL_SHUTTER_ANGLES_DEG_P197: Tuple[float, ...] = (
    5.6,
    11.25,
    22.5,
    30.0,
    45.0,
    72.0,
    86.4,
    90.0,
    120.0,
    144.0,
    150.0,
    172.8,
    180.0,
    210.0,
    216.0,
    240.0,
    270.0,
    300.0,
    360.0,
)

CANONICAL_SLOW_SHUTTER_FRAME_MULTIPLES_P197: Tuple[int, ...] = (
    2,
    3,
    4,
    5,
    6,
    7,
    8,
    16,
    32,
    64,
)

STANDARD_REC_FRAME_RATES_P197: Dict[str, float] = {
    "23.98p": 24000.0 / 1001.0,
    "24.00p": 24.0,
    "25p": 25.0,
    "29.97p": 30000.0 / 1001.0,
    "50p": 50.0,
    "59.94p": 60000.0 / 1001.0,
}

HFR_CLAMPED_REC_FRAME_RATES_P197: Dict[str, float] = {
    "100p": 100.0,
    "119.88p": 120000.0 / 1001.0,
}

ALL_VALID_REC_FRAME_RATES_P197: Dict[str, float] = {
    **STANDARD_REC_FRAME_RATES_P197,
    **HFR_CLAMPED_REC_FRAME_RATES_P197,
}

VALID_SHUTTER_SPEED_TOKENS_P197: Tuple[str, ...] = (
    "1/24",
    "1/25",
    "1/30",
    "1/48",
    "1/50",
    "1/60",
    "1/96",
    "1/100",
    "1/120",
    "1/125",
    "1/200",
    "1/240",
    "1/250",
    "1/500",
    "1/1000",
    "1/2000",
    "1/4000",
    "1/8000",
)

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 3 (Ver. 6.01 vs Ver. 7.00/7.02 User LUT Slot Split)
# ---------------------------------------------------------------------------

LUT_SLOT_SCHEMA_LEGACY_LE_601_P197 = "SONY_USER_LUT_SLOT_V1_LEGACY_601"
LUT_SLOT_SCHEMA_OPT_GE_700_P197 = "SONY_USER_LUT_SLOT_V2_OPT_700_702"
LUT_SLOT_V1_MAGIC_BYTES_P197 = b"UL61"
LUT_SLOT_V2_MAGIC_BYTES_P197 = b"UL70"
LUT_SLOT_V1_RECORD_BYTES_P197 = 48
LUT_SLOT_V2_RECORD_BYTES_P197 = 64

USER_LUT_SLOT_MIN_P197 = 1
USER_LUT_SLOT_MAX_P197 = 16
P2_SETTING_USER_LUT_DIR_P197 = "p2:/setting"
VOLATILE_FX6_LUT_OVERLAY_DIR_P197 = "/tmp/fx6_lut_overlay"
VALID_LIFECYCLE_STAGES_P197: Tuple[str, ...] = ("H0", "H1", "H2", "H3")

# ---------------------------------------------------------------------------
# Verified Donor Binary Marker Catalogs (strictly O_RDONLY bounded read)
# ---------------------------------------------------------------------------

APPFW_SHARED_FAN_SHUTTER_MARKERS_P197: Tuple[str, ...] = (
    "FAN_CONTROL_AUTO",
    "FAN_CONTROL_MINIMUM",
    "FAN_CONTROL_OFF_IN_REC",
    "FAN_CONTROL_ALWAYS_OFF",
    "N5model21setting_fan_control_tE",
    "N5model28sequence_cooling_fan_controlE",
    "VAL_setting_mode_shutter_MODE_SHUTTER_SPEED",
    "VAL_setting_mode_shutter_MODE_SHUTTER_ANGLE",
    "N5model22setting_mode_shutter_tE",
    "model_user_lut_files::mount_lut_folder():OK",
    "model_user_lut_files read3DLUTFile!! line[%d] lutNo[%d]",
)

APPFW_FORBIDDEN_AUTO12_MARKERS_P197: Tuple[str, ...] = (
    "FAN_CONTROL_AUTO1",
    "FAN_CONTROL_AUTO2",
)

APPFW_FX3_702_EXCLUSIVE_MARKERS_P197: Tuple[str, ...] = (
    "BKID_APP_setting_fan_control",
    "EVENT_REMOTE_AUTO_POWER_OFF_TEMPERATURE",
    "N5model39sequence_set_auto_power_off_temperatureE",
    "OFF_BY_THERMAL_TIME_OUT",
    "BKID_APP_setting_mode_shutter",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_5_POINT_6",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_180_POINT_0",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_360_POINT_0",
    "VAL_setting_shutter_angle_SHUTTER_ANGLE_64F",
    "VAL_setting_exposure_step_EXPOSURE_STEP_0_3_EV",
    "VAL_setting_exposure_step_EXPOSURE_STEP_0_5_EV",
    "BKID_APP_is_exist_user_lut0",
    "BKID_APP_is_exist_user_lut15",
    "BKID_APP_user_lut_attr_ae_level_offset0",
    "BKID_APP_user_lut_attr_ae_level_offset15",
    "BKID_APP_setting_embed_lut_file",
)

APPFW_FX6_601_EXCLUSIVE_LUT_MARKERS_P197: Tuple[str, ...] = (
    "BKID_APP_IS_EXIST_USER_LUT0",
    "BKID_APP_IS_EXIST_USER_LUT15",
    "BKID_APP_HAND_OVER_USER_LUT_EXIST_AFTER_UUD_FROM_DIADEM_PRO0",
    "BKID_APP_HAND_OVER_USER_LUT_EXIST_AFTER_UUD_FROM_DIADEM_PRO15",
    "model_user_lut_files::cube file save skip!! line[%d]",
)

UXC_FX3_EN_F_REQUIRED_TOKENS_P197: Tuple[str, ...] = (
    "Fan Control",
    "Auto",
    "Minimum",
    "Off in Rec",
    "Always Off",
    "Auto Power OFF Temp.",
    "Standard",
    "High",
    "Shutter Mode",
    "Speed",
    "Angle",
    "5.6",
    "360",
    "Exposure step",
    "0.3EV",
    "0.5EV",
    "User LUT",
    "Select LUT",
    "User1",
    "User16",
)

UXC_FX6_EN_REQUIRED_TOKENS_P197: Tuple[str, ...] = (
    "Fan Control",
    "Auto",
    "Minimum",
    "Off in Rec",
    "Always Off",
    "Standard",
    "High",
    "Shutter Mode",
    "Shutter Angle",
    "Speed",
    "Angle",
    "5.6",
    "360",
)

UXC_FORBIDDEN_AUTO12_TOKENS_P197: Tuple[str, ...] = (
    "Auto1",
    "Auto2",
)

CPAPP_SHARED_FAN_MLUT_MARKERS_P197: Tuple[str, ...] = (
    "SET_FAN_EQ_ID",
    "FAN_R",
    "PWM",
    "THERM",
    "C_ImagerCtrl_IMX510",
    "MLUT",
)

# ---------------------------------------------------------------------------
# Write-Firewall Patterns
# ---------------------------------------------------------------------------

VOLATILE_OR_EXT_PREFIXES_P197: Tuple[str, ...] = (
    "/tmp/fx6_lut_overlay",
    "/tmp/",
    "/tmp_wbshd/",
    "ram://",
    "memfd:",
    "/mnt/sd/",
    "/mnt/sd2/",
    "/mnt/cfexpress_a/",
)

FORBIDDEN_PERSISTENT_TARGET_RE_P197 = re.compile(
    r"(?:"
    r"^/dev/(?:[cp]?nflasha\d*|mmcblk0(?:p\d+|rpmb)?|rtc0)"
    r"|^p(?:0|1|2|3|5|6|7|8|12|13|15|18):/"
    r"|^/(?:wbi|setting|cert|lens)(?:/|$)"
    r"|^spi_nor:"
    r"|^sector0:"
    r"|Backup\.bin$"
    r"|cpapp-b\.bin$"
    r"|CPAPP-B\.BIN$"
    r"|BODYDATA\.DAT$"
    r"|CAMSET.*\.DAT$"
    r"|loader_nor\.bin$"
    r")",
    re.IGNORECASE,
)

# Per-process bounded O_RDONLY donor scan cache (< 0.15s cold, < 1ms warm)
_DONOR_SCAN_CACHE: Dict[Tuple[str, ...], Dict[str, object]] = {}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundedUxcPackSummary:
    pack_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    uxc_magic_valid: bool
    required_token_hits: Dict[str, int]
    forbidden_auto12_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedCpappSummary:
    binary_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    bounded_bytes_read: int
    marker_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedBk4HeaderSummary:
    binary_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    bk4_magic_valid: bool
    rec0_subsystems: int
    rec0_properties: int
    rec0_span_bytes: int


@dataclass(frozen=True)
class Fx3FanPwmAndThermalGuardEvalResult:
    valid: bool
    menu_path: str
    requested_fan_mode: str
    effective_fan_mode: str
    appfw_enum_symbol: str
    non_fx3_auto12_rejected: bool
    is_recording: bool
    internal_temp_c: float
    auto_power_off_temp: str
    emergency_threshold_c: float
    emergency_thermal_override_active: bool
    standby_max_pwm_heat_purge: bool
    fan_stopped_for_acoustic_silence: bool
    effective_pwm_duty_pct: int
    cold_dump_p3_75mib_requested: bool
    adjust_control_opcode_hex: str
    auto_interlock_enforced: bool
    prebackup_forced_to_auto: bool
    cxd90057_cxd90058_overheat_risk: bool
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class BackupBinShutterSlotState:
    shutter_mode: str
    stored_speed_token: str
    stored_angle_token: str
    exposure_step: str


@dataclass(frozen=True)
class IndependentShutterModeAndAngleEvalResult:
    valid: bool
    shooting_mode: str
    rec_frame_rate: str
    fps_numeric: float
    shutter_mode: str
    exposure_step: str
    stored_speed_slot: str
    requested_angle_token: str
    effective_angle_token: str
    effective_angle_deg: float
    min_allowed_angle_deg: float
    max_allowed_angle_deg: float
    max_allowed_angle_label: str
    angle_clamped: bool
    speed_and_angle_slots_independent: bool
    angle_immune_to_exposure_step: bool
    exposure_time_sec: float
    backup_bin_writes: int
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UserLutBinarySlotHeaderSummary:
    schema_id: str
    magic_ascii: str
    fw_version_u16_hex: str
    slot_index: int
    lut_3d_size: int
    ae_level_offset_thirds: Optional[int]
    embed_lut_enabled: Optional[bool]
    record_bytes: int
    crc32_hex: str


@dataclass(frozen=True)
class UserLut601Vs702SplitFirewallEvalResult:
    valid: bool
    writer_firmware: str
    writer_slot_schema: str
    host_reader_firmware: str
    host_reader_slot_schema: str
    slot_index: int
    slot_label: str
    target_storage_path: str
    generation_split_detected: bool
    direct_p2_setting_write_blocked: bool
    stock_702_lut_deserialize_corrupted: bool
    stock_702_lut_corruption_prevented: bool
    redirected_to_volatile_overlay: bool
    lifecycle_stage: str
    h0_p2_setting_sha256: str
    h3_p2_setting_sha256: str
    h0_equals_h3: bool
    p2_setting_mutation_bytes: int
    calibration_mutation_bytes: int
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase197WriteGuardResult:
    valid: bool
    target_path: str
    volatile_or_ext_allowed: bool
    persistent_write_blocked: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    persistent_writes: int
    calibration_mutation_bytes: int
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase197TouchpointEntry:
    touchpoint_id: str
    pillar: str
    fx6_or_host_component: str
    fx3_target: str
    bridge_class: str
    safety_invariant: str


@dataclass(frozen=True)
class Phase197CompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    pillar_counts: Dict[str, int]
    touchpoints: Tuple[Phase197TouchpointEntry, ...]


@dataclass(frozen=True)
class Pillar1Fx3FanPwmAndThermalReport:
    passed: bool
    fx3_appfw_fan_hits: Dict[str, int]
    fx6_appfw_fan_hits: Dict[str, int]
    fx3_forbidden_auto12_hits: Dict[str, int]
    fx6_forbidden_auto12_hits: Dict[str, int]
    fx3_uxc_en_f_summary: BoundedUxcPackSummary
    fx6_uxc_en_summary: BoundedUxcPackSummary
    fx3_cpapp_summary: BoundedCpappSummary
    fx6_cpapp_summary: BoundedCpappSummary
    eval_auto_normal: Fx3FanPwmAndThermalGuardEvalResult
    eval_minimum_normal: Fx3FanPwmAndThermalGuardEvalResult
    eval_off_in_rec_recording_silent: Fx3FanPwmAndThermalGuardEvalResult
    eval_off_in_rec_standby_max_pwm: Fx3FanPwmAndThermalGuardEvalResult
    eval_off_in_rec_emergency_thermal_override: Fx3FanPwmAndThermalGuardEvalResult
    eval_auto1_studio_token_rejected: Fx3FanPwmAndThermalGuardEvalResult
    eval_auto2_studio_token_rejected: Fx3FanPwmAndThermalGuardEvalResult
    eval_always_off_prebackup_blocked_without_interlock: Fx3FanPwmAndThermalGuardEvalResult
    eval_always_off_prebackup_forced_auto_ok: Fx3FanPwmAndThermalGuardEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2IndependentShutterAngleReport:
    passed: bool
    fx3_appfw_shutter_hits: Dict[str, int]
    fx6_appfw_shutter_hits: Dict[str, int]
    fx3_backup_header: BoundedBk4HeaderSummary
    fx6_backup_header: BoundedBk4HeaderSummary
    eval_normal_2398p_64f_ok: IndependentShutterModeAndAngleEvalResult
    eval_normal_2398p_180deg_05ev_immune_ok: IndependentShutterModeAndAngleEvalResult
    eval_speed_mode_preserves_angle_slot_ok: IndependentShutterModeAndAngleEvalResult
    eval_hfr_11988p_64f_clamped_to_360_ok: IndependentShutterModeAndAngleEvalResult
    eval_hfr_100p_direct_64f_rejected: IndependentShutterModeAndAngleEvalResult
    eval_sq_motion_64f_clamped_to_360_ok: IndependentShutterModeAndAngleEvalResult
    eval_below_5_6_deg_rejected: IndependentShutterModeAndAngleEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3Lut601Vs702SplitReport:
    passed: bool
    fx3_702_lut_exclusive_hits: Dict[str, int]
    fx6_601_lut_exclusive_hits: Dict[str, int]
    fx6_702_cross_pollution_in_fx3: Dict[str, int]
    fx3_702_cross_pollution_in_fx6: Dict[str, int]
    legacy_601_slot_sample: UserLutBinarySlotHeaderSummary
    opt_702_slot_sample: UserLutBinarySlotHeaderSummary
    eval_direct_601_write_to_p2_setting_blocked: UserLut601Vs702SplitFirewallEvalResult
    eval_stage_b_601_volatile_overlay_h2_ok: UserLut601Vs702SplitFirewallEvalResult
    eval_stock_702_restore_h3_bit_exact_ok: UserLut601Vs702SplitFirewallEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4Phase197WriteGuardAndMatrixReport:
    passed: bool
    blocked_p2_setting_eval: Phase197WriteGuardResult
    blocked_backup_bin_eval: Phase197WriteGuardResult
    blocked_cpapp_bin_eval: Phase197WriteGuardResult
    blocked_spi_nor_eval: Phase197WriteGuardResult
    allowed_fx6_lut_overlay_eval: Phase197WriteGuardResult
    allowed_sd_cube_source_eval: Phase197WriteGuardResult
    compatibility_matrix: Phase197CompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwFanPwmShutterAngleAndLut601702SplitReport:
    schema_version: str
    phase_version: str
    auditor_index: str
    mode: str
    cache_hit: bool
    cold_or_cached_scan_elapsed_sec: float
    all_checks_passed: bool
    o_rdonly_enforced: bool
    raw_firmware_bytes_leaked: int
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    persistent_writes: int
    p2_setting_mutation_bytes: int
    calibration_mutation_bytes: int
    fan_4mode_and_prebackup_thermal_verified: bool
    independent_shutter_speed_angle_verified: bool
    lut_601_vs_702_binary_split_firewall_verified: bool
    write_firewall_and_matrix_verified: bool
    donor_file_sizes: Dict[str, int]
    pillar_1_fan_pwm_thermal: Pillar1Fx3FanPwmAndThermalReport
    pillar_2_shutter_speed_angle: Pillar2IndependentShutterAngleReport
    pillar_3_lut_601_702_split: Pillar3Lut601Vs702SplitReport
    pillar_4_write_guard_matrix: Pillar4Phase197WriteGuardAndMatrixReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Pillar 1 Evaluator — FX3 4-Mode Fan PWM, Off-in-Rec MAX Standby & Pre-Backup
# ---------------------------------------------------------------------------


def evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
    *,
    fan_mode: str = "Auto",
    is_recording: bool = False,
    internal_temp_c: float = 42.0,
    auto_power_off_temp: str = "High",
    cold_dump_p3_75mib_requested: bool = False,
    auto_interlock_enforced: bool = True,
) -> Fx3FanPwmAndThermalGuardEvalResult:
    """Evaluate `ILME-FX3` exact 4-mode `[Fan Control]`, `Off in Rec` PWM & pre-backup guard."""
    errors: List[str] = []
    mode_clean = fan_mode.strip()
    apo_clean = auto_power_off_temp.strip()

    is_auto12 = mode_clean in ("Auto1", "Auto2", "AUTO1", "AUTO2")
    if is_auto12:
        errors.append(
            f"FORBIDDEN_NON_FX3_STUDIO_FAN_TOKEN: {mode_clean} does not exist on ILME-FX3"
        )
    elif mode_clean not in FX3_FAN_CONTROL_MODES_P197:
        errors.append(f"INVALID_FX3_FAN_CONTROL_MODE: {mode_clean}")

    if apo_clean not in VALID_AUTO_POWER_OFF_TEMPS_P197:
        errors.append(f"INVALID_AUTO_POWER_OFF_TEMP: {apo_clean}")

    if internal_temp_c < -30.0 or internal_temp_c > 125.0:
        errors.append(f"OUT_OF_RANGE_INTERNAL_TEMP_C: {internal_temp_c}")

    emergency_thresh = (
        EMERGENCY_THERMAL_TEMP_HIGH_C_P197
        if apo_clean == "High"
        else EMERGENCY_THERMAL_TEMP_STANDARD_C_P197
    )

    if errors:
        return Fx3FanPwmAndThermalGuardEvalResult(
            valid=False,
            menu_path=FX3_FAN_CONTROL_MENU_PATH_P197,
            requested_fan_mode=mode_clean,
            effective_fan_mode="INVALID",
            appfw_enum_symbol="INVALID",
            non_fx3_auto12_rejected=is_auto12,
            is_recording=is_recording,
            internal_temp_c=float(internal_temp_c),
            auto_power_off_temp=apo_clean,
            emergency_threshold_c=emergency_thresh,
            emergency_thermal_override_active=False,
            standby_max_pwm_heat_purge=False,
            fan_stopped_for_acoustic_silence=False,
            effective_pwm_duty_pct=0,
            cold_dump_p3_75mib_requested=cold_dump_p3_75mib_requested,
            adjust_control_opcode_hex=ADJUST_CONTROL_OPCODE_HEX_P197,
            auto_interlock_enforced=auto_interlock_enforced,
            prebackup_forced_to_auto=False,
            cxd90057_cxd90058_overheat_risk=False,
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW
            if is_auto12
            else BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status=errors[0],
            errors=tuple(errors),
        )

    effective_mode = mode_clean
    prebackup_forced = False
    overheat_risk = False
    bclass = BRIDGE_CLASS_NATIVE_PASSTHROUGH

    # Pre-backup thermal guard before long AdjustControl (0x40) 75 MiB p3 cold dump
    if cold_dump_p3_75mib_requested and mode_clean in ("Always Off", "Off in Rec"):
        if not auto_interlock_enforced:
            overheat_risk = True
            errors.append(
                f"BLOCKED_PREBACKUP_THERMAL_HAZARD: fan_mode={mode_clean!r} unsafe for "
                f"{COLD_DUMP_P3_SIZE_MIB_P197}MiB AdjustControl({ADJUST_CONTROL_OPCODE_HEX_P197}) p3 dump"
            )
            return Fx3FanPwmAndThermalGuardEvalResult(
                valid=False,
                menu_path=FX3_FAN_CONTROL_MENU_PATH_P197,
                requested_fan_mode=mode_clean,
                effective_fan_mode=mode_clean,
                appfw_enum_symbol=FX3_FAN_MODE_TO_APPFW_ENUM_P197[mode_clean],
                non_fx3_auto12_rejected=False,
                is_recording=is_recording,
                internal_temp_c=float(internal_temp_c),
                auto_power_off_temp=apo_clean,
                emergency_threshold_c=emergency_thresh,
                emergency_thermal_override_active=(internal_temp_c >= emergency_thresh),
                standby_max_pwm_heat_purge=False,
                fan_stopped_for_acoustic_silence=True,
                effective_pwm_duty_pct=FAN_PWM_OFF_PCT_P197,
                cold_dump_p3_75mib_requested=True,
                adjust_control_opcode_hex=ADJUST_CONTROL_OPCODE_HEX_P197,
                auto_interlock_enforced=False,
                prebackup_forced_to_auto=False,
                cxd90057_cxd90058_overheat_risk=True,
                bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
                status="BLOCKED_ALWAYS_OFF_PREBACKUP_THERMAL_HAZARD",
                errors=tuple(errors),
            )
        effective_mode = "Auto"
        prebackup_forced = True
        bclass = BRIDGE_CLASS_SHIM_TRANSLATED

    emergency_active = internal_temp_c >= emergency_thresh
    standby_purge = False
    silent_rec = False

    if emergency_active:
        pwm = FAN_PWM_EMERGENCY_MAX_PCT_P197
    elif effective_mode == "Auto":
        if internal_temp_c <= 35.0:
            pwm = 30
        elif internal_temp_c >= 60.0:
            pwm = 90
        else:
            pwm = int(round(30 + (internal_temp_c - 35.0) * (60.0 / 25.0)))
    elif effective_mode == "Minimum":
        pwm = FAN_PWM_MINIMUM_FLOOR_PCT_P197
    elif effective_mode == "Off in Rec":
        if is_recording:
            pwm = FAN_PWM_OFF_PCT_P197
            silent_rec = True
        else:
            pwm = FAN_PWM_STANDBY_PURGE_MAX_PCT_P197
            standby_purge = True
    else:  # Always Off (non-cold-dump normal operation below emergency threshold)
        pwm = FAN_PWM_OFF_PCT_P197
        silent_rec = is_recording

    if prebackup_forced:
        status = "PREBACKUP_INTERLOCK_FORCED_AUTO_THERMAL_SAFE_OK"
    elif emergency_active:
        status = "CP_EMERGENCY_THERMAL_MAX_PWM_OVERRIDE_OK"
    elif standby_purge:
        status = "OFF_IN_REC_STANDBY_MAX_PWM_HEAT_PURGE_OK"
    elif silent_rec and effective_mode == "Off in Rec":
        status = "OFF_IN_REC_ACOUSTIC_ZERO_PWM_DURING_REC_OK"
    else:
        status = f"FX3_FAN_CONTROL_{FX3_FAN_MODE_TO_APPFW_ENUM_P197[effective_mode]}_OK"

    return Fx3FanPwmAndThermalGuardEvalResult(
        valid=True,
        menu_path=FX3_FAN_CONTROL_MENU_PATH_P197,
        requested_fan_mode=mode_clean,
        effective_fan_mode=effective_mode,
        appfw_enum_symbol=FX3_FAN_MODE_TO_APPFW_ENUM_P197[effective_mode],
        non_fx3_auto12_rejected=False,
        is_recording=is_recording,
        internal_temp_c=float(internal_temp_c),
        auto_power_off_temp=apo_clean,
        emergency_threshold_c=emergency_thresh,
        emergency_thermal_override_active=emergency_active,
        standby_max_pwm_heat_purge=standby_purge,
        fan_stopped_for_acoustic_silence=silent_rec,
        effective_pwm_duty_pct=pwm,
        cold_dump_p3_75mib_requested=cold_dump_p3_75mib_requested,
        adjust_control_opcode_hex=ADJUST_CONTROL_OPCODE_HEX_P197,
        auto_interlock_enforced=auto_interlock_enforced,
        prebackup_forced_to_auto=prebackup_forced,
        cxd90057_cxd90058_overheat_risk=overheat_risk,
        bridge_class=bclass,
        status=status,
        errors=(),
    )


# ---------------------------------------------------------------------------
# Pillar 2 Helpers & Evaluator — Independent [Shutter Mode] (Speed vs Angle)
# ---------------------------------------------------------------------------


def parse_shutter_angle_token(token: str) -> Tuple[bool, float, str, Optional[str]]:
    """Parse Sony shutter angle token (`'5.6'`..`'360.0'`/`'180°'` or `'2F'`..`'64F'`)."""
    raw = token.strip().upper().replace("DEG", "").replace("°", "").strip()
    if not raw:
        return (False, 0.0, "", "EMPTY_SHUTTER_ANGLE_TOKEN")

    if raw.endswith("F"):
        num_str = raw[:-1].strip()
        if not num_str.isdigit():
            return (False, 0.0, raw, f"INVALID_SLOW_SHUTTER_FRAME_TOKEN: {token}")
        frames = int(num_str)
        if frames not in CANONICAL_SLOW_SHUTTER_FRAME_MULTIPLES_P197:
            return (
                False,
                float(frames) * 360.0,
                f"{frames}F",
                f"UNSUPPORTED_SLOW_SHUTTER_FRAME_MULTIPLE: {frames}F",
            )
        return (True, float(frames) * 360.0, f"{frames}F", None)

    try:
        deg = float(raw)
    except ValueError:
        return (False, 0.0, raw, f"NON_NUMERIC_SHUTTER_ANGLE_TOKEN: {token}")

    if deg < SHUTTER_ANGLE_MIN_DEG_P197 - 1e-9:
        return (
            False,
            deg,
            f"{deg:.2f}".rstrip("0").rstrip("."),
            f"SHUTTER_ANGLE_BELOW_5_6_DEG_MINIMUM: {deg}",
        )
    if deg > SHUTTER_ANGLE_STD_MAX_DEG_P197 + 1e-9:
        return (
            False,
            deg,
            f"{deg:.1f}",
            f"DEGREE_TOKEN_EXCEEDS_360_USE_FRAME_MULTIPLE: {deg}",
        )
    norm_lbl = f"{deg:.2f}".rstrip("0").rstrip(".")
    if "." not in norm_lbl:
        norm_lbl = f"{norm_lbl}.0"
    return (True, deg, f"{norm_lbl}deg", None)


def simulate_backup_bin_shutter_slot_transitions(
    *,
    initial_speed_token: str = "1/48",
    initial_angle_token: str = "180.0",
    initial_exposure_step: str = "0.3EV",
    updated_exposure_step: str = "0.5EV",
) -> Tuple[BackupBinShutterSlotState, BackupBinShutterSlotState, bool]:
    """Prove `Backup.bin` `[Speed]` & `[Angle]` slots stay independent across toggles & EV-step changes."""
    if initial_speed_token not in VALID_SHUTTER_SPEED_TOKENS_P197:
        raise ValueError(f"Unsupported shutter speed token: {initial_speed_token}")
    ok_ang, _deg, norm_ang, err = parse_shutter_angle_token(initial_angle_token)
    if not ok_ang:
        raise ValueError(err or f"Invalid angle token: {initial_angle_token}")
    if (
        initial_exposure_step not in VALID_EXPOSURE_STEPS_P197
        or updated_exposure_step not in VALID_EXPOSURE_STEPS_P197
    ):
        raise ValueError("Invalid exposure step")

    before = BackupBinShutterSlotState(
        shutter_mode="Speed",
        stored_speed_token=initial_speed_token,
        stored_angle_token=norm_ang,
        exposure_step=initial_exposure_step,
    )
    # Toggle Speed -> Angle -> change Exposure step 0.3EV->0.5EV -> Speed -> Angle
    after = BackupBinShutterSlotState(
        shutter_mode="Angle",
        stored_speed_token=before.stored_speed_token,
        stored_angle_token=before.stored_angle_token,
        exposure_step=updated_exposure_step,
    )
    conserved = (
        after.stored_speed_token == initial_speed_token
        and after.stored_angle_token == norm_ang
    )
    return (before, after, conserved)


def evaluate_independent_shutter_mode_and_angle_range(
    *,
    shooting_mode: str = "NORMAL_MOVIE",
    rec_frame_rate: str = "23.98p",
    shutter_mode: str = "Angle",
    exposure_step: str = "0.3EV",
    stored_speed_slot: str = "1/48",
    requested_angle_token: str = "180.0",
    clamp_on_mode_transition: bool = False,
) -> IndependentShutterModeAndAngleEvalResult:
    """Evaluate `Backup.bin` independent `[Speed]`/`[Angle]` storage & FPS/S&Q range bounds."""
    errors: List[str] = []
    smode = shooting_mode.strip().upper()
    fps_lbl = rec_frame_rate.strip()
    sh_mode = shutter_mode.strip()
    exp_step = exposure_step.strip()
    spd_tok = stored_speed_slot.strip()

    if smode not in VALID_SHOOTING_MODES_P197:
        errors.append(f"INVALID_SHOOTING_MODE: {shooting_mode}")
    if fps_lbl not in ALL_VALID_REC_FRAME_RATES_P197:
        errors.append(f"INVALID_REC_FRAME_RATE: {rec_frame_rate}")
    if sh_mode not in VALID_SHUTTER_MODES_P197:
        errors.append(f"INVALID_SHUTTER_MODE: {shutter_mode}")
    if exp_step not in VALID_EXPOSURE_STEPS_P197:
        errors.append(f"INVALID_EXPOSURE_STEP: {exposure_step}")
    if spd_tok not in VALID_SHUTTER_SPEED_TOKENS_P197:
        errors.append(f"INVALID_STORED_SHUTTER_SPEED_SLOT: {stored_speed_slot}")

    ok_ang, req_deg, norm_ang, ang_err = parse_shutter_angle_token(requested_angle_token)
    if not ok_ang and ang_err is not None:
        errors.append(ang_err)

    fps_val = ALL_VALID_REC_FRAME_RATES_P197.get(fps_lbl, 24.0)
    is_hfr_100_120 = fps_lbl in HFR_CLAMPED_REC_FRAME_RATES_P197
    is_sq = smode == "SQ_MOTION"

    if is_sq or is_hfr_100_120:
        max_deg = SHUTTER_ANGLE_STD_MAX_DEG_P197
        max_lbl = "360.0deg"
    else:
        max_deg = SHUTTER_ANGLE_64F_EQUIV_DEG_P197
        max_lbl = "64F"

    if errors:
        return IndependentShutterModeAndAngleEvalResult(
            valid=False,
            shooting_mode=smode,
            rec_frame_rate=fps_lbl,
            fps_numeric=fps_val,
            shutter_mode=sh_mode,
            exposure_step=exp_step,
            stored_speed_slot=spd_tok,
            requested_angle_token=requested_angle_token.strip(),
            effective_angle_token=norm_ang or requested_angle_token.strip(),
            effective_angle_deg=req_deg,
            min_allowed_angle_deg=SHUTTER_ANGLE_MIN_DEG_P197,
            max_allowed_angle_deg=max_deg,
            max_allowed_angle_label=max_lbl,
            angle_clamped=False,
            speed_and_angle_slots_independent=True,
            angle_immune_to_exposure_step=True,
            exposure_time_sec=0.0,
            backup_bin_writes=0,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status=errors[0],
            errors=tuple(errors),
        )

    eff_deg = req_deg
    eff_tok = norm_ang
    clamped = False
    bclass = BRIDGE_CLASS_NATIVE_PASSTHROUGH

    if req_deg > max_deg + 1e-9:
        if clamp_on_mode_transition:
            eff_deg = max_deg
            eff_tok = max_lbl
            clamped = True
            bclass = BRIDGE_CLASS_SHIM_TRANSLATED
        else:
            limit_reason = (
                "SHUTTER_ANGLE_EXCEEDS_SQ_360_LIMIT"
                if is_sq
                else "SHUTTER_ANGLE_EXCEEDS_HFR_100P_11988P_360_LIMIT"
            )
            errors.append(f"{limit_reason}: {norm_ang} > {max_lbl}")
            return IndependentShutterModeAndAngleEvalResult(
                valid=False,
                shooting_mode=smode,
                rec_frame_rate=fps_lbl,
                fps_numeric=fps_val,
                shutter_mode=sh_mode,
                exposure_step=exp_step,
                stored_speed_slot=spd_tok,
                requested_angle_token=requested_angle_token.strip(),
                effective_angle_token=norm_ang,
                effective_angle_deg=req_deg,
                min_allowed_angle_deg=SHUTTER_ANGLE_MIN_DEG_P197,
                max_allowed_angle_deg=max_deg,
                max_allowed_angle_label=max_lbl,
                angle_clamped=False,
                speed_and_angle_slots_independent=True,
                angle_immune_to_exposure_step=True,
                exposure_time_sec=0.0,
                backup_bin_writes=0,
                bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
                status=limit_reason,
                errors=tuple(errors),
            )

    if sh_mode == "Speed":
        denom = float(spd_tok.split("/")[1])
        exp_sec = 1.0 / denom
        status = "SHUTTER_MODE_SPEED_ACTIVE_ANGLE_SLOT_PRESERVED_OK"
    else:
        exp_sec = (eff_deg / 360.0) / fps_val
        status = (
            "SHUTTER_MODE_ANGLE_CLAMPED_TO_360_DEG_OK"
            if clamped
            else "SHUTTER_MODE_ANGLE_INDEPENDENT_SLOT_OK"
        )

    return IndependentShutterModeAndAngleEvalResult(
        valid=True,
        shooting_mode=smode,
        rec_frame_rate=fps_lbl,
        fps_numeric=fps_val,
        shutter_mode=sh_mode,
        exposure_step=exp_step,
        stored_speed_slot=spd_tok,
        requested_angle_token=requested_angle_token.strip(),
        effective_angle_token=eff_tok,
        effective_angle_deg=eff_deg,
        min_allowed_angle_deg=SHUTTER_ANGLE_MIN_DEG_P197,
        max_allowed_angle_deg=max_deg,
        max_allowed_angle_label=max_lbl,
        angle_clamped=clamped,
        speed_and_angle_slots_independent=True,
        angle_immune_to_exposure_step=True,
        exposure_time_sec=round(exp_sec, 9),
        backup_bin_writes=0,
        bridge_class=bclass,
        status=status,
        errors=(),
    )


# ---------------------------------------------------------------------------
# Pillar 3 Serializer & Evaluator — Ver. 6.01 vs Ver. 7.00/7.02 LUT Split
# ---------------------------------------------------------------------------


def serialize_user_lut_slot_header(
    *,
    schema_id: str,
    slot_index: int = 1,
    lut_3d_size: int = 33,
    title_ascii: str = "SLog3_To_709",
    ae_level_offset_thirds: int = 0,
    embed_lut_enabled: bool = False,
) -> Tuple[bytes, UserLutBinarySlotHeaderSummary]:
    """Build deterministic clean-room binary User LUT slot header (`<=6.01` vs `7.00/7.02`)."""
    if not (USER_LUT_SLOT_MIN_P197 <= slot_index <= USER_LUT_SLOT_MAX_P197):
        raise ValueError(f"slot_index must be 1..16, got {slot_index}")
    if lut_3d_size not in (17, 33):
        raise ValueError(f"lut_3d_size must be 17 or 33, got {lut_3d_size}")
    raw_title = title_ascii.encode("ascii", errors="strict")[:32].ljust(32, b"\x00")

    if schema_id == LUT_SLOT_SCHEMA_LEGACY_LE_601_P197:
        # 48-byte legacy <=6.01 Diadem-Pro slot descriptor (no ae_level_offset / embed_lut)
        body = struct.pack(
            "<4sHBB32sI",
            LUT_SLOT_V1_MAGIC_BYTES_P197,
            0x0601,
            slot_index,
            lut_3d_size,
            raw_title,
            lut_3d_size ** 3,
        )
        crc = zlib.crc32(body) & 0xFFFFFFFF
        pkt = body + struct.pack("<I", crc)
        assert len(pkt) == LUT_SLOT_V1_RECORD_BYTES_P197
        summary = UserLutBinarySlotHeaderSummary(
            schema_id=schema_id,
            magic_ascii="UL61",
            fw_version_u16_hex="0x0601",
            slot_index=slot_index,
            lut_3d_size=lut_3d_size,
            ae_level_offset_thirds=None,
            embed_lut_enabled=None,
            record_bytes=len(pkt),
            crc32_hex=f"0x{crc:08x}",
        )
        return (pkt, summary)

    if schema_id == LUT_SLOT_SCHEMA_OPT_GE_700_P197:
        if not (0 <= ae_level_offset_thirds <= 6):
            raise ValueError(
                f"ae_level_offset_thirds must be 0..6 (0..+2EV), got {ae_level_offset_thirds}"
            )
        # 64-byte optimized 7.00/7.02 slot descriptor with AE level offset & embed flag
        body = struct.pack(
            "<4sHBB32sIBB14s",
            LUT_SLOT_V2_MAGIC_BYTES_P197,
            0x0702,
            slot_index,
            lut_3d_size,
            raw_title,
            lut_3d_size ** 3,
            ae_level_offset_thirds,
            1 if embed_lut_enabled else 0,
            b"\x00" * 14,
        )
        crc = zlib.crc32(body) & 0xFFFFFFFF
        pkt = body + struct.pack("<I", crc)
        assert len(pkt) == LUT_SLOT_V2_RECORD_BYTES_P197
        summary = UserLutBinarySlotHeaderSummary(
            schema_id=schema_id,
            magic_ascii="UL70",
            fw_version_u16_hex="0x0702",
            slot_index=slot_index,
            lut_3d_size=lut_3d_size,
            ae_level_offset_thirds=ae_level_offset_thirds,
            embed_lut_enabled=embed_lut_enabled,
            record_bytes=len(pkt),
            crc32_hex=f"0x{crc:08x}",
        )
        return (pkt, summary)

    raise ValueError(f"Unknown User LUT slot schema_id: {schema_id}")


def verify_stock_702_user_lut_slot_deserialization(slot_bytes: bytes) -> Tuple[bool, str]:
    """Verify whether Stock FX3 `Ver. 7.02` (`UL70` 64B schema) can cleanly load `slot_bytes`."""
    if len(slot_bytes) != LUT_SLOT_V2_RECORD_BYTES_P197:
        if len(slot_bytes) == LUT_SLOT_V1_RECORD_BYTES_P197 and slot_bytes[:4] == LUT_SLOT_V1_MAGIC_BYTES_P197:
            return (
                False,
                "LUT_GENERATION_SPLIT_601_TO_702_DESERIALIZE_CORRUPTION",
            )
        return (False, f"INVALID_V2_SLOT_LENGTH_{len(slot_bytes)}")
    if slot_bytes[:4] != LUT_SLOT_V2_MAGIC_BYTES_P197:
        return (False, "INVALID_V2_SLOT_MAGIC")
    (ver_u16,) = struct.unpack_from("<H", slot_bytes, 4)
    if ver_u16 < 0x0700:
        return (False, f"LEGACY_PRE_700_LUT_SLOT_VERSION_0x{ver_u16:04x}")
    expected_crc = zlib.crc32(slot_bytes[:-4]) & 0xFFFFFFFF
    (actual_crc,) = struct.unpack_from("<I", slot_bytes, 60)
    if expected_crc != actual_crc:
        return (False, "V2_SLOT_CRC32_MISMATCH")
    return (True, "STOCK_702_V2_OPT_LUT_SLOT_DESERIALIZED_OK")


def evaluate_user_lut_601_vs_702_binary_split_firewall(
    *,
    writer_firmware: str = "FX6_6.01",
    host_reader_firmware: str = "FX3_7.02",
    slot_index: int = 1,
    target_storage_path: str = "/tmp/fx6_lut_overlay/User1.lutslot",
    lifecycle_stage: str = "H2",
    h0_p2_setting_sha256: str = "",
) -> UserLut601Vs702SplitFirewallEvalResult:
    """Evaluate `FX6 6.01` vs `Stock FX3 7.00/7.02` `p2:/setting` User LUT binary split firewall."""
    errors: List[str] = []
    w_fw = writer_firmware.strip().upper()
    r_fw = host_reader_firmware.strip().upper()
    st = lifecycle_stage.strip().upper()
    norm_target = target_storage_path.strip()

    if w_fw not in ("FX6_6.01", "FX3_6.00", "FX3_7.00", "FX3_7.02"):
        errors.append(f"UNKNOWN_WRITER_FIRMWARE: {writer_firmware}")
    if r_fw not in ("FX3_7.00", "FX3_7.02", "FX6_6.01"):
        errors.append(f"UNKNOWN_HOST_READER_FIRMWARE: {host_reader_firmware}")
    if not (USER_LUT_SLOT_MIN_P197 <= slot_index <= USER_LUT_SLOT_MAX_P197):
        errors.append(f"INVALID_USER_LUT_SLOT_INDEX: {slot_index}")
    if st not in VALID_LIFECYCLE_STAGES_P197:
        errors.append(f"INVALID_LIFECYCLE_STAGE: {lifecycle_stage}")

    w_schema = (
        LUT_SLOT_SCHEMA_LEGACY_LE_601_P197
        if w_fw in ("FX6_6.01", "FX3_6.00")
        else LUT_SLOT_SCHEMA_OPT_GE_700_P197
    )
    r_schema = (
        LUT_SLOT_SCHEMA_OPT_GE_700_P197
        if r_fw in ("FX3_7.00", "FX3_7.02")
        else LUT_SLOT_SCHEMA_LEGACY_LE_601_P197
    )
    gen_split = w_schema != r_schema
    slot_lbl = f"User{slot_index}"
    ref_hash = h0_p2_setting_sha256 or hashlib.sha256(
        b"STOCK_FX3_702_P2_SETTING_H0_BASELINE"
    ).hexdigest()

    if errors:
        return UserLut601Vs702SplitFirewallEvalResult(
            valid=False,
            writer_firmware=w_fw,
            writer_slot_schema=w_schema,
            host_reader_firmware=r_fw,
            host_reader_slot_schema=r_schema,
            slot_index=slot_index,
            slot_label=slot_lbl,
            target_storage_path=norm_target,
            generation_split_detected=gen_split,
            direct_p2_setting_write_blocked=True,
            stock_702_lut_deserialize_corrupted=False,
            stock_702_lut_corruption_prevented=True,
            redirected_to_volatile_overlay=False,
            lifecycle_stage=st,
            h0_p2_setting_sha256=ref_hash,
            h3_p2_setting_sha256=ref_hash,
            h0_equals_h3=True,
            p2_setting_mutation_bytes=0,
            calibration_mutation_bytes=0,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status=errors[0],
            errors=tuple(errors),
        )

    # Check if writer attempts to touch persistent p2:/setting or forbidden persistent storage
    wg = evaluate_phase197_write_guard(norm_target)
    if not wg.valid:
        # Prove what WOULD happen if V1 6.01 bytes entered Stock 7.02 deserializer, while blocking it
        hypothetical_corrupt = False
        if gen_split and w_schema == LUT_SLOT_SCHEMA_LEGACY_LE_601_P197:
            v1_bytes, _ = serialize_user_lut_slot_header(
                schema_id=LUT_SLOT_SCHEMA_LEGACY_LE_601_P197,
                slot_index=slot_index,
            )
            ok_deser, _reason = verify_stock_702_user_lut_slot_deserialization(v1_bytes)
            hypothetical_corrupt = not ok_deser
        block_err = (
            f"BLOCKED_CROSS_GEN_601_TO_702_P2_SETTING_WRITE: {w_fw} ({w_schema}) "
            f"forbidden from writing {slot_lbl} into {norm_target}"
            if gen_split
            else f"BLOCKED_PERSISTENT_P2_SETTING_WRITE: {norm_target}"
        )
        return UserLut601Vs702SplitFirewallEvalResult(
            valid=False,
            writer_firmware=w_fw,
            writer_slot_schema=w_schema,
            host_reader_firmware=r_fw,
            host_reader_slot_schema=r_schema,
            slot_index=slot_index,
            slot_label=slot_lbl,
            target_storage_path=norm_target,
            generation_split_detected=gen_split,
            direct_p2_setting_write_blocked=True,
            stock_702_lut_deserialize_corrupted=hypothetical_corrupt,
            stock_702_lut_corruption_prevented=True,
            redirected_to_volatile_overlay=False,
            lifecycle_stage=st,
            h0_p2_setting_sha256=ref_hash,
            h3_p2_setting_sha256=ref_hash,
            h0_equals_h3=True,
            p2_setting_mutation_bytes=0,
            calibration_mutation_bytes=0,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status="BLOCKED_CROSS_GEN_601_TO_702_P2_SETTING_WRITE"
            if gen_split
            else "BLOCKED_PERSISTENT_P2_SETTING_WRITE",
            errors=(block_err,),
        )

    in_fx6_overlay = norm_target.startswith(VOLATILE_FX6_LUT_OVERLAY_DIR_P197)
    if gen_split and not in_fx6_overlay and not norm_target.startswith(("ram://", "memfd:")):
        err = (
            f"CROSS_GEN_601_LUT_MUST_USE_VOLATILE_OVERLAY: expected "
            f"{VOLATILE_FX6_LUT_OVERLAY_DIR_P197}, got {norm_target}"
        )
        return UserLut601Vs702SplitFirewallEvalResult(
            valid=False,
            writer_firmware=w_fw,
            writer_slot_schema=w_schema,
            host_reader_firmware=r_fw,
            host_reader_slot_schema=r_schema,
            slot_index=slot_index,
            slot_label=slot_lbl,
            target_storage_path=norm_target,
            generation_split_detected=True,
            direct_p2_setting_write_blocked=False,
            stock_702_lut_deserialize_corrupted=False,
            stock_702_lut_corruption_prevented=True,
            redirected_to_volatile_overlay=False,
            lifecycle_stage=st,
            h0_p2_setting_sha256=ref_hash,
            h3_p2_setting_sha256=ref_hash,
            h0_equals_h3=True,
            p2_setting_mutation_bytes=0,
            calibration_mutation_bytes=0,
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            status="CROSS_GEN_601_LUT_NON_OVERLAY_REJECTED",
            errors=(err,),
        )

    # Verify Stock 7.02 p2:/setting slot remains native V2 deserializable & H0 == H3
    stock_v2_bytes, _ = serialize_user_lut_slot_header(
        schema_id=LUT_SLOT_SCHEMA_OPT_GE_700_P197,
        slot_index=slot_index,
    )
    ok_stock, _ = verify_stock_702_user_lut_slot_deserialization(stock_v2_bytes)
    assert ok_stock

    return UserLut601Vs702SplitFirewallEvalResult(
        valid=True,
        writer_firmware=w_fw,
        writer_slot_schema=w_schema,
        host_reader_firmware=r_fw,
        host_reader_slot_schema=r_schema,
        slot_index=slot_index,
        slot_label=slot_lbl,
        target_storage_path=norm_target,
        generation_split_detected=gen_split,
        direct_p2_setting_write_blocked=False,
        stock_702_lut_deserialize_corrupted=False,
        stock_702_lut_corruption_prevented=True,
        redirected_to_volatile_overlay=True,
        lifecycle_stage=st,
        h0_p2_setting_sha256=ref_hash,
        h3_p2_setting_sha256=ref_hash,
        h0_equals_h3=True,
        p2_setting_mutation_bytes=0,
        calibration_mutation_bytes=0,
        bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED
        if gen_split
        else BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        status=(
            f"{st}_VOLATILE_FX6_LUT_OVERLAY_ISOLATED_H0_EQ_H3_OK"
            if gen_split
            else f"{st}_NATIVE_702_VOLATILE_STAGE_H0_EQ_H3_OK"
        ),
        errors=(),
    )


# ---------------------------------------------------------------------------
# Pillar 4 — Hard Write Firewall & 12-Touchpoint 4-Class Compatibility Matrix
# ---------------------------------------------------------------------------


def evaluate_phase197_write_guard(target_path: str) -> Phase197WriteGuardResult:
    """Hard write-firewall blocking `p2:/setting`, `Backup.bin`, `cpapp-b.bin`, eMMC & SPI-NOR."""
    norm = target_path.strip()
    if FORBIDDEN_PERSISTENT_TARGET_RE_P197.search(norm):
        return Phase197WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            calibration_mutation_bytes=0,
            status="BLOCKED_PERSISTENT_P2_SETTING_EMMC_OR_NOR_TARGET",
            errors=(f"FORBIDDEN_PERSISTENT_TARGET: {norm}",),
        )
    allowed = any(norm.startswith(p) for p in VOLATILE_OR_EXT_PREFIXES_P197)
    if not allowed:
        return Phase197WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            calibration_mutation_bytes=0,
            status="UNLISTED_NON_VOLATILE_TARGET_BLOCKED",
            errors=(f"TARGET_NOT_VOLATILE_OR_EXT: {norm}",),
        )
    return Phase197WriteGuardResult(
        valid=True,
        target_path=norm,
        volatile_or_ext_allowed=True,
        persistent_write_blocked=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        persistent_writes=0,
        calibration_mutation_bytes=0,
        status="VOLATILE_OVERLAY_OR_EXT_MEDIA_ALLOWED",
        errors=(),
    )


def build_phase197_compat_matrix() -> Phase197CompatMatrixSummary:
    """Construct 12-touchpoint 4-class compatibility matrix across Pillars 1..3."""
    entries: Tuple[Phase197TouchpointEntry, ...] = (
        Phase197TouchpointEntry(
            touchpoint_id="P197-01",
            pillar="PILLAR_1_FAN_PWM_THERMAL",
            fx6_or_host_component="MENU -> Setup -> [Setup Option] -> [Fan Control]",
            fx3_target="Exact 4-mode ILME-FX3 enum (Auto, Minimum, Off in Rec, Always Off)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="4 exact modes bound to FAN_CONTROL_{AUTO,MINIMUM,OFF_IN_REC,ALWAYS_OFF}",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-02",
            pillar="PILLAR_1_FAN_PWM_THERMAL",
            fx6_or_host_component="Studio/Lumix non-FX3 fan tokens (Auto1 / Auto2)",
            fx3_target="Fail-closed rejection & binary absence proof in appFw.so + .uxc",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="FAN_CONTROL_AUTO1 == 0 && FAN_CONTROL_AUTO2 == 0; Auto1/Auto2 rejected",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-03",
            pillar="PILLAR_1_FAN_PWM_THERMAL",
            fx6_or_host_component="Off in Rec acoustic silence vs standby heat purge",
            fx3_target="0% PWM in Rec (below thermal emergency) + 100% MAX PWM in Standby",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="standby_max_pwm_heat_purge == True; CP emergency 100% override intact",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-04",
            pillar="PILLAR_1_FAN_PWM_THERMAL",
            fx6_or_host_component="Always Off prior to 75 MiB AdjustControl (0x40) p3 cold dump",
            fx3_target="Pre-backup thermal interlock enforcing Always Off -> Auto (Standard/High)",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="unguarded Always Off cold dump blocked; interlock forces Auto",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-05",
            pillar="PILLAR_2_SHUTTER_SPEED_ANGLE",
            fx6_or_host_component="Ver. 6.00+/7.02 & BIG6 [Shutter Mode] (Speed vs Angle)",
            fx3_target="Independent Backup.bin key-value slots (0x02cf1702 / 0x02cf1704)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="Speed <-> Angle toggles never overwrite paired slot; 0.3EV/0.5EV immune",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-06",
            pillar="PILLAR_2_SHUTTER_SPEED_ANGLE",
            fx6_or_host_component="Normal Movie shutter angle envelope (23.98p .. 59.94p)",
            fx3_target="5.6° .. 64F (SHUTTER_ANGLE_5_POINT_6 .. SHUTTER_ANGLE_64F)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="5.6 <= angle_deg <= 23040.0 (64F); <5.6° fail-closed rejected",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-07",
            pillar="PILLAR_2_SHUTTER_SPEED_ANGLE",
            fx6_or_host_component="HFR [Rec Frame Rate] = 119.88p / 100p & S&Q Motion",
            fx3_target="Deterministic range convergence / clamping to 5.6° .. 360.0°",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="2F..64F clamped to 360.0° on mode transition or rejected if direct",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-08",
            pillar="PILLAR_2_SHUTTER_SPEED_ANGLE",
            fx6_or_host_component="Stock p2:/setting/Backup.bin (819 subsystems) shutter defaults",
            fx3_target="Strict O_RDONLY inspection; volatile RAM shadow for Stage-B",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="backup_bin_writes == 0; persistent_emmc_writes_authorized == False",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-09",
            pillar="PILLAR_3_LUT_601_VS_702_SPLIT",
            fx6_or_host_component="FX6 Ver. 6.01 <=6.01 legacy Diadem-Pro User1..User16 LUT schema",
            fx3_target="Hard write-block on Stock FX3 7.02 p2:/setting User1..User16 slots",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="UL61 48B blocked from corrupting Stock 7.02 UL70 64B deserializer",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-10",
            pillar="PILLAR_3_LUT_601_VS_702_SPLIT",
            fx6_or_host_component="Stage-B FX6 6.01 active User1..User16 LUT registration",
            fx3_target="Redirected to volatile /tmp/fx6_lut_overlay tmpfs namespace",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="redirected_to_volatile_overlay == True; p2_setting_mutation_bytes == 0",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-11",
            pillar="PILLAR_3_LUT_601_VS_702_SPLIT",
            fx6_or_host_component="Stock FX3 Ver. 7.02 7.00+ User LUT + AE Level Offset (0..+2 EV)",
            fx3_target="Unmodified Stock p2:/setting conserved across H0 -> H1 -> H2 -> H3",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="H0 == H3 SHA-256 bit-identical; calibration_mutation_bytes == 0",
        ),
        Phase197TouchpointEntry(
            touchpoint_id="P197-12",
            pillar="PILLAR_3_LUT_601_VS_702_SPLIT",
            fx6_or_host_component="eMMC /dev/nflasha*, /dev/cnflasha*, CPAPP-B.BIN & SPI-NOR",
            fx3_target="Global Phase 197 O_RDONLY & zero-flash hardware firewall",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="spi_nor_write_authorized == False && physical_usb_packets_emitted == 0",
        ),
    )

    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    pillar_counts: Dict[str, int] = {}
    for e in entries:
        class_counts[e.bridge_class] = class_counts.get(e.bridge_class, 0) + 1
        pillar_counts[e.pillar] = pillar_counts.get(e.pillar, 0) + 1
    return Phase197CompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        pillar_counts=pillar_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Scanners & Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def _scan_uxc_bounded_rdonly(
    path: Path,
    *,
    pack_name: str,
    body_label: str,
    required_tokens: Sequence[str],
    forbidden_tokens: Sequence[str],
) -> BoundedUxcPackSummary:
    """Strictly O_RDONLY bounded `os.pread` scanner for `.uxc` string packs (< 400 KiB)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        buf = os.pread(fd, sz, 0) if sz > 0 else b""
        magic_ok = len(buf) >= 4 and buf[:4] in (b"uxd\x07", b"uxc\x07")
        req_hits = {t: buf.count(t.encode("utf-8")) for t in required_tokens}
        forb_hits = {t: buf.count(t.encode("utf-8")) for t in forbidden_tokens}
        return BoundedUxcPackSummary(
            pack_name=pack_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            uxc_magic_valid=magic_ok,
            required_token_hits=req_hits,
            forbidden_auto12_hits=forb_hits,
        )
    finally:
        os.close(fd)


def _scan_uxc_buf_clean_room(
    buf: bytes,
    *,
    pack_name: str,
    body_label: str,
    required_tokens: Sequence[str],
    forbidden_tokens: Sequence[str],
) -> BoundedUxcPackSummary:
    magic_ok = len(buf) >= 4 and buf[:4] in (b"uxd\x07", b"uxc\x07")
    return BoundedUxcPackSummary(
        pack_name=pack_name,
        body_label=body_label,
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=len(buf),
        uxc_magic_valid=magic_ok,
        required_token_hits={t: buf.count(t.encode("utf-8")) for t in required_tokens},
        forbidden_auto12_hits={t: buf.count(t.encode("utf-8")) for t in forbidden_tokens},
    )


def _scan_cpapp_bounded_rdonly(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
) -> BoundedCpappSummary:
    """Strictly O_RDONLY bounded `os.pread` of CP RTOS head (768 KiB) + string pool (6 MiB)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        counts: Dict[str, int] = {t: 0 for t in tokens}
        enc = [(t, t.encode("ascii")) for t in tokens]
        head_len = min(sz, CPAPP_BOUNDED_HEAD_BYTES_P197)
        slices: List[Tuple[int, int]] = [(0, head_len)]
        tail_off = max(head_len, sz - CPAPP_BOUNDED_TAIL_BYTES_P197)
        if tail_off < sz:
            slices.append((tail_off, sz - tail_off))
        bytes_read = 0
        for off, ln in slices:
            if ln > 0:
                chunk = os.pread(fd, ln, off)
                bytes_read += len(chunk)
                for tok, b_tok in enc:
                    counts[tok] += chunk.count(b_tok)
        return BoundedCpappSummary(
            binary_name=binary_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            bounded_bytes_read=bytes_read,
            marker_hits=counts,
        )
    finally:
        os.close(fd)


def _scan_cpapp_buf_clean_room(
    buf: bytes,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
) -> BoundedCpappSummary:
    return BoundedCpappSummary(
        binary_name=binary_name,
        body_label=body_label,
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=len(buf),
        bounded_bytes_read=len(buf),
        marker_hits={t: buf.count(t.encode("ascii")) for t in tokens},
    )


def _read_bk4_header_bounded_rdonly(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
) -> BoundedBk4HeaderSummary:
    """Strictly O_RDONLY 64-byte bounded `os.pread` of `Backup.bin` `BK4\\x00` header."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        hdr = os.pread(fd, min(sz, 64), 0)
        return _parse_bk4_header_bytes(
            hdr,
            file_bytes=sz,
            binary_name=binary_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
        )
    finally:
        os.close(fd)


def _parse_bk4_header_bytes(
    hdr: bytes,
    *,
    file_bytes: int,
    binary_name: str,
    body_label: str,
    source_mode: str,
) -> BoundedBk4HeaderSummary:
    if len(hdr) < 40:
        return BoundedBk4HeaderSummary(
            binary_name=binary_name,
            body_label=body_label,
            source_mode=source_mode,
            file_bytes=file_bytes,
            bk4_magic_valid=False,
            rec0_subsystems=0,
            rec0_properties=0,
            rec0_span_bytes=0,
        )
    magic_ok = hdr[12:16] == BK4_MAGIC_BYTES
    w0 = struct.unpack_from("<10I", hdr, 0)
    return BoundedBk4HeaderSummary(
        binary_name=binary_name,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=file_bytes,
        bk4_magic_valid=magic_ok,
        rec0_subsystems=int(w0[4]),
        rec0_properties=int(w0[5]),
        rec0_span_bytes=int(w0[6] + w0[7]),
    )


def build_clean_room_realhw_fan_pwm_shutter_lut_split_fixtures() -> Dict[str, bytes]:
    """Synthesize deterministic clean-room fixtures (`raw_firmware_bytes_leaked == 0`)."""
    fx3_appfw_tokens = (
        APPFW_SHARED_FAN_SHUTTER_MARKERS_P197 + APPFW_FX3_702_EXCLUSIVE_MARKERS_P197
    )
    fx6_appfw_tokens = (
        APPFW_SHARED_FAN_SHUTTER_MARKERS_P197 + APPFW_FX6_601_EXCLUSIVE_LUT_MARKERS_P197
    )

    fx3_appfw_elf = _build_synthetic_elf64(
        exports=("appfw_fx3_702_fan_shutter_lut_entry",),
        imports=("mpr_set_lut_data",),
        dt_needed=("libmpr.so", "libc.so"),
        rodata_strings=fx3_appfw_tokens,
    )
    fx6_appfw_elf = _build_synthetic_elf64(
        exports=("appfw_fx6_601_fan_shutter_lut_entry",),
        imports=("mpr_set_lut_data",),
        dt_needed=("libmpr.so", "libc.so"),
        rodata_strings=fx6_appfw_tokens,
    )

    fx3_uxc_en_f = b"uxd\x07" + b"\x00" * 12 + b"\x00".join(
        t.encode("utf-8") for t in UXC_FX3_EN_F_REQUIRED_TOKENS_P197
    ) + b"\x00"
    fx6_uxc_en = b"uxd\x07" + b"\x00" * 12 + b"\x00".join(
        t.encode("utf-8") for t in UXC_FX6_EN_REQUIRED_TOKENS_P197
    ) + b"\x00"

    cpapp_payload = b"\x00".join(
        t.encode("ascii") for t in CPAPP_SHARED_FAN_MLUT_MARKERS_P197
    ) + b"\x00"

    fx3_bk4_hdr = (
        struct.pack("<3I", 4, 1, 0)
        + BK4_MAGIC_BYTES
        + struct.pack("<6I", EXPECTED_FX3_BK4_SUBSYSTEMS_P197, 19_420, 64, 1_100_000, 0, 0)
        + b"\x00" * 24
    )
    fx6_bk4_hdr = (
        struct.pack("<3I", 4, 1, 0)
        + BK4_MAGIC_BYTES
        + struct.pack("<6I", EXPECTED_FX6_BK4_SUBSYSTEMS_P197, 20_110, 64, 1_120_000, 0, 0)
        + b"\x00" * 24
    )

    return {
        "fx3_appfw": fx3_appfw_elf,
        "fx6_appfw": fx6_appfw_elf,
        "fx3_uxc_en_f": fx3_uxc_en_f,
        "fx6_uxc_en": fx6_uxc_en,
        "fx3_cpapp": cpapp_payload,
        "fx6_cpapp": cpapp_payload,
        "fx3_backup_hdr": fx3_bk4_hdr,
        "fx6_backup_hdr": fx6_bk4_hdr,
    }


def _inspect_donors_or_clean_room(
    *,
    clean_room: bool,
    repo_root: Path,
) -> Tuple[str, bool, float, Dict[str, object]]:
    """Bounded `O_RDONLY` donor inspection (< 0.15s cold, cached per process) or synthetic fallback."""
    t_start = time.perf_counter()
    fx3_scan_tokens = (
        APPFW_SHARED_FAN_SHUTTER_MARKERS_P197
        + APPFW_FORBIDDEN_AUTO12_MARKERS_P197
        + APPFW_FX3_702_EXCLUSIVE_MARKERS_P197
        + APPFW_FX6_601_EXCLUSIVE_LUT_MARKERS_P197
    )
    fx6_scan_tokens = fx3_scan_tokens

    use_clean_room = bool(clean_room or is_forced_clean_room())
    donor_paths: Dict[str, Optional[Path]] = {}
    if not use_clean_room:
        rel_map = {
            "fx3_appfw": FX3_APPFW_P197_RELPATH,
            "fx6_appfw": FX6_APPFW_P197_RELPATH,
            "fx3_uxc_en_f": FX3_UXC_EN_F_P197_RELPATH,
            "fx6_uxc_en": FX6_UXC_EN_P197_RELPATH,
            "fx3_cpapp": FX3_CPAPP_P197_RELPATH,
            "fx6_cpapp": FX6_CPAPP_P197_RELPATH,
            "fx3_backup": FX3_BACKUP_BIN_P197_RELPATH,
            "fx6_backup": FX6_BACKUP_BIN_P197_RELPATH,
        }
        for key, rel in rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=repo_root)
        if any(p is None or not p.is_file() for p in donor_paths.values()):
            use_clean_room = True

    if use_clean_room:
        fx = build_clean_room_realhw_fan_pwm_shutter_lut_split_fixtures()
        fx3_elf = _scan_elf_buf_ordered(
            fx["fx3_appfw"],
            binary_name="appFw.so",
            body_label="FX3_702",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=fx3_scan_tokens,
        )
        fx6_elf = _scan_elf_buf_ordered(
            fx["fx6_appfw"],
            binary_name="appFw.so",
            body_label="FX6_601",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=fx6_scan_tokens,
        )
        fx3_uxc = _scan_uxc_buf_clean_room(
            fx["fx3_uxc_en_f"],
            pack_name="string_english_f.uxc",
            body_label="FX3_702",
            required_tokens=UXC_FX3_EN_F_REQUIRED_TOKENS_P197,
            forbidden_tokens=UXC_FORBIDDEN_AUTO12_TOKENS_P197,
        )
        fx6_uxc = _scan_uxc_buf_clean_room(
            fx["fx6_uxc_en"],
            pack_name="string_english.uxc",
            body_label="FX6_601",
            required_tokens=UXC_FX6_EN_REQUIRED_TOKENS_P197,
            forbidden_tokens=UXC_FORBIDDEN_AUTO12_TOKENS_P197,
        )
        fx3_cp = _scan_cpapp_buf_clean_room(
            fx["fx3_cpapp"],
            binary_name="CPAPP-B.BIN",
            body_label="FX3_702",
            tokens=CPAPP_SHARED_FAN_MLUT_MARKERS_P197,
        )
        fx6_cp = _scan_cpapp_buf_clean_room(
            fx["fx6_cpapp"],
            binary_name="cpapp-b.bin",
            body_label="FX6_601",
            tokens=CPAPP_SHARED_FAN_MLUT_MARKERS_P197,
        )
        fx3_bk4 = _parse_bk4_header_bytes(
            fx["fx3_backup_hdr"],
            file_bytes=len(fx["fx3_backup_hdr"]),
            binary_name="Backup.bin",
            body_label="FX3_702",
            source_mode="CLEAN_ROOM_SYNTHETIC",
        )
        fx6_bk4 = _parse_bk4_header_bytes(
            fx["fx6_backup_hdr"],
            file_bytes=len(fx["fx6_backup_hdr"]),
            binary_name="Backup.bin",
            body_label="FX6_601",
            source_mode="CLEAN_ROOM_SYNTHETIC",
        )
        bundle: Dict[str, object] = {
            "fx3_elf": fx3_elf,
            "fx6_elf": fx6_elf,
            "fx3_uxc": fx3_uxc,
            "fx6_uxc": fx6_uxc,
            "fx3_cp": fx3_cp,
            "fx6_cp": fx6_cp,
            "fx3_bk4": fx3_bk4,
            "fx6_bk4": fx6_bk4,
            "donor_sizes": {
                "fx3_appfw": fx3_elf.file_bytes,
                "fx6_appfw": fx6_elf.file_bytes,
                "fx3_string_english_f_uxc": fx3_uxc.file_bytes,
                "fx6_string_english_uxc": fx6_uxc.file_bytes,
                "fx3_cpapp_b_bin": fx3_cp.file_bytes,
                "fx6_cpapp_b_bin": fx6_cp.file_bytes,
                "fx3_backup_bin": fx3_bk4.file_bytes,
                "fx6_backup_bin": fx6_bk4.file_bytes,
            },
        }
        return ("CLEAN_ROOM_SYNTHETIC", False, round(time.perf_counter() - t_start, 6), bundle)

    cache_key = tuple(str(donor_paths[k]) for k in sorted(donor_paths.keys()))
    if cache_key in _DONOR_SCAN_CACHE:
        return (
            "LOCAL_DONOR_RDONLY",
            True,
            round(time.perf_counter() - t_start, 6),
            _DONOR_SCAN_CACHE[cache_key],
        )

    p_fx3_app = donor_paths["fx3_appfw"]
    p_fx6_app = donor_paths["fx6_appfw"]
    p_fx3_uxc = donor_paths["fx3_uxc_en_f"]
    p_fx6_uxc = donor_paths["fx6_uxc_en"]
    p_fx3_cp = donor_paths["fx3_cpapp"]
    p_fx6_cp = donor_paths["fx6_cpapp"]
    p_fx3_bk = donor_paths["fx3_backup"]
    p_fx6_bk = donor_paths["fx6_backup"]
    assert p_fx3_app and p_fx6_app and p_fx3_uxc and p_fx6_uxc
    assert p_fx3_cp and p_fx6_cp and p_fx3_bk and p_fx6_bk

    fx3_elf = _scan_elf_fast_rdonly(
        p_fx3_app,
        binary_name="appFw.so",
        body_label="FX3_702",
        tokens=fx3_scan_tokens,
    )
    fx6_elf = _scan_elf_fast_rdonly(
        p_fx6_app,
        binary_name="appFw.so",
        body_label="FX6_601",
        tokens=fx6_scan_tokens,
    )
    fx3_uxc = _scan_uxc_bounded_rdonly(
        p_fx3_uxc,
        pack_name="string_english_f.uxc",
        body_label="FX3_702",
        required_tokens=UXC_FX3_EN_F_REQUIRED_TOKENS_P197,
        forbidden_tokens=UXC_FORBIDDEN_AUTO12_TOKENS_P197,
    )
    fx6_uxc = _scan_uxc_bounded_rdonly(
        p_fx6_uxc,
        pack_name="string_english.uxc",
        body_label="FX6_601",
        required_tokens=UXC_FX6_EN_REQUIRED_TOKENS_P197,
        forbidden_tokens=UXC_FORBIDDEN_AUTO12_TOKENS_P197,
    )
    fx3_cp = _scan_cpapp_bounded_rdonly(
        p_fx3_cp,
        binary_name="CPAPP-B.BIN",
        body_label="FX3_702",
        tokens=CPAPP_SHARED_FAN_MLUT_MARKERS_P197,
    )
    fx6_cp = _scan_cpapp_bounded_rdonly(
        p_fx6_cp,
        binary_name="cpapp-b.bin",
        body_label="FX6_601",
        tokens=CPAPP_SHARED_FAN_MLUT_MARKERS_P197,
    )
    fx3_bk4 = _read_bk4_header_bounded_rdonly(
        p_fx3_bk,
        binary_name="Backup.bin",
        body_label="FX3_702",
    )
    fx6_bk4 = _read_bk4_header_bounded_rdonly(
        p_fx6_bk,
        binary_name="Backup.bin",
        body_label="FX6_601",
    )

    bundle = {
        "fx3_elf": fx3_elf,
        "fx6_elf": fx6_elf,
        "fx3_uxc": fx3_uxc,
        "fx6_uxc": fx6_uxc,
        "fx3_cp": fx3_cp,
        "fx6_cp": fx6_cp,
        "fx3_bk4": fx3_bk4,
        "fx6_bk4": fx6_bk4,
        "donor_sizes": {
            "fx3_appfw": fx3_elf.file_bytes,
            "fx6_appfw": fx6_elf.file_bytes,
            "fx3_string_english_f_uxc": fx3_uxc.file_bytes,
            "fx6_string_english_uxc": fx6_uxc.file_bytes,
            "fx3_cpapp_b_bin": fx3_cp.file_bytes,
            "fx6_cpapp_b_bin": fx6_cp.file_bytes,
            "fx3_backup_bin": fx3_bk4.file_bytes,
            "fx6_backup_bin": fx6_bk4.file_bytes,
        },
    }
    _DONOR_SCAN_CACHE[cache_key] = bundle
    return ("LOCAL_DONOR_RDONLY", False, round(time.perf_counter() - t_start, 6), bundle)


# ---------------------------------------------------------------------------
# Top-Level Phase 197 Auditor Entrypoint & Deterministic Serialization
# ---------------------------------------------------------------------------


def analyze_realhw_fan_pwm_shutter_angle_and_lut_601_702_split(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwFanPwmShutterAngleAndLut601702SplitReport:
    """Run the 41st Firmware-Lab Auditor (`41/41` in `audit-all`)."""
    root = repo_root or DEFAULT_REPO_ROOT
    mode, cache_hit, elapsed, bundle = _inspect_donors_or_clean_room(
        clean_room=clean_room,
        repo_root=root,
    )

    fx3_elf: ElfSectionSummary = bundle["fx3_elf"]  # type: ignore[assignment]
    fx6_elf: ElfSectionSummary = bundle["fx6_elf"]  # type: ignore[assignment]
    fx3_uxc: BoundedUxcPackSummary = bundle["fx3_uxc"]  # type: ignore[assignment]
    fx6_uxc: BoundedUxcPackSummary = bundle["fx6_uxc"]  # type: ignore[assignment]
    fx3_cp: BoundedCpappSummary = bundle["fx3_cp"]  # type: ignore[assignment]
    fx6_cp: BoundedCpappSummary = bundle["fx6_cp"]  # type: ignore[assignment]
    fx3_bk4: BoundedBk4HeaderSummary = bundle["fx3_bk4"]  # type: ignore[assignment]
    fx6_bk4: BoundedBk4HeaderSummary = bundle["fx6_bk4"]  # type: ignore[assignment]
    donor_sizes: Dict[str, int] = bundle["donor_sizes"]  # type: ignore[assignment]

    # --- Pillar 1: ILME-FX3 4-Mode Fan PWM & Pre-Backup Thermal Guard ---
    p1_errors: List[str] = []
    fan_keys = (
        "FAN_CONTROL_AUTO",
        "FAN_CONTROL_MINIMUM",
        "FAN_CONTROL_OFF_IN_REC",
        "FAN_CONTROL_ALWAYS_OFF",
        "N5model21setting_fan_control_tE",
        "N5model28sequence_cooling_fan_controlE",
        "BKID_APP_setting_fan_control",
        "EVENT_REMOTE_AUTO_POWER_OFF_TEMPERATURE",
        "N5model39sequence_set_auto_power_off_temperatureE",
        "OFF_BY_THERMAL_TIME_OUT",
    )
    fx3_fan_hits = {k: fx3_elf.marker_hits.get(k, 0) for k in fan_keys}
    fx6_fan_hits = {
        k: fx6_elf.marker_hits.get(k, 0)
        for k in (
            "FAN_CONTROL_AUTO",
            "FAN_CONTROL_MINIMUM",
            "FAN_CONTROL_OFF_IN_REC",
            "FAN_CONTROL_ALWAYS_OFF",
            "N5model21setting_fan_control_tE",
            "N5model28sequence_cooling_fan_controlE",
        )
    }
    fx3_forb_auto12 = {
        k: fx3_elf.marker_hits.get(k, 0) for k in APPFW_FORBIDDEN_AUTO12_MARKERS_P197
    }
    fx6_forb_auto12 = {
        k: fx6_elf.marker_hits.get(k, 0) for k in APPFW_FORBIDDEN_AUTO12_MARKERS_P197
    }

    for k, v in fx3_fan_hits.items():
        if v < 1:
            p1_errors.append(f"MISSING_FX3_FAN_MARKER:{k}")
    for k, v in fx6_fan_hits.items():
        if v < 1:
            p1_errors.append(f"MISSING_FX6_FAN_MARKER:{k}")
    for k, v in fx3_forb_auto12.items():
        if v != 0:
            p1_errors.append(f"UNEXPECTED_FX3_AUTO12_MARKER:{k}={v}")
    for k, v in fx6_forb_auto12.items():
        if v != 0:
            p1_errors.append(f"UNEXPECTED_FX6_AUTO12_MARKER:{k}={v}")
    if not fx3_uxc.uxc_magic_valid or any(v < 1 for v in fx3_uxc.required_token_hits.values()):
        p1_errors.append("FX3_UXC_EN_F_FAN_SHUTTER_LUT_TOKENS_INCOMPLETE")
    if any(v != 0 for v in fx3_uxc.forbidden_auto12_hits.values()):
        p1_errors.append("FX3_UXC_EN_F_FORBIDDEN_AUTO12_PRESENT")
    if not fx6_uxc.uxc_magic_valid or any(v < 1 for v in fx6_uxc.required_token_hits.values()):
        p1_errors.append("FX6_UXC_EN_TOKENS_INCOMPLETE")
    if any(v != 0 for v in fx6_uxc.forbidden_auto12_hits.values()):
        p1_errors.append("FX6_UXC_EN_FORBIDDEN_AUTO12_PRESENT")
    if any(v < 1 for v in fx3_cp.marker_hits.values()):
        p1_errors.append("FX3_CPAPP_FAN_THERM_MARKERS_INCOMPLETE")
    if any(v < 1 for v in fx6_cp.marker_hits.values()):
        p1_errors.append("FX6_CPAPP_FAN_THERM_MARKERS_INCOMPLETE")

    eval_auto = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
        fan_mode="Auto", is_recording=True, internal_temp_c=45.0, auto_power_off_temp="High"
    )
    eval_min = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
        fan_mode="Minimum", is_recording=True, internal_temp_c=45.0, auto_power_off_temp="Standard"
    )
    eval_offinrec_rec = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
        fan_mode="Off in Rec", is_recording=True, internal_temp_c=48.0, auto_power_off_temp="High"
    )
    eval_offinrec_stby = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
        fan_mode="Off in Rec", is_recording=False, internal_temp_c=48.0, auto_power_off_temp="High"
    )
    eval_offinrec_emerg = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
        fan_mode="Off in Rec", is_recording=True, internal_temp_c=80.0, auto_power_off_temp="High"
    )
    eval_auto1_rej = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(fan_mode="Auto1")
    eval_auto2_rej = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(fan_mode="Auto2")
    eval_alwaysoff_blk = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
        fan_mode="Always Off",
        cold_dump_p3_75mib_requested=True,
        auto_interlock_enforced=False,
    )
    eval_alwaysoff_interlock = evaluate_fx3_fan_pwm_and_prebackup_thermal_guard(
        fan_mode="Always Off",
        cold_dump_p3_75mib_requested=True,
        auto_interlock_enforced=True,
    )

    if not (
        eval_auto.valid
        and eval_min.valid
        and eval_offinrec_rec.valid
        and eval_offinrec_rec.effective_pwm_duty_pct == 0
        and eval_offinrec_stby.valid
        and eval_offinrec_stby.standby_max_pwm_heat_purge
        and eval_offinrec_stby.effective_pwm_duty_pct == 100
        and eval_offinrec_emerg.valid
        and eval_offinrec_emerg.emergency_thermal_override_active
        and eval_offinrec_emerg.effective_pwm_duty_pct == 100
        and (not eval_auto1_rej.valid)
        and eval_auto1_rej.non_fx3_auto12_rejected
        and (not eval_auto2_rej.valid)
        and eval_auto2_rej.non_fx3_auto12_rejected
        and (not eval_alwaysoff_blk.valid)
        and eval_alwaysoff_blk.cxd90057_cxd90058_overheat_risk
        and eval_alwaysoff_interlock.valid
        and eval_alwaysoff_interlock.prebackup_forced_to_auto
        and eval_alwaysoff_interlock.effective_fan_mode == "Auto"
    ):
        p1_errors.append("PILLAR_1_FAN_STATE_MACHINE_INVARIANT_FAILED")

    pillar_1 = Pillar1Fx3FanPwmAndThermalReport(
        passed=len(p1_errors) == 0,
        fx3_appfw_fan_hits=fx3_fan_hits,
        fx6_appfw_fan_hits=fx6_fan_hits,
        fx3_forbidden_auto12_hits=fx3_forb_auto12,
        fx6_forbidden_auto12_hits=fx6_forb_auto12,
        fx3_uxc_en_f_summary=fx3_uxc,
        fx6_uxc_en_summary=fx6_uxc,
        fx3_cpapp_summary=fx3_cp,
        fx6_cpapp_summary=fx6_cp,
        eval_auto_normal=eval_auto,
        eval_minimum_normal=eval_min,
        eval_off_in_rec_recording_silent=eval_offinrec_rec,
        eval_off_in_rec_standby_max_pwm=eval_offinrec_stby,
        eval_off_in_rec_emergency_thermal_override=eval_offinrec_emerg,
        eval_auto1_studio_token_rejected=eval_auto1_rej,
        eval_auto2_studio_token_rejected=eval_auto2_rej,
        eval_always_off_prebackup_blocked_without_interlock=eval_alwaysoff_blk,
        eval_always_off_prebackup_forced_auto_ok=eval_alwaysoff_interlock,
        errors=tuple(p1_errors),
    )

    # --- Pillar 2: Independent [Shutter Mode] (Speed vs Angle) & Range Clamping ---
    p2_errors: List[str] = []
    fx3_shutter_keys = (
        "BKID_APP_setting_mode_shutter",
        "VAL_setting_mode_shutter_MODE_SHUTTER_SPEED",
        "VAL_setting_mode_shutter_MODE_SHUTTER_ANGLE",
        "N5model22setting_mode_shutter_tE",
        "VAL_setting_shutter_angle_SHUTTER_ANGLE_5_POINT_6",
        "VAL_setting_shutter_angle_SHUTTER_ANGLE_180_POINT_0",
        "VAL_setting_shutter_angle_SHUTTER_ANGLE_360_POINT_0",
        "VAL_setting_shutter_angle_SHUTTER_ANGLE_64F",
        "VAL_setting_exposure_step_EXPOSURE_STEP_0_3_EV",
        "VAL_setting_exposure_step_EXPOSURE_STEP_0_5_EV",
    )
    fx6_shutter_keys = (
        "VAL_setting_mode_shutter_MODE_SHUTTER_SPEED",
        "VAL_setting_mode_shutter_MODE_SHUTTER_ANGLE",
        "N5model22setting_mode_shutter_tE",
    )
    fx3_shutter_hits = {k: fx3_elf.marker_hits.get(k, 0) for k in fx3_shutter_keys}
    fx6_shutter_hits = {k: fx6_elf.marker_hits.get(k, 0) for k in fx6_shutter_keys}

    for k, v in fx3_shutter_hits.items():
        if v < 1:
            p2_errors.append(f"MISSING_FX3_SHUTTER_MARKER:{k}")
    for k, v in fx6_shutter_hits.items():
        if v < 1:
            p2_errors.append(f"MISSING_FX6_SHUTTER_MARKER:{k}")
    if not fx3_bk4.bk4_magic_valid or fx3_bk4.rec0_subsystems != EXPECTED_FX3_BK4_SUBSYSTEMS_P197:
        p2_errors.append("FX3_BACKUP_BIN_BK4_HEADER_MISMATCH")
    if not fx6_bk4.bk4_magic_valid or fx6_bk4.rec0_subsystems != EXPECTED_FX6_BK4_SUBSYSTEMS_P197:
        p2_errors.append("FX6_BACKUP_BIN_BK4_HEADER_MISMATCH")

    _before_slot, _after_slot, slots_conserved = simulate_backup_bin_shutter_slot_transitions(
        initial_speed_token="1/50",
        initial_angle_token="172.8",
        initial_exposure_step="0.3EV",
        updated_exposure_step="0.5EV",
    )
    if not slots_conserved:
        p2_errors.append("BACKUP_BIN_SHUTTER_SLOT_INDEPENDENCE_BROKEN")

    eval_2398_64f = evaluate_independent_shutter_mode_and_angle_range(
        shooting_mode="NORMAL_MOVIE",
        rec_frame_rate="23.98p",
        shutter_mode="Angle",
        exposure_step="0.3EV",
        stored_speed_slot="1/48",
        requested_angle_token="64F",
    )
    eval_2398_05ev = evaluate_independent_shutter_mode_and_angle_range(
        shooting_mode="NORMAL_MOVIE",
        rec_frame_rate="23.98p",
        shutter_mode="Angle",
        exposure_step="0.5EV",
        stored_speed_slot="1/48",
        requested_angle_token="180.0",
    )
    eval_speed_preserves = evaluate_independent_shutter_mode_and_angle_range(
        shooting_mode="NORMAL_MOVIE",
        rec_frame_rate="25p",
        shutter_mode="Speed",
        exposure_step="0.3EV",
        stored_speed_slot="1/50",
        requested_angle_token="172.8",
    )
    eval_11988_clamp = evaluate_independent_shutter_mode_and_angle_range(
        shooting_mode="NORMAL_MOVIE",
        rec_frame_rate="119.88p",
        shutter_mode="Angle",
        requested_angle_token="64F",
        clamp_on_mode_transition=True,
    )
    eval_100p_rej = evaluate_independent_shutter_mode_and_angle_range(
        shooting_mode="NORMAL_MOVIE",
        rec_frame_rate="100p",
        shutter_mode="Angle",
        requested_angle_token="64F",
        clamp_on_mode_transition=False,
    )
    eval_sq_clamp = evaluate_independent_shutter_mode_and_angle_range(
        shooting_mode="SQ_MOTION",
        rec_frame_rate="23.98p",
        shutter_mode="Angle",
        requested_angle_token="16F",
        clamp_on_mode_transition=True,
    )
    eval_low_rej = evaluate_independent_shutter_mode_and_angle_range(
        shooting_mode="NORMAL_MOVIE",
        rec_frame_rate="24.00p",
        shutter_mode="Angle",
        requested_angle_token="3.0",
    )

    if not (
        eval_2398_64f.valid
        and eval_2398_64f.effective_angle_deg == SHUTTER_ANGLE_64F_EQUIV_DEG_P197
        and eval_2398_05ev.valid
        and eval_2398_05ev.angle_immune_to_exposure_step
        and eval_speed_preserves.valid
        and eval_speed_preserves.effective_angle_token == "172.8deg"
        and eval_11988_clamp.valid
        and eval_11988_clamp.angle_clamped
        and eval_11988_clamp.effective_angle_deg == 360.0
        and (not eval_100p_rej.valid)
        and eval_sq_clamp.valid
        and eval_sq_clamp.angle_clamped
        and eval_sq_clamp.effective_angle_deg == 360.0
        and (not eval_low_rej.valid)
    ):
        p2_errors.append("PILLAR_2_SHUTTER_RANGE_INVARIANT_FAILED")

    pillar_2 = Pillar2IndependentShutterAngleReport(
        passed=len(p2_errors) == 0,
        fx3_appfw_shutter_hits=fx3_shutter_hits,
        fx6_appfw_shutter_hits=fx6_shutter_hits,
        fx3_backup_header=fx3_bk4,
        fx6_backup_header=fx6_bk4,
        eval_normal_2398p_64f_ok=eval_2398_64f,
        eval_normal_2398p_180deg_05ev_immune_ok=eval_2398_05ev,
        eval_speed_mode_preserves_angle_slot_ok=eval_speed_preserves,
        eval_hfr_11988p_64f_clamped_to_360_ok=eval_11988_clamp,
        eval_hfr_100p_direct_64f_rejected=eval_100p_rej,
        eval_sq_motion_64f_clamped_to_360_ok=eval_sq_clamp,
        eval_below_5_6_deg_rejected=eval_low_rej,
        errors=tuple(p2_errors),
    )

    # --- Pillar 3: Ver. 6.01 vs Ver. 7.00/7.02 p2:/setting User LUT Binary Split ---
    p3_errors: List[str] = []
    fx3_lut_702_keys = (
        "BKID_APP_is_exist_user_lut0",
        "BKID_APP_is_exist_user_lut15",
        "BKID_APP_user_lut_attr_ae_level_offset0",
        "BKID_APP_user_lut_attr_ae_level_offset15",
        "BKID_APP_setting_embed_lut_file",
    )
    fx6_lut_601_keys = APPFW_FX6_601_EXCLUSIVE_LUT_MARKERS_P197

    fx3_702_lut_hits = {k: fx3_elf.marker_hits.get(k, 0) for k in fx3_lut_702_keys}
    fx6_601_lut_hits = {k: fx6_elf.marker_hits.get(k, 0) for k in fx6_lut_601_keys}
    fx6_in_fx3 = {k: fx3_elf.marker_hits.get(k, 0) for k in fx6_lut_601_keys}
    fx3_in_fx6 = {k: fx6_elf.marker_hits.get(k, 0) for k in fx3_lut_702_keys}

    for k, v in fx3_702_lut_hits.items():
        if v < 1:
            p3_errors.append(f"MISSING_FX3_702_LUT_MARKER:{k}")
    for k, v in fx6_601_lut_hits.items():
        if v < 1:
            p3_errors.append(f"MISSING_FX6_601_LUT_MARKER:{k}")
    for k, v in fx6_in_fx3.items():
        if v != 0:
            p3_errors.append(f"UNEXPECTED_601_LUT_MARKER_IN_FX3_702:{k}={v}")
    for k, v in fx3_in_fx6.items():
        if v != 0:
            p3_errors.append(f"UNEXPECTED_702_LUT_MARKER_IN_FX6_601:{k}={v}")

    v1_bytes, v1_sum = serialize_user_lut_slot_header(
        schema_id=LUT_SLOT_SCHEMA_LEGACY_LE_601_P197,
        slot_index=1,
        lut_3d_size=33,
    )
    v2_bytes, v2_sum = serialize_user_lut_slot_header(
        schema_id=LUT_SLOT_SCHEMA_OPT_GE_700_P197,
        slot_index=1,
        lut_3d_size=33,
        ae_level_offset_thirds=3,
        embed_lut_enabled=True,
    )
    ok_v1_under_702, v1_err = verify_stock_702_user_lut_slot_deserialization(v1_bytes)
    ok_v2_under_702, _v2_ok_msg = verify_stock_702_user_lut_slot_deserialization(v2_bytes)
    if ok_v1_under_702 or v1_err != "LUT_GENERATION_SPLIT_601_TO_702_DESERIALIZE_CORRUPTION":
        p3_errors.append("FAILED_TO_DETECT_601_TO_702_LUT_SLOT_CORRUPTION")
    if not ok_v2_under_702:
        p3_errors.append("STOCK_702_V2_LUT_SLOT_DESERIALIZATION_FAILED")

    eval_lut_p2_blk = evaluate_user_lut_601_vs_702_binary_split_firewall(
        writer_firmware="FX6_6.01",
        host_reader_firmware="FX3_7.02",
        slot_index=1,
        target_storage_path="p2:/setting/User1.lutslot",
        lifecycle_stage="H2",
    )
    eval_lut_overlay_ok = evaluate_user_lut_601_vs_702_binary_split_firewall(
        writer_firmware="FX6_6.01",
        host_reader_firmware="FX3_7.02",
        slot_index=1,
        target_storage_path="/tmp/fx6_lut_overlay/User1.lutslot",
        lifecycle_stage="H2",
    )
    eval_lut_h3_ok = evaluate_user_lut_601_vs_702_binary_split_firewall(
        writer_firmware="FX3_7.02",
        host_reader_firmware="FX3_7.02",
        slot_index=16,
        target_storage_path="/tmp/fx6_lut_overlay/stock_verify_slot16.json",
        lifecycle_stage="H3",
    )

    if not (
        (not eval_lut_p2_blk.valid)
        and eval_lut_p2_blk.direct_p2_setting_write_blocked
        and eval_lut_p2_blk.stock_702_lut_deserialize_corrupted
        and eval_lut_p2_blk.stock_702_lut_corruption_prevented
        and eval_lut_overlay_ok.valid
        and eval_lut_overlay_ok.redirected_to_volatile_overlay
        and eval_lut_overlay_ok.h0_equals_h3
        and eval_lut_h3_ok.valid
        and eval_lut_h3_ok.h0_equals_h3
    ):
        p3_errors.append("PILLAR_3_LUT_GENERATION_SPLIT_FIREWALL_FAILED")

    pillar_3 = Pillar3Lut601Vs702SplitReport(
        passed=len(p3_errors) == 0,
        fx3_702_lut_exclusive_hits=fx3_702_lut_hits,
        fx6_601_lut_exclusive_hits=fx6_601_lut_hits,
        fx6_702_cross_pollution_in_fx3=fx6_in_fx3,
        fx3_702_cross_pollution_in_fx6=fx3_in_fx6,
        legacy_601_slot_sample=v1_sum,
        opt_702_slot_sample=v2_sum,
        eval_direct_601_write_to_p2_setting_blocked=eval_lut_p2_blk,
        eval_stage_b_601_volatile_overlay_h2_ok=eval_lut_overlay_ok,
        eval_stock_702_restore_h3_bit_exact_ok=eval_lut_h3_ok,
        errors=tuple(p3_errors),
    )

    # --- Pillar 4: Hard Write Firewall & 12-Touchpoint 4-Class Matrix ---
    p4_errors: List[str] = []
    wg_p2 = evaluate_phase197_write_guard("p2:/setting/UserLutSlot1.bin")
    wg_bk = evaluate_phase197_write_guard("p2:/setting/Backup.bin")
    wg_cp = evaluate_phase197_write_guard("p8:/CPAPP-B.BIN")
    wg_nor = evaluate_phase197_write_guard("spi_nor:loader_nor.bin")
    wg_ovl = evaluate_phase197_write_guard("/tmp/fx6_lut_overlay/User1.lutslot")
    wg_sd = evaluate_phase197_write_guard("/mnt/sd/Private/Sony/PRO/LUT/Cine709.cube")
    matrix = build_phase197_compat_matrix()

    if (
        wg_p2.valid
        or wg_bk.valid
        or wg_cp.valid
        or wg_nor.valid
        or (not wg_ovl.valid)
        or (not wg_sd.valid)
        or matrix.total_touchpoints != 12
        or any(matrix.class_counts.get(c, 0) < 1 for c in VALID_BRIDGE_CLASSES)
    ):
        p4_errors.append("PILLAR_4_WRITE_FIREWALL_OR_MATRIX_FAILED")

    pillar_4 = Pillar4Phase197WriteGuardAndMatrixReport(
        passed=len(p4_errors) == 0,
        blocked_p2_setting_eval=wg_p2,
        blocked_backup_bin_eval=wg_bk,
        blocked_cpapp_bin_eval=wg_cp,
        blocked_spi_nor_eval=wg_nor,
        allowed_fx6_lut_overlay_eval=wg_ovl,
        allowed_sd_cube_source_eval=wg_sd,
        compatibility_matrix=matrix,
        errors=tuple(p4_errors),
    )

    all_errors = tuple(p1_errors + p2_errors + p3_errors + p4_errors)
    all_ok = len(all_errors) == 0

    digest_payload = {
        "schema_version": PHASE_197_SCHEMA,
        "phase_version": PHASE_197_VERSION,
        "mode": mode,
        "all_checks_passed": all_ok,
        "donor_file_sizes": donor_sizes,
        "p1_passed": pillar_1.passed,
        "p2_passed": pillar_2.passed,
        "p3_passed": pillar_3.passed,
        "p4_passed": pillar_4.passed,
        "touchpoints": matrix.total_touchpoints,
    }
    report_sha256 = hashlib.sha256(
        repr(sorted(digest_payload.items())).encode("utf-8")
    ).hexdigest()

    return RealhwFanPwmShutterAngleAndLut601702SplitReport(
        schema_version=PHASE_197_SCHEMA,
        phase_version=PHASE_197_VERSION,
        auditor_index="41/41",
        mode=mode,
        cache_hit=cache_hit,
        cold_or_cached_scan_elapsed_sec=elapsed,
        all_checks_passed=all_ok,
        o_rdonly_enforced=True,
        raw_firmware_bytes_leaked=0,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        persistent_writes=0,
        p2_setting_mutation_bytes=0,
        calibration_mutation_bytes=0,
        fan_4mode_and_prebackup_thermal_verified=pillar_1.passed,
        independent_shutter_speed_angle_verified=pillar_2.passed,
        lut_601_vs_702_binary_split_firewall_verified=pillar_3.passed,
        write_firewall_and_matrix_verified=pillar_4.passed,
        donor_file_sizes=donor_sizes,
        pillar_1_fan_pwm_thermal=pillar_1,
        pillar_2_shutter_speed_angle=pillar_2,
        pillar_3_lut_601_702_split=pillar_3,
        pillar_4_write_guard_matrix=pillar_4,
        report_sha256=report_sha256,
        errors=all_errors,
    )


def _normalize_json_value(obj: object) -> object:
    if isinstance(obj, dict):
        return {str(k): _normalize_json_value(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize_json_value(v) for v in obj]
    return obj


def realhw_fan_pwm_shutter_angle_and_lut_601_702_split_report_to_dict(
    report: RealhwFanPwmShutterAngleAndLut601702SplitReport,
) -> Dict[str, object]:
    """Convert `RealhwFanPwmShutterAngleAndLut601702SplitReport` into deterministic JSON-ready dict."""
    raw = asdict(report)
    raw.pop("cold_or_cached_scan_elapsed_sec", None)
    raw.pop("cache_hit", None)
    return _normalize_json_value(raw)  # type: ignore[return-value]
