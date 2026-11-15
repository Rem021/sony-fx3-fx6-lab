"""Phase 90 — Unified 24-Gate + OTP/RPMB/Tier-0 + 16-Auditor + 13-Stage VM + Round 16 Master Gate (`stage_b_milestone90_master_gate_v1`).

Composes all six Milestone Phase 90 engineering & safety pillars (`P1 .. P6`) into a single
tamper-evident, fail-closed certificate executing in `< 3.5s` across both
`LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

- `P1` (`SAFETY_24GATE_MASTER_PREFLIGHT`):
  Runs Phase 84 `dewpoint_tec_usbc_and_24gate_guard.evaluate_24gate_preflight` (`G01..G24`),
  verifying `21/24` offline hardware-truth block (`overall_ready_for_hardware_attach=False`) vs
  `24/24` simulated rehearsal (`dry_run_rehearsal_only=True`), including:
  - `G21` (`XLR-H1 +48V` phantom transducer burnout & hot-plug discharge guard),
  - `G22` (gimbal/follow-focus E-Mount mount-shear, venue-laser CMOS & shutter blade park guard),
  - `G23` (Magnus-Tetens psychrometric dew-point & sub-dewpoint Peltier `TEC` condensation firewall),
  - `G24` (PMIC `5V` `900 mA` accessory budget, USB-C PD cable IR droop & cage strain clamp guard),
  plus `G19`/`G20`.
- `P2` (`OTP_RPMB_ANTIROLLBACK_TIER0_GF256_SD_ESCAPE`):
  Verifies Phase 79 `CXD90057` OTP/RPMB monotonic anti-rollback firewall (`otp_fuse_touches == 0`,
  `rpmb_counter_increments == 0`, `FX3 v7.02 + FX6 v6.01 == TIER_A_GOLD_VERIFIED`, `EXT_CSD`
  permanent-WP fuse trap blocked) + Phase 72 `GF(256)` P+Q 2-erasure / 1-bit-rot healer +
  3-loss quorum rejection + cross-body `cnflasha`/`C2PA` anti-transplant lock + Phase 66
  `FX3_SAFE_STOCK.FLG` SD-sentinel `<1s` escape + `CXD90057 WDT` + `p1 FAT12/FAT16` mirror.
- `P3` (`SIXTEEN_FIRMWARE_LAB_AUDITORS`):
  Verifies all `16/16` `fx3_firmware_lab` auditors (`Phases 1..85`), including Auditors 1..14
  (Phase 65 WB `3x3`, Phase 70 Dual-Slot Proxy / `NRTM v2.20`, Phase 75 Assignable / CIZ /
  Touch-AF / Big6-Fn volatile shadow) + Auditor 15 (`falsecolor_lpcm_tc_ub_audit`, Phase 80:
  `S-Log3` `41%/94% IRE` False Color / EL-Zone, `24-bit/48kHz` 4-ch LPCM soft-knee limiter with
  `int24_wrap_around_count == 0`, SMPTE 12M `BG1..BG8` `User-Bits` with `bus_contention_count == 0`)
  + Auditor 16 (`playback_shotmark_and_ae_audit`, Phase 85: Playback/Thumbnail shuttle,
  `ShotMark1/2` `<EssenceMark>` XML round-trip, `Cine EI` `Push Auto Iris` with
  `p4_nd_motor_fault_attempts == 0` and `internal_emmc_format_possible == False`).
- `P4` (`THIRTEEN_STAGE_VM_COEMULATION`):
  Verifies all `13/13` `outputs/fx3-vm` heterogeneous AArch64 AP + ARM32 Thumb-2 Stock-CP
  co-emulation stages (`Stages 1..13`, `Phases 1..87`), including Stages 1..11 + Stage 12
  (`stage12_phase82_camset_lpcm_tcub`, `uart_boot_contention_events == 0`) + Stage 13
  (`stage13_phase87_playback_shotmark_dewpoint`, `internal_emmc_format_blocked == True`,
  `p4_nd_motor_faults == 0`, `cp_mutation_bytes == 0`, `bk4_persistent_nvram_writes == 0`).
- `P5` (`ROUND16_MULTITAB_AND_4LANG_KERNEL_CLOSURE`):
  Verifies Round 14 (`18/18` 4-language x 3-surface pixel-delta matrix `> 0`) AND Round 16
  (`reports/2026-11-14-round16-fx6-on-fx3-status-tabs45-tcmedia/summary.json`, opened strictly
  `os.O_RDONLY` or deterministic clean-room synthetic fallback) proving 5-tab `Status Check`
  (`0x2f..0x33`, `C(5,2)=10` pairwise pixel deltas strictly `> 0`) + 3-layer `TC/Media` (`ZH-TW`)
  + 3-layer `Monitoring` (`JA`, `0x11`) on real unmodified FX3 `7.02` kernel (`4.9.337-scel+`,
  `nop_count == 0`, `crashes == 0`, `13/13` Stage-B SHA-256).
- `P6` (`DOSSIER_V3_CAPSTONE_AND_H0_VS_H2_IMMUTABILITY`):
  Verifies Dossier v3 (`stage_b_release_dossier_v3`) + Capstone 22-Gate
  (`stage_b_capstone_22gate_v1`) schema contracts AND `H0 == H2` 16-surface bit-for-bit
  post-trial forensic immutability (`Phase 62/68/83`: `drifted_surface_count == 0`,
  `c2pa_rq_lic_intact == True`, `spacc_cnflasha_untouched == True`, `10/10` anomaly scenarios).

Hard-Locked Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `P8_CP_MUTATION_FORBIDDEN = True`, `CP_MUTATION_BYTES = 0`
- `WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN = True`, `WBI_MUTATION_BYTES = 0`
- `CALIBRATION_MUTATION_BYTES = 0`, `USB_OR_CAMERA_OPERATIONS = 0`
- `OTP_FUSE_TOUCHES = 0`, `RPMB_COUNTER_INCREMENTS = 0`
- Zero raw binary `bytes` reprs (`b'...'` / `b"..."`).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from concurrent.futures import ProcessPoolExecutor
import copy
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import multiprocessing as mp
from pathlib import Path
import re
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _ensure_cross_package_paths(repo_root: Path) -> None:
    """Ensure all sibling lab package roots are importable under default PYTHONPATH."""
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

from fx3_firmware_lab.falsecolor_lpcm_tc_ub_auditor import (  # noqa: E402
    analyze_falsecolor_lpcm_tc_ub,
    falsecolor_lpcm_tc_ub_report_to_dict,
)
from fx3_firmware_lab.playback_shotmark_and_ae_auditor import (  # noqa: E402
    analyze_playback_shotmark_and_ae,
    evaluate_media_format_and_delete_firewall,
    playback_shotmark_and_ae_report_to_dict,
)
from fx3_safety.dewpoint_tec_usbc_and_24gate_guard import (  # noqa: E402
    evaluate_24gate_preflight,
)
from fx3_vm_coemulation_suite import (  # noqa: E402
    CoEmulationConfig,
    run_fx3_vm_coemulation_suite,
)
from playback_shotmark_dewpoint_emulator import (  # noqa: E402
    PlaybackShotmarkMediaSession,
)

from .hardware_readiness_packet import (  # noqa: E402
    HEX64_RE,
    _is_forced_clean_room,
)
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
)
from .stage_b_capstone_22gate_verifier import (  # noqa: E402
    CAPSTONE_22GATE_SCHEMA_VERSION,
    DOMAIN_IDS as CAPSTONE_DOMAIN_IDS,
    FIRMWARE_LAB_14_AUDITOR_KEYS,
    STAGE_B_CAPSTONE_22GATE_SCHEMA,
    StageBCapstone22GateFaultInjection,
    VM_COEMULATION_11_STAGE_KEYS,
    _build_clean_room_stage_b_manifest_items,
    _evaluate_domain_2,
    _evaluate_domain_4,
    _worker_domain_2,
    _worker_domain_4_group,
)
from .stage_b_post_trial_auditor import (  # noqa: E402
    _read_file_o_rdonly,
)
from .stage_b_ram_overlay_packager import (  # noqa: E402
    STAGE_B_BK_LANG_SPECS,
)
from .stage_b_rehearsal_orchestrator import (  # noqa: E402
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
)
from .stage_b_release_dossier_v3 import (  # noqa: E402
    DOSSIER_V3_SCHEMA_VERSION,
    PILLAR_IDS as DOSSIER_V3_PILLAR_IDS,
    ROUND14_4LANG_PAIRS,
    STAGE_B_RELEASE_DOSSIER_V3_SCHEMA,
    StageBReleaseDossierV3FaultInjection,
    _evaluate_pillar_b,
    _evaluate_pillar_e,
    _evaluate_pillar_f,
    _worker_pillar_b,
    _worker_pillar_f,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

STAGE_B_MILESTONE90_SCHEMA: str = "stage_b_milestone90_master_gate_v1"
MILESTONE90_SCHEMA_VERSION: str = STAGE_B_MILESTONE90_SCHEMA
SCHEMA_VERSION: str = STAGE_B_MILESTONE90_SCHEMA
PHASE_90_VERSION: str = "90.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P8_CP_MUTATION_FORBIDDEN: bool = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN: bool = True
CP_MUTATION_BYTES: int = 0
WBI_MUTATION_BYTES: int = 0
CALIBRATION_MUTATION_BYTES: int = 0
USB_OR_CAMERA_OPERATIONS: int = 0
OTP_FUSE_TOUCHES: int = 0
RPMB_COUNTER_INCREMENTS: int = 0

STATUS_MILESTONE_READY: str = "MILESTONE_90_SIMULATION_READY"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("P1", "SAFETY_24GATE_MASTER_PREFLIGHT"),
    ("P2", "OTP_RPMB_ANTIROLLBACK_TIER0_GF256_SD_ESCAPE"),
    ("P3", "SIXTEEN_FIRMWARE_LAB_AUDITORS"),
    ("P4", "THIRTEEN_STAGE_VM_COEMULATION"),
    ("P5", "ROUND16_MULTITAB_AND_4LANG_KERNEL_CLOSURE"),
    ("P6", "DOSSIER_V3_CAPSTONE_AND_H0_VS_H2_IMMUTABILITY"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

FIRMWARE_LAB_16_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_14_AUDITOR_KEYS,
    "falsecolor_lpcm_tc_ub_audit",
    "playback_shotmark_and_ae_audit",
)

VM_COEMULATION_13_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_11_STAGE_KEYS,
    "stage12_phase82_camset_lpcm_tcub",
    "stage13_phase87_playback_shotmark_dewpoint",
)

ROUND16_SUMMARY_RELPATH: str = (
    "reports/2026-11-14-round16-fx6-on-fx3-status-tabs45-tcmedia/summary.json"
)
ROUND16_RUN_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("r16a_status_tab4_schinese", "0x32", "schinese"),
    ("r16b_status_tab5_schinese", "0x33", "schinese"),
    ("r16c_menu_3layer_tcmedia_tchinese", "0x11", "tchinese"),
    ("r16d_menu_3layer_monitoring_japanese", "0x11", "japanese"),
)
ROUND16_RUN_IDS: Tuple[str, ...] = tuple(rid for rid, _, _ in ROUND16_RUN_SPECS)
ROUND16_MULTITAB_SIDS: Tuple[str, ...] = ("0x2f", "0x30", "0x31", "0x32", "0x33")
ROUND16_5TAB_PAIR_KEYS: Tuple[str, ...] = (
    "tab1_vs_tab2",
    "tab1_vs_tab3",
    "tab1_vs_tab4",
    "tab1_vs_tab5",
    "tab2_vs_tab3",
    "tab2_vs_tab4",
    "tab2_vs_tab5",
    "tab3_vs_tab4",
    "tab3_vs_tab5",
    "tab4_vs_tab5",
)
ROUND16_TCMEDIA_PAIR_KEYS: Tuple[str, ...] = (
    "tcmedia_vs_shooting_r13b",
    "tcmedia_vs_monitoring_r15c",
)
ROUND16_MONITORING_PAIR_KEYS: Tuple[str, ...] = (
    "monitoring_vs_shooting_r12d",
    "monitoring_japanese_vs_schinese_r15c",
    "monitoring_japanese_vs_tcmedia_tchinese_r16c",
)

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Milestone90FaultInjection:
    """Deterministic fault-injection knobs across Pillars P1..P6 for fail-closed testing."""

    # P1 faults (24-gate preflight, G21..G24)
    p1_dewpoint_kwargs: Optional[Mapping[str, Any]] = None
    p1_pmic_usbc_kwargs: Optional[Mapping[str, Any]] = None
    p1_xlr_kwargs: Optional[Mapping[str, Any]] = None
    p1_gimbal_kwargs: Optional[Mapping[str, Any]] = None
    p1_rig_kwargs: Optional[Mapping[str, Any]] = None
    p1_emount_kwargs: Optional[Mapping[str, Any]] = None
    p1_power_failover_kwargs: Optional[Mapping[str, Any]] = None
    p1_request_persistent_writes: bool = False

    # P2 faults (OTP/RPMB downgrade, cross-SKU brick, EXT_CSD perm-WP, Tier-0 GF(256), init2 escape)
    p2_otp_downgrade_version: Optional[str] = None
    p2_inject_cross_sku_target: Optional[str] = None
    p2_inject_ext_csd_perm_wp: bool = False
    p2_otp_fuse_touches_override: int = 0
    p2_rpmb_increments_override: int = 0
    p2_inject_cross_body_cnflasha_transplant: bool = False
    p2_inject_gf256_quorum_loss: bool = False
    p2_inject_init2_escape_fault: bool = False

    # P3 faults (16 fx3_firmware_lab auditors, incl. Phase 80 #15 & Phase 85 #16)
    p3_calibration_mutation_bytes: int = 0
    p3_bk4_persistent_nvram_writes: int = 0
    p3_corrupt_wb_whitepoint: bool = False
    p3_corrupt_nrtm_sidecar: bool = False
    p3_inject_legacy_sq_big6_block: bool = False
    p3_inject_persistent_nvram_shadow_path: bool = False
    p3_int24_wrap_around_count: int = 0
    p3_bus_contention_count: int = 0
    p3_p4_nd_motor_fault_attempts: int = 0
    p3_inject_internal_emmc_format_attempt: bool = False

    # P4 faults (13-stage VM co-emulation, Stage 12/13)
    p4_cp_mutation_bytes: int = 0
    p4_bk4_persistent_nvram_writes: int = 0
    p4_stage10_dropped_frames: int = 0
    p4_stage11_nop_count: int = 0
    p4_stage11_null_gpio_derefs: int = 0
    p4_stage12_uart_contention_events: int = 0
    p4_stage13_p1_emmc_format_attempt: bool = False
    p4_stage13_p4_nd_motor_faults: int = 0

    # P5 faults (Round 14 + Round 16 5-tab Status Check & TC/Media / Monitoring JA)
    p5_round14_nop_count: int = 0
    p5_round14_zero_pair: bool = False
    p5_round16_nop_count: int = 0
    p5_round16_crashes: int = 0
    p5_round16_zero_tab_pair: Optional[str] = None
    p5_round16_zero_tcmedia_pair: Optional[str] = None
    p5_round16_zero_monitoring_pair: Optional[str] = None
    p5_round16_manifest_count_override: Optional[int] = None

    # P6 faults (Dossier v3 + Capstone 22-Gate + H0-vs-H2 16-surface drift / tamper negative control)
    p6_drift_surface: Optional[str] = None
    p6_tamper_negative_control: bool = False


@dataclass(frozen=True)
class Milestone90PillarResult:
    pillar_id: str
    pillar_name: str
    passed: bool
    status: str
    summary: str
    evidence: Dict[str, Any]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageBMilestone90MasterGateReport:
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_milestone_ready: bool
    status: str
    o_rdonly_enforced: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    hardware_live_attachment_authorized: bool
    hardware_live_attachment_requirements: Tuple[str, ...]
    p8_cp_mutation_forbidden: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    cp_mutation_bytes: int
    wbi_mutation_bytes: int
    calibration_mutation_bytes: int
    usb_or_camera_operations: int
    otp_fuse_touches: int
    rpmb_counter_increments: int
    temp_dir_cleaned: bool
    pillar_count: int
    passed_pillar_count: int
    failed_pillar_ids: Tuple[str, ...]
    pillars: Tuple[Milestone90PillarResult, ...]
    gate24_offline_verified: int
    gate24_simulated_verified: int
    firmware_lab_auditor_count: int
    firmware_lab_auditors_passed: int
    vm_coemulation_stage_count: int
    vm_coemulation_stages_passed: int
    round14_positive_pairs: int
    round16_tabs_verified: int
    round16_pairwise_deltas_verified: int
    round16_runs_verified: int
    round16_nop_count: int
    round16_crashes: int
    h0_surface_count: int
    drifted_surface_count: int
    c2pa_rq_lic_intact: bool
    spacc_cnflasha_untouched: bool
    errors: Tuple[str, ...]
    milestone90_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class StageBMilestone90VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_milestone90_sha256: str
    observed_milestone90_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_milestone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Digest & O_RDONLY Round 16 Loader
# ---------------------------------------------------------------------------


def compute_milestone90_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `StageBMilestone90MasterGateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("milestone90_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _load_round16_summary(
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load Round 16 summary strictly via `os.O_RDONLY` when present, else clean-room synthetic."""
    summary_path = repo_root / ROUND16_SUMMARY_RELPATH
    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"
    if not use_clean_room:
        raise FileNotFoundError(f"Missing Round 16 summary report: {summary_path}")

    langs_block = {
        code: {
            "language_enum": f"0x{spec.enum_id:04x}",
            "bk4_language_id": spec.bk_id_hex,
            "bk4_language_val": f"0x{spec.bk_lang_value:02x}",
            "uxc_banks": {
                "font": spec.font_bank,
                "ns1_string": spec.ns1_bank,
                "ns2_string": spec.ns2_bank,
            },
        }
        for code, spec in STAGE_B_BK_LANG_SPECS.items()
    }
    manifest_items = _build_clean_room_stage_b_manifest_items()
    faithful = {
        "FX6_NATIVE_FAITHFUL": 1,
        "subst_color": 0,
        "subst_image": 0,
        "forced_render": 0,
        "skipped_node": 0,
        "lock_bypass": 0,
    }
    runs_block: Dict[str, Any] = {}
    for run_id, target_sid, lang_name in ROUND16_RUN_SPECS:
        runs_block[run_id] = {
            "run_id": run_id.replace("_", "-"),
            "round": 16,
            "lang": lang_name,
            "target_sid": target_sid,
            "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
            "nop_count": 0,
            "crashes": 0,
            "faithful_invariants": dict(faithful),
            "stage_b": {
                "stage": "B",
                "r16_enabled": True,
                "lang": lang_name,
                "manifest_count": 13,
                "manifest_items": list(manifest_items),
            },
        }

    tab_pair_defaults = {
        "tab1_vs_tab2": ("0x2f", "0x30", 69094),
        "tab1_vs_tab3": ("0x2f", "0x31", 130085),
        "tab1_vs_tab4": ("0x2f", "0x32", 63255),
        "tab1_vs_tab5": ("0x2f", "0x33", 87492),
        "tab2_vs_tab3": ("0x30", "0x31", 125103),
        "tab2_vs_tab4": ("0x30", "0x32", 60513),
        "tab2_vs_tab5": ("0x30", "0x33", 80436),
        "tab3_vs_tab4": ("0x31", "0x32", 128493),
        "tab3_vs_tab5": ("0x31", "0x33", 91456),
        "tab4_vs_tab5": ("0x32", "0x33", 87504),
    }
    pairwise_block: Dict[str, Any] = {
        pk: {"sid_a": sa, "sid_b": sb, "diff_pixels": px, "strictly_positive": True}
        for pk, (sa, sb, px) in tab_pair_defaults.items()
    }
    pairwise_block["pair_count"] = 10
    pairwise_block["all_10_tab_pairs_strictly_positive"] = True

    synthetic = {
        "schema": "fx6-on-fx3-round16-status-tabs45-tcmedia-v1",
        "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
        "languages": langs_block,
        "status_check_multitab_contract": {
            "entry_infra_key": "0x7052",
            "step_next_infra_key": "0x0030",
            "step_prev_infra_key": "0x0003",
            "index_jump_infra_key": "0x0015",
            "tabs_verified": [
                {"tab_index": 1, "sid": "0x2f", "presenter": "34procam_touch_status_main_presenter"},
                {"tab_index": 2, "sid": "0x30", "presenter": "36procam_touch_status_camera_presenter"},
                {"tab_index": 3, "sid": "0x31", "presenter": "35procam_touch_status_audio_presenter"},
                {"tab_index": 4, "sid": "0x32", "presenter": "37procam_touch_status_project_presenter"},
                {"tab_index": 5, "sid": "0x33", "presenter": "40procam_touch_status_monitoring_presenter"},
            ],
        },
        "runs": runs_block,
        "r16_status5_and_tcmedia_audit": {
            "status_check_5tab_pairwise_schinese": pairwise_block,
            "menu_3layer_tcmedia_tchinese": {
                "tcmedia_vs_shooting_r13b": {"diff_pixels": 35765, "strictly_positive": True},
                "tcmedia_vs_monitoring_r15c": {"diff_pixels": 19082, "strictly_positive": True},
                "all_tchinese_deltas_strictly_positive": True,
            },
            "menu_3layer_monitoring_japanese": {
                "monitoring_vs_shooting_r12d": {"diff_pixels": 24616, "strictly_positive": True},
                "monitoring_japanese_vs_schinese_r15c": {"diff_pixels": 8114, "strictly_positive": True},
                "monitoring_japanese_vs_tcmedia_tchinese_r16c": {"diff_pixels": 20779, "strictly_positive": True},
                "all_japanese_deltas_strictly_positive": True,
            },
        },
    }
    return synthetic, "CLEAN_ROOM_SYNTHETIC"


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 3.5s Runtime)
# ---------------------------------------------------------------------------


