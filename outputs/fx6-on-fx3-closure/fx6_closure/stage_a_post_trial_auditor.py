"""Phase 16 — Stage-A Post-Trial Zero-Mutation Receipt Auditor & End-to-End H0->H1->H2 Lifecycle Drill.

Automates Phase H2 Step 2/3 of `docs/STAGE-A-HARDWARE-RUNBOOK.md` so post-power-cycle hardware
verification produces a deterministic, machine-verifiable cryptographic receipt
(`stage_a_post_trial_receipt_v1`) rather than relying on manual SHA-256 inspection:

1. `verify_post_trial_zero_mutation(h0_bundle_dir, h2_bundle_dir, h1_telemetry_log_path=None)`:
   - Validates BOTH `h0_bundle_dir` (pre-trial baseline) and `h2_bundle_dir` (post-power-cycle
     readback) via `verify_real_tier0_capture_bundle()`, deterministically rejecting missing,
     symlinked, synthetic, placeholder, two-pass-mismatched, or magic-corrupted bundles.
   - Enforces distinct capture directories (`h0_bundle_dir != h2_bundle_dir`) and 100% same-body
     hardware identity (`model_id == "0x91030080"`, `h0.body_serial == h2.body_serial`,
     `h0.emmc_cid == h2.emmc_cid`, and `h0.camera_body_tag == h2.camera_body_tag`).
   - Streams and compares all 11 mandatory Tier-0 partition/calibration images (`sector0`,
     `boot0`, `boot1`, `p1_updater`, `p2_backup_bin`, `p2_psd_bin`, `p2_defdet_bin`,
     `p6_jiritsu`, `p12_cert`, `p18_lensfile`, `spi_nor_ddrtraining`) PLUS both mandatory
     redline header probes (`p8_tomco.txt`, `p5_wbi_header.bin` — 13 persistent surfaces total),
     counting exact differing bytes on disk (`persistent_bytes_mutated == 0`, `drifted_items == ()`).
   - Verifies `U5` sticky-boot cleanliness on H2 (`p2_backup_bin.bin` `BK4\\0` `boot_img` active
     selector byte `+8 == 0x00` across valid `BK4\\0` records and zero sticky
     `/setting/updater/mode*` residue files or manifest flags).
   - When `h1_telemetry_log_path` (or `h1_telemetry_text`) is supplied, runs
     `verify_h1_orchestrator_telemetry()` checking Layer-2 Clear-Before-Exec (`/tmp/mod_arm_once`
     unlinked strictly before first `mount`/`insmod`), WBI (`p5:/wbi`) hibernation guard,
     Verify-Before-Mount (`11/11` SHA-256 checks), forward steps `1..10`, and exact reverse
     `10..1` LIFO unwind with `0` persistent flash/WBI writes and `0` lingering mounts/loops/kmods.
   - Unconditionally hard-locks `persistent_emmc_writes_authorized = False` and
     `persistent_write_release = False`.

2. `run_h0_h1_h2_lifecycle_drill()`:
   - Executes a complete, zero-residue offline `TemporaryDirectory` lifecycle drill across
     Phase H0 -> Phase H1 (real `PREFIX`-isolated `/bin/sh` execution of
     `etc/fx6_overlay/30-stage-a-orchestrator.sh` + unarmed cold-reboot passthrough check) ->
     Phase H2 (`stage_a_post_trial_receipt_v1` zero-mutation verification), followed by a
     10-case deterministic negative fault-injection suite (`F01..F10`), working identically in
     both local-donor mode and `FX3_FX6_FORCE_CLEAN_ROOM=1` donorless CI mode.
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
import json
import os
import re
import struct
import subprocess
import tempfile
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from fx3_safety.boot_contracts import BK4_HEADER_SIZE, BK4_MAGIC, parse_bk4_record
from fx3_safety.preflight import TIER0_CANONICAL_SOURCES, TIER0_REQUIRED_BACKUPS

from .backup_mount_tolerance_verifier import (
    DEFAULT_FX3_SEED_BK4_PATH,
    build_canonical_fa0080_normal_boot_table,
    synthesize_ram_shadow_bk4,
)
from .hardware_readiness_packet import (
    FX3_MODEL_ID_HEX,
    REQUIRED_REDLINE_HEADER_PROBES,
    SAFE_FILENAME_RE,
    STREAM_CHUNK_BYTES,
    RealTier0CaptureBundleAudit,
    _build_valid_fat16_p1_header_prefix,
    _build_valid_fx3_sector0_bytes,
    _build_valid_p5_wbi2_header_bytes,
    _build_valid_p8_tomco_bytes,
    _is_forced_clean_room,
    _write_sparse_or_patterned_image,
    verify_real_tier0_capture_bundle,
)
from .patcher import DEFAULT_FX3_MODULES_DIR, DEFAULT_FX6_DONOR_LIB_DIR
from .ram_overlay_packager import build_stage_a_ram_overlay_package, extract_cpio_newc_to_dir
from .stage_a_boot_orchestrator import (
    EXPECTED_STAGE_A_FORWARD_STEP_IDS,
    EXPECTED_STAGE_A_LIFO_UNWIND_STEP_IDS,
    ORCHESTRATOR_CPIO_REL_PATH,
)


POST_TRIAL_RECEIPT_SCHEMA = "stage_a_post_trial_receipt_v1"
H1_TELEMETRY_SCHEMA = "stage_a_h1_telemetry_v1"
LIFECYCLE_DRILL_SCHEMA = "stage_a_h0_h1_h2_lifecycle_drill_v1"
PHASE_16_VERSION = "16.0.0"
EXPECTED_H1_VERIFIED_DIGEST_COUNT = 11

STICKY_UPDATER_RELPATH_RE = re.compile(
    r"(?:^|/)(?:setting/|p2_setting/|p2/)?updater/mode[0-9A-Za-z_.-]*$"
    r"|^p2_updater_mode[0-9A-Za-z_.-]*$"
)


@dataclass(frozen=True)
class H1OrchestratorTelemetryAudit:
    valid: bool
    source_kind: str
    boot_branch: str
    diag_code: str
    clear_before_exec_ok: bool
    token_cleared_before_exec: bool
    token_present_after: bool
    no_mount_or_insmod_before_token_unlink: bool
    wbi_hibernation_guard_ok: bool
    wbi_guard_verified: bool
    lingering_wbi_inhibit_lock: bool
    verify_before_mount_ok: bool
    verified_digest_count: int
    forward_steps_ok: bool
    forward_steps: Tuple[str, ...]
    lifo_unwind_ok: bool
    unwind_steps: Tuple[str, ...]
    im_elf_invoked: bool
    zero_persistent_writes_ok: bool
    emmc_write_count: int
    wbi_write_count: int
    sandbox_violation_count: int
    lingering_mount_count: int
    lingering_loop_count: int
    lingering_kmod_count: int
    errors: Tuple[str, ...]


@dataclass(frozen=True)
class PostTrialItemParityRecord:
    item_id: str
    category: str
    file_name: str
    h0_bytes: int
    h2_bytes: int
    h0_sha256: str
    h2_sha256: str
    differing_bytes: int
    bit_exact_match: bool


@dataclass(frozen=True)
class StageAPostTrialReceipt:
    schema: str
    phase_version: str
    all_checks_passed: bool
    zero_mutation_verified: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    usb_or_camera_operations: int
    distinct_capture_dirs_ok: bool
    h0_bundle_valid: bool
    h2_bundle_valid: bool
    both_bundles_real_hardware_valid: bool
    same_body_identity_verified: bool
    model_id: str
    body_serial: str
    emmc_cid: str
    camera_body_tag: str
    audited_item_count: int
    matched_item_count: int
    persistent_bytes_mutated: int
    drifted_items: Tuple[str, ...]
    item_comparisons: Tuple[PostTrialItemParityRecord, ...]
    u5_sticky_boot_clean: bool
    u5_boot_img_byte8_zero_ok: bool
    h2_bk4_byte8: Optional[int]
    u5_zero_updater_mode_residue_ok: bool
    sticky_updater_residue: Tuple[str, ...]
    h1_telemetry_supplied: bool
    h1_telemetry_verified: bool
    h1_telemetry_audit: Optional[H1OrchestratorTelemetryAudit]
    h0_bundle_audit: RealTier0CaptureBundleAudit
    h2_bundle_audit: RealTier0CaptureBundleAudit
    errors: Tuple[str, ...]
    receipt_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class LifecycleFaultInjectionCase:
    fault_id: str
    description: str
    rejected_as_expected: bool
    persistent_bytes_mutated: int
    drifted_items: Tuple[str, ...]
    same_body_identity_verified: bool
    u5_sticky_boot_clean: bool
    h1_telemetry_verified: bool
    both_bundles_real_hardware_valid: bool
    primary_rejection_reason: str


@dataclass(frozen=True)
class StageAH0H1H2LifecycleDrillReport:
    schema: str
    phase_version: str
    verification_mode: str
    all_checks_passed: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    usb_or_camera_operations: int
    temp_dir_cleaned: bool
    h0_baseline_valid: bool
    h1_orchestrator_returncode: int
    h1_telemetry_audit: H1OrchestratorTelemetryAudit
    h1_cold_reboot_passthrough_ok: bool
    h1_cold_reboot_branch: str
    h1_cold_reboot_diag: str
    h2_nominal_zero_mutation_ok: bool
    h2_nominal_persistent_bytes_mutated: int
    h2_nominal_drifted_items: Tuple[str, ...]
    h2_nominal_u5_sticky_boot_clean: bool
    h2_nominal_receipt_sha256: str
    fault_injection_count: int
    fault_injections_all_rejected: bool
    fault_cases: Tuple[LifecycleFaultInjectionCase, ...]
    errors: Tuple[str, ...]
    drill_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


def _compute_canonical_sha256(payload: Mapping[str, object], exclude_key: str) -> str:
    body = dict(copy.deepcopy(payload))
    body.pop(exclude_key, None)
    raw = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def _stream_compare_two_files(
    h0_path: Optional[Path],
    h2_path: Optional[Path],
) -> Tuple[int, int, str, str, int]:
    """Stream-hash and byte-diff two files in fixed chunks.

    Returns `(h0_size, h2_size, h0_sha256, h2_sha256, differing_byte_count)`.
    """
    if h0_path is None or not h0_path.is_file() or h0_path.is_symlink():
        if h2_path is None or not h2_path.is_file() or h2_path.is_symlink():
            return 0, 0, "", "", 0
        h2_sz, h2_sha = _hash_single_file(h2_path)
        return 0, h2_sz, "", h2_sha, max(1, h2_sz)

    if h2_path is None or not h2_path.is_file() or h2_path.is_symlink():
        h0_sz, h0_sha = _hash_single_file(h0_path)
        return h0_sz, 0, h0_sha, "", max(1, h0_sz)

    d0 = hashlib.sha256()
    d2 = hashlib.sha256()
    sz0 = 0
    sz2 = 0
    diff_bytes = 0

    with h0_path.open("rb") as f0, h2_path.open("rb") as f2:
        while True:
            b0 = f0.read(STREAM_CHUNK_BYTES)
            b2 = f2.read(STREAM_CHUNK_BYTES)
            if not b0 and not b2:
                break
            if b0:
                sz0 += len(b0)
                d0.update(b0)
            if b2:
                sz2 += len(b2)
                d2.update(b2)
            if b0 == b2:
                continue
            common_len = min(len(b0), len(b2))
            if common_len > 0:
                mv0 = memoryview(b0)[:common_len]
                mv2 = memoryview(b2)[:common_len]
                for x, y in zip(mv0, mv2):
                    if x != y:
                        diff_bytes += 1
            diff_bytes += abs(len(b0) - len(b2))

    return sz0, sz2, d0.hexdigest(), d2.hexdigest(), diff_bytes


def _hash_single_file(path: Path) -> Tuple[int, str]:
    h = hashlib.sha256()
    sz = 0
    with path.open("rb") as fh:
        while True:
            blk = fh.read(STREAM_CHUNK_BYTES)
            if not blk:
                break
            sz += len(blk)
            h.update(blk)
    return sz, h.hexdigest()


def _parse_kv_lines(lines: Sequence[str]) -> Dict[str, str]:
    out: Dict[str, str] = {}
    for raw in lines:
        ln = raw.strip()
        if not ln or ln.startswith("#") or "=" not in ln:
            continue
        k, v = ln.split("=", 1)
        out[k.strip()] = v.strip()
    return out


def _read_nonempty_lines(path: Path) -> Tuple[str, ...]:
    if not path.is_file():
        return ()
    return tuple(ln.strip() for ln in path.read_text(encoding="utf-8").splitlines() if ln.strip())


def serialize_h1_orchestrator_telemetry_from_sandbox(sandbox_root: Path) -> Dict[str, object]:
    """Capture structured H1 telemetry from a `PREFIX`-isolated `30-stage-a-orchestrator.sh` sandbox."""
    tmp_dir = sandbox_root / "tmp"
    state = _parse_kv_lines(_read_nonempty_lines(tmp_dir / "stage_a_orchestrator_state.env"))
    forward_steps = list(_read_nonempty_lines(tmp_dir / "stage_a_forward_steps.log"))
    unwind_steps = list(_read_nonempty_lines(tmp_dir / "stage_a_unwind_steps.log"))
    events = list(_read_nonempty_lines(tmp_dir / "mock_events.log"))
    mounts_after = list(_read_nonempty_lines(tmp_dir / "mock_mounts.tbl"))
    loops_after = list(_read_nonempty_lines(tmp_dir / "mock_loops.tbl"))
    kmods_after = list(_read_nonempty_lines(tmp_dir / "mock_kmods.tbl"))
    wbi_writes = list(_read_nonempty_lines(tmp_dir / "mock_wbi_writes.log"))
    wbi_blocked = list(_read_nonempty_lines(tmp_dir / "mock_wbi_blocked.log"))
    violations = list(_read_nonempty_lines(tmp_dir / "mock_sandbox_violations.log"))
    emmc_writes = list(_read_nonempty_lines(tmp_dir / "mock_emmc_writes.log"))

    return {
        "schema": H1_TELEMETRY_SCHEMA,
        "boot_branch": state.get("BOOT_BRANCH", "MISSING"),
        "diag_code": state.get("DIAG_CODE", "MISSING"),
        "stock_boot_invoked": state.get("STOCK_BOOT_INVOKED") == "1",
        "im_elf_invoked": state.get("IM_ELF_INVOKED") == "1",
        "token_cleared_before_exec": state.get("TOKEN_CLEARED_BEFORE_EXEC") == "1",
        "token_present_after": (tmp_dir / "mod_arm_once").exists(),
        "wbi_guard_verified": state.get("WBI_GUARD_VERIFIED") == "1",
        "wbi_hibernation_masked": state.get("WBI_HIBERNATION_MASKED") == "1",
        "lingering_wbi_inhibit_lock": (
            sandbox_root / "tmp_wbshd" / "stage_a_wbi_inhibit.lock"
        ).exists(),
        "double_mount_prevented": state.get("DOUBLE_MOUNT_PREVENTED") == "1",
        "verified_digest_count": int(state.get("VERIFIED_DIGEST_COUNT", "0")),
        "forward_steps": forward_steps,
        "unwind_steps": unwind_steps,
        "events": events,
        "wbi_blocked_events": wbi_blocked,
        "lingering_mount_count": len(mounts_after),
        "lingering_loop_count": len(loops_after),
        "lingering_kmod_count": len(kmods_after),
        "emmc_write_count": len(emmc_writes),
        "wbi_write_count": len(wbi_writes),
        "sandbox_violation_count": len(violations),
    }


def verify_h1_orchestrator_telemetry(
    telemetry_source: Path | str | Mapping[str, object],
) -> H1OrchestratorTelemetryAudit:
    """Validate Phase H1 `30-stage-a-orchestrator.sh` execution telemetry fail-closed.

    Accepts:
    - A `Mapping` or JSON file/string matching `stage_a_h1_telemetry_v1`,
    - A `PREFIX` sandbox directory containing `tmp/stage_a_orchestrator_state.env` & step logs, or
    - Structured key/value telemetry log text (`BOOT_BRANCH=...`, `FORWARD_STEP=...`, `UNWIND_STEP=...`).
    """
    errors: List[str] = []
    source_kind = "invalid"
    data: Dict[str, object] = {}

    if isinstance(telemetry_source, Mapping):
        source_kind = "json_mapping"
        data = dict(telemetry_source)
    elif isinstance(telemetry_source, Path) or (
        isinstance(telemetry_source, str)
        and "\n" not in telemetry_source
        and not telemetry_source.lstrip().startswith("{")
    ):
        p = Path(telemetry_source)
        if not p.exists() or p.is_symlink():
            return H1OrchestratorTelemetryAudit(
                valid=False,
                source_kind="missing_or_symlink",
                boot_branch="",
                diag_code="",
                clear_before_exec_ok=False,
                token_cleared_before_exec=False,
                token_present_after=True,
                no_mount_or_insmod_before_token_unlink=False,
                wbi_hibernation_guard_ok=False,
                wbi_guard_verified=False,
                lingering_wbi_inhibit_lock=False,
                verify_before_mount_ok=False,
                verified_digest_count=0,
                forward_steps_ok=False,
                forward_steps=(),
                lifo_unwind_ok=False,
                unwind_steps=(),
                im_elf_invoked=False,
                zero_persistent_writes_ok=False,
                emmc_write_count=0,
                wbi_write_count=0,
                sandbox_violation_count=0,
                lingering_mount_count=0,
                lingering_loop_count=0,
                lingering_kmod_count=0,
                errors=(f"H1 telemetry path does not exist or is a symlink: {p}",),
            )
        if p.is_dir():
            source_kind = "sandbox_dir"
            data = serialize_h1_orchestrator_telemetry_from_sandbox(p)
        else:
            raw_text = p.read_text(encoding="utf-8")
            source_kind, data, parse_errs = _parse_telemetry_text(raw_text)
            errors.extend(parse_errs)
    else:
        source_kind, data, parse_errs = _parse_telemetry_text(str(telemetry_source))
        errors.extend(parse_errs)

    boot_branch = str(data.get("boot_branch", ""))
    diag_code = str(data.get("diag_code", ""))
    tok_cleared = bool(data.get("token_cleared_before_exec", False))
    tok_after = bool(data.get("token_present_after", False))
    wbi_guard = bool(data.get("wbi_guard_verified", False))
    lingering_wbi_lock = bool(data.get("lingering_wbi_inhibit_lock", False))
    im_invoked = bool(data.get("im_elf_invoked", False))

    try:
        verified_cnt = int(data.get("verified_digest_count", 0))  # type: ignore[arg-type]
    except (TypeError, ValueError):
        verified_cnt = 0
        errors.append("Invalid integer for verified_digest_count")

    forward_raw = data.get("forward_steps", ())
    unwind_raw = data.get("unwind_steps", ())
    events_raw = data.get("events", ())
    forward_steps = tuple(str(x) for x in forward_raw) if isinstance(forward_raw, (list, tuple)) else ()
    unwind_steps = tuple(str(x) for x in unwind_raw) if isinstance(unwind_raw, (list, tuple)) else ()
    events = tuple(str(x) for x in events_raw) if isinstance(events_raw, (list, tuple)) else ()

    emmc_writes = int(data.get("emmc_write_count", 0))  # type: ignore[arg-type]
    wbi_writes = int(data.get("wbi_write_count", 0))  # type: ignore[arg-type]
    violations = int(data.get("sandbox_violation_count", 0))  # type: ignore[arg-type]
    lingering_mounts = int(data.get("lingering_mount_count", 0))  # type: ignore[arg-type]
    lingering_loops = int(data.get("lingering_loop_count", 0))  # type: ignore[arg-type]
    lingering_kmods = int(data.get("lingering_kmod_count", 0))  # type: ignore[arg-type]

    # 1. Clear-Before-Exec check (state flags + event-trace ordering)
    no_mount_before_unlink = True
    seen_sync_unlinked = False
    for ev in events:
        if ev.startswith("SYNC|"):
            if "arm_token_absent=0" in ev:
                no_mount_before_unlink = False
                errors.append(f"H1 telemetry violation: /tmp/mod_arm_once still present at initial sync ({ev})")
            elif "arm_token_absent=1" in ev:
                seen_sync_unlinked = True
        elif ev.startswith(("INSMOD|", "LOSETUP_ATTACH|", "MOUNT|")):
            if "arm_token_absent=0" in ev:
                no_mount_before_unlink = False
                errors.append(f"H1 telemetry violation: mount/insmod executed while /tmp/mod_arm_once existed ({ev})")
            if any(e.startswith("SYNC|") for e in events) and not seen_sync_unlinked:
                no_mount_before_unlink = False
                errors.append(f"H1 telemetry violation: {ev} preceded Clear-Before-Exec token unlink sync")

    clear_ok = tok_cleared and (not tok_after) and no_mount_before_unlink
    if not tok_cleared:
        errors.append("H1 telemetry missing Clear-Before-Exec confirmation (token_cleared_before_exec != True)")
    if tok_after:
        errors.append("H1 telemetry violation: /tmp/mod_arm_once remained present after execution")

    # 2. WBI hibernation guard check
    has_wbi_event_violation = any(
        "FORBIDDEN_WBI" in ev or "UNMASKED_WBI_WRITE" in ev for ev in events
    )
    wbi_ok = wbi_guard and wbi_writes == 0 and (not lingering_wbi_lock) and (not has_wbi_event_violation)
    if not wbi_guard:
        errors.append("H1 telemetry missing WBI hibernation safety guard confirmation (wbi_guard_verified != True)")
    if wbi_writes != 0 or has_wbi_event_violation:
        errors.append(f"H1 telemetry detected WBI (p5:/dev/nflasha5) write/mount violation (wbi_write_count={wbi_writes})")
    if lingering_wbi_lock:
        errors.append("H1 telemetry detected lingering /tmp_wbshd/stage_a_wbi_inhibit.lock after teardown")

    # 3. Verify-Before-Mount (11/11 SHA-256 checks)
    verify_ok = verified_cnt == EXPECTED_H1_VERIFIED_DIGEST_COUNT
    if not verify_ok:
        errors.append(
            f"H1 Verify-Before-Mount digest count {verified_cnt} != expected {EXPECTED_H1_VERIFIED_DIGEST_COUNT}"
        )

    # 4. Forward steps 1..10
    forward_ok = forward_steps == EXPECTED_STAGE_A_FORWARD_STEP_IDS
    if not forward_ok:
        errors.append(
            f"H1 forward activation steps {forward_steps!r} != canonical 1..10 {EXPECTED_STAGE_A_FORWARD_STEP_IDS!r}"
        )

    # 5. Reverse 10..1 LIFO unwind & zero lingering mounts/loops/kmods
    lifo_ok = (
        unwind_steps == EXPECTED_STAGE_A_LIFO_UNWIND_STEP_IDS
        and lingering_mounts == 0
        and lingering_loops == 0
        and lingering_kmods == 0
    )
    if unwind_steps != EXPECTED_STAGE_A_LIFO_UNWIND_STEP_IDS:
        errors.append(
            f"H1 unwind steps {unwind_steps!r} != exact reverse 10..1 LIFO {EXPECTED_STAGE_A_LIFO_UNWIND_STEP_IDS!r}"
        )
    if lingering_mounts != 0 or lingering_loops != 0 or lingering_kmods != 0:
        errors.append(
            f"H1 teardown left lingering state (mounts={lingering_mounts}, loops={lingering_loops}, kmods={lingering_kmods})"
        )

    if boot_branch != "STAGE_A_ADAPTED_CLEAN_EXIT":
        errors.append(f"Expected H1 boot_branch 'STAGE_A_ADAPTED_CLEAN_EXIT', got {boot_branch!r}")
    if diag_code != "OK_STAGE_A_LIFO_TEARDOWN_CLEAN":
        errors.append(f"Expected H1 diag_code 'OK_STAGE_A_LIFO_TEARDOWN_CLEAN', got {diag_code!r}")
    if not im_invoked:
        errors.append("H1 telemetry indicates im.elf handoff did not occur (im_elf_invoked != True)")

    zero_writes_ok = emmc_writes == 0 and wbi_writes == 0 and violations == 0
    if not zero_writes_ok:
        errors.append(
            f"H1 telemetry reported non-zero writes/violations (emmc={emmc_writes}, wbi={wbi_writes}, sandbox={violations})"
        )

    all_ok = (
        clear_ok
        and wbi_ok
        and verify_ok
        and forward_ok
        and lifo_ok
        and boot_branch == "STAGE_A_ADAPTED_CLEAN_EXIT"
        and diag_code == "OK_STAGE_A_LIFO_TEARDOWN_CLEAN"
        and im_invoked
        and zero_writes_ok
        and len(errors) == 0
    )

    return H1OrchestratorTelemetryAudit(
        valid=all_ok,
        source_kind=source_kind,
        boot_branch=boot_branch,
        diag_code=diag_code,
        clear_before_exec_ok=clear_ok,
        token_cleared_before_exec=tok_cleared,
        token_present_after=tok_after,
        no_mount_or_insmod_before_token_unlink=no_mount_before_unlink,
        wbi_hibernation_guard_ok=wbi_ok,
        wbi_guard_verified=wbi_guard,
        lingering_wbi_inhibit_lock=lingering_wbi_lock,
        verify_before_mount_ok=verify_ok,
        verified_digest_count=verified_cnt,
        forward_steps_ok=forward_ok,
        forward_steps=forward_steps,
        lifo_unwind_ok=lifo_ok,
        unwind_steps=unwind_steps,
        im_elf_invoked=im_invoked,
        zero_persistent_writes_ok=zero_writes_ok,
        emmc_write_count=emmc_writes,
        wbi_write_count=wbi_writes,
        sandbox_violation_count=violations,
        lingering_mount_count=lingering_mounts,
        lingering_loop_count=lingering_loops,
        lingering_kmod_count=lingering_kmods,
        errors=tuple(errors),
    )


def _parse_telemetry_text(raw_text: str) -> Tuple[str, Dict[str, object], List[str]]:
    stripped = raw_text.strip()
    if not stripped:
        return "empty", {}, ["Empty H1 telemetry log content"]
    if stripped.startswith("{"):
        try:
            parsed = json.loads(stripped)
            if not isinstance(parsed, dict):
                return "invalid_json_root", {}, ["H1 JSON telemetry root must be an object"]
            return "json", parsed, []
        except Exception as exc:
            return "invalid_json", {}, [f"Malformed H1 telemetry JSON: {exc}"]

    # Structured line-oriented log parser
    lines = [ln.strip() for ln in stripped.splitlines() if ln.strip() and not ln.strip().startswith("#")]
    kv = _parse_kv_lines(lines)
    fwd: List[str] = []
    unw: List[str] = []
    evs: List[str] = []
    for ln in lines:
        if ln.startswith("FORWARD_STEP="):
            fwd.append(ln.split("=", 1)[1].strip())
        elif ln.startswith("UNWIND_STEP="):
            unw.append(ln.split("=", 1)[1].strip())
        elif ln.startswith("EVENT="):
            evs.append(ln.split("=", 1)[1].strip())

    def _as_bool(val: Optional[str]) -> bool:
        return str(val or "").strip().lower() in ("1", "true", "yes")

    data: Dict[str, object] = {
        "boot_branch": kv.get("BOOT_BRANCH", ""),
        "diag_code": kv.get("DIAG_CODE", ""),
        "im_elf_invoked": _as_bool(kv.get("IM_ELF_INVOKED")),
        "token_cleared_before_exec": _as_bool(kv.get("TOKEN_CLEARED_BEFORE_EXEC")),
        "token_present_after": _as_bool(kv.get("TOKEN_PRESENT_AFTER")),
        "wbi_guard_verified": _as_bool(kv.get("WBI_GUARD_VERIFIED")),
        "lingering_wbi_inhibit_lock": _as_bool(kv.get("LINGERING_WBI_INHIBIT_LOCK")),
        "verified_digest_count": int(kv.get("VERIFIED_DIGEST_COUNT", "0") or "0"),
        "forward_steps": fwd,
        "unwind_steps": unw,
        "events": evs,
        "lingering_mount_count": int(kv.get("LINGERING_MOUNT_COUNT", "0") or "0"),
        "lingering_loop_count": int(kv.get("LINGERING_LOOP_COUNT", "0") or "0"),
        "lingering_kmod_count": int(kv.get("LINGERING_KMOD_COUNT", "0") or "0"),
        "emmc_write_count": int(kv.get("EMMC_WRITE_COUNT", "0") or "0"),
        "wbi_write_count": int(kv.get("WBI_WRITE_COUNT", "0") or "0"),
        "sandbox_violation_count": int(kv.get("SANDBOX_VIOLATION_COUNT", "0") or "0"),
    }
    return "structured_log", data, []


def _load_manifest_dict_if_valid(bundle_dir: Path) -> Dict[str, object]:
    mpath = bundle_dir / "backup-manifest.json"
    if not mpath.exists() or mpath.is_symlink() or not mpath.is_file():
        return {}
    try:
        obj = json.loads(mpath.read_text(encoding="utf-8"))
        return obj if isinstance(obj, dict) else {}
    except Exception:
        return {}


def _resolve_item_filename(
    manifest: Mapping[str, object],
    section_key: str,
    item_key: str,
    default_fn: str,
) -> str:
    sec = manifest.get(section_key)
    if isinstance(sec, Mapping):
        ent = sec.get(item_key)
        if isinstance(ent, Mapping):
            cand = str(ent.get("file_name", default_fn))
            if SAFE_FILENAME_RE.fullmatch(cand) and cand not in (".", ".."):
                return cand
    return default_fn


def _audit_h2_u5_sticky_boot_cleanliness(
    h2_dir: Path,
    h2_manifest: Mapping[str, object],
) -> Tuple[bool, bool, Optional[int], bool, Tuple[str, ...], List[str]]:
    """Verify `U5` sticky-boot cleanliness on H2 (`boot_img` byte `+8 == 0x00` & zero updater residue)."""
    errors: List[str] = []

    # 1. Inspect `p2_backup_bin.bin` `BK4\0` active selector byte `+8` across Record 0 (and Record 1 if present)
    p2_fn = _resolve_item_filename(
        h2_manifest,
        "items",
        "p2_backup_bin",
        str(TIER0_CANONICAL_SOURCES["p2_backup_bin"]["output_name"]),
    )
    p2_path = h2_dir / p2_fn
    byte8_val: Optional[int] = None
    byte8_ok = False
    if p2_path.exists() and (not p2_path.is_symlink()) and p2_path.is_file():
        p2_bytes = p2_path.read_bytes()
        if len(p2_bytes) >= BK4_HEADER_SIZE and p2_bytes[0x0C:0x10] == BK4_MAGIC:
            byte8_val = int(p2_bytes[0x08])
            rec0, rec0_errs = parse_bk4_record(p2_bytes, offset=0, record_index=0)
            if rec0 is None or rec0_errs:
                errors.append(f"U5 H2 p2_backup_bin Record 0 invalid: {rec0_errs}")
            elif rec0.active_byte8 != 0x00:
                errors.append(
                    f"U5 sticky boot_img violation: H2 p2_backup_bin Record 0 byte +8 == 0x{rec0.active_byte8:02x} (expected 0x00)"
                )
            else:
                # Also check Record 1 if a second BK4 record follows Record 0
                rec1_bad = False
                next_off = rec0.total_bytes
                if next_off + BK4_HEADER_SIZE <= len(p2_bytes) and p2_bytes[next_off + 0x0C : next_off + 0x10] == BK4_MAGIC:
                    rec1_b8 = int(p2_bytes[next_off + 0x08])
                    if rec1_b8 != 0x00:
                        byte8_val = rec1_b8
                        rec1_bad = True
                        errors.append(
                            f"U5 sticky boot_img violation: H2 p2_backup_bin Record 1 byte +8 == 0x{rec1_b8:02x} (expected 0x00)"
                        )
                if not rec1_bad:
                    byte8_ok = True
        else:
            errors.append("U5 H2 p2_backup_bin missing valid BK4\\0 header at Record 0")
    else:
        errors.append(f"U5 H2 p2_backup_bin missing at {p2_fn}")

    # 2. Scan H2 directory tree and manifest metadata for sticky `/setting/updater/mode*` residue
    residue: List[str] = []
    if h2_dir.exists() and (not h2_dir.is_symlink()) and h2_dir.is_dir():
        for root, _dirs, files in os.walk(h2_dir, followlinks=False):
            root_p = Path(root)
            for fname in sorted(files):
                rel = (root_p / fname).relative_to(h2_dir).as_posix()
                if STICKY_UPDATER_RELPATH_RE.search(rel):
                    residue.append(rel)

    for mkey in ("sticky_updater_mode_files", "setting_updater_mode_files"):
        mval = h2_manifest.get(mkey)
        if isinstance(mval, list):
            for item in mval:
                s = str(item).strip()
                if s and s not in residue:
                    residue.append(s)

    u5_state = h2_manifest.get("u5_updater_state")
    if isinstance(u5_state, Mapping):
        mfiles = u5_state.get("mode_files")
        if isinstance(mfiles, list):
            for item in mfiles:
                s = str(item).strip()
                if s and s not in residue:
                    residue.append(s)
        ank_mode = u5_state.get("ank_sub_lsi_mode", 0)
        if ank_mode != 0:
            tag = f"ank_sub_lsi_mode={ank_mode}"
            residue.append(tag)

    residue_sorted = tuple(sorted(residue))
    zero_residue_ok = len(residue_sorted) == 0
    if not zero_residue_ok:
        errors.append(
            f"U5 sticky updater residue detected in H2: {list(residue_sorted)!r} "
            "(mandatory 2-step reset `rm -f /setting/updater/mode* && sync` + `ud_send_lsi.elf 0` required)"
        )

    u5_clean = byte8_ok and zero_residue_ok
    return u5_clean, byte8_ok, byte8_val, zero_residue_ok, residue_sorted, errors


def recompute_bk4_record0_checksum(p2_bytes: bytes) -> bytes:
    """Recompute the 32-bit unsigned byte-sum checksum at `+0x20..+0x24` of Record 0 in `Backup.bin`."""
    if len(p2_bytes) < BK4_HEADER_SIZE or p2_bytes[0x0C:0x10] != BK4_MAGIC:
        raise ValueError("Buffer does not start with a valid 256-byte BK4\\0 header")
    dataoff, datasize = struct.unpack_from("<II", p2_bytes, 0x18)
    total_bytes = dataoff + datasize
    if dataoff < BK4_HEADER_SIZE or total_bytes > len(p2_bytes):
        raise ValueError("BK4 Record 0 span exceeds buffer length")
    buf = bytearray(p2_bytes)
    csum = (sum(buf[0:0x20]) + sum(buf[0x24:total_bytes])) & 0xFFFFFFFF
    struct.pack_into("<I", buf, 0x20, csum)
    return bytes(buf)


def verify_post_trial_zero_mutation(
    h0_bundle_dir: Path | str,
    h2_bundle_dir: Path | str,
    h1_telemetry_log_path: Optional[Path | str] = None,
    *,
    h1_telemetry_text: Optional[str] = None,
) -> StageAPostTrialReceipt:
    """Verify bit-exact post-power-cycle zero-mutation parity between Phase H0 and Phase H2.

    Produces a deterministic `stage_a_post_trial_receipt_v1` receipt with
    `persistent_emmc_writes_authorized = False` hard-locked.
    """
    h0_dir = Path(h0_bundle_dir)
    h2_dir = Path(h2_bundle_dir)
    errors: List[str] = []

    distinct_dirs_ok = True
    if h0_dir.exists() and h2_dir.exists():
        if h0_dir.resolve() == h2_dir.resolve():
            distinct_dirs_ok = False
            errors.append(
                "h0_bundle_dir and h2_bundle_dir resolve to the identical directory; "
                "Phase H2 must be an independent post-power-cycle Tier-0 readback capture"
            )

    # 1. Validate BOTH H0 and H2 via `verify_real_tier0_capture_bundle`
    h0_audit = verify_real_tier0_capture_bundle(h0_dir)
    h2_audit = verify_real_tier0_capture_bundle(h2_dir)
    if not h0_audit.valid:
        errors.extend(f"h0-bundle: {e}" for e in h0_audit.errors)
    if not h2_audit.valid:
        errors.extend(f"h2-bundle: {e}" for e in h2_audit.errors)

    both_real_valid = (
        h0_audit.valid
        and h0_audit.is_non_synthetic_hardware
        and h2_audit.valid
        and h2_audit.is_non_synthetic_hardware
    )

    # 2. Same-body hardware identity check
    same_body_ok = (
        h0_audit.is_non_synthetic_hardware
        and h2_audit.is_non_synthetic_hardware
        and h0_audit.model_id == FX3_MODEL_ID_HEX
        and h2_audit.model_id == FX3_MODEL_ID_HEX
        and bool(h0_audit.body_serial)
        and h0_audit.body_serial == h2_audit.body_serial
        and bool(h0_audit.emmc_cid)
        and h0_audit.emmc_cid.lower() == h2_audit.emmc_cid.lower()
        and bool(h0_audit.camera_body_tag)
        and h0_audit.camera_body_tag == h2_audit.camera_body_tag
    )
    if not same_body_ok:
        if h0_audit.body_serial != h2_audit.body_serial:
            errors.append(
                f"Same-body serial mismatch: H0 body_serial={h0_audit.body_serial!r} vs H2 body_serial={h2_audit.body_serial!r}"
            )
        if h0_audit.emmc_cid.lower() != h2_audit.emmc_cid.lower():
            errors.append(
                f"Same-body eMMC CID mismatch: H0 cid={h0_audit.emmc_cid!r} vs H2 cid={h2_audit.emmc_cid!r}"
            )
        if h0_audit.camera_body_tag != h2_audit.camera_body_tag:
            errors.append("Same-body camera_body_tag digest mismatch between H0 and H2")

    # 3. Stream-compare all 11 mandatory Tier-0 items + 2 mandatory redline header probes (13 total)
    h0_manifest = _load_manifest_dict_if_valid(h0_dir)
    h2_manifest = _load_manifest_dict_if_valid(h2_dir)

    comparisons: List[PostTrialItemParityRecord] = []
    drifted: List[str] = []
    total_mutated_bytes = 0

    audited_specs: List[Tuple[str, str, str, str]] = [
        (
            key,
            "tier0_partition",
            "items",
            str(TIER0_CANONICAL_SOURCES[key]["output_name"]),
        )
        for key in TIER0_REQUIRED_BACKUPS
    ] + [
        (
            probe_key,
            "redline_header_probe",
            "redline_headers",
            default_fn,
        )
        for probe_key, default_fn in REQUIRED_REDLINE_HEADER_PROBES.items()
    ]

    for item_id, category, sec_name, default_fn in audited_specs:
        fn0 = _resolve_item_filename(h0_manifest, sec_name, item_id, default_fn)
        fn2 = _resolve_item_filename(h2_manifest, sec_name, item_id, default_fn)
        p0 = (h0_dir / fn0) if h0_dir.is_dir() and not h0_dir.is_symlink() else None
        p2 = (h2_dir / fn2) if h2_dir.is_dir() and not h2_dir.is_symlink() else None

        sz0, sz2, sha0, sha2, diff_b = _stream_compare_two_files(p0, p2)
        matched = (
            sz0 > 0
            and sz0 == sz2
            and bool(sha0)
            and sha0 == sha2
            and diff_b == 0
        )
        if not matched:
            mutated_cnt = diff_b if diff_b > 0 else 1
            total_mutated_bytes += mutated_cnt
            drifted.append(item_id)
            errors.append(
                f"Post-trial drift on {item_id} ({fn2}): "
                f"h0=({sz0} B, {sha0[:16]}...) vs h2=({sz2} B, {sha2[:16]}...), diff_bytes={mutated_cnt}"
            )

        comparisons.append(
            PostTrialItemParityRecord(
                item_id=item_id,
                category=category,
                file_name=fn2,
                h0_bytes=sz0,
                h2_bytes=sz2,
                h0_sha256=sha0,
                h2_sha256=sha2,
                differing_bytes=diff_b,
                bit_exact_match=matched,
            )
        )

    matched_count = sum(1 for c in comparisons if c.bit_exact_match)

    # 4. U5 sticky-boot cleanliness on H2
    (
        u5_clean,
        u5_byte8_ok,
        h2_byte8,
        u5_no_residue_ok,
        u5_residue,
        u5_errs,
    ) = _audit_h2_u5_sticky_boot_cleanliness(h2_dir, h2_manifest)
    errors.extend(u5_errs)

    # 5. Optional H1 orchestrator telemetry verification
    h1_supplied = (h1_telemetry_log_path is not None) or (h1_telemetry_text is not None)
    h1_audit: Optional[H1OrchestratorTelemetryAudit] = None
    h1_ok = False
    if h1_supplied:
        src = h1_telemetry_log_path if h1_telemetry_log_path is not None else str(h1_telemetry_text)
        h1_audit = verify_h1_orchestrator_telemetry(src)
        h1_ok = h1_audit.valid
        if not h1_audit.valid:
            errors.extend(f"h1-telemetry: {e}" for e in h1_audit.errors)

    zero_mutation_ok = (
        distinct_dirs_ok
        and both_real_valid
        and same_body_ok
        and total_mutated_bytes == 0
        and len(drifted) == 0
        and matched_count == len(audited_specs)
        and u5_clean
    )
    all_passed = zero_mutation_ok and ((not h1_supplied) or h1_ok) and len(errors) == 0

    draft = StageAPostTrialReceipt(
        schema=POST_TRIAL_RECEIPT_SCHEMA,
        phase_version=PHASE_16_VERSION,
        all_checks_passed=all_passed,
        zero_mutation_verified=zero_mutation_ok,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        usb_or_camera_operations=0,
        distinct_capture_dirs_ok=distinct_dirs_ok,
        h0_bundle_valid=h0_audit.valid,
        h2_bundle_valid=h2_audit.valid,
        both_bundles_real_hardware_valid=both_real_valid,
        same_body_identity_verified=same_body_ok,
        model_id=h2_audit.model_id or h0_audit.model_id,
        body_serial=h0_audit.body_serial if same_body_ok else f"{h0_audit.body_serial}!={h2_audit.body_serial}",
        emmc_cid=h0_audit.emmc_cid if same_body_ok else f"{h0_audit.emmc_cid}!={h2_audit.emmc_cid}",
        camera_body_tag=h0_audit.camera_body_tag if same_body_ok else "",
        audited_item_count=len(audited_specs),
        matched_item_count=matched_count,
        persistent_bytes_mutated=total_mutated_bytes,
        drifted_items=tuple(drifted),
        item_comparisons=tuple(comparisons),
        u5_sticky_boot_clean=u5_clean,
        u5_boot_img_byte8_zero_ok=u5_byte8_ok,
        h2_bk4_byte8=h2_byte8,
        u5_zero_updater_mode_residue_ok=u5_no_residue_ok,
        sticky_updater_residue=u5_residue,
        h1_telemetry_supplied=h1_supplied,
        h1_telemetry_verified=h1_ok,
        h1_telemetry_audit=h1_audit,
        h0_bundle_audit=h0_audit,
        h2_bundle_audit=h2_audit,
        errors=tuple(errors),
        receipt_sha256="",
    )
    receipt_sha = _compute_canonical_sha256(draft.to_dict(), "receipt_sha256")

    return StageAPostTrialReceipt(
        schema=draft.schema,
        phase_version=draft.phase_version,
        all_checks_passed=draft.all_checks_passed,
        zero_mutation_verified=draft.zero_mutation_verified,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        usb_or_camera_operations=0,
        distinct_capture_dirs_ok=draft.distinct_capture_dirs_ok,
        h0_bundle_valid=draft.h0_bundle_valid,
        h2_bundle_valid=draft.h2_bundle_valid,
        both_bundles_real_hardware_valid=draft.both_bundles_real_hardware_valid,
        same_body_identity_verified=draft.same_body_identity_verified,
        model_id=draft.model_id,
        body_serial=draft.body_serial,
        emmc_cid=draft.emmc_cid,
        camera_body_tag=draft.camera_body_tag,
        audited_item_count=draft.audited_item_count,
        matched_item_count=draft.matched_item_count,
        persistent_bytes_mutated=draft.persistent_bytes_mutated,
        drifted_items=draft.drifted_items,
        item_comparisons=draft.item_comparisons,
        u5_sticky_boot_clean=draft.u5_sticky_boot_clean,
        u5_boot_img_byte8_zero_ok=draft.u5_boot_img_byte8_zero_ok,
        h2_bk4_byte8=draft.h2_bk4_byte8,
        u5_zero_updater_mode_residue_ok=draft.u5_zero_updater_mode_residue_ok,
        sticky_updater_residue=draft.sticky_updater_residue,
        h1_telemetry_supplied=draft.h1_telemetry_supplied,
        h1_telemetry_verified=draft.h1_telemetry_verified,
        h1_telemetry_audit=draft.h1_telemetry_audit,
        h0_bundle_audit=draft.h0_bundle_audit,
        h2_bundle_audit=draft.h2_bundle_audit,
        errors=draft.errors,
        receipt_sha256=receipt_sha,
    )


def _install_lifecycle_mock_bin(mock_bin: Path, sandbox_root: Path) -> None:
    """Install sandboxed `busybox` + `wbi_hibernation_probe` recording Clear-Before-Exec event ordering."""
    mock_bin.mkdir(parents=True, exist_ok=True)
    bb_script = mock_bin / "busybox"
    bb_script.write_text(
        f"""#!/bin/sh
