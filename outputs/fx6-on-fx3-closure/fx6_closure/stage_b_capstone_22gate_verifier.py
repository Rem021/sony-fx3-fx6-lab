"""Phase 83 — Stage-B Capstone 22-Gate + OTP/RPMB Anti-Rollback + 11-Stage VM + Multi-Tab UI Verifier (`stage_b_capstone_22gate_v1`).

Synthesizes all 7 Stage-B Capstone readiness & anti-brick domains (`D1 .. D7`) into a
single tamper-evident, fail-closed Capstone certificate executing in `< 3.5s` across both
`LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

- `D1` (`SAFETY_22GATE_MASTER_PREFLIGHT`):
  Runs Phase 77 `phantom48v_gimbal_and_22gate_guard.evaluate_22gate_preflight` (`G01..G22`),
  verifying `19/22` offline hardware-truth block (`overall_ready_for_hardware_attach=False`)
  vs `22/22` simulated dry-run (`dry_run_rehearsal_only=True`), `G21` (`XLR-H1 +48V`
  phantom-power transducer burnout & hot-plug discharge firewall), `G22` (gimbal/follow-focus
  E-Mount mount-shear, venue-laser CMOS, and shutter-blade park guard), plus `G19`/`G20`.
- `D2` (`OTP_RPMB_ANTIROLLBACK_AND_EXTCSD_FIREWALL`):
  Runs Phase 79 `firmware_updata_and_antirollback_guard` proving `otp_fuse_touches == 0`,
  `rpmb_counter_increments == 0`, `FX3 v7.02 + FX6 v6.01 == TIER_A_GOLD_VERIFIED`,
  boot-chain downgrade & cross-SKU brick firewalls, and `EXT_CSD` permanent write-protect
  (`B_PERM_WP_EN` / `US_PERM_WP_EN` / `mmc boot_wp enable_perm`) fuse trap blocking.
- `D3` (`TIER0_GF256_HEALER_AND_SD_SENTINEL_ESCAPE`):
  Verifies Phase 72 `GF(256)` P+Q 2-shard erasure / 1-shard silent bit-rot self-healing +
  3-loss quorum rejection + cross-body `cnflasha`/`C2PA` anti-transplant lock AND Phase 66
  SD-card `FX3_SAFE_STOCK.FLG` `<1s` stock escape + `CXD90057 WDT` + `p1 FAT12/FAT16`
  clean mirror.
- `D4` (`FOURTEEN_FIRMWARE_LAB_AUDITORS`):
  Verifies all `14/14` `fx3_firmware_lab` auditors through Phase 75
  (`assignable_zoom_ciz_and_fn_auditor`: Assignable Buttons, T/W Zoom & CIZ, Anamorphic
  Touch-AF, Big6/Fn CAMSET volatile shadow with `bk4_persistent_nvram_writes == 0`, plus
  Phase 65 WB `3x3` white-point `calibration_mutation_bytes == 0` and Phase 70 Dual-Slot
  Proxy / `NRTM v2.20`).
- `D5` (`ELEVEN_STAGE_VM_COEMULATION`):
  Verifies all `11/11` `outputs/fx3-vm` heterogeneous co-emulation stages (`Stages 1..11`,
  including Stage 11 `stage11_phase78_touchaf_ciz_assignable`, Stage 9 `SMPTE 12M EXT-LK` +
  `PZ/IBIS`, Stage 10 `256 MiB` Dual-Slot `Relay` + `.RSV` salvage, `cp_mutation_bytes == 0`).
- `D6` (`ROUND15_MULTITAB_REAL_KERNEL_CLOSURE`):
  Verifies Round 14 (`18/18` 4-language x 3-surface pixel-delta matrix) AND Round 15
  (`reports/2026-11-14-round15-fx6-on-fx3-multitab-status-monitoring/summary.json` opened
  strictly `os.O_RDONLY` or deterministic clean-room fallback) proving `Status Check`
  (`0x2f`/`0x30`/`0x31`) multi-tab stepping + 3-layer `Monitoring` (`0x11`) CJK menu on real
  unmodified FX3 `7.02` kernel (`4.9.337-scel+`, `nop_count == 0`, `crashes == 0`,
  `13/13` Stage-B SHA-256).
- `D7` (`DOSSIER_V3_AND_H0_VS_H2_FORENSIC_IMMUTABILITY`):
  Verifies Dossier v3 (`stage_b_release_dossier_v3`) contracts and `H0 == H2` across all
  `16/16` persistent surfaces (`drifted_surface_count == 0`, `c2pa_rq_lic_intact == True`,
  `spacc_cnflasha_untouched == True`, `10/10` anomaly scenarios).

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

from fx3_firmware_lab.assignable_zoom_ciz_and_fn_auditor import (  # noqa: E402
    analyze_assignable_zoom_ciz_and_fn,
    assignable_zoom_ciz_and_fn_report_to_dict,
    build_and_verify_big6_fn_volatile_shadow,
)
from fx3_recovery.firmware_updata_and_antirollback_guard import (  # noqa: E402
    ANTIROLLBACK_GUARD_SCHEMA,
    BLOCKED_ANTIROLLBACK_EPOCH_DOWNGRADE,
    BLOCKED_CROSS_SKU_BOOTCHAIN_BRICK,
    BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP,
    EXT_CSD_B_PERM_WP_EN,
    FX3_SKU_CODE,
    FX6_SKU_CODE,
    TIER_A_GOLD_VERIFIED,
    ZERO_USERSPACE_RAM_ONLY,
    audit_ext_csd_write_protect,
    audit_mmc_wp_command_or_write,
    build_synthetic_ext_csd_with_wp,
    classify_byof_version_pair,
    evaluate_bootchain_transition,
    run_antirollback_and_byof_guard_suite,
)
from fx3_safety.phantom48v_gimbal_and_22gate_guard import (  # noqa: E402
    evaluate_22gate_preflight,
)
from fx3_vm_coemulation_suite import (  # noqa: E402
    CoEmulationConfig,
    run_fx3_vm_coemulation_suite,
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
from .stage_b_post_trial_auditor import (  # noqa: E402
    _read_file_o_rdonly,
)
from .stage_b_ram_overlay_packager import (  # noqa: E402
    STAGE_B_BK_LANG_SPECS,
    STAGE_B_LOCK_TABLE_13_ARTIFACTS,
    STAGE_B_SUPPORTED_LANGS,
)
from .stage_b_rehearsal_orchestrator import (  # noqa: E402
    HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
    REHEARSAL_STAGE_IDS,
    STAGE_B_REHEARSAL_SCHEMA,
)
from .stage_b_release_dossier_v3 import (  # noqa: E402
    DOSSIER_V3_SCHEMA_VERSION,
    FIRMWARE_LAB_13_AUDITOR_KEYS,
    PILLAR_IDS,
    ROUND14_4LANG_PAIRS,
    ROUND14_RUN_IDS,
    ROUND14_SUMMARY_RELPATH,
    STAGE_B_RELEASE_DOSSIER_V3_SCHEMA,
    VM_COEMULATION_10_STAGE_KEYS,
    StageBReleaseDossierV3FaultInjection,
    _evaluate_pillar_b,
    _evaluate_pillar_c,
    _evaluate_pillar_e,
    _evaluate_pillar_f,
    _worker_c_auditor_group,
    _worker_pillar_b,
    _worker_pillar_f,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

STAGE_B_CAPSTONE_22GATE_SCHEMA: str = "stage_b_capstone_22gate_v1"
CAPSTONE_22GATE_SCHEMA_VERSION: str = STAGE_B_CAPSTONE_22GATE_SCHEMA
SCHEMA_VERSION: str = STAGE_B_CAPSTONE_22GATE_SCHEMA
PHASE_83_VERSION: str = "83.0.0"

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

STATUS_SIMULATION_READY: str = "SIMULATION_READY"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

DOMAIN_SPECS: Tuple[Tuple[str, str], ...] = (
    ("D1", "SAFETY_22GATE_MASTER_PREFLIGHT"),
    ("D2", "OTP_RPMB_ANTIROLLBACK_AND_EXTCSD_FIREWALL"),
    ("D3", "TIER0_GF256_HEALER_AND_SD_SENTINEL_ESCAPE"),
    ("D4", "FOURTEEN_FIRMWARE_LAB_AUDITORS"),
    ("D5", "ELEVEN_STAGE_VM_COEMULATION"),
    ("D6", "ROUND15_MULTITAB_REAL_KERNEL_CLOSURE"),
    ("D7", "DOSSIER_V3_AND_H0_VS_H2_FORENSIC_IMMUTABILITY"),
)
DOMAIN_IDS: Tuple[str, ...] = tuple(did for did, _ in DOMAIN_SPECS)

FIRMWARE_LAB_14_AUDITOR_KEYS: Tuple[str, ...] = (
    *FIRMWARE_LAB_13_AUDITOR_KEYS,
    "assignable_zoom_ciz_and_fn_audit",
)

VM_COEMULATION_11_STAGE_KEYS: Tuple[str, ...] = (
    *VM_COEMULATION_10_STAGE_KEYS,
    "stage11_phase78_touchaf_ciz_assignable",
)

ROUND15_SUMMARY_RELPATH: str = (
    "reports/2026-11-14-round15-fx6-on-fx3-multitab-status-monitoring/summary.json"
)
ROUND15_RUN_SPECS: Tuple[Tuple[str, str, str], ...] = (
    ("r15a_status_tab2_schinese", "0x30", "schinese"),
    ("r15b_status_tab3_schinese", "0x31", "schinese"),
    ("r15c_menu_3layer_monitoring_schinese", "0x11", "schinese"),
    ("r15d_status_tab2_japanese", "0x30", "japanese"),
)
ROUND15_RUN_IDS: Tuple[str, ...] = tuple(rid for rid, _, _ in ROUND15_RUN_SPECS)
ROUND15_MULTITAB_SIDS: Tuple[str, ...] = ("0x2f", "0x30", "0x31")
ROUND15_STEPPING_PAIR_KEYS: Tuple[str, ...] = (
    "tab1_vs_tab2",
    "tab2_vs_tab3",
    "tab1_vs_tab3",
)
ROUND15_CATEGORY_PAIR_KEYS: Tuple[str, ...] = (
    "monitoring_vs_shooting_r11d",
    "monitoring_vs_paintlook_r13c",
)

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageBCapstone22GateFaultInjection:
    """Deterministic fault-injection knobs across Domains D1..D7 for fail-closed testing."""

    # D1 faults (22-gate preflight, G21 XLR-H1 +48V, G22 gimbal/follow-focus/laser/shutter)
    d1_xlr_kwargs: Optional[Mapping[str, Any]] = None
    d1_gimbal_kwargs: Optional[Mapping[str, Any]] = None
    d1_rig_kwargs: Optional[Mapping[str, Any]] = None
    d1_emount_kwargs: Optional[Mapping[str, Any]] = None
    d1_power_failover_kwargs: Optional[Mapping[str, Any]] = None
    d1_request_persistent_writes: bool = False

    # D2 faults (OTP/RPMB downgrade, cross-SKU brick, EXT_CSD permanent WP fuse trap)
    d2_otp_downgrade_version: Optional[str] = None
    d2_inject_cross_sku_target: Optional[str] = None
    d2_inject_ext_csd_perm_wp: bool = False
    d2_otp_fuse_touches_override: int = 0
    d2_rpmb_increments_override: int = 0

    # D3 faults (Tier-0 GF(256) P+Q, cross-body cnflasha transplant, init2/WDT/FAT)
    d3_inject_cross_body_cnflasha_transplant: bool = False
    d3_inject_gf256_quorum_loss: bool = False
    d3_inject_init2_escape_fault: bool = False

    # D4 faults (14 fx3_firmware_lab auditors, Phase 65 WB/matrix, Phase 70 NRTM, Phase 75 Big6/CIZ)
    d4_calibration_mutation_bytes: int = 0
    d4_bk4_persistent_nvram_writes: int = 0
    d4_corrupt_wb_whitepoint: bool = False
    d4_corrupt_nrtm_sidecar: bool = False
    d4_inject_legacy_sq_big6_block: bool = False
    d4_inject_persistent_nvram_shadow_path: bool = False

    # D5 faults (11-stage VM co-emulation, Stage 10 Relay drop, Stage 11 TouchAF/CIZ/Assignable)
    d5_cp_mutation_bytes: int = 0
    d5_stage10_dropped_frames: int = 0
    d5_stage11_nop_count: int = 0
    d5_stage11_null_gpio_derefs: int = 0

    # D6 faults (Round 14 + Round 15 multi-tab Status Check & 3-layer Monitoring)
    d6_round14_nop_count: int = 0
    d6_round14_zero_pair: bool = False
    d6_round15_nop_count: int = 0
    d6_round15_crashes: int = 0
    d6_round15_zero_tab_pair: Optional[str] = None
    d6_round15_zero_category_pair: Optional[str] = None
    d6_round15_manifest_count_override: Optional[int] = None

    # D7 faults (Dossier v3 + H0-vs-H2 16-surface drift / tamper negative control)
    d7_drift_surface: Optional[str] = None
    d7_tamper_negative_control: bool = False


@dataclass(frozen=True)
class CapstoneDomainResult:
    domain_id: str
    domain_name: str
    passed: bool
    status: str
    summary: str
    evidence: Dict[str, Any]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageBCapstone22GateReport:
    schema_version: str
    phase_version: str
    verification_mode: str
    all_domains_capstone_ready: bool
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
    domain_count: int
    passed_domain_count: int
    failed_domain_ids: Tuple[str, ...]
    domains: Tuple[CapstoneDomainResult, ...]
    gate22_offline_verified: int
    gate22_simulated_verified: int
    firmware_lab_auditor_count: int
    firmware_lab_auditors_passed: int
    vm_coemulation_stage_count: int
    vm_coemulation_stages_passed: int
    round14_positive_pairs: int
    round15_tabs_verified: int
    round15_runs_verified: int
    round15_nop_count: int
    round15_crashes: int
    h0_surface_count: int
    drifted_surface_count: int
    c2pa_rq_lic_intact: bool
    spacc_cnflasha_untouched: bool
    errors: Tuple[str, ...]
    capstone_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class StageBCapstone22GateVerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_capstone_sha256: str
    observed_capstone_sha256: str
    safety_redlines_ok: bool
    all_7_domains_ok: bool
    all_domains_capstone_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Helpers & O_RDONLY Loaders
# ---------------------------------------------------------------------------


def compute_capstone_22gate_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `StageBCapstone22GateReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("capstone_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _build_clean_room_stage_b_manifest_items() -> List[Dict[str, str]]:
    manifest_items: List[Dict[str, str]] = []
    for key, rel_guest_path in STAGE_B_LOCK_TABLE_13_ARTIFACTS:
        if key == "P1_P4_P8_P10_appFw":
            guest_path = "/usr/lib/appFw.so"
            sha = FX6_APPFW_STAGE_B_SHA256
        elif key == "P12_libWlanResource":
            guest_path = "/usr/lib/libWlanResource.so"
            sha = FX6_WLAN_RSRC_P12_SHA256
        elif rel_guest_path.startswith("lib/"):
            guest_path = f"/usr/{rel_guest_path}"
            sha = hashlib.sha256(f"clean-room-{key}-{guest_path}".encode("utf-8")).hexdigest()
        elif rel_guest_path.startswith("modules/"):
            guest_path = f"/usr/kmod/{rel_guest_path.split('/', 1)[1]}"
            sha = hashlib.sha256(f"clean-room-{key}-{guest_path}".encode("utf-8")).hexdigest()
        else:
            guest_path = f"/{rel_guest_path}"
            sha = hashlib.sha256(f"clean-room-{key}-{guest_path}".encode("utf-8")).hexdigest()
        manifest_items.append({"guest_path": guest_path, "sha256": sha})
    return manifest_items


def _load_round15_summary(
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load Round 15 summary strictly via `os.O_RDONLY` when present, else clean-room synthetic."""
    summary_path = repo_root / ROUND15_SUMMARY_RELPATH
    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"
    if not use_clean_room:
        raise FileNotFoundError(f"Missing Round 15 summary report: {summary_path}")

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
    for run_id, target_sid, lang_name in ROUND15_RUN_SPECS:
        runs_block[run_id] = {
            "run_id": run_id.replace("_", "-"),
            "round": 15,
            "lang": lang_name,
            "target_sid": target_sid,
            "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
            "nop_count": 0,
            "crashes": 0,
            "faithful_invariants": dict(faithful),
            "stage_b": {
                "stage": "B",
                "r15_enabled": True,
                "lang": lang_name,
                "manifest_count": 13,
                "manifest_items": list(manifest_items),
            },
        }

    synthetic = {
        "schema": "fx6-on-fx3-round15-multitab-status-monitoring-v1",
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
            ],
        },
        "runs": runs_block,
        "r15_multitab_and_category_audit": {
            "status_check_multitab_stepping_schinese": {
                "tab1_vs_tab2": {"sid_a": "0x2f", "sid_b": "0x30", "diff_pixels": 69094, "strictly_positive": True},
                "tab2_vs_tab3": {"sid_a": "0x30", "sid_b": "0x31", "diff_pixels": 125103, "strictly_positive": True},
                "tab1_vs_tab3": {"sid_a": "0x2f", "sid_b": "0x31", "diff_pixels": 130085, "strictly_positive": True},
                "all_3_tab_pairs_strictly_positive": True,
            },
            "menu_3layer_category_navigation_schinese": {
                "monitoring_vs_shooting_r11d": {"diff_pixels": 124819, "strictly_positive": True},
                "monitoring_vs_paintlook_r13c": {"diff_pixels": 31140, "strictly_positive": True},
                "all_category_deltas_strictly_positive": True,
            },
            "cjk_cross_engine_tab2_audit": {
                "japanese_tab1_vs_tab2": {"sid_a": "0x2f", "sid_b": "0x30", "diff_pixels": 62815, "strictly_positive": True},
                "schinese_tab2_vs_japanese_tab2": {"sid_a": "0x30", "sid_b": "0x30", "diff_pixels": 33462, "strictly_positive": True},
            },
        },
    }
    return synthetic, "CLEAN_ROOM_SYNTHETIC"


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 3.5s Runtime)
# ---------------------------------------------------------------------------