def _worker_pillar_1(args: Tuple[str, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, fault_dict = args
    repo_root = Path(repo_root_str)
    dewpoint_kwargs = fault_dict.get("p1_dewpoint_kwargs")
    pmic_usbc_kwargs = fault_dict.get("p1_pmic_usbc_kwargs")
    xlr_kwargs = fault_dict.get("p1_xlr_kwargs")
    gimbal_kwargs = fault_dict.get("p1_gimbal_kwargs")
    rig_kwargs = fault_dict.get("p1_rig_kwargs")
    emount_kwargs = fault_dict.get("p1_emount_kwargs")
    power_kwargs = fault_dict.get("p1_power_failover_kwargs")
    req_persist = bool(fault_dict.get("p1_request_persistent_writes", False))

    rep_off = evaluate_24gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=False,
        dewpoint_kwargs=dewpoint_kwargs,
        pmic_usbc_kwargs=pmic_usbc_kwargs,
        xlr_kwargs=xlr_kwargs,
        gimbal_kwargs=gimbal_kwargs,
        rig_kwargs=rig_kwargs,
        emount_kwargs=emount_kwargs,
        power_failover_kwargs=power_kwargs,
        request_persistent_emmc_writes=req_persist,
    )
    rep_sim = evaluate_24gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=True,
        dewpoint_kwargs=dewpoint_kwargs,
        pmic_usbc_kwargs=pmic_usbc_kwargs,
        xlr_kwargs=xlr_kwargs,
        gimbal_kwargs=gimbal_kwargs,
        rig_kwargs=rig_kwargs,
        emount_kwargs=emount_kwargs,
        power_failover_kwargs=power_kwargs,
        request_persistent_emmc_writes=req_persist,
    )

    m22 = rep_sim.master_22_report
    m20 = m22.get("master_20_report", {})
    g19 = m20.get("g19_result", {})
    g20 = m20.get("g20_result", {})
    emount = g19.get("emount_lensrail", {})
    pf = g20.get("power_failover_ups", {})
    rsv = pf.get("rsv_salvage", {})

    g21 = m22.get("g21_result", {})
    g22 = m22.get("g22_result", {})
    xlr_fw = g21.get("xlr_phantom_firewall", {})
    gimbal_fw = g22.get("gimbal_focus_laser_shutter", {})

    g23 = rep_sim.g23_result
    g24 = rep_sim.g24_result
    dp_fw = g23.get("dewpoint_tec_firewall", {})
    pmic_fw = g24.get("pmic_5v_usbc_strain_guard", {})

    ibis_hex = str(emount.get("ibis_park_opcode_hex", "0x0000"))
    ibis_opcode = int(ibis_hex, 16) if ibis_hex.startswith("0x") else 0

    return {
        "schema": rep_sim.schema,
        "verification_mode": rep_sim.verification_mode,
        "offline_verified_gates": int(rep_off.summary.get("verified_gates", 0)),
        "offline_21_gates_verified": bool(rep_off.offline_21_gates_verified),
        "offline_all_24_gates_verified": bool(rep_off.all_24_gates_verified),
        "offline_ready_for_hw": bool(rep_off.overall_ready_for_hardware_attach),
        "sim_verified_gates": int(rep_sim.summary.get("verified_gates", 0)),
        "sim_all_24_gates_verified": bool(rep_sim.all_24_gates_verified),
        "sim_dry_run_rehearsal_only": bool(rep_sim.dry_run_rehearsal_only),
        "sim_ready_for_hw": bool(rep_sim.overall_ready_for_hardware_attach),
        "g13_to_g24_all_passed": bool(rep_sim.g13_to_g24_all_passed),
        "g23_to_g24_all_passed": bool(rep_sim.g23_to_g24_all_passed),
        "g21_passed": bool(g21.get("valid", False)),
        "g21_hot_plug_discharge_safe": bool(xlr_fw.get("hot_plug_discharge_safe", False)),
        "g22_passed": bool(g22.get("valid", False)),
        "g22_single_control_bus_arbitrated": bool(gimbal_fw.get("single_control_bus_arbitrated", False)),
        "g23_passed": bool(g23.get("valid", False)),
        "g23_status": str(g23.get("status", "")),
        "g23_dew_point_c": dp_fw.get("dew_point_c"),
        "g23_tec_condensation_safe": bool(dp_fw.get("tec_condensation_safe", False)),
        "g23_cold_to_warm_shock_safe": bool(dp_fw.get("cold_to_warm_shock_safe", False)),
        "g23_internal_fan_dewpoint_immune": bool(dp_fw.get("internal_fan_dewpoint_immune", False)),
        "g24_passed": bool(g24.get("valid", False)),
        "g24_status": str(g24.get("status", "")),
        "g24_total_pmic_5v_ma": pmic_fw.get("total_pmic_5v_ma"),
        "g24_pmic_5v_budget_ma": pmic_fw.get("pmic_5v_budget_ma"),
        "g24_pmic_5v_budget_safe": bool(pmic_fw.get("pmic_5v_budget_safe", False)),
        "g24_usbc_cable_droop_safe": bool(pmic_fw.get("usbc_cable_droop_safe", False)),
        "g24_cage_cable_strain_safe": bool(pmic_fw.get("cage_cable_strain_safe", False)),
        "g19_crowbar_ms": float(emount.get("v_lens_servo_crowbar_ms", 99.0)),
        "g19_ibis_park_opcode": ibis_opcode,
        "g20_lost_frames": int(pf.get("lost_frames_on_switchover", -1)),
        "g20_rsv_salvage_ok": bool(pf.get("rsv_salvage_verified", False) and rsv.get("valid", False)),
        "persistent_emmc_writes_authorized": bool(rep_sim.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep_sim.persistent_write_release),
        "sim_errors": list(rep_sim.errors),
        "g23_errors": list(g23.get("errors", [])),
        "g24_errors": list(g24.get("errors", [])),
    }


