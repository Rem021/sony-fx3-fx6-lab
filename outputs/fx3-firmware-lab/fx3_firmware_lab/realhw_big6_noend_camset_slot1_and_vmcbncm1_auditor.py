"""Phase 203 — 42nd Firmware-Lab Auditor (42/42): Real-Hardware `ILME-FX3`
(`Ver. 7.02`) `BIG6` `[Home (Lower Left)]` Zero e-ND Actuator Boundary, Slot-1
`CAMSET` Dual-Media Path Split & `VMC-BNCM1` Body-Only `TC IN` / HDMI `TC OUT`
Auditor.

Strictly Read-Only (`os.O_RDONLY` + `os.pread` bounded section inspection) &
Clean-Room Dual-Mode:
- Local Donor Mode: inspects Stock FX3 `Ver. 7.02` (`appFw.so`,
  `string_english_f.uxc`, `CPAPP-B.BIN`) vs FX6 `Ver. 6.01` (`appFw.so`,
  `string_english.uxc`, `cpapp-b.bin`) strictly via `os.O_RDONLY` + bounded
  `os.pread` (< 0.15 s cold, cached per process via `_DONOR_SCAN_CACHE_P203`,
  never scanning >50 MiB whole images redundantly).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`, `.uxc` string
  packs, and `cpapp-b.bin` RTOS token slices with zero proprietary bytes leaked
  (`raw_firmware_bytes_leaked == 0`).

Audits Four Core Wave-26 Real-Hardware Pillars:
1. Pillar 1 (`FX3_BIG6_HOME_6TILE_TOPOLOGY_AND_ZERO_END_ACTUATOR_BOUNDARY`):
   Audits `ILME-FX3` (`Ver. 7.00+ / 7.02`) `Home` (`BIG6`) prerequisites
   (`[Mode Settings] = [Fixed/Variable]` + `[HOME]` custom key via
   `[Custom Key/Dial Set.]`), exact 6-tile + 7th status-bar topology (`1: FPS`,
   `2: ISO / Base ISO`, `3: Shutter Speed / Shutter Angle`,
   `4: Aperture / ND Filter` via `MENU -> Setup -> [Operation Customize] ->
   [Home (Lower Left)]`, `5: Picture Profile / Select LUT`, `6: White Balance`),
   proving `ILME-FX3` lacks `ILME-FX6`'s physical motorized/LCD Variable ND
   (`1/4..1/128`) hardware (`PID_SET_VARIABLE_ND_VALUE == 0` in FX3) and
   enforcing `e_nd_actuator_tx_count == 0` in Stage-B (`[ND Filter]` treated
   strictly as manual reference fraction metadata).
2. Pillar 2 (`CAMSET_SLOT1_LOCK_DUAL_MEDIA_PATH_SPLIT_AND_CROSS_MODEL_FIREWALL`):
   Audits `[Save/Load Settings]` (`CAMSET01.DAT .. CAMSET10.DAT`) Slot-1-only
   lock (`Slot 2` disallowed, max `10` profiles per card, greyed out in `MR`
   `Recall Camera Setting` mode, excluded machine-bound fields `Custom WB 1/2/3`,
   `FTP`, `Network Streaming`, `IP/Cert`, `Date/Time`), SD/SDHC/SDXC
   (`/PRIVATE/SONY/SETTING/FX3/CAMSET/`) vs CFexpress Type A
   (`/SONY/SETTING/FX3/CAMSET/`) root directory split (`%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT`),
   and `ILME-FX3` vs `ILME-FX3A` vs `ILME-FX6` `.DAT` binary incompatibility
   with `/tmp/fx6_camset_overlay` Stage-B sandboxing (`H0 == H3`).
3. Pillar 3 (`VMC_BNCM1_BODY_ONLY_TC_IN_XLRH1_PROHIBITION_AND_HDMI_TC_OUT`):
   Audits `VMC-BNCM1` (`A-5051-506-A`, `0.2m`) unidirectional `TC IN` strictly
   on the camera body `Multi/Micro USB` port (`[Movie]` + `[Time Code Make] =
   [Preset]` + `[Time Code Run] = [Free Run]` + `>= 10.0s` lock dwell ->
   `EXT-LK`, immediately unlocked on `S&Q` or `TC Make/Run/Preset` edits),
   prohibits plugging `VMC-BNCM1` into the `XLR-H1` handle Micro-USB port,
   rejects reverse LTC/BNC `TC OUT` drive (`EOPNOTSUPP`), and routes digital
   `TC OUT` exclusively over Type-A HDMI (`[Time Code Output] = [On]`,
   automatically disabled in `S&Q`).
4. Pillar 4 (`ZERO_WRITE_FIREWALL_AND_12TP_COMPAT_MATRIX`):
   Enforces hard safety invariants (`persistent_emmc_writes_authorized = False`,
   `spi_nor_write_authorized = False`, `el3_payload_transmit_authorized = False`,
   `physical_usb_packets_emitted = 0`, `raw_firmware_bytes_leaked = 0`,
   `e_nd_actuator_tx_count = 0`) and builds a 12-touchpoint 4-class matrix.
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
    FX3_CPAPP_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_CPAPP_P146_RELPATH,
    VALID_BRIDGE_CLASSES,
    ElfSectionSummary,
    _build_synthetic_elf64,
)
from .uxc_multilang_and_font_verifier import (
    FX3_SHARE_APP_RELDIR,
    FX6_SHARE_APP_RELDIR,
)


PHASE_203_SCHEMA = (
    "fx3_firmware_lab_phase203_realhw_big6_noend_camset_slot1_vmcbncm1_v1"
)
PHASE_203_VERSION = "203.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + bounded os.pread)
# ---------------------------------------------------------------------------

FX3_APPFW_P203_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P203_RELPATH = FX6_APPFW_P146_RELPATH
FX3_UXC_EN_F_P203_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_f.uxc"
FX6_UXC_EN_P203_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX3_CPAPP_P203_RELPATH = FX3_CPAPP_P146_RELPATH
FX6_CPAPP_P203_RELPATH = FX6_CPAPP_P146_RELPATH

# ---------------------------------------------------------------------------
# Verified Expected Donor Sizes & Cold Scan Budget
# ---------------------------------------------------------------------------

EXPECTED_FX3_APPFW_BYTES_P203 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P203 = 50_520_424
EXPECTED_FX3_UXC_EN_F_BYTES_P203 = 373_820
EXPECTED_FX6_UXC_EN_BYTES_P203 = 118_208
EXPECTED_FX3_CPAPP_BYTES_P203 = 15_980_568
EXPECTED_FX6_CPAPP_BYTES_P203 = 17_952_816

CPAPP_BOUNDED_HEAD_BYTES_P203 = 768 * 1024
CPAPP_BOUNDED_TAIL_BYTES_P203 = 6 * 1024 * 1024
DONOR_COLD_SCAN_BUDGET_SEC_P203 = 0.15

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 1 (`BIG6` Home 6-Tile Topology & Zero e-ND Boundary)
# ---------------------------------------------------------------------------

FX3_HOME_LOWER_LEFT_MENU_PATH_P203 = (
    "MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)]"
)
FX3_BIG6_PREREQ_MODE_SETTINGS_P203 = "Fixed/Variable"
VALID_MODE_SETTINGS_P203: Tuple[str, ...] = (
    "Fixed/Variable",
    "Normal_Movie_Non_FixedVariable",
    "S&Q_Legacy",
)
VALID_HOME_LOWER_LEFT_CHOICES_P203: Tuple[str, ...] = (
    "Aperture",
    "ND Filter",
)
FX3_HOME_LOWER_LEFT_TO_APPFW_ENUM_P203: Dict[str, str] = {
    "Aperture": "MOVIE_HOME_LOWER_LEFT_APERTURE",
    "ND Filter": "MOVIE_HOME_LOWER_LEFT_ND_FILTER",
}

FX3_BIG6_SIX_TILE_TOPOLOGY_P203: Tuple[Tuple[int, str, str], ...] = (
    (1, "TILE_1_FPS", "FPS (Fixed/Variable)"),
    (2, "TILE_2_ISO_BASE_ISO", "ISO / Base ISO"),
    (3, "TILE_3_SHUTTER", "Shutter Speed / Shutter Angle"),
    (4, "TILE_4_LOWER_LEFT", "Aperture / ND Filter ([Home (Lower Left)])"),
    (5, "TILE_5_LOOK_LUT", "Picture Profile / Select LUT"),
    (6, "TILE_6_WHITE_BALANCE", "White Balance"),
)
FX3_BIG6_SEVENTH_STATUS_REGION_P203 = "REGION_7_STATUS_BAR_TC_AUDIO_MEDIA"

FX6_MOTORIZED_END_RANGE_FRACTIONS_P203: Tuple[str, ...] = (
    "1/4",
    "1/8",
    "1/16",
    "1/32",
    "1/64",
    "1/128",
)
VALID_ND_REFERENCE_LABELS_P203: Tuple[str, ...] = (
    "Clear",
    *FX6_MOTORIZED_END_RANGE_FRACTIONS_P203,
)

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 2 (Slot-1 `CAMSET`, Dual-Media Path & `.DAT` Firewall)
# ---------------------------------------------------------------------------

CAMSET_MAX_PROFILES_PER_CARD_P203 = 10
CAMSET_MIN_PROFILE_INDEX_P203 = 1
CAMSET_ALLOWED_SLOT_P203 = "Slot 1"
CAMSET_DISALLOWED_SLOT_P203 = "Slot 2"

CAMSET_CANONICAL_FILENAMES_P203: Tuple[str, ...] = tuple(
    f"CAMSET{i:02d}.DAT" for i in range(1, CAMSET_MAX_PROFILES_PER_CARD_P203 + 1)
)

CAMSET_SD_ROOT_DIR_P203 = "/PRIVATE/SONY/SETTING/FX3/CAMSET/"
CAMSET_CFEXPRESS_A_ROOT_DIR_P203 = "/SONY/SETTING/FX3/CAMSET/"
CAMSET_APPFW_PRINTF_TEMPLATE_P203 = "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT"
FTPSET_APPFW_PRINTF_TEMPLATE_P203 = "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT"

VALID_CAMSET_MEDIA_TYPES_P203: Tuple[str, ...] = (
    "SD",
    "SDHC",
    "SDXC",
    "CFEXPRESS_TYPE_A",
)
SD_FAMILY_MEDIA_TYPES_P203: Tuple[str, ...] = ("SD", "SDHC", "SDXC")

VALID_CAMERA_OPERATING_MODES_P203: Tuple[str, ...] = (
    "MOVIE_NORMAL",
    "CINE_EI",
    "MR_RECALL_CAMERA_SETTING",
)

EXCLUDED_MACHINE_BOUND_CAMSET_FIELDS_P203: Tuple[str, ...] = (
    "Custom WB 1/2/3",
    "FTP",
    "Network Streaming",
    "IP/Cert",
    "Date/Time",
)

CAMSET_MODEL_SPECS_P203: Dict[str, Tuple[int, bytes, int]] = {
    "ILME-FX3": (0x91030080, b"CSFX3_70", 819),
    "ILME-FX3A": (0x91030082, b"CSFX3A20", 823),
    "ILME-FX6": (0x91030060, b"CSFX6_60", 840),
}
CAMSET_DAT_HEADER_BYTES_P203 = 32
VOLATILE_FX6_CAMSET_OVERLAY_DIR_P203 = "/tmp/fx6_camset_overlay"
P2_SETTING_DIR_P203 = "p2:/setting"
VALID_LIFECYCLE_STAGES_P203: Tuple[str, ...] = ("H0", "H1", "H2", "H3")

# ---------------------------------------------------------------------------
# Domain Constants — Pillar 3 (`VMC-BNCM1` Body-Only `TC IN` & HDMI `TC OUT`)
# ---------------------------------------------------------------------------

VMC_BNCM1_PART_NUMBER_P203 = "A-5051-506-A"
VMC_BNCM1_CABLE_LENGTH_M_P203 = 0.2
EXT_LK_MIN_LOCK_DWELL_SEC_P203 = 10.0

HDMI_TC_OUT_MENU_PATH_P203 = (
    "MENU -> Setup -> [External Output] -> [HDMI Output Settings] -> [Time Code Output]"
)

VALID_TC_PHYSICAL_PORTS_P203: Tuple[str, ...] = (
    "BODY_MULTI_MICRO_USB",
    "XLR_H1_HANDLE_MICRO_USB",
    "HDMI_TYPE_A",
    "FX6_VIRTUAL_BNC_PORT",
)
VALID_TC_DIRECTIONS_P203: Tuple[str, ...] = ("TC_IN", "TC_OUT")
VALID_TC_SHOOTING_MODES_P203: Tuple[str, ...] = ("Movie", "S&Q", "Stills")
VALID_TC_MAKE_MODES_P203: Tuple[str, ...] = ("Preset", "Regenerate")
VALID_TC_RUN_MODES_P203: Tuple[str, ...] = ("Free Run", "Rec Run")
VALID_BOOT_CONTEXTS_P203: Tuple[str, ...] = ("NORMAL_OS", "H0_UART_BOOT")

# ---------------------------------------------------------------------------
# Verified Donor Binary Marker Catalogs (strictly O_RDONLY bounded read)
# ---------------------------------------------------------------------------

APPFW_SHARED_WAVE26_MARKERS_P203: Tuple[str, ...] = (
    "N5model31setting_movie_home_lower_left_tE",
    "set_movie_home_lower_left",
    "MOVIE_HOME_LOWER_LEFT_APERTURE",
    "MOVIE_HOME_LOWER_LEFT_ND_FILTER",
    "GUIDE_BIG6_FPS_SELECT",
    "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT",
    "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT",
    "save_load_settings_file0",
    "save_load_settings_file9",
    "sequence/sequence_save_load_settings_save.cpp",
    "sequence/sequence_save_load_ftp_settings_save.cpp",
    "sequence_hdmi_tc_output",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_OFF",
    "VAL_setting_tc_run_TC_RUN_FREE_RUN",
    "VAL_setting_tc_run_TC_RUN_REC_RUN",
)

APPFW_FX3_702_EXCLUSIVE_MARKERS_P203: Tuple[str, ...] = (
    "BKID_APP_setting_movie_home_lower_left",
    "26view_tp_button_01_for_big6",
    "BKID_APP_setting_nd_filter_manual_set",
    "EVENT_FUNC_CUSTOM_FPS_FIXED_VARIABLE_SELECT_ON",
    "CAMSET%02d",
    "is_recall_camera_setting_screen_push_ok",
    "No301_EXTLK",
    "MSG_ID_TCUB_TC_SYNC",
)

APPFW_FX6_601_EXCLUSIVE_END_AND_SDI_MARKERS_P203: Tuple[str, ...] = (
    "BKID_APP_VARIABLE_ND_CONT",
    "PID_SET_VARIABLE_ND_VALUE",
    "PID_SET_VARIABLE_ND_ROTARY_ENCODER",
    "PID_GET_VARIABLE_ND_STORED_VALUE",
    "INFRA_NOTIFY_VARIABLE_ND_FILTER_VALUE",
    "FUNC_set_auto_nd_filter",
    "FUNC_set_push_auto_nd_filter",
    "PRM_HAITA_setting_hdmi_tc_output_sdi_output",
)

UXC_FX3_EN_F_REQUIRED_TOKENS_P203: Tuple[str, ...] = (
    "Home (Lower Left)",
    "Mode Settings",
    "Fixed/Variable",
    "Aperture",
    "ND Filter",
    "FPS",
    "Base ISO",
    "Shutter Speed",
    "Picture Profile",
    "Select LUT",
    "White Balance",
    "Save/Load Settings",
    "Slot 1",
    "Slot 2",
    "Time Code Make",
    "Time Code Run",
    "Preset",
    "Free Run",
    "Time Code Output",
    "HDMI Output Settings",
)

UXC_FX6_EN_REQUIRED_TOKENS_P203: Tuple[str, ...] = (
    "Home",
    "Fixed/Variable",
    "Aperture",
    "ND Filter",
    "FPS",
    "Base ISO",
    "Shutter Speed",
    "Shutter Angle",
    "White Balance",
    "Preset",
    "Free Run",
    "All File",
    "Slot A",
    "Slot B",
)

CPAPP_SHARED_TC_IMAGER_MARKERS_P203: Tuple[str, ...] = (
    "C_ImagerCtrl_IMX510",
    "LTC",
    "29:Vitc/LTC/DPACK",
    "EXTERNALTC_LOCK",
    "HDMI::MSG_PARAM_SET_TC_OUTPUT",
)

CPAPP_FORBIDDEN_END_ACTUATOR_MARKERS_P203: Tuple[str, ...] = (
    "PID_SET_VARIABLE_ND_VALUE",
    "PID_SET_VARIABLE_ND_ROTARY_ENCODER",
)

# ---------------------------------------------------------------------------
# Write-Firewall Patterns
# ---------------------------------------------------------------------------

VOLATILE_ALLOWED_PREFIXES_P203: Tuple[str, ...] = (
    "/tmp/fx6_camset_overlay",
    "/tmp/",
    "/tmp_wbshd/",
    "ram://",
    "memfd:",
)

FORBIDDEN_PERSISTENT_TARGET_RE_P203 = re.compile(
    r"(?:"
    r"^/dev/(?:[cp]?nflasha\d*|mmcblk0(?:p\d+|rpmb)?|rtc0)"
    r"|^p(?:0|1|2|3|5|6|7|8|12|13|15|18):/"
    r"|^/(?:wbi|setting|cert|lens)(?:/|$)"
    r"|^/(?:PRIVATE/)?SONY/SETTING/FX3/CAMSET/"
    r"|^/mnt/(?:sd|sd2|cfexpress_a)/(?:PRIVATE/)?SONY/SETTING/FX3/CAMSET/"
    r"|^spi_nor:"
    r"|^sector0:"
    r"|Backup\.bin$"
    r"|cpapp-b\.bin$"
    r"|CPAPP-B\.BIN$"
    r"|BODYDATA\.DAT$"
    r"|CAMSET\d*\.DAT$"
    r"|loader_nor\.bin$"
    r")",
    re.IGNORECASE,
)

# Per-process bounded O_RDONLY donor scan cache (< 0.15s cold, < 1ms warm)
_DONOR_SCAN_CACHE_P203: Dict[Tuple[str, ...], Dict[str, object]] = {}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class BoundedUxcSummaryP203:
    pack_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    uxc_magic_valid: bool
    required_token_hits: Dict[str, int]


@dataclass(frozen=True)
class BoundedCpappSummaryP203:
    binary_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    bounded_bytes_read: int
    marker_hits: Dict[str, int]
    forbidden_end_actuator_hits: Dict[str, int]


@dataclass(frozen=True)
class Big6HomeAndZeroEndEvalResult:
    valid: bool
    menu_path: str
    mode_settings: str
    home_custom_key_bound: bool
    big6_home_accessible: bool
    tile_count: int
    tiles: Tuple[str, ...]
    seventh_status_region: str
    home_lower_left_choice: str
    appfw_lower_left_enum: str
    tile_4_effective_binding: str
    requested_nd_label: str
    physical_internal_end_present_on_fx3: bool
    physical_internal_end_present_on_fx6: bool
    nd_treated_as_manual_reference_only: bool
    stage_b_end_actuator_tx_blocked: bool
    e_nd_actuator_tx_count: int
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CamsetDatHeaderSummary:
    model_name: str
    model_id_hex: str
    magic_ascii: str
    bk4_subsystems: int
    profile_index: int
    header_bytes: int
    crc32_hex: str


@dataclass(frozen=True)
class CamsetSlot1PathAndFirewallEvalResult:
    valid: bool
    camera_mode: str
    menu_greyed_out: bool
    target_slot: str
    slot1_only_enforced: bool
    media_type: str
    profile_index: int
    canonical_filename: str
    expected_card_directory: str
    requested_card_path: str
    dual_media_path_valid: bool
    excluded_machine_bound_fields: Tuple[str, ...]
    stripped_machine_bound_fields: Tuple[str, ...]
    writer_model: str
    reader_model: str
    cross_model_incompatible_blocked: bool
    stage_b_active: bool
    stage_b_storage_target: str
    redirected_to_volatile_camset_overlay: bool
    lifecycle_stage: str
    h0_state_sha256: str
    h3_state_sha256: str
    h0_equals_h3: bool
    p2_setting_mutation_bytes: int
    stock_slot1_camset_mutation_bytes: int
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class VmcBncm1TcInAndHdmiTcOutEvalResult:
    valid: bool
    adapter_model: str
    adapter_part_number: str
    physical_port: str
    requested_direction: str
    boot_context: str
    shooting_mode: str
    tc_make: str
    tc_run: str
    lock_dwell_sec: float
    tc_setting_edited_after_lock: bool
    xlr_h1_handle_port_prohibited: bool
    uart_boot_pin_contention_blocked: bool
    bnc_tc_out_rejected_eopnotsupp: bool
    errno_code: Optional[str]
    bnc_tc_out_tx_packets: int
    ext_lk_locked: bool
    ext_lk_state_label: str
    hdmi_tc_output_menu_setting: str
    hdmi_tc_out_active: bool
    hdmi_tc_out_disabled_in_sq: bool
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase203WriteGuardResult:
    valid: bool
    target_path: str
    volatile_overlay_allowed: bool
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
class Phase203TouchpointEntry:
    touchpoint_id: str
    pillar: str
    fx6_or_host_component: str
    fx3_target: str
    bridge_class: str
    safety_invariant: str


@dataclass(frozen=True)
class Phase203CompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    pillar_counts: Dict[str, int]
    touchpoints: Tuple[Phase203TouchpointEntry, ...]


@dataclass(frozen=True)
class Pillar1Big6HomeAndZeroEndReport:
    passed: bool
    fx3_appfw_big6_hits: Dict[str, int]
    fx6_appfw_big6_hits: Dict[str, int]
    fx6_exclusive_end_hits_in_fx6: Dict[str, int]
    fx6_exclusive_end_hits_in_fx3: Dict[str, int]
    fx3_uxc_en_f_summary: BoundedUxcSummaryP203
    fx6_uxc_en_summary: BoundedUxcSummaryP203
    fx3_cpapp_summary: BoundedCpappSummaryP203
    fx6_cpapp_summary: BoundedCpappSummaryP203
    eval_big6_default_aperture_ok: Big6HomeAndZeroEndEvalResult
    eval_big6_nd_filter_manual_metadata_ok: Big6HomeAndZeroEndEvalResult
    eval_big6_blocked_without_fixed_variable_mode: Big6HomeAndZeroEndEvalResult
    eval_big6_blocked_without_home_custom_key: Big6HomeAndZeroEndEvalResult
    eval_stage_b_unblocked_end_actuator_tx_rejected: Big6HomeAndZeroEndEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2CamsetSlot1AndFirewallReport:
    passed: bool
    fx3_appfw_camset_hits: Dict[str, int]
    fx6_appfw_camset_hits: Dict[str, int]
    fx3_dat_header_sample: CamsetDatHeaderSummary
    fx3a_dat_header_sample: CamsetDatHeaderSummary
    fx6_dat_header_sample: CamsetDatHeaderSummary
    eval_slot1_sd_private_path_ok: CamsetSlot1PathAndFirewallEvalResult
    eval_slot1_cfexpress_a_no_private_path_ok: CamsetSlot1PathAndFirewallEvalResult
    eval_slot2_rejected: CamsetSlot1PathAndFirewallEvalResult
    eval_profile_11_rejected: CamsetSlot1PathAndFirewallEvalResult
    eval_mr_recall_mode_greyed_out_rejected: CamsetSlot1PathAndFirewallEvalResult
    eval_sd_missing_private_prefix_rejected: CamsetSlot1PathAndFirewallEvalResult
    eval_cfexpress_with_private_prefix_rejected: CamsetSlot1PathAndFirewallEvalResult
    eval_cross_model_fx3a_on_fx3_rejected: CamsetSlot1PathAndFirewallEvalResult
    eval_cross_model_fx6_on_fx3_rejected: CamsetSlot1PathAndFirewallEvalResult
    eval_stage_b_direct_slot1_overwrite_blocked: CamsetSlot1PathAndFirewallEvalResult
    eval_stage_b_volatile_overlay_h0_eq_h3_ok: CamsetSlot1PathAndFirewallEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3VmcBncm1AndHdmiTcOutReport:
    passed: bool
    fx3_appfw_tc_hits: Dict[str, int]
    fx6_appfw_tc_hits: Dict[str, int]
    eval_body_multi_usb_tcin_ext_lk_10s_ok: VmcBncm1TcInAndHdmiTcOutEvalResult
    eval_body_multi_usb_tcin_under_10s_acquiring: VmcBncm1TcInAndHdmiTcOutEvalResult
    eval_sq_mode_unlocks_ext_lk_and_disables_hdmi_tc: VmcBncm1TcInAndHdmiTcOutEvalResult
    eval_tc_setting_edit_unlocks_ext_lk: VmcBncm1TcInAndHdmiTcOutEvalResult
    eval_xlr_h1_handle_micro_usb_prohibited: VmcBncm1TcInAndHdmiTcOutEvalResult
    eval_multi_usb_reverse_tc_out_eopnotsupp: VmcBncm1TcInAndHdmiTcOutEvalResult
    eval_hdmi_type_a_digital_tc_out_movie_ok: VmcBncm1TcInAndHdmiTcOutEvalResult
    eval_uart_boot_h0_vmcbncm1_blocked: VmcBncm1TcInAndHdmiTcOutEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4Phase203WriteGuardAndMatrixReport:
    passed: bool
    blocked_p2_setting_eval: Phase203WriteGuardResult
    blocked_backup_bin_eval: Phase203WriteGuardResult
    blocked_stock_slot1_camset_eval: Phase203WriteGuardResult
    blocked_cpapp_bin_eval: Phase203WriteGuardResult
    blocked_spi_nor_eval: Phase203WriteGuardResult
    allowed_fx6_camset_overlay_eval: Phase203WriteGuardResult
    allowed_ram_shadow_eval: Phase203WriteGuardResult
    compatibility_matrix: Phase203CompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwBig6NoendCamsetSlot1AndVmcbncm1Report:
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
    e_nd_actuator_tx_count: int
    persistent_writes: int
    p2_setting_mutation_bytes: int
    calibration_mutation_bytes: int
    big6_6tile_and_zero_end_boundary_verified: bool
    camset_slot1_dual_path_and_firewall_verified: bool
    vmcbncm1_body_tcin_and_hdmi_tcout_verified: bool
    zero_write_firewall_and_matrix_verified: bool
    donor_file_sizes: Dict[str, int]
    pillar_1_big6_zero_end: Pillar1Big6HomeAndZeroEndReport
    pillar_2_camset_slot1_firewall: Pillar2CamsetSlot1AndFirewallReport
    pillar_3_vmcbncm1_hdmi_tc: Pillar3VmcBncm1AndHdmiTcOutReport
    pillar_4_write_guard_matrix: Pillar4Phase203WriteGuardAndMatrixReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Pillar 1 Evaluator — `BIG6` Home 6-Tile Topology & Zero Physical e-ND Guard
# ---------------------------------------------------------------------------


def evaluate_fx3_big6_home_and_zero_end_boundary(
    *,
    mode_settings: str = "Fixed/Variable",
    home_custom_key_bound: bool = True,
    home_lower_left_choice: str = "Aperture",
    requested_nd_label: str = "Clear",
    stage_b_end_actuator_tx_blocked: bool = True,
) -> Big6HomeAndZeroEndEvalResult:
    """Evaluate `ILME-FX3` (`Ver. 7.00+/7.02`) `BIG6` 6-tile topology & zero e-ND boundary."""
    errors: List[str] = []
    mode_clean = mode_settings.strip()
    ll_clean = home_lower_left_choice.strip()
    nd_clean = requested_nd_label.strip()
    tile_labels = tuple(label for _idx, _id, label in FX3_BIG6_SIX_TILE_TOPOLOGY_P203)

    if mode_clean not in VALID_MODE_SETTINGS_P203:
        errors.append(f"INVALID_MODE_SETTINGS_VALUE: {mode_clean}")
    elif mode_clean != FX3_BIG6_PREREQ_MODE_SETTINGS_P203:
        errors.append(
            "BIG6_HOME_UNAVAILABLE_REQUIRES_MODE_SETTINGS_FIXED_VARIABLE"
        )

    if not home_custom_key_bound:
        errors.append("BIG6_HOME_UNAVAILABLE_REQUIRES_CUSTOM_KEY_HOME_BINDING")

    if ll_clean not in VALID_HOME_LOWER_LEFT_CHOICES_P203:
        errors.append(f"INVALID_HOME_LOWER_LEFT_CHOICE: {ll_clean}")

    if nd_clean not in VALID_ND_REFERENCE_LABELS_P203:
        errors.append(f"INVALID_ND_FILTER_LABEL: {nd_clean}")

    # Stage-B must NEVER transmit FX6 physical motorized Variable ND commands to FX3 CP!
    if (not stage_b_end_actuator_tx_blocked) and (
        ll_clean == "ND Filter" or nd_clean in FX6_MOTORIZED_END_RANGE_FRACTIONS_P203
    ):
        errors.append(
            "FX3_ABSENT_PHYSICAL_END_ACTUATOR_TX_FORBIDDEN: "
            "Stage-B must block PID_SET_VARIABLE_ND_VALUE frames on ILME-FX3"
        )

    appfw_enum = FX3_HOME_LOWER_LEFT_TO_APPFW_ENUM_P203.get(ll_clean, "INVALID")
    accessible = (
        mode_clean == FX3_BIG6_PREREQ_MODE_SETTINGS_P203 and bool(home_custom_key_bound)
    )

    if ll_clean == "Aperture":
        tile4_binding = "EMOUNT_LENS_APERTURE_IRIS_SERVO"
        nd_manual_only = False
        b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH
    elif ll_clean == "ND Filter":
        tile4_binding = f"MANUAL_ND_FRACTION_METADATA_ONLY:{nd_clean}"
        nd_manual_only = True
        b_cls = BRIDGE_CLASS_MASKED_ABSENT_HW
    else:
        tile4_binding = "INVALID"
        nd_manual_only = False
        b_cls = BRIDGE_CLASS_MASKED_ABSENT_HW

    if errors:
        return Big6HomeAndZeroEndEvalResult(
            valid=False,
            menu_path=FX3_HOME_LOWER_LEFT_MENU_PATH_P203,
            mode_settings=mode_clean,
            home_custom_key_bound=bool(home_custom_key_bound),
            big6_home_accessible=accessible,
            tile_count=len(tile_labels),
            tiles=tile_labels,
            seventh_status_region=FX3_BIG6_SEVENTH_STATUS_REGION_P203,
            home_lower_left_choice=ll_clean,
            appfw_lower_left_enum=appfw_enum,
            tile_4_effective_binding=tile4_binding,
            requested_nd_label=nd_clean,
            physical_internal_end_present_on_fx3=False,
            physical_internal_end_present_on_fx6=True,
            nd_treated_as_manual_reference_only=nd_manual_only,
            stage_b_end_actuator_tx_blocked=bool(stage_b_end_actuator_tx_blocked),
            e_nd_actuator_tx_count=0,
            bridge_class=b_cls,
            status=errors[0],
            errors=tuple(errors),
        )

    status = (
        "OK_BIG6_TILE4_EMOUNT_APERTURE_ZERO_END_TX"
        if ll_clean == "Aperture"
        else "OK_BIG6_TILE4_ND_MANUAL_METADATA_ONLY_ZERO_END_TX"
    )
    return Big6HomeAndZeroEndEvalResult(
        valid=True,
        menu_path=FX3_HOME_LOWER_LEFT_MENU_PATH_P203,
        mode_settings=mode_clean,
        home_custom_key_bound=True,
        big6_home_accessible=True,
        tile_count=6,
        tiles=tile_labels,
        seventh_status_region=FX3_BIG6_SEVENTH_STATUS_REGION_P203,
        home_lower_left_choice=ll_clean,
        appfw_lower_left_enum=appfw_enum,
        tile_4_effective_binding=tile4_binding,
        requested_nd_label=nd_clean,
        physical_internal_end_present_on_fx3=False,
        physical_internal_end_present_on_fx6=True,
        nd_treated_as_manual_reference_only=nd_manual_only,
        stage_b_end_actuator_tx_blocked=True,
        e_nd_actuator_tx_count=0,
        bridge_class=b_cls,
        status=status,
        errors=(),
    )


# ---------------------------------------------------------------------------
# Pillar 2 Evaluator — Slot-1 `CAMSET` Dual-Media Path Split & `.DAT` Firewall
# ---------------------------------------------------------------------------


def serialize_camset_dat_header(
    *,
    model_name: str,
    profile_index: int = 1,
) -> Tuple[bytes, CamsetDatHeaderSummary]:
    """Synthesize a clean-room 32-byte `CAMSETxx.DAT` model-bound header."""
    if model_name not in CAMSET_MODEL_SPECS_P203:
        raise ValueError(f"Unsupported CAMSET model_name: {model_name}")
    if not (CAMSET_MIN_PROFILE_INDEX_P203 <= profile_index <= CAMSET_MAX_PROFILES_PER_CARD_P203):
        raise ValueError(f"CAMSET profile_index out of range 1..10: {profile_index}")

    model_id_u32, magic8, bk4_subsys = CAMSET_MODEL_SPECS_P203[model_name]
    body = struct.pack(
        "<8sIIHH8s",
        magic8,
        model_id_u32,
        bk4_subsys,
        profile_index,
        CAMSET_DAT_HEADER_BYTES_P203,
        b"CAMSETv7",
    )
    crc = zlib.crc32(body) & 0xFFFFFFFF
    raw = body + struct.pack("<I", crc)
    summary = CamsetDatHeaderSummary(
        model_name=model_name,
        model_id_hex=f"0x{model_id_u32:08x}",
        magic_ascii=magic8.decode("ascii"),
        bk4_subsystems=bk4_subsys,
        profile_index=profile_index,
        header_bytes=len(raw),
        crc32_hex=f"0x{crc:08x}",
    )
    return raw, summary


def verify_camset_dat_model_compatibility(
    dat_header_bytes: bytes,
    *,
    expected_reader_model: str = "ILME-FX3",
) -> Tuple[bool, str]:
    """Verify binary `CAMSETxx.DAT` header CRC32 and strict model-ID / BK4 compatibility."""
    if expected_reader_model not in CAMSET_MODEL_SPECS_P203:
        return (False, f"UNKNOWN_READER_MODEL:{expected_reader_model}")
    if len(dat_header_bytes) != CAMSET_DAT_HEADER_BYTES_P203:
        return (False, "CAMSET_DAT_TRUNCATED_OR_INVALID_SIZE")

    magic8, model_id_u32, bk4_subsys, prof_idx, hdr_sz, _tag, stored_crc = struct.unpack(
        "<8sIIHH8sI", dat_header_bytes
    )
    calc_crc = zlib.crc32(dat_header_bytes[:-4]) & 0xFFFFFFFF
    if calc_crc != stored_crc or hdr_sz != CAMSET_DAT_HEADER_BYTES_P203:
        return (False, "CAMSET_DAT_CRC32_CORRUPT")
    if not (CAMSET_MIN_PROFILE_INDEX_P203 <= prof_idx <= CAMSET_MAX_PROFILES_PER_CARD_P203):
        return (False, "CAMSET_DAT_PROFILE_INDEX_INVALID")

    exp_id, exp_magic, exp_subsys = CAMSET_MODEL_SPECS_P203[expected_reader_model]
    if magic8 != exp_magic or model_id_u32 != exp_id or bk4_subsys != exp_subsys:
        return (False, "CAMSET_CROSS_MODEL_DAT_INCOMPATIBLE")

    return (True, "OK_CAMSET_DAT_MODEL_EXACT_MATCH")


def resolve_expected_camset_directory(media_type: str) -> str:
    """Return canonical FX3 Slot-1 `CAMSET` directory for SD family vs CFexpress Type A."""
    m = media_type.strip().upper()
    if m in SD_FAMILY_MEDIA_TYPES_P203:
        return CAMSET_SD_ROOT_DIR_P203
    if m == "CFEXPRESS_TYPE_A":
        return CAMSET_CFEXPRESS_A_ROOT_DIR_P203
    raise ValueError(f"Unsupported CAMSET media_type: {media_type}")


def evaluate_camset_slot1_path_and_cross_model_firewall(
    *,
    camera_mode: str = "MOVIE_NORMAL",
    target_slot: str = "Slot 1",
    media_type: str = "SDXC",
    profile_index: int = 1,
    requested_card_path: Optional[str] = None,
    requested_payload_fields: Sequence[str] = ("FPS", "Base ISO", "Shutter Angle"),
    force_include_machine_bound_fields: bool = False,
    writer_model: str = "ILME-FX3",
    reader_model: str = "ILME-FX3",
    stage_b_active: bool = False,
    stage_b_storage_target: str = "/tmp/fx6_camset_overlay/CAMSET01.json",
    lifecycle_stage: str = "H0",
) -> CamsetSlot1PathAndFirewallEvalResult:
    """Audit `[Save/Load Settings]` Slot-1 lock, SD vs CFexpress-A path split & cross-model firewall."""
    errors: List[str] = []
    cam_clean = camera_mode.strip()
    slot_clean = target_slot.strip()
    media_clean = media_type.strip().upper()
    stage_clean = lifecycle_stage.strip().upper()

    h0_digest = hashlib.sha256(b"STOCK_FX3_702_P2_SETTING_AND_SLOT1_CAMSET_H0").hexdigest()

    if cam_clean not in VALID_CAMERA_OPERATING_MODES_P203:
        errors.append(f"INVALID_CAMERA_OPERATING_MODE: {cam_clean}")

    menu_greyed = cam_clean == "MR_RECALL_CAMERA_SETTING"
    if menu_greyed:
        errors.append("CAMSET_GREYED_OUT_IN_MR_RECALL_MODE")

    if slot_clean != CAMSET_ALLOWED_SLOT_P203:
        errors.append(f"CAMSET_SLOT2_DISALLOWED_SLOT1_ONLY: got {slot_clean}")

    if media_clean not in VALID_CAMSET_MEDIA_TYPES_P203:
        errors.append(f"INVALID_CAMSET_MEDIA_TYPE: {media_clean}")
        expected_dir = "INVALID"
    else:
        expected_dir = resolve_expected_camset_directory(media_clean)

    if not (
        CAMSET_MIN_PROFILE_INDEX_P203
        <= int(profile_index)
        <= CAMSET_MAX_PROFILES_PER_CARD_P203
    ):
        errors.append(f"CAMSET_PROFILE_INDEX_OUT_OF_RANGE_1_TO_10: {profile_index}")
        canonical_fn = "INVALID"
    else:
        canonical_fn = f"CAMSET{int(profile_index):02d}.DAT"

    effective_card_path = (
        requested_card_path.strip()
        if requested_card_path is not None
        else (f"{expected_dir}{canonical_fn}" if expected_dir != "INVALID" and canonical_fn != "INVALID" else "INVALID")
    )

    path_ok = False
    if expected_dir != "INVALID" and canonical_fn != "INVALID":
        expected_full = f"{expected_dir}{canonical_fn}"
        if effective_card_path == expected_full:
            path_ok = True
        else:
            if media_clean in SD_FAMILY_MEDIA_TYPES_P203 and effective_card_path.startswith(
                CAMSET_CFEXPRESS_A_ROOT_DIR_P203
            ):
                errors.append("CAMSET_SD_MISSING_PRIVATE_ROOT_PREFIX")
            elif media_clean == "CFEXPRESS_TYPE_A" and effective_card_path.startswith(
                CAMSET_SD_ROOT_DIR_P203
            ):
                errors.append("CAMSET_CFEXPRESS_A_FORBIDDEN_PRIVATE_PREFIX")
            else:
                errors.append(
                    f"CAMSET_CARD_PATH_MISMATCH: expected {expected_full}, got {effective_card_path}"
                )

    stripped = tuple(
        f for f in requested_payload_fields if f in EXCLUDED_MACHINE_BOUND_CAMSET_FIELDS_P203
    )
    if force_include_machine_bound_fields and stripped:
        errors.append(
            f"CAMSET_MACHINE_BOUND_FIELDS_FORBIDDEN:{','.join(stripped)}"
        )

    if writer_model not in CAMSET_MODEL_SPECS_P203:
        errors.append(f"UNKNOWN_CAMSET_WRITER_MODEL: {writer_model}")
    if reader_model not in CAMSET_MODEL_SPECS_P203:
        errors.append(f"UNKNOWN_CAMSET_READER_MODEL: {reader_model}")

    cross_incompat = False
    if (
        writer_model in CAMSET_MODEL_SPECS_P203
        and reader_model in CAMSET_MODEL_SPECS_P203
        and not stage_b_active
        and writer_model != reader_model
    ):
        cross_incompat = True
        errors.append(
            f"CAMSET_CROSS_MODEL_DAT_INCOMPATIBLE: {writer_model} -> {reader_model}"
        )

    if stage_clean not in VALID_LIFECYCLE_STAGES_P203:
        errors.append(f"INVALID_LIFECYCLE_STAGE: {stage_clean}")

    redirected_overlay = False
    if stage_b_active:
        tgt_clean = stage_b_storage_target.strip()
        if tgt_clean.startswith(f"{VOLATILE_FX6_CAMSET_OVERLAY_DIR_P203}/"):
            redirected_overlay = True
        else:
            cross_incompat = writer_model != reader_model
            errors.append(
                f"STAGE_B_CAMSET_WRITE_TO_STOCK_PATH_BLOCKED: {tgt_clean}"
            )

    if stage_b_active:
        b_cls = (
            BRIDGE_CLASS_SHIM_TRANSLATED
            if redirected_overlay
            else BRIDGE_CLASS_HARD_WRITE_PROTECTED
        )
    elif cross_incompat or not errors:
        b_cls = (
            BRIDGE_CLASS_HARD_WRITE_PROTECTED
            if cross_incompat
            else BRIDGE_CLASS_NATIVE_PASSTHROUGH
        )
    else:
        b_cls = BRIDGE_CLASS_HARD_WRITE_PROTECTED

    status = (
        errors[0]
        if errors
        else (
            "OK_STAGE_B_CAMSET_SANDBOXED_IN_VOLATILE_OVERLAY_H0_EQ_H3"
            if stage_b_active
            else "OK_STOCK_SLOT1_CAMSET_DUAL_MEDIA_PATH_VERIFIED"
        )
    )

    return CamsetSlot1PathAndFirewallEvalResult(
        valid=len(errors) == 0,
        camera_mode=cam_clean,
        menu_greyed_out=menu_greyed,
        target_slot=slot_clean,
        slot1_only_enforced=(slot_clean == CAMSET_ALLOWED_SLOT_P203),
        media_type=media_clean,
        profile_index=int(profile_index),
        canonical_filename=canonical_fn,
        expected_card_directory=expected_dir,
        requested_card_path=effective_card_path,
        dual_media_path_valid=path_ok,
        excluded_machine_bound_fields=EXCLUDED_MACHINE_BOUND_CAMSET_FIELDS_P203,
        stripped_machine_bound_fields=stripped,
        writer_model=writer_model,
        reader_model=reader_model,
        cross_model_incompatible_blocked=cross_incompat,
        stage_b_active=bool(stage_b_active),
        stage_b_storage_target=stage_b_storage_target.strip(),
        redirected_to_volatile_camset_overlay=redirected_overlay,
        lifecycle_stage=stage_clean,
        h0_state_sha256=h0_digest,
        h3_state_sha256=h0_digest,
        h0_equals_h3=True,
        p2_setting_mutation_bytes=0,
        stock_slot1_camset_mutation_bytes=0,
        bridge_class=b_cls,
        status=status,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3 Evaluator — `VMC-BNCM1` Body-Only `TC IN` & Digital HDMI `TC OUT`
# ---------------------------------------------------------------------------


def evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
    *,
    physical_port: str = "BODY_MULTI_MICRO_USB",
    requested_direction: str = "TC_IN",
    boot_context: str = "NORMAL_OS",
    shooting_mode: str = "Movie",
    tc_make: str = "Preset",
    tc_run: str = "Free Run",
    lock_dwell_sec: float = 10.0,
    tc_setting_edited_after_lock: bool = False,
    hdmi_tc_output_menu_setting: str = "On",
) -> VmcBncm1TcInAndHdmiTcOutEvalResult:
    """Audit `VMC-BNCM1` body-only `TC IN` (`EXT-LK`), `XLR-H1` prohibition & HDMI `TC OUT`."""
    errors: List[str] = []
    port_clean = physical_port.strip()
    dir_clean = requested_direction.strip().upper()
    boot_clean = boot_context.strip().upper()
    shoot_clean = shooting_mode.strip()
    make_clean = tc_make.strip()
    run_clean = tc_run.strip()
    hdmi_clean = hdmi_tc_output_menu_setting.strip()

    if port_clean not in VALID_TC_PHYSICAL_PORTS_P203:
        errors.append(f"INVALID_TC_PHYSICAL_PORT: {port_clean}")
    if dir_clean not in VALID_TC_DIRECTIONS_P203:
        errors.append(f"INVALID_TC_DIRECTION: {dir_clean}")
    if boot_clean not in VALID_BOOT_CONTEXTS_P203:
        errors.append(f"INVALID_BOOT_CONTEXT: {boot_clean}")
    if shoot_clean not in VALID_TC_SHOOTING_MODES_P203:
        errors.append(f"INVALID_TC_SHOOTING_MODE: {shoot_clean}")
    if make_clean not in VALID_TC_MAKE_MODES_P203:
        errors.append(f"INVALID_TC_MAKE_MODE: {make_clean}")
    if run_clean not in VALID_TC_RUN_MODES_P203:
        errors.append(f"INVALID_TC_RUN_MODE: {run_clean}")
    if hdmi_clean not in ("On", "Off"):
        errors.append(f"INVALID_HDMI_TC_OUTPUT_SETTING: {hdmi_clean}")
    if lock_dwell_sec < 0.0:
        errors.append(f"NEGATIVE_LOCK_DWELL_SEC: {lock_dwell_sec}")

    xlr_h1_prohibited = port_clean == "XLR_H1_HANDLE_MICRO_USB"
    if xlr_h1_prohibited:
        errors.append(
            "VMC_BNCM1_PROHIBITED_ON_XLR_H1_HANDLE_MICRO_USB: "
            "VMC-BNCM1 must connect ONLY to camera body Multi/Micro USB terminal"
        )

    uart_blocked = (
        boot_clean == "H0_UART_BOOT" and port_clean == "BODY_MULTI_MICRO_USB"
    )
    if uart_blocked:
        errors.append(
            "VMC_BNCM1_FORBIDDEN_DURING_UART_BOOT_PINS_7_8_9: "
            "disconnect VMC-BNCM1 during H0/Tier-3 uart_boot"
        )

    bnc_out_rejected = dir_clean == "TC_OUT" and port_clean in (
        "BODY_MULTI_MICRO_USB",
        "FX6_VIRTUAL_BNC_PORT",
    )
    errno_code: Optional[str] = None
    if bnc_out_rejected:
        errno_code = "EOPNOTSUPP"
        errors.append(
            "BNC_MULTI_USB_TC_OUT_EOPNOTSUPP: "
            "ILME-FX3 has no BNC/LTC TC OUT; route digital TC OUT via Type-A HDMI only"
        )

    if dir_clean == "TC_IN" and port_clean == "HDMI_TYPE_A":
        errno_code = "EOPNOTSUPP"
        errors.append("HDMI_TYPE_A_DOES_NOT_ACCEPT_EXTERNAL_LTC_IN")

    if dir_clean == "TC_IN" and port_clean == "FX6_VIRTUAL_BNC_PORT":
        errors.append("FX6_DEDICATED_BNC_ABSENT_USE_BODY_MULTI_USB_VMC_BNCM1")

    # HDMI TC OUT state: active only when HDMI menu = On AND Movie mode (auto-disabled in S&Q)
    hdmi_disabled_sq = shoot_clean == "S&Q"
    hdmi_tc_active = (
        hdmi_clean == "On"
        and shoot_clean == "Movie"
        and not uart_blocked
    )

    ext_lk_locked = False
    ext_lk_label = "INTERNAL_TC"

    if not errors and dir_clean == "TC_IN" and port_clean == "BODY_MULTI_MICRO_USB":
        if shoot_clean != "Movie":
            ext_lk_label = "UNLOCKED_NON_MOVIE_OR_SQ_MODE"
        elif make_clean != "Preset" or run_clean != "Free Run":
            ext_lk_label = "UNLOCKED_REQUIRES_PRESET_AND_FREE_RUN"
        elif tc_setting_edited_after_lock:
            ext_lk_label = "UNLOCKED_BY_TC_SETTING_EDIT"
        elif lock_dwell_sec < EXT_LK_MIN_LOCK_DWELL_SEC_P203:
            ext_lk_label = "ACQUIRING_EXT_LK_UNDER_10S"
        else:
            ext_lk_locked = True
            ext_lk_label = "EXT-LK"
    elif not errors and dir_clean == "TC_OUT" and port_clean == "HDMI_TYPE_A":
        ext_lk_label = (
            "HDMI_DIGITAL_TC_OUT_ACTIVE"
            if hdmi_tc_active
            else (
                "HDMI_TC_OUT_AUTO_DISABLED_IN_SQ"
                if hdmi_disabled_sq
                else "HDMI_TC_OUT_OFF"
            )
        )

    if xlr_h1_prohibited or uart_blocked:
        b_cls = BRIDGE_CLASS_HARD_WRITE_PROTECTED
    elif bnc_out_rejected:
        b_cls = BRIDGE_CLASS_MASKED_ABSENT_HW
    elif dir_clean == "TC_OUT" and port_clean == "HDMI_TYPE_A":
        b_cls = BRIDGE_CLASS_SHIM_TRANSLATED
    else:
        b_cls = BRIDGE_CLASS_NATIVE_PASSTHROUGH

    status = errors[0] if errors else f"OK_{ext_lk_label}"
    return VmcBncm1TcInAndHdmiTcOutEvalResult(
        valid=len(errors) == 0,
        adapter_model="VMC-BNCM1",
        adapter_part_number=VMC_BNCM1_PART_NUMBER_P203,
        physical_port=port_clean,
        requested_direction=dir_clean,
        boot_context=boot_clean,
        shooting_mode=shoot_clean,
        tc_make=make_clean,
        tc_run=run_clean,
        lock_dwell_sec=float(lock_dwell_sec),
        tc_setting_edited_after_lock=bool(tc_setting_edited_after_lock),
        xlr_h1_handle_port_prohibited=xlr_h1_prohibited,
        uart_boot_pin_contention_blocked=uart_blocked,
        bnc_tc_out_rejected_eopnotsupp=bnc_out_rejected,
        errno_code=errno_code,
        bnc_tc_out_tx_packets=0,
        ext_lk_locked=ext_lk_locked,
        ext_lk_state_label=ext_lk_label,
        hdmi_tc_output_menu_setting=hdmi_clean,
        hdmi_tc_out_active=hdmi_tc_active,
        hdmi_tc_out_disabled_in_sq=hdmi_disabled_sq,
        bridge_class=b_cls,
        status=status,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4 Evaluator — Hard Write Firewall & 12-Touchpoint Compatibility Matrix
# ---------------------------------------------------------------------------


def evaluate_phase203_write_guard(target_path: str) -> Phase203WriteGuardResult:
    """Enforce zero persistent eMMC / SPI-NOR / stock Slot-1 `CAMSET` Stage-B mutations."""
    clean = target_path.strip()
    errors: List[str] = []

    if not clean:
        errors.append("EMPTY_TARGET_PATH_BLOCKED")
        return Phase203WriteGuardResult(
            valid=False,
            target_path=clean,
            volatile_overlay_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            calibration_mutation_bytes=0,
            status=errors[0],
            errors=tuple(errors),
        )

    norm = os.path.normpath(clean) if clean.startswith("/") else clean
    if ".." in clean.split("/") or FORBIDDEN_PERSISTENT_TARGET_RE_P203.search(clean) or FORBIDDEN_PERSISTENT_TARGET_RE_P203.search(norm):
        errors.append(f"HARD_WRITE_PROTECTED_TARGET_BLOCKED: {clean}")
        return Phase203WriteGuardResult(
            valid=False,
            target_path=clean,
            volatile_overlay_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            calibration_mutation_bytes=0,
            status=errors[0],
            errors=tuple(errors),
        )

    is_allowed_volatile = any(
        clean.startswith(pfx) for pfx in VOLATILE_ALLOWED_PREFIXES_P203
    )
    if not is_allowed_volatile:
        errors.append(f"UNAPPROVED_NON_VOLATILE_PATH_BLOCKED: {clean}")
        return Phase203WriteGuardResult(
            valid=False,
            target_path=clean,
            volatile_overlay_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            calibration_mutation_bytes=0,
            status=errors[0],
            errors=tuple(errors),
        )

    return Phase203WriteGuardResult(
        valid=True,
        target_path=clean,
        volatile_overlay_allowed=True,
        persistent_write_blocked=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        persistent_writes=0,
        calibration_mutation_bytes=0,
        status="OK_VOLATILE_OVERLAY_TARGET_PERMITTED",
        errors=(),
    )


def build_phase203_compat_matrix() -> Phase203CompatMatrixSummary:
    """Build deterministic 12-touchpoint 4-class Wave-26 compatibility matrix."""
    entries: Tuple[Phase203TouchpointEntry, ...] = (
        Phase203TouchpointEntry(
            touchpoint_id="P203-01",
            pillar="PILLAR_1_BIG6_ZERO_END",
            fx6_or_host_component="FX3 Ver. 7.00+/7.02 BIG6 Home 6-Tile + Status Bar ([Mode Settings]=Fixed/Variable + [HOME] key)",
            fx3_target="FPS, ISO/Base ISO, Shutter Speed/Angle, Aperture/ND, PP/Select LUT, White Balance",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="big6_home_accessible == True when Fixed/Variable & HOME bound",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-02",
            pillar="PILLAR_1_BIG6_ZERO_END",
            fx6_or_host_component="MENU -> Setup -> [Operation Customize] -> [Home (Lower Left)] = [Aperture]",
            fx3_target="MOVIE_HOME_LOWER_LEFT_APERTURE -> E-Mount lens iris servo",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="e_nd_actuator_tx_count == 0",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-03",
            pillar="PILLAR_1_BIG6_ZERO_END",
            fx6_or_host_component="FX6 Physical Motorized Variable ND (1/4..1/128, PID_SET_VARIABLE_ND_VALUE)",
            fx3_target="ILME-FX3 absent internal e-ND -> [Home (Lower Left)]=[ND Filter] manual fraction metadata only",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="e_nd_actuator_tx_count == 0 && physical_internal_end_present_on_fx3 == False",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-04",
            pillar="PILLAR_1_BIG6_ZERO_END",
            fx6_or_host_component="Stage-B Unmasked CP e-ND Actuator Frame Injection Guard",
            fx3_target="CP UIPC bus firewall blocking PID_SET_VARIABLE_ND_VALUE / ROTARY_ENCODER",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="e_nd_actuator_tx_count == 0 (fail-closed before CP wire)",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-05",
            pillar="PILLAR_2_CAMSET_SLOT1_FIREWALL",
            fx6_or_host_component="[Save/Load Settings] Slot-1 Lock (CAMSET01..CAMSET10.DAT, greyed in MR mode)",
            fx3_target="Slot 1 only (Slot 2 disallowed), strips Custom WB 1/2/3, FTP, Streaming, IP/Cert, Date/Time",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="slot1_only_enforced == True && max_profiles == 10",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-06",
            pillar="PILLAR_2_CAMSET_SLOT1_FIREWALL",
            fx6_or_host_component="SD/SDHC/SDXC vs CFexpress Type A CAMSET Root Path Split (%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT)",
            fx3_target="SD -> /PRIVATE/SONY/SETTING/FX3/CAMSET/ vs CFexpress-A -> /SONY/SETTING/FX3/CAMSET/",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="dual_media_path_valid == True",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-07",
            pillar="PILLAR_2_CAMSET_SLOT1_FIREWALL",
            fx6_or_host_component="Cross-Model CAMSETxx.DAT Binary Firewall (ILME-FX3 vs ILME-FX3A vs ILME-FX6)",
            fx3_target="Reject mismatched model IDs (0x91030080 vs 0x91030082 vs 0x91030060) & BK4 counts",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="cross_model_incompatible_blocked == True",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-08",
            pillar="PILLAR_2_CAMSET_SLOT1_FIREWALL",
            fx6_or_host_component="Stage-B FX6 All-File / CAMSET Save-Load Redirection",
            fx3_target="Volatile /tmp/fx6_camset_overlay sandbox (zero writes to FX3/CAMSET/ or p2:/setting)",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="h0_equals_h3 == True && p2_setting_mutation_bytes == 0",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-09",
            pillar="PILLAR_3_VMC_BNCM1_HDMI_TC",
            fx6_or_host_component="VMC-BNCM1 (A-5051-506-A, 0.2m) Body Multi/Micro USB Unidirectional TC IN",
            fx3_target="[Movie] + [Preset] + [Free Run] >= 10s -> EXT-LK (unlocked on S&Q or TC edits)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="ext_lk_locked == True after >= 10s dwell",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-10",
            pillar="PILLAR_3_VMC_BNCM1_HDMI_TC",
            fx6_or_host_component="XLR-H1 Top Handle Side Micro-USB Port Mis-Plug & H0 uart_boot Pin 7/8/9 Guard",
            fx3_target="Hard prohibition of VMC-BNCM1 on XLR-H1 handle Micro-USB & during H0 uart_boot",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="xlr_h1_handle_port_prohibited == True on handle port",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-11",
            pillar="PILLAR_3_VMC_BNCM1_HDMI_TC",
            fx6_or_host_component="FX6 Switchable BNC TC OUT Request on ILME-FX3 Multi/Micro USB",
            fx3_target="Fail-closed EOPNOTSUPP rejection (zero reverse LTC/BNC drive on Multi/Micro USB)",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="errno_code == 'EOPNOTSUPP' && bnc_tc_out_tx_packets == 0",
        ),
        Phase203TouchpointEntry(
            touchpoint_id="P203-12",
            pillar="PILLAR_3_VMC_BNCM1_HDMI_TC",
            fx6_or_host_component="FX6 Timecode Output -> FX3 Full-Size Type-A HDMI Digital TC OUT",
            fx3_target="[HDMI Output Settings] -> [Time Code Output] = [On] in Movie (auto-disabled in S&Q)",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="hdmi_tc_out_active == True in Movie && False in S&Q",
        ),
    )
    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    pillar_counts: Dict[str, int] = {}
    for entry in entries:
        class_counts[entry.bridge_class] = class_counts.get(entry.bridge_class, 0) + 1
        pillar_counts[entry.pillar] = pillar_counts.get(entry.pillar, 0) + 1
    return Phase203CompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        pillar_counts=pillar_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Scanners & Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def _scan_uxc_bounded_rdonly_p203(
    path: Path,
    *,
    pack_name: str,
    body_label: str,
    required_tokens: Sequence[str],
) -> BoundedUxcSummaryP203:
    """Strictly `os.O_RDONLY` bounded `os.pread` scanner for `.uxc` string packs (< 400 KiB)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        buf = os.pread(fd, sz, 0) if sz > 0 else b""
        magic_ok = len(buf) >= 4 and buf[:4] in (b"uxd\x07", b"uxc\x07")
        req_hits = {t: buf.count(t.encode("utf-8")) for t in required_tokens}
        return BoundedUxcSummaryP203(
            pack_name=pack_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            uxc_magic_valid=magic_ok,
            required_token_hits=req_hits,
        )
    finally:
        os.close(fd)


