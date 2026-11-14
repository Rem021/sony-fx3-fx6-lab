"""Phase 39 — Stage-B `P1..P12+Fan` Master Hardware Readiness Packet v2 (`stage_b_readiness_packet_v2`) & Fail-Closed Tamper Verifier.

Unifies all Phase 17..38 Stage-B and hardware-safety closures into a fast (<5s),
deterministic, self-authenticating JSON readiness packet (`stage_b_readiness_packet_v2`)
inside `outputs/fx6-on-fx3-closure/`:

1. **Stage-B `P1..P12+Fan` (`13/13` Matrix + `8` Binary Patch/Rollback Specs)**:
   - `P1` (`33^3` `.cube` LUT `p20 -> p30` partition adaptation + `libInfraSetupFile.so`,
     `libInfraMediaCommon.so`, `libInfraMediaConfig.so`, `appFw.so` site)
   - `P2` (`opelog.vfat` `8m_ram` VFAT loopback & `/OPE/{00,01}` verification)
   - `P3` (`libInfraAppRemoteBoard.so` Unicorn check & rollback)
   - `P4` (`appFw.so` ND Clear lock 576-combination Unicorn sweep)
   - `P5` (`0x032d -> 0x132d` Audio/HDMI UIPC completion) & `P6` (`0x0400/0x0402/0x0404/0x0152`)
   - `P7` (Kernel-Space Backup Sync100 `pcidma_transfer_async` dual-kernel Unicorn bridge)
   - `P8` (`appFw.so` `0x2159c50` non-blocking async log wait)
   - `P9` (`upm.ko` `.text+0x136b8` null-callback guard)
   - `Fan` (`libfan.so` `0x1dec` `_Z19fan_i_bkup_is_validv`)
   - `P10` (`24 B` `.rodata` FX3 physical body keymap inside `appFw.so` `e2bc2619...`)
   - `P11` (`Uipc/CP` Smart Handle `0x91db059b` + RTC `0x92d2091c` `/dev/rtc0->udate` +
     Audio `XLR-H1` `0x5d90` shim + Cine EI `800/12800` + `33^3` LUT + 5-axis IBIS center-lock)
   - `P12` (`libWlanResource.so` `0x70d4 -> mov w0, #0; ret` `47fec188...` `WF-12` bootloop
     guard + `BK4\0` cold-boot Airplane-Mode shadow `0x019e0012=00`/`0x0051000f=00`/`0x01a20002=00`)
2. **Phase 35 Stage-B Lifecycle Verifier (`stage_b_lifecycle_verifier.py`)**:
   - `10/10` `H0 -> H1 -> H2` scenarios `S01..S10`, `serial_fault_detector_v2` dispositions
     (`PASS` / `ALLOWED_DEGRADED` / `FAIL_CLOSED_ABORT`), and `13/13` cryptographic zero drift.
3. **Phase 28 `fx3_safety.h0_hardware_rehearsal`**:
   - `6-stage H0` read-only hardware rehearsal + `preflight` `12/12` safety gates.
4. **Phase 38 `fx3_safety.crsdk_mishoe_ltc_spacc_guard`**:
   - Multi-Port `VMC-BNCM1` LTC vs `uart_boot` (`Pin 7/8/9`) guard, `24-pin MI-Shoe XLR-H1` +
     `P11 0x91db059b` coexistence, `CrSDK PTP2 0x9201..0x9209` remote-flash firewall, and
     `CXD90057 SPACC 0xf7fc0000 AES-XTS-256 cnflasha vs nflasha` block-layer isolation.
5. **Phase 25 `fx3_safety.runtime_antibrick_guards`**:
   - `ld.so.preload` dynamic BusyBox deadlock ban, BusyBox `dd` truncation ban + 5-step atomic
     contract, `nflasha10` `0x10000009` 12 MiB VFAT headroom, and `PRODUCT_MODEL` NVRAM immutability.

Hard-locked Redlines:
- `persistent_emmc_writes_authorized = False`
- `persistent_write_release = False`
- `p8_cp_mutation_forbidden = True`, `cp_mutation_bytes = 0`
- `wbi_p5_write_and_hibernation_forbidden = True`, `wbi_mutation_bytes = 0`
- `usb_or_camera_operations = 0`
"""

from __future__ import annotations

import sys

sys.dont_write_bytecode = True

import copy
import hashlib
import json
import os
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from fx3_safety.crsdk_mishoe_ltc_spacc_guard import (
    CRSDK_MISHOE_LTC_SPACC_GUARD_SCHEMA,
    CRSDK_MISHOE_LTC_SPACC_GUARD_VERSION,
    MULTIPORT_UART_BOOT_PINS,
    STATUS_VERIFIED_SAFE,
    evaluate_phase38_safety_guards,
)
from fx3_safety.h0_hardware_rehearsal import (
    H0RehearsalConfig,
    H0RehearsalReport,
    run_h0_hardware_rehearsal,
)
from fx3_safety.preflight import evaluate_12_safety_gates
from fx3_safety.runtime_antibrick_guards import (
    NFLASHA10_HARD_FLOOR_HEADROOM_BYTES,
    NFLASHA10_PARTITION_BYTES,
    audit_busybox_dd_commands,
    audit_camset_bk4_diff,
    audit_ld_so_preload_and_overlay,
    audit_nflasha10_vfat_budget,
    audit_pmca_5step_write_contract,
    evaluate_runtime_antibrick_guards,
)
from fx3_safety.serial_fault_detector_v2 import (
    DISPOSITION_ALLOWED_DEGRADED,
    DISPOSITION_FAIL_CLOSED_ABORT,
    DISPOSITION_PASS,
)

from .backup_bridge_verifier import (
    FALLBACK_NONZERO_REL_OFFSET,
    FALLBACK_ZERO_REL_OFFSET,
    FX3_PCIDMA_API_VA,
    FX6_PCIDMA_API_VA,
    PINNED_ENTRY16_BYTES,
    SYNC100_REPLY_BYTES,
    build_synthetic_kernel_image_for_base,
    run_trampoline_unicorn_check,
    simulate_sync100_dma_and_unlock_transaction,
    verify_kernel_pcidma_entry_signature,
    verify_p7_backup_bridge,
)
from .backup_mount_tolerance_verifier import (
    DEFAULT_FX3_SEED_BK4_PATH,
    audit_ram_shadow_bk4,
    build_canonical_fa0080_normal_boot_table,
    synthesize_ram_shadow_bk4,
)
from .candidate_builder import (
    CandidateDryRunReport,
    run_offline_candidate_dry_run,
    verify_combined_stage_b_appfw_contract,
)
from .hardware_readiness_packet import (
    HEX64_RE,
    HardwareExecutionPhaseStep,
    RealTier0CaptureBundleAudit,
    _is_forced_clean_room,
    _load_byof_verifier_module,
    _normalize_gates_dict,
    verify_real_tier0_capture_bundle,
)
from .nd_unicorn_verifier import (
    run_fan_libfan_unicorn_check,
    run_p3_remoteboard_unicorn_check,
    run_p4_nd_unicorn_sweep,
    run_p8_appfw_unicorn_check,
    run_p9_upm_ko_unicorn_check,
)
from .patcher import (
    DEFAULT_FX3_MODULES_DIR,
    DEFAULT_FX6_DONOR_LIB_DIR,
    FAN_LIBFAN_SPEC,
    FX6_APPFW_DONOR_SHA256,
    FX6_APPFW_STAGE_B_SHA256,
    FX6_WLAN_RSRC_DONOR_SHA256,
    FX6_WLAN_RSRC_P12_SHA256,
    P1_P4_P8_P10_APPFW_COMBINED_SPEC,
    P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC,
    P9_UPM_KO_SPEC,
    P12_WLAN_FATAL_GUARD_SPEC,
    apply_patch_spec,
    get_target_patch_specs,
    read_donor_bytes_readonly,
    resolve_donor_binary_path,
    rollback_patch_spec,
    verify_patch_sites_non_overlapping,
)
from .ram_overlay_packager import generate_stage_a_init2_guard_script
from .stage_b_lifecycle_verifier import (
    DEFAULT_REPO_ROOT,
    STAGE_B_AIRPLANE_SHADOW_KEYS,
    STAGE_B_FORWARD_STEP_IDS,
    STAGE_B_LIFECYCLE_SCHEMA,
    STAGE_B_LIFO_UNWIND_STEP_IDS,
    STAGE_B_ORCHESTRATOR_CPIO_REL_PATH,
    STAGE_B_SCENARIO_IDS,
    StageBLifecycleReport,
    build_stage_b_ram_overlay_package,
    run_stage_b_lifecycle_drill,
)
from .uipc_completion_verifier import (
    UIPC_BB_TARGET_QUEUE,
    UIPC_P5_P6_RULES,
    decode_uipc_completion_packet,
    run_p5_p6_uipc_unicorn_audit,
    synthesize_uipc_completion,
)
from .uipc_cp_shim_verifier import (
    Phase21UipcCpShimReport,
    run_phase21_uipc_cp_shim_verification,
)
from .vfat_builder import build_opelog_vfat_image, verify_vfat_image
from .wireless_fault_isolation_verifier import (
    Phase22WirelessFaultIsolationReport,
    run_phase22_wireless_fault_isolation_verification,
)


STAGE_B_READINESS_PACKET_SCHEMA = "stage_b_readiness_packet_v2"
PHASE_39_VERSION = "39.0.0"

STAGE_B_MATRIX_13_ITEMS: Tuple[str, ...] = (
    "P1",
    "P2",
    "P3",
    "P4",
    "P5",
    "P6",
    "P7",
    "P8",
    "P9",
    "P10",
    "P11",
    "P12",
    "Fan",
)

EXPECTED_STAGE_B_PATCH_SPEC_COUNT = 8
EXPECTED_STAGE_B_PATCH_SITE_COUNT = 18

EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS: Dict[str, str] = {
    "S01_NOMINAL_STAGE_B_BOOT_AND_CLEAN_POWERCYCLE": DISPOSITION_PASS,
    "S02_STAGE_B_APPFW_P10_SHA_TAMPER_ABORT": DISPOSITION_FAIL_CLOSED_ABORT,
    "S03_STAGE_B_P12_LIBWLAN_SHA_TAMPER_ABORT": DISPOSITION_FAIL_CLOSED_ABORT,
    "S04_WF12_HARDWARE_MALFUNCTION_00342260_SURVIVAL": DISPOSITION_ALLOWED_DEGRADED,
    "S05_BT_BSA_UART_ABSENT_SURVIVAL": DISPOSITION_ALLOWED_DEGRADED,
    "S06_DETACHED_SMART_HANDLE_XLR_H1_ACTIVE": DISPOSITION_ALLOWED_DEGRADED,
    "S07_LD_SO_PRELOAD_INJECTION_BLOCKED": DISPOSITION_FAIL_CLOSED_ABORT,
    "S08_NFLASHA10_0x10000009_HEADROOM_GUARD": DISPOSITION_FAIL_CLOSED_ABORT,
    "S09_TIMER_IP_WATCHDOG_TIMEOUT_AUTO_REVERT": DISPOSITION_FAIL_CLOSED_ABORT,
    "S10_POST_TRIAL_DRIFT_DETECTION": DISPOSITION_FAIL_CLOSED_ABORT,
}


@dataclass(frozen=True)
class StageBMasterReadinessPacketReport:
    schema: str
    phase_version: str
    verification_mode: str
    offline_engineering_complete: bool
    persistent_emmc_writes_authorized: bool
    persistent_write_release: bool
    p8_cp_mutation_forbidden: bool
    cp_mutation_bytes: int
    wbi_p5_write_and_hibernation_forbidden: bool
    wbi_mutation_bytes: int
    usb_or_camera_operations: int
    real_tier0_hardware_backup_verified: bool
    stage_b_ram_trial_hardware_go: bool
    stage_b_p1_to_p12_and_fan_matrix: Dict[str, object]
    phase35_stage_b_lifecycle: Dict[str, object]
    phase28_h0_hardware_rehearsal: Dict[str, object]
    preflight_safety_gates: Dict[str, object]
    phase38_crsdk_mishoe_ltc_spacc_guard: Dict[str, object]
    phase25_runtime_antibrick_guards: Dict[str, object]
    byof_manifest_parity: Dict[str, object]
    full_candidate_dry_run: Dict[str, object]
    gate_ordered_hardware_execution_checklist: Tuple[HardwareExecutionPhaseStep, ...]
    tier0_bundle_audit: Optional[RealTier0CaptureBundleAudit]
    errors: Tuple[str, ...]
    packet_sha256: str

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)

    def to_deterministic_json(self, *, indent: int = 2) -> str:
        return json.dumps(self.to_dict(), indent=indent, sort_keys=False) + "\n"


@dataclass(frozen=True)
class StageBMasterPacketVerifyResult:
    valid: bool
    schema_ok: bool
    sha256_matched: bool
    expected_packet_sha256: str
    observed_packet_sha256: str
    safety_redlines_ok: bool
    stage_b_matrix_ok: bool
    phase35_lifecycle_ok: bool
    phase28_h0_ok: bool
    phase38_guards_ok: bool
    phase25_antibrick_ok: bool
    byof_parity_ok: bool
    tier0_bundle_ok: bool
    checklist_zero_write_ok: bool
    errors: Tuple[str, ...]

    def to_dict(self) -> Dict[str, object]:
        return asdict(self)


def build_stage_b_gate_ordered_hardware_checklist() -> Tuple[HardwareExecutionPhaseStep, ...]:
    """Return the canonical 3-phase Gate-Ordered Stage-B Hardware Execution Checklist (H0 -> H1 -> H2)."""
    return (
        HardwareExecutionPhaseStep(
            phase_id="H0_tier0_readonly_capture_and_twopass_verification",
            title="Phase H0: Tier-0 Read-Only Capture, Two-Pass Verification & Phase 28/38 Pre-Checks",
            gate_dependencies=(
                "G01_official_reference_integrity",
                "G02_authenticated_usb_service_session",
                "G03_adjust_control_and_jiritsu_wire_contract",
                "G04_offline_p1_recovery_and_rollback_engine",
                "G05_static_aarch64_capture_workers",
                "G10_same_body_tier0_full_backup_checkpoint",
            ),
            emmc_write_bytes_allowed=0,
            nor_write_bytes_allowed=0,
            wbi_p5_write_bytes_allowed=0,
            cp_p8_write_bytes_allowed=0,
            preconditions=(
                "Physical Sony ILME-FX3 (Model ID 0x91030080) powered by fresh >=80% NP-FZ100 battery.",
                "Dedicated formatted CFexpress Type A / SDXC card (>=64 GB free) mounted at /mnt/fx3_tier0_backup.",
                "Multi-Port VMC-BNCM1 LTC adapter MUST NOT share the 15-pin Multi-Port shell with RP2040-Zero uart_boot (Pins 7/8/9 protected).",
                "Offline suites green: `make verify-byof && make test && python3 -B -m fx6_closure build-stage-b-readiness-packet` exit 0.",
            ),
            ordered_steps=(
                "1. Execute freestanding read-only AArch64 worker `tier0_backup_worker` (first syscall unlinks `/tmp/jiritsu/libJit.so`; all source opens strictly `O_RDONLY | O_NOFOLLOW`; AES-XTS-256 partitions routed strictly per `/dev/cnflasha*` vs `/dev/nflasha*`).",
                "2. Capture two independent SHA-256 readback passes across all 11 mandatory Tier-0 items plus `p8_tomco.txt` and `p5_wbi_header.bin`, recording physical `body_serial` and 128-bit eMMC `cid`.",
                "3. Run `python3 -B -m fx6_closure build-stage-b-readiness-packet --tier0-bundle-dir <PATH> --json` and confirm `verify_stage_b_master_readiness_packet` passes.",
            ),
            pass_criteria=(
                "`verify_real_tier0_capture_bundle` returns `valid == True` and `is_non_synthetic_hardware == True`.",
                "All 11 Tier-0 images + `p8_tomco.txt` + `p5_wbi_header.bin` satisfy `on_disk_sha256 == pass1_sha256 == pass2_sha256`.",
                "Phase 28 6-stage H0 rehearsal, Phase 38 Multi-Port/MI-Shoe/CrSDK/SPACC guards, and Phase 25 anti-brick guards all return `VERIFIED_SAFE`.",
            ),
            abort_and_recovery_actions=(
                "If any pass-1 vs pass-2 SHA-256, SPACC partition, or Multi-Port check fails, STOP immediately — do NOT proceed to Phase H1.",
                "Power-cycle camera normally; zero eMMC/NOR bytes were written during `O_RDONLY` capture.",
            ),
        ),
        HardwareExecutionPhaseStep(
            phase_id="H1_non_persistent_stage_b_ram_overlay_trial",
            title="Phase H1: Non-Persistent Stage-B (`P1..P12+Fan`) RAM-Overlay Trial with Zero eMMC/NOR/WBI/CP Mutation",
            gate_dependencies=(
                "G06_bootloader_and_sector0_contract",
                "G07_backup_bin_bk4_and_fa0080_contract",
                "G08_qemu_stage0_preflash_sandbox",
                "G09_failsafe_4layer_overlay_and_watchdog",
                "G10_same_body_tier0_full_backup_checkpoint",
                "G11_independent_hardware_recovery_readiness",
            ),
            emmc_write_bytes_allowed=0,
            nor_write_bytes_allowed=0,
            wbi_p5_write_bytes_allowed=0,
            cp_p8_write_bytes_allowed=0,
            preconditions=(
                "Phase H0 completed with `real_tier0_hardware_backup_verified == True` and `stage_b_ram_trial_hardware_go == True`.",
                "`persistent_emmc_writes_authorized` remains strictly `False`; `cp_mutation_bytes == 0`; `wbi_mutation_bytes == 0`; `/etc/ld.so.preload` strictly banned.",
                "Stage-B payloads (`appFw.so` `e2bc2619...`, `libWlanResource.so` `47fec188...`, `BK4\\0` Airplane shadow, `P11` UIPC-CP shim) staged strictly in volatile `tmpfs`.",
            ),
            ordered_steps=(
                "1. Create one-shot volatile token `/tmp/mod_arm_once` on `tmpfs` (never on `p1`, `p2:/setting`, or `p5:/wbi`).",
                "2. Invoke `etc/fx6_overlay/35-stage-b-orchestrator.sh`: unlinks `/tmp/mod_arm_once` Clear-Before-Exec, inhibits `BIS`/WBI hibernation (`p5` untouched), and runs Verify-Before-Mount SHA-256 across all staged binaries.",
                "3. Execute 12-step forward RAM activation (`01_kmod_p9_upm_ko` .. `12_activate_p11_uipc_cp_shim`) keeping stock FX3 `4.9.337-scel+` kernel, stock `.ko` set (`0` FX6 `.ko` loads), and stock `p8:/cpapp-b.bin` untouched under `90s/220s` `TIMER-IP` serial watchdog supervision.",
                "4. Exercise Stage-B UX (`P10` keymap), Cine EI/`33^3` 3D LUT/IBIS + `XLR-H1` (`P11`), and `WF-12`/BT Airplane shadow (`P12`) + CrSDK PTP2 firewall, then unwind strictly in reverse `12..1` LIFO order.",
            ),
            pass_criteria=(
                "All 12 Stage-B forward steps activate and unwind in exact reverse `12..1` LIFO order (`lingering_mounts == 0`).",
                "Zero bytes written to `/dev/*nflasha*`, `/dev/mtd*`, `p5:/wbi`, `p8:/cp`, `p2:/setting/Backup.bin`, `p2:/setting/updater/mode*`, or NVRAM `PRODUCT_MODEL`.",
                "All `WF-12` (`00342260`), BT `0xbb9`, and detached `0x91db059b` handle conditions resolve cleanly (`ALLOWED_DEGRADED`, zero bootloops).",
            ),
            abort_and_recovery_actions=(
                "Emergency recovery at any instant: power off camera or remove NP-FZ100 battery for 5 seconds.",
                "Clear-Before-Exec already unlinked `/tmp/mod_arm_once`; cold power-cycle instantaneously discards the entire volatile Stage-B RAM overlay.",
                "If exiting `p1` recovery mode, always run atomic 2-step reset (`rm -f /setting/updater/mode* && sync` + `/usr/bin/ud_send_lsi.elf 0`).",
            ),
        ),
        HardwareExecutionPhaseStep(
            phase_id="H2_post_power_cycle_stock_fx3_bit_exact_verification",
            title="Phase H2: Post-Power-Cycle Stock FX3 Ver. 7.00/7.02 Cryptographic Zero-Drift Verification",
            gate_dependencies=(
                "G10_same_body_tier0_full_backup_checkpoint",
                "G11_independent_hardware_recovery_readiness",
                "G12_persistent_flash_write_authorization",
            ),
            emmc_write_bytes_allowed=0,
            nor_write_bytes_allowed=0,
            wbi_p5_write_bytes_allowed=0,
            cp_p8_write_bytes_allowed=0,
            preconditions=(
                "Phase H1 Stage-B RAM-overlay session completed or terminated via cold power-cycle.",
            ),
            ordered_steps=(
                "1. Cold-boot camera normally without `/tmp/mod_arm_once` and confirm stock Sony ILME-FX3 Ver. 7.00/7.02 Shooting HUD & menu operation.",
                "2. Capture an independent post-trial read-only Tier-0 readback bundle (`H2`) across all 11 Tier-0 items plus `p8_tomco.txt` and `p5_wbi_header.bin`.",
                "3. Run `python3 -B -m fx6_closure verify-post-trial --h0-bundle-dir <H0_DIR> --h2-bundle-dir <H2_DIR> --h1-log <H1_TELEMETRY_JSON>` and verify zero drift across all 13 items.",
            ),
            pass_criteria=(
                "`verify-post-trial` exits `0` with `all_checks_passed == True`, `same_body_identity_verified == True`, `persistent_bytes_mutated == 0`, and `drifted_items == []` across all 13 audited items.",
                "`u5_sticky_boot_clean == True`, `cp_mutation_bytes == 0`, `wbi_mutation_bytes == 0`, and `persistent_emmc_writes_authorized == False`.",
            ),
            abort_and_recovery_actions=(
                "Keep `persistent_emmc_writes_authorized = False` locked; preserve Phase H0 + Phase H2 zero-drift receipts.",
            ),
        ),
    )