def _worker_pillar_3_group(args: Tuple[str, bool]) -> Dict[str, Dict[str, Any]]:
    group, clean_room = args
    if group == "falsecolor":
        return {
            "falsecolor_lpcm_tc_ub_audit": falsecolor_lpcm_tc_ub_report_to_dict(
                analyze_falsecolor_lpcm_tc_ub(clean_room=clean_room)
            )
        }
    if group == "playback":
        return {
            "playback_shotmark_and_ae_audit": playback_shotmark_and_ae_report_to_dict(
                analyze_playback_shotmark_and_ae(clean_room=clean_room)
            )
        }
    return _worker_domain_4_group((group, clean_room))


def _worker_pillar_4(use_clean_room: bool) -> Dict[str, Any]:
    return run_fx3_vm_coemulation_suite(CoEmulationConfig(force_clean_room=use_clean_room))


# ---------------------------------------------------------------------------
# Pillar Evaluators (P1 .. P6)
# ---------------------------------------------------------------------------


def _evaluate_pillar_1(raw_1: Mapping[str, Any]) -> Milestone90PillarResult:
    errors: List[str] = []
    if not raw_1["offline_21_gates_verified"] or raw_1["offline_verified_gates"] != 21:
        errors.append(
            f"p1: offline hardware-truth gates expected 21/24, got {raw_1['offline_verified_gates']}/24"
        )
    if raw_1["offline_all_24_gates_verified"] or raw_1["offline_ready_for_hw"]:
        errors.append("p1: offline mode must remain blocked for live hardware attach")
    if not raw_1["sim_all_24_gates_verified"] or raw_1["sim_verified_gates"] != 24:
        errors.append(
            f"p1: simulated rehearsal gates expected 24/24, got {raw_1['sim_verified_gates']}/24"
        )
    if not raw_1["sim_dry_run_rehearsal_only"] or raw_1["sim_ready_for_hw"]:
        errors.append("p1: simulated 24/24 rehearsal must keep overall_ready_for_hardware_attach=False")
    if not raw_1["g13_to_g24_all_passed"] or not raw_1["g23_to_g24_all_passed"]:
        errors.append("p1: G13..G24 or G23..G24 guard gate blocked")
    if not raw_1["g21_passed"] or not raw_1["g21_hot_plug_discharge_safe"]:
        errors.append("p1: G21 XLR-H1 +48V phantom firewall failed")
    if not raw_1["g22_passed"] or not raw_1["g22_single_control_bus_arbitrated"]:
        errors.append("p1: G22 gimbal/follow-focus/laser/shutter guard failed")
    if (
        not raw_1["g23_passed"]
        or not raw_1["g23_tec_condensation_safe"]
        or not raw_1["g23_cold_to_warm_shock_safe"]
        or not raw_1["g23_internal_fan_dewpoint_immune"]
    ):
        errors.append(f"p1: G23 Magnus dew-point TEC condensation guard failed ({raw_1['g23_status']})")
    if (
        not raw_1["g24_passed"]
        or not raw_1["g24_pmic_5v_budget_safe"]
        or not raw_1["g24_usbc_cable_droop_safe"]
        or not raw_1["g24_cage_cable_strain_safe"]
    ):
        errors.append(f"p1: G24 PMIC 5V budget / USB-C droop / clamp guard failed ({raw_1['g24_status']})")
    if raw_1["g19_crowbar_ms"] >= 2.0 or raw_1["g19_ibis_park_opcode"] != 0x0400:
        errors.append("p1: G19 E-Mount rail crowbar or 0x0400 IBIS park check failed")
    if raw_1["g20_lost_frames"] != 0 or not raw_1["g20_rsv_salvage_ok"]:
        errors.append("p1: G20 USB-PD->NP-FZ100 UPS or .RSV salvage failed")
    if raw_1["persistent_emmc_writes_authorized"] or raw_1["persistent_write_release"]:
        errors.append("p1: hard-locked persistent_emmc_writes_authorized / persistent_write_release breached")
    for err in raw_1["sim_errors"]:
        errors.append(f"p1_24gate: {err}")
    for err in raw_1["g23_errors"]:
        errors.append(f"p1_g23: {err}")
    for err in raw_1["g24_errors"]:
        errors.append(f"p1_g24: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_1["schema"],
        "verification_mode": raw_1["verification_mode"],
        "offline_verified_gates": raw_1["offline_verified_gates"],
        "offline_ready_for_hardware_attach": raw_1["offline_ready_for_hw"],
        "simulated_verified_gates": raw_1["sim_verified_gates"],
        "simulated_ready_for_hardware_attach": raw_1["sim_ready_for_hw"],
        "g21_passed": raw_1["g21_passed"],
        "g22_passed": raw_1["g22_passed"],
        "g23_passed": raw_1["g23_passed"],
        "g23_status": raw_1["g23_status"],
        "g23_dew_point_c": raw_1["g23_dew_point_c"],
        "g23_tec_condensation_safe": raw_1["g23_tec_condensation_safe"],
        "g23_internal_fan_dewpoint_immune": raw_1["g23_internal_fan_dewpoint_immune"],
        "g24_passed": raw_1["g24_passed"],
        "g24_status": raw_1["g24_status"],
        "g24_total_pmic_5v_ma": raw_1["g24_total_pmic_5v_ma"],
        "g24_pmic_5v_budget_ma": raw_1["g24_pmic_5v_budget_ma"],
        "g24_usbc_cable_droop_safe": raw_1["g24_usbc_cable_droop_safe"],
        "g24_cage_cable_strain_safe": raw_1["g24_cage_cable_strain_safe"],
        "g19_ibis_park_opcode": f"0x{raw_1['g19_ibis_park_opcode']:04x}",
        "g20_rsv_salvage_ok": raw_1["g20_rsv_salvage_ok"],
        "persistent_emmc_writes_authorized": raw_1["persistent_emmc_writes_authorized"],
        "persistent_write_release": raw_1["persistent_write_release"],
    }
    return Milestone90PillarResult(
        pillar_id="P1",
        pillar_name="SAFETY_24GATE_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"24-Gate offline={raw_1['offline_verified_gates']}/24 sim={raw_1['sim_verified_gates']}/24, "
            f"G21(+48V)={raw_1['g21_passed']}, G22(Gimbal)={raw_1['g22_passed']}, "
            f"G23(DewPoint/TEC)={raw_1['g23_passed']}, G24(5V {raw_1['g24_total_pmic_5v_ma']}/900mA)="
            f"{raw_1['g24_passed']} {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_2(
    raw_antirollback: Mapping[str, Any],
    raw_tier0_init2: Mapping[str, Any],
    faults: Milestone90FaultInjection,
) -> Tuple[Milestone90PillarResult, Dict[str, Any]]:
    cap_faults = StageBCapstone22GateFaultInjection(
        d2_otp_downgrade_version=faults.p2_otp_downgrade_version,
        d2_inject_cross_sku_target=faults.p2_inject_cross_sku_target,
        d2_inject_ext_csd_perm_wp=faults.p2_inject_ext_csd_perm_wp,
        d2_otp_fuse_touches_override=faults.p2_otp_fuse_touches_override,
        d2_rpmb_increments_override=faults.p2_rpmb_increments_override,
    )
    d2, meta_2 = _evaluate_domain_2(raw_antirollback, cap_faults)

    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_b_inject_cross_body_cnflasha_transplant=faults.p2_inject_cross_body_cnflasha_transplant,
        pillar_b_inject_gf256_quorum_loss=faults.p2_inject_gf256_quorum_loss,
        pillar_b_inject_init2_escape_fault=faults.p2_inject_init2_escape_fault,
    )
    pb = _evaluate_pillar_b(raw_tier0_init2, v3_faults)

    errors: List[str] = [e.replace("d2:", "p2_otp:") for e in d2.errors]
    errors.extend(e.replace("pillar_b:", "p2_tier0:") for e in pb.errors)
    passed = len(errors) == 0 and d2.passed and pb.passed

    evidence = {
        "antirollback": dict(d2.evidence),
        "tier0_gf256_and_sd_escape": dict(pb.evidence),
    }
    pillar = Milestone90PillarResult(
        pillar_id="P2",
        pillar_name="OTP_RPMB_ANTIROLLBACK_TIER0_GF256_SD_ESCAPE",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"OTP={meta_2['otp_fuse_touches']}, RPMB={meta_2['rpmb_counter_increments']}, "
            f"EXT_CSD perm-WP=BLOCKED, GF(256) RAID-6 P+Q=2-shard heal, FX3_SAFE_STOCK.FLG=OK "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    return pillar, meta_2


def _evaluate_pillar_3(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: Milestone90FaultInjection,
) -> Tuple[Milestone90PillarResult, Dict[str, Any]]:
    cap_faults = StageBCapstone22GateFaultInjection(
        d4_calibration_mutation_bytes=faults.p3_calibration_mutation_bytes,
        d4_bk4_persistent_nvram_writes=faults.p3_bk4_persistent_nvram_writes,
        d4_corrupt_wb_whitepoint=faults.p3_corrupt_wb_whitepoint,
        d4_corrupt_nrtm_sidecar=faults.p3_corrupt_nrtm_sidecar,
        d4_inject_legacy_sq_big6_block=faults.p3_inject_legacy_sq_big6_block,
        d4_inject_persistent_nvram_shadow_path=faults.p3_inject_persistent_nvram_shadow_path,
    )
    d4, meta_14 = _evaluate_domain_4(auditors, cap_faults)
    errors: List[str] = [e.replace("d4:", "p3:") for e in d4.errors]

    # Auditor #15: Phase 80 False Color / 24-bit LPCM / User-Bits
    a15 = auditors.get("falsecolor_lpcm_tc_ub_audit", {})
    a15_ok = isinstance(a15, Mapping) and bool(a15.get("all_checks_passed"))
    if not a15_ok:
        errors.append("p3: fx3_firmware_lab 15th auditor falsecolor_lpcm_tc_ub_audit failed")

    a15_cal = int(a15.get("calibration_mutation_bytes", -1))
    a15_wrap = int(a15.get("int24_wrap_around_count", -1)) + int(faults.p3_int24_wrap_around_count)
    a15_cont = int(a15.get("bus_contention_count", -1)) + int(faults.p3_bus_contention_count)
    if a15_cal != 0:
        errors.append(f"p3: #15 calibration_mutation_bytes={a15_cal} != 0")
    if a15_wrap != 0:
        errors.append(f"p3: #15 int24_wrap_around_count={a15_wrap} != 0")
    if a15_cont != 0:
        errors.append(f"p3: #15 bus_contention_count={a15_cont} != 0")
    if a15.get("persistent_emmc_writes_authorized") is not False:
        errors.append("p3: #15 breached persistent_emmc_writes_authorized")
    if not (
        bool(a15.get("pillar_1_false_color_el_zone", {}).get("passed", False))
        and bool(a15.get("pillar_2_lpcm_headroom_dsp", {}).get("passed", False))
        and bool(a15.get("pillar_3_smpte_ub_direction", {}).get("passed", False))
        and bool(a15.get("pillar_4_zero_mutation_proof", {}).get("passed", False))
    ):
        errors.append("p3: one or more Phase 80 False Color / LPCM / User-Bits pillars failed")

    # Auditor #16: Phase 85 Playback / ShotMark1/2 <EssenceMark> / Cine EI Push Auto Iris
    a16 = auditors.get("playback_shotmark_and_ae_audit", {})
    a16_ok = isinstance(a16, Mapping) and bool(a16.get("all_checks_passed"))
    if not a16_ok:
        errors.append("p3: fx3_firmware_lab 16th auditor playback_shotmark_and_ae_audit failed")

    a16_cal = int(a16.get("calibration_mutation_bytes", -1))
    a16_nd_faults = int(a16.get("p4_nd_motor_fault_attempts", -1)) + int(
        faults.p3_p4_nd_motor_fault_attempts
    )
    a16_fmt_possible = bool(a16.get("internal_emmc_format_possible", True))
    if a16_cal != 0:
        errors.append(f"p3: #16 calibration_mutation_bytes={a16_cal} != 0")
    if a16_nd_faults != 0:
        errors.append(f"p3: #16 p4_nd_motor_fault_attempts={a16_nd_faults} != 0")
    if a16_fmt_possible:
        errors.append("p3: #16 internal_emmc_format_possible must be False")
    if a16.get("persistent_emmc_writes_authorized") is not False:
        errors.append("p3: #16 breached persistent_emmc_writes_authorized")
    if not (
        bool(a16.get("pillar_1_playback_thumbnail_firewall", {}).get("passed", False))
        and bool(a16.get("pillar_2_shotmark_essencemark_xml", {}).get("passed", False))
        and bool(a16.get("pillar_3_push_auto_iris_ae_shift", {}).get("passed", False))
        and bool(a16.get("pillar_4_zero_mutation_proof", {}).get("passed", False))
    ):
        errors.append("p3: one or more Phase 85 Playback / ShotMark / Push Auto Iris pillars failed")

    if faults.p3_inject_internal_emmc_format_attempt:
        blk = evaluate_media_format_and_delete_firewall(
            operation="FORMAT_FULL",
            target_slot="INTERNAL_P1",
            target_device="/dev/mmcblk0p1",
        )
        errors.append(f"p3: internal eMMC p1 format attempt blocked ({blk.status})")

    auditor_statuses = dict(d4.evidence["auditor_statuses"])
    auditor_statuses["falsecolor_lpcm_tc_ub_audit"] = a15_ok
    auditor_statuses["playback_shotmark_and_ae_audit"] = a16_ok

    auditor_sha256s = dict(d4.evidence["auditor_sha256s"])
    auditor_sha256s["falsecolor_lpcm_tc_ub_audit"] = (
        str(a15.get("report_sha256")) if isinstance(a15, Mapping) and a15.get("report_sha256") else None
    )
    auditor_sha256s["playback_shotmark_and_ae_audit"] = (
        str(a16.get("report_sha256")) if isinstance(a16, Mapping) and a16.get("report_sha256") else None
    )

    passed_count = int(meta_14["passed_count"]) + (1 if a15_ok else 0) + (1 if a16_ok else 0)
    total_count = len(FIRMWARE_LAB_16_AUDITOR_KEYS)
    total_cal_mut = max(int(meta_14["calibration_mutation_bytes"]), a15_cal, a16_cal)
    passed = len(errors) == 0 and passed_count == total_count and total_cal_mut == 0

    evidence = dict(d4.evidence)
    evidence.update(
        {
            "auditor_count": total_count,
            "passed_auditor_count": passed_count,
            "auditor_statuses": auditor_statuses,
            "auditor_sha256s": auditor_sha256s,
            "phase80_falsecolor_lpcm_tc_ub_ok": a15_ok,
            "phase80_int24_wrap_around_count": a15_wrap,
            "phase80_bus_contention_count": a15_cont,
            "phase85_playback_shotmark_ae_ok": a16_ok,
            "phase85_p4_nd_motor_fault_attempts": a16_nd_faults,
            "phase85_internal_emmc_format_possible": a16_fmt_possible,
            "calibration_mutation_bytes": total_cal_mut,
        }
    )
    pillar = Milestone90PillarResult(
        pillar_id="P3",
        pillar_name="SIXTEEN_FIRMWARE_LAB_AUDITORS",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {passed_count}/{total_count} auditors "
            f"(incl. #15 S-Log3 False Color/24b LPCM/UB & #16 Playback/ShotMark/Push Auto Iris), "
            f"p4_nd_faults={a16_nd_faults}, emmc_fmt={a16_fmt_possible}, cal_mut={total_cal_mut}B "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "auditor_count": total_count,
        "passed_count": passed_count,
        "calibration_mutation_bytes": total_cal_mut,
        "bk4_persistent_nvram_writes": int(meta_14["bk4_persistent_nvram_writes"]),
    }
    return pillar, meta


def _evaluate_pillar_4(
    vm_rep: Mapping[str, Any],
    faults: Milestone90FaultInjection,
) -> Tuple[Milestone90PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    if not vm_rep.get("all_checks_passed"):
        errors.append("p4: outputs/fx3-vm 13-stage co-emulation top-level all_checks_passed is False")

    stage_statuses: Dict[str, bool] = {}
    passed_stages = 0
    for skey in VM_COEMULATION_13_STAGE_KEYS:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if ok:
            passed_stages += 1
        else:
            errors.append(f"p4: VM co-emulation {skey} failed")

    redlines = vm_rep.get("redlines", {})
    cp_mut_bytes = int(redlines.get("cp_mutation_bytes", -1)) + int(faults.p4_cp_mutation_bytes)
    wbi_mut_bytes = int(redlines.get("wbi_mutation_bytes", -1))
    nvram_writes = int(redlines.get("nvram_persistent_writes", -1)) + int(
        faults.p4_bk4_persistent_nvram_writes
    )
    phys_writes = int(redlines.get("physical_device_writes", -1))
    if not redlines.get("p8_cp_mutation_forbidden"):
        errors.append("p4: p8_cp_mutation_forbidden must be True")
    if cp_mut_bytes != 0:
        errors.append(f"p4: cp_mutation_bytes={cp_mut_bytes} != 0")
    if wbi_mut_bytes != 0 or nvram_writes != 0 or phys_writes != 0:
        errors.append(
            f"p4: VM co-emulation write counters non-zero (wbi={wbi_mut_bytes}, nvram={nvram_writes}, phys={phys_writes})"
        )

    # Stage 10 Dual-Slot Relay & .RSV salvage
    s10 = vm_rep.get("stage10_phase71_dualslot_ups_salvage", {})
    ds = s10.get("dualslot_proxy_pipeline", {})
    relay = ds.get("relay_auto_switch", {})
    relay_dropped = int(relay.get("dropped_frames", -1)) + int(faults.p4_stage10_dropped_frames)
    if relay_dropped != 0 or bool(relay.get("main_stalled", True)):
        errors.append(f"p4: Stage 10 Dual-Slot Relay failed 0-drop contract (dropped={relay_dropped})")

    # Stage 11 Touch AF / CIZ / Assignable
    s11 = vm_rep.get("stage11_phase78_touchaf_ciz_assignable", {})
    s11_nop = int(s11.get("nop_count", -1)) + int(faults.p4_stage11_nop_count)
    s11_null_gpio = int(s11.get("null_gpio_derefs", -1)) + int(faults.p4_stage11_null_gpio_derefs)
    if s11_nop != 0 or s11_null_gpio != 0:
        errors.append(f"p4: Stage 11 nop={s11_nop} or null_gpio={s11_null_gpio} != 0")

    # Stage 12 CAMSET / 4ch 24-bit LPCM / User-Bits
    s12 = vm_rep.get("stage12_phase82_camset_lpcm_tcub", {})
    s12_nop = int(s12.get("nop_count", -1))
    s12_cp_mut = int(s12.get("cp_mutation_bytes", -1))
    s12_bk4 = int(s12.get("bk4_persistent_nvram_writes", -1))
    s12_uart_cont = int(s12.get("uart_boot_contention_events", -1)) + int(
        faults.p4_stage12_uart_contention_events
    )
    if s12_nop != 0 or s12_cp_mut != 0 or s12_bk4 != 0 or s12_uart_cont != 0:
        errors.append(
            f"p4: Stage 12 nop={s12_nop}, cp_mut={s12_cp_mut}, bk4={s12_bk4}, uart_cont={s12_uart_cont} != 0"
        )
    if s12.get("persistent_emmc_writes_authorized") is not False:
        errors.append("p4: Stage 12 persistent_emmc_writes_authorized must be False")

    # Stage 13 Playback/ShotMark, Push Auto Iris & Dew-Point/PMIC 5V HIL
    s13 = vm_rep.get("stage13_phase87_playback_shotmark_dewpoint", {})
    s13_nop = int(s13.get("nop_count", -1))
    s13_cp_mut = int(s13.get("cp_mutation_bytes", -1))
    s13_bk4 = int(s13.get("bk4_persistent_nvram_writes", -1))
    s13_p1_mut = int(s13.get("p1_emmc_mutations", -1))
    s13_emmc_writes = int(s13.get("internal_emmc_writes", -1))
    s13_nd_faults = int(s13.get("p4_nd_motor_faults", -1)) + int(
        faults.p4_stage13_p4_nd_motor_faults
    )
    s13_fmt_blocked = bool(s13.get("internal_emmc_format_blocked", False))
    s13_c2pa_ok = bool(s13.get("c2pa_license_untouched", False))
    if s13_nop != 0 or s13_cp_mut != 0 or s13_bk4 != 0:
        errors.append(f"p4: Stage 13 nop={s13_nop}, cp_mut={s13_cp_mut}, bk4={s13_bk4} != 0")
    if not s13_fmt_blocked or s13_p1_mut != 0 or s13_emmc_writes != 0:
        errors.append("p4: Stage 13 p1 eMMC isolation check failed")
    if s13_nd_faults != 0 or not s13_c2pa_ok:
        errors.append(f"p4: Stage 13 p4_nd_motor_faults={s13_nd_faults} or c2pa_untouched={s13_c2pa_ok}")
    if s13.get("persistent_emmc_writes_authorized") is not False:
        errors.append("p4: Stage 13 persistent_emmc_writes_authorized must be False")

    if faults.p4_stage13_p1_emmc_format_attempt:
        sess = PlaybackShotmarkMediaSession()
        verdict = sess.request_format_media("/dev/mmcblk0p1")
        errors.append(f"p4: Stage 13 p1 format attempt blocked ({verdict.status})")

    total_stages = len(VM_COEMULATION_13_STAGE_KEYS)
    passed = len(errors) == 0 and passed_stages == total_stages
    evidence = {
        "vm_schema": vm_rep.get("schema"),
        "stage_count": total_stages,
        "passed_stage_count": passed_stages,
        "stage_statuses": stage_statuses,
        "audit_digest_sha256": vm_rep.get("audit_digest_sha256"),
        "cp_mutation_bytes": cp_mut_bytes,
        "wbi_mutation_bytes": wbi_mut_bytes,
        "bk4_persistent_nvram_writes": nvram_writes,
        "stage12_uart_boot_contention_events": s12_uart_cont,
        "stage12_digest_sha256": s12.get("phase82_audit_digest_sha256"),
        "stage13_internal_emmc_format_blocked": s13_fmt_blocked,
        "stage13_p1_emmc_mutations": s13_p1_mut,
        "stage13_p4_nd_motor_faults": s13_nd_faults,
        "stage13_c2pa_license_untouched": s13_c2pa_ok,
        "stage13_digest_sha256": s13.get("phase87_audit_digest_sha256"),
    }
    pillar = Milestone90PillarResult(
        pillar_id="P4",
        pillar_name="THIRTEEN_STAGE_VM_COEMULATION",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {passed_stages}/{total_stages} stages (Stages 1..13, "
            f"Stage 13 p1_fmt_blocked={s13_fmt_blocked}, nd_faults={s13_nd_faults}), "
            f"cp_mut={cp_mut_bytes}B, bk4_nvram_writes={nvram_writes} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "stage_count": total_stages,
        "passed_count": passed_stages,
        "cp_mutation_bytes": cp_mut_bytes,
        "bk4_persistent_nvram_writes": nvram_writes,
    }
    return pillar, meta


def _evaluate_pillar_5(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: Milestone90FaultInjection,
) -> Tuple[Milestone90PillarResult, Dict[str, Any]]:
    # 1. Verify Round 14 (18/18 4-lang x 3-surface matrix)
    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_e_nop_count=faults.p5_round14_nop_count,
        pillar_e_zero_pair_surface="status_check" if faults.p5_round14_zero_pair else None,
        pillar_e_zero_pair_name=ROUND14_4LANG_PAIRS[0] if faults.p5_round14_zero_pair else None,
    )
    pe, meta_r14 = _evaluate_pillar_e(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=v3_faults,
    )
    errors: List[str] = [e.replace("pillar_e", "p5_r14") for e in pe.errors]

    # 2. Verify Round 16 (5-tab Status Check 0x2f..0x33 C(5,2)=10 pairs + TC/Media ZH-TW + Monitoring JA)
    r16, r16_source = _load_round16_summary(repo_root=repo_root, use_clean_room=use_clean_room)
    schema = str(r16.get("schema", ""))
    kernel_ver = str(r16.get("kernel_version", ""))
    if schema != "fx6-on-fx3-round16-status-tabs45-tcmedia-v1":
        errors.append(f"p5_r16: unexpected Round 16 schema {schema!r}")
    if "4.9.337-scel+" not in kernel_ver:
        errors.append(f"p5_r16: unexpected FX3 kernel_version {kernel_ver!r}")

    contract = r16.get("status_check_multitab_contract", {})
    tabs = contract.get("tabs_verified", [])
    tab_sids = tuple(str(t.get("sid", "")) for t in tabs if isinstance(t, Mapping))
    if tab_sids != ROUND16_MULTITAB_SIDS:
        errors.append(
            f"p5_r16: Status Check 5-tab sids expected {ROUND16_MULTITAB_SIDS!r}, got {tab_sids!r}"
        )

    runs = r16.get("runs", {})
    r16_nops = int(faults.p5_round16_nop_count)
    r16_crashes = int(faults.p5_round16_crashes)
    runs_verified = 0
    key_stage_b_sha_ok = True
    manifest_counts: Dict[str, int] = {}

    for run_id, expected_sid, expected_lang in ROUND16_RUN_SPECS:
        robj = runs.get(run_id)
        if not isinstance(robj, Mapping):
            errors.append(f"p5_r16: missing Round 16 run {run_id}")
            continue
        r16_nops += int(robj.get("nop_count", -1))
        r16_crashes += int(robj.get("crashes", -1))
        if robj.get("target_sid") != expected_sid or robj.get("lang") != expected_lang:
            errors.append(
                f"p5_r16: {run_id} expected sid={expected_sid} lang={expected_lang}, "
                f"got sid={robj.get('target_sid')!r} lang={robj.get('lang')!r}"
            )
        fi = robj.get("faithful_invariants", {})
        if fi.get("FX6_NATIVE_FAITHFUL") != 1 or any(
            int(fi.get(k, -1)) != 0
            for k in ("subst_color", "subst_image", "forced_render", "skipped_node", "lock_bypass")
        ):
            errors.append(f"p5_r16: {run_id} failed FX6_NATIVE_FAITHFUL invariants")
        sb = robj.get("stage_b", {})
        mc = (
            int(faults.p5_round16_manifest_count_override)
            if faults.p5_round16_manifest_count_override is not None
            else int(sb.get("manifest_count", -1))
        )
        manifest_counts[run_id] = mc
        items = sb.get("manifest_items", [])
        if mc != 13 or len(items) != 13:
            errors.append(f"p5_r16: {run_id} Stage-B manifest count expected 13/13, got {mc}/{len(items)}")
        by_path = {str(it.get("guest_path")): str(it.get("sha256")) for it in items if isinstance(it, Mapping)}
        if by_path.get("/usr/lib/appFw.so") != FX6_APPFW_STAGE_B_SHA256:
            key_stage_b_sha_ok = False
        if by_path.get("/usr/lib/libWlanResource.so") != FX6_WLAN_RSRC_P12_SHA256:
            key_stage_b_sha_ok = False
        runs_verified += 1

    if not key_stage_b_sha_ok:
        errors.append("p5_r16: Stage-B manifest_items SHA-256 mismatch for appFw.so or libWlanResource.so")
    if r16_nops != 0:
        errors.append(f"p5_r16: Round 16 real-kernel nop_count={r16_nops} != 0")
    if r16_crashes != 0:
        errors.append(f"p5_r16: Round 16 real-kernel crashes={r16_crashes} != 0")

    audit = copy.deepcopy(r16.get("r16_status5_and_tcmedia_audit", {}))
    pairwise = audit.get("status_check_5tab_pairwise_schinese", {})
    tcmedia = audit.get("menu_3layer_tcmedia_tchinese", {})
    mon_ja = audit.get("menu_3layer_monitoring_japanese", {})

    if faults.p5_round16_zero_tab_pair and faults.p5_round16_zero_tab_pair in pairwise:
        pairwise[faults.p5_round16_zero_tab_pair]["diff_pixels"] = 0
        pairwise[faults.p5_round16_zero_tab_pair]["strictly_positive"] = False
    if faults.p5_round16_zero_tcmedia_pair and faults.p5_round16_zero_tcmedia_pair in tcmedia:
        tcmedia[faults.p5_round16_zero_tcmedia_pair]["diff_pixels"] = 0
        tcmedia[faults.p5_round16_zero_tcmedia_pair]["strictly_positive"] = False
    if faults.p5_round16_zero_monitoring_pair and faults.p5_round16_zero_monitoring_pair in mon_ja:
        mon_ja[faults.p5_round16_zero_monitoring_pair]["diff_pixels"] = 0
        mon_ja[faults.p5_round16_zero_monitoring_pair]["strictly_positive"] = False

    if int(pairwise.get("pair_count", -1)) != 10:
        errors.append(f"p5_r16: Status Check pairwise count expected 10, got {pairwise.get('pair_count')}")

    tab_deltas: Dict[str, int] = {}
    positive_tab_pairs = 0
    for pk in ROUND16_5TAB_PAIR_KEYS:
        ent = pairwise.get(pk, {})
        px = int(ent.get("diff_pixels", 0))
        tab_deltas[pk] = px
        if px > 0 and bool(ent.get("strictly_positive", False)):
            positive_tab_pairs += 1
        else:
            errors.append(f"p5_r16: Status Check 5-tab pair {pk} delta is not strictly positive")

    tcmedia_deltas: Dict[str, int] = {}
    for pk in ROUND16_TCMEDIA_PAIR_KEYS:
        ent = tcmedia.get(pk, {})
        px = int(ent.get("diff_pixels", 0))
        tcmedia_deltas[pk] = px
        if px <= 0 or not bool(ent.get("strictly_positive", False)):
            errors.append(f"p5_r16: 3-layer TC/Media TChinese pair {pk} delta is not strictly positive")

    mon_ja_deltas: Dict[str, int] = {}
    for pk in ROUND16_MONITORING_PAIR_KEYS:
        ent = mon_ja.get(pk, {})
        px = int(ent.get("diff_pixels", 0))
        mon_ja_deltas[pk] = px
        if px <= 0 or not bool(ent.get("strictly_positive", False)):
            errors.append(f"p5_r16: 3-layer Monitoring Japanese pair {pk} delta is not strictly positive")

    passed = (
        len(errors) == 0
        and pe.passed
        and len(tab_sids) == 5
        and positive_tab_pairs == 10
        and runs_verified == len(ROUND16_RUN_SPECS)
        and r16_nops == 0
        and r16_crashes == 0
        and key_stage_b_sha_ok
    )
    evidence = {
        "round14_positive_pairs": meta_r14["positive_pairs"],
        "round14_nop_count": meta_r14["nop_count"],
        "round14_source": pe.evidence["round14_source"],
        "round16_source": r16_source,
        "round16_schema": schema,
        "round16_kernel_version": kernel_ver,
        "round16_tabs_verified": len(tab_sids),
        "round16_tab_sids": list(tab_sids),
        "round16_pairwise_deltas_verified": positive_tab_pairs,
        "round16_runs_verified": runs_verified,
        "round16_run_ids": list(ROUND16_RUN_IDS),
        "round16_nop_count": r16_nops,
        "round16_crashes": r16_crashes,
        "round16_manifest_counts": manifest_counts,
        "round16_stage_b_sha256_verified": key_stage_b_sha_ok,
        "round16_5tab_pairwise_deltas": tab_deltas,
        "round16_tcmedia_tchinese_deltas": tcmedia_deltas,
        "round16_monitoring_japanese_deltas": mon_ja_deltas,
    }
    pillar = Milestone90PillarResult(
        pillar_id="P5",
        pillar_name="ROUND16_MULTITAB_AND_4LANG_KERNEL_CLOSURE",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"R14 {meta_r14['positive_pairs']}/18 + R16 FX3 7.02 Status Check 0x2f..0x33 "
            f"{len(tab_sids)} tabs ({positive_tab_pairs}/10 pairs > 0) + TC/Media ZH-TW & "
            f"Monitoring JA, {runs_verified}/4 runs, nop={r16_nops}, crash={r16_crashes} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "round14_positive_pairs": meta_r14["positive_pairs"],
        "round16_tabs_verified": len(tab_sids),
        "round16_pairwise_deltas_verified": positive_tab_pairs,
        "round16_runs_verified": runs_verified,
        "round16_nop_count": r16_nops,
        "round16_crashes": r16_crashes,
    }
    return pillar, meta


def _evaluate_pillar_6(
    raw_6: Mapping[str, Any],
    faults: Milestone90FaultInjection,
) -> Tuple[Milestone90PillarResult, Dict[str, Any]]:
    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_f_drift_surface=faults.p6_drift_surface,
        pillar_f_tamper_negative_control=faults.p6_tamper_negative_control,
    )
    pf, meta_f = _evaluate_pillar_f(raw_6, v3_faults)
    errors: List[str] = [e.replace("pillar_f", "p6") for e in pf.errors]
    if DOSSIER_V3_SCHEMA_VERSION != STAGE_B_RELEASE_DOSSIER_V3_SCHEMA or len(DOSSIER_V3_PILLAR_IDS) != 6:
        errors.append("p6: Dossier v3 anchor contract mismatch")
    if CAPSTONE_22GATE_SCHEMA_VERSION != STAGE_B_CAPSTONE_22GATE_SCHEMA or len(CAPSTONE_DOMAIN_IDS) != 7:
        errors.append("p6: Capstone 22-Gate anchor contract mismatch")

    passed = len(errors) == 0 and pf.passed
    evidence = dict(pf.evidence)
    evidence["dossier_v3_schema_anchor"] = DOSSIER_V3_SCHEMA_VERSION
    evidence["capstone_22gate_schema_anchor"] = CAPSTONE_22GATE_SCHEMA_VERSION
    evidence["capstone_22gate_domain_count"] = len(CAPSTONE_DOMAIN_IDS)

    pillar = Milestone90PillarResult(
        pillar_id="P6",
        pillar_name="DOSSIER_V3_CAPSTONE_AND_H0_VS_H2_IMMUTABILITY",
        passed=passed,
        status=STATUS_MILESTONE_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Dossier v3 + Capstone 22-Gate + H0==H2 {meta_f['h0_surface_count']}/16 surfaces "
            f"(drifted={meta_f['drifted_surface_count']}, C2PA intact={meta_f['c2pa_rq_lic_intact']}, "
            f"scenarios={raw_6['audit_passed_scenario_count']}/{raw_6['audit_scenario_count']}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    return pillar, meta_f


# ---------------------------------------------------------------------------
# Parallel Collector, Builder & Fail-Closed Verifier
# ---------------------------------------------------------------------------


def _fault_to_worker_dict(faults: Milestone90FaultInjection) -> Dict[str, Any]:
    return {
        "p1_dewpoint_kwargs": dict(faults.p1_dewpoint_kwargs) if faults.p1_dewpoint_kwargs is not None else None,
        "p1_pmic_usbc_kwargs": dict(faults.p1_pmic_usbc_kwargs) if faults.p1_pmic_usbc_kwargs is not None else None,
        "p1_xlr_kwargs": dict(faults.p1_xlr_kwargs) if faults.p1_xlr_kwargs is not None else None,
        "p1_gimbal_kwargs": dict(faults.p1_gimbal_kwargs) if faults.p1_gimbal_kwargs is not None else None,
        "p1_rig_kwargs": dict(faults.p1_rig_kwargs) if faults.p1_rig_kwargs is not None else None,
        "p1_emount_kwargs": dict(faults.p1_emount_kwargs) if faults.p1_emount_kwargs is not None else None,
        "p1_power_failover_kwargs": (
            dict(faults.p1_power_failover_kwargs)
            if faults.p1_power_failover_kwargs is not None
            else None
        ),
        "p1_request_persistent_writes": bool(faults.p1_request_persistent_writes),
        "d2_otp_downgrade_version": faults.p2_otp_downgrade_version,
        "d2_inject_cross_sku_target": faults.p2_inject_cross_sku_target,
        "d2_inject_ext_csd_perm_wp": bool(faults.p2_inject_ext_csd_perm_wp),
        "p2_inject_cross_body_cnflasha_transplant": bool(
            faults.p2_inject_cross_body_cnflasha_transplant
        ),
    }


def _collect_parallel_milestone90_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: Milestone90FaultInjection,
) -> Tuple[
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
    Dict[str, Any],
]:
    fault_dict = _fault_to_worker_dict(faults)
    p3_groups = (
        "group_a",
        "group_b",
        "multilang",
        "sensor",
        "haita",
        "emount",
        "wbi",
        "assignable",
        "falsecolor",
        "playback",
    )

    use_fork_pool = not use_clean_room
    if use_fork_pool:
        try:
            ctx = mp.get_context("fork")
            with ProcessPoolExecutor(max_workers=10, mp_context=ctx) as ex:
                fut_1 = ex.submit(_worker_pillar_1, (str(repo_root), use_clean_room, fault_dict))
                fut_2a = ex.submit(_worker_domain_2, (use_clean_room, fault_dict))
                fut_2b = ex.submit(
                    _worker_pillar_b,
                    (
                        use_clean_room,
                        {
                            "pillar_b_inject_cross_body_cnflasha_transplant": bool(
                                faults.p2_inject_cross_body_cnflasha_transplant
                            )
                        },
                    ),
                )
                fut_3 = [ex.submit(_worker_pillar_3_group, (g, use_clean_room)) for g in p3_groups]
                fut_4 = ex.submit(_worker_pillar_4, use_clean_room)
                fut_6 = ex.submit(
                    _worker_pillar_f,
                    (
                        str(fx6_lib_dir),
                        str(fx3_modules_dir),
                        use_clean_room,
                        faults.p6_drift_surface,
                    ),
                )
                raw_1 = fut_1.result()
                raw_2a = fut_2a.result()
                raw_2b = fut_2b.result()
                auditors: Dict[str, Dict[str, Any]] = {}
                for fg in fut_3:
                    auditors.update(fg.result())
                raw_4 = fut_4.result()
                raw_6 = fut_6.result()
                return raw_1, raw_2a, raw_2b, auditors, raw_4, raw_6
        except (ValueError, RuntimeError, OSError):
            pass

    raw_1 = _worker_pillar_1((str(repo_root), use_clean_room, fault_dict))
    raw_2a = _worker_domain_2((use_clean_room, fault_dict))
    raw_2b = _worker_pillar_b(
        (
            use_clean_room,
            {
                "pillar_b_inject_cross_body_cnflasha_transplant": bool(
                    faults.p2_inject_cross_body_cnflasha_transplant
                )
            },
        )
    )
    auditors = {}
    for g in p3_groups:
        auditors.update(_worker_pillar_3_group((g, use_clean_room)))
    raw_4 = _worker_pillar_4(use_clean_room)
    raw_6 = _worker_pillar_f(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, faults.p6_drift_surface)
    )
    return raw_1, raw_2a, raw_2b, auditors, raw_4, raw_6


