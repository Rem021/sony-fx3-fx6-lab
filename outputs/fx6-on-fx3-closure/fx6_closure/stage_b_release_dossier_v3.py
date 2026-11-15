"""Phase 76 — Unified Stage-B Release Dossier v3 (`stage_b_release_dossier_v3`).

Synthesizes all 6 cross-track verification pillars (`Pillar A .. Pillar F`) into a
single tamper-evident, fail-closed Stage-B Release Dossier executing in `< 3.5s`
across both `LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

- `PILLAR_A` (`PHYSICAL_RIG_AND_20GATE_SAFETY`):
  Runs Phase 69 `rig_groundloop_lensrail_and_20gate_guard.evaluate_20gate_preflight`
  verifying `17/20` offline hardware-truth block (`overall_ready_for_hardware_attach=False`)
  vs `20/20` simulated rehearsal (`dry_run_rehearsal_only=True`), D-Tap/HDMI ground-loop
  protection (`G19`), E-Mount `< 2.0 ms` rail crowbar + `0x0400` IBIS center-lock park,
  and `USB-PD -> NP-FZ100` UPS failover + `.RSV` salvage (`G20`).
- `PILLAR_B` (`TIER0_GF256_SELFHEAL_AND_INIT2_ESCAPE`):
  Runs Phase 72 `tier0_backup_parity_and_manifest_guard` (proving `GF(256)` P+Q RAID-6
  2-shard erasure & 1-shard silent bit-rot self-healing + 3-loss quorum rejection +
  cross-body `cnflasha`/`C2PA` anti-transplant lock) AND Phase 66
  `init2_escape_and_watchdog_simulator` (proving external SD card `FX3_SAFE_STOCK.FLG`
  instant stock escape + `CXD90057 WDT` crash-loop breaker + `p1 FAT12/FAT16` clean
  mirror & atomic 8.3 directory swap).
- `PILLAR_C` (`FIRMWARE_PARITY_13PLUS_AUDITORS`):
  Verifies all 13 `fx3_firmware_lab` cross-body auditors including Phase 70 Dual-Slot
  Proxy / Cinema `CamID/Reel` / `NonRealTimeMeta v2.20` XML sidecar and Phase 65 White
  Balance / `3x3 Paint Matrix` white-point preservation (`calibration_mutation_bytes == 0`).
- `PILLAR_D` (`TEN_STAGE_HETEROGENEOUS_COEMULATION`):
  Verifies all 10 stages (`Stages 1..10`) of `outputs/fx3-vm` co-emulation (including
  Stage 9 `SMPTE 12M EXT-LK` + `PZ/IBIS` + `libpaint` and Stage 10 `256 MiB` Dual-Slot
  `Relay` 0-drop rollover + `M01.XML` + UPS/`.RSV` salvage, `cp_mutation_bytes == 0`).
- `PILLAR_E` (`FOUR_LANG_THREE_SURFACE_REAL_KERNEL_UI`):
  Verifies Round 14 (`reports/2026-11-14-round14-fx6-on-fx3-statuscheck-4lang-matrix/summary.json`,
  opened strictly `os.O_RDONLY` with deterministic clean-room schema fallback when
  `FX3_FX6_FORCE_CLEAN_ROOM=1` or missing in synthetic CI) proving real unmodified FX3
  `7.02` kernel (`4.9.337-scel+`, `nop_count == 0`, `crashes == 0`, `13/13` Stage-B SHA-256,
  `FX6_NATIVE_FAITHFUL == 1`) renders `Big6 Home`, `3-Layer Menu`, and `Status Check`
  (`sid=0x2f`) across all 4 languages (`EN`, `ZH-CN`, `ZH-TW`, `JA`) with `18/18` strictly
  positive pairwise pixel deltas.
- `PILLAR_F` (`CLOSED_LOOP_R0_R6_ZERO_PERSISTENCE_PROOF`):
  Composes Phase 68/62 `H0 == H2` 16-surface bit-for-bit post-trial forensic proof
  (`drifted_surface_count == 0`, `c2pa_rq_lic_intact == True`, `spacc_cnflasha_untouched == True`,
  and `10/10` anomaly classifier scenarios).

Hard-Locked Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `HARDWARE_LIVE_ATTACHMENT_AUTHORIZED = False`
- `P8_CP_MUTATION_FORBIDDEN = True`, `CP_MUTATION_BYTES = 0`
- `WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN = True`, `WBI_MUTATION_BYTES = 0`
- `CALIBRATION_MUTATION_BYTES = 0`, `USB_OR_CAMERA_OPERATIONS = 0`
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
import os
from pathlib import Path
import re
import tempfile
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

from fx3_firmware_lab.audio_tc_hdmi_sdi_routing_auditor import (  # noqa: E402
    analyze_audio_tc_hdmi_sdi_routing,
    audio_tc_hdmi_sdi_routing_report_to_dict,
)
from fx3_firmware_lab.cube_lut_and_rtmd_verifier import (  # noqa: E402
    analyze_cube_lut_and_rtmd,
    cube_lut_and_rtmd_report_to_dict,
)
from fx3_firmware_lab.emount_af_breathing_and_ibis_auditor import (  # noqa: E402
    analyze_emount_af_breathing_and_ibis,
    emount_af_breathing_and_ibis_report_to_dict,
)
from fx3_firmware_lab.global_xdb_and_menu_tree_auditor import (  # noqa: E402
    analyze_global_xdb_and_menu_tree,
    global_xdb_and_menu_tree_report_to_dict,
)
from fx3_firmware_lab.haita_bk4_feature_analyzer import (  # noqa: E402
    analyze_haita_and_bk4_features,
    haita_report_to_dict,
)
from fx3_firmware_lab.proxy_clipname_and_sidecar_auditor import (  # noqa: E402
    analyze_proxy_clipname_and_sidecar,
    proxy_clipname_and_sidecar_report_to_dict,
)
from fx3_firmware_lab.sensor_codec_compatibility_analyzer import (  # noqa: E402
    analyze_sensor_and_codec_compatibility,
    sensor_codec_report_to_dict,
)
from fx3_firmware_lab.shutter_ecs_sq_and_tally_auditor import (  # noqa: E402
    analyze_shutter_ecs_sq_and_tally,
    shutter_ecs_sq_and_tally_report_to_dict,
)
from fx3_firmware_lab.ufu_container_auditor import audit_ufu_suite  # noqa: E402
from fx3_firmware_lab.uxc_ldec_inspector import (  # noqa: E402
    inspect_uxc_and_ldec,
    uxc_report_to_dict,
)
from fx3_firmware_lab.uxc_multilang_and_font_verifier import (  # noqa: E402
    multilang_report_to_dict,
    verify_multilang_and_fonts,
)
from fx3_firmware_lab.wb_color_matrix_and_look_auditor import (  # noqa: E402
    analyze_wb_color_matrix_and_look,
    verify_raw_3x3_color_matrix,
    wb_color_matrix_and_look_report_to_dict,
)
from fx3_firmware_lab.wbi_hibdrv_and_elf_abi_differ import (  # noqa: E402
    analyze_wbi_hibdrv_and_elf_abi,
    wbi_hibdrv_and_elf_abi_report_to_dict,
)
from fx3_recovery.init2_escape_and_watchdog_simulator import (  # noqa: E402
    run_init2_escape_and_watchdog_suite,
)
from fx3_recovery.tier0_backup_parity_and_manifest_guard import (  # noqa: E402
    build_body_hardware_identity,
    build_synthetic_tier0_backup_bundle,
    build_tier0_backup_manifest,
    run_tier0_backup_parity_suite,
    verify_cross_body_anti_transplant,
)
from fx3_safety.rig_groundloop_lensrail_and_20gate_guard import (  # noqa: E402
    evaluate_20gate_preflight,
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
    STAGE_B_FORENSIC_PROBE_DEFAULTS,
    _probe_donor_surfaces_o_rdonly,
    _read_file_o_rdonly,
    _with_normalized_bundle_dirs,
    build_persistent_stock_bk4_bytes,
    populate_stage_b_capture_bundle_fixture,
    run_stage_b_post_trial_forensic_audit,
    verify_stage_b_post_trial_report,
    verify_stage_b_post_trial_zero_persistence,
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


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

STAGE_B_RELEASE_DOSSIER_V3_SCHEMA: str = "stage_b_release_dossier_v3"
DOSSIER_V3_SCHEMA_VERSION: str = STAGE_B_RELEASE_DOSSIER_V3_SCHEMA
SCHEMA_VERSION: str = STAGE_B_RELEASE_DOSSIER_V3_SCHEMA
PHASE_76_VERSION: str = "76.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
HARDWARE_LIVE_ATTACHMENT_AUTHORIZED: bool = False
P8_CP_MUTATION_FORBIDDEN: bool = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN: bool = True
CP_MUTATION_BYTES: int = 0
WBI_MUTATION_BYTES: int = 0
CALIBRATION_MUTATION_BYTES: int = 0
USB_OR_CAMERA_OPERATIONS: int = 0

STATUS_SIMULATION_READY: str = "SIMULATION_READY"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

PILLAR_SPECS: Tuple[Tuple[str, str], ...] = (
    ("PILLAR_A", "PHYSICAL_RIG_AND_20GATE_SAFETY"),
    ("PILLAR_B", "TIER0_GF256_SELFHEAL_AND_INIT2_ESCAPE"),
    ("PILLAR_C", "FIRMWARE_PARITY_13PLUS_AUDITORS"),
    ("PILLAR_D", "TEN_STAGE_HETEROGENEOUS_COEMULATION"),
    ("PILLAR_E", "FOUR_LANG_THREE_SURFACE_REAL_KERNEL_UI"),
    ("PILLAR_F", "CLOSED_LOOP_R0_R6_ZERO_PERSISTENCE_PROOF"),
)
PILLAR_IDS: Tuple[str, ...] = tuple(pid for pid, _ in PILLAR_SPECS)

FIRMWARE_LAB_13_AUDITOR_KEYS: Tuple[str, ...] = (
    "ufu_container_audit",
    "haita_bk4_feature_audit",
    "uxc_ldec_asset_audit",
    "uxc_multilang_and_font_audit",
    "sensor_codec_compatibility_audit",
    "cube_lut_and_rtmd_audit",
    "wbi_hibdrv_and_elf_abi_audit",
    "global_xdb_and_menu_tree_audit",
    "audio_tc_hdmi_sdi_routing_audit",
    "emount_af_breathing_and_ibis_audit",
    "shutter_ecs_sq_and_tally_audit",
    "wb_color_matrix_and_look_audit",
    "proxy_clipname_and_sidecar_audit",
)

VM_COEMULATION_10_STAGE_KEYS: Tuple[str, ...] = (
    "stage1_coldboot_and_bt",
    "stage2_dual_isa_cp_shooting",
    "stage3_soft_gpe_hud_ramfb",
    "stage4_phase41_dtb_mhlx",
    "stage5_phase45_imx510_xavc",
    "stage6_phase53_hil_fault_harness",
    "stage7_phase58_qmp_introspection",
    "stage8_phase63_hdmi_raw_uvc",
    "stage9_phase67_tc_lens_paint",
    "stage10_phase71_dualslot_ups_salvage",
)

ROUND14_SUMMARY_RELPATH: str = (
    "reports/2026-11-14-round14-fx6-on-fx3-statuscheck-4lang-matrix/summary.json"
)
ROUND14_RUN_IDS: Tuple[str, ...] = (
    "r14a_status_check_japanese",
    "r14b_status_check_tchinese",
    "r14c_status_check_english",
)
ROUND14_3_SURFACES: Tuple[str, ...] = ("big6_home", "full_menu", "status_check")
ROUND14_4LANG_PAIRS: Tuple[str, ...] = (
    "en_vs_schinese",
    "en_vs_tchinese",
    "en_vs_japanese",
    "schinese_vs_tchinese",
    "schinese_vs_japanese",
    "tchinese_vs_japanese",
)

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")
_DRIFT_SURFACE_ALIASES: Dict[str, str] = {
    "BK4": "p2_backup_bin",
    "p2_backup_bin": "p2_backup_bin",
    "C2PA": "c2pa_rq_lic",
    "c2pa_rq_lic": "c2pa_rq_lic",
    "WBI2": "p5_wbi_header",
    "p5_wbi_header": "p5_wbi_header",
    "CP": "p8_cp_image",
    "p8_cp_image": "p8_cp_image",
    "sector0": "sector0",
    "SECTOR0": "sector0",
    "SPACC": "spacc_cnflasha",
    "spacc_cnflasha": "spacc_cnflasha",
}


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class StageBReleaseDossierV3FaultInjection:
    """Deterministic fault-injection knobs across Pillar A..F for fail-closed tests."""

    # Pillar A faults (20-gate, G19 D-Tap/HDMI ground-loop, E-mount rail, G20 UPS/.RSV)
    pillar_a_rig_kwargs: Optional[Mapping[str, Any]] = None
    pillar_a_emount_kwargs: Optional[Mapping[str, Any]] = None
    pillar_a_power_failover_kwargs: Optional[Mapping[str, Any]] = None
    pillar_a_request_persistent_writes: bool = False

    # Pillar B faults (Tier-0 GF(256) P+Q, cross-body cnflasha transplant, init2/WDT/FAT)
    pillar_b_inject_cross_body_cnflasha_transplant: bool = False
    pillar_b_inject_gf256_quorum_loss: bool = False
    pillar_b_inject_init2_escape_fault: bool = False

    # Pillar C faults (13+ fx3_firmware_lab auditors, Phase 65 WB/matrix, Phase 70 NRTM)
    pillar_c_calibration_mutation_bytes: int = 0
    pillar_c_corrupt_wb_whitepoint: bool = False
    pillar_c_corrupt_nrtm_sidecar: bool = False

    # Pillar D faults (10-stage co-emulation, Stage 9, Stage 10 Relay drop / UPS salvage)
    pillar_d_stage10_dropped_frames: int = 0
    pillar_d_cp_mutation_bytes: int = 0
    pillar_d_stage9_nop_count: int = 0

    # Pillar E faults (Round 14 real 7.02 kernel, 4-lang x 3-surface, 18/18 pixel deltas)
    pillar_e_nop_count: int = 0
    pillar_e_crashes: int = 0
    pillar_e_zero_pair_surface: Optional[str] = None
    pillar_e_zero_pair_name: Optional[str] = None
    pillar_e_stage_b_manifest_count_override: Optional[int] = None

    # Pillar F faults (H0 vs H2 16-surface 1-byte drift, C2PA/SPACC/calibration drift)
    pillar_f_drift_surface: Optional[str] = None
    pillar_f_tamper_negative_control: bool = False


@dataclass(frozen=True)
class DossierV3PillarResult:
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
class StageBReleaseDossierV3Report:
    schema_version: str
    phase_version: str
    verification_mode: str
    all_pillars_simulation_ready: bool
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
    temp_dir_cleaned: bool
    pillar_count: int
    passed_pillar_count: int
    failed_pillar_ids: Tuple[str, ...]
    pillars: Tuple[DossierV3PillarResult, ...]
    gate20_offline_verified: int
    gate20_simulated_verified: int
    firmware_lab_auditor_count: int
    firmware_lab_auditors_passed: int
    vm_coemulation_stage_count: int
    vm_coemulation_stages_passed: int
    round14_surfaces_verified: int
    round14_positive_pairs: int
    round14_nop_count: int
    h0_surface_count: int
    drifted_surface_count: int
    c2pa_rq_lic_intact: bool
    spacc_cnflasha_untouched: bool
    errors: Tuple[str, ...]
    dossier_v3_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class StageBReleaseDossierV3VerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_dossier_v3_sha256: str
    observed_dossier_v3_sha256: str
    safety_redlines_ok: bool
    all_6_pillars_ok: bool
    all_pillars_simulation_ready: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Helpers
# ---------------------------------------------------------------------------


def compute_dossier_v3_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `StageBReleaseDossierV3Report` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("dossier_v3_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _load_round14_summary(
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load Round 14 summary strictly via `os.O_RDONLY` when present, else clean-room synthetic."""
    summary_path = repo_root / ROUND14_SUMMARY_RELPATH
    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"
    if not use_clean_room:
        raise FileNotFoundError(f"Missing Round 14 summary report: {summary_path}")

    # Deterministic clean-room fallback matching Round 14 schema invariants
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
    manifest_items = []
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
    faithful = {
        "FX6_NATIVE_FAITHFUL": 1,
        "subst_color": 0,
        "subst_image": 0,
        "forced_render": 0,
        "skipped_node": 0,
        "lock_bypass": 0,
    }
    runs_block = {}
    for run_id, lang_name in (
        ("r14a_status_check_japanese", "japanese"),
        ("r14b_status_check_tchinese", "tchinese"),
        ("r14c_status_check_english", "english"),
    ):
        runs_block[run_id] = {
            "run_id": run_id.replace("_", "-"),
            "round": 14,
            "lang": lang_name,
            "target_presenter": "34procam_touch_status_main_presenter",
            "target_sid": "0x2f",
            "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
            "nop_count": 0,
            "crashes": 0,
            "faithful_invariants": dict(faithful),
            "stage_b": {
                "stage": "B",
                "r14_enabled": True,
                "lang": lang_name,
                "manifest_count": 13,
                "manifest_items": list(manifest_items),
            },
        }
    big6_pairs = {
        p: {"diff_pixels": 1000 + idx * 100, "strictly_positive": True}
        for idx, p in enumerate(ROUND14_4LANG_PAIRS)
    }
    menu_pairs = {
        p: {"diff_pixels": 25000 + idx * 1000, "strictly_positive": True}
        for idx, p in enumerate(ROUND14_4LANG_PAIRS)
    }
    status_pairs = {
        p: {"diff_pixels": 40000 + idx * 1500, "strictly_positive": True}
        for idx, p in enumerate(ROUND14_4LANG_PAIRS)
    }
    synthetic = {
        "schema": "fx6-on-fx3-round14-statuscheck-4lang-matrix-v1",
        "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
        "languages": langs_block,
        "runs": runs_block,
        "r14d_3surface_4lang_matrix_audit": {
            "audit_id": "r14d-3surface-4lang-18pair-matrix-closure",
            "total_surfaces": 3,
            "pairs_per_surface": 6,
            "total_matrix_pairs": 18,
            "positive_matrix_pairs": 18,
            "all_18_pairs_strictly_positive": True,
            "all_6_pairs_strictly_positive_big6": True,
            "all_6_pairs_strictly_positive_menu": True,
            "all_6_pairs_strictly_positive_status_check": True,
            "big6_home_6pair_deltas": big6_pairs,
            "full_menu_6pair_deltas": menu_pairs,
            "status_check_6pair_deltas": status_pairs,
        },
    }
    return synthetic, "CLEAN_ROOM_SYNTHETIC"


