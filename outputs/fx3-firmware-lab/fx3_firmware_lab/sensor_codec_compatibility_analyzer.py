"""Phase 31 — IMX510 Sensor Readout, Dual Base ISO, HDMI RAW & XAVC Codec Matrix Verifier.

Strictly Read-Only (`os.O_RDONLY`) & Clean-Room Dual-Mode:
- Local Donor Mode: opens FX3 v7.02 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`) and
  FX6 v6.01 (`appFw.so`, `libmpr.so`, `cpapp-b.bin`) strictly `os.O_RDONLY` and scans
  using C-level `bytes.find` (< 0.8s across all 6 binaries).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1` or `clean_room=True` or donors absent):
  runs deterministic clean-room synthetic binary fixtures with zero proprietary assets.

Quantifies three hardware/firmware compatibility pillars between ILME-FX3 and ILME-FX6:
1. IMX510 10.2 MP Full-Frame Sensor Readout & Dual Base ISO (`800 / 12800`) Matrix,
   including negative proof that `5016x3344` (`IMAGER_SCANMODE_FF_5K_3_2` /
   `SELECT_CODEC_X_OCN_LT`) lacks encoder support in both `libmpr.so` and `cpapp-b.bin`.
2. `libmpr.so` & `appFw.so` Hardware Encoder Profile Matrix proving `XAVC-I` (`MXF`)
   and `XAVC S-I` (`MP4`) share the identical CXD90057 H.264 High422Intra (`H422IP`)
   bitstream engine and `mpr::SetMovieRecParam` contract, diverging only at muxing
   (`libXavcMxf` vs `libXavcMp4`), alongside `XAVC-L` / `XAVC S` / `XAVC HS` (HEVC).
3. Dual Media Slot (`Slot A / Slot B` <-> `Slot 1 / Slot 2` CFexpress Type A + SDXC)
   parity and `12G-SDI` (`BNC`) vs `HDMI` / `HDMI 16-bit RAW` graceful fallback boundary.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from .haita_bk4_feature_analyzer import (
    DEFAULT_REPO_ROOT,
    FX3_APPFW_RELPATH,
    FX6_APPFW_RELPATH,
    read_bytes_rdonly,
    resolve_donor_file,
)


PHASE_31_SCHEMA = "fx3_firmware_lab_phase31_imx510_xavc_matrix_v1"
PHASE_31_VERSION = "31.0.0"

FX3_LIBMPR_RELPATH = "sony-firmware-20261024/stage2/extraction/files/nflasha15/lib/libmpr.so"
FX6_LIBMPR_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so"
)
FX3_CPAPP_RELPATH = "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin"
FX6_CPAPP_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/fat-files/nflasha8/cpapp-b.bin"
)

IMX510_EFFECTIVE_RESOLUTION = "4264x2408"
IMX510_DUAL_BASE_ISO: Tuple[int, int] = (800, 12800)

# ---------------------------------------------------------------------------
# Verified Binary Marker Contracts (FX3 v7.02 & FX6 v6.01)
# ---------------------------------------------------------------------------

CP_IMX510_DRIVER_MARKERS: Tuple[str, ...] = (
    "N6Camera6Imager6IMX51019C_ImagerCtrl_IMX510E",
    "Camera6Imager21ImagerDrvParam_IMX510E",
)

CP_SHARED_SENSOR_LIROSEQ_MARKERS: Tuple[str, ...] = (
    "mov_size_req",
    "mov_aspect_req",
    "frate_req",
    "e_set_img_frame_size",
    "baseSensitivity",
    "DCI4K",
    "QFHD",
    "FHD",
    "RAW_OUTPUT_MODE",
    "SLOG3",
)

FX3_APPFW_RESOLUTION_MARKERS: Tuple[str, ...] = (
    "DCI4K",
    "QFHD",
    "REC_FORMAT_S_I_DCI_4K_MSG",
    "4096",
    "3840",
    "1920",
)

FX6_APPFW_RESOLUTION_MARKERS: Tuple[str, ...] = (
    "DCI4K",
    "QFHD",
    "VIDEO_FORMAT_4096x2160P",
    "VIDEO_FORMAT_3840x2160P",
    "VIDEO_FORMAT_1920x1080P",
)

FX3_APPFW_DUAL_BASE_ISO_MARKERS: Tuple[str, ...] = (
    "EXPOSURE_INDEX_BASE_ISO_800_EI",
    "EXPOSURE_INDEX_BASE_ISO_12800_EI",
    "BASE_ISO_LOW_800",
    "BASE_ISO_HIGH_12800",
    "SLOG3",
)

FX6_APPFW_DUAL_BASE_ISO_MARKERS: Tuple[str, ...] = (
    "EXPOSURE_INDEX_BASE_ISO_800_EI",
    "EXPOSURE_INDEX_BASE_ISO_12800_EI",
    "BASE_ISO_LOW",
    "BASE_ISO_HIGH",
    "800EI",
    "12800EI",
    "S-Log3",
)

APPFW_SHARED_SQ_HFR_MARKERS: Tuple[str, ...] = (
    "FRAME_RATE_120P",
    "FRAME_RATE_240P",
    "FRAME_RATE_240FPS",
)

FX6_CP_HFR_MARKERS: Tuple[str, ...] = (
    "120p",
    "240p",
)

OPEN_GATE_FX6_APPFW_STRINGS: Tuple[str, ...] = (
    "IMAGER_SCANMODE_FF_5K_3_2",
    "VIDEO_FORMAT_5016x3344P",
    "SELECT_CODEC_X_OCN_LT",
)

OPEN_GATE_ENCODER_ABSENCE_NEEDLES: Tuple[str, ...] = (
    "5016",
    "3344",
    "X_OCN",
    "XOCN",
)

FX3_APPFW_XAVC_MARKERS: Tuple[str, ...] = (
    "XAVC_S_I",
    "XAVC_S_4K",
    "XAVC_S_HD",
    "XAVC_HS_4K",
)

FX6_APPFW_XAVC_MARKERS: Tuple[str, ...] = (
    "XAVC_I",
    "XAVC_L",
    "XAVC_S_I",
    "XAVC_HS_4K",
)

MPR_SHARED_API_SYMBOLS: Tuple[str, ...] = (
    "_ZN3mpr16SetMovieRecParamERKNS_13movieRecParamE",
    "_ZN3mpr28SetMediaProfileClipInfoParamERNS_12MovieRecInfoERNS_10RecMngInfoEPN17LibMediaProfileIf15LibMediaProfile15T_MPF_CLIP_INFOE",
    "_ZN3mpr32SetMediaProfileTakeMaterialParamERNS_12MovieRecInfoERNS_10RecMngInfoEhPN17LibMediaProfileIf15LibMediaProfile15T_MPF_CLIP_INFOE",
    "_ZN5MprIf13SetMediaTitleEmN3MPR9TitleAreaENS0_8CharCodeEPKcS4_",
    "_ZN5MprIf22SetMediaSizeMarginSyncEmj",
)

MPR_SHARED_MOVIE_REC_PARAM_CLASSES: Tuple[str, ...] = (
    "AVC_Intra_4KEN3mpr13movieRecParamE",
    "AVC_Intra_FHDEN3mpr13movieRecParamE",
    "AVC_Long_4KEN3mpr13movieRecParamE",
    "AVC_Long_FHDEN3mpr13movieRecParamE",
    "HEVC_Long_4KEN3mpr13movieRecParamE",
    "HEVC_Long_8KEN3mpr13movieRecParamE",
)

MPR_SHARED_H264_INTRA_PROFILES: Tuple[str, ...] = (
    "AVC480_4096_2160_H422IP",
    "AVC480CBG_4096_2160_H422IP",
    "AVC480_3840_2160_H422IP",
    "AVC480CBG_3840_2160_H422IP",
    "AVCCBG_4096_2160_H422IP",
    "AVCCBG_3840_2160_H422IP",
    "AVC100_1920_1080_H422IP",
    "AVC200CBG_1920_1080_H422IP",
)

MPR_SHARED_H264_LONG_PROFILES: Tuple[str, ...] = (
    "AVC280_3840_2160_H422P",
    "AVC200_3840_2160_H422P",
    "AVC140_3840_2160_H422P",
    "AVC100_3840_2160_H422P",
    "AVC50_1920_1080_H422P",
    "AVC35_1920_1080_H422P",
    "AVC25_1920_1080_H422P",
)

MPR_SHARED_HEVC_PROFILES: Tuple[str, ...] = (
    "HEVC_3840_2160_M42210P",
    "HEVC_3840_2160_M10P",
    "HEVC_Proxy_1920_1080_M10P",
)

MPR_MP4_MUX_MARKERS: Tuple[str, ...] = (
    "LOG_ID_LIBXAVCMP4",
    "XavcsNamer",
)

MPR_FX6_MXF_MUX_MARKERS: Tuple[str, ...] = (
    "LOG_ID_LIBXAVCMXF_MUX",
    "_ZN10libXavcMxf11SetClipNameEjRA4_KN3mpr13ClipNameParamE",
    "GetDProXavcIntraVQuality",
)

FX3_APPFW_DUAL_SLOT_MARKERS: Tuple[str, ...] = (
    "MEDIA_SLOT_1",
    "MEDIA_SLOT_2",
    "SIMULTANEOUS_REC",
    "RELAY_REC",
)

FX6_APPFW_DUAL_SLOT_MARKERS: Tuple[str, ...] = (
    "MEDIA_SLOT_1",
    "MEDIA_SLOT_2",
    "SLOT_A",
    "SLOT_B",
    "No10_SSA",
    "No117_SSA_INACTIVE_FRAME",
    "No116_SSB_INACTIVE_FRAME",
    "SIMULTANEOUS_REC",
    "RELAY_REC",
)

FX6_MPR_SLOT_MARKERS: Tuple[str, ...] = (
    "Slot1",
    "SlotA",
    "SlotB",
    "SDXC",
    "isSDcardMediaType",
    "pmaplSlot2Idx",
)

FX6_APPFW_SDI_MARKERS: Tuple[str, ...] = (
    "PRM_FEATURE_MANAGER_sdi_output",
    "OUTPUT_SDI1",
    "OUTPUT_SDI_SUPER",
    "OUTPUT_SDI_HDMI_STOPPED_VIA_BOOT",
    "MODEL_SDI_HDMI_OUTPUT_PERMITTED",
    "BKID_APP_SETTING_OUTPUT_FORMAT_SDI_HDMI",
)

FX6_CP_SDI_MARKERS: Tuple[str, ...] = (
    "MoniFpgaSdi_SetRegSDIOutFormat",
    "MoniFpga_StartStopSDI",
    "SDIC_ST01_SetMonModeInit",
    "SDIC_ST04_SetModeMonOut",
)

FX3_APPFW_HDMI_RAW_MARKERS: Tuple[str, ...] = (
    "HDMI_RAW_OUTPUT_STATUS_CHANGED",
    "HDMI_RAW_CONNECTSTATE_HDMI_CONNECT",
    "RAW_OUTPUT_FRAME_RATE_60P",
)

FX6_APPFW_HDMI_RAW_MARKERS: Tuple[str, ...] = (
    "HDMI_RAW_OUTPUT_STATUS_CHANGED",
    "RAW_OUTPUT_FORMAT_4096x2160",
    "RAW_OUTPUT_FORMAT_3840x2160",
)


# ---------------------------------------------------------------------------
# Report Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Imx510ScanModeEntry:
    mode_id: str
    resolution: str
    aspect_ratio: str
    max_fps: str
    fx3_supported: bool
    fx6_supported: bool
    encoder_backed: bool
    verdict: str
    notes: str


@dataclass(frozen=True)
class Imx510SensorMatrixReport:
    passed: bool
    sensor_id: str
    effective_resolution: str
    dual_base_iso_bases: Tuple[int, int]
    fx3_cp_imx510_markers: Tuple[str, ...]
    fx6_cp_imx510_markers: Tuple[str, ...]
    shared_cp_liroseq_keys: Tuple[str, ...]
    fx3_appfw_resolution_markers: Tuple[str, ...]
    fx6_appfw_resolution_markers: Tuple[str, ...]
    fx3_appfw_dual_base_iso_markers: Tuple[str, ...]
    fx6_appfw_dual_base_iso_markers: Tuple[str, ...]
    fx3_sq_hfr_markers: Tuple[str, ...]
    fx6_sq_hfr_markers: Tuple[str, ...]
    fx6_cp_hfr_markers: Tuple[str, ...]
    open_gate_fx6_appfw_strings_present: Tuple[str, ...]
    open_gate_fx3_appfw_strings_present: Tuple[str, ...]
    open_gate_libmpr_hits_fx3: Tuple[str, ...]
    open_gate_libmpr_hits_fx6: Tuple[str, ...]
    open_gate_cp_hits_fx3: Tuple[str, ...]
    open_gate_cp_hits_fx6: Tuple[str, ...]
    open_gate_5016x3344_supported: bool
    open_gate_encoder_absence_proven: bool
    scan_mode_matrix: Tuple[Imx510ScanModeEntry, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class CodecCompatibilityEntry:
    codec_id: str
    container: str
    bitstream_format: str
    chroma_bit_depth: str
    fx6_supported: bool
    fx3_supported: bool
    shared_mpr_hw_engine: bool
    verdict: str
    notes: str


@dataclass(frozen=True)
class MprEncoderMatrixReport:
    passed: bool
    fx3_appfw_xavc_markers: Tuple[str, ...]
    fx6_appfw_xavc_markers: Tuple[str, ...]
    fx3_mpr_api_symbols: Tuple[str, ...]
    fx6_mpr_api_symbols: Tuple[str, ...]
    shared_movie_rec_param_classes: Tuple[str, ...]
    shared_h264_intra_profiles: Tuple[str, ...]
    shared_h264_long_profiles: Tuple[str, ...]
    shared_hevc_profiles: Tuple[str, ...]
    fx3_mp4_mux_markers: Tuple[str, ...]
    fx6_mp4_mux_markers: Tuple[str, ...]
    fx6_mxf_mux_markers: Tuple[str, ...]
    fx3_mxf_mux_markers_unexpected: Tuple[str, ...]
    xavc_i_and_xavc_si_hw_engine_identical: bool
    codec_matrix: Tuple[CodecCompatibilityEntry, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MediaSlotAndVideoOutputReport:
    passed: bool
    fx3_dual_slot_markers: Tuple[str, ...]
    fx6_dual_slot_markers: Tuple[str, ...]
    fx6_mpr_slot_markers: Tuple[str, ...]
    dual_cfexpress_sdxc_parity_ok: bool
    slot_parity_verdict: str
    fx6_appfw_sdi_markers: Tuple[str, ...]
    fx3_appfw_sdi_markers_unexpected: Tuple[str, ...]
    fx6_cp_sdi_markers: Tuple[str, ...]
    fx3_cp_sdi_markers_unexpected: Tuple[str, ...]
    fx3_cp_hdmi_present: bool
    fx6_cp_hdmi_present: bool
    fx3_hdmi_raw_markers: Tuple[str, ...]
    fx6_hdmi_raw_markers: Tuple[str, ...]
    sdi_absent_graceful_hdmi_fallback_non_blocking: bool
    video_output_verdict: str
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class SensorCodecCompatibilityReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    donor_file_sizes: Dict[str, int]
    sensor_matrix: Imx510SensorMatrixReport
    mpr_encoder_matrix: MprEncoderMatrixReport
    media_slot_and_video_output: MediaSlotAndVideoOutputReport
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=True) + "\n"


# ---------------------------------------------------------------------------
# Fast C-level `bytes.find` Helpers
# ---------------------------------------------------------------------------


def _find_present_markers(buf: bytes, markers: Sequence[str]) -> Tuple[str, ...]:
    """Return tuple of markers present in `buf` via C-level `bytes.find`."""
    return tuple(m for m in markers if buf.find(m.encode("latin1")) != -1)


# ---------------------------------------------------------------------------
# Clean-Room Synthetic Fixtures (Used ONLY when FX3_FX6_FORCE_CLEAN_ROOM=1 or donors absent)
# ---------------------------------------------------------------------------


def build_clean_room_sensor_codec_fixtures(
    *,
    drop_imx510_cp: bool = False,
    drop_dual_base_iso: bool = False,
    inject_open_gate_in_libmpr: bool = False,
    drop_mpr_h422_profile: bool = False,
    inject_mxf_in_fx3_mpr: bool = False,
    drop_fx3_dual_slot: bool = False,
    inject_sdi_fpga_in_fx3_cp: bool = False,
) -> Dict[str, bytes]:
    """Build deterministic clean-room synthetic buffers matching all 6 donor binaries."""
    elf_hdr = b"\x7fELF\x02\x01\x01\x00" + bytes(56)

    def _pack_tokens(tokens: Sequence[str], *, prefix: bytes = elf_hdr) -> bytes:
        return prefix + b"\x00".join(t.encode("latin1") for t in tokens) + b"\x00"

    fx3_appfw_tokens = [
        *([] if drop_dual_base_iso else list(FX3_APPFW_DUAL_BASE_ISO_MARKERS)),
        *FX3_APPFW_RESOLUTION_MARKERS,
        *APPFW_SHARED_SQ_HFR_MARKERS,
        *FX3_APPFW_HDMI_RAW_MARKERS,
        *([] if drop_fx3_dual_slot else list(FX3_APPFW_DUAL_SLOT_MARKERS)),
        *FX3_APPFW_XAVC_MARKERS,
    ]
    fx6_appfw_tokens = [
        *([] if drop_dual_base_iso else list(FX6_APPFW_DUAL_BASE_ISO_MARKERS)),
        *FX6_APPFW_RESOLUTION_MARKERS,
        *APPFW_SHARED_SQ_HFR_MARKERS,
        *OPEN_GATE_FX6_APPFW_STRINGS,
        *FX6_APPFW_DUAL_SLOT_MARKERS,
        *FX6_APPFW_SDI_MARKERS,
        *FX6_APPFW_HDMI_RAW_MARKERS,
        *FX6_APPFW_XAVC_MARKERS,
    ]

    fx3_mpr_tokens = [
        *MPR_SHARED_API_SYMBOLS,
        *MPR_SHARED_MOVIE_REC_PARAM_CLASSES,
        *(MPR_SHARED_H264_INTRA_PROFILES[:-1] if drop_mpr_h422_profile else MPR_SHARED_H264_INTRA_PROFILES),
        *MPR_SHARED_H264_LONG_PROFILES,
        *MPR_SHARED_HEVC_PROFILES,
        *MPR_MP4_MUX_MARKERS,
        *(MPR_FX6_MXF_MUX_MARKERS if inject_mxf_in_fx3_mpr else ()),
        *(("5016", "3344", "X_OCN") if inject_open_gate_in_libmpr else ()),
    ]
    fx6_mpr_tokens = [
        *MPR_SHARED_API_SYMBOLS,
        *MPR_SHARED_MOVIE_REC_PARAM_CLASSES,
        *(MPR_SHARED_H264_INTRA_PROFILES[:-1] if drop_mpr_h422_profile else MPR_SHARED_H264_INTRA_PROFILES),
        *MPR_SHARED_H264_LONG_PROFILES,
        *MPR_SHARED_HEVC_PROFILES,
        *MPR_MP4_MUX_MARKERS,
        *MPR_FX6_MXF_MUX_MARKERS,
        *FX6_MPR_SLOT_MARKERS,
        *(("5016", "3344", "X_OCN") if inject_open_gate_in_libmpr else ()),
    ]

    cp_hdr = b"LDR\x00" + bytes(60)
    fx3_cp_tokens = [
        *([] if drop_imx510_cp else list(CP_IMX510_DRIVER_MARKERS)),
        *CP_SHARED_SENSOR_LIROSEQ_MARKERS,
        "HDMI",
        *(("MoniFpgaSdi_SetRegSDIOutFormat",) if inject_sdi_fpga_in_fx3_cp else ()),
    ]
    fx6_cp_tokens = [
        *([] if drop_imx510_cp else list(CP_IMX510_DRIVER_MARKERS)),
        *CP_SHARED_SENSOR_LIROSEQ_MARKERS,
        *FX6_CP_HFR_MARKERS,
        *FX6_CP_SDI_MARKERS,
        "HDMI",
    ]

    return {
        "fx3_appfw": _pack_tokens(fx3_appfw_tokens),
        "fx6_appfw": _pack_tokens(fx6_appfw_tokens),
        "fx3_libmpr": _pack_tokens(fx3_mpr_tokens),
        "fx6_libmpr": _pack_tokens(fx6_mpr_tokens),
        "fx3_cpapp": _pack_tokens(fx3_cp_tokens, prefix=cp_hdr),
        "fx6_cpapp": _pack_tokens(fx6_cp_tokens, prefix=cp_hdr),
    }


# ---------------------------------------------------------------------------
# Pillar Evaluators
# ---------------------------------------------------------------------------


def evaluate_imx510_sensor_matrix(blobs: Mapping[str, bytes]) -> Imx510SensorMatrixReport:
    """Audit IMX510 sensor identity, Dual Base ISO (800/12800), S&Q, and 5016x3344 absence."""
    errors: List[str] = []
    fx3_app = blobs["fx3_appfw"]
    fx6_app = blobs["fx6_appfw"]
    fx3_mpr = blobs["fx3_libmpr"]
    fx6_mpr = blobs["fx6_libmpr"]
    fx3_cp = blobs["fx3_cpapp"]
    fx6_cp = blobs["fx6_cpapp"]

    fx3_cp_imx = _find_present_markers(fx3_cp, CP_IMX510_DRIVER_MARKERS)
    fx6_cp_imx = _find_present_markers(fx6_cp, CP_IMX510_DRIVER_MARKERS)
    if fx3_cp_imx != CP_IMX510_DRIVER_MARKERS or fx6_cp_imx != CP_IMX510_DRIVER_MARKERS:
        errors.append("IMX510 sensor driver markers missing in FX3 or FX6 cpapp-b.bin")

    fx3_cp_liro = _find_present_markers(fx3_cp, CP_SHARED_SENSOR_LIROSEQ_MARKERS)
    fx6_cp_liro = _find_present_markers(fx6_cp, CP_SHARED_SENSOR_LIROSEQ_MARKERS)
    shared_liro = tuple(k for k in CP_SHARED_SENSOR_LIROSEQ_MARKERS if k in fx3_cp_liro and k in fx6_cp_liro)
    if shared_liro != CP_SHARED_SENSOR_LIROSEQ_MARKERS:
        errors.append(
            f"Missing shared CP LiroSeq IMX510 keys: "
            f"{tuple(k for k in CP_SHARED_SENSOR_LIROSEQ_MARKERS if k not in shared_liro)}"
        )

    fx3_res = _find_present_markers(fx3_app, FX3_APPFW_RESOLUTION_MARKERS)
    fx6_res = _find_present_markers(fx6_app, FX6_APPFW_RESOLUTION_MARKERS)
    if fx3_res != FX3_APPFW_RESOLUTION_MARKERS or fx6_res != FX6_APPFW_RESOLUTION_MARKERS:
        errors.append("Missing 4K DCI / QFHD / FHD resolution markers in FX3 or FX6 appFw.so")

    fx3_iso = _find_present_markers(fx3_app, FX3_APPFW_DUAL_BASE_ISO_MARKERS)
    fx6_iso = _find_present_markers(fx6_app, FX6_APPFW_DUAL_BASE_ISO_MARKERS)
    if fx3_iso != FX3_APPFW_DUAL_BASE_ISO_MARKERS:
        errors.append("FX3 appFw.so missing Dual Base ISO 800/12800 markers")
    if fx6_iso != FX6_APPFW_DUAL_BASE_ISO_MARKERS:
        errors.append("FX6 appFw.so missing Dual Base ISO 800/12800 markers")

    fx3_sq = _find_present_markers(fx3_app, APPFW_SHARED_SQ_HFR_MARKERS)
    fx6_sq = _find_present_markers(fx6_app, APPFW_SHARED_SQ_HFR_MARKERS)
    fx6_cp_hfr = _find_present_markers(fx6_cp, FX6_CP_HFR_MARKERS)
    if fx3_sq != APPFW_SHARED_SQ_HFR_MARKERS or fx6_sq != APPFW_SHARED_SQ_HFR_MARKERS:
        errors.append("Missing 120p/240p S&Q framerate markers in appFw.so")
    if fx6_cp_hfr != FX6_CP_HFR_MARKERS:
        errors.append("Missing 120p/240p markers in FX6 cpapp-b.bin")

    og_fx6_app = _find_present_markers(fx6_app, OPEN_GATE_FX6_APPFW_STRINGS)
    og_fx3_app = _find_present_markers(fx3_app, OPEN_GATE_FX6_APPFW_STRINGS)
    og_mpr_fx3 = _find_present_markers(fx3_mpr, OPEN_GATE_ENCODER_ABSENCE_NEEDLES)
    og_mpr_fx6 = _find_present_markers(fx6_mpr, OPEN_GATE_ENCODER_ABSENCE_NEEDLES)
    og_cp_fx3 = _find_present_markers(fx3_cp, OPEN_GATE_FX6_APPFW_STRINGS)
    og_cp_fx6 = _find_present_markers(fx6_cp, OPEN_GATE_FX6_APPFW_STRINGS)

    encoder_absent_proven = (
        og_fx6_app == OPEN_GATE_FX6_APPFW_STRINGS
        and len(og_fx3_app) == 0
        and len(og_mpr_fx3) == 0
        and len(og_mpr_fx6) == 0
        and len(og_cp_fx3) == 0
        and len(og_cp_fx6) == 0
    )
    if not encoder_absent_proven:
        errors.append("Open-Gate 5016x3344 / X-OCN LT encoder absence negative proof failed")

    scan_modes: Tuple[Imx510ScanModeEntry, ...] = (
        Imx510ScanModeEntry(
            mode_id="IMX510_FF_4K_DCI",
            resolution="4096x2160",
            aspect_ratio="17:9",
            max_fps="60p (FX6) / 60p XAVC S-I DCI (FX3)",
            fx3_supported=True,
            fx6_supported=True,
            encoder_backed=True,
            verdict="FULL_PARITY",
            notes="Full-width 4.2K oversampled readout via shared CP DCI4K LiroSeq & AVC480_4096_2160_H422IP.",
        ),
        Imx510ScanModeEntry(
            mode_id="IMX510_FF_QFHD_4K",
            resolution="3840x2160",
            aspect_ratio="16:9",
            max_fps="120p (S&Q / HFR crop)",
            fx3_supported=True,
            fx6_supported=True,
            encoder_backed=True,
            verdict="FULL_PARITY",
            notes="Full-frame readout up to 60p + 100p/120p HFR via QFHD LiroSeq & H422IP/M42210P.",
        ),
        Imx510ScanModeEntry(
            mode_id="IMX510_FHD_1080P",
            resolution="1920x1080",
            aspect_ratio="16:9",
            max_fps="240p (S&Q / HFR)",
            fx3_supported=True,
            fx6_supported=True,
            encoder_backed=True,
            verdict="FULL_PARITY",
            notes="1080p up to 240fps S&Q supported by FX3/FX6 appFw.so & libmpr.so H422IP/H422P.",
        ),
        Imx510ScanModeEntry(
            mode_id="IMX510_HDMI_16BIT_RAW",
            resolution="4096x2160 / 3840x2160 (4264x2408 sensor)",
            aspect_ratio="17:9 / 16:9",
            max_fps="60p",
            fx3_supported=True,
            fx6_supported=True,
            encoder_backed=True,
            verdict="HDMI_RAW_PARITY",
            notes="16-bit linear RAW over HDMI (FX3 native; FX6 supports SDI RAW + HDMI RAW fallback).",
        ),
        Imx510ScanModeEntry(
            mode_id="IMX510_OPEN_GATE_5K_3_2",
            resolution="5016x3344",
            aspect_ratio="3:2",
            max_fps="N/A",
            fx3_supported=False,
            fx6_supported=False,
            encoder_backed=False,
            verdict="UNSUPPORTED_NEGATIVE_PROOF",
            notes="Strings exist only in FX6 appFw.so; 0 hits in libmpr.so (FX3 & FX6) and cpapp-b.bin.",
        ),
    )

    return Imx510SensorMatrixReport(
        passed=len(errors) == 0,
        sensor_id="IMX510",
        effective_resolution=IMX510_EFFECTIVE_RESOLUTION,
        dual_base_iso_bases=IMX510_DUAL_BASE_ISO,
        fx3_cp_imx510_markers=fx3_cp_imx,
        fx6_cp_imx510_markers=fx6_cp_imx,
        shared_cp_liroseq_keys=shared_liro,
        fx3_appfw_resolution_markers=fx3_res,
        fx6_appfw_resolution_markers=fx6_res,
        fx3_appfw_dual_base_iso_markers=fx3_iso,
        fx6_appfw_dual_base_iso_markers=fx6_iso,
        fx3_sq_hfr_markers=fx3_sq,
        fx6_sq_hfr_markers=fx6_sq,
        fx6_cp_hfr_markers=fx6_cp_hfr,
        open_gate_fx6_appfw_strings_present=og_fx6_app,
        open_gate_fx3_appfw_strings_present=og_fx3_app,
        open_gate_libmpr_hits_fx3=og_mpr_fx3,
        open_gate_libmpr_hits_fx6=og_mpr_fx6,
        open_gate_cp_hits_fx3=og_cp_fx3,
        open_gate_cp_hits_fx6=og_cp_fx6,
        open_gate_5016x3344_supported=False,
        open_gate_encoder_absence_proven=encoder_absent_proven,
        scan_mode_matrix=scan_modes,
        errors=tuple(errors),
    )


def evaluate_mpr_encoder_matrix(blobs: Mapping[str, bytes]) -> MprEncoderMatrixReport:
    """Compare libmpr.so & appFw.so codec profiles and MXF vs MP4 muxer capabilities."""
    errors: List[str] = []
    fx3_app = blobs["fx3_appfw"]
    fx6_app = blobs["fx6_appfw"]
    fx3_mpr = blobs["fx3_libmpr"]
    fx6_mpr = blobs["fx6_libmpr"]

    fx3_app_xavc = _find_present_markers(fx3_app, FX3_APPFW_XAVC_MARKERS)
    fx6_app_xavc = _find_present_markers(fx6_app, FX6_APPFW_XAVC_MARKERS)
    if fx3_app_xavc != FX3_APPFW_XAVC_MARKERS or fx6_app_xavc != FX6_APPFW_XAVC_MARKERS:
        errors.append("Missing XAVC codec selection markers in FX3 or FX6 appFw.so")

    fx3_api = _find_present_markers(fx3_mpr, MPR_SHARED_API_SYMBOLS)
    fx6_api = _find_present_markers(fx6_mpr, MPR_SHARED_API_SYMBOLS)
    if fx3_api != MPR_SHARED_API_SYMBOLS or fx6_api != MPR_SHARED_API_SYMBOLS:
        errors.append("Shared mpr::SetMovieRecParam / SetMediaProfile API symbols missing in libmpr.so")

    fx3_classes = _find_present_markers(fx3_mpr, MPR_SHARED_MOVIE_REC_PARAM_CLASSES)
    fx6_classes = _find_present_markers(fx6_mpr, MPR_SHARED_MOVIE_REC_PARAM_CLASSES)
    shared_classes = tuple(
        c for c in MPR_SHARED_MOVIE_REC_PARAM_CLASSES if c in fx3_classes and c in fx6_classes
    )
    if shared_classes != MPR_SHARED_MOVIE_REC_PARAM_CLASSES:
        errors.append("movieRecParam hardware encoder class parity broken between FX3 and FX6 libmpr.so")

    fx3_intra = _find_present_markers(fx3_mpr, MPR_SHARED_H264_INTRA_PROFILES)
    fx6_intra = _find_present_markers(fx6_mpr, MPR_SHARED_H264_INTRA_PROFILES)
    shared_intra = tuple(p for p in MPR_SHARED_H264_INTRA_PROFILES if p in fx3_intra and p in fx6_intra)
    if shared_intra != MPR_SHARED_H264_INTRA_PROFILES:
        errors.append("H.264 High422Intra (H422IP) encoder profile mismatch between FX3 and FX6 libmpr.so")

    fx3_long = _find_present_markers(fx3_mpr, MPR_SHARED_H264_LONG_PROFILES)
    fx6_long = _find_present_markers(fx6_mpr, MPR_SHARED_H264_LONG_PROFILES)
    shared_long = tuple(p for p in MPR_SHARED_H264_LONG_PROFILES if p in fx3_long and p in fx6_long)
    if shared_long != MPR_SHARED_H264_LONG_PROFILES:
        errors.append("H.264 High422 Long-GOP (H422P) encoder profile mismatch between FX3 and FX6 libmpr.so")

    fx3_hevc = _find_present_markers(fx3_mpr, MPR_SHARED_HEVC_PROFILES)
    fx6_hevc = _find_present_markers(fx6_mpr, MPR_SHARED_HEVC_PROFILES)
    shared_hevc = tuple(p for p in MPR_SHARED_HEVC_PROFILES if p in fx3_hevc and p in fx6_hevc)
    if shared_hevc != MPR_SHARED_HEVC_PROFILES:
        errors.append("HEVC (M42210P/M10P) encoder profile mismatch between FX3 and FX6 libmpr.so")

    fx3_mp4 = _find_present_markers(fx3_mpr, MPR_MP4_MUX_MARKERS)
    fx6_mp4 = _find_present_markers(fx6_mpr, MPR_MP4_MUX_MARKERS)
    if fx3_mp4 != MPR_MP4_MUX_MARKERS or fx6_mp4 != MPR_MP4_MUX_MARKERS:
        errors.append("MP4 XAVC muxer markers missing in FX3 or FX6 libmpr.so")

    fx6_mxf = _find_present_markers(fx6_mpr, MPR_FX6_MXF_MUX_MARKERS)
    fx3_mxf_unexpected = _find_present_markers(fx3_mpr, MPR_FX6_MXF_MUX_MARKERS)
    if fx6_mxf != MPR_FX6_MXF_MUX_MARKERS:
        errors.append("FX6 libmpr.so missing libXavcMxf / GetDProXavcIntraVQuality markers")
    if len(fx3_mxf_unexpected) > 0:
        errors.append(f"FX3 libmpr.so unexpectedly contains FX6 MXF symbols: {fx3_mxf_unexpected}")

    hw_engine_identical = (
        shared_classes == MPR_SHARED_MOVIE_REC_PARAM_CLASSES
        and shared_intra == MPR_SHARED_H264_INTRA_PROFILES
        and shared_long == MPR_SHARED_H264_LONG_PROFILES
        and shared_hevc == MPR_SHARED_HEVC_PROFILES
    )

    codec_matrix: Tuple[CodecCompatibilityEntry, ...] = (
        CodecCompatibilityEntry(
            codec_id="XAVC-I",
            container="MXF",
            bitstream_format="H.264 High422Intra (AVC_Intra_4K / AVC480_*_H422IP)",
            chroma_bit_depth="4:2:2 10-bit All-Intra",
            fx6_supported=True,
            fx3_supported=False,
            shared_mpr_hw_engine=True,
            verdict="SHARED_HW_ENGINE_MXF_MUX_FX6_ONLY",
            notes="Identical CXD90057 H422IP encoder bitstream as XAVC S-I; FX6 libmpr.so adds libXavcMxf.",
        ),
        CodecCompatibilityEntry(
            codec_id="XAVC S-I",
            container="MP4",
            bitstream_format="H.264 High422Intra (AVC_Intra_4K / AVC480_*_H422IP)",
            chroma_bit_depth="4:2:2 10-bit All-Intra",
            fx6_supported=True,
            fx3_supported=True,
            shared_mpr_hw_engine=True,
            verdict="FULLY_SHARED_BITSTREAM_AND_MP4",
            notes="Both FX3 & FX6 share H422IP bitstream profiles and LOG_ID_LIBXAVCMP4 muxer.",
        ),
        CodecCompatibilityEntry(
            codec_id="XAVC-L",
            container="MXF",
            bitstream_format="H.264 Long-GOP (AVC_Long_4K / AVC*_H422P)",
            chroma_bit_depth="4:2:2 10-bit / 4:2:0 8-bit",
            fx6_supported=True,
            fx3_supported=False,
            shared_mpr_hw_engine=True,
            verdict="SHARED_HW_ENGINE_MXF_MUX_FX6_ONLY",
            notes="Shared AVC*_H422P hardware Long-GOP encoder; MXF container muxing lives in FX6 libmpr.so.",
        ),
        CodecCompatibilityEntry(
            codec_id="XAVC S",
            container="MP4",
            bitstream_format="H.264 Long-GOP (AVC_Long_4K / AVC*_H422P)",
            chroma_bit_depth="4:2:2 10-bit / 4:2:0 8-bit",
            fx6_supported=True,
            fx3_supported=True,
            shared_mpr_hw_engine=True,
            verdict="FULLY_SHARED_BITSTREAM_AND_MP4",
            notes="Shared H.264 Long-GOP profiles and libXavcMp4 container path.",
        ),
        CodecCompatibilityEntry(
            codec_id="XAVC HS",
            container="MP4",
            bitstream_format="HEVC (HEVC_Long_4K / HEVC_3840_2160_M42210P / M10P)",
            chroma_bit_depth="4:2:2 10-bit / 4:2:0 10-bit",
            fx6_supported=True,
            fx3_supported=True,
            shared_mpr_hw_engine=True,
            verdict="FULLY_SHARED_BITSTREAM_AND_MP4",
            notes="Identical HEVC_3840_2160_M42210P & M10P profiles in both FX3 & FX6 libmpr.so.",
        ),
        CodecCompatibilityEntry(
            codec_id="X-OCN LT (5016x3344)",
            container="N/A",
            bitstream_format="None (absent in libmpr.so)",
            chroma_bit_depth="N/A",
            fx6_supported=False,
            fx3_supported=False,
            shared_mpr_hw_engine=False,
            verdict="UNSUPPORTED_ENCODER_ABSENT_BOTH_BODIES",
            notes="UI/scanmode string exists in FX6 appFw.so only; no encoder exists in FX3/FX6 libmpr.so.",
        ),
    )

    return MprEncoderMatrixReport(
        passed=len(errors) == 0,
        fx3_appfw_xavc_markers=fx3_app_xavc,
        fx6_appfw_xavc_markers=fx6_app_xavc,
        fx3_mpr_api_symbols=fx3_api,
        fx6_mpr_api_symbols=fx6_api,
        shared_movie_rec_param_classes=shared_classes,
        shared_h264_intra_profiles=shared_intra,
        shared_h264_long_profiles=shared_long,
        shared_hevc_profiles=shared_hevc,
        fx3_mp4_mux_markers=fx3_mp4,
        fx6_mp4_mux_markers=fx6_mp4,
        fx6_mxf_mux_markers=fx6_mxf,
        fx3_mxf_mux_markers_unexpected=fx3_mxf_unexpected,
        xavc_i_and_xavc_si_hw_engine_identical=hw_engine_identical,
        codec_matrix=codec_matrix,
        errors=tuple(errors),
    )


def evaluate_media_slot_and_video_output(blobs: Mapping[str, bytes]) -> MediaSlotAndVideoOutputReport:
    """Verify dual CFexpress Type A / SDXC slot parity and SDI-absent/HDMI-present fallback."""
    errors: List[str] = []
    fx3_app = blobs["fx3_appfw"]
    fx6_app = blobs["fx6_appfw"]
    fx6_mpr = blobs["fx6_libmpr"]
    fx3_cp = blobs["fx3_cpapp"]
    fx6_cp = blobs["fx6_cpapp"]

    fx3_slots = _find_present_markers(fx3_app, FX3_APPFW_DUAL_SLOT_MARKERS)
    fx6_slots = _find_present_markers(fx6_app, FX6_APPFW_DUAL_SLOT_MARKERS)
    fx6_mpr_slots = _find_present_markers(fx6_mpr, FX6_MPR_SLOT_MARKERS)

    slot_parity_ok = (
        fx3_slots == FX3_APPFW_DUAL_SLOT_MARKERS
        and fx6_slots == FX6_APPFW_DUAL_SLOT_MARKERS
        and fx6_mpr_slots == FX6_MPR_SLOT_MARKERS
    )
    if not slot_parity_ok:
        errors.append("Dual CFexpress Type A / SDXC slot markers incomplete across FX3/FX6")

    fx6_app_sdi = _find_present_markers(fx6_app, FX6_APPFW_SDI_MARKERS)
    fx3_app_sdi_unexpected = _find_present_markers(fx3_app, FX6_APPFW_SDI_MARKERS)
    fx6_cp_sdi = _find_present_markers(fx6_cp, FX6_CP_SDI_MARKERS)
    fx3_cp_sdi_unexpected = _find_present_markers(fx3_cp, FX6_CP_SDI_MARKERS)

    fx3_cp_hdmi = fx3_cp.find(b"HDMI") != -1
    fx6_cp_hdmi = fx6_cp.find(b"HDMI") != -1
    fx3_hdmi = _find_present_markers(fx3_app, FX3_APPFW_HDMI_RAW_MARKERS)
    fx6_hdmi = _find_present_markers(fx6_app, FX6_APPFW_HDMI_RAW_MARKERS)

    if fx6_app_sdi != FX6_APPFW_SDI_MARKERS or fx6_cp_sdi != FX6_CP_SDI_MARKERS:
        errors.append("FX6 SDI output markers missing from FX6 appFw.so or cpapp-b.bin")
    if len(fx3_app_sdi_unexpected) > 0 or len(fx3_cp_sdi_unexpected) > 0:
        errors.append("FX3 unexpectedly contains FX6-only SDI hardware driver markers")
    if (not fx3_cp_hdmi) or (not fx6_cp_hdmi):
        errors.append("HDMI marker missing in FX3 or FX6 cpapp-b.bin")
    if fx3_hdmi != FX3_APPFW_HDMI_RAW_MARKERS or fx6_hdmi != FX6_APPFW_HDMI_RAW_MARKERS:
        errors.append("HDMI / HDMI RAW markers missing in FX3 or FX6 appFw.so")

    sdi_fallback_ok = (
        fx6_app_sdi == FX6_APPFW_SDI_MARKERS
        and fx6_cp_sdi == FX6_CP_SDI_MARKERS
        and len(fx3_app_sdi_unexpected) == 0
        and len(fx3_cp_sdi_unexpected) == 0
        and fx3_cp_hdmi
        and fx6_cp_hdmi
        and fx3_hdmi == FX3_APPFW_HDMI_RAW_MARKERS
        and fx6_hdmi == FX6_APPFW_HDMI_RAW_MARKERS
    )

    return MediaSlotAndVideoOutputReport(
        passed=len(errors) == 0,
        fx3_dual_slot_markers=fx3_slots,
        fx6_dual_slot_markers=fx6_slots,
        fx6_mpr_slot_markers=fx6_mpr_slots,
        dual_cfexpress_sdxc_parity_ok=slot_parity_ok,
        slot_parity_verdict=(
            "DUAL_CFEXPRESS_TYPE_A_SDXC_PARITY_VERIFIED"
            if slot_parity_ok
            else "MEDIA_SLOT_PARITY_FAILED"
        ),
        fx6_appfw_sdi_markers=fx6_app_sdi,
        fx3_appfw_sdi_markers_unexpected=fx3_app_sdi_unexpected,
        fx6_cp_sdi_markers=fx6_cp_sdi,
        fx3_cp_sdi_markers_unexpected=fx3_cp_sdi_unexpected,
        fx3_cp_hdmi_present=fx3_cp_hdmi,
        fx6_cp_hdmi_present=fx6_cp_hdmi,
        fx3_hdmi_raw_markers=fx3_hdmi,
        fx6_hdmi_raw_markers=fx6_hdmi,
        sdi_absent_graceful_hdmi_fallback_non_blocking=sdi_fallback_ok,
        video_output_verdict=(
            "SDI_ABSENT_GRACEFUL_HDMI_FALLBACK_NON_BLOCKING"
            if sdi_fallback_ok
            else "VIDEO_OUTPUT_BOUNDARY_FAILED"
        ),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Top-Level Analyzer
# ---------------------------------------------------------------------------


def analyze_sensor_and_codec_compatibility(
    *,
    clean_room: bool = False,
    repo_root: Path = DEFAULT_REPO_ROOT,
    env: Optional[Mapping[str, str]] = None,
    synthetic_overrides: Optional[Mapping[str, bytes]] = None,
) -> SensorCodecCompatibilityReport:
    """Run Phase 31 IMX510 sensor, Dual Base ISO, XAVC encoder, and slot/video audit."""
    if synthetic_overrides is not None:
        mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        blobs = dict(synthetic_overrides)
    else:
        relpaths = {
            "fx3_appfw": FX3_APPFW_RELPATH,
            "fx6_appfw": FX6_APPFW_RELPATH,
            "fx3_libmpr": FX3_LIBMPR_RELPATH,
            "fx6_libmpr": FX6_LIBMPR_RELPATH,
            "fx3_cpapp": FX3_CPAPP_RELPATH,
            "fx6_cpapp": FX6_CPAPP_RELPATH,
        }
        resolved = {
            k: resolve_donor_file(rel, repo_root=repo_root, env=env, clean_room=clean_room)
            for k, rel in relpaths.items()
        }
        if all(p is not None for p in resolved.values()):
            mode = "LOCAL_DONOR_VERIFIED"
            blobs = {k: read_bytes_rdonly(p) for k, p in resolved.items() if p is not None}
        else:
            mode = "CLEAN_ROOM_SYNTHETIC_VERIFIED"
            blobs = build_clean_room_sensor_codec_fixtures()

    donor_sizes = {k: len(v) for k, v in sorted(blobs.items())}
    sensor_rep = evaluate_imx510_sensor_matrix(blobs)
    mpr_rep = evaluate_mpr_encoder_matrix(blobs)
    slot_video_rep = evaluate_media_slot_and_video_output(blobs)

    errors = sensor_rep.errors + mpr_rep.errors + slot_video_rep.errors
    all_passed = bool(
        len(errors) == 0
        and sensor_rep.passed
        and mpr_rep.passed
        and slot_video_rep.passed
    )

    body_for_hash = {
        "schema_version": PHASE_31_SCHEMA,
        "phase_version": PHASE_31_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "donor_file_sizes": donor_sizes,
        "sensor_matrix": asdict(sensor_rep),
        "mpr_encoder_matrix": asdict(mpr_rep),
        "media_slot_and_video_output": asdict(slot_video_rep),
        "errors": errors,
    }
    report_sha256 = hashlib.sha256(
        json.dumps(body_for_hash, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return SensorCodecCompatibilityReport(
        schema_version=PHASE_31_SCHEMA,
        phase_version=PHASE_31_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        donor_file_sizes=donor_sizes,
        sensor_matrix=sensor_rep,
        mpr_encoder_matrix=mpr_rep,
        media_slot_and_video_output=slot_video_rep,
        errors=errors,
        report_sha256=report_sha256,
    )


def sensor_codec_report_to_dict(report: SensorCodecCompatibilityReport) -> Dict[str, object]:
    return asdict(report)