def _worker_domain_1(args: Tuple[str, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, fault_dict = args
    repo_root = Path(repo_root_str)
    xlr_kwargs = fault_dict.get("d1_xlr_kwargs")
    gimbal_kwargs = fault_dict.get("d1_gimbal_kwargs")
    rig_kwargs = fault_dict.get("d1_rig_kwargs")
    emount_kwargs = fault_dict.get("d1_emount_kwargs")
    power_kwargs = fault_dict.get("d1_power_failover_kwargs")
    req_persist = bool(fault_dict.get("d1_request_persistent_writes", False))

    rep_off = evaluate_22gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=False,
        xlr_kwargs=xlr_kwargs,
        gimbal_kwargs=gimbal_kwargs,
        rig_kwargs=rig_kwargs,
        emount_kwargs=emount_kwargs,
        power_failover_kwargs=power_kwargs,
        request_persistent_emmc_writes=req_persist,
    )
    rep_sim = evaluate_22gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=True,
        xlr_kwargs=xlr_kwargs,
        gimbal_kwargs=gimbal_kwargs,
        rig_kwargs=rig_kwargs,
        emount_kwargs=emount_kwargs,
        power_failover_kwargs=power_kwargs,
        request_persistent_emmc_writes=req_persist,
    )
    m20 = rep_sim.master_20_report
    g19 = m20.get("g19_result", {})
    g20 = m20.get("g20_result", {})
    emount = g19.get("emount_lensrail", {})
    pf = g20.get("power_failover_ups", {})
    rsv = pf.get("rsv_salvage", {})

    g21 = rep_sim.g21_result
    g22 = rep_sim.g22_result
    xlr_fw = g21.get("xlr_phantom_firewall", {})
    gimbal_fw = g22.get("gimbal_focus_laser_shutter", {})
    ibis_hex = str(emount.get("ibis_park_opcode_hex", "0x0000"))
    ibis_opcode = int(ibis_hex, 16) if ibis_hex.startswith("0x") else 0

    return {
        "schema": rep_sim.schema,
        "verification_mode": rep_sim.verification_mode,
        "offline_verified_gates": int(rep_off.summary.get("verified_gates", 0)),
        "offline_19_gates_verified": bool(rep_off.offline_19_gates_verified),
        "offline_all_22_gates_verified": bool(rep_off.all_22_gates_verified),
        "offline_ready_for_hw": bool(rep_off.overall_ready_for_hardware_attach),
        "sim_verified_gates": int(rep_sim.summary.get("verified_gates", 0)),
        "sim_all_22_gates_verified": bool(rep_sim.all_22_gates_verified),
        "sim_dry_run_rehearsal_only": bool(rep_sim.dry_run_rehearsal_only),
        "sim_ready_for_hw": bool(rep_sim.overall_ready_for_hardware_attach),
        "g13_to_g22_all_passed": bool(rep_sim.g13_to_g22_all_passed),
        "g21_to_g22_all_passed": bool(rep_sim.g21_to_g22_all_passed),
        "g21_passed": bool(g21.get("valid", False)),
        "g21_status": str(g21.get("status", "")),
        "g21_hot_plug_discharge_safe": bool(xlr_fw.get("hot_plug_discharge_safe", False)),
        "g21_channel_count": len(xlr_fw.get("channels", [])),
        "g22_passed": bool(g22.get("valid", False)),
        "g22_status": str(g22.get("status", "")),
        "g22_single_control_bus_arbitrated": bool(gimbal_fw.get("single_control_bus_arbitrated", False)),
        "g22_follow_focus_shear_safe": bool(gimbal_fw.get("follow_focus_shear_safe", False)),
        "g22_laser_cmos_safe": bool(gimbal_fw.get("laser_cmos_safe", False)),
        "g22_shutter_curtain_safe": bool(gimbal_fw.get("shutter_curtain_safe", False)),
        "g22_shutter_blade_parked_open": bool(gimbal_fw.get("shutter_blade_parked_open", False)),
        "g22_ibis_gimbal_drift_safe": bool(gimbal_fw.get("ibis_gimbal_drift_safe", False)),
        "g22_cp_mutation_bytes": int(gimbal_fw.get("cp_mutation_bytes", -1)),
        "g19_crowbar_ms": float(emount.get("v_lens_servo_crowbar_ms", 99.0)),
        "g19_ibis_park_opcode": ibis_opcode,
        "g20_lost_frames": int(pf.get("lost_frames_on_switchover", -1)),
        "g20_rsv_salvage_ok": bool(pf.get("rsv_salvage_verified", False) and rsv.get("valid", False)),
        "persistent_emmc_writes_authorized": bool(rep_sim.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep_sim.persistent_write_release),
        "sim_status": str(rep_sim.status),
        "sim_errors": list(rep_sim.errors),
        "g21_errors": list(g21.get("errors", [])),
        "g22_errors": list(g22.get("errors", [])),
    }


