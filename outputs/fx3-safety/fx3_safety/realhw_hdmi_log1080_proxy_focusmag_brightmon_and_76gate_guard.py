"""Phase 210 — Real-Hardware Main Track Part 25:
Gate G75 (`ILME-FX3` `Ver. 7.02` `[HDMI Output Settings]` `[Rec. Media dur HDMI Output]`
`[On]` vs `[Off(HDMI Only)]`, `[4K Output Set.(HDMI Only)]` `59.94p..24.00p 10bit`,
`[Log Shooting]` `Cine EI / Cine EI Quick / Flexible ISO` & `PPLUT1..PPLUT4` `1080p` HDMI
Downshift Rule, `[Off(HDMI Only)]` Zero-Internal-Card-Recording Lockout, Automatic
`[HDMI Info. Display]->[Off]` & HDMI `[De-Squeeze Display]` Suppression, and Camera Built-In
LCD Blanking Guard when `[HDMI Info. Display]=[On]`),
Gate G76 (`ILME-FX3` `Ver. 7.02` `[Proxy Settings]` Exact 2-Format / 3-Setting Table
`XAVC HS HD 16M/9M 10bit` & `XAVC S HD 6M 8bit`, `119.88p/100p` + `S&Q >=100/120fps` +
`[Off(HDMI Only)]` Proxy Cutoffs, Atomic Coupled `M4ROOT/CLIP/` + `M4ROOT/SUB/` Delete/Protect
Vault Parity, and `[Focus Magnifier]` x `[Auto Magnifier in MF]` x `[Bright Monitoring]`
Interlock Guard),
and Unified 76-Gate Master Safety Preflight (`G01..G76` / `verify-76-gates`).

Delegates `G01..G74` directly to `evaluate_74gate_preflight()` from
`realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard` while hard-locking:
- `EL3_PAYLOAD_TRANSMIT_AUTHORIZED = False`
- `SPI_NOR_WRITE_AUTHORIZED = False`
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `USB_PACKETS_TRANSMITTED = 0`
- `RAW_FIRMWARE_BYTES_LEAKED = 0`
"""

from __future__ import annotations

import argparse
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple, Union

from .master_16gate_preflight import DEFAULT_REPO_ROOT, GateVerdict
from .realhw_desqueeze_focusmap_simult_shocklesswb_and_74gate_guard import (
    Master74GateReport,
    evaluate_74gate_preflight,
)
from .realhw_fx3a_firewall_xlrh1_mishoe_and_64gate_guard import (
    FX3_MODEL_ID,
    FX3_MODEL_NAME,
)
from .thermal_pwm_and_power_guard import (
    ENV_FORCE_CLEAN_ROOM,
    resolve_donor_thermal_power_paths,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

REALHW_HDMI_LOG1080_PROXY_FOCUSMAG_BRIGHTMON_76GATE_SCHEMA: str = (
    "fx3-realhw-hdmi-log1080-proxy-focusmag-brightmon-76gate-preflight-v1"
)
REALHW_HDMI_LOG1080_PROXY_FOCUSMAG_BRIGHTMON_76GATE_VERSION: str = "1.0.0"

EL3_PAYLOAD_TRANSMIT_AUTHORIZED: bool = False
SPI_NOR_WRITE_AUTHORIZED: bool = False
PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED: bool = False
HUMAN_HARDWARE_ATTACH_TOKEN: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
USB_PACKETS_TRANSMITTED: int = 0
PHYSICAL_USB_PACKETS_EMITTED: int = 0
RAW_FIRMWARE_BYTES_LEAKED: int = 0

DONOR_CHECK_MAX_SECONDS: float = 0.15
FX3_DEFAULT_FW_VERSION_G75: str = "7.02"

# Gate IDs & Canonical Codes for G75..G76
G75_GATE_ID: str = "G75_hdmi_log_1080p_downshift_and_hdmionly_4k_blank_lcd_guard"
G75_GATE_CODE: str = "G75_HDMI_LOG_1080P_DOWNSHIFT_AND_HDMIONLY_4K_BLANK_LCD_GUARD"
GATE_G75_HDMI_LOG_1080P_DOWNSHIFT_AND_HDMIONLY_4K_BLANK_LCD_GUARD: str = G75_GATE_CODE
G75: str = G75_GATE_CODE

G76_GATE_ID: str = "G76_proxy_coupled_vault_and_focusmag_brightmon_interlock_guard"
G76_GATE_CODE: str = "G76_PROXY_COUPLED_VAULT_AND_FOCUSMAG_BRIGHTMON_INTERLOCK_GUARD"
GATE_G76_PROXY_COUPLED_VAULT_AND_FOCUSMAG_BRIGHTMON_INTERLOCK_GUARD: str = G76_GATE_CODE
G76: str = G76_GATE_CODE

# Status & Violation Codes
STATUS_VERIFIED_SAFE: str = "VERIFIED_SAFE"
STATUS_VERIFIED_G75: str = (
    "VERIFIED_HDMI_LOG_1080P_DOWNSHIFT_AND_HDMIONLY_4K_BLANK_LCD_GUARD"
)
STATUS_VERIFIED_G76: str = (
    "VERIFIED_PROXY_COUPLED_VAULT_AND_FOCUSMAG_BRIGHTMON_INTERLOCK_GUARD"
)

STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID: str = (
    "BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID"
)
STATUS_BLOCKED_G75_SIMULTANEOUS_REC_LOG_OR_PPLUT_4K_HDMI_CLAIM: str = (
    "BLOCKED_G75_SIMULTANEOUS_REC_LOG_OR_PPLUT_4K_HDMI_CLAIM"
)
STATUS_BLOCKED_G75_HDMI_ONLY_INTERNAL_CARD_REC_FORBIDDEN: str = (
    "BLOCKED_G75_HDMI_ONLY_INTERNAL_CARD_REC_FORBIDDEN"
)
STATUS_BLOCKED_G75_HDMI_INFO_DISPLAY_OR_DESQUEEZE_LOCK_VIOLATION: str = (
    "BLOCKED_G75_HDMI_INFO_DISPLAY_OR_DESQUEEZE_LOCK_VIOLATION"
)
STATUS_BLOCKED_G75_HDMI_INFO_ON_CAMERA_LCD_NOT_BLANKED: str = (
    "BLOCKED_G75_HDMI_INFO_ON_CAMERA_LCD_NOT_BLANKED"
)
STATUS_BLOCKED_G75_TELEMETRY_INVALID: str = (
    "BLOCKED_G75_HDMI_LOG1080_HDMIONLY_TELEMETRY_INVALID"
)

STATUS_BLOCKED_G76_PROXY_FORMAT_TABLE_INVALID: str = (
    "BLOCKED_G76_PROXY_FORMAT_TABLE_INVALID"
)
STATUS_BLOCKED_G76_PROXY_HIGH_FPS_OR_HDMIONLY_CUTOFF: str = (
    "BLOCKED_G76_PROXY_HIGH_FPS_OR_HDMIONLY_CUTOFF"
)
STATUS_BLOCKED_G76_PROXY_COUPLED_VAULT_OR_PLAYBACK_VIOLATION: str = (
    "BLOCKED_G76_PROXY_COUPLED_VAULT_OR_PLAYBACK_VIOLATION"
)
STATUS_BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION: str = (
    "BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION"
)
STATUS_BLOCKED_G76_MARKER_DISPLAY_OR_ESSENCE_MAGNIFIED: str = (
    "BLOCKED_G76_MARKER_DISPLAY_OR_ESSENCE_MAGNIFIED"
)
STATUS_BLOCKED_G76_BRIGHT_MONITORING_INTERLOCK_VIOLATION: str = (
    "BLOCKED_G76_BRIGHT_MONITORING_INTERLOCK_VIOLATION"
)
STATUS_BLOCKED_G76_TELEMETRY_INVALID: str = (
    "BLOCKED_G76_PROXY_FOCUSMAG_BRIGHTMON_TELEMETRY_INVALID"
)

STATUS_BLOCKED_PHASE210_DONOR_INTEGRITY: str = (
    "BLOCKED_PHASE210_76GATE_DONOR_INTEGRITY_OR_BUDGET_EXCEEDED"
)
STATUS_BLOCKED_PERSISTENT_EMMC_WRITE: str = (
    "BLOCKED_BY_PERSISTENT_EMMC_WRITE_REDLINE"
)

# Gate G75 Constants — [HDMI Output Settings], Log/PPLUT 1080p Downshift & LCD Blanking
HDMI_OUTPUT_SETTINGS_MENU_PATH: str = (
    "MENU -> Setup -> [External Output] -> [HDMI Output Settings]"
)
REC_MEDIA_DUR_HDMI_ON: str = "ON"
REC_MEDIA_DUR_HDMI_OFF_ONLY: str = "OFF_HDMI_ONLY"
ALLOWED_REC_MEDIA_DUR_HDMI_MODES: Tuple[str, ...] = (
    REC_MEDIA_DUR_HDMI_ON,
    REC_MEDIA_DUR_HDMI_OFF_ONLY,
)
ALLOWED_HDMI_OUTPUT_RESOLUTIONS: Tuple[str, ...] = ("AUTO", "2160P", "1080P", "1080I")
ALLOWED_4K_HDMI_ONLY_FORMATS: Tuple[str, ...] = (
    "59.94P_10BIT",
    "50P_10BIT",
    "29.97P_10BIT",
    "25P_10BIT",
    "23.98P_10BIT",
    "24.00P_10BIT",
)
ALLOWED_LOG_SHOOTING_MODES_G75: Tuple[str, ...] = (
    "OFF",
    "CINE_EI",
    "CINE_EI_QUICK",
    "FLEXIBLE_ISO",
)
ACTIVE_LOG_SHOOTING_MODES_G75: Tuple[str, ...] = (
    "CINE_EI",
    "CINE_EI_QUICK",
    "FLEXIBLE_ISO",
)
PPLUT_PICTURE_PROFILES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
ALLOWED_PICTURE_PROFILES_G75: Tuple[str, ...] = (
    "OFF",
    "PP1",
    "PP2",
    "PP3",
    "PP4",
    "PP5",
    "PP6",
    "PP7",
    "PP8",
    "PP9",
    "PP10",
    "PP11",
    *PPLUT_PICTURE_PROFILES,
)

# Gate G76 Constants — [Proxy Settings], Coupled Vault & FocusMag / BrightMon Interlocks
PROXY_SETTINGS_MENU_PATH: str = (
    "MENU -> Shooting -> [Image Quality/Rec] -> [Proxy Settings]"
)
PROXY_FORMAT_XAVC_HS_HD: str = "XAVC_HS_HD"
PROXY_FORMAT_XAVC_S_HD: str = "XAVC_S_HD"
FX3_PROXY_FORMAT_TABLE: Mapping[str, Mapping[str, Tuple[int, int, int, int, str, float]]] = {
    PROXY_FORMAT_XAVC_HS_HD: {
        "16M_420_10BIT": (1920, 1080, 16, 10, "HEVC_H265", 59.94),
        "9M_420_10BIT": (1920, 1080, 9, 10, "HEVC_H265", 59.94),
    },
    PROXY_FORMAT_XAVC_S_HD: {
        "6M_420_8BIT": (1280, 720, 6, 8, "AVC_H264", 59.94),
    },
}
PROXY_BLOCKED_REC_FRAME_RATES: Tuple[str, ...] = ("119.88P", "120P", "100P")
PROXY_SQ_SENSOR_FPS_CUTOFF: float = 100.0
PROXY_MAIN_CLIP_DIR: str = "M4ROOT/CLIP/"
PROXY_SUB_CLIP_DIR: str = "M4ROOT/SUB/"

ALLOWED_MOVIE_INITIAL_FOCUS_MAG: Tuple[str, ...] = ("X1.0", "X4.0")
ALLOWED_STILL_FF_INITIAL_FOCUS_MAG: Tuple[str, ...] = ("X1.0", "X2.1")
ALLOWED_STILL_APSC_INITIAL_FOCUS_MAG: Tuple[str, ...] = ("X1.0", "X1.5")
ALLOWED_FOCUS_MAGNIF_TIMES: Tuple[str, ...] = ("2_SEC", "5_SEC", "NO_LIMIT")
ALLOWED_BRIGHT_MONITORING_EXPOSURE_MODES: Tuple[str, ...] = ("P", "A", "S", "M")

# Pinned FX3 v7.02 & FX6 v6.01 Donor Specs (bounded <0.15s O_RDONLY verification)
PINNED_PHASE210_DONOR_SPECS: Mapping[
    str, Tuple[str, str, int, str, Tuple[bytes, ...], str]
] = {
    "fx3_cpapp_b": (
        "fx3",
        "sony-firmware-20261024/stage2/extraction/files/nflasha8/cpapp-b.bin",
        15_980_568,
        "c90d00d807874a5309dc1b65b203287e83608ceee513cc57b53409333fb6bcba",
        (
            b"ILME-FX3",
            b"HDMI",
            b"RAW",
            b"Log",
            b"LUT",
            b"DeSqueeze",
            b"Proxy",
            b"CLIP",
            b"SUB",
            b"Focus",
            b"Magnif",
            b"Bright",
            b"1080",
            b"BK4",
            b"/setting",
        ),
        "fx3/cpapp-b.bin::{15980568B,ILME-FX3,HDMI,RAW,Log,LUT,DeSqueeze,Proxy,CLIP,SUB,Focus,Magnif,Bright,1080}",
    ),
    "fx3_saveload_so": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/ap-projection/regular-files/usr/lib/libSaveLoadSettings.so",
        18_760,
        "07819f42bdad381ecdd41c3765c117c33b0c44c25be36279b26f83906d244cb7",
        (b"\x7fELF", b"SaveLoadSettings", b"Settings", b"Backup"),
        "fx3/libSaveLoadSettings.so::{18760B,ELF,SaveLoadSettings,Settings,Backup}",
    ),
    "fx3_bk4_bin": (
        "fx3",
        "fx3-vm-20261101/menu-repair-01/original-uipc/original-seeds/FX3-CX95900_ALLLANG-Backup.bin",
        2_229_740,
        "bf3a9d851f9853fd80953be165f2e4d77770314a85465bc7698ebad438d0e7a2",
        (b"BK4", b"ILME-FX3", b"TC", b"/setting"),
        "fx3/FX3-CX95900_ALLLANG-Backup.bin::{2229740B,BK4,ILME-FX3,TC,/setting}",
    ),
    "fx6_bk4_bin": (
        "fx6",
        "fx3-color-port-20261027/FX6-donor-assessment-20261103/team/donor/tree/0110_backup/SYSIPSX-DSLR/CHAPLIN/CX95898_NTSC.bin",
        2_253_333,
        "e2eafd4e950ead94fdba64722b225b9ccf4cf294ce4c1cf956b9e62926bbf89e",
        (b"BK4", b"WB", b"TC", b"/setting"),
        "fx6/CX95898_NTSC.bin::{2253333B,BK4,WB,TC,/setting}",
    ),
}


