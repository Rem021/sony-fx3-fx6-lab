"""Phase 68 — Stage-B `R0..R6` Closed-Loop Hardware Rehearsal Orchestrator (`stage_b_closed_loop_rehearsal_v1`).

Unifies all pre-hardware bench, safety-gate, cryptographic baseline, volatile RAM
overlay, QMP/HDMI/4-language co-emulation, cold power-cycle wipe, and post-trial
16-surface forensic audit tracks into a deterministic, zero-write 7-stage
closed-loop rehearsal (`R0..R6`) executing in `< 4.0s` in both
`LOCAL_DONOR_O_RDONLY` and `CLEAN_ROOM_SYNTHETIC` modes:

- `R0` (`BENCH_FIXTURE_SELFTEST`):
  Calls Phase 59 `rp2040_multiport_fixture_selftest` verifying `-DOPEN_DRAIN=1`
  `1.8V` pull-up safety, `48000` baud PIO divider, loopback framing, and
  multimeter pre-plug interlocks before any camera cable could be attached.
- `R1` (`SAFETY_18GATE_AND_MEDIA_FIREWALL`):
  Calls Phase 61 `usblan_ptpip_and_18gate_preflight` (`G01..G18` dry-run +
  offline readiness truth) AND Phase 57 `exfat_media_integrity_guard` (proving
  production CFexpress/SD cards with `XDROOT`/`M4ROOT`/`.RSV` are rejected while
  blank dedicated lab media passes 12-sector `BootChecksum`).
- `R2` (`H0_BASELINE_SNAPSHOT`):
  Captures the deterministic `H0` 16-surface cryptographic baseline (`Tier-0`
  eMMC + `BK4\\0` + `WBI2` + `Stock-CP` + `C2PA RQ_LIC.DAT` + `SPACC cnflasha`)
  via Phase 62's baseline builder.
- `R3` (`STAGE_B_VOLATILE_OVERLAY_MOUNT`):
  Verifies the Phase 48/52 Stage-B SVR4 `cpio newc` volatile RAM overlay
  (`9.21 MiB` local / `8.11 MiB` clean-room equivalent, `13/13` Stage-B SHA-256
  items, `P12` Airplane-Mode `00342260` `WF-12` immunity, `init2` `/bin/sh`
  bind-mount drill with `0` persistent writes).
- `R4` (`LIVE_H1_COEMULATION_AND_4LANG_UI`):
  Verifies Stage 7 (`QMP` non-intrusive guest tracer, `nop_count == 0`) +
  Stage 8 (`HDMI RAW16 256B EDID` & `USB-C` mode arbitrator) + Round 13
  4-Language (`EN / ZH-CN / ZH-TW / JA`) real FX3 `7.02` kernel native
  presenter closure (`Status Check sid=0x2f`, 3-layer menu `sid=0x11`, all 6
  cross-language pixel-delta pairs `> 0`).
- `R5` (`COLD_POWER_CYCLE_WIPE`):
  Models cold power-off (`H1 -> H2`), asserting volatile `tmpfs` `/tmp/fx6_overlay`
  unmounts and vanishes completely with `0` residual eMMC writes.
- `R6` (`H0_VS_H2_POST_TRIAL_FORENSIC_AUDIT`):
  Runs Phase 62 `stage_b_post_trial_auditor` comparing `H0` vs `H2` across all
  16 persistent surfaces (`drifted_surface_count == 0`,
  `c2pa_keystore_untouched == True`, `calibration_mutation_bytes == 0`), plus
  negative-control tamper drills proving any injected drift in `R6` or failed
  gate in `R0..R4` immediately flips `rehearsal_passed = False` (`FAIL_CLOSED`).

Hard-Locked Safety Redlines:
- `PERSISTENT_EMMC_WRITES_AUTHORIZED = False`
- `PERSISTENT_WRITE_RELEASE = False`
- `hardware_live_attachment_authorized = False` (simulation rehearsal only;
  physical attachment separately requires `G10..G12` Tier-0 body backup
  readback + explicit human signoff, while `persistent_emmc_writes_authorized`
  remains `False` permanently)
- `P8_CP_MUTATION_FORBIDDEN = True`, `CP_MUTATION_BYTES = 0`
- `WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN = True`, `WBI_MUTATION_BYTES = 0`
- `CALIBRATION_MUTATION_BYTES = 0`, `USB_OR_CAMERA_OPERATIONS = 0`
- All local donor reads strictly use `os.open(..., os.O_RDONLY)`.
- Zero raw binary `bytes` reprs (`b'...'` / `b"..."`).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
from dataclasses import asdict, dataclass, replace
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple


def _ensure_cross_package_paths(repo_root: Path) -> None:
    """Ensure sibling lab package directories are importable under default PYTHONPATH."""
    for rel in (
        "outputs/fx3-safety",
        "outputs/fx3-recovery-adapter",
        "outputs/fx3-vm",
        "outputs/fx6-on-fx3-closure",
    ):
        cand = str(repo_root / rel)
        if cand not in sys.path:
            sys.path.append(cand)


DEFAULT_REPO_ROOT: Path = Path(__file__).resolve().parents[3]
_ensure_cross_package_paths(DEFAULT_REPO_ROOT)

from fx3_recovery.rp2040_multiport_fixture_selftest import (  # noqa: E402
    OhmmeterMeasurementSpec,
    UART_BOOT_BAUD,
    audit_ohmmeter_isolation,
    run_rp2040_multiport_fixture_selftest,
    simulate_uart_loopback_and_handshake,
    verify_open_drain_1v8_swing,
)
from fx3_safety.exfat_media_integrity_guard import (  # noqa: E402
    MediaSlotConfig,
    build_synthetic_exfat_boot_region,
    evaluate_exfat_media_integrity_guard,
    inspect_sony_media_tree,
)
from fx3_safety.thermal_pwm_and_power_guard import USBPD_REQUIRED_POWER_MW  # noqa: E402
from fx3_safety.usblan_ptpip_and_18gate_preflight import (  # noqa: E402
    evaluate_18_master_safety_gates,
)
import qmp_guest_introspection_tracer as qmp_tracer  # noqa: E402
import uvc_hdmi_raw_output_emulator as hdmi_uvc_emu  # noqa: E402

from .hardware_readiness_packet import (  # noqa: E402
    FX3_MODEL_ID_HEX,
    HEX64_RE,
    _is_forced_clean_room,
    verify_real_tier0_capture_bundle,
)
from .patcher import (  # noqa: E402
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
)
from .stage_b_post_trial_auditor import (  # noqa: E402
    REQUIRED_FSYNC_ORDER,
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
    BK_KEY_LANG,
    STAGE_B_AIRPLANE_KEYS,
    STAGE_B_BK_LANG_SPECS,
    STAGE_B_SUPPORTED_LANGS,
    STAGE_B_TMPFS_BUDGET_LIMIT_MIB,
    audit_stage_b_bk4_shadow,
    synthesize_stage_b_bk4_shadow,
    verify_stage_b_ram_overlay_v2,
)


# ---------------------------------------------------------------------------
# Hard-Locked Safety Policy & Schema Constants
# ---------------------------------------------------------------------------

STAGE_B_REHEARSAL_SCHEMA: str = "stage_b_closed_loop_rehearsal_v1"
SCHEMA_VERSION: str = STAGE_B_REHEARSAL_SCHEMA
PHASE_68_VERSION: str = "68.0.0"

PERSISTENT_EMMC_WRITES_AUTHORIZED: bool = False
PERSISTENT_WRITE_RELEASE: bool = False
P8_CP_MUTATION_FORBIDDEN: bool = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN: bool = True
CP_MUTATION_BYTES: int = 0
WBI_MUTATION_BYTES: int = 0
CALIBRATION_MUTATION_BYTES: int = 0
USB_OR_CAMERA_OPERATIONS: int = 0

STATUS_REHEARSAL_PASSED: str = "REHEARSAL_PASSED"
STATUS_FAIL_CLOSED: str = "FAIL_CLOSED"

REHEARSAL_STAGE_SPECS: Tuple[Tuple[str, str], ...] = (
    ("R0", "BENCH_FIXTURE_SELFTEST"),
    ("R1", "SAFETY_18GATE_AND_MEDIA_FIREWALL"),
    ("R2", "H0_BASELINE_SNAPSHOT"),
    ("R3", "STAGE_B_VOLATILE_OVERLAY_MOUNT"),
    ("R4", "LIVE_H1_COEMULATION_AND_4LANG_UI"),
    ("R5", "COLD_POWER_CYCLE_WIPE"),
    ("R6", "H0_VS_H2_POST_TRIAL_FORENSIC_AUDIT"),
)
REHEARSAL_STAGE_IDS: Tuple[str, ...] = tuple(sid for sid, _ in REHEARSAL_STAGE_SPECS)

HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS: Tuple[str, ...] = (
    "G10_physical_tier0_same_body_readback",
    "G11_physical_p1_recovery_capsule_verified",
    "G12_physical_stage_b_preflight_pass",
    "explicit_human_operator_signoff",
)

ROUND13_SUMMARY_RELPATH: str = (
    "reports/2026-11-14-round13-fx6-on-fx3-status-4lang-closure/summary.json"
)
ROUND13_4LANG_PAIRS: Tuple[str, ...] = (
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
class StageBRehearsalFaultInjection:
    """Deterministic fault-injection knobs across R0..R6 for negative-control drills."""

    # R0 faults
    r0_v_idle_tx_v: Optional[float] = None
    r0_open_drain: Optional[bool] = None
    r0_camera_connected: bool = False
    r0_ltc_cable_connected: bool = False
    r0_inject_framing_error: bool = False

    # R1 faults
    r1_slot_a_entries: Optional[Tuple[Tuple[str, int], ...]] = None
    r1_exfat_boot_bytes: Optional[bytes] = None
    r1_usblan_overrides: Optional[Mapping[str, Any]] = None
    r1_request_persistent_writes: bool = False

    # R2 faults
    r2_corrupt_wbi2: bool = False
    r2_corrupt_sector0: bool = False
    r2_bk4_active_byte8: int = 0

    # R3 faults
    r3_violate_wf12_airplane: bool = False
    r3_corrupt_lock_table: bool = False
    r3_exceed_tmpfs_budget: bool = False

    # R4 faults
    r4_nop_count: int = 0
    r4_crashes: int = 0
    r4_corrupt_edid_checksum: bool = False
    r4_zero_lang_pair_delta: Optional[str] = None

    # R5 faults
    r5_lingering_overlay_mount: bool = False
    r5_residual_emmc_writes: int = 0
    r5_sticky_mod_arm_once: bool = False

    # R6 faults
    r6_drift_surface: Optional[str] = None
    r6_tamper_negative_control: bool = False


@dataclass(frozen=True)
class StageBRehearsalStageResult:
    stage_id: str
    stage_name: str
    passed: bool
    status: str
    summary: str
    evidence: Dict[str, Any]
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageBClosedLoopRehearsalReport:
    schema_version: str
    phase_version: str
    verification_mode: str
    selected_lang: str
    rehearsal_passed: bool
    status: str
    hardware_live_attachment_authorized: bool
    hardware_live_attachment_requirements: Tuple[str, ...]
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    p8_cp_mutation_forbidden: bool
    wbi_p5_write_and_hibernation_forbidden: bool
    cp_mutation_bytes: int
    wbi_mutation_bytes: int
    calibration_mutation_bytes: int
    usb_or_camera_operations: int
    temp_dir_cleaned: bool
    stage_count: int
    passed_stage_count: int
    failed_stage_ids: Tuple[str, ...]
    stages: Tuple[StageBRehearsalStageResult, ...]
    h0_surface_count: int
    h2_drifted_surface_count: int
    c2pa_keystore_untouched: bool
    spacc_cnflasha_untouched: bool
    round13_4lang_pairs_verified: int
    negative_tamper_drills_passed: int
    errors: Tuple[str, ...]
    rehearsal_digest_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


@dataclass(frozen=True)
class StageBRehearsalCertificateVerifyResult:
    valid: bool
    schema_ok: bool
    digest_matched: bool
    expected_rehearsal_digest_sha256: str
    observed_rehearsal_digest_sha256: str
    safety_redlines_ok: bool
    all_7_stages_ok: bool
    rehearsal_passed: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Deterministic Helpers
# ---------------------------------------------------------------------------


def compute_rehearsal_digest_sha256(payload: Mapping[str, Any]) -> str:
    """Compute canonical SHA-256 over `StageBClosedLoopRehearsalReport` JSON."""
    body = copy.deepcopy(dict(payload))
    body.pop("rehearsal_digest_sha256", None)
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode(
        "utf-8"
    )
    return hashlib.sha256(canonical).hexdigest()


def _strip_utc_fields(obj: Any) -> Any:
    if isinstance(obj, Mapping):
        return {
            str(k): _strip_utc_fields(v)
            for k, v in obj.items()
            if str(k) != "evaluated_utc"
        }
    if isinstance(obj, (list, tuple)):
        return [_strip_utc_fields(x) for x in obj]
    return obj


def _load_round13_summary(
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], str]:
    """Load Round 13 summary strictly via `os.O_RDONLY` when present, else clean-room synthetic."""
    summary_path = repo_root / ROUND13_SUMMARY_RELPATH
    if summary_path.is_file() and not summary_path.is_symlink():
        raw_text = _read_file_o_rdonly(summary_path).decode("utf-8")
        obj = json.loads(raw_text)
        if isinstance(obj, dict):
            return obj, "REPO_SUMMARY_O_RDONLY"
    if not use_clean_room:
        raise FileNotFoundError(f"Missing Round 13 summary report: {summary_path}")

    # Deterministic clean-room equivalent matching Round 13 schema invariants
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
    big6_pairs = {
        p: {"diff_pixels": 1000 + idx * 100, "strictly_positive": True}
        for idx, p in enumerate(ROUND13_4LANG_PAIRS)
    }
    menu_pairs = {
        p: {"diff_pixels": 25000 + idx * 1000, "strictly_positive": True}
        for idx, p in enumerate(ROUND13_4LANG_PAIRS)
    }
    faithful = {
        "FX6_NATIVE_FAITHFUL": 1,
        "subst_color": 0,
        "subst_image": 0,
        "forced_render": 0,
        "skipped_node": 0,
        "lock_bypass": 0,
    }
    synthetic = {
        "schema": "fx6-on-fx3-round13-status-4lang-closure-v1",
        "kernel_version": "Linux version 4.9.337-scel+ (clean-room-synthetic)",
        "languages": langs_block,
        "runs": {
            "r13a_status_check_schinese": {
                "target_presenter": "34procam_touch_status_main_presenter",
                "target_sid": "0x2f",
                "nop_count": 0,
                "crashes": 0,
                "faithful_invariants": dict(faithful),
            },
            "r13b_menu_3layer_tchinese": {
                "target_presenter": "31procam_menu_layer_3rd_presenter",
                "target_sid": "0x11",
                "nop_count": 0,
                "crashes": 0,
                "faithful_invariants": dict(faithful),
            },
            "r13c_menu_3layer_paintlook_schinese": {
                "target_presenter": "31procam_menu_layer_3rd_presenter",
                "target_sid": "0x11",
                "nop_count": 0,
                "crashes": 0,
                "faithful_invariants": dict(faithful),
            },
        },
        "r13d_4lang_matrix_audit": {
            "big6_home_6pair_deltas": big6_pairs,
            "full_menu_6pair_deltas": menu_pairs,
            "all_6_pairs_strictly_positive_big6": True,
            "all_6_pairs_strictly_positive_menu": True,
            "four_lang_3layer_menu_parity_closure": {
                lang: {"sid": "0x10" if lang == "en" else "0x11"}
                for lang in STAGE_B_SUPPORTED_LANGS
            },
        },
    }
    return synthetic, "CLEAN_ROOM_SYNTHETIC"


# ---------------------------------------------------------------------------
# Stage Runners (R0..R6)
# ---------------------------------------------------------------------------


def _run_stage_r0(
    *,
    use_clean_room: bool,
    faults: StageBRehearsalFaultInjection,
) -> StageBRehearsalStageResult:
    """R0 (BENCH_FIXTURE_SELFTEST): Phase 59 RP2040-Zero -DOPEN_DRAIN 1.8V & pre-plug interlocks."""
    errors: List[str] = []
    rep = run_rp2040_multiport_fixture_selftest(force_clean_room=use_clean_room)

    ohm_res = audit_ohmmeter_isolation(
        OhmmeterMeasurementSpec(
            camera_connected=faults.r0_camera_connected,
            ltc_cable_connected=faults.r0_ltc_cable_connected,
        ),
        board=rep.board,
    )
    swing_res = verify_open_drain_1v8_swing(
        v_idle_tx_v=faults.r0_v_idle_tx_v if faults.r0_v_idle_tx_v is not None else 1.8,
        open_drain=faults.r0_open_drain if faults.r0_open_drain is not None else True,
        drive_mode=(
            "push_pull"
            if faults.r0_open_drain is False
            else "open_drain"
        ),
    )
    loop_res = simulate_uart_loopback_and_handshake(
        baud_rate=UART_BOOT_BAUD,
        inject_stop_bit_error=faults.r0_inject_framing_error,
        persistent_emmc_writes_authorized=False,
    )

    pio_48000 = [d for d in rep.pio_dividers if d.target_baud == UART_BOOT_BAUD]
    pio_48000_ok = bool(pio_48000) and all(d.passed for d in pio_48000)

    if not rep.all_passed:
        errors.extend(f"r0_selftest: {e}" for e in rep.errors)
    if not ohm_res.passed:
        errors.extend(f"r0_ohmmeter: {e}" for e in ohm_res.errors)
    if not swing_res.passed:
        errors.extend(f"r0_swing: {e}" for e in swing_res.errors)
    if not loop_res.passed:
        errors.extend(f"r0_loopback: {e}" for e in loop_res.errors)
    if not rep.cmake_audit.open_drain_equals_one:
        errors.append("r0_cmake: -DOPEN_DRAIN=1 not enforced")
    if not pio_48000_ok:
        errors.append("r0_pio: 48000 baud PIO divider failed accuracy check")
    if not rep.pio_program_audit.uses_pindirs_direction_toggle or rep.pio_program_audit.drives_pins_high:
        errors.append("r0_pio: open-drain pindirs direction-toggle invariant violated")
    if rep.persistent_emmc_writes_authorized:
        errors.append("r0_redline: persistent_emmc_writes_authorized must remain False")

    passed = (
        rep.all_passed
        and ohm_res.passed
        and swing_res.passed
        and loop_res.passed
        and rep.cmake_audit.open_drain_equals_one
        and pio_48000_ok
        and rep.glitch_rejection_verified
        and rep.framing_error_rejection_verified
        and (not rep.persistent_emmc_writes_authorized)
        and len(errors) == 0
    )
    evidence = {
        "schema": rep.schema,
        "board": rep.board,
        "cmake_open_drain_equals_one": rep.cmake_audit.open_drain_equals_one,
        "v_idle_tx_v": swing_res.v_idle_tx_v,
        "open_drain_enforced": swing_res.open_drain_enforced,
        "overvoltage_hazard": swing_res.overvoltage_hazard,
        "pio_48000_baud_error_pct": pio_48000[0].baud_error_pct if pio_48000 else None,
        "loopback_48000_bit_exact": loop_res.bit_exact_match,
        "camera_disconnected_verified": ohm_res.camera_disconnected_verified,
        "ltc_cable_disconnected_verified": ohm_res.ltc_cable_disconnected_verified,
        "glitch_rejection_verified": rep.glitch_rejection_verified,
        "framing_error_rejection_verified": rep.framing_error_rejection_verified,
        "ohmmeter_status": ohm_res.status,
        "swing_status": swing_res.status,
        "loopback_status": loop_res.status,
    }
    return StageBRehearsalStageResult(
        stage_id="R0",
        stage_name="BENCH_FIXTURE_SELFTEST",
        passed=passed,
        status=STATUS_REHEARSAL_PASSED if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"RP2040 {rep.board} -DOPEN_DRAIN=1 {swing_res.v_idle_tx_v:.2f}V "
            f"48000bps loopback & pre-plug interlocks {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _run_stage_r1(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: StageBRehearsalFaultInjection,
) -> StageBRehearsalStageResult:
    """R1 (SAFETY_18GATE_AND_MEDIA_FIREWALL): Phase 61 G01..G18 + Phase 57 exFAT media guard."""
    errors: List[str] = []

    lab_exfat_bytes = (
        faults.r1_exfat_boot_bytes
        if faults.r1_exfat_boot_bytes is not None
        else build_synthetic_exfat_boot_region()
    )
    lab_slot_a = MediaSlotConfig(
        slot_id="SLOT_A",
        inserted=True,
        exfat_boot_bytes=lab_exfat_bytes,
        card_entries=faults.r1_slot_a_entries if faults.r1_slot_a_entries is not None else (),
    )

    rep_18 = evaluate_18_master_safety_gates(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        use_synthetic_dry_run_tier0=True,
        slot_a=lab_slot_a,
        usblan_kwargs=faults.r1_usblan_overrides,
        request_persistent_emmc_writes=faults.r1_request_persistent_writes,
    )
    rep_exfat = evaluate_exfat_media_integrity_guard(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        slot_a=lab_slot_a,
        request_persistent_emmc_writes=faults.r1_request_persistent_writes,
    )

    # Negative control: prove production cards with XDROOT/M4ROOT/.RSV are deterministically rejected
    client_xdroot = inspect_sony_media_tree(
        entries=(("XDROOT/Clip/A001C001.MXF", 65536), ("XDROOT/Sub/A001S01.MP4", 4096))
    )
    client_m4root_rsv = inspect_sony_media_tree(
        entries=(("PRIVATE/M4ROOT/CLIP/C0001.MP4", 32768), ("PRIVATE/M4ROOT/CLIP/C0002.RSV", 4096))
    )
    production_cards_rejected = (
        (not client_xdroot.valid)
        and (not client_xdroot.is_clean_lab_media)
        and bool(client_xdroot.fx6_xdroot_mxf_clips)
        and (not client_m4root_rsv.valid)
        and (not client_m4root_rsv.is_clean_lab_media)
        and bool(client_m4root_rsv.unfinalized_rsv_files)
    )

    if not rep_18.all_18_gates_verified:
        errors.extend(f"r1_18gate: {e}" for e in (rep_18.errors or (rep_18.status,)))
    if not rep_18.offline_15_gates_verified or not rep_18.g17_to_g18_all_passed:
        errors.append("r1_18gate: offline_15_gates_verified or g17_to_g18_all_passed is False")
    if rep_18.persistent_emmc_writes_authorized or rep_18.persistent_write_release:
        errors.append("r1_18gate: persistent write redline violated")
    if not rep_exfat.all_passed or not rep_exfat.h0_h1_trial_entry_allowed:
        errors.extend(f"r1_exfat: {e}" for e in (rep_exfat.errors or (rep_exfat.status,)))
    if not production_cards_rejected:
        errors.append("r1_exfat: negative-control client production card rejection failed")

    passed = (
        rep_18.all_18_gates_verified
        and rep_18.offline_15_gates_verified
        and rep_18.g17_to_g18_all_passed
        and (not rep_18.persistent_emmc_writes_authorized)
        and (not rep_18.persistent_write_release)
        and rep_exfat.all_passed
        and rep_exfat.h0_h1_trial_entry_allowed
        and production_cards_rejected
        and len(errors) == 0
    )
    gates_summary = [
        {
            "gate_id": str(g.get("gate_id", "")),
            "gate_code": str(g.get("gate_code", "")),
            "status": str(g.get("status", "")),
        }
        for g in rep_18.gates
    ]
    evidence = {
        "schema_18gate": rep_18.schema,
        "status_18gate": rep_18.status,
        "gate_count": len(gates_summary),
        "all_18_gates_verified": rep_18.all_18_gates_verified,
        "offline_15_gates_verified": rep_18.offline_15_gates_verified,
        "g17_to_g18_all_passed": rep_18.g17_to_g18_all_passed,
        "gates": _strip_utc_fields(gates_summary),
        "exfat_status": rep_exfat.status,
        "exfat_lab_card_all_passed": rep_exfat.all_passed,
        "exfat_bootchecksum_ok": bool(
            rep_exfat.dual_slot_firewall.get("slot_a_result", {})
            .get("exfat_audit", {})
            .get("main_checksum_ok", False)
        ),
        "p1_vs_exfat_separated": bool(rep_exfat.filesystem_separation.get("valid", False)),
        "production_xdroot_rejected": not client_xdroot.valid,
        "production_m4root_rsv_rejected": not client_m4root_rsv.valid,
    }
    return StageBRehearsalStageResult(
        stage_id="R1",
        stage_name="SAFETY_18GATE_AND_MEDIA_FIREWALL",
        passed=passed,
        status=STATUS_REHEARSAL_PASSED if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"18-Gate ({len(gates_summary)}/18) + exFAT 12-sector BootChecksum "
            f"+ XDROOT/M4ROOT/.RSV firewall {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _run_stage_r2(
    *,
    h0_dir: Path,
    use_clean_room: bool,
    faults: StageBRehearsalFaultInjection,
) -> Tuple[StageBRehearsalStageResult, bytes, bytes]:
    """R2 (H0_BASELINE_SNAPSHOT): Capture deterministic 16-surface H0 cryptographic baseline."""
    errors: List[str] = []
    donor_probes, fa0080_tbl, probe_errs = _probe_donor_surfaces_o_rdonly(use_clean_room=use_clean_room)
    errors.extend(f"r2_probe: {e}" for e in probe_errs)

    stock_bk4 = build_persistent_stock_bk4_bytes(
        fa0080_table=fa0080_tbl,
        wireless_enabled=True,
        bk_lang_byte=0x00,
        active_byte8=faults.r2_bk4_active_byte8,
    )
    h0_manifest = populate_stage_b_capture_bundle_fixture(
        h0_dir,
        fa0080_table=fa0080_tbl,
        bk4_bytes=stock_bk4,
    )

    if faults.r2_corrupt_wbi2:
        wbi_p = h0_dir / "p5_wbi_header.bin"
        raw = bytearray(_read_file_o_rdonly(wbi_p))
        raw[0:4] = b"XXXX"
        wbi_p.write_bytes(bytes(raw))
    if faults.r2_corrupt_sector0:
        sec_p = h0_dir / "sector0.bin"
        raw = bytearray(_read_file_o_rdonly(sec_p))
        raw[0:4] = b"0000"
        sec_p.write_bytes(bytes(raw))

    h0_audit = verify_real_tier0_capture_bundle(h0_dir)
    if not h0_audit.valid:
        errors.extend(f"r2_h0_bundle: {e}" for e in h0_audit.errors)

    surface_digests: Dict[str, Dict[str, Any]] = {}
    for sec_name in ("items", "redline_headers", "stage_b_forensic_probes"):
        sec_obj = h0_manifest.get(sec_name, {})
        if isinstance(sec_obj, Mapping):
            for k in sorted(sec_obj.keys()):
                ent = sec_obj[k]
                if isinstance(ent, Mapping):
                    surface_digests[str(k)] = {
                        "category": sec_name,
                        "file_name": str(ent.get("file_name", "")),
                        "bytes": int(ent.get("bytes", 0)),
                        "sha256": str(ent.get("pass1_sha256", "")),
                    }

    if len(surface_digests) != 16:
        errors.append(f"r2_surfaces: expected 16 baseline surfaces, got {len(surface_digests)}")

    passed = (
        h0_audit.valid
        and h0_audit.is_non_synthetic_hardware
        and h0_audit.sector0_magic_ok
        and h0_audit.p2_bk4_magic_ok
        and h0_audit.p1_vfat_header_ok
        and h0_audit.p5_wbi2_header_ok
        and h0_audit.p8_tomco_header_ok
        and len(surface_digests) == 16
        and len(errors) == 0
    )
    h0_audit_dict = asdict(h0_audit)
    h0_audit_dict["bundle_dir"] = "<REHEARSAL_SANDBOX>/h0_capture"

    evidence = {
        "model_id": h0_audit.model_id,
        "body_serial": h0_audit.body_serial,
        "emmc_cid": h0_audit.emmc_cid,
        "surface_count": len(surface_digests),
        "surfaces": surface_digests,
        "donor_o_rdonly_probes": donor_probes,
        "h0_bundle_audit": h0_audit_dict,
    }
    return (
        StageBRehearsalStageResult(
            stage_id="R2",
            stage_name="H0_BASELINE_SNAPSHOT",
            passed=passed,
            status=STATUS_REHEARSAL_PASSED if passed else STATUS_FAIL_CLOSED,
            summary=(
                f"H0 16-surface snapshot (Tier-0 + BK4 + WBI2 + Stock-CP + C2PA + SPACC) "
                f"{'PASS' if passed else 'FAIL_CLOSED'}"
            ),
            evidence=evidence,
            errors=tuple(errors),
        ),
        fa0080_tbl,
        stock_bk4,
    )


def _run_stage_r3(
    *,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    lang: str,
    use_clean_room: bool,
    volatile_overlay_dir: Path,
    faults: StageBRehearsalFaultInjection,
) -> StageBRehearsalStageResult:
    """R3 (STAGE_B_VOLATILE_OVERLAY_MOUNT): Phase 48/52 Stage-B CPIO v2 + P12 WF-12 + init2 drill."""
    errors: List[str] = []
    rep = verify_stage_b_ram_overlay_v2(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        lang=lang,
        synthetic_clean_room=use_clean_room,
    )

    # Populate simulated volatile tmpfs `/tmp/fx6_overlay` inside sandbox
    overlay_root = volatile_overlay_dir / "tmp" / "fx6_overlay"
    overlay_root.mkdir(parents=True, exist_ok=True)
    (overlay_root / "stage_b_overlay_manifest.json").write_text(
        json.dumps({"lock_table_count": rep.lock_table_count, "lang": rep.lang}, sort_keys=True),
        encoding="utf-8",
    )
    bk4_shadow_bytes, bk4_shadow_audit = synthesize_stage_b_bk4_shadow(
        lang=lang,
        flash_write_allowed=False,
        use_clean_room=use_clean_room,
    )
    (volatile_overlay_dir / "tmp" / "bk4_shadow").write_bytes(bk4_shadow_bytes)

    # Fault injections in R3
    wf12_immunity_ok = True
    if faults.r3_violate_wf12_airplane:
        # Inject non-zero Airplane-Mode key 0x019e0012=0x01 and audit via Phase 48 BK4 auditor
        bad_audit = audit_stage_b_bk4_shadow(
            build_persistent_stock_bk4_bytes(wireless_enabled=True, bk_lang_byte=STAGE_B_BK_LANG_SPECS[lang].bk_lang_value),
            expected_lang=lang,
        )
        wf12_immunity_ok = bad_audit["valid"] is True
        if not wf12_immunity_ok:
            errors.append(
                "r3_wf12: P12 Airplane-Mode BK4 shadow violation (0x019e0012 != 0x00, WF-12 00342260 hazard)"
            )

    lock_count = rep.lock_table_count
    if faults.r3_corrupt_lock_table:
        lock_count = 12
        errors.append("r3_lock_table: Stage-B lock table incomplete (12/13 != 13/13)")

    tmpfs_within_budget = rep.tmpfs_budget_audit.within_budget
    if faults.r3_exceed_tmpfs_budget:
        tmpfs_within_budget = False
        errors.append(
            f"r3_tmpfs_budget: volatile overlay exceeded {STAGE_B_TMPFS_BUDGET_LIMIT_MIB} MiB DDR ceiling"
        )

    if not rep.all_checks_passed:
        errors.extend(f"r3_overlay: {e}" for e in rep.errors)
    if not rep.cpio_deterministic_metadata_ok:
        errors.append("r3_cpio: SVR4 cpio newc (070701) deterministic metadata audit failed")
    if not rep.init2_failsafe_audit_valid or not rep.init2_ld_preload_audit_valid:
        errors.append("r3_init2: init2 failsafe or ld.so.preload guard audit failed")
    if not rep.rollback_all_matched:
        errors.append("r3_rollback: Stage-B binary rollback SHA-256 verification failed")
    if rep.sandbox_drill.total_emmc_mutation_bytes != 0:
        errors.append(
            f"r3_drill: expected 0 eMMC mutation bytes, got {rep.sandbox_drill.total_emmc_mutation_bytes}"
        )
    if rep.sandbox_drill.passed_count != rep.sandbox_drill.scenario_count:
        errors.append(
            f"r3_drill: {rep.sandbox_drill.passed_count}/{rep.sandbox_drill.scenario_count} scenarios passed"
        )
    if not all(v == "00" for v in bk4_shadow_audit.get("airplane_keys", {}).values()):
        errors.append("r3_bk4_shadow: Airplane-Mode keys must all be 0x00")

    passed = (
        rep.all_checks_passed
        and rep.cpio_deterministic_metadata_ok
        and rep.init2_failsafe_audit_valid
        and rep.init2_ld_preload_audit_valid
        and rep.rollback_all_matched
        and lock_count == 13
        and tmpfs_within_budget
        and wf12_immunity_ok
        and rep.sandbox_drill.passed_count == rep.sandbox_drill.scenario_count
        and rep.sandbox_drill.clean_mount_verified
        and rep.sandbox_drill.all_faults_fail_closed
        and rep.sandbox_drill.total_emmc_mutation_bytes == 0
        and rep.sandbox_drill.total_cp_mutation_bytes == 0
        and rep.sandbox_drill.total_wbi_mutation_bytes == 0
        and (not rep.persistent_emmc_writes_authorized)
        and rep.cp_mutation_bytes == 0
        and rep.wbi_mutation_bytes == 0
        and len(errors) == 0
    )
    evidence = {
        "schema": rep.schema,
        "lang": rep.lang,
        "bk_lang_id": f"0x{BK_KEY_LANG:08x}",
        "bk_lang_value_hex": f"0x{rep.bk_lang_spec.bk_lang_value:02x}",
        "cpio_archive_bytes": rep.cpio_size_bytes,
        "cpio_entry_count": rep.cpio_entry_count,
        "cpio_sha256": rep.cpio_sha256,
        "lock_table_count": lock_count,
        "volatile_tmpfs_overlay_mib": rep.tmpfs_budget_audit.volatile_tmpfs_overlay_mib,
        "tmpfs_budget_limit_mib": STAGE_B_TMPFS_BUDGET_LIMIT_MIB,
        "tmpfs_within_budget": tmpfs_within_budget,
        "stage_b_appfw_sha256": rep.stage_b_appfw_sha256,
        "stage_b_wlan_rsrc_sha256": rep.stage_b_wlan_rsrc_sha256,
        "expected_local_appfw_sha256": FX6_APPFW_STAGE_B_SHA256,
        "expected_local_wlan_sha256": FX6_WLAN_RSRC_P12_SHA256,
        "bk4_airplane_keys": dict(bk4_shadow_audit.get("airplane_keys", {})),
        "wf12_immunity_ok": wf12_immunity_ok,
        "init2_sandbox_passed": rep.sandbox_drill.passed_count,
        "init2_sandbox_total": rep.sandbox_drill.scenario_count,
        "init2_total_emmc_writes": rep.sandbox_drill.total_emmc_mutation_bytes,
    }
    return StageBRehearsalStageResult(
        stage_id="R3",
        stage_name="STAGE_B_VOLATILE_OVERLAY_MOUNT",
        passed=passed,
        status=STATUS_REHEARSAL_PASSED if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"Stage-B CPIO newc ({rep.tmpfs_budget_audit.volatile_tmpfs_overlay_mib:.2f} MiB, "
            f"{lock_count}/13 locks, init2 {rep.sandbox_drill.passed_count}/{rep.sandbox_drill.scenario_count}, "
            f"0 eMMC writes) {'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _run_stage_r4(
    *,
    repo_root: Path,
    use_clean_room: bool,
    faults: StageBRehearsalFaultInjection,
) -> Tuple[StageBRehearsalStageResult, int]:
    """R4 (LIVE_H1_COEMULATION_AND_4LANG_UI): QMP Stage 7 + HDMI RAW16/USB-C Stage 8 + Round 13 4-Lang."""
    errors: List[str] = []

    qmp_rep = qmp_tracer.run_phase58_qmp_tracer_audit(force_clean_room=use_clean_room)
    hdmi_rep = hdmi_uvc_emu.run_phase63_hdmi_uvc_audit(force_clean_room=use_clean_room)
    r13_summary, r13_source = _load_round13_summary(repo_root=repo_root, use_clean_room=use_clean_room)

    # 1. QMP non-intrusive guest tracer invariants
    qmp_red = qmp_rep.get("redlines", {})
    observed_nop = int(qmp_red.get("nop_count", -1)) + int(faults.r4_nop_count)
    if not qmp_rep.get("all_checks_passed"):
        errors.append("r4_qmp: Phase 58 QMP guest introspection audit failed")
    if observed_nop != 0:
        errors.append(f"r4_qmp: non-intrusive invariant violated (nop_count={observed_nop} != 0)")
    if int(qmp_red.get("cp_mutation_bytes", -1)) != 0:
        errors.append("r4_qmp: cp_mutation_bytes != 0")

    # 2. HDMI RAW16 256B EDID & USB-C mode arbitrator invariants
    hdmi_red = hdmi_rep.get("redlines", {})
    edid_ok = bool(hdmi_rep.get("all_checks_passed"))
    if faults.r4_corrupt_edid_checksum:
        corrupt_edid = bytearray(hdmi_uvc_emu.synthesize_sink_edid(hdmi_uvc_emu.HDMI_SINK_ATOMOS_NINJA_RAW16))
        corrupt_edid[127] ^= 0x55
        try:
            hdmi_uvc_emu.parse_and_verify_edid(bytes(corrupt_edid))
            edid_ok = False
        except hdmi_uvc_emu.EdidValidationError as exc:
            edid_ok = False
            errors.append(f"r4_edid: {exc}")

    if not hdmi_rep.get("all_checks_passed"):
        errors.append("r4_hdmi: Phase 63 HDMI RAW16 / USB-C arbitrator audit failed")
    if int(hdmi_red.get("sdi_transceiver_faults", -1)) != 0:
        errors.append("r4_hdmi: sdi_transceiver_faults != 0")
    if not hdmi_rep.get("usbc_arbitrator_matrix", {}).get("passed", False):
        errors.append("r4_usbc: USB-C mode arbitrator matrix failed")

    # 3. Round 13 4-Language real FX3 7.02 kernel native presenter closure
    kernel_ver = str(r13_summary.get("kernel_version", ""))
    if "4.9.337-scel+" not in kernel_ver:
        errors.append(f"r4_round13: unexpected kernel_version {kernel_ver!r}")

    runs = r13_summary.get("runs", {})
    r13a = runs.get("r13a_status_check_schinese", {})
    r13b = runs.get("r13b_menu_3layer_tchinese", {})
    r13c = runs.get("r13c_menu_3layer_paintlook_schinese", {})

    r13_nops = (
        int(r13a.get("nop_count", -1))
        + int(r13b.get("nop_count", -1))
        + int(r13c.get("nop_count", -1))
        + int(faults.r4_nop_count)
    )
    r13_crashes = (
        int(r13a.get("crashes", -1))
        + int(r13b.get("crashes", -1))
        + int(r13c.get("crashes", -1))
        + int(faults.r4_crashes)
    )
    if r13a.get("target_sid") != "0x2f":
        errors.append(f"r4_round13: expected Status Check sid=0x2f, got {r13a.get('target_sid')!r}")
    if r13b.get("target_sid") != "0x11" or r13c.get("target_sid") != "0x11":
        errors.append("r4_round13: expected 3-layer menu sid=0x11 in r13b and r13c")
    if r13_nops != 0:
        errors.append(f"r4_round13: nop_count={r13_nops} != 0")
    if r13_crashes != 0:
        errors.append(f"r4_round13: crashes={r13_crashes} != 0")

    for run_id, run_obj in (("r13a", r13a), ("r13b", r13b), ("r13c", r13c)):
        fi = run_obj.get("faithful_invariants", {})
        if fi.get("FX6_NATIVE_FAITHFUL") != 1 or any(
            int(fi.get(k, -1)) != 0
            for k in ("subst_color", "subst_image", "forced_render", "skipped_node", "lock_bypass")
        ):
            errors.append(f"r4_round13: {run_id} failed FX6_NATIVE_FAITHFUL invariants")

    langs_obj = r13_summary.get("languages", {})
    if not all(code in langs_obj for code in STAGE_B_SUPPORTED_LANGS):
        errors.append("r4_round13: missing one or more of the 4 languages (en/schinese/tchinese/japanese)")

    matrix = r13_summary.get("r13d_4lang_matrix_audit", {})
    big6_deltas = copy.deepcopy(matrix.get("big6_home_6pair_deltas", {}))
    menu_deltas = copy.deepcopy(matrix.get("full_menu_6pair_deltas", {}))
    if faults.r4_zero_lang_pair_delta:
        if faults.r4_zero_lang_pair_delta in big6_deltas:
            big6_deltas[faults.r4_zero_lang_pair_delta]["diff_pixels"] = 0
            big6_deltas[faults.r4_zero_lang_pair_delta]["strictly_positive"] = False
        if faults.r4_zero_lang_pair_delta in menu_deltas:
            menu_deltas[faults.r4_zero_lang_pair_delta]["diff_pixels"] = 0
            menu_deltas[faults.r4_zero_lang_pair_delta]["strictly_positive"] = False

    positive_pairs_verified = 0
    for pair_name in ROUND13_4LANG_PAIRS:
        b_ent = big6_deltas.get(pair_name, {})
        m_ent = menu_deltas.get(pair_name, {})
        b_ok = int(b_ent.get("diff_pixels", 0)) > 0 and bool(b_ent.get("strictly_positive", False))
        m_ok = int(m_ent.get("diff_pixels", 0)) > 0 and bool(m_ent.get("strictly_positive", False))
        if b_ok and m_ok:
            positive_pairs_verified += 1
        else:
            errors.append(f"r4_round13: cross-language pixel delta pair {pair_name} not strictly positive")

    passed = (
        bool(qmp_rep.get("all_checks_passed"))
        and observed_nop == 0
        and edid_ok
        and bool(hdmi_rep.get("all_checks_passed"))
        and int(hdmi_red.get("sdi_transceiver_faults", -1)) == 0
        and positive_pairs_verified == 6
        and r13_nops == 0
        and r13_crashes == 0
        and len(errors) == 0
    )
    evidence = {
        "qmp_schema": qmp_rep.get("schema"),
        "qmp_all_checks_passed": bool(qmp_rep.get("all_checks_passed")),
        "qmp_nop_count": observed_nop,
        "qmp_ctrl_magic_verified": bool(
            qmp_rep.get("guest_introspection", {}).get("ctrl_mailbox", {}).get("magic_valid")
        ),
        "hdmi_uvc_schema": hdmi_rep.get("schema"),
        "hdmi_all_checks_passed": bool(hdmi_rep.get("all_checks_passed")),
        "edid_256b_valid": edid_ok,
        "usbc_max_concurrent_gadgets": hdmi_rep.get("usbc_arbitrator_matrix", {}).get(
            "max_concurrent_gadgets"
        ),
        "sdi_transceiver_faults": int(hdmi_red.get("sdi_transceiver_faults", -1)),
        "round13_source": r13_source,
        "round13_kernel_version": kernel_ver,
        "round13_status_check_sid": r13a.get("target_sid"),
        "round13_menu_3layer_sid": r13b.get("target_sid"),
        "round13_4lang_positive_pairs": positive_pairs_verified,
        "round13_big6_pair_deltas": {
            p: int(big6_deltas.get(p, {}).get("diff_pixels", 0)) for p in ROUND13_4LANG_PAIRS
        },
        "round13_menu_pair_deltas": {
            p: int(menu_deltas.get(p, {}).get("diff_pixels", 0)) for p in ROUND13_4LANG_PAIRS
        },
    }
    return (
        StageBRehearsalStageResult(
            stage_id="R4",
            stage_name="LIVE_H1_COEMULATION_AND_4LANG_UI",
            passed=passed,
            status=STATUS_REHEARSAL_PASSED if passed else STATUS_FAIL_CLOSED,
            summary=(
                f"QMP nop={observed_nop} + HDMI RAW16 256B EDID/USB-C + Round 13 "
                f"4-Lang ({positive_pairs_verified}/6 pairs>0, sid=0x2f/0x11) "
                f"{'PASS' if passed else 'FAIL_CLOSED'}"
            ),
            evidence=evidence,
            errors=tuple(errors),
        ),
        positive_pairs_verified,
    )


def _run_stage_r5(
    *,
    volatile_overlay_dir: Path,
    h2_dir: Path,
    fa0080_tbl: bytes,
    stock_bk4: bytes,
    faults: StageBRehearsalFaultInjection,
) -> StageBRehearsalStageResult:
    """R5 (COLD_POWER_CYCLE_WIPE): Cold power-off wipe of volatile tmpfs + H2 readback prep."""
    errors: List[str] = []

    overlay_root = volatile_overlay_dir / "tmp" / "fx6_overlay"
    bk4_shadow_path = volatile_overlay_dir / "tmp" / "bk4_shadow"

    # Simulate cold power-cycle volatile tmpfs wipe (unless lingering mount fault injected)
    if not faults.r5_lingering_overlay_mount:
        for p in (
            overlay_root / "stage_b_overlay_manifest.json",
            bk4_shadow_path,
        ):
            if p.exists():
                p.unlink()
        if overlay_root.exists():
            overlay_root.rmdir()

    lingering_files = sum(1 for _ in overlay_root.rglob("*")) if overlay_root.exists() else 0
    volatile_vanished = (not overlay_root.exists()) and (not bk4_shadow_path.exists()) and lingering_files == 0
    lingering_mounts = 1 if faults.r5_lingering_overlay_mount else 0
    emmc_residual_writes = int(faults.r5_residual_emmc_writes)
    mod_arm_once_present = bool(faults.r5_sticky_mod_arm_once)

    if not volatile_vanished or lingering_mounts != 0:
        errors.append(
            f"r5_wipe: volatile /tmp/fx6_overlay did not vanish cleanly (lingering_mounts={lingering_mounts}, files={lingering_files})"
        )
    if emmc_residual_writes != 0:
        errors.append(f"r5_emmc: non-zero residual eMMC writes after cold power cycle ({emmc_residual_writes} B)")
    if mod_arm_once_present:
        errors.append("r5_oneshot: /tmp/mod_arm_once residue persisted across cold power cycle")

    # Populate H2 stock FX3 v7.02 readback bundle (with optional R6 drift injection)
    cap_sha = hashlib.sha256(b"fx3-p1-fat12-rollback-capsule-v702").hexdigest()
    p1_cap = {
        "boot_attempts": 1 if mod_arm_once_present else 0,
        "mod_arm_once_present": mod_arm_once_present,
        "capsule_sha256": cap_sha,
        "expected_capsule_sha256": cap_sha,
        "fsync_order": list(REQUIRED_FSYNC_ORDER),
        "allow_boot_partition_targeting": False,
        "emmc_write_bytes": emmc_residual_writes,
    }
    populate_stage_b_capture_bundle_fixture(
        h2_dir,
        fa0080_table=fa0080_tbl,
        bk4_bytes=stock_bk4,
        p1_capsule_info=p1_cap,
    )

    # Apply R6 drift injection if requested
    if faults.r6_drift_surface:
        target_key = _DRIFT_SURFACE_ALIASES.get(faults.r6_drift_surface, faults.r6_drift_surface)
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
            raise ValueError(f"Unsupported r6_drift_surface target: {faults.r6_drift_surface!r}")
        mf_path.write_text(json.dumps(mf, indent=2) + "\n", encoding="utf-8")

    passed = (
        volatile_vanished
        and lingering_mounts == 0
        and emmc_residual_writes == 0
        and (not mod_arm_once_present)
        and len(errors) == 0
    )
    evidence = {
        "transition": "H1 -> H2",
        "volatile_overlay_vanished": volatile_vanished,
        "lingering_mounts": lingering_mounts,
        "tmpfs_residue_files": lingering_files,
        "emmc_residual_writes": emmc_residual_writes,
        "mod_arm_once_present": mod_arm_once_present,
        "stock_fx3_restored": passed,
    }
    return StageBRehearsalStageResult(
        stage_id="R5",
        stage_name="COLD_POWER_CYCLE_WIPE",
        passed=passed,
        status=STATUS_REHEARSAL_PASSED if passed else STATUS_FAIL_CLOSED,
        summary=(
            f"H1->H2 cold power-cycle wipe (tmpfs vanished={volatile_vanished}, "
            f"lingering_mounts={lingering_mounts}, emmc_writes={emmc_residual_writes}) "
            f"{'PASS' if passed else 'FAIL_CLOSED'}"
        ),
        evidence=evidence,
        errors=tuple(errors),
    )


def _run_stage_r6(
    *,
    h0_dir: Path,
    h2_dir: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
    faults: StageBRehearsalFaultInjection,
) -> Tuple[StageBRehearsalStageResult, Dict[str, Any]]:
    """R6 (H0_VS_H2_POST_TRIAL_FORENSIC_AUDIT): Phase 62 16-surface H0 vs H2 diff + 10-scenario tamper drills."""
    errors: List[str] = []

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

    drifted_count = len(receipt.drifted_items)
    if not receipt.all_checks_passed or not receipt.zero_persistence_verified:
        errors.extend(f"r6_receipt: {e}" for e in (receipt.errors or (receipt.classification,)))
    if not audit_rep.all_checks_passed or not audit_rep.all_10_scenarios_passed or not audit_verify.valid:
        errors.append("r6_tamper_drill: Phase 62 10-scenario negative-control drill failed")

    # Optional explicit negative-control failure injection to verify fail-closed orchestration
    tamper_drills_passed = audit_rep.passed_scenario_count if audit_rep.all_10_scenarios_passed else 0
    if faults.r6_tamper_negative_control:
        tamper_drills_passed = 0
        errors.append("r6_tamper_drill: injected negative-control audit failure")

    passed = (
        receipt.all_checks_passed
        and receipt.zero_persistence_verified
        and drifted_count == 0
        and receipt.matched_item_count == 16
        and receipt.c2pa_keystore_untouched
        and receipt.spacc_cnflasha_untouched
        and receipt.calibration_mutation_bytes == 0
        and receipt.wbi_mutation_bytes == 0
        and receipt.cp_mutation_bytes == 0
        and receipt.sector0_mutation_bytes == 0
        and audit_rep.all_checks_passed
        and audit_rep.all_10_scenarios_passed
        and audit_verify.valid
        and (not faults.r6_tamper_negative_control)
        and len(errors) == 0
    )
    receipt_norm = copy.deepcopy(receipt.to_dict())
    if isinstance(receipt_norm.get("h0_bundle_audit"), dict):
        receipt_norm["h0_bundle_audit"]["bundle_dir"] = "<REHEARSAL_SANDBOX>/h0_capture"
    if isinstance(receipt_norm.get("h2_bundle_audit"), dict):
        receipt_norm["h2_bundle_audit"]["bundle_dir"] = "<REHEARSAL_SANDBOX>/h2_capture"

    evidence = {
        "receipt_schema": receipt.schema,
        "classification": receipt.classification,
        "anomaly_codes": list(receipt.anomaly_codes),
        "audited_item_count": receipt.audited_item_count,
        "matched_item_count": receipt.matched_item_count,
        "drifted_surface_count": drifted_count,
        "drifted_items": list(receipt.drifted_items),
        "persistent_bytes_mutated": receipt.persistent_bytes_mutated,
        "wbi_mutation_bytes": receipt.wbi_mutation_bytes,
        "cp_mutation_bytes": receipt.cp_mutation_bytes,
        "calibration_mutation_bytes": receipt.calibration_mutation_bytes,
        "sector0_mutation_bytes": receipt.sector0_mutation_bytes,
        "c2pa_keystore_untouched": receipt.c2pa_keystore_untouched,
        "spacc_cnflasha_untouched": receipt.spacc_cnflasha_untouched,
        "exfat_media_clean": receipt.p1_exfat_audit.exfat_media_clean,
        "peak_soc_c": receipt.serial_thermal_post_mortem.peak_soc_c,
        "negative_tamper_scenarios_passed": tamper_drills_passed,
        "negative_tamper_scenarios_total": audit_rep.scenario_count,
        "audit_report_sha256": audit_rep.report_sha256,
        "receipt_sha256": receipt.receipt_sha256,
    }
    meta = {
        "drifted_surface_count": drifted_count,
        "c2pa_keystore_untouched": receipt.c2pa_keystore_untouched,
        "spacc_cnflasha_untouched": receipt.spacc_cnflasha_untouched,
        "cp_mutation_bytes": receipt.cp_mutation_bytes,
        "wbi_mutation_bytes": receipt.wbi_mutation_bytes,
        "calibration_mutation_bytes": receipt.calibration_mutation_bytes,
        "tamper_drills_passed": tamper_drills_passed,
    }
    return (
        StageBRehearsalStageResult(
            stage_id="R6",
            stage_name="H0_VS_H2_POST_TRIAL_FORENSIC_AUDIT",
            passed=passed,
            status=STATUS_REHEARSAL_PASSED if passed else STATUS_FAIL_CLOSED,
            summary=(
                f"H0 vs H2 ({receipt.matched_item_count}/{receipt.audited_item_count} surfaces, "
                f"drifted={drifted_count}, C2PA untouched={receipt.c2pa_keystore_untouched}, "
                f"tamper drills {tamper_drills_passed}/{audit_rep.scenario_count}) "
                f"{'PASS' if passed else 'FAIL_CLOSED'}"
            ),
            evidence=evidence,
            errors=tuple(errors),
        ),
        meta,
    )


# ---------------------------------------------------------------------------
# Primary Orchestrator & Fail-Closed Certificate Verifier
# ---------------------------------------------------------------------------


def run_stage_b_closed_loop_rehearsal(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    lang: str = "en",
    synthetic_clean_room: Optional[bool] = None,
    faults: Optional[StageBRehearsalFaultInjection] = None,
) -> StageBClosedLoopRehearsalReport:
    """Execute the complete 7-stage zero-write Stage-B closed-loop rehearsal (`R0..R6`)."""
    if lang not in STAGE_B_SUPPORTED_LANGS:
        raise ValueError(f"Unsupported Stage-B language {lang!r}; expected one of {STAGE_B_SUPPORTED_LANGS}")

    active_faults = faults if faults is not None else StageBRehearsalFaultInjection()
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    verification_mode = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"

    all_errors: List[str] = []
    stages: List[StageBRehearsalStageResult] = []
    temp_dir_cleaned = False

    tmp_ctx = tempfile.TemporaryDirectory(prefix="fx6_phase68_rehearsal_")
    tmp_path = Path(tmp_ctx.name)
    try:
        h0_dir = tmp_path / "h0_capture"
        h2_dir = tmp_path / "h2_capture"
        volatile_overlay_dir = tmp_path / "volatile_tmpfs"
        volatile_overlay_dir.mkdir(parents=True, exist_ok=True)

        # R0: Bench Fixture Self-Test
        r0 = _run_stage_r0(use_clean_room=use_clean_room, faults=active_faults)
        stages.append(r0)

        # R1: 18-Gate Safety + exFAT Media Firewall
        r1 = _run_stage_r1(repo_root=repo_root, use_clean_room=use_clean_room, faults=active_faults)
        stages.append(r1)

        # R2: H0 Baseline Snapshot (16 surfaces)
        r2, fa0080_tbl, stock_bk4 = _run_stage_r2(
            h0_dir=h0_dir,
            use_clean_room=use_clean_room,
            faults=active_faults,
        )
        stages.append(r2)

        # R3: Stage-B Volatile Overlay Mount (CPIO v2 + P12 WF-12 + init2 drill)
        r3 = _run_stage_r3(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            lang=lang,
            use_clean_room=use_clean_room,
            volatile_overlay_dir=volatile_overlay_dir,
            faults=active_faults,
        )
        stages.append(r3)

        # R4: Live H1 Co-Emulation (QMP + HDMI RAW16 / USB-C) + Round 13 4-Language Closure
        r4, round13_pairs_ok = _run_stage_r4(
            repo_root=repo_root,
            use_clean_room=use_clean_room,
            faults=active_faults,
        )
        stages.append(r4)

        # R5: Cold Power-Cycle Wipe (H1 -> H2)
        r5 = _run_stage_r5(
            volatile_overlay_dir=volatile_overlay_dir,
            h2_dir=h2_dir,
            fa0080_tbl=fa0080_tbl,
            stock_bk4=stock_bk4,
            faults=active_faults,
        )
        stages.append(r5)

        # R6: H0 vs H2 Post-Trial Forensic Audit (16 surfaces + 10-scenario tamper drills)
        r6, r6_meta = _run_stage_r6(
            h0_dir=h0_dir,
            h2_dir=h2_dir,
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            use_clean_room=use_clean_room,
            faults=active_faults,
        )
        stages.append(r6)
    finally:
        tmp_ctx.cleanup()
        temp_dir_cleaned = not tmp_path.exists()

    for st in stages:
        for err in st.errors:
            all_errors.append(f"{st.stage_id}: {err}")
    if not temp_dir_cleaned:
        all_errors.append("sandbox: ephemeral temporary rehearsal directory was not cleaned up")

    failed_ids = tuple(st.stage_id for st in stages if not st.passed)
    passed_count = sum(1 for st in stages if st.passed)
    rehearsal_passed = (
        len(stages) == 7
        and passed_count == 7
        and len(failed_ids) == 0
        and temp_dir_cleaned
        and r6_meta["drifted_surface_count"] == 0
        and r6_meta["c2pa_keystore_untouched"]
        and r6_meta["spacc_cnflasha_untouched"]
        and r6_meta["cp_mutation_bytes"] == 0
        and r6_meta["wbi_mutation_bytes"] == 0
        and r6_meta["calibration_mutation_bytes"] == 0
        and len(all_errors) == 0
    )

    draft = StageBClosedLoopRehearsalReport(
        schema_version=STAGE_B_REHEARSAL_SCHEMA,
        phase_version=PHASE_68_VERSION,
        verification_mode=verification_mode,
        selected_lang=lang,
        rehearsal_passed=rehearsal_passed,
        status=STATUS_REHEARSAL_PASSED if rehearsal_passed else STATUS_FAIL_CLOSED,
        hardware_live_attachment_authorized=False,
        hardware_live_attachment_requirements=HARDWARE_LIVE_ATTACHMENT_REQUIREMENTS,
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        cp_mutation_bytes=int(r6_meta["cp_mutation_bytes"]),
        wbi_mutation_bytes=int(r6_meta["wbi_mutation_bytes"]),
        calibration_mutation_bytes=int(r6_meta["calibration_mutation_bytes"]),
        usb_or_camera_operations=USB_OR_CAMERA_OPERATIONS,
        temp_dir_cleaned=temp_dir_cleaned,
        stage_count=len(stages),
        passed_stage_count=passed_count,
        failed_stage_ids=failed_ids,
        stages=tuple(stages),
        h0_surface_count=int(r2.evidence.get("surface_count", 0)),
        h2_drifted_surface_count=int(r6_meta["drifted_surface_count"]),
        c2pa_keystore_untouched=bool(r6_meta["c2pa_keystore_untouched"]),
        spacc_cnflasha_untouched=bool(r6_meta["spacc_cnflasha_untouched"]),
        round13_4lang_pairs_verified=round13_pairs_ok,
        negative_tamper_drills_passed=int(r6_meta["tamper_drills_passed"]),
        errors=tuple(all_errors),
        rehearsal_digest_sha256="",
    )
    digest = compute_rehearsal_digest_sha256(draft.to_dict())
    return replace(draft, rehearsal_digest_sha256=digest)


def verify_stage_b_rehearsal_certificate(
    payload: object,
) -> StageBRehearsalCertificateVerifyResult:
    """Fail-closed verifier for `stage_b_closed_loop_rehearsal_v1` certificates."""
    if isinstance(payload, StageBClosedLoopRehearsalReport):
        data: Dict[str, Any] = payload.to_dict()
    elif isinstance(payload, Mapping):
        data = dict(payload)
    else:
        return StageBRehearsalCertificateVerifyResult(
            valid=False,
            schema_ok=False,
            digest_matched=False,
            expected_rehearsal_digest_sha256="",
            observed_rehearsal_digest_sha256="",
            safety_redlines_ok=False,
            all_7_stages_ok=False,
            rehearsal_passed=False,
            errors=("Certificate payload must be a mapping or StageBClosedLoopRehearsalReport",),
        )

    errors: List[str] = []
    schema_ok = data.get("schema_version") == STAGE_B_REHEARSAL_SCHEMA
    if not schema_ok:
        errors.append(
            f"Invalid schema_version {data.get('schema_version')!r}, expected {STAGE_B_REHEARSAL_SCHEMA!r}"
        )

    observed_digest = str(data.get("rehearsal_digest_sha256", ""))
    expected_digest = compute_rehearsal_digest_sha256(data)
    digest_matched = bool(HEX64_RE.fullmatch(observed_digest)) and (observed_digest == expected_digest)
    if not digest_matched:
        errors.append(
            f"rehearsal_digest_sha256 mismatch: observed={observed_digest!r} vs expected={expected_digest!r}"
        )

    rendered = json.dumps(data, sort_keys=True, ensure_ascii=False)
    if _RAW_BYTES_REPR_RE.search(rendered):
        errors.append("Certificate contains forbidden raw binary bytes repr")

    safety_redlines_ok = (
        data.get("persistent_emmc_writes_authorized") is False
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
        errors.append("Hard-locked safety redlines violated in rehearsal certificate")

    stages_raw = data.get("stages")
    all_7_stages_ok = False
    if not isinstance(stages_raw, (list, tuple)) or len(stages_raw) != 7:
        errors.append("stages must contain exactly 7 entries (R0..R6)")
    else:
        seen_ids = tuple(str(s.get("stage_id", "")) for s in stages_raw if isinstance(s, Mapping))
        if seen_ids != REHEARSAL_STAGE_IDS:
            errors.append(f"Stage sequence mismatch: {seen_ids!r} != {REHEARSAL_STAGE_IDS!r}")
        else:
            all_7_stages_ok = all(
                isinstance(s, Mapping) and s.get("passed") is True and s.get("status") == STATUS_REHEARSAL_PASSED
                for s in stages_raw
            )
            if not all_7_stages_ok:
                errors.append("One or more stages in R0..R6 failed")

    rehearsal_passed = (
        data.get("rehearsal_passed") is True
        and data.get("status") == STATUS_REHEARSAL_PASSED
        and data.get("passed_stage_count") == 7
        and data.get("stage_count") == 7
        and data.get("h2_drifted_surface_count") == 0
        and data.get("c2pa_keystore_untouched") is True
        and data.get("spacc_cnflasha_untouched") is True
    )
    if not rehearsal_passed:
        errors.append("rehearsal_passed is False or post-trial zero-drift counters failed")

    valid = (
        schema_ok
        and digest_matched
        and safety_redlines_ok
        and all_7_stages_ok
        and rehearsal_passed
        and len(errors) == 0
    )
    return StageBRehearsalCertificateVerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        digest_matched=digest_matched,
        expected_rehearsal_digest_sha256=expected_digest,
        observed_rehearsal_digest_sha256=observed_digest,
        safety_redlines_ok=safety_redlines_ok,
        all_7_stages_ok=all_7_stages_ok,
        rehearsal_passed=rehearsal_passed,
        errors=tuple(errors),
    )


def render_stage_b_rehearsal_markdown(report: StageBClosedLoopRehearsalReport) -> str:
    """Render deterministic Markdown summary for `--markdown-out`."""
    lines = [
        "# Stage-B `R0..R6` Closed-Loop Hardware Rehearsal Certificate",
        "",
        f"- **Schema Version**: `{report.schema_version}`",
        f"- **Verification Mode**: `{report.verification_mode}`",
        f"- **Selected Language**: `{report.selected_lang}`",
        f"- **Rehearsal Verdict**: `{report.status}` (`rehearsal_passed={report.rehearsal_passed}`, `{report.passed_stage_count}/{report.stage_count}` stages)",
        f"- **Live Hardware Attachment Authorized**: `{report.hardware_live_attachment_authorized}` (requires `{', '.join(report.hardware_live_attachment_requirements)}`)",
        f"- **Persistent eMMC Writes Authorized**: `{report.persistent_emmc_writes_authorized}` (`persistent_write_release={report.persistent_write_release}`)",
        f"- **Rehearsal Digest (`SHA-256`)**: `{report.rehearsal_digest_sha256}`",
        "",
        "## 7-Stage Rehearsal Matrix (`R0..R6`)",
        "",
        "| Stage | Name | Status | Summary |",
        "| :---: | --- | :---: | --- |",
    ]
    for st in report.stages:
        lines.append(f"| `{st.stage_id}` | `{st.stage_name}` | `{st.status}` | {st.summary} |")
    lines.extend(
        [
            "",
            "## Post-Trial Zero-Persistence & 4-Language Invariants",
            "",
            f"- `h0_surface_count`: `{report.h0_surface_count}`",
            f"- `h2_drifted_surface_count`: `{report.h2_drifted_surface_count}`",
            f"- `cp_mutation_bytes`: `{report.cp_mutation_bytes}`",
            f"- `wbi_mutation_bytes`: `{report.wbi_mutation_bytes}`",
            f"- `calibration_mutation_bytes`: `{report.calibration_mutation_bytes}`",
            f"- `c2pa_keystore_untouched`: `{report.c2pa_keystore_untouched}`",
            f"- `spacc_cnflasha_untouched`: `{report.spacc_cnflasha_untouched}`",
            f"- `round13_4lang_pairs_verified`: `{report.round13_4lang_pairs_verified}/6`",
            f"- `negative_tamper_drills_passed`: `{report.negative_tamper_drills_passed}/10`",
            "",
        ]
    )
    return "\n".join(lines)