def _worker_domain_2(args: Tuple[bool, Dict[str, Any]]) -> Dict[str, Any]:
    use_clean_room, fault_dict = args
    rep = run_antirollback_and_byof_guard_suite(force_clean_room=use_clean_room)
    gold_pair = classify_byof_version_pair("v7.02", "v6.01")

    fault_errors: List[str] = []
    downgrade_ver = fault_dict.get("d2_otp_downgrade_version")
    if downgrade_ver:
        dec = evaluate_bootchain_transition(
            host_sku=FX3_SKU_CODE,
            host_version="v7.02",
            target_component="nbl_a",
            candidate_sku=FX3_SKU_CODE,
            candidate_version=str(downgrade_ver),
        )
        fault_errors.append(
            f"d2: OTP/RPMB downgrade fault {downgrade_ver} blocked ({dec.decision_code})"
        )

    cross_target = fault_dict.get("d2_inject_cross_sku_target")
    if cross_target:
        dec_x = evaluate_bootchain_transition(
            host_sku=FX3_SKU_CODE,
            host_version="v7.02",
            target_component=str(cross_target),
            candidate_sku=FX6_SKU_CODE,
            candidate_version="v6.01",
        )
        fault_errors.append(
            f"d2: cross-SKU target '{cross_target}' blocked ({dec_x.decision_code})"
        )

    if fault_dict.get("d2_inject_ext_csd_perm_wp"):
        wp_rep = audit_ext_csd_write_protect(
            build_synthetic_ext_csd_with_wp(boot_wp=EXT_CSD_B_PERM_WP_EN)
        )
        cmd_rep = audit_mmc_wp_command_or_write("mmc boot_wp enable_perm /dev/mmcblk0boot0")
        fault_errors.append(
            f"d2: EXT_CSD permanent write-protect fuse trap blocked ({wp_rep.status}/{cmd_rep.status})"
        )

    return {
        "schema": rep.schema,
        "verification_mode": rep.verification_mode,
        "all_passed": bool(rep.all_passed),
        "status": str(rep.status),
        "otp_fuse_touches": int(rep.otp_fuse_touches),
        "rpmb_counter_increments": int(rep.rpmb_counter_increments),
        "antirollback_brick_risk": str(rep.antirollback_brick_risk),
        "physical_device_writes": int(rep.physical_device_writes),
        "persistent_emmc_writes_authorized": bool(rep.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep.persistent_write_release),
        "allow_boot_partition_targeting": bool(rep.allow_boot_partition_targeting),
        "allow_destructive_fastboot": bool(rep.allow_destructive_fastboot),
        "gold_pair_tier": str(gold_pair.tier),
        "gold_pair_compatible": bool(gold_pair.compatible),
        "fx3_wbi2_sections": int(rep.donor_snapshot.fx3_wbi2_sections),
        "fx6_wbi2_sections": int(rep.donor_snapshot.fx6_wbi2_sections),
        "downgrade_v205_blocked_code": str(rep.downgrade_v205_blocked.decision_code),
        "downgrade_v600_blocked_code": str(rep.downgrade_v600_blocked.decision_code),
        "cross_sku_fx6_nbl_blocked_code": str(rep.cross_sku_fx6_nbl_blocked.decision_code),
        "cross_sku_fx6_wbi2_blocked_code": str(rep.cross_sku_fx6_wbi2_blocked.decision_code),
        "ext_csd_clean_safe": bool(rep.ext_csd_clean_report.safe),
        "ext_csd_boot_perm_wp_status": str(rep.ext_csd_boot_perm_wp_blocked.status),
        "ext_csd_user_perm_wp_status": str(rep.ext_csd_user_perm_wp_blocked.status),
        "mmc_perm_wp_cmd_status": str(rep.mmc_perm_wp_cmd_blocked.status),
        "errors": list(rep.errors) + fault_errors,
    }


def _worker_domain_4_group(args: Tuple[str, bool]) -> Dict[str, Dict[str, Any]]:
    group, clean_room = args
    if group == "assignable":
        return {
            "assignable_zoom_ciz_and_fn_audit": assignable_zoom_ciz_and_fn_report_to_dict(
                analyze_assignable_zoom_ciz_and_fn(clean_room=clean_room)
            )
        }
    return _worker_c_auditor_group((group, clean_room))


def _worker_domain_5(use_clean_room: bool) -> Dict[str, Any]:
    return run_fx3_vm_coemulation_suite(CoEmulationConfig(force_clean_room=use_clean_room))


# ---------------------------------------------------------------------------
# Domain Evaluators (D1 .. D7)
# ---------------------------------------------------------------------------