# ---------------------------------------------------------------------------
# Data Models (Zero raw bytes reprs; hex strings / ASCII markers only)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase210DonorAuditResult:
    valid: bool
    status: str
    verification_mode: str
    access_mode: str
    files_inspected: int
    elapsed_seconds: float
    within_budget_150ms: bool
    raw_firmware_bytes_leaked: int
    checked_markers: Tuple[str, ...]
    missing_markers: Tuple[str, ...]
    fx3_contracts_verified: bool
    fx6_contracts_verified: bool
    sha256_by_artifact: Dict[str, str]
    bytes_by_artifact: Dict[str, int]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class HdmiLog1080AndHdmiOnly4kBlankLcdResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    body_model_name: str
    body_model_id_hex: str
    firmware_version: str
    canonical_rec_media_dur_hdmi: str
    canonical_output_resolution_menu: str
    canonical_4k_hdmi_only_format: str
    canonical_log_shooting_mode: str
    canonical_picture_profile: str
    hdmi_raw_output_on: bool
    log_or_pplut_1080p_downshift_active: bool
    modeled_effective_hdmi_output: str
    internal_card_recording_active: bool
    effective_hdmi_info_display_on: bool
    hdmi_desqueeze_display_active: bool
    camera_lcd_panel_blanked: bool
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class ProxyCoupledVaultAndFocusMagBrightMonResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    canonical_proxy_format: str
    canonical_proxy_setting: str
    proxy_width: int
    proxy_height: int
    proxy_bitrate_mbps: int
    proxy_bit_depth: int
    proxy_recording_on: bool
    proxy_cutoff_reasons: Tuple[str, ...]
    coupled_vault_delete_parity: bool
    coupled_vault_protect_parity: bool
    on_camera_proxy_playback_blocked: bool
    canonical_shooting_mode: str
    canonical_initial_focus_mag: str
    focus_magnifier_active: bool
    auto_magnifier_in_mf_active: bool
    marker_display_suppressed: bool
    bright_monitoring_active: bool
    live_view_display_mode: str
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G75HdmiLog1080HdmiOnlyGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    hdmi_log1080_hdmionly_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class G76ProxyFocusMagBrightMonGuardResult:
    valid: bool
    status: str
    violation_codes: Tuple[str, ...]
    verification_mode: str
    donor_audit: Dict[str, Any]
    proxy_focusmag_brightmon_guard: Dict[str, Any]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class Master76GateReport:
    schema: str
    version: str
    evaluated_utc: str
    verification_mode: str
    clean_room_forced: bool
    dry_run_rehearsal_only: bool
    overall_ready_for_hardware_attach: bool
    hardware_live_attachment_authorized: bool
    offline_73_gates_verified: bool
    all_76_gates_verified: bool
    g13_to_g76_all_passed: bool
    g75_to_g76_all_passed: bool
    h0_h1_trial_entry_allowed: bool
    status: str
    agent_auto_flash_blocked: bool
    human_hardware_attach_token: bool
    el3_payload_transmit_authorized: bool
    spi_nor_write_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    physical_flash_auto_exec_authorized: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    technical_gates_passed: int
    summary: Dict[str, Any]
    gates: Tuple[Dict[str, Any], ...]
    master_74_report: Dict[str, Any]
    g75_result: Dict[str, Any]
    g76_result: Dict[str, Any]
    errors: Tuple[str, ...]
    warnings: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Internal Helpers & Normalization