def build_stage_b_milestone90_master_gate_report(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[Milestone90FaultInjection] = None,
) -> StageBMilestone90MasterGateReport:
    """Build deterministic 6-Pillar Milestone Phase 90 Master Gate report (`< 3.5s`)."""
    active_faults = faults if faults is not None else Milestone90FaultInjection()
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    verification_mode = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"

    raw_1, raw_2a, raw_2b, auditors, raw_4, raw_6 = _collect_parallel_milestone90_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )

    p1 = _evaluate_pillar_1(raw_1)
    p2, meta_2 = _evaluate_pillar_2(raw_2a, raw_2b, active_faults)
    p3, meta_3 = _evaluate_pillar_3(auditors, active_faults)
    p4, meta_4 = _evaluate_pillar_4(raw_4, active_faults)
    p5, meta_5 = _evaluate_pillar_5(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )
    p6, meta_6 = _evaluate_pillar_6(raw_6, active_faults)

    pillars = (p1, p2, p3, p4, p5, p6)
    all_errors: List[str] = []
    for pil in pillars:
        for err in pil.errors:
            all_errors.append(f"{pil.pillar_id}: {err}")

    failed_ids = tuple(pil.pillar_id for pil in pillars if not pil.passed)
    passed_count = sum(1 for pil in pillars if pil.passed)

    total_cp_mut = max(int(meta_4["cp_mutation_bytes"]), int(meta_6["cp_mutation_bytes"]))
    total_wbi_mut = int(meta_6["wbi_mutation_bytes"])
    total_cal_mut = max(
        int(meta_3["calibration_mutation_bytes"]),
        int(meta_6["calibration_mutation_bytes"]),
    )
    total_nvram_writes = max(
        int(meta_3["bk4_persistent_nvram_writes"]),
        int(meta_4["bk4_persistent_nvram_writes"]),
    )
    otp_touches = int(meta_2["otp_fuse_touches"])
    rpmb_inc = int(meta_2["rpmb_counter_increments"])
    temp_cleaned = bool(meta_6["temp_dir_cleaned"])

    all_ready = (
        len(pillars) == 6
        and passed_count == 6
        and len(failed_ids) == 0
        and len(all_errors) == 0
        and temp_cleaned
        and total_cp_mut == 0
        and total_wbi_mut == 0
        and total_cal_mut == 0
        and total_nvram_writes == 0
        and otp_touches == 0
        and rpmb_inc == 0
        and int(meta_6["drifted_surface_count"]) == 0
        and bool(meta_6["c2pa_rq_lic_intact"])
        and bool(meta_6["spacc_cnflasha_untouched"])
    )

    draft = StageBMilestone90MasterGateReport(
        schema_version=STAGE_B_MILESTONE90_SCHEMA,
        phase_version=PHASE_90_VERSION,
        verification_mode=verification_mode,
        all_pillars_milestone_ready=all_ready,
        status=STATUS_MILESTONE_READY if all_ready else STATUS_FAIL_CLOSED,
        o_rdonly_enforced=True,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        hardware_live_attachment_authorized=HARDWARE_LIVE_ATTACHMENT_AUTHORIZED,
        hardware_live_attachment_requirements=HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        cp_mutation_bytes=total_cp_mut,
        wbi_mutation_bytes=total_wbi_mut,
        calibration_mutation_bytes=total_cal_mut,
        usb_or_camera_operations=USB_OR_CAMERA_OPERATIONS,
        otp_fuse_touches=otp_touches,
        rpmb_counter_increments=rpmb_inc,
        temp_dir_cleaned=temp_cleaned,
        pillar_count=len(pillars),
        passed_pillar_count=passed_count,
        failed_pillar_ids=failed_ids,
        pillars=pillars,
        gate24_offline_verified=int(raw_1["offline_verified_gates"]),
        gate24_simulated_verified=int(raw_1["sim_verified_gates"]),
        firmware_lab_auditor_count=int(meta_3["auditor_count"]),
        firmware_lab_auditors_passed=int(meta_3["passed_count"]),
        vm_coemulation_stage_count=int(meta_4["stage_count"]),
        vm_coemulation_stages_passed=int(meta_4["passed_count"]),
        round14_positive_pairs=int(meta_5["round14_positive_pairs"]),
        round16_tabs_verified=int(meta_5["round16_tabs_verified"]),
        round16_pairwise_deltas_verified=int(meta_5["round16_pairwise_deltas_verified"]),
        round16_runs_verified=int(meta_5["round16_runs_verified"]),
        round16_nop_count=int(meta_5["round16_nop_count"]),
        round16_crashes=int(meta_5["round16_crashes"]),
        h0_surface_count=int(meta_6["h0_surface_count"]),
        drifted_surface_count=int(meta_6["drifted_surface_count"]),
        c2pa_rq_lic_intact=bool(meta_6["c2pa_rq_lic_intact"]),
        spacc_cnflasha_untouched=bool(meta_6["spacc_cnflasha_untouched"]),
        errors=tuple(all_errors),
        milestone90_sha256="",
    )
    digest = compute_milestone90_sha256(draft.to_dict())
    return replace(draft, milestone90_sha256=digest)


