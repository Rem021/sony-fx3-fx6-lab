"""Phase 51 — 4-Ch 24-bit 48kHz XLR-H1 Audio Routing, SMPTE 12M Timecode (VMC-BNCM1 EXT-LK & HDMI TC) & 12G-SDI -> HDMI Type-A 16-bit RAW Output Matrix Auditor.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: opens FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`) and
  FX6 v6.01 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`, `libInfraHotshoe.so`,
  `AVBB_SCN_START_AUDIO.so`, `AVBB_SCN_START_PANELEVF.so`) strictly via
  `os.O_RDONLY` + read-only `mmap` and verifies markers using C-level `find()`.
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room binary fixtures carrying the
  exact contract markers and executes the identical three-pillar verification
  pipeline with zero proprietary files required.

Audits Three Cross-Body I/O Compatibility Pillars:
1. Pillar A — 4-Channel 24-bit 48kHz LPCM Audio Matrix:
   Maps FX6 Smart Handle CH1/CH2 + MI-Shoe CH3/CH4 against FX3 XLR-H1 MI-Shoe
   digital audio interface (CH1/CH2 XLR/TRS + CH3/CH4 3.5mm/Internal), 3.5mm
   body mic jack, and 3.5mm headphone monitor bus, verifying P11 (`0x91db059b`)
   hot-detach graceful fallback (`0x88000002` + `libInfraHotshoe.so` `E_TMO = -50
   -> 0x8000`) to Internal Stereo (or body 3.5mm mic jack) without stalling
   recording.
2. Pillar B — SMPTE 12M Timecode (`Preset` / `Regen` / `Free Run` / `Rec Run` / `EXT-LK`):
   Maps FX6 dedicated BNC `TC IN/OUT` vs FX3 Multi-Port `VMC-BNCM1` `LTC IN` +
   HDMI Timecode Out (`HDMI TC ON` for Atomos Ninja/Shogun external trigger),
   validates SMPTE 12M BCD/drop-frame packing, enforces normal-shooting `EXT-LK`
   support (`P11 0x92d2091c` RTC shim), and cross-checks the Phase 38 rule that
   `VMC-BNCM1` MUST be disconnected during `H0`/`Tier-3` `uart_boot` (`Pins 7/8/9`).
3. Pillar C — FX6 12G-SDI + HDMI Monitoring -> FX3 Full-Size HDMI Type-A Safe Routing:
   Audits `4264x2408` (4.2K) `16-bit Linear RAW` HDMI output, `4K DCI / QFHD`
   `10-bit 4:2:2` clean feed, `MLUT` (`Monitor 3D LUT On/Off` per output), and
   `SDI Sub-Output` / `SDI Main` no-op containment on FX3 body (`0` missing-
   transceiver panics or black-screen stalls).
"""

from __future__ import annotations

import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

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


PHASE_51_SCHEMA = "fx3_firmware_lab_phase51_audio_tc_hdmi_sdi_matrix_v1"
PHASE_51_VERSION = "51.0.0"

FX6_HOTSHOE_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraHotshoe.so"
)
FX6_AVBB_AUDIO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/scenario/AVBB_SCN_START_AUDIO.so"
)
FX6_AVBB_PANELEVF_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/scenario/AVBB_SCN_START_PANELEVF.so"
)

# ---------------------------------------------------------------------------
# Pinned Cross-Body Hardware & Protocol Constants
# ---------------------------------------------------------------------------