def _evaluate_domain_1(raw_1: Mapping[str, Any]) -> CapstoneDomainResult:
    errors: List[str] = []
    if not raw_1["offline_19_gates_verified"] or raw_1["offline_verified_gates"] != 19:
        errors.append(
            f"d1: offline hardware-truth gates expected 19/22, got {raw_1['offline_verified_gates']}/22"
        )
    if raw_1["offline_all_22_gates_verified"] or raw_1["offline_ready_for_hw"]:
        errors.append("d1: offline mode must remain blocked for live hardware attach")
    if not raw_1["sim_all_22_gates_verified"] or raw_1["sim_verified_gates"] != 22:
        errors.append(
            f"d1: simulated rehearsal gates expected 22/22, got {raw_1['sim_verified_gates']}/22"
        )
    if not raw_1["sim_dry_run_rehearsal_only"] or raw_1["sim_ready_for_hw"]:
        errors.append("d1: simulated 22/22 rehearsal must keep overall_ready_for_hardware_attach=False")
    if not raw_1["g13_to_g22_all_passed"] or not raw_1["g21_to_g22_all_passed"]:
        errors.append("d1: G13..G22 or G21..G22 guard gate blocked")
    if not raw_1["g21_passed"] or not raw_1["g21_hot_plug_discharge_safe"] or raw_1["g21_channel_count"] != 3:
        errors.append(f"d1: G21 XLR-H1 +48V firewall failed ({raw_1['g21_status']})")
    if (
        not raw_1["g22_passed"]
        or not raw_1["g22_single_control_bus_arbitrated"]
        or not raw_1["g22_follow_focus_shear_safe"]
        or not raw_1["g22_laser_cmos_safe"]
        or not raw_1["g22_shutter_curtain_safe"]
        or not raw_1["g22_shutter_blade_parked_open"]
        or not raw_1["g22_ibis_gimbal_drift_safe"]
        or raw_1["g22_cp_mutation_bytes"] != 0
    ):
        errors.append(f"d1: G22 gimbal/follow-focus/laser/shutter guard failed ({raw_1['g22_status']})")
    if raw_1["g19_crowbar_ms"] >= 2.0 or raw_1["g19_ibis_park_opcode"] != 0x0400:
        errors.append("d1: G19 E-Mount rail crowbar or 0x0400 IBIS park check failed")
    if raw_1["g20_lost_frames"] != 0 or not raw_1["g20_rsv_salvage_ok"]:
        errors.append("d1: G20 USB-PD->NP-FZ100 UPS or .RSV salvage failed")
    if raw_1["persistent_emmc_writes_authorized"] or raw_1["persistent_write_release"]:
        errors.append("d1: hard-locked persistent_emmc_writes_authorized / persistent_write_release breached")
    for err in raw_1["sim_errors"]:
        errors.append(f"d1_22gate: {err}")
    for err in raw_1["g21_errors"]:
        errors.append(f"d1_g21: {err}")
    for err in raw_1["g22_errors"]:
        errors.append(f"d1_g22: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_1["schema"],
        "verification_mode": raw_1["verification_mode"],
        "offline_verified_gates": raw_1["offline_verified_gates"],
        "offline_ready_for_hardware_attach": raw_1["offline_ready_for_hw"],
        "simulated_verified_gates": raw_1["sim_verified_gates"],
        "simulated_ready_for_hardware_attach": raw_1["sim_ready_for_hw"],
        "g21_passed": raw_1["g21_passed"],
        "g21_status": raw_1["g21_status"],
        "g21_hot_plug_discharge_safe": raw_1["g21_hot_plug_discharge_safe"],
        "g21_channel_count": raw_1["g21_channel_count"],
        "g22_passed": raw_1["g22_passed"],
        "g22_status": raw_1["g22_status"],
        "g22_single_control_bus_arbitrated": raw_1["g22_single_control_bus_arbitrated"],
        "g22_follow_focus_shear_safe": raw_1["g22_follow_focus_shear_safe"],
        "g22_laser_cmos_safe": raw_1["g22_laser_cmos_safe"],
        "g22_shutter_curtain_safe": raw_1["g22_shutter_curtain_safe"],
        "g22_shutter_blade_parked_open": raw_1["g22_shutter_blade_parked_open"],
        "g22_ibis_gimbal_drift_safe": raw_1["g22_ibis_gimbal_drift_safe"],
        "g19_crowbar_ms": raw_1["g19_crowbar_ms"],
        "g19_ibis_park_opcode": f"0x{raw_1['g19_ibis_park_opcode']:04x}",
        "g20_lost_frames_on_switchover": raw_1["g20_lost_frames"],
        "g20_rsv_salvage_ok": raw_1["g20_rsv_salvage_ok"],
        "persistent_emmc_writes_authorized": raw_1["persistent_emmc_writes_authorized"],
        "persistent_write_release": raw_1["persistent_write_release"],
    }
    return CapstoneDomainResult(
        domain_id="D1",
        domain_name="SAFETY_22GATE_MASTER_PREFLIGHT",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"22-Gate offline={raw_1['offline_verified_gates']}/22 sim={raw_1['sim_verified_gates']}/22, "
            f"G21 XLR-H1 +48V={raw_1['g21_passed']}, G22 Gimbal/Laser/Shutter={raw_1['g22_passed']} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_domain_2(
    raw_2: Mapping[str, Any],
    faults: StageBCapstone22GateFaultInjection,
) -> Tuple[CapstoneDomainResult, Dict[str, Any]]:
    errors: List[str] = []
    if raw_2["schema"] != ANTIROLLBACK_GUARD_SCHEMA:
        errors.append(f"d2: unexpected antirollback schema {raw_2['schema']!r}")
    if not raw_2["all_passed"]:
        errors.append("d2: Phase 79 firmware_updata_and_antirollback_guard failed")

    otp_touches = int(raw_2["otp_fuse_touches"]) + int(faults.d2_otp_fuse_touches_override)
    rpmb_inc = int(raw_2["rpmb_counter_increments"]) + int(faults.d2_rpmb_increments_override)

    if otp_touches != 0:
        errors.append(f"d2: otp_fuse_touches={otp_touches} != 0")
    if rpmb_inc != 0:
        errors.append(f"d2: rpmb_counter_increments={rpmb_inc} != 0")
    if raw_2["antirollback_brick_risk"] != ZERO_USERSPACE_RAM_ONLY:
        errors.append(f"d2: unexpected antirollback_brick_risk {raw_2['antirollback_brick_risk']!r}")
    if raw_2["gold_pair_tier"] != TIER_A_GOLD_VERIFIED or not raw_2["gold_pair_compatible"]:
        errors.append(f"d2: FX3 v7.02 + FX6 v6.01 expected {TIER_A_GOLD_VERIFIED}, got {raw_2['gold_pair_tier']!r}")
    if (
        raw_2["downgrade_v205_blocked_code"] != BLOCKED_ANTIROLLBACK_EPOCH_DOWNGRADE
        or raw_2["downgrade_v600_blocked_code"] != BLOCKED_ANTIROLLBACK_EPOCH_DOWNGRADE
    ):
        errors.append("d2: monotonic OTP/RPMB downgrade firewall check failed")
    if (
        raw_2["cross_sku_fx6_nbl_blocked_code"] != BLOCKED_CROSS_SKU_BOOTCHAIN_BRICK
        or raw_2["cross_sku_fx6_wbi2_blocked_code"] != BLOCKED_CROSS_SKU_BOOTCHAIN_BRICK
    ):
        errors.append("d2: cross-SKU FX6->FX3 bootchain firewall check failed")
    if (
        not raw_2["ext_csd_clean_safe"]
        or raw_2["ext_csd_boot_perm_wp_status"] != BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP
        or raw_2["ext_csd_user_perm_wp_status"] != BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP
        or raw_2["mmc_perm_wp_cmd_status"] != BLOCKED_PERMANENT_EMMC_WP_FUSE_TRAP
    ):
        errors.append("d2: EXT_CSD permanent write-protect fuse trap firewall failed")
    if (
        raw_2["physical_device_writes"] != 0
        or raw_2["persistent_emmc_writes_authorized"]
        or raw_2["persistent_write_release"]
        or raw_2["allow_boot_partition_targeting"]
        or raw_2["allow_destructive_fastboot"]
    ):
        errors.append("d2: persistent eMMC write / boot-partition / fastboot lock breached")
    for err in raw_2["errors"]:
        errors.append(str(err))

    passed = len(errors) == 0
    evidence = {
        "schema": raw_2["schema"],
        "verification_mode": raw_2["verification_mode"],
        "otp_fuse_touches": otp_touches,
        "rpmb_counter_increments": rpmb_inc,
        "antirollback_brick_risk": raw_2["antirollback_brick_risk"],
        "gold_pair_tier": raw_2["gold_pair_tier"],
        "gold_pair_compatible": raw_2["gold_pair_compatible"],
        "fx3_wbi2_sections": raw_2["fx3_wbi2_sections"],
        "fx6_wbi2_sections": raw_2["fx6_wbi2_sections"],
        "downgrade_v205_blocked": raw_2["downgrade_v205_blocked_code"],
        "downgrade_v600_blocked": raw_2["downgrade_v600_blocked_code"],
        "cross_sku_fx6_nbl_blocked": raw_2["cross_sku_fx6_nbl_blocked_code"],
        "cross_sku_fx6_wbi2_blocked": raw_2["cross_sku_fx6_wbi2_blocked_code"],
        "ext_csd_clean_safe": raw_2["ext_csd_clean_safe"],
        "ext_csd_boot_perm_wp_blocked": raw_2["ext_csd_boot_perm_wp_status"],
        "ext_csd_user_perm_wp_blocked": raw_2["ext_csd_user_perm_wp_status"],
        "mmc_perm_wp_cmd_blocked": raw_2["mmc_perm_wp_cmd_status"],
        "physical_device_writes": raw_2["physical_device_writes"],
        "persistent_emmc_writes_authorized": raw_2["persistent_emmc_writes_authorized"],
        "persistent_write_release": raw_2["persistent_write_release"],
    }
    domain = CapstoneDomainResult(
        domain_id="D2",
        domain_name="OTP_RPMB_ANTIROLLBACK_AND_EXTCSD_FIREWALL",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"OTP={otp_touches}, RPMB={rpmb_inc}, FX3v7.02+FX6v6.01={raw_2['gold_pair_tier']}, "
            f"EXT_CSD perm-WP firewall=ACTIVE {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "otp_fuse_touches": otp_touches,
        "rpmb_counter_increments": rpmb_inc,
    }
    return domain, meta


def _evaluate_domain_3(
    raw_3: Mapping[str, Any],
    faults: StageBCapstone22GateFaultInjection,
) -> CapstoneDomainResult:
    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_b_inject_cross_body_cnflasha_transplant=faults.d3_inject_cross_body_cnflasha_transplant,
        pillar_b_inject_gf256_quorum_loss=faults.d3_inject_gf256_quorum_loss,
        pillar_b_inject_init2_escape_fault=faults.d3_inject_init2_escape_fault,
    )
    pb = _evaluate_pillar_b(raw_3, v3_faults)
    return CapstoneDomainResult(
        domain_id="D3",
        domain_name="TIER0_GF256_HEALER_AND_SD_SENTINEL_ESCAPE",
        passed=pb.passed,
        status=pb.status,
        summary=pb.summary,
        evidence=dict(pb.evidence),
        errors=tuple(e.replace("pillar_b", "d3") for e in pb.errors),
    )