set -u
SANDBOX_ROOT="{sandbox_root}"
MNT_TABLE="${{SANDBOX_ROOT}}/tmp/mock_mounts.tbl"
LOOP_TABLE="${{SANDBOX_ROOT}}/tmp/mock_loops.tbl"
KMOD_TABLE="${{SANDBOX_ROOT}}/tmp/mock_kmods.tbl"
EVENT_LOG="${{SANDBOX_ROOT}}/tmp/mock_events.log"
VIOLATIONS="${{SANDBOX_ROOT}}/tmp/mock_sandbox_violations.log"
WBI_VIOLATIONS="${{SANDBOX_ROOT}}/tmp/mock_wbi_writes.log"
mkdir -p "${{SANDBOX_ROOT}}/tmp"
touch "$MNT_TABLE" "$LOOP_TABLE" "$KMOD_TABLE" "$EVENT_LOG"

arm_absent_flag() {{
    if [ -e "${{SANDBOX_ROOT}}/tmp/mod_arm_once" ]; then
        echo "0"
    else
        echo "1"
    fi
}}

check_sandbox_path() {{
    P="$1"
    [ -z "$P" ] && return 0
    case "$P" in
        "$SANDBOX_ROOT"/*|vfat|tmpfs|proc|sysfs|none|-*)
            return 0
            ;;
        /*)
            echo "OUTSIDE_SANDBOX:$P" >> "$VIOLATIONS"
            exit 98
            ;;
    esac
}}

SUBCMD="${{1:-}}"
shift || true

case "$SUBCMD" in
    sync)
        ABS=$(arm_absent_flag)
        echo "SYNC|arm_token_absent=${{ABS}}" >> "$EVENT_LOG"
        exit 0
        ;;
    insmod)
        KO_PATH="${{1:-}}"
        check_sandbox_path "$KO_PATH"
        [ -f "$KO_PATH" ] || exit 2
        ABS=$(arm_absent_flag)
        MOD_BASE=$(basename "$KO_PATH" .ko)
        echo "INSMOD|arm_token_absent=${{ABS}}|$MOD_BASE" >> "$EVENT_LOG"
        echo "$MOD_BASE|$KO_PATH" >> "$KMOD_TABLE"
        exit 0
        ;;
    rmmod)
        MOD_NAME="${{1:-}}"
        echo "RMMOD|$MOD_NAME" >> "$EVENT_LOG"
        if [ -f "$KMOD_TABLE" ]; then
            grep -v "^${{MOD_NAME}}|" "$KMOD_TABLE" > "${{KMOD_TABLE}}.tmp" || true
            mv "${{KMOD_TABLE}}.tmp" "$KMOD_TABLE"
        fi
        exit 0
        ;;
    losetup)
        if [ "${{1:-}}" = "-d" ]; then
            LDEV="${{2:-}}"
            check_sandbox_path "$LDEV"
            echo "LOSETUP_DETACH|loop7" >> "$EVENT_LOG"
            if [ -f "$LOOP_TABLE" ]; then
                grep -v "^${{LDEV}}|" "$LOOP_TABLE" > "${{LOOP_TABLE}}.tmp" || true
                mv "${{LOOP_TABLE}}.tmp" "$LOOP_TABLE"
            fi
            rm -f "$LDEV"
            exit 0
        fi
        LDEV="${{1:-}}"
        IMG="${{2:-}}"
        check_sandbox_path "$LDEV"
        check_sandbox_path "$IMG"
        [ -f "$IMG" ] || exit 2
        ABS=$(arm_absent_flag)
        echo "LOSETUP_ATTACH|arm_token_absent=${{ABS}}|loop7" >> "$EVENT_LOG"
        echo "$LDEV|$IMG" > "$LDEV"
        echo "$LDEV|$IMG" >> "$LOOP_TABLE"
        exit 0
        ;;
    mount)
        IS_BIND=0
        IS_RO=0
        POS_1=""
        POS_2=""
        while [ $# -gt 0 ]; do
            case "$1" in
                --bind)
                    IS_BIND=1
                    shift
                    ;;
                -t)
                    shift 2
                    ;;
                -o)
                    case "${{2:-}}" in
                        *ro*) IS_RO=1 ;;
                    esac
                    shift 2
                    ;;
                -*)
                    shift
                    ;;
                *)
                    if [ -z "$POS_1" ]; then
                        POS_1="$1"
                    else
                        POS_2="$1"
                    fi
                    shift
                    ;;
            esac
        done
        check_sandbox_path "$POS_1"
        check_sandbox_path "$POS_2"
        case "$POS_1$POS_2" in
            *nflasha5*|*/wbi*)
                echo "FORBIDDEN_WBI_MOUNT|$POS_1|$POS_2" >> "$WBI_VIOLATIONS"
                exit 91
                ;;
        esac
        if [ "$IS_RO" -ne 1 ]; then
            echo "NON_RO_MOUNT_REJECTED|$POS_1|$POS_2" >> "$VIOLATIONS"
            exit 92
        fi
        [ -e "$POS_1" ] || exit 3
        ABS=$(arm_absent_flag)
        REL_DST="${{POS_2#$SANDBOX_ROOT}}"
        echo "MOUNT|arm_token_absent=${{ABS}}|bind=${{IS_BIND}}|ro=${{IS_RO}}|$REL_DST" >> "$EVENT_LOG"
        echo "$POS_2|$POS_1" >> "$MNT_TABLE"
        exit 0
        ;;
    umount)
        if [ "${{1:-}}" = "-l" ]; then
            shift
        fi
        TGT="${{1:-}}"
        check_sandbox_path "$TGT"
        REL_TGT="${{TGT#$SANDBOX_ROOT}}"
        echo "UMOUNT|$REL_TGT" >> "$EVENT_LOG"
        if [ -f "$MNT_TABLE" ]; then
            grep -v "^${{TGT}}|" "$MNT_TABLE" > "${{MNT_TABLE}}.tmp" || true
            mv "${{MNT_TABLE}}.tmp" "$MNT_TABLE"
        fi
        exit 0
        ;;
    *)
        "$SUBCMD" "$@"
        ;;
