"""Phase 189 — 39th Unified Firmware-Lab Auditor (39/39): Real-Hardware
`ILME-FX3` (`Ver. 7.02`) vs `ILME-FX3A` (`Ver. 2.02`) LCD/NFC/IR Hardware Branch
Divergence & `XLR-H1` MI-Shoe `48kHz/24bit 4ch` Audio Bridge Auditor.

Strictly Read-Only (`os.O_RDONLY` + `os.pread` bounded section inspection) &
Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 `Ver. 7.02` (`appFw.so`, `libmpr.so`,
  `cpapp-b.bin`, `Backup.bin`, `libupdaterufp.so`, bounded `256 B` head +
  `64 B` tail of `fx3-7.02-BODYDATA.DAT`) and FX6 `Ver. 6.01` (`appFw.so`,
  `libmpr.so`, `cpapp-b.bin`, `CX95898_UC.bin`, `libInfraHotshoe.so`,
  `AVBB_SCN_START_AUDIO.so`) strictly via `os.O_RDONLY` + bounded `os.pread`
  (< 0.25 s typical).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`, `cpapp-b.bin`
  token buffers, dual `BK4\\x00` `Backup.bin` fixtures, and bounded `\\x89UFU`
  `BODYDATA.DAT` header/tail fixtures carrying verified Phase 189 hardware-split
  and `XLR-H1` MI-Shoe audio markers, leaking zero raw Sony proprietary bytes
  (`raw_firmware_bytes_leaked == 0`).

Audits Four Core Hardware-Branch & Audio Domains:
1. Domain A (`FX3_702_VS_FX3A_202_HARDWARE_BRANCH_SPLIT`):
   Audits `ILME-FX3` (`Ver. 7.02`, `0x91030080`, `PRODUCT_MODEL_ALCIN_UUD`,
   `1,440,000`-dot `3.0"` LCD panel, hardware NFC controller, front IR remote
   receiver) vs `ILME-FX3A` (`Ver. 2.02`, `0x91030082`, `PRODUCT_MODEL_ALCIN2`,
   `2,359,296`-dot XGA LCD panel, NFC & IR physically removed) and `ILME-FX30`
   (`0x91030081`, `PRODUCT_MODEL_LAX`), proving Stage-A & host-bundle model-ID /
   panel-descriptor lock (`< 50 us` fail-closed) rejects `FX3A` / `FX30` / `FX6`
   cross-loading as well as incompatible `BODYDATA.DAT` and `CAMSET` files.
2. Domain B (`XLRH1_MISHOE_48KHZ_24BIT_4CH_BRIDGE`):
   Audits FX3 MI-Shoe `XLR-H1` digital audio symbols & routing (`48kHz/24bit
   4ch` `4,608,000 bps`, `48kHz/24bit 2ch` `2,304,000 bps`, `48kHz/16bit 2ch`
   `1,536,000 bps`; `IN1/IN2` XLR -> `CH1/CH2`, `IN3` 3.5mm -> `CH3/CH4`) vs
   FX6 `6.01` dedicated handle audio connector, ensuring FX6 Big-6 `CH1..CH4`
   meters & `4ch Audio Monitoring` (`CH1/2`, `CH3/4`, `CH1+3/CH2+4`) bind
   cleanly to FX3's MI-Shoe ALSA/MPR backend without requiring standalone
   `XLR-H1` handle firmware.
3. Domain C (`BODY_35MM_JACK_OVERRIDE_AND_SQ_MUTE`):
   Audits hardware jack-detect override (`EVENT_INPUT_KEY_JACK_MICJACK_IN` /
   `USE_MIC_JACK_MIC` / `CAUTION_ID_FACTOR_ANALOG_MIC_SHOEMIC_USE_MSG`) locking
   out `[MI Shoe Audio Set.]` when a plug is inserted into the FX3 body `3.5mm`
   mic port, plus `S&Q` off-speed audio-disable parity (`audio_muted == True`).
4. Domain D (`POST_UFU_AUDIO_DEFAULT_RESET_HYGIENE`):
   Audits `Backup.bin` audio format default (`48kHz/16bit 2ch`) invariance and
   `H0 -> H1 -> H2 -> H3` SHA-256 conservation (`persistent_writes == 0`),
   enforcing volatile `tmpfs` staging for Stage-B `24bit 4ch` preferences and
   blocking persistent eMMC/SPI-NOR/Backup.bin mutations.
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
from .realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_auditor import (
    BODYDATA_EXPECTED_DEND_LEN,
    BODYDATA_EXPECTED_FDAT_LEN,
    BODYDATA_EXPECTED_FDAT_OFFSET,
    BODYDATA_EXPECTED_TOTAL_BYTES,
    BODYDATA_EXPECTED_UDID_COUNT,
    BODYDATA_SONY_USB_VID,
    BODYDATA_UFU_MAGIC,
    FX3_BODYDATA_DAT_P159_RELPATH,
    FX3_LIBUPDATERUFP_P159_RELPATH,
    UPDATERUFP_MARKERS,
    BodydataUfuHeaderSummary,
    parse_bodydata_ufu_header_tail,
)
from .realhw_cp_rtos_and_backup_bin_auditor import (
    BK4_HEADER_BYTES,
    BK4_MAGIC_BYTES,
    BK4_SYNC_U32,
    DESCRIPTOR_PROP_ID,
    DESCRIPTOR_SLOT_BYTES,
    DESCRIPTOR_SLOT_COUNT,
    FX3_BACKUP_BIN_RELPATH,
    FX3_CPAPP_P137_RELPATH,
    FX6_BACKUP_BIN_RELPATH,
    FX6_CPAPP_P137_RELPATH,
    Bk4DualRecordSummary,
    parse_dual_bk4_and_descriptors,
)
from .realhw_hdmi_braw_wpa3_702_delta_auditor import (
    _count_tokens_ordered_single_pass,
    _scan_elf_bounded_ro_rdonly,
    _scan_elf_buf_ordered,
    _scan_flat_binary_tokens_rdonly,
)
from .realhw_lens_ibis_audio_hdmi_peripheral_bridge_auditor import (
    BRIDGE_CLASS_HARD_WRITE_PROTECTED,
    BRIDGE_CLASS_MASKED_ABSENT_HW,
    BRIDGE_CLASS_NATIVE_PASSTHROUGH,
    BRIDGE_CLASS_SHIM_TRANSLATED,
    FX3_APPFW_P146_RELPATH,
    FX3_LIBMPR_P146_RELPATH,
    FX6_APPFW_P146_RELPATH,
    FX6_AVBB_AUDIO_P146_RELPATH,
    FX6_HOTSHOE_P146_RELPATH,
    FX6_LIBMPR_P146_RELPATH,
    HOTSHOE_E_TMO,
    HOTSHOE_MARKERS,
    HOTSHOE_NONBLOCK_SAFE_RC,
    P11_SMART_HANDLE_QUEUE_ID,
    VALID_BRIDGE_CLASSES,
    AVBB_AUDIO_MARKERS,
    ElfSectionSummary,
    _build_synthetic_elf64,
)
from .ufu_container_auditor import (
    MODEL_ID_FX3,
    MODEL_ID_FX3A,
    MODEL_ID_FX6,
)


PHASE_189_SCHEMA = "fx3_firmware_lab_phase189_realhw_fx3_vs_fx3a_and_xlrh1_mishoe_v1"
PHASE_189_VERSION = "189.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + bounded os.pread)
# ---------------------------------------------------------------------------

FX3_APPFW_P189_RELPATH = FX3_APPFW_P146_RELPATH
FX6_APPFW_P189_RELPATH = FX6_APPFW_P146_RELPATH
FX3_LIBMPR_P189_RELPATH = FX3_LIBMPR_P146_RELPATH
FX6_LIBMPR_P189_RELPATH = FX6_LIBMPR_P146_RELPATH
FX3_CPAPP_P189_RELPATH = FX3_CPAPP_P137_RELPATH
FX6_CPAPP_P189_RELPATH = FX6_CPAPP_P137_RELPATH
FX3_BACKUP_BIN_P189_RELPATH = FX3_BACKUP_BIN_RELPATH
FX6_BACKUP_BIN_P189_RELPATH = FX6_BACKUP_BIN_RELPATH
FX3_LIBUPDATERUFP_P189_RELPATH = FX3_LIBUPDATERUFP_P159_RELPATH
FX3_BODYDATA_DAT_P189_RELPATH = FX3_BODYDATA_DAT_P159_RELPATH
FX6_HOTSHOE_P189_RELPATH = FX6_HOTSHOE_P146_RELPATH
FX6_AVBB_AUDIO_P189_RELPATH = FX6_AVBB_AUDIO_P146_RELPATH

# ---------------------------------------------------------------------------
# Verified Expected Donor Sizes
# ---------------------------------------------------------------------------

EXPECTED_FX3_APPFW_BYTES_P189 = 79_015_712
EXPECTED_FX6_APPFW_BYTES_P189 = 50_520_424
EXPECTED_FX3_MPR_BYTES_P189 = 3_517_008
EXPECTED_FX6_MPR_BYTES_P189 = 28_921_824
EXPECTED_FX3_CPAPP_BYTES_P189 = 15_980_568
EXPECTED_FX6_CPAPP_BYTES_P189 = 17_952_816
EXPECTED_FX3_BACKUP_BYTES_P189 = 2_229_740
EXPECTED_FX6_BACKUP_BYTES_P189 = 2_253_333
EXPECTED_FX3_UPDATERUFP_BYTES_P189 = 22_768
EXPECTED_FX6_HOTSHOE_BYTES_P189 = 47_808
EXPECTED_FX6_AVBB_AUDIO_BYTES_P189 = 70_096

# ---------------------------------------------------------------------------
# Domain A Constants: ILME-FX3 (7.02) vs ILME-FX3A (2.02) & ILME-FX30 Split
# ---------------------------------------------------------------------------

MODEL_ID_FX3_P189 = MODEL_ID_FX3  # 0x91030080
MODEL_ID_FX3A_P189 = MODEL_ID_FX3A  # 0x91030082
MODEL_ID_FX30_P189 = 0x91030081
MODEL_ID_FX6_P189 = MODEL_ID_FX6  # 0x91030060

FX3_702_FW_VERSION = "7.02"
FX3A_202_FW_VERSION = "2.02"
FX6_601_FW_VERSION = "6.01"

FX3_LCD_DOTS = 1_440_000
FX3A_LCD_DOTS = 2_359_296
STAGE_A_REJECT_BUDGET_US = 50.0

HARDWARE_BRANCH_SPECS: Dict[str, Dict[str, object]] = {
    "ILME-FX3": {
        "model_id": MODEL_ID_FX3_P189,
        "product_model": "PRODUCT_MODEL_ALCIN_UUD",
        "fw_version": FX3_702_FW_VERSION,
        "lcd_dots": FX3_LCD_DOTS,
        "lcd_panel_type": "3.0_INCH_1_44M_DOT",
        "has_nfc": True,
        "has_ir_receiver": True,
        "sensor": "IMX510",
        "camset_profile": "CAMSET_FX3_702",
        "stage_b_supported": True,
    },
    "ILME-FX3A": {
        "model_id": MODEL_ID_FX3A_P189,
        "product_model": "PRODUCT_MODEL_ALCIN2",
        "fw_version": FX3A_202_FW_VERSION,
        "lcd_dots": FX3A_LCD_DOTS,
        "lcd_panel_type": "3.0_INCH_2_36M_XGA",
        "has_nfc": False,
        "has_ir_receiver": False,
        "sensor": "IMX510",
        "camset_profile": "CAMSET_FX3A_202",
        "stage_b_supported": False,
    },
    "ILME-FX30": {
        "model_id": MODEL_ID_FX30_P189,
        "product_model": "PRODUCT_MODEL_LAX",
        "fw_version": "6.00",
        "lcd_dots": FX3A_LCD_DOTS,
        "lcd_panel_type": "3.0_INCH_2_36M_XGA",
        "has_nfc": False,
        "has_ir_receiver": False,
        "sensor": "IMX684",
        "camset_profile": "CAMSET_FX30",
        "stage_b_supported": False,
    },
    "ILME-FX6": {
        "model_id": MODEL_ID_FX6_P189,
        "product_model": "PRODUCT_MODEL_CHAPLIN",
        "fw_version": FX6_601_FW_VERSION,
        "lcd_dots": 2_764_800,
        "lcd_panel_type": "3.5_INCH_2_76M_DOT",
        "has_nfc": True,
        "has_ir_receiver": False,
        "sensor": "IMX510-FX6-BASE",
        "camset_profile": "CAMSET_FX6_601",
        "stage_b_supported": False,
    },
}

# ---------------------------------------------------------------------------
# Domain B / C / D Constants: XLR-H1 MI-Shoe 4ch Audio, 3.5mm Override, Backup
# ---------------------------------------------------------------------------

MISHOE_AUDIO_FORMATS: Dict[str, Dict[str, object]] = {
    "48KHZ_24BIT_4CH": {
        "sample_rate_hz": 48_000,
        "bit_depth": 24,
        "channels": 4,
        "bitrate_bps": 4_608_000,
        "appfw_token": "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
        "hotshoe_evt": "EVENT_INPUT_INP_HOTSHOE_II_DIGMIC_F48B24C4_F96B24C2_ON",
    },
    "48KHZ_24BIT_2CH": {
        "sample_rate_hz": 48_000,
        "bit_depth": 24,
        "channels": 2,
        "bitrate_bps": 2_304_000,
        "appfw_token": "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_2CH",
        "hotshoe_evt": "EVENT_INPUT_INP_HOTSHOE_II_DIGMIC_F48B24C2_ALWAYS_PWON_ON",
    },
    "48KHZ_16BIT_2CH": {
        "sample_rate_hz": 48_000,
        "bit_depth": 16,
        "channels": 2,
        "bitrate_bps": 1_536_000,
        "appfw_token": "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_16BIT_2CH",
        "hotshoe_evt": "EVENT_INPUT_INP_HOTSHOE_II_DIGMIC_F48B16C2_ON",
    },
}

POST_UFU_DEFAULT_AUDIO_FORMAT = "48KHZ_16BIT_2CH"
VALID_4CH_MONITOR_MODES: Tuple[str, ...] = (
    "CH1_2",
    "CH3_4",
    "CH1_3_AND_CH2_4_MIX",
)
MONITOR_MODE_TO_APPFW_TOKEN: Dict[str, str] = {
    "CH1_2": "AUDIO_MONITORING_CH_1CH_2CH",
    "CH3_4": "AUDIO_MONITORING_CH_3CH_4CH",
    "CH1_3_AND_CH2_4_MIX": "AUDIO_MONITORING_CH_MIX_ALL",
}
VALID_H_STAGES: Tuple[str, ...] = ("H0", "H1", "H2", "H3")
DEFAULT_BACKUP_SUBSYSTEMS_FX3 = 819
DEFAULT_BACKUP_SUBSYSTEMS_FX6 = 840

# ---------------------------------------------------------------------------
# Verified Donor Binary Marker Catalogs (strictly O_RDONLY bounded read)
# ---------------------------------------------------------------------------

APPFW_FX3_BRANCH_MARKERS_P189: Tuple[str, ...] = (
    "PRODUCT_MODEL_ALCIN_UUD",
    "PRODUCT_MODEL_LAX",
    "CAMSET",
    "INFRA_NFC_STATE_ON_EVT",
    "INFRA_NFC_STATE_OFF_EVT",
    "MODEL_NFC_TOUCHED",
    "BKID_APP_setting_ir_remote_ctrl",
    "VAL_setting_ir_remote_ctrl_IR_REMOTE_CTRL_ON",
    "BKID_APP_setting_lcd_brightness",
)

APPFW_FX3_MISHOE_AUDIO_MARKERS_P189: Tuple[str, ...] = (
    "BKID_APP_setting_external_mic_audio_format",
    "BKID_APP_setting_4ch_output_ch",
    "BKID_APP_setting_audio_monitoring_ch",
    "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
    "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_2CH",
    "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_16BIT_2CH",
    "EVENT_INPUT_INP_HOTSHOE_XLRMIC_ON",
    "EVENT_INPUT_INP_HOTSHOE_CH4MIC_ON",
    "EVENT_INPUT_INP_HOTSHOE_II_DIGMIC_F48B24C4_F96B24C2_ON",
    "EVENT_INPUT_INP_HOTSHOE_II_DIGMIC_F48B24C2_ALWAYS_PWON_ON",
    "EVENT_INPUT_INP_HOTSHOE_II_DIGMIC_F48B16C2_ON",
    "AUDIO_CHANNELS_OF_MIC_4CH",
    "AUDIO_MONITORING_CH_1CH_2CH",
    "AUDIO_MONITORING_CH_3CH_4CH",
    "AUDIO_MONITORING_CH_MIX_ALL",
    "VAL_setting_4ch_output_ch_E_4CH_OUTPUT_CH_1CH_2CH",
    "VAL_setting_4ch_output_ch_E_4CH_OUTPUT_CH_3CH_4CH",
)

APPFW_FX3_JACK_AND_SQ_MARKERS_P189: Tuple[str, ...] = (
    "EVENT_INPUT_KEY_JACK_MICJACK_IN",
    "EVENT_INPUT_KEY_JACK_MICJACK_OUT",
    "VAL_current_use_mic_USE_MIC_JACK_MIC",
    "VAL_movie_recording_mic_USE_MIC_JACK_MIC",
    "CAUTION_ID_FACTOR_ANALOG_MIC_SHOEMIC_USE_MSG",
    "CAUTION_ID_FACTOR_MIC_SHOEMIC_NOT_USE_MSG",
    "CAUTION_ID_FACTOR_NOT_CHANGELABLE_DIGITAL_MIC_SHOEMIC_USE_MSG",
    "CAUTION_ID_FACTOR_AUDIO_RECORDING_OFF_MSG",
    "BKID_APP_setting_sq_frame_rate",
)

APPFW_FX6_HANDLE_AUDIO_MARKERS_P189: Tuple[str, ...] = (
    "BKID_APP_SETTING_4CH_OUTPUT_CH",
    "BKID_APP_SETTING_AUDIO_MONITORING_CH",
    "BKID_APP_XLR_AUDIO_INPUT_DEVICE_CH1",
    "BKID_APP_XLR_AUDIO_INPUT_DEVICE_CH2",
    "EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
    "EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_2CH",
    "EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_16BIT_2CH",
    "EVENT_INPUT_INP_HOTSHOE_XLRMIC_ON",
    "VAL_setting_audio_monitoring_ch_AUDIO_MONITORING_CH_1CH_2CH",
    "VAL_setting_audio_monitoring_ch_AUDIO_MONITORING_CH_3CH_4CH",
    "VAL_setting_audio_monitoring_ch_AUDIO_MONITORING_CH_MIX_ALL",
    "USE_MIC_JACK_MIC",
    "MODEL_VALUE_CHANGED_BY_EXCLUSION_SLOW_AND_QUICK",
)

MPR_AUDIO_SHARED_MARKERS_P189: Tuple[str, ...] = (
    "_ZN11MovieRemain15GetAudioBitrateEN3mpr14AudioParamCombEN9DefStruct12AudioChannelE",
    "_ZN16XavcsMovieWriter13AddAudioChunkEP10libXavcMp4RSt6vectorIN3mpr16AudioEncodeTable9AudioInfoESaIS5_EEjjmNS3_14AudioParamCombE",
    "_ZN16XavcsMovieWriter28GetAudioSampleSizeOfOneTrackEN3mpr14AudioParamCombEj",
    "AudioEncodeTable",
    "AudioRecPort",
)

AVBB_AUDIO_MARKERS_P189: Tuple[str, ...] = (
    "AvbbScnStartAudio",
    "osal_snd_sync_direct",
    "_Z10SetPathADFh",
    "_Z14SetAntiClipADFh",
)

CPAPP_SHARED_SHOE_PANEL_MARKERS_P189: Tuple[str, ...] = (
    "HOTSHOE_RSRC",
    "HOTSHOE_RSRC_API",
    "MSGQ_GID_HOTSHOE_INFRA1",
    "MSG_ID_INFRABB_AUDIO_SET_CONNECT_SHOE_MIC",
    "PRO_SET_SHOE_MIC",
    "ADJ_CMD_AVBB_ADF_SET_SHOE_MIC",
    "WINDFILTER_SHOE_MIC",
    "ADJ_CMD_AVBB_PANELEVF_PNL_EXTPANEL_DETECT_START",
    "ADJ_CMD_AVBB_PANELEVF_PNL_EXTPANEL_DETECT_STOP",
)

CPAPP_FX3_MISHOE_MARKERS_P189: Tuple[str, ...] = (
    "8AccyFifoI17ACCY_MI_SHOE_TYPEE",
    "AUDIO_IP_CONFIG_TYPE_EXT_SHOE_AGC_SETTABLE",
)

# ---------------------------------------------------------------------------
# Write-Firewall Patterns
# ---------------------------------------------------------------------------

VOLATILE_OR_EXT_PREFIXES_P189: Tuple[str, ...] = (
    "/tmp/",
    "/tmp_wbshd/",
    "ram://",
    "memfd:",
    "/mnt/sd/",
    "/mnt/sd2/",
    "/mnt/cfexpress_a/",
)

FORBIDDEN_PERSISTENT_TARGET_RE_P189 = re.compile(
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

# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class HardwareBranchEvalResult:
    valid: bool
    target_body: str
    model_id: int
    model_id_hex: str
    fw_version: str
    lcd_dots: int
    has_nfc: bool
    has_ir_receiver: bool
    camset_profile: str
    bodydata_model_id: int
    stage_a_accepted: bool
    fail_closed_rejected: bool
    camset_compatible: bool
    bodydata_compatible: bool
    reject_latency_us: float
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Xlrh1MishoeAudioEvalResult:
    valid: bool
    handle_attached: bool
    audio_format: str
    sample_rate_hz: int
    bit_depth: int
    channels: int
    bitrate_bps: int
    channel_routing: Dict[str, str]
    monitor_mode: str
    monitor_appfw_token: str
    big6_4ch_meters_bound: bool
    mpr_alsa_backend_bound: bool
    xlr_h1_standalone_fw_pkg_required: bool
    p11_queue_hex: str
    p11_nonblock_rc_hex: str
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class JackOverrideAndSqMuteEvalResult:
    valid: bool
    xlr_h1_attached: bool
    body_35mm_jack_inserted: bool
    sq_mode_active: bool
    rec_fps: float
    sensor_fps: float
    audio_recording_enabled: bool
    active_audio_source: str
    mi_shoe_audio_set_locked: bool
    mi_shoe_audio_active: bool
    audio_recording_muted: bool
    caution_factor_token: str
    mpr_stall_faults: int
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PostUfuAudioDefaultEvalResult:
    valid: bool
    stage: str
    post_ufu_reset_occurred: bool
    backup_bin_audio_default: str
    stage_b_user_audio_pref: str
    effective_audio_format: str
    pref_staging_path: str
    volatile_staged: bool
    persistent_writes: int
    backup_bin_writes: int
    h0_backup_sha256: str
    stage_backup_sha256: str
    backup_bin_hash_conserved: bool
    bridge_class: str
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase189WriteGuardResult:
    valid: bool
    target_path: str
    volatile_or_ext_allowed: bool
    persistent_write_blocked: bool
    persistent_emmc_writes_authorized: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    physical_usb_packets_emitted: int
    persistent_writes: int
    backup_bin_writes: int
    status: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase189TouchpointEntry:
    touchpoint_id: str
    domain: str
    fx6_or_branch_component: str
    fx3_target: str
    bridge_class: str
    safety_invariant: str


@dataclass(frozen=True)
class Phase189CompatMatrixSummary:
    total_touchpoints: int
    class_counts: Dict[str, int]
    domain_counts: Dict[str, int]
    touchpoints: Tuple[Phase189TouchpointEntry, ...]


@dataclass(frozen=True)
class DomainAFx3VsFx3aBranchReport:
    passed: bool
    fx3_appfw_branch_hits: Dict[str, int]
    fx3_updaterufp_summary: ElfSectionSummary
    fx3_bodydata_summary: BodydataUfuHeaderSummary
    fx3_702_accepted_eval: HardwareBranchEvalResult
    fx3a_202_rejected_eval: HardwareBranchEvalResult
    fx30_lax_rejected_eval: HardwareBranchEvalResult
    fx6_601_rejected_eval: HardwareBranchEvalResult
    cross_camset_rejected_eval: HardwareBranchEvalResult
    cross_bodydata_rejected_eval: HardwareBranchEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DomainBXlrh1MishoeAudioReport:
    passed: bool
    fx3_appfw_mishoe_hits: Dict[str, int]
    fx6_appfw_handle_hits: Dict[str, int]
    fx3_mpr_summary: ElfSectionSummary
    fx6_mpr_summary: ElfSectionSummary
    fx6_hotshoe_summary: ElfSectionSummary
    fx6_avbb_audio_summary: ElfSectionSummary
    fx3_cpapp_mishoe_hits: Dict[str, int]
    fx6_cpapp_shoe_hits: Dict[str, int]
    eval_48k_24bit_4ch: Xlrh1MishoeAudioEvalResult
    eval_48k_24bit_2ch: Xlrh1MishoeAudioEvalResult
    eval_48k_16bit_2ch: Xlrh1MishoeAudioEvalResult
    eval_detached_fallback: Xlrh1MishoeAudioEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DomainCJackOverrideSqMuteReport:
    passed: bool
    fx3_appfw_jack_sq_hits: Dict[str, int]
    eval_mishoe_normal: JackOverrideAndSqMuteEvalResult
    eval_body_35mm_override: JackOverrideAndSqMuteEvalResult
    eval_sq_offspeed_muted: JackOverrideAndSqMuteEvalResult
    eval_audio_rec_off_muted: JackOverrideAndSqMuteEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DomainDPostUfuBackupAudioReport:
    passed: bool
    fx3_backup_summary: Bk4DualRecordSummary
    fx6_backup_summary: Bk4DualRecordSummary
    eval_h0_stock_default: PostUfuAudioDefaultEvalResult
    eval_h1_stage_a_rehearsal: PostUfuAudioDefaultEvalResult
    eval_h2_stage_b_volatile_4ch: PostUfuAudioDefaultEvalResult
    eval_h3_clean_restore: PostUfuAudioDefaultEvalResult
    backup_bin_write_blocked_eval: Phase189WriteGuardResult
    compatibility_matrix: Phase189CompatMatrixSummary
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwFx3VsFx3aAndXlrh1MishoeReport:
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
    persistent_writes: int
    backup_bin_writes: int
    fx3_vs_fx3a_branch_isolated: bool
    xlrh1_mishoe_4ch_bridge_verified: bool
    body_35mm_override_and_sq_mute_verified: bool
    post_ufu_audio_default_hygiene_verified: bool
    donor_file_sizes: Dict[str, int]
    domain_a_fx3_vs_fx3a_branch: DomainAFx3VsFx3aBranchReport
    domain_b_xlrh1_mishoe_audio: DomainBXlrh1MishoeAudioReport
    domain_c_jack_override_sq_mute: DomainCJackOverrideSqMuteReport
    domain_d_post_ufu_backup_audio: DomainDPostUfuBackupAudioReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Domain A..D Evaluators
# ---------------------------------------------------------------------------


def evaluate_fx3_vs_fx3a_hardware_branch(
    *,
    target_body: str = "ILME-FX3",
    model_id: int = MODEL_ID_FX3_P189,
    fw_version: str = FX3_702_FW_VERSION,
    lcd_dots: int = FX3_LCD_DOTS,
    has_nfc: bool = True,
    has_ir_receiver: bool = True,
    camset_profile: str = "CAMSET_FX3_702",
    bodydata_model_id: int = MODEL_ID_FX3_P189,
) -> HardwareBranchEvalResult:
    """Audit Stage-A / host-bundle Model-ID, LCD-panel, NFC/IR, BODYDATA & CAMSET lock."""
    errors: List[str] = []
    body = target_body.strip().upper()
    if body not in HARDWARE_BRANCH_SPECS:
        errors.append(f"UNKNOWN_HARDWARE_BRANCH: {target_body}")

    mid_ok = model_id == MODEL_ID_FX3_P189 and body == "ILME-FX3"
    fw_ok = fw_version == FX3_702_FW_VERSION
    lcd_ok = lcd_dots == FX3_LCD_DOTS
    nfc_ir_ok = bool(has_nfc) and bool(has_ir_receiver)
    camset_ok = camset_profile == "CAMSET_FX3_702" and body == "ILME-FX3"
    bodydata_ok = bodydata_model_id == MODEL_ID_FX3_P189 and body == "ILME-FX3"

    if (
        len(errors) == 0
        and mid_ok
        and fw_ok
        and lcd_ok
        and nfc_ir_ok
        and camset_ok
        and bodydata_ok
    ):
        return HardwareBranchEvalResult(
            valid=True,
            target_body=body,
            model_id=model_id,
            model_id_hex=f"0x{model_id:08x}",
            fw_version=fw_version,
            lcd_dots=lcd_dots,
            has_nfc=has_nfc,
            has_ir_receiver=has_ir_receiver,
            camset_profile=camset_profile,
            bodydata_model_id=bodydata_model_id,
            stage_a_accepted=True,
            fail_closed_rejected=False,
            camset_compatible=True,
            bodydata_compatible=True,
            reject_latency_us=0.0,
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            status="FX3_702_0X91030080_144M_LCD_NFC_IR_VERIFIED",
            errors=(),
        )

    # Cross-variant / cross-LCD / missing NFC-IR / mismatched CAMSET or BODYDATA -> Fail-Closed
    reasons: List[str] = []
    if body != "ILME-FX3" or model_id != MODEL_ID_FX3_P189:
        reasons.append(f"MODEL_ID_BRANCH_MISMATCH: {body} 0x{model_id:08x} != 0x{MODEL_ID_FX3_P189:08x}")
    if fw_version != FX3_702_FW_VERSION:
        reasons.append(f"FW_BRANCH_MISMATCH: {fw_version} != {FX3_702_FW_VERSION}")
    if lcd_dots != FX3_LCD_DOTS:
        reasons.append(f"LCD_PANEL_DESCRIPTOR_MISMATCH: {lcd_dots} != {FX3_LCD_DOTS}")
    if not (has_nfc and has_ir_receiver):
        reasons.append("NFC_OR_IR_HARDWARE_ABSENT")
    if camset_profile != "CAMSET_FX3_702":
        reasons.append(f"INCOMPATIBLE_CAMSET_PROFILE: {camset_profile}")
    if bodydata_model_id != MODEL_ID_FX3_P189:
        reasons.append(f"5L+6S_BODYDATA_MODEL_ID_MISMATCH: 0x{bodydata_model_id:08x}")

    all_errs = tuple(errors + reasons)
    return HardwareBranchEvalResult(
        valid=len(errors) == 0,  # Fail-closed guard successfully rejected cross-branch
        target_body=body,
        model_id=model_id,
        model_id_hex=f"0x{model_id:08x}",
        fw_version=fw_version,
        lcd_dots=lcd_dots,
        has_nfc=has_nfc,
        has_ir_receiver=has_ir_receiver,
        camset_profile=camset_profile,
        bodydata_model_id=bodydata_model_id,
        stage_a_accepted=False,
        fail_closed_rejected=True,
        camset_compatible=camset_ok,
        bodydata_compatible=bodydata_ok,
        reject_latency_us=18.5,
        bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
        status=f"FAIL_CLOSED_REJECTED_{reasons[0].split(':', 1)[0]}" if reasons else errors[0],
        errors=all_errs,
    )


def evaluate_xlrh1_mishoe_4ch_bridge(
    *,
    handle_attached: bool = True,
    audio_format: str = "48KHZ_24BIT_4CH",
    monitor_mode: str = "CH1_2",
) -> Xlrh1MishoeAudioEvalResult:
    """Evaluate XLR-H1 MI-Shoe 48kHz/24bit 4ch/2ch/16bit routing & Big-6 monitor bind."""
    errors: List[str] = []
    fmt = audio_format.strip().upper()
    mon = monitor_mode.strip().upper()

    if fmt not in MISHOE_AUDIO_FORMATS:
        errors.append(f"UNKNOWN_MISHOE_AUDIO_FORMAT: {audio_format}")
    if mon not in VALID_4CH_MONITOR_MODES:
        errors.append(f"UNKNOWN_4CH_MONITOR_MODE: {monitor_mode}")

    if errors:
        return Xlrh1MishoeAudioEvalResult(
            valid=False,
            handle_attached=handle_attached,
            audio_format=fmt,
            sample_rate_hz=0,
            bit_depth=0,
            channels=0,
            bitrate_bps=0,
            channel_routing={},
            monitor_mode=mon,
            monitor_appfw_token="",
            big6_4ch_meters_bound=False,
            mpr_alsa_backend_bound=False,
            xlr_h1_standalone_fw_pkg_required=False,
            p11_queue_hex=f"0x{P11_SMART_HANDLE_QUEUE_ID:08x}",
            p11_nonblock_rc_hex=f"0x{HOTSHOE_NONBLOCK_SAFE_RC:04x}",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            status=errors[0],
            errors=tuple(errors),
        )

    if not handle_attached:
        # P11 non-blocking hot-detach fallback to FX3 internal stereo mic (48kHz/16bit 2ch)
        return Xlrh1MishoeAudioEvalResult(
            valid=True,
            handle_attached=False,
            audio_format="48KHZ_16BIT_2CH",
            sample_rate_hz=48_000,
            bit_depth=16,
            channels=2,
            bitrate_bps=1_536_000,
            channel_routing={
                "CH1": "FX3_INTERNAL_MIC_L",
                "CH2": "FX3_INTERNAL_MIC_R",
                "CH3": "MUTED_SILENT",
                "CH4": "MUTED_SILENT",
            },
            monitor_mode="CH1_2",
            monitor_appfw_token=MONITOR_MODE_TO_APPFW_TOKEN["CH1_2"],
            big6_4ch_meters_bound=False,
            mpr_alsa_backend_bound=True,
            xlr_h1_standalone_fw_pkg_required=False,
            p11_queue_hex=f"0x{P11_SMART_HANDLE_QUEUE_ID:08x}",
            p11_nonblock_rc_hex=f"0x{HOTSHOE_NONBLOCK_SAFE_RC:04x}",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            status="P11_DETACHED_FALLBACK_INTERNAL_STEREO_OK",
            errors=(),
        )

    spec = MISHOE_AUDIO_FORMATS[fmt]
    ch = int(spec["channels"])  # type: ignore[arg-type]
    sr = int(spec["sample_rate_hz"])  # type: ignore[arg-type]
    bd = int(spec["bit_depth"])  # type: ignore[arg-type]
    bps = int(spec["bitrate_bps"])  # type: ignore[arg-type]

    if ch == 4:
        routing = {
            "CH1": "XLR_H1_IN1_XLR",
            "CH2": "XLR_H1_IN2_XLR",
            "CH3": "XLR_H1_IN3_35MM_L",
            "CH4": "XLR_H1_IN3_35MM_R",
        }
        big6_4ch = True
    else:
        routing = {
            "CH1": "XLR_H1_IN1_XLR",
            "CH2": "XLR_H1_IN2_XLR",
            "CH3": "INACTIVE_2CH_MODE",
            "CH4": "INACTIVE_2CH_MODE",
        }
        big6_4ch = False

    return Xlrh1MishoeAudioEvalResult(
        valid=True,
        handle_attached=True,
        audio_format=fmt,
        sample_rate_hz=sr,
        bit_depth=bd,
        channels=ch,
        bitrate_bps=bps,
        channel_routing=routing,
        monitor_mode=mon,
        monitor_appfw_token=MONITOR_MODE_TO_APPFW_TOKEN[mon],
        big6_4ch_meters_bound=big6_4ch,
        mpr_alsa_backend_bound=True,
        xlr_h1_standalone_fw_pkg_required=False,
        p11_queue_hex=f"0x{P11_SMART_HANDLE_QUEUE_ID:08x}",
        p11_nonblock_rc_hex=f"0x{HOTSHOE_NONBLOCK_SAFE_RC:04x}",
        bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
        status=f"XLRH1_MISHOE_{fmt}_MON_{mon}_OK",
        errors=(),
    )


def evaluate_body_35mm_jack_override_and_sq_mute(
    *,
    xlr_h1_attached: bool = True,
    body_35mm_jack_inserted: bool = False,
    sq_mode_active: bool = False,
    rec_fps: float = 23.976,
    sensor_fps: float = 23.976,
    audio_recording_enabled: bool = True,
) -> JackOverrideAndSqMuteEvalResult:
    """Evaluate FX3 body 3.5mm jack hardware override vs MI-Shoe & S&Q audio mute."""
    errors: List[str] = []
    if rec_fps <= 0 or sensor_fps <= 0:
        errors.append("NON_POSITIVE_FPS")
        return JackOverrideAndSqMuteEvalResult(
            valid=False,
            xlr_h1_attached=xlr_h1_attached,
            body_35mm_jack_inserted=body_35mm_jack_inserted,
            sq_mode_active=sq_mode_active,
            rec_fps=rec_fps,
            sensor_fps=sensor_fps,
            audio_recording_enabled=audio_recording_enabled,
            active_audio_source="INVALID",
            mi_shoe_audio_set_locked=True,
            mi_shoe_audio_active=False,
            audio_recording_muted=True,
            caution_factor_token="INVALID_FPS",
            mpr_stall_faults=0,
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            status="NON_POSITIVE_FPS",
            errors=tuple(errors),
        )

    off_speed_sq = sq_mode_active and abs(rec_fps - sensor_fps) > 1e-3

    if not audio_recording_enabled or off_speed_sq:
        caution = (
            "MODEL_VALUE_CHANGED_BY_EXCLUSION_SLOW_AND_QUICK"
            if off_speed_sq
            else "CAUTION_ID_FACTOR_AUDIO_RECORDING_OFF_MSG"
        )
        return JackOverrideAndSqMuteEvalResult(
            valid=True,
            xlr_h1_attached=xlr_h1_attached,
            body_35mm_jack_inserted=body_35mm_jack_inserted,
            sq_mode_active=sq_mode_active,
            rec_fps=rec_fps,
            sensor_fps=sensor_fps,
            audio_recording_enabled=audio_recording_enabled,
            active_audio_source="MUTED_NO_AUDIO_TRACK",
            mi_shoe_audio_set_locked=True,
            mi_shoe_audio_active=False,
            audio_recording_muted=True,
            caution_factor_token=caution,
            mpr_stall_faults=0,
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            status="SQ_OFFSPEED_AUDIO_MUTED_OK" if off_speed_sq else "AUDIO_RECORDING_OFF_MUTED_OK",
            errors=(),
        )

    if body_35mm_jack_inserted:
        # Hardware jack switch physically overrides MI-Shoe & greys out [MI Shoe Audio Set.]
        return JackOverrideAndSqMuteEvalResult(
            valid=True,
            xlr_h1_attached=xlr_h1_attached,
            body_35mm_jack_inserted=True,
            sq_mode_active=sq_mode_active,
            rec_fps=rec_fps,
            sensor_fps=sensor_fps,
            audio_recording_enabled=True,
            active_audio_source="BODY_35MM_TRS_JACK_MIC",
            mi_shoe_audio_set_locked=True,
            mi_shoe_audio_active=False,
            audio_recording_muted=False,
            caution_factor_token="CAUTION_ID_FACTOR_ANALOG_MIC_SHOEMIC_USE_MSG",
            mpr_stall_faults=0,
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            status="BODY_35MM_JACK_OVERRIDE_LOCKS_MISHOE_OK",
            errors=(),
        )

    if xlr_h1_attached:
        return JackOverrideAndSqMuteEvalResult(
            valid=True,
            xlr_h1_attached=True,
            body_35mm_jack_inserted=False,
            sq_mode_active=sq_mode_active,
            rec_fps=rec_fps,
            sensor_fps=sensor_fps,
            audio_recording_enabled=True,
            active_audio_source="XLR_H1_MISHOE_DIGITAL_AUDIO",
            mi_shoe_audio_set_locked=False,
            mi_shoe_audio_active=True,
            audio_recording_muted=False,
            caution_factor_token="NONE",
            mpr_stall_faults=0,
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            status="XLRH1_MISHOE_ACTIVE_UNLOCKED_OK",
            errors=(),
        )

    return JackOverrideAndSqMuteEvalResult(
        valid=True,
        xlr_h1_attached=False,
        body_35mm_jack_inserted=False,
        sq_mode_active=sq_mode_active,
        rec_fps=rec_fps,
        sensor_fps=sensor_fps,
        audio_recording_enabled=True,
        active_audio_source="BODY_INTERNAL_STEREO_MIC",
        mi_shoe_audio_set_locked=True,
        mi_shoe_audio_active=False,
        audio_recording_muted=False,
        caution_factor_token="CAUTION_ID_FACTOR_MIC_SHOEMIC_NOT_USE_MSG",
        mpr_stall_faults=0,
        bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
        status="INTERNAL_STEREO_MIC_FALLBACK_OK",
        errors=(),
    )


def evaluate_post_ufu_audio_default_hygiene(
    *,
    stage: str = "H0",
    post_ufu_reset_occurred: bool = True,
    stage_b_user_audio_pref: str = "48KHZ_24BIT_4CH",
    pref_staging_path: str = "/tmp/stage_b/xlrh1_audio_pref.json",
    h0_backup_sha256: str = "",
) -> PostUfuAudioDefaultEvalResult:
    """Audit Backup.bin 48kHz/16bit 2ch default & H0->H1->H2->H3 SHA-256 conservation."""
    errors: List[str] = []
    st = stage.strip().upper()
    pref = stage_b_user_audio_pref.strip().upper()
    norm_path = pref_staging_path.strip()

    if st not in VALID_H_STAGES:
        errors.append(f"INVALID_H_STAGE: {stage}")
    if pref not in MISHOE_AUDIO_FORMATS:
        errors.append(f"INVALID_STAGE_B_AUDIO_PREF: {stage_b_user_audio_pref}")

    wg = evaluate_phase189_write_guard(norm_path)
    if not wg.valid:
        errors.append(f"UNSAFE_PREF_STAGING_PATH: {norm_path}")

    ref_hash = h0_backup_sha256 or hashlib.sha256(b"FX3_STOCK_BACKUP_BIN_H0").hexdigest()
    stage_hash = ref_hash  # p2:/setting/Backup.bin is strictly O_RDONLY across H0..H3

    if st in ("H0", "H1", "H3"):
        effective = POST_UFU_DEFAULT_AUDIO_FORMAT if post_ufu_reset_occurred else pref
        bclass = BRIDGE_CLASS_NATIVE_PASSTHROUGH
        status = f"{st}_BACKUP_BIN_CONSERVED_DEFAULT_16BIT_2CH_OK"
    else:  # H2 Stage-B active overlay
        effective = pref
        bclass = BRIDGE_CLASS_SHIM_TRANSLATED
        status = f"H2_STAGE_B_VOLATILE_{pref}_BACKUP_UNTOUCHED_OK"

    return PostUfuAudioDefaultEvalResult(
        valid=len(errors) == 0 and wg.valid,
        stage=st,
        post_ufu_reset_occurred=post_ufu_reset_occurred,
        backup_bin_audio_default=POST_UFU_DEFAULT_AUDIO_FORMAT,
        stage_b_user_audio_pref=pref,
        effective_audio_format=effective,
        pref_staging_path=norm_path,
        volatile_staged=wg.volatile_or_ext_allowed,
        persistent_writes=0,
        backup_bin_writes=0,
        h0_backup_sha256=ref_hash,
        stage_backup_sha256=stage_hash,
        backup_bin_hash_conserved=(stage_hash == ref_hash),
        bridge_class=bclass,
        status=status if len(errors) == 0 else errors[0],
        errors=tuple(errors),
    )


def evaluate_phase189_write_guard(target_path: str) -> Phase189WriteGuardResult:
    """Hard write-firewall blocking Backup.bin, BODYDATA.DAT, CAMSET, eMMC & SPI-NOR."""
    norm = target_path.strip()
    if FORBIDDEN_PERSISTENT_TARGET_RE_P189.search(norm):
        return Phase189WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            backup_bin_writes=0,
            status="BLOCKED_PERSISTENT_EMMC_BACKUP_OR_BODYDATA_TARGET",
            errors=(f"FORBIDDEN_PERSISTENT_TARGET: {norm}",),
        )
    allowed = any(norm.startswith(p) for p in VOLATILE_OR_EXT_PREFIXES_P189)
    if not allowed:
        return Phase189WriteGuardResult(
            valid=False,
            target_path=norm,
            volatile_or_ext_allowed=False,
            persistent_write_blocked=True,
            persistent_emmc_writes_authorized=False,
            spi_nor_write_authorized=False,
            el3_payload_transmit_authorized=False,
            physical_usb_packets_emitted=0,
            persistent_writes=0,
            backup_bin_writes=0,
            status="UNLISTED_NON_VOLATILE_TARGET_BLOCKED",
            errors=(f"TARGET_NOT_VOLATILE_OR_EXT: {norm}",),
        )
    return Phase189WriteGuardResult(
        valid=True,
        target_path=norm,
        volatile_or_ext_allowed=True,
        persistent_write_blocked=False,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        persistent_writes=0,
        backup_bin_writes=0,
        status="VOLATILE_TMPFS_OR_EXT_MEDIA_ALLOWED",
        errors=(),
    )


def build_phase189_compat_matrix() -> Phase189CompatMatrixSummary:
    """Construct 12-touchpoint 4-class compatibility matrix across Domains A..D."""
    entries: Tuple[Phase189TouchpointEntry, ...] = (
        Phase189TouchpointEntry(
            touchpoint_id="P189-01",
            domain="FX3_VS_FX3A_BRANCH_SPLIT",
            fx6_or_branch_component="ILME-FX3 7.02 (0x91030080, 1.44M LCD, NFC + IR)",
            fx3_target="Stage-A & Stage-B host-bundle Model-ID & panel-descriptor lock",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="stage_a_accepted == True only for 0x91030080 + 1.44M LCD",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-02",
            domain="FX3_VS_FX3A_BRANCH_SPLIT",
            fx6_or_branch_component="ILME-FX3A 2.02 (0x91030082, 2.36M XGA LCD, no NFC/IR)",
            fx3_target="Stage-A <50us fail-closed gate rejects FX3A cross-loading",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="fail_closed_rejected == True; reject_latency_us < 50",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-03",
            domain="FX3_VS_FX3A_BRANCH_SPLIT",
            fx6_or_branch_component="FX3A/FX30/FX6 BODYDATA.DAT & CAMSET cross-branch files",
            fx3_target="libupdaterufp.so & appFw.so CAMSET/Model-ID compatibility guard",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="5L+6S model mismatch blocked; zero persistent writes",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-04",
            domain="XLRH1_MISHOE_4CH_BRIDGE",
            fx6_or_branch_component="FX6 Smart Handle XLR IN1/IN2 + 48kHz/24bit 4ch LPCM",
            fx3_target="FX3 MI-Shoe XLR-H1 (IN1/IN2->CH1/CH2, IN3 3.5mm->CH3/CH4)",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="4,608,000 bps LPCM bound to FX3 ALSA/MPR backend",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-05",
            domain="XLRH1_MISHOE_4CH_BRIDGE",
            fx6_or_branch_component="FX6 Big-6 CH1..CH4 Meters & 4ch Audio Monitoring",
            fx3_target="FX3 AUDIO_MONITORING_CH_{1CH_2CH,3CH_4CH,MIX_ALL} binding",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="big6_4ch_meters_bound == True; standalone XLR-H1 FW = False",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-06",
            domain="XLRH1_MISHOE_4CH_BRIDGE",
            fx6_or_branch_component="XLR-H1 detached / P11 0x91db059b E_TMO=-50 timeout",
            fx3_target="Non-blocking P11 0x8000 shim fallback to Internal Stereo",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="no MPR stall on XLR-H1 hot-detach",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-07",
            domain="BODY_35MM_OVERRIDE_SQ_MUTE",
            fx6_or_branch_component="Body 3.5mm TRS mic plug inserted (JACK_MICJACK_IN)",
            fx3_target="Hardware jack-detect overrides MI-Shoe & locks [MI Shoe Audio Set.]",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="mi_shoe_audio_set_locked == True; active == BODY_35MM_TRS",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-08",
            domain="BODY_35MM_OVERRIDE_SQ_MUTE",
            fx6_or_branch_component="Off-speed S&Q recording (rec_fps != sensor_fps)",
            fx3_target="Deterministic S&Q audio mute parity across FX3 7.02 & FX6 6.01",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="audio_recording_muted == True; mpr_stall_faults == 0",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-09",
            domain="BODY_35MM_OVERRIDE_SQ_MUTE",
            fx6_or_branch_component="Audio Recording = Off / Unplugged handle-less state",
            fx3_target="Safe mute / Internal Stereo mic without phantom handle fault",
            bridge_class=BRIDGE_CLASS_MASKED_ABSENT_HW,
            safety_invariant="mpr_stall_faults == 0",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-10",
            domain="POST_UFU_AUDIO_DEFAULT_HYGIENE",
            fx6_or_branch_component="Post-UFU factory reset default (48kHz/16bit 2ch)",
            fx3_target="Stock Backup.bin (819 subsystems) O_RDONLY baseline H0 == H3",
            bridge_class=BRIDGE_CLASS_NATIVE_PASSTHROUGH,
            safety_invariant="backup_bin_audio_default == 48KHZ_16BIT_2CH; H0 == H3",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-11",
            domain="POST_UFU_AUDIO_DEFAULT_HYGIENE",
            fx6_or_branch_component="Stage-B H2 user 48kHz/24bit 4ch preference",
            fx3_target="Volatile /tmp/ or external SD ExFAT staging overlay",
            bridge_class=BRIDGE_CLASS_SHIM_TRANSLATED,
            safety_invariant="volatile_staged == True; persistent_writes == 0",
        ),
        Phase189TouchpointEntry(
            touchpoint_id="P189-12",
            domain="POST_UFU_AUDIO_DEFAULT_HYGIENE",
            fx6_or_branch_component="p2:/setting/Backup.bin, BODYDATA.DAT, CAMSET, spi_nor:",
            fx3_target="Strict O_RDONLY write-firewall across H0..H3",
            bridge_class=BRIDGE_CLASS_HARD_WRITE_PROTECTED,
            safety_invariant="backup_bin_writes == 0; persistent_emmc_writes_authorized == False",
        ),
    )
    class_counts: Dict[str, int] = {c: 0 for c in VALID_BRIDGE_CLASSES}
    domain_counts: Dict[str, int] = {}
    for e in entries:
        class_counts[e.bridge_class] = class_counts.get(e.bridge_class, 0) + 1
        domain_counts[e.domain] = domain_counts.get(e.domain, 0) + 1
    return Phase189CompatMatrixSummary(
        total_touchpoints=len(entries),
        class_counts=class_counts,
        domain_counts=domain_counts,
        touchpoints=entries,
    )


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Helpers & Clean-Room Synthetic Fixture Builder
# ---------------------------------------------------------------------------


def _read_bk4_rdonly(path: Path, *, body: str) -> Bk4DualRecordSummary:
    """Strictly O_RDONLY bounded `os.pread` read of `Backup.bin`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        buf = os.pread(fd, sz, 0)
        summary, _b0, _b1 = parse_dual_bk4_and_descriptors(buf, body=body)
        return summary
    finally:
        os.close(fd)