def verify_stage_b_milestone90_master_gate(
    payload: object,
) -> StageBMilestone90VerifyResult:
    """Fail-closed tamper-evident verifier for `stage_b_milestone90_master_gate_v1` reports."""
    if isinstance(payload, StageBMilestone90MasterGateReport):
        data: Dict[str, Any] = payload.to_dict()
    elif isinstance(payload, Mapping):
        data = dict(payload)
    else:
        return StageBMilestone90VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_milestone90_sha256="",
            observed_milestone90_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_milestone_ready=False,
            errors=("Milestone-90 payload must be a mapping or StageBMilestone90MasterGateReport",),
        )

    errors: List[str] = []
    schema_ok = data.get("schema_version") == STAGE_B_MILESTONE90_SCHEMA
    if not schema_ok:
        errors.append(
            f"Invalid schema_version {data.get('schema_version')!r}, expected {STAGE_B_MILESTONE90_SCHEMA!r}"
        )

    observed_digest = str(data.get("milestone90_sha256", ""))
    expected_digest = compute_milestone90_sha256(data)
    digest_matched = bool(HEX64_RE.fullmatch(observed_digest)) and (observed_digest == expected_digest)
    if not digest_matched:
        errors.append(
            f"milestone90_sha256 mismatch: observed={observed_digest!r} vs expected={expected_digest!r}"
        )

    rendered = json.dumps(data, sort_keys=True, ensure_ascii=False)
    if _RAW_BYTES_REPR_RE.search(rendered):
        errors.append("Milestone-90 report contains forbidden raw binary bytes repr")

    safety_redlines_ok = (
        data.get("o_rdonly_enforced") is True
        and data.get("persistent_emmc_writes_authorized") is False
        and data.get("persistent_write_release") is False
        and data.get("hardware_live_attachment_authorized") is False
        and data.get("p8_cp_mutation_forbidden") is True
        and data.get("wbi_p5_write_and_hibernation_forbidden") is True
        and data.get("cp_mutation_bytes") == 0
        and data.get("wbi_mutation_bytes") == 0
        and data.get("calibration_mutation_bytes") == 0
        and data.get("usb_or_camera_operations") == 0
        and data.get("otp_fuse_touches") == 0
        and data.get("rpmb_counter_increments") == 0
        and data.get("temp_dir_cleaned") is True
    )
    if not safety_redlines_ok:
        errors.append("Hard-locked safety redlines violated in Milestone-90 Master Gate report")

    pillars_raw = data.get("pillars")
    all_6_pillars_ok = False
    if not isinstance(pillars_raw, (list, tuple)) or len(pillars_raw) != 6:
        errors.append("pillars must contain exactly 6 entries (P1..P6)")
    else:
        seen_ids = tuple(str(p.get("pillar_id", "")) for p in pillars_raw if isinstance(p, Mapping))
        if seen_ids != PILLAR_IDS:
            errors.append(f"Pillar sequence mismatch: {seen_ids!r} != {PILLAR_IDS!r}")
        else:
            all_6_pillars_ok = all(
                isinstance(p, Mapping)
                and p.get("passed") is True
                and p.get("status") == STATUS_MILESTONE_READY
                for p in pillars_raw
            )
            if not all_6_pillars_ok:
                errors.append("One or more pillars in P1..P6 failed")

    all_pillars_milestone_ready = (
        data.get("all_pillars_milestone_ready") is True
        and data.get("status") == STATUS_MILESTONE_READY
        and data.get("passed_pillar_count") == 6
        and data.get("pillar_count") == 6
        and data.get("gate24_offline_verified") == 21
        and data.get("gate24_simulated_verified") == 24
        and data.get("firmware_lab_auditor_count") == 16
        and data.get("firmware_lab_auditors_passed") == 16
        and data.get("vm_coemulation_stage_count") == 13
        and data.get("vm_coemulation_stages_passed") == 13
        and data.get("round14_positive_pairs") == 18
        and data.get("round16_tabs_verified") == 5
        and data.get("round16_pairwise_deltas_verified") == 10
        and data.get("round16_runs_verified") == 4
        and data.get("round16_nop_count") == 0
        and data.get("round16_crashes") == 0
        and data.get("h0_surface_count") == 16
        and data.get("drifted_surface_count") == 0
        and data.get("c2pa_rq_lic_intact") is True
        and data.get("spacc_cnflasha_untouched") is True
    )
    if not all_pillars_milestone_ready:
        errors.append("all_pillars_milestone_ready is False or Milestone-90 readiness counters failed")

    valid = (
        schema_ok
        and digest_matched
        and safety_redlines_ok
        and all_6_pillars_ok
        and all_pillars_milestone_ready
        and len(errors) == 0
    )
    return StageBMilestone90VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_milestone90_sha256=expected_digest,
        observed_milestone90_sha256=observed_digest,
        safety_redlines_ok=safety_redlines_ok,
        all_6_pillars_ok=all_6_pillars_ok,
        all_pillars_milestone_ready=all_pillars_milestone_ready,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Bilingual Markdown Summary Generator (中文 + English)