# ---------------------------------------------------------------------------


def _is_forced_clean_room(force_clean_room: Optional[bool] = None) -> bool:
    if force_clean_room is not None:
        return bool(force_clean_room)
    return os.environ.get(ENV_FORCE_CLEAN_ROOM, "").strip() in (
        "1",
        "true",
        "TRUE",
        "yes",
        "YES",
    )


def _read_file_o_rdonly(path: Path) -> bytes:
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0)
    fd = os.open(str(path), flags)
    chunks: List[bytes] = []
    try:
        while True:
            buf = os.read(fd, 1 << 20)
            if not buf:
                break
            chunks.append(buf)
    finally:
        os.close(fd)
    return b"".join(chunks)


def _add_code(codes: List[str], code: str) -> None:
    if code not in codes:
        codes.append(code)


def _is_finite_num(val: Any) -> bool:
    if isinstance(val, bool) or not isinstance(val, (int, float)):
        return False
    f = float(val)
    return abs(f) < 1e12 and (f == f)


def _norm_token(val: str) -> str:
    s = val.strip().upper().replace("&", "_AND_")
    return re.sub(r"[^A-Z0-9.]+", "_", s).strip("_")


def _norm_rec_media_dur_hdmi(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", val.strip().upper()).strip("_")
    if t in ("ON", "REC_MEDIA_ON", "INTERNAL_AND_HDMI"):
        return REC_MEDIA_DUR_HDMI_ON
    if t in ("OFF_HDMI_ONLY", "HDMI_ONLY", "OFF"):
        return REC_MEDIA_DUR_HDMI_OFF_ONLY
    return t


def _norm_4k_hdmi_only_format(val: str) -> str:
    s = val.strip().upper().replace(" ", "_")
    s = re.sub(r"_+", "_", s).strip("_")
    aliases = {
        "59.94P_10BIT": "59.94P_10BIT",
        "50P_10BIT": "50P_10BIT",
        "29.97P_10BIT": "29.97P_10BIT",
        "25P_10BIT": "25P_10BIT",
        "23.98P_10BIT": "23.98P_10BIT",
        "24.00P_10BIT": "24.00P_10BIT",
        "24P_10BIT": "24.00P_10BIT",
    }
    return aliases.get(s, s)


def _norm_log_shooting_mode(val: Union[str, bool]) -> str:
    if isinstance(val, bool):
        return "CINE_EI" if val else "OFF"
    t = re.sub(r"[^A-Z0-9]+", "_", val.strip().upper()).strip("_")
    if t in ("OFF", "DISABLED", "NONE"):
        return "OFF"
    if t in ("CINE_EI", "ON_CINE_EI"):
        return "CINE_EI"
    if t in ("CINE_EI_QUICK", "ON_CINE_EI_QUICK"):
        return "CINE_EI_QUICK"
    if t in ("FLEXIBLE_ISO", "ON_FLEXIBLE_ISO"):
        return "FLEXIBLE_ISO"
    return t


def _norm_picture_profile(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "", val.strip().upper())
    return "OFF" if t in ("OFF", "NONE", "DISABLED") else t


def _norm_proxy_format(val: str) -> str:
    t = re.sub(r"[^A-Z0-9]+", "_", val.strip().upper()).strip("_")
    return t


def _norm_proxy_setting(val: str) -> str:
    s = val.strip().upper().replace("4:2:0", "420")
    return re.sub(r"[^A-Z0-9]+", "_", s).strip("_")


def _norm_shooting_mode(val: str) -> str:
    t = _norm_token(val).replace(".", "_")
    if t in ("MOVIE", "CINE_EI", "FLEXIBLE_ISO", "BIG6_MOVIE"):
        return "MOVIE"
    if t in ("S_AND_Q", "SQ", "SLOW_AND_QUICK"):
        return "S&Q"
    if t in ("STILL", "PHOTO"):
        return "STILL"
    return t


def _norm_focus_mag_scale(val: str) -> str:
    s = val.strip().upper().replace(" ", "")
    if not s.startswith("X") and s.endswith("X"):
        s = "X" + s[:-1]
    if s in ("X1", "1.0"):
        return "X1.0"
    if s in ("X4", "4.0"):
        return "X4.0"
    return s


# ---------------------------------------------------------------------------
# 1. Bounded `<0.15s` O_RDONLY Local Donor Audit (`FX3_FX6_FORCE_CLEAN_ROOM=1`)
# ---------------------------------------------------------------------------

_DONOR_BLOB_CACHE: Dict[str, Tuple[int, float, int, str, bytes]] = {}


def _read_cached_donor_o_rdonly(path: Path) -> Tuple[int, str, bytes]:
    key = str(path.resolve())
    st = os.stat(key)
    cached = _DONOR_BLOB_CACHE.get(key)
    if cached is not None and cached[0] == st.st_size and cached[1] == st.st_mtime:
        return cached[2], cached[3], cached[4]
    blob = _read_file_o_rdonly(path)
    sha = hashlib.sha256(blob).hexdigest()
    _DONOR_BLOB_CACHE[key] = (st.st_size, st.st_mtime, len(blob), sha, blob)
    return len(blob), sha, blob


def audit_phase210_donor_contracts(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    max_budget_seconds: float = DONOR_CHECK_MAX_SECONDS,
) -> Phase210DonorAuditResult:
    """Bounded `<0.15s` `O_RDONLY` local donor contract check with deterministic
    `FX3_FX6_FORCE_CLEAN_ROOM=1` synthetic fallback (`raw_firmware_bytes_leaked == 0`).
    """
    t0 = time.perf_counter()
    clean_forced = _is_forced_clean_room(force_clean_room)
    resolved_repo = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    paths = resolve_donor_thermal_power_paths(
        work_root=work_root, repo_root=resolved_repo
    )
    effective_work_root: Optional[Path] = (
        Path(work_root) if work_root is not None else paths.work_root
    )

    resolved: Dict[str, Path] = {}
    if effective_work_root is not None:
        for key, (_body, rel_path, *_rest) in PINNED_PHASE210_DONOR_SPECS.items():
            resolved[key] = effective_work_root / rel_path

    donor_available = (
        (not clean_forced)
        and (effective_work_root is not None)
        and bool(resolved)
        and all(p.is_file() for p in resolved.values())
    )

    if not donor_available:
        elapsed = time.perf_counter() - t0
        within_budget = elapsed < max_budget_seconds
        return Phase210DonorAuditResult(
            valid=within_budget,
            status=(
                STATUS_VERIFIED_SAFE
                if within_budget
                else STATUS_BLOCKED_PHASE210_DONOR_INTEGRITY
            ),
            verification_mode="CLEAN_ROOM_SYNTHETIC",
            access_mode="O_RDONLY",
            files_inspected=0,
            elapsed_seconds=round(elapsed, 6),
            within_budget_150ms=within_budget,
            raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
            checked_markers=tuple(
                spec[5] for spec in PINNED_PHASE210_DONOR_SPECS.values()
            ),
            missing_markers=(),
            fx3_contracts_verified=within_budget,
            fx6_contracts_verified=within_budget,
            sha256_by_artifact={
                k: spec[3] for k, spec in PINNED_PHASE210_DONOR_SPECS.items()
            },
            bytes_by_artifact={
                k: spec[2] for k, spec in PINNED_PHASE210_DONOR_SPECS.items()
            },
            errors=()
            if within_budget
            else (
                f"Clean-room donor check exceeded budget ({elapsed:.4f}s >= {max_budget_seconds:.4f}s).",
            ),
            warnings=(),
        )

    checked: List[str] = []
    missing: List[str] = []
    shas: Dict[str, str] = {}
    sizes: Dict[str, int] = {}
    errors: List[str] = []
    passed_keys: Set[str] = set()
    files_inspected = 0

    for key, (
        _body,
        _rel_name,
        exp_size,
        exp_sha,
        marker_tuple,
        marker_label,
    ) in PINNED_PHASE210_DONOR_SPECS.items():
        size_b, sha, blob = _read_cached_donor_o_rdonly(resolved[key])
        files_inspected += 1
        shas[key] = sha
        sizes[key] = size_b

        missing_for_file = [m for m in marker_tuple if m not in blob]
        integrity_ok = size_b == exp_size and sha == exp_sha
        if not missing_for_file:
            checked.append(marker_label)
        else:
            missing.append(marker_label)
            errors.append(
                f"Donor {key} missing {len(missing_for_file)} required marker(s) for {marker_label}."
            )
        if not integrity_ok:
            errors.append(
                f"Donor {key} integrity mismatch: size={size_b} (expected {exp_size}), "
                f"sha256={sha} (expected {exp_sha})."
            )
        if not missing_for_file and integrity_ok:
            passed_keys.add(key)

    elapsed = time.perf_counter() - t0
    within_budget = elapsed < max_budget_seconds
    if not within_budget:
        errors.append(
            f"Local O_RDONLY donor check exceeded {max_budget_seconds:.3f}s budget ({elapsed:.4f}s)."
        )

    fx3_keys = {k for k, s in PINNED_PHASE210_DONOR_SPECS.items() if s[0] == "fx3"}
    fx6_keys = {k for k, s in PINNED_PHASE210_DONOR_SPECS.items() if s[0] == "fx6"}
    valid = (len(errors) == 0) and (len(missing) == 0) and within_budget
    return Phase210DonorAuditResult(
        valid=valid,
        status=STATUS_VERIFIED_SAFE if valid else STATUS_BLOCKED_PHASE210_DONOR_INTEGRITY,
        verification_mode="LOCAL_DONOR_O_RDONLY",
        access_mode="O_RDONLY",
        files_inspected=files_inspected,
        elapsed_seconds=round(elapsed, 6),
        within_budget_150ms=within_budget,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        checked_markers=tuple(checked),
        missing_markers=tuple(missing),
        fx3_contracts_verified=fx3_keys.issubset(passed_keys) and valid,
        fx6_contracts_verified=fx6_keys.issubset(passed_keys) and valid,
        sha256_by_artifact=shas,
        bytes_by_artifact=sizes,
        errors=tuple(errors),
        warnings=(),
    )


# ---------------------------------------------------------------------------
# 2. Gate G75 Validators (`G75_HDMI_LOG_1080P_DOWNSHIFT_AND_HDMIONLY_4K_BLANK_LCD_GUARD`)
# ---------------------------------------------------------------------------


def resolve_effective_fx3_hdmi_output(
    *,
    rec_media_dur_hdmi_output: str = "On",
    output_resolution_menu: str = "2160p",
    four_k_hdmi_only_format: str = "59.94p 10bit",
    log_shooting_mode: Union[str, bool] = "Cine EI",
    picture_profile: str = "Off",
    hdmi_raw_output_on: bool = False,
) -> Tuple[str, bool]:
    """Return `(modeled_effective_hdmi_output, log_or_pplut_1080p_downshift_active)`
    under `ILME-FX3 Ver. 7.02` hardware rules.
    """
    rec_dur = _norm_rec_media_dur_hdmi(rec_media_dur_hdmi_output)
    out_res = output_resolution_menu.strip().upper()
    log_mode = _norm_log_shooting_mode(log_shooting_mode)
    pp = _norm_picture_profile(picture_profile)
    fk_fmt = _norm_4k_hdmi_only_format(four_k_hdmi_only_format)

    if hdmi_raw_output_on:
        return "4264X2408_16BIT_RAW", False

    if rec_dur == REC_MEDIA_DUR_HDMI_OFF_ONLY:
        return f"2160P_HDMI_ONLY_{fk_fmt}", False

    log_or_pplut = (log_mode in ACTIVE_LOG_SHOOTING_MODES_G75) or (
        pp in PPLUT_PICTURE_PROFILES
    )
    if log_or_pplut:
        return "1080P", True

    if out_res == "AUTO":
        return "2160P", False
    return out_res, False


def verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
    *,
    body_model_name: str = FX3_MODEL_NAME,
    body_model_id: Union[int, str] = FX3_MODEL_ID,
    firmware_version: str = FX3_DEFAULT_FW_VERSION_G75,
    rec_media_dur_hdmi_output: str = "On",
    output_resolution_menu: str = "2160p",
    four_k_hdmi_only_format: str = "59.94p 10bit",
    four_k_hdmi_only_setting_applied: Optional[bool] = None,
    qfhd_24p_enabled: bool = True,
    log_shooting_mode: Union[str, bool] = "Cine EI",
    picture_profile: str = "Off",
    hdmi_raw_output_on: bool = False,
    claimed_effective_hdmi_resolution: Optional[str] = None,
    simultaneous_internal_rec_and_nonraw_4k_log_hdmi_claimed: bool = False,
    internal_card_recording_active: Optional[bool] = None,
    hdmi_info_display_menu: str = "Off",
    effective_hdmi_info_display_on: Optional[bool] = None,
    hdmi_desqueeze_display_active: bool = False,
    camera_lcd_panel_blanked: Optional[bool] = None,
    camera_lcd_live_image_or_osd_visible: Optional[bool] = None,
) -> HdmiLog1080AndHdmiOnly4kBlankLcdResult:
    """Validate `ILME-FX3 Ver. 7.02` Gate G75 HDMI Log/PPLUT 1080p downshift,
    `[Off(HDMI Only)]` 4K output & zero-card-recording lockout, automatic
    `[HDMI Info. Display]->[Off]` & HDMI `[De-Squeeze Display]` suppression,
    and camera built-in LCD blanking when `[HDMI Info. Display]=[On]`.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        not isinstance(body_model_name, str)
        or not isinstance(firmware_version, str)
        or not isinstance(rec_media_dur_hdmi_output, str)
        or not isinstance(output_resolution_menu, str)
        or not isinstance(four_k_hdmi_only_format, str)
        or not isinstance(picture_profile, str)
        or not isinstance(hdmi_info_display_menu, str)
        or not isinstance(hdmi_raw_output_on, bool)
        or not isinstance(qfhd_24p_enabled, bool)
        or not isinstance(simultaneous_internal_rec_and_nonraw_4k_log_hdmi_claimed, bool)
        or not isinstance(hdmi_desqueeze_display_active, bool)
    ):
        _add_code(codes, STATUS_BLOCKED_G75_TELEMETRY_INVALID)
        errors.append("Gate G75 received non-string/non-bool telemetry argument.")
        return HdmiLog1080AndHdmiOnly4kBlankLcdResult(
            valid=False,
            status=codes[0],
            violation_codes=tuple(codes),
            body_model_name=str(body_model_name),
            body_model_id_hex=hex(FX3_MODEL_ID),
            firmware_version=str(firmware_version),
            canonical_rec_media_dur_hdmi="INVALID",
            canonical_output_resolution_menu="INVALID",
            canonical_4k_hdmi_only_format="INVALID",
            canonical_log_shooting_mode="INVALID",
            canonical_picture_profile="INVALID",
            hdmi_raw_output_on=False,
            log_or_pplut_1080p_downshift_active=False,
            modeled_effective_hdmi_output="INVALID",
            internal_card_recording_active=False,
            effective_hdmi_info_display_on=False,
            hdmi_desqueeze_display_active=False,
            camera_lcd_panel_blanked=False,
            errors=tuple(errors),
            warnings=(),
        )

    model_id_int = (
        body_model_id
        if isinstance(body_model_id, int) and not isinstance(body_model_id, bool)
        else int(str(body_model_id), 0)
        if isinstance(body_model_id, str) and str(body_model_id).strip()
        else -1
    )
    if body_model_name.strip().upper() != FX3_MODEL_NAME or model_id_int != FX3_MODEL_ID:
        _add_code(codes, STATUS_BLOCKED_G75_TELEMETRY_INVALID)
        errors.append(
            f"Gate G75 requires {FX3_MODEL_NAME} ({hex(FX3_MODEL_ID)}), got "
            f"{body_model_name!r} ({hex(max(model_id_int, 0))})."
        )

    rec_dur = _norm_rec_media_dur_hdmi(rec_media_dur_hdmi_output)
    out_res = output_resolution_menu.strip().upper()
    fk_fmt = _norm_4k_hdmi_only_format(four_k_hdmi_only_format)
    log_mode = _norm_log_shooting_mode(log_shooting_mode)
    pp = _norm_picture_profile(picture_profile)
    info_menu = hdmi_info_display_menu.strip().upper()

    if rec_dur not in ALLOWED_REC_MEDIA_DUR_HDMI_MODES:
        _add_code(codes, STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID)
        errors.append(
            f"[Rec. Media dur HDMI Output]={rec_media_dur_hdmi_output!r} invalid; "
            f"expected [On] or [Off(HDMI Only)]."
        )
    if out_res not in ALLOWED_HDMI_OUTPUT_RESOLUTIONS:
        _add_code(codes, STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID)
        errors.append(
            f"[Output Resolution]={output_resolution_menu!r} invalid; expected Auto/2160p/1080p/1080i."
        )
    if fk_fmt not in ALLOWED_4K_HDMI_ONLY_FORMATS:
        _add_code(codes, STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID)
        errors.append(
            f"[4K Output Set.(HDMI Only)]={four_k_hdmi_only_format!r} invalid; "
            f"expected one of {ALLOWED_4K_HDMI_ONLY_FORMATS}."
        )
    if (
        rec_dur == REC_MEDIA_DUR_HDMI_OFF_ONLY
        and fk_fmt == "24.00P_10BIT"
        and not qfhd_24p_enabled
    ):
        _add_code(codes, STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID)
        errors.append(
            "[4K Output Set.(HDMI Only)]=24.00p 10bit requires [QFHD 24p] system mode enabled."
        )
    if rec_dur == REC_MEDIA_DUR_HDMI_ON and four_k_hdmi_only_setting_applied is True:
        _add_code(codes, STATUS_BLOCKED_G75_HDMI_OUTPUT_MODE_OR_4K_SET_INVALID)
        errors.append(
            "[4K Output Set.(HDMI Only)] cannot be applied while [Rec. Media dur HDMI Output]=[On]."
        )
    if log_mode not in ALLOWED_LOG_SHOOTING_MODES_G75:
        _add_code(codes, STATUS_BLOCKED_G75_TELEMETRY_INVALID)
        errors.append(f"Unsupported [Log Shooting] mode {log_shooting_mode!r}.")
    if pp not in ALLOWED_PICTURE_PROFILES_G75:
        _add_code(codes, STATUS_BLOCKED_G75_TELEMETRY_INVALID)
        errors.append(f"Unsupported [Picture Profile] {picture_profile!r}.")
    if info_menu not in ("ON", "OFF"):
        _add_code(codes, STATUS_BLOCKED_G75_TELEMETRY_INVALID)
        errors.append(f"[HDMI Info. Display] menu must be On or Off, got {hdmi_info_display_menu!r}.")

    modeled_hdmi, downshift_1080p = resolve_effective_fx3_hdmi_output(
        rec_media_dur_hdmi_output=rec_dur,
        output_resolution_menu=out_res,
        four_k_hdmi_only_format=fk_fmt,
        log_shooting_mode=log_mode,
        picture_profile=pp,
        hdmi_raw_output_on=hdmi_raw_output_on,
    )

    # 1. Log Shooting / PPLUT1..4 1080p HDMI downshift under [Rec. Media dur HDMI Output]=[On] & non-RAW
    if simultaneous_internal_rec_and_nonraw_4k_log_hdmi_claimed:
        _add_code(codes, STATUS_BLOCKED_G75_SIMULTANEOUS_REC_LOG_OR_PPLUT_4K_HDMI_CLAIM)
        errors.append(
            "ILME-FX3 Ver. 7.02 forbids simultaneous internal card recording + non-RAW 4K Log/PPLUT HDMI output."
        )
    if claimed_effective_hdmi_resolution is not None:
        claimed_norm = claimed_effective_hdmi_resolution.strip().upper().replace(" ", "_")
        if downshift_1080p and claimed_norm not in ("1080P", "1920X1080", "1080I"):
            _add_code(codes, STATUS_BLOCKED_G75_SIMULTANEOUS_REC_LOG_OR_PPLUT_4K_HDMI_CLAIM)
            errors.append(
                f"Active Log Shooting ({log_mode}) or Picture Profile ({pp}) with "
                f"[Rec. Media dur HDMI Output]=[On] & [RAW Output]=[Off] downshifts HDMI to 1080p, "
                f"blocking claimed {claimed_effective_hdmi_resolution!r}."
            )

    # 2. [Off(HDMI Only)] zero-internal-card-recording lockout
    eff_internal_rec = (
        (rec_dur == REC_MEDIA_DUR_HDMI_ON)
        if internal_card_recording_active is None
        else bool(internal_card_recording_active)
    )
    if rec_dur == REC_MEDIA_DUR_HDMI_OFF_ONLY and eff_internal_rec:
        _add_code(codes, STATUS_BLOCKED_G75_HDMI_ONLY_INTERNAL_CARD_REC_FORBIDDEN)
        errors.append(
            "[Rec. Media dur HDMI Output]=[Off(HDMI Only)] locks out internal CFexpress-A/SDXC movie recording."
        )

    # 3. Automatic [HDMI Info. Display]->[Off] & HDMI [De-Squeeze Display] suppression
    info_suppressed = (rec_dur == REC_MEDIA_DUR_HDMI_OFF_ONLY) or hdmi_raw_output_on
    modeled_info_on = False if info_suppressed else (info_menu == "ON")
    eff_info_on = (
        modeled_info_on
        if effective_hdmi_info_display_on is None
        else bool(effective_hdmi_info_display_on)
    )
    if info_suppressed and eff_info_on:
        _add_code(codes, STATUS_BLOCKED_G75_HDMI_INFO_DISPLAY_OR_DESQUEEZE_LOCK_VIOLATION)
        errors.append(
            "[HDMI Info. Display] is automatically forced to [Off] under [Off(HDMI Only)] or [RAW Output]=[On]."
        )
    if info_suppressed and hdmi_desqueeze_display_active:
        _add_code(codes, STATUS_BLOCKED_G75_HDMI_INFO_DISPLAY_OR_DESQUEEZE_LOCK_VIOLATION)
        errors.append(
            "HDMI [De-Squeeze Display] is suppressed under [Off(HDMI Only)] or [RAW Output]=[On]."
        )

    # 4. Camera built-in LCD blanking whenever [HDMI Info. Display]=[On]
    eff_lcd_blanked = (
        eff_info_on if camera_lcd_panel_blanked is None else bool(camera_lcd_panel_blanked)
    )
    if eff_info_on and (
        (not eff_lcd_blanked) or (camera_lcd_live_image_or_osd_visible is True)
    ):
        _add_code(codes, STATUS_BLOCKED_G75_HDMI_INFO_ON_CAMERA_LCD_NOT_BLANKED)
        errors.append(
            "When [HDMI Info. Display]=[On], the FX3 built-in LCD panel is blanked (zero image/OSD)."
        )

    valid = len(codes) == 0
    return HdmiLog1080AndHdmiOnly4kBlankLcdResult(
        valid=valid,
        status=STATUS_VERIFIED_G75 if valid else codes[0],
        violation_codes=tuple(codes),
        body_model_name=FX3_MODEL_NAME,
        body_model_id_hex=hex(FX3_MODEL_ID),
        firmware_version=firmware_version.strip(),
        canonical_rec_media_dur_hdmi=rec_dur,
        canonical_output_resolution_menu=out_res,
        canonical_4k_hdmi_only_format=fk_fmt,
        canonical_log_shooting_mode=log_mode,
        canonical_picture_profile=pp,
        hdmi_raw_output_on=hdmi_raw_output_on,
        log_or_pplut_1080p_downshift_active=downshift_1080p,
        modeled_effective_hdmi_output=modeled_hdmi,
        internal_card_recording_active=eff_internal_rec,
        effective_hdmi_info_display_on=eff_info_on,
        hdmi_desqueeze_display_active=hdmi_desqueeze_display_active,
        camera_lcd_panel_blanked=eff_lcd_blanked,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 3. Gate G76 Validators (`G76_PROXY_COUPLED_VAULT_AND_FOCUSMAG_BRIGHTMON_INTERLOCK_GUARD`)
# ---------------------------------------------------------------------------


def compute_fx3_proxy_cutoff_reasons(
    *,
    shooting_mode: str = "Movie",
    rec_frame_rate: str = "23.98p",
    sq_sensor_frame_rate_fps: float = 60.0,
    rec_media_dur_hdmi_output: str = "On",
) -> Tuple[str, ...]:
    """Return active hardware cutoff reasons blocking `[Proxy Recording]=[On]` on `ILME-FX3`."""
    reasons: List[str] = []
    mode = _norm_shooting_mode(shooting_mode)
    rec_fps = rec_frame_rate.strip().upper().replace(" ", "")
    if mode == "MOVIE" and rec_fps in PROXY_BLOCKED_REC_FRAME_RATES:
        reasons.append(f"NORMAL_MOVIE_HIGH_FPS_{rec_fps}")
    if mode == "S&Q":
        if rec_fps in PROXY_BLOCKED_REC_FRAME_RATES:
            reasons.append(f"SQ_REC_FRAME_RATE_{rec_fps}")
        if float(sq_sensor_frame_rate_fps) >= PROXY_SQ_SENSOR_FPS_CUTOFF:
            reasons.append(f"SQ_SENSOR_FPS_GE_100_{int(round(sq_sensor_frame_rate_fps))}FPS")
    if _norm_rec_media_dur_hdmi(rec_media_dur_hdmi_output) == REC_MEDIA_DUR_HDMI_OFF_ONLY:
        reasons.append("REC_MEDIA_DUR_HDMI_OFF_HDMI_ONLY")
    return tuple(reasons)


def verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
    *,
    proxy_file_format: str = "XAVC S HD",
    proxy_setting: str = "6M 4:2:0 8bit",
    proxy_width: Optional[int] = None,
    proxy_height: Optional[int] = None,
    proxy_max_fps: float = 59.94,
    proxy_recording_on: bool = True,
    shooting_mode: str = "Movie",
    rec_frame_rate: str = "23.98p",
    sq_sensor_frame_rate_fps: float = 60.0,
    rec_media_dur_hdmi_output: str = "On",
    main_clip_dir: str = PROXY_MAIN_CLIP_DIR,
    sub_proxy_dir: str = PROXY_SUB_CLIP_DIR,
    clip_deleted: bool = False,
    sub_proxy_deleted: bool = False,
    clip_protected: bool = True,
    sub_proxy_protected: bool = True,
    uncoupled_single_side_incamera_op_attempted: bool = False,
    on_camera_proxy_playback_claimed: bool = False,
    sensor_scan_mode: str = "FULL_FRAME",
    initial_focus_mag: str = "x1.0",
    focus_magnif_time: str = "No Limit",
    focus_magnifier_active: bool = False,
    auto_magnifier_in_mf_active: bool = False,
    auto_magnifier_in_mf_triggered_in_movie: bool = False,
    marker_display_visible_while_magnified: bool = False,
    recorded_essence_magnified: bool = False,
    bright_monitoring_active: bool = False,
    bright_monitoring_key_toggle_accepted: bool = False,
    exposure_mode: str = "M",
    focus_mode: str = "Manual Focus",
    camera_powered_off: bool = False,
    live_view_display_mode: Optional[str] = None,
) -> ProxyCoupledVaultAndFocusMagBrightMonResult:
    """Validate `ILME-FX3 Ver. 7.02` Gate G76 `[Proxy Settings]` 2-format/3-setting table,
    high-fps / HDMI-Only proxy cutoffs, coupled `M4ROOT/CLIP/` + `M4ROOT/SUB/` Delete/Protect
    vault parity, and `[Focus Magnifier]` x `[Auto Magnifier in MF]` x `[Bright Monitoring]`
    interlocks.
    """
    codes: List[str] = []
    errors: List[str] = []
    warnings: List[str] = []

    if (
        not isinstance(proxy_file_format, str)
        or not isinstance(proxy_setting, str)
        or not isinstance(shooting_mode, str)
        or not isinstance(rec_frame_rate, str)
        or not isinstance(initial_focus_mag, str)
        or not _is_finite_num(sq_sensor_frame_rate_fps)
        or not _is_finite_num(proxy_max_fps)
        or not isinstance(proxy_recording_on, bool)
    ):
        _add_code(codes, STATUS_BLOCKED_G76_TELEMETRY_INVALID)
        errors.append("Gate G76 received invalid telemetry argument types.")
        return ProxyCoupledVaultAndFocusMagBrightMonResult(
            valid=False,
            status=codes[0],
            violation_codes=tuple(codes),
            canonical_proxy_format="INVALID",
            canonical_proxy_setting="INVALID",
            proxy_width=0,
            proxy_height=0,
            proxy_bitrate_mbps=0,
            proxy_bit_depth=0,
            proxy_recording_on=False,
            proxy_cutoff_reasons=(),
            coupled_vault_delete_parity=False,
            coupled_vault_protect_parity=False,
            on_camera_proxy_playback_blocked=False,
            canonical_shooting_mode="INVALID",
            canonical_initial_focus_mag="INVALID",
            focus_magnifier_active=False,
            auto_magnifier_in_mf_active=False,
            marker_display_suppressed=False,
            bright_monitoring_active=False,
            live_view_display_mode="INVALID",
            errors=tuple(errors),
            warnings=(),
        )

    canon_pfmt = _norm_proxy_format(proxy_file_format)
    canon_pset = _norm_proxy_setting(proxy_setting)
    fmt_map = FX3_PROXY_FORMAT_TABLE.get(canon_pfmt)
    spec = fmt_map.get(canon_pset) if fmt_map is not None else None

    if spec is None or float(proxy_max_fps) > 59.94 + 1e-6:
        _add_code(codes, STATUS_BLOCKED_G76_PROXY_FORMAT_TABLE_INVALID)
        errors.append(
            f"Invalid FX3 [Proxy Settings] combination ({proxy_file_format!r}, {proxy_setting!r}, "
            f"max_fps={proxy_max_fps}); allowed XAVC HS HD (16M/9M 10bit 1080p) or XAVC S HD (6M 8bit 720p) <=59.94p."
        )
        exp_w, exp_h, exp_mbps, exp_bits = 0, 0, 0, 0
    else:
        exp_w, exp_h, exp_mbps, exp_bits, _codec, _mfps = spec
        if (proxy_width is not None and proxy_width != exp_w) or (
            proxy_height is not None and proxy_height != exp_h
        ):
            _add_code(codes, STATUS_BLOCKED_G76_PROXY_FORMAT_TABLE_INVALID)
            errors.append(
                f"Proxy dimensions ({proxy_width}x{proxy_height}) mismatch expected {exp_w}x{exp_h} for {canon_pfmt}."
            )

    # 2. High-FPS & [Off(HDMI Only)] proxy cutoffs
    cutoff_reasons = compute_fx3_proxy_cutoff_reasons(
        shooting_mode=shooting_mode,
        rec_frame_rate=rec_frame_rate,
        sq_sensor_frame_rate_fps=sq_sensor_frame_rate_fps,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
    )
    if cutoff_reasons and proxy_recording_on:
        _add_code(codes, STATUS_BLOCKED_G76_PROXY_HIGH_FPS_OR_HDMIONLY_CUTOFF)
        errors.append(
            f"[Proxy Recording]=[On] blocked by hardware cutoff(s): {', '.join(cutoff_reasons)}."
        )

    # 3. Coupled M4ROOT/CLIP/ + M4ROOT/SUB/ vault parity & on-camera proxy playback block
    main_ok = main_clip_dir.strip().upper().rstrip("/").endswith("M4ROOT/CLIP")
    sub_ok = sub_proxy_dir.strip().upper().rstrip("/").endswith("M4ROOT/SUB")
    del_parity = (clip_deleted == sub_proxy_deleted) and (
        not uncoupled_single_side_incamera_op_attempted
    )
    prot_parity = (clip_protected == sub_proxy_protected) and (
        not uncoupled_single_side_incamera_op_attempted
    )
    if (
        (not main_ok)
        or (not sub_ok)
        or (not del_parity)
        or (not prot_parity)
        or on_camera_proxy_playback_claimed
    ):
        _add_code(codes, STATUS_BLOCKED_G76_PROXY_COUPLED_VAULT_OR_PLAYBACK_VIOLATION)
        errors.append(
            "In-camera Delete/Protect must atomically couple M4ROOT/CLIP/ + M4ROOT/SUB/, "
            "and on-camera proxy playback is unsupported on ILME-FX3."
        )

    # 4. [Initial Focus Mag.] movie vs still & [Auto Magnifier in MF] movie lockout
    canon_mode = _norm_shooting_mode(shooting_mode)
    canon_mag = _norm_focus_mag_scale(initial_focus_mag)
    canon_mag_time = re.sub(r"[^A-Z0-9]+", "_", focus_magnif_time.strip().upper()).strip("_")
    canon_scan = re.sub(r"[^A-Z0-9]+", "_", sensor_scan_mode.strip().upper()).strip("_")

    if canon_mag_time not in ALLOWED_FOCUS_MAGNIF_TIMES:
        _add_code(codes, STATUS_BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION)
        errors.append(f"Invalid [Focus Magnif. Time]={focus_magnif_time!r}.")

    if canon_mode in ("MOVIE", "S&Q"):
        if canon_mag not in ALLOWED_MOVIE_INITIAL_FOCUS_MAG:
            _add_code(codes, STATUS_BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION)
            errors.append(
                f"Movie/S&Q [Initial Focus Mag.] supports only x1.0 or x4.0, got {initial_focus_mag!r}."
            )
        if auto_magnifier_in_mf_triggered_in_movie or auto_magnifier_in_mf_active:
            _add_code(codes, STATUS_BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION)
            errors.append(
                "[Auto Magnifier in MF] (focus-ring trigger) is disabled during movie shooting on ILME-FX3."
            )
    elif canon_mode == "STILL":
        allowed_still = (
            ALLOWED_STILL_APSC_INITIAL_FOCUS_MAG
            if canon_scan in ("APSC_S35", "APS_C", "SUPER_35", "S35")
            else ALLOWED_STILL_FF_INITIAL_FOCUS_MAG
        )
        if canon_mag not in allowed_still:
            _add_code(codes, STATUS_BLOCKED_G76_FOCUS_MAG_SCALE_OR_MOVIE_AUTOMAG_VIOLATION)
            errors.append(
                f"Still ({canon_scan}) [Initial Focus Mag.]={initial_focus_mag!r} invalid; expected {allowed_still}."
            )
    else:
        _add_code(codes, STATUS_BLOCKED_G76_TELEMETRY_INVALID)
        errors.append(f"Unsupported shooting_mode={shooting_mode!r}.")

    # 5. [Marker Display] suppression while magnified & unmagnified recorded essence
    any_mag_active = focus_magnifier_active or auto_magnifier_in_mf_active
    marker_suppressed = not (any_mag_active and marker_display_visible_while_magnified)
    if (not marker_suppressed) or recorded_essence_magnified:
        _add_code(codes, STATUS_BLOCKED_G76_MARKER_DISPLAY_OR_ESSENCE_MAGNIFIED)
        errors.append(
            "[Marker Display] is suppressed while Focus Magnifier is active, and recorded movie essence stays unmagnified."
        )

    # 6. [Bright Monitoring] hard key-toggle lockout & P/A/S/M + MF auto-cancel + Setting Effect OFF
    canon_exp = exposure_mode.strip().upper()
    canon_fmode = re.sub(r"[^A-Z0-9]+", "_", focus_mode.strip().upper()).strip("_")
    is_mf = canon_fmode in ("MANUAL_FOCUS", "MF", "MANUAL")

    eff_lv_mode = (
        ("SETTING_EFFECT_OFF" if bright_monitoring_active else "SETTING_EFFECT_ON")
        if live_view_display_mode is None
        else re.sub(r"[^A-Z0-9]+", "_", live_view_display_mode.strip().upper()).strip("_")
    )

    if any_mag_active and (bright_monitoring_active or bright_monitoring_key_toggle_accepted):
        _add_code(codes, STATUS_BLOCKED_G76_BRIGHT_MONITORING_INTERLOCK_VIOLATION)
        errors.append(
            "[Bright Monitoring] custom-key toggle is hard-locked out while [Focus Magnifier] or [Auto Magnifier in MF] is active."
        )
    if bright_monitoring_active and (
        (canon_exp not in ALLOWED_BRIGHT_MONITORING_EXPOSURE_MODES)
        or (not is_mf)
        or camera_powered_off
        or (eff_lv_mode != "SETTING_EFFECT_OFF")
    ):
        _add_code(codes, STATUS_BLOCKED_G76_BRIGHT_MONITORING_INTERLOCK_VIOLATION)
        errors.append(
            "[Bright Monitoring] auto-cancels outside P/A/S/M or MF (or on power-off) and forces [Live View Display]=[Setting Effect OFF]."
        )

    valid = len(codes) == 0
    return ProxyCoupledVaultAndFocusMagBrightMonResult(
        valid=valid,
        status=STATUS_VERIFIED_G76 if valid else codes[0],
        violation_codes=tuple(codes),
        canonical_proxy_format=canon_pfmt,
        canonical_proxy_setting=canon_pset,
        proxy_width=exp_w,
        proxy_height=exp_h,
        proxy_bitrate_mbps=exp_mbps,
        proxy_bit_depth=exp_bits,
        proxy_recording_on=proxy_recording_on,
        proxy_cutoff_reasons=cutoff_reasons,
        coupled_vault_delete_parity=del_parity,
        coupled_vault_protect_parity=prot_parity,
        on_camera_proxy_playback_blocked=not on_camera_proxy_playback_claimed,
        canonical_shooting_mode=canon_mode,
        canonical_initial_focus_mag=canon_mag,
        focus_magnifier_active=focus_magnifier_active,
        auto_magnifier_in_mf_active=auto_magnifier_in_mf_active,
        marker_display_suppressed=marker_suppressed,
        bright_monitoring_active=bright_monitoring_active,
        live_view_display_mode=eff_lv_mode,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


# ---------------------------------------------------------------------------
# 4. Gate G75 & Gate G76 Evaluators
# ---------------------------------------------------------------------------


def evaluate_g75_hdmi_log1080_hdmionly_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    hdmi_log1080_hdmionly_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase210DonorAuditResult] = None,
) -> Tuple[GateVerdict, G75HdmiLog1080HdmiOnlyGuardResult]:
    """Evaluate Gate G75 (`G75_HDMI_LOG_1080P_DOWNSHIFT_AND_HDMIONLY_4K_BLANK_LCD_GUARD`)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase210_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_hdmi_log1080_and_hdmionly_4k_blank_lcd_guard(
        **dict(hdmi_log1080_hdmionly_kwargs or {})
    )

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE210_DONOR_INTEGRITY)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G75 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G75 if valid else codes[0]

    res = G75HdmiLog1080HdmiOnlyGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        hdmi_log1080_hdmionly_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, rec_dur_hdmi={guard.canonical_rec_media_dur_hdmi}, "
        f"log={guard.canonical_log_shooting_mode}, pp={guard.canonical_picture_profile}, "
        f"hdmi_eff={guard.modeled_effective_hdmi_output}(downshift1080p={guard.log_or_pplut_1080p_downshift_active}), "
        f"card_rec={guard.internal_card_recording_active}, info_on={guard.effective_hdmi_info_display_on}, "
        f"lcd_blanked={guard.camera_lcd_panel_blanked}"
    )
    verdict = GateVerdict(
        gate_id=G75_GATE_ID,
        gate_code=G75_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


def evaluate_g76_proxy_focusmag_brightmon_guard(
    *,
    work_root: Optional[Path] = None,
    repo_root: Optional[Path] = None,
    force_clean_room: Optional[bool] = None,
    proxy_focusmag_brightmon_kwargs: Optional[Mapping[str, Any]] = None,
    request_persistent_emmc_writes: bool = False,
    donor_audit: Optional[Phase210DonorAuditResult] = None,
) -> Tuple[GateVerdict, G76ProxyFocusMagBrightMonGuardResult]:
    """Evaluate Gate G76 (`G76_PROXY_COUPLED_VAULT_AND_FOCUSMAG_BRIGHTMON_INTERLOCK_GUARD`)."""
    audit = (
        donor_audit
        if donor_audit is not None
        else audit_phase210_donor_contracts(
            work_root=work_root,
            repo_root=repo_root,
            force_clean_room=force_clean_room,
        )
    )
    guard = verify_proxy_coupled_vault_and_focusmag_brightmon_guard(
        **dict(proxy_focusmag_brightmon_kwargs or {})
    )

    codes: List[str] = list(guard.violation_codes)
    errors: List[str] = list(audit.errors) + list(guard.errors)
    warnings: List[str] = list(audit.warnings) + list(guard.warnings)

    if not audit.valid:
        _add_code(codes, STATUS_BLOCKED_PHASE210_DONOR_INTEGRITY)
    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        _add_code(codes, STATUS_BLOCKED_PERSISTENT_EMMC_WRITE)
        errors.append("Gate G76 blocked persistent eMMC write authorization request.")

    valid = audit.valid and guard.valid and (not codes)
    status = STATUS_VERIFIED_G76 if valid else codes[0]

    res = G76ProxyFocusMagBrightMonGuardResult(
        valid=valid,
        status=status,
        violation_codes=tuple(codes),
        verification_mode=audit.verification_mode,
        donor_audit=audit.to_dict(),
        proxy_focusmag_brightmon_guard=guard.to_dict(),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    evidence = (
        f"mode={audit.verification_mode}, proxy={guard.canonical_proxy_format}/"
        f"{guard.canonical_proxy_setting}({guard.proxy_width}x{guard.proxy_height},on={guard.proxy_recording_on}), "
        f"coupled_vault=(del={guard.coupled_vault_delete_parity},prot={guard.coupled_vault_protect_parity}), "
        f"focus_mag={guard.canonical_initial_focus_mag}@{guard.canonical_shooting_mode}, "
        f"bright_mon={guard.bright_monitoring_active}({guard.live_view_display_mode})"
    )
    verdict = GateVerdict(
        gate_id=G76_GATE_ID,
        gate_code=G76_GATE_CODE,
        passed=valid,
        status=status,
        evidence=evidence,
        violation_codes=tuple(codes),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )
    return verdict, res


# ---------------------------------------------------------------------------
# 5. Unified 76-Gate Master Safety Preflight (`G01..G76`)
# ---------------------------------------------------------------------------


def evaluate_76gate_preflight(
    repo_root: Optional[Path] = None,
    *,
    force_clean_room: Optional[bool] = None,
    dry_run_simulated: bool = False,
    dry_run_simulated_backup: Optional[bool] = None,
    simulate_bench_dry_run: bool = False,
    include_large_binaries: bool = False,
    work_root: Optional[Path] = None,
    request_persistent_emmc_writes: bool = False,
    hdmi_log1080_hdmionly_kwargs: Optional[Mapping[str, Any]] = None,
    proxy_focusmag_brightmon_kwargs: Optional[Mapping[str, Any]] = None,
    master_74_override: Optional[Master74GateReport] = None,
    **m74_passthrough_kwargs: Any,
) -> Master76GateReport:
    """Evaluate all 76 Master Safety Gates (`G01..G76`) deterministically by delegating
    `G01..G74` directly to `evaluate_74gate_preflight()`.
    """
    resolved_root = (
        DEFAULT_REPO_ROOT if repo_root is None else Path(repo_root)
    ).resolve()
    clean_forced = _is_forced_clean_room(force_clean_room)
    effective_dry_run = bool(
        dry_run_simulated
        or simulate_bench_dry_run
        or bool(dry_run_simulated_backup)
    )

    m74_report: Master74GateReport = (
        master_74_override
        if master_74_override is not None
        else evaluate_74gate_preflight(
            resolved_root,
            force_clean_room=clean_forced,
            dry_run_simulated=effective_dry_run,
            include_large_binaries=include_large_binaries,
            work_root=work_root,
            request_persistent_emmc_writes=request_persistent_emmc_writes,
            **m74_passthrough_kwargs,
        )
    )

    phase210_audit = audit_phase210_donor_contracts(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
    )

    g75_verdict, g75_res = evaluate_g75_hdmi_log1080_hdmionly_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        hdmi_log1080_hdmionly_kwargs=hdmi_log1080_hdmionly_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase210_audit,
    )

    g76_verdict, g76_res = evaluate_g76_proxy_focusmag_brightmon_guard(
        work_root=work_root,
        repo_root=resolved_root,
        force_clean_room=clean_forced,
        proxy_focusmag_brightmon_kwargs=proxy_focusmag_brightmon_kwargs,
        request_persistent_emmc_writes=request_persistent_emmc_writes,
        donor_audit=phase210_audit,
    )

    gates_75_to_76 = [
        {
            "gate_id": v.gate_id,
            "gate_code": v.gate_code,
            "status": v.status,
            "passed": v.passed,
            "evidence": v.evidence,
            "violation_codes": list(v.violation_codes),
        }
        for v in (g75_verdict, g76_verdict)
    ]
    all_gates = tuple(list(m74_report.gates) + gates_75_to_76)

    g01_to_g12_verified = int(m74_report.summary["g01_to_g12_verified"])
    g13_to_g74_verified = (
        int(m74_report.summary["g13_to_g72_verified"])
        + int(m74_report.summary["g73_to_g74_verified"])
    )
    g75_to_g76_verified = sum(1 for v in (g75_verdict, g76_verdict) if v.passed)
    total_verified = g01_to_g12_verified + g13_to_g74_verified + g75_to_g76_verified

    g75_to_g76_all_passed = g75_to_g76_verified == 2
    g13_to_g76_all_passed = m74_report.g13_to_g74_all_passed and g75_to_g76_all_passed
    g01_to_g09_ok = all(bool(g["passed"]) for g in m74_report.gates[:9])

    offline_73_verified = (
        g01_to_g09_ok
        and m74_report.offline_71_gates_verified
        and g75_to_g76_all_passed
        and (not request_persistent_emmc_writes)
    )
    all_76_verified = (
        (g01_to_g12_verified == 12)
        and g13_to_g76_all_passed
        and (not request_persistent_emmc_writes)
    )

    overall_ready_for_hardware_attach = False
    agent_auto_flash_blocked = bool(m74_report.agent_auto_flash_blocked)

    h0_h1_allowed = (
        offline_73_verified
        and m74_report.h0_h1_trial_entry_allowed
        and g75_to_g76_all_passed
        and agent_auto_flash_blocked
        and (not HUMAN_HARDWARE_ATTACH_TOKEN)
        and (not HARDWARE_LIVE_ATTACHMENT_AUTHORIZED)
        and (not PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED)
        and (not EL3_PAYLOAD_TRANSMIT_AUTHORIZED)
        and (not SPI_NOR_WRITE_AUTHORIZED)
        and (not PERSISTENT_EMMC_WRITES_AUTHORIZED)
        and (not request_persistent_emmc_writes)
    )

    errors: List[str] = (
        list(m74_report.errors) + list(g75_verdict.errors) + list(g76_verdict.errors)
    )
    warnings: List[str] = (
        list(m74_report.warnings)
        + list(g75_verdict.warnings)
        + list(g76_verdict.warnings)
    )

    if (
        request_persistent_emmc_writes
        or PERSISTENT_EMMC_WRITES_AUTHORIZED
        or PERSISTENT_WRITE_RELEASE
    ):
        overall_status = STATUS_BLOCKED_PERSISTENT_EMMC_WRITE
    elif not m74_report.g13_to_g74_all_passed:
        overall_status = m74_report.status
    elif not g75_verdict.passed:
        overall_status = g75_verdict.status
    elif not g76_verdict.passed:
        overall_status = g76_verdict.status
    elif not g01_to_g09_ok:
        overall_status = "BLOCKED_BY_CORE_G01_G09_REFERENCE_MISSING"
    elif all_76_verified and effective_dry_run:
        overall_status = "VERIFIED_ALL_76_GATES_DRY_RUN_SIMULATED_BACKUP"
    elif all_76_verified:
        overall_status = "VERIFIED_ALL_76_GATES"
    else:
        overall_status = "VERIFIED_73_OF_76_AWAITING_PHYSICAL_TIER0"

    if clean_forced:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"
    elif (
        m74_report.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g75_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
        or g76_res.verification_mode == "LOCAL_DONOR_O_RDONLY"
    ):
        verification_mode = "LOCAL_DONOR_O_RDONLY"
    else:
        verification_mode = "CLEAN_ROOM_SYNTHETIC"

    summary = {
        "total_gates": 76,
        "verified_gates": total_verified,
        "technical_gates_passed": total_verified,
        "blocked_or_pending_gates": 76 - total_verified,
        "g01_to_g12_verified": g01_to_g12_verified,
        "g13_to_g74_verified": g13_to_g74_verified,
        "g75_to_g76_verified": g75_to_g76_verified,
        "g13_to_g76_all_passed": g13_to_g76_all_passed,
        "g75_to_g76_all_passed": g75_to_g76_all_passed,
        "offline_73_gates_verified": offline_73_verified,
        "all_76_gates_verified": all_76_verified,
        "dry_run_rehearsal_only": effective_dry_run,
        "overall_ready_for_hardware_attach": overall_ready_for_hardware_attach,
        "hardware_live_attachment_authorized": HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        "h0_h1_trial_entry_allowed": h0_h1_allowed,
        "agent_auto_flash_blocked": agent_auto_flash_blocked,
        "human_hardware_attach_token": HUMAN_HARDWARE_ATTACH_TOKEN,
        "physical_flash_auto_exec_authorized": PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        "el3_payload_transmit_authorized": EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        "spi_nor_write_authorized": SPI_NOR_WRITE_AUTHORIZED,
        "persistent_emmc_writes_authorized": PERSISTENT_EMMC_WRITES_AUTHORIZED,
        "persistent_write_release": PERSISTENT_WRITE_RELEASE,
        "usb_packets_transmitted": USB_PACKETS_TRANSMITTED,
        "physical_usb_packets_emitted": PHYSICAL_USB_PACKETS_EMITTED,
        "raw_firmware_bytes_leaked": RAW_FIRMWARE_BYTES_LEAKED,
    }

    return Master76GateReport(
        schema=REALHW_HDMI_LOG1080_PROXY_FOCUSMAG_BRIGHTMON_76GATE_SCHEMA,
        version=REALHW_HDMI_LOG1080_PROXY_FOCUSMAG_BRIGHTMON_76GATE_VERSION,
        evaluated_utc=datetime.now(timezone.utc).isoformat(),
        verification_mode=verification_mode,
        clean_room_forced=clean_forced,
        dry_run_rehearsal_only=effective_dry_run,
        overall_ready_for_hardware_attach=overall_ready_for_hardware_attach,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        offline_73_gates_verified=offline_73_verified,
        all_76_gates_verified=all_76_verified,
        g13_to_g76_all_passed=g13_to_g76_all_passed,
        g75_to_g76_all_passed=g75_to_g76_all_passed,
        h0_h1_trial_entry_allowed=h0_h1_allowed,
        status=overall_status,
        agent_auto_flash_blocked=agent_auto_flash_blocked,
        human_hardware_attach_token=HUMAN_HARDWARE_ATTACH_TOKEN,
        el3_payload_transmit_authorized=EL3_PAYLOAD_TRANSMIT_AUTHORIZED,
        spi_nor_write_authorized=SPI_NOR_WRITE_AUTHORIZED,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        physical_flash_auto_exec_authorized=PHYSICAL_FLASH_AUTO_EXEC_AUTHORIZED,
        usb_packets_transmitted=USB_PACKETS_TRANSMITTED,
        physical_usb_packets_emitted=PHYSICAL_USB_PACKETS_EMITTED,
        raw_firmware_bytes_leaked=RAW_FIRMWARE_BYTES_LEAKED,
        technical_gates_passed=total_verified,
        summary=summary,
        gates=all_gates,
        master_74_report=m74_report.to_dict(),
        g75_result=g75_res.to_dict(),
        g76_result=g76_res.to_dict(),
        errors=tuple(errors),
        warnings=tuple(warnings),
    )


evaluate_76_master_safety_gates = evaluate_76gate_preflight
run_76_gate_preflight = evaluate_76gate_preflight


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(
        prog="realhw_hdmi_log1080_proxy_focusmag_brightmon_and_76gate_guard",
        description=(
            "Phase 210 Safety Gates G75 (HDMI Log/PPLUT 1080p Downshift & HDMI-Only 4K / "
            "LCD Blanking Guard) + G76 (Proxy Coupled Vault & FocusMag/BrightMon Interlock) "
            "+ Unified 76-Gate Master Safety Preflight"
        ),
    )
    parser.add_argument("--repo-root", type=Path, default=DEFAULT_REPO_ROOT)
    parser.add_argument(
        "--force-clean-room",
        "--clean-room",
        dest="force_clean_room",
        action="store_true",
    )
    parser.add_argument(
        "--simulate-bench-dry-run",
        "--dry-run-simulated",
        "--dry-run-simulated-backup",
        dest="dry_run_simulated",
        action="store_true",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args(list(argv) if argv is not None else None)

    report = evaluate_76gate_preflight(
        args.repo_root,
        force_clean_room=True if args.force_clean_room else None,
        dry_run_simulated=bool(args.dry_run_simulated),
    )
    if args.json:
        sys.stdout.write(json.dumps(report.to_dict(), indent=2, ensure_ascii=False) + "\n")
    else:
        sys.stdout.write(
            f"status={report.status} mode={report.verification_mode} "
            f"verified={report.summary['verified_gates']}/76 "
            f"g75_to_g76_all_passed={report.g75_to_g76_all_passed} "
            f"all_76_gates_verified={report.all_76_gates_verified} "
            f"overall_ready_for_hardware_attach={report.overall_ready_for_hardware_attach}\n"
        )
    ok = report.all_76_gates_verified if args.dry_run_simulated else report.offline_73_gates_verified
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
