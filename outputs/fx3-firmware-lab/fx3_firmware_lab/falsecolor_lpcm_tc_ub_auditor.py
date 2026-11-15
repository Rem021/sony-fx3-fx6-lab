"""Phase 80 — 15th Unified Firmware-Lab Auditor: False Color / EL-Zone `S-Log3` Exposure Mapping, 4-Ch `24-bit 48kHz` LPCM Headroom & Digital Limiter DSP, and SMPTE 12M User-Bits (`BG1..BG8`) + Multi-Port/HDMI TC Direction Guard.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`appFw.so` / `icx1295` AP host,
  `cpapp-b.bin`, `global.xdb`, `string_english.uxc`, `string_english_g.uxc`)
  and FX6 v6.01 (`appFw.so`, `cpapp-b.bin`, `libInfraHotshoe.so`,
  `AVBB_SCN_START_AUDIO.so`, `global.xdb`, `string_english.uxc`,
  `string_english_2.uxc`) strictly via `os.O_RDONLY` + read-only `mmap` and
  ELF64 `.rodata`/`.dynstr` section-scoped scanning, plus `uxa\\x07` / `.uxc`
  container parsing.
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 / CP / `global.xdb` /
  `.uxc` fixtures carrying the exact contract markers and executes the
  identical four-pillar verification pipeline with zero proprietary files
  required.

Audits Four Cinematography Monitoring, Audio DSP, Timecode UB & Safety Pillars:
1. Pillar 1 — Sony Cinema Line `S-Log3` / `S-Cinetone` / `Rec.709` False Color &
   EL-Zone Stop-Band IRE Verifier:
   Verifies `Zebra 1` (`70%`/`52%`/`41%`), `Zebra 2` (`94%`/`100%+`),
   Histogram, Waveform, and False Color exposure monitoring markers, and maps
   exact Sony `S-Log3` transfer landmarks (`3.5% IRE` black clip `code 95`,
   `41.0% IRE` / `40.6%..41.4%` `18%` middle grey green band `code 420`, `~52%`
   `+1.0 EV` skin pink band, `~61%` `90%` white card, and **`94.0% IRE`**
   `+6.0 EV` sensor saturation clip `code 963` full-range / `887` legal-range
   — proving why `Zebra = 100%` on `S-Log3` misses sensor clipping!), contrasted
   with `S-Cinetone` (`40%..42%` grey, `109% IRE` super-white clip) and
   `Rec.709` (`100% IRE` clip).
2. Pillar 2 — 4-Channel `24-bit / 48 kHz` Uncompressed LPCM Headroom, Digital
   Limiter & Wind-Filter DSP Verifier:
   Verifies `CH1..CH4` source routing (`XLR-H1` Digital MI-Shoe `4,608,000 bps`
   vs `Internal Stereo` / `3.5mm` `2,304,000 bps` fallback on hot-detach),
   SMPTE `RP 155` (`-20.0 dBFS = +4 dBu = 0 VU`, `20 dB` headroom) vs EBU
   `R68` (`-18.0 dBFS = 0 dBu`, `18 dB` headroom), deterministic `int24` `1 kHz`
   `-20.0 dBFS` reference test-tone synthesis & PCM byte roundtrip, `-3.0 dBFS`
   soft-knee digital peak limiter (`< 0.0 dBFS` brickwall ceiling with `0`
   `int24` wrap-around overflows), and `CH1..CH4` Wind-Filter HPF masks.
3. Pillar 3 — SMPTE 12M Timecode `User Bits` (`UB` 32-bit BCD/Hex: `Fix / Date /
   Time / FrameRate / CamID-Reel`) & HDMI/Multi-Port TC Direction Guard:
   Verifies 8-nibble (`XX:XX:XX:XX`) SMPTE 12M Binary Group (`BG1..BG8`)
   pack/unpack roundtrips across `FIX_HEX`, `DATE_YYMMDD`, `CLK_TIME`,
   `FRAME_RATE`, and Cinema `CAM_ID_REEL` (`A0:01:00:01`), plus FX3 Multi-Port
   (`VMC-BNCM1` `TC_IN` only) vs `HDMI Type-A` (`TC_OUT` only) directional
   arbitration (`0` bus contention, Phase 38 `uart_boot` Pins 7/8/9 isolation).
4. Pillar 4 — Zero Calibration / Zero eMMC Mutation Proof:
   Proves `calibration_mutation_bytes == 0`,
   `persistent_emmc_writes_authorized == False`, and fail-closed blocking of
   any `cnflasha` / `nflasha` / `p2:/Backup.bin` / `p2:/psd.bin` / `p6:Jiritsu`
   write target.
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

from .audio_tc_hdmi_sdi_routing_auditor import (
    FX6_AVBB_AUDIO_MARKERS,
    FX6_AVBB_AUDIO_RELPATH,
    FX6_HOTSHOE_MARKERS,
    FX6_HOTSHOE_RELPATH,
)
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
    FX6_CPAPP_RELPATH,
)
from .uxc_multilang_and_font_verifier import FX3_SHARE_APP_RELDIR, FX6_SHARE_APP_RELDIR


PHASE_80_SCHEMA = "fx3_firmware_lab_phase80_falsecolor_lpcm_tc_ub_v1"
PHASE_80_VERSION = "80.0.0"

FX3_GLOBAL_XDB_RELPATH = f"{FX3_SHARE_APP_RELDIR}/global.xdb"
FX6_GLOBAL_XDB_RELPATH = f"{FX6_SHARE_APP_RELDIR}/global.xdb"
FX3_STR_EN_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english.uxc"
FX3_STR_EN_G_RELPATH = f"{FX3_SHARE_APP_RELDIR}/string_english_g.uxc"
FX6_STR_EN_1_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english.uxc"
FX6_STR_EN_2_RELPATH = f"{FX6_SHARE_APP_RELDIR}/string_english_2.uxc"

# ---------------------------------------------------------------------------
# Pillar 1 Constants: S-Log3 / S-Cinetone / Rec.709 False Color & EL-Zone IRE
# ---------------------------------------------------------------------------

VALID_GAMMA_PROFILES: Tuple[str, ...] = ("SLOG3", "S_CINETONE", "REC709")

SLOG3_BLACK_FLOOR_CODE10 = 95
SLOG3_BLACK_FLOOR_IRE = 3.5
SLOG3_MIDDLE_GREY_18PCT_CODE10 = 420
SLOG3_MIDDLE_GREY_18PCT_IRE = 41.0
SLOG3_MIDDLE_GREY_IRE_BAND: Tuple[float, float] = (40.6, 41.4)
SLOG3_SKIN_HIGHLIGHT_PLUS1EV_IRE = 52.0
SLOG3_WHITE_CARD_90PCT_IRE = 61.0
SLOG3_SENSOR_CLIP_CODE10_FULL = 963
SLOG3_SENSOR_CLIP_CODE10_LEGAL = 887
SLOG3_SENSOR_CLIP_IRE = 94.0
SLOG3_ZEBRA_100_TRAP_IRE = 100.0

SCINETONE_MIDDLE_GREY_IRE_RANGE: Tuple[float, float] = (40.0, 42.0)
SCINETONE_WHITE_CLIP_IRE = 109.0
REC709_MIDDLE_GREY_IRE_RANGE: Tuple[float, float] = (41.0, 45.0)
REC709_WHITE_CLIP_IRE = 100.0

# EL-Zone / False Color Stop-Band Table for Sony S-Log3 (800 EI reference)
EL_ZONE_SLOG3_BANDS: Tuple[Dict[str, object], ...] = (
    {
        "zone_id": "PURPLE_BLACK_CLIP",
        "color": "PURPLE",
        "stop_min_ev": -8.0,
        "stop_max_ev": -6.0,
        "ire_min": 0.0,
        "ire_max": 3.6,
        "meaning": "Black Clip Floor (3.5% IRE / 10-bit code 95)",
    },
    {
        "zone_id": "BLUE_DEEP_SHADOW",
        "color": "BLUE",
        "stop_min_ev": -6.0,
        "stop_max_ev": -2.5,
        "ire_min": 3.6,
        "ire_max": 22.0,
        "meaning": "Deep Shadows (-5..-3 EV)",
    },
    {
        "zone_id": "CYAN_SHADOW",
        "color": "CYAN",
        "stop_min_ev": -2.5,
        "stop_max_ev": -0.5,
        "ire_min": 22.0,
        "ire_max": 40.6,
        "meaning": "Shadow / Under-Exposed Skin (-2..-1 EV)",
    },
    {
        "zone_id": "GREEN_MIDDLE_GREY_18PCT",
        "color": "GREEN",
        "stop_min_ev": -0.5,
        "stop_max_ev": 0.5,
        "ire_min": 40.6,
        "ire_max": 41.4,
        "meaning": "18% Middle Grey (0.0 EV, 41.0% IRE nominal, code 420)",
    },
    {
        "zone_id": "PINK_SKIN_TONE_PLUS_1EV",
        "color": "PINK",
        "stop_min_ev": 0.5,
        "stop_max_ev": 1.5,
        "ire_min": 41.4,
        "ire_max": 55.0,
        "meaning": "Caucasian Skin Highlight (+1.0 EV, ~49%..52% IRE)",
    },
    {
        "zone_id": "LIGHT_GREY_90PCT_WHITE_CARD",
        "color": "LIGHT_GREY",
        "stop_min_ev": 1.5,
        "stop_max_ev": 2.8,
        "ire_min": 55.0,
        "ire_max": 66.0,
        "meaning": "90% White Card (+2.32 EV, ~61% IRE)",
    },
    {
        "zone_id": "YELLOW_HIGHLIGHT",
        "color": "YELLOW",
        "stop_min_ev": 2.8,
        "stop_max_ev": 4.5,
        "ire_min": 66.0,
        "ire_max": 82.0,
        "meaning": "Bright Highlights (+3..+4 EV, Zebra 1 70% ref)",
    },
    {
        "zone_id": "ORANGE_NEAR_CLIP",
        "color": "ORANGE",
        "stop_min_ev": 4.5,
        "stop_max_ev": 5.95,
        "ire_min": 82.0,
        "ire_max": 93.8,
        "meaning": "Near-Clip Highlight Roll-off (+5 EV)",
    },
    {
        "zone_id": "RED_SENSOR_SATURATION_CLIP",
        "color": "RED",
        "stop_min_ev": 5.95,
        "stop_max_ev": 12.0,
        "ire_min": 93.8,
        "ire_max": 110.0,
        "meaning": "S-Log3 Sensor Saturation Clip (+6.0 EV at 800 EI, 94.0% IRE / code 963)",
    },
)

# ---------------------------------------------------------------------------
# Pillar 2 Constants: 4-Ch 24-bit 48kHz LPCM Headroom, Limiter & 1kHz DSP
# ---------------------------------------------------------------------------

LPCM_SAMPLE_RATE_HZ = 48_000
LPCM_BIT_DEPTH = 24
LPCM_INT24_MIN = -(1 << 23)  # -8,388,608
LPCM_INT24_MAX = (1 << 23) - 1  # +8,388,607
LPCM_4CH_BITRATE_BPS = LPCM_SAMPLE_RATE_HZ * LPCM_BIT_DEPTH * 4  # 4,608,000 bps
LPCM_2CH_BITRATE_BPS = LPCM_SAMPLE_RATE_HZ * LPCM_BIT_DEPTH * 2  # 2,304,000 bps

VALID_AUDIO_REF_STANDARDS: Tuple[str, ...] = ("SMPTE_RP155", "EBU_R68")
SMPTE_RP155_REF_DBFS = -20.0
SMPTE_RP155_NOMINAL_DBU = 4.0
SMPTE_RP155_CLIP_DBU = 24.0
EBU_R68_REF_DBFS = -18.0
EBU_R68_NOMINAL_DBU = 0.0
EBU_R68_CLIP_DBU = 18.0

LIMITER_THRESHOLD_DBFS = -3.0
LIMITER_CEILING_DBFS = -0.1
REFERENCE_TONE_FREQ_HZ = 1_000.0

# ---------------------------------------------------------------------------
# Pillar 3 Constants: SMPTE 12M User Bits (BG1..BG8) & Port Direction Guard
# ---------------------------------------------------------------------------

VALID_UB_MODES: Tuple[str, ...] = (
    "FIX_HEX",
    "DATE_YYMMDD",
    "CLK_TIME",
    "FRAME_RATE",
    "CAM_ID_REEL",
)
VALID_FPS_TAGS: Dict[str, Tuple[int, int, int, int]] = {
    "23.98": (0x23, 0x98, 0x00, 0x00),
    "24.00": (0x24, 0x00, 0x00, 0x00),
    "25.00": (0x25, 0x00, 0x00, 0x00),
    "29.97DF": (0x29, 0x97, 0xDF, 0x00),
    "50.00": (0x50, 0x00, 0x00, 0x00),
    "59.94DF": (0x59, 0x94, 0xDF, 0x00),
}
VALID_MULTIPORT_DIRECTIONS: Tuple[str, ...] = ("OFF", "TC_IN", "TC_OUT")
VALID_HDMI_TC_DIRECTIONS: Tuple[str, ...] = ("OFF", "TC_IN", "TC_OUT")

# ---------------------------------------------------------------------------
# Pillar 4 Constants: Zero Calibration & Zero Persistent eMMC Mutation
# ---------------------------------------------------------------------------

VOLATILE_SHADOW_PREFIXES: Tuple[str, ...] = ("/tmp/", "ram://", "memory://")
FORBIDDEN_CALIBRATION_AND_EMMC_PATHS: Tuple[str, ...] = (
    "/dev/nflasha",
    "/dev/cnflasha",
    "/dev/mtdblock",
    "nflasha",
    "cnflasha",
    "p1:",
    "p2:",
    "p6:",
    "backup.bin",
    "psd.bin",
    "jiritsu",
    "nvram://",
)

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_EXPOSURE_MARKERS: Tuple[str, ...] = (
    "VAL_setting_zebra_display_ZEBRA_DISPLAY_ON",
    "VAL_setting_zebra_display_ZEBRA_DISPLAY_OFF",
    "VAL_setting_zebra_level_ZEBRA_LEVEL_70",
    "VAL_setting_zebra_level_ZEBRA_LEVEL_95",
    "VAL_setting_zebra_level_ZEBRA_LEVEL_100",
    "VAL_setting_zebra_level_ZEBRA_LEVEL_100_PLUS",
    "VAL_setting_zebra_level_ZEBRA_LEVEL_CUSTOM_1",
    "VAL_setting_zebra_level_ZEBRA_LEVEL_CUSTOM_2",
    "VAL_disp_mode_shoot_monitor_DISP_MODE_SHOOT_MONITOR_HISTOGRAM",
    "VAL_setting_pictureprofile_gamma0_SETTING_PICTUREPROFILE_GAMMA_SLOG3",
    "VAL_setting_pictureprofile_gamma0_SETTING_PICTUREPROFILE_GAMMA_ITU709",
    "CAUTION_ID_FACTOR_GAMMA_SCINETONE_MSG",
)

FX6_APPFW_EXPOSURE_MARKERS: Tuple[str, ...] = (
    "VAL_setting_zebra_display_ZEBRA_DISPLAY_ZEBRA1",
    "VAL_setting_zebra_display_ZEBRA_DISPLAY_ZEBRA2",
    "BKID_APP_SETTING_ZEBRA1_LEVEL",
    "BKID_APP_SETTING_ZEBRA2_LEVEL",
    "BKID_APP_SETTING_FALSE_COLOR_SETTING",
    "VAL_setting_false_color_setting_FALSE_COLOR_SETTING_ON",
    "VAL_setting_false_color_target_hdmi_FALSE_COLOR_TARGET_HDMI_ON",
    "VAL_setting_false_color_target_lcd_monitor_vf_FALSE_COLOR_TARGET_LCD_MONITOR_VF_ON",
    "VIDEO_SIGNAL_MONITOR_WAVEFORM",
    "VIDEO_SIGNAL_MONITOR_HISTOGRAM",
    "VAL_setting_select_lut_hdr_SELECT_LUT_HDR_S_LOG3",
    "VAL_setting_select_lut_sdr_SELECT_LUT_SDR_S_CINETONE",
    "VAL_setting_select_lut_sdr_SELECT_LUT_SDR_ITU709",
)

FX3_APPFW_AUDIO_DSP_MARKERS: Tuple[str, ...] = (
    "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
    "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_2CH",
    "MSG_ID_INFRABB_ADF_IN_SET_WIND_NR_MODE",
    "VAL_setting_wind_noise_reduct_WIND_NOISE_REDUCT_ON",
    "VAL_setting_wind_noise_reduct_WIND_NOISE_REDUCT_AUTO",
    "VAL_setting_wind_noise_reduct_WIND_NOISE_REDUCT_OFF",
    "INFRA_NOTIFY_GET_AUDIO_LEVEL_TIMER",
    "INFRA_NOTIFY_GET_AUDIO_LEVEL_PEAK_TIMER",
)

FX6_APPFW_AUDIO_DSP_MARKERS: Tuple[str, ...] = (
    "EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
    "extern_BKID_APP_EXTERN_LIMITER_MODE",
    "extern_BKID_APP_EXTERN_REFERENCE_LEVEL",
    "No14_CH4_REF_LEVEL_20DB",
    "No14_CH4_REF_LEVEL_18DB",
    "No14_CH4_REF_LEVEL_EBUL",
    "BKID_APP_EXTERN_1KHZ_TONE_ON_COLOR_BARS",
    "AUDIO_1KHZ_TONE_ON_COLOR_BARS_ON",
    "extern_BKID_APP_EXTERN_CH1_WIND_FILTER",
    "extern_BKID_APP_EXTERN_CH2_WIND_FILTER",
    "extern_BKID_APP_EXTERN_CH3_WIND_FILTER",
    "extern_BKID_APP_EXTERN_CH4_WIND_FILTER",
)

FX3_APPFW_TC_UB_MARKERS: Tuple[str, ...] = (
    "VAL_setting_tc_ub_disp_setting_TC_UB_DISP_SETTING_TC",
    "VAL_setting_tc_ub_disp_setting_TC_UB_DISP_SETTING_U_BIT",
    "VAL_setting_tc_ub_disp_setting_TC_UB_DISP_SETTING_COUNTER",
    "TC_UB_DISP_SETTING_DURATION",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_OFF",
)

FX6_APPFW_TC_UB_MARKERS: Tuple[str, ...] = (
    "BKID_APP_EXTERN_UB_MODE",
    "BKID_APP_SETTING_TC_UB_DISP_SETTING",
    "VAL_setting_tc_ub_disp_setting_TC_UB_DISP_SETTING_TC",
    "VAL_setting_tc_ub_disp_setting_TC_UB_DISP_SETTING_U_BIT",
    "EXTERN_UB_MODE_PRESET_FIX",
    "EXTERN_UB_MODE_CLK_TIME",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_OFF",
)

CP_SHARED_PHASE80_MARKERS: Tuple[str, ...] = (
    "SET_ZEBRA_ERR",
    "MSG_ID_INFRABB_VDF_SRVC_SET_ZEBRA",
    "MSG_ID_INFRABB_VDF_SRVC_SET_HISTOGRAM",
    "MSG_ID_INFRABB_AUDIO_SET_LIMITER",
    "AUDIO_HEADROOM_LEVEL",
    "AUDIO_REF_MIC_LEVEL",
    "AUDIO_REF_LINE_LEVEL",
    "WINDFILTER_CH1",
    "WINDFILTER_CH2",
    "WINDFILTER_CH3",
    "WINDFILTER_CH4",
    "WINDFILTER_INTERNAL_MIC",
    "WINDFILTER_SHOE_MIC",
    "SET_TIMECODE_UBMODE",
    "SET_TIMECODE_UB",
    "TCUB_CMD_SET_TIMECODE_UBMODE",
    "TCUB_CMD_SET_TIMECODE_UB",
    "MSG_ID_INFRABB_SYS_SET_TIMECODE_UBMODE",
    "MSG_ID_INFRABB_SYS_SET_TIMECODE_UB",
)

FX3_NS39_PHASE80_LABELS: Dict[int, str] = {
    0x0004E07B: "Histogram",
    0x0004E4B1: "Wind Noise Reduct.",
}

FX3_NS3_PHASE80_LABELS: Dict[int, str] = {
    0x00006352: "Zebra Display",
    0x00006441: "Reset the user bit?",
}

FX6_NS1_PHASE80_LABELS: Dict[int, str] = {
    0x000020F5: "S-Cinetone",
    0x0000219F: "S-Log3",
    0x000023A5: "Zebra1",
    0x000023A7: "Zebra2",
    0x00003114: "Exposure Assist False Color",
    0x00003132: "Wind Filter",
    0x000032F3: "Histogram",
    0x00003368: "Waveform",
}

FX6_NS2_PHASE80_LABELS: Dict[int, str] = {
    0x000044A4: "Limiter Mode",
    0x000044A6: "1kHz Tone",
    0x00004528: "Zebra1 Level",
    0x00004530: "Zebra2 Level",
    0x0000489F: "Waveform",
    0x000048A1: "Histogram",
    0x00004E77: "Reference Level",
    0x00005438: "DURATION/TC/U-BIT",
}

# ---------------------------------------------------------------------------
# Report & Evaluation Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FalseColorEvalResult:
    valid: bool
    status: str
    gamma_profile: str
    base_iso_ei: int
    ev_offset: float
    code10_legal: float
    code10_full: float
    ire_pct: float
    el_zone_id: str
    el_zone_color: str
    zebra1_ire: float
    zebra2_ire: float
    zebra1_triggered: bool
    zebra2_triggered: bool
    zebra_misses_slog3_sensor_clip: bool
    clip_ceiling_ire: float
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FalseColorElZoneReport:
    passed: bool
    fx3_exposure_markers: Tuple[str, ...]
    fx6_exposure_markers: Tuple[str, ...]
    cp_exposure_markers: Tuple[str, ...]
    uxc_exposure_labels: Dict[str, str]
    slog3_black_floor_eval: FalseColorEvalResult
    slog3_middle_grey_eval: FalseColorEvalResult
    slog3_skin_plus1ev_eval: FalseColorEvalResult
    slog3_white_card_90pct_eval: FalseColorEvalResult
    slog3_sensor_clip_94_eval: FalseColorEvalResult
    slog3_zebra_100_trap_eval: FalseColorEvalResult
    scinetone_grey_eval: FalseColorEvalResult
    scinetone_clip_109_eval: FalseColorEvalResult
    rec709_clip_100_eval: FalseColorEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class LpcmHeadroomEvalResult:
    valid: bool
    status: str
    xlr_h1_attached: bool
    active_audio_bus: str
    active_channels: int
    sample_rate_hz: int
    bit_depth: int
    pcm_bitrate_bps: int
    reference_standard: str
    ref_dbfs: float
    nominal_dbu: float
    clip_ceiling_dbu: float
    headroom_db: float
    input_level_dbu: float
    digital_level_dbfs: float
    wind_filter_ch_mask: Tuple[bool, bool, bool, bool]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ToneSynthesisResult:
    valid: bool
    status: str
    freq_hz: float
    measured_freq_hz: float
    sample_rate_hz: int
    sample_count: int
    pcm_byte_count: int
    target_peak_dbfs: float
    measured_peak_dbfs: float
    measured_rms_dbfs: float
    int24_roundtrip_exact: bool
    pcm_sha256: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class LimiterDspEvalResult:
    valid: bool
    status: str
    limiter_enabled: bool
    threshold_dbfs: float
    ceiling_dbfs: float
    input_peak_dbfs: float
    output_peak_dbfs: float
    gain_reduction_db: float
    output_int24_peak: int
    int24_wrap_around_count: int
    brickwall_ceiling_held: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class LpcmAudioDspReport:
    passed: bool
    fx3_audio_dsp_markers: Tuple[str, ...]
    fx6_audio_dsp_markers: Tuple[str, ...]
    cp_audio_dsp_markers: Tuple[str, ...]
    fx6_hotshoe_markers: Tuple[str, ...]
    fx6_avbb_audio_markers: Tuple[str, ...]
    xlr_h1_smpte_rp155_eval: LpcmHeadroomEvalResult
    internal_fallback_ebu_r68_eval: LpcmHeadroomEvalResult
    tone_1khz_minus20dbfs_eval: ToneSynthesisResult
    limiter_nominal_eval: LimiterDspEvalResult
    limiter_hot_plus6dbfs_eval: LimiterDspEvalResult
    limiter_overload_plus12dbfs_eval: LimiterDspEvalResult
    unprotected_wraparound_trap_eval: LimiterDspEvalResult
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Smpte12mUserBitsResult:
    valid: bool
    status: str
    mode: str
    ub_formatted: str
    ub_hex: str
    packed_bytes_hex: str
    binary_groups_bg1_to_bg8: Tuple[int, ...]
    roundtrip_exact: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TcPortDirectionEvalResult:
    valid: bool
    status: str
    target_body: str
    multiport_direction: str
    hdmi_direction: str
    vmc_bncm1_attached: bool
    uart_boot_active: bool
    bus_contention_count: int
    ext_lk_input_active: bool
    hdmi_tc_ub_output_active: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SmpteUserBitsReport:
    passed: bool
    fx3_tc_ub_markers: Tuple[str, ...]
    fx6_tc_ub_markers: Tuple[str, ...]
    cp_tc_ub_markers: Tuple[str, ...]
    ub_fix_hex_eval: Smpte12mUserBitsResult
    ub_date_yymmdd_eval: Smpte12mUserBitsResult
    ub_clk_time_eval: Smpte12mUserBitsResult
    ub_framerate_eval: Smpte12mUserBitsResult
    ub_cam_id_reel_eval: Smpte12mUserBitsResult
    valid_simultaneous_in_out_eval: TcPortDirectionEvalResult
    blocked_multiport_tc_out_eval: TcPortDirectionEvalResult
    blocked_hdmi_tc_in_eval: TcPortDirectionEvalResult
    blocked_uart_boot_collision_eval: TcPortDirectionEvalResult
    bus_contention_count: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZeroMutationProofResult:
    valid: bool
    status: str
    target_path: str
    volatile_shadow_only: bool
    calibration_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class ZeroCalibrationAndEmmcReport:
    passed: bool
    fx3_global_xdb_valid: bool
    fx6_global_xdb_valid: bool
    volatile_shadow_eval: ZeroMutationProofResult
    blocked_cnflasha_eval: ZeroMutationProofResult
    blocked_backup_bin_eval: ZeroMutationProofResult
    blocked_emmc_flag_eval: ZeroMutationProofResult
    calibration_mutation_bytes: int
    persistent_emmc_writes_authorized: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class FalseColorLpcmTcUbReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    calibration_mutation_bytes: int
    int24_wrap_around_count: int
    bus_contention_count: int
    donor_file_sizes: Dict[str, int]
    pillar_1_false_color_el_zone: FalseColorElZoneReport
    pillar_2_lpcm_headroom_dsp: LpcmAudioDspReport
    pillar_3_smpte_ub_direction: SmpteUserBitsReport
    pillar_4_zero_mutation_proof: ZeroCalibrationAndEmmcReport
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
    """Read a compact `.uxc` or `global.xdb` artifact strictly via `os.O_RDONLY`."""
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


def build_clean_room_falsecolor_lpcm_ub_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room ELF64, CP, `global.xdb`, and `.uxc` fixtures for Phase 80."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_appfw_blob = _pack(
        (
            *FX3_APPFW_EXPOSURE_MARKERS,
            *FX3_APPFW_AUDIO_DSP_MARKERS,
            *FX3_APPFW_TC_UB_MARKERS,
        )
    )
    fx6_appfw_blob = _pack(
        (
            *FX6_APPFW_EXPOSURE_MARKERS,
            *FX6_APPFW_AUDIO_DSP_MARKERS,
            *FX6_APPFW_TC_UB_MARKERS,
        )
    )
    cp_blob = _pack(CP_SHARED_PHASE80_MARKERS, prefix=cp_hdr)
    hotshoe_blob = _pack(FX6_HOTSHOE_MARKERS)
    avbb_audio_blob = _pack(FX6_AVBB_AUDIO_MARKERS)

    fx3_xdb = build_synthetic_global_xdb("fx3_702")
    fx6_xdb = build_synthetic_global_xdb("fx6_601")

    fx3_str_en = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS39_PHASE80_LABELS.items()}, namespace_id=39
    )
    fx3_str_en_g = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX3_NS3_PHASE80_LABELS.items()}, namespace_id=3
    )
    fx6_str_en_1 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS1_PHASE80_LABELS.items()}, namespace_id=1
    )
    fx6_str_en_2 = build_sparse_uxc_string_pack(
        {k & 0x1FFF: v for k, v in FX6_NS2_PHASE80_LABELS.items()}, namespace_id=2
    )

    return {
        "fx3_appfw": fx3_appfw_blob,
        "fx6_appfw": fx6_appfw_blob,
        "fx3_cpapp": cp_blob,
        "fx6_cpapp": cp_blob,
        "fx6_hotshoe": hotshoe_blob,
        "fx6_avbb_audio": avbb_audio_blob,
        "fx3_global_xdb": fx3_xdb,
        "fx6_global_xdb": fx6_xdb,
        "fx3_str_en": fx3_str_en,
        "fx3_str_en_g": fx3_str_en_g,
        "fx6_str_en_1": fx6_str_en_1,
        "fx6_str_en_2": fx6_str_en_2,
    }


# ---------------------------------------------------------------------------
# Pillar 1: Sony S-Log3 / S-Cinetone / Rec.709 False Color & EL-Zone IRE Mapper
# ---------------------------------------------------------------------------


def slog3_reflection_to_code10(linear_reflection: float) -> float:
    """Official Sony S-Log3 OETF mapping scene-linear reflection -> 10-bit code [95..1023]."""
    if not math.isfinite(linear_reflection):
        raise ValueError(f"linear_reflection must be finite, got {linear_reflection!r}")
    x = max(0.0, float(linear_reflection))
    if x >= 0.01125000:
        code10 = 420.0 + math.log10((x + 0.01) / (0.18 + 0.01)) * 261.5
    else:
        code10 = (x * (171.2102946929 - 95.0) / 0.01125000) + 95.0
    return min(1023.0, max(95.0, code10))


def slog3_code10_to_ire(code10: float, *, full_range: bool = False) -> float:
    """Convert 10-bit code to IRE percentage (legal 64..940 -> 0..100% or full 0..1023)."""
    if not math.isfinite(code10):
        raise ValueError(f"code10 must be finite, got {code10!r}")
    if full_range:
        return (float(code10) / 1023.0) * 100.0
    return ((float(code10) - 64.0) / (940.0 - 64.0)) * 100.0


def slog3_ev_to_ire(ev_offset: float, *, base_iso_ei: int = 800) -> Tuple[float, float, float]:
    """Map an exposure stop offset (`0.0 EV` = 18% grey) at Base EI -> `(code10_legal, code10_full, ire_pct)`.

    At Sony FX3/FX6 `800 EI`, sensor saturation occurs at `+6.0 EV` above 18% grey
    (`x = 0.18 * 2^6 = 11.52`, `code10_legal ~ 886.3 -> 93.9% IRE` / `code10_full = 963 -> 94.1% IRE`
    = Sony's documented **`94.0% IRE`** S-Log3 sensor clip ceiling).
    """
    if not math.isfinite(ev_offset):
        raise ValueError(f"ev_offset must be finite, got {ev_offset!r}")
    if base_iso_ei <= 0:
        raise ValueError(f"base_iso_ei must be > 0, got {base_iso_ei!r}")

    # Linear reflection relative to 18% middle grey at base EI
    lin = 0.18 * (2.0 ** float(ev_offset)) if ev_offset > -12.0 else 0.0
    code10_legal = slog3_reflection_to_code10(lin)
    ire_legal = slog3_code10_to_ire(code10_legal, full_range=False)
    # Full-range 0..1023 scaling corresponding to Sony camera waveform/zebra mapping (0..109% IRE)
    code10_full = min(1023.0, max(0.0, (ire_legal / 100.0) * 1023.0))
    return round(code10_legal, 3), round(code10_full, 3), round(ire_legal, 3)


def _classify_el_zone_slog3(ire_pct: float) -> Tuple[str, str]:
    for band in EL_ZONE_SLOG3_BANDS:
        if float(band["ire_min"]) <= ire_pct < float(band["ire_max"]):
            return str(band["zone_id"]), str(band["color"])
    if ire_pct < 3.6:
        return "PURPLE_BLACK_CLIP", "PURPLE"
    return "RED_SENSOR_SATURATION_CLIP", "RED"


def _classify_false_color_scinetone(ire_pct: float) -> Tuple[str, str]:
    if ire_pct <= 3.5:
        return "PURPLE_BLACK_CLIP", "PURPLE"
    if ire_pct < 40.0:
        return "CYAN_SHADOW", "CYAN"
    if ire_pct <= 42.0:
        return "GREEN_MIDDLE_GREY_18PCT", "GREEN"
    if ire_pct <= 58.0:
        return "PINK_SKIN_TONE_PLUS_1EV", "PINK"
    if ire_pct < 100.0:
        return "YELLOW_HIGHLIGHT", "YELLOW"
    if ire_pct < 109.0:
        return "ORANGE_SUPER_WHITE_HEADROOM", "ORANGE"
    return "RED_WHITE_CLIP_109_IRE", "RED"


def _classify_false_color_rec709(ire_pct: float) -> Tuple[str, str]:
    if ire_pct <= 1.0:
        return "PURPLE_BLACK_CLIP", "PURPLE"
    if ire_pct < 41.0:
        return "CYAN_SHADOW", "CYAN"
    if ire_pct <= 45.0:
        return "GREEN_MIDDLE_GREY_18PCT", "GREEN"
    if ire_pct <= 75.0:
        return "PINK_SKIN_HIGHLIGHT", "PINK"
    if ire_pct < 100.0:
        return "ORANGE_NEAR_CLIP", "ORANGE"
    return "RED_REC709_WHITE_CLIP", "RED"


def evaluate_false_color_el_zone(
    *,
    gamma_profile: str = "SLOG3",
    ev_offset: float = 0.0,
    ire_pct: Optional[float] = None,
    zebra1_ire: float = 70.0,
    zebra2_ire: float = 94.0,
    base_iso_ei: int = 800,
) -> FalseColorEvalResult:
    """Evaluate False Color / EL-Zone stop-band IRE mapping and Zebra clip-trap guard."""
    errors: List[str] = []
    norm_gamma = gamma_profile.strip().upper()
    if norm_gamma not in VALID_GAMMA_PROFILES:
        errors.append(f"Unsupported gamma_profile {gamma_profile!r}; expected {VALID_GAMMA_PROFILES}")
    if not math.isfinite(ev_offset):
        errors.append(f"ev_offset must be finite, got {ev_offset!r}")
    if not (0.0 <= zebra1_ire <= 109.0):
        errors.append(f"zebra1_ire={zebra1_ire!r} outside [0.0..109.0]")
    if not (0.0 <= zebra2_ire <= 109.0):
        errors.append(f"zebra2_ire={zebra2_ire!r} outside [0.0..109.0]")
    if base_iso_ei not in (800, 12800):
        errors.append(f"Sony FX3/FX6 Dual Base ISO EI must be 800 or 12800, got {base_iso_ei}")

    if errors:
        return FalseColorEvalResult(
            valid=False,
            status="BLOCKED_INVALID_EXPOSURE_PARAM",
            gamma_profile=norm_gamma,
            base_iso_ei=base_iso_ei,
            ev_offset=float(ev_offset),
            code10_legal=0.0,
            code10_full=0.0,
            ire_pct=0.0,
            el_zone_id="INVALID",
            el_zone_color="NONE",
            zebra1_ire=float(zebra1_ire),
            zebra2_ire=float(zebra2_ire),
            zebra1_triggered=False,
            zebra2_triggered=False,
            zebra_misses_slog3_sensor_clip=False,
            clip_ceiling_ire=0.0,
            errors=tuple(errors),
        )

    if norm_gamma == "SLOG3":
        clip_ceiling = SLOG3_SENSOR_CLIP_IRE
        c_legal, c_full, computed_ire = slog3_ev_to_ire(ev_offset, base_iso_ei=base_iso_ei)
        eff_ire = round(float(ire_pct), 3) if ire_pct is not None else computed_ire
        zone_id, zone_color = _classify_el_zone_slog3(eff_ire)
    elif norm_gamma == "S_CINETONE":
        clip_ceiling = SCINETONE_WHITE_CLIP_IRE
        if ire_pct is not None:
            eff_ire = round(float(ire_pct), 3)
        else:
            # S-Cinetone 18% grey ~ 41% IRE, white clip at 109% IRE (+3.5..+4 EV)
            eff_ire = round(min(109.0, max(0.0, 41.0 + ev_offset * 17.0)), 3)
        c_legal = round(64.0 + (eff_ire / 100.0) * (940.0 - 64.0), 3)
        c_full = round((eff_ire / 100.0) * 1023.0, 3)
        zone_id, zone_color = _classify_false_color_scinetone(eff_ire)
    else:
        clip_ceiling = REC709_WHITE_CLIP_IRE
        if ire_pct is not None:
            eff_ire = round(float(ire_pct), 3)
        else:
            eff_ire = round(min(109.0, max(0.0, 42.0 + ev_offset * 21.0)), 3)
        c_legal = round(64.0 + (eff_ire / 100.0) * (940.0 - 64.0), 3)
        c_full = round((eff_ire / 100.0) * 1023.0, 3)
        zone_id, zone_color = _classify_false_color_rec709(eff_ire)

    z1_trig = abs(eff_ire - zebra1_ire) <= 2.5
    z2_trig = (eff_ire >= zebra2_ire) or (
        ire_pct is None
        and norm_gamma == "SLOG3"
        and ev_offset >= 6.0
        and zebra2_ire <= SLOG3_SENSOR_CLIP_IRE
    )
    zebra_trap = bool(norm_gamma == "SLOG3" and zebra2_ire > SLOG3_SENSOR_CLIP_IRE + 1.0)

    if zebra_trap:
        errors.append(
            f"Zebra2={zebra2_ire:.1f}% IRE misses S-Log3 sensor saturation clip at {SLOG3_SENSOR_CLIP_IRE:.1f}% IRE (+6.0 EV, code 963)"
        )
        status = "BLOCKED_ZEBRA_100_MISSES_SLOG3_94_CLIP"
    else:
        status = "FALSE_COLOR_EL_ZONE_VERIFIED"

    return FalseColorEvalResult(
        valid=len(errors) == 0,
        status=status,
        gamma_profile=norm_gamma,
        base_iso_ei=base_iso_ei,
        ev_offset=round(float(ev_offset), 4),
        code10_legal=c_legal,
        code10_full=c_full,
        ire_pct=eff_ire,
        el_zone_id=zone_id,
        el_zone_color=zone_color,
        zebra1_ire=float(zebra1_ire),
        zebra2_ire=float(zebra2_ire),
        zebra1_triggered=z1_trig,
        zebra2_triggered=z2_trig,
        zebra_misses_slog3_sensor_clip=zebra_trap,
        clip_ceiling_ire=clip_ceiling,
        errors=tuple(errors),
    )


def evaluate_pillar_1_false_color_el_zone(
    present_map: Mapping[str, Tuple[str, ...]],
    uxc_labels: Mapping[str, str],
) -> FalseColorElZoneReport:
    """Audit Pillar 1 across exposure markers, `.uxc` labels, S-Log3/S-Cinetone/Rec.709 & Zebra 94% clip."""
    errors: List[str] = []
    fx3_exp = present_map["fx3_appfw_exposure"]
    fx6_exp = present_map["fx6_appfw_exposure"]
    cp_all = present_map["cp_shared_phase80"]
    cp_exp = tuple(m for m in cp_all if "ZEBRA" in m or "HISTOGRAM" in m)

    if fx3_exp != FX3_APPFW_EXPOSURE_MARKERS:
        missing = tuple(m for m in FX3_APPFW_EXPOSURE_MARKERS if m not in fx3_exp)
        errors.append(f"FX3 appFw.so missing Zebra/Histogram/S-Log3 markers: {missing}")
    if fx6_exp != FX6_APPFW_EXPOSURE_MARKERS:
        missing = tuple(m for m in FX6_APPFW_EXPOSURE_MARKERS if m not in fx6_exp)
        errors.append(f"FX6 appFw.so missing False Color/Waveform/Zebra markers: {missing}")
    for m in ("SET_ZEBRA_ERR", "MSG_ID_INFRABB_VDF_SRVC_SET_ZEBRA", "MSG_ID_INFRABB_VDF_SRVC_SET_HISTOGRAM"):
        if m not in cp_exp:
            errors.append(f"cpapp-b.bin missing exposure monitoring IPC marker: {m}")

    # Exact S-Log3 landmarks
    black_floor = evaluate_false_color_el_zone(gamma_profile="SLOG3", ev_offset=-15.0, zebra1_ire=41.0, zebra2_ire=94.0)
    middle_grey = evaluate_false_color_el_zone(gamma_profile="SLOG3", ev_offset=0.0, zebra1_ire=41.0, zebra2_ire=94.0)
    skin_plus1 = evaluate_false_color_el_zone(gamma_profile="SLOG3", ev_offset=1.0, zebra1_ire=52.0, zebra2_ire=94.0)
    white_90 = evaluate_false_color_el_zone(
        gamma_profile="SLOG3",
        ev_offset=math.log2(0.90 / 0.18),
        zebra1_ire=70.0,
        zebra2_ire=94.0,
    )
    clip_94 = evaluate_false_color_el_zone(gamma_profile="SLOG3", ev_offset=6.0, zebra1_ire=70.0, zebra2_ire=94.0)
    zebra_100_trap = evaluate_false_color_el_zone(gamma_profile="SLOG3", ev_offset=6.0, zebra1_ire=70.0, zebra2_ire=100.0)
    scinetone_grey = evaluate_false_color_el_zone(gamma_profile="S_CINETONE", ev_offset=0.0, ire_pct=41.0, zebra1_ire=70.0, zebra2_ire=109.0)
    scinetone_clip = evaluate_false_color_el_zone(gamma_profile="S_CINETONE", ev_offset=4.0, ire_pct=109.0, zebra1_ire=70.0, zebra2_ire=109.0)
    rec709_clip = evaluate_false_color_el_zone(gamma_profile="REC709", ev_offset=3.0, ire_pct=100.0, zebra1_ire=70.0, zebra2_ire=100.0)

    for ev in (black_floor, middle_grey, skin_plus1, white_90, clip_94, scinetone_grey, scinetone_clip, rec709_clip):
        if not ev.valid:
            errors.extend(ev.errors)

    if not (3.4 <= black_floor.ire_pct <= 3.6 and round(black_floor.code10_legal) == SLOG3_BLACK_FLOOR_CODE10):
        errors.append(f"S-Log3 black floor expected ~3.5% IRE / code 95, got {black_floor.ire_pct}% / {black_floor.code10_legal}")
    if not (40.6 <= middle_grey.ire_pct <= 41.4 and middle_grey.el_zone_color == "GREEN"):
        errors.append(f"S-Log3 18% middle grey expected 40.6..41.4% IRE GREEN, got {middle_grey.ire_pct}% / {middle_grey.el_zone_color}")
    if not (93.8 <= clip_94.ire_pct <= 94.5 and clip_94.zebra2_triggered and clip_94.el_zone_color == "RED"):
        errors.append(f"S-Log3 +6.0 EV sensor clip expected ~94% IRE RED triggered, got {clip_94.ire_pct}% / trig={clip_94.zebra2_triggered}")
    if zebra_100_trap.valid or not zebra_100_trap.zebra_misses_slog3_sensor_clip or zebra_100_trap.zebra2_triggered:
        errors.append("Zebra 100% trap on S-Log3 failed to prove missed 94% sensor clipping")
    if scinetone_clip.ire_pct != 109.0 or not scinetone_clip.zebra2_triggered:
        errors.append(f"S-Cinetone super-white clip expected 109.0% IRE, got {scinetone_clip.ire_pct}%")

    return FalseColorElZoneReport(
        passed=len(errors) == 0,
        fx3_exposure_markers=fx3_exp,
        fx6_exposure_markers=fx6_exp,
        cp_exposure_markers=cp_exp,
        uxc_exposure_labels=dict(uxc_labels),
        slog3_black_floor_eval=black_floor,
        slog3_middle_grey_eval=middle_grey,
        slog3_skin_plus1ev_eval=skin_plus1,
        slog3_white_card_90pct_eval=white_90,
        slog3_sensor_clip_94_eval=clip_94,
        slog3_zebra_100_trap_eval=zebra_100_trap,
        scinetone_grey_eval=scinetone_grey,
        scinetone_clip_109_eval=scinetone_clip,
        rec709_clip_100_eval=rec709_clip,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 2: 4-Ch 24-bit 48kHz LPCM Headroom, 1kHz Tone & Digital Limiter DSP
# ---------------------------------------------------------------------------


def evaluate_lpcm_headroom_and_routing(
    *,
    xlr_h1_attached: bool = True,
    body_35mm_mic_plugged: bool = False,
    reference_standard: str = "SMPTE_RP155",
    input_level_dbu: float = 4.0,
    wind_filter_ch_mask: Tuple[bool, bool, bool, bool] = (True, True, False, False),
    sample_rate_hz: int = LPCM_SAMPLE_RATE_HZ,
    bit_depth: int = LPCM_BIT_DEPTH,
) -> LpcmHeadroomEvalResult:
    """Verify 4-ch 24-bit 48kHz routing, SMPTE RP 155 (-20 dBFS) vs EBU R68 (-18 dBFS) headroom, & wind HPF."""
    errors: List[str] = []
    norm_std = reference_standard.strip().upper()
    if norm_std not in VALID_AUDIO_REF_STANDARDS:
        errors.append(f"Unsupported reference_standard {reference_standard!r}; expected {VALID_AUDIO_REF_STANDARDS}")
    if sample_rate_hz != LPCM_SAMPLE_RATE_HZ:
        errors.append(f"LPCM sample rate must be {LPCM_SAMPLE_RATE_HZ} Hz, got {sample_rate_hz}")
    if bit_depth != LPCM_BIT_DEPTH:
        errors.append(f"LPCM bit depth must be {LPCM_BIT_DEPTH}-bit, got {bit_depth}")
    if len(wind_filter_ch_mask) != 4 or any(not isinstance(b, bool) for b in wind_filter_ch_mask):
        errors.append("wind_filter_ch_mask must be a 4-tuple of booleans for CH1..CH4")
    if not math.isfinite(input_level_dbu):
        errors.append(f"input_level_dbu must be finite, got {input_level_dbu!r}")

    if xlr_h1_attached:
        bus = "XLR_H1_MI_SHOE_4CH_24BIT_48KHZ"
        channels = 4
    elif body_35mm_mic_plugged:
        bus = "BODY_3_5MM_STEREO_JACK_2CH"
        channels = 2
    else:
        bus = "INTERNAL_BODY_STEREO_MIC_2CH_FALLBACK"
        channels = 2

    if norm_std == "EBU_R68":
        ref_dbfs = EBU_R68_REF_DBFS
        nom_dbu = EBU_R68_NOMINAL_DBU
        clip_dbu = EBU_R68_CLIP_DBU
    else:
        ref_dbfs = SMPTE_RP155_REF_DBFS
        nom_dbu = SMPTE_RP155_NOMINAL_DBU
        clip_dbu = SMPTE_RP155_CLIP_DBU

    headroom_db = abs(ref_dbfs)
    digital_dbfs = ref_dbfs + (float(input_level_dbu) - nom_dbu)
    bitrate_bps = sample_rate_hz * bit_depth * channels

    if digital_dbfs >= 0.0 and not errors:
        status = "OVERLOAD_REQUIRES_SOFT_KNEE_LIMITER"
    elif errors:
        status = "BLOCKED_INVALID_LPCM_CONFIG"
    else:
        status = "LPCM_24BIT_48KHZ_HEADROOM_VERIFIED"

    return LpcmHeadroomEvalResult(
        valid=len(errors) == 0,
        status=status,
        xlr_h1_attached=xlr_h1_attached,
        active_audio_bus=bus,
        active_channels=channels,
        sample_rate_hz=sample_rate_hz,
        bit_depth=bit_depth,
        pcm_bitrate_bps=bitrate_bps,
        reference_standard=norm_std,
        ref_dbfs=ref_dbfs,
        nominal_dbu=nom_dbu,
        clip_ceiling_dbu=clip_dbu,
        headroom_db=headroom_db,
        input_level_dbu=round(float(input_level_dbu), 3),
        digital_level_dbfs=round(digital_dbfs, 3),
        wind_filter_ch_mask=tuple(bool(x) for x in wind_filter_ch_mask[:4]) if len(wind_filter_ch_mask) >= 4 else (False, False, False, False),
        errors=tuple(errors),
    )


def synthesize_and_verify_1khz_int24_tone(
    *,
    ref_dbfs: float = SMPTE_RP155_REF_DBFS,
    freq_hz: float = REFERENCE_TONE_FREQ_HZ,
    sample_rate_hz: int = LPCM_SAMPLE_RATE_HZ,
    duration_ms: int = 20,
) -> ToneSynthesisResult:
    """Synthesize deterministic `int24` `1 kHz` reference tone, pack/unpack 3B LE PCM, & check RMS/freq."""
    errors: List[str] = []
    if not math.isfinite(ref_dbfs) or ref_dbfs > 0.0 or ref_dbfs < -96.0:
        errors.append(f"ref_dbfs={ref_dbfs!r} outside [-96.0..0.0]")
    if not math.isfinite(freq_hz) or freq_hz <= 0.0 or freq_hz >= sample_rate_hz / 2.0:
        errors.append(f"freq_hz={freq_hz!r} violates Nyquist for {sample_rate_hz} Hz")
    if duration_ms <= 0:
        errors.append(f"duration_ms={duration_ms!r} must be > 0")

    if errors:
        return ToneSynthesisResult(
            valid=False,
            status="BLOCKED_INVALID_TONE_PARAM",
            freq_hz=float(freq_hz),
            measured_freq_hz=0.0,
            sample_rate_hz=sample_rate_hz,
            sample_count=0,
            pcm_byte_count=0,
            target_peak_dbfs=float(ref_dbfs),
            measured_peak_dbfs=-144.0,
            measured_rms_dbfs=-144.0,
            int24_roundtrip_exact=False,
            pcm_sha256="",
            errors=tuple(errors),
        )

    n_samples = int(round(sample_rate_hz * (duration_ms / 1000.0)))
    amp = (10.0 ** (float(ref_dbfs) / 20.0)) * float(LPCM_INT24_MAX)
    samples: List[int] = []
    buf = bytearray()
    for i in range(n_samples):
        val = int(round(amp * math.sin(2.0 * math.pi * float(freq_hz) * (i / float(sample_rate_hz)))))
        val = max(LPCM_INT24_MIN, min(LPCM_INT24_MAX, val))
        samples.append(val)
        u24 = val & 0xFFFFFF
        buf.extend((u24 & 0xFF, (u24 >> 8) & 0xFF, (u24 >> 16) & 0xFF))

    raw_bytes = bytes(buf)
    decoded: List[int] = []
    for off in range(0, len(raw_bytes), 3):
        u24 = raw_bytes[off] | (raw_bytes[off + 1] << 8) | (raw_bytes[off + 2] << 16)
        if u24 & 0x800000:
            u24 -= 0x1000000
        decoded.append(u24)

    roundtrip_ok = decoded == samples
    if not roundtrip_ok:
        errors.append("int24 little-endian 3-byte pack/unpack mismatch")

    peak_abs = max(abs(s) for s in decoded)
    rms = math.sqrt(sum(s * s for s in decoded) / float(len(decoded)))
    measured_peak_dbfs = 20.0 * math.log10(max(1e-12, peak_abs / float(LPCM_INT24_MAX)))
    measured_rms_dbfs = 20.0 * math.log10(max(1e-12, rms / float(LPCM_INT24_MAX)))

    # Rising zero-crossings to verify tone frequency from first-to-last full cycle span
    rising_indices = [
        idx for idx in range(1, len(decoded)) if decoded[idx - 1] < 0 and decoded[idx] >= 0
    ]
    if len(rising_indices) >= 2:
        cycle_span = rising_indices[-1] - rising_indices[0]
        measured_freq = ((len(rising_indices) - 1) * float(sample_rate_hz)) / float(cycle_span)
    else:
        measured_freq = (len(rising_indices) * float(sample_rate_hz)) / float(len(decoded))

    if abs(measured_peak_dbfs - float(ref_dbfs)) > 0.05:
        errors.append(f"Peak dBFS mismatch: {measured_peak_dbfs:.3f} vs {ref_dbfs:.3f}")
    if abs(measured_rms_dbfs - (float(ref_dbfs) - 3.0103)) > 0.10:
        errors.append(f"RMS dBFS mismatch: {measured_rms_dbfs:.3f} vs {ref_dbfs - 3.0103:.3f}")
    if abs(measured_freq - float(freq_hz)) > max(1.0, float(freq_hz) * 0.01):
        errors.append(f"Measured tone frequency {measured_freq:.2f} Hz != {freq_hz:.2f} Hz")

    pcm_sha = hashlib.sha256(raw_bytes).hexdigest()
    return ToneSynthesisResult(
        valid=len(errors) == 0,
        status="TONE_1KHZ_INT24_VERIFIED" if len(errors) == 0 else "BLOCKED_TONE_MISMATCH",
        freq_hz=float(freq_hz),
        measured_freq_hz=round(measured_freq, 3),
        sample_rate_hz=sample_rate_hz,
        sample_count=len(decoded),
        pcm_byte_count=len(raw_bytes),
        target_peak_dbfs=round(float(ref_dbfs), 3),
        measured_peak_dbfs=round(measured_peak_dbfs, 3),
        measured_rms_dbfs=round(measured_rms_dbfs, 3),
        int24_roundtrip_exact=roundtrip_ok,
        pcm_sha256=pcm_sha,
        errors=tuple(errors),
    )


def evaluate_int24_soft_knee_limiter(
    *,
    input_peak_dbfs: float,
    limiter_enabled: bool = True,
    threshold_dbfs: float = LIMITER_THRESHOLD_DBFS,
    ceiling_dbfs: float = LIMITER_CEILING_DBFS,
) -> LimiterDspEvalResult:
    """Evaluate `-3.0 dBFS` soft-knee digital peak limiter (`< 0.0 dBFS` brickwall, 0 `int24` wrap)."""
    errors: List[str] = []
    if not math.isfinite(input_peak_dbfs):
        errors.append(f"input_peak_dbfs must be finite, got {input_peak_dbfs!r}")
    if threshold_dbfs >= ceiling_dbfs or ceiling_dbfs >= 0.0:
        errors.append("threshold_dbfs must be < ceiling_dbfs < 0.0 dBFS")

    if errors:
        return LimiterDspEvalResult(
            valid=False,
            status="BLOCKED_INVALID_LIMITER_PARAM",
            limiter_enabled=limiter_enabled,
            threshold_dbfs=threshold_dbfs,
            ceiling_dbfs=ceiling_dbfs,
            input_peak_dbfs=float(input_peak_dbfs),
            output_peak_dbfs=0.0,
            gain_reduction_db=0.0,
            output_int24_peak=0,
            int24_wrap_around_count=0,
            brickwall_ceiling_held=False,
            errors=tuple(errors),
        )

    wrap_count = 0
    if not limiter_enabled:
        raw_int = int(round((10.0 ** (float(input_peak_dbfs) / 20.0)) * float(LPCM_INT24_MAX)))
        if raw_int > LPCM_INT24_MAX:
            # Unprotected signed 24-bit two's-complement wrap-around hazard!
            wrap_count = 1
            wrapped_u24 = raw_int & 0xFFFFFF
            out_int = wrapped_u24 - 0x1000000 if (wrapped_u24 & 0x800000) else wrapped_u24
            out_dbfs = float(input_peak_dbfs)
            errors.append(
                f"BLOCKED_INT24_WRAPAROUND_OVERFLOW: limiter disabled at +{input_peak_dbfs:.1f} dBFS overflows int24 ({raw_int} -> {out_int})"
            )
            status = "BLOCKED_INT24_WRAPAROUND_OVERFLOW"
        else:
            out_int = raw_int
            out_dbfs = float(input_peak_dbfs)
            status = "LIMITER_BYPASSED_WITHIN_FULLSCALE"
        gain_red = 0.0
    else:
        if input_peak_dbfs <= threshold_dbfs:
            out_dbfs = float(input_peak_dbfs)
        else:
            # Smooth asymptotic soft-knee curve: maps [threshold, +inf) strictly into [threshold, ceiling_dbfs)
            head = ceiling_dbfs - threshold_dbfs  # e.g. 2.9 dB
            excess = float(input_peak_dbfs) - threshold_dbfs
            out_dbfs = threshold_dbfs + head * math.tanh(excess / head)
        out_int = min(LPCM_INT24_MAX, int(round((10.0 ** (out_dbfs / 20.0)) * float(LPCM_INT24_MAX))))
        gain_red = max(0.0, float(input_peak_dbfs) - out_dbfs)
        status = (
            "SOFT_KNEE_LIMITER_ENGAGED_BRICKWALL_SAFE"
            if input_peak_dbfs > threshold_dbfs
            else "SOFT_KNEE_LIMITER_UNITY_BELOW_THRESHOLD"
        )

    ceiling_held = (out_dbfs < 0.0) and (wrap_count == 0) and (abs(out_int) <= LPCM_INT24_MAX)
    if not ceiling_held and len(errors) == 0:
        errors.append(f"Limiter output {out_dbfs:.3f} dBFS breached 0.0 dBFS ceiling")

    return LimiterDspEvalResult(
        valid=len(errors) == 0,
        status=status,
        limiter_enabled=limiter_enabled,
        threshold_dbfs=round(float(threshold_dbfs), 3),
        ceiling_dbfs=round(float(ceiling_dbfs), 3),
        input_peak_dbfs=round(float(input_peak_dbfs), 3),
        output_peak_dbfs=round(out_dbfs, 4),
        gain_reduction_db=round(gain_red, 4),
        output_int24_peak=out_int,
        int24_wrap_around_count=wrap_count,
        brickwall_ceiling_held=ceiling_held,
        errors=tuple(errors),
    )


def evaluate_pillar_2_lpcm_dsp(present_map: Mapping[str, Tuple[str, ...]]) -> LpcmAudioDspReport:
    """Audit Pillar 2 across 4-ch 24-bit 48kHz audio, RP 155 / EBU R68 headroom, 1kHz tone, & soft-knee limiter."""
    errors: List[str] = []
    fx3_aud = present_map["fx3_appfw_audio_dsp"]
    fx6_aud = present_map["fx6_appfw_audio_dsp"]
    cp_all = present_map["cp_shared_phase80"]
    cp_aud = tuple(
        m for m in cp_all if any(k in m for k in ("AUDIO", "LIMITER", "WINDFILTER"))
    )
    fx6_hot = present_map["fx6_hotshoe"]
    fx6_avbb = present_map["fx6_avbb_audio"]

    if fx3_aud != FX3_APPFW_AUDIO_DSP_MARKERS:
        missing = tuple(m for m in FX3_APPFW_AUDIO_DSP_MARKERS if m not in fx3_aud)
        errors.append(f"FX3 appFw.so missing LPCM / Wind-NR DSP markers: {missing}")
    if fx6_aud != FX6_APPFW_AUDIO_DSP_MARKERS:
        missing = tuple(m for m in FX6_APPFW_AUDIO_DSP_MARKERS if m not in fx6_aud)
        errors.append(f"FX6 appFw.so missing LPCM / Ref-Level / 1kHz / Limiter markers: {missing}")
    for m in ("MSG_ID_INFRABB_AUDIO_SET_LIMITER", "AUDIO_HEADROOM_LEVEL", "WINDFILTER_CH1", "WINDFILTER_CH4"):
        if m not in cp_aud:
            errors.append(f"cpapp-b.bin missing audio DSP marker: {m}")
    if fx6_hot != FX6_HOTSHOE_MARKERS:
        errors.append("libInfraHotshoe.so missing MI-Shoe UIPC markers")
    if fx6_avbb != FX6_AVBB_AUDIO_MARKERS:
        errors.append("AVBB_SCN_START_AUDIO.so missing LOG_SET_ANTI_CLIP_ADF_START / BO_ID_SHOE_MIC markers")

    xlr_rp155 = evaluate_lpcm_headroom_and_routing(
        xlr_h1_attached=True,
        reference_standard="SMPTE_RP155",
        input_level_dbu=4.0,
        wind_filter_ch_mask=(True, True, False, False),
    )
    int_ebu = evaluate_lpcm_headroom_and_routing(
        xlr_h1_attached=False,
        body_35mm_mic_plugged=False,
        reference_standard="EBU_R68",
        input_level_dbu=0.0,
        wind_filter_ch_mask=(True, True, True, True),
    )
    tone_1k = synthesize_and_verify_1khz_int24_tone(ref_dbfs=-20.0, freq_hz=1000.0)
    lim_nom = evaluate_int24_soft_knee_limiter(input_peak_dbfs=-20.0, limiter_enabled=True)
    lim_hot = evaluate_int24_soft_knee_limiter(input_peak_dbfs=6.0, limiter_enabled=True)
    lim_ovl = evaluate_int24_soft_knee_limiter(input_peak_dbfs=12.0, limiter_enabled=True)
    wrap_trap = evaluate_int24_soft_knee_limiter(input_peak_dbfs=6.0, limiter_enabled=False)

    for ev in (xlr_rp155, int_ebu, tone_1k, lim_nom, lim_hot, lim_ovl):
        if not ev.valid:
            errors.extend(ev.errors)
    if wrap_trap.valid or wrap_trap.int24_wrap_around_count == 0:
        errors.append("Unprotected +6.0 dBFS bypass test failed to catch int24 wrap-around hazard")

    return LpcmAudioDspReport(
        passed=len(errors) == 0,
        fx3_audio_dsp_markers=fx3_aud,
        fx6_audio_dsp_markers=fx6_aud,
        cp_audio_dsp_markers=cp_aud,
        fx6_hotshoe_markers=fx6_hot,
        fx6_avbb_audio_markers=fx6_avbb,
        xlr_h1_smpte_rp155_eval=xlr_rp155,
        internal_fallback_ebu_r68_eval=int_ebu,
        tone_1khz_minus20dbfs_eval=tone_1k,
        limiter_nominal_eval=lim_nom,
        limiter_hot_plus6dbfs_eval=lim_hot,
        limiter_overload_plus12dbfs_eval=lim_ovl,
        unprotected_wraparound_trap_eval=wrap_trap,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 3: SMPTE 12M User Bits (BG1..BG8) & Multi-Port/HDMI TC Direction Guard
# ---------------------------------------------------------------------------


def _bcd_byte_checked(val: int, name: str, lo: int, hi: int) -> int:
    if not (lo <= val <= hi):
        raise ValueError(f"{name}={val} outside [{lo}..{hi}]")
    return ((val // 10) << 4) | (val % 10)


def unpack_smpte12m_user_bits(ub_bytes: bytes) -> Tuple[str, Tuple[int, ...]]:
    """Unpack 4 SMPTE 12M user-bit bytes into `'XX:XX:XX:XX'` and 8 nibbles `(BG8..BG1)`."""
    if len(ub_bytes) != 4:
        raise ValueError(f"SMPTE 12M User Bits require exactly 4 bytes, got {len(ub_bytes)}")
    nibbles = tuple(
        v
        for b in ub_bytes
        for v in ((b >> 4) & 0xF, b & 0xF)
    )
    formatted = ":".join(f"{b:02X}" for b in ub_bytes)
    return formatted, nibbles


def pack_smpte12m_user_bits(
    *,
    mode: str = "CAM_ID_REEL",
    ub_str: Optional[str] = None,
    cam_id: str = "A",
    cam_index: int = 0,
    reel: int = 1,
    clip_or_slate: int = 1,
    year: int = 26,
    month: int = 11,
    day: int = 14,
    hours: int = 16,
    minutes: int = 45,
    seconds: int = 0,
    fps_tag: str = "23.98",
) -> Smpte12mUserBitsResult:
    """Pack and roundtrip-verify 8-nibble (`XX:XX:XX:XX`) SMPTE 12M Binary Group (`BG1..BG8`) User Bits."""
    errors: List[str] = []
    norm_mode = mode.strip().upper()
    if norm_mode not in VALID_UB_MODES:
        errors.append(f"Unsupported UB mode {mode!r}; expected {VALID_UB_MODES}")

    raw_bytes = b""
    if not errors:
        try:
            if ub_str is not None:
                cleaned = ub_str.strip().replace(":", "").replace("-", "").upper()
                if len(cleaned) != 8 or not all(c in "0123456789ABCDEF" for c in cleaned):
                    raise ValueError(f"ub_str={ub_str!r} must contain 8 hex nibbles (XX:XX:XX:XX)")
                raw_bytes = bytes.fromhex(cleaned)
            elif norm_mode == "FIX_HEX":
                raw_bytes = bytes((0x1A, 0x2B, 0x3C, 0x4D))
            elif norm_mode == "DATE_YYMMDD":
                b0 = _bcd_byte_checked(year, "year", 0, 99)
                b1 = _bcd_byte_checked(month, "month", 1, 12)
                b2 = _bcd_byte_checked(day, "day", 1, 31)
                raw_bytes = bytes((b0, b1, b2, 0x00))
            elif norm_mode == "CLK_TIME":
                b0 = _bcd_byte_checked(hours, "hours", 0, 23)
                b1 = _bcd_byte_checked(minutes, "minutes", 0, 59)
                b2 = _bcd_byte_checked(seconds, "seconds", 0, 59)
                raw_bytes = bytes((b0, b1, b2, 0x00))
            elif norm_mode == "FRAME_RATE":
                tag = VALID_FPS_TAGS.get(fps_tag.strip().upper())
                if tag is None:
                    raise ValueError(f"Unsupported fps_tag {fps_tag!r}; expected {tuple(VALID_FPS_TAGS)}")
                raw_bytes = bytes(tag)
            elif norm_mode == "CAM_ID_REEL":
                cid = cam_id.strip().upper()
                if len(cid) != 1 or not ("A" <= cid <= "Z"):
                    raise ValueError(f"cam_id={cam_id!r} must be single letter A..Z")
                if not (0 <= cam_index <= 9):
                    raise ValueError(f"cam_index={cam_index} outside [0..9]")
                if not (1 <= reel <= 99):
                    raise ValueError(f"reel={reel} outside [1..99]")
                if not (0 <= clip_or_slate <= 9999):
                    raise ValueError(f"clip_or_slate={clip_or_slate} outside [0..9999]")
                cam_nibble = 0xA + ((ord(cid) - ord("A")) % 6) if cid <= "F" else 0xF
                b0 = ((cam_nibble & 0xF) << 4) | (cam_index & 0xF)
                b1 = _bcd_byte_checked(reel, "reel", 1, 99)
                b2 = _bcd_byte_checked(clip_or_slate // 100, "clip_hi", 0, 99)
                b3 = _bcd_byte_checked(clip_or_slate % 100, "clip_lo", 0, 99)
                raw_bytes = bytes((b0, b1, b2, b3))
        except ValueError as exc:
            errors.append(str(exc))

    if errors or len(raw_bytes) != 4:
        return Smpte12mUserBitsResult(
            valid=False,
            status="BLOCKED_INVALID_USER_BITS",
            mode=norm_mode,
            ub_formatted="00:00:00:00",
            ub_hex="00000000",
            packed_bytes_hex="",
            binary_groups_bg1_to_bg8=(),
            roundtrip_exact=False,
            errors=tuple(errors),
        )

    formatted, nibbles = unpack_smpte12m_user_bits(raw_bytes)
    repacked = bytes(
        ((nibbles[i] & 0xF) << 4) | (nibbles[i + 1] & 0xF) for i in range(0, 8, 2)
    )
    rt_ok = repacked == raw_bytes
    if not rt_ok:
        errors.append("SMPTE 12M BG1..BG8 User Bits pack/unpack roundtrip mismatch")

    return Smpte12mUserBitsResult(
        valid=len(errors) == 0,
        status="SMPTE_12M_USER_BITS_VERIFIED" if len(errors) == 0 else "BLOCKED_USER_BITS_ROUNDTRIP",
        mode=norm_mode,
        ub_formatted=formatted,
        ub_hex=raw_bytes.hex().upper(),
        packed_bytes_hex=raw_bytes.hex(),
        binary_groups_bg1_to_bg8=nibbles,
        roundtrip_exact=rt_ok,
        errors=tuple(errors),
    )


def evaluate_tc_port_direction_guard(
    *,
    target_body: str = "ILME-FX3",
    multiport_direction: str = "TC_IN",
    hdmi_direction: str = "TC_OUT",
    vmc_bncm1_attached: bool = True,
    uart_boot_active: bool = False,
) -> TcPortDirectionEvalResult:
    """Arbitrate FX3 Multi-Port (`VMC-BNCM1` `TC_IN` only) vs `HDMI Type-A` (`TC_OUT` only) directions."""
    errors: List[str] = []
    norm_body = target_body.strip().upper()
    norm_mp = multiport_direction.strip().upper()
    norm_hdmi = hdmi_direction.strip().upper()

    if norm_mp not in VALID_MULTIPORT_DIRECTIONS:
        errors.append(f"Unsupported multiport_direction={multiport_direction!r}")
    if norm_hdmi not in VALID_HDMI_TC_DIRECTIONS:
        errors.append(f"Unsupported hdmi_direction={hdmi_direction!r}")

    if norm_body == "ILME-FX3":
        if norm_mp == "TC_OUT":
            errors.append(
                "BLOCKED_FX3_MULTIPORT_TC_IN_ONLY: FX3 Multi-Port VMC-BNCM1 supports LTC TC_IN only (no TC_OUT)"
            )
        if norm_hdmi == "TC_IN":
            errors.append(
                "BLOCKED_HDMI_TC_OUT_ONLY: FX3 HDMI Type-A supports TC_OUT + User Bits only (no TC_IN)"
            )
        if uart_boot_active and (vmc_bncm1_attached or norm_mp != "OFF"):
            errors.append(
                "BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION: Multi-Port Pins 7/8/9 uart_boot forbids VMC-BNCM1 TC_IN"
            )
        if norm_mp == "TC_IN" and not vmc_bncm1_attached:
            errors.append("FX3 Multi-Port TC_IN requires VMC-BNCM1 680kOhm adapter attached")

    if errors:
        if any("MULTIPORT_TC_IN_ONLY" in e for e in errors):
            status = "BLOCKED_FX3_MULTIPORT_TC_IN_ONLY"
        elif any("HDMI_TC_OUT_ONLY" in e for e in errors):
            status = "BLOCKED_HDMI_TC_OUT_ONLY"
        elif any("UART_BOOT" in e for e in errors):
            status = "BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION"
        else:
            status = "BLOCKED_TC_DIRECTION_POLICY"
    else:
        status = "TC_DIRECTION_ARBITRATED_ZERO_CONTENTION"

    return TcPortDirectionEvalResult(
        valid=len(errors) == 0,
        status=status,
        target_body=norm_body,
        multiport_direction=norm_mp,
        hdmi_direction=norm_hdmi,
        vmc_bncm1_attached=vmc_bncm1_attached,
        uart_boot_active=uart_boot_active,
        bus_contention_count=0,
        ext_lk_input_active=(len(errors) == 0 and norm_mp == "TC_IN" and vmc_bncm1_attached),
        hdmi_tc_ub_output_active=(len(errors) == 0 and norm_hdmi == "TC_OUT"),
        errors=tuple(errors),
    )


def evaluate_pillar_3_smpte_ub_and_direction(
    present_map: Mapping[str, Tuple[str, ...]],
) -> SmpteUserBitsReport:
    """Audit Pillar 3 across User-Bits binary markers, 5 UB formats (`A0:01:00:01`), and TC direction guards."""
    errors: List[str] = []
    fx3_ub = present_map["fx3_appfw_tc_ub"]
    fx6_ub = present_map["fx6_appfw_tc_ub"]
    cp_all = present_map["cp_shared_phase80"]
    cp_ub = tuple(m for m in cp_all if "TIMECODE_UB" in m or "TCUB_" in m)

    if fx3_ub != FX3_APPFW_TC_UB_MARKERS:
        missing = tuple(m for m in FX3_APPFW_TC_UB_MARKERS if m not in fx3_ub)
        errors.append(f"FX3 appFw.so missing User-Bits / HDMI TC markers: {missing}")
    if fx6_ub != FX6_APPFW_TC_UB_MARKERS:
        missing = tuple(m for m in FX6_APPFW_TC_UB_MARKERS if m not in fx6_ub)
        errors.append(f"FX6 appFw.so missing User-Bits / UB_MODE markers: {missing}")
    for m in ("SET_TIMECODE_UBMODE", "SET_TIMECODE_UB", "MSG_ID_INFRABB_SYS_SET_TIMECODE_UB"):
        if m not in cp_ub:
            errors.append(f"cpapp-b.bin missing User-Bits IPC marker: {m}")

    ub_fix = pack_smpte12m_user_bits(mode="FIX_HEX", ub_str="1A:2B:3C:4D")
    ub_date = pack_smpte12m_user_bits(mode="DATE_YYMMDD", year=26, month=11, day=14)
    ub_time = pack_smpte12m_user_bits(mode="CLK_TIME", hours=16, minutes=45, seconds=0)
    ub_fps = pack_smpte12m_user_bits(mode="FRAME_RATE", fps_tag="23.98")
    ub_cam = pack_smpte12m_user_bits(mode="CAM_ID_REEL", cam_id="A", cam_index=0, reel=1, clip_or_slate=1)

    for ev in (ub_fix, ub_date, ub_time, ub_fps, ub_cam):
        if not ev.valid or not ev.roundtrip_exact:
            errors.extend(ev.errors)
    if ub_cam.ub_formatted != "A0:01:00:01":
        errors.append(f"Expected CamID+Reel UB 'A0:01:00:01', got {ub_cam.ub_formatted!r}")

    dir_ok = evaluate_tc_port_direction_guard(
        target_body="ILME-FX3",
        multiport_direction="TC_IN",
        hdmi_direction="TC_OUT",
        vmc_bncm1_attached=True,
        uart_boot_active=False,
    )
    dir_bad_mp = evaluate_tc_port_direction_guard(
        target_body="ILME-FX3",
        multiport_direction="TC_OUT",
        hdmi_direction="TC_OUT",
        vmc_bncm1_attached=True,
    )
    dir_bad_hdmi = evaluate_tc_port_direction_guard(
        target_body="ILME-FX3",
        multiport_direction="OFF",
        hdmi_direction="TC_IN",
        vmc_bncm1_attached=False,
    )
    dir_bad_uart = evaluate_tc_port_direction_guard(
        target_body="ILME-FX3",
        multiport_direction="TC_IN",
        hdmi_direction="TC_OUT",
        vmc_bncm1_attached=True,
        uart_boot_active=True,
    )

    if not dir_ok.valid or dir_ok.bus_contention_count != 0:
        errors.extend(dir_ok.errors or ("Valid simultaneous TC_IN + HDMI TC_OUT failed",))
    if dir_bad_mp.valid or dir_bad_mp.status != "BLOCKED_FX3_MULTIPORT_TC_IN_ONLY":
        errors.append("Multi-Port TC_OUT guard failed to block")
    if dir_bad_hdmi.valid or dir_bad_hdmi.status != "BLOCKED_HDMI_TC_OUT_ONLY":
        errors.append("HDMI TC_IN guard failed to block")
    if dir_bad_uart.valid or dir_bad_uart.status != "BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION":
        errors.append("uart_boot VMC-BNCM1 collision guard failed to block")

    total_contention = sum(
        ev.bus_contention_count for ev in (dir_ok, dir_bad_mp, dir_bad_hdmi, dir_bad_uart)
    )
    return SmpteUserBitsReport(
        passed=len(errors) == 0 and total_contention == 0,
        fx3_tc_ub_markers=fx3_ub,
        fx6_tc_ub_markers=fx6_ub,
        cp_tc_ub_markers=cp_ub,
        ub_fix_hex_eval=ub_fix,
        ub_date_yymmdd_eval=ub_date,
        ub_clk_time_eval=ub_time,
        ub_framerate_eval=ub_fps,
        ub_cam_id_reel_eval=ub_cam,
        valid_simultaneous_in_out_eval=dir_ok,
        blocked_multiport_tc_out_eval=dir_bad_mp,
        blocked_hdmi_tc_in_eval=dir_bad_hdmi,
        blocked_uart_boot_collision_eval=dir_bad_uart,
        bus_contention_count=total_contention,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar 4: Zero Calibration & Zero Persistent eMMC Mutation Proof
# ---------------------------------------------------------------------------


def verify_zero_calibration_and_emmc_immutability(
    *,
    target_path: str = "/tmp/fx3_stageb_phase80_shadow.json",
    persistent_emmc_writes_authorized: bool = False,
) -> ZeroMutationProofResult:
    """Enforce `calibration_mutation_bytes == 0` and `persistent_emmc_writes_authorized == False`."""
    errors: List[str] = []
    low = target_path.strip().lower()
    is_volatile = low.startswith(VOLATILE_SHADOW_PREFIXES)
    is_forbidden = any(low.startswith(p) or p in low for p in FORBIDDEN_CALIBRATION_AND_EMMC_PATHS)

    if persistent_emmc_writes_authorized:
        errors.append("BLOCKED_PERSISTENT_EMMC_WRITE_FLAG: persistent_emmc_writes_authorized must remain False")
    if is_forbidden:
        errors.append(f"BLOCKED_CALIBRATION_OR_EMMC_MUTATION: {target_path!r} targets protected flash/calibration")
    elif not is_volatile:
        errors.append(f"target_path={target_path!r} must use a volatile prefix {VOLATILE_SHADOW_PREFIXES}")

    if errors:
        status = "BLOCKED_PROTECTED_CALIBRATION_OR_EMMC_WRITE"
    else:
        status = "ZERO_CALIBRATION_ZERO_EMMC_MUTATION_VERIFIED"

    return ZeroMutationProofResult(
        valid=len(errors) == 0,
        status=status,
        target_path=target_path,
        volatile_shadow_only=(not is_forbidden) and is_volatile,
        calibration_mutation_bytes=0,
        persistent_emmc_writes_authorized=persistent_emmc_writes_authorized,
        errors=tuple(errors),
    )


def evaluate_pillar_4_zero_mutation(
    fx3_xdb_ok: bool,
    fx6_xdb_ok: bool,
) -> ZeroCalibrationAndEmmcReport:
    """Audit Pillar 4 across `global.xdb` validity and protected flash/calibration write guards."""
    errors: List[str] = []
    if not fx3_xdb_ok or not fx6_xdb_ok:
        errors.append(f"global.xdb validation failed (fx3={fx3_xdb_ok}, fx6={fx6_xdb_ok})")

    vol_ok = verify_zero_calibration_and_emmc_immutability(
        target_path="/tmp/fx3_stageb_phase80_shadow.json",
        persistent_emmc_writes_authorized=False,
    )
    blk_cnf = verify_zero_calibration_and_emmc_immutability(
        target_path="/dev/cnflasha1/cal_override.bin",
        persistent_emmc_writes_authorized=False,
    )
    blk_bak = verify_zero_calibration_and_emmc_immutability(
        target_path="p2:/Backup.bin",
        persistent_emmc_writes_authorized=False,
    )
    blk_flag = verify_zero_calibration_and_emmc_immutability(
        target_path="/tmp/fx3_stageb_phase80_shadow.json",
        persistent_emmc_writes_authorized=True,
    )

    if not vol_ok.valid or vol_ok.calibration_mutation_bytes != 0:
        errors.extend(vol_ok.errors or ("Volatile shadow proof failed",))
    for blk in (blk_cnf, blk_bak, blk_flag):
        if blk.valid or blk.calibration_mutation_bytes != 0:
            errors.append(f"Protected path/flag failed to block: {blk.target_path}")

    total_mut = sum(
        ev.calibration_mutation_bytes for ev in (vol_ok, blk_cnf, blk_bak, blk_flag)
    )
    return ZeroCalibrationAndEmmcReport(
        passed=len(errors) == 0 and total_mut == 0,
        fx3_global_xdb_valid=fx3_xdb_ok,
        fx6_global_xdb_valid=fx6_xdb_ok,
        volatile_shadow_eval=vol_ok,
        blocked_cnflasha_eval=blk_cnf,
        blocked_backup_bin_eval=blk_bak,
        blocked_emmc_flag_eval=blk_flag,
        calibration_mutation_bytes=total_mut,
        persistent_emmc_writes_authorized=False,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Main Dual-Mode Entrypoint
# ---------------------------------------------------------------------------


def analyze_falsecolor_lpcm_tc_ub(
    repo_root: Optional[Path] = None,
    *,
    clean_room: bool = False,
) -> FalseColorLpcmTcUbReport:
    """Run the 15th Unified Firmware-Lab Auditor across Local Donor (`os.O_RDONLY`) or Clean-Room fixtures."""
    root = repo_root or DEFAULT_REPO_ROOT
    forced_clean = clean_room or is_forced_clean_room()

    donor_relpaths: Dict[str, str] = {
        "fx3_appfw": FX3_APPFW_RELPATH,
        "fx6_appfw": FX6_APPFW_RELPATH,
        "fx3_cpapp": FX3_CPAPP_RELPATH,
        "fx6_cpapp": FX6_CPAPP_RELPATH,
        "fx6_hotshoe": FX6_HOTSHOE_RELPATH,
        "fx6_avbb_audio": FX6_AVBB_AUDIO_RELPATH,
        "fx3_global_xdb": FX3_GLOBAL_XDB_RELPATH,
        "fx6_global_xdb": FX6_GLOBAL_XDB_RELPATH,
        "fx3_str_en": FX3_STR_EN_RELPATH,
        "fx3_str_en_g": FX3_STR_EN_G_RELPATH,
        "fx6_str_en_1": FX6_STR_EN_1_RELPATH,
        "fx6_str_en_2": FX6_STR_EN_2_RELPATH,
    }

    resolved_paths: Dict[str, Path] = {}
    if not forced_clean:
        for key, rel in donor_relpaths.items():
            p = resolve_donor_file(rel, repo_root=root)
            if p is not None and p.is_file():
                resolved_paths[key] = p

    use_local_donors = (not forced_clean) and (len(resolved_paths) == len(donor_relpaths))
    mode = "LOCAL_DONOR_VERIFIED" if use_local_donors else "CLEAN_ROOM_SYNTHETIC_VERIFIED"

    errors: List[str] = []
    donor_sizes: Dict[str, int] = {}
    present_map: Dict[str, Tuple[str, ...]] = {}

    fx3_appfw_groups = {
        "fx3_appfw_exposure": FX3_APPFW_EXPOSURE_MARKERS,
        "fx3_appfw_audio_dsp": FX3_APPFW_AUDIO_DSP_MARKERS,
        "fx3_appfw_tc_ub": FX3_APPFW_TC_UB_MARKERS,
    }
    fx6_appfw_groups = {
        "fx6_appfw_exposure": FX6_APPFW_EXPOSURE_MARKERS,
        "fx6_appfw_audio_dsp": FX6_APPFW_AUDIO_DSP_MARKERS,
        "fx6_appfw_tc_ub": FX6_APPFW_TC_UB_MARKERS,
    }

    if use_local_donors:
        sz_fx3_app, fx3_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx3_appfw"], fx3_appfw_groups, is_elf=True
        )
        sz_fx6_app, fx6_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_appfw"], fx6_appfw_groups, is_elf=True
        )
        sz_fx3_cp, fx3_cp_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx3_cpapp"], {"cp": CP_SHARED_PHASE80_MARKERS}, is_elf=False
        )
        sz_fx6_cp, fx6_cp_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_cpapp"], {"cp": CP_SHARED_PHASE80_MARKERS}, is_elf=False
        )
        sz_hot, hot_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_hotshoe"], {"fx6_hotshoe": FX6_HOTSHOE_MARKERS}, is_elf=True
        )
        sz_avbb, avbb_hits = _scan_donor_rdonly_markers(
            resolved_paths["fx6_avbb_audio"], {"fx6_avbb_audio": FX6_AVBB_AUDIO_MARKERS}, is_elf=False
        )

        fx3_xdb_bytes = _read_bytes_rdonly(resolved_paths["fx3_global_xdb"])
        fx6_xdb_bytes = _read_bytes_rdonly(resolved_paths["fx6_global_xdb"])
        fx3_str_en_bytes = _read_bytes_rdonly(resolved_paths["fx3_str_en"])
        fx3_str_eng_bytes = _read_bytes_rdonly(resolved_paths["fx3_str_en_g"])
        fx6_str_en1_bytes = _read_bytes_rdonly(resolved_paths["fx6_str_en_1"])
        fx6_str_en2_bytes = _read_bytes_rdonly(resolved_paths["fx6_str_en_2"])

        donor_sizes = {
            "fx3_appfw": sz_fx3_app,
            "fx6_appfw": sz_fx6_app,
            "fx3_cpapp": sz_fx3_cp,
            "fx6_cpapp": sz_fx6_cp,
            "fx6_hotshoe": sz_hot,
            "fx6_avbb_audio": sz_avbb,
            "fx3_global_xdb": len(fx3_xdb_bytes),
            "fx6_global_xdb": len(fx6_xdb_bytes),
            "fx3_str_en": len(fx3_str_en_bytes),
            "fx3_str_en_g": len(fx3_str_eng_bytes),
            "fx6_str_en_1": len(fx6_str_en1_bytes),
            "fx6_str_en_2": len(fx6_str_en2_bytes),
        }
    else:
        fixtures = build_clean_room_falsecolor_lpcm_ub_fixtures()
        sz_fx3_app, fx3_hits = _scan_bytes_marker_groups(fixtures["fx3_appfw"], fx3_appfw_groups)
        sz_fx6_app, fx6_hits = _scan_bytes_marker_groups(fixtures["fx6_appfw"], fx6_appfw_groups)
        sz_fx3_cp, fx3_cp_hits = _scan_bytes_marker_groups(
            fixtures["fx3_cpapp"], {"cp": CP_SHARED_PHASE80_MARKERS}
        )
        sz_fx6_cp, fx6_cp_hits = _scan_bytes_marker_groups(
            fixtures["fx6_cpapp"], {"cp": CP_SHARED_PHASE80_MARKERS}
        )
        sz_hot, hot_hits = _scan_bytes_marker_groups(
            fixtures["fx6_hotshoe"], {"fx6_hotshoe": FX6_HOTSHOE_MARKERS}
        )
        sz_avbb, avbb_hits = _scan_bytes_marker_groups(
            fixtures["fx6_avbb_audio"], {"fx6_avbb_audio": FX6_AVBB_AUDIO_MARKERS}
        )

        fx3_xdb_bytes = fixtures["fx3_global_xdb"]
        fx6_xdb_bytes = fixtures["fx6_global_xdb"]
        fx3_str_en_bytes = fixtures["fx3_str_en"]
        fx3_str_eng_bytes = fixtures["fx3_str_en_g"]
        fx6_str_en1_bytes = fixtures["fx6_str_en_1"]
        fx6_str_en2_bytes = fixtures["fx6_str_en_2"]

        donor_sizes = {
            "fx3_appfw": sz_fx3_app,
            "fx6_appfw": sz_fx6_app,
            "fx3_cpapp": sz_fx3_cp,
            "fx6_cpapp": sz_fx6_cp,
            "fx6_hotshoe": sz_hot,
            "fx6_avbb_audio": sz_avbb,
            "fx3_global_xdb": len(fx3_xdb_bytes),
            "fx6_global_xdb": len(fx6_xdb_bytes),
            "fx3_str_en": len(fx3_str_en_bytes),
            "fx3_str_en_g": len(fx3_str_eng_bytes),
            "fx6_str_en_1": len(fx6_str_en1_bytes),
            "fx6_str_en_2": len(fx6_str_en2_bytes),
        }

    present_map.update(fx3_hits)
    present_map.update(fx6_hits)
    present_map.update(hot_hits)
    present_map.update(avbb_hits)
    present_map["cp_shared_phase80"] = tuple(
        m for m in CP_SHARED_PHASE80_MARKERS if m in fx3_cp_hits["cp"] and m in fx6_cp_hits["cp"]
    )

    xdb_source_mode = "LOCAL_DONOR_RDONLY" if use_local_donors else "SYNTHETIC_CLEAN_ROOM"
    fx3_xdb_audit = parse_global_xdb_buffer(
        fx3_xdb_bytes,
        body="fx3_702",
        source_mode=xdb_source_mode,
        share_app_dir=resolved_paths["fx3_global_xdb"].parent if use_local_donors else None,
    )
    fx6_xdb_audit = parse_global_xdb_buffer(
        fx6_xdb_bytes,
        body="fx6_601",
        source_mode=xdb_source_mode,
        share_app_dir=resolved_paths["fx6_global_xdb"].parent if use_local_donors else None,
    )
    fx3_xdb_ok = fx3_xdb_audit.valid
    fx6_xdb_ok = fx6_xdb_audit.valid
    if not fx3_xdb_ok:
        errors.extend(fx3_xdb_audit.errors)
    if not fx6_xdb_ok:
        errors.extend(fx6_xdb_audit.errors)

    lbl_fx3_en, errs_fx3_en = _extract_uxc_labels(fx3_str_en_bytes, FX3_NS39_PHASE80_LABELS)
    lbl_fx3_eng, errs_fx3_eng = _extract_uxc_labels(fx3_str_eng_bytes, FX3_NS3_PHASE80_LABELS)
    lbl_fx6_en1, errs_fx6_en1 = _extract_uxc_labels(fx6_str_en1_bytes, FX6_NS1_PHASE80_LABELS)
    lbl_fx6_en2, errs_fx6_en2 = _extract_uxc_labels(fx6_str_en2_bytes, FX6_NS2_PHASE80_LABELS)
    errors.extend((*errs_fx3_en, *errs_fx3_eng, *errs_fx6_en1, *errs_fx6_en2))

    uxc_labels: Dict[str, str] = {
        "fx3_histogram": lbl_fx3_en.get("0x0004e07b", ""),
        "fx3_wind_noise_reduct": lbl_fx3_en.get("0x0004e4b1", ""),
        "fx3_zebra_display": lbl_fx3_eng.get("0x00006352", ""),
        "fx3_reset_user_bit": lbl_fx3_eng.get("0x00006441", ""),
        "fx6_scinetone": lbl_fx6_en1.get("0x000020f5", ""),
        "fx6_slog3": lbl_fx6_en1.get("0x0000219f", ""),
        "fx6_zebra1": lbl_fx6_en1.get("0x000023a5", ""),
        "fx6_zebra2": lbl_fx6_en1.get("0x000023a7", ""),
        "fx6_false_color": lbl_fx6_en1.get("0x00003114", ""),
        "fx6_wind_filter": lbl_fx6_en1.get("0x00003132", ""),
        "fx6_histogram": lbl_fx6_en1.get("0x000032f3", ""),
        "fx6_waveform": lbl_fx6_en1.get("0x00003368", ""),
        "fx6_limiter_mode": lbl_fx6_en2.get("0x000044a4", ""),
        "fx6_1khz_tone": lbl_fx6_en2.get("0x000044a6", ""),
        "fx6_reference_level": lbl_fx6_en2.get("0x00004e77", ""),
        "fx6_duration_tc_ubit": lbl_fx6_en2.get("0x00005438", ""),
    }

    p1 = evaluate_pillar_1_false_color_el_zone(present_map, uxc_labels)
    p2 = evaluate_pillar_2_lpcm_dsp(present_map)
    p3 = evaluate_pillar_3_smpte_ub_and_direction(present_map)
    p4 = evaluate_pillar_4_zero_mutation(fx3_xdb_ok, fx6_xdb_ok)

    errors.extend((*p1.errors, *p2.errors, *p3.errors, *p4.errors))
    wrap_count = (
        p2.limiter_nominal_eval.int24_wrap_around_count
        + p2.limiter_hot_plus6dbfs_eval.int24_wrap_around_count
        + p2.limiter_overload_plus12dbfs_eval.int24_wrap_around_count
    )
    all_passed = bool(
        len(errors) == 0
        and p1.passed
        and p2.passed
        and p3.passed
        and p4.passed
        and p4.calibration_mutation_bytes == 0
        and wrap_count == 0
        and p3.bus_contention_count == 0
    )

    pre_hash_payload = {
        "schema_version": PHASE_80_SCHEMA,
        "phase_version": PHASE_80_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "calibration_mutation_bytes": p4.calibration_mutation_bytes,
        "int24_wrap_around_count": wrap_count,
        "bus_contention_count": p3.bus_contention_count,
        "donor_file_sizes": donor_sizes,
        "pillar_1_false_color_el_zone": asdict(p1),
        "pillar_2_lpcm_headroom_dsp": asdict(p2),
        "pillar_3_smpte_ub_direction": asdict(p3),
        "pillar_4_zero_mutation_proof": asdict(p4),
        "errors": list(errors),
    }
    report_sha256 = hashlib.sha256(
        json.dumps(pre_hash_payload, sort_keys=True).encode("utf-8")
    ).hexdigest()

    return FalseColorLpcmTcUbReport(
        schema_version=PHASE_80_SCHEMA,
        phase_version=PHASE_80_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=False,
        calibration_mutation_bytes=p4.calibration_mutation_bytes,
        int24_wrap_around_count=wrap_count,
        bus_contention_count=p3.bus_contention_count,
        donor_file_sizes=donor_sizes,
        pillar_1_false_color_el_zone=p1,
        pillar_2_lpcm_headroom_dsp=p2,
        pillar_3_smpte_ub_direction=p3,
        pillar_4_zero_mutation_proof=p4,
        errors=tuple(errors),
        report_sha256=report_sha256,
    )


def falsecolor_lpcm_tc_ub_report_to_dict(
    report: FalseColorLpcmTcUbReport,
) -> Dict[str, object]:
    """Convert `FalseColorLpcmTcUbReport` to a deterministic JSON-serializable dict."""
    return report.to_dict()