def _evaluate_domain_4(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: StageBCapstone22GateFaultInjection,
) -> Tuple[CapstoneDomainResult, Dict[str, Any]]:
    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_c_calibration_mutation_bytes=faults.d4_calibration_mutation_bytes,
        pillar_c_corrupt_wb_whitepoint=faults.d4_corrupt_wb_whitepoint,
        pillar_c_corrupt_nrtm_sidecar=faults.d4_corrupt_nrtm_sidecar,
    )
    pc, meta_c = _evaluate_pillar_c(auditors, v3_faults)
    errors: List[str] = [e.replace("pillar_c", "d4") for e in pc.errors]

    a14 = auditors.get("assignable_zoom_ciz_and_fn_audit", {})
    a14_ok = isinstance(a14, Mapping) and bool(a14.get("all_checks_passed"))
    if not a14_ok:
        errors.append("d4: fx3_firmware_lab 14th auditor assignable_zoom_ciz_and_fn_audit failed")

    nvram_writes = int(a14.get("bk4_persistent_nvram_writes", -1)) + int(
        faults.d4_bk4_persistent_nvram_writes
    )
    null_gpio = int(a14.get("null_gpio_faults", -1))
    if nvram_writes != 0:
        errors.append(f"d4: bk4_persistent_nvram_writes={nvram_writes} != 0")
    if null_gpio != 0:
        errors.append(f"d4: null_gpio_faults={null_gpio} != 0")
    if a14.get("persistent_emmc_writes_authorized") is not False:
        errors.append("d4: assignable_zoom_ciz_and_fn_audit breached persistent_emmc_writes_authorized")
    if a14.get("icx1295_crashed") or a14.get("libcamera_crashed"):
        errors.append("d4: icx1295 or libcamera crash detected in Phase 75 auditor")

    p1_ok = bool(a14.get("pillar_1_assignable_catalog", {}).get("passed", False))
    p2_ok = bool(a14.get("pillar_2_zoom_ciz_matrix", {}).get("passed", False))
    p3_ok = bool(a14.get("pillar_3_touch_af_desqueeze", {}).get("passed", False))
    p4_ok = bool(a14.get("pillar_4_big6_fn_shadow", {}).get("passed", False))
    if not (p1_ok and p2_ok and p3_ok and p4_ok):
        errors.append("d4: one or more Phase 75 Assignable/CIZ/Touch-AF/Big6 pillars failed")

    if faults.d4_inject_legacy_sq_big6_block:
        leg_ev = build_and_verify_big6_fn_volatile_shadow(
            sq_mode_settings="LEGACY_SQ_MODE",
            home_lower_left_mode="APERTURE",
            shadow_path="/tmp/fx3_legacy_sq_fault.json",
        )
        errors.append(f"d4: Big6 S&Q gate blocked legacy mode ({leg_ev.status})")

    if faults.d4_inject_persistent_nvram_shadow_path:
        nv_ev = build_and_verify_big6_fn_volatile_shadow(
            sq_mode_settings="FIXED_VARIABLE",
            home_lower_left_mode="APERTURE",
            shadow_path="/dev/cnflasha1/bk4_overwrite.bin",
        )
        errors.append(f"d4: persistent NVRAM shadow write rejected ({nv_ev.status})")

    auditor_statuses = dict(pc.evidence["auditor_statuses"])
    auditor_statuses["assignable_zoom_ciz_and_fn_audit"] = a14_ok
    auditor_sha256s = dict(pc.evidence["auditor_sha256s"])
    a14_sha = a14.get("report_sha256") if isinstance(a14, Mapping) else None
    auditor_sha256s["assignable_zoom_ciz_and_fn_audit"] = str(a14_sha) if a14_sha else None

    passed_count = int(meta_c["passed_count"]) + (1 if a14_ok else 0)
    total_count = len(FIRMWARE_LAB_14_AUDITOR_KEYS)
    passed = len(errors) == 0 and passed_count == total_count

    evidence = dict(pc.evidence)
    evidence.update(
        {
            "auditor_count": total_count,
            "passed_auditor_count": passed_count,
            "auditor_statuses": auditor_statuses,
            "auditor_sha256s": auditor_sha256s,
            "phase75_assignable_catalog_ok": p1_ok,
            "phase75_zoom_ciz_matrix_ok": p2_ok,
            "phase75_touch_af_desqueeze_ok": p3_ok,
            "phase75_big6_fn_shadow_ok": p4_ok,
            "phase75_bk4_persistent_nvram_writes": nvram_writes,
            "phase75_null_gpio_faults": null_gpio,
        }
    )
    domain = CapstoneDomainResult(
        domain_id="D4",
        domain_name="FOURTEEN_FIRMWARE_LAB_AUDITORS",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {passed_count}/{total_count} auditors "
            f"(incl. Phase 75 Assignable/CIZ/Touch-AF/Big6), bk4_nvram_writes={nvram_writes}, "
            f"cal_mut={meta_c['calibration_mutation_bytes']}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "auditor_count": total_count,
        "passed_count": passed_count,
        "calibration_mutation_bytes": meta_c["calibration_mutation_bytes"],
        "bk4_persistent_nvram_writes": nvram_writes,
    }
    return domain, meta


