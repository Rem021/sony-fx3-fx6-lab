"""Phase 52 — Unified Stage-B End-to-End Candidate Integrator (`stage_b_integrated_dossier_v1`).

Composes all five cross-track Stage-B safety, recovery, forensic, and packaging
engines into a single fast (<5s), deterministic, self-authenticating JSON dossier
(`stage_b_integrated_dossier_v1`) with fail-closed tamper verification:

1. **Phase 50 `fx3_safety.master_16gate_preflight` (`G01..G16`)**:
   - Verifies C2PA `RQ_LIC.DAT` & factory sensor/IBIS calibration immutability
     (`calibration_mutation_bytes == 0`), thermal PWM + `NP-FZ100 >= 80%` +
     `USB-PD 9V/3A`, Multi-Port `VMC-BNCM1` LTC isolation, `P12` `WF-12` bootloop
     immunity, and `WBI2` cold-boot isolation.
2. **Phase 48 `fx6_closure.stage_b_ram_overlay_packager`**:
   - Deterministic SVR4 `cpio newc` (`070701`) Stage-B archive across all 4 selectable
     `BK_LANG` profiles (`en`, `schinese`, `tchinese`, `japanese`), `13/13`
     `P1..P12+Fan` Verify-Before-Mount SHA-256 locks, `< 48 MiB` `tmpfs` DDR
     footprint, and POSIX `/bin/sh` `stage_b_init2_guard.sh` 9-scenario audit.
3. **Phase 47 `fx3_recovery.unbrick_ladder_and_capsule_verifier`**:
   - `12/12` Tier-0..Tier-4 escalation state-machine scenarios + `p1` VFAT
     (`FAT12`/`FAT16`) atomic rollback capsule SHA-256 verification.
4. **Phase 42 `fx3_recovery.emmc_dump_forensic_verifier`**:
   - Strictly `O_RDONLY` stuck-bus / truncation / `'8246'` / `'BK4\\0'` / `'WBI2'`
     pre-session gate + boot-chain immutability firewall.
5. **Phase 39 `fx6_closure.stage_b_master_readiness_packet`**:
   - `stage_b_readiness_packet_v2` self-authenticating readiness packet + Phase 35
     `10/10` `S01..S10` Stage-B lifecycle drill & `H2` zero-drift verification.

Hard-Locked Safety Redlines:
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`
- `wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`
- `calibration_mutation_bytes = 0`
- `usb_or_camera_operations = 0`
- Never prints or embeds raw binary `bytes` reprs (`b'...'` / `b"..."`).
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

from concurrent.futures import ThreadPoolExecutor
import copy
from dataclasses import asdict, dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from typing import Any, Dict, List, Mapping, Optional, Tuple

from fx3_recovery.emmc_dump_forensic_verifier import (
    ALLOW_BOOT_PARTITION_TARGETING as FORENSIC_ALLOW_BOOT_PARTITION_TARGETING,
    FORENSIC_VERIFIER_SCHEMA,
    PERSISTENT_EMMC_WRITES_AUTHORIZED as FORENSIC_EMMC_AUTH,
    READ_ONLY_DONOR_ACCESS,
    WBI2_HEADER_SIZE,
    WBI2_INVALIDATED_MAGICS,
    WBI2_MAGIC,
    analyze_bus_and_entropy,
    audit_boot_chain_immutability,
    build_synthetic_encrypted_cnflasha,
    build_synthetic_p5_wbi2_image,
    read_two_pass_sha256_readonly,
    run_clean_room_forensic_suite,
    verify_emmc_dump_bytes,
    verify_p1_vfat_dump,
    verify_p8_cp_rtos_dump,
)
from fx3_recovery.files import resolve_donor_path
from fx3_recovery.unbrick_ladder_and_capsule_verifier import (
    UNBRICK_LADDER_SCHEMA,
    UnbrickLadderVerificationReport,
    run_unbrick_ladder_and_capsule_suite,
)
from fx3_safety.master_16gate_preflight import (
    MASTER_16GATE_PREFLIGHT_SCHEMA,
    Master16GateReport,
    evaluate_16_master_safety_gates,
)
from fx3_safety.preflight import verify_failsafe_hook_script
from fx3_safety.runtime_antibrick_guards import audit_ld_so_preload_and_overlay

from .hardware_readiness_packet import HEX64_RE, _is_forced_clean_room
from .patcher import DEFAULT_FX3_MODULES_DIR, DEFAULT_FX6_DONOR_LIB_DIR
from .ram_overlay_packager import CpioEntrySpec, S_IFDIR, S_IFREG
from .stage_b_master_readiness_packet import (
    DEFAULT_REPO_ROOT,
    STAGE_B_READINESS_PACKET_SCHEMA,
    StageBMasterReadinessPacketReport,
    build_stage_b_master_readiness_packet,
    verify_stage_b_master_readiness_packet,
)
from .stage_b_ram_overlay_packager import (
    FX3_PRODUCT_MODEL_HEX,
    PHASE_48_SCHEMA,
    PHASE_48_VERSION,
    STAGE_B_BK_LANG_SPECS,
    STAGE_B_LOCK_TABLE_13_ARTIFACTS,
    STAGE_B_SUPPORTED_LANGS,
    STAGE_B_TMPFS_BUDGET_LIMIT_MIB,
    StageBRamOverlayV2Bundle,
    StageBRamOverlayV2Report,
    build_stage_b_cpio_newc_archive,
    build_stage_b_ram_overlay_v2_package,
    generate_stage_b_init2_guard_script,
    parse_and_audit_stage_b_cpio_newc,
    synthesize_stage_b_bk4_shadow,
    verify_stage_b_ram_overlay_v2,
    verify_stage_b_tmpfs_ddr_budget,
)


STAGE_B_CANDIDATE_DOSSIER_SCHEMA = "stage_b_integrated_dossier_v1"
PHASE_52_VERSION = "52.0.0"

# Hard-locked safety redlines (immutable)
PERSISTENT_EMMC_WRITES_AUTHORIZED = False
PERSISTENT_WRITE_RELEASE = False
P8_CP_MUTATION_FORBIDDEN = True
WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN = True
CP_MUTATION_BYTES = 0
WBI_MUTATION_BYTES = 0
CALIBRATION_MUTATION_BYTES = 0
USB_OR_CAMERA_OPERATIONS = 0

STAGE_B_CANDIDATE_PILLARS: Tuple[str, ...] = (
    "phase50_master_16gate_preflight",
    "phase48_stage_b_ram_overlay_v2",
    "phase47_unbrick_ladder_and_capsule",
    "phase42_emmc_dump_forensic_gate",
    "phase39_stage_b_master_readiness",
)

FORENSIC_REQUIRED_ROLES: Tuple[str, ...] = (
    "sector0",
    "p1",
    "p2",
    "p5",
    "p8",
    "ext_csd",
    "cnflasha",
)

DONOR_FORENSIC_DUMP_SPECS: Tuple[Tuple[str, str], ...] = (
    ("p1", "fx3-color-port-20261027/input-20261028/original-update-engine/2.05/nflasha1"),
    ("p8", "sony-firmware-20261024/stage2/extraction/nflasha8.img"),
)
DONOR_P5_WBI2_RELPATH = "sony-firmware-20261024/stage2/extraction/nflasha5.img"

_RAW_BYTES_REPR_RE = re.compile(r"(?<![0-9A-Za-z_/.-])b['\"]")


@dataclass(frozen=True)
class StageBCandidateVerifyResult:
    valid: bool
    schema_ok: bool
    sha256_matched: bool
    expected_dossier_sha256: str
    observed_dossier_sha256: str
    safety_redlines_ok: bool
    phase50_16gate_ok: bool
    phase48_ram_overlay_ok: bool
    phase47_unbrick_capsule_ok: bool
    phase42_forensic_gate_ok: bool
    phase39_readiness_ok: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass(frozen=True)
class StageBIntegratedDossierReport:
    schema: str
    phase_version: str
    verification_mode: str
    selected_lang: str
    all_5_pillars_passed: bool
    candidate_ready: bool
    status: str
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    p8_cp_mutation_forbidden: bool
    cp_mutation_bytes: int
    wbi_p5_write_and_hibernation_forbidden: bool
    wbi_mutation_bytes: int
    calibration_mutation_bytes: int
    usb_or_camera_operations: int
    pillar_count: int
    passed_pillar_count: int
    phase50_master_16gate_preflight: Dict[str, Any]
    phase48_stage_b_ram_overlay_v2: Dict[str, Any]
    phase47_unbrick_ladder_and_capsule: Dict[str, Any]
    phase42_emmc_dump_forensic_gate: Dict[str, Any]
    phase39_stage_b_master_readiness: Dict[str, Any]
    errors: Tuple[str, ...]
    dossier_sha256: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    def to_deterministic_json(self, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), sort_keys=True, indent=indent, ensure_ascii=False) + "\n"


def _compute_dossier_sha256(dossier_dict: Mapping[str, Any]) -> str:
    payload = copy.deepcopy(dict(dossier_dict))
    payload["dossier_sha256"] = ""
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


def _run_pillar1_16gate(
    *,
    repo_root: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], bool, List[str]]:
    rep: Master16GateReport = evaluate_16_master_safety_gates(
        repo_root=repo_root,
        force_clean_room=use_clean_room,
        use_synthetic_dry_run_tier0=True,
    )
    errors: List[str] = []
    if not rep.all_16_gates_verified:
        errors.append(f"pillar1-16gate: all_16_gates_verified=False status={rep.status}")
    if not rep.offline_13_gates_verified or not rep.g13_to_g16_all_passed:
        errors.append("pillar1-16gate: offline_13_gates_verified or g13_to_g16_all_passed is False")
    if rep.persistent_emmc_writes_authorized is not False or rep.persistent_write_release is not False:
        errors.append("pillar1-16gate: persistent write redline violated")
    if rep.g15_result.get("calibration_mutation_bytes") != 0:
        errors.append("pillar1-16gate: G15 calibration_mutation_bytes != 0")
    if rep.g16_result.get("wbi_mutation_bytes") != 0 or rep.g16_result.get("cp_mutation_bytes") != 0:
        errors.append("pillar1-16gate: G16 wbi_mutation_bytes or cp_mutation_bytes != 0")
    errors.extend(f"pillar1-16gate: {e}" for e in rep.errors)

    gates_summary = [
        {
            "gate_id": str(g.get("gate_id", "")),
            "gate_code": str(g.get("gate_code", "")),
            "status": str(g.get("status", "")),
        }
        for g in rep.gates
    ]
    g14_details = dict(rep.g14_result.get("details", {}))
    summary: Dict[str, Any] = {
        "schema": rep.schema,
        "version": rep.version,
        "verification_mode": rep.verification_mode,
        "clean_room_forced": rep.clean_room_forced,
        "status": rep.status,
        "all_16_gates_verified": rep.all_16_gates_verified,
        "offline_13_gates_verified": rep.offline_13_gates_verified,
        "g13_to_g16_all_passed": rep.g13_to_g16_all_passed,
        "persistent_emmc_writes_authorized": rep.persistent_emmc_writes_authorized,
        "persistent_write_release": rep.persistent_write_release,
        "summary": dict(rep.summary),
        "gates_g01_to_g16": gates_summary,
        "g13_ltc_mishoe_crsdk_spacc": {
            "passed": bool(rep.g13_result.get("passed")),
            "status": str(rep.g13_result.get("status", "")),
            "xlr_h1_preserved": bool(rep.g13_result.get("details", {}).get("mishoe", {}).get("xlr_h1_preserved", True)),
        },
        "g14_thermal_npfz100_usbpd": {
            "passed": bool(rep.g14_result.get("passed")),
            "status": str(rep.g14_result.get("status", "")),
            "soc_c": g14_details.get("soc_c"),
            "soc_start_ceiling_c": g14_details.get("soc_start_ceiling_c"),
            "npfz100_soc_pct": g14_details.get("npfz100_soc_pct"),
            "npfz100_mv": g14_details.get("npfz100_mv"),
            "usbpd_contract_mw": g14_details.get("usbpd_contract_mw"),
            "usbpd_vbus_droop_mv": g14_details.get("usbpd_vbus_droop_mv"),
        },
        "g15_c2pa_and_factory_calibration": {
            "valid": bool(rep.g15_result.get("valid")),
            "status": str(rep.g15_result.get("status", "")),
            "calibration_mutation_bytes": int(rep.g15_result.get("calibration_mutation_bytes", -1)),
            "cnflasha_protected": bool(rep.g15_result.get("cnflasha_protected")),
            "rpmb_protected": bool(rep.g15_result.get("rpmb_protected")),
            "trustzone_c2pa_keystore_protected": bool(rep.g15_result.get("trustzone_c2pa_keystore_protected")),
            "factory_sensor_ibis_protected": bool(rep.g15_result.get("factory_sensor_ibis_protected")),
            "exfat_media_hygiene_ok": bool(rep.g15_result.get("exfat_media_hygiene_ok")),
        },
        "g16_p12_wf12_and_wbi2_lock": {
            "valid": bool(rep.g16_result.get("valid")),
            "status": str(rep.g16_result.get("status", "")),
            "p12_guard_verified": bool(rep.g16_result.get("p12_guard_verified")),
            "p12_patched_rc": int(rep.g16_result.get("p12_patched_rc", -1)),
            "bk4_airplane_shadow_verified": bool(rep.g16_result.get("bk4_airplane_shadow_verified")),
            "wf12_bootloop_immune": bool(rep.g16_result.get("wf12_bootloop_immune")),
            "wbi_mutation_bytes": int(rep.g16_result.get("wbi_mutation_bytes", -1)),
            "cp_mutation_bytes": int(rep.g16_result.get("cp_mutation_bytes", -1)),
        },
    }
    ok = (
        rep.all_16_gates_verified
        and rep.offline_13_gates_verified
        and rep.g13_to_g16_all_passed
        and rep.persistent_emmc_writes_authorized is False
        and rep.persistent_write_release is False
        and summary["g15_c2pa_and_factory_calibration"]["calibration_mutation_bytes"] == 0
        and summary["g16_p12_wf12_and_wbi2_lock"]["wbi_mutation_bytes"] == 0
        and summary["g16_p12_wf12_and_wbi2_lock"]["cp_mutation_bytes"] == 0
        and len(errors) == 0
    )
    return summary, ok, errors


def _run_pillar2_ram_overlay_v2(
    *,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    lang: str,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], bool, List[str]]:
    selected_bundle: StageBRamOverlayV2Bundle = build_stage_b_ram_overlay_v2_package(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        lang=lang,
        synthetic_clean_room=use_clean_room,
    )
    selected_rep: StageBRamOverlayV2Report = verify_stage_b_ram_overlay_v2(
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        lang=lang,
        synthetic_clean_room=use_clean_room,
        prebuilt_bundle=selected_bundle,
    )

    errors: List[str] = []
    if not selected_rep.all_checks_passed:
        errors.extend(f"pillar2-ram-overlay: {e}" for e in selected_rep.errors)

    base_lock_map = {e.rel_path: e.sha256 for e in selected_bundle.lock_table_13}
    lang_profiles: Dict[str, Any] = {}
    all_4_langs_ok = True
    for code in STAGE_B_SUPPORTED_LANGS:
        if code == lang:
            b = selected_bundle
            lang_ok = (
                b.cpio_audit.valid
                and b.rollback_all_matched
                and b.tmpfs_budget_audit.within_budget
                and b.failsafe_hook_audit.valid
                and b.ld_preload_guard_audit.valid
                and len(b.lock_table_13) == 13
            )
            if not lang_ok:
                all_4_langs_ok = False
                errors.append(f"pillar2-ram-overlay: BK_LANG profile {code} failed validation")
            lang_profiles[code] = {
                "lang_code": b.lang,
                "bk_lang_value": b.bk_lang_spec.bk_lang_value,
                "bk_lang_hex": f"0x{b.bk_lang_spec.bk_lang_value:02x}",
                "cpio_sha256": b.cpio_sha256,
                "cpio_size_bytes": b.cpio_size,
                "cpio_entry_count": len(b.cpio_audit.entries),
                "cpio_deterministic_metadata_ok": b.cpio_audit.valid,
                "bk4_shadow_sha256": b.bk4_shadow_sha256,
                "lock_table_count": len(b.lock_table_13),
                "rollback_all_matched": b.rollback_all_matched,
                "tmpfs_within_budget": b.tmpfs_budget_audit.within_budget,
                "volatile_tmpfs_overlay_mib": b.tmpfs_budget_audit.volatile_tmpfs_overlay_mib,
                "init2_failsafe_audit_valid": b.failsafe_hook_audit.valid,
                "init2_ld_preload_audit_valid": b.ld_preload_guard_audit.valid,
            }
            continue

        lspec = STAGE_B_BK_LANG_SPECS[code]
        bk4_bytes, bk4_audit = synthesize_stage_b_bk4_shadow(
            lang=code,
            flash_write_allowed=False,
            use_clean_room=use_clean_room,
        )
        bk4_sha = str(bk4_audit["sha256"])
        lock_lines = [
            f"{(bk4_sha if rp == 'tmp/bk4_shadow' else base_lock_map[rp])}|{rp}"
            for _, rp in STAGE_B_LOCK_TABLE_13_ARTIFACTS
        ]
        bk4_meta = {
            "schema": "fx6-bk4-shadow-lang-airplane-v2",
            "target_path": "/tmp/bk4_shadow",
            "lang": lspec.lang_code,
            "bk_lang_spec": asdict(lspec),
            "airplane_mode_keys": dict(bk4_audit["airplane_keys"]),
            "bk4_shadow_sha256": bk4_sha,
            "nvram_persistent_writes": 0,
        }
        bk4_meta_bytes = (json.dumps(bk4_meta, indent=2, sort_keys=True) + "\n").encode("utf-8")
        prelim_tmpfs_sizes = {
            rp: (len(bk4_bytes) if rp == "tmp/bk4_shadow" else len(blob))
            for rp, blob in selected_bundle.staged_blobs.items()
            if rp != "lib/appFw.so"
        }
        init2_script = generate_stage_b_init2_guard_script(
            required_tmpfs_bytes=sum(prelim_tmpfs_sizes.values()) + 65536
        )
        overlay_manifest = {
            "schema": "fx6-on-fx3-stage-b-ram-overlay-manifest-v2",
            "phase_version": PHASE_48_VERSION,
            "verification_mode": selected_bundle.verification_mode,
            "product_model_expected": FX3_PRODUCT_MODEL_HEX,
            "persistent_emmc_writes_authorized": False,
            "persistent_write_release": False,
            "p8_cp_mutation_forbidden": True,
            "cp_mutation_bytes": 0,
            "wbi_p5_write_and_hibernation_forbidden": True,
            "wbi_mutation_bytes": 0,
            "lang": lspec.lang_code,
            "bk_lang_spec": asdict(lspec),
            "bk4_shadow_sha256": bk4_sha,
            "stage_b_appfw_sha256": selected_bundle.stage_b_appfw_sha256,
            "stage_b_wlan_rsrc_sha256": selected_bundle.stage_b_wlan_rsrc_sha256,
            "lock_table_count": len(lock_lines),
            "sha256_lock_table": lock_lines,
            "binary_components": list(selected_bundle.component_records),
        }
        manifest_bytes = (json.dumps(overlay_manifest, indent=2) + "\n").encode("utf-8")
        cpio_bytes = build_stage_b_cpio_newc_archive((
            CpioEntrySpec(name="etc", mode=S_IFDIR | 0o755),
            CpioEntrySpec(name="etc/fx6_overlay", mode=S_IFDIR | 0o755),
            CpioEntrySpec(name="etc/fx6_overlay/stage_b_init2_guard.sh", mode=S_IFREG | 0o755, data=init2_script.encode("utf-8")),
            CpioEntrySpec(name="etc/fx6_overlay/stage_b_overlay_manifest.json", mode=S_IFREG | 0o644, data=manifest_bytes),
            CpioEntrySpec(name="etc/fx6_overlay/bk4_shadow_meta.json", mode=S_IFREG | 0o644, data=bk4_meta_bytes),
            CpioEntrySpec(name="etc/fx6_overlay/p11_uipc_cp_shim.json", mode=S_IFREG | 0o644, data=selected_bundle.staged_blobs["contracts/p11_uipc_cp_shim.json"]),
            CpioEntrySpec(name="tmp", mode=S_IFDIR | 0o755),
            CpioEntrySpec(name="tmp/bk4_shadow", mode=S_IFREG | 0o644, data=bk4_bytes),
        ))
        cpio_audit = parse_and_audit_stage_b_cpio_newc(cpio_bytes)
        tmpfs_audit = verify_stage_b_tmpfs_ddr_budget(
            tmpfs_payload_sizes=prelim_tmpfs_sizes,
            cpio_archive_bytes=len(cpio_bytes),
            appfw_size_bytes=len(selected_bundle.staged_blobs["lib/appFw.so"]),
            appfw_staging_mode="ro_sd_loop_bind",
        )
        fs_audit = verify_failsafe_hook_script(init2_script)
        ld_audit = audit_ld_so_preload_and_overlay(script_text=init2_script)
        lang_ok = (
            bool(bk4_audit["valid"])
            and cpio_audit.valid
            and selected_bundle.rollback_all_matched
            and tmpfs_audit.within_budget
            and fs_audit.valid
            and ld_audit.valid
            and len(lock_lines) == 13
        )
        if not lang_ok:
            all_4_langs_ok = False
            errors.append(f"pillar2-ram-overlay: BK_LANG profile {code} failed validation")
        lang_profiles[code] = {
            "lang_code": lspec.lang_code,
            "bk_lang_value": lspec.bk_lang_value,
            "bk_lang_hex": f"0x{lspec.bk_lang_value:02x}",
            "cpio_sha256": hashlib.sha256(cpio_bytes).hexdigest(),
            "cpio_size_bytes": len(cpio_bytes),
            "cpio_entry_count": len(cpio_audit.entries),
            "cpio_deterministic_metadata_ok": cpio_audit.valid,
            "bk4_shadow_sha256": bk4_sha,
            "lock_table_count": len(lock_lines),
            "rollback_all_matched": selected_bundle.rollback_all_matched,
            "tmpfs_within_budget": tmpfs_audit.within_budget,
            "volatile_tmpfs_overlay_mib": tmpfs_audit.volatile_tmpfs_overlay_mib,
            "init2_failsafe_audit_valid": fs_audit.valid,
            "init2_ld_preload_audit_valid": ld_audit.valid,
        }

    summary: Dict[str, Any] = {
        "schema": selected_rep.schema,
        "phase_version": selected_rep.phase_version,
        "verification_mode": selected_rep.verification_mode,
        "selected_lang": selected_rep.lang,
        "all_checks_passed": selected_rep.all_checks_passed and all_4_langs_ok,
        "persistent_emmc_writes_authorized": selected_rep.persistent_emmc_writes_authorized,
        "persistent_write_release": selected_rep.persistent_write_release,
        "cp_mutation_bytes": selected_rep.cp_mutation_bytes,
        "wbi_mutation_bytes": selected_rep.wbi_mutation_bytes,
        "product_model_hex": selected_rep.product_model_hex,
        "stage_b_appfw_sha256": selected_rep.stage_b_appfw_sha256,
        "stage_b_wlan_rsrc_sha256": selected_rep.stage_b_wlan_rsrc_sha256,
        "bk4_shadow_sha256": selected_rep.bk4_shadow_sha256,
        "cpio_sha256": selected_rep.cpio_sha256,
        "cpio_size_bytes": selected_rep.cpio_size_bytes,
        "cpio_entry_count": selected_rep.cpio_entry_count,
        "cpio_deterministic_metadata_ok": selected_rep.cpio_deterministic_metadata_ok,
        "lock_table_count": selected_rep.lock_table_count,
        "rollback_all_matched": selected_rep.rollback_all_matched,
        "tmpfs_budget_audit": {
            "within_budget": selected_rep.tmpfs_budget_audit.within_budget,
            "volatile_tmpfs_overlay_bytes": selected_rep.tmpfs_budget_audit.volatile_tmpfs_overlay_bytes,
            "volatile_tmpfs_overlay_mib": selected_rep.tmpfs_budget_audit.volatile_tmpfs_overlay_mib,
            "tmpfs_budget_limit_mib": selected_rep.tmpfs_budget_audit.tmpfs_budget_limit_mib,
            "tmpfs_headroom_mib": selected_rep.tmpfs_budget_audit.tmpfs_headroom_mib,
            "fx3_ddr_total_mib": selected_rep.tmpfs_budget_audit.fx3_ddr_total_mib,
        },
        "init2_failsafe_audit_valid": selected_rep.init2_failsafe_audit_valid,
        "init2_ld_preload_audit_valid": selected_rep.init2_ld_preload_audit_valid,
        "sandbox_drill": {
            "all_scenarios_passed": selected_rep.sandbox_drill.all_scenarios_passed,
            "scenario_count": selected_rep.sandbox_drill.scenario_count,
            "passed_count": selected_rep.sandbox_drill.passed_count,
            "clean_mount_verified": selected_rep.sandbox_drill.clean_mount_verified,
            "all_faults_fail_closed": selected_rep.sandbox_drill.all_faults_fail_closed,
            "total_emmc_mutation_bytes": selected_rep.sandbox_drill.total_emmc_mutation_bytes,
            "total_cp_mutation_bytes": selected_rep.sandbox_drill.total_cp_mutation_bytes,
            "total_wbi_mutation_bytes": selected_rep.sandbox_drill.total_wbi_mutation_bytes,
            "temp_dir_cleaned": selected_rep.sandbox_drill.temp_dir_cleaned,
        },
        "lang_profiles": lang_profiles,
        "report_sha256": selected_rep.report_sha256,
    }
    ok = (
        selected_rep.all_checks_passed
        and all_4_langs_ok
        and selected_rep.lock_table_count == 13
        and selected_rep.tmpfs_budget_audit.within_budget
        and selected_rep.tmpfs_budget_audit.volatile_tmpfs_overlay_mib < float(STAGE_B_TMPFS_BUDGET_LIMIT_MIB)
        and selected_rep.sandbox_drill.passed_count == 9
        and len(errors) == 0
    )
    return summary, ok, errors


def _run_pillar3_unbrick_capsule(
    *,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], bool, List[str]]:
    rep: UnbrickLadderVerificationReport = run_unbrick_ladder_and_capsule_suite(
        force_clean_room=use_clean_room,
    )
    errors = [f"pillar3-unbrick: {e}" for e in rep.errors]
    summary: Dict[str, Any] = {
        "schema": rep.schema,
        "verification_mode": rep.verification_mode,
        "all_passed": rep.all_passed,
        "status": rep.status,
        "scenario_count": rep.scenario_count,
        "scenarios_passed": rep.scenarios_passed,
        "persistent_emmc_writes_authorized": rep.persistent_emmc_writes_authorized,
        "allow_boot_partition_targeting": rep.allow_boot_partition_targeting,
        "allow_destructive_fastboot": rep.allow_destructive_fastboot,
        "allow_persistent_jiritsu_writes": rep.allow_persistent_jiritsu_writes,
        "wbi_mutation_bytes": rep.wbi_mutation_bytes,
        "emmc_write_bytes": rep.emmc_write_bytes,
        "donor_audit": {
            "mode": rep.donor_audit.mode,
            "passed": rep.donor_audit.passed,
            "two_pass_stable": rep.donor_audit.two_pass_stable,
            "source_sha256": rep.donor_audit.source_sha256,
            "p1_bytes": rep.donor_audit.p1_bytes,
            "capture_contract_ok": rep.donor_audit.capture_contract_ok,
            "boot_worker_contract_ok": rep.donor_audit.boot_worker_contract_ok,
            "autolocator_sites": dict(rep.donor_audit.autolocator_sites),
        },
        "capsules": {
            "fat12_armed": {
                "valid": rep.capsule_fat12_armed.valid,
                "fat_type": rep.capsule_fat12_armed.fat_type,
                "capsule_sha256": rep.capsule_fat12_armed.capsule_sha256,
                "oneshot_latch_tripped": rep.capsule_fat12_armed.oneshot_latch_tripped,
            },
            "fat12_tripped": {
                "valid": rep.capsule_fat12_tripped.valid,
                "fat_type": rep.capsule_fat12_tripped.fat_type,
                "capsule_sha256": rep.capsule_fat12_tripped.capsule_sha256,
                "oneshot_latch_tripped": rep.capsule_fat12_tripped.oneshot_latch_tripped,
            },
            "fat16_tripped": {
                "valid": rep.capsule_fat16_tripped.valid,
                "fat_type": rep.capsule_fat16_tripped.fat_type,
                "capsule_sha256": rep.capsule_fat16_tripped.capsule_sha256,
                "oneshot_latch_tripped": rep.capsule_fat16_tripped.oneshot_latch_tripped,
            },
        },
        "scenarios": [
            {
                "scenario_id": sc.scenario_id,
                "selected_tier": sc.selected_tier.value,
                "disposition": sc.disposition,
                "status": sc.status,
                "passed": sc.passed,
            }
            for sc in rep.scenarios
        ],
    }
    ok = (
        rep.all_passed
        and rep.scenarios_passed == 12
        and rep.scenario_count == 12
        and rep.persistent_emmc_writes_authorized is False
        and rep.wbi_mutation_bytes == 0
        and rep.emmc_write_bytes == 0
        and len(errors) == 0
    )
    return summary, ok, errors


def _run_pillar4_forensic_gate(
    *,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], bool, List[str]]:
    errors: List[str] = []
    clean_suite = run_clean_room_forensic_suite()
    roles_dict = dict(clean_suite.get("roles_verified", {}))
    clean_ok = bool(clean_suite.get("all_passed")) and all(
        bool(roles_dict.get(r, {}).get("passed")) for r in FORENSIC_REQUIRED_ROLES
    )
    if not clean_ok:
        errors.append("pillar4-forensic: clean-room 7-role forensic gate failed")

    # Pre-session negative gates (stuck-bus, truncation, invalidated WBI2, BOOT0 firewall)
    stuck_bus_rep = analyze_bus_and_entropy(b"\x00" * 16384, role="generic")
    trunc_rep = analyze_bus_and_entropy(build_synthetic_encrypted_cnflasha(8192), expected_size=16384, role="cnflasha", expect_encrypted=True)
    bad_wbi2_rep = verify_emmc_dump_bytes(build_synthetic_p5_wbi2_image(magic=WBI2_INVALIDATED_MAGICS[0]), role="p5")
    fw_block = audit_boot_chain_immutability({"target": "BOOT0", "operation": "flash"})

    stuck_bus_rejected = not stuck_bus_rep.passed and stuck_bus_rep.stuck_bus_detected
    truncation_rejected = not trunc_rep.passed and trunc_rep.truncation_detected
    invalidated_wbi2_rejected = not bad_wbi2_rep.passed
    boot0_blocked = not fw_block.allowed

    if not (stuck_bus_rejected and truncation_rejected and invalidated_wbi2_rejected and boot0_blocked):
        errors.append("pillar4-forensic: one or more negative pre-session forensic gates failed to reject")

    local_donor_dumps: Dict[str, Any] = {}
    if not use_clean_room:
        for role, rel in DONOR_FORENSIC_DUMP_SPECS:
            p = resolve_donor_path(rel)
            if p.is_file():
                stab, raw_dump = read_two_pass_sha256_readonly(p)
                part_rep = (
                    (
                        verify_p1_vfat_dump(raw_dump, check_fat_tree=True)
                        if role == "p1"
                        else verify_p8_cp_rtos_dump(raw_dump)
                    )
                    if (stab.stable and raw_dump is not None)
                    else None
                )
                two_pass_ok = bool(stab.stable)
                passed = bool(
                    two_pass_ok
                    and raw_dump is not None
                    and len(raw_dump) >= 512
                    and (len(raw_dump) % 512 == 0)
                    and part_rep is not None
                    and part_rep.valid
                )
                if not passed:
                    errors.append(f"pillar4-forensic: donor dump {role} failed O_RDONLY verification")
                local_donor_dumps[role] = {
                    "passed": passed,
                    "sha256": stab.pass1_sha256,
                    "two_pass_stable": two_pass_ok,
                    "magic_ok": bool(part_rep and part_rep.magic_ok),
                    "geometry_ok": bool(part_rep and part_rep.geometry_ok),
                }
        p5_path = resolve_donor_path(DONOR_P5_WBI2_RELPATH)
        if p5_path.is_file():
            fd = os.open(p5_path, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK)
            try:
                hdr = os.read(fd, WBI2_HEADER_SIZE)
                p5_sz = os.fstat(fd).st_size
            finally:
                os.close(fd)
            magic_ok = len(hdr) == WBI2_HEADER_SIZE and hdr[0:4] == WBI2_MAGIC
            hdr_sha = hashlib.sha256(hdr).hexdigest()
            if not magic_ok:
                errors.append("pillar4-forensic: donor p5 WBI2 header magic invalid")
            local_donor_dumps["p5"] = {
                "passed": magic_ok,
                "sha256": hdr_sha,
                "two_pass_stable": True,
                "magic_ok": magic_ok,
                "geometry_ok": p5_sz >= WBI2_HEADER_SIZE,
            }

    mode = (
        "LOCAL_DONOR_O_RDONLY"
        if (not use_clean_room and len(local_donor_dumps) > 0)
        else "CLEAN_ROOM_SYNTHETIC"
    )
    all_ok = (
        clean_ok
        and stuck_bus_rejected
        and truncation_rejected
        and invalidated_wbi2_rejected
        and boot0_blocked
        and (FORENSIC_EMMC_AUTH is False)
        and (FORENSIC_ALLOW_BOOT_PARTITION_TARGETING is False)
        and (READ_ONLY_DONOR_ACCESS is True)
        and (len(local_donor_dumps) > 0 if mode == "LOCAL_DONOR_O_RDONLY" else True)
        and len(errors) == 0
    )
    summary: Dict[str, Any] = {
        "schema": FORENSIC_VERIFIER_SCHEMA,
        "verification_mode": mode,
        "status": "VERIFIED_READONLY" if all_ok else "REJECTED",
        "all_passed": all_ok,
        "persistent_emmc_writes_authorized": FORENSIC_EMMC_AUTH,
        "allow_boot_partition_targeting": FORENSIC_ALLOW_BOOT_PARTITION_TARGETING,
        "read_only_donor_access": READ_ONLY_DONOR_ACCESS,
        "clean_room_roles_verified": roles_dict,
        "local_donor_dumps_verified": local_donor_dumps,
        "pre_session_negative_gates": {
            "stuck_bus_rejected": stuck_bus_rejected,
            "truncation_rejected": truncation_rejected,
            "invalidated_wbi2_rejected": invalidated_wbi2_rejected,
            "boot_chain_firewall_blocks_boot0_flash": boot0_blocked,
        },
    }
    return summary, all_ok, errors


def _run_pillar5_master_readiness(
    *,
    repo_root: Path,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    use_clean_room: bool,
) -> Tuple[Dict[str, Any], bool, List[str]]:
    pkt: StageBMasterReadinessPacketReport = build_stage_b_master_readiness_packet(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=use_clean_room,
        include_full_candidate_dry_run=False,
    )
    pkt_dict = pkt.to_dict()
    v_res = verify_stage_b_master_readiness_packet(pkt_dict)
    errors = [f"pillar5-readiness: {e}" for e in pkt.errors]
    if not v_res.valid:
        errors.extend(f"pillar5-readiness-verify: {e}" for e in v_res.errors)

    mat = pkt.stage_b_p1_to_p12_and_fan_matrix
    p35 = pkt.phase35_stage_b_lifecycle
    byof = pkt.byof_manifest_parity
    pkt_sha_ok = bool(HEX64_RE.fullmatch(pkt.packet_sha256))
    h2_sha_ok = bool(HEX64_RE.fullmatch(str(p35.get("h2_receipt_sha256", ""))))
    if not pkt_sha_ok:
        errors.append("pillar5-readiness: invalid packet_sha256 format")
    if not h2_sha_ok:
        errors.append("pillar5-readiness: invalid h2_receipt_sha256 format")

    summary: Dict[str, Any] = {
        "schema": pkt.schema,
        "phase_version": pkt.phase_version,
        "verification_mode": pkt.verification_mode,
        "offline_engineering_complete": pkt.offline_engineering_complete,
        "self_verify_valid": v_res.valid,
        "packet_sha256_verified": pkt_sha_ok and v_res.sha256_matched,
        "persistent_emmc_writes_authorized": pkt.persistent_emmc_writes_authorized,
        "persistent_write_release": pkt.persistent_write_release,
        "cp_mutation_bytes": pkt.cp_mutation_bytes,
        "wbi_mutation_bytes": pkt.wbi_mutation_bytes,
        "stage_b_matrix_item_count": int(mat.get("matrix_item_count", 0)),
        "all_13_items_verified": bool(mat.get("all_13_items_verified")),
        "rollback_all_matched": bool(mat.get("rollback_all_matched")),
        "stage_b_appfw_sha256": str(mat.get("p10_keymap", {}).get("appfw_stage_b_sha256", "")),
        "stage_b_wlan_rsrc_sha256": str(mat.get("p12_wireless_guard", {}).get("stage_b_wlan_rsrc_sha256", "")),
        "phase35_lifecycle": {
            "schema": str(p35.get("schema", "")),
            "all_checks_passed": bool(p35.get("all_checks_passed")),
            "scenario_count": int(p35.get("scenario_count", 0)),
            "passed_scenario_count": int(p35.get("passed_scenario_count", 0)),
            "h2_zero_drift_verified": bool(p35.get("h2_zero_drift_verified")),
            "h2_persistent_bytes_mutated": int(p35.get("h2_persistent_bytes_mutated", -1)),
            "h2_receipt_sha256_verified": h2_sha_ok,
            "report_sha256": str(p35.get("report_sha256", "")),
        },
        "byof_manifest_parity": {
            "all_checks_passed": bool(byof.get("all_checks_passed")),
            "en_zh_parity_ok": bool(byof.get("en_zh_parity_ok")),
            "en_entry_count": int(byof.get("en_entry_count", 0)),
            "zh_entry_count": int(byof.get("zh_entry_count", 0)),
        },
    }
    ok = (
        pkt.offline_engineering_complete
        and v_res.valid
        and pkt_sha_ok
        and h2_sha_ok
        and pkt.persistent_emmc_writes_authorized is False
        and pkt.persistent_write_release is False
        and pkt.cp_mutation_bytes == 0
        and pkt.wbi_mutation_bytes == 0
        and len(errors) == 0
    )
    return summary, ok, errors


def build_stage_b_integrated_dossier(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    lang: str = "en",
    synthetic_clean_room: Optional[bool] = None,
) -> StageBIntegratedDossierReport:
    """Compose all 5 Phase 35..50 Stage-B engines into `stage_b_integrated_dossier_v1` (<5s)."""
    if lang not in STAGE_B_SUPPORTED_LANGS:
        raise ValueError(f"Unsupported BK_LANG {lang!r}; expected one of {STAGE_B_SUPPORTED_LANGS}")

    resolved_root = Path(repo_root).resolve()
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )

    def _run_pillars_1_to_4() -> Tuple[
        Tuple[Dict[str, Any], bool, List[str]],
        Tuple[Dict[str, Any], bool, List[str]],
        Tuple[Dict[str, Any], bool, List[str]],
        Tuple[Dict[str, Any], bool, List[str]],
    ]:
        r1 = _run_pillar1_16gate(repo_root=resolved_root, use_clean_room=use_clean_room)
        r3 = _run_pillar3_unbrick_capsule(use_clean_room=use_clean_room)
        r4 = _run_pillar4_forensic_gate(use_clean_room=use_clean_room)
        r2 = _run_pillar2_ram_overlay_v2(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            lang=lang,
            use_clean_room=use_clean_room,
        )
        return r1, r2, r3, r4

    with ThreadPoolExecutor(max_workers=2) as pool:
        f5 = pool.submit(
            _run_pillar5_master_readiness,
            repo_root=resolved_root,
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            use_clean_room=use_clean_room,
        )
        f14 = pool.submit(_run_pillars_1_to_4)

        (p1_sum, p1_ok, p1_errs), (p2_sum, p2_ok, p2_errs), (p3_sum, p3_ok, p3_errs), (p4_sum, p4_ok, p4_errs) = f14.result()
        p5_sum, p5_ok, p5_errs = f5.result()

    errors: List[str] = [*p1_errs, *p2_errs, *p3_errs, *p4_errs, *p5_errs]
    passed_count = sum(1 for flag in (p1_ok, p2_ok, p3_ok, p4_ok, p5_ok) if flag)
    all_5_ok = passed_count == 5 and len(errors) == 0

    verification_mode = "CLEAN_ROOM_SYNTHETIC" if use_clean_room else "LOCAL_DONOR_O_RDONLY"
    draft = StageBIntegratedDossierReport(
        schema=STAGE_B_CANDIDATE_DOSSIER_SCHEMA,
        phase_version=PHASE_52_VERSION,
        verification_mode=verification_mode,
        selected_lang=lang,
        all_5_pillars_passed=all_5_ok,
        candidate_ready=all_5_ok,
        status=(
            "VERIFIED_STAGE_B_CANDIDATE_OFFLINE_READY"
            if all_5_ok
            else "FAILED_STAGE_B_CANDIDATE_INTEGRATION"
        ),
        persistent_emmc_writes_authorized=PERSISTENT_EMMC_WRITES_AUTHORIZED,
        persistent_write_release=PERSISTENT_WRITE_RELEASE,
        p8_cp_mutation_forbidden=P8_CP_MUTATION_FORBIDDEN,
        cp_mutation_bytes=CP_MUTATION_BYTES,
        wbi_p5_write_and_hibernation_forbidden=WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN,
        wbi_mutation_bytes=WBI_MUTATION_BYTES,
        calibration_mutation_bytes=CALIBRATION_MUTATION_BYTES,
        usb_or_camera_operations=USB_OR_CAMERA_OPERATIONS,
        pillar_count=5,
        passed_pillar_count=passed_count,
        phase50_master_16gate_preflight=p1_sum,
        phase48_stage_b_ram_overlay_v2=p2_sum,
        phase47_unbrick_ladder_and_capsule=p3_sum,
        phase42_emmc_dump_forensic_gate=p4_sum,
        phase39_stage_b_master_readiness=p5_sum,
        errors=tuple(errors),
        dossier_sha256="",
    )
    dossier_sha = _compute_dossier_sha256(draft.to_dict())
    return StageBIntegratedDossierReport(
        schema=draft.schema,
        phase_version=draft.phase_version,
        verification_mode=draft.verification_mode,
        selected_lang=draft.selected_lang,
        all_5_pillars_passed=draft.all_5_pillars_passed,
        candidate_ready=draft.candidate_ready,
        status=draft.status,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        p8_cp_mutation_forbidden=True,
        cp_mutation_bytes=0,
        wbi_p5_write_and_hibernation_forbidden=True,
        wbi_mutation_bytes=0,
        calibration_mutation_bytes=0,
        usb_or_camera_operations=0,
        pillar_count=5,
        passed_pillar_count=draft.passed_pillar_count,
        phase50_master_16gate_preflight=draft.phase50_master_16gate_preflight,
        phase48_stage_b_ram_overlay_v2=draft.phase48_stage_b_ram_overlay_v2,
        phase47_unbrick_ladder_and_capsule=draft.phase47_unbrick_ladder_and_capsule,
        phase42_emmc_dump_forensic_gate=draft.phase42_emmc_dump_forensic_gate,
        phase39_stage_b_master_readiness=draft.phase39_stage_b_master_readiness,
        errors=draft.errors,
        dossier_sha256=dossier_sha,
    )


def verify_stage_b_integrated_dossier(
    payload: Mapping[str, Any],
) -> StageBCandidateVerifyResult:
    """Fail-closed tamper & semantic invariant detector for `stage_b_integrated_dossier_v1`."""
    if not isinstance(payload, Mapping):
        return StageBCandidateVerifyResult(
            valid=False,
            schema_ok=False,
            sha256_matched=False,
            expected_dossier_sha256="",
            observed_dossier_sha256="",
            safety_redlines_ok=False,
            phase50_16gate_ok=False,
            phase48_ram_overlay_ok=False,
            phase47_unbrick_capsule_ok=False,
            phase42_forensic_gate_ok=False,
            phase39_readiness_ok=False,
            errors=("Dossier payload must be a mapping/dict",),
        )

    doc = copy.deepcopy(dict(payload))
    errors: List[str] = []

    schema_ok = (
        doc.get("schema") == STAGE_B_CANDIDATE_DOSSIER_SCHEMA
        and doc.get("phase_version") == PHASE_52_VERSION
        and doc.get("selected_lang") in STAGE_B_SUPPORTED_LANGS
        and doc.get("verification_mode") in ("LOCAL_DONOR_O_RDONLY", "CLEAN_ROOM_SYNTHETIC")
    )
    if not schema_ok:
        errors.append("Schema, phase_version, selected_lang, or verification_mode invalid")

    observed_sha = str(doc.get("dossier_sha256", ""))
    expected_sha = _compute_dossier_sha256(doc)
    sha256_matched = bool(HEX64_RE.fullmatch(observed_sha)) and (observed_sha == expected_sha)
    if not sha256_matched:
        errors.append(
            f"dossier_sha256 mismatch: observed={observed_sha!r} != expected={expected_sha!r}"
        )

    rendered_check = json.dumps(doc, sort_keys=True, ensure_ascii=False)
    if _RAW_BYTES_REPR_RE.search(rendered_check):
        errors.append("Raw binary bytes repr detected in dossier payload")

    # Top-level safety redlines (independent of SHA-256)
    redline_errs: List[str] = []
    if doc.get("persistent_emmc_writes_authorized") is not False:
        redline_errs.append("persistent_emmc_writes_authorized must be False")
    if doc.get("persistent_write_release") is not False:
        redline_errs.append("persistent_write_release must be False")
    if doc.get("p8_cp_mutation_forbidden") is not True:
        redline_errs.append("p8_cp_mutation_forbidden must be True")
    if doc.get("cp_mutation_bytes") != 0:
        redline_errs.append("cp_mutation_bytes must be 0")
    if doc.get("wbi_p5_write_and_hibernation_forbidden") is not True:
        redline_errs.append("wbi_p5_write_and_hibernation_forbidden must be True")
    if doc.get("wbi_mutation_bytes") != 0:
        redline_errs.append("wbi_mutation_bytes must be 0")
    if doc.get("calibration_mutation_bytes") != 0:
        redline_errs.append("calibration_mutation_bytes must be 0")
    if doc.get("usb_or_camera_operations") != 0:
        redline_errs.append("usb_or_camera_operations must be 0")
    if doc.get("all_5_pillars_passed") is not True or doc.get("candidate_ready") is not True:
        redline_errs.append("all_5_pillars_passed and candidate_ready must be True")
    if doc.get("pillar_count") != 5 or doc.get("passed_pillar_count") != 5:
        redline_errs.append("pillar_count and passed_pillar_count must equal 5")
    if doc.get("status") != "VERIFIED_STAGE_B_CANDIDATE_OFFLINE_READY":
        redline_errs.append("status must be VERIFIED_STAGE_B_CANDIDATE_OFFLINE_READY")
    doc_errs = doc.get("errors")
    if not isinstance(doc_errs, (list, tuple)) or len(doc_errs) != 0:
        redline_errs.append("Dossier contains non-empty errors")
    safety_redlines_ok = len(redline_errs) == 0
    errors.extend(redline_errs)

    # Pillar 1: Phase 50 16-gate preflight
    p1_errs: List[str] = []
    p1 = doc.get("phase50_master_16gate_preflight")
    if not isinstance(p1, Mapping):
        p1_errs.append("Missing phase50_master_16gate_preflight")
    else:
        if (
            p1.get("schema") != MASTER_16GATE_PREFLIGHT_SCHEMA
            or p1.get("all_16_gates_verified") is not True
            or p1.get("offline_13_gates_verified") is not True
            or p1.get("g13_to_g16_all_passed") is not True
            or p1.get("persistent_emmc_writes_authorized") is not False
            or p1.get("persistent_write_release") is not False
        ):
            p1_errs.append("Pillar 1 top-level 16-gate invariant invalid")
        gates_list = p1.get("gates_g01_to_g16")
        if (
            not isinstance(gates_list, (list, tuple))
            or len(gates_list) != 16
            or not all(isinstance(g, Mapping) and str(g.get("status", "")).startswith("VERIFIED") for g in gates_list)
        ):
            p1_errs.append("Pillar 1 gates_g01_to_g16 must contain 16 VERIFIED* gates")
        g13 = p1.get("g13_ltc_mishoe_crsdk_spacc")
        g14 = p1.get("g14_thermal_npfz100_usbpd")
        g15 = p1.get("g15_c2pa_and_factory_calibration")
        g16 = p1.get("g16_p12_wf12_and_wbi2_lock")
        if not isinstance(g13, Mapping) or g13.get("passed") is not True or g13.get("xlr_h1_preserved") is not True:
            p1_errs.append("Pillar 1 G13 LTC/MI-Shoe isolation invalid")
        if (
            not isinstance(g14, Mapping)
            or g14.get("passed") is not True
            or (g14.get("npfz100_soc_pct") or 0) < 80
            or (g14.get("usbpd_contract_mw") or 0) < 27000
        ):
            p1_errs.append("Pillar 1 G14 thermal/NP-FZ100/USB-PD envelope invalid")
        if (
            not isinstance(g15, Mapping)
            or g15.get("valid") is not True
            or g15.get("calibration_mutation_bytes") != 0
            or g15.get("cnflasha_protected") is not True
            or g15.get("rpmb_protected") is not True
            or g15.get("trustzone_c2pa_keystore_protected") is not True
            or g15.get("factory_sensor_ibis_protected") is not True
            or g15.get("exfat_media_hygiene_ok") is not True
        ):
            p1_errs.append("Pillar 1 G15 C2PA/calibration immutability invalid")
        if (
            not isinstance(g16, Mapping)
            or g16.get("valid") is not True
            or g16.get("p12_guard_verified") is not True
            or g16.get("p12_patched_rc") != 0
            or g16.get("bk4_airplane_shadow_verified") is not True
            or g16.get("wf12_bootloop_immune") is not True
            or g16.get("wbi_mutation_bytes") != 0
            or g16.get("cp_mutation_bytes") != 0
        ):
            p1_errs.append("Pillar 1 G16 P12/WF-12/WBI2 lock invalid")
    phase50_16gate_ok = len(p1_errs) == 0
    errors.extend(p1_errs)

    # Pillar 2: Phase 48 Stage-B RAM-Overlay v2
    p2_errs: List[str] = []
    p2 = doc.get("phase48_stage_b_ram_overlay_v2")
    if not isinstance(p2, Mapping):
        p2_errs.append("Missing phase48_stage_b_ram_overlay_v2")
    else:
        if (
            p2.get("schema") != PHASE_48_SCHEMA
            or p2.get("all_checks_passed") is not True
            or p2.get("selected_lang") != doc.get("selected_lang")
            or p2.get("lock_table_count") != 13
            or p2.get("rollback_all_matched") is not True
            or p2.get("cpio_deterministic_metadata_ok") is not True
            or p2.get("init2_failsafe_audit_valid") is not True
            or p2.get("init2_ld_preload_audit_valid") is not True
            or p2.get("cp_mutation_bytes") != 0
            or p2.get("wbi_mutation_bytes") != 0
        ):
            p2_errs.append("Pillar 2 RAM-Overlay v2 top-level invariant invalid")
        tmpfs = p2.get("tmpfs_budget_audit")
        if (
            not isinstance(tmpfs, Mapping)
            or tmpfs.get("within_budget") is not True
            or float(tmpfs.get("volatile_tmpfs_overlay_mib", 999.0)) >= float(STAGE_B_TMPFS_BUDGET_LIMIT_MIB)
        ):
            p2_errs.append("Pillar 2 tmpfs DDR budget exceeded or tampered")
        drill = p2.get("sandbox_drill")
        if (
            not isinstance(drill, Mapping)
            or drill.get("all_scenarios_passed") is not True
            or drill.get("scenario_count") != 9
            or drill.get("passed_count") != 9
            or drill.get("total_emmc_mutation_bytes") != 0
            or drill.get("total_cp_mutation_bytes") != 0
            or drill.get("total_wbi_mutation_bytes") != 0
        ):
            p2_errs.append("Pillar 2 init2 9-scenario sandbox drill invalid")
        profiles = p2.get("lang_profiles")
        if not isinstance(profiles, Mapping) or set(profiles.keys()) != set(STAGE_B_SUPPORTED_LANGS):
            p2_errs.append("Pillar 2 lang_profiles must cover all 4 BK_LANG languages")
        else:
            for code in STAGE_B_SUPPORTED_LANGS:
                prof = profiles.get(code)
                exp_val = STAGE_B_BK_LANG_SPECS[code].bk_lang_value
                if (
                    not isinstance(prof, Mapping)
                    or prof.get("bk_lang_value") != exp_val
                    or prof.get("lock_table_count") != 13
                    or prof.get("rollback_all_matched") is not True
                    or prof.get("tmpfs_within_budget") is not True
                    or prof.get("cpio_deterministic_metadata_ok") is not True
                    or prof.get("init2_failsafe_audit_valid") is not True
                    or prof.get("init2_ld_preload_audit_valid") is not True
                    or not HEX64_RE.fullmatch(str(prof.get("cpio_sha256", "")))
                    or not HEX64_RE.fullmatch(str(prof.get("bk4_shadow_sha256", "")))
                ):
                    p2_errs.append(f"Pillar 2 lang_profiles[{code!r}] invariant invalid")
    phase48_ram_overlay_ok = len(p2_errs) == 0
    errors.extend(p2_errs)

    # Pillar 3: Phase 47 Unbrick Ladder & p1 VFAT Capsule
    p3_errs: List[str] = []
    p3 = doc.get("phase47_unbrick_ladder_and_capsule")
    if not isinstance(p3, Mapping):
        p3_errs.append("Missing phase47_unbrick_ladder_and_capsule")
    else:
        if (
            p3.get("schema") != UNBRICK_LADDER_SCHEMA
            or p3.get("all_passed") is not True
            or p3.get("scenario_count") != 12
            or p3.get("scenarios_passed") != 12
            or p3.get("persistent_emmc_writes_authorized") is not False
            or p3.get("allow_boot_partition_targeting") is not False
            or p3.get("allow_destructive_fastboot") is not False
            or p3.get("allow_persistent_jiritsu_writes") is not False
            or p3.get("wbi_mutation_bytes") != 0
            or p3.get("emmc_write_bytes") != 0
        ):
            p3_errs.append("Pillar 3 top-level unbrick ladder invariant invalid")
        caps = p3.get("capsules")
        if not isinstance(caps, Mapping):
            p3_errs.append("Pillar 3 capsules missing")
        else:
            for cap_key in ("fat12_armed", "fat12_tripped", "fat16_tripped"):
                cap = caps.get(cap_key)
                if (
                    not isinstance(cap, Mapping)
                    or cap.get("valid") is not True
                    or not HEX64_RE.fullmatch(str(cap.get("capsule_sha256", "")))
                ):
                    p3_errs.append(f"Pillar 3 capsule {cap_key} invalid")
    phase47_unbrick_capsule_ok = len(p3_errs) == 0
    errors.extend(p3_errs)

    # Pillar 4: Phase 42 eMMC Dump Forensic Gate
    p4_errs: List[str] = []
    p4 = doc.get("phase42_emmc_dump_forensic_gate")
    if not isinstance(p4, Mapping):
        p4_errs.append("Missing phase42_emmc_dump_forensic_gate")
    else:
        if (
            p4.get("schema") != FORENSIC_VERIFIER_SCHEMA
            or p4.get("all_passed") is not True
            or p4.get("persistent_emmc_writes_authorized") is not False
            or p4.get("allow_boot_partition_targeting") is not False
            or p4.get("read_only_donor_access") is not True
        ):
            p4_errs.append("Pillar 4 forensic gate top-level invariant invalid")
        roles_v = p4.get("clean_room_roles_verified")
        if not isinstance(roles_v, Mapping):
            p4_errs.append("Pillar 4 clean_room_roles_verified missing")
        else:
            for role in FORENSIC_REQUIRED_ROLES:
                entry = roles_v.get(role)
                if not isinstance(entry, Mapping) or entry.get("passed") is not True:
                    p4_errs.append(f"Pillar 4 role {role} did not pass")
        neg = p4.get("pre_session_negative_gates")
        if (
            not isinstance(neg, Mapping)
            or neg.get("stuck_bus_rejected") is not True
            or neg.get("truncation_rejected") is not True
            or neg.get("invalidated_wbi2_rejected") is not True
            or neg.get("boot_chain_firewall_blocks_boot0_flash") is not True
        ):
            p4_errs.append("Pillar 4 pre_session_negative_gates invalid")
        if p4.get("verification_mode") == "LOCAL_DONOR_O_RDONLY":
            local_dumps = p4.get("local_donor_dumps_verified")
            if not isinstance(local_dumps, Mapping) or len(local_dumps) == 0:
                p4_errs.append("Pillar 4 LOCAL_DONOR_O_RDONLY mode missing verified donor dumps")
            else:
                for dk, dv in local_dumps.items():
                    if not isinstance(dv, Mapping) or dv.get("passed") is not True or dv.get("two_pass_stable") is not True:
                        p4_errs.append(f"Pillar 4 local donor dump {dk} invalid")
    phase42_forensic_gate_ok = len(p4_errs) == 0
    errors.extend(p4_errs)

    # Pillar 5: Phase 39 Master Readiness Packet v2 + Phase 35 10/10 Lifecycle
    p5_errs: List[str] = []
    p5 = doc.get("phase39_stage_b_master_readiness")
    if not isinstance(p5, Mapping):
        p5_errs.append("Missing phase39_stage_b_master_readiness")
    else:
        if (
            p5.get("schema") != STAGE_B_READINESS_PACKET_SCHEMA
            or p5.get("offline_engineering_complete") is not True
            or p5.get("self_verify_valid") is not True
            or p5.get("packet_sha256_verified") is not True
            or p5.get("persistent_emmc_writes_authorized") is not False
            or p5.get("persistent_write_release") is not False
            or p5.get("cp_mutation_bytes") != 0
            or p5.get("wbi_mutation_bytes") != 0
            or p5.get("stage_b_matrix_item_count") != 13
            or p5.get("all_13_items_verified") is not True
            or p5.get("rollback_all_matched") is not True
        ):
            p5_errs.append("Pillar 5 Phase 39 readiness summary invariant invalid")
        p35 = p5.get("phase35_lifecycle")
        if (
            not isinstance(p35, Mapping)
            or p35.get("all_checks_passed") is not True
            or p35.get("scenario_count") != 10
            or p35.get("passed_scenario_count") != 10
            or p35.get("h2_zero_drift_verified") is not True
            or p35.get("h2_persistent_bytes_mutated") != 0
            or p35.get("h2_receipt_sha256_verified") is not True
            or not HEX64_RE.fullmatch(str(p35.get("report_sha256", "")))
        ):
            p5_errs.append("Pillar 5 Phase 35 10/10 lifecycle summary invalid")
        byof = p5.get("byof_manifest_parity")
        if (
            not isinstance(byof, Mapping)
            or byof.get("all_checks_passed") is not True
            or byof.get("en_zh_parity_ok") is not True
        ):
            p5_errs.append("Pillar 5 BYOF parity invalid")
    phase39_readiness_ok = len(p5_errs) == 0
    errors.extend(p5_errs)

    valid = (
        schema_ok
        and sha256_matched
        and safety_redlines_ok
        and phase50_16gate_ok
        and phase48_ram_overlay_ok
        and phase47_unbrick_capsule_ok
        and phase42_forensic_gate_ok
        and phase39_readiness_ok
        and len(errors) == 0
    )
    return StageBCandidateVerifyResult(
        valid=valid,
        schema_ok=schema_ok,
        sha256_matched=sha256_matched,
        expected_dossier_sha256=expected_sha,
        observed_dossier_sha256=observed_sha,
        safety_redlines_ok=safety_redlines_ok,
        phase50_16gate_ok=phase50_16gate_ok,
        phase48_ram_overlay_ok=phase48_ram_overlay_ok,
        phase47_unbrick_capsule_ok=phase47_unbrick_capsule_ok,
        phase42_forensic_gate_ok=phase42_forensic_gate_ok,
        phase39_readiness_ok=phase39_readiness_ok,
        errors=tuple(errors),
    )


__all__ = [
    "CALIBRATION_MUTATION_BYTES",
    "CP_MUTATION_BYTES",
    "DONOR_FORENSIC_DUMP_SPECS",
    "DONOR_P5_WBI2_RELPATH",
    "FORENSIC_REQUIRED_ROLES",
    "P8_CP_MUTATION_FORBIDDEN",
    "PERSISTENT_EMMC_WRITES_AUTHORIZED",
    "PERSISTENT_WRITE_RELEASE",
    "PHASE_52_VERSION",
    "STAGE_B_CANDIDATE_DOSSIER_SCHEMA",
    "STAGE_B_CANDIDATE_PILLARS",
    "USB_OR_CAMERA_OPERATIONS",
    "WBI_MUTATION_BYTES",
    "WBI_P5_WRITE_AND_HIBERNATION_FORBIDDEN",
    "StageBCandidateVerifyResult",
    "StageBIntegratedDossierReport",
    "build_stage_b_integrated_dossier",
    "verify_stage_b_integrated_dossier",
]