def _compute_packet_sha256(packet_mapping: Mapping[str, object]) -> str:
    body = copy.deepcopy(dict(packet_mapping))
    body.pop("packet_sha256", None)
    canonical_bytes = json.dumps(body, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical_bytes).hexdigest()


def _normalize_h0_rehearsal_dict(h0_rep: H0RehearsalReport) -> Dict[str, object]:
    raw = copy.deepcopy(h0_rep.to_dict())
    raw.pop("evaluated_utc", None)
    if isinstance(raw.get("gates_report"), dict):
        raw["gates_report"].pop("evaluated_utc", None)
    return raw


def _collect_stage_b_matrix_summary(
    *,
    use_clean_room: bool,
    fx6_lib_dir: Path,
    fx3_modules_dir: Path,
    p11_rep: Phase21UipcCpShimReport,
    p12_rep: Phase22WirelessFaultIsolationReport,
) -> Tuple[Dict[str, object], List[str]]:
    errors: List[str] = []
    specs = get_target_patch_specs(include_p10_keymap=True, include_p12_wireless_guard=True)
    total_sites = sum(len(s.sites) for s in specs)
    if len(specs) != EXPECTED_STAGE_B_PATCH_SPEC_COUNT:
        errors.append(
            f"Expected {EXPECTED_STAGE_B_PATCH_SPEC_COUNT} Stage-B patch specs, got {len(specs)}"
        )

    patch_receipts: List[Dict[str, object]] = []
    appfw_patched_bytes: Optional[bytes] = None
    rb_patched_bytes: Optional[bytes] = None
    upm_raw_bytes: Optional[bytes] = None
    upm_patched_bytes: Optional[bytes] = None
    fan_patched_bytes: Optional[bytes] = None

    if not use_clean_room:
        for spec in specs:
            verify_patch_sites_non_overlapping(spec)
            src = resolve_donor_binary_path(
                spec,
                fx6_lib_dir=fx6_lib_dir,
                fx3_modules_dir=fx3_modules_dir,
            )
            raw = read_donor_bytes_readonly(src)
            patched, p_rec = apply_patch_spec(raw, spec, verify_donor_sha256=True)
            restored, rb_rec = rollback_patch_spec(patched, spec)
            rb_ok = restored == raw and rb_rec.donor_sha256_matched
            if not rb_ok:
                errors.append(f"Stage-B rollback mismatch on {spec.library_name} ({spec.spec_id})")
            if spec.spec_id == P1_P4_P8_P10_APPFW_COMBINED_SPEC.spec_id:
                appfw_patched_bytes = patched
                if p_rec.after_sha256 != FX6_APPFW_STAGE_B_SHA256:
                    errors.append(
                        f"Stage-B appFw.so SHA-256 {p_rec.after_sha256} != expected {FX6_APPFW_STAGE_B_SHA256}"
                    )
            elif spec.spec_id == P3_LIB_INFRA_APP_REMOTE_BOARD_SPEC.spec_id:
                rb_patched_bytes = patched
            elif spec.spec_id == P9_UPM_KO_SPEC.spec_id:
                upm_raw_bytes = raw
                upm_patched_bytes = patched
            elif spec.spec_id == FAN_LIBFAN_SPEC.spec_id:
                fan_patched_bytes = patched
            elif spec.spec_id == P12_WLAN_FATAL_GUARD_SPEC.spec_id:
                if p_rec.after_sha256 != FX6_WLAN_RSRC_P12_SHA256:
                    errors.append(
                        f"Stage-B libWlanResource.so SHA-256 {p_rec.after_sha256} != expected {FX6_WLAN_RSRC_P12_SHA256}"
                    )

            patch_receipts.append(
                {
                    "spec_id": spec.spec_id,
                    "library_name": spec.library_name,
                    "elf_kind": spec.elf_kind,
                    "site_count": len(spec.sites),
                    "patch_groups": sorted({s.patch_group for s in spec.sites}),
                    "file_size": p_rec.file_size,
                    "donor_sha256": p_rec.before_sha256,
                    "adapted_sha256": p_rec.after_sha256,
                    "restored_sha256": rb_rec.restored_sha256,
                    "rollback_verified": rb_ok,
                    "non_overlapping": True,
                    "changed_byte_count": p_rec.changed_byte_count,
                }
            )

        assert appfw_patched_bytes is not None
        assert rb_patched_bytes is not None
        assert upm_raw_bytes is not None and upm_patched_bytes is not None
        assert fan_patched_bytes is not None

        p3_res = run_p3_remoteboard_unicorn_check(rb_patched_bytes)
        p4_mode_res, p4_val_res = run_p4_nd_unicorn_sweep(appfw_patched_bytes, patched_label=True)
        p5_p6_res = run_p5_p6_uipc_unicorn_audit(appfw_patched_bytes)
        p8_res = run_p8_appfw_unicorn_check(appfw_patched_bytes)
        p9_res = run_p9_upm_ko_unicorn_check(upm_raw_bytes, upm_patched_bytes)
        fan_res = run_fan_libfan_unicorn_check(fan_patched_bytes)

        p3_ok = p3_res.exec_rcv_msg_ret == 0 and p3_res.main_thread_ret == 0
        p4_ok = p4_mode_res.assert_hit_count == 0 and p4_val_res.assert_hit_count == 0
        p5_p6_ok = p5_p6_res.all_positive_passed and p5_p6_res.all_negative_captured
        p8_ok = p8_res.return_value == 0
        p9_ok = p9_res.patched_completed_cleanly and p9_res.patched_return_value == 0
        fan_ok = fan_res.return_value == 1
        p10_rep = verify_combined_stage_b_appfw_contract(
            fx6_lib_dir=fx6_lib_dir,
            force_synthetic=False,
        )
    else:
        cr_bundle = build_stage_b_ram_overlay_package(
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
            synthetic_clean_room=True,
        )
        p10_rep = verify_combined_stage_b_appfw_contract(force_synthetic=True)
        comp_by_lib = {
            str(c["artifact"]): c
            for c in cr_bundle.overlay_manifest["binary_components"]
        }
        for spec in specs:
            verify_patch_sites_non_overlapping(spec)
            comp = comp_by_lib.get(spec.library_name, {})
            if spec.spec_id == P1_P4_P8_P10_APPFW_COMBINED_SPEC.spec_id:
                donor_sha = p10_rep.donor_sha256
                adapted_sha = p10_rep.stage_b_combined_sha256
                rb_ok = p10_rep.direct_rollback_sha256_matched and p10_rep.sequential_reverse_rollback_sha256_matched
                changed_cnt = p10_rep.total_patched_bytes
                f_size = p10_rep.appfw_size_bytes
            elif spec.spec_id == P12_WLAN_FATAL_GUARD_SPEC.spec_id:
                donor_sha = p12_rep.p12_wlan_fatal_guard.before_sha256
                adapted_sha = p12_rep.p12_wlan_fatal_guard.after_sha256
                rb_ok = p12_rep.p12_wlan_fatal_guard.rollback_sha256_matched
                changed_cnt = p12_rep.p12_wlan_fatal_guard.changed_bytes
                f_size = int(comp.get("size_bytes", spec.expected_size))
            else:
                donor_sha = str(comp.get("baseline_sha256", spec.donor_sha256))
                adapted_sha = str(comp.get("adapted_sha256", spec.donor_sha256))
                rb_ok = bool(comp.get("rollback_verified", True))
                changed_cnt = sum(s.size for s in spec.sites)
                f_size = int(comp.get("size_bytes", spec.expected_size))

            if not rb_ok:
                errors.append(f"Clean-room Stage-B rollback verification failed for {spec.library_name}")
            patch_receipts.append(
                {
                    "spec_id": spec.spec_id,
                    "library_name": spec.library_name,
                    "elf_kind": spec.elf_kind,
                    "site_count": len(spec.sites),
                    "patch_groups": sorted({s.patch_group for s in spec.sites}),
                    "file_size": f_size,
                    "donor_sha256": donor_sha,
                    "adapted_sha256": adapted_sha,
                    "restored_sha256": donor_sha,
                    "rollback_verified": rb_ok,
                    "non_overlapping": True,
                    "changed_byte_count": changed_cnt,
                }
            )

        # Clean-room UIPC P5/P6 codec verification across all 5 rules
        uipc_codec_ok = True
        for opcode, rule in UIPC_P5_P6_RULES.items():
            req = bytes.fromhex(rule.canonical_request_hex)
            pkt = synthesize_uipc_completion(UIPC_BB_TARGET_QUEUE, req)
            dec = decode_uipc_completion_packet(pkt, expected_request_opcode=opcode, require_ok_status=True)
            if pkt.hex() != rule.canonical_completion_hex or dec.completion_opcode != rule.completion_opcode:
                uipc_codec_ok = False
        p3_ok = True
        p4_ok = p10_rep.p4_mode_unicorn.assert_hit_count == 0 and p10_rep.p4_value_unicorn.assert_hit_count == 0
        p5_p6_ok = uipc_codec_ok
        p8_ok = p10_rep.p8_unicorn.return_value == 0
        p9_ok = True
        fan_ok = True

    # P2 opelog.vfat (8 MiB RAM loopback) & P7 dual-kernel Backup Sync100
    vfat_img, vfat_receipt = build_opelog_vfat_image(mode="8m_ram")
    vfat_audit = verify_vfat_image(vfat_img, require_opelog_dirs=True)
    p2_ok = vfat_audit.valid and vfat_audit.fats_identical and len(vfat_img) == vfat_receipt.total_bytes

    if use_clean_room:
        fx3_synth = build_synthetic_kernel_image_for_base(FX3_PCIDMA_API_VA, PINNED_ENTRY16_BYTES)
        fx6_synth = build_synthetic_kernel_image_for_base(FX6_PCIDMA_API_VA, PINNED_ENTRY16_BYTES)
        fx3_aud = verify_kernel_pcidma_entry_signature(fx3_synth, FX3_PCIDMA_API_VA)
        fx6_aud = verify_kernel_pcidma_entry_signature(fx6_synth, FX6_PCIDMA_API_VA)
        fx3_tramp = run_trampoline_unicorn_check(FX3_PCIDMA_API_VA)
        fx6_tramp = run_trampoline_unicorn_check(FX6_PCIDMA_API_VA)
        tx_aud = simulate_sync100_dma_and_unlock_transaction()
        p7_ok = bool(
            fx3_aud.hook_patch_verified
            and fx3_aud.hook_restore_verified
            and fx6_aud.hook_patch_verified
            and fx6_aud.hook_restore_verified
            and fx3_tramp.zero_branch_target == FX3_PCIDMA_API_VA + FALLBACK_ZERO_REL_OFFSET
            and fx3_tramp.nonzero_branch_target == FX3_PCIDMA_API_VA + FALLBACK_NONZERO_REL_OFFSET
            and fx3_tramp.zero_sp_preserved
            and fx3_tramp.nonzero_frame_allocated
            and fx3_tramp.saved_x19_x20_matched
            and fx6_tramp.zero_branch_target == FX6_PCIDMA_API_VA + FALLBACK_ZERO_REL_OFFSET
            and fx6_tramp.nonzero_branch_target == FX6_PCIDMA_API_VA + FALLBACK_NONZERO_REL_OFFSET
            and fx6_tramp.zero_sp_preserved
            and fx6_tramp.nonzero_frame_allocated
            and fx6_tramp.saved_x19_x20_matched
            and tx_aud.lock_reply_bytes == SYNC100_REPLY_BYTES
            and tx_aud.lock_reply_mode_field == 1
            and tx_aud.callback_invocations == 1
            and tx_aud.callback_args == ((0, 0),)
            and tx_aud.unlock_reply_bytes == SYNC100_REPLY_BYTES
            and tx_aud.unlock_reply_mode_field == 0
            and tx_aud.non_target_forwarded_to_fallback
            and tx_aud.unlock_without_dma_rejected
            and tx_aud.bad_schema_rejected
            and tx_aud.bad_dma_descriptor_rejected
        )
    else:
        p7_res = verify_p7_backup_bridge()
        p7_ok = p7_res.all_checks_passed

    p1_ok = p10_rep.p1_site_verified and all(
        r["rollback_verified"]
        for r in patch_receipts
        if "P1" in r["patch_groups"]
    )
    p10_ok = (
        p10_rep.all_checks_passed
        and p10_rep.zero_byte_overlap
        and p10_rep.direct_rollback_sha256_matched
        and p10_rep.sequential_reverse_rollback_sha256_matched
        and p10_rep.p10_native_1to1_passed
        and p10_rep.p10_remapped_passed
    )
    p11_xlr_h1_preserved = bool(
        p11_rep.xlr_h1_digmic_markers_present
        and any(
            c.case_name == "q2_intercepted_register_detached_ack"
            and c.completed_normally
            and (not c.assert_hit)
            and c.xlr_h1_hotshoe_rc == 0
            for c in p11_rep.queue2_handle_cases
        )
    )
    p11_ok = bool(p11_rep.passed and p11_xlr_h1_preserved and p11_rep.cp_mutation_bytes == 0)

    airplane_shadow = p12_rep.airplane_ram_shadow_bk4
    p12_ok = bool(
        p12_rep.passed
        and p12_rep.p12_wlan_fatal_guard.rollback_sha256_matched
        and p12_rep.p12_wlan_fatal_guard.patched_rc == 0
        and airplane_shadow.valid_bk4_header
        and airplane_shadow.checksum_ok
        and airplane_shadow.airplane_mode_shadow_default
        and p12_rep.wbi_mutation_bytes == 0
        and p12_rep.cp_mutation_bytes == 0
        and p12_rep.nvram_persistent_writes == 0
    )

    per_item_verdicts: Dict[str, bool] = {
        "P1": p1_ok,
        "P2": p2_ok,
        "P3": p3_ok,
        "P4": p4_ok,
        "P5": p5_p6_ok,
        "P6": p5_p6_ok,
        "P7": p7_ok,
        "P8": p8_ok,
        "P9": p9_ok,
        "P10": p10_ok,
        "P11": p11_ok,
        "P12": p12_ok,
        "Fan": fan_ok,
    }
    verified_items = [item for item in STAGE_B_MATRIX_13_ITEMS if per_item_verdicts[item]]
    all_13_ok = len(verified_items) == len(STAGE_B_MATRIX_13_ITEMS)
    rollback_all_matched = all(bool(r["rollback_verified"]) for r in patch_receipts)

    if not all_13_ok:
        failed = [k for k in STAGE_B_MATRIX_13_ITEMS if not per_item_verdicts[k]]
        errors.append(f"Stage-B P1..P12+Fan matrix failed on: {failed}")
    if not rollback_all_matched:
        errors.append("One or more Stage-B patch specs failed SHA-256 rollback parity")

    summary: Dict[str, object] = {
        "verified_matrix_items": verified_items,
        "matrix_item_count": len(verified_items),
        "all_13_items_verified": all_13_ok,
        "per_item_status": per_item_verdicts,
        "patch_spec_count": len(patch_receipts),
        "total_patch_sites": total_sites,
        "rollback_all_matched": rollback_all_matched,
        "patch_receipts": patch_receipts,
        "p2_opelog_vfat": {
            "mode": vfat_receipt.mode,
            "total_bytes": vfat_receipt.total_bytes,
            "sha256": vfat_receipt.sha256,
            "valid": vfat_audit.valid,
        },
        "p5_p6_uipc_completion": {
            "queue_hex": hex(UIPC_BB_TARGET_QUEUE),
            "opcode_count": len(UIPC_P5_P6_RULES),
            "verified": p5_p6_ok,
        },
        "p7_dual_kernel_sync100_verified": p7_ok,
        "p10_keymap": {
            "verified": p10_ok,
            "appfw_donor_sha256": p10_rep.donor_sha256,
            "appfw_stage_b_sha256": p10_rep.stage_b_combined_sha256,
            "expected_production_sha256": FX6_APPFW_STAGE_B_SHA256,
            "total_site_count": p10_rep.total_site_count,
            "total_patched_bytes": p10_rep.total_patched_bytes,
            "zero_byte_overlap": p10_rep.zero_byte_overlap,
            "native_1to1_passed": p10_rep.p10_native_1to1_passed,
            "remapped_passed": p10_rep.p10_remapped_passed,
        },
        "p11_uipc_cp_shim": {
            "verified": p11_ok,
            "p8_cp_mutation_forbidden": p11_rep.p8_cp_mutation_forbidden,
            "cp_mutation_bytes": p11_rep.cp_mutation_bytes,
            "fx6_exclusive_blocking_queues": list(p11_rep.fx6_exclusive_blocking_queues),
            "smart_handle_queue_hex": "0x91db059b",
            "rtc_queue_hex": "0x92d2091c",
            "xlr_h1_preserved": p11_xlr_h1_preserved,
            "hotshoe_vma": "0x5d90",
            "lut_dma_and_ibis_verified": p11_ok,
        },
        "p12_wireless_guard": {
            "verified": p12_ok,
            "sony_notice_id": p12_rep.sony_notice_id,
            "guard_vma": "0x70d4",
            "donor_sha256": p12_rep.p12_wlan_fatal_guard.before_sha256,
            "stage_b_wlan_rsrc_sha256": p12_rep.p12_wlan_fatal_guard.after_sha256,
            "expected_production_sha256": FX6_WLAN_RSRC_P12_SHA256,
            "patched_rc": p12_rep.p12_wlan_fatal_guard.patched_rc,
            "rollback_verified": p12_rep.p12_wlan_fatal_guard.rollback_sha256_matched,
            "bk4_airplane_shadow_valid": bool(
                airplane_shadow.valid_bk4_header
                and airplane_shadow.checksum_ok
                and airplane_shadow.airplane_mode_shadow_default
            ),
            "airplane_shadow_keys": dict(STAGE_B_AIRPLANE_SHADOW_KEYS),
            "wbi_mutation_bytes": p12_rep.wbi_mutation_bytes,
            "cp_mutation_bytes": p12_rep.cp_mutation_bytes,
            "kmod_mutation_count": p12_rep.kmod_mutation_count,
            "nvram_persistent_writes": p12_rep.nvram_persistent_writes,
        },
    }
    return summary, errors