def _evaluate_domain_5(
    vm_rep: Mapping[str, Any],
    faults: StageBCapstone22GateFaultInjection,
) -> Tuple[CapstoneDomainResult, Dict[str, Any]]:
    errors: List[str] = []
    if not vm_rep.get("all_checks_passed"):
        errors.append("d5: outputs/fx3-vm 11-stage co-emulation top-level all_checks_passed is False")

    stage_statuses: Dict[str, bool] = {}
    passed_stages = 0
    for skey in VM_COEMULATION_11_STAGE_KEYS:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if ok:
            passed_stages += 1
        else:
            errors.append(f"d5: VM co-emulation {skey} failed")

    redlines = vm_rep.get("redlines", {})
    cp_mut_bytes = int(redlines.get("cp_mutation_bytes", -1)) + int(faults.d5_cp_mutation_bytes)
    wbi_mut_bytes = int(redlines.get("wbi_mutation_bytes", -1))
    nvram_writes = int(redlines.get("nvram_persistent_writes", -1))
    phys_writes = int(redlines.get("physical_device_writes", -1))
    if not redlines.get("p8_cp_mutation_forbidden"):
        errors.append("d5: p8_cp_mutation_forbidden must be True")
    if cp_mut_bytes != 0:
        errors.append(f"d5: cp_mutation_bytes={cp_mut_bytes} != 0")
    if wbi_mut_bytes != 0 or nvram_writes != 0 or phys_writes != 0:
        errors.append("d5: VM co-emulation redline write counters non-zero")

    s9 = vm_rep.get("stage9_phase67_tc_lens_paint", {})
    s9_nop = int(s9.get("nop_count", -1))
    if s9_nop != 0:
        errors.append(f"d5: Stage 9 SMPTE 12M / PZ-IBIS nop_count={s9_nop} != 0")

    s10 = vm_rep.get("stage10_phase71_dualslot_ups_salvage", {})
    ds = s10.get("dualslot_proxy_pipeline", {})
    relay = ds.get("relay_auto_switch", {})
    fifo_mib = int(ds.get("dram_elastic_fifo_mib", 0))
    relay_dropped = int(relay.get("dropped_frames", -1)) + int(faults.d5_stage10_dropped_frames)
    relay_stalled = bool(relay.get("main_stalled", True))
    rsv_salvageable = int(s10.get("rsv_salvageable_frames", -1))
    rsv_committed = int(s10.get("rsv_committed_frames", -2))
    c2pa_untouched = bool(s10.get("c2pa_license_untouched", False))
    s10_nop = int(s10.get("nop_count", -1))
    if fifo_mib != 256:
        errors.append(f"d5: Stage 10 DRAM elastic FIFO expected 256 MiB, got {fifo_mib}")
    if relay_dropped != 0 or relay_stalled:
        errors.append(f"d5: Stage 10 Dual-Slot Relay failed 0-drop contract (dropped={relay_dropped})")
    if rsv_salvageable <= 0 or rsv_salvageable != rsv_committed:
        errors.append(f"d5: Stage 10 UPS .RSV salvage mismatch ({rsv_salvageable}/{rsv_committed})")
    if not c2pa_untouched or s10_nop != 0:
        errors.append("d5: Stage 10 C2PA license mutated or nop_count != 0")

    s11 = vm_rep.get("stage11_phase78_touchaf_ciz_assignable", {})
    s11_nop = int(s11.get("nop_count", -1)) + int(faults.d5_stage11_nop_count)
    s11_cp_mut = int(s11.get("cp_mutation_bytes", -1))
    s11_bk4_writes = int(s11.get("bk4_persistent_nvram_writes", -1))
    s11_null_gpio = int(s11.get("null_gpio_derefs", -1)) + int(faults.d5_stage11_null_gpio_derefs)
    s11_mailbox_stalls = int(s11.get("mailbox_stalls", -1))
    if s11_nop != 0:
        errors.append(f"d5: Stage 11 nop_count={s11_nop} != 0")
    if s11_cp_mut != 0 or s11_bk4_writes != 0:
        errors.append(f"d5: Stage 11 cp_mutation={s11_cp_mut} or bk4_writes={s11_bk4_writes} != 0")
    if s11_null_gpio != 0 or s11_mailbox_stalls != 0:
        errors.append(f"d5: Stage 11 null_gpio={s11_null_gpio} or mailbox_stalls={s11_mailbox_stalls} != 0")
    if s11.get("persistent_emmc_writes_authorized") is not False:
        errors.append("d5: Stage 11 persistent_emmc_writes_authorized must be False")

    total_stages = len(VM_COEMULATION_11_STAGE_KEYS)
    passed = len(errors) == 0 and passed_stages == total_stages
    evidence = {
        "vm_schema": vm_rep.get("schema"),
        "stage_count": total_stages,
        "passed_stage_count": passed_stages,
        "stage_statuses": stage_statuses,
        "audit_digest_sha256": vm_rep.get("audit_digest_sha256"),
        "cp_mutation_bytes": cp_mut_bytes,
        "wbi_mutation_bytes": wbi_mut_bytes,
        "stage9_nop_count": s9_nop,
        "stage10_dram_elastic_fifo_mib": fifo_mib,
        "stage10_relay_dropped_frames": relay_dropped,
        "stage10_rsv_salvageable_frames": rsv_salvageable,
        "stage10_rsv_committed_frames": rsv_committed,
        "stage11_nop_count": s11_nop,
        "stage11_null_gpio_derefs": s11_null_gpio,
        "stage11_mailbox_stalls": s11_mailbox_stalls,
        "stage11_bk4_persistent_nvram_writes": s11_bk4_writes,
        "stage11_digest_sha256": s11.get("phase78_audit_digest_sha256"),
    }
    domain = CapstoneDomainResult(
        domain_id="D5",
        domain_name="ELEVEN_STAGE_VM_COEMULATION",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {passed_stages}/{total_stages} stages (incl. Stage 11 Touch-AF/CIZ/Assignable "
            f"nop={s11_nop}, null_gpio={s11_null_gpio}), cp_mut={cp_mut_bytes}B "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "stage_count": total_stages,
        "passed_count": passed_stages,
        "cp_mutation_bytes": cp_mut_bytes,
    }
    return domain, meta


def _evaluate_domain_6(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: StageBCapstone22GateFaultInjection,
) -> Tuple[CapstoneDomainResult, Dict[str, Any]]:
    # 1. Verify Round 14 (18/18 4-lang x 3-surface matrix)
    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_e_nop_count=faults.d6_round14_nop_count,
        pillar_e_zero_pair_surface="status_check" if faults.d6_round14_zero_pair else None,
        pillar_e_zero_pair_name=ROUND14_4LANG_PAIRS[0] if faults.d6_round14_zero_pair else None,
    )
    pe, meta_r14 = _evaluate_pillar_e(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=v3_faults,
    )
    errors: List[str] = [e.replace("pillar_e", "d6_r14") for e in pe.errors]

    # 2. Verify Round 15 (Status Check 0x2f/0x30/0x31 multi-tab + 3-layer Monitoring CJK menu)
    r15, r15_source = _load_round15_summary(repo_root=repo_root, use_clean_room=use_clean_room)
    schema = str(r15.get("schema", ""))
    kernel_ver = str(r15.get("kernel_version", ""))
    if schema != "fx6-on-fx3-round15-multitab-status-monitoring-v1":
        errors.append(f"d6_r15: unexpected Round 15 schema {schema!r}")
    if "4.9.337-scel+" not in kernel_ver:
        errors.append(f"d6_r15: unexpected FX3 kernel_version {kernel_ver!r}")

    contract = r15.get("status_check_multitab_contract", {})
    tabs = contract.get("tabs_verified", [])
    tab_sids = tuple(str(t.get("sid", "")) for t in tabs if isinstance(t, Mapping))
    if tab_sids != ROUND15_MULTITAB_SIDS:
        errors.append(
            f"d6_r15: Status Check multi-tab sids expected {ROUND15_MULTITAB_SIDS!r}, got {tab_sids!r}"
        )

    runs = r15.get("runs", {})
    r15_nops = int(faults.d6_round15_nop_count)
    r15_crashes = int(faults.d6_round15_crashes)
    runs_verified = 0
    key_stage_b_sha_ok = True
    manifest_counts: Dict[str, int] = {}

    for run_id, expected_sid, expected_lang in ROUND15_RUN_SPECS:
        robj = runs.get(run_id)
        if not isinstance(robj, Mapping):
            errors.append(f"d6_r15: missing Round 15 run {run_id}")
            continue
        r15_nops += int(robj.get("nop_count", -1))
        r15_crashes += int(robj.get("crashes", -1))
        if robj.get("target_sid") != expected_sid or robj.get("lang") != expected_lang:
            errors.append(
                f"d6_r15: {run_id} expected sid={expected_sid} lang={expected_lang}, "
                f"got sid={robj.get('target_sid')!r} lang={robj.get('lang')!r}"
            )
        fi = robj.get("faithful_invariants", {})
        if fi.get("FX6_NATIVE_FAITHFUL") != 1 or any(
            int(fi.get(k, -1)) != 0
            for k in ("subst_color", "subst_image", "forced_render", "skipped_node", "lock_bypass")
        ):
            errors.append(f"d6_r15: {run_id} failed FX6_NATIVE_FAITHFUL invariants")
        sb = robj.get("stage_b", {})
        mc = (
            int(faults.d6_round15_manifest_count_override)
            if faults.d6_round15_manifest_count_override is not None
            else int(sb.get("manifest_count", -1))
        )
        manifest_counts[run_id] = mc
        items = sb.get("manifest_items", [])
        if mc != 13 or len(items) != 13:
            errors.append(f"d6_r15: {run_id} Stage-B manifest count expected 13/13, got {mc}/{len(items)}")
        by_path = {str(it.get("guest_path")): str(it.get("sha256")) for it in items if isinstance(it, Mapping)}
        if by_path.get("/usr/lib/appFw.so") != FX6_APPFW_STAGE_B_SHA256:
            key_stage_b_sha_ok = False
        if by_path.get("/usr/lib/libWlanResource.so") != FX6_WLAN_RSRC_P12_SHA256:
            key_stage_b_sha_ok = False
        runs_verified += 1

    if not key_stage_b_sha_ok:
        errors.append("d6_r15: Stage-B manifest_items SHA-256 mismatch for appFw.so or libWlanResource.so")
    if r15_nops != 0:
        errors.append(f"d6_r15: Round 15 real-kernel nop_count={r15_nops} != 0")
    if r15_crashes != 0:
        errors.append(f"d6_r15: Round 15 real-kernel crashes={r15_crashes} != 0")

    audit = copy.deepcopy(r15.get("r15_multitab_and_category_audit", {}))
    stepping = audit.get("status_check_multitab_stepping_schinese", {})
    cat_nav = audit.get("menu_3layer_category_navigation_schinese", {})
    cross_cjk = audit.get("cjk_cross_engine_tab2_audit", {})

    if faults.d6_round15_zero_tab_pair and faults.d6_round15_zero_tab_pair in stepping:
        stepping[faults.d6_round15_zero_tab_pair]["diff_pixels"] = 0
        stepping[faults.d6_round15_zero_tab_pair]["strictly_positive"] = False
    if faults.d6_round15_zero_category_pair and faults.d6_round15_zero_category_pair in cat_nav:
        cat_nav[faults.d6_round15_zero_category_pair]["diff_pixels"] = 0
        cat_nav[faults.d6_round15_zero_category_pair]["strictly_positive"] = False

    tab_deltas: Dict[str, int] = {}
    for pk in ROUND15_STEPPING_PAIR_KEYS:
        ent = stepping.get(pk, {})
        px = int(ent.get("diff_pixels", 0))
        tab_deltas[pk] = px
        if px <= 0 or not bool(ent.get("strictly_positive", False)):
            errors.append(f"d6_r15: Status Check multi-tab pair {pk} delta is not strictly positive")

    cat_deltas: Dict[str, int] = {}
    for pk in ROUND15_CATEGORY_PAIR_KEYS:
        ent = cat_nav.get(pk, {})
        px = int(ent.get("diff_pixels", 0))
        cat_deltas[pk] = px
        if px <= 0 or not bool(ent.get("strictly_positive", False)):
            errors.append(f"d6_r15: 3-layer Monitoring category pair {pk} delta is not strictly positive")

    for pk in ("japanese_tab1_vs_tab2", "schinese_tab2_vs_japanese_tab2"):
        ent = cross_cjk.get(pk, {})
        if int(ent.get("diff_pixels", 0)) <= 0 or not bool(ent.get("strictly_positive", False)):
            errors.append(f"d6_r15: CJK cross-engine pair {pk} delta is not strictly positive")

    passed = (
        len(errors) == 0
        and pe.passed
        and runs_verified == len(ROUND15_RUN_SPECS)
        and r15_nops == 0
        and r15_crashes == 0
        and key_stage_b_sha_ok
    )
    evidence = {
        "round14_positive_pairs": meta_r14["positive_pairs"],
        "round14_nop_count": meta_r14["nop_count"],
        "round14_source": pe.evidence["round14_source"],
        "round15_source": r15_source,
        "round15_schema": schema,
        "round15_kernel_version": kernel_ver,
        "round15_tabs_verified": len(tab_sids),
        "round15_tab_sids": list(tab_sids),
        "round15_runs_verified": runs_verified,
        "round15_run_ids": list(ROUND15_RUN_IDS),
        "round15_nop_count": r15_nops,
        "round15_crashes": r15_crashes,
        "round15_manifest_counts": manifest_counts,
        "round15_stage_b_sha256_verified": key_stage_b_sha_ok,
        "round15_tab_stepping_deltas": tab_deltas,
        "round15_monitoring_category_deltas": cat_deltas,
    }
    domain = CapstoneDomainResult(
        domain_id="D6",
        domain_name="ROUND15_MULTITAB_REAL_KERNEL_CLOSURE",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"R14 {meta_r14['positive_pairs']}/18 + R15 FX3 7.02 (0x2f/0x30/0x31 {len(tab_sids)} tabs + "
            f"Monitoring 0x11, {runs_verified}/4 runs, nop={r15_nops}, crash={r15_crashes}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "round14_positive_pairs": meta_r14["positive_pairs"],
        "round15_tabs_verified": len(tab_sids),
        "round15_runs_verified": runs_verified,
        "round15_nop_count": r15_nops,
        "round15_crashes": r15_crashes,
    }
    return domain, meta


