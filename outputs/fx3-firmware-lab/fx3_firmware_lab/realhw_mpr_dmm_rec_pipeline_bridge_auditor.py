"""Phase 140 — 28th Unified Firmware-Lab Auditor: Real-Hardware Main Track Part 6 —
FX6 `appFw.so` -> Stock FX3 `libMpr.so` / `osal_uipc` / `DMM` `MAIN` Card-Recording
& Live-View Parameter-Binding ABI Bridge Auditor.

Strictly Read-Only (`os.O_RDONLY` + `mmap.ACCESS_READ`) & Clean-Room Dual-Mode:
- Local Donor Mode: inspects FX3 v7.02 (`libmpr.so`, `appFw.so`, `DmmCfg.bin` AP,
  `osal_uipc.ko`, `libosal_uipc.so`, `libInfraAvbbc.so`, `im.elf`) and FX6 v6.01
  (`libmpr.so`, `appFw.so`, `DmmCfg.bin` AP `59,364 B`, `osal_uipc.ko`,
  `libosal_uipc.so`, `libInfraAvbbc.so`, `im.elf`) strictly via `os.O_RDONLY` +
  `mmap.ACCESS_READ` using fast ELF64 `.dynsym`/`.dynstr`/`DT_NEEDED`, DmmCfg binary
  decoding, and targeted byte scans (< 0.25s total).
- Clean-Room Mode (`FX3_FX6_FORCE_CLEAN_ROOM=1`, `clean_room=True`, or donors
  absent): synthesizes deterministic clean-room ELF64 `.so`/`.elf` fixtures,
  `DmmCfg.bin` containers, `osal_uipc.ko` markers, and parameter contracts
  (< 0.03s warm, zero proprietary files required).

Audits Four Phase 140 Pillars:
1. Pillar 1 (`LIBMPR_EXPORT_AND_OPEN_START_CLOSE_ABI_DIFF`):
   Compares exported dynamic symbols (`SHT_DYNSYM`/`SHT_STRTAB` + `DT_NEEDED`),
   `PrepareRecStart`/`RecStart`/`RecStop`, `Codec::EncOpen`/`EncStart`/`EncStop`/
   `EncClose`, `SetMovieRecParam`/`GetMovieRecStatus`, `ParameterControl`
   (`libInfraAvbbc.so` / `libMWF.so`), and `CallbackFromAvbbc`/`execRecMovie` queue
   lifecycle between FX3 v7.02 and FX6 v6.01, proving exact pass-through vs
   `LD_PRELOAD` shim interceptors (`15` FX6-only `libmpr.so` symbols imported by
   FX6 `appFw.so`) and struct size isolation (`g_videoParamComb` `312 B` vs `480 B`,
   `s_movieRecInfo` `3,144 B` vs `5,248 B`).
2. Pillar 2 (`DMM_CFG_NODE_TOPOLOGY_AND_UNSUPPORTED_SINK_MASK`):
   Decodes FX3 (`66,796 B`, `603` units, `290` rules) and FX6 (`59,364 B`, `556`
   units, `259` rules) AP `DmmCfg.bin` tables, verifies all `20` target MAIN
   recording unit IDs across DMM modes `21/25/31/32` (`7/10/13/19` rows, `1` extent
   each, max `8` extents in `0xa8` stack reply), audits `MAIN` / `LIVE_VIEW_GPE_HDMI` /
   `PROXY` / `AUDIO_LPCM` sinks, and enforces fail-safe masking/stubbing of FX6-only
   hardware nodes (`12G_SDI_SERIALIZER` / `mew.bin`, `RAW_OVER_SDI`,
   `DARWIN_VARIABLE_ND` / `darwin_core.bin`).
3. Pillar 3 (`MENU_EVENT_TO_CP_PARAMETER_BINDING_CONTRACT`):
   Verifies deterministic end-to-end parameter translation (`FX6 Menu Event ->
   ParameterControl Payload -> Stock FX3 CP Consumer`) across all 6 core real-
   shooting domains: Base ISO (`800` / `12800` dual native gain), Frame Rate &
   S&Q (`1..240 fps` IMX510 readout), Exposure/Shutter Angle->Speed (`180 deg @ 24p
   -> 1/48s`, mechanical shutter parked open), White Balance (`2000K..15000K` + Tint
   `-99..+99`), Color/Look (`S-Log3 / S-Gamut3.Cine`, `S-Cinetone`, `.cube` MLUT),
   and REC Start/Stop (`CFexpress Type A` / `SDXC` `Slot A & B`), rejecting
   unsupported `5016x3344` Open-Gate / `X-OCN` / unmasked FX6-only hardware.
4. Pillar 4 (`UIPC_QUEUE_GUARD_AND_RECORD_LOCK_SAFETY`):
   Verifies `osal_uipc` fixed-message-area bounds (`GetFixedArea(0..4)`, `0x8e00`
   total, `+0x08` phys vs `+0x28` virt domain separation, `osal_valloc_msg_wait`
   `align64(align4(L)+24+4+40)` on `0x80c70047 -> 0x8055001f`, `ReceiveASync`
   `384 B` cap, `op 0..16` & `pointer+15 <= limit`), callback release order
   (`CallbackFromAvbbc` 48 B copy before `osal_free_msg` `0x8000000b`), `s_movieRWlock`
   pairing on `s_movieRecStatus` (`136 B`), `execRecMovie` (`36,512 B` / `0x8ea0`)
   + 4-record (`384 B`) cleanup, `s_recordCounter` close gating (preventing `.RSV`
   unfinalized clips or IPC queue hangs), and zero persistent eMMC/NOR/calibration
   write authorization (`persistent_emmc_writes_authorized = False`).
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


PHASE_140_SCHEMA = "fx3_firmware_lab_phase140_realhw_mpr_dmm_rec_bridge_v1"
PHASE_140_VERSION = "140.0.0"

# ---------------------------------------------------------------------------
# Verified Local Donor Relative Paths (strictly O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------

FX3_LIBMPR_P140_RELPATH = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libmpr.so"
)
FX6_LIBMPR_P140_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libmpr.so"
)
FX3_APPFW_P140_RELPATH = "fx3-vm-20261101/fx3-audit/original-members/nflasha15/lib/appFw.so"
FX6_APPFW_P140_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/appFw.so"
)
FX3_AP_DMMCFG_RELPATH = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/setting/DmmCfg.bin"
)
FX6_AP_DMMCFG_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0800_appli/setting/DmmCfg.bin"
)
FX3_OSAL_UIPC_KO_RELPATH = (
    "sony-firmware-20261024/stage201-updater-request-endpoint/originals/7.02-main/kmod/osal_uipc.ko"
)
FX6_OSAL_UIPC_KO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/kmod/osal_uipc.ko"
)
FX3_LIBOSAL_UIPC_SO_RELPATH = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libosal_uipc.so"
)
FX6_LIBOSAL_UIPC_SO_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libosal_uipc.so"
)
FX3_LIBINFRA_AVBBC_RELPATH = (
    "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libInfraAvbbc.so"
)
FX6_LIBINFRA_AVBBC_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/lib/libInfraAvbbc.so"
)
FX3_IM_ELF_RELPATH = "fx3-vm-20261101/fx3-audit/original-members/nflasha15/bin/im.elf"
FX6_IM_ELF_RELPATH = (
    "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/nflasha15-files/bin/im.elf"
)

# ---------------------------------------------------------------------------
# Pillar 1 Constants: libmpr.so / libInfraAvbbc.so / im.elf ABI Diff
# ---------------------------------------------------------------------------

CORE_MPR_LIFECYCLE_SYMBOLS: Tuple[str, ...] = (
    "_ZN3mpr15PrepareRecStartERKNS_22prepareRecStartInParamEPNS_23prepareRecStartOutParamE",
    "_ZN3mpr8RecStartERKNS_15recStartInParamE",
    "_ZN3mpr7RecStopERKNS_14recStopInParamE",
    "_ZN3mpr16SetMovieRecParamERKNS_13movieRecParamE",
    "_ZN3mpr16GetMovieRecParamEPNS_13movieRecParamE",
    "_ZN3mpr17GetMovieRecStatusENS_24getMovieRecStatusInParamEPNS_25getMovieRecStatusOutParamE",
    "_ZN3mpr25GetMovieRecStatusInternalEPNS_25getMovieRecStatusOutParamE",
    "_ZN3mpr26GetMovieRecStatusForUpdateEPNS_25getMovieRecStatusOutParamE",
    "_ZN3mpr20UnlockMovieRecStatusEv",
    "_ZN3mpr12GetDmmModeIdERNS_12MovieRecInfoE",
    "_ZN3mpr10DmmMemInfo13GetDmmExtListEPNS0_21t_unitTypeConvertListEPjP10dmm_munmap",
    "_ZN3mpr10DmmMemInfo9SetMemTblEjiPNS0_11BufferTableE",
    "_ZN3mpr11ExecEncOpenEPv",
    "_ZN3mpr12ExecEncStartEPv",
    "_ZN3mpr11ExecEncStopEPv",
    "_ZN3mpr12ExecEncCloseEPv",
    "_ZN3mpr5Codec17CallbackFromAvbbcEPvS1_",
    "_ZN3mpr5Codec14SendMsgToAvbbcEP10PayloadMprP12PayloadCodec",
    "_ZN3mpr6memory12GetFixedAreaENS0_13FixedAreaTypeEPPvS3_Pj",
    "_ZN3mpr10SetLutDataERKNS_17setLutDataInParamE",
)

FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS: Tuple[str, ...] = (
    "_ZN3mpr12RecClipCloseERKNS_19recClipCloseInParamE",
    "_ZN3mpr13GetResumeInfoERKNS_20getResumeInfoInParamE",
    "_ZN3mpr18GetMovieDetailInfoERKNS_25getMovieDetailInfoInParamE",
    "_ZN3mpr19ChangeMovieRecMediaERKNS_26changeMovieRecMediaInParamE",
    "_ZN3mpr19GetCacheRecBackTimeERKNS_26getCacheRecBackTimeInParamEPNS_27getCacheRecBackTimeOutParamE",
    "_ZN3mpr23GetMediaTransferRateInhERKNS_30getMediaTransferRateInhInParamEPNS_31getMediaTransferRateInhOutParamE",
    "_ZN3mpr4file25GetTrimSupportFormatTableEPNS0_33getTrimSupportFormatTableOutParamE",
    "_ZN3mpr4file4StatEPcPmPN9DefStruct9LocalTimeES5_S5_",
    "_ZN3mpr8ClipNameC1Ev",
    "_ZN3mpr8ClipNameD1Ev",
    "_ZN3mpr8RecPauseERKNS_15recPauseInParamE",
    "_ZN3mpr9CheckCopyERKNS_13copyConditionERKNS_12ContentsListEPbPNS_7CopyInhEPNS_15CheckCopyDetailE",
    "_ZN3mpr9GetLastTCERKNS_16getLastTCInParamEPNS_17getLastTCOutParamE",
    "_ZN3mpr9NextThumbERKNS_16nextThumbInParamE",
    "_ZN3mpr9RecResumeERKNS_16recResumeInParamE",
)

MPR_STATE_STRUCT_SIZES_FX3: Dict[str, int] = {
    "_ZN3mpr16g_videoParamCombE": 312,
    "_ZN3mpr14s_movieRecInfoE": 3144,
    "_ZN3mpr16s_movieRecStatusE": 136,
    "_ZN3mpr13s_movieRWlockE": 64,
    "_ZN3mpr15s_recordCounterE": 4,
    "_ZN3mpr6memory14s_mprFixedAreaE": 160,
}

MPR_STATE_STRUCT_SIZES_FX6: Dict[str, int] = {
    "_ZN3mpr16g_videoParamCombE": 480,
    "_ZN3mpr14s_movieRecInfoE": 5248,
    "_ZN3mpr16s_movieRecStatusE": 136,
    "_ZN3mpr13s_movieRWlockE": 64,
    "_ZN3mpr15s_recordCounterE": 4,
    "_ZN3mpr6memory14s_mprFixedAreaE": 160,
}

# ---------------------------------------------------------------------------
# Pillar 2 Constants: DmmCfg.bin Topology & Unsupported Sink Mask
# ---------------------------------------------------------------------------

TARGET_MAIN_DMM_UNIT_IDS: Tuple[int, ...] = (
    700, 701, 822, 823, 922, 939, 962, 963, 966, 974,
    975, 985, 986, 987, 991, 1243, 1244, 1245, 1246, 528413,
)

DMM_MODE_ROW_COUNTS: Dict[int, int] = {
    21: 7,
    25: 10,
    31: 13,
    32: 19,
}

FX3_DMMCFG_EXPECTED_UNITS = 603
FX6_DMMCFG_EXPECTED_UNITS = 556
FX3_DMMCFG_EXPECTED_RULES = 290
FX6_DMMCFG_EXPECTED_RULES = 259
DMM_MAX_EXTENTS_IN_MPR_REPLY = 8  # Stage 127: 0xa8 stack buffer holds 0x18 + 8*16 = 0x98 + 0x10 trailer
DMM_VARIABLE_REPLY_TYPES: Tuple[int, ...] = (0x8020, 0x8021, 0x8022, 0x8024, 0x8026, 0x802A)

SUPPORTED_FX3_DMM_SINKS: Tuple[str, ...] = (
    "MAIN_CARD_RECORDER",
    "LIVE_VIEW_GPE_HDMI",
    "PROXY_RECORDER",
    "AUDIO_LPCM_4CH",
)

FX6_ONLY_MASKED_DMM_SINKS: Tuple[str, ...] = (
    "12G_SDI_SERIALIZER",
    "RAW_OVER_SDI",
    "DARWIN_VARIABLE_ND",
)

# ---------------------------------------------------------------------------
# Pillar 3 Constants: 6-Domain Menu Event -> ParameterControl -> FX3 CP Contract
# ---------------------------------------------------------------------------

SUPPORTED_BASE_ISOS: Tuple[int, ...] = (800, 12800)
VALID_FPS_VALUES: Tuple[float, ...] = (23.976, 24.0, 25.0, 29.97, 50.0, 59.94, 100.0, 119.88, 120.0, 240.0)
SHUTTER_ANGLE_MIN_DEG = 5.6
SHUTTER_ANGLE_MAX_DEG = 360.0
WB_KELVIN_MIN = 2000
WB_KELVIN_MAX = 15000
WB_TINT_MIN = -99
WB_TINT_MAX = 99
SUPPORTED_LOOK_PROFILES: Tuple[str, ...] = (
    "SLOG3_SGAMUT3_CINE",
    "SLOG3_SGAMUT3",
    "S_CINETONE",
    "ITU709",
    "709_800PCT",
    "HLG",
    "USER_CUBE_MLUT",
)
SUPPORTED_MEDIA_SLOTS: Tuple[str, ...] = ("SLOT_A", "SLOT_B", "SIMUL", "RELAY", "SORT")
SUPPORTED_REC_FORMATS: Tuple[str, ...] = ("XAVC_S_I_4K", "XAVC_S_4K", "XAVC_HS_4K", "XAVC_S_HD", "HDMI_RAW16")
UNSUPPORTED_FX6_CP_MODES: Tuple[str, ...] = ("OPEN_GATE_5016X3344", "X_OCN_LT", "SDI_12G_OUT", "DARWIN_AUTO_ND")

# ---------------------------------------------------------------------------
# Pillar 4 Constants: osal_uipc Bounds, Callback Order & Record Lock Safety
# ---------------------------------------------------------------------------

FIXED_AREA_TABLE: Dict[int, Tuple[int, int]] = {
    # area_type -> (offset_from_base, byte_length) per stage107
    0: (0x0200, 0x8000),
    1: (0x8200, 0x0400),
    2: (0x0000, 0x0200),
    3: (0x8600, 0x0400),
    4: (0x8A00, 0x0400),
}
FIXED_AREA_TOTAL_BYTES = 0x8E00

UIPC_MPR_SRC_ID = 0x80C70047
UIPC_AV_DST_QUEUE_ID = 0x8055001F
UIPC_MSG_HEADER_BYTES = 24
UIPC_MSG_TAIL_BYTES = 4
UIPC_MSG_EXTRA_RESERVE_BYTES = 40
UIPC_DATAFLOW_ASYNC_CAP_BYTES = 384
UIPC_MAX_IOCTL_OP = 16
UIPC_CMD_STRUCT_BYTES = 56
UIPC_OPEN_PARAM_BYTES = 98
UIPC_START_PARAM_BYTES = 128
UIPC_ENC_OPEN_PARAM_BYTES = 152
UIPC_REPLY_ENVELOPE_BYTES = 48
UIPC_EXEC_TASK_DESC_BYTES = 0x8EA0  # 36,512 B
UIPC_CALLBACK_REC_POOL_BYTES = 384  # 4 * 0x60 B
UIPC_MOVIE_REC_STATUS_BYTES = 136
UIPC_MOVIE_REC_STATUS_HEADER_U32 = 0x53

VOLATILE_STAGING_PREFIXES_P140: Tuple[str, ...] = ("/tmp/", "ram://", "ramdisk://", "mem://")
FORBIDDEN_PERSISTENT_EMMC_RE_P140 = re.compile(
    r"(^/dev/(nflash|cnflash|mmcblk0)|Backup\.bin|psd\.bin|defdet\.bin|cpapp-b\.bin|loader_nor\.bin|^p[0-9]+:)",
    re.IGNORECASE,
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ElfAbiSummary:
    library_name: str
    body_label: str
    source_mode: str
    file_bytes: int
    export_count: int
    import_count: int
    dt_needed: Tuple[str, ...]
    has_libsecvlt_dep: bool


@dataclass(frozen=True)
class LibmprShimEvalResult:
    valid: bool
    status: str  # "PASS_THROUGH_COMPATIBLE", "LD_PRELOAD_SHIM_REQUIRED", "BLOCKED_STRUCT_ABI_MISMATCH"
    symbol_name: str
    resolution_kind: str
    shim_interceptor_needed: bool
    struct_isolation_required: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar1LibmprAbiDiffReport:
    passed: bool
    fx3_libmpr: ElfAbiSummary
    fx6_libmpr: ElfAbiSummary
    fx3_im_elf: ElfAbiSummary
    fx6_im_elf: ElfAbiSummary
    shared_export_count: int
    fx3_only_export_count: int
    fx6_only_export_count: int
    core_lifecycle_symbols_present_count: int
    fx6_appfw_mpr_import_count: int
    fx6_appfw_passthrough_count: int
    fx6_appfw_shim_required_symbols: Tuple[str, ...]
    parameter_control_fx3_count: int
    parameter_control_fx6_count: int
    libosal_uipc_exports_identical: bool
    g_videoparamcomb_bytes_fx3: int
    g_videoparamcomb_bytes_fx6: int
    s_movierecinfo_bytes_fx3: int
    s_movierecinfo_bytes_fx6: int
    direct_struct_dereference_blocked: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class DmmCfgSummary:
    body_label: str
    source_mode: str
    file_bytes: int
    consumed_bytes: int
    roots_count: int
    rules_count: int
    units_count: int
    max_extents_per_unit: int
    target_20_units_present: int
    target_units_max_extent: int
    version_ascii: str


@dataclass(frozen=True)
class DmmSinkEvalResult:
    valid: bool
    status: str
    sink_name: str
    dmm_mode: int
    extent_count: int
    reply_bytes: int
    masked_to_stub: bool
    cp_pool_request_issued: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar2DmmTopologyReport:
    passed: bool
    fx3_dmmcfg: DmmCfgSummary
    fx6_dmmcfg: DmmCfgSummary
    shared_unit_count: int
    fx3_only_unit_count: int
    fx6_only_unit_count: int
    mode_row_counts_verified: Dict[str, int]
    supported_fx3_sinks: Tuple[str, ...]
    masked_fx6_only_sinks: Tuple[str, ...]
    sample_sink_evals: Tuple[DmmSinkEvalResult, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class MenuToCpBindingEvalResult:
    valid: bool
    status: str
    domain: str
    menu_event: str
    cp_payload: Dict[str, object]
    parameter_control_bytes: int
    mech_shutter_actuations: int
    gpio_faults: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar3MenuCpBindingReport:
    passed: bool
    fx3_appfw_marker_hits: int
    fx6_appfw_marker_hits: int
    domains_verified_count: int
    domain_bindings: Tuple[MenuToCpBindingEvalResult, ...]
    unsupported_modes_blocked: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class UipcQueueSafetyEvalResult:
    valid: bool
    status: str
    area_type: int
    payload_bytes: int
    alloc_bytes: int
    uses_virtual_domain_ptr: bool
    copied_before_free: bool
    rwlock_paired: bool
    close_counter_before: int
    close_counter_after: int
    codec_close_executed: bool
    rsv_corruption_prevented: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Phase140WriteGuardResult:
    valid: bool
    status: str
    target_path: str
    volatile_ram_staged: bool
    persistent_write_blocked: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Pillar4UipcRecordLockReport:
    passed: bool
    fx3_osal_ko_bytes: int
    fx6_osal_ko_bytes: int
    fixed_area_total_bytes: int
    dataflow_async_cap_bytes: int
    exec_task_desc_bytes: int
    movie_rec_status_bytes: int
    sample_queue_evals: Tuple[UipcQueueSafetyEvalResult, ...]
    volatile_guard_ok: Phase140WriteGuardResult
    forbidden_guard_blocked: Phase140WriteGuardResult
    persistent_emmc_writes_authorized: bool
    emmc_mutation_bytes: int
    calibration_mutation_bytes: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealhwMprDmmRecPipelineBridgeReport:
    schema_version: str
    phase_version: str
    mode: str
    all_checks_passed: bool
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    donor_file_sizes: Dict[str, int]
    pillar1_libmpr_abi_diff: Pillar1LibmprAbiDiffReport
    pillar2_dmm_topology: Pillar2DmmTopologyReport
    pillar3_menu_cp_binding: Pillar3MenuCpBindingReport
    pillar4_uipc_record_lock: Pillar4UipcRecordLockReport
    report_sha256: str
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Strictly Read-Only Binary Helpers (os.O_RDONLY + mmap.ACCESS_READ)
# ---------------------------------------------------------------------------


def _read_bytes_rdonly_mmap(path: Path) -> bytes:
    """Strictly open a donor file via `os.O_RDONLY` + `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        if st.st_size == 0:
            return b""
        mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        try:
            return bytes(mm)
        finally:
            mm.close()
    finally:
        os.close(fd)


def _scan_markers_rdonly(path: Path, needles: Sequence[bytes]) -> Tuple[int, Dict[str, bool]]:
    """Fast C-level `mmap.find` probe strictly using `os.O_RDONLY` + `mmap.ACCESS_READ`."""
    fd = os.open(str(path), os.O_RDONLY)
    try:
        st = os.fstat(fd)
        sz = st.st_size
        if sz == 0:
            return 0, {n.decode("ascii", errors="replace"): False for n in needles}
        mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        try:
            ranges: List[Tuple[int, int]] = []
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
                                if sh_type == 8:  # SHT_NOBITS
                                    continue
                                _, sec_off, sec_sz = struct.unpack_from("<QQQ", mm, off + 16)
                                if sec_off + sec_sz <= sz and sh_name < len(shstr):
                                    end_n = shstr.find(b"\x00", sh_name)
                                    sname = shstr[sh_name:end_n] if end_n != -1 else b""
                                    if sname.startswith((b".dynstr", b".rodata", b".strtab", b".modinfo")):
                                        ranges.append((sec_off, sec_off + sec_sz))
            hits: Dict[str, bool] = {}
            for n in needles:
                key = n.decode("ascii", errors="replace")
                if ranges:
                    found = any(mm.find(n, lo, hi) != -1 for lo, hi in ranges)
                    if not found:
                        found = mm.find(n) != -1
                else:
                    found = mm.find(n) != -1
                hits[key] = found
            return sz, hits
        finally:
            mm.close()
    finally:
        os.close(fd)


def _parse_elf64_fast(
    buf: bytes | mmap.mmap,
    *,
    library_name: str,
    body_label: str,
    source_mode: str,
    tracked_struct_names: Sequence[str] = (),
) -> Tuple[ElfAbiSummary, set[str], set[str], Dict[str, int]]:
    """Pure-Python fast ELF64 `.dynsym`/`.dynstr`/`.dynamic` parser (< 5 ms per .so)."""
    if len(buf) < 64 or buf[:4] != b"\x7fELF" or buf[4] != 2 or buf[5] != 1:
        raise ValueError(f"Invalid ELF64 LSB header for {library_name}")

    e_shoff, = struct.unpack_from("<Q", buf, 40)
    e_shentsize, e_shnum, _ = struct.unpack_from("<HHH", buf, 58)

    dynsym_sh: Optional[Tuple[int, int, int]] = None
    dynamic_sh: Optional[Tuple[int, int, int]] = None
    for idx in range(e_shnum):
        off = e_shoff + idx * e_shentsize
        if off + 64 > len(buf):
            break
        sh_type, = struct.unpack_from("<I", buf, off + 4)
        if sh_type == 11:  # SHT_DYNSYM
            _, d_off, d_sz, d_link = struct.unpack_from("<QQQI", buf, off + 16)
            dynsym_sh = (d_off, d_sz, d_link)
        elif sh_type == 6:  # SHT_DYNAMIC
            _, d_off, d_sz, d_link = struct.unpack_from("<QQQI", buf, off + 16)
            dynamic_sh = (d_off, d_sz, d_link)

    exports: set[str] = set()
    imports: set[str] = set()
    struct_sizes: Dict[str, int] = {}
    tracked_set = set(tracked_struct_names)

    if dynsym_sh is not None:
        d_off, d_sz, d_link = dynsym_sh
        str_hdr = e_shoff + d_link * e_shentsize
        _, s_off, s_sz = struct.unpack_from("<QQQ", buf, str_hdr + 16)
        dynstr = buf[s_off : s_off + s_sz]
        dynsym = buf[d_off : d_off + d_sz]
        for st_name, _st_info, _st_other, st_shndx, _st_val, st_size in struct.iter_unpack(
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
                if name in tracked_set:
                    struct_sizes[name] = st_size

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
            if d_tag == 1 and 0 <= d_val < len(dynstr):  # DT_NEEDED
                end = dynstr.find(b"\x00", d_val)
                if end != -1:
                    dt_needed.append(dynstr[d_val:end].decode("ascii", errors="replace"))

    summary = ElfAbiSummary(
        library_name=library_name,
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=len(buf),
        export_count=len(exports),
        import_count=len(imports),
        dt_needed=tuple(dt_needed),
        has_libsecvlt_dep="libsecvlt.so" in dt_needed,
    )
    return summary, exports, imports, struct_sizes


def _inspect_elf64_rdonly(
    path: Path,
    *,
    library_name: str,
    body_label: str,
    tracked_struct_names: Sequence[str] = (),
) -> Tuple[ElfAbiSummary, set[str], set[str], Dict[str, int]]:
    fd = os.open(str(path), os.O_RDONLY)
    try:
        mm = mmap.mmap(fd, 0, access=mmap.ACCESS_READ)
        try:
            return _parse_elf64_fast(
                mm,
                library_name=library_name,
                body_label=body_label,
                source_mode="LOCAL_DONOR_RDONLY",
                tracked_struct_names=tracked_struct_names,
            )
        finally:
            mm.close()
    finally:
        os.close(fd)


def parse_dmm_cfg_bytes(
    raw: bytes,
    *,
    body_label: str,
    source_mode: str = "LOCAL_DONOR_RDONLY",
) -> Tuple[DmmCfgSummary, Dict[int, Tuple[int, ...]]]:
    """Decode Sony `DmmCfg.bin` (roots, rules, units, 44-byte version trailer)."""
    offset = 0
    total = len(raw)

    def take(n: int) -> bytes:
        nonlocal offset
        if not 0 <= n <= total - offset:
            raise ValueError(f"DmmCfg truncated at 0x{offset:x}")
        chunk = raw[offset : offset + n]
        offset += n
        return chunk

    roots_count = 0
    rules_count = 0
    for phase, limit in (("roots", 2), ("rules", 1024)):
        cnt = 0
        for _ in range(limit + 1):
            hdr = take(0x50)
            kind, _selector = struct.unpack_from("<II", hdr, 8)
            if kind == 0xFFFFFFFF:
                break
            for _ in range(0xC01):
                row = take(0x14)
                vals = struct.unpack("<5I", row)
                if vals[2] == 0xFFFFFFFF:
                    break
            else:
                raise ValueError(f"DmmCfg row terminator missing in {phase}")
            cnt += 1
        else:
            raise ValueError(f"DmmCfg group terminator missing in {phase}")
        if phase == "roots":
            roots_count = cnt
        else:
            rules_count = cnt

    units_extents: Dict[int, Tuple[int, ...]] = {}
    for _ in range(0x401):
        uhdr = take(8)
        unit_type, _attr = struct.unpack("<II", uhdr)
        if unit_type == 0xFFFFFFFF:
            break
        refs: List[int] = []
        for _ in range(0xC01):
            val, = struct.unpack("<I", take(4))
            if val == 0xFFFFFFFF:
                break
            refs.append(val)
        else:
            raise ValueError("DmmCfg unit extent terminator missing")
        if unit_type in units_extents:
            raise ValueError(f"Duplicate DmmCfg unit_type {unit_type}")
        units_extents[unit_type] = tuple(refs)
    else:
        raise ValueError("DmmCfg unit table terminator missing")

    version_bytes = take(44)
    if offset != total:
        raise ValueError(f"Unexpected trailing DmmCfg bytes: {total - offset}")

    version_ascii = version_bytes.rstrip(b"\x00").lstrip(b"\x00").decode("ascii", errors="replace")
    max_ext = max((len(v) for v in units_extents.values()), default=0)
    target_hits = [units_extents[u] for u in TARGET_MAIN_DMM_UNIT_IDS if u in units_extents]
    target_max = max((len(v) for v in target_hits), default=0)

    summary = DmmCfgSummary(
        body_label=body_label,
        source_mode=source_mode,
        file_bytes=total,
        consumed_bytes=offset,
        roots_count=roots_count,
        rules_count=rules_count,
        units_count=len(units_extents),
        max_extents_per_unit=max_ext,
        target_20_units_present=len(target_hits),
        target_units_max_extent=target_max,
        version_ascii=version_ascii,
    )
    return summary, units_extents


# ---------------------------------------------------------------------------
# Clean-Room Fixture Builders (Zero Proprietary Files Required)
# ---------------------------------------------------------------------------


def _build_synthetic_elf64(
    *,
    exports: Sequence[Tuple[str, int]],
    imports: Sequence[str],
    dt_needed: Sequence[str],
) -> bytes:
    """Build a valid minimal ELF64 AArch64 ET_DYN binary parseable by `_parse_elf64_fast`."""
    dynstr = bytearray(b"\x00")
    str_offsets: Dict[str, int] = {}

    def intern(s: str) -> int:
        if s not in str_offsets:
            str_offsets[s] = len(dynstr)
            dynstr.extend(s.encode("ascii") + b"\x00")
        return str_offsets[s]

    for s in dt_needed:
        intern(s)
    for s, _ in exports:
        intern(s)
    for s in imports:
        intern(s)

    dynsym = bytearray(24)  # STN_UNDEF
    for name, sz in exports:
        dynsym.extend(struct.pack("<IBBHQQ", intern(name), 0x12, 0, 1, 0x1000, sz))
    for name in imports:
        dynsym.extend(struct.pack("<IBBHQQ", intern(name), 0x10, 0, 0, 0, 0))

    dynamic = bytearray()
    for dep in dt_needed:
        dynamic.extend(struct.pack("<Qq", 1, intern(dep)))  # DT_NEEDED
    dynamic.extend(struct.pack("<Qq", 0, 0))  # DT_NULL

    # Layout: 64B ELF header | dynstr | dynsym | dynamic | 4 section headers (NULL, dynstr, dynsym, dynamic)
    off_dynstr = 64
    off_dynsym = off_dynstr + len(dynstr)
    off_dynamic = off_dynsym + len(dynsym)
    e_shoff = off_dynamic + len(dynamic)

    ehdr = bytearray(64)
    ehdr[0:16] = b"\x7fELF\x02\x01\x01\x00" + bytes(8)
    struct.pack_into("<HHIQQQIHHHHHH", ehdr, 16, 3, 183, 1, 0, 0, e_shoff, 0, 64, 0, 0, 64, 4, 0)

    sh_null = bytes(64)
    sh_dynstr = struct.pack("<IIQQQQIIQQ", 0, 3, 2, off_dynstr, off_dynstr, len(dynstr), 0, 0, 1, 0)
    sh_dynsym = struct.pack("<IIQQQQIIQQ", 0, 11, 2, off_dynsym, off_dynsym, len(dynsym), 1, 1, 8, 24)
    sh_dynamic = struct.pack("<IIQQQQIIQQ", 0, 6, 3, off_dynamic, off_dynamic, len(dynamic), 1, 0, 8, 16)

    return bytes(ehdr) + bytes(dynstr) + bytes(dynsym) + bytes(dynamic) + sh_null + sh_dynstr + sh_dynsym + sh_dynamic


def _build_synthetic_dmmcfg(
    *,
    rules_count: int,
    unit_ids: Sequence[int],
    version_str: str,
) -> bytes:
    """Build a valid synthetic `DmmCfg.bin` passing `parse_dmm_cfg_bytes`."""
    buf = bytearray()
    # 1 root group + 1 row + terminator
    hdr = bytearray(0x50)
    struct.pack_into("<II", hdr, 8, 1, 0)
    buf.extend(hdr)
    buf.extend(struct.pack("<5I", 0, 0, 100, 0, 0))
    buf.extend(struct.pack("<5I", 0, 0, 0xFFFFFFFF, 0, 0))
    term_hdr = bytearray(0x50)
    struct.pack_into("<II", term_hdr, 8, 0xFFFFFFFF, 0)
    buf.extend(term_hdr)

    # rules
    for r_idx in range(rules_count):
        rh = bytearray(0x50)
        struct.pack_into("<II", rh, 8, 2, r_idx)
        buf.extend(rh)
        buf.extend(struct.pack("<5I", r_idx, 0, 100 + (r_idx % 8), 0x1000, 0))
        buf.extend(struct.pack("<5I", 0, 0, 0xFFFFFFFF, 0, 0))
    buf.extend(term_hdr)

    # units
    for idx, uid in enumerate(unit_ids):
        buf.extend(struct.pack("<II", uid, 0x10))
        # Target 20 MAIN units always carry 1 extent; non-target sentinel gets up to 8 extents
        ext_n = 1 if uid in TARGET_MAIN_DMM_UNIT_IDS else (8 if idx == 0 else 1)
        for e in range(ext_n):
            buf.extend(struct.pack("<I", 100 + e))
        buf.extend(struct.pack("<I", 0xFFFFFFFF))
    buf.extend(struct.pack("<II", 0xFFFFFFFF, 0))

    ver_b = version_str.encode("ascii")[:40]
    buf.extend(b"\x00\x00\x00\x00" + ver_b.ljust(40, b"\x00"))
    return bytes(buf)


def build_clean_room_realhw_mpr_dmm_fixtures() -> Dict[str, bytes]:
    """Build deterministic clean-room fixtures for all Phase 140 tests."""
    shared_mpr_exports = list(CORE_MPR_LIFECYCLE_SYMBOLS) + [
        "_ZN3mpr16GetMediaRemainEv",
        "_ZN3mpr15SetMovieRecTimeEv",
    ]
    fx3_mpr_exports: List[Tuple[str, int]] = [(s, 0) for s in shared_mpr_exports] + [
        (k, v) for k, v in MPR_STATE_STRUCT_SIZES_FX3.items()
    ]
    fx6_mpr_exports: List[Tuple[str, int]] = (
        [(s, 0) for s in shared_mpr_exports]
        + [(s, 0) for s in FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS]
        + [(k, v) for k, v in MPR_STATE_STRUCT_SIZES_FX6.items()]
    )

    fx3_libmpr = _build_synthetic_elf64(
        exports=fx3_mpr_exports,
        imports=["osal_valloc_msg_wait", "osal_free_msg", "osal_rcv_msg_tmo", "osal_set_msg_src"],
        dt_needed=("libexpat.so.1", "libsecvlt.so", "libpthread.so.0", "libc.so.6"),
    )
    fx6_libmpr = _build_synthetic_elf64(
        exports=fx6_mpr_exports,
        imports=["osal_valloc_msg_wait", "osal_free_msg", "osal_rcv_msg_tmo", "osal_set_msg_src"],
        dt_needed=("libexpat.so.1", "libpthread.so.0", "libc.so.6"),
    )

    fx6_appfw_elf = _build_synthetic_elf64(
        exports=[("appFw_main", 0)],
        imports=list(CORE_MPR_LIFECYCLE_SYMBOLS[:12]) + list(FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS),
        dt_needed=(),
    ) + (
        b"\x00S-Log3\x00S-Gamut3.Cine\x00S-Cinetone\x00PrepareRecStart\x00"
        b"SetMovieRecParam\x00SetLutData\x00GetMovieRecStatus\x00RecStart\x00RecStop\x00"
        b"RecClipClose\x00PRM_HAITA_FEATURE_MANAGER\x00PRM_FEATURE_MANAGER_sdi_output\x00"
        b"EID_MOVIE_REC\x00CINE_EI\x00"
    )
    fx3_appfw_elf = _build_synthetic_elf64(
        exports=[("appFw_main", 0)],
        imports=list(CORE_MPR_LIFECYCLE_SYMBOLS[:12]),
        dt_needed=("libInfraSKD.so",),
    ) + (
        b"\x00S-Log3\x00PrepareRecStart\x00SetMovieRecParam\x00SetLutData\x00"
        b"GetMovieRecStatus\x00RecStart\x00RecStop\x00PRM_HAITA_FEATURE_MANAGER\x00"
        b"EID_MOVIE_REC\x00CINE_EI\x00CineEI\x00BaseISO\x00WhiteBalance\x00"
    )

    shared_avbb_pc = [(f"_ZN14AvbbcParamCtrl16ParameterControl8SetValueEj{c}", 0) for c in "bhij"]
    fx3_avbb = _build_synthetic_elf64(exports=shared_avbb_pc, imports=[], dt_needed=("libMWF.so",))
    fx6_avbb = _build_synthetic_elf64(exports=shared_avbb_pc, imports=[], dt_needed=("libMWF.so",))

    uipc_exports = [
        ("osal_valloc_msg_wait", 0),
        ("osal_free_msg", 0),
        ("osal_rcv_msg_tmo", 0),
        ("osal_set_msg_src", 0),
        ("osal_get_msg_src", 0),
        ("osal_msg_size", 0),
    ]
    fx3_libosal = _build_synthetic_elf64(exports=uipc_exports, imports=[], dt_needed=("libc.so.6",))
    fx6_libosal = _build_synthetic_elf64(exports=uipc_exports, imports=[], dt_needed=("libc.so.6",))

    im_imports = ["Backup_read", "Backup_write", "IMDB_find_entry", "abort"]
    im_deps = ("libIMDB.so", "libbackup.so", "libosal_uipc.so", "libc.so.6")
    fx3_im = _build_synthetic_elf64(exports=[("__bss_start", 0)], imports=im_imports, dt_needed=im_deps)
    fx6_im = _build_synthetic_elf64(exports=[("__bss_start", 0)], imports=im_imports, dt_needed=im_deps)

    shared_non_target = [2000 + i for i in range(548 - len(TARGET_MAIN_DMM_UNIT_IDS))]
    fx3_only_units = [3000 + i for i in range(FX3_DMMCFG_EXPECTED_UNITS - 548)]
    fx6_only_units = [1204, 1205, 1615, 1620, 1621, 1622, 1867, 1868]
    non_target_fx3 = shared_non_target + fx3_only_units
    non_target_fx6 = shared_non_target + fx6_only_units
    fx3_dmmcfg = _build_synthetic_dmmcfg(
        rules_count=FX3_DMMCFG_EXPECTED_RULES,
        unit_ids=non_target_fx3[:1] + list(TARGET_MAIN_DMM_UNIT_IDS) + non_target_fx3[1:],
        version_str="for ilc32g12m-ipsxmp     2025/06/20 15:43:19",
    )
    fx6_dmmcfg = _build_synthetic_dmmcfg(
        rules_count=FX6_DMMCFG_EXPECTED_RULES,
        unit_ids=non_target_fx6[:1] + list(TARGET_MAIN_DMM_UNIT_IDS) + non_target_fx6[1:],
        version_str="for ilc32g12m-ipsxmp     2025/10/02 12:16:04",
    )

    osal_ko = b"\x7fELF_SYNTH_OSAL_UIPC_KO\x00osal_uipc\x00osal_valloc_msg_wait\x00osal_free_msg\x00uipc\x00"
    return {
        "fx3_libmpr": fx3_libmpr,
        "fx6_libmpr": fx6_libmpr,
        "fx3_appfw": fx3_appfw_elf,
        "fx6_appfw": fx6_appfw_elf,
        "fx3_dmmcfg": fx3_dmmcfg,
        "fx6_dmmcfg": fx6_dmmcfg,
        "fx3_osal_ko": osal_ko,
        "fx6_osal_ko": osal_ko + b"\x00",
        "fx3_libosal": fx3_libosal,
        "fx6_libosal": fx6_libosal,
        "fx3_avbb": fx3_avbb,
        "fx6_avbb": fx6_avbb,
        "fx3_im": fx3_im,
        "fx6_im": fx6_im,
    }


# ---------------------------------------------------------------------------
# Public Evaluators (Positive & Negative Unit Test Surfaces)
# ---------------------------------------------------------------------------


def evaluate_libmpr_shim_and_abi_compat(
    *,
    symbol_name: str,
    fx3_exports: Sequence[str] = CORE_MPR_LIFECYCLE_SYMBOLS,
    fx6_shim_symbols: Sequence[str] = FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS,
    direct_struct_deref_attempted: bool = False,
) -> LibmprShimEvalResult:
    """Classify FX6 `appFw.so` -> Stock FX3 `libmpr.so` ABI compatibility & shim needs."""
    errors: List[str] = []
    if direct_struct_deref_attempted:
        errors.append(
            f"BLOCKED_STRUCT_ABI_MISMATCH: Direct dereference of {symbol_name!r} forbidden "
            f"(g_videoParamComb 312B vs 480B, s_movieRecInfo 3144B vs 5248B)"
        )
        return LibmprShimEvalResult(
            valid=False,
            status="BLOCKED_STRUCT_ABI_MISMATCH",
            symbol_name=symbol_name,
            resolution_kind="DIRECT_STRUCT_ABI_VIOLATION",
            shim_interceptor_needed=True,
            struct_isolation_required=True,
            errors=tuple(errors),
        )

    if symbol_name in fx3_exports:
        return LibmprShimEvalResult(
            valid=True,
            status="PASS_THROUGH_COMPATIBLE",
            symbol_name=symbol_name,
            resolution_kind="STOCK_FX3_LIBMPR_EXPORT",
            shim_interceptor_needed=False,
            struct_isolation_required=False,
            errors=(),
        )

    if symbol_name in fx6_shim_symbols:
        return LibmprShimEvalResult(
            valid=True,
            status="LD_PRELOAD_SHIM_REQUIRED",
            symbol_name=symbol_name,
            resolution_kind="STAGE_B_LD_PRELOAD_SHIM",
            shim_interceptor_needed=True,
            struct_isolation_required=True,
            errors=(),
        )

    errors.append(f"BLOCKED_UNRESOLVED_MPR_SYMBOL: {symbol_name!r} has neither FX3 export nor Stage-B shim")
    return LibmprShimEvalResult(
        valid=False,
        status="BLOCKED_UNRESOLVED_MPR_SYMBOL",
        symbol_name=symbol_name,
        resolution_kind="UNRESOLVED",
        shim_interceptor_needed=False,
        struct_isolation_required=False,
        errors=tuple(errors),
    )


def evaluate_dmm_sink_topology_and_pool_request(
    *,
    sink_name: str,
    dmm_mode: int = 21,
    extent_count: int = 1,
    reply_type: int = 0x8020,
    mask_fx6_only_sinks: bool = True,
) -> DmmSinkEvalResult:
    """Validate DMM sink routing and stage127/128 bounded reply geometry (1..8 extents)."""
    sink = sink_name.strip().upper()
    errors: List[str] = []
    if reply_type not in DMM_VARIABLE_REPLY_TYPES:
        errors.append(f"BLOCKED_INVALID_DMM_REPLY_TYPE: 0x{reply_type:04x}")
    if extent_count < 1 or extent_count > DMM_MAX_EXTENTS_IN_MPR_REPLY:
        errors.append(
            f"BLOCKED_DMM_EXTENT_OVERFLOW: extent_count={extent_count} exceeds GetDmmExtList 0xa8 cap (1..8)"
        )
    reply_bytes = 0x18 + 16 * max(0, extent_count)

    if sink in FX6_ONLY_MASKED_DMM_SINKS:
        if not mask_fx6_only_sinks:
            errors.append(
                f"BLOCKED_UNMASKED_FX6_ONLY_DMM_SINK: {sink} would request non-existent pool from Stock FX3 CP"
            )
            return DmmSinkEvalResult(
                valid=False,
                status="BLOCKED_UNMASKED_FX6_ONLY_DMM_SINK",
                sink_name=sink,
                dmm_mode=dmm_mode,
                extent_count=extent_count,
                reply_bytes=reply_bytes,
                masked_to_stub=False,
                cp_pool_request_issued=True,
                errors=tuple(errors),
            )
        return DmmSinkEvalResult(
            valid=len(errors) == 0,
            status="MASKED_FX6_ONLY_SINK_STUB" if not errors else errors[0].split(":", 1)[0],
            sink_name=sink,
            dmm_mode=dmm_mode,
            extent_count=extent_count,
            reply_bytes=reply_bytes,
            masked_to_stub=True,
            cp_pool_request_issued=False,
            errors=tuple(errors),
        )

    if sink not in SUPPORTED_FX3_DMM_SINKS:
        errors.append(f"BLOCKED_UNKNOWN_DMM_SINK: {sink!r}")
    if dmm_mode not in DMM_MODE_ROW_COUNTS:
        errors.append(f"BLOCKED_UNSUPPORTED_DMM_MODE: {dmm_mode}")

    status = "FX3_DMM_SINK_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return DmmSinkEvalResult(
        valid=len(errors) == 0,
        status=status,
        sink_name=sink,
        dmm_mode=dmm_mode,
        extent_count=extent_count,
        reply_bytes=reply_bytes,
        masked_to_stub=False,
        cp_pool_request_issued=len(errors) == 0,
        errors=tuple(errors),
    )


def translate_menu_event_to_cp_parameter(
    *,
    domain: str,
    params: Mapping[str, object],
) -> MenuToCpBindingEvalResult:
    """Translate an FX6 menu event across 6 shooting domains into a Stock FX3 CP ParameterControl payload."""
    dom = domain.strip().upper()
    errors: List[str] = []
    cp_payload: Dict[str, object] = {}
    menu_event = str(params.get("menu_event", f"EVENT_{dom}"))

    mode_flag = str(params.get("unsupported_mode", "")).strip().upper()
    if mode_flag in UNSUPPORTED_FX6_CP_MODES:
        errors.append(f"BLOCKED_UNSUPPORTED_FX6_HARDWARE_MODE: {mode_flag}")
        return MenuToCpBindingEvalResult(
            valid=False,
            status="BLOCKED_UNSUPPORTED_FX6_HARDWARE_MODE",
            domain=dom,
            menu_event=menu_event,
            cp_payload={},
            parameter_control_bytes=UIPC_CMD_STRUCT_BYTES,
            mech_shutter_actuations=0,
            gpio_faults=0,
            errors=tuple(errors),
        )

    if dom == "BASE_ISO":
        base_iso = int(params.get("base_iso", 800))
        ei_index = int(params.get("ei_index", base_iso))
        if base_iso not in SUPPORTED_BASE_ISOS:
            errors.append(f"BLOCKED_INVALID_BASE_ISO: {base_iso} not in {SUPPORTED_BASE_ISOS}")
        if not (200 <= ei_index <= 51200):
            errors.append(f"BLOCKED_INVALID_EI_INDEX: {ei_index}")
        gain_mode = "LOW_BASE_800" if base_iso == 800 else "HIGH_BASE_12800"
        cp_payload = {
            "imx510_dual_gain": gain_mode,
            "base_iso": base_iso,
            "ei_index": ei_index,
            "bk4_prop_id": "0x02cf1443",
            "cp_param_id": "0x1001",
        }
    elif dom == "FRAME_RATE_SQ":
        resolution = str(params.get("resolution", "4K_DCI")).upper()
        sensor_fps = float(params.get("sensor_fps", 23.976))
        project_fps = float(params.get("project_fps", 23.976))
        if resolution == "5K_OPEN_GATE":
            errors.append("BLOCKED_5K_OPEN_GATE_UNSUPPORTED_ON_FX3_CP")
        if sensor_fps <= 0.0 or sensor_fps > 240.0 or project_fps <= 0.0 or project_fps > 120.0:
            errors.append(f"BLOCKED_FPS_OUT_OF_RANGE: sensor={sensor_fps}, project={project_fps}")
        if resolution in ("4K_DCI", "QFHD") and sensor_fps > 120.0:
            errors.append(f"BLOCKED_4K_OVER_120FPS: sensor_fps={sensor_fps}")
        is_sq = abs(sensor_fps - project_fps) > 0.05
        cp_payload = {
            "resolution": resolution,
            "sensor_fps": sensor_fps,
            "project_fps": project_fps,
            "sq_off_speed": is_sq,
            "audio_muted": is_sq,
            "imx510_readout_mode": "4K_120P_BIN_SKIP" if sensor_fps > 60.0 else "4K_FULL_READOUT",
        }
    elif dom == "EXPOSURE_SHUTTER_ANGLE":
        angle_deg = float(params.get("shutter_angle_deg", 180.0))
        fps = float(params.get("fps", 24.0))
        if not (SHUTTER_ANGLE_MIN_DEG <= angle_deg <= SHUTTER_ANGLE_MAX_DEG):
            errors.append(f"BLOCKED_SHUTTER_ANGLE_OUT_OF_RANGE: {angle_deg}")
        if fps <= 0.0:
            errors.append(f"BLOCKED_INVALID_FPS: {fps}")
        t_exp = (angle_deg / 360.0) / fps if fps > 0.0 else 0.0
        denom = round(1.0 / t_exp, 3) if t_exp > 0.0 else 0.0
        cp_payload = {
            "shutter_angle_deg": angle_deg,
            "fps": fps,
            "cp_exposure_sec": round(t_exp, 8),
            "cp_shutter_speed_reciprocal": denom,
            "bk4_mode_prop": "0x02cf1702",
            "bk4_val_prop": "0x02cf1704",
            "electronic_rolling_shutter": True,
        }
    elif dom == "WHITE_BALANCE":
        kelvin = int(params.get("kelvin", 5600))
        tint = int(params.get("tint", 0))
        preset = str(params.get("preset", "MEMORY_A")).upper()
        if not (WB_KELVIN_MIN <= kelvin <= WB_KELVIN_MAX):
            errors.append(f"BLOCKED_WB_KELVIN_OUT_OF_RANGE: {kelvin}")
        if not (WB_TINT_MIN <= tint <= WB_TINT_MAX):
            errors.append(f"BLOCKED_WB_TINT_OUT_OF_RANGE: {tint}")
        cp_payload = {
            "wb_preset": preset,
            "kelvin": kelvin,
            "tint_cc": tint,
            "soft_mapped_wht_bal_switch": True,
        }
    elif dom == "COLOR_LOOK_MLUT":
        look = str(params.get("look_profile", "SLOG3_SGAMUT3_CINE")).upper()
        mlut_slot = int(params.get("mlut_slot", 1))
        if look not in SUPPORTED_LOOK_PROFILES:
            errors.append(f"BLOCKED_UNKNOWN_LOOK_PROFILE: {look}")
        if not (0 <= mlut_slot <= 16):
            errors.append(f"BLOCKED_INVALID_MLUT_SLOT: {mlut_slot}")
        cp_payload = {
            "look_profile": look,
            "mlut_slot": mlut_slot,
            "mpr_set_lut_cmd": "0x0165/0x0166",
            "bk4_select_lut_prop": "0x02cf1453",
            "volatile_ram_staged": True,
        }
    elif dom == "REC_START_STOP_MEDIA":
        slot_mode = str(params.get("slot_mode", "SIMUL")).upper()
        rec_format = str(params.get("rec_format", "XAVC_S_I_4K")).upper()
        action = str(params.get("action", "REC_START")).upper()
        card_class = str(params.get("card_speed_class", "VPG400")).upper()
        if slot_mode not in SUPPORTED_MEDIA_SLOTS:
            errors.append(f"BLOCKED_INVALID_MEDIA_SLOT_MODE: {slot_mode}")
        if rec_format not in SUPPORTED_REC_FORMATS:
            errors.append(f"BLOCKED_INVALID_REC_FORMAT: {rec_format}")
        if rec_format == "XAVC_S_I_4K" and card_class in ("V30", "V60"):
            errors.append(f"BLOCKED_INSUFFICIENT_CARD_SPEED_CLASS: {card_class} for {rec_format}")
        file_format_id = 3 if rec_format == "XAVC_S_HD" else 15
        cp_payload = {
            "action": action,
            "slot_mode": slot_mode,
            "rec_format": rec_format,
            "card_speed_class": card_class,
            "mpr_sequence": ("PrepareRecStart", "RecStart", "ExecEncOpen", "ExecEncStart")
            if action == "REC_START"
            else ("RecStop", "ExecEncStop", "ExecEncClose"),
            "enc_open_file_format": file_format_id,
            "enc_open_bytes": UIPC_ENC_OPEN_PARAM_BYTES,
        }
    else:
        errors.append(f"BLOCKED_UNKNOWN_PARAMETER_DOMAIN: {dom}")

    status = f"{dom}_CP_BINDING_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return MenuToCpBindingEvalResult(
        valid=len(errors) == 0,
        status=status,
        domain=dom,
        menu_event=menu_event,
        cp_payload=cp_payload,
        parameter_control_bytes=UIPC_CMD_STRUCT_BYTES,
        mech_shutter_actuations=0,
        gpio_faults=0,
        errors=tuple(errors),
    )


def evaluate_uipc_queue_and_close_safety(
    *,
    area_type: int = 2,
    payload_bytes: int = 152,
    ioctl_op: int = 10,
    user_map_base: int = 0x70000000,
    ptr_addr: int = 0x70001000,
    addr_limit: int = 0x7FFFF000,
    uses_virtual_domain_ptr: bool = True,
    copied_before_free: bool = True,
    rwlock_paired: bool = True,
    close_counter_before: int = 1,
    decrement_flag: int = 0,
) -> UipcQueueSafetyEvalResult:
    """Audit `osal_uipc` bounds, virtual-domain pointer safety, callback copy order & close counter."""
    errors: List[str] = []

    if area_type not in FIXED_AREA_TABLE:
        errors.append(f"BLOCKED_INVALID_FIXED_AREA_TYPE: {area_type}")
    else:
        _, area_len = FIXED_AREA_TABLE[area_type]
        if payload_bytes > area_len:
            errors.append(f"BLOCKED_FIXED_AREA_OVERFLOW: {payload_bytes} > {area_len}")

    if payload_bytes < 0 or payload_bytes > UIPC_DATAFLOW_ASYNC_CAP_BYTES:
        errors.append(
            f"BLOCKED_DATAFLOW_PAYLOAD_CAP_EXCEEDED: {payload_bytes} > {UIPC_DATAFLOW_ASYNC_CAP_BYTES}"
        )

    op_num = ioctl_op & 0x7FFFFFFF
    if op_num > UIPC_MAX_IOCTL_OP:
        errors.append(f"BLOCKED_UIPC_OP_OUT_OF_RANGE: op={op_num}")
    if op_num != 16 and user_map_base == 0:
        errors.append("BLOCKED_UIPC_UNMAPPED_USER_BASE")
    if ptr_addr + 15 > addr_limit:
        errors.append(f"BLOCKED_UIPC_ADDR_LIMIT_EXCEEDED: 0x{ptr_addr+15:x} > 0x{addr_limit:x}")
    if not uses_virtual_domain_ptr:
        errors.append("BLOCKED_PHYSICAL_PTR_DOMAIN_DEREF: Must use PayloadMpr +0x28 virtual ptr, not +0x08 phys")
    if not copied_before_free:
        errors.append("BLOCKED_USE_AFTER_FREE_CALLBACK_PTR: Must copy 48B reply before osal_free_msg (0x8000000b)")
    if not rwlock_paired:
        errors.append("BLOCKED_MOVIE_RWLOCK_LEAK: GetMovieRecStatusForUpdate must pair with UnlockMovieRecStatus")

    aligned4 = (max(0, payload_bytes) + 3) & ~3
    raw_alloc = aligned4 + UIPC_MSG_HEADER_BYTES + UIPC_MSG_TAIL_BYTES + UIPC_MSG_EXTRA_RESERVE_BYTES
    alloc_bytes = (raw_alloc + 63) & ~63

    # Stage 124 ExecEncClose counter logic
    if decrement_flag == 0 and close_counter_before > 0:
        close_counter_after = close_counter_before - 1
    else:
        close_counter_after = close_counter_before
    codec_close_executed = (decrement_flag == 0) and (close_counter_after == 0)
    rsv_prevented = len(errors) == 0 and codec_close_executed

    if close_counter_after != 0 and decrement_flag == 0:
        errors.append(f"CLOSE_SKIPPED_ACTIVE_WRITER_REMAINING: counter={close_counter_after}")

    status = "UIPC_AND_RECORD_LOCK_VERIFIED" if not errors else errors[0].split(":", 1)[0]
    return UipcQueueSafetyEvalResult(
        valid=len(errors) == 0,
        status=status,
        area_type=area_type,
        payload_bytes=payload_bytes,
        alloc_bytes=alloc_bytes,
        uses_virtual_domain_ptr=uses_virtual_domain_ptr,
        copied_before_free=copied_before_free,
        rwlock_paired=rwlock_paired,
        close_counter_before=close_counter_before,
        close_counter_after=close_counter_after,
        codec_close_executed=codec_close_executed,
        rsv_corruption_prevented=rsv_prevented,
        errors=tuple(errors),
    )


def evaluate_phase140_write_guard(target_path: str) -> Phase140WriteGuardResult:
    """Enforce volatile RAM staging only and zero persistent eMMC / calibration mutations."""
    norm = target_path.strip()
    is_volatile = norm.startswith(VOLATILE_STAGING_PREFIXES_P140) and not bool(
        FORBIDDEN_PERSISTENT_EMMC_RE_P140.search(norm)
    )
    if is_volatile:
        return Phase140WriteGuardResult(
            valid=True,
            status="VOLATILE_RAM_STAGING_ALLOWED",
            target_path=norm,
            volatile_ram_staged=True,
            persistent_write_blocked=False,
            emmc_mutation_bytes=0,
            calibration_mutation_bytes=0,
            errors=(),
        )
    return Phase140WriteGuardResult(
        valid=False,
        status="BLOCKED_PERSISTENT_EMMC_OR_CALIBRATION_WRITE",
        target_path=norm,
        volatile_ram_staged=False,
        persistent_write_blocked=True,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        errors=(f"BLOCKED_PERSISTENT_EMMC_OR_CALIBRATION_WRITE: target_path={norm!r}",),
    )


# ---------------------------------------------------------------------------
# Unified Phase 140 Auditor Entrypoint
# ---------------------------------------------------------------------------


def analyze_realhw_mpr_dmm_rec_pipeline_bridge(
    *,
    clean_room: bool = False,
    repo_root: Optional[Path] = None,
) -> RealhwMprDmmRecPipelineBridgeReport:
    """Run all 4 Phase 140 pillars in Local Donor (O_RDONLY+mmap) or Clean-Room mode."""
    root = repo_root if repo_root is not None else DEFAULT_REPO_ROOT
    forced = clean_room or is_forced_clean_room()

    donor_paths: Dict[str, Optional[Path]] = {}
    if not forced:
        rel_map = {
            "fx3_libmpr": FX3_LIBMPR_P140_RELPATH,
            "fx6_libmpr": FX6_LIBMPR_P140_RELPATH,
            "fx3_appfw": FX3_APPFW_P140_RELPATH,
            "fx6_appfw": FX6_APPFW_P140_RELPATH,
            "fx3_dmmcfg": FX3_AP_DMMCFG_RELPATH,
            "fx6_dmmcfg": FX6_AP_DMMCFG_RELPATH,
            "fx3_osal_ko": FX3_OSAL_UIPC_KO_RELPATH,
            "fx6_osal_ko": FX6_OSAL_UIPC_KO_RELPATH,
            "fx3_libosal": FX3_LIBOSAL_UIPC_SO_RELPATH,
            "fx6_libosal": FX6_LIBOSAL_UIPC_SO_RELPATH,
            "fx3_avbb": FX3_LIBINFRA_AVBBC_RELPATH,
            "fx6_avbb": FX6_LIBINFRA_AVBBC_RELPATH,
            "fx3_im": FX3_IM_ELF_RELPATH,
            "fx6_im": FX6_IM_ELF_RELPATH,
        }
        donor_paths = {k: resolve_donor_file(v, repo_root=root) for k, v in rel_map.items()}

    use_local = (not forced) and bool(donor_paths) and all(p is not None for p in donor_paths.values())
    mode = "LOCAL_DONOR_VERIFIED" if use_local else "CLEAN_ROOM_SYNTHETIC"
    source_mode = "LOCAL_DONOR_RDONLY" if use_local else "SYNTHETIC_CLEAN_ROOM"

    tracked_mpr_structs = tuple(MPR_STATE_STRUCT_SIZES_FX3.keys())
    donor_sizes: Dict[str, int] = {}
    errors: List[str] = []

    appfw_markers = (
        b"S-Log3",
        b"PrepareRecStart",
        b"SetMovieRecParam",
        b"SetLutData",
        b"GetMovieRecStatus",
        b"RecStart",
        b"RecStop",
        b"PRM_HAITA_FEATURE_MANAGER",
        b"EID_MOVIE_REC",
        b"CINE_EI",
    )

    if use_local:
        p = {k: v for k, v in donor_paths.items() if v is not None}
        fx3_mpr_sum, fx3_mpr_exp, _, fx3_mpr_sz = _inspect_elf64_rdonly(
            p["fx3_libmpr"],
            library_name="libmpr.so",
            body_label="FX3_7.02",
            tracked_struct_names=tracked_mpr_structs,
        )
        fx6_mpr_sum, fx6_mpr_exp, _, fx6_mpr_sz = _inspect_elf64_rdonly(
            p["fx6_libmpr"],
            library_name="libmpr.so",
            body_label="FX6_6.01",
            tracked_struct_names=tracked_mpr_structs,
        )
        _, _, fx6_app_imp, _ = _inspect_elf64_rdonly(
            p["fx6_appfw"], library_name="appFw.so", body_label="FX6_6.01"
        )
        fx3_im_sum, _, _, _ = _inspect_elf64_rdonly(
            p["fx3_im"], library_name="im.elf", body_label="FX3_7.02"
        )
        fx6_im_sum, _, _, _ = _inspect_elf64_rdonly(
            p["fx6_im"], library_name="im.elf", body_label="FX6_6.01"
        )
        _, fx3_avbb_exp, _, _ = _inspect_elf64_rdonly(
            p["fx3_avbb"], library_name="libInfraAvbbc.so", body_label="FX3_7.02"
        )
        _, fx6_avbb_exp, _, _ = _inspect_elf64_rdonly(
            p["fx6_avbb"], library_name="libInfraAvbbc.so", body_label="FX6_6.01"
        )
        _, fx3_osal_exp, _, _ = _inspect_elf64_rdonly(
            p["fx3_libosal"], library_name="libosal_uipc.so", body_label="FX3_7.02"
        )
        _, fx6_osal_exp, _, _ = _inspect_elf64_rdonly(
            p["fx6_libosal"], library_name="libosal_uipc.so", body_label="FX6_6.01"
        )
        fx3_dmm_raw = _read_bytes_rdonly_mmap(p["fx3_dmmcfg"])
        fx6_dmm_raw = _read_bytes_rdonly_mmap(p["fx6_dmmcfg"])
        fx3_app_sz, fx3_app_hits = _scan_markers_rdonly(p["fx3_appfw"], appfw_markers)
        fx6_app_sz, fx6_app_hits = _scan_markers_rdonly(p["fx6_appfw"], appfw_markers)
        fx3_ko_sz, fx3_ko_hits = _scan_markers_rdonly(p["fx3_osal_ko"], (b"osal_uipc", b"osal_valloc_msg_wait", b"osal_free_msg"))
        fx6_ko_sz, fx6_ko_hits = _scan_markers_rdonly(p["fx6_osal_ko"], (b"osal_uipc", b"osal_valloc_msg_wait", b"osal_free_msg"))

        for k, path_obj in p.items():
            donor_sizes[k] = path_obj.stat().st_size
    else:
        fx = build_clean_room_realhw_mpr_dmm_fixtures()
        fx3_mpr_sum, fx3_mpr_exp, _, fx3_mpr_sz = _parse_elf64_fast(
            fx["fx3_libmpr"],
            library_name="libmpr.so",
            body_label="FX3_7.02",
            source_mode=source_mode,
            tracked_struct_names=tracked_mpr_structs,
        )
        fx6_mpr_sum, fx6_mpr_exp, _, fx6_mpr_sz = _parse_elf64_fast(
            fx["fx6_libmpr"],
            library_name="libmpr.so",
            body_label="FX6_6.01",
            source_mode=source_mode,
            tracked_struct_names=tracked_mpr_structs,
        )
        _, _, fx6_app_imp, _ = _parse_elf64_fast(
            fx["fx6_appfw"],
            library_name="appFw.so",
            body_label="FX6_6.01",
            source_mode=source_mode,
        )
        fx3_im_sum, _, _, _ = _parse_elf64_fast(
            fx["fx3_im"], library_name="im.elf", body_label="FX3_7.02", source_mode=source_mode
        )
        fx6_im_sum, _, _, _ = _parse_elf64_fast(
            fx["fx6_im"], library_name="im.elf", body_label="FX6_6.01", source_mode=source_mode
        )
        _, fx3_avbb_exp, _, _ = _parse_elf64_fast(
            fx["fx3_avbb"], library_name="libInfraAvbbc.so", body_label="FX3_7.02", source_mode=source_mode
        )
        _, fx6_avbb_exp, _, _ = _parse_elf64_fast(
            fx["fx6_avbb"], library_name="libInfraAvbbc.so", body_label="FX6_6.01", source_mode=source_mode
        )
        _, fx3_osal_exp, _, _ = _parse_elf64_fast(
            fx["fx3_libosal"], library_name="libosal_uipc.so", body_label="FX3_7.02", source_mode=source_mode
        )
        _, fx6_osal_exp, _, _ = _parse_elf64_fast(
            fx["fx6_libosal"], library_name="libosal_uipc.so", body_label="FX6_6.01", source_mode=source_mode
        )
        fx3_dmm_raw = fx["fx3_dmmcfg"]
        fx6_dmm_raw = fx["fx6_dmmcfg"]
        fx3_app_sz = len(fx["fx3_appfw"])
        fx6_app_sz = len(fx["fx6_appfw"])
        fx3_app_hits = {m.decode("ascii"): (m in fx["fx3_appfw"]) for m in appfw_markers}
        fx6_app_hits = {m.decode("ascii"): (m in fx["fx6_appfw"]) for m in appfw_markers}
        fx3_ko_sz = len(fx["fx3_osal_ko"])
        fx6_ko_sz = len(fx["fx6_osal_ko"])
        fx3_ko_hits = {"osal_uipc": b"osal_uipc" in fx["fx3_osal_ko"], "osal_valloc_msg_wait": b"osal_valloc_msg_wait" in fx["fx3_osal_ko"], "osal_free_msg": b"osal_free_msg" in fx["fx3_osal_ko"]}
        fx6_ko_hits = {"osal_uipc": b"osal_uipc" in fx["fx6_osal_ko"], "osal_valloc_msg_wait": b"osal_valloc_msg_wait" in fx["fx6_osal_ko"], "osal_free_msg": b"osal_free_msg" in fx["fx6_osal_ko"]}
        for k, buf in fx.items():
            donor_sizes[k] = len(buf)

    # ---- Pillar 1: libmpr.so / libInfraAvbbc.so / im.elf ABI Diff ----
    p1_errors: List[str] = []
    shared_mpr = fx3_mpr_exp & fx6_mpr_exp
    fx3_only_mpr = fx3_mpr_exp - fx6_mpr_exp
    fx6_only_mpr = fx6_mpr_exp - fx3_mpr_exp
    core_present = sum(1 for sym in CORE_MPR_LIFECYCLE_SYMBOLS if sym in shared_mpr)
    if core_present != len(CORE_MPR_LIFECYCLE_SYMBOLS):
        p1_errors.append(
            f"Missing core MPR lifecycle symbols: {core_present}/{len(CORE_MPR_LIFECYCLE_SYMBOLS)}"
        )

    fx6_app_mpr_needed = fx6_app_imp & fx6_mpr_exp
    fx6_app_passthrough = fx6_app_mpr_needed & fx3_mpr_exp
    fx6_app_missing_shim = tuple(sorted(fx6_app_mpr_needed - fx3_mpr_exp))
    if fx6_app_missing_shim != tuple(sorted(FX6_APPFW_SHIM_REQUIRED_MPR_SYMBOLS)):
        p1_errors.append(
            f"Unexpected shim symbol list mismatch: got {len(fx6_app_missing_shim)} symbols"
        )

    pc_fx3 = sum(1 for s in fx3_avbb_exp if "ParameterControl" in s)
    pc_fx6 = sum(1 for s in fx6_avbb_exp if "ParameterControl" in s)
    if pc_fx3 == 0 or pc_fx6 == 0:
        p1_errors.append("Missing ParameterControl exports in libInfraAvbbc.so")

    osal_identical = fx3_osal_exp == fx6_osal_exp and len(fx3_osal_exp) > 0
    if not osal_identical:
        p1_errors.append("libosal_uipc.so export parity failed")

    vpc3 = fx3_mpr_sz.get("_ZN3mpr16g_videoParamCombE", 0)
    vpc6 = fx6_mpr_sz.get("_ZN3mpr16g_videoParamCombE", 0)
    mri3 = fx3_mpr_sz.get("_ZN3mpr14s_movieRecInfoE", 0)
    mri6 = fx6_mpr_sz.get("_ZN3mpr14s_movieRecInfoE", 0)
    if vpc3 != 312 or vpc6 != 480 or mri3 != 3144 or mri6 != 5248:
        p1_errors.append(f"Unexpected MPR struct sizes: vpc=({vpc3},{vpc6}) mri=({mri3},{mri6})")

    # Verify im.elf carries libosal_uipc.so + libbackup.so + libIMDB.so
    for im_sum in (fx3_im_sum, fx6_im_sum):
        if "libosal_uipc.so" not in im_sum.dt_needed or "libbackup.so" not in im_sum.dt_needed:
            p1_errors.append(f"im.elf missing required DT_NEEDED in {im_sum.body_label}")

    p1_report = Pillar1LibmprAbiDiffReport(
        passed=len(p1_errors) == 0,
        fx3_libmpr=fx3_mpr_sum,
        fx6_libmpr=fx6_mpr_sum,
        fx3_im_elf=fx3_im_sum,
        fx6_im_elf=fx6_im_sum,
        shared_export_count=len(shared_mpr),
        fx3_only_export_count=len(fx3_only_mpr),
        fx6_only_export_count=len(fx6_only_mpr),
        core_lifecycle_symbols_present_count=core_present,
        fx6_appfw_mpr_import_count=len(fx6_app_mpr_needed),
        fx6_appfw_passthrough_count=len(fx6_app_passthrough),
        fx6_appfw_shim_required_symbols=fx6_app_missing_shim,
        parameter_control_fx3_count=pc_fx3,
        parameter_control_fx6_count=pc_fx6,
        libosal_uipc_exports_identical=osal_identical,
        g_videoparamcomb_bytes_fx3=vpc3,
        g_videoparamcomb_bytes_fx6=vpc6,
        s_movierecinfo_bytes_fx3=mri3,
        s_movierecinfo_bytes_fx6=mri6,
        direct_struct_dereference_blocked=True,
        errors=tuple(p1_errors),
    )

    # ---- Pillar 2: DmmCfg.bin Node Topology & Unsupported Sink Mask ----
    p2_errors: List[str] = []
    fx3_dmm_sum, fx3_dmm_units = parse_dmm_cfg_bytes(
        fx3_dmm_raw, body_label="FX3_7.02_AP", source_mode=source_mode
    )
    fx6_dmm_sum, fx6_dmm_units = parse_dmm_cfg_bytes(
        fx6_dmm_raw, body_label="FX6_6.01_AP", source_mode=source_mode
    )
    if fx3_dmm_sum.units_count != FX3_DMMCFG_EXPECTED_UNITS or fx6_dmm_sum.units_count != FX6_DMMCFG_EXPECTED_UNITS:
        p2_errors.append(
            f"Unexpected DmmCfg unit counts: fx3={fx3_dmm_sum.units_count}, fx6={fx6_dmm_sum.units_count}"
        )
    if fx3_dmm_sum.target_20_units_present != 20 or fx6_dmm_sum.target_20_units_present != 20:
        p2_errors.append("Missing target MAIN DMM units in FX3/FX6 DmmCfg.bin")
    if fx3_dmm_sum.max_extents_per_unit > DMM_MAX_EXTENTS_IN_MPR_REPLY or fx6_dmm_sum.max_extents_per_unit > DMM_MAX_EXTENTS_IN_MPR_REPLY:
        p2_errors.append("DmmCfg extent count exceeds MPR 0xa8 reply safety bound (8)")

    fx3_uid_set = set(fx3_dmm_units.keys())
    fx6_uid_set = set(fx6_dmm_units.keys())
    sink_evals = (
        evaluate_dmm_sink_topology_and_pool_request(sink_name="MAIN_CARD_RECORDER", dmm_mode=21, extent_count=1),
        evaluate_dmm_sink_topology_and_pool_request(sink_name="LIVE_VIEW_GPE_HDMI", dmm_mode=25, extent_count=1),
        evaluate_dmm_sink_topology_and_pool_request(sink_name="PROXY_RECORDER", dmm_mode=31, extent_count=1),
        evaluate_dmm_sink_topology_and_pool_request(sink_name="AUDIO_LPCM_4CH", dmm_mode=32, extent_count=1),
        evaluate_dmm_sink_topology_and_pool_request(sink_name="12G_SDI_SERIALIZER", dmm_mode=21, extent_count=1, mask_fx6_only_sinks=True),
        evaluate_dmm_sink_topology_and_pool_request(sink_name="RAW_OVER_SDI", dmm_mode=21, extent_count=1, mask_fx6_only_sinks=True),
        evaluate_dmm_sink_topology_and_pool_request(sink_name="DARWIN_VARIABLE_ND", dmm_mode=21, extent_count=1, mask_fx6_only_sinks=True),
    )
    for se in sink_evals:
        if not se.valid:
            p2_errors.extend(se.errors)

    p2_report = Pillar2DmmTopologyReport(
        passed=len(p2_errors) == 0,
        fx3_dmmcfg=fx3_dmm_sum,
        fx6_dmmcfg=fx6_dmm_sum,
        shared_unit_count=len(fx3_uid_set & fx6_uid_set),
        fx3_only_unit_count=len(fx3_uid_set - fx6_uid_set),
        fx6_only_unit_count=len(fx6_uid_set - fx3_uid_set),
        mode_row_counts_verified={str(k): v for k, v in DMM_MODE_ROW_COUNTS.items()},
        supported_fx3_sinks=SUPPORTED_FX3_DMM_SINKS,
        masked_fx6_only_sinks=FX6_ONLY_MASKED_DMM_SINKS,
        sample_sink_evals=sink_evals,
        errors=tuple(p2_errors),
    )

    # ---- Pillar 3: Menu Event -> ParameterControl -> FX3 CP Binding ----
    p3_errors: List[str] = []
    fx3_hit_cnt = sum(1 for v in fx3_app_hits.values() if v)
    fx6_hit_cnt = sum(1 for v in fx6_app_hits.values() if v)
    if fx3_hit_cnt < len(appfw_markers) or fx6_hit_cnt < len(appfw_markers):
        p3_errors.append(f"Incomplete appFw marker coverage: fx3={fx3_hit_cnt}, fx6={fx6_hit_cnt}")
    if fx3_app_sz == 0 or fx6_app_sz == 0:
        p3_errors.append("appFw binary size must be > 0")

    bindings = (
        translate_menu_event_to_cp_parameter(
            domain="BASE_ISO",
            params={"menu_event": "EVENT_BASE_ISO_HIGH_12800", "base_iso": 12800, "ei_index": 12800},
        ),
        translate_menu_event_to_cp_parameter(
            domain="FRAME_RATE_SQ",
            params={"menu_event": "EVENT_SQ_4K_120P", "resolution": "4K_DCI", "sensor_fps": 119.88, "project_fps": 23.976},
        ),
        translate_menu_event_to_cp_parameter(
            domain="EXPOSURE_SHUTTER_ANGLE",
            params={"menu_event": "EVENT_SHUTTER_ANGLE_180_24P", "shutter_angle_deg": 180.0, "fps": 24.0},
        ),
        translate_menu_event_to_cp_parameter(
            domain="WHITE_BALANCE",
            params={"menu_event": "EVENT_WB_MEMORY_A_4300K", "preset": "MEMORY_A", "kelvin": 4300, "tint": 2},
        ),
        translate_menu_event_to_cp_parameter(
            domain="COLOR_LOOK_MLUT",
            params={"menu_event": "EVENT_LOOK_SLOG3_MLUT", "look_profile": "SLOG3_SGAMUT3_CINE", "mlut_slot": 1},
        ),
        translate_menu_event_to_cp_parameter(
            domain="REC_START_STOP_MEDIA",
            params={"menu_event": "EVENT_REC_START_SIMUL_CFEX_A_B", "action": "REC_START", "slot_mode": "SIMUL", "rec_format": "XAVC_S_I_4K", "card_speed_class": "VPG400"},
        ),
    )
    for b in bindings:
        if not b.valid or b.mech_shutter_actuations != 0 or b.gpio_faults != 0:
            p3_errors.extend(b.errors)

    p3_report = Pillar3MenuCpBindingReport(
        passed=len(p3_errors) == 0,
        fx3_appfw_marker_hits=fx3_hit_cnt,
        fx6_appfw_marker_hits=fx6_hit_cnt,
        domains_verified_count=len(bindings),
        domain_bindings=bindings,
        unsupported_modes_blocked=UNSUPPORTED_FX6_CP_MODES,
        errors=tuple(p3_errors),
    )

    # ---- Pillar 4: UIPC Queue Guard & Record Lock Safety ----
    p4_errors: List[str] = []
    if not (all(fx3_ko_hits.values()) and all(fx6_ko_hits.values())):
        p4_errors.append("osal_uipc.ko marker verification failed")

    q_evals = (
        evaluate_uipc_queue_and_close_safety(
            area_type=2,
            payload_bytes=152,
            ioctl_op=10,
            uses_virtual_domain_ptr=True,
            copied_before_free=True,
            rwlock_paired=True,
            close_counter_before=1,
            decrement_flag=0,
        ),
        evaluate_uipc_queue_and_close_safety(
            area_type=0,
            payload_bytes=384,
            ioctl_op=0x8000000B,
            uses_virtual_domain_ptr=True,
            copied_before_free=True,
            rwlock_paired=True,
            close_counter_before=0,
            decrement_flag=0,
        ),
    )
    for qe in q_evals:
        if not qe.valid:
            p4_errors.extend(qe.errors)

    vol_guard = evaluate_phase140_write_guard("/tmp/stage_b/rec_pipeline_bridge_state.json")
    forb_guard = evaluate_phase140_write_guard("/dev/nflasha15/usr/lib/libmpr.so")
    if not vol_guard.valid or not forb_guard.persistent_write_blocked:
        p4_errors.append("Phase 140 write guard failed")

    p4_report = Pillar4UipcRecordLockReport(
        passed=len(p4_errors) == 0,
        fx3_osal_ko_bytes=fx3_ko_sz,
        fx6_osal_ko_bytes=fx6_ko_sz,
        fixed_area_total_bytes=FIXED_AREA_TOTAL_BYTES,
        dataflow_async_cap_bytes=UIPC_DATAFLOW_ASYNC_CAP_BYTES,
        exec_task_desc_bytes=UIPC_EXEC_TASK_DESC_BYTES,
        movie_rec_status_bytes=UIPC_MOVIE_REC_STATUS_BYTES,
        sample_queue_evals=q_evals,
        volatile_guard_ok=vol_guard,
        forbidden_guard_blocked=forb_guard,
        persistent_emmc_writes_authorized=False,
        emmc_mutation_bytes=0,
        calibration_mutation_bytes=0,
        errors=tuple(p4_errors),
    )

    all_errors = tuple(errors + p1_errors + p2_errors + p3_errors + p4_errors)
    all_passed = (
        p1_report.passed
        and p2_report.passed
        and p3_report.passed
        and p4_report.passed
        and len(all_errors) == 0
    )

    draft_dict = {
        "schema_version": PHASE_140_SCHEMA,
        "phase_version": PHASE_140_VERSION,
        "mode": mode,
        "all_checks_passed": all_passed,
        "o_rdonly_enforced": True,
        "persistent_emmc_writes_authorized": False,
        "donor_file_sizes": donor_sizes,
        "pillar1_libmpr_abi_diff": asdict(p1_report),
        "pillar2_dmm_topology": asdict(p2_report),
        "pillar3_menu_cp_binding": asdict(p3_report),
        "pillar4_uipc_record_lock": asdict(p4_report),
        "errors": list(all_errors),
    }
    digest = hashlib.sha256(
        json.dumps(draft_dict, sort_keys=True, separators=(",", ":")).encode("utf-8")
    ).hexdigest()

    return RealhwMprDmmRecPipelineBridgeReport(
        schema_version=PHASE_140_SCHEMA,
        phase_version=PHASE_140_VERSION,
        mode=mode,
        all_checks_passed=all_passed,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=False,
        donor_file_sizes=donor_sizes,
        pillar1_libmpr_abi_diff=p1_report,
        pillar2_dmm_topology=p2_report,
        pillar3_menu_cp_binding=p3_report,
        pillar4_uipc_record_lock=p4_report,
        report_sha256=digest,
        errors=all_errors,
    )


def realhw_mpr_dmm_rec_pipeline_bridge_report_to_dict(
    report: RealhwMprDmmRecPipelineBridgeReport,
) -> Dict[str, object]:
    """Convert `RealhwMprDmmRecPipelineBridgeReport` to a deterministic JSON-serializable dict."""
    return asdict(report)