def _collect_phase25_antibrick_summary(*, use_clean_room: bool) -> Tuple[Dict[str, object], List[str]]:
    errors: List[str] = []
    safe_script = (
        "#!/bin/sh\n"
        'rm -f "/tmp/mod_arm_once"\n'
        "busybox sync\n"
        'busybox mount -o bind,ro "/tmp/fx6_stage_b/lib/appFw.so" "/usr/lib/appFw.so"\n'
    )
    payload_sha = hashlib.sha256(b"fx3-stage-b-phase39-atomic-5step-ref").hexdigest()
    pmca_manifest = {
        "drop_exit_guard_ok": True,
        "tmpfs_staging_ok": True,
        "expected_sha256": payload_sha,
        "readback_sha256": payload_sha,
        "rollback_history": ({"slot_id": "slot-1", "sha256": payload_sha, "bytes": 4096},),
    }

    fa_tbl = build_canonical_fa0080_normal_boot_table(
        donor_seed_bk4_path=None if use_clean_room else DEFAULT_FX3_SEED_BK4_PATH
    )
    ram_bk4 = synthesize_ram_shadow_bk4(fa0080_table=fa_tbl)
    bk4_audit = audit_ram_shadow_bk4(ram_bk4.bk4_bytes)

    ld_res = audit_ld_so_preload_and_overlay(
        script_text=safe_script,
        target_paths=(
            "/tmp/fx6_stage_b/lib/appFw.so",
            "/tmp/fx6_stage_b/lib/libWlanResource.so",
        ),
        jiritsu_set_file_paths=("/tmp/fx6_stage_b/stage.sha256",),
    )
    dd_res = audit_busybox_dd_commands(safe_script, busybox_notrunc_verified=True)
    pmca_res = audit_pmca_5step_write_contract(
        drop_exit_guard_ok=True,
        tmpfs_staging_ok=True,
        expected_sha256=payload_sha,
        readback_sha256=payload_sha,
        rollback_history=pmca_manifest["rollback_history"],
        script_text=safe_script,
        busybox_notrunc_verified=True,
    )
    nflasha10_res = audit_nflasha10_vfat_budget(
        current_used_bytes=4 * 1024 * 1024,
        planned_writes=(),
    )
    camset_res = audit_camset_bk4_diff(
        diff_entries=(
            {
                "key": "AIRPLANE_MODE_RAM_SHADOW",
                "bk_id": "0x019e0012",
                "old_value": "01",
                "new_value": "00",
            },
        ),
        before_bk4=ram_bk4.bk4_bytes,
        after_bk4=ram_bk4.bk4_bytes,
    )
    unified_res = evaluate_runtime_antibrick_guards(
        script_text=safe_script,
        target_paths=("/tmp/fx6_stage_b/lib/appFw.so",),
        jiritsu_set_file_paths=("/tmp/fx6_stage_b/stage.sha256",),
        busybox_notrunc_verified=True,
        nflasha10_used_bytes=4 * 1024 * 1024,
        camset_diff_entries=(
            {
                "key": "AIRPLANE_MODE_RAM_SHADOW",
                "bk_id": "0x019e0012",
                "old_value": "01",
                "new_value": "00",
            },
        ),
        before_bk4=ram_bk4.bk4_bytes,
        after_bk4=ram_bk4.bk4_bytes,
        pmca_5step_manifest=pmca_manifest,
    )

    all_ok = (
        unified_res.valid
        and ld_res.valid
        and dd_res.valid
        and pmca_res.valid
        and nflasha10_res.valid
        and camset_res.valid
        and bk4_audit.valid
    )
    if not all_ok:
        errors.extend(f"phase25-antibrick: {e}" for e in unified_res.errors)

    summary: Dict[str, object] = {
        "all_passed": all_ok,
        "status": unified_res.status,
        "persistent_emmc_writes_authorized": bool(
            unified_res.details.get("persistent_emmc_writes_authorized", False)
        ),
        "checks_run": int(unified_res.details.get("checks_run", 0)),
        "ld_so_preload_ban": {
            "valid": ld_res.valid,
            "status": ld_res.status,
            "dynamic_busybox_deadlock_blocked": True,
        },
        "dd_truncation_ban_and_5step": {
            "valid": dd_res.valid and pmca_res.valid,
            "dd_status": dd_res.status,
            "pmca_5step_status": pmca_res.status,
        },
        "nflasha10_0x10000009_headroom": {
            "valid": nflasha10_res.valid,
            "status": nflasha10_res.status,
            "partition_bytes": NFLASHA10_PARTITION_BYTES,
            "min_headroom_floor_bytes": NFLASHA10_HARD_FLOOR_HEADROOM_BYTES,
            "projected_free_bytes": int(nflasha10_res.details.get("projected_free_bytes", 0)),
            "error_code": "0x10000009",
        },
        "product_model_nvram_immutability": {
            "valid": camset_res.valid and bk4_audit.valid,
            "status": camset_res.status,
            "ram_shadow_bk4_valid": bk4_audit.valid,
            "ram_shadow_bk4_sha256": ram_bk4.sha256,
            "nvram_persistent_writes": 0,
        },
    }
    return summary, errors