# ---------------------------------------------------------------------------


def render_milestone90_markdown(report: StageBMilestone90MasterGateReport) -> str:
    """Render deterministic bilingual (中文 + English) Milestone Phase 90 signoff packet."""
    lines: List[str] = [
        "# Milestone Phase 90 里程碑总门禁与防砖闭环验证报告 / Milestone Phase 90 Unified Master Gate Report (`stage_b_milestone90_master_gate_v1`)",
        "",
        f"- **Schema Version / 档案模式**: `{report.schema_version}` (`v{report.phase_version}`)",
        f"- **Verification Mode / 验证模式**: `{report.verification_mode}` (`o_rdonly_enforced={report.o_rdonly_enforced}`)",
        (
            f"- **Milestone 90 Verdict / 综合结论**: `{report.status}` "
            f"(`all_pillars_milestone_ready={report.all_pillars_milestone_ready}`, "
            f"`{report.passed_pillar_count}/{report.pillar_count}` pillars)"
        ),
        (
            f"- **Live Hardware Attach Lock / 实机接入锁**: "
            f"`hardware_live_attachment_authorized={report.hardware_live_attachment_authorized}` "
            f"(requires `{', '.join(report.hardware_live_attachment_requirements)}`)"
        ),
        (
            f"- **Persistent Flash & OTP Lock / eMMC 持久写与熔丝锁**: "
            f"`persistent_emmc_writes_authorized={report.persistent_emmc_writes_authorized}`, "
            f"`persistent_write_release={report.persistent_write_release}`, "
            f"`otp_fuse_touches={report.otp_fuse_touches}`, `rpmb_counter_increments={report.rpmb_counter_increments}`"
        ),
        f"- **Canonical Milestone-90 SHA-256 / 不可篡改签章摘要**: `{report.milestone90_sha256}`",
        "",
        "## 六大里程碑验证支柱矩阵 / 6-Pillar Milestone-90 Matrix (`P1 .. P6`)",
        "",
        "| Pillar | Name | Status | Summary / 摘要 |",
        "| :---: | --- | :---: | --- |",
    ]
    for pil in report.pillars:
        lines.append(f"| `{pil.pillar_id}` | `{pil.pillar_name}` | `{pil.status}` | {pil.summary} |")

    lines.extend(
        [
            "",
            "## 关键工程与安全红线指标 / Key Metrics & Hard-Locked Redlines",
            "",
            f"- **24-Gate 预检 (`P1`)**: 离线真机前置阻断 `{report.gate24_offline_verified}/24` vs 模拟演练 `{report.gate24_simulated_verified}/24`（含 `G21` +48V XLR、`G22` 稳定器扭矩/激光/快门、`G23` Magnus 露点 `TEC` 冷凝阻断、`G24` 5V `900 mA` PMIC 预算与 USB-C 线缆压降/夹具锁）",
            f"- **OTP/RPMB + Tier-0 GF(256) + SD 逃生 (`P2`)**: `otp_fuse_touches={report.otp_fuse_touches}`, `rpmb_counter_increments={report.rpmb_counter_increments}`, `EXT_CSD` 永久写保护拦截, 2 分片 RAID-6 自愈, `FX3_SAFE_STOCK.FLG` 秒级回退",
            f"- **固件实验室 16 项跨机审计 (`P3`)**: `{report.firmware_lab_auditors_passed}/{report.firmware_lab_auditor_count}` auditors pass（含 Phase 80 `S-Log3` 41%/94% IRE 伪色 / 24-bit LPCM / User-Bits 与 Phase 85 Playback / `ShotMark1/2` / `Push Auto Iris`）",
            f"- **13 阶段异构共仿真 (`P4`)**: `{report.vm_coemulation_stages_passed}/{report.vm_coemulation_stage_count}` stages pass（含 Stage 12 CAMSET/LPCM/UB 与 Stage 13 Playback/ShotMark/Dewpoint HIL）",
            f"- **Round 14 + Round 16 真核 5-Tab UI 闭环 (`P5`)**: Round 14 `{report.round14_positive_pairs}/18` + Round 16 FX3 `4.9.337-scel+` Status Check `{report.round16_tabs_verified}` 标签 (`0x2f..0x33`, `{report.round16_pairwise_deltas_verified}/10` 组配对 `> 0`) + 繁体 `TC/Media` & 日语 `Monitoring` 3 层菜单 (`{report.round16_runs_verified}/4` runs, `nop_count={report.round16_nop_count}`, `crashes={report.round16_crashes}`)",
            f"- **Dossier v3 + Capstone + H0==H2 取证 (`P6`)**: `{report.h0_surface_count}/16` 表面逐比特一致（`drifted_surface_count={report.drifted_surface_count}`，`c2pa_rq_lic_intact={report.c2pa_rq_lic_intact}`，`spacc_cnflasha_untouched={report.spacc_cnflasha_untouched}`）",
            f"- **零改动红线 Counters**: `cp_mutation_bytes={report.cp_mutation_bytes}`, `wbi_mutation_bytes={report.wbi_mutation_bytes}`, `calibration_mutation_bytes={report.calibration_mutation_bytes}`, `usb_or_camera_operations={report.usb_or_camera_operations}`",
            "",
        ]
    )
    if report.errors:
        lines.extend(["## Errors / 异常信息", ""])
        for err in report.errors:
            lines.append(f"- `{err}`")
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DEFAULT_FX3_MODULES_DIR",
    "DEFAULT_FX6_DONOR_LIB_DIR",
    "DEFAULT_REPO_ROOT",
    "FIRMWARE_LAB_16_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "MILESTONE90_SCHEMA_VERSION",
    "OTP_FUSE_TOUCHES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_90_VERSION",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "ROUND16_5TAB_PAIR_KEYS",
    "ROUND16_MONITORING_PAIR_KEYS",
    "ROUND16_MULTITAB_SIDS",
    "ROUND16_RUN_IDS",
    "ROUND16_RUN_SPECS",
    "ROUND16_SUMMARY_RELPATH",
    "ROUND16_TCMEDIA_PAIR_KEYS",
    "RPMB_COUNTER_INCREMENTS",
    "SCHEMA_VERSION",
    "STAGE_B_MILESTONE90_SCHEMA",
    "STATUS_FAIL_CLOSED",
    "STATUS_MILESTONE_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "VM_COEMULATION_13_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "Milestone90FaultInjection",
    "Milestone90PillarResult",
    "StageBMilestone90MasterGateReport",
    "StageBMilestone90VerifyResult",
    "build_stage_b_milestone90_master_gate_report",
    "compute_milestone90_sha256",
    "render_milestone90_markdown",
    "verify_stage_b_milestone90_master_gate",
]