def _evaluate_domain_7(
    raw_7: Mapping[str, Any],
    faults: StageBCapstone22GateFaultInjection,
) -> Tuple[CapstoneDomainResult, Dict[str, Any]]:
    v3_faults = StageBReleaseDossierV3FaultInjection(
        pillar_f_drift_surface=faults.d7_drift_surface,
        pillar_f_tamper_negative_control=faults.d7_tamper_negative_control,
    )
    pf, meta_f = _evaluate_pillar_f(raw_7, v3_faults)
    errors: List[str] = [e.replace("pillar_f", "d7") for e in pf.errors]
    if DOSSIER_V3_SCHEMA_VERSION != STAGE_B_RELEASE_DOSSIER_V3_SCHEMA or len(PILLAR_IDS) != 6:
        errors.append("d7: Dossier v3 anchor contract mismatch")

    passed = len(errors) == 0 and pf.passed
    evidence = dict(pf.evidence)
    evidence["dossier_v3_schema_anchor"] = DOSSIER_V3_SCHEMA_VERSION
    evidence["dossier_v3_pillar_count"] = len(PILLAR_IDS)

    domain = CapstoneDomainResult(
        domain_id="D7",
        domain_name="DOSSIER_V3_AND_H0_VS_H2_FORENSIC_IMMUTABILITY",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Dossier v3 + H0==H2 {meta_f['h0_surface_count']}/16 surfaces "
            f"(drifted={meta_f['drifted_surface_count']}, C2PA intact={meta_f['c2pa_rq_lic_intact']}, "
            f"scenarios={raw_7['audit_passed_scenario_count']}/{raw_7['audit_scenario_count']}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    return domain, meta_f


# ---------------------------------------------------------------------------
# Parallel Collector, Builder & Fail-Closed Verifier
# ---------------------------------------------------------------------------


def _fault_to_worker_dict(faults: StageBCapstone22GateFaultInjection) -> Dict[str, Any]:
    return {
        "d1_xlr_kwargs": dict(faults.d1_xlr_kwargs) if faults.d1_xlr_kwargs is not None else None,
        "d1_gimbal_kwargs": dict(faults.d1_gimbal_kwargs) if faults.d1_gimbal_kwargs is not None else None,
        "d1_rig_kwargs": dict(faults.d1_rig_kwargs) if faults.d1_rig_kwargs is not None else None,
        "d1_emount_kwargs": dict(faults.d1_emount_kwargs) if faults.d1_emount_kwargs is not None else None,
        "d1_power_failover_kwargs": (
            dict(faults.d1_power_failover_kwargs)
            if faults.d1_power_failover_kwargs is not None
            else None
        ),
        "d1_request_persistent_writes": bool(faults.d1_request_persistent_writes),
        "d2_otp_downgrade_version": faults.d2_otp_downgrade_version,
        "d2_inject_cross_sku_target": faults.d2_inject_cross_sku_target,
        "d2_inject_ext_csd_perm_wp": bool(faults.d2_inject_ext_csd_perm_wp),
        "d3_inject_cross_body_cnflasha_transplant": bool(
            faults.d3_inject_cross_body_cnflasha_transplant
        ),
    }


def _collect_parallel_capstone_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: StageBCapstone22GateFaultInjection,
) -> Tuple[
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Any],
    Dict[str, Dict[str, Any]],
    Dict[str, Any],
    Dict[str, Any],
]:
    fault_dict = _fault_to_worker_dict(faults)
    d4_groups = ("group_a", "group_b", "multilang", "sensor", "haita", "emount", "wbi", "assignable")

    use_fork_pool = not use_clean_room
    if use_fork_pool:
        try:
            ctx = mp.get_context("fork")
            with ProcessPoolExecutor(max_workers=10, mp_context=ctx) as ex:
                fut_1 = ex.submit(_worker_domain_1, (str(repo_root), use_clean_room, fault_dict))
                fut_2 = ex.submit(_worker_domain_2, (use_clean_room, fault_dict))
                fut_3 = ex.submit(
                    _worker_pillar_b,
                    (
                        use_clean_room,
                        {
                            "pillar_b_inject_cross_body_cnflasha_transplant": bool(
                                faults.d3_inject_cross_body_cnflasha_transplant
                            )
                        },
                    ),
                )
                fut_4 = [ex.submit(_worker_domain_4_group, (g, use_clean_room)) for g in d4_groups]
                fut_5 = ex.submit(_worker_domain_5, use_clean_room)
                fut_7 = ex.submit(
                    _worker_pillar_f,
                    (
                        str(fx6_lib_dir),
                        str(fx3_modules_dir),
                        use_clean_room,
                        faults.d7_drift_surface,
                    ),
                )
                raw_1 = fut_1.result()
                raw_2 = fut_2.result()
                raw_3 = fut_3.result()
                auditors: Dict[str, Dict[str, Any]] = {}
                for fg in fut_4:
                    auditors.update(fg.result())
                raw_5 = fut_5.result()
                raw_7 = fut_7.result()
                return raw_1, raw_2, raw_3, auditors, raw_5, raw_7
        except (ValueError, RuntimeError, OSError):
            pass

    raw_1 = _worker_domain_1((str(repo_root), use_clean_room, fault_dict))
    raw_2 = _worker_domain_2((use_clean_room, fault_dict))
    raw_3 = _worker_pillar_b(
        (
            use_clean_room,
            {
                "pillar_b_inject_cross_body_cnflasha_transplant": bool(
                    faults.d3_inject_cross_body_cnflasha_transplant
                )
            },
        )
    )
    auditors = {}
    for g in d4_groups:
        auditors.update(_worker_domain_4_group((g, use_clean_room)))
    raw_5 = _worker_domain_5(use_clean_room)
    raw_7 = _worker_pillar_f(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, faults.d7_drift_surface)
    )
    return raw_1, raw_2, raw_3, auditors, raw_5, raw_7


def build_stage_b_capstone_22gate_report(
    *,\
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[StageBCapstone22GateFaultInjection] = None,
) -> StageBCapstone22GateReport:
    """Build deterministic 7-Domain Stage-B Capstone 22-Gate verifier report."""
    active_faults = faults if faults is not None else StageBCapstone22GateFaultInjection()
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    verification_mode = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"

    raw_1, raw_2, raw_3, auditors, raw_5, raw_7 = _collect_parallel_capstone_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )

    d1 = _evaluate_domain_1(raw_1)
    d2, meta_2 = _evaluate_domain_2(raw_2, active_faults)
    d3 = _evaluate_domain_3(raw_3, active_faults)
    d4, meta_4 = _evaluate_domain_4(auditors, active_faults)
    d5, meta_5 = _evaluate_domain_5(raw_5, active_faults)
    d6, meta_6 = _evaluate_domain_6(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )
    d7, meta_7 = _evaluate_domain_7(raw_7, active_faults)

    domains = (d1, d2, d3, d4, d5, d6, d7)
    all_errors: List[str] = []
    for dom in domains:
        for err in dom.errors:
            all_errors.append(f"{dom.domain_id}: {err}")

    failed_ids = tuple(dom.domain_id for dom in domains if not dom.passed)
    passed_count = sum(1 for dom in domains if dom.passed)

    total_cp_mut = max(int(meta_5["cp_mutation_bytes"]), int(meta_7["cp_mutation_bytes"]))
    total_wbi_mut = int(meta_7["wbi_mutation_bytes"])
    total_cal_mut = max(
        int(meta_4["calibration_mutation_bytes"]),
        int(meta_7["calibration_mutation_bytes"]),
    )
    otp_touches = int(meta_2["otp_fuse_touches"])
    rpmb_inc = int(meta_2["rpmb_counter_increments"])
    temp_cleaned = bool(meta_7["temp_dir_cleaned"])

    all_ready = (
        len(domains) == 7
        and passed_count == 7
        and len(failed_ids) == 0
        and len(all_errors) == 0
        and temp_cleaned
        and total_cp_mut == 0
        and total_wbi_mut == 0
        and total_cal_mut == 0
        and int(meta_4["bk4_persistent_nvram_writes"]) == 0
        and otp_touches == 0
        and rpmb_inc == 0
        and int(meta_7["drifted_surface_count"]) == 0
        and bool(meta_7["c2pa_rq_lic_intact"])
        and bool(meta_7["spacc_cnflasha_untouched"])
    )

    draft = StageBCapstone22GateReport(
        schema_version=STAGE_B_CAPSTONE_22GATE_SCHEMA,
        phase_version=PHASE_83_VERSION,
        verification_mode=verification_mode,
        all_domains_capstone_ready=all_ready,
        status=STATUS_SIMULATION_READY if all_ready else STATUS_FAIL_CLOSED,
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
        domain_count=len(domains),
        passed_domain_count=passed_count,
        failed_domain_ids=failed_ids,
        domains=domains,
        gate22_offline_verified=int(raw_1["offline_verified_gates"]),
        gate22_simulated_verified=int(raw_1["sim_verified_gates"]),
        firmware_lab_auditor_count=int(meta_4["auditor_count"]),
        firmware_lab_auditors_passed=int(meta_4["passed_count"]),
        vm_coemulation_stage_count=int(meta_5["stage_count"]),
        vm_coemulation_stages_passed=int(meta_5["passed_count"]),
        round14_positive_pairs=int(meta_6["round14_positive_pairs"]),
        round15_tabs_verified=int(meta_6["round15_tabs_verified"]),
        round15_runs_verified=int(meta_6["round15_runs_verified"]),
        round15_nop_count=int(meta_6["round15_nop_count"]),
        round15_crashes=int(meta_6["round15_crashes"]),
        h0_surface_count=int(meta_7["h0_surface_count"]),
        drifted_surface_count=int(meta_7["drifted_surface_count"]),
        c2pa_rq_lic_intact=bool(meta_7["c2pa_rq_lic_intact"]),
        spacc_cnflasha_untouched=bool(meta_7["spacc_cnflasha_untouched"]),
        errors=tuple(all_errors),
        capstone_sha256="",
    )
    digest = compute_capstone_22gate_sha256(draft.to_dict())
    return replace(draft, capstone_sha256=digest)


