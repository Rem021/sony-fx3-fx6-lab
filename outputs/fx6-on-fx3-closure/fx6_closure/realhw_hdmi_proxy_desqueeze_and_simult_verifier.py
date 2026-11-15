"""Phase 216 — Real-Hardware Physical Shoot & Monitoring Readiness Preflight (`preflight-hdmi-proxy-desqueeze-and-simult`).

Dedicated host-side read-only pre-shoot bench & media readiness verifier for physical Sony
`ILME-FX3` (`Ver. 7.02`, Model `0x91030080`), extending the operator bench preflight series
(`preflight-card-insert` -> `preflight-bench-cable-fan-slot1` ->
`preflight-hdmi-proxy-desqueeze-and-simult`) by synthesizing Waves 27–29 real-hardware
intelligence into 5 deterministic fail-closed checklists (`S1..S5`), bounded `O_RDONLY`
donor inspection (`< 0.15s`), and dual-media `528 B FX3RCPT1` Tier-0 receipt gating:

1. **Checklist 1 (`S1_DESQUEEZE_165X_4LOCKS_AND_EXTERNAL_MC_FOCUS_MAP`)**:
   - Verifies anamorphic `De-Squeeze Display` (`Off`, `1.3x`, `1.5x`, `1.6x -> actual 1.65x`,
     `1.8x`, `2.0x`), 4-setting locks (`Marker`, `FocusMag`, `AutoMagMF`, `FaceEyeAF`),
     movie `Initial Focus Mag.` (`x1.0`/`x4.0`) x `Bright Monitoring` mutual exclusion,
     4 auto-suppressions (`HDMI RAW`, `Off(HDMI Only)`, `Log Off`, `Remote`), zero in-body
     FX3 `Focus Map` menu/overlay, and external-only `Monitor & Control` Focus Map `< 150fps`.
2. **Checklist 2 (`S2_HDMI_LOG_1080P_DOWNSHIFT_VS_HDMIONLY_4K_AND_BLANK_LCD`)**:
   - Prevents accidental loss of internal card recording when `[Rec. Media dur HDMI Output]`
     is switched to `[Off(HDMI Only)]` for `4K 10-bit` HDMI Log output, enforces `1080p`
     downshift when `Log Shooting` / `PPLUT1..4` runs alongside internal card recording
     (non-RAW), and warns/gates built-in LCD blanking when `[HDMI Info. Display] = [On]`.
3. **Checklist 3 (`S3_DUAL_SLOT_SIMULT_AUTOSWITCH_AND_PX_PROXY_COUPLED_VAULT`)**:
   - Verifies dual-slot exFAT capacity/speed parity (`CFexpress-A` / `SDXC` vs `SDHC`),
     `Auto Switch Media` (`Off` strict `1:1` vault parity vs `On` rollover), `XAVC HS HD` /
     `XAVC S HD` `Px` proxy frame-rate cutoffs (`< 100p` / `< 100fps`), no in-camera proxy
     playback, and atomic `M4ROOT/CLIP/` + `M4ROOT/SUB/` Delete/Protect pairing.
4. **Checklist 4 (`S4_FILE_SETTINGS_37CHAR_SHOTMARK_XML_AND_TC_REGENERATE_SLOT1`)**:
   - Verifies `File Settings` (`37`-char ASCII Title, non-colliding `Series` counter, `SDHC`
     -> `[Standard]` hardware lock), `Shot Mark1/2` `*M01.XML` sidecars, `[Time Code Make] =
     [Regenerate]` Slot-1 master read + forced `[Rec Run]`, and `VMC-BNCM1` `EXT-LK`
     (`[Movie]` + `[Preset]` + `[Free Run]`) lock preservation.
5. **Checklist 5 (`S5_REC_LAMP_COUPLED_TALLY_SHOCKLESS_WB_AND_TIER0_RECEIPT_GATE`)**:
   - Verifies 3-state physical `[REC Lamp]` (`All On`, `Only Front Off` coupled Rear+Top
     tally, `All Off`), `[Silent Mode]` -> `[Audio signals] = Off` lock, `Shockless WB`
     `0`-frame Kelvin/grid behavior, `16/16 H0 == H3` parity, and offline fail-closed
     `BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT` (or `--simulate-bench-dry-run` ->
     `DRY_RUN_SIMULATED_PASS_NOT_PHYSICAL_AUTH`).

Hard-Locked Safety Invariants (UNCONDITIONAL):
- `hardware_live_attachment_authorized = False`
- `persistent_emmc_writes_authorized = False`
- `spi_nor_write_authorized = False`
- `el3_payload_transmit_authorized = False`
- `usb_packets_transmitted = 0` (`physical_usb_packets_emitted = 0`)
- `raw_firmware_bytes_leaked = 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
import stat
import time
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple
import zlib


def _ensure_cross_package_paths(repo_root: Path) -> None:
    for rel in (
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-firmware-lab",
        "outputs/fx3-vm",
        "outputs/fx6-on-fx3-closure",
    ):
        cand = str(repo_root / rel)
        if cand not in sys.path:
            sys.path.append(cand)


DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

from fx3_recovery.realhw_adjustcontrol_streaming_backup_client import (  # noqa: E402
    COLD_BACKUP_ITEMS,
    SD_RECEIPT_BYTES,
    build_sd_backup_receipt_bytes,
    parse_sd_backup_receipt_bytes,
)

from .donor_paths import is_forced_clean_room, resolve_work_subpath  # noqa: E402
from .hardware_readiness_packet import (  # noqa: E402
    BODY_SERIAL_RE,
    FORBIDDEN_TRIVIAL_CIDS,
    FORBIDDEN_TRIVIAL_SERIALS,
    HEX32_CID_RE,
    HEX64_RE,
)
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_WLAN_RSRC_DONOR_SHA256,
)
from .realhw_bench_cable_fan_and_slot1_verifier import (  # noqa: E402
    FX3_LIBUSBBUSPOWER_EXPECTED_SHA256,
    FX3_LIBUSBBUSPOWER_EXPECTED_SIZE,
    FX3_LIBUSBBUSPOWER_RELPATH,
)
from .realhw_card_insert_readiness_verifier import (  # noqa: E402
    DONOR_INSPECTION_MAX_SECONDS,
    EM_AARCH64,
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    MIN_BODY_FW_TUPLE,
    REQUIRED_H0_BASELINE_KEYS,
    TARGET_BODY_FW,
    TARGET_MODEL_ID_HEX,
    TARGET_MODEL_ID_INT,
    _parse_elf64_header_and_pt_load,
    _parse_fw_tuple,
    _read_bounded_slice_o_rdonly,
    build_default_h0_baselines,
)
from .realhw_jiritsu_and_tier0_dumper_auditor import (  # noqa: E402
    LIBJIRITSU_EXPECTED_SHA256,
    LIBJIRITSU_EXPECTED_SIZE,
    LIBJIRITSU_RELPATH,
)
from .realhw_sd_stageb_bundle_and_uninstaller import (  # noqa: E402
    DEFAULT_TARGET_BODY_SERIAL,
    DEFAULT_TARGET_EMMC_CID,
    FX3_IM_ELF_EXPECTED_SHA256,
    FX3_IM_ELF_EXPECTED_SIZE,
    FX3_IM_ELF_RELPATH,
    FX6_APPFW_EXPECTED_SIZE,
    SIXTEEN_STORAGE_SURFACES,
    read_only_o_rdonly_digest_and_header,
)

# ---------------------------------------------------------------------------
# Schema, Verdicts & Domain Constants
# ---------------------------------------------------------------------------

PHASE_216_SCHEMA: str = "phase216_realhw_hdmi_proxy_desqueeze_and_simult_preflight_v1"
PHASE_216_VERSION: str = "216.0.0"

GO_NO_GO_HDMI_PROXY_DESQUEEZE_SIMULT_VERIFIED: str = (
    "GO_HDMI_PROXY_DESQUEEZE_SIMULT_READONLY_PREFLIGHT_VERIFIED"
)
GO_NO_GO_BLOCKED_HDMI_PROXY_DESQUEEZE_SIMULT_FAILURE: str = (
    "BLOCKED_HDMI_PROXY_DESQUEEZE_SIMULT_CHECK_FAILURE"
)
PHASE_216_VALID_GO_NO_GO_VALUES: Tuple[str, ...] = (
    GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT,
    GO_NO_GO_BLOCKED_HDMI_PROXY_DESQUEEZE_SIMULT_FAILURE,
    GO_NO_GO_DRY_RUN_SIMULATED_READY,
    GO_NO_GO_HDMI_PROXY_DESQUEEZE_SIMULT_VERIFIED,
)

CHECKLIST_S1_ID: str = "S1_DESQUEEZE_165X_4LOCKS_AND_EXTERNAL_MC_FOCUS_MAP"
CHECKLIST_S2_ID: str = "S2_HDMI_LOG_1080P_DOWNSHIFT_VS_HDMIONLY_4K_AND_BLANK_LCD"
CHECKLIST_S3_ID: str = "S3_DUAL_SLOT_SIMULT_AUTOSWITCH_AND_PX_PROXY_COUPLED_VAULT"
CHECKLIST_S4_ID: str = "S4_FILE_SETTINGS_37CHAR_SHOTMARK_XML_AND_TC_REGENERATE_SLOT1"
CHECKLIST_S5_ID: str = "S5_REC_LAMP_COUPLED_TALLY_SHOCKLESS_WB_AND_TIER0_RECEIPT_GATE"
PHASE_216_CHECKLIST_IDS: Tuple[str, ...] = (
    CHECKLIST_S1_ID,
    CHECKLIST_S2_ID,
    CHECKLIST_S3_ID,
    CHECKLIST_S4_ID,
    CHECKLIST_S5_ID,
)

PHASE216_RAW_FIRMWARE_BYTES_LEAKED: int = 0

# Checklist 1: De-Squeeze (`1.6x = 1.65x`), 4-setting locks & External M&C Focus Map < 150fps
DESQUEEZE_RATIO_ACTUAL_FACTORS: Dict[str, float] = {
    "OFF": 1.0,
    "1.3X": 1.3,
    "1.5X": 1.5,
    "1.6X": 1.65,
    "1.8X": 1.8,
    "2.0X": 2.0,
}
DESQUEEZE_FOUR_SETTING_LOCKS: Tuple[str, ...] = (
    "Marker",
    "FocusMag",
    "AutoMagMF",
    "FaceEyeAF",
)
MOVIE_ALLOWED_INITIAL_FOCUS_MAG_SCALES: Tuple[str, ...] = ("X1.0", "X4.0")
MC_EXTERNAL_FOCUS_MAP_FPS_CEILING: float = 150.0
MC_EXTERNAL_FOCUS_MAP_MIN_FW_TUPLE: Tuple[int, int] = (6, 0)
DESQUEEZE_15X_16X_MIN_FW_TUPLE: Tuple[int, int] = (7, 0)

# Checklist 2: HDMI Log 1080p Downshift vs [Off(HDMI Only)] 4K 10-bit & Blank LCD
HDMI_REC_MEDIA_ON: str = "ON"
HDMI_REC_MEDIA_OFF_HDMI_ONLY: str = "OFF_HDMI_ONLY"
VALID_HDMI_REC_MEDIA_MODES: Tuple[str, ...] = (
    HDMI_REC_MEDIA_ON,
    HDMI_REC_MEDIA_OFF_HDMI_ONLY,
)
VALID_LOG_SHOOTING_MODES: Tuple[str, ...] = (
    "OFF",
    "CINE_EI",
    "CINE_EI_QUICK",
    "FLEXIBLE_ISO",
)
PPLUT_PICTURE_PROFILES: Tuple[str, ...] = ("PPLUT1", "PPLUT2", "PPLUT3", "PPLUT4")
VALID_HDMI_ONLY_4K_10BIT_FORMATS: Tuple[str, ...] = (
    "59.94P_10BIT",
    "50P_10BIT",
    "29.97P_10BIT",
    "25P_10BIT",
    "23.98P_10BIT",
    "24.00P_10BIT",
)
WARN_HDMI_INFO_DISPLAY_ON_BLANKS_LCD: str = "WARN_HDMI_INFO_DISPLAY_ON_BLANKS_BUILT_IN_LCD"

# Checklist 3: Dual-Slot Simult + Auto Switch Media & Px Proxy Coupled Vault
VALID_DUAL_SLOT_MEDIA_TYPES: Tuple[str, ...] = ("CFEXPRESS_A", "SDXC", "SDHC", "NONE")
EXFAT_CAPABLE_MEDIA_TYPES: Tuple[str, ...] = ("CFEXPRESS_A", "SDXC")
MEDIA_SPEED_TIERS: Dict[str, int] = {
    "NONE": 0,
    "V30": 30,
    "V60": 60,
    "V90": 90,
    "CFEXPRESS_A_VPG200": 200,
    "CFEXPRESS_A_VPG400": 400,
}
VALID_PROXY_FILE_FORMATS: Tuple[str, ...] = ("XAVC_HS_HD", "XAVC_S_HD")
PROXY_CUTOFF_FPS: float = 100.0
M4ROOT_CLIP_DIR: str = "/M4ROOT/CLIP/"
M4ROOT_SUB_DIR: str = "/M4ROOT/SUB/"

# Checklist 4: File Settings (37-Char / Series / SDHC), Shot Mark1/2 XML & TC Regenerate Slot-1
VALID_FILE_NAME_FORMATS: Tuple[str, ...] = (
    "STANDARD",
    "CAM_ID_PLUS_REEL",
    "TITLE",
    "DATE_PLUS_TITLE",
    "TITLE_PLUS_DATE",
)
VALID_FILE_NUMBER_MODES: Tuple[str, ...] = ("SERIES", "RESET")
TITLE_MAX_ASCII_CHARS: int = 37
TITLE_ALLOWED_RE = re.compile(r"^[A-Za-z0-9.\-_@!#$%+=^~(),;\[\]]{1,37}$")
CAM_ID_ALLOWED_RE = re.compile(r"^[A-Z]$")
VALID_IMAGE_JUMP_MODES: Tuple[str, ...] = (
    "SHOT_MARK_ONLY",
    "SHOT_MARK1_ONLY",
    "SHOT_MARK2_ONLY",
    "NO_SHOT_MARK",
)
VALID_TC_MAKE_MODES: Tuple[str, ...] = ("PRESET", "REGENERATE")
VALID_TC_RUN_MODES: Tuple[str, ...] = ("REC_RUN", "FREE_RUN")
VALID_SHOOT_MODES: Tuple[str, ...] = ("MOVIE", "S_AND_Q", "PHOTO")

# Checklist 5: Physical REC Lamp 3-State Coupled Tally, Silent Mode, Shockless WB & Tier-0 Gate
REC_LAMP_ALL_ON: str = "ALL_ON"
REC_LAMP_ONLY_FRONT_OFF: str = "ONLY_FRONT_OFF"
REC_LAMP_ALL_OFF: str = "ALL_OFF"
VALID_REC_LAMP_MODES: Tuple[str, ...] = (
    REC_LAMP_ALL_ON,
    REC_LAMP_ONLY_FRONT_OFF,
    REC_LAMP_ALL_OFF,
)
VALID_SHOCKLESS_WB_MODES: Tuple[str, ...] = ("OFF", "1", "2", "3")
WB_KELVIN_MIN_K: int = 2500
WB_KELVIN_MAX_K: int = 9900

# Error Codes
S1_ERR_MODEL_OR_FW_FLOOR: str = "S1_ERR_MODEL_OR_FW_FLOOR"
S1_ERR_UNSUPPORTED_DESQUEEZE_RATIO: str = "S1_ERR_UNSUPPORTED_DESQUEEZE_RATIO"
S1_ERR_DESQUEEZE_FOUR_SETTING_LOCK_VIOLATION: str = "S1_ERR_DESQUEEZE_FOUR_SETTING_LOCK_VIOLATION"
S1_ERR_DESQUEEZE_SUPPRESSED_STATE_CONFLICT: str = "S1_ERR_DESQUEEZE_SUPPRESSED_STATE_CONFLICT"
S1_ERR_FOCUS_MAG_OR_BRIGHT_MON_CONFLICT: str = "S1_ERR_FOCUS_MAG_OR_BRIGHT_MON_CONFLICT"
S1_ERR_IN_BODY_FOCUS_MAP_FORBIDDEN: str = "S1_ERR_IN_BODY_FOCUS_MAP_FORBIDDEN"
S1_ERR_MC_FOCUS_MAP_150FPS_OR_LENS_LIMIT: str = "S1_ERR_MC_FOCUS_MAP_150FPS_OR_LENS_LIMIT"

S2_ERR_UNSUPPORTED_HDMI_MODE_OR_FORMAT: str = "S2_ERR_UNSUPPORTED_HDMI_MODE_OR_FORMAT"
S2_ERR_HDMI_ONLY_DISABLES_INTERNAL_CARD_REC: str = "S2_ERR_HDMI_ONLY_DISABLES_INTERNAL_CARD_REC"
S2_ERR_HDMI_LOG_OR_PPLUT_FORCES_1080P_DOWNSHIFT: str = (
    "S2_ERR_HDMI_LOG_OR_PPLUT_FORCES_1080P_DOWNSHIFT"
)
S2_ERR_HDMI_INFO_DISPLAY_FORCED_OFF_CONFLICT: str = "S2_ERR_HDMI_INFO_DISPLAY_FORCED_OFF_CONFLICT"
S2_ERR_BUILT_IN_LCD_BLANKED_UNACKNOWLEDGED: str = "S2_ERR_BUILT_IN_LCD_BLANKED_UNACKNOWLEDGED"
S2_ERR_HDMI_ONLY_24P_REQUIRES_DCI_GATE: str = "S2_ERR_HDMI_ONLY_24P_REQUIRES_DCI_GATE"

S3_ERR_SIMULT_DUAL_SLOT_EXFAT_OR_PARITY: str = "S3_ERR_SIMULT_DUAL_SLOT_EXFAT_OR_PARITY"
S3_ERR_AUTO_SWITCH_BREAKS_STRICT_VAULT_PARITY: str = (
    "S3_ERR_AUTO_SWITCH_BREAKS_STRICT_VAULT_PARITY"
)
S3_ERR_PROXY_UNSUPPORTED_FORMAT_OR_CUTOFF_100FPS: str = (
    "S3_ERR_PROXY_UNSUPPORTED_FORMAT_OR_CUTOFF_100FPS"
)
S3_ERR_PROXY_IN_CAMERA_PLAYBACK_UNSUPPORTED: str = "S3_ERR_PROXY_IN_CAMERA_PLAYBACK_UNSUPPORTED"
S3_ERR_CLIP_SUB_COUPLED_DELETE_PROTECT_BROKEN: str = (
    "S3_ERR_CLIP_SUB_COUPLED_DELETE_PROTECT_BROKEN"
)

S4_ERR_FILE_SETTINGS_TITLE_OR_SERIES_COUNTER: str = (
    "S4_ERR_FILE_SETTINGS_TITLE_OR_SERIES_COUNTER"
)
S4_ERR_SDHC_FORCES_STANDARD_FILE_FORMAT: str = "S4_ERR_SDHC_FORCES_STANDARD_FILE_FORMAT"
S4_ERR_SHOT_MARK_XML_SIDECAR_MISMATCH: str = "S4_ERR_SHOT_MARK_XML_SIDECAR_MISMATCH"
S4_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION: str = (
    "S4_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION"
)
S4_ERR_VMC_BNCM1_EXT_LK_OR_SQ_TC_VIOLATION: str = "S4_ERR_VMC_BNCM1_EXT_LK_OR_SQ_TC_VIOLATION"

S5_ERR_REC_LAMP_COUPLED_REAR_TOP_VIOLATION: str = "S5_ERR_REC_LAMP_COUPLED_REAR_TOP_VIOLATION"
S5_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK: str = "S5_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK"
S5_ERR_SHOCKLESS_WB_ZERO_FRAME_KELVIN_GRID: str = "S5_ERR_SHOCKLESS_WB_ZERO_FRAME_KELVIN_GRID"
S5_ERR_H0_H3_IMMUTABILITY_DRIFT: str = "S5_ERR_H0_H3_IMMUTABILITY_DRIFT"
S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID: str = (
    "S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID"
)

_TRIVIAL_HEX64_SET = frozenset(
    {
        "0" * 64,
        "f" * 64,
        "a" * 64,
        "5" * 64,
        hashlib.sha256(b"").hexdigest(),
    }
)


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Phase216DonorInspectionResult:
    passed: bool
    verification_mode: str
    read_only_o_rdonly_enforced: bool
    elapsed_seconds: float
    within_150ms_budget: bool
    inspected_artifacts: Tuple[str, ...]
    fx3_im_elf_verified: bool
    fx3_libjiritsu_verified: bool
    fx3_libusbbuspower_verified: bool
    fx6_appfw_verified: bool
    fx6_wlan_rsrc_verified: bool
    fx3_upm_ko_verified: bool
    raw_firmware_bytes_leaked: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Checklist1DesqueezeAndMcFocusMapResult:
    checklist_id: str
    passed: bool
    body_model_id_hex: str
    body_fw: str
    desqueeze_ratio: str
    actual_desqueeze_factor: float
    effective_desqueeze_factor: float
    desqueeze_suppressed: bool
    suppression_reasons: Tuple[str, ...]
    four_setting_locks: Tuple[str, ...]
    four_setting_locks_satisfied: bool
    initial_focus_mag_scale: str
    bright_monitoring_compatible: bool
    in_body_focus_map_absent: bool
    mc_external_focus_map_enabled: bool
    mc_sensor_fps: float
    mc_focus_map_under_150fps: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Checklist2HdmiLogAndBlankLcdResult:
    checklist_id: str
    passed: bool
    rec_media_dur_hdmi_output: str
    internal_card_recording_active: bool
    log_shooting_mode: str
    picture_profile: str
    hdmi_raw_output: bool
    hdmi_only_4k_setting: str
    effective_hdmi_resolution: str
    log_or_pplut_1080p_downshift_active: bool
    hdmi_info_display: str
    effective_hdmi_info_display: str
    camera_lcd_blanked: bool
    warnings: Tuple[str, ...]
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Checklist3SimultAutoSwitchAndProxyVaultResult:
    checklist_id: str
    passed: bool
    simult_recording_enabled: bool
    auto_switch_media: str
    slot1_media_type: str
    slot2_media_type: str
    slot1_capacity_gb: int
    slot2_capacity_gb: int
    dual_slot_exfat_and_speed_parity_ok: bool
    strict_dual_vault_parity_preserved: bool
    proxy_recording_enabled: bool
    proxy_file_format: str
    rec_frame_rate_fps: float
    sq_mode_enabled: bool
    sq_frame_rate_fps: float
    proxy_under_100fps_cutoff: bool
    in_camera_proxy_playback_supported: bool
    m4root_clip_sub_coupled_delete_protect_ok: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Checklist4FileSettingsShotMarkAndTcSlot1Result:
    checklist_id: str
    passed: bool
    file_name_format: str
    file_number_mode: str
    title_name: str
    title_ascii_length: int
    cam_id: str
    reel_number: int
    sdhc_standard_lock_respected: bool
    shot_mark1_count: int
    shot_mark2_count: int
    shot_mark_xml_sidecar_verified: bool
    image_jump_setting: str
    shoot_mode: str
    tc_make: str
    requested_tc_run: str
    effective_tc_run: str
    tc_regenerate_slot1_master_verified: bool
    vmc_bncm1_ext_lk_required: bool
    vmc_bncm1_ext_lk_preserved: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class Checklist5RecLampShocklessWbAndTier0Result:
    checklist_id: str
    passed: bool
    rec_lamp_mode: str
    front_tally_lit: bool
    rear_tally_lit: bool
    top_rec_button_lit: bool
    rear_and_top_coupled: bool
    emphasized_rec_display_independent: bool
    silent_mode_enabled: bool
    audio_signals_mode: str
    shockless_wb_mode: str
    wb_kelvin_k: int
    kelvin_or_grid_transition_frames: int
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    tier0_receipt_present: bool
    tier0_receipt_verified: bool
    distinct_physical_media_verified: bool
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class RealHwHdmiProxyDesqueezeSimultReport:
    schema: str
    phase_version: str
    verification_mode: str
    simulate_bench_dry_run: bool
    go_no_go: str
    hardware_live_attachment_authorized: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    spi_nor_write_authorized: bool
    el3_payload_transmit_authorized: bool
    sd_physical_media_written: bool
    usb_packets_transmitted: int
    physical_usb_packets_emitted: int
    raw_firmware_bytes_leaked: int
    checklist_count: int
    checklists_passed: int
    all_5_operator_checklists_passed: bool
    tier0_receipt_verified: bool
    h0_h3_surface_count: int
    h0_equals_h3_count: int
    donor_inspection: Phase216DonorInspectionResult
    checklist_1_desqueeze_and_mc_focus_map: Checklist1DesqueezeAndMcFocusMapResult
    checklist_2_hdmi_log_and_blank_lcd: Checklist2HdmiLogAndBlankLcdResult
    checklist_3_simult_autoswitch_and_proxy_vault: Checklist3SimultAutoSwitchAndProxyVaultResult
    checklist_4_file_settings_shotmark_and_tc_slot1: Checklist4FileSettingsShotMarkAndTcSlot1Result
    checklist_5_reclamp_shockless_wb_and_tier0_gate: Checklist5RecLampShocklessWbAndTier0Result
    warnings: Tuple[str, ...]
    remediation_actions: Tuple[str, ...]
    errors: Tuple[str, ...]
    report_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class Phase216ReportVerifyResult:
    valid: bool
    errors: Tuple[str, ...]


# ---------------------------------------------------------------------------
# Internal Helpers
# ---------------------------------------------------------------------------


def _norm_token(raw: str) -> str:
    return re.sub(r"[\s\-]+", "_", str(raw).strip().upper())


def _canonical_sha256_dict(obj: Mapping[str, Any], exclude_key: Optional[str] = None) -> str:
    body = dict(copy.deepcopy(obj))
    if exclude_key:
        body.pop(exclude_key, None)
    donor_sub = body.get("donor_inspection")
    if isinstance(donor_sub, dict):
        donor_sub.pop("elapsed_seconds", None)
    raw = json.dumps(body, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode(
        "utf-8"
    )
    return hashlib.sha256(raw).hexdigest()


def _is_trivial_hex64(val: str) -> bool:
    norm = str(val).strip().lower()
    if not HEX64_RE.match(norm):
        return True
    return norm in _TRIVIAL_HEX64_SET


# ---------------------------------------------------------------------------
# Bounded O_RDONLY Donor Inspection (< 0.15s) + Clean-Room Synthetic Fallback
# ---------------------------------------------------------------------------


def inspect_phase216_donors_bounded(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    max_seconds: float = DONOR_INSPECTION_MAX_SECONDS,
) -> Phase216DonorInspectionResult:
    """Inspect local BYOF donors strictly via O_RDONLY within < 0.15s, or Clean-Room fallback."""
    t0 = time.perf_counter()
    errors: List[str] = []
    eff_clean = force_clean_room if force_clean_room is not None else synthetic_clean_room
    clean_room = is_forced_clean_room() if eff_clean is None else bool(eff_clean)

    fx3_im_path = resolve_work_subpath(FX3_IM_ELF_RELPATH, require_file=False)
    fx3_jit_path = resolve_work_subpath(LIBJIRITSU_RELPATH, require_file=False)
    fx3_usb_pwr_path = resolve_work_subpath(FX3_LIBUSBBUSPOWER_RELPATH, require_file=False)
    fx6_appfw_path = fx6_lib_dir / "appFw.so"
    fx6_wlan_path = fx6_lib_dir / "libWlanResource.so"
    fx3_upm_path = fx3_modules_dir / "upm.ko"

    donors_present = (
        fx3_im_path.is_file()
        and fx3_jit_path.is_file()
        and fx3_usb_pwr_path.is_file()
        and fx6_appfw_path.is_file()
        and fx6_wlan_path.is_file()
        and fx3_upm_path.is_file()
    )

    if eff_clean is False and not donors_present:
        elapsed = round(time.perf_counter() - t0, 6)
        return Phase216DonorInspectionResult(
            passed=False,
            verification_mode="LOCAL_DONOR_O_RDONLY",
            read_only_o_rdonly_enforced=True,
            elapsed_seconds=elapsed,
            within_150ms_budget=(elapsed < max_seconds),
            inspected_artifacts=(),
            fx3_im_elf_verified=fx3_im_path.is_file(),
            fx3_libjiritsu_verified=fx3_jit_path.is_file(),
            fx3_libusbbuspower_verified=fx3_usb_pwr_path.is_file(),
            fx6_appfw_verified=fx6_appfw_path.is_file(),
            fx6_wlan_rsrc_verified=fx6_wlan_path.is_file(),
            fx3_upm_ko_verified=fx3_upm_path.is_file(),
            raw_firmware_bytes_leaked=PHASE216_RAW_FIRMWARE_BYTES_LEAKED,
            errors=(f"Local BYOF donors missing under fx6_lib_dir={fx6_lib_dir}",),
        )

    use_live = (not clean_room) and donors_present
    mode = "LOCAL_DONOR_O_RDONLY" if use_live else "CLEAN_ROOM_SYNTHETIC"
    inspected: List[str] = []

    if use_live:
        im_sz, im_sha, im_head = read_only_o_rdonly_digest_and_header(fx3_im_path)
        im_mag, im_64, im_mach, _ = _parse_elf64_header_and_pt_load(im_head)
        im_ok = (
            im_sz == FX3_IM_ELF_EXPECTED_SIZE
            and im_sha == FX3_IM_ELF_EXPECTED_SHA256
            and im_mag
            and im_64
            and im_mach == EM_AARCH64
        )
        inspected.append("im.elf")
        if not im_ok:
            errors.append(f"im.elf O_RDONLY verification failed: size={im_sz}")

        jit_sz, jit_sha, jit_head = read_only_o_rdonly_digest_and_header(fx3_jit_path)
        jit_mag, jit_64, jit_mach, _ = _parse_elf64_header_and_pt_load(jit_head)
        jit_ok = (
            jit_sz == LIBJIRITSU_EXPECTED_SIZE
            and jit_sha == LIBJIRITSU_EXPECTED_SHA256
            and jit_mag
            and jit_64
            and jit_mach == EM_AARCH64
        )
        inspected.append("libJiritsu.so")
        if not jit_ok:
            errors.append(f"libJiritsu.so O_RDONLY verification failed: size={jit_sz}")

        pwr_sz, pwr_sha, pwr_head = read_only_o_rdonly_digest_and_header(fx3_usb_pwr_path)
        pwr_mag, pwr_64, pwr_mach, _ = _parse_elf64_header_and_pt_load(pwr_head)
        pwr_ok = (
            pwr_sz == FX3_LIBUSBBUSPOWER_EXPECTED_SIZE
            and pwr_sha == FX3_LIBUSBBUSPOWER_EXPECTED_SHA256
            and pwr_mag
            and pwr_64
            and pwr_mach == EM_AARCH64
        )
        inspected.append("libUsbBusPower.so")
        if not pwr_ok:
            errors.append(f"libUsbBusPower.so O_RDONLY verification failed: size={pwr_sz}")

        appfw_sz, appfw_head, _ = _read_bounded_slice_o_rdonly(fx6_appfw_path, 4096)
        appfw_mag, appfw_64, appfw_mach, _ = _parse_elf64_header_and_pt_load(appfw_head)
        appfw_ok = (
            appfw_sz == FX6_APPFW_EXPECTED_SIZE
            and appfw_mag
            and appfw_64
            and appfw_mach == EM_AARCH64
        )
        inspected.append("appFw.so(bounded-4KiB)")
        if not appfw_ok:
            errors.append(f"appFw.so bounded O_RDONLY header failed: size={appfw_sz}")

        wlan_sz, wlan_sha, wlan_head = read_only_o_rdonly_digest_and_header(fx6_wlan_path)
        wlan_mag, wlan_64, wlan_mach, _ = _parse_elf64_header_and_pt_load(wlan_head)
        wlan_ok = (
            wlan_sz > 0
            and wlan_sha == FX6_WLAN_RSRC_DONOR_SHA256
            and wlan_mag
            and wlan_64
            and wlan_mach == EM_AARCH64
        )
        inspected.append("libWlanResource.so")
        if not wlan_ok:
            errors.append("libWlanResource.so O_RDONLY SHA-256 verification failed")

        upm_sz, upm_head, _ = _read_bounded_slice_o_rdonly(fx3_upm_path, 4096)
        upm_mag, upm_64, upm_mach, _ = _parse_elf64_header_and_pt_load(upm_head)
        upm_ok = upm_sz > 0 and upm_mag and upm_64 and upm_mach == EM_AARCH64
        inspected.append("upm.ko(bounded-4KiB)")
        if not upm_ok:
            errors.append(f"upm.ko bounded O_RDONLY header failed: size={upm_sz}")
    else:
        im_ok = jit_ok = pwr_ok = appfw_ok = wlan_ok = upm_ok = True
        inspected.extend(
            [
                "synthetic:im.elf",
                "synthetic:libJiritsu.so",
                "synthetic:libUsbBusPower.so",
                "synthetic:appFw.so",
                "synthetic:libWlanResource.so",
                "synthetic:upm.ko",
            ]
        )

    elapsed = round(time.perf_counter() - t0, 6)
    within_budget = elapsed < max_seconds
    if not within_budget:
        errors.append(f"Donor inspection exceeded {max_seconds:.3f}s budget: {elapsed:.6f}s")

    return Phase216DonorInspectionResult(
        passed=(len(errors) == 0),
        verification_mode=mode,
        read_only_o_rdonly_enforced=True,
        elapsed_seconds=elapsed,
        within_150ms_budget=within_budget,
        inspected_artifacts=tuple(inspected),
        fx3_im_elf_verified=im_ok,
        fx3_libjiritsu_verified=jit_ok,
        fx3_libusbbuspower_verified=pwr_ok,
        fx6_appfw_verified=appfw_ok,
        fx6_wlan_rsrc_verified=wlan_ok,
        fx3_upm_ko_verified=upm_ok,
        raw_firmware_bytes_leaked=PHASE216_RAW_FIRMWARE_BYTES_LEAKED,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Checklist 1: De-Squeeze (`1.6x=1.65x`), 4-Setting Locks & External M&C Focus Map
# ---------------------------------------------------------------------------


def evaluate_checklist_1_desqueeze_and_mc_focus_map(
    *,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    desqueeze_ratio: str = "OFF",
    marker_display_locked_off: bool = True,
    focus_magnifier_locked_off: bool = True,
    auto_mag_mf_locked_off: bool = True,
    face_eye_af_locked_off: bool = True,
    hdmi_raw_output: bool = False,
    rec_media_dur_hdmi_output: str = HDMI_REC_MEDIA_ON,
    log_shooting_mode: str = "CINE_EI",
    remote_shooting_active: bool = False,
    expect_active_desqueeze_under_suppression: bool = False,
    initial_focus_mag_scale: str = "x4.0",
    focus_magnifier_active: bool = False,
    bright_monitoring_active: bool = False,
    in_body_focus_map_menu_present: bool = False,
    in_body_focus_map_overlay_injected: bool = False,
    mc_external_focus_map_enabled: bool = False,
    mc_sensor_fps: float = 23.98,
    mc_pdaf_compatible_lens: bool = True,
    camera_in_playback: bool = False,
) -> Checklist1DesqueezeAndMcFocusMapResult:
    errors: List[str] = []
    fw_clean = str(body_fw).strip()
    fw_tuple = _parse_fw_tuple(fw_clean)
    if (
        int(body_model_id) != TARGET_MODEL_ID_INT
        or fw_tuple is None
        or fw_tuple < MIN_BODY_FW_TUPLE
        or fw_clean != TARGET_BODY_FW
    ):
        errors.append(
            f"{S1_ERR_MODEL_OR_FW_FLOOR}: expected ILME-FX3 {TARGET_MODEL_ID_HEX} fw={TARGET_BODY_FW}, "
            f"got 0x{int(body_model_id) & 0xFFFFFFFF:08x} fw={fw_clean!r}"
        )

    ratio_norm = str(desqueeze_ratio).strip().upper()
    if ratio_norm == "1.6X(1.65X)":
        ratio_norm = "1.6X"
    if ratio_norm not in DESQUEEZE_RATIO_ACTUAL_FACTORS:
        errors.append(
            f"{S1_ERR_UNSUPPORTED_DESQUEEZE_RATIO}: unsupported De-Squeeze Display ratio {desqueeze_ratio!r}"
        )
        actual_factor = 1.0
    else:
        actual_factor = DESQUEEZE_RATIO_ACTUAL_FACTORS[ratio_norm]
        if ratio_norm in ("1.5X", "1.6X") and (
            fw_tuple is None or fw_tuple < DESQUEEZE_15X_16X_MIN_FW_TUPLE
        ):
            errors.append(
                f"{S1_ERR_MODEL_OR_FW_FLOOR}: De-Squeeze {ratio_norm} requires FX3 fw >= 7.00"
            )

    suppression_reasons: List[str] = []
    rec_media_norm = _norm_token(rec_media_dur_hdmi_output)
    log_norm = _norm_token(log_shooting_mode)
    if hdmi_raw_output:
        suppression_reasons.append("HDMI_RAW_OUTPUT_ACTIVE")
    if rec_media_norm == HDMI_REC_MEDIA_OFF_HDMI_ONLY:
        suppression_reasons.append("OFF_HDMI_ONLY_INFO_DISPLAY_FORCED_OFF")
    if log_norm == "OFF":
        suppression_reasons.append("LOG_SHOOTING_OFF")
    if remote_shooting_active:
        suppression_reasons.append("REMOTE_SHOOTING_ACTIVE")

    desqueeze_requested = ratio_norm != "OFF" and ratio_norm in DESQUEEZE_RATIO_ACTUAL_FACTORS
    desqueeze_suppressed = bool(desqueeze_requested and len(suppression_reasons) > 0)
    effective_factor = 1.0 if (not desqueeze_requested or desqueeze_suppressed) else actual_factor

    if desqueeze_suppressed and expect_active_desqueeze_under_suppression:
        errors.append(
            f"{S1_ERR_DESQUEEZE_SUPPRESSED_STATE_CONFLICT}: De-Squeeze {ratio_norm} is suppressed by "
            f"{','.join(suppression_reasons)} (effective 1.0x)"
        )

    locks_ok = True
    if desqueeze_requested and not desqueeze_suppressed:
        if not (
            marker_display_locked_off
            and focus_magnifier_locked_off
            and auto_mag_mf_locked_off
            and face_eye_af_locked_off
        ):
            locks_ok = False
            errors.append(
                f"{S1_ERR_DESQUEEZE_FOUR_SETTING_LOCK_VIOLATION}: active De-Squeeze {ratio_norm} "
                "requires Marker/FocusMag/AutoMagMF/FaceEyeAF locked off"
            )

    mag_norm = str(initial_focus_mag_scale).strip().upper()
    bright_ok = True
    if mag_norm not in MOVIE_ALLOWED_INITIAL_FOCUS_MAG_SCALES:
        bright_ok = False
        errors.append(
            f"{S1_ERR_FOCUS_MAG_OR_BRIGHT_MON_CONFLICT}: movie [Initial Focus Mag.] only allows "
            f"x1.0/x4.0, got {initial_focus_mag_scale!r}"
        )
    if focus_magnifier_active and bright_monitoring_active:
        bright_ok = False
        errors.append(
            f"{S1_ERR_FOCUS_MAG_OR_BRIGHT_MON_CONFLICT}: Focus Magnifier and Bright Monitoring "
            "cannot be active simultaneously"
        )

    in_body_absent = (not in_body_focus_map_menu_present) and (
        not in_body_focus_map_overlay_injected
    )
    if not in_body_absent:
        errors.append(
            f"{S1_ERR_IN_BODY_FOCUS_MAP_FORBIDDEN}: ILME-FX3 has zero in-body [Focus Map] menu/OSD"
        )

    fps_val = float(mc_sensor_fps)
    under_150 = 0.0 < fps_val < MC_EXTERNAL_FOCUS_MAP_FPS_CEILING
    if mc_external_focus_map_enabled:
        if (
            not under_150
            or not mc_pdaf_compatible_lens
            or camera_in_playback
            or fw_tuple is None
            or fw_tuple < MC_EXTERNAL_FOCUS_MAP_MIN_FW_TUPLE
        ):
            errors.append(
                f"{S1_ERR_MC_FOCUS_MAP_150FPS_OR_LENS_LIMIT}: Monitor & Control external Focus Map "
                f"requires fw>=6.00, PDAF lens, live view, and <150.0fps (got fps={fps_val})"
            )

    return Checklist1DesqueezeAndMcFocusMapResult(
        checklist_id=CHECKLIST_S1_ID,
        passed=(len(errors) == 0),
        body_model_id_hex=f"0x{int(body_model_id) & 0xFFFFFFFF:08x}",
        body_fw=fw_clean,
        desqueeze_ratio=ratio_norm,
        actual_desqueeze_factor=actual_factor,
        effective_desqueeze_factor=effective_factor,
        desqueeze_suppressed=desqueeze_suppressed,
        suppression_reasons=tuple(suppression_reasons),
        four_setting_locks=DESQUEEZE_FOUR_SETTING_LOCKS,
        four_setting_locks_satisfied=locks_ok,
        initial_focus_mag_scale=mag_norm,
        bright_monitoring_compatible=bright_ok,
        in_body_focus_map_absent=in_body_absent,
        mc_external_focus_map_enabled=bool(mc_external_focus_map_enabled),
        mc_sensor_fps=fps_val,
        mc_focus_map_under_150fps=under_150,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Checklist 2: HDMI Log 1080p Downshift vs [Off(HDMI Only)] 4K 10-bit & Blank LCD
# ---------------------------------------------------------------------------


def evaluate_checklist_2_hdmi_log_and_blank_lcd(
    *,
    rec_media_dur_hdmi_output: str = HDMI_REC_MEDIA_ON,
    require_internal_card_recording: bool = True,
    ack_hdmi_only_no_internal_card_rec: bool = False,
    log_shooting_mode: str = "CINE_EI",
    picture_profile: str = "OFF",
    hdmi_raw_output: bool = False,
    hdmi_output_resolution: str = "AUTO",
    hdmi_only_4k_setting: str = "23.98P_10BIT",
    dci_4k_24p_mode: bool = False,
    expected_hdmi_4k_with_internal_rec_and_log: bool = False,
    hdmi_info_display: str = "OFF",
    require_unblanked_camera_lcd: bool = True,
) -> Checklist2HdmiLogAndBlankLcdResult:
    errors: List[str] = []
    warnings: List[str] = []

    rec_norm = _norm_token(rec_media_dur_hdmi_output)
    if rec_norm in ("OFF(HDMI_ONLY)", "HDMI_ONLY"):
        rec_norm = HDMI_REC_MEDIA_OFF_HDMI_ONLY
    if rec_norm not in VALID_HDMI_REC_MEDIA_MODES:
        errors.append(
            f"{S2_ERR_UNSUPPORTED_HDMI_MODE_OR_FORMAT}: invalid [Rec. Media dur HDMI Output]={rec_media_dur_hdmi_output!r}"
        )

    log_norm = _norm_token(log_shooting_mode)
    if log_norm not in VALID_LOG_SHOOTING_MODES:
        errors.append(
            f"{S2_ERR_UNSUPPORTED_HDMI_MODE_OR_FORMAT}: invalid [Log Shooting]={log_shooting_mode!r}"
        )

    pp_norm = _norm_token(picture_profile)
    hdmi_4k_norm = _norm_token(hdmi_only_4k_setting)
    if rec_norm == HDMI_REC_MEDIA_OFF_HDMI_ONLY:
        if hdmi_4k_norm not in VALID_HDMI_ONLY_4K_10BIT_FORMATS:
            errors.append(
                f"{S2_ERR_UNSUPPORTED_HDMI_MODE_OR_FORMAT}: invalid [4K Output Set.(HDMI Only)]={hdmi_only_4k_setting!r}"
            )
        if hdmi_4k_norm == "24.00P_10BIT" and not dci_4k_24p_mode:
            errors.append(
                f"{S2_ERR_HDMI_ONLY_24P_REQUIRES_DCI_GATE}: 24.00p 10bit HDMI Only output requires DCI 4K 24.00p gate"
            )

    internal_rec_active = rec_norm == HDMI_REC_MEDIA_ON
    if rec_norm == HDMI_REC_MEDIA_OFF_HDMI_ONLY and (
        require_internal_card_recording or not ack_hdmi_only_no_internal_card_rec
    ):
        errors.append(
            f"{S2_ERR_HDMI_ONLY_DISABLES_INTERNAL_CARD_REC}: [Off(HDMI Only)] disables internal Slot-1/Slot-2 "
            "card recording; keep [Rec. Media dur HDMI Output]=[On] or explicitly acknowledge external-only capture"
        )

    log_or_pplut = (log_norm != "OFF") or (pp_norm in PPLUT_PICTURE_PROFILES)
    downshift_1080p = bool(internal_rec_active and (not hdmi_raw_output) and log_or_pplut)
    if hdmi_raw_output:
        effective_res = "4264X2408_RAW16"
    elif rec_norm == HDMI_REC_MEDIA_OFF_HDMI_ONLY:
        effective_res = "2160P_10BIT_HDMI_ONLY"
    elif downshift_1080p:
        effective_res = "1080P"
    else:
        res_norm = _norm_token(hdmi_output_resolution)
        effective_res = "2160P" if res_norm in ("AUTO", "2160P", "2160P_1080P") else res_norm

    if downshift_1080p and expected_hdmi_4k_with_internal_rec_and_log:
        errors.append(
            f"{S2_ERR_HDMI_LOG_OR_PPLUT_FORCES_1080P_DOWNSHIFT}: simultaneous internal card rec + non-RAW "
            "Log/PPLUT downshifts HDMI output to 1080p"
        )

    info_norm = _norm_token(hdmi_info_display)
    if info_norm not in ("ON", "OFF"):
        errors.append(
            f"{S2_ERR_UNSUPPORTED_HDMI_MODE_OR_FORMAT}: invalid [HDMI Info. Display]={hdmi_info_display!r}"
        )

    forced_info_off = (rec_norm == HDMI_REC_MEDIA_OFF_HDMI_ONLY) or bool(hdmi_raw_output)
    if forced_info_off and info_norm == "ON":
        errors.append(
            f"{S2_ERR_HDMI_INFO_DISPLAY_FORCED_OFF_CONFLICT}: [HDMI Info. Display] is hardware-locked to [Off] "
            "when [Off(HDMI Only)] or [RAW Output] is enabled"
        )
    effective_info = "OFF" if forced_info_off else info_norm

    lcd_blanked = bool(effective_info == "ON")
    if lcd_blanked:
        warnings.append(WARN_HDMI_INFO_DISPLAY_ON_BLANKS_LCD)
        if require_unblanked_camera_lcd:
            errors.append(
                f"{S2_ERR_BUILT_IN_LCD_BLANKED_UNACKNOWLEDGED}: [HDMI Info. Display]=[On] blanks the built-in "
                "camera LCD panel; set [HDMI Info. Display]=[Off] to retain dual clean-HDMI + camera OSD"
            )

    return Checklist2HdmiLogAndBlankLcdResult(
        checklist_id=CHECKLIST_S2_ID,
        passed=(len(errors) == 0),
        rec_media_dur_hdmi_output=rec_norm,
        internal_card_recording_active=internal_rec_active,
        log_shooting_mode=log_norm,
        picture_profile=pp_norm,
        hdmi_raw_output=bool(hdmi_raw_output),
        hdmi_only_4k_setting=hdmi_4k_norm,
        effective_hdmi_resolution=effective_res,
        log_or_pplut_1080p_downshift_active=downshift_1080p,
        hdmi_info_display=info_norm,
        effective_hdmi_info_display=effective_info,
        camera_lcd_blanked=lcd_blanked,
        warnings=tuple(warnings),
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Checklist 3: Dual-Slot Simult + Auto Switch Media & Px Proxy Coupled Vault
# ---------------------------------------------------------------------------


def evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
    *,
    simult_recording_enabled: bool = True,
    auto_switch_media: str = "OFF",
    require_strict_dual_vault_parity: bool = True,
    slot1_media_type: str = "CFEXPRESS_A",
    slot2_media_type: str = "CFEXPRESS_A",
    slot1_capacity_gb: int = 160,
    slot2_capacity_gb: int = 160,
    slot1_speed_tier: str = "CFEXPRESS_A_VPG400",
    slot2_speed_tier: str = "CFEXPRESS_A_VPG400",
    required_min_speed_tier: str = "V90",
    proxy_recording_enabled: bool = True,
    proxy_file_format: str = "XAVC_HS_HD",
    rec_frame_rate_fps: float = 23.98,
    sq_mode_enabled: bool = False,
    sq_frame_rate_fps: float = 60.0,
    rec_media_dur_hdmi_output: str = HDMI_REC_MEDIA_ON,
    expect_in_camera_proxy_playback: bool = False,
    clip_sub_delete_coupled: bool = True,
    clip_sub_protect_coupled: bool = True,
    orphan_clip_or_sub_count: int = 0,
) -> Checklist3SimultAutoSwitchAndProxyVaultResult:
    errors: List[str] = []
    s1_media = _norm_token(slot1_media_type)
    s2_media = _norm_token(slot2_media_type)
    autosw_norm = _norm_token(auto_switch_media)
    s1_speed = _norm_token(slot1_speed_tier)
    s2_speed = _norm_token(slot2_speed_tier)
    min_speed = _norm_token(required_min_speed_tier)

    if (
        s1_media not in VALID_DUAL_SLOT_MEDIA_TYPES
        or s2_media not in VALID_DUAL_SLOT_MEDIA_TYPES
        or autosw_norm not in ("ON", "OFF")
        or s1_speed not in MEDIA_SPEED_TIERS
        or s2_speed not in MEDIA_SPEED_TIERS
        or min_speed not in MEDIA_SPEED_TIERS
    ):
        errors.append(
            f"{S3_ERR_SIMULT_DUAL_SLOT_EXFAT_OR_PARITY}: invalid dual-slot media/speed/AutoSwitch parameter"
        )

    min_tier_val = MEDIA_SPEED_TIERS.get(min_speed, 90)
    dual_parity_ok = True
    if simult_recording_enabled:
        s1_exfat = s1_media in EXFAT_CAPABLE_MEDIA_TYPES
        s2_exfat = s2_media in EXFAT_CAPABLE_MEDIA_TYPES
        speed_ok = (
            MEDIA_SPEED_TIERS.get(s1_speed, 0) >= min_tier_val
            and MEDIA_SPEED_TIERS.get(s2_speed, 0) >= min_tier_val
        )
        cap_ok = (
            int(slot1_capacity_gb) >= 64
            and int(slot2_capacity_gb) >= 64
            and (int(slot1_capacity_gb) == int(slot2_capacity_gb) or autosw_norm == "ON")
        )
        if not (s1_exfat and s2_exfat and speed_ok and cap_ok):
            dual_parity_ok = False
            errors.append(
                f"{S3_ERR_SIMULT_DUAL_SLOT_EXFAT_OR_PARITY}: Simult. Recording requires dual exFAT "
                f"(CFexpress-A/SDXC >=64GB, parity capacity, speed>={min_speed}); got "
                f"Slot1={s1_media}/{slot1_capacity_gb}GB/{s1_speed}, Slot2={s2_media}/{slot2_capacity_gb}GB/{s2_speed}"
            )

    strict_vault_ok = True
    if simult_recording_enabled and require_strict_dual_vault_parity and autosw_norm != "OFF":
        strict_vault_ok = False
        errors.append(
            f"{S3_ERR_AUTO_SWITCH_BREAKS_STRICT_VAULT_PARITY}: [Auto Switch Media]=[On] rolls over to "
            "single-card non-redundant recording when one slot fills; set [Auto Switch Media]=[Off] for 1:1 dual vault"
        )

    px_fmt = _norm_token(proxy_file_format)
    rec_fps = float(rec_frame_rate_fps)
    sq_fps = float(sq_frame_rate_fps)
    rec_media_norm = _norm_token(rec_media_dur_hdmi_output)
    under_100fps = (rec_fps < PROXY_CUTOFF_FPS) and (
        (not sq_mode_enabled) or (sq_fps < PROXY_CUTOFF_FPS)
    )
    if proxy_recording_enabled:
        if px_fmt not in VALID_PROXY_FILE_FORMATS:
            errors.append(
                f"{S3_ERR_PROXY_UNSUPPORTED_FORMAT_OR_CUTOFF_100FPS}: unsupported proxy format {proxy_file_format!r}"
            )
        if not under_100fps or rec_media_norm == HDMI_REC_MEDIA_OFF_HDMI_ONLY:
            errors.append(
                f"{S3_ERR_PROXY_UNSUPPORTED_FORMAT_OR_CUTOFF_100FPS}: Px proxy recording is disabled at "
                f">=100p / S&Q >=100fps or under [Off(HDMI Only)] (rec_fps={rec_fps}, sq={sq_mode_enabled}/{sq_fps})"
            )

    if expect_in_camera_proxy_playback:
        errors.append(
            f"{S3_ERR_PROXY_IN_CAMERA_PLAYBACK_UNSUPPORTED}: M4ROOT/SUB proxy MP4 clips cannot be played back in-camera"
        )

    coupled_ok = (
        bool(clip_sub_delete_coupled)
        and bool(clip_sub_protect_coupled)
        and int(orphan_clip_or_sub_count) == 0
    )
    if not coupled_ok:
        errors.append(
            f"{S3_ERR_CLIP_SUB_COUPLED_DELETE_PROTECT_BROKEN}: M4ROOT/CLIP + M4ROOT/SUB Delete/Protect "
            f"must remain atomically paired (orphans={orphan_clip_or_sub_count})"
        )

    return Checklist3SimultAutoSwitchAndProxyVaultResult(
        checklist_id=CHECKLIST_S3_ID,
        passed=(len(errors) == 0),
        simult_recording_enabled=bool(simult_recording_enabled),
        auto_switch_media=autosw_norm,
        slot1_media_type=s1_media,
        slot2_media_type=s2_media,
        slot1_capacity_gb=int(slot1_capacity_gb),
        slot2_capacity_gb=int(slot2_capacity_gb),
        dual_slot_exfat_and_speed_parity_ok=dual_parity_ok,
        strict_dual_vault_parity_preserved=strict_vault_ok,
        proxy_recording_enabled=bool(proxy_recording_enabled),
        proxy_file_format=px_fmt,
        rec_frame_rate_fps=rec_fps,
        sq_mode_enabled=bool(sq_mode_enabled),
        sq_frame_rate_fps=sq_fps,
        proxy_under_100fps_cutoff=under_100fps,
        in_camera_proxy_playback_supported=False,
        m4root_clip_sub_coupled_delete_protect_ok=coupled_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Checklist 4: File Settings (37-Char / Series / SDHC), Shot Mark XML & TC Slot-1
# ---------------------------------------------------------------------------


def evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
    *,
    file_name_format: str = "CAM_ID_PLUS_REEL",
    file_number_mode: str = "SERIES",
    require_series_counter: bool = True,
    title_name: str = "FX3_BENCH_A",
    cam_id: str = "A",
    reel_number: int = 1,
    slot1_media_type: str = "CFEXPRESS_A",
    slot2_media_type: str = "CFEXPRESS_A",
    custom_folder_name_requested: bool = False,
    shot_mark1_count: int = 1,
    shot_mark2_count: int = 1,
    shot_mark_xml_sidecar_enabled: bool = True,
    image_jump_setting: str = "SHOT_MARK_ONLY",
    shoot_mode: str = "MOVIE",
    tc_make: str = "PRESET",
    tc_run: str = "FREE_RUN",
    tc_regenerate_reference_slot: int = 1,
    expect_free_run_under_regenerate: bool = False,
    vmc_bncm1_ext_lk_required: bool = False,
    hdmi_tc_output_expected_in_sq: bool = False,
) -> Checklist4FileSettingsShotMarkAndTcSlot1Result:
    errors: List[str] = []
    fmt_norm = _norm_token(file_name_format).replace("REEL#", "REEL").replace("_+_", "_PLUS_")
    num_norm = _norm_token(file_number_mode)
    title_str = str(title_name)
    cam_str = str(cam_id).strip().upper()
    reel_int = int(reel_number)

    if fmt_norm not in VALID_FILE_NAME_FORMATS:
        errors.append(
            f"{S4_ERR_FILE_SETTINGS_TITLE_OR_SERIES_COUNTER}: unsupported [File Name Format]={file_name_format!r}"
        )
    if num_norm not in VALID_FILE_NUMBER_MODES or (require_series_counter and num_norm != "SERIES"):
        errors.append(
            f"{S4_ERR_FILE_SETTINGS_TITLE_OR_SERIES_COUNTER}: [File Number] must be non-colliding SERIES, got {file_number_mode!r}"
        )
    if len(title_str) > TITLE_MAX_ASCII_CHARS or not TITLE_ALLOWED_RE.match(title_str):
        errors.append(
            f"{S4_ERR_FILE_SETTINGS_TITLE_OR_SERIES_COUNTER}: [Title Name Settings] must be 1..37 allowed ASCII chars, "
            f"got len={len(title_str)} {title_str!r}"
        )
    if not CAM_ID_ALLOWED_RE.match(cam_str) or not (1 <= reel_int <= 999):
        errors.append(
            f"{S4_ERR_FILE_SETTINGS_TITLE_OR_SERIES_COUNTER}: invalid Cam ID ({cam_id!r}) or Reel# ({reel_number})"
        )

    s1_media = _norm_token(slot1_media_type)
    s2_media = _norm_token(slot2_media_type)
    sdhc_present = "SDHC" in (s1_media, s2_media)
    sdhc_ok = True
    if sdhc_present and (fmt_norm != "STANDARD" or custom_folder_name_requested):
        sdhc_ok = False
        errors.append(
            f"{S4_ERR_SDHC_FORCES_STANDARD_FILE_FORMAT}: inserting SDHC media locks [File Name Format] to [Standard] "
            "and disables custom folder names"
        )

    jump_norm = _norm_token(image_jump_setting)
    has_marks = (int(shot_mark1_count) > 0) or (int(shot_mark2_count) > 0)
    xml_ok = (
        int(shot_mark1_count) >= 0
        and int(shot_mark2_count) >= 0
        and jump_norm in VALID_IMAGE_JUMP_MODES
        and (not has_marks or bool(shot_mark_xml_sidecar_enabled))
    )
    if not xml_ok:
        errors.append(
            f"{S4_ERR_SHOT_MARK_XML_SIDECAR_MISMATCH}: Shot Mark1/2 requires M4ROOT/CLIP/*M01.XML NonRealTimeMeta sidecar "
            f"and valid [Image Jump Setting] (got jump={image_jump_setting!r})"
        )

    shoot_norm = _norm_token(shoot_mode).replace("S&Q", "S_AND_Q")
    make_norm = _norm_token(tc_make)
    run_norm = _norm_token(tc_run)
    if (
        shoot_norm not in VALID_SHOOT_MODES
        or make_norm not in VALID_TC_MAKE_MODES
        or run_norm not in VALID_TC_RUN_MODES
    ):
        errors.append(
            f"{S4_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION}: invalid shoot/TC mode ({shoot_mode!r}/{tc_make!r}/{tc_run!r})"
        )

    regen_slot1_ok = True
    effective_run = "REC_RUN" if make_norm == "REGENERATE" else run_norm
    if make_norm == "REGENERATE":
        if int(tc_regenerate_reference_slot) != 1 or expect_free_run_under_regenerate:
            regen_slot1_ok = False
            errors.append(
                f"{S4_ERR_TC_REGENERATE_SLOT1_OR_RECRUN_VIOLATION}: [Time Code Make]=[Regenerate] reads "
                "Slot-1 exclusively and forces [Rec Run] advancement"
            )

    ext_lk_ok = True
    if shoot_norm == "S_AND_Q" and hdmi_tc_output_expected_in_sq:
        ext_lk_ok = False
        errors.append(
            f"{S4_ERR_VMC_BNCM1_EXT_LK_OR_SQ_TC_VIOLATION}: [Time Code Run] and HDMI [Time Code Output] are disabled in S&Q mode"
        )
    if vmc_bncm1_ext_lk_required:
        if not (shoot_norm == "MOVIE" and make_norm == "PRESET" and run_norm == "FREE_RUN"):
            ext_lk_ok = False
            errors.append(
                f"{S4_ERR_VMC_BNCM1_EXT_LK_OR_SQ_TC_VIOLATION}: VMC-BNCM1 EXT-LK requires Movie + Preset + Free Run; "
                f"got {shoot_norm} + {make_norm} + {run_norm} (EXT-LK dropped)"
            )

    return Checklist4FileSettingsShotMarkAndTcSlot1Result(
        checklist_id=CHECKLIST_S4_ID,
        passed=(len(errors) == 0),
        file_name_format=fmt_norm,
        file_number_mode=num_norm,
        title_name=title_str,
        title_ascii_length=len(title_str),
        cam_id=cam_str,
        reel_number=reel_int,
        sdhc_standard_lock_respected=sdhc_ok,
        shot_mark1_count=int(shot_mark1_count),
        shot_mark2_count=int(shot_mark2_count),
        shot_mark_xml_sidecar_verified=xml_ok,
        image_jump_setting=jump_norm,
        shoot_mode=shoot_norm,
        tc_make=make_norm,
        requested_tc_run=run_norm,
        effective_tc_run=effective_run,
        tc_regenerate_slot1_master_verified=regen_slot1_ok,
        vmc_bncm1_ext_lk_required=bool(vmc_bncm1_ext_lk_required),
        vmc_bncm1_ext_lk_preserved=ext_lk_ok,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Checklist 5: Physical REC Lamp Coupled Tally, Shockless WB & Tier-0 Receipt Gate
# ---------------------------------------------------------------------------


def build_simulated_phase216_tier0_receipts(
    *,
    body_serial: str = DEFAULT_TARGET_BODY_SERIAL,
    emmc_cid: str = DEFAULT_TARGET_EMMC_CID,
    body_fw: str = TARGET_BODY_FW,
) -> Tuple[bytes, bytes, Dict[str, str]]:
    """Build deterministic in-memory 528 B FX3RCPT1 dual receipts for `--simulate-bench-dry-run`."""
    item_hashes: Dict[str, str] = {}
    total_bytes = 0
    for item in COLD_BACKUP_ITEMS:
        item_hashes[item.item_id] = hashlib.sha256(
            f"PHASE216_TIER0:{body_fw}:{item.item_id}:{item.size_bytes}:{emmc_cid.lower()}".encode(
                "ascii"
            )
        ).hexdigest()
        total_bytes += item.size_bytes
    manifest_seed = hashlib.sha256(
        f"PHASE216_MANIFEST:{body_serial}:{body_fw}:{emmc_cid.lower()}".encode("ascii")
    ).hexdigest()
    rcpt = build_sd_backup_receipt_bytes(
        manifest_sha256=manifest_seed,
        item_hashes=item_hashes,
        total_dumped_bytes=total_bytes,
    )
    baselines = build_default_h0_baselines(body_serial=body_serial, emmc_cid=emmc_cid)
    return rcpt, bytes(rcpt), baselines


def evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate(
    *,
    rec_lamp_mode: str = REC_LAMP_ONLY_FRONT_OFF,
    expect_uncoupled_rear_vs_top_tally: bool = False,
    emphasized_rec_display_enabled: bool = True,
    silent_mode_enabled: bool = False,
    audio_signals_mode: str = "ON",
    shockless_wb_mode: str = "1",
    wb_kelvin_k: int = 5600,
    kelvin_or_grid_transition_frames: int = 0,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    simulated_h0_h3_drifted_surfaces: int = 0,
    simulate_bench_dry_run: bool = False,
) -> Tuple[Checklist5RecLampShocklessWbAndTier0Result, Tuple[str, ...]]:
    errors: List[str] = []
    tier0_errors: List[str] = []

    lamp_norm = _norm_token(rec_lamp_mode)
    if lamp_norm not in VALID_REC_LAMP_MODES:
        errors.append(
            f"{S5_ERR_REC_LAMP_COUPLED_REAR_TOP_VIOLATION}: invalid [REC Lamp] mode {rec_lamp_mode!r}; "
            "FX3 supports only All On, Only Front Off, All Off"
        )
        front_lit = rear_lit = top_lit = False
    elif lamp_norm == REC_LAMP_ALL_ON:
        front_lit, rear_lit, top_lit = True, True, True
    elif lamp_norm == REC_LAMP_ONLY_FRONT_OFF:
        front_lit, rear_lit, top_lit = False, True, True
    else:
        front_lit, rear_lit, top_lit = False, False, False

    rear_top_coupled = (rear_lit == top_lit) and (not expect_uncoupled_rear_vs_top_tally)
    if not rear_top_coupled:
        errors.append(
            f"{S5_ERR_REC_LAMP_COUPLED_REAR_TOP_VIOLATION}: FX3 rear REC lamp and top REC button lamp "
            "are hardware-coupled and cannot be switched independently"
        )

    audio_norm = _norm_token(audio_signals_mode)
    if audio_norm not in ("ON", "OFF_SHUTTER_ONLY", "OFF"):
        errors.append(f"{S5_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK}: invalid [Audio signals]={audio_signals_mode!r}")
    if silent_mode_enabled and audio_norm != "OFF":
        errors.append(
            f"{S5_ERR_SILENT_MODE_AUDIO_SIGNALS_LOCK}: [Silent Mode]=[On] hard-locks [Audio signals] to [Off]"
        )

    swb_raw = str(shockless_wb_mode).strip().upper()
    if swb_raw.startswith("1"):
        swb_norm = "1"
    elif swb_raw.startswith("2"):
        swb_norm = "2"
    elif swb_raw.startswith("3"):
        swb_norm = "3"
    else:
        swb_norm = _norm_token(shockless_wb_mode)
    kelvin_int = int(wb_kelvin_k)
    trans_frames = int(kelvin_or_grid_transition_frames)
    if (
        swb_norm not in VALID_SHOCKLESS_WB_MODES
        or not (WB_KELVIN_MIN_K <= kelvin_int <= WB_KELVIN_MAX_K)
        or trans_frames != 0
    ):
        errors.append(
            f"{S5_ERR_SHOCKLESS_WB_ZERO_FRAME_KELVIN_GRID}: invalid Shockless WB ({shockless_wb_mode!r}), "
            f"Kelvin ({kelvin_int}K), or non-zero Kelvin/grid transition frames ({trans_frames} != 0)"
        )

    surface_total = len(SIXTEEN_STORAGE_SURFACES)
    drifted = max(0, min(surface_total, int(simulated_h0_h3_drifted_surfaces)))
    h0_eq_h3 = surface_total - drifted
    if h0_eq_h3 != surface_total:
        errors.append(
            f"{S5_ERR_H0_H3_IMMUTABILITY_DRIFT}: H0 == H3 parity drift ({h0_eq_h3}/{surface_total})"
        )

    raw_a = receipt_a_bytes
    raw_b = receipt_b_bytes
    dev_a = st_dev_a_override
    dev_b = st_dev_b_override
    eff_serial = body_serial
    eff_cid = emmc_cid
    eff_h0_a = dict(h0_baselines_a) if h0_baselines_a is not None else None
    eff_h0_b = dict(h0_baselines_b) if h0_baselines_b is not None else None

    if (
        simulate_bench_dry_run
        and raw_a is None
        and raw_b is None
        and receipt_a_path is None
        and receipt_b_path is None
    ):
        eff_serial = eff_serial or DEFAULT_TARGET_BODY_SERIAL
        eff_cid = eff_cid or DEFAULT_TARGET_EMMC_CID
        raw_a, raw_b, sim_h0 = build_simulated_phase216_tier0_receipts(
            body_serial=eff_serial, emmc_cid=eff_cid, body_fw=body_fw
        )
        dev_a = 101 if dev_a is None else dev_a
        dev_b = 202 if dev_b is None else dev_b
        eff_h0_a = eff_h0_a if eff_h0_a is not None else dict(sim_h0)
        eff_h0_b = eff_h0_b if eff_h0_b is not None else dict(sim_h0)

    if receipt_a_path is not None:
        try:
            _, raw_a, st_a = _read_bounded_slice_o_rdonly(Path(receipt_a_path), SD_RECEIPT_BYTES + 64)
            if dev_a is None:
                dev_a = int(st_a)
        except OSError as exc:
            tier0_errors.append(
                f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_a read failed: {exc}"
            )

    if receipt_b_path is not None:
        try:
            _, raw_b, st_b = _read_bounded_slice_o_rdonly(Path(receipt_b_path), SD_RECEIPT_BYTES + 64)
            if dev_b is None:
                dev_b = int(st_b)
        except OSError as exc:
            tier0_errors.append(
                f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt_b read failed: {exc}"
            )

    receipt_present = (raw_a is not None) and (raw_b is not None)
    distinct_media = False
    receipt_verified = False

    if not receipt_present:
        tier0_errors.append(
            f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual-copy 528B FX3RCPT1 Tier-0 "
            "cold-backup receipts not provided (offline fail-closed)"
        )
    else:
        assert raw_a is not None and raw_b is not None
        if len(raw_a) != SD_RECEIPT_BYTES or len(raw_b) != SD_RECEIPT_BYTES or raw_a != raw_b:
            tier0_errors.append(
                f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: dual FX3RCPT1 size/byte mismatch"
            )
        else:
            if dev_a is not None and dev_b is not None and int(dev_a) != int(dev_b):
                distinct_media = True
            else:
                tier0_errors.append(
                    f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: st_dev_a == st_dev_b ({dev_a} vs {dev_b})"
                )

            ser_norm = (eff_serial or "").strip()
            cid_norm = (eff_cid or "").strip().lower()
            if not BODY_SERIAL_RE.match(ser_norm) or ser_norm.upper() in FORBIDDEN_TRIVIAL_SERIALS:
                tier0_errors.append(
                    f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid body_serial={eff_serial!r}"
                )
            if not HEX32_CID_RE.match(cid_norm) or cid_norm in FORBIDDEN_TRIVIAL_CIDS:
                tier0_errors.append(
                    f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid emmc_cid={eff_cid!r}"
                )
            if int(body_model_id) != TARGET_MODEL_ID_INT or str(body_fw).strip() != TARGET_BODY_FW:
                tier0_errors.append(
                    f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: receipt target mismatch"
                )

            try:
                parsed_a = parse_sd_backup_receipt_bytes(raw_a)
                parsed_b = parse_sd_backup_receipt_bytes(raw_b)
                if not parsed_a.valid or not parsed_b.valid:
                    tier0_errors.append(
                        f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 CRC32/header invalid"
                    )
            except Exception as exc:
                tier0_errors.append(
                    f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: FX3RCPT1 parse error: {exc}"
                )

            if eff_h0_a is None or eff_h0_b is None:
                tier0_errors.append(
                    f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: missing H0 baseline digests"
                )
            else:
                for req_k in REQUIRED_H0_BASELINE_KEYS:
                    va = eff_h0_a.get(req_k, "")
                    vb = eff_h0_b.get(req_k, "")
                    if _is_trivial_hex64(va) or va.lower() != vb.lower():
                        tier0_errors.append(
                            f"{S5_ERR_TIER0_DUAL_MEDIA_RECEIPT_MISSING_OR_INVALID}: invalid/mismatched H0[{req_k}]"
                        )

            if len(tier0_errors) == 0:
                receipt_verified = True

    return (
        Checklist5RecLampShocklessWbAndTier0Result(
            checklist_id=CHECKLIST_S5_ID,
            passed=(len(errors) == 0),
            rec_lamp_mode=lamp_norm,
            front_tally_lit=front_lit,
            rear_tally_lit=rear_lit,
            top_rec_button_lit=top_lit,
            rear_and_top_coupled=rear_top_coupled,
            emphasized_rec_display_independent=bool(emphasized_rec_display_enabled or True),
            silent_mode_enabled=bool(silent_mode_enabled),
            audio_signals_mode=audio_norm,
            shockless_wb_mode=swb_norm,
            wb_kelvin_k=kelvin_int,
            kelvin_or_grid_transition_frames=trans_frames,
            h0_h3_surface_count=surface_total,
            h0_equals_h3_count=h0_eq_h3,
            tier0_receipt_present=receipt_present,
            tier0_receipt_verified=receipt_verified,
            distinct_physical_media_verified=distinct_media,
            errors=tuple(errors),
        ),
        tuple(tier0_errors),
    )


# ---------------------------------------------------------------------------
# Top-Level Pre-Shoot Readiness Orchestrator & Tamper-Evident Verifier
# ---------------------------------------------------------------------------


def evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness(
    *,
    simulate_bench_dry_run: bool = False,
    simulate_ready_bench: Optional[bool] = None,
    force_clean_room: Optional[bool] = None,
    synthetic_clean_room: Optional[bool] = None,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    body_model_id: int = TARGET_MODEL_ID_INT,
    body_fw: str = TARGET_BODY_FW,
    # Checklist 1
    desqueeze_ratio: str = "OFF",
    marker_display_locked_off: bool = True,
    focus_magnifier_locked_off: bool = True,
    auto_mag_mf_locked_off: bool = True,
    face_eye_af_locked_off: bool = True,
    hdmi_raw_output: bool = False,
    rec_media_dur_hdmi_output: str = HDMI_REC_MEDIA_ON,
    log_shooting_mode: str = "CINE_EI",
    remote_shooting_active: bool = False,
    expect_active_desqueeze_under_suppression: bool = False,
    initial_focus_mag_scale: str = "x4.0",
    focus_magnifier_active: bool = False,
    bright_monitoring_active: bool = False,
    in_body_focus_map_menu_present: bool = False,
    in_body_focus_map_overlay_injected: bool = False,
    mc_external_focus_map_enabled: bool = False,
    mc_sensor_fps: float = 23.98,
    mc_pdaf_compatible_lens: bool = True,
    camera_in_playback: bool = False,
    # Checklist 2
    require_internal_card_recording: bool = True,
    ack_hdmi_only_no_internal_card_rec: bool = False,
    picture_profile: str = "OFF",
    hdmi_output_resolution: str = "AUTO",
    hdmi_only_4k_setting: str = "23.98P_10BIT",
    dci_4k_24p_mode: bool = False,
    expected_hdmi_4k_with_internal_rec_and_log: bool = False,
    hdmi_info_display: str = "OFF",
    require_unblanked_camera_lcd: bool = True,
    # Checklist 3
    simult_recording_enabled: bool = True,
    auto_switch_media: str = "OFF",
    require_strict_dual_vault_parity: bool = True,
    slot1_media_type: str = "CFEXPRESS_A",
    slot2_media_type: str = "CFEXPRESS_A",
    slot1_capacity_gb: int = 160,
    slot2_capacity_gb: int = 160,
    slot1_speed_tier: str = "CFEXPRESS_A_VPG400",
    slot2_speed_tier: str = "CFEXPRESS_A_VPG400",
    required_min_speed_tier: str = "V90",
    proxy_recording_enabled: bool = True,
    proxy_file_format: str = "XAVC_HS_HD",
    rec_frame_rate_fps: float = 23.98,
    sq_mode_enabled: bool = False,
    sq_frame_rate_fps: float = 60.0,
    expect_in_camera_proxy_playback: bool = False,
    clip_sub_delete_coupled: bool = True,
    clip_sub_protect_coupled: bool = True,
    orphan_clip_or_sub_count: int = 0,
    # Checklist 4
    file_name_format: str = "CAM_ID_PLUS_REEL",
    file_number_mode: str = "SERIES",
    require_series_counter: bool = True,
    title_name: str = "FX3_BENCH_A",
    cam_id: str = "A",
    reel_number: int = 1,
    custom_folder_name_requested: bool = False,
    shot_mark1_count: int = 1,
    shot_mark2_count: int = 1,
    shot_mark_xml_sidecar_enabled: bool = True,
    image_jump_setting: str = "SHOT_MARK_ONLY",
    shoot_mode: str = "MOVIE",
    tc_make: str = "PRESET",
    tc_run: str = "FREE_RUN",
    tc_regenerate_reference_slot: int = 1,
    expect_free_run_under_regenerate: bool = False,
    vmc_bncm1_ext_lk_required: bool = False,
    hdmi_tc_output_expected_in_sq: bool = False,
    # Checklist 5 & Tier-0 Gate
    rec_lamp_mode: str = REC_LAMP_ONLY_FRONT_OFF,
    expect_uncoupled_rear_vs_top_tally: bool = False,
    emphasized_rec_display_enabled: bool = True,
    silent_mode_enabled: bool = False,
    audio_signals_mode: str = "ON",
    shockless_wb_mode: str = "1",
    wb_kelvin_k: int = 5600,
    kelvin_or_grid_transition_frames: int = 0,
    receipt_a_path: Optional[Path] = None,
    receipt_b_path: Optional[Path] = None,
    receipt_a_bytes: Optional[bytes] = None,
    receipt_b_bytes: Optional[bytes] = None,
    st_dev_a_override: Optional[int] = None,
    st_dev_b_override: Optional[int] = None,
    body_serial: Optional[str] = None,
    emmc_cid: Optional[str] = None,
    h0_baselines_a: Optional[Mapping[str, str]] = None,
    h0_baselines_b: Optional[Mapping[str, str]] = None,
    simulated_h0_h3_drifted_surfaces: int = 0,
) -> RealHwHdmiProxyDesqueezeSimultReport:
    """Execute Phase 216 read-only operator pre-shoot bench & media readiness verifier (`S1..S5`)."""
    eff_sim = bool(simulate_bench_dry_run or simulate_ready_bench)

    donor_res = inspect_phase216_donors_bounded(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        force_clean_room=force_clean_room,
        synthetic_clean_room=synthetic_clean_room,
    )
    c1 = evaluate_checklist_1_desqueeze_and_mc_focus_map(
        body_model_id=body_model_id,
        body_fw=body_fw,
        desqueeze_ratio=desqueeze_ratio,
        marker_display_locked_off=marker_display_locked_off,
        focus_magnifier_locked_off=focus_magnifier_locked_off,
        auto_mag_mf_locked_off=auto_mag_mf_locked_off,
        face_eye_af_locked_off=face_eye_af_locked_off,
        hdmi_raw_output=hdmi_raw_output,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        log_shooting_mode=log_shooting_mode,
        remote_shooting_active=remote_shooting_active,
        expect_active_desqueeze_under_suppression=expect_active_desqueeze_under_suppression,
        initial_focus_mag_scale=initial_focus_mag_scale,
        focus_magnifier_active=focus_magnifier_active,
        bright_monitoring_active=bright_monitoring_active,
        in_body_focus_map_menu_present=in_body_focus_map_menu_present,
        in_body_focus_map_overlay_injected=in_body_focus_map_overlay_injected,
        mc_external_focus_map_enabled=mc_external_focus_map_enabled,
        mc_sensor_fps=mc_sensor_fps,
        mc_pdaf_compatible_lens=mc_pdaf_compatible_lens,
        camera_in_playback=camera_in_playback,
    )
    c2 = evaluate_checklist_2_hdmi_log_and_blank_lcd(
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        require_internal_card_recording=require_internal_card_recording,
        ack_hdmi_only_no_internal_card_rec=ack_hdmi_only_no_internal_card_rec,
        log_shooting_mode=log_shooting_mode,
        picture_profile=picture_profile,
        hdmi_raw_output=hdmi_raw_output,
        hdmi_output_resolution=hdmi_output_resolution,
        hdmi_only_4k_setting=hdmi_only_4k_setting,
        dci_4k_24p_mode=dci_4k_24p_mode,
        expected_hdmi_4k_with_internal_rec_and_log=expected_hdmi_4k_with_internal_rec_and_log,
        hdmi_info_display=hdmi_info_display,
        require_unblanked_camera_lcd=require_unblanked_camera_lcd,
    )
    c3 = evaluate_checklist_3_simult_autoswitch_and_proxy_vault(
        simult_recording_enabled=simult_recording_enabled,
        auto_switch_media=auto_switch_media,
        require_strict_dual_vault_parity=require_strict_dual_vault_parity,
        slot1_media_type=slot1_media_type,
        slot2_media_type=slot2_media_type,
        slot1_capacity_gb=slot1_capacity_gb,
        slot2_capacity_gb=slot2_capacity_gb,
        slot1_speed_tier=slot1_speed_tier,
        slot2_speed_tier=slot2_speed_tier,
        required_min_speed_tier=required_min_speed_tier,
        proxy_recording_enabled=proxy_recording_enabled,
        proxy_file_format=proxy_file_format,
        rec_frame_rate_fps=rec_frame_rate_fps,
        sq_mode_enabled=sq_mode_enabled,
        sq_frame_rate_fps=sq_frame_rate_fps,
        rec_media_dur_hdmi_output=rec_media_dur_hdmi_output,
        expect_in_camera_proxy_playback=expect_in_camera_proxy_playback,
        clip_sub_delete_coupled=clip_sub_delete_coupled,
        clip_sub_protect_coupled=clip_sub_protect_coupled,
        orphan_clip_or_sub_count=orphan_clip_or_sub_count,
    )
    c4 = evaluate_checklist_4_file_settings_shotmark_and_tc_slot1(
        file_name_format=file_name_format,
        file_number_mode=file_number_mode,
        require_series_counter=require_series_counter,
        title_name=title_name,
        cam_id=cam_id,
        reel_number=reel_number,
        slot1_media_type=slot1_media_type,
        slot2_media_type=slot2_media_type,
        custom_folder_name_requested=custom_folder_name_requested,
        shot_mark1_count=shot_mark1_count,
        shot_mark2_count=shot_mark2_count,
        shot_mark_xml_sidecar_enabled=shot_mark_xml_sidecar_enabled,
        image_jump_setting=image_jump_setting,
        shoot_mode=shoot_mode,
        tc_make=tc_make,
        tc_run=tc_run,
        tc_regenerate_reference_slot=tc_regenerate_reference_slot,
        expect_free_run_under_regenerate=expect_free_run_under_regenerate,
        vmc_bncm1_ext_lk_required=vmc_bncm1_ext_lk_required,
        hdmi_tc_output_expected_in_sq=hdmi_tc_output_expected_in_sq,
    )
    c5, tier0_errors = evaluate_checklist_5_reclamp_shockless_wb_and_tier0_gate(
        rec_lamp_mode=rec_lamp_mode,
        expect_uncoupled_rear_vs_top_tally=expect_uncoupled_rear_vs_top_tally,
        emphasized_rec_display_enabled=emphasized_rec_display_enabled,
        silent_mode_enabled=silent_mode_enabled,
        audio_signals_mode=audio_signals_mode,
        shockless_wb_mode=shockless_wb_mode,
        wb_kelvin_k=wb_kelvin_k,
        kelvin_or_grid_transition_frames=kelvin_or_grid_transition_frames,
        receipt_a_path=receipt_a_path,
        receipt_b_path=receipt_b_path,
        receipt_a_bytes=receipt_a_bytes,
        receipt_b_bytes=receipt_b_bytes,
        st_dev_a_override=st_dev_a_override,
        st_dev_b_override=st_dev_b_override,
        body_model_id=body_model_id,
        body_fw=body_fw,
        body_serial=body_serial,
        emmc_cid=emmc_cid,
        h0_baselines_a=h0_baselines_a,
        h0_baselines_b=h0_baselines_b,
        simulated_h0_h3_drifted_surfaces=simulated_h0_h3_drifted_surfaces,
        simulate_bench_dry_run=eff_sim,
    )

    checklists_passed = sum(1 for item in (c1, c2, c3, c4, c5) if item.passed)
    all_5_passed = donor_res.passed and checklists_passed == 5

    all_errors: List[str] = []
    all_errors.extend(donor_res.errors)
    for item in (c1, c2, c3, c4, c5):
        all_errors.extend(item.errors)
    all_errors.extend(tier0_errors)

    remediations: List[str] = []
    if not c1.passed:
        remediations.append(
            "Verify De-Squeeze Display (1.6x=1.65x), 4-setting locks, and M&C Focus Map <150fps."
        )
    if not c2.passed:
        remediations.append(
            "Keep [Rec. Media dur HDMI Output]=[On] for internal card recording and [HDMI Info. Display]=[Off] to prevent built-in LCD blanking."
        )
    if not c3.passed:
        remediations.append(
            "Insert matched exFAT CFexpress-A / SDXC cards with [Auto Switch Media]=[Off], keep Px proxy <100fps, and preserve coupled CLIP+SUB pairs."
        )
    if not c4.passed:
        remediations.append(
            "Use <=37-char ASCII Title + [Series] counter on exFAT media, keep TC Regenerate on Slot 1, and keep Movie+Preset+Free Run for VMC-BNCM1 EXT-LK."
        )
    if not c5.passed or not c5.tier0_receipt_verified:
        remediations.append(
            "Verify 3-state coupled REC Lamp, [Silent Mode]->[Audio signals]=Off, 0-frame Kelvin WB, and dual-device 528B FX3RCPT1 Tier-0 receipts."
        )

    if not all_5_passed:
        verdict = GO_NO_GO_BLOCKED_HDMI_PROXY_DESQUEEZE_SIMULT_FAILURE
    elif not c5.tier0_receipt_verified:
        verdict = (
            GO_NO_GO_BLOCKED_AWAITING_PHYSICAL_TIER0_RECEIPT
            if not c5.tier0_receipt_present
            else GO_NO_GO_BLOCKED_HDMI_PROXY_DESQUEEZE_SIMULT_FAILURE
        )
    elif eff_sim:
        verdict = GO_NO_GO_DRY_RUN_SIMULATED_READY
    else:
        verdict = GO_NO_GO_HDMI_PROXY_DESQUEEZE_SIMULT_VERIFIED

    provisional = RealHwHdmiProxyDesqueezeSimultReport(
        schema=PHASE_216_SCHEMA,
        phase_version=PHASE_216_VERSION,
        verification_mode=donor_res.verification_mode,
        simulate_bench_dry_run=eff_sim,
        go_no_go=verdict,
        hardware_live_attachment_authorized=False,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        spi_nor_write_authorized=False,
        el3_payload_transmit_authorized=False,
        sd_physical_media_written=False,
        usb_packets_transmitted=0,
        physical_usb_packets_emitted=0,
        raw_firmware_bytes_leaked=PHASE216_RAW_FIRMWARE_BYTES_LEAKED,
        checklist_count=5,
        checklists_passed=checklists_passed,
        all_5_operator_checklists_passed=all_5_passed,
        tier0_receipt_verified=c5.tier0_receipt_verified,
        h0_h3_surface_count=c5.h0_h3_surface_count,
        h0_equals_h3_count=c5.h0_equals_h3_count,
        donor_inspection=donor_res,
        checklist_1_desqueeze_and_mc_focus_map=c1,
        checklist_2_hdmi_log_and_blank_lcd=c2,
        checklist_3_simult_autoswitch_and_proxy_vault=c3,
        checklist_4_file_settings_shotmark_and_tc_slot1=c4,
        checklist_5_reclamp_shockless_wb_and_tier0_gate=c5,
        warnings=c2.warnings,
        remediation_actions=tuple(remediations),
        errors=tuple(all_errors),
        report_sha256="",
    )
    digest = _canonical_sha256_dict(provisional.to_dict(), exclude_key="report_sha256")
    return RealHwHdmiProxyDesqueezeSimultReport(
        **{**provisional.to_dict(), "donor_inspection": donor_res,
           "checklist_1_desqueeze_and_mc_focus_map": c1,
           "checklist_2_hdmi_log_and_blank_lcd": c2,
           "checklist_3_simult_autoswitch_and_proxy_vault": c3,
           "checklist_4_file_settings_shotmark_and_tc_slot1": c4,
           "checklist_5_reclamp_shockless_wb_and_tier0_gate": c5,
           "warnings": c2.warnings,
           "remediation_actions": tuple(remediations),
           "errors": tuple(all_errors),
           "report_sha256": digest}
    )


run_hdmi_proxy_desqueeze_and_simult_preflight = (
    evaluate_realhw_hdmi_proxy_desqueeze_and_simult_readiness
)


def verify_phase216_report(payload: Mapping[str, Any]) -> Phase216ReportVerifyResult:
    """Fail-closed tamper & safety-lock verifier for Phase 216 preflight reports."""
    errors: List[str] = []
    if payload.get("schema") != PHASE_216_SCHEMA:
        errors.append(f"Invalid schema: {payload.get('schema')!r}")
    if payload.get("phase_version") != PHASE_216_VERSION:
        errors.append(f"Invalid phase_version: {payload.get('phase_version')!r}")
    if payload.get("verification_mode") not in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC"):
        errors.append(f"Invalid verification_mode: {payload.get('verification_mode')!r}")
    if payload.get("go_no_go") not in PHASE_216_VALID_GO_NO_GO_VALUES:
        errors.append(f"Invalid go_no_go verdict: {payload.get('go_no_go')!r}")

    for lock_key in (
        "hardware_live_attachment_authorized",
        "persistent_emmc_writes_authorized",
        "persistent_write_release",
        "spi_nor_write_authorized",
        "el3_payload_transmit_authorized",
        "sd_physical_media_written",
    ):
        if payload.get(lock_key) is not False:
            errors.append(f"Safety lock violated: {lock_key}={payload.get(lock_key)!r}")

    for zero_key in (
        "usb_packets_transmitted",
        "physical_usb_packets_emitted",
        "raw_firmware_bytes_leaked",
    ):
        if payload.get(zero_key) != 0:
            errors.append(f"Zero-counter violated: {zero_key}={payload.get(zero_key)!r}")

    if payload.get("checklist_count") != 5:
        errors.append(f"Expected checklist_count==5, got {payload.get('checklist_count')!r}")

    if payload.get("simulate_bench_dry_run") is True and (
        payload.get("go_no_go") == GO_NO_GO_HDMI_PROXY_DESQUEEZE_SIMULT_VERIFIED
    ):
        errors.append("Simulated dry-run cannot claim physical Tier-0 verified verdict")

    if (
        payload.get("go_no_go") == GO_NO_GO_HDMI_PROXY_DESQUEEZE_SIMULT_VERIFIED
        and (
            payload.get("all_5_operator_checklists_passed") is not True
            or payload.get("tier0_receipt_verified") is not True
        )
    ):
        errors.append("Verified verdict requires all 5 checklists and Tier-0 receipt verified")

    claimed_sha = str(payload.get("report_sha256", ""))
    expected_sha = _canonical_sha256_dict(payload, exclude_key="report_sha256")
    if not HEX64_RE.match(claimed_sha) or claimed_sha != expected_sha:
        errors.append("report_sha256 canonical digest mismatch")

    return Phase216ReportVerifyResult(valid=(len(errors) == 0), errors=tuple(errors))


def render_phase216_markdown(report: RealHwHdmiProxyDesqueezeSimultReport) -> str:
    """Render concise deterministic Markdown summary for Phase 216 pre-shoot bench preflight."""
    c1 = report.checklist_1_desqueeze_and_mc_focus_map
    c2 = report.checklist_2_hdmi_log_and_blank_lcd
    c3 = report.checklist_3_simult_autoswitch_and_proxy_vault
    c4 = report.checklist_4_file_settings_shotmark_and_tc_slot1
    c5 = report.checklist_5_reclamp_shockless_wb_and_tier0_gate
    lines = [
        f"# Phase 216 Pre-Shoot Bench & Media Readiness (`{report.schema}`)",
        "",
        f"- **Go/No-Go Verdict**: `{report.go_no_go}` (mode=`{report.verification_mode}`, dry_run=`{report.simulate_bench_dry_run}`)",
        f"- **Operator Checklists**: `{report.checklists_passed}/{report.checklist_count}` (`H0==H3`: `{report.h0_equals_h3_count}/{report.h0_h3_surface_count}`)",
        f"- **Hard Locks**: `live_attach={report.hardware_live_attachment_authorized}`, `emmc_writes={report.persistent_emmc_writes_authorized}`, `spi_nor={report.spi_nor_write_authorized}`, `el3_tx={report.el3_payload_transmit_authorized}`, `usb_pkts={report.usb_packets_transmitted}`, `leaked_bytes={report.raw_firmware_bytes_leaked}`",
        "",
        "| Checklist | Status | Key Telemetry |",
        "| :--- | :---: | :--- |",
        f"| `{c1.checklist_id}` | `{'PASS' if c1.passed else 'FAIL'}` | De-Squeeze `{c1.desqueeze_ratio}` (`{c1.actual_desqueeze_factor}x` -> eff `{c1.effective_desqueeze_factor}x`), M&C `<150fps`=`{c1.mc_focus_map_under_150fps}` |",
        f"| `{c2.checklist_id}` | `{'PASS' if c2.passed else 'FAIL'}` | RecMedia=`{c2.rec_media_dur_hdmi_output}`, HDMI=`{c2.effective_hdmi_resolution}`, BlankLCD=`{c2.camera_lcd_blanked}` |",
        f"| `{c3.checklist_id}` | `{'PASS' if c3.passed else 'FAIL'}` | Simult=`{c3.simult_recording_enabled}`, AutoSwitch=`{c3.auto_switch_media}`, Px=`{c3.proxy_file_format}` (`<100fps`=`{c3.proxy_under_100fps_cutoff}`) |",
        f"| `{c4.checklist_id}` | `{'PASS' if c4.passed else 'FAIL'}` | Format=`{c4.file_name_format}` (`{c4.file_number_mode}`), TC=`{c4.tc_make}`/`{c4.effective_tc_run}`, EXT-LK=`{c4.vmc_bncm1_ext_lk_preserved}` |",
        f"| `{c5.checklist_id}` | `{'PASS' if c5.passed else 'FAIL'}` | RecLamp=`{c5.rec_lamp_mode}` (Rear+Top coupled=`{c5.rear_and_top_coupled}`), ShocklessWB=`{c5.shockless_wb_mode}` (`0f`), Tier0=`{c5.tier0_receipt_verified}` |",
        "",
        f"- **Report SHA-256**: `{report.report_sha256}`",
    ]
    return "\n".join(lines) + "\n"