esac
""",
        encoding="utf-8",
    )
    bb_script.chmod(0o755)

    wbi_probe = mock_bin / "wbi_hibernation_probe"
    wbi_probe.write_text(
        f"""#!/bin/sh
set -u
SANDBOX_ROOT="{sandbox_root}"
INHIBIT="${{SANDBOX_ROOT}}/tmp_wbshd/stage_a_wbi_inhibit.lock"
BLOCKED_LOG="${{SANDBOX_ROOT}}/tmp/mock_wbi_blocked.log"
WBI_VIOLATIONS="${{SANDBOX_ROOT}}/tmp/mock_wbi_writes.log"
if [ "${{STAGE_A_WBI_HIBERNATION_MASKED:-0}}" = "1" ] || [ -f "$INHIBIT" ]; then
    echo "BLOCKED_BY_STAGE_A_WBI_GUARD" >> "$BLOCKED_LOG"
    exit 0
fi
echo "UNMASKED_WBI_WRITE_ATTEMPT" >> "$WBI_VIOLATIONS"
exit 93
""",
        encoding="utf-8",
    )
    wbi_probe.chmod(0o755)


def _populate_deterministic_hw_emmc_and_capture(
    hw_dir: Path,
    capture_dir: Path,
    *,
    body_serial: str,
    emmc_cid: str,
    fa0080_table: bytes,
    initialize_hw: bool,
) -> Dict[str, object]:
    """Initialize simulated FX3 hardware partitions (if `initialize_hw`) and perform a read-only Tier-0 capture."""
    hw_dir.mkdir(parents=True, exist_ok=True)
    capture_dir.mkdir(parents=True, exist_ok=True)

    if initialize_hw:
        sec0_bytes = _build_valid_fx3_sector0_bytes()
        bk4_bundle = synthesize_ram_shadow_bk4(fa0080_table=fa0080_table)
        p1_prefix = _build_valid_fat16_p1_header_prefix(25_100_288)
        size_and_headers: Dict[str, Tuple[int, bytes]] = {
            "sector0": (512, sec0_bytes),
            "boot0": (131_072, b"BOOT0_FX3_LDR\x00"),
            "boot1": (131_072, b"BOOT1_FX3_LDR\x00"),
            "p1_updater": (25_100_288, p1_prefix),
            "p2_backup_bin": (262_144, bk4_bundle.bk4_bytes),
            "p2_psd_bin": (4_096, b"PSD_CAL_V1\x00"),
            "p2_defdet_bin": (4_096, b"DEFDET_CAL_V1\x00"),
            "p6_jiritsu": (26_214_400, b"JIRITSU_EXT2_RO\x00"),
            "p12_cert": (20_971_520, b"SONY_CERT_RO\x00"),
            "p18_lensfile": (4_096, b"LENSFILE_MOUNT_CAL\x00"),
            "spi_nor_ddrtraining": (8_192, b"DDRTRAINING_NOR\x00"),
        }
        for key, (total_sz, hdr) in size_and_headers.items():
            fn = str(TIER0_CANONICAL_SOURCES[key]["output_name"])
            _write_sparse_or_patterned_image(
                hw_dir / fn,
                total_sz,
                hdr,
                tail_seed=f"FX3_{key}_".encode("ascii"),
            )
        (hw_dir / "p8_tomco.txt").write_bytes(_build_valid_p8_tomco_bytes())
        (hw_dir / "p5_wbi_header.bin").write_bytes(_build_valid_p5_wbi2_header_bytes())
        (hw_dir / "p30_lut.img").write_bytes(b"FX3_P30_LUT_RO\x00" * 256)
        (hw_dir / "p11_log.img").write_bytes(b"FX3_P11_LOG\x00" * 256)
        (hw_dir / "p15_usr.img").write_bytes(b"FX3_P15_USR_RO\x00" * 256)

    # Read-only two-pass Tier-0 capture from `hw_dir` into `capture_dir`
    tag = hashlib.sha256(f"FX3:{body_serial}:{emmc_cid}".encode("utf-8")).hexdigest()
    items_manifest: Dict[str, Dict[str, object]] = {}
    for key in TIER0_REQUIRED_BACKUPS:
        fn = str(TIER0_CANONICAL_SOURCES[key]["output_name"])
        src = hw_dir / fn
        dst = capture_dir / fn
        pass1_h = hashlib.sha256()
        written = 0
        with src.open("rb") as f_in, dst.open("wb") as f_out:
            while True:
                blk = f_in.read(STREAM_CHUNK_BYTES)
                if not blk:
                    break
                f_out.write(blk)
                pass1_h.update(blk)
                written += len(blk)
        _, pass2_hex = _hash_single_file(src)
        items_manifest[key] = {
            "file_name": fn,
            "source_path": str(TIER0_CANONICAL_SOURCES[key]["source_path"]),
            "bytes": written,
            "pass1_sha256": pass1_h.hexdigest(),
            "pass2_sha256": pass2_hex,
        }

    redlines_manifest: Dict[str, Dict[str, object]] = {}
    for probe_key, fn in REQUIRED_REDLINE_HEADER_PROBES.items():
        src = hw_dir / fn
        dst = capture_dir / fn
        raw = src.read_bytes()
        dst.write_bytes(raw)
        sha1 = hashlib.sha256(raw).hexdigest()
        sha2 = hashlib.sha256(src.read_bytes()).hexdigest()
        entry: Dict[str, object] = {
            "file_name": fn,
            "source_path": "/cp/tomco.txt" if probe_key == "p8_tomco_txt" else "/dev/nflasha5",
            "bytes": len(raw),
            "pass1_sha256": sha1,
            "pass2_sha256": sha2,
        }
        if probe_key == "p5_wbi_header":
            entry["partition_image_bytes"] = 202_677_056
        redlines_manifest[probe_key] = entry

    manifest: Dict[str, object] = {
        "schema": "fx3-tier0-hardware-backup-manifest-v1",
        "capture_origin": "physical_fx3_hardware",
        "model_id": FX3_MODEL_ID_HEX,
        "camera_body_tag": tag,
        "body_serial": body_serial,
        "cid": emmc_cid,
        "items": items_manifest,
        "redline_headers": redlines_manifest,
    }
    (capture_dir / "backup-manifest.json").write_text(
        json.dumps(manifest, indent=2) + "\n",
        encoding="utf-8",
    )
    return manifest


def _normalize_receipt_for_deterministic_hash(
    receipt: StageAPostTrialReceipt,
    *,
    h0_label: str = "<SANDBOX>/h0_capture",
    h2_label: str = "<SANDBOX>/h2_capture",
) -> str:
    """Compute a path-independent receipt SHA-256 across ephemeral `TemporaryDirectory` runs."""
    d = receipt.to_dict()
    d.pop("receipt_sha256", None)
    if isinstance(d.get("h0_bundle_audit"), dict):
        d["h0_bundle_audit"]["bundle_dir"] = h0_label
    if isinstance(d.get("h2_bundle_audit"), dict):
        d["h2_bundle_audit"]["bundle_dir"] = h2_label
    raw = json.dumps(d, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def run_h0_h1_h2_lifecycle_drill(
    *,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    synthetic_clean_room: Optional[bool] = None,
) -> StageAH0H1H2LifecycleDrillReport:
    """Execute the full Phase H0 -> H1 (`/bin/sh` orchestrator) -> H2 zero-mutation drill + 10 negative faults.

    Works deterministically in both local-donor mode and `FX3_FX6_FORCE_CLEAN_ROOM=1` donorless CI mode.
    """
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    verification_mode = (
        "CLEAN_ROOM_SYNTHETIC_VERIFIED" if use_clean_room else "LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED"
    )
    fa0080_tbl = build_canonical_fa0080_normal_boot_table(
        donor_seed_bk4_path=None if use_clean_room else DEFAULT_FX3_SEED_BK4_PATH
    )

    overlay_bundle = build_stage_a_ram_overlay_package(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=use_clean_room,
    )
    ram_bk4 = synthesize_ram_shadow_bk4(fa0080_table=fa0080_tbl)

    errors: List[str] = []
    fault_cases: List[LifecycleFaultInjectionCase] = []

    tmp_ctx = tempfile.TemporaryDirectory(prefix="fx6_phase16_h0_h1_h2_")
    tmp_path = Path(tmp_ctx.name)
    try:
        hw_dir = tmp_path / "emmc_hw"
        h0_dir = tmp_path / "h0_capture"
        h2_dir = tmp_path / "h2_capture"
        sandbox_root = tmp_path / "stage_a_sandbox"
        mock_bin = tmp_path / "mock_bin"

        # --- Phase H0: Baseline Read-Only Tier-0 Capture ---
        _populate_deterministic_hw_emmc_and_capture(
            hw_dir,
            h0_dir,
            body_serial="3018492",
            emmc_cid="15010038474d453452019c4a7b8e5f91",
            fa0080_table=fa0080_tbl,
            initialize_hw=True,
        )
        h0_baseline_audit = verify_real_tier0_capture_bundle(h0_dir)
        if not h0_baseline_audit.valid:
            errors.extend(f"H0 baseline invalid: {e}" for e in h0_baseline_audit.errors)

        # Snapshot hardware mtimes/digests prior to Phase H1
        hw_before = {
            p.name: (p.stat().st_mtime_ns, _hash_single_file(p)[1])
            for p in sorted(hw_dir.iterdir())
            if p.is_file()
        }

        # --- Phase H1: Real `PREFIX`-Isolated `/bin/sh` Execution of `30-stage-a-orchestrator.sh` ---
        extract_cpio_newc_to_dir(overlay_bundle.cpio_bytes, sandbox_root)
        _install_lifecycle_mock_bin(mock_bin, sandbox_root)

        # Wire simulated `/dev/*` nodes directly to `hw_dir` so any illegal write mutates `hw_dir`
        dev_dir = sandbox_root / "dev"
        dev_dir.mkdir(parents=True, exist_ok=True)
        for link_name, target_fn in (
            ("nflasha5", "p5_wbi_header.bin"),
            ("pnflasha5", "p5_wbi_header.bin"),
            ("cnflasha30", "p30_lut.img"),
            ("pnflasha30", "p30_lut.img"),
            ("nflasha11", "p11_log.img"),
            ("nflasha15", "p15_usr.img"),
        ):
            lnk = dev_dir / link_name
            if lnk.exists() or lnk.is_symlink():
                lnk.unlink()
            lnk.symlink_to(hw_dir / target_fn)

        # Stage adapted runtime blobs + RAM-shadow `BK4\0` inside `sandbox_root/tmp/fx6_stage_a`
        stage_dir = sandbox_root / "tmp" / "fx6_stage_a"
        for rel_path, blob in overlay_bundle.staged_runtime_blobs.items():
            dst = stage_dir / rel_path
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_bytes(blob)
        bk4_stage_dir = stage_dir / "backup"
        bk4_stage_dir.mkdir(parents=True, exist_ok=True)
        (bk4_stage_dir / "ram_shadow_Backup.bin").write_bytes(ram_bk4.bk4_bytes)
        (bk4_stage_dir / "ram_shadow_Backup.sha256").write_text(
            ram_bk4.sha256 + "\n",
            encoding="utf-8",
        )

        # Arm one-shot `/tmp/mod_arm_once` and configure `/proc/udm/upm_bootmode` + `/proc/mounts`
        (sandbox_root / "tmp" / "mod_arm_once").write_text("1\n", encoding="utf-8")
        (sandbox_root / "proc" / "udm").mkdir(parents=True, exist_ok=True)
        (sandbox_root / "proc" / "udm" / "upm_bootmode").write_text("NORMAL\n", encoding="utf-8")
        (sandbox_root / "proc" / "mounts").write_text(
            "/dev/nflasha15 /usr ext2 ro 0 0\n",
            encoding="utf-8",
        )

        orch_script = sandbox_root / ORCHESTRATOR_CPIO_REL_PATH
        h1_env = dict(os.environ)
        h1_env["PREFIX"] = str(sandbox_root)
        h1_env["FX3_STAGE_A_DIR"] = str(stage_dir)
        h1_env["FX3_IM_ELF_CMD"] = "wbi_hibernation_probe"
        h1_env["FX3_STOCK_BOOT_CMD"] = f': > "{sandbox_root}/tmp/stock_fx3_booted.marker"'
        h1_env["PATH"] = f"{mock_bin}:/usr/bin:/bin:/usr/sbin:/sbin"

        h1_proc = subprocess.run(
            ["/bin/sh", str(orch_script)],
            env=h1_env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )

        hw_after_h1 = {
            p.name: (p.stat().st_mtime_ns, _hash_single_file(p)[1])
            for p in sorted(hw_dir.iterdir())
            if p.is_file()
        }
        emmc_mutations = [
            fname for fname in hw_before if hw_after_h1.get(fname) != hw_before[fname]
        ]
        if emmc_mutations:
            emmc_log = sandbox_root / "tmp" / "mock_emmc_writes.log"
            emmc_log.write_text("\n".join(emmc_mutations) + "\n", encoding="utf-8")

        h1_telemetry_dict = serialize_h1_orchestrator_telemetry_from_sandbox(sandbox_root)
        h1_telemetry_path = tmp_path / "h1-orchestrator-telemetry.json"
        h1_telemetry_path.write_text(
            json.dumps(h1_telemetry_dict, indent=2) + "\n",
            encoding="utf-8",
        )
        h1_audit = verify_h1_orchestrator_telemetry(h1_telemetry_path)
        if h1_proc.returncode != 0 or not h1_audit.valid:
            errors.append(
                f"Phase H1 orchestrator drill failed: rc={h1_proc.returncode}, errors={h1_audit.errors}"
            )

        # Simulate cold power-cycle (volatile tmpfs lock vanishes; `/tmp/mod_arm_once` was already unlinked!)
        (sandbox_root / "tmp" / "stage_a_orchestrator.lock").unlink(missing_ok=True)
        (sandbox_root / "tmp" / "mock_events.log").unlink(missing_ok=True)
        (sandbox_root / "tmp" / "stage_a_orchestrator_state.env").unlink(missing_ok=True)
        cold_proc = subprocess.run(
            ["/bin/sh", str(orch_script)],
            env=h1_env,
            capture_output=True,
            text=True,
            timeout=15,
            check=False,
        )
        cold_state = _parse_kv_lines(
            _read_nonempty_lines(sandbox_root / "tmp" / "stage_a_orchestrator_state.env")
        )
        cold_branch = cold_state.get("BOOT_BRANCH", "MISSING")
        cold_diag = cold_state.get("DIAG_CODE", "MISSING")
        cold_events = _read_nonempty_lines(sandbox_root / "tmp" / "mock_events.log")
        cold_mount_or_insmod = sum(
            1 for ev in cold_events if ev.startswith(("INSMOD|", "MOUNT|", "LOSETUP_ATTACH|"))
        )
        cold_passthrough_ok = (
            cold_proc.returncode == 0
            and cold_branch == "STOCK_FX3"
            and cold_diag == "STOCK_COLD_BOOT_PASSTHROUGH"
            and cold_state.get("STOCK_BOOT_INVOKED") == "1"
            and cold_mount_or_insmod == 0
        )
        if not cold_passthrough_ok:
            errors.append(
                f"Post-H1 cold reboot passthrough failed: branch={cold_branch!r}, diag={cold_diag!r}"
            )

        # --- Phase H2: Post-Power-Cycle Second Read-Only Capture & Receipt Verification ---
        _populate_deterministic_hw_emmc_and_capture(
            hw_dir,
            h2_dir,
            body_serial="3018492",
            emmc_cid="15010038474d453452019c4a7b8e5f91",
            fa0080_table=fa0080_tbl,
            initialize_hw=False,
        )
        nominal_receipt = verify_post_trial_zero_mutation(
            h0_dir,
            h2_dir,
            h1_telemetry_log_path=h1_telemetry_path,
        )
        if not nominal_receipt.all_checks_passed:
            errors.extend(f"H2 nominal receipt failed: {e}" for e in nominal_receipt.errors)

        nominal_norm_sha = _normalize_receipt_for_deterministic_hash(nominal_receipt)

        # --- Deterministic Negative Fault-Injection Suite (10 faults >= 8 required) ---
        h2_manifest_path = h2_dir / "backup-manifest.json"
        base_h2_manifest = json.loads(h2_manifest_path.read_text(encoding="utf-8"))

        def _record_fault(
            fault_id: str,
            description: str,
            rec: StageAPostTrialReceipt,
            predicate_ok: bool,
        ) -> None:
            rejected_ok = (not rec.all_checks_passed) and predicate_ok
            if not rejected_ok:
                errors.append(
                    f"Fault injection {fault_id} was not rejected with expected predicate "
                    f"(all_checks_passed={rec.all_checks_passed}, errors={rec.errors})"
                )
            reason = rec.errors[0] if rec.errors else "UNEXPECTED_PASS"
            fault_cases.append(
                LifecycleFaultInjectionCase(
                    fault_id=fault_id,
                    description=description,
                    rejected_as_expected=rejected_ok,
                    persistent_bytes_mutated=rec.persistent_bytes_mutated,
                    drifted_items=rec.drifted_items,
                    same_body_identity_verified=rec.same_body_identity_verified,
                    u5_sticky_boot_clean=rec.u5_sticky_boot_clean,
                    h1_telemetry_verified=rec.h1_telemetry_verified,
                    both_bundles_real_hardware_valid=rec.both_bundles_real_hardware_valid,
                    primary_rejection_reason=reason,
                )
            )

        # Fault 01: 1-bit flip in `sector0.bin`
        sec0_p = h2_dir / "sector0.bin"
        orig_sec0 = sec0_p.read_bytes()
        try:
            mut_sec0 = bytearray(orig_sec0)
            mut_sec0[16] ^= 0x01
            sec0_p.write_bytes(bytes(mut_sec0))
            m_f1 = copy.deepcopy(base_h2_manifest)
            s_f1 = hashlib.sha256(bytes(mut_sec0)).hexdigest()
            m_f1["items"]["sector0"]["pass1_sha256"] = s_f1
            m_f1["items"]["sector0"]["pass2_sha256"] = s_f1
            h2_manifest_path.write_text(json.dumps(m_f1, indent=2) + "\n", encoding="utf-8")
            r_f1 = verify_post_trial_zero_mutation(h0_dir, h2_dir, h1_telemetry_log_path=h1_telemetry_path)
            _record_fault(
                "F01_sector0_1bit_flip",
                "1-bit flip in H2 sector0.bin rejected via byte-exact H0-vs-H2 parity",
                r_f1,
                r_f1.persistent_bytes_mutated == 1 and r_f1.drifted_items == ("sector0",),
            )
        finally:
            sec0_p.write_bytes(orig_sec0)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # Fault 02: 1-bit flip in `p2_backup_bin.bin`
        p2_p = h2_dir / "p2_backup_bin.bin"
        orig_p2 = p2_p.read_bytes()
        try:
            mut_p2 = bytearray(orig_p2)
            mut_p2[-1] ^= 0x01  # trailing slack byte outside Record 0 span (or raw bit flip)
            p2_p.write_bytes(bytes(mut_p2))
            m_f2 = copy.deepcopy(base_h2_manifest)
            s_f2 = hashlib.sha256(bytes(mut_p2)).hexdigest()
            m_f2["items"]["p2_backup_bin"]["pass1_sha256"] = s_f2
            m_f2["items"]["p2_backup_bin"]["pass2_sha256"] = s_f2
            h2_manifest_path.write_text(json.dumps(m_f2, indent=2) + "\n", encoding="utf-8")
            r_f2 = verify_post_trial_zero_mutation(h0_dir, h2_dir, h1_telemetry_log_path=h1_telemetry_path)
            _record_fault(
                "F02_p2_backup_bin_1bit_flip",
                "1-bit flip in H2 p2_backup_bin.bin rejected via byte-exact H0-vs-H2 parity",
                r_f2,
                r_f2.persistent_bytes_mutated == 1 and r_f2.drifted_items == ("p2_backup_bin",),
            )
        finally:
            p2_p.write_bytes(orig_p2)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # Fault 03: 1-bit flip in `p5_wbi_header.bin`
        wbi_p = h2_dir / "p5_wbi_header.bin"
        orig_wbi = wbi_p.read_bytes()
        try:
            mut_wbi = bytearray(orig_wbi)
            mut_wbi[200] ^= 0x01
            wbi_p.write_bytes(bytes(mut_wbi))
            m_f3 = copy.deepcopy(base_h2_manifest)
            s_f3 = hashlib.sha256(bytes(mut_wbi)).hexdigest()
            m_f3["redline_headers"]["p5_wbi_header"]["pass1_sha256"] = s_f3
            m_f3["redline_headers"]["p5_wbi_header"]["pass2_sha256"] = s_f3
            h2_manifest_path.write_text(json.dumps(m_f3, indent=2) + "\n", encoding="utf-8")
            r_f3 = verify_post_trial_zero_mutation(h0_dir, h2_dir, h1_telemetry_log_path=h1_telemetry_path)
            _record_fault(
                "F03_p5_wbi_header_1bit_flip",
                "1-bit flip in H2 p5_wbi_header.bin rejected via WBI redline parity",
                r_f3,
                r_f3.persistent_bytes_mutated == 1 and r_f3.drifted_items == ("p5_wbi_header",),
            )
        finally:
            wbi_p.write_bytes(orig_wbi)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # Fault 04: 1-bit flip in `p8_tomco.txt`
        tomco_p = h2_dir / "p8_tomco.txt"
        orig_tomco = tomco_p.read_bytes()
        try:
            mut_tomco = bytearray(orig_tomco)
            # Flip 1 bit inside comment header ('#' line) so ASCII & memcfg remain valid yet SHA-256 drifts
            mut_tomco[2] ^= 0x01
            tomco_p.write_bytes(bytes(mut_tomco))
            m_f4 = copy.deepcopy(base_h2_manifest)
            s_f4 = hashlib.sha256(bytes(mut_tomco)).hexdigest()
            m_f4["redline_headers"]["p8_tomco_txt"]["pass1_sha256"] = s_f4
            m_f4["redline_headers"]["p8_tomco_txt"]["pass2_sha256"] = s_f4
            h2_manifest_path.write_text(json.dumps(m_f4, indent=2) + "\n", encoding="utf-8")
            r_f4 = verify_post_trial_zero_mutation(h0_dir, h2_dir, h1_telemetry_log_path=h1_telemetry_path)
            _record_fault(
                "F04_p8_tomco_txt_1bit_flip",
                "1-bit flip in H2 p8_tomco.txt rejected via CP RTOS redline parity",
                r_f4,
                r_f4.persistent_bytes_mutated == 1 and r_f4.drifted_items == ("p8_tomco_txt",),
            )
        finally:
            tomco_p.write_bytes(orig_tomco)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # Fault 05: Mismatched physical `body_serial` and 128-bit eMMC `cid`
        try:
            m_f5 = copy.deepcopy(base_h2_manifest)
            other_serial = "3094827"
            other_cid = "15010038474d453452019c4a7b8e5f93"
            m_f5["body_serial"] = other_serial
            m_f5["cid"] = other_cid
            m_f5["camera_body_tag"] = hashlib.sha256(
                f"FX3:{other_serial}:{other_cid}".encode("utf-8")
            ).hexdigest()
            h2_manifest_path.write_text(json.dumps(m_f5, indent=2) + "\n", encoding="utf-8")
            r_f5 = verify_post_trial_zero_mutation(h0_dir, h2_dir, h1_telemetry_log_path=h1_telemetry_path)
            _record_fault(
                "F05_mismatched_body_serial_and_cid",
                "Cross-body H2 bundle (mismatched body_serial & eMMC cid) rejected",
                r_f5,
                (not r_f5.same_body_identity_verified) and r_f5.both_bundles_real_hardware_valid,
            )
        finally:
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # Fault 06: Sticky `boot_img` byte `+8 = 0x01` in H2 `p2_backup_bin.bin` (with valid BK4 checksum)
        try:
            sticky_p2_arr = bytearray(orig_p2)
            sticky_p2_arr[0x08] = 0x01
            sticky_p2_bytes = recompute_bk4_record0_checksum(bytes(sticky_p2_arr))
            p2_p.write_bytes(sticky_p2_bytes)
            m_f6 = copy.deepcopy(base_h2_manifest)
            s_f6 = hashlib.sha256(sticky_p2_bytes).hexdigest()
            m_f6["items"]["p2_backup_bin"]["pass1_sha256"] = s_f6
            m_f6["items"]["p2_backup_bin"]["pass2_sha256"] = s_f6
            h2_manifest_path.write_text(json.dumps(m_f6, indent=2) + "\n", encoding="utf-8")
            r_f6 = verify_post_trial_zero_mutation(h0_dir, h2_dir, h1_telemetry_log_path=h1_telemetry_path)
            _record_fault(
                "F06_sticky_boot_img_byte8_nonzero",
                "Sticky BK4\\0 boot_img selector byte +8 == 0x01 rejected by U5 cleanliness check",
                r_f6,
                (not r_f6.u5_sticky_boot_clean)
                and (not r_f6.u5_boot_img_byte8_zero_ok)
                and r_f6.h2_bk4_byte8 == 0x01,
            )
        finally:
            p2_p.write_bytes(orig_p2)
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

        # Fault 07: Sticky `/setting/updater/mode5` file residue in H2 directory
        sticky_mode_file = h2_dir / "setting" / "updater" / "mode5"
        try:
            sticky_mode_file.parent.mkdir(parents=True, exist_ok=True)
            sticky_mode_file.write_text("1\n", encoding="utf-8")
            r_f7 = verify_post_trial_zero_mutation(h0_dir, h2_dir, h1_telemetry_log_path=h1_telemetry_path)
            _record_fault(
                "F07_sticky_setting_updater_mode_residue",
                "Sticky /setting/updater/mode5 residue in H2 rejected by U5 cleanliness check",
                r_f7,
                (not r_f7.u5_sticky_boot_clean)
                and (not r_f7.u5_zero_updater_mode_residue_ok)
                and ("setting/updater/mode5" in r_f7.sticky_updater_residue),
            )
        finally:
            sticky_mode_file.unlink(missing_ok=True)
            (h2_dir / "setting" / "updater").rmdir()
            (h2_dir / "setting").rmdir()

        # Fault 08: Missing Clear-Before-Exec in H1 telemetry (`/tmp/mod_arm_once` not cleared before mount)
        bad_h1_clear = copy.deepcopy(h1_telemetry_dict)
        bad_h1_clear["token_cleared_before_exec"] = False
        bad_h1_clear["token_present_after"] = True
        r_f8 = verify_post_trial_zero_mutation(
            h0_dir,
            h2_dir,
            h1_telemetry_text=json.dumps(bad_h1_clear),
        )
        _record_fault(
            "F08_h1_missing_clear_before_exec",
            "Missing Clear-Before-Exec (/tmp/mod_arm_once unlink) in H1 telemetry rejected",
            r_f8,
            (not r_f8.h1_telemetry_verified)
            and r_f8.h1_telemetry_audit is not None
            and (not r_f8.h1_telemetry_audit.clear_before_exec_ok),
        )

        # Fault 09: Incomplete / non-LIFO unwind in H1 telemetry (`unwind_steps` truncated + lingering mount)
        bad_h1_lifo = copy.deepcopy(h1_telemetry_dict)
        bad_h1_lifo["unwind_steps"] = list(EXPECTED_STAGE_A_LIFO_UNWIND_STEP_IDS[:-1])
        bad_h1_lifo["lingering_mount_count"] = 1
        r_f9 = verify_post_trial_zero_mutation(
            h0_dir,
            h2_dir,
            h1_telemetry_text=json.dumps(bad_h1_lifo),
        )
        _record_fault(
            "F09_h1_incomplete_lifo_unwind",
            "Incomplete 10..1 LIFO teardown & lingering mount in H1 telemetry rejected",
            r_f9,
            (not r_f9.h1_telemetry_verified)
            and r_f9.h1_telemetry_audit is not None
            and (not r_f9.h1_telemetry_audit.lifo_unwind_ok),
        )

        # Fault 10: Synthetic / emulated Tier-0 bundle rejected fail-closed
        try:
            m_f10 = copy.deepcopy(base_h2_manifest)
            m_f10["synthetic"] = True
            m_f10["capture_origin"] = "unicorn_emulation"
            h2_manifest_path.write_text(json.dumps(m_f10, indent=2) + "\n", encoding="utf-8")
            r_f10 = verify_post_trial_zero_mutation(h0_dir, h2_dir, h1_telemetry_log_path=h1_telemetry_path)
            _record_fault(
                "F10_synthetic_placeholder_bundle_rejected",
                "Synthetic/Unicorn H2 Tier-0 capture manifest rejected fail-closed",
                r_f10,
                not r_f10.both_bundles_real_hardware_valid,
            )
        finally:
            h2_manifest_path.write_text(json.dumps(base_h2_manifest, indent=2) + "\n", encoding="utf-8")

    finally:
        tmp_ctx.cleanup()

    temp_cleaned = not tmp_path.exists()
    if not temp_cleaned:
        errors.append(f"Temporary lifecycle drill directory not cleaned: {tmp_path}")

    all_faults_ok = len(fault_cases) >= 8 and all(fc.rejected_as_expected for fc in fault_cases)
    overall_ok = (
        h0_baseline_audit.valid
        and h1_proc.returncode == 0
        and h1_audit.valid
        and cold_passthrough_ok
        and nominal_receipt.all_checks_passed
        and nominal_receipt.persistent_bytes_mutated == 0
        and nominal_receipt.drifted_items == ()
        and nominal_receipt.u5_sticky_boot_clean
        and all_faults_ok
        and temp_cleaned
        and len(errors) == 0
    )

    draft_drill = StageAH0H1H2LifecycleDrillReport(
        schema=LIFECYCLE_DRILL_SCHEMA,
        phase_version=PHASE_16_VERSION,
        verification_mode=verification_mode,
        all_checks_passed=overall_ok,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        usb_or_camera_operations=0,
        temp_dir_cleaned=temp_cleaned,
        h0_baseline_valid=h0_baseline_audit.valid,
        h1_orchestrator_returncode=h1_proc.returncode,
        h1_telemetry_audit=h1_audit,
        h1_cold_reboot_passthrough_ok=cold_passthrough_ok,
        h1_cold_reboot_branch=cold_branch,
        h1_cold_reboot_diag=cold_diag,
        h2_nominal_zero_mutation_ok=nominal_receipt.zero_mutation_verified,
        h2_nominal_persistent_bytes_mutated=nominal_receipt.persistent_bytes_mutated,
        h2_nominal_drifted_items=nominal_receipt.drifted_items,
        h2_nominal_u5_sticky_boot_clean=nominal_receipt.u5_sticky_boot_clean,
        h2_nominal_receipt_sha256=nominal_norm_sha,
        fault_injection_count=len(fault_cases),
        fault_injections_all_rejected=all_faults_ok,
        fault_cases=tuple(fault_cases),
        errors=tuple(errors),
        drill_sha256="",
    )
    drill_sha = _compute_canonical_sha256(draft_drill.to_dict(), "drill_sha256")

    return StageAH0H1H2LifecycleDrillReport(
        schema=draft_drill.schema,
        phase_version=draft_drill.phase_version,
        verification_mode=draft_drill.verification_mode,
        all_checks_passed=draft_drill.all_checks_passed,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        usb_or_camera_operations=0,
        temp_dir_cleaned=draft_drill.temp_dir_cleaned,
        h0_baseline_valid=draft_drill.h0_baseline_valid,
        h1_orchestrator_returncode=draft_drill.h1_orchestrator_returncode,
        h1_telemetry_audit=draft_drill.h1_telemetry_audit,
        h1_cold_reboot_passthrough_ok=draft_drill.h1_cold_reboot_passthrough_ok,
        h1_cold_reboot_branch=draft_drill.h1_cold_reboot_branch,
        h1_cold_reboot_diag=draft_drill.h1_cold_reboot_diag,
        h2_nominal_zero_mutation_ok=draft_drill.h2_nominal_zero_mutation_ok,
        h2_nominal_persistent_bytes_mutated=draft_drill.h2_nominal_persistent_bytes_mutated,
        h2_nominal_drifted_items=draft_drill.h2_nominal_drifted_items,
        h2_nominal_u5_sticky_boot_clean=draft_drill.h2_nominal_u5_sticky_boot_clean,
        h2_nominal_receipt_sha256=draft_drill.h2_nominal_receipt_sha256,
        fault_injection_count=draft_drill.fault_injection_count,
        fault_injections_all_rejected=draft_drill.fault_injections_all_rejected,
        fault_cases=draft_drill.fault_cases,
        errors=draft_drill.errors,
        drill_sha256=drill_sha,
    )