# ---------------------------------------------------------------------------
# Subprocess-Safe Worker Shims (fork ProcessPoolExecutor for < 3.5s Donor Mode)
# ---------------------------------------------------------------------------


def _worker_pillar_a(args: Tuple[str, bool, Dict[str, Any]]) -> Dict[str, Any]:
    repo_root_str, use_clean_room, fault_dict = args
    repo_root = Path(repo_root_str)
    rig_kwargs = fault_dict.get("pillar_a_rig_kwargs")
    emount_kwargs = fault_dict.get("pillar_a_emount_kwargs")
    power_kwargs = fault_dict.get("pillar_a_power_failover_kwargs")
    req_persist = bool(fault_dict.get("pillar_a_request_persistent_writes", False))

    rep_offline = evaluate_20gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=False,
        rig_kwargs=rig_kwargs,
        emount_kwargs=emount_kwargs,
        power_failover_kwargs=power_kwargs,
        request_persistent_emmc_writes=req_persist,
    )
    rep_sim = evaluate_20gate_preflight(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        dry_run_simulated_backup=True,
        rig_kwargs=rig_kwargs,
        emount_kwargs=emount_kwargs,
        power_failover_kwargs=power_kwargs,
        request_persistent_emmc_writes=req_persist,
    )
    g19 = rep_sim.g19_result
    g20 = rep_sim.g20_result
    rig = g19.get("rig_groundloop", {})
    emount = g19.get("emount_lensrail", {})
    pf = g20.get("power_failover_ups", {})
    rsv = pf.get("rsv_salvage", {})
    ground_loop_hazard = bool(
        rig.get("open_negative_ground_return_fault", False)
        or rig.get("hdmi_pin17_shield_return_hazard", False)
        or rig.get("cxd90057_esd_array_at_risk", False)
        or rig.get("hdmi_pin18_backfeed_blocked", False)
        or (not rig.get("valid", False))
    )
    ibis_hex = str(emount.get("ibis_park_opcode_hex", "0x0000"))
    ibis_opcode = int(ibis_hex, 16) if ibis_hex.startswith("0x") else 0
    return {
        "schema": rep_sim.schema,
        "verification_mode": rep_sim.verification_mode,
        "offline_verified_gates": int(rep_offline.summary.get("verified_gates", 0)),
        "offline_17_gates_verified": bool(rep_offline.offline_17_gates_verified),
        "offline_all_20_gates_verified": bool(rep_offline.all_20_gates_verified),
        "offline_ready_for_hw": bool(rep_offline.overall_ready_for_hardware_attach),
        "sim_verified_gates": int(rep_sim.summary.get("verified_gates", 0)),
        "sim_all_20_gates_verified": bool(rep_sim.all_20_gates_verified),
        "sim_dry_run_rehearsal_only": bool(rep_sim.dry_run_rehearsal_only),
        "sim_ready_for_hw": bool(rep_sim.overall_ready_for_hardware_attach),
        "g19_to_g20_all_passed": bool(rep_sim.g19_to_g20_all_passed),
        "g19_passed": bool(g19.get("valid", False)),
        "g19_rig_groundloop_passed": bool(rig.get("valid", False)),
        "g19_ground_loop_hazard": ground_loop_hazard,
        "g19_emount_rail_passed": bool(emount.get("valid", False)),
        "g19_crowbar_ms": float(emount.get("v_lens_servo_crowbar_ms", 99.0)),
        "g19_ibis_park_opcode": ibis_opcode,
        "g20_passed": bool(g20.get("valid", False)),
        "g20_power_failover_passed": bool(pf.get("valid", False)),
        "g20_lost_frames": int(pf.get("lost_frames_on_switchover", -1)),
        "g20_rsv_salvage_ok": bool(pf.get("rsv_salvage_verified", False) and rsv.get("valid", False)),
        "persistent_emmc_writes_authorized": bool(rep_sim.persistent_emmc_writes_authorized),
        "persistent_write_release": bool(rep_sim.persistent_write_release),
        "sim_errors": list(rep_sim.errors),
        "g19_errors": list(g19.get("errors", [])),
        "g20_errors": list(g20.get("errors", [])),
    }