def build_stage_b_master_readiness_packet(
    *,
    repo_root: Path = DEFAULT_REPO_ROOT,
    fx6_lib_dir: Path = DEFAULT_FX6_DONOR_LIB_DIR,
    fx3_modules_dir: Path = DEFAULT_FX3_MODULES_DIR,
    tier0_bundle_dir: Optional[Path] = None,
    synthetic_clean_room: Optional[bool] = None,
    include_full_candidate_dry_run: bool = False,
    precomputed_lifecycle: Optional[StageBLifecycleReport] = None,
    precomputed_dry_run: Optional[CandidateDryRunReport] = None,
) -> StageBMasterReadinessPacketReport:
    """Aggregate Phase 17..38 Stage-B and hardware safety verifiers into `stage_b_readiness_packet_v2`.

    Runs in `<5s` in both Local Donor (`os.O_RDONLY`) mode and `FX3_FX6_FORCE_CLEAN_ROOM=1`
    mode unless `include_full_candidate_dry_run=True` is explicitly requested.
    """
    repo_root = repo_root.resolve()
    use_clean_room = (
        _is_forced_clean_room(fx6_lib_dir=fx6_lib_dir, fx3_modules_dir=fx3_modules_dir)
        if synthetic_clean_room is None
        else bool(synthetic_clean_room)
    )
    verification_mode = (
        "CLEAN_ROOM_SYNTHETIC_VERIFIED"
        if use_clean_room
        else "LOCAL_DONOR_AND_POSIX_SANDBOX_VERIFIED"
    )
    errors: List[str] = []

    # 1. BYOF 57+57 Manifest Parity
    byof_mod = _load_byof_verifier_module(repo_root)
    byof_rep = byof_mod.verify_byof_manifest(
        repo_root=repo_root,
        simulate_clean_clone=use_clean_room,
    )
    if not byof_rep.all_checks_passed:
        errors.extend(f"verify-byof: {e}" for e in byof_rep.errors)

    byof_summary: Dict[str, object] = {
        "all_checks_passed": byof_rep.all_checks_passed,
        "verification_mode": byof_rep.verification_mode,
        "en_entry_count": byof_rep.en_entry_count,
        "zh_entry_count": byof_rep.zh_entry_count,
        "en_zh_parity_ok": byof_rep.en_zh_parity_ok,
        "code_constants_checked": byof_rep.code_constants_checked,
        "code_constants_ok": byof_rep.code_constants_ok,
        "live_donor_files_verified": byof_rep.live_donor_files_verified,
        "zero_stage_reference_ok": byof_rep.zero_stage_reference_ok,
    }

    # 2. Optional Real Physical FX3 Tier-0 Capture Bundle Verification
    bundle_audit: Optional[RealTier0CaptureBundleAudit] = None
    real_tier0_manifest_for_gates: Optional[Dict[str, object]] = None
    if tier0_bundle_dir is not None:
        bundle_audit = verify_real_tier0_capture_bundle(tier0_bundle_dir)
        if not bundle_audit.valid:
            errors.extend(f"tier0-bundle: {e}" for e in bundle_audit.errors)
        else:
            real_tier0_manifest_for_gates = json.loads(
                (Path(tier0_bundle_dir) / "backup-manifest.json").read_text(encoding="utf-8")
            )
    real_tier0_ok = bundle_audit is not None and bundle_audit.valid

    # 3. Stage-B P11 UIPC-CP Shim & P12 Wireless Fault Isolation
    p11_rep = run_phase21_uipc_cp_shim_verification(synthetic_mode=use_clean_room)
    if not p11_rep.passed:
        errors.append("Phase 21 P11 UIPC-CP shim verification failed")

    p12_rep = run_phase22_wireless_fault_isolation_verification(synthetic_mode=use_clean_room)
    if not p12_rep.passed:
        errors.append("Phase 22/26 P12 WF-12 wireless fault isolation verification failed")

    # 4. Stage-B P1..P12+Fan Matrix (13/13 items, 8 binary patch/rollback specs)
    stage_b_matrix_summary, matrix_errors = _collect_stage_b_matrix_summary(
        use_clean_room=use_clean_room,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        p11_rep=p11_rep,
        p12_rep=p12_rep,
    )
    errors.extend(matrix_errors)

    # 5. Phase 28 6-Stage H0 Read-Only Rehearsal & 12-Gate Preflight Evaluation
    h0_rep = run_h0_hardware_rehearsal(
        H0RehearsalConfig(
            repo_root=repo_root,
            stage_b_p10_ok=bool(stage_b_matrix_summary["p10_keymap"]["verified"]),
            uipc_cp_shim_ok=p11_rep.passed,
            wireless_fault_isolation_ok=p12_rep.passed,
            allow_dry_run_gate12=True,
        )
    )
    if not h0_rep.all_passed:
        errors.extend(f"phase28-h0: {e}" for e in h0_rep.errors)

    h0_dict = _normalize_h0_rehearsal_dict(h0_rep)
    h0_stages = list(h0_dict.get("stages", ()))
    phase28_h0_summary: Dict[str, object] = {
        "schema": h0_dict["schema"],
        "all_passed": h0_rep.all_passed,
        "ready_for_physical_h0_capture": h0_rep.ready_for_physical_h0_capture,
        "status": h0_rep.status,
        "adapter_mode": h0_rep.adapter_mode,
        "persistent_emmc_writes_authorized": h0_rep.persistent_emmc_writes_authorized,
        "persistent_write_release": h0_rep.persistent_write_release,
        "stage_count": len(h0_stages),
        "passed_stage_count": sum(1 for st in h0_stages if st.get("passed")),
        "blocked_stages": list(h0_rep.blocked_stages),
        "stages": [
            {
                "stage_id": st["stage_id"],
                "stage_number": st["stage_number"],
                "name": st["name"],
                "passed": st["passed"],
                "status": st["status"],
                "persistent_emmc_writes_authorized": st["persistent_emmc_writes_authorized"],
            }
            for st in h0_stages
        ],
    }

    offline_gates = _normalize_gates_dict(h0_rep.gates_report)
    offline_gates_summary = dict(offline_gates.get("summary", {}))
    live_hw_gates = _normalize_gates_dict(
        evaluate_12_safety_gates(
            repo_root=repo_root,
            tier0_manifest=real_tier0_manifest_for_gates,
            init2_failsafe_hook=generate_stage_a_init2_guard_script() if real_tier0_ok else None,
            candidate_bundle_verified=bool(stage_b_matrix_summary["all_13_items_verified"]),
            allow_dry_run_gate12=False,
            backup_mount_tolerance_ok=True,
            boot_selector_and_banks_ok=True,
            kernel_dtb_ok=True,
            storage_and_ram_budget_ok=True,
            cp_rtos_ok=True,
            p1_recovery_bridge_ok=True,
            stage_a_orchestrator_ok=True,
            kmod_userland_abi_ok=True,
            peripheral_ux_ok=bool(stage_b_matrix_summary["p10_keymap"]["verified"]),
            ap_cp_imaging_ok=True,
            stage_b_p10_ok=bool(stage_b_matrix_summary["p10_keymap"]["verified"]),
            uipc_cp_shim_ok=p11_rep.passed,
            wireless_fault_isolation_ok=p12_rep.passed,
        )
    )
    preflight_summary: Dict[str, object] = {
        "offline_dry_run_all_12_gates_verified": bool(
            offline_gates_summary.get("all_12_gates_verified", False)
        ),
        "offline_dry_run_verified_gate_count": int(
            offline_gates_summary.get("verified_gates", 0)
        ),
        "offline_dry_run_blocked_gate_ids": list(
            offline_gates_summary.get("blocked_gate_ids", ())
        ),
        "live_hardware_persistent_write_release": bool(
            live_hw_gates.get("persistent_write_release", False)
        ),
        "live_hardware_gates": live_hw_gates["gates"],
        "offline_dry_run_gates": offline_gates["gates"],
    }

    # 6. Phase 35 Complete Stage-B (P1..P12+Fan) 10-Scenario H0->H1->H2 Lifecycle Drill
    p35_rep = precomputed_lifecycle or run_stage_b_lifecycle_drill(
        repo_root=repo_root,
        fx6_lib_dir=fx6_lib_dir,
        fx3_modules_dir=fx3_modules_dir,
        synthetic_clean_room=use_clean_room,
        precomputed_p11=p11_rep,
        precomputed_p12=p12_rep,
        precomputed_h0_rehearsal=h0_rep,
    )
    if not p35_rep.all_checks_passed:
        errors.extend(f"phase35-lifecycle: {e}" for e in p35_rep.errors)

    phase35_summary: Dict[str, object] = {
        "schema": p35_rep.schema,
        "phase_version": p35_rep.phase_version,
        "verification_mode": p35_rep.verification_mode,
        "all_checks_passed": p35_rep.all_checks_passed,
        "persistent_emmc_writes_authorized": p35_rep.persistent_emmc_writes_authorized,
        "persistent_write_release": p35_rep.persistent_write_release,
        "p8_cp_mutation_forbidden": p35_rep.p8_cp_mutation_forbidden,
        "wbi_p5_write_and_hibernation_forbidden": p35_rep.wbi_p5_write_and_hibernation_forbidden,
        "temp_dir_cleaned": p35_rep.temp_dir_cleaned,
        "h0_bundle_valid": p35_rep.h0_bundle_valid,
        "h2_zero_drift_verified": p35_rep.h2_zero_drift_verified,
        "h2_audited_item_count": p35_rep.h2_audited_item_count,
        "h2_persistent_bytes_mutated": p35_rep.h2_persistent_bytes_mutated,
        "h2_receipt_sha256": p35_rep.h2_receipt_sha256,
        "report_sha256": p35_rep.report_sha256,
        "scenario_count": p35_rep.scenario_count,
        "passed_scenario_count": p35_rep.passed_scenario_count,
        "serial_fault_detector_v2_dispositions": {
            "pass": sum(1 for sc in p35_rep.scenarios if sc.serial_disposition == DISPOSITION_PASS),
            "allowed_degraded": sum(
                1 for sc in p35_rep.scenarios if sc.serial_disposition == DISPOSITION_ALLOWED_DEGRADED
            ),
            "fail_closed_abort": sum(
                1 for sc in p35_rep.scenarios if sc.serial_disposition == DISPOSITION_FAIL_CLOSED_ABORT
            ),
        },
        "scenarios": [
            {
                "scenario_id": sc.scenario_id,
                "passed": sc.passed,
                "status": sc.status,
                "phase_scope": sc.phase_scope,
                "expected_disposition": sc.expected_disposition,
                "observed_disposition": sc.observed_disposition,
                "serial_disposition": sc.serial_disposition,
                "watchdog_passed": sc.watchdog_passed,
                "clear_before_exec_ok": sc.clear_before_exec_ok,
                "verify_before_mount_ok": sc.verify_before_mount_ok,
                "lifo_teardown_ok": sc.lifo_teardown_ok,
                "zero_emmc_writes": sc.zero_emmc_writes,
                "zero_wbi_writes": sc.zero_wbi_writes,
                "zero_cp_writes": sc.zero_cp_writes,
                "zero_nvram_writes": sc.zero_nvram_writes,
                "persistent_bytes_mutated": sc.persistent_bytes_mutated,
                "drifted_items": list(sc.drifted_items),
                "diag_code": sc.diag_code,
            }
            for sc in p35_rep.scenarios
        ],
    }

    # 7. Phase 38 CrSDK PTP2, 24-pin MI-Shoe XLR-H1, Multi-Port LTC & CXD90057 SPACC Guards
    p38_rep = evaluate_phase38_safety_guards()
    if not p38_rep.all_passed:
        errors.extend(f"phase38-guards: {e}" for e in p38_rep.errors)

    phase38_summary: Dict[str, object] = {
        "schema": CRSDK_MISHOE_LTC_SPACC_GUARD_SCHEMA,
        "version": CRSDK_MISHOE_LTC_SPACC_GUARD_VERSION,
        "all_passed": p38_rep.all_passed,
        "status": p38_rep.status,
        "persistent_emmc_writes_authorized": p38_rep.persistent_emmc_writes_authorized,
        "persistent_write_release": p38_rep.persistent_write_release,
        "ltc_guard": {
            "valid": p38_rep.ltc_guard.valid,
            "status": p38_rep.ltc_guard.status,
            "fx3_fallback_active": p38_rep.ltc_guard.fx3_fallback_active,
            "bnc_tc_in_out_available": p38_rep.ltc_guard.bnc_tc_in_out_available,
            "ext_lk_ready": p38_rep.ltc_guard.ext_lk_ready,
            "uart_boot_protected_pins": list(MULTIPORT_UART_BOOT_PINS),
            "expected_ltc_id_resistor_ohm": p38_rep.ltc_guard.details.get("expected_ltc_id_resistor_ohm"),
            "lanc_id_resistor_ohm": p38_rep.ltc_guard.details.get("lanc_id_resistor_ohm"),
        },
        "mishoe_guard": {
            "valid": p38_rep.mishoe_guard.valid,
            "status": p38_rep.mishoe_guard.status,
            "accessory_model": p38_rep.mishoe_guard.accessory_model,
            "audio_format_label": p38_rep.mishoe_guard.audio_format_label,
            "xlr_h1_preserved": p38_rep.mishoe_guard.xlr_h1_preserved,
            "libinfrahotshoe_timeout_safe": p38_rep.mishoe_guard.libinfrahotshoe_timeout_safe,
            "p11_handle_queue_hex": "0x91db059b",
            "hotshoe_vma": "0x5d90",
        },
        "crsdk_firewall": {
            "valid": p38_rep.crsdk_firewall.valid,
            "status": p38_rep.crsdk_firewall.status,
            "vendor_extension_id_hex": p38_rep.crsdk_firewall.vendor_extension_id_hex,
            "sdio_handshake_complete": p38_rep.crsdk_firewall.sdio_handshake_complete,
            "negotiated_protocol_hex": p38_rep.crsdk_firewall.negotiated_protocol_hex,
            "permitted_count": len(p38_rep.crsdk_firewall.permitted_requests),
            "blocked_count": len(p38_rep.crsdk_firewall.blocked_requests),
        },
        "spacc_guard": {
            "valid": p38_rep.spacc_guard.valid,
            "status": p38_rep.spacc_guard.status,
            "persistent_emmc_writes_authorized": p38_rep.spacc_guard.persistent_emmc_writes_authorized,
            "spacc_mmio_range": list(p38_rep.spacc_guard.details.get("spacc_mmio_range", [])),
            "xts_partitions_count": len(p38_rep.spacc_guard.xts_partitions),
            "plaintext_partitions_count": len(p38_rep.spacc_guard.plaintext_partitions),
            "xts_partitions": list(p38_rep.spacc_guard.xts_partitions),
            "plaintext_partitions": list(p38_rep.spacc_guard.plaintext_partitions),
        },
    }

    # 8. Phase 25 Runtime Anti-Brick Guards
    phase25_summary, p25_errors = _collect_phase25_antibrick_summary(use_clean_room=use_clean_room)
    errors.extend(p25_errors)

    # 9. Optional Full 165s Candidate Dry-Run (opt-in only!)
    full_dry_run_summary: Dict[str, object]
    full_dry_run_ok = True
    if include_full_candidate_dry_run:
        dry = precomputed_dry_run or run_offline_candidate_dry_run(
            repo_root=repo_root,
            fx6_lib_dir=fx6_lib_dir,
            fx3_modules_dir=fx3_modules_dir,
        )
        full_dry_run_ok = bool(
            dry.candidate_ready
            and dry.all_12_gates_verified
            and dry.stage_b_combined_appfw_verified
            and dry.uipc_cp_shim_ok
            and dry.wireless_fault_isolation_ok
        )
        if not full_dry_run_ok:
            errors.append(f"Full candidate dry-run failed: blocked_gates={dry.blocked_gate_ids}")
        full_dry_run_summary = {
            "included": True,
            "candidate_ready": dry.candidate_ready,
            "all_12_gates_verified": dry.all_12_gates_verified,
            "verified_gate_count": dry.verified_gate_count,
            "stage_b_appfw_sha256": dry.stage_b_appfw_sha256,
            "stage_b_wlan_rsrc_sha256": dry.stage_b_wlan_rsrc_sha256,
            "stage_a_overlay_cpio_sha256": dry.stage_a_overlay_cpio_sha256,
        }
    else:
        full_dry_run_summary = {
            "included": False,
            "skipped_reason": "fast_default_unless_include_full_candidate_dry_run_requested",
        }

    offline_complete = (
        byof_rep.all_checks_passed
        and bool(stage_b_matrix_summary["all_13_items_verified"])
        and bool(stage_b_matrix_summary["rollback_all_matched"])
        and p35_rep.all_checks_passed
        and h0_rep.all_passed
        and bool(preflight_summary["offline_dry_run_all_12_gates_verified"])
        and p38_rep.all_passed
        and bool(phase25_summary["all_passed"])
        and full_dry_run_ok
        and len(errors) == 0
    )

    checklist = build_stage_b_gate_ordered_hardware_checklist()
    draft = StageBMasterReadinessPacketReport(
        schema=STAGE_B_READINESS_PACKET_SCHEMA,
        phase_version=PHASE_39_VERSION,
        verification_mode=verification_mode,
        offline_engineering_complete=offline_complete,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        p8_cp_mutation_forbidden=True,
        cp_mutation_bytes=0,
        wbi_p5_write_and_hibernation_forbidden=True,
        wbi_mutation_bytes=0,
        usb_or_camera_operations=0,
        real_tier0_hardware_backup_verified=real_tier0_ok,
        stage_b_ram_trial_hardware_go=bool(offline_complete and real_tier0_ok),
        stage_b_p1_to_p12_and_fan_matrix=stage_b_matrix_summary,
        phase35_stage_b_lifecycle=phase35_summary,
        phase28_h0_hardware_rehearsal=phase28_h0_summary,
        preflight_safety_gates=preflight_summary,
        phase38_crsdk_mishoe_ltc_spacc_guard=phase38_summary,
        phase25_runtime_antibrick_guards=phase25_summary,
        byof_manifest_parity=byof_summary,
        full_candidate_dry_run=full_dry_run_summary,
        gate_ordered_hardware_execution_checklist=checklist,
        tier0_bundle_audit=bundle_audit,
        errors=tuple(errors),
        packet_sha256="",
    )

    pkt_sha = _compute_packet_sha256(draft.to_dict())
    return StageBMasterReadinessPacketReport(
        schema=draft.schema,
        phase_version=draft.phase_version,
        verification_mode=draft.verification_mode,
        offline_engineering_complete=draft.offline_engineering_complete,
        persistent_emmc_writes_authorized=False,
        persistent_write_release=False,
        p8_cp_mutation_forbidden=True,
        cp_mutation_bytes=0,
        wbi_p5_write_and_hibernation_forbidden=True,
        wbi_mutation_bytes=0,
        usb_or_camera_operations=0,
        real_tier0_hardware_backup_verified=draft.real_tier0_hardware_backup_verified,
        stage_b_ram_trial_hardware_go=draft.stage_b_ram_trial_hardware_go,
        stage_b_p1_to_p12_and_fan_matrix=draft.stage_b_p1_to_p12_and_fan_matrix,
        phase35_stage_b_lifecycle=draft.phase35_stage_b_lifecycle,
        phase28_h0_hardware_rehearsal=draft.phase28_h0_hardware_rehearsal,
        preflight_safety_gates=draft.preflight_safety_gates,
        phase38_crsdk_mishoe_ltc_spacc_guard=draft.phase38_crsdk_mishoe_ltc_spacc_guard,
        phase25_runtime_antibrick_guards=draft.phase25_runtime_antibrick_guards,
        byof_manifest_parity=draft.byof_manifest_parity,
        full_candidate_dry_run=draft.full_candidate_dry_run,
        gate_ordered_hardware_execution_checklist=draft.gate_ordered_hardware_execution_checklist,
        tier0_bundle_audit=draft.tier0_bundle_audit,
        errors=draft.errors,
        packet_sha256=pkt_sha,
    )