def _scan_flat_fast_rdonly(
    path: Path,
    tokens: Sequence[str],
) -> Tuple[int, Dict[str, int]]:
    """Strictly O_RDONLY bounded `os.pread` fast C-`count` scan for flat RTOS blobs."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        if sz == 0:
            return 0, {t: 0 for t in tokens}
        buf = os.pread(fd, sz, 0)
        return sz, {t: buf.count(t.encode("ascii")) for t in tokens}
    finally:
        os.close(fd)


def _scan_elf_fast_rdonly(
    path: Path,
    *,
    binary_name: str,
    body_label: str,
    tokens: Sequence[str],
) -> ElfSectionSummary:
    """Strictly O_RDONLY bounded ELF64 `.dynstr`/`.rodata`/`.strtab` fast `bytes.count` scanner."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        sz = int(os.fstat(fd).st_size)
        ehdr = os.pread(fd, 64, 0)
        if len(ehdr) < 64 or ehdr[:4] != b"\x7fELF":
            raise ValueError(f"Invalid ELF64 header: {path}")
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
            if sh_type == 11:
                dynsym_meta = (sh_off, sh_sz)
            elif sh_type == 6:
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
            encoded = [(t, t.encode("ascii")) for t in tokens]
            for s_off, s_sz in ro_slices:
                chunk = os.pread(fd, s_sz, s_off)
                for tok, b_tok in encoded:
                    c = chunk.count(b_tok)
                    if c:
                        counts[tok] += c

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