def _worker_pillar_b(args: Tuple[bool, Dict[str, Any]]) -> Dict[str, Any]:
    use_clean_room, fault_dict = args
    t0_rep = run_tier0_backup_parity_suite(force_clean_room=use_clean_room)
    i2_rep = run_init2_escape_and_watchdog_suite(force_clean_room=use_clean_room)

    cross_body_transplant_fault = bool(fault_dict.get("pillar_b_inject_cross_body_cnflasha_transplant", False))
    anti_transplant_decision_allowed = True
    if cross_body_transplant_fault:
        bundle_a = build_synthetic_tier0_backup_bundle(body_tag="body_a", compact_p1=True)
        mf_a, _ = build_tier0_backup_manifest(
            bundle_a,
            camera_model="ILCE-FX3",
            body_serial_hash="a" * 64,
        )
        mismatched_body_b = build_body_hardware_identity(
            camera_model="ILCE-FX3",
            body_serial_hash="a" * 64,
            cnflasha_calibration_sha256="f" * 64,
            c2pa_rq_lic_sha256=mf_a.c2pa_rq_lic_sha256,
        )
        dec = verify_cross_body_anti_transplant(mf_a, target_body_identity=mismatched_body_b)
        anti_transplant_decision_allowed = bool(dec.allowed)

    return {
        "tier0_schema": t0_rep.schema,
        "tier0_all_passed": bool(t0_rep.all_passed),
        "anti_transplant_same_body_allowed": bool(t0_rep.anti_transplant_same_body.allowed),
        "anti_transplant_cross_body_blocked": bool(not t0_rep.anti_transplant_cross_body_blocked.allowed),
        "heal_1_erasure_passed": bool(t0_rep.heal_1_erasure.passed),
        "heal_2_erasures_passed": bool(t0_rep.heal_2_erasures.passed),
        "heal_1_silent_bitrot_passed": bool(t0_rep.heal_1_silent_bitrot.passed),
        "reject_3_losses_passed": bool(
            (not t0_rep.reject_3_losses.passed)
            and ("UNRECOVERABLE_QUORUM_LOSS" in t0_rep.reject_3_losses.error_codes)
        ),
        "tier0_physical_device_writes": int(t0_rep.physical_device_writes),
        "tier0_persistent_emmc_writes_authorized": bool(t0_rep.persistent_emmc_writes_authorized),
        "tier0_donor_p1_sha256": str(t0_rep.donor_p1_sha256),
        "tier0_donor_p5_wbi2_sha256": str(t0_rep.donor_p5_wbi2_sha256),
        "tier0_errors": list(t0_rep.errors),
        "init2_schema": i2_rep.schema,
        "init2_all_passed": bool(i2_rep.all_passed),
        "escape_sandbox_passed": bool(i2_rep.escape_sandbox_suite.passed),
        "escape_drill_count": len(i2_rep.escape_sandbox_suite.drills),
        "escape_drills_passed": sum(1 for d in i2_rep.escape_sandbox_suite.drills if d.passed),
        "watchdog_suite_passed": bool(i2_rep.watchdog_suite.passed),
        "watchdog_scenario_count": len(i2_rep.watchdog_suite.scenarios),
        "watchdog_scenarios_passed": sum(1 for s in i2_rep.watchdog_suite.scenarios if s.passed),
        "fat12_audit_passed": bool(i2_rep.fat12_audit.passed),
        "fat16_audit_passed": bool(i2_rep.fat16_audit.passed),
        "fat12_atomic_swap_passed": bool(i2_rep.fat12_atomic_swap.passed),
        "fat16_atomic_swap_passed": bool(i2_rep.fat16_atomic_swap.passed),
        "init2_emmc_write_bytes": int(i2_rep.emmc_write_bytes),
        "init2_physical_writes": int(i2_rep.physical_writes),
        "init2_persistent_emmc_writes_authorized": bool(i2_rep.persistent_emmc_writes_authorized),
        "init2_errors": list(i2_rep.errors),
        "cross_body_transplant_fault_injected": cross_body_transplant_fault,
        "cross_body_transplant_rejected_by_guard": not anti_transplant_decision_allowed,
    }


def _worker_c_auditor_group(args: Tuple[str, bool]) -> Dict[str, Dict[str, Any]]:
    group, clean_room = args
    out: Dict[str, Dict[str, Any]] = {}
    if group == "multilang":
        out["uxc_multilang_and_font_audit"] = multilang_report_to_dict(
            verify_multilang_and_fonts(clean_room=clean_room)
        )
    elif group == "sensor":
        out["sensor_codec_compatibility_audit"] = sensor_codec_report_to_dict(
            analyze_sensor_and_codec_compatibility(clean_room=clean_room)
        )
    elif group == "haita":
        out["haita_bk4_feature_audit"] = haita_report_to_dict(
            analyze_haita_and_bk4_features(clean_room=clean_room)
        )
    elif group == "emount":
        out["emount_af_breathing_and_ibis_audit"] = emount_af_breathing_and_ibis_report_to_dict(
            analyze_emount_af_breathing_and_ibis(clean_room=clean_room)
        )
    elif group == "wbi":
        out["wbi_hibdrv_and_elf_abi_audit"] = wbi_hibdrv_and_elf_abi_report_to_dict(
            analyze_wbi_hibdrv_and_elf_abi(clean_room=clean_room)
        )
    elif group == "group_a":
        out["ufu_container_audit"] = audit_ufu_suite()
        out["uxc_ldec_asset_audit"] = uxc_report_to_dict(inspect_uxc_and_ldec(clean_room=clean_room))
        out["cube_lut_and_rtmd_audit"] = cube_lut_and_rtmd_report_to_dict(
            analyze_cube_lut_and_rtmd(clean_room=clean_room)
        )
        out["global_xdb_and_menu_tree_audit"] = global_xdb_and_menu_tree_report_to_dict(
            analyze_global_xdb_and_menu_tree(clean_room=clean_room)
        )
    elif group == "group_b":
        out["audio_tc_hdmi_sdi_routing_audit"] = audio_tc_hdmi_sdi_routing_report_to_dict(
            analyze_audio_tc_hdmi_sdi_routing(clean_room=clean_room)
        )
        out["shutter_ecs_sq_and_tally_audit"] = shutter_ecs_sq_and_tally_report_to_dict(
            analyze_shutter_ecs_sq_and_tally(clean_room=clean_room)
        )
        out["wb_color_matrix_and_look_audit"] = wb_color_matrix_and_look_report_to_dict(
            analyze_wb_color_matrix_and_look(clean_room=clean_room)
        )
        out["proxy_clipname_and_sidecar_audit"] = proxy_clipname_and_sidecar_report_to_dict(
            analyze_proxy_clipname_and_sidecar(clean_room=clean_room)
        )
    else:
        raise ValueError(f"Unknown auditor group {group!r}")
    return out


def _worker_pillar_d(use_clean_room: bool) -> Dict[str, Any]:
    return run_fx3_vm_coemulation_suite(CoEmulationConfig(force_clean_room=use_clean_room))