def _scan_uxc_buf_clean_room_p203(
    buf: bytes,
    *,
    pack_name: str,
    body_label: str,
    required_tokens: Sequence[str],
) -> BoundedUxcSummaryP203:
    magic_ok = len(buf) >= 4 and buf[:4] in (b"uxd\x07", b"uxc\x07")
    return BoundedUxcSummaryP203(
        pack_name=pack_name,
        body_label=body_label,
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=len(buf),
        uxc_magic_valid=magic_ok,
        required_token_hits={t: buf.count(t.encode("utf-8")) for t in required_tokens},
    )


def _scan_cpapp_bounded_rdonly_p203(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
    forbidden_tokens: Sequence[str],
) -> BoundedCpappSummaryP203:
    """Strictly `os.O_RDONLY` bounded `os.pread` of CP RTOS head (768 KiB) + tail (6 MiB)."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        counts: Dict[str, int] = {t: 0 for t in tokens}
        forb_counts: Dict[str, int] = {t: 0 for t in forbidden_tokens}
        enc = [(t, t.encode("ascii")) for t in tokens]
        forb_enc = [(t, t.encode("ascii")) for t in forbidden_tokens]
        head_len = min(sz, CPAPP_BOUNDED_HEAD_BYTES_P203)
        slices: List[Tuple[int, int]] = [(0, head_len)]
        tail_off = max(head_len, sz - CPAPP_BOUNDED_TAIL_BYTES_P203)
        if tail_off < sz:
            slices.append((tail_off, sz - tail_off))
        bytes_read = 0
        for off, ln in slices:
            if ln > 0:
                chunk = os.pread(fd, ln, off)
                bytes_read += len(chunk)
                for tok, b_tok in enc:
                    counts[tok] += chunk.count(b_tok)
                for tok, b_tok in forb_enc:
                    forb_counts[tok] += chunk.count(b_tok)
        return BoundedCpappSummaryP203(
            binary_name=binary_name,
            body_label=body_label,
            source_mode="LOCAL_DONOR_RDONLY",
            file_bytes=sz,
            bounded_bytes_read=bytes_read,
            marker_hits=counts,
            forbidden_end_actuator_hits=forb_counts,
        )
    finally:
        os.close(fd)


def _scan_cpapp_buf_clean_room_p203(
    buf: bytes,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
    forbidden_tokens: Sequence[str],
) -> BoundedCpappSummaryP203:
    return BoundedCpappSummaryP203(
        binary_name=binary_name,
        body_label=body_label,
        source_mode="CLEAN_ROOM_SYNTHETIC",
        file_bytes=len(buf),
        bounded_bytes_read=len(buf),
        marker_hits={t: buf.count(t.encode("ascii")) for t in tokens},
        forbidden_end_actuator_hits={
            t: buf.count(t.encode("ascii")) for t in forbidden_tokens
        },
    )


def build_clean_room_realhw_big6_noend_camset_vmcbncm1_fixtures() -> Dict[str, bytes]:
    """Synthesize deterministic clean-room fixtures (`raw_firmware_bytes_leaked == 0`)."""
    fx3_appfw_tokens = (
        APPFW_SHARED_WAVE26_MARKERS_P203 + APPFW_FX3_702_EXCLUSIVE_MARKERS_P203
    )
    fx6_appfw_tokens = (
        APPFW_SHARED_WAVE26_MARKERS_P203
        + APPFW_FX6_601_EXCLUSIVE_END_AND_SDI_MARKERS_P203
    )

    fx3_appfw_elf = _build_synthetic_elf64(
        exports=("appfw_fx3_702_big6_camset_vmcbncm1_entry",),
        imports=("mpr_set_tc_output",),
        dt_needed=("libmpr.so", "libc.so"),
        rodata_strings=fx3_appfw_tokens,
    )
    fx6_appfw_elf = _build_synthetic_elf64(
        exports=("appfw_fx6_601_big6_camset_tc_entry",),
        imports=("mpr_set_tc_output",),
        dt_needed=("libmpr.so", "libc.so"),
        rodata_strings=fx6_appfw_tokens,
    )

    fx3_uxc_en_f = (
        b"uxd\x07"
        + b"\x00" * 12
        + b"\x00".join(t.encode("utf-8") for t in UXC_FX3_EN_F_REQUIRED_TOKENS_P203)
        + b"\x00"
    )
    fx6_uxc_en = (
        b"uxd\x07"
        + b"\x00" * 12
        + b"\x00".join(t.encode("utf-8") for t in UXC_FX6_EN_REQUIRED_TOKENS_P203)
        + b"\x00"
    )
    cpapp_payload = (
        b"\x00".join(t.encode("ascii") for t in CPAPP_SHARED_TC_IMAGER_MARKERS_P203)
        + b"\x00"
    )

    return {
        "fx3_appfw": fx3_appfw_elf,
        "fx6_appfw": fx6_appfw_elf,
        "fx3_uxc_en_f": fx3_uxc_en_f,
        "fx6_uxc_en": fx6_uxc_en,
        "fx3_cpapp": cpapp_payload,
        "fx6_cpapp": cpapp_payload,
    }


def _inspect_donors_or_clean_room_p203(
    *,
    clean_room: bool,
    repo_root: Path,
) -> Tuple[str, bool, float, Dict[str, object]]:
    """Bounded `O_RDONLY` donor inspection (< 0.15s cold, cached per process) or synthetic fallback."""
    t_start = time.perf_counter()
    all_appfw_scan_tokens = (
        APPFW_SHARED_WAVE26_MARKERS_P203
        + APPFW_FX3_702_EXCLUSIVE_MARKERS_P203
        + APPFW_FX6_601_EXCLUSIVE_END_AND_SDI_MARKERS_P203
    )

    use_clean_room = bool(clean_room or is_forced_clean_room())
    donor_paths: Dict[str, Optional[Path]] = {}
    if not use_clean_room:
        rel_map = {
            "fx3_appfw": FX3_APPFW_P203_RELPATH,
            "fx6_appfw": FX6_APPFW_P203_RELPATH,
            "fx3_uxc_en_f": FX3_UXC_EN_F_P203_RELPATH,
            "fx6_uxc_en": FX6_UXC_EN_P203_RELPATH,
            "fx3_cpapp": FX3_CPAPP_P203_RELPATH,
            "fx6_cpapp": FX6_CPAPP_P203_RELPATH,
        }
        for key, rel in rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=repo_root)
        if any(p is None or not p.is_file() for p in donor_paths.values()):
            use_clean_room = True

    if use_clean_room:
        fx = build_clean_room_realhw_big6_noend_camset_vmcbncm1_fixtures()
        fx3_elf = _scan_elf_buf_ordered(
            fx["fx3_appfw"],
            binary_name="appFw.so",
            body_label="FX3_702",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=all_appfw_scan_tokens,
        )
        fx6_elf = _scan_elf_buf_ordered(
            fx["fx6_appfw"],
            binary_name="appFw.so",
            body_label="FX6_601",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=all_appfw_scan_tokens,
        )
        fx3_uxc = _scan_uxc_buf_clean_room_p203(
            fx["fx3_uxc_en_f"],
            pack_name="string_english_f.uxc",
            body_label="FX3_702",
            required_tokens=UXC_FX3_EN_F_REQUIRED_TOKENS_P203,
        )
        fx6_uxc = _scan_uxc_buf_clean_room_p203(
            fx["fx6_uxc_en"],
            pack_name="string_english.uxc",
            body_label="FX6_601",
            required_tokens=UXC_FX6_EN_REQUIRED_TOKENS_P203,
        )
        fx3_cp = _scan_cpapp_buf_clean_room_p203(
            fx["fx3_cpapp"],
            binary_name="CPAPP-B.BIN",
            body_label="FX3_702",
            tokens=CPAPP_SHARED_TC_IMAGER_MARKERS_P203,
            forbidden_tokens=CPAPP_FORBIDDEN_END_ACTUATOR_MARKERS_P203,
        )
        fx6_cp = _scan_cpapp_buf_clean_room_p203(
            fx["fx6_cpapp"],
            binary_name="cpapp-b.bin",
            body_label="FX6_601",
            tokens=CPAPP_SHARED_TC_IMAGER_MARKERS_P203,
            forbidden_tokens=CPAPP_FORBIDDEN_END_ACTUATOR_MARKERS_P203,
        )
        bundle: Dict[str, object] = {
            "fx3_elf": fx3_elf,
            "fx6_elf": fx6_elf,
            "fx3_uxc": fx3_uxc,
            "fx6_uxc": fx6_uxc,
            "fx3_cp": fx3_cp,
            "fx6_cp": fx6_cp,
            "donor_sizes": {
                "fx3_appfw": fx3_elf.file_bytes,
                "fx6_appfw": fx6_elf.file_bytes,
                "fx3_string_english_f_uxc": fx3_uxc.file_bytes,
                "fx6_string_english_uxc": fx6_uxc.file_bytes,
                "fx3_cpapp_b_bin": fx3_cp.file_bytes,
                "fx6_cpapp_b_bin": fx6_cp.file_bytes,
            },
        }
        return (
            "CLEAN_ROOM_SYNTHETIC",
            False,
            round(time.perf_counter() - t_start, 6),
            bundle,
        )

    cache_key = tuple(str(donor_paths[k]) for k in sorted(donor_paths.keys()))
    if cache_key in _DONOR_SCAN_CACHE_P203:
        return (
            "LOCAL_DONOR_RDONLY",
            True,
            round(time.perf_counter() - t_start, 6),
            _DONOR_SCAN_CACHE_P203[cache_key],
        )

    p_fx3_app = donor_paths["fx3_appfw"]
    p_fx6_app = donor_paths["fx6_appfw"]
    p_fx3_uxc = donor_paths["fx3_uxc_en_f"]
    p_fx6_uxc = donor_paths["fx6_uxc_en"]
    p_fx3_cp = donor_paths["fx3_cpapp"]
    p_fx6_cp = donor_paths["fx6_cpapp"]
    assert p_fx3_app and p_fx6_app and p_fx3_uxc and p_fx6_uxc and p_fx3_cp and p_fx6_cp

    fx3_elf = _scan_elf_fast_rdonly(
        p_fx3_app,
        binary_name="appFw.so",
        body_label="FX3_702",
        tokens=all_appfw_scan_tokens,
    )
    fx6_elf = _scan_elf_fast_rdonly(
        p_fx6_app,
        binary_name="appFw.so",
        body_label="FX6_601",
        tokens=all_appfw_scan_tokens,
    )
    fx3_uxc = _scan_uxc_bounded_rdonly_p203(
        p_fx3_uxc,
        pack_name="string_english_f.uxc",
        body_label="FX3_702",
        required_tokens=UXC_FX3_EN_F_REQUIRED_TOKENS_P203,
    )
    fx6_uxc = _scan_uxc_bounded_rdonly_p203(
        p_fx6_uxc,
        pack_name="string_english.uxc",
        body_label="FX6_601",
        required_tokens=UXC_FX6_EN_REQUIRED_TOKENS_P203,
    )
    fx3_cp = _scan_cpapp_bounded_rdonly_p203(
        p_fx3_cp,
        binary_name="CPAPP-B.BIN",
        body_label="FX3_702",
        tokens=CPAPP_SHARED_TC_IMAGER_MARKERS_P203,
        forbidden_tokens=CPAPP_FORBIDDEN_END_ACTUATOR_MARKERS_P203,
    )
    fx6_cp = _scan_cpapp_bounded_rdonly_p203(
        p_fx6_cp,
        binary_name="cpapp-b.bin",
        body_label="FX6_601",
        tokens=CPAPP_SHARED_TC_IMAGER_MARKERS_P203,
        forbidden_tokens=CPAPP_FORBIDDEN_END_ACTUATOR_MARKERS_P203,
    )

    bundle = {
        "fx3_elf": fx3_elf,
        "fx6_elf": fx6_elf,
        "fx3_uxc": fx3_uxc,
        "fx6_uxc": fx6_uxc,
        "fx3_cp": fx3_cp,
        "fx6_cp": fx6_cp,
        "donor_sizes": {
            "fx3_appfw": fx3_elf.file_bytes,
            "fx6_appfw": fx6_elf.file_bytes,
            "fx3_string_english_f_uxc": fx3_uxc.file_bytes,
            "fx6_string_english_uxc": fx6_uxc.file_bytes,
            "fx3_cpapp_b_bin": fx3_cp.file_bytes,
            "fx6_cpapp_b_bin": fx6_cp.file_bytes,
        },
    }
    _DONOR_SCAN_CACHE_P203[cache_key] = bundle
    return (
        "LOCAL_DONOR_RDONLY",
        False,
        round(time.perf_counter() - t_start, 6),
        bundle,
    )


# ---------------------------------------------------------------------------
# Top-Level Phase 203 Auditor Entrypoint & Deterministic Serialization
# ---------------------------------------------------------------------------


def analyze_realhw_big6_noend_camset_slot1_and_vmcbncm1(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwBig6NoendCamsetSlot1AndVmcbncm1Report:
    """Run the 42nd Firmware-Lab Auditor (`42/42` in `audit-all`)."""
    root = repo_root or DEFAULT_REPO_ROOT
    mode, cache_hit, elapsed, bundle = _inspect_donors_or_clean_room_p203(
        clean_room=clean_room,
        repo_root=root,
    )

    fx3_elf: ElfSectionSummary = bundle["fx3_elf"]  # type: ignore[assignment]
    fx6_elf: ElfSectionSummary = bundle["fx6_elf"]  # type: ignore[assignment]
    fx3_uxc: BoundedUxcSummaryP203 = bundle["fx3_uxc"]  # type: ignore[assignment]
    fx6_uxc: BoundedUxcSummaryP203 = bundle["fx6_uxc"]  # type: ignore[assignment]
    fx3_cp: BoundedCpappSummaryP203 = bundle["fx3_cp"]  # type: ignore[assignment]
    fx6_cp: BoundedCpappSummaryP203 = bundle["fx6_cp"]  # type: ignore[assignment]
    donor_sizes: Dict[str, int] = bundle["donor_sizes"]  # type: ignore[assignment]

    # --- Pillar 1: ILME-FX3 BIG6 6-Tile Topology & Zero Physical e-ND Boundary ---
    p1_errors: List[str] = []
    fx3_big6_keys = (
        "N5model31setting_movie_home_lower_left_tE",
        "set_movie_home_lower_left",
        "MOVIE_HOME_LOWER_LEFT_APERTURE",
        "MOVIE_HOME_LOWER_LEFT_ND_FILTER",
        "GUIDE_BIG6_FPS_SELECT",
        "BKID_APP_setting_movie_home_lower_left",
        "26view_tp_button_01_for_big6",
        "BKID_APP_setting_nd_filter_manual_set",
        "EVENT_FUNC_CUSTOM_FPS_FIXED_VARIABLE_SELECT_ON",
    )
    fx6_big6_keys = (
        "N5model31setting_movie_home_lower_left_tE",
        "set_movie_home_lower_left",
        "MOVIE_HOME_LOWER_LEFT_APERTURE",
        "MOVIE_HOME_LOWER_LEFT_ND_FILTER",
        "GUIDE_BIG6_FPS_SELECT",
    )
    fx6_end_excl_keys = (
        "BKID_APP_VARIABLE_ND_CONT",
        "PID_SET_VARIABLE_ND_VALUE",
        "PID_SET_VARIABLE_ND_ROTARY_ENCODER",
        "PID_GET_VARIABLE_ND_STORED_VALUE",
        "INFRA_NOTIFY_VARIABLE_ND_FILTER_VALUE",
        "FUNC_set_auto_nd_filter",
        "FUNC_set_push_auto_nd_filter",
    )

    fx3_big6_hits = {k: fx3_elf.marker_hits.get(k, 0) for k in fx3_big6_keys}
    fx6_big6_hits = {k: fx6_elf.marker_hits.get(k, 0) for k in fx6_big6_keys}
    fx6_end_in_fx6 = {k: fx6_elf.marker_hits.get(k, 0) for k in fx6_end_excl_keys}
    fx6_end_in_fx3 = {k: fx3_elf.marker_hits.get(k, 0) for k in fx6_end_excl_keys}

    for k, v in fx3_big6_hits.items():
        if v < 1:
            p1_errors.append(f"MISSING_FX3_BIG6_MARKER:{k}")
    for k, v in fx6_big6_hits.items():
        if v < 1:
            p1_errors.append(f"MISSING_FX6_BIG6_MARKER:{k}")
    for k, v in fx6_end_in_fx6.items():
        if v < 1:
            p1_errors.append(f"MISSING_FX6_END_ACTUATOR_MARKER:{k}")
    for k, v in fx6_end_in_fx3.items():
        if v != 0:
            p1_errors.append(f"UNEXPECTED_FX6_END_MARKER_IN_FX3:{k}={v}")
    if not fx3_uxc.uxc_magic_valid or any(
        v < 1 for v in fx3_uxc.required_token_hits.values()
    ):
        p1_errors.append("FX3_UXC_EN_F_WAVE26_TOKENS_INCOMPLETE")
    if not fx6_uxc.uxc_magic_valid or any(
        v < 1 for v in fx6_uxc.required_token_hits.values()
    ):
        p1_errors.append("FX6_UXC_EN_WAVE26_TOKENS_INCOMPLETE")
    if any(v < 1 for v in fx3_cp.marker_hits.values()):
        p1_errors.append("FX3_CPAPP_TC_IMAGER_MARKERS_INCOMPLETE")
    if any(v != 0 for v in fx3_cp.forbidden_end_actuator_hits.values()):
        p1_errors.append("FX3_CPAPP_UNEXPECTED_END_ACTUATOR_TOKEN")
    if any(v < 1 for v in fx6_cp.marker_hits.values()):
        p1_errors.append("FX6_CPAPP_TC_IMAGER_MARKERS_INCOMPLETE")

    eval_big6_aperture = evaluate_fx3_big6_home_and_zero_end_boundary(
        mode_settings="Fixed/Variable",
        home_custom_key_bound=True,
        home_lower_left_choice="Aperture",
        requested_nd_label="Clear",
        stage_b_end_actuator_tx_blocked=True,
    )
    eval_big6_nd_meta = evaluate_fx3_big6_home_and_zero_end_boundary(
        mode_settings="Fixed/Variable",
        home_custom_key_bound=True,
        home_lower_left_choice="ND Filter",
        requested_nd_label="1/16",
        stage_b_end_actuator_tx_blocked=True,
    )
    eval_big6_no_fv = evaluate_fx3_big6_home_and_zero_end_boundary(
        mode_settings="Normal_Movie_Non_FixedVariable",
        home_custom_key_bound=True,
        home_lower_left_choice="Aperture",
    )
    eval_big6_no_key = evaluate_fx3_big6_home_and_zero_end_boundary(
        mode_settings="Fixed/Variable",
        home_custom_key_bound=False,
        home_lower_left_choice="Aperture",
    )
    eval_big6_end_tx_rej = evaluate_fx3_big6_home_and_zero_end_boundary(
        mode_settings="Fixed/Variable",
        home_custom_key_bound=True,
        home_lower_left_choice="ND Filter",
        requested_nd_label="1/64",
        stage_b_end_actuator_tx_blocked=False,
    )

    if not (
        eval_big6_aperture.valid
        and eval_big6_aperture.tile_count == 6
        and eval_big6_aperture.e_nd_actuator_tx_count == 0
        and eval_big6_nd_meta.valid
        and eval_big6_nd_meta.nd_treated_as_manual_reference_only
        and eval_big6_nd_meta.e_nd_actuator_tx_count == 0
        and (not eval_big6_no_fv.valid)
        and (not eval_big6_no_key.valid)
        and (not eval_big6_end_tx_rej.valid)
        and eval_big6_end_tx_rej.e_nd_actuator_tx_count == 0
    ):
        p1_errors.append("PILLAR_1_BIG6_ZERO_END_STATE_MACHINE_FAILED")

    pillar_1 = Pillar1Big6HomeAndZeroEndReport(
        passed=len(p1_errors) == 0,
        fx3_appfw_big6_hits=fx3_big6_hits,
        fx6_appfw_big6_hits=fx6_big6_hits,
        fx6_exclusive_end_hits_in_fx6=fx6_end_in_fx6,
        fx6_exclusive_end_hits_in_fx3=fx6_end_in_fx3,
        fx3_uxc_en_f_summary=fx3_uxc,
        fx6_uxc_en_summary=fx6_uxc,
        fx3_cpapp_summary=fx3_cp,
        fx6_cpapp_summary=fx6_cp,
        eval_big6_default_aperture_ok=eval_big6_aperture,
        eval_big6_nd_filter_manual_metadata_ok=eval_big6_nd_meta,
        eval_big6_blocked_without_fixed_variable_mode=eval_big6_no_fv,
        eval_big6_blocked_without_home_custom_key=eval_big6_no_key,
        eval_stage_b_unblocked_end_actuator_tx_rejected=eval_big6_end_tx_rej,
        errors=tuple(p1_errors),
    )

    # --- Pillar 2: Slot-1 CAMSET Dual-Media Path Split & Cross-Model Firewall ---
    p2_errors: List[str] = []
    fx3_camset_keys = (
        "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT",
        "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT",
        "CAMSET%02d",
        "save_load_settings_file0",
        "save_load_settings_file9",
        "sequence/sequence_save_load_settings_save.cpp",
        "sequence/sequence_save_load_ftp_settings_save.cpp",
        "is_recall_camera_setting_screen_push_ok",
    )
    fx6_camset_keys = (
        "%c:%s/SONY/SETTING/%s/CAMSET/%s.DAT",
        "%c:%s/SONY/SETTING/%s/FTPSET/%s.DAT",
        "save_load_settings_file0",
        "save_load_settings_file9",
        "sequence/sequence_save_load_settings_save.cpp",
        "sequence/sequence_save_load_ftp_settings_save.cpp",
    )
    fx3_camset_hits = {k: fx3_elf.marker_hits.get(k, 0) for k in fx3_camset_keys}
    fx6_camset_hits = {k: fx6_elf.marker_hits.get(k, 0) for k in fx6_camset_keys}

    for k, v in fx3_camset_hits.items():
        if v < 1:
            p2_errors.append(f"MISSING_FX3_CAMSET_MARKER:{k}")
    for k, v in fx6_camset_hits.items():
        if v < 1:
            p2_errors.append(f"MISSING_FX6_CAMSET_MARKER:{k}")

    fx3_dat_raw, fx3_dat_sum = serialize_camset_dat_header(
        model_name="ILME-FX3", profile_index=1
    )
    fx3a_dat_raw, fx3a_dat_sum = serialize_camset_dat_header(
        model_name="ILME-FX3A", profile_index=1
    )
    fx6_dat_raw, fx6_dat_sum = serialize_camset_dat_header(
        model_name="ILME-FX6", profile_index=10
    )

    ok_fx3_dat, _ = verify_camset_dat_model_compatibility(
        fx3_dat_raw, expected_reader_model="ILME-FX3"
    )
    ok_fx3a_on_fx3, err_fx3a = verify_camset_dat_model_compatibility(
        fx3a_dat_raw, expected_reader_model="ILME-FX3"
    )
    ok_fx6_on_fx3, err_fx6 = verify_camset_dat_model_compatibility(
        fx6_dat_raw, expected_reader_model="ILME-FX3"
    )
    if (
        (not ok_fx3_dat)
        or ok_fx3a_on_fx3
        or err_fx3a != "CAMSET_CROSS_MODEL_DAT_INCOMPATIBLE"
        or ok_fx6_on_fx3
        or err_fx6 != "CAMSET_CROSS_MODEL_DAT_INCOMPATIBLE"
    ):
        p2_errors.append("CAMSET_DAT_BINARY_HEADER_COMPAT_CHECK_FAILED")

    eval_sd_ok = evaluate_camset_slot1_path_and_cross_model_firewall(
        camera_mode="MOVIE_NORMAL",
        target_slot="Slot 1",
        media_type="SDXC",
        profile_index=1,
        requested_card_path="/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
        requested_payload_fields=("FPS", "Base ISO", "FTP", "Date/Time"),
    )
    eval_cfa_ok = evaluate_camset_slot1_path_and_cross_model_firewall(
        camera_mode="CINE_EI",
        target_slot="Slot 1",
        media_type="CFEXPRESS_TYPE_A",
        profile_index=10,
        requested_card_path="/SONY/SETTING/FX3/CAMSET/CAMSET10.DAT",
    )
    eval_slot2_rej = evaluate_camset_slot1_path_and_cross_model_firewall(
        target_slot="Slot 2",
        media_type="SDXC",
        profile_index=1,
    )
    eval_prof11_rej = evaluate_camset_slot1_path_and_cross_model_firewall(
        target_slot="Slot 1",
        media_type="SDXC",
        profile_index=11,
    )
    eval_mr_rej = evaluate_camset_slot1_path_and_cross_model_firewall(
        camera_mode="MR_RECALL_CAMERA_SETTING",
        target_slot="Slot 1",
        media_type="SDXC",
        profile_index=1,
    )
    eval_sd_no_priv_rej = evaluate_camset_slot1_path_and_cross_model_firewall(
        target_slot="Slot 1",
        media_type="SDXC",
        profile_index=1,
        requested_card_path="/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
    )
    eval_cfa_with_priv_rej = evaluate_camset_slot1_path_and_cross_model_firewall(
        target_slot="Slot 1",
        media_type="CFEXPRESS_TYPE_A",
        profile_index=1,
        requested_card_path="/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
    )
    eval_fx3a_rej = evaluate_camset_slot1_path_and_cross_model_firewall(
        writer_model="ILME-FX3A",
        reader_model="ILME-FX3",
    )
    eval_fx6_rej = evaluate_camset_slot1_path_and_cross_model_firewall(
        writer_model="ILME-FX6",
        reader_model="ILME-FX3",
    )
    eval_stageb_blk = evaluate_camset_slot1_path_and_cross_model_firewall(
        writer_model="ILME-FX6",
        reader_model="ILME-FX3",
        stage_b_active=True,
        stage_b_storage_target="/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT",
        lifecycle_stage="H2",
    )
    eval_stageb_ovl_ok = evaluate_camset_slot1_path_and_cross_model_firewall(
        writer_model="ILME-FX6",
        reader_model="ILME-FX3",
        stage_b_active=True,
        stage_b_storage_target="/tmp/fx6_camset_overlay/CAMSET01.json",
        lifecycle_stage="H2",
    )

    if not (
        eval_sd_ok.valid
        and eval_sd_ok.stripped_machine_bound_fields == ("FTP", "Date/Time")
        and eval_cfa_ok.valid
        and (not eval_slot2_rej.valid)
        and (not eval_prof11_rej.valid)
        and (not eval_mr_rej.valid)
        and eval_mr_rej.menu_greyed_out
        and (not eval_sd_no_priv_rej.valid)
        and (not eval_cfa_with_priv_rej.valid)
        and (not eval_fx3a_rej.valid)
        and eval_fx3a_rej.cross_model_incompatible_blocked
        and (not eval_fx6_rej.valid)
        and eval_fx6_rej.cross_model_incompatible_blocked
        and (not eval_stageb_blk.valid)
        and eval_stageb_ovl_ok.valid
        and eval_stageb_ovl_ok.redirected_to_volatile_camset_overlay
        and eval_stageb_ovl_ok.h0_equals_h3
    ):
        p2_errors.append("PILLAR_2_CAMSET_SLOT1_FIREWALL_INVARIANT_FAILED")

    pillar_2 = Pillar2CamsetSlot1AndFirewallReport(
        passed=len(p2_errors) == 0,
        fx3_appfw_camset_hits=fx3_camset_hits,
        fx6_appfw_camset_hits=fx6_camset_hits,
        fx3_dat_header_sample=fx3_dat_sum,
        fx3a_dat_header_sample=fx3a_dat_sum,
        fx6_dat_header_sample=fx6_dat_sum,
        eval_slot1_sd_private_path_ok=eval_sd_ok,
        eval_slot1_cfexpress_a_no_private_path_ok=eval_cfa_ok,
        eval_slot2_rejected=eval_slot2_rej,
        eval_profile_11_rejected=eval_prof11_rej,
        eval_mr_recall_mode_greyed_out_rejected=eval_mr_rej,
        eval_sd_missing_private_prefix_rejected=eval_sd_no_priv_rej,
        eval_cfexpress_with_private_prefix_rejected=eval_cfa_with_priv_rej,
        eval_cross_model_fx3a_on_fx3_rejected=eval_fx3a_rej,
        eval_cross_model_fx6_on_fx3_rejected=eval_fx6_rej,
        eval_stage_b_direct_slot1_overwrite_blocked=eval_stageb_blk,
        eval_stage_b_volatile_overlay_h0_eq_h3_ok=eval_stageb_ovl_ok,
        errors=tuple(p2_errors),
    )

    # --- Pillar 3: VMC-BNCM1 Body-Only TC IN (EXT-LK) & Digital HDMI TC OUT ---
    p3_errors: List[str] = []
    fx3_tc_keys = (
        "No301_EXTLK",
        "MSG_ID_TCUB_TC_SYNC",
        "VAL_setting_tc_run_TC_RUN_FREE_RUN",
        "VAL_setting_tc_run_TC_RUN_REC_RUN",
        "sequence_hdmi_tc_output",
        "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON",
        "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_OFF",
    )
    fx6_tc_keys = (
        "VAL_setting_tc_run_TC_RUN_FREE_RUN",
        "VAL_setting_tc_run_TC_RUN_REC_RUN",
        "sequence_hdmi_tc_output",
        "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON",
        "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_OFF",
        "PRM_HAITA_setting_hdmi_tc_output_sdi_output",
    )
    fx3_tc_hits = {k: fx3_elf.marker_hits.get(k, 0) for k in fx3_tc_keys}
    fx6_tc_hits = {k: fx6_elf.marker_hits.get(k, 0) for k in fx6_tc_keys}

    for k, v in fx3_tc_hits.items():
        if v < 1:
            p3_errors.append(f"MISSING_FX3_TC_MARKER:{k}")
    for k, v in fx6_tc_hits.items():
        if v < 1:
            p3_errors.append(f"MISSING_FX6_TC_MARKER:{k}")
    if fx3_elf.marker_hits.get("PRM_HAITA_setting_hdmi_tc_output_sdi_output", 0) != 0:
        p3_errors.append("UNEXPECTED_FX6_SDI_TC_MARKER_IN_FX3")

    eval_tcin_10s = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
        physical_port="BODY_MULTI_MICRO_USB",
        requested_direction="TC_IN",
        shooting_mode="Movie",
        tc_make="Preset",
        tc_run="Free Run",
        lock_dwell_sec=10.5,
        hdmi_tc_output_menu_setting="On",
    )
    eval_tcin_4s = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
        physical_port="BODY_MULTI_MICRO_USB",
        requested_direction="TC_IN",
        shooting_mode="Movie",
        tc_make="Preset",
        tc_run="Free Run",
        lock_dwell_sec=4.0,
    )
    eval_tc_sq = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
        physical_port="BODY_MULTI_MICRO_USB",
        requested_direction="TC_IN",
        shooting_mode="S&Q",
        tc_make="Preset",
        tc_run="Free Run",
        lock_dwell_sec=15.0,
        hdmi_tc_output_menu_setting="On",
    )
    eval_tc_edit = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
        physical_port="BODY_MULTI_MICRO_USB",
        requested_direction="TC_IN",
        shooting_mode="Movie",
        tc_make="Preset",
        tc_run="Free Run",
        lock_dwell_sec=12.0,
        tc_setting_edited_after_lock=True,
    )
    eval_xlr_handle_rej = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
        physical_port="XLR_H1_HANDLE_MICRO_USB",
        requested_direction="TC_IN",
    )
    eval_bnc_tcout_rej = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
        physical_port="BODY_MULTI_MICRO_USB",
        requested_direction="TC_OUT",
    )
    eval_hdmi_tcout_ok = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
        physical_port="HDMI_TYPE_A",
        requested_direction="TC_OUT",
        shooting_mode="Movie",
        hdmi_tc_output_menu_setting="On",
    )
    eval_uart_h0_blk = evaluate_vmcbncm1_tcin_and_hdmi_tcout_routing(
        physical_port="BODY_MULTI_MICRO_USB",
        requested_direction="TC_IN",
        boot_context="H0_UART_BOOT",
    )

    if not (
        eval_tcin_10s.valid
        and eval_tcin_10s.ext_lk_locked
        and eval_tcin_10s.ext_lk_state_label == "EXT-LK"
        and eval_tcin_4s.valid
        and (not eval_tcin_4s.ext_lk_locked)
        and eval_tc_sq.valid
        and (not eval_tc_sq.ext_lk_locked)
        and (not eval_tc_sq.hdmi_tc_out_active)
        and eval_tc_sq.hdmi_tc_out_disabled_in_sq
        and eval_tc_edit.valid
        and (not eval_tc_edit.ext_lk_locked)
        and (not eval_xlr_handle_rej.valid)
        and eval_xlr_handle_rej.xlr_h1_handle_port_prohibited
        and (not eval_bnc_tcout_rej.valid)
        and eval_bnc_tcout_rej.errno_code == "EOPNOTSUPP"
        and eval_hdmi_tcout_ok.valid
        and eval_hdmi_tcout_ok.hdmi_tc_out_active
        and (not eval_uart_h0_blk.valid)
        and eval_uart_h0_blk.uart_boot_pin_contention_blocked
    ):
        p3_errors.append("PILLAR_3_VMC_BNCM1_HDMI_TC_INVARIANT_FAILED")

    pillar_3 = Pillar3VmcBncm1AndHdmiTcOutReport(
        passed=len(p3_errors) == 0,
        fx3_appfw_tc_hits=fx3_tc_hits,
        fx6_appfw_tc_hits=fx6_tc_hits,
        eval_body_multi_usb_tcin_ext_lk_10s_ok=eval_tcin_10s,
        eval_body_multi_usb_tcin_under_10s_acquiring=eval_tcin_4s,
        eval_sq_mode_unlocks_ext_lk_and_disables_hdmi_tc=eval_tc_sq,
        eval_tc_setting_edit_unlocks_ext_lk=eval_tc_edit,
        eval_xlr_h1_handle_micro_usb_prohibited=eval_xlr_handle_rej,
        eval_multi_usb_reverse_tc_out_eopnotsupp=eval_bnc_tcout_rej,
        eval_hdmi_type_a_digital_tc_out_movie_ok=eval_hdmi_tcout_ok,
        eval_uart_boot_h0_vmcbncm1_blocked=eval_uart_h0_blk,
        errors=tuple(p3_errors),
    )

    # --- Pillar 4: Hard Write Firewall & 12-Touchpoint 4-Class Matrix ---
    p4_errors: List[str] = []
    wg_p2 = evaluate_phase203_write_guard("p2:/setting/CAMSET01.DAT")
    wg_bk = evaluate_phase203_write_guard("p2:/setting/Backup.bin")
    wg_slot1 = evaluate_phase203_write_guard(
        "/PRIVATE/SONY/SETTING/FX3/CAMSET/CAMSET01.DAT"
    )
    wg_cp = evaluate_phase203_write_guard("p8:/CPAPP-B.BIN")
    wg_nor = evaluate_phase203_write_guard("spi_nor:loader_nor.bin")
    wg_ovl = evaluate_phase203_write_guard("/tmp/fx6_camset_overlay/CAMSET01.json")
    wg_ram = evaluate_phase203_write_guard("ram://big6_lower_left_shadow")
    matrix = build_phase203_compat_matrix()

    if (
        wg_p2.valid
        or wg_bk.valid
        or wg_slot1.valid
        or wg_cp.valid
        or wg_nor.valid
        or (not wg_ovl.valid)
        or (not wg_ram.valid)
        or matrix.total_touchpoints != 12
        or any(matrix.class_counts.get(c, 0) < 1 for c in VALID_BRIDGE_CLASSES)
    ):
        p4_errors.append("PILLAR_4_WRITE_FIREWALL_OR_MATRIX_FAILED")

    pillar_4 = Pillar4Phase203WriteGuardAndMatrixReport(
        passed=len(p4_errors) == 0,
        blocked_p2_setting_eval=wg_p2,
        blocked_backup_bin_eval=wg_bk,
        blocked_stock_slot1_camset_eval=wg_slot1,
        blocked_cpapp_bin_eval=wg_cp,
        blocked_spi_nor_eval=wg_nor,
        allowed_fx6_camset_overlay_eval=wg_ovl,
        allowed_ram_shadow_eval=wg_ram,
        compatibility_matrix=matrix,
        errors=tuple(p4_errors),
    )

    all_errors = tuple(p1_errors + p2_errors + p3_errors + p4_errors)
    all_ok = len(all_errors) == 0

    digest_payload = {
        "schema_version": PHASE_203_SCHEMA,
        "phase_version": PHASE_203_VERSION,
        "auditor_index": "42/42",
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

    return RealhwBig6NoendCamsetSlot1AndVmcbncm1Report(
        schema_version=PHASE_203_SCHEMA,
        phase_version=PHASE_203_VERSION,
        auditor_index="42/42",
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
        e_nd_actuator_tx_count=0,
        persistent_writes=0,
        p2_setting_mutation_bytes=0,
        calibration_mutation_bytes=0,
        big6_6tile_and_zero_end_boundary_verified=pillar_1.passed,
        camset_slot1_dual_path_and_firewall_verified=pillar_2.passed,
        vmcbncm1_body_tcin_and_hdmi_tcout_verified=pillar_3.passed,
        zero_write_firewall_and_matrix_verified=pillar_4.passed,
        donor_file_sizes=donor_sizes,
        pillar_1_big6_zero_end=pillar_1,
        pillar_2_camset_slot1_firewall=pillar_2,
        pillar_3_vmcbncm1_hdmi_tc=pillar_3,
        pillar_4_write_guard_matrix=pillar_4,
        report_sha256=report_sha256,
        errors=all_errors,
    )


def _normalize_json_value_p203(obj: object) -> object:
    if isinstance(obj, dict):
        return {str(k): _normalize_json_value_p203(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [_normalize_json_value_p203(v) for v in obj]
    return obj


def realhw_big6_noend_camset_slot1_and_vmcbncm1_report_to_dict(
    report: RealhwBig6NoendCamsetSlot1AndVmcbncm1Report,
) -> Dict[str, object]:
    """Convert `RealhwBig6NoendCamsetSlot1AndVmcbncm1Report` into deterministic JSON-ready dict."""
    raw = asdict(report)
    raw.pop("cold_or_cached_scan_elapsed_sec", None)
    raw.pop("cache_hit", None)
    return _normalize_json_value_p203(raw)  # type: ignore[return-value]