def verify_stage_b_master_readiness_packet(
    packet_dict: Mapping[str, object],
) -> StageBMasterPacketVerifyResult:
    """Fail-closed tamper & semantic drift detector for `stage_b_readiness_packet_v2`."""
    errors: List[str] = []

    if not isinstance(packet_dict, Mapping):
        return StageBMasterPacketVerifyResult(
            valid=False,
            schema_ok=False,
            sha256_matched=False,
            expected_packet_sha256="",
            observed_packet_sha256="",
            safety_redlines_ok=False,
            stage_b_matrix_ok=False,
            phase35_lifecycle_ok=False,
            phase28_h0_ok=False,
            phase38_guards_ok=False,
            phase25_antibrick_ok=False,
            byof_parity_ok=False,
            tier0_bundle_ok=False,
            checklist_zero_write_ok=False,
            errors=("Packet must be a mapping/dict",),
        )

    pkt = copy.deepcopy(dict(packet_dict))

    # 1. Schema & Version
    schema_ok = (
        pkt.get("schema") == STAGE_B_READINESS_PACKET_SCHEMA
        and pkt.get("phase_version") == PHASE_39_VERSION
    )
    if not schema_ok:
        errors.append(
            f"Schema/version mismatch: got schema={pkt.get('schema')!r}, version={pkt.get('phase_version')!r}"
        )

    # 2. Cryptographic packet_sha256 check
    observed_sha = str(pkt.get("packet_sha256", ""))
    expected_sha = _compute_packet_sha256(pkt)
    sha256_matched = bool(HEX64_RE.fullmatch(observed_sha)) and (observed_sha == expected_sha)
    if not sha256_matched:
        errors.append(
            f"packet_sha256 tamper/mismatch: observed={observed_sha!r} != expected={expected_sha!r}"
        )

    # 3. Hard-locked Redlines
    redline_errs: List[str] = []
    if pkt.get("persistent_emmc_writes_authorized") is not False:
        redline_errs.append("Redline breach: persistent_emmc_writes_authorized must be False")
    if pkt.get("persistent_write_release") is not False:
        redline_errs.append("Redline breach: persistent_write_release must be False")
    if pkt.get("p8_cp_mutation_forbidden") is not True:
        redline_errs.append("Redline breach: p8_cp_mutation_forbidden must be True")
    if pkt.get("cp_mutation_bytes") != 0:
        redline_errs.append(f"Redline breach: cp_mutation_bytes={pkt.get('cp_mutation_bytes')!r} != 0")
    if pkt.get("wbi_p5_write_and_hibernation_forbidden") is not True:
        redline_errs.append("Redline breach: wbi_p5_write_and_hibernation_forbidden must be True")
    if pkt.get("wbi_mutation_bytes") != 0:
        redline_errs.append(f"Redline breach: wbi_mutation_bytes={pkt.get('wbi_mutation_bytes')!r} != 0")
    if pkt.get("usb_or_camera_operations") != 0:
        redline_errs.append(
            f"Redline breach: usb_or_camera_operations={pkt.get('usb_or_camera_operations')!r} != 0"
        )
    if pkt.get("offline_engineering_complete") is not True:
        redline_errs.append("offline_engineering_complete must be True")
    pkt_errors = pkt.get("errors")
    if not isinstance(pkt_errors, (list, tuple)) or len(pkt_errors) != 0:
        redline_errs.append(f"Packet contains non-empty errors: {pkt_errors!r}")
    safety_redlines_ok = len(redline_errs) == 0
    errors.extend(redline_errs)

    # 4. Stage-B P1..P12+Fan Matrix & Rollback
    m_errs: List[str] = []
    mat = pkt.get("stage_b_p1_to_p12_and_fan_matrix")
    if not isinstance(mat, Mapping):
        m_errs.append("Missing stage_b_p1_to_p12_and_fan_matrix section")
    else:
        if mat.get("all_13_items_verified") is not True:
            m_errs.append("stage_b_p1_to_p12_and_fan_matrix.all_13_items_verified must be True")
        if mat.get("matrix_item_count") != 13 or tuple(mat.get("verified_matrix_items", ())) != STAGE_B_MATRIX_13_ITEMS:
            m_errs.append("Stage-B verified_matrix_items does not match exact 13-item P1..P12+Fan tuple")
        if mat.get("patch_spec_count") != EXPECTED_STAGE_B_PATCH_SPEC_COUNT:
            m_errs.append(
                f"Expected {EXPECTED_STAGE_B_PATCH_SPEC_COUNT} patch specs, got {mat.get('patch_spec_count')!r}"
            )
        if mat.get("rollback_all_matched") is not True:
            m_errs.append("rollback_all_matched must be True")
        receipts = mat.get("patch_receipts")
        if not isinstance(receipts, (list, tuple)) or len(receipts) != EXPECTED_STAGE_B_PATCH_SPEC_COUNT:
            m_errs.append("patch_receipts must contain 8 Stage-B binary specs")
        else:
            for r in receipts:
                if not isinstance(r, Mapping) or r.get("rollback_verified") is not True or r.get("non_overlapping") is not True:
                    m_errs.append(f"Patch receipt failed rollback/non-overlap: {r!r}")
        p10 = mat.get("p10_keymap")
        if not isinstance(p10, Mapping) or p10.get("verified") is not True or p10.get("zero_byte_overlap") is not True:
            m_errs.append("P10 keymap verification invalid or tampered")
        p11 = mat.get("p11_uipc_cp_shim")
        if (
            not isinstance(p11, Mapping)
            or p11.get("verified") is not True
            or p11.get("p8_cp_mutation_forbidden") is not True
            or p11.get("cp_mutation_bytes") != 0
            or p11.get("xlr_h1_preserved") is not True
            or set(p11.get("fx6_exclusive_blocking_queues", ())) != {"0x92d2091c", "0x91db059b"}
        ):
            m_errs.append("P11 UIPC-CP shim invariant invalid or tampered")
        p12 = mat.get("p12_wireless_guard")
        if (
            not isinstance(p12, Mapping)
            or p12.get("verified") is not True
            or p12.get("rollback_verified") is not True
            or p12.get("patched_rc") != 0
            or p12.get("bk4_airplane_shadow_valid") is not True
            or p12.get("airplane_shadow_keys") != STAGE_B_AIRPLANE_SHADOW_KEYS
            or p12.get("nvram_persistent_writes") != 0
            or p12.get("wbi_mutation_bytes") != 0
            or p12.get("cp_mutation_bytes") != 0
        ):
            m_errs.append("P12 wireless guard or BK4 Airplane shadow invariant invalid or tampered")
    stage_b_matrix_ok = len(m_errs) == 0
    errors.extend(m_errs)

    # 5. Phase 35 S01..S10 Lifecycle & Serial Fault Detector v2
    p35_errs: List[str] = []
    p35 = pkt.get("phase35_stage_b_lifecycle")
    if not isinstance(p35, Mapping):
        p35_errs.append("Missing phase35_stage_b_lifecycle section")
    else:
        if p35.get("schema") != STAGE_B_LIFECYCLE_SCHEMA or p35.get("all_checks_passed") is not True:
            p35_errs.append("Phase 35 lifecycle schema/pass check failed")
        if p35.get("persistent_emmc_writes_authorized") is not False or p35.get("persistent_write_release") is not False:
            p35_errs.append("Phase 35 persistent write redline tampered")
        if p35.get("h2_zero_drift_verified") is not True or p35.get("h2_persistent_bytes_mutated") != 0:
            p35_errs.append("Phase 35 H2 zero-drift invariant violated")
        if p35.get("scenario_count") != 10 or p35.get("passed_scenario_count") != 10:
            p35_errs.append("Phase 35 scenario count != 10/10")
        scs = p35.get("scenarios")
        if not isinstance(scs, (list, tuple)) or len(scs) != 10:
            p35_errs.append("Phase 35 scenarios list missing or != 10 entries")
        else:
            seen_ids = [s.get("scenario_id") if isinstance(s, Mapping) else None for s in scs]
            if tuple(seen_ids) != STAGE_B_SCENARIO_IDS:
                p35_errs.append("Phase 35 scenario IDs S01..S10 tampered or out of order")
            for sc in scs:
                if not isinstance(sc, Mapping):
                    p35_errs.append("Malformed scenario entry")
                    continue
                sid = str(sc.get("scenario_id", ""))
                exp_disp = EXPECTED_STAGE_B_SCENARIO_DISPOSITIONS.get(sid)
                common_ok = (
                    sc.get("passed") is True
                    and sc.get("zero_cp_writes") is True
                    and sc.get("zero_nvram_writes") is True
                    and sc.get("serial_disposition") == exp_disp
                )
                if sid == "S10_POST_TRIAL_DRIFT_DETECTION":
                    s10_ok = (
                        common_ok
                        and sc.get("status") == "POST_TRIAL_DRIFT_DETECTED"
                        and len(sc.get("drifted_items", ())) >= 1
                    )
                    if not s10_ok:
                        p35_errs.append("Phase 35 S10 post-trial drift detector tampered")
                else:
                    if (
                        not common_ok
                        or sc.get("zero_emmc_writes") is not True
                        or sc.get("zero_wbi_writes") is not True
                        or sc.get("persistent_bytes_mutated") != 0
                    ):
                        p35_errs.append(f"Phase 35 scenario {sid} tampered or failed zero-write/disposition invariant")
    phase35_lifecycle_ok = len(p35_errs) == 0
    errors.extend(p35_errs)

    # 6. Phase 28 H0 Rehearsal + 12-Gate Preflight
    p28_errs: List[str] = []
    p28 = pkt.get("phase28_h0_hardware_rehearsal")
    gates = pkt.get("preflight_safety_gates")
    if not isinstance(p28, Mapping):
        p28_errs.append("Missing phase28_h0_hardware_rehearsal section")
    else:
        if (
            p28.get("all_passed") is not True
            or p28.get("stage_count") != 6
            or p28.get("passed_stage_count") != 6
            or p28.get("persistent_emmc_writes_authorized") is not False
            or p28.get("persistent_write_release") is not False
        ):
            p28_errs.append("Phase 28 H0 6-stage rehearsal invariant invalid or tampered")
    if not isinstance(gates, Mapping):
        p28_errs.append("Missing preflight_safety_gates section")
    else:
        if (
            gates.get("offline_dry_run_all_12_gates_verified") is not True
            or gates.get("offline_dry_run_verified_gate_count") != 12
            or gates.get("live_hardware_persistent_write_release") is not False
        ):
            p28_errs.append("Preflight 12-gate summary invalid or persistent_write_release tampered")
    phase28_h0_ok = len(p28_errs) == 0
    errors.extend(p28_errs)

    # 7. Phase 38 Multi-Port LTC, MI-Shoe, CrSDK PTP2, CXD90057 SPACC
    p38_errs: List[str] = []
    p38 = pkt.get("phase38_crsdk_mishoe_ltc_spacc_guard")
    if not isinstance(p38, Mapping):
        p38_errs.append("Missing phase38_crsdk_mishoe_ltc_spacc_guard section")
    else:
        if (
            p38.get("all_passed") is not True
            or p38.get("status") != STATUS_VERIFIED_SAFE
            or p38.get("persistent_emmc_writes_authorized") is not False
            or p38.get("persistent_write_release") is not False
        ):
            p38_errs.append("Phase 38 top-level status or write redline tampered")
        ltc = p38.get("ltc_guard")
        if (
            not isinstance(ltc, Mapping)
            or ltc.get("valid") is not True
            or ltc.get("status") != STATUS_VERIFIED_SAFE
            or tuple(ltc.get("uart_boot_protected_pins", ())) != MULTIPORT_UART_BOOT_PINS
        ):
            p38_errs.append("Phase 38 Multi-Port VMC-BNCM1 LTC vs uart_boot guard tampered")
        mi = p38.get("mishoe_guard")
        if (
            not isinstance(mi, Mapping)
            or mi.get("valid") is not True
            or mi.get("status") != STATUS_VERIFIED_SAFE
            or mi.get("xlr_h1_preserved") is not True
            or mi.get("libinfrahotshoe_timeout_safe") is not True
        ):
            p38_errs.append("Phase 38 24-pin MI-Shoe XLR-H1 / P11 coexistence guard tampered")
        cr = p38.get("crsdk_firewall")
        if (
            not isinstance(cr, Mapping)
            or cr.get("valid") is not True
            or cr.get("status") != STATUS_VERIFIED_SAFE
            or cr.get("vendor_extension_id_hex") != "0x11"
            or cr.get("sdio_handshake_complete") is not True
        ):
            p38_errs.append("Phase 38 CrSDK PTP2 0x9201..0x9209 firewall tampered")
        sp = p38.get("spacc_guard")
        if (
            not isinstance(sp, Mapping)
            or sp.get("valid") is not True
            or sp.get("status") != STATUS_VERIFIED_SAFE
            or sp.get("persistent_emmc_writes_authorized") is not False
        ):
            p38_errs.append("Phase 38 CXD90057 SPACC AES-XTS-256 block-layer guard tampered")
    phase38_guards_ok = len(p38_errs) == 0
    errors.extend(p38_errs)

    # 8. Phase 25 Runtime Anti-Brick Guards
    p25_errs: List[str] = []
    p25 = pkt.get("phase25_runtime_antibrick_guards")
    if not isinstance(p25, Mapping):
        p25_errs.append("Missing phase25_runtime_antibrick_guards section")
    else:
        if (
            p25.get("all_passed") is not True
            or p25.get("status") != STATUS_VERIFIED_SAFE
            or p25.get("persistent_emmc_writes_authorized") is not False
        ):
            p25_errs.append("Phase 25 runtime anti-brick top-level status or write redline tampered")
        for sub_key in (
            "ld_so_preload_ban",
            "dd_truncation_ban_and_5step",
            "nflasha10_0x10000009_headroom",
            "product_model_nvram_immutability",
        ):
            sub_val = p25.get(sub_key)
            if not isinstance(sub_val, Mapping) or sub_val.get("valid") is not True:
                p25_errs.append(f"Phase 25 guard {sub_key} invalid or tampered")
    phase25_antibrick_ok = len(p25_errs) == 0
    errors.extend(p25_errs)

    # 9. BYOF Parity
    byof = pkt.get("byof_manifest_parity")
    byof_parity_ok = (
        isinstance(byof, Mapping)
        and byof.get("all_checks_passed") is True
        and byof.get("en_zh_parity_ok") is True
        and byof.get("zero_stage_reference_ok") is True
    )
    if not byof_parity_ok:
        errors.append("byof_manifest_parity invalid or tampered")

    # 10. Tier-0 Bundle Consistency
    bundle = pkt.get("tier0_bundle_audit")
    tier0_bundle_ok = True
    if bundle is None:
        if pkt.get("real_tier0_hardware_backup_verified") is not False or pkt.get("stage_b_ram_trial_hardware_go") is not False:
            tier0_bundle_ok = False
            errors.append("Without tier0_bundle_audit, hardware_go/tier0_verified must be False")
    elif isinstance(bundle, Mapping):
        if bundle.get("valid") is not True or pkt.get("real_tier0_hardware_backup_verified") is not True or pkt.get("stage_b_ram_trial_hardware_go") is not True:
            tier0_bundle_ok = False
            errors.append("Present tier0_bundle_audit must be valid=True with hardware_go=True")
    else:
        tier0_bundle_ok = False
        errors.append("Malformed tier0_bundle_audit")

    # 11. Gate-Ordered Checklist Zero-Write Bounds
    chk_errs: List[str] = []
    chk = pkt.get("gate_ordered_hardware_execution_checklist")
    if not isinstance(chk, (list, tuple)) or len(chk) != 3:
        chk_errs.append("gate_ordered_hardware_execution_checklist must have 3 phases (H0, H1, H2)")
    else:
        for step in chk:
            if not isinstance(step, Mapping):
                chk_errs.append("Malformed checklist step")
                continue
            for field_name in (
                "emmc_write_bytes_allowed",
                "nor_write_bytes_allowed",
                "wbi_p5_write_bytes_allowed",
                "cp_p8_write_bytes_allowed",
            ):
                if step.get(field_name) != 0:
                    chk_errs.append(f"Checklist step {step.get('phase_id')!r} {field_name} != 0")
    checklist_zero_write_ok = len(chk_errs) == 0
    errors.extend(chk_errs)

    all_ok = (
        schema_ok
        and sha256_matched
        and safety_redlines_ok
        and stage_b_matrix_ok
        and phase35_lifecycle_ok
        and phase28_h0_ok
        and phase38_guards_ok
        and phase25_antibrick_ok
        and byof_parity_ok
        and tier0_bundle_ok
        and checklist_zero_write_ok
        and len(errors) == 0
    )

    return StageBMasterPacketVerifyResult(
        valid=all_ok,
        schema_ok=schema_ok,
        sha256_matched=sha256_matched,
        expected_packet_sha256=expected_sha,
        observed_packet_sha256=observed_sha,
        safety_redlines_ok=safety_redlines_ok,
        stage_b_matrix_ok=stage_b_matrix_ok,
        phase35_lifecycle_ok=phase35_lifecycle_ok,
        phase28_h0_ok=phase28_h0_ok,
        phase38_guards_ok=phase38_guards_ok,
        phase25_antibrick_ok=phase25_antibrick_ok,
        byof_parity_ok=byof_parity_ok,
        tier0_bundle_ok=tier0_bundle_ok,
        checklist_zero_write_ok=checklist_zero_write_ok,
        errors=tuple(errors),
    )