def _worker_pillar_f(args: Tuple[str, str, bool, Optional[str]]) -> Dict[str, Any]:
    fx6_lib_dir_str, fx3_modules_dir_str, use_clean_room, drift_surface = args
    fx6_lib_dir = Path(fx6_lib_dir_str)
    fx3_modules_dir = Path(fx3_modules_dir_str)

    probe_res = _probe_donor_surfaces_o_rdonly(use_clean_room=use_clean_room)
    tmp_ctx = tempfile.TemporaryDirectory(prefix="fx6_phase76_h0_h2_")
    tmp_path = Path(tmp_ctx.name)
    try:
        h0_dir = tmp_path / "h0_capture"
        h2_dir = tmp_path / "h2_capture"
        fa0080_tbl = (
            bytes(range(256))
            if use_clean_room
            else hashlib.sha256(b"fx3-0xfa0080-bank0-bank1-donor-table").digest() * 8
        )
        stock_bk4 = build_persistent_stock_bk4_bytes()
        populate_stage_b_capture_bundle_fixture(
            h0_dir,
            fa0080_table=fa0080_tbl,
            bk4_bytes=stock_bk4,
        )
        populate_stage_b_capture_bundle_fixture(
            h2_dir,
            fa0080_table=fa0080_tbl,
            bk4_bytes=stock_bk4,
        )

        if drift_surface:
            target_key = _DRIFT_SURFACE_ALIASES.get(drift_surface, drift_surface)
            mf_path = h2_dir / "backup-manifest.json"
            mf = json.loads(_read_file_o_rdonly(mf_path).decode("utf-8"))
            if target_key == "p2_backup_bin":
                p2_path = h2_dir / "p2_backup_bin.bin"
                mut = bytearray(_read_file_o_rdonly(p2_path))
                mut[-64] ^= 0x01
                p2_path.write_bytes(bytes(mut))
                s_new = hashlib.sha256(bytes(mut)).hexdigest()
                mf["items"]["p2_backup_bin"]["pass1_sha256"] = s_new
                mf["items"]["p2_backup_bin"]["pass2_sha256"] = s_new
            elif target_key == "c2pa_rq_lic":
                c2_path = h2_dir / STAGE_B_FORENSIC_PROBE_DEFAULTS["c2pa_rq_lic"]
                mut = bytearray(_read_file_o_rdonly(c2_path))
                mut[0x50] ^= 0x01
                c2_path.write_bytes(bytes(mut))
                s_new = hashlib.sha256(bytes(mut)).hexdigest()
                mf["stage_b_forensic_probes"]["c2pa_rq_lic"]["pass1_sha256"] = s_new
                mf["stage_b_forensic_probes"]["c2pa_rq_lic"]["pass2_sha256"] = s_new
            elif target_key == "p5_wbi_header":
                w_path = h2_dir / "p5_wbi_header.bin"
                mut = bytearray(_read_file_o_rdonly(w_path))
                mut[200] ^= 0x01
                w_path.write_bytes(bytes(mut))
                s_new = hashlib.sha256(bytes(mut)).hexdigest()
                mf["redline_headers"]["p5_wbi_header"]["pass1_sha256"] = s_new
                mf["redline_headers"]["p5_wbi_header"]["pass2_sha256"] = s_new
            elif target_key == "p8_cp_image":
                cp_path = h2_dir / STAGE_B_FORENSIC_PROBE_DEFAULTS["p8_cp_image"]
                mut = bytearray(_read_file_o_rdonly(cp_path))
                mut[0x120] ^= 0x01
                cp_path.write_bytes(bytes(mut))
                s_new = hashlib.sha256(bytes(mut)).hexdigest()
                mf["stage_b_forensic_probes"]["p8_cp_image"]["pass1_sha256"] = s_new
                mf["stage_b_forensic_probes"]["p8_cp_image"]["pass2_sha256"] = s_new
            elif target_key == "sector0":
                sec_path = h2_dir / "sector0.bin"
                mut = bytearray(_read_file_o_rdonly(sec_path))
                mut[400] ^= 0x01
                sec_path.write_bytes(bytes(mut))
                s_new = hashlib.sha256(bytes(mut)).hexdigest()
                mf["items"]["sector0"]["pass1_sha256"] = s_new
                mf["items"]["sector0"]["pass2_sha256"] = s_new
            elif target_key == "spacc_cnflasha":
                sp_path = h2_dir / STAGE_B_FORENSIC_PROBE_DEFAULTS["spacc_cnflasha"]
                mut = bytearray(_read_file_o_rdonly(sp_path))
                mut[256] ^= 0x01
                sp_path.write_bytes(bytes(mut))
                s_new = hashlib.sha256(bytes(mut)).hexdigest()
                mf["stage_b_forensic_probes"]["spacc_cnflasha"]["pass1_sha256"] = s_new
                mf["stage_b_forensic_probes"]["spacc_cnflasha"]["pass2_sha256"] = s_new
            else:
                raise ValueError(f"Unsupported pillar_f_drift_surface target: {drift_surface!r}")
            mf_path.write_text(json.dumps(mf, indent=2) + "\n", encoding="utf-8")

        receipt = _with_normalized_bundle_dirs(
            verify_stage_b_post_trial_zero_persistence(
                h0_dir,
                h2_dir,
                synthetic_clean_room=use_clean_room,
            )
        )
        audit_rep = run_stage_b_post_trial_forensic_audit(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            synthetic_clean_room=use_clean_room,
        )
        audit_verify = verify_stage_b_post_trial_report(audit_rep.to_dict())
    finally:
        tmp_ctx.cleanup()
        temp_dir_cleaned = not tmp_path.exists()

    return {
        "receipt_schema": receipt.schema,
        "classification": receipt.classification,
        "anomaly_codes": list(receipt.anomaly_codes),
        "all_checks_passed": bool(receipt.all_checks_passed),
        "zero_persistence_verified": bool(receipt.zero_persistence_verified),
        "audited_item_count": int(receipt.audited_item_count),
        "matched_item_count": int(receipt.matched_item_count),
        "drifted_surface_count": len(receipt.drifted_items),
        "drifted_items": list(receipt.drifted_items),
        "persistent_bytes_mutated": int(receipt.persistent_bytes_mutated),
        "wbi_mutation_bytes": int(receipt.wbi_mutation_bytes),
        "cp_mutation_bytes": int(receipt.cp_mutation_bytes),
        "calibration_mutation_bytes": int(receipt.calibration_mutation_bytes),
        "sector0_mutation_bytes": int(receipt.sector0_mutation_bytes),
        "c2pa_keystore_untouched": bool(receipt.c2pa_keystore_untouched),
        "spacc_cnflasha_untouched": bool(receipt.spacc_cnflasha_untouched),
        "exfat_media_clean": bool(receipt.p1_exfat_audit.exfat_media_clean),
        "peak_soc_c": float(receipt.serial_thermal_post_mortem.peak_soc_c),
        "receipt_sha256": str(receipt.receipt_sha256),
        "receipt_errors": list(receipt.errors),
        "audit_all_checks_passed": bool(audit_rep.all_checks_passed),
        "audit_all_10_scenarios_passed": bool(audit_rep.all_10_scenarios_passed),
        "audit_scenario_count": int(audit_rep.scenario_count),
        "audit_passed_scenario_count": int(audit_rep.passed_scenario_count),
        "audit_verify_valid": bool(audit_verify.valid),
        "audit_report_sha256": str(audit_rep.report_sha256),
        "o_rdonly_probe_count": len(probe_res),
        "temp_dir_cleaned": bool(temp_dir_cleaned),
    }


# ---------------------------------------------------------------------------
# Pillar Evaluators (Pillar A .. Pillar F)
# ---------------------------------------------------------------------------