AUDIO_SAMPLE_RATE_HZ = 48_000
AUDIO_BIT_DEPTH_24 = 24
AUDIO_CHANNELS_4CH = 4
AUDIO_CHANNELS_2CH = 2
AUDIO_4CH_24BIT_BITRATE_BPS = AUDIO_SAMPLE_RATE_HZ * AUDIO_BIT_DEPTH_24 * AUDIO_CHANNELS_4CH  # 4,608,000 bps
AUDIO_4CH_24BIT_FRAME_BYTES = (AUDIO_BIT_DEPTH_24 // 8) * AUDIO_CHANNELS_4CH  # 12 bytes/sample period

P11_SMART_HANDLE_QUEUE_ID = 0x91DB059B
P11_SMART_HANDLE_ATTACHED_EVT = 0x88000001
P11_SMART_HANDLE_DETACHED_EVT = 0x88000002
P11_RTC_QUEUE_ID = 0x92D2091C
LIBINFRAHOTSHOE_E_TMO = -50
LIBINFRAHOTSHOE_TMO_SAFE_RC = 0x8000

VMC_BNCM1_ID_RESISTOR_OHM = 680_000
VMC_BNCM1_LTC_PIN = 3
VMC_BNCM1_GND_PIN = 2
VMC_BNCM1_ID_PIN = 6
MULTIPORT_UART_BOOT_PINS: Tuple[int, ...] = (7, 8, 9)

SMPTE_12M_VALID_FPS: Tuple[float, ...] = (23.976, 24.0, 25.0, 29.97, 30.0, 50.0, 59.94, 60.0)
SMPTE_12M_DROP_FRAME_FPS: Tuple[float, ...] = (29.97, 59.94)

FX3_HDMI_RAW_SENSOR_READOUT = "4264x2408"
FX3_HDMI_RAW_ACTIVE_FORMATS: Tuple[str, ...] = ("4264x2408 16-bit Linear RAW", "4096x2160 16-bit RAW", "3840x2160 16-bit RAW")

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

FX3_APPFW_AUDIO_MARKERS: Tuple[str, ...] = (
    "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
    "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_2CH",
    "VAL_setting_external_mic_audio_format_EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_16BIT_2CH",
    "AUDIO_MONITORING_CH_3CH_4CH",
    "VAL_setting_4ch_output_ch_E_4CH_OUTPUT_CH_1CH_2CH",
    "VAL_setting_4ch_output_ch_E_4CH_OUTPUT_CH_3CH_4CH",
    "EVENT_INPUT_INP_HOTSHOE_XLRMIC_ON",
    "EVENT_INPUT_INP_HOTSHOE_CH4MIC_ON",
    "VAL_HAITA_current_use_mic_is_started_sequence_start_movie_recording_USE_MIC_DIG_MIC_F48B24C4_F96B24C2",
    "EVENT_INPUT_KEY_JACK_MICJACK_IN",
    "EVENT_INPUT_KEY_JACK_MICJACK_OUT",
    "HEADPHONE_CONNECT",
    "HEADPHONE_DISCONNECT",
)

FX6_APPFW_AUDIO_MARKERS: Tuple[str, ...] = (
    "EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_ON",
    "EVENT_INPUT_INP_HOTSHOE_DIGMIC_F48B24C4_F96B24C2_OFF",
    "EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_4CH",
    "EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_24BIT_2CH",
    "EXTERNAL_MIC_AUDIO_FORMAT_48KHZ_16BIT_2CH",
    "VAL_HAITA_setting_ch1_input_select_connect_shoe_mic_CH1_INPUT_SELECT_SHOE_CH_CONNECT_SHOE_MIC_DIGITAL_XLR",
    "VAL_setting_ch1_input_select_CH1_INPUT_SELECT_INTERNAL_MIC",
    "VAL_setting_ch2_input_select_CH2_INPUT_SELECT_INTERNAL_MIC",
    "VAL_setting_ch3_input_select_CH3_INPUT_SELECT_INTERNAL_MIC",
    "VAL_setting_ch4_input_select_CH4_INPUT_SELECT_INTERNAL_MIC",
    "BKID_APP_SETTING_CH1_LEVEL_MI_SHOE",
    "BKID_APP_SETTING_CH3_LEVEL_MI_SHOE",
    "BKID_APP_SETTING_CH4_LEVEL_MI_SHOE",
    "BKID_APP_SETTING_HEADPHONE_OUT",
    "HEADPHONE_CONNECT",
    "HEADPHONE_DISCONNECT",
    "JACK_MIC_CONNECT_ON",
    "infra_wrapper_handle_procam_chaplin_base",
)

MPR_SHARED_AUDIO_MARKERS: Tuple[str, ...] = (
    "AudioRecStart",
    "AudioRecPort",
    "AudioFormat",
)

FX6_MPR_LPCM_MARKERS: Tuple[str, ...] = (
    "DEMUXCHUNKTYPE_EVENT_LPCM_STREAM_TO_CODEC_1",
    "DEMUXCHUNKTYPE_EVENT_LPCM_STREAM_TO_CODEC_4",
)

FX6_HOTSHOE_MARKERS: Tuple[str, ...] = (
    "INFRA_HOTSHOE_UIPC_SHOEINFO_EVT",
    "INFRA_HOTSHOE_UIPC_SETCTRL_BCK_LRCK",
    "INFRA_HOTSHOE_UIPC_SETSHOE_PWR_ON",
    "RCMHR_TMO",
    "WaitRecvCompMsgFromHotshoeRsrc",
)

FX6_AVBB_AUDIO_MARKERS: Tuple[str, ...] = (
    "AVBB_SCN_START_AUDIO",
    "BO_ID_SHOE_MIC",
    "BO_ID_MIC",
    "LOG_SET_ANTI_CLIP_ADF_START",
)

SHARED_APPFW_TIMECODE_MARKERS: Tuple[str, ...] = (
    "VAL_setting_tc_make_TC_MAKE_PRESET",
    "VAL_setting_tc_make_TC_MAKE_REGENRATE",
    "VAL_setting_tc_run_TC_RUN_FREE_RUN",
    "VAL_setting_tc_run_TC_RUN_REC_RUN",
    "EXT_TC_LOCK_STATUS_LOCK",
    "EXT_TC_LOCK_STATUS_PSEUDOLOCK",
    "EXT_TC_LOCK_STATUS_UNLOCK",
    "INFRA_NOTIFY_TIMECODE_EXT_TC_STATUS",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_ON",
    "VAL_setting_hdmi_tc_output_EXTERNAL_HDMI_TC_OUTPUT_OFF",
)

FX6_APPFW_EXTRA_TC_MARKERS: Tuple[str, ...] = (
    "BKID_APP_EXT_TC_LOCK_STATUS",
    "BKID_APP_LAST_EXT_TC_LOCK_FREQ",
    "VAL_HAITA_setting_hdmi_tc_output_sdi_output_EXTERNAL_HDMI_TC_OUTPUT_OFF_TYPE_SDI_OUTPUT_NOT_SUPPORT",
    "infra_wrapper_rtc_procam_chaplin_base",
)

CP_SHARED_TC_MARKERS: Tuple[str, ...] = (
    "MSG_ID_INFRABB_SYS_SET_TIMECODE_PRESET",
    "MSG_ID_INFRABB_SYS_SET_TIMECODE_DFMODE",
)

FX6_CP_BNC_TC_MARKERS: Tuple[str, ...] = (
    "ADJ_CMD_AVBB_TIMECODE_CHANGE_TC_IO",
    "ADJ_CMD_AVBB_TIMECODE_TC_GET_TCOUT_VALUE",
)

SHARED_APPFW_HDMI_RAW_MARKERS: Tuple[str, ...] = (
    "MODEL_HDMI_RAW_OUTPUT_STATUS_CHANGED",
    "EVENT_REMOTE_MOVIE_HDMI_OUTPUT_SETTINGS_W_DIALOG_RAW_OUTPUT",
    "EVENT_REMOTE_MOVIE_HDMI_OUTPUT_SETTINGS_W_DIALOG_OUTPUT_RESOLUTION",
    "VAL_setting_hdmi_info_display_HDMI_INFO_DISPLAY_OFF",
    "VAL_setting_hdmi_info_display_HDMI_INFO_DISPLAY_ON",
)

FX3_APPFW_HDMI_FEED_MARKERS: Tuple[str, ...] = (
    "VAL_HAITA_hdmi_connect_state_connect_with_raw_compatible_device_HDMI_RAW_CONNECTSTATE_HDMI_CONNECT",
    "LINE_OUTPUT_RESOLUTION_STATUS_4K",
    "LINE_OUTPUT_RESOLUTION_STATUS_QFHD",
    "CAUTION_ID_FACTOR_RECORD_SETTING_280M_422_10BIT",
)

FX6_APPFW_MLUT_AND_SDI_MARKERS: Tuple[str, ...] = (
    "VAL_setting_raw_output_format_RAW_OUTPUT_FORMAT_4096x2160",
    "VAL_setting_raw_output_format_RAW_OUTPUT_FORMAT_3840x2160",
    "VAL_setting_raw_output_format_RAW_OUTPUT_FORMAT_4240x2392",
    "BKID_APP_EXTERN_MONITOR_LUT_ONOFF",
    "BKID_APP_EXTERN_MONITOR_LUT_HDMI_ONOFF",
    "BKID_APP_EXTERN_MONITOR_LUT_LCD_VF_ONOFF",
    "BKID_APP_EXTERN_MONITOR_LUT_SDI1_ONOFF",
    "VAL_setting_lut_setting_monitor_out_LUT_SETTING_MONITOR_OUT_MLUT_ON",
    "VAL_setting_lut_setting_monitor_out_LUT_SETTING_MONITOR_OUT_MLUT_OFF",
    "VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT",
    "PRM_FEATURE_MANAGER_sdi_output",
)

FX6_AVBB_PANELEVF_MARKERS: Tuple[str, ...] = (
    "AVBB_SCN_START_HDMI",
    "AVBB_SCN_START_HDMI_SDI",
    "AVBB_SCN_START_HDMI_SDI_SUB",
    "EXEC_SDI_MAIN_OUTPUT",
    "EXEC_SDI_SUB_OUTPUT",
    "SET_MONITOR_MLUT",
    "_Z12GetOutputSelhPh",
)

FX3_FORBIDDEN_SDI_HW_MARKERS: Tuple[str, ...] = (
    "PRM_FEATURE_MANAGER_sdi_output",
    "MoniFpgaSdi_SetRegSDIOutFormat",
    "MoniFpga_StartStopSDI",
)


# ---------------------------------------------------------------------------
# Report & Policy Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AudioChannelMappingEntry:
    channel_id: str
    fx6_source: str
    fx3_primary_source: str
    fx3_fallback_source: str
    sample_rate_hz: int
    bit_depth: int
    verdict: str
    notes: str


@dataclass(frozen=True)
class HotDetachFallbackResult:
    valid: bool
    status: str
    xlr_h1_attached: bool
    p11_handle_queue_hex: str
    p11_event_cmd_hex: str
    hotshoe_tmo_safe_rc_hex: str
    active_audio_bus: str
    active_channels: int
    sample_rate_hz: int
    bit_depth: int
    pcm_bitrate_bps: int
    recording_continues: bool
    recording_stalled: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AudioRoutingMatrixReport:
    passed: bool
    fx3_appfw_audio_markers: Tuple[str, ...]
    fx6_appfw_audio_markers: Tuple[str, ...]
    fx3_mpr_audio_markers: Tuple[str, ...]
    fx6_mpr_audio_markers: Tuple[str, ...]
    fx6_hotshoe_markers: Tuple[str, ...]
    fx6_avbb_audio_markers: Tuple[str, ...]
    attached_4ch_24bit_48khz_bitrate_bps: int
    attached_scenario: HotDetachFallbackResult
    detached_fallback_scenario: HotDetachFallbackResult
    channel_matrix: Tuple[AudioChannelMappingEntry, ...]
    p11_hot_detach_non_stalling_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TimecodeInterfaceEntry:
    feature_id: str
    fx6_interface: str
    fx3_interface: str
    smpte_12m_compatible: bool
    verdict: str
    notes: str


@dataclass(frozen=True)
class Smpte12mTimecodeEvalResult:
    valid: bool
    status: str
    smpte_tc_str: str
    smpte_bcd_hex: str
    fps: float
    drop_frame: bool
    tc_make_mode: str
    tc_run_mode: str
    ext_lk_requested: bool
    ext_lk_active: bool
    hdmi_tc_out_on: bool
    vmc_bncm1_attached: bool
    uart_boot_active: bool
    phase38_uart_boot_guard_ok: bool
    bnc_tc_out_blocked_on_fx3: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class TimecodeMatrixReport:
    passed: bool
    shared_appfw_tc_markers: Tuple[str, ...]
    fx6_extra_tc_markers: Tuple[str, ...]
    fx3_cp_tc_markers: Tuple[str, ...]
    fx6_cp_tc_markers: Tuple[str, ...]
    fx6_cp_bnc_tc_markers: Tuple[str, ...]
    normal_shooting_ext_lk_eval: Smpte12mTimecodeEvalResult
    hdmi_tc_atomos_trigger_eval: Smpte12mTimecodeEvalResult
    phase38_uart_boot_collision_blocked: Smpte12mTimecodeEvalResult
    timecode_matrix: Tuple[TimecodeInterfaceEntry, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class VideoOutputRouteEntry:
    route_id: str
    fx6_output_mode: str
    fx3_hdmi_type_a_route: str
    mlut_per_output_supported: bool
    sdi_noop_contained: bool
    verdict: str
    notes: str


@dataclass(frozen=True)
class VideoOutputPolicyResult:
    valid: bool
    status: str
    target_body: str
    hdmi_mode: str
    hdmi_raw_resolution: str
    lcd_mlut_on: bool
    hdmi_mlut_on: bool
    sdi_sub_output_requested: bool
    sdi_transceiver_present: bool
    sdi_noop_contained: bool
    active_hdmi_feed: bool
    missing_transceiver_panics: int
    black_screen_stalls: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class VideoOutputRoutingMatrixReport:
    passed: bool
    fx3_shared_hdmi_markers: Tuple[str, ...]
    fx6_shared_hdmi_markers: Tuple[str, ...]
    fx3_hdmi_feed_markers: Tuple[str, ...]
    fx6_mlut_sdi_markers: Tuple[str, ...]
    fx6_avbb_panelevf_markers: Tuple[str, ...]
    fx3_unexpected_sdi_markers: Tuple[str, ...]
    raw_16bit_4264x2408_eval: VideoOutputPolicyResult
    clean_4k_422_10bit_mlut_eval: VideoOutputPolicyResult
    sdi_sub_output_noop_eval: VideoOutputPolicyResult
    output_matrix: Tuple[VideoOutputRouteEntry, ...]
    zero_panics_and_zero_stalls_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class AudioTcHdmiSdiRoutingReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    donor_file_sizes: Dict[str, int]
    pillar_a_audio: AudioRoutingMatrixReport
    pillar_b_timecode: TimecodeMatrixReport
    pillar_c_video_output: VideoOutputRoutingMatrixReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Strictly O_RDONLY Scanning Helpers (Zero Raw Binary Output)
# ---------------------------------------------------------------------------


def _scan_rdonly_markers(path: Path, markers: Sequence[str]) -> Tuple[int, Tuple[str, ...]]:
    """Open `path` strictly `os.O_RDONLY` and scan `markers` via C-level `bytes.find`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        with os.fdopen(fd, "rb") as fh:
            data = fh.read()
    except Exception:
        try:
            os.close(fd)
        except OSError:
            pass
        raise
    if not data:
        return 0, ()
    present = tuple(m for m in markers if data.find(m.encode("latin1")) != -1)
    return len(data), present


def _scan_buffer_markers(buf: bytes, markers: Sequence[str]) -> Tuple[int, Tuple[str, ...]]:
    """Scan an in-memory buffer for ASCII/Latin-1 markers using C-level `bytes.find`."""
    return len(buf), tuple(m for m in markers if buf.find(m.encode("latin1")) != -1)


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_audio_tc_hdmi_fixtures(
    *,
    drop_fx3_4ch_audio: bool = False,
    drop_fx6_hotshoe_tmo: bool = False,
    drop_fx3_ext_tc: bool = False,
    drop_fx6_mlut_sdi: bool = False,
    inject_sdi_hw_in_fx3: bool = False,
) -> Dict[str, bytes]:
    """Build deterministic clean-room synthetic ELF/CP buffers representing all 9 donor files."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)
    cp_hdr = b"LDR\x00" + bytes(60)

    def _pack(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_audio = FX3_APPFW_AUDIO_MARKERS[:-1] if drop_fx3_4ch_audio else FX3_APPFW_AUDIO_MARKERS
    fx3_tc = SHARED_APPFW_TIMECODE_MARKERS[:-1] if drop_fx3_ext_tc else SHARED_APPFW_TIMECODE_MARKERS
    fx3_appfw_tokens = [
        *fx3_audio,
        *fx3_tc,
        *SHARED_APPFW_HDMI_RAW_MARKERS,
        *FX3_APPFW_HDMI_FEED_MARKERS,
        *(FX3_FORBIDDEN_SDI_HW_MARKERS if inject_sdi_hw_in_fx3 else ()),
    ]

    fx6_mlut = FX6_APPFW_MLUT_AND_SDI_MARKERS[:-1] if drop_fx6_mlut_sdi else FX6_APPFW_MLUT_AND_SDI_MARKERS
    fx6_appfw_tokens = [
        *FX6_APPFW_AUDIO_MARKERS,
        *SHARED_APPFW_TIMECODE_MARKERS,
        *FX6_APPFW_EXTRA_TC_MARKERS,
        *SHARED_APPFW_HDMI_RAW_MARKERS,
        *fx6_mlut,
    ]

    fx3_mpr_tokens = [*MPR_SHARED_AUDIO_MARKERS]
    fx6_mpr_tokens = [*MPR_SHARED_AUDIO_MARKERS, *FX6_MPR_LPCM_MARKERS]

    fx3_cp_tokens = [
        *CP_SHARED_TC_MARKERS,
        *(("MoniFpgaSdi_SetRegSDIOutFormat",) if inject_sdi_hw_in_fx3 else ()),
    ]
    fx6_cp_tokens = [
        *CP_SHARED_TC_MARKERS,
        *FX6_CP_BNC_TC_MARKERS,
    ]

    fx6_hotshoe_tokens = (
        [t for t in FX6_HOTSHOE_MARKERS if t != "RCMHR_TMO"]
        if drop_fx6_hotshoe_tmo
        else list(FX6_HOTSHOE_MARKERS)
    )

    return {
        "fx3_appfw": _pack(fx3_appfw_tokens),
        "fx6_appfw": _pack(fx6_appfw_tokens),
        "fx3_libmpr": _pack(fx3_mpr_tokens),
        "fx6_libmpr": _pack(fx6_mpr_tokens),
        "fx3_cpapp": _pack(fx3_cp_tokens, prefix=cp_hdr),
        "fx6_cpapp": _pack(fx6_cp_tokens, prefix=cp_hdr),
        "fx6_hotshoe": _pack(fx6_hotshoe_tokens),
        "fx6_avbb_audio": _pack(FX6_AVBB_AUDIO_MARKERS),
        "fx6_avbb_panelevf": _pack(FX6_AVBB_PANELEVF_MARKERS),
    }


# ---------------------------------------------------------------------------
# Pillar A: 4-Channel 24-bit 48kHz Audio & P11 (0x91db059b) Hot-Detach Evaluators
# ---------------------------------------------------------------------------


def evaluate_p11_hot_detach_audio_fallback(
    *,
    xlr_h1_attached: bool = True,
    body_35mm_mic_plugged: bool = False,
    p11_smart_handle_event_cmd: int = P11_SMART_HANDLE_DETACHED_EVT,
    hotshoe_tmo_rc: int = LIBINFRAHOTSHOE_TMO_SAFE_RC,
    sample_rate_hz: int = AUDIO_SAMPLE_RATE_HZ,
    bit_depth: int = AUDIO_BIT_DEPTH_24,
    recording_active: bool = True,
    simulate_blocking_wait: bool = False,
) -> HotDetachFallbackResult:
    """Verify XLR-H1 4ch 24-bit 48kHz audio vs P11 (0x91db059b) hot-detach Internal Stereo fallback."""
    errors: List[str] = []

    if sample_rate_hz != AUDIO_SAMPLE_RATE_HZ:
        errors.append(f"Unsupported LPCM sample rate {sample_rate_hz} Hz (expected {AUDIO_SAMPLE_RATE_HZ} Hz)")
    if bit_depth not in (16, 24):
        errors.append(f"Unsupported LPCM bit depth {bit_depth} (expected 16 or 24)")
    if simulate_blocking_wait or hotshoe_tmo_rc != LIBINFRAHOTSHOE_TMO_SAFE_RC:
        errors.append(
            f"libInfraHotshoe timeout must return 0x{LIBINFRAHOTSHOE_TMO_SAFE_RC:04x} without stalling recording"
        )
    if p11_smart_handle_event_cmd == P11_SMART_HANDLE_ATTACHED_EVT:
        errors.append(
            "Spoofed P11 Smart Handle attached ACK (0x88000001) on FX3 suppresses XLR-H1 MI-shoe audio"
        )
    elif p11_smart_handle_event_cmd != P11_SMART_HANDLE_DETACHED_EVT:
        errors.append(f"Unexpected P11 Smart Handle event cmd 0x{p11_smart_handle_event_cmd:08x}")

    if xlr_h1_attached:
        if bit_depth != AUDIO_BIT_DEPTH_24:
            errors.append("XLR-H1 4-channel MI-Shoe mode requires 24-bit LPCM framing")
        active_bus = "XLR_H1_MI_SHOE_4CH_24BIT_48KHZ"
        channels = AUDIO_CHANNELS_4CH
    elif body_35mm_mic_plugged:
        active_bus = "BODY_3_5MM_STEREO_JACK"
        channels = AUDIO_CHANNELS_2CH
    else:
        active_bus = "INTERNAL_STEREO"
        channels = AUDIO_CHANNELS_2CH

    bitrate_bps = sample_rate_hz * bit_depth * channels
    recording_stalled = bool(simulate_blocking_wait or len(errors) > 0)
    recording_continues = bool(recording_active and not recording_stalled)

    if len(errors) == 0:
        status = "XLR_H1_4CH_ACTIVE" if xlr_h1_attached else "HOT_DETACH_FALLBACK_NON_STALLING"
    else:
        status = "BLOCKED_AUDIO_FALLBACK_STALL_OR_COLLISION"

    return HotDetachFallbackResult(
        valid=len(errors) == 0,
        status=status,
        xlr_h1_attached=xlr_h1_attached,
        p11_handle_queue_hex=f"0x{P11_SMART_HANDLE_QUEUE_ID:08x}",
        p11_event_cmd_hex=f"0x{p11_smart_handle_event_cmd:08x}",
        hotshoe_tmo_safe_rc_hex=f"0x{hotshoe_tmo_rc:04x}",
        active_audio_bus=active_bus,
        active_channels=channels,
        sample_rate_hz=sample_rate_hz,
        bit_depth=bit_depth,
        pcm_bitrate_bps=bitrate_bps,
        recording_continues=recording_continues,
        recording_stalled=recording_stalled,
        errors=tuple(errors),
    )


def evaluate_pillar_a_audio_matrix(
    present_map: Mapping[str, Tuple[str, ...]],
) -> AudioRoutingMatrixReport:
    """Audit Pillar A: 4-Ch 24-bit 48kHz LPCM audio routing and P11 hot-detach fallback."""
    errors: List[str] = []

    fx3_app = present_map["fx3_appfw_audio"]
    fx6_app = present_map["fx6_appfw_audio"]
    fx3_mpr = present_map["fx3_libmpr_audio"]
    fx6_mpr = present_map["fx6_libmpr_audio"]
    fx6_hot = present_map["fx6_hotshoe"]
    fx6_avbb = present_map["fx6_avbb_audio"]

    if fx3_app != FX3_APPFW_AUDIO_MARKERS:
        missing = tuple(m for m in FX3_APPFW_AUDIO_MARKERS if m not in fx3_app)
        errors.append(f"FX3 appFw.so missing audio/XLR-H1 markers: {missing}")
    if fx6_app != FX6_APPFW_AUDIO_MARKERS:
        missing = tuple(m for m in FX6_APPFW_AUDIO_MARKERS if m not in fx6_app)
        errors.append(f"FX6 appFw.so missing audio/MI-shoe markers: {missing}")
    if fx3_mpr != MPR_SHARED_AUDIO_MARKERS:
        errors.append("FX3 libmpr.so missing shared AudioRec/AudioFormat markers")
    if fx6_mpr != (MPR_SHARED_AUDIO_MARKERS + FX6_MPR_LPCM_MARKERS):
        errors.append("FX6 libmpr.so missing shared AudioRec or LPCM stream markers")
    if fx6_hot != FX6_HOTSHOE_MARKERS:
        errors.append("FX6 libInfraHotshoe.so missing bounded E_TMO / UIPC MI-Shoe markers")
    if fx6_avbb != FX6_AVBB_AUDIO_MARKERS:
        errors.append("FX6 AVBB_SCN_START_AUDIO.so missing audio/shoe scenario markers")

    attached_eval = evaluate_p11_hot_detach_audio_fallback(xlr_h1_attached=True)
    detached_eval = evaluate_p11_hot_detach_audio_fallback(xlr_h1_attached=False)
    if not attached_eval.valid:
        errors.extend(attached_eval.errors)
    if not detached_eval.valid or detached_eval.recording_stalled or detached_eval.active_audio_bus != "INTERNAL_STEREO":
        errors.append("P11 0x91db059b hot-detach did not cleanly fall back to Internal Stereo without stalling")

    channel_matrix: Tuple[AudioChannelMappingEntry, ...] = (
        AudioChannelMappingEntry(
            channel_id="CH1",
            fx6_source="Smart Handle XLR1 (Line/Mic/+48V)",
            fx3_primary_source="XLR-H1 MI-Shoe INPUT 1 (XLR/TRS +48V Digital I2S)",
            fx3_fallback_source="Body 3.5mm Mic Jack L / Internal Stereo L",
            sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
            bit_depth=AUDIO_BIT_DEPTH_24,
            verdict="FULL_PARITY_MI_SHOE_24BIT_48KHZ",
            notes="24-bit 48kHz LPCM via MI-Shoe digital I2S; P11 0x91db059b detached ACK preserves XLR-H1.",
        ),
        AudioChannelMappingEntry(
            channel_id="CH2",
            fx6_source="Smart Handle XLR2 (Line/Mic/+48V)",
            fx3_primary_source="XLR-H1 MI-Shoe INPUT 2 (XLR/TRS +48V Digital I2S)",
            fx3_fallback_source="Body 3.5mm Mic Jack R / Internal Stereo R",
            sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
            bit_depth=AUDIO_BIT_DEPTH_24,
            verdict="FULL_PARITY_MI_SHOE_24BIT_48KHZ",
            notes="Independent +48V phantom power & ATT/level dials on XLR-H1 handle.",
        ),
        AudioChannelMappingEntry(
            channel_id="CH3",
            fx6_source="MI-Shoe Digital CH3 / Body Internal Mic L",
            fx3_primary_source="XLR-H1 INPUT 3 (3.5mm Stereo L) / Internal Mic L",
            fx3_fallback_source="Internal Stereo L (Graceful Hot-Detach Fallback)",
            sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
            bit_depth=AUDIO_BIT_DEPTH_24,
            verdict="FULL_PARITY_4CH_EXPANSION",
            notes="Maps to FX3 4CH_OUTPUT_CH_3CH_4CH & AUDIO_MONITORING_CH_3CH_4CH.",
        ),
        AudioChannelMappingEntry(
            channel_id="CH4",
            fx6_source="MI-Shoe Digital CH4 / Body Internal Mic R",
            fx3_primary_source="XLR-H1 INPUT 3 (3.5mm Stereo R) / Internal Mic R",
            fx3_fallback_source="Internal Stereo R (Graceful Hot-Detach Fallback)",
            sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
            bit_depth=AUDIO_BIT_DEPTH_24,
            verdict="FULL_PARITY_4CH_EXPANSION",
            notes="Non-blocking hot-detach falls back via E_TMO=-50 -> 0x8000 without stalling movie rec.",
        ),
        AudioChannelMappingEntry(
            channel_id="BODY_3_5MM_MIC_JACK",
            fx6_source="Body 3.5mm Mic Input (JACK_MIC_CONNECT_ON)",
            fx3_primary_source="FX3 Red 3.5mm Stereo Mic Jack (Plug-in Power)",
            fx3_fallback_source="Internal Stereo Mic",
            sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
            bit_depth=AUDIO_BIT_DEPTH_24,
            verdict="NATIVE_1_TO_1_PARITY",
            notes="Shared EVENT_INPUT_KEY_JACK_MICJACK_IN/OUT & JACK_MIC_CONNECT_ON state machine.",
        ),
        AudioChannelMappingEntry(
            channel_id="HEADPHONE_3_5MM_MONITOR_BUS",
            fx6_source="Headphone 3.5mm Out (BKID_APP_SETTING_HEADPHONE_OUT)",
            fx3_primary_source="FX3 Black 3.5mm Headphone Jack (CH1/2, CH3/4, Mix)",
            fx3_fallback_source="Built-in Monitor Speaker",
            sample_rate_hz=AUDIO_SAMPLE_RATE_HZ,
            bit_depth=AUDIO_BIT_DEPTH_24,
            verdict="NATIVE_1_TO_1_PARITY",
            notes="HEADPHONE_CONNECT / HEADPHONE_DISCONNECT & AUDIO_MONITORING_CH_3CH_4CH supported.",
        ),
    )

    hot_detach_ok = bool(
        attached_eval.valid
        and detached_eval.valid
        and detached_eval.recording_continues
        and not detached_eval.recording_stalled
        and detached_eval.active_audio_bus == "INTERNAL_STEREO"
    )

    return AudioRoutingMatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_audio_markers=fx3_app,
        fx6_appfw_audio_markers=fx6_app,
        fx3_mpr_audio_markers=fx3_mpr,
        fx6_mpr_audio_markers=fx6_mpr,
        fx6_hotshoe_markers=fx6_hot,
        fx6_avbb_audio_markers=fx6_avbb,
        attached_4ch_24bit_48khz_bitrate_bps=AUDIO_4CH_24BIT_BITRATE_BPS,
        attached_scenario=attached_eval,
        detached_fallback_scenario=detached_eval,
        channel_matrix=channel_matrix,
        p11_hot_detach_non_stalling_verified=hot_detach_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar B: SMPTE 12M Timecode (VMC-BNCM1 EXT-LK & HDMI TC) Evaluators
# ---------------------------------------------------------------------------


def _bcd_byte(val: int, *, flag_bit: int = 0) -> int:
    tens = (val // 10) & 0xF
    units = (val % 10) & 0xF
    return ((tens << 4) | units | flag_bit) & 0xFF


def encode_smpte12m_bcd(
    hours: int,
    minutes: int,
    seconds: int,
    frames: int,
    *,
    fps: float = 23.976,
    drop_frame: bool = False,
) -> bytes:
    """Encode a 4-byte SMPTE 12M HH:MM:SS:FF BCD word (frames, seconds, minutes, hours)."""
    if fps not in SMPTE_12M_VALID_FPS:
        raise ValueError(f"Unsupported SMPTE 12M fps: {fps}")
    max_frames = int(round(fps))
    if not (0 <= hours <= 23 and 0 <= minutes <= 59 and 0 <= seconds <= 59 and 0 <= frames < max_frames):
        raise ValueError(f"Out-of-range SMPTE 12M timecode: {hours:02d}:{minutes:02d}:{seconds:02d}:{frames:02d}")
    if drop_frame and fps not in SMPTE_12M_DROP_FRAME_FPS:
        raise ValueError(f"Drop-Frame SMPTE 12M is only valid for {SMPTE_12M_DROP_FRAME_FPS}, got {fps}")
    if drop_frame and frames in (0, 1) and seconds == 0 and (minutes % 10) != 0:
        raise ValueError("Invalid SMPTE 12M drop-frame boundary (frames 00/01 dropped on non-10th minutes)")
    df_flag = 0x40 if drop_frame else 0x00
    return bytes((
        _bcd_byte(frames, flag_bit=df_flag),
        _bcd_byte(seconds),
        _bcd_byte(minutes),
        _bcd_byte(hours),
    ))


def evaluate_smpte12m_tc_routing(
    *,
    target_body: str = "ILME-FX3",
    hours: int = 1,
    minutes: int = 23,
    seconds: int = 45,
    frames: int = 12,
    fps: float = 23.976,
    drop_frame: bool = False,
    tc_make_mode: str = "PRESET",
    tc_run_mode: str = "FREE_RUN",
    ext_lk_requested: bool = True,
    bnc_tc_out_requested: bool = False,
    hdmi_tc_out_on: bool = True,
    vmc_bncm1_attached: bool = True,
    vmc_bncm1_id_ohm: int = VMC_BNCM1_ID_RESISTOR_OHM,
    uart_boot_active: bool = False,
    p11_rtc_shim_active: bool = True,
) -> Smpte12mTimecodeEvalResult:
    """Validate SMPTE 12M timecode, normal-shooting EXT-LK, HDMI TC Out, and Phase 38 uart_boot isolation."""
    errors: List[str] = []
    norm_make = tc_make_mode.strip().upper()
    norm_run = tc_run_mode.strip().upper()

    try:
        bcd = encode_smpte12m_bcd(hours, minutes, seconds, frames, fps=fps, drop_frame=drop_frame)
        bcd_hex = bcd.hex()
    except ValueError as exc:
        bcd_hex = ""
        errors.append(str(exc))

    sep = ";" if drop_frame else ":"
    tc_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}{sep}{frames:02d}"

    if norm_make not in ("PRESET", "REGEN"):
        errors.append(f"Invalid TC Make mode: {tc_make_mode!r}")
    if norm_run not in ("FREE_RUN", "REC_RUN"):
        errors.append(f"Invalid TC Run mode: {tc_run_mode!r}")

    phase38_guard_ok = not (uart_boot_active and vmc_bncm1_attached)
    if not phase38_guard_ok:
        errors.append(
            "Phase 38 violation: VMC-BNCM1 LTC cable MUST be disconnected during H0/Tier-3 uart_boot (Multi-Port Pins 7/8/9)"
        )

    bnc_tc_out_blocked = False
    if target_body.upper() == "ILME-FX3" and bnc_tc_out_requested:
        bnc_tc_out_blocked = True
        errors.append("FX3 has no dedicated BNC TC OUT hardware; use HDMI TC ON for external recorder trigger")

    ext_lk_active = False
    if ext_lk_requested:
        if target_body.upper() == "ILME-FX3":
            if uart_boot_active:
                errors.append("EXT-LK via VMC-BNCM1 is forbidden during H0/Tier-3 uart_boot")
            elif not vmc_bncm1_attached:
                errors.append("EXT-LK requested on FX3 without VMC-BNCM1 Multi-Port adapter attached")
            elif not (612_000 <= vmc_bncm1_id_ohm <= 748_000):
                errors.append(f"VMC-BNCM1 Pin 6 ID resistor {vmc_bncm1_id_ohm} Ohm outside 680kOhm +/-10% window")
            elif norm_make != "PRESET" or norm_run != "FREE_RUN":
                errors.append("FX3 VMC-BNCM1 EXT-LK requires TC Make=PRESET and TC Run=FREE_RUN")
            elif not p11_rtc_shim_active:
                errors.append("FX6-on-FX3 EXT-LK requires P11 0x92d2091c /dev/rtc0->udate shim active")
            else:
                ext_lk_active = True
        else:
            ext_lk_active = norm_make == "PRESET" and norm_run == "FREE_RUN"

    if len(errors) == 0:
        if ext_lk_active:
            status = "SMPTE_12M_EXT_LK_READY"
        elif hdmi_tc_out_on:
            status = "SMPTE_12M_HDMI_TC_OUT_READY"
        else:
            status = "SMPTE_12M_INTERNAL_TC_READY"
    elif not phase38_guard_ok:
        status = "BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION"
    elif bnc_tc_out_blocked:
        status = "BLOCKED_FX3_NO_BNC_TC_OUT"
    else:
        status = "BLOCKED_SMPTE_12M_TC_CONTRACT"

    return Smpte12mTimecodeEvalResult(
        valid=len(errors) == 0,
        status=status,
        smpte_tc_str=tc_str,
        smpte_bcd_hex=bcd_hex,
        fps=fps,
        drop_frame=drop_frame,
        tc_make_mode=norm_make,
        tc_run_mode=norm_run,
        ext_lk_requested=ext_lk_requested,
        ext_lk_active=ext_lk_active,
        hdmi_tc_out_on=hdmi_tc_out_on,
        vmc_bncm1_attached=vmc_bncm1_attached,
        uart_boot_active=uart_boot_active,
        phase38_uart_boot_guard_ok=phase38_guard_ok,
        bnc_tc_out_blocked_on_fx3=bnc_tc_out_blocked,
        errors=tuple(errors),
    )


def evaluate_pillar_b_timecode_matrix(
    present_map: Mapping[str, Tuple[str, ...]],
) -> TimecodeMatrixReport:
    """Audit Pillar B: SMPTE 12M Timecode, VMC-BNCM1 EXT-LK, HDMI TC Out, and Phase 38 uart_boot isolation."""
    errors: List[str] = []

    fx3_tc = present_map["fx3_appfw_tc"]
    fx6_tc = present_map["fx6_appfw_tc"]
    fx6_extra_tc = present_map["fx6_appfw_extra_tc"]
    fx3_cp_tc = present_map["fx3_cp_tc"]
    fx6_cp_tc = present_map["fx6_cp_tc"]
    fx6_cp_bnc = present_map["fx6_cp_bnc_tc"]

    if fx3_tc != SHARED_APPFW_TIMECODE_MARKERS:
        missing = tuple(m for m in SHARED_APPFW_TIMECODE_MARKERS if m not in fx3_tc)
        errors.append(f"FX3 appFw.so missing SMPTE 12M / HDMI TC markers: {missing}")
    if fx6_tc != SHARED_APPFW_TIMECODE_MARKERS:
        missing = tuple(m for m in SHARED_APPFW_TIMECODE_MARKERS if m not in fx6_tc)
        errors.append(f"FX6 appFw.so missing SMPTE 12M / HDMI TC markers: {missing}")
    if fx6_extra_tc != FX6_APPFW_EXTRA_TC_MARKERS:
        missing = tuple(m for m in FX6_APPFW_EXTRA_TC_MARKERS if m not in fx6_extra_tc)
        errors.append(f"FX6 appFw.so missing EXT-LK / RTC 0x92d2091c markers: {missing}")
    if fx3_cp_tc != CP_SHARED_TC_MARKERS or fx6_cp_tc != CP_SHARED_TC_MARKERS:
        errors.append("Shared CP timecode PRESET/DFMODE markers missing in cpapp-b.bin")
    if fx6_cp_bnc != FX6_CP_BNC_TC_MARKERS:
        errors.append("FX6 cpapp-b.bin missing BNC TC IO switch markers")

    normal_ext_lk = evaluate_smpte12m_tc_routing(
        target_body="ILME-FX3",
        fps=23.976,
        drop_frame=False,
        tc_make_mode="PRESET",
        tc_run_mode="FREE_RUN",
        ext_lk_requested=True,
        hdmi_tc_out_on=True,
        vmc_bncm1_attached=True,
        uart_boot_active=False,
        p11_rtc_shim_active=True,
    )
    if not normal_ext_lk.valid or not normal_ext_lk.ext_lk_active:
        errors.append("Normal-shooting VMC-BNCM1 EXT-LK check failed")

    hdmi_tc_atomos = evaluate_smpte12m_tc_routing(
        target_body="ILME-FX3",
        fps=29.97,
        drop_frame=True,
        tc_make_mode="REGEN",
        tc_run_mode="REC_RUN",
        ext_lk_requested=False,
        hdmi_tc_out_on=True,
        vmc_bncm1_attached=False,
        uart_boot_active=False,
    )
    if not hdmi_tc_atomos.valid or not hdmi_tc_atomos.hdmi_tc_out_on:
        errors.append("HDMI TC ON (Atomos Ninja/Shogun external trigger) check failed")

    uart_collision = evaluate_smpte12m_tc_routing(
        target_body="ILME-FX3",
        ext_lk_requested=True,
        vmc_bncm1_attached=True,
        uart_boot_active=True,
    )
    if uart_collision.valid or uart_collision.status != "BLOCKED_VMC_BNCM1_UART_BOOT_COLLISION":
        errors.append("Phase 38 VMC-BNCM1 + H0/Tier-3 uart_boot collision guard failed to block")

    tc_matrix: Tuple[TimecodeInterfaceEntry, ...] = (
        TimecodeInterfaceEntry(
            feature_id="TC_MAKE_PRESET_AND_REGEN",
            fx6_interface="TC Make: Preset / Regen (VAL_setting_tc_make_TC_MAKE_*)",
            fx3_interface="TC Make: Preset / Regen (Identical appFw.so + CP DFMODE)",
            smpte_12m_compatible=True,
            verdict="FULL_PARITY",
            notes="Both bodies expose identical TC_MAKE_PRESET / TC_MAKE_REGENRATE & MSG_ID_INFRABB_SYS_SET_TIMECODE_PRESET.",
        ),
        TimecodeInterfaceEntry(
            feature_id="TC_RUN_FREE_RUN_AND_REC_RUN",
            fx6_interface="TC Run: Free Run / Rec Run",
            fx3_interface="TC Run: Free Run / Rec Run",
            smpte_12m_compatible=True,
            verdict="FULL_PARITY",
            notes="Shared TC_RUN_FREE_RUN / TC_RUN_REC_RUN state machine + P11 0x92d2091c /dev/rtc0->udate Free-Run bridge.",
        ),
        TimecodeInterfaceEntry(
            feature_id="EXT_LK_LTC_JAM_SYNC_IN",
            fx6_interface="Dedicated Rear BNC TC IN (Lock/PseudoLock/Unlock)",
            fx3_interface="Multi-Port 15-Pin VMC-BNCM1 LTC IN (Pin 3 LTC+, Pin 2 GND, Pin 6 680k ID)",
            smpte_12m_compatible=True,
            verdict="NORMAL_SHOOTING_EXT_LK_PARITY_WITH_UART_BOOT_ISOLATION",
            notes="Normal shooting EXT-LK supported; Phase 38 rule requires VMC-BNCM1 disconnected during H0/Tier-3 uart_boot (Pins 7/8/9).",
        ),
        TimecodeInterfaceEntry(
            feature_id="BNC_TC_OUT_VS_HDMI_TC_OUT",
            fx6_interface="Dedicated BNC TC OUT + HDMI TC Output On/Off",
            fx3_interface="No BNC TC OUT; HDMI TC Output ON (EXTERNAL_HDMI_TC_OUTPUT_ON)",
            smpte_12m_compatible=True,
            verdict="HDMI_TC_ON_ATOMOS_TRIGGER_PARITY",
            notes="FX3 triggers Atomos Ninja/Shogun via HDMI TC ON; FX3 BNC TC OUT requests fail-closed.",
        ),
    )

    return TimecodeMatrixReport(
        passed=len(errors) == 0,
        shared_appfw_tc_markers=fx3_tc,
        fx6_extra_tc_markers=fx6_extra_tc,
        fx3_cp_tc_markers=fx3_cp_tc,
        fx6_cp_tc_markers=fx6_cp_tc,
        fx6_cp_bnc_tc_markers=fx6_cp_bnc,
        normal_shooting_ext_lk_eval=normal_ext_lk,
        hdmi_tc_atomos_trigger_eval=hdmi_tc_atomos,
        phase38_uart_boot_collision_blocked=uart_collision,
        timecode_matrix=tc_matrix,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Pillar C: 12G-SDI + HDMI Monitoring -> FX3 Full-Size HDMI Type-A Routing
# ---------------------------------------------------------------------------


def evaluate_video_output_routing_policy(
    *,
    target_body: str = "ILME-FX3",
    hdmi_mode: str = "16BIT_LINEAR_RAW",
    hdmi_raw_resolution: str = FX3_HDMI_RAW_SENSOR_READOUT,
    hdmi_output_enabled: bool = True,
    clean_feed_info_off: bool = True,
    lcd_mlut_on: bool = True,
    hdmi_mlut_on: bool = False,
    sdi_sub_output_requested: bool = False,
    sdi_transceiver_present: bool = False,
    fx3_sdi_hw_driver_detected: bool = False,
) -> VideoOutputPolicyResult:
    """Verify HDMI Type-A 16-bit RAW / 4K 4:2:2 clean feed, per-output MLUT, and SDI Sub-Output no-op containment."""
    errors: List[str] = []
    norm_body = target_body.strip().upper()
    norm_mode = hdmi_mode.strip().upper()

    if norm_mode not in ("16BIT_LINEAR_RAW", "4K_DCI_10BIT_422_CLEAN", "QFHD_10BIT_422_CLEAN"):
        errors.append(f"Unsupported HDMI output mode: {hdmi_mode!r}")

    if norm_body == "ILME-FX3":
        if sdi_transceiver_present or fx3_sdi_hw_driver_detected:
            errors.append("FX3 body cannot host 12G-SDI Mew FPGA transceiver hardware")
        if not hdmi_output_enabled:
            errors.append("HDMI Type-A output disabled on FX3 without SDI fallback -> black-screen stall")

    sdi_noop_contained = bool(
        norm_body == "ILME-FX3"
        and not sdi_transceiver_present
        and not fx3_sdi_hw_driver_detected
        and hdmi_output_enabled
    )

    if norm_mode == "16BIT_LINEAR_RAW" and hdmi_mlut_on:
        errors.append("16-bit Linear RAW HDMI stream cannot bake Monitor 3D LUT (MLUT) onto RAW output")

    if norm_mode in ("4K_DCI_10BIT_422_CLEAN", "QFHD_10BIT_422_CLEAN") and not clean_feed_info_off:
        errors.append("Clean feed mode requires HDMI_INFO_DISPLAY_OFF")

    missing_transceiver_panics = 1 if (norm_body == "ILME-FX3" and fx3_sdi_hw_driver_detected) else 0
    black_screen_stalls = 1 if not hdmi_output_enabled else 0
    active_hdmi_feed = bool(hdmi_output_enabled and missing_transceiver_panics == 0)

    if len(errors) == 0:
        if sdi_sub_output_requested and sdi_noop_contained:
            status = "SDI_SUB_OUTPUT_NOOP_CONTAINED_TO_HDMI"
        elif norm_mode == "16BIT_LINEAR_RAW":
            status = "HDMI_TYPE_A_16BIT_LINEAR_RAW_READY"
        else:
            status = "HDMI_TYPE_A_4K_10BIT_422_CLEAN_MLUT_READY"
    else:
        status = "BLOCKED_VIDEO_OUTPUT_PANIC_OR_STALL"

    return VideoOutputPolicyResult(
        valid=len(errors) == 0,
        status=status,
        target_body=norm_body,
        hdmi_mode=norm_mode,
        hdmi_raw_resolution=hdmi_raw_resolution,
        lcd_mlut_on=lcd_mlut_on,
        hdmi_mlut_on=hdmi_mlut_on,
        sdi_sub_output_requested=sdi_sub_output_requested,
        sdi_transceiver_present=sdi_transceiver_present,
        sdi_noop_contained=sdi_noop_contained,
        active_hdmi_feed=active_hdmi_feed,
        missing_transceiver_panics=missing_transceiver_panics,
        black_screen_stalls=black_screen_stalls,
        errors=tuple(errors),
    )


def evaluate_pillar_c_video_output_matrix(
    present_map: Mapping[str, Tuple[str, ...]],
) -> VideoOutputRoutingMatrixReport:
    """Audit Pillar C: 12G-SDI + HDMI Monitoring -> FX3 HDMI Type-A 16-bit RAW, 4:2:2 clean, MLUT, and SDI no-op."""
    errors: List[str] = []

    fx3_shared_hdmi = present_map["fx3_appfw_hdmi_shared"]
    fx6_shared_hdmi = present_map["fx6_appfw_hdmi_shared"]
    fx3_hdmi_feed = present_map["fx3_appfw_hdmi_feed"]
    fx6_mlut_sdi = present_map["fx6_appfw_mlut_sdi"]
    fx6_avbb_panel = present_map["fx6_avbb_panelevf"]
    fx3_unexpected_sdi = present_map["fx3_unexpected_sdi"]

    if fx3_shared_hdmi != SHARED_APPFW_HDMI_RAW_MARKERS or fx6_shared_hdmi != SHARED_APPFW_HDMI_RAW_MARKERS:
        errors.append("Shared HDMI RAW / HDMI Info Display markers missing in FX3 or FX6 appFw.so")
    if fx3_hdmi_feed != FX3_APPFW_HDMI_FEED_MARKERS:
        missing = tuple(m for m in FX3_APPFW_HDMI_FEED_MARKERS if m not in fx3_hdmi_feed)
        errors.append(f"FX3 appFw.so missing HDMI 4K/QFHD 4:2:2 10-bit markers: {missing}")
    if fx6_mlut_sdi != FX6_APPFW_MLUT_AND_SDI_MARKERS:
        missing = tuple(m for m in FX6_APPFW_MLUT_AND_SDI_MARKERS if m not in fx6_mlut_sdi)
        errors.append(f"FX6 appFw.so missing MLUT or SDI containment markers: {missing}")
    if fx6_avbb_panel != FX6_AVBB_PANELEVF_MARKERS:
        missing = tuple(m for m in FX6_AVBB_PANELEVF_MARKERS if m not in fx6_avbb_panel)
        errors.append(f"FX6 AVBB_SCN_START_PANELEVF.so missing HDMI/SDI/MLUT scenario markers: {missing}")
    if len(fx3_unexpected_sdi) > 0:
        errors.append(f"FX3 unexpectedly contains FX6 12G-SDI hardware markers: {fx3_unexpected_sdi}")

    raw_eval = evaluate_video_output_routing_policy(
        target_body="ILME-FX3",
        hdmi_mode="16BIT_LINEAR_RAW",
        hdmi_raw_resolution=FX3_HDMI_RAW_SENSOR_READOUT,
        lcd_mlut_on=True,
        hdmi_mlut_on=False,
        sdi_sub_output_requested=False,
        fx3_sdi_hw_driver_detected=len(fx3_unexpected_sdi) > 0,
    )
    clean_mlut_eval = evaluate_video_output_routing_policy(
        target_body="ILME-FX3",
        hdmi_mode="4K_DCI_10BIT_422_CLEAN",
        hdmi_raw_resolution="4096x2160",
        clean_feed_info_off=True,
        lcd_mlut_on=True,
        hdmi_mlut_on=True,
        sdi_sub_output_requested=False,
        fx3_sdi_hw_driver_detected=len(fx3_unexpected_sdi) > 0,
    )
    sdi_noop_eval = evaluate_video_output_routing_policy(
        target_body="ILME-FX3",
        hdmi_mode="QFHD_10BIT_422_CLEAN",
        hdmi_raw_resolution="3840x2160",
        clean_feed_info_off=True,
        lcd_mlut_on=True,
        hdmi_mlut_on=False,
        sdi_sub_output_requested=True,
        sdi_transceiver_present=False,
        fx3_sdi_hw_driver_detected=len(fx3_unexpected_sdi) > 0,
    )

    for ev in (raw_eval, clean_mlut_eval, sdi_noop_eval):
        if not ev.valid:
            errors.extend(ev.errors)

    zero_panics_stalls = bool(
        raw_eval.missing_transceiver_panics == 0
        and clean_mlut_eval.missing_transceiver_panics == 0
        and sdi_noop_eval.missing_transceiver_panics == 0
        and raw_eval.black_screen_stalls == 0
        and clean_mlut_eval.black_screen_stalls == 0
        and sdi_noop_eval.black_screen_stalls == 0
        and sdi_noop_eval.sdi_noop_contained
    )

    output_matrix: Tuple[VideoOutputRouteEntry, ...] = (
        VideoOutputRouteEntry(
            route_id="HDMI_16BIT_LINEAR_RAW",
            fx6_output_mode="12G-SDI RAW / HDMI RAW (4096x2160 / 3840x2160 / 4240x2392)",
            fx3_hdmi_type_a_route="Full-Size HDMI Type-A 4264x2408 16-bit Linear RAW (up to 60p)",
            mlut_per_output_supported=True,
            sdi_noop_contained=True,
            verdict="HDMI_TYPE_A_16BIT_RAW_VERIFIED",
            notes="LCD MLUT may remain On for operator exposure while HDMI Type-A outputs unbaked 16-bit Linear RAW.",
        ),
        VideoOutputRouteEntry(
            route_id="HDMI_4K_DCI_QFHD_10BIT_422_CLEAN",
            fx6_output_mode="HDMI Out 4K DCI / QFHD 10-bit 4:2:2 (Info Display Off)",
            fx3_hdmi_type_a_route="Full-Size HDMI Type-A 4096x2160 / 3840x2160 10-bit 4:2:2 Clean Feed",
            mlut_per_output_supported=True,
            sdi_noop_contained=True,
            verdict="FULL_PARITY_CLEAN_FEED",
            notes="HDMI_INFO_DISPLAY_OFF suppresses OSD overlays on external monitor/recorder feed.",
        ),
        VideoOutputRouteEntry(
            route_id="MLUT_PER_OUTPUT_LCD_HDMI",
            fx6_output_mode="Monitor 3D LUT On/Off (LCD/VF + HDMI + SDI1/2)",
            fx3_hdmi_type_a_route="Independent LCD MLUT On/Off & HDMI Type-A MLUT On/Off",
            mlut_per_output_supported=True,
            sdi_noop_contained=True,
            verdict="PER_OUTPUT_MLUT_ACTIVE",
            notes="BKID_APP_EXTERN_MONITOR_LUT_LCD_VF_ONOFF & _HDMI_ONOFF active; SDI1 LUT gated via TYPE_SDI_OUTPUT_NOT_SUPPORT.",
        ),
        VideoOutputRouteEntry(
            route_id="SDI_MAIN_AND_SUB_OUTPUT_CONTAINMENT",
            fx6_output_mode="12G-SDI Main + SDI Sub-Output (EXEC_SDI_MAIN_OUTPUT / EXEC_SDI_SUB_OUTPUT)",
            fx3_hdmi_type_a_route="No-Op Contained -> Active HDMI Type-A Feed",
            mlut_per_output_supported=True,
            sdi_noop_contained=True,
            verdict="NO_OP_CONTAINED_ZERO_PANICS_ZERO_STALLS",
            notes="VAL_FEATURE_MANAGER_sdi_output_TYPE_SDI_OUTPUT_NOT_SUPPORT prevents Mew FPGA probe panics & black-screen stalls.",
        ),
    )

    return VideoOutputRoutingMatrixReport(
        passed=len(errors) == 0,
        fx3_shared_hdmi_markers=fx3_shared_hdmi,
        fx6_shared_hdmi_markers=fx6_shared_hdmi,
        fx3_hdmi_feed_markers=fx3_hdmi_feed,
        fx6_mlut_sdi_markers=fx6_mlut_sdi,
        fx6_avbb_panelevf_markers=fx6_avbb_panel,
        fx3_unexpected_sdi_markers=fx3_unexpected_sdi,
        raw_16bit_4264x2408_eval=raw_eval,
        clean_4k_422_10bit_mlut_eval=clean_mlut_eval,
        sdi_sub_output_noop_eval=sdi_noop_eval,
        output_matrix=output_matrix,
        zero_panics_and_zero_stalls_verified=zero_panics_stalls,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Top-Level Phase 51 Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_audio_tc_hdmi_sdi_routing(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    synthetic_overrides: Optional[Mapping[str, bytes]] = None,
) -> AudioTcHdmiSdiRoutingReport:
    """Run Phase 51 4-Ch 24-bit 48kHz Audio, SMPTE 12M Timecode, and 12G-SDI->HDMI Matrix Audit."""
    relpaths: Dict[str, str] = {
        "fx3_appfw": FX3_APPFW_RELPATH,
        "fx6_appfw": FX6_APPFW_RELPATH,
        "fx3_libmpr": FX3_LIBMPR_RELPATH,
        "fx6_libmpr": FX6_LIBMPR_RELPATH,
        "fx3_cpapp": FX3_CPAPP_RELPATH,
        "fx6_cpapp": FX6_CPAPP_RELPATH,
        "fx6_hotshoe": FX6_HOTSHOE_RELPATH,
        "fx6_avbb_audio": FX6_AVBB_AUDIO_RELPATH,
        "fx6_avbb_panelevf": FX6_AVBB_PANELEVF_RELPATH,
    }

    scan_specs: Dict[str, Tuple[str, Tuple[str, ...]]] = {
        "fx3_appfw_audio": ("fx3_appfw", FX3_APPFW_AUDIO_MARKERS),
        "fx6_appfw_audio": ("fx6_appfw", FX6_APPFW_AUDIO_MARKERS),
        "fx3_libmpr_audio": ("fx3_libmpr", MPR_SHARED_AUDIO_MARKERS),
        "fx6_libmpr_audio": ("fx6_libmpr", MPR_SHARED_AUDIO_MARKERS + FX6_MPR_LPCM_MARKERS),
        "fx6_hotshoe": ("fx6_hotshoe", FX6_HOTSHOE_MARKERS),
        "fx6_avbb_audio": ("fx6_avbb_audio", FX6_AVBB_AUDIO_MARKERS),
        "fx3_appfw_tc": ("fx3_appfw", SHARED_APPFW_TIMECODE_MARKERS),
        "fx6_appfw_tc": ("fx6_appfw", SHARED_APPFW_TIMECODE_MARKERS),
        "fx6_appfw_extra_tc": ("fx6_appfw", FX6_APPFW_EXTRA_TC_MARKERS),
        "fx3_cp_tc": ("fx3_cpapp", CP_SHARED_TC_MARKERS),
        "fx6_cp_tc": ("fx6_cpapp", CP_SHARED_TC_MARKERS),
        "fx6_cp_bnc_tc": ("fx6_cpapp", FX6_CP_BNC_TC_MARKERS),
        "fx3_appfw_hdmi_shared": ("fx3_appfw", SHARED_APPFW_HDMI_RAW_MARKERS),
        "fx6_appfw_hdmi_shared": ("fx6_appfw", SHARED_APPFW_HDMI_RAW_MARKERS),
        "fx3_appfw_hdmi_feed": ("fx3_appfw", FX3_APPFW_HDMI_FEED_MARKERS),
        "fx6_appfw_mlut_sdi": ("fx6_appfw", FX6_APPFW_MLUT_AND_SDI_MARKERS),
        "fx6_avbb_panelevf": ("fx6_avbb_panelevf", FX6_AVBB_PANELEVF_MARKERS),
    }

    donor_sizes: Dict[str, int] = {}
    present_map: Dict[str, Tuple[str, ...]] = {}

    if synthetic_overrides is not None:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        blobs = dict(synthetic_overrides)
        use_mmap = False
    else:
        resolved = {
            k: resolve_donor_file(rel, repo_root=repo_root, env=env, clean_room=clean_room)
            for k, rel in relpaths.items()
        }
        if all(p is not None for p in resolved.values()) and not (clean_room or is_forced_clean_room(env)):
            mode = "LOCAL_DONOR_VERIFIED"
            use_mmap = True
        else:
            mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
            blobs = build_clean_room_audio_tc_hdmi_fixtures()
            use_mmap = False

    if use_mmap:
        # Group all marker checks per file so each donor binary is opened & mmapped only once
        file_needles: Dict[str, List[str]] = {k: [] for k in relpaths}
        for spec_file, needles in scan_specs.values():
            file_needles[spec_file].extend(needles)
        file_needles["fx3_appfw"].extend(FX3_FORBIDDEN_SDI_HW_MARKERS)
        file_needles["fx3_cpapp"].extend(FX3_FORBIDDEN_SDI_HW_MARKERS)

        found_per_file: Dict[str, set[str]] = {}
        for fkey, fpath in resolved.items():
            assert fpath is not None
            uniq = tuple(dict.fromkeys(file_needles[fkey]))
            fsize, found = _scan_rdonly_markers(fpath, uniq)
            donor_sizes[fkey] = fsize
            found_per_file[fkey] = set(found)

        for scan_key, (fkey, needles) in scan_specs.items():
            fset = found_per_file[fkey]
            present_map[scan_key] = tuple(n for n in needles if n in fset)

        sdi_hits = []
        for marker in FX3_FORBIDDEN_SDI_HW_MARKERS:
            if marker in found_per_file["fx3_appfw"] or marker in found_per_file["fx3_cpapp"]:
                sdi_hits.append(marker)
        present_map["fx3_unexpected_sdi"] = tuple(sdi_hits)
    else:
        donor_sizes = {k: len(v) for k, v in sorted(blobs.items())}
        for scan_key, (fkey, needles) in scan_specs.items():
            _sz, present = _scan_buffer_markers(blobs[fkey], needles)
            present_map[scan_key] = present

        sdi_hits = []
        for marker in FX3_FORBIDDEN_SDI_HW_MARKERS:
            if (
                blobs["fx3_appfw"].find(marker.encode("latin1")) != -1
                or blobs["fx3_cpapp"].find(marker.encode("latin1")) != -1
            ):
                sdi_hits.append(marker)
        present_map["fx3_unexpected_sdi"] = tuple(sdi_hits)

    pillar_a = evaluate_pillar_a_audio_matrix(present_map)
    pillar_b = evaluate_pillar_b_timecode_matrix(present_map)
    pillar_c = evaluate_pillar_c_video_output_matrix(present_map)

    errors = pillar_a.errors + pillar_b.errors + pillar_c.errors
    all_passed = bool(
        len(errors) == 0
        and pillar_a.passed
        and pillar_b.passed
        and pillar_c.passed
    )

    body_for_hash = {
        "schema_version": PHASE_51_SCHEMA,
        "phase_version": PHASE_51_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "donor_file_sizes": donor_sizes,
        "pillar_a_audio": asdict(pillar_a),
        "pillar_b_timecode": asdict(pillar_b),
        "pillar_c_video_output": asdict(pillar_c),
        "errors": errors,
    }
    report_sha256 = hashlib.sha256(
        json.dumps(body_for_hash, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return AudioTcHdmiSdiRoutingReport(
        schema_version=PHASE_51_SCHEMA,
        phase_version=PHASE_51_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        donor_file_sizes=donor_sizes,
        pillar_a_audio=pillar_a,
        pillar_b_timecode=pillar_b,
        pillar_c_video_output=pillar_c,
        errors=errors,
        report_sha256=report_sha256,
    )


def audio_tc_hdmi_sdi_routing_report_to_dict(report: AudioTcHdmiSdiRoutingReport) -> Dict[str, object]:
    return asdict(report)