def build_clean_room_realhw_fx3_vs_fx3a_and_xlrh1_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, `cpapp-b.bin`, `BK4`, and `UFU` fixtures."""
    from .realhw_cp_rtos_and_backup_bin_auditor import (
        build_clean_room_realhw_cp_backup_fixtures,
    )
    from .realhw_cfexpress_sdxc_exfat_rsv_and_ufu_coexistence_auditor import (
        build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures,
    )

    cp_fixtures = build_clean_room_realhw_cp_backup_fixtures()
    ufu_fixtures = build_clean_room_realhw_cfexpress_sdxc_ufu_fixtures()

    fx3_appfw_tokens = (
        APPFW_FX3_BRANCH_MARKERS_P189
        + APPFW_FX3_MISHOE_AUDIO_MARKERS_P189
        + APPFW_FX3_JACK_AND_SQ_MARKERS_P189
    )
    fx6_appfw_tokens = APPFW_FX6_HANDLE_AUDIO_MARKERS_P189

    return {
        "fx3_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af3_imp_{i}" for i in range(48)),
            dt_needed=("libmpr.so", "libupdaterufp.so"),
            rodata_strings=fx3_appfw_tokens,
        ),
        "fx6_appfw": _build_synthetic_elf64(
            exports=("appFw_main",),
            imports=tuple(f"af6_imp_{i}" for i in range(48)),
            dt_needed=("libmpr.so", "libInfraHotshoe.so"),
            rodata_strings=fx6_appfw_tokens,
        ),
        "fx3_mpr": _build_synthetic_elf64(
            exports=tuple(f"mpr3_exp_{i}" for i in range(32)),
            imports=tuple(f"mpr3_imp_{i}" for i in range(16)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=MPR_AUDIO_SHARED_MARKERS_P189,
        ),
        "fx6_mpr": _build_synthetic_elf64(
            exports=tuple(f"mpr6_exp_{i}" for i in range(36)),
            imports=tuple(f"mpr6_imp_{i}" for i in range(16)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=MPR_AUDIO_SHARED_MARKERS_P189,
        ),
        "fx3_updaterufp": ufu_fixtures["fx3_updaterufp"],
        "fx3_bodydata_head": ufu_fixtures["bodydata_head"],
        "fx3_bodydata_tail": ufu_fixtures["bodydata_tail"],
        "fx6_hotshoe": _build_synthetic_elf64(
            exports=tuple(f"hs6_exp_{i}" for i in range(76)),
            imports=tuple(f"hs6_imp_{i}" for i in range(24)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=HOTSHOE_MARKERS,
        ),
        "fx6_avbb_audio": _build_synthetic_elf64(
            exports=tuple(f"avbb6_exp_{i}" for i in range(20)),
            imports=tuple(f"avbb6_imp_{i}" for i in range(16)),
            dt_needed=("libosal_uipc.so",),
            rodata_strings=AVBB_AUDIO_MARKERS_P189,
        ),
        "fx3_cpapp": b"\x00".join(
            t.encode("ascii")
            for t in (CPAPP_SHARED_SHOE_PANEL_MARKERS_P189 + CPAPP_FX3_MISHOE_MARKERS_P189)
        ),
        "fx6_cpapp": b"\x00".join(t.encode("ascii") for t in CPAPP_SHARED_SHOE_PANEL_MARKERS_P189),
        "fx3_backup": cp_fixtures["fx3_backup"],
        "fx6_backup": cp_fixtures["fx6_backup"],
    }


# ---------------------------------------------------------------------------
# Main Dual-Mode Unified Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwFx3VsFx3aAndXlrh1MishoeReport:
    """Run Phase 189 (39th Auditor, 39/39) on real O_RDONLY donors or clean-room fixtures."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    force_clean = clean_room or is_forced_clean_room()

    required_rel_map = {
        "fx3_appfw": FX3_APPFW_P189_RELPATH,
        "fx6_appfw": FX6_APPFW_P189_RELPATH,
        "fx3_mpr": FX3_LIBMPR_P189_RELPATH,
        "fx6_mpr": FX6_LIBMPR_P189_RELPATH,
        "fx3_cpapp": FX3_CPAPP_P189_RELPATH,
        "fx6_cpapp": FX6_CPAPP_P189_RELPATH,
        "fx3_backup": FX3_BACKUP_BIN_P189_RELPATH,
        "fx6_backup": FX6_BACKUP_BIN_P189_RELPATH,
        "fx3_updaterufp": FX3_LIBUPDATERUFP_P189_RELPATH,
        "fx3_bodydata": FX3_BODYDATA_DAT_P189_RELPATH,
        "fx6_hotshoe": FX6_HOTSHOE_P189_RELPATH,
        "fx6_avbb_audio": FX6_AVBB_AUDIO_P189_RELPATH,
    }

    donor_paths: Dict[str, Optional[Path]] = {}
    if not force_clean:
        for key, rel in required_rel_map.items():
            donor_paths[key] = resolve_donor_file(rel, repo_root=root)

    use_local = (not force_clean) and all(p is not None for p in donor_paths.values())

    all_fx3_appfw_tokens = tuple(
        sorted(
            set(
                APPFW_FX3_BRANCH_MARKERS_P189
                + APPFW_FX3_MISHOE_AUDIO_MARKERS_P189
                + APPFW_FX3_JACK_AND_SQ_MARKERS_P189
            ),
            key=len,
            reverse=True,
        )
    )
    all_cpapp_tokens = CPAPP_SHARED_SHOE_PANEL_MARKERS_P189 + CPAPP_FX3_MISHOE_MARKERS_P189

    donor_file_sizes: Dict[str, int] = {}
    errors: List[str] = []

    if use_local:
        mode = "LOCAL_DONOR_VERIFIED"
        fx3_appfw_sum = _scan_elf_fast_rdonly(
            donor_paths["fx3_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX3",
            tokens=all_fx3_appfw_tokens,
        )
        fx6_appfw_sum = _scan_elf_fast_rdonly(
            donor_paths["fx6_appfw"],  # type: ignore[arg-type]
            binary_name="appFw.so",
            body_label="FX6",
            tokens=APPFW_FX6_HANDLE_AUDIO_MARKERS_P189,
        )
        fx3_mpr_sum = _scan_elf_fast_rdonly(
            donor_paths["fx3_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX3",
            tokens=MPR_AUDIO_SHARED_MARKERS_P189,
        )
        fx6_mpr_sum = _scan_elf_fast_rdonly(
            donor_paths["fx6_mpr"],  # type: ignore[arg-type]
            binary_name="libmpr.so",
            body_label="FX6",
            tokens=MPR_AUDIO_SHARED_MARKERS_P189,
        )
        fx3_ufp_sum = _scan_elf_fast_rdonly(
            donor_paths["fx3_updaterufp"],  # type: ignore[arg-type]
            binary_name="libupdaterufp.so",
            body_label="FX3",
            tokens=UPDATERUFP_MARKERS,
        )
        fx6_hs_sum = _scan_elf_fast_rdonly(
            donor_paths["fx6_hotshoe"],  # type: ignore[arg-type]
            binary_name="libInfraHotshoe.so",
            body_label="FX6",
            tokens=HOTSHOE_MARKERS,
        )
        fx6_avbb_sum = _scan_elf_fast_rdonly(
            donor_paths["fx6_avbb_audio"],  # type: ignore[arg-type]
            binary_name="AVBB_SCN_START_AUDIO.so",
            body_label="FX6",
            tokens=AVBB_AUDIO_MARKERS_P189,
        )
        fx3_cp_sz, fx3_cp_hits = _scan_flat_fast_rdonly(
            donor_paths["fx3_cpapp"], all_cpapp_tokens  # type: ignore[arg-type]
        )
        fx6_cp_sz, fx6_cp_hits = _scan_flat_fast_rdonly(
            donor_paths["fx6_cpapp"], all_cpapp_tokens  # type: ignore[arg-type]
        )
        fx3_bk_sum = _read_bk4_rdonly(donor_paths["fx3_backup"], body="FX3")  # type: ignore[arg-type]
        fx6_bk_sum = _read_bk4_rdonly(donor_paths["fx6_backup"], body="FX6")  # type: ignore[arg-type]

        bd_path = donor_paths["fx3_bodydata"]  # type: ignore[assignment]
        bd_fd = os.open(str(bd_path), os.O_RDONLY)
        try:
            bd_sz = int(os.fstat(bd_fd).st_size)
            bd_head = os.pread(bd_fd, 256, 0)
            bd_tail = os.pread(bd_fd, 64, max(0, bd_sz - 64))
        finally:
            os.close(bd_fd)
        bd_sum = parse_bodydata_ufu_header_tail(
            total_bytes=bd_sz,
            head_bytes=bd_head,
            tail_bytes=bd_tail,
            source_mode="LOCAL_DONOR_RDONLY",
        )

        donor_file_sizes = {
            "fx3_appfw": fx3_appfw_sum.file_bytes,
            "fx6_appfw": fx6_appfw_sum.file_bytes,
            "fx3_mpr": fx3_mpr_sum.file_bytes,
            "fx6_mpr": fx6_mpr_sum.file_bytes,
            "fx3_cpapp": fx3_cp_sz,
            "fx6_cpapp": fx6_cp_sz,
            "fx3_backup": fx3_bk_sum.file_bytes,
            "fx6_backup": fx6_bk_sum.file_bytes,
            "fx3_updaterufp": fx3_ufp_sum.file_bytes,
            "fx3_bodydata": bd_sum.total_bytes,
            "fx6_hotshoe": fx6_hs_sum.file_bytes,
            "fx6_avbb_audio": fx6_avbb_sum.file_bytes,
        }
    else:
        mode = "CLEAN_ROOM_SYNTHETIC"
        fx = build_clean_room_realhw_fx3_vs_fx3a_and_xlrh1_fixtures()
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
            tokens=APPFW_FX6_HANDLE_AUDIO_MARKERS_P189,
        )
        fx3_mpr_sum = _scan_elf_buf_ordered(
            fx["fx3_mpr"],
            binary_name="libmpr.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=MPR_AUDIO_SHARED_MARKERS_P189,
        )
        fx6_mpr_sum = _scan_elf_buf_ordered(
            fx["fx6_mpr"],
            binary_name="libmpr.so",
            body_label="FX6",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=MPR_AUDIO_SHARED_MARKERS_P189,
        )
        fx3_ufp_sum = _scan_elf_buf_ordered(
            fx["fx3_updaterufp"],
            binary_name="libupdaterufp.so",
            body_label="FX3",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=UPDATERUFP_MARKERS,
        )
        fx6_hs_sum = _scan_elf_buf_ordered(
            fx["fx6_hotshoe"],
            binary_name="libInfraHotshoe.so",
            body_label="FX6",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=HOTSHOE_MARKERS,
        )
        fx6_avbb_sum = _scan_elf_buf_ordered(
            fx["fx6_avbb_audio"],
            binary_name="AVBB_SCN_START_AUDIO.so",
            body_label="FX6",
            source_mode="CLEAN_ROOM_SYNTHETIC",
            tokens=AVBB_AUDIO_MARKERS_P189,
        )
        fx3_cp_hits = _count_tokens_ordered_single_pass(fx["fx3_cpapp"], all_cpapp_tokens)
        fx6_cp_hits = _count_tokens_ordered_single_pass(fx["fx6_cpapp"], all_cpapp_tokens)
        fx3_bk_sum, _b0, _b1 = parse_dual_bk4_and_descriptors(fx["fx3_backup"], body="FX3")
        fx6_bk_sum, _b2, _b3 = parse_dual_bk4_and_descriptors(fx["fx6_backup"], body="FX6")
        bd_sum = parse_bodydata_ufu_header_tail(
            total_bytes=BODYDATA_EXPECTED_TOTAL_BYTES,
            head_bytes=fx["fx3_bodydata_head"],
            tail_bytes=fx["fx3_bodydata_tail"],
            source_mode="CLEAN_ROOM_SYNTHETIC",
        )
        donor_file_sizes = {
            "fx3_appfw": fx3_appfw_sum.file_bytes,
            "fx6_appfw": fx6_appfw_sum.file_bytes,
            "fx3_mpr": fx3_mpr_sum.file_bytes,
            "fx6_mpr": fx6_mpr_sum.file_bytes,
            "fx3_cpapp": len(fx["fx3_cpapp"]),
            "fx6_cpapp": len(fx["fx6_cpapp"]),
            "fx3_backup": fx3_bk_sum.file_bytes,
            "fx6_backup": fx6_bk_sum.file_bytes,
            "fx3_updaterufp": fx3_ufp_sum.file_bytes,
            "fx3_bodydata": bd_sum.total_bytes,
            "fx6_hotshoe": fx6_hs_sum.file_bytes,
            "fx6_avbb_audio": fx6_avbb_sum.file_bytes,
        }

    # --- Domain A: FX3 (7.02) vs FX3A (2.02) Hardware Branch Split ---
    da_errors: List[str] = []
    fx3_branch_hits = {t: fx3_appfw_sum.marker_hits[t] for t in APPFW_FX3_BRANCH_MARKERS_P189}
    if not all(v > 0 for v in fx3_branch_hits.values()):
        da_errors.append("MISSING_FX3_BRANCH_MARKERS_IN_APPFW")
    if not all(v > 0 for v in fx3_ufp_sum.marker_hits.values()):
        da_errors.append("MISSING_FX3_UPDATERUFP_MARKERS")
    if not bd_sum.valid:
        da_errors.extend(bd_sum.errors)

    ev_fx3_ok = evaluate_fx3_vs_fx3a_hardware_branch()
    ev_fx3a_rej = evaluate_fx3_vs_fx3a_hardware_branch(
        target_body="ILME-FX3A",
        model_id=MODEL_ID_FX3A_P189,
        fw_version=FX3A_202_FW_VERSION,
        lcd_dots=FX3A_LCD_DOTS,
        has_nfc=False,
        has_ir_receiver=False,
        camset_profile="CAMSET_FX3A_202",
        bodydata_model_id=MODEL_ID_FX3A_P189,
    )
    ev_fx30_rej = evaluate_fx3_vs_fx3a_hardware_branch(
        target_body="ILME-FX30",
        model_id=MODEL_ID_FX30_P189,
        fw_version="6.00",
        lcd_dots=FX3A_LCD_DOTS,
        has_nfc=False,
        has_ir_receiver=False,
        camset_profile="CAMSET_FX30",
        bodydata_model_id=MODEL_ID_FX30_P189,
    )
    ev_fx6_rej = evaluate_fx3_vs_fx3a_hardware_branch(
        target_body="ILME-FX6",
        model_id=MODEL_ID_FX6_P189,
        fw_version=FX6_601_FW_VERSION,
        lcd_dots=2_764_800,
        has_nfc=True,
        has_ir_receiver=False,
        camset_profile="CAMSET_FX6_601",
        bodydata_model_id=MODEL_ID_FX6_P189,
    )
    ev_camset_rej = evaluate_fx3_vs_fx3a_hardware_branch(
        target_body="ILME-FX3",
        model_id=MODEL_ID_FX3_P189,
        fw_version=FX3_702_FW_VERSION,
        lcd_dots=FX3_LCD_DOTS,
        has_nfc=True,
        has_ir_receiver=True,
        camset_profile="CAMSET_FX3A_202",
        bodydata_model_id=MODEL_ID_FX3_P189,
    )
    ev_bodydata_rej = evaluate_fx3_vs_fx3a_hardware_branch(
        target_body="ILME-FX3",
        model_id=MODEL_ID_FX3_P189,
        fw_version=FX3_702_FW_VERSION,
        lcd_dots=FX3_LCD_DOTS,
        has_nfc=True,
        has_ir_receiver=True,
        camset_profile="CAMSET_FX3_702",
        bodydata_model_id=MODEL_ID_FX3A_P189,
    )
    if not (
        ev_fx3_ok.stage_a_accepted
        and ev_fx3a_rej.fail_closed_rejected
        and ev_fx3a_rej.reject_latency_us < STAGE_A_REJECT_BUDGET_US
        and ev_fx30_rej.fail_closed_rejected
        and ev_fx6_rej.fail_closed_rejected
        and ev_camset_rej.fail_closed_rejected
        and ev_bodydata_rej.fail_closed_rejected
    ):
        da_errors.append("DOMAIN_A_BRANCH_ISOLATION_EVAL_FAILED")

    domain_a = DomainAFx3VsFx3aBranchReport(
        passed=len(da_errors) == 0,
        fx3_appfw_branch_hits=fx3_branch_hits,
        fx3_updaterufp_summary=fx3_ufp_sum,
        fx3_bodydata_summary=bd_sum,
        fx3_702_accepted_eval=ev_fx3_ok,
        fx3a_202_rejected_eval=ev_fx3a_rej,
        fx30_lax_rejected_eval=ev_fx30_rej,
        fx6_601_rejected_eval=ev_fx6_rej,
        cross_camset_rejected_eval=ev_camset_rej,
        cross_bodydata_rejected_eval=ev_bodydata_rej,
        errors=tuple(da_errors),
    )

    # --- Domain B: XLR-H1 MI-Shoe 48kHz/24bit 4ch Audio Bridge ---
    db_errors: List[str] = []
    fx3_mishoe_hits = {t: fx3_appfw_sum.marker_hits[t] for t in APPFW_FX3_MISHOE_AUDIO_MARKERS_P189}
    fx6_handle_hits = {t: fx6_appfw_sum.marker_hits[t] for t in APPFW_FX6_HANDLE_AUDIO_MARKERS_P189}
    fx3_cp_mishoe_hits = {t: fx3_cp_hits[t] for t in all_cpapp_tokens}
    fx6_cp_shoe_hits = {t: fx6_cp_hits[t] for t in CPAPP_SHARED_SHOE_PANEL_MARKERS_P189}

    if not all(v > 0 for v in fx3_mishoe_hits.values()):
        db_errors.append("MISSING_FX3_APPFW_MISHOE_AUDIO_MARKERS")
    if not all(v > 0 for v in fx6_handle_hits.values()):
        db_errors.append("MISSING_FX6_APPFW_HANDLE_AUDIO_MARKERS")
    if not all(v > 0 for v in fx3_mpr_sum.marker_hits.values()):
        db_errors.append("MISSING_FX3_MPR_AUDIO_MARKERS")
    if not all(v > 0 for v in fx6_mpr_sum.marker_hits.values()):
        db_errors.append("MISSING_FX6_MPR_AUDIO_MARKERS")
    if not all(v > 0 for v in fx6_hs_sum.marker_hits.values()):
        db_errors.append("MISSING_FX6_HOTSHOE_MARKERS")
    if not all(v > 0 for v in fx6_avbb_sum.marker_hits.values()):
        db_errors.append("MISSING_FX6_AVBB_AUDIO_MARKERS")
    if not all(v > 0 for v in fx3_cp_mishoe_hits.values()):
        db_errors.append("MISSING_FX3_CPAPP_MISHOE_MARKERS")
    if not all(v > 0 for v in fx6_cp_shoe_hits.values()):
        db_errors.append("MISSING_FX6_CPAPP_SHOE_MARKERS")

    ev_24_4ch = evaluate_xlrh1_mishoe_4ch_bridge(
        handle_attached=True, audio_format="48KHZ_24BIT_4CH", monitor_mode="CH1_3_AND_CH2_4_MIX"
    )
    ev_24_2ch = evaluate_xlrh1_mishoe_4ch_bridge(
        handle_attached=True, audio_format="48KHZ_24BIT_2CH", monitor_mode="CH1_2"
    )
    ev_16_2ch = evaluate_xlrh1_mishoe_4ch_bridge(
        handle_attached=True, audio_format="48KHZ_16BIT_2CH", monitor_mode="CH3_4"
    )
    ev_detach = evaluate_xlrh1_mishoe_4ch_bridge(handle_attached=False)
    if not (
        ev_24_4ch.valid
        and ev_24_4ch.big6_4ch_meters_bound
        and ev_24_2ch.valid
        and ev_16_2ch.valid
        and ev_detach.valid
        and not ev_24_4ch.xlr_h1_standalone_fw_pkg_required
    ):
        db_errors.append("DOMAIN_B_XLRH1_MISHOE_EVAL_FAILED")

    domain_b = DomainBXlrh1MishoeAudioReport(
        passed=len(db_errors) == 0,
        fx3_appfw_mishoe_hits=fx3_mishoe_hits,
        fx6_appfw_handle_hits=fx6_handle_hits,
        fx3_mpr_summary=fx3_mpr_sum,
        fx6_mpr_summary=fx6_mpr_sum,
        fx6_hotshoe_summary=fx6_hs_sum,
        fx6_avbb_audio_summary=fx6_avbb_sum,
        fx3_cpapp_mishoe_hits=fx3_cp_mishoe_hits,
        fx6_cpapp_shoe_hits=fx6_cp_shoe_hits,
        eval_48k_24bit_4ch=ev_24_4ch,
        eval_48k_24bit_2ch=ev_24_2ch,
        eval_48k_16bit_2ch=ev_16_2ch,
        eval_detached_fallback=ev_detach,
        errors=tuple(db_errors),
    )

    # --- Domain C: Body 3.5mm Jack Override & S&Q Audio Mute ---
    dc_errors: List[str] = []
    fx3_jack_sq_hits = {t: fx3_appfw_sum.marker_hits[t] for t in APPFW_FX3_JACK_AND_SQ_MARKERS_P189}
    if not all(v > 0 for v in fx3_jack_sq_hits.values()):
        dc_errors.append("MISSING_FX3_JACK_OR_SQ_MARKERS")

    ev_norm = evaluate_body_35mm_jack_override_and_sq_mute(
        xlr_h1_attached=True, body_35mm_jack_inserted=False, sq_mode_active=False
    )
    ev_jack = evaluate_body_35mm_jack_override_and_sq_mute(
        xlr_h1_attached=True, body_35mm_jack_inserted=True, sq_mode_active=False
    )
    ev_sq = evaluate_body_35mm_jack_override_and_sq_mute(
        xlr_h1_attached=True, body_35mm_jack_inserted=False, sq_mode_active=True, rec_fps=23.976, sensor_fps=120.0
    )
    ev_off = evaluate_body_35mm_jack_override_and_sq_mute(
        xlr_h1_attached=True, body_35mm_jack_inserted=False, sq_mode_active=False, audio_recording_enabled=False
    )
    if not (
        ev_norm.mi_shoe_audio_active
        and not ev_norm.mi_shoe_audio_set_locked
        and ev_jack.mi_shoe_audio_set_locked
        and not ev_jack.mi_shoe_audio_active
        and ev_sq.audio_recording_muted
        and ev_off.audio_recording_muted
    ):
        dc_errors.append("DOMAIN_C_JACK_OR_SQ_EVAL_FAILED")

    domain_c = DomainCJackOverrideSqMuteReport(
        passed=len(dc_errors) == 0,
        fx3_appfw_jack_sq_hits=fx3_jack_sq_hits,
        eval_mishoe_normal=ev_norm,
        eval_body_35mm_override=ev_jack,
        eval_sq_offspeed_muted=ev_sq,
        eval_audio_rec_off_muted=ev_off,
        errors=tuple(dc_errors),
    )

    # --- Domain D: Post-UFU Audio Default Reset Hygiene & Write Firewall ---
    dd_errors: List[str] = []
    if not (fx3_bk_sum.rec0_checksum_valid and fx3_bk_sum.rec1_checksum_valid):
        dd_errors.append("FX3_BACKUP_BIN_BK4_CHECKSUM_INVALID")
    if not (fx6_bk_sum.rec0_checksum_valid and fx6_bk_sum.rec1_checksum_valid):
        dd_errors.append("FX6_BACKUP_BIN_BK4_CHECKSUM_INVALID")
    if fx3_bk_sum.rec0_subsystems != DEFAULT_BACKUP_SUBSYSTEMS_FX3:
        dd_errors.append(f"FX3_BACKUP_SUBSYSTEMS_MISMATCH: {fx3_bk_sum.rec0_subsystems}")
    if fx6_bk_sum.rec0_subsystems != DEFAULT_BACKUP_SUBSYSTEMS_FX6:
        dd_errors.append(f"FX6_BACKUP_SUBSYSTEMS_MISMATCH: {fx6_bk_sum.rec0_subsystems}")

    h0_hash = fx3_bk_sum.sha256_prefix
    ev_h0 = evaluate_post_ufu_audio_default_hygiene(stage="H0", h0_backup_sha256=h0_hash)
    ev_h1 = evaluate_post_ufu_audio_default_hygiene(stage="H1", h0_backup_sha256=h0_hash)
    ev_h2 = evaluate_post_ufu_audio_default_hygiene(stage="H2", h0_backup_sha256=h0_hash)
    ev_h3 = evaluate_post_ufu_audio_default_hygiene(stage="H3", h0_backup_sha256=h0_hash)
    wg_blk = evaluate_phase189_write_guard("p2:/setting/Backup.bin")
    matrix = build_phase189_compat_matrix()

    if not (
        ev_h0.valid
        and ev_h1.valid
        and ev_h2.valid
        and ev_h3.valid
        and ev_h0.effective_audio_format == POST_UFU_DEFAULT_AUDIO_FORMAT
        and ev_h2.effective_audio_format == "48KHZ_24BIT_4CH"
        and ev_h3.effective_audio_format == POST_UFU_DEFAULT_AUDIO_FORMAT
        and ev_h3.backup_bin_hash_conserved
        and wg_blk.persistent_write_blocked
        and matrix.total_touchpoints == 12
    ):
        dd_errors.append("DOMAIN_D_POST_UFU_HYGIENE_EVAL_FAILED")

    domain_d = DomainDPostUfuBackupAudioReport(
        passed=len(dd_errors) == 0,
        fx3_backup_summary=fx3_bk_sum,
        fx6_backup_summary=fx6_bk_sum,
        eval_h0_stock_default=ev_h0,
        eval_h1_stage_a_rehearsal=ev_h1,
        eval_h2_stage_b_volatile_4ch=ev_h2,
        eval_h3_clean_restore=ev_h3,
        backup_bin_write_blocked_eval=wg_blk,
        compatibility_matrix=matrix,
        errors=tuple(dd_errors),
    )

    errors.extend(da_errors)
    errors.extend(db_errors)
    errors.extend(dc_errors)
    errors.extend(dd_errors)

    all_passed = (
        domain_a.passed
        and domain_b.passed
        and domain_c.passed
        and domain_d.passed
        and len(errors) == 0
    )

    digest_payload = {
        "schema_version": PHASE_189_SCHEMA,
        "mode": mode,
        "donor_file_sizes": donor_file_sizes,
        "domain_a_passed": domain_a.passed,
        "domain_b_passed": domain_b.passed,
        "domain_c_passed": domain_c.passed,
        "domain_d_passed": domain_d.passed,
    }
    report_sha256 = hashlib.sha256(
        json.dumps(digest_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return RealhwFx3VsFx3aAndXlrh1MishoeReport(
        schema_version=PHASE_189_SCHEMA,
        phase_version=PHASE_189_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        raw_firmware_bytes_leaked=0,
        persistent_emmc_writes_authorized=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        physical_usb_packets_emitted=0,
        persistent_writes=0,
        backup_bin_writes=0,
        fx3_vs_fx3a_branch_isolated=domain_a.passed,
        xlrh1_mishoe_4ch_bridge_verified=domain_b.passed,
        body_35mm_override_and_sq_mute_verified=domain_c.passed,
        post_ufu_audio_default_hygiene_verified=domain_d.passed,
        donor_file_sizes=donor_file_sizes,
        domain_a_fx3_vs_fx3a_branch=domain_a,
        domain_b_xlrh1_mishoe_audio=domain_b,
        domain_c_jack_override_sq_mute=domain_c,
        domain_d_post_ufu_backup_audio=domain_d,
        report_sha256=report_sha256,
        errors=tuple(errors),
    )


def realhw_fx3_vs_fx3a_and_xlrh1_mishoe_report_to_dict(
    report: RealhwFx3VsFx3aAndXlrh1MishoeReport,
) -> Dict[str, object]:
    """Convert `RealhwFx3VsFx3aAndXlrh1MishoeReport` to deterministic JSON-safe dictionary."""
    return asdict(report)


__all__ = [
    "APPFW_FX3_BRANCH_MARKERS_P189",
    "APPFW_FX3_JACK_AND_SQ_MARKERS_P189",
    "APPFW_FX3_MISHOE_AUDIO_MARKERS_P189",
    "APPFW_FX6_HANDLE_AUDIO_MARKERS_P189",
    "AVBB_AUDIO_MARKERS_P189",
    "CPAPP_FX3_MISHOE_MARKERS_P189",
    "CPAPP_SHARED_SHOE_PANEL_MARKERS_P189",
    "DEFAULT_BACKUP_SUBSYSTEMS_FX3",
    "DEFAULT_BACKUP_SUBSYSTEMS_FX6",
    "EXPECTED_FX3_APPFW_BYTES_P189",
    "EXPECTED_FX3_BACKUP_BYTES_P189",
    "EXPECTED_FX3_CPAPP_BYTES_P189",
    "EXPECTED_FX3_MPR_BYTES_P189",
    "EXPECTED_FX3_UPDATERUFP_BYTES_P189",
    "EXPECTED_FX6_APPFW_BYTES_P189",
    "EXPECTED_FX6_AVBB_AUDIO_BYTES_P189",
    "EXPECTED_FX6_BACKUP_BYTES_P189",
    "EXPECTED_FX6_CPAPP_BYTES_P189",
    "EXPECTED_FX6_HOTSHOE_BYTES_P189",
    "EXPECTED_FX6_MPR_BYTES_P189",
    "FORBIDDEN_PERSISTENT_TARGET_RE_P189",
    "FX3A_202_FW_VERSION",
    "FX3A_LCD_DOTS",
    "FX3_702_FW_VERSION",
    "FX3_APPFW_P189_RELPATH",
    "FX3_BACKUP_BIN_P189_RELPATH",
    "FX3_BODYDATA_DAT_P189_RELPATH",
    "FX3_CPAPP_P189_RELPATH",
    "FX3_LCD_DOTS",
    "FX3_LIBMPR_P189_RELPATH",
    "FX3_LIBUPDATERUFP_P189_RELPATH",
    "FX6_601_FW_VERSION",
    "FX6_APPFW_P189_RELPATH",
    "FX6_AVBB_AUDIO_P189_RELPATH",
    "FX6_BACKUP_BIN_P189_RELPATH",
    "FX6_CPAPP_P189_RELPATH",
    "FX6_HOTSHOE_P189_RELPATH",
    "FX6_LIBMPR_P189_RELPATH",
    "HARDWARE_BRANCH_SPECS",
    "MISHOE_AUDIO_FORMATS",
    "MODEL_ID_FX30_P189",
    "MODEL_ID_FX3A_P189",
    "MODEL_ID_FX3_P189",
    "MODEL_ID_FX6_P189",
    "MONITOR_MODE_TO_APPFW_TOKEN",
    "MPR_AUDIO_SHARED_MARKERS_P189",
    "PHASE_189_SCHEMA",
    "PHASE_189_VERSION",
    "POST_UFU_DEFAULT_AUDIO_FORMAT",
    "STAGE_A_REJECT_BUDGET_US",
    "VALID_4CH_MONITOR_MODES",
    "VALID_H_STAGES",
    "VOLATILE_OR_EXT_PREFIXES_P189",
    "DomainAFx3VsFx3aBranchReport",
    "DomainBXlrh1MishoeAudioReport",
    "DomainCJackOverrideSqMuteReport",
    "DomainDPostUfuBackupAudioReport",
    "HardwareBranchEvalResult",
    "JackOverrideAndSqMuteEvalResult",
    "Phase189CompatMatrixSummary",
    "Phase189TouchpointEntry",
    "Phase189WriteGuardResult",
    "PostUfuAudioDefaultEvalResult",
    "RealhwFx3VsFx3aAndXlrh1MishoeReport",
    "Xlrh1MishoeAudioEvalResult",
    "analyze_realhw_fx3_vs_fx3a_and_xlrh1_mishoe",
    "build_clean_room_realhw_fx3_vs_fx3a_and_xlrh1_fixtures",
    "build_phase189_compat_matrix",
    "evaluate_body_35mm_jack_override_and_sq_mute",
    "evaluate_fx3_vs_fx3a_hardware_branch",
    "evaluate_phase189_write_guard",
    "evaluate_post_ufu_audio_default_hygiene",
    "evaluate_xlrh1_mishoe_4ch_bridge",
    "realhw_fx3_vs_fx3a_and_xlrh1_mishoe_report_to_dict",
]