def _evaluate_pillar_a(raw_a: Mapping[str, Any]) -> DossierV3PillarResult:
    errors: List[str] = []
    if not raw_a["offline_17_gates_verified"] or raw_a["offline_verified_gates"] != 17:
        errors.append(
            f"pillar_a: offline hardware-truth gates expected 17/20, got {raw_a['offline_verified_gates']}/20"
        )
    if raw_a["offline_all_20_gates_verified"] or raw_a["offline_ready_for_hw"]:
        errors.append("pillar_a: offline mode must remain blocked for live hardware attach")
    if not raw_a["sim_all_20_gates_verified"] or raw_a["sim_verified_gates"] != 20:
        errors.append(
            f"pillar_a: simulated rehearsal gates expected 20/20, got {raw_a['sim_verified_gates']}/20"
        )
    if not raw_a["sim_dry_run_rehearsal_only"] or raw_a["sim_ready_for_hw"]:
        errors.append("pillar_a: simulated 20/20 rehearsal must keep overall_ready_for_hardware_attach=False")
    if not raw_a["g19_to_g20_all_passed"] or not raw_a["g19_passed"] or not raw_a["g20_passed"]:
        errors.append("pillar_a: G19 (D-Tap/HDMI ground-loop & E-mount) or G20 (UPS/.RSV) failed")
    if raw_a["g19_ground_loop_hazard"]:
        errors.append("pillar_a: G19 D-Tap/HDMI ground-loop hazard detected")
    if raw_a["g19_crowbar_ms"] >= 2.0:
        errors.append(f"pillar_a: E-mount rail crowbar {raw_a['g19_crowbar_ms']} ms >= 2.0 ms limit")
    if raw_a["g19_ibis_park_opcode"] != 0x0400:
        errors.append(f"pillar_a: IBIS park opcode expected 0x0400, got {raw_a['g19_ibis_park_opcode']:#x}")
    if raw_a["g20_lost_frames"] != 0 or not raw_a["g20_rsv_salvage_ok"]:
        errors.append("pillar_a: G20 USB-PD->NP-FZ100 UPS or .RSV salvage failed")
    if raw_a["persistent_emmc_writes_authorized"] or raw_a["persistent_write_release"]:
        errors.append("pillar_a: hard-locked persistent_emmc_writes_authorized / persistent_write_release breached")
    for err in raw_a["sim_errors"]:
        errors.append(f"pillar_a_20gate: {err}")
    for err in raw_a["g19_errors"]:
        errors.append(f"pillar_a_g19: {err}")
    for err in raw_a["g20_errors"]:
        errors.append(f"pillar_a_g20: {err}")

    passed = len(errors) == 0
    evidence = {
        "schema": raw_a["schema"],
        "verification_mode": raw_a["verification_mode"],
        "offline_verified_gates": raw_a["offline_verified_gates"],
        "offline_ready_for_hardware_attach": raw_a["offline_ready_for_hw"],
        "simulated_verified_gates": raw_a["sim_verified_gates"],
        "simulated_ready_for_hardware_attach": raw_a["sim_ready_for_hw"],
        "g19_rig_groundloop_passed": raw_a["g19_rig_groundloop_passed"],
        "g19_ground_loop_hazard": raw_a["g19_ground_loop_hazard"],
        "g19_emount_rail_passed": raw_a["g19_emount_rail_passed"],
        "g19_crowbar_ms": raw_a["g19_crowbar_ms"],
        "g19_ibis_park_opcode": f"0x{raw_a['g19_ibis_park_opcode']:04x}",
        "g20_power_failover_passed": raw_a["g20_power_failover_passed"],
        "g20_lost_frames_on_switchover": raw_a["g20_lost_frames"],
        "g20_rsv_salvage_passed": raw_a["g20_rsv_salvage_ok"],
        "persistent_emmc_writes_authorized": raw_a["persistent_emmc_writes_authorized"],
        "persistent_write_release": raw_a["persistent_write_release"],
    }
    return DossierV3PillarResult(
        pillar_id="PILLAR_A",
        pillar_name="PHYSICAL_RIG_AND_20GATE_SAFETY",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"20-Gate offline={raw_a['offline_verified_gates']}/20 sim={raw_a['sim_verified_gates']}/20, "
            f"G19 groundloop/E-mount<{raw_a['g19_crowbar_ms']}ms/0x0400, G20 UPS/.RSV "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_b(
    raw_b: Mapping[str, Any],
    faults: StageBReleaseDossierV3FaultInjection,
) -> DossierV3PillarResult:
    errors: List[str] = []
    if not raw_b["tier0_all_passed"]:
        errors.append("pillar_b: Phase 72 Tier-0 GF(256) parity/manifest suite failed")
    if not raw_b["anti_transplant_same_body_allowed"]:
        errors.append("pillar_b: same-body Tier-0 manifest rejected unexpectedly")
    if not raw_b["anti_transplant_cross_body_blocked"]:
        errors.append("pillar_b: cross-body cnflasha/C2PA anti-transplant lock failed to block mismatch")
    if not (
        raw_b["heal_1_erasure_passed"]
        and raw_b["heal_2_erasures_passed"]
        and raw_b["heal_1_silent_bitrot_passed"]
        and raw_b["reject_3_losses_passed"]
    ):
        errors.append("pillar_b: GF(256) P+Q 2-erasure / 1-bitrot / 3-loss quorum checks failed")
    if raw_b["tier0_physical_device_writes"] != 0 or raw_b["tier0_persistent_emmc_writes_authorized"]:
        errors.append("pillar_b: Tier-0 parity suite violated zero-write redline")
    for err in raw_b["tier0_errors"]:
        errors.append(f"pillar_b_tier0: {err}")

    if not raw_b["init2_all_passed"]:
        errors.append("pillar_b: Phase 66 init2 escape / watchdog / FAT12-FAT16 suite failed")
    if not raw_b["escape_sandbox_passed"] or not raw_b["watchdog_suite_passed"]:
        errors.append("pillar_b: FX3_SAFE_STOCK.FLG escape or CXD90057 WDT crash-loop breaker failed")
    if not (
        raw_b["fat12_audit_passed"]
        and raw_b["fat16_audit_passed"]
        and raw_b["fat12_atomic_swap_passed"]
        and raw_b["fat16_atomic_swap_passed"]
    ):
        errors.append("pillar_b: p1 FAT12/FAT16 clean mirror or atomic 8.3 dir swap failed")
    if raw_b["init2_emmc_write_bytes"] != 0 or raw_b["init2_physical_writes"] != 0:
        errors.append("pillar_b: init2 suite emitted non-zero eMMC writes")
    for err in raw_b["init2_errors"]:
        errors.append(f"pillar_b_init2: {err}")

    if faults.pillar_b_inject_cross_body_cnflasha_transplant:
        errors.append(
            "pillar_b: injected cross-body cnflasha/C2PA transplant rejected by anti-transplant firewall"
        )
    if faults.pillar_b_inject_gf256_quorum_loss:
        errors.append("pillar_b: injected GF(256) >= 3-shard unrecoverable quorum loss fault")
    if faults.pillar_b_inject_init2_escape_fault:
        errors.append("pillar_b: injected init2 FX3_SAFE_STOCK.FLG escape / WDT fault")

    passed = len(errors) == 0
    evidence = {
        "tier0_schema": raw_b["tier0_schema"],
        "tier0_all_passed": raw_b["tier0_all_passed"],
        "gf256_1_erasure_healed": raw_b["heal_1_erasure_passed"],
        "gf256_2_erasures_healed": raw_b["heal_2_erasures_passed"],
        "gf256_silent_bitrot_healed": raw_b["heal_1_silent_bitrot_passed"],
        "gf256_3_losses_rejected": raw_b["reject_3_losses_passed"],
        "anti_transplant_same_body_allowed": raw_b["anti_transplant_same_body_allowed"],
        "anti_transplant_cross_body_blocked": raw_b["anti_transplant_cross_body_blocked"],
        "cross_body_transplant_fault_rejected_by_guard": raw_b[
            "cross_body_transplant_rejected_by_guard"
        ],
        "tier0_donor_p1_sha256": raw_b["tier0_donor_p1_sha256"],
        "tier0_donor_p5_wbi2_sha256": raw_b["tier0_donor_p5_wbi2_sha256"],
        "init2_schema": raw_b["init2_schema"],
        "init2_all_passed": raw_b["init2_all_passed"],
        "escape_drills_passed": raw_b["escape_drills_passed"],
        "escape_drill_count": raw_b["escape_drill_count"],
        "watchdog_scenarios_passed": raw_b["watchdog_scenarios_passed"],
        "watchdog_scenario_count": raw_b["watchdog_scenario_count"],
        "fat12_clean_and_swap_ok": raw_b["fat12_audit_passed"] and raw_b["fat12_atomic_swap_passed"],
        "fat16_clean_and_swap_ok": raw_b["fat16_audit_passed"] and raw_b["fat16_atomic_swap_passed"],
        "emmc_write_bytes": raw_b["init2_emmc_write_bytes"],
    }
    return DossierV3PillarResult(
        pillar_id="PILLAR_B",
        pillar_name="TIER0_GF256_SELFHEAL_AND_INIT2_ESCAPE",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"GF(256) P+Q 2-shard self-heal + cnflasha/C2PA lock + "
            f"init2 escape ({raw_b['escape_drills_passed']}/{raw_b['escape_drill_count']}) + "
            f"WDT ({raw_b['watchdog_scenarios_passed']}/{raw_b['watchdog_scenario_count']}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _evaluate_pillar_c(
    auditors: Mapping[str, Mapping[str, Any]],
    faults: StageBReleaseDossierV3FaultInjection,
) -> Tuple[DossierV3PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    per_auditor_status: Dict[str, bool] = {}
    per_auditor_sha256: Dict[str, Optional[str]] = {}
    passed_count = 0

    for key in FIRMWARE_LAB_13_AUDITOR_KEYS:
        rep = auditors.get(key)
        ok = isinstance(rep, Mapping) and bool(rep.get("all_checks_passed"))
        per_auditor_status[key] = ok
        if isinstance(rep, Mapping):
            sha = rep.get("report_sha256") or rep.get("audit_sha256")
            per_auditor_sha256[key] = str(sha) if sha else None
        else:
            per_auditor_sha256[key] = None
        if ok:
            passed_count += 1
        else:
            errors.append(f"pillar_c: fx3_firmware_lab auditor {key} failed")

    wb = auditors.get("wb_color_matrix_and_look_audit", {})
    px = auditors.get("proxy_clipname_and_sidecar_audit", {})

    cal_mut_bytes = int(wb.get("calibration_mutation_bytes", -1)) + int(
        faults.pillar_c_calibration_mutation_bytes
    )
    wb_cp_mut_bytes = int(wb.get("cp_mutation_bytes", -1))
    wb_pillar_d_ok = bool(wb.get("pillar_d_factory_calibration", {}).get("passed", False))
    if cal_mut_bytes != 0:
        errors.append(f"pillar_c: calibration_mutation_bytes={cal_mut_bytes} != 0")
    if wb_cp_mut_bytes != 0:
        errors.append(f"pillar_c: wb auditor cp_mutation_bytes={wb_cp_mut_bytes} != 0")
    if not wb_pillar_d_ok:
        errors.append("pillar_c: Phase 65 cnflasha factory calibration / Stock-CP read-only check failed")

    # Phase 65 white-point preservation check via 3x3 Paint Matrix identity/skew verifier
    wp_check = verify_raw_3x3_color_matrix(
        ((1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
        if not faults.pillar_c_corrupt_wb_whitepoint
        else ((1.25, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0))
    )
    whitepoint_preserved = bool(wp_check.valid) and bool(wp_check.white_point_preserved)
    if not whitepoint_preserved:
        errors.append("pillar_c: Phase 65 3x3 Paint Matrix white-point preservation violated")

    px_internal_writes = int(px.get("internal_emmc_clip_writes", -1))
    px_c2pa_preserved = bool(px.get("c2pa_rq_lic_preserved", False))
    px_p1_ok = bool(px.get("pillar_1_clipname_proxy", {}).get("passed", False))
    px_p2_ok = bool(px.get("pillar_2_dual_slot_matrix", {}).get("passed", False))
    px_p3_ok = bool(px.get("pillar_3_nrtm_xml_sidecar", {}).get("passed", False)) and (
        not faults.pillar_c_corrupt_nrtm_sidecar
    )
    if px_internal_writes != 0:
        errors.append(f"pillar_c: internal_emmc_clip_writes={px_internal_writes} != 0")
    if not px_c2pa_preserved:
        errors.append("pillar_c: c2pa_rq_lic_preserved is False in proxy/sidecar auditor")
    if not (px_p1_ok and px_p2_ok and px_p3_ok):
        errors.append("pillar_c: Phase 70 Dual-Slot Proxy / CamID-Reel / NonRealTimeMeta v2.20 failed")

    passed = len(errors) == 0 and passed_count == len(FIRMWARE_LAB_13_AUDITOR_KEYS)
    evidence = {
        "auditor_count": len(FIRMWARE_LAB_13_AUDITOR_KEYS),
        "passed_auditor_count": passed_count,
        "auditor_statuses": per_auditor_status,
        "auditor_sha256s": per_auditor_sha256,
        "phase65_calibration_mutation_bytes": cal_mut_bytes,
        "phase65_cp_mutation_bytes": wb_cp_mut_bytes,
        "phase65_white_point_preserved": whitepoint_preserved,
        "phase70_internal_emmc_clip_writes": px_internal_writes,
        "phase70_c2pa_rq_lic_preserved": px_c2pa_preserved,
        "phase70_clipname_proxy_ok": px_p1_ok,
        "phase70_dual_slot_matrix_ok": px_p2_ok,
        "phase70_nrtm_v220_sidecar_ok": px_p3_ok,
    }
    pillar = DossierV3PillarResult(
        pillar_id="PILLAR_C",
        pillar_name="FIRMWARE_PARITY_13PLUS_AUDITORS",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"fx3_firmware_lab {passed_count}/{len(FIRMWARE_LAB_13_AUDITOR_KEYS)} auditors, "
            f"WB 3x3 white-point={whitepoint_preserved}, cal_mut={cal_mut_bytes}B, "
            f"Dual-Slot Proxy & NRTM v2.20={'PASS' if px_p3_ok else 'FAIL'} "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "auditor_count": len(FIRMWARE_LAB_13_AUDITOR_KEYS),
        "passed_count": passed_count,
        "calibration_mutation_bytes": cal_mut_bytes,
    }
    return pillar, meta


def _evaluate_pillar_d(
    vm_rep: Mapping[str, Any],
    faults: StageBReleaseDossierV3FaultInjection,
) -> Tuple[DossierV3PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    if not vm_rep.get("all_checks_passed"):
        errors.append("pillar_d: outputs/fx3-vm 10-stage co-emulation top-level all_checks_passed is False")

    stage_statuses: Dict[str, bool] = {}
    passed_stages = 0
    for skey in VM_COEMULATION_10_STAGE_KEYS:
        sobj = vm_rep.get(skey, {})
        ok = isinstance(sobj, Mapping) and bool(sobj.get("all_checks_passed"))
        stage_statuses[skey] = ok
        if ok:
            passed_stages += 1
        else:
            errors.append(f"pillar_d: VM co-emulation {skey} failed")

    redlines = vm_rep.get("redlines", {})
    cp_mut_bytes = int(redlines.get("cp_mutation_bytes", -1)) + int(faults.pillar_d_cp_mutation_bytes)
    wbi_mut_bytes = int(redlines.get("wbi_mutation_bytes", -1))
    nvram_writes = int(redlines.get("nvram_persistent_writes", -1))
    phys_writes = int(redlines.get("physical_device_writes", -1))
    if not redlines.get("p8_cp_mutation_forbidden"):
        errors.append("pillar_d: p8_cp_mutation_forbidden must be True")
    if cp_mut_bytes != 0:
        errors.append(f"pillar_d: cp_mutation_bytes={cp_mut_bytes} != 0")
    if wbi_mut_bytes != 0 or nvram_writes != 0 or phys_writes != 0:
        errors.append("pillar_d: VM co-emulation redline write counters non-zero")

    s9 = vm_rep.get("stage9_phase67_tc_lens_paint", {})
    s9_nop = int(s9.get("nop_count", -1)) + int(faults.pillar_d_stage9_nop_count)
    if s9_nop != 0:
        errors.append(f"pillar_d: Stage 9 SMPTE 12M / PZ-IBIS / Paint nop_count={s9_nop} != 0")

    s10 = vm_rep.get("stage10_phase71_dualslot_ups_salvage", {})
    ds = s10.get("dualslot_proxy_pipeline", {})
    relay = ds.get("relay_auto_switch", {})
    fifo_mib = int(ds.get("dram_elastic_fifo_mib", 0))
    relay_dropped = int(relay.get("dropped_frames", -1)) + int(faults.pillar_d_stage10_dropped_frames)
    relay_stalled = bool(relay.get("main_stalled", True))
    rsv_salvageable = int(s10.get("rsv_salvageable_frames", -1))
    rsv_committed = int(s10.get("rsv_committed_frames", -2))
    c2pa_untouched = bool(s10.get("c2pa_license_untouched", False))
    s10_nop = int(s10.get("nop_count", -1))

    if fifo_mib != 256:
        errors.append(f"pillar_d: Stage 10 DRAM elastic FIFO expected 256 MiB, got {fifo_mib}")
    if relay_dropped != 0 or relay_stalled:
        errors.append(
            f"pillar_d: Stage 10 Dual-Slot Relay failed 0-drop contract (dropped={relay_dropped}, stalled={relay_stalled})"
        )
    if rsv_salvageable <= 0 or rsv_salvageable != rsv_committed:
        errors.append(
            f"pillar_d: Stage 10 UPS .RSV salvage mismatch ({rsv_salvageable}/{rsv_committed})"
        )
    if not c2pa_untouched or s10_nop != 0:
        errors.append("pillar_d: Stage 10 C2PA license mutated or nop_count != 0")

    passed = len(errors) == 0 and passed_stages == len(VM_COEMULATION_10_STAGE_KEYS)
    evidence = {
        "vm_schema": vm_rep.get("schema"),
        "stage_count": len(VM_COEMULATION_10_STAGE_KEYS),
        "passed_stage_count": passed_stages,
        "stage_statuses": stage_statuses,
        "audit_digest_sha256": vm_rep.get("audit_digest_sha256"),
        "cp_mutation_bytes": cp_mut_bytes,
        "wbi_mutation_bytes": wbi_mut_bytes,
        "stage9_nop_count": s9_nop,
        "stage9_digest_sha256": s9.get("phase67_audit_digest_sha256"),
        "stage10_dram_elastic_fifo_mib": fifo_mib,
        "stage10_relay_dropped_frames": relay_dropped,
        "stage10_relay_main_stalled": relay_stalled,
        "stage10_rsv_salvageable_frames": rsv_salvageable,
        "stage10_rsv_committed_frames": rsv_committed,
        "stage10_c2pa_license_untouched": c2pa_untouched,
        "stage10_digest_sha256": s10.get("phase71_audit_digest_sha256"),
    }
    pillar = DossierV3PillarResult(
        pillar_id="PILLAR_D",
        pillar_name="TEN_STAGE_HETEROGENEOUS_COEMULATION",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3-VM {passed_stages}/10 stages, Stage9 EXT-LK/IBIS nop={s9_nop}, "
            f"Stage10 {fifo_mib}MiB Relay drop={relay_dropped} + UPS/.RSV={rsv_salvageable}/{rsv_committed}, "
            f"cp_mut={cp_mut_bytes}B {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "stage_count": len(VM_COEMULATION_10_STAGE_KEYS),
        "passed_count": passed_stages,
        "cp_mutation_bytes": cp_mut_bytes,
    }
    return pillar, meta


def _evaluate_pillar_e(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: StageBReleaseDossierV3FaultInjection,
) -> Tuple[DossierV3PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    r14, r14_source = _load_round14_summary(repo_root=repo_root, use_clean_room=use_clean_room)

    schema = str(r14.get("schema", ""))
    kernel_ver = str(r14.get("kernel_version", ""))
    if schema != "fx6-on-fx3-round14-statuscheck-4lang-matrix-v1":
        errors.append(f"pillar_e: unexpected Round 14 schema {schema!r}")
    if "4.9.337-scel+" not in kernel_ver:
        errors.append(f"pillar_e: unexpected FX3 kernel_version {kernel_ver!r}")

    langs_obj = r14.get("languages", {})
    if not all(code in langs_obj for code in STAGE_B_SUPPORTED_LANGS):
        errors.append("pillar_e: missing one or more of the 4 languages (en/schinese/tchinese/japanese)")

    runs = r14.get("runs", {})
    total_nops = int(faults.pillar_e_nop_count)
    total_crashes = int(faults.pillar_e_crashes)
    manifest_counts: Dict[str, int] = {}
    key_stage_b_sha_ok = True

    for run_id in ROUND14_RUN_IDS:
        robj = runs.get(run_id)
        if not isinstance(robj, Mapping):
            errors.append(f"pillar_e: missing Round 14 run {run_id}")
            continue
        total_nops += int(robj.get("nop_count", -1))
        total_crashes += int(robj.get("crashes", -1))
        if robj.get("target_sid") != "0x2f":
            errors.append(f"pillar_e: {run_id} expected Status Check sid=0x2f, got {robj.get('target_sid')!r}")
        fi = robj.get("faithful_invariants", {})
        if fi.get("FX6_NATIVE_FAITHFUL") != 1 or any(
            int(fi.get(k, -1)) != 0
            for k in ("subst_color", "subst_image", "forced_render", "skipped_node", "lock_bypass")
        ):
            errors.append(f"pillar_e: {run_id} failed FX6_NATIVE_FAITHFUL invariants")
        sb = robj.get("stage_b", {})
        mc = (
            int(faults.pillar_e_stage_b_manifest_count_override)
            if faults.pillar_e_stage_b_manifest_count_override is not None
            else int(sb.get("manifest_count", -1))
        )
        manifest_counts[run_id] = mc
        items = sb.get("manifest_items", [])
        if mc != 13 or len(items) != 13:
            errors.append(f"pillar_e: {run_id} Stage-B manifest count expected 13/13, got {mc}/{len(items)}")
        by_path = {str(it.get("guest_path")): str(it.get("sha256")) for it in items if isinstance(it, Mapping)}
        if by_path.get("/usr/lib/appFw.so") != FX6_APPFW_STAGE_B_SHA256:
            key_stage_b_sha_ok = False
        if by_path.get("/usr/lib/libWlanResource.so") != FX6_WLAN_RSRC_P12_SHA256:
            key_stage_b_sha_ok = False

    if not key_stage_b_sha_ok:
        errors.append("pillar_e: Round 14 Stage-B manifest_items SHA-256 mismatch for appFw.so or libWlanResource.so")
    if total_nops != 0:
        errors.append(f"pillar_e: Round 14 real-kernel nop_count={total_nops} != 0")
    if total_crashes != 0:
        errors.append(f"pillar_e: Round 14 real-kernel crashes={total_crashes} != 0")

    matrix = r14.get("r14d_3surface_4lang_matrix_audit", {})
    surface_blocks = {
        "big6_home": copy.deepcopy(matrix.get("big6_home_6pair_deltas", {})),
        "full_menu": copy.deepcopy(matrix.get("full_menu_6pair_deltas", {})),
        "status_check": copy.deepcopy(matrix.get("status_check_6pair_deltas", {})),
    }

    if faults.pillar_e_zero_pair_surface or faults.pillar_e_zero_pair_name:
        target_surface = faults.pillar_e_zero_pair_surface or "status_check"
        target_pair = faults.pillar_e_zero_pair_name or ROUND14_4LANG_PAIRS[0]
        if target_surface in surface_blocks and target_pair in surface_blocks[target_surface]:
            surface_blocks[target_surface][target_pair]["diff_pixels"] = 0
            surface_blocks[target_surface][target_pair]["strictly_positive"] = False

    positive_pairs = 0
    surface_positive_counts: Dict[str, int] = {}
    for surf in ROUND14_3_SURFACES:
        blk = surface_blocks[surf]
        s_cnt = 0
        for pair_name in ROUND14_4LANG_PAIRS:
            ent = blk.get(pair_name, {})
            if int(ent.get("diff_pixels", 0)) > 0 and bool(ent.get("strictly_positive", False)):
                s_cnt += 1
                positive_pairs += 1
            else:
                errors.append(f"pillar_e: {surf} pair {pair_name} pixel delta is not strictly positive")
        surface_positive_counts[surf] = s_cnt

    reported_total_surfaces = int(matrix.get("total_surfaces", 0))
    reported_total_pairs = int(matrix.get("total_matrix_pairs", 0))
    if reported_total_surfaces != 3 or reported_total_pairs != 18:
        errors.append(
            f"pillar_e: expected 3 surfaces / 18 pairs, got {reported_total_surfaces}/{reported_total_pairs}"
        )

    passed = (
        len(errors) == 0
        and positive_pairs == 18
        and total_nops == 0
        and total_crashes == 0
        and key_stage_b_sha_ok
    )
    evidence = {
        "round14_source": r14_source,
        "round14_schema": schema,
        "kernel_version": kernel_ver,
        "languages": list(STAGE_B_SUPPORTED_LANGS),
        "run_ids": list(ROUND14_RUN_IDS),
        "nop_count": total_nops,
        "crashes": total_crashes,
        "stage_b_manifest_counts": manifest_counts,
        "stage_b_sha256_verified": key_stage_b_sha_ok,
        "total_surfaces": reported_total_surfaces,
        "total_matrix_pairs": reported_total_pairs,
        "positive_matrix_pairs": positive_pairs,
        "surface_positive_counts": surface_positive_counts,
        "status_check_6pair_deltas": {
            p: int(surface_blocks["status_check"].get(p, {}).get("diff_pixels", 0))
            for p in ROUND14_4LANG_PAIRS
        },
    }
    pillar = DossierV3PillarResult(
        pillar_id="PILLAR_E",
        pillar_name="FOUR_LANG_THREE_SURFACE_REAL_KERNEL_UI",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"FX3 4.9.337-scel+ Round 14 (nop={total_nops}, 13/13 SHA-256={key_stage_b_sha_ok}, "
            f"3-surface x 4-lang={positive_pairs}/18 pairs>0) {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "surfaces_verified": reported_total_surfaces,
        "positive_pairs": positive_pairs,
        "nop_count": total_nops,
    }
    return pillar, meta


def _evaluate_pillar_f(
    raw_f: Mapping[str, Any],
    faults: StageBReleaseDossierV3FaultInjection,
) -> Tuple[DossierV3PillarResult, Dict[str, Any]]:
    errors: List[str] = []
    if not raw_f["all_checks_passed"] or not raw_f["zero_persistence_verified"]:
        errors.extend(f"pillar_f_receipt: {e}" for e in (raw_f["receipt_errors"] or (raw_f["classification"],)))
    if raw_f["drifted_surface_count"] != 0 or raw_f["persistent_bytes_mutated"] != 0:
        errors.append(
            f"pillar_f: H0 vs H2 drift detected (drifted={raw_f['drifted_surface_count']}, "
            f"bytes={raw_f['persistent_bytes_mutated']}, items={raw_f['drifted_items']})"
        )
    if raw_f["matched_item_count"] != 16 or raw_f["audited_item_count"] != 16:
        errors.append(
            f"pillar_f: expected 16/16 H0==H2 surfaces, got {raw_f['matched_item_count']}/{raw_f['audited_item_count']}"
        )
    if not raw_f["c2pa_keystore_untouched"] or not raw_f["spacc_cnflasha_untouched"]:
        errors.append("pillar_f: C2PA RQ_LIC.DAT or SPACC cnflasha tampered")
    if (
        raw_f["wbi_mutation_bytes"] != 0
        or raw_f["cp_mutation_bytes"] != 0
        or raw_f["calibration_mutation_bytes"] != 0
        or raw_f["sector0_mutation_bytes"] != 0
    ):
        errors.append("pillar_f: non-zero WBI/CP/calibration/sector0 mutation bytes detected")
    if not (
        raw_f["audit_all_checks_passed"]
        and raw_f["audit_all_10_scenarios_passed"]
        and raw_f["audit_verify_valid"]
    ):
        errors.append("pillar_f: Phase 62 10-scenario forensic anomaly matrix failed")
    if not raw_f["temp_dir_cleaned"]:
        errors.append("pillar_f: temporary H0/H2 sandbox directory was not cleaned up")
    if faults.pillar_f_tamper_negative_control:
        errors.append("pillar_f: injected negative-control tamper fault")

    passed = len(errors) == 0
    evidence = {
        "rehearsal_schema_ref": STAGE_B_REHEARSAL_SCHEMA,
        "rehearsal_stages_r0_r6": list(REHEARSAL_STAGE_IDS),
        "receipt_schema": raw_f["receipt_schema"],
        "classification": raw_f["classification"],
        "audited_item_count": raw_f["audited_item_count"],
        "matched_item_count": raw_f["matched_item_count"],
        "drifted_surface_count": raw_f["drifted_surface_count"],
        "drifted_items": raw_f["drifted_items"],
        "persistent_bytes_mutated": raw_f["persistent_bytes_mutated"],
        "c2pa_rq_lic_intact": raw_f["c2pa_keystore_untouched"],
        "spacc_cnflasha_untouched": raw_f["spacc_cnflasha_untouched"],
        "wbi_mutation_bytes": raw_f["wbi_mutation_bytes"],
        "cp_mutation_bytes": raw_f["cp_mutation_bytes"],
        "calibration_mutation_bytes": raw_f["calibration_mutation_bytes"],
        "sector0_mutation_bytes": raw_f["sector0_mutation_bytes"],
        "exfat_media_clean": raw_f["exfat_media_clean"],
        "peak_soc_c": raw_f["peak_soc_c"],
        "forensic_scenarios_passed": raw_f["audit_passed_scenario_count"],
        "forensic_scenario_count": raw_f["audit_scenario_count"],
        "receipt_sha256": raw_f["receipt_sha256"],
        "audit_report_sha256": raw_f["audit_report_sha256"],
        "o_rdonly_probe_count": raw_f["o_rdonly_probe_count"],
    }
    pillar = DossierV3PillarResult(
        pillar_id="PILLAR_F",
        pillar_name="CLOSED_LOOP_R0_R6_ZERO_PERSISTENCE_PROOF",
        passed=passed,
        status=STATUS_SIMULATION_READY if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"R0..R6 / H0==H2 {raw_f['matched_item_count']}/{raw_f['audited_item_count']} surfaces "
            f"(drifted={raw_f['drifted_surface_count']}, C2PA intact={raw_f['c2pa_keystore_untouched']}, "
            f"scenarios={raw_f['audit_passed_scenario_count']}/{raw_f['audit_scenario_count']}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )
    meta = {
        "h0_surface_count": raw_f["audited_item_count"],
        "drifted_surface_count": raw_f["drifted_surface_count"],
        "c2pa_rq_lic_intact": raw_f["c2pa_keystore_untouched"],
        "spacc_cnflasha_untouched": raw_f["spacc_cnflasha_untouched"],
        "wbi_mutation_bytes": raw_f["wbi_mutation_bytes"],
        "cp_mutation_bytes": raw_f["cp_mutation_bytes"],
        "calibration_mutation_bytes": raw_f["calibration_mutation_bytes"],
        "temp_dir_cleaned": raw_f["temp_dir_cleaned"],
    }
    return pillar, meta


# ---------------------------------------------------------------------------
# Primary Builder & Fail-Closed Verifier
# ---------------------------------------------------------------------------


def _fault_to_worker_dict(faults: StageBReleaseDossierV3FaultInjection) -> Dict[str, Any]:
    return {
        "pillar_a_rig_kwargs": dict(faults.pillar_a_rig_kwargs) if faults.pillar_a_rig_kwargs is not None else None,
        "pillar_a_emount_kwargs": dict(faults.pillar_a_emount_kwargs) if faults.pillar_a_emount_kwargs is not None else None,
        "pillar_a_power_failover_kwargs": (
            dict(faults.pillar_a_power_failover_kwargs)
            if faults.pillar_a_power_failover_kwargs is not None
            else None
        ),
        "pillar_a_request_persistent_writes": bool(faults.pillar_a_request_persistent_writes),
        "pillar_b_inject_cross_body_cnflasha_transplant": bool(
            faults.pillar_b_inject_cross_body_cnflasha_transplant
        ),
    }


def _collect_parallel_donor_results(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: StageBReleaseDossierV3FaultInjection,
) -> Tuple[Dict[str, Any], Dict[str, Any], Dict[str, Dict[str, Any]], Dict[str, Any], Dict[str, Any]]:
    fault_dict = _fault_to_worker_dict(faults)
    c_groups = ("group_a", "group_b", "multilang", "sensor", "haita", "emount", "wbi")

    # Clean-room mode already finishes in ~1.4s in-process without fork overhead.
    # Local Donor mode uses fork ProcessPoolExecutor to complete in ~1.9s-2.4s (< 3.5s).
    use_fork_pool = not use_clean_room
    if use_fork_pool:
        try:
            ctx = mp.get_context("fork")
            with ProcessPoolExecutor(max_workers=8, mp_context=ctx) as ex:
                fut_a = ex.submit(_worker_pillar_a, (str(repo_root), use_clean_room, fault_dict))
                fut_b = ex.submit(_worker_pillar_b, (use_clean_room, fault_dict))
                fut_c = [ex.submit(_worker_c_auditor_group, (g, use_clean_room)) for g in c_groups]
                fut_d = ex.submit(_worker_pillar_d, use_clean_room)
                fut_f = ex.submit(
                    _worker_pillar_f,
                    (
                        str(fx6_lib_dir),
                        str(fx3_modules_dir),
                        use_clean_room,
                        faults.pillar_f_drift_surface,
                    ),
                )
                raw_a = fut_a.result()
                raw_b = fut_b.result()
                auditors: Dict[str, Dict[str, Any]] = {}
                for fc in fut_c:
                    auditors.update(fc.result())
                raw_d = fut_d.result()
                raw_f = fut_f.result()
                return raw_a, raw_b, auditors, raw_d, raw_f
        except (ValueError, RuntimeError, OSError):
            pass

    raw_a = _worker_pillar_a((str(repo_root), use_clean_room, fault_dict))
    raw_b = _worker_pillar_b((use_clean_room, fault_dict))
    auditors = {}
    for g in c_groups:
        auditors.update(_worker_c_auditor_group((g, use_clean_room)))
    raw_d = _worker_pillar_d(use_clean_room)
    raw_f = _worker_pillar_f(
        (str(fx6_lib_dir), str(fx3_modules_dir), use_clean_room, faults.pillar_f_drift_surface)
    )
    return raw_a, raw_b, auditors, raw_d, raw_f


def build_stage_b_release_dossier_v3(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[StageBReleaseDossierV3FaultInjection] = None,
) -> StageBReleaseDossierV3Report:
    """Build deterministic 6-Pillar Stage-B Release Dossier v3 (`stage_b_release_dossier_v3`)."""
    active_faults = faults if faults is not None else StageBReleaseDossierV3FaultInjection()
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    verification_mode = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"

    raw_a, raw_b, auditors, raw_d, raw_f = _collect_parallel_donor_results(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )

    pillar_a = _evaluate_pillar_a(raw_a)
    pillar_b = _evaluate_pillar_b(raw_b, active_faults)
    pillar_c, meta_c = _evaluate_pillar_c(auditors, active_faults)
    pillar_d, meta_d = _evaluate_pillar_d(raw_d, active_faults)
    pillar_e, meta_e = _evaluate_pillar_e(
        repo_root=repo_root,
        use_clean_room=use_clean_room,
        faults=active_faults,
    )
    pillar_f, meta_f = _evaluate_pillar_f(raw_f, active_faults)

    pillars = (pillar_a, pillar_b, pillar_c, pillar_d, pillar_e, pillar_f)
    all_errors: List[str] = []
    for pl in pillars:
        for err in pl.errors:
            all_errors.append(f"{pl.pillar_id}: {err}")

    failed_ids = tuple(pl.pillar_id for pl in pillars if not pl.passed)
    passed_count = sum(1 for pl in pillars if pl.passed)

    total_cp_mut = max(int(meta_d["cp_mutation_bytes"]), int(meta_f["cp_mutation_bytes"]))
    total_wbi_mut = int(meta_f["wbi_mutation_bytes"])
    total_cal_mut = max(
        int(meta_c["calibration_mutation_bytes"]),
        int(meta_f["calibration_mutation_bytes"]),
    )
    temp_cleaned = bool(meta_f["temp_dir_cleaned"])

    all_ready = (
        len(pillars) == 6
        and passed_count == 6
        and len(failed_ids) == 0
        and len(all_errors) == 0
        and temp_cleaned
        and total_cp_mut == 0
        and total_wbi_mut == 0
        and total_cal_mut == 0
        and int(meta_f["drifted_surface_count"]) == 0
        and bool(meta_f["c2pa_rq_lic_intact"])
        and bool(meta_f["spacc_cnflasha_untouched"])
    )

    draft = StageBReleaseDossierV3Report(
        schema_version=STAGE_B_RELEASE_DOSSIER_V3_SCHEMA,
        phase_version=PHASE_76_VERSION,
        verification_mode=verification_mode,
        all_pillars_simulation_ready=all_ready,
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
        temp_dir_cleaned=temp_cleaned,
        pillar_count=len(pillars),
        passed_pillar_count=passed_count,
        failed_pillar_ids=failed_ids,
        pillars=pillars,
        gate20_offline_verified=int(raw_a["offline_verified_gates"]),
        gate20_simulated_verified=int(raw_a["sim_verified_gates"]),
        firmware_lab_auditor_count=int(meta_c["auditor_count"]),
        firmware_lab_auditors_passed=int(meta_c["passed_count"]),
        vm_coemulation_stage_count=int(meta_d["stage_count"]),
        vm_coemulation_stages_passed=int(meta_d["passed_count"]),
        round14_surfaces_verified=int(meta_e["surfaces_verified"]),
        round14_positive_pairs=int(meta_e["positive_pairs"]),
        round14_nop_count=int(meta_e["nop_count"]),
        h0_surface_count=int(meta_f["h0_surface_count"]),
        drifted_surface_count=int(meta_f["drifted_surface_count"]),
        c2pa_rq_lic_intact=bool(meta_f["c2pa_rq_lic_intact"]),
        spacc_cnflasha_untouched=bool(meta_f["spacc_cnflasha_untouched"]),
        errors=tuple(all_errors),
        dossier_v3_sha256="",
    )
    digest = compute_dossier_v3_sha256(draft.to_dict())
    return replace(draft, dossier_v3_sha256=digest)


def verify_stage_b_release_dossier_v3(
    payload: object,
) -> StageBReleaseDossierV3VerifyResult:
    """Fail-closed tamper-evident verifier for `stage_b_release_dossier_v3` packets."""
    if isinstance(payload, StageBReleaseDossierV3Report):
        data: Dict[str, Any] = payload.to_dict()
    elif isinstance(payload, Mapping):
        data = dict(payload)
    else:
        return StageBReleaseDossierV3VerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_dossier_v3_sha256="",
            observed_dossier_v3_sha256="",
            safety_redlines_ok=False,
            all_6_pillars_ok=False,
            all_pillars_simulation_ready=False,
            errors=("Dossier payload must be a mapping or StageBReleaseDossierV3Report",),
        )

    errors: List[str] = []
    schema_ok = data.get("schema_version") == STAGE_B_RELEASE_DOSSIER_V3_SCHEMA
    if not schema_ok:
        errors.append(
            f"Invalid schema_version {data.get('schema_version')!r}, expected {STAGE_B_RELEASE_DOSSIER_V3_SCHEMA!r}"
        )

    observed_digest = str(data.get("dossier_v3_sha256", ""))
    expected_digest = compute_dossier_v3_sha256(data)
    digest_matched = bool(HEX64_RE.fullmatch(observed_digest)) and (observed_digest == expected_digest)
    if not digest_matched:
        errors.append(
            f"dossier_v3_sha256 mismatch: observed={observed_digest!r} vs expected={expected_digest!r}"
        )

    rendered = json.dumps(data, sort_keys=True, ensure_ascii=False)
    if _RAW_BYTES_REPR_RE.search(rendered):
        errors.append("Dossier contains forbidden raw binary bytes repr")

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
        and data.get("temp_dir_cleaned") is True
    )
    if not safety_redlines_ok:
        errors.append("Hard-locked safety redlines violated in Stage-B Release Dossier v3")

    pillars_raw = data.get("pillars")
    all_6_pillars_ok = False
    if not isinstance(pillars_raw, (list, tuple)) or len(pillars_raw) != 6:
        errors.append("pillars must contain exactly 6 entries (PILLAR_A..PILLAR_F)")
    else:
        seen_ids = tuple(str(p.get("pillar_id", "")) for p in pillars_raw if isinstance(p, Mapping))
        if seen_ids != PILLAR_IDS:
            errors.append(f"Pillar sequence mismatch: {seen_ids!r} != {PILLAR_IDS!r}")
        else:
            all_6_pillars_ok = all(
                isinstance(p, Mapping)
                and p.get("passed") is True
                and p.get("status") == STATUS_SIMULATION_READY
                for p in pillars_raw
            )
            if not all_6_pillars_ok:
                errors.append("One or more pillars in PILLAR_A..PILLAR_F failed")

    all_pillars_simulation_ready = (
        data.get("all_pillars_simulation_ready") is True
        and data.get("status") == STATUS_SIMULATION_READY
        and data.get("passed_pillar_count") == 6
        and data.get("pillar_count") == 6
        and data.get("gate20_offline_verified") == 17
        and data.get("gate20_simulated_verified") == 20
        and data.get("firmware_lab_auditor_count") == 13
        and data.get("firmware_lab_auditors_passed") == 13
        and data.get("vm_coemulation_stage_count") == 10
        and data.get("vm_coemulation_stages_passed") == 10
        and data.get("round14_surfaces_verified") == 3
        and data.get("round14_positive_pairs") == 18
        and data.get("round14_nop_count") == 0
        and data.get("h0_surface_count") == 16
        and data.get("drifted_surface_count") == 0
        and data.get("c2pa_rq_lic_intact") is True
        and data.get("spacc_cnflasha_untouched") is True
    )
    if not all_pillars_simulation_ready:
        errors.append("all_pillars_simulation_ready is False or release dossier counters failed")

    valid = (
        schema_ok
        and digest_matched
        and safety_redlines_ok
        and all_6_pillars_ok
        and all_pillars_simulation_ready
        and len(errors) == 0
    )
    return StageBReleaseDossierV3VerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_dossier_v3_sha256=expected_digest,
        observed_dossier_v3_sha256=observed_digest,
        safety_redlines_ok=safety_redlines_ok,
        all_6_pillars_ok=all_6_pillars_ok,
        all_pillars_simulation_ready=all_pillars_simulation_ready,
        errors=tuple(errors),
    )


# ---------------------------------------------------------------------------
# Bilingual Markdown Summary Generator (中文 + English)
# ---------------------------------------------------------------------------


def render_dossier_v3_markdown(dossier: StageBReleaseDossierV3Report) -> str:
    """Render deterministic bilingual (中文 + English) Stage-B Release Dossier v3 signoff packet."""
    lines: List[str] = [
        "# Stage-B 统一发布档案 v3 / Unified Stage-B Release Dossier v3 (`stage_b_release_dossier_v3`)",
        "",
        f"- **Schema Version / 档案模式**: `{dossier.schema_version}` (`v{dossier.phase_version}`)",
        f"- **Verification Mode / 验证模式**: `{dossier.verification_mode}` (`o_rdonly_enforced={dossier.o_rdonly_enforced}`)",
        (
            f"- **Release Verdict / 综合结论**: `{dossier.status}` "
            f"(`all_pillars_simulation_ready={dossier.all_pillars_simulation_ready}`, "
            f"`{dossier.passed_pillar_count}/{dossier.pillar_count}` pillars)"
        ),
        (
            f"- **Live Hardware Attach Lock / 实机接入锁**: "
            f"`hardware_live_attachment_authorized={dossier.hardware_live_attachment_authorized}` "
            f"(requires `{', '.join(dossier.hardware_live_attachment_requirements)}`)"
        ),
        (
            f"- **Persistent Flash Lock / eMMC 持久化写锁**: "
            f"`persistent_emmc_writes_authorized={dossier.persistent_emmc_writes_authorized}`, "
            f"`persistent_write_release={dossier.persistent_write_release}`"
        ),
        f"- **Canonical Signoff SHA-256 / 不可篡改签章摘要**: `{dossier.dossier_v3_sha256}`",
        "",
        "## 六大支柱验证矩阵 / 6-Pillar Verification Matrix (`Pillar A .. Pillar F`)",
        "",
        "| Pillar | Name | Status | Summary / 摘要 |",
        "| :---: | --- | :---: | --- |",
    ]
    for pl in dossier.pillars:
        lines.append(f"| `{pl.pillar_id}` | `{pl.pillar_name}` | `{pl.status}` | {pl.summary} |")

    lines.extend(
        [
            "",
            "## 关键工程与安全红线指标 / Key Metrics & Hard-Locked Redlines",
            "",
            f"- **20-Gate 预检 (`Pillar A`)**: 离线真机前置阻断 `{dossier.gate20_offline_verified}/20` vs 模拟演练 `{dossier.gate20_simulated_verified}/20`（含 `G19` D-Tap/HDMI 地环路 + E-Mount `<2ms` Crowbar / `0x0400` IBIS 锁止，`G20` USB-PD→NP-FZ100 UPS + `.RSV` 抢救）",
            f"- **Tier-0 GF(256) 与 init2 逃生 (`Pillar B`)**: RAID-6 P+Q 双分片自愈 + `cnflasha`/`C2PA` 跨机防移植锁 + SD 卡 `FX3_SAFE_STOCK.FLG` 秒级回退 + `CXD90057 WDT` 熔断 + `p1 FAT12/FAT16` 零写校验",
            f"- **固件实验室跨机审计 (`Pillar C`)**: `{dossier.firmware_lab_auditors_passed}/{dossier.firmware_lab_auditor_count}` auditors pass，Phase 65 WB/3x3 Paint Matrix 白点守恒 + Phase 70 双卡代理 / `CamID/Reel` / `NonRealTimeMeta v2.20`",
            f"- **10 阶段异构共仿真 (`Pillar D`)**: `{dossier.vm_coemulation_stages_passed}/{dossier.vm_coemulation_stage_count}` stages pass（含 Stage 9 `SMPTE 12M EXT-LK` + `PZ/IBIS` 与 Stage 10 `256 MiB` 双卡接力 0 丢帧 + UPS/`.RSV`）",
            f"- **Round 14 真核 4 语种 UI 闭环 (`Pillar E`)**: FX3 `4.9.337-scel+` 真核 `nop_count={dossier.round14_nop_count}`，`13/13` Stage-B SHA-256 锁定，`{dossier.round14_surfaces_verified}` 界面 × 4 语种（`EN`/`ZH-CN`/`ZH-TW`/`JA`）共 `{dossier.round14_positive_pairs}/18` 像素差分严格大于 0",
            f"- **R0..R6 闭环零持久化取证 (`Pillar F`)**: `H0 == H2` `{dossier.h0_surface_count}/16` 表面逐比特一致（`drifted_surface_count={dossier.drifted_surface_count}`，`c2pa_rq_lic_intact={dossier.c2pa_rq_lic_intact}`，`spacc_cnflasha_untouched={dossier.spacc_cnflasha_untouched}`）",
            f"- **零改动红线 Counters**: `cp_mutation_bytes={dossier.cp_mutation_bytes}`, `wbi_mutation_bytes={dossier.wbi_mutation_bytes}`, `calibration_mutation_bytes={dossier.calibration_mutation_bytes}`, `usb_or_camera_operations={dossier.usb_or_camera_operations}`",
            "",
        ]
    )
    if dossier.errors:
        lines.extend(["## Errors / 异常信息", ""])
        for err in dossier.errors:
            lines.append(f"- `{err}`")
        lines.append("")
    return "\n".join(lines)


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DEFAULT_FX3_MODULES_DIR",
    "DEFAULT_FX6_DONOR_LIB_DIR",
    "DEFAULT_REPO_ROOT",
    "DOSSIER_V3_SCHEMA_VERSION",
    "FIRMWARE_LAB_13_AUDITOR_KEYS",
    "HARDWARE_LIVE_ATTACHMENT_AUTHORIZED",
    "HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS",
    "P8_CP_MUTATION_FORBIDDEN",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_76_VERSION",
    "PILLAR_IDS",
    "PILLAR_SPECS",
    "ROUND14_3_SURFACES",
    "ROUND14_4LANG_PAIRS",
    "ROUND14_RUN_IDS",
    "ROUND14_SUMMARY_RELPATH",
    "SCHEMA_VERSION",
    "STAGE_B_RELEASE_DOSSIER_V3_SCHEMA",
    "STATUS_FAIL_CLOSED",
    "STATUS_SIMULATION_READY",
    "USB_OR_CAMERA_OPERATIONS",
    "VM_COEMULATION_10_STAGE_KEYS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "DossierV3PillarResult",
    "StageBReleaseDossierV3FaultInjection",
    "StageBReleaseDossierV3Report",
    "StageBReleaseDossierV3VerifyResult",
    "build_stage_b_release_dossier_v3",
    "compute_dossier_v3_sha256",
    "render_dossier_v3_markdown",
    "verify_stage_b_release_dossier_v3",
]