def verify_stage_b_capstone_22gate(
    payload: object,
) -> StageBCapstone22GateVerifyResult:
    """Fail-closed tamper-evident verifier for `stage_b_capstone_22gate_v1` reports."""
    if isinstance(payload, StageBCapstone22GateReport):
        data: Dict[str, Any] = payload.to_dict()
    elif isinstance(payload, Mapping):
        data = dict(payload)
    else:
        return StageBCapstone22GateVerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_capstone_sha256="",
            observed_capstone_sha256="",
            safety_redlines_ok=False,
            all_7_domains_ok=False,
            all_domains_capstone_ready=False,
            errors=("Capstone payload must be a mapping or StageBCapstone22GateReport",),
        )

    errors: List[str] = []
    schema_ok = data.get("schema_version") == STAGE_B_CAPSTONE_22GATE_SCHEMA
    if not schema_ok:
        errors.append(
            f"Invalid schema_version {data.get('schema_version')!r}, expected {STAGE_B_CAPSTONE_22GATE_SCHEMA!r}"
        )

    observed_digest = str(data.get("capstone_sha256", ""))
    expected_digest = compute_capstone_22gate_sha256(data)
    digest_matched = bool(HEX64_RE.fullmatch(observed_digest)) and (observed_digest == expected_digest)
    if not digest_matched:
        errors.append(
            f"capstone_sha256 mismatch: observed={observed_digest!r} vs expected={expected_digest!r}"
        )

    rendered = json.dumps(data, sort_keys=True, ensure_ascii=False)
    if _RAW_BYTES_REPR_RE.search(rendered):
        errors.append("Capstone report contains forbidden raw binary bytes repr")

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
        errors.append("Hard-locked safety redlines violated in Stage-B Capstone 22-Gate report")

    domains_raw = data.get("domains")
    all_7_domains_ok = False
    if not isinstance(domains_raw, (list, tuple)) or len(domains_raw) != 7:
        errors.append("domains must contain exactly 7 entries (D1..D7)")
    else:
        seen_ids = tuple(str(d.get("domain_id", "")) for d in domains_raw if isinstance(d, Mapping))
        if seen_ids != DOMAIN_IDS:
            errors.append(f"Domain sequence mismatch: {seen_ids!r} != {DOMAIN_IDS!r}")
        else:
            all_7_domains_ok = all(
                isinstance(d, Mapping)
                and d.get("passed") is True
                and d.get("status") == STATUS_SIMULATION_READY
                for d in domains_raw
            )
            if not all_7_domains_ok:
                errors.append("One or more domains in D1..D7 failed")

    all_domains_capstone_ready = (
        data.get("all_domains_capstone_ready") is True
        and data.get("status") == STATUS_SIMULATION_READY
        and data.get("passed_domain_count") == 7
        and data.get("domain_count") == 7
        and data.get("gate22_offline_verified") == 19
        and data.get("gate22_simulated_verified") == 22
        and data.get("firmware_lab_auditor_count") == 14
        and data.get("firmware_lab_auditors_passed") == 14
        and data.get("vm_coemulation_stage_count") == 11
        and data.get("vm_coemulation_stages_passed") == 11
        and data.get("round14_positive_pairs") == 18
        and data.get("round15_tabs_verified") == 3
        and data.get("round15_runs_verified") == 4
        and data.get("round15_nop_count") == 0
        and data.get("round15_crashes") == 0
        and data.get("h0_surface_count") == 16
        and data.get("drifted_surface_count") == 0
        and data.get("c2pa_rq_lic_intact") is True
        and data.get("spacc_cnflasha_untouched") is True
    )
    if not all_domains_capstone_ready:
        errors.append("all_domains_capstone_ready is False or capstone readiness counters failed")

    valid = (
        schema_ok
        and digest_matched
        and safety_redlines_ok
        and all_7_domains_ok
        and all_domains_capstone_ready
        and len(errors) == 0
    )
    return StageBCapstone22GateVerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_capstone_sha256=expected_digest,
        observed_capstone_sha256=observed_digest,
        safety_redlines_ok=safety_redlines_ok,
        all_7_domains_ok=all_7_domains_ok,
        all_domains_capstone_ready=all_domains_capstone_ready,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Bilingual Markdown Summary Generator (中文 + English)
# ---------------------------------------------------------------------------


def render_capstone_22gate_markdown(report: StageBCapstone22GateReport) -> str:
    """Render deterministic bilingual (中文 + English) Stage-B Capstone 22-Gate signoff packet."""
    lines: List[str] = [
        "# Stage-B 终局 22-Gate 与防回滚闭环验证报告 / Stage-B Capstone 22-Gate & Anti-Rollback Verification Report (`stage_b_capstone_22gate_v1`)",
        "",
        f"- **Schema Version / 档案模式**: `{report.schema_version}` (`v{report.phase_version}`)",
        f"- **Verification Mode / 验证模式**: `{report.verification_mode}` (`o_rdonly_enforced={report.o_rdonly_enforced}`)",
        (
            f"- **Capstone Verdict / 综合结论**: `{report.status}` "
            f"(`all_domains_capstone_ready={report.all_domains_capstone_ready}`, "
            f"`{report.passed_domain_count}/{report.domain_count}` domains)"
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
        f"- **Canonical Capstone SHA-256 / 不可篡改签章摘要**: `{report.capstone_sha256}`",
        "",
        "## 七大终局验证域矩阵 / 7-Domain Capstone Matrix (`D1 .. D7`)",
        "",
        "| Domain | Name | Status | Summary / 摘要 |",
        "| :---: | --- | :---: | --- |",
    ]
    for dom in report.domains:
        lines.append(f"| `{dom.domain_id}` | `{dom.domain_name}` | `{dom.status}` | {dom.summary} |")

    lines.extend(
        [
            "",
            "## 关键工程与安全红线指标 / Key Metrics & Hard-Locked Redlines",
            "",
            f"- **22-Gate 预检 (`D1`)**: 离线真机前置阻断 `{report.gate22_offline_verified}/22` vs 模拟演练 `{report.gate22_simulated_verified}/22`（含 `G21` XLR-H1 +48V 幻象电源防火墙与 `G22` 稳定器/跟焦器 E 卡口扭矩、激光护 sensor 与快门帘保护）",
            f"- **OTP / RPMB 防回滚与 EXT_CSD 写保护 (`D2`)**: `otp_fuse_touches={report.otp_fuse_touches}`, `rpmb_counter_increments={report.rpmb_counter_increments}`, FX3 v7.02 + FX6 v6.01 = `TIER_A_GOLD_VERIFIED`, 永久写保护熔丝陷阱已阻断",
            "- **Tier-0 GF(256) 与 SD 卡紧急逃生 (`D3`)**: RAID-6 P+Q 双分片自愈 + `cnflasha`/`C2PA` 跨机防移植锁 + `FX3_SAFE_STOCK.FLG` 秒级回退stock",
            f"- **固件实验室 14 项跨机审计 (`D4`)**: `{report.firmware_lab_auditors_passed}/{report.firmware_lab_auditor_count}` auditors pass（含 Phase 75 可自定义键 / T-W 清晰影像变焦 / Touch-AF / Big6-Fn CAMSET 易失影子）",
            f"- **11 阶段异构共仿真 (`D5`)**: `{report.vm_coemulation_stages_passed}/{report.vm_coemulation_stage_count}` stages pass（含 Stage 11 Touch-AF / CIZ / Assignable）",
            f"- **Round 14 + Round 15 真核多标签 UI 闭环 (`D6`)**: Round 14 `{report.round14_positive_pairs}/18` + Round 15 FX3 `4.9.337-scel+` Status Check `{report.round15_tabs_verified}` 标签 (`0x2f/0x30/0x31`) + 3 层 Monitoring (`0x11`)，`{report.round15_runs_verified}/4` runs `nop_count={report.round15_nop_count}`, `crashes={report.round15_crashes}`",
            f"- **Dossier v3 与 H0==H2 取证 (`D7`)**: `{report.h0_surface_count}/16` 表面逐比特一致（`drifted_surface_count={report.drifted_surface_count}`，`c2pa_rq_lic_intact={report.c2pa_rq_lic_intact}`，`spacc_cnflasha_untouched={report.spacc_cnflasha_untouched}`）",
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
    "CAPSTONE_22GATE_SCHEMA_VERSION",
    "CP_MUTATION_BYTES",
    "DEFAULT_FX3_MODULES_DIR",
    "DEFAULT_FX6_DONOR_LIB_DIR",
    "DEFAULT_REPO_ROOT",
    "DOMAIN_IDS",
    "DOMAIN_SPECS",
    "FIRMWARE_LAB_14_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "OTP_FUSE_TOUCHES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_83_VERSION",
    "ROUND15_CATEGORY_PAIR_KEYS",
    "ROUND15_MULTITAB_SIDS",
    "ROUND15_RUN_IDS",
    "ROUND15_RUN_SPECS",
    "ROUND15_STEPPING_PAIR_KEYS",
    "ROUND15_SUMMARY_RELPATH",
    "RPMB_COUNTER_INCREMENTS",
    "SCHEMA_VERSION",
    "STAGE_B_CAPSTONE_22GATE_SCHEMA",
    "STATUS_FAIL_CLOSED",
    "STATUS_SIMULATION_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "VM_COEMULATION_11_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "CapstoneDomainResult",
    "StageBCapstone22GateFaultInjection",
    "StageBCapstone22GateReport",
    "StageBCapstone22GateVerifyResult",
    "build_stage_b_capstone_22gate_report",
    "compute_capstone_22gate_sha256",
    "render_capstone_22gate_markdown",
    "verify_stage_b_capstone_22gate",
]
